#!/usr/bin/env python3
"""Transições na hora da fala: chicote, zoom-soco e flash, cada um com o seu som.

Uso:
  .venv/bin/python .claude/skills/transicoes/transicoes.py <video> <palavras.json> <pasta-de-saida> \\
      --chicote "nota cinco" --zoom "segurança" --flash "valeu" [opções]

Cada --chicote / --zoom / --flash recebe o trecho falado ("quando eu digo X") e pode se repetir.
O efeito cai no começo da primeira palavra do trecho.

Opções:
  --todas               aplica em todas as vezes que o trecho aparece (padrão: só a primeira)
  --sem-som             não mistura os efeitos sonoros (só grava eventos.json para a skill som)
  --segura 0.7          quanto tempo o zoom-soco fica aproximado (segundos)
  --forca-zoom 1.22     quanto o zoom-soco aproxima
  --centro-zoom 0.5,0.42  ponto que o zoom mira (fração da largura, da altura); 0.42 é onde o rosto costuma ficar no 9:16

Gera na pasta: transicoes.mp4, eventos.json (efeitos e sons com o tempo), relatorio.md
e conferencia/<n>-<efeito>.jpg (quadros em volta de cada efeito, para olhar).
O vídeo não muda de duração: palavras.json continua valendo.
"""
import difflib, json, os, re, subprocess, sys, unicodedata
import numpy as np
try:
    from PIL import Image
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
def opts(nome):
    vals = []
    while nome in args:
        i = args.index(nome); vals.append(args[i + 1]); del args[i:i + 2]
    return vals
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SONS = os.path.join(RAIZ, "assets", "sons")
PEDIDOS = [("chicote", t) for t in opts("--chicote")] + [("zoom", t) for t in opts("--zoom")] + [("flash", t) for t in opts("--flash")]
TODAS = opt("--todas", flag=True)
SEM_SOM = opt("--sem-som", flag=True)
SEGURA = float(opt("--segura", 0.7))
FORCA = float(opt("--forca-zoom", 1.22))
CX, CY = map(float, opt("--centro-zoom", "0.5,0.42").split(","))
if len(args) < 3 or not PEDIDOS:
    print(__doc__); sys.exit(1)
ENTRADA, PALAVRAS, PASTA = os.path.abspath(args[0]), os.path.abspath(args[1]), os.path.abspath(args[2])
os.makedirs(os.path.join(PASTA, "conferencia"), exist_ok=True)
SAIDA = os.path.join(PASTA, "transicoes.mp4")

# som de cada efeito e o volume em relação à voz (dB): negativo = abaixo da voz
SOM = {"chicote": ("whoosh", -4.0), "zoom": ("impacto", -2.0), "flash": ("brilho", -7.0)}
KIT = json.load(open(os.path.join(SONS, "kit.json")))

sonda = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", ENTRADA],
                                  capture_output=True, text=True, check=True).stdout)
v = next(s for s in sonda["streams"] if s["codec_type"] == "video")
W, H = v["width"], v["height"]
num, den = map(int, v.get("r_frame_rate", "30/1").split("/"))
FPS = num / den
DUR = float(sonda["format"]["duration"])
tem_audio = any(s["codec_type"] == "audio" for s in sonda["streams"])


def lufs(arquivo):
    """Loudness integrada (LUFS) do áudio do arquivo, medida pelo ffmpeg."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", arquivo, "-map", "0:a:0", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None
VOZ = (lufs(ENTRADA) if tem_audio else None) or -16.0
if VOZ < -60:
    VOZ = -16.0

# ---------- acha os trechos na transcrição ----------
def limpa(t):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", t.lower()).encode("ascii", "ignore").decode())
NUMEROS = {"zero": "0", "um": "1", "uma": "1", "dois": "2", "duas": "2", "tres": "3", "quatro": "4", "cinco": "5",
           "seis": "6", "sete": "7", "oito": "8", "nove": "9", "dez": "10"}
def token(t):
    t = limpa(t)
    return NUMEROS.get(t, t)

pal = json.load(open(PALAVRAS))
toks = [token(p["w"]) for p in pal]
eventos, faltou = [], []
for efeito, texto in PEDIDOS:
    alvo = [token(t) for t in texto.split() if token(t)]
    achados = [i for i in range(len(toks) - len(alvo) + 1) if alvo and toks[i:i + len(alvo)] == alvo]
    if not achados:
        perto = difflib.get_close_matches(texto.lower(), [" ".join(p["w"] for p in pal[i:i + len(alvo)]).lower()
                                                          for i in range(len(pal))], n=3, cutoff=0.5)
        faltou.append((efeito, texto, perto))
        continue
    for i in (achados if TODAS else achados[:1]):
        som, db = SOM[efeito]
        eventos.append(dict(efeito=efeito, quando=texto, t=round(pal[i]["s"], 3), som=som, db=db))
eventos.sort(key=lambda e: e["t"])
if not eventos:
    for efeito, texto, perto in faltou:
        print(f"Não achei \"{texto}\" na fala." + (f" Parecidos: {', '.join(perto)}" if perto else ""))
    sys.exit(1)

# ---------- os efeitos (por quadro) ----------
D_CHICOTE = 0.30             # duração do chicote; o meio (mais borrado) cai no tempo da palavra
def suave(u):                # começa e termina devagar, rápido no meio
    u = np.clip(u, 0, 1); return u * u * u * (u * (6 * u - 15) + 10)

def chicote(q, t, t0):
    u0 = (t - 0.5 / FPS - (t0 - D_CHICOTE / 2)) / D_CHICOTE
    u1 = (t + 0.5 / FPS - (t0 - D_CHICOTE / 2)) / D_CHICOTE
    if u1 <= 0 or u0 >= 1:
        return q
    x0, x1 = W * suave(u0), W * suave(u1)                 # a imagem anda para a esquerda e volta pela direita
    L = max(1, int(round(x1 - x0)))                       # borrão = quanto andou durante o quadro
    meio = int(round((x0 + x1) / 2))
    img = np.roll(q, -meio, axis=1).astype(np.float32)
    if L > 1:
        ext = np.concatenate([img[:, -L // 2:], img, img[:, :L - L // 2]], axis=1)
        c = np.cumsum(ext, axis=1, dtype=np.float64)
        c = np.concatenate([np.zeros((H, 1, 3)), c], axis=1)
        img = ((c[:, L:L + W] - c[:, :W]) / L).astype(np.float32)
    return np.clip(img, 0, 255).astype(np.uint8)

def escala_zoom(t, t0):
    d = t - t0 + 1 / FPS                                 # começa um quadro antes: na palavra já está quase todo
    if d < 0 or d > SEGURA + 0.25:
        return 1.0
    if d < 2 / FPS:                                      # entra em 2 quadros: é o "soco"
        return 1 + (FORCA - 1) * (1 - (1 - d / (2 / FPS)) ** 2)
    if d < SEGURA:
        return FORCA + 0.015 * (d - 2 / FPS) / SEGURA    # continua aproximando bem pouco: não fica parado
    return 1 + (FORCA + 0.015 - 1) * (1 - suave((d - SEGURA) / 0.25))

def zoom(q, s):
    if s <= 1.0001:
        return q
    w, h = W / s, H / s
    x0 = min(max(CX * W - w / 2, 0), W - w); y0 = min(max(CY * H - h / 2, 0), H - h)
    return np.asarray(Image.fromarray(q).resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h)))

def forca_flash(t, t0):
    d = t - t0
    if d < -1 / FPS or d > 0.45:
        return 0.0
    if d < 0:
        return 0.45                                       # um quadro antes já clareia
    return 0.9 * np.exp(-d / 0.11)

def flash(q, a):
    if a <= 0.003:
        return q
    return (q.astype(np.float32) * (1 - a) + 255 * a + 0.5).astype(np.uint8)

ativos = [(e["efeito"], e["t"]) for e in eventos]
def precisa(t):
    for ef, t0 in ativos:
        if ef == "chicote" and abs(t - t0) <= D_CHICOTE / 2 + 1 / FPS: return True
        if ef == "zoom" and -1 / FPS <= t - t0 <= SEGURA + 0.3: return True
        if ef == "flash" and -2 / FPS <= t - t0 <= 0.5: return True
    return False

# quadros para a conferência: em volta de cada efeito
olhar = {}
for k, e in enumerate(eventos):
    n0 = int(round(e["t"] * FPS))
    for d in (-3, -1, 0, 1, 2, 4, 8):
        olhar.setdefault(n0 + d, []).append(k)
miniaturas = {k: [] for k in range(len(eventos))}

dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", ENTRADA, "-map", "0:v:0", "-vf",
                        "scale=in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24", "-f", "rawvideo", "-"],
                       stdout=subprocess.PIPE)
video_tmp = os.path.join(PASTA, "_imagem.mp4")
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", f"{num}/{den}",
                        "-i", "-", "-vf", "scale=out_color_matrix=bt709:in_range=pc:out_range=tv,format=yuv420p",
                        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-colorspace", "bt709", "-color_range", "tv", video_tmp], stdin=subprocess.PIPE)
tam_q, n = W * H * 3, 0
while True:
    buf = dec.stdout.read(tam_q)
    if len(buf) < tam_q:
        break
    t = n / FPS
    if precisa(t):
        q = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        for ef, t0 in ativos:
            if ef == "zoom": q = zoom(q, escala_zoom(t, t0))
        for ef, t0 in ativos:
            if ef == "chicote": q = chicote(q, t, t0)
        for ef, t0 in ativos:
            if ef == "flash": q = flash(q, forca_flash(t, t0))
        buf = np.ascontiguousarray(q).tobytes()
    if n in olhar:
        mini = Image.frombytes("RGB", (W, H), buf).resize((W // 4, H // 4))
        for k in olhar[n]:
            miniaturas[k].append(mini)
    enc.stdin.write(buf)
    n += 1
enc.stdin.close(); enc.wait(); dec.wait()
if enc.returncode != 0:
    sys.exit("O ffmpeg falhou ao gravar a imagem.")

# ---------- som ----------
json.dump(eventos, open(os.path.join(PASTA, "eventos.json"), "w"), ensure_ascii=False, indent=1)
cmd = ["ffmpeg", "-v", "error", "-y", "-i", video_tmp]
if tem_audio:
    cmd += ["-i", ENTRADA]
if SEM_SOM or not eventos:
    cmd += ["-map", "0:v"] + (["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"] if tem_audio else [])
else:
    filtros, rotulos = [], []
    base = 2 if tem_audio else 1
    for k, e in enumerate(eventos):
        info = KIT[e["som"]]
        cmd += ["-i", os.path.join(SONS, info["arquivo"])]
        atraso = max(0, int(round((e["t"] - info["ponto"]) * 1000)))
        ganho = VOZ + e["db"] - info["lufs"]               # deixa o efeito "db" abaixo (ou acima) da voz
        filtros.append(f"[{base + k}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={atraso}|{atraso},volume={ganho:.1f}dB[s{k}]")
        rotulos.append(f"[s{k}]")
    voz = "[1:a]aresample=48000,aformat=channel_layouts=stereo[voz];" if tem_audio else ""
    entradas = ("[voz]" if tem_audio else "") + "".join(rotulos)
    n_ent = len(rotulos) + (1 if tem_audio else 0)
    mix = (f"{voz}{';'.join(filtros)};{entradas}amix=inputs={n_ent}:duration=first:normalize=0,alimiter=limit=0.89:level=false[a]"
           if tem_audio else f"{';'.join(filtros)};{entradas}amix=inputs={n_ent}:normalize=0,apad,atrim=0:{DUR:.3f}[a]")
    cmd += ["-filter_complex", mix, "-map", "0:v", "-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
cmd += ["-c:v", "copy", "-movflags", "+faststart", "-shortest", SAIDA]
subprocess.run(cmd, check=True)
os.remove(video_tmp)

# ---------- conferência e relatório ----------
for k, e in enumerate(eventos):
    ms = miniaturas[k]
    if ms:
        tira = Image.new("RGB", (ms[0].width * len(ms), ms[0].height))
        for i, m in enumerate(ms):
            tira.paste(m, (i * m.width, 0))
        tira.save(os.path.join(PASTA, "conferencia", f"{k + 1}-{e['efeito']}.jpg"), quality=85)
rel = [f"# Transições · {len(eventos)} efeito(s)", ""]
rel += [f"- {e['t']:6.2f} s  {e['efeito']} em \"{e['quando']}\" · som {e['som']} ({e['db']:+.0f} dB em relação à voz)" for e in eventos]
for efeito, texto, perto in faltou:
    rel.append(f"- NÃO ACHEI \"{texto}\" ({efeito})" + (f" · parecidos: {', '.join(perto)}" if perto else ""))
rel += ["", "Quadros de cada efeito em conferencia/ (3 quadros antes, o quadro do efeito e depois)."]
if SEM_SOM:
    rel.append("Sem som de efeito: use eventos.json na skill som.")
open(os.path.join(PASTA, "relatorio.md"), "w").write("\n".join(rel) + "\n")
print("\n".join(rel[2:2 + len(eventos) + len(faltou)]))
print(f"ok · {SAIDA}")
