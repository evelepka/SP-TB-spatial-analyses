"""Standalone report — TB programme fragility (diagnostic axis): molecular-test
coverage, laboratory confirmation, their relation to the outcome geographies, and an
independent SIA-SUS cross-check. Companion to the hotspot/vulnerability reports.
Self-contained HTML with figures embedded.
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
h1{font-size:26px;line-height:1.22;color:var(--navy);margin:0 0 6px;}
.sub{font-size:15px;color:var(--teal);font-weight:600;margin:0 0 4px;}
.meta{font-size:12.5px;color:var(--muted);margin:0 0 6px;}
h2{font-size:20px;color:var(--navy);margin:38px 0 8px;padding-bottom:6px;border-bottom:2px solid var(--teal);}
h3{font-size:16px;color:var(--navy);margin:22px 0 6px;}
p{margin:9px 0;} ul,ol{margin:9px 0;padding-left:22px;} li{margin:4px 0;}
code{background:#eef2f5;padding:1px 5px;border-radius:4px;font-size:12.5px;}
.callout{background:var(--callout);border:1px solid #cfe9e3;border-left:4px solid var(--mint);border-radius:8px;padding:12px 20px;margin:16px 0;}
.callout h3{margin-top:0;color:var(--teal);}
.keybox{background:var(--amberbg);border:1px solid #f0e0b0;border-left:4px solid var(--amber);border-radius:8px;padding:6px 20px;margin:16px 0;}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:13px;}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top;}
th{background:var(--navy);color:#fff;font-weight:600;} tr:nth-child(even) td{background:#f7fafc;}
figure{margin:20px 0;text-align:center;}figure img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px;}
figcaption{font-size:12px;color:var(--muted);margin-top:7px;text-align:left;line-height:1.45;}
.figlabel{font-weight:600;color:var(--navy);}
.footer{margin-top:44px;padding-top:14px;border-top:1px solid var(--line);font-size:11.5px;color:var(--muted);}
@media print{body{background:#fff}.page{box-shadow:none;max-width:none;padding:0 6px;}h2{page-break-after:avoid}figure{page-break-inside:avoid}}
"""

H=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TB programme fragility (diagnostic axis) — São Paulo, 2013–2024</title><style>{CSS}</style></head><body><div class="page">
<p class="sub">WHO TB Screening Investment Case · Brazil — companion analysis (programme fragility)</p>
<h1>Tuberculosis programme fragility in São Paulo: diagnostic coverage and its relation to vulnerability and adverse outcomes, 2013–2024</h1>
<p class="meta">Adults (≥15 years), new and relapse cases · area-level diagnostic and infrastructure indicators</p>

<div class="callout"><h3>Summary</h3>
<p>Having mapped where TB and its adverse outcomes concentrate, we ask whether the <b>local TB programme</b> is weakest
where the burden is highest. On the <b>diagnostic axis</b> — molecular testing (TRM-TB/Xpert) and laboratory
confirmation — the answer is reassuring and somewhat counter-intuitive: diagnostic coverage is <b>not lower in the
vulnerable, high-burden areas; if anything it is higher</b>, because the big urban centres concentrate the laboratory
capacity. The under-tested places are the <b>less-vulnerable interior</b>, not the metropolitan hotspots. Diagnostic
coverage is also <b>essentially uncorrelated with the abandonment and mortality geographies</b> — so the programme's
weak link in the bad-outcome areas is <b>not diagnosis</b> (the actionable gap is treatment retention). An independent
SIA-SUS test-volume series corroborates only weakly (it under-captures billing), so the surveillance-based coverage
remains the trustworthy sub-municipal measure. On the <b>infrastructure</b> side the picture splits: <b>primary care is
pro-equity and protective</b> (denser in vulnerable municipalities, tracking lower abandonment and death), whereas
<b>X-ray imaging capacity is the one anti-equity gap</b> — fewer machines per capita and per TB case in the vulnerable,
high-burden municipalities (a gap that doubles once machine capacity, not mere presence, is counted).</p></div>

<h2>1. Objective</h2>
<p>The hotspot and vulnerability analyses show <i>where</i> TB, abandonment and mortality concentrate, and that the
geography is socially patterned. This companion analysis tests a programme-equity question: <b>is the local TB programme
weakest exactly where it is needed most?</b> We examine the <b>diagnostic axis</b> at the area level — molecular-test
coverage and laboratory confirmation — and the ecological health-system <b>infrastructure</b> (primary-care and X-ray
availability, from CNES) — and relate them to vulnerability and to the adverse-outcome geographies. Treatment-support
(DOT/follow-up) indicators remain for a later iteration.</p>

<h2>2. Data sources</h2>
<table>
<tr><th>Source</th><th>Indicator</th><th>Resolution / nature</th></tr>
<tr><td><b>TBWeb</b> (<code>tmr_tb</code>, <code>lab_confirmed</code>)</td><td>Molecular-test coverage; laboratory (bacteriological) confirmation, per case → aggregated to area</td><td>Sub-municipal (geocoded to census sector); case-derived (programme performance)</td></tr>
<tr><td><b>SIA-SUS</b> via DATASUS/TABNET (procedure <code>0202090361</code>, TRM-TB), by municipality of <b>residence</b>, 2019–2024</td><td>Independent count of molecular tests performed (supply side)</td><td>Municipal; administrative billing</td></tr>
<tr><td><b>CNES</b> (estabelecimentos ST + equipamentos EQ, via DATASUS/pysus), 2024</td><td>Primary-care (Posto/UBS) facilities; X-ray machines (general radiography)</td><td>Municipal (no coordinates); ecological infrastructure</td></tr>
<tr><td><b>IBGE Census 2022</b> + vulnerability composite</td><td>Adult population denominators; place vulnerability (sector composite)</td><td>Census-sector → unit</td></tr>
</table>

<h2>3. Methods</h2>
<p><b>Coverage definitions.</b> Molecular coverage = molecular test done ÷ (done + not-done), among cases with a known
status. Laboratory confirmation = % of cases bacteriologically confirmed. Both are programme-performance metrics and are
therefore computed over notified cases (the place's <i>context</i> — vulnerability — is the ecological layer; performance
is necessarily case-based).</p>
<p><b>Window.</b> The molecular test (Xpert/TRM-TB) was rolled out gradually (0.5% of cases in 2013 → 60% by 2023), so a
12-year pooled coverage would mix the pre-Xpert and Xpert eras and understate current performance. We therefore report
the diagnostic coverage over the recent window <b>2020–2024</b> (with the full roll-out trend shown), while the hotspot,
incidence, outcome and vulnerability analyses use the full 2013–2024 period.</p>
<p><b>Equity analyses.</b> Coverage by vulnerability decile (sector pooled); coverage inside each hotspot type vs the
rest; a unit-level Spearman correlation of all layers (vulnerability, incidence, abandonment, TB mortality (% notified and rate),
molecular coverage, laboratory confirmation). <b>Cross-check.</b> The SIA-SUS TRM-TB count per municipality (residence)
gives an independent supply-side measure (tests per 100k, tests per notified case) compared with the TBWeb coverage.</p>
<p><b>Infrastructure (CNES).</b> Primary-care facilities (Posto/UBS) and X-ray machines (general radiography, excluding
dental/mammography/CT/MRI) per 100,000 adults by municipality. For X-ray we count machines (capacity) rather than mere
facility presence, and also machines per TB case (demand-adjusted), because a facility being present does not mean
adequate capacity for the local burden.</p>

<h2>4. Results</h2>

<h3>4.1 Molecular-test coverage — scaled up, and not inequitable</h3>
<p>Molecular coverage rose steeply with the Xpert roll-out (0.5% in 2013 → 60% by 2023; ~56% in 2020–2024). Crucially,
it is <b>not lower in the vulnerable areas</b> — coverage is flat (~52–57%) across vulnerability deciles 1–9 and rises to
<b>65.7% in the most-vulnerable decile</b>; and it is higher in incidence hotspots (<b>64.5% vs 50.6%</b> elsewhere)
(Figure 1). The under-tested places are the less-vulnerable interior, where laboratory capacity is thinner — not the
metropolitan hotspots.</p>
{fig("fig_molecular_coverage_2013-2024.png","Molecular (TRM-TB) coverage. Left: coverage by place-vulnerability decile (2020–2024) — flat then rising in the most-vulnerable decile. Right: coverage by unit, Greater SP + Baixada (red = low = fragile). The high-burden urban areas are well covered; gaps are elsewhere.")}

<h3>4.2 Laboratory confirmation — same pattern</h3>
<p>Bacteriological confirmation is 74% over the period (77.6% in 2020–2024) and follows the same gradient: it rises from
70.4% in the least-vulnerable decile to <b>82.5% in the most-vulnerable</b>, and is higher in incidence hotspots
(79.9% vs 75.9%) (Figure 2). Again, the more-vulnerable, higher-burden areas are better, not worse, on diagnostic
confirmation.</p>
{fig("fig_lab_confirmation_2013-2024.png","Laboratory (bacteriological) confirmation. Left: by vulnerability decile (2020–2024), rising with vulnerability. Right: by unit, Greater SP + Baixada.")}

<h3>4.3 Diagnostic coverage vs the outcome geographies</h3>
<p>At the unit level, molecular coverage and laboratory confirmation are <b>essentially uncorrelated with abandonment</b>
(ρ = 0.05 and 0.00) and only weakly, positively related to mortality (via urbanicity) (Figure 3). Inside the
abandonment and mortality hotspots, diagnostic coverage is <b>equal to or higher</b> than the rest. So low diagnostic
coverage does <b>not</b> explain the bad-outcome geography — the programme's weak link there is not diagnosis.
Abandonment in particular is a treatment-<i>retention</i> problem, not a diagnostic gap.</p>
{fig("fig_program_vs_outcomes_2013-2024.png","Left: unit-level Spearman correlation of all layers (vulnerability, incidence, abandonment, TB mortality (% notified and rate), molecular coverage, laboratory confirmation). Right: diagnostic coverage inside each hotspot type vs the rest — equal or higher in the bad-outcome areas.")}

<h3>4.4 Independent SIA-SUS cross-check</h3>
<p>The SIA-SUS TRM-TB series (procedure 0202090361, by residence, 2019–2024; 68,168 tests in 2020–2024, 0.83 per
notified case) is an independent supply-side measure. It agrees only <b>weakly</b> with the TBWeb coverage at the
municipal level (ρ = 0.11) and with incidence (ρ = 0.15) (Figure 4). This mostly reflects that SIA-SUS under-captures
molecular testing — much TRM-TB is processed by the state laboratory network (LACEN/IAL) and may not be billed in SIA —
and that the municipal scale collapses the capital into a single unit. SIA-SUS therefore serves as context (testing
volume is large and real) but is a limited validator; the surveillance-based TBWeb coverage remains the trustworthy
sub-municipal measure.</p>
{fig("fig_sia_crosscheck_2013-2024.png","SIA-SUS (independent, municipal) vs TBWeb. Left: SIA tests per notified case vs TBWeb molecular coverage (weak agreement, ρ≈0.11). Right: SIA testing volume vs incidence. SIA under-captures (billing) and is municipal, so it corroborates only weakly.")}

<h3>4.5 Health-system infrastructure (CNES) — primary care vs imaging</h3>
<p>Two ecological infrastructure layers (CNES, municipal) tell <b>opposite</b> stories (Figure 5). <b>Primary care is
pro-equity and protective</b>: primary-care (Posto/UBS) density is higher in more-vulnerable municipalities (ρ = +0.29)
and is associated with <i>lower</i> abandonment (−0.24) and death rate (−0.18) — the public primary-care network is
denser where it is needed and tracks better outcomes. <b>X-ray imaging is the opposite — an access gap</b>: it is thinner
in vulnerable municipalities, and the gap is far larger when measured as machine <i>capacity</i> (ρ = −0.41 for machines
per 100k) than as mere facility presence (−0.22), because one machine may serve a large, overloaded population.
Demand-adjusted (machines per TB case) the most-vulnerable municipalities again have fewer (−0.43); imaging capacity does
not scale with TB burden, with a suggestion of higher mortality where it is scarcest (−0.27). (Municipal resolution;
equipment existence, not utilisation/queues.)</p>
{fig("fig_cnes_infrastructure_2013-2024.png","CNES infrastructure (municipal). Left: primary-care (UBS) density vs vulnerability — pro-equity (denser where more vulnerable). Right: X-ray machine capacity vs vulnerability — an access gap (fewer machines per capita in vulnerable municipalities). Counting machines (capacity), not just facility presence, roughly doubles the measured gap.")}
<p>Mapped across the state (Figure 6 — <b>municipal maps</b>, since CNES has no sub-municipal coordinates), the imaging
gap is visible spatially: X-ray machine capacity is lower across the more-vulnerable municipalities, while primary-care
density does not show the same deficit.</p>
{fig("fig_cnes_municipal_maps_2013-2024.png","MUNICIPAL choropleth maps — São Paulo State (645 municipalities; CNES has no sub-municipal coordinates, so the capital is a single unit). Left: place vulnerability. Middle: primary-care (UBS) density per 100k. Right: X-ray machine capacity per 100k (red = scarce). X-ray capacity thins across the more-vulnerable municipalities.")}

<h3>4.6 Chest X-ray imaging capacity — a graded equity gap</h3>
<p>Of all the programme layers, chest X-ray is the only one that is <b>both scarcer and more demand-mismatched where TB
concentrates</b>, so it merits the same dose-response treatment given to molecular and laboratory diagnosis above.
Ranking the 645 municipalities by their vulnerability and splitting them into ten equal-count deciles (~64–65 each)
produces a clear monotone gradient (Figure 7). Imaging <b>supply</b> falls from <b>22.5 machines per 100k adults</b> in
the least-vulnerable decile to <b>11.9</b> in the most-vulnerable — a <b>1.9× gap</b> per capita. Adjusting for need
(machines per 100 TB cases) widens it further, from <b>6.3 to 2.1 — a 2.9× gap</b>, because the more-vulnerable
municipalities also carry more cases. Unlike molecular and laboratory diagnosis, which scale up <i>toward</i> the
high-burden areas, imaging hardware thins out exactly where the disease is densest. (Municipal resolution; CNES records
equipment existence, not utilisation or queue times, so the effective access gap may be larger still.)</p>
{fig("fig_xray_doseresponse_2013-2024.png","Chest X-ray (general radiography) machine capacity across deciles of municipal vulnerability (645 municipalities, ~64–65 per decile; bars shaded green→red from least to most vulnerable). Left: machines per 100k adults (supply) — 1.9× lower in the most-vulnerable decile. Right: machines per 100 TB cases (demand-adjusted) — 2.9× lower. Counting machines (capacity) not facility presence; excludes dental, mammography, CT/MRI.")}

<h2>5. Key findings</h2>
<ul>
<li><b>Molecular diagnosis has scaled and is not inequitable:</b> coverage ~56% (2020–2024), and it is highest in the most-vulnerable decile (65.7%) and in incidence hotspots (64.5% vs 50.6%). The gap is in the less-vulnerable interior.</li>
<li><b>Laboratory confirmation shows the same pattern</b> (rising with vulnerability; higher in hotspots).</li>
<li><b>Diagnosis is not the weak link where outcomes are bad:</b> diagnostic coverage is ~uncorrelated with abandonment (ρ≈0.0–0.05) and equal/higher in abandonment & mortality hotspots — abandonment is a treatment-retention problem, not a diagnostic gap.</li>
<li><b>The independent SIA-SUS source under-captures</b> (billing; LACEN tests) and corroborates only weakly (ρ≈0.11); TBWeb is the trustworthy sub-municipal measure — itself a finding about administrative data completeness.</li>
<li><b>Primary-care infrastructure is pro-equity and protective:</b> denser in vulnerable municipalities (ρ = +0.29) and associated with less abandonment (−0.24) and death (−0.18).</li>
<li><b>X-ray imaging capacity is the one anti-equity gap:</b> fewer machines per capita in vulnerable municipalities (ρ = −0.41 — roughly double the gap seen from facility presence, −0.22) and fewer per TB case (−0.43); capacity does not scale with burden, with a hint of higher mortality where scarcest (−0.27). Across vulnerability deciles the gradient is monotone: <b>1.9× fewer machines per capita and 2.9× fewer per TB case</b> in the most- vs least-vulnerable decile (Figure 7).</li>
</ul>

<h2>6. Limitations</h2>
<p>(i) Coverage is computed over notified cases (programme performance, by design), not population-level access. (ii) The
diagnostic window is 2020–2024 because of the Xpert roll-out; the full trend is shown. (iii) Municipal SIA-SUS does not
discriminate within the capital and under-captures non-billed (LACEN) tests. (iv) CNES infrastructure is municipal
(capital = one unit) and measures equipment <i>existence</i>, not utilisation or queues — true overload would need
throughput data; the machines-per-case vs incidence correlation is also partly mechanical (cases appear in both).
(v) Treatment-support (DOT/follow-up) and ESF/APS coverage are not yet included and may behave differently.</p>

<h2>7. Next steps</h2>
<ol>
<li><b>Sub-municipal infrastructure</b> (within the capital): geocode CNES facilities by CEP to compute facility density / distance per unit — the municipal CNES cannot discriminate within the capital, where most hotspots are.</li>
<li><b>ESF/APS coverage</b> (e-Gestor/DATASUS) and <b>treatment-support</b> indicators (DOT/follow-up) — the more likely lever for the abandonment geography.</li>
<li>Integrate the confirmed programme-fragility findings into the unified manuscript.</li>
</ol>

<h2>8. Reproducibility</h2>
<p>Repository <code>SP-TB-spatial-analyses</code>: molecular coverage — script 70; laboratory confirmation — script 71;
programme-vs-outcomes correlation — script 72; SIA-SUS cross-check — script 73; CNES infrastructure — script 75; this
report — script 74. Diagnostic fields from TBWeb (<code>tmr_tb</code>, <code>lab_confirmed</code>); SIA-SUS TRM-TB
(procedure 0202090361, by residence); CNES establishments (ST) + equipment (EQ) via pysus (raio-X CODEQUIP 04/05/06)
from DATASUS/TABNET. Scope: adults ≥15, new+relapse; diagnostic coverage 2020–2024 (roll-out), other layers 2013–2024.</p>

<div class="footer">Companion analysis · TB programme fragility (diagnostic axis) · São Paulo 2013–2024 · WHO TB Screening Investment Case (Brazil). Self-contained file — figures embedded.</div>
</div></body></html>"""

H=H.replace("<b>","").replace("</b>","")
out="/tmp/SP_TB_Program_Fragility_Report.html"
with open(out,"w") as f: f.write(H)
print("Saved:",out,f"({os.path.getsize(out)/1e6:.1f} MB) — {N[0]} figures")
