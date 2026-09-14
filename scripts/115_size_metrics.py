"""Print the headline findings from the CURRENT /tmp/region_units.csv + region_cases.csv,
for the region-size sensitivity analysis. Usage: python3 115_size_metrics.py <label>
"""
import sys, pandas as pd, numpy as np
np.random.seed(20240625)
lab=sys.argv[1] if len(sys.argv)>1 else "?"
d=pd.read_csv("/tmp/region_units.csv",dtype={"region_id":str})
c=pd.read_csv("/tmp/region_cases.csv",dtype={"region_id":str})
pop=d.set_index("region_id")["pop"]; units=list(pop.index); idx={u:i for i,u in enumerate(units)}; K=len(units); popv=pop.values
def dtop20(col=None,B=80):
    sub=c if col is None else c[c[col]==1]
    ix=sub["region_id"].map(idx).dropna().astype(int).values; s=[]
    for _ in range(B):
        h=np.random.rand(len(ix))<0.5; a=np.bincount(ix[h],minlength=K).astype(float); b=np.bincount(ix[~h],minlength=K).astype(float)
        for rk,vl in [(a,b),(b,a)]:
            if vl.sum()==0: continue
            ra=rk/popv; o=np.argsort(-ra); cp=np.cumsum(popv[o])/popv.sum(); cv=np.cumsum(vl[o])/vl.sum(); s.append(np.interp(0.20,cp,cv)*100)
    return np.mean(s)
el=d[d["n"]>=10]
def cohend(col,flag):
    a=el.loc[el[flag],col].dropna(); bb=el.loc[~el[flag],col].dropna()
    sp=np.sqrt((a.var()+bb.var())/2); return (a.mean()-bb.mean())/sp if sp>0 else np.nan
print(f"{lab:>6} | regions {len(d):>5} | elig {int((d['n']>=10).sum()):>5} | medpop {int(pop.median()):>5} | "
      f"inc/100k {c.shape[0]/pop.sum()*1e5/12:5.1f} | top20 inc {dtop20():2.0f}% mort {dtop20('death'):2.0f}% aband {dtop20('aband'):2.0f}% | "
      f"income-d(HSvsNon) {cohend('income','hs_inc'):+.2f} | vuln-d {cohend('vuln','hs_inc'):+.2f}")
