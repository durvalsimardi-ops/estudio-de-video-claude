---
name: motion-hyperframes
description: Motion por código com HyperFrames (HTML que vira vídeo), do zero ou por cima de um vídeo gravado. Use quando o aluno disser "faz uma abertura animada", "quero um motion", "título entrando palavra por palavra", "põe título, legenda e cartões no meu vídeo", "anima por cima do vídeo que eu gravei", "troca o texto/cor/duração" ou "renderiza o motion". Aulas 17, 21 e 28.
---

# Motion por código com HyperFrames (aulas 17, 21 e 28)

Para que serve: escrever uma página HTML que o HyperFrames grava como MP4, quadro a quadro. Dois exemplos prontos, comentados:

| Exemplo | Quando usar |
|---|---|
| `exemplo/index.html` (aulas 21 e 28) | **Animação do zero**: abertura, vinheta, cartela, texto animado. Não tem vídeo gravado. Abertura de 5 s do Café Aurora. |
| `exemplo-sobre-video/` (aula 17) | **Por cima do vídeo gravado**: a pessoa falando no fundo e, no tempo da fala, título, legenda palavra a palavra e cartões. Usa o `palavras.json` do `ferramentas/transcrever.py`. |

Na dúvida: tem gravação da pessoa? Use o segundo. Não tem? Use o primeiro.

## Antes de começar

- Node.js 22 ou mais novo e ffmpeg (`bash ferramentas/instalar.sh` confere). Para o exemplo por cima do vídeo, também o `.venv` do estúdio (transcrição).
- HyperFrames: não precisa instalar, o `npx hyperframes` baixa sozinho na primeira vez (inclui o Chrome que ele usa para gravar). Testado com a versão 0.8.212. Se uma versão nova quebrar algo, use `npx hyperframes@0.8.212`.
- Licença: HyperFrames é código aberto, **Apache-2.0** (pode usar em trabalho comercial, de graça): https://github.com/heygen-com/hyperframes/blob/main/LICENSE
- O HyperFrames manda estatística anônima de uso. Para desligar: `npx hyperframes telemetry disable`.
- Fontes: Fraunces e Inter (OFL), em `assets/fontes/`, com o `OFL.txt` de cada uma.

## Passo a passo · animação do zero

1. Criar a peça (troque o nome):
   ```bash
   bash .claude/skills/motion-hyperframes/nova-peca.sh trabalho/abertura-aurora
   ```
2. Editar só `trabalho/abertura-aurora/index.html`:
   - **Texto:** constantes `TITULO` e `APOIO` no começo do `<script>`.
   - **Cor:** variáveis no `:root`.
   - **Duração:** `data-duration` no `#root` e a constante `DURACAO`; depois espalhe os tempos da função `desenhar(t)` (cada `prog(t, início, fim)` está em segundos).
   - **Fonte:** copie o `.woff2` e a licença para `fontes/` e troque o `@font-face`. Só fonte livre (OFL, Apache) ou comprada.
   - **Logo da marca do aluno:** cole o conteúdo de `marcas/<marca>/logo.svg` dentro do `#logo`.
3. Seguir em "Ver, conferir e gravar".

## Passo a passo · por cima do vídeo gravado

1. Preparar (vídeo, pasta da peça, início e duração do trecho em segundos):
   ```bash
   bash .claude/skills/motion-hyperframes/preparar-video.sh originais/fala.mov trabalho/dica-cafe 0 12
   ```
   Ele converte o trecho para 30 qps e 1080x1920 (assim o HyperFrames pega o quadro certo), transcreve sem custo e copia página, `config.js` e fontes. O original não muda.
2. Ler `trabalho/dica-cafe/palavras.json` e propor ao aluno: título, palavras em destaque e cartões (cada cartão entra quando uma palavra é falada). Com o OK, escrever em `trabalho/dica-cafe/config.js`.
3. Cores e tamanhos ficam no `index.html` da peça. A legenda fica em `top: 1330px`, fora da faixa de baixo do 9:16.
4. Seguir em "Ver, conferir e gravar" (o vídeo final já sai com a voz).

## Ver, conferir e gravar

```bash
npx hyperframes preview trabalho/<peça>     # abre o Studio com linha do tempo
npx hyperframes check trabalho/<peça>       # texto escondido, contraste, tempo de leitura
npx hyperframes render trabalho/<peça> -o trabalho/<peça>/render/final.mp4
```
Conferido, copiar para `entrega/`.

## Como conferir

- Tirar quadros e olhar um por um:
  ```bash
  for t in 0 1 2 3 4.8; do ffmpeg -v error -y -ss $t -i trabalho/<peça>/render/final.mp4 -frames:v 1 trabalho/<peça>/render/q-$t.png; done
  ```
- Texto legível, nada cortado nas bordas, nada importante nos 300 px de baixo. Letra da marca (Fraunces tem serifa; letra "de sistema" = fonte não carregou, confira `fontes/`).
- Por cima do vídeo: a palavra azul da legenda é a que está sendo falada; cartão entra junto com a palavra; rosto da pessoa não fica coberto; tem som.
- `ffprobe` com 1080x1920, 30 qps e a duração pedida.

## Regras

- Tudo dirigido pelo tempo: a função `desenhar(t)` decide cada quadro. Proibido `setTimeout`, animação CSS solta, `Date.now()` e `Math.random()`.
- Fontes carregadas antes do primeiro quadro (os exemplos esperam `document.fonts`). Não use fonte de site externo.
- Mantenha `data-no-timeline` no `#root`: os exemplos não usam GSAP, e sem esse aviso o render espera 45 s à toa.
- Texto com no mínimo 34 px em 1080 de largura; texto sobre vídeo sempre com faixa atrás. Último texto parado pelo menos 2 s.
- Vídeo de fundo sempre convertido para 30 qps pelo `preparar-video.sh`, nunca o arquivo de `originais/` direto.
- Não use `npx hyperframes publish`, `cloud` ou `lambda` sem o OK do aluno: enviam o projeto para a internet ou gastam crédito.
- Arquivos de trabalho em `trabalho/<peça>/`, final em `entrega/`.
