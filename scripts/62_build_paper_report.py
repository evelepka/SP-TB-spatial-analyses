"""Comprehensive paper-base report — SP TB spatial analysis, adults 2013-2024.
Self-contained HTML with embedded figures + detailed methodology per process.
"""
import base64, os
FIGDIR = ("/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/"
          "My Drive/WHO modelling Project/SP-TB-spatial-analyses/Figures_2013-2024_adults")
def img(name, alt=""):
    p=os.path.join(FIGDIR,name)
    if not os.path.exists(p): return f'<p style="color:#b00">[missing: {name}]</p>'
    with open(p,"rb") as f: b=base64.b64encode(f.read()).decode()
    return f'<img src="data:image/png;base64,{b}" alt="{alt}">'
def figure(name,num,cap):
    return f'<figure>{img(name,cap)}<figcaption><span class="figlabel">Figure {num}.</span> {cap}</figcaption></figure>'

CSS="""
:root{--navy:#0d2b45;--teal:#028090;--mint:#02c39a;--ink:#1a202c;--muted:#5b6b7a;--line:#e2e8f0;--callout:#f0f9f7;--amber:#9a6700;--amberbg:#fff8e6;}
*{box-sizing:border-box}
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);line-height:1.65;margin:0;background:#f4f6f8;}
.page{max-width:880px;margin:0 auto;background:#fff;padding:60px 74px;box-shadow:0 1px 4px rgba(0,0,0,.08);}
h1{font-size:29px;line-height:1.22;color:var(--navy);margin:0 0 6px;}
.sub{font-size:15px;color:var(--teal);font-weight:600;margin:0 0 4px;}
.meta{font-size:12.5px;color:var(--muted);margin:0 0 6px;}
h2{font-size:21px;color:var(--navy);margin:40px 0 8px;padding-bottom:6px;border-bottom:2px solid var(--teal);}
h3{font-size:16.5px;color:var(--navy);margin:24px 0 6px;}
h4{font-size:14.5px;color:var(--teal);margin:18px 0 4px;}
p{margin:9px 0;} ul,ol{margin:9px 0;padding-left:22px;} li{margin:4px 0;}
code{background:#eef2f5;padding:1px 5px;border-radius:4px;font-size:12.5px;}
.callout{background:var(--callout);border:1px solid #cfe9e3;border-left:4px solid var(--mint);border-radius:8px;padding:12px 20px;margin:16px 0;}
.callout h3{margin-top:0;color:var(--teal);}
.optional{background:var(--amberbg);border:1px solid #f0e0b0;border-left:4px solid var(--amber);border-radius:8px;padding:6px 20px;margin:16px 0;}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:13px;}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top;}
th{background:var(--navy);color:#fff;font-weight:600;}
tr:nth-child(even) td{background:#f7fafc;}
figure{margin:20px 0;text-align:center;}
figure img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px;}
figcaption{font-size:12px;color:var(--muted);margin-top:7px;text-align:left;line-height:1.45;}
.figlabel{font-weight:600;color:var(--navy);}
.statgrid{display:flex;flex-wrap:wrap;gap:11px;margin:14px 0;}
.stat{flex:1 1 150px;background:#0d2b45;color:#fff;border-radius:8px;padding:11px 13px;}
.stat .v{font-size:22px;font-weight:700;color:var(--mint);}
.stat .l{font-size:11.5px;color:#cfe0ea;line-height:1.3;}
.footer{margin-top:44px;padding-top:14px;border-top:1px solid var(--line);font-size:11.5px;color:var(--muted);}
@media print{body{background:#fff}.page{box-shadow:none;max-width:none;padding:0 6px;}h2{page-break-after:avoid}figure{page-break-inside:avoid}}
"""

H=f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Geographic concentration of TB in São Paulo state, 2013–2024</title>
<style>{CSS}</style></head><body><div class="page">

<p class="sub">WHO TB Screening Investment Case · Brazil — working manuscript base</p>
<h1>Geographic concentration, temporal stability, and outcome-based hotspots of tuberculosis in São Paulo State, 2013–2024</h1>
<p class="meta">Adults (≥15 years), new and relapse cases · Evelyn Lepka de Lima</p>

<div class="statgrid">
 <div class="stat"><div class="v">177,013</div><div class="l">adult TB cases geocoded (2013–2024)</div></div>
 <div class="stat"><div class="v">35.9M</div><div class="l">adult (≥15) population (IBGE 2022)</div></div>
 <div class="stat"><div class="v">332</div><div class="l">priority hotspot areas</div></div>
 <div class="stat"><div class="v">39.3%</div><div class="l">of cases in 20% of population</div></div>
</div>

<div class="callout"><h3>Summary</h3>
<p>Using 12 years of individual TB notifications from the São Paulo State surveillance system (TBWeb), geocoded to the
census-sector level via the IBGE national address registry (CNEFE 2022), we show that adult tuberculosis in São Paulo
state is <b>strongly and stably geographically concentrated</b>. The top 20% of the adult population by local TB rate
holds <b>39.3% of cases</b> (Gini 0.367). This concentration is <b>remarkably stable across 2013–2024</b> (annual Gini
0.36–0.39; year-to-year Jaccard overlap 0.44–0.48), supporting multi-year programmatic targeting. We then ask whether
adverse treatment outcomes are even more concentrated — and de-noise every comparison, because rarer events inflate
concentration indices. After noise correction, <b>treatment abandonment is genuinely the most concentrated outcome</b>
(de-noised Gini 0.41 vs 0.32 for cases) and is temporally stable, making it the strongest programmatic signal. TB
<b>mortality</b>, measured with an integrated TBWeb + civil-registry (SIM) death marker, is concentrated at about the
incidence level (de-noised Gini 0.33); a <b>negative control</b> (non-TB deaths among TB patients) shows this excess
mortality concentration is <b>general vulnerability/lethality, not TB-specific</b>. Mapped separately rather than
combined, abandonment hotspots and mortality hotspots are <b>nearly independent geographies</b> (Jaccard 0.11 with each
other) — each surfacing distinct areas the incidence lens misses: treatment-retention failures and high-lethality areas
respectively.</p></div>

<h2>1. Background and objective</h2>
<p>Brazil is among the highest-burden tuberculosis (TB) countries, and São Paulo — the most populous state — accounts
for a large share of national notifications. Active case finding (ACF) is resource-intensive and cost-effective only
when correctly targeted. Within the WHO TB Screening Investment Case, we require a <b>reproducible, methodologically
defensible</b> way to (i) identify geographic priority areas for TB screening, (ii) quantify how concentrated TB is and
whether that concentration is stable enough to plan multi-year programmes, and (iii) test whether targeting on
<i>incidence</i> alone misses high-vulnerability areas that could instead be revealed by <i>adverse outcomes</i>.</p>

<h2>2. Data sources</h2>
<table>
<tr><th>Source</th><th>Use</th><th>Detail</th></tr>
<tr><td><b>TBWeb</b> — São Paulo State TB notification system</td><td>Individual TB cases: residential address, dates, age, sex, clinical form, HIV, treatment outcome</td><td>Original cohort 1980–2025; analysis 2013–2024 (complete coverage from 2013)</td></tr>
<tr><td><b>SIM</b> — Mortality Information System (civil registry), linked to TBWeb</td><td>Cause of death from the death certificate (underlying cause + all certificate lines), to build an integrated TB-death marker</td><td>10,056 deaths linked to the cohort by notification number; full ICD-10 lines used to flag TB anywhere on the certificate</td></tr>
<tr><td><b>IBGE CNEFE 2022</b> — National Address File for Statistics</td><td>Gold-standard address → census-sector geocoding reference</td><td>~10 million SP addresses, collected face-of-block during the Census</td></tr>
<tr><td><b>IBGE Census 2022</b></td><td>Census-sector boundaries and population denominators (total and by age group)</td><td>~100k sectors; adult (≥15) population from demographic aggregates V01034–V01041</td></tr>
</table>

<h2>3. Methods</h2>

<h3>3.1 Study population</h3>
<p>We included TB cases notified in São Paulo state in <b>2013–2024</b> (the period of complete TBWeb coverage; ~19,000–21,000
notifications/year statewide), restricted to <b>adults aged ≥15 years</b> and to <b>new and relapse cases</b>
(<code>case_type ∈ {{NOVO, RECIDIVA}}</code>), with a standard residential address recorded
(<code>address_type = ENDERECO PADRAO</code>). Detentees (prison address type) and people with no fixed residence were
handled separately and are not part of this community analysis.</p>

<h3>3.2 Geocoding pipeline (address → census sector)</h3>
<p>We deliberately did <b>not</b> use the postal code (CEP) as the basis for geocoding, because a substantial share of
TBWeb records have missing, truncated, or incorrect CEP — disproportionately in peripheral neighbourhoods and favelas,
exactly the areas of interest. Instead we matched the <b>textual address (street + number + neighbourhood)</b> against
the CNEFE 2022 reference, after a careful address-cleaning step.</p>
<h4>Address cleaning</h4>
<ul>
<li><b>Leading numbers before the street type</b> (e.g. "194 RUA X", "1ª RUA Y") — stripped via an ordinal/number regex.</li>
<li><b>Duplicated street tokens</b> ("RUA RUA", repeated "R."/"AV.") — collapsed.</li>
<li><b>Address complements</b> (apto, bloco, casa, fundos, etc.) — removed.</li>
<li><b>Common typos and abbreviations</b> in street names — corrected against a curated map.</li>
<li>House number normalised (first numeric token; empty/garbage → no number).</li>
</ul>
<h4>Multi-level matching cascade (per residence municipality)</h4>
<ol>
<li><b>T1 — exact:</b> street + number found in CNEFE → sector of that exact address.</li>
<li><b>T2 — street:</b> street found (most frequent sector for that street).</li>
<li><b>T3 — fuzzy:</b> approximate street match (token-set ratio ≥ 88).</li>
<li><b>T4 — neighbourhood fallback:</b> TBweb <i>bairro</i> matched to a CNEFE neighbourhood centroid (used only as a fallback, not in the primary spatial analysis).</li>
</ol>
<p>Cases matched at <b>T1–T3</b> (census-sector resolution) were retained for the spatial analysis. Coverage was
consistent across all 12 years and across regions: <b>Greater São Paulo 90.1%, Baixada Santista 92.8%, interior
89.5%</b> (T1–T3). Crucially, the per-year geocoding rate was flat (89–92%) throughout 2013–2024, so the time series is
not biased by changing geocoding completeness.</p>

<h3>3.3 Geographic unit construction</h3>
<p>Census sectors are too small and noisy to be operational units. We aggregated sectors into epidemiologically
meaningful units: <b>Functional Census Units (FCU/UCF)</b> with ≥5,000 residents where available; otherwise
<b>neighbourhoods (bairros)</b>, and for the São Paulo capital, <b>districts/subdistricts</b>. This yields ~3,014
candidate units covering the state. The <b>population denominator is the adult (≥15) population</b> of each unit
(IBGE 2022); sector eligibility used total population ≥100 residents.</p>

<h3>3.4 Hotspot selection algorithm</h3>
<ol>
<li><b>Quality filter:</b> retain T1–T3 geocoded adult cases.</li>
<li><b>Minimum volume:</b> units must have ≥10 adult TB cases pooled over 2013–2024 (ensures a stable rate; eliminates weak-denominator noise).</li>
<li><b>Rate ranking:</b> eligible units ranked by 12-year pooled adult TB incidence rate (cases ÷ adult population ÷ 12 × 100,000).</li>
<li><b>Population window:</b> units added in descending-rate order until cumulative adult population reaches <b>20%</b> of the state total — balancing epidemiological yield and ACF feasibility.</li>
</ol>

<h3>3.5 Concentration indices (Lorenz / Gini)</h3>
<p>For each event type (cases, TB deaths, abandonments), units were ranked by the per-capita event rate and we plotted
the cumulative share of events against the cumulative share of (adult) population (a Lorenz curve), summarised by the
<b>Gini coefficient</b> and the share captured by the top 20% of population. To avoid <b>artificially inflating</b>
concentration, the Lorenz/Gini was computed over units with <b>≥10 cases</b> only (small, weak-denominator units whose
"zero events" reflect absence of cases rather than a true low rate were excluded; these were 67% of units but only ~2%
of cases).</p>

<h3>3.6 Temporal analysis (concentration and stability over time)</h3>
<p>To test whether concentration and targeting are stable over time, for <b>each year 2013–2024</b> we (i) recomputed
the <b>annual Gini</b> (ranking units by that year's rate — a year-specific concentration measure), and (ii)
<b>re-selected the top-20%-population hotspots independently each year</b>. Year-to-year stability was measured by the
<b>Jaccard index</b> of overlap between consecutive years' selected sets. The candidate unit frame was held fixed
(units with ≥10 pooled cases) so years are comparable; the concentration value and the hotspot selection are
year-specific. We additionally examined temporal autocorrelation: for every pair of years we computed the
Spearman correlation of unit-level incidence rates and the Jaccard overlap of selected hotspots, summarised as a
function of the lag (years apart), to test whether the resemblance decays over time or persists across the whole period. Because single-year rates in small areas are subject to Poisson noise, we also examined how this correlation varies with the case volume per unit (case-count thresholds) and with multi-year pooling.</p>

<h3>3.7 Outcome-based hotspots</h3>
<p>Because incidence (cases/population) may under-count high-vulnerability areas that <b>under-notify</b>, we defined an
alternative based on <b>adverse treatment outcomes among notified cases</b> — a signal robust to differential
ascertainment, since it measures what happens to patients who <i>were</i> captured. The primary <b>adverse marker = TB
death (Óbito TB) + treatment abandonment (Abandono + Abandono Primário)</b>, expressed as a proportion of
<b>evaluated cases</b> (those with a definitive outcome). Poor-outcome hotspots were selected by ranking units (≥10
cases and ≥10 evaluated) by adverse-outcome % up to a 20% population window, and compared with incidence hotspots
(overlap, Jaccard). A sensitivity analysis added non-TB deaths to the adverse marker.</p>

<h3>3.8 Integrated mortality and noise correction</h3>
<p><b>Integrated TB-death marker.</b> The TBWeb treatment outcome captures deaths during treatment but classifies cause
clinically; the civil registry (SIM) records the official death certificate but, in this linkage, covers a subset. We
therefore defined TB death as a <b>union of both sources</b>: TBWeb <code>Óbito TB</code> <b>OR</b> tuberculosis (ICD-10
A15–A19) recorded <b>anywhere on the death certificate</b> (underlying cause or any certificate line). The "any line"
rule deliberately recovers HIV/TB co-infection deaths that are coded to HIV (B20–B24) as the underlying cause but list
TB as a contributing cause — these would vanish under an underlying-cause-only definition. This yields ~11,010 adult TB
deaths (2013–2024) versus 9,799 from TBWeb alone (+12%).</p>
<p><b>Why de-noise.</b> Event counts in small areas are subject to Poisson sampling noise, which (i) <b>inflates</b>
concentration indices — the fewer the events, the higher the Gini purely by chance — and (ii) <b>attenuates</b>
correlations over time. A naïve comparison of cases (abundant) with deaths or abandonments (rarer) is therefore
confounded: the rarer outcome looks more concentrated even if the underlying geography is identical. We applied four
corrections so that every concentration claim is "noise-honest":</p>
<ul>
<li><b>Rarefaction.</b> Down-sample the more-common event to the rarer event's count (a constant-rate null), and
down-sample every time window to a common count, so concentration is compared at <b>equal noise</b> rather than equal
calendar coverage.</li>
<li><b>Split-sample (cross-fit) Gini.</b> Rank units on one random half of the events and read the Lorenz value from
the <b>other</b> half. Because the ranking noise and the value noise are independent, noise cannot manufacture spurious
concentration. This is a conservative, de-noised estimate of the true Gini.</li>
<li><b>Disattenuation.</b> Divide the observed temporal autocorrelation by the split-half reliability of each window
(Spearman–Brown), recovering the true (noise-free) year-to-year correlation.</li>
<li><b>Negative control.</b> Repeat the mortality-concentration analysis for <b>non-TB deaths among the same TB
patients</b>. If the excess concentration of TB deaths were TB-specific, non-TB deaths should be diffuse; if instead it
reflects where vulnerable patients die of any cause, the two will coincide.</li>
</ul>

<h2>4. Results</h2>

<h3>4.1 TB is strongly concentrated</h3>
<p>Adult TB cases are far more concentrated than population (Figure 1): the top 20% of the adult population by local TB
rate accounts for <b>39.3% of cases</b> (Gini = 0.367). 332 areas were selected as hotspots (20% of adult population).</p>
{figure("fig1_lorenz_adult_2013-2024.png",1,"Lorenz curve of adult TB case concentration, São Paulo state 2013–2024. Geographic units ranked from highest to lowest adult incidence rate. Gini = 0.367; top 20% of adult population → 39.3% of adult cases.")}

<h3>4.2 Selected hotspot areas</h3>
{figure("fig2_map_adult_2013-2024.png",2,"The 332 selected adult TB hotspot areas (20% of adult population, 39.3% of cases). Colour = 12-year pooled adult incidence rate per 100,000/year.")}

<h3>4.3 Selected vs non-selected areas</h3>
<p>Selected areas have ~2–3× the incidence of non-selected areas within the same region (Figure 3, Table A–B). The
São Paulo urban agglomeration + Baixada Santista corridor concentrates the large majority of hotspots; the interior
contributes a small number of high-rate units.</p>
{figure("table_four_groups_adult_2013-2024.png",3,"Four-group comparison (selected vs non-selected × metropolitan vs interior), adults 2013–2024. Population and case shares relative to the whole state; rates per 100,000/year.")}
{figure("table_metro_adult_2013-2024.png",4,"São Paulo urban agglomeration: selected (254 areas; 18.9% of adult population, 37.1% of cases, 80/100k/yr) vs non-selected.")}
{figure("fig4_table_adult_2013-2024.png",5,"Characteristics of selected vs non-selected areas (adults 2013–2024): demography, HIV, clinical form, case-finding mode, and treatment outcomes.")}

<h3>4.4 Concentration and stability are stable over 12 years</h3>
<p>Both the degree of concentration and the geographic targeting are remarkably stable across 2013–2024 (Figure 6).
The annual Gini stays in a narrow band (<b>0.36–0.39</b>), with a slight peak in 2020 (0.391) consistent with COVID-19
disruption of notification, and a gentle softening thereafter. Year-to-year overlap of the selected hotspots is
consistently <b>0.44–0.48</b> (mean 0.455) — the same areas are selected, year after year.</p>
{figure("fig_gini_stability_over_time_2013-2024_adults.png",6,"Left: annual Gini of adult TB concentration (recomputed each year). Right: year-to-year Jaccard overlap of independently re-selected top-20% hotspots. Both stable across 12 years; no discontinuity.")}
{figure("fig3_stability_adult_2013-2024.png",7,"Temporal stability map: number of years (out of 12) each area was selected. Persistently-selected ('iron') hotspots cluster in the São Paulo urban core.")}
<p>This persistence is not limited to consecutive years. The Spearman correlation of unit rates and the Jaccard
overlap of selected hotspots are essentially flat across all lags from 1 to 11 years (Figure 8): the resemblance
between 2013 and 2024 (lag 11; Spearman 0.45, Jaccard 0.43) is almost identical to that between consecutive years
(lag 1; Spearman 0.50, Jaccard 0.46). The hotspot pattern does not drift — an area that is high-burden in one year
tends to remain so a decade later.</p>
{figure("fig_temporal_autocorrelation_2013-2024.png",8,"Temporal autocorrelation of adult TB hotspots. Left: year × year Spearman correlation of unit incidence rates (all year-pairs). Right: mean rate correlation (Spearman) and hotspot overlap (Jaccard) as a function of the lag; at this scale both are nearly flat across lags of 1–11 years (the level partly reflects small-area noise — see Figure 9).")}
<p>The year-to-year rank correlation itself (Spearman ρ ≈ 0.50 at lag 1) is partly attenuated by Poisson noise in
single-year rates of small areas, which carry few cases per year. When this noise is reduced — by restricting to
higher-case-volume units or by pooling years into multi-year windows — the correlation rises substantially toward the
underlying stability (Figure 9): from ρ ≈ 0.50 (units with ≥10 cases) to ρ ≈ 0.74 (units with ≥50 cases) and ρ ≈ 0.76
(4-year windows). This indicates that the true spatial pattern is highly stable (ρ ≈ 0.75), and that a modest genuine
decay — masked at the noisy single-year / small-area level — becomes visible once noise is removed (ρ ≈ 0.74 → 0.64
over the decade for units with ≥50 cases). Larger areas help only insofar as they carry more cases: municipalities,
many of which are small, do not (ρ ≈ 0.41), confirming that case volume — not area size per se — drives the noise.</p>
{figure("fig_autocorr_by_scale_2013-2024.png",9,"Sensitivity of the temporal rank correlation to spatial scale and time window. Left: Spearman autocorrelation by lag rises as units carry more cases (bairro/FCU ≥10 → ≥30 → ≥50); municipality ≥10 is lower because many municipalities are small. Right: pooling years into longer windows also raises the consecutive-period correlation. The ~0.5 single-year value reflects small-area Poisson noise; the underlying spatial stability is ≈0.75.")}

<h3>4.5 Adverse-outcome concentration — and what survives noise correction</h3>
<p>At face value, adverse outcomes look more concentrated than cases: the top 20% of the population holds 40.4% of
cases but 44.8% of TB deaths and 50.6% of abandonments, with the Gini rising from 0.33 (cases) to 0.41 (deaths) to 0.48
(abandonment) (Figure 10). But deaths and abandonments are rarer than cases, and rarer events inflate the Gini, so this
naïve ordering could be a sampling artefact. We therefore de-noised every comparison.</p>
{figure("fig_concentration_lorenz_2013-2024.png",10,"Naïve concentration of cases vs adverse outcomes (units with ≥10 cases). TB deaths (Gini 0.414) and abandonment (Gini 0.477) appear markedly more concentrated than notified cases (Gini 0.331) — but see the noise-corrected estimates below.")}
<p>Two corrections matter. Ranking units on one half of the events and reading the value from the other half
(split-sample cross-fit) removes the inflation from noise-driven ranking; and rarefying every time window to a common
event count removes the confounding of calendar-time comparisons by changing event volumes. After both, the picture is
cleaner (Figure 11): the <b>case</b> concentration is essentially noise-free and <b>stable across the decade</b>
(de-noised Gini ≈ 0.32, flat once windows carry equal events), while the apparent <b>decline</b> in outcome
concentration after 2020 is shown to be largely an artefact of rising event counts (more TB notified post-COVID → fewer
"noise" inflation → lower naïve Gini), not a real dispersion.</p>
{figure("fig_noise_honest_gini_2013-2024.png",11,"Noise-honest concentration. Left: temporal Gini rarefied to a common event count — the case concentration is flat and the abandonment 'decline' shrinks to roughly one-third its naïve size once noise is held constant. Right: pooled Gini, naïve vs split-sample de-noised — cases barely move (abundant events, little noise), confirming the case concentration is real.")}
<p><b>Abandonment is genuinely the most concentrated outcome.</b> It survives every de-noising test: rarefaction (its
Gini is +0.11 above the constant-rate null, far beyond sampling noise), unbiased restriction to higher case-count units
(the ordering abandonment &gt; deaths &gt; cases holds), and the cross-fit (de-noised Gini 0.41, versus 0.32 for cases)
(Figure 12). It is also temporally stable: the disattenuated year-to-year autocorrelation of abandonment rates is
≈0.65 across the decade, so the abandonment hotspots persist rather than reshuffling — they are a real, durable,
programmatically actionable signal (Figure 15).</p>
{figure("fig_outcome_denoise_2013-2024.png",12,"De-noising the outcome concentration. Left: rarefaction — abandonment (teal) sits far above the constant-rate noise null built from cases (excess +0.11); TB deaths (red) only modestly above. Right: under unbiased restriction to higher case-count units the ordering abandonment > deaths > cases holds throughout.")}

<h3>4.6 Integrated mortality, and a negative control for the death finding</h3>
<p>The mortality result depends critically on how death is measured. Using only the TBWeb clinical "Óbito TB" marker
(~7,400 deaths in eligible units), the de-noised death Gini collapses to 0.28 — <b>below</b> the case concentration —
looking like pure noise. But that marker is incomplete: linking the civil registry (SIM) recovers TB deaths recorded on
the death certificate that TBWeb missed, including HIV/TB co-infection deaths coded to HIV as the underlying cause. With
the <b>integrated TBWeb + SIM marker</b> (~8,500 deaths, "TB anywhere on the certificate"), the de-noised death Gini
rises to <b>0.33 — at the incidence level</b> — and its excess over the noise null nearly triples (+0.021 → +0.058)
(Figure 13). So TB mortality <b>is</b> genuinely spatially concentrated, about as much as incidence; the earlier
"mostly noise" reading was an artefact of an incomplete death marker.</p>
{figure("fig_death_sim_integrated_2013-2024.png",13,"TB-death concentration by death marker, de-noised. Moving from TBWeb-only 'Óbito TB' to the integrated TBWeb+SIM 'TB anywhere on the certificate' marker raises the de-noised death Gini from 0.28 (below cases) to 0.33 (at the case level, dashed line), and the genuine excess over the constant-rate noise null from +0.02 to +0.06.")}
<p><b>But the excess mortality concentration is not TB-specific.</b> As a negative control we repeated the analysis for
<b>non-TB deaths among the same TB patients</b>. If TB deaths clustered because of TB itself, non-TB deaths should be
diffuse. Instead they are <b>just as concentrated</b> as TB deaths (de-noised Gini 0.34 vs 0.33; at a common event
count 0.45 vs 0.44, difference −0.004), and both sit above the case concentration (Figure 14). The interpretation is
that the neighbourhoods where TB patients die of TB are the same neighbourhoods where they die of everything else: the
excess is a signature of <b>concentrated social vulnerability and lethality</b>, not of TB transmission or virulence.
This disciplines the inference — mortality marks vulnerable places, while <b>abandonment</b> remains the one adverse
outcome whose concentration is both genuine and specific to the TB programme.</p>
{figure("fig_death_negative_control_2013-2024.png",14,"Negative control. Left: de-noised Gini — non-TB deaths cluster as much as TB deaths, both just above cases; abandonment stands clearly apart. Right: TB vs non-TB deaths rarefied to a common event count are essentially identical (0.44 vs 0.45). The excess mortality concentration is vulnerability-driven, not TB-cause-specific.")}
{figure("fig_outcome_temporal_2013-2024.png",15,"Temporal de-noising of outcomes. Left: sliding-window concentration of TB deaths and abandonment over calendar time (bootstrap CI). Right: the abandonment autocorrelation is strongly attenuated by noise (reliability 0.58 vs 0.78 for cases) but, once disattenuated, the true year-to-year correlation is ≈0.65 across the decade — the abandonment hotspots are stable, not reshuffling.")}

<h3>4.7 Outcome-based hotspots — two distinct geographies, mapped separately</h3>
<p>Because abandonment and mortality behave so differently — abandonment a genuine, TB-specific concentration; mortality
a general-vulnerability signal — we do <b>not</b> combine them into a single "adverse outcome". We select and map each
lens on its own (Figure 16). They pick out <b>different places</b>: a unit can have high abandonment with ordinary
mortality, or high mortality with ordinary abandonment.</p>
{figure("fig_outcome_maps_separate_2013-2024.png",16,"The two adverse-outcome geographies, side by side. Left: treatment abandonment % of evaluated cases. Right: TB mortality % (integrated TBWeb+SIM deaths). Units with ≥10 evaluated cases. The two surfaces are visibly different — combining them would blur two distinct signals.")}
<p><b>Abandonment hotspots</b> partly overlap incidence (Jaccard 0.24) but surface <b>185 areas (4.5M people) with
moderate incidence (35/100k) and high abandonment (14.7% vs 9.0% in incidence-only areas)</b> — treatment-retention
failures the case-finding lens would miss (Figure 17). Spatially, the overlap with incidence (126 areas selected by
both lenses) is <b>concentrated in the São Paulo metropolitan core and the Baixada Santista</b>: in the Greater SP zoom
the abandonment hotspots light up <i>together with</i> the incidence belt, so abandonment is anchored in the same dense
urban TB corridor.</p>
{figure("fig_inc_vs_aband_2013-2024.png",17,"Incidence vs abandonment hotspots (whole state + Greater SP/Baixada zoom). Purple = both; red = incidence-only; blue = abandonment-only. Abandonment surfaces a partly distinct set of treatment-retention-failure areas.")}
<p><b>Mortality hotspots</b> diverge far more from incidence (Jaccard 0.10): <b>222 areas (4.9M people) with
below-average incidence (30/100k) but TB mortality 10.1% (vs 5.1% in incidence-only areas)</b> — low-detection,
high-lethality places (Figure 18). The spatial signature is the opposite of abandonment: only 56 areas are selected by
both incidence and mortality, and the mortality-only areas are <b>dispersed across the interior, away from the
metropolitan incidence core</b> — in the Greater SP zoom they light up <i>apart from</i> the case-finding belt. This is
the visual counterpart of the negative control: mortality marks a <b>diffuse, statewide gradient of vulnerability and
lethality</b>, not the urban TB-transmission map.</p>
{figure("fig_inc_vs_death_2013-2024.png",18,"Incidence vs mortality hotspots (whole state + Greater SP/Baixada zoom). Purple = both; red = incidence-only; orange = mortality-only. TB mortality picks out low-incidence, high-lethality areas that diverge strongly from the case-finding map.")}
<p>Critically, the two outcome lenses also diverge <b>from each other</b> (Jaccard 0.11; Figure 19): the abandonment map
and the mortality map are nearly independent geographies. This is the empirical reason not to collapse them — a single
combined adverse-outcome map would average two unrelated patterns and point programmes to neither well. For planning,
abandonment hotspots indicate <b>where to strengthen treatment support and retention</b>, while mortality hotspots
indicate <b>where vulnerable patients die</b> and earlier diagnosis / linkage is most needed.</p>
{figure("fig_aband_vs_death_2013-2024.png",19,"Abandonment vs mortality hotspots. Blue = abandonment-only; orange = mortality-only; purple = both. The two outcome targeting lenses overlap little (Jaccard 0.11) — they are distinct geographies and are best used separately.")}

<h2>5. Key findings</h2>
<ul>
<li><b>Strong concentration:</b> top 20% of adult population → 39.3% of cases (Gini 0.367); ~2:1 detection efficiency for geographically-targeted ACF.</li>
<li><b>Stable over 12 years:</b> annual Gini 0.36–0.39 and Jaccard 0.44–0.48; the de-noised case concentration is flat and the disattenuated rank-correlation is ≈0.75 — the same priority areas persist, enabling multi-year programme planning.</li>
<li><b>Abandonment is the most concentrated outcome, and it is real:</b> de-noised Gini 0.41 vs 0.32 for cases, robust to rarefaction and restriction, and temporally stable (disattenuated autocorrelation ≈0.65) — the strongest, most actionable programmatic signal.</li>
<li><b>TB mortality is concentrated at about the incidence level</b> once measured with an integrated TBWeb + SIM death marker (de-noised Gini 0.33); the naïve "deaths far more concentrated" impression does not survive noise correction.</li>
<li><b>The excess mortality concentration is general vulnerability, not TB-specific:</b> a negative control shows non-TB deaths among TB patients cluster identically — these are high-lethality places, not a TB-transmission signal.</li>
<li><b>Two distinct outcome maps, kept separate:</b> abandonment hotspots (185 areas, treatment-retention failure) and mortality hotspots (222 areas, high lethality) each diverge from incidence (Jaccard 0.24 and 0.10) and from each other (0.11) — they should be targeted separately, not merged into one adverse marker.</li>
</ul>

<h2>6. Discussion and limitations</h2>
<p>The stability of the concentration across a full decade strengthens the case for geographically-targeted ACF: today's
priority areas are very likely to remain priority areas. The outcome-based analysis adds a complementary targeting
rationale — not only "where to find cases" (incidence) but "where the programme is failing patients"
(mortality/abandonment) — and directly addresses the concern that incidence under-counts the most vulnerable areas.</p>
<p>Two methodological choices make the outcome findings defensible. First, every concentration claim is noise-corrected,
because rarer events spuriously inflate concentration indices; after correction, the headline that survives is that
<b>treatment abandonment</b> is genuinely and durably the most concentrated outcome — a programme-actionable target —
whereas the apparent excess concentration of mortality is more modest. Second, integrating the civil registry (SIM) with
the surveillance death marker both completes mortality ascertainment and, through a negative control, reframes it: the
spatial excess in deaths is shared by non-TB causes, so it marks <b>where vulnerable patients die</b> rather than a
TB-specific effect. For programme design this still matters — these are high-lethality areas warranting treatment
support — but it should be communicated as a vulnerability signal, not as differential TB severity.</p>
<p><b>Limitations.</b> (i) The population denominator is fixed at the 2022 Census; absolute rates for earlier years
carry a small bias, although concentration (a relative measure) is robust to this. (ii) CNEFE 2022 is the geocoding
reference for all years; older addresses are matched against the current registry. (iii) Outcome proportions are
computed over evaluated cases; recent cohorts have some still in treatment. (iv) The analysis is at residence level and
does not capture transmission location.</p>

<div class="optional"><h3>Proposed extension — vulnerability archetypes</h3>
<p>As a possible extension (not part of the core method), the priority areas can be classified into structural
archetypes — favela/urban community, degraded inner-city core, urban periphery, other — using IBGE markers and an
operational definition of the degraded inner-city core from the Brazilian urban-health literature. This would make
priority areas interpretable for programme planners and let a transmission model carry a small number of vulnerability
classes rather than hundreds of individual units.</p></div>

<h2>7. Next steps (link to modelling)</h2>
<ol>
<li><b>Modelling target population:</b> use the 332 areas to estimate the <b>proportion of incident adult TB occurring in the high-burden geographic target group</b> — a direct input to the WHO investment-case transmission model.</li>
<li><b>Two-lens targeting:</b> combine incidence hotspots (case detection) with poor-outcome hotspots (treatment support / retention).</li>
<li><b>Quantify ACF yield and cost</b> per area/archetype to parameterise intervention scenarios.</li>
<li><b>Optional analyses</b> already scoped: fixed-hotspot annual capture (targeting durability) and 3-year rolling-window selection.</li>
</ol>

<h2>8. Reproducibility</h2>
<p>Code: repository <code>SP-TB-spatial-analyses</code> — geocoding (scripts 20–21, 28–29, 40–41), unit construction +
hotspot selection (48–49), four-group/metro tables (49d–49e), outcome hotspots (50), concentration indices (51),
temporal stability and autocorrelation (52–55), concentration dynamics (56), and the noise-correction / integrated-
mortality suite: outcome de-noising (57), outcome temporal + autocorrelation (58), noise-honest Gini (59), SIM-integrated
death concentration (60) and the non-TB-death negative control (61). The integrated TB-death marker links TBWeb to the
civil registry (SIM) by notification number (<code>Banco de dados / LINKAGE SIM</code>), flagging TB (ICD-10 A15–A19)
anywhere on the death certificate. Figures and tables in the shared Drive folder <code>SP-TB-spatial-analyses /
Figures_2013-2024_adults</code>. Scope throughout: adults ≥15, new+relapse, 2013–2024, adult-population denominator,
units with ≥10 pooled cases.</p>

<div class="footer">Working manuscript base · São Paulo adult TB spatial analysis 2013–2024 · WHO TB Screening Investment Case (Brazil).
Self-contained file — figures embedded; opens in any browser and prints to PDF.</div>
</div></body></html>"""

H = H.replace("<b>","").replace("</b>","")   # remove emphasis bold from prose (labels use CSS)
out="/tmp/SP_TB_Paper_Base_Report.html"
with open(out,"w") as f: f.write(H)
print("Saved:",out,f"({os.path.getsize(out)/1e6:.1f} MB)")
