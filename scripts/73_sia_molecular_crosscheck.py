"""Independent cross-check of TB molecular testing using SIA-SUS (DATASUS / TABNET),
procedure 0202090361 (TRM-TB), por local de residência, by município, 2019-2024.
Validates the TBweb-derived coverage (case-side) against an independent supply-side
count of tests performed. Municipal resolution (does not split the capital).

Computes per município: SIA TRM-TB tests/100k/yr, SIA tests per notified TB case,
TBweb molecular coverage; correlates them + with incidence and vulnerability.
SIA file: Data/sia_cnv_qbsp224519179_111_74_244 (1).csv (TABNET export).
Output: /tmp/fig_sia_crosscheck.png
"""
import pandas as pd, numpy as np, re, glob, matplotlib, matplotlib.pyplot as plt
from scipy.stats import spearmanr
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
DONE={"Mtb detectado - Rifamp sensivel","Mtb nao detectado","Mtb detectado - Rifamp indeterm","Mtb detectado - Rifamp resistente"}
def ns(x):
    if pd.isna(x): return None
    x=str(x).strip(); return x[:-1] if x.endswith("P") else x

print("Parsing SIA TABNET export...")
sf=glob.glob(f"{SP}/sia_cnv_qbsp*.csv")[0]
raw=pd.read_csv(sf,sep=";",encoding="latin-1",skiprows=4,dtype=str)
raw=raw[raw["Município"].astype(str).str.match(r"^\d{6}\s")].copy()
raw["mun6"]=raw["Município"].str.slice(0,6)
yrs=[c for c in raw.columns if c.strip().isdigit()]
print(f"  municípios: {len(raw)} | anos: {yrs}")
for c in yrs+["Total"]:
    raw[c]=pd.to_numeric(raw[c].str.replace("-","0",regex=False).str.replace(".","",regex=False).str.strip(),errors="coerce").fillna(0)
recyrs=[y for y in yrs if 2020<=int(y)<=2024]
raw["sia_rec"]=raw[recyrs].sum(axis=1)   # 2020-2024 to match TBweb
sia=raw.set_index("mun6")["sia_rec"]
print(f"  total TRM-TB SIA 2020-2024 (SP): {sia.sum():,.0f}")

print("Loading population + vulnerability (by município)...")
vs=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)[["CD_SETOR","vuln","pop15"]]
vs=vs[vs["pop15"]>0]; vs["mun6"]=vs["CD_SETOR"].str.slice(0,6)
mpop=vs.groupby("mun6")["pop15"].sum()
mvuln=(vs.assign(vw=vs["vuln"]*vs["pop15"]).groupby("mun6")["vw"].sum())/mpop

print("Loading cohort (cases + molecular) by município...")
def lc(p,raw_=False):
    x=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    if not raw_:
        x["t"]=x["cnefe_match"].astype(str).str.extract(r"^(T\d)"); x=x[x["t"].isin(["T1","T2","T3"])]
    x["CD_SETOR"]=x["setor_cnefe"].apply(ns); return x[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
co=pd.concat([lc("/tmp/cohort_with_cnefe.csv",raw_=True),lc("/tmp/cohort_baixada_with_cnefe_v2.csv"),lc("/tmp/cohort_sp_outros_with_cnefe.csv")])
m=pd.read_csv(f"{SP}/cohort_with_spatial.csv",usecols=["sinan_clean","notification_date","age_tb","tmr_tb","tx_seq"],low_memory=False,dtype={"sinan_clean":str})
m["year"]=pd.to_datetime(m["notification_date"],errors="coerce").dt.year
m=m.sort_values("tx_seq").drop_duplicates("sinan_clean",keep="last").set_index("sinan_clean")
for c in ["year","age_tb","tmr_tb"]: co[c]=co["sinan_clean"].map(m[c])
co=co[(co["age_tb"]>=15)&co["year"].between(2013,2024)]
co["mun6"]=co["CD_SETOR"].str.slice(0,6)
rec=co["year"].between(2020,2024)
co["mdone"]=co["tmr_tb"].isin(DONE)&rec; co["mknown"]=(co["tmr_tb"].isin(DONE)|co["tmr_tb"].eq("N/realiz"))&rec
g=co.groupby("mun6").agg(cases_all=("sinan_clean","size"),cases_rec=("year",lambda s:(s.between(2020,2024)).sum()),
    mdone=("mdone","sum"),mknown=("mknown","sum")).reset_index()

d=pd.DataFrame({"pop":mpop,"vuln":mvuln}).reset_index().merge(g,on="mun6",how="left").fillna(0)
d["sia"]=d["mun6"].map(sia).fillna(0)
d["incid"]=np.where(d["cases_all"]>=10,d["cases_all"]/(d["pop"]*12)*1e5,np.nan)
d["sia_rate"]=np.where(d["pop"]>0,d["sia"]/(d["pop"]*5)*1e5,np.nan)        # tests/100k/yr (2020-24=5y)
d["sia_per_case"]=np.where(d["cases_rec"]>=20,d["sia"]/d["cases_rec"],np.nan) # tests per notified case
d["tbweb_cov"]=np.where(d["mknown"]>=20,d["mdone"]/d["mknown"]*100,np.nan)
e=d[d["cases_rec"]>=20].copy()
print(f"\nMunicípios with >=20 recent cases: {len(e)}  (cover {e['cases_rec'].sum()/d['cases_rec'].sum()*100:.0f}% of cases)")
print(f"SIA tests per notified case (SP overall): {d['sia'].sum()/d['cases_rec'].sum():.2f}")

print("\nCorrelations (municipal, >=20 recent cases):")
for a,b in [("sia_per_case","tbweb_cov"),("sia_rate","incid"),("sia_per_case","vuln"),("sia_rate","vuln"),("tbweb_cov","vuln")]:
    r=spearmanr(e[a],e[b],nan_policy="omit").correlation
    print(f"  {a:14s} vs {b:11s}: rho={r:+.2f}")

# ── figure: SIA vs TBweb agreement + SIA testing rate vs incidence ───────────
fig,(axA,axB)=plt.subplots(1,2,figsize=(14,6))
s=e.dropna(subset=["sia_per_case","tbweb_cov"])
axA.scatter(s["tbweb_cov"],s["sia_per_case"],s=18,alpha=0.5,color="#1f6f8b")
axA.set_xlabel("TBweb molecular coverage % (case-side)"); axA.set_ylabel("SIA TRM-TB tests per notified case (supply-side)")
axA.set_title(f"A)  Independent agreement (município)\nρ={spearmanr(s['tbweb_cov'],s['sia_per_case']).correlation:+.2f}",fontsize=11.5,fontweight="bold")
axA.grid(alpha=0.3)
s2=e.dropna(subset=["sia_rate","incid"])
axB.scatter(s2["incid"],s2["sia_rate"],s=18,alpha=0.5,color="#c0392b")
axB.set_xlabel("TB incidence /100k/yr"); axB.set_ylabel("SIA TRM-TB tests /100k/yr")
axB.set_title(f"B)  Testing volume tracks burden\nρ={spearmanr(s2['incid'],s2['sia_rate']).correlation:+.2f}",fontsize=11.5,fontweight="bold")
axB.grid(alpha=0.3)
fig.suptitle("SIA-SUS molecular testing (independent, municipal) vs TBweb coverage & incidence — SP",fontsize=12.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_sia_crosscheck.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_sia_crosscheck.png")
