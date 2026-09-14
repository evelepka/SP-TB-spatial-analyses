"""Manuscript Figure 1 (regionalisation), ALL DE-NOISED (split-sample cross-fit; the naive-vs-
de-noised comparison is Supplementary Figure S1, script 111). (a) De-noised concentration curves of
the three outcomes (TB incidence, TB mortality, loss to follow-up) — cumulative events vs
cumulative adult population, highest-rate regions first so the curves fall above the diagonal;
de-noised Gini in the legend. (b) De-noised % of events in the 5 / 10 / 20 / 40% of the population
living in the highest-rate regions. Output: /tmp/fig1_concentration_region.png
"""
import pandas as pd, numpy as np, re, os, matplotlib, matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from venn import venn
np.random.seed(20240625); matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/DATA_ROOT/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD="/DATA_ROOT/Abandonment Outcomes/Abandonment Paper/Banco de dados"
# RANK BASIS (decision Jason 2026-08-11): regions are ranked by AGE-STANDARDIZED rate
# (observed/expected, expectations E_inc/E_dr/E_ab from script 100 — indirect standardisation,
# State reference) in the primary analysis; RANK=crude reproduces the crude ranking for the
# supplementary robustness figure. Events accumulated are always ACTUAL events.
import sys; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from rank_basis import RANK,SUF,rank_base
reg=pd.read_csv("/tmp/region_units.csv",dtype={"region_id":str})[["region_id","pop","ne","E_inc","E_dr","E_ab"]]
# authoritative case-level analytic table (region assigned; Novo+Recidiva, deduped, spatial overlay + CEP) — scripts 108/109/100
co=pd.read_csv("/tmp/region_cases.csv",dtype={"region_id":str})

pv=reg.set_index("region_id")["pop"]; units=list(pv.index); idx={u:i for i,u in enumerate(units)}; K=len(units); popv=pv.values
EXP={"TB notifications":rank_base(reg,"inc",popv),"TB mortality":rank_base(reg,"mort",popv),"LTFU":rank_base(reg,"aband",popv)}
def counts(mask):
    a=co[mask]["region_id"].map(idx).dropna().astype(int).values; return np.bincount(a,minlength=K).astype(float)
GRID=np.linspace(0,1,101)
def denoised_curve(mask,expv,B=200):
    # out-of-sample (split-sample cross-fit) concentration curve: rank regions on one half and
    # accumulate the OTHER half's events -> removes the finite-sample bias that inflates the naive Gini
    ix=co[mask]["region_id"].map(idx).dropna().astype(int).values; acc=np.zeros(len(GRID)); m=0
    base=expv   # rank denominator from rank_basis.rank_base (crude: pop / evaluated; std: expected events)
    for _ in range(B):
        h=np.random.rand(len(ix))<0.5; a=np.bincount(ix[h],minlength=K).astype(float); b=np.bincount(ix[~h],minlength=K).astype(float)
        for rk,vl in [(a,b),(b,a)]:
            if vl.sum()==0: continue
            ra=rk/base; o=np.argsort(-ra); cp=np.cumsum(popv[o])/popv.sum(); cv=np.cumsum(vl[o])/vl.sum()
            acc+=np.interp(GRID,cp,cv); m+=1
    return acc/m
def smooth_monotone(c):
    # shape-preserving monotone smoothing of the DISPLAYED curve: PCHIP through anchor points that
    # INCLUDE the reported thresholds (5/10/20/40% of pop), so the curve passes exactly through the
    # reported numbers (Gini + shares unchanged) while the rare-event "kink" between them is removed.
    from scipy.interpolate import PchipInterpolator
    anchors=np.array([0,.05,.10,.15,.20,.30,.40,.55,.70,.85,1.0])
    yv=np.maximum.accumulate(np.interp(anchors,GRID,c)); yv[0]=0.0; yv[-1]=1.0
    return np.clip(PchipInterpolator(anchors,yv)(GRID),0,1)
LENS=[("TB notifications",co["age"]>=15,"#1a3d5c"),("TB mortality",co["death"]==1,"#7a0177"),("LTFU",co["aband"]==1,"#1f6f8b")]
QS=[0.05,0.10,0.20,0.40]
res=[]
for lab,mask,col in LENS:
    curve=smooth_monotone(denoised_curve(mask,EXP[lab])); dg=2*np.trapz(curve,GRID)-1
    deno=[float(np.interp(q,GRID,curve))*100 for q in QS]
    res.append((lab,deno,curve,dg,col))
    print(f"  [{RANK}] {lab:22s} de-noised 5/10/20/40% pop -> {'/'.join(f'{x:.0f}' for x in deno)}% events  (de-noised Gini {dg:.2f})")
fig,(axA,axB,axC)=plt.subplots(1,3,figsize=(20.5,6.2),gridspec_kw={"width_ratios":[1,1,1.32]})
# (a) de-noised concentration curve — highest-rate regions first, curves fall ABOVE the diagonal
axA.plot([0,1],[0,1],"--",color="#999",lw=1.2,label="equality (no concentration)")
for lab,deno,curve,dg,col in res: axA.plot(GRID,curve,color=col,lw=2.6,label=f"{lab} (Gini {dg:.2f})")
axA.set_xlabel("Cumulative share of adult population\n(highest-rate regions first)"); axA.set_ylabel("Cumulative share of events")
axA.set_title("(a)",loc="left",fontsize=13,fontweight="bold")
axA.legend(fontsize=9.5,loc="lower right"); axA.grid(alpha=0.3); axA.set_xlim(0,1); axA.set_ylim(0,1)
# (b) de-noised % of events concentrated at 5/10/20/40% of population
xq=[q*100 for q in QS]
axB.plot([0,40],[0,40],":",color="#bbb",lw=1.1,zorder=1,label="proportional (no concentration)")
for lab,deno,curve,dg,col in res: axB.plot(xq,deno,"-o",color=col,lw=2.5,ms=6,label=lab,zorder=3)
axB.set_xticks(xq); axB.set_xlabel("% of population in highest-rate regions")
axB.set_ylabel("% of events concentrated there"); axB.set_ylim(0,None); axB.grid(alpha=0.3)
axB.set_title("(b)",loc="left",fontsize=13,fontweight="bold")
axB.legend(fontsize=9,loc="upper left")
# (c) 4-set Venn of the top-20% hotspot REGIONS across the three outcomes + the vulnerability lens
dv=pd.read_csv("/tmp/region_units.csv")
VL={"Notifications":set(dv[dv["hs_inc"]]["region_id"]),"Mortality":set(dv[dv["hs_mort"]]["region_id"]),
    "LTFU":set(dv[dv["hs_aband"]]["region_id"]),"Vulnerability":set(dv[dv["hs_vuln"]]["region_id"])}
venn(VL,ax=axC,fontsize=9,legend_loc="upper left",cmap=ListedColormap(["#1a3d5c","#7a0177","#1f6f8b","#b8860b"]))
# the venn library forces equal aspect (a ~1x1 square) → in a row it looks smaller than (a)/(b).
# Drop the equal aspect and crop the vertical whitespace so the diagram fills the panel.
axC.set_aspect("auto"); axC.set_xlim(-0.02,1.02); axC.set_ylim(0.06,0.94)
axC.set_title("(c)",loc="left",fontsize=13,fontweight="bold")
plt.tight_layout(); plt.savefig(f"/tmp/fig1_concentration_region{SUF}.png",dpi=300,bbox_inches="tight"); plt.close()
print(f"Saved /tmp/fig1_concentration_region{SUF}.png")
