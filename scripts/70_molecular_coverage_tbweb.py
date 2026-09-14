"""Molecular (TRM-TB / GeneXpert) test COVERAGE as a TB-programme fragility indicator,
sub-municipal, from TBweb (`tmr_tb`). Equity question: are the most vulnerable / highest-
burden areas the LEAST tested? Coverage = molecular test done / (done + not-done), among
cases with a known status. Primary window 2020-2024 (Xpert is standard by then; earlier
years reflect roll-out, shown as a trend). To be paired later with SIA-SUS (independent
municipal testing volume).

Output: /tmp/fig_molecular_coverage.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, re
import matplotlib, matplotlib.pyplot as plt
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL,FCU_MIN,POP_WIN="3550308",5000,0.20
ADULT=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
ZOOM=dict(xlim=(-47.6,-45.8),ylim=(-24.3,-23.2))
DONE={"Mtb detectado - Rifamp sensivel","Mtb nao detectado","Mtb detectado - Rifamp indeterm","Mtb detectado - Rifamp resistente"}
def ns(x):
    if pd.isna(x): return None
    x=str(x).strip(); return x[:-1] if x.endswith("P") else x

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
# sector vulnerability (script 64) + population-weighted percentile
vs=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)[["CD_SETOR","vuln"]]
sec=sec.merge(vs,on="CD_SETOR",how="left")
d=sec.dropna(subset=["vuln"]).sort_values("vuln")
sec["vpct"]=sec["CD_SETOR"].map(dict(zip(d["CD_SETOR"],(d["pop_adult"].cumsum()-0.5*d["pop_adult"])/d["pop_adult"].sum()*100)))

print("Loading cohort + tmr_tb...")
def lc(p,raw=False):
    x=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    if not raw:
        x["t"]=x["cnefe_match"].astype(str).str.extract(r"^(T\d)"); x=x[x["t"].isin(["T1","T2","T3"])]
    x["CD_SETOR"]=x["setor_cnefe"].apply(ns); return x[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
co=pd.concat([lc("/tmp/cohort_with_cnefe.csv",raw=True),lc("/tmp/cohort_baixada_with_cnefe_v2.csv"),lc("/tmp/cohort_sp_outros_with_cnefe.csv")])
m=pd.read_csv(f"{SP}/cohort_with_spatial.csv",usecols=["sinan_clean","notification_date","age_tb","tmr_tb","case_outcome","tx_seq"],low_memory=False,dtype={"sinan_clean":str})
m["year"]=pd.to_datetime(m["notification_date"],errors="coerce").dt.year
m=m.sort_values("tx_seq").drop_duplicates("sinan_clean",keep="last").set_index("sinan_clean")
for c in ["year","age_tb","tmr_tb","case_outcome"]: co[c]=co["sinan_clean"].map(m[c])
co=co[(co["age_tb"]>=15)&co["year"].between(2013,2024)]
smap=sec.set_index("CD_SETOR")
co["unit_id"]=co["CD_SETOR"].map(smap["unit_id"]); co["vpct"]=co["CD_SETOR"].map(smap["vpct"])
co=co.dropna(subset=["unit_id","vpct"])
co["done"]=co["tmr_tb"].isin(DONE)
co["known"]=co["done"]|co["tmr_tb"].eq("N/realiz")

# statewide + trend
def cov(df): return df["done"].sum()/df["known"].sum()*100 if df["known"].sum() else np.nan
print(f"\nStatewide molecular coverage (known status): all 2013-24 = {cov(co[co['known']]):.1f}%")
print("Coverage by year (TRM-TB roll-out):")
for y in range(2013,2025):
    s=co[(co['year']==y)&co['known']]; print(f"  {y}: {cov(s):4.1f}%  (n_known={s['known'].sum():,})")
REC=co[co["year"].between(2020,2024)&co["known"]].copy()
print(f"\nRecent window 2020-2024 coverage = {cov(REC):.1f}%  (n_known={len(REC):,})")

# ── equity dose-response: coverage by vulnerability decile (recent) ───────────
REC["vdec"]=pd.cut(REC["vpct"],bins=range(0,101,10),labels=range(1,11)).astype(float)
dr=REC.groupby("vdec").apply(lambda x: pd.Series({"cov":cov(x),"n":x["known"].sum()}))
print("\nMolecular coverage by vulnerability decile (1=least,10=most vulnerable):")
print(dr.round(1).to_string())

# per-unit coverage (recent, >=10 known) for the map; + hotspot comparison
uagg=REC.groupby("unit_id").agg(done=("done","sum"),known=("known","sum")).reset_index()
uagg["cov"]=np.where(uagg["known"]>=10,uagg["done"]/uagg["known"]*100,np.nan)
# incidence hotspots (12-yr, like the rest of the paper)
allco=co.copy()
ginc=allco.groupby("unit_id").size()
upop=sec.groupby("unit_id")["pop_adult"].sum()
ud=pd.DataFrame({"pop":upop}).reset_index().merge(ginc.rename("n").reset_index(),on="unit_id",how="left").fillna({"n":0})
ud["inc"]=np.where(ud["n"]>=10,ud["n"]/(ud["pop"]*12)*1e5,np.nan)
TOTAL=sec["pop_adult"].sum()
dd=ud.dropna(subset=["inc"]).sort_values("inc",ascending=False); dd["c"]=dd["pop"].cumsum()
HS_inc=set(dd[dd["c"]<=TOTAL*POP_WIN]["unit_id"])
covm=uagg.set_index("unit_id")["cov"]
inhs=REC[REC["unit_id"].isin(HS_inc)]; ouths=REC[~REC["unit_id"].isin(HS_inc)]
print(f"\nMolecular coverage in incidence hotspots {cov(inhs):.1f}% vs rest {cov(ouths):.1f}%")

print("Dissolving geometry...")
gdf=sec[["unit_id","geometry"]].dissolve(by="unit_id").reset_index().merge(uagg,on="unit_id",how="left")
STATE=sec.dissolve()

# ── figure ───────────────────────────────────────────────────────────────────
fig,(axA,axB)=plt.subplots(1,2,figsize=(15.5,6.2))
x=dr.index.values
axA.plot(x,dr["cov"],"o-",color="#c0392b",lw=2.6,ms=8)
axA.set_xlabel("Vulnerability decile (1=least → 10=most vulnerable)"); axA.set_ylabel("Molecular (TRM-TB) coverage, %")
axA.set_title("A)  Are the most vulnerable areas the least tested?\nmolecular coverage by vulnerability decile (2020–2024)",fontsize=11.5,fontweight="bold")
axA.grid(alpha=0.3); axA.set_xticks(x)
d2=gdf[gdf["cov"].notna()]; vmin,vmax=np.nanpercentile(d2["cov"],5),np.nanpercentile(d2["cov"],95)
STATE.boundary.plot(ax=axB,color="#aaa",lw=0.3); gdf.plot(ax=axB,color="#eeeeee",edgecolor="white",lw=0.04)
d2.plot(column="cov",ax=axB,cmap="RdYlGn",vmin=vmin,vmax=vmax,edgecolor="white",lw=0.05,legend=True,legend_kwds={"shrink":0.55,"label":"TRM-TB coverage % (red=low=fragile)"})
axB.set_xlim(*ZOOM["xlim"]); axB.set_ylim(*ZOOM["ylim"])
axB.set_title("B)  Molecular coverage by unit — Greater SP + Baixada\n(2020–2024; units with ≥10 known-status cases)",fontsize=11.5,fontweight="bold")
axB.set_xlabel("Longitude"); axB.set_ylabel("Latitude")
fig.suptitle("TB molecular-test (TRM-TB / GeneXpert) coverage — programme fragility, SP adults",fontsize=13,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_molecular_coverage.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_molecular_coverage.png")
