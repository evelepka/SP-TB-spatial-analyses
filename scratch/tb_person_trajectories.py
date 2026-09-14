"""sinan_clean IS the person-level ID (per 00_clean_sinan.py).
Build per-person trajectories from cohort_with_spatial.csv:

  - Each row is a (person × notification × tx_seq) record
  - One person can have multiple notifications (TB episodes) and within each,
    multiple tx_seq rows (treatment-sequence / facility transfers)

Quantify:
  A. Persons with multiple distinct notification_dates (multi-episode)
  B. Within-notification transitions (mid-treatment address_type change)
  C. Across-notification transitions (between TB episodes)
  D. The most common trajectories
"""
from pathlib import Path
import pandas as pd

CSV = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/cohort_with_spatial.csv")
df = pd.read_csv(
    CSV,
    dtype=str,
    low_memory=False,
    usecols=["sinan_clean","tx_seq","notification_date","tx_start","address_type",
             "case_type","case_outcome","tx_city","lives_in_favela","cep","dob","sex"],
)
df["tx_seq_i"]  = pd.to_numeric(df["tx_seq"], errors="coerce")
df["notif_dt"]  = pd.to_datetime(df["notification_date"], errors="coerce")
df["addr_code"] = df["address_type"].map({"DETENTO":"P","ENDERECO PADRAO":"C","SEM RESIDENCIA FIXA":"H"}).fillna("?")
print(f"rows: {len(df):,}, unique persons (sinan_clean): {df['sinan_clean'].nunique():,}")

# Notifications: one row per (sinan_clean, notification_date)
df = df.sort_values(["sinan_clean","notif_dt","tx_seq_i"])
notif = df.drop_duplicates(["sinan_clean","notif_dt"], keep="first")
print(f"unique (person, notification_date) tuples: {len(notif):,}")

# ----- A: persons with multiple notifications -----
notifs_per_person = notif.groupby("sinan_clean")["notif_dt"].nunique()
print(f"\n=== A: Person-level notification counts ===")
print(notifs_per_person.value_counts().sort_index().head(15).to_string())
multi_episode_persons = notifs_per_person[notifs_per_person >= 2].index
print(f"persons with >=2 notification dates: {len(multi_episode_persons):,}")

# ----- B: within-notification transitions (same sinan_clean + same notif_dt, address varies) -----
within = (
    df.dropna(subset=["address_type"])
      .groupby(["sinan_clean","notif_dt"])["addr_code"]
      .nunique()
)
multi_addr_notif = within[within >= 2]
print(f"\n=== B: Within-notification transitions ===")
print(f"  (sinan_clean, notification_date) tuples with >=2 address_types in their tx_seq rows: {len(multi_addr_notif):,}")

# Direction within notification: first vs last tx_seq's address_code
ordered = df.dropna(subset=["address_type","notif_dt"]).sort_values(["sinan_clean","notif_dt","tx_seq_i"])
within_first = ordered.groupby(["sinan_clean","notif_dt"])["addr_code"].first()
within_last  = ordered.groupby(["sinan_clean","notif_dt"])["addr_code"].last()
wdir = pd.DataFrame({"first": within_first, "last": within_last})
wdir = wdir[wdir["first"] != wdir["last"]]
print(f"  notifications with directional change: {len(wdir):,}")
ct_w = pd.crosstab(wdir["first"].map({"P":"Prison","C":"Community","H":"Homeless"}),
                   wdir["last"].map({"P":"Prison","C":"Community","H":"Homeless"}),
                   margins=True)
print(ct_w.to_string())

# ----- C: across-notification transitions (between TB episodes for same person) -----
# Per person, take the FIRST tx_seq row of each notification (i.e., entry address_type)
entry = ordered.drop_duplicates(["sinan_clean","notif_dt"], keep="first")[
    ["sinan_clean","notif_dt","addr_code","case_type","case_outcome","tx_city","lives_in_favela"]
]
entry = entry.sort_values(["sinan_clean","notif_dt"])
multi_entry = entry[entry["sinan_clean"].isin(multi_episode_persons)]
print(f"\n=== C: Across-notification (between-episode) transitions ===")
print(f"  multi-episode entries: {len(multi_entry):,} from {multi_entry['sinan_clean'].nunique():,} persons")

# Trajectory string per person
seq = multi_entry.groupby("sinan_clean")["addr_code"].apply(list)
seq_str = seq.apply(lambda l: "".join(l))
print("\nTop 25 across-notification trajectories (entry addr_type at each notification):")
print(seq_str.value_counts().head(25).to_string())

# Consecutive transitions
pairs = []
for s in seq:
    for i in range(len(s)-1):
        pairs.append((s[i], s[i+1]))
ptab = pd.DataFrame(pairs, columns=["from","to"])
ptab["from_lbl"] = ptab["from"].map({"P":"Prison","C":"Community","H":"Homeless","?":"Unknown"})
ptab["to_lbl"]   = ptab["to"].map(  {"P":"Prison","C":"Community","H":"Homeless","?":"Unknown"})
print("\nConsecutive across-notification address_type pairs:")
print(pd.crosstab(ptab["from_lbl"], ptab["to_lbl"], margins=True).to_string())

# ----- D: Time gap between consecutive notifications by transition type -----
gaps = []
for sid, sub in multi_entry.groupby("sinan_clean"):
    sub = sub.sort_values("notif_dt")
    rows = sub.to_dict("records")
    for i in range(len(rows)-1):
        a, b = rows[i], rows[i+1]
        if pd.notna(a["notif_dt"]) and pd.notna(b["notif_dt"]):
            gaps.append({
                "from": a["addr_code"], "to": b["addr_code"],
                "gap_days": (b["notif_dt"] - a["notif_dt"]).days,
                "from_outcome": a["case_outcome"], "to_case_type": b["case_type"],
            })
gdf = pd.DataFrame(gaps)
print(f"\n=== D: Time gap (days) between consecutive notifications, by transition ===")
print(gdf.groupby(["from","to"])["gap_days"].describe().round(0).to_string())

# Save full trajectory file
OUT = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/person_trajectories.parquet")
multi_entry.to_parquet(OUT, index=False)
print(f"\nSaved {len(multi_entry):,} multi-episode entries from {len(multi_episode_persons):,} persons → {OUT}")

# Headline numbers
print("\n=== HEADLINE NUMBERS ===")
print(f"Total persons in cohort:                                  {df['sinan_clean'].nunique():,}")
print(f"Persons with multiple TB notifications (>=2 dates):       {len(multi_episode_persons):,}  ({len(multi_episode_persons)/df['sinan_clean'].nunique()*100:.1f}%)")
print(f"Within-notification address_type changes:                 {len(wdir):,} notifications")
print(f"  of which Prison↔Community (either direction):           {((wdir['first'].isin(['P','C'])) & (wdir['last'].isin(['P','C']))).sum():,}")
print(f"Across-notification (between episodes) consecutive pairs: {len(ptab):,}")
print(f"  Community → Prison:                                     {((ptab['from']=='C')&(ptab['to']=='P')).sum():,}")
print(f"  Prison → Community:                                     {((ptab['from']=='P')&(ptab['to']=='C')).sum():,}")
print(f"  Prison → Prison:                                        {((ptab['from']=='P')&(ptab['to']=='P')).sum():,}")
print(f"  Community → Community:                                  {((ptab['from']=='C')&(ptab['to']=='C')).sum():,}")
