#!/usr/bin/env python3
"""Every /tmp file the 100-series READS must be either restored by 00_restore_tmp.py or
WRITTEN by another pipeline script.

Why: /tmp is cleared between sessions. On 2026-08-10, region_cases.csv — read by 11 scripts —
was missing from 00_restore's FILES list, so any session that restored and then ran a figure
script without first re-running 100_region_units.py crashed (or worse, read a stale file left
by an earlier same-day run). This check makes that class of gap impossible to reintroduce.

Exit 0 = closed. Exit 1 = some read /tmp file has no producer and is not restored.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

restore_src = (SCRIPTS / "00_restore_tmp.py").read_text()
m = re.search(r"FILES\s*=\s*\[(.*?)\]", restore_src, re.S)
restored = set(re.findall(r'"([^"]+)"', m.group(1))) if m else set()

TMP_RE = re.compile(r'/tmp/([A-Za-z0-9_.\-]+\.(?:csv|gpkg|json|parquet))')
WRITE_METHOD = re.compile(r'\.(to_csv|to_file|to_json|to_parquet)\s*\(')

# Scope: the MANUSCRIPT pipeline (00_restore + the 100-series). Exploratory scripts (< 100)
# may read ad-hoc /tmp extractions; only the pipeline is under a reproducibility contract.
PIPELINE = [SCRIPTS / "00_restore_tmp.py"] + sorted(SCRIPTS.glob("1[0-9][0-9]_*.py"))

# R companions (e.g. 121_ltfu_region_glmm.R) write /tmp files via write.csv — count those as produced
R_WRITES = set()
for rp in SCRIPTS.glob("1[0-9][0-9]_*.R"):
    for m in re.finditer(r'write\.csv\([^,]+,\s*"/tmp/([A-Za-z0-9_.\-]+)"', rp.read_text(errors="replace")):
        R_WRITES.add(m.group(1))

reads, writes = {}, set()
for p in PIPELINE:
    src = p.read_text(errors="replace")
    has_writer = bool(WRITE_METHOD.search(src))
    for line in src.splitlines():
        code = line.split("#")[0]
        for fname in TMP_RE.findall(code):
            esc = re.escape(fname)
            if re.search(r'(to_csv|to_file|to_json|to_parquet)\s*\(\s*f?["\']/tmp/' + esc, code) \
               or re.search(r'open\s*\(\s*f?["\']/tmp/' + esc + r'["\']\s*,\s*["\']w', code):
                writes.add(fname)
            elif has_writer and re.search(r'=\s*f?["\']/tmp/' + esc + r'["\']', code):
                # self-cache pattern (e.g. 117): path assigned to a variable, script builds the
                # file itself when it is absent and writes it via .to_file(var)
                writes.add(fname)
            else:
                reads.setdefault(fname, set()).add(p.name)

orphans = {f: sorted(rs) for f, rs in reads.items() if f not in restored and f not in writes and f not in R_WRITES}
if orphans:
    print("RESTORE CLOSURE FAILED — /tmp files read but neither restored nor produced by any script:")
    for f, rs in sorted(orphans.items()):
        print(f"  /tmp/{f}   read by: {', '.join(rs[:6])}{' ...' if len(rs) > 6 else ''}")
    print("\nFix: add the file to FILES in scripts/00_restore_tmp.py (and persist it to Data/analytic/),")
    print("or make the producing script write it.")
    sys.exit(1)

print(f"restore closure OK: {len(reads)} /tmp inputs, {len(restored)} restored, {len(writes)} produced in-pipeline")
sys.exit(0)
