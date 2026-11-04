"""Funções comuns dos scripts de vídeo do estúdio.

Ler e gravar quadros com o ffmpeg, abrir o rostos.json do recorte, suavizar movimentos e carregar fontes.
Os scripts das skills importam este arquivo; ele não roda sozinho.
"""
import json, os, subprocess, sys

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTES = os.path.join(RAIZ, "assets", "fontes")


def precisa_pillow():
    """Pillow desenha as letras e os adesivos. Avisa como instalar se faltar."""
    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit("Falta o Pillow (desenho de letras). Rode uma vez:  .venv/bin/pip install pillow")


def info(video):
    """Largura, altura, fps, duração e se tem som."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", video],
                       capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    n, q = v["r_frame_rate"].split("/")
    return {"largura": int(v["width"]), "altura": int(v["height"]), "fps": float(n) / float(q or 1),
            "duracao": float(d["format"]["duration"]),
            "tem_som": any(s["codec_type"] == "audio" for s in d["streams"])}


def ler_quadros(video, largura, altura, fps, inicio=0.0, duracao=None, cinza=False):
    """Entrega os quadros um a um como matriz numpy (altura, largura, 3) ou (altura, largura)."""
    fmt, canais = ("gray", 1) if cinza else ("rgb24", 3)
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{inicio:.3f}", "-i", video]
    if duracao:
        cmd += ["-t", f"{duracao:.3f}"]
    cmd += ["-vf", f"scale={largura}:{altura},fps={fps}", "-f", "rawvideo", "-pix_fmt", fmt, "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10 ** 8)
    tam = largura * altura * canais
    try:
        while True:
            b = p.stdout.read(tam)
            if len(b) < tam:
                break
            q = np.frombuffer(b, np.uint8)
            yield q.reshape(altura, largura) if cinza else q.reshape(altura, largura, 3)
    finally:
        p.stdout.close()
        p.wait()


class Gravador:
    """Recebe quadros numpy e grava o MP4 final, com o som do vídeo original no mesmo trecho."""

    def __init__(self, saida, largura, altura, fps, video_som=None, inicio=0.0, duracao=None):
        os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{largura}x{altura}", "-r", str(fps), "-i", "-"]
        if video_som and info(video_som)["tem_som"]:
            cmd += ["-ss", f"{inicio:.3f}", "-i", video_som, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k"]
            if duracao:
                cmd += ["-t", f"{duracao:.3f}"]
        cmd += ["-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", saida]
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        self.saida = saida

    def escrever(self, quadro):
        self.p.stdin.write(np.clip(quadro, 0, 255).astype(np.uint8).tobytes())

    def fechar(self):
        self.p.stdin.close()
        self.p.wait()
        if self.p.returncode != 0:
            sys.exit("O ffmpeg falhou ao gravar " + self.saida)


class Recorte:
    """Lê o rostos.json do recorte (ferramentas/recorte.sh) e responde onde está o rosto em cada tempo."""

    def __init__(self, caminho):
        if os.path.isdir(caminho):
            caminho = os.path.join(caminho, "rostos.json")
        self.pasta = os.path.dirname(os.path.abspath(caminho))
        d = json.load(open(caminho))
        self.largura, self.altura = d["largura"], d["altura"]
        self.fps, self.inicio, self.fim = d["fps"], d["inicio"], d["fim"]
        self.matte = os.path.join(self.pasta, d["matte"]) if d.get("matte") else None
        q = d["quadros"]
        self.t = np.array([x["t"] for x in q], float)
        nan = float("nan")
        caixa = [x["rosto"] or {"x": nan, "y": nan, "w": nan, "h": nan} for x in q]
        self.x = _preencher(np.array([c["x"] for c in caixa], float))
        self.y = _preencher(np.array([c["y"] for c in caixa], float))
        self.w = _preencher(np.array([c["w"] for c in caixa], float))
        self.h = _preencher(np.array([c["h"] for c in caixa], float))
        topo = np.array([nan if x.get("topo_cabeca") is None else x["topo_cabeca"] for x in q], float)
        # sem topo medido, estima pelo rosto (o cabelo fica mais ou menos meio rosto acima da testa)
        estimado = self.y - 0.45 * self.h
        self.topo = _preencher(np.where(np.isnan(topo), estimado, topo))
        self.tem_rosto = np.array([x["rosto"] is not None for x in q])

    def indice(self, t):
        return int(np.clip(np.searchsorted(self.t, t - 1e-6), 0, len(self.t) - 1))

    def rosto(self, t):
        """(x, y, w, h) do rosto em pixels do vídeo original."""
        i = self.indice(t)
        return self.x[i], self.y[i], self.w[i], self.h[i]

    def entre(self, t0, t1):
        """Índices dos quadros entre dois tempos (ao menos um)."""
        a, b = self.indice(t0), self.indice(t1)
        return slice(a, max(a + 1, b + 1))


def _preencher(v):
    """Troca buracos (nan) pelo valor vizinho mais próximo."""
    v = v.copy()
    ok = ~np.isnan(v)
    if not ok.any():
        return v
    i = np.arange(len(v))
    v[~ok] = np.interp(i[~ok], i[ok], v[ok])
    return v


def suavizar(serie, fps, segundos):
    """Média com peso em sino (gaussiana), sem atraso: tira o tremido mantendo o movimento."""
    sigma = max(1e-3, segundos * fps)
    r = int(3 * sigma) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    p = np.pad(serie, r, mode="edge")
    return np.convolve(p, k, mode="valid")


def minimo_movel(serie, janela):
    """Menor valor numa janela de quadros (no vídeo, menor y = mais alto na tela)."""
    r = max(0, janela // 2)
    p = np.pad(serie, r, mode="edge")
    return np.array([p[i:i + 2 * r + 1].min() for i in range(len(serie))])


def fonte(arquivo, tamanho):
    """Carrega uma fonte de assets/fontes (ex.: 'barlow-condensed/BarlowCondensed-Black.ttf')."""
    from PIL import ImageFont
    caminho = arquivo if os.path.isabs(arquivo) or os.path.exists(arquivo) else os.path.join(FONTES, arquivo)
    return ImageFont.truetype(caminho, tamanho)


def cor(hexa):
    hexa = hexa.lstrip("#")
    return tuple(int(hexa[i:i + 2], 16) for i in (0, 2, 4))


def limitar(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def saida_suave(x):
    """Começa rápido e chega devagar (ease-out)."""
    x = limitar(x)
    return 1 - (1 - x) ** 3


def saida_suave_forte(x):
    x = limitar(x)
    return 1 - (1 - x) ** 4


def recuo_leve(x, folga=1.1):
    """Chega passando um pouquinho e volta (ease-out-back suave). folga 1.1 ≈ 3% de passada."""
    x = limitar(x)
    return 1 + (folga + 1) * (x - 1) ** 3 + folga * (x - 1) ** 2


def carregar_cenas(arquivo):
    d = json.load(open(arquivo))
    return d["cenas"] if isinstance(d, dict) else d


def rel(caminho):
    """Caminho curto para mostrar ao aluno (relativo à raiz do estúdio quando der)."""
    try:
        return os.path.relpath(caminho, RAIZ) if os.path.abspath(caminho).startswith(RAIZ) else caminho
    except ValueError:
        return caminho
