"""1. Within-notification direction: tx_seq=1 vs tx_seq=max for multi-address sinan_clean.
   2. Check raw TBweb exports for a name field (CNS / nome / mae) to confirm cross-notification person linkage.
"""
import pandas as pd
from pathlib import Path

CSV = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/Abandonment Paper/Data/Final_table_cleaned.csv")
df = pd.read_csv(CSV, dtype=str, low_memory=False)
df["tx_seq_int"] = pd.to_numeric(df["tx_seq"], errors="coerce")

# --- Direction within multi-address notifications ---
g = df.groupby("sinan_clean")["address_type"].nunique(dropna=True)
multi = g[g >= 2].index
sub = df[df["sinan_clean"].isin(multi)].copy()

# First row (lowest tx_seq) and last row (highest tx_seq) per notification
sub_sorted = sub.sort_values(["sinan_clean", "tx_seq_int"])
first = sub_sorted.dropna(subset=["address_type"]).groupby("sinan_clean").first()["address_type"]
last  = sub_sorted.dropna(subset=["address_type"]).groupby("sinan_clean").last()["address_type"]
pair = pd.DataFrame({"first": first, "last": last})
pair = pair[pair["first"] != pair["last"]]

print(f"=== Direction of within-notification address_type changes (n={len(pair):,}) ===")
ct = pd.crosstab(pair["first"], pair["last"], margins=True)
print(ct.to_string())

# --- Look at raw TBweb XLSX for hidden name fields ---
TBWEB = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/Abandonment Paper/Banco de dados/tb web/TBWeb_20250123.xlsx")
print(f"\n=== Probing raw {TBWEB.name} ===")
try:
    # read header only
    xls = pd.ExcelFile(TBWEB)
    print(f"sheets: {xls.sheet_names}")
    head_df = pd.read_excel(TBWEB, sheet_name=xls.sheet_names[0], nrows=1, dtype=str)
    print(f"raw TBweb columns ({len(head_df.columns)}):")
    for i, c in enumerate(head_df.columns, 1):
        print(f"  {i:3d}. {c}")
except Exception as e:
    print(f"read failed: {e}")

# --- Probe Tabela mae ---
MAE = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/Abandonment Paper/Banco de dados/tb web/Tabela mae.xlsx")
print(f"\n=== Probing {MAE.name} ===")
try:
    xls = pd.ExcelFile(MAE)
    print(f"sheets: {xls.sheet_names}")
    head_df = pd.read_excel(MAE, sheet_name=xls.sheet_names[0], nrows=1, dtype=str)
    print(f"Tabela mae columns ({len(head_df.columns)}):")
    for i, c in enumerate(head_df.columns, 1):
        print(f"  {i:3d}. {c}")
except Exception as e:
    print(f"read failed: {e}")
