# ADR-0002 — Geocode by CNEFE address match, not CEP centroid

- **Status:** accepted (2026-06, branch `gsp-vulnerability-typology`)
- **Superseded by:** —

## Context

TBWeb CEPs (postal codes) carry a systematic bias: ~91% of cases showed a bairro mismatch
between the CEP centroid and the recorded address neighbourhood (documented in
`PROJECT_CONTEXT_GSP.md` §1). Spatial analysis at sector level on CEP centroids would place
cases in the wrong neighbourhoods wholesale.

## Decision

Match cohort addresses (street, number) against CNEFE 2022 — IBGE's canonical residential
address registry — per municipality, achieving 90.8% match in GSP. Precision is flagged per
case: T1 exact street+number · T2 street · T3 fuzzy street · T4 neighbourhood centroid ·
T5 CEP centroid (fallback only, `scripts/109_cep_fallback.py`).

## Consequences

99%+ of episodes geocode to a residential sector. T5 cases are kept in the primary analysis
with a sensitivity analysis excluding them (advisor decision). The CEP pipeline (scripts
`01_*`, master branch) remains for the abandonment paper; it is not used here.
