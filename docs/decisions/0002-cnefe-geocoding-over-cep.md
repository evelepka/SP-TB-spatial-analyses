# ADR-0002 — Geocode by address match against CNEFE, not by postal-code centroid

## Context
Postal codes (CEP) in the notification register are systematically imprecise: for about 91%
of cases the postal-code centroid fell in a different neighbourhood from the recorded address.
Sector-level analysis on postal-code centroids would misplace cases wholesale.

## Decision
Match the residential address (street, number) of each episode against CNEFE 2022, IBGE's
national address register, municipality by municipality (90.8% match in Greater São Paulo).
Precision is flagged per episode: T1 exact street and number; T2 street; T3 fuzzy street;
T4 neighbourhood centroid; T5 postal-code centroid (fallback only,
`scripts/109_cep_fallback.py`).

## Consequences
More than 99% of episodes are geocoded to a residential census sector. T5 episodes are kept
in the primary analysis, with a sensitivity analysis excluding them.
