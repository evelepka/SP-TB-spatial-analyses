"""Bairro-level hotspot analysis — GSP + Baixada Santista.

Geographic unit:
  SP capital   → NM_DIST  (96 distritos, ~100k pop each)
  Other munis  → NM_BAIRRO where available, NM_DIST as fallback

Reports: case numbers, concentration, unit sizes, year-to-year stability
across window sizes 1%–20% of population.
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL  = "3550308"
WINDOWS  = [0.01, 0.02, 0.05, 0.10, 0.15, 0.20]
YEARS    = [2020, 2021, 2022, 2023, 2024]

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s

# ---- 1) Shapefile + census ----
print("Loading shapefile + aggregates...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]   = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)
sec22["AREA_KM2"] = pd.to_numeric(sec22["AREA_KM2"], errors="coerce")

agg = pd.read_csv(
    f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
    sep=";", encoding="latin-1", decimal=",",
    usecols=["CD_SETOR","v0001"], dtype={"CD_SETOR": str}, low_memory=False,
)
agg["v0001"] = pd.to_numeric(agg["v0001"], errors="coerce").fillna(0)

GSP_MUNIS = set(sec22[sec22["NM_CONCURB"] == "São Paulo/SP"]["CD_MUN"].unique())
BX_MUNIS  = {"3506359","3513504","3518701","3522109","3531100","3537602","3541000","3548500","3551009"}
ALL_MUNIS = GSP_MUNIS | BX_MUNIS

sec = sec22[sec22["CD_MUN"].isin(ALL_MUNIS)].copy()
sec = sec.merge(agg, on="CD_SETOR", how="left")
sec_res = sec[
    sec["CD_TIPO"].astype(str).isin(["0","1"]) &
    (sec["v0001"] >= 100)
].copy()

# ---- 2) Build hybrid geo unit ----
sec_res["geo_unit"] = sec_res.apply(
    lambda r: f"dist_{r['CD_DIST']}" if str(r["CD_MUN"]) == CAPITAL
              else (f"bairro_{r['CD_MUN']}_{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"dist_{r['CD_DIST']}"),
    axis=1
)
sec_res["geo_label"] = sec_res.apply(
    lambda r: f"SP/{r['NM_DIST']}" if str(r["CD_MUN"]) == CAPITAL
              else (f"{r['NM_MUN']}/{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"{r['NM_MUN']}/{r['NM_DIST']}"),
    axis=1
)
sec2unit  = sec_res.set_index("CD_SETOR")["geo_unit"].to_dict()
sec2label = sec_res.set_index("CD_SETOR")["geo_label"].to_dict()
unit_pop  = sec_res.groupby("geo_unit")["v0001"].sum().rename("pop")
unit_label = sec_res.groupby("geo_unit")["geo_label"].first()

print(f"  Geo units: {len(unit_pop):,} | Sectors assigned: {len(sec2unit):,}/{len(sec_res):,}")
print(f"  Unit pop: p10={unit_pop.quantile(0.10):,.0f} "
      f"p25={unit_pop.quantile(0.25):,.0f} median={unit_pop.median():,.0f} "
      f"p75={unit_pop.quantile(0.75):,.0f} p90={unit_pop.quantile(0.90):,.0f}")

# ---- 3) Cases with year ----
print("\nLoading cases with year...")
gsp_co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False, dtype={"sinan_clean": str})
gsp_co["key"]       = gsp_co["sinan_clean"].str.zfill(7)
gsp_co["CD_SETOR"]  = gsp_co["setor_cnefe"].apply(norm_setor)

bx_co = pd.read_csv("/tmp/cohort_baixada_with_cnefe_v2.csv", low_memory=False, dtype={"sinan_clean": str})
bx_co["match_tier"] = bx_co["cnefe_match"].astype(str).str.extract(r"^(T\d)")
bx_co = bx_co[bx_co["match_tier"].isin(["T1","T2","T3"])]
bx_co["key"]       = bx_co["sinan_clean"].str.zfill(7)
bx_co["CD_SETOR"]  = bx_co["setor_cnefe"].apply(norm_setor)

spatial_yr = pd.read_csv(
    f"{SPATIAL}/cohort_with_spatial.csv",
    usecols=["sinan_clean","notification_date"], dtype={"sinan_clean": str}, low_memory=False
)
spatial_yr["key"]  = spatial_yr["sinan_clean"].str.strip()
spatial_yr["year"] = pd.to_datetime(spatial_yr["notification_date"], errors="coerce").dt.year
spatial_yr = (spatial_yr[spatial_yr["year"].between(2020,2024)]
              .drop_duplicates("key")[["key","year"]])

all_co = pd.concat([gsp_co[["key","CD_SETOR"]], bx_co[["key","CD_SETOR"]]], ignore_index=True)
all_co = all_co.merge(spatial_yr, on="key", how="left")
all_co["year"] = all_co["year"].fillna(2022).astype(int)
all_co = all_co.dropna(subset=["CD_SETOR"])
all_co["geo_unit"] = all_co["CD_SETOR"].map(sec2unit)
all_co = all_co.dropna(subset=["geo_unit"])

n_total_cases = len(all_co)
print(f"  Cases mapped to geo units: {len(all_co):,}")

# ---- 4) Unit-level aggregates ----
cases_total = all_co.groupby("geo_unit").size().rename("n_total").reset_index()
cases_yr_df = all_co.groupby(["geo_unit","year"]).size().rename("n").reset_index()

pop_df  = unit_pop.reset_index(); pop_df.columns = ["geo_unit","pop"]
pooled  = pop_df.merge(cases_total, on="geo_unit", how="left")
pooled["n_total"] = pooled["n_total"].fillna(0)
pooled["rate_pooled"] = pooled["n_total"] / (pooled["pop"] * 5) * 1e5
pooled = pooled.sort_values("rate_pooled", ascending=False).reset_index(drop=True)
pooled["cum_pop"]    = pooled["pop"].cumsum()
pooled["cum_cases"]  = pooled["n_total"].cumsum()
total_pop_u = pooled["pop"].sum()

# ---- 5) Year-specific rates ----
yr_data = {}
for yr in YEARS:
    yc = cases_yr_df[cases_yr_df["year"]==yr][["geo_unit","n"]].copy()
    df = pop_df.merge(yc, on="geo_unit", how="left")
    df["n"]    = df["n"].fillna(0)
    df["rate"] = df["n"] / df["pop"] * 1e5
    yr_data[yr] = df.set_index("geo_unit")

# ---- 6) Window-level metrics ----
print("\n" + "="*100)
print("BAIRRO-LEVEL METRICS BY WINDOW SIZE")
print("="*100)

rows = []
for w in WINDOWS:
    # Concentration
    mask = pooled["cum_pop"] <= total_pop_u * w
    if mask.sum() == 0:
        mask.iloc[0] = True
    n_units    = int(mask.sum())
    cases_pct  = pooled[mask]["n_total"].sum() / n_total_cases * 100
    conc_ratio = cases_pct / (w * 100)
    pop_window = pooled[mask]["pop"].sum()

    # Cases per unit in window
    hot_units  = pooled[mask]
    cases_per_unit_yr = hot_units["n_total"].values / 5  # annual average
    med_cases_yr = np.median(cases_per_unit_yr)
    p25_cases_yr = np.percentile(cases_per_unit_yr, 25)
    p75_cases_yr = np.percentile(cases_per_unit_yr, 75)

    # Pop distribution in window
    med_pop   = hot_units["pop"].median()
    p25_pop   = hot_units["pop"].quantile(0.25)
    p75_pop   = hot_units["pop"].quantile(0.75)
    pct_lt1k  = (hot_units["pop"] < 1000).mean() * 100
    pct_5k    = (hot_units["pop"] >= 5000).mean() * 100
    pct_10k   = (hot_units["pop"] >= 10000).mean() * 100

    # Rate distribution in window
    med_rate  = hot_units["rate_pooled"].median()

    # Stability (Jaccard year-over-year)
    jaccards = []
    for i, yr_a in enumerate(YEARS[:-1]):
        yr_b = YEARS[i+1]
        df_a  = yr_data[yr_a]; tot_a = df_a["pop"].sum()
        df_b  = yr_data[yr_b]; tot_b = df_b["pop"].sum()
        inc_a = df_a[df_a["n"]>0].sort_values("rate", ascending=False)
        inc_a = inc_a.copy(); inc_a["cum"] = inc_a["pop"].cumsum()
        hot_a = set(inc_a[inc_a["cum"] <= tot_a*w].index)
        inc_b = df_b[df_b["n"]>0].sort_values("rate", ascending=False)
        inc_b = inc_b.copy(); inc_b["cum"] = inc_b["pop"].cumsum()
        hot_b = set(inc_b[inc_b["cum"] <= tot_b*w].index)
        if hot_a | hot_b:
            jaccards.append(len(hot_a & hot_b) / len(hot_a | hot_b))

    mean_j = np.mean(jaccards) if jaccards else 0

    rows.append({
        "window_pct": w*100,
        "n_units": n_units,
        "pop_window": int(pop_window),
        "cases_pct": round(cases_pct, 1),
        "conc_ratio": round(conc_ratio, 2),
        "med_rate_pooled": round(med_rate, 0),
        "med_pop": round(med_pop, 0),
        "p25_pop": round(p25_pop, 0),
        "p75_pop": round(p75_pop, 0),
        "pct_lt1k_pop": round(pct_lt1k, 1),
        "pct_5k_pop": round(pct_5k, 1),
        "pct_10k_pop": round(pct_10k, 1),
        "med_cases_yr": round(med_cases_yr, 1),
        "p25_cases_yr": round(p25_cases_yr, 1),
        "p75_cases_yr": round(p75_cases_yr, 1),
        "mean_jaccard": round(mean_j, 3),
        "jaccards": [round(j,3) for j in jaccards],
    })

df_r = pd.DataFrame(rows)

print(f"\n{'Win':>4} | {'N units':>7} | {'%Cases':>7} | {'C.Ratio':>7} | "
      f"{'Jaccard':>8} | {'Med rate':>9} | {'Med pop':>8} | {'%<1k':>5} | {'%≥5k':>5} | "
      f"{'Med cases/yr':>13} | {'Cases/yr IQR':>14}")
print("-"*120)
for _, r in df_r.iterrows():
    marker = " ◄" if r["window_pct"]==5 else ""
    print(f"{r['window_pct']:>4.0f}% | {r['n_units']:>7,} | {r['cases_pct']:>6.1f}% | "
          f"{r['conc_ratio']:>6.2f}x | {r['mean_jaccard']:>8.3f} | "
          f"{r['med_rate_pooled']:>9.0f}/100k | {r['med_pop']:>8,.0f} | "
          f"{r['pct_lt1k_pop']:>4.0f}% | {r['pct_5k_pop']:>4.0f}% | "
          f"{r['med_cases_yr']:>12.1f} | "
          f"{r['p25_cases_yr']:.1f}–{r['p75_cases_yr']:.1f}{marker}")

# ---- 7) Top units at 5% window ----
print("\n" + "="*80)
print("TOP HOTSPOT UNITS AT 5% WINDOW")
print("="*80)
w5 = 0.05
mask5 = pooled["cum_pop"] <= total_pop_u * w5
hot5 = pooled[mask5].copy()
hot5["label"] = hot5["geo_unit"].map(unit_label.to_dict())
hot5["cases_yr_avg"] = hot5["n_total"] / 5

# Add year-specific counts for variability
for yr in YEARS:
    yc = cases_yr_df[cases_yr_df["year"]==yr].set_index("geo_unit")["n"]
    hot5[f"n_{yr}"] = hot5["geo_unit"].map(yc).fillna(0).astype(int)

hot5_show = hot5[["label","pop","n_total","cases_yr_avg","rate_pooled",
                   "n_2020","n_2021","n_2022","n_2023","n_2024"]].head(30)
print(f"\n{'Unit':<40} {'Pop':>8} {'Tot':>5} {'Yr avg':>7} {'Rate':>7} "
      f"{'2020':>5} {'2021':>5} {'2022':>5} {'2023':>5} {'2024':>5}")
print("-"*95)
for _, r in hot5_show.iterrows():
    lbl = str(r["label"])[:40]
    print(f"{lbl:<40} {r['pop']:>8,.0f} {r['n_total']:>5.0f} {r['cases_yr_avg']:>7.1f} "
          f"{r['rate_pooled']:>7.0f} "
          f"{r['n_2020']:>5} {r['n_2021']:>5} {r['n_2022']:>5} {r['n_2023']:>5} {r['n_2024']:>5}")

# ---- 8) Jaccard detail at 5% ----
print("\n" + "="*60)
print("YEAR-TO-YEAR JACCARD DETAIL (5% window, bairro level)")
print("="*60)
r5 = df_r[df_r["window_pct"]==5.0].iloc[0]
pairs = ["2020→21","2021→22","2022→23","2023→24"]
for pair, j in zip(pairs, r5["jaccards"]):
    bar = "█" * int(j * 40)
    print(f"  {pair}: {j:.3f}  {bar}")
print(f"  Mean Jaccard: {r5['mean_jaccard']:.3f}")

# ---- 9) Plot ----
print("\nGenerating bairro sensitivity plot...")
fig, axes = plt.subplots(2, 3, figsize=(18, 11))
fig.suptitle(
    "Bairro-level Hotspot Analysis — GSP + Baixada Santista (2020–2024)\n"
    "Unit: NM_DIST for SP capital · NM_BAIRRO for other municipalities",
    fontsize=14, fontweight="bold", y=0.99
)

wins = df_r["window_pct"].tolist()
xlabels = [f"{w:.0f}%" for w in wins]
hl = "#c0392b"  # highlight color (5% window)
bar_c = [hl if w==5 else "#2980b9" for w in wins]

# A) Cases captured
ax = axes[0,0]
bars = ax.bar(xlabels, df_r["cases_pct"], color=bar_c, edgecolor="white")
for b, v in zip(bars, df_r["cases_pct"]):
    ax.text(b.get_x()+b.get_width()/2, v+0.5, f"{v:.0f}%", ha="center", fontsize=10, fontweight="bold")
ax.set_ylabel("TB cases captured (%)"); ax.set_title("A) Cases captured per window", fontweight="bold")
ax.set_ylim(0, 75); ax.grid(axis="y", alpha=0.3)

# B) Concentration ratio
ax = axes[0,1]
ax.plot(xlabels, df_r["conc_ratio"], "o-", color="#27ae60", lw=2.5, ms=9)
ax.axhline(3, color="grey", ls="--", lw=1, label="3× threshold")
ax.scatter([xlabels[2]], [df_r.iloc[2]["conc_ratio"]], color=hl, s=150, zorder=5)
for x, v in zip(xlabels, df_r["conc_ratio"]):
    ax.annotate(f"{v:.1f}×", (x,v), textcoords="offset points", xytext=(0,8), ha="center", fontsize=10)
ax.set_ylabel("Concentration ratio"); ax.set_title("B) Concentration ratio", fontweight="bold")
ax.legend(fontsize=9); ax.grid(alpha=0.3)

# C) Jaccard stability
ax = axes[0,2]
ax.plot(xlabels, df_r["mean_jaccard"], "s-", color="#8e44ad", lw=2.5, ms=9)
ax.axhline(0.5, color="grey", ls="--", lw=1, label="0.5 (moderate)")
ax.axhline(0.3, color="grey", ls=":", lw=1, label="0.3 (minimum)")
ax.scatter([xlabels[2]], [df_r.iloc[2]["mean_jaccard"]], color=hl, s=150, zorder=5)
for x, v in zip(xlabels, df_r["mean_jaccard"]):
    ax.annotate(f"{v:.2f}", (x,v), textcoords="offset points", xytext=(0,8), ha="center", fontsize=10)
ax.set_ylabel("Mean Jaccard (year-over-year)"); ax.set_title("C) Year-to-year stability", fontweight="bold")
ax.set_ylim(0, 0.8); ax.legend(fontsize=9); ax.grid(alpha=0.3)

# D) Unit pop distribution in window
ax = axes[1,0]
ax.bar(xlabels, df_r["med_pop"], color=bar_c, edgecolor="white", label="Median pop")
ax.errorbar(xlabels, df_r["med_pop"],
            yerr=[df_r["med_pop"]-df_r["p25_pop"], df_r["p75_pop"]-df_r["med_pop"]],
            fmt="none", color="black", capsize=5, lw=1.5)
ax.axhline(5000, color="#e67e22", ls="--", lw=1.5, label="5k minimum")
ax.axhline(10000, color="#c0392b", ls="--", lw=1.5, label="10k preferred")
ax.set_ylabel("Unit population (IQR bars)"); ax.set_title("D) Unit population in hotspot window", fontweight="bold")
ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3)
for b, v in zip(ax.patches, df_r["med_pop"]):
    ax.text(b.get_x()+b.get_width()/2, v+200, f"{v/1000:.0f}k", ha="center", fontsize=9)

# E) Median cases/year per unit
ax = axes[1,1]
ax.bar(xlabels, df_r["med_cases_yr"], color=bar_c, edgecolor="white")
ax.errorbar(xlabels, df_r["med_cases_yr"],
            yerr=[df_r["med_cases_yr"]-df_r["p25_cases_yr"],
                  df_r["p75_cases_yr"]-df_r["med_cases_yr"]],
            fmt="none", color="black", capsize=5, lw=1.5)
ax.axhline(5, color="#e67e22", ls="--", lw=1.5, label="5 cases/yr (min ACF)")
ax.axhline(10, color="#c0392b", ls="--", lw=1.5, label="10 cases/yr (preferred)")
for b, v in zip(ax.patches, df_r["med_cases_yr"]):
    ax.text(b.get_x()+b.get_width()/2, v+0.1, f"{v:.1f}", ha="center", fontsize=9)
ax.set_ylabel("Median cases/year per unit (IQR bars)")
ax.set_title("E) Annual TB cases per hotspot unit", fontweight="bold")
ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3)

# F) % units <1k pop vs ≥5k pop
ax = axes[1,2]
x = np.arange(len(wins))
w_bar = 0.35
ax.bar(x - w_bar/2, df_r["pct_lt1k_pop"], w_bar, color="#e74c3c", alpha=0.8, label="< 1k pop (too small)")
ax.bar(x + w_bar/2, df_r["pct_5k_pop"],   w_bar, color="#27ae60", alpha=0.8, label="≥ 5k pop (viable)")
ax.set_xticks(x); ax.set_xticklabels(xlabels)
ax.set_ylabel("% of hotspot units"); ax.set_title("F) Unit size viability", fontweight="bold")
ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3)

plt.tight_layout()
plt.savefig("/tmp/bairro_sensitivity_plot.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()

df_r.drop(columns=["jaccards"]).to_csv("/tmp/bairro_sensitivity.csv", index=False)
print("Saved: /tmp/bairro_sensitivity_plot.png")
print("Saved: /tmp/bairro_sensitivity.csv")
print("\nDone.")
