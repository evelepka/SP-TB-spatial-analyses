"""Test what the `cep` field actually means on DETENTO rows in TBWeb_20250328_endereco.xlsx.

Hypotheses to distinguish:
  H1 (assumed): cep on a DETENTO row = home/residence address declared at prison intake
  H2:           cep on a DETENTO row = prison facility address

Tests:
  Test A — Within-person consistency: for persons with BOTH a DETENTO row (cep filled)
           AND a community/homeless row (cep filled), do the two CEPs match? Match → H1.
  Test B — cep vs ceptrat on the same DETENTO row: if cep == ceptrat on DETENTO rows,
           cep is plausibly the prison (since ceptrat is the treatment location, which IS
           the prison for incarcerated patients). If cep != ceptrat, they're distinct
           addresses → cep is the residence (H1).
  Test C — Concentration test: prison CEPs would be heavily clustered on a small number
           of values (SP has ~176 prison units). Home CEPs would be widely distributed.
  Test D — Show example `endereco` text strings for DETENTO rows with cep filled — does
           it look like a residence (rua / avenida + número) or a prison?
"""
from pathlib import Path
import pandas as pd

ADDR = Path("/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/.shortcut-targets-by-id/1WMps9BoKmDA6_Lzak12042gQKkXVI4qg/WHO modelling Project/Data/TBWeb_20250328_endereco.xlsx")

def clean_cep(s):
    if s is None or pd.isna(s): return pd.NA
    s = str(s).strip().replace("-","").replace(".","").replace(" ","")
    if s in {"", "nan", "NaN", "NAN", "None", "NONE", "0", "00000000"}: return pd.NA
    if not s.isdigit(): return pd.NA
    s = s.zfill(8)
    return s if len(s) == 8 else pd.NA

print("Loading endereco file...")
addr = pd.read_excel(
    ADDR, sheet_name="Exportacao_TBWeb_20250328",
    usecols=["SINAN","tipoEnd","cep","ceptrat","munResid","munNotif","bairro","endereco","numEnd"],
    dtype=str,
)
addr["sinan_padded"] = addr["SINAN"].astype(str).str.strip().str.zfill(7)
addr["cep_c"]    = addr["cep"].map(clean_cep)
addr["ceptrat_c"] = addr["ceptrat"].map(clean_cep)
print(f"rows: {len(addr):,}")

# ----- Test A: within-person consistency -----
print("\n=== Test A: Within-person, does DETENTO.cep match community-row.cep? ===")
detento_with_cep = addr[(addr["tipoEnd"]=="DETENTO") & (addr["cep_c"].notna())][["sinan_padded","cep_c","munResid","bairro","endereco"]].rename(
    columns={"cep_c":"detento_cep","munResid":"detento_munResid","bairro":"detento_bairro","endereco":"detento_endereco"})
community_with_cep = addr[(addr["tipoEnd"]=="ENDERECO PADRAO") & (addr["cep_c"].notna())][["sinan_padded","cep_c","munResid","bairro","endereco"]].rename(
    columns={"cep_c":"community_cep","munResid":"community_munResid","bairro":"community_bairro","endereco":"community_endereco"})

# Both must have only one row per person to compare cleanly — take any (first)
det_one = detento_with_cep.drop_duplicates("sinan_padded", keep="first")
com_one = community_with_cep.drop_duplicates("sinan_padded", keep="first")

both = det_one.merge(com_one, on="sinan_padded", how="inner")
print(f"  persons with BOTH a DETENTO-cep AND a community-cep filled: {len(both):,}")
print(f"  CEPs match exactly:    {(both['detento_cep']==both['community_cep']).sum():,} ({(both['detento_cep']==both['community_cep']).mean()*100:.1f}%)")
print(f"  CEPs differ:           {(both['detento_cep']!=both['community_cep']).sum():,}")

# When they differ, also check if same municipality (to see if at least same general area)
diff = both[both["detento_cep"]!=both["community_cep"]]
same_mun = (diff["detento_munResid"]==diff["community_munResid"]).sum()
print(f"    of the differing ones, same munResid: {same_mun:,} ({same_mun/max(1,len(diff))*100:.1f}%)")

print("\n  --- 10 example pairs (same person, two different rows) ---")
print(both.head(10)[["sinan_padded","detento_cep","community_cep","detento_munResid","community_munResid","detento_bairro","community_bairro"]].to_string(index=False))

# ----- Test B: on DETENTO rows, is cep == ceptrat? -----
print("\n=== Test B: On DETENTO rows, does cep equal ceptrat? ===")
det_both = addr[(addr["tipoEnd"]=="DETENTO") & (addr["cep_c"].notna()) & (addr["ceptrat_c"].notna())]
print(f"  DETENTO rows with BOTH cep and ceptrat filled: {len(det_both):,}")
print(f"  cep == ceptrat: {(det_both['cep_c']==det_both['ceptrat_c']).sum():,} ({(det_both['cep_c']==det_both['ceptrat_c']).mean()*100:.1f}%)")
print(f"  cep != ceptrat: {(det_both['cep_c']!=det_both['ceptrat_c']).sum():,}")

print("\n  --- 8 example DETENTO rows where cep == ceptrat (suggests prison address) ---")
print(det_both[det_both['cep_c']==det_both['ceptrat_c']].head(8)[["cep_c","ceptrat_c","munResid","munNotif","bairro","endereco"]].to_string(index=False))

print("\n  --- 8 example DETENTO rows where cep != ceptrat (cep would be residence) ---")
print(det_both[det_both['cep_c']!=det_both['ceptrat_c']].head(8)[["cep_c","ceptrat_c","munResid","munNotif","bairro","endereco"]].to_string(index=False))

# ----- Test C: concentration of DETENTO cep vs community cep -----
print("\n=== Test C: Concentration of cep values ===")
det_ceps = addr[(addr["tipoEnd"]=="DETENTO") & (addr["cep_c"].notna())]["cep_c"]
com_ceps = addr[(addr["tipoEnd"]=="ENDERECO PADRAO") & (addr["cep_c"].notna())]["cep_c"]
print(f"  DETENTO rows with cep: {len(det_ceps):,}, unique CEPs: {det_ceps.nunique():,}, top10 share:")
print(f"    {(det_ceps.value_counts().head(10).sum()/len(det_ceps)*100):.1f}% of DETENTO ceps are in the top 10 most-common values")
print(f"  ENDERECO PADRAO with cep: {len(com_ceps):,}, unique CEPs: {com_ceps.nunique():,}, top10 share:")
print(f"    {(com_ceps.value_counts().head(10).sum()/len(com_ceps)*100):.1f}% of community ceps are in the top 10 most-common values")
print("\n  Top 10 most-common DETENTO ceps (with bairro/mun for context):")
top_det = det_ceps.value_counts().head(10).index.tolist()
for c in top_det:
    sample = addr[(addr["tipoEnd"]=="DETENTO") & (addr["cep_c"]==c)].iloc[0]
    n = (det_ceps == c).sum()
    print(f"    {c}  n={n:>5,}  munResid={sample['munResid']!r:>30}  bairro={sample['bairro']!r:>40}  endereco={(sample['endereco'] or '')[:60]!r}")

# ----- Test D: example endereco strings -----
print("\n=== Test D: 10 random DETENTO rows with cep filled — what does `endereco` text look like? ===")
import numpy as np
samp = addr[(addr["tipoEnd"]=="DETENTO") & (addr["cep_c"].notna())].sample(min(10, len(addr)), random_state=0)
for _, r in samp.iterrows():
    print(f"  cep={r['cep_c']}  mun={r['munResid']}  bairro={r['bairro']}  endereco={r['endereco']!r:.<80} numEnd={r['numEnd']}")
