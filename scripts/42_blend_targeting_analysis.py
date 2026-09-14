"""Blend targeting analysis: FCU-as-unit + non-FCU hotspot bairros.

1) Rebuild bairro + FCU group stats (population, cases, rate)
2) Show population denominators for the characteristics table
3) Evaluate blend strategies:
   - Pure bairro (current 20% window)
   - FCU-named groups only (by NM_FCU, min pop threshold)
   - Blend: FCU groups + non-FCU hotspot bairros
4) Output comparison table
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import zipfile, io, re, unicodedata

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL = "3550308"
BAIXADA_CD_MUN = {"3506359","3513504","3518701","3522109","3531100",
                  "3537602","3541000","3548500","3551009"}

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s

# ── 1. Build sector-level base table ──────────────────────────────────────────
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

GSP_MUNIS = set(sec22[sec22["NM_CONCURB"]=="São Paulo/SP"]["CD_MUN"].unique())
ALL_MUNIS = GSP_MUNIS | BAIXADA_CD_MUN

sec = sec22[sec22["CD_MUN"].isin(ALL_MUNIS)].copy()
sec = sec.merge(agg, on="CD_SETOR", how="left")
sec_res = sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["v0001"]>=100)].copy()

# Hybrid bairro geo_unit
sec_res["geo_unit"] = sec_res.apply(
    lambda r: f"dist_{r['CD_DIST']}" if str(r["CD_MUN"])==CAPITAL
              else (f"bairro_{r['CD_MUN']}_{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"dist_{r['CD_DIST']}"),
    axis=1
)
sec_res["geo_label"] = sec_res.apply(
    lambda r: f"SP/{r['NM_DIST']}" if str(r["CD_MUN"])==CAPITAL
              else (f"{r['NM_MUN']}/{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"{r['NM_MUN']}/{r['NM_DIST']}"),
    axis=1
)
sec_res["is_fcu"] = sec_res["NM_FCU"].notna().astype(int)
sec_res["pop"] = sec_res["v0001"]

TOTAL_POP = sec_res["pop"].sum()
print(f"Total residential population (GSP+Baixada): {TOTAL_POP:,.0f}")

# ── 2. Cases ──────────────────────────────────────────────────────────────────
import os
gsp_co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False, dtype={"sinan_clean":str})
gsp_co["CD_SETOR"] = gsp_co["setor_cnefe"].apply(norm_setor)
bx_co  = pd.read_csv("/tmp/cohort_baixada_with_cnefe_v2.csv", low_memory=False, dtype={"sinan_clean":str})
bx_co["match_tier"] = bx_co["cnefe_match"].astype(str).str.extract(r"^(T\d)")
bx_co  = bx_co[bx_co["match_tier"].isin(["T1","T2","T3"])]
bx_co["CD_SETOR"] = bx_co["setor_cnefe"].apply(norm_setor)

all_co = pd.concat([gsp_co[["CD_SETOR"]], bx_co[["CD_SETOR"]]], ignore_index=True)
all_co = all_co.dropna(subset=["CD_SETOR"])

sec2unit = sec_res.set_index("CD_SETOR")["geo_unit"].to_dict()
all_co["geo_unit"] = all_co["CD_SETOR"].map(sec2unit)
all_co["CD_SETOR_map"] = all_co["CD_SETOR"]

# Also map cases to NM_FCU
sec2fcu  = sec_res.set_index("CD_SETOR")["NM_FCU"].to_dict()
sec2pop  = sec_res.set_index("CD_SETOR")["pop"].to_dict()
all_co["nm_fcu"]  = all_co["CD_SETOR"].map(sec2fcu)
all_co["nm_mun"]  = all_co["CD_SETOR"].map(sec_res.set_index("CD_SETOR")["NM_MUN"].to_dict())
all_co["cd_mun_s"]= all_co["CD_SETOR"].map(sec_res.set_index("CD_SETOR")["CD_MUN"].to_dict())

TOTAL_CASES = len(all_co.dropna(subset=["geo_unit"]))  # geocoded cases only

# ── 3. Bairro-level stats ─────────────────────────────────────────────────────
unit_pop   = sec_res.groupby("geo_unit")["pop"].sum()
fcu_pop_by_unit = sec_res[sec_res["is_fcu"]==1].groupby("geo_unit")["pop"].sum().rename("fcu_pop")
cases_by_unit = all_co.dropna(subset=["geo_unit"]).groupby("geo_unit").size().rename("n_cases")

bairro_df = (unit_pop.rename("pop").reset_index()
             .merge(cases_by_unit.reset_index(), on="geo_unit", how="left")
             .merge(fcu_pop_by_unit.reset_index(), on="geo_unit", how="left"))
bairro_df["n_cases"] = bairro_df["n_cases"].fillna(0)
bairro_df["fcu_pop"] = bairro_df["fcu_pop"].fillna(0)
bairro_df["rate"]    = bairro_df["n_cases"] / (bairro_df["pop"] * 5) * 1e5
bairro_df["geo_label"] = bairro_df["geo_unit"].map(
    sec_res.groupby("geo_unit")["geo_label"].first().to_dict())

# Hotspot bairros: top 20% population window
bairro_sorted = bairro_df.sort_values("rate", ascending=False).copy()
bairro_sorted["cum_pop"] = bairro_sorted["pop"].cumsum()
TARGET_POP = TOTAL_POP * 0.20
hotspot_mask = bairro_sorted["cum_pop"] <= TARGET_POP
# Include one more to cross threshold
if hotspot_mask.sum() < len(bairro_sorted):
    hotspot_mask.iloc[hotspot_mask.sum()] = True
hotspot_units = set(bairro_sorted[hotspot_mask]["geo_unit"])
print(f"\nHotspot bairros (20% window): {len(hotspot_units)} units")

bairro_df["is_hotspot"] = bairro_df["geo_unit"].isin(hotspot_units)

# ── 4. Named FCU groups (by NM_FCU) ──────────────────────────────────────────
print("\nBuilding named FCU group stats...")
fcu_sec = sec_res[sec_res["is_fcu"]==1].copy()

# FCU pop by name (can span multiple sectors, sometimes multiple municipalities)
fcu_pop_grp = fcu_sec.groupby("NM_FCU")["pop"].sum().rename("pop")
fcu_cases_co = all_co[all_co["nm_fcu"].notna()].copy()
fcu_cases_grp = fcu_cases_co.groupby("nm_fcu").size().rename("n_cases")

fcu_df = (fcu_pop_grp.reset_index()
          .merge(fcu_cases_grp.rename("n_cases").reset_index().rename(columns={"nm_fcu":"NM_FCU"}),
                 on="NM_FCU", how="left"))
fcu_df["n_cases"] = fcu_df["n_cases"].fillna(0)
fcu_df["rate"]    = fcu_df["n_cases"] / (fcu_df["pop"] * 5) * 1e5
fcu_df["mun"]     = fcu_df["NM_FCU"].map(
    fcu_sec.groupby("NM_FCU")["NM_MUN"].agg(lambda x: x.mode().iloc[0] if len(x)>0 else "")).fillna("")

print(f"Named FCU groups: {len(fcu_df)}")
print(f"  Total FCU pop: {fcu_df['pop'].sum():,.0f} ({fcu_df['pop'].sum()/TOTAL_POP*100:.1f}% of regional)")
print(f"  FCU size distribution:")
for thr in [500, 1000, 2000, 5000, 10000]:
    n = (fcu_df["pop"] >= thr).sum()
    p = fcu_df[fcu_df["pop"] >= thr]["pop"].sum()
    c = fcu_df[fcu_df["pop"] >= thr]["n_cases"].sum()
    print(f"    ≥{thr:,} pop: {n} FCUs, {p/TOTAL_POP*100:.1f}% of region, {c/TOTAL_CASES*100:.1f}% of cases")

# ── 5. Build comparison of targeting strategies ────────────────────────────────
print("\n=== STRATEGY COMPARISON ===")

strategies = {}

# Strategy A: Current — hotspot bairros (20% window)
hb = bairro_df[bairro_df["is_hotspot"]]
strategies["A_bairros_20pct"] = {
    "label": "A. Hotspot bairros\n(top 20% pop)",
    "n_units": len(hb),
    "pop": hb["pop"].sum(),
    "cases": hb["n_cases"].sum(),
    "median_unit_pop": hb["pop"].median(),
    "min_unit_pop": hb["pop"].min(),
    "pct_units_gt5k": (hb["pop"] >= 5000).mean() * 100,
    "unit_type": "Hybrid bairro/distrito (admin)",
}

# Strategy B: All named FCU groups ≥2,000 pop
FCU_MIN = 2000
fcu_large = fcu_df[fcu_df["pop"] >= FCU_MIN]
strategies["B_fcu_2k"] = {
    "label": f"B. Named FCUs\n(pop ≥ {FCU_MIN:,})",
    "n_units": len(fcu_large),
    "pop": fcu_large["pop"].sum(),
    "cases": fcu_large["n_cases"].sum(),
    "median_unit_pop": fcu_large["pop"].median(),
    "min_unit_pop": fcu_large["pop"].min(),
    "pct_units_gt5k": (fcu_large["pop"] >= 5000).mean() * 100,
    "unit_type": "Named FCU (IBGE 2022)",
}

# Strategy C: All named FCU groups ≥5,000 pop
FCU_MIN2 = 5000
fcu_xlarge = fcu_df[fcu_df["pop"] >= FCU_MIN2]
strategies["C_fcu_5k"] = {
    "label": f"C. Named FCUs\n(pop ≥ {FCU_MIN2:,})",
    "n_units": len(fcu_xlarge),
    "pop": fcu_xlarge["pop"].sum(),
    "cases": fcu_xlarge["n_cases"].sum(),
    "median_unit_pop": fcu_xlarge["pop"].median(),
    "min_unit_pop": fcu_xlarge["pop"].min(),
    "pct_units_gt5k": (fcu_xlarge["pop"] >= 5000).mean() * 100,
    "unit_type": "Named FCU (IBGE 2022)",
}

# Strategy D: Blend — large FCUs (≥2k) + non-FCU hotspot bairros
# For non-FCU hotspot bairros: rank bairros by their non-FCU-sector TB rate,
# take enough to reach same total population as strategy A minus FCU pop already covered
fcu_pop_total = fcu_large["pop"].sum()
fcu_cases_total = fcu_large["n_cases"].sum()

# non-FCU rate for each bairro: cases in non-FCU sectors / non-FCU pop
nonfcu_sec = sec_res[sec_res["is_fcu"]==0].copy()
nonfcu_sec2unit = nonfcu_sec.set_index("CD_SETOR")["geo_unit"].to_dict()
all_co["geo_unit_nonfcu"] = all_co["CD_SETOR"].map(nonfcu_sec2unit)
nonfcu_pop_by_unit = nonfcu_sec.groupby("geo_unit")["pop"].sum().rename("nonfcu_pop")
nonfcu_cases_by_unit = (all_co[all_co["nm_fcu"].isna()]
                         .dropna(subset=["geo_unit"])
                         .groupby("geo_unit").size().rename("nonfcu_cases"))

nonfcu_bairro = (nonfcu_pop_by_unit.reset_index()
                 .merge(nonfcu_cases_by_unit.reset_index(), on="geo_unit", how="left"))
nonfcu_bairro["nonfcu_cases"] = nonfcu_bairro["nonfcu_cases"].fillna(0)
nonfcu_bairro["nonfcu_rate"] = nonfcu_bairro["nonfcu_cases"] / (nonfcu_bairro["nonfcu_pop"] * 5) * 1e5

# Rank by non-FCU rate, take enough to reach 20% regional pop MINUS FCU pop
target_nonfcu_pop = TARGET_POP - fcu_pop_total
nonfcu_sorted = nonfcu_bairro.sort_values("nonfcu_rate", ascending=False).copy()
nonfcu_sorted["cum_pop"] = nonfcu_sorted["nonfcu_pop"].cumsum()
nonfcu_hotspot_mask = nonfcu_sorted["cum_pop"] <= target_nonfcu_pop
if nonfcu_hotspot_mask.sum() < len(nonfcu_sorted) and target_nonfcu_pop > 0:
    nonfcu_hotspot_mask.iloc[nonfcu_hotspot_mask.sum()] = True
nonfcu_hotspot_units = set(nonfcu_sorted[nonfcu_hotspot_mask]["geo_unit"])

# Full pop and cases for those bairros (not just non-FCU portion)
blend_bairros = bairro_df[bairro_df["geo_unit"].isin(nonfcu_hotspot_units)]

blend_total_pop   = fcu_pop_total  + blend_bairros["pop"].sum()
blend_total_cases = fcu_cases_total + blend_bairros["n_cases"].sum()
# Avoid double-counting: some FCU cases are also in hotspot bairros
# Use the non-FCU sector cases from blend bairros + all FCU cases
nonfcu_blend_cases = all_co[all_co["nm_fcu"].isna() & all_co["geo_unit"].isin(nonfcu_hotspot_units)].shape[0]
blend_actual_cases = fcu_cases_total + nonfcu_blend_cases
blend_actual_pop   = fcu_pop_total  + nonfcu_bairro[nonfcu_bairro["geo_unit"].isin(nonfcu_hotspot_units)]["nonfcu_pop"].sum()

strategies["D_blend_2k"] = {
    "label": f"D. Blend: FCUs ≥{FCU_MIN:,}\n+ non-FCU hotspot bairros",
    "n_units": len(fcu_large) + len(blend_bairros),
    "pop": blend_actual_pop,
    "cases": blend_actual_cases,
    "median_unit_pop": pd.concat([fcu_large["pop"],
                                  nonfcu_bairro[nonfcu_bairro["geo_unit"].isin(nonfcu_hotspot_units)]["nonfcu_pop"]]).median(),
    "min_unit_pop": min(fcu_large["pop"].min(),
                        nonfcu_bairro[nonfcu_bairro["geo_unit"].isin(nonfcu_hotspot_units)]["nonfcu_pop"].min()
                        if len(nonfcu_hotspot_units) > 0 else float("inf")),
    "pct_units_gt5k": pd.concat([fcu_large["pop"],
                                  nonfcu_bairro[nonfcu_bairro["geo_unit"].isin(nonfcu_hotspot_units)]["nonfcu_pop"]]
                                 ).ge(5000).mean() * 100,
    "unit_type": "Named FCU + bairro (mixed)",
}

# Strategy E: Same blend but FCU ≥ 5k
nonfcu_hotspot_mask_e = nonfcu_sorted["cum_pop"] <= (TARGET_POP - fcu_xlarge["pop"].sum())
if nonfcu_hotspot_mask_e.sum() < len(nonfcu_sorted) and (TARGET_POP - fcu_xlarge["pop"].sum()) > 0:
    nonfcu_hotspot_mask_e.iloc[nonfcu_hotspot_mask_e.sum()] = True
nonfcu_hotspot_units_e = set(nonfcu_sorted[nonfcu_hotspot_mask_e]["geo_unit"])
blend_bairros_e = bairro_df[bairro_df["geo_unit"].isin(nonfcu_hotspot_units_e)]
nonfcu_blend_cases_e = all_co[all_co["nm_fcu"].isna() & all_co["geo_unit"].isin(nonfcu_hotspot_units_e)].shape[0]
blend_actual_pop_e   = fcu_xlarge["pop"].sum() + nonfcu_bairro[nonfcu_bairro["geo_unit"].isin(nonfcu_hotspot_units_e)]["nonfcu_pop"].sum()
blend_actual_cases_e = fcu_xlarge["n_cases"].sum() + nonfcu_blend_cases_e

strategies["E_blend_5k"] = {
    "label": f"E. Blend: FCUs ≥{FCU_MIN2:,}\n+ non-FCU hotspot bairros",
    "n_units": len(fcu_xlarge) + len(blend_bairros_e),
    "pop": blend_actual_pop_e,
    "cases": blend_actual_cases_e,
    "median_unit_pop": pd.concat([fcu_xlarge["pop"],
                                  nonfcu_bairro[nonfcu_bairro["geo_unit"].isin(nonfcu_hotspot_units_e)]["nonfcu_pop"]]).median(),
    "min_unit_pop": min(fcu_xlarge["pop"].min(),
                        nonfcu_bairro[nonfcu_bairro["geo_unit"].isin(nonfcu_hotspot_units_e)]["nonfcu_pop"].min()
                        if len(nonfcu_hotspot_units_e) > 0 else float("inf")),
    "pct_units_gt5k": pd.concat([fcu_xlarge["pop"],
                                  nonfcu_bairro[nonfcu_bairro["geo_unit"].isin(nonfcu_hotspot_units_e)]["nonfcu_pop"]]
                                 ).ge(5000).mean() * 100,
    "unit_type": "Named FCU + bairro (mixed)",
}

# Print summary
print(f"\n{'Strategy':<40} {'Units':>6} {'Pop (M)':>8} {'% reg':>7} {'Cases/yr':>9} {'% cases':>8} {'Rate':>8} {'Med unit':>9} {'≥5k (%)':>8}")
print("-"*110)
for k, s in strategies.items():
    pop_m  = s["pop"] / 1e6
    pct_p  = s["pop"] / TOTAL_POP * 100
    cases_yr = s["cases"] / 5
    pct_c  = s["cases"] / TOTAL_CASES * 100
    rate   = s["cases"] / (s["pop"] * 5) * 1e5 if s["pop"] > 0 else 0
    med    = s["median_unit_pop"]
    gt5k   = s["pct_units_gt5k"]
    label = s["label"].replace("\n"," ")
    print(f"{label:<40} {s['n_units']:>6} {pop_m:>8.2f} {pct_p:>6.1f}% {cases_yr:>9.0f} {pct_c:>7.1f}% {rate:>8.0f} {med:>9.0f} {gt5k:>7.1f}%")

# ── 6. Population denominators for the updated table ─────────────────────────
print("\n=== POPULATION DENOMINATORS FOR TABLE ===")
hb_pop  = bairro_df[bairro_df["is_hotspot"]]["pop"].sum()
fcu_all_pop = sec_res[sec_res["is_fcu"]==1]["pop"].sum()
nonfcu_pop  = TOTAL_POP - fcu_all_pop
nonsel_pop  = TOTAL_POP - hb_pop

print(f"Total regional pop (GSP+Baixada): {TOTAL_POP/1e6:.2f}M")
print(f"  Hotspot bairros (191):          {hb_pop/1e6:.2f}M ({hb_pop/TOTAL_POP*100:.1f}% of region)")
print(f"  All FCU sectors:                {fcu_all_pop/1e6:.2f}M ({fcu_all_pop/TOTAL_POP*100:.1f}% of region)")
print(f"  Non-selected bairros:           {nonsel_pop/1e6:.2f}M ({nonsel_pop/TOTAL_POP*100:.1f}% of region)")
print(f"\n  Note: hotspot bairros and FCU overlap (19.4% of hotspot pop is in FCU sectors)")

hb_cases   = bairro_df[bairro_df["is_hotspot"]]["n_cases"].sum()
fcu_all_co = all_co[all_co["nm_fcu"].notna()].shape[0]
nonsel_cases = TOTAL_CASES - hb_cases

print(f"\nCases (geocoded, 2020-2024, pooled):")
print(f"  Total geocoded:                 {TOTAL_CASES:,}")
print(f"  Hotspot bairros:                {hb_cases:,.0f} ({hb_cases/TOTAL_CASES*100:.1f}%)")
print(f"  FCU (anywhere):                 {fcu_all_co:,} ({fcu_all_co/TOTAL_CASES*100:.1f}%)")
print(f"  Non-selected:                   {nonsel_cases:,.0f} ({nonsel_cases/TOTAL_CASES*100:.1f}%)")

print(f"\nTB rate /100k·yr:")
print(f"  Hotspot bairros:                {hb_cases/(hb_pop*5)*1e5:.0f}")
print(f"  FCU (anywhere):                 {fcu_all_co/(fcu_all_pop*5)*1e5:.0f}")
print(f"  Non-selected:                   {nonsel_cases/(nonsel_pop*5)*1e5:.0f}")

# ── 7. Named FCU unit size distribution for feasibility ───────────────────────
print("\n=== NAMED FCU SIZE DISTRIBUTION ===")
size_bins = [0, 500, 1000, 2000, 5000, 10000, 30000, float("inf")]
bin_labels = ["<500","500–999","1k–2k","2k–5k","5k–10k","10k–30k","≥30k"]
fcu_df["size_bin"] = pd.cut(fcu_df["pop"], bins=size_bins, labels=bin_labels)
grp = fcu_df.groupby("size_bin", observed=True).agg(
    n_fcu=("NM_FCU","count"),
    pop=("pop","sum"),
    cases=("n_cases","sum"),
).reset_index()
grp["rate"] = grp["cases"] / (grp["pop"] * 5) * 1e5
grp["pct_pop"] = grp["pop"] / TOTAL_POP * 100
grp["pct_cases"] = grp["cases"] / TOTAL_CASES * 100
print(grp.to_string(index=False))

# ── 8. Save outputs ───────────────────────────────────────────────────────────
# Strategy comparison table
rows = []
for k, s in strategies.items():
    rows.append({
        "strategy": k,
        "label": s["label"].replace("\n"," "),
        "n_units": s["n_units"],
        "pop_M": round(s["pop"]/1e6, 2),
        "pct_regional_pop": round(s["pop"]/TOTAL_POP*100, 1),
        "cases_5yr": int(s["cases"]),
        "cases_yr": round(s["cases"]/5, 0),
        "pct_cases": round(s["cases"]/TOTAL_CASES*100, 1),
        "rate_100k": round(s["cases"]/(s["pop"]*5)*1e5, 0) if s["pop"] > 0 else None,
        "median_unit_pop": int(s["median_unit_pop"]),
        "pct_units_ge5k": round(s["pct_units_gt5k"], 1),
        "unit_type": s["unit_type"],
    })
strat_df = pd.DataFrame(rows)
strat_df.to_csv("/tmp/blend_strategy_comparison.csv", index=False)
print(f"\nSaved: /tmp/blend_strategy_comparison.csv")

# FCU size distribution
grp.to_csv("/tmp/fcu_size_distribution.csv", index=False)
print(f"Saved: /tmp/fcu_size_distribution.csv")

# Top FCUs by population (for reference)
fcu_top = fcu_df.nlargest(30, "pop")[["NM_FCU","mun","pop","n_cases","rate"]].copy()
fcu_top["rate"] = fcu_top["rate"].round(0)
fcu_top.to_csv("/tmp/fcu_top30.csv", index=False)
print(f"Saved: /tmp/fcu_top30.csv")

# ── 9. Plot: FCU size distribution + strategy comparison ──────────────────────
fig, axes = plt.subplots(1, 2, figsize=(18, 7))
fig.suptitle("Blend targeting: FCU unit viability + strategy comparison\nGSP + Baixada Santista (2020–2024)",
             fontsize=14, fontweight="bold")

# Panel A: FCU size bins — n_fcu bars, coloured by operational viability
ax = axes[0]
colors_bin = ["#e74c3c","#e74c3c","#f39c12","#f39c12","#27ae60","#27ae60","#27ae60"]
bars = ax.bar(grp["size_bin"], grp["n_fcu"], color=colors_bin, edgecolor="white", linewidth=0.8)

ax2_r = ax.twinx()
ax2_r.plot(grp["size_bin"], grp["rate"], "o--", color="#1a3d5c", lw=2, ms=8, label="TB rate /100k·yr")
ax2_r.set_ylabel("TB rate /100k·yr", color="#1a3d5c", fontsize=11)
ax2_r.tick_params(axis="y", labelcolor="#1a3d5c")

for bar, row in zip(bars, grp.itertuples()):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
            f"n={int(row.n_fcu)}\n{row.pct_pop:.1f}% pop", ha="center", va="bottom", fontsize=9)

ax.set_xlabel("Named FCU population size", fontsize=12)
ax.set_ylabel("Number of named FCUs", fontsize=12)
ax.set_title("A) FCU unit size distribution\n(red = too small for ACF, orange = marginal, green = viable)",
             fontsize=11, fontweight="bold")
for tick in ax.get_xticklabels(): tick.set_rotation(30)

legend_patches = [
    mpatches.Patch(color="#e74c3c", label="<1,000 — too small for ACF"),
    mpatches.Patch(color="#f39c12", label="1k–5k — marginal"),
    mpatches.Patch(color="#27ae60", label="≥5,000 — operationally viable"),
]
ax.legend(handles=legend_patches, fontsize=9, loc="upper right")

# Panel B: Strategy comparison — % pop vs % cases (concentration plot)
ax2 = axes[1]
strategy_keys = list(strategies.keys())
x_pos = range(len(strategy_keys))
pop_pcts   = [strategies[k]["pop"]/TOTAL_POP*100 for k in strategy_keys]
case_pcts  = [strategies[k]["cases"]/TOTAL_CASES*100 for k in strategy_keys]
rates      = [strategies[k]["cases"]/(strategies[k]["pop"]*5)*1e5 if strategies[k]["pop"]>0 else 0 for k in strategy_keys]
labels     = [strategies[k]["label"].replace("\n"," ") for k in strategy_keys]

bar_width = 0.35
x = np.arange(len(strategy_keys))
bars_pop  = ax2.bar(x - bar_width/2, pop_pcts,  bar_width, color="#2980b9", alpha=0.85, label="% of regional population")
bars_case = ax2.bar(x + bar_width/2, case_pcts, bar_width, color="#c0392b", alpha=0.85, label="% of TB cases (5-yr geocoded)")

for bar, v in zip(bars_pop,  pop_pcts):  ax2.text(bar.get_x()+bar.get_width()/2, v+0.3, f"{v:.0f}%", ha="center", fontsize=9)
for bar, v in zip(bars_case, case_pcts): ax2.text(bar.get_x()+bar.get_width()/2, v+0.3, f"{v:.0f}%", ha="center", fontsize=9, color="#c0392b")

# Concentration ratio annotation
for i, (pp, cp) in enumerate(zip(pop_pcts, case_pcts)):
    if pp > 0:
        ratio = cp / pp
        ax2.text(i, max(pp, cp) + 2, f"×{ratio:.1f}", ha="center", fontsize=10,
                 color="#1a3d5c", fontweight="bold")

ax2.set_xticks(x)
ax2.set_xticklabels([s["label"].replace("\n","\n") for s in strategies.values()],
                     fontsize=9, rotation=15, ha="right")
ax2.set_ylabel("% of regional total", fontsize=12)
ax2.set_title("B) Concentration ratio by strategy\n(×N = ratio cases/pop — higher = more concentrated)",
              fontsize=11, fontweight="bold")
ax2.legend(fontsize=10)
ax2.set_ylim(0, max(case_pcts) * 1.25)
ax2.grid(axis="y", alpha=0.3)

plt.tight_layout()
plt.savefig("/tmp/blend_targeting_comparison.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("Saved: /tmp/blend_targeting_comparison.png")
print("\nDone.")
