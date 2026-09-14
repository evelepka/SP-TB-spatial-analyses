"""Advisor request: overlap of the top-20% (hotspot) units by FIVE lenses — incidence,
TB mortality (rate per population), case-fatality (deaths/evaluated), treatment abandonment,
and the place-vulnerability index. All outcome rates age-standardised. We render BOTH a
5-set Venn (what was asked) and an UpSet plot (far more legible for 5 sets), plus a pairwise
Jaccard matrix. Hotspot = top units by the metric until cumulative adult population reaches
20% of the eligible state, on the common eligible set (>=10 cases AND >=10 evaluated).
Output: /tmp/fig_hotspot_venn.png, /tmp/fig_hotspot_upset.png
"""
import pandas as pd, numpy as np, matplotlib, matplotlib.pyplot as plt
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})

u=pd.read_csv("/tmp/outcome_units.csv")
asr=pd.read_csv("/tmp/unit_age_standardised.csv")[["unit_id","drate_adj"]]
u=u.merge(asr,on="unit_id",how="left")
vf=pd.read_csv("/tmp/vuln_final.csv",dtype={"CD_SETOR":str})
vu=vf.groupby("unit_id").apply(lambda d:np.average(d["vuln_final"],weights=d["pop15"])).rename("vuln")
u=u.merge(vu,on="unit_id",how="left")
u["cfr"]=np.where(u["n_eval"]>0, u["n_death_tb"]/u["n_eval"]*100, np.nan)   # case-fatality = deaths / evaluated

elig=u[(u["n_cases"]>=10)&(u["n_eval"]>=10)].dropna(subset=["rate","drate_adj","cfr","aband_pct","vuln"]).copy()
TOT=elig["pop"].sum()
def hs(col):
    d=elig.sort_values(col,ascending=False); cum=d["pop"].cumsum(); m=cum<=TOT*0.20
    if m.sum()<len(d): m.iloc[m.sum()]=True
    return set(d[m]["unit_id"])
LENS={"Incidence":hs("rate"),"Mortality (rate)":hs("drate_adj"),"Case-fatality":hs("cfr"),
      "Abandonment":hs("aband_pct"),"Vulnerability":hs("vuln")}
print(f"Eligible units: {len(elig):,}")
for k,v in LENS.items(): print(f"  {k:18s} hotspots = {len(v)}")
# pairwise Jaccard
keys=list(LENS); print("\nPairwise Jaccard:")
J=pd.DataFrame(index=keys,columns=keys,dtype=float)
for a in keys:
    for b in keys:
        A,B=LENS[a],LENS[b]; J.loc[a,b]=len(A&B)/len(A|B) if (A|B) else np.nan
print(J.round(2).to_string())
# how many units are in 0..5 lenses
from collections import Counter
allu=set().union(*LENS.values()); cnt=Counter()
for x in allu: cnt[sum(x in s for s in LENS.values())]+=1
print("\nUnits by # of lenses they are a hotspot in:", dict(sorted(cnt.items())))

# ---- 5-set Venn ----
try:
    from venn import venn
    fig,ax=plt.subplots(figsize=(9,8))
    venn(LENS,ax=ax,fontsize=9,legend_loc="upper left")
    ax.set_title("Overlap of top-20% hotspot units across five lenses — SP adults 2013–2024\n(age-standardised rates; numbers = units in each intersection)",fontsize=11.5,fontweight="bold")
    plt.tight_layout(); plt.savefig("/tmp/fig_hotspot_venn.png",dpi=150,bbox_inches="tight"); plt.close()
    print("\nSaved /tmp/fig_hotspot_venn.png")
except Exception as e:
    print("venn failed:",e)

# ---- UpSet (legible for 5 sets) ----
try:
    from upsetplot import from_contents, UpSet
    data=from_contents(LENS)
    fig=plt.figure(figsize=(12,6.5))
    UpSet(data,subset_size="count",sort_by="cardinality",show_counts=True,min_subset_size=1).plot(fig=fig)
    fig.suptitle("Hotspot-unit overlap across five lenses (UpSet) — SP adults 2013–2024",fontsize=12.5,fontweight="bold")
    plt.savefig("/tmp/fig_hotspot_upset.png",dpi=150,bbox_inches="tight"); plt.close()
    print("Saved /tmp/fig_hotspot_upset.png")
except Exception as e:
    print("upset failed:",e)
