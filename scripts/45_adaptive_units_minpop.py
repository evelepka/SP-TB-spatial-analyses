"""Adaptive units with minimum population threshold applied to the SELECTION POOL.

For each combination of (FCU_MIN, SELECTION_MIN):
  - Named FCUs ≥ FCU_MIN → standalone FCU unit
  - All other sectors → bairro/distrito unit
  - ONLY units with pop ≥ SELECTION_MIN are eligible for hotspot selection
  - Select top units by pooled TB rate until 20% of TOTAL regional pop is covered
  - Report: n units eligible, n selected, % cases, TB rate, Jaccard

Key fix over previous script: the minimum size applies uniformly to all units,
preventing small-number noise from tiny bairros (e.g. Santos/Paquetá, pop=671)
from inflating concentration metrics.
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL = "3550308"
BAIXADA = {"3506359","3513504","3518701","3522109","3531100","3537602","3541000","3548500","3551009"}

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s

# ── 1. Sector base ────────────────────────────────────────────────────────────
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

# ── 2. Cases with year ────────────────────────────────────────────────────────
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
print(f"  Total pop: {TOTAL_POP/1e6:.2f}M  |  Geocoded cases 2020-2024: {TOTAL_CASES:,}")

# ── 3. Core function ──────────────────────────────────────────────────────────
def run_strategy(fcu_min, sel_min, label, pct_window=0.20):
    """
    fcu_min   : minimum FCU pop to qualify as a standalone FCU unit
    sel_min   : minimum unit pop to be ELIGIBLE for selection (applies to all units)
    """
    qualified_fcus = set(fcu_pop_by_name[fcu_pop_by_name >= fcu_min].index) if fcu_min else set()

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

    # Apply SELECTION minimum — units below sel_min are ineligible
    total_units     = len(unit_df)
    eligible        = unit_df[unit_df["pop"] >= sel_min].copy()
    ineligible_pop  = unit_df[unit_df["pop"] <  sel_min]["pop"].sum()
    ineligible_cases= unit_df[unit_df["pop"] <  sel_min]["n_cases"].sum()

    # Select top eligible units until 20% of TOTAL pop
    eligible_sorted = eligible.sort_values("rate", ascending=False).copy()
    eligible_sorted["cum_pop"] = eligible_sorted["pop"].cumsum()
    target = TOTAL_POP * pct_window
    mask = eligible_sorted["cum_pop"] <= target
    if mask.sum() < len(eligible_sorted):
        mask.iloc[mask.sum()] = True
    sel = eligible_sorted[mask]

    # Jaccard: year-by-year
    jaccards = []
    for ya, yb in zip([2020,2021,2022,2023],[2021,2022,2023,2024]):
        sets = []
        for yr in [ya, yb]:
            yr_cases = (all_co[all_co["year"]==yr].dropna(subset=["unit_id"])
                        .groupby("unit_id").size().rename("n").reset_index())
            yr_df = eligible[["unit_id","pop"]].merge(yr_cases, on="unit_id", how="left")
            yr_df["n"] = yr_df["n"].fillna(0)
            yr_df["rate_yr"] = yr_df["n"] / yr_df["pop"] * 1e5
            yr_sorted = yr_df.sort_values("rate_yr", ascending=False).copy()
            yr_sorted["cum"] = yr_sorted["pop"].cumsum()
            m = yr_sorted["cum"] <= target
            m.iloc[m.sum()] = True
            sets.append(set(yr_sorted[m]["unit_id"]))
        inter = sets[0] & sets[1]
        union = sets[0] | sets[1]
        jaccards.append(len(inter)/len(union) if union else 0)

    n_fcu_sel    = int((sel["unit_type"]=="FCU").sum())
    n_bairro_sel = int((sel["unit_type"]=="bairro").sum())
    med_sel_pop  = int(sel["pop"].median())
    min_sel_pop  = int(sel["pop"].min())

    return {
        "label":           label,
        "fcu_min":         fcu_min,
        "sel_min":         sel_min,
        "total_units":     total_units,
        "n_eligible":      len(eligible),
        "n_selected":      len(sel),
        "n_sel_fcu":       n_fcu_sel,
        "n_sel_bairro":    n_bairro_sel,
        "sel_pop_M":       round(sel["pop"].sum()/1e6, 2),
        "sel_pct_pop":     round(sel["pop"].sum()/TOTAL_POP*100, 1),
        "sel_cases":       int(sel["n_cases"].sum()),
        "sel_pct_cases":   round(sel["n_cases"].sum()/TOTAL_CASES*100, 1),
        "sel_rate":        round(sel["n_cases"].sum()/(sel["pop"].sum()*5)*1e5, 0) if sel["pop"].sum()>0 else 0,
        "median_sel_pop":  med_sel_pop,
        "min_sel_pop":     min_sel_pop,
        "jaccard_mean":    round(np.mean(jaccards), 3),
        "jaccard_detail":  [round(j,3) for j in jaccards],
        "ineligible_pop_pct": round(ineligible_pop/TOTAL_POP*100, 1),
        "ineligible_cases_pct": round(ineligible_cases/TOTAL_CASES*100, 1),
        # save for top-units inspection
        "_sel_df":         sel,
        "_eligible":       eligible,
        "_sec2unit":       sec2unit,
    }

# ── 4. Run strategies ─────────────────────────────────────────────────────────
print("\nRunning strategies...")

strategies = [
    # label,                          fcu_min, sel_min
    ("Baseline: pure bairro, no min",       0,    0),
    ("Pure bairro ≥2k",                     0, 2000),
    ("Pure bairro ≥5k",                     0, 5000),
    ("Adaptive FCU≥2k, sel≥2k",          2000, 2000),
    ("Adaptive FCU≥2k, sel≥5k",          2000, 5000),
    ("Adaptive FCU≥5k, sel≥2k",          5000, 2000),
    ("Adaptive FCU≥5k, sel≥5k",          5000, 5000),
]

results = []
for lbl, fcu_min, sel_min in strategies:
    print(f"  {lbl}...", end=" ", flush=True)
    r = run_strategy(fcu_min, sel_min, lbl)
    results.append(r)
    print(f"eligible={r['n_eligible']}, selected={r['n_selected']} "
          f"({r['n_sel_fcu']}FCU+{r['n_sel_bairro']}bairro), "
          f"cases={r['sel_pct_cases']:.1f}%, rate={r['sel_rate']:.0f}, "
          f"Jaccard={r['jaccard_mean']:.3f}, minUnitPop={r['min_sel_pop']:,}")

# ── 5. Print table ────────────────────────────────────────────────────────────
print("\n" + "="*140)
hdr = (f"{'Strategy':<35} {'Eligible':>9} {'Selected':>9} {'(FCU+B)':>10} "
       f"{'Pop%':>6} {'Cases%':>7} {'Rate':>6} {'Jaccard':>8} "
       f"{'Med sel':>8} {'Min sel':>8} {'Inelig%':>8}")
print(hdr)
print("-"*140)
for r in results:
    mix = f"({r['n_sel_fcu']}F+{r['n_sel_bairro']}B)"
    inelig = f"{r['ineligible_pop_pct']:.1f}%pop"
    print(f"{r['label']:<35} {r['n_eligible']:>9,} {r['n_selected']:>9} {mix:>10} "
          f"{r['sel_pct_pop']:>5.1f}% {r['sel_pct_cases']:>6.1f}% {r['sel_rate']:>6.0f} "
          f"{r['jaccard_mean']:>8.3f} {r['median_sel_pop']:>8,} {r['min_sel_pop']:>8,} {inelig:>8}")

print()
print("Jaccard detail (2020→21, 21→22, 22→23, 23→24):")
for r in results:
    print(f"  {r['label']:<35}: {r['jaccard_detail']}")

# ── 6. Show top selected units for key strategies ─────────────────────────────
for lbl in ["Pure bairro ≥2k", "Adaptive FCU≥5k, sel≥2k"]:
    r = next(x for x in results if x["label"]==lbl)
    print(f"\n=== Top 20 selected units: {lbl} ===")
    top = r["_sel_df"].nlargest(20,"rate")[["label","unit_type","pop","n_cases","rate"]]
    print(top.to_string(index=False))

# ── 7. Plot ───────────────────────────────────────────────────────────────────
# Exclude the private keys before saving
save_cols = ["label","fcu_min","sel_min","total_units","n_eligible","n_selected",
             "n_sel_fcu","n_sel_bairro","sel_pop_M","sel_pct_pop","sel_cases",
             "sel_pct_cases","sel_rate","median_sel_pop","min_sel_pop",
             "jaccard_mean","jaccard_detail","ineligible_pop_pct","ineligible_cases_pct"]
pd.DataFrame([{k:v for k,v in r.items() if not k.startswith("_")} for r in results]
             ).to_csv("/tmp/adaptive_minpop_summary.csv", index=False)

# Plotting: compare key strategies
plot_strats = ["Baseline: pure bairro, no min", "Pure bairro ≥2k", "Pure bairro ≥5k",
               "Adaptive FCU≥5k, sel≥2k", "Adaptive FCU≥5k, sel≥5k"]
plot_res = [r for r in results if r["label"] in plot_strats]

fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle("Adaptive units with minimum population threshold\nGSP + Baixada Santista · 20% pop window",
             fontsize=13, fontweight="bold")

colors = ["#95a5a6","#3498db","#1a3d5c","#e67e22","#c0392b"]
short_labels = ["Bairro\n(no min)", "Bairro\n≥2k", "Bairro\n≥5k", "Adaptive\nFCU≥5k+≥2k", "Adaptive\nFCU≥5k+≥5k"]
cases_pct  = [r["sel_pct_cases"]    for r in plot_res]
rates      = [r["sel_rate"]         for r in plot_res]
jaccards   = [r["jaccard_mean"]     for r in plot_res]
n_sel      = [r["n_selected"]       for r in plot_res]
med_pop    = [r["median_sel_pop"]   for r in plot_res]
min_pop    = [r["min_sel_pop"]      for r in plot_res]

# Panel A: cases%
ax = axes[0]
bars = ax.bar(short_labels, cases_pct, color=colors, edgecolor="white", lw=0.8)
ax.axhline(cases_pct[0], color="#95a5a6", ls="--", lw=1.5)
for bar, v, n in zip(bars, cases_pct, n_sel):
    ax.text(bar.get_x()+bar.get_width()/2, v+0.15, f"{v:.1f}%\n({n} units)",
            ha="center", fontsize=9.5, fontweight="bold")
ax.set_ylim(25, max(cases_pct)*1.18)
ax.set_ylabel("% of all TB cases captured", fontsize=11)
ax.set_title("A) Case concentration\n(top 20% pop)", fontsize=11, fontweight="bold")
ax.grid(axis="y", alpha=0.3)

# Panel B: Jaccard
ax = axes[1]
bars = ax.bar(short_labels, jaccards, color=colors, edgecolor="white", lw=0.8)
ax.axhline(jaccards[0], color="#95a5a6", ls="--", lw=1.5)
for bar, v in zip(bars, jaccards):
    ax.text(bar.get_x()+bar.get_width()/2, v+0.005, f"{v:.3f}",
            ha="center", fontsize=10, fontweight="bold")
ax.set_ylim(0.35, max(jaccards)*1.15)
ax.set_ylabel("Year-to-year Jaccard (stability)", fontsize=11)
ax.set_title("B) Targeting stability\n(higher = more consistent year to year)", fontsize=11, fontweight="bold")
ax.grid(axis="y", alpha=0.3)

# Panel C: selected unit size (median and min)
ax = axes[2]
x = np.arange(len(plot_res))
w = 0.35
bars_med = ax.bar(x - w/2, med_pop, w, color=colors, alpha=0.85, edgecolor="white", label="Median")
bars_min = ax.bar(x + w/2, min_pop, w, color=colors, alpha=0.45, edgecolor=colors, linewidth=1.5, label="Min")
ax.axhline(2000, color="#e67e22", ls="--", lw=1.5, label="2,000 (ACF min)")
ax.axhline(5000, color="#27ae60", ls="--", lw=1.5, label="5,000 (ACF viable)")
for bar, v in zip(bars_med, med_pop):
    ax.text(bar.get_x()+bar.get_width()/2, v+100, f"{v:,.0f}", ha="center", fontsize=8.5, fontweight="bold")
for bar, v in zip(bars_min, min_pop):
    ax.text(bar.get_x()+bar.get_width()/2, v+100, f"{v:,.0f}", ha="center", fontsize=8.5, color="#555")
ax.set_xticks(x); ax.set_xticklabels(short_labels, fontsize=9)
ax.set_ylabel("Population of selected units", fontsize=11)
ax.set_title("C) Selected unit size\n(solid=median, faded=minimum)", fontsize=11, fontweight="bold")
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3)
ax.set_ylim(0, max(med_pop)*1.2)

plt.tight_layout()
plt.savefig("/tmp/adaptive_minpop_comparison.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("\nSaved: /tmp/adaptive_minpop_comparison.png")
print("Done.")
