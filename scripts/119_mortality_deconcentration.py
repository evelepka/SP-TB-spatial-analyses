"""EXPLORATORY — mortality de-concentration over the decade (KEPT OUT of the manuscript for now,
advisor decision 2026-07-07: "not top-5, keep out for now, add later if we need more"; case-fatality
is not one of the paper's three defined outcomes, so including it would expand scope + need a Methods
definition). This script preserves the full analysis so it can be reinstated quickly if wanted:

  Finding: mortality CONCENTRATION (de-noised top-20%-population share of deaths) fell ~38%→33% over
  2013–24, onset in the 2019–21 (COVID) period; incidence and LTFU concentration stayed flat.
  Decomposition (mortality rate = incidence x case-fatality): incidence stayed concentrated, so the
  driver is case-fatality. Stratifying by the STABLE incidence-hotspot set (NOT by the noisy mortality
  rate, which would regress to the mean), case-fatality rose in the lower-incidence regions
  (4.4%->5.1%, +0.6 pts, 95% CI 0.3–1.0) and was flat in the hotspots; the gap-closing difference-in-
  differences was NOT conclusive (CI includes 0). SIM-linkage artifact ruled out (single retrospective
  linkage, uniform over time).

Reads /tmp/region_units.csv + /tmp/region_cases.csv. Print-only.
"""
import pandas as pd, numpy as np
from scipy.stats import spearmanr
rng=np.random.default_rng(20240707)
ru=pd.read_csv("/tmp/region_units.csv",dtype={"region_id":str}); ru["hs_inc"]=ru["hs_inc"].fillna(0).astype(int)
reg=ru[ru["pop"]>0]
pv=reg.set_index("region_id")["pop"]; units=list(pv.index); idx={u:i for i,u in enumerate(units)}
K=len(units); popv=pv.values; TOT=popv.sum()
inHi=reg.set_index("region_id")["hs_inc"].reindex(units).fillna(0).astype(bool).values
co=pd.read_csv("/tmp/region_cases.csv",dtype={"region_id":str})
co["ri"]=co["region_id"].map(idx); co=co.dropna(subset=["ri"]); co["ri"]=co["ri"].astype(int)
PER=[(2013,2015),(2016,2018),(2019,2021),(2022,2024)]; PL=["2013-15","2016-18","2019-21","2022-24"]; Y=3

def deaths_ri(p): s=co[co.year.between(*p)]; return s[s["death"]==1]["ri"].values
def cnt(p,coln=None):
    s=co[co.year.between(*p)]; s=s[s[coln]==1] if coln else s
    return np.bincount(s["ri"].values,minlength=K).astype(float)

# ── 1) mortality concentration per period (de-noised) + subsampling significance ──
def dshare_once(ri,q=0.20):
    h=rng.random(len(ri))<0.5; a=np.bincount(ri[h],minlength=K).astype(float); b=np.bincount(ri[~h],minlength=K).astype(float); s=[]
    for rk,vl in [(a,b),(b,a)]:
        if vl.sum()==0: continue
        o=np.argsort(-rk/popv); cp=np.cumsum(popv[o])/TOT; cv=np.cumsum(vl[o])/vl.sum(); s.append(np.interp(q,cp,cv)*100)
    return np.mean(s)
def dshare(ri,B=80): return np.mean([dshare_once(ri) for _ in range(B)])
RI=[deaths_ri(p) for p in PER]; pts=[dshare(r) for r in RI]
print("1) de-noised mortality concentration (top-20% share) by period:",[round(x,1) for x in pts])
SE=[]
for r in RI:
    n=len(r); m=n//2; sub=[dshare(r[rng.permutation(n)[:m]],40) for _ in range(250)]
    SE.append(np.std(sub)*np.sqrt(m/n))   # subsample -> full-sample SE (no replacement: keeps cross-fit valid)
diff=pts[0]-pts[3]; sed=np.sqrt(SE[0]**2+SE[3]**2)
print(f"   P1-P4 = {diff:.1f} pts, z = {diff/sed:.1f}  ({'real p<0.05' if abs(diff/sed)>1.96 else 'n.s.'})")

# ── 2) decomposition by STABLE incidence-hotspot stratum: mortality rate + case-fatality (CFR) ──
print("\n2) by incidence-hotspot stratum (stable) — mortality rate /100k/yr, and case-fatality % (95% CI):")
print("   period  | mort HS | mort rest | CFR HS (CI)      | CFR rest (CI)     | deaths")
def cfr_ci(p,hs,B=2000):
    s=co[co.year.between(*p)]; x=s[s["ri"].isin(np.where(inHi==(hs==1))[0])]["death"].values.astype(float)
    m=x.mean()*100; bs=np.array([x[rng.integers(0,len(x),len(x))].mean()*100 for _ in range(B)])
    return m,bs
BS={}
for i,p in enumerate(PER):
    dd=cnt(p,"death"); cc=cnt(p,None)
    mr_h=dd[inHi].sum()/popv[inHi].sum()/Y*1e5; mr_r=dd[~inHi].sum()/popv[~inHi].sum()/Y*1e5
    (mh,bh)=cfr_ci(p,1); (mr,br)=cfr_ci(p,0); BS[i]=(bh,br)
    lh,hh=np.percentile(bh,[2.5,97.5]); lr,hr=np.percentile(br,[2.5,97.5])
    print(f"   {PL[i]} | {mr_h:5.1f}   | {mr_r:5.1f}     | {mh:.1f} ({lh:.1f}-{hh:.1f}) | {mr:.1f} ({lr:.1f}-{hr:.1f}) | {int(dd.sum()):,}")
dR=BS[3][1]-BS[0][1]; lo,hi=np.percentile(dR,[2.5,97.5])
print(f"   CFR rest P4-P1 = {dR.mean():+.1f} pts [{lo:+.1f},{hi:+.1f}]  ({'real' if lo>0 else 'n.s.'})")
dGap=(BS[3][1]-BS[3][0])-(BS[0][1]-BS[0][0]); lo,hi=np.percentile(dGap,[2.5,97.5])
print(f"   gap(rest-HS) DiD P4-P1 = {dGap.mean():+.1f} pts [{lo:+.1f},{hi:+.1f}]  ({'converged' if hi<0 else 'NOT conclusive'})")
