---
name: peca-completa
description: Faz uma peça de vídeo inteira do começo ao fim, com conferência antes de mostrar. Use quando o aluno disser "faz o vídeo completo", "do roteiro ao final", "faz um vídeo de 20 s da marca X com a ficha Y" ou "quero a primeira peça pronta".
---

# Uma peça completa (aula 28)

Junta as outras skills numa ordem fixa. Cada etapa só começa quando a anterior foi conferida.

## Antes de começar

Confirmar com o aluno, em uma mensagem só:
- a marca (e a skill dela, ex.: `/cafe-aurora`);
- a duração e o formato (padrão 9:16, 1080x1920);
- a ficha de referência (`referencias/fichas/`), se houver;
- se é vídeo gravado (tem bruto em `originais/`) ou animado (só roteiro);
- se tem narração e com qual voz (o ID no `CLAUDE.md`), e se pode gastar crédito.

## Ordem

1. **Pasta:** `trabalho/<marca>-<assunto>-AAAA-MM-DD/`.
2. **Roteiro:** frases curtas, uma ideia por frase, no tom da marca. Mostrar ao aluno antes de seguir.
3. **Linguagem:** ler a ficha de referência e anotar o que copiar (ritmo dos cortes, letra, som). Nunca a imagem, a música ou a marca do outro.
4. **Imagem:**
   - vídeo gravado: `/converter-iphone` → `/cortar-fala` → efeitos pedidos (`/transicoes`, `/palavra-acima`, `/meia-tela`, `/animacoes-em-cima`) → `/legenda` por último, para a legenda não entrar no chicote nem no zoom;
   - vídeo animado: `/motion-hyperframes` (ou `/video-desenhado`).
5. **Voz** (se tiver): `/voz-elevenlabs`, só com OK do crédito. Transcrever e conferir a pronúncia.
6. **Som:** `/som`: efeitos nos acontecimentos, trilha baixa, −14 LUFS.
7. **Conferência:** `listas/antes-de-entregar.md` inteira. Corrigir e conferir de novo.
8. **Entrega:** vídeo em `entrega/` com nome claro e a legenda do post ao lado. Responder curto: o que foi feito, as medidas e onde está.

## Regras

- Não pular a conferência para entregar mais rápido.
- Publicar ou enviar só com OK (`listas/antes-de-enviar.md`).
