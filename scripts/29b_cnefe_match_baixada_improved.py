"""IMPROVED CNEFE matching for Baixada Santista.

Improvements over 29:
  1. Strip complement tokens (BLOCO, APTO, QUADRA, LOTE, KM, CASA, PROX) before normalize
  2. Extract embedded number if numEnd is missing (e.g. 'R FULANO 73' → rua='FULANO', num=73)
  3. Normalize numbered/ordinal street prefixes (1A, 10A, etc.)
  4. Tier 3: fuzzy match within município via rapidfuzz (token_set_ratio >= 88)
  5. Tier 4: bairro_cnefe fallback (assign centroid sector when rua is FAVELA/COMUNIDADE)
  6. Typo dictionary for common misspellings
"""

import os, json, re, time, unicodedata
import zipfile
import pandas as pd
import geopandas as gpd
from collections import defaultdict, Counter
import statistics
from rapidfuzz import fuzz, process

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
WHO_DATA = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/Data"
CNEFE_DIR = f"{SPATIAL}/IBGE_2022_extended/CNEFE_Baixada"
INDEX_DIR = f"{CNEFE_DIR}/indices"

BAIXADA_CD_MUN = {"3506359", "3513504", "3518701", "3522109", "3531100",
                  "3537602", "3541000", "3548500", "3551009"}

# Common typos / misspellings in TBweb addresses
TYPO_MAP = {
    "MORRIHOS": "MORRINHOS",
    "SARAYVA": "SARAIVA",
    "DEALBUQUERQUE": "DE ALBUQUERQUE",
    "BRUZARROSCO": "BRUZZAROSCO",
    "SAMBAIATUBA": "SAMBAIATUBA",
    "CACHETAS": "CACHETA",
}

# Patterns to STRIP (complement suffixes that pollute street name)
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

# Ordinal prefix (e.g. "1A RUA", "10A RUA") — keep ordinal as part of name
ORDINAL_RUA_RE = re.compile(r"^(\d+)\s*([AABNOSPÃª])?\s+RUA\s+", re.IGNORECASE)

# Embedded number at end (when numEnd is null)
EMBED_NUM_RE = re.compile(r"\s+(\d{1,5})$")

# Street type prefix
STREET_PREFIX_RE = re.compile(
    r"^(RUA RUA|RUA|R\.?|AV\.?|AVENIDA|TV\.?|TRAVESSA|ROD\.?|RODOVIA|"
    r"EST\.?|ESTRADA|AL\.?|ALAMEDA|PR\.?|PRACA|PRAÇA|"
    r"VIA|ACESSO|VL|VILA|BECO|LARGO|CAMINHO|CAM|VIELA|"
    r"MARGINAL|SERVIDAO|SERV)\s+", re.IGNORECASE
)

# Favela/comunidade indicator (cannot match as a street; needs bairro fallback)
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

    # 1) Strip complement suffixes BEFORE removing prefix
    s = COMPL_RE.sub("", s)

    # 2) Handle ordinal "10A RUA X" → preserve "10A " prefix on street name
    ordinal_match = ORDINAL_RUA_RE.match(s)
    ordinal_prefix = ""
    if ordinal_match:
        ordinal_prefix = ordinal_match.group(1) + "A "
        s = ORDINAL_RUA_RE.sub("", s)

    # 3) Strip street type prefix
    s = STREET_PREFIX_RE.sub("", s)

    # 4) Extract embedded num if numEnd is None
    extracted_num = None
    if num_end is None or pd.isna(num_end) or str(num_end).strip() in ("", "S/N", "SN", "NAN"):
        m = EMBED_NUM_RE.search(s)
        if m:
            extracted_num = int(m.group(1))
            s = EMBED_NUM_RE.sub("", s).strip()

    # 5) Clean punctuation
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    # 6) Apply typo map
    for typo, correct in TYPO_MAP.items():
        s = re.sub(rf"\b{typo}\b", correct, s)

    # 7) Re-add ordinal
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
    if pd.isna(s): return None
    s = str(s).strip().upper()
    s = strip_accents(s)
    return re.sub(r"\s+", " ", s)


def to_sinan(x, width=11):
    if pd.isna(x): return None
    try: return f"{int(float(x)):0{width}d}"
    except: return None


# ========== Load CNEFE indices ==========
print("Loading CNEFE municipal indices...")
muni_index_paths = {}
for f in sorted(os.listdir(CNEFE_DIR)):
    if f.endswith(".zip"):
        cd_mun = f.split("_")[1]
        muni_index_paths[cd_mun] = f"{INDEX_DIR}/idx_{cd_mun}.csv"
print(f"  {len(muni_index_paths)} índices CNEFE")

# Build per-município lookup structures
print("Building lookup structures (exact, by-rua, by-bairro centroid)...")
mun_data = {}
for cd_mun, path in muni_index_paths.items():
    idx_df = pd.read_csv(path)
    by_key = {(r.rua, r.num): r for r in idx_df.itertuples(index=False)}
    by_rua = (idx_df.sort_values("n", ascending=False)
                    .drop_duplicates("rua")
                    .set_index("rua").to_dict(orient="index"))
    rua_list = list(by_rua.keys())
    # Centroid by bairro (for favela fallback)
    by_bairro = idx_df.dropna(subset=["bairro"]).groupby("bairro").agg(
        setor=("setor", lambda x: x.mode().iloc[0] if not x.mode().empty else None),
        lat=("lat", "median"),
        lon=("lon", "median"),
        n=("n", "sum"),
    ).to_dict(orient="index")
    bairro_norm_map = {norm_text(k): k for k in by_bairro}
    mun_data[cd_mun] = {
        "by_key": by_key,
        "by_rua": by_rua,
        "rua_list": rua_list,
        "by_bairro": by_bairro,
        "bairro_norm_map": bairro_norm_map,
    }
print(f"  {len(mun_data)} municípios prontos")

# ========== Load cohort ==========
print("\nLoading cohort + endereços...")
cohort = pd.read_csv(f"{SPATIAL}/cohort_with_spatial.csv",
                     usecols=["sinan_clean", "sinan_padded", "address_type", "case_type",
                              "cep", "notification_date"],
                     low_memory=False)
cohort["sinan_key"] = cohort["sinan_padded"].apply(to_sinan)
cohort["year"] = pd.to_datetime(cohort["notification_date"], errors="coerce").dt.year

end = pd.read_excel(f"{WHO_DATA}/TBWeb_20250328_endereco.xlsx",
                    usecols=["SINAN", "endereco", "numEnd", "bairro", "munResid"])
end["sinan_key"] = end["SINAN"].apply(to_sinan)
end_d = end.dropna(subset=["sinan_key"]).drop_duplicates("sinan_key")
cohort = cohort.merge(end_d[["sinan_key", "endereco", "numEnd", "bairro", "munResid"]],
                     on="sinan_key", how="left")

sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"] = sec22["CD_MUN"].astype(str)
mun_to_cd = sec22.drop_duplicates("CD_MUN").set_index(
    sec22.drop_duplicates("CD_MUN")["NM_MUN"].apply(norm_text)
)["CD_MUN"]
cohort["cd_mun"] = cohort["munResid"].apply(norm_text).map(mun_to_cd)

work = cohort[
    (cohort["address_type"] == "ENDERECO PADRAO") &
    cohort["case_type"].astype(str).str.strip().str.upper().isin(["NOVO", "RECIDIVA"]) &
    cohort["year"].between(2013, 2024) &
    cohort["cd_mun"].isin(BAIXADA_CD_MUN)
].copy()
print(f"  Cohort Baixada 2013-2024: {len(work):,}")

# Apply normalize_street_v2 with num extraction
norm_results = work.apply(lambda r: normalize_street_v2(r["endereco"], r["numEnd"]),
                          axis=1)
work["rua_norm2"] = [r[0] for r in norm_results]
work["num_extracted"] = [r[1] for r in norm_results]
work["is_favela_hint"] = [r[2] for r in norm_results]
work["num_norm"] = work["numEnd"].apply(normalize_num).fillna(work["num_extracted"])
work["num_norm"] = work["num_norm"].apply(lambda x: int(x) if pd.notna(x) else None)

print(f"  Embedded numbers recovered: {work['num_extracted'].notna().sum():,}")
print(f"  Favela-hint addresses:      {work['is_favela_hint'].sum():,}")

# ========== Matching cascade ==========
print("\nMatching cascade (T1=exact, T2=rua, T3=fuzzy, T4=bairro_fallback)...")
result_cols = ["bairro_cnefe", "setor_cnefe", "lat_cnefe", "lon_cnefe", "cnefe_match"]
for c in result_cols:
    work[c] = None

t0 = time.time()
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

        # T2: rua only
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
        if not is_favela:
            best = process.extractOne(rua, rua_list, scorer=fuzz.token_set_ratio,
                                       score_cutoff=88)
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
            # Try exact bairro
            cnefe_bairro_orig = bairro_norm_map.get(b_norm)
            if cnefe_bairro_orig is None:
                # Fuzzy on bairro names
                best_b = process.extractOne(b_norm, list(bairro_norm_map.keys()),
                                            scorer=fuzz.token_set_ratio,
                                            score_cutoff=85)
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

    elapsed = time.time() - t0
    print(f"  {cd_mun}: {len(sub):,} casos processados ({elapsed/60:.1f} min total)", flush=True)

# Results
total = len(work)
print(f"\n=== IMPROVED CNEFE MATCHING (Baixada) ===")
print(f"Total cohort:                    {total:,}")
print(f"  T1 exact (rua+num):            {n_t1:,} ({n_t1/total*100:.1f}%)")
print(f"  T2 rua only:                   {n_t2:,} ({n_t2/total*100:.1f}%)")
print(f"  T3 fuzzy match:                {n_t3:,} ({n_t3/total*100:.1f}%)")
print(f"  T4 bairro fallback:            {n_t4:,} ({n_t4/total*100:.1f}%)")
print(f"  no_match:                      {n_no:,} ({n_no/total*100:.1f}%)")
print(f"\n→ Total coverage: {(n_t1+n_t2+n_t3+n_t4)/total*100:.1f}%")
print(f"  Sector resolution (T1+T2+T3): {(n_t1+n_t2+n_t3)/total*100:.1f}%")
print(f"  Including bairro fallback:    {(n_t1+n_t2+n_t3+n_t4)/total*100:.1f}%")

# Bairro concordance check (only on T1+T2+T3, not T4)
matched = work[work["cnefe_match"].isin(["T1_exact","T2_rua"]) |
               work["cnefe_match"].str.startswith("T3", na=False)].copy()
both = matched[matched["bairro_cnefe"].notna() & matched["bairro"].notna()].copy()
both["b_cnefe_n"] = both["bairro_cnefe"].apply(norm_text)
both["b_tb_n"] = both["bairro"].apply(norm_text)
n_match_b = (both["b_cnefe_n"] == both["b_tb_n"]).sum()
print(f"\nBairro concordance (T1+T2+T3 only, n={len(both):,}):")
print(f"  Exact match: {n_match_b:,} ({n_match_b/len(both)*100:.1f}%)")

out_cols = ["sinan_clean", "cd_mun", "munResid", "endereco", "numEnd",
            "bairro", "rua_norm2", "num_norm", "is_favela_hint",
            "bairro_cnefe", "setor_cnefe", "lat_cnefe", "lon_cnefe", "cnefe_match"]
work[out_cols].to_csv("/tmp/cohort_baixada_with_cnefe_v2.csv", index=False)
print(f"\nSaved: /tmp/cohort_baixada_with_cnefe_v2.csv ({len(work):,} rows)")
print(f"Total time: {(time.time()-t0)/60:.1f} min")
