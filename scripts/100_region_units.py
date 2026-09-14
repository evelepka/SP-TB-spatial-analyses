"""Foundation for the regionalisation-based MANUSCRIPT: per-REGION dataset with age-
standardised outcomes (incidence, TB-mortality rate, abandonment, TB-mortality %, case-
fatality), the place-vulnerability composite, the individual vulnerability components
(income, % favela, illiteracy, residents/household — NO density per advisor), and top-20%
hotspot flags by lens. Unit = REGIONALISATION (region_id, /tmp/regions_sectors.csv); the
advisor prefers it over the operational unit. Age-standardisation engine reused from
script 78 (indirect, SP internal reference). Output: /tmp/region_units.csv
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, re
SP="/DATA_ROOT/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD="/DATA_ROOT/Abandonment Outcomes/Abandonment Paper/Banco de dados"
T=12; BANDS=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
EDGES=[15,20,25,30,40,50,60,70,200]
def ns(x):
    if pd.isna(x): return None
    x=str(x).strip(); return x[:-1] if x.endswith("P") else x
def nk(x): return x.astype(str).str.strip().str.replace(r'\.0$','',regex=True).str.lstrip("0")

print("Sectors + age bands + REGION id...")
sec=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp")[["CD_SETOR","CD_MUN","CD_DIST","CD_TIPO","geometry"]]
sec["CD_SETOR"]=sec["CD_SETOR"].astype(str)
pop=pd.read_csv(f"{SP}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",sep=";",encoding="latin-1",decimal=",",usecols=["CD_SETOR","v0001"],dtype={"CD_SETOR":str},low_memory=False)
pop["v0001"]=pd.to_numeric(pop["v0001"],errors="coerce").fillna(0)
with zipfile.ZipFile(f"{SP}/IBGE_2022_extended/demografia.zip") as z:
    dem=pd.read_csv(z.open("Agregados_por_setores_demografia_BR.csv"),sep=";",encoding="latin-1",decimal=",",usecols=["CD_setor"]+BANDS,dtype={"CD_setor":str},low_memory=False)
for b in BANDS: dem[b]=pd.to_numeric(dem[b],errors="coerce").fillna(0)
dem=dem.rename(columns={"CD_setor":"CD_SETOR"})
sec=sec.merge(pop,on="CD_SETOR",how="left").merge(dem,on="CD_SETOR",how="left")
sec["v0001"]=sec["v0001"].fillna(0)
for b in BANDS: sec[b]=sec[b].fillna(0)
sec=sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["v0001"]>=100)].copy()   # residential (0=common,1=favela), populated → stable region universe
sec["pop_adult"]=sec[BANDS].sum(axis=1)
# REGION id (regionalisation), fallback to district where uncovered
rg=pd.read_csv("/tmp/regions_sectors.csv",dtype={"CD_SETOR":str})[["CD_SETOR","region_id"]]
sec=sec.merge(rg,on="CD_SETOR",how="left")
sec["region_id"]=sec["region_id"].fillna("DIST_"+sec["CD_DIST"].astype(str))
sec=sec[sec["pop_adult"]>0].copy()
upop=sec.groupby("region_id")[BANDS].sum()

print("Episode-level cohort (each new/relapse notification = one incident case; deaths once per person)...")
# person -> sector (scripts 108/109, unrestricted person geocode)
pg=pd.read_csv("/tmp/geocoded_cohort.csv",dtype={"sinan_clean":str,"CD_SETOR":str})[["sinan_clean","CD_SETOR","tier"]]
pg["region_id"]=pg["CD_SETOR"].map(sec.set_index("CD_SETOR")["region_id"].to_dict())
pg=pg.dropna(subset=["region_id"]).drop_duplicates("sinan_clean")
# master = ALL treatment/notification rows (episode-level)
M=pd.read_csv(f"{SP}/cohort_with_spatial.csv",
    usecols=["sinan_clean","notification_date","age_tb","case_type","case_outcome","address_type","tx_seq"],
    low_memory=False,dtype={"sinan_clean":str})
M["year"]=pd.to_datetime(M["notification_date"],errors="coerce").dt.year
# INCIDENT EPISODES: each Novo/Recidiva notification (adult, in-period, standard residential address);
# retreatments of the same episode are NOT incident cases and are excluded.
epi=M[(M["age_tb"]>=15)&M["year"].between(2013,2024)
      &(M["address_type"]=="ENDERECO PADRAO")&M["case_type"].isin(["Novo","Recidiva"])].copy()
epi=epi.drop_duplicates(["sinan_clean","case_type","year"])   # drop the ~200 same-episode duplicate entries
oc=epi["case_outcome"]                                        # per-EPISODE treatment outcome
epi["aband"]=oc.isin(["Abandono","Abandono Primario"]).astype(int)
epi["eval"]=oc.isin(["Cura","Abandono","Abandono Primario","Obito TB","Obito NTB","Falencia/Resistencia"]).astype(int)
# TB DEATH is a PERSON event, counted ONCE: TBWeb 'Obito TB' on any episode OR SIM tuberculosis (any line)
sim=pd.read_excel(f"{BD}/LINKAGE SIM (1).xlsx",sheet_name="Limpo",usecols=["SINAN","CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"],dtype=str).dropna(subset=["SINAN"])
sim["all"]=[" ".join([str(x) for x in r if x and str(x)!='nan']).upper().replace(".","") for r in sim[["CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"]].values]
stb=set(nk(sim.loc[sim["all"].str.contains(re.compile(r'A1[5-9]')),"SINAN"]))
tbweb_dead=set(M.loc[M["case_outcome"].eq("Obito TB"),"sinan_clean"])
epi["_dead"]=epi["sinan_clean"].isin(tbweb_dead)|nk(epi["sinan_clean"]).isin(stb)
epi=epi.sort_values("tx_seq")
epi["death"]=(epi["_dead"]&(~epi.duplicated("sinan_clean",keep="last"))).astype(int)   # mark on last episode only -> 1 per person
# join person geocode -> region + precision tier
co=epi.merge(pg[["sinan_clean","region_id","tier"]],on="sinan_clean",how="inner")
co["age"]=co["age_tb"]; co["ab"]=pd.cut(co["age"],EDGES,right=False,labels=BANDS)
# authoritative CASE-LEVEL analytic table (episode-level; region assigned) — the single source for all figures
_rc=co[["sinan_clean","region_id","year","age","tier","death","aband","eval"]].copy()
_rc.to_csv("/tmp/region_cases.csv",index=False)
import os as _os
_AN0=f"{SP.rsplit('/Data',1)[0]}/Data/analytic"; _os.makedirs(_AN0,exist_ok=True)
_rc.to_csv(f"{_AN0}/region_cases.csv",index=False)

# state age-specific reference (internal standard) + indirect standardisation (same as script 78)
poptot=upop.sum(); cs=co.groupby("ab",observed=True)
n_a=cs.size().reindex(BANDS).fillna(0); ev_a=cs["eval"].sum().reindex(BANDS).fillna(0)
ab_a=cs["aband"].sum().reindex(BANDS).fillna(0); de_a=cs["death"].sum().reindex(BANDS).fillna(0)
inc_a=n_a/(poptot*T); abr_a=(ab_a/ev_a).replace([np.inf,np.nan],0)
dra_a=de_a/(poptot*T); mp_a=(de_a/n_a).replace([np.inf,np.nan],0)
state_inc=n_a.sum()/(poptot.sum()*T)*1e5; state_ab=ab_a.sum()/ev_a.sum()*100
state_drate=de_a.sum()/(poptot.sum()*T)*1e5; state_mp=de_a.sum()/n_a.sum()*100
def pr(col): return co.groupby(["region_id","ab"],observed=True)[col].sum().unstack(fill_value=0).reindex(columns=BANDS,fill_value=0)
N=co.groupby(["region_id","ab"],observed=True).size().unstack(fill_value=0).reindex(columns=BANDS,fill_value=0)
EV=pr("eval"); AB=pr("aband"); DE=pr("death")
U=upop.index; P=upop.reindex(U).fillna(0)
d=pd.DataFrame({"region_id":U,"pop":P.sum(axis=1).values,
    "n":N.reindex(U).sum(axis=1).values,"ne":EV.reindex(U).sum(axis=1).values,
    "na":AB.reindex(U).sum(axis=1).values,"nd":DE.reindex(U).sum(axis=1).values,
    "E_inc":(P*inc_a*T).sum(axis=1).values,"E_ab":(EV.reindex(U).fillna(0)*abr_a).sum(axis=1).values,
    "E_dr":(P*dra_a*T).sum(axis=1).values,"E_mp":(N.reindex(U).fillna(0)*mp_a).sum(axis=1).values})
ok=d["n"]>=10
d["inc_adj"]=np.where(ok&(d["E_inc"]>0),d["n"]/d["E_inc"]*state_inc,np.nan)
d["ltfu_adj"]=np.where((d["ne"]>=10)&(d["E_ab"]>0),d["na"]/d["E_ab"]*state_ab,np.nan)
d["drate_adj"]=np.where(ok&(d["E_dr"]>0),d["nd"]/d["E_dr"]*state_drate,np.nan)
d["mortprop_adj"]=np.where(ok&(d["E_mp"]>0),d["nd"]/d["E_mp"]*state_mp,np.nan)
d["cfr"]=np.where(d["ne"]>=10,d["nd"]/d["ne"]*100,np.nan)   # case-fatality (deaths/evaluated)
# crude basis (ADR-0006): rates per adult population; LTFU as crude proportion of evaluated
d["inc_crude"]=np.where(ok,d["n"]/(d["pop"]*T)*1e5,np.nan)
d["drate_crude"]=np.where(ok,d["nd"]/(d["pop"]*T)*1e5,np.nan)
d["ltfu_crude"]=np.where(d["ne"]>=10,d["na"]/d["ne"]*100,np.nan)
d["ltfu_percap"]=np.where(ok,d["na"]/(d["pop"]*T)*1e5,np.nan)

# ---- predictors + composite per region (pop-weighted from sectors) ----
vs=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)[["CD_SETOR","pop15","V06004","lit15","v0005","NM_FCU"]]
vf=pd.read_csv("/tmp/vuln_final.csv",dtype={"CD_SETOR":str})[["CD_SETOR","vuln_final"]]
s=sec[["CD_SETOR","region_id","pop_adult"]].merge(vs,on="CD_SETOR",how="left").merge(vf,on="CD_SETOR",how="left")
s["w"]=s["pop15"].fillna(s["pop_adult"]); s["fav"]=s["NM_FCU"].notna().astype(int)
def wm(col):
    t=s.dropna(subset=[col]); return (t[col]*t["w"]).groupby(t["region_id"]).sum()/t.groupby("region_id")["w"].sum()
gp=s.groupby("region_id")
comp=pd.DataFrame({
    "income":wm("V06004"),
    "residents":wm("v0005"),
    "illit":(1-gp["lit15"].sum()/gp["pop15"].sum())*100,
    "favela":gp.apply(lambda x:np.average(x["fav"],weights=x["w"]))*100,
    "vuln":wm("vuln_final"),
}).reset_index()
d=d.merge(comp,on="region_id",how="left")

# ---- top-20%-pop hotspot flags per lens ----
def hs(col,need_eval=False):
    e=d[(d["n"]>=10)] if not need_eval else d[(d["ne"]>=10)]
    e=e.dropna(subset=[col]).sort_values(col,ascending=False); tot=d["pop"].sum()
    cum=e["pop"].cumsum(); m=cum<=tot*0.20
    if m.sum()<len(e): m.iloc[m.sum()]=True
    return set(e[m]["region_id"])
import os,sys; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from rank_basis import RANK,RATE
print(f"hotspot flags on RANK={RANK} basis: {RATE}")
for lens,col,ne in [("inc",RATE["inc"],False),("mort",RATE["mort"],False),("aband",RATE["aband"],True),("cfr","cfr",True),("vuln","vuln",False)]:
    sel=hs(col,ne); d[f"hs_{lens}"]=d["region_id"].isin(sel)
d.to_csv("/tmp/region_units.csv",index=False)
import os
_AN=f"{SP.rsplit('/Data',1)[0]}/Data/analytic"; os.makedirs(_AN,exist_ok=True)
if RANK=="crude": d.to_csv(f"{_AN}/region_units.csv",index=False)   # persist the PRIMARY basis only (survives /tmp wipe)
print(f"\nregions: {len(d):,} | eligible (n>=10): {(d['n']>=10).sum():,}")
print(f"state: incidence {state_inc:.1f}/100k | abandonment {state_ab:.1f}% | TB mort {state_drate:.1f}/100k ({state_mp:.1f}% notif)")
print("hotspots:", {l:int(d[f'hs_{l}'].sum()) for l in ["inc","mort","aband","cfr","vuln"]})
print("Saved /tmp/region_units.csv")
