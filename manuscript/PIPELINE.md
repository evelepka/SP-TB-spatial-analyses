# Manuscript pipeline — SP TB spatial (regionalisation)

Reproduction order for the manuscript analysis. **`/tmp` is cleared between sessions**; the
expensive/authoritative intermediates are persisted in Drive `Data/analytic/`.

## Fast start (reuse persisted base)
```
python3 scripts/00_restore_tmp.py      # Data/analytic/* -> /tmp   (skips the costly steps below)
python3 scripts/100_region_units.py    # rebuild region_units.csv from the authoritative geocoded cohort
# then figures: 101 102 103 104 105 106  ; report: 107
```

## Full rebuild from raw (only if geocoding must be redone)
| step | script | output | note |
|------|--------|--------|------|
| geocode GSP | `21_cnefe_match_cohort.py` | `cohort_with_cnefe.csv` | CNEFE match; ENDERECO PADRAO only |
| geocode Baixada | `29b_cnefe_match_baixada_improved.py` | `cohort_baixada_with_cnefe_v2.csv` | + Novo/Recidiva filter, favela-hint |
| geocode interior | `41_cnefe_match_sp_outros.py` | `cohort_sp_outros_with_cnefe.csv` | rest of state |
| regionalise | `83_regionalize_state.py` | `regions_sectors.csv` | sectors -> ~5,000-adult regions, favela separate |
| **geocoded base P1** | **`108_build_geocoded_cohort.py`** | `geocoded_cohort.csv` | spatial overlay of lat/lon on official mesh (fixes "P" codes) |
| **geocoded base P2** | **`109_cep_fallback.py`** | `geocoded_cohort.csv` (+T5) | CNEFE-internal CEP fallback for no-match |
| vulnerability | `64_vulnerability_composite.py` → `89_build_vuln_final.py` | `vuln_sectors.csv`, `vuln_final.csv` | 4-domain composite (income+illit+crowd+favela) |
| **region dataset** | **`100_region_units.py`** | `region_units.csv` | per-region crude + age-std outcomes + vuln + hotspot flags on the `RANK` basis (`scripts/rank_basis.py`, crude default — ADR-0006) |
| figures | `101`–`106` | `figN_*.png` → FIGDIR | manuscript figures 1–5 |
| composites | `122_manuscript_composites.py`, `123_fig1_choropleth.py`, `124_fig3_composite.py` | `fig2/fig5_composite.png`, `fig1_choropleth.png`, `fig3_composite.png` | Figs 1/2/3/5 as in the docx; 124 header documents the Fig 3 inset provenance |
| metro flag | `130_region_metro.py` | `region_metro.csv` | metropolitan (GSP+Baixada) majority flag per region; used by 129 |
| supp. S4 | `131_figS4_spatial_structure.py` | `figS4_spatial_structure.png` + values json | Moran's I / R² / spatial-lag ρ on the RANK basis |
| supp. S5–S7 | `129_figS5_S7_deprivation_variants.py` | `figS5..S7*.png` + values json | deprivation-quintile variants (LTFU, composite index, metro-restricted) |
| sensitivity | same scripts with `RANK=std` (suffix `_std`) / `RANK=percap` | `*_std.png`, `fig2_composite_percap.png` | supplement S8/S9 (116) |
| report | `107_build_manuscript_report.py` | `SP_TB_Manuscript_Figures.html` → Reports | |

## Study population (STROBE — episode-level, matches Fig S1 in `114_figS_strobe.py`)
```
270,492  TB notifications, SP, 2013-2024
 - 7,132  children (<15) and 308 missing age
 =263,052  adult notifications
 -24,484  re-treatment notifications (not incident)
 =238,568  incident notifications (new + recurrence)
 -28,565  incarcerated and 9,711 no fixed residence      exclusion by design
 =200,292  with standard residential address
 -   185  duplicate notification records
 =200,107  unique incident episodes
 - 7,946  not geocodable to a residential region
 =192,161  analytic set (episodes geocoded to a region)  = rows of region_cases.csv
```
<!-- The previous block here was the PERSON-level flow (228,343 -> 176,127), stale since the
     episode-level rebuild (commits 5397103/cb39cb3). Replaced 2026-08-10 with the flow the
     committed STROBE figure actually draws. test/run_fast.sh now pins the 192,161 against
     region_cases.csv so the figure, this doc and the artifact cannot drift apart silently. -->
Geocoding precision flag per case: **T1** exact street+number · **T2** street · **T3** fuzzy street ·
**T4** neighbourhood centroid · **T5** postal-code (CEP) centroid. Sensitivity = re-run excluding T5.

Persisted artifacts live in `Data/analytic/` (NOT in Git — individual data). `geocoded_cohort.csv`
(sinan_clean, CD_SETOR, tier) is individual-level and must stay out of the repo.
