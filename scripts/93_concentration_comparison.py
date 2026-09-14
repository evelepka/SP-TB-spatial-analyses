"""P1 headline figure (clean): how concentrated is each lens, before and after noise
correction? Bars = Gini of cases, treatment abandonment, and TB mortality, shown NAIVE
(faded) and DE-NOISED (split-sample cross-fit, solid). Rarer events inflate the naive Gini,
so the de-noised bars are the honest comparison — and there abandonment is the single most
concentrated lens (above cases and mortality). All rates age-standardised (indirect, SP
reference; same machinery as script 61). Output: /tmp/fig_concentration_comparison.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, re, matplotlib, matplotlib.pyplot as plt
np.random.seed(20240625); matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SPATIAL="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/Abandonment Outcomes/Abandonment Paper/Banco de dados"
CAPITAL,FCU_MIN="3550308",5000
ADULT_COLS=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
def norm_setor(s):
    if pd.isna(s): return None
    s=str(s).strip(); return s[:-1] if s.endswith("P") else s
def norm_key(s): return s.astype(str).str.strip().str.replace(r'\.0$','',regex=True).str.lstrip("0")

print("Building units (same as script 61)...")
sec22=gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]=sec22["CD_MUN"].astype(str); sec22["CD_SETOR"]=sec22["CD_SETOR"].astype(str)
pop_df=pd.read_csv(f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",sep=";",encoding="latin-1",decimal=",",usecols=["CD_SETOR","v0001"],dtype={"CD_SETOR":str},low_memory=False)
pop_df["pop_total"]=pd.to_numeric(pop_df["v0001"],errors="coerce").fillna(0)
with zipfile.ZipFile(f"{SPATIAL}/IBGE_2022_extended/demografia.zip") as z:
    with z.open("Agregados_por_setores_demografia_BR.csv") as fh:
        demo=pd.read_csv(fh,sep=";",encoding="latin-1",decimal=",",usecols=["CD_setor"]+ADULT_COLS,dtype={"CD_setor":str},low_memory=False)
for _b in ADULT_COLS: demo[_b]=pd.to_numeric(demo[_b],errors="coerce").fillna(0)
demo["pop_adult"]=demo[ADULT_COLS].sum(axis=1)
demo=demo.rename(columns={"CD_setor":"CD_SETOR"})
sec=sec22.merge(pop_df[["CD_SETOR","pop_total"]],on="CD_SETOR",how="left").merge(demo[["CD_SETOR","pop_adult"]+ADULT_COLS],on="CD_SETOR",how="left")
sec["pop_total"]=sec["pop_total"].fillna(0); sec["pop_adult"]=sec["pop_adult"].fillna(0)
sec_res=sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["pop_total"]>=100)].copy()
def bkey(r):
    if str(r["CD_MUN"])==CAPITAL: return f"dist_{r['CD_DIST']}"
    if pd.notna(r.get("NM_BAIRRO")): return f"bairro_{r['CD_MUN']}_{r['NM_BAIRRO']}"
    if pd.notna(r.get("NM_DIST")): return f"dist_{r['CD_DIST']}"
    return f"mun_{r['CD_MUN']}"
sec_res["bairro_id"]=sec_res.apply(bkey,axis=1)
fcu_pop=sec_res[sec_res["NM_FCU"].notna()].groupby("NM_FCU")["pop_adult"].sum(); qf=set(fcu_pop[fcu_pop>=FCU_MIN].index)
sec_res["unit_id"]=sec_res.apply(lambda r: f"fcu__{r['NM_FCU']}" if (pd.notna(r['NM_FCU']) and r['NM_FCU'] in qf) else r["bairro_id"],axis=1)
unit_pop=sec_res.groupby("unit_id")["pop_adult"].sum()

print("SIM + cohort...")
sim=pd.read_excel(f"{BD}/LINKAGE SIM (1).xlsx",sheet_name="Limpo",usecols=["SINAN","CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"],dtype=str).dropna(subset=["SINAN"])
def cc(*v): return " ".join([str(x) for x in v if x and str(x)!='nan']).upper().replace(".","")
sim["alllines"]=[cc(*r) for r in sim[["CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"]].values]
sim["k"]=norm_key(sim["SINAN"]); sim_tb=set(sim.loc[sim["alllines"].str.contains(re.compile(r'A1[5-9]')),"k"])
def load_co(p,raw=False):
    d=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    if not raw:
        d["tier"]=d["cnefe_match"].astype(str).str.extract(r"^(T\d)"); d=d[d["tier"].isin(["T1","T2","T3"])]
    d["CD_SETOR"]=d["setor_cnefe"].apply(norm_setor); return d[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
cohort=pd.concat([load_co("/tmp/cohort_with_cnefe.csv",raw=True),load_co("/tmp/cohort_baixada_with_cnefe_v2.csv"),load_co("/tmp/cohort_sp_outros_with_cnefe.csv")],ignore_index=True)
meta=pd.read_csv(f"{SPATIAL}/cohort_with_spatial.csv",usecols=["sinan_clean","notification_date","age_tb","case_outcome","tx_seq"],low_memory=False,dtype={"sinan_clean":str})
meta["year"]=pd.to_datetime(meta["notification_date"],errors="coerce").dt.year
meta=meta.sort_values("tx_seq").drop_duplicates("sinan_clean",keep="last").set_index("sinan_clean")
cohort["year"]=cohort["sinan_clean"].map(meta["year"]); cohort["age_tb"]=cohort["sinan_clean"].map(meta["age_tb"]); cohort["outcome"]=cohort["sinan_clean"].map(meta["case_outcome"])
cohort["unit_id"]=cohort["CD_SETOR"].map(sec_res.set_index("CD_SETOR")["unit_id"].to_dict())
cohort=cohort[(cohort["age_tb"]>=15)&cohort["year"].between(2013,2024)].dropna(subset=["unit_id"])
ck=norm_key(cohort["sinan_clean"])
cohort["d_tb"]=cohort["outcome"].eq("Obito TB")|ck.isin(sim_tb)
cohort["aband"]=cohort["outcome"].isin(["Abandono","Abandono Primario"])
pooled=cohort.groupby("unit_id").size(); elig=[u for u in pooled.index if pooled[u]>=10]
pe=unit_pop.reindex(elig); pev=pe.values; eidx={u:i for i,u in enumerate(elig)}
coh=cohort[cohort["unit_id"].isin(elig)].copy(); coh["ui"]=coh["unit_id"].map(eidx)

EDGES=[15,20,25,30,40,50,60,70,200]; coh["band"]=pd.cut(coh["age_tb"],EDGES,right=False,labels=False).astype(int)
Pb=sec_res.groupby("unit_id")[ADULT_COLS].sum().reindex(elig).fillna(0).to_numpy(float); popband=Pb.sum(axis=0)
def adj_factor(mask):
    cb=np.bincount(coh["band"].values[mask],minlength=8).astype(float)
    rate=np.divide(cb,popband,where=popband>0,out=np.zeros(8)); E_age=Pb@rate; R=cb.sum()/popband.sum()
    return np.divide(R*pev,E_age,where=E_age>0,out=np.ones_like(E_age))
def counts(ui): return np.bincount(ui,minlength=len(elig)).astype(float)
def gini(n,f):
    nn=(n*f)[pev>0]; pp=pev[pev>0]
    if nn.sum()==0: return np.nan
    r=nn/pp; o=np.argsort(-r); cp=np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]); cv=np.concatenate([[0],np.cumsum(nn[o])/nn.sum()])
    return 2*np.trapz(cv,cp)-1
def cv_gini(ui_array,f,B=150):
    g=[]
    for _ in range(B):
        h=np.random.rand(len(ui_array))<0.5; a=counts(ui_array[h])*f; b=counts(ui_array[~h])*f
        for rk,vl in [(a,b),(b,a)]:
            m=pev>0; ra=rk[m]/pev[m]; vb=vl[m]; pp=pev[m]
            if vb.sum()==0: continue
            o=np.argsort(-ra); cp=np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]); cv=np.concatenate([[0],np.cumsum(vb[o])/vb.sum()])
            g.append(2*np.trapz(cv,cp)-1)
    return np.mean(g)

LENS=[("TB cases",np.ones(len(coh),bool),"#1a3d5c"),
      ("TB mortality",coh["d_tb"].values,"#7a0177"),
      ("Treatment\nabandonment",coh["aband"].values,"#1f6f8b")]
rows=[]
for name,mask,col in LENS:
    f=adj_factor(mask); ui=coh[mask]["ui"].values
    rows.append((name,gini(counts(ui),f),cv_gini(ui,f),col))
    print(f"  {name.replace(chr(10),' '):22s} naive={rows[-1][1]:.3f}  de-noised={rows[-1][2]:.3f}")

fig,ax=plt.subplots(figsize=(8.4,5.6))
x=np.arange(len(rows)); w=0.38
ax.bar(x-w/2,[r[1] for r in rows],w,color=[r[3] for r in rows],alpha=0.32,label="naïve (noise-inflated)")
ax.bar(x+w/2,[r[2] for r in rows],w,color=[r[3] for r in rows],label="de-noised (cross-fit)")
for i,r in enumerate(rows):
    ax.text(i-w/2,r[1]+0.006,f"{r[1]:.2f}",ha="center",fontsize=9,color="#666")
    ax.text(i+w/2,r[2]+0.006,f"{r[2]:.2f}",ha="center",fontsize=10,fontweight="bold",color=r[3])
ax.axhline(rows[0][2],ls="--",color="#1a3d5c",lw=1.2,alpha=0.6)
ax.text(2.45,rows[0][2]+0.004,"cases (de-noised)",fontsize=8,color="#1a3d5c",ha="right",va="bottom")
ax.set_xticks(x); ax.set_xticklabels([r[0] for r in rows],fontsize=11)
ax.set_ylabel("Gini of geographic concentration"); ax.set_ylim(0,0.55); ax.grid(axis="y",alpha=0.3)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(facecolor="#888",alpha=0.32,label="naïve (noise-inflated)"),Patch(facecolor="#888",label="de-noised (cross-fit)")],fontsize=9.5,loc="upper left")
ax.set_title("Treatment abandonment is the most spatially concentrated lens\n(rarer events inflate the naïve Gini; de-noised, abandonment still leads) — SP adults 2013–2024",fontsize=11.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_concentration_comparison.png",dpi=150,bbox_inches="tight"); plt.close()
print("Saved /tmp/fig_concentration_comparison.png")
