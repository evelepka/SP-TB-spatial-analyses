# SP TB × incarceration spatial analysis — session summary

May 2026. Working session summary covering: (a) feasibility of obtaining community-level incarceration data, (b) prison↔community circulation in SP TBweb, and (c) whether incarcerated TB cases come from disproportionately favela or low-income communities.

## 1. Original question

For modeling the role of prisons in community TB epidemics in São Paulo state, we want to know whether high-TB communities (favelas in particular) supply disproportionate shares of SP's incarcerated population, and whether individuals circulate between prison and the same communities. Two angles:

- **External data on community-level incarceration rates** — could TJSP court records be scraped to identify communities of origin of incarcerated people?
- **Within-cohort analysis** — does SP TBweb itself capture prison↔community transitions and community-of-origin information?

## 2. Feasibility of court-records scraping (TJSP)

See `docs/incarceration_data_feasibility.md` for the full assessment. Bottom line: TJSP e-SAJ is technically scrapable (multiple academic Python tools exist — `pyESAJ`, `jespimentel/esaj_2_grau`, LabCidade `portas`), but **defendant home addresses are not routinely published in TJSP decisions** because of LGPD + CNJ Resolução 121/2010 redaction rules. The Oliveira & Sperandio Nascimento 2024 paper (PLOS ONE) is about document similarity clustering, not address extraction. The realistic data path is SAP-SP intake records (via formal research convênio) and/or Defensoria Pública client records, not court scraping.

## 3. Cohort structure

| File | Path | What it is |
|---|---|---|
| `Final_table_cleaned.csv` | `Abandonment Paper/Data/` | 270,735 rows × 58 cols. Cleaned per-notification TBweb data. |
| `cohort_with_spatial.csv` | `SP-TB-spatial-analyses/Data/` | Same + favela flag + collapsed CEP per person. |
| `TBWeb_20250328_endereco.xlsx` | `WHO modelling Project/Data/` | The per-notification address export: `cep` (residence), `ceptrat` (treatment), `endereco`, `bairro`, `munResid`, `munNotif`. **Not in the Abandonment Paper data folder** — only in WHO modelling Project. |
| `outcomes-after-tb-abandonment/00_clean_sinan.py` | repo | Documents how `sinan_clean` is built as the resolved person-level ID (zero-padded + DOB+sex conflict resolution). |

`sinan_clean` IS the person-level ID (not the notification ID). 235,629 unique persons; 25,943 (11.0%) have ≥2 distinct notification dates.

## 4. Within- vs across-notification transitions

`address_type` in the cleaned cohort takes values `ENDERECO PADRAO` (community, 226k), `DETENTO` (prison, 31k), or `SEM RESIDENCIA FIXA` (homeless, 14k).

- **Within-notification mid-treatment transitions are NOT captured** in `address_type`. The `tx_seq` rows for one `(person, notification_date)` tuple carry a constant `address_type`. Mid-treatment release-while-on-therapy events would need to be recovered from other facility-transfer fields not in this export.
- **Across-notification transitions ARE captured**. Among the 25,943 multi-episode persons, consecutive (episode *n* → episode *n+1*) address-type pairs:

| from \ to | Community | Homeless | Prison | total |
|---|---:|---:|---:|---:|
| **Community** | 23,668 | 1,184 | **1,417** | 26,269 |
| **Homeless** | 672 | 3,018 | 186 | 3,876 |
| **Prison** | **1,430** | 226 | 3,267 | 4,923 |
| total | 25,770 | 4,428 | 4,870 | 35,068 |

Of people whose first observed episode was in prison and had a second episode, **29% (1,430 / 4,923) appear as community residents at the next episode**. Median time-gap for P→C transitions is 1,362 days (consistent with sentence length before release). See `docs/prison_community_transitions_tbweb.md` for full tables.

## 5. Community address recovery

The `cep` field in `cohort_with_spatial.csv` carries ONE CEP per person, joined from `analysis_ready_cohort.csv` via `sinan_clean`. So all 1,417 C→P and 1,430 P→C transition pairs have identical from-CEP and to-CEP — the join collapsed per-notification addresses to per-person addresses. The per-notification distinction existed upstream (proven by `tx_city` correctly differing per row) but was lost in the join.

The per-notification address source is `TBWeb_20250328_endereco.xlsx`. Linkage via `sinan_padded ↔ SINAN`: 235,522 / 235,612 (99.96%) match.

**For ever-incarcerated persons (n=27,608), recovery of a community CEP is severely limited:**

| Source | n | Validity |
|---|---:|---|
| Community-episode row (ENDERECO PADRAO) | 943 | ✓ real home CEP |
| Homeless-episode row (SEM RES) | 160 | ✓ last known residence |
| ~~DETENTO row's own `cep`~~ | ~~4,481~~ | **✗ this is the prison CEP, not home** |
| **Total truly usable** | **1,103** | (4.0% of 27,608) |

The DETENTO-row-`cep` exclusion is dispositive — three independent tests confirm it's the prison address:

1. **`cep == ceptrat` on 92.9%** of DETENTO rows where both are filled. `ceptrat` is the treatment location (the prison itself for incarcerated patients).
2. **Concentration**: 6,303 DETENTO rows resolve to only **442 unique CEPs** (top 10 = 59%); SP has ~176 prison units. Community CEPs in contrast span 64,670 unique values.
3. **`endereco` strings** on DETENTO rows literally read "CDP I PINHEIROS", "CDP BELEM II", "Rodovia Padre Manoel da Nóbrega KM 66" — prison names and access roads, not residential addresses.

The remaining **26,505 ever-incarcerated persons (96.0%) have no home CEP captured** in this dataset. Recovery would require an SES-SP / SAP-SP intake-record backfill.

## 6. Favela & income comparison

Using IBGE setor populations (V007 for 2010, v0001 for 2022) joined to favela polygons (AGSN 2010 vs Favelas e Comunidades Urbanas 2022) for the SP-general-population baseline.

### SP baselines

| Polygon definition | SP pop in favela |
|---|---:|
| 2010 AGSN (strict informal-settlement def) | **2.91%** |
| 2022 FCU (broader, includes urban communities) | **8.18%** |

### Stratified by sex, 2010 AGSN polygons

| Group | n with flag | % favela | OR vs B (crude) | OR vs S (crude) | Adj OR A vs B (age+year) |
|---|---:|---:|---:|---:|---:|
| **Males** | | | | | |
| A — ever-incarcerated TB, community CEP | 990 | 5.96% | 1.23 (0.94–1.60) | **2.12 (1.63–2.75)** | 1.16 (0.89–1.51, p=0.27) |
| B — non-incarcerated TB | 101,806 | 4.91% | — | **1.72 (1.68–1.77)** | — |
| S — SP general male pop | — | 2.91% | — | — | — |
| **Females** | | | | | |
| A | 32 | 3.12% (1 case) | 0.51 (0.07–3.75) | 1.08 (0.15–7.89) | 0.47 (0.06–3.58, p=0.46) |
| B | 54,306 | 5.93% | — | **2.10 (2.03–2.18)** | — |
| S | — | 2.91% | — | — | — |

### Stratified by sex, 2022 FCU polygons

| Stratum | A favela % | B favela % | S favela % | OR A vs B (crude) | OR B vs S (crude) |
|---|---:|---:|---:|---:|---:|
| Males | 7.07% | 5.76% | 8.18% | 1.24 (0.97–1.59) | **0.69 (0.67–0.71)** |
| Females | 3.12% | 6.91% | 8.18% | 0.43 (0.06–3.19) | **0.83 (0.81–0.86)** |
| Both sexes | 6.95% | 6.16% | 8.18% | 1.14 (0.89–1.45) | **0.74 (0.72–0.75)** |

### Adjusted income (V005 setor mean household income, log-linear regression, males)

Adjusted income ratio for ever_incarcerated vs non-incarcerated TB males (age + year adjusted): 0.977 (95% CI 0.945–1.010, p=0.17). Within males, no significant income difference.

## 7. Findings summary

1. **TB itself is a strong marker of favela residence.** In the 2010 AGSN definition, male TB OR vs SP general male pop = 1.72, female TB OR = 2.10. Both highly significant. Female TB is *more* concentrated in favelas than male TB despite far lower incarceration rates.

2. **Within male TB patients, ever-incarcerated and non-incarcerated come from essentially the same neighborhoods.** Adjusted OR ≈ 1.16 (NS) using AGSN 2010 polygons; ≈ 1.19 (NS) using 2022 FCU polygons. The crude all-sex effect (adjusted OR 1.52, p=0.056) was substantially driven by sex confounding — incarcerated TB is 97% male, non-incarcerated is 67% male, and male TB patients live in poorer neighborhoods than female TB patients in general.

3. **Polygon definition matters substantially for the SP baseline.** AGSN 2010 captures 2.91% of SP population; FCU 2022 captures 8.18%. TB cohorts look elevated relative to the AGSN definition (~1.7–2.1×) but de-concentrated relative to the FCU definition (~0.7–0.8×). The 2010 AGSN definition is the better discriminator of high-TB-risk informal settlements.

4. **The full-sample (n=27,608) municipality-of-origin map is dominated by prison locations** (Lavínia, Tremembé, Pacaembu, São Vicente, Franco da Rocha, etc.) because only 1,684 of the 27,608 have non-DETENTO source municipality. The municipality map answers "where are SP's prisons" more than "where are SP's incarcerated people from."

5. **Power is the binding constraint** for any A-vs-B comparison and the entire female-stratified analysis. With only 32 ever-incarcerated TB females with community CEP (1 favela case) and 990 males (59 favela cases), the within-TB incarceration-effect estimates have wide confidence intervals. The hypothesis cannot be tested precisely without obtaining home CEPs for the other 26,505 ever-incarcerated persons.

## 8. Limitations

- **Multi-episode selection bias.** The 1,103 ever-incarcerated persons with community CEP are persons who had both a prison episode *and* a community/homeless TB episode in the 2013–2024 window. They're not necessarily representative of the broader incarcerated population. Persons whose only TB episode was while incarcerated (the other 26,505) have unknown community origin.
- **Prior episodes outside the window are invisible.** Persons coded `Recidiva` or `Retr Aband` at their first observed notification had earlier episodes (likely pre-2013) that aren't in the export.
- **CEP geocoding success rate is ~75%.** Some unmatched CEPs may be systematically in less-formal areas, which could bias all analyses if non-randomly missing.
- **The DETENTO `cep` field cannot be re-purposed.** Verified to be the prison facility CEP via three independent tests.
- **SP population sums via V007 (2010) are ~3× too high** due to a Brazilian thousand-separator parsing artifact; the favela *rate* (2.91%) is invariant to this multiplicative scaling and is consistent with published IBGE figures.

## 9. Recommended next steps

1. **Data acquisition.** The single highest-value action is a formal data request to SES-SP / SAP-SP to backfill `cep` for the ~26,500 DETENTO rows that lack it. SAP holds intake-declared residence for every custódia. With backfilled home CEPs, the within-TB A-vs-B comparison would have ~4× power and any modest effect should become detectable.
2. **TJSP scrape proof-of-concept.** Independent of (1), the TJSP scrape pipeline (e-SAJ → NER for *local do crime* + charge class + sentencing) has standalone publishable value as the first community-level criminal-justice map of SP using NLP, even though it doesn't recover home addresses.
3. **DPE-SP partnership.** Defensoria Pública holds defendant residence for the population it represents (which heavily overlaps the disadvantaged communities of interest).
4. **Municipal-level analysis on the full 27,608.** Despite the prison-location bias, the prison-municipality distribution is useful as a denominator and to characterize which SP prisons concentrate TB cases. Pair with SAP's published unit list for prison CEPs.
5. **Stratification by income tier, age, year of incarceration** to look for heterogeneity even within the small samples.

## File index (scripts + outputs)

All in `scratch/`. Scripts are kept as-is for traceability; numerical results were reproduced and refined across iterations (later versions supersede earlier).

| Script | Purpose |
|---|---|
| `tb_person_trajectories.py` | Build per-person episode timelines, classify transitions |
| `link_endereco_to_transitions.py` | Join WHO modelling Project endereco file to transition pairs |
| `validate_detento_cep_meaning.py` | Test what DETENTO row's `cep` actually represents |
| `community_cep_v3.py` | **Current.** Build community-CEP lookup for ever-incarcerated persons |
| `favela_income_overlay.py` | First-pass favela/income comparison |
| `favela_income_with_sp_baseline.py` | Add SP CEP baseline |
| `incarceration_geo_v2.py` | **Current.** Population-weighted SP baseline + adjusted regressions + municipality map |
| `males_only_favela_comparison.py` | Sex-stratified analysis (males) with three-way OR |
| `sex_strat_favela_2010_and_2022.py` | **Current.** Full sex × polygon-vintage analysis |

| Output (parquet, gitignored) | Contents |
|---|---|
| `community_cep_for_incarcerated.parquet` | 5,584 ever-incarcerated × CEP rows (1,103 valid, 4,481 invalid DETENTO-source) |
| `incarcerated_community_ceps_with_geo.parquet` | 1,103 valid × CEP × favela/income |
| `incarcerated_origin_by_municipality.parquet` | Origin municipality counts × population × rate |
| `person_trajectories.parquet` | Multi-episode trajectories for 25,943 persons |
| `transition_pairs_with_real_addresses.parquet` | 3,025 prison↔community pair rows with cep_resid and ceptrat per side |
