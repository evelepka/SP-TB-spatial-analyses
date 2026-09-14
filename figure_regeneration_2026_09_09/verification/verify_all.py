"""Verify the numeric claims in v12 against the analytic tables."""
import numpy as np, pandas as pd
from scipy.stats import zscore, spearmanr

AN = "/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Data/analytic"
reg = pd.read_csv(f"{AN}/region_units.csv", dtype={"region_id": str})
co = pd.read_csv(f"{AN}/region_cases.csv", dtype={"region_id": str})

def chk(label, claim, got, tol=0.55):
    try:
        ok = abs(float(claim) - float(got)) <= tol
        flag = "OK " if ok else "MISMATCH"
    except Exception:
        flag = "    "
    print(f"  [{flag}] {label:52s} claim={claim!s:>16s}  computed={got}")

print("=== COUNTS ===")
chk("geocoded episodes", 192161, len(co))
chk("regions", 7314, len(reg))
chk("adult population", 35933055, int(reg['pop'].sum()))
chk("TB deaths", 9301, int(co['death'].sum()))
chk("LTFU events", 21561, int(co['aband'].sum()))
chk("evaluated episodes", 171024, int(co['eval'].sum()))
chk("regions <10 cases", 2066, int((reg['n'] < 10).sum()))
chk("  their share of adult pop, %", 16.3, round(100*reg.loc[reg['n']<10,'pop'].sum()/reg['pop'].sum(),1))
chk("  their share of cases, %", 4.6, round(100*reg.loc[reg['n']<10,'n'].sum()/reg['n'].sum(),1))

print("\n=== GEOCODING TIERS (share of episodes) ===")
t = co['tier'].value_counts(normalize=True).sort_index()*100
for k, v in t.items():
    print(f"      tier {k}: {v:.1f}%")
chk("street level or better (T1-T3), %", 90.2, round(t.reindex([1,2,3]).sum(),1))
chk("exact address (T1), %", 58.6, round(t.get(1, np.nan),1))
chk("neighbourhood centroid (T4), %", 1.9, round(t.get(4, np.nan),1))
chk("postal-code centroid (T5), %", 7.9, round(t.get(5, np.nan),1))

print("\n=== FAVELA / TABLE 1 ===")
fav = reg[reg['favela'] > 0.5] if reg['favela'].max() <= 1 else reg[reg['favela'] >= 50]
chk("favela regions n", 1185, len(fav))
chk("favela share of adult pop, %", 7.6, round(100*fav['pop'].sum()/reg['pop'].sum(),1))
chk("favela share of cases, %", 12.5, round(100*fav['n'].sum()/reg['n'].sum(),1))
chk("favela notification rate /100k/yr", 72.9, round(fav['n'].sum()/fav['pop'].sum()/12*1e5,1))
chk("statewide notification rate /100k/yr", 44.6, round(reg['n'].sum()/reg['pop'].sum()/12*1e5,1))
chk("statewide mortality /100k/yr", 2.2, round(co['death'].sum()/reg['pop'].sum()/12*1e5,1))

print("\n=== HOTSPOT OVERLAP (Jaccard) ===")
S = {k: set(reg[reg[c]]["region_id"]) for k, c in
     [("inc","hs_inc"),("mort","hs_mort"),("ltfu","hs_aband"),("vuln","hs_vuln")]}
def jac(a,b): return len(S[a]&S[b])/len(S[a]|S[b])
chk("Jaccard notif-mort", 0.44, round(jac("inc","mort"),2), 0.015)
chk("Jaccard notif-LTFU", 0.20, round(jac("inc","ltfu"),2), 0.015)
chk("Jaccard mort-LTFU", 0.17, round(jac("mort","ltfu"),2), 0.015)
chk("Jaccard LTFU-vuln", 0.19, round(jac("ltfu","vuln"),2), 0.015)
anyhs = S["inc"]|S["mort"]|S["ltfu"]
only1 = sum(1 for r in anyhs if sum(r in S[k] for k in ("inc","mort","ltfu"))==1)
all3 = len(S["inc"]&S["mort"]&S["ltfu"])
chk("regions hotspot for any outcome", 2660, len(anyhs))
chk("  hotspot for only one", 1521, only1)
chk("  hotspot for all three", 277, all3)
chk("  pct only one, %", 57, round(100*only1/len(anyhs)))
chk("all four (incl vulnerability)", 121, len(S["inc"]&S["mort"]&S["ltfu"]&S["vuln"]))

print("\n=== COHEN'S D (>=10-case regions) ===")
d = reg[reg["n"] >= 10].dropna(subset=["income","favela","illit","residents"]).copy()
d["c_income"]=-zscore(d["income"]); d["c_favela"]=zscore(d["favela"])
d["c_illit"]=zscore(d["illit"]);    d["c_resid"]=zscore(d["residents"])
def cohend(col, flag):
    a=d.loc[d[flag],col]; b=d.loc[~d[flag],col]
    sp=np.sqrt((a.var()+b.var())/2); return (a.mean()-b.mean())/sp
for flag, name, lo, hi in [("hs_inc","notification",0.44,0.64),("hs_mort","mortality",0.17,0.39),("hs_aband","LTFU",0.08,0.20)]:
    vals={c:round(cohend(c,flag),2) for c in ["c_income","c_favela","c_illit","c_resid"]}
    print(f"      {name:12s} d: {vals}  claimed range {lo}-{hi}")

print("\n=== LTFU BY DEPRIVATION QUINTILE (per evaluated episode) ===")
r2 = reg[reg["n"]>=10].dropna(subset=["income"]).copy()
o = r2.sort_values("income", ascending=False)
cum = o["pop"].cumsum()/o["pop"].sum()
o["q"] = np.ceil(np.clip(cum,1e-9,1)*5).astype(int).clip(1,5)
ev = co[co["eval"]==1].groupby("region_id").agg(ev=("eval","sum"), ab=("aband","sum"))
o = o.join(ev, on="region_id")
g = o.groupby("q")[["ev","ab"]].sum()
g["pct"] = 100*g["ab"]/g["ev"]
print("      LTFU %% by income-deprivation quintile (1=least deprived):")
for q, row in g.iterrows():
    print(f"        Q{q}: {row['pct']:.1f}%")
chk("most deprived (Q5) LTFU %", 13.8, round(g.loc[5,"pct"],1))
chk("least deprived (Q1) LTFU %", 12.3, round(g.loc[1,"pct"],1))

print("\n=== SPEARMAN: region LTFU vs vulnerability ===")
rr = reg[reg["n"]>=10].dropna(subset=["ltfu_crude","vuln"])
chk("Spearman rho LTFU-vuln (crude proxy)", 0.01, round(spearmanr(rr["ltfu_crude"], rr["vuln"]).statistic,2), 0.12)
