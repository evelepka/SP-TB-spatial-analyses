"""De-noised concentration of LTFU as a proportion of evaluated episodes, crude and
age-standardised, using one consistent implementation.

Age standardisation follows the supplementary methods (indirect, state-internal reference): indirect standardisation against the state
population as internal reference, eight adult age bands, LTFU expressed as the
age-adjusted proportion of evaluated episodes (observed/expected x crude state proportion).
"""
import numpy as np, pandas as pd

AN = "/DATA_ROOT/Data/analytic"
reg = pd.read_csv(f"{AN}/region_units.csv", dtype={"region_id": str})
co = pd.read_csv(f"{AN}/region_cases.csv", dtype={"region_id": str})
pv = reg.set_index("region_id")["pop"]
units = list(pv.index); idx = {u: i for i, u in enumerate(units)}
K = len(units); popv = pv.values; GRID = np.linspace(0, 1, 101)

BANDS = [15, 20, 25, 30, 40, 50, 60, 70, 200]
ev = co[co["eval"] == 1].copy()
ev["ri"] = ev["region_id"].map(idx)
ev = ev.dropna(subset=["ri"]); ev["ri"] = ev["ri"].astype(int)
ev["band"] = pd.cut(ev["age"], bins=BANDS, right=False, labels=False)
ev = ev.dropna(subset=["band"]); ev["band"] = ev["band"].astype(int)
NB = ev["band"].max() + 1

ri = ev["ri"].values
bd = ev["band"].values
ab = (ev["aband"] == 1).values.astype(float)
state_p = ab.mean()
# state-wide age-specific LTFU proportion (internal reference)
ref_by_band = np.array([ab[bd == b].mean() for b in range(NB)])


def curve(mode, B=1000, seed=20240625):
    """mode='crude'  -> rank by LTFU/evaluated
       mode='agestd' -> rank by indirectly standardised LTFU proportion"""
    rs = np.random.RandomState(seed)
    acc = np.zeros(len(GRID)); m = 0
    for _ in range(B):
        h = rs.rand(len(ri)) < 0.5
        for sel in (h, ~h):
            oth = ~sel
            den = np.bincount(ri[sel], minlength=K).astype(float)
            num = np.bincount(ri[sel], weights=ab[sel], minlength=K).astype(float)
            vl = np.bincount(ri[oth], weights=ab[oth], minlength=K).astype(float)
            if vl.sum() == 0:
                continue
            if mode == "crude":
                rate = np.where(den > 0, num / np.maximum(den, 1), -1.0)
            else:
                # expected LTFU per region under state age-specific proportions
                exp = np.zeros(K)
                for b in range(NB):
                    mb = sel & (bd == b)
                    exp += np.bincount(ri[mb], minlength=K).astype(float) * ref_by_band[b]
                smr = np.where(exp > 0, num / np.maximum(exp, 1e-9), np.nan)
                rate = np.where(den > 0, smr * state_p, -1.0)
                rate = np.nan_to_num(rate, nan=-1.0)
            o = np.argsort(-rate)
            cp = np.cumsum(popv[o]) / popv.sum()
            cv = np.cumsum(vl[o]) / vl.sum()
            acc += np.interp(GRID, cp, cv); m += 1
    return acc / m


print("LTFU as a proportion of evaluated episodes, de-noised (split-sample cross-fitting)")
print(f"  evaluated episodes used: {len(ev):,}   state LTFU proportion: {state_p*100:.2f}%")
print()
for mode, label in [("crude", "crude"), ("agestd", "age-standardised")]:
    c = curve(mode)
    top20 = np.interp(0.20, GRID, c) * 100
    gini = 2 * np.trapz(c, GRID) - 1
    print(f"  {label:17s}: top-20% share {top20:5.2f}%   Gini {gini:.3f}"
          f"   -> reported as {top20:.0f}% / {gini:.2f}")
print()
