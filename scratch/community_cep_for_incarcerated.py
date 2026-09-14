"""Find a community CEP for every person who was incarcerated at any point in TBweb.

Strategy (greedy, takes first available):
  Source 1: For each DETENTO notification, the row's own `cep` field (residence
            declared at intake) — when filled, this IS the community CEP.
  Source 2: For each non-DETENTO notification of the same person, the row's `cep`
            (community or homeless residence at that notification).

Pick the best available source per person and tally coverage.
"""
from pathlib import Path
import pandas as pd

ADDR   = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/.shortcut-targets-by-id/1WMps9BoKmDA6_Lzak12042gQKkXVI4qg/WHO modelling Project/Data/TBWeb_20250328_endereco.xlsx")
COHORT = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/cohort_with_spatial.csv")

print("Loading endereco file...")
addr = pd.read_excel(
    ADDR, sheet_name="Exportacao_TBWeb_20250328",
    usecols=["SINAN","tipoEnd","cep","ceptrat","munResid","bairro","endereco","numEnd"],
    dtype=str,
)
addr["sinan_padded"] = addr["SINAN"].astype(str).str.strip().str.zfill(7)
addr["cep_clean"]    = addr["cep"].astype(str).str.strip().str.replace("-","").str.zfill(8)
# Treat "00000000" and "nan" as missing
addr.loc[addr["cep_clean"].isin(["00000000","nan","NAN","NONE","0"]), "cep_clean"] = pd.NA
addr.loc[addr["cep_clean"].str.len() != 8, "cep_clean"] = pd.NA

print("Loading cohort (sinan_clean=person, sinan_padded=notification, address_type)...")
cohort = pd.read_csv(COHORT, dtype=str, low_memory=False,
                     usecols=["sinan_clean","sinan_padded","tx_seq","notification_date","address_type"])

# Identify all persons with at least one DETENTO notification (across any tx_seq)
ever_detento = cohort[cohort["address_type"]=="DETENTO"]["sinan_clean"].unique()
print(f"\nPersons with ANY DETENTO notification (incarcerated at any point): {len(ever_detento):,}")
n_total = cohort["sinan_clean"].nunique()
print(f"  ({len(ever_detento)/n_total*100:.1f}% of {n_total:,} total cohort persons)")

# For each ever-incarcerated person, gather all their (notification, address_type, cep) rows from addr
# Join cohort sinan_padded → addr.SINAN. Cohort has multiple rows per (person, notif) via tx_seq; dedupe.
cohort_notif = cohort.sort_values(["sinan_clean","notification_date","tx_seq"]).drop_duplicates(
    ["sinan_clean","sinan_padded"], keep="first"
)
# Merge in addr per sinan_padded (first row per SINAN in addr is enough — cep is constant within SINAN)
addr_one = addr.drop_duplicates("sinan_padded", keep="first")[
    ["sinan_padded","cep_clean","ceptrat","tipoEnd","munResid","bairro","endereco","numEnd"]
].rename(columns={"cep_clean":"cep_resid"})

merged = cohort_notif.merge(addr_one, on="sinan_padded", how="left")

# Focus on incarcerated persons
inc = merged[merged["sinan_clean"].isin(ever_detento)].copy()
print(f"\nNotifications belonging to ever-incarcerated persons: {len(inc):,}")
print(f"  of which DETENTO notifications:                       {(inc['address_type']=='DETENTO').sum():,}")
print(f"  of which non-DETENTO notifications (these persons' community/homeless episodes): {(inc['address_type']!='DETENTO').sum():,}")

# Source 1: DETENTO rows with own cep_resid filled
src1 = inc[(inc["address_type"]=="DETENTO") & (inc["cep_resid"].notna())]
print(f"\nSource 1 — DETENTO row's own cep_resid filled (home declared at intake):")
print(f"  notifications: {len(src1):,}")
print(f"  unique persons covered: {src1['sinan_clean'].nunique():,}")

# Source 2: non-DETENTO rows (community or homeless) of these same persons, with cep_resid filled
src2 = inc[(inc["address_type"]!="DETENTO") & (inc["cep_resid"].notna())]
print(f"\nSource 2 — non-DETENTO notifications of incarcerated persons with cep_resid filled:")
print(f"  notifications: {len(src2):,}")
print(f"  unique persons covered: {src2['sinan_clean'].nunique():,}")

# Combine: per person, take first available community CEP, preferring non-DETENTO (likely more reliable home)
inc_with_cep = inc[inc["cep_resid"].notna()].copy()
# Prefer non-DETENTO source: rank 0 = ENDERECO PADRAO, 1 = SEM RES, 2 = DETENTO
rank = {"ENDERECO PADRAO":0, "SEM RESIDENCIA FIXA":1, "DETENTO":2}
inc_with_cep["src_rank"] = inc_with_cep["address_type"].map(rank).fillna(3).astype(int)
inc_with_cep = inc_with_cep.sort_values(["sinan_clean","src_rank","notification_date"])
best = inc_with_cep.drop_duplicates("sinan_clean", keep="first")
print(f"\nBest available community CEP per incarcerated person:")
print(f"  persons with ANY community CEP recovered: {len(best):,}")
print(f"  coverage of incarcerated persons: {len(best)/len(ever_detento)*100:.1f}%")
print(f"\n  source breakdown of the recovered CEP:")
print(best["address_type"].value_counts().to_string())

# Distribution of which source contributed
print("\n  (community = ENDERECO PADRAO row, homeless = SEM RES, prison-intake = DETENTO with cep)")
print(f"  from community notification:  {(best['address_type']=='ENDERECO PADRAO').sum():,}")
print(f"  from homeless notification:   {(best['address_type']=='SEM RESIDENCIA FIXA').sum():,}")
print(f"  from DETENTO intake cep:      {(best['address_type']=='DETENTO').sum():,}")

# Unreached: how many incarcerated persons have NO community CEP available anywhere?
unreached = set(ever_detento) - set(best["sinan_clean"])
print(f"\nIncarcerated persons with NO community CEP recoverable from any of their notifications: {len(unreached):,}  ({len(unreached)/len(ever_detento)*100:.1f}%)")

# Save the lookup table
OUT = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/community_cep_for_incarcerated.parquet")
best[["sinan_clean","cep_resid","address_type","munResid","bairro","notification_date"]].rename(
    columns={"cep_resid":"community_cep","address_type":"cep_source_addr_type",
             "notification_date":"cep_source_notif_date"}
).to_parquet(OUT, index=False)
print(f"\nSaved → {OUT}")
