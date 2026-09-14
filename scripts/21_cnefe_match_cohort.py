"""CNEFE efficient — processa por município, nunca carrega tudo em memória.

Para cada município:
  - Parse CNEFE → dicionários por (rua, num) e por rua
  - Salva por município como CSV pequeno
Depois:
  - Para cada caso TBweb: lookup direto sem DataFrame gigante
"""

import os, json, re, time, unicodedata
import zipfile
import pandas as pd
import geopandas as gpd
from collections import defaultdict

SPATIAL = "/DATA_ROOT/WHO modelling Project/SP-TB-spatial-analyses/Data"
WHO_DATA = "/DATA_ROOT/WHO modelling Project/Data"
CNEFE_DIR = f"{SPATIAL}/IBGE_2022_extended/CNEFE_GSP"
INDEX_DIR = f"{CNEFE_DIR}/indices"
os.makedirs(INDEX_DIR, exist_ok=True)


def normalize_street(s):
    if not s:
        return None
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"^(RUA RUA|RUA|R\.?|AV\.?|AVENIDA|TV\.?|TRAVESSA|ROD\.?|RODOVIA|EST\.?|ESTRADA|AL\.?|ALAMEDA|PR\.?|PRACA)\s+", "", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s if s else None


def normalize_num(x):
    if x is None or x == "":
        return None
    try:
        n = int(float(str(x).strip().split()[0]))
        return n if n > 0 else None
    except (ValueError, TypeError):
        return None


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


# ========== 1) Processa cada município → CSV pequeno por município ==========
print("Fase 1: processar cada CNEFE por município → salvar índices CSV pequenos")
t0 = time.time()
files = sorted([f for f in os.listdir(CNEFE_DIR) if f.endswith(".zip")])
muni_index_paths = {}

for i, fname in enumerate(files, 1):
    fpath = os.path.join(CNEFE_DIR, fname)
    # Extract CD_MUN from filename: cnefe_XXXXXXX_NOME.zip
    cd_mun = fname.split("_")[1]
    out_path = f"{INDEX_DIR}/idx_{cd_mun}.csv"
    if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
        muni_index_paths[cd_mun] = out_path
        # Skip — já processado
        continue

    with zipfile.ZipFile(fpath) as z:
        inner = z.namelist()[0]
        with z.open(inner) as f:
            data = json.load(f)

    # Acumula dicionário por (rua, num)
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
        rua_n = normalize_street(rua_part)
        if not rua_n:
            continue
        num_n = normalize_num(num_part)
        bairro = props.get("DSC_LOCALIDADE")
        setor = props.get("COD_SETOR")
        coords = feat.get("geometry", {}).get("coordinates", [None, None])
        lon, lat = coords[0], coords[1] if len(coords) > 1 else None
        if not bairro:
            continue
        # Key composta: (rua, num) - num pode ser None (fica como -1)
        key = (rua_n, num_n if num_n else -1)
        by_key[key]["bairros"].append(bairro)
        by_key[key]["setores"].append(setor)
        if lat is not None:
            by_key[key]["lats"].append(lat)
        if lon is not None:
            by_key[key]["lons"].append(lon)

    # Reduz: mode/median por key
    from collections import Counter
    import statistics
    rows = []
    for (rua, num), vals in by_key.items():
        bairro = Counter(vals["bairros"]).most_common(1)[0][0]
        setor = Counter(vals["setores"]).most_common(1)[0][0] if vals["setores"] else None
        lat = statistics.median(vals["lats"]) if vals["lats"] else None
        lon = statistics.median(vals["lons"]) if vals["lons"] else None
        rows.append([rua, num if num != -1 else None, bairro, setor, lat, lon, len(vals["bairros"])])

    df = pd.DataFrame(rows, columns=["rua", "num", "bairro", "setor", "lat", "lon", "n"])
    df.to_csv(out_path, index=False)
    muni_index_paths[cd_mun] = out_path
    print(f"  [{i:2d}/{len(files)}] {cd_mun} → {len(df):,} entradas únicas  "
          f"({(time.time()-t0)/60:.1f} min total)", flush=True)

print(f"\nFase 1 OK: {len(muni_index_paths)} índices municipais salvos em {(time.time()-t0)/60:.1f} min")

# ========== 2) Carrega cohort + faz matching município por município ==========
print("\nFase 2: carregar cohort + matching...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"] = sec22["CD_MUN"].astype(str)
cd_muns_gsp = set(sec22[sec22["NM_CONCURB"] == "São Paulo/SP"]["CD_MUN"].unique())

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

mun_to_cd = sec22.drop_duplicates("CD_MUN").set_index(
    sec22.drop_duplicates("CD_MUN")["NM_MUN"].apply(norm_text)
)["CD_MUN"]
cohort["cd_mun"] = cohort["munResid"].apply(norm_text).map(mun_to_cd)

work = cohort[
    (cohort["address_type"] == "ENDERECO PADRAO") &
    cohort["case_type"].astype(str).str.strip().str.upper().isin(["NOVO", "RECIDIVA"]) &
    cohort["year"].between(2013, 2024) &
    cohort["cd_mun"].isin(cd_muns_gsp)
].copy()
print(f"  Cohort GSP 2013-2024: {len(work):,}")

work["rua_norm"] = work["endereco"].apply(normalize_street)
work["num_norm"] = work["numEnd"].apply(normalize_num)

# Match município por município
print("\nMatching por município...")
result_cols = ["bairro_cnefe", "setor_cnefe", "lat_cnefe", "lon_cnefe", "cnefe_match"]
for c in result_cols:
    work[c] = None

for cd_mun, path in muni_index_paths.items():
    idx_df = pd.read_csv(path)
    # Dicionário (rua, num) → tudo
    by_key = {(r.rua, r.num): r for r in idx_df.itertuples(index=False)}
    # Dicionário (rua) → fallback: pega o mais frequente (n máximo)
    by_rua = (idx_df.sort_values("n", ascending=False)
                    .drop_duplicates("rua")
                    .set_index("rua").to_dict(orient="index"))

    sub = work[work["cd_mun"] == cd_mun]
    n_exact = 0
    n_fb = 0
    for idx, row in sub.iterrows():
        rua = row["rua_norm"]
        num = row["num_norm"]
        if not rua:
            continue
        # Tier 1: exact
        if num is not None and (rua, num) in by_key:
            r = by_key[(rua, num)]
            work.at[idx, "bairro_cnefe"] = r.bairro
            work.at[idx, "setor_cnefe"] = r.setor
            work.at[idx, "lat_cnefe"] = r.lat
            work.at[idx, "lon_cnefe"] = r.lon
            work.at[idx, "cnefe_match"] = "exact_rua_num"
            n_exact += 1
        # Tier 2: fallback (só rua)
        elif rua in by_rua:
            r = by_rua[rua]
            work.at[idx, "bairro_cnefe"] = r["bairro"]
            work.at[idx, "setor_cnefe"] = r["setor"]
            work.at[idx, "lat_cnefe"] = r["lat"]
            work.at[idx, "lon_cnefe"] = r["lon"]
            work.at[idx, "cnefe_match"] = "fallback_rua"
            n_fb += 1
        else:
            work.at[idx, "cnefe_match"] = "no_match"

# Resultados
total = len(work)
n_match_exact = (work["cnefe_match"] == "exact_rua_num").sum()
n_match_fb = (work["cnefe_match"] == "fallback_rua").sum()
n_no = (work["cnefe_match"] == "no_match").sum()

print(f"\n=== RESULTADOS CNEFE MATCHING ===")
print(f"Total cohort GSP: {total:,}")
print(f"  exact_rua_num: {n_match_exact:,} ({n_match_exact/total*100:.1f}%)")
print(f"  fallback_rua:  {n_match_fb:,} ({n_match_fb/total*100:.1f}%)")
print(f"  no_match:      {n_no:,} ({n_no/total*100:.1f}%)")
print(f"\n→ Cobertura CNEFE total: {(n_match_exact+n_match_fb)/total*100:.1f}%")

# Concordância bairro_cnefe vs bairro TBweb
matched = work[work["cnefe_match"] != "no_match"].copy()
both = matched[matched["bairro_cnefe"].notna() & matched["bairro"].notna()].copy()
both["b_cnefe_n"] = both["bairro_cnefe"].apply(norm_text)
both["b_tb_n"] = both["bairro"].apply(norm_text)

n_match_b = (both["b_cnefe_n"] == both["b_tb_n"]).sum()
print(f"\nConcordância bairro_cnefe vs bairro TBweb (n={len(both):,}):")
print(f"  Match exato: {n_match_b:,} ({n_match_b/len(both)*100:.1f}%)")

# Salva
out_cols = ["sinan_clean", "cd_mun", "munResid", "endereco", "numEnd",
            "bairro", "rua_norm", "num_norm",
            "bairro_cnefe", "setor_cnefe", "lat_cnefe", "lon_cnefe", "cnefe_match"]
work[out_cols].to_csv("/tmp/cohort_with_cnefe.csv", index=False)
print(f"\nSalvo: /tmp/cohort_with_cnefe.csv ({len(work):,} linhas)")
print(f"\nTempo total: {(time.time()-t0)/60:.1f} min")
