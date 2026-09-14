"""Three analyses combined:
  (1) Population-weighted SP baseline for favela residence
  (2) Age + sex + year-adjusted comparison of favela & poverty (incarcerated vs non)
  (3) Municipality-level map for all 27,608 ever-incarcerated persons
"""
from pathlib import Path
import pandas as pd
import numpy as np

# ----- File paths -----
BASE  = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data")
INC   = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/community_cep_for_incarcerated.parquet")
INCOME = BASE / "cep_income_linkage.csv"
COHORT = BASE / "cohort_with_spatial.csv"
B1     = BASE / "SP_Agregados_2010" / "Basico_SP1.csv"
B2     = BASE / "SP_Agregados_2010" / "Basico_SP2.csv"
ADDR   = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/.shortcut-targets-by-id/1WMps9BoKmDA6_Lzak12042gQKkXVI4qg/WHO modelling Project/Data/TBWeb_20250328_endereco.xlsx")

# ============================================================
# (1) Population-weighted SP baseline favela rate
# ============================================================
print("=== (1) Population-weighted SP baseline ===")
basico = pd.concat([
    pd.read_csv(B1, sep=";", encoding="latin1", dtype=str, usecols=["Cod_setor","Nome_do_municipio","V005"]),
    pd.read_csv(B2, sep=";", encoding="latin1", dtype=str, usecols=["Cod_setor","Nome_do_municipio","V005"]),
])
basico["pop"] = pd.to_numeric(basico["V005"].str.replace(",","."), errors="coerce").fillna(0)
basico["CD_SETOR"] = basico["Cod_setor"].astype(str).str.strip()
print(f"  basico rows: {len(basico):,}, total SP pop: {basico['pop'].sum():,.0f}")
print(f"  unique setors: {basico['CD_SETOR'].nunique():,}")

# Setor-level favela flag from cep_income_linkage (majority over CEPs in that setor)
inclinkage = pd.read_csv(INCOME, dtype={"cep":str, "CD_SETOR":str})
inclinkage["CD_SETOR"] = inclinkage["CD_SETOR"].astype(str).str.replace(r"\.0$","",regex=True).str.strip()
inclinkage["lives_in_favela"]      = pd.to_numeric(inclinkage["lives_in_favela"], errors="coerce")
inclinkage["lives_in_favela_2010"] = pd.to_numeric(inclinkage["lives_in_favela_2010"], errors="coerce")
inclinkage["income_V005"]          = pd.to_numeric(inclinkage["income_V005"], errors="coerce")

setor_fav = (inclinkage.dropna(subset=["CD_SETOR"]).groupby("CD_SETOR")
                       .agg(fav22=("lives_in_favela","mean"),
                            fav10=("lives_in_favela_2010","mean"),
                            inc=("income_V005","mean"))
                       .reset_index())
setor_fav["fav22_bin"] = (setor_fav["fav22"]>=0.5).astype(int)
setor_fav["fav10_bin"] = (setor_fav["fav10"]>=0.5).astype(int)
sp = basico.merge(setor_fav, on="CD_SETOR", how="left")
matched = sp["fav22_bin"].notna().sum()
print(f"  setors matched to favela flag: {matched:,} / {len(sp):,} ({matched/len(sp)*100:.1f}%)")

tot_pop  = sp["pop"].sum()
fav_pop22 = sp.loc[sp["fav22_bin"]==1,"pop"].sum()
fav_pop10 = sp.loc[sp["fav10_bin"]==1,"pop"].sum()
print(f"\n  SP total pop (V005): {tot_pop:,.0f}")
print(f"  Pop in favela setors (2022 polygons): {fav_pop22:,.0f} ({fav_pop22/tot_pop*100:.2f}%)")
print(f"  Pop in favela setors (2010 polygons): {fav_pop10:,.0f} ({fav_pop10/tot_pop*100:.2f}%)")

# Population-weighted median income (via setor median income aggregation)
sp["inc_x_pop"] = sp["inc"] * sp["pop"]
pop_weighted_mean_inc = sp["inc_x_pop"].sum() / sp.loc[sp["inc"].notna(),"pop"].sum()
print(f"  SP pop-weighted mean V005-income (R$/mo): R${pop_weighted_mean_inc:.0f}")

# Save population-weighted SP baseline
SP_BASELINE = {"favela_2022_pct": fav_pop22/tot_pop*100,
               "favela_2010_pct": fav_pop10/tot_pop*100,
               "mean_income_pop_weighted": pop_weighted_mean_inc}

# ============================================================
# (2) Age + sex + year-adjusted comparison
# ============================================================
print("\n=== (2) Age + sex + year-adjusted comparison ===")
# Build per-person feature frame
co = pd.read_csv(COHORT, dtype=str, low_memory=False,
                 usecols=["sinan_clean","tx_seq","notification_date","address_type","cep","age_tb","sex"])
co["tx_seq_i"] = pd.to_numeric(co["tx_seq"], errors="coerce")
co["notif_dt"] = pd.to_datetime(co["notification_date"], errors="coerce")
co["year"]     = co["notif_dt"].dt.year
co["age_n"]    = pd.to_numeric(co["age_tb"], errors="coerce")
co["age_grp"]  = pd.cut(co["age_n"], bins=[0,24,44,64,200], labels=["15-24","25-44","45-64","65+"], include_lowest=True).astype(str)
co["sex_n"]    = co["sex"].str.strip().str.upper().map(lambda s: "M" if s=="M" or s=="MASCULINO" else ("F" if s in ("F","FEMININO") else "U"))

ever_inc_persons = set(co.loc[co["address_type"]=="DETENTO","sinan_clean"].unique())

# Inc: take the persons with valid community CEP (the 1,103)
inc_lookup = pd.read_parquet(INC)
inc_lookup = inc_lookup[inc_lookup["cep_source"].isin(["ENDERECO PADRAO","SEM RESIDENCIA FIXA"])].copy()
inc_lookup["sinan_clean"] = inc_lookup["sinan_clean"].astype(str)
# For each, find their FIRST community-episode row in cohort to get age/sex/year at that point
first_row = (co[co["sinan_clean"].isin(inc_lookup["sinan_clean"]) & (co["address_type"]!="DETENTO")]
              .sort_values(["sinan_clean","notif_dt","tx_seq_i"])
              .drop_duplicates("sinan_clean", keep="first"))
a = first_row.merge(inc_lookup[["sinan_clean","community_cep"]], on="sinan_clean", how="left")
a["cep"] = a["community_cep"].astype(str).str.zfill(8)

# Non-inc: one row per person, use first record
co_first = (co.sort_values(["sinan_clean","notif_dt","tx_seq_i"])
              .drop_duplicates("sinan_clean", keep="first"))
b = co_first[~co_first["sinan_clean"].isin(ever_inc_persons)].copy()
b["cep"] = b["cep"].astype(str).str.zfill(8)

# Join both with CEP-level favela & income
geo_cols = ["cep","lives_in_favela","lives_in_favela_2010","income_V005","income_quartile"]
a = a.merge(inclinkage[geo_cols], on="cep", how="left")
b = b.merge(inclinkage[geo_cols], on="cep", how="left")
print(f"  A (incarcerated, community CEP):       {len(a):,}, with favela flag {a['lives_in_favela'].notna().sum():,}")
print(f"  B (non-incarcerated TB):               {len(b):,}, with favela flag {b['lives_in_favela'].notna().sum():,}")

# Crude rates
print(f"\n  Crude % in favela (2010 polygons):")
print(f"    A: {pd.to_numeric(a['lives_in_favela_2010'],errors='coerce').mean()*100:.2f}%")
print(f"    B: {pd.to_numeric(b['lives_in_favela_2010'],errors='coerce').mean()*100:.2f}%")

# Demographics: how different are the cohorts?
def demo(df, name):
    print(f"\n  {name} demographics:")
    print(f"    sex: {df['sex_n'].value_counts(normalize=True).head(3).to_dict()}")
    print(f"    age_grp: {df['age_grp'].value_counts(normalize=True).sort_index().to_dict()}")
    yr = df['year'].dropna()
    print(f"    year median {yr.median():.0f}, IQR {yr.quantile(.25):.0f}-{yr.quantile(.75):.0f}")
demo(a, "A (incarcerated, community CEP)")
demo(b, "B (non-incarcerated TB)")

# Logistic regression: favela ~ ever_incarcerated + age_grp + sex + year
import statsmodels.api as sm
df = pd.concat([a.assign(group=1), b.assign(group=0)], ignore_index=True)
df["favela10"] = pd.to_numeric(df["lives_in_favela_2010"], errors="coerce")
fit_data = df.dropna(subset=["favela10","age_grp","sex_n","year","group"]).copy()
fit_data = fit_data[fit_data["sex_n"].isin(["M","F"])]
fit_data["age_grp"] = fit_data["age_grp"].astype("category")
fit_data["sex_n"]   = fit_data["sex_n"].astype("category")
print(f"\n  Logistic regression sample: {len(fit_data):,} (A={int(fit_data['group'].sum()):,}, B={int((fit_data['group']==0).sum()):,})")
fit_data["year_c"] = fit_data["year"] - 2013
import patsy
y, X = patsy.dmatrices("favela10 ~ group + C(age_grp) + C(sex_n) + year_c", fit_data, return_type="dataframe")
mod = sm.Logit(y, X).fit(disp=False)
print("\n  Logit (favela2010 ~ incarcerated + age_grp + sex + year_centered):")
res = mod.summary2().tables[1]
print(res.round(4).to_string())

# OR for incarceration
or_grp = np.exp(mod.params["group"])
or_grp_lo, or_grp_hi = np.exp(mod.conf_int().loc["group"])
print(f"\n  Adjusted OR for ever_incarcerated (favela vs not): {or_grp:.2f}  (95% CI {or_grp_lo:.2f}-{or_grp_hi:.2f}, p={mod.pvalues['group']:.3g})")

# Also: linear regression on log-income
fit_inc = df.dropna(subset=["income_V005","age_grp","sex_n","year","group"]).copy()
fit_inc = fit_inc[fit_inc["sex_n"].isin(["M","F"])]
fit_inc["log_inc"] = np.log(pd.to_numeric(fit_inc["income_V005"], errors="coerce"))
fit_inc["age_grp"] = fit_inc["age_grp"].astype("category")
fit_inc["sex_n"]   = fit_inc["sex_n"].astype("category")
fit_inc["year_c"]  = fit_inc["year"] - 2013
y2, X2 = patsy.dmatrices("log_inc ~ group + C(age_grp) + C(sex_n) + year_c", fit_inc, return_type="dataframe")
mod2 = sm.OLS(y2, X2).fit()
print("\n  Linear (log_income ~ incarcerated + age_grp + sex + year):")
res2 = mod2.summary2().tables[1]
print(res2.round(4).to_string())
print(f"\n  Adjusted income ratio (incarcerated vs non, exp(beta)): {np.exp(mod2.params['group']):.3f}  (i.e. {(np.exp(mod2.params['group'])-1)*100:+.1f}%)")

# ============================================================
# (3) Municipality-level map for ALL 27,608 ever-incarcerated
# ============================================================
print("\n=== (3) Municipality-level full-sample map for ever-incarcerated ===")
print("Loading endereco file...")
def clean_cep(s):
    if s is None or pd.isna(s): return pd.NA
    s = str(s).strip().replace("-","").replace(".","").replace(" ","")
    if s in {"","nan","NaN","NAN","None","NONE","0","00000000"}: return pd.NA
    if not s.isdigit(): return pd.NA
    s = s.zfill(8)
    return s if len(s)==8 else pd.NA
addr = pd.read_excel(ADDR, sheet_name="Exportacao_TBWeb_20250328",
                    usecols=["SINAN","tipoEnd","cep","munResid","munNotif","bairro"], dtype=str)
addr["sinan_padded"] = addr["SINAN"].astype(str).str.strip().str.zfill(7)
addr["cep_c"] = addr["cep"].map(clean_cep)

ever_inc_padded = set(co.loc[co["address_type"]=="DETENTO","sinan_clean"].unique())
addr_inc = addr[addr["sinan_padded"].isin(ever_inc_padded)].copy()
print(f"  addr rows for ever-incarcerated persons: {len(addr_inc):,}")

# Best-available origin municipality per person:
#   priority 1 — munResid from any ENDERECO PADRAO row (true home muni)
#   priority 2 — munResid from any SEM RES row
#   priority 3 — munNotif from a DETENTO row (= prison location, used as low-res proxy)
addr_inc["rank"] = addr_inc["tipoEnd"].map({"ENDERECO PADRAO":0,"SEM RESIDENCIA FIXA":1,"DETENTO":2}).fillna(9).astype(int)
addr_inc = addr_inc.sort_values(["sinan_padded","rank"])

# For non-DETENTO rows, use munResid; for DETENTO, use munNotif
addr_inc["origin_mun"] = np.where(addr_inc["tipoEnd"]=="DETENTO", addr_inc["munNotif"], addr_inc["munResid"])
best_origin = addr_inc.dropna(subset=["origin_mun"]).drop_duplicates("sinan_padded", keep="first")
print(f"  persons with origin municipality recovered: {len(best_origin):,} / {len(ever_inc_padded):,}")
print(f"  source breakdown of origin municipality:")
print(best_origin["tipoEnd"].value_counts().to_string())

# Top 25 origin municipalities
top = best_origin["origin_mun"].value_counts().head(25)
print("\n  Top 25 origin municipalities for ever-incarcerated TB cases:")
for mun, n in top.items():
    print(f"    {mun:30s}  {n:>5,d}")

# Compare to SP-wide population (Basico)
mun_pop = basico.groupby("Nome_do_municipio")["pop"].sum().reset_index().rename(columns={"Nome_do_municipio":"mun"})
# Normalize names: upper, strip accents
import unicodedata
def norm_mun(s):
    if s is None or pd.isna(s): return ""
    s = str(s).strip().upper().replace('"','')
    s = unicodedata.normalize("NFKD", s).encode("ASCII","ignore").decode("ASCII")
    return s
mun_pop["mun_n"] = mun_pop["mun"].map(norm_mun)
best_origin["mun_n"] = best_origin["origin_mun"].map(norm_mun)

mun_inc = best_origin.groupby("mun_n").size().reset_index(name="n_inc")
mun_merged = mun_inc.merge(mun_pop, on="mun_n", how="left")
mun_merged["rate_per_100k"] = mun_merged["n_inc"] / mun_merged["pop"] * 1e5

# Cleanest signal: top munis by incarcerated TB cases AND by rate per 100k
print("\n  Top 15 municipalities by N incarcerated TB cases (filed at prison):")
print(mun_merged.sort_values("n_inc", ascending=False).head(15)[["mun_n","n_inc","pop","rate_per_100k"]].to_string(index=False))

print("\n  Top 15 municipalities by rate per 100k pop (min 30 cases for stability):")
sigp = mun_merged[mun_merged["n_inc"]>=30].sort_values("rate_per_100k", ascending=False).head(15)
print(sigp[["mun_n","n_inc","pop","rate_per_100k"]].to_string(index=False))

# Save municipality-level table
OUT = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/incarcerated_origin_by_municipality.parquet")
mun_merged.to_parquet(OUT, index=False)
print(f"\nSaved → {OUT}")

print("\n=== SUMMARY ===")
print(f"  SP population-weighted favela rate (2010 polygons): {SP_BASELINE['favela_2010_pct']:.2f}%")
print(f"  SP population-weighted favela rate (2022 polygons): {SP_BASELINE['favela_2022_pct']:.2f}%")
print(f"  Adjusted OR (favela | ever_incarcerated, ages+sex+year): {or_grp:.2f} (95% CI {or_grp_lo:.2f}-{or_grp_hi:.2f}, p={mod.pvalues['group']:.3g})")
print(f"  Adjusted income ratio: {np.exp(mod2.params['group']):.3f}  (incarcerated vs non, log scale)")
