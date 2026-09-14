"""Build a person-level key from raw TBweb (nome + mae + DTNASC + sexo),
join the cleaned cohort's address_type, and classify across-notification transitions
between prison (DETENTO), community (ENDERECO PADRAO), and homeless (SEM RESIDENCIA FIXA).

Outputs a summary table and saves a per-person trajectory file for further work.
"""
import unicodedata, re
from pathlib import Path
import pandas as pd

RAW   = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/Abandonment Paper/Banco de dados/tb web/TBWeb_20250123.xlsx")
CLEAN = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/Abandonment Paper/Data/Final_table_cleaned.csv")
OUT   = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/person_trajectories.parquet")

def norm(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

print("Loading raw TBweb (xlsx, ~80MB; this takes ~1-3 min)...")
raw = pd.read_excel(
    RAW,
    sheet_name="Exportacao_TBWeb_20250123",
    usecols=["sinan", "nome", "mae", "DTNASC", "sexo", "seqTrat", "tipoEndTrat",
             "notification_date", "tipoCaso", "munNotif"],
    dtype=str,
)
print(f"  raw rows: {len(raw):,}")

# Build normalized person key
raw["nome_n"] = raw["nome"].map(norm)
raw["mae_n"]  = raw["mae"].map(norm)
raw["dob_n"]  = raw["DTNASC"].astype(str).str[:10]
raw["sex_n"]  = raw["sexo"].map(norm)

# Drop rows missing critical identifiers (can't link)
linkable = raw[(raw["nome_n"] != "") & (raw["dob_n"] != "")].copy()
print(f"  linkable (have nome+DTNASC): {len(linkable):,}")

# Person key: nome + mae + dob + sex (nome+dob alone would over-merge common names)
linkable["person_key"] = (
    linkable["nome_n"] + "|" + linkable["mae_n"] + "|" + linkable["dob_n"] + "|" + linkable["sex_n"]
)

# One row per notification (sinan) for cross-notification trajectory analysis
# Many sinan have multiple seqTrat rows; we want notification-level rep with worst-case address type later.
# For the address_type, take the FIRST seqTrat (tx_seq=1) for each sinan from the cleaned table,
# since cleaned table already has a parsed address_type.
print("\nLoading cleaned cohort...")
clean = pd.read_csv(CLEAN, dtype=str, low_memory=False, usecols=["sinan_clean","tx_seq","notification_date","address_type","case_type","case_outcome","tx_city"])
clean["tx_seq_i"] = pd.to_numeric(clean["tx_seq"], errors="coerce")
# Per-notification: take first seqTrat row for entry address type, last for exit address type
ord_clean = clean.sort_values(["sinan_clean","tx_seq_i"])
entry = ord_clean.drop_duplicates("sinan_clean", keep="first")[["sinan_clean","address_type","notification_date","case_type","case_outcome","tx_city"]].rename(columns={"address_type":"addr_entry"})
exit_ = ord_clean.dropna(subset=["address_type"]).drop_duplicates("sinan_clean", keep="last")[["sinan_clean","address_type"]].rename(columns={"address_type":"addr_exit"})
notif = entry.merge(exit_, on="sinan_clean", how="left")
print(f"  notifications: {len(notif):,}")

# Map raw sinan -> person_key (one row per sinan; pick first)
raw_per_sinan = linkable.drop_duplicates("sinan", keep="first")[["sinan","person_key"]]
notif["sinan"] = notif["sinan_clean"].astype(str)
raw_per_sinan["sinan"] = raw_per_sinan["sinan"].astype(str)
merged = notif.merge(raw_per_sinan, on="sinan", how="left")
linked = merged.dropna(subset=["person_key"]).copy()
print(f"  notifications linked to a person_key: {len(linked):,} / {len(merged):,}")

# Parse notification_date
linked["notif_dt"] = pd.to_datetime(linked["notification_date"], errors="coerce", dayfirst=False)
linked = linked.sort_values(["person_key","notif_dt"])

# How many person_keys have multiple notifications?
counts = linked.groupby("person_key").size()
print(f"\n=== Person-level linkage ===")
print(f"  unique person_keys: {len(counts):,}")
print(f"  person_keys with >=2 notifications: {(counts>=2).sum():,}")
print(f"  max notifications per person: {counts.max()}")

multi_persons = counts[counts >= 2].index
multi = linked[linked["person_key"].isin(multi_persons)].copy()

# For each multi-notification person, sequence of address_types (entry-of-each-notification)
seq = (
    multi.dropna(subset=["addr_entry"])
         .groupby("person_key")["addr_entry"]
         .apply(list)
)

# Map address_type to short code
def code(a):
    return {"DETENTO":"P","ENDERECO PADRAO":"C","SEM RESIDENCIA FIXA":"H"}.get(a, "?")

seq_str = seq.apply(lambda lst: "".join(code(a) for a in lst))
print("\n=== Sequence of (entry) address types across notifications, top 30 patterns ===")
print(seq_str.value_counts().head(30).to_string())

# Bigram transitions across consecutive notifications per person
def bigrams(lst):
    return [(lst[i], lst[i+1]) for i in range(len(lst)-1)]

trans = []
for pk, lst in seq.items():
    trans.extend(bigrams(lst))
tdf = pd.DataFrame(trans, columns=["from_addr","to_addr"])
print("\n=== Across-notification consecutive-pair transitions (entry→entry) ===")
print(pd.crosstab(tdf["from_addr"], tdf["to_addr"], margins=True).to_string())

# Save trajectories
out_cols = ["person_key","sinan","notif_dt","addr_entry","addr_exit","case_type","case_outcome","tx_city"]
multi[out_cols].to_parquet(OUT, index=False)
print(f"\nSaved per-person trajectories ({len(multi):,} rows, {len(multi_persons):,} persons) -> {OUT}")
