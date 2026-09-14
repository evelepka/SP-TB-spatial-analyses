"""Appendix v13 -> v14: remove three non-essential items and renumber.

Removed: figure S6 (duplicates main figure 3 for income; composite result kept as prose),
         table S3 (converted to prose in the vulnerability methods),
         table S7 (message retained in figure S3's legend).

Renumbering: figures S7->S6, S8->S7, S9->S8 ; tables S4->S3, S5->S4, S6->S5.
Applied cleanly (not as tracked changes) because a renumbering pass in tracked form is
unreadable; v13 is retained for diffing.
"""
import re, zipfile, sys
from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
BASE = "/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Manuscript/Review /"
SRC = BASE + "SP_TB_Supplementary_2026_09_09_v13_LPH.docx"
OUT = BASE + "SP_TB_Supplementary_2026_09_09_v14_LPH.docx"
TMP = "/private/tmp/scratch/-Users-jasonandrews-Library-CloudStorage-GoogleDrive-jasonandr-gmail-com-My-Drive/a1a6740e-2cf0-4f29-b6f8-fb5285e84435/scratchpad/ms/sup13x"

# ---- prose edits applied BEFORE renumbering (they remove refs to deleted items) ----
PRE = [
    # vulnerability methods: fold table S3's content into prose; retarget the IBP reference
    ("The four-domain vulnerability index",
     "Other candidate domains were tested but excluded (appendix table S3).",
     "Four further domains were tested and excluded: sanitation, because approximately 87% of "
     "the adult population lived in sectors with no more than 5% inadequate sanitation and its "
     "inclusion lowered agreement with the IPVS; precarious housing (cortiço), recorded in only "
     "0·3% of census sectors; race (Black and mixed-race), which was strongly correlated with "
     "the income-based composite (Spearman ρ ≈ 0·98); and population density, which was "
     "negatively correlated with the composite (ρ ≈ −0·20), the densest sectors being "
     "predominantly high-income vertical housing."),
    ("The four-domain vulnerability index",
     "is reported in appendix table S7.",
     "is also reported there."),

    # sensitivity list: drop the deprivation-index item (table S7 removed)
    ("Sensitivity analyses assessed geocoding precision",
     "regionalisation criteria (appendix table S5), deprivation-index choice "
     "(appendix table S7), and age adjustment",
     "regionalisation criteria (appendix table S5), and age adjustment"),

    # additional results: composite-index numbers stay, pointer to deleted figure S6 goes
    ("Excess fractions based on the composite vulnerability index",
     "(33% for notifications and 25% for mortality; appendix figure S6)",
     "(33% for notifications and 25% for mortality)"),

    # figure S3 legend: table S7 removed
    ("Supplementary figure S3. External validation",
     " (see appendix table S7)", ""),

    # metropolitan figure legend: was defined by reference to the deleted figure S6.
    # Only this trailing run needs rewriting; the caption number is handled by RENUM.
    ("Supplementary figure S7. Excess burden",
     " Layout as in appendix figure S6, restricted to metropolitan regions.",
     " Tuberculosis notification rate (a, b) and mortality (c, d) by quintile of "
     "household-income deprivation (a, c) and of the composite vulnerability index (b, d), "
     "from 1 (least) to 5 (most deprived). The dashed line marks the least-deprived "
     "(reference) quintile; numbers above bars are excess cases or deaths relative to that "
     "quintile, and insets report the excess fraction (region-cluster bootstrap 95% CI)."),
]

# ---- two-phase renumbering (tokens prevent cascade collisions) ----
RENUM = [("figure S7", "figure S6"), ("figure S8", "figure S7"), ("figure S9", "figure S8"),
         ("table S4", "table S3"), ("table S5", "table S4"), ("table S6", "table S5")]

DELETED_BOOKMARKS = {"LPHV11Appendix9", "LPHV11Appendix15", "LPHV11Appendix19"}


def ptx(el):
    return "".join(n.text or "" for n in el.iter(W + "t"))


def replace_in(el, old, new):
    """Plain text replacement inside a single w:t of this element."""
    for tn in el.iter(W + "t"):
        if tn.text and old in tn.text:
            tn.text = tn.text.replace(old, new)
            return True
    return False


def main():
    docxml = f"{TMP}/word/document.xml"
    tree = etree.parse(docxml)
    body = tree.getroot().find(W + "body")
    kids = list(body)

    # ---------- 1. prose edits ----------
    print("=== prose edits (before renumbering) ===")
    ok = fail = 0
    for loc, old, new in PRE:
        tgt = next((p for p in body.iter(W + "p") if loc in ptx(p) and old in ptx(p)), None)
        if tgt is None or not replace_in(tgt, old, new):
            print(f"  FAIL {old[:58]!r}"); fail += 1
        else:
            print(f"  ok   {old[:58]!r}"); ok += 1

    # ---------- 2. collect elements to delete ----------
    to_del = []
    # contents entries whose PAGEREF targets a deleted bookmark
    for ch in kids:
        if etree.QName(ch).localname != "p":
            continue
        instr = "".join(n.text or "" for n in ch.iter(W + "instrText"))
        m = re.search(r"PAGEREF (\S+)", instr)
        if m and m.group(1) in DELETED_BOOKMARKS:
            to_del.append((ch, f"contents entry -> {m.group(1)}  {ptx(ch)[:34]!r}"))

    # captions carrying the deleted bookmarks, plus their image / table / footnote
    for i, ch in enumerate(kids):
        if etree.QName(ch).localname != "p":
            continue
        names = {b.get(W + "name") for b in ch.findall(W + "bookmarkStart")}
        hit = names & DELETED_BOOKMARKS
        if not hit:
            continue
        label = ptx(ch)[:52]
        to_del.append((ch, f"caption {label!r}"))
        prev, nxt = kids[i - 1], kids[i + 1] if i + 1 < len(kids) else None
        # figure: image paragraph immediately precedes the caption
        if len(prev.findall(f".//{W}drawing")) > 0:
            to_del.append((prev, "  its figure image"))
        # table: table follows the caption, optionally then a footnote paragraph
        if nxt is not None and etree.QName(nxt).localname == "tbl":
            to_del.append((nxt, "  its table"))
            after = kids[i + 2] if i + 2 < len(kids) else None
            if (after is not None and etree.QName(after).localname == "p"
                    and not after.findall(W + "bookmarkStart") and ptx(after).strip()
                    and not ptx(after).startswith("Supplementary")):
                to_del.append((after, f"  its footnote {ptx(after)[:40]!r}"))

    print("\n=== removing ===")
    seen = set()
    for el, desc in to_del:
        if id(el) in seen:
            continue
        seen.add(id(el))
        print(f"  - {desc}")
        el.getparent().remove(el)

    # ---------- 3. renumber ----------
    print("\n=== renumbering ===")
    counts = {}
    for phase, pairs in enumerate([[(o, f"@@{k}@@") for k, (o, _) in enumerate(RENUM)],
                                   [(f"@@{k}@@", n) for k, (_, n) in enumerate(RENUM)]]):
        for old, new in pairs:
            for tn in body.iter(W + "t"):
                if tn.text and old in tn.text:
                    if phase == 0:
                        counts[old] = counts.get(old, 0) + tn.text.count(old)
                    tn.text = tn.text.replace(old, new)
    for (o, n) in RENUM:
        print(f"  {o} -> {n}   ({counts.get(o, 0)} occurrence(s))")

    leftover = [t.text for t in body.iter(W + "t") if t.text and "@@" in t.text]
    if leftover:
        print("  FAIL leftover tokens:", leftover); fail += 1

    print(f"\nprose edits: applied {ok}, failed {fail}")
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
