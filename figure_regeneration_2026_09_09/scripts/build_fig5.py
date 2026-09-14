"""Composite Figure 5 (1x3): temporal stability + out-of-sample usefulness.
(a) de-noised concentration (% of events in top 20% of population) per 3-year period
(b) out-of-sample hotspot prediction: hotspots frozen on old data vs best-possible ceiling
(c) alluvial of incidence-quintile transitions across the four periods
Computation reused from manuscript script 105 (a, c) and new-analysis script 123 (b).
"""
import os, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
import matplotlib.patches as mpatches
from fig_common import INC, MORT, LTFU, GRIDCLR, AN, OUT, set_style

set_style(); os.makedirs(OUT, exist_ok=True)
np.random.seed(20240625)
reg = pd.read_csv(f"{AN}/region_units.csv", dtype={"region_id": str})[["region_id", "pop", "n"]]
reg = reg[reg["pop"] > 0]
co = pd.read_csv(f"{AN}/region_cases.csv", dtype={"region_id": str})
pv = reg.set_index("region_id")["pop"]; units = list(pv.index)
idx = {u: i for i, u in enumerate(units)}; K = len(units); popv = pv.values; TOT = popv.sum()
co["ri"] = co["region_id"].map(idx); co = co.dropna(subset=["ri"]); co["ri"] = co["ri"].astype(int)

PERIODS = [(2013, 2015), (2016, 2018), (2019, 2021), (2022, 2024)]
PLAB = ["2013–15", "2016–18", "2019–21", "2022–24"]
OUTC = [("inc", None, INC, "Notifications"), ("mort", "death", MORT, "Mortality"), ("aband", "aband", LTFU, "LTFU")]

# ---------- (a) de-noised concentration per period (script 105) ----------
def ri_of(period, coln):
    s = co[co["year"].between(period[0], period[1])]
    if coln is not None: s = s[s[coln] == 1]
    return s["ri"].values
def denoised_share(ri, B=150, q=0.20):
    if len(ri) < 50: return np.nan
    s = []
    for _ in range(B):
        h = np.random.rand(len(ri)) < 0.5
        a = np.bincount(ri[h], minlength=K).astype(float); b = np.bincount(ri[~h], minlength=K).astype(float)
        for rk, vl in [(a, b), (b, a)]:
            if vl.sum() == 0: continue
            ra = rk / popv; o = np.argsort(-ra)
            cp = np.cumsum(popv[o]) / TOT; cv = np.cumsum(vl[o]) / vl.sum(); s.append(np.interp(q, cp, cv) * 100)
    return np.mean(s)

def denoised_share_prop(period, B=150, q=0.20):
    """LTFU as a PROPORTION of evaluated episodes: rank regions by split-sample
    LTFU/evaluated, accumulate to q of the adult population, then measure the share
    of held-out LTFU events falling in those regions."""
    s = co[co["year"].between(period[0], period[1])]
    ev = s[s["eval"] == 1]
    ri = ev["ri"].values
    ab = (ev["aband"] == 1).values.astype(float)
    if ab.sum() < 50: return np.nan
    out = []
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
            cp = np.cumsum(popv[o]) / TOT
            cv = np.cumsum(vl[o]) / vl.sum()
            out.append(np.interp(q, cp, cv) * 100)
    return float(np.mean(out))

SH = {ln: [] for ln, _, _, _ in OUTC}
for p in PERIODS:
    for ln, coln, _, _ in OUTC:
        if ln == "aband":
            SH[ln].append(denoised_share_prop(p))
        else:
            SH[ln].append(denoised_share(ri_of(p, coln)))
print("de-noised top-20% share by period:", {ln: [round(x) for x in SH[ln]] for ln, _, _, _ in OUTC})

# ---------- (b) out-of-sample prediction (script 123) ----------
rng = np.random.default_rng(20260718)
pop = pv
def hotspots(lo, hi, frac=0.20, minc=10):
    s = co[co.year.between(lo, hi)]
    c = s.groupby("region_id").size().reindex(pop.index).fillna(0)
    dd = pd.DataFrame({"pop": pop, "c": c}); dd = dd[dd["c"] >= minc].copy()
    dd["rate"] = dd["c"] / dd["pop"]; dd = dd.sort_values("rate", ascending=False)
    cum = dd["pop"].cumsum() / pop.sum(); sel = cum <= frac
    if sel.sum() < len(dd): sel.iloc[sel.sum()] = True
    return set(dd[sel].index)
def capture(hsset, lo, hi):
    s = co[co.year.between(lo, hi)]; c = s.groupby("region_id").size()
    return c[c.index.isin(hsset)].sum() / c.sum()
def capture_ci(hsset, lo, hi, B=1000):
    s = co[co.year.between(lo, hi)]; inset = s["region_id"].isin(hsset).values; n = len(inset)
    bs = [inset[rng.integers(0, n, n)].mean() for _ in range(B)]
    return np.percentile(bs, [2.5, 97.5])
SC = [((2013, 2018), (2019, 2024)), ((2013, 2018), (2022, 2024)), ((2013, 2015), (2022, 2024))]
RES = []
for (elo, ehi), (llo, lhi) in SC:
    fr = hotspots(elo, ehi); capR = capture(fr, llo, lhi); ciR = capture_ci(fr, llo, lhi)
    ct = hotspots(llo, lhi); capC = capture(ct, llo, lhi)
    RES.append(dict(tr=f"{elo}-{ehi}", te=f"{llo}-{lhi}", capR=capR, ciR=ciR, capC=capC))
print("OOS capR:", [round(r["capR"]*100) for r in RES], "capC:", [round(r["capC"]*100) for r in RES])

# ---------- (c) alluvial (script 105 panel d) ----------
NB = 5; rege = reg[reg["n"] >= 10].reset_index(drop=True)
Q = pd.DataFrame(index=rege["region_id"])
for i, p in enumerate(PERIODS):
    c = co[co.year.between(*p)].groupby("region_id").size()
    rr = rege.set_index("region_id").assign(c=c).fillna({"c": 0})
    Q[i] = pd.qcut((rr["c"] / rr["pop"]).reindex(rege["region_id"].values).rank(method="first"), NB, labels=False).values
gap = 0.02; bh = (1 - (NB - 1) * gap) / NB
def yb(j): return j * (bh + gap)
nodw = 0.05
qcols = ["#fdd9a0", "#fdae61", "#f46d43", "#c0392b", "#7a0177"]
def draw_alluvial(ax):
    def ribbon(x0, x1, ys0, ys1, yt0, yt1, color):
        xm = (x0 + x1) / 2
        verts = [(x0, ys0), (xm, ys0), (xm, yt0), (x1, yt0), (x1, yt1), (xm, yt1), (xm, ys1), (x0, ys1), (x0, ys0)]
        codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.CLOSEPOLY]
        ax.add_patch(mpatches.PathPatch(Path(verts, codes), fc=color, ec="none", alpha=0.62, zorder=1))
    for t in range(len(PERIODS) - 1):
        Mt = np.zeros((NB, NB))
        for (i, j), v in Q.groupby([t, t + 1]).size().items(): Mt[int(i), int(j)] = v
        ni = Mt.sum(axis=1); nj = Mt.sum(axis=0)
        x0 = t + nodw / 2; x1 = (t + 1) - nodw / 2
        soff = {i: yb(i) for i in range(NB)}; toff = {j: yb(j) for j in range(NB)}
        for i in range(NB):
            for j in range(NB):
                cc = Mt[i, j]
                if cc == 0: continue
                hs = bh * cc / ni[i]; ht = bh * cc / nj[j]
                ys0 = soff[i]; ys1 = ys0 + hs; soff[i] = ys1
                yt0 = toff[j]; yt1 = yt0 + ht; toff[j] = yt1
                ribbon(x0, x1, ys0, ys1, yt0, yt1, qcols[i])
    for t in range(len(PERIODS)):
        for j in range(NB):
            ax.add_patch(mpatches.Rectangle((t - nodw / 2, yb(j)), nodw, bh, fc="#33373b", ec="none", zorder=3))
        ax.text(t, -0.075, PLAB[t], ha="center", va="top", fontsize=9, fontweight="bold", clip_on=False)
    ql = ["Q1 (lowest)", "Q2", "Q3", "Q4", "Q5 (highest)"]
    for j in range(NB):
        ax.text(-0.06, yb(j) + bh / 2, ql[j], ha="right", va="center", fontsize=8, color=qcols[j] if j != 0 else "#c8922f", fontweight="bold", clip_on=False)
    ax.text(3.0, 1.045, "ribbon colour = incidence quintile at the start of each step",
            ha="right", va="bottom", fontsize=8, style="italic", color="#666", clip_on=False)
    ax.set_xlim(-0.03, 3.03); ax.set_ylim(-0.02, 1.02); ax.axis("off")

# ================= FIGURE =================
fig, AX = plt.subplots(1, 3, figsize=(17, 5.0), gridspec_kw={"width_ratios": [1, 1, 1.55]})
plt.subplots_adjust(left=0.05, right=0.985, top=0.9, bottom=0.16, wspace=0.28)

# (a) concentration per period
a = AX[0]; xp = list(range(len(PERIODS)))
for ln, _, col, lab in OUTC: a.plot(xp, SH[ln], "o-", color=col, lw=2.4, ms=7, label=lab)
a.set_xticks(xp); a.set_xticklabels(PLAB, fontsize=9); a.set_ylim(0, max(max(SH[l]) for l in SH) * 1.35)
a.set_xlabel("3-year period"); a.set_ylabel("% of events in top 20% of population\n(de-noised, cross-fit)")
a.legend(fontsize=9.5, title="Outcome", title_fontsize=9.5); a.grid(alpha=0.35, color=GRIDCLR)
a.spines[["top", "right"]].set_visible(False)
a.set_title("(a)", loc="left", fontsize=13, fontweight="bold")

# (b) out-of-sample prediction bars (no descriptive title)
b = AX[1]; x = np.arange(len(RES)); w = 0.36
capR = [r["capR"] * 100 for r in RES]; capC = [r["capC"] * 100 for r in RES]
b.bar(x - w / 2, capR, w, color=INC, label="Hotspots from old data", zorder=3)
b.bar(x + w / 2, capC, w, color="#b0b6ba", label="Best possible (current data)", zorder=3)
b.axhline(20, ls=":", lw=1.1, color="#333")
b.text(1.5, 21, "no targeting (20%)", va="bottom", ha="center", fontsize=8, color="#555")
for xi, v in zip(x - w / 2, capR): b.text(xi, v + 1, f"{v:.0f}", ha="center", fontsize=9, fontweight="bold")
for xi, v in zip(x + w / 2, capC): b.text(xi, v + 1, f"{v:.0f}", ha="center", fontsize=9, color="#555")
def _sh(rng_):
    a, bb = rng_.split("-"); return f"{a}\u2013{bb[2:]}"
b.set_xticks(x)
b.set_xticklabels([f"{_sh(r['tr'])}\n\u2193\n{_sh(r['te'])}" for r in RES], fontsize=9)
b.set_ylabel("Test-period cases captured (%)\ntop 20% of population"); b.set_ylim(0, 62)
b.grid(axis="y", lw=.5, color=GRIDCLR, zorder=0); b.legend(fontsize=9, loc="upper right")
b.spines[["top", "right"]].set_visible(False)
b.set_title("(b)", loc="left", fontsize=13, fontweight="bold")

# (c) alluvial
c = AX[2]; draw_alluvial(c)
_pos = c.get_position()
fig.text(_pos.x0 - 0.008, _pos.y1 + 0.015, "(c)", fontsize=13, fontweight="bold", va="bottom", ha="left")

fig.savefig(f"{OUT}/Figure5_temporal_oos.png", dpi=300, bbox_inches="tight", facecolor="white")
print(f"saved {OUT}/Figure5_temporal_oos.png")
