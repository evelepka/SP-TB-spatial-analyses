"""Manuscript Figure 1 — CHOROPLETH of the analysis regionalisation (replaces the kernel-smoothed
surfaces; NM review comments #55/#56 and Evelyn 2026-08-11: show the outcomes the analysis uses,
on the units the analysis uses).

2x3 panels: columns = notified TB incidence (age-std), TB mortality (age-std), LTFU (age-adjusted
% of evaluated episodes, ADR-0005); row 1 = whole state, row 2 = metropolitan zoom (Greater São
Paulo + Baixada Santista). Regions below the reporting threshold (<10 cases / <10 evaluated) are
grey — the suppression rule made visible. Colour scales capped at the 98th percentile of eligible
regions. Reads /tmp/region_units.csv + /tmp/region_geom.gpkg. Output: /tmp/fig1_choropleth.png
"""
import pandas as pd, geopandas as gpd, numpy as np, matplotlib, matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.cm import ScalarMappable
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
ZOOM_CONCURB=["São Paulo/SP","Baixada Santista/SP"]

geo=gpd.read_file("/tmp/region_geom.gpkg").to_crs(31983)
ru=pd.read_csv("/tmp/region_units.csv",dtype={"region_id":str})
import os,sys; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from rank_basis import RANK,SUF,RATE,RATE_LABEL
g=geo.merge(ru[["region_id",RATE["inc"],RATE["mort"],RATE["aband"]]],on="region_id",how="left")

# metropolitan municipality outlines, dissolved per municipality (cached)
import os
CACHE="/tmp/sp_zoom_munis_dissolved.gpkg"
if os.path.exists(CACHE):
    mun=gpd.read_file(CACHE)
else:
    sec=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp")[["CD_MUN","NM_CONCURB","geometry"]].to_crs(31983)
    z=sec[sec["NM_CONCURB"].isin(ZOOM_CONCURB)].copy()
    z["geometry"]=z.geometry.buffer(0)
    mun=z.dissolve(by="CD_MUN")[["geometry"]].reset_index()
    mun["geometry"]=mun.geometry.simplify(60)
    mun.to_file(CACHE)
zx0,zy0,zx1,zy1=mun.total_bounds

PANELS=[(RATE["inc"],RATE_LABEL["inc"],"#1a3d5c"),(RATE["mort"],RATE_LABEL["mort"],"#7a0177"),(RATE["aband"],RATE_LABEL["aband"],"#1f6f8b")]
GREY="#d8d8d8"

fig,axes=plt.subplots(2,3,figsize=(15.6,10.6),gridspec_kw={"hspace":0.02,"wspace":0.02})
letters="ABCDEF"
for j,(col,lab,cx) in enumerate(PANELS):
    cmap=LinearSegmentedColormap.from_list(col,["#f6f8fa",cx])
    vmax=np.nanpercentile(g[col],98); norm=Normalize(vmin=0,vmax=vmax)
    for i,(ax,scope) in enumerate([(axes[0,j],"state"),(axes[1,j],"zoom")]):
        gg=g if scope=="state" else g.cx[zx0:zx1,zy0:zy1]
        gg[gg[col].isna()].plot(ax=ax,color=GREY,edgecolor="none",rasterized=True)
        gg[gg[col].notna()].plot(ax=ax,column=col,cmap=cmap,norm=norm,edgecolor="none",rasterized=True)
        if scope=="zoom":
            mun.boundary.plot(ax=ax,color="#777",linewidth=0.4)
            ax.set_xlim(zx0,zx1); ax.set_ylim(zy0,zy1)
        ax.set_axis_off()
        ax.set_title(f"({letters[i*3+j]})",loc="left",fontsize=13,fontweight="bold")
        if i==0: ax.text(0.5,1.05,lab,transform=ax.transAxes,ha="center",fontsize=10.5)
    # colorbar horizontal sob a coluna
    sm=ScalarMappable(norm=norm,cmap=cmap)
    pos=axes[1,j].get_position()
    cax=fig.add_axes([pos.x0+pos.width*0.12,pos.y0-0.055,pos.width*0.76,0.014])
    cb=fig.colorbar(sm,cax=cax,orientation="horizontal")
    cb.ax.tick_params(labelsize=8.5)
    cb.set_label(f"capped at 98th percentile ({vmax:.0f})",fontsize=8)
fig.text(0.5,-0.035,"Grey: regions below the reporting threshold (<10 cases, 2013–2024). Bottom row: Greater São Paulo and Baixada Santista, with municipal boundaries.",
         ha="center",fontsize=9,color="#555")
plt.savefig(f"/tmp/fig1_choropleth{SUF}.png",dpi=300,bbox_inches="tight"); plt.savefig(f"/tmp/fig1_choropleth{SUF}.pdf",bbox_inches="tight",dpi=400)   # polygons rasterised at 400 dpi, text stays vector; plt.close()
n_el=ru[RATE["inc"]].notna().sum()
print(f"regions: {len(ru):,} | coloured (eligible): {n_el:,} | grey: {len(ru)-n_el:,}")
print(f"Saved /tmp/fig1_choropleth{SUF}.png")
