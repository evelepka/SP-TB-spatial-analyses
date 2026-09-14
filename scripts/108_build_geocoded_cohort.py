"""AUTHORITATIVE per-PERSON geocode (Phase 1: spatial overlay).

Geocodes EVERY person (sinan_clean) with a residential address in the CNEFE-matched files to their
2022 census sector, by SPATIAL OVERLAY of the geocoded point on the official sector mesh (not the
CNEFE-reported code, which carries preliminary "P" suffixes for many favela sectors). One row per
person, best geocoding tier. This is only the person -> sector lookup; the EPISODE-level case
selection (each Novo/Recidiva notification = one incident case; adults >=15; 2013-2024; ENDERECO
PADRAO; deaths once per person) happens downstream in script 100. Keeping the geocode unrestricted
here is deliberate: it INCLUDES people the old person-level keep=last pipeline dropped when their
LAST record happened to be a retreatment, even though they had valid new/relapse episodes.
no_match persons (no coordinates) go to the Phase-2 CEP fallback (script 109).
Output: /tmp/geocoded_cohort.csv  (sinan_clean, CD_SETOR, CD_TIPO, tier, favela)
"""
import pandas as pd, geopandas as gpd, numpy as np
from shapely.geometry import Point
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"

# ── GEOCODING ROWS → unified tier, best per person ─────────────────────────────
def tier_of(lbl):
    s=str(lbl)
    if s in ("exact_rua_num","T1_exact"): return "T1"
    if s in ("fallback_rua","T2_rua"):    return "T2"
    if s.startswith("T3_fuzzy"):          return "T3"
    if s=="T4_bairro_fallback":           return "T4"
    return None
def load(p):
    d=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    d["tier"]=d["cnefe_match"].apply(tier_of)
    return d[["sinan_clean","tier","lat_cnefe","lon_cnefe"]]
g=pd.concat([load("/tmp/cohort_with_cnefe.csv"),
             load("/tmp/cohort_baixada_with_cnefe_v2.csv"),
             load("/tmp/cohort_sp_outros_with_cnefe.csv")],ignore_index=True)
g=g[g["tier"].notna()&g["lat_cnefe"].notna()&g["lon_cnefe"].notna()].copy()
g["trk"]=g["tier"].map({"T1":1,"T2":2,"T3":3,"T4":4})
g=g.sort_values("trk").drop_duplicates("sinan_clean",keep="first")   # best tier per person
print(f"Persons with a geocoded point: {len(g):,}")
print("  tier mix:",dict(g["tier"].value_counts()))

# ── SPATIAL OVERLAY on the official 2022 sector mesh ───────────────────────────
sec=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp")[["CD_SETOR","CD_TIPO","geometry"]]
sec["CD_SETOR"]=sec["CD_SETOR"].astype(str); sec["CD_TIPO"]=sec["CD_TIPO"].astype(str)
pts=gpd.GeoDataFrame(g,geometry=[Point(xy) for xy in zip(g["lon_cnefe"],g["lat_cnefe"])],
                     crs="EPSG:4326").to_crs(sec.crs)
j=gpd.sjoin(pts,sec,how="left",predicate="within")
j=j.drop_duplicates("sinan_clean")   # a point on a shared border can hit 2 polys; keep one

# ── keep residential (0=common, 1=favela); drop only institutional sectors ─────
INSTIT={"2","3","5","6","7","8","9"}   # barracks, camp, indigenous, prison, asylum, rural-agglom, other
out=j[j["CD_SETOR"].notna()].copy()
out=out[~out["CD_TIPO"].isin(INSTIT)].copy()
out["favela"]=(out["CD_TIPO"]=="1").astype(int)
res=out[["sinan_clean","CD_SETOR","CD_TIPO","tier","favela"]].reset_index(drop=True)
res.to_csv("/tmp/geocoded_cohort.csv",index=False)
print(f"\nPersons geocoded to a residential 2022 sector (overlay): {len(res):,}")
print(f"  of which favela (aglomerado subnormal): {int(res['favela'].sum()):,}  ({res['favela'].mean()*100:.1f}%)")
print("  tier mix of final:",dict(res["tier"].value_counts()))
print("Saved /tmp/geocoded_cohort.csv (person -> sector; episode selection is in script 100)")
