"""Manuscript Figure 2b (regionalisation): clean 4-set Venn of the top-20% hotspot REGIONS
across four lenses — incidence, TB mortality (rate), loss to follow-up, vulnerability index.
Reads /tmp/region_units.csv hotspot flags. Output: /tmp/fig2b_venn_region.png
"""
import pandas as pd, matplotlib, matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from venn import venn
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
d=pd.read_csv("/tmp/region_units.csv")
L={"Incidence":set(d[d["hs_inc"]]["region_id"]),
   "Mortality":set(d[d["hs_mort"]]["region_id"]),
   "LTFU":set(d[d["hs_aband"]]["region_id"]),
   "Vulnerability":set(d[d["hs_vuln"]]["region_id"])}
for k,v in L.items(): print(f"  {k:14s} {len(v)}")
both4=L["Incidence"]&L["Mortality"]&L["LTFU"]&L["Vulnerability"]; print("  all 4:",len(both4))
fig,ax=plt.subplots(figsize=(6.4,6.0))
venn(L,ax=ax,fontsize=10,legend_loc="upper left",cmap=ListedColormap(["#1a3d5c","#7a0177","#1f6f8b","#b8860b"]))
plt.tight_layout(); plt.savefig("/tmp/fig2b_venn_region.png",dpi=300,bbox_inches="tight"); plt.close()
print("Saved /tmp/fig2b_venn_region.png")
