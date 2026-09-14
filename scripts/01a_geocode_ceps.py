import pandas as pd
import requests
import time
import json
import os

EXCEL_PATH = "/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/.shortcut-targets-by-id/1WMps9BoKmDA6_Lzak12042gQKkXVI4qg/WHO modelling Project/Data/TBWeb_20250328_endereco.xlsx"
CACHE_PATH = "/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/Abandonment Paper/Data/cep_coords_cache.json"

def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=4)

def clean_cep(cep_series):
    # Remove non-numeric, drop na, and pad with leading zeros to 8 chars
    s = cep_series.astype(str).str.replace(r"[^\d]", "", regex=True)
    # Only keep those that are numeric and not empty
    s = s[s != "nan"]
    s = s[s != ""]
    return s.str.zfill(8)

def main():
    print("Loading unique CEPs from dataset...")
    df = pd.read_excel(EXCEL_PATH, usecols=["cep"])
    valid_ceps = clean_cep(df["cep"]).unique()
    print(f"Found {len(valid_ceps)} unique valid CEPs.")

    cache = load_cache()
    print(f"Loaded {len(cache)} CEPs from cache.")

    # Find CEPs we still need to process
    ceps_to_process = [c for c in valid_ceps if c not in cache]
    print(f"Remaining CEPs to geocode: {len(ceps_to_process)}")

    if len(ceps_to_process) == 0:
        print("All CEPs geocoded!")
        return

    print("Starting geocoding process with BrasilAPI...")
    
    # We will save the cache every 50 records to prevent data loss on interruption
    batch_size = 50
    processed = 0

    for cep in ceps_to_process:
        try:
            url = f"https://brasilapi.com.br/api/cep/v2/{cep}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                location = data.get("location", {}).get("coordinates", {})
                lat = location.get("latitude")
                lon = location.get("longitude")
                
                # We save regardless of whether lat/lon is found, to avoid retrying a bad CEP
                cache[cep] = {
                    "lat": lat,
                    "lon": lon,
                    "city": data.get("city", ""),
                    "bairro": data.get("neighborhood", "")
                }
            else:
                # 404 means not found; mark as None to avoid infinite retries
                cache[cep] = {"lat": None, "lon": None, "city": "", "bairro": ""}
                
            processed += 1
            
            # Save periodic checkpoints
            if processed % batch_size == 0:
                save_cache(cache)
                print(f"Processed {processed}/{len(ceps_to_process)}... Cache saved.")
                
        except Exception as e:
            print(f"\nError processing CEP {cep}: {e}")
            print("Saving cache and pausing...")
            save_cache(cache)
            time.sleep(10) # Pause longer on exceptions
            continue
            
        # polite rate limiting for BrasilAPI
        time.sleep(1)
        
    # Final save
    save_cache(cache)
    print("\nBatch complete! Cache saved.")

if __name__ == "__main__":
    main()
