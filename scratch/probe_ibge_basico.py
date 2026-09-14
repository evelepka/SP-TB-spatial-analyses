"""Find the population variable in IBGE Basico_SP files."""
import pandas as pd
from pathlib import Path

P1 = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/SP_Agregados_2010/Basico_SP1.csv")
P2 = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/SP_Agregados_2010/Basico_SP2.csv")

for p in [P1, P2]:
    try:
        df = pd.read_csv(p, sep=";", encoding="latin1", nrows=3, dtype=str)
    except Exception as e:
        print(f"{p.name}: err {e}"); continue
    print(f"\n=== {p.name} — {df.shape[1]} cols ===")
    for i,c in enumerate(df.columns,1):
        print(f"  {i:3d}. {c}")
