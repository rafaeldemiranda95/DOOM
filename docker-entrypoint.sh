#!/bin/sh
set -eu

# Evita morte do linuxxdoom (exit 141) quando o sndserver OSS já morreu:
# atirar (Ctrl) escrevia no pipe → SIGPIPE → container cai → noVNC desconecta.
trap '' PIPE

IWAD=""
for f in doom1.wad doom.wad doom2.wad doomu.wad plutonia.wad tnt.wad; do
  if [ -f "/wad/$f" ]; then
    IWAD="$f"
    break
  fi
done

if [ -z "$IWAD" ]; then
  echo "Nenhum IWAD em /wad. Monte um volume com doom1.wad (ex.: -v ./wad:/wad:ro)" >&2
  exit 1
fi

ln -sfn "/wad/$IWAD" "/doom/$IWAD"

# Não inicia sndserver (/dev/dsp inexistente). Sem isso o pipe quebra no 1º tiro.
rm -f /doom/sndserver

export DISPLAY=:99
export HOME="${HOME:-/root}"
export DOOMWADDIR=/doom

# 24-bit TrueColor; 640x400 casa com escala -2 do Doom (320x200*2)
XVFB_GEOM="${XVFB_GEOM:-640x400x24}"

Xvfb :99 -screen 0 "$XVFB_GEOM" -ac +extension MIT-SHM >/tmp/xvfb.log 2>&1 &
XVFB_PID=$!

cleanup() {
  kill "$DOOM_PID" 2>/dev/null || true
  kill "$NOVNC_PID" 2>/dev/null || true
  kill "$X11VNC_PID" 2>/dev/null || true
  kill "$XVFB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

i=0
while [ "$i" -lt 50 ]; do
  if xdpyinfo -display :99 >/dev/null 2>&1; then
    break
  fi
  i=$((i + 1))
  sleep 0.1
done

x11vnc -display :99 -forever -shared -rfbport 5900 -nopw -xkb -repeat \
  -noxdamage -ncache 0 >/tmp/x11vnc.log 2>&1 &
X11VNC_PID=$!

websockify --web=/usr/share/novnc/ 8080 localhost:5900 >/tmp/novnc.log 2>&1 &
NOVNC_PID=$!

cd /doom

# -2 escala 2x (640x400). Sem args extras: E1M1 direto.
# Mouse: grab ativo por padrão (virar + botão esquerdo atira).
if [ "$#" -eq 0 ]; then
  set -- -2 -skill 3 -warp 1 1
fi

echo "DOOM no navegador: http://localhost:8080/vnc.html?autoconnect=1&resize=scale"
echo "Controles: WASD/setas=mover, mouse=virar, Ctrl/botao-esquerdo=atirar, scroll=arma, Espaco=usar"

./linuxxdoom "$@" &
DOOM_PID=$!

wait "$DOOM_PID"
