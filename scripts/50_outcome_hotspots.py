"""Outcome-based hotspots — abandonment and mortality treated SEPARATELY.

Rationale: incidence (cases/pop) under-counts high-vulnerability areas that
under-notify. Adverse outcomes AMONG NOTIFIED cases measure how hostile an area
is to successful TB treatment, independent of case ascertainment. Crucially,
abandonment and mortality are NOT combined: the de-noising + non-TB-death negative
control (scripts 57-61) show abandonment is a robust, TB-specific concentration
while the mortality concentration is general vulnerability. We map each lens on its
own and compare each to incidence.

Abandonment marker : Abandono + Abandono Primario (denominator: evaluated cases)
Mortality marker   : TB mortality = integrated TBweb 'Obito TB' OR SIM TB on any
                     death-certificate line (see script 60), capturing deaths before
                     and/or after treatment. Reported here as the PROPORTION of ALL
                     NOTIFIED cases (not restricted to evaluated; CFR is dropped); the
                     TB-mortality RATE per population lives in the intensity maps (67/69).
All metrics age-standardised (indirect, SP reference; script 78).

Outputs (/tmp/):
  fig_outcome_maps_separate.png — abandonment % and TB mortality % (of notified) choropleths
  fig_inc_vs_aband.png          — incidence vs abandonment hotspots (state + metro)
  fig_inc_vs_death.png          — incidence vs mortality hotspots (state + metro)
  fig_aband_vs_death.png        — abandonment vs mortality hotspots (do they agree?)
  outcome_units.csv
"""
import pandas as pd, geopandas as gpd, numpy as np, re
import matplotlib, matplotlib.pyplot as plt, matplotlib.patches as mpatches
matplotlib.rcParams.update({"font.family": "sans-serif", "font.size": 11})

SPATIAL   = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD        = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/Abandonment Outcomes/Abandonment Paper/Banco de dados"
CAPITAL, FCU_MIN, MIN_CASES, POP_WIN, MIN_EVAL = "3550308", 5000, 10, 0.20, 10

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip(); return s[:-1] if s.endswith("P") else s
def norm_key(s): return s.astype(str).str.strip().str.replace(r'\.0$','',regex=True).str.lstrip("0")

# ── unit construction (identical to script 49) ──────────────────────────────
print("Building units...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"] = sec22["CD_MUN"].astype(str); sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)
import zipfile
pop_df = pd.read_csv(f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
                     sep=";", encoding="latin-1", decimal=",",
                     usecols=["CD_SETOR","v0001"], dtype={"CD_SETOR":str}, low_memory=False)
pop_df["pop_total"] = pd.to_numeric(pop_df["v0001"], errors="coerce").fillna(0)
ADULT_COLS=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]  # ages 15+
with zipfile.ZipFile(f"{SPATIAL}/IBGE_2022_extended/demografia.zip") as z:
    with z.open("Agregados_por_setores_demografia_BR.csv") as fh:
        _demo=pd.read_csv(fh,sep=";",encoding="latin-1",decimal=",",usecols=["CD_setor"]+ADULT_COLS,dtype={"CD_setor":str},low_memory=False)
_demo["pop"]=_demo[ADULT_COLS].apply(pd.to_numeric,errors="coerce").fillna(0).sum(axis=1)
_demo=_demo[["CD_setor","pop"]].rename(columns={"CD_setor":"CD_SETOR"})
sec = sec22.merge(pop_df[["CD_SETOR","pop_total"]],on="CD_SETOR",how="left").merge(_demo,on="CD_SETOR",how="left")
sec["pop"]=sec["pop"].fillna(0); sec["pop_total"]=sec["pop_total"].fillna(0)
sec_res = sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["pop_total"] >= 100)].copy()

def bairro_key(row):
    if str(row["CD_MUN"]) == CAPITAL: return f"dist_{row['CD_DIST']}", f"SP/{row['NM_DIST']}"
    if pd.notna(row.get("NM_BAIRRO")): return f"bairro_{row['CD_MUN']}_{row['NM_BAIRRO']}", f"{row['NM_MUN']}/{row['NM_BAIRRO']}"
    if pd.notna(row.get("NM_DIST")):   return f"dist_{row['CD_DIST']}", f"{row['NM_MUN']}/{row['NM_DIST']}"
    return f"mun_{row['CD_MUN']}", row["NM_MUN"]
sec_res[["bairro_id","bairro_label"]] = sec_res.apply(bairro_key, axis=1, result_type="expand")
fcu_pop = sec_res[sec_res["NM_FCU"].notna()].groupby("NM_FCU")["pop"].sum()
qualifying_fcus = set(fcu_pop[fcu_pop >= FCU_MIN].index)
TOTAL_POP = sec_res["pop"].sum()
def assign(row):
    nm = row["NM_FCU"]
    if pd.notna(nm) and nm in qualifying_fcus: return f"fcu__{nm}", nm, "FCU"
    return row["bairro_id"], row["bairro_label"], "bairro"
sec_res[["unit_id","label","unit_type"]] = sec_res.apply(assign, axis=1, result_type="expand")

# ── cases + outcomes ────────────────────────────────────────────────────────
print("Loading cases + outcomes...")
def load_co(path, raw=False):
    df = pd.read_csv(path, low_memory=False, dtype={"sinan_clean":str})
    if not raw:
        df["tier"] = df["cnefe_match"].astype(str).str.extract(r"^(T\d)")
        df = df[df["tier"].isin(["T1","T2","T3"])]
    df["CD_SETOR"] = df["setor_cnefe"].apply(norm_setor)
    return df[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
cohort = pd.concat([load_co("/tmp/cohort_with_cnefe.csv", raw=True),
                    load_co("/tmp/cohort_baixada_with_cnefe_v2.csv"),
                    load_co("/tmp/cohort_sp_outros_with_cnefe.csv")], ignore_index=True)

meta = pd.read_csv(f"{SPATIAL}/cohort_with_spatial.csv",
                   usecols=["sinan_clean","notification_date","case_outcome","tx_seq","age_tb"],
                   low_memory=False, dtype={"sinan_clean":str})
meta["year"] = pd.to_datetime(meta["notification_date"], errors="coerce").dt.year
meta = meta.sort_values("tx_seq").drop_duplicates("sinan_clean", keep="last")
mi = meta.set_index("sinan_clean")
cohort["year"]    = cohort["sinan_clean"].map(mi["year"])
cohort["outcome"] = cohort["sinan_clean"].map(mi["case_outcome"])
cohort["age_tb"]  = cohort["sinan_clean"].map(mi["age_tb"])
cohort = cohort[(cohort["year"].between(2013, 2024)) & (cohort["age_tb"] >= 15)]  # adults 2013-2024
cohort["unit_id"] = cohort["CD_SETOR"].map(sec_res.set_index("CD_SETOR")["unit_id"].to_dict())

DEATH_TB={"Obito TB"}; DEATH_NTB={"Obito NTB"}; ABAND={"Abandono","Abandono Primario"}
CURE={"Cura"}; FAIL={"Falencia/Resistencia"}
EVAL = CURE|ABAND|DEATH_TB|DEATH_NTB|FAIL          # definitive outcomes (denominator)
# integrated TB-death marker: TBweb 'Obito TB' OR SIM TB on any death-certificate line (see script 60)
print("Loading SIM integrated mortality...")
_sim = pd.read_excel(f"{BD}/LINKAGE SIM (1).xlsx", sheet_name="Limpo",
                     usecols=["SINAN","CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"], dtype=str).dropna(subset=["SINAN"])
_sim["all"]=[" ".join([str(x) for x in r if x and str(x)!='nan']).upper().replace(".","") for r in _sim[["CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"]].values]
SIM_TB = set(norm_key(_sim.loc[_sim["all"].str.contains(re.compile(r'A1[5-9]')), "SINAN"]))
o = cohort["outcome"]; sim_tb = norm_key(cohort["sinan_clean"]).isin(SIM_TB)
cohort["death_tb"]  = o.isin(DEATH_TB) | sim_tb                 # integrated TBweb+SIM TB death
cohort["death_ntb"] = o.isin(DEATH_NTB) & ~cohort["death_tb"]   # non-TB death (excl. SIM-confirmed TB)
cohort["aband"]     = o.isin(ABAND)
cohort["evaluated"] = o.isin(EVAL) | cohort["death_tb"]         # SIM TB-death is a definitive outcome
cohort["adv_p"]     = cohort["death_tb"] | cohort["aband"]                       # PRIMARY: TB death + abandonment
cohort["adv_s"]     = cohort["death_tb"] | cohort["death_ntb"] | cohort["aband"]  # SENSITIVITY: + non-TB death

# ── unit-level aggregation ──────────────────────────────────────────────────
g = cohort.groupby("unit_id").agg(
    n_cases=("sinan_clean","size"), n_eval=("evaluated","sum"),
    n_adv_p=("adv_p","sum"), n_adv_s=("adv_s","sum"),
    n_death_tb=("death_tb","sum"), n_death_ntb=("death_ntb","sum"), n_aband=("aband","sum")).reset_index()
upop = sec_res.groupby("unit_id").agg(pop=("pop","sum"), label=("label","first"),
                                      unit_type=("unit_type","first")).reset_index()
u = upop.merge(g, on="unit_id", how="left").fillna(0)
u["rate"]      = u["n_cases"]/(u["pop"]*12)*1e5
u["adv_pct"]   = np.where(u["n_eval"]>0, u["n_adv_p"]/u["n_eval"]*100, np.nan)   # primary
u["adv_pct_s"] = np.where(u["n_eval"]>0, u["n_adv_s"]/u["n_eval"]*100, np.nan)   # +non-TB death
u["tbmort_pct"]= np.where(u["n_cases"]>0, u["n_death_tb"]/u["n_cases"]*100, np.nan)  # TB mortality, % of ALL notified
u["aband_pct"] = np.where(u["n_eval"]>0, u["n_aband"]/u["n_eval"]*100, np.nan)
# age-standardised rates (indirect standardisation, SP internal reference; script 78) replace crude
# for all mapped/selected geospatial metrics — incidence, abandonment, TB mortality (% of notified cases).
_asr=pd.read_csv("/tmp/unit_age_standardised.csv")[["unit_id","inc_adj","ltfu_adj","mortprop_adj"]]
u=u.merge(_asr,on="unit_id",how="left")
u["rate"]=u["inc_adj"]; u["aband_pct"]=u["ltfu_adj"]; u["tbmort_pct"]=u["mortprop_adj"]
assert u["rate"].notna().sum()>=1000, f"age-std merge coverage too low: {u['rate'].notna().sum()}"

# ── selections: SEPARATE outcome lenses (abandonment vs mortality) ───────────
# Abandonment and mortality behave differently — abandonment is a TB-specific,
# robustly concentrated signal, whereas the mortality concentration is general
# vulnerability (non-TB-death negative control, script 61). We therefore select and
# map them SEPARATELY, not as a single combined adverse marker.
def select(df, by):
    d = df.sort_values(by, ascending=False).copy()
    d["cum"] = d["pop"].cumsum(); m = d["cum"] <= TOTAL_POP*POP_WIN
    if m.sum() < len(d): m.iloc[m.sum()] = True
    return set(d[m]["unit_id"])
elig   = u[u["n_cases"] >= MIN_CASES].copy()
elig_o = elig[elig["n_eval"] >= MIN_EVAL].copy()
HS_inc   = select(elig,   "rate")
HS_aband = select(elig_o, "aband_pct")    # abandonment hotspots (TB-specific, robust)
HS_death = select(elig_o, "tbmort_pct")       # mortality hotspots (TB case-fatality; vulnerability)

# ── summary ─────────────────────────────────────────────────────────────────
ev=cohort["evaluated"].sum()
def jac(a,b): return len(a&b)/len(a|b) if (a|b) else float("nan")
print("\n================  STATE SUMMARY (2013–2024)  ================")
print(f"Geocoded cases {len(cohort):,} | evaluated {ev:,}")
print(f"State abandonment % (of evaluated)         : {cohort['aband'].sum()/ev*100:.1f}%")
print(f"State TB mortality (Obito TB/SIM), % of notified : {cohort['death_tb'].sum()/len(cohort)*100:.1f}%")

def prof(ids, lab):
    d = u[u["unit_id"].isin(ids)]; ev_=d["n_eval"].sum(); cs=d["n_cases"].sum()
    print(f"  {lab:22s} units={len(d):4d} pop={d['pop'].sum()/1e6:.2f}M inc={cs/(d['pop'].sum()*12)*1e5:5.0f}/100k "
          f"aband%={d['n_aband'].sum()/ev_*100:4.1f} TBmort%notif={d['n_death_tb'].sum()/cs*100:4.1f}")

def compare(HS_o, tag):
    both=HS_inc&HS_o; io=HS_inc-HS_o; oo=HS_o-HS_inc
    print(f"\n--- {tag} hotspots vs incidence ---")
    print(f"Incidence HS={len(HS_inc)} | {tag} HS={len(HS_o)} | Jaccard={jac(HS_inc,HS_o):.3f} "
          f"(both={len(both)} inc-only={len(io)} {tag.lower()}-only={len(oo)})")
    prof(HS_inc,"Incidence HS"); prof(HS_o,f"{tag} HS")
    prof(oo,f"  {tag.lower()}-ONLY"); prof(io,"  incidence-ONLY")
    return oo
oo_a = compare(HS_aband, "Abandonment")
oo_d = compare(HS_death, "Mortality")
print(f"\nDo the two outcome lenses agree with EACH OTHER?  "
      f"Abandonment-HS vs Mortality-HS Jaccard = {jac(HS_aband,HS_death):.3f}")
u["hs_inc"]=u["unit_id"].isin(HS_inc); u["hs_aband"]=u["unit_id"].isin(HS_aband); u["hs_death"]=u["unit_id"].isin(HS_death)
u.to_csv("/tmp/outcome_units.csv", index=False); print("Saved /tmp/outcome_units.csv")

# ── geometry ────────────────────────────────────────────────────────────────
print("Dissolving geometries...")
gdf = (sec_res[sec_res["unit_id"].isin(elig["unit_id"])][["unit_id","geometry"]]
       .dissolve(by="unit_id").reset_index().merge(u, on="unit_id", how="left"))
STATE = sec_res.dissolve()
BASE = gpd.read_file("/tmp/sp_muni_base.gpkg")  # full municipal territory (fills unpopulated Serra do Mar void)
ZOOM = dict(xlim=(-47.6,-45.8), ylim=(-24.3,-23.2))

def overlap_panel(ax, A, B, colB, labB, xlim=None, ylim=None, title="", legend=True):
    both=A&B; ao=A-B; bo=B-A
    def cat(uid): return "Both" if uid in both else "Incidence only" if uid in ao else (f"{labB} only" if uid in bo else "Other")
    gdf["_cat"]=gdf["unit_id"].map(cat)
    COL={"Both":"#6a0dad","Incidence only":"#c0392b",f"{labB} only":colB,"Other":"#ededed"}
    BASE.plot(ax=ax, color="#eeeeee", edgecolor="#dcdcdc", lw=0.15)  # full municipal territory (no void)
    BASE.boundary.plot(ax=ax, color="#b8b8b8", lw=0.3)
    for c in ["Other","Incidence only",f"{labB} only","Both"]:
        s=gdf[gdf["_cat"]==c]
        if len(s): s.plot(ax=ax, color=COL[c], edgecolor="white", lw=0.05)
    if xlim: ax.set_xlim(*xlim)
    if ylim: ax.set_ylim(*ylim)
    if legend:
        ax.legend(handles=[mpatches.Patch(color=COL[c],label=f"{c} (n={(gdf['_cat']==c).sum()})")
                  for c in ["Both","Incidence only",f"{labB} only"]], loc="lower left", fontsize=9)
    ax.set_title(title, fontsize=11, fontweight="bold"); ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")

gdf_ch = gdf[gdf["n_eval"] >= MIN_EVAL]

# FIG 1: two separate choropleths — abandonment % and TB case-fatality %
fig, axes = plt.subplots(1, 2, figsize=(18,7.5))
BASE.plot(ax=axes[0], color="#eeeeee", edgecolor="#dcdcdc", lw=0.15); BASE.boundary.plot(ax=axes[0], color="#cccccc", lw=0.3)
gdf_ch.plot(column="aband_pct", ax=axes[0], cmap="Blues", legend=True, vmin=4, vmax=24,
            legend_kwds={"label":"Treatment abandonment %, age-standardised","shrink":0.5})
axes[0].set_title("A)  Treatment abandonment (age-standardised)", fontsize=12, fontweight="bold")
BASE.plot(ax=axes[1], color="#eeeeee", edgecolor="#dcdcdc", lw=0.15); BASE.boundary.plot(ax=axes[1], color="#cccccc", lw=0.3)
gdf_ch.plot(column="tbmort_pct", ax=axes[1], cmap="Reds", legend=True, vmin=0, vmax=14,
            legend_kwds={"label":"TB mortality, % of notified cases (TBweb+SIM), age-standardised","shrink":0.5})
axes[1].set_title("B)  TB mortality (% of notified cases, age-standardised)", fontsize=12, fontweight="bold")
for a in axes: a.set_xlabel("Longitude"); a.set_ylabel("Latitude")
fig.suptitle("Two distinct adverse-outcome geographies (age-standardised) — São Paulo state, 2013–2024  ·  units with ≥10 evaluated cases",
             fontsize=13, fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_outcome_maps_separate.png", dpi=140, bbox_inches="tight"); plt.close()
print("Saved fig_outcome_maps_separate.png")

# FIG 2: incidence vs ABANDONMENT hotspots
fig, axes = plt.subplots(1, 2, figsize=(17,7))
overlap_panel(axes[0], HS_inc, HS_aband, "#1f77b4", "Abandonment", title="A)  Whole state")
overlap_panel(axes[1], HS_inc, HS_aband, "#1f77b4", "Abandonment", title="B)  Greater SP + Baixada (zoom)", legend=False, **ZOOM)
fig.suptitle("Incidence vs ABANDONMENT hotspots — the robust, TB-specific outcome signal",
             fontsize=13, fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_inc_vs_aband.png", dpi=140, bbox_inches="tight"); plt.close()
print("Saved fig_inc_vs_aband.png")

# FIG 3: incidence vs MORTALITY hotspots
fig, axes = plt.subplots(1, 2, figsize=(17,7))
overlap_panel(axes[0], HS_inc, HS_death, "#c44e00", "Mortality", title="A)  Whole state")
overlap_panel(axes[1], HS_inc, HS_death, "#c44e00", "Mortality", title="B)  Greater SP + Baixada (zoom)", legend=False, **ZOOM)
fig.suptitle("Incidence vs MORTALITY hotspots — TB mortality, % of notified cases (age-standardised)",
             fontsize=13, fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_inc_vs_death.png", dpi=140, bbox_inches="tight"); plt.close()
print("Saved fig_inc_vs_death.png")

# FIG 4: do the two outcome lenses agree with each other?  abandonment vs mortality
fig, ax = plt.subplots(figsize=(11,8))
both=HS_aband&HS_death; ao=HS_aband-HS_death; do_=HS_death-HS_aband
def cat2(uid): return "Both outcomes" if uid in both else "Abandonment only" if uid in ao else ("Mortality only" if uid in do_ else "Other")
gdf["_c2"]=gdf["unit_id"].map(cat2)
COL2={"Both outcomes":"#6a0dad","Abandonment only":"#1f77b4","Mortality only":"#c44e00","Other":"#ededed"}
BASE.plot(ax=ax, color="#eeeeee", edgecolor="#dcdcdc", lw=0.15); BASE.boundary.plot(ax=ax, color="#b8b8b8", lw=0.3)
for c in ["Other","Abandonment only","Mortality only","Both outcomes"]:
    s=gdf[gdf["_c2"]==c]
    if len(s): s.plot(ax=ax, color=COL2[c], edgecolor="white", lw=0.05)
ax.legend(handles=[mpatches.Patch(color=COL2[c],label=f"{c} (n={(gdf['_c2']==c).sum()})")
          for c in ["Both outcomes","Abandonment only","Mortality only"]], loc="lower left", fontsize=9)
ax.set_title(f"Abandonment vs mortality hotspots — the two outcome lenses largely diverge (Jaccard {jac(HS_aband,HS_death):.2f})",
             fontsize=12, fontweight="bold")
ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
plt.tight_layout(); plt.savefig("/tmp/fig_aband_vs_death.png", dpi=140, bbox_inches="tight"); plt.close()
print("Saved fig_aband_vs_death.png")
print("Done.")
