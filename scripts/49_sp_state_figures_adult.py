"""SP state targeting figures — adults (≥15 years) only.

Identical methodology to 49_sp_state_figures.py but:
  • Population denominator = IBGE 2022 pop aged ≥15 per census sector
    (V01034–V01041 from Agregados_por_setores_demografia_BR.csv)
  • TB cases filtered to age_tb ≥ 15 (excludes ~2.6% paediatric + ~0.1% unknown age)

Outputs (saved to /tmp/):
  fig1_lorenz_adult.png
  fig2_map_adult.png
  fig3_stability_adult.png
  fig4_table_adult.png
"""

import time
import zipfile
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from shapely.ops import unary_union

matplotlib.rcParams.update({"font.family": "sans-serif", "font.size": 11})

SPATIAL   = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL   = "3550308"
FCU_MIN   = 5000
MIN_CASES = 10
POP_WIN   = 0.20

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s

# ── DATA LOADING ───────────────────────────────────────────────────────────────
print("Loading sectors + population...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]   = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)

pop_df = pd.read_csv(
    f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
    sep=";", encoding="latin-1", decimal=",",
    usecols=["CD_SETOR","v0001"], dtype={"CD_SETOR":str}, low_memory=False,
)
pop_df["pop_total"] = pd.to_numeric(pop_df["v0001"], errors="coerce").fillna(0)

# ── ADULT POPULATION (≥15 years) ──────────────────────────────────────────────
print("Loading adult population (≥15 years)...")
ADULT_COLS = ["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
DEMO_ZIP   = f"{SPATIAL}/IBGE_2022_extended/demografia.zip"
with zipfile.ZipFile(DEMO_ZIP) as z:
    with z.open("Agregados_por_setores_demografia_BR.csv") as f:
        demo_df = pd.read_csv(f, sep=";", encoding="latin-1", decimal=",",
                              usecols=["CD_setor"] + ADULT_COLS,
                              dtype={"CD_setor": str}, low_memory=False)
demo_df["pop_adult"] = (demo_df[ADULT_COLS]
                        .apply(pd.to_numeric, errors="coerce")
                        .fillna(0).sum(axis=1))
demo_df = demo_df[["CD_setor", "pop_adult"]].rename(columns={"CD_setor": "CD_SETOR"})

pop_df = pop_df.merge(demo_df, on="CD_SETOR", how="left")
pop_df["pop_adult"] = pop_df["pop_adult"].fillna(0)

sec = sec22.merge(pop_df[["CD_SETOR","pop_adult"]], on="CD_SETOR", how="left")
sec["pop_adult"] = sec["pop_adult"].fillna(0)
# Keep sectors with ≥100 total residents (same filter as all-ages, use pop_total for filter)
pop_total_df = pop_df[["CD_SETOR","pop_total"]].copy()
sec = sec.merge(pop_total_df, on="CD_SETOR", how="left")
sec["pop_total"] = sec["pop_total"].fillna(0)
sec_res = sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["pop_total"] >= 100)].copy()
sec_res = sec_res.rename(columns={"pop_adult": "pop"})   # use adult pop as 'pop' throughout

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

fcu_pop = sec_res[sec_res["NM_FCU"].notna()].groupby("NM_FCU")["pop"].sum()
qualifying_fcus = set(fcu_pop[fcu_pop >= FCU_MIN].index)
TOTAL_POP = sec_res["pop"].sum()   # adult (≥15) population

def assign(row):
    nm = row["NM_FCU"]
    if pd.notna(nm) and nm in qualifying_fcus:
        return f"fcu__{nm}", nm, "FCU"
    return row["bairro_id"], row["bairro_label"], "bairro"

asgn = sec_res.apply(assign, axis=1, result_type="expand")
asgn.columns = ["unit_id","label","unit_type"]
sec_w = pd.concat([sec_res.reset_index(drop=True), asgn.reset_index(drop=True)], axis=1)

# ── CASES (adults only) ───────────────────────────────────────────────────────
print("Loading cases (adults ≥15 years)...")
def load_co(path, tier_filter=True):
    df = pd.read_csv(path, low_memory=False, dtype={"sinan_clean":str})
    if tier_filter:
        df["tier"] = df["cnefe_match"].astype(str).str.extract(r"^(T\d)")
        df = df[df["tier"].isin(["T1","T2","T3"])]
    df["CD_SETOR"] = df["setor_cnefe"].apply(norm_setor)
    return df[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])

gsp_co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False, dtype={"sinan_clean":str})
gsp_co["CD_SETOR"] = gsp_co["setor_cnefe"].apply(norm_setor)
gsp_co = gsp_co[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])

cohort_all = pd.concat([gsp_co,
                        load_co("/tmp/cohort_baixada_with_cnefe_v2.csv"),
                        load_co("/tmp/cohort_sp_outros_with_cnefe.csv")],
                       ignore_index=True)

cohort_meta = pd.read_csv(f"{SPATIAL}/cohort_with_spatial.csv",
                          usecols=["sinan_clean","notification_date","age_tb"],
                          low_memory=False, dtype={"sinan_clean":str})
cohort_meta["year"] = pd.to_datetime(cohort_meta["notification_date"], errors="coerce").dt.year

meta_dedup = cohort_meta.dropna(subset=["sinan_clean"]).drop_duplicates("sinan_clean")
yr_map  = meta_dedup.set_index("sinan_clean")["year"].to_dict()
age_map = meta_dedup.set_index("sinan_clean")["age_tb"].to_dict()

cohort_all["year"]   = cohort_all["sinan_clean"].map(yr_map)
cohort_all["age_tb"] = cohort_all["sinan_clean"].map(age_map)

# Apply year + age filters
cohort_all = cohort_all[cohort_all["year"].between(2013, 2024)]
cohort_all = cohort_all[cohort_all["age_tb"] >= 15]   # ← adult filter
TOTAL_CASES = len(cohort_all)
print(f"  Adult pop {TOTAL_POP/1e6:.1f}M | Adult TB cases 2013-2024: {TOTAL_CASES:,}")

# Unit-level aggregation
cohort_all["unit_id"] = cohort_all["CD_SETOR"].map(sec_w.set_index("CD_SETOR")["unit_id"].to_dict())
sec_cases_pooled = cohort_all.groupby("unit_id").size().rename("n_cases").reset_index()

unit_df = sec_w.groupby("unit_id").agg(
    pop=("pop","sum"), label=("label","first"), unit_type=("unit_type","first"),
).reset_index()
unit_df = unit_df.merge(sec_cases_pooled, on="unit_id", how="left")
unit_df["n_cases"] = unit_df["n_cases"].fillna(0)
unit_df["rate"]    = unit_df["n_cases"] / (unit_df["pop"] * 12) * 1e5

# Selection: ≥ MIN_CASES pooled 5yr, ranked by rate, until 20% of adult pop
elig_df = unit_df[unit_df["n_cases"] >= MIN_CASES].copy()
elig_df = elig_df.sort_values("rate", ascending=False)
elig_df["cum_pop"] = elig_df["pop"].cumsum()
target_pop = TOTAL_POP * POP_WIN
mask = elig_df["cum_pop"] <= target_pop
if mask.sum() < len(elig_df): mask.iloc[mask.sum()] = True
sel_df = elig_df[mask].copy()
selected_ids = set(sel_df["unit_id"])
print(f"  Units total: {len(unit_df):,} | Eligible: {len(elig_df):,} | Selected: {len(sel_df)}")

# Year-specific selections
yr_unit = cohort_all.dropna(subset=["unit_id"]).groupby(["unit_id","year"]).size().reset_index(name="n_yr")

def select_for_year(yr):
    yc = yr_unit[yr_unit["year"] == yr][["unit_id","n_yr"]]
    yp = elig_df[["unit_id","pop"]].merge(yc, on="unit_id", how="left")
    yp["n_yr"]    = yp["n_yr"].fillna(0)
    yp["rate_yr"] = yp["n_yr"] / yp["pop"] * 1e5
    yp = yp.sort_values("rate_yr", ascending=False).copy()
    yp["cum"] = yp["pop"].cumsum()
    target = TOTAL_POP * POP_WIN
    mask = yp["cum"] <= target
    if mask.sum() < len(yp): mask.iloc[mask.sum()] = True
    return set(yp[mask]["unit_id"])

print("Computing year-specific selections...")
yr_selections = {yr: select_for_year(yr) for yr in range(2013, 2025)}

PAIRS = [(y,y+1) for y in range(2013,2024)]
jacs  = []
for ya, yb in PAIRS:
    i = yr_selections[ya] & yr_selections[yb]
    u = yr_selections[ya] | yr_selections[yb]
    jacs.append(len(i)/len(u) if u else 0)
print(f"  Jaccard: {[round(j,3) for j in jacs]}  mean={np.mean(jacs):.3f}")

all_sel_ever = set.union(*yr_selections.values())
stability = {}
for uid in all_sel_ever:
    stability[uid] = sum(1 for yr in range(2013,2025) if uid in yr_selections[yr])
stability_s = pd.Series(stability).rename("years_selected")
unit_df["stability"] = unit_df["unit_id"].map(stability_s).fillna(0).astype(int)

fixed_pct   = {}
optimal_pct = {}
for yr in range(2013, 2025):
    yc = yr_unit[yr_unit["year"]==yr][["unit_id","n_yr"]]
    total_yr = yc["n_yr"].sum()
    fixed_pct[yr]   = yc[yc["unit_id"].isin(selected_ids)]["n_yr"].sum() / total_yr * 100 if total_yr else 0
    optimal_pct[yr] = yc[yc["unit_id"].isin(yr_selections[yr])]["n_yr"].sum() / total_yr * 100 if total_yr else 0

# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 1: Lorenz Curve
# ══════════════════════════════════════════════════════════════════════════════
print("\nFigure 1: Lorenz curve...")
CASES_MAPPED = unit_df["n_cases"].sum()
all_u = unit_df.sort_values("rate", ascending=False).copy()
all_u["cum_pop"]   = all_u["pop"].cumsum() / TOTAL_POP * 100
all_u["cum_cases"] = all_u["n_cases"].cumsum() / CASES_MAPPED * 100

idx_20       = np.searchsorted(all_u["cum_pop"].values, POP_WIN*100)
sel_cases_20 = all_u["n_cases"].cumsum().iloc[min(idx_20, len(all_u)-1)]
cases_at_20_mapped = sel_cases_20 / CASES_MAPPED * 100
cases_at_20_all    = sel_cases_20 / TOTAL_CASES * 100

x_lor = np.concatenate([[0], all_u["cum_pop"].values / 100])
y_lor = np.concatenate([[0], all_u["cum_cases"].values / 100])
gini  = 2 * np.trapz(y_lor, x_lor) - 1

fig1, ax = plt.subplots(figsize=(7, 6.2))
ax.plot([0,100],[0,100], ls="--", color="#aaaaaa", lw=1.2, label="Line of equality", zorder=1)
ax.fill_between(all_u["cum_pop"], all_u["cum_pop"], all_u["cum_cases"],
                alpha=0.10, color="#1a3d5c", zorder=2)
ax.plot(all_u["cum_pop"], all_u["cum_cases"],
        color="#1a3d5c", lw=2.2, label=f"TB case distribution  (Gini = {gini:.3f})", zorder=3)
ax.axvline(POP_WIN*100, color="#c0392b", ls=":", lw=1.5, zorder=4)
ax.scatter([POP_WIN*100], [cases_at_20_mapped], color="#c0392b", zorder=5, s=55)
ax.annotate(
    f"Top 20% of adult population\n→ {cases_at_20_all:.1f}% of adult TB cases",
    xy=(POP_WIN*100, cases_at_20_mapped), xytext=(28, cases_at_20_mapped - 11),
    fontsize=10, color="#c0392b",
    arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.2),
)
ax.set_xlabel("Cumulative % of SP state adult population (≥15 years)\n(bairros ranked highest → lowest TB rate)", fontsize=11)
ax.set_ylabel("Cumulative % of adult TB cases (2013–2024)", fontsize=11)
ax.set_title(f"TB case concentration — São Paulo state  ·  Adults ≥15 years\n"
             f"Bairro/FCU-level analysis  ·  {len(all_u):,} geographic units  ·  "
             f"{TOTAL_POP/1e6:.0f}M adults",
             fontsize=12, fontweight="bold", pad=10)
ax.set_xlim(0,100); ax.set_ylim(0,100)
ax.legend(fontsize=10, loc="upper left")
ax.grid(alpha=0.25)
plt.tight_layout()
plt.savefig("/tmp/fig1_lorenz_adult.png", dpi=180, bbox_inches="tight", facecolor="white")
plt.close()
print("  Saved /tmp/fig1_lorenz_adult.png")

# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 2: Map of selected hotspot units
# ══════════════════════════════════════════════════════════════════════════════
print("\nFigure 2: Map...")
print("  Dissolving municipalities (background)...")
t0 = time.time()
mun_bg = sec22[["CD_MUN","geometry"]].dissolve(by="CD_MUN").reset_index()
print(f"  {len(mun_bg)} municipality polygons ({time.time()-t0:.0f}s)")

print("  Dissolving selected units...")
t1 = time.time()
sec_w["rate_unit"] = sec_w["unit_id"].map(unit_df.set_index("unit_id")["rate"].to_dict())
sel_secs = sec_w[sec_w["unit_id"].isin(selected_ids)].copy()
sel_geom = (gpd.GeoDataFrame(sel_secs[["unit_id","rate_unit","geometry"]],
                              geometry="geometry", crs=sec_res.crs)
            .dissolve(by="unit_id", aggfunc={"rate_unit":"first"}).reset_index())
print(f"  {len(sel_geom)} selected unit polygons ({time.time()-t1:.0f}s)")

vmin, vmax = 45, 300
cmap_map = plt.cm.YlOrRd
norm_map  = mcolors.Normalize(vmin=vmin, vmax=vmax)

fig2, ax = plt.subplots(figsize=(14, 10))
mun_bg.plot(ax=ax, color="#efefef", edgecolor="#c8c8c8", linewidth=0.3)
sel_geom["rate_c"] = sel_geom["rate_unit"].clip(vmin, vmax)
sel_geom.plot(ax=ax, column="rate_c", cmap=cmap_map, norm=norm_map,
              edgecolor="#333333", linewidth=0.2, legend=False)

sm = plt.cm.ScalarMappable(cmap=cmap_map, norm=norm_map)
sm.set_array([])
cbar = fig2.colorbar(sm, ax=ax, shrink=0.42, pad=0.01, aspect=18)
cbar.set_label("TB incidence rate\n(per 100,000 adults · 5-year pooled)", fontsize=9.5)
cbar.ax.text(1.12, 1.03, f"≥{vmax}", transform=cbar.ax.transAxes, fontsize=8, ha="left")

CITIES = {
    "São Paulo":              (-46.633, -23.548),
    "Campinas":               (-47.060, -22.906),
    "Santos":                 (-46.333, -23.960),
    "Ribeirão Preto":         (-47.807, -21.177),
    "São José dos Campos":    (-45.886, -23.179),
    "Sorocaba":               (-47.458, -23.501),
    "Pres. Prudente":         (-51.389, -22.121),
    "São J. Rio Preto":       (-49.379, -20.819),
    "Guarujá":                (-46.264, -23.993),
}
for city, (lon, lat) in CITIES.items():
    ax.annotate(city, xy=(lon, lat), fontsize=7.5, color="#222222",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75))

sel_patch   = mpatches.Patch(facecolor=cmap_map(0.7), edgecolor="#333333", lw=0.5,
                              label=f"Selected hotspot areas  (n = {len(sel_geom):,})")
nosel_patch = mpatches.Patch(facecolor="#efefef", edgecolor="#c8c8c8", lw=0.5,
                              label="Non-selected areas")
ax.legend(handles=[sel_patch, nosel_patch], loc="lower left", fontsize=9,
          framealpha=0.92, edgecolor="#cccccc")
ax.set_title(f"TB hotspot areas — São Paulo state  ·  Adults ≥15 years  ·  2013–2024\n"
             f"{len(sel_geom):,} units  ·  {TOTAL_POP*POP_WIN/1e6:.1f}M adults (20% of state adult pop)  ·  "
             f"{cases_at_20_all:.1f}% of adult TB cases",
             fontsize=12, fontweight="bold", pad=12)
ax.set_xlabel("Longitude", fontsize=9); ax.set_ylabel("Latitude", fontsize=9)
ax.tick_params(labelsize=8); ax.set_aspect("equal")
plt.tight_layout()
plt.savefig("/tmp/fig2_map_adult.png", dpi=180, bbox_inches="tight", facecolor="white")
plt.close()
print("  Saved /tmp/fig2_map_adult.png")

# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 3: Stability
# ══════════════════════════════════════════════════════════════════════════════
print("\nFigure 3: Stability...")
all_sel_ids = all_sel_ever
sec_w["stability"] = sec_w["unit_id"].map(stability_s).fillna(0).astype(int)
stab_secs = sec_w[sec_w["unit_id"].isin(all_sel_ids)].copy()
stab_geom = (gpd.GeoDataFrame(stab_secs[["unit_id","stability","geometry"]],
                               geometry="geometry", crs=sec_res.crs)
             .dissolve(by="unit_id", aggfunc={"stability":"first"}).reset_index())

fig3, axes = plt.subplots(1, 2, figsize=(17, 9),
                           gridspec_kw={"width_ratios": [1, 1.8]})

ax = axes[0]
pair_labels = [f"{a%100}→{b%100}" for a,b in PAIRS]
bar_colors  = ["#2980b9","#27ae60","#8e44ad","#e67e22"]
bars = ax.bar(pair_labels, jacs, color=bar_colors, edgecolor="white", width=0.55)
ax.axhline(np.mean(jacs), color="#c0392b", ls="--", lw=1.5,
           label=f"Mean = {np.mean(jacs):.3f}")
for bar, j in zip(bars, jacs):
    ax.text(bar.get_x()+bar.get_width()/2, j+0.006,
            f"{j:.3f}", ha="center", fontsize=11, fontweight="bold", color="#222222")
ax.set_ylim(0, 0.75)
ax.set_ylabel("Jaccard index (year-to-year overlap)", fontsize=11)
ax.set_title("A)  Year-to-year Jaccard stability\n"
             "(overlap of top-20%-adult-pop selections)", fontsize=11, fontweight="bold")
ax.legend(fontsize=10); ax.grid(axis="y", alpha=0.3)
ax.tick_params(axis="x", labelsize=9, rotation=15)
for spine in ["top","right"]: ax.spines[spine].set_visible(False)
ax.text(0.5, -0.22,
        "Jaccard = |A ∩ B| / |A ∪ B|  where A, B are the sets of selected units\n"
        "in consecutive years.  1.0 = identical selection;  0 = no overlap.",
        transform=ax.transAxes, fontsize=8, color="#555555",
        ha="center", va="top",
        bbox=dict(boxstyle="round,pad=0.3", fc="#f5f5f5", ec="#cccccc"))

ax = axes[1]
mun_bg.plot(ax=ax, color="#efefef", edgecolor="#c8c8c8", linewidth=0.3)
stab_cmap = plt.cm.get_cmap("RdYlGn", 5)
stab_norm = mcolors.BoundaryNorm(boundaries=[0.5,1.5,2.5,3.5,4.5,5.5], ncolors=5)
stab_geom.plot(ax=ax, column="stability", cmap=stab_cmap, norm=stab_norm,
               edgecolor="#444444", linewidth=0.15, legend=False)

score_labels = {
    5: "5/5 years  — always selected (iron hotspot)",
    4: "4/5 years",
    3: "3/5 years",
    2: "2/5 years",
    1: "1/5 years  — marginal hotspot",
}
score_colors = [stab_cmap(i/4) for i in range(5)][::-1]
stab_counts  = stab_geom["stability"].value_counts().sort_index(ascending=False)
handles = []
for score, col in zip([5,4,3,2,1], score_colors):
    n = int(stab_counts.get(score, 0))
    handles.append(mpatches.Patch(
        facecolor=col, edgecolor="#444444", lw=0.5,
        label=f"{score_labels[score]}  (n={n})"
    ))
handles.append(mpatches.Patch(facecolor="#efefef", edgecolor="#c8c8c8", lw=0.5,
                               label="Never selected"))
ax.legend(handles=handles, loc="lower left", fontsize=8.5,
          framealpha=0.93, edgecolor="#cccccc", title="Stability score", title_fontsize=9)

for city, (lon, lat) in CITIES.items():
    ax.annotate(city, xy=(lon, lat), fontsize=7, color="#222222",
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.72))

ax.set_title("B)  Stability score — years each area was in top-20% selection\n"
             f"(adults ≥15 years,  2013–2024,  {len(stab_geom):,} areas ever selected)",
             fontsize=11, fontweight="bold")
ax.set_xlabel("Longitude", fontsize=9); ax.set_ylabel("Latitude", fontsize=9)
ax.tick_params(labelsize=8); ax.set_aspect("equal")

fig3.suptitle("Year-to-year stability of TB hotspot targeting — São Paulo state  ·  Adults ≥15 years",
              fontsize=13, fontweight="bold", y=1.01)
plt.tight_layout()
plt.savefig("/tmp/fig3_stability_adult.png", dpi=180, bbox_inches="tight", facecolor="white")
plt.close()
print("  Saved /tmp/fig3_stability_adult.png")

# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 4: Characteristics table
# ══════════════════════════════════════════════════════════════════════════════
print("\nFigure 4: Characteristics table...")
nosel_ids  = set(unit_df["unit_id"]) - selected_ids
nosel_df2  = unit_df[unit_df["unit_id"].isin(nosel_ids)]

def stats(df):
    pop   = df["pop"].sum()
    cases = df["n_cases"].sum()
    return {
        "n":         len(df),
        "pop":       pop,
        "pct_pop":   pop / TOTAL_POP * 100,
        "cases":     cases,
        "pct_cases": cases / TOTAL_CASES * 100,
        "rate":      cases / (pop * 12) * 1e5 if pop > 0 else 0,
        "med_pop":   int(df["pop"].median()) if len(df) else 0,
    }

sel_fcu_u   = sel_df[sel_df["unit_type"] == "FCU"]
sel_other_u = sel_df[sel_df["unit_type"] != "FCU"]
s_fcu   = stats(sel_fcu_u)
s_oth   = stats(sel_other_u)
s_nos   = stats(nosel_df2)
s_tot   = stats(unit_df)

rows = [
    ("Number of units",                    [s_fcu["n"],         s_oth["n"],         s_nos["n"],         s_tot["n"]]),
    ("Total adult population (≥15 yrs)",   [s_fcu["pop"],       s_oth["pop"],       s_nos["pop"],       s_tot["pop"]]),
    ("% of SP state adult population",     [s_fcu["pct_pop"],   s_oth["pct_pop"],   s_nos["pct_pop"],   100.0]),
    ("Adult TB cases 2013–2024 (N)",       [s_fcu["cases"],     s_oth["cases"],     s_nos["cases"],     s_tot["cases"]]),
    ("% of SP state adult TB cases",       [s_fcu["pct_cases"], s_oth["pct_cases"], s_nos["pct_cases"], 100.0]),
    ("TB incidence rate (per 100k·yr)",    [s_fcu["rate"],      s_oth["rate"],      s_nos["rate"],      s_tot["rate"]]),
    ("Median unit adult population",       [s_fcu["med_pop"],   s_oth["med_pop"],   s_nos["med_pop"],   s_tot["med_pop"]]),
]

def fmt(label, v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    if "%" in label:        return f"{v:.1f}%"
    if "rate" in label:     return f"{v:.0f}"
    if isinstance(v, float): return f"{int(v):,}"
    return f"{int(v):,}"

cell_text  = [[fmt(r[0], v) for v in r[1]] for r in rows]
row_labels = [r[0] for r in rows]
col_labels = ["FCU areas\n(selected)", "Other hotspot\nareas (selected)",
              "Non-selected\nareas", "SP State\ntotal"]

fig4, ax4 = plt.subplots(figsize=(13, 4.6))
ax4.axis("off")
tbl = ax4.table(cellText=cell_text, rowLabels=row_labels, colLabels=col_labels,
                cellLoc="center", rowLoc="left", loc="center")
tbl.auto_set_font_size(False)
tbl.set_fontsize(10.5)
tbl.scale(1, 1.7)

hdr_cols = ["#2c6e9b","#1a6b4a","#5d6d7e","#2c2c2c"]
for j, hc in enumerate(hdr_cols):
    c = tbl[0, j]
    c.set_facecolor(hc); c.set_text_props(color="white", fontweight="bold")

for i in range(len(rows)):
    row_bg = ["#d6e8f5","#e8f5e9","#f0f0f0","#e8e8e8"] if i%2==0 \
             else ["#c8ddf0","#dff0e0","#e4e4e4","#d8d8d8"]
    tbl[i+1, -1].set_text_props(ha="left", fontsize=10, color="#444")
    for j in range(4):
        c = tbl[i+1, j]
        c.set_facecolor(row_bg[j])
        if j == 3: c.set_text_props(fontweight="bold")

ax4.set_title("Characteristics of TB targeting areas — São Paulo state  ·  Adults ≥15 years\n"
              "Min 10 cases / 5 yr  ·  FCU ≥ 5,000 pop  ·  Min unit pop 2,000",
              fontsize=12, fontweight="bold", pad=16, y=0.98)
fig4.text(0.01, 0.01,
          f"SINAN notifications 2013–2024 geocoded to IBGE CNEFE 2022  ·  Adults ≥15 years  ·  "
          f"{TOTAL_POP/1e6:.1f}M adult residents  ·  {TOTAL_CASES:,} adult cases",
          fontsize=8, color="#666")

plt.tight_layout()
plt.savefig("/tmp/fig4_table_adult.png", dpi=180, bbox_inches="tight", facecolor="white")
plt.close()
print("  Saved /tmp/fig4_table_adult.png")

print("\n✓ All adult outputs:")
for f in ["/tmp/fig1_lorenz_adult.png", "/tmp/fig2_map_adult.png",
          "/tmp/fig3_stability_adult.png", "/tmp/fig4_table_adult.png"]:
    print(f"  {f}")
