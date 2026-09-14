"""Adaptive units with minimum CASES threshold applied to the selection pool.

A small bairro with 507/100k and 17 cases over 5 years IS operationally relevant
— you want to send an ACF team there precisely because of the concentration.
Filtering by minimum cases (not population) is the right operational criterion:
it directly answers "is there enough TB burden here to justify an ACF program?"

For each combination of (FCU_MIN_POP, MIN_CASES_5YR):
  - Named FCUs ≥ FCU_MIN_POP → standalone FCU unit
  - All other sectors → bairro/distrito unit
  - Only units with n_cases ≥ MIN_CASES_5YR are eligible for hotspot selection
  - Select top eligible units by pooled TB rate until 20% of TOTAL pop is covered
  - Metrics: cases%, TB rate, Jaccard stability, unit size distribution
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL = "3550308"
BAIXADA = {"3506359","3513504","3518701","3522109","3531100","3537602","3541000","3548500","3551009"}

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s

# ── 1. Sector base ─────────────────────────────────────────────────────────────
print("Loading data...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]   = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)
agg = pd.read_csv(
    f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
    sep=";", encoding="latin-1", decimal=",",
    usecols=["CD_SETOR","v0001"], dtype={"CD_SETOR": str}, low_memory=False,
)
agg["v0001"] = pd.to_numeric(agg["v0001"], errors="coerce").fillna(0)
GSP = set(sec22[sec22["NM_CONCURB"]=="São Paulo/SP"]["CD_MUN"].unique())
ALL_MUNIS = GSP | BAIXADA
sec = sec22[sec22["CD_MUN"].isin(ALL_MUNIS)].merge(agg, on="CD_SETOR", how="left")
sec_res = sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["v0001"]>=100)].copy()
sec_res["pop"] = sec_res["v0001"]
sec_res["is_fcu"] = sec_res["NM_FCU"].notna().astype(int)
sec_res["bairro_unit"] = sec_res.apply(
    lambda r: f"dist_{r['CD_DIST']}" if str(r["CD_MUN"])==CAPITAL
              else (f"bairro_{r['CD_MUN']}_{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"dist_{r['CD_DIST']}"), axis=1)
sec_res["bairro_label"] = sec_res.apply(
    lambda r: f"SP/{r['NM_DIST']}" if str(r["CD_MUN"])==CAPITAL
              else (f"{r['NM_MUN']}/{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"{r['NM_MUN']}/{r['NM_DIST']}"), axis=1)

TOTAL_POP = sec_res["pop"].sum()
fcu_pop_by_name = sec_res[sec_res["is_fcu"]==1].groupby("NM_FCU")["pop"].sum()

# ── 2. Cases with year ─────────────────────────────────────────────────────────
print("Loading cases...")
gsp_co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False, dtype={"sinan_clean":str})
gsp_co["CD_SETOR"] = gsp_co["setor_cnefe"].apply(norm_setor)
bx_co  = pd.read_csv("/tmp/cohort_baixada_with_cnefe_v2.csv", low_memory=False, dtype={"sinan_clean":str})
bx_co["match_tier"] = bx_co["cnefe_match"].astype(str).str.extract(r"^(T\d)")
bx_co  = bx_co[bx_co["match_tier"].isin(["T1","T2","T3"])]
bx_co["CD_SETOR"] = bx_co["setor_cnefe"].apply(norm_setor)

cohort_full = pd.read_csv(f"{SPATIAL}/cohort_with_spatial.csv",
                          usecols=["sinan_clean","notification_date"], low_memory=False,
                          dtype={"sinan_clean":str})
cohort_full["year"] = pd.to_datetime(cohort_full["notification_date"], errors="coerce").dt.year
yr_map = (cohort_full.dropna(subset=["sinan_clean","year"])
          .drop_duplicates("sinan_clean").set_index("sinan_clean")["year"].to_dict())

all_co = pd.concat([gsp_co[["sinan_clean","CD_SETOR"]],
                    bx_co[["sinan_clean","CD_SETOR"]]], ignore_index=True).dropna(subset=["CD_SETOR"])
all_co["year"] = all_co["sinan_clean"].map(yr_map)
all_co = all_co[all_co["year"].between(2020, 2024)]
TOTAL_CASES = len(all_co)
print(f"  Pop: {TOTAL_POP/1e6:.2f}M  |  Cases: {TOTAL_CASES:,}")

# ── 3. Run strategy ────────────────────────────────────────────────────────────
def run(fcu_min_pop, min_cases, label, pct_window=0.20):
    qualified_fcus = set(fcu_pop_by_name[fcu_pop_by_name >= fcu_min_pop].index) if fcu_min_pop else set()

    def assign(row):
        nm = row["NM_FCU"]
        if pd.notna(nm) and nm in qualified_fcus:
            return f"fcu__{nm}", nm, "FCU"
        return row["bairro_unit"], row["bairro_label"], "bairro"

    tmp = sec_res[["CD_SETOR","NM_FCU","bairro_unit","bairro_label","pop"]].copy()
    asgn = tmp.apply(assign, axis=1, result_type="expand")
    asgn.columns = ["unit_id","label_u","unit_type"]
    tmp = pd.concat([tmp, asgn], axis=1)
    sec2unit = tmp.set_index("CD_SETOR")["unit_id"].to_dict()

    unit_pop = tmp.groupby("unit_id").agg(
        pop=("pop","sum"), label=("label_u","first"), unit_type=("unit_type","first")
    ).reset_index()

    all_co["unit_id"] = all_co["CD_SETOR"].map(sec2unit)
    cases = all_co.dropna(subset=["unit_id"]).groupby("unit_id").size().rename("n_cases").reset_index()
    unit_df = unit_pop.merge(cases, on="unit_id", how="left")
    unit_df["n_cases"] = unit_df["n_cases"].fillna(0)
    unit_df["rate"]    = unit_df["n_cases"] / (unit_df["pop"] * 5) * 1e5

    # Filter selection pool by minimum cases
    eligible = unit_df[unit_df["n_cases"] >= min_cases].copy()
    inelig_cases = unit_df[unit_df["n_cases"] < min_cases]["n_cases"].sum()

    # Select top units until 20% of TOTAL pop covered
    el_sorted = eligible.sort_values("rate", ascending=False).copy()
    el_sorted["cum_pop"] = el_sorted["pop"].cumsum()
    target = TOTAL_POP * pct_window
    mask = el_sorted["cum_pop"] <= target
    if mask.sum() < len(el_sorted):
        mask.iloc[mask.sum()] = True
    sel = el_sorted[mask]

    # Jaccard
    jacs = []
    for ya, yb in zip([2020,2021,2022,2023],[2021,2022,2023,2024]):
        sets = []
        for yr in [ya, yb]:
            yc = (all_co[all_co["year"]==yr].dropna(subset=["unit_id"])
                  .groupby("unit_id").size().rename("n").reset_index())
            yd = eligible[["unit_id","pop"]].merge(yc, on="unit_id", how="left")
            yd["n"] = yd["n"].fillna(0)
            yd = yd[yd["n"] >= min_cases]   # apply same min_cases to year-specific
            yd["rate_yr"] = yd["n"] / yd["pop"] * 1e5
            ys = yd.sort_values("rate_yr", ascending=False).copy()
            ys["cum"] = ys["pop"].cumsum()
            m = ys["cum"] <= target
            if m.sum() < len(ys): m.iloc[m.sum()] = True
            sets.append(set(ys[m]["unit_id"]))
        i = sets[0] & sets[1]; u = sets[0] | sets[1]
        jacs.append(len(i)/len(u) if u else 0)

    return {
        "label":             label,
        "fcu_min_pop":       fcu_min_pop,
        "min_cases":         min_cases,
        "n_eligible":        len(eligible),
        "n_selected":        len(sel),
        "n_sel_fcu":         int((sel["unit_type"]=="FCU").sum()),
        "n_sel_bairro":      int((sel["unit_type"]=="bairro").sum()),
        "sel_pop_M":         round(sel["pop"].sum()/1e6, 2),
        "sel_pct_pop":       round(sel["pop"].sum()/TOTAL_POP*100, 1),
        "sel_pct_cases":     round(sel["n_cases"].sum()/TOTAL_CASES*100, 1),
        "sel_rate":          round(sel["n_cases"].sum()/(sel["pop"].sum()*5)*1e5, 0),
        "median_sel_pop":    int(sel["pop"].median()),
        "min_sel_pop":       int(sel["pop"].min()),
        "min_sel_cases":     int(sel["n_cases"].min()),
        "max_sel_rate":      round(sel["rate"].max(), 0),
        "jaccard_mean":      round(np.mean(jacs), 3),
        "jaccard_detail":    [round(j,3) for j in jacs],
        "_sel":              sel,
        "_unit_df":          unit_df,
    }

# ── 4. Define scenarios ────────────────────────────────────────────────────────
# FCU min pop = 5000 throughout (large enough to be standalone operational unit)
FCU_MIN = 5000

scenarios = [
    # label,                            fcu_min, min_cases
    ("Baseline (no filter)",            0,       0),
    ("Bairro only, ≥5 cases",           0,       5),
    ("Bairro only, ≥10 cases",          0,      10),
    ("Adaptive FCU≥5k, ≥5 cases",   FCU_MIN,    5),
    ("Adaptive FCU≥5k, ≥10 cases",  FCU_MIN,   10),
    ("Adaptive FCU≥5k, ≥15 cases",  FCU_MIN,   15),
    ("Adaptive FCU≥5k, ≥20 cases",  FCU_MIN,   20),
]

print("\nRunning scenarios...")
results = []
for lbl, fcu_min, mc in scenarios:
    print(f"  {lbl}...", end=" ", flush=True)
    r = run(fcu_min, mc, lbl)
    results.append(r)
    print(f"eligible={r['n_eligible']}, sel={r['n_selected']} "
          f"({r['n_sel_fcu']}FCU+{r['n_sel_bairro']}B), "
          f"cases={r['sel_pct_cases']:.1f}%, rate={r['sel_rate']:.0f}, "
          f"Jac={r['jaccard_mean']:.3f}, minCases={r['min_sel_cases']}")

# ── 5. Print table ─────────────────────────────────────────────────────────────
print("\n" + "="*130)
print(f"{'Strategy':<35} {'Elig':>6} {'Sel':>5} {'(F+B)':>8} "
      f"{'Pop%':>6} {'Cases%':>7} {'Rate':>6} {'Jac':>6} "
      f"{'MedPop':>8} {'MinPop':>8} {'MinCas':>7} {'MaxRate':>8}")
print("-"*130)
for r in results:
    mix = f"({r['n_sel_fcu']}F+{r['n_sel_bairro']}B)"
    print(f"{r['label']:<35} {r['n_eligible']:>6} {r['n_selected']:>5} {mix:>8} "
          f"{r['sel_pct_pop']:>5.1f}% {r['sel_pct_cases']:>6.1f}% {r['sel_rate']:>6.0f} "
          f"{r['jaccard_mean']:>6.3f} {r['median_sel_pop']:>8,} {r['min_sel_pop']:>8,} "
          f"{r['min_sel_cases']:>7} {r['max_sel_rate']:>8.0f}")

print()
print("Jaccard detail (2020→21, 21→22, 22→23, 23→24):")
for r in results:
    print(f"  {r['label']:<35}: {r['jaccard_detail']}")

# ── 6. Show top 20 for recommended scenario ───────────────────────────────────
rec = next(r for r in results if "≥10" in r["label"] and "FCU" in r["label"])
print(f"\n=== Top 25 selected units: {rec['label']} ===")
top = rec["_sel"].nlargest(25,"rate")[["label","unit_type","pop","n_cases","rate"]]
print(top.to_string(index=False))

print(f"\n=== Bottom 10 selected units (lowest rate): {rec['label']} ===")
bot = rec["_sel"].nsmallest(10,"rate")[["label","unit_type","pop","n_cases","rate"]]
print(bot.to_string(index=False))

# Distribution of selected unit sizes
print(f"\n=== Size distribution of SELECTED units: {rec['label']} ===")
sel = rec["_sel"]
for thr in [500, 1000, 2000, 5000, 10000, 20000]:
    n = (sel["pop"] < thr).sum()
    print(f"  < {thr:,} pop: {n} units ({n/len(sel)*100:.1f}%)")

# ── 7. Plot ───────────────────────────────────────────────────────────────────
# Key scenarios for plot
plot_labels = [
    "Baseline (no filter)",
    "Bairro only, ≥5 cases",
    "Adaptive FCU≥5k, ≥5 cases",
    "Adaptive FCU≥5k, ≥10 cases",
    "Adaptive FCU≥5k, ≥15 cases",
    "Adaptive FCU≥5k, ≥20 cases",
]
plot_res = [r for r in results if r["label"] in plot_labels]

short = ["No filter", "Bairro\n≥5 cases", "Adaptive\n≥5 cases",
         "Adaptive\n≥10 cases", "Adaptive\n≥15 cases", "Adaptive\n≥20 cases"]
cols = ["#95a5a6","#3498db","#e67e22","#27ae60","#1a3d5c","#c0392b"]

fig, axes = plt.subplots(1, 4, figsize=(22, 6))
fig.suptitle("Adaptive units — minimum cases threshold (instead of population)\n"
             "GSP + Baixada Santista · FCU ≥5k standalone · 20% pop window",
             fontsize=13, fontweight="bold")

def bar_panel(ax, values, title, ylabel, baseline_idx=0, fmt="{:.1f}", ylim_pad=1.2, annotate_extra=None):
    bars = ax.bar(short, values, color=cols, edgecolor="white", lw=0.8)
    ax.axhline(values[baseline_idx], color="#95a5a6", ls="--", lw=1.5)
    for bar, v in zip(bars, values):
        label = fmt.format(v)
        ax.text(bar.get_x()+bar.get_width()/2, v + (max(values)-min(values))*0.03,
                label, ha="center", fontsize=9, fontweight="bold")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_ylim(min(values)*0.85, max(values)*ylim_pad)
    ax.grid(axis="y", alpha=0.3)
    for tick in ax.get_xticklabels():
        tick.set_rotation(20); tick.set_ha("right")

bar_panel(axes[0],
          [r["sel_pct_cases"] for r in plot_res],
          "A) Case concentration\n(% of cases in 20% pop window)",
          "% of geocoded TB cases", fmt="{:.1f}%")

bar_panel(axes[1],
          [r["jaccard_mean"] for r in plot_res],
          "B) Year-to-year stability\n(Jaccard index)",
          "Mean Jaccard (2020–2024)", fmt="{:.3f}", ylim_pad=1.15)

bar_panel(axes[2],
          [r["n_selected"] for r in plot_res],
          "C) Number of selected units",
          "Units selected", fmt="{:.0f}", ylim_pad=1.2)

bar_panel(axes[3],
          [r["median_sel_pop"] for r in plot_res],
          "D) Median size of selected units\n(population)",
          "Median unit population", fmt="{:,.0f}", ylim_pad=1.2)

plt.tight_layout()
plt.savefig("/tmp/adaptive_mincases_comparison.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("\nSaved: /tmp/adaptive_mincases_comparison.png")

# Save summary
pd.DataFrame([{k:v for k,v in r.items() if not k.startswith("_")} for r in results]
             ).to_csv("/tmp/adaptive_mincases_summary.csv", index=False)
print("Saved: /tmp/adaptive_mincases_summary.csv")
print("Done.")
