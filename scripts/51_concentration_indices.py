"""Concentration (Lorenz/Gini) of TB cases vs adverse outcomes across SP units.

Parallels the incidence Lorenz: rank geographic units by the per-capita rate of
each event, then plot cumulative % of events vs cumulative % of population.
Reports the Gini index and the share captured by the top 20% of population.

Events: notified cases | TB deaths | treatment abandonment | (all-cause death).
Input : /tmp/outcome_units.csv  (per-unit pop, n_cases, n_death_tb, n_death_ntb, n_aband)
Output: /tmp/fig_concentration_lorenz.png
"""
import pandas as pd, numpy as np, matplotlib, matplotlib.pyplot as plt
matplotlib.rcParams.update({"font.family": "sans-serif", "font.size": 11})

MIN_CASES = 10   # restrict to units with a meaningful TB denominator
u_all = pd.read_csv("/tmp/outcome_units.csv")
u_all["n_death_all"] = u_all["n_death_tb"] + u_all["n_death_ntb"]
u = u_all[u_all["n_cases"] >= MIN_CASES].copy()   # eligible pool (same as hotspots)
print(f"Restricted to units with >={MIN_CASES} cases: {len(u)}/{len(u_all)} units | "
      f"{u['pop'].sum()/u_all['pop'].sum()*100:.0f}% of population | "
      f"{u['n_cases'].sum()/u_all['n_cases'].sum()*100:.0f}% of cases\n")

def lorenz(df, val):
    d = df[["pop", val]].copy()
    d = d[d["pop"] > 0]
    d["rate"] = d[val] / d["pop"]
    d = d.sort_values("rate", ascending=False)
    cum_pop = np.concatenate([[0], (d["pop"].cumsum() / d["pop"].sum()).values])
    cum_val = np.concatenate([[0], (d[val].cumsum() / d[val].sum()).values])
    gini = 2 * np.trapz(cum_val, cum_pop) - 1
    top20 = np.interp(0.20, cum_pop, cum_val) * 100
    return cum_pop, cum_val, gini, top20

# transparency: all-units vs restricted
print("Effect of restriction on Gini (all units → ≥10 cases):")
for val, name, _, _ in [("n_cases","cases","",""),("n_death_tb","TB deaths","",""),("n_aband","abandonment","","")]:
    g_all = lorenz(u_all, val)[2]; g_res = lorenz(u, val)[2]
    print(f"  {name:<14} {g_all:.3f} → {g_res:.3f}")
print()

METRICS = [
    ("n_cases",     "Notified TB cases",        "#1a3d5c", "-"),
    ("n_death_tb",  "TB deaths",                "#c0392b", "-"),
    ("n_aband",     "Treatment abandonment",    "#1f77b4", "-"),
]

print(f"{'Event':<26}{'N events':>10}{'Gini':>8}{'Top 20% pop →':>16}")
print("-"*60)
fig, ax = plt.subplots(figsize=(8.2, 7.4))
ax.plot([0,1],[0,1], ls="--", color="#999999", lw=1.2, label="Line of equality")
ax.axvline(0.20, color="#666", ls=":", lw=1.2, zorder=1)
results = {}
for val, name, col, ls in METRICS:
    x, y, gini, top20 = lorenz(u, val)
    results[val] = (gini, top20)
    ax.plot(x, y, color=col, lw=2.4, ls=ls, label=f"{name}  (Gini {gini:.3f})", zorder=3)
    ax.scatter([0.20], [top20/100], color=col, s=45, zorder=4)
    print(f"{name:<26}{int(u[val].sum()):>10,}{gini:>8.3f}{top20:>14.1f}%")

# all-cause death reported in text only
_, _, gini_all, top20_all = lorenz(u, "n_death_all")
print(f"{'(All-cause death, sens.)':<26}{int(u['n_death_all'].sum()):>10,}{gini_all:>8.3f}{top20_all:>14.1f}%")

# annotate top-20% readouts
txt = "\n".join([f"{name.split('(')[0].strip()}: {results[val][1]:.0f}%"
                 for val, name, _, _ in METRICS])
ax.annotate("Top 20% of population →\n" + txt, xy=(0.20, results["n_cases"][1]/100),
            xytext=(0.30, 0.30), fontsize=10, color="#222",
            bbox=dict(boxstyle="round,pad=0.4", fc="#f4f6f8", ec="#cccccc"))
ax.set_xlim(0,1); ax.set_ylim(0,1)
ax.set_xlabel("Cumulative share of population\n(units ranked highest → lowest event rate)")
ax.set_ylabel("Cumulative share of events")
ax.set_title("Geographic concentration of TB cases vs adverse outcomes\n"
             "São Paulo state, 2013–2024 · adults ≥15  ·  units with ≥10 cases",
             fontsize=12.5, fontweight="bold")
ax.legend(loc="lower right", fontsize=10, framealpha=0.95)
ax.set_aspect("equal")
plt.tight_layout(); plt.savefig("/tmp/fig_concentration_lorenz.png", dpi=150, bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_concentration_lorenz.png")
