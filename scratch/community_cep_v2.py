"""Recompute community-CEP coverage for ever-incarcerated persons, with proper NA
handling for the cep field (the prior script's str→zfill produced '00000nan' artifacts)."""
from pathlib import Path
import pandas as pd

ADDR   = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/.shortcut-targets-by-id/1WMps9BoKmDA6_Lzak12042gQKkXVI4qg/WHO modelling Project/Data/TBWeb_20250328_endereco.xlsx")
COHORT = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/cohort_with_spatial.csv")

print("Loading endereco file...")
addr = pd.read_excel(
    ADDR, sheet_name="Exportacao_TBWeb_20250328",
    usecols=["SINAN","tipoEnd","cep","ceptrat","munResid","bairro"],
    dtype=str,
)
addr["sinan_padded"] = addr["SINAN"].astype(str).str.strip().str.zfill(7)

def clean_cep(s):
    if s is None: return pd.NA
    if pd.isna(s): return pd.NA
    s = str(s).strip().replace("-","").replace(".","").replace(" ","")
    if s in {"", "nan", "NaN", "NAN", "None", "NONE", "0", "00000000"}: return pd.NA
    if not s.isdigit(): return pd.NA
    s = s.zfill(8)
    if len(s) != 8: return pd.NA
    return s

addr["cep_clean"] = addr["cep"].map(clean_cep)
print(f"addr rows: {len(addr):,}, cep_clean filled: {addr['cep_clean'].notna().sum():,} ({addr['cep_clean'].notna().mean()*100:.1f}%)")

# Fill rate by tipoEnd, properly
print("\n=== cep_clean fill rate by tipoEnd ===")
for v, g in addr.groupby("tipoEnd", dropna=False):
    print(f"  {str(v):25s} n={len(g):>7,d}  cep_clean filled={g['cep_clean'].notna().sum():>7,d} ({g['cep_clean'].notna().mean()*100:5.1f}%)")

print("\nLoading cohort...")
cohort = pd.read_csv(COHORT, dtype=str, low_memory=False,
                     usecols=["sinan_clean","sinan_padded","tx_seq","notification_date","address_type"])

# Persons ever incarcerated
ever_detento = set(cohort.loc[cohort["address_type"]=="DETENTO","sinan_clean"].unique())
print(f"\nEver-incarcerated persons: {len(ever_detento):,}")

# One row per (person, notification) at cohort level
cohort_notif = (cohort.sort_values(["sinan_clean","notification_date","tx_seq"])
                      .drop_duplicates(["sinan_clean","sinan_padded"], keep="first"))
print(f"Cohort notification-level rows: {len(cohort_notif):,}")

# All notifications for ever-incarcerated persons (across address types)
inc_notif = cohort_notif[cohort_notif["sinan_clean"].isin(ever_detento)]
print(f"  of which belong to ever-incarcerated persons: {len(inc_notif):,}")
print(f"  breakdown by address_type:\n{inc_notif['address_type'].value_counts(dropna=False).to_string()}")

# Merge addr (dedupe to one row per sinan_padded)
addr_one = addr.drop_duplicates("sinan_padded", keep="first")[["sinan_padded","cep_clean","tipoEnd","munResid","bairro"]]
m = inc_notif.merge(addr_one, on="sinan_padded", how="left")
print(f"\nMerged inc_notif × addr: {len(m):,} rows")
print(f"  with cep_clean filled: {m['cep_clean'].notna().sum():,}")
print(f"  by address_type:\n{m.dropna(subset=['cep_clean']).groupby('address_type').size().to_string()}")

# Pick best community CEP per incarcerated person:
# Priority: ENDERECO PADRAO > SEM RESIDENCIA FIXA > DETENTO (with cep_clean filled)
rank = {"ENDERECO PADRAO":0, "SEM RESIDENCIA FIXA":1, "DETENTO":2}
m["rank"] = m["address_type"].map(rank).fillna(9).astype(int)
m_with = m.dropna(subset=["cep_clean"]).sort_values(["sinan_clean","rank","notification_date"])
best = m_with.drop_duplicates("sinan_clean", keep="first")
print(f"\n=== Coverage ===")
print(f"  Incarcerated persons WITH a community CEP recovered: {len(best):,} ({len(best)/len(ever_detento)*100:.1f}%)")
print(f"  By source of the CEP:")
print(best["address_type"].value_counts().to_string())
print(f"\n  Incarcerated persons with NO CEP in any of their notifications: {len(ever_detento)-len(best):,}")

# Save
OUT = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/community_cep_for_incarcerated.parquet")
best[["sinan_clean","cep_clean","address_type","munResid","bairro","notification_date"]].rename(
    columns={"cep_clean":"community_cep","address_type":"cep_source_addr_type",
             "notification_date":"cep_source_notif_date"}
).to_parquet(OUT, index=False)
print(f"\nSaved → {OUT}")
