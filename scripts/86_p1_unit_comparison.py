"""P1 (geographic concentration) re-run on the NEW regionalisation unit, compared with the
operational unit (and sector/district/municipality as context). For the three lenses
(incidence, treatment abandonment, integrated TB mortality) we report the crude and the
de-noised (cross-fit) Gini at each unit definition, plus Lorenz curves (operational vs
regionalisation). De-noised values are the headline (the P1 decision). Output:
/tmp/fig_p1_unit_comparison.png + printed table.
"""
import pandas as pd, numpy as np, re, matplotlib, matplotlib.pyplot as plt
np.random.seed(20240625)
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/Abandonment Outcomes/Abandonment Paper/Banco de dados"
def ns(x):
    if pd.isna(x): return None
    x=str(x).strip(); return x[:-1] if x.endswith("P") else x
def nk(s): return s.astype(str).str.strip().str.replace(r'\.0$','',regex=True).str.lstrip("0")

print("Sector -> unit lookups (operational + regionalisation + admin scales)...")
sec=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)[["CD_SETOR","unit_id","pop15"]]
sec=sec[sec["pop15"]>0]
rg=pd.read_csv("/tmp/regions_sectors.csv",dtype={"CD_SETOR":str})[["CD_SETOR","region_id"]]
sec=sec.merge(rg,on="CD_SETOR",how="left")
sec["sector"]=sec["CD_SETOR"]; sec["district"]=sec["CD_SETOR"].str.slice(0,9); sec["municipality"]=sec["CD_SETOR"].str.slice(0,7)
sec["region_id"]=sec["region_id"].fillna("DIST_"+sec["district"])   # rare uncovered -> district fallback

print("Cohort + outcomes (integrated TB mortality)...")
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
look=sec.set_index("CD_SETOR")
for c in ["unit_id","region_id","sector","district","municipality"]: co[c]=co["CD_SETOR"].map(look[c])
co=co.dropna(subset=["region_id"])

def wgini(c,p):
    m=p>0; n=c[m]; pp=p[m]
    if n.sum()==0: return np.nan
    r=n/pp; o=np.argsort(-r); cp=np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]); cv=np.concatenate([[0],np.cumsum(n[o])/n.sum()])
    return 2*np.trapz(cv,cp)-1
def cvg(ix,p,K,B=80):
    g=[]; bc=lambda a:np.bincount(a,minlength=K).astype(float)
    for _ in range(B):
        h=np.random.rand(len(ix))<0.5; a=bc(ix[h]); b=bc(ix[~h])
        for rk,vl in [(a,b),(b,a)]:
            m=p>0; ra=rk[m]/p[m]; vb=vl[m]; pp=p[m]
            if vb.sum()==0: continue
            o=np.argsort(-ra); cp=np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]); cv=np.concatenate([[0],np.cumsum(vb[o])/vb.sum()])
            g.append(2*np.trapz(cv,cp)-1)
    return np.mean(g)
def lorenz(c,p):
    m=p>0; n=c[m]; pp=p[m]; r=n/pp; o=np.argsort(r)
    return np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]),np.concatenate([[0],np.cumsum(n[o])/n.sum()])

UNITS=[("Census sector","sector"),("Operational unit","unit_id"),("Regionalisation (new)","region_id"),("District","district"),("Municipality","municipality")]
LENS=[("Incidence",None),("TB mortality",co["death"]==1),("Abandonment",co["aband"]==1)]
print(f"\n{'Unit':22s}{'n units':>9}   "+"".join(f"{l:>22s}" for l,_ in LENS))
print(" "*31+"".join(f"{'crude / de-noised':>22s}" for _ in LENS))
store={}
for uname,col in UNITS:
    pv=sec.groupby(col)["pop15"].sum(); units=list(pv.index); idx={u:i for i,u in enumerate(units)}; K=len(units); popv=pv.values
    ci=co[col].map(idx)
    row=[]
    for lname,mask in LENS:
        ev=ci if mask is None else ci[mask]
        cnt=np.bincount(ev.values.astype(int),minlength=K).astype(float)
        cr=wgini(cnt,popv); dn=cvg(ev.values.astype(int),popv,K); row.append((cr,dn))
        if lname=="Incidence": store[uname]=lorenz(cnt,popv)
    print(f"{uname:22s}{K:>9,d}   "+"".join(f"{cr:>9.3f} /{dn:>9.3f}" for cr,dn in row))

# Lorenz figure: incidence, operational vs regionalisation vs sector
fig,ax=plt.subplots(figsize=(7.5,7))
ax.plot([0,1],[0,1],"--",color="#999",lw=1.3,label="equality (Gini=0)")
for uname,col,c in [("Census sector","sector","#9aa7b1"),("Operational unit","unit_id","#1f6f8b"),("Regionalisation (new)","region_id","#c0392b")]:
    cp,cv=store[uname]; ax.plot(cp,cv,color=c,lw=2.4,label=uname)
ax.set_xlabel("Cumulative share of adult population"); ax.set_ylabel("Cumulative share of TB cases")
ax.set_title("P1 — concentration of TB incidence by spatial unit (Lorenz)\nthe new regionalisation unit sits between sector and operational",fontsize=11.5,fontweight="bold")
ax.legend(fontsize=10,loc="upper left"); ax.grid(alpha=0.3); ax.set_xlim(0,1); ax.set_ylim(0,1)
plt.tight_layout(); plt.savefig("/tmp/fig_p1_unit_comparison.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_p1_unit_comparison.png")
