# TB concentration in Greater São Paulo (2020-2024) and active case-finding strategies: discussion document

**Author:** Evelyn Lepka de Lima (Stanford University)
**Date:** June 2026
**Context:** WHO TB Screening Investment Case — Brazil. Defining geographic targets for active case-finding (ACF) in Greater São Paulo (GSP), before expansion to Baixada Santista region.
**Purpose of this document:** support discussion with advisor on **which spatial unit and which prioritization criterion** to adopt — including a proposal to move from point-based hotspots to a **TB vulnerability typology (archetypes)** that travels nationally and regionally.

---

## Executive summary

1. **TB in GSP is highly concentrated at the fine scale** (census sector) but **dispersed at the neighborhood/municipality scale**. 5 % of the population (1.03 M) concentrates **29 % of cases** (RR 7.75×), but these 5 % are spread across **2,501 sectors in 121 neighborhoods and 37 municipalities**.
2. **IBGE-defined slums (FCU — Favelas e Comunidades Urbanas) capture only 19 % of cases** with 14 % of the population (RR 1.40×). A slum-restricted strategy would miss 81 % of GSP cases. Even the two megafavelas (Paraisópolis + Heliópolis) together represent only **5.1 % of FCU cases** — there is no "TB favela".
3. **A priori composite vulnerability index** (income + density + FCU) has **weak predictive performance** (RR 1.5×, captures 7 % of cases in 5 % of the population). Likely missing critical dimensions: HIV, drug use, homelessness, prison contacts.
4. **ABCD industrial belt + Guarulhos + Osasco** emerge as **critical non-favela axes** (Pimentas, Cumbíca, Montanhão, Eldorado, Munhoz Jr., Padroeira). São Paulo city has high case volume but dilutes across very granular micro-neighborhoods.
5. **Methodological pivot under consideration**: shift from a sector-level point-hotspot logic to a **TB vulnerability typology (4–5 archetypes)** — a transferable framework that other Brazilian states and Region of the Americas (AR) countries can adapt to their own territories. Rationale: urban mobility makes ~141-m sectors finer than the true epidemiological unit; national policy needs portable concepts, not nominal lists.
6. **Key open decisions for advisor**: (a) hotspot vs typology vs hybrid; (b) sector vs neighborhood vs primary care catchment (UBS) as the operational unit; (c) a priori vs clustering-based archetype derivation.

---

## 1. Data base

- **Cohort:** 51,016 TB cases notified in GSP between 2020 and 2024 (Pulmonary + Mixed forms; New + Relapse cases; Community entry route; SINAN-TBweb).
- **Geocoding:** via **CNEFE 2022** (National Address Registry for Statistical Purposes, IBGE September 2024 release) — matching of (street, number) to neighborhood + census sector + lat/lon.
- **Matching rate:** 46,303 cases (90.8 %) successfully assigned to a CNEFE census sector.
- **Denominator:** IBGE 2022 resident population (v0001), restricted to residential sectors (CD_TIPO 0/1) with ≥ 100 inhabitants — total 43,972 sectors covering 20.5 M people.
- **Average GSP rate:** 42.6 per 100k person-years.

---

## 2. Prevalence and concentration of TB in GSP (2020-2024)

### 2.1 FCU — IBGE-defined favelas and urban communities

| | Population | Cases | Rate /100k py |
|---|---|---|---|
| **In FCU** | 2.93 M (14.3 %) | 8,305 (19.0 %) | **56.6** |
| **Outside FCU** | 17.6 M (85.7 %) | 35,486 (81.0 %) | 40.3 |
| **Rate ratio** | — | — | **1.40 ×** |

→ Living in an FCU implies **40 % higher TB risk**, but **81 % of GSP cases occur outside IBGE favelas**. A slum-restricted strategy would miss the majority.

### 2.2 Composite vulnerability index (a priori)

Built without using observed TB. Formula: `z(-log income) + z(log density) + z(is_FCU)`.

| Target % pop | N sectors | % cases captured | Rate | RR vs rest |
|---|---|---|---|---|
| Top 1 % | 318 | 1.3 % | 57 / 100k | 1.35 × |
| Top 5 % | 1,919 | 7.3 % | 62 / 100k | 1.49 × |
| Top 10 % | 4,062 | 14.3 % | 61 / 100k | 1.50 × |
| Top 20 % | 8,425 | 27.4 % | 58 / 100k | 1.51 × |
| Top 30 % | 12,337 | 39.8 % | 57 / 100k | 1.54 × |

**Low efficiency**: top 5 % of population captures only 7.3 % of cases. Implies that **income + density + FCU explain little of the spatial variation of TB** in GSP. Critical predictors are missing.

### 2.3 Empirical hotspots — top 5 % of population by observed TB rate (a posteriori)

| Hotspot pop | N sectors | Cases | Rate | RR vs rest |
|---|---|---|---|---|
| 1.03 M (5.0 %) | 2,501 | **12,689 (29.0 %)** | **247 / 100k py** | **7.75 ×** |

→ Within 5 % of the population, 29 % of cases concentrate, with a rate **7.75 × higher** than the rest of GSP.

### 2.4 Combined coverage

| Strategy | % target population | % cases covered |
|---|---|---|
| FCU only | 14.3 % | 19.0 % |
| Empirical hotspots only | 5.0 % | 29.0 % |
| Top 5 % composite index only | 5.0 % | 7.3 % |
| Union of all three categories | 18.0 % | 40.2 % |

---

## 3. Hotspot anatomy: neighborhoods with most hotspot sectors

The 2,501 hotspot sectors are **spread across 121 neighborhoods** in many GSP municipalities. The top neighborhoods reveal a clear **metropolitan periphery pattern**:

| # | Municipality | Neighborhood | N hotspot sectors | Hotspot cases | Rate /100k |
|---|---|---|---|---|---|
| 1 | Guarulhos | **Pimentas** | 13 | 60 | 191 |
| 2 | São Bernardo do Campo | **Montanhão** | 7 | 51 | 238 |
| 3 | Osasco | Munhoz Júnior | 5 | 38 | 249 |
| 4 | Guarulhos | **Cumbíca** | 9 | 37 | 201 |
| 5 | Diadema | **Eldorado** | 7 | 36 | 225 |
| 6 | Osasco | Padroeira | 6 | 35 | 256 |
| 7 | Barueri | Silveira | 5 | 34 | 228 |
| 8 | Guarulhos | Jardim Vila Galvão | 5 | 33 | 240 |
| 9 | Diadema | Canhema | 4 | 32 | 299 |
| 10 | Diadema | Taboão | 4 | 31 | 269 |
| 11-30 | (continues) | Mauá RP8/RP9, SBC Baeta Neves, Sto. André Miami/Riviera, Osasco Piratininga/Bela Vista, Guarulhos Vila Rio/Taboão | … | … | … |

**Key observations:**

- **ABCD belt + Guarulhos + Osasco** dominate the top positions. The ABCD industrial periphery (Diadema, Mauá, SBC) shows particularly high intensity.
- **São Paulo city barely appears in the top 30** — because the IBGE 2022 shapefile splits the capital into **very granular micro-neighborhoods** (Itaim Paulista, Brasilândia are subdivided into dozens of sub-units), whereas smaller municipalities have larger, more aggregated neighborhoods.
- **The top 30 neighborhoods capture only 6.1 % of hotspot cases** — confirming that cases are genuinely dispersed. There are no obvious "TB-neighborhoods" at the macro scale.
- These neighborhoods are **well-known territories to local family health teams (ESF)** — operational feasibility is high.

---

## 4. Anatomy of FCU cases: how many favelas concentrate the 19 %?

The 8,305 FCU cases (19 % of GSP total) are distributed across **2,427 distinct FCUs** — high pulverization:

| Desired coverage | Number of FCUs |
|---|---|
| 25 % of FCU cases | **43 FCUs** (1.8 % of total) |
| 50 % of FCU cases | **177 FCUs** (7.3 %) |
| 75 % of FCU cases | 457 FCUs (18.8 %) |
| 90 % of FCU cases | 823 FCUs |

**Top FCUs by absolute case count:**

| # | Municipality | FCU | Pop | Cases | Rate /100k py |
|---|---|---|---|---|---|
| 1 | São Paulo | **Paraisópolis** | 58,438 | **280** | 96 |
| 2 | São Paulo | **Heliópolis** | 55,503 | **147** | 53 |
| 3 | Mauá | Chafik / Macuco | 26,835 | 88 | 66 |
| 4 | Mauá | Jardim Oratório | 25,946 | 74 | 57 |
| 5 | São Paulo | Recanto do Paraíso | 16,553 | 67 | 81 |
| 6 | São Paulo | Safira | 15,485 | 65 | 84 |
| 7 | São Paulo | Jardim Felicidade | 16,739 | 65 | 78 |
| 8 | SBC | Vila São Pedro | 28,466 | 61 | 43 |
| 9 | São Paulo | Jardim Iporanga | 6,930 | 60 | 173 |
| 10 | São Paulo | Jardim Nova Harmonia | 20,513 | 55 | 54 |

**Key observations:**

- **Paraisópolis (280) + Heliópolis (147) = 427 cases = 5.1 % of FCU cases = 1.0 % of total GSP cases.** No "TB favela" exists — even the two megafavelas account for very little of the total.
- **Rates within the largest FCUs (53–100 / 100k py) are NOT notably higher than the GSP average (42.6).** What stands out is population volume, not per-capita risk.
- Jardim Iporanga (173 / 100k) and Castro Alves (168), while smaller in volume, have **rates ~4× the GSP average** — these are the **FCUs that are truly "hot" by rate**.

---

## 5. Hotspot size: what is a hotspot in practice?

Each hotspot is **1 IBGE census sector** — a unit much smaller than a neighborhood:

| Metric | Median | p25–p75 |
|---|---|---|
| **Population** | 382 inhabitants | 250 – 532 |
| **Area** | 0.02 km² (~1.98 ha) | 0.01 – 0.035 km² |
| **Equivalent side length** (if square) | **~141 m × 141 m** | — |
| **Population density** | 19,838 hab/km² | 11,903 – 33,659 |
| **TB cases over 5 years** | 4 cases | 3 – 6 |
| **Observed rate** | 206 / 100k py | 174 – 275 |

**Hotspot vs non-hotspot comparison (medians):**

| Variable | Hotspot | Non-hotspot |
|---|---|---|
| Population | 382 | 444 |
| Area (km²) | 0.02 | 0.028 |
| Density (hab/km²) | **19,838** | 16,562 |
| People per household | 2.80 | 2.70 |
| **Mean income (R$)** | **2,203** | 2,806 |

→ Hotspots are only **slightly denser, with marginally larger families, and 21 % lower income**. This is not the classical favela-vs-affluent-neighborhood contrast — it is a more subtle gradient within consolidated peripheral neighborhoods.

**Operational aggregation:**

- **Total intervention area:** 157 km² — only ~2 % of GSP area (which totals ~8,000 km²).
- **Estimated coverage by primary care:** each hotspot sector falls within the catchment of 1 reference primary care unit (UBS); each family health team (ESF) covers ~3,000 people. Estimate: **~300–500 ESF teams** mobilized for the intervention, distributed across 37 municipalities.

---

## 6. Operational strategy alternatives

Four alternatives under discussion. Preliminary assessment:

| Strategy | Geographic target | Target pop | Expected % cases | Operational cost | Political feasibility |
|---|---|---|---|---|---|
| **A) Empirical hotspots (sector)** | 2,501 sectors in 121 neighborhoods | 1.03 M (5 %) | **29 %** | High: requires fine-grained maps + inter-municipal coordination + GPS-equipped teams | Medium: depends on alignment between state and 37 municipal health authorities |
| **B) Megafavelas (FCU)** | Paraisópolis + Heliópolis + top 50 FCUs | ~500 k (2–3 %) | ~15–20 % | Low: UBS already operate in these territories | High: "favela" narrative is politically simple |
| **C) Neighborhoods with most absolute cases** | Top 30 neighborhoods | ~1.5 M (~7 %) | only 6 % | Medium | Technical failure — does not capture actual concentration |
| **D) Hybrid (recommended for discussion)** | Empirical hotspots + Paraisópolis/Heliópolis + FCUs with rate > 150 / 100k | ~1.3 M (~6 %) | ~32–35 % | High, but modular | Highest: combines "favela" narrative with technical criterion |

### Why A wins technically but is operationally challenging

- The scale at which TB actually concentrates (a sector of ~141 × 141 m) is **smaller than the political communication unit** (neighborhood/district) and **smaller than the operational management unit** (UBS). This creates friction between epidemiological analysis and execution.
- Possible solution: **aggregate hotspot sectors by UBS catchment** — produce a nominal UBS list per municipality, with the expected number of hotspot sectors per team. This transforms 2,501 polygons into ~300–500 operational units with accountable managers.

---

## 7. Proposed methodological pivot: a TB vulnerability typology (archetypes)

This section proposes an alternative analytical framing motivated by two limitations of the point-hotspot approach.

### 7.1 Rationale

**Limitation 1 — Urban mobility.** The TBweb residential address is where the patient sleeps, not where transmission occurs. In São Paulo, the median home-to-work commute is ~14 km and ~1h30 each way (PDU 2017). Transmission can occur in public transport, schools, workplaces, prison-visiting rooms, drug treatment centers (CAPS-AD), and crowded UBS waiting rooms. **A 141-m sector is finer than the actual epidemiological transmission unit.**

**Limitation 2 — National replicability.** The WHO Investment Case requires messages that travel to other Brazilian states and to other Region of the Americas (AR) countries. A nominal list of 2,501 sectors in GSP does not generalize. **Archetypes do generalize**: each national tuberculosis program (NTP) or state health secretariat adapts the typology to its own territory.

### 7.2 Proposed archetypes (preliminary, 5 types)

Derived from observed GSP patterns; to be validated empirically.

| # | Archetype | GSP example | Defining characteristics | Suggested intervention |
|---|---|---|---|---|
| **1** | **Consolidated urban megafavela** | Paraisópolis, Heliópolis | IBGE FCU, ≥ 50k inhabitants, located inside capital, moderate rate but high volume | UBS already present; door-to-door + contact tracing |
| **2** | **Industrial metropolitan periphery** | Pimentas (Guarulhos), Cumbíca, Montanhão (SBC), Eldorado (Diadema), Munhoz Jr. (Osasco) | Non-FCU, medium-high density, low income, ABCD/northern belt, consolidated working-class neighborhoods | Direct alignment with local municipal health secretariat; mapping via family health teams; screening at social facilities |
| **3** | **Degraded central area / "cracolândia"** | Santa Cecília, República (capital center) | High density, **not low income by mean** but very high concentration of homeless population, drug users, single-room occupancy (cortiço) | Specific approach: street outreach (Consultório na Rua), CAPS-AD, mobile screening |
| **4** | **Small dispersed FCU** | ~2,000 small favelas | Small FCU, high rate (> 150/100k), low absolute volume | Integrate into routine ESF activities; sentinel surveillance |
| **5** | **Prison-adjacent surroundings** | Sectors near prison units (SAP, LOTOM) | Proximity to prison, high family-visiting flow, data not yet tested | Contact investigation of released inmates + visitors |

### 7.3 Construction approach — three options

**Option A — A priori (rule-based).** Define archetypes from literature + clinical/programmatic experience, then classify each sector by rule (e.g., "FCU + pop ≥ 50k → Megafavela"; "near prison + density > X → Prison-adjacent"). Pros: interpretable, transparent, easy to defend. Cons: may miss data-driven structures.

**Option B — Empirical clustering.** Apply k-means or hierarchical clustering on hotspot sectors using a feature vector (income, density, is_FCU, household size, distance to city center, prison proximity, etc.). Let the data reveal natural groupings; name them a posteriori. Pros: data-driven, captures unexpected patterns. Cons: clusters may not be policy-interpretable; sensitive to feature choice and scaling.

**Option C — Hybrid (recommended).** Run empirical clustering as discovery, then refine to 4–5 final archetypes that are both data-supported and operationally meaningful. Name and validate with field knowledge.

### 7.4 Validation plan

- Classify all 2,501 GSP hotspot sectors into archetypes; report per-archetype profile (mean characteristics, % of GSP cases covered, rate, nominal examples).
- Validate on **Baixada Santista** (Santos, São Vicente, Cubatão, Guarujá, etc.) — do the same archetypes recur, or does the coastal region add new types (e.g., "port hillside favela", "tourist-area precarity")?
- If transferable to Baixada, propose the typology as a national framework for the WHO IC document.

### 7.5 Operational consequence

- Each NTP/SES applies the typology to its own territory using local data (IBGE Censo, CadÚnico, SIM, DATASUS, state penitentiary records).
- Each archetype carries a **pre-designed intervention package** (already linked to existing Brazilian programs: ESF, Consultório na Rua, CAPS-AD, SAP/LOTOM TB protocol).
- Reduces 2,501 polygons → 4–5 communicable categories without losing analytical fidelity, because the categories are **definitionally tied** to operational decisions.

---

## 8. Discussion points for advisor

### On the unit of analysis

1. **Sector vs neighborhood vs primary care catchment (UBS)** — which is the right unit for reporting to the WHO Investment Case and for operationalization? Sector is technically correct but poorly communicable; neighborhood is communicable but loses resolution; UBS is operational but requires mapping of SUS territories.
2. Does the **distance between analytical and operational units** matter for the intervention impact calculation?

### On the prioritization criterion

3. **A priori index (RR 1.5×) vs empirical hotspots a posteriori (RR 7.75×)** — does the advisor prefer an a priori model (replicable in TB-naïve settings) or accept a hybrid strategy using past TB to predict future TB?
4. **Hotspot × index overlap is only 9 % in the capital** — does this confirm the index is misspecified, or is it regression to the mean (sectors with high TB in 2020–2024 won't have high TB in 2026–2030)?
5. If we accept empirical hotspot as criterion, we need **out-of-sample validation**: split the cohort into 2020–2022 vs 2023–2024 and check whether hotspots identified in the first period predict those in the second.

### On what is missing from the index

6. **Which variables should we add to increase the composite index RR?** Candidates: homeless population (CadÚnico), HIV/SAE coverage (DATASUS), prison density (SAP/LOTOM), drug use (CAPS-AD), proximity to prisons / cracolândia centers.
7. **Is there prior TB notification data at the sector level?** Using cumulative TB 2015–2019 to predict TB 2020–2024 would probably be the single strongest predictor.

### On megafavelas

8. **Paraisópolis (280 cases) + Heliópolis (147) = 1 % of GSP cases** — is it worth treating them as symbolic pillars of the intervention (despite low quantitative weight)? Do they carry political-narrative weight for the WHO?
9. **Rates in large FCUs (53–100 / 100k) are comparable to the GSP average.** Does this reinforce that **low income is not the dominant driver in GSP** (unlike the classical literature expectation)?

### On the ABCD industrial belt

10. The **ABC + Guarulhos + Osasco axis** emerges as a cluster outside the capital — is it worth prioritizing a pilot intervention along this axis (politically "off-agenda" for the state secretariat, but technically justified)?
11. These municipalities have strong autonomous management capacity — could we directly engage with Diadema, SBC, and Guarulhos municipal health secretariats without state mediation?

### On the proposed archetype typology

12. **A priori vs clustering vs hybrid** — which path for archetype construction? Hybrid (run clustering, then refine to interpretable categories) is our preliminary preference.
13. **How many archetypes?** 4–5 simple and communicable, or 6–8 more granular (e.g., separating ABCD periphery from capital eastern periphery)?
14. **Should the typology cover only hotspots** (top 5 % by rate) **or all of GSP** (including affluent neighborhoods as a "low priority" archetype)? — for the WHO IC, having the full universe classified might be useful.

### On external validity

15. In **Baixada Santista** (next target), do we expect a similar pattern (sector-level concentration + neighborhood-level dispersion) or a different pattern (Santos / São Vicente have prisons and hillside favelas with distinct geography)?
16. **Verification of the cited São Vicente rate (577 / 100k)** — source: Jason Andrews' `municipality_incidence_rates.csv`. Suspected to include prison TB in the numerator without a penitentiary denominator — needs review before official citation.

---

## 9. Available files

| File | Content |
|---|---|
| `cohort_with_cnefe.csv` | 51,016 cases with CNEFE sector/neighborhood/lat/lon |
| `setores_priorizados_GSP.csv` | 43,972 GSP sectors ranked by vuln_score |
| `hotspots_top5pct_setores.csv` | 2,501 empirical hotspot sectors |
| `hotspots_por_bairro.csv` | 121 neighborhoods aggregating hotspot sectors |
| `casos_por_FCU.csv` | 2,427 FCUs with population and case counts |
| `casos_por_bairro_GSP.csv` | 446 complete GSP neighborhoods |
| `mapas_GSP/mapa_GSP_panel.png` | 2×2 panel of GSP overview maps |
| `mapas_GSP/mapa_capital_vuln_hotspots.png` | Zoom on SP capital — vulnerability × hotspots × rate |
| `mapas_GSP/mapa_GSP_interativo.html` | Interactive Folium map (14 MB) |
| `README_pipeline_TB_vulnerabilidade.{md,html,pdf}` | Complete CNEFE geocoding pipeline |

---

*Discussion document — Stanford University / WHO TB Screening Investment Case — June 2026.*
