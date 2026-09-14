"""Full TB vulnerability analysis for Baixada Santista (RMBS).

Mirrors scripts 22-25 (GSP) in a single pass:
  1. Hotspot identification (top 5% pop by observed rate)
  2. Composite vulnerability index (z(-renda) + z(densidade) + z(FCU))
  3. Prevalence and concentration metrics
  4. Anatomy: top neighborhoods, FCUs
  5. Hotspot size statistics

Outputs to /tmp/baixada_* CSVs and console tables.
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import zipfile, io, unicodedata, re

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
IBGE_EXT = f"{SPATIAL}/IBGE_2022_extended"

BAIXADA_CD_MUN = {"3506359", "3513504", "3518701", "3522109", "3531100",
                  "3537602", "3541000", "3548500", "3551009"}


def norm(s):
    if pd.isna(s): return None
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s)


def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s


# ========== Load cohort + IBGE ==========
print("Loading data...")
co = pd.read_csv("/tmp/cohort_baixada_with_cnefe.csv", low_memory=False)
co_m = co[co["setor_cnefe"].notna()].copy()
co_m["CD_SETOR"] = co_m["setor_cnefe"].apply(norm_setor)
print(f"  Cases with CNEFE sector: {len(co_m):,} (of {len(co):,}, {len(co_m)/len(co)*100:.1f}%)")

agg = pd.read_csv(
    f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
    sep=";", encoding="latin-1", decimal=",",
    usecols=["CD_SETOR", "v0001", "v0005"],
    dtype={"CD_SETOR": str}, low_memory=False,
)
agg["v0001"] = pd.to_numeric(agg["v0001"], errors="coerce").fillna(0)
agg["v0005"] = pd.to_numeric(agg["v0005"], errors="coerce")

with zipfile.ZipFile(f"{IBGE_EXT}/renda_responsavel.zip") as z:
    fname = [n for n in z.namelist() if n.endswith(".csv")][0]
    with z.open(fname) as f:
        renda = pd.read_csv(io.TextIOWrapper(f, encoding="latin-1"),
                            sep=";", decimal=",",
                            usecols=["CD_SETOR", "V06004"],
                            dtype={"CD_SETOR": str}, low_memory=False)
renda["renda_2022"] = pd.to_numeric(renda["V06004"], errors="coerce")
agg = agg.merge(renda[["CD_SETOR", "renda_2022"]], on="CD_SETOR", how="left")

sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"] = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)
sec22["AREA_KM2"] = pd.to_numeric(sec22["AREA_KM2"], errors="coerce")
sec_bx = sec22[sec22["CD_MUN"].isin(BAIXADA_CD_MUN)].copy()
sec_bx = sec_bx.merge(agg, on="CD_SETOR", how="left")
sec_bx["is_fcu"] = sec_bx["NM_FCU"].notna().astype(int)
sec_bx["density_km2"] = sec_bx["v0001"] / sec_bx["AREA_KM2"]

cases_per = co_m.groupby("CD_SETOR").size().rename("n_cases").reset_index()
sec_bx = sec_bx.merge(cases_per, on="CD_SETOR", how="left")
sec_bx["n_cases"] = sec_bx["n_cases"].fillna(0)
sec_bx["py"] = sec_bx["v0001"] * 5
sec_bx["rate_per_100k"] = np.where(sec_bx["py"] > 0,
                                    sec_bx["n_cases"] / sec_bx["py"] * 100_000, 0)

# Residential filter
sec_an = sec_bx[sec_bx["CD_TIPO"].astype(str).isin(["0", "1"]) &
                (sec_bx["v0001"] >= 100)].copy()

total_pop = sec_an["v0001"].sum()
total_cases = sec_an["n_cases"].sum()
total_py = total_pop * 5
print(f"\nResidential sectors Baixada: {len(sec_an):,}")
print(f"Total population:             {total_pop:,.0f}")
print(f"Total cases attributed:       {total_cases:,.0f}")
print(f"Average Baixada rate:         {total_cases/total_py*1e5:.1f} /100k py")

# ========== 1) Hotspots (top 5% pop by rate) ==========
print(f"\n{'='*80}")
print("1) HOTSPOTS — top 5% pop by observed TB rate")
print('='*80)
sec_inc = sec_an[sec_an["n_cases"] > 0].sort_values("rate_per_100k", ascending=False).copy()
sec_inc["cum_pop"] = sec_inc["v0001"].cumsum()
hot = sec_inc[sec_inc["cum_pop"] <= total_pop * 0.05].copy()
hot_pop = hot["v0001"].sum()
hot_cases = hot["n_cases"].sum()
non_hot = sec_an[~sec_an["CD_SETOR"].isin(hot["CD_SETOR"])]
tx_hot = hot_cases / (hot_pop * 5) * 1e5
tx_non = non_hot["n_cases"].sum() / (non_hot["v0001"].sum() * 5) * 1e5
print(f"  N hotspot sectors: {len(hot):,}")
print(f"  Pop in hotspots:   {hot_pop:,.0f} ({hot_pop/total_pop*100:.1f}%)")
print(f"  Cases in hotspots: {hot_cases:,.0f} ({hot_cases/total_cases*100:.1f}%)")
print(f"  Rate in hotspots:  {tx_hot:.0f} /100k py")
print(f"  Rate outside:      {tx_non:.0f} /100k py")
print(f"  RR hotspots:       {tx_hot/tx_non:.2f}×")

# ========== 2) FCU ==========
print(f"\n{'='*80}")
print("2) FCU — IBGE-defined favelas and urban communities")
print('='*80)
fcu = sec_an[sec_an["is_fcu"] == 1]
non = sec_an[sec_an["is_fcu"] == 0]
fcu_pop, fcu_cases = fcu["v0001"].sum(), fcu["n_cases"].sum()
non_pop, non_cases = non["v0001"].sum(), non["n_cases"].sum()
tx_fcu = fcu_cases / (fcu_pop * 5) * 1e5
tx_non2 = non_cases / (non_pop * 5) * 1e5
print(f"  Pop in FCU:        {fcu_pop:,.0f} ({fcu_pop/total_pop*100:.1f}%)")
print(f"  Cases in FCU:      {fcu_cases:,.0f} ({fcu_cases/total_cases*100:.1f}%)")
print(f"  Rate in FCU:       {tx_fcu:.1f} /100k py")
print(f"  Rate outside FCU:  {tx_non2:.1f} /100k py")
print(f"  RR FCU:            {tx_fcu/tx_non2:.2f}×")

# ========== 3) Composite vulnerability index ==========
print(f"\n{'='*80}")
print("3) COMPOSITE INDEX — z(-log renda) + z(log densidade) + z(FCU)")
print('='*80)
sec_v = sec_an[sec_an["renda_2022"].notna() & sec_an["density_km2"].notna()].copy()
sec_v["log_renda"] = np.log(sec_v["renda_2022"].clip(lower=100))
sec_v["log_dens"] = np.log(sec_v["density_km2"].clip(lower=1))

def z(x): return (x - x.mean()) / x.std()
sec_v["z_renda_inv"] = -z(sec_v["log_renda"])
sec_v["z_dens"] = z(sec_v["log_dens"])
sec_v["z_fcu"] = z(sec_v["is_fcu"].astype(float))
sec_v["vuln_score"] = sec_v["z_renda_inv"] + sec_v["z_dens"] + sec_v["z_fcu"]

sec_v_sorted = sec_v.sort_values("vuln_score", ascending=False).copy()
sec_v_sorted["cum_pop"] = sec_v_sorted["v0001"].cumsum()
total_v_cases = sec_v["n_cases"].sum()
print(f"  Sectors in index: {len(sec_v):,} (covering {sec_v['v0001'].sum()/total_pop*100:.1f}% pop)")
print(f"\n{'Target %pop':>11} {'N sec':>7} {'%cases':>8} {'Rate':>7} {'RR':>6}")
for pct in [1, 5, 10, 20, 30]:
    target = total_pop * pct / 100
    sub = sec_v_sorted[sec_v_sorted["cum_pop"] <= target]
    rest = sec_v_sorted[sec_v_sorted["cum_pop"] > target]
    if len(sub) == 0: continue
    pop_s, cas_s = sub["v0001"].sum(), sub["n_cases"].sum()
    pop_r, cas_r = rest["v0001"].sum(), rest["n_cases"].sum()
    tx_s = cas_s / (pop_s * 5) * 1e5
    tx_r = cas_r / (pop_r * 5) * 1e5
    print(f"{pct:>10}% {len(sub):>7,} {cas_s/total_v_cases*100:>7.1f}% {tx_s:>7.0f} {tx_s/tx_r:>5.2f}×")

# ========== 4) Top neighborhoods + FCUs ==========
print(f"\n{'='*80}")
print("4) ANATOMY — top neighborhoods by hotspot count")
print('='*80)
hot_b = hot.groupby(["NM_MUN", "NM_BAIRRO"]).agg(
    n_setores=("CD_SETOR", "count"),
    pop=("v0001", "sum"),
    casos=("n_cases", "sum"),
).reset_index().sort_values("casos", ascending=False)
hot_b["taxa"] = hot_b["casos"] / (hot_b["pop"] * 5) * 1e5
print(f"\n{'Município':<15} {'Bairro':<35} {'Set':>4} {'Pop':>6} {'Cas':>4} {'Taxa':>6}")
for r in hot_b.head(20).itertuples():
    b = str(r.NM_BAIRRO) if pd.notna(r.NM_BAIRRO) else "(no name)"
    print(f"{str(r.NM_MUN)[:15]:<15} {b[:35]:<35} {int(r.n_setores):>4} {int(r.pop):>6} "
          f"{int(r.casos):>4} {r.taxa:>6.0f}")
print(f"\nTotal neighborhoods with at least 1 hotspot: {hot_b['NM_BAIRRO'].nunique():,}")

print(f"\n{'='*80}")
print("5) ANATOMY — top FCUs by absolute case count")
print('='*80)
fcu_d = sec_an[sec_an["is_fcu"] == 1].groupby(["NM_MUN", "NM_FCU"]).agg(
    n_setores=("CD_SETOR", "count"),
    pop=("v0001", "sum"),
    casos=("n_cases", "sum"),
).reset_index().sort_values("casos", ascending=False)
fcu_d["taxa"] = fcu_d["casos"] / (fcu_d["pop"] * 5) * 1e5
print(f"\nN distinct FCUs in Baixada: {len(fcu_d):,}")
print(f"\n{'Município':<15} {'FCU':<40} {'Pop':>6} {'Cas':>4} {'Taxa':>6}")
for r in fcu_d.head(15).itertuples():
    f = str(r.NM_FCU) if pd.notna(r.NM_FCU) else "(no name)"
    print(f"{str(r.NM_MUN)[:15]:<15} {f[:40]:<40} {int(r.pop):>6} {int(r.casos):>4} {r.taxa:>6.0f}")

# ========== 6) Hotspot size ==========
print(f"\n{'='*80}")
print("6) HOTSPOT SIZE (median characteristics)")
print('='*80)
print(f"{'Variable':<30} {'Hotspot':>12} {'Non-hot':>12}")
for col, lbl, fmt in [
    ("v0001", "Population", "{:.0f}"),
    ("AREA_KM2", "Area (km²)", "{:.4f}"),
    ("density_km2", "Density (hab/km²)", "{:.0f}"),
    ("v0005", "Persons/household", "{:.2f}"),
    ("renda_2022", "Mean income (R$)", "{:.0f}"),
    ("n_cases", "Cases over 5y", "{:.0f}"),
    ("rate_per_100k", "Rate /100k py", "{:.0f}"),
]:
    h_med = hot[col].median() if col in hot.columns else None
    n_med = non_hot[col].median() if col in non_hot.columns else None
    if h_med is None or pd.isna(h_med):
        print(f"{lbl:<30} {'n/a':>12} {'n/a':>12}")
    else:
        print(f"{lbl:<30} {fmt.format(h_med):>12} {fmt.format(n_med):>12}")

# Median hotspot side length
median_area_m2 = hot["AREA_KM2"].median() * 1e6
print(f"\nMedian hotspot area: {median_area_m2:,.0f} m² ≈ {median_area_m2**0.5:.0f}m × {median_area_m2**0.5:.0f}m square")

# ========== 7) By municipality ==========
print(f"\n{'='*80}")
print("7) RATES BY MUNICIPALITY (Baixada)")
print('='*80)
by_mun = sec_an.groupby(["CD_MUN", "NM_MUN"]).agg(
    pop=("v0001", "sum"),
    casos=("n_cases", "sum"),
    fcu_pop=("v0001", lambda x: x[sec_an.loc[x.index, "is_fcu"] == 1].sum()),
).reset_index()
by_mun["taxa"] = by_mun["casos"] / (by_mun["pop"] * 5) * 1e5
by_mun["pct_fcu"] = by_mun["fcu_pop"] / by_mun["pop"] * 100
by_mun = by_mun.sort_values("taxa", ascending=False)
print(f"\n{'Município':<15} {'Pop':>9} {'Casos':>7} {'Taxa':>7} {'%FCU':>6}")
for r in by_mun.itertuples():
    print(f"{str(r.NM_MUN)[:15]:<15} {int(r.pop):>9,} {int(r.casos):>7,} "
          f"{r.taxa:>7.0f} {r.pct_fcu:>5.1f}%")

# ========== Save outputs ==========
hot.to_csv("/tmp/baixada_hotspots.csv", index=False)
hot_b.to_csv("/tmp/baixada_hotspots_por_bairro.csv", index=False)
fcu_d.to_csv("/tmp/baixada_casos_por_FCU.csv", index=False)
by_mun.to_csv("/tmp/baixada_taxas_por_municipio.csv", index=False)
output_cols = ["CD_SETOR", "NM_MUN", "NM_BAIRRO", "NM_FCU",
               "v0001", "AREA_KM2", "density_km2", "renda_2022",
               "is_fcu", "n_cases", "rate_per_100k", "vuln_score"]
sec_v_sorted[output_cols + ["cum_pop"]].to_csv("/tmp/baixada_setores_priorizados.csv", index=False)
print(f"\nFiles saved to /tmp/baixada_*.csv")
