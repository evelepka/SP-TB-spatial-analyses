"""Quantificar a concentração de TB GSP em áreas vulneráveis e em aglomerados urbanos (FCU).

Perguntas:
  1) Qual a % dos casos de TB da GSP que ocorre em FCU (favelas/comunidades urbanas IBGE 2022)?
  2) Qual a % dos casos em áreas top X% pelo índice composto de vulnerabilidade?
  3) Quão maior é a taxa nessas áreas vs resto?
"""

import pandas as pd
import numpy as np

sp = pd.read_csv("/tmp/setores_priorizados_GSP.csv",
                 dtype={"CD_SETOR": str}, low_memory=False)
print(f"Setores na análise: {len(sp):,}")
print(f"Pop GSP coberta:    {sp['v0001'].sum():,.0f}")
print(f"Casos GSP atribuídos: {sp['n_cases'].sum():,.0f}")
print()

total_pop = sp["v0001"].sum()
total_cases = sp["n_cases"].sum()
total_py = total_pop * 5
taxa_gsp = total_cases / total_py * 1e5
print(f"Taxa média GSP: {taxa_gsp:.1f}/100k pa")
print()
print("=" * 90)
print("1) FCU — Favelas e Comunidades Urbanas (definição IBGE Censo 2022)")
print("=" * 90)
fcu = sp[sp["is_fcu"] == 1]
non = sp[sp["is_fcu"] == 0]
fcu_pop, fcu_cases = fcu["v0001"].sum(), fcu["n_cases"].sum()
non_pop, non_cases = non["v0001"].sum(), non["n_cases"].sum()
taxa_fcu = fcu_cases / (fcu_pop * 5) * 1e5
taxa_non = non_cases / (non_pop * 5) * 1e5
print(f"\n  {'Pop em FCU':<35}: {fcu_pop:>11,.0f} ({fcu_pop/total_pop*100:.1f}% da GSP)")
print(f"  {'Pop fora FCU':<35}: {non_pop:>11,.0f} ({non_pop/total_pop*100:.1f}% da GSP)")
print(f"\n  {'Casos em FCU':<35}: {fcu_cases:>11,.0f} ({fcu_cases/total_cases*100:.1f}% do total)")
print(f"  {'Casos fora FCU':<35}: {non_cases:>11,.0f} ({non_cases/total_cases*100:.1f}% do total)")
print(f"\n  {'Taxa em FCU':<35}: {taxa_fcu:>11.1f}/100k pa")
print(f"  {'Taxa fora FCU':<35}: {taxa_non:>11.1f}/100k pa")
print(f"  {'Razão de taxas (FCU/não-FCU)':<35}: {taxa_fcu/taxa_non:>11.2f}×")
print(f"\n  → FCU concentra {fcu_pop/total_pop*100:.1f}% da pop e {fcu_cases/total_cases*100:.1f}% dos casos.")
print(f"  → Quem mora em FCU tem {taxa_fcu/taxa_non:.1f}× mais risco de TB.")

print()
print("=" * 90)
print("2) ÍNDICE COMPOSTO de vulnerabilidade — z(-renda) + z(densidade) + z(FCU)")
print("=" * 90)
print(f"\n{'Target % pop':>12} {'N setores':>10} {'Pop':>13} {'Casos':>9} {'% casos':>9} "
      f"{'Taxa /100k pa':>14} {'Razão vs resto':>16}")
print("-" * 95)

sp_sorted = sp.sort_values("vuln_score", ascending=False).copy()
sp_sorted["cum_pop"] = sp_sorted["v0001"].cumsum()

for pct in [1, 2, 5, 10, 15, 20, 25, 30, 50]:
    target = total_pop * pct / 100
    sub = sp_sorted[sp_sorted["cum_pop"] <= target]
    rest = sp_sorted[sp_sorted["cum_pop"] > target]
    if len(sub) == 0:
        continue
    pop_s, cas_s = sub["v0001"].sum(), sub["n_cases"].sum()
    pop_r, cas_r = rest["v0001"].sum(), rest["n_cases"].sum()
    tx_s = cas_s / (pop_s * 5) * 1e5
    tx_r = cas_r / (pop_r * 5) * 1e5
    pct_c = cas_s / total_cases * 100
    print(f"{pct:>11}% {len(sub):>10,} {pop_s:>13,.0f} {cas_s:>9,.0f} "
          f"{pct_c:>8.1f}% {tx_s:>13.1f} {tx_s/tx_r:>15.2f}×")

print()
print("=" * 90)
print("3) HOTSPOTS EMPÍRICOS — top 5% pop por TAXA observada de TB (a posteriori)")
print("=" * 90)

sp_inc = sp[sp["n_cases"] > 0].sort_values("rate_per_100k", ascending=False).copy()
sp_inc["cum_pop"] = sp_inc["v0001"].cumsum()
hot = sp_inc[sp_inc["cum_pop"] <= total_pop * 0.05]
nh = sp[~sp["CD_SETOR"].isin(hot["CD_SETOR"])]
pop_h, cas_h = hot["v0001"].sum(), hot["n_cases"].sum()
pop_n, cas_n = nh["v0001"].sum(), nh["n_cases"].sum()
tx_h = cas_h / (pop_h * 5) * 1e5
tx_n = cas_n / (pop_n * 5) * 1e5
print(f"\n  N setores hotspot:           {len(hot):>11,}")
print(f"  Pop hotspot:                 {pop_h:>11,.0f} ({pop_h/total_pop*100:.1f}% da GSP)")
print(f"  Casos hotspot:               {cas_h:>11,.0f} ({cas_h/total_cases*100:.1f}% do total)")
print(f"  Taxa nos hotspots:           {tx_h:>11.1f}/100k pa")
print(f"  Taxa no resto:               {tx_n:>11.1f}/100k pa")
print(f"  Razão hotspots/resto:        {tx_h/tx_n:>11.2f}×")

print()
print("=" * 90)
print("4) Sobreposição: FCU × Hotspots empíricos × Top vulnerabilidade")
print("=" * 90)

vuln5 = set(sp_sorted.head(int(len(sp_sorted)*0.05))["CD_SETOR"])  # top 5% por nº
top5_pop = sp_sorted[sp_sorted["cum_pop"] <= total_pop*0.05]
vuln5p = set(top5_pop["CD_SETOR"])  # top 5% pop
hot5 = set(hot["CD_SETOR"])
fcu_set = set(sp[sp["is_fcu"]==1]["CD_SETOR"])

print(f"\nN setores em cada categoria:")
print(f"  FCU IBGE:                       {len(fcu_set):>7,}")
print(f"  Hotspots empíricos (top 5% pop):{len(hot5):>7,}")
print(f"  Top 5% pop pelo índice:         {len(vuln5p):>7,}")

print(f"\nSobreposições:")
print(f"  FCU ∩ Hotspots:                 {len(fcu_set & hot5):>7,} "
      f"({len(fcu_set & hot5)/len(hot5)*100:.1f}% dos hotspots são FCU)")
print(f"  Top vuln ∩ Hotspots:            {len(vuln5p & hot5):>7,} "
      f"({len(vuln5p & hot5)/len(hot5)*100:.1f}% dos hotspots são top-vuln)")
print(f"  FCU ∩ Top vuln:                 {len(fcu_set & vuln5p):>7,}")
print(f"  Os três (FCU ∩ Hot ∩ TopVuln):  {len(fcu_set & hot5 & vuln5p):>7,}")

# Frações por categoria do total de casos
hot_cases  = sp[sp["CD_SETOR"].isin(hot5)]["n_cases"].sum()
fcu_cases  = sp[sp["CD_SETOR"].isin(fcu_set)]["n_cases"].sum()
vuln_cases = sp[sp["CD_SETOR"].isin(vuln5p)]["n_cases"].sum()
union_cases = sp[sp["CD_SETOR"].isin(hot5 | fcu_set | vuln5p)]["n_cases"].sum()
union_pop = sp[sp["CD_SETOR"].isin(hot5 | fcu_set | vuln5p)]["v0001"].sum()

print(f"\n% casos GSP capturados:")
print(f"  Apenas FCU:                  {fcu_cases/total_cases*100:>5.1f}%  "
      f"(pop {fcu['v0001'].sum()/total_pop*100:.1f}%)")
print(f"  Apenas Hotspots:             {hot_cases/total_cases*100:>5.1f}%  "
      f"(pop {pop_h/total_pop*100:.1f}%)")
print(f"  Apenas Top 5% vuln:          {vuln_cases/total_cases*100:>5.1f}%  "
      f"(pop {top5_pop['v0001'].sum()/total_pop*100:.1f}%)")
print(f"  União das 3 categorias:      {union_cases/total_cases*100:>5.1f}%  "
      f"(pop {union_pop/total_pop*100:.1f}%)")
