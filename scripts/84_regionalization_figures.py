"""Figures for the unit-definition report: (A) the Vila Andrade test bed showing the
regionalisation keeping Paraisópolis (favela) separate from Morumbi (affluent), and
(B) the state-wide region-size distribution (uniform around ~5,000 adults).
Outputs: /tmp/fig_region_vila_andrade.png, /tmp/fig_region_sizes.png
"""
import geopandas as gpd, pandas as pd, numpy as np, matplotlib, matplotlib.pyplot as plt
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"

reg=pd.read_csv("/tmp/regions_sectors.csv",dtype={"CD_SETOR":str})
g=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp",columns=["CD_SETOR","CD_MUN","NM_DIST","geometry"])
g["CD_SETOR"]=g["CD_SETOR"].astype(str)
g=g.merge(reg,on="CD_SETOR",how="inner")

# ── A) Vila Andrade: regions coloured by income, favela regions outlined ──────────
va=g[(g["CD_MUN"].astype(str)=="3550308")&(g["NM_DIST"]=="Vila Andrade")].copy()
ru=va.dissolve(by="region_id",aggfunc={"inc":"median","fav":"mean","pop15":"sum"}).reset_index()
fig,ax=plt.subplots(figsize=(8.5,8))
ru.plot(column="inc",ax=ax,cmap="RdYlGn",legend=True,edgecolor="white",lw=0.5,
        legend_kwds={"label":"Median household income (R$)","shrink":0.55},vmin=1500,vmax=20000)
ru[ru["fav"]>=0.5].boundary.plot(ax=ax,color="#111",lw=1.8)            # favela regions outlined
ax.set_title("Regionalisation keeps favela and affluent areas apart — Vila Andrade (capital)\n"
             "fill = income (red=poor, green=rich) · thick outline = favela (FCU) units (Paraisópolis)",
             fontsize=11.5,fontweight="bold")
ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
plt.tight_layout(); plt.savefig("/tmp/fig_region_vila_andrade.png",dpi=145,bbox_inches="tight"); plt.close()
print("Saved /tmp/fig_region_vila_andrade.png")

# ── B) state-wide region size distribution ──────────────────────────────────────
u=reg.groupby("region_id").agg(pop=("pop15","sum"),fav=("fav","mean")).reset_index()
fig,ax=plt.subplots(figsize=(9,5.2))
ax.hist(u.loc[u["fav"]<=0.1,"pop"].clip(0,15000),bins=40,color="#1f6f8b",alpha=0.75,label=f"non-favela (n={(u['fav']<=0.1).sum():,})")
ax.hist(u.loc[u["fav"]>=0.9,"pop"].clip(0,15000),bins=40,color="#c0392b",alpha=0.7,label=f"favela (n={(u['fav']>=0.9).sum():,})")
ax.axvline(5000,ls="--",color="#444",lw=1.5,label="target floor = 5,000")
ax.axvline(u["pop"].median(),ls=":",color="#7a0177",lw=1.8,label=f"median = {u['pop'].median():,.0f}")
ax.set_xlabel("Adults per unit"); ax.set_ylabel("Number of units")
ax.set_title(f"State-wide unit sizes — {len(u):,} units, uniform around ~5,000 adults (IQR {u['pop'].quantile(.25):,.0f}–{u['pop'].quantile(.75):,.0f})",fontsize=11.5,fontweight="bold")
ax.legend(fontsize=9.5); ax.grid(alpha=0.3,axis="y")
plt.tight_layout(); plt.savefig("/tmp/fig_region_sizes.png",dpi=145,bbox_inches="tight"); plt.close()
print("Saved /tmp/fig_region_sizes.png")
