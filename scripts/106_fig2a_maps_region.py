"""Manuscript Figure 2 (regionalisation), COMBINED 2x2 (advisor: bigger maps, smaller Venn):
(a) TB-incidence, (b) TB-mortality, (c) treatment-loss to follow-up hotspot maps at the metropolitan
scale (Greater SP + Baixada) — hotspot regions (top 20% of the adult population) solid-coloured,
the rest grey — and (d) a 4-set Venn of the top-20% hotspot overlap (incidence, mortality,
loss to follow-up, vulnerability). Output: /tmp/fig2_combined_region.png
"""
import pandas as pd, geopandas as gpd, numpy as np, os, matplotlib, matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from venn import venn
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":10})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
GEO="/tmp/region_geom.gpkg"
if os.path.exists(GEO):
    g=gpd.read_file(GEO)
else:
    sec=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp")[["CD_SETOR","CD_DIST","CD_TIPO","geometry"]]
    sec["CD_SETOR"]=sec["CD_SETOR"].astype(str); sec=sec[sec["CD_TIPO"].astype(str).isin(["0","1"])]
    rg=pd.read_csv("/tmp/regions_sectors.csv",dtype={"CD_SETOR":str})[["CD_SETOR","region_id"]]
    sec=sec.merge(rg,on="CD_SETOR",how="left"); sec["region_id"]=sec["region_id"].fillna("DIST_"+sec["CD_DIST"].astype(str))
    print("dissolving regions..."); g=sec.dissolve(by="region_id").reset_index()[["region_id","geometry"]]
    g.to_file(GEO,driver="GPKG")
d=pd.read_csv("/tmp/region_units.csv",dtype={"region_id":str})
g["region_id"]=g["region_id"].astype(str); g=g.merge(d,on="region_id",how="left")
try: base=gpd.read_file("/tmp/sp_muni_base.gpkg")
except Exception: base=None
ZOOM=dict(xlim=(-47.35,-46.0),ylim=(-24.15,-23.30))
PAN=[("hs_inc","a) TB incidence","#c0392b"),("hs_mort","b) TB mortality rate","#6a1b9a"),("hs_aband","c) Loss to follow-up","#1565c0")]

fig,axes=plt.subplots(2,2,figsize=(15,13.5)); axf=axes.flatten()
for a,(hsf,lab,c) in zip(axf[:3],PAN):
    if base is not None: base.plot(ax=a,color="#f4f4f4",edgecolor="#e6e6e6",lw=0.1)
    g.plot(ax=a,color="#e0e0e0",edgecolor="none")
    sel=g[g[hsf]==True]
    if len(sel): sel.plot(ax=a,color=c,edgecolor="white",lw=0.12)
    a.set_xlim(*ZOOM["xlim"]); a.set_ylim(*ZOOM["ylim"]); a.set_axis_off()
    a.set_title(f"{lab} hotspots\n(top 20% of population · {int((g[hsf]==True).sum())} regions)",fontsize=12,fontweight="bold",color=c)
# (d) Venn of top-20% hotspot overlap across four lenses
L={"Incidence":set(d[d["hs_inc"]]["region_id"]),"Mortality":set(d[d["hs_mort"]]["region_id"]),
   "Loss to follow-up":set(d[d["hs_aband"]]["region_id"]),"Vulnerability":set(d[d["hs_vuln"]]["region_id"])}
venn(L,ax=axf[3],fontsize=9,legend_loc="upper left",cmap=ListedColormap(["#1a3d5c","#7a0177","#1f6f8b","#b8860b"]))
alln=len(L["Incidence"]&L["Mortality"]&L["Loss to follow-up"]&L["Vulnerability"])
axf[3].set_title(f"d) Overlap of top-20% hotspot regions\n(four lenses · {alln} in all four)",fontsize=12,fontweight="bold",color="#0d2b45")
fig.suptitle("Figure 2. Hotspot regions by outcome and their overlap — Greater São Paulo + Baixada Santista (regionalisation, age-standardised, 2013–2024)",fontsize=12.5,fontweight="bold")
plt.tight_layout(rect=[0,0,1,0.98]); plt.savefig("/tmp/fig2_combined_region.png",dpi=150,bbox_inches="tight"); plt.close()
print("Saved /tmp/fig2_combined_region.png  | all-4 overlap:",alln)
