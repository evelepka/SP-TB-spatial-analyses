"""Hotspot window sensitivity analysis — GSP + Baixada Santista.

Evaluates window sizes (1%–25% of population) on three criteria:
  1. Concentration  — % TB cases captured per window
  2. Stability      — mean pairwise Jaccard of hotspot sets across years 2020–2024
  3. Operability    — spatial cluster count and size distribution

Output: /tmp/window_sensitivity.csv + window_sensitivity_plot.png
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Patch
import zipfile, io, unicodedata, re
from scipy.ndimage import label as scipy_label

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
WINDOWS = [0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.25]

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s

# ---- 1) Shapefile ----
print("Loading shapefile...")
GSP_MUNIS = None
BX_MUNIS = {"3506359","3513504","3518701","3522109","3531100","3537602","3541000","3548500","3551009"}
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"] = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)
sec22["AREA_KM2"] = pd.to_numeric(sec22["AREA_KM2"], errors="coerce")
GSP_MUNIS = set(sec22[sec22["NM_CONCURB"] == "São Paulo/SP"]["CD_MUN"].unique())

# ---- 2) Census aggregates ----
print("Loading census aggregates...")
agg = pd.read_csv(
    f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
    sep=";", encoding="latin-1", decimal=",",
    usecols=["CD_SETOR","v0001"],
    dtype={"CD_SETOR": str}, low_memory=False,
)
agg["v0001"] = pd.to_numeric(agg["v0001"], errors="coerce").fillna(0)

# ---- 3) Cases with year ----
print("Loading cases with year...")
# GSP cohort
gsp_co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False, dtype={"sinan_clean": str})
gsp_co["key"] = gsp_co["sinan_clean"].str.zfill(7)
gsp_co["CD_SETOR"] = gsp_co["setor_cnefe"].apply(norm_setor)

# Get year from cohort_with_spatial.csv
spatial_yr = pd.read_csv(
    f"{SPATIAL}/cohort_with_spatial.csv",
    usecols=["sinan_clean","notification_date"],
    dtype={"sinan_clean": str}, low_memory=False
)
spatial_yr["key"] = spatial_yr["sinan_clean"].str.strip()
spatial_yr["year"] = pd.to_datetime(spatial_yr["notification_date"], errors="coerce").dt.year
# Keep first match per key, prefer 2020-2024
spatial_yr = spatial_yr[spatial_yr["year"].between(2020,2024)]
spatial_yr = spatial_yr.drop_duplicates("key", keep="first")[["key","year"]]

gsp_co = gsp_co.merge(spatial_yr, on="key", how="left")
# Fallback: any not matched are still 2020-2024 (per script 21 filter), assign 2022 median
gsp_co["year"] = gsp_co["year"].fillna(2022).astype(int)
gsp_cases_yr = gsp_co.dropna(subset=["CD_SETOR"])[["CD_SETOR","year"]].copy()

# Baixada cohort
bx_co = pd.read_csv("/tmp/cohort_baixada_with_cnefe_v2.csv", low_memory=False, dtype={"sinan_clean": str})
bx_co["match_tier"] = bx_co["cnefe_match"].astype(str).str.extract(r"^(T\d)")
bx_co = bx_co[bx_co["match_tier"].isin(["T1","T2","T3"])]
bx_co["key"] = bx_co["sinan_clean"].str.zfill(7)
bx_co["CD_SETOR"] = bx_co["setor_cnefe"].apply(norm_setor)
bx_co = bx_co.merge(spatial_yr, on="key", how="left")
bx_co["year"] = bx_co["year"].fillna(2022).astype(int)
bx_cases_yr = bx_co.dropna(subset=["CD_SETOR"])[["CD_SETOR","year"]].copy()

all_cases_yr = pd.concat([gsp_cases_yr, bx_cases_yr], ignore_index=True)
print(f"  Cases with year: {len(all_cases_yr):,}")
print(f"  Year distribution:\n{all_cases_yr['year'].value_counts().sort_index()}")

# ---- 4) Build sector dataset ----
print("\nBuilding sector dataset...")
sec_all = sec22[sec22["CD_MUN"].isin(GSP_MUNIS | BX_MUNIS)].copy()
sec_all = sec_all.merge(agg, on="CD_SETOR", how="left")
n_cases_total = all_cases_yr.groupby("CD_SETOR").size().rename("n_cases").reset_index()
sec_all = sec_all.merge(n_cases_total, on="CD_SETOR", how="left")
sec_all["n_cases"] = sec_all["n_cases"].fillna(0)
sec_all["density_km2"] = sec_all["v0001"] / sec_all["AREA_KM2"]

# Residential filter
sec_an = sec_all[
    sec_all["CD_TIPO"].astype(str).isin(["0","1"]) &
    (sec_all["v0001"] >= 100)
].copy()
sec_an["rate_per_100k"] = np.where(
    sec_an["v0001"] > 0,
    sec_an["n_cases"] / (sec_an["v0001"] * 5) * 1e5, 0
)
print(f"  Residential sectors: {len(sec_an):,}, total cases: {int(sec_an['n_cases'].sum()):,}")
print(f"  Total population: {int(sec_an['v0001'].sum()):,}")

total_pop = sec_an["v0001"].sum()
total_cases = sec_an["n_cases"].sum()

# ---- 5) Concentration curve (Lorenz) ----
print("\nBuilding concentration curve...")
# Sort sectors by rate descending
sec_sorted = sec_an[sec_an["n_cases"] > 0].sort_values("rate_per_100k", ascending=False).copy()
sec_sorted["cum_pop_pct"] = sec_sorted["v0001"].cumsum() / total_pop
sec_sorted["cum_cases_pct"] = sec_sorted["n_cases"].cumsum() / total_cases

# ---- 6) Stability analysis (Jaccard per year) ----
print("\nComputing year-by-year stability...")
years = sorted(all_cases_yr["year"].unique())
years = [y for y in years if 2020 <= y <= 2024]
print(f"  Years: {years}")

# Cases per sector per year
cases_by_yr = {}
for yr in years:
    yr_cases = all_cases_yr[all_cases_yr["year"] == yr]
    sector_counts = yr_cases.groupby("CD_SETOR").size().rename("n").reset_index()
    # Merge with sector pop
    sc = sec_an[["CD_SETOR","v0001"]].merge(sector_counts, on="CD_SETOR", how="left")
    sc["n"] = sc["n"].fillna(0)
    sc["rate"] = np.where(sc["v0001"] > 0, sc["n"] / (sc["v0001"]) * 1e5, 0)
    cases_by_yr[yr] = sc.set_index("CD_SETOR")

stability_rows = []
for w in WINDOWS:
    jaccards = []
    for i, yr_a in enumerate(years[:-1]):
        yr_b = years[i+1]
        # Hot set for yr_a
        df_a = cases_by_yr[yr_a].copy()
        tot_a = df_a["v0001"].sum()
        inc_a = df_a[df_a["n"] > 0].sort_values("rate", ascending=False)
        inc_a["cum_pop"] = inc_a["v0001"].cumsum()
        hot_a = set(inc_a[inc_a["cum_pop"] <= tot_a * w].index)
        # Hot set for yr_b
        df_b = cases_by_yr[yr_b].copy()
        tot_b = df_b["v0001"].sum()
        inc_b = df_b[df_b["n"] > 0].sort_values("rate", ascending=False)
        inc_b["cum_pop"] = inc_b["v0001"].cumsum()
        hot_b = set(inc_b[inc_b["cum_pop"] <= tot_b * w].index)
        if len(hot_a | hot_b) > 0:
            j = len(hot_a & hot_b) / len(hot_a | hot_b)
            jaccards.append(j)
    stability_rows.append({"window": w, "mean_jaccard": np.mean(jaccards), "jaccards": jaccards})
    print(f"  w={w*100:.0f}%: mean Jaccard={np.mean(jaccards):.3f} "
          f"(year-pairs: {[f'{j:.2f}' for j in jaccards]})")

# ---- 7) Operational cluster analysis (spatial contiguity) ----
print("\nComputing operational cluster sizes...")
# Use projected CRS for adjacency
sec_proj = sec_an.to_crs("EPSG:31983")

cluster_rows = []
for w in WINDOWS:
    # Identify hotspot sectors
    inc = sec_sorted.copy()
    inc_cumm = inc["v0001"].cumsum()
    hot_sectors = set(inc[inc["cum_pop_pct"] <= w]["CD_SETOR"])

    hot_geom = sec_proj[sec_proj["CD_SETOR"].isin(hot_sectors)].copy()
    if len(hot_geom) == 0:
        cluster_rows.append({"window": w, "n_clusters": 0, "median_cluster_pop": 0,
                              "min_cluster_pop": 0, "max_cluster_pop": 0, "pct_clusters_gt5k": 0})
        continue

    # Spatial join to find neighbors (queen contiguity via buffer)
    hot_buf = hot_geom.copy()
    hot_buf["geometry"] = hot_buf.geometry.buffer(10)  # 10m buffer to catch shared edges
    joined = gpd.sjoin(hot_geom[["CD_SETOR","geometry"]],
                       hot_buf[["CD_SETOR","geometry"]].rename(columns={"CD_SETOR":"CD_SETOR_nb"}),
                       how="left", predicate="intersects")
    joined = joined[joined["CD_SETOR"] != joined["CD_SETOR_nb"]]

    # Build adjacency and find connected components via union-find
    sectors = list(hot_sectors)
    idx = {s: i for i, s in enumerate(sectors)}
    parent = list(range(len(sectors)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for _, row in joined.iterrows():
        a, b = row["CD_SETOR"], row["CD_SETOR_nb"]
        if a in idx and b in idx:
            union(idx[a], idx[b])

    # Assign cluster IDs
    hot_geom = hot_geom.copy()
    hot_geom["cluster_id"] = hot_geom["CD_SETOR"].map(lambda s: find(idx[s]))

    cluster_pop = hot_geom.merge(
        sec_an[["CD_SETOR","v0001"]], on="CD_SETOR", how="left", suffixes=("","_pop")
    )
    # Handle duplicate v0001 columns
    v0001_col = "v0001_pop" if "v0001_pop" in cluster_pop.columns else "v0001"
    clust_summary = cluster_pop.groupby("cluster_id")[v0001_col].sum()

    n_clusters = len(clust_summary)
    median_pop = clust_summary.median()
    min_pop = clust_summary.min()
    max_pop = clust_summary.max()
    pct_gt5k = (clust_summary >= 5000).mean() * 100

    cluster_rows.append({
        "window": w,
        "n_clusters": n_clusters,
        "median_cluster_pop": median_pop,
        "min_cluster_pop": min_pop,
        "max_cluster_pop": max_pop,
        "pct_clusters_gt5k": pct_gt5k
    })
    print(f"  w={w*100:.0f}%: {n_clusters} clusters | "
          f"median pop={median_pop:.0f} | ≥5k: {pct_gt5k:.0f}%")

# ---- 8) Summary table ----
print("\n" + "="*90)
print("WINDOW SENSITIVITY SUMMARY")
print("="*90)

summary = []
for w in WINDOWS:
    # Concentration
    mask = sec_sorted["cum_pop_pct"] <= w
    cases_pct = sec_sorted[mask]["n_cases"].sum() / total_cases * 100 if mask.any() else 0
    n_sectors = mask.sum()
    pop_in_window = sec_sorted[mask]["v0001"].sum()
    concentration_ratio = (cases_pct / (w * 100)) if w > 0 else 0

    stab = next((r for r in stability_rows if r["window"] == w), {})
    clust = next((r for r in cluster_rows if r["window"] == w), {})

    row = {
        "window_pct": w * 100,
        "n_sectors": n_sectors,
        "pop_in_window": int(pop_in_window),
        "cases_pct": round(cases_pct, 1),
        "concentration_ratio": round(concentration_ratio, 2),
        "mean_jaccard": round(stab.get("mean_jaccard", 0), 3),
        "n_clusters": int(clust.get("n_clusters", 0)),
        "median_cluster_pop": int(clust.get("median_cluster_pop", 0)),
        "pct_clusters_gt5k": round(clust.get("pct_clusters_gt5k", 0), 0),
    }
    summary.append(row)

df_sum = pd.DataFrame(summary)
print(f"\n{'Win%':>5} {'NSect':>6} {'Pop':>9} {'%Cases':>7} {'ConRatio':>9} "
      f"{'Jaccard':>8} {'NClust':>7} {'MedPop':>8} {'%≥5k':>6}")
print("-" * 90)
for _, r in df_sum.iterrows():
    marker = " ← current" if r["window_pct"] == 5.0 else ""
    print(f"{r['window_pct']:>5.0f}% {r['n_sectors']:>6,} {r['pop_in_window']:>9,} "
          f"{r['cases_pct']:>6.1f}% {r['concentration_ratio']:>8.2f}x "
          f"{r['mean_jaccard']:>8.3f} {r['n_clusters']:>7,} "
          f"{r['median_cluster_pop']:>8,} {r['pct_clusters_gt5k']:>5.0f}%{marker}")

df_sum.to_csv("/tmp/window_sensitivity.csv", index=False)

# ---- 9) Plot ----
print("\nGenerating sensitivity plot...")
fig = plt.figure(figsize=(18, 14))
fig.suptitle("Hotspot Window Sensitivity — GSP + Baixada Santista (2020–2024)",
             fontsize=16, fontweight="bold", y=0.98)

gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.38, wspace=0.32)

wins_pct = [r["window_pct"] for r in summary]
cases_pcts = [r["cases_pct"] for r in summary]
conc_ratios = [r["concentration_ratio"] for r in summary]
jaccards = [r["mean_jaccard"] for r in summary]
n_clusters = [r["n_clusters"] for r in summary]
med_pops = [r["median_cluster_pop"] for r in summary]
pct_5k = [r["pct_clusters_gt5k"] for r in summary]

current_idx = wins_pct.index(5.0)

# Panel A: Lorenz / concentration curve
ax_a = fig.add_subplot(gs[0, 0])
# Full Lorenz curve (all sectors)
lorenz_x = [0] + list(sec_sorted["cum_pop_pct"] * 100) + [100]
lorenz_y = [0] + list(sec_sorted["n_cases"].cumsum() / total_cases * 100) + [100]
ax_a.plot(lorenz_x, lorenz_y, color="#1f4e79", lw=2, label="Concentration curve")
ax_a.plot([0, 100], [0, 100], "--", color="grey", lw=1, label="Diagonal (equal dist.)")
ax_a.axvline(x=5, color="#c0392b", ls=":", lw=1.5, label="5% window (current)")
for w_pct, c_pct in zip(wins_pct, cases_pcts):
    ax_a.scatter(w_pct, c_pct, color="#c0392b", s=60, zorder=5)
    if w_pct in [1, 5, 10, 20]:
        ax_a.annotate(f"{c_pct:.0f}%", (w_pct, c_pct),
                      textcoords="offset points", xytext=(4, 4), fontsize=9)
ax_a.set_xlabel("% Population in window", fontsize=11)
ax_a.set_ylabel("% TB cases captured", fontsize=11)
ax_a.set_title("A) Concentration curve", fontsize=12, fontweight="bold")
ax_a.set_xlim(0, 27); ax_a.set_ylim(0, 100)
ax_a.legend(fontsize=9, loc="lower right")
ax_a.grid(alpha=0.3)

# Panel B: Cases % vs window size (bar)
ax_b = fig.add_subplot(gs[0, 1])
colors_b = ["#c0392b" if w == 5.0 else "#2980b9" for w in wins_pct]
bars = ax_b.bar([f"{w:.0f}%" for w in wins_pct], cases_pcts, color=colors_b, edgecolor="white")
for bar, pct in zip(bars, cases_pcts):
    ax_b.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
              f"{pct:.0f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")
ax_b.set_xlabel("Window size (% population)", fontsize=11)
ax_b.set_ylabel("TB cases captured (%)", fontsize=11)
ax_b.set_title("B) Cases captured per window", fontsize=12, fontweight="bold")
ax_b.set_ylim(0, 105)
ax_b.grid(axis="y", alpha=0.3)
ax_b.legend(handles=[Patch(color="#c0392b", label="Current (5%)"),
                      Patch(color="#2980b9", label="Other windows")], fontsize=9)

# Panel C: Concentration ratio
ax_c = fig.add_subplot(gs[0, 2])
ax_c.plot(wins_pct, conc_ratios, "o-", color="#27ae60", lw=2, ms=8)
ax_c.axvline(x=5, color="#c0392b", ls=":", lw=1.5)
ax_c.axhline(y=3, color="grey", ls="--", lw=1, label="3x threshold")
ax_c.scatter([5], [conc_ratios[current_idx]], color="#c0392b", s=100, zorder=5)
ax_c.set_xlabel("Window size (% population)", fontsize=11)
ax_c.set_ylabel("Concentration ratio (cases% / pop%)", fontsize=11)
ax_c.set_title("C) Concentration ratio", fontsize=12, fontweight="bold")
ax_c.legend(fontsize=9)
ax_c.grid(alpha=0.3)
for w, cr in zip(wins_pct, conc_ratios):
    ax_c.annotate(f"{cr:.1f}x", (w, cr), textcoords="offset points",
                  xytext=(0, 7), ha="center", fontsize=9)

# Panel D: Jaccard stability
ax_d = fig.add_subplot(gs[1, 0])
colors_d = ["#c0392b" if w == 5.0 else "#8e44ad" for w in wins_pct]
ax_d.plot(wins_pct, jaccards, "s-", color="#8e44ad", lw=2, ms=8)
ax_d.axvline(x=5, color="#c0392b", ls=":", lw=1.5)
ax_d.axhline(y=0.5, color="grey", ls="--", lw=1, label="Jaccard=0.5 (moderate stability)")
ax_d.scatter([5], [jaccards[current_idx]], color="#c0392b", s=100, zorder=5)
for w, j in zip(wins_pct, jaccards):
    ax_d.annotate(f"{j:.2f}", (w, j), textcoords="offset points",
                  xytext=(0, 7), ha="center", fontsize=9)
ax_d.set_xlabel("Window size (% population)", fontsize=11)
ax_d.set_ylabel("Mean Jaccard (year-over-year)", fontsize=11)
ax_d.set_title("D) Year-to-year stability (Jaccard)", fontsize=12, fontweight="bold")
ax_d.set_ylim(0, 1.0)
ax_d.legend(fontsize=9)
ax_d.grid(alpha=0.3)

# Panel E: Cluster count
ax_e = fig.add_subplot(gs[1, 1])
ax_e2 = ax_e.twinx()
ax_e.bar([f"{w:.0f}%" for w in wins_pct], n_clusters, color="#e67e22", alpha=0.7, label="N clusters")
ax_e2.plot([f"{w:.0f}%" for w in wins_pct], med_pops, "D-", color="#1f4e79",
           lw=2, ms=8, label="Median cluster pop")
ax_e.axvline(x=2, color="#c0392b", ls=":", lw=0.5)
ax_e.set_xlabel("Window size (% population)", fontsize=11)
ax_e.set_ylabel("N spatial clusters", fontsize=11)
ax_e2.set_ylabel("Median cluster population", fontsize=11, color="#1f4e79")
ax_e.set_title("E) Operational clusters", fontsize=12, fontweight="bold")
lines_e = [Patch(color="#e67e22", alpha=0.7, label="N clusters"),
           plt.Line2D([0],[0], color="#1f4e79", marker="D", label="Median cluster pop")]
ax_e.legend(handles=lines_e, fontsize=9, loc="upper left")
ax_e.grid(axis="y", alpha=0.3)

# Panel F: % clusters ≥ 5,000 pop (operationally viable)
ax_f = fig.add_subplot(gs[1, 2])
ax_f.bar([f"{w:.0f}%" for w in wins_pct], pct_5k, color="#16a085", edgecolor="white")
ax_f.axhline(y=50, color="grey", ls="--", lw=1, label="50% threshold")
for i, (w, pct) in enumerate(zip(wins_pct, pct_5k)):
    if w == 5.0:
        ax_f.get_children()[i].set_color("#c0392b")
    ax_f.text(i, pct + 1, f"{pct:.0f}%", ha="center", fontsize=9, fontweight="bold")
ax_f.set_xlabel("Window size (% population)", fontsize=11)
ax_f.set_ylabel("% clusters with pop ≥ 5,000", fontsize=11)
ax_f.set_title("F) Operationally viable clusters (≥5k pop)", fontsize=12, fontweight="bold")
ax_f.set_ylim(0, 110)
ax_f.legend(fontsize=9)
ax_f.grid(axis="y", alpha=0.3)

plt.savefig("/tmp/window_sensitivity_plot.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("Saved: /tmp/window_sensitivity_plot.png")
print("Saved: /tmp/window_sensitivity.csv")
print("\nDone.")
