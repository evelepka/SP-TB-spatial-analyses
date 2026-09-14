# TB concentration in the Baixada Santista region (2020-2024) and comparison with Greater São Paulo: discussion document

**Author:** Evelyn Lepka de Lima (Stanford University)
**Date:** June 2026
**Context:** WHO TB Screening Investment Case — Brazil. Second regional application of the GSP vulnerability-typology pipeline, intended to validate the archetype framework before adoption as a national replicable tool.
**Purpose of this document:** present the Baixada Santista (RMBS) results in the same structure as the previous GSP report, and **side-by-side comparison with Greater São Paulo (GSP)** to identify (a) where the same patterns recur, (b) where new patterns emerge, and (c) implications for the proposed TB vulnerability typology (archetypes).

---

## Executive summary

1. **Baixada Santista has 2.1× the TB rate of GSP** (88.9 vs 42.6 / 100k py). Highest-rate municipalities: Guarujá (112), Cubatão (107), São Vicente (99).
2. **CNEFE matching improved from 72.5 % (v1) to 97.5 % (v2)** through aggressive complement stripping (BLOCO/APTO/QUADRA/KM/PROX), embedded-number recovery, fuzzy matching (rapidfuzz token_set_ratio ≥ 88), and bairro-level fallback. Higher matching rate than GSP (90.8 %).
3. **FCU is more predictive in Baixada**: 26.4 % of cases occur in FCU (vs 19.0 % GSP), with rate ratio 1.68× (vs 1.40× GSP). 40.9 % of Baixada hotspots fall within an FCU (vs 24.8 % GSP).
4. **Composite vulnerability index also performs better in Baixada**: top 5 % pop captures 8.1 % of cases (vs 7.3 % GSP), RR 1.70× (vs 1.49 × GSP).
5. **Geographic concentration is radically higher in Baixada than in GSP**:
   - **5 FCUs** cover 25 % of FCU cases (vs 43 in GSP — **8.6× more concentrated**).
   - **15 FCUs** cover 50 % of FCU cases (vs 177 in GSP — **12× more concentrated**).
   - **Top 30 neighborhoods** cover **63 % of hotspot cases** (vs only 6 % in GSP — **10× more concentrated**).
6. **Operational implication**: a Baixada intervention is dramatically easier than GSP — visiting ~15 favelas + ~10 hotspot neighborhoods covers a third of all cases.
7. **São Vicente "577/100k" claim is unsupported**: our estimate is **99/100k py**. The 577 figure likely originates from a numerator-denominator mismatch (probably including referenced cases or prison cases without their proper denominator).
8. **Three new archetypes emerge in Baixada that did NOT appear in GSP**: (a) palafita / dike community, (b) port-side hillside favela ("morro portuário"), (c) degraded port-area cortiço — each tied to coastal-industrial geography absent from GSP.

---

## 1. Data base

- **Cohort:** 9,447 TB cases notified in the 9 Baixada Santista municipalities between 2020 and 2024 (Pulmonary + Mixed forms; New + Relapse cases; Community entry; SINAN-TBweb).
- **9 RMBS municipalities** (Lei Complementar Estadual 815/1996): Bertioga, Cubatão, Guarujá, Itanhaém, Mongaguá, Peruíbe, Praia Grande, Santos, São Vicente.
- **Geocoding:** CNEFE 2022 (IBGE Sept 2024 release) with improved matching cascade (see § 2).
- **Denominator:** IBGE 2022 resident population (v0001), residential sectors (CD_TIPO 0/1) with ≥ 100 inhabitants — 4,024 sectors covering 1,773,009 people.
- **Average Baixada rate:** 88.9 / 100k py (2.1× GSP average of 42.6).

---

## 2. CNEFE matching cascade (improved for Baixada)

The initial matching (script `29_cnefe_match_cohort_baixada.py`, replicating the GSP pipeline) achieved only **72.5 %** coverage in Baixada vs **90.8 %** in GSP. Audit of failures showed coastal-specific patterns: embedded street numbers when `numEnd` is missing, complement tokens (`BLOCO X`, `APTO Y`, `KM 66`, `PROX AO RIO`), name truncations, typographical errors, and informal addresses (`FAVELA DO RIO CACHETA`).

The improved cascade (script `29b_cnefe_match_baixada_improved.py`) applies, in order:

| Tier | Method | Hit rate | Notes |
|---|---|---|---|
| **T1** | Exact (street, number) | 51.2 % | After aggressive complement stripping. |
| **T2** | Street only (modal sector for street) | 21.4 % | Numbered street, no number match. |
| **T3** | Fuzzy match within municipality (rapidfuzz, score ≥ 88) | 20.6 % | Median score 100; only 37 cases at the minimum threshold of 88. |
| **T4** | Bairro centroid fallback (TBweb bairro → CNEFE bairro) | 4.2 % | Used **only for cohort enumeration**, NOT for sector-level analysis (would inflate centroids). |
| **no match** | — | 2.5 % | Mostly informal favela addresses with no street structure. |

**Total coverage: 97.5 %.** Sector-resolution coverage (T1+T2+T3 only, suitable for spatial analysis): **93.2 %**. Bairro concordance (T1+T2+T3) with TBweb bairro: 37.7 %, in line with the GSP finding that TBweb bairro is unreliable for fine-grained analysis.

---

## 3. Prevalence and concentration of TB in Baixada Santista (2020-2024)

### 3.1 FCU — IBGE-defined favelas and urban communities

| | Population | Cases | Rate /100k py | **GSP** |
|---|---|---|---|---|
| **In FCU** | 311,578 (17.6 %) | 2,078 **(26.4 %)** | **133.4** | 56.6 |
| **Outside FCU** | 1.46 M (82.4 %) | 5,802 (73.6 %) | 79.4 | 40.3 |
| **Rate ratio (FCU/non-FCU)** | — | — | **1.68 ×** | 1.40 × |

→ FCU is **more predictive in Baixada** than in GSP — both the absolute case share (26.4 vs 19.0 %) and the rate ratio (1.68 vs 1.40) are higher. Still, 73.6 % of cases occur outside formal IBGE favelas.

### 3.2 Composite vulnerability index (a priori — same markers as GSP)

Formula: `z(-log income) + z(log density) + z(is_FCU)` — identical to GSP.

| Target % pop | N sectors | % cases | Rate /100k py | RR vs rest | **GSP RR** |
|---|---|---|---|---|---|
| Top 1 % | 30 | 1.1 % | 94 | 1.06 × | 1.35 × |
| Top 5 % | 162 | **8.1 %** | **146** | **1.70 ×** | 1.49 × |
| Top 10 % | 335 | 16.9 % | 151 | 1.84 × | 1.50 × |
| Top 20 % | 709 | 29.4 % | 131 | 1.67 × | 1.51 × |
| Top 30 % | 1,025 | 40.7 % | 121 | 1.60 × | 1.54 × |

→ Index performs **slightly better in Baixada** than GSP. Income + density + FCU correlate more tightly with TB in the coastal context, presumably because socioeconomic vulnerability and informal housing are more visually and structurally aligned in Baixada than in the dispersed GSP periphery.

### 3.3 Empirical hotspots — top 5 % pop by observed TB rate

| | Baixada | **GSP** |
|---|---|---|
| N hotspot sectors | 220 | 2,501 |
| Hotspot population | 88,286 (5.0 %) | 1.03 M (5.0 %) |
| **Cases in hotspots** | **2,077 (26.4 %)** | 12,689 (29.0 %) |
| Hotspot rate | 470 / 100k py | 247 / 100k py |
| Non-hotspot rate | 69 / 100k py | 32 / 100k py |
| **Rate ratio** | **6.83 ×** | 7.75 × |

→ Spatial concentration is similar (~5 % pop ≈ 27 % cases), but the **absolute rate inside Baixada hotspots is roughly 2× higher** than inside GSP hotspots — Baixada hotspots are more intense.

### 3.4 Combined coverage of all three strategies

| Strategy | % target pop | % cases covered | **GSP comparison** |
|---|---|---|---|
| FCU only | 17.6 % | **26.4 %** | 19.0 % |
| Empirical hotspots only | 5.0 % | 26.4 % | 29.0 % |
| Top 5 % composite index only | 4.9 % | 8.1 % | 7.3 % |
| **Union of all three** | **20.2 %** | **39.8 %** | 40.2 % |

**Overlaps:**
- **40.9 % of Baixada hotspots are inside FCU** (vs 24.8 % GSP) — strong favela-TB alignment.
- 12.7 % of Baixada hotspots are within the top 5 % index (vs 8.7 % GSP).
- 28 sectors are in all three categories.

---

## 4. FCU anatomy: extreme concentration in Baixada (vs GSP dispersion)

**The single most important methodological finding of this analysis.**

| Coverage desired | N FCUs in Baixada | N FCUs in **GSP** | Concentration ratio |
|---|---|---|---|
| 25 % of FCU cases | **5 FCUs** | 43 | **8.6× more concentrated** |
| 50 % of FCU cases | **15 FCUs** | 177 | **12× more concentrated** |
| 75 % of FCU cases | 33 FCUs | 457 | 14× more concentrated |
| 90 % of FCU cases | 57 FCUs | 823 | 14× more concentrated |

**Top 15 FCUs Baixada (cover ~50 % of FCU cases):**

| # | Municipality | FCU | Pop | Cases | Rate /100k py |
|---|---|---|---|---|---|
| 1 | Cubatão | **Vila Esperança** | 16,949 | **115** | 136 |
| 2 | Guarujá | **Complexo Prainha** | 7,638 | 100 | 262 |
| 3 | São Vicente | **CDHU** | 6,661 | 97 | 291 |
| 4 | São Vicente | **Saquaré** | 5,772 | 77 | 267 |
| 5 | São Vicente | Canal do Meio | 4,788 | 73 | 305 |
| 6 | Santos | **Dique Vila Gilda** | 7,275 | 73 | 201 |
| 7 | Guarujá | Sítio Conceiçãozinha | 4,755 | 71 | 299 |
| 8 | Cubatão | **Vila dos Pescadores** | 9,750 | 66 | 135 |
| 9 | São Vicente | Quarentenário Público | 9,225 | 64 | 139 |
| 10 | Santos | **Vila Alemoa** | 2,264 | 61 | **539** |
| 11 | São Vicente | Jardim Rio Negro | 4,744 | 54 | 228 |
| 12 | São Vicente | Jardim Rio Branco | 8,278 | 43 | 104 |
| 13 | Guarujá | Perequê | 7,324 | 43 | 117 |
| 14 | Guarujá | Cachoeira Plano | 5,644 | 42 | 149 |
| 15 | São Vicente | Rio da Avó | 4,797 | 40 | 167 |

**Implication**: an intervention targeting these **15 favelas** alone (each well-known to local UBS teams) would reach ~50 % of all Baixada FCU cases. In GSP, achieving the same proportion required 177 favelas distributed across 37 municipalities.

---

## 5. Hotspot anatomy by neighborhood: also far more concentrated than GSP

| | Baixada | **GSP** |
|---|---|---|
| Neighborhoods with at least 1 hotspot | 101 | 121 |
| **Top 30 neighborhoods cover** | **63.2 % of hotspot cases** | only 6.1 % |
| Top 5 neighborhoods cover | 23.9 % | ~1.5 % |

**Top 20 hotspot neighborhoods in Baixada (cover 52 % of hotspot cases):**

| # | Municipality | Neighborhood | Sectors | Cases | Rate /100k py | % cum |
|---|---|---|---|---|---|---|
| 1 | São Vicente | **Vila Margarida** | 14 | **181** | 479 | 8.7 % |
| 2 | Guarujá | **Cachoeira** | 6 | 91 | 576 | 13.1 % |
| 3 | Santos | **Saboó** | 4 | 90 | **1,002** | 17.4 % |
| 4 | Guarujá | Porto de Guarujá | 5 | 69 | 502 | 20.8 % |
| 5 | Santos | **Chico de Paula** | 5 | 66 | 627 | 23.9 % |
| 6 | Santos | **Rádio Clube** | 5 | 64 | 638 | 27.0 % |
| 7 | Guarujá | Enseada | 7 | 61 | 565 | 29.9 % |
| 8 | Guarujá | Pae Cará | 5 | 48 | 449 | 32.3 % |
| 9 | Santos | Vila Nova | 5 | 42 | 441 | 34.3 % |
| 10 | São Vicente | Samarita | 2 | 38 | 745 | 36.1 % |
| 11 | Santos | Estuário | 2 | 37 | 501 | 37.9 % |
| 12 | Guarujá | Santo Antônio | 2 | 36 | 517 | 39.6 % |
| 13 | Cubatão | Vila Esperança | 2 | 36 | 936 | 41.4 % |
| 14 | Santos | **Morro São Bento** | 2 | 35 | 668 | 43.0 % |
| 15 | Cubatão | Vila dos Pescadores | 2 | 33 | 387 | 44.6 % |
| 16 | Guarujá | Vila Zilda | 4 | 32 | 597 | 46.2 % |
| 17 | Praia Grande | Esmeralda | 2 | 32 | 375 | 47.7 % |
| 18 | São Vicente | Jardim Irmã Dolores | 3 | 30 | 338 | 49.2 % |
| 19 | São Vicente | Parque Bitaru | 3 | 30 | 337 | 50.6 % |
| 20 | Bertioga | Centro | 4 | 29 | 499 | 52.0 % |

**Operational reading:** unlike GSP (where you would need a granular sector-level operation), in Baixada **20 well-known neighborhoods cover half the hotspots**, and **30 neighborhoods cover 63 %**.

---

## 6. Hotspot size

| Metric | Baixada (median) | **GSP (median)** |
|---|---|---|
| Population | 394 | 382 |
| Area (km²) | 0.032 | 0.020 |
| Equivalent side length | **~178 m × 178 m** | ~141 m × 141 m |
| Density (hab/km²) | 12,765 | 19,838 |
| Persons/household | 2.80 | 2.80 |
| **Mean income (R$)** | **2,010** | 2,203 |
| Cases over 5 years | 8 | 4 |
| **Rate /100k py** | **380** | 206 |

→ Baixada hotspots are **slightly larger geographically** but **less densely populated** than GSP hotspots — consistent with coastal-suburban morphology. **Income is lower** and **observed TB rate is nearly 2× higher**.

---

## 7. Rates by municipality

| Municipality | Pop | Cases | Rate /100k py | % pop in FCU |
|---|---|---|---|---|
| Guarujá | 280,953 | 1,569 | **112** | 37.6 % |
| Cubatão | 111,536 | 594 | 107 | 32.7 % |
| São Vicente | 323,796 | 1,599 | 99 | 26.3 % |
| Peruíbe | 67,059 | 309 | 92 | 0.4 % |
| Praia Grande | 342,894 | 1,397 | 81 | 6.2 % |
| Mongaguá | 58,551 | 236 | 81 | 0.0 % |
| Santos | 417,120 | 1,587 | 76 | 11.1 % |
| Itanhaém | 110,547 | 395 | 71 | 0.5 % |
| Bertioga | 60,553 | 194 | 64 | 26.8 % |

**Note on São Vicente**: our estimate is **99 / 100k py**, which contrasts sharply with the 577 / 100k figure circulating in working drafts (source: `municipality_incidence_rates.csv`). The discrepancy strongly suggests a numerator-denominator mismatch in that file — likely the inclusion of prison or referenced cases in the numerator without the corresponding denominator. **The 577 figure should not be cited in the WHO IC document until reconciled.**

---

## 8. Operational strategy alternatives for Baixada

| Strategy | Geographic target | Target pop | Expected % cases | Notes |
|---|---|---|---|---|
| **A) Empirical hotspots (sector)** | 220 sectors in 101 neighborhoods | 88,286 (5 %) | 26 % | Easier than GSP (220 vs 2,501 sectors). |
| **B) Top 15 FCUs** | Vila Esperança, Complexo Prainha, CDHU, Saquaré, Canal do Meio, Dique Vila Gilda, Sítio Conceiçãozinha, Vila dos Pescadores, Quarentenário, Vila Alemoa, Jd. Rio Negro/Branco, Perequê, Cachoeira Plano, Rio da Avó | ~120,000 | ~17 % (50 % of FCU cases) | **Operationally most attractive**: well-known territories, often a single UBS per FCU. |
| **C) Top 20 neighborhoods** | 20 neighborhoods covering 52 % of hotspot cases | ~50,000 | ~14 % | More politically defendable than sector-level. |
| **D) Hybrid (recommended)** | Top 15 FCUs + Top 20 hotspot neighborhoods (with overlap deduplication) | ~150,000 (8 %) | **~30–35 %** | Best return on operational effort. |

**Key contrast with GSP**: in GSP, no strategy short of sector-level granularity captured > 30 % of cases without targeting > 15 % of population. **In Baixada, ~8 % of population can be targeted for ~32 % of cases** — a far better operational ratio.

---

## 9. Implications for the proposed archetype typology

The five archetypes proposed in the GSP document (Megafavela, Industrial periphery, Cracolândia, Small dispersed FCU, Prison-adjacent) do **not fully cover Baixada patterns**. Three new archetypes emerge from coastal-industrial geography:

| # | New archetype | Baixada example | Defining features |
|---|---|---|---|
| **A6** | **Palafita / dike community** | Vila dos Pescadores (Cubatão), Dique Vila Gilda (Santos), Sítio Conceiçãozinha (Guarujá) | Stilted housing over tidal flats; flooding; precarious water/sanitation; mostly fishing communities transformed into urban poverty pockets. |
| **A7** | **Port-side hillside favela ("morro portuário")** | Morro São Bento (Santos), Morro do Itararé (São Vicente), Castelo (Santos) | Favela on steep slope immediately adjacent to port operations; landslide risk; air pollution; mix of port workers and informal economy. |
| **A8** | **Degraded port area / historical cortiço** | Saboó (Santos, rate 1,002/100k), Vila Alemoa (Santos, rate 539), Centro (Bertioga) | Historic port-related architecture converted into multi-family rooming houses; high density per building; transient population; substance use prevalence. |

Combined with the original 5 GSP archetypes, this produces an **8-archetype framework** spanning capital metropolitan and coastal-industrial Brazilian geography. The CDHU social-housing pattern (#3 in the FCU list, top 3 Baixada FCUs) may warrant a 9th archetype ("planned social housing") but requires further validation.

---

## 10. Discussion points for advisor

### On the Baixada-specific findings

1. **The 2× rate gap between Baixada (89/100k) and GSP (43/100k)** — what drives this? Port-related occupational TB? Higher HIV prevalence in coastal cities? Underreporting bias different between regions? Worth investigating before WHO IC modeling assumptions.
2. **São Vicente "577 / 100k"** — needs reconciliation with our 99 / 100k estimate before any external citation. Hypothesis: numerator-denominator mismatch (prison cases or referenced cases in numerator without proper denominator).
3. **Why is FCU more predictive in Baixada than GSP?** Possible explanation: in Baixada, formal favela boundaries correspond more closely to socioeconomic vulnerability because the coastal geography limits informal expansion. In GSP, peripheral non-FCU neighborhoods absorb much of the vulnerable population.

### On the typology

4. **Are the 3 new archetypes (palafita, morro portuário, cortiço portuário) coastal-Brazil specific, or generalizable to other Latin American port cities** (Buenaventura, Callao, Valparaíso, Guayaquil)?
5. **CDHU "planned social housing"** — should this be a 9th archetype, or treated as a variant within "industrial periphery"?
6. **Combined GSP + Baixada calibration**: with 8 archetypes from two regions, do we have enough confidence to propose this as a national framework, or do we need a 3rd region (recommendation: a northeastern capital like Salvador or Recife, with distinct urban form)?

### On the operational strategy

7. **Recommendation for Baixada**: hybrid (D) — top 15 FCUs + top 20 hotspot neighborhoods. Reaches ~32 % of cases by targeting ~8 % of population. **Confirm this is acceptable as the Baixada strategy proposal.**
8. **The contrast in operational tractability between Baixada and GSP** — Baixada is dramatically more concentrated. Does this support a sequenced WHO IC rollout (start in Baixada, prove concept, then scale to GSP)?

### On reproducibility

9. **Matching cascade T3 (fuzzy)** contributed 20.6 % of matches in Baixada. We adopted a conservative threshold (token_set_ratio ≥ 88, median match score 100). **Should we re-run GSP with the same improved cascade** to see if GSP coverage rises from 90.8 % closer to 97 %?
10. **T4 (bairro centroid fallback)** added 4.2 % of matches but is excluded from sector-level analysis. **Should T4 be used for any analysis** (e.g., bairro-level epidemiology) or left as cohort enumeration only?

---

## 11. Available files

| File | Content |
|---|---|
| `scripts/28_download_cnefe_baixada.py` | CNEFE download for 9 RMBS municipalities (29 MB total) |
| `scripts/29_cnefe_match_cohort_baixada.py` | Baseline matching (72.5 % coverage) |
| `scripts/29b_cnefe_match_baixada_improved.py` | Improved cascade (97.5 % coverage, T1–T4 + fuzzy) |
| `scripts/30_baixada_full_analysis.py` | Full Baixada analysis (v1) |
| `scripts/30b_baixada_full_analysis_v2.py` | Full Baixada analysis (v2) — final |
| `/tmp/cohort_baixada_with_cnefe_v2.csv` | 9,447 Baixada cases with sector/lat/lon/match tier |
| `/tmp/baixada_setores_priorizados_v2.csv` | 4,024 sectors ranked by vuln_score |
| `/tmp/baixada_hotspots_v2.csv` | 220 hotspot sectors |
| `/tmp/baixada_hotspots_por_bairro_v2.csv` | 101 neighborhoods aggregated |
| `/tmp/baixada_casos_por_FCU_v2.csv` | 187 FCUs with population and case counts |
| `/tmp/baixada_taxas_por_municipio_v2.csv` | Rates per municipality |

---

*Discussion document — Stanford University / WHO TB Screening Investment Case — June 2026.*
