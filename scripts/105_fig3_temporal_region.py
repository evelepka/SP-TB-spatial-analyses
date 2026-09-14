"""Temporal-stability panels (Figure 5; composite in script 122, regionalisation) — 2x2 panels, all outcomes unless noted:
(a) de-noised concentration (% of events in the top 20% of population) per 3-year period;
(b) hotspot Jaccard between consecutive periods; (c) rank autocorrelation across period lags;
(d) ALLUVIAL — regions ranked into INCIDENCE quintiles each 3-year period; ribbons coloured by the
    SOURCE quintile of each step (colour resets each period), showing the transition structure period
    to period (eligible regions, >=10 cases over the decade; quintiles not deciles because ~6
    cases/region per period make finer bins noise-dominated).
Years grouped into 3-year periods to remove year-to-year noise; the de-noised cross-fit
removes the rare-event bias within each period. Reads /tmp/region_cases.csv + /tmp/region_units.csv.
Output: /tmp/fig3_temporal_region.png
"""
import pandas as pd, numpy as np, os, matplotlib, matplotlib.pyplot as plt
from matplotlib.path import Path
import matplotlib.patches as mpatches
from scipy.stats import spearmanr
np.random.seed(20240625); matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
# RANK BASIS: crude is primary (ADR-0006); RANK=std
# for the supplementary robustness version. E_* are full-period expectations from script 100 —
# their scale cancels in a within-period ranking, so the same vector serves every period.
import sys; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from rank_basis import RANK,SUF,rank_base as _rb
reg=pd.read_csv("/tmp/region_units.csv",dtype={"region_id":str})[["region_id","pop","n","ne","E_inc","E_dr","E_ab"]]; reg=reg[reg["pop"]>0]
co=pd.read_csv("/tmp/region_cases.csv",dtype={"region_id":str})
pv=reg.set_index("region_id")["pop"]; units=list(pv.index); idx={u:i for i,u in enumerate(units)}; K=len(units); popv=pv.values; TOT=popv.sum()
co["ri"]=co["region_id"].map(idx); co=co.dropna(subset=["ri"]); co["ri"]=co["ri"].astype(int)

PERIODS=[(2013,2015),(2016,2018),(2019,2021),(2022,2024)]
PLAB=["2013–15","2016–18","2019–21","2022–24"]
OUTC=[("inc",None,"#1a3d5c","Notifications"),("mort","death","#7a0177","Mortality"),("aband","aband","#1f6f8b","LTFU")]
def rank_base(ln): return _rb(reg,ln,popv)

def ri_of(period,coln):
    s=co[co["year"].between(period[0],period[1])]
    if coln is not None: s=s[s[coln]==1]
    return s["ri"].values
def hotspot(cnt,base):
    r=cnt/base; o=np.argsort(-r); cum=np.cumsum(popv[o]); return set(o[cum<=TOT*0.20].tolist())
def denoised_share(ri,base,B=150,q=0.20):
    if len(ri)<50: return np.nan
    s=[]
    for _ in range(B):
        h=np.random.rand(len(ri))<0.5
        a=np.bincount(ri[h],minlength=K).astype(float); b=np.bincount(ri[~h],minlength=K).astype(float)
        for rk,vl in [(a,b),(b,a)]:
            if vl.sum()==0: continue
            ra=rk/base; o=np.argsort(-ra); cp=np.cumsum(popv[o])/TOT; cv=np.cumsum(vl[o])/vl.sum(); s.append(np.interp(q,cp,cv)*100)
    return np.mean(s)

SH={ln:[] for ln,_,_,_ in OUTC}; HS={ln:[] for ln,_,_,_ in OUTC}; RM={ln:[] for ln,_,_,_ in OUTC}
for p in PERIODS:
    for ln,coln,_,_ in OUTC:
        base=rank_base(ln)
        ri=ri_of(p,coln); SH[ln].append(denoised_share(ri,base))
        cnt=np.bincount(ri,minlength=K).astype(float); HS[ln].append(hotspot(cnt,base)); RM[ln].append(cnt/base)
def jac(a,b): return len(a&b)/len(a|b) if (a|b) else np.nan
JAC={ln:[jac(HS[ln][i],HS[ln][i+1]) for i in range(len(PERIODS)-1)] for ln,_,_,_ in OUTC}
AC={ln:[] for ln,_,_,_ in OUTC}
for ln,_,_,_ in OUTC:
    M=np.array(RM[ln])
    for lag in range(1,len(PERIODS)):
        AC[ln].append(np.nanmean([spearmanr(M[i],M[i+lag],nan_policy="omit").correlation for i in range(len(PERIODS)-lag)]))
print(f"[{RANK}] de-noised top-20% share by period:",{ln:[round(x) for x in SH[ln]] for ln,_,_,_ in OUTC})
print(f"[{RANK}] Jaccard between periods:",{ln:[round(x,2) for x in JAC[ln]] for ln,_,_,_ in OUTC})

# ── panel (d) alluvial: incidence-quintile flow; ribbons coloured by the SOURCE quintile of each
#    step (colour RESETS each period — 5 ribbons out of each block).
#    Eligible regions (>=10 cases over the decade). ──
NB=5; rege=reg[reg["n"]>=10].reset_index(drop=True)          # eligible regions for the alluvial
Q=pd.DataFrame(index=rege["region_id"])
qden="E_inc" if RANK=="std" else "pop"   # incidence quintiles: expected (std) or population (crude/percap)                        # quintiles on the same rank basis as (a)-(c)
for i,p in enumerate(PERIODS):
    c=co[co.year.between(*p)].groupby("region_id").size()
    rr=rege.set_index("region_id").assign(c=c).fillna({"c":0})
    Q[i]=pd.qcut((rr["c"]/rr[qden]).reindex(rege["region_id"].values).rank(method="first"),NB,labels=False).values
gap=0.02; bh=(1-(NB-1)*gap)/NB
def yb(j): return j*(bh+gap)
nodw=0.05
qcols=["#fdd9a0","#fdae61","#f46d43","#c0392b","#7a0177"]
def draw_alluvial(ax):
    def ribbon(x0,x1,ys0,ys1,yt0,yt1,color):
        xm=(x0+x1)/2
        verts=[(x0,ys0),(xm,ys0),(xm,yt0),(x1,yt0),(x1,yt1),(xm,yt1),(xm,ys1),(x0,ys1),(x0,ys0)]
        codes=[Path.MOVETO,Path.CURVE4,Path.CURVE4,Path.CURVE4,Path.LINETO,Path.CURVE4,Path.CURVE4,Path.CURVE4,Path.CLOSEPOLY]
        ax.add_patch(mpatches.PathPatch(Path(verts,codes),fc=color,ec="none",alpha=0.62,zorder=1))
    for t in range(len(PERIODS)-1):
        M=np.zeros((NB,NB))                              # aggregate by (source i -> target j): 5 ribbons per block
        for (i,j),v in Q.groupby([t,t+1]).size().items(): M[int(i),int(j)]=v
        ni=M.sum(axis=1); nj=M.sum(axis=0)
        x0=t+nodw/2; x1=(t+1)-nodw/2
        soff={i:yb(i) for i in range(NB)}; toff={j:yb(j) for j in range(NB)}
        for i in range(NB):
            for j in range(NB):
                c=M[i,j]
                if c==0: continue
                hs=bh*c/ni[i]; ht=bh*c/nj[j]
                ys0=soff[i]; ys1=ys0+hs; soff[i]=ys1
                yt0=toff[j]; yt1=yt0+ht; toff[j]=yt1
                ribbon(x0,x1,ys0,ys1,yt0,yt1,qcols[i])
    for t in range(len(PERIODS)):
        for j in range(NB):
            ax.add_patch(mpatches.Rectangle((t-nodw/2,yb(j)),nodw,bh,fc="#33373b",ec="none",zorder=3))
        ax.text(t,-0.075,PLAB[t],ha="center",va="top",fontsize=9,fontweight="bold",clip_on=False)  # bottom margin
    ql=["Q1 (lowest)","Q2","Q3","Q4","Q5 (highest)"]
    for j in range(NB):                                                                             # left margin
        ax.text(-0.10,yb(j)+bh/2,ql[j],ha="right",va="center",fontsize=8.5,color=qcols[j] if j!=0 else "#c8922f",fontweight="bold",clip_on=False)
    ax.text(-0.10,1.075,"Notification-rate quintile",ha="right",va="bottom",fontsize=8.5,fontweight="bold",color="#0d2b45",clip_on=False)
    ax.text(3.0,1.075,"ribbon colour = notification-rate quintile at the start of each step",
            ha="right",va="bottom",fontsize=8.5,style="italic",color="#666",clip_on=False)
    ax.set_xlim(-0.03,3.03); ax.set_ylim(-0.02,1.02); ax.axis("off")   # content fills the cell; labels sit in the margins

# ── 2x2 figure ──
fig,axes=plt.subplots(2,2,figsize=(15.5,11.2))
xp=list(range(len(PERIODS)))
a=axes[0,0]                                             # (a) de-noised concentration per period
for ln,_,col,lab in OUTC: a.plot(xp,SH[ln],"o-",color=col,lw=2.4,ms=7,label=lab)
a.set_xticks(xp); a.set_xticklabels(PLAB,fontsize=9); a.set_ylim(0, max(max(SH[l]) for l in SH)*1.35)
a.set_xlabel("3-year period"); a.set_ylabel("% of events in top 20% of population\n(de-noised, cross-fit)")
a.legend(fontsize=9,title="Outcome"); a.grid(alpha=0.3); a.set_title("(a)",loc="left",fontsize=13,fontweight="bold")
b=axes[0,1]                                             # (b) Jaccard between consecutive periods
tl=[f"{PLAB[i].replace('20','')}→{PLAB[i+1].replace('20','')}" for i in range(len(PERIODS)-1)]; xt=list(range(len(PERIODS)-1))
for ln,_,col,lab in OUTC: b.plot(xt,JAC[ln],"o-",color=col,lw=2.4,ms=7,label=f"{lab} ({np.nanmean(JAC[ln]):.2f})")
b.axhline(0.11,ls="--",color="#999",lw=1.1); b.text(len(xt)-1,0.125,"expected by chance",fontsize=8,color="#777",ha="right")
b.set_xticks(xt); b.set_xticklabels(tl,fontsize=8.5); b.set_ylim(0,1)
b.set_xlabel("Consecutive periods"); b.set_ylabel("Hotspot Jaccard overlap")
b.legend(fontsize=9,title="Outcome (mean)"); b.grid(alpha=0.3); b.set_title("(b)",loc="left",fontsize=13,fontweight="bold")
c=axes[1,0]                                             # (c) autocorrelation by period lag
lags=list(range(1,len(PERIODS)))
for ln,_,col,lab in OUTC: c.plot(lags,AC[ln],"s-",color=col,lw=2.4,ms=7,label=lab)
c.set_xticks(lags); c.set_ylim(0,1); c.set_xlabel("Lag (periods)"); c.set_ylabel("Rank autocorrelation"); c.grid(alpha=0.3)
c.legend(fontsize=9,title="Outcome"); c.set_title("(c)",loc="left",fontsize=13,fontweight="bold")
d=axes[1,1]                                             # (d) alluvial
draw_alluvial(d); d.set_title("(d)",loc="left",fontsize=13,fontweight="bold")
plt.tight_layout(w_pad=2.5,h_pad=3.0)
plt.savefig(f"/tmp/fig3_temporal_region{SUF}.png",dpi=300,bbox_inches="tight"); plt.close()
print(f"Saved /tmp/fig3_temporal_region{SUF}.png")
