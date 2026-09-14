"""Composite Figure 3 (1x3): social patterning + attributable burden.
(a) Cohen's d of each vulnerability component between hotspot and non-hotspot regions (3 outcomes)
(b) incidence attributable to income deprivation (PAF, by household-income quintile)
(c) mortality attributable to income deprivation (PAF, by household-income quintile)
Computation reused from manuscript script 104 (a) and new-analysis script 122 (b,c).
"""
import os, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import zscore
from fig_common import INC, MORT, LTFU, REFLINE, GRIDCLR, AN, OUT, set_style

set_style(); os.makedirs(OUT, exist_ok=True)
reg = pd.read_csv(f"{AN}/region_units.csv", dtype={"region_id": str})

# ---------- Cohen's d (script 104) ----------
d = reg[reg["n"] >= 10].dropna(subset=["income", "favela", "illit", "residents"]).copy()
d["c_income"] = -zscore(d["income"]); d["c_favela"] = zscore(d["favela"])
d["c_illit"] = zscore(d["illit"]);   d["c_resid"] = zscore(d["residents"])
COMP = [("c_income", "Low income"), ("c_favela", "% favela"), ("c_illit", "Illiteracy"), ("c_resid", "Residents/hh")]
LENS = [("hs_inc", "Incidence", INC), ("hs_mort", "Mortality", MORT), ("hs_aband", "LTFU", LTFU)]
def cohend(col, flag):
    a = d.loc[d[flag], col]; b = d.loc[~d[flag], col]
    sp = np.sqrt((a.var() + b.var()) / 2); return (a.mean() - b.mean()) / sp if sp > 0 else np.nan
M = np.array([[cohend(c, l) for l, _, _ in LENS] for c, _ in COMP])

# ---------- deprivation PAF (script 122) ----------
T = 12; rng = np.random.default_rng(20260718)
def qassign(df, by, ascending):
    o = df.sort_values(by, ascending=ascending); cum = o["pop"].cumsum() / o["pop"].sum()
    q = np.ceil(np.clip(cum.values, 1e-9, 1) * 5).astype(int).clip(1, 5)
    return pd.Series(q, index=o.index).reindex(df.index)
def paf_point(df, col, by, ascending):
    df = df.dropna(subset=[col, by]).copy(); df = df[df["pop"] > 0].reset_index(drop=True)
    df["q"] = qassign(df, by, ascending); py = df["pop"] * T
    obs = (df[col] * py / 1e5).sum(); ref = (df.loc[df.q == 1, col] * df.loc[df.q == 1, "pop"]).sum() / df.loc[df.q == 1, "pop"].sum()
    exp = (ref * py / 1e5).sum()
    rates = [(df.loc[df.q == qi, col] * df.loc[df.q == qi, "pop"]).sum() / df.loc[df.q == qi, "pop"].sum() for qi in range(1, 6)]
    excess = [((df.loc[df.q == qi, col] - ref) * df.loc[df.q == qi, "pop"] * T / 1e5).sum() for qi in range(1, 6)]
    return dict(paf=(obs - exp) / obs * 100, excess=obs - exp, ref=ref, rates=rates, excesses=excess)
def paf_ci(df, col, by, ascending, B=4000):
    df = df.dropna(subset=[col, by]).copy(); df = df[df["pop"] > 0].reset_index(drop=True); ix = df.index.values; out = []
    for _ in range(B):
        b = df.loc[rng.choice(ix, len(ix), replace=True)].reset_index(drop=True)
        b["q"] = qassign(b, by, ascending); py = b["pop"] * T
        obs = (b[col] * py / 1e5).sum(); ref = (b.loc[b.q == 1, col] * b.loc[b.q == 1, "pop"]).sum() / b.loc[b.q == 1, "pop"].sum()
        exp = (ref * py / 1e5).sum(); out.append((obs - exp) / obs * 100)
    return np.percentile(out, [2.5, 97.5])

def paf_panel(ax, col, color, letter, oname, noun):
    rr = paf_point(reg, col, "income", False); ci = paf_ci(reg, col, "income", False)
    qs = range(1, 6)
    ax.bar(qs, rr["rates"], color=color, alpha=0.9, width=0.70, zorder=3)
    ax.axhline(rr["ref"], ls="--", lw=1, color=REFLINE, zorder=2)
    ax.text(5.6, rr["ref"], "reference\n(least-deprived)", fontsize=8, va="center", ha="left", color=REFLINE)
    for qi, r, ex in zip(qs, rr["rates"], rr["excesses"]):
        if qi > 1: ax.text(qi, r + max(rr["rates"]) * 0.02, f"+{ex:,.0f}", ha="center", fontsize=8.3, color="#333")
    ax.set_title(f"({letter})  {oname}", loc="left", fontsize=12.5, fontweight="bold")
    ax.set_xlabel("Household-income deprivation quintile\n(1 = least → 5 = most)")
    ax.set_ylabel("Rate per 100,000/yr")
    ax.set_xticks(list(qs)); ax.set_xlim(0.4, 6.6); ax.set_ylim(0, max(rr["rates"]) * 1.32)
    ax.grid(axis="y", lw=.5, color=GRIDCLR, zorder=0); ax.spines[["top", "right"]].set_visible(False)
    box = f"PAF = {rr['paf']:.0f}%  (95% CI {ci[0]:.0f}–{ci[1]:.0f})\n{noun}: {rr['excess']:,.0f}"
    ax.text(.04, .985, box, transform=ax.transAxes, fontsize=9, va="top", linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#ccc"))
    print(f"  {oname:9s}: PAF {rr['paf']:.0f}% [{ci[0]:.0f}-{ci[1]:.0f}] excess {rr['excess']:,.0f}")

# ================= FIGURE =================
fig, AX = plt.subplots(1, 3, figsize=(16.5, 5.2), gridspec_kw={"width_ratios": [1.35, 1, 1]})
plt.subplots_adjust(left=0.055, right=0.975, top=0.88, bottom=0.17, wspace=0.30)

# (a) Cohen's d
a = AX[0]; xc = np.arange(len(COMP)); w = 0.25
for j, (l, ln, col) in enumerate(LENS):
    a.bar(xc + (j - 1) * w, M[:, j], w, color=col, label=ln)
a.set_xticks(xc); a.set_xticklabels([c[1] for c in COMP]); a.axhline(0, color="#333", lw=0.8)
a.set_ylabel("Standardized difference (Cohen's d)\nhotspot − rest")
a.legend(fontsize=9.5, title="Hotspot type", title_fontsize=9.5, loc="upper right")
a.grid(axis="y", alpha=0.35, color=GRIDCLR); a.spines[["top", "right"]].set_visible(False)
a.set_title("(a)", loc="left", fontsize=13, fontweight="bold")

# (b) incidence PAF ; (c) mortality PAF
paf_panel(AX[1], "inc_crude", INC, "b", "Notifications", "excess cases")
paf_panel(AX[2], "drate_crude", MORT, "c", "Mortality", "excess deaths")

fig.savefig(f"{OUT}/Figure3_social_attributable.png", dpi=300, bbox_inches="tight", facecolor="white")
print(f"saved {OUT}/Figure3_social_attributable.png")
