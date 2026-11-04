#!/usr/bin/env python3
"""Converte vídeo HDR do iPhone (HLG ou Dolby Vision) para SDR padrão (BT.709) sem lavar as cores.

Uso:
  .venv/bin/python .claude/skills/converter-iphone/converter.py <video> <pasta-de-saida> [--9x16] [--metodo lut|apple] [--crf 18]

  --9x16     recorta o centro para 9:16 e entrega em 1080x1920
  --metodo   lut (padrão, funciona no Mac e no Windows) ou apple (usa o avconvert do Mac)
  --crf      qualidade do H.264 (menor = melhor e mais pesado; 18 é quase igual ao original)

Gera <pasta>/<nome>-sdr.mp4 e <pasta>/<nome>-sdr.jpg (um quadro do meio, para olhar).
Mantém resolução e quadros por segundo (qps constante). Tira a localização e outros dados do arquivo.
O original nunca é alterado.
"""
import json, os, shutil, subprocess, sys, tempfile
import numpy as np

args = sys.argv[1:]
def opt(nome, padrao=None, flag=False):
    if nome in args:
        i = args.index(nome)
        if flag:
            args.pop(i); return True
        v = args[i + 1]; del args[i:i + 2]; return v
    return False if flag else padrao
VERTICAL = opt("--9x16", flag=True)
METODO = opt("--metodo", "lut")
CRF = str(opt("--crf", 18))
if len(args) < 2:
    print(__doc__); sys.exit(1)
ENTRADA, PASTA = os.path.abspath(args[0]), os.path.abspath(args[1])
os.makedirs(PASTA, exist_ok=True)
NOME = os.path.splitext(os.path.basename(ENTRADA))[0]
SAIDA = os.path.join(PASTA, NOME + "-sdr.mp4")
if os.path.abspath(SAIDA) == ENTRADA:
    sys.exit("A saída não pode ser o próprio original.")


def sonda(arquivo):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", arquivo],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


info = sonda(ENTRADA)
v = next(s for s in info["streams"] if s["codec_type"] == "video")
tem_audio = any(s["codec_type"] == "audio" for s in info["streams"])
TRANSF = v.get("color_transfer", "desconhecida")
num, den = map(int, v.get("r_frame_rate", "30/1").split("/"))
QPS = f"{num}/{den}"
# rotação do iPhone: o ffmpeg já gira o vídeo; largura e altura de verdade trocam se girar 90°
rot = 0
for sd in v.get("side_data_list", []):
    if "rotation" in sd:
        rot = int(sd["rotation"])
W, H = (v["height"], v["width"]) if abs(rot) % 180 == 90 else (v["width"], v["height"])
dovi = any(sd.get("side_data_type", "").startswith("DOVI") for sd in v.get("side_data_list", []))
perfil_dv = next((sd.get("dv_profile") for sd in v.get("side_data_list", []) if "dv_profile" in sd), None)

HDR = TRANSF in ("arib-std-b67", "smpte2084")
tipo = {"arib-std-b67": "HLG", "smpte2084": "PQ (HDR10)"}.get(TRANSF, "SDR")
print(f"Entrada: {W}x{H}, {num/den:.3f} qps, {tipo}{' + Dolby Vision perfil ' + str(perfil_dv) if dovi else ''}")
if dovi and perfil_dv == 5:
    print("Aviso: Dolby Vision perfil 5 não é do iPhone e não tem base HLG; as cores podem sair erradas. Use --metodo apple.")

# ---------- curvas (BT.2100, BT.2020, BT.709) ----------
A, B, C = 0.17883277, 0.28466892, 0.55991073
def hlg_para_luz(e):                      # sinal HLG → luz da cena (0..1)
    e = np.clip(e, 0, 1)
    return np.where(e <= 0.5, e * e / 3, (np.exp((e - C) / A) + B) / 12)
def pq_para_nits(e):                       # sinal PQ → nits
    m1, m2, c1, c2, c3 = 0.1593017578125, 78.84375, 0.8359375, 18.8515625, 18.6875
    p = np.clip(e, 0, 1) ** (1 / m2)
    return 10000 * (np.maximum(p - c1, 0) / (c2 - c3 * p)) ** (1 / m1)
# BT.2020 → BT.709 (luz linear)
M = np.array([[1.6605, -0.5876, -0.0728], [-0.1246, 1.1329, -0.0083], [-0.0182, -0.1006, 1.1187]])
BRANCO = 203.0        # nits do branco de referência do HDR (ITU-R BT.2408) = 100% do SDR
JOELHO = 0.75         # até aqui não comprime nada; acima, os brilhos encostam suavemente no branco


def tom(x):
    """Comprime só os brilhos: identidade até o joelho e curva suave até 1 (sem estourar)."""
    k = JOELHO
    return np.where(x <= k, x, k + (1 - k) * (1 - np.exp(-(x - k) / (1 - k))))


def gera_lut(caminho, n=65):
    with np.errstate(all="ignore"):          # o numpy do Mac às vezes avisa à toa em multiplicação de matriz
        sdr = _lut(n)
    with open(caminho, "w") as f:
        f.write(f"LUT_3D_SIZE {n}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n")
        f.write("\n".join(f"{a:.6f} {b_:.6f} {c:.6f}" for a, b_, c in sdr))
        f.write("\n")


def _lut(n):
    g = np.linspace(0, 1, n)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")     # no .cube o vermelho varia mais rápido
    rgb = np.stack([r, gg, b], axis=-1).reshape(-1, 3)
    if TRANSF == "arib-std-b67":
        e = hlg_para_luz(rgb)
        ys = e @ np.array([0.2627, 0.6780, 0.0593])
        nits = 1000 * np.maximum(ys, 1e-6)[:, None] ** 0.2 * e      # OOTF do HLG para tela de 1000 nits
    else:
        nits = pq_para_nits(rgb)
    lin = (nits / BRANCO) @ M.T                                   # para as cores do SDR
    lin = np.maximum(lin, 0)
    m = lin.max(axis=1, keepdims=True)
    lin = lin * np.where(m > 1e-6, tom(m) / np.maximum(m, 1e-6), 1)   # comprime pelo canal mais forte: não desbota
    return np.nan_to_num(np.clip(lin, 0, 1) ** (1 / 2.4))      # tela SDR (BT.1886)


def recorte_9x16():
    # recorta o centro em 9:16 e leva para 1080x1920
    return "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',scale=1080:1920:flags=lanczos,setsar=1"


def codifica(entrada, filtros, saida, audio_de=None):
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", entrada]
    cmd += ["-map", "0:v:0"]
    if tem_audio:
        cmd += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-vf", filtros, "-fps_mode", "cfr", "-r", QPS,
            "-c:v", "libx264", "-crf", CRF, "-preset", "medium", "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
            "-map_metadata", "-1", "-movflags", "+faststart", saida]
    subprocess.run(cmd, check=True)


if VERTICAL and min(W, H * 9 / 16) < 1080:
    print(f"Aviso: o recorte 9:16 deste vídeo tem {int(min(W, H * 9 / 16))} px de largura e será ampliado para 1080 (perde nitidez).")
SAIDA_SDR = "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv"
with tempfile.TemporaryDirectory() as tmp:
    if not HDR:
        print("Este vídeo já é SDR: só padronizo (H.264, qps constante" + (", 9:16" if VERTICAL else "") + ").")
        f = ["scale=in_color_matrix=bt709:out_color_matrix=bt709", "format=yuv420p", SAIDA_SDR]
        if VERTICAL:
            f.insert(0, recorte_9x16())
        codifica(ENTRADA, ",".join(f), SAIDA)
    elif METODO == "apple":
        if not shutil.which("avconvert"):
            sys.exit("O avconvert só existe no Mac. Use --metodo lut.")
        mov = os.path.join(tmp, "apple.mov")
        subprocess.run(["avconvert", "--source", ENTRADA, "--output", mov, "--preset", "PresetHighestQuality", "--replace"],
                       check=True, stdout=subprocess.DEVNULL)
        t2 = sonda(mov)["streams"]
        tr = next(s for s in t2 if s["codec_type"] == "video").get("color_transfer")
        if tr in ("arib-std-b67", "smpte2084"):
            sys.exit("O avconvert manteve o HDR neste arquivo. Use --metodo lut.")
        f = ["scale=in_color_matrix=bt709:out_color_matrix=bt709", "format=yuv420p", SAIDA_SDR]
        if VERTICAL:
            f.insert(0, recorte_9x16())
        codifica(mov, ",".join(f), SAIDA)
    else:
        lut = os.path.join(tmp, "hdr-para-sdr.cube")
        gera_lut(lut)
        f = ["scale=in_color_matrix=bt2020:in_range=tv:out_range=pc", "format=gbrp16le",
             f"lut3d=file='{lut}':interp=tetrahedral",
             "scale=out_color_matrix=bt709:in_range=pc:out_range=tv", "format=yuv420p", SAIDA_SDR]
        if VERTICAL:
            f.insert(-2, recorte_9x16())
        codifica(ENTRADA, ",".join(f), SAIDA)

# ---------- conferência ----------
out = sonda(SAIDA)
vs = next(s for s in out["streams"] if s["codec_type"] == "video")
ok_cor = (vs.get("color_transfer"), vs.get("color_primaries"), vs.get("color_space")) == ("bt709", "bt709", "bt709")
sem_dv = not any(sd.get("side_data_type", "").startswith("DOVI") for sd in vs.get("side_data_list", []))
dur = float(out["format"]["duration"])
jpg = os.path.join(PASTA, NOME + "-sdr.jpg")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{dur / 2:.2f}", "-i", SAIDA, "-frames:v", "1", "-q:v", "3", jpg], check=True)
print(f"Saída: {vs['width']}x{vs['height']}, {vs['r_frame_rate']} qps, cor {vs.get('color_transfer')}/{vs.get('color_primaries')}/{vs.get('color_space')}, "
      f"{vs.get('pix_fmt')}, {dur:.2f} s")
print(("OK" if ok_cor and sem_dv else "ATENÇÃO") + f": {'BT.709 confirmado' if ok_cor else 'cor NÃO saiu BT.709'}"
      f"{'' if sem_dv else ', ainda tem Dolby Vision'} · {SAIDA}")
print(f"Quadro para olhar: {jpg}")
sys.exit(0 if ok_cor and sem_dv else 2)
