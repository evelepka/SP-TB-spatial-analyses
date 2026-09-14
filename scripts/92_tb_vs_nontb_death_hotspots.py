"""Appendix E companion (P3-style): are the TB-death and non-TB-death geographies the SAME?
The negative control (script 61) shows TB and non-TB deaths CONCENTRATE equally; here we ask
the spatial-overlap question directly — do their age-standardised hotspots fall in the same
places, and do those places share the same structural profile? High overlap + identical
profile = the mortality geography is 'where vulnerable patients die of anything', not a
TB-cause-specific signal. Both rates are age-standardised (indirect, SP reference; same
adj_factor as script 61). Output: /tmp/fig_tb_vs_nontb_death.png + numbers.
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
fav_share=sec_res.assign(f=sec_res["NM_FCU"].notna()*sec_res["pop_adult"]).groupby("unit_id")["f"].sum()/unit_pop*100

print("SIM + cohort...")
sim=pd.read_excel(f"{BD}/LINKAGE SIM (1).xlsx",sheet_name="Limpo",usecols=["SINAN","CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"],dtype=str).dropna(subset=["SINAN"])
def cc(*v): return " ".join([str(x) for x in v if x and str(x)!='nan']).upper().replace(".","")
sim["alllines"]=[cc(*r) for r in sim[["CAUSABAS","LINHAA","LINHAB","LINHAC","LINHAD","LINHAII"]].values]
sim["k"]=norm_key(sim["SINAN"]); sim_all=set(sim["k"]); sim_tb=set(sim.loc[sim["alllines"].str.contains(re.compile(r'A1[5-9]')),"k"])
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
cohort["d_nontb"]=(cohort["outcome"].eq("Obito NTB")|ck.isin(sim_all))&~cohort["d_tb"]
pooled=cohort.groupby("unit_id").size(); elig=[u for u in pooled.index if pooled[u]>=10]
pe=unit_pop.reindex(elig); pev=pe.values; eidx={u:i for i,u in enumerate(elig)}
coh=cohort[cohort["unit_id"].isin(elig)].copy(); coh["ui"]=coh["unit_id"].map(eidx)
print(f"  eligible units {len(elig)} | TB deaths {coh['d_tb'].sum():,} | non-TB deaths {coh['d_nontb'].sum():,}")

EDGES=[15,20,25,30,40,50,60,70,200]
coh["band"]=pd.cut(coh["age_tb"],EDGES,right=False,labels=False).astype(int)
Pb=sec_res.groupby("unit_id")[ADULT_COLS].sum().reindex(elig).fillna(0).to_numpy(float); popband=Pb.sum(axis=0)
def adj_factor(mask):
    cb=np.bincount(coh["band"].values[mask],minlength=8).astype(float)
    rate=np.divide(cb,popband,where=popband>0,out=np.zeros(8))
    E_age=Pb@rate; R=cb.sum()/popband.sum()
    return np.divide(R*pev,E_age,where=E_age>0,out=np.ones_like(E_age))
def counts(ui): return np.bincount(ui,minlength=len(elig)).astype(float)
def hotspots(col):                      # top-20%-pop units by AGE-STANDARDISED rate
    m=coh[col].values; cnt=counts(coh[coh[col]]["ui"].values); f=adj_factor(m)
    rate=np.divide(cnt*f,pev,where=pev>0,out=np.zeros_like(pev))
    o=np.argsort(-rate); cum=np.cumsum(pev[o]); sel=o[cum<=pev.sum()*0.20]
    return set(sel.tolist())
HS_tb=hotspots("d_tb"); HS_nt=hotspots("d_nontb")
both=HS_tb&HS_nt; jac=len(both)/len(HS_tb|HS_nt)
print(f"\nTB-death HS={len(HS_tb)} | non-TB-death HS={len(HS_nt)} | both={len(both)} | Jaccard={jac:.3f}")

# structural profile of each hotspot set
vf=pd.read_csv("/tmp/vuln_final.csv",dtype={"CD_SETOR":str})
vu=vf.groupby("unit_id").apply(lambda d:np.average(d["vuln_final"],weights=d["pop15"]))
elig_arr=np.array(elig)
def prof(ids):
    us=elig_arr[list(ids)]
    v=vu.reindex(us).dropna(); fv=fav_share.reindex(us).dropna()
    return v.mean(), fv.mean()
vtb,ftb=prof(HS_tb); vnt,fnt=prof(HS_nt)
vall=vu.reindex(elig_arr).mean(); fall=fav_share.reindex(elig_arr).mean()
print(f"  TB-death HS:     vuln {vtb:+.2f}  favela {ftb:.1f}%")
print(f"  non-TB-death HS: vuln {vnt:+.2f}  favela {fnt:.1f}%")
print(f"  all eligible:    vuln {vall:+.2f}  favela {fall:.1f}%")

# ── figure ──
fig,(axA,axB)=plt.subplots(1,2,figsize=(13.5,5.4),gridspec_kw={"width_ratios":[1,1.1]})
# A: overlap
axA.bar(["TB-death\nonly","both","non-TB-death\nonly"],[len(HS_tb-HS_nt),len(both),len(HS_nt-HS_tb)],
        color=["#c0392b","#7a0177","#6c8ebf"],width=0.62)
axA.set_ylabel("number of hotspot units")
axA.set_title(f"A)  TB-death vs non-TB-death hotspots overlap\nJaccard = {jac:.2f} (vs 0.13–0.22 between the main lenses)",fontsize=11.5,fontweight="bold")
axA.grid(axis="y",alpha=0.3)
# B: structural profile (two y-axes: vuln z, favela %)
g=["TB-death HS","non-TB-death HS"]; xb=np.arange(2); w=0.36
bvt=axB.bar(xb-w/2,[vtb,vnt],w,color="#3a6ea5",label="vulnerability (z)")
axB.axhline(vall,ls="--",color="#3a6ea5",lw=1.1,alpha=.7)
axB.bar_label(bvt,labels=[f"{vtb:+.2f}",f"{vnt:+.2f}"],padding=2,fontsize=9)
axB.set_ylabel("place vulnerability (z)",color="#3a6ea5"); axB.tick_params(axis="y",labelcolor="#3a6ea5")
axB.set_ylim(0,0.42)
ax2=axB.twinx(); bfv=ax2.bar(xb+w/2,[ftb,fnt],w,color="#cc7a00",label="favela %")
ax2.axhline(fall,ls="--",color="#cc7a00",lw=1.1,alpha=.7)
ax2.bar_label(bfv,labels=[f"{ftb:.0f}%",f"{fnt:.0f}%"],padding=2,fontsize=9)
ax2.set_ylabel("favela share (%)",color="#cc7a00"); ax2.tick_params(axis="y",labelcolor="#cc7a00"); ax2.set_ylim(0,30)
axB.set_xticks(xb); axB.set_xticklabels(g,fontsize=10)
axB.set_title("B)  ...and the two sets look structurally identical\n(dashed = state-eligible mean)",fontsize=11.5,fontweight="bold")
fig.suptitle("Appendix E — TB-death vs non-TB-death geographies are the same (age-standardised) · SP adults 2013–2024",fontsize=12,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_tb_vs_nontb_death.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_tb_vs_nontb_death.png")
