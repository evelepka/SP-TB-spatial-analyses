"""Full SP-state targeting analysis with minimum operational unit size.

Combines all three geocoded cohorts:
  - GSP (~37 municipalities)
  - Baixada Santista (9 municipalities)
  - SP outros (568 municipalities)

Unit tiers:
  1. Named FCU >= FCU_MIN pop  →  standalone FCU unit (if >= MIN_CASES)
  2. Non-FCU sectors           →  bairro/distrito aggregate
       a) bairro >= min_pop AND >= MIN_CASES → eligible as-is
       b) bairro >= MIN_CASES but < min_pop  → merge with adjacent bairros
          (greedily absorb highest-rate neighbor within same municipality)
          until pop >= min_pop → "micro-community" unit
       c) bairro < MIN_CASES                → excluded

Compares min_pop = 0 (no constraint), 1000, 2000, 5000.
Addresses the "small islands" operational concern.

Output: /tmp/sp_state_targeting_comparison.png
        /tmp/sp_state_selected_{min_pop}.csv (for each threshold)
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from shapely.ops import unary_union

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL  = "3550308"
BAIXADA  = {"3506359","3513504","3518701","3522109","3531100","3537602","3541000","3548500","3551009"}
FCU_MIN  = 5000
MIN_CASES = 10

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s

# ── 1. Load full SP-state sectors ──────────────────────────────────────────────
print("Loading SP state sectors...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]   = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)

pop_df = pd.read_csv(
    f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
    sep=";", encoding="latin-1", decimal=",",
    usecols=["CD_SETOR","v0001"], dtype={"CD_SETOR": str}, low_memory=False,
)
pop_df["pop"] = pd.to_numeric(pop_df["v0001"], errors="coerce").fillna(0)

sec = sec22.merge(pop_df[["CD_SETOR","pop"]], on="CD_SETOR", how="left")
sec["pop"] = sec["pop"].fillna(0)

# Urban/sub-urban residential sectors only, with meaningful population
sec_res = sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["pop"] >= 100)].copy()

# Bairro unit key
GSP = set(sec22[sec22["NM_CONCURB"] == "São Paulo/SP"]["CD_MUN"].unique())

def bairro_key(row):
    if str(row["CD_MUN"]) == CAPITAL:
        return f"dist_{row['CD_DIST']}", f"SP/{row['NM_DIST']}"
    if pd.notna(row.get("NM_BAIRRO")):
        return (f"bairro_{row['CD_MUN']}_{row['NM_BAIRRO']}",
                f"{row['NM_MUN']}/{row['NM_BAIRRO']}")
    if pd.notna(row.get("NM_DIST")):
        return f"dist_{row['CD_DIST']}", f"{row['NM_MUN']}/{row['NM_DIST']}"
    return f"mun_{row['CD_MUN']}", row["NM_MUN"]

bkeys = sec_res.apply(bairro_key, axis=1, result_type="expand")
sec_res[["bairro_id","bairro_label"]] = bkeys

fcu_pop = (sec_res[sec_res["NM_FCU"].notna()]
           .groupby("NM_FCU")["pop"].sum())
qualifying_fcus = set(fcu_pop[fcu_pop >= FCU_MIN].index)

TOTAL_POP   = sec_res["pop"].sum()
TOTAL_MUNIS = sec_res["CD_MUN"].nunique()
print(f"  Residential sectors: {len(sec_res):,}  |  Pop: {TOTAL_POP/1e6:.1f}M  |  Municipalities: {TOTAL_MUNIS}")

# ── 2. Load all three cohorts ──────────────────────────────────────────────────
print("Loading cohorts...")

def load_gsp():
    df = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False, dtype={"sinan_clean":str})
    df["CD_SETOR"] = df["setor_cnefe"].apply(norm_setor)
    return df[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])

def load_baixada():
    df = pd.read_csv("/tmp/cohort_baixada_with_cnefe_v2.csv", low_memory=False, dtype={"sinan_clean":str})
    df["tier"] = df["cnefe_match"].astype(str).str.extract(r"^(T\d)")
    df = df[df["tier"].isin(["T1","T2","T3"])]
    df["CD_SETOR"] = df["setor_cnefe"].apply(norm_setor)
    return df[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])

def load_outros():
    df = pd.read_csv("/tmp/cohort_sp_outros_with_cnefe.csv", low_memory=False, dtype={"sinan_clean":str})
    df["tier"] = df["cnefe_match"].astype(str).str.extract(r"^(T\d)")
    df = df[df["tier"].isin(["T1","T2","T3"])]
    df["CD_SETOR"] = df["setor_cnefe"].apply(norm_setor)
    return df[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])

cohort_all = pd.concat([load_gsp(), load_baixada(), load_outros()], ignore_index=True)

# Attach notification year
cohort_yr = pd.read_csv(f"{SPATIAL}/cohort_with_spatial.csv",
                        usecols=["sinan_clean","notification_date"],
                        low_memory=False, dtype={"sinan_clean":str})
cohort_yr["year"] = pd.to_datetime(cohort_yr["notification_date"], errors="coerce").dt.year
yr_map = (cohort_yr.dropna(subset=["sinan_clean","year"])
          .drop_duplicates("sinan_clean").set_index("sinan_clean")["year"].to_dict())
cohort_all["year"] = cohort_all["sinan_clean"].map(yr_map)
cohort_all = cohort_all[cohort_all["year"].between(2020, 2024)]

TOTAL_CASES = len(cohort_all)
print(f"  Cases 2020-2024: {TOTAL_CASES:,}")

# ── 3. Build bairro-level units ────────────────────────────────────────────────
print("Building bairro units...")

# Assign each sector to FCU or bairro
def assign(row):
    nm = row["NM_FCU"]
    if pd.notna(nm) and nm in qualifying_fcus:
        return f"fcu__{nm}", nm, "FCU"
    return row["bairro_id"], row["bairro_label"], "bairro"

asgn = sec_res.apply(assign, axis=1, result_type="expand")
asgn.columns = ["unit_id","label","unit_type"]
sec_w = pd.concat([sec_res.reset_index(drop=True), asgn], axis=1)

# Case counts per sector (pooled 5yr)
sec_cases = cohort_all.groupby("CD_SETOR").size().rename("n_cases").reset_index()
sec_w = sec_w.merge(sec_cases, on="CD_SETOR", how="left")
sec_w["n_cases"] = sec_w["n_cases"].fillna(0)

unit_df = sec_w.groupby("unit_id").agg(
    pop=("pop","sum"), label=("label","first"), unit_type=("unit_type","first"),
    n_cases=("n_cases","sum"), CD_MUN=("CD_MUN","first"),
).reset_index()
unit_df["rate"] = unit_df["n_cases"] / (unit_df["pop"] * 5) * 1e5

print(f"  FCU units:    {(unit_df['unit_type']=='FCU').sum():,}")
print(f"  Bairro units: {(unit_df['unit_type']=='bairro').sum():,}")

# ── 4. Spatial adjacency for bairro merging ────────────────────────────────────
print("Computing bairro spatial adjacency...")

# Build bairro geometries (dissolve within each unit_id)
bairro_rows = sec_w[sec_w["unit_type"] == "bairro"].copy().set_index("unit_id")
bairro_geom_gdf = gpd.GeoDataFrame(
    bairro_rows[["CD_MUN","geometry"]], geometry="geometry", crs=sec_res.crs
).dissolve(by="unit_id").reset_index()
bairro_geom_gdf = bairro_geom_gdf.merge(
    unit_df[unit_df["unit_type"]=="bairro"][["unit_id","n_cases","pop","rate","label"]],
    on="unit_id", how="left"
)
mun_map = unit_df.set_index("unit_id")["CD_MUN"].to_dict()
bairro_geom_gdf["CD_MUN"] = bairro_geom_gdf["unit_id"].map(mun_map)

# Project to metres for buffer
bairro_proj = bairro_geom_gdf.to_crs("EPSG:31983")
bairro_buf  = bairro_proj.copy()
bairro_buf["geometry"] = bairro_buf["geometry"].buffer(5)

adj = gpd.sjoin(
    bairro_buf[["unit_id","CD_MUN","geometry"]].rename(columns={"unit_id":"u_l","CD_MUN":"m_l"}),
    bairro_buf[["unit_id","CD_MUN","geometry"]].rename(columns={"unit_id":"u_r","CD_MUN":"m_r"}),
    how="inner", predicate="intersects"
)
adj = adj[(adj["u_l"] != adj["u_r"]) & (adj["m_l"] == adj["m_r"])]
adj_dict = adj.groupby("u_l")["u_r"].apply(set).to_dict()
print(f"  Bairro adjacency: {len(adj_dict):,} units have neighbours")

# ── 5. Merging function ────────────────────────────────────────────────────────
def merge_small_bairros(min_pop):
    """
    For bairros with >= MIN_CASES but < min_pop:
      Greedily absorb the highest-rate adjacent bairro (within same municipality)
      until pop >= min_pop.  Stop early if no unmerged neighbours remain.
    Returns a pool DataFrame of all eligible units (FCU + merged/unmerged bairros).
    """
    # Start with a mutable copy of bairro units
    bairro_pool = unit_df[unit_df["unit_type"] == "bairro"].copy()
    merged_into  = {}  # bairro_id → group_id (for bairros absorbed into a growing unit)
    groups = {}        # group_id → dict with accumulated stats

    # Only bairros with >= MIN_CASES are "active" — below-threshold bairros sit out
    active = set(bairro_pool[bairro_pool["n_cases"] >= MIN_CASES]["unit_id"])

    if min_pop == 0:
        # No merging: return eligible bairros as-is
        elig_bairro = bairro_pool[bairro_pool["n_cases"] >= MIN_CASES].copy()
        elig_bairro["unit_type"] = "bairro"
        elig_bairro["n_bairros"] = 1
    else:
        # Seed from highest-rate bairro downward
        active_df = bairro_pool[bairro_pool["unit_id"].isin(active)].sort_values("rate", ascending=False)

        gc = 0
        for _, row in active_df.iterrows():
            uid = row["unit_id"]
            if uid in merged_into:
                continue
            # Start a new group with this bairro as seed
            gid = f"mg_{gc}"; gc += 1
            members = [uid]
            merged_into[uid] = gid
            g_pop    = row["pop"]
            g_cases  = row["n_cases"]
            g_labels = [row["label"]]
            g_mun    = row["CD_MUN"]

            # Grow until pop >= min_pop
            frontier = {uid}
            while g_pop < min_pop:
                candidates = []
                for fid in frontier:
                    for nbr in adj_dict.get(fid, set()):
                        nbr_row = bairro_pool[bairro_pool["unit_id"] == nbr]
                        if len(nbr_row) and nbr not in merged_into:
                            candidates.append(nbr_row.iloc[0])
                if not candidates:
                    break
                best = max(candidates, key=lambda x: x["rate"])
                merged_into[best["unit_id"]] = gid
                members.append(best["unit_id"])
                g_pop    += best["pop"]
                g_cases  += best["n_cases"]
                g_labels.append(best["label"])
                frontier = {best["unit_id"]}

            groups[gid] = {
                "unit_id":   gid,
                "label":     g_labels[0] + ("+" if len(g_labels)>1 else ""),
                "unit_type": "bairro" if len(members)==1 else "micro_community",
                "n_cases":   g_cases,
                "pop":       g_pop,
                "rate":      g_cases / (g_pop * 5) * 1e5 if g_pop > 0 else 0,
                "n_bairros": len(members),
            }

        elig_bairro = pd.DataFrame(list(groups.values()))
        elig_bairro = elig_bairro[elig_bairro["n_cases"] >= MIN_CASES].copy()

    # Combine FCU + bairro/micro_community
    fcu_elig = unit_df[(unit_df["unit_type"]=="FCU") & (unit_df["n_cases"]>=MIN_CASES)].copy()
    fcu_elig["n_bairros"] = 1
    pool = pd.concat([fcu_elig[["unit_id","label","unit_type","n_cases","pop","rate","n_bairros"]],
                      elig_bairro[["unit_id","label","unit_type","n_cases","pop","rate","n_bairros"]]],
                     ignore_index=True)
    return pool

# ── 6. Select units (20% pop window) ──────────────────────────────────────────
def select(pool):
    s = pool.sort_values("rate", ascending=False).copy()
    s["cum_pop"] = s["pop"].cumsum()
    target = TOTAL_POP * 0.20
    mask = s["cum_pop"] <= target
    if mask.sum() < len(s): mask.iloc[mask.sum()] = True
    return s[mask]

# ── 7. Jaccard (pooled-unit-pool, year-specific ranking) ──────────────────────
def jaccard(pool):
    sec2unit = sec_w.set_index("CD_SETOR")["unit_id"].to_dict()
    cohort_all["unit_id_tmp"] = cohort_all["CD_SETOR"].map(sec2unit)
    target = TOTAL_POP * 0.20
    jacs = []
    for ya, yb in zip([2020,2021,2022,2023],[2021,2022,2023,2024]):
        sets = []
        for yr in [ya, yb]:
            yc = (cohort_all[cohort_all["year"]==yr]
                  .dropna(subset=["unit_id_tmp"])
                  .groupby("unit_id_tmp").size().rename("n_yr").reset_index()
                  .rename(columns={"unit_id_tmp":"unit_id"}))
            yp = pool[["unit_id","pop"]].merge(yc, on="unit_id", how="left")
            yp["n_yr"] = yp["n_yr"].fillna(0)
            yp["rate_yr"] = yp["n_yr"] / yp["pop"] * 1e5
            yp = yp.sort_values("rate_yr", ascending=False).copy()
            yp["cum"] = yp["pop"].cumsum()
            m = yp["cum"] <= target
            if m.sum() < len(yp): m.iloc[m.sum()] = True
            sets.append(set(yp[m]["unit_id"]))
        i = sets[0] & sets[1]; u = sets[0] | sets[1]
        jacs.append(len(i)/len(u) if u else 0)
    return jacs

# ── 8. Run all thresholds ──────────────────────────────────────────────────────
thresholds = [0, 1000, 2000, 5000]
results = []

for mp in thresholds:
    label = f"min_pop={mp:,}" if mp else "no min"
    print(f"\nRunning {label}...")
    pool = merge_small_bairros(mp)
    sel  = select(pool)
    jacs = jaccard(pool)

    n_mc = int((sel["unit_type"]=="micro_community").sum())
    n_b  = int((sel["unit_type"]=="bairro").sum())
    n_f  = int((sel["unit_type"]=="FCU").sum())

    r = {
        "label":          label,
        "min_pop":        mp,
        "n_eligible":     len(pool),
        "n_sel":          len(sel),
        "n_sel_fcu":      n_f,
        "n_sel_bairro":   n_b,
        "n_sel_micro":    n_mc,
        "pop_M":          round(sel["pop"].sum()/1e6, 2),
        "pct_pop":        round(sel["pop"].sum()/TOTAL_POP*100, 1),
        "pct_cases":      round(sel["n_cases"].sum()/TOTAL_CASES*100, 1),
        "mean_rate":      round(sel["n_cases"].sum()/(sel["pop"].sum()*5)*1e5, 0),
        "median_pop_sel": int(sel["pop"].median()),
        "min_pop_sel":    int(sel["pop"].min()),
        "pct_lt1k":       round((sel["pop"]<1000).sum()/len(sel)*100, 1),
        "pct_lt2k":       round((sel["pop"]<2000).sum()/len(sel)*100, 1),
        "jaccard_mean":   round(np.mean(jacs), 3),
        "jaccard_detail": [round(j,3) for j in jacs],
        "_sel":           sel,
    }
    results.append(r)
    print(f"  {n_f}FCU + {n_b}bairro + {n_mc}micro | pop={r['pct_pop']:.1f}% "
          f"cases={r['pct_cases']:.1f}% rate={r['mean_rate']:.0f} Jac={r['jaccard_mean']:.3f} "
          f"medPop={r['median_pop_sel']:,} <1k={r['pct_lt1k']:.0f}%")

# ── 9. Print table ─────────────────────────────────────────────────────────────
print(f"\n{'='*115}")
print(f"{'Strategy':<18} {'Elig':>6} {'Sel':>5} {'(F+B+M)':>10} {'Pop%':>6} {'Cases%':>7} {'Rate':>6} "
      f"{'Jac':>6} {'MedPop':>8} {'<1k%':>6} {'<2k%':>6}")
print(f"{'-'*115}")
for r in results:
    mix = f"({r['n_sel_fcu']}F+{r['n_sel_bairro']}B+{r['n_sel_micro']}M)"
    print(f"{r['label']:<18} {r['n_eligible']:>6} {r['n_sel']:>5} {mix:>10} "
          f"{r['pct_pop']:>5.1f}% {r['pct_cases']:>6.1f}% {r['mean_rate']:>6.0f} "
          f"{r['jaccard_mean']:>6.3f} {r['median_pop_sel']:>8,} {r['pct_lt1k']:>5.0f}% {r['pct_lt2k']:>5.0f}%")

print("\nJaccard detail:")
for r in results:
    print(f"  {r['label']}: {r['jaccard_detail']}")

# ── 10. Top 30 units for the recommended strategy (min_pop=2000) ──────────────
rec = next(r for r in results if r["min_pop"] == 2000)
print(f"\n=== Top 30 units by TB rate: {rec['label']} ===")
top = rec["_sel"].nlargest(30,"rate")[["label","unit_type","pop","n_cases","rate"]]
print(top.to_string(index=False))

print(f"\n=== Bottom 10 selected units: {rec['label']} ===")
bot = rec["_sel"].nsmallest(10,"rate")[["label","unit_type","pop","n_cases","rate"]]
print(bot.to_string(index=False))

# Geographic spread
print(f"\n=== Municipalities with selected units ({rec['label']}) ===")
sel2 = rec["_sel"].copy()
# Map back to municipality
sel2_sec = sec_w.groupby("unit_id")["NM_MUN"].first().to_dict()
sel2["NM_MUN"] = sel2["unit_id"].apply(lambda x: sel2_sec.get(x, x.split("__")[-1] if "__" in x else ""))
mun_ct = sel2.groupby("NM_MUN").agg(n_units=("unit_id","count"), pop=("pop","sum"),
                                     n_cases=("n_cases","sum")).sort_values("n_units", ascending=False)
mun_ct["rate"] = mun_ct["n_cases"] / (mun_ct["pop"] * 5) * 1e5
print(mun_ct.head(20).to_string())

# ── 11. Plot ───────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 3, figsize=(20, 11))
fig.suptitle(f"Full SP state targeting analysis · {TOTAL_POP/1e6:.0f}M pop · "
             f"{TOTAL_CASES:,} cases 2020-2024\n"
             "FCU + Bairro + Micro-community units · 20% population window",
             fontsize=12, fontweight="bold")

labels_short = ["No\nmin", "≥1,000", "≥2,000", "≥5,000"]
cols = ["#95a5a6","#3498db","#27ae60","#1a3d5c"]

def panel_bar(ax, vals, title, ylabel, fmt="{:.1f}", pad=0.05):
    bars = ax.bar(labels_short, vals, color=cols, edgecolor="white", lw=0.8)
    rng = max(vals) - min(vals) if max(vals) != min(vals) else 1
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x()+bar.get_width()/2, v + rng*pad,
                fmt.format(v), ha="center", fontsize=10, fontweight="bold")
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_ylim(min(vals)*0.9, max(vals)*1.15)
    ax.grid(axis="y", alpha=0.3)

panel_bar(axes[0,0],
          [r["pct_cases"] for r in results],
          "A) Case concentration (20% pop)",
          "% of cases captured", fmt="{:.1f}%")

panel_bar(axes[0,1],
          [r["jaccard_mean"] for r in results],
          "B) Year-to-year stability",
          "Mean Jaccard index", fmt="{:.3f}")

panel_bar(axes[0,2],
          [r["n_sel"] for r in results],
          "C) Number of selected units\n(operational sites)",
          "Units", fmt="{:.0f}")

panel_bar(axes[1,0],
          [r["median_pop_sel"] for r in results],
          "D) Median unit population",
          "Population", fmt="{:,.0f}")

panel_bar(axes[1,1],
          [r["pct_lt1k"] for r in results],
          "E) % units < 1,000 pop\n(small islands)",
          "% of selected units", fmt="{:.0f}%")

# Panel F: population distribution for each threshold
ax = axes[1,2]
for r, col in zip(results, cols):
    pops = r["_sel"]["pop"].values
    ax.hist(np.log10(pops+1), bins=30, alpha=0.5, color=col, label=r["label"], density=True)
ax.set_xlabel("Unit population (log10 scale)")
ax.set_xticks([2,3,4,5])
ax.set_xticklabels(["100","1k","10k","100k"])
ax.set_title("F) Unit size distribution", fontsize=10, fontweight="bold")
ax.legend(fontsize=8); ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig("/tmp/sp_state_targeting_comparison.png", dpi=150,
            bbox_inches="tight", facecolor="white")
plt.close()
print("\nSaved: /tmp/sp_state_targeting_comparison.png")

# Save selected unit lists
for r in results:
    mp = r["min_pop"]
    r["_sel"].drop(columns="cum_pop", errors="ignore").to_csv(
        f"/tmp/sp_state_selected_minpop{mp}.csv", index=False
    )
    print(f"Saved: /tmp/sp_state_selected_minpop{mp}.csv ({len(r['_sel'])} units)")

print("Done.")
