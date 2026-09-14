"""Download CNEFE GeoJSON for the 9 municipalities of the Baixada Santista (RMBS).

RMBS official composition (Lei Complementar Estadual nº 815/1996): Bertioga,
Cubatão, Guarujá, Itanhaém, Mongaguá, Peruíbe, Praia Grande, Santos, São Vicente.

Bertioga and Peruíbe have NM_CONCURB = None in IBGE 2022 shapefile (they are
not part of the contiguous urban agglomeration), so we hardcode CD_MUN here.
"""

import os, time, requests

SPATIAL = "/DATA_ROOT/WHO modelling Project/SP-TB-spatial-analyses/Data"
DEST = f"{SPATIAL}/IBGE_2022_extended/CNEFE_Baixada"
os.makedirs(DEST, exist_ok=True)

BAIXADA = [
    ("3506359", "Bertioga"),
    ("3513504", "Cubatao"),
    ("3518701", "Guaruja"),
    ("3522109", "Itanhaem"),
    ("3531100", "Mongagua"),
    ("3537602", "Peruibe"),
    ("3541000", "Praia_Grande"),
    ("3548500", "Santos"),
    ("3551009", "Sao_Vicente"),
]

BASE = ("https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/"
        "Censo_Demografico_2022/Arquivos_CNEFE/GeoJSON/Municipio_20240910/"
        "qg_810_endereco_Munic{cd_mun}.json.zip")

t0 = time.time()
total_size = 0
for i, (cd_mun, nm_mun) in enumerate(BAIXADA, 1):
    fname = f"{DEST}/cnefe_{cd_mun}_{nm_mun}.zip"
    if os.path.exists(fname) and os.path.getsize(fname) > 1000:
        size = os.path.getsize(fname)
        total_size += size
        print(f"[{i}/9] ✓ {nm_mun:<15} ({size/1e6:.1f} MB) [já baixado]")
        continue

    url = BASE.format(cd_mun=cd_mun)
    try:
        r = requests.get(url, timeout=180, stream=True)
        if r.status_code != 200:
            print(f"[{i}/9] ✗ {nm_mun:<15} HTTP {r.status_code}")
            continue
        with open(fname, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                f.write(chunk)
        size = os.path.getsize(fname)
        total_size += size
        elapsed = time.time() - t0
        print(f"[{i}/9] ✓ {nm_mun:<15} ({size/1e6:.1f} MB) "
              f"[total {total_size/1e6:.0f} MB, {elapsed/60:.1f} min]", flush=True)
    except Exception as e:
        print(f"[{i}/9] ✗ {nm_mun:<15} ERR: {e}")

print(f"\nFINAL: {total_size/1e6:.0f} MB em {(time.time()-t0)/60:.1f} min")
