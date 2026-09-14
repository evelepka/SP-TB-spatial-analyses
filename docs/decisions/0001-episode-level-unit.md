# ADR-0001 — Unit of analysis is the incident episode; TB death is a person-level event

## Context
Notification rates are event rates: a person notified with a new episode in 2015 and a
recurrence in 2021 contributes two incident episodes. Person-level counting under-counts
incidence and makes the denominator depend on which record is the last one. Death, by contrast,
happens once per person but can appear on more than one episode record (register outcome and
mortality-register linkage).

## Decision
Each new or recurrent notification is one incident episode
(`drop_duplicates([person id, case type, year])`). Treatment outcomes (LTFU, evaluated
episodes) are per episode. TB death is ascertained per person (register outcome or
mortality-register ICD-10 A15–A19) and attached to the last episode only, so it is counted
exactly once. Implemented in `scripts/100_region_units.py`; `region_cases.csv` is the single
case-level source for every downstream script.

## Consequences
Study flow: 270,492 notifications to 192,161 analytic episodes (Supplementary Figure S1,
`scripts/114_figS_strobe.py`). `test/check_artifact_pins.py` ties the artifacts, the STROBE
figure and `manuscript/PIPELINE.md` together so the counts cannot drift apart.
