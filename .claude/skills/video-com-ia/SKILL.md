---
name: video-com-ia
description: Regras para gerar vídeo ou imagem com IA (Higgsfield, Seedance, Kling, Katana e outros). Use quando o aluno disser "gera um vídeo com IA", "anima essa foto", "quanto custa gerar", "faz o produto se mexer".
---

# Vídeo gerado por IA (aula 24)

## Quando vale

- O produto ou a cena precisa de **movimento real** que o código não faz (pessoa andando, líquido, câmera passando pelo lugar).
- Para título, lista, número, legenda e logo, o vídeo por código (`/motion-hyperframes`) é mais barato, exato e repetível.

## Passo a passo

1. Perguntar o que o aluno quer ver se mexendo, em uma frase, e qual foto real usar de base (produto real dá resultado mais fiel).
2. **Dizer o preço antes:** consultar na ferramenta conectada quanto custa aquela duração e modelo, e mostrar ao aluno: "6 s no modelo X custam N créditos. Posso gerar?". Preços mudam: sempre consultar na hora, nunca de memória.
3. Gerar só depois do OK. Uma tentativa por vez.
4. Conferir o resultado quadro a quadro: mãos, texto, logo e o produto certo (cor, formato, número de peças).
5. Salvar em `trabalho/<peca>/ia/` com o prompt usado ao lado (`prompt.txt`).

## Regras

- Gastar crédito só com OK, sempre.
- Não usar rosto, voz ou marca de outra pessoa sem autorização.
- Imagem gerada por IA pode errar texto e logo: logo e texto entram depois, por código, por cima.
- Vídeo de propaganda política tem regras próprias sobre IA: conferir a lei eleitoral vigente antes.
