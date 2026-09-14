"""P2 (temporal stability) on the regionalisation unit vs the operational unit. Two plain
metrics, for INCIDENCE (the lens P2 is about): (1) the annual Gini each year 2013-2024 — is
the concentration stable? (2) year-to-year Jaccard overlap of independently re-selected
top-20%-population hotspots — do the same places stay hotspots? Finer units have noisier
ANNUAL rates, so we expect the new (smaller) unit to look a bit less stable year-on-year,
while the underlying geography is the same. Output: /tmp/fig_p2_temporal_comparison.png
"""
import pandas as pd, numpy as np, re, matplotlib, matplotlib.pyplot as plt
from scipy.stats import spearmanr
np.random.seed(20240625); matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
def ns(x):
    if pd.isna(x): return None
    x=str(x).strip(); return x[:-1] if x.endswith("P") else x

print("Lookups + cohort...")
sec=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)[["CD_SETOR","unit_id","pop15"]]
sec=sec[sec["pop15"]>0]
rg=pd.read_csv("/tmp/regions_sectors.csv",dtype={"CD_SETOR":str})[["CD_SETOR","region_id"]]
sec=sec.merge(rg,on="CD_SETOR",how="left"); sec["region_id"]=sec["region_id"].fillna("DIST_"+sec["CD_SETOR"].str.slice(0,9))
def lc(p,raw=False):
    d=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    if not raw:
        d["t"]=d["cnefe_match"].astype(str).str.extract(r"^(T\d)"); d=d[d["t"].isin(["T1","T2","T3"])]
    d["CD_SETOR"]=d["setor_cnefe"].apply(ns); return d[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
co=pd.concat([lc("/tmp/cohort_with_cnefe.csv",raw=True),lc("/tmp/cohort_baixada_with_cnefe_v2.csv"),lc("/tmp/cohort_sp_outros_with_cnefe.csv")])
m=pd.read_csv(f"{SP}/cohort_with_spatial.csv",usecols=["sinan_clean","notification_date","age_tb","tx_seq"],low_memory=False,dtype={"sinan_clean":str})
m["year"]=pd.to_datetime(m["notification_date"],errors="coerce").dt.year
m=m.sort_values("tx_seq").drop_duplicates("sinan_clean",keep="last").set_index("sinan_clean")
co["year"]=co["sinan_clean"].map(m["year"]); co["age"]=co["sinan_clean"].map(m["age_tb"])
co=co[(co["age"]>=15)&co["year"].between(2013,2024)]
look=sec.set_index("CD_SETOR")
for c in ["unit_id","region_id"]: co[c]=co["CD_SETOR"].map(look[c])
YEARS=list(range(2013,2025))

def wgini(c,p):
    m=p>0; n=c[m]; pp=p[m]
    if n.sum()==0: return np.nan
    r=n/pp; o=np.argsort(-r); cp=np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]); cv=np.concatenate([[0],np.cumsum(n[o])/n.sum()])
    return 2*np.trapz(cv,cp)-1
def metrics(col):
    pv=sec.groupby(col)["pop15"].sum(); units=list(pv.index); idx={u:i for i,u in enumerate(units)}; K=len(units); popv=pv.values
    TOT=popv.sum()
    yr_gini={}; hs={}; ratemat=np.full((len(YEARS),K),np.nan)
    for j,y in enumerate(YEARS):
        cc=co[co["year"]==y][col].map(idx).dropna().astype(int)
        cnt=np.bincount(cc.values,minlength=K).astype(float)
        yr_gini[y]=wgini(cnt,popv)
        rate=cnt/popv; ratemat[j]=rate
        o=np.argsort(-rate); cum=np.cumsum(popv[o]); sel=o[cum<=TOT*0.20]
        hs[y]=set(sel.tolist())
    jac=[len(hs[YEARS[i]]&hs[YEARS[i+1]])/len(hs[YEARS[i]]|hs[YEARS[i+1]]) for i in range(len(YEARS)-1)]
    # lag-1 autocorrelation of unit rates (mean Spearman of consecutive years)
    ac=[spearmanr(ratemat[i],ratemat[i+1],nan_policy="omit").correlation for i in range(len(YEARS)-1)]
    return yr_gini,np.array(jac),np.nanmean(ac),K

res={}
for uname,col in [("Operational unit","unit_id"),("Regionalisation (new)","region_id")]:
    yg,jac,ac,K=metrics(col); res[uname]=(yg,jac,ac,K)
    gv=[yg[y] for y in YEARS]
    print(f"\n{uname} (n={K:,})")
    print(f"  annual Gini: {np.nanmin(gv):.3f}-{np.nanmax(gv):.3f} (range {np.nanmax(gv)-np.nanmin(gv):.3f})")
    print(f"  year-to-year hotspot Jaccard: mean {jac.mean():.3f} [{jac.min():.3f}-{jac.max():.3f}]")
    print(f"  lag-1 rate autocorrelation (mean Spearman): {ac:.3f}")

fig,(axA,axB)=plt.subplots(1,2,figsize=(15,5.6))
for uname,c in [("Operational unit","#1f6f8b"),("Regionalisation (new)","#c0392b")]:
    yg=res[uname][0]; axA.plot(YEARS,[yg[y] for y in YEARS],"-o",color=c,lw=2.2,ms=6,label=uname)
axA.set_ylim(0,0.6); axA.set_xlabel("Year"); axA.set_ylabel("Annual Gini (incidence)"); axA.grid(alpha=0.3)
axA.set_title("A)  Is concentration stable each year?\n(flat line = stable)",fontsize=11.5,fontweight="bold"); axA.legend(fontsize=9.5)
xs=np.arange(len(YEARS)-1)
for k,(uname,c) in enumerate([("Operational unit","#1f6f8b"),("Regionalisation (new)","#c0392b")]):
    axB.plot(YEARS[1:],res[uname][1],"-o",color=c,lw=2.2,ms=6,label=f"{uname} (mean {res[uname][1].mean():.2f})")
axB.set_ylim(0,0.7); axB.set_xlabel("Year pair (t-1 → t)"); axB.set_ylabel("Hotspot Jaccard overlap"); axB.grid(alpha=0.3)
axB.set_title("B)  Do the same places stay hotspots?\n(higher = more stable)",fontsize=11.5,fontweight="bold"); axB.legend(fontsize=9.5)
fig.suptitle("P2 — temporal stability: operational vs regionalisation unit (incidence)",fontsize=12.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_p2_temporal_comparison.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_p2_temporal_comparison.png")
