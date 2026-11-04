#!/usr/bin/env python3
"""Palavra grande ATRÁS da pessoa: entre ela e o fundo, no tempo da fala.

Uso:
  .venv/bin/python .claude/skills/palavra-atras/palavra_atras.py <video> <pasta-do-recorte> <cenas.json> <saida.mp4>
      [--cor "#FFFFFF"] [--fonte barlow-condensed/BarlowCondensed-Black.ttf] [--altura 0.5] [--maiusculas sim]

- pasta-do-recorte: onde estão matte.mp4 e rostos.json (feitos por ferramentas/recorte.sh).
- cenas.json: [{"texto": "AURORA", "inicio": 1.2, "fim": 2.9}], tempos do vídeo original.
- --altura: quanto da (última) linha a cabeça cobre (0 = palavra toda acima da cabeça, 1 = toda atrás do rosto). Padrão 0,45.
Só o trecho do recorte é processado (se o recorte foi feito com --inicio/--fim, a saída é esse trecho).
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


COR = e.cor(opt("--cor", "#FFFFFF"))
FONTE = opt("--fonte", "barlow-condensed/BarlowCondensed-Black.ttf")
COBRE = float(opt("--altura", "0.45"))
MAIUSC = opt("--maiusculas", "sim") != "nao"
if len(args) < 4:
    print(__doc__)
    sys.exit(1)
VIDEO, PASTA, CENAS, SAIDA = args[:4]

rec = e.Recorte(PASTA)
if not rec.matte:
    sys.exit("Este recorte foi feito com --so-rostos. Rode de novo sem essa opção para ter o matte.mp4.")
W, H, FPS = rec.largura, rec.altura, rec.fps
INICIO, DUR = rec.inicio, rec.fim - rec.inicio
TOPO_SEGURO = int(0.09 * H)  # a faixa de cima do 9:16 tem o nome do perfil

ENTRA, SAI = 0.38, 0.22


def montar(c):
    """Desenha a palavra uma vez (máscara em tons de cinza) e decide onde ela fica."""
    texto = c["texto"].upper() if MAIUSC else c["texto"]
    sl = rec.entre(c["inicio"], c["fim"])
    topo = float(np.percentile(rec.topo[sl], 20))  # cabeça mais alta do trecho
    cx = float(np.median(rec.x[sl] + rec.w[sl] / 2))
    # duas palavras ou mais: testa em uma linha e em duas, fica com a que deixa a letra maior
    opcoes = [[texto]]
    partes = texto.split()
    if len(partes) > 1:
        meio = min(range(1, len(partes)), key=lambda i: abs(len(" ".join(partes[:i])) - len(" ".join(partes[i:]))))
        opcoes.append([" ".join(partes[:meio]), " ".join(partes[meio:])])
    melhor = None
    for linhas in opcoes:
        tam = int(H * 0.2)
        while tam > 60:
            f = e.fonte(FONTE, tam)
            caixas = [f.getbbox(l) for l in linhas]
            if max(b[2] - b[0] for b in caixas) <= W * 0.94 and len(linhas) * tam <= H * 0.3:
                break
            tam -= 6
        if melhor is None or tam > melhor[0] * 1.15:
            melhor = (tam, linhas, f)
    tam, linhas, f = melhor
    pad = 40
    entre = int(tam * 0.86)  # letra condensada em caixa alta: linhas bem juntas
    a0, a1 = f.getbbox("ÁG")[1], f.getbbox("ÁG")[3]
    largura = max(f.getbbox(l)[2] - f.getbbox(l)[0] for l in linhas)
    altura_letra = (len(linhas) - 1) * entre + (a1 - a0)
    mascara = Image.new("L", (largura + 2 * pad, altura_letra + 2 * pad), 0)
    d = ImageDraw.Draw(mascara)
    for i, l in enumerate(linhas):
        b = f.getbbox(l)
        d.text((pad + (largura - (b[2] - b[0])) / 2 - b[0], pad + i * entre - a0), l, font=f, fill=255)
    # a cabeça cobre a parte de baixo da palavra; nunca sobe para a faixa do perfil
    y_letra = topo - altura_letra + COBRE * (a1 - a0)  # em duas linhas, a cabeça só cobre a de baixo
    y_letra = max(TOPO_SEGURO, y_letra)
    x = (W - mascara.width) / 2 + 0.12 * (cx - W / 2)  # puxa um pouco para o lado da pessoa
    x = min(max(x, -pad + W * 0.03), W - mascara.width + pad - W * 0.03)
    sombra = mascara.filter(ImageFilter.GaussianBlur(18))
    return dict(c, texto=texto, mascara=mascara, sombra=sombra, x=x, y=y_letra - pad)


cenas = [montar(c) for c in e.carregar_cenas(CENAS) if c["fim"] > INICIO and c["inicio"] < rec.fim]
print(f"{len(cenas)} palavras: " + ", ".join(f"{c['texto']} ({c['inicio']:.1f}s)" for c in cenas))

gravar = e.Gravador(SAIDA, W, H, FPS, VIDEO, INICIO, DUR)
quadros = e.ler_quadros(VIDEO, W, H, FPS, INICIO, DUR)
mattes = e.ler_quadros(rec.matte, W, H, FPS, 0, DUR, cinza=True)
n = 0
for quadro, matte in zip(quadros, mattes):
    t = INICIO + n / FPS
    ativas = [c for c in cenas if c["inicio"] - 0.01 <= t <= c["fim"] + SAI]
    if not ativas:
        gravar.escrever(quadro)
        n += 1
        continue
    fundo = quadro.astype(np.float32)
    for c in ativas:
        k = e.saida_suave((t - c["inicio"]) / ENTRA)            # entrada
        s = e.limitar(1 - (t - c["fim"]) / SAI) if t > c["fim"] else 1.0  # saída
        alfa = e.limitar((t - c["inicio"]) / (ENTRA * 0.6)) * s
        escala = 1.10 - 0.10 * k + 0.03 * (1 - s)
        sobe = 36 * (1 - k)
        m, sb = c["mascara"], c["sombra"]
        nw, nh = int(m.width * escala), int(m.height * escala)
        m = np.asarray(m.resize((nw, nh), Image.BILINEAR), np.float32) / 255 * alfa
        sb = np.asarray(sb.resize((nw, nh), Image.BILINEAR), np.float32) / 255 * alfa
        x = int(c["x"] + (c["mascara"].width - nw) / 2)
        y = int(c["y"] + (c["mascara"].height - nh) / 2 + sobe)
        # recorta o que sair da tela
        ax, ay = max(0, x), max(0, y)
        bx, by = min(W, x + nw), min(H, y + nh)
        if bx <= ax or by <= ay:
            continue
        m = m[ay - y:by - y, ax - x:bx - x, None]
        sb = sb[ay - y + 0:by - y, ax - x:bx - x, None]
        reg = fundo[ay:by, ax:bx]
        reg = reg * (1 - 0.35 * sb)                       # sombra macia: a palavra descola do fundo
        reg = reg * (1 - m) + np.array(COR, np.float32) * m
        fundo[ay:by, ax:bx] = reg
    # a pessoa volta por cima: a palavra fica entre ela e o fundo
    p = matte.astype(np.float32) / 255
    p = np.clip((p - 0.3) / 0.4, 0, 1)[..., None]
    gravar.escrever(fundo * (1 - p) + quadro * p)
    n += 1
gravar.fechar()
print(f"ok · {n} quadros · {e.rel(SAIDA)}")
