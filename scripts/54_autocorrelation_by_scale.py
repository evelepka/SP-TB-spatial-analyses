"""Temporal autocorrelation by spatial scale and time-window — is the ~0.5
year-to-year Spearman small-area noise? (advisor follow-up)

Tests whether the rate autocorrelation rises when we reduce per-unit Poisson
noise by (a) using larger areas / higher case thresholds, and (b) pooling years
into multi-year windows. If the underlying pattern is genuinely stable, the
level rises toward 1 and any true decay becomes visible.

Adults >=15, new+relapse, 2013-2024.
Output: /tmp/fig_autocorr_by_scale.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, matplotlib, matplotlib.pyplot as plt
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SPATIAL="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL,FCU_MIN="3550308",5000
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
mun_pop=sec_res.groupby("CD_MUN")["pop_adult"].sum()
setor_mun=sec_res.set_index("CD_SETOR")["CD_MUN"].to_dict()
setor_unit=sec_res.set_index("CD_SETOR")["unit_id"].to_dict()

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
meta["year"]=pd.to_datetime(meta["notification_date"],errors="coerce").dt.year
md=meta.dropna(subset=["sinan_clean"]).drop_duplicates("sinan_clean").set_index("sinan_clean")
cohort["year"]=cohort["sinan_clean"].map(md["year"]); cohort["age_tb"]=cohort["sinan_clean"].map(md["age_tb"])
cohort=cohort[(cohort["age_tb"]>=15)&cohort["year"].between(2013,2024)].dropna(subset=["CD_SETOR"])
cohort["unit_id"]=cohort["CD_SETOR"].map(setor_unit)
cohort["CD_MUN"]=cohort["CD_SETOR"].map(setor_mun)
cohort=cohort.dropna(subset=["unit_id"])

def acf(geo_col, pop_series, min_cases):
    """Spearman ACF over units of a given geography with >=min_cases pooled."""
    pooled=cohort.groupby(geo_col).size()
    keep=[u for u in pooled.index if pooled[u]>=min_cases and u in pop_series.index]
    pe=pop_series.reindex(keep)
    R={}
    for y in YEARS:
        cnt=cohort[cohort["year"]==y].groupby(geo_col).size().reindex(keep).fillna(0)
        R[y]=cnt/pe
    SP=pd.DataFrame(R).corr(method="spearman")
    out={}
    for k in range(1,len(YEARS)):
        out[k]=np.mean([SP.loc[YEARS[i],YEARS[i+k]] for i in range(len(YEARS)-k)])
    med=pooled[keep].median()
    return out, len(keep), med

def window_lag1(geo_col, pop_series, min_cases, w):
    """Mean consecutive-window Spearman for non-overlapping w-year blocks."""
    pooled=cohort.groupby(geo_col).size()
    keep=[u for u in pooled.index if pooled[u]>=min_cases and u in pop_series.index]
    pe=pop_series.reindex(keep)
    blocks=[YEARS[i:i+w] for i in range(0,len(YEARS)-w+1,w)]
    R={}
    for bi,blk in enumerate(blocks):
        cnt=cohort[cohort["year"].isin(blk)].groupby(geo_col).size().reindex(keep).fillna(0)
        R[bi]=cnt/pe
    SP=pd.DataFrame(R).corr(method="spearman")
    return np.mean([SP.loc[i,i+1] for i in range(len(blocks)-1)])

print("\n=== ACF by spatial scale (annual rates) ===")
configs=[("bairro/FCU ≥10","unit_id",unit_pop,10,"#1a3d5c"),
         ("bairro/FCU ≥30","unit_id",unit_pop,30,"#2a7f9e"),
         ("bairro/FCU ≥50","unit_id",unit_pop,50,"#5bb0c9"),
         ("municipality ≥10","CD_MUN",mun_pop,10,"#c0392b")]
acfs={}
print(f"{'scale':<18}{'n_units':>8}{'med_cases':>10}{'lag1':>7}{'lag11':>7}")
for name,col,pop,mc,_ in configs:
    a,n,med=acf(col,pop,mc); acfs[name]=a
    print(f"{name:<18}{n:>8}{med:>10.0f}{a[1]:>7.2f}{a[11]:>7.2f}")

print("\n=== Consecutive Spearman vs window length (bairro/FCU ≥10) ===")
wins={}
for w in [1,2,3,4]:
    wins[w]=window_lag1("unit_id",unit_pop,10,w)
    print(f"  {w}-year window: {wins[w]:.2f}")

# ── figure ──────────────────────────────────────────────────────────────────
fig,(axA,axB)=plt.subplots(1,2,figsize=(15,5.6))
for name,col,pop,mc,c in configs:
    a=acfs[name]; xs=list(a.keys())
    axA.plot(xs,[a[k] for k in xs],"o-",color=c,lw=2.2,ms=5,label=name)
axA.set_xlabel("Lag (years apart)"); axA.set_ylabel("Spearman ρ of rates")
axA.set_title("A)  Autocorrelation rises with area size / case volume\n(less per-unit Poisson noise → higher correlation)",fontsize=11.5,fontweight="bold")
axA.set_xticks(range(1,12)); axA.set_ylim(0,1); axA.grid(alpha=0.3); axA.legend(fontsize=9,loc="lower left")
axB.plot(list(wins.keys()),list(wins.values()),"s-",color="#028090",lw=2.4,ms=9)
for w,v in wins.items(): axB.annotate(f"{v:.2f}",(w,v),textcoords="offset points",xytext=(0,9),ha="center",fontsize=9,color="#028090")
axB.set_xlabel("Time window length (years)"); axB.set_ylabel("Consecutive-window Spearman ρ")
axB.set_title("B)  Pooling years also raises correlation\n(bairro/FCU ≥10; non-overlapping windows)",fontsize=11.5,fontweight="bold")
axB.set_xticks([1,2,3,4]); axB.set_ylim(0,1); axB.grid(alpha=0.3)
fig.suptitle("Is the ~0.5 year-to-year Spearman small-area noise?  São Paulo adults, 2013–2024",fontsize=13,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_autocorr_by_scale.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_autocorr_by_scale.png")
