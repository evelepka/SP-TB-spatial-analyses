"""MUNICIPAL choropleth maps (São Paulo State) of programme infrastructure: place
vulnerability, primary-care (UBS) density, and X-ray machine capacity per 100k, by
MUNICIPALITY (CNES has no coordinates -> municipal resolution; the capital is a single
unit). Companion maps for the programme-fragility report.
Output: /tmp/fig_cnes_municipal_maps.png
"""
import pandas as pd, geopandas as gpd, numpy as np, glob, matplotlib, matplotlib.pyplot as plt
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"

print("Dissolving sectors -> municipal geometry...")
sec22=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp")[["CD_MUN","geometry"]]
sec22["mun6"]=sec22["CD_MUN"].astype(str).str.slice(0,6)
muni=sec22.dissolve(by="mun6").reset_index()
print(f"  municípios: {len(muni)}")

print("Indicators by município...")
vs=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)[["CD_SETOR","vuln","pop15"]]
vs=vs[vs["pop15"]>0]; vs["mun6"]=vs["CD_SETOR"].str.slice(0,6)
pop=vs.groupby("mun6")["pop15"].sum(); vuln=(vs.assign(w=vs["vuln"]*vs["pop15"]).groupby("mun6")["w"].sum())/pop
st=pd.read_parquet("/tmp/cnes_st_sp.parquet"); st["mun6"]=st["CODUFMUN"].astype(str).str.strip()
ubs=st[st["TP_UNID"].isin(["01","02"])].groupby("mun6").size()
eq=pd.read_parquet(glob.glob("/Users/evelynlepkadelima/pysus/EQSP*.parquet")[-1]); eq["mun6"]=eq["CODUFMUN"].astype(str).str.strip()
eq["qt"]=pd.to_numeric(eq["QT_EXIST"],errors="coerce").fillna(0)
xraym=eq[(eq["TIPEQUIP"]=="1")&(eq["CODEQUIP"].isin(["04","05","06"]))&(eq["qt"]>0)].groupby("mun6")["qt"].sum()
d=pd.DataFrame({"pop":pop,"vuln":vuln}).reset_index()
d["ubs_dens"]=(d["mun6"].map(ubs).fillna(0))/d["pop"]*1e5
d["xray_dens"]=(d["mun6"].map(xraym).fillna(0))/d["pop"]*1e5
g=muni.merge(d,on="mun6",how="left")

PAN=[("vuln","Place vulnerability (composite)","Purples",None),
     ("ubs_dens","Primary-care (UBS) per 100k","YlGn",(5,95)),
     ("xray_dens","X-ray machine capacity per 100k","RdYlGn",(5,95))]
fig,axes=plt.subplots(1,3,figsize=(19,7.2))
for ax,(col,title,cmap,clip) in zip(axes,PAN):
    dd=g[g[col].notna()]
    vmin,vmax=(np.nanpercentile(dd[col],clip[0]),np.nanpercentile(dd[col],clip[1])) if clip else (np.nanpercentile(dd[col],2),np.nanpercentile(dd[col],98))
    g.plot(ax=ax,color="#eeeeee",edgecolor="white",lw=0.1)
    dd.plot(column=col,ax=ax,cmap=cmap,vmin=vmin,vmax=vmax,edgecolor="white",lw=0.1,legend=True,legend_kwds={"shrink":0.5})
    ax.set_title(title,fontsize=12,fontweight="bold"); ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
fig.suptitle("Programme infrastructure — MUNICIPAL maps, São Paulo State (645 municipalities; CNES has no sub-municipal coordinates)",fontsize=13,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_cnes_municipal_maps.png",dpi=140,bbox_inches="tight"); plt.close()
print("Saved /tmp/fig_cnes_municipal_maps.png")
