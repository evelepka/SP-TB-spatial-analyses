"""Supplementary Figure S4 — spatial structure of the three outcomes.

(a) Global Moran's I (queen contiguity, row-standardised weights, 999 permutations) on
    log region-level rates, unadjusted and on the residuals of a regression on the
    place-vulnerability index;
(b) share of variance in each log rate explained by the vulnerability index (OLS R²);
(c) spatial autoregressive parameter rho from a maximum-likelihood spatial-lag model
    (log rate ~ vulnerability + rho*W*y), fitted on the largest connected component of the
    contiguity graph so that separately regionalised favela units do not distort W.
Rates follow scripts/rank_basis.py (crude by default). Zero rates are handled with
log(rate + half the smallest positive rate). Eligible regions: >=10 cases (LTFU: >=10 evaluated).
Output: /tmp/figS4_spatial_structure{SUF}.png, /tmp/figS4_values{SUF}.json
"""
import os, sys, json
import numpy as np, pandas as pd, geopandas as gpd, libpysal, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from esda.moran import Moran
from spreg import ML_Lag
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rank_basis import RANK, SUF, RATE
np.random.seed(20240625)

reg = pd.read_csv("/tmp/region_units.csv", dtype={"region_id": str}); reg = reg[reg["pop"] > 0]
geo = gpd.read_file("/tmp/region_geom.gpkg"); geo["region_id"] = geo["region_id"].astype(str)
OUT = [("Notifications", RATE["inc"], reg["n"] >= 10, "#1a3d5c"),
       ("Mortality", RATE["mort"], reg["n"] >= 10, "#7a0177"),
       ("LTFU", RATE["aband"], reg["ne"] >= 10, "#1f6f8b")]
res = {}
for lab, col, elig, color in OUT:
    d = geo.merge(reg.loc[elig, ["region_id", col, "vuln"]], on="region_id").dropna(subset=[col, "vuln"]).reset_index(drop=True)
    pos = d[col][d[col] > 0]; y = np.log(d[col].values + 0.5 * pos.min())
    w = libpysal.weights.Queen.from_dataframe(d, use_index=False, silence_warnings=True)
    keep = [i for i in range(len(d)) if i not in w.islands]
    d = d.iloc[keep].reset_index(drop=True); y = y[keep]
    w = libpysal.weights.Queen.from_dataframe(d, use_index=False, silence_warnings=True); w.transform = "R"
    X = d[["vuln"]].values
    beta = np.linalg.lstsq(np.column_stack([np.ones(len(y)), X]), y, rcond=None)[0]
    resid = y - (beta[0] + beta[1] * X[:, 0]); r2 = 1 - resid.var() / y.var()
    mi = Moran(y, w, permutations=999); mr = Moran(resid, w, permutations=999)
    # largest connected component for the lag model
    comp = w.component_labels; big = np.bincount(comp).argmax(); idx = np.where(comp == big)[0]
    dl = d.iloc[idx].reset_index(drop=True); wl = libpysal.weights.Queen.from_dataframe(dl, use_index=False, silence_warnings=True); wl.transform = "R"
    ml = ML_Lag(y[idx].reshape(-1, 1), X[idx], w=wl, name_y=lab, name_x=["vuln"])
    rho = float(ml.rho)
    res[lab] = {"n": int(len(d)), "moran_I": round(float(mi.I), 3), "moran_p": float(mi.p_sim),
                "moran_I_adj": round(float(mr.I), 3), "moran_p_adj": float(mr.p_sim), "R2_vuln": round(float(r2), 3),
                "rho_lag": round(rho, 3), "n_lcc": int(len(idx))}
    print(f"{lab:14s} n={len(d)} I={mi.I:.2f} (p={mi.p_sim}) I_adj={mr.I:.2f} R2={r2:.2f} rho={rho:.2f} (LCC n={len(idx)})")

fig, axes = plt.subplots(1, 3, figsize=(11, 3.6))
labs = [o[0] for o in OUT]; cols = [o[3] for o in OUT]; x = np.arange(3)
axes[0].bar(x - 0.18, [res[l]["moran_I"] for l in labs], 0.36, color=cols, label="unadjusted")
axes[0].bar(x + 0.18, [res[l]["moran_I_adj"] for l in labs], 0.36, color=cols, alpha=0.45, label="adjusted for vulnerability")
axes[0].set_ylabel("Global Moran's I"); axes[0].set_title("(a) Spatial autocorrelation", loc="left", fontsize=10); axes[0].legend(fontsize=8, frameon=False)
axes[1].bar(x, [100 * res[l]["R2_vuln"] for l in labs], 0.5, color=cols); axes[1].set_ylabel("% variance explained by vulnerability index")
axes[1].set_title("(b) Variance explained", loc="left", fontsize=10)
axes[2].bar(x, [res[l]["rho_lag"] for l in labs], 0.5, color=cols); axes[2].set_ylabel("Spatial autoregressive parameter (ρ)")
axes[2].set_title("(c) Spatial-lag model", loc="left", fontsize=10)
for ax in axes:
    ax.set_xticks(x); ax.set_xticklabels(labs, fontsize=9); ax.set_ylim(0, None); ax.grid(axis="y", alpha=0.3)
plt.tight_layout(); plt.savefig(f"/tmp/figS4_spatial_structure{SUF}.png", dpi=250, bbox_inches="tight"); plt.close()
json.dump(res, open(f"/tmp/figS4_values{SUF}.json", "w"), indent=1)
print(f"Saved /tmp/figS4_spatial_structure{SUF}.png")
