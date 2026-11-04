---
name: meia-tela
description: Monta o vídeo em meia tela - a pessoa numa janela embaixo e, em cima, um painel por ideia com lista e check entrando no tempo da fala. Use quando o aluno disser "meia tela", "eu embaixo e a lista em cima", "painel com checklist", "vídeo explicando com tópicos" ou pedir a aula 14.
---

# Meia tela (aula 14)

Embaixo, a pessoa numa janela com o rosto inteiro. Em cima, um painel claro com título e itens que ganham um check quando são falados. Um painel por ideia.

## Antes de começar

- Precisa do **Google Chrome** instalado (ele desenha os painéis sem janela) e do **Node 22 ou mais novo** (`node --version`). Não precisa instalar pacote do npm.
- O enquadramento usa o `rostos.json` do recorte do Mac. No Windows, ver a regra no fim.
- De preferência, o vídeo já passou pelo `/cortar-fala` (`cortado.mp4` e `palavras.json`).

## Passo a passo

1. Achar o rosto (rápido, sem matte):
   ```bash
   bash ferramentas/recorte.sh trabalho/minha-peca/cortado.mp4 trabalho/minha-peca/recorte --so-rostos
   ```
2. Ler `palavras.json` e propor os painéis ao aluno: um por ideia, título curto, 2 a 4 itens curtos. Esperar o OK.
3. Achar o tempo de cada item (o tempo em que é falado):
   ```bash
   .venv/bin/python ferramentas/marcar_palavras.py trabalho/minha-peca/palavras.json trabalho/minha-peca/itens.json "grão" "torra" "moagem"
   ```
4. Escrever `trabalho/minha-peca/paineis.json` com esses tempos:
   ```json
   {"paineis": [
     {"etiqueta": "Passo 1", "titulo": "Como escolher o café", "inicio": 0.5, "fim": 8.0,
      "itens": [{"texto": "Grão inteiro", "em": 2.1}, {"texto": "Torra média", "em": 4.0}]}
   ]}
   ```
   O `fim` de um painel deve ser igual ou menor que o `inicio` do próximo (a saída leva 0,3 s antes do `fim`).
5. Montar:
   ```bash
   node .claude/skills/meia-tela/meia_tela.mjs trabalho/minha-peca/cortado.mp4 trabalho/minha-peca/recorte trabalho/minha-peca/paineis.json entrega/minha-peca-meia-tela.mp4
   ```
   Opções: `--cor "#2E6BFF"` (cor da marca nos checks e na etiqueta), `--fundo "#EEF1F6"`.
   O script diz na tela se o rosto ficou inteiro na janela.

## Como conferir

```bash
ffmpeg -v error -i entrega/minha-peca-meia-tela.mp4 -vf "fps=1/2,scale=270:-2,tile=6x1" -frames:v 1 trabalho/minha-peca/folha-meia.jpg
```
- Rosto inteiro na janela (testa, cabelo e queixo), em todos os quadros.
- Cada check entra quando a palavra é falada, não antes.
- Título em no máximo duas linhas; com mais de 4 itens a letra diminui sozinha.

## Regras

- Fundo claro, uma cor de destaque (a da marca). Fontes livres do repositório: Barlow Condensed (título) e Barlow (texto), licença OFL em `assets/fontes/`.
- Texto da tela é resumo do que foi falado, nunca outra coisa.
- O enquadramento é fixo: se a pessoa anda muito de lado, a janela abre mais. Para ficar justo, divida o vídeo em trechos.
- O painel é uma página HTML com `window.seek(t)`: o mesmo tempo dá sempre o mesmo desenho. Para mudar o visual, edite `.claude/skills/meia-tela/pagina.html`.
- **Windows**: sem o recorte do Mac, escreva o `rostos.json` à mão com um só quadro (`{"largura":1080,"altura":1920,"fps":30,"inicio":0,"fim":<duração>,"quadros":[{"t":0,"rosto":{"x":..,"y":..,"w":..,"h":..},"topo_cabeca":..}]}`), medindo o rosto num quadro.
