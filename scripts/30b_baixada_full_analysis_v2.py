"""Baixada Santista full analysis using IMPROVED CNEFE matching (v2).

Inputs: /tmp/cohort_baixada_with_cnefe_v2.csv (from script 29b)
Excludes T4 (bairro fallback) from sector-level analysis to avoid
artificial inflation of centroid sectors.
"""
import pandas as pd
import geopandas as gpd
import numpy as np
import zipfile, io, unicodedata, re

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
IBGE_EXT = f"{SPATIAL}/IBGE_2022_extended"

BAIXADA_CD_MUN = {"3506359","3513504","3518701","3522109","3531100",
                  "3537602","3541000","3548500","3551009"}


def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s


print("Loading data (v2 matching)...")
co = pd.read_csv("/tmp/cohort_baixada_with_cnefe_v2.csv", low_memory=False)

# Classify match quality
co["match_tier"] = co["cnefe_match"].str.extract(r"^(T\d)")
print(f"\nMatch tier distribution:")
print(co["match_tier"].value_counts(dropna=False).to_string())

# For SECTOR analysis: only T1+T2+T3 (T4 inflates centroids)
sector_quality = co[co["match_tier"].isin(["T1","T2","T3"])].copy()
sector_quality["CD_SETOR"] = sector_quality["setor_cnefe"].apply(norm_setor)
print(f"\nCases for sector-level analysis (T1+T2+T3): {len(sector_quality):,}")
print(f"Cases with valid sector: {sector_quality['CD_SETOR'].notna().sum():,}")

# IBGE data
agg = pd.read_csv(
    f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
    sep=";", encoding="latin-1", decimal=",",
    usecols=["CD_SETOR","v0001","v0005"],
    dtype={"CD_SETOR": str}, low_memory=False,
)
agg["v0001"] = pd.to_numeric(agg["v0001"], errors="coerce").fillna(0)
agg["v0005"] = pd.to_numeric(agg["v0005"], errors="coerce")

with zipfile.ZipFile(f"{IBGE_EXT}/renda_responsavel.zip") as z:
    fname = [n for n in z.namelist() if n.endswith(".csv")][0]
    with z.open(fname) as f:
        renda = pd.read_csv(io.TextIOWrapper(f, encoding="latin-1"),
                            sep=";", decimal=",",
                            usecols=["CD_SETOR","V06004"],
                            dtype={"CD_SETOR": str}, low_memory=False)
renda["renda_2022"] = pd.to_numeric(renda["V06004"], errors="coerce")
agg = agg.merge(renda[["CD_SETOR","renda_2022"]], on="CD_SETOR", how="left")

sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"] = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)
sec22["AREA_KM2"] = pd.to_numeric(sec22["AREA_KM2"], errors="coerce")
sec_bx = sec22[sec22["CD_MUN"].isin(BAIXADA_CD_MUN)].copy()
sec_bx = sec_bx.merge(agg, on="CD_SETOR", how="left")
sec_bx["is_fcu"] = sec_bx["NM_FCU"].notna().astype(int)
sec_bx["density_km2"] = sec_bx["v0001"] / sec_bx["AREA_KM2"]

cases_per = sector_quality.dropna(subset=["CD_SETOR"]).groupby("CD_SETOR").size().rename("n_cases").reset_index()
sec_bx = sec_bx.merge(cases_per, on="CD_SETOR", how="left")
sec_bx["n_cases"] = sec_bx["n_cases"].fillna(0)
sec_bx["py"] = sec_bx["v0001"] * 5
sec_bx["rate_per_100k"] = np.where(sec_bx["py"]>0,
                                    sec_bx["n_cases"]/sec_bx["py"]*1e5, 0)

sec_an = sec_bx[sec_bx["CD_TIPO"].astype(str).isin(["0","1"]) &
                (sec_bx["v0001"]>=100)].copy()

total_pop = sec_an["v0001"].sum()
total_cases = sec_an["n_cases"].sum()
print(f"\nResidential sectors Baixada: {len(sec_an):,}")
print(f"Total pop residente:           {total_pop:,.0f}")
print(f"Casos atribuídos (T1+T2+T3):   {total_cases:,.0f}")
print(f"Taxa média Baixada:            {total_cases/(total_pop*5)*1e5:.1f} /100k pa")

# ========== Hotspots ==========
print(f"\n{'='*80}\n1) HOTSPOTS — top 5% pop por taxa observada\n{'='*80}")
sec_inc = sec_an[sec_an["n_cases"]>0].sort_values("rate_per_100k", ascending=False).copy()
sec_inc["cum_pop"] = sec_inc["v0001"].cumsum()
hot = sec_inc[sec_inc["cum_pop"] <= total_pop*0.05].copy()
hot_pop, hot_cases = hot["v0001"].sum(), hot["n_cases"].sum()
non = sec_an[~sec_an["CD_SETOR"].isin(hot["CD_SETOR"])]
tx_h = hot_cases/(hot_pop*5)*1e5
tx_n = non["n_cases"].sum()/(non["v0001"].sum()*5)*1e5
print(f"  N hotspot sectors:  {len(hot):,}")
print(f"  Pop hotspots:       {hot_pop:,.0f} ({hot_pop/total_pop*100:.1f}%)")
print(f"  Casos hotspots:     {hot_cases:,.0f} ({hot_cases/total_cases*100:.1f}%)")
print(f"  Taxa hotspots:      {tx_h:.0f} /100k pa")
print(f"  Taxa resto:         {tx_n:.0f} /100k pa")
print(f"  RR:                 {tx_h/tx_n:.2f}×")

# ========== FCU ==========
print(f"\n{'='*80}\n2) FCU — Favelas IBGE\n{'='*80}")
fcu = sec_an[sec_an["is_fcu"]==1]
nfu = sec_an[sec_an["is_fcu"]==0]
print(f"  Pop em FCU:         {fcu['v0001'].sum():,.0f} ({fcu['v0001'].sum()/total_pop*100:.1f}%)")
print(f"  Casos em FCU:       {fcu['n_cases'].sum():,.0f} ({fcu['n_cases'].sum()/total_cases*100:.1f}%)")
tx_fcu = fcu['n_cases'].sum()/(fcu['v0001'].sum()*5)*1e5
tx_n2 = nfu['n_cases'].sum()/(nfu['v0001'].sum()*5)*1e5
print(f"  Taxa FCU:           {tx_fcu:.1f} /100k pa")
print(f"  Taxa não-FCU:       {tx_n2:.1f} /100k pa")
print(f"  RR FCU:             {tx_fcu/tx_n2:.2f}×")

# ========== Composite index ==========
print(f"\n{'='*80}\n3) ÍNDICE COMPOSTO z(-renda)+z(densidade)+z(FCU)\n{'='*80}")
sec_v = sec_an[sec_an["renda_2022"].notna() & sec_an["density_km2"].notna()].copy()
sec_v["log_renda"] = np.log(sec_v["renda_2022"].clip(lower=100))
sec_v["log_dens"] = np.log(sec_v["density_km2"].clip(lower=1))
def z(x): return (x-x.mean())/x.std()
sec_v["z_renda_inv"] = -z(sec_v["log_renda"])
sec_v["z_dens"] = z(sec_v["log_dens"])
sec_v["z_fcu"] = z(sec_v["is_fcu"].astype(float))
sec_v["vuln_score"] = sec_v["z_renda_inv"]+sec_v["z_dens"]+sec_v["z_fcu"]
sec_v = sec_v.sort_values("vuln_score", ascending=False)
sec_v["cum_pop"] = sec_v["v0001"].cumsum()
tcas = sec_v["n_cases"].sum()
print(f"\n{'%pop':>5} {'N sec':>7} {'%casos':>8} {'Taxa':>7} {'RR':>6}")
for pct in [1,5,10,20,30]:
    sub = sec_v[sec_v["cum_pop"] <= total_pop*pct/100]
    rest = sec_v[sec_v["cum_pop"] > total_pop*pct/100]
    if len(sub)==0: continue
    tx_s = sub["n_cases"].sum()/(sub["v0001"].sum()*5)*1e5
    tx_r = rest["n_cases"].sum()/(rest["v0001"].sum()*5)*1e5
    print(f"{pct:>4}% {len(sub):>7,} {sub['n_cases'].sum()/tcas*100:>7.1f}% {tx_s:>7.0f} {tx_s/tx_r:>5.2f}×")

# ========== Hotspot anatomy by bairro ==========
print(f"\n{'='*80}\n4) ANATOMIA — top bairros por hotspots\n{'='*80}")
hot_b = hot.groupby(["NM_MUN","NM_BAIRRO"]).agg(
    n_setores=("CD_SETOR","count"),
    pop=("v0001","sum"),
    casos=("n_cases","sum"),
).reset_index().sort_values("casos", ascending=False)
hot_b["taxa"] = hot_b["casos"]/(hot_b["pop"]*5)*1e5
print(f"{'Município':<14} {'Bairro':<32} {'Set':>4} {'Pop':>6} {'Cas':>4} {'Taxa':>6}")
for r in hot_b.head(25).itertuples():
    b = str(r.NM_BAIRRO) if pd.notna(r.NM_BAIRRO) else "(no name)"
    print(f"{str(r.NM_MUN)[:14]:<14} {b[:32]:<32} {int(r.n_setores):>4} {int(r.pop):>6} {int(r.casos):>4} {r.taxa:>6.0f}")
print(f"\nTotal bairros distintos com setor hotspot: {hot_b['NM_BAIRRO'].nunique():,}")

# ========== FCU anatomy ==========
print(f"\n{'='*80}\n5) ANATOMIA — top FCUs por casos\n{'='*80}")
fcu_d = sec_an[sec_an["is_fcu"]==1].groupby(["NM_MUN","NM_FCU"]).agg(
    n_setores=("CD_SETOR","count"),
    pop=("v0001","sum"),
    casos=("n_cases","sum"),
).reset_index().sort_values("casos", ascending=False)
fcu_d["taxa"] = fcu_d["casos"]/(fcu_d["pop"]*5)*1e5
print(f"\nN distinct FCUs in Baixada: {len(fcu_d):,}")
print(f"\n{'Município':<14} {'FCU':<40} {'Pop':>6} {'Cas':>4} {'Taxa':>6}")
for r in fcu_d.head(15).itertuples():
    f = str(r.NM_FCU) if pd.notna(r.NM_FCU) else "(no name)"
    print(f"{str(r.NM_MUN)[:14]:<14} {f[:40]:<40} {int(r.pop):>6} {int(r.casos):>4} {r.taxa:>6.0f}")

# ========== Hotspot size ==========
print(f"\n{'='*80}\n6) TAMANHO DOS HOTSPOTS\n{'='*80}")
print(f"{'Variável':<28} {'Hotspot':>12} {'Não-hot':>12}")
for col, lbl, fmt in [
    ("v0001","População","{:.0f}"),
    ("AREA_KM2","Área (km²)","{:.4f}"),
    ("density_km2","Densidade (hab/km²)","{:.0f}"),
    ("v0005","Mor/dom","{:.2f}"),
    ("renda_2022","Renda (R$)","{:.0f}"),
    ("n_cases","Casos 5a","{:.0f}"),
    ("rate_per_100k","Taxa /100k","{:.0f}"),
]:
    hm = hot[col].median()
    nm = non[col].median()
    print(f"{lbl:<28} {fmt.format(hm):>12} {fmt.format(nm):>12}")
ma_m2 = hot["AREA_KM2"].median()*1e6
print(f"\nÁrea mediana hotspot: {ma_m2:,.0f} m² ≈ {ma_m2**0.5:.0f}m × {ma_m2**0.5:.0f}m")

# ========== Por município ==========
print(f"\n{'='*80}\n7) TAXAS POR MUNICÍPIO\n{'='*80}")
by_mun = sec_an.groupby(["CD_MUN","NM_MUN"]).agg(
    pop=("v0001","sum"),
    casos=("n_cases","sum"),
    fcu_pop=("v0001", lambda x: x[sec_an.loc[x.index,"is_fcu"]==1].sum()),
).reset_index()
by_mun["taxa"] = by_mun["casos"]/(by_mun["pop"]*5)*1e5
by_mun["pct_fcu"] = by_mun["fcu_pop"]/by_mun["pop"]*100
by_mun = by_mun.sort_values("taxa", ascending=False)
print(f"\n{'Município':<14} {'Pop':>9} {'Casos':>7} {'Taxa':>7} {'%FCU':>6}")
for r in by_mun.itertuples():
    print(f"{str(r.NM_MUN)[:14]:<14} {int(r.pop):>9,} {int(r.casos):>7,} {r.taxa:>7.0f} {r.pct_fcu:>5.1f}%")

# Save
hot.to_csv("/tmp/baixada_hotspots_v2.csv", index=False)
hot_b.to_csv("/tmp/baixada_hotspots_por_bairro_v2.csv", index=False)
fcu_d.to_csv("/tmp/baixada_casos_por_FCU_v2.csv", index=False)
by_mun.to_csv("/tmp/baixada_taxas_por_municipio_v2.csv", index=False)
sec_v.to_csv("/tmp/baixada_setores_priorizados_v2.csv", index=False)
print(f"\nFiles saved to /tmp/baixada_*_v2.csv")
