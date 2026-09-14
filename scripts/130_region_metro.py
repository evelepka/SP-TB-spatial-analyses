"""Metropolitan flag per region (Greater São Paulo concurb + Baixada Santista), population-weighted
majority of its census sectors — the same rule as Table 1 (script 112). Output: /tmp/region_metro.csv
(region_id, metro). Used by 129 (Supplementary Figure S7) and ad-hoc metro-restricted analyses."""
import pandas as pd, geopandas as gpd, numpy as np, zipfile
SP="/DATA_ROOT/WHO modelling Project/SP-TB-spatial-analyses/Data"
BAIXADA={"3506359","3513504","3518701","3522109","3531100","3537602","3541000","3548500","3551009"}
BANDS=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
sec=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp")[["CD_SETOR","CD_MUN","CD_DIST","CD_TIPO","NM_CONCURB"]]
sec["CD_SETOR"]=sec["CD_SETOR"].astype(str); sec["CD_MUN"]=sec["CD_MUN"].astype(str)
with zipfile.ZipFile(f"{SP}/IBGE_2022_extended/demografia.zip") as z:
    dem=pd.read_csv(z.open("Agregados_por_setores_demografia_BR.csv"),sep=";",encoding="latin-1",decimal=",",usecols=["CD_setor"]+BANDS,dtype={"CD_setor":str},low_memory=False)
dem["pop_adult"]=dem[BANDS].apply(pd.to_numeric,errors="coerce").fillna(0).sum(axis=1)
sec=sec.merge(dem.rename(columns={"CD_setor":"CD_SETOR"})[["CD_SETOR","pop_adult"]],on="CD_SETOR",how="left"); sec["pop_adult"]=sec["pop_adult"].fillna(0)
sec=sec[sec["CD_TIPO"].astype(str).isin(["0","1"])&(sec["pop_adult"]>0)].copy()
GSP=set(sec.loc[sec["NM_CONCURB"]=="São Paulo/SP","CD_MUN"].unique()); METRO=GSP|BAIXADA
sec["metro"]=sec["CD_MUN"].isin(METRO)
rg=pd.read_csv("/tmp/regions_sectors.csv",dtype={"CD_SETOR":str})[["CD_SETOR","region_id"]]
sec=sec.merge(rg,on="CD_SETOR",how="left"); sec["region_id"]=sec["region_id"].fillna("DIST_"+sec["CD_DIST"].astype(str))
rm=sec.groupby("region_id").apply(lambda x:np.average(x["metro"],weights=x["pop_adult"])>0.5).rename("metro").reset_index()
rm.to_csv("/tmp/region_metro.csv",index=False); print("metro regions:",int(rm["metro"].sum()),"| Saved /tmp/region_metro.csv")
