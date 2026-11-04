---
name: animacoes-em-cima
description: Põe adesivos, bonecos e carimbos (PNG com fundo transparente) entrando por cima do vídeo no tempo da fala, estilo corte de podcast, sem cobrir o rosto. Use quando o aluno disser "põe uns adesivos", "figurinhas no vídeo", "carimbo quando eu falar tal palavra", "animações por cima" ou pedir a aula 15.
---

# Animações em cima (aula 15)

Cada adesivo entra quando a palavra é falada: cresce com uma passadinha leve, gira um pouco, fica respirando e sai. Ganha borda branca de adesivo recortado e sombra macia. O lugar é escolhido longe do rosto.

## Antes de começar

- Uma vez só: `.venv/bin/pip install pillow`.
- Os adesivos são PNG com fundo transparente. Exemplos livres em `assets/adesivos/` (xícara, carimbo "APROVADO", "UAU!"). O aluno pode trazer os dele (gerados por IA ou desenhados) ou pedir ao Claude um SVG simples e converter:
  ```bash
  node ferramentas/svg-para-png.mjs meu-desenho.svg assets/adesivos/meu-adesivo.png
  ```
- O lugar do rosto vem do recorte do Mac (só rostos, rápido). De preferência, o vídeo já passou pelo `/cortar-fala`.

## Passo a passo

1. Achar o rosto:
   ```bash
   bash ferramentas/recorte.sh trabalho/minha-peca/cortado.mp4 trabalho/minha-peca/recorte --so-rostos
   ```
2. Combinar com o aluno a lista "palavra → adesivo" (no máximo um a cada 2–3 s).
3. Achar os tempos:
   ```bash
   .venv/bin/python ferramentas/marcar_palavras.py trabalho/minha-peca/palavras.json trabalho/minha-peca/adesivos.json --campo arquivo "café=assets/adesivos/xicara.png" "aprovado=assets/adesivos/carimbo-aprovado.png"
   ```
   Para fixar o lado, acrescente `"lugar": "esquerda"` (ou `direita`, `cima`, `baixo`) na linha do adesivo.
4. Montar:
   ```bash
   .venv/bin/python .claude/skills/animacoes-em-cima/animacoes_em_cima.py trabalho/minha-peca/cortado.mp4 trabalho/minha-peca/recorte trabalho/minha-peca/adesivos.json entrega/minha-peca-adesivos.mp4
   ```
   Opções: `--tamanho 0.28` (adesivo menor), `--sem-borda` (sem a borda branca).

## Como conferir

```bash
ffmpeg -v error -i entrega/minha-peca-adesivos.mp4 -vf "fps=2,scale=200:-2,tile=8x2" -frames:v 1 trabalho/minha-peca/folha-adesivos.jpg
```
- Nenhum adesivo em cima de olhos ou boca. Se o script avisar "encosta no rosto", diminuir o `--tamanho`.
- Nada na faixa de baixo do 9:16 (legenda e botões) nem no alto (nome do perfil): o script já evita.
- A entrada é suave: sem quique exagerado.

## Regras

- Adesivo só com licença conferida: desenho próprio, gerado pelo aluno ou com licença livre declarada. Nunca logo ou personagem de outra marca.
- Um adesivo por ideia, ligado à palavra falada. Enfeite sem motivo atrapalha.
- No Windows o recorte de rosto não roda: use `"lugar"` em cada adesivo e confira os quadros a olho.
