---
name: palavra-acima
description: Faz a palavra subir de trás da cabeça e parar acima dela, em letra de vidro, acompanhando a cabeça sem tremer. Use quando o aluno disser "palavra saindo da cabeça", "texto em cima da minha cabeça", "letra de vidro", "palavra que sobe atrás de mim" ou pedir a aula 12.
---

# Palavra acima da cabeça (aula 12)

A palavra nasce escondida atrás da cabeça, sobe e para logo acima dela, com folga. Se a pessoa se mexe, a palavra acompanha, suave. Letra de vidro: o fundo aparece desfocado e claro dentro da letra, com um brilho fino na borda e sombra macia.

## Antes de começar

- Só no Mac (recorte com o Vision da Apple). Precisa do `swift` (`xcode-select --install`).
- Uma vez só: `.venv/bin/pip install pillow`.
- Funciona melhor com espaço livre acima da cabeça (celular um pouco mais longe, cabeça no meio da tela). Rode `/conferir-gravacao` se tiver dúvida.
- De preferência, o vídeo já passou pelo `/cortar-fala` (`cortado.mp4` e `palavras.json`).

## Passo a passo

1. Recortar a pessoa:
   ```bash
   bash ferramentas/recorte.sh trabalho/minha-peca/cortado.mp4 trabalho/minha-peca/recorte
   ```
2. Escolher as palavras com o aluno (uma por ideia). Pode ter uma linha pequena de apoio acima, com as palavras que vêm antes na fala.
3. Achar os tempos:
   ```bash
   .venv/bin/python ferramentas/marcar_palavras.py trabalho/minha-peca/palavras.json trabalho/minha-peca/acima.json "aurora=Aurora" "torra=torra média"
   ```
   Depois, se quiser a linha de apoio, abrir `acima.json` e acrescentar `"apoio": "o café da"` na cena.
4. Montar:
   ```bash
   .venv/bin/python .claude/skills/palavra-acima/palavra_acima.py trabalho/minha-peca/cortado.mp4 trabalho/minha-peca/recorte trabalho/minha-peca/acima.json entrega/minha-peca-acima.mp4
   ```
   Opções: `--folga 60` (mais espaço até a cabeça), `--fonte barlow-condensed/BarlowCondensed-Bold.ttf` (letra reta em vez da itálica).

## Como conferir

- Três quadros seguidos com a palavra parada: ela não pode pular de um para o outro.
  ```bash
  ffmpeg -v error -i entrega/minha-peca-acima.mp4 -vf "select='between(n\,90\,92)',crop=iw:ih/3:0:ih/6,tile=1x3" -frames:v 1 trabalho/minha-peca/tres.jpg
  ```
- A palavra não encosta no cabelo e não sai pelo alto da tela.
- Na subida, ela aparece saindo de trás da cabeça (a cabeça passa na frente).

## Regras

- Letra de vidro discreta: nada de contorno grosso, cor berrante ou brilho exagerado.
- A palavra fica sempre acima da cabeça, nunca em cima do rosto.
- Se não houver espaço acima da cabeça, a letra diminui sozinha; se ficar pequena demais, usar `/palavra-atras` ou regravar com mais espaço.
- **Windows**: sem Vision. Alternativas livres para o matte: `rembg` (MIT) ou MediaPipe (Apache 2.0), não testadas com este script.
