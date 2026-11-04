---
name: instalar-hyperframes
description: Instala e confere o HyperFrames, o motor que transforma HTML em vídeo, e as skills dele no Claude. Use quando o aluno disser "instala o HyperFrames", "o render não funciona", "hyperframes não encontrado" ou antes da primeira animação por código.
---

# Instalar o HyperFrames (aula 21)

O HyperFrames (da HeyGen, código aberto, licença Apache 2.0, https://github.com/heygen-com/hyperframes) transforma uma página HTML em vídeo MP4, quadro a quadro. É o motor da maior parte das edições do curso: legenda, títulos, painéis, cartões por cima do vídeo e animações do zero.

## Passo a passo

1. **Node.js 22 ou mais novo.** Conferir: `node --version`. Se faltar ou for antigo: `/preparar-estudio` (no Mac, `brew install node`).
2. **Conferir o computador:**
   ```bash
   npx hyperframes doctor
   ```
   O `npx` baixa o HyperFrames na primeira vez (o aluno confirma com "y"). Os itens que importam: Node, FFmpeg, FFprobe e Chrome com ✓. whisper-cpp, Kokoro e MusicGen aparecem como opcionais: não precisa instalar (o estúdio transcreve com o `ferramentas/transcrever.py` e a voz vem do ElevenLabs).
3. **Chrome do render:** se o doctor marcar o Chrome com ✗, rodar `npx hyperframes browser` e seguir o que ele pedir.
4. **As skills do HyperFrames no Claude** (ensinam o Claude a escrever composições válidas, conferir e renderizar). Mostrar ao aluno e rodar com o OK dele:
   ```bash
   npx hyperframes skills update
   ```
   Depois, fechar e abrir a sessão: aparecem skills como `/hyperframes`. Alternativa pelo terminal do Claude Code: `claude plugin marketplace add heygen-com/hyperframes` e `claude plugin install hyperframes@hyperframes`.
5. **Teste de 5 s**, numa pasta de trabalho:
   ```bash
   cd trabalho && npx hyperframes init teste-hyperframes && cd teste-hyperframes
   npx hyperframes render -o ../../entrega/teste-hyperframes.mp4
   ```
   Abrir o MP4. Se saiu, está instalado.
6. Para ver e ajustar ao vivo antes de renderizar: `npx hyperframes preview` (abre o estúdio no navegador).

## Se der erro

- `command not found: npx`: falta o Node.js.
- Erro de versão do Node: atualizar para 22 ou mais novo.
- Render travado ou lento: fechar outros programas pesados; `npx hyperframes doctor` mostra memória e disco livres.
- Versão nova disponível: `npx hyperframes upgrade` (só com OK do aluno; depois, `npx hyperframes skills update` de novo para as skills baterem com a versão).

## Versão e privacidade

- Os exemplos do curso foram testados na versão 0.8.212. Se uma versão nova quebrar algo: `npx hyperframes@0.8.212 render ...`.
- O HyperFrames manda estatística anônima de uso. Para desligar: `npx hyperframes telemetry disable`.

## Regras

- O `publish` do HyperFrames sobe o projeto para a internet: só com pedido do aluno.
- Conferir os termos atuais no repositório antes de usar em trabalho de cliente (hoje: Apache 2.0, uso comercial permitido).
