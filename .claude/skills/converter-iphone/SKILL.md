---
name: converter-iphone
description: Converte vídeo HDR do iPhone (HLG ou Dolby Vision) para cor padrão (SDR, BT.709) sem lavar as cores, mantendo resolução e quadros por segundo, e recorta em 9:16 se pedir. Usar quando o aluno disser "converte o vídeo do iPhone", "o vídeo ficou lavado", "as cores ficaram estranhas", "tira o HDR", "deixa em 9:16" ou trouxer um .MOV do iPhone para editar.
---

# Converter vídeo do iPhone (aula 4)

O iPhone grava em HDR. Fora do iPhone (editor, Instagram, WhatsApp) esse vídeo costuma aparecer lavado ou estourado. Esta skill converte para a cor padrão antes de qualquer edição.

## Antes de começar

- O vídeo fica em `originais/` e nunca é alterado.
- Escolha um nome para a peça (ex.: `cafe-aurora-lancamento`). Tudo vai para `trabalho/<peça>/`.

## Passo a passo

1. Converter (o padrão mantém o tamanho original):
   ```
   .venv/bin/python .claude/skills/converter-iphone/converter.py originais/IMG_0001.MOV trabalho/<peça>/
   ```
   Para recortar o centro em 9:16 (1080x1920), acrescente `--9x16`.
2. Se a cor não agradar, teste o conversor da Apple (só no Mac; costuma sair um pouco mais escuro):
   ```
   .venv/bin/python .claude/skills/converter-iphone/converter.py originais/IMG_0001.MOV trabalho/<peça>/apple --metodo apple
   ```
3. Resultado: `trabalho/<peça>/IMG_0001-sdr.mp4` e um quadro do meio em `IMG_0001-sdr.jpg`.

## Como conferir

- O script lê o arquivo pronto e precisa terminar com `OK: BT.709 confirmado`. Se aparecer `ATENÇÃO`, não siga.
- Abra o `.jpg` (Read) e olhe: pele com cor natural, céu e luzes sem estourar, preto que é preto. Lavado = cinza e sem contraste.
- Se avisar que o recorte 9:16 foi ampliado, diga ao aluno que o vídeo perde nitidez (o ideal é gravar em pé).

## Regras

- Converter sempre antes de cortar, legendar ou editar. Vídeo que não é HDR só é padronizado (H.264, qps constante).
- O arquivo novo sai sem localização e sem os dados do celular.
- Windows: use `.venv\Scripts\python` no lugar de `.venv/bin/python`. O método `lut` funciona igual; o `--metodo apple` só existe no Mac.
