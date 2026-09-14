"""APPENDIX sensitivity: how much does the place-vulnerability composite depend on the
favela / urban-agglomeration domain? We compare the MAIN composite (5 domains, favela in)
against the alternative (4 domains, favela out) on the two things that matter:
  A) the TB-incidence dose-response across vulnerability deciles -- with favela the gradient
     is monotonic to the top; without favela it saturates (concave) because favela, where
     TB concentrates, is the axis carrying the top decile;
  B) external agreement with the official IPVS 2022 (SEADE) -- Spearman, and the share of
     our most-vulnerable quintile that the IPVS also rates Alta/Muito Alta.
This is the user's requested "analysis without favela" so the supervisor can judge the call.
Reads /tmp/vuln_final.csv (script 89: vuln_final=5-dom, vuln_nofav=4-dom). Output:
/tmp/fig_appendix_favela_sensitivity.png + printed numbers.
"""
import pandas as pd, numpy as np, geopandas as gpd, re, matplotlib, matplotlib.pyplot as plt
from scipy.stats import spearmanr
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"

sec=pd.read_csv("/tmp/vuln_final.csv",dtype={"CD_SETOR":str})
sec=sec[sec["pop15"]>0].copy()

# ---- cohort -> incidence ----
def ns(x):
    if pd.isna(x): return None
    x=str(x).strip(); return x[:-1] if x.endswith("P") else x
def lc(p,raw=False):
    dd=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    if not raw:
        dd["t"]=dd["cnefe_match"].astype(str).str.extract(r"^(T\d)"); dd=dd[dd["t"].isin(["T1","T2","T3"])]
    dd["CD_SETOR"]=dd["setor_cnefe"].apply(ns); return dd[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
co=pd.concat([lc("/tmp/cohort_with_cnefe.csv",raw=True),lc("/tmp/cohort_baixada_with_cnefe_v2.csv"),lc("/tmp/cohort_sp_outros_with_cnefe.csv")])
m=pd.read_csv(f"{SP}/cohort_with_spatial.csv",usecols=["sinan_clean","age_tb","notification_date","tx_seq"],dtype={"sinan_clean":str},low_memory=False)
m["year"]=pd.to_datetime(m["notification_date"],errors="coerce").dt.year
m=m.sort_values("tx_seq").drop_duplicates("sinan_clean",keep="last").set_index("sinan_clean")
co["age"]=co["sinan_clean"].map(m["age_tb"]); co["year"]=co["sinan_clean"].map(m["year"])
co=co[(co["age"]>=15)&co["year"].between(2013,2024)]

def decile_inc(col):
    d=sec.sort_values(col).copy()
    d["vpct"]=(d["pop15"].cumsum()-0.5*d["pop15"])/d["pop15"].sum()*100
    d["dec"]=np.ceil(d["vpct"]/10).clip(1,10)
    c=co.copy(); c["dec"]=c["CD_SETOR"].map(d.set_index("CD_SETOR")["dec"])
    n=c.groupby("dec").size(); pop=d.groupby("dec")["pop15"].sum()
    inc=(n/(pop*12)*1e5)
    x=np.arange(1,11); b=np.polyfit(x,inc.values,1)
    r2=1-np.sum((inc.values-np.polyval(b,x))**2)/np.sum((inc.values-inc.values.mean())**2)
    return inc.values, r2
i5,r5=decile_inc("vuln_final"); i4,r4=decile_inc("vuln_nofav")
print("Incidence /100k/yr by vulnerability decile:")
print("  5-dom (favela in): "+" ".join(f"{x:.0f}" for x in i5)+f"   R2-lin={r5:.2f}  top/base={i5[-1]/i5[0]:.2f}x")
print("  4-dom (favela out):"+" ".join(f"{x:.0f}" for x in i4)+f"   R2-lin={r4:.2f}  top/base={i4[-1]/i4[0]:.2f}x")

# ---- IPVS agreement, both composites ----
ip=gpd.read_file("/tmp/ipvs_2022/IPVS_2022.shp",ignore_geometry=True)[["CD_SETOR","C_IPVS"]]
ip["CD_SETOR"]=ip["CD_SETOR"].astype(str)
mm=sec.merge(ip,on="CD_SETOR").dropna(subset=["C_IPVS"]); mm["C_IPVS"]=mm["C_IPVS"].astype(int)
def ipvs_stats(col):
    rho,_=spearmanr(mm[col],mm["C_IPVS"])
    q=pd.qcut(mm[col],5,labels=False)+1
    top_overlap=(mm.loc[q==5,"C_IPVS"]>=5).mean()*100
    return rho,top_overlap
rho5,ov5=ipvs_stats("vuln_final"); rho4,ov4=ipvs_stats("vuln_nofav")
print(f"\nIPVS Spearman: 5-dom {rho5:.3f} | 4-dom {rho4:.3f}")
print(f"Most-vuln quintile in IPVS 5-6: 5-dom {ov5:.1f}% | 4-dom {ov4:.1f}%")

# ---- figure ----
fig,(axA,axB)=plt.subplots(1,2,figsize=(13.5,5.4),gridspec_kw={"width_ratios":[1.45,1]})
x=np.arange(1,11)
axA.plot(x,i5,"-o",color="#185FA5",lw=2.6,ms=6,label=f"5 domains — favela IN (main)  ·  R²={r5:.2f}")
axA.plot(x,i4,"--s",color="#993C1D",lw=2.2,ms=5,label=f"4 domains — favela OUT (sensitivity)  ·  R²={r4:.2f}")
axA.set_xticks(x); axA.set_xlabel("Place-vulnerability decile (1 = least, 10 = most)")
axA.set_ylabel("TB incidence per 100k/yr"); axA.grid(alpha=0.3)
axA.set_title("A)  TB-incidence dose-response\nfavela carries the top of the gradient",fontsize=11.5,fontweight="bold")
axA.legend(fontsize=9,loc="upper left")

lbl=["IPVS Spearman ρ","most-vuln quintile\nin IPVS Alta/M.Alta (%)"]
v5=[rho5,ov5/100]; v4=[rho4,ov4/100]; xb=np.arange(2); w=0.36
axB.bar(xb-w/2,v5,w,color="#185FA5",label="5-dom (favela in)")
axB.bar(xb+w/2,v4,w,color="#993C1D",label="4-dom (favela out)")
for i,(a,b) in enumerate(zip(v5,v4)):
    axB.text(i-w/2,a+0.01,f"{a:.2f}" if i==0 else f"{a*100:.0f}%",ha="center",fontsize=9)
    axB.text(i+w/2,b+0.01,f"{b:.2f}" if i==0 else f"{b*100:.0f}%",ha="center",fontsize=9)
axB.set_xticks(xb); axB.set_xticklabels(lbl,fontsize=9.5); axB.set_ylim(0,1)
axB.set_title("B)  External agreement (IPVS 2022)\nfavela slightly improves agreement",fontsize=11.5,fontweight="bold")
axB.legend(fontsize=9,loc="upper right"); axB.grid(axis="y",alpha=0.3)
fig.suptitle("Appendix — sensitivity to the favela / urban-agglomeration domain (SP adults 2013–2024)",fontsize=12.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_appendix_favela_sensitivity.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_appendix_favela_sensitivity.png")
