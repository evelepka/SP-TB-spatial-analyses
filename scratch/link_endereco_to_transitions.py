"""Bring per-notification addresses from TBWeb_20250328_endereco.xlsx into the
prison↔community transition-pair table.

For each (sinan, notification) row, we have:
  - cep      = CEP of residence (often missing when DETENTO)
  - ceptrat  = CEP of treatment location (prison unit for incarcerated; clinic for community)
  - munResid, bairro, endereco — residence components
  - munNotif, munAtend, municTra — facility-location components
"""
from pathlib import Path
import pandas as pd

ADDR = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/.shortcut-targets-by-id/1WMps9BoKmDA6_Lzak12042gQKkXVI4qg/WHO modelling Project/Data/TBWeb_20250328_endereco.xlsx")
COHORT = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/cohort_with_spatial.csv")

print("Loading endereco file (xlsx ~34MB)...")
addr = pd.read_excel(
    ADDR,
    sheet_name="Exportacao_TBWeb_20250328",
    usecols=["SINAN","DTNASC","sexo","munResid","tipoEnd","endereco","numEnd","cep","bairro","munNotif","munAtend","endtrat","ceptrat","baitrat","municTra"],
    dtype=str,
)
print(f"  rows: {len(addr):,}, unique SINAN: {addr['SINAN'].nunique():,}")
print(f"  cep fill: {addr['cep'].notna().mean()*100:.1f}%  |  ceptrat fill: {addr['ceptrat'].notna().mean()*100:.1f}%")
print(f"  tipoEnd values: {addr['tipoEnd'].value_counts(dropna=False).head().to_dict()}")

# CEP fill rate by tipoEnd
print("\n=== CEP fill rate by tipoEnd ===")
for v, sub in addr.groupby("tipoEnd", dropna=False):
    print(f"  {str(v):25s} n={len(sub):>7,d}  cep filled={sub['cep'].notna().mean()*100:5.1f}%  ceptrat filled={sub['ceptrat'].notna().mean()*100:5.1f}%")

# Match key: SINAN here is raw; cohort has sinan_original / sinan_padded / sinan_clean
# Try: sinan_original (most likely matches SINAN exactly)
print("\nLoading cohort (sinan_original column for raw match)...")
cohort = pd.read_csv(COHORT, dtype=str, low_memory=False,
                     usecols=["sinan_clean","sinan_original","sinan_padded","tx_seq","notification_date","address_type","cep","tx_city"])
cohort = cohort.rename(columns={"cep":"cep_collapsed"})

# How well does SINAN (raw, addr file) match sinan_original (raw, cohort)?
for key in ["sinan_original","sinan_padded","sinan_clean"]:
    cohort_keys = set(cohort[key].dropna().unique())
    addr_keys = set(addr["SINAN"].dropna().unique())
    overlap = len(cohort_keys & addr_keys)
    print(f"  cohort.{key} ∩ addr.SINAN = {overlap:,}  (cohort unique = {len(cohort_keys):,}, addr unique = {len(addr_keys):,})")

# The addr file is at notification level — there may be multiple rows per SINAN if seqTrat varies.
# Check: do we have duplicate SINAN in addr?
dup = addr["SINAN"].value_counts()
print(f"\nSINAN multiplicity in endereco file: {(dup>=2).sum():,} SINANs have >=2 rows  (max={dup.max()})")

# Key insight: SINAN in this file is the notification number; each (person, notification) has its OWN cep.
# Pad SINAN to 7 digits to match sinan_padded
addr["sinan_padded"] = addr["SINAN"].astype(str).str.strip().str.zfill(7)
cohort["sinan_padded"] = cohort["sinan_padded"].astype(str)

# Now: build per-notification cohort rows (sinan_clean, notification_date) and try to match each
# to a row in the endereco file. The endereco file likely has one row per SINAN; cohort may have
# multiple sinan per person. Match by sinan_padded.
print("\n=== Joining per-notification CEPs onto cohort transition rows ===")
cohort_sorted = cohort.sort_values(["sinan_clean","notification_date","tx_seq"])
notif = cohort_sorted.drop_duplicates(["sinan_clean","notification_date"], keep="first").copy()
print(f"unique (person, notification_date) tuples: {len(notif):,}")

# In the addr file, dedupe to one row per sinan_padded (these may have multiple seqTrat already)
addr_one = addr.drop_duplicates("sinan_padded", keep="first")[
    ["sinan_padded","cep","ceptrat","munResid","bairro","tipoEnd","munNotif","municTra"]
].rename(columns={"cep":"cep_resid","bairro":"bairro_resid"})

merged = notif.merge(addr_one, on="sinan_padded", how="left")
print(f"  merged rows: {len(merged):,}")
print(f"  with cep_resid: {merged['cep_resid'].notna().sum():,} ({merged['cep_resid'].notna().mean()*100:.1f}%)")
print(f"  with ceptrat:   {merged['ceptrat'].notna().sum():,} ({merged['ceptrat'].notna().mean()*100:.1f}%)")

# Per-person distinct CEPs (residence vs treatment) across notifications
multi_episode_persons = notif.groupby("sinan_clean").size()
multi_episode_persons = multi_episode_persons[multi_episode_persons >= 2].index
multi_merged = merged[merged["sinan_clean"].isin(multi_episode_persons)].copy()

distinct_resid = multi_merged.dropna(subset=["cep_resid"]).groupby("sinan_clean")["cep_resid"].nunique()
distinct_trat  = multi_merged.dropna(subset=["ceptrat"]).groupby("sinan_clean")["ceptrat"].nunique()
print(f"\nAmong {len(multi_episode_persons):,} multi-episode persons:")
print(f"  with >=2 distinct cep_resid across notifications: {(distinct_resid >= 2).sum():,}")
print(f"  with >=2 distinct ceptrat across notifications:    {(distinct_trat  >= 2).sum():,}")

# Now: among transition pairs C→P and P→C, do we now see different CEPs?
multi_merged["addr_code"] = multi_merged["address_type"].map({"DETENTO":"P","ENDERECO PADRAO":"C","SEM RESIDENCIA FIXA":"H"}).fillna("?")
multi_merged = multi_merged.sort_values(["sinan_clean","notification_date"])

pairs = []
for sid, g in multi_merged.groupby("sinan_clean"):
    rows = g.to_dict("records")
    for i in range(len(rows)-1):
        a, b = rows[i], rows[i+1]
        pairs.append({
            "from": a["addr_code"], "to": b["addr_code"],
            "from_cep_resid": a["cep_resid"], "to_cep_resid": b["cep_resid"],
            "from_ceptrat":   a["ceptrat"],   "to_ceptrat":   b["ceptrat"],
            "from_munResid":  a["munResid"],  "to_munResid":  b["munResid"],
            "from_munNotif":  a["munNotif"],  "to_munNotif":  b["munNotif"],
            "from_bairro":    a["bairro_resid"], "to_bairro": b["bairro_resid"],
        })
pdf = pd.DataFrame(pairs)
print(f"\nconsecutive multi-episode pairs: {len(pdf):,}")

cp = pdf[(pdf["from"]=="C") & (pdf["to"]=="P")]
pc = pdf[(pdf["from"]=="P") & (pdf["to"]=="C")]

print(f"\n=== C→P pairs (n={len(cp):,}) — community to prison ===")
print(f"  from_cep_resid filled (community home CEP): {cp['from_cep_resid'].notna().sum():,} ({cp['from_cep_resid'].notna().mean()*100:.1f}%)")
print(f"  to_ceptrat filled (prison facility CEP):    {cp['to_ceptrat'].notna().sum():,} ({cp['to_ceptrat'].notna().mean()*100:.1f}%)")
print(f"  both filled:                                 {((cp['from_cep_resid'].notna()) & (cp['to_ceptrat'].notna())).sum():,}")
print(f"  community CEP != prison CEP (when both filled): {((cp['from_cep_resid'].notna()) & (cp['to_ceptrat'].notna()) & (cp['from_cep_resid']!=cp['to_ceptrat'])).sum():,}")

print(f"\n=== P→C pairs (n={len(pc):,}) — prison to community ===")
print(f"  from_ceptrat filled (prison facility CEP):  {pc['from_ceptrat'].notna().sum():,} ({pc['from_ceptrat'].notna().mean()*100:.1f}%)")
print(f"  to_cep_resid filled (community home CEP):   {pc['to_cep_resid'].notna().sum():,} ({pc['to_cep_resid'].notna().mean()*100:.1f}%)")
print(f"  both filled:                                 {((pc['from_ceptrat'].notna()) & (pc['to_cep_resid'].notna())).sum():,}")
print(f"  prison CEP != community CEP (when both filled): {((pc['from_ceptrat'].notna()) & (pc['to_cep_resid'].notna()) & (pc['from_ceptrat']!=pc['to_cep_resid'])).sum():,}")

print("\n--- 8 example C→P transitions (community CEP → prison CEP) ---")
print(cp[(cp['from_cep_resid'].notna()) & (cp['to_ceptrat'].notna())].head(8)[
    ["from_cep_resid","to_ceptrat","from_munResid","to_munResid","from_bairro"]
].to_string(index=False))

print("\n--- 8 example P→C transitions (prison CEP → community CEP) ---")
print(pc[(pc['from_ceptrat'].notna()) & (pc['to_cep_resid'].notna())].head(8)[
    ["from_ceptrat","to_cep_resid","from_munResid","to_munResid","to_bairro"]
].to_string(index=False))

# Save
OUT = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/transition_pairs_with_real_addresses.parquet")
pdf.to_parquet(OUT, index=False)
print(f"\nSaved → {OUT}")
