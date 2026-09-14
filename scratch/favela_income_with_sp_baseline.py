"""Add SP-wide CEP-level baseline to the favela/income comparison."""
from pathlib import Path
import pandas as pd
import numpy as np

INC      = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/community_cep_for_incarcerated.parquet")
INCOME   = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/cep_income_linkage.csv")
COHORT   = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/cohort_with_spatial.csv")

inc_all = pd.read_parquet(INC)
inc = inc_all[inc_all["cep_source"].isin(["ENDERECO PADRAO","SEM RESIDENCIA FIXA"])].copy()
inc["cep"] = inc["community_cep"].astype(str).str.zfill(8)

income = pd.read_csv(INCOME, dtype={"cep":str})
income["cep"] = income["cep"].astype(str).str.zfill(8)
income["lives_in_favela"] = pd.to_numeric(income["lives_in_favela"], errors="coerce")
income["lives_in_favela_2010"] = pd.to_numeric(income["lives_in_favela_2010"], errors="coerce")
income["income_V005"] = pd.to_numeric(income["income_V005"], errors="coerce")

# (A) Incarcerated with community CEP
a = inc.merge(income[["cep","lives_in_favela","lives_in_favela_2010","favela_tier","income_V005","income_quartile","NM_MUN"]], on="cep", how="left")

# (B) Non-incarcerated TB cohort
co = pd.read_csv(COHORT, dtype=str, low_memory=False, usecols=["sinan_clean","address_type","cep"])
ever_inc_persons = set(co.loc[co["address_type"]=="DETENTO","sinan_clean"].unique())
non_inc = co[~co["sinan_clean"].isin(ever_inc_persons)].drop_duplicates("sinan_clean")
non_inc["cep"] = non_inc["cep"].astype(str).str.zfill(8)
b = non_inc.merge(income[["cep","lives_in_favela","lives_in_favela_2010","favela_tier","income_V005","income_quartile"]], on="cep", how="left")

# (S) SP-wide CEP baseline (one row per CEP — geographic baseline; not population-weighted but covers all populated SP CEPs in the linkage)
s = income.copy()

def summarize(name, df):
    fav = df["lives_in_favela"].dropna()
    fav10 = df["lives_in_favela_2010"].dropna()
    inc_v = df["income_V005"].dropna()
    qd = df["income_quartile"].value_counts(normalize=True).sort_index() * 100
    print(f"\n--- {name} ---")
    print(f"  n CEPs (joined):                 {df['lives_in_favela'].notna().sum():,}")
    print(f"  % in favela (2022 polygons):     {fav.mean()*100:.2f}%   ({int(fav.sum()):,}/{len(fav):,})")
    print(f"  % in favela (2010 polygons):     {fav10.mean()*100:.2f}%   ({int(fav10.sum()):,}/{len(fav10):,})")
    print(f"  median V005 household income:    R${inc_v.median():.0f}   (mean R${inc_v.mean():.0f}, n={len(inc_v):,})")
    print(f"  income quartile distribution (%):  Q1={qd.get('Q1 (Poorest)',0):.1f}  Q2={qd.get('Q2',0):.1f}  Q3={qd.get('Q3',0):.1f}  Q4={qd.get('Q4 (Wealthiest)',0):.1f}")
    return df

summarize("(A) Ever-incarcerated, community-episode CEP (n=1,103)", a)
summarize("(B) Non-incarcerated TB cohort, single cep (n=208,021)", b)
summarize("(S) All SP geocoded CEPs — geographic baseline (one row per CEP, unweighted)", s)

print("\n=== Side-by-side ===")
def row(name, df, weight=None):
    f = pd.to_numeric(df["lives_in_favela"], errors="coerce").dropna()
    f10 = pd.to_numeric(df["lives_in_favela_2010"], errors="coerce").dropna()
    inv = pd.to_numeric(df["income_V005"], errors="coerce").dropna()
    return f"  {name:55s} n={len(f):>7,d}  favela2022={f.mean()*100:5.2f}%  favela2010={f10.mean()*100:5.2f}%  medianInc=R${inv.median():>5.0f}"

print(row("(A) Ever-incarcerated, community CEP", a))
print(row("(B) Non-incarcerated TB cohort",       b))
print(row("(S) SP CEPs (geo baseline, unweighted)", s))

# Also: ratios
def rate(df, col):
    v = pd.to_numeric(df[col], errors="coerce").dropna()
    return v.mean()

print("\n=== Favela & poverty ratios ===")
for col in ["lives_in_favela","lives_in_favela_2010"]:
    rA, rB, rS = rate(a, col), rate(b, col), rate(s, col)
    print(f"  {col:25s}   A={rA*100:5.2f}%   B={rB*100:5.2f}%   S={rS*100:5.2f}%   A/S={rA/rS:.2f}×   B/S={rB/rS:.2f}×")

# Income — fraction in Q1 (poorest)
def q1share(df):
    q = df["income_quartile"].value_counts(normalize=True)
    return q.get("Q1 (Poorest)", 0)
print(f"  share in income Q1 (poorest)         A={q1share(a)*100:5.1f}%   B={q1share(b)*100:5.1f}%   S={q1share(s)*100:5.1f}%")

# More restrictive sensitivity: take ONLY persons whose ENDERECO PADRAO row was the source
# (most conservative — explicit community residence)
a_strict = a[a["cep_source"]=="ENDERECO PADRAO"]
print(f"\n=== Strict subset: ever-incarcerated with an ENDERECO PADRAO row CEP only (n={len(a_strict):,}) ===")
print(row("(A-strict)", a_strict))
