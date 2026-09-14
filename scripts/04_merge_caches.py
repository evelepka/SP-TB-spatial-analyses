"""
Script to merge all parallel geocoding cache files into one definitive dictionary/CSV.
It prioritizes high-accuracy coordinate hits from BrasilAPI over "misses" or fast-geocoder approximated centroids.
"""
import json
import os
import csv

def load_cache(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {filepath} might be corrupted.")
    return {}

def merge_caches():
    # List of all expected cache files from the 6 workers
    cache_files = [
        "cep_coords_cache.json",           # Original forward
        "cep_cache_chunk_1.json",          # Chunk 1
        "cep_cache_chunk_2.json",          # Chunk 2
        "cep_cache_chunk_3.json",          # Chunk 3
        "cep_coords_cache_reverse.json",   # Local Mac reverse
        "cep_coords_fast.json"             # Fast bulk geocoder (fallback)
    ]
    
    master_cache = {}
    
    for file in cache_files:
        print(f"Loading {file}...")
        cache = load_cache(file)
        
        for cep, data in cache.items():
            # Only add if the current master doesn't have it, OR if the new data is "better"
            # (e.g. replacing a null/miss with a real lat/lon)
            if cep not in master_cache:
                master_cache[cep] = data
            elif master_cache[cep].get("lat") is None and data.get("lat") is not None:
                # Replace an empty placeholder with a successful hit!
                master_cache[cep] = data
                
    valid_hits = sum(1 for v in master_cache.values() if v.get("lat") is not None)
    print(f"\nMerge Complete!")
    print(f"Total Unique CEPs in Master Cache: {len(master_cache)}")
    print(f"Total with valid geographic coordinates: {valid_hits}")
    print(f"Coverage: {(valid_hits / max(len(master_cache), 1)) * 100:.2f}%\n")
    
    # Save unified JSON
    with open("cep_coords_MASTER.json", "w") as f:
        json.dump(master_cache, f, indent=4)
        
    # Also save as a friendly CSV for R/survival models
    with open("cep_coords_MASTER.csv", "w", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["cep", "lat", "lon", "city", "bairro", "source"])
        for cep, data in master_cache.items():
            writer.writerow([
                cep, 
                data.get("lat", ""), 
                data.get("lon", ""), 
                data.get("city", ""), 
                data.get("bairro", ""),
                data.get("source", "brasilapi")
            ])
            
    print("Saved 'cep_coords_MASTER.json' and 'cep_coords_MASTER.csv'. Ready for spatial intersection!")

if __name__ == "__main__":
    merge_caches()
