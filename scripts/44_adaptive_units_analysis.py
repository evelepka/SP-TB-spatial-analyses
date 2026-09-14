"""Adaptive geographic unit analysis.

For each minimum-population threshold (1k, 2k, 5k, 10k):
  - Named FCUs ≥ MIN_POP → standalone FCU units
  - All other sectors (non-FCU OR in small FCUs) → aggregate to bairro/distrito
  - Units are ranked by pooled 5-yr TB rate; top 20% population window selected
  - Metrics: case concentration, TB rate, unit count, size distribution, Jaccard stability

Compares to baseline: pure bairro (current approach).
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
WHO_DATA = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/Data"
CAPITAL  = "3550308"
BAIXADA  = {"3506359","3513504","3518701","3522109","3531100","3537602","3541000","3548500","3551009"}

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s

# ── 1. Sector base table ────────────────────────────────────────────────────
print("Loading shapefiles and population...")
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

# Base hybrid-bairro unit (for fallback)
sec_res["bairro_unit"] = sec_res.apply(
    lambda r: f"dist_{r['CD_DIST']}" if str(r["CD_MUN"])==CAPITAL
              else (f"bairro_{r['CD_MUN']}_{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"dist_{r['CD_DIST']}"), axis=1)
sec_res["bairro_label"] = sec_res.apply(
    lambda r: f"SP/{r['NM_DIST']}" if str(r["CD_MUN"])==CAPITAL
              else (f"{r['NM_MUN']}/{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"{r['NM_MUN']}/{r['NM_DIST']}"), axis=1)

TOTAL_POP = sec_res["pop"].sum()
print(f"  Residential sectors: {len(sec_res):,}  Total pop: {TOTAL_POP/1e6:.2f}M")

# FCU population per named FCU
fcu_pop_by_name = sec_res[sec_res["is_fcu"]==1].groupby("NM_FCU")["pop"].sum()

# ── 2. Geocoded cases with year ─────────────────────────────────────────────
print("Loading geocoded cases + year...")
gsp_co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False, dtype={"sinan_clean":str})
gsp_co["CD_SETOR"] = gsp_co["setor_cnefe"].apply(norm_setor)

bx_co = pd.read_csv("/tmp/cohort_baixada_with_cnefe_v2.csv", low_memory=False, dtype={"sinan_clean":str})
bx_co["match_tier"] = bx_co["cnefe_match"].astype(str).str.extract(r"^(T\d)")
bx_co = bx_co[bx_co["match_tier"].isin(["T1","T2","T3"])]
bx_co["CD_SETOR"] = bx_co["setor_cnefe"].apply(norm_setor)

# Join year from original cohort
cohort_full = pd.read_csv(f"{SPATIAL}/cohort_with_spatial.csv",
                          usecols=["sinan_clean","notification_date"], low_memory=False,
                          dtype={"sinan_clean":str})
cohort_full["year"] = pd.to_datetime(cohort_full["notification_date"], errors="coerce").dt.year
yr_map = cohort_full.dropna(subset=["sinan_clean","year"]).drop_duplicates("sinan_clean").set_index("sinan_clean")["year"].to_dict()

all_co = pd.concat([
    gsp_co[["sinan_clean","CD_SETOR"]],
    bx_co[["sinan_clean","CD_SETOR"]]
], ignore_index=True).dropna(subset=["CD_SETOR"])
all_co["year"] = all_co["sinan_clean"].map(yr_map)
all_co = all_co[all_co["year"].between(2020, 2024)]

# FCU name per sector
sec2fcu    = sec_res.set_index("CD_SETOR")["NM_FCU"].to_dict()
sec2bairro = sec_res.set_index("CD_SETOR")["bairro_unit"].to_dict()
sec2blabel = sec_res.set_index("CD_SETOR")["bairro_label"].to_dict()
all_co["nm_fcu"]      = all_co["CD_SETOR"].map(sec2fcu)
all_co["bairro_unit"] = all_co["CD_SETOR"].map(sec2bairro)

TOTAL_CASES = len(all_co)
print(f"  Geocoded cases 2020-2024: {TOTAL_CASES:,}")

# ── 3. Build adaptive units for a given MIN_POP ──────────────────────────────
def build_adaptive_units(min_pop):
    """
    Returns:
      units_df — one row per unit with: unit_id, label, pop, n_cases, rate
      case_unit_map — dict sinan_clean -> unit_id (for year-by-year Jaccard)
      sec_to_unit — dict CD_SETOR -> unit_id
    """
    # Which FCU names qualify as standalone units?
    qualified_fcus = set(fcu_pop_by_name[fcu_pop_by_name >= min_pop].index)

    def assign_unit(row):
        nm_fcu = row["NM_FCU"]
        if pd.notna(nm_fcu) and nm_fcu in qualified_fcus:
            return f"fcu__{nm_fcu}", nm_fcu, "FCU"
        else:
            return row["bairro_unit"], row["bairro_label"], "bairro"

    tmp = sec_res[["CD_SETOR","NM_FCU","bairro_unit","bairro_label","pop"]].copy()
    assigned = tmp.apply(assign_unit, axis=1, result_type="expand")
    assigned.columns = ["unit_id","label","unit_type"]
    tmp = pd.concat([tmp, assigned], axis=1)

    sec_to_unit = tmp.set_index("CD_SETOR")["unit_id"].to_dict()

    unit_pop = tmp.groupby("unit_id").agg(
        pop=("pop","sum"),
        label=("label","first"),
        unit_type=("unit_type","first"),
    ).reset_index()

    # Cases per unit (pooled)
    all_co["unit_id"] = all_co["CD_SETOR"].map(sec_to_unit)
    cases_by_unit = all_co.dropna(subset=["unit_id"]).groupby("unit_id").size().rename("n_cases").reset_index()
    unit_df = unit_pop.merge(cases_by_unit, on="unit_id", how="left")
    unit_df["n_cases"] = unit_df["n_cases"].fillna(0)
    unit_df["rate"]    = unit_df["n_cases"] / (unit_df["pop"] * 5) * 1e5

    return unit_df, sec_to_unit

def jaccard_stability(unit_df, sec_to_unit, pct_window=0.20):
    """Year-to-year Jaccard at fixed pop% window."""
    # Rank by rate (use pooled), pick hotspot units
    unit_sorted = unit_df.sort_values("rate", ascending=False).copy()
    unit_sorted["cum_pop"] = unit_sorted["pop"].cumsum()
    target = TOTAL_POP * pct_window
    mask = unit_sorted["cum_pop"] <= target
    mask.iloc[mask.sum()] = True

    # For each year pair, pick hotspot by year-specific rate
    jaccards = []
    years = [2020,2021,2022,2023,2024]
    all_co["unit_id"] = all_co["CD_SETOR"].map(sec_to_unit)
    for ya, yb in zip(years[:-1], years[1:]):
        for yr, tag in [(ya,"a"),(yb,"b")]:
            yr_cases = all_co[all_co["year"]==yr].dropna(subset=["unit_id"]).groupby("unit_id").size().rename("n").reset_index()
            yr_df = unit_df[["unit_id","pop"]].merge(yr_cases, on="unit_id", how="left")
            yr_df["n"] = yr_df["n"].fillna(0)
            yr_df["rate_yr"] = yr_df["n"] / (yr_df["pop"]) * 1e5
            yr_sorted = yr_df.sort_values("rate_yr", ascending=False).copy()
            yr_sorted["cum_pop"] = yr_sorted["pop"].cumsum()
            yr_mask = yr_sorted["cum_pop"] <= target
            yr_mask.iloc[yr_mask.sum()] = True
            if tag=="a": set_a = set(yr_sorted[yr_mask]["unit_id"])
            else:         set_b = set(yr_sorted[yr_mask]["unit_id"])
        inter = set_a & set_b
        union = set_a | set_b
        jaccards.append(len(inter)/len(union) if union else 0)
    return jaccards

def summarise_strategy(unit_df, label, pct_window=0.20, min_pop_unit=None):
    unit_sorted = unit_df.sort_values("rate", ascending=False).copy()
    unit_sorted["cum_pop"] = unit_sorted["pop"].cumsum()
    target = TOTAL_POP * pct_window
    mask = unit_sorted["cum_pop"] <= target
    mask.iloc[mask.sum()] = True
    sel = unit_sorted[mask]
    n_fcu   = (sel["unit_type"]=="FCU").sum()   if "unit_type" in sel.columns else 0
    n_bairro= (sel["unit_type"]=="bairro").sum() if "unit_type" in sel.columns else len(sel)
    return {
        "label": label,
        "total_units":       len(unit_df),
        "n_selected":        len(sel),
        "n_selected_fcu":    int(n_fcu),
        "n_selected_bairro": int(n_bairro),
        "sel_pop_M":         round(sel["pop"].sum()/1e6,2),
        "sel_pct_pop":       round(sel["pop"].sum()/TOTAL_POP*100,1),
        "sel_cases":         int(sel["n_cases"].sum()),
        "sel_pct_cases":     round(sel["n_cases"].sum()/TOTAL_CASES*100,1),
        "sel_rate":          round(sel["n_cases"].sum()/(sel["pop"].sum()*5)*1e5,0),
        "median_unit_pop":   int(unit_df["pop"].median()),
        "p10_unit_pop":      int(unit_df["pop"].quantile(0.10)),
        "pct_units_lt2k":    round((unit_df["pop"]<2000).mean()*100,1),
        "pct_units_lt5k":    round((unit_df["pop"]<5000).mean()*100,1),
    }

# ── 4. Run for each threshold ────────────────────────────────────────────────
print("\nBuilding adaptive units and computing metrics...")

THRESHOLDS = [
    ("Pure bairro", None),       # baseline — no FCU splitting
    ("Adaptive ≥1k", 1000),
    ("Adaptive ≥2k", 2000),
    ("Adaptive ≥5k", 5000),
    ("Adaptive ≥10k", 10000),
]

# Pure bairro baseline
bairro_unit_df = (sec_res.groupby("bairro_unit").agg(
    pop=("pop","sum"), label=("bairro_label","first")).reset_index()
    .rename(columns={"bairro_unit":"unit_id"}))
bairro_unit_df["unit_type"] = "bairro"
all_co["unit_id"] = all_co["bairro_unit"]
bairro_cases = all_co.dropna(subset=["unit_id"]).groupby("unit_id").size().rename("n_cases").reset_index()
bairro_unit_df = bairro_unit_df.merge(bairro_cases, on="unit_id", how="left")
bairro_unit_df["n_cases"] = bairro_unit_df["n_cases"].fillna(0)
bairro_unit_df["rate"]    = bairro_unit_df["n_cases"] / (bairro_unit_df["pop"] * 5) * 1e5
sec_to_bairro = sec_res.set_index("CD_SETOR")["bairro_unit"].to_dict()

results = []
unit_dfs = {}
sec_to_units = {}

for lbl, min_pop in THRESHOLDS:
    print(f"  {lbl}...", end=" ", flush=True)
    if min_pop is None:
        udf = bairro_unit_df.copy()
        s2u = sec_to_bairro.copy()
    else:
        udf, s2u = build_adaptive_units(min_pop)
    unit_dfs[lbl]   = udf
    sec_to_units[lbl] = s2u

    summary = summarise_strategy(udf, lbl)
    # Jaccard
    jacs = jaccard_stability(udf, s2u)
    summary["jaccard_mean"]   = round(np.mean(jacs), 3)
    summary["jaccard_detail"] = [round(j,3) for j in jacs]
    results.append(summary)
    print(f"done ({len(udf)} units, {summary['n_selected']} selected, "
          f"{summary['sel_pct_cases']:.1f}% cases, Jaccard {summary['jaccard_mean']:.3f})")

# ── 5. Print summary table ───────────────────────────────────────────────────
print("\n" + "="*120)
print(f"{'Strategy':<22} {'Tot units':>10} {'Selected':>9} {'(FCU+bairro)':>13} "
      f"{'Pop%':>6} {'Cases%':>7} {'Rate':>6} {'Jaccard':>8} {'Med unit':>9} {'<2k%':>6} {'<5k%':>6}")
print("-"*120)
for r in results:
    mix = f"({r['n_selected_fcu']}FCU+{r['n_selected_bairro']}bairro)"
    print(f"{r['label']:<22} {r['total_units']:>10,} {r['n_selected']:>9} {mix:>13} "
          f"{r['sel_pct_pop']:>5.1f}% {r['sel_pct_cases']:>6.1f}% {r['sel_rate']:>6.0f} "
          f"{r['jaccard_mean']:>8.3f} {r['median_unit_pop']:>9,} {r['pct_units_lt2k']:>5.1f}% {r['pct_units_lt5k']:>5.1f}%")
print()
print("Jaccard detail (2020→21, 21→22, 22→23, 23→24):")
for r in results:
    print(f"  {r['label']:<22}: {r['jaccard_detail']}")

# ── 6. Top units for Adaptive ≥5k to show what changed ──────────────────────
print("\n=== TOP SELECTED UNITS in Adaptive ≥5k (first 30) ===")
udf5k, s2u5k = unit_dfs["Adaptive ≥5k"], sec_to_units["Adaptive ≥5k"]
u5k_sorted = udf5k.sort_values("rate", ascending=False).copy()
u5k_sorted["cum_pop"] = u5k_sorted["pop"].cumsum()
target = TOTAL_POP * 0.20
mask5k = u5k_sorted["cum_pop"] <= target
mask5k.iloc[mask5k.sum()] = True
sel5k = u5k_sorted[mask5k].head(30)
print(sel5k[["label","unit_type","pop","n_cases","rate"]].to_string(index=False))

# Show Vila Andrade in adaptive unit
print("\n=== Vila Andrade + Paraisópolis in Adaptive ≥5k ===")
va_para = udf5k[udf5k["label"].str.contains("Vila Andrade|Paraisópolis|PARAISO", case=False, na=False)]
print(va_para[["unit_id","label","unit_type","pop","n_cases","rate"]].to_string(index=False))

# ── 7. Plots ─────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(18, 12))
fig.suptitle("Adaptive geographic units — GSP + Baixada Santista (2020–2024)\n"
             "Hybrid FCU/bairro targeting vs pure bairro baseline",
             fontsize=14, fontweight="bold")

labels  = [r["label"]  for r in results]
cases   = [r["sel_pct_cases"] for r in results]
rates   = [r["sel_rate"]      for r in results]
jaccards= [r["jaccard_mean"]  for r in results]
n_units = [r["total_units"]   for r in results]
colors  = ["#7f8c8d","#e74c3c","#e67e22","#27ae60","#2980b9"]

# Panel A: % cases in 20% pop window
ax = axes[0,0]
bars = ax.bar(labels, cases, color=colors, edgecolor="white", linewidth=0.8)
ax.axhline(cases[0], color="#7f8c8d", linestyle="--", lw=1.5, label=f"Baseline: {cases[0]:.1f}%")
for bar, v in zip(bars, cases):
    ax.text(bar.get_x()+bar.get_width()/2, v+0.2, f"{v:.1f}%", ha="center", fontsize=11, fontweight="bold")
ax.set_ylabel("% of all TB cases in selected units", fontsize=11)
ax.set_title("A) Case concentration\n(top-20% population window)", fontsize=11, fontweight="bold")
ax.set_ylim(30, max(cases)*1.15)
ax.legend(fontsize=10)
ax.grid(axis="y", alpha=0.3)
for tick in ax.get_xticklabels(): tick.set_rotation(20); tick.set_ha("right")

# Panel B: TB rate of selected units
ax = axes[0,1]
bars = ax.bar(labels, rates, color=colors, edgecolor="white", linewidth=0.8)
ax.axhline(rates[0], color="#7f8c8d", linestyle="--", lw=1.5, label=f"Baseline: {rates[0]:.0f}/100k")
for bar, v in zip(bars, rates):
    ax.text(bar.get_x()+bar.get_width()/2, v+0.5, f"{v:.0f}", ha="center", fontsize=11, fontweight="bold")
ax.set_ylabel("TB rate /100k·yr (pop-weighted mean)", fontsize=11)
ax.set_title("B) TB rate of selected units\n(higher = more concentrated targeting)", fontsize=11, fontweight="bold")
ax.set_ylim(60, max(rates)*1.2)
ax.legend(fontsize=10)
ax.grid(axis="y", alpha=0.3)
for tick in ax.get_xticklabels(): tick.set_rotation(20); tick.set_ha("right")

# Panel C: Jaccard stability
ax = axes[1,0]
bars = ax.bar(labels, jaccards, color=colors, edgecolor="white", linewidth=0.8)
ax.axhline(jaccards[0], color="#7f8c8d", linestyle="--", lw=1.5, label=f"Baseline: {jaccards[0]:.3f}")
for bar, v in zip(bars, jaccards):
    ax.text(bar.get_x()+bar.get_width()/2, v+0.003, f"{v:.3f}", ha="center", fontsize=11, fontweight="bold")
ax.set_ylabel("Mean year-to-year Jaccard (2020–2024)", fontsize=11)
ax.set_title("C) Year-to-year stability\n(higher = more consistent targeting)", fontsize=11, fontweight="bold")
ax.set_ylim(0, max(jaccards)*1.25)
ax.legend(fontsize=10)
ax.grid(axis="y", alpha=0.3)
for tick in ax.get_xticklabels(): tick.set_rotation(20); tick.set_ha("right")

# Panel D: Unit size distribution for each strategy (violin/box)
ax = axes[1,1]
data_for_box = []
box_labels   = []
for lbl, _ in THRESHOLDS:
    udf = unit_dfs[lbl]
    data_for_box.append(udf["pop"].clip(upper=50000).values)
    box_labels.append(lbl)

bp = ax.boxplot(data_for_box, labels=box_labels, patch_artist=True,
                medianprops=dict(color="black",lw=2), showfliers=False)
for patch, color in zip(bp["boxes"], colors):
    patch.set_facecolor(color); patch.set_alpha(0.7)

ax.axhline(2000, color="#c0392b", linestyle="--", lw=1.5, label="2,000 (ACF min)")
ax.axhline(5000, color="#27ae60", linestyle="--", lw=1.5, label="5,000 (ACF viable)")
ax.set_ylabel("Unit population (capped at 50k for display)", fontsize=11)
ax.set_title("D) Unit size distribution\n(box = IQR, line = median)", fontsize=11, fontweight="bold")
ax.legend(fontsize=10)
ax.grid(axis="y", alpha=0.3)
for tick in ax.get_xticklabels(): tick.set_rotation(20); tick.set_ha("right")

plt.tight_layout()
plt.savefig("/tmp/adaptive_units_comparison.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("\nSaved: /tmp/adaptive_units_comparison.png")

# ── 8. Save summary CSV ──────────────────────────────────────────────────────
pd.DataFrame(results).to_csv("/tmp/adaptive_units_summary.csv", index=False)
print("Saved: /tmp/adaptive_units_summary.csv")
print("\nDone.")
