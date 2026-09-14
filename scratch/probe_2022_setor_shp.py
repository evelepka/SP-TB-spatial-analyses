"""Inspect 2022 setor shapefile for the favela classification column."""
import geopandas as gpd
from pathlib import Path
import pandas as pd

P = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/SP_setores_2022/SP_setores_CD2022.shp")
g = gpd.read_file(P, rows=5)
print(f"shp cols ({g.shape[1]}): {list(g.columns)}")
print(g.drop(columns="geometry").head(3).to_string())

# Now full read with just attributes
g_full = gpd.read_file(P, columns=[c for c in g.columns if c != "geometry"])
for col in g_full.columns:
    if col == "geometry": continue
    n_uniq = g_full[col].nunique(dropna=False)
    if n_uniq < 20:
        print(f"\n{col} (nunique={n_uniq}):")
        print(g_full[col].value_counts(dropna=False).head(15).to_string())
