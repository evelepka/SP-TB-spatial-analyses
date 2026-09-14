"""Peek at the LINKAGE files in Banco de dados to see if they provide a person-level
linkage we can use instead of raw name matching."""
from pathlib import Path
import pandas as pd

p1 = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/Abandonment Paper/Banco de dados/LINKAGE SIM  X  EXPORTACAO TBWEB  26 DEZEMBRO 2024 (1).xlsx")
p2 = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/Abandonment Paper/Banco de dados/LINKAGE SIM (1).xlsx")

for p in [p1, p2]:
    print(f"\n=== {p.name} ===")
    try:
        xls = pd.ExcelFile(p)
        print(f"sheets: {xls.sheet_names}")
        for sh in xls.sheet_names[:2]:
            d = pd.read_excel(p, sheet_name=sh, nrows=2, dtype=str)
            print(f"  -- {sh} ({d.shape[1]} cols) --")
            for i, c in enumerate(d.columns, 1):
                print(f"     {i:3d}. {c}")
    except Exception as e:
        print(f"err: {e}")
