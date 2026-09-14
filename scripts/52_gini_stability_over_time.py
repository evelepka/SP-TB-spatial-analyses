"""Do incidence concentration (Gini) and hotspot stability change over time?
ADULTS (>=15 yr), new+relapse, 2013-2024. Adult population as denominator.

For each year, over a fixed eligible pool (units with >=10 pooled adult cases):
  - Gini of TB case concentration + share captured by top 20% of (adult) population
  - top-20%-population selection (for year-to-year stability)
Stability = Jaccard overlap between consecutive years' selections.

Output: /tmp/fig_gini_stability_over_time.png
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile, matplotlib, matplotlib.pyplot as plt
matplotlib.rcParams.update({"font.family": "sans-serif", "font.size": 11})
SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
CAPITAL, FCU_MIN, MIN_CASES, POP_WIN = "3550308", 5000, 10, 0.20
ADULT_COLS = ["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]  # ages 15+
def norm_setor(s):
    if pd.isna(s): return None
    s=str(s).strip(); return s[:-1] if s.endswith("P") else s

print("Building units (adult population denominator)...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]=sec22["CD_MUN"].astype(str); sec22["CD_SETOR"]=sec22["CD_SETOR"].astype(str)
# total population (for >=100 sector eligibility, same as main analysis)
pop_df = pd.read_csv(f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
                     sep=";", encoding="latin-1", decimal=",", usecols=["CD_SETOR","v0001"],
                     dtype={"CD_SETOR":str}, low_memory=False)
pop_df["pop_total"]=pd.to_numeric(pop_df["v0001"],errors="coerce").fillna(0)
# adult population (>=15) from demografia.zip
with zipfile.ZipFile(f"{SPATIAL}/IBGE_2022_extended/demografia.zip") as z:
    with z.open("Agregados_por_setores_demografia_BR.csv") as f:
        demo = pd.read_csv(f, sep=";", encoding="latin-1", decimal=",",
                           usecols=["CD_setor"]+ADULT_COLS, dtype={"CD_setor":str}, low_memory=False)
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
qf=set(fcu_pop[fcu_pop>=FCU_MIN].index); TOTAL_POP=sec_res["pop_adult"].sum()
sec_res["unit_id"]=sec_res.apply(lambda r: f"fcu__{r['NM_FCU']}" if (pd.notna(r['NM_FCU']) and r['NM_FCU'] in qf) else r["bairro_id"], axis=1)
upop=sec_res.groupby("unit_id")["pop_adult"].sum()

print("Loading cases (adults >=15, new+relapse)...")
def load_co(path, raw=False):
    df=pd.read_csv(path,low_memory=False,dtype={"sinan_clean":str})
    if not raw:
        df["tier"]=df["cnefe_match"].astype(str).str.extract(r"^(T\d)"); df=df[df["tier"].isin(["T1","T2","T3"])]
    df["CD_SETOR"]=df["setor_cnefe"].apply(norm_setor)
    return df[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
cohort=pd.concat([load_co("/tmp/cohort_with_cnefe.csv",raw=True),
                  load_co("/tmp/cohort_baixada_with_cnefe_v2.csv"),
                  load_co("/tmp/cohort_sp_outros_with_cnefe.csv")],ignore_index=True)
meta=pd.read_csv(f"{SPATIAL}/cohort_with_spatial.csv",usecols=["sinan_clean","notification_date","age_tb"],
                 low_memory=False,dtype={"sinan_clean":str})
meta["year"]=pd.to_datetime(meta["notification_date"],errors="coerce").dt.year
md=meta.dropna(subset=["sinan_clean"]).drop_duplicates("sinan_clean").set_index("sinan_clean")
cohort["year"]=cohort["sinan_clean"].map(md["year"])
cohort["age_tb"]=cohort["sinan_clean"].map(md["age_tb"])
n0=len(cohort)
cohort["unit_id"]=cohort["CD_SETOR"].map(sec_res.set_index("CD_SETOR")["unit_id"].to_dict())
cohort=cohort[(cohort["age_tb"]>=15) & cohort["year"].between(2013,2024)].dropna(subset=["unit_id"])
print(f"  Adultos >=15 geocodificados 2013-2024: {len(cohort):,} (de {n0:,} totais)")

pooled=cohort.groupby("unit_id").size()
elig_ids=[u for u in pooled.index if pooled[u]>=MIN_CASES]
base=pd.DataFrame({"unit_id":elig_ids}); base["pop"]=base["unit_id"].map(upop)
print(f"  Pool elegível (>=10 casos adultos agrupados): {len(base)} unidades | {base['pop'].sum()/1e6:.1f}M adultos\n")

def lorenz_gini(df):
    d=df[df["pop"]>0].copy(); d["rate"]=d["n"]/d["pop"]; d=d.sort_values("rate",ascending=False)
    cp=np.concatenate([[0],(d["pop"].cumsum()/d["pop"].sum()).values])
    cv=np.concatenate([[0],(d["n"].cumsum()/d["n"].sum()).values])
    return 2*np.trapz(cv,cp)-1, np.interp(0.20,cp,cv)*100
def select_year(df):
    d=df[df["pop"]>0].copy(); d["rate"]=d["n"]/d["pop"]; d=d.sort_values("rate",ascending=False)
    d["cum"]=d["pop"].cumsum(); m=d["cum"]<=TOTAL_POP*POP_WIN
    if m.sum()<len(d): m.iloc[m.sum()]=True
    return set(d[m]["unit_id"])

YEARS=list(range(2013,2025)); ginis={}; top20s={}; sels={}
print(f"{'Year':<6}{'cases':>8}{'Gini':>8}{'Top20%':>9}")
for y in YEARS:
    cnt=cohort[cohort["year"]==y].groupby("unit_id").size()
    d=base.copy(); d["n"]=d["unit_id"].map(cnt).fillna(0)
    g,t=lorenz_gini(d); ginis[y]=g; top20s[y]=t; sels[y]=select_year(d)
    print(f"{y:<6}{int(d['n'].sum()):>8,}{g:>8.3f}{t:>8.1f}%")

print("\nStability (Jaccard, consecutive years):")
pairs=[(y,y+1) for y in range(2013,2024)]; jacs={}
for a,b in pairs:
    j=len(sels[a]&sels[b])/len(sels[a]|sels[b]); jacs[(a,b)]=j
    print(f"  {a}-{b}: {j:.3f}")
print(f"  mean = {np.mean(list(jacs.values())):.3f}")

fig,(ax1,ax2)=plt.subplots(1,2,figsize=(15,5.4))
ax1.plot(YEARS,[ginis[y] for y in YEARS],"o-",color="#1a3d5c",lw=2.4,ms=8)
for y in YEARS: ax1.annotate(f"{ginis[y]:.3f}",(y,ginis[y]),textcoords="offset points",xytext=(0,9),ha="center",fontsize=8,color="#1a3d5c")
ax1.set_title("A)  Concentration over time (Gini of adult TB cases)",fontsize=12,fontweight="bold")
ax1.set_xlabel("Year"); ax1.set_ylabel("Gini coefficient"); ax1.set_xticks(YEARS); ax1.tick_params(axis="x",rotation=45)
ax1.set_ylim(min(ginis.values())-0.04,max(ginis.values())+0.05); ax1.grid(alpha=0.3)
ax1.axvspan(2019.6,2021.4,color="#f0c0c0",alpha=0.40); ax1.text(2020.5,ax1.get_ylim()[0]+0.004,"COVID-19",ha="center",fontsize=9,color="#a33",style="italic",fontweight="bold")
ax1.annotate("2020: highest concentration\ndespite the fewest notifications",(2020,ginis[2020]),textcoords="offset points",xytext=(16,-30),fontsize=8.5,color="#a33",ha="left",arrowprops=dict(arrowstyle="->",color="#a33",lw=1.3))
xp=[f"{a%100}-{b%100}" for a,b in pairs]
ax2.plot(range(len(pairs)),[jacs[p] for p in pairs],"s-",color="#028090",lw=2.4,ms=8)
for i,p in enumerate(pairs): ax2.annotate(f"{jacs[p]:.2f}",(i,jacs[p]),textcoords="offset points",xytext=(0,9),ha="center",fontsize=8,color="#028090")
ax2.axhline(np.mean(list(jacs.values())),ls="--",color="#888",lw=1.2,label=f"mean {np.mean(list(jacs.values())):.3f}")
ax2.set_title("B)  Stability over time (Jaccard, consecutive years)",fontsize=12,fontweight="bold")
ax2.set_xlabel("Consecutive year pair"); ax2.set_ylabel("Jaccard overlap of top-20% selection")
ax2.set_xticks(range(len(pairs))); ax2.set_xticklabels(xp,rotation=45); ax2.set_ylim(0,1); ax2.grid(alpha=0.3); ax2.legend(fontsize=9)
fig.suptitle("Adult TB hotspots over time — São Paulo state, 2013-2024 (≥15 yr, new+relapse, units with ≥10 cases)",fontsize=12.5,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_gini_stability_over_time.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_gini_stability_over_time.png")
