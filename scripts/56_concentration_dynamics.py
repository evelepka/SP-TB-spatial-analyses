"""Alternative views of how TB concentration changes over time (advisor request:
Gini 0.34->0.36 is underwhelming).

(A) Share of cases captured by the top 1/5/10/20% of population, over sliding
    3-year windows -> shows whether the extreme tail is intensifying even if the
    bulk Gini is flat. More interpretable than Gini.
(B) Rate ratio: incidence in the top-10%-population areas vs the rest, over time,
    with bootstrap CI -> "how many fold higher is the hotspot rate", and is the
    gap widening or narrowing.

Adults >=15, new+relapse, 2013-2024, units with >=10 pooled cases.
Output: /tmp/fig_concentration_dynamics.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, matplotlib, matplotlib.pyplot as plt
np.random.seed(20240625)
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SPATIAL="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL,FCU_MIN,MIN_CASES="3550308",5000,10
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
cohort["unit_id"]=cohort["CD_SETOR"].map(sec_res.set_index("CD_SETOR")["unit_id"].to_dict())
cohort=cohort[(cohort["age_tb"]>=15)&cohort["year"].between(2013,2024)].dropna(subset=["unit_id"])
pooled=cohort.groupby("unit_id").size(); elig=[u for u in pooled.index if pooled[u]>=MIN_CASES]
pe=unit_pop.reindex(elig); coh=cohort[cohort["unit_id"].isin(elig)]
print(f"  Eligible pool: {len(elig)} units\n")

def ranked(cnt):
    d=pd.DataFrame({"pop":pe.values,"n":cnt.reindex(elig).fillna(0).values})
    d=d[d["pop"]>0]; d["rate"]=d["n"]/d["pop"]; d=d.sort_values("rate",ascending=False)
    d["cp"]=d["pop"].cumsum()/d["pop"].sum(); return d
def top_share(cnt,frac):
    d=ranked(cnt); return np.interp(frac, np.concatenate([[0],d["cp"].values]),
                                    np.concatenate([[0],(d["n"].cumsum()/d["n"].sum()).values]))*100
def rate_ratio(cnt,frac=0.10):
    d=ranked(cnt); top=d[d["cp"]<=frac]; rest=d[d["cp"]>frac]
    if top["pop"].sum()==0 or rest["pop"].sum()==0: return np.nan
    return (top["n"].sum()/top["pop"].sum())/(rest["n"].sum()/rest["pop"].sum())

WB=3
centers=[]; shares={1:[],5:[],10:[],20:[]}; rr=[]; rr_lo=[]; rr_hi=[]
for y in range(2013,2025-WB+1):
    blk=list(range(y,y+WB)); centers.append(np.mean(blk))
    sub=coh[coh["year"].isin(blk)]; cnt=sub.groupby("unit_id").size()
    for f in (1,5,10,20): shares[f].append(top_share(cnt,f/100))
    rr.append(rate_ratio(cnt,0.10))
    idx=sub["unit_id"].values; bs=[]
    for _ in range(300):
        b=np.random.choice(idx,len(idx),replace=True)
        bs.append(rate_ratio(pd.Series(b).value_counts(),0.10))
    se=np.nanstd(bs); rr_lo.append(rr[-1]-1.96*se); rr_hi.append(rr[-1]+1.96*se)

print("(A) top-X% case share over time (3-yr windows):")
print("  centre  top1%  top5% top10% top20%")
for i,c in enumerate(centers):
    print(f"  {c:.1f}  {shares[1][i]:5.1f}  {shares[5][i]:5.1f}  {shares[10][i]:5.1f}  {shares[20][i]:5.1f}")
print("\n(B) rate ratio top-10% vs rest:")
for c,v,lo,hi in zip(centers,rr,rr_lo,rr_hi): print(f"  {c:.1f}: {v:.2f}x [{lo:.2f},{hi:.2f}]")

fig,(axA,axB)=plt.subplots(1,2,figsize=(15,5.6))
cols={1:"#7a0177",5:"#c0392b",10:"#e8893a",20:"#1a3d5c"}
for f in (20,10,5,1):
    axA.plot(centers,shares[f],"o-",color=cols[f],lw=2.3,ms=6,label=f"Top {f}% of population")
axA.set_xlabel("Window centre (year)"); axA.set_ylabel("% of adult TB cases captured")
axA.set_title("A)  Case share captured by the most-affected areas\n(3-yr sliding windows)",fontsize=11.5,fontweight="bold")
axA.grid(alpha=0.3); axA.legend(fontsize=9,loc="center right"); axA.set_ylim(0,None)
axB.fill_between(centers,rr_lo,rr_hi,color="#c0392b",alpha=0.15,label="95% bootstrap CI")
axB.plot(centers,rr,"o-",color="#c0392b",lw=2.6,ms=7,label="Top 10% vs rest")
axB.set_xlabel("Window centre (year)"); axB.set_ylabel("Incidence-rate ratio (fold)")
axB.set_title("B)  How many fold higher is the hotspot rate?\n(top-10%-population areas vs the rest)",fontsize=11.5,fontweight="bold")
axB.grid(alpha=0.3); axB.legend(fontsize=9,loc="upper right"); axB.set_ylim(0,max(rr_hi)+0.5)
fig.suptitle("How the concentration of adult TB changes over time — São Paulo, 2013–2024",fontsize=12.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_concentration_dynamics.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_concentration_dynamics.png")
