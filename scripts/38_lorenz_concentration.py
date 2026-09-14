"""Lorenz concentration curve: % population vs % TB cases by bairro.

Bairros ranked highest → lowest TB rate.
X-axis: cumulative % of population (starting from highest-rate bairros)
Y-axis: cumulative % of TB cases
Diagonal = perfect equality (uniform rate everywhere)
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import zipfile, io

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL = "3550308"

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s

# ---- 1) Rebuild bairro unit table (same logic as scripts 35/36) ----
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
BX_MUNIS  = {"3506359","3513504","3518701","3522109","3531100","3537602","3541000","3548500","3551009"}
ALL_MUNIS = GSP_MUNIS | BX_MUNIS

sec = sec22[sec22["CD_MUN"].isin(ALL_MUNIS)].copy()
sec = sec.merge(agg, on="CD_SETOR", how="left")
sec_res = sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["v0001"]>=100)].copy()

sec_res["geo_unit"] = sec_res.apply(
    lambda r: f"dist_{r['CD_DIST']}" if str(r["CD_MUN"])==CAPITAL
              else (f"bairro_{r['CD_MUN']}_{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"dist_{r['CD_DIST']}"), axis=1)
sec_res["geo_label"] = sec_res.apply(
    lambda r: f"SP/{r['NM_DIST']}" if str(r["CD_MUN"])==CAPITAL
              else (f"{r['NM_MUN']}/{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"{r['NM_MUN']}/{r['NM_DIST']}"), axis=1)
sec_res["is_fcu"] = sec_res["NM_FCU"].notna().astype(int)

sec2unit = sec_res.set_index("CD_SETOR")["geo_unit"].to_dict()
unit_pop = sec_res.groupby("geo_unit")["v0001"].sum().rename("pop")
# FCU share per bairro
fcu_pop  = sec_res[sec_res["is_fcu"]==1].groupby("geo_unit")["v0001"].sum().rename("fcu_pop")

# ---- 2) Cases ----
gsp_co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False, dtype={"sinan_clean": str})
gsp_co["CD_SETOR"] = gsp_co["setor_cnefe"].apply(norm_setor)
bx_co  = pd.read_csv("/tmp/cohort_baixada_with_cnefe_v2.csv", low_memory=False, dtype={"sinan_clean": str})
bx_co["match_tier"] = bx_co["cnefe_match"].astype(str).str.extract(r"^(T\d)")
bx_co  = bx_co[bx_co["match_tier"].isin(["T1","T2","T3"])]
bx_co["CD_SETOR"] = bx_co["setor_cnefe"].apply(norm_setor)

all_co = pd.concat([gsp_co[["CD_SETOR"]], bx_co[["CD_SETOR"]]], ignore_index=True)
all_co = all_co.dropna(subset=["CD_SETOR"])
all_co["geo_unit"] = all_co["CD_SETOR"].map(sec2unit)
all_co = all_co.dropna(subset=["geo_unit"])

cases_tot = all_co.groupby("geo_unit").size().rename("n_cases")

# ---- 3) Bairro table ----
df = unit_pop.reset_index().merge(cases_tot.reset_index(), on="geo_unit", how="left")
df = df.merge(fcu_pop.reset_index(), on="geo_unit", how="left")
df["n_cases"] = df["n_cases"].fillna(0)
df["fcu_pop"] = df["fcu_pop"].fillna(0)
df["pct_fcu"] = df["fcu_pop"] / df["pop"]
df["rate"]    = df["n_cases"] / (df["pop"] * 5) * 1e5
df["geo_label"] = df["geo_unit"].map(sec_res.groupby("geo_unit")["geo_label"].first().to_dict())

total_pop   = df["pop"].sum()
total_cases = df["n_cases"].sum()
n_bairros   = len(df)

# ---- 4) Sort HIGH → LOW rate for concentration curve ----
df_sorted = df.sort_values("rate", ascending=False).copy()
df_sorted["cum_pop_pct"]   = df_sorted["pop"].cumsum()   / total_pop   * 100
df_sorted["cum_cases_pct"] = df_sorted["n_cases"].cumsum() / total_cases * 100

# Also build LOW → HIGH for classic Lorenz
df_lorenz = df.sort_values("rate", ascending=True).copy()
df_lorenz["cum_pop_pct"]   = df_lorenz["pop"].cumsum()   / total_pop   * 100
df_lorenz["cum_cases_pct"] = df_lorenz["n_cases"].cumsum() / total_cases * 100

# ---- 5) Gini coefficient ----
# Using trapezoidal rule on Lorenz curve (low→high)
x = np.concatenate([[0], df_lorenz["cum_pop_pct"].values / 100])
y = np.concatenate([[0], df_lorenz["cum_cases_pct"].values / 100])
area_under = np.trapz(y, x)
gini = 1 - 2 * area_under
print(f"Gini coefficient: {gini:.4f}")

# ---- 6) Key annotation points ----
THRESHOLDS = [0.05, 0.10, 0.20, 0.30, 0.50]
annotations = []
for thr in THRESHOLDS:
    mask = df_sorted["cum_pop_pct"] <= thr * 100
    if mask.sum() == 0:
        mask.iloc[0] = True
    n_u    = mask.sum()
    c_pct  = df_sorted[mask]["n_cases"].sum() / total_cases * 100
    p_pct  = df_sorted[mask]["pop"].sum() / total_pop * 100
    annotations.append((p_pct, c_pct, n_u, thr))
    print(f"  Top {thr*100:.0f}% pop → {n_u} bairros → {c_pct:.1f}% of cases")

# ---- 7) PLOT ----
fig, axes = plt.subplots(1, 2, figsize=(18, 8))
fig.suptitle(
    "TB case concentration by bairro — GSP + Baixada Santista (2020–2024)\n"
    f"{n_bairros} bairros · {total_cases:,.0f} geocoded cases · "
    f"NOVO+RECIDIVA · Gini = {gini:.3f}",
    fontsize=14, fontweight="bold", y=1.01
)

# ── Panel A: High → Low (operational view: "top X% of pop accounts for Y% of cases") ──
ax = axes[0]
x_hi = np.concatenate([[0], df_sorted["cum_pop_pct"].values])
y_hi = np.concatenate([[0], df_sorted["cum_cases_pct"].values])

ax.fill_between(x_hi, y_hi, x_hi, alpha=0.12, color="#c0392b", label="Excess concentration")
ax.plot(x_hi, y_hi, color="#c0392b", lw=2.5, label="Observed concentration")
ax.plot([0, 100], [0, 100], "--", color="#7f8c8d", lw=1.5, label="Line of equality\n(uniform TB rate)")

# Annotate threshold points
colors_thr = ["#1a0a00","#6e0a0a","#c0392b","#e67e22","#f1c40f"]
for i, (p_pct, c_pct, n_u, thr) in enumerate(annotations):
    ax.scatter(p_pct, c_pct, color=colors_thr[i], s=90, zorder=6)
    offset_x = 2 if p_pct < 75 else -2
    offset_y = 3 if i < 3 else -5
    ha = "left" if p_pct < 75 else "right"
    ax.annotate(
        f"Top {thr*100:.0f}% pop\n→ {c_pct:.0f}% cases\n({n_u} bairros)",
        (p_pct, c_pct),
        xytext=(p_pct + offset_x*3, c_pct + offset_y),
        fontsize=9, color=colors_thr[i], fontweight="bold", ha=ha,
        arrowprops=dict(arrowstyle="->", color=colors_thr[i], lw=1.2)
    )

ax.set_xlabel("Cumulative % of population\n(bairros ranked highest → lowest TB rate)", fontsize=12)
ax.set_ylabel("Cumulative % of TB cases", fontsize=12)
ax.set_title("A) Concentration curve (high→low rate)", fontsize=12, fontweight="bold")
ax.set_xlim(0, 102); ax.set_ylim(0, 102)
ax.legend(fontsize=10, loc="lower right")
ax.grid(alpha=0.3)
ax.annotate(f"Gini = {gini:.3f}", (50, 15), fontsize=14, color="#1a3d5c",
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.8, edgecolor="#1a3d5c"))

# ── Panel B: Classic Lorenz (low → high) ──
ax2 = axes[1]
x_lo = np.concatenate([[0], df_lorenz["cum_pop_pct"].values])
y_lo = np.concatenate([[0], df_lorenz["cum_cases_pct"].values])

ax2.plot(x_lo, y_lo, color="#2980b9", lw=2.5, label="Lorenz curve (TB cases)")
ax2.plot([0, 100], [0, 100], "--", color="#7f8c8d", lw=1.5, label="Line of equality")

# Shade Gini area (between diagonal and Lorenz)
ax2.fill_between(x_lo, x_lo, y_lo, alpha=0.18, color="#2980b9", label="Gini area")

# FCU reference: what % of cases are in FCU bairros?
fcu_bairros = df[df["pct_fcu"] > 0.5]  # majority FCU
fcu_cases_pct = fcu_bairros["n_cases"].sum() / total_cases * 100
fcu_pop_pct   = fcu_bairros["pop"].sum() / total_pop * 100
ax2.scatter(100 - fcu_pop_pct, 100 - fcu_cases_pct, color="#27ae60", s=100, zorder=6,
            label=f"FCU-majority bairros\n({fcu_pop_pct:.0f}% pop, {fcu_cases_pct:.0f}% cases)")

ax2.set_xlabel("Cumulative % of population\n(bairros ranked lowest → highest TB rate)", fontsize=12)
ax2.set_ylabel("Cumulative % of TB cases", fontsize=12)
ax2.set_title("B) Classic Lorenz curve (low→high rate)", fontsize=12, fontweight="bold")
ax2.set_xlim(0, 102); ax2.set_ylim(0, 102)
ax2.legend(fontsize=10, loc="upper left")
ax2.grid(alpha=0.3)
ax2.annotate(f"Gini = {gini:.3f}\n(0 = perfect equality\n1 = all cases in 1 bairro)",
             (55, 12), fontsize=11, color="#1a3d5c", fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.8, edgecolor="#1a3d5c"))

plt.tight_layout()
plt.savefig("/tmp/lorenz_concentration.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("Saved: /tmp/lorenz_concentration.png")
