"""Three-tier adaptive unit selection: FCU / Sector / Bairro

For each census sector, assign to the most granular viable unit:
  Tier 1 — Named FCU ≥ FCU_MIN_POP: all sectors of that FCU form one unit
  Tier 2 — Single sector (not in FCU): standalone SECTOR unit if it has ≥ MIN_CASES
  Tier 3 — Remaining sectors: aggregate to bairro/distrito (same as before)
  Tier 4 — Adjacent bairro groups: for bairros still < MIN_CASES, greedily merge
            with spatially adjacent bairros within same municipality until ≥ MIN_CASES
            (these are "micro-region" units — most granular fallback)

The threshold is MIN_CASES = 10 (cases pooled over 2020-2024, 5 years).
Operationally, a unit with <10 TB cases in 5 years (~2/year) is likely too small
to justify a sustained ACF program on its own.

Output: comparison of this three-tier approach vs. pure-bairro-≥10 baseline
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from shapely.ops import unary_union

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL = "3550308"
BAIXADA = {"3506359","3513504","3518701","3522109","3531100","3537602","3541000","3548500","3551009"}
FCU_MIN  = 5000
MIN_CASES = 10

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s

# ── 1. Load sectors ─────────────────────────────────────────────────────────────
print("Loading sectors...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"] = sec22["CD_MUN"].astype(str)
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
sec_res = sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["v0001"] >= 100)].copy()
sec_res["pop"] = sec_res["v0001"]

# Bairro unit label
sec_res["bairro_id"] = sec_res.apply(
    lambda r: f"dist_{r['CD_DIST']}" if str(r["CD_MUN"]) == CAPITAL
              else (f"bairro_{r['CD_MUN']}_{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"dist_{r['CD_DIST']}"), axis=1)
sec_res["bairro_label"] = sec_res.apply(
    lambda r: f"SP/{r['NM_DIST']}" if str(r["CD_MUN"]) == CAPITAL
              else (f"{r['NM_MUN']}/{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"{r['NM_MUN']}/{r['NM_DIST']}"), axis=1)

TOTAL_POP = sec_res["pop"].sum()
fcu_pop_by_name = sec_res[sec_res["NM_FCU"].notna()].groupby("NM_FCU")["pop"].sum()
qualifying_fcus = set(fcu_pop_by_name[fcu_pop_by_name >= FCU_MIN].index)
print(f"  Residential sectors: {len(sec_res):,}  |  Total pop: {TOTAL_POP/1e6:.2f}M")
print(f"  Qualifying FCUs (≥{FCU_MIN:,} pop): {len(qualifying_fcus)}")

# ── 2. Load cases ──────────────────────────────────────────────────────────────
print("Loading cases...")
gsp_co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False, dtype={"sinan_clean":str})
gsp_co["CD_SETOR"] = gsp_co["setor_cnefe"].apply(norm_setor)

bx_co = pd.read_csv("/tmp/cohort_baixada_with_cnefe_v2.csv", low_memory=False, dtype={"sinan_clean":str})
bx_co["match_tier"] = bx_co["cnefe_match"].astype(str).str.extract(r"^(T\d)")
bx_co = bx_co[bx_co["match_tier"].isin(["T1","T2","T3"])]
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

# Sector-level case count (pooled 5-year)
sector_cases_pooled = all_co.groupby("CD_SETOR").size().rename("n_cases").reset_index()
sector_year_cases   = all_co.groupby(["CD_SETOR","year"]).size().rename("n_cases_yr").reset_index()
print(f"  Total geocoded cases: {TOTAL_CASES:,}")

# ── 3. Assign each sector to a unit ────────────────────────────────────────────
print("\nAssigning sectors to units...")
sec_w = sec_res.merge(sector_cases_pooled, on="CD_SETOR", how="left")
sec_w["n_cases"] = sec_w["n_cases"].fillna(0)

def assign_unit(row):
    nm = row["NM_FCU"]
    if pd.notna(nm) and nm in qualifying_fcus:
        return f"fcu__{nm}", nm, "FCU"
    if row["n_cases"] >= MIN_CASES:
        lbl = (f"SP/sector_{row['CD_SETOR'][-6:]}" if str(row["CD_MUN"]) == CAPITAL
               else f"{row['NM_MUN']}/sector_{row['CD_SETOR'][-6:]}")
        return f"sector__{row['CD_SETOR']}", lbl, "sector"
    return row["bairro_id"], row["bairro_label"], "bairro"

asgn = sec_w.apply(assign_unit, axis=1, result_type="expand")
asgn.columns = ["unit_id","label","unit_type"]
sec_w = pd.concat([sec_w, asgn], axis=1)

# ── 4. Aggregate to unit level ─────────────────────────────────────────────────
unit_pop    = sec_w.groupby("unit_id").agg(
    pop=("pop","sum"), label=("label","first"), unit_type=("unit_type","first"),
    n_cases=("n_cases","sum"),
).reset_index()
unit_pop["rate"] = unit_pop["n_cases"] / (unit_pop["pop"] * 5) * 1e5

# ── 5. Tier 4 — Spatial aggregation of adjacent bairros below threshold ─────────
# For bairro units with <MIN_CASES, merge with adjacent bairros within same municipality
# to rescue high-rate micro-clusters that span a bairro boundary

print("Building bairro spatial index for adjacent aggregation...")
bairro_units_below = unit_pop[(unit_pop["unit_type"]=="bairro") &
                               (unit_pop["n_cases"] < MIN_CASES)]["unit_id"].tolist()

# Build bairro geometries — use dissolve on GeoDataFrame to avoid pandas/geopandas conflict
bairro_geom_raw = sec_w[sec_w["unit_type"].isin(["bairro","sector","FCU"])].copy()
bairro_geom_raw = bairro_geom_raw.set_index("unit_id")
bairro_geom = (gpd.GeoDataFrame(bairro_geom_raw[["CD_MUN","geometry"]],
                                  geometry="geometry", crs=sec_res.crs)
               .dissolve(by="unit_id").reset_index())
# Add CD_MUN back (take first occurrence per unit)
mun_map = sec_w.groupby("unit_id")["CD_MUN"].first().to_dict()
bairro_geom["CD_MUN"] = bairro_geom["unit_id"].map(mun_map)
bairro_geom = bairro_geom.merge(unit_pop[["unit_id","n_cases","pop","rate","label","unit_type"]],
                                 on="unit_id")

# Spatial adjacency among bairros (within same municipality) via small buffer
print("  Computing spatial adjacency (buffer 5m)...")
bairro_geom_proj = bairro_geom.to_crs("EPSG:31983")  # SIRGAS 2000 UTM 23S — metres
bairro_buf = bairro_geom_proj.copy()
bairro_buf["geometry"] = bairro_buf["geometry"].buffer(5)

adj_df = gpd.sjoin(
    bairro_buf[["unit_id","CD_MUN","geometry"]].rename(columns={"unit_id":"uid_l","CD_MUN":"mun_l"}),
    bairro_buf[["unit_id","CD_MUN","geometry"]].rename(columns={"unit_id":"uid_r","CD_MUN":"mun_r"}),
    how="inner", predicate="intersects"
)
adj_df = adj_df[(adj_df["uid_l"] != adj_df["uid_r"]) & (adj_df["mun_l"] == adj_df["mun_r"])]
adj_dict = adj_df.groupby("uid_l")["uid_r"].apply(set).to_dict()
print(f"  Adjacency built: {len(adj_dict):,} bairro units have ≥1 neighbor")

# Greedy aggregation of below-threshold bairros
# Seed: sort by rate desc; expand to highest-rate unassigned neighbor until ≥MIN_CASES
below_df = (bairro_geom[bairro_geom["unit_id"].isin(bairro_units_below)]
            .sort_values("rate", ascending=False).copy())
below_ids = set(below_df["unit_id"])

merged_map  = {}   # unit_id → merged_group_id
group_info  = {}   # group_id → {pop, cases, label}
group_counter = 0

for _, row in below_df.iterrows():
    uid = row["unit_id"]
    if uid in merged_map:
        continue
    gid = f"micro_{group_counter}"
    members = {uid}
    g_cases = row["n_cases"]
    g_pop   = row["pop"]
    labels  = [row["label"]]
    merged_map[uid] = gid

    # Expand to adjacent below-threshold neighbors until threshold met
    frontier = {uid}
    while g_cases < MIN_CASES:
        candidates = []
        for fid in frontier:
            for nbr in adj_dict.get(fid, set()):
                if nbr in below_ids and nbr not in merged_map:
                    nbr_row = below_df[below_df["unit_id"] == nbr]
                    if len(nbr_row):
                        candidates.append(nbr_row.iloc[0])
        if not candidates:
            break
        best = max(candidates, key=lambda x: x["rate"])
        members.add(best["unit_id"])
        merged_map[best["unit_id"]] = gid
        g_cases += best["n_cases"]
        g_pop   += best["pop"]
        labels.append(best["label"])
        frontier = {best["unit_id"]}

    group_info[gid] = {
        "unit_id": gid, "label": "+".join(labels[:3]) + ("..." if len(labels)>3 else ""),
        "unit_type": "micro_region",
        "n_cases": g_cases, "pop": g_pop,
        "rate": g_cases / (g_pop * 5) * 1e5 if g_pop > 0 else 0,
    }
    group_counter += 1

# Micro-region units with ≥MIN_CASES
micro_units = pd.DataFrame(list(group_info.values()))
micro_eligible = micro_units[micro_units["n_cases"] >= MIN_CASES].copy()

print(f"  Below-threshold bairros: {len(bairro_units_below):,}")
print(f"  Micro-region groups formed: {len(micro_units):,}  |  "
      f"Eligible (≥{MIN_CASES} cases): {len(micro_eligible):,}")

# ── 6. Build final selection pool ──────────────────────────────────────────────
# Keep above-threshold units from main pool; replace below-threshold bairros with micro-regions
pool_main = unit_pop[unit_pop["n_cases"] >= MIN_CASES].copy()
pool_full = pd.concat([pool_main, micro_eligible[["unit_id","label","unit_type","n_cases","pop","rate"]]],
                       ignore_index=True)

print(f"\n{'Unit type':<15} {'Eligible':>8} {'Total pop':>12} {'Total cases':>12}")
for utype in ["FCU","sector","bairro","micro_region"]:
    sub = pool_full[pool_full["unit_type"]==utype]
    print(f"  {utype:<13} {len(sub):>8,} {sub['pop'].sum():>12,.0f} {sub['n_cases'].sum():>12,.0f}")
print(f"  {'TOTAL':<13} {len(pool_full):>8,} {pool_full['pop'].sum():>12,.0f} "
      f"{pool_full['n_cases'].sum():>12,.0f}")

# ── 7. Select until 20% pop covered ───────────────────────────────────────────
def select_pool(pool_df, target_pop_frac=0.20):
    s = pool_df.sort_values("rate", ascending=False).copy()
    s["cum_pop"] = s["pop"].cumsum()
    target = TOTAL_POP * target_pop_frac
    mask = s["cum_pop"] <= target
    if mask.sum() < len(s):
        mask.iloc[mask.sum()] = True
    return s[mask]

sel = select_pool(pool_full)

print(f"\n{'='*70}")
print("THREE-TIER SELECTION RESULT (≥10 cases, 20% pop window)")
print(f"{'='*70}")
print(f"  Selected units:  {len(sel):,}")
print(f"    FCU:           {(sel['unit_type']=='FCU').sum():,}")
print(f"    Sector:        {(sel['unit_type']=='sector').sum():,}")
print(f"    Bairro:        {(sel['unit_type']=='bairro').sum():,}")
print(f"    Micro-region:  {(sel['unit_type']=='micro_region').sum():,}")
print(f"  Population:      {sel['pop'].sum()/1e6:.2f}M ({sel['pop'].sum()/TOTAL_POP*100:.1f}%)")
print(f"  Cases covered:   {sel['n_cases'].sum()/TOTAL_CASES*100:.1f}%")
print(f"  Mean TB rate:    {sel['n_cases'].sum()/(sel['pop'].sum()*5)*1e5:.0f}/100k")
print(f"  Median unit pop: {sel['pop'].median():,.0f}")
print(f"  Min unit pop:    {sel['pop'].min():,}")
print(f"  Min unit cases:  {sel['n_cases'].min():.0f}")
print(f"  Max unit rate:   {sel['rate'].max():.0f}/100k")

# Size distribution
print(f"\n  Size distribution of selected units:")
for thr in [500, 1000, 2000, 5000, 10000]:
    n = (sel["pop"] < thr).sum()
    print(f"    < {thr:>6,} pop: {n:>3} units ({n/len(sel)*100:.1f}%)")

# ── 8. Top units ───────────────────────────────────────────────────────────────
print(f"\nTop 30 selected units by TB rate:")
top = sel.nlargest(30,"rate")[["label","unit_type","pop","n_cases","rate"]]
print(top.to_string(index=False))

print(f"\nBottom 10 selected units (lowest rate):")
bot = sel.nsmallest(10,"rate")[["label","unit_type","pop","n_cases","rate"]]
print(bot.to_string(index=False))

# ── 9. Sector-level breakdown ──────────────────────────────────────────────────
n_sector_units = (pool_full["unit_type"]=="sector").sum()
sector_df = pool_full[pool_full["unit_type"]=="sector"].copy()
print(f"\n--- Standalone sector units (n={n_sector_units:,}) ---")
print(f"  Pop range:    {sector_df['pop'].min():,} – {sector_df['pop'].max():,.0f}")
print(f"  Cases range:  {sector_df['n_cases'].min():.0f} – {sector_df['n_cases'].max():.0f}")
print(f"  Rate range:   {sector_df['rate'].min():.0f} – {sector_df['rate'].max():.0f}/100k")
print(f"  Selected:     {(sel['unit_type']=='sector').sum()} of {n_sector_units:,} eligible sector units")

# Municipality breakdown of sector units
sec_mun = sec_w[sec_w["unit_type"]=="sector"].merge(
    sector_cases_pooled, on="CD_SETOR", how="left")
if len(sec_mun):
    print("\n  Standalone sector units by municipality:")
    mun_ct = sec_mun.groupby("NM_MUN").size().sort_values(ascending=False)
    print(mun_ct.head(15).to_string())

# ── 10. Jaccard stability ──────────────────────────────────────────────────────
print("\nComputing Jaccard stability...")
# For each year, build the same three-tier unit pool but using that year's case counts
# Units eligible if pooled-5yr cases ≥ MIN_CASES (unit definition fixed)
# Re-rank by that year's rate → re-select

sec2unit = sec_w.set_index("CD_SETOR")["unit_id"].to_dict()
all_co["unit_id"] = all_co["CD_SETOR"].map(sec2unit)

jacs = []
for ya, yb in zip([2020,2021,2022,2023],[2021,2022,2023,2024]):
    sets = []
    for yr in [ya, yb]:
        yr_cases = (all_co[all_co["year"]==yr].dropna(subset=["unit_id"])
                    .groupby("unit_id").size().rename("n_yr").reset_index())
        # Use pool_full (fixed eligibility) but update rates with year-specific counts
        yr_pool = pool_full[["unit_id","pop"]].merge(yr_cases, on="unit_id", how="left")
        yr_pool["n_yr"] = yr_pool["n_yr"].fillna(0)
        yr_pool["rate_yr"] = yr_pool["n_yr"] / yr_pool["pop"] * 1e5
        yr_pool = yr_pool.sort_values("rate_yr", ascending=False).copy()
        yr_pool["cum"] = yr_pool["pop"].cumsum()
        target = TOTAL_POP * 0.20
        mask = yr_pool["cum"] <= target
        if mask.sum() < len(yr_pool): mask.iloc[mask.sum()] = True
        sets.append(set(yr_pool[mask]["unit_id"]))
    i = sets[0] & sets[1]; u = sets[0] | sets[1]
    jacs.append(len(i)/len(u) if u else 0)

print(f"  Jaccard (2020→21, 21→22, 22→23, 23→24): {[round(j,3) for j in jacs]}")
print(f"  Mean Jaccard: {np.mean(jacs):.3f}")

# ── 11. Comparison table ───────────────────────────────────────────────────────
print(f"\n{'='*100}")
print("COMPARISON: pure bairro ≥10 cases vs. three-tier ≥10 cases")
print(f"{'='*100}")

# Recompute pure bairro ≥10 for fair comparison
bairro_pool = unit_pop[(unit_pop["unit_type"].isin(["bairro","FCU"])) |
                       (unit_pop["unit_type"]=="sector")].copy()
# Actually, just bairro (no sector tier, no FCU):
bairro_only = (sec_w.groupby("bairro_id")
               .agg(pop=("pop","sum"), label=("bairro_label","first"),
                    n_cases=("n_cases","sum"))
               .reset_index().rename(columns={"bairro_id":"unit_id"}))
bairro_only["rate"] = bairro_only["n_cases"] / (bairro_only["pop"] * 5) * 1e5
bairro_only["unit_type"] = "bairro"
bairro_only_elig = bairro_only[bairro_only["n_cases"] >= MIN_CASES]
sel_bairro = select_pool(bairro_only_elig)

# FCU + bairro (script 46 equivalent)
fcu_bairro_pool = unit_pop[unit_pop["n_cases"] >= MIN_CASES].copy()
# Remove sector units (only FCU + bairro in this pool):
fcu_bairro_pool = fcu_bairro_pool[fcu_bairro_pool["unit_type"].isin(["FCU","bairro"])]
sel_fcu_bairro = select_pool(fcu_bairro_pool)

rows = [
    ("Pure bairro ≥10 cases", sel_bairro, None),
    ("FCU+bairro ≥10 cases", sel_fcu_bairro, None),
    ("Three-tier (FCU+sector+bairro+micro)", sel, jacs),
]
print(f"\n{'Strategy':<42} {'Sel':>5} {'Pop%':>6} {'Cases%':>7} {'Rate':>6} {'Jac':>6} {'MedPop':>8}")
print("-"*90)
for label, s, jac_list in rows:
    j = f"{np.mean(jac_list):.3f}" if jac_list else "  —  "
    print(f"{label:<42} {len(s):>5} {s['pop'].sum()/TOTAL_POP*100:>5.1f}% "
          f"{s['n_cases'].sum()/TOTAL_CASES*100:>6.1f}% "
          f"{s['n_cases'].sum()/(s['pop'].sum()*5)*1e5:>6.0f} "
          f"{j:>6} {s['pop'].median():>8,.0f}")

# ── 12. Plot ───────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("Three-tier unit selection (FCU / Standalone Sector / Bairro / Micro-region)\n"
             "GSP + Baixada Santista · min 10 cases/5 years · 20% pop window",
             fontsize=12, fontweight="bold")

# Panel A: unit type composition of selected units
ax = axes[0,0]
utypes = ["FCU","sector","bairro","micro_region"]
colors = ["#1a3d5c","#e74c3c","#3498db","#27ae60"]
counts = [int((sel["unit_type"]==u).sum()) for u in utypes]
bars = ax.bar([u.replace("_"," ") for u in utypes], counts, color=colors, edgecolor="white")
for bar, c in zip(bars, counts):
    ax.text(bar.get_x()+bar.get_width()/2, c+1, str(c), ha="center", fontsize=11, fontweight="bold")
ax.set_title("A) Selected units by type", fontsize=11, fontweight="bold")
ax.set_ylabel("Count"); ax.grid(axis="y", alpha=0.3)

# Panel B: Population distribution of selected units (log scale)
ax = axes[0,1]
for utype, col in zip(utypes, colors):
    sub = sel[sel["unit_type"]==utype]["pop"]
    if len(sub):
        ax.hist(sub, bins=30, alpha=0.6, color=col, label=utype.replace("_"," "), density=True)
ax.set_xscale("log"); ax.set_xlabel("Unit population (log scale)")
ax.set_title("B) Unit population distribution", fontsize=11, fontweight="bold")
ax.legend(fontsize=8); ax.grid(alpha=0.3)

# Panel C: TB rate by unit type
ax = axes[1,0]
data = [sel[sel["unit_type"]==u]["rate"].dropna().values for u in utypes]
bp = ax.boxplot(data, labels=[u.replace("_","\n") for u in utypes], patch_artist=True, notch=False)
for patch, col in zip(bp["boxes"], colors):
    patch.set_facecolor(col); patch.set_alpha(0.7)
ax.set_title("C) TB rate by unit type (selected)", fontsize=11, fontweight="bold")
ax.set_ylabel("TB rate / 100k"); ax.grid(axis="y", alpha=0.3)

# Panel D: Jaccard by year-pair
ax = axes[1,1]
pairs = ["2020→21","2021→22","2022→23","2023→24"]
ax.bar(pairs, jacs, color="#1a3d5c", edgecolor="white")
ax.axhline(np.mean(jacs), ls="--", color="#e74c3c", lw=1.5, label=f"Mean={np.mean(jacs):.3f}")
for i, j in enumerate(jacs):
    ax.text(i, j+0.005, f"{j:.3f}", ha="center", fontsize=10, fontweight="bold", color="white" if j>0.4 else "black")
ax.set_title("D) Year-to-year Jaccard stability", fontsize=11, fontweight="bold")
ax.set_ylabel("Jaccard index"); ax.set_ylim(0, 0.8); ax.legend(); ax.grid(axis="y", alpha=0.3)

plt.tight_layout()
plt.savefig("/tmp/three_tier_units.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("\nSaved: /tmp/three_tier_units.png")

pool_full.to_csv("/tmp/three_tier_all_units.csv", index=False)
sel.to_csv("/tmp/three_tier_selected_units.csv", index=False)
print("Saved: /tmp/three_tier_all_units.csv")
print("Saved: /tmp/three_tier_selected_units.csv")
print("Done.")
