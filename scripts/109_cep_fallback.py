"""AUTHORITATIVE per-PERSON geocode, Phase 2: CNEFE-internal postal-code (CEP) fallback.

Persons whose street address did not match CNEFE (no coordinates) but who carry a valid postal code
are assigned the census sector MOST FREQUENTLY observed, among successfully geocoded persons, for
their own postal code (a CNEFE-internal CEP -> sector centroid — NOT an external CEP service, which
would displace favela residents into adjacent formal areas). Flagged tier "T5" (postal-code level,
coarse) for the sensitivity analysis; at the ~5,000-adult REGION scale a CEP is region-accurate.
Universe = every person in the CNEFE-matched files (unrestricted; episode/case selection is in 100).
Input: /tmp/geocoded_cohort.csv (Phase 1)   Output: overwrites it with T5 rows appended (+ persist).
"""
import pandas as pd, numpy as np, os
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
def cclean(x):
    if pd.isna(x): return None
    s=''.join(ch for ch in str(x) if ch.isdigit()); return s.zfill(8)[:8] if s else None

# universe of persons = every sinan_clean in the CNEFE-matched files
def sinans(p): return pd.read_csv(p,usecols=["sinan_clean"],dtype={"sinan_clean":str})["sinan_clean"]
universe=set(pd.concat([sinans("/tmp/cohort_with_cnefe.csv"),
                        sinans("/tmp/cohort_baixada_with_cnefe_v2.csv"),
                        sinans("/tmp/cohort_sp_outros_with_cnefe.csv")]))
# CEP is a person attribute
m=pd.read_csv(f"{SP}/cohort_with_spatial.csv",usecols=["sinan_clean","cep"],low_memory=False,dtype={"sinan_clean":str,"cep":str})
m["cep8"]=m["cep"].apply(cclean)
cepmap=m.dropna(subset=["cep8"]).drop_duplicates("sinan_clean").set_index("sinan_clean")["cep8"]

geo=pd.read_csv("/tmp/geocoded_cohort.csv",dtype={"sinan_clean":str,"CD_SETOR":str,"CD_TIPO":str})
geo["cep8"]=geo["sinan_clean"].map(cepmap)
# CEP -> modal sector (most frequent among geocoded persons sharing that CEP)
cnt=geo.dropna(subset=["cep8"]).groupby(["cep8","CD_SETOR","CD_TIPO"]).size().rename("k").reset_index()
cnt=cnt.sort_values("k",ascending=False).drop_duplicates("cep8",keep="first")
cep2sec=cnt.set_index("cep8")[["CD_SETOR","CD_TIPO"]]

nomatch=universe-set(geo["sinan_clean"])
nm=pd.DataFrame({"sinan_clean":list(nomatch)}); nm["cep8"]=nm["sinan_clean"].map(cepmap)
nm=nm.join(cep2sec,on="cep8")
rec=nm.dropna(subset=["CD_SETOR"]).copy()
rec["tier"]="T5"; rec["favela"]=(rec["CD_TIPO"]=="1").astype(int)
rec=rec[["sinan_clean","CD_SETOR","CD_TIPO","tier","favela"]]

out=pd.concat([geo[["sinan_clean","CD_SETOR","CD_TIPO","tier","favela"]],rec],ignore_index=True)
out=out.drop_duplicates("sinan_clean")
out.to_csv("/tmp/geocoded_cohort.csv",index=False)
_AN=f"{SP.rsplit('/Data',1)[0]}/Data/analytic"; os.makedirs(_AN,exist_ok=True)
out.to_csv(f"{_AN}/geocoded_cohort.csv",index=False)   # persist (survives /tmp wipe)

print("================ PERSON GEOCODE ================")
print(f"  persons in CNEFE files (universe)     : {len(universe):,}")
print(f"  Phase 1 (spatial overlay, T1-T4)      : {len(geo):,}")
print(f"  Phase 2 (CEP fallback, T5)            : +{len(rec):,}")
print(f"  >>> persons geocoded                  : {len(out):,}")
print(f"  favela persons                        : {int(out['favela'].sum()):,}  ({out['favela'].mean()*100:.1f}%)")
print(f"  tier mix:",dict(out['tier'].value_counts()))
print("Saved /tmp/geocoded_cohort.csv (person -> sector)")
