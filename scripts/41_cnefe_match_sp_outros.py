"""CNEFE matching for SP-state municipalities outside GSP and Baixada Santista.

Phase 1: Build per-municipality index CSVs from CNEFE GeoJSON zips.
Phase 2: Match TBweb addresses to CNEFE using a 4-tier cascade:
  T1: exact (rua_norm, num_norm)
  T2: rua only (most frequent entry)
  T3: fuzzy match via rapidfuzz token_set_ratio >= 88
  T4: bairro fallback (fuzzy bairro match >= 85, assign centroid setor)
"""

import os
import json
import re
import time
import unicodedata
import zipfile
from collections import defaultdict, Counter
import statistics

import pandas as pd
import geopandas as gpd
from rapidfuzz import fuzz, process

SPATIAL = "/DATA_ROOT/Data"
WHO_DATA = "/DATA_ROOT/TBWeb"
CNEFE_DIR = f"{SPATIAL}/IBGE_2022_extended/CNEFE_SP_outros"
INDEX_DIR = f"{CNEFE_DIR}/indices"
os.makedirs(INDEX_DIR, exist_ok=True)

BAIXADA = {"3506359", "3513504", "3518701", "3522109", "3531100",
           "3537602", "3541000", "3548500", "3551009"}

# ── Normalization helpers (reused from 29b) ──────────────────────────────────

TYPO_MAP = {
    "MORRIHOS": "MORRINHOS",
    "SARAYVA": "SARAIVA",
    "DEALBUQUERQUE": "DE ALBUQUERQUE",
    "BRUZARROSCO": "BRUZZAROSCO",
    "CACHETAS": "CACHETA",
}

COMPLEMENT_PATTERNS = [
    r"\s+(BLOCO|BL|BLC)\s*\d+.*$",
    r"\s+(APTO|APT|AP)\s*\d+.*$",
    r"\s+(QUADRA|QD|QUAD)\s*\d+.*$",
    r"\s+(LOTE|LT|LOTES?)\s*\d+.*$",
    r"\s+(CASA|CS)\s*\d+.*$",
    r"\s+(CONJ|CONJUNTO)\s*\d+.*$",
    r"\s+KM\s*\d+.*$",
    r"\s+(PREDIO|PRED)\s+\d+.*$",
    r"\s+(PROX|PROXIMO|JUNTO)\s+.*$",
    r"\s+(VIELA)\s+.*$",
    r"\s+(EDIFICIO|EDIF)\s+.*$",
]
COMPL_RE = re.compile("|".join(COMPLEMENT_PATTERNS), re.IGNORECASE)

ORDINAL_RUA_RE = re.compile(r"^(\d+)\s*([AABNOSPÃª])?\s+RUA\s+", re.IGNORECASE)
EMBED_NUM_RE = re.compile(r"\s+(\d{1,5})$")

STREET_PREFIX_RE = re.compile(
    r"^(RUA RUA|RUA|R\.?|AV\.?|AVENIDA|TV\.?|TRAVESSA|ROD\.?|RODOVIA|"
    r"EST\.?|ESTRADA|AL\.?|ALAMEDA|PR\.?|PRACA|PRAÇA|"
    r"VIA|ACESSO|VL|VILA|BECO|LARGO|CAMINHO|CAM|VIELA|"
    r"MARGINAL|SERVIDAO|SERV)\s+",
    re.IGNORECASE,
)

FAVELA_HINT_RE = re.compile(r"^(FAVELA|COMUNIDADE|NUCLEO)\s+", re.IGNORECASE)


def strip_accents(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def normalize_street_v2(s, num_end=None):
    """Returns (normalized_street, extracted_num_or_None, is_favela_hint)"""
    if not s or pd.isna(s):
        return None, None, False
    s = str(s).strip().upper()
    s = strip_accents(s)

    is_favela = bool(FAVELA_HINT_RE.match(s))

    s = COMPL_RE.sub("", s)

    ordinal_match = ORDINAL_RUA_RE.match(s)
    ordinal_prefix = ""
    if ordinal_match:
        ordinal_prefix = ordinal_match.group(1) + "A "
        s = ORDINAL_RUA_RE.sub("", s)

    s = STREET_PREFIX_RE.sub("", s)

    extracted_num = None
    if num_end is None or pd.isna(num_end) or str(num_end).strip() in ("", "S/N", "SN", "NAN"):
        m = EMBED_NUM_RE.search(s)
        if m:
            extracted_num = int(m.group(1))
            s = EMBED_NUM_RE.sub("", s).strip()

    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    for typo, correct in TYPO_MAP.items():
        s = re.sub(rf"\b{typo}\b", correct, s)

    s = (ordinal_prefix + s).strip() if ordinal_prefix else s

    return (s if s else None, extracted_num, is_favela)


def normalize_num(x):
    if x is None or pd.isna(x):
        return None
    try:
        n = int(float(str(x).strip().split()[0]))
        return n if n > 0 else None
    except (ValueError, TypeError, IndexError):
        return None


def norm_text(s):
    if pd.isna(s):
        return None
    s = str(s).strip().upper()
    s = strip_accents(s)
    return re.sub(r"\s+", " ", s)


def to_sinan(x, width=11):
    if pd.isna(x):
        return None
    try:
        return f"{int(float(x)):0{width}d}"
    except (ValueError, TypeError):
        return None


# ── Phase 1: Build per-municipality index CSVs ───────────────────────────────
print("=" * 60)
print("Phase 1: Building CNEFE municipal indices")
print("=" * 60)
t0 = time.time()

zip_files = sorted([f for f in os.listdir(CNEFE_DIR) if f.endswith(".zip")])
print(f"Found {len(zip_files)} CNEFE zip files in {CNEFE_DIR}")

muni_index_paths = {}

for i, fname in enumerate(zip_files, 1):
    fpath = os.path.join(CNEFE_DIR, fname)
    # filename pattern: cnefe_XXXXXXX_NOME.zip
    cd_mun = fname.split("_")[1]
    out_path = f"{INDEX_DIR}/idx_{cd_mun}.csv"

    if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
        muni_index_paths[cd_mun] = out_path
        print(f"  [{i:3d}/{len(zip_files)}] {cd_mun} skip (index exists)", flush=True)
        continue

    try:
        with zipfile.ZipFile(fpath) as z:
            inner = z.namelist()[0]
            with z.open(inner) as f:
                data = json.load(f)
    except Exception as e:
        print(f"  [{i:3d}/{len(zip_files)}] {cd_mun} ERR reading zip: {e}", flush=True)
        continue

    # Accumulate by (rua, num)
    by_key = defaultdict(lambda: {"bairros": [], "setores": [], "lats": [], "lons": []})
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        if str(props.get("COD_ESPECIE")) != "1":
            continue
        lograd = props.get("LOGRAD_NUM", "")
        if "," in lograd:
            rua_part, num_part = lograd.split(",", 1)
        else:
            rua_part = lograd
            num_part = ""
        # Use normalize_street_v2 (same as matching phase)
        rua_n, _, _ = normalize_street_v2(rua_part)
        if not rua_n:
            continue
        num_n = normalize_num(num_part)
        bairro = props.get("DSC_LOCALIDADE")
        setor = props.get("COD_SETOR")
        coords = feat.get("geometry", {}).get("coordinates", [None, None])
        lon = coords[0] if len(coords) > 0 else None
        lat = coords[1] if len(coords) > 1 else None
        if not bairro:
            continue
        key = (rua_n, num_n)
        by_key[key]["bairros"].append(bairro)
        by_key[key]["setores"].append(setor)
        if lat is not None:
            by_key[key]["lats"].append(lat)
        if lon is not None:
            by_key[key]["lons"].append(lon)

    # Reduce: mode/median per key
    rows = []
    for (rua, num), vals in by_key.items():
        bairro = Counter(vals["bairros"]).most_common(1)[0][0]
        setor = Counter(vals["setores"]).most_common(1)[0][0] if vals["setores"] else None
        lat = statistics.median(vals["lats"]) if vals["lats"] else None
        lon = statistics.median(vals["lons"]) if vals["lons"] else None
        rows.append([rua, num, bairro, setor, lat, lon, len(vals["bairros"])])

    df = pd.DataFrame(rows, columns=["rua", "num", "bairro", "setor", "lat", "lon", "n"])
    df.to_csv(out_path, index=False)
    muni_index_paths[cd_mun] = out_path
    elapsed = time.time() - t0
    print(
        f"  [{i:3d}/{len(zip_files)}] {cd_mun} → {len(df):,} unique entries "
        f"({elapsed/60:.1f} min total)",
        flush=True,
    )

print(f"\nPhase 1 done: {len(muni_index_paths)} indices in {(time.time()-t0)/60:.1f} min")

# ── Phase 2: Load cohort + matching ─────────────────────────────────────────
print("\n" + "=" * 60)
print("Phase 2: Loading cohort + address matching")
print("=" * 60)

# Determine SP outros set from shapefile
print("Loading shapefile...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"] = sec22["CD_MUN"].astype(str)
all_munis = sec22[["CD_MUN", "NM_MUN"]].drop_duplicates()
gsp_set = set(sec22[sec22["NM_CONCURB"] == "São Paulo/SP"]["CD_MUN"].unique())
sp_outros_set = set(all_munis[~all_munis["CD_MUN"].isin(gsp_set | BAIXADA)]["CD_MUN"])

mun_to_cd = sec22.drop_duplicates("CD_MUN").set_index(
    sec22.drop_duplicates("CD_MUN")["NM_MUN"].apply(norm_text)
)["CD_MUN"]

print("Loading cohort + addresses...")
cohort = pd.read_csv(
    f"{SPATIAL}/cohort_with_spatial.csv",
    usecols=["sinan_clean", "sinan_padded", "address_type", "case_type", "notification_date"],
    low_memory=False,
)
cohort["sinan_key"] = cohort["sinan_padded"].apply(to_sinan)
cohort["year"] = pd.to_datetime(cohort["notification_date"], errors="coerce").dt.year

end = pd.read_excel(
    f"{WHO_DATA}/TBWeb_20250328_endereco.xlsx",
    usecols=["SINAN", "endereco", "numEnd", "bairro", "munResid"],
)
end["sinan_key"] = end["SINAN"].apply(to_sinan)
end_d = end.dropna(subset=["sinan_key"]).drop_duplicates("sinan_key")
cohort = cohort.merge(
    end_d[["sinan_key", "endereco", "numEnd", "bairro", "munResid"]],
    on="sinan_key",
    how="left",
)
cohort["cd_mun"] = cohort["munResid"].apply(norm_text).map(mun_to_cd)

# Filter to SP outros, 2013-2024, NOVO+RECIDIVA, ENDERECO PADRAO
work = cohort[
    (cohort["address_type"] == "ENDERECO PADRAO")
    & cohort["case_type"].astype(str).str.strip().str.upper().isin(["NOVO", "RECIDIVA"])
    & cohort["year"].between(2013, 2024)
    & cohort["cd_mun"].isin(sp_outros_set)
].copy()
print(f"  SP outros cohort 2013-2024: {len(work):,} cases")

# Normalize addresses
norm_results = work.apply(
    lambda r: normalize_street_v2(r["endereco"], r["numEnd"]), axis=1
)
work["rua_norm2"] = [r[0] for r in norm_results]
work["num_extracted"] = [r[1] for r in norm_results]
work["is_favela_hint"] = [r[2] for r in norm_results]
work["num_norm"] = work["numEnd"].apply(normalize_num).fillna(work["num_extracted"])
work["num_norm"] = work["num_norm"].apply(lambda x: int(x) if pd.notna(x) else None)

print(f"  Embedded numbers recovered: {work['num_extracted'].notna().sum():,}")
print(f"  Favela-hint addresses:      {work['is_favela_hint'].sum():,}")

# ── Build per-municipality lookup structures ─────────────────────────────────
print("\nBuilding lookup structures...")
mun_data = {}
for cd_mun, path in muni_index_paths.items():
    if cd_mun not in sp_outros_set:
        continue
    try:
        idx_df = pd.read_csv(path)
    except Exception:
        continue
    by_key = {(r.rua, r.num): r for r in idx_df.itertuples(index=False)}
    by_rua = (
        idx_df.sort_values("n", ascending=False)
        .drop_duplicates("rua")
        .set_index("rua")
        .to_dict(orient="index")
    )
    rua_list = list(by_rua.keys())
    by_bairro = (
        idx_df.dropna(subset=["bairro"])
        .groupby("bairro")
        .agg(
            setor=("setor", lambda x: x.mode().iloc[0] if not x.mode().empty else None),
            lat=("lat", "median"),
            lon=("lon", "median"),
            n=("n", "sum"),
        )
        .to_dict(orient="index")
    )
    bairro_norm_map = {norm_text(k): k for k in by_bairro}
    mun_data[cd_mun] = {
        "by_key": by_key,
        "by_rua": by_rua,
        "rua_list": rua_list,
        "by_bairro": by_bairro,
        "bairro_norm_map": bairro_norm_map,
    }
print(f"  {len(mun_data)} municipalities ready for matching")

# ── Matching cascade ─────────────────────────────────────────────────────────
print("\nMatching cascade (T1=exact, T2=rua, T3=fuzzy, T4=bairro_fallback)...")

result_cols = ["bairro_cnefe", "setor_cnefe", "lat_cnefe", "lon_cnefe", "cnefe_match"]
for c in result_cols:
    work[c] = None

t_match = time.time()
n_t1 = n_t2 = n_t3 = n_t4 = n_no = 0

for cd_mun, mdata in mun_data.items():
    sub = work[work["cd_mun"] == cd_mun].copy()
    if len(sub) == 0:
        continue
    by_key = mdata["by_key"]
    by_rua = mdata["by_rua"]
    rua_list = mdata["rua_list"]
    by_bairro = mdata["by_bairro"]
    bairro_norm_map = mdata["bairro_norm_map"]

    for idx, row in sub.iterrows():
        rua = row["rua_norm2"]
        num = row["num_norm"]
        bairro_tbweb = row["bairro"]
        is_favela = row["is_favela_hint"]

        if not rua:
            work.at[idx, "cnefe_match"] = "no_match"
            n_no += 1
            continue

        # T1: exact (rua, num)
        if num is not None and (rua, num) in by_key:
            r = by_key[(rua, num)]
            work.at[idx, "bairro_cnefe"] = r.bairro
            work.at[idx, "setor_cnefe"] = r.setor
            work.at[idx, "lat_cnefe"] = r.lat
            work.at[idx, "lon_cnefe"] = r.lon
            work.at[idx, "cnefe_match"] = "T1_exact"
            n_t1 += 1
            continue

        # T2: rua only (most frequent)
        if rua in by_rua:
            r = by_rua[rua]
            work.at[idx, "bairro_cnefe"] = r["bairro"]
            work.at[idx, "setor_cnefe"] = r["setor"]
            work.at[idx, "lat_cnefe"] = r["lat"]
            work.at[idx, "lon_cnefe"] = r["lon"]
            work.at[idx, "cnefe_match"] = "T2_rua"
            n_t2 += 1
            continue

        # T3: fuzzy match (token_set_ratio >= 88)
        if not is_favela and rua_list:
            best = process.extractOne(
                rua, rua_list, scorer=fuzz.token_set_ratio, score_cutoff=88
            )
            if best:
                matched_rua = best[0]
                r = by_rua[matched_rua]
                work.at[idx, "bairro_cnefe"] = r["bairro"]
                work.at[idx, "setor_cnefe"] = r["setor"]
                work.at[idx, "lat_cnefe"] = r["lat"]
                work.at[idx, "lon_cnefe"] = r["lon"]
                work.at[idx, "cnefe_match"] = f"T3_fuzzy_{int(best[1])}"
                n_t3 += 1
                continue

        # T4: bairro fallback via TBweb bairro
        if bairro_tbweb and pd.notna(bairro_tbweb):
            b_norm = norm_text(bairro_tbweb)
            cnefe_bairro_orig = bairro_norm_map.get(b_norm)
            if cnefe_bairro_orig is None and bairro_norm_map:
                best_b = process.extractOne(
                    b_norm,
                    list(bairro_norm_map.keys()),
                    scorer=fuzz.token_set_ratio,
                    score_cutoff=85,
                )
                if best_b:
                    cnefe_bairro_orig = bairro_norm_map[best_b[0]]
            if cnefe_bairro_orig and cnefe_bairro_orig in by_bairro:
                r = by_bairro[cnefe_bairro_orig]
                work.at[idx, "bairro_cnefe"] = cnefe_bairro_orig
                work.at[idx, "setor_cnefe"] = r["setor"]
                work.at[idx, "lat_cnefe"] = r["lat"]
                work.at[idx, "lon_cnefe"] = r["lon"]
                work.at[idx, "cnefe_match"] = "T4_bairro_fallback"
                n_t4 += 1
                continue

        work.at[idx, "cnefe_match"] = "no_match"
        n_no += 1

    elapsed = time.time() - t_match
    print(
        f"  {cd_mun}: {len(sub):,} cases processed ({elapsed/60:.1f} min total)",
        flush=True,
    )

# ── Results ──────────────────────────────────────────────────────────────────
total = len(work)
print(f"\n{'='*60}")
print("=== CNEFE MATCHING — SP outros ===")
print(f"{'='*60}")
print(f"Total cohort:                    {total:,}")
print(f"  T1 exact (rua+num):            {n_t1:,} ({n_t1/total*100:.1f}%)")
print(f"  T2 rua only:                   {n_t2:,} ({n_t2/total*100:.1f}%)")
print(f"  T3 fuzzy match:                {n_t3:,} ({n_t3/total*100:.1f}%)")
print(f"  T4 bairro fallback:            {n_t4:,} ({n_t4/total*100:.1f}%)")
print(f"  no_match:                      {n_no:,} ({n_no/total*100:.1f}%)")
matched_total = n_t1 + n_t2 + n_t3 + n_t4
print(f"\n-> Total coverage: {matched_total/total*100:.1f}%")
print(f"   Sector resolution (T1+T2+T3): {(n_t1+n_t2+n_t3)/total*100:.1f}%")
print(f"   Including bairro fallback:    {matched_total/total*100:.1f}%")

# Bairro concordance check
matched = work[
    work["cnefe_match"].isin(["T1_exact", "T2_rua"])
    | work["cnefe_match"].str.startswith("T3", na=False)
].copy()
both = matched[matched["bairro_cnefe"].notna() & matched["bairro"].notna()].copy()
both["b_cnefe_n"] = both["bairro_cnefe"].apply(norm_text)
both["b_tb_n"] = both["bairro"].apply(norm_text)
n_match_b = (both["b_cnefe_n"] == both["b_tb_n"]).sum()
print(f"\nBairro concordance (T1+T2+T3 only, n={len(both):,}):")
print(f"  Exact match: {n_match_b:,} ({n_match_b/len(both)*100:.1f}%)")

# ── Save ─────────────────────────────────────────────────────────────────────
out_cols = [
    "sinan_clean", "cd_mun", "munResid", "endereco", "numEnd",
    "bairro", "rua_norm2", "num_norm", "is_favela_hint",
    "bairro_cnefe", "setor_cnefe", "lat_cnefe", "lon_cnefe", "cnefe_match",
]
work[out_cols].to_csv("/tmp/cohort_sp_outros_with_cnefe.csv", index=False)
print(f"\nSaved: /tmp/cohort_sp_outros_with_cnefe.csv ({len(work):,} rows)")
print(f"Total matching time: {(time.time()-t_match)/60:.1f} min")
print(f"Total script time:   {(time.time()-t0)/60:.1f} min")

