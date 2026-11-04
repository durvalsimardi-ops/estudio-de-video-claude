#!/usr/bin/env python3
"""Acha na transcrição o tempo de cada palavra-chave e monta a lista de cenas.

Uso:
  .venv/bin/python ferramentas/marcar_palavras.py <transcricao.json> <cenas.json> "chave" "chave=TEXTO NA TELA" ...
    [--segura 1.8] [--campo texto]

- chave: palavra (ou palavras seguidas) como foi falada. Acento, maiúscula e pontuação não importam.
- =TEXTO: o que aparece na tela (sem isso, usa a palavra falada).
- As chaves são procuradas na ordem: a segunda só depois da primeira, e assim por diante.
- --segura: quanto tempo a cena fica depois da palavra, se a próxima não vier antes (padrão 1,8 s).
- --campo: nome do campo do valor (use --campo arquivo para adesivos: "cafe=assets/adesivos/xicara.png").

Saída: [{"texto": "...", "chave": "...", "inicio": s, "fim": s}]
"""
import json, sys, unicodedata

args = sys.argv[1:]


def opt(nome, padrao):
    if nome in args:
        i = args.index(nome)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return padrao


SEGURA = float(opt("--segura", "1.8"))
CAMPO = opt("--campo", "texto")
if len(args) < 3:
    print(__doc__)
    sys.exit(1)


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return "".join(c for c in s if c.isalnum() or c == " ").strip()


palavras = json.load(open(args[0]))
ditas = [norm(p["w"]) for p in palavras]
cenas, depois = [], 0
for pedido in args[2:]:
    chave, _, valor = pedido.partition("=")
    alvo = norm(chave).split()
    achou = None
    for i in range(depois, len(ditas) - len(alvo) + 1):
        if ditas[i:i + len(alvo)] == alvo:
            achou = i
            break
    if achou is None:
        print(f"  não achei «{chave}» depois de {palavras[depois - 1]['e'] if depois else 0:.1f} s")
        continue
    p0, p1 = palavras[achou], palavras[achou + len(alvo) - 1]
    texto = valor or " ".join(p["w"] for p in palavras[achou:achou + len(alvo)]).strip(" ,.!?;:")
    cenas.append({CAMPO: texto, "chave": chave, "inicio": round(max(0, p0["s"] - 0.08), 2), "fim_fala": p1["e"]})
    depois = achou + len(alvo)

for i, c in enumerate(cenas):
    limite = cenas[i + 1]["inicio"] - 0.05 if i + 1 < len(cenas) else c["fim_fala"] + SEGURA
    c["fim"] = round(min(c.pop("fim_fala") + SEGURA, limite), 2)
    print(f"  {c['inicio']:6.2f}–{c['fim']:6.2f}  {c[CAMPO]}")

json.dump(cenas, open(args[1], "w"), ensure_ascii=False, indent=1)
print(f"ok · {len(cenas)} cenas · {args[1]}")
