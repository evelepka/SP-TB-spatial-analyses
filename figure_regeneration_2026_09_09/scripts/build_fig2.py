"""Composite Figure 2 (2x2): geographic concentration of TB + geographic-inequality PAF.
(a) de-noised Lorenz curves   (b) top-k concentration shares   (c) 4-set hotspot Venn
(d) geographic-inequality excess fraction in notifications (all Sao Paulo; reference = lowest-incidence quintile)
Computation follows scripts/102_fig1_concentration_region.py (a-c) and scripts/122_manuscript_composites.py (d).
"""
import os, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from scipy.interpolate import PchipInterpolator
from venn import venn
from fig_common import INC, MORT, LTFU, VULN, REFLINE, GRIDCLR, AN, OUT, set_style, panel_tag

set_style(); os.makedirs(OUT, exist_ok=True)
np.random.seed(20240625)
reg = pd.read_csv(f"{AN}/region_units.csv", dtype={"region_id": str})
co  = pd.read_csv(f"{AN}/region_cases.csv", dtype={"region_id": str})

# ---------- concentration machinery (script 102) ----------
pv = reg.set_index("region_id")["pop"]; units = list(pv.index)
idx = {u: i for i, u in enumerate(units)}; K = len(units); popv = pv.values
GRID = np.linspace(0, 1, 101)
def denoised_curve(mask, B=200):
    ix = co[mask]["region_id"].map(idx).dropna().astype(int).values; acc = np.zeros(len(GRID)); m = 0
    for _ in range(B):
        h = np.random.rand(len(ix)) < 0.5
        a = np.bincount(ix[h], minlength=K).astype(float); b = np.bincount(ix[~h], minlength=K).astype(float)
        for rk, vl in [(a, b), (b, a)]:
            if vl.sum() == 0: continue
            ra = rk / popv; o = np.argsort(-ra)
            cp = np.cumsum(popv[o]) / popv.sum(); cv = np.cumsum(vl[o]) / vl.sum()
            acc += np.interp(GRID, cp, cv); m += 1
    return acc / m
def smooth_monotone(c):
    anchors = np.array([0, .05, .10, .15, .20, .30, .40, .55, .70, .85, 1.0])
    yv = np.maximum.accumulate(np.interp(anchors, GRID, c)); yv[0] = 0.0; yv[-1] = 1.0
    return np.clip(PchipInterpolator(anchors, yv)(GRID), 0, 1)

def denoised_curve_prop(B=200):
    """LTFU as a PROPORTION of evaluated episodes: rank regions by split-sample
    LTFU/evaluated; plot cumulative held-out LTFU events vs cumulative adult population."""
    ev = co[co["eval"] == 1]
    ri = ev["region_id"].map(idx).dropna().astype(int).values
    ab = (ev["aband"] == 1).values.astype(float)
    acc = np.zeros(len(GRID)); m = 0
    for _ in range(B):
        h = np.random.rand(len(ri)) < 0.5
        for sel in (h, ~h):
            oth = ~sel
            den = np.bincount(ri[sel], minlength=K).astype(float)
            num = np.bincount(ri[sel], weights=ab[sel], minlength=K).astype(float)
            vl  = np.bincount(ri[oth], weights=ab[oth], minlength=K).astype(float)
            if vl.sum() == 0: continue
            prop = np.where(den > 0, num / np.maximum(den, 1), -1.0)
            o = np.argsort(-prop)
            cp = np.cumsum(popv[o]) / popv.sum()
            cv = np.cumsum(vl[o]) / vl.sum()
            acc += np.interp(GRID, cp, cv); m += 1
    return acc / m

LENS = [("TB notifications", co["age"] >= 15, INC), ("TB mortality", co["death"] == 1, MORT), ("LTFU", co["aband"] == 1, LTFU)]
QS = [0.05, 0.10, 0.20, 0.40]
res = []
for lab, mask, col in LENS:
    raw = denoised_curve_prop() if lab == "LTFU" else denoised_curve(mask)
    curve = smooth_monotone(raw); dg = 2 * np.trapz(curve, GRID) - 1
    deno = [float(np.interp(q, GRID, curve)) * 100 for q in QS]
    res.append((lab, deno, curve, dg, col))

# ---------- PAF machinery (script 122) ----------
T = 12; rng = np.random.default_rng(20260718)
def qassign(d, by, ascending):
    o = d.sort_values(by, ascending=ascending); cum = o["pop"].cumsum() / o["pop"].sum()
    q = np.ceil(np.clip(cum.values, 1e-9, 1) * 5).astype(int).clip(1, 5)
    return pd.Series(q, index=o.index).reindex(d.index)
def paf_point(d, col, by, ascending):
    d = d.dropna(subset=[col, by]).copy(); d = d[d["pop"] > 0].reset_index(drop=True)
    d["q"] = qassign(d, by, ascending); py = d["pop"] * T
    obs = (d[col] * py / 1e5).sum(); ref = (d.loc[d.q == 1, col] * d.loc[d.q == 1, "pop"]).sum() / d.loc[d.q == 1, "pop"].sum()
    exp = (ref * py / 1e5).sum()
    rates = [(d.loc[d.q == qi, col] * d.loc[d.q == qi, "pop"]).sum() / d.loc[d.q == qi, "pop"].sum() for qi in range(1, 6)]
    excess = [((d.loc[d.q == qi, col] - ref) * d.loc[d.q == qi, "pop"] * T / 1e5).sum() for qi in range(1, 6)]
    return dict(paf=(obs - exp) / obs * 100, excess=obs - exp, ref=ref, rates=rates, excesses=excess)
def paf_ci(d, col, ascending, B=4000):
    d = d.dropna(subset=[col]).copy(); d = d[d["pop"] > 0].reset_index(drop=True); ix = d.index.values; out = []
    for _ in range(B):
        b = d.loc[rng.choice(ix, len(ix), replace=True)].reset_index(drop=True)
        b["q"] = qassign(b, col, ascending); py = b["pop"] * T
        obs = (b[col] * py / 1e5).sum(); ref = (b.loc[b.q == 1, col] * b.loc[b.q == 1, "pop"]).sum() / b.loc[b.q == 1, "pop"].sum()
        exp = (ref * py / 1e5).sum(); out.append((obs - exp) / obs * 100)
    return np.percentile(out, [2.5, 97.5])

# ================= FIGURE =================
fig, AX = plt.subplots(2, 2, figsize=(13, 10.6))
plt.subplots_adjust(left=0.075, right=0.965, top=0.94, bottom=0.075, wspace=0.24, hspace=0.30)

# (a) Lorenz
a = AX[0, 0]
a.plot([0, 1], [0, 1], "--", color="#aaa", lw=1.2, label="equality (no concentration)")
for lab, deno, curve, dg, col in res:
    a.plot(GRID, curve, color=col, lw=2.6, label=f"{lab} (Gini {dg:.2f})")
a.set_xlabel("Cumulative share of adult population\n(highest-rate regions first)")
a.set_ylabel("Cumulative share of events")
a.set_xlim(0, 1); a.set_ylim(0, 1); a.grid(alpha=0.35, color=GRIDCLR)
a.legend(fontsize=9.5, loc="upper left"); a.spines[["top", "right"]].set_visible(False)
panel_tag(a, "a")

# (b) top-k shares
b = AX[0, 1]; xq = [q * 100 for q in QS]
b.plot([0, 40], [0, 40], ":", color="#bbb", lw=1.1, zorder=1, label="proportional (no concentration)")
for lab, deno, curve, dg, col in res:
    b.plot(xq, deno, "-o", color=col, lw=2.5, ms=6, label=lab, zorder=3)
b.set_xticks(xq); b.set_xlabel("% of adult population in highest-rate regions")
b.set_ylabel("% of events concentrated there"); b.set_ylim(0, None)
b.grid(alpha=0.35, color=GRIDCLR); b.legend(fontsize=9.5, loc="upper left")
b.spines[["top", "right"]].set_visible(False); panel_tag(b, "b")

# (c) 4-set Venn
c = AX[1, 0]
VL = {"Notifications": set(reg[reg["hs_inc"]]["region_id"]), "Mortality": set(reg[reg["hs_mort"]]["region_id"]),
      "LTFU": set(reg[reg["hs_aband"]]["region_id"]), "Vulnerability": set(reg[reg["hs_vuln"]]["region_id"])}
venn(VL, ax=c, fontsize=9, legend_loc="upper left", cmap=ListedColormap([INC, MORT, LTFU, VULN]))
c.set_aspect("auto"); c.set_xlim(-0.02, 1.02); c.set_ylim(0.06, 0.94)
panel_tag(c, "c")

# (d) geographic-inequality PAF (all Sao Paulo, incidence, ref = lowest-incidence quintile)
d = AX[1, 1]
rr = paf_point(reg, "inc_crude", "inc_crude", True); ci = paf_ci(reg, "inc_crude", True)
qs = range(1, 6)
d.bar(qs, rr["rates"], color=INC, alpha=0.9, width=0.70, zorder=3)
d.axhline(rr["ref"], ls="--", lw=1, color=REFLINE, zorder=2)
d.text(5.6, rr["ref"], "reference\n(lowest notification rate)", fontsize=8, va="center", ha="left", color=REFLINE)
for qi, r, ex in zip(qs, rr["rates"], rr["excesses"]):
    if qi > 1: d.text(qi, r + max(rr["rates"]) * 0.02, f"+{ex:,.0f}", ha="center", fontsize=8.3, color="#333")
d.set_xlabel("Notification-rate quintile (1 = lowest → 5 = highest)")
d.set_ylabel("Notification rate per 100,000/yr")
d.set_xticks(list(qs)); d.set_xlim(0.4, 6.6); d.set_ylim(0, max(rr["rates"]) * 1.30)
d.grid(axis="y", lw=.5, color=GRIDCLR, zorder=0); d.spines[["top", "right"]].set_visible(False)
box = f"Excess fraction = {rr['paf']:.0f}%  (95% CI {ci[0]:.0f}–{ci[1]:.0f})\nExcess cases: {rr['excess']:,.0f}"
d.text(.04, .985, box, transform=d.transAxes, fontsize=9, va="top", linespacing=1.5,
       bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#ccc"))
panel_tag(d, "d")

fig.savefig(f"{OUT}/Figure2_concentration.pdf", bbox_inches="tight", facecolor="white")
fig.savefig(f"{OUT}/Figure2_concentration.png", dpi=300, bbox_inches="tight", facecolor="white")
print(f"saved {OUT}/Figure2_concentration.png")
print("  top-20% shares: " + ", ".join(f"{l} {d[2]:.1f}%" for l, d, _, _, _ in res))
print(f"  Lorenz Gini: " + ", ".join(f"{l} {g:.2f}" for l, _, _, g, _ in res))
print(f"  geo-inequality PAF {rr['paf']:.0f}% [{ci[0]:.0f}-{ci[1]:.0f}], excess {rr['excess']:,.0f}, ref {rr['ref']:.1f}")
