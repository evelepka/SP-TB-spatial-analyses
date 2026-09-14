"""Appendix v11 -> v12 as tracked changes.
Aligns the LTFU (per-evaluated-episode) concentration values with the regenerated
main-text Figure 2, and documents the cross-fitting implementation for a proportion outcome.
"""
import copy, os, re, zipfile, sys
from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML = "{http://www.w3.org/XML/1998/namespace}"
AUTHOR, DATE = "Editor", "2026-09-09T16:40:00Z"

BASE = "/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Manuscript/Review /"
SRC = BASE + "SP_TB_Supplementary_2026_09_09_v11_LPH.docx"
OUT = BASE + "SP_TB_Supplementary_2026_09_09_v12_LPH.docx"
TMP = "/private/tmp/scratch/-Users-jasonandrews-Library-CloudStorage-GoogleDrive-jasonandr-gmail-com-My-Drive/a1a6740e-2cf0-4f29-b6f8-fb5285e84435/scratchpad/ms/sup11x"

# (paragraph locator, old, new)
EDITS = [
    # Rate definitions: LTFU per-episode concentration, both rate bases, one implementation
    ("The main findings were consistent under crude and age-standardised rates",
     "for LTFU, they were 22% with age adjustment and 24% without "
     "(Gini coefficients 0·21 and 0·23, respectively)",
     "for LTFU, they were 24% with age adjustment and 25% without "
     "(Gini coefficients 0·23 and 0·25, respectively)"),

    # Figure S8 legend
    ("Supplementary figure S8",
     "it is the least concentrated (Gini 0·23)",
     "it is the least concentrated (Gini 0·25)"),

    # Methods: document how cross-fitting is applied to a proportion outcome
    ("Concentration was quantified using Lorenz curves and Gini coefficients",
     "We also estimated the share of events occurring among the 5%, 10%, 20%, and 40% "
     "of the adult population living in the highest-rate regions.",
     "For notifications and mortality, which are counts per population, the events "
     "themselves were split. For LTFU, which is a proportion of evaluated episodes, the "
     "evaluated episodes were split: regions were ranked by the LTFU proportion observed "
     "in one half and the share of LTFU events was measured in the other, in both cases "
     "accumulating regions to 20% of the adult population. We also estimated the share of "
     "events occurring among the 5%, 10%, 20%, and 40% of the adult population living in "
     "the highest-rate regions."),
]

# Table S4: LTFU column (last cell of each data row) 24 -> 25, 26 -> 27
TABLE_EDITS = [("All tiers", "24", "25"), ("Excluding postal-code", "26", "27")]

_id = [9700]
def nid():
    _id[0] += 1
    return str(_id[0])

def make_run(tmpl, text, deleted=False):
    r = etree.Element(W + "r")
    if tmpl is not None:
        rpr = tmpl.find(W + "rPr")
        if rpr is not None:
            r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, W + ("delText" if deleted else "t"))
    t.set(XML + "space", "preserve"); t.text = text
    return r

def wrap(tag, run):
    e = etree.Element(W + tag)
    e.set(W + "id", nid()); e.set(W + "author", AUTHOR); e.set(W + "date", DATE)
    e.append(run); return e

def apply_edit(p, old, new):
    for run in p.findall(W + "r"):
        t = run.find(W + "t")
        if t is None or not t.text or old not in t.text:
            continue
        full = t.text; i = full.index(old)
        before, after = full[:i], full[i + len(old):]
        parent = run.getparent(); pos = list(parent).index(run)
        nodes = []
        if before: nodes.append(make_run(run, before))
        nodes.append(wrap("del", make_run(run, old, deleted=True)))
        if new: nodes.append(wrap("ins", make_run(run, new)))
        if after: nodes.append(make_run(run, after))
        parent.remove(run)
        for k, n in enumerate(nodes): parent.insert(pos + k, n)
        return True
    return False

def ptext(el):
    return "".join(n.text or "" for n in el.iter(W + "t"))

def main():
    docxml = f"{TMP}/word/document.xml"
    tree = etree.parse(docxml)
    body = tree.getroot().find(W + "body")
    allp = list(body.iter(W + "p"))          # includes paragraphs inside table cells

    ok = fail = 0
    print("=== prose edits ===")
    for loc, old, new in EDITS:
        tgt = next((p for p in allp if loc in ptext(p) and old in ptext(p)), None)
        if tgt is None or not apply_edit(tgt, old, new):
            print(f"  FAIL {old[:60]!r}"); fail += 1
        else:
            print(f"  ok   {old[:56]!r}"); ok += 1

    print("=== table S4 LTFU column ===")
    for rowkey, old, new in TABLE_EDITS:
        row = next((tr for tr in body.iter(W + "tr") if rowkey in ptext(tr)), None)
        if row is None:
            print(f"  FAIL row {rowkey!r} not found"); fail += 1; continue
        cells = row.findall(W + "tc")
        last = cells[-1]
        cellp = last.find(W + "p")
        if ptext(last).strip() != old:
            print(f"  FAIL {rowkey!r} last cell is {ptext(last).strip()!r}, expected {old!r}")
            fail += 1; continue
        if apply_edit(cellp, old, new):
            print(f"  ok   {rowkey:24s} LTFU {old} -> {new}   (row: {ptext(row).strip()[:60]!r})")
            ok += 1
        else:
            print(f"  FAIL could not edit {rowkey!r}"); fail += 1

    print(f"\napplied {ok}, failed {fail}")
    if fail:
        sys.exit(1)
    tree.write(docxml, xml_declaration=True, encoding="UTF-8", standalone=True)

    zin = zipfile.ZipFile(SRC, "r"); zout = zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED)
    for item in zin.infolist():
        data = open(docxml, "rb").read() if item.filename == "word/document.xml" else zin.read(item.filename)
        zout.writestr(item, data)
    zout.close(); zin.close()
    print("wrote", OUT)

main()
