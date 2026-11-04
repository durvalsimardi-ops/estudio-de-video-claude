#!/usr/bin/env bash
# Copia o exemplo Remotion para uma pasta de trabalho, põe as fontes (com licença) e instala as dependências ali.
# Uso (na raiz do estúdio): bash .claude/skills/remotion-ou-hyperframes/preparar.sh trabalho/<nome-da-peca>
# O node_modules fica dentro de trabalho/ (que não vai para o git). Precisa de internet só na primeira vez.
set -eu
DESTINO="${1:?Diga a pasta da peça, ex.: trabalho/abertura-remotion}"
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/../../.." && pwd)"
if [ -e "$DESTINO/package.json" ]; then echo "Já existe $DESTINO/package.json. Escolha outro nome."; exit 1; fi
mkdir -p "$DESTINO/public/fontes" "$DESTINO/render"
cp -R "$AQUI/exemplo-remotion/." "$DESTINO/"
cp "$RAIZ/assets/fontes/fraunces/Fraunces-600.woff2" "$DESTINO/public/fontes/"
cp "$RAIZ/assets/fontes/fraunces/OFL.txt" "$DESTINO/public/fontes/OFL-Fraunces.txt"
cp "$RAIZ/assets/fontes/inter/Inter-400.woff2" "$DESTINO/public/fontes/"
cp "$RAIZ/assets/fontes/inter/OFL.txt" "$DESTINO/public/fontes/OFL-Inter.txt"
cd "$DESTINO" && npm install --no-audit --no-fund
echo "Pronto. Ver: (cd $DESTINO && npm run studio)   Gravar: (cd $DESTINO && npm run render)"
