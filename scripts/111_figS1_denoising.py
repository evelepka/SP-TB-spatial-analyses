"""Supplementary Figure S1 (regionalisation): the de-noising bias correction. For each outcome,
the NAIVE concentration (dashed) overstates the true clustering — most for the rarer events
(TB mortality, loss to follow-up) — because finite-sample noise inflates the naive Gini/share;
the split-sample cross-fit de-noised estimate (solid) removes that bias. This justifies reporting
the de-noised values throughout the main text (Figures 1 and 3). Output: /tmp/figS1_denoising.png
"""
import pandas as pd, numpy as np, matplotlib, matplotlib.pyplot as plt
np.random.seed(20240625); matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
import os,sys; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from rank_basis import RANK,SUF,rank_base
reg=pd.read_csv("/tmp/region_units.csv",dtype={"region_id":str})[["region_id","pop","ne","E_inc","E_dr","E_ab"]]
co=pd.read_csv("/tmp/region_cases.csv",dtype={"region_id":str})
pv=reg.set_index("region_id")["pop"]; units=list(pv.index); idx={u:i for i,u in enumerate(units)}; K=len(units); popv=pv.values
def counts(mask):
    a=co[mask]["region_id"].map(idx).dropna().astype(int).values; return np.bincount(a,minlength=K).astype(float)
def naive_share(c,q,base):
    r=c/np.where(base>0,base,np.inf); o=np.argsort(-r); cp=np.cumsum(popv[o])/popv.sum(); cv=np.cumsum(c[o])/c.sum(); return np.interp(q,cp,cv)*100
def deno_share(mask,q,base,B=200):
    ix=co[mask]["region_id"].map(idx).dropna().astype(int).values; s=[]
    for _ in range(B):
        h=np.random.rand(len(ix))<0.5; a=np.bincount(ix[h],minlength=K).astype(float); b=np.bincount(ix[~h],minlength=K).astype(float)
        for rk,vl in [(a,b),(b,a)]:
            if vl.sum()==0: continue
            ra=rk/np.where(base>0,base,np.inf); o=np.argsort(-ra); cp=np.cumsum(popv[o])/popv.sum(); cv=np.cumsum(vl[o])/vl.sum(); s.append(np.interp(q,cp,cv)*100)
    return np.mean(s)
LENS=[("TB notifications",co["age"]>=15,"#1a3d5c","inc"),("TB mortality",co["death"]==1,"#7a0177","mort"),("LTFU",(co["aband"]==1)&(co["eval"]==1),"#1f6f8b","aband")]
QS=[0.05,0.10,0.20,0.40]; xq=[q*100 for q in QS]
fig,ax=plt.subplots(figsize=(8.4,6.0))
ax.plot([0,40],[0,40],":",color="#bbb",lw=1.1,label="proportional (no concentration)")
for lab,mask,col,ln in LENS:
    c=counts(mask); base=rank_base(reg,ln,popv)
    nv=[naive_share(c,q,base) for q in QS]; dv=[deno_share(mask,q,base) for q in QS]
    ax.plot(xq,nv,"--",color=col,lw=1.6,alpha=0.6,zorder=2)
    ax.plot(xq,dv,"-o",color=col,lw=2.5,ms=6,label=lab,zorder=3)
    print(f"  {lab:22s} top-20%  naive {nv[2]:.0f}%  ->  de-noised {dv[2]:.0f}%")
ax.set_xticks(xq); ax.set_xlabel("% of population in highest-rate regions")
ax.set_ylabel("% of events concentrated there"); ax.set_ylim(0,None); ax.grid(alpha=0.3)
from matplotlib.lines import Line2D
h=[Line2D([0],[0],color=c,lw=2.5,marker="o",label=l) for l,_,c,_ in LENS]
h+=[Line2D([0],[0],color="#888",lw=2.5,ls="-",label="de-noised (cross-fit)"),Line2D([0],[0],color="#888",lw=1.6,ls="--",label="naïve (uncorrected)")]
ax.legend(handles=h,fontsize=9,loc="upper left")
plt.tight_layout(); plt.savefig(f"/tmp/figS1_denoising{SUF}.png",dpi=300,bbox_inches="tight"); plt.close()
print("Saved /tmp/figS1_denoising.png")
