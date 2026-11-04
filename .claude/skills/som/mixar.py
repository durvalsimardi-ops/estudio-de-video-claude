#!/usr/bin/env python3
"""Mixagem final: voz tratada + efeitos na hora dos eventos + trilha opcional com ducking, master em −14 LUFS.

Uso:
  .venv/bin/python .claude/skills/som/mixar.py <video> <pasta-de-saida> [opções]

Opções:
  --eventos eventos.json   efeitos: [{"t": 12.2, "som": "whoosh", "db": -4}] (pode repetir a opção)
                           "som" é um nome do kit (assets/sons/kit.json) ou o caminho de um .wav
                           "db" é o volume em relação à voz (−4 = 4 dB abaixo da voz); o "ponto" do kit cai em "t"
  --trilha musica.mp3      trilha de fundo (precisa ter licença); repete se for curta
  --trilha-db -14          volume da trilha em relação à voz, antes do ducking
  --sem-tratar-voz         não mexe na voz (sem filtro, sem compressor)
  --alvo -14               loudness final em LUFS (Instagram, TikTok e YouTube: −14)

Gera na pasta: mixado.mp4 (vídeo igual, som novo), mix.wav e relatorio-som.md com a medida final.
Pico final sempre ≤ −1 dBTP (o loudnorm roda em 2 passadas e, se o AAC passar do pico, o volume é corrigido).
"""
import json, os, re, subprocess, sys

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
EVENTOS = opts("--eventos")
TRILHA = opt("--trilha")
TRILHA_DB = float(opt("--trilha-db", -14))
SEM_TRATAR = opt("--sem-tratar-voz", flag=True)
ALVO = float(opt("--alvo", -14))
TP = -1.5                                   # alvo de pico do loudnorm: folga para o AAC ficar abaixo de −1 dBTP
if len(args) < 2:
    print(__doc__); sys.exit(1)
ENTRADA, PASTA = os.path.abspath(args[0]), os.path.abspath(args[1])
os.makedirs(PASTA, exist_ok=True)
P = lambda n: os.path.join(PASTA, n)
KIT = json.load(open(os.path.join(SONS, "kit.json")))


def roda(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ffmpeg falhou:\n" + r.stderr[-1500:])
    return r.stderr


def medida(arquivo, mapa="0:a:0"):
    """Loudness integrada, pico verdadeiro e LRA (ffmpeg ebur128)."""
    s = roda(["ffmpeg", "-hide_banner", "-nostats", "-i", arquivo, "-map", mapa, "-af", "ebur128=peak=true", "-f", "null", "-"])
    resumo = s[s.rfind("Summary:"):]
    pega = lambda rot: float(re.search(rot + r":\s+(-?[\d.]+|-inf)", resumo).group(1).replace("-inf", "-120"))
    return dict(I=pega("I"), TP=pega("Peak"), LRA=pega("LRA"))


sonda = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", ENTRADA],
                                  capture_output=True, text=True, check=True).stdout)
if not any(s["codec_type"] == "audio" for s in sonda["streams"]):
    sys.exit("Este vídeo não tem áudio para mixar.")
tem_video = any(s["codec_type"] == "video" for s in sonda["streams"])
DUR = float(sonda["format"]["duration"])
antes = medida(ENTRADA)

# ---------- 1) voz ----------
voz = P("_voz.wav")
if SEM_TRATAR:
    roda(["ffmpeg", "-v", "error", "-y", "-i", ENTRADA, "-map", "0:a:0", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s24le", voz])
else:
    ganho = -20 - antes["I"] if antes["I"] > -70 else 0      # leva a voz para ~−20 LUFS antes do compressor
    cadeia = (f"volume={ganho:.2f}dB,highpass=f=80,"           # tira ronco e grave de mesa
              "equalizer=f=250:t=q:w=1.2:g=-2,"                # menos "caixa" na voz
              "equalizer=f=3500:t=q:w=1.0:g=3,"                # presença: a voz chega na frente
              "deesser=i=0.3,"                                 # suaviza o "s"
              "acompressor=threshold=-22dB:ratio=2.5:attack=10:release=150:makeup=2dB")
    roda(["ffmpeg", "-v", "error", "-y", "-i", ENTRADA, "-map", "0:a:0", "-af", cadeia, "-ac", "2", "-ar", "48000", "-c:a", "pcm_s24le", voz])
VOZ_I = medida(voz)["I"]

# ---------- 2) efeitos ----------
eventos = []
for arq in EVENTOS:
    eventos += json.load(open(arq))
entradas, filtros, rotulos = ["-i", voz], [], []
desc_ev = []
for k, e in enumerate(eventos):
    nome = e["som"]
    if nome in KIT:
        caminho, ponto, lufs = os.path.join(SONS, KIT[nome]["arquivo"]), KIT[nome]["ponto"], KIT[nome]["lufs"]
    else:
        caminho, ponto = os.path.abspath(nome), float(e.get("ponto", 0))
        lufs = medida(caminho)["I"]
    db = float(e.get("db", -6))
    ganho = VOZ_I + db - lufs
    atraso = max(0, int(round((float(e["t"]) - ponto) * 1000)))
    entradas += ["-i", caminho]
    filtros.append(f"[{len(entradas) // 2 - 1}:a]aresample=48000,aformat=channel_layouts=stereo,volume={ganho:.1f}dB,adelay={atraso}|{atraso}[e{k}]")
    rotulos.append(f"[e{k}]")
    desc_ev.append(f"- {float(e['t']):6.2f} s  {os.path.basename(nome)}  ({db:+.0f} dB em relação à voz)")

# ---------- 3) trilha com ducking ----------
if TRILHA:
    entradas += ["-stream_loop", "-1", "-i", os.path.abspath(TRILHA)]
    idx = sum(1 for x in entradas if x == "-i") - 1
    t_lufs = medida(os.path.abspath(TRILHA))["I"]
    ganho_t = VOZ_I + TRILHA_DB - t_lufs
    filtros.append("[0:a]asplit=2[voz][chave]")
    filtros.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{DUR:.3f},volume={ganho_t:.1f}dB,"
                   f"afade=t=in:d=0.8,afade=t=out:st={max(0, DUR - 1.5):.3f}:d=1.5[tri]")
    # a voz aperta a trilha: quando alguém fala, a música abaixa sozinha (~8 dB) e volta nas pausas
    filtros.append("[tri][chave]sidechaincompress=threshold=0.02:ratio=8:attack=30:release=400:makeup=1[duck]")
    voz_rot, extra = "[voz]", ["[duck]"]
else:
    voz_rot, extra = "[0:a]", []
n_ent = 1 + len(rotulos) + len(extra)
grafo = ";".join(filtros + [f"{voz_rot}{''.join(rotulos)}{''.join(extra)}amix=inputs={n_ent}:duration=first:normalize=0[pre]"]) \
    if n_ent > 1 else "[0:a]anull[pre]"
pre = P("_pre.wav")
roda(["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex", grafo, "-map", "[pre]", "-ar", "48000", "-c:a", "pcm_s24le", pre])

# ---------- 4) master: ganho + limitador de picos, depois loudnorm em 2 passadas ----------
# o limitador segura só os picos mais altos; assim o loudnorm consegue trabalhar linear (sem achatar a fala)
pre_I = medida(pre)["I"]
lim = P("_lim.wav")
roda(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af",
      f"volume={ALVO - pre_I:.2f}dB,alimiter=limit=0.70:attack=4:release=60:level=false",
      "-ar", "48000", "-c:a", "pcm_s24le", lim])
os.replace(lim, pre)
s = roda(["ffmpeg", "-hide_banner", "-nostats", "-i", pre, "-af", f"loudnorm=I={ALVO}:TP={TP}:LRA=11:print_format=json", "-f", "null", "-"])
m = json.loads(s[s.rfind("{"):s.rfind("}") + 1])
ln = (f"loudnorm=I={ALVO}:TP={TP}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=json")
s = roda(["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", pre, "-af", ln, "-ar", "48000", "-c:a", "pcm_s24le", P("mix.wav")])
m2 = json.loads(s[s.rfind("{"):s.rfind("}") + 1])
modo = "linear (sem mexer na dinâmica)" if m2.get("normalization_type") == "linear" else "dinâmico (o loudnorm precisou segurar picos)"

# ---------- 5) junta com o vídeo e confere o pico depois do AAC ----------
def junta(ajuste_db):
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if tem_video:
        cmd += ["-i", ENTRADA, "-i", P("mix.wav"), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy"]
        saida = P("mixado.mp4")
    else:
        cmd += ["-i", P("mix.wav")]
        saida = P("mixado.m4a")
    cmd += ["-af", f"volume={ajuste_db:.2f}dB", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", saida]
    roda(cmd)
    return saida, medida(saida)

ajuste = 0.0
saida, final = junta(ajuste)
for _ in range(3):
    if final["TP"] <= -1.0:
        break
    ajuste -= final["TP"] + 1.0 + 0.2                  # baixa só o que passou, com folga
    saida, final = junta(ajuste)
wav_final = medida(P("mix.wav"))
for f in (voz, pre):
    os.remove(f)

ok = abs(final["I"] - ALVO) <= 1.0 and final["TP"] <= -1.0
rel = ["# Som · relatório da mixagem", "",
       f"Entrada: {antes['I']:.1f} LUFS, pico {antes['TP']:.1f} dBTP.",
       f"Voz: {'sem tratamento' if SEM_TRATAR else 'passa-alta 80 Hz, menos 250 Hz, presença em 3,5 kHz, de-esser, compressor 2,5:1'} ({VOZ_I:.1f} LUFS antes do master).",
       f"Efeitos: {len(eventos)}" + ("" if eventos else " (nenhum)")]
rel += desc_ev
rel += [f"Trilha: {os.path.basename(TRILHA)} a {TRILHA_DB:+.0f} dB da voz, com ducking (abaixa sob a fala)" if TRILHA else "Trilha: nenhuma", "",
        "## Medida final", "",
        f"- mix.wav: {wav_final['I']:.1f} LUFS · pico {wav_final['TP']:.1f} dBTP · LRA {wav_final['LRA']:.1f} LU · loudnorm {modo}",
        f"- {os.path.basename(saida)} (AAC): {final['I']:.1f} LUFS · pico {final['TP']:.1f} dBTP · LRA {final['LRA']:.1f} LU"
        + (f" · volume corrigido {ajuste:+.1f} dB para o pico" if ajuste else ""),
        f"- Alvo: {ALVO:.0f} LUFS (±1) e pico ≤ −1 dBTP → {'OK' if ok else 'FORA DO ALVO, conferir'}"]
open(P("relatorio-som.md"), "w").write("\n".join(rel) + "\n")
print("\n".join(rel[-3:]))
print(f"ok · {saida}")
sys.exit(0 if ok else 2)
