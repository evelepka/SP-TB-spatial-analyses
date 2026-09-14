# ADR-0003 — Analysis unit is a purpose-built ~5,000-adult regionalisation, with favelas as separate units

## Context
Census sectors are too small for stable rates; municipalities are too large (the capital would
be one unit). Aggregating sectors requires a size floor, which trades boundary fidelity for
rate stability: the floor subdivides large homogeneous areas (a large district may become
several units), a limitation acknowledged in the manuscript.

## Decision
Census sectors are aggregated into regions of about 5,000 adults by income, population and
contiguity, with favela (subnormal agglomerate) sectors grouped into their own units
(`scripts/83_regionalize_state.py`, output `regions_sectors.csv`). Sectors not covered fall
back to district units (`DIST_*`). Residential sectors with at least 100 residents define the
universe.

## Consequences
About 7,300 regions state-wide. Sensitivity to the size floor (modifiable areal unit problem)
is reported in the supplement.

**Small-count suppression.** `region_units.csv` sets rates to missing by design: notification
and mortality rates require at least 10 cases; LTFU and case-fatality require at least 10
evaluated episodes. Hotspot flags use the same thresholds, so suppressed regions never enter
the rate figures. The four regions with missing income or vulnerability are `DIST_*` fallback
units outside census coverage (all with fewer than 10 cases). Downstream scripts keep missing
values as missing; `test/check_artifact_pins.py` checks that the missing set equals the
below-threshold set.
