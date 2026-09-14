"""Age standardisation of all geospatial TB metrics (advisor request): incidence,
abandonment (LTFU), and TB mortality, per geographic unit, adjusted for the age
structure of each place. TB mortality is reported with BOTH denominators (advisor):
a RATE per population (deaths/100k/yr) and a PROPORTION of ALL notified cases
(deaths/notified, not restricted to evaluated/in-treatment cases — the older CFR is
dropped). The TB-death marker is the integrated TBWeb 'Óbito TB' OR SIM TB (A15-A19,
any certificate line), capturing deaths before and/or after treatment.

Method — INDIRECT standardisation (appropriate for small areas; stable where some units
have few cases). The reference is São Paulo State itself (internal standard), so a value
of 1.0 = "as expected for this place's age structure".
  Age bands (census + cohort): 15-19,20-24,25-29,30-39,40-49,50-59,60-69,70+
  Incidence:   SIR = O/E,  E = Σ_a pop_a·T·state_inc_a   → age-adj rate = SIR·state_crude_inc
  Abandonment: O/E among evaluated cases, expected from state age-specific abandonment
  Case-fatality: O/E among evaluated cases, expected from state age-specific CFR
Outputs: /tmp/unit_age_standardised.csv  and  /tmp/fig_age_standardisation.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, re
import matplotlib, matplotlib.pyplot as plt
from scipy.stats import spearmanr
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/DATA_ROOT/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD="/DATA_ROOT/Abandonment Outcomes/Abandonment Paper/Banco de dados"
CAPITAL,FCU_MIN,T="3550308",5000,12   # 2013-2024 = 12 years
BANDS=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
EDGES=[15,20,25,30,40,50,60,70,200]   # bin edges for cohort age -> 8 bands
def ns(x):
    if pd.isna(x): return None
    x=str(x).strip(); return x[:-1] if x.endswith("P") else x
def nk(x): return x.astype(str).str.strip().str.replace(r'\.0$','',regex=True).str.lstrip("0")
def wgini(v,w):
    v=np.asarray(v,float); w=np.asarray(w,float); o=np.argsort(v); v,w=v[o],w[o]
    cw=np.cumsum(w); cv=np.cumsum(v*w)
    if cv[-1]==0: return np.nan
    cv=cv/cv[-1]; cw=cw/cw[-1]
    return 1-np.sum((cw[1:]-cw[:-1])*(cv[1:]+cv[:-1]))

print("Building units + per-band population...")
sec=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp")
sec["CD_MUN"]=sec["CD_MUN"].astype(str); sec["CD_SETOR"]=sec["CD_SETOR"].astype(str)
pop=pd.read_csv(f"{SP}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",sep=";",encoding="latin-1",decimal=",",usecols=["CD_SETOR","v0001"],dtype={"CD_SETOR":str},low_memory=False)
pop["v0001"]=pd.to_numeric(pop["v0001"],errors="coerce").fillna(0)
with zipfile.ZipFile(f"{SP}/IBGE_2022_extended/demografia.zip") as z:
    dem=pd.read_csv(z.open("Agregados_por_setores_demografia_BR.csv"),sep=";",encoding="latin-1",decimal=",",usecols=["CD_setor"]+BANDS,dtype={"CD_setor":str},low_memory=False)
for b in BANDS: dem[b]=pd.to_numeric(dem[b],errors="coerce").fillna(0)
dem=dem.rename(columns={"CD_setor":"CD_SETOR"})
sec=sec.merge(pop,on="CD_SETOR",how="left").merge(dem,on="CD_SETOR",how="left")
sec["v0001"]=sec["v0001"].fillna(0)
for b in BANDS: sec[b]=sec[b].fillna(0)
sec=sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["v0001"]>=100)].copy()
def bkey(r):
    if str(r["CD_MUN"])==CAPITAL: return f"dist_{r['CD_DIST']}"
    if pd.notna(r.get("NM_BAIRRO")): return f"bairro_{r['CD_MUN']}_{r['NM_BAIRRO']}"
    if pd.notna(r.get("NM_DIST")): return f"dist_{r['CD_DIST']}"
    return f"mun_{r['CD_MUN']}"
sec["bairro_id"]=sec.apply(bkey,axis=1)
sec["pop_adult"]=sec[BANDS].sum(axis=1)
fp=sec[sec["NM_FCU"].notna()].groupby("NM_FCU")["pop_adult"].sum(); qf=set(fp[fp>=FCU_MIN].index)
sec["unit_id"]=sec.apply(lambda r: f"fcu__{r['NM_FCU']}" if (pd.notna(r['NM_FCU']) and r['NM_FCU'] in qf) else r["bairro_id"],axis=1)
upop=sec.groupby("unit_id")[BANDS].sum()                       # unit × age-band population

print("Loading cohort with age + outcomes...")
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
co=co[(co["age"]>=15)&co["year"].between(2013,2024)].copy()
sim=pd.read_excel(f"{BD}/LINKAGE SIM (1).xlsx",sheet_name="Limpo",usecols=["SINAN","CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"],dtype=str).dropna(subset=["SINAN"])
sim["all"]=[" ".join([str(x) for x in r if x and str(x)!='nan']).upper().replace(".","") for r in sim[["CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"]].values]
stb=set(nk(sim.loc[sim["all"].str.contains(re.compile(r'A1[5-9]')),"SINAN"]))
oc=co["outcome"]
co["death"]=(oc.eq("Obito TB")|nk(co["sinan_clean"]).isin(stb)).astype(int)
co["aband"]=oc.isin(["Abandono","Abandono Primario"]).astype(int)
co["eval"]=(oc.isin(["Cura","Abandono","Abandono Primario","Obito TB","Obito NTB","Falencia/Resistencia"])|(co["death"]==1)).astype(int)
co["unit_id"]=co["CD_SETOR"].map(sec.set_index("CD_SETOR")["unit_id"].to_dict()); co=co.dropna(subset=["unit_id"])
co["ab"]=pd.cut(co["age"],EDGES,right=False,labels=BANDS)    # age band per case

# state age-specific reference rates (internal standard)
poptot=upop.sum()                                            # state pop per band
cs=co.groupby("ab",observed=True)
n_a=cs.size().reindex(BANDS).fillna(0)                       # cases per band
ev_a=cs["eval"].sum().reindex(BANDS).fillna(0)
ab_a=cs["aband"].sum().reindex(BANDS).fillna(0)
de_a=cs["death"].sum().reindex(BANDS).fillna(0)
inc_a=n_a/(poptot*T)                                        # state incidence per band (per person-year)
abr_a=(ab_a/ev_a).replace([np.inf,np.nan],0)               # state abandonment per band
dra_a=de_a/(poptot*T)                                       # state TB-mortality RATE per band (deaths per person-year)
mp_a=(de_a/n_a).replace([np.inf,np.nan],0)                  # state TB-mortality PROPORTION per band (deaths per NOTIFIED case)
state_inc=n_a.sum()/(poptot.sum()*T)*1e5
state_ab=ab_a.sum()/ev_a.sum()*100
state_drate=de_a.sum()/(poptot.sum()*T)*1e5                 # TB mortality rate /100k/yr
state_mp=de_a.sum()/n_a.sum()*100                           # TB mortality % of notified cases

print("Per-unit observed + expected (indirect standardisation)...")
def perunit(col): return co.groupby(["unit_id","ab"],observed=True)[col].sum().unstack(fill_value=0).reindex(columns=BANDS,fill_value=0)
N=co.groupby(["unit_id","ab"],observed=True).size().unstack(fill_value=0).reindex(columns=BANDS,fill_value=0)
EV=perunit("eval"); AB=perunit("aband"); DE=perunit("death")
units=upop.index
P=upop.reindex(units).fillna(0)
O_inc=N.reindex(units).sum(axis=1); E_inc=(P*inc_a*T).sum(axis=1)
O_ab=AB.reindex(units).sum(axis=1);  E_ab=(EV.reindex(units).fillna(0)*abr_a).sum(axis=1)
O_de=DE.reindex(units).sum(axis=1)
E_dr=(P*dra_a*T).sum(axis=1)                                 # expected TB deaths from POPULATION age-structure (rate)
E_mp=(N.reindex(units).fillna(0)*mp_a).sum(axis=1)           # expected TB deaths from CASE age-mix (proportion)
ev_tot=EV.reindex(units).sum(axis=1)
d=pd.DataFrame({"unit_id":units,"pop":P.sum(axis=1).values,"n":O_inc.values,"ne":ev_tot.values,"na":O_ab.values,"nd":O_de.values,
    "E_inc":E_inc.values,"E_ab":E_ab.values,"E_dr":E_dr.values,"E_mp":E_mp.values})
d["inc_crude"]=np.where(d["n"]>=10,d["n"]/(d["pop"]*T)*1e5,np.nan)
d["inc_adj"]=np.where((d["n"]>=10)&(d["E_inc"]>0),d["n"]/d["E_inc"]*state_inc,np.nan)
d["ltfu_crude"]=np.where(d["ne"]>=10,d["na"]/d["ne"]*100,np.nan)
d["ltfu_adj"]=np.where((d["ne"]>=10)&(d["E_ab"]>0),d["na"]/d["E_ab"]*state_ab,np.nan)
# TB mortality, two denominators (advisor): RATE per population, and PROPORTION of all notified cases
d["drate_crude"]=np.where(d["n"]>=10,d["nd"]/(d["pop"]*T)*1e5,np.nan)              # TB mortality RATE /100k/yr
d["drate_adj"]=np.where((d["n"]>=10)&(d["E_dr"]>0),d["nd"]/d["E_dr"]*state_drate,np.nan)
d["mortprop_crude"]=np.where(d["n"]>=10,d["nd"]/d["n"]*100,np.nan)                 # TB mortality PROPORTION (% of ALL notified)
d["mortprop_adj"]=np.where((d["n"]>=10)&(d["E_mp"]>0),d["nd"]/d["E_mp"]*state_mp,np.nan)
d.to_csv("/tmp/unit_age_standardised.csv",index=False)

# vulnerability per unit (pop-weighted) for the gradient comparison
vs=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)[["CD_SETOR","vuln"]]
s2=sec[["CD_SETOR","unit_id","pop_adult"]].merge(vs,on="CD_SETOR",how="left")
vu=(s2.assign(w=s2["vuln"]*s2["pop_adult"]).groupby("unit_id")["w"].sum())/s2.groupby("unit_id")["pop_adult"].sum()
d["vuln"]=d["unit_id"].map(vu)

print(f"\nState crude: incidence {state_inc:.1f}/100k/yr | abandonment {state_ab:.1f}% | TB mortality {state_drate:.1f}/100k/yr ({state_mp:.1f}% of notified)")
print(f"Units mapped (n>=10): incidence {d['inc_adj'].notna().sum()} | outcomes {d['ltfu_adj'].notna().sum()}")
gi=d.dropna(subset=["inc_crude","inc_adj"])
print(f"\nIncidence  pop-weighted Gini: crude {wgini(gi['inc_crude'],gi['pop']):.3f} -> age-adj {wgini(gi['inc_adj'],gi['pop']):.3f}")
print(f"Incidence  crude vs adj Spearman: {spearmanr(gi['inc_crude'],gi['inc_adj']).correlation:.3f}")
print("\nVulnerability gradient (Spearman vs vuln), crude -> age-adjusted:")
for lab,a,b in [("Incidence","inc_crude","inc_adj"),("Abandonment","ltfu_crude","ltfu_adj"),
                ("TB mortality rate","drate_crude","drate_adj"),("TB mortality prop","mortprop_crude","mortprop_adj")]:
    s=d.dropna(subset=[a,b,"vuln"])
    print(f"  {lab:18s}: {spearmanr(s['vuln'],s[a]).correlation:+.2f} -> {spearmanr(s['vuln'],s[b]).correlation:+.2f}")

# figure: crude vs age-adjusted per unit, 4 metrics (incidence, abandonment, TB mortality rate, TB mortality proportion)
fig,ax=plt.subplots(1,4,figsize=(22,5.6))
for a,(lab,c1,c2,col) in zip(ax,[("Incidence /100k/yr","inc_crude","inc_adj","#1f6f8b"),
        ("Abandonment %","ltfu_crude","ltfu_adj","#d98000"),
        ("TB mortality /100k/yr","drate_crude","drate_adj","#7b2d8e"),
        ("TB mortality % of notified","mortprop_crude","mortprop_adj","#c0392b")]):
    s=d.dropna(subset=[c1,c2]); lim=max(s[c1].quantile(.99),s[c2].quantile(.99))
    a.scatter(s[c1],s[c2],s=14,alpha=0.45,color=col)
    a.plot([0,lim],[0,lim],"--",color="#888",lw=1)
    a.set_xlim(0,lim); a.set_ylim(0,lim)
    a.set_xlabel(f"Crude {lab}"); a.set_ylabel(f"Age-standardised {lab}")
    a.set_title(f"{lab}\nρ(crude,adj)={spearmanr(s[c1],s[c2]).correlation:.2f}",fontsize=11,fontweight="bold"); a.grid(alpha=0.3)
fig.suptitle("Crude vs age-standardised metrics by geographic unit (indirect standardisation, SP internal reference) — SP",fontsize=12.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_age_standardisation.png",dpi=140,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/unit_age_standardised.csv + /tmp/fig_age_standardisation.png")
