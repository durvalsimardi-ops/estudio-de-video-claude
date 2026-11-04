#!/usr/bin/env bash
# Prepara o estúdio: confere o que já está instalado e mostra o que falta ANTES de instalar.
# Uso: bash ferramentas/instalar.sh            → só confere e lista o que falta
#      bash ferramentas/instalar.sh --instalar → instala o que falta (pede confirmação)
# Instala: ffmpeg e yt-dlp (Homebrew), Node.js, e um Python só do estúdio em .venv com o Whisper.
# Nada é instalado fora do Homebrew e da pasta .venv deste projeto.
set -u
cd "$(dirname "$0")/.."
INSTALAR=0; [ "${1:-}" = "--instalar" ] && INSTALAR=1
SO="$(uname -s)"; CHIP="$(uname -m)"
falta=()

tem() { command -v "$1" >/dev/null 2>&1; }
linha() { printf "  %-10s %s\n" "$1" "$2"; }

echo "Estúdio de Vídeo · conferência ($SO $CHIP)"
for p in ffmpeg yt-dlp node python3; do
  if tem "$p"; then linha "$p" "ok"; else linha "$p" "FALTA"; falta+=("$p"); fi
done
if [ -x .venv/bin/python ] && .venv/bin/python -c "import numpy, PIL" 2>/dev/null; then linha ".venv" "ok"; else linha ".venv" "FALTA (Python do estúdio com Whisper)"; falta+=("venv"); fi
if [ "$SO" = "Darwin" ]; then
  if tem swift; then linha "swift" "ok (recorte de pessoa)"; else linha "swift" "FALTA: rode  xcode-select --install"; fi
fi
if tem node; then
  NV=$(node -p 'process.versions.node.split(".")[0]')
  if [ "$NV" -ge 22 ]; then linha "hyperframes" "Node $NV ok · confira com: npx hyperframes doctor (aula 21)"; else linha "node" "versão $NV: o HyperFrames pede 22 ou mais"; falta+=("node"); fi
fi
tem blender && linha "blender" "ok (opcional, aula 23)" || linha "blender" "opcional: só para a aula 23"

if [ ${#falta[@]} -eq 0 ]; then echo "Tudo pronto."; exit 0; fi
echo; echo "Falta: ${falta[*]}"
[ $INSTALAR -eq 0 ] && { echo "Para instalar: bash ferramentas/instalar.sh --instalar"; exit 0; }

read -r -p "Instalar agora? [s/N] " ok; [ "$ok" = "s" ] || [ "$ok" = "S" ] || exit 0
if [ "$SO" = "Darwin" ]; then
  tem brew || { echo "Instale o Homebrew primeiro: https://brew.sh (o Claude pode te mostrar o comando)."; exit 1; }
  for p in ffmpeg yt-dlp node python3; do
    case " ${falta[*]} " in *" $p "*) brew install "${p/python3/python}";; esac
  done
else
  echo "Fora do Mac: instale ffmpeg, yt-dlp, Node.js e Python 3 pelo gerenciador do seu sistema (winget no Windows) e rode de novo."
fi
case " ${falta[*]} " in *" venv "*)
  python3 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  if [ "$SO" = "Darwin" ] && [ "$CHIP" = "arm64" ]; then .venv/bin/pip install -q numpy pillow mlx-whisper
  else .venv/bin/pip install -q numpy pillow faster-whisper; fi
  ;;
esac
echo "Pronto. Rode de novo para conferir: bash ferramentas/instalar.sh"
