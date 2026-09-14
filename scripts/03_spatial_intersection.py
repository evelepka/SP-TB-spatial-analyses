import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import json
import os

CACHE_PATH = "cep_coords_cache.json"
SHAPEFILE_PATH = "SP_setores_2022/SP_Setores_2022.shp" # Adjust based on actual .shp name inside directory
OUTPUT_PATH = "spatial_linkage_results.csv"

def main():
    print("Loading geocoded CEP coordinates...")
    if not os.path.exists(CACHE_PATH):
        print(f"Error: Could not find {CACHE_PATH}!")
        return
        
    with open(CACHE_PATH, "r") as f:
        cache = json.load(f)

    # Convert cache to a DataFrame
    records = []
    for cep, data in cache.items():
        if data.get("lat") is not None and data.get("lon") is not None:
            records.append({
                "cep": cep,
                "lat": float(data["lat"]),
                "lon": float(data["lon"]),
                "city": data.get("city", ""),
                "bairro": data.get("bairro", "")
            })
    
    df_pts = pd.DataFrame(records)
    print(f"Loaded {len(df_pts)} valid coordinates from cache.")

    # Convert to GeoDataFrame
    print("Converting to Spatial Points...")
    geometry = [Point(xy) for xy in zip(df_pts['lon'], df_pts['lat'])]
    gdf_pts = gpd.GeoDataFrame(df_pts, geometry=geometry)
    
    # Set Coordinate Reference System (CRS) for GPS coordinates (WGS84)
    gdf_pts.set_crs(epsg=4326, inplace=True)

    print(f"Loading IBGE 2022 Census Tract Shapefiles from {SHAPEFILE_PATH}...")
    try:
        gdf_polys = gpd.read_file(SHAPEFILE_PATH)
    except Exception as e:
        print(f"Error loading shapefile: {e}")
        return

    # Check CRS of shapefile and align point CRS to match
    print(f"Shapefile CRS: {gdf_polys.crs}")
    gdf_pts = gdf_pts.to_crs(gdf_polys.crs)

    print("Filtering for Favelas e Comunidades Urbanas...")
    # The specific column name for "Tipo de Setor" varies slightly by IBGE release (e.g., TIPO_SETOR, CD_FCU, etc.)
    # We will identify the favela polygons dynamically or you can adjust the column matching TIPO=='Favela'
    # Assuming 'NM_FCU' exists or similar indicator for Favelas in 2022 data
    favela_cols = [col for col in gdf_polys.columns if 'FCU' in col.upper() or 'FAVELA' in col.upper() or 'TIPO' in col.upper()]
    print(f"Found potential Favela indicator columns: {favela_cols}")
    
    # This is a placeholder filter. Inspect `gdf_polys.head()` on Sherlock to set the exact string match if needed.
    # For now, we will just do the spatial join against ALL tracts and keep the metadata so you can see which tract they landed in.

    print("Executing Spatial Join (Point-in-Polygon)...")
    # Join points to the polygon they intersect
    joined = gpd.sjoin(gdf_pts, gdf_polys, how="left", predicate="intersects")
    
    joined.to_csv(OUTPUT_PATH, index=False)
    print(f"Completed! Saved linkage results to {OUTPUT_PATH}")
    print(joined.head())

if __name__ == "__main__":
    main()
