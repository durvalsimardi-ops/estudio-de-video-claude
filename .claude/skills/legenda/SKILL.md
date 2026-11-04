---
name: legenda
description: Coloca legenda palavra a palavra queimada no vídeo, com a palavra falada acesa e palavras-chave em cor, sempre fora da faixa dos botões do Instagram. Usar quando o aluno disser "põe legenda", "legenda dinâmica", "legenda palavra por palavra", "destaca a palavra", "legenda igual de Reels" ou "a legenda ficou embaixo dos botões".
---

# Legenda palavra a palavra (aula 10)

A legenda aparece em blocos de até 3 palavras; a palavra que está sendo dita acende, e as palavras-chave ganham cor.

## Antes de começar

- Precisa do `palavras.json` no tempo do vídeo (sai do `/cortar-fala`). Sem ele, transcreva:
  `.venv/bin/python ferramentas/transcrever.py <video> trabalho/<peça>/palavras.json`
- Precisa do Pillow no Python do estúdio. Confira com `.venv/bin/python -c "import PIL"`; se der erro: `.venv/bin/pip install pillow`.
- Pergunte quais são as palavras-chave (produto, preço, marca) e se a marca tem cor própria (veja `marcas/<marca>/`).

## Passo a passo

1. Legendar:
   ```
   .venv/bin/python .claude/skills/legenda/legenda.py trabalho/<peça>/corte/cortado.mp4 trabalho/<peça>/corte/palavras.json trabalho/<peça>/legenda --chaves "café,aurora,promoção"
   ```
2. Opções mais usadas:
   - `--por-vez 2` (menos palavras por vez), `--caixa-alta`, `--tamanho 90`;
   - `--estilo caixa --cor-caixa "#FF5A36"`: a palavra falada ganha uma caixa colorida;
   - `--cor-chave "#FFD23F"`: cor das palavras-chave; `--altura 0.55`: sobe a legenda;
   - `--fonte assets/fontes/<outra>.ttf`: outra fonte (só com licença livre, com o arquivo de licença junto).
3. Saem em `trabalho/<peça>/legenda/`: `legendado.mp4`, `legenda.srt` e `conferencia-legenda.jpg`.

## Como conferir

- Abra `conferencia-legenda.jpg` (Read): seis quadros com duas linhas vermelhas. Todo texto tem que ficar entre elas.
- Confira se as palavras estão escritas certo (nomes, marcas, números). Se houver erro, corrija o texto no `palavras.json` (só o campo `w`) e rode de novo.
- Veja se a legenda não cobre o rosto; se cobrir, mude `--altura`.

## Regras

- Letra nunca menor que 34 px em 1080 de largura (o script não deixa passar do piso).
- No 9:16 o texto fica entre y 250 e y 1560: embaixo ficam os botões e a descrição do Instagram.
- Fonte padrão: Montserrat ExtraBold, licença OFL (`assets/fontes/montserrat/OFL.txt`).
- Se for fazer transições (`/transicoes`), rode as transições antes e a legenda depois: assim o texto não balança junto com o chicote e o zoom.
- Windows: `.venv\Scripts\python` e `.venv\Scripts\pip` no lugar de `.venv/bin/...`.
