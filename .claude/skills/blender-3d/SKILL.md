---
name: blender-3d
description: Objeto 3D girando, feito por código no Blender, sem abrir o programa. Use quando o aluno disser "faz uma xícara 3D girando", "quero um produto 3D", "objeto girando em fundo azul", "troca a xícara por uma garrafa/caneca/vaso" ou "renderiza o 3D". Aula 23.
---

# Objeto 3D girando com Blender (aula 23)

Para que serve: gerar um vídeo de objeto 3D simples girando (vitrine de produto, vinheta) só com um script Python. O exemplo `xicara.py` cria xícara (corpo torneado + alça + pires + café), luz de estúdio e fundo azul `#2E6BFF`; 4 s, 30 qps, 1080x1920, EEVEE.

## Antes de começar

- Blender instalado (grátis, licença GPL; o que você renderiza é seu, sem restrição): https://www.blender.org/about/license/ . No Mac: `brew install --cask blender`. Conferir: `blender --version` (testado no 5.2).
- ffmpeg instalado (junta os quadros no mp4).
- Render pesado demora: 4 s levam ~1,5 min num Mac com chip Apple; `--rapido` leva ~30 s.

## Passo a passo

1. Prévia rápida (menos amostras):
   ```bash
   blender -b -P .claude/skills/blender-3d/xicara.py -- trabalho/xicara-3d --rapido
   ```
2. Olhar os quadros (abaixo). Ajustar e repetir.
3. Versão final: o mesmo comando sem `--rapido`. Outra duração: `--segundos 6`.
4. Sai `trabalho/xicara-3d/xicara.mp4` (quadros em `trabalho/xicara-3d/quadros/`). Conferido, copiar para `entrega/`.

## Pedir outro objeto girando

Copie o script para a pasta da peça e edite a cópia (o original fica de modelo):
```bash
cp .claude/skills/blender-3d/xicara.py trabalho/garrafa-3d/garrafa.py
blender -b -P trabalho/garrafa-3d/garrafa.py -- trabalho/garrafa-3d --rapido
```
- **Objeto redondo** (copo, garrafa, vaso, caneca, pote): troque só a lista de pontos do `torneado(...)`. Cada ponto é (raio, altura), de baixo para cima por fora e de cima para baixo por dentro. Desenhe o perfil num papel e dite os números.
- **Alça, asa, cabo:** a curva `alca` (4 pontos). Sem alça: apague o bloco.
- **Objeto não redondo** (caixa, celular, placa): `bpy.ops.mesh.primitive_cube_add(...)` com escala e o modificador de quinas `BEVEL`.
- **Cor:** `LOUCA`, `CAFE`, `FAIXA` e `AZUL_FUNDO` no começo (em código de cor, como no site).
- **Câmera mais perto/longe:** `cam.data.lens` (maior = mais perto).
- **Velocidade:** o giro dá 1 volta no tempo do vídeo. Duas voltas: troque `math.tau` por `2 * math.tau` no driver.

Peça ao Claude: "troca a xícara por uma garrafa de 1 litro, vidro verde, girando 6 s".

## Como conferir

```bash
for t in 0 1 2 3; do ffmpeg -v error -y -ss $t -i trabalho/xicara-3d/xicara.mp4 -frames:v 1 trabalho/xicara-3d/q-$t.png; done
```
- O objeto aparece inteiro, reconhecível, e muda de posição de um quadro para o outro (a alça anda).
- Fundo azul liso, sem faixa cortando o objeto, nada estourado de branco.
- `ffprobe` mostra 1080x1920, 30 qps e a duração pedida.

## Regras

- Sempre `blender -b` (sem abrir janela) e pasta de saída como argumento.
- Só modelo feito por código ou arquivo 3D com licença livre declarada (ex.: CC0), com a licença na pasta da peça.
- Quadros e vídeo em `trabalho/<peça>/`; só o final vai para `entrega/`.
