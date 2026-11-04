#!/usr/bin/env bash
# Atalho do recorte de pessoa (só no Mac). Compila ferramentas/recorte.swift uma vez,
# guarda o programa em trabalho/.ferramentas/ e roda. Se o .swift mudar, compila de novo.
# Uso: bash ferramentas/recorte.sh <video> <pasta-de-saida> [--so-rostos] [--inicio s] [--fim s] [--fps 30] [--qualidade precisa|equilibrada|rapida]
set -e
cd "$(dirname "$0")/.."
RAIZ="$(pwd)"
cd - >/dev/null
[ "$(uname -s)" = "Darwin" ] || { echo "O recorte usa o Vision da Apple e só roda no Mac. No Windows, veja a nota no SKILL.md (rembg ou MediaPipe)."; exit 1; }
command -v swiftc >/dev/null || { echo "Falta o compilador da Apple. Rode: xcode-select --install"; exit 1; }
FONTE="$RAIZ/ferramentas/recorte.swift"
BIN="$RAIZ/trabalho/.ferramentas/recorte"
if [ ! -x "$BIN" ] || [ "$FONTE" -nt "$BIN" ]; then
  mkdir -p "$(dirname "$BIN")"
  echo "Preparando o recorte (só na primeira vez, uns 30 s)..."
  swiftc -O -o "$BIN" "$FONTE"
fi
exec "$BIN" "$@"
