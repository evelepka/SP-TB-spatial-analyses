"""Manuscript temporal-stability ALLUVIAL (advisor idea): rank regions by TB incidence into
quintiles in each 3-year period (2013–15, 2016–18, 2019–21, 2022–24) and show how regions flow
between quintiles over time. Quintiles (not deciles) because ~4 cases/region per 3-year period make
finer bins noise-dominated. Eligible regions (>=10 cases over the decade). Ribbons coloured by the
ORIGIN (2013-15 baseline) quintile, carried through time so each cohort can be traced visually.
Output: /tmp/fig_alluvial_incidence.png
"""
import pandas as pd, numpy as np, matplotlib, matplotlib.pyplot as plt
from matplotlib.path import Path
import matplotlib.patches as mpatches
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
NB=5   # quintiles
reg=pd.read_csv("/tmp/region_units.csv",dtype={"region_id":str})[["region_id","pop","n"]]
reg=reg[(reg["pop"]>0)&(reg["n"]>=10)].reset_index(drop=True)          # eligible regions
co=pd.read_csv("/tmp/region_cases.csv",dtype={"region_id":str})
PER=[(2013,2015),(2016,2018),(2019,2021),(2022,2024)]; PL=["2013–15","2016–18","2019–21","2022–24"]
Q=pd.DataFrame(index=reg["region_id"])
for i,p in enumerate(PER):
    c=co[co.year.between(*p)].groupby("region_id").size()
    r=reg.set_index("region_id").assign(c=c).fillna({"c":0})
    rate=(r["c"]/r["pop"]).reindex(reg["region_id"].values)
    Q[i]=pd.qcut(rate.rank(method="first"),NB,labels=False).values   # 0=lowest .. NB-1=highest
N=len(Q)

# layout
gap=0.018; bh=(1-(NB-1)*gap)/NB                      # block height
def yb(j): return j*(bh+gap)                          # bottom-y of quintile block j (0 bottom .. top)
nodw=0.045
cols=["#fdd9a0","#fdae61","#f46d43","#c0392b","#7a0177"]  # Q1(low) light -> Q5(high) dark
fig,ax=plt.subplots(figsize=(12,7))
def ribbon(x0,x1,ys0,ys1,yt0,yt1,color):
    xm=(x0+x1)/2
    verts=[(x0,ys0),(xm,ys0),(xm,yt0),(x1,yt0),(x1,yt1),(xm,yt1),(xm,ys1),(x0,ys1),(x0,ys0)]
    codes=[Path.MOVETO,Path.CURVE4,Path.CURVE4,Path.CURVE4,Path.LINETO,Path.CURVE4,Path.CURVE4,Path.CURVE4,Path.CLOSEPOLY]
    ax.add_patch(mpatches.PathPatch(Path(verts,codes),fc=color,ec="none",alpha=0.62,zorder=1))
# ribbons coloured by ORIGIN (2013–15) quintile — each region keeps its baseline colour to the
# end, so the eye follows where each 2013–15 cohort disperses. Within every block, cohorts are
# stacked in a fixed origin order (o=0..4) so the colour bands stay contiguous across all periods.
Q["o"]=Q[0]
def block_cohort(t):                                 # cc[k,o] = #regions in quintile k at period t, origin o
    cc=np.zeros((NB,NB))
    for (k,o),v in Q.groupby([t,"o"]).size().items(): cc[int(k),int(o)]=v
    return cc
def cohort_base(cc):                                 # y-start of each origin cohort within its block
    blk=cc.sum(axis=1); base={}
    for k in range(NB):
        cum=0.0
        for o in range(NB): base[(k,o)]=yb(k)+bh*cum/blk[k]; cum+=cc[k,o]
    return base,blk
for t in range(len(PER)-1):
    ccs=block_cohort(t); cct=block_cohort(t+1)
    bs,blks=cohort_base(ccs); bt,blkt=cohort_base(cct)
    T=np.zeros((NB,NB,NB))                            # T[o,i,j] origin o, quintile i->j
    for (o,i,j),v in Q.groupby(["o",t,t+1]).size().items(): T[int(o),int(i),int(j)]=v
    x0=t+nodw/2; x1=(t+1)-nodw/2
    soff=dict(bs); toff=dict(bt)                      # running offsets within each (block,cohort) slice
    for o in range(NB):
        for i in range(NB):
            for j in range(NB):
                m=T[o,i,j]
                if m==0: continue
                hs=bh*m/blks[i]; ht=bh*m/blkt[j]
                ys0=soff[(i,o)]; ys1=ys0+hs; soff[(i,o)]=ys1
                yt0=toff[(j,o)]; yt1=yt0+ht; toff[(j,o)]=yt1
                ribbon(x0,x1,ys0,ys1,yt0,yt1,cols[o])
# node bars + labels
for t in range(len(PER)):
    for j in range(NB):
        ax.add_patch(mpatches.Rectangle((t-nodw/2,yb(j)),nodw,bh,fc="#33373b",ec="none",zorder=3))
    ax.text(t,-0.045,PL[t],ha="center",va="top",fontsize=11,fontweight="bold")
qlab=["Q1 (lowest)","Q2","Q3","Q4","Q5 (highest)"]
for j in range(NB):
    ax.text(-0.09,yb(j)+bh/2,qlab[j],ha="right",va="center",fontsize=9.5,color=cols[j] if j!=0 else "#c8922f",fontweight="bold")
ax.text(-0.09,1.09,"Incidence quintile",ha="right",va="center",fontsize=10,fontweight="bold",color="#0d2b45")
ax.text(1.5,1.055,"Ribbon colour = 2013–15 (baseline) quintile — followed through time",ha="center",va="center",fontsize=9.5,style="italic",color="#555")
ax.set_xlim(-0.55,3.25); ax.set_ylim(-0.09,1.03); ax.axis("off")
plt.tight_layout(); plt.savefig("/tmp/fig_alluvial_incidence.png",dpi=300,bbox_inches="tight"); plt.close()
# quantify
d14=(Q[3]-Q[0]).abs()
print(f"regions: {N} | P1->P4: same quintile {(d14==0).mean()*100:.0f}%, within ±1 {(d14<=1).mean()*100:.0f}%, moved ≥2 {(d14>=2).mean()*100:.0f}%")
print("Saved /tmp/fig_alluvial_incidence.png")
