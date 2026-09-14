"""Males-only three-way comparison of favela residence:
  A. Ever-incarcerated TB males, community CEP from non-prison episode
  B. Non-incarcerated TB males
  S. SP general male population (population-weighted, from IBGE setor counts + AGSN polygons)

Note: For the SP baseline, we assume sex distribution is approximately uniform across
setores (favela ratio for males ≈ overall favela ratio of 2.91% × small adjustment).
We use V007 (all residents) divided by 2 as a male population proxy. Sensitivity:
if favela setores have a higher male share (often true: younger pop), the SP-male
baseline would be slightly higher than the overall 2.91%.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import geopandas as gpd

BASE  = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data")
INC   = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/community_cep_for_incarcerated.parquet")
INCOME = BASE / "cep_income_linkage.csv"
COHORT = BASE / "cohort_with_spatial.csv"
B1     = BASE / "SP_Agregados_2010" / "Basico_SP1.csv"
B2     = BASE / "SP_Agregados_2010" / "Basico_SP2.csv"
SETOR_SHP = BASE / "SP_setores_2010" / "35SEE250GC_SIR.shp"
AGSN_SHP  = BASE / "SP_AGSN_2010"    / "AglomeradosSubnormais2010_Limites.shp"

# ----- SP baseline (carries over from v2 logic) -----
basico = pd.concat([
    pd.read_csv(B1, sep=";", encoding="latin1", dtype=str),
    pd.read_csv(B2, sep=";", encoding="latin1", dtype=str),
])
basico["pop"] = pd.to_numeric(basico["V007"].str.replace(".","",regex=False).str.replace(",",".",regex=False), errors="coerce").fillna(0)
basico["CD_SETOR"] = basico["Cod_setor"].astype(str).str.strip()

print("Spatial join setor centroids × AGSN polygons...")
setores = gpd.read_file(SETOR_SHP)
agsn    = gpd.read_file(AGSN_SHP)
if setores.crs is None: setores = setores.set_crs("EPSG:4674")
if agsn.crs is None:    agsn    = agsn.set_crs("EPSG:4674")
# Project to UTM zone 23S for accurate centroid
setores_proj = setores.to_crs("EPSG:31983")
agsn_proj    = agsn.to_crs("EPSG:31983")
setores_proj["CD_SETOR"] = setores_proj["CD_GEOCODI"].astype(str)
sc = gpd.GeoDataFrame(setores_proj[["CD_SETOR"]].copy(), geometry=setores_proj.geometry.centroid, crs=setores_proj.crs)
sj = gpd.sjoin(sc, agsn_proj[["geometry"]], how="left", predicate="intersects")
agsn_flag = (sj.groupby("CD_SETOR").apply(lambda d: int(d["index_right"].notna().any()))
                .reset_index(name="in_agsn"))
sp = basico.merge(agsn_flag, on="CD_SETOR", how="left")
sp["in_agsn"] = sp["in_agsn"].fillna(0).astype(int)
tot = sp["pop"].sum()
ag  = sp.loc[sp["in_agsn"]==1,"pop"].sum()
SP_FAV_PCT = ag/tot*100
SP_FAV_PROP = ag/tot
print(f"SP population-weighted favela rate (both sexes): {SP_FAV_PCT:.3f}%  ({ag:,.0f} / {tot:,.0f})")
# For males, assume similar (≈ all-sex rate). Document caveat at end.
SP_MALE_FAV_PROP = SP_FAV_PROP  # approximate; favela slightly higher male share so this is a slight underestimate

# ----- Cohorts -----
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

first_nondet = (co[co["sinan_clean"].isin(inc_lookup["sinan_clean"]) & (co["address_type"]!="DETENTO")]
                .sort_values(["sinan_clean","notif_dt","tx_seq_i"])
                .drop_duplicates("sinan_clean", keep="first"))
a = first_nondet.merge(inc_lookup[["sinan_clean","community_cep"]], on="sinan_clean", how="left")
a["cep"] = a["community_cep"].astype(str).str.zfill(8)

co_first = co.sort_values(["sinan_clean","notif_dt","tx_seq_i"]).drop_duplicates("sinan_clean", keep="first")
b = co_first[~co_first["sinan_clean"].isin(ever_inc)].copy()
b["cep"] = b["cep"].astype(str).str.zfill(8)

inclink = pd.read_csv(INCOME, dtype={"cep":str})
inclink["cep"] = inclink["cep"].astype(str).str.zfill(8)
inclink["lives_in_favela_2010"] = pd.to_numeric(inclink["lives_in_favela_2010"], errors="coerce")
inclink["income_V005"]          = pd.to_numeric(inclink["income_V005"], errors="coerce")
geo = inclink[["cep","lives_in_favela_2010","income_V005"]]
a = a.merge(geo, on="cep", how="left")
b = b.merge(geo, on="cep", how="left")

# Restrict to males
a_m = a[a["sex_n"]=="M"].copy()
b_m = b[b["sex_n"]=="M"].copy()
a_m["fav"] = pd.to_numeric(a_m["lives_in_favela_2010"], errors="coerce")
b_m["fav"] = pd.to_numeric(b_m["lives_in_favela_2010"], errors="coerce")
print(f"\nMales only:")
print(f"  A (ever-incarcerated TB males, community CEP): n={len(a_m):,}, with favela flag={a_m['fav'].notna().sum():,}")
print(f"  B (non-incarcerated TB males):                  n={len(b_m):,}, with favela flag={b_m['fav'].notna().sum():,}")

p_a = a_m["fav"].mean()
p_b = b_m["fav"].mean()
n_a = a_m["fav"].notna().sum()
n_b = b_m["fav"].notna().sum()
print(f"\n=== Crude % living in favela (2010 AGSN polygons) ===")
print(f"  A (ever-incarcerated TB males):  {p_a*100:.2f}%   ({int(a_m['fav'].sum()):,} / {n_a:,})")
print(f"  B (non-incarcerated TB males):    {p_b*100:.2f}%   ({int(b_m['fav'].sum()):,} / {n_b:,})")
print(f"  S (SP general male population):   {SP_MALE_FAV_PROP*100:.2f}%   (population-weighted, sex-neutral baseline)")

# Pairwise ORs with 95% CI (Wald)
def or_ci_2x2(p1, n1, p0, n0):
    # 2x2: fav-yes, fav-no
    a, b = int(round(p1*n1)), n1 - int(round(p1*n1))
    c, d = int(round(p0*n0)), n0 - int(round(p0*n0))
    if min(a,b,c,d) == 0:
        a,b,c,d = a+0.5, b+0.5, c+0.5, d+0.5
    or_ = (a*d) / (b*c)
    se = (1/a + 1/b + 1/c + 1/d) ** 0.5
    lo, hi = np.exp(np.log(or_) - 1.96*se), np.exp(np.log(or_) + 1.96*se)
    return or_, lo, hi

print(f"\n=== Pairwise ORs (Wald 95% CI), males only ===")
# A vs B
or_AB, lo, hi = or_ci_2x2(p_a, n_a, p_b, n_b)
print(f"  A vs B (incarcerated vs non-inc, both TB males): OR={or_AB:.2f} (95% CI {lo:.2f}-{hi:.2f})")
# A vs S
or_AS, lo, hi = or_ci_2x2(p_a, n_a, SP_MALE_FAV_PROP, int(tot/2))  # treat SP-male as ~half of pop
print(f"  A vs S (incarcerated TB males vs SP general male pop): OR={or_AS:.2f} (95% CI {lo:.2f}-{hi:.2f})")
# B vs S
or_BS, lo, hi = or_ci_2x2(p_b, n_b, SP_MALE_FAV_PROP, int(tot/2))
print(f"  B vs S (non-inc TB males vs SP general male pop):       OR={or_BS:.2f} (95% CI {lo:.2f}-{hi:.2f})")

# Age-adjusted OR for A vs B (males only)
import statsmodels.api as sm
print("\n=== Age + year adjusted logistic regression (A vs B, males only) ===")
df = pd.concat([a_m.assign(group=1), b_m.assign(group=0)], ignore_index=True)
df["fav"] = pd.to_numeric(df["lives_in_favela_2010"], errors="coerce")
fit = df.dropna(subset=["fav","age_grp","year"]).copy()
fit["year_c"] = fit["year"] - 2018
age_d = pd.get_dummies(fit["age_grp"], prefix="age", drop_first=True)
X = pd.concat([fit[["group","year_c"]], age_d], axis=1).astype(float)
X = sm.add_constant(X)
y = fit["fav"].astype(int)
m = sm.Logit(y, X).fit(disp=False, maxiter=200, method="bfgs")
or_adj = np.exp(m.params["group"])
lo_adj, hi_adj = np.exp(m.conf_int().loc["group"])
print(f"  Adjusted OR for ever_incarcerated (favela ~ group + age + year, males only): {or_adj:.2f} (95% CI {lo_adj:.2f}-{hi_adj:.2f}, p={m.pvalues['group']:.3g})")

# Age-standardized rate, standardized to B-male age distribution
ref_w = b_m.dropna(subset=["age_grp"]).groupby("age_grp").size() / len(b_m.dropna(subset=["age_grp"]))
def std_rate(df, ref_w):
    df = df.dropna(subset=["age_grp","fav"])
    rate = df.groupby("age_grp")["fav"].mean()
    common = rate.index.intersection(ref_w.index)
    return (rate.loc[common] * ref_w.loc[common]).sum() / ref_w.loc[common].sum()
sr_a = std_rate(a_m, ref_w)
sr_b = std_rate(b_m, ref_w)
print(f"\n  Age-standardized favela rate, standardized to B-male age distribution:")
print(f"    A (incarcerated TB males):    {sr_a*100:.2f}%")
print(f"    B (non-incarcerated TB males): {sr_b*100:.2f}%")

# Income comparison (males only)
print("\n=== Household income (males only) ===")
i_a = pd.to_numeric(a_m["income_V005"], errors="coerce").dropna()
i_b = pd.to_numeric(b_m["income_V005"], errors="coerce").dropna()
print(f"  A median income: R${i_a.median():.0f}  (mean R${i_a.mean():.0f}, n={len(i_a):,})")
print(f"  B median income: R${i_b.median():.0f}  (mean R${i_b.mean():.0f}, n={len(i_b):,})")
print(f"  A < B by R${i_b.median()-i_a.median():.0f}")

# Adjusted log-income regression (males only)
fit_i = df.dropna(subset=["income_V005","age_grp","year"]).copy()
fit_i["log_inc"] = np.log(pd.to_numeric(fit_i["income_V005"], errors="coerce"))
fit_i["year_c"]  = fit_i["year"] - 2018
age_d = pd.get_dummies(fit_i["age_grp"], prefix="age", drop_first=True)
X2 = pd.concat([fit_i[["group","year_c"]], age_d], axis=1).astype(float)
X2 = sm.add_constant(X2)
y2 = fit_i["log_inc"].astype(float)
m2 = sm.OLS(y2, X2).fit()
beta = m2.params["group"]
ci = m2.conf_int().loc["group"]
print(f"  Adjusted income ratio (males, A vs B): {np.exp(beta):.3f}  (95% CI {np.exp(ci[0]):.3f}-{np.exp(ci[1]):.3f}, p={m2.pvalues['group']:.3g})")
print(f"    interpretation: incarcerated TB males live in setores with {(np.exp(beta)-1)*100:+.1f}% income vs non-incarcerated TB males")
