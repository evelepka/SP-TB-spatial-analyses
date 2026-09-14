"""High-quality characteristics table — PNG + DOCX.

Outputs:
  /tmp/table_sp_hotspots.png   — publication-quality figure
  /tmp/table_sp_hotspots.docx  — Word table (copy-paste ready)
"""

import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

matplotlib.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
})

# ── DATA ──────────────────────────────────────────────────────────────────────
# Sections with rows. Format: (display_label, sel_value, nosel_value)
# "---" = section separator row
SECTIONS = [
    ("POPULATION & TB BURDEN", None, None),
    ("Number of geographic units",          "300",        "2,750"),
    ("Total population",                    "8,801,695",  "35,039,330"),
    ("% of SP state population",            "20.1%",      "79.9%"),
    ("TB cases 2020–2024 (N)",              "30,254",     "47,021"),
    ("% of SP state TB cases",             "39.2%",      "60.8%"),
    ("TB incidence rate (per 100,000/yr)",  "69",         "27"),
    ("Median unit population",              "8,379",      "2,929"),
    ("Median cases/yr per unit",            "7.6",        "0.4"),

    ("PATIENT CHARACTERISTICS", None, None),
    ("HIV positive (% of HIV-tested)",      "8.9%",       "9.3%"),
    ("Pulmonary TB (%)",                    "84.2%",      "82.5%"),

    ("DISCOVERY ROUTE", None, None),
    ("Outpatient care — patient demand (%)", "52.4%",      "55.1%"),
    ("Emergency/urgency presentation (%)",  "21.9%",      "18.2%"),
    ("Diagnosed during hospitalisation (%)", "16.3%",     "20.2%"),
    ("Active case finding (ACF) (%)",       "4.8%",       "2.4%"),
    ("Contact investigation (%)",           "2.9%",       "2.8%"),

    ("TREATMENT OUTCOMES  (% of known-outcome cases)", None, None),
    ("Treatment success / cure (%)",        "72.3%",      "74.4%"),
    ("Lost to follow-up (%)",               "16.6%",      "13.4%"),
    ("Death from TB (%)",                   "5.1%",       "5.3%"),
    ("Hospitalised during treatment (%)",   "28.4%",      "24.4%"),
]

FOOTNOTE = (
    "SINAN notifications 2020–2024 geocoded to IBGE CNEFE 2022  ·  "
    "Hotspot selection: ≥10 cases/5yr, 20% population window, FCU ≥5,000 pop  ·  "
    "HIV+: % of HIV-tested cases  ·  "
    "Outcomes exclude transfers and diagnostic changes  ·  "
    "43.8M residents  ·  77,275 geocoded cases"
)

# ═══════════════════════════════════════════════════════════════════════════════
# 1. HIGH-QUALITY PNG  — uses explicit pixel-grid via imshow + text overlay
# ═══════════════════════════════════════════════════════════════════════════════

# Build cell data: list of (label, v_sel, v_nos, is_section)
cell_rows = []
for label, v_sel, v_nos in SECTIONS:
    cell_rows.append((label, v_sel, v_nos, v_sel is None))

n_data = sum(1 for *_, s in cell_rows if not s)
n_sec  = sum(1 for *_, s in cell_rows if s)

# Row heights in inches
ROW_H = 0.34
SEC_H = 0.37
HDR_H = 0.60
TITLE_H = 0.38
FOOT_H  = 0.30

# X positions (inches from left margin)
PAD   = 0.25          # left/right margin
C0_W  = 5.8           # label column width
C1_W  = 3.0           # selected column width
C2_W  = 3.0           # non-selected column width
GAP   = 0.06          # gap between columns

FW = PAD + C0_W + GAP + C1_W + GAP + C2_W + PAD
FH = (TITLE_H + HDR_H
      + n_sec  * SEC_H
      + n_data * ROW_H
      + FOOT_H + 0.10)

# Column x centres
X0_L  = PAD + 0.18                           # label left-aligned from here
X1_C  = PAD + C0_W + GAP + C1_W / 2         # selected centre
X2_C  = PAD + C0_W + GAP + C1_W + GAP + C2_W / 2  # non-sel centre
X_TOT = PAD + C0_W + GAP + C1_W + GAP + C2_W      # right edge

# Background x extents for each column
X0_BG = (PAD,                            PAD + C0_W)
X1_BG = (PAD + C0_W + GAP,              PAD + C0_W + GAP + C1_W)
X2_BG = (PAD + C0_W + GAP + C1_W + GAP, X_TOT)

# Colours
C_SEC_BG    = "#2c5282";  C_SEC_FG = "white"
C_HDR_SEL   = "#1a5c3a";  C_HDR_NS = "#4a5568"
C_ROW       = ["#f7fafc", "#edf2f7"]
C_SEL       = ["#e6f4ec", "#d4edda"]
C_NS        = ["#f5f5f5", "#ebebeb"]

fig, ax = plt.subplots(figsize=(FW, FH))
ax.set_xlim(0, FW); ax.set_ylim(0, FH); ax.axis("off")

def fill(ax, x0, x1, y0, y1, color, zorder=1):
    ax.add_patch(patches.Rectangle(
        (x0, y0), x1 - x0, y1 - y0,
        linewidth=0, facecolor=color, zorder=zorder))

def hline(ax, y, color="#cbd5e0", lw=0.5):
    ax.plot([PAD, X_TOT], [y, y], color=color, lw=lw, zorder=3)

# ── Title ─────────────────────────────────────────────────────────────────────
y_cur = FH
ax.text(FW / 2, y_cur - TITLE_H / 2,
        "Characteristics of TB hotspot areas — São Paulo state  ·  2020–2024",
        ha="center", va="center", fontsize=13, fontweight="bold",
        color="#1a202c", zorder=5)
y_cur -= TITLE_H

# ── Column headers ────────────────────────────────────────────────────────────
y0_hdr = y_cur - HDR_H
fill(ax, PAD,    PAD + C0_W,   y0_hdr, y_cur, "white")
fill(ax, X1_BG[0], X1_BG[1],  y0_hdr, y_cur, C_HDR_SEL)
fill(ax, X2_BG[0], X2_BG[1],  y0_hdr, y_cur, C_HDR_NS)

ax.text(X1_C, (y_cur + y0_hdr) / 2,
        "Selected hotspot areas\n(n = 300 units)",
        ha="center", va="center", fontsize=11, fontweight="bold",
        color="white", multialignment="center", zorder=5)
ax.text(X2_C, (y_cur + y0_hdr) / 2,
        "Non-selected areas\n(n = 2,750 units)",
        ha="center", va="center", fontsize=11, fontweight="bold",
        color="white", multialignment="center", zorder=5)
hline(ax, y0_hdr, "#1a3d5c", lw=1.5)
y_cur = y0_hdr

# ── Data rows ─────────────────────────────────────────────────────────────────
data_i = 0
for label, v_sel, v_nos, is_sec in cell_rows:
    rh = SEC_H if is_sec else ROW_H
    y0 = y_cur - rh

    if is_sec:
        fill(ax, PAD, X_TOT, y0, y_cur, C_SEC_BG)
        ax.text(X0_L, (y_cur + y0) / 2, label,
                ha="left", va="center", fontsize=10, fontweight="bold",
                color=C_SEC_FG, zorder=5)
        hline(ax, y0, "#1a3d5c", lw=1.2)
    else:
        ci = data_i % 2
        fill(ax, X0_BG[0], X0_BG[1], y0, y_cur, C_ROW[ci])
        fill(ax, X1_BG[0], X1_BG[1], y0, y_cur, C_SEL[ci])
        fill(ax, X2_BG[0], X2_BG[1], y0, y_cur, C_NS[ci])
        ax.text(X0_L, (y_cur + y0) / 2, label,
                ha="left", va="center", fontsize=10.5,
                color="#1a202c", zorder=5)
        ax.text(X1_C, (y_cur + y0) / 2, v_sel,
                ha="center", va="center", fontsize=10.5,
                fontweight="bold", color="#1a202c", zorder=5)
        ax.text(X2_C, (y_cur + y0) / 2, v_nos,
                ha="center", va="center", fontsize=10.5,
                fontweight="bold", color="#1a202c", zorder=5)
        hline(ax, y0, "#cbd5e0", lw=0.4)
        data_i += 1

    y_cur = y0

# ── Outer border ──────────────────────────────────────────────────────────────
for spine_y in [FH - TITLE_H, y_cur]:
    hline(ax, spine_y, "#2c5282", lw=1.5)

# ── Vertical column dividers ──────────────────────────────────────────────────
for xv in [X1_BG[0], X2_BG[0]]:
    ax.plot([xv, xv], [y_cur, FH - TITLE_H],
            color="#cbd5e0", lw=0.5, zorder=3)

# ── Footnote ──────────────────────────────────────────────────────────────────
ax.text(PAD, y_cur - 0.07, FOOTNOTE,
        ha="left", va="top", fontsize=7.5, color="#718096", style="italic")

plt.tight_layout(pad=0.2)
plt.savefig("/tmp/table_sp_hotspots.png", dpi=250,
            bbox_inches="tight", facecolor="white")
plt.close()
print("Saved /tmp/table_sp_hotspots.png")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. WORD DOCUMENT (.docx)
# ═══════════════════════════════════════════════════════════════════════════════
def rgb(r, g, b):
    return RGBColor(r, g, b)

def set_cell_bg(cell, hex_color):
    """Set cell background colour."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color.lstrip("#"))
    tcPr.append(shd)

def set_cell_borders(cell, top=None, bottom=None, left=None, right=None):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for side, val in [("top", top), ("bottom", bottom),
                      ("left", left), ("right", right)]:
        if val:
            el = OxmlElement(f"w:{side}")
            el.set(qn("w:val"),   val.get("val", "single"))
            el.set(qn("w:sz"),    str(val.get("sz", 4)))
            el.set(qn("w:color"), val.get("color", "auto"))
            tcBorders.append(el)
    tcPr.append(tcBorders)

doc = Document()

# Page margins
for sec in doc.sections:
    sec.top_margin    = Cm(1.8)
    sec.bottom_margin = Cm(1.8)
    sec.left_margin   = Cm(2.2)
    sec.right_margin  = Cm(2.2)

# Title paragraph
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run(
    "Characteristics of TB hotspot areas — São Paulo state · 2020–2024")
run.bold      = True
run.font.size = Pt(13)
run.font.color.rgb = rgb(26, 32, 44)
title.paragraph_format.space_after = Pt(8)

# Table: 3 columns, rows = sections + data rows + 1 header
n_rows = len(SECTIONS) + 1   # +1 for column header row
tbl = doc.add_table(rows=n_rows, cols=3)
tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
tbl.style     = "Table Grid"

# Column widths (cm): label | sel | nosel
col_cm = [8.5, 3.8, 3.8]
for i, row in enumerate(tbl.rows):
    for j, cell in enumerate(row.cells):
        cell.width = Cm(col_cm[j])

THIN_BORDER = {"val": "single", "sz": 4,  "color": "CBD5E0"}
NO_BORDER   = {"val": "none",   "sz": 0,  "color": "auto"}

# ── Header row ────────────────────────────────────────────────────────────────
hdr_row = tbl.rows[0]
hdr_data = [
    ("", "FFFFFF"),
    ("Selected hotspot areas\n(n = 300 units)", "1a5c3a"),
    ("Non-selected areas\n(n = 2,750 units)",   "4a5568"),
]
for j, (txt, bg) in enumerate(hdr_data):
    cell = hdr_row.cells[j]
    set_cell_bg(cell, "#" + bg)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    run = p.add_run(txt)
    run.bold           = True
    run.font.size      = Pt(10.5)
    run.font.color.rgb = rgb(255, 255, 255)
    set_cell_borders(cell,
        top=THIN_BORDER, bottom=THIN_BORDER,
        left=THIN_BORDER, right=THIN_BORDER)

# ── Data / section rows ───────────────────────────────────────────────────────
ODD_ROW_BG  = "f7fafc"
EVEN_ROW_BG = "edf2f7"
ODD_SEL_BG  = "e6f4ec"
EVEN_SEL_BG = "d4edda"
ODD_NS_BG   = "f5f5f5"
EVEN_NS_BG  = "ebebeb"
SEC_BG      = "2c5282"

data_i = 0
for r_idx, (label, v_sel, v_nos) in enumerate(SECTIONS):
    row = tbl.rows[r_idx + 1]
    is_sec = (v_sel is None)

    if is_sec:
        # Merge all 3 cells for section header
        row.cells[0].merge(row.cells[2])
        cell = row.cells[0]
        set_cell_bg(cell, "#" + SEC_BG)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after  = Pt(3)
        run = p.add_run(label)
        run.bold           = True
        run.font.size      = Pt(10)
        run.font.color.rgb = rgb(255, 255, 255)
        set_cell_borders(cell,
            top={"val":"single","sz":6,"color":"1a3d5c"},
            bottom={"val":"single","sz":6,"color":"1a3d5c"},
            left=THIN_BORDER, right=THIN_BORDER)
    else:
        even   = (data_i % 2 == 0)
        row_bg = ODD_ROW_BG  if even else EVEN_ROW_BG
        sel_bg = ODD_SEL_BG  if even else EVEN_SEL_BG
        ns_bg  = ODD_NS_BG   if even else EVEN_NS_BG
        bgs    = [row_bg, sel_bg, ns_bg]
        vals   = [label, v_sel, v_nos]
        aligns = [WD_ALIGN_PARAGRAPH.LEFT,
                  WD_ALIGN_PARAGRAPH.CENTER,
                  WD_ALIGN_PARAGRAPH.CENTER]

        for j in range(3):
            cell = row.cells[j]
            set_cell_bg(cell, "#" + bgs[j])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = aligns[j]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after  = Pt(2)
            run = p.add_run(vals[j])
            run.font.size = Pt(10.5)
            run.bold      = (j > 0)
            run.font.color.rgb = rgb(26, 32, 44)
            set_cell_borders(cell,
                top=THIN_BORDER, bottom=THIN_BORDER,
                left=THIN_BORDER, right=THIN_BORDER)

        data_i += 1

# Footnote
fn = doc.add_paragraph()
fn.alignment = WD_ALIGN_PARAGRAPH.LEFT
fn.paragraph_format.space_before = Pt(5)
run = fn.add_run(FOOTNOTE)
run.italic         = True
run.font.size      = Pt(8)
run.font.color.rgb = rgb(113, 128, 150)

doc.save("/tmp/table_sp_hotspots.docx")
print("Saved /tmp/table_sp_hotspots.docx")
