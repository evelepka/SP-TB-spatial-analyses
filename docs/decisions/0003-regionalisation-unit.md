# ADR-0003 — Analysis unit is the ~5,000-adult regionalisation, favelas split out

- **Status:** accepted (2026-07, advisor; report in commit f04deac)
- **Superseded by:** —

## Context

Census sectors are too small (unstable rates); municipalities are too large (the capital is
one unit). An operational unit existed, but the advisor preferred a purpose-built
regionalisation. Aggregating sectors needs a size floor, which trades boundary fidelity for
rate stability (the ~5,000 floor subdivides large homogeneous areas — e.g. Itaim Bibi → 14
units; recorded as an honest limitation).

## Decision

Sectors are aggregated into ~5,000-adult regions by income + population + contiguity, with
favela (subnormal) sectors split into their own units (`scripts/83_regionalize_state.py` →
`regions_sectors.csv`). Sectors not covered fall back to district units (`DIST_*`). Residential
sectors with ≥100 residents define the universe.

## Consequences

~7,300 region units state-wide. MAUP sensitivity: the floor is parameterised and a region-size
sensitivity (floor 83, alternative metrics) is Supp Table S2 (commit 1f1c5c0).

**Small-count suppression (verified exact, 2026-08-10):** `region_units.csv` sets adjusted
rates to NaN by design — `inc_adj`/`drate_adj`/`mortprop_adj` require **n ≥ 10 cases** (2,066
of 7,314 regions are NaN, exactly the n<10 set), `ltfu_adj`/`cfr` require **ne ≥ 10 evaluated
episodes** (2,386 regions, exactly the ne<10 set). Hotspot flags also require the same
thresholds, so suppressed regions never enter rate figures. The 4 regions with NaN
`income`/`vuln` are `DIST_*` fallback units outside the census-vulnerability coverage (pop
155-744, all n<10 — harmless). Downstream scripts must handle NaN, never fill it;
`test/check_artifact_pins.py` asserts the NaN↔threshold correspondence stays exact.
