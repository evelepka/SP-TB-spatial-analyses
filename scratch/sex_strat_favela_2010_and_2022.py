"""Same three-way comparison (A=ever-incarcerated TB, B=non-inc TB, S=SP general),
stratified by sex, run with BOTH 2010 AGSN polygons and 2022 Favela-e-Comunidade-Urbana polygons.

SP baselines:
  2010: spatial join setor centroids × AGSN 2010 polygons, weighted by V007.
  2022: setores with CD_FCU.notna() flagged as favela; pop-weighted by v0001 in IBGE 2022.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import geopandas as gpd
import statsmodels.api as sm

BASE  = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data")
INC   = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/community_cep_for_incarcerated.parquet")
INCOME = BASE / "cep_income_linkage.csv"
COHORT = BASE / "cohort_with_spatial.csv"
B1     = BASE / "SP_Agregados_2010" / "Basico_SP1.csv"
B2     = BASE / "SP_Agregados_2010" / "Basico_SP2.csv"
SETOR2010 = BASE / "SP_setores_2010" / "35SEE250GC_SIR.shp"
AGSN2010  = BASE / "SP_AGSN_2010"    / "AglomeradosSubnormais2010_Limites.shp"
SETOR2022 = BASE / "SP_setores_2022" / "SP_setores_CD2022.shp"
BASICO2022 = BASE / "SP_Agregados_2022" / "Agregados_por_setores_basico_BR_20250417.csv"

# ----------------------------------------------------------------
# (1) SP population-weighted favela rate — 2010 AGSN polygons
# ----------------------------------------------------------------
print("=== SP baseline (2010 AGSN polygons) ===")
basico10 = pd.concat([
    pd.read_csv(B1, sep=";", encoding="latin1", dtype=str),
    pd.read_csv(B2, sep=";", encoding="latin1", dtype=str),
])
basico10["pop"] = pd.to_numeric(basico10["V007"].str.replace(".","",regex=False).str.replace(",",".",regex=False), errors="coerce").fillna(0)
basico10["CD_SETOR"] = basico10["Cod_setor"].astype(str).str.strip()

setores10 = gpd.read_file(SETOR2010)
agsn10    = gpd.read_file(AGSN2010)
if setores10.crs is None: setores10 = setores10.set_crs("EPSG:4674")
if agsn10.crs is None:    agsn10    = agsn10.set_crs("EPSG:4674")
setores10p = setores10.to_crs("EPSG:31983")
agsn10p    = agsn10.to_crs("EPSG:31983")
setores10p["CD_SETOR"] = setores10p["CD_GEOCODI"].astype(str)
sc10 = gpd.GeoDataFrame(setores10p[["CD_SETOR"]].copy(), geometry=setores10p.geometry.centroid, crs=setores10p.crs)
sj10 = gpd.sjoin(sc10, agsn10p[["geometry"]], how="left", predicate="intersects")
flag10 = sj10.groupby("CD_SETOR")["index_right"].apply(lambda s: int(s.notna().any())).reset_index(name="in_agsn")
sp10 = basico10.merge(flag10, on="CD_SETOR", how="left")
sp10["in_agsn"] = sp10["in_agsn"].fillna(0).astype(int)
SP10_FAV = sp10.loc[sp10["in_agsn"]==1,"pop"].sum() / sp10["pop"].sum()
print(f"  SP pop-weighted favela rate (2010 AGSN): {SP10_FAV*100:.3f}%")

# ----------------------------------------------------------------
# (2) SP population-weighted favela rate — 2022 Favela e Comunidade Urbana
# ----------------------------------------------------------------
print("\n=== SP baseline (2022 Favela e Comunidade Urbana polygons) ===")
basico22 = pd.read_csv(BASICO2022, sep=";", encoding="latin1", dtype=str,
                       usecols=["CD_SETOR","CD_UF","CD_FCU","v0001"])
basico22 = basico22[basico22["CD_UF"]=="35"].copy()
basico22["pop"] = pd.to_numeric(basico22["v0001"].str.replace(".","",regex=False).str.replace(",",".",regex=False), errors="coerce").fillna(0)
basico22["in_fav22"] = (basico22["CD_FCU"].notna() & (basico22["CD_FCU"]!=".")).astype(int)
SP22_FAV = basico22.loc[basico22["in_fav22"]==1,"pop"].sum() / basico22["pop"].sum()
print(f"  SP 2022 setores: {len(basico22):,}, total pop: {basico22['pop'].sum():,.0f}")
print(f"  setores flagged favela (CD_FCU filled): {basico22['in_fav22'].sum():,}")
print(f"  SP pop-weighted favela rate (2022 FCU):   {SP22_FAV*100:.3f}%")

# ----------------------------------------------------------------
# Load cohorts and join geo flags (both 2010 and 2022)
# ----------------------------------------------------------------
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
inclink["lives_in_favela"]      = pd.to_numeric(inclink["lives_in_favela"], errors="coerce")
inclink["lives_in_favela_2010"] = pd.to_numeric(inclink["lives_in_favela_2010"], errors="coerce")
geo = inclink[["cep","lives_in_favela","lives_in_favela_2010"]]
a = a.merge(geo, on="cep", how="left")
b = b.merge(geo, on="cep", how="left")

# ----------------------------------------------------------------
# Stratified analysis: by sex × polygon vintage
# ----------------------------------------------------------------
def or_ci(p1, n1, p0, n0):
    a, bb = int(round(p1*n1)), n1 - int(round(p1*n1))
    c, d  = int(round(p0*n0)), n0 - int(round(p0*n0))
    if min(a,bb,c,d) == 0:
        a,bb,c,d = a+0.5, bb+0.5, c+0.5, d+0.5
    or_ = (a*d) / (bb*c)
    se = (1/a + 1/bb + 1/c + 1/d) ** 0.5
    lo, hi = np.exp(np.log(or_) - 1.96*se), np.exp(np.log(or_) + 1.96*se)
    return or_, lo, hi

def adj_logit(a_df, b_df, fav_col):
    df = pd.concat([a_df.assign(group=1), b_df.assign(group=0)], ignore_index=True)
    df["fav"] = pd.to_numeric(df[fav_col], errors="coerce")
    fit = df.dropna(subset=["fav","age_grp","year"]).copy()
    if fit["group"].sum() < 10:
        return None
    fit["year_c"] = fit["year"] - 2018
    age_d = pd.get_dummies(fit["age_grp"], prefix="age", drop_first=True)
    X = pd.concat([fit[["group","year_c"]], age_d], axis=1).astype(float)
    X = sm.add_constant(X)
    y = fit["fav"].astype(int)
    try:
        m = sm.Logit(y, X).fit(disp=False, maxiter=200, method="bfgs")
        or_ = np.exp(m.params["group"])
        lo, hi = np.exp(m.conf_int().loc["group"])
        return or_, lo, hi, m.pvalues["group"], int(fit["group"].sum()), int((fit["group"]==0).sum())
    except Exception as e:
        return None

def std_rate(df, ref_w, fav_col):
    df = df.copy()
    df["fav"] = pd.to_numeric(df[fav_col], errors="coerce")
    df = df.dropna(subset=["age_grp","fav"])
    rate = df.groupby("age_grp")["fav"].mean()
    common = rate.index.intersection(ref_w.index)
    return (rate.loc[common] * ref_w.loc[common]).sum() / ref_w.loc[common].sum()

def run_sex(sex_label, sex_code, polygon_label, fav_col, SP_FAV):
    print(f"\n────────────────────── {sex_label}, {polygon_label} ──────────────────────")
    if sex_code == "ALL":
        a_s, b_s = a.copy(), b.copy()
    else:
        a_s = a[a["sex_n"]==sex_code].copy()
        b_s = b[b["sex_n"]==sex_code].copy()
    a_s["fav"] = pd.to_numeric(a_s[fav_col], errors="coerce")
    b_s["fav"] = pd.to_numeric(b_s[fav_col], errors="coerce")
    n_a = a_s["fav"].notna().sum()
    n_b = b_s["fav"].notna().sum()
    p_a = a_s["fav"].mean() if n_a > 0 else float("nan")
    p_b = b_s["fav"].mean() if n_b > 0 else float("nan")
    print(f"  A (ever-incarcerated TB, community CEP):  n={n_a:>7,d}   favela {p_a*100:>5.2f}%   ({int(a_s['fav'].sum()):,d})")
    print(f"  B (non-incarcerated TB):                  n={n_b:>7,d}   favela {p_b*100:>5.2f}%   ({int(b_s['fav'].sum()):,d})")
    print(f"  S (SP general {sex_label.lower()} pop):                       favela {SP_FAV*100:>5.2f}%   (pop-weighted)")

    or_AB, lo, hi = or_ci(p_a, n_a, p_b, n_b)
    print(f"  OR A vs B (crude): {or_AB:.2f} ({lo:.2f}-{hi:.2f})")
    or_AS, lo, hi = or_ci(p_a, n_a, SP_FAV, int(2e7))
    print(f"  OR A vs S (crude): {or_AS:.2f} ({lo:.2f}-{hi:.2f})")
    or_BS, lo, hi = or_ci(p_b, n_b, SP_FAV, int(2e7))
    print(f"  OR B vs S (crude): {or_BS:.2f} ({lo:.2f}-{hi:.2f})")

    # Age-adjusted
    res = adj_logit(a_s, b_s, fav_col)
    if res is not None:
        or_, lo, hi, p, n1, n0 = res
        print(f"  Age+year adjusted OR A vs B: {or_:.2f} ({lo:.2f}-{hi:.2f}, p={p:.3g})  [n A={n1}, B={n0}]")

    # Age-standardized
    ref_w = b_s.dropna(subset=["age_grp"]).groupby("age_grp").size() / len(b_s.dropna(subset=["age_grp"]))
    sr_a = std_rate(a_s, ref_w, fav_col)
    sr_b = std_rate(b_s, ref_w, fav_col)
    print(f"  Age-standardized rates (to B's age dist): A={sr_a*100:.2f}%, B={sr_b*100:.2f}%, ratio {sr_a/sr_b:.2f}×")

# 2010 polygons by sex
run_sex("Males",   "M",  "2010 AGSN polygons", "lives_in_favela_2010", SP10_FAV)
run_sex("Females", "F",  "2010 AGSN polygons", "lives_in_favela_2010", SP10_FAV)

# 2022 polygons by sex
run_sex("Males",   "M",  "2022 Favela polygons", "lives_in_favela", SP22_FAV)
run_sex("Females", "F",  "2022 Favela polygons", "lives_in_favela", SP22_FAV)

# Bonus: 2022 polygons all-sex
run_sex("Both sexes", "ALL", "2022 Favela polygons", "lives_in_favela", SP22_FAV)

print(f"\n=== Summary baselines ===")
print(f"  SP pop-weighted favela rate (2010 AGSN):    {SP10_FAV*100:.3f}%")
print(f"  SP pop-weighted favela rate (2022 FCU):     {SP22_FAV*100:.3f}%")
