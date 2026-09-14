"""Temporal autocorrelation of TB hotspots — correlation across ALL year-lags,
not just consecutive years (advisor request).

For adults (>=15), 2013-2024, over the fixed eligible pool (>=10 pooled cases):
  (A) Year x year correlation matrix of unit incidence rates (Spearman) — shows
      whether years far apart still resemble each other.
  (B) Autocorrelation function vs lag: mean Jaccard (hotspot-set overlap) and
      mean Spearman (rate correlation) for all pairs separated by k years.

Output: /tmp/fig_temporal_autocorrelation.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, matplotlib, matplotlib.pyplot as plt
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SPATIAL="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL,FCU_MIN,MIN_CASES,POP_WIN="3550308",5000,10,0.20
ADULT_COLS=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
def norm_setor(s):
    if pd.isna(s): return None
    s=str(s).strip(); return s[:-1] if s.endswith("P") else s

print("Building units (adult denominator)...")
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
qf=set(fcu_pop[fcu_pop>=FCU_MIN].index); TOTAL_POP=sec_res["pop_adult"].sum()
sec_res["unit_id"]=sec_res.apply(lambda r: f"fcu__{r['NM_FCU']}" if (pd.notna(r['NM_FCU']) and r['NM_FCU'] in qf) else r["bairro_id"],axis=1)
upop=sec_res.groupby("unit_id")["pop_adult"].sum()

print("Loading adult cases 2013-2024...")
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
meta["year"]=pd.to_datetime(meta["notification_date"],errors="coerce").dt.year
md=meta.dropna(subset=["sinan_clean"]).drop_duplicates("sinan_clean").set_index("sinan_clean")
cohort["year"]=cohort["sinan_clean"].map(md["year"]); cohort["age_tb"]=cohort["sinan_clean"].map(md["age_tb"])
cohort["unit_id"]=cohort["CD_SETOR"].map(sec_res.set_index("CD_SETOR")["unit_id"].to_dict())
cohort=cohort[(cohort["age_tb"]>=15)&cohort["year"].between(2013,2024)].dropna(subset=["unit_id"])

pooled=cohort.groupby("unit_id").size(); elig=[u for u in pooled.index if pooled[u]>=MIN_CASES]
pop_e=upop.reindex(elig)
print(f"  Eligible pool: {len(elig)} units\n")
YEARS=list(range(2013,2025))

# per-year rate vector + hotspot set over the fixed pool
def hotspot_set(rate):
    d=pd.DataFrame({"pop":pop_e,"rate":rate}).sort_values("rate",ascending=False)
    d["cum"]=d["pop"].cumsum(); m=d["cum"]<=TOTAL_POP*POP_WIN
    if m.sum()<len(d): m.iloc[m.sum()]=True
    return set(d[m].index)
rates={}; sels={}
for y in YEARS:
    cnt=cohort[cohort["year"]==y].groupby("unit_id").size().reindex(elig).fillna(0)
    rates[y]=cnt/pop_e
    sels[y]=hotspot_set(rates[y])
R=pd.DataFrame(rates)                       # unit x year
SP=R.corr(method="spearman")                # 12x12 Spearman of rates
# Jaccard matrix of hotspot sets
JA=pd.DataFrame(index=YEARS,columns=YEARS,dtype=float)
for a in YEARS:
    for b in YEARS:
        JA.loc[a,b]=len(sels[a]&sels[b])/len(sels[a]|sels[b])

# autocorrelation vs lag
print(f"{'Lag':<5}{'n_pairs':>8}{'Jaccard':>10}{'Spearman':>10}")
lags=range(1,12); jac_l={}; sp_l={}; jac_sd={}; sp_sd={}
for k in lags:
    js=[JA.loc[a,a+k] for a in YEARS if a+k in YEARS]
    ss=[SP.loc[a,a+k] for a in YEARS if a+k in YEARS]
    jac_l[k]=np.mean(js); sp_l[k]=np.mean(ss); jac_sd[k]=np.std(js); sp_sd[k]=np.std(ss)
    print(f"{k:<5}{len(js):>8}{np.mean(js):>10.3f}{np.mean(ss):>10.3f}")

# ── figure ──────────────────────────────────────────────────────────────────
fig,(axA,axB)=plt.subplots(1,2,figsize=(15.5,6.2),gridspec_kw={"width_ratios":[1,1.05]})
# A: Spearman correlation matrix heatmap
im=axA.imshow(SP.values,cmap="RdYlBu_r",vmin=0,vmax=1,aspect="equal")
axA.set_xticks(range(len(YEARS))); axA.set_yticks(range(len(YEARS)))
axA.set_xticklabels(YEARS,rotation=45,fontsize=8); axA.set_yticklabels(YEARS,fontsize=8)
for i in range(len(YEARS)):
    for j in range(len(YEARS)):
        v=SP.values[i,j]
        axA.text(j,i,f"{v:.2f}",ha="center",va="center",fontsize=6,
                 color="white" if v>0.7 or v<0.25 else "black")
axA.set_title("A)  Year × year correlation of unit TB rates\n(Spearman ρ — all pairs)",fontsize=12,fontweight="bold")
cb=fig.colorbar(im,ax=axA,shrink=0.8); cb.set_label("Spearman ρ",fontsize=9)
# B: autocorrelation vs lag
xs=list(lags)
axB.plot(xs,[sp_l[k] for k in xs],"o-",color="#c0392b",lw=2.4,ms=7,label="Rate correlation (Spearman ρ)")
axB.fill_between(xs,[sp_l[k]-sp_sd[k] for k in xs],[sp_l[k]+sp_sd[k] for k in xs],color="#c0392b",alpha=0.12)
axB.plot(xs,[jac_l[k] for k in xs],"s-",color="#028090",lw=2.4,ms=7,label="Hotspot overlap (Jaccard)")
axB.fill_between(xs,[jac_l[k]-jac_sd[k] for k in xs],[jac_l[k]+jac_sd[k] for k in xs],color="#028090",alpha=0.12)
axB.set_xlabel("Lag (years apart)"); axB.set_ylabel("Correlation / overlap")
axB.set_title("B)  Temporal autocorrelation vs lag\n(mean over all pairs k years apart; band = ±1 SD)",fontsize=12,fontweight="bold")
axB.set_xticks(xs); axB.set_ylim(0,1); axB.grid(alpha=0.3); axB.legend(fontsize=10,loc="upper right")
fig.suptitle("Temporal autocorrelation of adult TB hotspots — São Paulo state, 2013–2024",fontsize=13,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_temporal_autocorrelation.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_temporal_autocorrelation.png")
print(f"\nLag-1 Spearman {sp_l[1]:.3f} -> Lag-11 (2013 vs 2024) Spearman {SP.loc[2013,2024]:.3f}")
print(f"Lag-1 Jaccard  {jac_l[1]:.3f} -> Lag-11 (2013 vs 2024) Jaccard  {JA.loc[2013,2024]:.3f}")
