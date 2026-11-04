---
name: remotion-ou-hyperframes
description: Ajuda a escolher entre Remotion e HyperFrames para motion por código e mostra a mesma abertura nos dois. Use quando o aluno perguntar "Remotion ou HyperFrames?", "qual eu uso?", "faz em Remotion", "o Remotion é pago?" ou "quero ver a abertura em React". Aula 22.
---

# Remotion ou HyperFrames (aula 22)

Os dois fazem a mesma coisa: código que vira vídeo, quadro a quadro. A abertura do Café Aurora existe nos dois:
- HyperFrames: `.claude/skills/motion-hyperframes/exemplo/index.html`
- Remotion: `exemplo-remotion/` (nesta pasta)

## Quando usar cada um

| | HyperFrames | Remotion |
|---|---|---|
| Escreve em | HTML, CSS e JavaScript (uma página) | React (componentes em TypeScript) |
| Instalar | nada: `npx hyperframes` | `npm install` em cada projeto (~250 pacotes) |
| Bom para | abertura, vinheta, texto animado, peça rápida | projeto grande, muitas versões do mesmo modelo, quem já sabe React |
| Licença | Apache-2.0, livre para qualquer uso | grátis só para alguns casos (abaixo) |

Regra do curso: **comece pelo HyperFrames**. Use Remotion se o aluno já sabe React, se o cliente exige, ou se o projeto já é em Remotion.

## Licença do Remotion (confira antes de usar em trabalho pago)

O Remotion não é código aberto. Pelo texto da licença conferido em 04/11/2026, é **grátis** para: pessoa física, empresa com fins lucrativos de **até 3 funcionários**, entidade sem fins lucrativos, e para testar antes de usar comercialmente. **Empresa com 4 funcionários ou mais precisa comprar a Company License.**
- Termos: https://www.remotion.dev/docs/license (texto: https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)
- Compra: https://www.remotion.pro/license
- As regras podem mudar: confira os termos atuais nesses links antes de entregar para cliente.

HyperFrames: Apache-2.0, https://github.com/heygen-com/hyperframes/blob/main/LICENSE

## Passo a passo (Remotion)

1. Copiar o exemplo, pôr as fontes e instalar (precisa de internet na primeira vez, ~1 min):
   ```bash
   bash .claude/skills/remotion-ou-hyperframes/preparar.sh trabalho/abertura-remotion
   ```
2. Editar `trabalho/abertura-remotion/src/Abertura.tsx` (texto, cores e tempos no começo do arquivo). Duração e tamanho ficam em `src/Root.tsx` (`durationInFrames` = segundos x 30).
3. Ver com linha do tempo: `cd trabalho/abertura-remotion && npm run studio`
4. Gravar: `cd trabalho/abertura-remotion && npm run render` (sai em `render/abertura.mp4`).
5. Conferido, copiar para `entrega/`.

Na primeira gravação o Remotion baixa um Chrome próprio. Se der "Timed out ... connect to the browser", rode de novo: na segunda vez abre.

## Como conferir

- Mesmos quadros do HyperFrames (0, 1, 2, 3 e 4,8 s): os dois vídeos devem ficar quase iguais.
- Palavras do título com espaço entre elas, letra Fraunces (com serifa), nada cortado.
- `ffprobe` com 1080x1920, 30 qps, 5 s.

## Regras

- O `node_modules` fica só em `trabalho/<peça>/`, nunca dentro de `.claude/skills/`.
- Tudo pelo número do quadro (`useCurrentFrame`): nada de `setTimeout`, `Math.random()` ou animação CSS solta.
- Fontes por `loadFont` com arquivo local em `public/fontes/` e licença junto.
