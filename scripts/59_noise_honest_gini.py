"""Noise-honest concentration (advisor: 'for anything we calculate, de-attenuate
the noise'). Two corrections, applied together:

  (1) Split-sample (cross-fit) Gini: rank units by one random half of the events,
      read the Lorenz value from the OTHER half. The ranking noise and the value
      noise are independent, so noise cannot create spurious concentration. Removes
      the ranking-selection inflation. (Conservative: imperfect half-data ranking
      slightly attenuates -> lower bound on the true Gini.)
  (2) Rarefaction to a common event count: downsample every window to the same N,
      so all windows carry the SAME noise level -> Gini trend is no longer
      confounded by changing event counts (the 'decline after 2020' concern).

Applied to: (A) abandonment & cases Gini over calendar time (naive vs rarefied-to-
common-N), and (B) pooled concentration levels (naive vs split-sample de-noised).

Adults >=15, 2013-2024, units with >=10 pooled cases.
Output: /tmp/fig_noise_honest_gini.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, matplotlib, matplotlib.pyplot as plt
np.random.seed(20240625)
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SPATIAL="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL,FCU_MIN="3550308",5000
ADULT_COLS=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
def norm_setor(s):
    if pd.isna(s): return None
    s=str(s).strip(); return s[:-1] if s.endswith("P") else s

print("Building units...")
sec22=gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]=sec22["CD_MUN"].astype(str); sec22["CD_SETOR"]=sec22["CD_SETOR"].astype(str)
pop_df=pd.read_csv(f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
                   sep=";",encoding="latin-1",decimal=",",usecols=["CD_SETOR","v0001"],dtype={"CD_SETOR":str},low_memory=False)
pop_df["pop_total"]=pd.to_numeric(pop_df["v0001"],errors="coerce").fillna(0)
with zipfile.ZipFile(f"{SPATIAL}/IBGE_2022_extended/demografia.zip") as z:
    with z.open("Agregados_por_setores_demografia_BR.csv") as fh:
        demo=pd.read_csv(fh,sep=";",encoding="latin-1",decimal=",",usecols=["CD_setor"]+ADULT_COLS,dtype={"CD_setor":str},low_memory=False)
demo["pop_adult"]=demo[ADULT_COLS].apply(pd.to_numeric,errors="coerce").fillna(0).sum(axis=1)
demo=demo[["CD_setor","pop_adult"]].rename(columns={"CD_setor":"CD_SETOR"})
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
cohort["death"]=cohort["outcome"].isin(["Obito TB"]); cohort["aband"]=cohort["outcome"].isin(["Abandono","Abandono Primario"])
pooled=cohort.groupby("unit_id").size(); elig=[u for u in pooled.index if pooled[u]>=10]
pe=unit_pop.reindex(elig); pev=pe.values; eidx={u:i for i,u in enumerate(elig)}
coh=cohort[cohort["unit_id"].isin(elig)].copy(); coh["ui"]=coh["unit_id"].map(eidx)
print(f"  Eligible pool: {len(elig)} units\n")

def gini_from_counts(n):
    m=pev>0; nn=n[m]; pp=pev[m]
    if nn.sum()==0: return np.nan
    rate=nn/pp; o=np.argsort(-rate)
    cp=np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]); cv=np.concatenate([[0],np.cumsum(nn[o])/nn.sum()])
    return 2*np.trapz(cv,cp)-1
def counts(ui): return np.bincount(ui,minlength=len(elig)).astype(float)

def cv_gini(ui_array, B=120):
    g=[]
    for _ in range(B):
        h=np.random.rand(len(ui_array))<0.5
        a=counts(ui_array[h]); b=counts(ui_array[~h])
        for rank,val in [(a,b),(b,a)]:
            m=pev>0; ra=rank[m]/pev[m]; vb=val[m]; pp=pev[m]
            if vb.sum()==0: continue
            o=np.argsort(-ra)
            cp=np.concatenate([[0],np.cumsum(pp[o])/pp.sum()]); cvv=np.concatenate([[0],np.cumsum(vb[o])/vb.sum()])
            g.append(2*np.trapz(cvv,cp)-1)
    return np.mean(g),np.std(g)

def rarefy_gini(ui_array, N, B=120):
    g=[]
    for _ in range(B):
        s=np.random.choice(ui_array,size=N,replace=False)
        g.append(gini_from_counts(counts(s)))
    return np.mean(g),np.std(g)

# ── (A) temporal Gini, naive vs rarefied-to-common-N ────────────────────────
WB=3; wins=[list(range(y,y+WB)) for y in range(2013,2025-WB+1)]; gx=[np.mean(w) for w in wins]
def event_ui(flag,w):
    sub=coh[coh["year"].isin(w)]; sub=sub[sub[flag]] if flag else sub
    return sub["ui"].values
print("=== (A) temporal Gini: naive vs rarefied-to-common-N ===")
res={}
for flag,name in [(None,"cases"),("aband","abandonment")]:
    Ns=[len(event_ui(flag,w)) for w in wins]; Nmin=min(Ns)
    naive=[gini_from_counts(counts(event_ui(flag,w))) for w in wins]
    rare=[rarefy_gini(event_ui(flag,w),Nmin)[0] for w in wins]
    rsd=[rarefy_gini(event_ui(flag,w),Nmin)[1] for w in wins]
    res[name]=(naive,rare,rsd,Nmin)
    print(f"  {name}: rarefied to N={Nmin:,}/window")
    print("   yr   naive  rarefied")
    for i,c in enumerate(gx): print(f"   {c:.1f}  {naive[i]:.3f}  {rare[i]:.3f}")

# ── (B) pooled levels: naive vs split-sample de-noised ──────────────────────
print("\n=== (B) pooled Gini: naive vs split-sample (cross-fit) de-noised ===")
lvl={}
for flag,name in [(None,"cases"),("death","TB deaths"),("aband","abandonment")]:
    ui=(coh[coh[flag]] if flag else coh)["ui"].values
    naive=gini_from_counts(counts(ui)); cv,cvsd=cv_gini(ui)
    lvl[name]=(naive,cv,cvsd)
    print(f"  {name:12s} naive={naive:.3f}  de-noised(cross-fit)={cv:.3f} ± {cvsd:.3f}")

# ── figure ──────────────────────────────────────────────────────────────────
fig,(axA,axB)=plt.subplots(1,2,figsize=(15,5.6))
cols={"cases":"#1a3d5c","abandonment":"#1f6f8b"}
for name in ("abandonment","cases"):
    naive,rare,rsd,Nmin=res[name]
    axA.plot(gx,naive,"o--",color=cols[name],lw=1.6,ms=5,alpha=0.5,label=f"{name} — naive")
    axA.plot(gx,rare,"o-",color=cols[name],lw=2.6,ms=7,label=f"{name} — rarefied to N={Nmin:,}")
    axA.fill_between(gx,np.array(rare)-1.96*np.array(rsd),np.array(rare)+1.96*np.array(rsd),color=cols[name],alpha=0.12)
axA.set_xlabel("Window centre (year)"); axA.set_ylabel("Gini coefficient")
axA.set_title("A)  Temporal Gini at CONSTANT noise (rarefied to common N)\ndoes the post-2020 'decline' survive?",fontsize=11,fontweight="bold")
axA.grid(alpha=0.3); axA.legend(fontsize=8.5,loc="upper right")
names=list(lvl); x=np.arange(len(names)); w=0.36
axB.bar(x-w/2,[lvl[n][0] for n in names],w,color="#bbb",label="Naive (noise-inflated)")
axB.bar(x+w/2,[lvl[n][1] for n in names],w,yerr=[1.96*lvl[n][2] for n in names],color="#c0392b",capsize=4,label="De-noised (cross-fit)")
for i,n in enumerate(names):
    axB.text(i-w/2,lvl[n][0]+0.008,f"{lvl[n][0]:.2f}",ha="center",fontsize=8.5)
    axB.text(i+w/2,lvl[n][1]+0.008,f"{lvl[n][1]:.2f}",ha="center",fontsize=8.5)
axB.set_xticks(x); axB.set_xticklabels(names); axB.set_ylabel("Gini coefficient"); axB.set_ylim(0,0.55)
axB.set_title("B)  Pooled concentration: naive vs noise-corrected\n(split-sample removes ranking-selection inflation)",fontsize=11,fontweight="bold")
axB.legend(fontsize=9); axB.grid(alpha=0.3,axis="y")
fig.suptitle("Noise-honest concentration — São Paulo adult TB, 2013–2024",fontsize=12.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_noise_honest_gini.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_noise_honest_gini.png")
