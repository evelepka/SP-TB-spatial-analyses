# Project context — GSP vulnerability typology branch

> **⚠️ HISTORICAL (frozen 2026-06-06).** This documents the GSP-only phase (51,016 cases
> 2020-2024, scripts 20-49). The current work is the STATE-WIDE episode-level manuscript
> (192,161 episodes 2013-2024, scripts 100-120) — current state lives in
> `manuscript/PIPELINE.md`, decisions in `docs/decisions/`. Read this file
> for the history of the CNEFE pipeline and the vulnerability typology, not for next steps.

This file documents the **state, decisions, and next steps** for the GSP TB vulnerability typology branch of the SP-TB-spatial-analyses repository. It complements the main `README.md` (geocoding pipeline, Jason Andrews) by adding the analytical work led by Evelyn Lepka (Stanford) for the WHO TB Screening Investment Case.

**Branch:** `gsp-vulnerability-typology`
**Maintainer:** Evelyn Lepka de Lima (evelepka)
**Context:** WHO TB Screening Investment Case — Brazil. Designing geographic targets for active case-finding (ACF) starting in Greater São Paulo (GSP), then Baixada Santista.

---

## 1. Scope of this branch

The branch adds an **alternative geocoding pipeline (CNEFE-based)** and a downstream **vulnerability/concentration analysis** that:

1. Replaces the CEP-based geocoding (in master, scripts `01_*`) with a CNEFE-based pipeline that achieves **90.8 % matching rate** vs the systematic CEP bias of TBweb (~91 % bairro mismatch documented).
2. Identifies **empirical hotspot sectors** (top 5 % of GSP population by observed TB rate).
3. Builds an **a priori composite vulnerability index** combining income + density + FCU, and benchmarks it against the empirical hotspots.
4. Proposes a **TB vulnerability typology (5 archetypes)** as a portable framework for the WHO Investment Case, replacing nominal hotspot lists with replicable categories.

Output documents under `docs/`:

- `README_pipeline_TB_vulnerabilidade.md` — full pipeline documentation.
- `GSP_TB_concentracao_e_estrategias.md` — strategy discussion document for advisor (English).

---

## 2. Data sources

| Source | Location | Notes |
|---|---|---|
| TBweb cohort (51,016 cases 2020-2024) | Drive: `WHO modelling Project/SP-TB-spatial-analyses/Data/` | Sensitive — never commit. Comunidade entry, Novo+Recidiva, Pulmonar+Mista. |
| IBGE Censo 2022 — Agregados básicos | Drive: `SP_Agregados_2022/` | v0001 (pop), v0005 (mor/dom). |
| IBGE Censo 2022 — Renda do responsável | Drive: `IBGE_2022_extended/renda_responsavel.zip` | V06004 (mean monthly income). |
| IBGE 2022 setor shapefile | Drive: `SP_setores_2022/SP_setores_CD2022.shp` | CD_MUN, NM_BAIRRO, NM_FCU, AREA_KM2, NM_CONCURB. |
| CNEFE 2022 (Sept 2024 release) | Drive: `IBGE_2022_extended/CNEFE_GSP/` (37 zip files, ~324 MB) | Canonical residential address registry. |
| Jason's incidence data | Drive: `Abandonment Outcomes/.../municipality_incidence_rates.csv` | São Vicente rate (577/100k) — under verification; suspected denominator issue with prison cases. |

**GSP definition**: `NM_CONCURB == "São Paulo/SP"` in the IBGE setor shapefile → 37 municipalities.

---

## 3. Scripts (this branch)

Run in numerical order. All scripts use hardcoded Drive paths today (refactor to `config.py` is on the todo).

| Script | Purpose | Output |
|---|---|---|
| `20_download_cnefe_gsp.py` | Downloads CNEFE for 37 GSP municipalities | `CNEFE_GSP/` (zips) + `indices/idx_{CD_MUN}.csv` |
| `21_cnefe_match_cohort.py` | Builds (street, number) → (bairro, setor, lat, lon) index per município; matches cohort | `cohort_with_cnefe.csv` (51,016 rows) |
| `22_hotspots_analysis.py` | Identifies top 5 % pop by TB rate; characterizes hotspots vs rest | `hotspots_top5pct_setores.csv`, `bairros_cnefe_ranking.csv` |
| `23_vulnerability_index.py` | Builds composite z-score index; ranks 43,972 sectors | `setores_priorizados_GSP.csv` |
| `24_prevalence_concentration.py` | Quantifies % cases in FCU, by index quantile, hotspot overlap | console tables only |
| `25_hotspot_anatomy.py` | Aggregates hotspots by bairro and FCU; case distribution | `hotspots_por_bairro.csv`, `casos_por_FCU.csv`, `casos_por_bairro_GSP.csv` |
| `26_maps_gsp_overview.py` | 2×2 panel PNG + interactive Folium HTML | `mapas_GSP/mapa_GSP_panel.png`, `mapa_GSP_interativo.html` |
| `27_maps_capital_zoom.py` | Zoom on SP capital: vulnerability × hotspots × rate | `mapas_GSP/mapa_capital_vuln_hotspots.png` |
| `utils/md_to_html_*.py` | Convert markdown docs to styled HTML for PDF print | — |

---

## 4. Aggregated outputs (in repo)

Committed under `outputs/aggregates/` — small CSVs aggregated to neighborhood/FCU level (no individual data):

- `hotspots_por_bairro.csv` — 121 neighborhoods × {N hotspot sectors, pop, cases, rate}.
- `casos_por_FCU.csv` — 2,427 FCUs × {pop, cases, rate}.
- `casos_por_bairro_GSP.csv` — 446 complete GSP neighborhoods.
- `bairros_cnefe_ranking.csv` — CNEFE-derived neighborhood ranking by case count.

Larger or sensitive intermediate files (`cohort_with_cnefe.csv`, `setores_priorizados_GSP.csv`, `hotspots_top5pct_setores.csv`) stay in Drive only.

---

## 5. Key decisions to date

| Decision | When | Rationale |
|---|---|---|
| Pivot from CEP geocoding to CNEFE | After ViaCEP throttling + 91.5 % bairro mismatch | CNEFE 2022 (Sept 2024 IBGE release) is the canonical residential address-to-sector mapping. |
| Use only residential sectors (CD_TIPO 0/1) with pop ≥ 100 | At analysis stage | Excludes non-residential and very small sectors that produce spurious rates. |
| Hotspot definition = top 5 % pop by observed rate, accumulated | Hotspot identification | Operationally tractable population denominator. |
| Composite index = z(-log income) + z(log density) + z(FCU) | Index construction | Three independent dimensions of urban vulnerability from IBGE 2022. |
| Move toward a typology of 5 archetypes (vs nominal hotspot list) | Latest discussion | (a) Urban mobility makes 141-m sectors finer than the true epi unit; (b) WHO IC needs nationally replicable categories. See `docs/GSP_TB_concentracao_e_estrategias.md`. |

---

## 6. Headline empirical findings (GSP)

- **GSP average rate**: 42.6 / 100k py (2020–2024).
- **FCU (slums)** concentrate **14.3 % of pop and 19.0 % of cases** (RR 1.40×). Slum-only strategy would miss 81 % of cases.
- **Empirical hotspots (top 5 % pop)**: 2,501 sectors, 1.03 M people, **29.0 % of cases**, rate 247 / 100k py (RR **7.75×**).
- **Composite index efficiency low**: top 5 % pop by index captures only 7.3 % of cases (RR 1.49×). Index–hotspot overlap on capital = 9.2 %.
- **Hotspot anatomy**: 2,501 sectors spread across **121 neighborhoods**; ABCD belt + Guarulhos + Osasco dominate (Pimentas, Cumbíca, Montanhão, Eldorado, Munhoz Jr., Padroeira).
- **FCU dispersion**: 8,305 FCU cases distributed across 2,427 distinct favelas; Paraisópolis (280) + Heliópolis (147) = 1.0 % of total GSP cases.
- **Hotspot median sector size**: 382 inhabitants, 0.02 km² (~141 m × 141 m), 4 cases in 5 years.

---

## 7. Open questions for advisor

The strategy document (`docs/GSP_TB_concentracao_e_estrategias.md` § 8) lists 16 discussion points organized in 5 themes:

1. **Unit of analysis** — sector vs neighborhood vs UBS catchment.
2. **Prioritization criterion** — a priori index vs empirical hotspots vs hybrid.
3. **Missing variables in the index** — HIV, drugs, homelessness, prison contacts, prior TB.
4. **Megafavelas** — symbolic value vs quantitative weight.
5. **ABCD axis** — pilot priority outside the capital.
6. **Archetype typology** — a priori vs clustering vs hybrid; how many archetypes; cover only hotspots or all GSP.
7. **External validity** — what to expect in Baixada Santista; São Vicente rate verification.

---

## 8. Next steps

- [ ] Receive advisor feedback on the typology approach (5 archetypes; a priori vs clustering vs hybrid).
- [ ] Implement chosen archetype derivation method on the 2,501 GSP hotspots.
- [ ] Validate by replicating the pipeline on Baixada Santista (9 RMBS municipalities: Santos, Cubatão, Guarujá, Praia Grande, São Vicente, Bertioga, Itanhaém, Mongaguá, Peruíbe).
- [ ] Verify São Vicente incidence (currently cited as 577/100k; suspected denominator issue).
- [ ] Refactor scripts to import paths from `config.py` (currently hardcoded).
- [ ] Open PR to advisor (`master` ← `gsp-vulnerability-typology`).

---

## 9. How to continue this work

1. Clone the repo, checkout the branch:
   ```bash
   git clone git@github.com:jasonandr/SP-TB-spatial-analyses.git
   cd SP-TB-spatial-analyses
   git checkout gsp-vulnerability-typology
   ```
2. Read `docs/GSP_TB_concentracao_e_estrategias.md` end-to-end — it contains the full analytical narrative and the open questions.
3. Ensure Google Drive Desktop is synced; data folder paths follow:
   `~/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data/`
4. Run scripts in order `20_` → `27_`. They are self-contained Python (no virtual env required if `pandas`, `geopandas`, `folium`, `mapclassify`, `markdown` are installed).
5. Aggregated outputs are reproducible from scripts `22_`, `25_` once `21_cnefe_match_cohort.py` has been run.
