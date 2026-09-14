"""Why our favela TB incidence is lower than the MS (ArcGIS polygon + 200 m buffer) figure.

Run after scripts/00_restore_tmp.py. Results of 2026-08-10 (episode-level analytic set):

1. GEOCODING IS NOT THE CAUSE. Street-level-or-better match (T1+T2) is HIGHER inside favela
   sectors (86.3%) than outside (79.0%) — CNEFE enumerates favelas exhaustively. Fallback
   tiers T3-T5, which can displace a case out of its favela sector, are LESS frequent in
   favelas; a generous upper bound on displaced favela cases is ~1,500 episodes (~6%).

2. THE BUFFER IS THE CAUSE. Favela sectors + a 200 m ring in urban SP capture:
      sectors:      7,995  ->  29,386   (3.7x)
      episodes:    24,034  ->  93,598   (3.89x)
      adult pop: 2.75 M    ->  10.92 M  (3.97x)
   MS-style rate (ring cases / favela-only pop)  = 283.9 /100k/yr
   Our rate      (favela cases / favela pop)     =  72.9 /100k/yr   -> 3.9x inflation
   Honest ring   (ring cases / ring pop)         =  71.4 /100k/yr   (= ours; the ring adds
   people at city-average rates — the inflation is purely numerator/denominator mismatch)

3. Window matters when comparing to a number quoted in a meeting:
   2013-24: 72.9   2020-24: 82.2   2023-24: 91.6 /100k/yr (favela, adult episodes)

Definitional gaps vs MS (per Evelyn 2026-08-10: MS EXCLUDES prisoners — no prisons inside
favelas — and INCLUDES children):
 - Children RAISE nothing: they are ~2.6% of notifications but 23.8% of favela population
   (vs 17.5% outside — favelas are younger), so an all-ages favela rate is LOWER than the
   adult rate: ~57.2 vs 72.9 /100k/yr. MS including children makes their high figure MORE
   attributable to the buffer mismatch, not less.
 - all notifications vs incident new+relapse; possibly 2010 AGSN polygons vs IBGE 2022
   favela sectors — both push MS upward, but are second-order next to the 3.9x buffer effect.
"""
import pandas as pd, geopandas as gpd

T = 12
SP = ("/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com"
      "/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data")

rc = pd.read_csv("/tmp/region_cases.csv", dtype={"sinan_clean": str}, low_memory=False)
g = pd.read_csv("/tmp/geocoded_cohort.csv", dtype={"CD_SETOR": str}, low_memory=False)
g["sinan_clean"] = g["sinan_clean"].astype(str)
m = rc.merge(g[["sinan_clean", "CD_SETOR", "favela"]], on="sinan_clean", how="left")
vs = pd.read_csv("/tmp/vuln_sectors.csv", dtype={"CD_SETOR": str}, low_memory=False)[["CD_SETOR", "CD_TIPO", "pop15"]]

# 1. tier profile by favela status
ct = pd.crosstab(m.merge(g[["sinan_clean"]], on="sinan_clean")["tier"] if "tier" in m else m["tier"],
                 m["favela"], normalize="columns") * 100
print("tier % (col 0 = fora, 1 = favela):\n", ct.round(1), "\n")

# 2. our rate vs the MS-style buffered rate
sec = gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp")[["CD_SETOR", "CD_TIPO", "geometry"]]
sec["CD_SETOR"] = sec["CD_SETOR"].astype(str)
sec = sec.to_crs(31983)
fav = sec[sec["CD_TIPO"].astype(str) == "1"]
buf = gpd.GeoDataFrame(geometry=[fav.buffer(200).union_all()], crs=31983)
hit = set(gpd.sjoin(sec, buf, predicate="intersects")["CD_SETOR"].unique())

pop_fav = vs.loc[vs["CD_TIPO"].astype(str) == "1", "pop15"].sum()
pop_buf = vs.loc[vs["CD_SETOR"].isin(hit), "pop15"].sum()
n_fav = int(m["favela"].sum())
n_buf = int(m["CD_SETOR"].isin(hit).sum())

ours = n_fav / (pop_fav * T) * 1e5
ms_style = n_buf / (pop_fav * T) * 1e5
honest = n_buf / (pop_buf * T) * 1e5
print(f"ours {ours:.1f}  ms-style {ms_style:.1f} ({ms_style/ours:.2f}x)  honest-ring {honest:.1f}")
