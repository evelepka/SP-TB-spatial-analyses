"""Improved person linkage:
  - Investigate flag_identity_conflict in cleaned table.
  - Verify sinan key matches across raw and cleaned.
  - Build a relaxed person key: nome_first2_words + mae_first2_words + DTNASC + sexo,
    with strong text normalization.
  - Also try a 'looser' key that drops mae if missing.
"""
import unicodedata, re
from pathlib import Path
import pandas as pd

RAW   = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/Abandonment Paper/Banco de dados/tb web/TBWeb_20250123.xlsx")
CLEAN = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/Abandonment Paper/Data/Final_table_cleaned.csv")

# ---------- Cleaned table: check flag_identity_conflict ----------
print("Loading cleaned table for identity flag check...")
clean = pd.read_csv(CLEAN, dtype=str, low_memory=False)
print(f"flag_identity_conflict values:\n{clean['flag_identity_conflict'].value_counts(dropna=False).to_string()}")
print(f"flag_leading_zero_padded values:\n{clean['flag_leading_zero_padded'].value_counts(dropna=False).to_string()}")

# ---------- Raw table ----------
print("\nLoading raw TBweb (xlsx)...")
raw = pd.read_excel(
    RAW,
    sheet_name="Exportacao_TBWeb_20250123",
    usecols=["sinan","nome","mae","DTNASC","sexo","seqTrat","tipoEndTrat","notification_date","tipoCaso"],
    dtype=str,
)
print(f"raw rows: {len(raw):,}, unique sinan: {raw['sinan'].nunique():,}")

# Verify sinan join: how many cleaned sinan_clean appear in raw sinan?
clean_sinan = set(clean["sinan_clean"].dropna().unique())
raw_sinan_str = raw["sinan"].astype(str)
raw_sinan_set = set(raw_sinan_str.unique())
overlap_clean_in_raw  = len(clean_sinan & raw_sinan_set)
print(f"sinan_clean values also in raw.sinan: {overlap_clean_in_raw:,} / {len(clean_sinan):,}")

# Try sinan_original too
orig_sinan = set(clean["sinan_original"].dropna().astype(str).unique())
overlap_orig_in_raw = len(orig_sinan & raw_sinan_set)
print(f"sinan_original values also in raw.sinan: {overlap_orig_in_raw:,} / {len(orig_sinan):,}")

# ---------- Normalization ----------
def norm(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ASCII","ignore").decode("ASCII")
    s = re.sub(r"[^A-Z ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# Tokens; drop ultra-short connectors
STOP = {"DE","DA","DO","DAS","DOS","E"}
def first_n_meaningful(s, n=2):
    toks = [t for t in norm(s).split() if t not in STOP]
    return " ".join(toks[:n])

raw["nome_n"] = raw["nome"].map(norm)
raw["mae_n"]  = raw["mae"].map(norm)
raw["nome_k"] = raw["nome"].map(lambda s: first_n_meaningful(s, 2))   # first + second non-stop tokens
raw["mae_k"]  = raw["mae"].map(lambda s: first_n_meaningful(s, 2))
raw["dob"]    = raw["DTNASC"].astype(str).str[:10]
raw["sex"]    = raw["sexo"].map(norm)

# Drop seqTrat duplicates within sinan; keep tx_seq=1 (or first)
raw["seqTrat_i"] = pd.to_numeric(raw["seqTrat"], errors="coerce")
raw_sinan = raw.sort_values(["sinan","seqTrat_i"]).drop_duplicates("sinan", keep="first").copy()
print(f"\nraw rows after one-row-per-sinan: {len(raw_sinan):,}")

# Key A: strict — full normalized nome + mae + dob + sex
raw_sinan["key_A"] = raw_sinan["nome_n"] + "|" + raw_sinan["mae_n"] + "|" + raw_sinan["dob"] + "|" + raw_sinan["sex"]
# Key B: relaxed — first 2 meaningful tokens of nome and mae + dob + sex
raw_sinan["key_B"] = raw_sinan["nome_k"] + "|" + raw_sinan["mae_k"] + "|" + raw_sinan["dob"] + "|" + raw_sinan["sex"]
# Key C: very relaxed — first token of nome + first token of mae + dob + sex
def first1(s):
    toks = [t for t in norm(s).split() if t not in STOP]
    return toks[0] if toks else ""
raw_sinan["nome_1"] = raw_sinan["nome"].map(first1)
raw_sinan["mae_1"]  = raw_sinan["mae"].map(first1)
raw_sinan["key_C"]  = raw_sinan["nome_1"] + "|" + raw_sinan["mae_1"] + "|" + raw_sinan["dob"] + "|" + raw_sinan["sex"]
# Key D: dob+sex+mae (drop nome — mae is usually more stable)
raw_sinan["key_D"]  = raw_sinan["mae_n"] + "|" + raw_sinan["dob"] + "|" + raw_sinan["sex"]

for k in ["key_A","key_B","key_C","key_D"]:
    valid = raw_sinan[raw_sinan["dob"].str.len() >= 8].copy()
    counts = valid[k].value_counts()
    multi = (counts >= 2).sum()
    multi_sinans = counts[counts >= 2].sum()
    print(f"  {k}: persons={len(counts):,}, with>=2 notifications={multi:,}, total multi-sinans={multi_sinans:,}, max={counts.max()}")

# Quick sanity: among case_type=Recidiva or Retr Aband (known-recurrent), what fraction of their sinan link to another sinan via key_B?
print("\nSanity check: for known-recurrent notifications, can we find a prior sinan via key_B?")
clean["sinan_clean"] = clean["sinan_clean"].astype(str)
raw_sinan["sinan"]   = raw_sinan["sinan"].astype(str)
m = clean[["sinan_clean","case_type","notification_date","address_type","tx_seq"]].drop_duplicates("sinan_clean")
m = m.merge(raw_sinan[["sinan","key_A","key_B","key_C","key_D","dob","sex"]], left_on="sinan_clean", right_on="sinan", how="left")
m_recur = m[m["case_type"].isin(["Recidiva","Retr Aband","Retrat apos falencia/resistencia","Retrat apos mud esquema int/tox"])]
print(f"  recurrent notifications: {len(m_recur):,}")
for k in ["key_A","key_B","key_C","key_D"]:
    # Count keys whose total occurrence in raw_sinan is >=2 (i.e., there's at least one other notification with this key)
    valid = raw_sinan[raw_sinan["dob"].str.len() >= 8]
    key_counts = valid[k].value_counts()
    mr_keys = m_recur[k].dropna()
    has_match = mr_keys.map(lambda x: key_counts.get(x, 0) >= 2).sum()
    print(f"    {k}: recurrent notifications whose key matches at least one other sinan: {has_match:,} ({has_match/len(m_recur)*100:.1f}%)")
