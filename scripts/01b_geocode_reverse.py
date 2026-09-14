"""
Reverse geocoder - processes CEPs from the END of the list backwards.
Uses a separate cache file so it won't conflict with the Sherlock instance.
After both finish, merge the two JSON caches together.
"""
import csv
import urllib.request
import urllib.error
import ssl
import time
import json
import os

# Bypass SSL verification (common macOS Python issue)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

CSV_PATH = "Data/unique_ceps.csv"
CACHE_PATH = "Data/cep_coords_cache_reverse.json"

def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=4)

def main():
    print("Loading unique CEPs from dataset...")
    valid_ceps = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        seen = set()
        for row in reader:
            cep = str(row.get("cep", "")).strip()
            if cep and cep not in seen:
                valid_ceps.append(cep.zfill(8))
                seen.add(cep)

    # REVERSE the list so we start from the end
    valid_ceps.reverse()
    print(f"Found {len(valid_ceps)} unique valid CEPs (processing in REVERSE order).")

    cache = load_cache()
    print(f"Loaded {len(cache)} CEPs from local reverse cache.")

    ceps_to_process = [c for c in valid_ceps if c not in cache]
    print(f"Remaining CEPs to geocode: {len(ceps_to_process)}")

    if len(ceps_to_process) == 0:
        print("All CEPs geocoded!")
        return

    print("Starting REVERSE geocoding with BrasilAPI...")

    batch_size = 50
    processed = 0

    for cep in ceps_to_process:
        try:
            url = f"https://brasilapi.com.br/api/cep/v2/{cep}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as response:
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
            except urllib.error.HTTPError:
                cache[cep] = {"lat": None, "lon": None, "city": "", "bairro": ""}

            processed += 1

            if processed % batch_size == 0:
                save_cache(cache)
                print(f"[REVERSE] Processed {processed}/{len(ceps_to_process)}... Cache saved.", flush=True)

        except Exception as e:
            print(f"\nError processing CEP {cep}: {e}")
            save_cache(cache)
            time.sleep(10)
            continue

        time.sleep(1)

    save_cache(cache)
    print("\nReverse batch complete! Cache saved.")

if __name__ == "__main__":
    main()
