"""External validation of the 5-domain place-vulnerability composite (vuln_final =
income + illiteracy + sanitation + intra-household crowding + favela) against the official
Indice Paulista de Vulnerabilidade Social (IPVS) 2022, SEADE — both keyed on the
2022 IBGE census sector (CD_SETOR). IPVS gives an ORDINAL group 1 (Baixissima) ->
6 (Muito Alta vulnerabilidade). We test whether our continuous composite reproduces
that official ordering:
  (1) Spearman rho (composite vs IPVS group), sector level;
  (2) the gradient of the composite across the six IPVS groups (should rise monotonically);
  (3) which domains drive the agreement (per-domain Spearman) -- this also exposes the
      one axis IPVS has that we deliberately drop: its demographic/life-cycle dimension.
Source: repositorio.seade.gov.br IPVS_2022 shapefile (87.6 MB). Output:
/tmp/fig_ipvs_validation.png + printed tables.
"""
import pandas as pd, numpy as np, geopandas as gpd, matplotlib, matplotlib.pyplot as plt
from scipy.stats import spearmanr
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})

print("Loading composite + IPVS 2022...")
v = pd.read_csv("/tmp/vuln_final.csv", dtype={"CD_SETOR":str})
ip = gpd.read_file("/tmp/ipvs_2022/IPVS_2022.shp", ignore_geometry=True)[["CD_SETOR","C_IPVS","N_IPVS"]]
ip["CD_SETOR"] = ip["CD_SETOR"].astype(str)

m = v.merge(ip, on="CD_SETOR", how="inner")
print(f"  composite sectors: {len(v):,} | IPVS sectors: {len(ip):,} | merged: {len(m):,}")
m = m.dropna(subset=["C_IPVS"])             # drop 'Nao classificado' (rural/unclassified)
m["C_IPVS"] = m["C_IPVS"].astype(int)
print(f"  merged & IPVS-classified: {len(m):,}")

# (1) overall Spearman: composite vs official ordinal group
rho, p = spearmanr(m["vuln_final"], m["C_IPVS"])
print(f"\n(1) Spearman(composite, IPVS group) = {rho:.3f}  (p={p:.1e}, n={len(m):,})")

# (2) gradient of the composite across the 6 IPVS groups
LAB = {1:"1 Lowest",2:"2 Very low",3:"3 Low",4:"4 Medium",5:"5 High",6:"6 Very high"}
g = m.groupby("C_IPVS")["vuln_final"].agg(["count","mean","median","std"])
print("\n(2) Composite by IPVS group (monotonic rise = agreement):")
for k,r in g.iterrows():
    print(f"   {LAB[k]:16s} n={int(r['count']):6,d}  mean z={r['mean']:+.3f}  median={r['median']:+.3f}")

# (3) per-domain Spearman -- which domains drive agreement
print("\n(3) Per-domain Spearman vs IPVS group:")
for c,lab in [("z_income","income"),("z_illit","illiteracy"),
              ("z_crowd","crowding (intra-hh)"),("z_favela","favela"),("vuln_final","COMPOSITE")]:
    rr,_ = spearmanr(m[c], m["C_IPVS"])
    print(f"   {lab:20s} rho={rr:+.3f}")

# tail agreement: do our top-quintile sectors land in IPVS high groups?
m["q5"] = pd.qcut(m["vuln_final"], 5, labels=[1,2,3,4,5]).astype(int)
top = m[m["q5"]==5]
share_high = (top["C_IPVS"]>=5).mean()
print(f"\n(4) Of our most-vulnerable quintile, {share_high*100:.1f}% are IPVS group 5-6 (Alta/Muito Alta).")
bot = m[m["q5"]==1]
share_low = (bot["C_IPVS"]<=2).mean()
print(f"    Of our least-vulnerable quintile, {share_low*100:.1f}% are IPVS group 1-2 (Baixissima/Muito Baixa).")

# ---- figure: boxplot of composite across IPVS groups + per-domain rho bar ----
fig,(axA,axB) = plt.subplots(1,2,figsize=(14,5.8),gridspec_kw={"width_ratios":[1.5,1]})
groups = sorted(m["C_IPVS"].unique())
data = [m.loc[m["C_IPVS"]==k,"vuln_final"].values for k in groups]
cols = plt.cm.YlOrRd(np.linspace(0.15,0.95,len(groups)))
bp = axA.boxplot(data, patch_artist=True, showfliers=False, widths=0.62,
                 medianprops=dict(color="black",lw=1.6))
for patch,c in zip(bp["boxes"],cols): patch.set_facecolor(c)
axA.set_xticks(range(1,len(groups)+1)); axA.set_xticklabels([LAB[k].split(" ",1)[1] for k in groups],rotation=20,ha="right")
axA.set_ylabel("Our place-vulnerability composite (z)"); axA.set_xlabel("Official IPVS 2022 group (SEADE)")
axA.axhline(0,color="#888",lw=0.8,ls="--")
axA.set_title(f"(a)  Spearman $\\rho$ = {rho:.2f}  (n = {len(m):,} sectors)",loc="left",fontsize=12,fontweight="bold")
axA.grid(axis="y",alpha=0.3)

doms=[("z_income","income"),("z_illit","illiteracy"),("z_crowd","crowding\n(intra-hh)"),("z_favela","favela")]
rs=[spearmanr(m[c],m["C_IPVS"])[0] for c,_ in doms]
order=np.argsort(rs)
axB.barh([doms[i][1] for i in order],[rs[i] for i in order],color="#1f6f8b")
axB.axvline(rho,color="#c0392b",lw=2,ls="--",label=f"composite ({rho:.2f})")
axB.set_xlabel("Spearman $\\rho$ vs IPVS group"); axB.set_xlim(0,max(rs+[rho])*1.15)
axB.set_title("(b)  Agreement by domain",loc="left",fontsize=12,fontweight="bold")
axB.legend(fontsize=9.5,loc="lower right"); axB.grid(axis="x",alpha=0.3)
plt.tight_layout(); plt.savefig("/tmp/fig_ipvs_validation.png",dpi=300,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_ipvs_validation.png")
