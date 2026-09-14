"""
Parallel chunk geocoder - processes a specific subset of CEPs from a text file.
Usage: python3 01c_geocode_chunk.py chunk_1_ceps.txt cep_cache_chunk_1.json
"""
import sys
import urllib.request
import urllib.error
import time
import json
import os

def load_cache(cache_path):
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache, cache_path):
    with open(cache_path, "w") as f:
        json.dump(cache, f)

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 01c_geocode_chunk.py <chunk_file> <cache_file>")
        sys.exit(1)
    
    chunk_file = sys.argv[1]
    cache_path = sys.argv[2]
    
    # Load CEPs from chunk file
    with open(chunk_file, "r") as f:
        ceps = [line.strip() for line in f if line.strip()]
    
    cache = load_cache(cache_path)
    print(f"Chunk: {chunk_file} | Total: {len(ceps)} | Already cached: {len(cache)}")
    
    remaining = [c for c in ceps if c not in cache]
    print(f"Remaining to process: {len(remaining)}")
    
    if not remaining:
        print("All done!")
        return
    
    batch_size = 50
    processed = 0
    
    for cep in remaining:
        try:
            url = f"https://brasilapi.com.br/api/cep/v2/{cep}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode())
                        location = data.get("location", {}).get("coordinates", {})
                        cache[cep] = {
                            "lat": location.get("latitude"),
                            "lon": location.get("longitude"),
                            "city": data.get("city", ""),
                            "bairro": data.get("neighborhood", "")
                        }
            except urllib.error.HTTPError:
                cache[cep] = {"lat": None, "lon": None, "city": "", "bairro": ""}
            
            processed += 1
            if processed % batch_size == 0:
                save_cache(cache, cache_path)
                print(f"[{chunk_file}] Processed {processed}/{len(remaining)}... Cache saved.", flush=True)
        
        except Exception as e:
            print(f"Error processing CEP {cep}: {e}")
            save_cache(cache, cache_path)
            time.sleep(10)
            continue
        
        time.sleep(1)
    
    save_cache(cache, cache_path)
    print(f"\n[{chunk_file}] Complete! Processed {processed} CEPs.")

if __name__ == "__main__":
    main()
