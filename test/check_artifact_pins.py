#!/usr/bin/env python3
"""Golden check: the persisted analytic artifacts must match test/artifact_pins.json exactly,
and the STROBE figure's hardcoded analytic n must match region_cases.csv.

Numbers live in THREE places that have already drifted apart once (manuscript/PIPELINE.md
carried the pre-episode-rebuild flow for five weeks): the artifact, the STROBE figure literals
in scripts/114_figS_strobe.py, and the docs. This check ties them together.

Exit 0 = all pinned values match. Exit 1 = drift. Exit 3 = analytic store not reachable (SKIP).
"""
import csv, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AN = Path("/DATA_ROOT/WHO modelling Project/SP-TB-spatial-analyses/Data/analytic")

pins = json.loads((ROOT / "test" / "artifact_pins.json").read_text())
if not AN.is_dir():
    print(f"SKIP: analytic store not mounted at {AN}")
    sys.exit(3)

fails = []

def nrows(path):
    with open(path, newline="") as fh:
        return sum(1 for _ in fh) - 1

for fname, expected in pins["rows"].items():
    p = AN / fname
    if not p.exists():
        fails.append(f"{fname}: MISSING from analytic store")
        continue
    got = nrows(p)
    if got != expected:
        fails.append(f"{fname}: {got} rows, pinned {expected}")

rc = AN / "region_cases.csv"
if rc.exists():
    t = pins["region_cases_tallies"]
    death = aband = 0
    ymin, ymax = 9999, 0
    with open(rc, newline="") as fh:
        for row in csv.DictReader(fh):
            death += int(row["death"]); aband += int(row["aband"])
            y = int(row["year"]); ymin = min(ymin, y); ymax = max(ymax, y)
    for name, got, exp in [("death_sum", death, t["death_sum"]), ("aband_sum", aband, t["aband_sum"]),
                           ("year_min", ymin, t["year_min"]), ("year_max", ymax, t["year_max"])]:
        if got != exp:
            fails.append(f"region_cases.{name}: {got}, pinned {exp}")

# structural invariant (ADR-0003): NaN in adjusted rates is EXACTLY the small-count
# suppression rule — inc_adj NaN <=> n < 10, ltfu_adj/cfr NaN <=> ne < 10. If this breaks,
# someone changed the suppression logic in scripts/100_region_units.py without meaning to.
ru_path = AN / "region_units.csv"
if ru_path.exists():
    with open(ru_path, newline="") as fh:
        for row in csv.DictReader(fh):
            n, ne = float(row["n"]), float(row["ne"])
            for col, thresh in [("inc_adj", n), ("drate_adj", n), ("ltfu_adj", ne), ("cfr", ne)]:
                if (row[col] == "") != (thresh < 10):
                    fails.append(f"region_units {row['region_id']}: {col} NaN-vs-threshold mismatch "
                                 f"(n={n:.0f}, ne={ne:.0f}, {col}={row[col] or 'NaN'})")
                    break
            else:
                continue
            break  # one example is enough to fail loudly

# GLMM place-effect pins (ADR-0005 companion; script 121). SKIP silently if never run.
glmm_path = AN / "ltfu_glmm_summary.json"
if glmm_path.exists() and "ltfu_glmm" in pins:
    g = json.loads(glmm_path.read_text()); p = pins["ltfu_glmm"]
    for name, got, exp in [("m1_MOR", round(g["m1"]["MOR"], 2), p["m1_MOR_2dp"]),
                           ("m2_MOR", round(g["m2"]["MOR"], 2), p["m2_MOR_2dp"]),
                           ("n_episodes", g["n_episodes"], p["n_episodes"])]:
        if got != exp:
            fails.append(f"ltfu_glmm.{name}: {got}, pinned {exp}")

# the STROBE figure's final box must state the same n as the artifact pin
strobe_src = (ROOT / "scripts" / "114_figS_strobe.py").read_text()
ns = [int(m.replace(",", "")) for m in re.findall(r"n = ([\d,]+)", strobe_src)]
if pins["strobe_analytic_n"] not in ns:
    fails.append(f"scripts/114_figS_strobe.py: no box states n = {pins['strobe_analytic_n']:,} "
                 f"(found {[f'{n:,}' for n in ns]})")

if fails:
    print("ARTIFACT PIN FAILURES — the cohort changed, or a number drifted:")
    for f in fails:
        print("  " + f)
    print("\nIf the change is INTENDED: update test/artifact_pins.json, scripts/114_figS_strobe.py")
    print("and manuscript/PIPELINE.md in the same commit, saying what changed and why.")
    sys.exit(1)

print(f"artifact pins OK: {len(pins['rows'])} row counts, region_cases tallies, STROBE n = {pins['strobe_analytic_n']:,}")
sys.exit(0)
