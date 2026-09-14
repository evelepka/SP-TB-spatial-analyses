"""P3 deepening: the three outcome lenses (incidence / abandonment / TB mortality) identify
LARGELY DIFFERENT places (Jaccard 0.13-0.22). This script asks WHAT differentiates those
places -- profiling each lens-ONLY hotspot group (and a non-hotspot reference) by the
structural characteristics: place vulnerability (5-dom composite), favela share, household
income, share in the State capital, and the age of the TB patients. Age-standardised rates
were used to SELECT the hotspots (script 50), so differences here are structural, not age.
Reads /tmp/outcome_units.csv (script 50, with hs_* flags), /tmp/vuln_final.csv,
/tmp/vuln_sectors.csv, the cohort. Output: /tmp/fig_lens_characterisation.png + table.
"""
import pandas as pd, numpy as np, re, matplotlib, matplotlib.pyplot as plt
matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"

u=pd.read_csv("/tmp/outcome_units.csv")
# ---- sector-level structural attributes -> population-weighted to the unit ----
vs=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)[["CD_SETOR","unit_id","pop15","NM_FCU","CD_MUN","V06004"]]
vf=pd.read_csv("/tmp/vuln_final.csv",dtype={"CD_SETOR":str})[["CD_SETOR","vuln_final"]]
s=vs.merge(vf,on="CD_SETOR",how="left")
s=s[s["pop15"]>0]
s["fav"]=s["NM_FCU"].notna().astype(int)
s["cap"]=(s["CD_MUN"].astype(str)=="3550308").astype(int)
def wmean(df,col,w="pop15"):
    g=df.dropna(subset=[col]);
    return g.groupby("unit_id").apply(lambda d:np.average(d[col],weights=d[w]))
attr=pd.DataFrame({
    "vuln":wmean(s,"vuln_final"),
    "fav":wmean(s,"fav")*100,
    "income":wmean(s,"V06004"),
    "cap":wmean(s,"cap")*100,
}).reset_index()
u=u.merge(attr,on="unit_id",how="left")

# ---- mean TB-patient age per unit (from cohort) ----
def ns(x):
    if pd.isna(x): return None
    x=str(x).strip(); return x[:-1] if x.endswith("P") else x
def lc(p,raw=False):
    dd=pd.read_csv(p,low_memory=False,dtype={"sinan_clean":str})
    if not raw:
        dd["t"]=dd["cnefe_match"].astype(str).str.extract(r"^(T\d)"); dd=dd[dd["t"].isin(["T1","T2","T3"])]
    dd["CD_SETOR"]=dd["setor_cnefe"].apply(ns); return dd[["sinan_clean","CD_SETOR"]].dropna(subset=["CD_SETOR"])
co=pd.concat([lc("/tmp/cohort_with_cnefe.csv",raw=True),lc("/tmp/cohort_baixada_with_cnefe_v2.csv"),lc("/tmp/cohort_sp_outros_with_cnefe.csv")])
m=pd.read_csv(f"{SP}/cohort_with_spatial.csv",usecols=["sinan_clean","age_tb","notification_date","tx_seq"],dtype={"sinan_clean":str},low_memory=False)
m["year"]=pd.to_datetime(m["notification_date"],errors="coerce").dt.year
m=m.sort_values("tx_seq").drop_duplicates("sinan_clean",keep="last").set_index("sinan_clean")
co["age"]=co["sinan_clean"].map(m["age_tb"]); co["year"]=co["sinan_clean"].map(m["year"])
co=co[(co["age"]>=15)&co["year"].between(2013,2024)]
co["unit_id"]=co["CD_SETOR"].map(s.set_index("CD_SETOR")["unit_id"])

# ---- lens-only groups ----
inc=u["hs_inc"]; ab=u["hs_aband"]; de=u["hs_death"]
groups={
 "Incidence-only":  u[inc&~ab&~de],
 "Abandonment-only":u[ab&~inc&~de],
 "Mortality-only":  u[de&~inc&~ab],
 "Reference (non-HS)":u[~inc&~ab&~de],
}
def pw(df,col):
    d=df.dropna(subset=[col]); return np.average(d[col],weights=d["pop"]) if len(d) else np.nan
rows=[]
print(f"\n{'group':20s}{'units':>6}{'pop M':>7}{'vuln z':>8}{'favela%':>9}{'income':>8}{'capital%':>9}{'age':>6}{'inc/100k':>9}{'aband%':>8}{'TBmort%':>9}")
for name,df in groups.items():
    ids=set(df["unit_id"]); age=co[co["unit_id"].isin(ids)]["age"].mean()
    r=dict(group=name,units=len(df),popM=df["pop"].sum()/1e6,vuln=pw(df,"vuln"),fav=pw(df,"fav"),
           income=pw(df,"income"),cap=pw(df,"cap"),age=age,
           inc=np.average(df["rate"],weights=df["pop"]),
           aband=pw(df,"aband_pct"),tbmort=pw(df,"tbmort_pct"))
    rows.append(r)
    print(f"{name:20s}{r['units']:>6d}{r['popM']:>7.2f}{r['vuln']:>8.2f}{r['fav']:>9.1f}{r['income']:>8.0f}{r['cap']:>9.0f}{r['age']:>6.0f}{r['inc']:>9.0f}{r['aband']:>8.1f}{r['tbmort']:>9.1f}")
R=pd.DataFrame(rows)

# ---- figure: small-multiples of the differentiators across the 3 lens-only groups ----
G=R[R["group"]!="Reference (non-HS)"].reset_index(drop=True)
ref=R[R["group"]=="Reference (non-HS)"].iloc[0]
cols=["#1a3d5c","#1f6f8b","#7a0177"]
panels=[("vuln","Place vulnerability (z)","higher = more deprived"),
        ("fav","Favela share (%)",""),
        ("income","Household income (R$)",""),
        ("cap","In State capital (%)",""),
        ("age","Mean patient age (yr)",""),
        ("inc","TB incidence /100k",""),]
fig,axs=plt.subplots(2,3,figsize=(15,8))
for ax,(col,title,sub) in zip(axs.ravel(),panels):
    ax.bar(G["group"],G[col],color=cols,width=0.66)
    ax.axhline(ref[col],ls="--",color="#888",lw=1.3)
    ax.text(2.4,ref[col],"state ref.",fontsize=8,color="#666",va="bottom",ha="right")
    ax.set_title(title+("\n"+sub if sub else ""),fontsize=11,fontweight="bold")
    ax.set_xticklabels(G["group"],rotation=18,ha="right",fontsize=9.5); ax.grid(axis="y",alpha=0.3)
fig.suptitle("P3 — what differentiates the three outcome geographies (lens-only hotspots) · SP adults 2013–2024",
             fontsize=13,fontweight="bold")
plt.tight_layout(); plt.savefig("/tmp/fig_lens_characterisation.png",dpi=150,bbox_inches="tight"); plt.close()
print("\nSaved /tmp/fig_lens_characterisation.png")
