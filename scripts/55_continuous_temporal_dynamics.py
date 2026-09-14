"""Continuous / sliding-window temporal dynamics of TB hotspots (advisor request):
characterise how hotspot correlation decays over time and how concentration (Gini)
changes — without hard annual discretization and while handling stochastic noise.

(A) Sliding-window autocorrelation, disattenuated for measurement noise.
    - w-year windows sliding by 1 year -> denser, smoother time series.
    - reliability of each window estimated by split-half (Spearman-Brown corrected).
    - disattenuated corr(lag) = observed corr(lag) / reliability  (lags >= w only,
      i.e. windows with NO shared years -> unbiased decay).
(B) Sliding-window Gini(t) with bootstrap confidence band.
    - centred w-year windows; Gini per window + case-resampling bootstrap CI ->
      shows whether year-to-year wiggles are real or sampling noise.

Adults >=15, new+relapse, 2013-2024, units with >=10 pooled cases.
Output: /tmp/fig_continuous_temporal.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, matplotlib, matplotlib.pyplot as plt
from scipy.stats import spearmanr
np.random.seed(20240625)
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SPATIAL="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL,FCU_MIN,MIN_CASES="3550308",5000,10
ADULT_COLS=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
YEARS=list(range(2013,2025))
def norm_setor(s):
    if pd.isna(s): return None
    s=str(s).strip(); return s[:-1] if s.endswith("P") else s

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

print("Loading adult cases...")
def load_co(p,raw=False):
    d=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    if not raw:
        d["tier"]=d["cnefe_match"].astype(str).str.extract(r"^(T\d)"); d=d[d["tier"].isin(["T1","T2","T3"])]
    d["CD_SETOR"]=d["setor_cnefe"].apply(norm_setor)
    return d[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
cohort=pd.concat([load_co("/tmp/cohort_with_cnefe.csv",raw=True),
                  load_co("/tmp/cohort_baixada_with_cnefe_v2.csv"),
                  load_co("/tmp/cohort_sp_outros_with_cnefe.csv")],ignore_index=True)
meta=pd.read_csv(f"{SPATIAL}/cohort_with_spatial.csv",usecols=["sinan_clean","notification_date","age_tb"],low_memory=False,dtype={"sinan_clean":str})
meta["dt"]=pd.to_datetime(meta["notification_date"],errors="coerce"); meta["year"]=meta["dt"].dt.year
md=meta.dropna(subset=["sinan_clean"]).drop_duplicates("sinan_clean").set_index("sinan_clean")
cohort["year"]=cohort["sinan_clean"].map(md["year"]); cohort["age_tb"]=cohort["sinan_clean"].map(md["age_tb"])
cohort["unit_id"]=cohort["CD_SETOR"].map(sec_res.set_index("CD_SETOR")["unit_id"].to_dict())
cohort=cohort[(cohort["age_tb"]>=15)&cohort["year"].between(2013,2024)].dropna(subset=["unit_id"])
pooled=cohort.groupby("unit_id").size(); elig=[u for u in pooled.index if pooled[u]>=MIN_CASES]
pe=unit_pop.reindex(elig)
coh=cohort[cohort["unit_id"].isin(elig)].copy()
print(f"  Eligible pool: {len(elig)} units\n")

def gini(val):
    d=pd.DataFrame({"pop":pe.values,"val":val.values})
    d=d[d["pop"]>0]; d["rate"]=d["val"]/d["pop"]; d=d.sort_values("rate",ascending=False)
    cp=np.concatenate([[0],(d["pop"].cumsum()/d["pop"].sum()).values])
    cv=np.concatenate([[0],(d["val"].cumsum()/d["val"].sum()).values])
    return 2*np.trapz(cv,cp)-1

# ── (A) sliding-window ACF, disattenuated ───────────────────────────────────
WA=2  # window width (years) for the autocorrelation
wins=[list(range(y,y+WA)) for y in range(2013,2025-WA+1)]
centers=[np.mean(w) for w in wins]
Rwin={}
for i,w in enumerate(wins):
    Rwin[i]=cohort[cohort["year"].isin(w)].groupby("unit_id").size().reindex(elig).fillna(0)/pe
RW=pd.DataFrame(Rwin)
SPW=RW.corr(method="spearman")
# split-half reliability (Spearman-Brown to full window), averaged over windows
rels=[]
for w in wins:
    sub=cohort[cohort["year"].isin(w)]
    h=np.random.rand(len(sub))<0.5
    r1=sub[h].groupby("unit_id").size().reindex(elig).fillna(0)/pe
    r2=sub[~h].groupby("unit_id").size().reindex(elig).fillna(0)/pe
    rels.append(spearmanr(r1,r2).correlation)
rel_half=np.mean(rels); rel_full=2*rel_half/(1+rel_half)
print(f"(A) split-half reliability (half-window)={rel_half:.3f} -> full-window={rel_full:.3f}")
lagvals={}
for i in range(len(wins)):
    for j in range(i+1,len(wins)):
        L=round(centers[j]-centers[i])
        if L>=WA:  # non-overlapping windows only
            lagvals.setdefault(L,[]).append(SPW.iloc[i,j])
lags=sorted(lagvals); obs={L:np.mean(lagvals[L]) for L in lags}; dis={L:obs[L]/rel_full for L in lags}
print(f"{'lag(yr)':>8}{'observed':>10}{'disattenuated':>15}")
for L in lags: print(f"{L:>8}{obs[L]:>10.3f}{dis[L]:>15.3f}")

# ── (B) sliding-window Gini(t) + bootstrap CI ───────────────────────────────
WB=3  # centred window width
gx=[]; gmean=[]; glo=[]; ghi=[]
for y in range(2013,2025-WB+1):
    blk=list(range(y,y+WB)); ctr=np.mean(blk)
    sub=coh[coh["year"].isin(blk)]
    cnt=sub.groupby("unit_id").size().reindex(elig).fillna(0)
    g0=gini(cnt)
    idx=sub["unit_id"].values
    boots=[]
    for _ in range(300):
        bs=np.random.choice(idx,size=len(idx),replace=True)
        cb=pd.Series(bs).value_counts().reindex(elig).fillna(0)
        boots.append(gini(cb))
    se=np.std(boots)  # bootstrap SE around the point estimate (Gini is upward-biased under resampling, so use SE not raw percentiles)
    gx.append(ctr); gmean.append(g0); glo.append(g0-1.96*se); ghi.append(g0+1.96*se)
print("\n(B) sliding-window Gini (centre, value, 95% CI):")
for c,m,lo,hi in zip(gx,gmean,glo,ghi): print(f"  {c:.1f}: {m:.3f} [{lo:.3f},{hi:.3f}]")

# ── figure ──────────────────────────────────────────────────────────────────
fig,(axA,axB)=plt.subplots(1,2,figsize=(15,5.6))
axA.plot(lags,[obs[L] for L in lags],"o-",color="#999",lw=2,ms=6,label="Observed (attenuated by noise)")
axA.plot(lags,[dis[L] for L in lags],"o-",color="#c0392b",lw=2.6,ms=7,label="Disattenuated (true correlation)")
axA.axhline(1,ls=":",color="#ccc",lw=1)
axA.set_xlabel("Lag between window centres (years)"); axA.set_ylabel("Spearman ρ of unit rates")
axA.set_title(f"A)  Sliding-window autocorrelation ({WA}-yr windows)\nnoise-corrected via split-half reliability",fontsize=11.5,fontweight="bold")
axA.set_ylim(0,1.05); axA.set_xticks(lags); axA.grid(alpha=0.3); axA.legend(fontsize=9,loc="lower left")
axB.fill_between(gx,glo,ghi,color="#028090",alpha=0.18,label="95% bootstrap CI")
axB.plot(gx,gmean,"o-",color="#028090",lw=2.6,ms=7,label=f"Gini ({WB}-yr sliding window)")
axB.set_xlabel("Window centre (year)"); axB.set_ylabel("Gini coefficient")
axB.set_title(f"B)  Concentration over time ({WB}-yr sliding window)\nbootstrap CI separates real change from noise",fontsize=11.5,fontweight="bold")
axB.set_ylim(min(glo)-0.02,max(ghi)+0.02); axB.grid(alpha=0.3); axB.legend(fontsize=9,loc="upper right")
fig.suptitle("Continuous temporal dynamics of adult TB hotspots — São Paulo, 2013–2024 (handling stochastic noise)",fontsize=12.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_continuous_temporal.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_continuous_temporal.png")
