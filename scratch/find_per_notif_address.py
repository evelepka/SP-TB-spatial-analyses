"""Look for a per-notification endereco/CEP column in the raw TBweb exports.
We've already seen the LINKAGE SIM file has an `endereco` column for the SIM-linked
mortality subset; check if the broader Exportacao_TBWeb file also has it.
"""
from pathlib import Path
import pandas as pd

candidates = [
    Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/Abandonment Paper/Banco de dados/tb web/Exportacao_TBWeb_20250123.xlsx"),
    Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/Abandonment Paper/Banco de dados/tb web/TBWeb_20250103 2013-2024.xlsx"),
    Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/Abandonment Paper/Banco de dados/tb web/tabela_final_corrigida_1.xlsx"),
]
ADDR_KEYWORDS = ["endereco","cep","logradouro","rua","bairro","mun","numero","tipoEnd","areaResid"]

for p in candidates:
    print(f"\n=== {p.name} ({p.stat().st_size//1024//1024} MB) ===")
    try:
        xls = pd.ExcelFile(p)
        for sh in xls.sheet_names[:2]:
            d = pd.read_excel(p, sheet_name=sh, nrows=1, dtype=str)
            print(f"  -- {sh} ({d.shape[1]} cols) --")
            addr_cols = [c for c in d.columns if any(k.lower() in c.lower() for k in ADDR_KEYWORDS)]
            if addr_cols:
                print(f"     address-related columns: {addr_cols}")
            else:
                print(f"     no obvious address columns; first 10 cols: {list(d.columns)[:10]}")
    except Exception as e:
        print(f"     err: {e}")
