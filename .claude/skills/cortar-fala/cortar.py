#!/usr/bin/env python3
"""Corte bruto pela fala: tira silêncio, vício (ahn, hã, hum...) e take repetido, sempre entre palavras.

Uso:
  .venv/bin/python .claude/skills/cortar-fala/cortar.py <video> <pasta-de-saida> [opções]

Opções:
  --pausa 0.35            pausa maior que isso é encurtada (segundos)
  --manter-vicios         não tira ahn, hã, hum...
  --manter-repeticoes     não tira take repetido
  --nomes "Café Aurora"   ajuda a transcrição a escrever nomes e marcas
  --retranscrever         transcreve de novo mesmo se já existir palavras-original.json

Gera na pasta:
  palavras-original.json  transcrição do vídeo inteiro (tempo do original)
  cortado.mp4             o vídeo cortado (mesma resolução e qps do original)
  palavras.json           palavras no tempo do vídeo CORTADO (é a que a legenda e as transições usam)
  corte.json              trechos mantidos e o que saiu, com o motivo
  relatorio.md            o que ficou e o que saiu, para conferir

Regras: corta sempre entre palavras; o ponto exato é o silêncio medido pela energia do áudio
(o fim que o Whisper dá costuma vir cedo); "né", "tipo" e "então" ficam; take repetido fica só a última vez.
"""
import json, os, re, subprocess, sys, wave
import numpy as np

args = sys.argv[1:]
def opt(nome, padrao=None, flag=False):
    if nome in args:
        i = args.index(nome)
        if flag:
            args.pop(i); return True
        v = args[i + 1]; del args[i:i + 2]; return v
    return False if flag else padrao
PAUSA = float(opt("--pausa", 0.35))
MANTER_VICIOS = opt("--manter-vicios", flag=True)
MANTER_REP = opt("--manter-repeticoes", flag=True)
NOMES = opt("--nomes", "")
RETRANSCREVER = opt("--retranscrever", flag=True)
if len(args) < 2:
    print(__doc__); sys.exit(1)
ENTRADA, PASTA = os.path.abspath(args[0]), os.path.abspath(args[1])
os.makedirs(PASTA, exist_ok=True)
P = lambda n: os.path.join(PASTA, n)
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SR = 48000

# ---------- 1) dados do vídeo ----------
sonda = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", ENTRADA],
                                  capture_output=True, text=True, check=True).stdout)
vid = next(s for s in sonda["streams"] if s["codec_type"] == "video")
if not any(s["codec_type"] == "audio" for s in sonda["streams"]):
    sys.exit("Este vídeo não tem áudio: não dá para cortar pela fala.")
num, den = map(int, vid.get("r_frame_rate", "30/1").split("/"))
FPS = num / den
if vid.get("color_transfer") in ("arib-std-b67", "smpte2084"):
    print("Aviso: o vídeo ainda é HDR. Converta antes com /converter-iphone para as cores não lavarem.")

# ---------- 2) áudio e energia (janelas de 10 ms) ----------
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", ENTRADA, "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.float32).reshape(-1, 2).copy()
mono = audio.mean(axis=1)
DUR = len(mono) / SR
hop = SR // 100
n_jan = len(mono) // hop
db = 20 * np.log10(np.sqrt((mono[:n_jan * hop].reshape(n_jan, hop) ** 2).mean(axis=1)) + 1e-9)
piso = float(np.percentile(db, 5))                 # ruído de fundo do próprio vídeo
LIM = min(max(-50.0, piso + 6), float(np.median(db)) - 12)   # abaixo disso é silêncio

# ---------- 3) transcrição palavra a palavra ----------
orig = P("palavras-original.json")
if RETRANSCREVER or not os.path.exists(orig):
    cmd = [sys.executable, os.path.join(RAIZ, "ferramentas", "transcrever.py"), ENTRADA, orig]
    if NOMES:
        cmd += ["--nomes", NOMES]
    subprocess.run(cmd, check=True)
else:
    print("Usando a transcrição que já existe (palavras-original.json). Para refazer: --retranscrever")
PAL = json.load(open(orig))


def transcreve_trecho(a, b):
    """Transcreve só o trecho a–b (em segundos) e devolve as palavras no tempo do vídeo."""
    wav_t, json_t = P("_trecho.wav"), P("_trecho.json")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", ENTRADA,
                    "-vn", "-ac", "1", "-ar", "16000", wav_t], check=True)
    cmd = [sys.executable, os.path.join(RAIZ, "ferramentas", "transcrever.py"), wav_t, json_t]
    if NOMES:
        cmd += ["--nomes", NOMES]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    novas = [dict(w=p["w"], s=round(p["s"] + a, 3), e=round(p["e"] + a, 3)) for p in json.load(open(json_t))]
    os.remove(wav_t); os.remove(json_t)
    return novas


def falas_em(a, b):
    """Divide a–b nos silêncios de 0,35 s ou mais e devolve os pedaços com fala."""
    ja, jb = int(a * 100), min(int(b * 100), n_jan)
    fala = db[ja:jb] > LIM
    pedacos, ini, quietos = [], None, 0
    for k, f in enumerate(fala):
        if f:
            if ini is None: ini = k
            quietos = 0
        elif ini is not None:
            quietos += 1
            if quietos >= 35:
                pedacos.append((ini, k - quietos + 1)); ini = None; quietos = 0
    if ini is not None:
        pedacos.append((ini, len(fala)))
    return [(max(0, a + i / 100 - 0.1), min(DUR, a + f / 100 + 0.1)) for i, f in pedacos if f - i >= 15]


# O Whisper às vezes "engole" um take repetido: escreve a frase uma vez só e estica uma palavra por cima
# da repetição. Onde isso aparece (palavra longa demais ou fala sem palavra), transcreve de novo em pedaços.
suspeitos = []
for i, p in enumerate(PAL):
    if p["e"] - p["s"] > 1.3:
        a = PAL[i - 1]["e"] if i > 0 else 0.0
        b = min(PAL[i + 1]["s"] if i + 1 < len(PAL) else DUR, p["e"] + 0.3)
        suspeitos.append((a, b))
cobertura = np.zeros(n_jan, bool)
for p in PAL:
    cobertura[int(p["s"] * 100):int(p["e"] * 100) + 1] = True
fala_sem_palavra = (db > LIM) & ~cobertura
k = 0
while k < n_jan:
    if fala_sem_palavra[k]:
        f = k
        while f < n_jan and fala_sem_palavra[f]: f += 1
        if f - k >= 50:
            suspeitos.append((k / 100, f / 100))
        k = f
    else:
        k += 1
refeitos = 0
for a, b in sorted(suspeitos)[:6]:
    pedacos = falas_em(a, b)
    if len(pedacos) < 1:
        continue
    novas = []
    for pa, pb in pedacos:
        novas += transcreve_trecho(pa, pb)
    if novas:
        PAL = [p for p in PAL if not (p["s"] >= a - 0.01 and p["e"] <= b + 0.01) and not (p["s"] < b and p["e"] > a and p["e"] - p["s"] > 1.3)]
        PAL = sorted(PAL + novas, key=lambda p: p["s"])
        refeitos += 1
if refeitos:
    print(f"Retranscrevi {refeitos} trecho(s) suspeito(s) em pedaços (possível take repetido).")
# junta pedaços que o Whisper separa: "R" "$" "3" ",00" → "R$ 3,00"
jun = []
for p in PAL:
    if jun and ((p["w"] == "$" and jun[-1]["w"] in ("R", "r")) or (re.match(r"^,\d", p["w"]) and re.search(r"\d$", jun[-1]["w"]))):
        jun[-1]["w"] += p["w"]; jun[-1]["e"] = p["e"]
    elif jun and jun[-1]["w"].endswith("$") and re.match(r"^\d", p["w"]):
        jun[-1]["w"] += " " + p["w"]; jun[-1]["e"] = p["e"]
    else:
        jun.append(dict(p))
PAL = jun
if not PAL:
    sys.exit("A transcrição não achou nenhuma palavra.")

# ---------- 4) o que sai ----------
def limpa(w):
    return re.sub(r"[^\wáàâãéêíóôõúç]", "", w.lower())

# vícios: só sons de hesitação. "um" (artigo) e "há" (verbo) NÃO entram.
VICIO = re.compile(r"^(a+h+n*|ã+h*n*|h+ã+|h+u+m+|h+m+|e+h+|é{2,}|e{3,}|u+h+m*|ã{2,}|a{3,})$")
fora = [None] * len(PAL)
if not MANTER_VICIOS:
    for i, p in enumerate(PAL):
        if VICIO.match(limpa(p["w"])):
            fora[i] = "vício"
if not MANTER_REP:
    toks = [limpa(p["w"]) for p in PAL]
    i = 0
    while i < len(PAL):
        achou = False
        for n in (6, 5, 4, 3):
            if i + n > len(PAL) or not all(toks[i:i + n]):
                continue
            for j in range(i + 1, len(PAL) - n + 1):
                if PAL[j]["s"] - PAL[i]["s"] > 8:
                    break
                if toks[j:j + n] == toks[i:i + n]:      # o mesmo começo volta em até 8 s: o anterior era take ruim
                    for k in range(i, j):
                        fora[k] = fora[k] or "take repetido"
                    achou = j
                    break
            if achou:
                break
        i = achou if achou else i + 1             # segue a partir do take que ficou


# ---------- 5) pontos de corte pela energia ----------
def janela(t):
    return int(np.clip(round(t * 100), 0, n_jan - 1))

def corte_antes(t_ini, limite):
    """Recua do começo da palavra até achar silêncio (no máx. 0,25 s, nunca antes de 'limite')."""
    j = janela(t_ini); minimo = max(janela(limite), j - 25)
    while j > minimo and db[j - 1] > LIM:
        j -= 1
    return max(j / 100 - 0.05, limite)

def corte_depois(t_fim, limite):
    """Avança do fim da palavra até 80 ms de silêncio (no máx. 0,6 s, nunca depois de 'limite')."""
    j = janela(t_fim); maximo = min(janela(limite), j + 60, n_jan - 8)
    while j < maximo and not (db[j:j + 8] < LIM).all():
        j += 1
    return min(j / 100 + 0.05, limite)

trechos, atual = [], None
for i, p in enumerate(PAL):
    if fora[i]:
        if atual: trechos.append(atual); atual = None
        continue
    if atual and p["s"] - PAL[atual[-1]]["e"] > PAUSA:
        trechos.append(atual); atual = None
    atual = (atual or []) + [i]
if atual:
    trechos.append(atual)

seg = []
for tr in trechos:
    i0, i1 = tr[0], tr[-1]
    esq = PAL[i0 - 1]["e"] + 0.02 if i0 > 0 else 0.0
    dir_ = PAL[i1 + 1]["s"] - 0.02 if i1 + 1 < len(PAL) else DUR
    a = corte_antes(PAL[i0]["s"], min(esq, PAL[i0]["s"]))
    b = corte_depois(PAL[i1]["e"], max(dir_, PAL[i1]["e"]))
    # encaixa no quadro mais próximo, para som e imagem não se desencontrarem
    a = round(a * FPS) / FPS; b = round(b * FPS) / FPS
    if b - a >= 1 / FPS:
        seg.append([a, min(b, DUR), list(tr)])
uni = []
for a, b, tr in seg:
    if uni and a <= uni[-1][1] + 0.5 / FPS:
        uni[-1][1] = max(uni[-1][1], b); uni[-1][2] += tr
    else:
        uni.append([a, b, tr])

# ---------- 6) palavras no tempo do vídeo cortado ----------
novas, t0 = [], 0.0
for a, b, tr in uni:
    for i in tr:
        p = PAL[i]
        novas.append(dict(w=p["w"], s=round(t0 + max(0.0, p["s"] - a), 3), e=round(t0 + min(b - a, p["e"] - a), 3)))
    t0 += b - a
json.dump(novas, open(P("palavras.json"), "w"), ensure_ascii=False, indent=0)
json.dump(dict(original=os.path.basename(ENTRADA), fps=round(FPS, 3), duracao_original=round(DUR, 3), duracao=round(t0, 3),
               silencio_db=round(LIM, 1), trechos=[dict(de=round(a, 3), ate=round(b, 3)) for a, b, _ in uni],
               fora=[dict(palavra=PAL[i]["w"], s=PAL[i]["s"], motivo=fora[i]) for i in range(len(PAL)) if fora[i]]),
          open(P("corte.json"), "w"), ensure_ascii=False, indent=1)

# ---------- 7) áudio cortado (emendas com 10 ms de fade) e vídeo pelos mesmos tempos ----------
fade = int(0.010 * SR)
rampa = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
pedacos = []
for a, b, _ in uni:
    x = audio[int(round(a * SR)):int(round(b * SR))].copy()
    if len(x) > 2 * fade:
        x[:fade] *= rampa; x[-fade:] *= rampa[::-1]
    pedacos.append(x)
cortado = np.concatenate(pedacos)
wav = P("_audio-cortado.wav")
with wave.open(wav, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(np.clip(np.round(cortado * 32767), -32768, 32767).astype("<i2").tobytes())

expr = "+".join(f"between(n,{int(round(a * FPS))},{int(round(b * FPS)) - 1})" for a, b, _ in uni)
filtro = f"fps={num}/{den},select='{expr}',setpts=N/({num}/{den})/TB"
cor = ["-color_primaries", vid.get("color_primaries", "bt709"), "-color_trc", vid.get("color_transfer", "bt709"),
       "-colorspace", vid.get("color_space", "bt709")] if vid.get("color_transfer") else []
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ENTRADA, "-i", wav, "-map", "0:v:0", "-map", "1:a:0", "-vf", filtro,
                "-fps_mode", "cfr", "-r", f"{num}/{den}", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
                *cor, "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", P("cortado.mp4")], check=True)
os.remove(wav)

# ---------- 8) relatório ----------
dur_final = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", P("cortado.mp4")],
                                 capture_output=True, text=True).stdout.strip() or 0)
txt = lambda ids: " ".join(PAL[i]["w"] for i in ids)
saiu = [i for i in range(len(PAL)) if fora[i]]
rel = [f"# Corte pela fala · {DUR:.1f} s → {t0:.1f} s ({len(uni)} trechos)", "",
       f"Silêncio medido: piso {piso:.0f} dB, limite {LIM:.0f} dB. Pausa máxima mantida: {PAUSA} s.",
       f"Duração do cortado.mp4: {dur_final:.2f} s (esperado {t0:.2f} s).", "", "## O que ficou"]
rel += [f"- {a:6.2f}–{b:6.2f}  {txt(tr)}" for a, b, tr in uni]
rel += ["", "## O que saiu (palavras)"]
rel += [f"- {PAL[i]['s']:6.2f}  “{PAL[i]['w']}”  ({fora[i]})" for i in saiu] or ["- só pausas"]
rel += ["", "Confira ouvindo as emendas. O Whisper às vezes não escreve o \"ahn\": se sobrar algum, diga em que segundo está."]
open(P("relatorio.md"), "w").write("\n".join(rel) + "\n")
print(f"ok · {DUR:.1f} s → {t0:.1f} s · {len(uni)} trechos · {len(saiu)} palavras fora · {P('relatorio.md')}")
