"""Metro-focused choropleth maps for the report (advisor: state-wide maps are hard to
read; the metropolitan view is the informative scale). Three hotspot lenses side by
side at the Greater SP + Baixada zoom: incidence, abandonment (LTFU), and TB-death
rate — selected priority units highlighted (coloured by rate), the rest light grey.

Reuses the unit geometry + per-unit metrics built as in script 67.
Output: /tmp/fig_hotspots_3lens_metro.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, re
import matplotlib, matplotlib.pyplot as plt, matplotlib.patches as mpatches
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/Abandonment Outcomes/Abandonment Paper/Banco de dados"
CAPITAL,FCU_MIN,POP_WIN="3550308",5000,0.20
ADULT=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
ZOOM=dict(xlim=(-47.6,-45.8),ylim=(-24.3,-23.2))
def ns(x):
    if pd.isna(x): return None
    x=str(x).strip(); return x[:-1] if x.endswith("P") else x
def nk(x): return x.astype(str).str.strip().str.replace(r'\.0$','',regex=True).str.lstrip("0")

print("Building units + geometry...")
sec22=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]=sec22["CD_MUN"].astype(str); sec22["CD_SETOR"]=sec22["CD_SETOR"].astype(str)
pop=pd.read_csv(f"{SP}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",sep=";",encoding="latin-1",decimal=",",usecols=["CD_SETOR","v0001"],dtype={"CD_SETOR":str},low_memory=False)
pop["v0001"]=pd.to_numeric(pop["v0001"],errors="coerce").fillna(0)
with zipfile.ZipFile(f"{SP}/IBGE_2022_extended/demografia.zip") as z:
    dem=pd.read_csv(z.open("Agregados_por_setores_demografia_BR.csv"),sep=";",encoding="latin-1",decimal=",",usecols=["CD_setor"]+ADULT,dtype={"CD_setor":str},low_memory=False)
dem["pop_adult"]=dem[ADULT].apply(pd.to_numeric,errors="coerce").fillna(0).sum(axis=1)
sec=sec22.merge(pop,on="CD_SETOR",how="left").merge(dem[["CD_setor","pop_adult"]].rename(columns={"CD_setor":"CD_SETOR"}),on="CD_SETOR",how="left")
sec["v0001"]=sec["v0001"].fillna(0); sec["pop_adult"]=sec["pop_adult"].fillna(0)
sec=sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["v0001"]>=100)].copy()
def bkey(r):
    if str(r["CD_MUN"])==CAPITAL: return f"dist_{r['CD_DIST']}"
    if pd.notna(r.get("NM_BAIRRO")): return f"bairro_{r['CD_MUN']}_{r['NM_BAIRRO']}"
    if pd.notna(r.get("NM_DIST")): return f"dist_{r['CD_DIST']}"
    return f"mun_{r['CD_MUN']}"
sec["bairro_id"]=sec.apply(bkey,axis=1)
fp=sec[sec["NM_FCU"].notna()].groupby("NM_FCU")["pop_adult"].sum(); qf=set(fp[fp>=FCU_MIN].index)
sec["unit_id"]=sec.apply(lambda r: f"fcu__{r['NM_FCU']}" if (pd.notna(r['NM_FCU']) and r['NM_FCU'] in qf) else r["bairro_id"],axis=1)

print("Loading cohort + outcomes...")
def lc(p,raw=False):
    d=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    if not raw:
        d["t"]=d["cnefe_match"].astype(str).str.extract(r"^(T\d)"); d=d[d["t"].isin(["T1","T2","T3"])]
    d["CD_SETOR"]=d["setor_cnefe"].apply(ns); return d[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
co=pd.concat([lc("/tmp/cohort_with_cnefe.csv",raw=True),lc("/tmp/cohort_baixada_with_cnefe_v2.csv"),lc("/tmp/cohort_sp_outros_with_cnefe.csv")])
m=pd.read_csv(f"{SP}/cohort_with_spatial.csv",usecols=["sinan_clean","notification_date","age_tb","case_outcome","tx_seq"],low_memory=False,dtype={"sinan_clean":str})
m["year"]=pd.to_datetime(m["notification_date"],errors="coerce").dt.year
m=m.sort_values("tx_seq").drop_duplicates("sinan_clean",keep="last").set_index("sinan_clean")
co["year"]=co["sinan_clean"].map(m["year"]); co["age"]=co["sinan_clean"].map(m["age_tb"]); co["outcome"]=co["sinan_clean"].map(m["case_outcome"])
co=co[(co["age"]>=15)&co["year"].between(2013,2024)]
sim=pd.read_excel(f"{BD}/LINKAGE SIM (1).xlsx",sheet_name="Limpo",usecols=["SINAN","CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"],dtype=str).dropna(subset=["SINAN"])
sim["all"]=[" ".join([str(x) for x in r if x and str(x)!='nan']).upper().replace(".","") for r in sim[["CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"]].values]
stb=set(nk(sim.loc[sim["all"].str.contains(re.compile(r'A1[5-9]')),"SINAN"]))
oc=co["outcome"]
co["death"]=(oc.eq("Obito TB")|nk(co["sinan_clean"]).isin(stb)).astype(int)
co["aband"]=oc.isin(["Abandono","Abandono Primario"]).astype(int)
co["eval"]=(oc.isin(["Cura","Abandono","Abandono Primario","Obito TB","Obito NTB","Falencia/Resistencia"])|(co["death"]==1)).astype(int)
co["unit_id"]=co["CD_SETOR"].map(sec.set_index("CD_SETOR")["unit_id"].to_dict()); co=co.dropna(subset=["unit_id"])
g=co.groupby("unit_id").agg(n=("sinan_clean","size"),ne=("eval","sum"),na=("aband","sum"),nd=("death","sum")).reset_index()
u=sec.groupby("unit_id").agg(pop=("pop_adult","sum")).reset_index().merge(g,on="unit_id",how="left").fillna({"n":0,"ne":0,"na":0,"nd":0})
# age-standardised rates (indirect standardisation, SP internal reference; script 78) for both display and selection
asr=pd.read_csv("/tmp/unit_age_standardised.csv")[["unit_id","inc_adj","ltfu_adj","drate_adj"]]
u=u.merge(asr,on="unit_id",how="left").rename(columns={"inc_adj":"inc","ltfu_adj":"ltfu","drate_adj":"drate"})
assert u["inc"].notna().sum()>=1000, f"age-std merge coverage too low: {u['inc'].notna().sum()}"

TOTAL=sec["pop_adult"].sum()
def select(by):
    d=u.dropna(subset=[by]).sort_values(by,ascending=False).copy(); d["c"]=d["pop"].cumsum(); mm=d["c"]<=TOTAL*POP_WIN
    if mm.sum()<len(d): mm.iloc[mm.sum()]=True
    return set(d[mm]["unit_id"])
HS={"inc":select("inc"),"ltfu":select("ltfu"),"drate":select("drate")}

print("Dissolving geometry...")
gdf=sec[["unit_id","geometry"]].dissolve(by="unit_id").reset_index().merge(u,on="unit_id",how="left")
BASE=gpd.read_file("/tmp/sp_muni_base.gpkg")  # full municipal territory (fills unpopulated Serra do Mar void)
LENS=[("inc","A)  Incidence hotspots (age-standardised)","Blues","cases/100k/yr"),
      ("ltfu","B)  Abandonment (LTFU) hotspots (age-standardised)","OrRd","abandonment %"),
      ("drate","C)  TB mortality hotspots (age-standardised, per 100k)","Reds","TB deaths/100k/yr")]
fig,axes=plt.subplots(1,3,figsize=(19,7))
for ax,(col,title,cmap,lab) in zip(axes,LENS):
    hs=HS[col]; sel=gdf[gdf["unit_id"].isin(hs) & gdf[col].notna()]
    vmin,vmax=np.nanpercentile(sel[col],5),np.nanpercentile(sel[col],95)
    BASE.plot(ax=ax,color="#eeeeee",edgecolor="#dcdcdc",lw=0.2)        # full municipal territory (no void)
    gdf.plot(ax=ax,color="#e6e6e6",edgecolor="white",lw=0.04)          # sub-municipal units (populated)
    BASE.boundary.plot(ax=ax,color="#9a9a9a",lw=0.3)                   # municipal outlines
    sel.plot(column=col,ax=ax,cmap=cmap,vmin=vmin,vmax=vmax,edgecolor="white",lw=0.06,legend=True,legend_kwds={"shrink":0.5,"label":lab})
    ax.set_xlim(*ZOOM["xlim"]); ax.set_ylim(*ZOOM["ylim"])
    ax.set_title(f"{title}  (n={len(hs)})",fontsize=12,fontweight="bold"); ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
fig.suptitle("Priority areas by lens — Greater São Paulo + Baixada Santista (selected hotspots, 20% of population)",fontsize=13.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_hotspots_3lens_metro.png",dpi=145,bbox_inches="tight"); plt.close()
print(f"Saved /tmp/fig_hotspots_3lens_metro.png  | HS: inc {len(HS['inc'])}, ltfu {len(HS['ltfu'])}, drate {len(HS['drate'])}")
