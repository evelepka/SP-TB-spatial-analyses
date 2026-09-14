"""Multi-scale hotspot stability analysis — GSP + Baixada Santista.

Compares sector, bairro, and custom-zone (10k / 20k pop minimum) aggregations
on three criteria at the 5% population window:
  1. Concentration  — % TB cases captured
  2. Stability      — mean pairwise Jaccard 2020–2024
  3. Operability    — cluster/zone sizes and ACF viability

Output: /tmp/multiscale_sensitivity.csv + multiscale_plot.png
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Patch
import zipfile, io, unicodedata, re

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s

# ============================================================
# 1) Load base data
# ============================================================
print("Loading shapefile + aggregates...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]   = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)
sec22["AREA_KM2"] = pd.to_numeric(sec22["AREA_KM2"], errors="coerce")

agg = pd.read_csv(
    f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
    sep=";", encoding="latin-1", decimal=",",
    usecols=["CD_SETOR","v0001"],
    dtype={"CD_SETOR": str}, low_memory=False,
)
agg["v0001"] = pd.to_numeric(agg["v0001"], errors="coerce").fillna(0)

GSP_MUNIS = set(sec22[sec22["NM_CONCURB"] == "São Paulo/SP"]["CD_MUN"].unique())
BX_MUNIS  = {"3506359","3513504","3518701","3522109","3531100","3537602","3541000","3548500","3551009"}
ALL_MUNIS = GSP_MUNIS | BX_MUNIS

# ============================================================
# 2) Cases with year
# ============================================================
print("Loading cases with year...")
gsp_co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False, dtype={"sinan_clean": str})
gsp_co["key"] = gsp_co["sinan_clean"].str.zfill(7)
gsp_co["CD_SETOR"] = gsp_co["setor_cnefe"].apply(norm_setor)

bx_co = pd.read_csv("/tmp/cohort_baixada_with_cnefe_v2.csv", low_memory=False, dtype={"sinan_clean": str})
bx_co["match_tier"] = bx_co["cnefe_match"].astype(str).str.extract(r"^(T\d)")
bx_co = bx_co[bx_co["match_tier"].isin(["T1","T2","T3"])]
bx_co["key"] = bx_co["sinan_clean"].str.zfill(7)
bx_co["CD_SETOR"] = bx_co["setor_cnefe"].apply(norm_setor)

spatial_yr = pd.read_csv(
    f"{SPATIAL}/cohort_with_spatial.csv",
    usecols=["sinan_clean","notification_date"], dtype={"sinan_clean": str}, low_memory=False
)
spatial_yr["key"]  = spatial_yr["sinan_clean"].str.strip()
spatial_yr["year"] = pd.to_datetime(spatial_yr["notification_date"], errors="coerce").dt.year
spatial_yr = spatial_yr[spatial_yr["year"].between(2020,2024)].drop_duplicates("key")[["key","year"]]

all_co = pd.concat([
    gsp_co[["key","CD_SETOR"]],
    bx_co[["key","CD_SETOR"]],
], ignore_index=True)
all_co = all_co.merge(spatial_yr, on="key", how="left")
all_co["year"] = all_co["year"].fillna(2022).astype(int)
all_co = all_co.dropna(subset=["CD_SETOR"])
print(f"  Cases loaded: {len(all_co):,}")

# ============================================================
# 3) Sector base table
# ============================================================
print("Building residential sector table...")
sec_all = sec22[sec22["CD_MUN"].isin(ALL_MUNIS)].copy()
sec_all = sec_all.merge(agg, on="CD_SETOR", how="left")
sec_res = sec_all[
    sec_all["CD_TIPO"].astype(str).isin(["0","1"]) &
    (sec_all["v0001"] >= 100)
].copy()
print(f"  Residential sectors: {len(sec_res):,}")

n_total_cases = len(all_co)
total_pop_sector = sec_res["v0001"].sum()
YEARS = [2020,2021,2022,2023,2024]

# ============================================================
# 4) Build aggregation units
# ============================================================

def build_bairro_units(sec_res, all_co, years):
    """Aggregate sectors to bairro level. Sectors with NaN bairro get their own unit."""
    sec_b = sec_res[["CD_SETOR","CD_MUN","NM_MUN","NM_BAIRRO","v0001"]].copy()
    # Assign fallback bairro key for null names
    sec_b["bairro_key"] = sec_b.apply(
        lambda r: f"{r['CD_MUN']}___{r['NM_BAIRRO']}" if pd.notna(r['NM_BAIRRO'])
                  else f"{r['CD_MUN']}___SETOR_{r['CD_SETOR']}", axis=1
    )
    # Unit population
    unit_pop = sec_b.groupby("bairro_key")["v0001"].sum().rename("pop")
    # Map sector → unit
    sec2unit = sec_b.set_index("CD_SETOR")["bairro_key"].to_dict()
    # Cases per unit per year
    cases = all_co.copy()
    cases["unit"] = cases["CD_SETOR"].map(sec2unit)
    cases = cases.dropna(subset=["unit"])
    cases_yr = cases.groupby(["unit","year"]).size().rename("n").reset_index()
    cases_total = cases.groupby("unit").size().rename("n_total").reset_index()
    return unit_pop, sec2unit, cases_yr, cases_total

def build_custom_zones(sec_res, all_co, years, min_pop, proj_crs="EPSG:31983"):
    """Aggregate contiguous sectors into zones with minimum population using greedy spatial expansion."""
    print(f"  Building custom zones (min_pop={min_pop:,})...")
    sec_proj = sec_res.to_crs(proj_crs)[["CD_SETOR","v0001","geometry"]].copy()
    sec_proj["zone_id"] = None

    # Sort sectors by rate (pooled) — highest rate seeds first
    cases_total = all_co.groupby("CD_SETOR").size().rename("n_cases").reset_index()
    sec_proj = sec_proj.merge(cases_total, on="CD_SETOR", how="left")
    sec_proj["n_cases"] = sec_proj["n_cases"].fillna(0)
    sec_proj["rate"] = sec_proj["n_cases"] / (sec_proj["v0001"] * 5) * 1e5
    sec_proj = sec_proj.sort_values("rate", ascending=False).reset_index(drop=True)

    # Build spatial adjacency (buffered 10m)
    buf = sec_proj.copy()
    buf["geometry"] = buf.geometry.buffer(10)
    adj = gpd.sjoin(
        sec_proj[["CD_SETOR","geometry"]],
        buf[["CD_SETOR","geometry"]].rename(columns={"CD_SETOR":"nb"}),
        how="left", predicate="intersects"
    )
    adj = adj[adj["CD_SETOR"] != adj["nb"]][["CD_SETOR","nb"]]
    neighbors = adj.groupby("CD_SETOR")["nb"].apply(set).to_dict()

    # Union-Find
    parent = {s: s for s in sec_proj["CD_SETOR"]}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(x, y):
        px, py = find(x), find(y)
        if px != py: parent[px] = py

    # Greedy: start with highest-rate sector, expand to adjacent until min_pop reached
    zone_counter = [0]
    sector_zone = {}
    pop_lookup = sec_proj.set_index("CD_SETOR")["v0001"].to_dict()

    assigned = set()
    for _, seed_row in sec_proj.iterrows():
        seed = seed_row["CD_SETOR"]
        if seed in assigned:
            continue
        # BFS expansion
        zone = {seed}
        queue = [seed]
        zone_pop = pop_lookup.get(seed, 0)
        visited = {seed}
        while zone_pop < min_pop and queue:
            curr = queue.pop(0)
            for nb in neighbors.get(curr, set()):
                if nb not in visited and nb not in assigned:
                    visited.add(nb)
                    zone.add(nb)
                    queue.append(nb)
                    zone_pop += pop_lookup.get(nb, 0)
                    if zone_pop >= min_pop:
                        break
        zone_id = f"zone_{zone_counter[0]:05d}"
        zone_counter[0] += 1
        for s in zone:
            sector_zone[s] = zone_id
            assigned.add(s)

    # Assign any remaining sectors
    for s in sec_proj["CD_SETOR"]:
        if s not in sector_zone:
            zone_id = f"zone_{zone_counter[0]:05d}"
            zone_counter[0] += 1
            sector_zone[s] = zone_id

    # Build unit_pop
    sec_proj["zone_id"] = sec_proj["CD_SETOR"].map(sector_zone)
    unit_pop = sec_proj.groupby("zone_id")["v0001"].sum().rename("pop")

    # Cases per unit per year
    cases = all_co.copy()
    cases["unit"] = cases["CD_SETOR"].map(sector_zone)
    cases = cases.dropna(subset=["unit"])
    cases_yr = cases.groupby(["unit","year"]).size().rename("n").reset_index()
    cases_total = cases.groupby("unit").size().rename("n_total").reset_index()

    print(f"    → {len(unit_pop):,} zones | median pop: {unit_pop.median():,.0f} | "
          f"min: {unit_pop.min():,.0f} | max: {unit_pop.max():,.0f}")
    return unit_pop, sector_zone, cases_yr, cases_total


# ============================================================
# 5) Analysis function: concentration + stability for any unit set
# ============================================================

WINDOWS = [0.01, 0.02, 0.05, 0.10, 0.15, 0.20]

def analyze_units(unit_pop, cases_yr, cases_total, total_cases, label):
    """For a given aggregation, compute concentration + stability for each window."""
    results = []

    # Pooled rate per unit
    pop_df = unit_pop.reset_index()
    pop_df.columns = ["unit","pop"]
    ct = cases_total.copy()
    ct.columns = ["unit","n_total"]
    pooled = pop_df.merge(ct, on="unit", how="left")
    pooled["n_total"] = pooled["n_total"].fillna(0)
    pooled["rate"] = pooled["n_total"] / (pooled["pop"] * 5) * 1e5

    pooled_sorted = pooled.sort_values("rate", ascending=False).copy()
    pooled_sorted["cum_pop"] = pooled_sorted["pop"].cumsum()
    pooled_sorted["cum_cases"] = pooled_sorted["n_total"].cumsum()
    total_pop_u = pooled_sorted["pop"].sum()

    # Year-specific rates
    yr_rates = {}
    for yr in YEARS:
        yr_cases = cases_yr[cases_yr["year"] == yr][["unit","n"]].copy()
        yr_df = pop_df.merge(yr_cases, on="unit", how="left")
        yr_df["n"] = yr_df["n"].fillna(0)
        yr_df["rate"] = yr_df["n"] / yr_df["pop"] * 1e5
        yr_rates[yr] = yr_df.set_index("unit")

    for w in WINDOWS:
        # Concentration
        mask = pooled_sorted["cum_pop"] <= total_pop_u * w
        if mask.sum() == 0:
            mask = pd.Series([True] + [False]*(len(pooled_sorted)-1), index=pooled_sorted.index)
        cases_pct = pooled_sorted[mask]["n_total"].sum() / total_cases * 100
        pop_pct = pooled_sorted[mask]["pop"].sum() / total_pop_u * 100
        n_units = mask.sum()
        conc_ratio = cases_pct / pop_pct if pop_pct > 0 else 0

        # Stability (Jaccard year-over-year)
        jaccards = []
        for i, yr_a in enumerate(YEARS[:-1]):
            yr_b = YEARS[i+1]
            df_a = yr_rates[yr_a].copy()
            df_b = yr_rates[yr_b].copy()
            tot_a = df_a["pop"].sum()
            tot_b = df_b["pop"].sum()
            inc_a = df_a[df_a["n"]>0].sort_values("rate", ascending=False)
            inc_a["cum_pop"] = inc_a["pop"].cumsum()
            hot_a = set(inc_a[inc_a["cum_pop"] <= tot_a * w].index)
            inc_b = df_b[df_b["n"]>0].sort_values("rate", ascending=False)
            inc_b["cum_pop"] = inc_b["pop"].cumsum()
            hot_b = set(inc_b[inc_b["cum_pop"] <= tot_b * w].index)
            if hot_a | hot_b:
                jaccards.append(len(hot_a & hot_b) / len(hot_a | hot_b))

        # Operability: median unit population in hotspot window
        hot_units = pooled_sorted[mask]
        median_unit_pop = hot_units["pop"].median() if len(hot_units) > 0 else 0
        pct_viable = (hot_units["pop"] >= 5000).mean() * 100 if len(hot_units) > 0 else 0
        pct_viable10k = (hot_units["pop"] >= 10000).mean() * 100 if len(hot_units) > 0 else 0

        results.append({
            "scale": label,
            "window_pct": w * 100,
            "n_units_in_window": int(n_units),
            "cases_pct": round(cases_pct, 1),
            "conc_ratio": round(conc_ratio, 2),
            "mean_jaccard": round(np.mean(jaccards), 3) if jaccards else 0,
            "median_unit_pop": int(median_unit_pop),
            "pct_viable_5k": round(pct_viable, 0),
            "pct_viable_10k": round(pct_viable10k, 0),
        })

    return results


# ============================================================
# 6) Run all scales
# ============================================================
all_results = []

# Scale 1: Sector (reuse from script 33 logic)
print("\n--- Scale: Sector ---")
cases_sec_total = all_co.groupby("CD_SETOR").size().rename("n_total").reset_index()
cases_sec_total.columns = ["unit","n_total"]
cases_sec_yr = all_co.groupby(["CD_SETOR","year"]).size().rename("n").reset_index()
cases_sec_yr.columns = ["unit","year","n"]
pop_sec = sec_res.set_index("CD_SETOR")["v0001"].rename("pop")
pop_sec.index.name = None
all_results += analyze_units(pop_sec, cases_sec_yr, cases_sec_total, n_total_cases, "Setor (~380)")

# Scale 2: Bairro
print("\n--- Scale: Bairro ---")
bairro_pop, _, bairro_cases_yr, bairro_cases_total = build_bairro_units(sec_res, all_co, YEARS)
all_results += analyze_units(bairro_pop, bairro_cases_yr, bairro_cases_total, n_total_cases, "Bairro (~5.6k)")

# Scale 3: Custom zone 10k
print("\n--- Scale: Custom zone 10k ---")
zone10_pop, _, zone10_cases_yr, zone10_cases_total = build_custom_zones(sec_res, all_co, YEARS, min_pop=10000)
all_results += analyze_units(zone10_pop, zone10_cases_yr, zone10_cases_total, n_total_cases, "Zona 10k")

# Scale 4: Custom zone 20k
print("\n--- Scale: Custom zone 20k ---")
zone20_pop, _, zone20_cases_yr, zone20_cases_total = build_custom_zones(sec_res, all_co, YEARS, min_pop=20000)
all_results += analyze_units(zone20_pop, zone20_cases_yr, zone20_cases_total, n_total_cases, "Zona 20k")

# Scale 5: Distrito
print("\n--- Scale: Distrito ---")
sec_dist = sec_res[["CD_SETOR","CD_MUN","NM_DIST","v0001"]].copy()
sec_dist["unit"] = sec_dist["CD_MUN"] + "___" + sec_dist["NM_DIST"].fillna("(sem_dist)")
dist_pop = sec_dist.groupby("unit")["v0001"].sum().rename("pop")
sec2dist = sec_dist.set_index("CD_SETOR")["unit"].to_dict()
cases_dist = all_co.copy()
cases_dist["unit"] = cases_dist["CD_SETOR"].map(sec2dist)
cases_dist = cases_dist.dropna(subset=["unit"])
cases_dist_yr = cases_dist.groupby(["unit","year"]).size().rename("n").reset_index()
cases_dist_total = cases_dist.groupby("unit").size().rename("n_total").reset_index()
all_results += analyze_units(dist_pop, cases_dist_yr, cases_dist_total, n_total_cases, "Distrito (~99k)")


# ============================================================
# 7) Summary table
# ============================================================
df = pd.DataFrame(all_results)
df.to_csv("/tmp/multiscale_sensitivity.csv", index=False)

print("\n" + "="*110)
print("MULTI-SCALE SENSITIVITY SUMMARY (5% window highlighted)")
print("="*110)
print(f"\n{'Scale':<20} {'Win%':>5} {'N units':>8} {'%Cases':>7} {'CRatio':>7} "
      f"{'Jaccard':>8} {'Med pop':>8} {'%≥5k':>6} {'%≥10k':>6}")
print("-" * 110)

for scale in df["scale"].unique():
    sub = df[df["scale"] == scale]
    for _, r in sub.iterrows():
        marker = " ◄" if r["window_pct"] == 5.0 else ""
        print(f"{r['scale']:<20} {r['window_pct']:>5.0f}% {r['n_units_in_window']:>8,} "
              f"{r['cases_pct']:>6.1f}% {r['conc_ratio']:>6.2f}x "
              f"{r['mean_jaccard']:>8.3f} {r['median_unit_pop']:>8,} "
              f"{r['pct_viable_5k']:>5.0f}% {r['pct_viable_10k']:>5.0f}%{marker}")
    print()


# ============================================================
# 8) Plot — 3-panel comparing scales at 5% window
# ============================================================
print("Generating multi-scale plot...")
scales = df["scale"].unique()
colors = {"Setor (~380)": "#e74c3c", "Bairro (~5.6k)": "#e67e22",
          "Zona 10k": "#2980b9", "Zona 20k": "#27ae60", "Distrito (~99k)": "#8e44ad"}
w5 = df[df["window_pct"] == 5.0].copy()

fig, axes = plt.subplots(1, 3, figsize=(18, 7))
fig.suptitle("Multi-scale Hotspot Analysis — GSP + Baixada Santista (5% population window)",
             fontsize=15, fontweight="bold", y=1.01)

# Panel A: Jaccard stability by scale
ax = axes[0]
bar_h = [w5[w5["scale"]==s]["mean_jaccard"].values[0] for s in scales]
bar_c = [colors[s] for s in scales]
bars = ax.barh(list(scales), bar_h, color=bar_c, edgecolor="white", height=0.6)
ax.axvline(x=0.5, color="grey", ls="--", lw=1.5, label="Jaccard=0.5\n(moderate)")
ax.axvline(x=0.3, color="grey", ls=":", lw=1, label="Jaccard=0.3\n(minimum)")
for bar, v in zip(bars, bar_h):
    ax.text(v + 0.01, bar.get_y() + bar.get_height()/2,
            f"{v:.3f}", va="center", fontsize=11, fontweight="bold")
ax.set_xlabel("Mean Jaccard (year-over-year, 2020-2024)", fontsize=12)
ax.set_title("A) Year-to-year stability", fontsize=13, fontweight="bold")
ax.set_xlim(0, 0.85)
ax.legend(fontsize=9, loc="lower right")
ax.grid(axis="x", alpha=0.3)

# Panel B: Concentration ratio by scale
ax = axes[1]
bar_cr = [w5[w5["scale"]==s]["conc_ratio"].values[0] for s in scales]
bars = ax.barh(list(scales), bar_cr, color=bar_c, edgecolor="white", height=0.6)
ax.axvline(x=3.0, color="grey", ls="--", lw=1.5, label="3x threshold")
for bar, v in zip(bars, bar_cr):
    ax.text(v + 0.05, bar.get_y() + bar.get_height()/2,
            f"{v:.1f}x", va="center", fontsize=11, fontweight="bold")
ax.set_xlabel("Concentration ratio (cases% / pop%)", fontsize=12)
ax.set_title("B) Concentration ratio", fontsize=13, fontweight="bold")
ax.set_xlim(0, max(bar_cr) * 1.2)
ax.legend(fontsize=9)
ax.grid(axis="x", alpha=0.3)

# Panel C: Operational viability (% units ≥ 10k pop)
ax = axes[2]
bar_op = [w5[w5["scale"]==s]["pct_viable_10k"].values[0] for s in scales]
bars = ax.barh(list(scales), bar_op, color=bar_c, edgecolor="white", height=0.6)
ax.axvline(x=50, color="grey", ls="--", lw=1.5, label="50% threshold")
for bar, v in zip(bars, bar_op):
    ax.text(v + 1, bar.get_y() + bar.get_height()/2,
            f"{v:.0f}%", va="center", fontsize=11, fontweight="bold")
ax.set_xlabel("% units with population ≥ 10,000", fontsize=12)
ax.set_title("C) Operationally viable units (≥10k pop)", fontsize=13, fontweight="bold")
ax.set_xlim(0, 115)
ax.legend(fontsize=9)
ax.grid(axis="x", alpha=0.3)

plt.tight_layout()
plt.savefig("/tmp/multiscale_plot.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("Saved: /tmp/multiscale_plot.png")

# Summary at 5% window
print("\n" + "="*70)
print("SUMMARY AT 5% WINDOW — key tradeoffs")
print("="*70)
print(f"\n{'Scale':<20} {'Jaccard':>8} {'CRatio':>8} {'%≥10k':>7} {'Med pop':>9}")
print("-"*70)
for s in scales:
    r = w5[w5["scale"]==s].iloc[0]
    print(f"{s:<20} {r['mean_jaccard']:>8.3f} {r['conc_ratio']:>7.2f}x "
          f"{r['pct_viable_10k']:>6.0f}% {r['median_unit_pop']:>9,}")

print("\nDone.")
