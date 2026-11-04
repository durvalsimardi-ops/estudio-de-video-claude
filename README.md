# Estúdio de Vídeo com Claude Code

O projeto que acompanha o curso **Estúdio de Vídeo com Claude Code**, de Durval Simardi. Você instala uma vez e usa em todas as aulas: as pastas do estúdio, o `CLAUDE.md` com as regras, as skills de cada aula e as listas de conferência.

## Instalar pelo app do Claude (aula 2)

1. Abra o app do Claude, aba **Code**, e escolha uma pasta vazia para o estúdio (ex.: `Documentos/Estudio`).
2. Cole este pedido, com o link deste repositório:
   > Lê este repositório antes de instalar: a licença, o que o instalador roda e se é seguro para o meu computador. Depois clona nesta pasta.
3. Depois que ele clonar, peça: **/preparar-estudio**. Ele mostra o que falta instalar (ffmpeg, Whisper, Node) e só instala com o seu OK.
4. Feche e abra a sessão na pasta do estúdio para as skills aparecerem quando você digitar `/`.

Sem o app: baixe o ZIP pelo botão **Code › Download ZIP** do GitHub, descompacte e abra a pasta no Claude.

## O que vem

| Pasta | Para quê |
|---|---|
| `CLAUDE.md` | As regras do seu estúdio. Preencha com o seu nome e duas regras suas (aula 3). |
| `originais/` | Vídeos como chegaram. Nunca são alterados. |
| `trabalho/` | Tudo que é intermediário, uma pasta por peça. |
| `entrega/` | Só o final. |
| `referencias/` | Fichas dos vídeos que você estuda (aulas 18 a 20). |
| `marcas/` | Manual, logo e cores de cada marca. Exemplo: Café Aurora (aula 29). |
| `listas/` | Conferências: antes de entregar, antes de enviar e segurança. |
| `assets/` | Sons, fontes, ícones e adesivos livres para usar. |
| `ferramentas/` | Instalador e transcrição. |

## Como editamos

A maior parte da edição é por código: scripts (ffmpeg e Python) para cortar, transcrever e mixar, e o **HyperFrames** para tudo que aparece na tela. O After Effects é exceção. Veja `/qual-ferramenta`.

## As skills, por aula

Digite `/` e o nome, ou peça com as suas palavras: o Claude escolhe a skill certa.

| Aula | Skill | O que faz |
|---|---|---|
| 1 a 3 | `/preparar-estudio` | Confere e instala o que falta, ajuda no `CLAUDE.md` |
| 4 | `/converter-iphone` | Vídeo do iPhone em HDR para vídeo comum, sem lavar as cores |
| 6 e 7 | `/receber-pelo-whatsapp` | Recebe, edita e devolve com aprovação |
| 8 | `/conferir-gravacao` | Mede luz, volume e se a cabeça cabe no quadro |
| 9 | `/cortar-fala` | Corta silêncio, vício e take repetido, sempre entre palavras |
| 10 | `/legenda` | Legenda palavra a palavra com destaque |
| 11 | `/palavra-atras` | Palavra atrás de você, entre você e o fundo |
| 12 | `/palavra-acima` | Palavra que sobe de trás da cabeça e para acima dela |
| 13 | `/transicoes` | Chicote, zoom e flash nas viradas da fala, com som |
| 14 | `/meia-tela` | Você embaixo e um painel por ideia em cima |
| 15 | `/animacoes-em-cima` | Adesivos entrando no tempo da fala |
| 16 | `/som` | Efeitos, trilha baixa e volume final em −14 LUFS |
| 17 | `/qual-ferramenta` | Scripts, HyperFrames, Remotion ou After: o que cada um faz e quando usar |
| 18 a 20 | `/referencias` | Baixa, estuda e guarda vídeos de referência em fichas |
| 21 | `/instalar-hyperframes` | Instala e confere o HyperFrames e as skills dele no Claude |
| 21 e 28 | `/motion-hyperframes` | Vídeo animado por código, do zero ou por cima do seu vídeo gravado |
| 22 | `/remotion-ou-hyperframes` | Quando usar cada um, com o mesmo exemplo nos dois |
| 23 | `/blender-3d` | Objeto 3D girando, renderizado pelo Blender |
| 24 | `/video-com-ia` | Regras e preço antes de gerar vídeo por IA |
| 25 e 26 | `/voz-elevenlabs` | Narração, efeitos e a sua própria voz |
| 27 | `/video-desenhado` | Desenho aparecendo traço a traço no tempo da fala |
| 28 | `/peca-completa` | Do roteiro à entrega, com conferência |
| 29 | `/cafe-aurora` | Exemplo de skill de marca e como criar a sua |
| 30 | `/revisao-por-link` | Link para o cliente comentar no segundo exato |
| 31 | `/custo-do-video` | Custo do vídeo e preço com margem |

## Precisa ter

- App do Claude com plano que inclua o Claude Code.
- Mac com chip Apple é o caminho principal do curso. No Windows quase tudo funciona; o recorte de pessoa (aulas 8, 11 e 12) usa um recurso que só o Mac tem.
- Contas opcionais, cada uma com o seu custo: ElevenLabs (voz), gerador de vídeo por IA, Cloudflare gratuito (revisão por link).

## Regras do estúdio

O Claude pergunta antes de publicar, enviar, gastar crédito ou apagar. Vídeo de outra pessoa é só estudo. Veja `listas/seguranca.md`.

## Licença

Código e skills sob licença MIT (`LICENSE`): pode usar, mudar e usar em trabalho de cliente. Fontes, ícones e outros arquivos de terceiros têm a licença ao lado, na própria pasta.
