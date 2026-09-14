# ADR-0005 — LTFU is analysed as the proportion of evaluated episodes

## Context
Two LTFU measures are possible: LTFU events per adult population (per capita) and the
proportion of LTFU among episodes with an evaluated outcome. Per-capita LTFU is the most
geographically concentrated outcome (Gini about 0.42, about half of events in the top 20% of
the population) because it inherits the concentration of notifications. The proportion among
evaluated episodes is the least concentrated (Gini 0.25) and is the measure of programme
retention.

## Decision
All LTFU analyses use the proportion of evaluated episodes (`na/ne` in
`scripts/100_region_units.py`). Because LTFU has individual-level data, age adjustment of that
proportion uses the evaluated episodes' own age mix (`E_ab`) and is a sensitivity analysis
(ADR-0006). The per-capita version is reported in the supplement as a finding: its
concentration largely reflects the concentration of notifications, not geographic variation in
retention.

## Consequences
LTFU is the least concentrated of the three outcomes and its concentration declines across
periods; notification and mortality results are unaffected by this choice.
