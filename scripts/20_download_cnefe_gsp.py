"""Download CNEFE 2022 GeoJSON files for the 37 municipalities of Greater São Paulo (GSP)."""

import os
import time
import json
import requests
import geopandas as gpd

SPATIAL = "/DATA_ROOT/Data"
DEST = f"{SPATIAL}/IBGE_2022_extended/CNEFE_GSP"
os.makedirs(DEST, exist_ok=True)

# The 37 GSP municipalities
sec = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec["CD_MUN"] = sec["CD_MUN"].astype(str)
gsp_munis = sec[sec["NM_CONCURB"] == "São Paulo/SP"][["CD_MUN", "NM_MUN"]].drop_duplicates()
print(f"GSP: {len(gsp_munis)} municipalities")

BASE = ("https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/"
        "Censo_Demografico_2022/Arquivos_CNEFE/GeoJSON/Municipio_20240910/"
        "qg_810_endereco_Munic{cd_mun}.json.zip")

t0 = time.time()
total_size = 0
for i, row in enumerate(gsp_munis.itertuples(), 1):
    cd_mun = row.CD_MUN
    nm_mun = row.NM_MUN
    fname = f"{DEST}/cnefe_{cd_mun}_{nm_mun.replace(' ','_').replace('ç','c').replace('ã','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('Ç','C').replace('Ã','A')}.zip"
    if os.path.exists(fname) and os.path.getsize(fname) > 1000:
        size = os.path.getsize(fname)
        total_size += size
        print(f"[{i:2d}/{len(gsp_munis)}] ✓ {nm_mun:<30} ({size/1e6:.1f} MB) [already downloaded]")
        continue

    url = BASE.format(cd_mun=cd_mun)
    try:
        r = requests.get(url, timeout=180, stream=True)
        if r.status_code != 200:
            print(f"[{i:2d}/{len(gsp_munis)}] ✗ {nm_mun:<30} HTTP {r.status_code}")
            continue
        with open(fname, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                f.write(chunk)
        size = os.path.getsize(fname)
        total_size += size
        elapsed = time.time() - t0
        print(f"[{i:2d}/{len(gsp_munis)}] ✓ {nm_mun:<30} ({size/1e6:.1f} MB) "
              f"[total {total_size/1e6:.0f} MB, {elapsed/60:.1f} min]", flush=True)
    except Exception as e:
        print(f"[{i:2d}/{len(gsp_munis)}] ✗ {nm_mun:<30} ERR: {e}")

print(f"\nFINAL: {total_size/1e6:.0f} MB in {(time.time()-t0)/60:.1f} min")
