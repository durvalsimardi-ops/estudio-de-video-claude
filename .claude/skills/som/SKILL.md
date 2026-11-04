---
name: som
description: Faz a mixagem final do vídeo - trata a voz, coloca efeitos sonoros (clique, pop, whoosh, brilho, impacto, subida) nos tempos certos, trilha baixa que abaixa sozinha sob a fala, e master em -14 LUFS com pico até -1 dBTP. Usar quando o aluno disser "arruma o som", "melhora o áudio", "põe efeito sonoro", "põe uma música de fundo", "o volume está baixo", "deixa no volume do Instagram" ou "mixa o vídeo".
---

# Som e mixagem (aula 16)

Duas partes: o kit de efeitos do projeto (feito por código, uso livre) e o script que mistura tudo e entrega no volume certo para redes sociais.

## Antes de começar

- O kit já está em `assets/sons/` (clique, pop, whoosh, brilho, impacto, subida) com `kit.json`. Se faltar algum arquivo, gere de novo (sai sempre igual):
  ```
  .venv/bin/python .claude/skills/som/gerar_kit.py
  ```
- Trilha: só música com licença conferida (do próprio aluno, comprada, ou de biblioteca que permite uso comercial). Pergunte a origem antes de usar. Se precisar comprar ou gastar crédito para conseguir uma, peça o OK do aluno antes.

## Passo a passo

1. Efeitos: o `/transicoes --sem-som` já gera `eventos.json`. Para outros efeitos, escreva um arquivo assim em `trabalho/<peça>/som/efeitos.json`:
   ```
   [{"t": 1.20, "som": "pop", "db": -6}, {"t": 9.80, "som": "subida", "db": -10}]
   ```
   `t` é o segundo do evento; `db` é o volume em relação à voz (−6 = 6 dB abaixo). O "ponto" de cada som cai em `t` (no whoosh é o meio; na subida é o fim, então ela termina na virada).
2. Mixar:
   ```
   .venv/bin/python .claude/skills/som/mixar.py trabalho/<peça>/transicoes/transicoes.mp4 trabalho/<peça>/som --eventos trabalho/<peça>/transicoes/eventos.json --eventos trabalho/<peça>/som/efeitos.json --trilha trabalho/<peça>/trilha.mp3
   ```
   Sem trilha, é só não passar `--trilha`. Trilha mais baixa: `--trilha-db -18`. Voz que já veio tratada: `--sem-tratar-voz`.
3. Saem em `trabalho/<peça>/som/`: `mixado.mp4` (imagem igual, som novo), `mix.wav` e `relatorio-som.md`.
4. Com tudo conferido e aprovado pelo aluno, copie para `entrega/<peça>.mp4`.

## Como conferir

- O `relatorio-som.md` traz a medida final do arquivo já em AAC. Precisa dar −14 LUFS (±1) e pico ≤ −1 dBTP, com "OK".
- Confira de novo quando quiser: `ffmpeg -i trabalho/<peça>/som/mixado.mp4 -af ebur128=peak=true -f null -` (veja `I:` e `Peak:` no fim).
- Peça para o aluno ouvir no celular: a voz tem que ficar na frente; a trilha nunca disputa com a fala.

## Regras

- Voz: passa-alta em 80 Hz, menos "caixa" em 250 Hz, presença em 3,5 kHz, de-esser e compressor leve. Nada de efeito na voz que o aluno não pediu.
- Efeito é tempero: poucos, nos momentos certos, sempre abaixo da voz.
- Não publicar, enviar nem gastar crédito sem o OK do aluno.
- Windows: `.venv\Scripts\python` no lugar de `.venv/bin/python`.
