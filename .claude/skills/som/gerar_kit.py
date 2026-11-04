#!/usr/bin/env python3
"""Gera o kit de efeitos do estúdio, todo por código (sem gravação de terceiros).

Uso:
  .venv/bin/python .claude/skills/som/gerar_kit.py [pasta]      (padrão: assets/sons)

Cria clique, pop, whoosh, brilho, impacto e subida em WAV 48 kHz 16 bits, mais kit.json
com o "ponto" de cada som (o instante, dentro do arquivo, que deve cair no tempo do evento)
e mede cada arquivo (pico, começo e fim em silêncio, estalos, agudos, loudness).
O resultado é sempre o mesmo (semente fixa): rodar de novo não muda o kit.
"""
import json, os, sys, wave
import numpy as np

SR = 48000
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PASTA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "assets", "sons")
rng = np.random.default_rng(20261104)


def tempo(dur):
    return np.arange(int(dur * SR)) / SR


def rampa(n_ini, n_fim, n):
    """Envelope com subida e descida em cosseno: evita estalo no começo e no fim."""
    e = np.ones(n)
    if n_ini > 0:
        e[:n_ini] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n_ini))
    if n_fim > 0:
        e[-n_fim:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, n_fim))
    return e


def svf(x, fc, q, modo="pb"):
    """Filtro de estado variável com frequência que pode mudar a cada amostra.
    modo: pb (passa-baixa), pf (passa-faixa), pa (passa-alta)."""
    fc = np.broadcast_to(np.asarray(fc, float), x.shape)
    g = np.tan(np.pi * np.clip(fc, 20, SR * 0.45) / SR)
    k = 1.0 / q
    a1 = 1 / (1 + g * (g + k)); a2 = g * a1; a3 = g * a2
    s1 = s2 = 0.0
    y = np.empty_like(x)
    for i in range(len(x)):
        v3 = x[i] - s2
        v1 = a1[i] * s1 + a2[i] * v3
        v2 = s2 + a2[i] * s1 + a3[i] * v3
        s1 = 2 * v1 - s1; s2 = 2 * v2 - s2
        y[i] = v2 if modo == "pb" else v1 if modo == "pf" else x[i] - k * v1 - v2
    return y


def passa_baixa(x, fc, q=0.707):
    return svf(x, fc, q, "pb")


def passa_alta(x, fc, q=0.707):
    return svf(x, fc, q, "pa")


def senoide(freq, n):
    """Seno com frequência que varia no tempo (fase acumulada, sem saltos)."""
    f = np.broadcast_to(np.asarray(freq, float), (n,))
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def atrasa(x, seg):
    """Atrasa o sinal preenchendo o começo com silêncio (np.roll traria o fim do som para o começo)."""
    n = int(seg * SR)
    return np.concatenate([np.zeros(n), x[:len(x) - n]])


def ruido(n):
    return rng.standard_normal(n)


def finaliza(x, pico_db=-3.0, ini_ms=1.0, fim_ms=8.0):
    """Tira o nível DC, aplica rampas e normaliza o pico."""
    x = np.atleast_2d(x.T).T if x.ndim == 1 else x
    x = x - x.mean(axis=0)
    e = rampa(int(ini_ms * SR / 1000), int(fim_ms * SR / 1000), len(x))
    x = x * e[:, None]
    x = x / (np.abs(x).max() + 1e-12) * 10 ** (pico_db / 20)
    return x


# ---------- os sons ----------

def clique():
    """Clique de interface: toque curto e seco, corpo médio, sem agudo cortante."""
    n = int(0.07 * SR); t = tempo(0.07)
    toque = passa_baixa(passa_alta(ruido(n), 900), 4200) * np.exp(-t / 0.004)
    corpo = senoide(1350, n) * np.exp(-t / 0.004) * 0.45
    grave = senoide(260, n) * np.exp(-t / 0.018) * 0.45
    return finaliza(toque * 0.6 + corpo + grave, -3, ini_ms=0.4, fim_ms=15)


def pop():
    """Pop de bolha: seno que sobe rápido de tom e some, com um sopro leve."""
    n = int(0.16 * SR); t = tempo(0.16)
    f = 320 + 680 * (1 - np.exp(-t / 0.018))
    corpo = senoide(f, n) * np.exp(-t / 0.035)
    sopro = passa_baixa(ruido(n), 2500) * np.exp(-t / 0.008) * 0.25
    return finaliza(corpo + sopro, -3, ini_ms=0.8, fim_ms=30)


def whoosh():
    """Passagem de ar: ruído com filtro que abre e fecha, indo da esquerda para a direita."""
    dur = 0.62; n = int(dur * SR); t = tempo(dur); u = t / dur
    apice = 0.58                                        # o ponto mais forte fica em 58% do som
    env = np.where(u < apice, (u / apice) ** 2.2, np.exp(-((u - apice) / 0.16) ** 2 * 1.4))
    fc = 300 + 1500 * np.exp(-((u - apice) / 0.22) ** 2)
    base = ruido(n)
    ar = passa_baixa(svf(base, fc, 1.1, "pf"), 4500)        # sem chiado agudo
    corpo = passa_baixa(base, 420 + 500 * env) * 0.5        # um pouco de corpo grave
    mono = (ar + corpo) * env
    pan = np.clip(0.15 + 0.7 * u, 0, 1)                     # esquerda → direita
    estereo = np.stack([mono * np.cos(pan * np.pi / 2), mono * np.sin(pan * np.pi / 2)], axis=1)
    return finaliza(estereo, -3, ini_ms=5, fim_ms=40), apice * dur


def brilho():
    """Brilho de flash: alguns sininhos suaves em cima de um sopro de ar que cresce e some."""
    dur = 1.1; n = int(dur * SR); t = tempo(dur)
    x = np.zeros(n)
    notas = [1046.5, 1318.5, 1568.0, 2093.0, 1760.0, 2637.0]   # dó maior: soa limpo, sem choque
    inicios = [0.00, 0.035, 0.07, 0.10, 0.14, 0.18]
    for f, t0 in zip(notas, inicios):
        k = t >= t0; tt = t[k] - t0
        ataque = np.clip(tt / 0.003, 0, 1)
        ganho = 0.5 if f > 2000 else 0.8                      # agudos mais baixos: nada estridente
        x[k] += ganho * ataque * np.exp(-tt / 0.22) * (np.sin(2 * np.pi * f * tt) + 0.12 * np.sin(2 * np.pi * 2.01 * f * tt))
    ar = passa_baixa(passa_alta(ruido(n), 1500), 6500) * (np.exp(-t / 0.09) - np.exp(-t / 0.01)) * 0.5
    mono = passa_baixa(x * 0.5 + ar, 7000)
    l = mono + 0.3 * atrasa(mono, 0.011); r = mono + 0.3 * atrasa(mono, 0.017)
    return finaliza(np.stack([l, r], axis=1), -4, ini_ms=1, fim_ms=120)


def impacto():
    """Impacto grave: batida curta e um corpo que cai de 95 para 42 Hz."""
    dur = 1.3; n = int(dur * SR); t = tempo(dur)
    f = 42 + 53 * np.exp(-t / 0.07)
    corpo = senoide(f, n) * np.exp(-t / 0.38)
    corpo = np.tanh(corpo * 1.6) / np.tanh(1.6)           # leve saturação: aparece em caixa pequena
    batida = passa_baixa(ruido(n), 2200) * np.exp(-t / 0.015) * 0.6
    ronco = passa_baixa(ruido(n), 500) * np.exp(-t / 0.16) * 0.5      # corpo que aparece em caixa de celular
    meio = senoide(120 * np.exp(-t / 0.4), n) * np.exp(-t / 0.10) * 0.35
    return finaliza(corpo + batida + ronco + meio, -2, ini_ms=0.8, fim_ms=200)


def subida():
    """Subida (riser): ar e um tom que sobem juntos por 2,4 s e terminam limpos."""
    dur = 2.4; n = int(dur * SR); t = tempo(dur); u = t / dur
    env = u ** 2.4
    fc = 250 * (12 ** u)                                   # 250 Hz → 3 kHz
    ar = svf(ruido(n), fc, 1.4, "pf")
    f0 = 110 * (2 ** (2 * u))                             # duas oitavas
    tom = sum(senoide(f0 * h, n) / h for h in (1, 2, 3, 4))
    tom = passa_baixa(tom, 900 + 1800 * u) * 0.35
    mono = passa_baixa((ar + tom) * env, 5500)            # topo controlado: nada estridente
    l = mono + 0.25 * atrasa(mono, 0.009); r = mono + 0.25 * atrasa(mono, 0.014)
    return finaliza(np.stack([l, r], axis=1), -3, ini_ms=20, fim_ms=50)


# ---------- gravar e medir ----------

def grava(nome, x):
    caminho = os.path.join(PASTA, nome + ".wav")
    x2 = x if x.ndim == 2 else x[:, None]
    pcm = np.clip(np.round(x2 * 32767), -32768, 32767).astype("<i2")
    with wave.open(caminho, "wb") as w:
        w.setnchannels(x2.shape[1]); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return caminho


def loudness(caminho):
    """Loudness do som (LUFS, BS.1770) medida pelo ffmpeg, com silêncio em volta para sons curtos."""
    import re, subprocess
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", caminho, "-af", "adelay=500:all=1,apad=pad_dur=0.5,ebur128",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def mede(x):
    m = x.mean(axis=1) if x.ndim == 2 else x
    pico = np.abs(x).max()
    # estalo: um salto isolado concentra energia na 2ª diferença; compara cada 1 ms com os vizinhos
    d2 = np.diff(m, 2); k = len(d2) // 48
    e = 10 * np.log10((d2[:k * 48].reshape(k, 48) ** 2).mean(axis=1) + 1e-20)
    viz = np.array([np.median(np.r_[e[max(0, i - 10):max(0, i - 2)], e[i + 3:i + 11]] if k > 12 else e) for i in range(k)])
    nivel = 10 * np.log10((m[:k * 48].reshape(k, 48) ** 2).mean(axis=1) + 1e-20)
    estalos = int(((e - viz > 18) & (nivel > nivel.max() - 60) & (np.arange(k) > 3)).sum())
    ini = np.abs(m[:48]).max() / (pico + 1e-12)               # primeiro 1 ms
    fim = np.abs(m[-480:]).max() / (pico + 1e-12)             # últimos 10 ms
    esp = np.abs(np.fft.rfft(m)) ** 2                          # sem janela: o som já começa e termina em zero
    fr = np.fft.rfftfreq(len(m), 1 / SR)
    total = esp.sum() + 1e-20
    return dict(pico_db=round(20 * np.log10(pico), 1),
                estalos=estalos,
                inicio_db=round(20 * np.log10(ini + 1e-9), 1),
                fim_db=round(20 * np.log10(fim + 1e-9), 1),
                agudo_2a5k=round(float(esp[(fr >= 2000) & (fr < 5000)].sum() / total), 3),
                acima_8k=round(float(esp[fr >= 8000].sum() / total), 4),
                centroide_hz=int((fr * esp).sum() / total))


if __name__ == "__main__":
    os.makedirs(PASTA, exist_ok=True)
    kit, sons = {}, {}
    sons["clique"] = (clique(), 0.0, "clique de interface, curto e seco")
    sons["pop"] = (pop(), 0.0, "pop de bolha, para algo que aparece")
    w, ap = whoosh(); sons["whoosh"] = (w, ap, "passagem de ar da esquerda para a direita, para chicote")
    sons["brilho"] = (brilho(), 0.0, "brilho suave, para flash")
    sons["impacto"] = (impacto(), 0.0, "impacto grave, para zoom-soco e entrada forte")
    s = subida(); sons["subida"] = (s, len(s) / SR, "subida de 2,4 s que termina no ponto (antes da virada)")
    print(f"{'som':8} {'dur':>5} {'pico':>6} {'início':>7} {'fim':>6} {'estalos':>7} {'2-5k':>5} {'>8k':>6} {'centro':>6}")
    for nome, (x, ponto, desc) in sons.items():
        caminho = grava(nome, x)
        m = mede(x)
        kit[nome] = dict(arquivo=nome + ".wav", ponto=round(ponto, 3), duracao=round(len(x) / SR, 3),
                         lufs=loudness(caminho), descricao=desc)
        print(f"{nome:8} {len(x)/SR:5.2f} {m['pico_db']:6.1f} {m['inicio_db']:7.1f} {m['fim_db']:6.1f} {m['estalos']:7d} "
              f"{m['agudo_2a5k']:5.2f} {m['acima_8k']:6.4f} {m['centroide_hz']:6d}")
    json.dump(kit, open(os.path.join(PASTA, "kit.json"), "w"), ensure_ascii=False, indent=1)
    print(f"ok · {len(kit)} sons em {PASTA}")
