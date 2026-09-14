"""Getis-Ord Gi* sensitivity: do the rank-based hotspots coincide with local statistical
clusters? (Amanda Coutinho review comments #5/#9, 2026-09-01.)

Our hotspots are an OPERATIONAL definition (regions ranked by age-standardised rate until
20% of adult population; script 50 / region pipeline 100). Gi* answers a different question
(where is local elevation improbable under spatial randomness). This script quantifies the
overlap so the Methods can state the distinction with evidence rather than rhetoric.

Method: Queen contiguity on region polygons (islands dropped from the test), Gi* (star=True,
999 conditional permutations, seed 42) on the same age-standardised rates used for ranking
(inc_adj / drate_adj / ltfu_adj). "Gi* hot" = z>0 with p_sim<0.05; FDR (Benjamini-Hochberg,
5%) reported as the stricter variant. Overlaps are population-weighted and Jaccard.

Output: /tmp/gistar_sensitivity.json
"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import libpysal
from esda.getisord import G_Local

g = gpd.read_file("/tmp/region_geom.gpkg")
ru = pd.read_csv("/tmp/region_units.csv", dtype={"region_id": str}, low_memory=False)
g["region_id"] = g["region_id"].astype(str)
d = g.merge(ru, on="region_id", how="inner")

OUT = [("incidence", "inc_adj", "hs_inc"),
       ("mortality", "drate_adj", "hs_mort"),
       ("ltfu", "ltfu_adj", "hs_aband")]

res = {}
for lab, rate, flag in OUT:
    dd = d.dropna(subset=[rate]).reset_index(drop=True).copy()
    w = libpysal.weights.Queen.from_dataframe(dd, use_index=False, silence_warnings=True)
    keep = [i for i in range(len(dd)) if i not in w.islands]
    dd2 = dd.iloc[keep].reset_index(drop=True)
    w2 = libpysal.weights.Queen.from_dataframe(dd2, use_index=False, silence_warnings=True)
    w2.transform = "R"
    np.random.seed(42)
    gi = G_Local(dd2[rate].values, w2, star=True, permutations=999)
    dd2["gi_z"] = gi.Zs
    dd2["gi_p"] = gi.p_sim
    dd2["gi_hot"] = (dd2["gi_z"] > 0) & (dd2["gi_p"] < 0.05)
    # FDR (Benjamini-Hochberg) at 5%, on the one-sided permutation p of hot-side regions
    p = dd2["gi_p"].values.copy()
    order = np.argsort(p)
    m = len(p)
    thresh = 0.0
    for rank, idx in enumerate(order, start=1):
        if p[idx] <= 0.05 * rank / m:
            thresh = p[idx]
    dd2["gi_hot_fdr"] = (dd2["gi_z"] > 0) & (dd2["gi_p"] <= thresh)

    hs = dd2[flag].fillna(0).astype(bool)
    pop = dd2["pop"].fillna(0)
    def olap(a, b):
        inter = (a & b); union = (a | b)
        return {"jaccard": round(inter.sum() / max(union.sum(), 1), 2),
                "pct_hs_in_gi": round(100 * pop[a & b].sum() / max(pop[a].sum(), 1), 1),
                "pct_gi_in_hs": round(100 * pop[a & b].sum() / max(pop[b].sum(), 1), 1)}
    res[lab] = {
        "n_regions_tested": len(dd2), "n_islands_dropped": len(w.islands),
        "n_hs": int(hs.sum()), "n_gi_hot": int(dd2["gi_hot"].sum()),
        "n_gi_hot_fdr": int(dd2["gi_hot_fdr"].sum()),
        "pop_share_gi_hot": round(100 * pop[dd2["gi_hot"]].sum() / pop.sum(), 1),
        "pop_share_gi_hot_fdr": round(100 * pop[dd2["gi_hot_fdr"]].sum() / pop.sum(), 1),
        "overlap_p05": olap(hs, dd2["gi_hot"]),
        "overlap_fdr": olap(hs, dd2["gi_hot_fdr"]),
    }
    r = res[lab]
    print(f"{lab:10s} testadas={r['n_regions_tested']} (ilhas {r['n_islands_dropped']}) "
          f"| HS={r['n_hs']} Gi*hot={r['n_gi_hot']} (FDR {r['n_gi_hot_fdr']}) "
          f"pop Gi*hot={r['pop_share_gi_hot']}%")
    print(f"           p<.05: J={r['overlap_p05']['jaccard']} "
          f"HS-pop em Gi*={r['overlap_p05']['pct_hs_in_gi']}% "
          f"Gi*-pop em HS={r['overlap_p05']['pct_gi_in_hs']}% "
          f"| FDR: J={r['overlap_fdr']['jaccard']} "
          f"HS em Gi*={r['overlap_fdr']['pct_hs_in_gi']}% "
          f"Gi* em HS={r['overlap_fdr']['pct_gi_in_hs']}%")

json.dump(res, open("/tmp/gistar_sensitivity.json", "w"), indent=1)
print("Saved /tmp/gistar_sensitivity.json")
