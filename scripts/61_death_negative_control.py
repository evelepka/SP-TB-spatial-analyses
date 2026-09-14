"""Negative control (advisor): non-TB deaths among TB patients should NOT be
spatially concentrated if the TB-death clustering is genuinely TB-specific
(driven by where transmission/vulnerability concentrate) rather than an artefact
of the death-ascertainment process or of where dying TB patients happen to live.

Markers (integrated TBweb + SIM, same sources as script 60):
  - TB death       = Obito TB (TBweb)  OR  SIM TB on any certificate line   (positive)
  - non-TB death   = (Obito NTB  OR  SIM-linked death)  AND NOT a TB death   (negative control)
  - cases, abandonment for reference.

De-noising: cross-fit (split-sample) Gini removes ranking-selection inflation. All rates
are AGE-STANDARDISED (indirect, SP reference; same construction as script 60).
Head-to-head: TB vs non-TB deaths rarefied to a COMMON event count, so the contrast
cannot be a function of how many events each has.

Prediction: de-noised Gini(non-TB death) < de-noised Gini(TB death); ideally the
non-TB control sits at/below the case concentration.

Adults >=15, 2013-2024, units with >=10 pooled cases.
Output: /tmp/fig_death_negative_control.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, re, matplotlib, matplotlib.pyplot as plt
np.random.seed(20240625)
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SPATIAL="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
BD="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/Abandonment Outcomes/Abandonment Paper/Banco de dados"
CAPITAL,FCU_MIN="3550308",5000
ADULT_COLS=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
def norm_setor(s):
    if pd.isna(s): return None
    s=str(s).strip(); return s[:-1] if s.endswith("P") else s
def norm_key(s): return s.astype(str).str.strip().str.replace(r'\.0$','',regex=True).str.lstrip("0")

print("Building units...")
sec22=gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]=sec22["CD_MUN"].astype(str); sec22["CD_SETOR"]=sec22["CD_SETOR"].astype(str)
pop_df=pd.read_csv(f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
                   sep=";",encoding="latin-1",decimal=",",usecols=["CD_SETOR","v0001"],dtype={"CD_SETOR":str},low_memory=False)
pop_df["pop_total"]=pd.to_numeric(pop_df["v0001"],errors="coerce").fillna(0)
with zipfile.ZipFile(f"{SPATIAL}/IBGE_2022_extended/demografia.zip") as z:
    with z.open("Agregados_por_setores_demografia_BR.csv") as fh:
        demo=pd.read_csv(fh,sep=";",encoding="latin-1",decimal=",",usecols=["CD_setor"]+ADULT_COLS,dtype={"CD_setor":str},low_memory=False)
for _b in ADULT_COLS: demo[_b]=pd.to_numeric(demo[_b],errors="coerce").fillna(0)
demo["pop_adult"]=demo[ADULT_COLS].sum(axis=1)
demo=demo[["CD_setor","pop_adult"]+ADULT_COLS].rename(columns={"CD_setor":"CD_SETOR"})
sec=sec22.merge(pop_df[["CD_SETOR","pop_total"]],on="CD_SETOR",how="left").merge(demo,on="CD_SETOR",how="left")
sec["pop_total"]=sec["pop_total"].fillna(0); sec["pop_adult"]=sec["pop_adult"].fillna(0)
sec_res=sec[sec["CD_TIPO"].astype(str).isin(["0","1"]) & (sec["pop_total"]>=100)].copy()
def bkey(r):
    if str(r["CD_MUN"])==CAPITAL: return f"dist_{r['CD_DIST']}"
    if pd.notna(r.get("NM_BAIRRO")): return f"bairro_{r['CD_MUN']}_{r['NM_BAIRRO']}"
    if pd.notna(r.get("NM_DIST")): return f"dist_{r['CD_DIST']}"
    return f"mun_{r['CD_MUN']}"
sec_res["bairro_id"]=sec_res.apply(bkey,axis=1)
fcu_pop=sec_res[sec_res["NM_FCU"].notna()].groupby("NM_FCU")["pop_adult"].sum()
qf=set(fcu_pop[fcu_pop>=FCU_MIN].index)
sec_res["unit_id"]=sec_res.apply(lambda r: f"fcu__{r['NM_FCU']}" if (pd.notna(r['NM_FCU']) and r['NM_FCU'] in qf) else r["bairro_id"],axis=1)
unit_pop=sec_res.groupby("unit_id")["pop_adult"].sum()

print("Loading SIM (TB-any-line + all linked deaths)...")
sim=pd.read_excel(f"{BD}/LINKAGE SIM (1).xlsx",sheet_name="Limpo",
    usecols=["SINAN","CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"],dtype=str).dropna(subset=["SINAN"])
TBRE=re.compile(r'A1[5-9]')
def cc(*v): return " ".join([str(x) for x in v if x and str(x)!='nan']).upper().replace(".","")
sim["alllines"]=[cc(*r) for r in sim[["CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"]].values]
sim["k"]=norm_key(sim["SINAN"])
sim_all=set(sim["k"])                                            # any SIM-linked death
sim_tb=set(sim.loc[sim["alllines"].str.contains(TBRE),"k"])      # TB on any line

print("Loading adult cases + outcomes...")
def load_co(p,raw=False):
    d=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    if not raw:
        d["tier"]=d["cnefe_match"].astype(str).str.extract(r"^(T\d)"); d=d[d["tier"].isin(["T1","T2","T3"])]
    d["CD_SETOR"]=d["setor_cnefe"].apply(norm_setor)
    return d[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
cohort=pd.concat([load_co("/tmp/cohort_with_cnefe.csv",raw=True),
                  load_co("/tmp/cohort_baixada_with_cnefe_v2.csv"),
                  load_co("/tmp/cohort_sp_outros_with_cnefe.csv")],ignore_index=True)
meta=pd.read_csv(f"{SPATIAL}/cohort_with_spatial.csv",usecols=["sinan_clean","notification_date","age_tb","case_outcome","tx_seq"],low_memory=False,dtype={"sinan_clean":str})
meta["year"]=pd.to_datetime(meta["notification_date"],errors="coerce").dt.year
meta=meta.sort_values("tx_seq").drop_duplicates("sinan_clean",keep="last").set_index("sinan_clean")
cohort["year"]=cohort["sinan_clean"].map(meta["year"]); cohort["age_tb"]=cohort["sinan_clean"].map(meta["age_tb"]); cohort["outcome"]=cohort["sinan_clean"].map(meta["case_outcome"])
cohort["unit_id"]=cohort["CD_SETOR"].map(sec_res.set_index("CD_SETOR")["unit_id"].to_dict())
cohort=cohort[(cohort["age_tb"]>=15)&cohort["year"].between(2013,2024)].dropna(subset=["unit_id"])
ck=norm_key(cohort["sinan_clean"])
obito_tb=cohort["outcome"].eq("Obito TB"); obito_ntb=cohort["outcome"].eq("Obito NTB")
sim_death=ck.isin(sim_all); sim_tbd=ck.isin(sim_tb)
cohort["d_tb"]=obito_tb|sim_tbd                                  # TB death (positive)
cohort["d_nontb"]=(obito_ntb|sim_death)&~cohort["d_tb"]          # non-TB death (negative control)
cohort["aband"]=cohort["outcome"].isin(["Abandono","Abandono Primario"])
pooled=cohort.groupby("unit_id").size(); elig=[u for u in pooled.index if pooled[u]>=10]
pe=unit_pop.reindex(elig); pev=pe.values; eidx={u:i for i,u in enumerate(elig)}
coh=cohort[cohort["unit_id"].isin(elig)].copy(); coh["ui"]=coh["unit_id"].map(eidx)
print(f"  Eligible pool: {len(elig)} units")
print(f"    TB deaths (positive):       {coh['d_tb'].sum():,}")
print(f"    non-TB deaths (neg control):{coh['d_nontb'].sum():,}\n")

# ── age standardisation (indirect; same construction as script 60): each unit's event
#    count × f_u = (crude rate)*(unit pop)/(expected from unit age structure), keeping
#    population as the Lorenz denominator so the cross-fit/rarefaction stay valid. ───────
EDGES=[15,20,25,30,40,50,60,70,200]
coh["band"]=pd.cut(coh["age_tb"],EDGES,right=False,labels=False).astype(int)
Pb=sec_res.groupby("unit_id")[ADULT_COLS].sum().reindex(elig).fillna(0).to_numpy(float)
popband=Pb.sum(axis=0)
def adj_factor(mask):
    cb=np.bincount(coh["band"].values[mask],minlength=8).astype(float)
    rate=np.divide(cb,popband,where=popband>0,out=np.zeros(8))
    E_age=Pb@rate; R=cb.sum()/popband.sum()
    return np.divide(R*pev,E_age,where=E_age>0,out=np.ones_like(E_age))

def gini_from_counts(n,f):
    nn=(n*f)[pev>0]; pp=pev[pev>0]
    if nn.sum()==0: return np.nan
    rate=nn/pp; o=np.argsort(-rate)
    cp=np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]); cv=np.concatenate([[0],np.cumsum(nn[o])/nn.sum()])
    return 2*np.trapz(cv,cp)-1
def counts(ui): return np.bincount(ui,minlength=len(elig)).astype(float)
def cv_gini(ui_array,f,B=150):
    g=[]
    for _ in range(B):
        h=np.random.rand(len(ui_array))<0.5
        a=counts(ui_array[h])*f; b=counts(ui_array[~h])*f
        for rank,val in [(a,b),(b,a)]:
            m=pev>0; ra=rank[m]/pev[m]; vb=val[m]; pp=pev[m]
            if vb.sum()==0: continue
            o=np.argsort(-ra)
            cp=np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]); cvv=np.concatenate([[0],np.cumsum(vb[o])/vb.sum()])
            g.append(2*np.trapz(cvv,cp)-1)
    return np.mean(g),np.std(g)
def rarefy(ui_array,N,f,B=200):
    g=[]
    for _ in range(B):
        s=np.random.choice(ui_array,size=N,replace=False); g.append(gini_from_counts(counts(s),f))
    return np.mean(g),np.std(g)

# de-noised levels (each series age-standardised with its own adjustment factor)
series=[("Cases",coh["ui"].values,"#1a3d5c",adj_factor(np.ones(len(coh),bool))),
        ("Non-TB death\n(neg. control)",coh[coh["d_nontb"]]["ui"].values,"#6c8ebf",adj_factor(coh["d_nontb"].values)),
        ("TB death\n(integrated)",coh[coh["d_tb"]]["ui"].values,"#c0392b",adj_factor(coh["d_tb"].values)),
        ("Abandonment",coh[coh["aband"]]["ui"].values,"#1f6f8b",adj_factor(coh["aband"].values))]
print("=== De-noised (cross-fit) Gini — age-standardised ===")
res=[]
for name,ui,col,f in series:
    naive=gini_from_counts(counts(ui),f); cv=cv_gini(ui,f)
    res.append((name,len(ui),naive,cv[0],cv[1],col))
    print(f"  {name.replace(chr(10),' '):26s} N={len(ui):6d}  naive={naive:.3f}  cross-fit={cv[0]:.3f}")

# head-to-head at common N
tb_ui=coh[coh["d_tb"]]["ui"].values; nt_ui=coh[coh["d_nontb"]]["ui"].values
f_tb=adj_factor(coh["d_tb"].values); f_nt=adj_factor(coh["d_nontb"].values)
Nc=min(len(tb_ui),len(nt_ui))
tb_r=rarefy(tb_ui,Nc,f_tb); nt_r=rarefy(nt_ui,Nc,f_nt)
tb_rcv=[]; nt_rcv=[]
print(f"\n=== Head-to-head rarefied to common N={Nc:,} (naive Gini at equal noise) ===")
print(f"  TB death:     {tb_r[0]:.3f} [{tb_r[0]-1.96*tb_r[1]:.3f},{tb_r[0]+1.96*tb_r[1]:.3f}]")
print(f"  non-TB death: {nt_r[0]:.3f} [{nt_r[0]-1.96*nt_r[1]:.3f},{nt_r[0]+1.96*nt_r[1]:.3f}]")
print(f"  difference (TB - nonTB): {tb_r[0]-nt_r[0]:+.3f}")

# ── figure ──────────────────────────────────────────────────────────────────
fig,(axA,axB)=plt.subplots(1,2,figsize=(15,5.8))
x=np.arange(len(res));
axA.bar(x,[r[3] for r in res],0.6,yerr=[1.96*r[4] for r in res],color=[r[5] for r in res],capsize=4)
for i,r in enumerate(res): axA.text(i,r[3]+0.006,f"{r[3]:.2f}",ha="center",fontsize=10,fontweight="bold")
axA.set_xticks(x); axA.set_xticklabels([r[0] for r in res],fontsize=9.5); axA.set_ylabel("De-noised (cross-fit) Gini"); axA.set_ylim(0,0.48)
axA.axhline(res[0][3],ls="--",color="#1a3d5c",lw=1.3,alpha=0.6)
axA.set_title("A)  Mortality clusters above incidence — TB AND non-TB alike (age-standardised)\n(the negative control does NOT separate from TB deaths)",fontsize=11,fontweight="bold")
axA.grid(alpha=0.3,axis="y")
g2=["TB death","non-TB death"]; xx=np.arange(2); w=0.38
axB.bar(xx-w/2,[tb_r[0],nt_r[0]],w,yerr=[1.96*tb_r[1],1.96*nt_r[1]],color=["#c0392b","#6c8ebf"],capsize=4)
for i,(m,s) in enumerate([tb_r,nt_r]): axB.text(i-w/2,m+0.006,f"{m:.2f}",ha="center",fontsize=10)
axB.set_xticks(xx-w/2); axB.set_xticklabels(g2,fontsize=10); axB.set_ylabel("Gini at common event count (rarefied)")
axB.set_title(f"B)  TB vs non-TB death at equal N={Nc:,}: ~identical\n(the excess concentration is not TB-cause-specific)",fontsize=11,fontweight="bold")
axB.set_ylim(0,0.5); axB.grid(alpha=0.3,axis="y")
fig.suptitle("Negative control (age-standardised): excess mortality concentration is vulnerability-driven, not TB-cause-specific — SP adults 2013–2024",fontsize=12,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_death_negative_control.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_death_negative_control.png")
