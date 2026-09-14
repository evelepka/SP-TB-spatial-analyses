"""Canonical builder for the place-vulnerability composite used in the paper.

MAIN composite (vuln_final) = mean of FIVE z-standardised domains of structural/social
deprivation, anchored at the 2022 census sector:
  income      household income of the responsible person (entered as deprivation)
  illit       adult illiteracy
  sanit       inadequate sanitation
  crowd       intra-household crowding (mean residents per household) -- a marker of
              social vulnerability (larger families sharing one dwelling)
  favela      urban agglomeration / favela (aglomerado subnormal) -- precarious housing,
              informal tenure, absent services = extreme structural deprivation, and the
              WHO investment-case target population. KEPT IN by user decision (it is an
              important axis); a 4-domain version WITHOUT favela is also emitted for the
              appendix sensitivity (vuln_nofav) so the dependence on this one axis is shown.

Excluded by design: race (rho 0.98 with the composite, redundant); the demographic/
life-cycle axis (age-confounds TB rates); neighbourhood density (transmission, not
deprivation).

Reads /tmp/vuln_sectors.csv (script 64, which already holds the z_* domains) and writes
/tmp/vuln_final.csv with BOTH the 5-domain main composite (vuln_final) and the 4-domain
appendix version (vuln_nofav). Self-contained + reproducible.
"""
import pandas as pd, numpy as np
from scipy.stats import spearmanr

D5 = ["z_income","z_illit","z_crowd","z_favela"]            # MAIN (manuscript): income+illiteracy+crowding+favela
D4 = ["z_income","z_illit","z_crowd"]                        # sensitivity (favela out)
D6 = D5 + ["z_dens"]                                         # sensitivity (+ pop density)
# NOTE 2026-06-29: sanitation DROPPED — near-universal in SP (87% of adult pop adequate),
# weakest IPVS link (0.29), ~zero TB link (-0.07), and INCLUDING it LOWERS IPVS agreement
# (0.762->0.727). Precarious housing (cortiço) also tested + rejected (only 0.3% of sectors
# have any; IPVS 0.00, incidence 0.04 — census undercounts cortiços). Composite = 4 domains.
print("Loading sector domains (script 64) ...")
sec = pd.read_csv("/tmp/vuln_sectors.csv", dtype={"CD_SETOR":str}, low_memory=False)
sec = sec[(sec["pop15"] > 0) & (sec["AREA_KM2"] > 0)].copy()
# population density (residents/km2), log-z — NOT a deprivation domain (it is slightly
# NEGATIVELY correlated with the composite: SP's densest sectors include verticalised
# high-income districts), but kept as a transmission-related sensitivity (TB is a disease
# of urban agglomeration). Discussed in Methods 3.9 / Appendix D.
from scipy.stats import zscore
sec["z_dens"] = zscore(np.log1p(sec["pop15"] / sec["AREA_KM2"]))

before = len(sec)
sec = sec.dropna(subset=D6)
print(f"  populated sectors: {before:,} | with all domains: {len(sec):,}")

sec["vuln_final"]   = sec[D5].mean(axis=1)   # 5-domain main
sec["vuln_nofav"]   = sec[D4].mean(axis=1)   # 4-domain appendix (favela out)
sec["vuln_density"] = sec[D6].mean(axis=1)   # 6-domain appendix (density in)

out = sec[["CD_SETOR"] + D6 + ["vuln_final","vuln_nofav","vuln_density","pop15","unit_id"]].copy()
out.to_csv("/tmp/vuln_final.csv", index=False)
print(f"  wrote /tmp/vuln_final.csv  ({len(out):,} sectors)")
print(f"  Spearman(density, 5-dom composite) = {spearmanr(sec['z_dens'],sec['vuln_final'])[0]:+.3f}  (negative => density is not deprivation)")

r,_ = spearmanr(out["vuln_final"], out["vuln_nofav"])
print(f"  Spearman(vuln_final[5-dom], vuln_nofav[4-dom]) = {r:.3f}")
for old in ["vuln","vuln_norace"]:
    if old in sec.columns:
        rr,_ = spearmanr(sec["vuln_final"], sec[old])
        print(f"  Spearman(vuln_final, {old}) = {rr:.3f}")
print(f"  vuln_final (5-dom): mean {out['vuln_final'].mean():+.3f}  sd {out['vuln_final'].std():.3f}")
