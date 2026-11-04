---
name: revisao-por-link
description: Revisão de vídeo com o cliente por link. Use quando o aluno disser "sobe a prévia para revisão", "me passa o link para o cliente comentar", "chegou comentário?", "puxa os comentários", "aplica as correções do cliente", "sobe a versão 2" ou "configura a revisão por link". O cliente assiste, pausa e comenta no segundo exato; o Claude puxa e transforma em lista de correções com o tempo e o quadro.
---

# Revisão por link

Aula 30. A prévia vai para uma página só sua. O cliente abre o link, pausa onde quer mudar e escreve o nome e o comentário. O comentário fica preso naquele segundo. Depois o Claude puxa tudo e monta a lista de correções, com um quadro de cada momento.

Funciona no plano gratuito da Cloudflare, sem cartão: um site (Pages) com o vídeo e um banco pequeno (D1) com os comentários.

## Antes de começar (uma vez só)

1. Ter Node.js e ffmpeg: `bash ferramentas/instalar.sh`.
2. Criar a conta gratuita em cloudflare.com. Quem cria e entra na conta é o aluno.
3. O aluno entra pelo terminal, no navegador dele:
   ```bash
   npx wrangler login
   ```
   O Claude não digita e-mail nem senha.
4. Criar o site e o banco na conta do aluno (o nome vira o endereço, ex.: `revisao-ana.pages.dev`):
   ```bash
   node .claude/skills/revisao-por-link/revisao.mjs configurar revisao-<nome-do-aluno>
   ```
   O script cria o token de leitura dos comentários e guarda em `~/.config/estudio-de-video/revisao.json`, fora do git. Nunca mostrar o token no chat nem copiar para o projeto.

## Passo a passo

**1. Subir a prévia** (só prepara no computador, ainda não publica):
```bash
node .claude/skills/revisao-por-link/revisao.mjs subir trabalho/<peca>/previa.mp4 --titulo "Café Aurora · Reels 1"
```
- O script faz uma prévia leve (H.264, até 1280 px). Se passar de 24 MB, reduz sozinho (o limite do Cloudflare é 25 MB por arquivo).
- Cada peça ganha um código aleatório no link (`/p/<codigo>/`). Sem o código ninguém acha a página.
- Versão nova da mesma peça (v2, v3...), com o que mudou:
  ```bash
  node .claude/skills/revisao-por-link/revisao.mjs subir trabalho/<peca>/previa-v2.mp4 --peca <codigo> --nota "legenda maior"
  ```

**2. Publicar.** Perguntar antes: "Posso publicar a prévia na sua página de revisão?". Só com o OK:
```bash
node .claude/skills/revisao-por-link/revisao.mjs publicar
```
Mostrar o link ao aluno. Quem manda o link ao cliente é o aluno. Se ele pedir para o Claude enviar, confirmar destinatário e texto antes.

**3. Ver se chegou comentário:**
```bash
node .claude/skills/revisao-por-link/revisao.mjs listar
```

**4. Puxar e virar lista de correções:**
```bash
node .claude/skills/revisao-por-link/revisao.mjs puxar            # só os novos, de todas as peças
node .claude/skills/revisao-por-link/revisao.mjs puxar <codigo> --todos   # todos de uma peça
```
- Cria `trabalho/revisao/correcoes/<peca>/v<n>-<data>/correcoes.md` e uma pasta `quadros/` com um quadro por comentário.
- Os comentários puxados ficam como "recebido" e não voltam no próximo `puxar`.

**5. Aplicar.**
- Abrir cada quadro (Read) e trocar cada "Correção: (preencher)" por uma ação concreta. Ex.: "0:02,4 · legenda de 34 para 48 px".
- Mostrar a lista ao aluno e esperar o OK.
- Editar e subir a versão seguinte com `--peca <codigo>`.
- Comentário vago ("não gostei"): sugerir ao aluno uma pergunta ao cliente. Não adivinhar.

## Testar no computador, sem publicar

```bash
node .claude/skills/revisao-por-link/revisao.mjs local
```
- Abre `http://localhost:8788/p/<codigo>/`, com banco de teste local.
- Em outro terminal, puxar com `--base http://localhost:8788`.
- Nada vai para a internet.

## Como conferir

- O link abre no celular, o vídeo toca e o botão mostra o segundo certo ("Comentar em 0:04,2").
- Depois de um comentário de teste, `puxar` gera a lista com o tempo, o nome, o texto e o quadro do momento.
- Um código inventado no link mostra "Link não encontrado" e não aceita comentário.

## Onde fica cada coisa

- `.claude/skills/revisao-por-link/site/`: modelo da página (`pagina.html`, cor em `--cor`), páginas fixas e a função dos comentários.
- `trabalho/revisao/`: o site montado (`publico/`), `wrangler.toml`, `pecas.json` e `correcoes/`. Fica fora do git.

## Regras

- Publicar ou enviar link para alguém só com o OK do aluno.
- O login na Cloudflare é sempre do aluno. O token fica fora do git e fora do chat.
- Só a prévia vai para a página, nunca o arquivo final em alta nem material bruto.
- Rodadas de revisão: as do contrato com o cliente.
- Tirar uma peça do ar: apagar a pasta `trabalho/revisao/publico/p/<codigo>/` e publicar de novo. Só com o OK do aluno.
