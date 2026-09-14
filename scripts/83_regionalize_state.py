"""Build the STATE-WIDE socioeconomically-homogeneous neighbourhood unit by spatially
constrained regionalisation. We use greedy region-growing (a standard regionalisation
heuristic): within each IBGE district, and SEPARATELY for favela (FCU) and non-favela
sectors, we grow contiguous regions by repeatedly adding the adjacent sector closest in
household income until the region reaches ~FLOOR adults; tiny leftovers are merged into the
most income-similar neighbour. Favela and non-favela are regionalised separately, so a favela
is never merged with an adjacent affluent area. Contiguity islands are reconnected to their
nearest sector so the growth never strands a singleton.
Output: /tmp/regions_sectors.csv  (CD_SETOR -> region_id) + composition summary.
"""
import geopandas as gpd, pandas as pd, numpy as np, libpysal, warnings, time
warnings.filterwarnings("ignore")
SP="/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
import os
FLOOR=int(os.environ.get("REGION_FLOOR",5000))   # sensitivity: override via env (3000 / 5000 / 8000)
np.random.seed(20240625)

print("Loading sectors + income/pop/favela...",flush=True)
g=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp",columns=["CD_SETOR","CD_DIST","CD_TIPO","NM_FCU","geometry"])
g["CD_SETOR"]=g["CD_SETOR"].astype(str); g["CD_DIST"]=g["CD_DIST"].astype(str)
vs=pd.read_csv("/tmp/vuln_sectors.csv",dtype={"CD_SETOR":str},low_memory=False)[["CD_SETOR","V06004","pop15"]]
g=g.merge(vs,on="CD_SETOR",how="left")
g["inc"]=pd.to_numeric(g["V06004"],errors="coerce"); g["pop15"]=pd.to_numeric(g["pop15"],errors="coerce").fillna(0)
g=g[g["CD_TIPO"].astype(str).isin(["0","1"])&(g["pop15"]>0)&g["inc"].notna()].reset_index(drop=True)
g["fav"]=g["NM_FCU"].notna(); g["inc_z"]=(g["inc"]-g["inc"].mean())/g["inc"].std()
print(f"  sectors: {len(g):,} | favela: {g['fav'].sum():,} | districts: {g['CD_DIST'].nunique():,}",flush=True)

def grow(sub,floor):
    n=len(sub)
    if n==0: return []
    if n<3 or sub["pop15"].sum()<1.5*floor: return [0]*n
    w=libpysal.weights.Queen.from_dataframe(sub,use_index=False)
    if w.islands:
        knn=libpysal.weights.KNN.from_dataframe(sub,k=1)
        w=libpysal.weights.set_operations.w_union(w,knn,silence_warnings=True)
    nb={i:list(w.neighbors[i]) for i in range(n)}
    pop=sub["pop15"].values.astype(float); inc=sub["inc_z"].values
    a=-np.ones(n,int); rid=0
    for seed in np.argsort(inc):                      # grow low-income blobs first
        if a[seed]>=0: continue
        reg=[seed]; a[seed]=rid; rpop=pop[seed]
        front=set(x for x in nb[seed] if a[x]<0)
        while rpop<floor and front:
            rm=inc[reg].mean(); best=min(front,key=lambda f:abs(inc[f]-rm))
            a[best]=rid; reg.append(best); rpop+=pop[best]
            front.discard(best); front.update(x for x in nb[best] if a[x]<0)
        rid+=1
    for i in range(n):                                # strand-free
        if a[i]<0:
            c=[a[x] for x in nb[i] if a[x]>=0]; a[i]=c[0] if c else rid; rid+= (0 if c else 1)
    for _ in range(4):                                # merge sub-floor/2 leftovers
        rp={r:pop[a==r].sum() for r in set(a)}
        small=[r for r in rp if rp[r]<floor*0.5]
        if not small: break
        for r in small:
            mem=np.where(a==r)[0]; adj=set(a[x] for m in mem for x in nb[m] if a[x]!=r)
            if not adj: continue
            rm=inc[mem].mean(); a[mem]=min(adj,key=lambda q:abs(inc[a==q].mean()-rm))
    return list(a)

print("Region-growing per district x favela-group...",flush=True)
out=[]; t0=time.time(); dists=g["CD_DIST"].unique(); done=0
for d in dists:
    gd=g[g["CD_DIST"]==d]
    for fv,sub in gd.groupby("fav"):
        sub=sub.reset_index(drop=True); labs=grow(sub,FLOOR)
        for i in range(len(sub)): out.append((sub.at[i,"CD_SETOR"],f"{d}_{'F' if fv else 'N'}_{labs[i]}"))
    done+=1
    if done%200==0: print(f"  {done}/{len(dists)} districts ({(time.time()-t0)/60:.1f} min)",flush=True)

reg=pd.DataFrame(out,columns=["CD_SETOR","region_id"]).merge(g[["CD_SETOR","pop15","fav","inc"]],on="CD_SETOR")
reg.to_csv("/tmp/regions_sectors.csv",index=False)
u=reg.groupby("region_id").agg(pop=("pop15","sum"),fav=("fav","mean"),inc=("inc","median"),n=("CD_SETOR","size"))
uf=u[u["fav"]>=0.9]; un=u[u["fav"]<=0.1]
print(f"\n=== STATE-WIDE REGIONS ===",flush=True)
print(f"  total regions: {len(u):,}  (favela {len(uf):,} | non-favela {len(un):,} | mixed {len(u)-len(uf)-len(un)})")
print(f"  adults/region — median {u['pop'].median():,.0f} | IQR {u['pop'].quantile(.25):,.0f}-{u['pop'].quantile(.75):,.0f} | min {u['pop'].min():,.0f} | max {u['pop'].max():,.0f}")
print(f"  % regions within 2,000-12,000 adults: {((u['pop']>=2000)&(u['pop']<=12000)).mean()*100:.0f}% | single-sector: {(u['n']==1).sum()}")
print(f"  social purity (favela vs non-favela kept apart): {((u['fav']>=0.9)|(u['fav']<=0.1)).mean()*100:.1f}%")
print(f"  capital units: {reg[reg['CD_SETOR'].str.startswith('3550308')]['region_id'].nunique():,} (was 96 districts)")
print("\nSaved /tmp/regions_sectors.csv",flush=True)
