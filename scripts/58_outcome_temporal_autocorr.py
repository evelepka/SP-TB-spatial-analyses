"""Temporal / autocorrelation of adverse-outcome concentration (advisor request,
continued): does the concentration of deaths & abandonment change over calendar
time, and are the outcome hotspots temporally stable (-> real) or noise?

(A) Sliding-window Gini(t) of deaths and abandonment, bootstrap CI (calendar time).
(B) Disattenuated autocorrelation (split-half reliability) of outcome rates -> if the
    true (noise-corrected) autocorrelation is high, the outcome hotspots persist
    and the concentration is real; if it collapses, it was noise.

Adults >=15, 2013-2024, units with >=10 pooled cases. 3-year sliding windows.
Output: /tmp/fig_outcome_temporal.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, re, matplotlib, matplotlib.pyplot as plt
from scipy.stats import spearmanr
np.random.seed(20240625)
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SPATIAL="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/Abandonment Outcomes/Abandonment Paper/Banco de dados"
CAPITAL,FCU_MIN,MIN_CASES="3550308",5000,10
ADULT_COLS=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
def norm_setor(s):
    if pd.isna(s): return None
    s=str(s).strip(); return s[:-1] if s.endswith("P") else s
def norm_key(s): return s.astype(str).str.strip().str.replace(r'\.0$','',regex=True).str.lstrip("0")

print("Building units...")
sec22=gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]=sec22["CD_MUN"].astype(str); sec22["CD_SETOR"]=sec22["CD_SETOR"].astype(str)
pop_df=pd.read_csv(f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
                   sep=";",encoding="latin-1",decimal=",",usecols=["CD_SETOR","v0001"],dtype={"CD_SETOR":str},low_memory=False)
pop_df["pop_total"]=pd.to_numeric(pop_df["v0001"],errors="coerce").fillna(0)
with zipfile.ZipFile(f"{SPATIAL}/IBGE_2022_extended/demografia.zip") as z:
    with z.open("Agregados_por_setores_demografia_BR.csv") as fh:
        demo=pd.read_csv(fh,sep=";",encoding="latin-1",decimal=",",usecols=["CD_setor"]+ADULT_COLS,dtype={"CD_setor":str},low_memory=False)
demo["pop_adult"]=demo[ADULT_COLS].apply(pd.to_numeric,errors="coerce").fillna(0).sum(axis=1)
demo=demo[["CD_setor","pop_adult"]].rename(columns={"CD_setor":"CD_SETOR"})
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
# integrated TB-death marker: TBweb 'Obito TB' OR SIM TB on any death-certificate line (see script 60)
sim=pd.read_excel(f"{BD}/LINKAGE SIM (1).xlsx",sheet_name="Limpo",usecols=["SINAN","CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"],dtype=str).dropna(subset=["SINAN"])
sim["all"]=[" ".join([str(x) for x in r if x and str(x)!='nan']).upper().replace(".","") for r in sim[["CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"]].values]
sim_tb=set(norm_key(sim.loc[sim["all"].str.contains(re.compile(r'A1[5-9]')),"SINAN"]))
cohort["death"]=cohort["outcome"].eq("Obito TB")|norm_key(cohort["sinan_clean"]).isin(sim_tb)
cohort["aband"]=cohort["outcome"].isin(["Abandono","Abandono Primario"])
pooled=cohort.groupby("unit_id").size(); elig=[u for u in pooled.index if pooled[u]>=MIN_CASES]
pe=unit_pop.reindex(elig); coh=cohort[cohort["unit_id"].isin(elig)]
print(f"  Eligible pool: {len(elig)} units\n")
YEARS=list(range(2013,2025))

def gini(counts):
    d=pd.DataFrame({"pop":pe.values,"n":counts.reindex(elig).fillna(0).values}); d=d[d["pop"]>0]
    if d["n"].sum()==0: return np.nan
    d["rate"]=d["n"]/d["pop"]; d=d.sort_values("rate",ascending=False)
    cp=np.concatenate([[0],(d["pop"].cumsum()/d["pop"].sum()).values]); cv=np.concatenate([[0],(d["n"].cumsum()/d["n"].sum()).values])
    return 2*np.trapz(cv,cp)-1

# ── (A) sliding-window Gini(t) for outcomes, bootstrap CI ────────────────────
WB=3
def slide_gini(flag):
    ev=coh[coh[flag]] if flag else coh
    cx=[];gm=[];lo=[];hi=[]
    for y in range(2013,2025-WB+1):
        blk=list(range(y,y+WB)); sub=ev[ev["year"].isin(blk)]; cx.append(np.mean(blk))
        g0=gini(sub.groupby("unit_id").size()); idx=sub["unit_id"].values
        bs=[gini(pd.Series(np.random.choice(idx,len(idx),replace=True)).value_counts()) for _ in range(200)]
        se=np.nanstd(bs); gm.append(g0); lo.append(g0-1.96*se); hi.append(g0+1.96*se)
    return cx,gm,lo,hi
gx,gd,gd_lo,gd_hi=slide_gini("death"); _,ga,ga_lo,ga_hi=slide_gini("aband")
print("(A) sliding-window Gini(t):")
for i,c in enumerate(gx): print(f"  {c:.1f}: deaths {gd[i]:.3f}[{gd_lo[i]:.3f},{gd_hi[i]:.3f}]  aband {ga[i]:.3f}[{ga_lo[i]:.3f},{ga_hi[i]:.3f}]")

# ── (B) disattenuated autocorrelation of outcome rates ──────────────────────
WA=3
wins=[list(range(y,y+WA)) for y in range(2013,2025-WA+1)]; centers=[np.mean(w) for w in wins]
def acf_disatt(flag):
    R={};
    for i,w in enumerate(wins):
        ev=coh[coh[flag] & coh["year"].isin(w)]
        R[i]=ev.groupby("unit_id").size().reindex(elig).fillna(0)/pe
    SP=pd.DataFrame(R).corr(method="spearman")
    rels=[]
    for w in wins:
        ev=coh[coh[flag] & coh["year"].isin(w)]
        if len(ev)<10: continue
        h=np.random.rand(len(ev))<0.5
        r1=ev[h].groupby("unit_id").size().reindex(elig).fillna(0)/pe
        r2=ev[~h].groupby("unit_id").size().reindex(elig).fillna(0)/pe
        rels.append(spearmanr(r1,r2).correlation)
    rh=np.nanmean(rels); rf=2*rh/(1+rh)
    lagv={}
    for i in range(len(wins)):
        for j in range(i+1,len(wins)):
            L=round(centers[j]-centers[i])
            if L>=WA: lagv.setdefault(L,[]).append(SP.iloc[i,j])
    lags=sorted(lagv); obs={L:np.nanmean(lagv[L]) for L in lags}; dis={L:min(obs[L]/rf,1.05) for L in lags}
    return rf,lags,obs,dis
rf_a,lags,obs_a,dis_a=acf_disatt("aband")
rf_c,_,obs_c,dis_c=acf_disatt(None) if False else (None,None,None,None)
# cases reference reliability
ev=coh;
relc=[]
for w in wins:
    e=ev[ev["year"].isin(w)]; h=np.random.rand(len(e))<0.5
    relc.append(spearmanr(e[h].groupby("unit_id").size().reindex(elig).fillna(0)/pe,
                          e[~h].groupby("unit_id").size().reindex(elig).fillna(0)/pe).correlation)
rh=np.nanmean(relc); rf_cases=2*rh/(1+rh)
print(f"\n(B) full-window reliability: cases={rf_cases:.3f}  abandonment={rf_a:.3f}")
print(f"   abandonment ACF (lag: observed -> disattenuated):")
for L in lags: print(f"     {L}yr: {obs_a[L]:.3f} -> {dis_a[L]:.3f}")

# ── figure ──────────────────────────────────────────────────────────────────
fig,(axA,axB)=plt.subplots(1,2,figsize=(15,5.6))
axA.fill_between(gx,ga_lo,ga_hi,color="#1f6f8b",alpha=0.15); axA.plot(gx,ga,"s-",color="#1f6f8b",lw=2.4,ms=7,label="Abandonment")
axA.fill_between(gx,gd_lo,gd_hi,color="#c0392b",alpha=0.15); axA.plot(gx,gd,"o-",color="#c0392b",lw=2.4,ms=7,label="TB deaths (TBweb+SIM)")
axA.set_xlabel("Window centre (year)"); axA.set_ylabel("Gini coefficient")
axA.set_title("A)  Concentration of adverse outcomes over calendar time\n(3-yr sliding windows, bootstrap CI)",fontsize=11,fontweight="bold")
axA.grid(alpha=0.3); axA.legend(fontsize=10)
axB.plot(lags,[obs_a[L] for L in lags],"o-",color="#999",lw=2,ms=6,label="Observed (noise-attenuated)")
axB.plot(lags,[dis_a[L] for L in lags],"o-",color="#1f6f8b",lw=2.6,ms=7,label="Disattenuated (true)")
axB.axhline(1,ls=":",color="#ccc")
axB.set_xlabel("Lag between window centres (years)"); axB.set_ylabel("Spearman ρ of abandonment rates")
axB.set_title(f"B)  Are abandonment hotspots stable over time?\n(reliability: cases {rf_cases:.2f} vs abandonment {rf_a:.2f})",fontsize=11,fontweight="bold")
axB.set_ylim(0,1.1); axB.set_xticks(lags); axB.grid(alpha=0.3); axB.legend(fontsize=9,loc="lower left")
fig.suptitle("Adverse-outcome concentration over time, de-noised — SP adults 2013–2024",fontsize=12.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_outcome_temporal.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_outcome_temporal.png")
