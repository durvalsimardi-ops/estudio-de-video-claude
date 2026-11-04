#!/usr/bin/env python3
"""Índice e busca das fichas de referência.

Uso (na raiz do estúdio):
  .venv/bin/python .claude/skills/referencias/scripts/fichas.py indice            → refaz referencias/INDICE.md
  .venv/bin/python .claude/skills/referencias/scripts/fichas.py buscar meia tela  → fichas com essa tag ou esse assunto
  .venv/bin/python .claude/skills/referencias/scripts/fichas.py listar            → todas, uma por linha
  --raiz <pasta>  usa outra pasta de referências (padrão: referencias/ do estúdio)

A tag manda: "meia tela", "meia-tela" e "Meia Tela" são a mesma coisa.
"""
import datetime, re, sys, unicodedata
from pathlib import Path

RAIZ_ESTUDIO = Path(__file__).resolve().parents[4]


def normal(s):
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def ler(arq):
    """Lê o cabeçalho (entre as linhas ---) e o corpo de uma ficha."""
    texto = Path(arq).read_text()
    dados, corpo = {}, texto
    m = re.match(r"---\n(.*?)\n---\n(.*)", texto, re.S)
    if m:
        corpo = m.group(2)
        for linha in m.group(1).splitlines():
            if ":" in linha:
                k, v = linha.split(":", 1)
                dados[k.strip()] = v.strip()
    dados["tags_lista"] = [t.strip() for t in dados.get("tags", "").split(",") if t.strip()]
    dados["arquivo"] = Path(arq)
    dados["corpo"] = corpo
    return dados


def todas(raiz):
    pasta = Path(raiz) / "fichas"
    return [ler(f) for f in sorted(pasta.glob("*.md")) if not f.name.startswith("_")]


def resumo(f, raiz):
    dur = f.get("duracao_s", "?")
    cps = f.get("cortes_por_segundo", "?").replace(".", ",")
    rel = f["arquivo"].relative_to(Path(raiz)).as_posix()
    return f"[{f.get('titulo', f['arquivo'].stem)}]({rel}) · {f.get('origem', '?')} · {dur} s · {cps} cortes/s"


def indice(raiz=RAIZ_ESTUDIO / "referencias"):
    raiz = Path(raiz)
    fs = todas(raiz)
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    out = ["# Índice das referências", "",
           "Gerado pela skill /referencias. Não edite à mão: mude a ficha e peça para refazer o índice.", "",
           f"{len(fs)} ficha(s) · atualizado em {hoje}.", "",
           "Origem: `curso` (estilo das aulas), `proprio` (vídeo seu), `terceiro` (só estudo, nunca entra no trabalho).", "",
           "## Todas", "", "| Ficha | Origem | Duração | Cortes/s | Tags |", "|---|---|---|---|---|"]
    for f in fs:
        rel = f["arquivo"].relative_to(raiz).as_posix()
        out.append(f"| [{f.get('titulo', f['arquivo'].stem)}]({rel}) | {f.get('origem', '?')} | {f.get('duracao_s', '?')} s | "
                   f"{f.get('cortes_por_segundo', '?').replace('.', ',')} | {', '.join(f['tags_lista'])} |")
    out += ["", "## Por tag", ""]
    por_tag = {}
    for f in fs:
        for t in f["tags_lista"] or ["sem-tag"]:
            por_tag.setdefault(t, []).append(f)
    for t in sorted(por_tag):
        out.append(f"### {t}")
        out += [f"- {resumo(f, raiz)}" for f in por_tag[t]]
        out.append("")
    (raiz / "INDICE.md").write_text("\n".join(out))
    return raiz / "INDICE.md"


def buscar(termos, raiz=RAIZ_ESTUDIO / "referencias"):
    q = normal(" ".join(termos))
    palavras = q.split()
    fortes, fracos = [], []
    for f in todas(raiz):
        tags = [normal(t) for t in f["tags_lista"]]
        pontos = 0
        if q in tags:
            pontos += 10                                    # tag exata
        pontos += 4 * sum(1 for t in tags if t != q and (q in t or t in q.split() or t in q))
        if q and q in normal(f.get("titulo", "")):
            pontos += 5
        if pontos:
            fortes.append((pontos, f)); continue
        corpo = normal(f["corpo"])
        uteis = [p for p in palavras if len(p) > 2]
        if uteis and all(p in corpo for p in uteis):        # no texto: só se tiver todas as palavras
            fracos.append((sum(corpo.count(p) for p in uteis), f))
    achados = fortes or fracos                              # tag e título primeiro; texto só se nada bater
    achados.sort(key=lambda x: -x[0])
    return [f for _, f in achados]


def main():
    args = sys.argv[1:]
    raiz = RAIZ_ESTUDIO / "referencias"
    if "--raiz" in args:
        i = args.index("--raiz"); raiz = Path(args[i + 1]).resolve(); del args[i:i + 2]
    if not args:
        print(__doc__); sys.exit(1)
    cmd, resto = args[0], args[1:]
    if cmd == "indice":
        print("ok ·", indice(raiz))
    elif cmd == "listar":
        for f in todas(raiz):
            print(f"{f['arquivo'].stem:32} {f.get('origem', '?'):9} {', '.join(f['tags_lista'])}")
    elif cmd == "buscar":
        if not resto:
            sys.exit("diga o que buscar: fichas.py buscar meia tela")
        r = buscar(resto, raiz)
        if not r:
            print("Nenhuma ficha com isso. Tags existentes:",
                  ", ".join(sorted({t for f in todas(raiz) for t in f["tags_lista"]})) or "nenhuma")
            return
        for f in r:
            print(f"- {f['arquivo']}\n    {f.get('titulo', '')} · tags: {', '.join(f['tags_lista'])} · "
                  f"{f.get('duracao_s', '?')} s · {f.get('cortes_por_segundo', '?')} cortes/s · origem {f.get('origem', '?')}")
    else:
        print(__doc__); sys.exit(1)


if __name__ == "__main__":
    main()
