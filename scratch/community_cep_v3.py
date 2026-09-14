"""Correct approach: for each ever-incarcerated person, scan ALL their endereco rows
(across episodes) and pick the best available community CEP.

Match key: cohort.sinan_padded ↔ addr.SINAN (zero-padded to 7 digits).
The endereco file has multiple rows per SINAN for multi-episode patients;
include all of them when searching for a CEP.
"""
from pathlib import Path
import pandas as pd

ADDR   = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/.shortcut-targets-by-id/1WMps9BoKmDA6_Lzak12042gQKkXVI4qg/WHO modelling Project/Data/TBWeb_20250328_endereco.xlsx")
COHORT = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/cohort_with_spatial.csv")

def clean_cep(s):
    if s is None or pd.isna(s): return pd.NA
    s = str(s).strip().replace("-","").replace(".","").replace(" ","")
    if s in {"", "nan", "NaN", "NAN", "None", "NONE", "0", "00000000"}: return pd.NA
    if not s.isdigit(): return pd.NA
    s = s.zfill(8)
    return s if len(s) == 8 else pd.NA

print("Loading endereco file...")
addr = pd.read_excel(
    ADDR, sheet_name="Exportacao_TBWeb_20250328",
    usecols=["SINAN","tipoEnd","cep","ceptrat","munResid","bairro"],
    dtype=str,
)
addr["sinan_padded"] = addr["SINAN"].astype(str).str.strip().str.zfill(7)
addr["cep_clean"]     = addr["cep"].map(clean_cep)
addr["ceptrat_clean"] = addr["ceptrat"].map(clean_cep)
print(f"  addr rows: {len(addr):,}")
print(f"  cep_clean filled: {addr['cep_clean'].notna().sum():,}")

# Identify ever-incarcerated persons (from cohort, addr_type=DETENTO at any row)
print("\nLoading cohort to identify ever-incarcerated persons...")
cohort = pd.read_csv(COHORT, dtype=str, low_memory=False,
                     usecols=["sinan_clean","sinan_padded","tx_seq","notification_date","address_type"])
ever_inc = cohort[cohort["address_type"]=="DETENTO"][["sinan_clean","sinan_padded"]].drop_duplicates()
# A person (sinan_clean) may have multiple sinan_padded? — only if they had identity-conflict re-numbering.
# Practically sinan_padded ≈ sinan_clean.
inc_padded = set(ever_inc["sinan_padded"].unique())
inc_persons = set(ever_inc["sinan_clean"].unique())
print(f"  ever-incarcerated unique sinan_clean: {len(inc_persons):,}")
print(f"  ever-incarcerated unique sinan_padded: {len(inc_padded):,}")

# Scan ALL addr rows belonging to these persons
addr_inc = addr[addr["sinan_padded"].isin(inc_padded)].copy()
print(f"\nAll endereco rows belonging to ever-incarcerated persons: {len(addr_inc):,}")
print(f"  breakdown by tipoEnd:\n{addr_inc['tipoEnd'].value_counts(dropna=False).to_string()}")
print(f"  with cep_clean filled:\n{addr_inc.dropna(subset=['cep_clean']).groupby('tipoEnd', dropna=False).size().to_string()}")

# Best community CEP per person: prefer non-DETENTO rows with cep, then DETENTO rows with cep
rank = {"ENDERECO PADRAO":0, "SEM RESIDENCIA FIXA":1, "DETENTO":2}
addr_inc["rank"] = addr_inc["tipoEnd"].map(rank).fillna(9).astype(int)
addr_with_cep = addr_inc.dropna(subset=["cep_clean"]).sort_values(["sinan_padded","rank"])
best = addr_with_cep.drop_duplicates("sinan_padded", keep="first")
print(f"\n=== Community CEP recovery for ever-incarcerated persons ===")
print(f"  Total ever-incarcerated persons:            {len(inc_padded):,}")
print(f"  Persons with ANY community CEP recovered:   {len(best):,}  ({len(best)/len(inc_padded)*100:.1f}%)")
print(f"  By source of the CEP (tipoEnd of the row that supplied it):")
print(best["tipoEnd"].value_counts().to_string())

# Of the "DETENTO" source ones — these are the cep declared at prison intake (residence)
n_detento_intake = (best["tipoEnd"]=="DETENTO").sum()
n_community_row  = (best["tipoEnd"]=="ENDERECO PADRAO").sum()
n_homeless_row   = (best["tipoEnd"]=="SEM RESIDENCIA FIXA").sum()
print(f"\n  Interpretation:")
print(f"    {n_community_row:,} from a community-episode row (the person had a non-prison TB episode and we use that row's home CEP)")
print(f"    {n_homeless_row:,} from a homeless-episode row")
print(f"    {n_detento_intake:,} from the DETENTO row's own cep field (home address declared at prison intake)")

# Cross-check: how many ever-incarcerated persons have a non-DETENTO addr row at all?
# (these would be multi-episode incarcerated persons)
inc_with_nondetento_row = addr_inc[addr_inc["tipoEnd"]!="DETENTO"]["sinan_padded"].unique()
print(f"\n  Persons with at least one non-DETENTO endereco row (≥1 community/homeless episode): {len(inc_with_nondetento_row):,}")
print(f"    of whom, with a non-DETENTO row that has cep filled:                                {((addr_inc['tipoEnd']!='DETENTO') & (addr_inc['cep_clean'].notna())).groupby(addr_inc['sinan_padded']).any().sum():,}")

# Persons with ZERO usable cep — what's the issue?
no_cep_persons = inc_padded - set(best["sinan_padded"])
print(f"\n  Persons with NO CEP recoverable from any endereco row: {len(no_cep_persons):,}")

# Save the lookup
OUT = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/community_cep_for_incarcerated.parquet")
best[["sinan_padded","cep_clean","tipoEnd","munResid","bairro"]].rename(
    columns={"sinan_padded":"sinan_clean","cep_clean":"community_cep","tipoEnd":"cep_source"}
).to_parquet(OUT, index=False)
print(f"\nSaved → {OUT}  ({len(best):,} persons with community CEP)")
