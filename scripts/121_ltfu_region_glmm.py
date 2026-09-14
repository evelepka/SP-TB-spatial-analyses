"""Independent place effect on LTFU (ADR-0005 companion).

Builds the individual-level dataset (same episode filter as the paper), fits three nested
logistic mixed models in R/lme4 (random region intercept), and persists the summary:
  m0: age bands only
  m1: + sex, alcohol, drug use, tobacco, diabetes, HIV, period   <- the primary "place effect"
  m2: + treatment administration (DOT)  [indication/mediator caveat -- see Methods]
Outputs: /tmp/ltfu_glmm_data.csv, /tmp/ltfu_region_blups.csv,
         Data/analytic/ltfu_glmm_summary.json  (pinned by test/check_artifact_pins.py)
Requires: Rscript + lme4. Runtime ~4 min.
"""
import pandas as pd, numpy as np, subprocess, json, os, sys

SP = ("/DATA_ROOT/Data")
cols = ['sinan_clean','age_tb','notification_date','case_type','case_outcome','address_type',
        'sex_std','alcoholism','drug_use','tobacco_use','hiv','diabetes','tx_administration_type']
M = pd.read_csv(f"{SP}/cohort_with_spatial.csv", usecols=cols, low_memory=False, dtype={'sinan_clean':str})
M['year'] = pd.to_datetime(M['notification_date'], errors='coerce').dt.year
epi = M[(M['age_tb']>=15) & M['year'].between(2013,2024) & (M['address_type']=='ENDERECO PADRAO')
        & M['case_type'].isin(['Novo','Recidiva'])].drop_duplicates(['sinan_clean','case_type','year'])
rc = pd.read_csv('/tmp/region_cases.csv', dtype={'sinan_clean':str}, low_memory=False)
d = rc[rc['eval']==1].merge(epi.drop_duplicates(['sinan_clean','year']), on=['sinan_clean','year'], how='inner')
EDGES=[15,20,25,30,40,50,60,70,200]
d['ageband'] = pd.cut(d['age'], EDGES, right=False).astype(str)
d['period']  = pd.cut(d['year'], [2012,2015,2018,2021,2024], labels=['13-15','16-18','19-21','22-24']).astype(str)
d['dot']  = d['tx_administration_type'].map({'Supervisionado':'DOT','Auto-Administrado':'self'}).fillna('missing')
d['hivc'] = d['hiv'].map({'Pos':'pos','Neg':'neg'}).fillna('unknown')
for v in ['alcoholism','drug_use','tobacco_use','diabetes']:
    d[v] = (d[v]=='S').astype(int)
out = d[['aband','region_id','ageband','sex_std','alcoholism','drug_use','tobacco_use',
         'diabetes','hivc','dot','period']].dropna(subset=['sex_std'])
out.to_csv('/tmp/ltfu_glmm_data.csv', index=False)
print(f"dataset: {len(out):,} evaluated episodes | LTFU {out['aband'].mean()*100:.1f}% | {out['region_id'].nunique():,} regions")

r = subprocess.run(['Rscript', os.path.join(os.path.dirname(__file__), '121_ltfu_region_glmm.R')],
                   capture_output=True, text=True)
sys.stdout.write(r.stdout)
if r.returncode != 0:
    sys.stderr.write(r.stderr); sys.exit(1)

# parse the R output block and persist as data, not prose
summ = {}
for line in r.stdout.splitlines():
    if line.startswith(('m0','m1','m2')):
        k = line.split(':')[0].split()[0]
        summ[k] = {p.split('=')[0]: float(p.split('=')[1]) for p in line.split(':')[1].split()}
summ['n_episodes'] = len(out); summ['n_regions'] = int(out['region_id'].nunique())
AN = f"{SP}/analytic"
json.dump(summ, open(f"{AN}/ltfu_glmm_summary.json", 'w'), indent=1)
json.dump(summ, open("/tmp/ltfu_glmm_summary.json", 'w'), indent=1)
print(f"summary -> {AN}/ltfu_glmm_summary.json")
