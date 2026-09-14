"""Manuscript Figure 5 (regionalisation): scatter + population-weighted GAM, rows = vulnerability
indicators (household income, % favela, adult illiteracy, residents/household — NO density),
cols = TB indicators (incidence [log-y], TB-mortality rate, loss to follow-up %). Regions (>=10 cases);
rate basis set by rank_basis.py (crude by default). Reads /tmp/region_units.csv. Output: /tmp/fig5_gam_region.png
"""
import pandas as pd, numpy as np, matplotlib, matplotlib.pyplot as plt
from pygam import LinearGAM, s
from matplotlib.ticker import ScalarFormatter, NullFormatter
np.random.seed(20240625); matplotlib.rcParams.update({"font.family":"sans-serif","font.size":10})
d=pd.read_csv("/tmp/region_units.csv")
PRED=[("income","Household income (R$, log)",True),
      ("illit","Adult illiteracy (%)",False),
      ("residents","Residents per household",False),
      ("vuln","Vulnerability index (composite)",False)]
# favela dropped from the GAM: on the regionalisation it is BINARY (regions are favela or
# non-favela, grown separately), so a scatter+GAM is meaningless. Favela's effect is reported
# in Figure 4 (standardized difference by hotspot type) — the right form for a binary variable.
import os,sys; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from rank_basis import RANK,SUF,RATE
OUT=[(RATE["inc"],"TB notification rate /100k/yr (log)","log"),
     (RATE["mort"],"TB-mortality rate /100k/yr",None),
     (RATE["aband"],"LTFU %",None)]
fig,axes=plt.subplots(len(PRED),len(OUT),figsize=(12,13))
for i,(pk,plab,logx) in enumerate(PRED):
    for j,(ok,olab,yscale) in enumerate(OUT):
        ax=axes[i,j]
        sub=d.dropna(subset=[pk,ok,"pop"]); sub=sub[sub[pk]>0] if logx else sub
        xv=sub[pk].values; y=sub[ok].values; w=sub["pop"].values; xf=np.log10(xv) if logx else xv
        ax.scatter(xv,y,s=8,c="#1f6f8b",alpha=0.15,edgecolors="none")
        # low-complexity smooth (n_splines capped) to avoid overfitting
        gam=LinearGAM(s(0,n_splines=4,lam=10)).fit(xf.reshape(-1,1),y,weights=w)
        if logx:
            xxv=np.logspace(np.log10(np.percentile(xv,1)),np.log10(np.percentile(xv,99)),120); xxf=np.log10(xxv)
        else:
            xxv=np.linspace(np.percentile(xv,1),np.percentile(xv,99),120); xxf=xxv
        mu=gam.predict(xxf.reshape(-1,1)); ci=gam.confidence_intervals(xxf.reshape(-1,1),width=.95); lo,hi=ci[:,0],ci[:,1]
        if yscale=="log": mu=np.clip(mu,0.5,None); lo=np.clip(lo,0.5,None)
        ax.fill_between(xxv,lo,hi,color="#c0392b",alpha=0.18); ax.plot(xxv,mu,color="#c0392b",lw=2.3)
        if logx: ax.set_xscale("log")
        if yscale=="log": ax.set_yscale("log"); ax.set_ylim(max(1,np.percentile(y[y>0],1)*0.8),np.percentile(y,99.5)*1.1); ax.yaxis.set_major_formatter(ScalarFormatter()); ax.yaxis.set_minor_formatter(NullFormatter())
        else: ax.set_ylim(0,np.percentile(y,99)*1.05)
        ax.grid(alpha=0.25,which="both"); ax.set_xlabel(plab,fontsize=8.5)
        if j==0: ax.set_ylabel(olab,fontsize=9)
        if i==0: ax.set_title(olab,fontsize=10.5,fontweight="bold",color="#0d2b45")
plt.tight_layout(rect=[0,0,1,0.99]); plt.savefig(f"/tmp/fig5_gam_region{SUF}.png",dpi=300,bbox_inches="tight"); plt.savefig(f"/tmp/fig5_gam_region{SUF}.pdf",bbox_inches="tight"); plt.close()
print(f"Saved /tmp/fig5_gam_region{SUF}.png  (regions used:",len(d.dropna(subset=[RATE["inc"]])),")")
