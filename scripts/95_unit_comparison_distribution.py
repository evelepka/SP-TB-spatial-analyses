"""Side-by-side distribution of the TWO candidate spatial units, on a shared axis, so the
contrast is immediate: the PRIMARY operational unit (official hybrid — FCU/bairro/district,
n=3,014) is deliberately heterogeneous (capital collapses to large districts), whereas the
REGIONALISATION (sectors grown to ~5,000 adults, income-homogeneous, favela separate,
n=7,310) is uniform by construction. Output: /tmp/fig_unit_comparison_distribution.png
"""
import pandas as pd, numpy as np, matplotlib, matplotlib.pyplot as plt
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})

vs=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)
vs=vs[vs["pop15"]>0].copy()
vs["cap"]=vs["CD_MUN"].astype(str).eq("3550308")
# operational unit pops
op=vs.groupby("unit_id").agg(pop=("pop15","sum"),cap=("cap","first")).reset_index()
# regionalisation unit pops
rg=pd.read_csv("/tmp/regions_sectors.csv",dtype={"CD_SETOR":str})[["CD_SETOR","region_id"]]
rgp=vs.merge(rg,on="CD_SETOR",how="inner").groupby("region_id")["pop15"].sum()
print(f"operational  n={len(op):,}  median {op['pop'].median():,.0f}  IQR [{op['pop'].quantile(.25):,.0f}, {op['pop'].quantile(.75):,.0f}]  range [{op['pop'].min():,.0f}, {op['pop'].max():,.0f}]")
print(f"regionalis.  n={len(rgp):,}  median {rgp.median():,.0f}  IQR [{rgp.quantile(.25):,.0f}, {rgp.quantile(.75):,.0f}]  range [{rgp.min():,.0f}, {rgp.max():,.0f}]")

bins=np.logspace(np.log10(50),np.log10(700000),46)
fig,(axA,axB)=plt.subplots(1,2,figsize=(14.5,5.4),sharex=True,sharey=True)
# A: operational
axA.hist(op[~op["cap"]]["pop"],bins=bins,color="#1f6f8b",alpha=0.85,label=f"interior + other metros (n={(~op['cap']).sum():,})")
axA.hist(op[op["cap"]]["pop"],bins=bins,color="#c0392b",alpha=0.8,label=f"capital — São Paulo city (n={op['cap'].sum():,})")
axA.axvline(op["pop"].median(),ls="--",color="#333",lw=1.4)
axA.set_xscale("log"); axA.set_xlabel("adult population per unit (log)"); axA.set_ylabel("number of units")
axA.set_title(f"A)  Operational unit (official hybrid, n={len(op):,})\nFCU / bairro / capital-district — HETEROGENEOUS (median {op['pop'].median():,.0f})",fontsize=11,fontweight="bold")
axA.legend(fontsize=9); axA.grid(alpha=0.3,axis="y")
# B: regionalisation
axB.hist(rgp.values,bins=bins,color="#7a0177",alpha=0.82,label=f"regions (n={len(rgp):,})")
axB.axvline(rgp.median(),ls="--",color="#333",lw=1.4)
axB.set_xscale("log"); axB.set_xlabel("adult population per unit (log)")
axB.set_title(f"B)  Regionalisation (constructed, n={len(rgp):,})\nsectors grown to ~5,000 adults, favela separate — UNIFORM (median {rgp.median():,.0f})",fontsize=11,fontweight="bold")
axB.legend(fontsize=9); axB.grid(alpha=0.3,axis="y")
fig.suptitle("The two candidate spatial units, compared — operational (real IBGE places, heterogeneous) vs regionalisation (constructed, uniform)",fontsize=12,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_unit_comparison_distribution.png",dpi=150,bbox_inches="tight"); plt.close()
print("Saved /tmp/fig_unit_comparison_distribution.png")
