"""Identificar áreas (setores e bairros) de alta incidência de TB usando o setor CNEFE
corrigido, e caracterizar o perfil de vulnerabilidade desses hotspots.

Inputs:
  - /tmp/cohort_with_cnefe.csv (51k casos com setor_cnefe corrigido)
  - IBGE 2022 agregados: pop (v0001), densidade habitacional (v0005), renda (V06004)
  - SP_setores_CD2022.shp: polígonos + NM_BAIRRO + NM_FCU
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import json
import zipfile
import io
import unicodedata, re

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
IBGE_EXT = f"{SPATIAL}/IBGE_2022_extended"


def norm(s):
    if pd.isna(s):
        return None
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s)


# ========== 1) Cohort com CNEFE ==========
print("Carregando cohort com CNEFE matching...")
co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False)
print(f"  Total cohort: {len(co):,}")

# Filtrar para casos com setor_cnefe (matched)
co_m = co[co["setor_cnefe"].notna()].copy()
print(f"  Com setor_cnefe matched: {len(co_m):,}")

# Normaliza setor — CNEFE usa "350308XXXXXXX0XXXP" format (15 char + 1 'P')
# IBGE shapefile usa apenas 15 chars
def norm_setor(s):
    if pd.isna(s):
        return None
    s = str(s).strip()
    # Remove o "P" sufixo se houver
    if s.endswith("P"):
        s = s[:-1]
    return s

co_m["setor_norm"] = co_m["setor_cnefe"].apply(norm_setor)
print(f"  Setores únicos com casos: {co_m['setor_norm'].nunique():,}")

# ========== 2) IBGE 2022: pop, densidade, renda ==========
print("\nCarregando IBGE 2022 agregados básicos + renda...")
agg = pd.read_csv(
    f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
    sep=";", encoding="latin-1", decimal=",",
    usecols=["CD_SETOR", "v0001", "v0005"],
    dtype={"CD_SETOR": str}, low_memory=False,
)
agg["v0001"] = pd.to_numeric(agg["v0001"], errors="coerce").fillna(0)
agg["v0005"] = pd.to_numeric(agg["v0005"], errors="coerce")

# Renda do responsável
with zipfile.ZipFile(f"{IBGE_EXT}/renda_responsavel.zip") as z:
    fname = [n for n in z.namelist() if n.endswith(".csv")][0]
    with z.open(fname) as f:
        renda = pd.read_csv(io.TextIOWrapper(f, encoding="latin-1"),
                            sep=";", decimal=",",
                            usecols=["CD_SETOR", "V06004"],
                            dtype={"CD_SETOR": str}, low_memory=False)
renda["renda_2022"] = pd.to_numeric(renda["V06004"], errors="coerce")
agg = agg.merge(renda[["CD_SETOR", "renda_2022"]], on="CD_SETOR", how="left")

# Shapefile: CD_MUN, NM_BAIRRO, NM_FCU, área
print("Carregando shapefile setores...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"] = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)
sec22["AREA_KM2"] = pd.to_numeric(sec22["AREA_KM2"], errors="coerce")
gsp_munis = set(sec22[sec22["NM_CONCURB"] == "São Paulo/SP"]["CD_MUN"].unique())
sec_gsp = sec22[sec22["CD_MUN"].isin(gsp_munis)].copy()

# Merge: setor + agregados
sec_gsp = sec_gsp.merge(agg, on="CD_SETOR", how="left")
sec_gsp["is_fcu"] = sec_gsp["NM_FCU"].notna()

# ========== 3) Contar casos por setor ==========
print("\nContando casos por setor CNEFE...")
cases_per_setor = co_m.groupby("setor_norm").size().rename("n_cases").reset_index()
cases_per_setor.columns = ["CD_SETOR", "n_cases"]

# Merge
sec_gsp = sec_gsp.merge(cases_per_setor, on="CD_SETOR", how="left")
sec_gsp["n_cases"] = sec_gsp["n_cases"].fillna(0)

# Filtra setores residenciais GSP
sec_an = sec_gsp[sec_gsp["CD_TIPO"].astype(str).isin(["0", "1"]) &
                 (sec_gsp["v0001"] >= 100)].copy()

# Compute rate per 100k pa
sec_an["py"] = sec_an["v0001"] * 5
sec_an["rate_per_100k"] = sec_an["n_cases"] / sec_an["py"] * 100_000
sec_an["density_km2"] = sec_an["v0001"] / sec_an["AREA_KM2"]

total_cases = sec_an["n_cases"].sum()
total_pop = sec_an["v0001"].sum()
print(f"\n  Total casos atribuídos a setores (CNEFE): {int(total_cases):,}")
print(f"  Total pop em setores residenciais: {int(total_pop):,}")
print(f"  Taxa média GSP: {total_cases/(total_pop*5)*100_000:.2f}/100k pa")

# ========== 4) HOTSPOTS — top setores por taxa (com pop mínima) ==========
print()
print("=" * 80)
print("HOTSPOTS — top 5% pop GSP por taxa de TB (setores via CNEFE)")
print("=" * 80)

# Ordena por taxa decrescente, acumula pop, corte em 5%
sorted_sec = sec_an[sec_an["n_cases"] > 0].sort_values("rate_per_100k", ascending=False).copy()
sorted_sec["cum_pop"] = sorted_sec["v0001"].cumsum()
target_pop = total_pop * 0.05
top5 = sorted_sec[sorted_sec["cum_pop"] <= target_pop].copy()

top5_cases = int(top5["n_cases"].sum())
top5_pop = top5["v0001"].sum()
print(f"\nTop 5% pop: {len(top5):,} setores")
print(f"  Pop: {int(top5_pop):,} ({top5_pop/total_pop*100:.2f}%)")
print(f"  Casos: {top5_cases:,} ({top5_cases/total_cases*100:.2f}%)")
print(f"  Taxa nesses setores: {top5_cases/(top5_pop*5)*100_000:.1f}/100k pa")
print(f"  Eficiência: capturando {top5_cases/total_cases*100:.0f}% dos casos em "
      f"{top5_pop/total_pop*100:.0f}% da pop")

# Caracterização: comparar hotspots vs resto
print()
print("=" * 80)
print("PERFIL DOS HOTSPOTS vs RESTO DA GSP")
print("=" * 80)

non_hot = sec_an[~sec_an["CD_SETOR"].isin(top5["CD_SETOR"])].copy()


def quantile_summary(s, name):
    vals = s.dropna()
    if len(vals) == 0:
        return f"{name}: sem dados"
    return (f"{name}: mediana={vals.median():.2f}, "
            f"p25={vals.quantile(.25):.2f}, p75={vals.quantile(.75):.2f}")


def weighted_mean(df, col, weight):
    sub = df.dropna(subset=[col])
    if len(sub) == 0:
        return float("nan")
    return (sub[col] * sub[weight]).sum() / sub[weight].sum()


print(f"\nN setores: top5={len(top5):,}, resto={len(non_hot):,}")
print()
print(f"{'Variável':<35} {'Hotspots':>15} {'Resto GSP':>15} {'Razão (Hot/Resto)':>20}")
print("-" * 90)
for var, label in [
    ("v0005", "Densidade habitacional (mor/dom)"),
    ("renda_2022", "Renda média responsável 2022 (R$)"),
    ("density_km2", "Densidade demográfica (hab/km²)"),
    ("v0001", "Pop do setor (média)"),
    ("AREA_KM2", "Área do setor (km²)"),
]:
    h = weighted_mean(top5, var, "v0001")
    r = weighted_mean(non_hot, var, "v0001")
    razao = h / r if r and r != 0 else float("nan")
    print(f"{label:<35} {h:>15.2f} {r:>15.2f} {razao:>20.2f}")

# % FCU nos hotspots vs resto
pct_fcu_hot = top5["is_fcu"].mean() * 100
pct_fcu_rest = non_hot["is_fcu"].mean() * 100
print(f"\n{'% setores classif. FCU':<35} {pct_fcu_hot:>14.1f}% {pct_fcu_rest:>14.1f}%")
print(f"{'% pop em FCU':<35} {top5[top5['is_fcu']]['v0001'].sum()/top5_pop*100:>14.1f}% "
      f"{non_hot[non_hot['is_fcu']]['v0001'].sum()/non_hot['v0001'].sum()*100:>14.1f}%")

# ========== 5) Top 20 setores hotspot — onde estão? ==========
print()
print("=" * 90)
print("TOP 20 SETORES POR TAXA (mais TB por habitante)")
print("=" * 90)
top20 = top5.head(20)
print(f"\n{'#':>2} {'Município':<22} {'Bairro':<25} {'Pop':>6} {'Casos':>5} {'Taxa/100k':>9} {'FCU':>4} {'Renda':>7} {'Dens':>5}")
print("-" * 90)
for i, r in enumerate(top20.itertuples(), 1):
    bairro = str(r.NM_BAIRRO) if pd.notna(r.NM_BAIRRO) else "(sem nome)"
    fcu = "Sim" if r.is_fcu else "-"
    renda = f"{r.renda_2022:.0f}" if pd.notna(r.renda_2022) else "n/a"
    print(f"{i:>2} {str(r.NM_MUN)[:22]:<22} {bairro[:25]:<25} "
          f"{int(r.v0001):>6,} {int(r.n_cases):>5,} {r.rate_per_100k:>9.0f} "
          f"{fcu:>4} {renda:>7} {r.v0005:>5.2f}")

# ========== 6) Agregar por bairro CNEFE ==========
print()
print("=" * 90)
print("TOP 15 BAIRROS por casos absolutos (via bairro_cnefe — IBGE oficial)")
print("=" * 90)
bairros = co_m.dropna(subset=["bairro_cnefe"]).copy()
bairros["bairro_n"] = bairros["bairro_cnefe"].apply(norm)
bairros["mun_n"] = bairros["munResid"].apply(norm)
g = bairros.groupby(["mun_n", "bairro_n"]).size().rename("n_cases").reset_index()
g = g.sort_values("n_cases", ascending=False)
print(f"\n{'#':>2} {'Município':<22} {'Bairro (CNEFE)':<35} {'N casos':>8}")
print("-" * 75)
for i, r in enumerate(g.head(15).itertuples(), 1):
    print(f"{i:>2} {str(r.mun_n)[:22]:<22} {str(r.bairro_n)[:35]:<35} {int(r.n_cases):>8,}")

# Salva resultados
top5.to_csv("/tmp/hotspots_top5pct_setores.csv", index=False)
g.to_csv("/tmp/bairros_cnefe_ranking.csv", index=False)
print(f"\nSalvos: /tmp/hotspots_top5pct_setores.csv (n={len(top5):,})")
print(f"        /tmp/bairros_cnefe_ranking.csv (n={len(g):,})")
