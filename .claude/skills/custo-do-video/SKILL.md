---
name: custo-do-video
description: Calcula quanto custou um vídeo (tempo + créditos + ferramentas) e um preço de venda. Use quando o aluno disser "quanto custou esse vídeo", "quanto cobrar", "calcula o custo" ou "meu preço está certo?".
---

# Custo e preço do vídeo (aula 31)

## Passo a passo

1. Levantar com o aluno, sem chutar:
   - minutos de trabalho dele nesse vídeo (gravar, pedir, conferir, ajustar);
   - quanto vale a hora dele (o valor que ele quer ganhar por hora);
   - créditos gastos (voz, vídeo por IA, imagem) e o preço de cada crédito no plano dele;
   - assinaturas usadas no mês (Claude, ElevenLabs etc.) e quantos vídeos ele faz por mês, para dividir.
2. Calcular:
   ```bash
   python3 .claude/skills/custo-do-video/calcular.py --minutos 40 --hora 60 --creditos 120 --preco-credito 0.05 --assinaturas 330 --videos-mes 20 --margem 50
   ```
3. Mostrar o resultado em 4 linhas: tempo, créditos, parte das assinaturas, custo total; e o preço com a margem que ele escolheu.
4. Guardar o cálculo em `trabalho/<peca>/custo.md` para comparar com os próximos.

## Regras

- Só números que o aluno informou ou que estão na conta dele. Preço de crédito muda: conferir no plano.
- O cálculo é de custo. Nunca prometer quanto o aluno vai ganhar ou vender.
- Revisões entram no contrato com o cliente (ex.: duas rodadas). Rodada extra é cobrada à parte.
