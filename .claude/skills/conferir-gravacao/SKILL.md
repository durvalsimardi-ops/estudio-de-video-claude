---
name: conferir-gravacao
description: Confere uma gravação antes de editar - luz, volume da voz, ruído e se a cabeça cabe no 9:16 e na meia tela. Use quando o aluno disser "confere minha gravação", "a luz ficou boa?", "o som está bom?", "minha cabeça cortou?", "posso editar esse vídeo?" ou mandar um vídeo bruto novo.
---

# Conferir gravação (aula 8)

Mede o vídeo bruto e diz, em poucas linhas, o que regravar antes de perder tempo editando.

## Antes de começar

- O vídeo está em `originais/` (nunca alterar o original).
- O enquadramento usa o recorte de pessoa do Mac (Vision). Na primeira vez ele se prepara sozinho (uns 30 s). Se faltar o `swift`, rodar `xcode-select --install`.

## Passo a passo

1. Rodar a conferência (troque `minha-peca` pelo nome da peça):
   ```bash
   .venv/bin/python .claude/skills/conferir-gravacao/conferir.py originais/video.mp4 trabalho/minha-peca
   ```
2. Ler o relatório (também salvo em `trabalho/minha-peca/conferencia.txt`) e responder ao aluno só o que importa:
   - **Luz**: rosto entre 90 e 195 de 255 é bom. Abaixo de 60, regravar com luz de frente. Área estourada alta = janela ou lâmpada no quadro.
   - **Som**: o volume final (−14 LUFS) se acerta na edição; o que não tem conserto é **ruído de fundo alto** e **estouro** (distorção). Esses pedem regravar.
   - **Enquadramento**: "cabeça cortada" e "rosto fora da área segura" vêm com os segundos. Em cima do 9:16 fica o nome do perfil; embaixo, a legenda e os botões.
   - **Meia tela**: diz se o rosto cabe inteiro na janela de baixo da skill `meia-tela`.
3. Se tiver problema, sugerir a correção concreta (luz, distância do celular, lugar mais quieto). Se estiver bom, seguir para `/cortar-fala`.

## Como conferir

Abrir 3 quadros (começo, meio e fim) para confirmar o que o relatório disse:
```bash
ffmpeg -v error -i originais/video.mp4 -vf "fps=1/5,scale=270:-2,tile=6x1" -frames:v 1 trabalho/minha-peca/folha.jpg
```

## Regras

- Relatório curto, em texto. Não editar nada nesta etapa.
- Números com explicação simples ("−51 dB: aceitável"), nunca só o número.
- Fora do Mac, só luz e som são medidos; o enquadramento se confere olhando a folha de quadros.
