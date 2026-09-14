"""Area-proportional Euler diagram of the overlap of top-20% hotspot units across FOUR
lenses — incidence, TB mortality (rate), treatment abandonment, and the vulnerability index
(case-fatality removed per advisor). Circle areas and overlaps are scaled to the actual unit
counts (R eulerr; matplotlib-venn only scales 2-3 sets). Python computes the region counts
and shells out to Rscript. Output: /tmp/fig_hotspot_euler.png
"""
import pandas as pd, numpy as np, subprocess, json
from collections import Counter

u=pd.read_csv("/tmp/outcome_units.csv")
asr=pd.read_csv("/tmp/unit_age_standardised.csv")[["unit_id","drate_adj"]]; u=u.merge(asr,on="unit_id",how="left")
vf=pd.read_csv("/tmp/vuln_final.csv",dtype={"CD_SETOR":str})
vu=vf.groupby("unit_id").apply(lambda d:np.average(d["vuln_final"],weights=d["pop15"])).rename("vuln")
u=u.merge(vu,on="unit_id",how="left")
elig=u[(u["n_cases"]>=10)&(u["n_eval"]>=10)].dropna(subset=["rate","drate_adj","aband_pct","vuln"]).copy()
TOT=elig["pop"].sum()
def hs(col):
    d=elig.sort_values(col,ascending=False); cum=d["pop"].cumsum(); m=cum<=TOT*0.20
    if m.sum()<len(d): m.iloc[m.sum()]=True
    return set(d[m]["unit_id"])
L={"Incidence":hs("rate"),"Mortality":hs("drate_adj"),"Abandonment":hs("aband_pct"),"Vulnerability":hs("vuln")}
keys=list(L); allu=set().union(*L.values())
reg=Counter()
for x in allu:
    reg["&".join(k for k in keys if x in L[k])]+=1
print("set sizes:",{k:len(v) for k,v in L.items()})
print("regions:",dict(reg))

combo="c(\n"+",\n".join(f'  "{k}" = {v}' for k,v in reg.items())+"\n)"
R=f'''
suppressMessages(library(eulerr))
set.seed(7)
combo <- {combo}
fit <- euler(combo, shape="ellipse")
cat("diagError:", fit$diagError, " stress:", fit$stress, "\\n")
png("/tmp/fig_hotspot_euler.png", width=2100, height=1750, res=200)
plot(fit,
     quantities=list(type="counts", fontsize=13),
     fills=list(fill=c("#1a3d5c","#7a0177","#1f6f8b","#b8860b"), alpha=0.50),
     edges=list(col="grey30", lwd=1.5),
     labels=list(fontsize=15, font=2),
     main=list(label="Hotspot-unit overlap across four lenses (area-proportional)", fontsize=13))
invisible(dev.off())
'''
open("/tmp/_hotspot_euler.R","w").write(R)
out=subprocess.run(["Rscript","/tmp/_hotspot_euler.R"],capture_output=True,text=True)
print(out.stdout.strip()); print(out.stderr.strip()[-400:] if out.stderr else "")
print("Saved /tmp/fig_hotspot_euler.png")
