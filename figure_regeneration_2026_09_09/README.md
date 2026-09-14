# Figure regeneration and numeric reconciliation — 2026-09-09

Provenance record for the corrections applied in **manuscript v13** and **appendix v12**.

- Inputs: `Data/analytic/region_units.csv`, `Data/analytic/region_cases.csv`,
  `Data/analytic/ltfu_glmm_summary.json`
- Superseded scripts: `New_analyses/scripts/build_fig{2,3,5}.py` (see `SUPERSEDED.md` there)
- Corrected scripts: `./scripts/` — run from that directory; they write into `./figures/`
- Re-runnable checks: `./verification/`

---

## 1. What was wrong

### 1.1 Figures 2d, 3b, 3c plotted age-standardised rates while the text described crude rates
*(flagged by Codex in the v12 figure comments)*

`build_fig2.py` panel (d) and `build_fig3.py` panels (b, c) drew the `inc_adj` and
`drate_adj` columns and carried the axis label "Age-standardised rate per 100,000/yr".
The main text and both figure legends describe the primary analysis as crude.

The **text was right and the panels were wrong**. Crude rates reproduce the reported values
exactly; age-standardised rates do not:

| Quantity | Manuscript text | Crude (computed) | Age-standardised (computed) |
|---|---|---|---|
| Fig 3b excess fraction, notifications | 34%, ~62 600 cases | **34·1%, 62 575** | 32·7%, 59 785 |
| Fig 3b gradient, /100 000/yr | 33 → 69 | **33·5 → 68·8** | 34·1 → 67·2 |
| Fig 3c excess fraction, mortality | 28%, ~2 500 deaths | **28·2%, 2 509** | 33·8%, 3 054 |
| Fig 3c gradient, /100 000/yr | 1·8 → 3·1 | **1·8 → 3·1** | 1·7 → 3·5 |
| Fig 2d excess fraction, notifications | 65% | **65·3%, 119 706** | 64·9%, 118 612 |

**Fix:** panels rebuilt on `inc_crude` / `drate_crude`; axis labels changed to
"Notification rate per 100,000/yr" and "Rate per 100,000/yr"; panel titles and the
quintile axis relabelled from "Incidence" to "Notifications" to match manuscript usage.
Verify with `verification/verify_rates.py`.

### 1.2 Figures 2a, 2b and 5a plotted LTFU per capita, not per evaluated episode
*(not flagged by Codex; found while checking 1.1)*

All three panels ranked regions by LTFU events ÷ adult population. The primary LTFU
measure is the **proportion of evaluated episodes**, and the Figure 2 legend explicitly
states that the per-capita version belongs in appendix figure S8.

Consequences in v12:
- Figure 2a legend showed LTFU Gini **0·42** (the per-capita value) while the text reported **0·23**.
- Figure 5a showed a **flat** LTFU series `[44, 43, 42, 43]`, directly contradicting the
  text's "declined markedly for LTFU".

**Fix:** added a proportion-aware cross-fitting routine (`denoised_curve_prop` in
`build_fig2.py`, `denoised_share_prop` in `build_fig5.py`). For a proportion outcome the
**evaluated episodes** are split, not the events: regions are ranked by the LTFU proportion
in one half and the share of LTFU events is measured in the other, accumulating regions to
20% of the adult population. This is now documented in appendix v12
("Concentration and hotspot overlap").

### 1.3 Figure 5b period labels overlapped
*(flagged by Codex)*

**Fix:** `trained 2013-2018 / tested 2019-2024` → compact two-line `2013–18 ↓ 2019–24`.

### 1.4 Out-of-sample capture for 2013–15 → 2022–24 was reported as 42%
Exact value is **40·81%**, i.e. 41%. Corrected in four places in the main text
(Findings, Added value, Results, Discussion). The other two scenarios were correct:
43·94% → 44% and 47·79%/47·97% → 48%.

### 1.5 Figure 2d bootstrap CI
Reported as 63–67. A stable bootstrap (B=4000, three seeds, spread <0·2) gives
**63·5–67·7 → 64–68**. Figure 3's CIs confirmed exactly as written (29·5–39·2 → 30–39;
21·8–34·2 → 22–34), so only 2d was adjusted. Bootstraps in the corrected scripts are
pinned at B=4000 so the inset CI is reproducible.

---

## 2. The one residual discrepancy (LTFU per evaluated episode)

The LTFU per-episode routine had to be reimplemented. It does **not** reproduce the
originally reported values, and the gap is systematic rather than Monte Carlo:

| | Originally reported | Reimplementation |
|---|---|---|
| Top-20% share, crude | 24% | **25·2%** |
| Gini, crude | 0·23 | **0·246** |
| Top-20% share, age-standardised | 22% | **24·0%** |
| Gini, age-standardised | 0·21 | **0·231** |
| Table S4, all tiers | 24% | **25·2%** |
| Table S4, excluding T5 | 26% | **26·9%** |
| Fig 5a series | 37 → 26 | **38, 36, 28, 29** |

Not Monte Carlo error: the estimate is stable to three decimal places from B=200 to
B=3000 (`verification/verify_ltfu2.py`). Notifications and mortality reproduce **exactly**
everywhere because they reuse the original code path, so the offset is confined to the
proportion-outcome routine. Alternative weightings were tested and none recovers the
original values (`verify_ltfu2.py` tries population vs episode weighting × three
minimum-episode thresholds).

**Where 24% / 0·23 came from — resolved 2026-09-10.** The original scripts were located in
the public companion repository `evelepka/SP-TB-spatial-analyses` (scripts 100–120), which
is not mirrored in `jasonandr/SP-TB-spatial-analyses`. They show that **no original script
ever computed a per-evaluated-episode LTFU concentration**. Every concentration script —
102 (main figure 2), 105 (main figure 5) and 111 (appendix figure S2) — defines the LTFU
lens as `co["aband"] == 1`, i.e. LTFU events per capita, which is exactly what the
superseded `build_fig*.py` scripts inherited and what §1.2 corrects. Only
`100_region_units.py` touches the `eval` denominator, and only to build the region-level
`ltfu_crude` / `ltfu_adj` columns.

Region-level alternatives were also tested and none reproduces the reported pair: ranking
regions by `ltfu_crude` gives a top-20% share of 43·5% (Gini 0·40), by `ltfu_adj` 41·2%
(Gini 0·37), and the share of LTFU events inside the stored `hs_aband` hotspot flag is
43·5%. The reported 24% / 0·23 therefore appears to have been computed ad hoc and not
preserved in any script. The reimplementation used here (25·2% / 0·246) is the closest of
everything tested and is the only candidate matching the definition the manuscript states
— LTFU as a proportion of evaluated episodes, share of events in the top 20% of the adult
population. It supersedes the earlier speculation that age adjustment had been misapplied.

**Resolution adopted:** report both rate bases from the single documented implementation in
`./scripts/`, so that main text, appendix and figures agree and every number is
reproducible from code in this folder. Changes made:

- main text: 24% → 25%, Gini 0·23 → 0·25, Fig 5a 37→26 → 38→29
- appendix: 22%/24% → 24%/25%, Gini 0·21/0·23 → 0·23/0·25, figure S8 legend 0·23 → 0·25,
  table S4 LTFU column 24 → 25 and 26 → 27

All are tracked changes in v13 / appendix v12 and can be reverted together if the original
implementation is recovered. Conclusions are unaffected: LTFU remains the least
concentrated outcome, remains far less concentrated per evaluated episode than per capita,
and still declines over the four periods.

---

## 3. Values confirmed unchanged

Verified against the analytic tables with `verification/verify_all.py`:

- 192 161 geocoded episodes; 7 314 regions; 35 933 055 adults; 9 301 deaths;
  21 561 LTFU events; 171 024 evaluated episodes
- 2 066 sub-threshold regions = 16·3% of adults, 4·6% of cases
- geocoding tiers T1 58·6%, T2 21·3%, T3 10·3% (sum 90·2%), T4 1·9%, T5 7·9%
- Jaccard 0·44 / 0·20 / 0·17 / 0·19; hotspot counts 2 660, 1 521 (57%), 277, 121
- Cohen's d: notifications 0·44–0·64 (income 0·64, favela 0·63); mortality 0·17–0·39;
  LTFU 0·08–0·20
- favela regions 1 185, 7·6% of adults, 12·5% of cases, rate 72·9, LTFU 14·9%
- statewide notification rate 44·6 and mortality 2·2 per 100 000/year
- notifications Gini 0·39 and mortality 0·28; LTFU per capita Gini 0·42
- de-noising: notifications 47·4% naïve → 45·4%; mortality 61·2% naïve → 38·8%
- GLMM: σ² 0·1385 → 0·1389 (0%) → 0·1325 (4%); ICC 4%; MOR 1·65; 171 024 episodes,
  6 927 regions
- out-of-sample: 43·94% → 44%, contemporaneous 47·79% → 48%

## 4. Not verifiable from the current analytic tables

`region_units.csv` carries no metropolitan flag, so the metropolitan/non-metropolitan
split in table 1 and the "51% of adults / 68% of cases / 60 vs 29 per 100 000" sentence
could not be recomputed here. Table 1's own totals are internally consistent
(populations and case counts sum to the state totals).
