"""Fixes from v1:
  - Use IBGE V007 (residents in private households) as population, not V005.
  - Do a real spatial join of SP setor centroids against AGSN polygons to get full
    SP coverage (not limited to cohort CEPs).
  - Simpler logistic regression (drop year dummies; use year as linear).
"""
from pathlib import Path
import pandas as pd
import numpy as np
import geopandas as gpd
import unicodedata

BASE  = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data")
INC   = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/community_cep_for_incarcerated.parquet")
INCOME = BASE / "cep_income_linkage.csv"
COHORT = BASE / "cohort_with_spatial.csv"
B1     = BASE / "SP_Agregados_2010" / "Basico_SP1.csv"
B2     = BASE / "SP_Agregados_2010" / "Basico_SP2.csv"
SETOR_SHP = BASE / "SP_setores_2010" / "35SEE250GC_SIR.shp"
AGSN_SHP  = BASE / "SP_AGSN_2010"    / "AglomeradosSubnormais2010_Limites.shp"
ADDR   = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/.shortcut-targets-by-id/1WMps9BoKmDA6_Lzak12042gQKkXVI4qg/WHO modelling Project/Data/TBWeb_20250328_endereco.xlsx")

# ============================================================
# (1) Population-weighted SP baseline via spatial join
# ============================================================
print("=== (1) Population-weighted SP baseline ===")
basico = pd.concat([
    pd.read_csv(B1, sep=";", encoding="latin1", dtype=str),
    pd.read_csv(B2, sep=";", encoding="latin1", dtype=str),
])
# V007 = Moradores em domicílios particulares (residents in private households)
for v in ["V006","V007","V008"]:
    if v in basico.columns:
        x = pd.to_numeric(basico[v].str.replace(",","."), errors="coerce")
        print(f"  {v}: sum={x.sum():,.0f}, median per setor={x.median():.0f}")
basico["pop"] = pd.to_numeric(basico["V007"].str.replace(",","."), errors="coerce").fillna(0)
basico["CD_SETOR"] = basico["Cod_setor"].astype(str).str.strip()
basico["Nome_do_municipio"] = basico["Nome_do_municipio"].str.replace('"','').str.strip()
print(f"  SP state total pop (V007): {basico['pop'].sum():,.0f}")

# Spatial join: setor centroids in AGSN polygon
print("\nLoading setor and AGSN shapefiles...")
setores = gpd.read_file(SETOR_SHP)
agsn    = gpd.read_file(AGSN_SHP)
print(f"  setores: {len(setores):,}, AGSN polygons: {len(agsn):,}")
print(f"  setores CRS: {setores.crs}, AGSN CRS: {agsn.crs}")
if setores.crs is None:
    setores = setores.set_crs("EPSG:4674")  # SIRGAS2000, IBGE default
if agsn.crs is None:
    agsn = agsn.set_crs("EPSG:4674")
if agsn.crs != setores.crs:
    agsn = agsn.to_crs(setores.crs)

# Use centroids of setores (faster than full polygon overlay)
setores["CD_SETOR"] = setores["CD_GEOCODI"].astype(str)
setores["centroid"] = setores.geometry.centroid
sc = gpd.GeoDataFrame(setores[["CD_SETOR"]].copy(), geometry=setores["centroid"], crs=setores.crs)
sj = gpd.sjoin(sc, agsn[["geometry"]], how="left", predicate="intersects")
sj["in_agsn"] = sj["index_right"].notna().astype(int)
agsn_flag = sj.groupby("CD_SETOR")["in_agsn"].max().reset_index()
print(f"  setores flagged AGSN (centroid in AGSN polygon): {agsn_flag['in_agsn'].sum():,} / {len(agsn_flag):,}")

# Join Basico pop with AGSN flag
sp = basico.merge(agsn_flag, on="CD_SETOR", how="left")
sp["in_agsn"] = sp["in_agsn"].fillna(0).astype(int)
total_pop = sp["pop"].sum()
agsn_pop  = sp.loc[sp["in_agsn"]==1,"pop"].sum()
print(f"\n  SP total pop (V007): {total_pop:,.0f}")
print(f"  Pop in AGSN (2010 favela polygons): {agsn_pop:,.0f}  ({agsn_pop/total_pop*100:.2f}%)")

# Income — using cep_income_linkage's setor-level mean income (good enough)
inclink = pd.read_csv(INCOME, dtype={"cep":str,"CD_SETOR":str})
inclink["CD_SETOR"] = inclink["CD_SETOR"].astype(str).str.replace(r"\.0$","",regex=True).str.strip()
inclink["lives_in_favela_2010"] = pd.to_numeric(inclink["lives_in_favela_2010"], errors="coerce")
inclink["income_V005"]          = pd.to_numeric(inclink["income_V005"], errors="coerce")
setor_inc = inclink.groupby("CD_SETOR")["income_V005"].mean().reset_index()
sp = sp.merge(setor_inc, on="CD_SETOR", how="left")
# Population-weighted mean income (only over setors with both pop & income)
sp_inc = sp.dropna(subset=["income_V005"])
pop_wt_inc = (sp_inc["income_V005"]*sp_inc["pop"]).sum() / sp_inc["pop"].sum()
print(f"  SP pop-weighted mean household income: R${pop_wt_inc:.0f}")

SP_BASELINE_AGSN_PCT = agsn_pop / total_pop * 100
SP_BASELINE_INCOME   = pop_wt_inc

# ============================================================
# (2) Age + sex + year-adjusted comparison
# ============================================================
print("\n=== (2) Age + sex + year-adjusted comparison ===")
co = pd.read_csv(COHORT, dtype=str, low_memory=False,
                 usecols=["sinan_clean","tx_seq","notification_date","address_type","cep","age_tb","sex"])
co["tx_seq_i"] = pd.to_numeric(co["tx_seq"], errors="coerce")
co["notif_dt"] = pd.to_datetime(co["notification_date"], errors="coerce")
co["year"]     = co["notif_dt"].dt.year
co["age_n"]    = pd.to_numeric(co["age_tb"], errors="coerce")
co["age_grp"]  = pd.cut(co["age_n"], bins=[0,24,44,64,200], labels=["15-24","25-44","45-64","65+"], include_lowest=True).astype(str)
co["sex_n"]    = co["sex"].str.strip().str.upper().map(lambda s: "M" if s in ("M","MASCULINO") else ("F" if s in ("F","FEMININO") else "U"))
ever_inc = set(co.loc[co["address_type"]=="DETENTO","sinan_clean"].unique())

inc_lookup = pd.read_parquet(INC)
inc_lookup = inc_lookup[inc_lookup["cep_source"].isin(["ENDERECO PADRAO","SEM RESIDENCIA FIXA"])].copy()
inc_lookup["sinan_clean"] = inc_lookup["sinan_clean"].astype(str)

# A: incarcerated, take first non-DETENTO row for demographics, but use community_cep from lookup
first_nondet = (co[co["sinan_clean"].isin(inc_lookup["sinan_clean"]) & (co["address_type"]!="DETENTO")]
                .sort_values(["sinan_clean","notif_dt","tx_seq_i"])
                .drop_duplicates("sinan_clean", keep="first"))
a = first_nondet.merge(inc_lookup[["sinan_clean","community_cep"]], on="sinan_clean", how="left")
a["cep"] = a["community_cep"].astype(str).str.zfill(8)

# B: non-incarcerated, first record
co_first = co.sort_values(["sinan_clean","notif_dt","tx_seq_i"]).drop_duplicates("sinan_clean", keep="first")
b = co_first[~co_first["sinan_clean"].isin(ever_inc)].copy()
b["cep"] = b["cep"].astype(str).str.zfill(8)

geo = inclink[["cep","lives_in_favela_2010","income_V005","income_quartile"]]
a = a.merge(geo, on="cep", how="left")
b = b.merge(geo, on="cep", how="left")

# Restrict to common geo coverage
a["favela10"] = pd.to_numeric(a["lives_in_favela_2010"], errors="coerce")
b["favela10"] = pd.to_numeric(b["lives_in_favela_2010"], errors="coerce")
print(f"  A n={len(a):,}, with favela flag={a['favela10'].notna().sum():,}; crude favela {a['favela10'].mean()*100:.2f}%")
print(f"  B n={len(b):,}, with favela flag={b['favela10'].notna().sum():,}; crude favela {b['favela10'].mean()*100:.2f}%")

# Stratified rates by age × sex
print("\n  Age × sex stratified favela rate (2010):")
df = pd.concat([a.assign(group="A_incarcerated"), b.assign(group="B_non_inc")], ignore_index=True)
df = df[df["sex_n"].isin(["M","F"])]
strat = df.groupby(["group","age_grp","sex_n"]).agg(
    n=("favela10","size"), fav=("favela10","sum"), n_with_flag=("favela10","count")
).reset_index()
strat["pct_favela"] = strat["fav"] / strat["n_with_flag"] * 100
print(strat.pivot(index=["age_grp","sex_n"], columns="group", values="pct_favela").round(2).to_string())

# Direct age-sex standardization to the non-incarcerated TB cohort distribution
ref = b.dropna(subset=["age_grp","sex_n"]).copy()
ref = ref[ref["sex_n"].isin(["M","F"])]
ref_weights = ref.groupby(["age_grp","sex_n"]).size() / len(ref)

def std_rate(df, ref_w):
    df = df.dropna(subset=["age_grp","sex_n","favela10"]).copy()
    df = df[df["sex_n"].isin(["M","F"])]
    rate_by = df.groupby(["age_grp","sex_n"])["favela10"].mean()
    common = rate_by.index.intersection(ref_w.index)
    return (rate_by.loc[common] * ref_w.loc[common]).sum() / ref_w.loc[common].sum()
sr_a = std_rate(a, ref_weights)
sr_b = std_rate(b, ref_weights)
print(f"\n  Age-sex standardized favela rate (2010), standardized to non-inc TB age-sex distribution:")
print(f"    A (incarcerated):     {sr_a*100:.2f}%")
print(f"    B (non-incarcerated): {sr_b*100:.2f}%")
print(f"    standardized ratio A/B: {sr_a/sr_b:.2f}×")

# Logistic regression — simpler: year as numeric linear
import statsmodels.api as sm
fit_df = df.dropna(subset=["favela10","age_grp","sex_n","year"]).copy()
fit_df["group_i"] = (fit_df["group"]=="A_incarcerated").astype(int)
fit_df["year_c"]  = fit_df["year"] - 2018
# One-hot encode age & sex by hand to avoid patsy issues
age_dummies = pd.get_dummies(fit_df["age_grp"], prefix="age", drop_first=True)
sex_dummies = pd.get_dummies(fit_df["sex_n"], prefix="sex", drop_first=True)
X = pd.concat([fit_df[["group_i","year_c"]], age_dummies, sex_dummies], axis=1).astype(float)
X = sm.add_constant(X)
y = fit_df["favela10"].astype(int)
print(f"\n  Logistic regression sample: {len(fit_df):,}  (incarcerated={int(fit_df['group_i'].sum()):,})")
try:
    mod = sm.Logit(y, X).fit(disp=False, maxiter=200, method="bfgs")
    or_ = np.exp(mod.params["group_i"])
    lo, hi = np.exp(mod.conf_int().loc["group_i"])
    p = mod.pvalues["group_i"]
    print(f"  Adjusted OR for ever_incarcerated (favela ~ group + age + sex + year): {or_:.2f} (95% CI {lo:.2f}-{hi:.2f}, p={p:.3g})")
except Exception as e:
    print(f"  Logit failed: {e}; falling back to sklearn")
    from sklearn.linear_model import LogisticRegression
    m = LogisticRegression(max_iter=500, C=1e6).fit(X.drop(columns="const"), y)
    print(f"  sklearn OR for group_i: {np.exp(m.coef_[0][0]):.2f}")

# Linear regression on log income
fit_inc = df.dropna(subset=["income_V005","age_grp","sex_n","year"]).copy()
fit_inc = fit_inc[fit_inc["sex_n"].isin(["M","F"])]
fit_inc["log_inc"] = np.log(pd.to_numeric(fit_inc["income_V005"], errors="coerce"))
fit_inc["group_i"] = (fit_inc["group"]=="A_incarcerated").astype(int)
fit_inc["year_c"]  = fit_inc["year"] - 2018
age_dums = pd.get_dummies(fit_inc["age_grp"], prefix="age", drop_first=True)
sex_dums = pd.get_dummies(fit_inc["sex_n"], prefix="sex", drop_first=True)
X2 = pd.concat([fit_inc[["group_i","year_c"]], age_dums, sex_dums], axis=1).astype(float)
X2 = sm.add_constant(X2)
y2 = fit_inc["log_inc"].astype(float)
m2 = sm.OLS(y2, X2).fit()
coef = m2.params["group_i"]
ci = m2.conf_int().loc["group_i"]
print(f"\n  Adjusted income ratio (incarcerated vs non, exp(beta)): {np.exp(coef):.3f}  (95% CI {np.exp(ci[0]):.3f}-{np.exp(ci[1]):.3f}, p={m2.pvalues['group_i']:.3g})")

# ============================================================
# (3) Municipality-level map for ALL ever-incarcerated
# ============================================================
print("\n=== (3) Municipality-level map ===")
def clean_cep(s):
    if s is None or pd.isna(s): return pd.NA
    s = str(s).strip().replace("-","").replace(".","").replace(" ","")
    if s in {"","nan","NaN","NAN","None","NONE","0","00000000"}: return pd.NA
    if not s.isdigit(): return pd.NA
    s = s.zfill(8)
    return s if len(s)==8 else pd.NA
addr = pd.read_excel(ADDR, sheet_name="Exportacao_TBWeb_20250328",
                     usecols=["SINAN","tipoEnd","cep","munResid","munNotif"], dtype=str)
addr["sinan_padded"] = addr["SINAN"].astype(str).str.strip().str.zfill(7)
addr_inc = addr[addr["sinan_padded"].isin(ever_inc)].copy()
print(f"  endereco rows for ever-incarcerated: {len(addr_inc):,}")

addr_inc["rank"] = addr_inc["tipoEnd"].map({"ENDERECO PADRAO":0,"SEM RESIDENCIA FIXA":1,"DETENTO":2}).fillna(9).astype(int)
addr_inc = addr_inc.sort_values(["sinan_padded","rank"])
addr_inc["origin_mun"] = np.where(addr_inc["tipoEnd"]=="DETENTO", addr_inc["munNotif"], addr_inc["munResid"])
best = addr_inc.dropna(subset=["origin_mun"]).drop_duplicates("sinan_padded", keep="first")
print(f"  persons with origin municipality recovered: {len(best):,} / {len(ever_inc):,}")
print(f"  source breakdown (tipoEnd of the row supplying origin):")
print(best["tipoEnd"].value_counts().to_string())

def norm_mun(s):
    if s is None or pd.isna(s): return ""
    s = str(s).strip().upper().replace('"','')
    s = unicodedata.normalize("NFKD", s).encode("ASCII","ignore").decode("ASCII")
    return s
best["mun_n"] = best["origin_mun"].map(norm_mun)
basico["mun_n"] = basico["Nome_do_municipio"].map(norm_mun)
mun_pop = basico.groupby("mun_n")["pop"].sum().reset_index()
mun_inc_cnt = best.groupby("mun_n").size().reset_index(name="n_inc")
mun = mun_inc_cnt.merge(mun_pop, on="mun_n", how="left")
mun["rate_per_100k"] = mun["n_inc"] / mun["pop"] * 1e5

# Show breakdown by whether origin came from DETENTO row (= prison location) vs not
print("\n  Top 20 origin municipalities by N ever-incarcerated TB cases:")
print(mun.sort_values("n_inc", ascending=False).head(20).to_string(index=False))
print("\n  Top 15 by rate per 100k (min 30 cases):")
print(mun[mun["n_inc"]>=30].sort_values("rate_per_100k", ascending=False).head(15).to_string(index=False))

OUT = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/incarcerated_origin_by_municipality.parquet")
mun.to_parquet(OUT, index=False)

print("\n=== SUMMARY ===")
print(f"  SP population-weighted AGSN (favela) rate: {SP_BASELINE_AGSN_PCT:.2f}%")
print(f"  SP population-weighted mean household income: R${SP_BASELINE_INCOME:.0f}")
print(f"  A (incarcerated, community CEP) crude favela: {a['favela10'].mean()*100:.2f}%")
print(f"  B (non-incarcerated TB) crude favela:         {b['favela10'].mean()*100:.2f}%")
print(f"  Age-sex standardized A favela: {sr_a*100:.2f}%, B: {sr_b*100:.2f}%, ratio {sr_a/sr_b:.2f}×")
