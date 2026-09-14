"""Anatomia dos hotspots e dos 19% de casos em FCU.

Responde:
  Q1) Os 2.501 setores hotspot agregam em quais BAIRROS? (top 30)
  Q2) Os 19% dos casos em FCU estão concentrados em quantas FCUs distintas?
  Q3) Qual a distribuição empírica: top N bairros pegam quantos % dos casos?
"""

import pandas as pd
import geopandas as gpd
import unicodedata, re

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"


def norm(s):
    if pd.isna(s):
        return None
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s)


sp = pd.read_csv("/tmp/setores_priorizados_GSP.csv",
                 dtype={"CD_SETOR": str}, low_memory=False)

# Recupera NM_BAIRRO e NM_FCU via shapefile
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)
sp = sp.merge(sec22[["CD_SETOR", "NM_BAIRRO", "NM_FCU"]].rename(
              columns={"NM_BAIRRO":"NM_BAIRRO_geo", "NM_FCU":"NM_FCU_geo"}),
              on="CD_SETOR", how="left")

# Usa NM_BAIRRO existente (já do shapefile) ou o do merge
sp["bairro"] = sp["NM_BAIRRO"].fillna(sp["NM_BAIRRO_geo"])
sp["fcu"] = sp["NM_FCU"].fillna(sp["NM_FCU_geo"])

# Reidentifica hotspots (top 5% pop)
total_pop = sp["v0001"].sum()
sp_inc = sp[sp["n_cases"] > 0].sort_values("rate_per_100k", ascending=False).copy()
sp_inc["cum_pop"] = sp_inc["v0001"].cumsum()
hot_setores = set(sp_inc[sp_inc["cum_pop"] <= total_pop * 0.05]["CD_SETOR"])
sp["is_hot"] = sp["CD_SETOR"].isin(hot_setores)
hot = sp[sp["is_hot"]]
total_cases = sp["n_cases"].sum()
hot_cases = hot["n_cases"].sum()

print(f"Hotspots: {len(hot):,} setores, {hot['v0001'].sum():,.0f} pessoas, "
      f"{hot_cases:,.0f} casos ({hot_cases/total_cases*100:.1f}% do total GSP)\n")

# ============================================================
# Q1 — Em QUAIS BAIRROS estão os hotspots?
# ============================================================
print("="*92)
print("Q1) BAIRROS que concentram os 2.501 setores hotspot")
print("="*92)

hot_bairro = hot.groupby(["NM_MUN", "bairro"]).agg(
    n_setores=("CD_SETOR", "count"),
    pop=("v0001", "sum"),
    casos=("n_cases", "sum"),
).reset_index().sort_values("casos", ascending=False)
hot_bairro["taxa"] = hot_bairro["casos"] / (hot_bairro["pop"] * 5) * 1e5
hot_bairro["cum_pct_casos"] = hot_bairro["casos"].cumsum() / hot_cases * 100

print(f"\n{'#':>2} {'Município':<22} {'Bairro':<32} {'Setores':>7} {'Pop':>9} "
      f"{'Casos':>6} {'Taxa':>7} {'%cum':>6}")
print("-" * 95)
for i, r in enumerate(hot_bairro.head(30).itertuples(), 1):
    b = str(r.bairro) if pd.notna(r.bairro) else "(sem bairro)"
    print(f"{i:>2} {str(r.NM_MUN)[:22]:<22} {b[:32]:<32} "
          f"{int(r.n_setores):>7,} {int(r.pop):>9,} {int(r.casos):>6,} "
          f"{r.taxa:>7.0f} {r.cum_pct_casos:>5.1f}%")

print(f"\nTotal bairros distintos com pelo menos 1 setor hotspot: "
      f"{hot_bairro['bairro'].nunique():,}")
print(f"Top 30 bairros pegam {hot_bairro.head(30)['casos'].sum()/hot_cases*100:.1f}% "
      f"dos casos-hotspot.")

# ============================================================
# Q2 — Os 19% (8.305) de casos em FCU estão em quantas FCUs?
# ============================================================
print()
print("="*92)
print("Q2) Anatomia dos 8.305 casos em FCU — em quantas favelas distintas?")
print("="*92)

fcu_cases = sp[sp["is_fcu"] == 1].copy()
fcu_dist = fcu_cases.groupby(["NM_MUN", "fcu"]).agg(
    n_setores=("CD_SETOR", "count"),
    pop=("v0001", "sum"),
    casos=("n_cases", "sum"),
).reset_index().sort_values("casos", ascending=False)
fcu_dist["taxa"] = fcu_dist["casos"] / (fcu_dist["pop"] * 5) * 1e5
total_fcu_casos = fcu_dist["casos"].sum()
fcu_dist["cum_pct"] = fcu_dist["casos"].cumsum() / total_fcu_casos * 100

print(f"\nTotal de FCUs distintas (com população residente): {len(fcu_dist):,}")
print(f"Total casos em FCU: {total_fcu_casos:,.0f}")

# Quantas FCUs até cobrir 50%, 80%, 90% dos casos-FCU
for cut in [25, 50, 75, 90]:
    n = (fcu_dist["cum_pct"] <= cut).sum()
    print(f"  Para cobrir {cut}% dos casos em FCU: {n:,} FCUs "
          f"({n/len(fcu_dist)*100:.1f}% do total)")

print(f"\n{'#':>2} {'Município':<22} {'FCU':<37} {'Setores':>7} {'Pop':>9} "
      f"{'Casos':>6} {'Taxa':>7} {'%cum':>6}")
print("-" * 100)
for i, r in enumerate(fcu_dist.head(25).itertuples(), 1):
    f = str(r.fcu) if pd.notna(r.fcu) else "(sem nome)"
    print(f"{i:>2} {str(r.NM_MUN)[:22]:<22} {f[:37]:<37} "
          f"{int(r.n_setores):>7,} {int(r.pop):>9,} {int(r.casos):>6,} "
          f"{r.taxa:>7.0f} {r.cum_pct:>5.1f}%")

# ============================================================
# Q3 — Top bairros GSP por casos absolutos (sem filtrar hotspot)
# ============================================================
print()
print("="*92)
print("Q3) Top BAIRROS GSP por casos absolutos (a estratégia 'pegar onde tem mais TB')")
print("="*92)
all_bairro = sp.groupby(["NM_MUN", "bairro"]).agg(
    n_setores=("CD_SETOR", "count"),
    pop=("v0001", "sum"),
    casos=("n_cases", "sum"),
).reset_index().sort_values("casos", ascending=False)
all_bairro["taxa"] = all_bairro["casos"] / (all_bairro["pop"] * 5) * 1e5
all_bairro["cum_casos_pct"] = all_bairro["casos"].cumsum() / total_cases * 100
all_bairro["cum_pop_pct"] = all_bairro["pop"].cumsum() / total_pop * 100

# Quantos bairros até cobrir 50/80%
for cut in [25, 50, 80]:
    n = (all_bairro["cum_casos_pct"] <= cut).sum()
    pop_pct = all_bairro.iloc[:n+1]["pop"].sum() / total_pop * 100
    print(f"  Para cobrir {cut}% dos casos GSP: top {n:,} bairros "
          f"({pop_pct:.1f}% da pop)")

print(f"\n{'#':>2} {'Município':<22} {'Bairro':<32} {'Pop':>9} {'Casos':>6} "
      f"{'Taxa':>7} {'%cumC':>7} {'%cumP':>7}")
print("-" * 100)
for i, r in enumerate(all_bairro.head(20).itertuples(), 1):
    b = str(r.bairro) if pd.notna(r.bairro) else "(sem bairro)"
    print(f"{i:>2} {str(r.NM_MUN)[:22]:<22} {b[:32]:<32} "
          f"{int(r.pop):>9,} {int(r.casos):>6,} {r.taxa:>7.0f} "
          f"{r.cum_casos_pct:>6.1f}% {r.cum_pop_pct:>6.1f}%")

hot_bairro.to_csv("/tmp/hotspots_por_bairro.csv", index=False)
fcu_dist.to_csv("/tmp/casos_por_FCU.csv", index=False)
all_bairro.to_csv("/tmp/casos_por_bairro_GSP.csv", index=False)
print(f"\nSalvos: /tmp/hotspots_por_bairro.csv ({len(hot_bairro):,} bairros)")
print(f"        /tmp/casos_por_FCU.csv ({len(fcu_dist):,} FCUs)")
print(f"        /tmp/casos_por_bairro_GSP.csv ({len(all_bairro):,} bairros)")
