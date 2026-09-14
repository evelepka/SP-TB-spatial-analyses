"""Dedicated chest-imaging (X-ray) analysis: dose-response of X-ray machine capacity
across deciles of MUNICIPAL vulnerability — the treatment molecular coverage and lab
confirmation each already get, now made symmetric for radiography.

X-ray is municipal (CNES has no sub-municipal coordinates), so municipalities are the
unit: 645 municipalities ranked by municipal vulnerability and split into 10 equal-count
deciles (~64-65 each). Within each decile we aggregate:
  - X-ray machines per 100k  = Σ machines / Σ adult pop × 1e5     (supply)
  - X-ray machines per 100 TB cases = Σ machines / Σ cases × 100  (demand-adjusted)
Raio-X = general radiography (TIPEQUIP=1, CODEQUIP 04/05/06; excl. 07 dental, mammography,
CT/MRI), counting MACHINES (QT_EXIST) not just facility presence.
Output: /tmp/fig_xray_doseresponse.png
"""
import pandas as pd, numpy as np, glob, matplotlib, matplotlib.pyplot as plt
from scipy.stats import spearmanr
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
def ns(x):
    if pd.isna(x): return None
    x=str(x).strip(); return x[:-1] if x.endswith("P") else x

print("Municipal population + vulnerability...")
vs=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)[["CD_SETOR","vuln","pop15"]]
vs=vs[vs["pop15"]>0]; vs["mun6"]=vs["CD_SETOR"].str.slice(0,6)
mpop=vs.groupby("mun6")["pop15"].sum(); mvuln=(vs.assign(w=vs["vuln"]*vs["pop15"]).groupby("mun6")["w"].sum())/mpop

print("X-ray machines (EQ) per município...")
eq=pd.read_parquet(glob.glob("/Users/evelynlepkadelima/pysus/EQSP*.parquet")[-1]); eq["mun6"]=eq["CODUFMUN"].astype(str).str.strip()
eq["qt"]=pd.to_numeric(eq["QT_EXIST"],errors="coerce").fillna(0)
xraym=eq[(eq["TIPEQUIP"]=="1")&(eq["CODEQUIP"].isin(["04","05","06"]))&(eq["qt"]>0)].groupby("mun6")["qt"].sum()

print("TB cases per município (adults, 2013-2024)...")
def lc(p,raw=False):
    x=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    if not raw:
        x["t"]=x["cnefe_match"].astype(str).str.extract(r"^(T\d)"); x=x[x["t"].isin(["T1","T2","T3"])]
    x["CD_SETOR"]=x["setor_cnefe"].apply(ns); return x[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
co=pd.concat([lc("/tmp/cohort_with_cnefe.csv",raw=True),lc("/tmp/cohort_baixada_with_cnefe_v2.csv"),lc("/tmp/cohort_sp_outros_with_cnefe.csv")])
m=pd.read_csv(f"{SP}/cohort_with_spatial.csv",usecols=["sinan_clean","notification_date","age_tb","tx_seq"],low_memory=False,dtype={"sinan_clean":str})
m["year"]=pd.to_datetime(m["notification_date"],errors="coerce").dt.year
m=m.sort_values("tx_seq").drop_duplicates("sinan_clean",keep="last").set_index("sinan_clean")
for c in ["year","age_tb"]: co[c]=co["sinan_clean"].map(m[c])
co=co[(co["age_tb"]>=15)&co["year"].between(2013,2024)]; co["mun6"]=co["CD_SETOR"].str.slice(0,6)
mcases=co.groupby("mun6").size()

d=pd.DataFrame({"pop":mpop,"vuln":mvuln}).reset_index()
d["mach"]=d["mun6"].map(xraym).fillna(0); d["cases"]=d["mun6"].map(mcases).fillna(0)
d=d[d["pop"]>0].copy()
d["dec"]=pd.qcut(d["vuln"],10,labels=False)+1   # 1=least vulnerable ... 10=most vulnerable
agg=d.groupby("dec").apply(lambda g:pd.Series({
    "n_mun":len(g),"pop":g["pop"].sum(),"mach":g["mach"].sum(),"cases":g["cases"].sum(),
    "mach_100k":g["mach"].sum()/g["pop"].sum()*1e5,
    "mach_100case":g["mach"].sum()/max(g["cases"].sum(),1)*100})).reset_index()
rho_v=spearmanr(d["vuln"],d["mach"]/d["pop"]).correlation
print(f"\nMunicipalities: {len(d)} | Spearman (machines/100k vs vuln): {rho_v:+.2f}")
print(agg[["dec","n_mun","mach_100k","mach_100case"]].round(2).to_string(index=False))
r1,r10=agg.loc[agg["dec"]==1,"mach_100k"].iloc[0],agg.loc[agg["dec"]==10,"mach_100k"].iloc[0]
c1,c10=agg.loc[agg["dec"]==1,"mach_100case"].iloc[0],agg.loc[agg["dec"]==10,"mach_100case"].iloc[0]
print(f"\nGradient machines/100k: D1={r1:.1f} -> D10={r10:.1f}  ({r1/r10:.1f}x lower in most-vulnerable decile)")
print(f"Gradient machines/100 cases: D1={c1:.1f} -> D10={c10:.1f}  ({c1/c10:.1f}x lower)")

cols=plt.cm.RdYlGn_r(np.linspace(0.05,0.95,10))
fig,(axA,axB)=plt.subplots(1,2,figsize=(14,6))
axA.bar(agg["dec"],agg["mach_100k"],color=cols,edgecolor="white")
axA.set_xlabel("Municipal vulnerability decile (1 = least, 10 = most vulnerable)"); axA.set_ylabel("X-ray machines per 100k adults")
axA.set_title(f"A)  Imaging supply\nmachines/100k: {r1:.1f} (D1) → {r10:.1f} (D10), {r1/r10:.1f}× lower",fontsize=11.5,fontweight="bold")
axA.set_xticks(range(1,11)); axA.grid(axis="y",alpha=0.3)
axB.bar(agg["dec"],agg["mach_100case"],color=cols,edgecolor="white")
axB.set_xlabel("Municipal vulnerability decile (1 = least, 10 = most vulnerable)"); axB.set_ylabel("X-ray machines per 100 TB cases")
axB.set_title(f"B)  Demand-adjusted\nmachines/100 cases: {c1:.1f} (D1) → {c10:.1f} (D10), {c1/c10:.1f}× lower",fontsize=11.5,fontweight="bold")
axB.set_xticks(range(1,11)); axB.grid(axis="y",alpha=0.3)
fig.suptitle("Chest X-ray capacity declines with municipal vulnerability (645 municipalities, deciles ~64-65 each) — SP",fontsize=12.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_xray_doseresponse.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_xray_doseresponse.png")
