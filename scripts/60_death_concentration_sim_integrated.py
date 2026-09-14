"""Does the TB-mortality concentration finding change once we use the INTEGRATED
mortality (TBweb + SIM), not TBweb alone?

Death markers compared:
  - tbweb_obito_tb : TBweb case_outcome == 'Obito TB' (what scripts 57/59 used)
  - union_underlying: Obito TB OR SIM underlying-cause TB (CAUSABAS in A15-A19)
  - union_anyline  : Obito TB OR SIM TB anywhere on the certificate (CAUSABAS or
                     LINHAA-D or LINHAII) -- recommended; recovers HIV/TB co-infection
                     deaths coded to B20-B24 as the underlying cause.

SIM source: 'Abandonment Paper/Banco de dados/LINKAGE SIM (1).xlsx' sheet 'Limpo'
(full death certificate, 10,056 linked deaths), merged to the cohort by sinan.

For each marker we de-noise exactly as in script 59, and all rates are AGE-STANDARDISED
(indirect, SP internal reference; each unit's event count is multiplied by the age
adjustment factor before the Lorenz, keeping population as the denominator):
  - cross-fit (split-sample) Gini -> removes ranking-selection inflation
  - rarefaction of age-standardised CASES to the same event count -> the constant-rate
    noise null; excess of the observed mortality Gini over that null = genuine concentration.

Adults >=15, 2013-2024, units with >=10 pooled cases.
Output: /tmp/fig_death_sim_integrated.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, re, matplotlib, matplotlib.pyplot as plt
np.random.seed(20240625)
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SPATIAL="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/Abandonment Outcomes/Abandonment Paper/Banco de dados"
CAPITAL,FCU_MIN="3550308",5000
ADULT_COLS=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
def norm_setor(s):
    if pd.isna(s): return None
    s=str(s).strip(); return s[:-1] if s.endswith("P") else s
def norm_key(s):  # consistent sinan normalisation on both sides
    return s.astype(str).str.strip().str.replace(r'\.0$','',regex=True).str.lstrip("0")

print("Building units...")
sec22=gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]=sec22["CD_MUN"].astype(str); sec22["CD_SETOR"]=sec22["CD_SETOR"].astype(str)
pop_df=pd.read_csv(f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
                   sep=";",encoding="latin-1",decimal=",",usecols=["CD_SETOR","v0001"],dtype={"CD_SETOR":str},low_memory=False)
pop_df["pop_total"]=pd.to_numeric(pop_df["v0001"],errors="coerce").fillna(0)
with zipfile.ZipFile(f"{SPATIAL}/IBGE_2022_extended/demografia.zip") as z:
    with z.open("Agregados_por_setores_demografia_BR.csv") as fh:
        demo=pd.read_csv(fh,sep=";",encoding="latin-1",decimal=",",usecols=["CD_setor"]+ADULT_COLS,dtype={"CD_setor":str},low_memory=False)
for _b in ADULT_COLS: demo[_b]=pd.to_numeric(demo[_b],errors="coerce").fillna(0)
demo["pop_adult"]=demo[ADULT_COLS].sum(axis=1)
demo=demo[["CD_setor","pop_adult"]+ADULT_COLS].rename(columns={"CD_setor":"CD_SETOR"})
sec=sec22.merge(pop_df[["CD_SETOR","pop_total"]],on="CD_SETOR",how="left").merge(demo,on="CD_SETOR",how="left")
sec["pop_total"]=sec["pop_total"].fillna(0); sec["pop_adult"]=sec["pop_adult"].fillna(0)
sec_res=sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["pop_total"]>=100)].copy()
def bkey(r):
    if str(r["CD_MUN"])==CAPITAL: return f"dist_{r['CD_DIST']}"
    if pd.notna(r.get("NM_BAIRRO")): return f"bairro_{r['CD_MUN']}_{r['NM_BAIRRO']}"
    if pd.notna(r.get("NM_DIST")): return f"dist_{r['CD_DIST']}"
    return f"mun_{r['CD_MUN']}"
sec_res["bairro_id"]=sec_res.apply(bkey,axis=1)
fcu_pop=sec_res[sec_res["NM_FCU"].notna()].groupby("NM_FCU")["pop_adult"].sum()
qf=set(fcu_pop[fcu_pop>=FCU_MIN].index)
sec_res["unit_id"]=sec_res.apply(lambda r: f"fcu__{r['NM_FCU']}" if (pd.notna(r['NM_FCU']) and r['NM_FCU'] in qf) else r["bairro_id"],axis=1)
unit_pop=sec_res.groupby("unit_id")["pop_adult"].sum()

print("Loading SIM integrated mortality...")
sim=pd.read_excel(f"{BD}/LINKAGE SIM (1).xlsx",sheet_name="Limpo",
    usecols=["SINAN","CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"],dtype=str).dropna(subset=["SINAN"])
TBRE=re.compile(r'A1[5-9]')
def cc(*v): return " ".join([str(x) for x in v if x and str(x)!='nan']).upper().replace(".","")
sim["alllines"]=[cc(*r) for r in sim[["CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"]].values]
sim["ub"]=sim["CAUSABAS"].fillna("").str.upper().str.replace(".","",regex=False)
sim["k"]=norm_key(sim["SINAN"])
sim_ub=set(sim.loc[sim["ub"].str.contains(TBRE),"k"])
sim_any=set(sim.loc[sim["alllines"].str.contains(TBRE),"k"])
print(f"  SIM TB underlying keys: {len(sim_ub):,}  | SIM TB any-line keys: {len(sim_any):,}")

print("Loading adult cases + outcomes...")
def load_co(p,raw=False):
    d=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    if not raw:
        d["tier"]=d["cnefe_match"].astype(str).str.extract(r"^(T\d)"); d=d[d["tier"].isin(["T1","T2","T3"])]
    d["CD_SETOR"]=d["setor_cnefe"].apply(norm_setor)
    return d[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
cohort=pd.concat([load_co("/tmp/cohort_with_cnefe.csv",raw=True),
                  load_co("/tmp/cohort_baixada_with_cnefe_v2.csv"),
                  load_co("/tmp/cohort_sp_outros_with_cnefe.csv")],ignore_index=True)
meta=pd.read_csv(f"{SPATIAL}/cohort_with_spatial.csv",usecols=["sinan_clean","notification_date","age_tb","case_outcome","tx_seq"],low_memory=False,dtype={"sinan_clean":str})
meta["year"]=pd.to_datetime(meta["notification_date"],errors="coerce").dt.year
meta=meta.sort_values("tx_seq").drop_duplicates("sinan_clean",keep="last").set_index("sinan_clean")
cohort["year"]=cohort["sinan_clean"].map(meta["year"]); cohort["age_tb"]=cohort["sinan_clean"].map(meta["age_tb"]); cohort["outcome"]=cohort["sinan_clean"].map(meta["case_outcome"])
cohort["unit_id"]=cohort["CD_SETOR"].map(sec_res.set_index("CD_SETOR")["unit_id"].to_dict())
cohort=cohort[(cohort["age_tb"]>=15)&cohort["year"].between(2013,2024)].dropna(subset=["unit_id"])
ck=norm_key(cohort["sinan_clean"])
cohort["obito_tb"]=cohort["outcome"].eq("Obito TB")
cohort["sim_ub"]=ck.isin(sim_ub); cohort["sim_any"]=ck.isin(sim_any)
cohort["d_tbweb"]=cohort["obito_tb"]
cohort["d_union_ub"]=cohort["obito_tb"]|cohort["sim_ub"]
cohort["d_union_any"]=cohort["obito_tb"]|cohort["sim_any"]
pooled=cohort.groupby("unit_id").size(); elig=[u for u in pooled.index if pooled[u]>=10]
pe=unit_pop.reindex(elig); pev=pe.values; eidx={u:i for i,u in enumerate(elig)}
coh=cohort[cohort["unit_id"].isin(elig)].copy(); coh["ui"]=coh["unit_id"].map(eidx)
print(f"  Eligible pool: {len(elig)} units")
for c,lab in [("d_tbweb","TBweb Obito TB"),("d_union_ub","Union (underlying)"),("d_union_any","Union (any-line)")]:
    print(f"    {lab:22s}: {coh[c].sum():,} deaths in eligible units")
print()

# ── age standardisation (indirect): multiply each unit's event count by the adjustment
#    factor f_u = (crude rate)*(unit pop)/(expected from the unit's age structure). The
#    Lorenz denominator stays the population, so cross-fit/rarefaction still resample
#    integer events; only the per-unit count is age-adjusted (f=1 at the state age mix).
EDGES=[15,20,25,30,40,50,60,70,200]
coh["band"]=pd.cut(coh["age_tb"],EDGES,right=False,labels=False).astype(int)
Pb=sec_res.groupby("unit_id")[ADULT_COLS].sum().reindex(elig).fillna(0).to_numpy(float)  # [n_elig × 8]
popband=Pb.sum(axis=0)
def adj_factor(mask):  # mask: bool array over coh rows
    cb=np.bincount(coh["band"].values[mask],minlength=8).astype(float)
    rate=np.divide(cb,popband,where=popband>0,out=np.zeros(8))   # state age-specific rate
    E_age=Pb@rate; R=cb.sum()/popband.sum()                      # expected per unit; crude rate
    return np.divide(R*pev,E_age,where=E_age>0,out=np.ones_like(E_age))

def gini_from_counts(n,f):
    nn=(n*f)[pev>0]; pp=pev[pev>0]
    if nn.sum()==0: return np.nan
    rate=nn/pp; o=np.argsort(-rate)
    cp=np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]); cv=np.concatenate([[0],np.cumsum(nn[o])/nn.sum()])
    return 2*np.trapz(cv,cp)-1
def counts(ui): return np.bincount(ui,minlength=len(elig)).astype(float)
def cv_gini(ui_array,f,B=120):
    g=[]
    for _ in range(B):
        h=np.random.rand(len(ui_array))<0.5
        a=counts(ui_array[h])*f; b=counts(ui_array[~h])*f
        for rank,val in [(a,b),(b,a)]:
            m=pev>0; ra=rank[m]/pev[m]; vb=val[m]; pp=pev[m]
            if vb.sum()==0: continue
            o=np.argsort(-ra)
            cp=np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]); cvv=np.concatenate([[0],np.cumsum(vb[o])/vb.sum()])
            g.append(2*np.trapz(cvv,cp)-1)
    return np.mean(g),np.std(g)
def rarefy_null(N,f,B=200):  # cases downsampled to N events = constant-rate (age-std) null
    ui_cases=coh["ui"].values; g=[]
    for _ in range(B):
        s=np.random.choice(ui_cases,size=N,replace=False); g.append(gini_from_counts(counts(s),f))
    return np.mean(g),np.std(g)

f_case=adj_factor(np.ones(len(coh),bool))
f_ab=adj_factor(coh["outcome"].isin(["Abandono","Abandono Primario"]).values)
cases_naive=gini_from_counts(counts(coh["ui"].values),f_case); cases_cv=cv_gini(coh["ui"].values,f_case)
ab=coh[coh["outcome"].isin(["Abandono","Abandono Primario"])]["ui"].values
ab_naive=gini_from_counts(counts(ab),f_ab); ab_cv=cv_gini(ab,f_ab)
print(f"CASES        naive={cases_naive:.3f}  cross-fit={cases_cv[0]:.3f}  (age-standardised)")
print(f"ABANDONMENT  naive={ab_naive:.3f}  cross-fit={ab_cv[0]:.3f}\n")

rows=[]
for c,lab in [("d_tbweb","TBweb\nObito TB"),("d_union_ub","Union\nunderlying"),("d_union_any","Union\nany-line")]:
    fmk=adj_factor(coh[c].values)
    ui=coh[coh[c]]["ui"].values; N=len(ui)
    naive=gini_from_counts(counts(ui),fmk); cv=cv_gini(ui,fmk); nullg=rarefy_null(N,f_case)
    excess=naive-nullg[0]
    rows.append((lab,N,naive,cv[0],cv[1],nullg[0],nullg[1],excess))
    print(f"{lab.replace(chr(10),' '):20s} N={N:5d}  naive={naive:.3f}  cross-fit={cv[0]:.3f}  null(age-std cases)={nullg[0]:.3f}  excess={excess:+.3f}")

# ── figure ──────────────────────────────────────────────────────────────────
fig,(axA,axB)=plt.subplots(1,2,figsize=(15,5.8))
labs=[r[0] for r in rows]; x=np.arange(len(labs)); w=0.38
axA.bar(x-w/2,[r[2] for r in rows],w,color="#bbb",label="Naive (noise-inflated)")
axA.bar(x+w/2,[r[3] for r in rows],w,yerr=[1.96*r[4] for r in rows],color="#c0392b",capsize=4,label="De-noised (cross-fit)")
axA.axhline(cases_cv[0],ls="--",color="#1a3d5c",lw=1.8,label=f"Cases (de-noised) = {cases_cv[0]:.2f}")
axA.axhline(ab_cv[0],ls="--",color="#1f6f8b",lw=1.8,label=f"Abandonment (de-noised) = {ab_cv[0]:.2f}")
for i,r in enumerate(rows):
    axA.text(i-w/2,r[2]+0.006,f"{r[2]:.2f}",ha="center",fontsize=8.5)
    axA.text(i+w/2,r[3]+0.006,f"{r[3]:.2f}",ha="center",fontsize=8.5)
axA.set_xticks(x); axA.set_xticklabels(labs,fontsize=9.5); axA.set_ylabel("Gini coefficient"); axA.set_ylim(0,0.55)
axA.set_title("A)  TB-mortality concentration by marker, de-noised (age-standardised)\n(does integrating SIM change the conclusion?)",fontsize=11,fontweight="bold")
axA.legend(fontsize=8.5,loc="upper left")
axB.bar(x,[r[7] for r in rows],0.5,yerr=[1.96*r[6] for r in rows],color="#7a0177",capsize=4)
axB.axhline(0,color="#444",lw=1)
for i,r in enumerate(rows): axB.text(i,r[7]+(0.004 if r[7]>=0 else -0.012),f"{r[7]:+.3f}",ha="center",fontsize=9)
axB.set_xticks(x); axB.set_xticklabels(labs,fontsize=9.5)
axB.set_ylabel("Excess Gini over constant-rate noise null")
axB.set_title("B)  Genuine concentration beyond noise (age-standardised)\n(observed mortality Gini − age-std cases rarefied to same N)",fontsize=11,fontweight="bold")
axB.grid(alpha=0.3,axis="y")
fig.suptitle("TB mortality concentration with integrated TBweb+SIM deaths (age-standardised) — SP adults 2013–2024",fontsize=12.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_death_sim_integrated.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_death_sim_integrated.png")
