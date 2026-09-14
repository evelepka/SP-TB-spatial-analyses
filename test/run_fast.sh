#!/bin/bash
# run_fast.sh — the FAST tier: one entry point, seconds. Plumbing, not science.
#
# One command that checks the pipeline plumbing, the pinned cohort numbers and the privacy rule.
#
#   bash test/run_fast.sh            # all
#   bash test/run_fast.sh --list     # names only
#
# The artifact-pin check needs the Google Drive analytic store mounted; it SKIPs cleanly
# when it is not (exit 3 from the checker).
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

PASS=0; FAIL=0; SKIP=0; XFAIL=0; FAILED_NAMES=()
START=$(date +%s)

# KNOWN FAILURES — real debt, deliberately not hidden. A known failure does not fail the run
# but is printed every time; a NEW failure fails the run; a known failure that starts PASSING
# also fails the run, so this list cannot rot. Each entry says what fixing it requires.
KNOWN_FAIL=()

# NOTE: macOS ships bash 3.2, where "${arr[@]}" on an EMPTY array trips `set -u`.
# The ${arr[@]+...} form expands to nothing when the array is empty.
is_known() { local n="$1"; for k in ${KNOWN_FAIL[@]+"${KNOWN_FAIL[@]}"}; do [ "$k" = "$n" ] && return 0; done; return 1; }

run() {                     # run <name> <command...>
  local name="$1"; shift
  local t0 out rc
  t0=$(date +%s)
  out=$("$@" 2>&1); rc=$?
  local dt=$(( $(date +%s) - t0 ))
  if [ $rc -eq 3 ]; then
    printf "  %-34s SKIP  %3ds  (prerequisite absent)\n" "$name" "$dt"; SKIP=$((SKIP+1)); return
  fi
  if [ $rc -eq 0 ]; then
    if is_known "$name"; then
      printf "  %-34s PASS  %3ds  <== was a KNOWN FAILURE; remove it from KNOWN_FAIL\n" "$name" "$dt"
      FAIL=$((FAIL+1)); FAILED_NAMES+=("$name (now passes — prune KNOWN_FAIL)")
    else
      printf "  %-34s PASS  %3ds\n" "$name" "$dt"; PASS=$((PASS+1))
    fi
  elif is_known "$name"; then
    printf "  %-34s XFAIL %3ds  (known debt)\n" "$name" "$dt"; XFAIL=$((XFAIL+1))
  else
    printf "  %-34s FAIL  %3ds\n" "$name" "$dt"; FAIL=$((FAIL+1)); FAILED_NAMES+=("$name")
    echo "$out" | tail -12 | sed 's/^/        | /'
  fi
}

compile_all() { python3 -m py_compile scripts/*.py; }

if [ "${1:-}" = "--list" ]; then
  grep -oE '^  run "[^"]+"' "$0" | sed 's/  run "/  /; s/"$//'; exit 0
fi

echo "FAST TIER"
echo

echo "pipeline plumbing"
  run "all scripts compile"          compile_all
  run "restore closure (/tmp deps)"  python3 test/check_restore_closure.py

echo
echo "numbers cannot drift silently"
  run "artifact pins + STROBE n"     python3 test/check_artifact_pins.py

echo
echo "privacy"
  run "no individual data in git"    python3 test/check_privacy.py

echo
DT=$(( $(date +%s) - START ))
echo "──────────────────────────────────────────────────────────────"
printf "PASS %d   FAIL %d   XFAIL %d   SKIP %d   in %ds\n" "$PASS" "$FAIL" "$XFAIL" "$SKIP" "$DT"
[ "$XFAIL" -gt 0 ] && echo "known debt (see KNOWN_FAIL in this script): ${KNOWN_FAIL[*]:-}"
[ "$DT" -gt 60 ] && echo "WARNING: over the 60s budget — gate something slow behind a --full flag."
if [ "$FAIL" -gt 0 ]; then
  echo "failed: ${FAILED_NAMES[*]:-}"
  exit 1
fi
exit 0
