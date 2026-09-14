"""Manuscript Figure 4 (regionalisation): association between vulnerability-index COMPONENTS
(income, % favela, illiteracy, residents/household — all oriented so higher = more deprived)
and the three hotspot types (incidence, mortality, loss to follow-up). Metric = standardized mean
difference (Cohen's d) of each component between hotspot and non-hotspot eligible regions.
TWO layout options (advisor to pick): A) grouped by component, B) grouped by hotspot type.
Reads /tmp/region_units.csv. Output: /tmp/fig4_components_hotspots.png
"""
import pandas as pd, numpy as np, matplotlib, matplotlib.pyplot as plt
from scipy.stats import zscore
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
d=pd.read_csv("/tmp/region_units.csv")
d=d[d["n"]>=10].dropna(subset=["income","favela","illit","residents"]).copy()
# orient each component so higher = more deprived
d["c_income"]=-zscore(d["income"]); d["c_favela"]=zscore(d["favela"]); d["c_illit"]=zscore(d["illit"]); d["c_resid"]=zscore(d["residents"])
COMP=[("c_income","Low income"),("c_favela","% favela"),("c_illit","Illiteracy"),("c_resid","Residents/hh")]
LENS=[("hs_inc","Incidence","#1a3d5c"),("hs_mort","Mortality","#7a0177"),("hs_aband","LTFU","#1f6f8b")]
def cohend(col,flag):
    a=d.loc[d[flag],col]; b=d.loc[~d[flag],col]
    sp=np.sqrt((a.var()+b.var())/2); return (a.mean()-b.mean())/sp if sp>0 else np.nan
M=np.array([[cohend(c,l) for l,_,_ in LENS] for c,_ in COMP])   # rows=comp, cols=lens
print("Cohen's d (component × hotspot type):")
print(pd.DataFrame(M,index=[c[1] for c in COMP],columns=[l[1] for l in LENS]).round(2).to_string())

fig,axA=plt.subplots(1,1,figsize=(9,5.6))   # advisor: use the grouped-by-component layout
xc=np.arange(len(COMP)); w=0.25
for j,(l,ln,col) in enumerate(LENS): axA.bar(xc+(j-1)*w,M[:,j],w,color=col,label=ln)
axA.set_xticks(xc); axA.set_xticklabels([c[1] for c in COMP]); axA.axhline(0,color="#333",lw=0.8)
axA.set_ylabel("Standardized difference (Cohen's d), hotspot − rest"); axA.legend(fontsize=10,title="Hotspot type")
axA.grid(axis="y",alpha=0.3)
plt.tight_layout(); plt.savefig("/tmp/fig4_components_hotspots.png",dpi=300,bbox_inches="tight"); plt.close()
print("Saved /tmp/fig4_components_hotspots.png")
