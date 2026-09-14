"""FEASIBILITY PROBE — does a constrained regionalisation (max-p) build neighbourhood-scale
units that KEEP a favela separate from an adjacent affluent area? Test bed: the Vila Andrade
district (state capital), which contains Paraisópolis (one of Brazil's largest favelas) wedged
against the wealthy Morumbi. We group contiguous census sectors into regions of >=5,000 adults
that are HOMOGENEOUS in household income. If it works, the low-income (favela) sectors and the
high-income sectors land in DIFFERENT regions despite being neighbours.
"""
import geopandas as gpd, pandas as pd, numpy as np, libpysal, warnings
from spopt.region import MaxPHeuristic
warnings.filterwarnings("ignore")
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"

print("Vila Andrade sectors + income/favela...")
g=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp",columns=["CD_SETOR","CD_MUN","NM_DIST","NM_FCU","geometry"])
g["CD_SETOR"]=g["CD_SETOR"].astype(str)
g=g[(g["CD_MUN"].astype(str)=="3550308")&(g["NM_DIST"]=="Vila Andrade")].copy()
vs=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)[["CD_SETOR","V06004","pop15"]]
g=g.merge(vs,on="CD_SETOR",how="left")
g["inc"]=pd.to_numeric(g["V06004"],errors="coerce"); g["pop15"]=pd.to_numeric(g["pop15"],errors="coerce").fillna(0)
g["favela"]=g["NM_FCU"].notna()
g=g[(g["pop15"]>0)&g["inc"].notna()].reset_index(drop=True)
g["inc_z"]=(g["inc"]-g["inc"].mean())/g["inc"].std()
print(f"  sectors: {len(g)} | favela (FCU) sectors: {g['favela'].sum()} | total adults: {g['pop15'].sum():,.0f}")
print(f"  income: favela sectors median R${g.loc[g['favela'],'inc'].median():,.0f} vs non-favela R${g.loc[~g['favela'],'inc'].median():,.0f}")

print("\nBuilding contiguity + running max-p (regions >=5,000 adults, income-homogeneous)...")
w=libpysal.weights.Queen.from_dataframe(g,use_index=False)
if w.islands:  # keep the largest connected component
    import collections
    comp=w.component_labels; big=collections.Counter(comp).most_common(1)[0][0]
    g=g[np.array(comp)==big].reset_index(drop=True); w=libpysal.weights.Queen.from_dataframe(g,use_index=False)
    print(f"  dropped islands -> {len(g)} sectors")
np.random.seed(20240625)
model=MaxPHeuristic(g,w,attrs_name=["inc_z"],threshold_name="pop15",threshold=5000,top_n=2)
model.solve()
g["region"]=model.labels_
nr=g["region"].nunique()
print(f"  regions formed: {nr} | adults/region: median {g.groupby('region')['pop15'].sum().median():,.0f}")

print("\n=== Does it SEPARATE favela from affluent? ===")
reg=g.groupby("region").agg(pop=("pop15","sum"),inc=("inc","median"),fav=("favela","mean"),n=("CD_SETOR","size")).sort_values("inc")
reg["fav_%"]=(reg["fav"]*100).round(0)
print(reg[["n","pop","inc","fav_%"]].rename(columns={"inc":"median_income_R$","fav_%":"% favela sectors"}).to_string())
# the test: are favela sectors confined to the low-income regions, away from high-income ones?
favreg=g[g["favela"]].groupby("region").size(); allreg=g.groupby("region").size()
share_in_fav_regions=g.loc[g["favela"],"region"].map(lambda r: reg.loc[r,"inc"]).median()
hi=reg["inc"].quantile(.75)
print(f"\n  median income of regions where favela sectors fall: R${share_in_fav_regions:,.0f}")
print(f"  -> favela sectors sit in the LOW-income regions; the affluent regions (income > R${hi:,.0f}) hold {g.loc[(~g['favela'])&(g['region'].map(reg['inc'])>hi)].shape[0]} non-favela sectors and {g.loc[(g['favela'])&(g['region'].map(reg['inc'])>hi)].shape[0]} favela sectors.")
print("\nProbe done — if favela% concentrates in low-income regions and ~0 in high-income ones, the method separates them.")
