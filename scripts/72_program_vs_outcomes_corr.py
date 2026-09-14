"""Do the diagnostic programme indicators line up with the outcome geographies?
Unit-level correlation of every layer: vulnerability, incidence, abandonment (LTFU),
TB mortality (% of notified and rate per population), molecular-test coverage, laboratory confirmation.
Plus: programme coverage inside each outcome's hotspots vs the rest.

Outcomes/incidence/vulnerability over 2013-2024 (paper standard); diagnostic coverage
over 2020-2024 (current programme). Unit mapping + vulnerability from /tmp/vuln_sectors.csv
(script 64) — no geometry needed. Output: /tmp/fig_program_vs_outcomes.png
"""
import pandas as pd, numpy as np, re, matplotlib, matplotlib.pyplot as plt
from scipy.stats import spearmanr
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/Abandonment Outcomes/Abandonment Paper/Banco de dados"
POP_WIN=0.20
DONE={"Mtb detectado - Rifamp sensivel","Mtb nao detectado","Mtb detectado - Rifamp indeterm","Mtb detectado - Rifamp resistente"}
def ns(x):
    if pd.isna(x): return None
    x=str(x).strip(); return x[:-1] if x.endswith("P") else x
def nk(x): return x.astype(str).str.strip().str.replace(r'\.0$','',regex=True).str.lstrip("0")

print("Loading sector->unit + vulnerability (script 64)...")
sec=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)[["CD_SETOR","vuln","pop15","unit_id"]]
sec=sec[sec["pop15"]>0]
upop=sec.groupby("unit_id")["pop15"].sum()
uvuln=(sec.assign(vw=sec["vuln"]*sec["pop15"]).groupby("unit_id")["vw"].sum())/upop

print("Loading cohort + outcomes + diagnostic fields...")
def lc(p,raw=False):
    x=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    if not raw:
        x["t"]=x["cnefe_match"].astype(str).str.extract(r"^(T\d)"); x=x[x["t"].isin(["T1","T2","T3"])]
    x["CD_SETOR"]=x["setor_cnefe"].apply(ns); return x[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
co=pd.concat([lc("/tmp/cohort_with_cnefe.csv",raw=True),lc("/tmp/cohort_baixada_with_cnefe_v2.csv"),lc("/tmp/cohort_sp_outros_with_cnefe.csv")])
m=pd.read_csv(f"{SP}/cohort_with_spatial.csv",usecols=["sinan_clean","notification_date","age_tb","case_outcome","tmr_tb","lab_confirmed","tx_seq"],low_memory=False,dtype={"sinan_clean":str})
m["year"]=pd.to_datetime(m["notification_date"],errors="coerce").dt.year
m=m.sort_values("tx_seq").drop_duplicates("sinan_clean",keep="last").set_index("sinan_clean")
for c in ["year","age_tb","case_outcome","tmr_tb","lab_confirmed"]: co[c]=co["sinan_clean"].map(m[c])
co=co[(co["age_tb"]>=15)&co["year"].between(2013,2024)]
co["unit_id"]=co["CD_SETOR"].map(sec.set_index("CD_SETOR")["unit_id"].to_dict()); co=co.dropna(subset=["unit_id"])
sim=pd.read_excel(f"{BD}/LINKAGE SIM (1).xlsx",sheet_name="Limpo",usecols=["SINAN","CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"],dtype=str).dropna(subset=["SINAN"])
sim["all"]=[" ".join([str(x) for x in r if x and str(x)!='nan']).upper().replace(".","") for r in sim[["CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"]].values]
stb=set(nk(sim.loc[sim["all"].str.contains(re.compile(r'A1[5-9]')),"SINAN"]))
oc=co["case_outcome"]
co["death"]=(oc.eq("Obito TB")|nk(co["sinan_clean"]).isin(stb)).astype(int)
co["aband"]=oc.isin(["Abandono","Abandono Primario"]).astype(int)
co["eval"]=(oc.isin(["Cura","Abandono","Abandono Primario","Obito TB","Obito NTB","Falencia/Resistencia"])|(co["death"]==1)).astype(int)
# diagnostic coverage (recent 2020-2024)
rec=co["year"].between(2020,2024)
co["mdone"]=co["tmr_tb"].isin(DONE); co["mknown"]=(co["mdone"]|co["tmr_tb"].eq("N/realiz"))&rec; co["mdone"]=co["mdone"]&rec
co["lconf"]=pd.to_numeric(co["lab_confirmed"],errors="coerce"); co["lknown"]=co["lconf"].notna()&rec
co["lc_num"]=((co["lconf"]==1)&co["lknown"]).astype(int)   # confirmed AND recent-known

# ── unit table ───────────────────────────────────────────────────────────────
g=co.groupby("unit_id").agg(n=("sinan_clean","size"),ne=("eval","sum"),na=("aband","sum"),nd=("death","sum"),
    mdone=("mdone","sum"),mknown=("mknown","sum"),lc=("lc_num","sum"),lknown=("lknown","sum")).reset_index()
u=pd.DataFrame({"pop":upop,"vuln":uvuln}).reset_index().merge(g,on="unit_id",how="left").fillna(0)
u["incidence"]=np.where(u["n"]>=10,u["n"]/(u["pop"]*12)*1e5,np.nan)
u["abandonment"]=np.where(u["ne"]>=10,u["na"]/u["ne"]*100,np.nan)
u["tb_mortality"]=np.where(u["n"]>=10,u["nd"]/u["n"]*100,np.nan)         # TB mortality, % of notified
u["death_rate"]=np.where(u["n"]>=10,u["nd"]/(u["pop"]*12)*1e5,np.nan)     # TB mortality rate per pop
u["molecular_cov"]=np.where(u["mknown"]>=10,u["mdone"]/u["mknown"]*100,np.nan)
u["lab_confirm"]=np.where(u["lknown"]>=10,u["lc"]/u["lknown"]*100,np.nan)
elig=u[u["n"]>=10].copy()
print(f"Eligible units: {len(elig)}")

# ── correlation matrix ───────────────────────────────────────────────────────
COLS=["vuln","incidence","abandonment","tb_mortality","death_rate","molecular_cov","lab_confirm"]
LAB=["Vulnerability","Incidence","Abandonment","TB mortality (% notif)","TB mortality rate","Molecular coverage","Lab confirmation"]
C=elig[COLS].corr(method="spearman")
print("\nSpearman correlation matrix (unit level):")
print(C.round(2).to_string())

# ── programme coverage inside each outcome's hotspots vs rest ─────────────────
TOTAL=sec["pop15"].sum()
def hotspots(by):
    d=elig.dropna(subset=[by]).sort_values(by,ascending=False).copy(); d["c"]=d["pop"].cumsum(); mm=d["c"]<=TOTAL*POP_WIN
    if mm.sum()<len(d): mm.iloc[mm.sum()]=True
    return set(d[mm]["unit_id"])
HS={"Incidence":hotspots("incidence"),"Abandonment":hotspots("abandonment"),"Mortality":hotspots("death_rate"),"Vulnerability":hotspots("vuln")}
print("\nDiagnostic coverage inside each hotspot type vs rest (pooled over cases):")
def pooled(ids,num,den):
    s=co[co["unit_id"].isin(ids)]; return s[num].sum()/s[den].sum()*100 if s[den].sum() else np.nan
rows=[]
for lens,ids in HS.items():
    rest=set(elig["unit_id"])-ids
    mc_in=pooled(ids,"mdone","mknown"); mc_out=pooled(rest,"mdone","mknown")
    lc_in=pooled(ids,"lc_num","lknown"); lc_out=pooled(rest,"lc_num","lknown")
    rows.append((lens,mc_in,mc_out,lc_in,lc_out))
    print(f"  {lens:14s} molecular {mc_in:4.1f}% (in) vs {mc_out:4.1f}% (rest) | lab-conf {lc_in:4.1f}% vs {lc_out:4.1f}%")

# ── figure ───────────────────────────────────────────────────────────────────
fig,(axA,axB)=plt.subplots(1,2,figsize=(16,6.5),gridspec_kw={"width_ratios":[1.15,1]})
im=axA.imshow(C.values,cmap="RdBu_r",vmin=-1,vmax=1)
axA.set_xticks(range(len(LAB))); axA.set_xticklabels(LAB,rotation=45,ha="right",fontsize=9.5)
axA.set_yticks(range(len(LAB))); axA.set_yticklabels(LAB,fontsize=9.5)
for i in range(len(COLS)):
    for j in range(len(COLS)):
        axA.text(j,i,f"{C.values[i,j]:.2f}",ha="center",va="center",fontsize=8.5,color="white" if abs(C.values[i,j])>0.55 else "#222")
axA.set_title("A)  Unit-level Spearman correlation of all layers",fontsize=11.5,fontweight="bold")
fig.colorbar(im,ax=axA,shrink=0.7,label="Spearman ρ")
labs=[r[0] for r in rows]; x=np.arange(len(labs)); w=0.2
axB.bar(x-1.5*w,[r[1] for r in rows],w,color="#c0392b",label="molecular — in hotspot")
axB.bar(x-0.5*w,[r[2] for r in rows],w,color="#e8a39a",label="molecular — rest")
axB.bar(x+0.5*w,[r[3] for r in rows],w,color="#1f6f8b",label="lab-conf — in hotspot")
axB.bar(x+1.5*w,[r[4] for r in rows],w,color="#a8cdd8",label="lab-conf — rest")
axB.set_xticks(x); axB.set_xticklabels(labs,fontsize=9.5); axB.set_ylabel("Coverage %"); axB.set_ylim(0,100)
axB.set_title("B)  Diagnostic coverage inside each hotspot type vs rest",fontsize=11.5,fontweight="bold")
axB.legend(fontsize=8,ncol=2,loc="lower center"); axB.grid(alpha=0.3,axis="y")
fig.suptitle("Programme diagnostic indicators vs the outcome geographies — SP adults",fontsize=13,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_program_vs_outcomes.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_program_vs_outcomes.png")
