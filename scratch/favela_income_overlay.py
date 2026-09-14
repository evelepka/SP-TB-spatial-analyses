"""For the 1,103 community CEPs of ever-incarcerated persons, compare their
favela rates and household income (IBGE V005) against the non-incarcerated TB
cohort."""
from pathlib import Path
import pandas as pd
import numpy as np

INC      = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/community_cep_for_incarcerated.parquet")
INCOME   = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/cep_income_linkage.csv")
COHORT   = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/cohort_with_spatial.csv")

# ----- 1. Load the 1,103 incarcerated-with-community-CEP -----
inc_all = pd.read_parquet(INC)
print(f"All recovered community-CEP rows: {len(inc_all):,}")
print(f"  by cep_source:\n{inc_all['cep_source'].value_counts().to_string()}")
# Drop DETENTO-source CEPs (those were prison addresses, not home)
inc = inc_all[inc_all["cep_source"].isin(["ENDERECO PADRAO","SEM RESIDENCIA FIXA"])].copy()
print(f"\nValid community CEPs (non-DETENTO source): {len(inc):,}")
inc["cep"] = inc["community_cep"].astype(str).str.zfill(8)

# ----- 2. Load income+favela linkage and join -----
income = pd.read_csv(INCOME, dtype={"cep":str})
income["cep"] = income["cep"].astype(str).str.zfill(8)
print(f"income linkage rows (unique CEPs in SP): {len(income):,}")
inc_joined = inc.merge(income[["cep","NM_MUN","lives_in_favela","lives_in_favela_2010","favela_tier","income_V005","income_quartile"]],
                       on="cep", how="left")
n_matched = inc_joined["income_V005"].notna().sum() + inc_joined["lives_in_favela"].notna().sum() - inc_joined[["income_V005","lives_in_favela"]].notna().all(axis=1).sum()  # rough
matched_either = (inc_joined["lives_in_favela"].notna()) | (inc_joined["income_V005"].notna())
print(f"  matched to spatial/income: {matched_either.sum():,} ({matched_either.mean()*100:.1f}%)")
print(f"  matched to income (V005): {inc_joined['income_V005'].notna().sum():,}")
print(f"  matched to favela flag:   {inc_joined['lives_in_favela'].notna().sum():,}")

# ----- 3. Build comparator: non-incarcerated TB cohort -----
print("\nLoading TB cohort to build non-incarcerated comparator...")
co = pd.read_csv(COHORT, dtype=str, low_memory=False, usecols=["sinan_clean","address_type","cep"])
ever_inc_persons = set(co.loc[co["address_type"]=="DETENTO","sinan_clean"].unique())
non_inc = co[~co["sinan_clean"].isin(ever_inc_persons)].drop_duplicates("sinan_clean")
non_inc["cep"] = non_inc["cep"].astype(str).str.zfill(8)
print(f"  non-incarcerated TB persons: {len(non_inc):,}")
non_inc_joined = non_inc.merge(income[["cep","NM_MUN","lives_in_favela","lives_in_favela_2010","favela_tier","income_V005","income_quartile"]],
                                on="cep", how="left")
print(f"  joined to income: {non_inc_joined['income_V005'].notna().sum():,}")

# Also break out: incarcerated comparator (ever-incarcerated, using the SINGLE collapsed cep from cohort_with_spatial)
# Just for reference, not the main comparison
inc_collapsed = co[co["sinan_clean"].isin(ever_inc_persons)].drop_duplicates("sinan_clean")
inc_collapsed["cep"] = inc_collapsed["cep"].astype(str).str.zfill(8)
inc_collapsed_joined = inc_collapsed.merge(income[["cep","lives_in_favela","lives_in_favela_2010","income_V005","income_quartile"]],
                                            on="cep", how="left")

# ----- 4. Compute stats -----
def stats(name, df, favela_col="lives_in_favela", income_col="income_V005", q_col="income_quartile"):
    d = df.copy()
    d[favela_col] = pd.to_numeric(d[favela_col], errors="coerce")
    d[income_col] = pd.to_numeric(d[income_col], errors="coerce")
    print(f"\n--- {name} (n={len(d):,}) ---")
    pop = d[favela_col].notna().sum()
    fav = d[favela_col].sum()
    print(f"  favela coverage (CEPs with flag): {pop:,}/{len(d):,} ({pop/len(d)*100:.1f}%)")
    print(f"  lives in favela:        {int(fav):,} / {pop:,} = {fav/pop*100:.2f}%")
    fav10 = pd.to_numeric(d["lives_in_favela_2010"], errors="coerce")
    pop10 = fav10.notna().sum()
    print(f"  lives in favela (2010): {int(fav10.sum()):,} / {pop10:,} = {fav10.sum()/pop10*100:.2f}%")
    inc_vals = d[income_col].dropna()
    print(f"  median V005 household income (R$/month): {inc_vals.median():.0f}  (mean {inc_vals.mean():.0f}, IQR {inc_vals.quantile(.25):.0f}-{inc_vals.quantile(.75):.0f}, n={len(inc_vals):,})")
    qvc = d[q_col].value_counts(normalize=True, dropna=True).sort_index() * 100
    print(f"  income quartile distribution (%):")
    for k, v in qvc.items():
        print(f"      {k!s:30s} {v:5.1f}%")

stats("(A) Ever-incarcerated persons, COMMUNITY CEP from non-prison TB episode (n=1,103)", inc_joined)
stats("(B) Non-incarcerated TB cohort (single collapsed cep_per_person)", non_inc_joined)
stats("(C) Ever-incarcerated persons, using the COLLAPSED person-level cep from cohort_with_spatial (sanity check; may be home or prison)", inc_collapsed_joined)

# ----- 5. Statistical comparison: A vs B -----
print("\n=== Statistical comparison: ever-incarcerated community CEP (A) vs non-incarcerated TB (B) ===")
def to_num(s): return pd.to_numeric(s, errors="coerce")

# Favela: 2x2 Fisher-style summary
a = inc_joined["lives_in_favela"].pipe(to_num).dropna()
b = non_inc_joined["lives_in_favela"].pipe(to_num).dropna()
print(f"  Favela (2022 polygons):")
print(f"    A: {int(a.sum()):,}/{len(a):,} = {a.mean()*100:.2f}%")
print(f"    B: {int(b.sum()):,}/{len(b):,} = {b.mean()*100:.2f}%")
print(f"    ratio (A/B): {(a.mean()/max(1e-9,b.mean())):.2f}×")

a10 = inc_joined["lives_in_favela_2010"].pipe(to_num).dropna()
b10 = non_inc_joined["lives_in_favela_2010"].pipe(to_num).dropna()
print(f"  Favela (2010 polygons):")
print(f"    A: {int(a10.sum()):,}/{len(a10):,} = {a10.mean()*100:.2f}%")
print(f"    B: {int(b10.sum()):,}/{len(b10):,} = {b10.mean()*100:.2f}%")
print(f"    ratio (A/B): {(a10.mean()/max(1e-9,b10.mean())):.2f}×")

ai = inc_joined["income_V005"].pipe(to_num).dropna()
bi = non_inc_joined["income_V005"].pipe(to_num).dropna()
print(f"  Median V005 income:")
print(f"    A: R${ai.median():.0f}  (n={len(ai):,})")
print(f"    B: R${bi.median():.0f}  (n={len(bi):,})")
print(f"    delta (A-B): R${ai.median()-bi.median():.0f}")

# Optional: chi-squared / Mann-Whitney
try:
    from scipy.stats import fisher_exact, mannwhitneyu
    table = [[int(a.sum()), len(a)-int(a.sum())], [int(b.sum()), len(b)-int(b.sum())]]
    odds, p = fisher_exact(table)
    print(f"  Fisher exact (favela 2022): OR={odds:.2f}, p={p:.2e}")
    table10 = [[int(a10.sum()), len(a10)-int(a10.sum())], [int(b10.sum()), len(b10)-int(b10.sum())]]
    odds10, p10 = fisher_exact(table10)
    print(f"  Fisher exact (favela 2010): OR={odds10:.2f}, p={p10:.2e}")
    u, pmw = mannwhitneyu(ai, bi, alternative="two-sided")
    print(f"  Mann-Whitney U (income):    p={pmw:.2e}  (A {'<' if ai.median()<bi.median() else '>'} B)")
except Exception as e:
    print(f"  scipy unavailable: {e}")

# Save the joined incarcerated table
OUT = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/incarcerated_community_ceps_with_geo.parquet")
inc_joined.to_parquet(OUT, index=False)
print(f"\nSaved → {OUT}")
