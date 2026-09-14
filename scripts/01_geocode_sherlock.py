import csv
import urllib.request
import urllib.error
import time
import json
import os

CSV_PATH = "unique_ceps.csv"
CACHE_PATH = "cep_coords_cache.json"

def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=4)

def main():
    if not os.path.exists(CSV_PATH):
        print(f"Error: Could not find {CSV_PATH}. Make sure it is in the same directory.")
        return

    print("Loading unique CEPs from dataset...")
    valid_ceps = set()
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cep = str(row.get("cep", "")).strip()
            if cep:
                valid_ceps.add(cep.zfill(8))
    valid_ceps = list(valid_ceps)
    print(f"Found {len(valid_ceps)} unique valid CEPs in CSV.")

    cache = load_cache()
    print(f"Loaded {len(cache)} CEPs from cache.")

    # Find CEPs we still need to process
    ceps_to_process = [c for c in valid_ceps if c not in cache]
    print(f"Remaining CEPs to geocode: {len(ceps_to_process)}")

    if len(ceps_to_process) == 0:
        print("All CEPs geocoded! The JSON cache is complete.")
        return

    print("Starting geocoding process with BrasilAPI...")
    
    batch_size = 50
    processed = 0

    for cep in ceps_to_process:
        try:
            url = f"https://brasilapi.com.br/api/cep/v2/{cep}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode())
                        location = data.get("location", {}).get("coordinates", {})
                        lat = location.get("latitude")
                        lon = location.get("longitude")
                        
                        cache[cep] = {
                            "lat": lat,
                            "lon": lon,
                            "city": data.get("city", ""),
                            "bairro": data.get("neighborhood", "")
                        }
            except urllib.error.HTTPError as e:
                cache[cep] = {"lat": None, "lon": None, "city": "", "bairro": ""}
                
            processed += 1
            
            if processed % batch_size == 0:
                save_cache(cache)
                print(f"Processed {processed}/{len(ceps_to_process)}... Cache saved.", flush=True)
                
        except Exception as e:
            print(f"\nError processing CEP {cep}: {e}")
            print("Saving cache and pausing...")
            save_cache(cache)
            time.sleep(10)
            continue
            
        time.sleep(1)
        
    save_cache(cache)
    print("\nBatch complete! Cache saved. You can now transfer cep_coords_cache.json back.")

if __name__ == "__main__":
    main()
