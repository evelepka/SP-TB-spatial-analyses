"""Classify GSP+Baixada hotspots into 4 structural archetypes (A-D).

Tipologia final:
  A  Aglomerado subnormal de grande porte  FCU + pop ≥ 30.000
  B  Aglomerado subnormal disperso         FCU + pop < 30.000
  C  Periferia consolidada não-FCU         não-FCU + renda ≤ p25 + dens ≥ p50
  D  Centro urbano degradado / cortiço     não-FCU + dens ≥ p75 + p25 ≤ renda ≤ p75

Cascade order: A → B → D → C → outros.
Percentis calculados separadamente por região (GSP / Baixada).

Reads directly from shapefile + IBGE aggregates + cohort CNEFE files,
to ensure CD_TIPO, CD_MUN etc. are all available.
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import zipfile, io, unicodedata, re

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
IBGE_EXT = f"{SPATIAL}/IBGE_2022_extended"

CAPITAL_CD_MUN = {"3550308"}  # SP only state capital in our scope


def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s


# ---- 1) Shapefile + Census aggregates ----
print("Loading shapefile + aggregates...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"] = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)
sec22["AREA_KM2"] = pd.to_numeric(sec22["AREA_KM2"], errors="coerce")

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

# Identify regions
GSP_MUNIS = set(sec22[sec22["NM_CONCURB"]=="São Paulo/SP"]["CD_MUN"].unique())
BX_MUNIS = {"3506359","3513504","3518701","3522109","3531100","3537602","3541000","3548500","3551009"}
print(f"  GSP municipalities: {len(GSP_MUNIS)}; Baixada: {len(BX_MUNIS)}")

# ---- 2) Cases per sector from cohort CNEFE files ----
print("\nLoading case counts...")
gsp_co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False)
gsp_co["CD_SETOR"] = gsp_co["setor_cnefe"].apply(norm_setor)
gsp_cases = gsp_co.dropna(subset=["CD_SETOR"]).groupby("CD_SETOR").size().rename("n_cases").reset_index()

bx_co = pd.read_csv("/tmp/cohort_baixada_with_cnefe_v2.csv", low_memory=False)
# Use only T1+T2+T3 (avoid T4 centroid inflation)
bx_co["match_tier"] = bx_co["cnefe_match"].astype(str).str.extract(r"^(T\d)")
bx_quality = bx_co[bx_co["match_tier"].isin(["T1","T2","T3"])]
bx_quality["CD_SETOR"] = bx_quality["setor_cnefe"].apply(norm_setor)
bx_cases = bx_quality.dropna(subset=["CD_SETOR"]).groupby("CD_SETOR").size().rename("n_cases").reset_index()

# Concat
all_cases = pd.concat([gsp_cases, bx_cases], ignore_index=True)
print(f"  Sectors with cases: GSP {len(gsp_cases):,}, Baixada {len(bx_cases):,}")

# ---- 3) Build full sector dataset ----
sec_all = sec22[sec22["CD_MUN"].isin(GSP_MUNIS | BX_MUNIS)].copy()
sec_all = sec_all.merge(agg, on="CD_SETOR", how="left")
sec_all = sec_all.merge(all_cases, on="CD_SETOR", how="left")
sec_all["n_cases"] = sec_all["n_cases"].fillna(0)
sec_all["is_fcu"] = sec_all["NM_FCU"].notna().astype(int)
sec_all["density_km2"] = sec_all["v0001"] / sec_all["AREA_KM2"]
sec_all["region"] = sec_all["CD_MUN"].map(lambda x: "Baixada" if x in BX_MUNIS else "GSP")
sec_all["py"] = sec_all["v0001"] * 5
sec_all["rate_per_100k"] = np.where(sec_all["py"]>0, sec_all["n_cases"]/sec_all["py"]*1e5, 0)

# Residential filter
sec_an = sec_all[
    sec_all["CD_TIPO"].astype(str).isin(["0","1"]) &
    (sec_all["v0001"] >= 100)
].copy()
print(f"  Residential sectors: {len(sec_an):,}")

# ---- 4) Regional percentiles ----
print("\nRegional percentiles:")
percentiles = {}
for region in ["GSP","Baixada"]:
    sub = sec_an[(sec_an["region"]==region) & sec_an["renda_2022"].notna() & sec_an["density_km2"].notna()]
    percentiles[region] = {
        "p25_renda": sub["renda_2022"].quantile(0.25),
        "p50_renda": sub["renda_2022"].quantile(0.50),
        "p75_renda": sub["renda_2022"].quantile(0.75),
        "p50_dens": sub["density_km2"].quantile(0.50),
        "p75_dens": sub["density_km2"].quantile(0.75),
    }
    print(f"  {region}: renda_p25={percentiles[region]['p25_renda']:.0f} "
          f"p50={percentiles[region]['p50_renda']:.0f} "
          f"p75={percentiles[region]['p75_renda']:.0f} | "
          f"dens_p50={percentiles[region]['p50_dens']:.0f} "
          f"p75={percentiles[region]['p75_dens']:.0f}")

# ---- 5) FCU pop totals ----
fcu_pop = (sec_an[sec_an["is_fcu"]==1]
           .groupby(["region","NM_MUN","NM_FCU"])["v0001"].sum()
           .rename("pop_FCU").reset_index())
print(f"\nDistinct FCUs: {len(fcu_pop):,}; megafavelas (pop≥30k): {(fcu_pop['pop_FCU']>=30000).sum()}")

# ---- 6) Identify hotspots per region ----
print("\nIdentifying hotspots (top 5% pop by rate)...")
hotspots = []
for region in ["GSP","Baixada"]:
    sub = sec_an[sec_an["region"]==region].copy()
    total_pop = sub["v0001"].sum()
    inc = sub[sub["n_cases"]>0].sort_values("rate_per_100k", ascending=False).copy()
    inc["cum_pop"] = inc["v0001"].cumsum()
    hot_r = inc[inc["cum_pop"] <= total_pop*0.05].copy()
    print(f"  {region}: {len(hot_r):,} hotspot sectors")
    hotspots.append(hot_r)
hot = pd.concat(hotspots, ignore_index=True)
print(f"  TOTAL: {len(hot):,}")

# ---- 7) Distance to municipal centroid ----
print("\nDistance to municipal centroid (only hotspots)...")
shp_proj = sec22[sec22["CD_MUN"].isin(GSP_MUNIS | BX_MUNIS)].to_crs("EPSG:31983")
# Mun centroid: dissolve and compute centroid
mun_diss = shp_proj.dissolve(by="CD_MUN", as_index=False)[["CD_MUN","geometry"]]
mun_diss["mun_centroid"] = mun_diss.geometry.centroid

# Hotspot centroids
hot_geom = shp_proj[shp_proj["CD_SETOR"].isin(hot["CD_SETOR"])][["CD_SETOR","CD_MUN","geometry"]].copy()
hot_geom["sec_centroid"] = hot_geom.geometry.centroid
hot_geom = hot_geom.drop(columns="geometry")  # drop original to avoid Geometry/series conflict
hot_geom = hot_geom.merge(mun_diss[["CD_MUN","mun_centroid"]], on="CD_MUN")
hot_geom["dist_to_mun_centroid_km"] = hot_geom.apply(
    lambda r: r["sec_centroid"].distance(r["mun_centroid"])/1000.0, axis=1
)
print(f"  Distance computed: {len(hot_geom):,} hotspots; median {hot_geom['dist_to_mun_centroid_km'].median():.1f} km")

hot = hot.merge(hot_geom[["CD_SETOR","dist_to_mun_centroid_km"]], on="CD_SETOR", how="left")
hot = hot.merge(fcu_pop, on=["region","NM_MUN","NM_FCU"], how="left")
hot["pop_FCU"] = hot["pop_FCU"].fillna(0)

# ---- 8) Classify ----
print("\nClassifying (cascade A→B→D→C→outros)...")
def classify(row):
    """4-archetype cascade (tipologia final).

    A  Megafavela             FCU + pop ≥ 30k
    B  FCU dispersa           FCU + pop < 30k
    D  Centro degradado       não-FCU + dens ≥ p75 + p25 ≤ renda ≤ p75
    C  Periferia consolidada  não-FCU + renda ≤ p25 + dens ≥ p50
    """
    region = row["region"]
    p = percentiles[region]
    is_fcu = int(row["is_fcu"]) == 1
    renda = row.get("renda_2022")
    dens = row.get("density_km2")

    # A: Megafavela
    if is_fcu and row["pop_FCU"] >= 30000:
        return "A_megafavela"
    # B: FCU dispersa
    if is_fcu:
        return "B_FCU_dispersa"
    if pd.isna(renda) or pd.isna(dens):
        return "outros_sem_dados"
    # D: Centro urbano degradado / cortiço histórico
    # Alta densidade + renda mediana (exclui FCU, exclui rico, exclui pobre extremo)
    if dens >= p["p75_dens"] and p["p25_renda"] <= renda <= p["p75_renda"]:
        return "D_centro_degradado"
    # C: Periferia consolidada não-FCU
    # Renda muito baixa + densidade acima da mediana
    if renda <= p["p25_renda"] and dens >= p["p50_dens"]:
        return "C_periferia_consolidada"
    return "outros"

hot["archetype"] = hot.apply(classify, axis=1)

# ---- 9) Report ----
print("\n"+"="*80)
print("CLASSIFICATION RESULTS")
print("="*80)
total_hot = len(hot)
total_cases = hot["n_cases"].sum()
counts = hot["archetype"].value_counts()
print(f"\n{'Archetype':<30} {'N':>6} {'%':>6} {'Cases':>7} {'%Cas':>6}")
for arch, n in counts.items():
    sub = hot[hot["archetype"]==arch]
    print(f"{arch:<30} {n:>6,} {n/total_hot*100:>5.1f}% {int(sub['n_cases'].sum()):>7,} {sub['n_cases'].sum()/total_cases*100:>5.1f}%")

print("\n"+"="*80)
print("PROFILE per archetype (medians)")
print("="*80)
print(f"\n{'Archetype':<30} {'Renda':>7} {'Dens':>7} {'Mor/d':>6} {'Taxa':>7} {'Dist_km':>9}")
profile_rows = []
for arch in counts.index:
    sub = hot[hot["archetype"]==arch]
    r = {"archetype":arch, "n":len(sub), "casos":int(sub["n_cases"].sum()), "pop":int(sub["v0001"].sum()),
         "renda_median":sub["renda_2022"].median(), "dens_median":sub["density_km2"].median(),
         "mor_dom_median":sub["v0005"].median(), "rate_median":sub["rate_per_100k"].median(),
         "dist_km_median":sub["dist_to_mun_centroid_km"].median(), "fcu_rate":sub["is_fcu"].mean()}
    profile_rows.append(r)
    print(f"{arch:<30} {(r['renda_median'] or 0):>7.0f} {(r['dens_median'] or 0):>7.0f} {(r['mor_dom_median'] or 0):>6.2f} {(r['rate_median'] or 0):>7.0f} {(r['dist_km_median'] or 0):>9.2f}")

print("\n"+"="*80)
print("TOP EXAMPLES per archetype")
print("="*80)
for arch in counts.index:
    sub = hot[hot["archetype"]==arch].copy()
    print(f"\n--- {arch} (n={len(sub):,}) ---")
    if arch in ("A_megafavela","B_FCU_dispersa"):
        grp = sub.groupby(["region","NM_MUN","NM_FCU"]).agg(
            n_setores=("CD_SETOR","count"),
            casos=("n_cases","sum"),
            pop=("v0001","sum"),
        ).reset_index().sort_values("casos",ascending=False)
        print(f"{'Reg':<8} {'Município':<18} {'FCU':<32} {'Set':>4} {'Cas':>5}")
        for r in grp.head(8).itertuples():
            print(f"{str(r.region)[:8]:<8} {str(r.NM_MUN)[:18]:<18} {str(r.NM_FCU)[:32]:<32} {int(r.n_setores):>4} {int(r.casos):>5}")
    else:
        grp = sub.groupby(["region","NM_MUN","NM_BAIRRO"]).agg(
            n_setores=("CD_SETOR","count"),
            casos=("n_cases","sum"),
            pop=("v0001","sum"),
        ).reset_index().sort_values("casos",ascending=False)
        print(f"{'Reg':<8} {'Município':<18} {'Bairro':<32} {'Set':>4} {'Cas':>5}")
        for r in grp.head(8).itertuples():
            b = str(r.NM_BAIRRO) if pd.notna(r.NM_BAIRRO) else "(sem nome)"
            print(f"{str(r.region)[:8]:<8} {str(r.NM_MUN)[:18]:<18} {b[:32]:<32} {int(r.n_setores):>4} {int(r.casos):>5}")

hot.to_csv("/tmp/hotspots_archetypes.csv", index=False)
pd.DataFrame(profile_rows).to_csv("/tmp/archetypes_profile.csv", index=False)
print(f"\nSaved /tmp/hotspots_archetypes.csv ({len(hot):,} rows)")
