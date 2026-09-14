"""Unified paper-base report — organised around the four study questions (P1-P4) with a
consolidated methodology, and an appendix (A scale sensitivity, B regionalisation, C IPVS
external validation, D favela-domain sensitivity, E mortality negative control + age-std
robustness). Self-contained HTML with all figures embedded.
"""
import base64, os
FIGDIR=("/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/"
        "My Drive/WHO modelling Project/SP-TB-spatial-analyses/Figures_2013-2024_adults")
def img(name):
    p=os.path.join(FIGDIR,name)
    if not os.path.exists(p): return f'<p style="color:#b00">[missing: {name}]</p>'
    with open(p,"rb") as f: b=base64.b64encode(f.read()).decode()
    return f'<img src="data:image/png;base64,{b}">'
N=[0]
def fig(name,cap):
    N[0]+=1
    return f'<figure>{img(name)}<figcaption><span class="figlabel">Figure {N[0]}.</span> {cap}</figcaption></figure>'

CSS="""
:root{--navy:#0d2b45;--teal:#028090;--mint:#02c39a;--ink:#1a202c;--muted:#5b6b7a;--line:#e2e8f0;--callout:#f0f9f7;--amber:#9a6700;--amberbg:#fff8e6;}
*{box-sizing:border-box}body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);line-height:1.65;margin:0;background:#f4f6f8;}
.page{max-width:880px;margin:0 auto;background:#fff;padding:60px 74px;box-shadow:0 1px 4px rgba(0,0,0,.08);}
h1{font-size:28px;line-height:1.22;color:var(--navy);margin:0 0 6px;}
.sub{font-size:15px;color:var(--teal);font-weight:600;margin:0 0 4px;}
.meta{font-size:12.5px;color:var(--muted);margin:0 0 6px;}
h2{font-size:21px;color:var(--navy);margin:42px 0 8px;padding-bottom:6px;border-bottom:2px solid var(--teal);}
h3{font-size:16.5px;color:var(--navy);margin:24px 0 6px;}
h4{font-size:14.5px;color:var(--teal);margin:18px 0 4px;}
p{margin:9px 0;} ul,ol{margin:9px 0;padding-left:22px;} li{margin:4px 0;}
code{background:#eef2f5;padding:1px 5px;border-radius:4px;font-size:12.5px;}
.callout{background:var(--callout);border:1px solid #cfe9e3;border-left:4px solid var(--mint);border-radius:8px;padding:12px 20px;margin:16px 0;}
.callout h3{margin-top:0;color:var(--teal);}
.toc{background:#fbfdfd;border:1px solid var(--line);border-radius:8px;padding:10px 26px;margin:14px 0;font-size:13.5px;}
.qbox{background:#f7fbfb;border:1px solid var(--line);border-left:4px solid var(--teal);border-radius:8px;padding:4px 20px;margin:18px 0 6px;}
.qbox .q{font-size:13px;color:var(--teal);font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
.optional{background:var(--amberbg);border:1px solid #f0e0b0;border-left:4px solid var(--amber);border-radius:8px;padding:6px 20px;margin:16px 0;}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:13px;}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top;}
th{background:var(--navy);color:#fff;font-weight:600;} tr:nth-child(even) td{background:#f7fafc;}
figure{margin:20px 0;text-align:center;}figure img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px;}
figcaption{font-size:12px;color:var(--muted);margin-top:7px;text-align:left;line-height:1.45;}
.figlabel{font-weight:600;color:var(--navy);}
.statgrid{display:flex;flex-wrap:wrap;gap:11px;margin:14px 0;}
.stat{flex:1 1 150px;background:#0d2b45;color:#fff;border-radius:8px;padding:11px 13px;}
.stat .v{font-size:22px;font-weight:700;color:var(--mint);} .stat .l{font-size:11.5px;color:#cfe0ea;line-height:1.3;}
.footer{margin-top:44px;padding-top:14px;border-top:1px solid var(--line);font-size:11.5px;color:var(--muted);}
@media print{body{background:#fff}.page{box-shadow:none;max-width:none;padding:0 6px;}h2{page-break-after:avoid}figure{page-break-inside:avoid}}
"""

H=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Geographic concentration, adverse-outcome hotspots and social vulnerability of TB — São Paulo, 2013–2024</title>
<style>{CSS}</style></head><body><div class="page">

<p class="sub">WHO TB Screening Investment Case · Brazil — manuscript base (concentration · outcomes · place vulnerability)</p>
<h1>Geographic concentration, adverse-outcome hotspots, and place social vulnerability of tuberculosis in São Paulo State, 2013–2024</h1>
<p class="meta">Adults (≥15 years), new and relapse cases · individual TB notifications geocoded to the census sector</p>

<div class="statgrid">
 <div class="stat"><div class="v">177,013</div><div class="l">adult TB cases geocoded (2013–2024)</div></div>
 <div class="stat"><div class="v">35.9M</div><div class="l">adult (≥15) population (IBGE 2022)</div></div>
 <div class="stat"><div class="v">39.3%</div><div class="l">of cases in 20% of population</div></div>
 <div class="stat"><div class="v">~2.3×</div><div class="l">incidence, least → most vulnerable areas</div></div>
</div>

<div class="callout"><h3>Summary</h3>
<p>Using 12 years of individual TB notifications from the São Paulo State surveillance system (TBWeb), geocoded to the
census sector via the national address registry (CNEFE 2022), we ask four questions: <b>(P1) how much</b> adult TB and its
adverse outcomes concentrate; <b>(P2) where</b> — and whether it is the socially vulnerable areas; <b>(P3) whether</b> the
incidence, abandonment and mortality lenses pick out the same places; and <b>(P4) whether</b> the pattern is stable over
time. Adult TB is <b>strongly and stably concentrated</b> — the top 20% of the population by local rate holds 39.3% of
cases (Gini 0.37), and the geography barely moves across the decade. Concentration claims are <b>noise-corrected</b>
throughout, because rarer events spuriously inflate concentration indices. After correction, <b>treatment abandonment is the
genuinely most concentrated and TB-specific adverse outcome</b>, while the excess concentration of mortality is general
vulnerability, not TB-specific (a non-TB-death negative control). Mortality uses an <b>integrated TBWeb + civil-registry
(SIM)</b> death marker. Place vulnerability (a five-domain IBGE-2022 composite, sector-anchored, externally validated
against the official IPVS 2022) explains the map in a <b>lens-specific</b> way: incidence rises with vulnerability (~2.3-fold),
abandonment as a <i>threshold</i> in the more-vulnerable half, and <b>TB mortality</b> by denominator (the rate per
population rises with incidence; the proportion of notified cases is flat once age-adjusted). The three lenses pick out
<b>largely different places</b> (pairwise Jaccard 0.13–0.22) with distinct structural profiles — three targeting maps, not
one. All mapped and ranked rates are <b>age-standardised</b> (indirect, to the State).</p></div>

<div class="toc"><b>Contents.</b> 1 Background · 2 Data · 3 Methods · 4 Results, by study question:
<b>P1</b> how much TB concentrates · <b>P2</b> where, and the role of place vulnerability · <b>P3</b> whether the three
lenses overlap · <b>P4</b> stability over time · 5 Key findings · 6 Discussion · 7 Next steps · 8 Reproducibility ·
Appendix A scale sensitivity · B regionalisation · C IPVS external validation · D favela-domain sensitivity · E mortality
negative control and age-standardisation robustness.</div>

<h2>1. Background and objective</h2>
<p>Brazil is a high-burden tuberculosis (TB) country, and São Paulo — the most populous state — carries a large share of
national notifications. Active case finding (ACF) is resource-intensive and cost-effective only when correctly targeted.
For the WHO TB Screening Investment Case we need a <b>reproducible, methodologically defensible</b> way to answer four
questions: <b>(P1)</b> how concentrated are TB notifications and poor outcomes; <b>(P2)</b> where are the priority areas,
and is it the socially vulnerable places; <b>(P3)</b> do high-incidence areas coincide with high-abandonment or
high-mortality areas, or are these distinct geographies; and <b>(P4)</b> is the pattern consistent over time so that
multi-year programmes can be planned.</p>

<h2>2. Data sources</h2>
<table>
<tr><th>Source</th><th>Use</th><th>Detail</th></tr>
<tr><td><b>TBWeb</b> — São Paulo State TB notification system</td><td>Individual TB cases: address, dates, age, sex, clinical form, HIV, treatment outcome</td><td>Analysis 2013–2024 (complete coverage from 2013)</td></tr>
<tr><td><b>SIM</b> — Mortality Information System (civil registry), linked to TBWeb</td><td>Death-certificate cause (underlying + all lines) for an integrated TB-death marker</td><td>10,056 deaths linked by notification number; full ICD-10 lines</td></tr>
<tr><td><b>IBGE CNEFE 2022</b></td><td>Gold-standard address → census-sector geocoding reference</td><td>~10M SP addresses, collected during the Census</td></tr>
<tr><td><b>IBGE Census 2022</b> (basic + demografia, renda, alfabetização, cor/raça, domicílios)</td><td>Sector boundaries, age-specific population denominators (8 adult age bands), and the five social-vulnerability domains</td><td>Census-sector resolution; official data dictionary</td></tr>
<tr><td><b>IPVS 2022</b> — Índice Paulista de Vulnerabilidade Social (SEADE)</td><td>Independent, official sector-level vulnerability classification, for external validation of our composite (Appendix C)</td><td>103,319 sectors; group 1 (lowest) → 6 (highest)</td></tr>
</table>

<h2>3. Methods</h2>

<h3>3.1 Study population</h3>
<p>TB cases notified in São Paulo state in <b>2013–2024</b>, restricted to <b>adults ≥15 years</b> and to <b>new and
relapse cases</b>, with a standard residential address. Detainees and people with no fixed residence are handled
separately and are not part of this community analysis.</p>

<h3>3.2 Geocoding (address → census sector)</h3>
<p>We deliberately did <b>not</b> use the postal code (CEP), because many TBWeb records have missing/incorrect CEP —
disproportionately in peripheral neighbourhoods and favelas, exactly the areas of interest. Instead we matched the
<b>textual address</b> against CNEFE 2022 after cleaning, via a cascade (T1 exact street+number, T2 street, T3 fuzzy
token-set ≥88). Coverage was a flat <b>89–93%</b> across all years and regions, so the time series is not biased by
changing geocoding completeness.</p>

<h3>3.3 Geographic units</h3>
<p>Census sectors (~300 residents) are too small for stable rates, so they were aggregated into operational units:
Functional Census Units (favela/urban community) with ≥5,000 residents where available; otherwise neighbourhoods, and
in the capital, districts (n = 3,014; median 2,872 adults, IQR 849–9,294, but heterogeneous — the capital collapses to
~118 large districts for want of an official bairro layer; full distribution in Appendix B, Figure 28). The adult (≥15)
population of each unit served as the rate denominator (IBGE 2022).
Sectors are nested within units: event rates (incidence, abandonment, mortality) were computed at the unit, where the
population is sufficient for a stable rate, whereas place vulnerability (§3.9) was retained at the sector. Sensitivity of
the concentration to the areal unit was assessed by a Gini scale analysis (Appendix A) and an independent statewide
regionalisation (Appendix B).</p>

<h3>3.4 Hotspot selection</h3>
<p>Units with ≥10 pooled adult cases were ranked by their <b>age-standardised</b> 12-year adult incidence rate (§3.10) and
added in descending order until cumulative adult population reached <b>20%</b> of the state — balancing epidemiological
yield and ACF feasibility. Adverse-outcome hotspots (abandonment, TB mortality) are selected the same way, on their own
age-standardised rates.</p>

<h3>3.5 Concentration indices and noise correction</h3>
<p>For each event type (cases, abandonments, TB deaths) units were ranked by per-capita rate and the cumulative share of
events plotted against cumulative population (a Lorenz curve), summarised by the Gini coefficient and the top-20% share.
Because small-area event counts are subject to Poisson noise that (i) <b>inflates</b> concentration indices and (ii)
<b>attenuates</b> correlations, every concentration claim is noise-corrected: <b>rarefaction</b> (down-sampling to a common
event count = the constant-rate null), <b>split-sample cross-fit Gini</b> (rank on one half of events, value from the
other), and <b>disattenuation</b> (dividing autocorrelation by split-half reliability).</p>

<h3>3.6 Integrated mortality and a negative control</h3>
<p>TB death is defined as a <b>union of both sources</b>: TBWeb <code>Óbito TB</code> OR tuberculosis (ICD-10 A15–A19)
anywhere on the SIM death certificate (deaths before and/or after treatment; not case-fatality). The "any line" rule
recovers HIV/TB co-infection deaths coded to HIV. As a <b>negative control</b> for whether any excess mortality
concentration is TB-specific, the same analysis is repeated for <b>non-TB deaths among the same TB patients</b> (Appendix E).</p>

<h3>3.7 Outcome-based hotspots — abandonment and mortality, separately</h3>
<p>Because incidence may under-count high-vulnerability areas that under-notify, units were also ranked by adverse-outcome
proportion among <b>evaluated</b> cases. Because the de-noising and negative control show they behave differently,
<b>abandonment and mortality are not combined</b>: each is mapped on its own and compared with incidence (P3).</p>

<h3>3.8 Temporal analysis</h3>
<p>For each year, the annual Gini was recomputed and the top-20% hotspots re-selected independently; year-to-year
stability was measured by the Jaccard index, and the full year×year Spearman autocorrelation of unit rates examined as a
function of lag (small-area noise handled by case-count thresholds, multi-year pooling, and disattenuation).</p>

<h3>3.9 Place social-vulnerability composite</h3>
<p>A transparent <b>five-domain</b> composite was built per census sector from the 2022 Census — income (mean head income),
illiteracy (15+), inadequate sanitation, <b>intra-household crowding</b> (residents per household, a marker of social
deprivation), and <b>favela / urban agglomeration</b> (aglomerado subnormal: precarious housing, informal tenure, absent
services — and the WHO target population) — each z-standardised, oriented so higher = more vulnerable, and averaged. Race
composition was examined but <b>excluded as redundant</b> (it correlates 0.98 with the composite); the demographic /
life-cycle axis was excluded because it age-confounds TB rates. <b>Population density</b> (residents/km²) was also excluded
from the deprivation index — it is a transmission rather than a deprivation construct, and is in fact slightly
<i>negatively</i> correlated with the composite (ρ = −0.20), because São Paulo's densest sectors include verticalised
high-income districts. Because TB is nonetheless epidemiologically a disease of urban agglomeration, a density-inclusive
version — and a four-domain version without favela — are reported as domain-choice sensitivities, with their inclusion
flagged as an open question (Appendix D). <b>Resolution and weighting.</b> Vulnerability was
assigned at the census sector rather than the operational unit — each case took the composite of its own sector — because
aggregation to the unit averages socioeconomically heterogeneous sectors (e.g. a favela and an adjacent affluent sector)
into a single, unrepresentative value. Unit-level summaries were computed both population-weighted and case-weighted; their
difference indexes within-unit concentration. Outcomes were modelled as smooth (GAM)
functions of the vulnerability percentile using <b>penalized B-splines (P-splines) capped at a small basis (k = 3)</b>; TB
mortality (% of notified) was additionally age-adjusted with a second smooth term. The composite is <b>externally validated</b>
against the official IPVS 2022 (SEADE) at the census sector (Appendix C).</p>

<h3>3.10 Age standardisation</h3>
<p>Every mapped and ranked geospatial metric — incidence, treatment abandonment, and TB mortality — is <b>age-standardised
by indirect standardisation</b>, using São Paulo State as the internal reference across eight census age bands (15–19,
20–24, 25–29, 30–39, 40–49, 50–59, 60–69, 70+). For each unit the observed count is divided by the count <i>expected</i>
from the State's age-specific rates applied to that unit's own age structure, and rescaled to the State baseline. <b>TB
mortality</b> is reported with two denominators: a <b>rate</b> per population and a <b>proportion of all notified cases</b>
(not case-fatality). Indirect standardisation is used because it is stable for small areas where some units have few
events.</p>
<p><b>Why indirect, and why two standardisations.</b> The choice follows the <i>denominator</i>. Incidence and the TB-mortality
<b>rate</b> are events per <i>population</i>, biased by each place's population age structure — captured by comparing observed
events to those <i>expected</i> under the State's age-specific rates (population age structure from the Census). <b>Direct</b>
standardisation is not viable here because a unit with a handful of deaths cannot yield stable age-band-specific rates.
Abandonment and the TB-mortality <b>proportion</b> have <i>cases</i> as the denominator, so the individual case age is used
directly (a second smooth term in the dose-response). Age standardisation left the incidence concentration essentially
unchanged (Gini 0.331 → 0.329), confirming it is not an age-structure artefact (Appendix E).</p>

<h2>4. Results</h2>

<div class="qbox"><span class="q">P1 — How much does TB concentrate?</span></div>
<h3>4.1 TB is strongly concentrated, and abandonment even more so</h3>
<p>Adult TB cases are far more concentrated than population (Figure 1): the top 20% of the adult population by local rate
holds <b>39.3% of cases</b> (Gini 0.367). The selected hotspots (Figure 2) cluster in the São Paulo urban agglomeration
and the Baixada Santista corridor, with a few high-rate units in the interior.</p>
<p>Splitting the state into four groups — selected vs non-selected × metropolitan vs interior (Figure 3) — shows the
targeting is efficient in <b>both</b> settings. The selected metropolitan units hold <b>18.9%</b> of the adult population
but <b>37.1%</b> of cases (80/100k); the selected interior units add another 2.4% of cases at a comparable rate (76/100k)
on just 1.3% of the population; while the non-selected interior — nearly half the state's population (47.8%) — carries only
26.3% of cases at 23/100k. The incidence gradient from selected-metropolitan to non-selected-interior areas is therefore
about <b>3.5-fold</b>. Within the metropolitan region alone (Figure 4) the selected areas run at 80/100k against 35/100k in
the non-selected. Separating the <b>favela / urban-community (FCU)</b> units (Figure 5), these carry the single highest
incidence — <b>90/100k</b> — on just 1.0% of the population (2.2% of cases), above the other selected hotspots (80/100k;
19.2% of population, 37.3% of cases), while the 79.8% of the population in non-selected areas sits at 27/100k. Targeting on
local rate thus reaches the densest, highest-incidence favela cores as well as the broader urban TB belt.</p>
{fig("fig1_lorenz_adult_2013-2024.png","Lorenz curve of adult TB case concentration. Gini = 0.367; the top 20% of adult population holds 39.3% of adult cases.")}
{fig("fig2_map_adult_2013-2024.png","Selected adult TB hotspot areas (20% of adult population, 39.3% of cases). Colour = 12-year pooled incidence per 100,000/year.")}
{fig("table_four_groups_adult_2013-2024.png","Four-group comparison: selected vs non-selected × metropolitan vs interior. Selected-metropolitan = 18.9% of population, 37.1% of cases, 80/100k; non-selected-interior = 47.8% of population, 26.3% of cases, 23/100k.")}
{fig("table_metro_adult_2013-2024.png","São Paulo urban agglomeration: selected (80/100k, 18.9% of state population, 37.1% of cases) vs non-selected (35/100k) areas.")}
{fig("fig4_table_adult_2013-2024.png","Targeting areas by type: favela/urban-community (FCU) selected units (90/100k, highest, 1.0% of population), other selected hotspots (80/100k, 19.2% of population, 37.3% of cases), and non-selected areas (27/100k, 79.8% of population), against the State total (38/100k).")}
<p>At face value, treatment abandonment and TB deaths look more concentrated than cases — but rarer events inflate the
naïve Gini, so every concentration is noise-corrected (split-sample cross-fit). The case concentration is <b>confirmed
real</b>: it barely moves under de-noising (naïve 0.33 → de-noised 0.32), so the headline 39.3% / Gini-0.367 is a genuine
feature of place, not a small-area artefact (Figures 6–7). Comparing the three lenses side by side after correction
(Figure 9), <b>treatment abandonment is the single most concentrated</b> — de-noised 0.40, above TB mortality (0.34) and
cases (0.32) — and it survives rarefaction (+0.11 above the constant-rate null) and unbiased restriction (Figure 8): the
robust, programmatically actionable signal. TB mortality is examined as a negative control in Appendix E; its magnitude
uses the integrated TBWeb+SIM marker (Figure 10).</p>
{fig("fig_concentration_lorenz_2013-2024.png","Naïve concentration of cases vs adverse outcomes. TB deaths (0.414) and abandonment (0.477) appear more concentrated than cases (0.331) — see the noise-corrected estimates next.")}
{fig("fig_noise_honest_gini_2013-2024.png","Noise-honest concentration. Left: temporal Gini rarefied to a common event count. Right: pooled Gini, naïve vs split-sample de-noised — cases barely move, confirming the case concentration is real.")}
{fig("fig_outcome_denoise_2013-2024.png","De-noising the outcome concentration. Left: rarefaction — abandonment far above the constant-rate null (+0.11); TB deaths only modestly. Right: under unbiased restriction the ordering abandonment > deaths > cases holds.")}
{fig("fig_concentration_comparison_2013-2024.png","Geographic concentration of the three lenses, naïve vs de-noised (split-sample cross-fit), age-standardised. Rarer events inflate the naïve Gini; after correction, treatment abandonment is the most concentrated (0.40), above TB mortality (0.34) and TB cases (0.32). Dashed line = the de-noised case level.")}
{fig("fig_death_sim_integrated_2013-2024.png","TB-mortality concentration by marker, de-noised and age-standardised. The integrated TBWeb+SIM marker raises the de-noised mortality Gini from 0.29 (below cases) to 0.34 (at the incidence level). Whether this excess is TB-specific is tested in Appendix E.")}

<div class="qbox"><span class="q">P2 — Where, and is it the socially vulnerable areas?</span></div>
<h3>4.2 Place social vulnerability explains the map, lens-specifically</h3>
<p>An exploratory screen of candidate variables (Figure 11; it also motivated the domain choices — race and population
density were excluded, Appendix D) shows every variable tracks <b>incidence</b> far more than abandonment, and TB mortality
per notified case essentially not at all; income alone is a weak discriminator, so the value comes from the combined index. Modelling each outcome as a GAM (P-splines, k = 3) of the
vulnerability percentile (Figure 12): TB <b>incidence rises</b> with vulnerability (R² = 0.98, ~2.3-fold), <b>abandonment is
a threshold</b> (flat to ~the 68th percentile then rising — the one non-linear lens), <b>TB mortality as a proportion of
notified cases is flat</b> (and slightly lower once age-adjusted), while the <b>TB-mortality rate per population rises</b>
(R² = 0.96), carried by incidence. One counter-intuitive detail — richer areas showing slightly higher TB mortality per
notified case — is <b>age confounding</b>: TB patients in richer areas are much older; once age is held constant the
income–mortality slope reverses to the expected protective direction (crude 5.1% → 5.6%, age-adjusted 4.7% → 3.8%;
Figure 13). At the unit level the population-weighted composite correlates (age-standardised) <b>+0.20</b> with incidence,
<b>+0.08</b> with abandonment and the TB-mortality rate, and <b>0.00</b> with TB mortality per notified case — vulnerable
areas carry more TB deaths per population (via incidence) but not a higher lethality per diagnosed case. The case-weighted
minus population-weighted value is positive — cases fall on the more-deprived micro-sectors the neighbourhood average hides
(the empirical justification for sector-anchoring). The composite reproduces the official IPVS 2022 ordering (Spearman
0.73; Appendix C).</p>
<p><b>Domain by domain</b> (age-standardised, unit level), the five components contribute unequally and tell a coherent
story. The <b>favela / urban-agglomeration</b> marker is the single strongest TB discriminator — Spearman <b>+0.35</b> with
incidence, +0.27 with the TB-mortality rate, and +0.17 with abandonment — TB concentrates in the densest precarious
settlements. <b>Income</b> is next for incidence (+0.27) and is the material-deprivation backbone that anchors the index to
the official IPVS (income alone reproduces the IPVS ordering at ρ = 0.81). <b>Intra-household crowding</b> contributes
moderately (+0.16 with incidence, +0.08 with abandonment). <b>Adult illiteracy</b> is a strong general-deprivation marker
(IPVS ρ = 0.68) but tracks TB only weakly (+0.08 with incidence). <b>Inadequate sanitation</b> is near-universal in urban
São Paulo, so its sector-level variation is low and concentrated in the rural interior, and it is essentially uncorrelated
with TB incidence (−0.07): it sharpens the deprived tail of the composite without being a TB gradient in itself. No single
domain suffices — the composite deliberately combines a TB-specific axis (favela), the material-deprivation backbone
(income), and the markers (illiteracy, sanitation, crowding) that fill in the most-deprived tail.</p>
{fig("fig_vulnerability_vs_ltfu_2013-2024.png","Exploratory variable screening (pre-composite): vulnerability variables vs the abandonment hotspots — left, standardized difference (Cohen's d); right, correlation with incidence, abandonment and TB mortality. Race and population density were also screened but are excluded from the composite (race redundant, ρ 0.98; density a transmission rather than a deprivation construct, Appendix D) and are not shown here. All variables track incidence far more than abandonment. Supplementary / exploratory — not a main-paper figure.")}
{fig("fig_vuln_gam_2013-2024.png","GAM-smoothed dose-response (P-splines, k=3; 95% CI; decile points overlaid). A) incidence — rises (R²=0.98, ~2.3×); B) abandonment — threshold (~p68, the one non-linear lens); C) TB mortality (% of notified) — flat, age-adjusted below crude; D) TB-mortality rate per population — rises (R²=0.96), driven by incidence.")}
{fig("fig_income_ageadj_2013-2024.png","TB mortality (% of notified) vs income percentile, crude vs age-adjusted (GAM). The crude positive slope is age confounding — richer areas have older TB patients; age-adjusted, the slope reverses to protective.")}
<h3>4.3 Choropleth maps by geographic unit</h3>
<p>The four quantities mapped as choropleths (Figure 14, Greater SP + Baixada; Figure 15, whole state). Social vulnerability
is lowest in the affluent capital core and rises toward the periphery; TB incidence and the TB-mortality rate concentrate
in the eastern/southern periphery and along the Baixada coast; abandonment forms its own patches — including central
districts — that only partly overlap incidence, the divergence quantified in P3.</p>
{fig("fig_unit_heatmaps_metro_2013-2024.png","Choropleth maps by unit — Greater São Paulo + Baixada Santista: social vulnerability, and the age-standardised TB incidence, abandonment, and TB-mortality rate per population. Full municipal territory is the grey base, so the Serra do Mar belt between metro and coast is filled by the correct city outlines rather than left blank.")}
{fig("fig_unit_heatmaps_state_2013-2024.png","Choropleth maps by unit — whole São Paulo State (same four quantities, age-standardised; units are small at this scale — see the metropolitan view above).")}

<div class="qbox"><span class="q">P3 — Do the three lenses pick out the same places?</span></div>
<h3>4.4 Three distinct geographies, with distinct structural profiles</h3>
<p>The incidence, abandonment and TB-mortality lenses identify <b>largely different places</b> (Figures 16–19): abandonment
overlaps incidence only partly (Jaccard 0.22), TB mortality less so (0.15), and the two outcome lenses overlap each other
least of all (0.13). Combining them would blur three distinct signals.</p>
{fig("fig_outcome_maps_separate_2013-2024.png","The two adverse-outcome geographies side by side, age-standardised: treatment abandonment (left) and TB mortality as % of notified cases (right). Combining them would blur two distinct signals.")}
{fig("fig_inc_vs_aband_2013-2024.png","Incidence vs abandonment hotspots (age-standardised; state + metro zoom). Abandonment surfaces a partly distinct set of treatment-retention-failure areas (Jaccard 0.22).")}
{fig("fig_inc_vs_death_2013-2024.png","Incidence vs TB-mortality hotspots (age-standardised; mortality as % of notified cases). A partly distinct set of areas (Jaccard 0.15).")}
{fig("fig_aband_vs_death_2013-2024.png","Abandonment vs mortality hotspots overlap little (Jaccard 0.13) — distinct geographies, best targeted separately.")}
<p>The three geographies also differ <b>structurally</b> (Figure 20). The <b>incidence-only</b> areas are the most deprived
(composite +0.26), most favela (22% vs ~6%), poorest (R$2,527), most in the State capital (56%), with younger patients
(40 vs 43) — the urban transmission belt. The <b>abandonment-only</b> areas are not especially deprived (composite −0.09,
below the state reference), have the <i>highest</i> income (R$4,417) and little favela, and are more dispersed — treatment
abandonment is its own geography, not where the poverty is. The <b>mortality-only</b> areas are structurally average
(composite, income and patient age ≈ the state reference) but combine <i>low</i> incidence (30/100k) with a <i>high</i>
proportion of deaths (8.7%); we report this descriptively and do not infer a mechanism here. In short: three lenses, three
geographies, three targeting maps — case-finding (incidence, favela/periphery), retention (abandonment, independent of
place poverty), and the mortality geography (distinct again).</p>
{fig("fig_lens_characterisation_2013-2024.png","What differentiates the three outcome geographies. Each lens-only hotspot group profiled by place vulnerability, favela share, household income, share in the State capital, mean patient age, and TB incidence (dashed line = state reference). Incidence-only = poor/favela/capital/young; abandonment-only = higher-income, dispersed; mortality-only = structurally average, low incidence with high mortality-%.")}
<p>Consolidated at the readable metropolitan scale (Figure 21), incidence hotspots sit in the dense urban TB belt and along
the Baixada coast, abandonment hotspots form their own patches, and TB-mortality-rate hotspots are dispersed differently
again.</p>
{fig("fig_hotspots_3lens_metro_2013-2024.png","Priority areas by lens at the metropolitan scale (Greater São Paulo + Baixada Santista), age-standardised: incidence, abandonment (LTFU), and TB-mortality-rate hotspots (per population; selected units coloured by rate, the rest grey). Full municipal territory shown as the grey base.")}

<div class="qbox"><span class="q">P4 — Is the pattern consistent over time?</span></div>
<h3>4.5 Concentration and targeting are stable over 12 years</h3>
<p>Both the degree of concentration and the geographic targeting are remarkably stable: the annual Gini stays in a narrow
band (0.36–0.39) and year-to-year hotspot overlap is consistently 0.44–0.48 (mean 0.46; Figure 22) — the same areas persist
(Figure 23). This is not limited to consecutive years: the rank correlation is essentially flat across lags of 1–11 years
(Figure 24). The single-year value (ρ ≈ 0.50) is partly small-area Poisson noise; once that is reduced (higher case
volume, multi-year pooling) the underlying stability rises to ρ ≈ 0.75 (Figure 25).</p>
<p>The <b>COVID-19 pandemic was a natural stress test</b>: in 2020 adult TB notifications fell to their lowest of the series
(12,047, ~10% below the neighbouring years), yet the concentration was the <b>highest</b> recorded (Gini 0.391, top-20%
share 43.4%; Figure 22). The pandemic cut the <i>volume</i> of TB but not its <i>geography</i> — notifications dropped while
the hotspots stayed locked on the same places, and the targeting recovered unchanged afterwards.</p>
<p>The <b>adverse-outcome geography is stable too</b>: treatment-abandonment hotspots do not reshuffle from year to year
(disattenuated autocorrelation ≈ 0.65 across the decade), and the apparent post-2020 dip in outcome concentration is largely
an event-count artefact, not real dispersion (Figure 26). The persistence holds for the two lenses the de-noising shows to
be real — incidence and abandonment.</p>
{fig("fig_gini_stability_over_time_2013-2024_adults.png","Annual Gini (left) and year-to-year Jaccard overlap of independently re-selected top-20% hotspots (right). Both stable across 12 years; the COVID-19 years are shaded — 2020 had the fewest notifications but the highest concentration.")}
{fig("fig3_stability_adult_2013-2024.png","Temporal stability: number of years (of 12) each area was selected. Persistently-selected hotspots cluster in the urban core.")}
{fig("fig_temporal_autocorrelation_2013-2024.png","Temporal autocorrelation: year×year Spearman correlation of unit rates (left) and correlation/overlap by lag (right) — nearly flat across 1–11 years.")}
{fig("fig_autocorr_by_scale_2013-2024.png","Sensitivity of the rank correlation to case volume and time window. The ~0.5 single-year value reflects small-area noise; the underlying stability is ≈0.75.")}
{fig("fig_outcome_temporal_2013-2024.png","Temporal de-noising of the adverse outcomes: sliding-window concentration (left) and the disattenuated abandonment autocorrelation (right, ≈0.65 across the decade) — abandonment hotspots are stable, not reshuffling.")}

<h2>5. Key findings</h2>
<ul>
<li><b>(P1) Strong, stable concentration:</b> top 20% of adult population → 39.3% of cases (Gini 0.367); de-noised case Gini ≈ 0.32. <b>Abandonment is the robust, TB-specific adverse outcome</b> (de-noised 0.41 vs 0.32), the strongest actionable programmatic signal.</li>
<li><b>(P2) Place vulnerability is lens-specific:</b> incidence rises with vulnerability (~2.3×, R²=0.98); abandonment is a threshold (~p68); TB mortality per notified case is flat once age-adjusted, while the TB-mortality rate per population rises via incidence. Income is protective once age is accounted for. Cases fall on the more-vulnerable micro-sectors (case- &gt; population-weighted) — anchor at the sector. The composite reproduces the official IPVS 2022 (Spearman 0.73).</li>
<li><b>(P3) Three distinct geographies:</b> incidence, abandonment and TB mortality overlap little (Jaccard 0.22 / 0.15 / 0.13) and differ structurally — incidence-only = poor/favela/capital/young; abandonment-only = higher-income, dispersed; mortality-only = structurally average, low incidence with high mortality-%. Three targeting maps, not one.</li>
<li><b>(P4) Stability:</b> annual Gini 0.36–0.39, Jaccard 0.44–0.48, de-noised rank-stability ≈ 0.75 — today's priority areas persist, enabling multi-year planning.</li>
<li><b>Robustness:</b> all rates are age-standardised (incidence concentration unchanged, Gini 0.331→0.329); conclusions hold across unit scales (Appendix A) and under a purpose-built regionalisation (Appendix B); the favela domain is examined as a sensitivity (Appendix D); the excess mortality concentration is general vulnerability, not TB-specific (negative control, Appendix E).</li>
</ul>

<h2>6. Discussion and limitations</h2>
<p>The decade-long stability strengthens the case for geographically-targeted ACF: today's priority areas are very likely
to remain so. The outcome analysis adds a complementary rationale — not only "where to find cases" (incidence) but "where
the programme is failing patients" (abandonment) — and the vulnerability analysis explains the gradient, lens by lens:
incidence is a transmission gradient (target across the whole range), abandonment a threshold (concentrate retention
support in the more-vulnerable half), and TB mortality per diagnosed case an individual rather than a place phenomenon —
while the TB-mortality rate per population follows incidence. Because the three lenses pick out largely different places
with different structural profiles, a single incidence map is insufficient for the programme's distinct goals.</p>
<p><b>Limitations.</b> (i) Population denominators and vulnerability are fixed at the 2022 Census; absolute rates for
earlier years carry a small bias, though concentration (relative) is robust. (ii) CNEFE 2022 geocodes all years. (iii)
Outcome proportions are over evaluated cases; recent cohorts have some still in treatment. (iv) The SIM linkage covers a
subset of deaths; the integrated marker mitigates but does not eliminate this. (v) The vulnerability composite is an
equal-weight transparent index; it is externally validated against the official IPVS 2022 (Appendix C), with GeoSES a
secondary cross-check still to be added. (vi) The mortality-only geography is described structurally; we do not have a
diagnostic-delay measure and make no mechanistic claim. (vii) Homeless and incarcerated patients have no residential sector
and are outside this place-based analysis.</p>

<h2>7. Next steps</h2>
<ol>
<li><b>Modelling input:</b> use the hotspots to estimate the proportion of incident adult TB in the high-burden target group — a direct input to the WHO investment-case transmission model.</li>
<li><b>Lens-specific targeting:</b> incidence hotspots for case detection; abandonment hotspots for treatment support/retention; the mortality geography for further characterisation.</li>
<li><b>Secondary cross-check</b> of the composite against GeoSES (IPVS already incorporated, Appendix C).</li>
<li><b>Vulnerability archetypes</b> (favela, degraded inner-city core, urban periphery) to make priority areas interpretable for planners.</li>
</ol>

<h2>8. Reproducibility</h2>
<p>Repository <code>SP-TB-spatial-analyses</code> (branch <code>gsp-vulnerability-typology</code>): geocoding (scripts
20–21, 28–29, 40–41); unit construction + hotspots (48–49); outcome hotspots, mapped separately, + lens characterisation
(50, 91); concentration + temporal stability + autocorrelation (51–55); noise correction / integrated-mortality suite
(57–61); vulnerability screening (63); composite builder, five-domain (89); GAM with P-splines k=3 + age-adjustment (66);
intensity heat-maps (67); metro hotspot maps (69); age-standardisation engine (78); scale sensitivity (79); statewide
regionalisation (83–87); IPVS external validation (88); favela-domain sensitivity (90); this report (68). (A separate
companion analysis of programme fragility along the diagnostic axis — scripts 70–77 — is reported on its own and is not
part of this manuscript base.) All choropleths use a full municipal-territory base layer. Age standardisation is indirect,
to São Paulo State across eight census age bands. Scope throughout: adults ≥15, new+relapse, 2013–2024, adult-population
denominator, units with ≥10 pooled cases.</p>

<h2>Appendix A — Scale sensitivity of the concentration</h2>
<p>The degree of concentration depends on the spatial scale (the modifiable areal unit problem): finer units give higher
Gini. The de-noised incidence Gini falls smoothly from the census sector to the municipality, but TB is concentrated at
every scale and the operational unit sits in the middle of this range (Figure 27). We therefore report the operational
unit and show the full scale curve here rather than claim a single "true" value.</p>
{fig("fig_gini_scale_sensitivity.png","De-noised incidence Gini at four spatial scales (census sector → operational unit → district → municipality). Concentration is real at every scale; finer units give higher Gini (the MAUP). The operational unit is intermediate.")}

<h2>Appendix B — The spatial unit: the operational unit and a regionalisation robustness check</h2>
<p>The primary (operational) unit is an official-geography hybrid — favela/urban community (FCU) with ≥5,000 residents,
otherwise the IBGE neighbourhood (bairro), and in the capital the district — <b>n = 3,014</b>. Its population is
<b>deliberately heterogeneous</b> (median <b>2,872</b> adults, IQR 849–9,294, range 56–618,897; Figure 28A): by type, 1,957
bairros (65%), 1,000 districts (33%) and 57 FCU/favela units (2%). The heterogeneity is driven by the capital — São Paulo
city has <i>no</i> official intra-urban bairro layer, so it collapses to ~118 large districts (median 74,053 adults),
whereas the interior is fine bairros (median 2,622). This — and the absence of any official neighbourhood unit in São Paulo
(the official units are subprefecture, district and census sector) — motivated a second, <i>constructed</i> unit as a
robustness check: a <b>regionalisation</b> (n = 7,310) that is <b>uniform by construction</b> (median 5,329, IQR
3,178–6,336; Figure 28B). The two distributions side by side (Figure 28) make the contrast plain: real IBGE places,
heterogeneous, versus a constructed, uniform unit.</p>
{fig("fig_unit_comparison_distribution_2013-2024.png","The two candidate spatial units compared, on a shared log scale. A) the operational unit (n = 3,014) is heterogeneous — the interior is fine bairros (median 2,622), but the capital collapses to ~118 large districts (median 74,053) for want of an official bairro layer. B) the regionalisation (n = 7,310) is uniform by construction (median 5,329, IQR 3,178–6,336). Real IBGE places (heterogeneous) versus a constructed, uniform unit.")}
<p>São Paulo has no official "neighbourhood" cartographic unit, and the operational unit is heterogeneous in population
because the capital collapses to districts. As a robustness check we built a statewide <b>regionalisation</b> — census
sectors grown into ~5,000-adult, income-homogeneous neighbourhoods, with favela and non-favela regionalised separately so
a favela never merges with an adjacent affluent area (Figure 29), giving far more uniform units (Figure 30). Re-running the
analysis on this constructed unit gives the same concentration and the same temporal conclusions as the operational unit
(Figures 31–32); the geography is not an artefact of the unit definition.</p>
{fig("fig_region_vila_andrade.png","Regionalisation example (Vila Andrade, capital): census sectors grown into ~5,000-adult units, favela (Paraisópolis) and non-favela regionalised separately and coloured by income — the favela is never merged with adjacent affluent Morumbi.")}
{fig("fig_region_sizes.png","Size distribution of the statewide regionalisation: 7,310 units, median ~5,300 adults (IQR 3,200–6,300) — far more uniform than the operational unit.")}
{fig("fig_p1_unit_comparison.png","P1 (concentration) on the operational unit vs the regionalisation: de-noised Gini and Lorenz curves for incidence, abandonment and TB mortality — the same conclusions on both units.")}
{fig("fig_p2_temporal_comparison.png","P4 (temporal stability) on the operational unit vs the regionalisation: annual Gini and year-to-year hotspot Jaccard — same conclusions; the finer regionalisation is slightly noisier year-on-year, as expected.")}

<h2>Appendix C — External validation against the official IPVS 2022 (SEADE)</h2>
<p>Our five-domain composite is validated against the official Índice Paulista de Vulnerabilidade Social (IPVS 2022,
SEADE), an independent sector-level classification (group 1 lowest → 6 highest), merged on the 2022 census sector
(n = 92,250 classified sectors). The composite reproduces the official ordering well (Spearman <b>0.73</b>); on income —
the shared backbone — agreement is near-perfect and strictly monotonic (ρ = 0.81); 86% of our least-vulnerable quintile
falls in IPVS groups 1–2 and 60% of our most-vulnerable quintile in IPVS 5–6 (Figure 33). By domain, income reproduces the
IPVS ordering most closely (ρ = 0.81), then illiteracy (0.68), favela (0.50), crowding (0.37) and sanitation (0.29) —
income and illiteracy carry the agreement, the order one expects of a socioeconomic index. The residual divergence is the
IPVS demographic / life-cycle axis (younger families, older household heads) that we deliberately exclude — confirming our
index is a material-deprivation instrument rather than a life-cycle typology.</p>
{fig("fig_ipvs_validation_2013-2024.png","External validation against the official IPVS 2022 (SEADE), by census sector. A) our composite rises across the six IPVS groups (Spearman 0.73, n=92,250). B) what drives the agreement, by domain — income and illiteracy lead.")}

<h2>Appendix D — Sensitivity to domain choice: favela and population density</h2>
<p>Favela / urban agglomeration is retained as a structural-deprivation domain by design. Because it is also where TB most
concentrates, we show how much the composite depends on it: with favela the TB-incidence dose-response is monotonic to the
top (decile top/base 2.3×) and IPVS agreement is slightly higher (0.73 vs 0.69); without it the gradient saturates (the
most-deprived decile, now loaded on rural illiteracy/sanitation extremes with little TB, dips), top/base 1.8× (Figure 34).
The supervisor can judge the inclusion with both versions in hand; conclusions about the lower deciles are unaffected
either way.</p>
{fig("fig_appendix_favela_sensitivity_2013-2024.png","Sensitivity to the favela domain. A) TB-incidence dose-response with favela in (5 domains, main) vs out (4 domains): favela carries the top of the gradient. B) external agreement with IPVS 2022: favela slightly improves it (0.73 vs 0.69; 60% vs 53% of the most-vulnerable quintile in IPVS Alta/Muito Alta).")}
<p><b>Population density.</b> By the same logic we tested adding population density (residents/km²) as a sixth domain. It
<i>strengthens</i> the TB-incidence gradient — decile top/base rises from 2.3× to <b>2.8×</b> — consistent with TB being a
disease of urban agglomeration, and external agreement with IPVS is essentially unchanged (0.73 → 0.75). But density is
<b>not</b> a deprivation marker: it is slightly <i>negatively</i> correlated with the composite (ρ = −0.20), because São
Paulo's densest sectors are verticalised high-income districts. Including it would therefore make the index partly a
transmission / risk score rather than a vulnerability index. We keep it out of the main composite and make the
density-inclusive (six-domain) version available; <b>whether to include population density is an open question for
discussion, given that TB is epidemiologically a disease of urban agglomeration.</b></p>

<h2>Appendix E — Mortality negative control and age-standardisation robustness</h2>
<p><b>Negative control.</b> Whether the excess concentration of TB mortality is TB-specific is tested by repeating the
analysis for <b>non-TB deaths among the same TB patients</b>: they cluster identically (de-noised 0.35 vs 0.34; equal event
count 0.45 vs 0.45; Figure 35) — the excess mortality concentration is vulnerability-driven, not TB-cause-specific. This is
why the mortality lens is reported separately and not combined with abandonment.</p>
{fig("fig_death_negative_control_2013-2024.png","Negative control (age-standardised): non-TB deaths cluster as much as TB deaths (left, de-noised; right, equal event count, 0.45 vs 0.45) — the excess mortality concentration is vulnerability-driven, not TB-cause-specific.")}
<p>The same holds for the <b>hotspots</b>: the age-standardised TB-death and non-TB-death rate hotspots overlap far more
than the main lenses do (Jaccard 0.34 vs 0.13–0.22) and are structurally near-identical — both concentrate in the
more-vulnerable, higher-favela areas (vulnerability z +0.31 vs +0.26; favela 25% vs 24%, against a state-eligible mean of
+0.09 and 11%; Figure 36). The mortality-rate geography is where vulnerable patients die of anything.</p>
{fig("fig_tb_vs_nontb_death_2013-2024.png","TB-death vs non-TB-death hotspots (age-standardised rates). A) the two sets overlap more than the main lenses (Jaccard 0.34). B) and are structurally near-identical — both concentrate in more-vulnerable, higher-favela areas (dashed = state-eligible mean). The mortality-rate concentration is general vulnerability, not TB-cause-specific.")}
<p><b>Age-standardisation robustness.</b> Crude and age-standardised metrics were compared unit by unit (Figure 37). The
spatial story is robust: age-standardised incidence is rank-identical to crude (Spearman = 1.00) and its Gini is unchanged
(0.331 → 0.329). The vulnerability gradients hold for incidence and, attenuated, for abandonment; for TB mortality the rate
per population strengthens (vulnerable areas are younger) while the proportion of notified cases goes from a weak negative
to 0.00 — the apparent "lower lethality per case in more-vulnerable areas" was entirely an artefact of those areas having
younger TB patients.</p>
{fig("fig_age_standardisation_2013-2024.png","Crude vs age-standardised metrics by geographic unit (indirect standardisation, São Paulo internal reference). Incidence essentially unchanged (ρ=1.00); abandonment shifts slightly; TB mortality shown both ways — the rate per population and the proportion of notified cases — the latter changing most as the older case-mix of less-vulnerable areas is removed.")}

<div class="footer">Unified working manuscript base · São Paulo adult TB spatial concentration, adverse-outcome hotspots, and place social vulnerability, 2013–2024 · WHO TB Screening Investment Case (Brazil). Self-contained file — figures embedded; opens in any browser and prints to PDF.</div>
</div></body></html>"""

H=H.replace("<b>","").replace("</b>","")
out="/tmp/SP_TB_Unified_Report.html"
with open(out,"w") as f: f.write(H)
print("Saved:",out,f"({os.path.getsize(out)/1e6:.1f} MB) — {N[0]} figures")
