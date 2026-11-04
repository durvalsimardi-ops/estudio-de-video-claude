---
name: preparar-estudio
description: Prepara o estúdio no primeiro uso. Use quando o aluno disser "acabei de instalar", "prepara o estúdio", "o que falta instalar?", "confere se está tudo pronto" ou "me ajuda a preencher o CLAUDE.md".
---

# Preparar o estúdio (aulas 1, 2 e 3)

Deixa o computador pronto para as aulas e o `CLAUDE.md` com as regras do aluno.

## Passo a passo

1. Conferir o que já existe, sem instalar nada:
   ```bash
   bash ferramentas/instalar.sh
   ```
2. Mostrar ao aluno a lista do que falta e o que cada item faz:
   - **ffmpeg**: corta, junta e converte vídeo e áudio.
   - **yt-dlp**: baixa vídeos de referência (aula 18).
   - **Node.js 22 ou mais**: roda o HyperFrames, que faz a maior parte da edição na tela (legenda, títulos, painéis, animação). Depois de instalar, `/instalar-hyperframes`.
   - **.venv**: um Python só deste projeto, com o Whisper, que transcreve a fala.
   - **swift** (Mac): recorta a pessoa do fundo (aulas 8, 11 e 12). Vem com `xcode-select --install`.
   - **Blender**: opcional, só para a aula 23.
3. Só depois do OK do aluno, instalar:
   ```bash
   bash ferramentas/instalar.sh --instalar
   ```
   O script pergunta de novo antes de instalar. No Mac ele usa o Homebrew; se o Homebrew não existir, mostrar o comando oficial de https://brew.sh e deixar o aluno rodar.
4. Rodar a conferência de novo até aparecer "Tudo pronto."
5. Abrir o `CLAUDE.md` e preencher com o aluno: nome, o que ele grava e duas regras dele em "Minhas regras extras".

## Regras

- Nada é instalado sem o aluno ver a lista antes.
- Senha do computador quem digita é o aluno, no Terminal. Nunca pedir senha no chat.
- No Windows: instalar ffmpeg, yt-dlp, Node.js e Python pelo `winget` e criar o `.venv` com `faster-whisper`. O recorte de pessoa (Vision) só existe no Mac.
