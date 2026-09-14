"""IBP (CIDACS) sensitivity and concordance (JC review comments, 2026-08-04; approved 2026-08-11).

Builds an index on the domains of the Brazilian Deprivation Index (IBP: income, education,
sanitation) from the 2022 Census sector data, then reports:
 (1) construct-validity concordance (Spearman, sector level): composite x IPVS, composite x
     IBP-style, IBP-style x IPVS  [reference values: 0.76 / 0.92 / 0.72]
 (2) robustness of the hotspot-deprivation divergence (region-level Cohen's d, hotspot vs rest)
     under composite vs IBP-style index  [targets: +0.44/+0.24/-0.06 vs +0.21/+0.07/-0.11]
 (3) sanitation coverage in SP  [targets: 95.5% adequate; 87% of pop in sectors <=5% inadequate]
Output: /tmp/ibp_sensitivity.json (read by 116 for Supplementary Table S8).
"""
import pandas as pd, numpy as np, geopandas as gpd, json
from scipy.stats import spearmanr

vs = pd.read_csv("/tmp/vuln_sectors.csv", dtype={"CD_SETOR": str}, low_memory=False)
vf = pd.read_csv("/tmp/vuln_final.csv", dtype={"CD_SETOR": str})[["CD_SETOR", "vuln_final"]]
s = vs.merge(vf, on="CD_SETOR", how="inner")
s["ibp"] = s[["z_income", "z_illit", "z_sanit"]].sum(axis=1)

ip = gpd.read_file("/tmp/ipvs_2022/IPVS_2022.shp", ignore_geometry=True)[["CD_SETOR", "C_IPVS"]]
ip["CD_SETOR"] = ip["CD_SETOR"].astype(str)
m = s.merge(ip, on="CD_SETOR", how="inner").dropna(subset=["C_IPVS", "vuln_final", "ibp"])
m["C_IPVS"] = m["C_IPVS"].astype(int)
r_cv = spearmanr(m["vuln_final"], m["C_IPVS"]).correlation
r_ci = spearmanr(m["vuln_final"], m["ibp"]).correlation
r_iv = spearmanr(m["ibp"], m["C_IPVS"]).correlation
print(f"(1) n={len(m):,}  comp×IPVS={r_cv:.2f}  comp×IBP={r_ci:.2f}  IBP×IPVS={r_iv:.2f}")

# (2) region-level Cohen's d, unweighted, hotspot vs rest, composite vs IBP-style
rg = pd.read_csv("/tmp/regions_sectors.csv", dtype={"CD_SETOR": str})[["CD_SETOR", "region_id"]]
sec = s.merge(rg, on="CD_SETOR", how="left")
sec["region_id"] = sec["region_id"].fillna("DIST_" + sec["CD_DIST"].astype(str))
w = sec["pop15"].fillna(0)
ribp = (sec["ibp"] * w).groupby(sec["region_id"]).sum() / w.groupby(sec["region_id"]).sum()
ru = pd.read_csv("/tmp/region_units.csv", dtype={"region_id": str}, low_memory=False)
ru = ru.merge(ribp.rename("ibp"), on="region_id", how="left")

def cohend(a, b):
    n1, n0 = len(a), len(b)
    sp = np.sqrt(((n1 - 1) * a.std() ** 2 + (n0 - 1) * b.std() ** 2) / (n1 + n0 - 2))
    return (a.mean() - b.mean()) / sp

D = {}
for lens, lab in [("hs_inc", "incidence"), ("hs_mort", "mortality"), ("hs_aband", "LTFU")]:
    d = ru.dropna(subset=["vuln", "ibp"])
    hs = d[d[lens].astype(bool)]; rest = d[~d[lens].astype(bool)]
    D[lab] = {"composite": round(cohend(hs["vuln"], rest["vuln"]), 2),
              "ibp": round(cohend(hs["ibp"], rest["ibp"]), 2)}
    print(f"(2) {lab:10s} d composto={D[lab]['composite']:+.2f}  d IBP={D[lab]['ibp']:+.2f}")

# (3) sanitation coverage (population-weighted; d_sanit = share with inadequate sanitation)
wpop = s["pop15"].fillna(0)
inad = float(np.average(s["d_sanit"].fillna(0), weights=wpop))
le5 = float(wpop[s["d_sanit"] <= 0.05].sum() / wpop.sum())
le10 = float(wpop[s["d_sanit"] <= 0.10].sum() / wpop.sum())
print(f"(3) saneamento adequado {100*(1-inad):.1f}% | pop em setores <=5% inadequado {le5*100:.0f}% | <=10% {le10*100:.0f}%")

json.dump({"n_sectors": len(m), "rho_comp_ipvs": round(r_cv, 2), "rho_comp_ibp": round(r_ci, 2),
           "rho_ibp_ipvs": round(r_iv, 2), "cohend": D,
           "sanit_adequate_pct": round(100 * (1 - inad), 1), "pop_le5_pct": round(le5 * 100, 0),
           "pop_le10_pct": round(le10 * 100, 0)},
          open("/tmp/ibp_sensitivity.json", "w"), indent=1)
print("Saved /tmp/ibp_sensitivity.json")
