"""Canonical builder for the place-vulnerability composite used in the paper.

MAIN composite (vuln_final) = mean of FOUR z-standardised domains of structural/social
deprivation, anchored at the 2022 census sector:
  income      household income of the responsible person (entered as deprivation)
  illit       adult illiteracy
  crowd       intra-household crowding (mean residents per household) -- a marker of
              social vulnerability (larger families sharing one dwelling)
  favela      urban agglomeration / favela (aglomerado subnormal) -- precarious housing,
              informal tenure, absent services = extreme structural deprivation, and the
              WHO investment-case target population. retained as a core domain (see
              docs/decisions/0004); a three-domain version without favela is also emitted for the
              supplementary sensitivity (vuln_nofav) so the dependence on this one axis is shown.

Excluded by design: race (rho 0.98 with the composite, redundant); the demographic/
life-cycle axis (age-confounds TB rates); neighbourhood density (transmission, not
deprivation).

Reads /tmp/vuln_sectors.csv (script 64, which already holds the z_* domains) and writes
/tmp/vuln_final.csv with the four-domain main composite (vuln_final), the three-domain version
without favela (vuln_nofav) and the five-domain version with density (vuln_density). Self-contained + reproducible.
"""
import pandas as pd, numpy as np
from scipy.stats import spearmanr

D4_MAIN = ["z_income","z_illit","z_crowd","z_favela"]            # MAIN (manuscript): income+illiteracy+crowding+favela
D3_NOFAV = ["z_income","z_illit","z_crowd"]                        # sensitivity (favela out)
D5_DENS = D4_MAIN + ["z_dens"]                                         # sensitivity (+ pop density)
# Sanitation excluded: near-universal in São Paulo (adequate for 87% of adults) and not associated
# with TB indicators. Precarious housing (cortiço) also excluded (0.3% of sectors). Composite = 4 domains.
print("Loading sector domains (script 64) ...")
sec = pd.read_csv("/tmp/vuln_sectors.csv", dtype={"CD_SETOR":str}, low_memory=False)
sec = sec[(sec["pop15"] > 0) & (sec["AREA_KM2"] > 0)].copy()
# population density (residents/km2), log-z — NOT a deprivation domain (it is slightly
# NEGATIVELY correlated with the composite: SP's densest sectors include verticalised
# high-income districts), but kept as a transmission-related sensitivity (TB is a disease
# of urban agglomeration). See docs/decisions/0004.
from scipy.stats import zscore
sec["z_dens"] = zscore(np.log1p(sec["pop15"] / sec["AREA_KM2"]))

before = len(sec)
sec = sec.dropna(subset=D5_DENS)
print(f"  populated sectors: {before:,} | with all domains: {len(sec):,}")

sec["vuln_final"]   = sec[D4_MAIN].mean(axis=1)   # 4-domain main
sec["vuln_nofav"]   = sec[D3_NOFAV].mean(axis=1)   # 3-domain sensitivity (favela out)
sec["vuln_density"] = sec[D5_DENS].mean(axis=1)   # 5-domain sensitivity (density in)

out = sec[["CD_SETOR"] + D5_DENS + ["vuln_final","vuln_nofav","vuln_density","pop15","unit_id"]].copy()
out.to_csv("/tmp/vuln_final.csv", index=False)
print(f"  wrote /tmp/vuln_final.csv  ({len(out):,} sectors)")
print(f"  Spearman(density, 4-dom composite) = {spearmanr(sec['z_dens'],sec['vuln_final'])[0]:+.3f}  (negative => density is not deprivation)")

r,_ = spearmanr(out["vuln_final"], out["vuln_nofav"])
print(f"  Spearman(vuln_final[4-dom], vuln_nofav[3-dom]) = {r:.3f}")
for old in ["vuln","vuln_norace"]:
    if old in sec.columns:
        rr,_ = spearmanr(sec["vuln_final"], sec[old])
        print(f"  Spearman(vuln_final, {old}) = {rr:.3f}")
print(f"  vuln_final (4-dom): mean {out['vuln_final'].mean():+.3f}  sd {out['vuln_final'].std():.3f}")
