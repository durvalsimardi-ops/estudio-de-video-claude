---
name: cortar-fala
description: Corta o vídeo de pessoa falando pela fala - tira silêncios, vícios (ahn, hã, hum) e takes repetidos, sempre entre palavras, e gera a transcrição no tempo do vídeo cortado. Usar quando o aluno disser "corta meu vídeo", "tira os silêncios", "tira os ahn", "deixa mais dinâmico", "tira as partes que eu errei" ou "faz o corte bruto".
---

# Cortar pela fala (aula 9)

Corte bruto automático: o vídeo fica só com a fala boa, sem pausas longas, sem "ahn" e sem o take que o aluno errou e repetiu.

## Antes de começar

- O vídeo já precisa estar em SDR. Se veio do iPhone, rode antes `/converter-iphone`.
- Pergunte se há nomes ou marcas na fala (ex.: "Café Aurora") e passe em `--nomes`: a transcrição acerta mais.

## Passo a passo

1. Cortar:
   ```
   .venv/bin/python .claude/skills/cortar-fala/cortar.py trabalho/<peça>/IMG_0001-sdr.mp4 trabalho/<peça>/corte --nomes "Café Aurora"
   ```
2. Saem em `trabalho/<peça>/corte/`:
   - `cortado.mp4`: o vídeo cortado (mesmo tamanho e qps);
   - `palavras.json`: cada palavra com o tempo no vídeo cortado (a legenda e as transições usam este);
   - `relatorio.md`: o que ficou e o que saiu, com o motivo;
   - `corte.json` e `palavras-original.json`: dados do corte e a transcrição do vídeo inteiro.
3. Ajustes, se o aluno pedir:
   - ritmo mais solto: `--pausa 0.5`; mais corrido: `--pausa 0.25`;
   - manter os "ahn": `--manter-vicios`; manter repetições de propósito: `--manter-repeticoes`;
   - rodar de novo é rápido: a transcrição é reaproveitada (use `--retranscrever` se trocou o vídeo).

## Como conferir

- Leia o `relatorio.md` e mostre ao aluno, em poucas linhas, o que saiu.
- Transcreva o `cortado.mp4` (`.venv/bin/python ferramentas/transcrever.py trabalho/<peça>/corte/cortado.mp4 trabalho/<peça>/corte/conferencia.json`) e confira se a fala está inteira, principalmente a última palavra.
- Peça para o aluno ouvir as emendas. O Whisper às vezes não escreve um "ahn": se sobrar algum, pergunte o segundo e corte de novo com `--pausa` menor.

## Regras

- Corta sempre entre palavras, nunca no meio. O ponto exato é o silêncio medido no áudio.
- "Né", "tipo" e "então" ficam: mudam o sentido. "Um" (artigo) e "há" (verbo) nunca são tratados como vício.
- Take repetido: fica só a última vez que a frase foi dita.
- Nunca mudar o sentido do que a pessoa falou. Na dúvida, manter e perguntar.
- Windows: `.venv\Scripts\python` no lugar de `.venv/bin/python`.
