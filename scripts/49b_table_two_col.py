"""Characteristics table — Selected hotspot areas vs Non-selected areas.
Compact 2-column format mirroring the GSP+Baixada table.

Outputs:
  /tmp/fig4b_table_two_col.png
"""

import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

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

# ── SECTORS + POPULATION ──────────────────────────────────────────────────────
import geopandas as gpd
print("Loading sectors...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]   = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)

pop_df = pd.read_csv(
    f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
    sep=";", encoding="latin-1", decimal=",",
    usecols=["CD_SETOR","v0001"], dtype={"CD_SETOR":str}, low_memory=False,
)
pop_df["pop"] = pd.to_numeric(pop_df["v0001"], errors="coerce").fillna(0)

sec = sec22.merge(pop_df[["CD_SETOR","pop"]], on="CD_SETOR", how="left")
sec["pop"] = sec["pop"].fillna(0)
sec_res = sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["pop"] >= 100)].copy()

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
sec_res = sec_res.copy()
sec_res[["bairro_id","bairro_label"]] = bkeys

fcu_pop = sec_res[sec_res["NM_FCU"].notna()].groupby("NM_FCU")["pop"].sum()
qualifying_fcus = set(fcu_pop[fcu_pop >= FCU_MIN].index)
TOTAL_POP = sec_res["pop"].sum()

def assign(row):
    nm = row["NM_FCU"]
    if pd.notna(nm) and nm in qualifying_fcus:
        return f"fcu__{nm}", nm, "FCU"
    return row["bairro_id"], row["bairro_label"], "bairro"

asgn = sec_res.apply(assign, axis=1, result_type="expand")
asgn.columns = ["unit_id","label","unit_type"]
# reset_index on BOTH sides to avoid outer-join NaN rows
sec_w = pd.concat([sec_res.reset_index(drop=True), asgn.reset_index(drop=True)], axis=1)

# ── GEOCODED CASES (sinan_clean → CD_SETOR) ───────────────────────────────────
print("Loading geocoded cohorts...")
def load_co(path):
    df = pd.read_csv(path, low_memory=False, dtype={"sinan_clean":str})
    df["tier"] = df["cnefe_match"].astype(str).str.extract(r"^(T\d)")
    df = df[df["tier"].isin(["T1","T2","T3"])]
    df["CD_SETOR"] = df["setor_cnefe"].apply(norm_setor)
    return df[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])

gsp_co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False, dtype={"sinan_clean":str})
gsp_co["CD_SETOR"] = gsp_co["setor_cnefe"].apply(norm_setor)
gsp_co = gsp_co[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])

cohort_geo = pd.concat([
    gsp_co,
    load_co("/tmp/cohort_baixada_with_cnefe_v2.csv"),
    load_co("/tmp/cohort_sp_outros_with_cnefe.csv"),
], ignore_index=True)

# Year filter: 2020-2024
cohort_yr = pd.read_csv(
    f"{SPATIAL}/cohort_with_spatial.csv",
    usecols=["sinan_clean","notification_date"],
    low_memory=False, dtype={"sinan_clean":str},
)
cohort_yr["year"] = pd.to_datetime(cohort_yr["notification_date"], errors="coerce").dt.year
yr_map = (cohort_yr.dropna(subset=["sinan_clean","year"])
          .drop_duplicates("sinan_clean").set_index("sinan_clean")["year"].to_dict())
cohort_geo["year"] = cohort_geo["sinan_clean"].map(yr_map)
cohort_geo = cohort_geo[cohort_geo["year"].between(2020, 2024)].copy()

# Assign unit_id to each case
setor_to_unit = sec_w.set_index("CD_SETOR")["unit_id"].to_dict()
cohort_geo["unit_id"] = cohort_geo["CD_SETOR"].map(setor_to_unit)

TOTAL_CASES = len(cohort_geo)
print(f"  Geocoded cases 2020-2024: {TOTAL_CASES:,}")

# ── UNIT-LEVEL AGGREGATION ─────────────────────────────────────────────────────
unit_df = sec_w.groupby("unit_id").agg(
    pop=("pop","sum"), label=("label","first"), unit_type=("unit_type","first"),
).reset_index()
unit_df = unit_df.merge(
    cohort_geo.groupby("unit_id").size().rename("n_cases").reset_index(),
    on="unit_id", how="left"
)
unit_df["n_cases"] = unit_df["n_cases"].fillna(0)
unit_df["rate"]    = unit_df["n_cases"] / (unit_df["pop"] * 5) * 1e5

# 20%-population selection
elig_df = unit_df[unit_df["n_cases"] >= MIN_CASES].copy()
elig_df = elig_df.sort_values("rate", ascending=False)
elig_df["cum_pop"] = elig_df["pop"].cumsum()
mask = elig_df["cum_pop"] <= TOTAL_POP * POP_WIN
if mask.sum() < len(elig_df): mask.iloc[mask.sum()] = True
sel_df      = elig_df[mask].copy()
selected_ids = set(sel_df["unit_id"])
print(f"  Selected units: {len(selected_ids):,}  |  All units: {len(unit_df):,}")

# ── CLINICAL VARIABLES ─────────────────────────────────────────────────────────
print("Loading clinical data...")
CLIN_COLS = [
    "sinan_clean","sex","age_tb","hiv","clinical_form_1","case_outcome",
    "disease_discovery","hosp_admission","address_type","drug_use",
    "alcoholism","diabetes","lives_in_favela","resistance",
]
clin = pd.read_csv(
    f"{SPATIAL}/cohort_with_spatial.csv",
    usecols=CLIN_COLS, low_memory=False, dtype={"sinan_clean":str},
)
# Keep unique sinan_clean (some may appear multiple times due to recurrence tracking)
clin = clin.drop_duplicates("sinan_clean")

# Merge into geocoded cohort
cohort = cohort_geo.merge(clin, on="sinan_clean", how="left")
print(f"  Clinical merge: {cohort['hiv'].notna().sum():,}/{len(cohort):,} cases matched")

# Label: selected vs non-selected
cohort["selected"] = cohort["unit_id"].isin(selected_ids)

# ── STATS FUNCTIONS ────────────────────────────────────────────────────────────
def pct(series, condition):
    """% of non-null rows meeting condition."""
    s = series.dropna()
    if len(s) == 0: return np.nan
    return (condition(s)).sum() / len(s) * 100

def pct_of(series, num_vals, denom_vals=None):
    """% with value in num_vals, denominator optionally restricted to denom_vals."""
    if denom_vals is not None:
        s = series[series.isin(num_vals + denom_vals)]
    else:
        s = series.dropna()
    if len(s) == 0: return np.nan
    return series.isin(num_vals).reindex(s.index).sum() / len(s) * 100

def unit_stats(uid_set, udf):
    sub = udf[udf["unit_id"].isin(uid_set)]
    pop   = sub["pop"].sum()
    cases = sub["n_cases"].sum()
    return {
        "n_units":  len(sub),
        "pop":      pop,
        "pct_pop":  pop / TOTAL_POP * 100,
        "cases":    cases,
        "pct_cases": cases / TOTAL_CASES * 100,
        "rate":     cases / (pop * 5) * 1e5 if pop > 0 else 0,
        "med_pop":  int(sub["pop"].median()) if len(sub) else 0,
    }

def case_stats(df):
    """Clinical characteristics for a subset of cases."""
    n = len(df)
    # Age
    age = pd.to_numeric(df["age_tb"], errors="coerce")
    # Sex
    male_pct = pct(df["sex"], lambda s: s == "M")
    # HIV positive among HIV-tested
    hiv_pos = pct_of(df["hiv"], num_vals=["Pos"], denom_vals=["Neg"])
    # Pulmonary TB
    pul_pct = pct_of(df["clinical_form_1"], ["Pul"])
    # Disease discovery groupings
    dd = df["disease_discovery"].dropna()
    dd_n = len(dd)
    outpt_pct  = (dd.isin(["Demanda Ambulatorial"])).sum() / dd_n * 100 if dd_n else np.nan
    emerg_pct  = (dd.isin(["Urgencia / Emergencia"])).sum() / dd_n * 100 if dd_n else np.nan
    hosp_dx_pct= (dd.isin(["Elucidacao Diagn. em Internacao"])).sum() / dd_n * 100 if dd_n else np.nan
    acf_inst_pct = (dd.isin(["Busca Ativa em Instituicao"])).sum() / dd_n * 100 if dd_n else np.nan
    acf_com_pct  = (dd.isin(["Busca Ativa na Comunidade"])).sum() / dd_n * 100 if dd_n else np.nan
    acf_total_pct = (dd.isin(["Busca Ativa em Instituicao","Busca Ativa na Comunidade"])).sum() / dd_n * 100 if dd_n else np.nan
    contact_pct  = (dd.isin(["Investigacao de Contatos"])).sum() / dd_n * 100 if dd_n else np.nan
    # Hospitalization
    hosp_pct = pct_of(df["hosp_admission"], ["S","Yes","1"], ["N","No","0"])
    # Address type
    addr = df["address_type"].dropna()
    addr_n = len(addr)
    detained_pct  = (addr == "DETENTO").sum() / addr_n * 100 if addr_n else np.nan
    homeless_pct  = (addr == "SEM RESIDENCIA FIXA").sum() / addr_n * 100 if addr_n else np.nan
    # Comorbidities (1 = yes; encoding may be S/N or 1/0)
    def comorb(col):
        s = df[col].dropna().astype(str).str.strip().str.upper()
        pos = s.isin(["1","S","SIM","YES","TRUE"])
        return pos.sum() / len(s) * 100 if len(s) > 0 else np.nan
    # Lives in favela
    fav = pd.to_numeric(df["lives_in_favela"], errors="coerce").dropna()
    fav_pct = (fav == 1).sum() / len(fav) * 100 if len(fav) > 0 else np.nan
    # Drug resistance (among those tested)
    res = df["resistance"].dropna()
    res_n = len(res)
    dr_pct = (res.isin(["TB R","TB MR"])).sum() / res_n * 100 if res_n else np.nan
    # Treatment outcomes (among those with outcome recorded, excl. in-treatment/transfer)
    oc = df["case_outcome"].dropna()
    oc_excl = oc[~oc.isin(["Transf Outro Estado/Pais","Mud Diag","S/inf"])]
    oc_n = len(oc_excl)
    cure_pct = (oc_excl == "Cura").sum() / oc_n * 100 if oc_n else np.nan
    ltfu_pct = (oc_excl.isin(["Abandono","Abandono Primario"])).sum() / oc_n * 100 if oc_n else np.nan
    tb_death_pct = (oc_excl == "Obito TB").sum() / oc_n * 100 if oc_n else np.nan

    return {
        "n_cases":         n,
        "male_pct":        male_pct,
        "median_age":      age.median(),
        "pul_pct":         pul_pct,
        "hiv_pos_pct":     hiv_pos,
        "dr_pct":          dr_pct,
        "drug_use_pct":    comorb("drug_use"),
        "alcohol_pct":     comorb("alcoholism"),
        "diabetes_pct":    comorb("diabetes"),
        "detained_pct":    detained_pct,
        "homeless_pct":    homeless_pct,
        "favela_pct":      fav_pct,
        "outpt_pct":       outpt_pct,
        "emerg_pct":       emerg_pct,
        "hosp_dx_pct":     hosp_dx_pct,
        "acf_inst_pct":    acf_inst_pct,
        "acf_com_pct":     acf_com_pct,
        "acf_total_pct":   acf_total_pct,
        "contact_pct":     contact_pct,
        "hosp_admission_pct": hosp_pct,
        "cure_pct":        cure_pct,
        "ltfu_pct":        ltfu_pct,
        "tb_death_pct":    tb_death_pct,
    }

# Split cases
cases_sel = cohort[cohort["unit_id"].isin(selected_ids)]
# Non-selected = everything NOT in a selected unit (includes unmapped cases)
cases_nosel = cohort[~cohort["unit_id"].isin(selected_ids)]

us_sel = unit_stats(selected_ids, unit_df)

# Non-selected aggregates as residuals so selected + non-selected = 100%
nosel_pop   = TOTAL_POP - us_sel["pop"]
nosel_cases = TOTAL_CASES - us_sel["cases"]
nosel_units_df = unit_df[~unit_df["unit_id"].isin(selected_ids)]
us_nosel = {
    "n_units":   len(nosel_units_df),
    "pop":       int(nosel_pop),
    "pct_pop":   nosel_pop / TOTAL_POP * 100,
    "cases":     int(nosel_cases),
    "pct_cases": nosel_cases / TOTAL_CASES * 100,
    "rate":      nosel_cases / (nosel_pop * 5) * 1e5,
    "med_pop":   int(nosel_units_df["pop"].median()) if len(nosel_units_df) else 0,
}

cs_sel   = case_stats(cases_sel)
cs_nosel = case_stats(cases_nosel)

print(f"\n  Selected:     {us_sel['n_units']:,} units  |  {int(us_sel['cases']):,} cases  |  rate {us_sel['rate']:.0f}/100k·yr")
print(f"  Non-selected: {us_nosel['n_units']:,} units  |  {int(us_nosel['cases']):,} cases  |  rate {us_nosel['rate']:.0f}/100k·yr")

# ── BUILD TABLE ────────────────────────────────────────────────────────────────
def f_pct(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    return f"{v:.1f}%"

def f_n(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    return f"{int(v):,}"

def f_rate(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    return f"{v:.0f}"

# Median cases/yr per selected unit
med_cases_yr_sel   = sel_df["n_cases"].median() / 5
med_cases_yr_nosel = unit_df[~unit_df["unit_id"].isin(selected_ids)]["n_cases"].median() / 5

# (label, sel_value_str, nosel_value_str, row_type)
rows = [
    # ── Population & TB burden ──────────────────────────────────────────────
    ("Population & TB burden",                     "",                              "",                               "header"),
    ("Number of geographic units",                 f_n(us_sel["n_units"]),          f_n(us_nosel["n_units"]),         "data"),
    ("Total population",                           f_n(us_sel["pop"]),              f_n(us_nosel["pop"]),             "data"),
    ("% of SP state population",                   f_pct(us_sel["pct_pop"]),        f_pct(us_nosel["pct_pop"]),       "data"),
    ("TB cases 2020–2024 (N)",                     f_n(us_sel["cases"]),            f_n(us_nosel["cases"]),           "data"),
    ("% of SP state TB cases",                     f_pct(us_sel["pct_cases"]),      f_pct(us_nosel["pct_cases"]),     "data"),
    ("TB incidence rate (per 100k/yr)",            f_rate(us_sel["rate"]),          f_rate(us_nosel["rate"]),         "data"),
    ("Median unit population",                     f_n(us_sel["med_pop"]),          f_n(us_nosel["med_pop"]),         "data"),
    ("Median cases/yr per unit",                   f"{med_cases_yr_sel:.1f}",       f"{med_cases_yr_nosel:.1f}",      "data"),
    # ── Patient characteristics ─────────────────────────────────────────────
    ("Patient characteristics",                    "",                              "",                               "header"),
    ("HIV positive (% of HIV-tested)",             f_pct(cs_sel["hiv_pos_pct"]),   f_pct(cs_nosel["hiv_pos_pct"]),   "data"),
    ("Pulmonary TB (%)",                           f_pct(cs_sel["pul_pct"]),        f_pct(cs_nosel["pul_pct"]),       "data"),
    # ── Discovery route ─────────────────────────────────────────────────────
    ("Discovery route",                            "",                              "",                               "header"),
    ("Found via outpatient demand (%)",            f_pct(cs_sel["outpt_pct"]),      f_pct(cs_nosel["outpt_pct"]),     "data"),
    ("Found via ER / urgency (%)",                 f_pct(cs_sel["emerg_pct"]),      f_pct(cs_nosel["emerg_pct"]),     "data"),
    ("Diagnosed during hospitalization (%)",       f_pct(cs_sel["hosp_dx_pct"]),   f_pct(cs_nosel["hosp_dx_pct"]),   "data"),
    ("Found via ACF (%)",                          f_pct(cs_sel["acf_total_pct"]),  f_pct(cs_nosel["acf_total_pct"]), "data"),
    ("Found via contact investigation (%)",        f_pct(cs_sel["contact_pct"]),    f_pct(cs_nosel["contact_pct"]),   "data"),
    # ── Treatment outcomes ──────────────────────────────────────────────────
    ("Treatment outcomes (% of known-outcome cases)", "",                           "",                               "header"),
    ("Treatment success / cure (%)",               f_pct(cs_sel["cure_pct"]),       f_pct(cs_nosel["cure_pct"]),      "data"),
    ("Lost to follow-up / abandonment (%)",        f_pct(cs_sel["ltfu_pct"]),       f_pct(cs_nosel["ltfu_pct"]),      "data"),
    ("Death from TB (%)",                          f_pct(cs_sel["tb_death_pct"]),   f_pct(cs_nosel["tb_death_pct"]),  "data"),
    ("Hospitalized during treatment (%)",          f_pct(cs_sel["hosp_admission_pct"]), f_pct(cs_nosel["hosp_admission_pct"]), "data"),
]

# ── CSV EXPORT ────────────────────────────────────────────────────────────────
csv_rows = [(r[0], r[1], r[2]) for r in rows if r[3] == "data"]
pd.DataFrame(csv_rows, columns=["Characteristic", "Selected hotspot areas", "Non-selected areas"]
    ).to_csv("/tmp/fig4b_table_two_col.csv", index=False)
print("  Saved /tmp/fig4b_table_two_col.csv")

# ── RENDER ─────────────────────────────────────────────────────────────────────
SEL_LAB   = f"Selected hotspot\nareas  (n = {us_sel['n_units']:,})"
NOSEL_LAB = f"Non-selected\nareas  (n = {us_nosel['n_units']:,})"

CLR_SEC_BG   = "#dce6f0"
CLR_SEL_HDR  = "#1a6b4a"
CLR_NOSEL_HDR= "#5d6d7e"
CLR_ROW_A    = "#f4f8fb";  CLR_ROW_B    = "#e8f2f8"
CLR_SEL_A    = "#e8f5ee";  CLR_SEL_B    = "#d5eddf"
CLR_NOSEL_A  = "#f2f2f2";  CLR_NOSEL_B  = "#e6e6e6"

row_h = 0.30; sec_h = 0.31
col_w = [4.2, 2.4, 2.4]
fig_w = sum(col_w) + 0.3
n_data = sum(1 for r in rows if r[3] == "data")
n_sec  = sum(1 for r in rows if r[3] == "header")
fig_h  = n_data * row_h + n_sec * sec_h + 0.95

fig4b, ax = plt.subplots(figsize=(fig_w, fig_h))
ax.set_xlim(0, fig_w); ax.set_ylim(0, fig_h); ax.axis("off")

# Column headers
hdr_y = fig_h - 0.55
for j, (lbl, clr, w) in enumerate(zip(
    ["", SEL_LAB, NOSEL_LAB],
    ["#1a3d5c", CLR_SEL_HDR, CLR_NOSEL_HDR], col_w,
)):
    x0 = sum(col_w[:j]) + 0.05
    ax.add_patch(matplotlib.patches.FancyBboxPatch(
        (x0, hdr_y - 0.28), w - 0.08, 0.48,
        boxstyle="round,pad=0.03", linewidth=0, facecolor=clr, zorder=2))
    ax.text(x0 + (w-0.08)/2, hdr_y - 0.04, lbl,
            ha="center", va="center", fontsize=9.5, fontweight="bold",
            color="white", multialignment="center", zorder=3)

y_cursor = hdr_y - 0.30
data_idx = 0
for label, v_sel, v_nosel, rtype in rows:
    rh = sec_h if rtype == "header" else row_h
    y0 = y_cursor - rh

    if rtype == "header":
        bgs = [CLR_SEC_BG, CLR_SEC_BG, CLR_SEC_BG]
        fg, fw, fs = "#1a3d5c", "bold", 9.5
    else:
        even = (data_idx % 2 == 0)
        bgs = [CLR_ROW_A if even else CLR_ROW_B,
               CLR_SEL_A if even else CLR_SEL_B,
               CLR_NOSEL_A if even else CLR_NOSEL_B]
        fg, fw, fs = "#222222", "normal", 9.5
        data_idx += 1

    for j, (bgc, w) in enumerate(zip(bgs, col_w)):
        x0 = sum(col_w[:j]) + 0.05
        ax.add_patch(matplotlib.patches.Rectangle(
            (x0, y0), w - 0.08, rh - 0.02,
            linewidth=0, facecolor=bgc, zorder=1))

    ax.text(sum(col_w[:0]) + 0.05 + 0.12, y0 + rh/2, label,
            ha="left", va="center", fontsize=fs, color=fg, fontweight=fw, zorder=3)

    if rtype == "data":
        for j, (val, w) in enumerate(zip([v_sel, v_nosel], col_w[1:])):
            x0 = sum(col_w[:j+1]) + 0.05
            ax.text(x0 + (w-0.08)/2, y0 + rh/2, val,
                    ha="center", va="center", fontsize=fs, color=fg,
                    fontweight="bold", zorder=3)

    y_cursor -= rh

# Title
ax.text(fig_w/2, fig_h - 0.20,
        "Characteristics of TB hotspot areas — São Paulo state  ·  2020–2024",
        ha="center", va="center", fontsize=11.5, fontweight="bold", color="#1a1a1a")

# Footnote
ax.text(fig_w/2, 0.06,
        f"SINAN 2020–2024 geocoded to IBGE CNEFE 2022  ·  "
        f"Selected: ≥10 cases/5yr, 20% pop window, FCU ≥5,000 pop  ·  "
        f"HIV+: % of HIV-tested  ·  outcomes exclude transfers & diagnostic changes  ·  "
        f"{TOTAL_POP/1e6:.1f}M residents  ·  {TOTAL_CASES:,} geocoded cases",
        ha="center", va="bottom", fontsize=7, color="#666", style="italic")

plt.tight_layout(pad=0.3)
plt.savefig("/tmp/fig4b_table_two_col.png", dpi=180, bbox_inches="tight", facecolor="white")
plt.close()
print("\n✓ Saved /tmp/fig4b_table_two_col.png")
