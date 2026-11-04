#!/usr/bin/env python3
"""Palavra que sobe de trás da cabeça e para ACIMA dela, em letra de vidro, acompanhando a cabeça.

Uso:
  .venv/bin/python .claude/skills/palavra-acima/palavra_acima.py <video> <pasta-do-recorte> <cenas.json> <saida.mp4>
      [--folga 44] [--fonte playfair-display/PlayfairDisplay-Italic.ttf] [--fonte-apoio barlow/Barlow-SemiBold.ttf]

- pasta-do-recorte: onde estão matte.mp4 e rostos.json (feitos por ferramentas/recorte.sh).
- cenas.json: [{"texto": "Aurora", "apoio": "o café da", "inicio": 1.2, "fim": 2.9}]
  "apoio" é opcional: uma linha pequena acima da palavra grande.
- --folga: distância mínima, em pixels, entre a palavra e o alto da cabeça (padrão 44).
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "ferramentas"))
import estudio as e  # noqa: E402

e.precisa_pillow()
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

args = sys.argv[1:]


def opt(nome, padrao):
    if nome in args:
        i = args.index(nome)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return padrao


FOLGA = float(opt("--folga", "44"))
FONTE = opt("--fonte", "playfair-display/PlayfairDisplay-Italic.ttf")
FONTE_APOIO = opt("--fonte-apoio", "barlow/Barlow-SemiBold.ttf")
if len(args) < 4:
    print(__doc__)
    sys.exit(1)
VIDEO, PASTA, CENAS, SAIDA = args[:4]

rec = e.Recorte(PASTA)
if not rec.matte:
    sys.exit("Este recorte foi feito com --so-rostos. Rode de novo sem essa opção para ter o matte.mp4.")
W, H, FPS = rec.largura, rec.altura, rec.fps
INICIO, DUR = rec.inicio, rec.fim - rec.inicio
TOPO_SEGURO = int(0.075 * H)
SOBE, SAI = 0.5, 0.18

# Topo da cabeça sem tremer: pega o ponto mais alto numa janela curta (a palavra nunca encosta
# quando a cabeça sobe rápido) e depois suaviza em sino. O mesmo para o centro do rosto, mais suave.
topo_liso = e.suavizar(e.minimo_movel(rec.topo, int(FPS * 0.5)), FPS, 0.3)
centro_liso = e.suavizar(rec.x + rec.w / 2, FPS, 0.8)


def fonte_var(arquivo, tam, peso=700):
    f = e.fonte(arquivo, tam)
    try:
        f.set_variation_by_axes([peso])  # fonte variável: escolhe o peso
    except Exception:
        pass
    return f


def montar(c):
    """Desenha a palavra (máscara) e a linha de apoio uma vez por cena."""
    sl = rec.entre(c["inicio"], c["fim"])
    espaco = float(np.percentile(topo_liso[sl], 10)) - FOLGA - TOPO_SEGURO  # altura livre acima da cabeça
    apoio = c.get("apoio", "").strip()
    fa = e.fonte(FONTE_APOIO, 52)
    ha = (fa.getbbox("Ág")[3] - fa.getbbox("Ág")[1] + 22) if apoio else 0
    tam = 260
    while tam > 70:
        f = fonte_var(FONTE, tam)
        x0, y0, x1, y1 = f.getbbox(c["texto"])
        if x1 - x0 <= W * 0.88 and (y1 - y0) + ha <= max(espaco, 150):
            break
        tam -= 6
    pad = 30
    gw, gh = x1 - x0, y1 - y0
    w = max(gw, (fa.getbbox(apoio)[2] - fa.getbbox(apoio)[0]) if apoio else 0) + 2 * pad
    h = gh + ha + 2 * pad
    letra = Image.new("L", (w, h), 0)
    ImageDraw.Draw(letra).text(((w - gw) / 2 - x0, pad + ha - y0), c["texto"], font=f, fill=255)
    linha = Image.new("L", (w, h), 0)
    if apoio:
        b = fa.getbbox(apoio)
        ImageDraw.Draw(linha).text(((w - (b[2] - b[0])) / 2 - b[0], pad - b[1]), apoio, font=fa, fill=255)
    # borda fina de luz (1 a 2 px): dá o brilho do vidro sem virar contorno grosso
    borda = np.clip(np.asarray(letra.filter(ImageFilter.MaxFilter(3)), np.float32)
                    - np.asarray(letra.filter(ImageFilter.MinFilter(3)), np.float32), 0, 255) / 255
    sombra_img = Image.fromarray(np.maximum(np.asarray(letra), np.asarray(linha)))
    sombra = np.asarray(sombra_img.filter(ImageFilter.GaussianBlur(16)), np.float32) / 255
    return dict(c, w=w, h=h, letra=np.asarray(letra, np.float32) / 255, linha=np.asarray(linha, np.float32) / 255,
                borda=borda, sombra=sombra)


cenas = [montar(c) for c in e.carregar_cenas(CENAS) if c["fim"] > INICIO and c["inicio"] < rec.fim]
print(f"{len(cenas)} palavras: " + ", ".join(f"{c['texto']} ({c['inicio']:.1f}s)" for c in cenas))

gravar = e.Gravador(SAIDA, W, H, FPS, VIDEO, INICIO, DUR)
quadros = e.ler_quadros(VIDEO, W, H, FPS, INICIO, DUR)
mattes = e.ler_quadros(rec.matte, W, H, FPS, 0, DUR, cinza=True)
n = 0
for quadro, matte in zip(quadros, mattes):
    t = INICIO + n / FPS
    i = rec.indice(t)
    ativas = [c for c in cenas if c["inicio"] - 0.01 <= t <= c["fim"] + SAI]
    if not ativas:
        gravar.escrever(quadro)
        n += 1
        continue
    original = quadro.astype(np.float32)
    saida = original.copy()
    for c in ativas:
        k = e.saida_suave_forte((t - c["inicio"]) / SOBE)
        some = e.limitar(1 - (t - c["fim"]) / SAI) if t > c["fim"] else 1.0
        alfa = e.limitar((t - c["inicio"]) / 0.12) * some
        w, h = c["w"], c["h"]
        # posição final: a base da palavra fica FOLGA px acima do topo da cabeça, sem sair da tela
        y_final = max(TOPO_SEGURO, topo_liso[i] - FOLGA - h)
        # começa escondida atrás da cabeça e sobe até a posição final
        y = int(round(y_final + (topo_liso[i] + 0.25 * rec.h[i] - y_final) * (1 - k)))
        x = int(round(min(max(centro_liso[i] - w / 2, W * 0.04), W * 0.96 - w)))
        ay, by = max(0, y), min(H, y + h)
        ax, bx = max(0, x), min(W, x + w)
        if by <= ay or bx <= ax:
            continue
        cy, cx = slice(ay - y, by - y), slice(ax - x, bx - x)
        letra = c["letra"][cy, cx, None] * alfa
        linha = c["linha"][cy, cx, None] * alfa
        borda = c["borda"][cy, cx, None] * alfa
        sombra = c["sombra"][cy, cx, None] * alfa
        reg = saida[ay:by, ax:bx]
        # vidro: dentro da letra aparece o fundo desfocado e clareado
        rh, rw = reg.shape[:2]
        fosco = Image.fromarray(reg.astype(np.uint8)).resize((max(1, rw // 4), max(1, rh // 4)), Image.BILINEAR)
        fosco = fosco.filter(ImageFilter.GaussianBlur(4)).resize((rw, rh), Image.BILINEAR)
        vidro = np.asarray(fosco, np.float32) * 0.5 + 255 * 0.42
        reg = reg * (1 - 0.30 * sombra)                 # sombra macia
        reg = reg * (1 - letra) + vidro * letra          # corpo de vidro
        reg = reg * (1 - 0.85 * borda) + 255 * 0.85 * borda  # brilho fino da borda
        reg = reg * (1 - 0.95 * linha) + 255 * 0.95 * linha  # linha de apoio em branco
        saida[ay:by, ax:bx] = reg
    # a pessoa fica sempre na frente: a palavra nasce de trás da cabeça
    p = np.clip((matte.astype(np.float32) / 255 - 0.3) / 0.4, 0, 1)[..., None]
    gravar.escrever(saida * (1 - p) + original * p)
    n += 1
gravar.fechar()
print(f"ok · {n} quadros · {e.rel(SAIDA)}")
