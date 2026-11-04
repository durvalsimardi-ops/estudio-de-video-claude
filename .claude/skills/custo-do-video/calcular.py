#!/usr/bin/env python3
"""Custo de um vídeo e preço com margem.

Uso: python3 calcular.py --minutos 40 --hora 60 [--creditos 120 --preco-credito 0.05]
                         [--assinaturas 330 --videos-mes 20] [--margem 50]
Valores em reais. --margem é a porcentagem somada ao custo para chegar no preço.
"""
import argparse

p = argparse.ArgumentParser(description="Custo e preço de um vídeo")
p.add_argument("--minutos", type=float, required=True, help="minutos de trabalho no vídeo")
p.add_argument("--hora", type=float, required=True, help="valor da sua hora, em R$")
p.add_argument("--creditos", type=float, default=0, help="créditos gastos no vídeo")
p.add_argument("--preco-credito", type=float, default=0, help="preço de 1 crédito, em R$")
p.add_argument("--assinaturas", type=float, default=0, help="soma das assinaturas do mês, em R$")
p.add_argument("--videos-mes", type=float, default=0, help="vídeos feitos por mês")
p.add_argument("--margem", type=float, default=0, help="margem sobre o custo, em %%")
a = p.parse_args()

brl = lambda v: ("R$ " + f"{v:,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")
tempo = a.minutos / 60 * a.hora
creditos = a.creditos * a.preco_credito
fixo = a.assinaturas / a.videos_mes if a.videos_mes else 0
custo = tempo + creditos + fixo
print(f"Tempo:        {brl(tempo)}  ({a.minutos:g} min a {brl(a.hora)}/h)")
print(f"Créditos:     {brl(creditos)}")
print(f"Assinaturas:  {brl(fixo)}  por vídeo")
print(f"Custo:        {brl(custo)}")
if a.margem:
    print(f"Preço com {a.margem:g}% de margem: {brl(custo * (1 + a.margem / 100))}")
