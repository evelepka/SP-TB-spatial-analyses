"""
05_spatial_intersection.py
--------------------------
Performs spatial point-in-polygon intersection between geocoded CEP coordinates
and IBGE 2022 Census Tract polygons to determine whether each patient lives in
a Favela/Comunidade Urbana.

Run locally on Mac (geopandas installed):
    cd "Abandonment Paper"
    python3 code/05_spatial_intersection.py

Inputs:
    - Data/cep_coords_MASTER.json  (merged geocoding cache from 04_merge_caches.py)
    - Data/SP_setores_2022/SP_setores_CD2022.shp  (IBGE 2022 census tracts)

Outputs:
    - Data/cep_spatial_linkage.csv  (CEP → census tract + favela flag)
"""

import json
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# ── Paths ──────────────────────────────────────────────────────────────────
CACHE_PATH     = "Data/cep_coords_MASTER.json"
SHAPEFILE_PATH = "Data/SP_setores_2022/SP_setores_CD2022.shp"
OUTPUT_PATH    = "Data/cep_spatial_linkage.csv"

def main():
    # ── 1. Load geocoded CEPs ──────────────────────────────────────────────
    print("1. Loading geocoded CEP coordinates...")
    if not os.path.exists(CACHE_PATH):
        print(f"   ✗ {CACHE_PATH} not found. Run 04_merge_caches.py first.")
        return
    
    with open(CACHE_PATH, "r") as f:
        cache = json.load(f)
    
    records = []
    for cep, data in cache.items():
        lat = data.get("lat")
        lon = data.get("lon")
        if lat is not None and lon is not None:
            try:
                records.append({
                    "cep": cep,
                    "lat": float(lat),
                    "lon": float(lon),
                    "city": data.get("city", ""),
                    "bairro": data.get("bairro", ""),
                    "source": data.get("source", "brasilapi"),
                })
            except (ValueError, TypeError):
                continue
    
    df_pts = pd.DataFrame(records)
    print(f"   ✓ {len(df_pts)} CEPs with valid coordinates (of {len(cache)} total)")

    # ── 2. Convert to spatial points ───────────────────────────────────────
    print("2. Converting to spatial points (GeoDataFrame)...")
    geometry = [Point(xy) for xy in zip(df_pts["lon"], df_pts["lat"])]
    gdf_pts = gpd.GeoDataFrame(df_pts, geometry=geometry, crs="EPSG:4326")
    
    # ── 3. Load IBGE 2022 Census Tracts ────────────────────────────────────
    print(f"3. Loading IBGE 2022 shapefiles from {SHAPEFILE_PATH}...")
    gdf_tracts = gpd.read_file(SHAPEFILE_PATH)
    print(f"   ✓ {len(gdf_tracts)} census tracts loaded (CRS: {gdf_tracts.crs})")
    
    favela_count = gdf_tracts["CD_FCU"].notna().sum()
    print(f"   ✓ {favela_count} tracts classified as Favelas/Comunidades Urbanas")
    
    # ── 4. Align CRS ──────────────────────────────────────────────────────
    print("4. Aligning coordinate reference systems...")
    gdf_pts = gdf_pts.to_crs(gdf_tracts.crs)
    print(f"   ✓ Points projected to {gdf_tracts.crs}")
    
    # ── 5. Spatial Join ────────────────────────────────────────────────────
    print("5. Performing spatial join (point-in-polygon)...")
    joined = gpd.sjoin(gdf_pts, gdf_tracts, how="left", predicate="within")
    print(f"   ✓ Join complete: {len(joined)} records")
    
    # ── 6. Create binary favela indicator ──────────────────────────────────
    print("6. Creating binary favela indicator...")
    joined["lives_in_favela"] = (joined["CD_FCU"].notna()).astype(int)
    
    # For CEPs that didn't fall within any tract (e.g. imprecise geocoding)
    no_match = joined["CD_SETOR"].isna().sum()
    in_favela = joined["lives_in_favela"].sum()
    not_favela = ((joined["lives_in_favela"] == 0) & (joined["CD_SETOR"].notna())).sum()
    
    print(f"   ✓ Results:")
    print(f"     - In favela:         {in_favela}")
    print(f"     - Not in favela:     {not_favela}")
    print(f"     - No tract match:    {no_match}")
    
    # ── 7. Select and save output columns ──────────────────────────────────
    print(f"7. Saving results to {OUTPUT_PATH}...")
    output_cols = [
        "cep", "lat", "lon", "city", "bairro", "source",
        "CD_SETOR", "NM_MUN", "NM_DIST", "NM_BAIRRO",     # Census tract info
        "CD_FCU", "NM_FCU",                                 # Favela classification
        "CD_TIPO", "SITUACAO", "AREA_KM2",                  # Tract metadata
        "lives_in_favela"                                    # Binary indicator
    ]
    # Keep only columns that exist (some might not be present)
    output_cols = [c for c in output_cols if c in joined.columns]
    
    result = joined[output_cols].copy()
    
    # Deduplicate: if a CEP matched multiple tracts, keep the first match
    result = result.drop_duplicates(subset=["cep"], keep="first")
    
    result.to_csv(OUTPUT_PATH, index=False)
    print(f"   ✓ Saved {len(result)} unique CEPs with spatial linkage data")
    
    # ── 8. Summary statistics ──────────────────────────────────────────────
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total CEPs geocoded:        {len(cache)}")
    print(f"  With valid coordinates:   {len(df_pts)}")
    print(f"  Matched to census tract:  {len(result) - result['CD_SETOR'].isna().sum()}")
    print(f"  In favela:                {result['lives_in_favela'].sum()}")
    print(f"  Not in favela:            {(result['lives_in_favela'] == 0).sum() - result['CD_SETOR'].isna().sum()}")
    print(f"  No tract match:           {result['CD_SETOR'].isna().sum()}")
    
    if result["lives_in_favela"].sum() > 0:
        print(f"\nTop favela communities matched:")
        print(result[result["lives_in_favela"] == 1]["NM_FCU"].value_counts().head(10).to_string())

if __name__ == "__main__":
    main()
