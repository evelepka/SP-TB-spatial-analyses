"""
Fast bulk geocoder using municipality centroids.
Strategy:
  1. Download the kelvins/municipios-brasileiros CSV (5,570 municipalities with lat/lon)
  2. Use ViaCEP (extremely fast, no documented rate limit) to map each CEP -> IBGE municipality code
  3. Look up the municipality centroid from the CSV

This gives us municipality-level coordinates in seconds rather than days.
We can later validate against our BrasilAPI results and use those where available for higher precision.
"""
import csv
import urllib.request
import urllib.error
import ssl
import json
import time
import os

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

MUNICIPIOS_URL = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"
UNIQUE_CEPS_PATH = "unique_ceps.csv"
CACHE_PATH = "cep_coords_fast.json"

def download_municipios():
    """Download municipality centroid database."""
    print("Downloading municipality centroid database...")
    req = urllib.request.Request(MUNICIPIOS_URL, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=30, context=SSL_CTX)
    lines = resp.read().decode('utf-8').split('\n')
    
    muni_db = {}
    reader = csv.DictReader(lines)
    for row in reader:
        ibge_code = row.get('codigo_ibge', '').strip()
        if ibge_code:
            muni_db[ibge_code] = {
                'lat': float(row['latitude']),
                'lon': float(row['longitude']),
                'city': row.get('nome', '')
            }
    print(f"Loaded {len(muni_db)} municipality centroids.")
    return muni_db

def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f)

def main():
    muni_db = download_municipios()
    
    # Load unique CEPs
    all_ceps = []
    seen = set()
    with open(UNIQUE_CEPS_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cep = str(row.get("cep", "")).strip().zfill(8)
            if cep and cep not in seen:
                all_ceps.append(cep)
                seen.add(cep)
    
    print(f"Total unique CEPs: {len(all_ceps)}")
    
    cache = load_cache()
    remaining = [c for c in all_ceps if c not in cache]
    print(f"Already cached: {len(cache)}, Remaining: {len(remaining)}")
    
    if not remaining:
        print("All CEPs already processed!")
        return
    
    processed = 0
    hits = 0
    misses = 0
    
    for cep in remaining:
        try:
            # ViaCEP returns IBGE code very quickly
            url = f"https://viacep.com.br/ws/{cep}/json/"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=10, context=SSL_CTX)
            data = json.loads(resp.read().decode())
            
            if data.get("erro"):
                cache[cep] = {"lat": None, "lon": None, "city": "", "bairro": "", "source": "viacep_not_found"}
                misses += 1
            else:
                ibge_code = data.get("ibge", "")
                bairro = data.get("bairro", "")
                city = data.get("localidade", "")
                
                if ibge_code in muni_db:
                    coords = muni_db[ibge_code]
                    cache[cep] = {
                        "lat": coords['lat'],
                        "lon": coords['lon'],
                        "city": city,
                        "bairro": bairro,
                        "source": "municipality_centroid",
                        "ibge_code": ibge_code
                    }
                    hits += 1
                else:
                    cache[cep] = {"lat": None, "lon": None, "city": city, "bairro": bairro, "source": "ibge_not_in_db"}
                    misses += 1
        
        except Exception as e:
            cache[cep] = {"lat": None, "lon": None, "city": "", "bairro": "", "source": f"error: {str(e)}"}
            misses += 1
        
        processed += 1
        
        if processed % 100 == 0:
            save_cache(cache)
            print(f"Processed {processed}/{len(remaining)} | Hits: {hits} | Misses: {misses}", flush=True)
        
        # ViaCEP is fast but let's be polite - 0.2s delay
        time.sleep(0.2)
    
    save_cache(cache)
    print(f"\nDone! Total processed: {processed}, Hits: {hits}, Misses: {misses}")
    print(f"Cache saved to {CACHE_PATH}")

if __name__ == "__main__":
    main()
