#!/bin/sh
set -eu

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

# IWAD em /doom junto com linuxxdoom/sndserver (DOOMWADDIR aponta para cá)
ln -sfn "/wad/$IWAD" "/doom/$IWAD"

# Xvfb em 8 bpp PseudoColor — exigência do i_video.c original
Xvfb :99 -screen 0 640x480x8 -ac +extension MIT-SHM >/tmp/xvfb.log 2>&1 &
XVFB_PID=$!

cleanup() {
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

export DISPLAY=:99
export HOME="${HOME:-/root}"
export DOOMWADDIR=/doom

cd /doom

# Sem args: inicia E1M1 direto (IWAD 1.8 tem demos incompatíveis com engine 1.10)
if [ "$#" -eq 0 ]; then
  set -- -skill 3 -warp 1 1
fi

exec ./linuxxdoom "$@"
