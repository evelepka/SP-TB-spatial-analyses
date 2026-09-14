"""Manuscript Figure — smoothed DENSITY (per-capita rate) surfaces for the three outcomes, as ONE
2x3 figure (advisor): row 1 (A,B,C) the ENTIRE state; row 2 (D,E,F) a zoom on the metropolitan areas
(São Paulo metropolitan region + Baixada Santista) with municipal boundaries. Columns = TB incidence,
TB mortality, LTFU, each with its own colour scheme. Each panel = a kernel-smoothed RATE surface =
KDE(cases) / KDE(population) — the spatial density of the outcome adjusted for where people live.
Small dark-grey dots mark case locations (one per incident episode / death / LTFU, at its census-
sector centroid with light jitter). Row labels ("São Paulo State" / "Metropolitan Areas") match the
Table 1 metropolitan/non-metropolitan split.
Reads /tmp/region_cases.csv + /tmp/geocoded_cohort.csv + /tmp/vuln_sectors.csv + the 2022 sector mesh.
Output: /tmp/fig_density_maps_combined.png.
"""
import os, pandas as pd, numpy as np, geopandas as gpd, shapely, matplotlib, matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from matplotlib.colors import PowerNorm
np.random.seed(20240703); matplotlib.rcParams.update({"font.family":"sans-serif","font.size":10})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
ZOOM_CONCURB=["São Paulo/SP","Baixada Santista/SP"]

# ── episode → sector, aggregate per-sector outcome counts ──────────────────────
c=pd.read_csv("/tmp/region_cases.csv",dtype={"sinan_clean":str})
g=pd.read_csv("/tmp/geocoded_cohort.csv",dtype={"sinan_clean":str,"CD_SETOR":str})[["sinan_clean","CD_SETOR"]]
c=c.merge(g,on="sinan_clean",how="left").dropna(subset=["CD_SETOR"])
agg=c.groupby("CD_SETOR").agg(n_inc=("sinan_clean","size"),n_mort=("death","sum"),n_ltfu=("aband","sum")).reset_index()

# ── sector geometry (centroids, metres) + adult population + metro flag ────────
sec=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp")[["CD_SETOR","CD_MUN","NM_CONCURB","geometry"]]
sec["CD_SETOR"]=sec["CD_SETOR"].astype(str); sec=sec.to_crs(31983)
cen=sec.geometry.centroid; sec["x"]=cen.x.values; sec["y"]=cen.y.values
pop=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str})[["CD_SETOR","pop15"]]
sec=sec.merge(pop,on="CD_SETOR",how="left").merge(agg,on="CD_SETOR",how="left")
for k in ["pop15","n_inc","n_mort","n_ltfu"]: sec[k]=sec[k].fillna(0.0)

# ── dissolved boundaries (cached): state outline + metro/Baixada municipalities ─
def state_boundary():
    f="/tmp/sp_state_boundary.gpkg"
    if os.path.exists(f): return gpd.read_file(f)
    uni=shapely.union_all(sec.geometry.buffer(0).values,grid_size=1)
    b=gpd.GeoDataFrame(geometry=[uni.simplify(150)],crs=31983); b.to_file(f); return b
def zoom_munis():
    f="/tmp/sp_zoom_munis.gpkg"
    if os.path.exists(f): return gpd.read_file(f)
    z=sec[sec.NM_CONCURB.isin(ZOOM_CONCURB)].copy(); z["geometry"]=z.geometry.buffer(0)
    polys,codes=[],[]
    for mun,grp in z.groupby("CD_MUN"):
        polys.append(shapely.union_all(grp.geometry.values,grid_size=1).simplify(60)); codes.append(mun)
    m=gpd.GeoDataFrame({"CD_MUN":codes},geometry=polys,crs=31983); m.to_file(f); return m
BND=state_boundary(); MUN=zoom_munis()

sec=sec[np.isfinite(sec.x)&np.isfinite(sec.y)&(sec.pop15>0)]
x=sec.x.values; y=sec.y.values; T=2024-2013+1  # 12 years → annualise
CMAP={"inc":"YlOrRd","mort":"BuPu","ltfu":"YlGnBu"}   # different colour scheme per outcome (advisor)
OUT=[("n_inc","Incidence","inc"),("n_mort","Mortality","mort"),("n_ltfu","LTFU","ltfu")]
# incidence has far more case points than mortality/LTFU → its dots are drawn smaller and fainter
DOT={("state","inc"):(0.3,0.06),("state","rare"):(1.5,0.40),("zoom","inc"):(1.2,0.10),("zoom","rare"):(3.5,0.45)}

def row_surf(xmin,xmax,ymin,ymax,cell,sig_km,clip_geom,jit):
    sig=sig_km*1000/cell
    xe=np.arange(xmin,xmax+cell,cell); ye=np.arange(ymin,ymax+cell,cell); ext=[xmin,xmax,ymin,ymax]
    xc=(xe[:-1]+xe[1:])/2; yc=(ye[:-1]+ye[1:])/2; XX,YY=np.meshgrid(xc,yc,indexing="ij")
    inside=shapely.contains_xy(clip_geom,XX,YY)  # surface clipped to the land polygon
    # wide kernel reach (truncate) so the ratio estimator is DEFINED in every land cell — SP is
    # densely settled, so the "white space" was only the default 4-sigma kernel cutoff, not real gaps.
    def surf(w): H,_,_=np.histogram2d(x,y,bins=[xe,ye],weights=w); return gaussian_filter(H,sig,truncate=15.0,mode="constant")
    Kpop=surf(sec.pop15.values)
    def rate(col): return np.ma.masked_where(~inside,surf(sec[col].values)/(Kpop+1e-12)/T*1e5)
    def dots(col):
        n=sec[col].values.astype(int); xr=np.repeat(x,n); yr=np.repeat(y,n)
        xr=xr+np.random.normal(0,jit,xr.size); yr=yr+np.random.normal(0,jit,yr.size)
        keep=shapely.contains_xy(clip_geom,xr,yr)  # only cases inside the mapped land polygon
        return xr[keep],yr[keep]
    return ext,rate,dots

# ── one combined 2x3 figure: row 1 (A,B,C) statewide · row 2 (D,E,F) metropolitan-areas zoom ──
STATE_GEOM=BND.geometry.iloc[0]; ZOOM_GEOM=shapely.union_all(MUN.geometry.values)
sx0,sx1=x.min()-15000,x.max()+15000; sy0,sy1=y.min()-15000,y.max()+15000
zb=MUN.total_bounds; pad=6000
ROWS=[("state",BND,0.5,dict(xmin=sx0,xmax=sx1,ymin=sy0,ymax=sy1,cell=2500.0,sig_km=24.0,clip_geom=STATE_GEOM,jit=700.0)),
      ("zoom", MUN,0.4,dict(xmin=zb[0]-pad,xmax=zb[2]+pad,ymin=zb[1]-pad,ymax=zb[3]+pad,cell=500.0,sig_km=5.0,clip_geom=ZOOM_GEOM,jit=250.0))]
ROWLAB=["São Paulo State","Metropolitan Areas"]; LETTERS=[["A","B","C"],["D","E","F"]]

fig,axes=plt.subplots(2,3,figsize=(18,11.6))
for r,(scale,outline,lw,gp) in enumerate(ROWS):
    ext,rate,dots=row_surf(**gp)
    for cc,(col,title,tag) in enumerate(OUT):
        ax=axes[r,cc]; R=rate(col); vmax=np.percentile(R.compressed(),97)
        im=ax.imshow(R.T,origin="lower",extent=ext,cmap=CMAP[tag],norm=PowerNorm(0.6,vmin=0,vmax=vmax),interpolation="bilinear",zorder=1)
        outline.boundary.plot(ax=ax,color="#5f6368",linewidth=lw,zorder=1.5)
        ds,da=DOT[(scale,"inc" if tag=="inc" else "rare")]; dx,dy=dots(col)
        ax.scatter(dx,dy,s=ds,c="#2b2b2b",alpha=da,edgecolors="none",zorder=2,rasterized=True)
        ax.set_title(f"({LETTERS[r][cc]}) {title}",fontsize=12.5,fontweight="bold",color="#0d2b45",loc="left")
        ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal"); ax.set_xlim(ext[0],ext[1]); ax.set_ylim(ext[2],ext[3])
        for sp in ax.spines.values(): sp.set_visible(False)
        cb=fig.colorbar(im,ax=ax,fraction=0.046,pad=0.02,shrink=0.8); cb.set_label("per 100 000 adults / year",fontsize=8); cb.ax.tick_params(labelsize=7.5)
plt.tight_layout(rect=[0.01,0,1,0.93],h_pad=7.0)
for r in range(2):                                    # horizontal banner centred above each row
    pos=[axes[r,cc].get_position() for cc in range(3)]
    xctr=(pos[0].x0+pos[2].x1)/2; ytop=max(p.y1 for p in pos)
    fig.text(xctr,ytop+0.032,ROWLAB[r],ha="center",va="bottom",fontsize=16,fontweight="bold",color="#0d2b45")
plt.savefig("/tmp/fig_density_maps_combined.png",dpi=300,bbox_inches="tight"); plt.close()
print("Saved /tmp/fig_density_maps_combined.png | sectors:",len(sec))
