# SP-TB-spatial-analyses

Analysis code for a population-based study of the geographic concentration of tuberculosis
notifications, mortality and loss to follow-up (LTFU) in São Paulo State, Brazil, 2013–2024.

The study geocodes every incident adult TB notification in the state to a residential
address (IBGE CNEFE address register), aggregates cases into ~7,300 regionalisation units of
roughly 5,000 adults each, and measures how notifications, TB deaths and LTFU concentrate in
space, how stable that concentration is over time, and how it relates to a place-vulnerability
index built from census indicators.

## Data availability and privacy

**This repository contains code only. No data are included.**

- Individual-level notification data (state TB register) are held by the São Paulo State
  Department of Health and are available from it subject to ethical approval. They are never
  committed here: `test/check_privacy.py` fails if any individual-level artifact is tracked, and
  `.gitignore` blocks all data file types.
- Census 2022 aggregates, sector boundaries and the CNEFE address register are public and are
  downloaded from IBGE by the scripts (`scripts/20_*`, `28_*`, `40_*`).
- Intermediate and aggregated outputs (region-level rates, figures, tables) are written to a
  local data folder, not to the repository.

## Path configuration

Scripts refer to the project data folder with the placeholder `/DATA_ROOT`. Before running,
replace it with the location of your data folder (for example with
`sed -i '' 's#/DATA_ROOT#/path/to/data#' scripts/*.py`). Expensive intermediates are staged in
`/tmp` and restored from `Data/analytic/` by `scripts/00_restore_tmp.py`. The figure scripts in
`figure_regeneration_2026_09_09/` read the `SPTB_AN` (analytic folder) and `SPTB_OUT` (output
folder) environment variables instead.

## Repository layout

| path | content |
|---|---|
| `scripts/00_restore_tmp.py` | stages the persisted analytic artifacts into `/tmp` |
| `scripts/20–41` | CNEFE download and address matching (Greater São Paulo, Baixada Santista, rest of the state) |
| `scripts/64`, `89` | place-vulnerability composite (income, illiteracy, crowding, favela) |
| `scripts/78` | indirect age-standardisation engine (sensitivity analysis) |
| `scripts/83` | regionalisation of census sectors into ~5,000-adult units |
| `scripts/108`, `109` | geocoded cohort: spatial overlay and CNEFE-internal postal-code fallback |
| `scripts/100_region_units.py` | region-level dataset: cases, population, crude and age-standardised rates, LTFU, vulnerability, hotspot flags |
| `scripts/101–106`, `122–124` | main-text figures 1–5 |
| `scripts/111–121`, `125`, `128–131` | Table 1, GLMM of LTFU, supplementary figures and tables, sensitivity analyses |
| `scripts/107`, `110`, `113`, `116`, `118` | manuscript report, methods/results/supplement documents |
| `scripts/rank_basis.py` | selects the rate basis for every ranking script (`RANK=crude`, the primary analysis; `RANK=std` age-standardised; `RANK=percap` LTFU per capita) |
| `figure_regeneration_2026_09_09/` | final versions of Figures 2, 3 and 5 as submitted, with re-runnable numeric verification (see its `README.md`) |
| `manuscript/PIPELINE.md` | reproduction order, full-rebuild table and STROBE flow |
| `manuscript/methods.md` | methods text as implemented |
| `docs/decisions/` | architecture decision records (unit of analysis, geocoding, regionalisation, vulnerability index, LTFU definition, crude rates as primary) |
| `test/` | fast checks: compilation, `/tmp` dependency closure, artifact pins, privacy |

## Reproducing the analysis

```bash
pip install -r requirements.txt          # Python 3.10+
python3 scripts/00_restore_tmp.py        # Data/analytic/* -> /tmp
python3 scripts/100_region_units.py      # region-level dataset
python3 scripts/101_fig1_concentration_region.py   # then 102 ... 106, 122, 123, 124 for the figures
RANK=std python3 scripts/100_region_units.py       # age-standardised sensitivity analysis
bash test/run_fast.sh                    # checks
```

The full rebuild from raw notifications (geocoding, regionalisation, vulnerability index) is
documented step by step in `manuscript/PIPELINE.md`.

## Software

Python 3.10+ with pandas, numpy, geopandas, shapely, scipy, statsmodels, matplotlib, pygam,
libpysal/esda/spreg (spatial autocorrelation), rapidfuzz (address matching) and python-docx
(document assembly). Exact versions are in `requirements.txt`.

## License

MIT (see `LICENSE`).
