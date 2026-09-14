"""TB outcome comparison: hotspot bairros vs. FCU vs. non-selected.

Groups (non-mutually exclusive):
  1. Hotspot bairros     — cases in the 191 top-rate bairros (20% pop window)
  2. FCU (favela/slum)   — cases geocoded to a sector with is_fcu=1 (any bairro)
  3. Non-selected        — cases NOT in hotspot bairros AND NOT in FCU

Outcomes: treatment success, abandonment, TB death, non-TB death,
          hospitalization, HIV, pulmonary form, lab-confirmed, discovery route.

Also reports mutually exclusive breakdown: FCU | hotspot non-FCU | non-selected
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import zipfile, io

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL = "3550308"

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s

# ============================================================
# 1) Shapefile + FCU flag
# ============================================================
print("Loading shapefile...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]   = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)

GSP_MUNIS = set(sec22[sec22["NM_CONCURB"]=="São Paulo/SP"]["CD_MUN"].unique())
BX_MUNIS  = {"3506359","3513504","3518701","3522109","3531100","3537602","3541000","3548500","3551009"}
ALL_MUNIS = GSP_MUNIS | BX_MUNIS

agg = pd.read_csv(
    f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
    sep=";", encoding="latin-1", decimal=",",
    usecols=["CD_SETOR","v0001"], dtype={"CD_SETOR": str}, low_memory=False,
)
agg["v0001"] = pd.to_numeric(agg["v0001"], errors="coerce").fillna(0)

sec = sec22[sec22["CD_MUN"].isin(ALL_MUNIS)].copy()
sec = sec.merge(agg, on="CD_SETOR", how="left")
sec_res = sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["v0001"]>=100)].copy()
sec_res["is_fcu"] = sec_res["NM_FCU"].notna().astype(int)

sec_res["geo_unit"] = sec_res.apply(
    lambda r: f"dist_{r['CD_DIST']}" if str(r["CD_MUN"])==CAPITAL
              else (f"bairro_{r['CD_MUN']}_{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"dist_{r['CD_DIST']}"), axis=1)
sec2unit = sec_res.set_index("CD_SETOR")["geo_unit"].to_dict()
sec2fcu  = sec_res.set_index("CD_SETOR")["is_fcu"].to_dict()

# ============================================================
# 2) Identify hotspot bairros (same logic as script 35/36)
# ============================================================
print("Identifying hotspot bairros...")
# Load CNEFE cohort for case counts
gsp_co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False, dtype={"sinan_clean": str})
gsp_co["key"]      = gsp_co["sinan_clean"].str.zfill(7)
gsp_co["CD_SETOR"] = gsp_co["setor_cnefe"].apply(norm_setor)
bx_co  = pd.read_csv("/tmp/cohort_baixada_with_cnefe_v2.csv", low_memory=False, dtype={"sinan_clean": str})
bx_co["match_tier"] = bx_co["cnefe_match"].astype(str).str.extract(r"^(T\d)")
bx_co  = bx_co[bx_co["match_tier"].isin(["T1","T2","T3"])]
bx_co["key"]       = bx_co["sinan_clean"].str.zfill(7)
bx_co["CD_SETOR"]  = bx_co["setor_cnefe"].apply(norm_setor)

all_co = pd.concat([gsp_co[["key","CD_SETOR"]], bx_co[["key","CD_SETOR"]]], ignore_index=True)
all_co = all_co.dropna(subset=["CD_SETOR"])
all_co["geo_unit"] = all_co["CD_SETOR"].map(sec2unit)
all_co = all_co.dropna(subset=["geo_unit"])

unit_pop   = sec_res.groupby("geo_unit")["v0001"].sum()
cases_tot  = all_co.groupby("geo_unit").size().rename("n_cases")
pooled     = unit_pop.rename("pop").reset_index().merge(cases_tot.reset_index(), on="geo_unit", how="left")
pooled["n_cases"]   = pooled["n_cases"].fillna(0)
pooled["rate"]      = pooled["n_cases"] / (pooled["pop"]*5) * 1e5
pooled              = pooled.sort_values("rate", ascending=False)
pooled["cum_pop"]   = pooled["pop"].cumsum()
total_pop_u         = pooled["pop"].sum()
hotspot_units       = set(pooled[pooled["cum_pop"] <= total_pop_u*0.20]["geo_unit"])
print(f"  Hotspot bairros: {len(hotspot_units):,}")

# ============================================================
# 3) Full cohort with outcomes (2020–2024, NOVO+RECIDIVA)
# ============================================================
print("Loading cohort outcomes...")
OUTCOME_COLS = ["sinan_clean","sinan_padded","notification_date","case_type","case_outcome",
                "hiv","aids","hosp_admission","cause_of_death_code","clinical_classif",
                "lab_confirmed","disease_discovery"]
cohort = pd.read_csv(f"{SPATIAL}/cohort_with_spatial.csv",
                     usecols=OUTCOME_COLS, dtype={"sinan_clean":str}, low_memory=False)
cohort["year"]    = pd.to_datetime(cohort["notification_date"], errors="coerce").dt.year
cohort = cohort[cohort["year"].between(2020,2024) &
                cohort["case_type"].isin(["Novo","Recidiva"])].copy()
cohort["key"]     = cohort["sinan_clean"].str.strip()
print(f"  Full cohort NOVO+RECIDIVA 2020–2024: {len(cohort):,}")

# ============================================================
# 4) Add geo flags to cohort
# ============================================================
# Build key→sector map from CNEFE files
key2sector = dict(zip(
    pd.concat([gsp_co[["key","CD_SETOR"]], bx_co[["key","CD_SETOR"]]])
      .dropna(subset=["CD_SETOR"])["key"],
    pd.concat([gsp_co[["key","CD_SETOR"]], bx_co[["key","CD_SETOR"]]])
      .dropna(subset=["CD_SETOR"])["CD_SETOR"]
))
cohort["CD_SETOR"] = cohort["key"].map(key2sector)
cohort["geo_unit"] = cohort["CD_SETOR"].map(sec2unit)
cohort["is_fcu"]   = cohort["CD_SETOR"].map(sec2fcu).fillna(0).astype(int)
cohort["is_hotspot_bairro"] = cohort["geo_unit"].map(
    lambda u: 1 if u in hotspot_units else 0).fillna(0).astype(int)
cohort["geocoded"] = cohort["CD_SETOR"].notna().astype(int)

print(f"  Geocoded cases: {cohort['geocoded'].sum():,} / {len(cohort):,} "
      f"({cohort['geocoded'].mean()*100:.1f}%)")
print(f"  In hotspot bairro:  {cohort['is_hotspot_bairro'].sum():,}")
print(f"  In FCU:             {cohort['is_fcu'].sum():,}")

# ============================================================
# 5) Outcome variables
# ============================================================
cohort["success"]    = cohort["case_outcome"].isin(["Cura"]).astype(float)
cohort["abandon"]    = cohort["case_outcome"].isin(["Abandono","Abandono Primario"]).astype(float)
cohort["death_tb"]   = cohort["case_outcome"].isin(["Obito TB"]).astype(float)
cohort["death_ntb"]  = cohort["case_outcome"].isin(["Obito NTB"]).astype(float)
cohort["death_any"]  = (cohort["death_tb"] + cohort["death_ntb"]).clip(upper=1)
cohort["failure"]    = cohort["case_outcome"].isin(
    ["Falencia","Mud Esquema Intoler/Toxicidade"]).astype(float)
cohort["hosp"]       = (cohort["hosp_admission"]=="S").astype(float)
cohort["hiv_pos"]    = (cohort["hiv"]=="Pos").astype(float)
cohort["pulm"]       = cohort["clinical_classif"].isin(["Pul","P+E"]).astype(float)
cohort["lab_conf"]   = (cohort["lab_confirmed"]==1).astype(float)
cohort["acf_discovery"] = cohort["disease_discovery"].isin(
    ["Busca Ativa em Instituicao","Busca Ativa na Comunidade"]).astype(float)
cohort["er_discovery"]  = (cohort["disease_discovery"]=="Urgencia / Emergencia").astype(float)

# Known outcome (exclude NaN case_outcome from % calcs)
cohort["known_outcome"] = cohort["case_outcome"].notna().astype(float)

# ============================================================
# 6) Compute group stats
# ============================================================
def group_stats(df, label):
    n_total = len(df)
    n_known = df["known_outcome"].sum()
    n_geocoded = df["geocoded"].sum()

    def pct(col, denom=None):
        d = df[col]
        den = len(df) if denom is None else df[denom].sum()
        if den == 0: return np.nan, 0, 0
        val = d.sum() / den * 100
        # Wilson 95% CI
        p = d.sum() / den
        z = 1.96
        denom_n = int(den)
        lo = (p + z**2/(2*denom_n) - z*np.sqrt(p*(1-p)/denom_n + z**2/(4*denom_n**2))) / (1 + z**2/denom_n)
        hi = (p + z**2/(2*denom_n) + z*np.sqrt(p*(1-p)/denom_n + z**2/(4*denom_n**2))) / (1 + z**2/denom_n)
        return round(val,1), round(lo*100,1), round(hi*100,1)

    r = {"group": label, "n": n_total, "n_known_outcome": int(n_known),
         "pct_known_outcome": round(n_known/n_total*100,1) if n_total>0 else 0}

    # Outcomes (denominator = known outcome)
    for col in ["success","abandon","death_tb","death_ntb","death_any","failure"]:
        v, lo, hi = pct(col, "known_outcome")
        r[f"{col}_pct"] = v
        r[f"{col}_ci"]  = f"{lo}–{hi}"
        r[f"{col}_n"]   = int(df[df["known_outcome"]==1][col].sum())

    # Other vars (denominator = total)
    for col in ["hosp","hiv_pos","pulm","lab_conf","acf_discovery","er_discovery"]:
        v, lo, hi = pct(col)
        r[f"{col}_pct"] = v
        r[f"{col}_ci"]  = f"{lo}–{hi}"

    return r

# Define groups
groups = {
    "1. Hotspot bairros":    cohort[cohort["is_hotspot_bairro"]==1],
    "2. FCU (all bairros)":  cohort[cohort["is_fcu"]==1],
    "3. Non-selected":       cohort[(cohort["is_hotspot_bairro"]==0) & (cohort["is_fcu"]==0)],
    "4. All geocoded":       cohort[cohort["geocoded"]==1],
    "5. All (incl. non-geocoded)": cohort,
}

stats = [group_stats(df, label) for label, df in groups.items()]
df_stats = pd.DataFrame(stats)

# ============================================================
# 7) Print comparison table
# ============================================================
print("\n" + "="*110)
print("TB OUTCOMES BY GROUP — GSP + Baixada Santista, NOVO+RECIDIVA 2020–2024")
print("="*110)

OUTCOME_LABELS = [
    ("n",              "N cases",                    None),
    ("pct_known_outcome", "% with known outcome",   None),
    ("───────",        "── Treatment outcomes (denominator = known outcome) ──", None),
    ("success_pct",    "Treatment success (cure) %", "success_ci"),
    ("abandon_pct",    "Loss to follow-up (abandon) %", "abandon_ci"),
    ("failure_pct",    "Treatment failure %",         "failure_ci"),
    ("death_tb_pct",   "Death from TB %",             "death_tb_ci"),
    ("death_ntb_pct",  "Death non-TB %",              "death_ntb_ci"),
    ("death_any_pct",  "Death any cause %",           "death_any_ci"),
    ("───────",        "── Disease characteristics ──", None),
    ("hosp_pct",       "Hospitalized %",              "hosp_ci"),
    ("hiv_pos_pct",    "HIV-positive %",              "hiv_pos_ci"),
    ("pulm_pct",       "Pulmonary TB %",              "pulm_ci"),
    ("lab_conf_pct",   "Lab-confirmed %",             "lab_conf_ci"),
    ("───────",        "── Discovery route ──",       None),
    ("acf_discovery_pct","Found via active case finding %","acf_discovery_ci"),
    ("er_discovery_pct", "Found via ER/urgency %",    "er_discovery_ci"),
]

grp_names = [s["group"] for s in stats]
header = f"{'Metric':<45}" + "".join(f"{g[:22]:>24}" for g in grp_names)
print(header)
print("-"*110)

for key, label, ci_key in OUTCOME_LABELS:
    if key.startswith("───"):
        print(f"\n{label}")
        continue
    row = f"  {label:<43}"
    for s in stats:
        val = s.get(key, "")
        if val is None or val == "":
            row += f"{'—':>24}"
        elif isinstance(val, float) and ci_key and s.get(ci_key):
            row += f"{val:>5.1f}% ({s[ci_key]}){' ':>5}"[:24].rjust(24)
        elif isinstance(val, (int, float)):
            row += f"{val:>24,}"
        else:
            row += f"{str(val):>24}"
    print(row)

# Mutually exclusive breakdown
print("\n" + "="*90)
print("MUTUALLY EXCLUSIVE BREAKDOWN (priority: FCU > hotspot non-FCU > non-selected)")
print("="*90)
cohort["group_excl"] = "Non-selected"
cohort.loc[(cohort["is_hotspot_bairro"]==1) & (cohort["is_fcu"]==0), "group_excl"] = "Hotspot non-FCU"
cohort.loc[cohort["is_fcu"]==1, "group_excl"] = "FCU"
cohort.loc[cohort["geocoded"]==0, "group_excl"] = "Non-geocoded"

excl_groups = {
    "FCU":              cohort[cohort["group_excl"]=="FCU"],
    "Hotspot non-FCU":  cohort[cohort["group_excl"]=="Hotspot non-FCU"],
    "Non-selected":     cohort[cohort["group_excl"]=="Non-selected"],
    "Non-geocoded":     cohort[cohort["group_excl"]=="Non-geocoded"],
}
excl_stats = [group_stats(df, label) for label, df in excl_groups.items()]

print(f"\n{'Group':<20} {'N':>7} {'Success%':>10} {'Abandon%':>10} "
      f"{'Death TB%':>10} {'Death any%':>11} {'Hosp%':>7} {'HIV+%':>7}")
print("-"*90)
for s in excl_stats:
    print(f"{s['group']:<20} {s['n']:>7,} {(s.get('success_pct') or 0):>9.1f}% "
          f"{(s.get('abandon_pct') or 0):>9.1f}% "
          f"{(s.get('death_tb_pct') or 0):>9.1f}% "
          f"{(s.get('death_any_pct') or 0):>10.1f}% "
          f"{(s.get('hosp_pct') or 0):>6.1f}% "
          f"{(s.get('hiv_pos_pct') or 0):>6.1f}%")

# Save
df_stats.to_csv("/tmp/tb_outcomes_by_group.csv", index=False)

# ============================================================
# 8) Plot
# ============================================================
print("\nGenerating outcomes plot...")
PLOT_GROUPS = ["1. Hotspot bairros","2. FCU (all bairros)","3. Non-selected"]
COLORS = {"1. Hotspot bairros":"#c0392b", "2. FCU (all bairros)":"#2980b9",
          "3. Non-selected":"#7f8c8d"}
s_dict = {s["group"]: s for s in stats}

fig, axes = plt.subplots(2, 4, figsize=(22, 12))
fig.suptitle("TB Outcomes by Geographic Group — GSP + Baixada Santista (NOVO+RECIDIVA 2020–2024)",
             fontsize=15, fontweight="bold", y=1.01)

plots = [
    ("Treatment success %",    "success_pct",      "success_ci"),
    ("Loss to follow-up %",    "abandon_pct",       "abandon_ci"),
    ("Death from TB %",        "death_tb_pct",      "death_tb_ci"),
    ("Death any cause %",      "death_any_pct",     "death_any_ci"),
    ("Hospitalized %",         "hosp_pct",          "hosp_ci"),
    ("HIV-positive %",         "hiv_pos_pct",       "hiv_pos_ci"),
    ("Found via ACF %",        "acf_discovery_pct", "acf_discovery_ci"),
    ("Found via ER %",         "er_discovery_pct",  "er_discovery_ci"),
]

for idx, (title, val_key, ci_key) in enumerate(plots):
    ax = axes[idx // 4][idx % 4]
    vals, errs_lo, errs_hi, colors = [], [], [], []
    for g in PLOT_GROUPS:
        s = s_dict[g]
        v = s.get(val_key) or 0
        ci = s.get(ci_key, "0–0")
        try:
            lo_str, hi_str = ci.split("–")
            lo, hi = float(lo_str), float(hi_str)
        except:
            lo, hi = v, v
        vals.append(v)
        errs_lo.append(max(0, v - lo))
        errs_hi.append(max(0, hi - v))
        colors.append(COLORS[g])

    short_labels = ["Hotspot\nbairros", "FCU\n(all)", "Non-\nselected"]
    bars = ax.bar(short_labels, vals, color=colors, edgecolor="white", width=0.55)
    ax.errorbar(short_labels, vals,
                yerr=[errs_lo, errs_hi],
                fmt="none", color="black", capsize=5, lw=1.5, zorder=5)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x()+bar.get_width()/2, v + max(errs_hi)*0.15 + 0.3,
                f"{v:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_ylim(0, max(vals + errs_hi) * 1.35 + 1)
    ax.grid(axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

plt.tight_layout()
plt.savefig("/tmp/tb_outcomes_plot.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("Saved: /tmp/tb_outcomes_plot.png")
print("Saved: /tmp/tb_outcomes_by_group.csv")
print("\nDone.")
