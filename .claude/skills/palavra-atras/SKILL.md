---
name: palavra-atras
description: Coloca uma palavra-chave grande ATRÁS da pessoa (entre ela e o fundo), no tempo da fala. Use quando o aluno disser "palavra atrás de mim", "texto atrás da pessoa", "palavra grande no fundo", "aquele efeito da palavra atrás da cabeça" ou pedir a aula 11.
---

# Palavra atrás da pessoa (aula 11)

A palavra aparece grande no fundo e a pessoa fica na frente dela, cobrindo um pedaço. Uma palavra por ideia, no momento em que ela é falada.

## Antes de começar

- Só no Mac: o recorte da pessoa usa o Vision da Apple. Precisa do `swift` (`xcode-select --install`).
  O atalho `ferramentas/recorte.sh` compila `ferramentas/recorte.swift` uma vez (fica em `trabalho/.ferramentas/`) e depois roda direto. Também funciona sem compilar: `swift ferramentas/recorte.swift <video> <pasta>` (demora mais para começar).
- Uma vez só: `.venv/bin/pip install pillow` (desenha as letras).
- De preferência, o vídeo já passou pelo `/cortar-fala`: assim existem `trabalho/<peça>/cortado.mp4` e `trabalho/<peça>/palavras.json`.

## Passo a passo

1. Recortar a pessoa (gera `matte.mp4` e `rostos.json`):
   ```bash
   bash ferramentas/recorte.sh trabalho/minha-peca/cortado.mp4 trabalho/minha-peca/recorte
   ```
   Para testar rápido num trecho: acrescente `--inicio 0 --fim 12` (a saída será só esse trecho).
2. Escolher as palavras. O aluno diz quais, ou o Claude lê `palavras.json` e sugere uma por ideia (substantivo forte, nada de "então", "muito"). Mostrar a lista e esperar o OK.
3. Achar o tempo de cada uma (o texto depois do `=` é o que aparece na tela):
   ```bash
   .venv/bin/python ferramentas/marcar_palavras.py trabalho/minha-peca/palavras.json trabalho/minha-peca/atras.json "café" "torra=TORRA MÉDIA" "aroma"
   ```
4. Montar:
   ```bash
   .venv/bin/python .claude/skills/palavra-atras/palavra_atras.py trabalho/minha-peca/cortado.mp4 trabalho/minha-peca/recorte trabalho/minha-peca/atras.json entrega/minha-peca-atras.mp4
   ```
   Opções: `--cor "#2E6BFF"` (cor da marca), `--altura 0.3` (cabeça cobre menos da palavra), `--fonte barlow-condensed/BarlowCondensed-Bold.ttf`.

## Como conferir

Tirar quadros no meio de cada palavra e olhar:
```bash
ffmpeg -v error -i entrega/minha-peca-atras.mp4 -vf "fps=1,scale=270:-2,tile=8x1" -frames:v 1 trabalho/minha-peca/folha-atras.jpg
```
- A cabeça precisa passar **na frente** da palavra (se a palavra estiver por cima do rosto, o recorte falhou: refazer o passo 1).
- A palavra tem que dar para ler. Se a cabeça cobrir demais, usar `--altura 0.3`.
- Palavra longa vira duas linhas sozinha.

## Regras

- Uma palavra por ideia, curta. Nunca a frase inteira.
- No máximo uma palavra a cada 2 s; mais que isso cansa.
- Cabelo solto, fundo da mesma cor da roupa ou pouca luz deixam a borda do recorte pior: avisar o aluno.
- **Windows**: o Vision não existe. Alternativas livres para fazer o matte: `rembg` (licença MIT) ou MediaPipe Selfie Segmentation (Apache 2.0). Elas não foram testadas com este script; o matte precisa ser um vídeo preto e branco (branco = pessoa) com o mesmo tamanho e 30 qps, e o `rostos.json` no mesmo formato.
