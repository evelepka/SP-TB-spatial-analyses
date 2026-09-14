"""Rebuild the analytical unit at the BAIRRO (neighbourhood) level, using the bairro that
the CNEFE address registry assigns to each census sector — far denser than the IBGE
shapefile's NM_BAIRRO (which is empty for the state capital). This unit respects social
boundaries (a favela and an adjacent affluent neighbourhood are different bairros, so they
stay distinct) and resolves the capital, where the previous scheme collapsed to 96 coarse
districts.

Build:
  1. setor -> bairro  : the modal (address-weighted) bairro of each census sector, from the
     CNEFE municipal indices (idx_<mun>.csv: rua,num,bairro,setor,n).
  2. bairro unit id    : (município, normalised bairro). Sectors with no CNEFE bairro fall
     back to their district (CD_SETOR[:9]).
  3. population         : adult (>=15) census population summed per bairro = the denominator.
  4. cases/outcomes     : each case -> its sector's bairro (numerator); integrated TB-death.
Outputs the composition + crude/de-noised Gini (incidence, abandonment, TB mortality) at
the bairro level, and /tmp/bairro_units.csv (CD_SETOR -> bairro unit) for downstream use.
"""
import pandas as pd, geopandas as gpd, numpy as np, glob, re, unicodedata, zipfile
np.random.seed(20240625)
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/Abandonment Outcomes/Abandonment Paper/Banco de dados"
CAPITAL="3550308"; ADULT=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
ABBR={"JD":"JARDIM","JDIM":"JARDIM","VL":"VILA","PQ":"PARQUE","CJ":"CONJUNTO","CONJ":"CONJUNTO",
      "RES":"RESIDENCIAL","STA":"SANTA","STO":"SANTO","PRES":"PRESIDENTE","PROF":"PROFESSOR","DR":"DOUTOR"}
def normb(s):
    if pd.isna(s) or str(s).strip()=="": return None
    s=unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().upper()
    s=re.sub(r"[^A-Z0-9 ]"," ",s); s=re.sub(r"\s+"," ",s).strip()
    if not s: return None
    return " ".join(ABBR.get(t,t) for t in s.split())
def stripP(s): s=str(s).strip(); return s[:-1] if s.endswith("P") else s

print("1) setor -> modal bairro from CNEFE indices...")
idx_files=glob.glob(f"{SP}/IBGE_2022_extended/*/indices/idx_*.csv")
print(f"   {len(idx_files)} municipal indices")
acc={}  # (CD_SETOR, bairro_norm) -> sum n
for fp in idx_files:
    d=pd.read_csv(fp,usecols=["bairro","setor","n"],dtype={"setor":str},low_memory=False)
    d["CD_SETOR"]=d["setor"].map(stripP); d["b"]=d["bairro"].map(normb); d=d.dropna(subset=["CD_SETOR","b"])
    d["n"]=pd.to_numeric(d["n"],errors="coerce").fillna(1)
    g=d.groupby(["CD_SETOR","b"])["n"].sum()
    for (cs,b),nn in g.items(): acc[(cs,b)]=acc.get((cs,b),0)+nn
ab=pd.DataFrame([(cs,b,nn) for (cs,b),nn in acc.items()],columns=["CD_SETOR","b","n"])
sec2bairro=ab.sort_values("n").drop_duplicates("CD_SETOR",keep="last")[["CD_SETOR","b"]]  # modal
print(f"   sectors with a CNEFE bairro: {len(sec2bairro):,}")

print("2) census population per sector (adult >=15)...")
sec=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp")[["CD_SETOR","CD_TIPO"]]
sec["CD_SETOR"]=sec["CD_SETOR"].astype(str)
pop=pd.read_csv(f"{SP}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",sep=";",encoding="latin-1",decimal=",",usecols=["CD_SETOR","v0001"],dtype={"CD_SETOR":str},low_memory=False)
pop["pt"]=pd.to_numeric(pop["v0001"],errors="coerce").fillna(0)
with zipfile.ZipFile(f"{SP}/IBGE_2022_extended/demografia.zip") as z:
    dem=pd.read_csv(z.open("Agregados_por_setores_demografia_BR.csv"),sep=";",encoding="latin-1",decimal=",",usecols=["CD_setor"]+ADULT,dtype={"CD_setor":str},low_memory=False)
dem["pa"]=dem[ADULT].apply(pd.to_numeric,errors="coerce").fillna(0).sum(axis=1)
sec=sec.merge(pop[["CD_SETOR","pt"]],on="CD_SETOR",how="left").merge(dem[["CD_setor","pa"]].rename(columns={"CD_setor":"CD_SETOR"}),on="CD_SETOR",how="left")
sec["pt"]=sec["pt"].fillna(0); sec["pa"]=sec["pa"].fillna(0)
sec=sec[sec["CD_TIPO"].astype(str).isin(["0","1"])&(sec["pt"]>=100)].copy()

print("3) assign each sector to a bairro unit (fallback: district)...")
sec=sec.merge(sec2bairro,on="CD_SETOR",how="left")
sec["mun"]=sec["CD_SETOR"].str.slice(0,7); sec["dist"]=sec["CD_SETOR"].str.slice(0,9)
sec["bairro_unit"]=np.where(sec["b"].notna(), sec["mun"]+"__"+sec["b"].astype(str), "DISTFB_"+sec["dist"])
sec["src"]=np.where(sec["b"].notna(),"bairro","district_fallback")
cov_sec=(sec["src"]=="bairro").mean()*100; cov_pop=sec.loc[sec["src"]=="bairro","pa"].sum()/sec["pa"].sum()*100
cap=sec["mun"]==CAPITAL
print(f"   coverage: {cov_sec:.1f}% of sectors / {cov_pop:.1f}% of pop on a CNEFE bairro")
print(f"   CAPITAL coverage: {(sec.loc[cap,'src']=='bairro').mean()*100:.1f}% of sectors")
sec[["CD_SETOR","bairro_unit","b","src"]].to_csv("/tmp/bairro_units.csv",index=False)

upop=sec.groupby("bairro_unit")["pa"].sum()
print(f"\n=== COMPOSITION ===")
print(f"   total bairro units: {len(upop):,}  (vs 3,014 operational, 1,033 districts before)")
print(f"   units in the CAPITAL: {sec.loc[cap,'bairro_unit'].nunique():,}  (was 96 districts)")
print(f"   adult pop per unit — median {upop.median():,.0f} | IQR {upop.quantile(.25):,.0f}-{upop.quantile(.75):,.0f} | max {upop.max():,.0f}")

print("\n4) cases + outcomes -> bairro...")
def ns(x):
    if pd.isna(x): return None
    x=str(x).strip(); return x[:-1] if x.endswith("P") else x
def nk(s): return s.astype(str).str.strip().str.replace(r'\.0$','',regex=True).str.lstrip("0")
def lc(p,raw=False):
    d=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    if not raw:
        d["t"]=d["cnefe_match"].astype(str).str.extract(r"^(T\d)"); d=d[d["t"].isin(["T1","T2","T3"])]
    d["CD_SETOR"]=d["setor_cnefe"].apply(ns); return d[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
co=pd.concat([lc("/tmp/cohort_with_cnefe.csv",raw=True),lc("/tmp/cohort_baixada_with_cnefe_v2.csv"),lc("/tmp/cohort_sp_outros_with_cnefe.csv")])
m=pd.read_csv(f"{SP}/cohort_with_spatial.csv",usecols=["sinan_clean","notification_date","age_tb","case_outcome","tx_seq"],low_memory=False,dtype={"sinan_clean":str})
m["year"]=pd.to_datetime(m["notification_date"],errors="coerce").dt.year
m=m.sort_values("tx_seq").drop_duplicates("sinan_clean",keep="last").set_index("sinan_clean")
co["year"]=co["sinan_clean"].map(m["year"]); co["age"]=co["sinan_clean"].map(m["age_tb"]); co["oc"]=co["sinan_clean"].map(m["case_outcome"])
co=co[(co["age"]>=15)&co["year"].between(2013,2024)]
sim=pd.read_excel(f"{BD}/LINKAGE SIM (1).xlsx",sheet_name="Limpo",usecols=["SINAN","CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"],dtype=str).dropna(subset=["SINAN"])
sim["all"]=[" ".join([str(x) for x in r if x and str(x)!='nan']).upper().replace(".","") for r in sim[["CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"]].values]
stb=set(nk(sim.loc[sim["all"].str.contains(re.compile(r'A1[5-9]')),"SINAN"]))
co["death"]=(co["oc"].eq("Obito TB")|nk(co["sinan_clean"]).isin(stb)).astype(int)
co["aband"]=co["oc"].isin(["Abandono","Abandono Primario"]).astype(int)
co["bu"]=co["CD_SETOR"].map(sec.set_index("CD_SETOR")["bairro_unit"].to_dict()); co=co.dropna(subset=["bu"])
units=list(upop.index); idx={u:i for i,u in enumerate(units)}; K=len(units); popv=upop.values
co["ui"]=co["bu"].map(idx)
print(f"   cases on a unit: {len(co):,}")

def wgini(c,p):
    m=p>0; n=c[m]; pp=p[m]
    if n.sum()==0: return np.nan
    r=n/pp; o=np.argsort(-r); cp=np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]); cv=np.concatenate([[0],np.cumsum(n[o])/n.sum()])
    return 2*np.trapz(cv,cp)-1
def cvg(ix,p,B=80):
    g=[]; bc=lambda a:np.bincount(a,minlength=K).astype(float)
    for _ in range(B):
        h=np.random.rand(len(ix))<0.5; a=bc(ix[h]); b=bc(ix[~h])
        for rk,vl in [(a,b),(b,a)]:
            m=p>0; ra=rk[m]/p[m]; vb=vl[m]; pp=p[m]
            if vb.sum()==0: continue
            o=np.argsort(-ra); cp=np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]); cv=np.concatenate([[0],np.cumsum(vb[o])/vb.sum()])
            g.append(2*np.trapz(cv,cp)-1)
    return np.mean(g)

print(f"\n=== BAIRRO-LEVEL Gini (crude / de-noised) ===")
for lab,mask in [("Incidence",None),("TB mortality",co["death"]==1),("Abandonment",co["aband"]==1)]:
    ev=co["ui"] if mask is None else co.loc[mask,"ui"]
    cnt=np.bincount(ev.values.astype(int),minlength=K).astype(float)
    print(f"   {lab:13s}: {wgini(cnt,popv):.3f} / {cvg(ev.values.astype(int),popv):.3f}")
print("\nSaved /tmp/bairro_units.csv")
