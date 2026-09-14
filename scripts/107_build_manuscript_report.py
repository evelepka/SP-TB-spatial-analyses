"""New MANUSCRIPT figures report (separate document). Regionalisation as the territorial unit.
Four questions + five figures + captions + brief methods + data limitation. Self-contained HTML.
"""
import base64, os
FIGDIR=("/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/"
        "My Drive/WHO modelling Project/SP-TB-spatial-analyses/Figures_2013-2024_adults")
def img(name):
    p=os.path.join(FIGDIR,name)
    if not os.path.exists(p): return f'<p style="color:#b00">[missing: {name}]</p>'
    with open(p,"rb") as f: b=base64.b64encode(f.read()).decode()
    return f'<img src="data:image/png;base64,{b}">'
def fig(n,name,cap):
    return f'<figure>{img(name)}<figcaption><span class="fl">Figure {n}.</span> {cap}</figcaption></figure>'
CSS="""
:root{--navy:#0d2b45;--teal:#028090;--mint:#02c39a;--ink:#1a202c;--muted:#5b6b7a;--line:#e2e8f0;--callout:#f0f9f7;}
*{box-sizing:border-box}body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);line-height:1.65;margin:0;background:#f4f6f8;}
.page{max-width:900px;margin:0 auto;background:#fff;padding:56px 70px;box-shadow:0 1px 4px rgba(0,0,0,.08);}
h1{font-size:26px;line-height:1.24;color:var(--navy);margin:0 0 6px;}
.sub{font-size:14.5px;color:var(--teal);font-weight:600;margin:0 0 4px;}
.meta{font-size:12.5px;color:var(--muted);margin:0 0 8px;}
h2{font-size:20px;color:var(--navy);margin:40px 0 8px;padding-bottom:6px;border-bottom:2px solid var(--teal);}
p{margin:9px 0;} ol{margin:9px 0;padding-left:22px;} li{margin:6px 0;}
.callout{background:var(--callout);border:1px solid #cfe9e3;border-left:4px solid var(--mint);border-radius:8px;padding:10px 20px;margin:16px 0;}
.lim{background:#fff8e6;border:1px solid #f0e0b0;border-left:4px solid #9a6700;border-radius:8px;padding:8px 20px;margin:16px 0;font-size:13.5px;}
figure{margin:20px 0;text-align:center;}figure img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px;}
figcaption{font-size:12px;color:var(--muted);margin-top:7px;text-align:left;line-height:1.45;}
.fl{font-weight:600;color:var(--navy);}
.footer{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);font-size:11.5px;color:var(--muted);}
"""
H=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SP TB — manuscript figures (regionalisation)</title><style>{CSS}</style></head><body><div class="page">
<p class="sub">WHO TB Screening Investment Case · Brazil — manuscript figures</p>
<h1>Geographic concentration, adverse-outcome hotspots, and place vulnerability of tuberculosis in São Paulo State, 2013–2024</h1>
<p class="meta">Adults ≥15, new + relapse · individual notifications geocoded to the census sector · territorial unit = statewide regionalisation (income-homogeneous ~5,000-adult neighbourhoods, favela regionalised separately); n = 7,314 regions (5,248 with ≥10 cases). 192,161 incident episodes (each new or relapse notification; deaths counted once per person). All rates age-standardised (indirect, State reference).</p>

<h2>Questions</h2>
<ol>
<li>To what extent do TB notifications and poor outcomes (loss to follow-up, death) concentrate geographically in São Paulo?</li>
<li>Where do areas of high TB incidence (notification as proxy), loss to follow-up or death occur within the State, and is it in areas of high socioeconomic vulnerability?</li>
<li>Do areas of high incidence overlap those of high loss to follow-up or death?</li>
<li>Are areas of high incidence, loss to follow-up or death consistent over time?</li>
</ol>

<div class="callout"><b>Vulnerability index.</b> Four census-sector domains, each z-standardised and oriented so higher = more deprived, then averaged: <b>household income · adult illiteracy · residents per household · favela / urban agglomeration</b>. Externally validated against the official IPVS 2022 (SEADE), Spearman ρ = 0.76. Anchored at the sector; population-weighted to the region.</div>

<h2>Figure 1 — How much does TB concentrate? (Question 1)</h2>
<p>Adult TB and its adverse outcomes are geographically concentrated. Concentration indices are noise-corrected (split-sample
cross-fit), because rarer events inflate the naïve Gini. After correction, the 20% of the population living in the
highest-rate regions carries roughly <b>49% of loss to follow-up, 45% of incidence and 39% of TB mortality</b> — loss to follow-up
the most concentrated lens; the high naïve mortality concentration is largely small-area noise.</p>
{fig(1,"fig1_concentration_region_2013-2024.png","All estimates are de-noised (split-sample cross-fit; the naïve-vs-de-noised comparison is Supplementary Figure S1). (a) De-noised concentration curves — cumulative share of events vs cumulative share of the adult population, highest-rate regions first, so the curves fall above the diagonal (de-noised Gini: incidence 0.39, loss to follow-up 0.42, TB mortality 0.28). (b) De-noised share of events in the 5%, 10%, 20% and 40% of the population living in the highest-rate regions. The top 20% of the population carries ~45% of incidence, ~49% of loss to follow-up and ~39% of TB mortality.")}

<h2>Figure 2 — Where does TB occur, and do the lenses overlap? (Questions 2–3)</h2>
<p>Across the whole State the three outcomes share the same broad geography: the highest per-capita rates fall in the
<b>metropolitan southeast — Greater São Paulo and the Baixada Santista coast</b> — with a secondary elevated zone in the
south-central interior and a smooth low-rate gradient across the west. Each surface is a <b>locally population-normalized rate</b>
(kernel density of cases &divide; kernel density of the adult population), mapping cases <i>per capita</i> rather than simply where
people live. Framed as discrete hotspots (top 20% of the population by rate), the incidence, mortality and loss to follow-up lenses
pick out <b>partly different regions</b>; adding the vulnerability index as a fourth lens, only 115 regions are hotspots on all four —
incidence and mortality overlap most, loss to follow-up is largely its own geography.</p>
{fig("2a","fig_density_maps_state_2013-2024.png","Smoothed spatial density of (A) TB incidence, (B) TB mortality and (C) loss to follow-up across São Paulo State, 2013–2024. Each panel is a locally population-normalized rate surface — kernel density of cases &divide; kernel density of the adult population (per 100,000 adults / year) — so the colour is a rate, not raw case counts. Dark points mark individual cases at their census-sector location; the surface is estimated continuously across the entire State.")}
{fig("2b","fig_density_maps_zoom_2013-2024.png","The same rate surfaces zoomed to the São Paulo metropolitan region and the Baixada Santista, with municipal boundaries. The coastal Baixada (Santos–São Vicente–Cubatão) and the dense periphery of Greater São Paulo carry the highest per-capita rates for all three outcomes.")}
{fig("2c","fig2b_venn_region_2013-2024.png","Four-set Venn of the top-20% hotspot overlap (incidence, mortality, loss to follow-up and vulnerability): the lenses are largely complementary — 115 regions are hotspots on all four, most on only one.")}

<h2>Figure 3 — Consistent over time? (Question 4)</h2>
<p>The geography is stable across the decade. Grouping the years into four 3-year periods, and applying the de-noising adjustment
<i>within</i> each period, removes both the single-year sparsity noise and the rare-event bias: the de-noised concentration is
essentially flat across periods for every outcome (the top 20% of the population carries ~43% of incidence, ~35% of TB mortality
and ~43% of loss to follow-up in every period), the same regions persist as hotspots between consecutive periods (Jaccard: incidence
~0.47, loss to follow-up ~0.28, mortality ~0.20), and the rank autocorrelation stays high across period lags. The COVID-19 period did
not break the pattern.</p>
{fig(3,"fig3_temporal_region_2013-2024.png","Temporal stability over four 3-year periods (2013–15, 2016–18, 2019–21, 2022–24), all three outcomes, with the de-noising (split-sample cross-fit) adjustment applied within each period. (a) De-noised concentration — % of events in the top 20% of the population — per period. (b) Hotspot Jaccard overlap between consecutive periods. (c) Rank autocorrelation of region rates across period lags. Grouping removes the single-year sparsity noise and the cross-fit removes the rare-event bias; every outcome is stable.")}

<h2>Figure 4 — Which vulnerability components track which hotspots? (Question 2)</h2>
<p>The <b>incidence</b> hotspots are strongly separated by every deprivation component (standardized difference, Cohen's d,
0.42–0.62 — low income and % favela lead); the <b>mortality</b> hotspots moderately; the <b>loss to follow-up</b> hotspots barely
(0.01–0.12) — loss to follow-up is not a place-deprivation phenomenon.</p>
{fig(4,"fig4_components_hotspots_2013-2024.png","Standardized mean difference (Cohen's d) of each vulnerability component between hotspot and non-hotspot regions, grouped by component. Components oriented so higher = more deprived. Incidence hotspots are the most deprived across all components; loss to follow-up hotspots are not.")}

<h2>Figure 5 — Dose-response of TB indicators on vulnerability indicators (Question 2)</h2>
<p>Population-weighted GAM smooths on the uniform regionalisation units, for the continuous indicators including the composite
vulnerability index (bottom row); low-complexity smooths (capped spline basis) are used to avoid overfitting. TB <b>incidence</b>
falls steeply with household income and rises with illiteracy, household crowding and the vulnerability index; the
<b>TB-mortality rate</b> follows the same directions more weakly; <b>loss to follow-up</b> is flat against every indicator —
again, not explained by place characteristics. (Favela is <i>binary</i> at the region level — regions are favela or non-favela —
so it is not smoothed here; its effect is reported in Figure 4.)</p>
{fig(5,"fig5_gam_region_2013-2024.png","Scatter (regions, sized by population) + population-weighted GAM (95% CI; low-complexity, capped spline basis), rows = the continuous vulnerability indicators (household income [log], adult illiteracy, residents per household, composite vulnerability index), columns = TB indicators (incidence [log], TB-mortality rate, loss to follow-up %). Income is protective; illiteracy, crowding and the vulnerability index raise incidence and mortality; loss to follow-up is flat. Favela is omitted here — it is binary at the region level and is shown in Figure 4.")}

<h2>Methods (brief)</h2>
<p><b>Data:</b> individual TB notifications (TBWeb, São Paulo State, 2013–2024), geocoded to the 2022 census sector via the
national address registry (CNEFE 2022). TB death = integrated marker (TBWeb 'Óbito TB' OR tuberculosis on any line of the
SIM death certificate). <b>Territorial unit:</b> a statewide regionalisation — census sectors grown into ~5,000-adult,
income-homogeneous neighbourhoods, favela and non-favela regionalised separately so a favela never merges with an adjacent
affluent area (n = 7,314; analyses on the 5,248 regions with ≥10 pooled cases). <b>Age standardisation:</b> indirect, São
Paulo State internal reference, eight adult age bands. <b>Concentration</b> is de-noised by split-sample cross-fit. <b>Hotspots</b>
= regions ranked by age-standardised rate until 20% of the adult population is covered. <b>Density surfaces
(Figure 2a–b):</b> a Gaussian kernel density of cases divided by the same-bandwidth kernel density of the adult population,
on the projected census-sector centroids, giving a locally population-normalised rate estimated continuously across the State.</p>

<div class="lim"><b>Limitation — vulnerability indicators.</b> The composite uses only variables the 2022 Census releases at the
census-sector level (income of the household head, literacy, residents per household, favela). Three indicators the ideal
index would include are <b>not available at this resolution</b> and are omitted: <b>unemployment</b> and <b>education level</b>
(years of schooling) come from the Census <i>sample</i>, released only at municipality / weighting-area level; <b>social
assistance</b> (CadÚnico) is administrative, municipal. <b>Sanitation</b> was tested and dropped (near-universal in São Paulo —
87% of the adult population adequate — and it lowered agreement with the IPVS). <b>Precarious housing (cortiço)</b> was tested
and dropped (only 0.3% of sectors record any; the Census undercounts tenements). <b>Population density</b> is not a deprivation
marker (it is slightly negatively correlated with the composite) and is excluded.</div>

<h2 style="margin-top:40px;border-top:3px double var(--teal);padding-top:22px;">Supplementary material</h2>
{fig("S1","figS1_denoising_2013-2024.png","<b>Supplementary Figure S1. De-noising the concentration estimate.</b> For each outcome, the naïve estimate (dashed) overstates clustering — most for the rarer outcomes (TB mortality, loss to follow-up) — because finite-sample noise inflates the naïve Gini/share; the split-sample cross-fit de-noised estimate (solid) removes this bias, justifying the de-noised values reported throughout (Figures 1 and 3).")}

<div class="footer">Manuscript figures · São Paulo adult TB — geographic concentration, adverse-outcome hotspots, and place vulnerability, 2013–2024 · WHO TB Screening Investment Case (Brazil) · territorial unit = statewide regionalisation. Self-contained; figures embedded.</div>
</div></body></html>"""
H=H.replace("<b>","").replace("</b>","") if False else H
out="/tmp/SP_TB_Manuscript_Figures.html"
open(out,"w").write(H)
print("Saved:",out,f"({os.path.getsize(out)/1e6:.1f} MB)")
