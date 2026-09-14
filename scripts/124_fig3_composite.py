"""Manuscript Figure 3, built end-to-end from /tmp/region_units.csv.

The figure previously had NO in-repo builder: the July 8 render survived only inside the
manuscript docx (word/media/image3.png), and the 2026-08-11 "PAF -> Excess fraction" relabel
was done by PATCHING the inset boxes of that old PNG (/tmp/inset_b_new.png et al.), not by
recomputing. This script is now the single source.

(a) Cohen's d (hotspot - rest) for the four deprivation components, by hotspot lens
(b) age-standardised incidence by household-income deprivation quintile + excess vs least-deprived
(c) same for TB mortality

SPEC ARCHAEOLOGY (2026-08-11, vs the manuscript image):
- Panel (a) recovered EXACTLY (12/12 bars to 3 decimals): eligible regions (inc_adj non-null),
  unweighted d = (mean_hs - mean_rest)/sqrt((var_hs + var_rest)/2), population variances,
  raw income sign-flipped. Pop-weighted, log-income, z-scored and pooled-n/overall-SD variants
  all fit worse.
- Panels (b)/(c): quintiles of ADULT population over eligible regions ranked by mean household
  income reproduce all 10 bar heights exactly (34.1/42.8/47.8/61.3/67.3; 1.64/2.09/2.38/2.95/3.41).
  The inset excesses are NOT exactly recoverable: the closest spec (implemented here) is
  excess_q = (rate_q - rate_1)/1e5 * pop_q * T, giving 6,257/9,849/19,641/23,936 cases
  (total 59,683) and 320/529/941/1,276 deaths (total 3,066) vs the manuscript's
  6,294/9,923/19,649/23,920 (59,785) and 316/510/933/1,294 (3,054) — within 0.2%/0.4% on
  totals, <=0.8% (inc) / <=3.7% (mort) per bar. The 122-style SIR excess (n_q - E_q*SIR_1)
  fits worse (60,264 / 2,945) and is printed as a sensitivity. Also rejected: age-stratified
  Q1-reference, direct standardisation, crude reference, fractional/left/mid quintile
  boundaries, per-lens eligibility, alternative income aggregations, region-count quintiles.
  DO NOT silently update the manuscript numbers to this script's output — the delta is
  documented in docs/dead-ends.md and needs an author decision.
Output: /tmp/fig3_composite.png
"""
import pandas as pd, numpy as np, matplotlib, matplotlib.pyplot as plt
np.random.seed(20240625); matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
T=12; B=500

reg=pd.read_csv("/tmp/region_units.csv",dtype={"region_id":str})
import os,sys; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from rank_basis import RANK,SUF
el=reg.dropna(subset=["inc_adj"]).copy()          # eligible regions (n>=10, E>0) — all panels

# ---------------- panel (a): Cohen's d, hotspot - rest ----------------
VARS=[("Low income","income",-1),("% favela","favela",1),("Illiteracy","illit",1),("Residents/hh","residents",1)]
LENS=[("Notifications","hs_inc","#1a3d5c"),("Mortality","hs_mort","#7a0177"),("LTFU","hs_aband","#1f6f8b")]
ea=el.dropna(subset=[v for _,v,_ in VARS])
def cohend(x,h):                                   # avg-of-variances denominator, ddof=0
    m1,m0=x[h].mean(),x[~h].mean(); v1,v0=x[h].var(ddof=0),x[~h].var(ddof=0)
    return (m1-m0)/np.sqrt((v1+v0)/2)
D={}
for lab,hs,_ in LENS:
    D[lab]=[sg*cohend(ea[v].values,ea[hs].values.astype(bool)) for _,v,sg in VARS]
    print(f"(a) {lab:10s} d = "+"  ".join(f"{x:5.3f}" for x in D[lab]))

# ---------------- panels (b)/(c): income-deprivation quintiles ----------------
# quintiles of adult population, regions ranked least- -> most-deprived (income descending)
def quintiles(d):
    d=d.sort_values("income",ascending=False).copy()
    cum=d["pop"].cumsum()/d["pop"].sum(); d["q"]=np.minimum((cum*5).astype(int),4)
    return d
def panel(d,ncol,Ecol):
    g=d.groupby("q").agg(n=(ncol,"sum"),E=(Ecol,"sum"),pop=("pop","sum"))
    state=reg[ncol].sum()/(reg["pop"].sum()*T)*1e5
    if RANK=="std": g["rate"]=g["n"]/g["E"]*state                  # indirectly standardised
    else:           g["rate"]=g["n"]/(g["pop"]*T)*1e5              # crude (ADR-0006)
    g["excess"]=(g["rate"]-g.loc[0,"rate"])/1e5*g["pop"]*T         # rate difference x person-years
    return g
def ef_of(g): return g["excess"][1:].sum()/g["n"].sum()*100
eq=quintiles(el.dropna(subset=["income"]))
gB=panel(eq,"n","E_inc"); gC=panel(eq,"nd","E_dr")
ci={}
for key,ncol,Ecol in [("b","n","E_inc"),("c","nd","E_dr")]:
    bs=[ef_of(panel(quintiles(eq.sample(len(eq),replace=True)),ncol,Ecol)) for _ in range(B)]
    ci[key]=np.percentile(bs,[2.5,97.5])
for key,g,unit in [("b",gB,"cases"),("c",gC,"deaths")]:
    lo,hi=ci[key]
    print(f"({key}) rates "+"/".join(f"{r:.2f}" for r in g["rate"])+"  excess "
          +"/".join(f"{e:,.0f}" for e in g["excess"][1:])
          +f"  total {g['excess'][1:].sum():,.0f} {unit}  EF {ef_of(g):.1f}% (95% CI {lo:.0f}-{hi:.0f})")

# validation against the manuscript image (docx word/media/image3.png, numbers of 2026-07-08)
MS={"b_exc":[6294,9923,19649,23920],"b_tot":59785,"c_exc":[316,510,933,1294],"c_tot":3054}
dev_b=max(abs(e-m)/m for e,m in zip(gB["excess"][1:],MS["b_exc"]))
dev_c=max(abs(e-m)/m for e,m in zip(gC["excess"][1:],MS["c_exc"]))
print(f"vs manuscript insets: totals {gB['excess'][1:].sum():,.0f} vs {MS['b_tot']:,} and "
      f"{gC['excess'][1:].sum():,.0f} vs {MS['c_tot']:,}; max per-bar dev {dev_b:.1%} / {dev_c:.1%}")
print("FLAG: manuscript inset excesses are from the lost 2026-07-08 spec — closest, not exact"
      " (see header + docs/dead-ends.md)" if dev_b>0.005 or dev_c>0.005 else "insets reproduced exactly")
# sensitivity: 122-style SIR excess (reference = least-deprived quintile's SIR)
for lab,g in [("inc",gB),("mort",gC)]:
    sir=g["n"]-g["E"]*(g.loc[0,"n"]/g.loc[0,"E"])
    print(f"    sensitivity SIR-excess {lab}: "+"/".join(f"{e:,.0f}" for e in sir[1:])
          +f"  total {sir[1:].sum():,.0f}")

# ---------------- figure ----------------
fig,(axA,axB,axC)=plt.subplots(1,3,figsize=(16.2,4.7))
x=np.arange(len(VARS)); w=0.26
for k,(lab,hs,col) in enumerate(LENS):
    axA.bar(x+(k-1)*w,D[lab],w,color=col,label=lab)
axA.set_xticks(x); axA.set_xticklabels([v for v,_,_ in VARS])
axA.set_ylabel("Standardized difference (Cohen's d)\nhotspot − rest")
axA.legend(title="Hotspot type",fontsize=9.5,title_fontsize=10,frameon=False)
axA.grid(alpha=0.3,axis="y"); axA.set_axisbelow(True)
axA.set_title("(a)",loc="left",fontsize=13,fontweight="bold")
for ax,g,col,unit,ymax,off,ttl in [(axB,gB,"#1a3d5c","cases",85,2.5,"(b)  Notifications"),
                                   (axC,gC,"#7a0177","deaths",4.25,0.12,"(c)  Mortality")]:
    ax.bar(range(1,6),g["rate"],color=col,width=0.62)
    for i,(r,e) in enumerate(zip(g["rate"],g["excess"])):
        if i>0: ax.text(i+1,r+off,f"+{e:,.0f}",ha="center",fontsize=9)
    ax.axhline(g.loc[0,"rate"],ls="--",color="#333",lw=1.1)
    ax.text(5.45,g.loc[0,"rate"],"reference\n(least-deprived)",fontsize=8,color="#555",va="center")
    lo,hi=ci["b" if unit=="cases" else "c"]; ef=ef_of(g)
    ax.text(0.03,0.97,f"Excess fraction = {ef:.0f}%  (95% CI {lo:.0f}–{hi:.0f})\n"
            f"excess {unit}: {g['excess'][1:].sum():,.0f}",transform=ax.transAxes,va="top",
            fontsize=10,bbox=dict(boxstyle="round",fc="white",ec="#aaa"))
    ax.set_xticks(range(1,6)); ax.set_ylim(0,ymax)
    if unit=="deaths": ax.set_yticks(range(0,5))
    ax.set_xlabel("Household-income deprivation quintile\n(1 = least → 5 = most)")
    ax.set_ylabel("Age-standardised rate per 100,000/yr")
    ax.grid(alpha=0.3,axis="y"); ax.set_axisbelow(True)
    ax.set_title(ttl,loc="left",fontsize=13,fontweight="bold")
for ax in (axA,axB,axC):
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
plt.tight_layout(); plt.savefig(f"/tmp/fig3_composite{SUF}.png",dpi=300,bbox_inches="tight"); plt.close()
print(f"Saved /tmp/fig3_composite{SUF}.png")
