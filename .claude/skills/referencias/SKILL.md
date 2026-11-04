---
name: referencias
description: Guardar e estudar vídeos de referência. Use quando o aluno mandar um link de vídeo (YouTube, TikTok, X, Vimeo; Instagram só com o login dele e se ele pedir) e disser "guarda essa referência", "faz a ficha desse vídeo", "estuda essa edição", quando pedir "me traz as fichas de meia tela", "quais referências eu tenho de abertura", ou quando pedir "aplica a linguagem da ficha X no meu vídeo" e "transforma este vídeo meu em referência".
---

# Referências

Aulas 18, 19 e 20. Um link vira uma ficha: quadros, cortes medidos, fala e o que copiar. Depois você busca pelas tags e aplica a linguagem no seu vídeo.

## Antes de começar

- Ferramentas instaladas: `bash ferramentas/instalar.sh` (precisa de ffmpeg, yt-dlp e `.venv`).
- Onde fica cada coisa:
  - `referencias/fichas/<nome>.md`: as fichas (vão para o git).
  - `referencias/INDICE.md`: a lista por tag, refeita sozinha.
  - `referencias/videos/<pasta>/`: o vídeo baixado, a prancha e as medidas. Fica fora do git.
- Modelo da ficha: `referencias/fichas/_modelo.md`. Exemplos prontos: `meia-tela-limpa.md` e `abertura-calma.md`.

## 1. Guardar um link (aula 18)

```bash
.venv/bin/python .claude/skills/referencias/scripts/baixar.py "<link>" --tag <assunto> --nota "<por que o aluno guardou>"
```

- Tags em minúsculas, com hífen: `meia-tela`, `abertura`, `legenda`, `transicao`, `falado`, `motion`. Pode repetir `--tag`.
- Fala em outro idioma: `--idioma en` (ou `es`...).
- Instagram pede login. Só use `--cookies-navegador chrome` se o aluno pedir, com a conta dele. Nunca peça senha.
- Vídeo do próprio aluno que deu certo (referência própria): `--arquivo originais/<video>.mp4 --tag <assunto>`.
- O script mostra a pasta, a prancha e a ficha criada.

O que o script faz sozinho: baixa (até 1080p), guarda link, autor, data e licença, tira a prancha de 24 quadros com o tempo, a folha com um quadro por plano, mede os cortes pela detecção de cena do ffmpeg, mede os ataques de som e transcreve a fala com `ferramentas/transcrever.py`.

## 2. Completar a ficha (aula 19)

1. Abrir `prancha.jpg` e `planos.jpg` (ferramenta Read). Para ver um momento de perto:
   `ffmpeg -v error -ss <segundos> -i referencias/videos/<pasta>/video.mp4 -frames:v 1 trabalho/quadro.jpg`
2. Conferir os cortes: o script conta toda troca forte de imagem. Palavra grande entrando também conta. Na tabela, diga o que é corte de verdade e o que é texto entrando.
3. Trocar cada "(preencher)" da ficha por texto curto e concreto:
   - **Estrutura cena a cena:** o que aparece e como entra.
   - **Tipografia, cor e som:** o que dá para ver e medir.
   - **Por que prende:** o gancho, o que segura, onde o ritmo muda.
   - **O que copiar (linguagem):** ritmo, letra, som, estrutura.
   - **O que não copiar:** imagem, música, voz, marca e texto do autor.
4. Ajustar as tags no cabeçalho e no fim da ficha e refazer o índice:
   `.venv/bin/python .claude/skills/referencias/scripts/fichas.py indice`
5. Responder ao aluno em 4 a 6 linhas: o que é, como é montado, o que dá para usar, onde está a ficha.

Várias referências de uma vez: um `baixar.py` por link e, no fim, dizer o que elas têm em comum (o que se repete vira regra do aluno).

## 3. Buscar

"Me traz as fichas de meia tela":
```bash
.venv/bin/python .claude/skills/referencias/scripts/fichas.py buscar meia tela
```
Tag e título vêm primeiro; o texto da ficha só entra se nada bater. `fichas.py listar` mostra todas. Abrir as fichas achadas e resumir em uma linha cada.

## 4. Aplicar a linguagem num vídeo do aluno (aula 20)

Pedido típico: "aplica a linguagem da ficha meia-tela-limpa no meu cortado.mp4".

1. Ler a ficha inteira e montar um plano curto antes de editar (mostrar ao aluno):
   - **Ritmo:** cortes por segundo, plano médio, onde cortar (na pausa da fala, na batida).
   - **Letra:** tamanho, peso, caixa, posição e como entra. Use a fonte e as cores da marca do aluno (`marcas/<marca>/`). Se ele não tiver, use uma fonte livre parecida.
   - **Som:** o tipo de efeito em cada corte, trilha alta ou baixa, silêncio. Use sons do próprio aluno ou com licença conferida (`assets/sons/`).
   - **Estrutura:** a sequência de cenas, adaptada ao conteúdo do aluno.
2. Editar com a skill de edição ou de motion do estúdio, seguindo o plano. Tudo em `trabalho/<peca>/`.
3. Conferir medindo a versão nova e comparando com a ficha:
   `.venv/bin/python .claude/skills/referencias/scripts/baixar.py --so-medir trabalho/<peca>/versao-referencia.mp4`
4. Lado a lado, só para o aluno comparar (nunca vai para `entrega/`):
   `ffmpeg -i <ref.mp4> -i <versao.mp4> -filter_complex "[0]scale=-2:960[a];[1]scale=-2:960[b];[a][b]hstack" -t 20 trabalho/<peca>/lado-a-lado.mp4`

Nunca use quadro, trecho, música, voz, logo ou texto do vídeo de referência. O arquivo baixado não entra em nenhuma linha do tempo, render ou entrega. O que passa para o vídeo do aluno é só o jeito de fazer.

## Como conferir

- A ficha existe em `referencias/fichas/`, tem o link original e nenhum "(preencher)" sobrando.
- `prancha.jpg` abre e mostra o tempo em cada quadro.
- `referencias/INDICE.md` lista a ficha nas tags certas.
- A busca por uma das tags acha a ficha.

## Regras

- Vídeo de terceiro é só estudo. Nunca entra em trabalho, entrega ou publicação.
- Guardar sempre o link original na ficha.
- Respeitar os termos da plataforma: baixar só o que está público (ou com o login do próprio aluno, se ele pedir), não repostar, não distribuir.
- Licença sem informação = todos os direitos reservados.
- Não apagar fichas nem vídeos sem o aluno pedir.
