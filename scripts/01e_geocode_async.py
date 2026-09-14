import asyncio
import aiohttp
import json
import csv
import sys
import os
import time

MASTER_JSON = "Data/cep_coords_MASTER.json"
CEP_LIST = "Data/unique_ceps.csv"
CONCURRENCY_LIMIT = 50

# Global counters
processed = 0
found = 0
not_found = 0
errors = 0
total_needed = 0

async def fetch_cep(session, cep, semaphore, master_dict):
    global processed, found, not_found, errors
    
    url = f"https://brasilapi.com.br/api/cep/v2/{cep}"
    
    async with semaphore:
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    location = data.get("location", {}).get("coordinates", {})
                    lat = location.get("latitude")
                    lon = location.get("longitude")
                    
                    if lat and lon:
                        master_dict[cep] = {
                            "lat": float(lat),
                            "lon": float(lon),
                            "city": data.get("city", ""),
                            "bairro": data.get("neighborhood", "")
                        }
                        found += 1
                    else:
                        master_dict[cep] = {"lat": None, "lon": None, "city": data.get("city", ""), "bairro": data.get("neighborhood", "")}
                        not_found += 1
                elif response.status == 404:
                    # Invalid CEP
                    master_dict[cep] = {"lat": None, "lon": None, "city": "", "bairro": ""}
                    not_found += 1
                elif response.status == 429:
                    # Rate limited - we'll catch these as errors to retry later
                    errors += 1
                else:
                    errors += 1
                    
        except Exception as e:
            errors += 1
            
        processed += 1
        
        # Periodic terminal updates
        if processed % 500 == 0:
            pct = (processed / total_needed) * 100
            print(f"[{pct:.1f}%] Processed {processed}/{total_needed} | Found coords: {found} | No coords/404: {not_found} | Errors: {errors}")

        # Save to disk every 1000 records to prevent total loss on crash
        if processed % 1000 == 0:
            with open(MASTER_JSON, "w") as f:
                json.dump(master_dict, f)

async def main():
    global total_needed
    print("1. Loading existing master cache...")
    if os.path.exists(MASTER_JSON):
        with open(MASTER_JSON, "r") as f:
            master = json.load(f)
    else:
        master = {}
        
    valid_ceps_so_far = sum(1 for v in master.values() if v.get("lat") is not None)
    print(f"   ✓ Loaded {len(master)} existing cache entries ({valid_ceps_so_far} have coordinates)")
    
    print("\n2. Identifying pending CEPs...")
    all_ceps = []
    with open(CEP_LIST, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_ceps.append(row["cep"].strip().zfill(8))
            
    # Need to process if it's not in master OR if it's in master but we flagged an error (None) but want to retry?
    # Actually, we shouldn't retry 404s endlessly. We only process if it is strictly completely missing from master keys.
    missing_ceps = [c for c in all_ceps if c not in master]
    total_needed = len(missing_ceps)
    
    print(f"   ✓ {len(all_ceps)} total unique CEPs in cohort")
    print(f"   ✓ {total_needed} CEPs have never been processed and need fetching now")
    
    if total_needed == 0:
        print("\nAll CEPs are already processed! Exiting.")
        return

    print(f"\n3. Launching Asynchronous Swarm (Concurrency = {CONCURRENCY_LIMIT})...")
    start_time = time.time()
    
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        # Create all task coroutines
        tasks = [fetch_cep(session, cep, semaphore, master) for cep in missing_ceps]
        
        # Run them
        await asyncio.gather(*tasks)

    # Final save
    print("\n4. Finalizing and saving cache...")
    with open(MASTER_JSON, "w") as f:
        json.dump(master, f)
        
    elapsed = time.time() - start_time
    print(f"\n===========================================================")
    print(f"ASYNC SWARM COMPLETE in {elapsed:.1f} seconds ({(total_needed/elapsed):.1f} req/sec)")
    print(f"===========================================================")
    print(f"Total processed: {processed}")
    print(f"Successfully geocoded: {found}")
    print(f"No coordinates / 404: {not_found}")
    print(f"Failed / Rate limited: {errors}")
    print(f"\nMaster JSON updated. You can re-run spatial intersection now!")

if __name__ == "__main__":
    # Prevent aiohttp windows errors on mac
    if sys.platform == "darwin":
        import selectors
        selector = selectors.SelectSelector()
        loop = asyncio.SelectorEventLoop(selector)
        asyncio.set_event_loop(loop)
    asyncio.run(main())
