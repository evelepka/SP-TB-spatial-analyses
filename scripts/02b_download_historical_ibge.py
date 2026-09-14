import os
try:
    from geobr import read_census_tract
    import geopandas as gpd
except ImportError:
    print("Please install geobr and geopandas: pip install geobr geopandas")
    exit(1)

OUTPUT_DIR = "Data/SP_setores_2010"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "SP_Setores_2010.shp")

def main():
    print("Downloading IBGE 2010 Census Tracts for São Paulo (State)...")
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    try:
        # Fetching the entire São Paulo state census tracts for 2010
        sp_tracts_2010 = read_census_tract(code_muni="SP", year=2010)
        
        print(f"Successfully downloaded {len(sp_tracts_2010)} census tracts. Saving to {OUTPUT_FILE}...")
        
        # Save output to shapefile
        sp_tracts_2010.to_file(OUTPUT_FILE)
        
        print("IBGE 2010 Shapefile Saved!")
        print("Note: When preparing for intersection, you will filter this by the 'TIPO' or 'nome_tipo_setor' column == 'Aglomerado Subnormal'")
        
    except Exception as e:
        print(f"Error fetching IBGE 2010 data: {e}")

if __name__ == "__main__":
    main()
