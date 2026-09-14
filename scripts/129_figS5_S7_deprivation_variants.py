"""Supplementary Figures S5–S7 on the primary (crude) rate basis (ADR-0006).

Produces:
  S5  LTFU (% of evaluated episodes) by quintile of (a) household-income deprivation and
      (b) the composite vulnerability index, region-cluster bootstrap 95% CI.
  S6  Incidence and mortality by quintile of household income (a,b) and of the composite
      index (c,d), all São Paulo; excess vs least-deprived quintile; excess fraction inset.
  S7  Same as S6 restricted to metropolitan regions (Greater São Paulo + Baixada Santista).
Rates follow scripts/rank_basis.py (RANK=crude -> crude rates; RANK=std -> indirect
age-standardisation as in 124). Quintiles are population-weighted over eligible regions
(>=10 cases; LTFU: >=10 evaluated). Outputs: /tmp/figS5_ltfu_deprivation{SUF}.png,
/tmp/figS6_attributable_deprivation{SUF}.png, /tmp/figS7_attributable_metro{SUF}.png,
/tmp/figS5_S7_values{SUF}.json (numbers quoted in the manuscript).
"""
import os, sys, json
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rank_basis import RANK, SUF
np.random.seed(20240625); T = 12; B = 300
matplotlib.rcParams.update({"font.family": "sans-serif", "font.size": 10})

reg = pd.read_csv("/tmp/region_units.csv", dtype={"region_id": str}); reg = reg[reg["pop"] > 0]
metro = pd.read_csv("/tmp/region_metro.csv", dtype={"region_id": str})   # scripts/130_region_metro.py
reg = reg.merge(metro, on="region_id", how="left"); reg["metro"] = reg["metro"].fillna(False).astype(bool)
state_rate = {"n": reg["n"].sum() / (reg["pop"].sum() * T) * 1e5, "nd": reg["nd"].sum() / (reg["pop"].sum() * T) * 1e5}
ECOL = {"n": "E_inc", "nd": "E_dr"}

def quintiles(d, key, ascending):
    d = d.sort_values(key, ascending=ascending).copy()   # q0 = least deprived (income desc / index asc)
    cum = d["pop"].cumsum() / d["pop"].sum(); d["q"] = np.minimum((cum * 5).astype(int), 4)
    return d

def rate_panel(d, ncol):
    g = d.groupby("q").agg(n=(ncol, "sum"), E=(ECOL[ncol], "sum"), pop=("pop", "sum"))
    if RANK == "std": g["rate"] = g["n"] / g["E"] * state_rate[ncol]
    else:             g["rate"] = g["n"] / (g["pop"] * T) * 1e5
    g["excess"] = (g["rate"] - g.loc[0, "rate"]) / 1e5 * g["pop"] * T
    return g

def ef(g): return g["excess"][1:].sum() / g["n"].sum() * 100

def ef_ci(d, key, asc, ncol):
    v = [ef(rate_panel(quintiles(d.sample(len(d), replace=True), key, asc), ncol)) for _ in range(B)]
    return np.percentile(v, [2.5, 97.5])

def ltfu_panel(d):
    g = d.groupby("q").agg(na=("na", "sum"), ne=("ne", "sum")); g["p"] = g["na"] / g["ne"] * 100; return g

def ltfu_ci(d, key, asc):
    P = np.array([ltfu_panel(quintiles(d.sample(len(d), replace=True), key, asc))["p"].values for _ in range(B)])
    return np.percentile(P, [2.5, 97.5], axis=0)

VAL = {}
QL = ["1\n(least)", "2", "3", "4", "5\n(most)"]

def draw_rates(ax, g, ncol, title, color):
    ax.bar(range(5), g["rate"], color=color, alpha=.85)
    ax.axhline(g.loc[0, "rate"], ls="--", color="#555", lw=1)
    for i in range(1, 5):
        ax.text(i, g.loc[i, "rate"], f"{g.loc[i,'excess']:,.0f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(range(5)); ax.set_xticklabels(QL, fontsize=8); ax.set_title(title, fontsize=10, loc="left")
    ax.set_ylabel("per 100,000 adults/yr" if ncol == "n" else "deaths per 100,000/yr")

# ---------------- S6 (all) and S7 (metro) ----------------
for tag, sub, fname in [("S6", reg, "figS6_attributable_deprivation"), ("S7", reg[reg["metro"]], "figS7_attributable_metro")]:
    el = sub[sub["n"] >= 10].dropna(subset=["income", "vuln"])
    fig, axes = plt.subplots(2, 2, figsize=(9, 7))
    VAL[tag] = {}
    for j, (key, asc, klab) in enumerate([("income", False, "household-income"), ("vuln", True, "composite-index")]):
        eq = quintiles(el, key, asc)
        for i, (ncol, olab, col) in enumerate([("n", "notifications", "#1a3d5c"), ("nd", "mortality", "#7a0177")]):
            g = rate_panel(eq, ncol); e = ef(g); lo, hi = ef_ci(el, key, asc, ncol)
            ax = axes[i, j]; draw_rates(ax, g, ncol, f"({'abcd'[i*2+j]}) {olab.capitalize()} by {klab} quintile", col)
            ax.text(.03, .95, f"Excess fraction {e:.0f}% (95% CI {lo:.0f}–{hi:.0f})\nexcess {g['excess'][1:].sum():,.0f}",
                    transform=ax.transAxes, va="top", fontsize=8, bbox=dict(fc="white", ec="#999", alpha=.9))
            VAL[tag][f"{olab}_{key}"] = {"EF": round(e, 1), "CI": [round(lo, 1), round(hi, 1)],
                                          "rates": [round(x, 2) for x in g["rate"]], "excess": round(g["excess"][1:].sum())}
            print(f"{tag} {olab:9s} {key:6s} EF {e:.1f}% ({lo:.0f}–{hi:.0f}) rates " + "/".join(f"{x:.1f}" for x in g["rate"]))
    plt.tight_layout(); plt.savefig(f"/tmp/{fname}{SUF}.png", dpi=250, bbox_inches="tight"); plt.close()

# ---------------- S5 LTFU by quintile ----------------
el = reg[reg["ne"] >= 10].dropna(subset=["income", "vuln"])
fig, axes = plt.subplots(1, 2, figsize=(9, 3.6)); VAL["S5"] = {}
for j, (key, asc, klab) in enumerate([("income", False, "household-income"), ("vuln", True, "composite-index")]):
    eq = quintiles(el, key, asc); g = ltfu_panel(eq); lo, hi = ltfu_ci(el, key, asc)
    ax = axes[j]; ax.bar(range(5), g["p"], color="#1f6f8b", alpha=.85)
    ax.errorbar(range(5), g["p"], yerr=[g["p"] - lo, hi - g["p"]], fmt="none", ecolor="#333", capsize=3, lw=1)
    ax.axhline(g.loc[0, "p"], ls="--", color="#555", lw=1)
    ax.set_xticks(range(5)); ax.set_xticklabels(QL, fontsize=8); ax.set_ylabel("LTFU, % of evaluated episodes")
    ax.set_title(f"({'ab'[j]}) LTFU by {klab} quintile", fontsize=10, loc="left"); ax.set_ylim(0, max(hi) * 1.25)
    VAL["S5"][key] = {"p": [round(x, 1) for x in g["p"]], "lo": [round(x, 1) for x in lo], "hi": [round(x, 1) for x in hi]}
    print(f"S5 LTFU by {key}: " + "/".join(f"{x:.1f}" for x in g["p"]))
plt.tight_layout(); plt.savefig(f"/tmp/figS5_ltfu_deprivation{SUF}.png", dpi=250, bbox_inches="tight"); plt.close()
json.dump(VAL, open(f"/tmp/figS5_S7_values{SUF}.json", "w"), indent=1)
print(f"Saved /tmp/figS5..S7{SUF}.png and values json")
