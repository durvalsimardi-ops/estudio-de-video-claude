#!/usr/bin/env bash
# Cria uma peça nova de motion a partir do exemplo comentado.
# Uso (na raiz do estúdio): bash .claude/skills/motion-hyperframes/nova-peca.sh trabalho/<nome-da-peca>
# Copia o index.html do exemplo e as fontes (com as licenças) para a pasta da peça. Não sobrescreve peça existente.
set -eu
DESTINO="${1:?Diga a pasta da peça, ex.: trabalho/abertura-aurora}"
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/../../.." && pwd)"
if [ -e "$DESTINO/index.html" ]; then echo "Já existe $DESTINO/index.html. Escolha outro nome ou edite essa peça."; exit 1; fi
mkdir -p "$DESTINO/fontes" "$DESTINO/render"
cp "$AQUI/exemplo/index.html" "$DESTINO/index.html"
cp "$RAIZ/assets/fontes/fraunces/Fraunces-600.woff2" "$DESTINO/fontes/"
cp "$RAIZ/assets/fontes/fraunces/OFL.txt" "$DESTINO/fontes/OFL-Fraunces.txt"
cp "$RAIZ/assets/fontes/inter/Inter-400.woff2" "$RAIZ/assets/fontes/inter/Inter-600.woff2" "$DESTINO/fontes/"
cp "$RAIZ/assets/fontes/inter/OFL.txt" "$DESTINO/fontes/OFL-Inter.txt"
echo "Pronto: $DESTINO"
echo "Ver no navegador:  npx hyperframes preview $DESTINO"
echo "Renderizar:        npx hyperframes render $DESTINO -o $DESTINO/render/abertura.mp4"
