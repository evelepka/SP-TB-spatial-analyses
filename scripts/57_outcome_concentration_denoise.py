"""De-noise the 'outcomes are more concentrated than cases' finding (advisor concern:
rarer events -> more Poisson noise -> Gini upward-biased).

(A) RAREFACTION: randomly downsample CASES to the same number of events as TB deaths
    / abandonments, recompute Gini (200 draws). This is the 'constant-rate' null —
    deaths distributed proportionally to cases. If the actual death/abandonment Gini
    exceeds this null, the extra concentration is REAL, not an artefact of fewer events.
(B) UNBIASED RESTRICTION: raise the threshold on CASE count (exposure), NOT on the
    outcome, and check the ordering (cases < deaths < abandonment) holds as noise falls.

Adults >=15, new+relapse, 2013-2024.
Output: /tmp/fig_outcome_denoise.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, matplotlib, matplotlib.pyplot as plt
np.random.seed(20240625)
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SPATIAL="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL,FCU_MIN="3550308",5000
ADULT_COLS=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
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
cohort["year"]=cohort["sinan_clean"].map(meta["year"]); cohort["age_tb"]=cohort["sinan_clean"].map(meta["age_tb"])
cohort["outcome"]=cohort["sinan_clean"].map(meta["case_outcome"])
cohort["unit_id"]=cohort["CD_SETOR"].map(sec_res.set_index("CD_SETOR")["unit_id"].to_dict())
cohort=cohort[(cohort["age_tb"]>=15)&cohort["year"].between(2013,2024)].dropna(subset=["unit_id"])
cohort["death"]=cohort["outcome"].isin(["Obito TB"])
cohort["aband"]=cohort["outcome"].isin(["Abandono","Abandono Primario"])
pooled=cohort.groupby("unit_id").size()

def gini_counts(counts, pop):
    d=pd.DataFrame({"pop":pop.values,"n":counts.values}); d=d[d["pop"]>0]
    if d["n"].sum()==0: return np.nan
    d["rate"]=d["n"]/d["pop"]; d=d.sort_values("rate",ascending=False)
    cp=np.concatenate([[0],(d["pop"].cumsum()/d["pop"].sum()).values])
    cv=np.concatenate([[0],(d["n"].cumsum()/d["n"].sum()).values])
    return 2*np.trapz(cv,cp)-1

# ── (B) unbiased restriction: Gini by CASE threshold ────────────────────────
print("\n=== (B) Gini by event, restricting on CASE count (unbiased) ===")
print(f"{'min_cases':>10}{'n_units':>8}{'cases':>8}{'deaths':>8}{'aband':>8}")
THR=[10,20,30,50]; gini_by_thr={"cases":[],"deaths":[],"aband":[]}
for mc in THR:
    keep=[u for u in pooled.index if pooled[u]>=mc]
    pe=unit_pop.reindex(keep); sub=cohort[cohort["unit_id"].isin(keep)]
    gc=gini_counts(sub.groupby("unit_id").size().reindex(keep).fillna(0),pe)
    gd=gini_counts(sub[sub["death"]].groupby("unit_id").size().reindex(keep).fillna(0),pe)
    ga=gini_counts(sub[sub["aband"]].groupby("unit_id").size().reindex(keep).fillna(0),pe)
    for k,v in [("cases",gc),("deaths",gd),("aband",ga)]: gini_by_thr[k].append(v)
    print(f"{mc:>10}{len(keep):>8}{gc:>8.3f}{gd:>8.3f}{ga:>8.3f}")

# ── (A) rarefaction at >=10 cases ───────────────────────────────────────────
keep10=[u for u in pooled.index if pooled[u]>=10]; pe10=unit_pop.reindex(keep10)
sub10=cohort[cohort["unit_id"].isin(keep10)].reset_index(drop=True)
case_units=sub10["unit_id"].values
N_death=int(sub10["death"].sum()); N_aband=int(sub10["aband"].sum()); N_case=len(sub10)
g_death=gini_counts(sub10[sub10["death"]].groupby("unit_id").size().reindex(keep10).fillna(0),pe10)
g_aband=gini_counts(sub10[sub10["aband"]].groupby("unit_id").size().reindex(keep10).fillna(0),pe10)
g_case =gini_counts(sub10.groupby("unit_id").size().reindex(keep10).fillna(0),pe10)
print(f"\n=== (A) Rarefaction (>=10 cases): N_case={N_case:,} N_death={N_death:,} N_aband={N_aband:,} ===")
def rarefy(n,B=300):
    out=[]
    for _ in range(B):
        samp=np.random.choice(case_units,size=n,replace=False)
        out.append(gini_counts(pd.Series(samp).value_counts().reindex(keep10).fillna(0),pe10))
    return np.array(out)
rd=rarefy(N_death); ra=rarefy(N_aband)
print(f"  Cases observed Gini        : {g_case:.3f}")
print(f"  TB deaths observed Gini    : {g_death:.3f}  | cases rarefied to {N_death:,}: {rd.mean():.3f} [{np.percentile(rd,2.5):.3f},{np.percentile(rd,97.5):.3f}]")
print(f"  Abandonment observed Gini  : {g_aband:.3f}  | cases rarefied to {N_aband:,}: {ra.mean():.3f} [{np.percentile(ra,2.5):.3f},{np.percentile(ra,97.5):.3f}]")
print(f"  -> deaths excess over noise null : {g_death-rd.mean():+.3f}")
print(f"  -> abandonment excess over null  : {g_aband-ra.mean():+.3f}")

# ── figure ──────────────────────────────────────────────────────────────────
fig,(axA,axB)=plt.subplots(1,2,figsize=(15,5.6))
# A: rarefaction
axA.hist(rd,bins=30,color="#bbb",alpha=0.6,density=True,label=f"Cases rarefied to N={N_death:,}\n(constant-rate noise null)")
axA.axvline(g_death,color="#c0392b",lw=3,label=f"TB deaths (observed) = {g_death:.3f}")
axA.hist(ra,bins=30,color="#9ecae1",alpha=0.5,density=True,label=f"Cases rarefied to N={N_aband:,}")
axA.axvline(g_aband,color="#1f6f8b",lw=3,label=f"Abandonment (observed) = {g_aband:.3f}")
axA.axvline(g_case,color="#1a3d5c",lw=2,ls="--",label=f"All cases = {g_case:.3f}")
axA.set_xlabel("Gini coefficient"); axA.set_ylabel("density")
axA.set_title("A)  Rarefaction test — is the excess concentration just fewer events?\nobserved outcome Gini vs cases downsampled to the same N",fontsize=11,fontweight="bold")
axA.legend(fontsize=8,loc="upper left")
# B: Gini by case threshold
xs=range(len(THR))
axB.plot(xs,gini_by_thr["aband"],"s-",color="#1f6f8b",lw=2.4,ms=8,label="Abandonment")
axB.plot(xs,gini_by_thr["deaths"],"o-",color="#c0392b",lw=2.4,ms=8,label="TB deaths")
axB.plot(xs,gini_by_thr["cases"],"^-",color="#1a3d5c",lw=2.4,ms=8,label="Cases")
axB.set_xticks(xs); axB.set_xticklabels([f"≥{t}" for t in THR])
axB.set_xlabel("Restriction: minimum CASE count per unit (selects on exposure, not outcome)")
axB.set_ylabel("Gini coefficient"); axB.set_ylim(0,0.55); axB.grid(alpha=0.3); axB.legend(fontsize=10)
axB.set_title("B)  Ordering holds as noise is reduced\n(deaths/abandonment stay above cases)",fontsize=11,fontweight="bold")
fig.suptitle("Are adverse outcomes genuinely more concentrated than cases, or is it Poisson noise? — SP adults 2013–2024",fontsize=12.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_outcome_denoise.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_outcome_denoise.png")
