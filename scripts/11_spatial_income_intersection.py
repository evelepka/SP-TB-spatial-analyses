import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import os

print("--- 1. Loading 2010 Agregados Demográficos ---")
# 2010 Setores Censitários Demographic Tables for SP are split into two files: Capital (SP1) and Interior (SP2)
try:
    df_sp1 = pd.read_csv('Data/SP_Agregados_2010/Basico_SP1.csv', sep=';', encoding='latin1', dtype={'Cod_setor': str})
    df_sp2 = pd.read_csv('Data/SP_Agregados_2010/Basico_SP2.csv', sep=';', encoding='latin1', dtype={'Cod_setor': str})
    df_agregados = pd.concat([df_sp1, df_sp2], ignore_index=True)
except Exception as e:
    print(f"Error loading Agregados 2010: {e}")
    sys.exit(1)

# V005: Valor do rendimento nominal médio mensal das pessoas responsáveis
# Convert V005 to numeric. IBGE often uses string commas for decimals.
if df_agregados['V005'].dtype == object:
    df_agregados['V005'] = df_agregados['V005'].str.replace(',', '.').astype(float)
    
df_agregados = df_agregados.dropna(subset=['V005'])
print(f"Loaded {len(df_agregados)} Sectors with valid V005 Income data.")


print("\n--- 2. Loading 2010 São Paulo Sector Geometries ---")
# Wait, did we download the 2010 SP Setores?
# The earlier steps showed Data/SP_setores_2010/35SEE250GC_SIR.shp exists!
shapefile_2010_path = "Data/SP_setores_2010/35SEE250GC_SIR.shp"
if not os.path.exists(shapefile_2010_path):
    print("Error: 2010 Setores Censitários Shapefile not found!")
    sys.exit(1)

gdf_2010 = gpd.read_file(shapefile_2010_path)
print(f"Loaded {len(gdf_2010)} Sector Polygons.")

# Ensure ID column matches. In 2010 SHP it's usually 'CD_GEOCODI'
col_id = next((c for c in gdf_2010.columns if c in ['CD_GEOCODI', 'CD_SETOR']), None)
if not col_id:
    print(f"Columns: {gdf_2010.columns}")
    raise ValueError("Setor ID column not found in SHP.")

gdf_2010[col_id] = gdf_2010[col_id].astype(str)

print("Merging Demographics into Geometries...")
gdf_merged = gdf_2010.merge(df_agregados[['Cod_setor', 'V005']], left_on=col_id, right_on='Cod_setor', how='inner')
print(f"Merge yielded {len(gdf_merged)} Sectors with geometries and V005.")


print("\n--- 3. Integrating Patient Geocoordinates ---")
linkage_file = 'Data/cep_spatial_linkage_longitudinal.csv'
df_patients = pd.read_csv(linkage_file)
print(f"Loaded {len(df_patients)} geocoded patient records.")

geometry = [Point(xy) for xy in zip(df_patients['lon'], df_patients['lat'])]
geo_patients = gpd.GeoDataFrame(df_patients, geometry=geometry, crs="EPSG:4326")

# Convert both to SIRGAS 2000 (EPSG:4674) for highly accurate intersection
print("Standardizing CRS to EPSG:4674...")
gdf_merged = gdf_merged.to_crs("EPSG:4674")
geo_patients = geo_patients.to_crs("EPSG:4674")

print("Executing Spatial Point-in-Polygon Overlay...")
joined = gpd.sjoin(geo_patients, gdf_merged[['Cod_setor', 'V005', 'geometry']], how="left", predicate="within")

joined = joined[~joined.index.duplicated(keep='first')]
df_patients['income_V005'] = joined['V005']
matched = df_patients['income_V005'].notna().sum()
print(f"Successfully acquired Income Data for {matched} patients ({matched/len(df_patients)*100:.1f}%).")


print("\n--- 4. Discretizing Income into Quartiles ---")
# Evaluate only non-null values to calculate precise quartiles
valid_income = df_patients['income_V005'].dropna()
quartiles = valid_income.quantile([0.25, 0.5, 0.75]).tolist()

print(f"Tract Average Income Thresholds:")
print(f"  Q1 (Poorest): < R$ {quartiles[0]:.2f}")
print(f"  Q2: R$ {quartiles[0]:.2f} - {quartiles[1]:.2f}")
print(f"  Q3: R$ {quartiles[1]:.2f} - {quartiles[2]:.2f}")
print(f"  Q4 (Wealthiest): > R$ {quartiles[2]:.2f}")

def assign_quartile(val):
    if pd.isna(val): return "Unknown"
    if val <= quartiles[0]: return "Q1 (Poorest)"
    elif val <= quartiles[1]: return "Q2"
    elif val <= quartiles[2]: return "Q3"
    else: return "Q4 (Wealthiest)"

df_patients['income_quartile'] = df_patients['income_V005'].apply(assign_quartile)

output_file = 'Data/cep_income_linkage.csv'
df_patients.to_csv(output_file, index=False)
print(f"\nSaved updated linkages heavily augmented with income tracking to {output_file}.")
