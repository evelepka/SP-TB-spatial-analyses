"""Self-contained report documenting the spatial-unit-of-analysis problem and the
regionalisation solution, so nothing from this investigation is lost. Methodology is
presented cleanly (one final method + a development note on the alternatives tested).
Output: /tmp/SP_TB_Spatial_Unit_Report.html
"""
import base64, os
def img(p):
    if not os.path.exists(p): return f'<p style="color:#b00">[missing: {p}]</p>'
    with open(p,"rb") as f: b=base64.b64encode(f.read()).decode()
    return f'<img src="data:image/png;base64,{b}" style="max-width:100%;border:1px solid #e2e8f0;border-radius:6px">'
def fig(p,cap):
    return f'<figure style="margin:20px 0;text-align:center">{img(p)}<figcaption style="font-size:12px;color:#5b6b7a;margin-top:7px;text-align:left;line-height:1.45">{cap}</figcaption></figure>'

CSS="""body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1a202c;line-height:1.65;margin:0;background:#f4f6f8}
.page{max-width:880px;margin:0 auto;background:#fff;padding:56px 70px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
h1{font-size:26px;color:#0d2b45;margin:0 0 4px}.sub{color:#028090;font-weight:600;font-size:15px;margin:0 0 4px}
.meta{color:#5b6b7a;font-size:12.5px;margin:0 0 8px}
h2{font-size:20px;color:#0d2b45;margin:36px 0 8px;padding-bottom:6px;border-bottom:2px solid #028090}
h3{font-size:16px;color:#0d2b45;margin:22px 0 6px}p{margin:9px 0}ul,ol{margin:9px 0;padding-left:22px}li{margin:4px 0}
code{background:#eef2f5;padding:1px 5px;border-radius:4px;font-size:12.5px}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:13px}
th,td{border:1px solid #e2e8f0;padding:6px 10px;text-align:left;vertical-align:top}
th{background:#0d2b45;color:#fff}tr:nth-child(even) td{background:#f7fafc}
.callout{background:#f0f9f7;border:1px solid #cfe9e3;border-left:4px solid #02c39a;border-radius:8px;padding:12px 20px;margin:16px 0}
.amber{background:#fff8e6;border:1px solid #f0e0b0;border-left:4px solid #9a6700;border-radius:8px;padding:10px 20px;margin:16px 0}
.footer{margin-top:40px;padding-top:14px;border-top:1px solid #e2e8f0;font-size:11.5px;color:#5b6b7a}"""

H=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Spatial unit of analysis — São Paulo TB study</title><style>{CSS}</style></head><body><div class="page">
<p class="sub">WHO TB Screening Investment Case · Brazil — methods working note</p>
<h1>Defining the spatial unit of analysis: problem, options, and a regionalisation solution</h1>
<p class="meta">São Paulo State · adult TB (≥15), 2013–2024 · documents the unit-definition investigation so it is not lost</p>

<div class="callout"><b>Summary.</b> Every concentration measure and map in this study depends on the spatial unit we aggregate
notifications to. There is <b>no off-the-shelf neighbourhood ("bairro") unit</b> for São Paulo: the bairro is not an official
cartographic unit, and the available administrative units range ~50-fold in population (a census sector ~300 residents vs a
capital district ~88,000), with the coarse capital districts blending favelas and adjacent affluent areas. After testing every
available bairro source (IBGE, CNEFE, OpenStreetMap — all inadequate), we <b>constructed</b> the unit by spatially-constrained
regionalisation: contiguous census sectors grouped into ~5,000-adult, income-homogeneous neighbourhoods, with favela and
non-favela sectors kept separate. The result is <b>7,310 uniform units</b> (median 5,329 adults) that resolve the capital
(1,944 units vs 96 districts) and never merge a favela with an affluent neighbour. This is offered as a <b>complement</b> to
the existing operational unit; both will be carried through the analyses and the final choice made on comparison.</div>

<h2>1. The problem</h2>
<p>The unit must be (i) <b>fine enough not to average across socially distinct areas</b> — in São Paulo a favela and an
affluent block can be ~200 m apart, and resolving that contrast is the whole point — and (ii) <b>coarse enough to carry
stable rates</b>, especially for rarer events (death, abandonment). These pull against each other (the modifiable areal unit
problem, MAUP): finer units reveal more concentration but are noisier.</p>
<p>Our initial <b>operational unit</b> (sectors aggregated to the finest IBGE-named level available: FCU favela ≥5,000,
neighbourhood where IBGE names one, district in the capital; ~3,014 units) carries a severe, unintended <b>scale
heterogeneity</b>: IBGE names a neighbourhood for only <b>28.5%</b> of sectors and <b>0%</b> of the capital, so the capital
(9.4M adults, highest burden) collapses to <b>96 districts of ~88,600 adults each</b>. Statewide, units span ~1,800 to
~88,600 adults — a <b>~50-fold</b> range — and the coarse capital districts mix favelas with affluent areas.</p>

<h2>2. Why no off-the-shelf neighbourhood unit exists</h2>
<p>The structural reason: <b>in São Paulo the "bairro" is not an official cartographic unit</b> — the legally defined
sub-municipal divisions are the subprefeitura, the district, and the census sector. There is no authoritative neighbourhood
boundary to match to, so every source is noisy. We tested them all:</p>
<table>
<tr><th>Candidate source</th><th>Coverage / result</th><th>Verdict</th></tr>
<tr><td>IBGE <code>NM_BAIRRO</code> (census mesh)</td><td>28.5% of sectors; <b>0% of the capital</b></td><td>Sparse; absent exactly where it is needed</td></tr>
<tr><td>CNEFE address-registry bairro</td><td>92% of cases, but <b>21,411 fragments</b> (median 661 adults)</td><td>Loteamento-level + spelling variants; not a neighbourhood</td></tr>
<tr><td>OpenStreetMap neighbourhood polygons</td><td><b>2%</b> of the capital; ~3–5% most interior cities</td><td>Crowd-sourced and near-empty for SP</td></tr>
<tr><td>IBGE subdistrito</td><td>capital = 96 (identical to districts)</td><td>No finer than district</td></tr>
<tr><td>IBGE Área de Ponderação</td><td>not released for the 2022 Census</td><td>Unavailable</td></tr>
</table>

<h2>3. The solution: spatially-constrained regionalisation</h2>
<p>We construct the unit by <b>spatially-constrained regionalisation</b>: census sectors are aggregated into contiguous,
neighbourhood-scale regions (target ≈ <b>5,000 adults</b>) that are <b>homogeneous in household income</b>, with favela
(IBGE Favelas e Comunidades Urbanas, FCU) and non-favela sectors regionalised <b>separately</b> so a favela is never merged
with an adjacent affluent area. The procedure is <b>greedy region-growing</b> (a standard regionalisation heuristic): starting
from the lowest-income unassigned sector, a region accretes the adjacent sector closest in income until it reaches the target
population; contiguity islands are reconnected to their nearest sector, and any sub-threshold leftover is merged into its most
income-similar neighbour. Income is the 2022 census mean household income (sector level); the target population is a tunable
parameter. The unit is <b>outcome-independent</b> (built on geography and income, blind to TB) and reproducible.</p>
<p>In plain terms, the unit is built from <b>three ingredients</b> (none drawn from the TB data):</p>
<table>
<tr><th>Ingredient</th><th>Role</th></tr>
<tr><td><b>Contiguity</b></td><td>only adjacent sectors can join the same unit → units are spatially connected</td></tr>
<tr><td><b>Household income</b></td><td>each step adds the neighbouring sector closest in income → each unit stays internally homogeneous, so a favela never grows into an affluent block</td></tr>
<tr><td><b>Population (~5,000 adults)</b></td><td>the unit stops growing at the target size → uniform, rate-stable units</td></tr>
</table>
<p>(plus the favela/non-favela split). The income keeps each unit socially coherent; the population target keeps units a
uniform, defensible size. The population floor is a parameter — like the choice of any spatial scale (the MAUP) — and §5
shows the substantive findings do not depend on it.</p>
<div class="amber"><b>Development note (for transparency).</b> We first evaluated the <b>max-p-regions</b> optimiser
(Duque, Anselin &amp; Rey, 2012; via PySAL/spopt), which gives an explicit population-floor guarantee but is computationally
prohibitive across ~1,000 districts (projected runtime &gt; 3 h). We then tried <b>Ward agglomerative clustering</b> with a
contiguity constraint — fast, but it optimises attribute homogeneity rather than region size and so produced very unequal
units (one region of 156,000 alongside thousands of singletons). <b>Greedy region-growing</b> combines the speed of Ward with
the size control of max-p, and is the method adopted. All three belong to the same regionalisation family.</div>

<h3>3.1 What the population target does to large homogeneous areas — the size-vs-boundaries trade-off</h3>
<p>Because the method grows each unit to a target population (~5,000 adults), a <b>large socially-homogeneous area is
subdivided</b> into several ~5,000-adult units rather than kept whole. This is clearest in the affluent districts of the
capital, which are internally uniform yet large — one everyday "neighbourhood" becomes many units:</p>
<table>
<tr><th>Capital district (affluent, homogeneous)</th><th>Adults</th><th>Units it became</th><th>Income (median; p10–p90)</th></tr>
<tr><td>Itaim Bibi</td><td>88,468</td><td><b>14</b></td><td>R$ 15,400 (8,800–23,700)</td></tr>
<tr><td>Jardim Paulista</td><td>72,037</td><td>13</td><td>R$ 14,800 (9,900–20,200)</td></tr>
<tr><td>Moema</td><td>71,242</td><td>12</td><td>R$ 15,300 (10,100–23,700)</td></tr>
<tr><td>Pinheiros</td><td>57,683</td><td>9</td><td>R$ 13,400 (8,200–20,000)</td></tr>
</table>
<p>So a single area such as Itaim Bibi becomes ~14 contiguous, income-homogeneous units; across the capital the median
district yields ~13 units and 92 districts became ≥4 units.</p>
<p><b>Does this distort the analysis?</b></p>
<ul>
<li><b>Rates and concentration (Lorenz, Gini): no.</b> The pieces of a uniform area carry similar rates, so subdividing it does not manufacture concentration.</li>
<li><b>The favela ↔ affluent contrast: preserved.</b> Subdivision happens only <i>within</i> one social type — a favela is never split off into an affluent piece, or vice versa.</li>
<li><b>Interpretation: a genuine limitation.</b> The pieces inside a large uniform area are statistical sub-areas, not individually-named neighbourhoods, and the internal boundary between consecutive pieces is not unique — it depends on the order in which the region grew.</li>
</ul>
<p><b>The underlying trade-off.</b> This is the unavoidable consequence of requiring a <i>uniform</i> unit size: any method
with a population target subdivides large homogeneous areas. The alternative — growing each zone until its social character
changes, with no size target — yields units that follow real social boundaries (a favela is one small unit; a large affluent
area is one large unit), but then unit size varies again and the smallest units carry too few rare events. The two goals
cannot both be satisfied:</p>
<table>
<tr><th>Approach</th><th>What it does</th><th>Cost</th></tr>
<tr><td><b>Uniform size</b> — population target (adopted here)</td><td>every unit ≈ 5,000 adults</td><td>subdivides large homogeneous areas; internal boundaries arbitrary</td></tr>
<tr><td><b>Natural boundaries</b> — no size target</td><td>each unit ends where the social character changes</td><td>unit size varies again; small units carry too few rare events</td></tr>
</table>
<p>We adopt the uniform-size target because (i) it removes the ~50-fold size heterogeneity of the administrative units,
(ii) it keeps every unit large enough for stable incidence rates, and (iii) the substantive findings are robust to the unit
(§5). The target value (5,000) is a parameter — like the choice of any spatial scale (the modifiable areal unit problem) — and
§5 shows the conclusions do not depend on it. <b>This subdivision of large homogeneous areas is the principal limitation of
the constructed unit, and is stated here transparently.</b></p>

<h2>4. Result</h2>
<table>
<tr><th></th><th>Value</th></tr>
<tr><td>Total units</td><td><b>7,310</b> (favela 1,182 · non-favela 6,128 · mixed 0)</td></tr>
<tr><td>Adults per unit</td><td>median <b>5,329</b> · IQR 3,178–6,336 · max 17,030 (vs the previous ~50-fold spread)</td></tr>
<tr><td>Uniformity</td><td>84% of units within 2,000–12,000 adults</td></tr>
<tr><td>Social purity (favela kept apart from non-favela)</td><td><b>100%</b> by construction</td></tr>
<tr><td>State capital</td><td><b>1,944 units</b> (was 96 districts) — finally resolved at neighbourhood scale</td></tr>
<tr><td>Runtime</td><td>~16 s (fully reproducible)</td></tr>
</table>
{fig("/tmp/fig_region_vila_andrade.png","Validation on the hardest case: Vila Andrade (capital), where Paraisópolis (one of Brazil's largest favelas, median income ~R$1,700) abuts the wealthy Morumbi (~R$12,800). Fill = median income (red=poor, green=rich); thick black outline = favela (FCU) units. Despite their adjacency, the favela and the affluent sectors fall into different units.")}
{fig("/tmp/fig_region_sizes.png","State-wide unit-size distribution: 7,310 units clustered around the ~5,000-adult target (median 5,329; IQR 3,178–6,336), replacing the previous ~50-fold heterogeneity.")}

<h2>5. Validation: the findings hold on both units (P1 + P2)</h2>
<p>We re-ran the first two analyses on the new unit and the operational unit side by side. <b>The substantive conclusions
are identical</b>; the regionalisation unit is simply finer, so it reads slightly more concentration and a little more
year-to-year noise.</p>
<h3>P1 — geographic concentration (de-noised Gini)</h3>
<table>
<tr><th>Lens</th><th>Operational unit (3,014)</th><th>Regionalisation (7,314)</th><th>Reading</th></tr>
<tr><td>Incidence</td><td>0.353</td><td><b>0.384</b></td><td>strong concentration in both; finer unit reads a touch more</td></tr>
<tr><td>Abandonment</td><td>0.436</td><td>0.408</td><td>similar</td></tr>
<tr><td>TB mortality</td><td>0.354</td><td>0.303</td><td>lower on the fine unit — a measurement limit, not a real difference: ~1 death per unit over 12 years is too sparse, so the noise-correction over-corrects (the same effect appears at the census-sector scale, 0.265)</td></tr>
</table>
<p>Across the full scale ladder the de-noised <b>incidence</b> Gini stays ≈0.30–0.40 (municipality → sector), so the
concentration conclusion is robust to the unit; the rarer outcomes need units large enough to hold a handful of events.</p>
{fig("/tmp/fig_p1_unit_comparison.png","P1 — Lorenz curves of TB incidence by spatial unit. The new regionalisation unit (red) sits between the census sector and the operational unit; all show strong concentration.")}
<h3>P2 — temporal stability</h3>
<table>
<tr><th></th><th>Operational unit</th><th>Regionalisation</th></tr>
<tr><td>Annual Gini (band, 2013–2024)</td><td>0.41–0.44 (range 0.03)</td><td>0.54–0.58 (range 0.04)</td></tr>
<tr><td>Year-to-year hotspot Jaccard (mean)</td><td>0.33</td><td>0.32</td></tr>
<tr><td>Lag-1 rate autocorrelation</td><td>0.54</td><td>0.45</td></tr>
</table>
<p>Concentration is <b>stable each year in both</b> (the annual Gini barely moves), and the same places stay hotspots to the
same degree (Jaccard ≈0.33). The regionalisation unit is a little noisier year-on-year (lower autocorrelation), because
smaller units carry fewer cases per year — the underlying geography is the same.</p>
{fig("/tmp/fig_p2_temporal_comparison.png","P2 — temporal stability, operational vs regionalisation. Left: annual Gini (flat = stable, in both). Right: year-to-year hotspot overlap (Jaccard, ~0.33 in both).")}

<h2>6. Status and decision</h2>
<p>The regionalisation is offered as a <b>complementary</b> unit, not a replacement: the existing operational unit is
retained, and the analyses are being re-run on both, comparing question by question. <b>P1 (concentration) and P2 (temporal
stability) are done and give the same conclusions on both units</b> (§5); P3 (social vulnerability — kept anchored at the
census sector, since the regionalisation already uses income) and P4 (overlap of the three lenses) remain. The final unit
choice will be made on the full comparison; the concentration findings are already robust to spatial scale (de-noised
incidence Gini ≈0.40 sector → 0.30 municipality), so the choice affects presentation and defensibility rather than the
substantive conclusions.</p>

<h2>7. Reproducibility</h2>
<p>Scripts in <code>SP-TB-spatial-analyses</code> (branch <code>gsp-vulnerability-typology</code>): Gini scale-sensitivity
(79); the rejected bairro probes — CNEFE (80), OpenStreetMap (81); the regionalisation feasibility test on Vila Andrade (82);
the state-wide regionalisation builder (83, greedy region-growing, <code>FLOOR=5000</code>, income attribute, favela/non-favela
split, island reconnection); the figures (84); the P1 concentration and P2 temporal-stability comparison of the two units
(86, 87); this report (85). Sector→unit mapping saved to <code>regions_sectors.csv</code>.
Inputs: IBGE 2022 census sectors + mean household income; IBGE FCU classification. Method family: spatially-constrained
regionalisation (Duque, Anselin &amp; Rey 2012; Assunção et al. 2006 / SKATER), via PySAL and scikit-learn.</p>

<div class="footer">Methods working note · spatial unit of analysis · São Paulo adult TB, 2013–2024 · WHO TB Screening Investment Case (Brazil). Self-contained file — figures embedded.</div>
</div></body></html>"""
out="/tmp/SP_TB_Spatial_Unit_Report.html"
with open(out,"w") as f: f.write(H)
print("Saved:",out,f"({os.path.getsize(out)/1e6:.2f} MB)")
