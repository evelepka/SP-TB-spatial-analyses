import pandas as pd
import numpy as np
import statsmodels.formula.api as smf

print("--- 1. Processing 2010 IBGE Demographics (Total State Population by Income Quartile) ---")
# Load the 2010 Setores Censitários Demographic Tables
df_sp1 = pd.read_csv('Data/SP_Agregados_2010/Basico_SP1.csv', sep=';', encoding='latin1', dtype={'Cod_setor': str})
df_sp2 = pd.read_csv('Data/SP_Agregados_2010/Basico_SP2.csv', sep=';', encoding='latin1', dtype={'Cod_setor': str})
df_agregados = pd.concat([df_sp1, df_sp2], ignore_index=True)

# Clean the Income (V005) and Population (V002) fields
if df_agregados['V005'].dtype == object:
    df_agregados['V005'] = df_agregados['V005'].str.replace(',', '.').astype(float)
if df_agregados['V002'].dtype == object:
    df_agregados['V002'] = df_agregados['V002'].astype(float)

# Drop missing income to establish the State-wide Income Quartiles correctly based on Sector Income
df_agregados = df_agregados.dropna(subset=['V005', 'V002'])

# Let's manually get the precise thresholds we established for patients from earlier
# Q1: < 874.24, Q2: 874.24 - 1148.39, Q3: 1148.39 - 1633.03, Q4: > 1633.03
# We will apply these thresholds directly to the State's census tracts to extract the denominator
def assign_quartile(val):
    if pd.isna(val): return "Unknown"
    if val <= 874.24: return "Q1 (Poorest)"
    elif val <= 1148.39: return "Q2"
    elif val <= 1633.03: return "Q3"
    else: return "Q4 (Wealthiest)"

df_agregados['income_quartile'] = df_agregados['V005'].apply(assign_quartile)

print("\n--- BASELINE STATE POPULATION BY TRACT INCOME QUARTILE ---")
pop_by_q = df_agregados.groupby('income_quartile')['V002'].sum()
for q, pop in pop_by_q.items():
    print(f"{q}: {pop:,.0f} residents")

print("\n--- 2. Loading Patient Cohort & Mapping Income ---")
df_cohort = pd.read_csv("Data/cohort_with_spatial.csv", low_memory=False)
df_spatial = pd.read_csv("Data/cep_income_linkage.csv")

# Standardize CEP strings and merge
df_cohort['cep'] = df_cohort['cep'].astype(str).str.split('.').str[0].str.zfill(8)
df_spatial['cep'] = df_spatial['cep'].astype(str).str.split('.').str[0].str.zfill(8)

df_spatial = df_spatial.drop_duplicates(subset=['cep'])
df = df_cohort.merge(df_spatial[['cep', 'income_quartile']], on='cep', how='inner')
print(f"Cohort merged. Total cases mapped strictly to an income quartile: {len(df)}")

print("\n--- 3. TB INCIDENCE BY INCOME QUARTILE ---")
cases_by_q = df['income_quartile'].value_counts()

# We need the scaling factor because we only geocoded a fraction of the cohort
# Total cohort was 220049. Total mapped here is len(df).
scale_factor = 220049 / len(df)

for q in ['Q1 (Poorest)', 'Q2', 'Q3', 'Q4 (Wealthiest)']:
    raw_cases = cases_by_q.get(q, 0)
    scaled_cases = raw_cases * scale_factor
    annual_cases = scaled_cases / 12  # 12-year longitudinal span
    
    pop = pop_by_q.get(q, 0)
    inc = (annual_cases / pop) * 100000 if pop > 0 else 0
    
    print(f"{q}: {int(raw_cases):,} cases -> {inc:.1f} per 100,000 residents/year")


print("\n--- 4. ABANDONMENT RISK BY INCOME QUARTILE ---")
df_outcomes = df[df['case_outcome'].isin(['Cura', 'Abandono'])].copy()
df_outcomes['abandonment'] = np.where(df_outcomes['case_outcome'] == 'Abandono', 1, 0)

# Raw cross-tabs
print("\nRaw Abandonment Rates:")
print(df_outcomes.groupby('income_quartile')['abandonment'].mean().sort_index() * 100)

# Multivariable Regression controlling for confounders
# Baseline Q1 (Poorest) as reference
df_outcomes['income_quartile'] = pd.Categorical(df_outcomes['income_quartile'], categories=['Q1 (Poorest)', 'Q2', 'Q3', 'Q4 (Wealthiest)', 'Unknown'], ordered=True)

model = smf.logit('abandonment ~ C(income_quartile, Treatment(reference="Q1 (Poorest)")) + age_tb + C(sex_std) + C(hiv)', data=df_outcomes)
result = model.fit(disp=0)

# Format outputs
print("\nMULTIVARIABLE LOGISTIC REGRESSION: ABANDONMENT RISK (Ref = Q1 Poorest)")
params = np.exp(result.params)
conf = np.exp(result.conf_int())
conf['OR'] = params
pvalues = result.pvalues

for idx, row in conf.iterrows():
    if "income_quartile" in idx:
        print(f"{idx}: OR={row['OR']:.3f} (95% CI: {row[0]:.3f}-{row[1]:.3f}), p={pvalues[idx]:.3f}")

print("\nAnalysis Complete.")
