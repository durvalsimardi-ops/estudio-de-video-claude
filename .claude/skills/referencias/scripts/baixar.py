#!/usr/bin/env python3
"""Baixa uma referência, mede e deixa a ficha pronta para o Claude completar.

Uso (na raiz do estúdio):
  .venv/bin/python .claude/skills/referencias/scripts/baixar.py "<link>" --tag meia-tela --nota "gostei do ritmo"
  .venv/bin/python .claude/skills/referencias/scripts/baixar.py --arquivo originais/meu-video.mp4 --tag abertura   (vídeo seu)
  .venv/bin/python .claude/skills/referencias/scripts/baixar.py --so-medir trabalho/minha-versao.mp4              (só mede)

Opções:
  --tag X               pode repetir (--tag meia-tela --tag legenda)
  --nota "..."          por que você guardou
  --idioma pt           idioma da fala (en, es...). Padrão: pt
  --cookies-navegador chrome   só para Instagram, com o SEU login, e só se você pedir
  --sem-fala            não transcreve
  --limiar 0.3          sensibilidade dos cortes (menor = acha mais cortes)
  --raiz <pasta>        onde ficam fichas/, videos/ e INDICE.md. Padrão: referencias/ do estúdio

Cria referencias/videos/<pasta>/ (fora do git) com video.mp4, meta.json, prancha.jpg (24 quadros com o tempo),
planos.jpg (um quadro por plano), cortes.txt, som.txt, fala.json e fala.txt.
Cria referencias/fichas/<slug>.md com o que foi medido e os campos que o Claude preenche depois de olhar.
Vídeo de terceiro é só para estudo: nunca entra em trabalho, entrega ou publicação.
"""
import argparse, datetime, json, math, os, re, shutil, subprocess, sys, tempfile, unicodedata, array
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ_ESTUDIO = AQUI.parents[3]          # .claude/skills/referencias/scripts → raiz do estúdio
sys.path.insert(0, str(AQUI))
import fichas  # noqa: E402  (mesmo diretório)


# ------------------------------------------------------------ utilidades
def slug(s, n=48):
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:n].strip("-") or "referencia"


def tempo(t):
    """12.34 → 0:12,3"""
    m, s = divmod(max(0.0, t), 60)
    return f"{int(m)}:{s:04.1f}".replace(".", ",")


def br(x, casas=2):
    """8.67 → 8,67 (número no jeito brasileiro, para a ficha)"""
    return f"{x:.{casas}f}".rstrip("0").rstrip(".").replace(".", ",") if casas else str(x)


def roda(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def python_do_estudio():
    for p in (RAIZ_ESTUDIO / ".venv/bin/python", RAIZ_ESTUDIO / ".venv/Scripts/python.exe"):
        if p.exists():
            return str(p)
    return None


# ------------------------------------------------------------ baixar
def baixar(link, destino, cookies=None):
    """Baixa com yt-dlp e devolve os dados públicos do post (autor, data, título, licença)."""
    if not shutil.which("yt-dlp"):
        sys.exit("Falta o yt-dlp. Rode: bash ferramentas/instalar.sh")
    cmd = ["yt-dlp", "-q", "--no-warnings", "--no-playlist",
           "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/b",
           "--merge-output-format", "mp4", "-o", str(destino / "video.%(ext)s"), "-j", "--no-simulate"]
    if cookies:
        cmd += ["--cookies-from-browser", cookies]
    r = roda(cmd + [link])
    if r.returncode != 0:
        erro = (r.stderr.strip().splitlines() or ["yt-dlp falhou"])[-1]
        if "login" in erro.lower() or "cookies" in erro.lower():
            erro += "\n→ Esse link pede login. Só use --cookies-navegador com a sua própria conta e se quiser."
        sys.exit("Não consegui baixar: " + erro)
    info = json.loads(r.stdout.strip().splitlines()[-1])
    videos = sorted(destino.glob("video.*"))
    if videos and videos[0].name != "video.mp4":
        videos[0].rename(destino / "video.mp4")
    data = info.get("upload_date") or ""
    if re.fullmatch(r"\d{8}", data):
        data = f"{data[:4]}-{data[4:6]}-{data[6:]}"
    autor = info.get("uploader_id") or info.get("channel") or info.get("uploader") or "desconhecido"
    if not str(autor).startswith("@"):
        autor = "@" + str(autor)
    return {
        "link": link,
        "plataforma": (info.get("extractor_key") or "web").lower(),
        "autor": autor,
        "autor_nome": info.get("uploader") or info.get("channel") or "",
        "publicado": data,
        "titulo": (info.get("title") or "").strip(),
        "descricao": (info.get("description") or "").strip()[:1500],
        "licenca": info.get("license") or "",
    }


# ------------------------------------------------------------ medir
def sondar(v):
    r = roda(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
              "-of", "json", str(v)])
    o = json.loads(r.stdout or "{}")
    vs = [s for s in o.get("streams", []) if s.get("codec_type") == "video"]
    if not vs:
        sys.exit("O arquivo não tem vídeo: " + str(v))
    w, h = vs[0]["width"], vs[0]["height"]
    num, den = (vs[0].get("r_frame_rate", "30/1") + "/1").split("/")[:2]
    fps = round(float(num) / max(1.0, float(den)), 2)
    prop = w / h
    formato = next((n for n, a in (("9:16", 9 / 16), ("4:5", .8), ("1:1", 1), ("16:9", 16 / 9)) if abs(prop - a) < .03), f"{w}x{h}")
    return {"duracao": round(float(o["format"].get("duration", 0)), 2), "largura": w, "altura": h, "fps": fps,
            "formato": formato, "tem_som": any(s.get("codec_type") == "audio" for s in o.get("streams", []))}


def medir_cortes(v, limiar):
    """Troca de plano pela detecção de cena do ffmpeg. Devolve os tempos (s) em que um plano novo começa.

    Conta como corte: nota de cena acima do limiar, ou (vídeo escuro ou de pouco contraste, em que as notas
    ficam baixas) um pico pelo menos 6 vezes maior que o normal daquele trecho.
    """
    r = roda(["ffmpeg", "-hide_banner", "-i", str(v), "-vf",
              "scale=320:-2,select='gte(scene,0)',metadata=print:key=lavfi.scene_score",
              "-an", "-f", "null", "-"])
    tempos = [float(x) for x in re.findall(r"pts_time:([\d.]+)", r.stderr)]
    notas = [float(x) for x in re.findall(r"lavfi\.scene_score=([\d.]+)", r.stderr)]
    pares = list(zip(tempos, notas))
    ts = []
    for i, (t, s) in enumerate(pares):
        vizinhos = sorted(x for _, x in pares[max(0, i - 12):i] + pares[i + 1:i + 13])
        normal = vizinhos[len(vizinhos) // 2] if vizinhos else 0
        if s >= limiar or (s >= limiar / 4 and s >= 6 * max(normal, 0.004)):
            ts.append(round(t, 2))
    limpos = []
    for t in ts:                      # dois "cortes" a menos de 0,2 s são o mesmo (flash, piscada)
        if t > 0.1 and (not limpos or t - limpos[-1] >= 0.2):
            limpos.append(t)
    return limpos


def medir_som(v, dur):
    """Energia a cada 50 ms e os ataques (som que começa forte: batida, efeito, palavra forte)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(v), "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    a = array.array("h", raw)
    if not a:
        return [], []
    jan = 400                               # 50 ms em 8 kHz
    db = []
    for i in range(0, len(a) - jan + 1, jan):
        bloco = a[i:i + jan]
        e = sum(x * x for x in bloco) / jan
        db.append(10 * math.log10(e / 32768 ** 2 + 1e-12))
    ataques = []
    for i in range(4, len(db)):
        antes = max(db[i - 4:i])
        if db[i] > -35 and db[i] - antes >= 6 and (not ataques or i * .05 - ataques[-1] > .25):
            ataques.append(round(i * .05, 2))
    return db, ataques


def quadro(v, t, saida, largura):
    roda(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(v), "-frames:v", "1",
          "-vf", f"scale={largura}:-2", "-q:v", "3", str(saida)])
    return Path(saida).exists()


def montar_prancha(itens, saida, colunas=6):
    """itens = [(arquivo_jpg, rótulo)]. Com Pillow escreve o tempo em cada quadro; sem Pillow, só junta."""
    itens = [(f, r) for f, r in itens if Path(f).exists()]
    if not itens:
        return False
    try:
        from PIL import Image, ImageDraw, ImageFont
        imgs = [Image.open(f).convert("RGB") for f, _ in itens]
        w, h = imgs[0].size
        lin = math.ceil(len(imgs) / colunas)
        folha = Image.new("RGB", (w * min(colunas, len(imgs)), h * lin), "white")
        try:
            fonte = ImageFont.load_default(size=max(14, w // 12))
        except TypeError:
            fonte = ImageFont.load_default()
        for i, (img, (_, rot)) in enumerate(zip(imgs, itens)):
            x, y = (i % colunas) * w, (i // colunas) * h
            folha.paste(img.resize((w, h)), (x, y))
            d = ImageDraw.Draw(folha)
            caixa = d.textbbox((0, 0), rot, font=fonte)
            d.rectangle([x, y + h - (caixa[3] - caixa[1]) - 10, x + (caixa[2] - caixa[0]) + 12, y + h], fill="black")
            d.text((x + 6, y + h - (caixa[3] - caixa[1]) - 8), rot, fill="white", font=fonte)
        folha.save(saida, quality=85)
        return True
    except ImportError:
        lista = Path(saida).with_suffix(".txt")
        lista.write_text("".join(f"file '{Path(f).resolve()}'\n" for f, _ in itens))
        lin = math.ceil(len(itens) / colunas)
        roda(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
              "-vf", f"tile={colunas}x{lin}", "-frames:v", "1", str(saida)])
        lista.unlink()
        return Path(saida).exists()


def transcrever(v, pasta, idioma):
    py = python_do_estudio()
    script = RAIZ_ESTUDIO / "ferramentas/transcrever.py"
    if not py or not script.exists():
        return None, "sem .venv: rode bash ferramentas/instalar.sh para transcrever"
    r = roda([py, str(script), str(v), str(pasta / "fala.json"), "--idioma", idioma])
    if r.returncode != 0:
        return None, "transcrição falhou: " + ((r.stderr.strip().splitlines() or ["?"])[-1])
    palavras = json.loads((pasta / "fala.json").read_text())
    linhas, atual = [], []
    for p in palavras:
        if atual and (p["s"] - atual[-1]["e"] > .6 or len(atual) >= 14):
            linhas.append(atual); atual = []
        atual.append(p)
    if atual:
        linhas.append(atual)
    # Em vídeo só com música o Whisper costuma "ouvir" frases prontas. Essas linhas saem da conta.
    inventadas = re.compile(r"^(thank you|thanks for watching|obrigad[oa]|tchau|music|musica|legendas? .*|subscribe|"
                            r"inscreva-se.*|you|bye|\W*)$")
    linhas = [l for l in linhas if not inventadas.match(slug(" ".join(p["w"] for p in l), 200).replace("-", " "))]
    if sum(len(l) for l in linhas) < 6:
        (pasta / "fala.txt").write_text("(sem fala: só música ou efeitos)\n")
        return [], "sem fala (só música ou efeitos)"
    palavras = [p for l in linhas for p in l]
    texto = "\n".join(f"{tempo(l[0]['s']):>7}  {' '.join(p['w'] for p in l)}" for l in linhas)
    (pasta / "fala.txt").write_text(texto + "\n")
    return palavras, f"{len(palavras)} palavras"


def medir_tudo(v, pasta, limiar, com_fala, idioma, gravar=True):
    info = sondar(v)
    dur = info["duracao"]
    cortes = medir_cortes(v, limiar)
    planos = [0.0] + cortes
    duracoes = [round(b - a, 2) for a, b in zip(planos, planos[1:] + [dur])]
    _, ataques = medir_som(v, dur) if info["tem_som"] else ([], [])
    no_som = sum(1 for c in cortes if any(abs(c - a) <= .12 for a in ataques))
    m = dict(info)
    m.update({
        "cortes": cortes, "n_cortes": len(cortes),
        "cortes_por_segundo": round(len(cortes) / dur, 2) if dur else 0,
        "plano_medio_s": round(sum(duracoes) / len(duracoes), 2) if duracoes else dur,
        "plano_mais_curto_s": min(duracoes) if duracoes else dur,
        "plano_mais_longo_s": max(duracoes) if duracoes else dur,
        "planos": [{"n": i + 1, "inicio": a, "duracao": d} for i, (a, d) in enumerate(zip(planos, duracoes))],
        "ataques_de_som": ataques,
        "cortes_no_som": no_som,
        "limiar": limiar,
    })
    if not gravar:
        return m
    (pasta / "cortes.txt").write_text("".join(f"{tempo(c)}\t{c:.2f}\n" for c in cortes) or "(nenhum corte seco)\n")
    (pasta / "som.txt").write_text("Ataques de som (s): " + " ".join(f"{a:.2f}" for a in ataques) + "\n")
    tmp = pasta / ".quadros"; tmp.mkdir(exist_ok=True)
    larg = 240 if info["altura"] > info["largura"] else 320
    itens = []
    for i in range(24):
        t = dur * (i + .5) / 24
        f = tmp / f"p{i:02d}.jpg"
        quadro(v, t, f, larg); itens.append((f, tempo(t)))
    m["prancha"] = montar_prancha(itens, pasta / "prancha.jpg")
    passo = max(1, math.ceil(len(m["planos"]) / 36))   # no máximo 36 quadros na folha de planos
    itens = []
    for p in m["planos"][::passo]:
        t = p["inicio"] + min(.4, p["duracao"] / 2)
        f = tmp / f"c{p['n']:03d}.jpg"
        quadro(v, t, f, larg); itens.append((f, f"#{p['n']} {tempo(p['inicio'])}"))
    m["folha_planos"] = montar_prancha(itens, pasta / "planos.jpg") if len(m["planos"]) > 1 else False
    shutil.rmtree(tmp, ignore_errors=True)
    if com_fala and info["tem_som"]:
        palavras, aviso = transcrever(v, pasta, idioma)
    else:
        palavras, aviso = None, "sem transcrição"
    m["fala"] = aviso
    m["_palavras"] = palavras or []
    return m


# ------------------------------------------------------------ ficha
def escrever_ficha(raiz, nome, dados, m, pasta_video, tags, nota, origem):
    fic = raiz / "fichas"; fic.mkdir(parents=True, exist_ok=True)
    arq = fic / f"{nome}.md"; n = 2
    while arq.exists():
        arq = fic / f"{nome}-{n}.md"; n += 1
    rel = os.path.relpath(pasta_video, raiz.parent) if raiz.parent in pasta_video.parents else str(pasta_video)
    pal = m.get("_palavras") or []

    def fala_no(a, b):
        ws = [p["w"] for p in pal if a <= p["s"] < b]
        return (" ".join(ws[:10]) + (" …" if len(ws) > 10 else "")) if ws else ""

    linhas_planos = []
    for p in m["planos"][:40]:
        fim = p["inicio"] + p["duracao"]
        f = fala_no(p["inicio"], fim)
        dura = f"{p['duracao']:.1f}".replace(".", ",")
        linhas_planos.append(f"| {p['n']} | {tempo(p['inicio'])} | {dura} s | (preencher) | {f} |")
    if len(m["planos"]) > 40:
        linhas_planos.append(f"| … | | | mais {len(m['planos']) - 40} planos em `cortes.txt` | |")
    fala_txt = (pasta_video / "fala.txt")
    fala = fala_txt.read_text().rstrip() if fala_txt.exists() else m.get("fala", "—")
    if len(fala) > 3000:
        fala = fala[:3000] + "\n… (resto em fala.txt)"
    hoje = datetime.date.today().isoformat()
    titulo = dados.get("titulo") or nome
    cps = f"{m['cortes_por_segundo']:.2f}".replace(".", ",")
    md = f"""---
titulo: {titulo.replace(chr(10), ' ')[:120]}
link: {dados.get('link') or '—'}
autor: {dados.get('autor') or '—'}
publicado: {dados.get('publicado') or '—'}
baixado: {hoje}
origem: {origem}
licenca: {dados.get('licenca') or 'não informada (tratar como todos os direitos reservados)'}
duracao_s: {m['duracao']}
formato: {m['formato']}
cortes: {m['n_cortes']}
cortes_por_segundo: {m['cortes_por_segundo']}
tags: {', '.join(tags)}
pasta: {rel}
---

# {titulo}

Em uma frase: (preencher: o que é e por que vale estudar)

{('Por que guardei: ' + nota + chr(10)) if nota else ''}
## Medido pelo script

- Duração: {br(m['duracao'])} s · {m['formato']} · {m['largura']}×{m['altura']} · {br(m['fps'])} fps · {'com som' if m['tem_som'] else 'sem som'}
- Cortes: {m['n_cortes']} ({cps} por segundo) · plano médio {br(m['plano_medio_s'], 1)} s · mais curto {br(m['plano_mais_curto_s'], 1)} s · mais longo {br(m['plano_mais_longo_s'], 1)} s
- Cortes junto de um ataque de som: {m['cortes_no_som']} de {m['n_cortes']}
- Fala: {m.get('fala')}
- Arquivos: `{rel}/` → `prancha.jpg` (24 quadros com o tempo), `planos.jpg` (1 quadro por plano), `cortes.txt`, `fala.txt`, `meta.json`

## Estrutura cena a cena

| # | começa | dura | o que aparece e como entra | fala |
|---|---|---|---|---|
""" + "\n".join(linhas_planos) + f"""

## Tipografia

(preencher: família parecida, peso, caixa alta ou baixa, tamanho em relação à tela, posição, como a palavra entra)

## Cor

(preencher: fundo, cor de destaque, quantas cores, contraste)

## Som

(preencher: tem trilha? efeito em cada corte? voz na frente? silêncio em algum ponto?)

## Fala

```
{fala}
```

## Por que prende

(preencher: o gancho dos primeiros 2 s, o que segura até o fim, onde o ritmo muda)

## O que copiar (linguagem)

(preencher: ritmo dos cortes, jeito de a letra entrar, tipo de som, estrutura. Isso é linguagem e pode ir para o seu vídeo)

## O que não copiar

A imagem, a música, a voz, a marca, o logotipo e o texto do autor. O vídeo baixado é só para estudo e não entra em nenhum trabalho.

## Tags

{', '.join(tags) or '(preencher)'}
"""
    arq.write_text(md)
    return arq


# ------------------------------------------------------------ principal
def main():
    ap = argparse.ArgumentParser(description="Baixa e mede uma referência de vídeo.")
    ap.add_argument("link", nargs="?")
    ap.add_argument("--arquivo", help="vídeo seu (referência própria), sem baixar")
    ap.add_argument("--so-medir", help="só mede um vídeo e mostra na tela; não grava nada")
    ap.add_argument("--tag", action="append", default=[])
    ap.add_argument("--nota", default="")
    ap.add_argument("--idioma", default="pt")
    ap.add_argument("--cookies-navegador", dest="cookies")
    ap.add_argument("--sem-fala", action="store_true")
    ap.add_argument("--limiar", type=float, default=0.3)
    ap.add_argument("--raiz", default=str(RAIZ_ESTUDIO / "referencias"))
    a = ap.parse_args()

    if a.so_medir:
        m = medir_tudo(Path(a.so_medir), None, a.limiar, False, a.idioma, gravar=False)
        m.pop("_palavras", None); m.pop("planos", None)
        print(json.dumps(m, ensure_ascii=False, indent=1)); return
    if not a.link and not a.arquivo:
        ap.print_help(); sys.exit(1)

    raiz = Path(a.raiz).resolve()
    videos = raiz / "videos"; videos.mkdir(parents=True, exist_ok=True)
    tags = [slug(t, 30) for t in a.tag]
    hoje = datetime.date.today().isoformat()

    if a.link:
        if "instagram.com" in a.link and not a.cookies:
            sys.exit("Instagram pede login. Só com a SUA conta e se você quiser: rode de novo com --cookies-navegador chrome "
                     "(ou safari/firefox). O yt-dlp lê o login do navegador só para este download.")
        tmp = Path(tempfile.mkdtemp(prefix=".baixando-", dir=videos))
        dados = baixar(a.link, tmp, a.cookies)
        nome = slug(f"{dados['autor'].lstrip('@')} {dados['titulo']}")
        pasta = videos / f"{hoje}-{nome}"; n = 2
        while pasta.exists():
            pasta = videos / f"{hoje}-{nome}-{n}"; n += 1
        tmp.rename(pasta)
        v = pasta / "video.mp4"
        origem = "terceiro"
    else:
        v = Path(a.arquivo).resolve()
        if not v.exists():
            sys.exit("Arquivo não encontrado: " + a.arquivo)
        nome = slug(v.stem)
        pasta = videos / f"{hoje}-{nome}"; pasta.mkdir(exist_ok=True)
        dados = {"link": f"(vídeo próprio: {os.path.relpath(v, RAIZ_ESTUDIO) if RAIZ_ESTUDIO in v.parents else v.name})",
                 "autor": "você", "titulo": v.stem, "publicado": "", "licenca": "vídeo seu"}
        origem = "proprio"

    print(f"medindo {v.name}…")
    m = medir_tudo(v, pasta, a.limiar, not a.sem_fala, a.idioma)
    meta = {k: val for k, val in m.items() if k != "_palavras"}
    meta.update({"dados": dados, "tags": tags, "nota": a.nota, "origem": origem, "baixado": hoje})
    (pasta / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    ficha = escrever_ficha(raiz, nome, dados, m, pasta, tags, a.nota, origem)
    fichas.indice(raiz)
    print(f"ok · {m['duracao']} s · {m['n_cortes']} cortes ({m['cortes_por_segundo']}/s) · fala: {m['fala']}")
    print(f"pasta:   {pasta}")
    print(f"prancha: {pasta / 'prancha.jpg'}")
    if m.get("folha_planos"):
        print(f"planos:  {pasta / 'planos.jpg'}")
    print(f"ficha:   {ficha}  (complete os campos 'preencher')")


if __name__ == "__main__":
    main()
