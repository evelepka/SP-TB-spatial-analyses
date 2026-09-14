"""For people with prison↔community transitions, check if each notification has its
own CEP (we have per-notification addresses) or if all notifications share one CEP
(the upstream join collapsed addresses).

If per-notification: we already have the community address for C→P pairs.
If collapsed: we need to re-join from a pre-collapse source.
"""
from pathlib import Path
import pandas as pd

CSV = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/cohort_with_spatial.csv")

df = pd.read_csv(CSV, dtype=str, low_memory=False,
                 usecols=["sinan_clean","tx_seq","notification_date","address_type","cep","tx_city","lives_in_favela","NM_FCU"])
df["tx_seq_i"] = pd.to_numeric(df["tx_seq"], errors="coerce")
df["notif_dt"] = pd.to_datetime(df["notification_date"], errors="coerce")
df["addr_code"] = df["address_type"].map({"DETENTO":"P","ENDERECO PADRAO":"C","SEM RESIDENCIA FIXA":"H"}).fillna("?")

print(f"rows: {len(df):,}, persons: {df['sinan_clean'].nunique():,}")
print(f"\nCEP fill rate:           {df['cep'].notna().sum():,}/{len(df):,} ({df['cep'].notna().mean()*100:.1f}%)")
print(f"tx_city fill rate:       {df['tx_city'].notna().sum():,}/{len(df):,} ({df['tx_city'].notna().mean()*100:.1f}%)")
print(f"NM_FCU (favela) fill:    {df['NM_FCU'].notna().sum():,}/{len(df):,} ({df['NM_FCU'].notna().mean()*100:.1f}%)")
print(f"lives_in_favela values:  {df['lives_in_favela'].value_counts(dropna=False).head(5).to_dict()}")

# Build one row per (person, notif_dt) using first tx_seq
df_sorted = df.sort_values(["sinan_clean","notif_dt","tx_seq_i"])
notif = df_sorted.drop_duplicates(["sinan_clean","notif_dt"], keep="first")
print(f"\nunique (person, notif_dt) tuples: {len(notif):,}")

# For each person, count distinct CEPs across their notifications
n_ceps = notif.dropna(subset=["cep"]).groupby("sinan_clean")["cep"].nunique()
print(f"\n=== Distinct CEPs per person (across notifications) ===")
print(n_ceps.value_counts().sort_index().head(10).to_string())

multi_episode = notif.groupby("sinan_clean")["notif_dt"].nunique()
multi_episode = multi_episode[multi_episode >= 2].index
n_ceps_me = notif[notif["sinan_clean"].isin(multi_episode)].dropna(subset=["cep"]).groupby("sinan_clean")["cep"].nunique()
print(f"\nAmong {len(multi_episode):,} multi-episode persons:")
print(f"  with >=2 distinct CEPs across notifications: {(n_ceps_me >= 2).sum():,}")
print(f"  CEP distribution:\n{n_ceps_me.value_counts().sort_index().head(10).to_string()}")

# Now focus on C→P and P→C pairs: do the two notifications have different CEPs?
# Per person, sequence of (addr_code, cep) ordered by notif_dt
def pairs_for(person_df):
    rows = person_df.sort_values("notif_dt").to_dict("records")
    out = []
    for i in range(len(rows)-1):
        a, b = rows[i], rows[i+1]
        out.append({
            "sinan_clean": a["sinan_clean"],
            "from_addr": a["addr_code"], "to_addr": b["addr_code"],
            "from_cep": a["cep"], "to_cep": b["cep"],
            "from_dt": a["notif_dt"], "to_dt": b["notif_dt"],
            "from_city": a["tx_city"], "to_city": b["tx_city"],
            "from_favela": a["NM_FCU"], "to_favela": b["NM_FCU"],
        })
    return out

multi_notif = notif[notif["sinan_clean"].isin(multi_episode)]
all_pairs = []
for sid, g in multi_notif.groupby("sinan_clean"):
    all_pairs.extend(pairs_for(g))
pdf = pd.DataFrame(all_pairs)
print(f"\nconsecutive pairs across multi-episode persons: {len(pdf):,}")

# Focus on transitions between Community and Prison
mask_cp = (pdf["from_addr"]=="C") & (pdf["to_addr"]=="P")
mask_pc = (pdf["from_addr"]=="P") & (pdf["to_addr"]=="C")
print(f"\n=== C→P pairs: {mask_cp.sum():,} ===")
cp = pdf[mask_cp]
print(f"  both have CEP:            {(cp['from_cep'].notna() & cp['to_cep'].notna()).sum():,}")
print(f"  CEPs differ:              {(cp['from_cep'].notna() & cp['to_cep'].notna() & (cp['from_cep']!=cp['to_cep'])).sum():,}")
print(f"  CEPs identical:           {(cp['from_cep'].notna() & cp['to_cep'].notna() & (cp['from_cep']==cp['to_cep'])).sum():,}")
print(f"  community CEP available (from_cep when from=C): {cp['from_cep'].notna().sum():,}")

print(f"\n=== P→C pairs: {mask_pc.sum():,} ===")
pc = pdf[mask_pc]
print(f"  both have CEP:            {(pc['from_cep'].notna() & pc['to_cep'].notna()).sum():,}")
print(f"  CEPs differ:              {(pc['from_cep'].notna() & pc['to_cep'].notna() & (pc['from_cep']!=pc['to_cep'])).sum():,}")
print(f"  CEPs identical:           {(pc['from_cep'].notna() & pc['to_cep'].notna() & (pc['from_cep']==pc['to_cep'])).sum():,}")
print(f"  community CEP available (to_cep when to=C):    {pc['to_cep'].notna().sum():,}")

# Show a few example pairs (no PHI; just CEPs)
print(f"\n--- 8 example C→P transitions (CEP_community → CEP_prison) ---")
print(cp.dropna(subset=["from_cep","to_cep"]).head(8)[["from_cep","to_cep","from_city","to_city","from_dt","to_dt"]].to_string(index=False))
print(f"\n--- 8 example P→C transitions (CEP_prison → CEP_community) ---")
print(pc.dropna(subset=["from_cep","to_cep"]).head(8)[["from_cep","to_cep","from_city","to_city","from_dt","to_dt"]].to_string(index=False))

# Save the resolved address pairs for downstream geocoding/community analysis
OUT = Path("/Users/jasonandrews/repos/SP-TB-spatial-analyses/scratch/transition_pairs_with_ceps.parquet")
pdf.to_parquet(OUT, index=False)
print(f"\nSaved {len(pdf):,} consecutive pairs → {OUT}")
