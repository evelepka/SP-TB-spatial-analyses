"""Try implementation variants for the LTFU (per-evaluated-episode) concentration series,
looking for the one that reproduces the manuscript's pooled 24% and per-period 37->26%."""
import numpy as np, pandas as pd

AN = "/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/analytic"
reg = pd.read_csv(f"{AN}/region_units.csv", dtype={"region_id": str})
reg = reg[reg["pop"] > 0]
co = pd.read_csv(f"{AN}/region_cases.csv", dtype={"region_id": str})
pv = reg.set_index("region_id")["pop"]
units = list(pv.index); idx = {u: i for i, u in enumerate(units)}
K = len(units); popv = pv.values; TOT = popv.sum()
co["ri"] = co["region_id"].map(idx); co = co.dropna(subset=["ri"]); co["ri"] = co["ri"].astype(int)
PERIODS = [(2013, 2015), (2016, 2018), (2019, 2021), (2022, 2024)]


def series(weight, B=150, q=0.20, minev=0):
    """weight: 'pop' -> accumulate share of adult population;
               'ep'  -> accumulate share of evaluated episodes."""
    rs = np.random.RandomState(20240625)
    out_all = []
    for p in [None] + PERIODS:
        sub = co if p is None else co[co.year.between(*p)]
        ev = sub[sub["eval"] == 1]
        ri = ev["ri"].values; ab = (ev["aband"] == 1).values.astype(float)
        vals = []
        for _ in range(B):
            h = rs.rand(len(ri)) < 0.5
            for sel in (h, ~h):
                oth = ~sel
                den = np.bincount(ri[sel], minlength=K).astype(float)
                num = np.bincount(ri[sel], weights=ab[sel], minlength=K).astype(float)
                vl = np.bincount(ri[oth], weights=ab[oth], minlength=K).astype(float)
                if vl.sum() == 0:
                    continue
                prop = np.where(den > minev, num / np.maximum(den, 1), -1.0)
                o = np.argsort(-prop)
                w = popv[o] if weight == "pop" else np.bincount(ri, minlength=K).astype(float)[o]
                cp = np.cumsum(w) / w.sum()
                cv = np.cumsum(vl[o]) / vl.sum()
                vals.append(np.interp(q, cp, cv) * 100)
        out_all.append(float(np.mean(vals)))
    return out_all


print("TARGET: pooled 24%, periods 37 -> 26\n")
for weight in ("pop", "ep"):
    for minev in (0, 5, 10):
        r = series(weight, minev=minev)
        print(f"  weight={weight:3s} min-episodes={minev:2d} -> pooled {r[0]:4.1f}%  "
              f"periods {[round(x) for x in r[1:]]}")
