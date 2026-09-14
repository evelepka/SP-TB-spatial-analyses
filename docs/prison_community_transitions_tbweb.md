# Prison ↔ community transitions in SP TBweb (2013–2024)

Quick descriptive analysis of how often people circulate between prison and community across TB episodes, using SP TBweb 2013–2024 with the existing `sinan_clean` person-level linkage from [`outcomes-after-tb-abandonment/00_clean_sinan.py`](https://github.com/jasonandr/outcomes-after-tb-abandonment).

## Setup

- File: `cohort_with_spatial.csv` (`/Users/jasonandrews/.../My Drive/SP-TB-spatial-analyses/Data/cohort_with_spatial.csv`)
- Person ID: `sinan_clean` (zero-padded SINAN with identity-conflict resolution; see `00_clean_sinan.py`)
- Residence type at each notification: `address_type` ∈ {`ENDERECO PADRAO` (community, C), `DETENTO` (prison, P), `SEM RESIDENCIA FIXA` (homeless, H)}
- Episode = distinct `notification_date` for a given person
- Code: `scratch/tb_person_trajectories.py`; trajectory output: `scratch/person_trajectories.parquet`

## Headline numbers

| Quantity | Count | % |
|---|---:|---:|
| Total persons in cohort | 235,629 | |
| Persons with ≥2 TB notifications | 25,943 | 11.0 |
| Total multi-episode consecutive notification pairs | 35,068 | |

## Within-notification mid-treatment address change

Address type does not change within a single notification in this dataset — `tx_seq` rows for one (person, notification_date) tuple carry a constant `address_type`. **Mid-treatment prison ↔ community transitions are not captured in the `address_type` field here.** They presumably exist in raw TBweb in another field (e.g., facility transfer fields) but not in this export.

## Across-notification transitions (between TB episodes)

Consecutive (episode *n* → episode *n+1*) address-type pairs for the 25,943 multi-episode persons:

| from \ to | Community | Homeless | Prison | total |
|---|---:|---:|---:|---:|
| **Community** | 23,668 | 1,184 | **1,417** | 26,269 |
| **Homeless** |    672 | 3,018 |    186 |  3,876 |
| **Prison**    | **1,430** |   226 | 3,267 |  4,923 |
| **total**     | 25,770 | 4,428 | 4,870 | 35,068 |

### Implications for prison-community circulation

- **Of people whose first-recorded TB episode was in prison and who had a second episode, 29% (1,430 / 4,923) are recorded as community residents at the second episode.** Direct evidence of prison-to-community release-while-circulating (or re-incarceration cycling with intermediate community time, depending on episode gap).
- **Of community-then-anything people, 5.4% (1,417 / 26,269) later appear in prison at a subsequent episode.** Direct evidence of community-to-prison movement.
- Prison → Prison is the largest non-stable pattern among formerly-incarcerated persons (66% of prison→anywhere pairs), reflecting high TB recurrence among the chronically incarcerated.
- ~8% of all multi-episode pairs involve a prison ↔ community switch in either direction (2,847 / 35,068).

### Time between consecutive notifications (days, median [IQR])

| from → to | n | median | IQR |
|---|---:|---:|---|
| C → C | 23,668 | 332 | 168–787 |
| C → P | 1,417 | 443 | 228–1,126 |
| C → H | 1,184 | 326 | 182–898 |
| P → C | 1,430 | **1,362** | 676–2,174 |
| P → P | 3,267 | 816 | 330–1,519 |
| P → H | 226 | 1,140 | 454–2,124 |
| H → C | 672 | 362 | 183–966 |
| H → P | 186 | 382 | 187–912 |
| H → H | 3,018 | 266 | 143–616 |

The much longer P→C median (≈3.7 years vs. <1 year for C→C) is consistent with sentence length before release: people who appear in prison at episode *n* and in the community at episode *n+1* typically experienced a multi-year gap, plausibly the remaining sentence.

## Top trajectories (≥2 notifications, entry-address at each)

| trajectory | n persons | interpretation |
|---|---:|---|
| CC | 13,771 | two community episodes |
| CCC | 2,480 | three community episodes |
| PP | 2,219 | two prison episodes |
| HH | 1,128 | two homeless episodes |
| **PC** | **904** | prison then community |
| **CP** | **890** | community then prison |
| CH | 525 | community then homeless |
| HC | 285 | homeless then community |
| PPP | 246 | three prison episodes |
| CCP | 145 | two community then prison |
| PCC | 125 | prison then two community |
| CHH | 116 | community then two homeless |
| CPP | 97 | community then two prison |
| HP | 96 | homeless then prison |
| PPC | 87 | two prison then community |
| CPC | 60 | C → P → C cycle |
| PCP | 47 | P → C → P cycle |

## Caveats

- Prior TB episodes outside the 2013–2024 export window are not captured. People coded as `Recidiva` or `Retr Aband` at their first observed notification likely had earlier episodes invisible to this analysis.
- "Address_type = Community" doesn't distinguish neighborhoods. The geocoded-CEP layer (`cep_spatial_linkage_longitudinal.csv`) is the right input for community-level resolution.
- This analysis treats `address_type` at episode entry as a snapshot. People released *during* treatment are not flagged here (within-notification field absent in this export).
- The 1,430 P→C and 1,417 C→P transitions are conservative lower bounds because the prior-episode window is limited; the true rate is plausibly higher.

## Next steps

- Geocode the CEP at each multi-episode entry to see whether prison-then-community returns concentrate in specific neighborhoods (e.g., AGSN favela polygons) — this is the direct test of the favela ↔ prison circulation hypothesis.
- Cross-tabulate with `case_type` (Novo vs Recidiva vs Retr Aband) to distinguish new diagnoses from retreatment after abandonment, which has different epidemiological meaning.
- Pull in mid-treatment facility transfers from raw TBweb (not in this export's `address_type`) to recover the within-notification prison-release-while-on-therapy events Jason described.
