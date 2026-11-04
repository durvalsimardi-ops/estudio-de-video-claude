#!/usr/bin/env python3
"""Confere uma gravação antes de editar: luz, volume da voz e se a cabeça cabe no 9:16 e na meia tela.

Uso:
  .venv/bin/python .claude/skills/conferir-gravacao/conferir.py <video> <pasta-de-trabalho>

Escreve o relatório na tela e em <pasta-de-trabalho>/conferencia.txt.
O enquadramento usa o recorte do Mac (ferramentas/recorte.sh). Fora do Mac, só luz e som.
"""
import json, os, platform, re, subprocess, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "ferramentas"))
import estudio as e  # noqa: E402
import numpy as np  # noqa: E402

if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)
VIDEO, PASTA = sys.argv[1], sys.argv[2]
os.makedirs(PASTA, exist_ok=True)
inf = e.info(VIDEO)
W, H, DUR = inf["largura"], inf["altura"], inf["duracao"]
linhas = []


def diz(texto=""):
    linhas.append(texto)


def num(x, casas=1):
    return f"{x:.{casas}f}".replace(".", ",")


def trechos(tempos, marcado, minimo=0.4):
    """Junta os momentos marcados em trechos 'de–até' (ignora piscadas menores que 'minimo' s)."""
    out, ini, ant = [], None, None
    passo = (tempos[1] - tempos[0]) if len(tempos) > 1 else 0.2
    for t, m in zip(tempos, marcado):
        if m and ini is None:
            ini = t
        if not m and ini is not None:
            out.append((ini, ant + passo))
            ini = None
        ant = t
    if ini is not None:
        out.append((ini, ant + passo))
    out = [(a, b) for a, b in out if b - a >= minimo]
    return ", ".join(f"{num(a)}–{num(b)} s" for a, b in out[:6]) + (" …" if len(out) > 6 else ""), len(out)


diz(f"Conferência da gravação · {os.path.basename(VIDEO)} · {W}x{H} · {num(DUR)} s")
diz("")

# ---------------- enquadramento (precisa do recorte do Mac) ----------------
rec = None
if platform.system() == "Darwin":
    pasta_rec = os.path.join(PASTA, "recorte-conferencia")
    r = subprocess.run(["bash", os.path.join(e.RAIZ, "ferramentas", "recorte.sh"), VIDEO, pasta_rec,
                        "--so-rostos", "--fps", "5"], capture_output=True, text=True)
    if r.returncode == 0:
        rec = e.Recorte(pasta_rec)
    else:
        diz("Enquadramento: não consegui rodar o recorte (" + (r.stderr or r.stdout).strip()[-200:] + ")")

# ---------------- luz ----------------
LW = 270
LH = int(round(LW * H / W / 2) * 2)
medias, rosto_luz, rosto_estouro, estouro, escuro, tempos_luz = [], [], [], [], [], []
for n, q in enumerate(e.ler_quadros(VIDEO, LW, LH, 2)):
    t = n / 2
    y = q[..., 0] * 0.299 + q[..., 1] * 0.587 + q[..., 2] * 0.114
    medias.append(y.mean())
    estouro.append((y >= 250).mean() * 100)
    escuro.append((y <= 12).mean() * 100)
    tempos_luz.append(t)
    if rec is not None:
        i = rec.indice(t)
        if rec.tem_rosto[i]:
            s = LW / W
            x0, y0 = int(rec.x[i] * s), int(rec.y[i] * s)
            x1, y1 = int((rec.x[i] + rec.w[i]) * s), int((rec.y[i] + rec.h[i]) * s)
            pedaco = y[max(0, y0):y1, max(0, x0):x1]
            if pedaco.size:
                rosto_luz.append(pedaco.mean())
                rosto_estouro.append((pedaco >= 250).mean() * 100)
diz("LUZ")
media = float(np.mean(medias))
diz(f"  Brilho médio da imagem: {num(media, 0)} de 255")
if rosto_luz:
    rl = float(np.median(rosto_luz))
    nota = ("escuro: ponha uma luz de frente para você" if rl < 60 else "um pouco escuro" if rl < 90
            else "claro demais: afaste a luz ou baixe a exposição" if rl > 195 else "bom")
    diz(f"  Rosto: {num(rl, 0)} de 255 → {nota}")
    if np.mean(rosto_estouro) > 2:
        diz(f"  Brilho estourado no rosto ({num(np.mean(rosto_estouro))}% do rosto branco puro): suavize a luz")
est = float(np.mean(estouro))
if est > 5:
    diz(f"  Área estourada: {num(est)}% da tela fica branca pura (janela ou lâmpada no quadro?)")
else:
    diz(f"  Área estourada: {num(est)}% da tela (ok)")
esc = float(np.mean(escuro))
diz(f"  Área preta: {num(esc)}% da tela" + (" (muito escuro no fundo)" if esc > 35 else " (ok)"))
diz("")

# ---------------- som ----------------
diz("SOM")
if not inf["tem_som"]:
    diz("  O vídeo não tem som.")
else:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", VIDEO, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    resumo = r.stderr[r.stderr.rfind("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", resumo).group(1))
    pico = re.search(r"Peak:\s+(-?[\d.inf]+) dBFS", resumo)
    pico = float(pico.group(1)) if pico and "inf" not in pico.group(1) else -99.0
    nota = ("baixo demais: aproxime o microfone" if lufs < -30 else "alto: pode distorcer" if lufs > -10
            else "ok (o volume final em −14 é ajustado na edição)")
    diz(f"  Volume da voz: {num(lufs)} LUFS → {nota}")
    # amostras do áudio para medir ruído de fundo e estouro
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", VIDEO, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    a = np.frombuffer(pcm, np.float32)
    janela = 800  # 50 ms
    blocos = a[:len(a) // janela * janela].reshape(-1, janela)
    rms = 20 * np.log10(np.sqrt((blocos ** 2).mean(axis=1)) + 1e-9)
    ruido, voz = float(np.percentile(rms, 10)), float(np.percentile(rms, 95))
    nota = ("alto: ar-condicionado, rua ou ventilador? grave em lugar mais quieto" if ruido > -45
            else "aceitável" if ruido > -55 else "silencioso (ótimo)")
    diz(f"  Ruído de fundo: {num(ruido, 0)} dB → {nota}")
    diz(f"  Voz acima do ruído: {num(voz - ruido, 0)} dB" + (" (pouco: a voz se mistura com o fundo)" if voz - ruido < 25 else " (bom)"))
    estourado = np.abs(blocos).max(axis=1) >= 0.99
    if estourado.any() or pico > -0.5:
        tx, qt = trechos(np.arange(len(blocos)) * 0.05, estourado, 0.05)
        diz(f"  Pico: {num(pico)} dBFS → ESTOUROU (distorção) em {tx or 'algum ponto'}: fale um pouco mais longe")
    else:
        diz(f"  Pico: {num(pico)} dBFS (sem estouro)")
diz("")

# ---------------- enquadramento ----------------
diz("ENQUADRAMENTO")
if rec is None:
    diz("  Só no Mac (usa o Vision da Apple). No Windows, confira olhando 3 quadros: começo, meio e fim.")
else:
    t = rec.t
    sem = ~rec.tem_rosto
    tx, qt = trechos(t, sem)
    diz(f"  Rosto encontrado em {num(100 * rec.tem_rosto.mean(), 0)}% do vídeo" + (f"; sumiu em {tx}" if qt else ""))
    # 9:16: se o vídeo for deitado, simula o corte do meio
    cw = min(W, H * 9 / 16)
    x0 = (W - cw) / 2
    cortada = (rec.topo <= 0.005 * H) & rec.tem_rosto
    tx, qt = trechos(t, cortada)
    diz("  Cabeça cortada no alto: " + (f"SIM em {tx}" if qt else "não"))
    fora = rec.tem_rosto & ((rec.x < x0 + 0.06 * cw) | (rec.x + rec.w > x0 + 0.94 * cw) |
                            (rec.y < 0.10 * H) | (rec.y + rec.h > 0.72 * H))
    tx, qt = trechos(t, fora)
    diz("  Rosto fora da área segura do 9:16 (perfil em cima, legenda embaixo): " + (f"SIM em {tx}" if qt else "não"))
    # meia tela: mesma conta da skill meia-tela (janela 1000x940)
    ok = rec.tem_rosto
    if ok.any():
        esq, dir_ = rec.x[ok].min(), (rec.x + rec.w)[ok].max()
        topo, queixo = rec.topo[ok].min(), (rec.y + rec.h)[ok].max()
        hr = float(np.median(rec.h[ok]))
        prop = 1000 / 940
        ch = max(queixo - topo + 1.5 * hr, 2.6 * hr)
        cw2 = ch * prop
        if (dir_ - esq) * 1.25 > cw2:
            cw2 = (dir_ - esq) * 1.25
            ch = cw2 / prop
        if cw2 > W:
            cw2, ch = W, W / prop
        if ch > H:
            ch, cw2 = H, H * prop
        cx = min(max((esq + dir_) / 2 - cw2 / 2, 0), W - cw2)
        cy = min(max(topo - 0.1 * ch, 0), H - ch)
        cabe = topo >= cy and queixo <= cy + ch and esq >= cx and dir_ <= cx + cw2
        diz(f"  Meia tela: rosto ocupa {num(100 * hr / H, 0)}% da altura · " +
            ("cabe inteiro na janela de baixo" if cabe else
             "NÃO cabe inteiro (perto demais da câmera ou se mexendo muito de lado)"))
diz("")

texto = "\n".join(linhas)
print(texto)
open(os.path.join(PASTA, "conferencia.txt"), "w").write(texto + "\n")
