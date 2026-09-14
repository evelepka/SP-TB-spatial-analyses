# ADR-0001 — Unit of analysis is the incident episode; TB death is a person event

- **Status:** accepted (2026-06-30, commits 5397103 / cb39cb3)
- **Superseded by:** —

## Context

The first build used person-level analysis (last treatment record per person). But incidence
is an event rate: a person notified as Novo in 2015 and Recidiva in 2021 contributes TWO
incident cases. Person-level counting under-counted incidence and made the denominator depend
on which record happened to be "last". Death, conversely, can only happen once, but appears on
multiple episode records (TBWeb `Obito TB` plus SIM linkage).

## Decision

Each new/relapse (Novo/Recidiva) notification is one incident episode:
`drop_duplicates([sinan_clean, case_type, year])`. Treatment outcomes (LTFU, evaluated) are
per-episode. TB death is ascertained per PERSON (TBWeb outcome OR SIM A15-A19 on any line) and
marked on the last episode only, so it is counted exactly once. Implemented in
`scripts/100_region_units.py`; `region_cases.csv` is the single case-level source downstream.

## Consequences

Analytic flow became 270,492 notifications → 192,161 analytic episodes (STROBE figure,
`scripts/114_figS_strobe.py`). All secondary numbers had to be refreshed (commit 1c37302) and
`manuscript/PIPELINE.md`'s old person-level flow went stale unnoticed for five weeks — which
is why `test/check_artifact_pins.py` now ties the artifact, the figure and the pins together.
