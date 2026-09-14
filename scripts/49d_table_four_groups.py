"""Four-group characteristics table:
  (1) GSP+Baixada Santista — Selected hotspots
  (2) GSP+Baixada Santista — Non-selected areas
  (3) Interior SP           — Selected hotspots
  (4) Interior SP           — Non-selected areas

Outputs:
  /tmp/table_four_groups.png
  /tmp/table_four_groups.docx
"""

import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import geopandas as gpd
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

matplotlib.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})

SPATIAL = ("/Users/evelynlepkadelima/Library/CloudStorage/"
           "GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/"
           "SP-TB-spatial-analyses/Data")
CAPITAL   = "3550308"
FCU_MIN   = 5000
MIN_CASES = 10
POP_WIN   = 0.20
BAIXADA   = {"3506359","3513504","3518701","3522109","3531100",
             "3537602","3541000","3548500","3551009"}

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s

# ── SECTORS + POPULATION ──────────────────────────────────────────────────────
print("Loading sectors...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]   = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)

pop_df = pd.read_csv(
    f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
    sep=";", encoding="latin-1", decimal=",",
    usecols=["CD_SETOR","v0001"], dtype={"CD_SETOR":str}, low_memory=False)
pop_df["pop"] = pd.to_numeric(pop_df["v0001"], errors="coerce").fillna(0)

sec = sec22.merge(pop_df[["CD_SETOR","pop"]], on="CD_SETOR", how="left")
sec["pop"] = sec["pop"].fillna(0)
sec_res = sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["pop"] >= 100)].copy()

# GSP = municipalities in the São Paulo urban conurbation
GSP = set(sec22[sec22["NM_CONCURB"] == "São Paulo/SP"]["CD_MUN"].unique())
ALL_GSP_BS = GSP | BAIXADA
sec_res = sec_res.copy()
sec_res["region"] = sec_res["CD_MUN"].apply(
    lambda m: "GSP_BS" if m in ALL_GSP_BS else "Interior")

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
TOTAL_POP = sec_res["pop"].sum()

def assign(row):
    nm = row["NM_FCU"]
    if pd.notna(nm) and nm in qualifying_fcus:
        return f"fcu__{nm}", nm, "FCU"
    return row["bairro_id"], row["bairro_label"], "bairro"

asgn = sec_res.apply(assign, axis=1, result_type="expand")
asgn.columns = ["unit_id","label","unit_type"]
sec_w = pd.concat([sec_res.reset_index(drop=True), asgn.reset_index(drop=True)], axis=1)

# unit_id → region (majority-sector)
unit_region = (sec_w.groupby("unit_id")["region"]
               .agg(lambda x: x.value_counts().index[0])
               .to_dict())

# Population stats by region
POP_GSP_BS   = sec_res[sec_res["region"] == "GSP_BS"]["pop"].sum()
POP_INTERIOR = sec_res[sec_res["region"] == "Interior"]["pop"].sum()

# ── GEOCODED CASES ─────────────────────────────────────────────────────────────
print("Loading geocoded cohorts...")
def load_co(path):
    df = pd.read_csv(path, low_memory=False, dtype={"sinan_clean":str})
    df["tier"] = df["cnefe_match"].astype(str).str.extract(r"^(T\d)")
    df = df[df["tier"].isin(["T1","T2","T3"])]
    df["CD_SETOR"] = df["setor_cnefe"].apply(norm_setor)
    return df[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])

gsp_co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False,
                     dtype={"sinan_clean":str})
gsp_co["CD_SETOR"] = gsp_co["setor_cnefe"].apply(norm_setor)
gsp_co = gsp_co[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])

cohort_geo = pd.concat([
    gsp_co,
    load_co("/tmp/cohort_baixada_with_cnefe_v2.csv"),
    load_co("/tmp/cohort_sp_outros_with_cnefe.csv"),
], ignore_index=True)

# Year filter
cohort_yr = pd.read_csv(f"{SPATIAL}/cohort_with_spatial.csv",
    usecols=["sinan_clean","notification_date"],
    low_memory=False, dtype={"sinan_clean":str})
cohort_yr["year"] = pd.to_datetime(
    cohort_yr["notification_date"], errors="coerce").dt.year
yr_map = (cohort_yr.dropna(subset=["sinan_clean","year"])
          .drop_duplicates("sinan_clean")
          .set_index("sinan_clean")["year"].to_dict())
cohort_geo["year"] = cohort_geo["sinan_clean"].map(yr_map)
cohort_geo = cohort_geo[cohort_geo["year"].between(2020, 2024)].copy()
TOTAL_CASES = len(cohort_geo)

# Assign unit_id and region to each case
setor_to_unit   = sec_w.set_index("CD_SETOR")["unit_id"].to_dict()
setor_to_region = sec_w.set_index("CD_SETOR")["region"].to_dict()
cohort_geo["unit_id"] = cohort_geo["CD_SETOR"].map(setor_to_unit)
cohort_geo["region"]  = cohort_geo["CD_SETOR"].map(setor_to_region)

# ── UNIT AGGREGATION + SELECTION ──────────────────────────────────────────────
unit_df = sec_w.groupby("unit_id").agg(
    pop=("pop","sum"), label=("label","first"),
    unit_type=("unit_type","first"), region=("region","first"),
).reset_index()
unit_df = unit_df.merge(
    cohort_geo.groupby("unit_id").size().rename("n_cases").reset_index(),
    on="unit_id", how="left")
unit_df["n_cases"] = unit_df["n_cases"].fillna(0)
unit_df["rate"]    = unit_df["n_cases"] / (unit_df["pop"] * 5) * 1e5

elig_df = unit_df[unit_df["n_cases"] >= MIN_CASES].copy()
elig_df = elig_df.sort_values("rate", ascending=False)
elig_df["cum_pop"] = elig_df["pop"].cumsum()
mask = elig_df["cum_pop"] <= TOTAL_POP * POP_WIN
if mask.sum() < len(elig_df): mask.iloc[mask.sum()] = True
sel_df       = elig_df[mask].copy()
selected_ids = set(sel_df["unit_id"])

print(f"  Selected: {len(selected_ids)} units")
sel_gsp = sel_df[sel_df["unit_id"].map(unit_region) == "GSP_BS"]
sel_int = sel_df[sel_df["unit_id"].map(unit_region) == "Interior"]
print(f"  GSP+BS selected: {len(sel_gsp)}  |  Interior selected: {len(sel_int)}")

# ── CLINICAL MERGE ─────────────────────────────────────────────────────────────
print("Loading clinical data...")
CLIN_COLS = ["sinan_clean","hiv","clinical_form_1","case_outcome",
             "disease_discovery","hosp_admission"]
clin = pd.read_csv(f"{SPATIAL}/cohort_with_spatial.csv",
    usecols=CLIN_COLS, low_memory=False,
    dtype={"sinan_clean":str}).drop_duplicates("sinan_clean")
cohort = cohort_geo.merge(clin, on="sinan_clean", how="left")

# ── FOUR GROUPS ────────────────────────────────────────────────────────────────
def split_group(region_tag, selected):
    if selected:
        unit_ids = {uid for uid in selected_ids
                    if unit_region.get(uid) == region_tag}
        cases = cohort[cohort["unit_id"].isin(unit_ids)]
    else:
        unit_ids = {uid for uid in unit_df["unit_id"]
                    if unit_region.get(uid) == region_tag
                    and uid not in selected_ids}
        # residual: all cases in region NOT in selected
        cases = cohort[
            (cohort["region"] == region_tag) &
            (~cohort["unit_id"].isin(selected_ids))
        ]
    return unit_ids, cases

g1_ids, g1_cases = split_group("GSP_BS",   selected=True)
g2_ids, g2_cases = split_group("GSP_BS",   selected=False)
g3_ids, g3_cases = split_group("Interior", selected=True)
g4_ids, g4_cases = split_group("Interior", selected=False)

# Unit-level stats
def unit_stats(uid_set, region_pop, region_cases_total):
    sub = unit_df[unit_df["unit_id"].isin(uid_set)]
    pop   = sub["pop"].sum()
    cases = cohort[cohort["unit_id"].isin(uid_set)].shape[0]
    return {
        "n_units":   len(sub),
        "pop":       pop,
        "pct_pop":   pop / TOTAL_POP * 100,
        "cases":     cases,
        "pct_cases": cases / TOTAL_CASES * 100,
        "rate":      cases / (pop * 5) * 1e5 if pop > 0 else 0,
        "med_pop":   int(sub["pop"].median()) if len(sub) else 0,
        "med_cases_yr": sub["n_cases"].median() / 5 if len(sub) else 0,
    }

# Compute region-level totals
cases_gsп_bs   = cohort[cohort["region"] == "GSP_BS"].shape[0]
cases_interior = cohort[cohort["region"] == "Interior"].shape[0]

# For non-selected: use residual population (region total - selected pop)
def nosel_stats(region_tag, sel_uid_set):
    region_pop   = POP_GSP_BS   if region_tag == "GSP_BS" else POP_INTERIOR
    region_cases = cases_gsп_bs if region_tag == "GSP_BS" else cases_interior
    sel_pop   = unit_df[unit_df["unit_id"].isin(sel_uid_set)]["pop"].sum()
    sel_cases = cohort[cohort["unit_id"].isin(sel_uid_set)].shape[0]
    ns_pop   = region_pop   - sel_pop
    ns_cases = region_cases - sel_cases
    ns_units = unit_df[(unit_df["unit_id"].map(unit_region) == region_tag) &
                       (~unit_df["unit_id"].isin(sel_uid_set))]
    return {
        "n_units":      len(ns_units),
        "pop":          int(ns_pop),
        "pct_pop":      ns_pop / TOTAL_POP * 100,
        "cases":        int(ns_cases),
        "pct_cases":    ns_cases / TOTAL_CASES * 100,
        "rate":         ns_cases / (ns_pop * 5) * 1e5 if ns_pop > 0 else 0,
        "med_pop":      int(ns_units["pop"].median()) if len(ns_units) else 0,
        "med_cases_yr": ns_units["n_cases"].median() / 5 if len(ns_units) else 0,
    }

s1 = unit_stats(g1_ids, POP_GSP_BS,   cases_gsп_bs)
s2 = nosel_stats("GSP_BS",   g1_ids)
s3 = unit_stats(g3_ids, POP_INTERIOR, cases_interior)
s4 = nosel_stats("Interior", g3_ids)

for tag, s in [("G1 GSP+BS sel", s1), ("G2 GSP+BS non", s2),
               ("G3 Interior sel", s3), ("G4 Interior non", s4)]:
    print(f"  {tag:20s}: {s['n_units']:>4} units | pop {s['pop']/1e6:.2f}M ({s['pct_pop']:.1f}%) | "
          f"{s['cases']:,} cases ({s['pct_cases']:.1f}%) | rate {s['rate']:.0f}/100k")

# Case-level clinical stats
def case_stats(df):
    dd   = df["disease_discovery"].dropna()
    n_dd = len(dd)
    oc   = df["case_outcome"].dropna()
    oc   = oc[~oc.isin(["Transf Outro Estado/Pais","Mud Diag","S/inf"])]
    n_oc = len(oc)
    hiv_tested = df["hiv"].isin(["Pos","Neg"])
    return {
        "hiv_pos":    df.loc[hiv_tested, "hiv"].eq("Pos").mean() * 100,
        "pulm":       df["clinical_form_1"].eq("Pul").sum() /
                      df["clinical_form_1"].notna().sum() * 100,
        "outpt":      dd.eq("Demanda Ambulatorial").sum() / n_dd * 100 if n_dd else np.nan,
        "er":         dd.eq("Urgencia / Emergencia").sum() / n_dd * 100 if n_dd else np.nan,
        "hosp_dx":    dd.eq("Elucidacao Diagn. em Internacao").sum() / n_dd * 100 if n_dd else np.nan,
        "acf":        dd.isin(["Busca Ativa em Instituicao",
                               "Busca Ativa na Comunidade"]).sum() / n_dd * 100 if n_dd else np.nan,
        "contact":    dd.eq("Investigacao de Contatos").sum() / n_dd * 100 if n_dd else np.nan,
        "cure":       oc.eq("Cura").sum() / n_oc * 100 if n_oc else np.nan,
        "ltfu":       oc.isin(["Abandono","Abandono Primario"]).sum() / n_oc * 100 if n_oc else np.nan,
        "tb_death":   oc.eq("Obito TB").sum() / n_oc * 100 if n_oc else np.nan,
        "hosp_tx":    df["hosp_admission"].eq("S").sum() /
                      df["hosp_admission"].isin(["S","N"]).sum() * 100,
    }

c1 = case_stats(g1_cases)
c2 = case_stats(g2_cases)
c3 = case_stats(g3_cases)
c4 = case_stats(g4_cases)

# ── BUILD TABLE ROWS ──────────────────────────────────────────────────────────
def fp(v):
    return "—" if (v is None or (isinstance(v, float) and np.isnan(v))) else f"{v:.1f}%"
def fn(v):
    return "—" if (v is None or (isinstance(v, float) and np.isnan(v))) else f"{int(v):,}"
def fr(v):
    return "—" if (v is None or (isinstance(v, float) and np.isnan(v))) else f"{v:.0f}"

ROWS = [
    # (label, G1, G2, G3, G4, is_section)
    ("POPULATION & TB BURDEN", "", "", "", "", True),
    ("Number of units",              fn(s1["n_units"]),    fn(s2["n_units"]),    fn(s3["n_units"]),    fn(s4["n_units"]),    False),
    ("Total population",             fn(s1["pop"]),        fn(s2["pop"]),        fn(s3["pop"]),        fn(s4["pop"]),        False),
    ("% of SP state population",      fp(s1["pct_pop"]),    fp(s2["pct_pop"]),    fp(s3["pct_pop"]),    fp(s4["pct_pop"]),    False),
    ("TB cases 2020–2024 (N)",       fn(s1["cases"]),      fn(s2["cases"]),      fn(s3["cases"]),      fn(s4["cases"]),      False),
    ("% of SP state TB cases",        fp(s1["pct_cases"]),  fp(s2["pct_cases"]),  fp(s3["pct_cases"]),  fp(s4["pct_cases"]),  False),
    ("TB rate (per 100,000/yr)",     fr(s1["rate"]),       fr(s2["rate"]),       fr(s3["rate"]),       fr(s4["rate"]),       False),
    ("Median unit population",       fn(s1["med_pop"]),    fn(s2["med_pop"]),    fn(s3["med_pop"]),    fn(s4["med_pop"]),    False),
    ("Median cases/yr per unit",     f"{s1['med_cases_yr']:.1f}", f"{s2['med_cases_yr']:.1f}",
                                     f"{s3['med_cases_yr']:.1f}", f"{s4['med_cases_yr']:.1f}", False),

    ("PATIENT CHARACTERISTICS", "", "", "", "", True),
    ("HIV positive (% of tested)",   fp(c1["hiv_pos"]),   fp(c2["hiv_pos"]),   fp(c3["hiv_pos"]),   fp(c4["hiv_pos"]),   False),
    ("Pulmonary TB (%)",             fp(c1["pulm"]),      fp(c2["pulm"]),      fp(c3["pulm"]),      fp(c4["pulm"]),      False),

    ("DISCOVERY ROUTE", "", "", "", "", True),
    ("Outpatient care — patient demand (%)", fp(c1["outpt"]),    fp(c2["outpt"]),    fp(c3["outpt"]),    fp(c4["outpt"]),    False),
    ("Emergency/urgency presentation (%)",  fp(c1["er"]),        fp(c2["er"]),        fp(c3["er"]),        fp(c4["er"]),        False),
    ("Diagnosed during hospitalisation (%)", fp(c1["hosp_dx"]), fp(c2["hosp_dx"]), fp(c3["hosp_dx"]), fp(c4["hosp_dx"]), False),
    ("Active case finding (ACF) (%)",        fp(c1["acf"]),      fp(c2["acf"]),      fp(c3["acf"]),      fp(c4["acf"]),      False),
    ("Contact investigation (%)",            fp(c1["contact"]),  fp(c2["contact"]),  fp(c3["contact"]),  fp(c4["contact"]),  False),

    ("TREATMENT OUTCOMES  (% of known-outcome cases)", "", "", "", "", True),
    ("Treatment success / cure (%)", fp(c1["cure"]),      fp(c2["cure"]),      fp(c3["cure"]),      fp(c4["cure"]),      False),
    ("Lost to follow-up (%)",        fp(c1["ltfu"]),      fp(c2["ltfu"]),      fp(c3["ltfu"]),      fp(c4["ltfu"]),      False),
    ("Death from TB (%)",            fp(c1["tb_death"]),  fp(c2["tb_death"]),  fp(c3["tb_death"]),  fp(c4["tb_death"]),  False),
    ("Hospitalised during treatment (%)", fp(c1["hosp_tx"]), fp(c2["hosp_tx"]), fp(c3["hosp_tx"]), fp(c4["hosp_tx"]), False),
]

FOOTNOTE = (
    "SINAN notifications 2020–2024 geocoded to IBGE CNEFE 2022  ·  "
    "GSP = Grande São Paulo (urban conurbation, IBGE NM_CONCURB São Paulo/SP)  ·  "
    "Baixada Santista = 9 coastal municipalities (Santos metropolitan region)  ·  "
    "Non-metropolitan SP state = all other SP state municipalities  ·  "
    "Hotspot selection: ≥10 cases/5yr, 20% population window, FCU ≥5,000 pop  ·  "
    "% of SP state pop/cases = relative to all 43.8M residents and all geocoded cases  ·  "
    "HIV+: % of HIV-tested  ·  outcomes exclude transfers and diagnostic changes  ·  "
    "43.8M residents  ·  77,275 geocoded cases"
)

# ═══════════════════════════════════════════════════════════════════════════════
# PNG
# ═══════════════════════════════════════════════════════════════════════════════
n_data = sum(1 for *_, s in ROWS if not s)
n_sec  = sum(1 for *_, s in ROWS if s)
ROW_H = 0.32; SEC_H = 0.36; HDR_H = 0.70; TITLE_H = 0.40; FOOT_H = 0.32

PAD  = 0.22
C0_W = 4.6    # label
C1_W = 1.85   # G1
C2_W = 1.85   # G2
C3_W = 1.85   # G3
C4_W = 1.85   # G4
GAP  = 0.00

FW = PAD + C0_W + C1_W + C2_W + C3_W + C4_W + PAD
FH = TITLE_H + HDR_H + n_sec*SEC_H + n_data*ROW_H + FOOT_H + 0.12

# X boundaries of each data column
X = [PAD,
     PAD + C0_W,
     PAD + C0_W + C1_W,
     PAD + C0_W + C1_W + C2_W,
     PAD + C0_W + C1_W + C2_W + C3_W,
     PAD + C0_W + C1_W + C2_W + C3_W + C4_W]

X_RIGHT = X[5]

def xc(col):   # centre of column col (1-indexed data col)
    return (X[col] + X[col+1]) / 2

# Colour scheme: two shades for the two regions
HDR_COL = ["#1a5c3a","#2d6a4f","#744210","#92400e"]  # G1,G2,G3,G4

ROW_BG = [
    ["#e6f4ec","#d4edda","#fef3c7","#fde68a"],   # odd
    ["#c3e6cb","#b8ddc0","#fde68a","#fcd34d"],   # even — slightly darker
]
SEC_BG = "#2c5282"

fig, ax = plt.subplots(figsize=(FW, FH))
ax.set_xlim(0, FW); ax.set_ylim(0, FH); ax.axis("off")

def fill(x0,x1,y0,y1,c, z=1):
    ax.add_patch(patches.Rectangle((x0,y0),x1-x0,y1-y0,linewidth=0,facecolor=c,zorder=z))
def hline(y, c="#cbd5e0", lw=0.5):
    ax.plot([PAD, X_RIGHT],[y,y], color=c, lw=lw, zorder=3)
def vline(x, y0, y1, c="#b0bec5", lw=0.5):
    ax.plot([x,x],[y0,y1], color=c, lw=lw, zorder=3)

# Title
ax.text(FW/2, FH - TITLE_H/2,
        "Characteristics of TB targeting areas by region — São Paulo state  ·  2020–2024",
        ha="center", va="center", fontsize=12, fontweight="bold", color="#1a202c", zorder=5)

# Region super-headers
y_super = FH - TITLE_H
y_hdr1  = y_super - HDR_H/2
y_hdr2  = y_super - HDR_H
fill(X[1],X[3], y_hdr2, y_super, "#1a4731")   # GSP+BS band
fill(X[3],X[5], y_hdr2, y_super, "#5c3a00")   # Interior band
ax.text((X[1]+X[3])/2, y_super - HDR_H*0.25,
        "São Paulo urban agglomeration", ha="center", va="center",
        fontsize=10.5, fontweight="bold", color="white", zorder=5)
ax.text((X[3]+X[5])/2, y_super - HDR_H*0.25,
        "Non-metropolitan SP state", ha="center", va="center",
        fontsize=10.5, fontweight="bold", color="white", zorder=5)

# Column sub-headers
for j, (txt, clr) in enumerate([
    ("", "#f0f4f8"),
    ("Selected\nhotspots", "#1a5c3a"),
    ("Non-selected\nareas",   "#2d6a4f"),
    ("Selected\nhotspots", "#92400e"),
    ("Non-selected\nareas",   "#b45309"),
]):
    fill(X[j], X[j+1], y_hdr2, y_super-HDR_H*0.45, clr)
    if txt:
        ax.text((X[j]+X[j+1])/2, y_super - HDR_H*0.73,
                txt, ha="center", va="center",
                fontsize=9.5, fontweight="bold", color="white",
                multialignment="center", zorder=5)

hline(y_hdr2, "#1a3d5c", lw=1.5)

# Data rows
y_cur = y_hdr2
data_i = 0
for row in ROWS:
    label, v1, v2, v3, v4, is_sec = row
    rh = SEC_H if is_sec else ROW_H
    y0 = y_cur - rh

    if is_sec:
        fill(PAD, X_RIGHT, y0, y_cur, SEC_BG)
        ax.text(PAD+0.12, (y_cur+y0)/2, label,
                ha="left", va="center", fontsize=9.5, fontweight="bold",
                color="white", zorder=5)
        hline(y0, "#1a3d5c", lw=1.2)
    else:
        ci = data_i % 2
        fill(X[0], X[1], y0, y_cur, "#f7fafc" if ci==0 else "#edf2f7")
        for j, (clr1, clr2) in enumerate([
            (ROW_BG[0][0], ROW_BG[1][0]),
            (ROW_BG[0][1], ROW_BG[1][1]),
            (ROW_BG[0][2], ROW_BG[1][2]),
            (ROW_BG[0][3], ROW_BG[1][3]),
        ]):
            fill(X[j+1], X[j+2], y0, y_cur, clr1 if ci==0 else clr2)

        ax.text(PAD+0.10, (y_cur+y0)/2, label,
                ha="left", va="center", fontsize=9.5, color="#1a202c", zorder=5)
        for j, val in enumerate([v1, v2, v3, v4]):
            ax.text(xc(j+1), (y_cur+y0)/2, val,
                    ha="center", va="center", fontsize=9.5,
                    fontweight="bold", color="#1a202c", zorder=5)
        hline(y0, "#cbd5e0", lw=0.35)
        data_i += 1

    y_cur = y0

# Vertical dividers
hline(FH-TITLE_H, "#2c5282", lw=1.5)
vline(X[1], y_cur, FH-TITLE_H, "#b0bec5", lw=0.6)
vline(X[2], y_cur, FH-TITLE_H, "#b0bec5", lw=0.6)
vline(X[3], y_cur, FH-TITLE_H, "#4a5568", lw=1.2)
vline(X[4], y_cur, FH-TITLE_H, "#b0bec5", lw=0.6)

ax.text(PAD, y_cur-0.07, FOOTNOTE,
        ha="left", va="top", fontsize=6.8, color="#718096", style="italic")

plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
plt.savefig("/tmp/table_four_groups.png", dpi=200, facecolor="white")
plt.close()
print("Saved /tmp/table_four_groups.png")

# ═══════════════════════════════════════════════════════════════════════════════
# DOCX
# ═══════════════════════════════════════════════════════════════════════════════
def set_cell_bg(cell, hex_color):
    tc = cell._tc; tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color.lstrip("#")); tcPr.append(shd)

def set_borders(cell, color="CBD5E0", sz=4):
    tc = cell._tc; tcPr = tc.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for side in ["top","bottom","left","right"]:
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"),"single"); el.set(qn("w:sz"),str(sz))
        el.set(qn("w:color"),color); b.append(el)
    tcPr.append(b)

def cell_text(cell, txt, bold=False, size=10, color=(26,32,44),
              align=WD_ALIGN_PARAGRAPH.CENTER, bg=None, italic=False):
    if bg: set_cell_bg(cell, bg)
    set_borders(cell)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after  = Pt(2)
    r = p.add_run(txt)
    r.bold = bold; r.italic = italic
    r.font.size = Pt(size)
    r.font.color.rgb = RGBColor(*color)

doc = Document()
for sec in doc.sections:
    sec.top_margin = Cm(1.8); sec.bottom_margin = Cm(1.8)
    sec.left_margin = Cm(1.5); sec.right_margin = Cm(1.5)
    sec.page_width  = Cm(29.7); sec.page_height = Cm(21.0)  # A4 landscape

title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = title.add_run(
    "Characteristics of TB targeting areas by region — São Paulo state · 2020–2024")
r.bold = True; r.font.size = Pt(13)
r.font.color.rgb = RGBColor(26,32,44)
title.paragraph_format.space_after = Pt(8)

# Table: 5 cols (label + 4 groups), region super-header + col sub-header + data
tbl = doc.add_table(rows=len(ROWS)+2, cols=5)
tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
tbl.style = "Table Grid"
CW_DOCX = [Cm(7.2), Cm(3.5), Cm(3.5), Cm(3.5), Cm(3.5)]
for row in tbl.rows:
    for j, cell in enumerate(row.cells):
        cell.width = CW_DOCX[j]

# Row 0: region super-headers (merged pairs)
r0 = tbl.rows[0]
cell_text(r0.cells[0], "", bg="#f0f4f8")
r0.cells[1].merge(r0.cells[2])
cell_text(r0.cells[1], "São Paulo urban agglomeration",
          bold=True, size=10.5, color=(255,255,255), bg="#1a4731")
r0.cells[3].merge(r0.cells[4])
cell_text(r0.cells[3], "Non-metropolitan SP state",
          bold=True, size=10.5, color=(255,255,255), bg="#5c3a00")

# Row 1: column sub-headers
r1 = tbl.rows[1]
cell_text(r1.cells[0], "", bg="#f0f4f8")
for j, (txt, bg) in enumerate([
    ("Selected hotspots",  "#1a5c3a"),
    ("Non-selected areas", "#2d6a4f"),
    ("Selected hotspots",  "#92400e"),
    ("Non-selected areas", "#b45309"),
]):
    cell_text(r1.cells[j+1], txt, bold=True, size=10,
              color=(255,255,255), bg=bg)

# Data rows
SEC_BG_HEX = "2c5282"
ROW_BG_DOCX = [
    ["f7fafc","e6f4ec","d4edda","fef3c7","fde68a"],
    ["edf2f7","c3e6cb","b8ddc0","fde68a","fcd34d"],
]
data_i = 0
for ri, row in enumerate(ROWS):
    label, v1, v2, v3, v4, is_sec = row
    tbl_row = tbl.rows[ri + 2]
    if is_sec:
        tbl_row.cells[0].merge(tbl_row.cells[4])
        cell_text(tbl_row.cells[0], label, bold=True, size=10,
                  color=(255,255,255), bg=SEC_BG_HEX,
                  align=WD_ALIGN_PARAGRAPH.LEFT)
    else:
        ci = data_i % 2
        bgs = ROW_BG_DOCX[ci]
        cell_text(tbl_row.cells[0], label, size=10, bg=bgs[0],
                  align=WD_ALIGN_PARAGRAPH.LEFT)
        for j, val in enumerate([v1, v2, v3, v4]):
            cell_text(tbl_row.cells[j+1], val, bold=True, size=10, bg=bgs[j+1])
        data_i += 1

fn_p = doc.add_paragraph()
fn_p.paragraph_format.space_before = Pt(5)
r = fn_p.add_run(FOOTNOTE)
r.italic = True; r.font.size = Pt(7.5)
r.font.color.rgb = RGBColor(113,128,150)

doc.save("/tmp/table_four_groups.docx")
print("Saved /tmp/table_four_groups.docx")
