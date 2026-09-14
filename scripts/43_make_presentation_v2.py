"""Generate Reveal.js presentation v2 — with corrected FCU rates, population denominators,
and blend targeting analysis slide."""

import base64

def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

print("Encoding images...")
img_lorenz   = b64("/tmp/lorenz_concentration.png")
img_map      = b64("/tmp/bairro_hotspot_map.png")
img_zoom     = b64("/tmp/bairro_hotspot_zoom.png")
img_outcomes = b64("/tmp/tb_outcomes_plot.png")
img_blend    = b64("/tmp/blend_targeting_comparison.png")

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>TB Hotspot Bairros — GSP + Baixada Santista v2</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.6.1/dist/reveal.css"/>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.6.1/dist/theme/white.css"/>
<style>
  :root {{ --r-heading-color: #1a3d5c; --r-link-color: #2980b9; --r-background-color: #ffffff; }}
  .reveal {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 22px; }}
  .reveal h1 {{ font-size: 1.8em; color: #1a3d5c; }}
  .reveal h2 {{ font-size: 1.3em; color: #1a3d5c; border-bottom: 3px solid #c0392b; padding-bottom: 6px; }}
  .reveal h3 {{ font-size: 1.05em; color: #2c3e50; }}
  .reveal .slides section {{ text-align: left; }}
  .reveal .slides .center {{ text-align: center; }}
  .reveal ul {{ margin-left: 1.2em; }}
  .reveal ul li {{ margin-bottom: 5px; }}

  table.scale-tbl {{ width:100%; border-collapse:collapse; font-size:0.78em; }}
  table.scale-tbl th {{ background:#1a3d5c; color:white; padding:6px 10px; text-align:center; }}
  table.scale-tbl td {{ padding:5px 10px; text-align:center; border-bottom:1px solid #ddd; }}
  table.scale-tbl tr.highlight td {{ background:#fef9c3; font-weight:bold; }}
  table.scale-tbl tr.highlight td:first-child {{ border-left:4px solid #c0392b; }}

  table.char-tbl {{ width:100%; border-collapse:collapse; font-size:0.70em; }}
  table.char-tbl th {{ background:#1a3d5c; color:white; padding:5px 8px; text-align:center; }}
  table.char-tbl th.col-hot  {{ background:#c0392b; }}
  table.char-tbl th.col-fcu  {{ background:#2980b9; }}
  table.char-tbl th.col-none {{ background:#7f8c8d; }}
  table.char-tbl td {{ padding:4px 8px; border-bottom:1px solid #eee; }}
  table.char-tbl td:not(:first-child) {{ text-align:center; }}
  table.char-tbl tr.pop-row td {{ background:#1a3d5c; color:white; font-weight:bold; font-size:1.05em; padding:6px 8px; }}
  table.char-tbl tr.pop-row td:not(:first-child) {{ text-align:center; }}
  table.char-tbl tr.section-hdr td {{ background:#f0f4f8; font-weight:bold; color:#1a3d5c; padding-top:7px; font-size:0.95em; }}
  .worse  {{ color:#c0392b; font-weight:bold; }}
  .better {{ color:#27ae60; }}
  .note   {{ font-size:0.75em; color:#777; font-style:italic; }}

  table.blend-tbl {{ width:100%; border-collapse:collapse; font-size:0.72em; }}
  table.blend-tbl th {{ background:#1a3d5c; color:white; padding:5px 8px; text-align:center; }}
  table.blend-tbl td {{ padding:4px 8px; border-bottom:1px solid #eee; text-align:center; }}
  table.blend-tbl td:first-child {{ text-align:left; font-weight:bold; }}
  table.blend-tbl tr.best td {{ background:#e8f8e8; }}
  table.blend-tbl tr.best td:first-child {{ border-left:4px solid #27ae60; }}

  .callout {{ background:#fef3cd; border-left:5px solid #f0a500; padding:7px 14px; border-radius:4px; margin:7px 0; font-size:0.82em; }}
  .callout.red   {{ background:#fde8e8; border-color:#c0392b; }}
  .callout.blue  {{ background:#e8f4fd; border-color:#2980b9; }}
  .callout.green {{ background:#e8f8f0; border-color:#27ae60; }}

  .tag {{ display:inline-block; background:#1a3d5c; color:white; padding:2px 8px; border-radius:12px; font-size:0.7em; margin:2px; }}
  .tag.red  {{ background:#c0392b; }}
  .tag.blue {{ background:#2980b9; }}
  .tag.gold {{ background:#c87000; }}

  .bad  {{ color:#c0392b; }}
  .good {{ color:#27ae60; }}
  .mid  {{ color:#e67e22; }}
  img.full {{ width:100%; max-height:62vh; object-fit:contain; }}
</style>
</head>
<body>
<div class="reveal">
<div class="slides">

<!-- ══════ SLIDE 1: Title ══════ -->
<section class="center" data-background="#1a3d5c">
  <h1 style="color:white; font-size:1.9em; border:none;">TB Hotspot Bairros<br/>in Metropolitan São Paulo</h1>
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
    <span class="tag gold">22.3M population</span>
  </div>
  <p style="color:#aad4f5; font-size:0.6em; margin-top:1.8em;">
    SP-TB-spatial-analyses · Stanford / Johns Hopkins · June 2025
  </p>
</section>

<!-- ══════ SLIDE 2: Unit selection rationale ══════ -->
<section>
  <h2>Choosing the geographic unit: multi-scale analysis</h2>
  <p style="font-size:0.85em; color:#555;">
    We need a unit <strong>precise enough</strong> to concentrate cases,
    <strong>stable enough</strong> year-over-year to plan programs,
    and <strong>large enough</strong> to be operationally viable.
  </p>
  <table class="scale-tbl" style="margin-top:0.8em;">
    <thead>
      <tr><th>Unit</th><th>Median pop</th><th>Units (GSP+BS)</th>
          <th>Stability (Jaccard)</th><th>Concentration (5% pop)</th><th>% units ≥10k (operational)</th></tr>
    </thead>
    <tbody>
      <tr>
        <td>Census sector</td><td>~380</td><td>48,000</td>
        <td class="bad">0.11 ✗</td><td class="good">5.5× ✓</td><td class="bad">0% ✗</td>
      </tr>
      <tr class="highlight">
        <td><strong>Bairro ★</strong></td><td><strong>~8,000</strong></td><td><strong>834</strong></td>
        <td class="mid"><strong>0.40 ~</strong></td><td class="good"><strong>2.6× ✓</strong></td><td class="mid"><strong>44% ~</strong></td>
      </tr>
      <tr>
        <td>Distrito</td><td>~99,000</td><td>173</td>
        <td class="good">0.63 ✓</td><td class="mid">2.1× ~</td><td class="good">100% ✓</td>
      </tr>
    </tbody>
  </table>
  <div class="callout" style="margin-top:0.9em;">
    <strong>Hybrid bairro unit:</strong> NM_DIST for SP capital (96 distritos) + NM_BAIRRO for other municipalities
    = 834 units · Jaccard 0.40 at 20% window
  </div>
</section>

<!-- ══════ SLIDE 3: Why not sectors ══════ -->
<section>
  <h2>Why sectors fail: the small-numbers problem</h2>
  <div style="display:flex; gap:2em; align-items:flex-start; font-size:0.82em;">
    <div style="flex:1;">
      <h3>Census sector (~380 residents)</h3>
      <ul>
        <li>Expected TB cases/sector/year: <strong class="bad">0.17</strong></li>
        <li>Most sectors: 0 or 1 case/year → huge Poisson noise</li>
        <li>Year-to-year Jaccard: <strong class="bad">0.11</strong></li>
        <li>Median cluster size: <strong class="bad">395 people</strong></li>
      </ul>
      <div class="callout red" style="margin-top:0.8em;">
        Instability is <em>statistical</em>, not epidemiological. Changing the window doesn't fix it — the scale is wrong.
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
        Use pooled 5-year rates for identification. Update targeting every 3–5 years.
      </div>
    </div>
  </div>
</section>

<!-- ══════ SLIDE 4: Lorenz curve ══════ -->
<section>
  <h2>Case concentration — Lorenz curve by bairro</h2>
  <div style="display:flex; gap:1.5em; align-items:center;">
    <div style="flex:1.8;"><img class="full" src="data:image/png;base64,{img_lorenz}" alt="Lorenz curve"/></div>
    <div style="flex:1; font-size:0.8em;">
      <h3>Key thresholds</h3>
      <table style="width:100%; border-collapse:collapse; font-size:0.95em;">
        <tr style="background:#f0f4f8;"><th style="padding:5px 8px; text-align:left;">Top bairros (% pop)</th><th style="padding:5px 8px; text-align:center;">% of cases</th></tr>
        <tr><td style="padding:4px 8px;">5%</td><td style="text-align:center;">13%</td></tr>
        <tr><td style="padding:4px 8px;">10%</td><td style="text-align:center;">22%</td></tr>
        <tr style="background:#fef9c3; font-weight:bold;">
          <td style="padding:4px 8px; border-left:4px solid #c0392b;">20% ★</td>
          <td style="text-align:center; color:#c0392b;">35%</td>
        </tr>
        <tr><td style="padding:4px 8px;">30%</td><td style="text-align:center;">49%</td></tr>
        <tr><td style="padding:4px 8px;">50%</td><td style="text-align:center;">71%</td></tr>
      </table>
      <div class="callout" style="margin-top:1em;"><strong>Gini = 0.300</strong><br/>Moderate concentration — TB is spatially structured but not extreme.</div>
      <div class="callout blue" style="margin-top:0.6em;"><strong>Selected threshold: 20%</strong><br/>191 bairros · 4.5M people · <strong>35% of cases</strong></div>
    </div>
  </div>
</section>

<!-- ══════ SLIDE 5: Map overview ══════ -->
<section>
  <h2>Map: 191 hotspot bairros — GSP + Baixada Santista</h2>
  <img class="full" src="data:image/png;base64,{img_map}" alt="Hotspot bairros map"/>
  <p style="font-size:0.7em; color:#555; text-align:center; margin-top:0.3em;">
    Colour = TB rate /100k·yr (pooled 2020–2024) · Grey = non-selected · Black = municipality borders
  </p>
</section>

<!-- ══════ SLIDE 6: Zoom maps ══════ -->
<section>
  <h2>Zoom: SP capital (distritos) · Baixada Santista (bairros)</h2>
  <img class="full" src="data:image/png;base64,{img_zoom}" alt="Zoom maps"/>
  <div style="display:flex; gap:2em; font-size:0.72em; color:#555; margin-top:0.4em;">
    <div style="flex:1; text-align:center;"><strong>SP capital:</strong> historic centre (Sé, República, Brás) + peripheral eastern/southern distritos</div>
    <div style="flex:1; text-align:center;"><strong>Baixada Santista:</strong> Santos, São Vicente, Guarujá almost entirely hotspot — rates 150–500+/100k</div>
  </div>
</section>

<!-- ══════ SLIDE 7: Characteristics table (UPDATED) ══════ -->
<section>
  <h2>Characteristics: hotspot bairros vs. FCU vs. non-selected</h2>
  <table class="char-tbl">
    <thead>
      <tr>
        <th style="text-align:left; width:36%;">Characteristic</th>
        <th class="col-hot">Hotspot bairros<br/><small>(n=192, 18k cases)</small></th>
        <th class="col-fcu">All FCU sectors<br/><small>(2,550 named FCUs)</small></th>
        <th class="col-none">Non-selected<br/><small>(rest of region)</small></th>
      </tr>
    </thead>
    <tbody>
      <!-- POPULATION ROW — highlighted -->
      <tr class="pop-row">
        <td>Population (% of GSP+Baixada, 22.3M)</td>
        <td>4.50M <span style="color:#ffdd99;">(20.2%)</span></td>
        <td>3.25M <span style="color:#aad4f5;">(14.6%)</span></td>
        <td>17.8M <span style="color:#ccc;">(79.8%)</span></td>
      </tr>
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
        <td class="worse">R$2,421</td><td class="worse">~R$1,800</td><td>R$2,918</td>
      </tr>
      <tr>
        <td>Pop density /km²</td>
        <td>9,769</td><td>~25,000</td><td>10,300</td>
      </tr>
      <tr class="section-hdr"><td colspan="4">TB burden (pooled 2020–2024)</td></tr>
      <tr>
        <td>TB rate /100k·yr<br/><span class="note">(pop-weighted mean)</span></td>
        <td class="worse"><strong>85</strong></td>
        <td>64 <span class="note">†</span></td>
        <td class="better">37</td>
      </tr>
      <tr>
        <td>Cases/yr per unit (median)</td>
        <td class="worse">8</td><td>—</td><td>2</td>
      </tr>
      <tr class="section-hdr"><td colspan="4">Treatment outcomes (% of known-outcome cases)</td></tr>
      <tr><td>Treatment success</td><td class="worse">67.0%</td><td>68.6%</td><td class="better">69.2%</td></tr>
      <tr><td>Loss to follow-up (abandon)</td><td class="worse">17.7%</td><td class="worse">17.2%</td><td class="better">15.1%</td></tr>
      <tr><td>Death from TB</td><td class="worse">5.3%</td><td>4.8%</td><td>4.8%</td></tr>
      <tr><td>Hospitalized</td><td class="worse">29.4%</td><td>27.2%</td><td class="better">24.9%</td></tr>
      <tr class="section-hdr"><td colspan="4">Discovery route</td></tr>
      <tr><td>Found via ACF</td><td class="worse">3.6% ↓</td><td>5.1%</td><td class="better">7.6%</td></tr>
      <tr><td>Found via ER / urgency</td><td class="worse">22.2% ↑</td><td class="worse">22.3% ↑</td><td>17.0%</td></tr>
    </tbody>
  </table>
  <p class="note" style="margin-top:0.4em;">
    † FCU overall rate is lower than hotspot bairros because many small FCUs are in low-burden municipalities.
    Top FCUs: Paraisópolis 96/100k, Vila Esperança 106, Quarentenário 139, Jardim Iporanga 173.
  </p>
</section>

<!-- ══════ SLIDE 8: Should we blend? ══════ -->
<section>
  <h2>Should we blend bairros + FCUs for targeting?</h2>
  <img class="full" src="data:image/png;base64,{img_blend}" alt="Blend targeting comparison"/>
</section>

<!-- ══════ SLIDE 9: Blend analysis — key insight ══════ -->
<section>
  <h2>The case for a targeted supplement — not a full blend</h2>
  <div style="display:flex; gap:1.6em; font-size:0.80em;">
    <div style="flex:1.1;">
      <h3>Why a full FCU overlay doesn't help</h3>
      <ul>
        <li>2,550 named FCUs — <strong class="bad">median pop only ~500</strong></li>
        <li>Only 82 FCUs have ≥5,000 pop (viable for ACF)</li>
        <li>FCU rate <em>overall</em> (64/100k) &lt; hotspot bairros (85/100k)</li>
        <li>High-rate FCUs are <strong>already inside</strong> hotspot bairros</li>
        <li>Adding all FCUs dilutes concentration: 37% → 35% cases</li>
      </ul>
      <div class="callout red" style="margin-top:0.7em;">
        A full blend <strong>reduces</strong> concentration while tripling unit count.
      </div>
      <h3 style="margin-top:1em;">The structural gap: dilution in wealthy districts</h3>
      <ul>
        <li><strong>Paraisópolis</strong> (58k pop, <strong>96/100k</strong>) sits inside <em>Vila Andrade</em> district</li>
        <li>Vila Andrade overall rate: <strong>55/100k</strong> — diluted by wealthy neighbors</li>
        <li>→ NOT captured by hotspot bairro approach</li>
        <li>52 large FCUs (≥5k) total are missed this way</li>
      </ul>
    </div>
    <div style="flex:1;">
      <h3>Recommendation: hotspot bairros + supplement</h3>
      <table class="blend-tbl">
        <thead>
          <tr><th style="text-align:left;">Approach</th><th>Units</th><th>% pop</th><th>% cases</th><th>Rate</th></tr>
        </thead>
        <tbody>
          <tr><td>A. Hotspot bairros (20%)</td><td>192</td><td>20.2%</td><td>36.9%</td><td>85</td></tr>
          <tr><td>B. All FCUs ≥5k</td><td>82</td><td>3.7%</td><td>6.0%</td><td>75</td></tr>
          <tr><td>D. Blend: FCU≥2k + bairros</td><td>569</td><td>20.2%</td><td>35.2%</td><td>81</td></tr>
          <tr class="best"><td>★ Bairros + supplement FCUs</td><td>244</td><td>22.7%</td><td>40.0%</td><td>82</td></tr>
        </tbody>
      </table>
      <div class="callout green" style="margin-top:0.8em;">
        <strong>★ Recommended:</strong> 192 hotspot bairros <em>+</em> 52 named FCUs ≥5k that are not already captured.
        Gains +3.1 pp of cases at only +2.5% more population. All units are well-circumscribed (IBGE boundaries) and large enough for ACF programs.
      </div>
      <p class="note">Key supplement FCUs: Paraisópolis (58k, 96/100k), Jardim Iporanga/Esmeralda (7k, 173/100k), Tamarutaca (5k, 101/100k), Vila Boa Vista/Santana (6k, 111/100k)</p>
    </div>
  </div>
</section>

<!-- ══════ SLIDE 10: ACF paradox ══════ -->
<section>
  <h2>The ACF paradox</h2>
  <img class="full" src="data:image/png;base64,{img_outcomes}" alt="TB outcomes by group"/>
  <div class="callout red" style="margin-top:0.6em; font-size:0.78em;">
    <strong>Key finding:</strong> Areas with the highest TB burden (hotspot bairros) have the lowest active case-finding rate (3.6% vs 7.6%).
    TB here is predominantly found via ER — a marker of delayed, crisis-driven diagnosis.
    This is the primary programmatic gap these bairros represent.
  </div>
</section>

<!-- ══════ SLIDE 11: Summary ══════ -->
<section data-background="#1a3d5c">
  <h2 style="color:white; border-bottom-color:#c0392b;">Summary</h2>
  <div style="display:flex; gap:2em; font-size:0.80em; color:#dce8f5;">
    <div style="flex:1;">
      <h3 style="color:#aad4f5;">Geographic unit</h3>
      <ul>
        <li>834 hybrid bairros (NM_DIST in SP capital)</li>
        <li>Median pop ~8,000 · Jaccard 0.40</li>
        <li>Balances precision, stability, operability</li>
      </ul>
      <h3 style="color:#aad4f5; margin-top:1em;">Concentration</h3>
      <ul>
        <li>Gini = 0.30 — moderate</li>
        <li>Top 20% pop → 192 bairros → <strong style="color:white;">35% of cases</strong></li>
        <li>Regional total pop: <strong style="color:white;">22.3M</strong></li>
      </ul>
    </div>
    <div style="flex:1;">
      <h3 style="color:#aad4f5;">Who is in the hotspot?</h3>
      <ul>
        <li>4.50M people (20.2% of region)</li>
        <li>Income R$2,421 vs R$2,918 non-selected</li>
        <li>FCU share 19.4% vs 13.4%</li>
      </ul>
      <h3 style="color:#aad4f5; margin-top:1em;">Recommendation</h3>
      <ul>
        <li><strong style="color:white;">192 hotspot bairros</strong> as primary unit</li>
        <li><strong style="color:#f1c40f;">+ 52 supplement FCUs</strong> ≥5k not already captured</li>
        <li>→ 244 units · 22.7% of pop · <strong style="color:white;">40% of cases</strong></li>
        <li>ACF reaching only <strong style="color:#f1c40f;">3.6%</strong> in hotspot areas (vs 7.6% elsewhere)</li>
      </ul>
    </div>
  </div>
</section>

</div>
</div>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@4.6.1/dist/reveal.js"></script>
<script>
  Reveal.initialize({{
    hash: true, slideNumber: 'c/t', transition: 'slide', transitionSpeed: 'fast',
    controls: true, progress: true, center: false, width: 1200, height: 700, margin: 0.04,
  }});
</script>
</body>
</html>"""

OUT = "/tmp/tb_hotspot_presentation_v2.html"
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Saved: {OUT} ({len(html)//1024} kB)")
