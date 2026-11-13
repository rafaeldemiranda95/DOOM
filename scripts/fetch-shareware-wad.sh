#!/usr/bin/env bash
# Baixa o DOOM shareware IWAD (v1.8) e grava como ./wad/doom1.wad
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WAD_DIR="$ROOT/wad"
GZ="$WAD_DIR/doom1v18.wad.gz"
OUT="$WAD_DIR/doom1.wad"
URL="http://www.ibiblio.org/pub/linux/games/doom/doom1v18.wad.gz"

mkdir -p "$WAD_DIR"

if [[ -f "$OUT" ]] && [[ "$(wc -c < "$OUT")" -gt 1000000 ]]; then
  echo "Já existe: $OUT"
  exit 0
fi

echo "Baixando $URL ..."
curl -fsSL -o "$GZ" "$URL"
gzip -dc "$GZ" > "$OUT"
rm -f "$GZ"

BYTES="$(wc -c < "$OUT")"
if [[ "$BYTES" -lt 1000000 ]]; then
  echo "doom1.wad inválido ($BYTES bytes)" >&2
  exit 1
fi
echo "OK: $OUT ($BYTES bytes)"
