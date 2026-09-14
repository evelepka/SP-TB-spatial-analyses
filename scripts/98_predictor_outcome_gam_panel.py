"""Advisor request: relationship between regional-unit characteristics and TB indicators.
A grid of scatter + fitted-GAM panels — one ROW per predictor (income, illiteracy, sanitation,
residents/household, population density) and one COLUMN per outcome (TB incidence, TB-mortality
rate, treatment abandonment %). Points = operational units (>=10 cases), sized by population;
GAM = population-weighted P-spline smooth with 95% CI. Outcomes age-standardised.
Output: /tmp/fig_predictor_outcome_gam.png
"""
import pandas as pd, numpy as np, matplotlib, matplotlib.pyplot as plt
from pygam import LinearGAM, s
np.random.seed(20240625); matplotlib.rcParams.update({"font.family":"sans-serif","font.size":10})

# ---- per-unit predictors (from sectors) ----
vs=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)
vs=vs[(vs["pop15"]>0)&(vs["AREA_KM2"]>0)].copy()
vs["fav"]=vs["NM_FCU"].notna().astype(int)
g=vs.groupby("unit_id")
U=pd.DataFrame({
 "pop":g["pop15"].sum(),
 "income":g.apply(lambda d:np.average(d["V06004"],weights=d["pop15"]) if d["V06004"].notna().any() else np.nan),
 "illit":(1-g["lit15"].sum()/g["pop15"].sum())*100,
 "sanit":g.apply(lambda d:np.average(d["d_sanit"],weights=d["pop15"])),
 "resid":g.apply(lambda d:np.average(d["v0005"],weights=d["pop15"])),
 "dens":g["pop15"].sum()/g["AREA_KM2"].sum(),
}).reset_index()

# ---- per-unit outcomes (age-standardised) ----
asr=pd.read_csv("/tmp/unit_age_standardised.csv")[["unit_id","inc_adj","drate_adj","ltfu_adj"]]
oc=pd.read_csv("/tmp/outcome_units.csv")[["unit_id","n_cases"]]
df=U.merge(asr,on="unit_id",how="inner").merge(oc,on="unit_id",how="left")
df=df[df["n_cases"]>=10].dropna(subset=["income","illit","sanit","resid","dens","inc_adj","drate_adj","ltfu_adj"])
print(f"units: {len(df):,}")

PRED=[("income","Household income (R$, log)",True),
      ("illit","Adult illiteracy (%)",False),
      ("resid","Residents per household",False),
      ("dens","Population density (/km², log)",True)]
OUT=[("inc_adj","TB incidence /100k/yr (log)","log"),
     ("drate_adj","TB-mortality rate /100k/yr",None),
     ("ltfu_adj","Treatment abandonment %",None)]

fig,axes=plt.subplots(len(PRED),len(OUT),figsize=(12,13))
for i,(pk,plab,logx) in enumerate(PRED):
    xv=df[pk].values; xf=np.log10(xv) if logx else xv
    for j,(ok,olab,yscale) in enumerate(OUT):
        ax=axes[i,j]; y=df[ok].values; w=df["pop"].values
        ax.scatter(xv,y,s=np.clip(df["pop"]/2500,2,40),c="#1f6f8b",alpha=0.18,edgecolors="none")
        gam=LinearGAM(s(0,n_splines=8,lam=8)).fit(xf.reshape(-1,1),y,weights=w)
        if logx:
            xxv=np.logspace(np.log10(np.percentile(xv,1)),np.log10(np.percentile(xv,99)),120); xxf=np.log10(xxv)
        else:
            xxv=np.linspace(np.percentile(xv,1),np.percentile(xv,99),120); xxf=xxv
        mu=gam.predict(xxf.reshape(-1,1)); ci=gam.confidence_intervals(xxf.reshape(-1,1),width=.95)
        lo,hi=ci[:,0],ci[:,1]
        if yscale=="log": mu=np.clip(mu,0.5,None); lo=np.clip(lo,0.5,None)
        ax.fill_between(xxv,lo,hi,color="#c0392b",alpha=0.18); ax.plot(xxv,mu,color="#c0392b",lw=2.3)
        if logx: ax.set_xscale("log")
        if yscale=="log":
            ax.set_yscale("log"); ax.set_ylim(max(1,np.percentile(y[y>0],1)*0.8), np.percentile(y,99.5)*1.1)
        else:
            ax.set_ylim(0,np.percentile(y,99)*1.05)
        ax.grid(alpha=0.25,which="both")
        ax.set_xlabel(plab,fontsize=8.5)
        if j==0: ax.set_ylabel(olab,fontsize=9)
        if i==0: ax.set_title(olab,fontsize=10.5,fontweight="bold",color="#0d2b45")
fig.suptitle("Regional-unit characteristics vs TB indicators — scatter + population-weighted GAM (operational units, SP adults 2013–2024)",
             fontsize=12,fontweight="bold",y=0.998)
plt.tight_layout(rect=[0,0,1,0.99]); plt.savefig("/tmp/fig_predictor_outcome_gam.png",dpi=145,bbox_inches="tight"); plt.close()
print("Saved /tmp/fig_predictor_outcome_gam.png")
