# Analysis pipeline

Reproduction order for the manuscript analysis. Scripts read and write intermediates in
`/tmp`; the expensive intermediates are persisted in the project data folder
(`Data/analytic/`) and restored by `scripts/00_restore_tmp.py`.

## Quick start (persisted intermediates available)
```
python3 scripts/00_restore_tmp.py      # Data/analytic/* -> /tmp
python3 scripts/100_region_units.py    # region-level dataset from the geocoded cohort
# figures: 101 102 103 104 105 106 122 123 124
```

## Full rebuild from raw notifications
| step | script | output | note |
|------|--------|--------|------|
| CNEFE download | `20_`, `28_`, `40_download_cnefe_*.py` | CNEFE 2022 address files | IBGE public FTP |
| geocode Greater São Paulo | `21_cnefe_match_cohort.py` | `cohort_with_cnefe.csv` | address match against CNEFE |
| geocode Baixada Santista | `29b_cnefe_match_baixada_improved.py` | `cohort_baixada_with_cnefe_v2.csv` | new/recurrent episodes; favela hint |
| geocode rest of state | `41_cnefe_match_sp_outros.py` | `cohort_sp_outros_with_cnefe.csv` | |
| regionalise | `83_regionalize_state.py` | `regions_sectors.csv` | census sectors -> ~5,000-adult regions, favela sectors as separate units |
| geocoded base, step 1 | `108_build_geocoded_cohort.py` | `geocoded_cohort.csv` | spatial overlay of coordinates on the official census mesh |
| geocoded base, step 2 | `109_cep_fallback.py` | `geocoded_cohort.csv` (+T5) | postal-code fallback for unmatched addresses |
| vulnerability index | `64_vulnerability_composite.py` -> `89_build_vuln_final.py` | `vuln_sectors.csv`, `vuln_final.csv` | four census domains (income, illiteracy, crowding, favela) |
| region dataset | `100_region_units.py` | `region_units.csv`, `region_cases.csv` | per-region cases, population, crude and age-standardised rates, LTFU, vulnerability, hotspot flags on the basis set in `rank_basis.py` |
| main figures | `101`–`106` | `fig1..fig5*.png` | |
| composite figures | `122_manuscript_composites.py`, `123_fig1_choropleth.py`, `124_fig3_composite.py` | Figures 1, 2, 3 and 5 as laid out in the manuscript | |
| metropolitan flag | `130_region_metro.py` | `region_metro.csv` | used by 129 |
| Table 1 | `112_table1.py` | `table1.csv` | |
| LTFU model | `121_ltfu_region_glmm.py` | `ltfu_glmm_summary.json` | mixed-effects logistic model of LTFU with a region random effect |
| Supplementary Figures S1–S7 | `114_figS_strobe.py`, `111_`, `115_`, `129_figS5_S7_deprivation_variants.py`, `131_figS4_spatial_structure.py` | | STROBE flow, concentration, deprivation quintiles, Moran's I / spatial-lag model |
| sensitivity analyses | same scripts with `RANK=std` (suffix `_std`) or `RANK=percap` | `*_std.png`, `*_percap.png` | age-standardised rates; LTFU per capita |
| supplement document | `116_build_supplementary_docx.py` | supplementary .docx | |

The final versions of Figures 2, 3 and 5 are produced by `figure_regeneration_2026_09_09/scripts/`
(see the README there), which reads `region_units.csv`, `region_cases.csv` and
`ltfu_glmm_summary.json`.

## Study population (episode level; Supplementary Figure S1)
```
270,492  TB notifications, São Paulo State, 2013-2024
 - 7,132  children (<15 years) and 308 missing age
 =263,052  adult notifications
 -24,484  re-treatment notifications (not incident)
 =238,568  incident notifications (new + recurrence)
 -28,565  incarcerated and 9,711 no fixed residence      excluded by design
 =200,292  with a standard residential address
 -   185  duplicate notification records
 =200,107  unique incident episodes
 - 7,946  not geocodable to a residential region
 =192,161  analytic set (episodes geocoded to a region)  = rows of region_cases.csv
```
Geocoding precision per episode: **T1** exact street and number; **T2** street; **T3** fuzzy street;
**T4** neighbourhood centroid; **T5** postal-code centroid. Sensitivity analysis: exclude T5.

## Rate basis
`scripts/rank_basis.py` is the single switch: `RANK=crude` (default, primary analysis),
`RANK=std` (indirect age-standardisation, sensitivity), `RANK=percap` (LTFU events per adult
population, supplementary). Every ranking script reads it; outputs carry the suffix `_std` or
`_percap`.

## Data handling
`geocoded_cohort.csv` and `region_cases.csv` are individual-level and are never committed.
`test/check_privacy.py` enforces this; `test/check_artifact_pins.py` verifies that the
persisted artifacts still match the counts above.
