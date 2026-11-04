---
name: video-desenhado
description: Transforma narração ou texto em vídeo desenhado à mão, com ícones aparecendo traço a traço e as palavras escritas no tempo da fala. Use quando o aluno disser "faz um vídeo desenhado", "estilo quadro branco", "explica desenhando", "transforma essa narração em desenho" ou "vídeo com ícones sendo desenhados". Aula 27.
---

# Vídeo desenhado (aula 27)

Para que serve: cada frase da narração vira uma folha de caderno. Os desenhos aparecem traço a traço, com um lápis seguindo a ponta, e a frase é escrita à mão palavra por palavra no tempo da fala. Palavras de destaque saem em azul e sublinhadas. Saída 1080x1920, 30 qps, com a voz em −14 LUFS.

Arquivos: `pagina.html` (o desenho de cada quadro, `window.seek(t)`), `render.mjs` (acerta o tempo e grava), `exemplo/` (cenas e texto do Café Aurora).

## Antes de começar

- Node.js 22+, ffmpeg e **Google Chrome** (ou Chromium) instalado. O `render.mjs` usa o Chrome em segundo plano, sem pacote npm. Se não achar o Chrome: `CHROME="<caminho do executável>" node ...`.
- Narração: o áudio do aluno (`narracao.wav`, `.mp3`, `.m4a` ou `.aiff`). Narração por ElevenLabs gasta crédito: só com o OK do aluno. Para testar sem custo no Mac: `say -v Luciana -f texto.txt -o narracao.aiff`.
- Ícones: Lucide (licença ISC, gratuita, aviso em `assets/icones/lucide/LICENSE`, que vai junto com o estúdio). 70 ícones em `assets/icones/lucide/`; para outro, baixe o SVG em https://lucide.dev e ponha na mesma pasta. Desenho próprio: um SVG de traço (viewBox 0 0 24 24, sem preenchimento) em `trabalho/<peça>/desenhos/<nome>.svg`.
- Letra manuscrita: Caveat (OFL), em `assets/fontes/caveat/` com o `OFL.txt`.

## Passo a passo

1. Criar a pasta da peça e pôr a narração nela como `narracao.<ext>`:
   ```bash
   mkdir -p trabalho/cafe-desenhado
   ```
2. Transcrever (sem custo):
   ```bash
   .venv/bin/python ferramentas/transcrever.py trabalho/cafe-desenhado/narracao.aiff trabalho/cafe-desenhado/palavras.json
   ```
3. **Pedir a lista de desenhos antes de desenhar.** Dividir a fala em frases e mostrar ao aluno uma tabela: frase → desenhos (1 a 3, nomes dos ícones) → palavra em destaque. Só seguir com o OK.
4. Escrever `trabalho/cafe-desenhado/cenas.json` no formato de `exemplo/cenas.json`:
   - `frase`: igual ao que foi falado (é assim que o tempo casa).
   - `desenhos`: nomes de ícones; para começar numa palavra: `{ "icone": "calendar", "na_palavra": "segunda" }`.
   - `destaques`: palavras em azul. Opcional: `"cores"`, `"letra"` (tamanho, padrão 120) e `"espessura"` do traço.
5. Conferir quadros soltos (rápido):
   ```bash
   node .claude/skills/video-desenhado/render.mjs trabalho/cafe-desenhado --quadros 0.5,2,4,8
   ```
6. Gravar o vídeo inteiro (segundos para 15 s de vídeo):
   ```bash
   node .claude/skills/video-desenhado/render.mjs trabalho/cafe-desenhado
   ```
   Sai `trabalho/cafe-desenhado/render/video.mp4`. Conferido, copiar para `entrega/`.

Testar com o exemplo (Mac, sem custo):
```bash
mkdir -p trabalho/cafe-desenhado && cp .claude/skills/video-desenhado/exemplo/cenas.json trabalho/cafe-desenhado/
say -v Luciana -f .claude/skills/video-desenhado/exemplo/narracao.txt -o trabalho/cafe-desenhado/narracao.aiff
```
e seguir dos passos 2, 5 e 6.

Sem narração, só texto: pule os passos 1 e 2. O tempo é estimado num ritmo calmo e o vídeo sai sem som.

## Como conferir

- O render diz quantas palavras das frases casaram com a fala. Menos de 70% = frase do `cenas.json` diferente do falado: corrigir.
- Quadros em `trabalho/<peça>/quadros/`: desenho pela metade nos primeiros quadros de cada folha (traço a traço), palavra escrita junto com a fala, acento inteiro, nada atrás da faixa de baixo.
- Letra manuscrita (Caveat), não a letra padrão do sistema.
- `ffprobe` com 1080x1920, 30 qps; volume perto de −14 LUFS.

## Regras

- Lista de desenhos aprovada pelo aluno antes de gravar.
- Tudo pelo tempo (`window.seek(t)`): nada de animação solta, `Date.now()` ou `Math.random()`.
- Só ícone e fonte com licença livre, com o arquivo de licença junto. Nada de desenho copiado de outro criador.
- Arquivos de trabalho em `trabalho/<peça>/`, final em `entrega/`.
