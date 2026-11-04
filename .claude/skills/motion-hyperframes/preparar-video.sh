#!/usr/bin/env bash
# Prepara uma peça de motion POR CIMA de um vídeo gravado (exemplo-sobre-video).
# Uso (na raiz do estúdio):
#   bash .claude/skills/motion-hyperframes/preparar-video.sh <video> trabalho/<nome-da-peca> [inicio] [duracao]
#   ex.: bash .claude/skills/motion-hyperframes/preparar-video.sh originais/fala.mov trabalho/dica-cafe 0 12
# Faz: corta o trecho e converte para 30 qps e 1080x1920 (o HyperFrames busca quadro certo assim),
# transcreve palavra a palavra, e copia o index.html, o config.js e as fontes. Não mexe no vídeo original.
set -eu
VIDEO="${1:?Diga o vídeo, ex.: originais/fala.mov}"
DESTINO="${2:?Diga a pasta da peça, ex.: trabalho/dica-cafe}"
INICIO="${3:-0}"
DURACAO="${4:-}"
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/../../.." && pwd)"
if [ -e "$DESTINO/index.html" ]; then echo "Já existe $DESTINO/index.html. Escolha outro nome ou edite essa peça."; exit 1; fi
mkdir -p "$DESTINO/fontes" "$DESTINO/render"

# 1) trecho em 30 qps constantes, 1080x1920 (corta as sobras se não for 9:16), som AAC
LIMITE=(); [ -n "$DURACAO" ] && LIMITE=(-t "$DURACAO")
ffmpeg -v error -y -ss "$INICIO" -i "$VIDEO" "${LIMITE[@]}" \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p" \
  -c:v libx264 -crf 18 -preset medium -g 30 -c:a aac -b:a 192k -ar 48000 -movflags +faststart "$DESTINO/video.mp4"
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$DESTINO/video.mp4")
D=$(python3 -c "print(round(float('$D') - 0.02, 2))")   # um fio a menos, para nunca pedir quadro além do fim

# 2) palavras com tempo (Whisper local, sem custo)
"$RAIZ/.venv/bin/python" "$RAIZ/ferramentas/transcrever.py" "$DESTINO/video.mp4" "$DESTINO/palavras.json"
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); open(sys.argv[2],'w').write('window.PALAVRAS = '+json.dumps(d,ensure_ascii=False)+';\n')" \
  "$DESTINO/palavras.json" "$DESTINO/palavras.js"

# 3) página, config e fontes
sed "s/__DURACAO__/$D/g" "$AQUI/exemplo-sobre-video/index.html" > "$DESTINO/index.html"
cp "$AQUI/exemplo-sobre-video/config.js" "$DESTINO/config.js"
cp "$RAIZ/assets/fontes/fraunces/Fraunces-600.woff2" "$DESTINO/fontes/"
cp "$RAIZ/assets/fontes/fraunces/OFL.txt" "$DESTINO/fontes/OFL-Fraunces.txt"
cp "$RAIZ/assets/fontes/inter/Inter-600.woff2" "$DESTINO/fontes/"
cp "$RAIZ/assets/fontes/inter/OFL.txt" "$DESTINO/fontes/OFL-Inter.txt"
echo "Pronto: $DESTINO ($D s). Edite $DESTINO/config.js (título, destaques, cartões)."
echo "Ver:        npx hyperframes preview $DESTINO"
echo "Renderizar: npx hyperframes render $DESTINO -o $DESTINO/render/video-com-motion.mp4"
