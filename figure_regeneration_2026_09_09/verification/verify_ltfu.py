"""Reproduce the LTFU concentration series for figure 5a under both definitions:
   (i) per capita  -> LTFU events / adult population   (supplement only)
   (ii) per evaluated episode -> LTFU / evaluated      (primary basis, what build_fig5.py plots)
Also reproduce the pooled top-20% shares reported in the Results.
"""
import numpy as np, pandas as pd

AN = "/DATA_ROOT/Data/analytic"
reg = pd.read_csv(f"{AN}/region_units.csv", dtype={"region_id": str})[["region_id", "pop", "n"]]
reg = reg[reg["pop"] > 0]
co = pd.read_csv(f"{AN}/region_cases.csv", dtype={"region_id": str})
pv = reg.set_index("region_id")["pop"]
units = list(pv.index); idx = {u: i for i, u in enumerate(units)}
K = len(units); popv = pv.values; TOT = popv.sum()
co["ri"] = co["region_id"].map(idx)
co = co.dropna(subset=["ri"]); co["ri"] = co["ri"].astype(int)

PERIODS = [(2013, 2015), (2016, 2018), (2019, 2021), (2022, 2024)]
PLAB = ["2013-15", "2016-18", "2019-21", "2022-24"]
rs = np.random.RandomState(20240625)


def share_percap(ri, B=150, q=0.20):
    """Rank by events/pop; measure share of held-out events in top q of population."""
    if len(ri) < 50:
        return np.nan
    out = []
    for _ in range(B):
        h = rs.rand(len(ri)) < 0.5
        a = np.bincount(ri[h], minlength=K).astype(float)
        b = np.bincount(ri[~h], minlength=K).astype(float)
        for rk, vl in [(a, b), (b, a)]:
            if vl.sum() == 0:
                continue
            ra = rk / popv
            o = np.argsort(-ra)
            cp = np.cumsum(popv[o]) / TOT
            cv = np.cumsum(vl[o]) / vl.sum()
            out.append(np.interp(q, cp, cv) * 100)
    return float(np.mean(out))


def share_proportion(sub, B=150, q=0.20):
    """Rank by LTFU/evaluated (split-sample); measure share of held-out LTFU events
    in regions comprising the top q of ADULT POPULATION."""
    ev = sub[sub["eval"] == 1]
    if ev["aband"].sum() < 50:
        return np.nan
    ri = ev["ri"].values
    ab = (ev["aband"] == 1).values.astype(float)
    out = []
    for _ in range(B):
        h = rs.rand(len(ri)) < 0.5
        for sel in (h, ~h):
            oth = ~sel
            den_r = np.bincount(ri[sel], minlength=K).astype(float)
            num_r = np.bincount(ri[sel], weights=ab[sel], minlength=K).astype(float)
            vl = np.bincount(ri[oth], weights=ab[oth], minlength=K).astype(float)
            if vl.sum() == 0:
                continue
            with np.errstate(invalid="ignore", divide="ignore"):
                prop = np.where(den_r > 0, num_r / den_r, -1.0)
            o = np.argsort(-prop)
            cp = np.cumsum(popv[o]) / TOT
            cv = np.cumsum(vl[o]) / vl.sum()
            out.append(np.interp(q, cp, cv) * 100)
    return float(np.mean(out))


print("MANUSCRIPT fig5a: notifications 43-44%, mortality 38->33%, LTFU 37->26%")
print("MANUSCRIPT pooled: notif 45%, mortality 39%, LTFU 24% (per episode), 42% Gini per capita\n")

print("--- per-period, LTFU per capita (supplementary basis) ---")
pc = [share_percap(co[(co.year.between(*p)) & (co["aband"] == 1)]["ri"].values) for p in PERIODS]
print("  LTFU per capita      :", [round(x) for x in pc])

print("--- per-period, LTFU PER EVALUATED EPISODE (primary basis) ---")
pe = [share_proportion(co[co.year.between(*p)]) for p in PERIODS]
print("  LTFU per episode     :", [round(x) for x in pe])

print("\n--- per-period notifications / mortality (for reference) ---")
inc = [share_percap(co[co.year.between(*p)]["ri"].values) for p in PERIODS]
mort = [share_percap(co[(co.year.between(*p)) & (co["death"] == 1)]["ri"].values) for p in PERIODS]
print("  notifications        :", [round(x) for x in inc])
print("  mortality            :", [round(x) for x in mort])

print("\n--- POOLED (all years) ---")
print(f"  notifications        : {share_percap(co['ri'].values):.1f}%")
print(f"  mortality            : {share_percap(co[co['death']==1]['ri'].values):.1f}%")
print(f"  LTFU per capita      : {share_percap(co[co['aband']==1]['ri'].values):.1f}%")
print(f"  LTFU per episode     : {share_proportion(co):.1f}%")
