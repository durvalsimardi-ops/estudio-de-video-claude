---
name: transicoes
description: Aplica transições na hora certa da fala - chicote (whip pan com borrão de movimento), zoom-soco e flash - cada uma com o seu efeito sonoro. Usar quando o aluno disser "põe uma transição quando eu digo X", "faz um zoom quando eu falo X", "chicote", "whip", "flash", "dá um soco de zoom", "deixa mais dinâmico com transições".
---

# Transições na fala (aula 13)

O aluno diz em que palavra quer cada efeito ("quando eu digo *promoção*, zoom"). O script acha a palavra na transcrição e aplica o efeito com o som no mesmo instante.

- **chicote**: a imagem corre para o lado com borrão de movimento e volta (som: whoosh, com o ponto mais forte no meio do borrão);
- **zoom-soco**: aproxima em 2 quadros, segura e volta suave (som: impacto grave);
- **flash**: clarão branco que some rápido (som: brilho).

## Antes de começar

- Precisa do `palavras.json` no tempo do vídeo (sai do `/cortar-fala`).
- Precisa do Pillow: `.venv/bin/python -c "import PIL"`; se der erro, `.venv/bin/pip install pillow`.
- Precisa do kit de sons em `assets/sons/` (já vem no projeto; se sumir, rode `.venv/bin/python .claude/skills/som/gerar_kit.py`).
- Pergunte as palavras exatas de cada efeito. Use poucos efeitos: 2 a 4 num vídeo de 30 s.

## Passo a passo

1. Aplicar:
   ```
   .venv/bin/python .claude/skills/transicoes/transicoes.py trabalho/<peça>/corte/cortado.mp4 trabalho/<peça>/corte/palavras.json trabalho/<peça>/transicoes --chicote "nota cinco" --zoom "promoção" --flash "café aurora"
   ```
   Cada opção pode se repetir. `--todas` aplica em todas as vezes que o trecho aparece.
2. Ajustes: `--forca-zoom 1.3` (zoom mais forte), `--segura 1.0` (fica mais tempo perto), `--centro-zoom 0.5,0.35` (mira mais alto).
3. Se depois vai usar `/som` para a mixagem final, rode com `--sem-som`: o som dos efeitos fica no `eventos.json` e entra na mixagem.
4. Saem em `trabalho/<peça>/transicoes/`: `transicoes.mp4`, `eventos.json`, `relatorio.md` e `conferencia/`.

## Como conferir

- Leia o `relatorio.md`: se aparecer "NÃO ACHEI", mostre os trechos parecidos e pergunte ao aluno qual é o certo.
- Abra cada imagem de `conferencia/` (Read): 3 quadros antes do efeito, o quadro do efeito e depois. O chicote tem que borrar na horizontal; o zoom tem que estar perto no quadro da palavra; o flash tem que ser mais forte no quadro da palavra.
- O vídeo não muda de duração: o `palavras.json` continua valendo para a legenda.

## Regras

- O efeito cai no começo da primeira palavra do trecho pedido. Nunca inventar efeito em palavra que o aluno não pediu.
- Os sons são do kit do próprio projeto (`assets/sons/LICENCA.md`): uso livre.
- Rode as transições antes da legenda, para o texto não entrar no chicote e no zoom.
- Windows: `.venv\Scripts\python` e `.venv\Scripts\pip` no lugar de `.venv/bin/...`.
