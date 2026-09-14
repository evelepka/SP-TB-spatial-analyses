# Dead ends

Approaches tried and abandoned. **Keyed on the SYMPTOM you would observe, not the conclusion.**
Add an entry the moment something is abandoned, while the symptom is fresh.

Seeded 2026-08-10 from what the repo itself records; the owner should add the dead ends that
live only in her head and old chats (candidates: geocoding variants 01a-01e, the 13+ hotspot
definitions tried before top-5%-by-rate, any smoothing approach rejected before PCHIP).

---

### Cases place in the wrong neighbourhood wholesale — the map contradicts local knowledge
**Tried (master branch, scripts `01_*`):** geocoding TBWeb by CEP centroid.
**Result:** ~91% bairro mismatch between CEP centroid and the recorded address neighbourhood —
a systematic TBWeb data-entry bias, not noise. Analysis at sector level was impossible.
**What worked instead:** CNEFE street+number matching, 90.8% match in GSP (ADR-0002). CEP
survives only as the T5 fallback tier, with a sensitivity analysis excluding it.

### A documented cohort flow disagrees with the built figure, and both are "in the repo"
**Observed (2026-08-10):** `manuscript/PIPELINE.md` said N = 176,127 while the committed STROBE
figure said N = 192,161 — the doc carried the person-level flow five weeks after the
episode-level rebuild (ADR-0001).
**Result:** numbers written in prose rot silently the moment a pipeline is re-run.
**What worked instead:** `test/artifact_pins.json` + `test/check_artifact_pins.py` tie the
artifact row counts, the figure literals and the pins together; `run_fast.sh` fails on drift.

### LTFU looks like the MOST concentrated outcome and its geography tracks incidence
**Observed (2026-08-11, during TC/NM review):** Figure 1 ranked regions by LTFU events per
capita — a quantity dominated by where the CASES are, not where treatment retention fails.
Under the proportion-among-evaluated (the estimand the hotspot analysis already used), LTFU is
the LEAST concentrated outcome (Gini 0.42 → 0.21; top-20% share 49% → 22%).
**Resolution:** ADR-0005 — proportion-among-evaluated everywhere; per-capita as supplementary,
reframed as a finding. If a future analysis shows LTFU strongly concentrated, first check
which denominator is in play.

### Figure 3 inset excesses cannot be reproduced to the digit; every reasonable spec is ~1% off
**Observed (2026-08-11):** the manuscript Figure 3 (Cohen's d + income-quintile excess panels)
had no in-repo builder. The numbers date from a lost 2026-07-08 session (the docx image was
merely inset-PATCHED on 2026-08-11 for the PAF → "Excess fraction" rename — see
/tmp/inset_b_new.png etc., never recomputed). Panel (a) was recovered EXACTLY (eligible
regions, unweighted Cohen's d with avg-of-variances SD, raw income sign-flipped), and all 10
quintile bar heights match exactly, but the inset excesses (59,785 cases / 3,054 deaths)
resist exact recovery: rate-difference × person-years lands at 59,683 / 3,066 (≤0.8% and
≤3.7% per bar); SIR-based, age-stratified-reference, direct-standardisation, crude-reference,
boundary-rule, eligibility, and income-aggregation variants all fit worse (see
`scripts/124_fig3_composite.py` header).
**Resolution:** `124_fig3_composite.py` is now the single source, implementing the closest
spec and printing the manuscript deltas. **Author decision (Evelyn, 2026-08-16): the scripted
values were ADOPTED** — Figure 3 regenerated from 124 and the manuscript text updated
(EF mortality 34%→35%, CI 28–40→29–40, excess cases ≈59,700). The legacy inset values are
retired.
Symptom to remember: if a figure's numbers survive a "regeneration" bit-identical, check
whether the PNG was patched rather than rebuilt.

### "Variance explained by region" comes out at 4% and makes the place effect look negligible
**Observed (2026-09-05):** the GLMM's latent-scale ICC, σ²/(σ²+π²/3) = 0.139/3.43 = 4%, was
proposed as a more intuitive replacement for the median odds ratio (MOR 1.65).
**Result:** for a binary outcome the individual-level variance is fixed at π²/3, so the ICC is
tiny by construction while the same σ² gives a >2-fold range in predicted LTFU across regions
(≈8% to 19% between the 10th and 90th percentile regions). Reporting 4% would have undercut a
real finding with an artefact of the scale (Merlo's motivation for the MOR in the first place).
**What worked instead:** report the predicted-probability range and the proportional change in
between-region variance after each adjustment (0% case-mix, 4% DOT); keep σ², MOR, ICC in the
supplementary model table (ADR-0006).

### `RANK=crude` produced a DIFFERENT LTFU than expected — "crude" meant per capita
**Observed (2026-09-05):** before ADR-0006, `RANK=crude` in scripts 102/105/122 ranked LTFU by
events per population (the pre-ADR-0005 estimand), not by the crude proportion of evaluated
episodes. Reusing it for the crude-primary switch would have silently resurrected the
per-capita dead end (Gini 0.42, "most concentrated outcome").
**What worked instead:** `scripts/rank_basis.py` with three explicit bases — crude
(pop / evaluated), std (expected events), percap — and `rank_base()` used by every ranking
script. Symptom to remember: an LTFU Gini near 0.4 means the denominator is population.

### A manuscript number survived an estimand change because nobody grepped for it
**Observed (2026-09-05):** the Results quoted consecutive-period hotspot Jaccard "LTFU 0.28"
three weeks after ADR-0005 moved LTFU to the proportion basis (true value 0.14–0.15). The
per-period shares were updated; the Jaccard line was not.
**What worked instead:** when an estimand changes, list every statistic derived from it
(scripts 102/105/122 print all of them) and grep the manuscript text for each, not just the
headline ones.

### Word refuses a docx that LibreOffice renders and the schema validator passes
**Observed (2026-09-05):** "Word found unreadable content" after porting reviewer comments
between documents. Cause: three comment hyperlinks (PubMed/IBGE/gov.br) carried `r:id`
references but `word/_rels/comments.xml.rels` had not been created. LibreOffice ignores
dangling relationships; Word rejects the whole file.
**What worked instead:** audit every part's `r:id`/`r:embed` against its `.rels` before
packaging, and test-open the file in Word itself via AppleScript
(`scratchpad/word_test.sh`) — the only oracle that reproduces the failure headlessly.

### LTFU concentration: 24% / Gini 0.23 vs 25% / 0.25 — two cross-fit variants, one canonical
**Observed (2026-09-10):** scripts 102/105/122 (via `rank_basis.rank_base`, `RANK=crude`) split the LTFU
EVENTS and rank regions by events ÷ evaluated episodes (24.4% / Gini 0.23 on 2026-09-05). Jason's
`figure_regeneration_2026_09_09/scripts/build_fig2.py` (branch `figure-regeneration-2026-09-09`)
splits the EVALUATED EPISODES and ranks by the LTFU proportion in one half, measuring the share of
events in the other (25.2% / 0.246; Fig 5a series 38,36,28,29). Both are defensible; they differ
systematically, not by Monte Carlo noise (his `verification/verify_ltfu2.py`).
**Resolution:** the submitted manuscript (v13+) uses Jason's episode-split routine everywhere (text,
appendix, Figures 2 and 5). Treat it as canonical for LTFU concentration; do not regenerate Figures 2/5
from scripts 122/105 without porting `denoised_curve_prop` first. Symptom to remember: an LTFU top-20%
share of 24% vs 25% (Gini 0.23 vs 0.25) is this definitional difference, not an error.
