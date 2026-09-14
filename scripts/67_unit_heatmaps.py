"""Intensity heat-maps by geographic unit (advisor request): choropleths of
vulnerability, TB incidence, LTFU (abandonment), and TB-death rate, each coloured
by intensity, at the hotspot-unit level (FCU / bairro / capital district).

Vulnerability = population-weighted sector composite (script 64, /tmp/vuln_sectors.csv).
Rates restricted to units with >=10 cases (>=10 evaluated for LTFU) to avoid noise.

Output: /tmp/fig_unit_heatmaps_state.png, /tmp/fig_unit_heatmaps_metro.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, re
import matplotlib, matplotlib.pyplot as plt
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/Abandonment Outcomes/Abandonment Paper/Banco de dados"
CAPITAL,FCU_MIN="3550308",5000
ADULT=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
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

# vulnerability per sector (4-domain vuln_final, script 89) -> population-weighted to unit
vs=pd.read_csv("/tmp/vuln_final.csv",dtype={"CD_SETOR":str},low_memory=False)[["CD_SETOR","vuln_final"]].rename(columns={"vuln_final":"vuln"})
sec=sec.merge(vs,on="CD_SETOR",how="left")
sec["vw"]=sec["vuln"]*sec["pop_adult"]

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
co["unit_id"]=co["CD_SETOR"].map(sec.set_index("CD_SETOR")["unit_id"].to_dict())
co=co.dropna(subset=["unit_id"])
g=co.groupby("unit_id").agg(n=("sinan_clean","size"),ne=("eval","sum"),na=("aband","sum"),nd=("death","sum")).reset_index()

# unit aggregation + metrics
u=sec.groupby("unit_id").agg(pop=("pop_adult","sum"),vw=("vw","sum")).reset_index()
u["vuln"]=u["vw"]/u["pop"]
u=u.merge(g,on="unit_id",how="left").fillna({"n":0,"ne":0,"na":0,"nd":0})
# age-standardised rates (indirect standardisation, SP internal reference; script 78) replace crude
asr=pd.read_csv("/tmp/unit_age_standardised.csv")[["unit_id","inc_adj","ltfu_adj","drate_adj"]]
u=u.merge(asr,on="unit_id",how="left").rename(columns={"inc_adj":"inc","ltfu_adj":"ltfu","drate_adj":"drate"})
assert u["inc"].notna().sum()>=1000, f"age-std merge coverage too low: {u['inc'].notna().sum()}"

print("Dissolving geometry...")
gdf=sec[["unit_id","geometry"]].dissolve(by="unit_id").reset_index().merge(u,on="unit_id",how="left")
BASE=gpd.read_file("/tmp/sp_muni_base.gpkg")  # full municipal territory (fills unpopulated Serra do Mar void)
# incidence kept cool/neutral; the ADVERSE outcomes (LTFU, TB death) get hot, high-contrast
# ramps so their peripheral concentration stands out.
PANELS=[("vuln","Social vulnerability (composite)","Greens",(2,98)),
        ("inc","TB incidence — age-standardised (per 100k/yr)","Blues",(5,95)),
        ("ltfu","Treatment abandonment / LTFU — age-standardised (%)","OrRd",(5,93)),
        ("drate","TB mortality — age-standardised (per 100k/yr)","Reds",(5,93))]
def draw(ax,col,title,cmap,clip):
    d=gdf[gdf[col].notna()]
    vmin,vmax=(np.nanpercentile(d[col],clip[0]),np.nanpercentile(d[col],clip[1])) if clip else (np.nanpercentile(gdf[col].dropna(),2),np.nanpercentile(gdf[col].dropna(),98))
    BASE.plot(ax=ax,color="#eeeeee",edgecolor="#dcdcdc",lw=0.15)  # full municipal territory (no void)
    gdf.plot(ax=ax,color="#e6e6e6",edgecolor="none")  # sub-municipal units (units w/o metric = grey)
    BASE.boundary.plot(ax=ax,color="#9a9a9a",lw=0.25)            # municipal outlines
    d.plot(column=col,ax=ax,cmap=cmap,vmin=vmin,vmax=vmax,edgecolor="white",lw=0.04,
           legend=True,legend_kwds={"shrink":0.55,"label":""})
    ax.set_title(title,fontsize=12,fontweight="bold"); ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")

def make(fig_name,xlim=None,ylim=None,supt=""):
    fig,axes=plt.subplots(2,2,figsize=(16,13))
    for ax,(col,title,cmap,clip) in zip(axes.ravel(),PANELS):
        draw(ax,col,title,cmap,clip)
        if xlim: ax.set_xlim(*xlim)
        if ylim: ax.set_ylim(*ylim)
    fig.suptitle(supt,fontsize=14,fontweight="bold")
    plt.tight_layout(); plt.savefig(fig_name,dpi=140,bbox_inches="tight"); plt.close()
    print("Saved",fig_name)

make("/tmp/fig_unit_heatmaps_state.png",supt="TB and social vulnerability by geographic unit — São Paulo State, 2013–2024 (adults)")
make("/tmp/fig_unit_heatmaps_metro.png",xlim=(-47.6,-45.8),ylim=(-24.3,-23.2),
     supt="TB and social vulnerability by geographic unit — Greater SP + Baixada Santista (zoom)")
print("Done.")
