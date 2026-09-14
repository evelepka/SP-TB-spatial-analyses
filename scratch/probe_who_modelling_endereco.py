"""Inspect TBWeb_20250328_endereco.xlsx — likely the per-notification address export."""
from pathlib import Path
import pandas as pd

P = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/.shortcut-targets-by-id/1WMps9BoKmDA6_Lzak12042gQKkXVI4qg/WHO modelling Project/Data/TBWeb_20250328_endereco.xlsx")

xls = pd.ExcelFile(P)
print(f"sheets: {xls.sheet_names}")
for sh in xls.sheet_names:
    d = pd.read_excel(P, sheet_name=sh, nrows=3, dtype=str)
    print(f"\n=== Sheet: {sh}  ({d.shape[1]} cols) ===")
    for i, c in enumerate(d.columns, 1):
        print(f"  {i:3d}. {c}")
    addr_kw = ["endereco","cep","logradouro","rua","bairro","numero","tipoEnd","municResid","munResid","areaResid","ENDERECO","CEP","NUMERO","BAIRRO"]
    addr_cols = [c for c in d.columns if any(k.lower() in c.lower() for k in addr_kw)]
    print(f"  ADDRESS-RELATED: {addr_cols}")
    print(f"\n  -- first 3 rows of address-related cols --")
    if addr_cols:
        print(d[addr_cols].head(3).to_string(index=False))
