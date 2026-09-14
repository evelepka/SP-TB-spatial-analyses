"""Main manuscript v13 -> v14 as tracked changes: update appendix cross-references after
the appendix restructuring (figures S7->S6, S8->S7, S9->S8; tables S4->S3, S5->S4, S6->S5;
figure S6, table S3 and table S7 removed), and restore specific appendix pointers so that
every remaining appendix item is cited from the main text."""
import copy, zipfile, sys
from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML = "{http://www.w3.org/XML/1998/namespace}"
AUTHOR, DATE = "Editor", "2026-09-09T18:10:00Z"

BASE = "/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Manuscript/Review /"
SRC = BASE + "SP_TB_Manuscript_2026_09_09_v13.docx"
OUT = BASE + "SP_TB_Manuscript_2026_09_09_v14.docx"
TMP = "/private/tmp/scratch/-Users-jasonandrews-Library-CloudStorage-GoogleDrive-jasonandr-gmail-com-May-Drive"
TMP = "/private/tmp/scratch/-Users-jasonandrews-Library-CloudStorage-GoogleDrive-jasonandr-gmail-com-My-Drive/a1a6740e-2cf0-4f29-b6f8-fb5285e84435/scratchpad/ms/v13x"

EDITS = [
    # ---- renumbered cross-references ----
    # metropolitan excess burden: figure S7 -> S6
    ("Tuberculosis notification rates increased across household-income deprivation",
     "appendix figure S7", "appendix figure S6"),
    # LTFU per capita: figure S8 -> S7 (Results, and again in the figure 2 legend)
    ("Hotspots defined separately for each outcome",
     "appendix figure S8", "appendix figure S7"),
    ("Figure 2. Geographic concentration of tuberculosis",
     "appendix figure S8", "appendix figure S7"),
    # GLMM predictors: table S6 -> S5
    ("In logistic mixed models of 171",
     "appendix table S6", "appendix table S5"),

    # ---- restore specific pointers (previously a bare "(appendix)") ----
    # the paragraph splits at "(appendix)", so this needs two targeted edits
    ("Sensitivity analyses varied geocoding precision",
     "Sensitivity analyses varied geocoding precision, region size, regionalisation "
     "criteria, and age adjustment (",
     "Sensitivity analyses varied geocoding precision (appendix table S3), region size "
     "(appendix table S2), regionalisation criteria (appendix table S4), and age adjustment ("),
    ("Sensitivity analyses varied geocoding precision", "appendix", "appendix figure S8"),

    # vulnerability validation now lives entirely in appendix figure S3 (table S7 removed)
    ("A place-based social vulnerability index was constructed",
     "comparison with an index based on the Brazilian Deprivation Index are reported in the "
     "appendix.",
     "comparison with an index based on the Brazilian Deprivation Index are reported in "
     "appendix figure S3."),
]

_id = [10100]
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

def ptx(el):
    return "".join(n.text or "" for n in el.iter(W + "t"))

def main():
    docxml = f"{TMP}/word/document.xml"
    tree = etree.parse(docxml)
    body = tree.getroot().find(W + "body")
    allp = list(body.iter(W + "p"))
    ok = fail = 0
    for loc, old, new in EDITS:
        tgt = next((p for p in allp if loc in ptx(p) and old in ptx(p)), None)
        if tgt is None or not apply_edit(tgt, old, new):
            print(f"  FAIL {loc[:38]!r} / {old[:44]!r}"); fail += 1
        else:
            print(f"  ok   {old[:46]!r} -> {new[:46]!r}"); ok += 1
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
