# SP-TB-spatial-analyses

Geocoding pipeline and spatial analyses for tuberculosis cohort work in São Paulo, Brazil.


## Structure

```
.
├── config.py             # Master path configuration (edit BASE_PATH if data moves)
├── scripts/
│   ├── 01_geocode_*.py   # CEP → lat/lon geocoding pipeline
│   ├── 02_download_*.py  # IBGE shapefile / historical data downloads
│   ├── 02c_extract_mapbiomas.py
│   ├── 03_spatial_intersection.py
│   ├── 05_spatial_intersection.py
│   ├── 06_integrate_spatial_cohort.py
│   ├── 07_spatial_visualizations.py
│   ├── 08_download_2010_agsn.py   # 2010 AGSN subnormal agglomerate library
│   ├── 08b_scrape_cem.py
│   ├── 08c_download_biblioteca_zip.py
│   ├── 10_favela_incidence.py
│   ├── 11_spatial_income_intersection.py
│   └── 13_income_incidence_abandonment.py
└── .gitignore            # Blocks data/cache files
```

## Pipeline

### 1. Geocoding (CEP → coordinates)

Brazilian CEPs (postal codes) are resolved to lat/lon via layered caches and APIs.
- `01_geocode_sherlock.py` — main geocoder (Sherlock cluster variant)
- `01a_geocode_ceps.py` — forward geocoding
- `01b_geocode_reverse.py` — reverse lookups
- `01c_geocode_chunk.py`, `01d_geocode_fast.py`, `01e_geocode_async.py` — variants
- `04_merge_caches.py` — merge CEP caches into `cep_coords_MASTER.json`

Cache files produced (stored in Google Drive):
- `cep_coords_cache.json`
- `cep_coords_cache_reverse.json`
- `cep_coords_MASTER.json`

### 2. Reference data downloads

- `02_download_shapefiles.py` — IBGE census tract shapefiles
- `02b_download_historical_ibge.py` — historical IBGE boundaries
- `02c_extract_mapbiomas.py` — MapBiomas land use
- `08_download_2010_agsn.py` — 2010 subnormal agglomerate polygons
- `08b_scrape_cem.py` — CEM São Paulo data
- `08c_download_biblioteca_zip.py` — IBGE biblioteca archive

### 3. Spatial join and cohort integration

- `03_spatial_intersection.py` — point-in-polygon for census tracts
- `05_spatial_intersection.py` — alternate intersection pass
- `06_integrate_spatial_cohort.py` — attach spatial covariates to cohort
- `07_spatial_visualizations.py` — choropleth / point maps

### 4. Outcome-spatial analyses

- `10_favela_incidence.py` — TB incidence within favelas (AGSNs)
- `11_spatial_income_intersection.py` — income × spatial linkage
- `13_income_incidence_abandonment.py` — income-incidence-abandonment joint analysis

## Setup

```bash
# Requires Python 3.10+ with geopandas stack
pip install geopandas shapely fiona pyproj pandas numpy requests aiohttp
```

Edit `config.py` to point `BASE_PATH` at your local Google Drive mount if it
differs from the default.

## Manuscript figures (2026-09-09 regeneration)

`figure_regeneration_2026_09_09/` holds the corrected scripts for main-text figures 2, 3
and 5, the verification scripts, and a provenance record of the numeric corrections applied
in manuscript v13/v14 and appendix v12/v14. **Start with its `README.md`.**

Two defects in the earlier figure code are fixed there: panels 2d/3b/3c plotted the
age-standardised rate columns while the text describes crude rates, and panels 2a/2b/5a
ranked LTFU per capita rather than per evaluated episode. Do not reuse the older
`build_fig*.py` scripts (Google Drive, `New_analyses/scripts/`) — see `SUPERSEDED.md` there.

```
figure_regeneration_2026_09_09/
├── README.md              # provenance: what was wrong, what changed, what was verified
├── scripts/               # corrected build_fig2/3/5.py + fig_common.py
├── verification/          # re-runnable checks of every manuscript number
└── manuscript_edits/      # scripts that produced the tracked-change .docx versions
```

Note: the analysis-pipeline scripts numbered 100–120 that generate the region units and the
original figures live in the companion repo
https://github.com/evelepka/SP-TB-spatial-analyses and are not mirrored here.

## Related repos

- Analysis pipeline (scripts 100–120, region units, original figures): https://github.com/evelepka/SP-TB-spatial-analyses
- Outcomes analysis (ITT + causal g-methods): https://github.com/jasonandr/outcomes-after-tb-abandonment
