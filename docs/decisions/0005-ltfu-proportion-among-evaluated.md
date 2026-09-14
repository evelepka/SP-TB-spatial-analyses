# ADR-0005 — LTFU is analysed as the proportion among evaluated episodes, everywhere

- **Status:** accepted (2026-08-11, Evelyn + Jason, prompted by NM review comments #0/#18/#52)
- **Superseded by:** —

## Context

The manuscript mixed two LTFU estimands under one label: Figure 1's concentration analysis
ranked regions by LTFU events **per capita**, while hotspot definition, the Venn overlaps and
Table 1 used the **proportion of abandonment among evaluated episodes** (`ltfu_adj`). Reviewer
NM flagged the ambiguity three times. Unifying the ranking exposed how much it matters:
per-capita LTFU is the MOST concentrated outcome (Gini 0.42; 49% of events in top-20% pop,
stable 42-44% across periods) because it piggy-backs on incidence concentration; the
proportion-among-evaluated is the LEAST concentrated (Gini 0.21; 22% in top-20% pop, declining
37→25 across periods).

Jason 2026-08-11: LTFU has individual-level data, so it needs no population-based
standardisation — age adjustment comes from the evaluated episodes' own age mix, which is
exactly what `E_ab` in script 100 already does.

## Decision

All LTFU analyses use the age-adjusted proportion among evaluated episodes (ranking basis
`na/E_ab`, i.e. `RANK=std` in scripts 102/105). The per-capita versions become supplementary
material, presented as a finding: per-capita LTFU concentration largely reflects incidence
concentration, not geographic variation in programme retention.

## Consequences

Headline changes: "LTFU was the most geographically concentrated outcome" inverts; abstract
49% → 22%; Gini 0.42 → 0.21; temporal stability 42-44% stable → 37→25 declining; LTFU hotspot
period-Jaccard 0.27-0.29 → 0.13-0.15. Incidence and mortality numbers are unchanged to the
reported precision under the same unification (rankings agree; Ginis 0.39/0.28 identical).
The incidence/mortality robustness statement (crude vs standardized immaterial) stays; LTFU's
change is an estimand correction, not fragility, and is described as such.
