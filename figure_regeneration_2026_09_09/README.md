# Final figure scripts and numeric verification

Scripts that produce the submitted versions of Figures 2, 3 and 5, and re-runnable checks of the
numbers quoted in the manuscript.

- Inputs: `Data/analytic/region_units.csv`, `Data/analytic/region_cases.csv`,
  `Data/analytic/ltfu_glmm_summary.json` (produced by `scripts/100_region_units.py` and
  `scripts/121_ltfu_region_glmm.py`)
- Figure scripts: `./scripts/` (`build_fig2.py`, `build_fig3.py`, `build_fig5.py`,
  `fig_common.py`); run from that directory, output to `./figures/`. Paths are read from the
  environment variables `SPTB_AN` (analytic folder) and `SPTB_OUT` (output folder).
- Verification: `./verification/` (`verify_all.py`, `verify_rates.py`, `verify_ltfu.py`,
  `ltfu_agestd.py`)

## What the scripts implement

**Rate basis.** Panels 2d, 3b and 3c use crude rates (`inc_crude`, `drate_crude`), the primary
basis of the analysis (ADR-0006). Axis labels read "Notification rate per 100,000/yr" and
"Rate per 100,000/yr"; "Notifications" is used in the Figure 2 and 3 labels rather than "Incidence".

**LTFU concentration (Figures 2a, 2b, 5a).** LTFU is the proportion of evaluated episodes
(ADR-0005). The cross-fitted (de-noised) concentration curve therefore splits the evaluated
episodes rather than the events: regions are ranked by the LTFU proportion in one half of the
episodes and the share of LTFU events is measured in the other half, accumulating regions up to
20% of the adult population (`denoised_curve_prop` in `build_fig2.py`, `denoised_share_prop` in
`build_fig5.py`). Notifications and mortality use the event-split routine. The per-capita LTFU
curve is shown in the supplement only.

**Bootstrap confidence intervals.** Pinned at B = 4,000 so the inset intervals are reproducible
(Figure 2d: 64–68%; Figure 3: 30–39% and 22–34%).

**Figure 5b.** Period labels use the compact two-line form (for example 2013–18 / 2019–24).

## Values verified against the analytic tables (`verification/verify_all.py`)

- 192,161 geocoded episodes; 7,314 regions; 35,933,055 adults; 9,301 deaths;
  21,561 LTFU events; 171,024 evaluated episodes
- 2,066 below-threshold regions = 16.3% of adults, 4.6% of cases
- geocoding tiers T1 58.6%, T2 21.3%, T3 10.3%, T4 1.9%, T5 7.9%
- statewide notification rate 44.6 and mortality 2.2 per 100,000 per year
- Gini: notifications 0.39, mortality 0.28, LTFU (proportion basis) 0.25, LTFU per capita 0.42
- top-20% population share: notifications 45.4% (47.4% before de-noising), mortality 38.8%
  (61.2% before de-noising), LTFU 25.2%
- deprivation excess fractions: notifications 34.1% (62,575 cases; gradient 33.5 to 68.8 per
  100,000), mortality 28.2% (2,509 deaths; gradient 1.8 to 3.1), Figure 2d 65.3%
- hotspot overlap (Jaccard) 0.44 / 0.20 / 0.17 / 0.19; hotspot counts 2,660; 1,521 (57%); 277; 121
- Cohen's d: notifications 0.44–0.64, mortality 0.17–0.39, LTFU 0.08–0.20
- favela regions: 1,185; 7.6% of adults; 12.5% of cases; rate 72.9; LTFU 14.9%
- out-of-sample capture: 2013–15 hotspots hold 40.8% of 2022–24 notifications; 43.9% and
  47.8% for the other two scenarios
- mixed-effects model: between-region variance 0.1385 (unadjusted), 0.1389 after case mix,
  0.1325 after supervised treatment; 171,024 episodes in 6,927 regions

The metropolitan/non-metropolitan split in Table 1 uses the flag produced by
`scripts/130_region_metro.py`.
