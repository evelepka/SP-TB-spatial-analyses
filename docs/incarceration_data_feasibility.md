# Incarceration data for community-level TB↔prison linkage in São Paulo state

Feasibility scan, May 2026. Question: can we obtain community-level incarceration rates in São Paulo state — ideally at neighborhood / census-tract resolution — to support analyses of bidirectional TB transmission between prisons and the communities that feed them?

## Bottom line

Scraping the **Tribunal de Justiça de São Paulo** (TJSP) e-SAJ portal is technically feasible — others have done it for academic urban research — but **defendant home addresses are not routinely published in TJSP decisions**. The realistic payoff from TJSP is extracting *place of the offense* and charge / sentencing metadata, which is a weaker proxy than home address. For the actual variable we want (residence of incarcerated people, aggregated to community), the strongest path is a formal data partnership with **SAP-SP** (state prison administration) or **DPE-SP** (public defender), complemented by **SSP-SP** offense data at the *Distrito Policial* level.

## What's actually accessible from TJSP

### Public e-SAJ (no login)

- 1º Grau and 2º Grau case lookup by process number, party name, OAB
- Full text of many *sentenças* and *acórdãos*
- Movements, classes (CNJ codes), charge codes
- robots.txt does not prohibit automated access; rate-limit and respect courtesy

### Working Python tooling

- [`pyESAJ`](https://pyesaj.readthedocs.io/pt/latest/) — Selenium wrapper for e-SAJ
- [`jespimentel/esaj_2_grau`](https://github.com/jespimentel/esaj_2_grau) — 2º Grau scraper
- [LabCidade `portas`](https://github.com/labcidade/portas) — TJSP sentence search/tabulation, built at FAU-USP for urban-research questions (closest analogue to our use case)

### Hard constraints on criminal cases

1. **Segredo de justiça.** Many criminal proceedings (juvenile, sexual offenses, ongoing investigations) are sealed; only metadata visible.
2. **LGPD + CNJ Resolução 121/2010.** Even in unsealed decisions, *qualificação completa* of the réu — CPF, RG, full home address — is routinely redacted. What appears in the decision body is typically: place of the crime, sometimes the neighborhood mentioned in narrative, age, occupation. Not a structured address.

## The Oliveira / Sperandio Nascimento paper (2024/2025)

The cited PLOS ONE paper ([2025 version](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0320244); [arXiv 2204.07182](https://arxiv.org/abs/2204.07182)) fine-tunes BERT, GPT-2, RoBERTa, and LLaMA on 210k Brazilian legal cases and clusters them by cosine similarity of embeddings.

It is a **document-similarity** paper. It does not extract structured entities (names, addresses) and does not address our question directly. It is useful evidence that Portuguese-language legal-domain LMs work at scale, but the right NLP anchor for an extraction-focused project is **LeNER-Br** (Araújo et al., PROPOR 2018) — the canonical Brazilian legal NER dataset — plus recent LLM-prompted NER work.

Important caveat from LeNER-Br: location entities make up ~0.6% of tagged words and have noticeably lower F1 than the other entity classes. That is not a model failure; it reflects the underlying fact that Brazilian court decisions rarely contain structured addresses. NER will not manufacture data that isn't in the text.

## DataJud (CNJ) — different beast

The [DataJud public API](https://datajud-wiki.cnj.jus.br/api-publica/) provides process metadata: process number, court, party names, movement codes, classes, decisions. **No addresses, no decision bodies.** Useful for denominators (case volumes by município, by charge class) and for sampling case numbers to then hydrate via e-SAJ. Not useful for residence extraction.

## Realistic paths, ranked

### 1. SAP-SP via formal data agreement (strongest)

SAP-SP runs all 176 prison units in São Paulo state and holds, for every custódia, the **município and endereço de prisão** and frequently the **endereço residencial declared at intake**. This is exactly the variable we want. Access requires a research convênio; possible institutional routes include SEADE, NEV-USP, or direct via Coordenadoria de Reintegração Social.

### 2. SSP-SP boletins de ocorrência (strong, complementary)

Monthly counts of offenses by *Distrito Policial*. DPs map cleanly to weighted-area aggregations of census tracts. Tells us about offense location, not offender residence, but is a usable spatial proxy for community-level crime exposure and arrest pressure.

### 3. TJSP scrape for place-of-crime + sentencing (possible, weak proxy)

Scrape *sentenças* via e-SAJ and run NER over the body for:

- *Local do crime* (street / bairro, mentioned in many decisions)
- Charge class (often structured as CNJ codes)
- Sentencing outcome (anos, regime inicial)

Output: conviction-rate map by *neighborhood of offense*. Under the assumption that for many crime types offense location is near residence, this is a usable proxy for community arrest intensity. Independent value as a method paper on Portuguese legal NER for spatial epi, even if SAP partnership succeeds.

### 4. Defensoria Pública de SP (possible, narrow)

DPE-SP case management contains *endereço residencial* — they need it to serve clients. A research convênio would give residence for the population DPE represents, which heavily overlaps our target (low-income communities, favela residents). Coverage is a sub-population, not the full pool of incarcerated people.

## Recommended sequencing

- Pursue **(1) SAP-SP** and **(4) DPE-SP** in parallel as the primary data acquisitions
- Build **(3) TJSP scrape + NER pipeline** as a proof-of-concept; independent value, fallback if (1) stalls
- Use **(2) SSP-SP DP-level data** as the immediately-available spatial proxy

## Open methodological questions

- Will the home-address signal in SAP intake records survive geocoding? Many incarcerated people give a relative's address or are de-facto unhoused at arrest.
- How to handle the (large) fraction with prior incarcerations — current address vs address at first arrest may differ.
- How to validate any TJSP-derived "neighborhood of offense" proxy against the SAP residence ground truth if both can be obtained for a subset.

## References

- Oliveira & Sperandio Nascimento, *Analysing similarities between legal court documents using NLP approaches based on transformers*. PLOS ONE 20(4):e0320244, 2025. arXiv:2204.07182.
- Araújo et al., *LeNER-Br: A Dataset for Named Entity Recognition in Brazilian Legal Text*. PROPOR 2018. https://teodecampos.github.io/LeNER-Br/
- CNJ DataJud public API wiki: https://datajud-wiki.cnj.jus.br/api-publica/
- TJSP e-SAJ consulta: https://esaj.tjsp.jus.br/cpopg/open.do
- pyESAJ: https://pyesaj.readthedocs.io/pt/latest/
- LabCidade `portas`: https://github.com/labcidade/portas
- jespimentel/esaj_2_grau: https://github.com/jespimentel/esaj_2_grau
- SAP-SP: https://www.sap.sp.gov.br/
