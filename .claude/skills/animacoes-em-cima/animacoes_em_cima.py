#!/usr/bin/env python3
"""Adesivos (PNG com fundo transparente) entrando por cima do vídeo no tempo da fala, longe do rosto.

Uso:
  .venv/bin/python .claude/skills/animacoes-em-cima/animacoes_em_cima.py <video> <pasta-do-recorte> <adesivos.json> <saida.mp4>
      [--tamanho 0.34] [--sem-borda]

- pasta-do-recorte: onde está o rostos.json (bash ferramentas/recorte.sh <video> <pasta> --so-rostos basta).
- adesivos.json: [{"arquivo": "assets/adesivos/xicara.png", "inicio": 2.1, "fim": 3.8, "lugar": "auto"}]
  lugar: auto (padrão), esquerda, direita, cima ou baixo. "tamanho" por adesivo também vale (fração da largura).
- --tamanho: largura do adesivo em relação ao vídeo (padrão 0,34).
- --sem-borda: não põe a borda branca de adesivo recortado.
"""
import math, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "ferramentas"))
import estudio as e  # noqa: E402

e.precisa_pillow()
import numpy as np  # noqa: E402
from PIL import Image, ImageFilter  # noqa: E402

args = sys.argv[1:]
SEM_BORDA = "--sem-borda" in args
if SEM_BORDA:
    args.remove("--sem-borda")


def opt(nome, padrao):
    if nome in args:
        i = args.index(nome)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return padrao


TAMANHO = float(opt("--tamanho", "0.34"))
if len(args) < 4:
    print(__doc__)
    sys.exit(1)
VIDEO, PASTA, LISTA, SAIDA = args[:4]

rec = e.Recorte(PASTA)
W, H, FPS = rec.largura, rec.altura, rec.fps
INICIO, DUR = rec.inicio, rec.fim - rec.inicio
ENTRA, SAI = 0.34, 0.22
# área livre do 9:16: em cima fica o nome do perfil, embaixo a legenda e os botões
ZONA = (0.05 * W, 0.11 * H, 0.95 * W, 0.74 * H)
LUGARES = {  # centro de cada posição possível (fração da tela)
    "cima-esquerda": (0.27, 0.22), "cima-direita": (0.73, 0.22),
    "meio-esquerda": (0.22, 0.45), "meio-direita": (0.78, 0.45),
    "baixo-esquerda": (0.25, 0.64), "baixo-direita": (0.75, 0.64),
}


def preparar(arquivo, largura):
    """Abre o PNG, põe a borda branca de adesivo e a sombra macia. Devolve imagem RGBA."""
    caminho = arquivo if os.path.exists(arquivo) else os.path.join(e.RAIZ, arquivo)
    img = Image.open(caminho).convert("RGBA")
    caixa = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if caixa:
        img = img.crop(caixa)
    alt = int(largura * img.height / img.width)
    if alt > 0.3 * H:  # adesivo comprido: limita a altura
        alt = int(0.3 * H)
        largura = int(alt * img.width / img.height)
    img = img.resize((largura, alt), Image.LANCZOS)
    borda = 0 if SEM_BORDA else max(6, largura // 45)
    pad = borda + 40
    tela = Image.new("RGBA", (largura + 2 * pad, alt + 2 * pad), (0, 0, 0, 0))
    alfa = Image.new("L", tela.size, 0)
    alfa.paste(img.getchannel("A"), (pad, pad))
    contorno = alfa.filter(ImageFilter.MaxFilter(2 * borda + 1)) if borda else alfa
    # sombra: o contorno desfocado, um pouco para baixo
    sombra = Image.new("L", tela.size, 0)
    sombra.paste(contorno.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.35)), (0, 10))
    tela = Image.composite(Image.new("RGBA", tela.size, (10, 12, 16, 255)), tela, sombra)
    tela.putalpha(sombra)
    if borda:
        branco = Image.new("RGBA", tela.size, (255, 255, 255, 255))
        branco.putalpha(contorno)
        tela = Image.alpha_composite(tela, branco)
    tela.alpha_composite(img, (pad, pad))
    return tela


def colar(tela, im, x, y):
    """Cola a imagem na tela mesmo se ela passar um pouco da borda."""
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(im.width, tela.width - x), min(im.height, tela.height - y)
    if cx1 > cx0 and cy1 > cy0:
        tela.alpha_composite(im.crop((cx0, cy0, cx1, cy1)), (x + cx0, y + cy0))


def sobrepoe(a, b):
    """Área em comum entre dois retângulos (x0, y0, x1, y1)."""
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def escolher_lugar(c, img, anterior):
    """Põe o adesivo onde ele não encosta no rosto (olhos e boca nunca ficam cobertos)."""
    sl = rec.entre(c["inicio"] - 0.1, c["fim"] + SAI)
    # rosto do trecho todo, com uma margem em volta
    rx0 = float((rec.x[sl] - 0.18 * rec.w[sl]).min())
    rx1 = float((rec.x[sl] + 1.18 * rec.w[sl]).max())
    ry0 = float(np.minimum(rec.topo[sl], rec.y[sl] - 0.2 * rec.h[sl]).min())
    ry1 = float((rec.y[sl] + 1.15 * rec.h[sl]).max())
    rosto = (rx0, ry0, rx1, ry1)
    cx_rosto, cy_rosto = (rx0 + rx1) / 2, (ry0 + ry1) / 2
    pedido = c.get("lugar", "auto")
    nomes = [n for n in LUGARES if pedido in ("auto", "") or pedido in n]
    melhor = None
    for nome in nomes:
        fx, fy = LUGARES[nome]
        # meio-tamanho visível do adesivo (sem a folga da sombra)
        mw, mh = img.width / 2 - 30, img.height / 2 - 30
        x = min(max(fx * W, ZONA[0] + mw), ZONA[2] - mw)
        y = min(max(fy * H, ZONA[1] + mh), ZONA[3] - mh)
        caixa = (x - mw, y - mh, x + mw, y + mh)
        nota = sobrepoe(caixa, rosto) * 10 - math.hypot(x - cx_rosto, y - cy_rosto)
        if anterior and nome == anterior:
            nota += 400  # não repete o mesmo canto em seguida
        if melhor is None or nota < melhor[0]:
            melhor = (nota, nome, x, y, sobrepoe(caixa, rosto))
    return melhor


itens, anterior = [], None
for c in e.carregar_cenas(LISTA):
    if not (c["fim"] > INICIO and c["inicio"] < rec.fim):
        continue
    arquivo = c.get("arquivo") or c.get("texto")
    largura = int(W * float(c.get("tamanho", TAMANHO)))
    for tentativa in range(4):  # se não couber longe do rosto, diminui um pouco
        img = preparar(arquivo, largura)
        nota, nome, x, y, encosta = escolher_lugar(c, img, anterior)
        if not encosta:
            break
        largura = int(largura * 0.85)
    if encosta:
        print(f"  aviso: {arquivo} encosta no rosto em {c['inicio']:.1f}s (pessoa ocupa a tela toda). Diminua o --tamanho.")
    anterior = nome
    giro = -5 if "esquerda" in nome else 5
    itens.append(dict(c, img=img, x=x, y=y, giro=giro, lugar=nome))
    print(f"  {c['inicio']:6.2f}–{c['fim']:6.2f}  {os.path.basename(arquivo)} → {nome}")

gravar = e.Gravador(SAIDA, W, H, FPS, VIDEO, INICIO, DUR)
n = 0
for quadro in e.ler_quadros(VIDEO, W, H, FPS, INICIO, DUR):
    t = INICIO + n / FPS
    ativos = [a for a in itens if a["inicio"] - 0.01 <= t <= a["fim"] + SAI]
    if not ativos:
        gravar.escrever(quadro)
        n += 1
        continue
    tela = Image.fromarray(quadro).convert("RGBA")
    for a in ativos:
        k = (t - a["inicio"]) / ENTRA
        sai = e.limitar((t - a["fim"]) / SAI) if t > a["fim"] else 0.0
        # entrada: cresce de 60% com uma passada de 3% e gira um pouco até o ângulo final
        escala = (0.6 + 0.4 * e.recuo_leve(k)) * (1 - 0.18 * e.saida_suave(sai))
        angulo = a["giro"] + (1 - e.saida_suave(k)) * (-a["giro"] * 2.2) + sai * a["giro"] * 0.8
        # parado: respira de leve para não parecer colado
        escala *= 1 + 0.012 * math.sin((t - a["inicio"]) * 2 * math.pi / 2.4)
        alfa = e.limitar(k / 0.4) * (1 - sai)
        im = a["img"]
        im = im.resize((max(1, int(im.width * escala)), max(1, int(im.height * escala))), Image.BICUBIC)
        im = im.rotate(angulo, resample=Image.BICUBIC, expand=True)
        if alfa < 1:
            im.putalpha(im.getchannel("A").point(lambda v, f=alfa: int(v * f)))
        colar(tela, im, int(a["x"] - im.width / 2), int(a["y"] - im.height / 2))
    gravar.escrever(np.asarray(tela.convert("RGB")))
    n += 1
gravar.fechar()
print(f"ok · {n} quadros · {e.rel(SAIDA)}")
