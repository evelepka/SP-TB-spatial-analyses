"""Build the manuscript RESULTS Word document: Table 1 (descriptive characteristics of the regions,
episode-level base) + the four-question skeleton for writing the results prose.
Output: Drive .../SP-TB-spatial-analyses/Reports/SP_TB_Manuscript_Results.docx
"""
import pandas as pd
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.shared import Inches
OUT=("/DATA_ROOT/WHO modelling Project/SP-TB-spatial-analyses/Reports/SP_TB_Manuscript_Results.docx")
t=pd.read_csv("/tmp/table1.csv").set_index("group")
GROUPS=["Metropolitan — hotspot","Metropolitan — non-hotspot","Interior — hotspot",
        "Interior — non-hotspot","Favela regions (subset)","State total"]
COLHEAD=["Metropolitan\nhotspot","Metropolitan\nnon-hotspot","Interior\nhotspot",
         "Interior\nnon-hotspot","Favela regions*","State total"]
def g(grp,col): return t.loc[grp,col]
# NOTE: Table 1 in the live Results.docx is now rebuilt IN PLACE by script 118 (full version:
# burden · clinical profile · mode of detection · treatment outcome · place characteristics).
# The ROWS below are the LEGACY renderer (burden + sociodemographic only) — do NOT rerun this
# script to regenerate the hand-edited doc; use 112 -> 118 to refresh Table 1.
ROWS=[  # (label, formatter) — LEGACY, superseded by script 118

 ("No. of regions", lambda x:f"{int(g(x,'n_reg')):,}"),
 ("Adult population, n (%)", lambda x:f"{int(g(x,'pop')):,} ({g(x,'pop_pct'):.1f})"),
 ("Incident TB cases, n (%)", lambda x:f"{int(g(x,'cases')):,} ({g(x,'cases_pct'):.1f})"),
 ("TB incidence, /100 000/year", lambda x:f"{g(x,'inc'):.1f}"),
 ("TB mortality, /100 000/year", lambda x:f"{g(x,'mort'):.1f}"),
 ("Loss to follow-up, %", lambda x:f"{g(x,'aband_pct'):.1f}"),
 ("Household income, R$ (mean)", lambda x:f"{int(round(g(x,'income'))):,}"),
 ("Adult illiteracy, %", lambda x:f"{g(x,'illit'):.1f}"),
 ("Residents per household", lambda x:f"{g(x,'residents'):.1f}"),
 ("Favela population, %", lambda x:f"{g(x,'favela_pct'):.1f}"),
 ("Vulnerability index (z-score)", lambda x:f"{g(x,'vuln'):+.2f}"),
]

doc=Document()
sec=doc.sections[0]; sec.orientation=WD_ORIENT.LANDSCAPE
sec.page_width,sec.page_height=Inches(11),Inches(8.5)
for m in ("left_margin","right_margin","top_margin","bottom_margin"): setattr(sec,m,Inches(0.7))
st=doc.styles["Normal"]; st.font.name="Calibri"; st.font.size=Pt(11)
h=doc.add_heading("Results",level=0)

sp=doc.add_heading("Study population",level=1)
for rr in sp.runs: rr.font.color.rgb=RGBColor(0x0d,0x2b,0x45)
flow=doc.add_paragraph(
 "Between 2013 and 2024, 270,492 tuberculosis notifications were recorded in São Paulo State. We "
 "excluded 7,132 in children (<15 years) and 308 with missing age, leaving 263,052 in adults. A "
 "further 24,484 were re-treatment notifications — re-entry after previous loss to follow-up (21,054), "
 "after treatment failure or drug resistance (1,903), or after a regimen change for intolerance or "
 "toxicity (1,527) — which represent the continuation of an ongoing episode rather than a new incident "
 "event; new and relapse notifications were retained, leaving 238,568 incident episodes. Of these, "
 "28,565 in incarcerated people and 9,711 in people with no fixed residence were excluded, as neither "
 "can be assigned to a residential census sector, leaving 200,292 with a standard residential address. "
 "After removing 185 duplicate notification records — the same person's new or relapse notification "
 "entered more than once in the same year — 200,107 unique incident episodes remained, of which "
 "192,161 (96.0%) were geocoded to a residential region and formed "
 "the analytic set; the remaining 7,946 (4.0%) could not be matched — the address was not found in the "
 "registry or fell outside the residential sector frame (study flow, Supplementary Figure S1).")
flow.paragraph_format.space_after=Pt(8)

geo=doc.add_paragraph(
 "Among the geocoded episodes, 90.2% were located at street level or better — to the exact "
 "street and number (T1, 58.6%), the street (T2, 21.3%), or an approximate street match (T3, 10.3%) — "
 "with 1.9% assigned to a neighbourhood centroid (T4) and 7.9% to a postal-code centroid (T5) "
 "(Supplementary Table S1). Findings were materially unchanged when the coarsest (postal-code-level, "
 "T5) assignments were excluded.")
geo.paragraph_format.space_after=Pt(8)

cap=doc.add_paragraph()
r=cap.add_run("Table 1. "); r.bold=True
cap.add_run("Characteristics of the regions of São Paulo State by incidence-hotspot status and "
            "location, adults ≥15 years, 2013–2024 (episode-level; regionalisation units).")
cap.paragraph_format.space_after=Pt(4)

tab=doc.add_table(rows=len(ROWS)+1,cols=len(GROUPS)+1); tab.style="Light Grid Accent 1"
hdr=tab.rows[0].cells
hdr[0].text=""
for j,ch in enumerate(COLHEAD):
    hdr[j+1].text=ch
    for p in hdr[j+1].paragraphs:
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        for rr in p.runs: rr.font.bold=True; rr.font.size=Pt(9)
for i,(lab,fmt) in enumerate(ROWS):
    cells=tab.rows[i+1].cells
    cells[0].text=lab
    for rr in cells[0].paragraphs[0].runs: rr.font.size=Pt(9)
    for j,grp in enumerate(GROUPS):
        cells[j+1].text=fmt(grp)
        for p in cells[j+1].paragraphs:
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            for rr in p.runs: rr.font.size=Pt(9)
fn=doc.add_paragraph()
fr=fn.add_run("* Favela regions are a cross-cutting subset (they also belong to the metropolitan / "
              "interior × hotspot groups). Hotspot = the regions holding the top 20% of the adult "
              "population when ranked by age-standardised TB incidence. Rates are crude; income is the "
              "population-weighted mean of the household-head income. Vulnerability index is the "
              "population-weighted mean of the composite z-score.")
fr.font.size=Pt(8.5); fr.font.color.rgb=RGBColor(0x5b,0x6b,0x7a)

ov=doc.add_paragraph(
 "Adult tuberculosis was markedly concentrated and tracked social deprivation (Table 1). The 17.4% of "
 "the adult population living in metropolitan hotspot regions carried 42.3% of all incident cases, at "
 "108 per 100 000 per year — nearly three times the State rate of 44.6. These regions were the most "
 "deprived within the metropolitan area (mean household income R$2,620 vs R$4,791 in non-hotspot areas; "
 "17.8% favela population). Favela regions, 7.6% of the population, carried 12.5% of cases at 72.9 per "
 "100 000 and had the lowest income (R$1,701) and the highest illiteracy (6.4%) and treatment "
 "loss to follow-up (14.9%). The interior non-hotspot regions — nearly half the population (46.5%) — carried "
 "a quarter of cases at 25.5 per 100 000.")
ov.paragraph_format.space_before=Pt(8); ov.paragraph_format.space_after=Pt(8)

# ── results by question (P1 written; P2–P4 to come) ───────────────────────────
doc.add_paragraph()
P1=("All three outcomes were geographically concentrated (Figure 1). Concentration estimates were "
    "de-noised by split-sample cross-fit, because the sparser events (mortality and loss to follow-up) inflate "
    "the naïve index (Supplementary Figure S2). The 20% of the adult population living in the highest-rate "
    "regions accounted for 45% of incident tuberculosis, 49% of loss to follow-up and 39% of "
    "tuberculosis mortality (de-noised Gini 0.39, 0.42 and 0.28, respectively). Loss to follow-up was "
    "therefore the most spatially concentrated lens, ahead of incidence and mortality. Concentration "
    "increased steadily at finer thresholds: the 5% of the population in the highest-rate regions already "
    "held 19% of incident tuberculosis and 22% of loss to follow-up (Figure 1b).")
SECTIONS=[("Geographic concentration of tuberculosis (Question 1)",P1),
          ("Place vulnerability and the hotspots (Question 2)",None),
          ("Overlap between the incidence, mortality and loss to follow-up hotspots (Question 3)",None),
          ("Temporal stability (Question 4)",None)]
for q,txt in SECTIONS:
    hh=doc.add_heading(q,level=1)
    for rr in hh.runs: rr.font.color.rgb=RGBColor(0x0d,0x2b,0x45)
    if txt:
        doc.add_paragraph(txt)
    else:
        p=doc.add_paragraph("[to be written]")
        for rr in p.runs: rr.italic=True; rr.font.color.rgb=RGBColor(0x99,0x99,0x99)

print("Results doc: supplementary material moved to the standalone Supplementary document.")

doc.save(OUT)
print("Saved:",OUT)

