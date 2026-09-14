#!/usr/bin/env python3
"""Privacy check for a code-only repo whose data is patient-level TB notifications.

FAIL (exit 1): any git-TRACKED file matches an individual-level artifact pattern. These hold
one row per person/episode (sinan_clean id, sector, outcomes) and must never enter git —
the rule PIPELINE.md states in prose, enforced here.

WARN (exit 0 with output): a tracked CSV under outputs/ contains case-count cells of 1-4.
Small-area counts below 5 are a disclosure risk; no such files are tracked in this repository.
"""
import csv, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDIVIDUAL = re.compile(r"(geocoded_cohort|cohort_.*cnefe|region_cases|sinan|LINKAGE|cohort_with_spatial)",
                        re.IGNORECASE)

tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()

DATA_EXT = (".csv", ".parquet", ".xlsx", ".xls", ".json", ".gpkg", ".dta", ".feather", ".pkl")
bad = [f for f in tracked
       if Path(f).suffix.lower() in DATA_EXT
       and INDIVIDUAL.search(Path(f).name)
       and not f.startswith("test/")]
if bad:
    print("PRIVACY FAILURE — individual-level artifact tracked in git:")
    for f in bad:
        print("  " + f)
    print("Remove from git (and from history if pushed) immediately. These files stay in Data/analytic/.")
    sys.exit(1)

warned = 0
for f in tracked:
    if not (f.startswith("outputs/") and f.endswith(".csv")):
        continue
    with open(ROOT / f, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        continue
    count_cols = [c for c in rows[0] if re.search(r"(caso|case|obito|death|n_pac)", c, re.I)
                  and not re.search(r"(pct|rate|taxa|cum|per)", c, re.I)]
    small = sum(1 for r in rows for c in count_cols
                if str(r[c]).isdigit() and 0 < int(r[c]) < 5)
    if small:
        print(f"WARN: {f}: {small} cells with case counts 1-4 in {count_cols} "
              f"(small-cell disclosure risk if ever published)")
        warned += 1

print(f"privacy OK: no individual-level files tracked ({len(tracked)} files); {warned} small-cell warning(s)")
sys.exit(0)
