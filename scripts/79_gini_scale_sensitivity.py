"""APPENDIX — sensitivity of the geographic-concentration (Gini) to the spatial scale of
aggregation (the modifiable areal unit problem, MAUP). The three lenses (incidence,
treatment abandonment, TB mortality) are re-ranked and the Gini recomputed at four
nested scales — census sector -> operational unit (FCU/neighbourhood/district) ->
municipal district -> municipality. We report the crude Gini and the de-noised
(cross-fit) Gini at each scale: the absolute value falls as units coarsen, but
substantial concentration, and the ordering abandonment > mortality > incidence,
persist at every scale.
Output: /tmp/fig_gini_scale_sensitivity.png  + printed table.
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, re, matplotlib, matplotlib.pyplot as plt
np.random.seed(20240625)
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/Abandonment Outcomes/Abandonment Paper/Banco de dados"
CAPITAL,FCU_MIN="3550308",5000
ADULT=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
def ns(x):
    if pd.isna(x): return None
    x=str(x).strip(); return x[:-1] if x.endswith("P") else x
def nk(s): return s.astype(str).str.strip().str.replace(r'\.0$','',regex=True).str.lstrip("0")

print("Sectors + the four scale labels...")
sec=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp")
for c in ["CD_SETOR","CD_MUN","CD_DIST"]: sec[c]=sec[c].astype(str)
pop=pd.read_csv(f"{SP}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",sep=";",encoding="latin-1",decimal=",",usecols=["CD_SETOR","v0001"],dtype={"CD_SETOR":str},low_memory=False)
pop["pt"]=pd.to_numeric(pop["v0001"],errors="coerce").fillna(0)
with zipfile.ZipFile(f"{SP}/IBGE_2022_extended/demografia.zip") as z:
    dem=pd.read_csv(z.open("Agregados_por_setores_demografia_BR.csv"),sep=";",encoding="latin-1",decimal=",",usecols=["CD_setor"]+ADULT,dtype={"CD_setor":str},low_memory=False)
dem["pop_adult"]=dem[ADULT].apply(pd.to_numeric,errors="coerce").fillna(0).sum(axis=1)
sec=sec.merge(pop[["CD_SETOR","pt"]],on="CD_SETOR",how="left").merge(dem[["CD_setor","pop_adult"]].rename(columns={"CD_setor":"CD_SETOR"}),on="CD_SETOR",how="left")
sec["pt"]=sec["pt"].fillna(0); sec["pop_adult"]=sec["pop_adult"].fillna(0)
sec=sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["pt"]>=100)].copy()
# operational (hybrid) unit
def bkey(r):
    if r["CD_MUN"]==CAPITAL: return f"dist_{r['CD_DIST']}"
    if pd.notna(r.get("NM_BAIRRO")): return f"bairro_{r['CD_MUN']}_{r['NM_BAIRRO']}"
    if pd.notna(r.get("NM_DIST")): return f"dist_{r['CD_DIST']}"
    return f"mun_{r['CD_MUN']}"
sec["bid"]=sec.apply(bkey,axis=1)
fp=sec[sec["NM_FCU"].notna()].groupby("NM_FCU")["pop_adult"].sum(); qf=set(fp[fp>=FCU_MIN].index)
sec["unit"]=sec.apply(lambda r: f"fcu__{r['NM_FCU']}" if (pd.notna(r['NM_FCU']) and r['NM_FCU'] in qf) else r["bid"],axis=1)
SCALES=[("Census sector","CD_SETOR"),("Operational unit","unit"),("District","CD_DIST"),("Municipality","CD_MUN")]

print("Cohort + outcomes (integrated mortality)...")
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
# attach each scale label to every case via its sector
s2=sec.set_index("CD_SETOR")
for _,col in SCALES:
    co[col]=co["CD_SETOR"].map(s2[col]) if col!="CD_SETOR" else co["CD_SETOR"]
co=co.dropna(subset=[c for _,c in SCALES])

def wgini(counts,popv):
    m=popv>0; n=counts[m]; p=popv[m]
    if n.sum()==0: return np.nan
    rate=n/p; o=np.argsort(-rate)
    cp=np.concatenate([[0],np.cumsum(p[o])/p.sum()]); cv=np.concatenate([[0],np.cumsum(n[o])/n.sum()])
    return 2*np.trapz(cv,cp)-1
def cvgini(idx,popv,K,B=80):
    g=[]
    bc=lambda a: np.bincount(a,minlength=K).astype(float)
    for _ in range(B):
        h=np.random.rand(len(idx))<0.5; a=bc(idx[h]); b=bc(idx[~h])
        for rk,vl in [(a,b),(b,a)]:
            m=popv>0; ra=rk[m]/popv[m]; vb=vl[m]; pp=popv[m]
            if vb.sum()==0: continue
            o=np.argsort(-ra); cp=np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]); cv=np.concatenate([[0],np.cumsum(vb[o])/vb.sum()])
            g.append(2*np.trapz(cv,cp)-1)
    return np.mean(g)

LENS=[("Incidence","_all","#1a3d5c"),("TB mortality","death","#7a3a8c"),("Abandonment","aband","#d98000")]
rows=[]; print(f"\n{'Scale':16s}{'n units':>9}{'':4}"+"".join(f"{l:>26s}" for l,_,_ in LENS))
print(" "*29+"".join(f"{'crude / de-noised':>26s}" for _ in LENS))
for sname,col in SCALES:
    upop=sec.groupby(col)["pop_adult"].sum(); units=list(upop.index); idxmap={u:i for i,u in enumerate(units)}
    K=len(units); popv=upop.values
    ci=co[col].map(idxmap)
    res={}
    for lname,flag,_ in LENS:
        ev=ci if flag=="_all" else ci[co[flag]==1]
        cnt=np.bincount(ev.values.astype(int),minlength=K).astype(float)
        res[lname]=(wgini(cnt,popv),cvgini(ev.values.astype(int),popv,K))
    rows.append((sname,K,res))
    print(f"{sname:16s}{K:>9d}{'':4}"+"".join(f"{res[l][0]:>11.3f} /{res[l][1]:>11.3f}" for l,_,_ in LENS))

# figure: de-noised Gini vs scale (3 lenses)
order=[r[0] for r in rows]; x=np.arange(len(order))
fig,ax=plt.subplots(figsize=(9,5.6))
for lname,_,col in LENS:
    yd=[r[2][lname][1] for r in rows]; yc=[r[2][lname][0] for r in rows]
    ax.plot(x,yd,"-o",color=col,lw=2.4,ms=7,label=f"{lname} (de-noised)")
    ax.plot(x,yc,":",color=col,lw=1.3,alpha=0.6)
ax.set_xticks(x); ax.set_xticklabels([f"{r[0]}\n(n={r[1]:,})" for r in rows],fontsize=9.5)
ax.set_ylabel("Gini coefficient"); ax.set_ylim(0,0.65); ax.grid(alpha=0.3,axis="y")
ax.set_title("Concentration (Gini) by spatial scale — solid = de-noised, dotted = crude\nMagnitude falls as units coarsen (MAUP), but concentration persists at every scale",fontsize=11.5,fontweight="bold")
ax.legend(fontsize=9.5,loc="upper right")
ax.annotate("finer  →  coarser",xy=(0.5,-0.16),xycoords="axes fraction",ha="center",fontsize=10,color="#666")
plt.tight_layout(); plt.savefig("/tmp/fig_gini_scale_sensitivity.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_gini_scale_sensitivity.png")
