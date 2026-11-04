#!/usr/bin/env python3
"""Legenda palavra a palavra queimada no vídeo.

Uso:
  .venv/bin/python .claude/skills/legenda/legenda.py <video> <palavras.json> <pasta-de-saida> [opções]

Opções:
  --por-vez 3             até quantas palavras aparecem juntas
  --chaves "café,aurora"  palavras-chave que ganham a cor de destaque
  --cor-chave "#FFD23F"   cor das palavras-chave
  --estilo luz|caixa      luz: a palavra falada acende e as outras ficam apagadas (padrão)
                          caixa: a palavra falada ganha uma caixa colorida atrás
  --cor-caixa "#FF5A36"   cor da caixa no estilo caixa
  --tamanho 80            altura da letra em px num vídeo de 1080 de largura (mínimo 34)
  --altura 0.62           centro da legenda, em fração da altura do vídeo (0 = topo, 1 = base)
  --caixa-alta            tudo em maiúsculas
  --fonte <arquivo.ttf>   outra fonte (padrão: Montserrat ExtraBold, licença OFL, em assets/fontes)

Gera na pasta: legendado.mp4, legenda.srt (para subir junto, se quiser) e conferencia-legenda.jpg
(seis quadros com as linhas da área segura do 9:16 desenhadas, só na conferência).
A legenda nunca sai da faixa segura: no 9:16 o texto fica entre y 250 e y 1560 (os botões do Instagram ficam embaixo).
"""
import io, json, os, re, subprocess, sys, unicodedata
import numpy as np
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Falta o Pillow. Instale com:  .venv/bin/pip install pillow")

args = sys.argv[1:]
def opt(nome, padrao=None, flag=False):
    if nome in args:
        i = args.index(nome)
        if flag:
            args.pop(i); return True
        v = args[i + 1]; del args[i:i + 2]; return v
    return False if flag else padrao
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
POR_VEZ = max(1, int(opt("--por-vez", 3)))
CHAVES_TXT = opt("--chaves", "")
COR_CHAVE = opt("--cor-chave", "#FFD23F")
ESTILO = opt("--estilo", "luz")
COR_CAIXA = opt("--cor-caixa", "#FF5A36")
TAMANHO = float(opt("--tamanho", 80))
ALTURA = float(opt("--altura", 0.62))
CAIXA_ALTA = opt("--caixa-alta", flag=True)
FONTE = opt("--fonte", os.path.join(RAIZ, "assets", "fontes", "montserrat", "Montserrat-ExtraBold.ttf"))
if len(args) < 3:
    print(__doc__); sys.exit(1)
ENTRADA, PALAVRAS, PASTA = os.path.abspath(args[0]), os.path.abspath(args[1]), os.path.abspath(args[2])
os.makedirs(PASTA, exist_ok=True)
SAIDA = os.path.join(PASTA, "legendado.mp4")

# ---------- vídeo ----------
sonda = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", ENTRADA],
                                  capture_output=True, text=True, check=True).stdout)
v = next(s for s in sonda["streams"] if s["codec_type"] == "video")
W, H = v["width"], v["height"]
num, den = map(int, v.get("r_frame_rate", "30/1").split("/"))
FPS = num / den
DUR = float(sonda["format"]["duration"])
tem_audio = any(s["codec_type"] == "audio" for s in sonda["streams"])

# área segura: no 9:16 de 1920 de altura, texto entre y 250 e y 1560 (proporcional em outros tamanhos)
TOPO, BASE = 250 / 1920 * H, 1560 / 1920 * H
escala = W / 1080
PISO = 34 * escala
tam = TAMANHO * escala
if tam < PISO:
    print(f"Aviso: {TAMANHO:.0f} px está abaixo do piso de 34 px; usando 34.")
    tam = PISO
LARG_MAX = W * 0.84


def cor(hexa, alfa=255):
    hexa = hexa.lstrip("#")
    return tuple(int(hexa[i:i + 2], 16) for i in (0, 2, 4)) + (alfa,)


def sem_acento(t):
    return unicodedata.normalize("NFD", t.lower()).encode("ascii", "ignore").decode()


CHAVES = {re.sub(r"[^a-z0-9]", "", sem_acento(c)) for c in CHAVES_TXT.split(",") if c.strip()}

# ---------- palavras em blocos ----------
pal = [p for p in json.load(open(PALAVRAS)) if p["w"].strip()]
if not pal:
    sys.exit("palavras.json está vazio.")
for p in pal:
    t = p["w"].strip()
    t = re.sub(r"[.,;:]+$", "", t)                  # tira ponto e vírgula do fim; mantém ? e !
    p["txt"] = t.upper() if CAIXA_ALTA else t
    p["chave"] = re.sub(r"[^a-z0-9]", "", sem_acento(t)) in CHAVES
blocos, atual = [], []
for i, p in enumerate(pal):
    if atual and (len(atual) >= POR_VEZ or re.search(r"[.!?;:,]$", pal[i - 1]["w"]) or p["s"] - pal[i - 1]["e"] > 0.5):
        blocos.append(atual); atual = []
    atual.append(p)
if atual:
    blocos.append(atual)
for k, b in enumerate(blocos):
    b_ini = b[0]["s"]
    prox = blocos[k + 1][0]["s"] if k + 1 < len(blocos) else DUR
    b_fim = prox if prox - b[-1]["e"] < 0.6 else b[-1]["e"] + 0.25
    blocos[k] = dict(palavras=b, ini=b_ini, fim=min(b_fim, DUR))

# ---------- desenho ----------
def fonte(t):
    return ImageFont.truetype(FONTE, int(round(t)))


def desenha(bloco, ativa, pop, t_letra):
    """Desenha um bloco; 'ativa' é o índice da palavra falada e 'pop' (0..1) o tamanho extra dela."""
    f = fonte(t_letra)
    espaco = f.getlength(" ")
    contorno = max(2, int(t_letra * 0.09))
    larguras = [f.getlength(p["txt"]) for p in bloco["palavras"]]
    # quebra em linhas que cabem na largura
    linhas, linha, larg = [], [], 0
    for i, lw in enumerate(larguras):
        if linha and larg + espaco + lw > LARG_MAX:
            linhas.append(linha); linha, larg = [], 0
        larg += (espaco if linha else 0) + lw
        linha.append(i)
    linhas.append(linha)
    alt_linha = t_letra * 1.18
    folga = int(t_letra * 0.5)
    lw_max = max(sum(larguras[i] for i in ln) + espaco * (len(ln) - 1) for ln in linhas)
    img = Image.new("RGBA", (int(lw_max + 2 * folga), int(alt_linha * len(linhas) + 2 * folga)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for n, ln in enumerate(linhas):
        largura_ln = sum(larguras[i] for i in ln) + espaco * (len(ln) - 1)
        x = folga + (lw_max - largura_ln) / 2
        y = folga + n * alt_linha
        for i in ln:
            p = bloco["palavras"][i]
            falada = i == ativa
            base = COR_CHAVE if p["chave"] else "#FFFFFF"
            if ESTILO == "caixa":
                alfa = 255
                if falada:
                    m = t_letra * 0.14
                    d.rounded_rectangle([x - m, y - m * 0.4, x + larguras[i] + m, y + t_letra * 1.08 + m * 0.4],
                                        radius=t_letra * 0.22, fill=cor(COR_CAIXA))
            else:
                alfa = 255 if falada else 165
            if falada and pop > 0:
                # a palavra falada nasce um pouco maior e assenta em 3 quadros
                fp = fonte(t_letra * (1 + 0.12 * pop))
                dx = (fp.getlength(p["txt"]) - larguras[i]) / 2
                d.text((x - dx, y - t_letra * 0.06 * pop), p["txt"], font=fp, fill=cor(base, alfa),
                       stroke_width=contorno, stroke_fill=(0, 0, 0, 235))
            else:
                d.text((x, y), p["txt"], font=f, fill=cor(base, alfa), stroke_width=contorno,
                       stroke_fill=(0, 0, 0, 235))
            x += larguras[i] + espaco
    return img


# confere se o bloco mais alto cabe na faixa segura; se não couber, diminui a letra (sem passar do piso)
alto = max(blocos, key=lambda b: len(b["palavras"]))
while tam > PISO and desenha(alto, 0, 0, tam).height > (BASE - TOPO):
    tam *= 0.92
tam = max(tam, PISO)

cache = {}
def imagem(k, ativa, pop):
    chave = (k, ativa, round(pop, 2))
    if chave not in cache:
        img = desenha(blocos[k], ativa, pop, tam)
        x = int((W - img.width) / 2)
        y = int(ALTURA * H - img.height / 2)
        y = int(min(max(y, TOPO - tam * 0.5), BASE + tam * 0.5 - img.height))   # a folga do desenho não conta como texto
        a = np.asarray(img, dtype=np.float32)
        cache[chave] = (x, y, a[..., :3], a[..., 3:] / 255.0)
        if len(cache) > 400:
            cache.pop(next(iter(cache)))
    return cache[chave]


# ---------- quadro a quadro ----------
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", ENTRADA, "-map", "0:v:0", "-vf",
                        "scale=in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24", "-f", "rawvideo", "-"],
                       stdout=subprocess.PIPE)
enc_cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", f"{num}/{den}", "-i", "-"]
if tem_audio:
    enc_cmd += ["-i", ENTRADA, "-map", "0:v", "-map", "1:a:0", "-c:a", "copy"]
enc_cmd += ["-vf", "scale=out_color_matrix=bt709:in_range=pc:out_range=tv,format=yuv420p",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
            "-movflags", "+faststart", "-shortest", SAIDA]
enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE)
tam_q = W * H * 3
k_bloco, n = 0, 0
while True:
    buf = dec.stdout.read(tam_q)
    if len(buf) < tam_q:
        break
    t = n / FPS
    while k_bloco + 1 < len(blocos) and blocos[k_bloco + 1]["ini"] <= t:
        k_bloco += 1
    b = blocos[k_bloco]
    if b["ini"] <= t < b["fim"]:
        ativa = 0
        for i, p in enumerate(b["palavras"]):
            if p["s"] <= t:
                ativa = i
        desde = t - b["palavras"][ativa]["s"]
        pop = max(0.0, 1 - desde / (3 / FPS)) if desde >= 0 else 0.0
        x, y, rgb, alfa = imagem(k_bloco, ativa, pop)
        q = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy()
        # recorta o pedaço da legenda que cai dentro do quadro
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + rgb.shape[1], W), min(y + rgb.shape[0], H)
        if x1 > x0 and y1 > y0:
            r = rgb[y0 - y:y1 - y, x0 - x:x1 - x]; a = alfa[y0 - y:y1 - y, x0 - x:x1 - x]
            fundo = q[y0:y1, x0:x1].astype(np.float32)
            q[y0:y1, x0:x1] = (fundo * (1 - a) + r * a + 0.5).astype(np.uint8)
        buf = q.tobytes()
    enc.stdin.write(buf)
    n += 1
enc.stdin.close(); enc.wait(); dec.wait()
if enc.returncode != 0:
    sys.exit("O ffmpeg falhou ao gravar o vídeo legendado.")

# ---------- SRT ----------
def ts(s):
    ms = int(round(s * 1000)); return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
with open(os.path.join(PASTA, "legenda.srt"), "w") as f:
    for k, b in enumerate(blocos, 1):
        f.write(f"{k}\n{ts(b['ini'])} --> {ts(b['fim'])}\n{' '.join(p['txt'] for p in b['palavras'])}\n\n")

# ---------- conferência: 6 quadros com as linhas da faixa segura ----------
meios = [blocos[int(i)] for i in np.linspace(0, len(blocos) - 1, 6)]
quadros = []
for b in meios:
    t = (b["ini"] + b["fim"]) / 2
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", SAIDA, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                       capture_output=True, check=True)
    im = Image.open(io.BytesIO(r.stdout)).convert("RGB")
    d = ImageDraw.Draw(im)
    for yy in (TOPO, BASE):
        d.line([(0, yy), (W, yy)], fill=(255, 40, 40), width=max(2, int(4 * escala)))
    quadros.append(im.resize((W // 3, H // 3)))
folha = Image.new("RGB", (W // 3 * 3, H // 3 * 2), "black")
for i, im in enumerate(quadros):
    folha.paste(im, ((i % 3) * (W // 3), (i // 3) * (H // 3)))
folha.save(os.path.join(PASTA, "conferencia-legenda.jpg"), quality=85)
print(f"ok · {len(blocos)} blocos · letra {tam / escala:.0f} px (em 1080) · {SAIDA}")
print(f"Confira: {os.path.join(PASTA, 'conferencia-legenda.jpg')} (linhas vermelhas = limite da faixa segura)")
