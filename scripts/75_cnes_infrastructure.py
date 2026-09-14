"""Health-system infrastructure (ecological, place-level) vs TB burden/outcomes, from
CNES (extracted via pysus). Municipal resolution (CNES FTP has no coordinates):
  - primary-care density: Posto/UBS (TP_UNID 01,02) per 100k adults  [ST file]
  - X-ray availability: establishments with general radiography
    (TIPEQUIP=1 imaging, CODEQUIP 04/05/06 = Raio X <100mA / 100-500mA / >500mA;
    excludes 07 dental, 02/03 mammography, 11/12 CT/MRI) per 100k  [EQ file]
Correlated with municipal vulnerability, incidence, abandonment, TB mortality, TB-mortality rate.

Caveat: municipal (capital = 1 unit); sub-municipal would need facility coordinates
(CNES FTP lacks them) — possible via CEP-geocoding as a refinement.
ST/EQ extracted to /tmp/cnes_st_sp.parquet and ~/pysus/EQSP2412.parquet.
Output: /tmp/fig_cnes_infrastructure.png
"""
import pandas as pd, numpy as np, re, glob, matplotlib, matplotlib.pyplot as plt
from scipy.stats import spearmanr
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/Abandonment Outcomes/Abandonment Paper/Banco de dados"
def ns(x):
    if pd.isna(x): return None
    x=str(x).strip(); return x[:-1] if x.endswith("P") else x
def nk(x): return x.astype(str).str.strip().str.replace(r'\.0$','',regex=True).str.lstrip("0")

print("CNES establishments (ST) -> primary care per município...")
st=pd.read_parquet("/tmp/cnes_st_sp.parquet")
st["mun6"]=st["CODUFMUN"].astype(str).str.strip()
ubs=st[st["TP_UNID"].isin(["01","02"])].groupby("mun6").size().rename("ubs")

print("CNES equipment (EQ) -> X-ray per município...")
eq=pd.read_parquet(glob.glob("/Users/evelynlepkadelima/pysus/EQSP*.parquet")[-1])
eq["mun6"]=eq["CODUFMUN"].astype(str).str.strip()
eq["qt"]=pd.to_numeric(eq["QT_EXIST"],errors="coerce").fillna(0)
print("  CODEQUIP em TIPEQUIP=1 (imagem) — top:")
print("   ",eq[eq["TIPEQUIP"]=="1"].groupby("CODEQUIP")["qt"].sum().sort_values(ascending=False).head(8).to_dict())
xray=eq[(eq["TIPEQUIP"]=="1")&(eq["CODEQUIP"].isin(["04","05","06"]))&(eq["qt"]>0)]  # Raio X geral (não dentário/mamo/TC)
xray_estab=xray.drop_duplicates(["CNES"]).groupby("mun6").size().rename("xray_estab")  # establishments with raio-X
xray_mach=xray.groupby("mun6")["qt"].sum().rename("xray_mach")                          # number of X-ray machines (capacity)
print(f"  estabelecimentos com raio-X (SP): {xray['CNES'].nunique():,} | máquinas de raio-X: {xray['qt'].sum():,.0f}")

print("Municipal population + vulnerability + TB metrics...")
vs=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)[["CD_SETOR","vuln","pop15"]]
vs=vs[vs["pop15"]>0]; vs["mun6"]=vs["CD_SETOR"].str.slice(0,6)
mpop=vs.groupby("mun6")["pop15"].sum(); mvuln=(vs.assign(w=vs["vuln"]*vs["pop15"]).groupby("mun6")["w"].sum())/mpop
def lc(p,raw=False):
    x=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    if not raw:
        x["t"]=x["cnefe_match"].astype(str).str.extract(r"^(T\d)"); x=x[x["t"].isin(["T1","T2","T3"])]
    x["CD_SETOR"]=x["setor_cnefe"].apply(ns); return x[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
co=pd.concat([lc("/tmp/cohort_with_cnefe.csv",raw=True),lc("/tmp/cohort_baixada_with_cnefe_v2.csv"),lc("/tmp/cohort_sp_outros_with_cnefe.csv")])
m=pd.read_csv(f"{SP}/cohort_with_spatial.csv",usecols=["sinan_clean","notification_date","age_tb","case_outcome","tx_seq"],low_memory=False,dtype={"sinan_clean":str})
m["year"]=pd.to_datetime(m["notification_date"],errors="coerce").dt.year
m=m.sort_values("tx_seq").drop_duplicates("sinan_clean",keep="last").set_index("sinan_clean")
for c in ["year","age_tb","case_outcome"]: co[c]=co["sinan_clean"].map(m[c])
co=co[(co["age_tb"]>=15)&co["year"].between(2013,2024)]; co["mun6"]=co["CD_SETOR"].str.slice(0,6)
sim=pd.read_excel(f"{BD}/LINKAGE SIM (1).xlsx",sheet_name="Limpo",usecols=["SINAN","CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"],dtype=str).dropna(subset=["SINAN"])
sim["all"]=[" ".join([str(x) for x in r if x and str(x)!='nan']).upper().replace(".","") for r in sim[["CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"]].values]
stb=set(nk(sim.loc[sim["all"].str.contains(re.compile(r'A1[5-9]')),"SINAN"]))
oc=co["case_outcome"]
co["death"]=(oc.eq("Obito TB")|nk(co["sinan_clean"]).isin(stb)).astype(int)
co["aband"]=oc.isin(["Abandono","Abandono Primario"]).astype(int)
co["eval"]=(oc.isin(["Cura","Abandono","Abandono Primario","Obito TB","Obito NTB","Falencia/Resistencia"])|(co["death"]==1)).astype(int)
g=co.groupby("mun6").agg(n=("sinan_clean","size"),ne=("eval","sum"),na=("aband","sum"),nd=("death","sum")).reset_index()

d=pd.DataFrame({"pop":mpop,"vuln":mvuln}).reset_index().merge(g,on="mun6",how="left").fillna(0)
d["ubs"]=d["mun6"].map(ubs).fillna(0); d["xray"]=d["mun6"].map(xray_estab).fillna(0); d["xraym"]=d["mun6"].map(xray_mach).fillna(0)
d["ubs_dens"]=d["ubs"]/d["pop"]*1e5
d["xray_dens"]=d["xray"]/d["pop"]*1e5                       # establishments with X-ray per 100k
d["xraymach_dens"]=d["xraym"]/d["pop"]*1e5                  # X-ray MACHINES per 100k (capacity)
d["xraymach_percase"]=np.where(d["n"]>=20,d["xraym"]/d["n"]*100,np.nan)  # machines per 100 TB cases (demand-adjusted)
d["incidence"]=np.where(d["n"]>=10,d["n"]/(d["pop"]*12)*1e5,np.nan)
d["abandonment"]=np.where(d["ne"]>=10,d["na"]/d["ne"]*100,np.nan)
d["tb_mortality"]=np.where(d["n"]>=10,d["nd"]/d["n"]*100,np.nan)  # TB mortality, % of notified
d["death_rate"]=np.where(d["n"]>=10,d["nd"]/(d["pop"]*12)*1e5,np.nan)
e=d[d["n"]>=20].copy()
print(f"\nMunicípios with >=20 cases: {len(e)} | UBS/100k median {e['ubs_dens'].median():.1f} | X-ray estab/100k median {e['xray_dens'].median():.1f}")
print(f"  X-ray machines/100k median {e['xraymach_dens'].median():.1f} | machines per 100 cases median {e['xraymach_percase'].median():.1f}")
print("\nSpearman correlations (municipal, >=20 cases):")
for inf in ["ubs_dens","xray_dens","xraymach_dens","xraymach_percase"]:
    for out in ["vuln","incidence","abandonment","tb_mortality","death_rate"]:
        r=spearmanr(e[inf],e[out],nan_policy="omit").correlation
        print(f"  {inf:10s} vs {out:13s}: rho={r:+.2f}")
    print()

# figure: infrastructure density vs vulnerability + vs death rate
fig,ax=plt.subplots(1,2,figsize=(14,6))
for a,(inf,lab,col) in zip(ax,[("ubs_dens","Primary-care (UBS) /100k","#1f6f8b"),("xraymach_dens","X-ray machines /100k (capacity)","#c0392b")]):
    s=e.dropna(subset=[inf,"vuln"])
    a.scatter(s["vuln"],s[inf],s=16,alpha=0.5,color=col)
    a.set_xlabel("Municipal vulnerability (composite)"); a.set_ylabel(lab)
    a.set_title(f"{lab}\nvs vulnerability: ρ={spearmanr(s['vuln'],s[inf]).correlation:+.2f}",fontsize=11.5,fontweight="bold"); a.grid(alpha=0.3)
fig.suptitle("CNES health-system infrastructure vs vulnerability (municipal) — SP",fontsize=12.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_cnes_infrastructure.png",dpi=150,bbox_inches="tight"); plt.close()
print("Saved /tmp/fig_cnes_infrastructure.png")
