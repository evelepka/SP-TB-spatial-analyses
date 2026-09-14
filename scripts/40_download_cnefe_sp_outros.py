"""Download CNEFE GeoJSON for SP-state municipalities outside GSP and Baixada Santista.

Only downloads files for municipalities that have TB cases in the cohort
(NOVO+RECIDIVA, 2020-2024, ENDERECO PADRAO), to avoid fetching hundreds of
tiny municipalities with no cases.
"""

import os
import re
import time
import unicodedata
import pandas as pd
import geopandas as gpd
import requests

SPATIAL = "/DATA_ROOT/WHO modelling Project/SP-TB-spatial-analyses/Data"
WHO_DATA = "/DATA_ROOT/WHO modelling Project/Data"
DEST = f"{SPATIAL}/IBGE_2022_extended/CNEFE_SP_outros"
os.makedirs(DEST, exist_ok=True)

BASE = ("https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/"
        "Censo_Demografico_2022/Arquivos_CNEFE/GeoJSON/Municipio_20240910/"
        "qg_810_endereco_Munic{cd_mun}.json.zip")

GSP_SET = None  # filled below
BAIXADA = {"3506359", "3513504", "3518701", "3522109", "3531100",
           "3537602", "3541000", "3548500", "3551009"}


def norm_text(s):
    if pd.isna(s):
        return None
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s)


def to_sinan(x, width=11):
    if pd.isna(x):
        return None
    try:
        return f"{int(float(x)):0{width}d}"
    except (ValueError, TypeError):
        return None


# ── 1. Build SP outros municipality list from shapefile ──────────────────────
print("Loading shapefile...")
sec = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec["CD_MUN"] = sec["CD_MUN"].astype(str)
all_munis = sec[["CD_MUN", "NM_MUN"]].drop_duplicates()

GSP_SET = set(sec[sec["NM_CONCURB"] == "São Paulo/SP"]["CD_MUN"].unique())
sp_outros_df = all_munis[~all_munis["CD_MUN"].isin(GSP_SET | BAIXADA)]
sp_outros_set = set(sp_outros_df["CD_MUN"])
print(f"SP outros: {len(sp_outros_set)} municípios (excl. {len(GSP_SET)} GSP + {len(BAIXADA)} Baixada)")

# ── 2. Filter cohort to find case-bearing municipalities ──────────────────────
print("Loading cohort to find case-bearing municipalities...")
mun_to_cd = sec.drop_duplicates("CD_MUN").set_index(
    sec.drop_duplicates("CD_MUN")["NM_MUN"].apply(norm_text)
)["CD_MUN"]

cohort = pd.read_csv(
    f"{SPATIAL}/cohort_with_spatial.csv",
    usecols=["sinan_padded", "address_type", "case_type", "notification_date"],
    low_memory=False,
)
cohort["year"] = pd.to_datetime(cohort["notification_date"], errors="coerce").dt.year
cohort["sinan_key"] = cohort["sinan_padded"].apply(to_sinan)

end = pd.read_excel(
    f"{WHO_DATA}/TBWeb_20250328_endereco.xlsx",
    usecols=["SINAN", "munResid"],
)
end["sinan_key"] = end["SINAN"].apply(to_sinan)
end_d = end.dropna(subset=["sinan_key"]).drop_duplicates("sinan_key")
cohort = cohort.merge(end_d[["sinan_key", "munResid"]], on="sinan_key", how="left")
cohort["cd_mun"] = cohort["munResid"].apply(norm_text).map(mun_to_cd)

active = (
    cohort[
        (cohort["address_type"] == "ENDERECO PADRAO")
        & cohort["case_type"].astype(str).str.strip().str.upper().isin(["NOVO", "RECIDIVA"])
        & cohort["year"].between(2020, 2024)
        & cohort["cd_mun"].isin(sp_outros_set)
    ]["cd_mun"]
    .dropna()
    .unique()
)
active_set = set(active)
print(f"Case-bearing SP outros municipalities: {len(active_set)} (out of {len(sp_outros_set)} total)")

# Build cd_mun → NM_MUN map
cd_to_nm = sp_outros_df.set_index("CD_MUN")["NM_MUN"].to_dict()
download_list = sorted([(cd, cd_to_nm.get(cd, cd)) for cd in active_set], key=lambda x: x[0])

# ── 3. Download ───────────────────────────────────────────────────────────────
t0 = time.time()
total_size = 0
n_skipped = n_ok = n_err = 0

print(f"\nDownloading {len(download_list)} CNEFE files → {DEST}")
for i, (cd_mun, nm_mun) in enumerate(download_list, 1):
    safe_name = (
        nm_mun.replace(" ", "_")
        .replace("ç", "c").replace("Ç", "C")
        .replace("ã", "a").replace("Ã", "A")
        .replace("â", "a").replace("Â", "A")
        .replace("á", "a").replace("Á", "A")
        .replace("à", "a").replace("À", "A")
        .replace("ê", "e").replace("Ê", "E")
        .replace("é", "e").replace("É", "E")
        .replace("í", "i").replace("Í", "I")
        .replace("ô", "o").replace("Ô", "O")
        .replace("ó", "o").replace("Ó", "O")
        .replace("õ", "o").replace("Õ", "O")
        .replace("ú", "u").replace("Ú", "U")
        .replace("ü", "u").replace("Ü", "U")
    )
    fname = f"{DEST}/cnefe_{cd_mun}_{safe_name}.zip"

    if os.path.exists(fname) and os.path.getsize(fname) > 1000:
        size = os.path.getsize(fname)
        total_size += size
        print(f"[{i:3d}/{len(download_list)}] skip {nm_mun:<35} ({size/1e6:.1f} MB)", flush=True)
        n_skipped += 1
        continue

    url = BASE.format(cd_mun=cd_mun)
    try:
        r = requests.get(url, timeout=180, stream=True)
        if r.status_code != 200:
            print(f"[{i:3d}/{len(download_list)}] ERR  {nm_mun:<35} HTTP {r.status_code}", flush=True)
            n_err += 1
            continue
        with open(fname, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                f.write(chunk)
        size = os.path.getsize(fname)
        total_size += size
        elapsed = time.time() - t0
        rate = total_size / elapsed / 1e6 if elapsed > 0 else 0
        print(
            f"[{i:3d}/{len(download_list)}] OK   {nm_mun:<35} ({size/1e6:.1f} MB) "
            f"[total {total_size/1e6:.0f} MB, {elapsed/60:.1f} min, {rate:.1f} MB/s]",
            flush=True,
        )
        n_ok += 1
    except Exception as e:
        print(f"[{i:3d}/{len(download_list)}] ERR  {nm_mun:<35} {e}", flush=True)
        n_err += 1

elapsed_total = time.time() - t0
print(f"\nDONE: {n_ok} downloaded, {n_skipped} skipped, {n_err} errors")
print(f"Total size: {total_size/1e6:.0f} MB in {elapsed_total/60:.1f} min")
