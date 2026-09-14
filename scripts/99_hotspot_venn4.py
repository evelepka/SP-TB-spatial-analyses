"""Clean 4-set Venn (fixed symmetric ellipses, counts in each region) of the top-20% hotspot
overlap — incidence, TB mortality (rate), abandonment, vulnerability index (CFR removed).
Companion to the area-proportional Euler (script 97): the Venn is figure-clean but NOT scaled
to size; the Euler is scaled but irregular. Output: /tmp/fig_hotspot_venn4.png
"""
import pandas as pd, numpy as np, matplotlib, matplotlib.pyplot as plt
from venn import venn
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})

u=pd.read_csv("/tmp/outcome_units.csv")
asr=pd.read_csv("/tmp/unit_age_standardised.csv")[["unit_id","drate_adj"]]; u=u.merge(asr,on="unit_id",how="left")
vf=pd.read_csv("/tmp/vuln_final.csv",dtype={"CD_SETOR":str})
vu=vf.groupby("unit_id").apply(lambda d:np.average(d["vuln_final"],weights=d["pop15"])).rename("vuln")
u=u.merge(vu,on="unit_id",how="left")
elig=u[(u["n_cases"]>=10)&(u["n_eval"]>=10)].dropna(subset=["rate","drate_adj","aband_pct","vuln"]).copy()
TOT=elig["pop"].sum()
def hs(col):
    d=elig.sort_values(col,ascending=False); cum=d["pop"].cumsum(); m=cum<=TOT*0.20
    if m.sum()<len(d): m.iloc[m.sum()]=True
    return set(d[m]["unit_id"])
L={"Incidence":hs("rate"),"Mortality":hs("drate_adj"),"Abandonment":hs("aband_pct"),"Vulnerability":hs("vuln")}

fig,ax=plt.subplots(figsize=(9.5,8.5))
venn(L,ax=ax,fontsize=10,legend_loc="upper left",
     cmap=matplotlib.colors.ListedColormap(["#1a3d5c","#7a0177","#1f6f8b","#b8860b"]))
ax.set_title("Overlap of top-20% hotspot units across four lenses (Venn) — SP adults 2013–2024\n"
             "fixed layout, counts per region (not area-proportional — see the Euler for scaled areas)",
             fontsize=11.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_hotspot_venn4.png",dpi=150,bbox_inches="tight"); plt.close()
print("Saved /tmp/fig_hotspot_venn4.png")
