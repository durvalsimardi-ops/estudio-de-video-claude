---
name: voz-elevenlabs
description: Narração, efeitos e a voz própria com o ElevenLabs ligado ao Claude. Use quando o aluno disser "narra esse roteiro", "me mostra três vozes", "usa a minha voz", "clona minha voz", "faz um som de clique" ou "a pronúncia saiu errada".
---

# Voz e efeitos com ElevenLabs (aulas 25 e 26)

## Antes de começar

- O ElevenLabs precisa estar conectado ao Claude: pelo conector do app do Claude, se aparecer na lista de conectores, ou pelo servidor MCP oficial do ElevenLabs (https://github.com/elevenlabs/elevenlabs-mcp). Quem cria a conta e cola a chave é o aluno, nas configurações, nunca no chat.
- Toda geração gasta crédito do plano do aluno. Dizer quanto antes, quando a ferramenta informar.

## Narração (aula 25)

1. Pegar o roteiro em frases curtas. Uma ideia por frase.
2. Se o aluno ainda não escolheu voz: listar vozes em português e gerar **a mesma frase curta em 3 vozes** para ele ouvir e escolher.
3. Gerar o roteiro inteiro com a voz escolhida, salvar em `trabalho/<peca>/voz.mp3`.
4. Transcrever o áudio gerado e conferir a pronúncia de nomes, números e marcas:
   ```bash
   .venv/bin/python ferramentas/transcrever.py trabalho/<peca>/voz.mp3 trabalho/<peca>/voz-palavras.json
   ```
5. Palavra pronunciada errado: reescrever do jeito que se fala (ex.: "Aifone" em vez de "iPhone") e gerar só aquela frase de novo.

## A sua própria voz (aula 26)

1. O aluno grava 1 a 3 minutos lendo naturalmente: Gravador do iPhone ou QuickTime, lugar silencioso, celular a um palmo da boca.
2. Ele cria a voz no site ou pela ferramenta conectada (clonagem de voz depende do plano; conferir na conta).
3. Salvar o ID da voz no `CLAUDE.md`, em "Minha voz".
4. Daí em diante, "narra com a minha voz" usa esse ID.

## Efeitos

- Efeito gerado por texto: pedir em inglês, um som por pedido, curto (ex.: "soft UI click", "short whoosh"). Para não gastar, o kit grátis do projeto está em `assets/sons/`.

## Regras

- Só a voz do próprio aluno, ou de quem autorizou por escrito. Voz de famoso, nunca.
- Gastar crédito só com OK.
- Depois de mixar, volume final em −14 LUFS (`/som`).
