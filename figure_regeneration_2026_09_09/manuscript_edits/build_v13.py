"""Build v13 from v12:
   - replace regenerated Figures 2, 3, 5 (crude rates; LTFU per evaluated episode; compact fig5b labels)
   - numeric corrections as tracked changes
   - Declaration of interests scaffold (resolves Jason's comment)
   - mark the two Codex figure comments resolved
"""
import copy, os, re, shutil, zipfile, sys
from lxml import etree
from PIL import Image

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
W15 = "{http://schemas.microsoft.com/office/word/2012/wordml}"
XML = "{http://www.w3.org/XML/1998/namespace}"
AUTHOR, DATE = "Editor", "2026-09-09T16:00:00Z"
MD = "·"     # middle dot decimal separator (Lancet style)
EN = "–"     # en dash

BASE = "/Users/jasonandrews/Library/CloudStorage/GoogleDrive-jasonandr@gmail.com/My Drive/SP-TB-spatial-analyses/Manuscript/Review /"
SRC = BASE + "SP_TB_Manuscript_2026_09_09_v12.docx"
OUT = BASE + "SP_TB_Manuscript_2026_09_09_v13.docx"
SCR = "/private/tmp/scratch/-Users-jasonandrews-Library-CloudStorage-GoogleDrive-jasonandr-gmail-com-My-Drive/a1a6740e-2cf0-4f29-b6f8-fb5285e84435/scratchpad/ms"
TMP = f"{SCR}/v12x"
NEWFIG = f"{SCR}/figs/out"

# media/imageN.png  ->  regenerated file  (figure 2, 3, 5)
IMG_MAP = {"image2.png": "Figure2_concentration.png",
           "image3.png": "Figure3_social_attributable.png",
           "image5.png": "Figure5_temporal_oos.png"}

# ---------------------------------------------------------------- text edits
EDITS = [
    # Summary / Findings
    ("Among 192", f"and 24% of LTFU events.", f"and 25% of LTFU events."),
    ("Among 192", "contained 42% of notifications in 2022", "contained 41% of notifications in 2022"),
    # Research in context / Added value
    ("We analysed 192", "contained 42% of notifications in 2022", "contained 41% of notifications in 2022"),
    # Results - concentration
    ("Hotspots defined separately for each outcome",
     f"and 24% of LTFU events (denoised Gini coefficients 0{MD}39, 0{MD}28, and 0{MD}23;",
     f"and 25% of LTFU events (denoised Gini coefficients 0{MD}39, 0{MD}28, and 0{MD}25;"),
    # Results - excess fraction CI (stable bootstrap, B=4000: 63.5-67.7)
    ("Notification and mortality hotspots overlapped substantially (Jaccard",
     f"An estimated 65% (95% CI 63{EN}67)", f"An estimated 65% (95% CI 64{EN}68)"),
    # Results - temporal stability, LTFU per evaluated episode
    ("Notification concentration remained stable",
     "declined markedly for LTFU (37% to 26%; figure 5a)",
     "declined markedly for LTFU (38% to 29%; figure 5a)"),
    # Results - out-of-sample
    ("Hotspots selected using 2013",
     "still identified 42% of notifications in 2022", "still identified 41% of notifications in 2022"),
    # Discussion - out-of-sample
    ("The persistence of notification hotspots",
     "still contained 42% of notifications in 2022", "still contained 41% of notifications in 2022"),
]

DOI_TEXT = (
    "ELL, NAM, and JRA report grant support from the World Health Organization for the "
    "submitted work. [PLACEHOLDER — each remaining author to confirm, for the previous "
    "36 months: grants or contracts, consulting fees, payment for lectures or expert "
    "testimony, patents, participation on advisory or data safety monitoring boards, "
    "leadership or fiduciary roles, stock or stock options, and any non-financial interests. "
    "Delete this bracket once all coauthors have returned ICMJE disclosure forms.] All other "
    "authors declare no competing interests."
)

_id = [9500]
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

def ptext(p):
    return "".join(n.text or "" for n in p.iter(W + "t"))

# ---------------------------------------------------------------- images
def stage_images():
    staged = {}
    os.makedirs(f"{SCR}/staged", exist_ok=True)
    for orig_name, new_name in IMG_MAP.items():
        o = Image.open(f"{TMP}/word/media/{orig_name}")
        n = Image.open(f"{NEWFIG}/{new_name}").convert("RGB")
        ow, oh = o.size
        target_ar = ow / oh
        nw, nh = n.size
        # pad (white, centred) so the new figure matches the original aspect exactly,
        # then resize to the original pixel dimensions -> zero layout change in Word
        if nw / nh > target_ar:
            H = int(round(nw / target_ar)); canvas = Image.new("RGB", (nw, H), "white")
            canvas.paste(n, (0, (H - nh) // 2))
        else:
            Wd = int(round(nh * target_ar)); canvas = Image.new("RGB", (Wd, nh), "white")
            canvas.paste(n, ((Wd - nw) // 2, 0))
        out = canvas.resize((ow, oh), Image.LANCZOS)
        path = f"{SCR}/staged/{orig_name}"
        out.save(path, "PNG", optimize=True)
        staged[f"word/media/{orig_name}"] = path
        print(f"  {orig_name}: orig {ow}x{oh} (ar {target_ar:.4f}) <- {new_name} {nw}x{nh} "
              f"(ar {nw/nh:.4f}) padded+resized")
    return staged

def main():
    print("=== staging regenerated figures ===")
    staged = stage_images()

    print("\n=== tracked text edits ===")
    docxml = f"{TMP}/word/document.xml"
    tree = etree.parse(docxml)
    body = tree.getroot().find(W + "body")
    paras = body.findall(W + "p")
    ok = fail = 0
    for prefix, old, new in EDITS:
        tgt = next((p for p in paras if prefix in ptext(p)[:220] and old in ptext(p)), None)
        if tgt is None or not apply_edit(tgt, old, new):
            print(f"  FAIL {old[:60]!r}"); fail += 1
        else:
            print(f"  ok   {old[:52]!r} -> {new[:52]!r}"); ok += 1

    # ---- Declaration of interests: insert a new tracked paragraph after the heading ----
    di = next((i for i, p in enumerate(paras) if ptext(p).strip() == "Declaration of interests"), None)
    if di is None:
        print("  FAIL could not find 'Declaration of interests' heading"); fail += 1
    else:
        body_tmpl = paras[di + 2] if len(paras) > di + 2 else paras[di - 1]  # a body-text paragraph
        newp = copy.deepcopy(body_tmpl)
        for ch in list(newp):
            if etree.QName(ch).localname != "pPr":
                newp.remove(ch)
        ppr = newp.find(W + "pPr")
        if ppr is None:
            ppr = etree.SubElement(newp, W + "pPr"); newp.insert(0, ppr)
        rpr = ppr.find(W + "rPr")
        if rpr is None:
            rpr = etree.SubElement(ppr, W + "rPr")
        insmark = etree.Element(W + "ins")
        insmark.set(W + "id", nid()); insmark.set(W + "author", AUTHOR); insmark.set(W + "date", DATE)
        rpr.insert(0, insmark)
        tmpl_run = next((r for r in body_tmpl.findall(W + "r")), None)
        newp.append(wrap("ins", make_run(tmpl_run, DOI_TEXT)))
        paras[di].addnext(newp)
        print(f"  ok   Declaration of interests text inserted after paragraph {di}")
        ok += 1

    print(f"\napplied {ok}, failed {fail}")
    if fail:
        sys.exit(1)
    tree.write(docxml, xml_declaration=True, encoding="UTF-8", standalone=True)

    # ---- mark the two Codex figure comments resolved ----
    cpath = f"{TMP}/word/comments.xml"
    cx = open(cpath, encoding="utf-8").read()
    codex_paraids = []
    for m in re.finditer(r'<w:comment\b[^>]*w:author="([^"]*)"[^>]*>(.*?)</w:comment>', cx, re.S):
        if m.group(1) == "Codex":
            codex_paraids += re.findall(r'w14:paraId="([0-9A-F]+)"', m.group(2))
    epath = f"{TMP}/word/commentsExtended.xml"
    ex = open(epath, encoding="utf-8").read()
    done = 0
    for pid in codex_paraids:
        new_ex = re.sub(rf'(<w15:commentEx w15:paraId="{pid}" w15:done=")0(")', r'\g<1>1\g<2>', ex)
        if new_ex != ex:
            ex = new_ex; done += 1
    open(epath, "w", encoding="utf-8").write(ex)
    print(f"marked {done} Codex comment(s) resolved (of {len(codex_paraids)} found)")

    # ---- rezip ----
    zin = zipfile.ZipFile(SRC, "r"); zout = zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED)
    for item in zin.infolist():
        name = item.filename
        if name == "word/document.xml":
            data = open(docxml, "rb").read()
        elif name == "word/commentsExtended.xml":
            data = open(epath, "rb").read()
        elif name in staged:
            data = open(staged[name], "rb").read()
        else:
            data = zin.read(name)
        zout.writestr(item, data)
    zout.close(); zin.close()
    print("wrote", OUT)

main()
