import numpy as np, pandas as pd

AN = "/DATA_ROOT/SP-TB-spatial-analyses/Data/analytic"
reg = pd.read_csv(f"{AN}/region_units.csv", dtype={"region_id": str})
T = 12
rng = np.random.default_rng(20260718)

def qassign(df, by, ascending):
    o = df.sort_values(by, ascending=ascending); cum = o["pop"].cumsum() / o["pop"].sum()
    q = np.ceil(np.clip(cum.values, 1e-9, 1) * 5).astype(int).clip(1, 5)
    return pd.Series(q, index=o.index).reindex(df.index)

def paf_point(df, col, by, ascending):
    df = df.dropna(subset=[col, by]).copy(); df = df[df["pop"] > 0].reset_index(drop=True)
    df["q"] = qassign(df, by, ascending); py = df["pop"] * T
    obs = (df[col] * py / 1e5).sum()
    ref = (df.loc[df.q == 1, col] * df.loc[df.q == 1, "pop"]).sum() / df.loc[df.q == 1, "pop"].sum()
    exp = (ref * py / 1e5).sum()
    rates = [(df.loc[df.q == qi, col] * df.loc[df.q == qi, "pop"]).sum() / df.loc[df.q == qi, "pop"].sum()
             for qi in range(1, 6)]
    return dict(paf=(obs-exp)/obs*100, excess=obs-exp, ref=ref, rates=rates, obs=obs, n=len(df))

def paf_ci(df, col, by, ascending, B=400):
    df = df.dropna(subset=[col, by]).copy(); df = df[df["pop"] > 0].reset_index(drop=True)
    ix = df.index.values; out = []
    for _ in range(B):
        b = df.loc[rng.choice(ix, len(ix), replace=True)].reset_index(drop=True)
        b["q"] = qassign(b, by, ascending); py = b["pop"] * T
        obs = (b[col] * py / 1e5).sum()
        ref = (b.loc[b.q == 1, col] * b.loc[b.q == 1, "pop"]).sum() / b.loc[b.q == 1, "pop"].sum()
        exp = (ref * py / 1e5).sum(); out.append((obs-exp)/obs*100)
    return np.percentile(out, [2.5, 97.5])

ge10 = reg[reg["n"] >= 10]

print("MANUSCRIPT CLAIMS: fig2d 65% (63-67), ~119,700 excess cases")
print("                   fig3b 34% (30-39), ~62,600 excess cases; gradient 33 -> 69")
print("                   fig3c 28% (22-34), ~2,500 excess deaths;  gradient 1.8 -> 3.1")
print()

CASES = [
    ("fig2d geo-inequality, notif", "inc_adj",    "inc_adj", True,  reg,  "all regions (NA-dropped => >=10)"),
    ("fig2d geo-inequality, notif", "inc_crude",  "inc_crude", True, reg,  "ALL regions incl <10"),
    ("fig2d geo-inequality, notif", "inc_crude",  "inc_crude", True, ge10, ">=10-case regions"),
    ("fig3b income, notifications", "inc_adj",    "income", False, reg,  "all regions (NA-dropped => >=10)"),
    ("fig3b income, notifications", "inc_crude",  "income", False, reg,  "ALL regions incl <10"),
    ("fig3b income, notifications", "inc_crude",  "income", False, ge10, ">=10-case regions"),
    ("fig3c income, mortality",     "drate_adj",  "income", False, reg,  "all regions (NA-dropped => >=10)"),
    ("fig3c income, mortality",     "drate_crude","income", False, reg,  "ALL regions incl <10"),
    ("fig3c income, mortality",     "drate_crude","income", False, ge10, ">=10-case regions"),
]

for label, col, by, asc, frame, note in CASES:
    r = paf_point(frame, col, by, asc)
    ci = paf_ci(frame, col, by, asc)
    grad = f"{r['rates'][0]:.1f} -> {r['rates'][4]:.1f}"
    kind = "ADJ " if "adj" in col else "CRUDE"
    print(f"{label:30s} {kind} {note:34s} PAF {r['paf']:5.1f}% "
          f"({ci[0]:.0f}-{ci[1]:.0f})  excess {r['excess']:>9,.0f}  grad {grad:>14s}  n={r['n']}")
