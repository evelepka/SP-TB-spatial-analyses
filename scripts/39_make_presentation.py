"""Generate Reveal.js presentation: TB hotspot bairros — GSP + Baixada Santista."""

import base64, os

def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

print("Encoding images...")
img_lorenz   = b64("/tmp/lorenz_concentration.png")
img_map      = b64("/tmp/bairro_hotspot_map.png")
img_zoom     = b64("/tmp/bairro_hotspot_zoom.png")
img_outcomes = b64("/tmp/tb_outcomes_plot.png")

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>TB Hotspot Bairros — GSP + Baixada Santista</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.6.1/dist/reveal.css"/>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.6.1/dist/theme/white.css"/>
<style>
  :root {{
    --r-heading-color: #1a3d5c;
    --r-link-color: #2980b9;
    --r-background-color: #ffffff;
  }}
  .reveal {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 22px; }}
  .reveal h1 {{ font-size: 1.8em; color: #1a3d5c; }}
  .reveal h2 {{ font-size: 1.3em; color: #1a3d5c; border-bottom: 3px solid #c0392b; padding-bottom: 6px; }}
  .reveal h3 {{ font-size: 1.05em; color: #2c3e50; }}
  .reveal .slides section {{ text-align: left; }}
  .reveal .slides .center {{ text-align: center; }}

  /* ── scale comparison table ── */
  table.scale-tbl {{ width: 100%; border-collapse: collapse; font-size: 0.78em; }}
  table.scale-tbl th {{
    background: #1a3d5c; color: white; padding: 6px 10px; text-align: center;
  }}
  table.scale-tbl td {{ padding: 5px 10px; text-align: center; border-bottom: 1px solid #ddd; }}
  table.scale-tbl tr.highlight td {{ background: #fef9c3; font-weight: bold; }}
  table.scale-tbl tr.highlight td:first-child {{ border-left: 4px solid #c0392b; }}
  .bad  {{ color: #c0392b; }}
  .good {{ color: #27ae60; }}
  .mid  {{ color: #e67e22; }}

  /* ── characteristics table ── */
  table.char-tbl {{ width: 100%; border-collapse: collapse; font-size: 0.72em; }}
  table.char-tbl th {{
    background: #1a3d5c; color: white; padding: 5px 8px; text-align: center;
  }}
  table.char-tbl th.col-hot  {{ background: #c0392b; }}
  table.char-tbl th.col-fcu  {{ background: #2980b9; }}
  table.char-tbl th.col-none {{ background: #7f8c8d; }}
  table.char-tbl td {{ padding: 4px 8px; border-bottom: 1px solid #eee; }}
  table.char-tbl td:not(:first-child) {{ text-align: center; }}
  table.char-tbl tr.section-hdr td {{
    background: #f0f4f8; font-weight: bold; color: #1a3d5c;
    padding-top: 8px; font-size: 0.95em;
  }}
  table.char-tbl .worse {{ color: #c0392b; font-weight: bold; }}
  table.char-tbl .better {{ color: #27ae60; }}

  /* ── outcome mini-bars ── */
  .bar-wrap {{ display: flex; align-items: center; gap: 6px; }}
  .bar {{ height: 14px; border-radius: 3px; display: inline-block; }}

  /* ── callout boxes ── */
  .callout {{
    background: #fef3cd; border-left: 5px solid #f0a500;
    padding: 8px 14px; border-radius: 4px; margin: 8px 0;
    font-size: 0.85em;
  }}
  .callout.red  {{ background: #fde8e8; border-color: #c0392b; }}
  .callout.blue {{ background: #e8f4fd; border-color: #2980b9; }}
  .callout.green{{ background: #e8f8f0; border-color: #27ae60; }}

  /* ── fragment bullets ── */
  .reveal ul {{ margin-left: 1.2em; }}
  .reveal ul li {{ margin-bottom: 6px; }}

  /* ── title slide ── */
  .title-logo {{ font-size: 0.6em; color: #888; margin-top: 1.2em; }}
  .tag {{
    display: inline-block; background: #1a3d5c; color: white;
    padding: 2px 8px; border-radius: 12px; font-size: 0.7em; margin: 2px;
  }}
  .tag.red {{ background: #c0392b; }}
  .tag.blue {{ background: #2980b9; }}

  img.full {{ width: 100%; max-height: 62vh; object-fit: contain; }}
  img.half {{ width: 49%; max-height: 58vh; object-fit: contain; }}
</style>
</head>
<body>
<div class="reveal">
<div class="slides">

<!-- ══════════════════════════════════════════════════════ SLIDE 1: Title -->
<section class="center" data-background="#1a3d5c">
  <h1 style="color:white; font-size:1.9em; border:none;">
    TB Hotspot Bairros<br/>in Metropolitan São Paulo
  </h1>
  <p style="color:#aad4f5; font-size:0.9em; margin-top:0.8em;">
    Geographic targeting for Active Case Finding<br/>
    <strong style="color:white;">Grande SP + Baixada Santista · 2020–2024</strong>
  </p>
  <div style="margin-top:1.4em;">
    <span class="tag">NOVO + RECIDIVA</span>
    <span class="tag">51,676 geocoded cases</span>
    <span class="tag">CNEFE 2022</span>
    <span class="tag red">834 bairros</span>
    <span class="tag blue">46 municipalities</span>
  </div>
  <p class="title-logo" style="color:#aad4f5; margin-top:1.8em;">
    SP-TB-spatial-analyses · Stanford / Johns Hopkins · June 2025
  </p>
</section>

<!-- ══════════════════════════════════════════════════════ SLIDE 2: The question -->
<section>
  <h2>The question: what geographic unit for ACF targeting?</h2>
  <p style="font-size:0.85em; color:#555;">
    We need a unit that is <strong>precise enough</strong> to concentrate cases,
    <strong>stable enough</strong> year-over-year to plan programs,
    and <strong>large enough</strong> to be operationally viable.
  </p>

  <table class="scale-tbl" style="margin-top:0.8em;">
    <thead>
      <tr>
        <th>Unit</th><th>Median pop</th><th>Units (GSP+BS)</th>
        <th>Stability<br/>(Jaccard)</th>
        <th>Concentration<br/>(5% pop)</th>
        <th>% units ≥10k<br/>(operational)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Census sector</td><td>~380</td><td>48,000</td>
        <td class="bad">0.11 ✗</td><td class="good">5.5× ✓</td><td class="bad">0% ✗</td>
      </tr>
      <tr class="highlight">
        <td><strong>Bairro ★</strong></td><td><strong>~8,000</strong></td><td><strong>834</strong></td>
        <td class="mid"><strong>0.40 ~</strong></td>
        <td class="good"><strong>2.6× ✓</strong></td>
        <td class="mid"><strong>44% ~</strong></td>
      </tr>
      <tr>
        <td>Distrito</td><td>~99,000</td><td>173</td>
        <td class="good">0.63 ✓</td><td class="bad">2.1× ~</td><td class="good">100% ✓</td>
      </tr>
    </tbody>
  </table>

  <div class="callout" style="margin-top:1em;">
    <strong>Bairro</strong> (NM_DIST for SP capital · NM_BAIRRO for other municipalities)
    balances all three criteria. Stability is much better than sector level (Jaccard 0.40 vs 0.11)
    while retaining meaningful TB concentration.
  </div>
</section>

<!-- ══════════════════════════════════════════════════════ SLIDE 3: Why not sector -->
<section>
  <h2>Why sectors fail: the small-numbers problem</h2>
  <div style="display:flex; gap:2em; align-items:flex-start; font-size:0.82em;">
    <div style="flex:1;">
      <h3>Census sector (~380 residents)</h3>
      <ul>
        <li>Expected TB cases/sector/year: <strong class="bad">0.17</strong></li>
        <li>Most sectors: <strong>0 or 1 case/year</strong> → huge Poisson noise</li>
        <li>Year-to-year Jaccard: <strong class="bad">0.11</strong> (only 11% of sectors stable)</li>
        <li>Median cluster size: <strong class="bad">395 people</strong> — too small for any program</li>
      </ul>
      <div class="callout red" style="margin-top:0.8em;">
        <strong>Root cause:</strong> instability is <em>statistical</em>, not epidemiological.
        Changing the window size doesn't fix it — the scale is wrong.
      </div>
    </div>
    <div style="flex:1;">
      <h3>Bairro (~8,000 residents)</h3>
      <ul>
        <li>Expected TB cases/bairro/year (hotspot): <strong class="good">8</strong></li>
        <li>IQR cases/year: <strong>3–17</strong> — workable for planning</li>
        <li>Year-to-year Jaccard: <strong class="mid">0.40</strong></li>
        <li>54% of bairros have <strong class="good">≥5,000 pop</strong></li>
      </ul>
      <div class="callout green" style="margin-top:0.8em;">
        <strong>Solution:</strong> Use pooled 5-year rates for identification;
        update targeting every 3–5 years — not annually.
      </div>
    </div>
  </div>
</section>

<!-- ══════════════════════════════════════════════════════ SLIDE 4: Lorenz curve -->
<section>
  <h2>Case concentration — Lorenz curve by bairro</h2>
  <div style="display:flex; gap:1.5em; align-items:center;">
    <div style="flex:1.8;">
      <img class="full" src="data:image/png;base64,{img_lorenz}" alt="Lorenz curve"/>
    </div>
    <div style="flex:1; font-size:0.8em;">
      <h3>Key thresholds</h3>
      <table style="width:100%; border-collapse:collapse; font-size:0.95em;">
        <tr style="background:#f0f4f8;">
          <th style="padding:5px 8px; text-align:left;">Top bairros<br/>(% of pop)</th>
          <th style="padding:5px 8px; text-align:center;">% of cases</th>
        </tr>
        <tr><td style="padding:4px 8px;">5%</td><td style="text-align:center;">13%</td></tr>
        <tr><td style="padding:4px 8px;">10%</td><td style="text-align:center;">22%</td></tr>
        <tr style="background:#fef9c3; font-weight:bold;">
          <td style="padding:4px 8px; border-left:4px solid #c0392b;">20% ★</td>
          <td style="text-align:center; color:#c0392b;">35%</td>
        </tr>
        <tr><td style="padding:4px 8px;">30%</td><td style="text-align:center;">49%</td></tr>
        <tr><td style="padding:4px 8px;">50%</td><td style="text-align:center;">71%</td></tr>
      </table>
      <div class="callout" style="margin-top:1em;">
        <strong>Gini = 0.300</strong><br/>
        Moderate concentration — TB is spatially structured
        but not extreme. The majority of cases still occur
        outside the top areas.
      </div>
      <div class="callout blue" style="margin-top:0.6em;">
        <strong>Selected threshold: 20%</strong><br/>
        191 bairros · 4.2M people · <strong>35% of all cases</strong>
      </div>
    </div>
  </div>
</section>

<!-- ══════════════════════════════════════════════════════ SLIDE 5: Map overview -->
<section>
  <h2>Map: 191 hotspot bairros — GSP + Baixada Santista</h2>
  <img class="full" src="data:image/png;base64,{img_map}" alt="Hotspot bairros map"/>
  <p style="font-size:0.7em; color:#555; text-align:center; margin-top:0.3em;">
    Colour = TB rate /100k·yr (pooled 2020–2024) · Grey = non-selected · Black borders = municipalities
  </p>
</section>

<!-- ══════════════════════════════════════════════════════ SLIDE 6: Zoom maps -->
<section>
  <h2>Zoom: SP capital (distritos) · Baixada Santista (bairros)</h2>
  <img class="full" src="data:image/png;base64,{img_zoom}" alt="Zoom hotspot maps"/>
  <div style="display:flex; gap:2em; font-size:0.72em; color:#555; margin-top:0.4em;">
    <div style="flex:1; text-align:center;">
      <strong>SP capital:</strong> hotspot distritos concentrated in the historic centre
      (Sé, República, Brás) and peripheral distritos in the east and south
    </div>
    <div style="flex:1; text-align:center;">
      <strong>Baixada Santista:</strong> Santos, São Vicente, and Guarujá are
      almost entirely hotspot — TB rates 150–500+/100k, among the highest in the state
    </div>
  </div>
</section>

<!-- ══════════════════════════════════════════════════════ SLIDE 7: Characteristics table -->
<section>
  <h2>Characteristics: selected bairros vs. FCU vs. non-selected</h2>

  <table class="char-tbl">
    <thead>
      <tr>
        <th style="text-align:left; width:36%;">Characteristic</th>
        <th class="col-hot">Hotspot bairros<br/><small>(n=191, 18k cases)</small></th>
        <th class="col-fcu">FCU / favelas<br/><small>(anywhere, 10k cases)</small></th>
        <th class="col-none">Non-selected<br/><small>(rest of region)</small></th>
      </tr>
    </thead>
    <tbody>
      <tr class="section-hdr"><td colspan="4">Population &amp; structure</td></tr>
      <tr>
        <td>Median unit population</td>
        <td>7,177</td><td>—</td><td>8,338</td>
      </tr>
      <tr>
        <td>% pop in FCU/favela</td>
        <td class="worse">19.4%</td><td>100%</td><td>13.4%</td>
      </tr>
      <tr>
        <td>Median income (R$/month)</td>
        <td class="worse">R$ 2,421</td><td class="worse">~R$ 1,800</td><td>R$ 2,918</td>
      </tr>
      <tr>
        <td>Population density /km²</td>
        <td>9,769</td><td>~25,000</td><td>10,300</td>
      </tr>

      <tr class="section-hdr"><td colspan="4">TB burden (pooled 2020–2024)</td></tr>
      <tr>
        <td>TB rate /100k·yr (median)</td>
        <td class="worse">97</td><td class="worse">~220</td><td>23</td>
      </tr>
      <tr>
        <td>Cases/yr per bairro (median)</td>
        <td class="worse">8</td><td>—</td><td>2</td>
      </tr>

      <tr class="section-hdr"><td colspan="4">Treatment outcomes (% of known-outcome cases)</td></tr>
      <tr>
        <td>Treatment success (cure)</td>
        <td class="worse">67.0%</td><td>68.6%</td><td class="better">69.2%</td>
      </tr>
      <tr>
        <td>Loss to follow-up (abandon)</td>
        <td class="worse">17.7%</td><td class="worse">17.2%</td><td class="better">15.1%</td>
      </tr>
      <tr>
        <td>Death from TB</td>
        <td class="worse">5.3%</td><td>4.8%</td><td>4.8%</td>
      </tr>
      <tr>
        <td>Hospitalized</td>
        <td class="worse">29.4%</td><td>27.2%</td><td class="better">24.9%</td>
      </tr>
      <tr>
        <td>HIV co-infection</td>
        <td class="worse">8.5%</td><td>7.5%</td><td>8.4%</td>
      </tr>

      <tr class="section-hdr"><td colspan="4">Discovery route</td></tr>
      <tr>
        <td>Found via Active Case Finding</td>
        <td class="worse">3.6% ↓</td><td>5.1%</td><td class="better">7.6%</td>
      </tr>
      <tr>
        <td>Found via ER / urgency</td>
        <td class="worse">22.2% ↑</td><td class="worse">22.3% ↑</td><td>17.0%</td>
      </tr>
    </tbody>
  </table>
</section>

<!-- ══════════════════════════════════════════════════════ SLIDE 8: ACF paradox -->
<section>
  <h2>The ACF paradox — and what it means</h2>
  <img class="full" src="data:image/png;base64,{img_outcomes}" alt="TB outcomes comparison"/>
  <div class="callout red" style="margin-top:0.6em; font-size:0.78em;">
    <strong>Key finding:</strong> The areas with the <em>highest TB burden</em> (hotspot bairros)
    have the <em>lowest active case-finding rate</em> (3.6% vs 7.6% in non-selected areas).
    TB in these areas is predominantly found via ER — a marker of delayed, crisis-driven diagnosis.
    This is the primary programmatic gap these bairros represent.
  </div>
</section>

<!-- ══════════════════════════════════════════════════════ SLIDE 9: Summary -->
<section data-background="#1a3d5c">
  <h2 style="color:white; border-bottom-color:#c0392b;">Summary</h2>
  <div style="display:flex; gap:2em; font-size:0.82em; color:#dce8f5;">
    <div style="flex:1;">
      <h3 style="color:#aad4f5;">Geographic unit</h3>
      <ul>
        <li>834 bairros (NM_DIST in SP capital)</li>
        <li>Median pop ~8,000 · Jaccard 0.40</li>
        <li>Balances precision, stability, operability</li>
      </ul>
      <h3 style="color:#aad4f5; margin-top:1em;">Concentration</h3>
      <ul>
        <li>Gini = 0.30 — moderate</li>
        <li>Top 20% pop → 191 bairros → <strong style="color:white;">35% of cases</strong></li>
      </ul>
    </div>
    <div style="flex:1;">
      <h3 style="color:#aad4f5;">Who is in the hotspot?</h3>
      <ul>
        <li>Lower income (R$2,421 vs R$2,918)</li>
        <li>Higher FCU share (19% vs 13%)</li>
        <li>4.2M people · 46 municipalities</li>
      </ul>
      <h3 style="color:#aad4f5; margin-top:1em;">The programmatic gap</h3>
      <ul>
        <li>Higher abandonment (17.7% vs 15.1%)</li>
        <li>Higher TB death (5.3% vs 4.8%)</li>
        <li><strong style="color:#f1c40f;">ACF reaching only 3.6%</strong> — vs 7.6% elsewhere</li>
        <li>22% diagnosed via ER (delayed diagnosis)</li>
      </ul>
    </div>
  </div>
</section>

</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/reveal.js@4.6.1/dist/reveal.js"></script>
<script>
  Reveal.initialize({{
    hash: true,
    slideNumber: 'c/t',
    transition: 'slide',
    transitionSpeed: 'fast',
    controls: true,
    progress: true,
    center: false,
    width: 1200,
    height: 700,
    margin: 0.04,
  }});
</script>
</body>
</html>"""

OUT = "/tmp/tb_hotspot_presentation.html"
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Saved: {OUT}")
