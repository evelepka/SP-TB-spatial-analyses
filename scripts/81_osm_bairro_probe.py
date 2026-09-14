"""FEASIBILITY PROBE — can OpenStreetMap supply usable neighbourhood (bairro) POLYGONS to
spatially join our geocoded coordinates against? Tests the state capital (the critical case,
where IBGE has no bairro) and a few interior cities. Reports: how many OSM bairro polygons
exist, what % of geocoded cases fall inside one, how many distinct bairros, and their
population scale (via census-sector centroids).
"""
import osmnx as ox, geopandas as gpd, pandas as pd, numpy as np, warnings
warnings.filterwarnings("ignore")
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
TAGS={"place":["suburb","neighbourhood","quarter"]}

def fetch(place):
    try:
        g=ox.features_from_place(place,tags=TAGS)
    except Exception as e:
        print(f"   [fetch falhou: {e}]"); return None
    g=g[g.geometry.geom_type.isin(["Polygon","MultiPolygon"])].copy()
    if "name" not in g.columns: g["name"]=None
    return g.to_crs(4326)[["name","geometry"]].reset_index(drop=True)

print("Loading geocoded cohort coords + sector geometry...")
df=pd.read_csv("/tmp/cohort_with_cnefe.csv",dtype=str,low_memory=False)
df["lat"]=pd.to_numeric(df["lat_cnefe"],errors="coerce"); df["lon"]=pd.to_numeric(df["lon_cnefe"],errors="coerce")
df=df.dropna(subset=["lat","lon"])
sec=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp")[["CD_SETOR","CD_MUN","geometry"]].to_crs(4326)
sec["CD_MUN"]=sec["CD_MUN"].astype(str)
basic=pd.read_csv(f"{SP}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",sep=";",encoding="latin-1",decimal=",",usecols=["CD_SETOR","v0001"],dtype={"CD_SETOR":str},low_memory=False)
basic["pop"]=pd.to_numeric(basic["v0001"],errors="coerce").fillna(0)
sec["CD_SETOR"]=sec["CD_SETOR"].astype(str); sec=sec.merge(basic,on="CD_SETOR",how="left"); sec["pop"]=sec["pop"].fillna(0)
sec["cent"]=sec.geometry.representative_point()

def probe(place,cd_mun,label):
    print(f"\n=== {label} (mun {cd_mun}) ===")
    poly=fetch(place)
    if poly is None or len(poly)==0: print("   nenhum polígono OSM."); return
    print(f"   polígonos de bairro no OSM: {len(poly):,} | com nome: {poly['name'].notna().sum():,}")
    # case coverage
    c=df[df["cd_mun"]==cd_mun]
    if len(c):
        pts=gpd.GeoDataFrame(c,geometry=gpd.points_from_xy(c["lon"],c["lat"]),crs=4326)
        j=gpd.sjoin(pts,poly,predicate="within",how="left")
        j=j[~j.index.duplicated(keep="first")]
        cov=j["name"].notna().mean()*100 if "name" in j else (j["index_right"].notna().mean()*100)
        nb=j["name"].nunique()
        print(f"   casos: {len(c):,} | dentro de um bairro OSM: {cov:.1f}% | bairros distintos atingidos: {nb}")
    # population scale via sector centroids
    sc=sec[sec["CD_MUN"]==cd_mun].copy()
    if len(sc):
        cg=gpd.GeoDataFrame(sc[["CD_SETOR","pop"]],geometry=sc["cent"].values,crs=4326)
        js=gpd.sjoin(cg,poly,predicate="within",how="left")
        js=js[~js.index.duplicated(keep="first")]
        sc_cov=js["name"].notna().mean()*100
        psize=js.dropna(subset=["name"]).groupby("name")["pop"].sum()
        print(f"   setores dentro de bairro OSM: {sc_cov:.1f}% | pop mediana por bairro OSM: {psize.median():,.0f} (n bairros c/ pop: {len(psize)})")

probe("São Paulo, São Paulo, Brazil","3550308","CAPITAL — São Paulo")
probe("Campinas, São Paulo, Brazil","3509502","INTERIOR — Campinas")
probe("Santos, São Paulo, Brazil","3548500","BAIXADA — Santos")
probe("Ribeirão Preto, São Paulo, Brazil","3543402","INTERIOR — Ribeirão Preto")
probe("Presidente Prudente, São Paulo, Brazil","3541406","INTERIOR menor — Pres. Prudente")
print("\nProbe done.")
