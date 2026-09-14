"""Descriptive distribution of the PRIMARY (operational) spatial unit — the official-unit
hybrid (FCU favela ≥5,000 / IBGE bairro / capital district), n=3,014. We had characterised
the regionalisation (Appendix B) but not the operational unit it complements; the advisor
asked for the official-unit distribution. Histogram of adult population per unit (capital vs
interior, log scale) + a summary table. Output: /tmp/fig_operational_unit_distribution.png
"""
import pandas as pd, numpy as np, matplotlib, matplotlib.pyplot as plt
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})

vs=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)
vs=vs[vs["pop15"]>0].copy()
def utype(u):
    u=str(u)
    if u.startswith("fcu__"): return "FCU (favela ≥5k)"
    if u.startswith("bairro_"): return "Bairro (IBGE)"
    if u.startswith("dist_"): return "District"
    return "Municipality (fallback)"
vs["utype"]=vs["unit_id"].apply(utype); vs["cap"]=vs["CD_MUN"].astype(str).eq("3550308")
u=vs.groupby("unit_id").agg(pop=("pop15","sum"),nsec=("CD_SETOR","size"),
                            utype=("utype","first"),cap=("cap","first")).reset_index()
p=u["pop"]
print(f"N units = {len(u):,}")
print(f"pop/unit: median {p.median():,.0f}  IQR [{p.quantile(.25):,.0f}, {p.quantile(.75):,.0f}]  range [{p.min():,.0f}, {p.max():,.0f}]")
print(f"heterogeneity p95/p5 = {p.quantile(.95)/p.quantile(.05):.0f}x")
print("\nby type:")
for ut,r in u.groupby("utype").agg(n=("unit_id","size"),med=("pop","median")).iterrows():
    print(f"  {ut:24s} n={int(r['n']):4d}  median {r['med']:,.0f}")
print("\ncapital vs interior:")
for cap,lab in [(True,"Capital (São Paulo city)"),(False,"Interior + other metros")]:
    s=u[u["cap"]==cap]["pop"]; print(f"  {lab:26s} n={len(s):4d}  median {s.median():,.0f}  IQR [{s.quantile(.25):,.0f}, {s.quantile(.75):,.0f}]")

# ── figure: population distribution, capital vs interior, log scale ──
fig,ax=plt.subplots(figsize=(9,5.4))
bins=np.logspace(np.log10(50),np.log10(700000),46)
ax.hist(u[~u["cap"]]["pop"],bins=bins,color="#1f6f8b",alpha=0.85,label=f"Interior + other metros (n={(~u['cap']).sum():,})")
ax.hist(u[u["cap"]]["pop"],bins=bins,color="#c0392b",alpha=0.8,label=f"Capital — São Paulo city (n={u['cap'].sum():,})")
ax.set_xscale("log")
ax.axvline(p.median(),ls="--",color="#333",lw=1.4); ax.text(p.median()*1.1,ax.get_ylim()[1]*0.92,f"overall median {p.median():,.0f}",fontsize=9,color="#333")
ax.set_xlabel("Adult (≥15) population per operational unit  (log scale)"); ax.set_ylabel("number of units")
ax.set_title(f"Distribution of the operational unit (n={len(u):,}) — heterogeneous by design\n"
             f"capital collapses to large districts (no official bairro layer); interior is fine bairros",
             fontsize=11.5,fontweight="bold")
ax.legend(fontsize=10); ax.grid(alpha=0.3,axis="y")
plt.tight_layout(); plt.savefig("/tmp/fig_operational_unit_distribution.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_operational_unit_distribution.png")
