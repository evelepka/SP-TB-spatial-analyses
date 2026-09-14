"""Manuscript composite figures 2 and 5, built end-to-end from the analytic artifacts.

These composites previously had NO in-repo builder (the PAF and out-of-sample panels were
assembled in lost session scripts — the same 'number without a script' debt as the STROBE flow).
This script is now their single source.

Figure 2 (2x2): (a) de-noised Lorenz curves  (b) de-noised shares at 5/10/20/40% of population
               (c) 4-set hotspot Venn        (d) age-standardised rate by incidence quintile + PAF
Figure 5 (1x3): (a) top-20% share per 3-yr period  (b) out-of-sample hotspot capture  (c) alluvial

RANK=std (default) ranks by age-standardized rate (LTFU: age-adjusted proportion of evaluated,
ADR-0005); RANK=crude reproduces the historical panels for the supplement (suffix _crude).
Validation: under RANK=crude this script reproduces the July manuscript numbers
(PAF 65% [63-67], excess 118,612; OOS capture 44/43/41 vs 48).
Outputs: /tmp/fig2_composite{_crude}.png, /tmp/fig5_composite{_crude}.png
"""
import pandas as pd, numpy as np, os, matplotlib, matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.path import Path
import matplotlib.patches as mpatches
from venn import venn
np.random.seed(20240625); matplotlib.rcParams.update({"font.family":"sans-serif","font.size":11})
import sys; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from rank_basis import RANK,SUF,RATE,rank_base as _rb

reg=pd.read_csv("/tmp/region_units.csv",dtype={"region_id":str})
co=pd.read_csv("/tmp/region_cases.csv",dtype={"region_id":str})
pv=reg.set_index("region_id")["pop"]; units=list(pv.index); idx={u:i for i,u in enumerate(units)}
K=len(units); popv=pv.values; TOT=popv.sum()
co["ri"]=co["region_id"].map(idx); co=co.dropna(subset=["ri"]); co["ri"]=co["ri"].astype(int)
EXPC={"inc":"E_inc","mort":"E_dr","aband":"E_ab"}
def base_of(ln): return _rb(reg,ln,popv)

GRID=np.linspace(0,1,101)
def denoised_curve(ix,base,B=200):
    acc=np.zeros(len(GRID)); m=0
    for _ in range(B):
        h=np.random.rand(len(ix))<0.5
        a=np.bincount(ix[h],minlength=K).astype(float); b=np.bincount(ix[~h],minlength=K).astype(float)
        for rk,vl in [(a,b),(b,a)]:
            if vl.sum()==0: continue
            ra=rk/base; o=np.argsort(-ra); cp=np.cumsum(popv[o])/TOT; cv=np.cumsum(vl[o])/vl.sum()
            acc+=np.interp(GRID,cp,cv); m+=1
    return acc/m
def smooth_monotone(c):
    from scipy.interpolate import PchipInterpolator
    anchors=np.array([0,.05,.10,.15,.20,.30,.40,.55,.70,.85,1.0])
    yv=np.maximum.accumulate(np.interp(anchors,GRID,c)); yv[0]=0.0; yv[-1]=1.0
    return np.clip(PchipInterpolator(anchors,yv)(GRID),0,1)

LENS=[("TB notifications","inc",co["age"]>=15,"#1a3d5c"),("TB mortality","mort",co["death"]==1,"#7a0177"),
      ("LTFU","aband",co["aband"]==1,"#1f6f8b")]
QS=[0.05,0.10,0.20,0.40]

# ---------------- FIGURE 2 ----------------
fig,axes=plt.subplots(2,2,figsize=(12.32,10.17))
axA,axB,axC,axD=axes[0,0],axes[0,1],axes[1,0],axes[1,1]
res=[]
for lab,ln,mask,col in LENS:
    ix=co[mask]["ri"].values
    curve=smooth_monotone(denoised_curve(ix,base_of(ln))); dg=2*np.trapz(curve,GRID)-1
    deno=[float(np.interp(q,GRID,curve))*100 for q in QS]; res.append((lab,deno,curve,dg,col))
    print(f"[{RANK}] {lab:14s} 5/10/20/40% -> {'/'.join(f'{x:.0f}' for x in deno)}%  Gini {dg:.2f}")
axA.plot([0,1],[0,1],"--",color="#999",lw=1.2,label="equality (no concentration)")
for lab,deno,curve,dg,col in res: axA.plot(GRID,curve,color=col,lw=2.6,label=f"{lab} (Gini {dg:.2f})")
axA.set_xlabel("Cumulative share of adult population\n(highest-rate regions first)")
axA.set_ylabel("Cumulative share of events"); axA.legend(fontsize=9.5,loc="lower right")
axA.grid(alpha=0.3); axA.set_xlim(0,1); axA.set_ylim(0,1)
axA.set_title("(a)",loc="left",fontsize=13,fontweight="bold")
xq=[q*100 for q in QS]
axB.plot([0,40],[0,40],":",color="#bbb",lw=1.1,zorder=1,label="proportional (no concentration)")
for lab,deno,curve,dg,col in res: axB.plot(xq,deno,"-o",color=col,lw=2.5,ms=6,label=lab,zorder=3)
axB.set_xticks(xq); axB.set_xlabel("% of adult population in highest-rate regions")
axB.set_ylabel("% of events concentrated there"); axB.set_ylim(0,None); axB.grid(alpha=0.3)
axB.legend(fontsize=9,loc="upper left"); axB.set_title("(b)",loc="left",fontsize=13,fontweight="bold")
VL={"Notifications":set(reg[reg["hs_inc"]]["region_id"]),"Mortality":set(reg[reg["hs_mort"]]["region_id"]),
    "LTFU":set(reg[reg["hs_aband"]]["region_id"]),"Vulnerability":set(reg[reg["hs_vuln"]]["region_id"])}
venn(VL,ax=axC,fontsize=9,legend_loc="upper left",cmap=ListedColormap(["#1a3d5c","#7a0177","#1f6f8b","#b8860b"]))
axC.set_aspect("auto"); axC.set_xlim(-0.02,1.02); axC.set_ylim(0.06,0.94)
axC.set_title("(c)",loc="left",fontsize=13,fontweight="bold")

# (d) age-standardised rate by population-weighted incidence quintile; excess vs lowest quintile; PAF
T=12; state_rate=reg["n"].sum()/(reg["pop"].sum()*T)*1e5
RC=RATE["inc"]
el=reg.dropna(subset=[RC]).sort_values(RC).copy()   # eligible regions, ascending on the rank-basis rate
cum=el["pop"].cumsum()/el["pop"].sum(); el["q5"]=np.minimum((cum*5).astype(int),4)
qs=el.groupby("q5").agg(n=("n","sum"),E=("E_inc","sum"),pop=("pop","sum"))
if RANK=="std":
    qs["rate"]=qs["n"]/qs["E"]*state_rate                  # indirectly standardised rate per quintile
    sir_ref=qs.loc[0,"n"]/qs.loc[0,"E"]; qs["excess"]=qs["n"]-qs["E"]*sir_ref
else:
    qs["rate"]=qs["n"]/(qs["pop"]*T)*1e5                     # crude rate per quintile
    qs["excess"]=qs["n"]-qs["pop"]*T*qs.loc[0,"rate"]/1e5
tot_excess=qs["excess"][1:].sum(); paf=tot_excess/qs["n"].sum()*100
# 95% CI by region bootstrap (the historical 63-67 was the same design; B=500)
def _paf_of(df):
    df=df.sort_values(RC)
    cum=df["pop"].cumsum()/df["pop"].sum(); q=np.minimum((cum*5).astype(int),4)
    g=df.groupby(q.values).agg(n=("n","sum"),E=("E_inc","sum"),pop=("pop","sum"))
    if RANK=="std":
        s=g.loc[0,"n"]/g.loc[0,"E"]; return (g["n"]-g["E"]*s)[1:].sum()/g["n"].sum()*100
    r0=g.loc[0,"n"]/(g.loc[0,"pop"]*T)
    return (g["n"]-g["pop"]*T*r0)[1:].sum()/g["n"].sum()*100
_bs=[_paf_of(el.sample(len(el),replace=True)) for _ in range(500)]
ci_lo,ci_hi=np.percentile(_bs,[2.5,97.5])
print(f"[{RANK}] excess fraction {paf:.0f}% (95% CI {ci_lo:.0f}-{ci_hi:.0f}) excess {tot_excess:,.0f}")
bars=axD.bar(range(1,6),qs["rate"],color="#1a3d5c",width=0.62)
for i,(r,e) in enumerate(zip(qs["rate"],qs["excess"])):
    if i>0: axD.text(i+1,r+2.5,f"+{e:,.0f}",ha="center",fontsize=9)
axD.axhline(qs.loc[0,"rate"],ls="--",color="#555",lw=1.1)
axD.text(5.45,qs.loc[0,"rate"],"reference\n(lowest notification rate)",fontsize=8,color="#555",va="center",ha="left")
axD.text(0.03,0.95,f"Excess fraction = {paf:.0f}%  (95% CI {ci_lo:.0f}–{ci_hi:.0f})\nExcess cases: {tot_excess:,.0f}",
         transform=axD.transAxes,va="top",fontsize=10,bbox=dict(boxstyle="round",fc="white",ec="#aaa"))
axD.set_xlabel("Notification-rate quintile (1 = lowest → 5 = highest)")
axD.set_ylabel("Age-standardised rate per 100,000/yr"); axD.set_xticks(range(1,6))
axD.set_title("(d)",loc="left",fontsize=13,fontweight="bold")
plt.tight_layout(); plt.savefig(f"/tmp/fig2_composite{SUF}.png",dpi=300,bbox_inches="tight"); plt.close()
print(f"Saved /tmp/fig2_composite{SUF}.png")

# ---------------- FIGURE 5 ----------------
PERIODS=[(2013,2015),(2016,2018),(2019,2021),(2022,2024)]
PLAB=["2013–15","2016–18","2019–21","2022–24"]
def ri_of(y0,y1,coln=None):
    s=co[co["year"].between(y0,y1)]
    if coln is not None: s=s[s[coln]==1]
    return s["ri"].values
def denoised_share(ri,base,B=150,q=0.20):
    if len(ri)<50: return np.nan
    s=[]
    for _ in range(B):
        h=np.random.rand(len(ri))<0.5
        a=np.bincount(ri[h],minlength=K).astype(float); b=np.bincount(ri[~h],minlength=K).astype(float)
        for rk,vl in [(a,b),(b,a)]:
            if vl.sum()==0: continue
            ra=rk/base; o=np.argsort(-ra); cp=np.cumsum(popv[o])/TOT; cv=np.cumsum(vl[o])/vl.sum()
            s.append(np.interp(q,cp,cv)*100)
    return np.mean(s)
def hotspot_set(cnt,base):
    r=cnt/base; o=np.argsort(-r); cum=np.cumsum(popv[o]); return o[cum<=TOT*0.20]
def capture(train,test,base):
    cnt=np.bincount(ri_of(*train),minlength=K).astype(float)
    hs=set(hotspot_set(cnt,base).tolist())
    te=ri_of(*test); return np.isin(te,list(hs)).mean()*100

fig,axes=plt.subplots(1,3,figsize=(16.9,4.55),gridspec_kw={"width_ratios":[1,1,1.9]})
a,b,c=axes
OUTC=[("inc",None,"#1a3d5c","Notifications"),("mort","death","#7a0177","Mortality"),("aband","aband","#1f6f8b","LTFU")]
for ln,coln,col,lab in OUTC:
    sh=[denoised_share(ri_of(*p,coln),base_of(ln)) for p in PERIODS]
    a.plot(range(4),sh,"o-",color=col,lw=2.4,ms=7,label=lab)
    print(f"[{RANK}] per-period {ln}: {[round(x) for x in sh]}")
a.set_xticks(range(4)); a.set_xticklabels(PLAB,fontsize=9)
a.set_xlabel("3-year period"); a.set_ylabel("% of events in top 20% of population\n(de-noised, cross-fit)")
a.set_ylim(0,None); a.legend(fontsize=9,title="Outcome"); a.grid(alpha=0.3)
a.set_title("(a)",loc="left",fontsize=13,fontweight="bold")

base_i=base_of("inc")
SETS=[((2013,2018),(2019,2024),"trained 2013-2018\ntested 2019-2024"),
      ((2013,2018),(2022,2024),"trained 2013-2018\ntested 2022-2024"),
      ((2013,2015),(2022,2024),"trained 2013-2015\ntested 2022-2024")]
old=[capture(tr,te,base_i) for tr,te,_ in SETS]
best=[capture(te,te,base_i) for _,te,_ in SETS]
print(f"[{RANK}] OOS capture: old {[round(x) for x in old]} vs best {[round(x) for x in best]}")
x=np.arange(3); w=0.36
b.bar(x-w/2,old,w,color="#1a3d5c",label="Hotspots from old data")
b.bar(x+w/2,best,w,color="#b9bec4",label="Best possible (current data)")
for xi,(o,bb) in enumerate(zip(old,best)):
    b.text(xi-w/2,o+0.8,f"{o:.0f}",ha="center",fontsize=10,fontweight="bold")
    b.text(xi+w/2,bb+0.8,f"{bb:.0f}",ha="center",fontsize=9,color="#666")
b.axhline(20,ls=":",color="#333",lw=1.0); b.text(2.2,20.7,"no targeting (20%)",fontsize=8,color="#777")
b.set_xticks(x); b.set_xticklabels([s for _,_,s in SETS],fontsize=8)
b.set_ylabel("Test-period cases captured (%)\ntop 20% of population"); b.set_ylim(0,62)
b.legend(fontsize=9); b.grid(alpha=0.3,axis="y"); b.set_title("(b)",loc="left",fontsize=13,fontweight="bold")

# (c) alluvial — incidence quintiles per period, ribbons coloured by source quintile
NB=5; rege=reg[reg["n"]>=10].reset_index(drop=True)
qden=reg.set_index("region_id")["E_inc"] if RANK=="std" else reg.set_index("region_id")["pop"]
Q=pd.DataFrame(index=rege["region_id"])
for i,p in enumerate(PERIODS):
    cq=co[co.year.between(*p)].groupby("region_id").size()
    rr=rege.set_index("region_id").assign(c=cq).fillna({"c":0})
    den=qden.reindex(rr.index)
    Q[i]=pd.qcut((rr["c"]/den).rank(method="first"),NB,labels=False).values
gap=0.02; bh=(1-(NB-1)*gap)/NB
def yb(j): return j*(bh+gap)
nodw=0.05; qcols=["#fdd9a0","#fdae61","#f46d43","#c0392b","#7a0177"]
def ribbon(ax,x0,x1,ys0,ys1,yt0,yt1,color):
    xm=(x0+x1)/2
    verts=[(x0,ys0),(xm,ys0),(xm,yt0),(x1,yt0),(x1,yt1),(xm,yt1),(xm,ys1),(x0,ys1),(x0,ys0)]
    codes=[Path.MOVETO,Path.CURVE4,Path.CURVE4,Path.CURVE4,Path.LINETO,Path.CURVE4,Path.CURVE4,Path.CURVE4,Path.CLOSEPOLY]
    ax.add_patch(mpatches.PathPatch(Path(verts,codes),fc=color,ec="none",alpha=0.62,zorder=1))
for t in range(3):
    M=np.zeros((NB,NB))
    for (i,j),v in Q.groupby([t,t+1]).size().items(): M[int(i),int(j)]=v
    ni=M.sum(axis=1); nj=M.sum(axis=0)
    x0=t+nodw/2; x1=(t+1)-nodw/2
    soff={i:yb(i) for i in range(NB)}; toff={j:yb(j) for j in range(NB)}
    for i in range(NB):
        for j in range(NB):
            cnt=M[i,j]
            if cnt==0: continue
            hs_=bh*cnt/ni[i]; ht=bh*cnt/nj[j]
            ys0=soff[i]; ys1=ys0+hs_; soff[i]=ys1
            yt0=toff[j]; yt1=yt0+ht; toff[j]=yt1
            ribbon(c,x0,x1,ys0,ys1,yt0,yt1,qcols[i])
for t in range(4):
    for j in range(NB):
        c.add_patch(mpatches.Rectangle((t-nodw/2,yb(j)),nodw,bh,fc="#33373b",ec="none",zorder=3))
    c.text(t,-0.075,PLAB[t],ha="center",va="top",fontsize=9,fontweight="bold",clip_on=False)
ql=["Q1 (lowest)","Q2","Q3","Q4","Q5 (highest)"]
for j in range(NB):
    c.text(-0.10,yb(j)+bh/2,ql[j],ha="right",va="center",fontsize=8.5,
           color=qcols[j] if j!=0 else "#c8922f",fontweight="bold",clip_on=False)
c.text(3.0,1.06,"ribbon colour = notification-rate quintile at the start of each step",
       ha="right",va="bottom",fontsize=8.5,style="italic",color="#666",clip_on=False)
c.set_xlim(-0.03,3.03); c.set_ylim(-0.02,1.02); c.axis("off")
c.set_title("(c)",loc="left",fontsize=13,fontweight="bold")
plt.tight_layout(); plt.savefig(f"/tmp/fig5_composite{SUF}.png",dpi=300,bbox_inches="tight"); plt.close()
print(f"Saved /tmp/fig5_composite{SUF}.png")
