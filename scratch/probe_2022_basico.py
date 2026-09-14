"""Inspect the 2022 IBGE Agregados Basico file to find the population variable."""
import pandas as pd
from pathlib import Path

P = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv")
# Try latin1 first
try:
    d = pd.read_csv(P, sep=";", encoding="latin1", nrows=5, dtype=str)
except Exception as e:
    print(e)
    d = pd.read_csv(P, sep=";", encoding="utf-8", nrows=5, dtype=str)
print(f"cols ({d.shape[1]}): {list(d.columns)}")
print(d.head(2).T.to_string())
