---
name: qual-ferramenta
description: Explica qual ferramenta usar em cada parte da edição (scripts de código, HyperFrames, Remotion, After Effects) e por quê. Use quando o aluno perguntar "faço isso no After?", "qual a diferença entre HyperFrames e Remotion?", "preciso do After?", "por onde eu edito isso?".
---

# Qual ferramenta usar (aula 17)

No curso, a maior parte da edição é feita **por código**: o Claude escreve e roda, você confere o resultado. O After Effects é exceção.

## As quatro formas de editar

| Ferramenta | O que é | Usamos para | Como pedir |
|---|---|---|---|
| **Scripts do estúdio** (ffmpeg + Python) | Comandos que cortam, juntam, convertem e medem vídeo e áudio | Converter do iPhone, cortar pela fala, transcrever, recortar a pessoa, mixar o som, medir volume | `/converter-iphone`, `/cortar-fala`, `/som`, `/conferir-gravacao` |
| **HyperFrames** | Uma página HTML que vira vídeo, quadro a quadro | **Quase tudo que aparece na tela:** legenda, títulos, palavra atrás e acima, meia tela, adesivos, cartões por cima do vídeo gravado e animação do zero | `/motion-hyperframes` (instalação: `/instalar-hyperframes`) |
| **Remotion** | O mesmo princípio, escrito em React | Quem já programa em React ou já tem projeto nele | `/remotion-ou-hyperframes` |
| **After Effects** | Programa da Adobe, por assinatura, editado à mão | Só quando alguém precisa abrir e mexer no projeto `.aep` | Pedir o projeto e montar no After |

## Por que código e HyperFrames primeiro

- **Repete igual:** troca o texto, a cor ou o vídeo e sai a mesma peça, quantas vezes precisar.
- **No tempo exato da fala:** a transcrição dá o segundo de cada palavra, e a animação entra nele.
- **O Claude confere sozinho:** renderiza, tira quadros, olha e corrige antes de te mostrar.
- **Sem assinatura e sem programa aberto:** roda em segundo plano, inclusive pelo celular com o Remote Control.
- **Grátis e aberto:** o HyperFrames é Apache 2.0.

## O After: vantagem e desvantagem

| Vantagem | Desvantagem |
|---|---|
| Projeto `.aep` que um editor abre e ajusta à mão | Assinatura paga da Adobe |
| Rastreamento de movimento, Roto Brush e plugins prontos | Por script é lento e frágil: o After precisa estar aberto, avisos travam o script e o render demora |
| Padrão do mercado: cliente ou agência pode pedir o arquivo | O Claude não vê o resultado sem renderizar e exportar |
| | Não roda pelo celular nem em segundo plano |

**Regra do curso:** comece por código e HyperFrames. Use o After só quando o cliente pedir o `.aep` editável ou quando precisar de um recurso que só ele tem.

## Se precisar do After mesmo assim

1. No After: **Configurações › Scripts e expressões › Permitir que scripts gravem arquivos e acessem a rede** ligado (quem liga é o aluno).
2. Peça ao Claude um script `.jsx` que monte a composição (vídeo de fundo, textos, posições) e salve o `.aep`.
3. No After: **Arquivo › Scripts › Executar arquivo de script**.
4. Renderize pela Fila de renderização e passe o resultado em `/som` para o volume final.
