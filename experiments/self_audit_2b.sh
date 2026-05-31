#!/usr/bin/env bash
# STEP 5 — Phase 2B self-audit. Prints evidence (not assertions) for each integrity claim.
# Run from anywhere; resolves the repo root (nous/) from its own location.
set -u
cd "$(dirname "$0")/.."   # -> repo root (nous/)

echo "=================================================================="
echo "PHASE 2B SELF-AUDIT  (evidence, not assertion)"
echo "=================================================================="
fail=0

echo
echo "[1] No file under src/ or tests/ was modified (git porcelain, path-scoped):"
changed=$(git status --porcelain src tests)
if [ -z "$changed" ]; then echo "    PASS — src/ and tests/ are clean."
else echo "    FAIL — modifications detected:"; echo "$changed"; fail=1; fi

echo
echo "[2] The engine src/nous_activation.py and src/nous_store.py were NOT altered:"
eng=$(git status --porcelain src/nous_activation.py src/nous_store.py)
if [ -z "$eng" ]; then echo "    PASS — engine + store unchanged in git."
else echo "    FAIL — engine/store shows modified."; echo "$eng"; fail=1; fi

echo
echo "[3] 2A harness functions UNCHANGED; only ADDITIVE additions (read_targets):"
# the three 2A functions must still be present and the file must still pass 2A tests
if grep -q "def build_graph_from_spec" experiments/harness.py \
   && grep -q "def retrieval_strength" experiments/harness.py \
   && grep -q "def run_trials" experiments/harness.py \
   && grep -q "def read_targets" experiments/harness.py; then
  echo "    PASS — 2A fns present; read_targets added (run test_harness.py separately to confirm 2A still green)."
else echo "    FAIL — a harness function is missing."; fail=1; fi

echo
echo "[4] The PREDICTION banner is printed BEFORE any result is computed (priming.py main):"
pred=$(grep -n "print_preregistration()" experiments/priming.py | tail -1 | cut -d: -f1)
load=$(grep -n "swow.load_edges()" experiments/priming.py | tail -1 | cut -d: -f1)
echo "    print_preregistration() at line $pred ; first data load at line $load"
if [ -n "$pred" ] && [ -n "$load" ] && [ "$pred" -lt "$load" ]; then
  echo "    PASS — prediction emitted before data is even loaded."
else echo "    FAIL — ordering wrong."; fail=1; fi

echo
echo "[5] Conditions selected BLIND (swow.py never IMPORTS or CALLS the engine):"
# Check actual import statements and call sites, NOT prose mentions in the docstring
# (the docstring explains that selection does not call spread_activation; that word is
# expected to appear in comments). We grep for import lines and bare-call syntax.
if grep -E "^\s*(import|from)\s+(nous_store|nous_activation|harness)" experiments/swow.py \
   || grep -E "(spread_activation|retrieval_strength|read_targets)\s*\(" experiments/swow.py; then
  echo "    FAIL — swow.py imports or calls an engine/readout function (selection not blind)."; fail=1
else echo "    PASS — swow.py has no engine import and no activation call; selection is topology-only."; fi

echo
echo "[6] Raw SWOW data is NOT committed (size + license):"
if git ls-files --error-unmatch experiments/data/strength.SWOW-EN.R123.20180827.csv >/dev/null 2>&1; then
  echo "    FAIL — the raw csv is tracked by git."; fail=1
else echo "    PASS — raw csv is not tracked (gitignored)."; fi

echo
echo "[7] Numbers in PRIMING.md match results/priming_output.txt (spot-check key values):"
ok7=1
for v in "0.750332" "0.136601" "0.027447" "0.2894" "185/300"; do
  if grep -q "$v" experiments/results/priming_output.txt && grep -q "$v" experiments/PRIMING.md; then :;
  else echo "    MISMATCH for value: $v"; ok7=0; fi
done
if [ "$ok7" -eq 1 ]; then echo "    PASS — key DIRECT/MEDIATED/median/rho/sign values match the capture."
else echo "    FAIL — a PRIMING.md value is not in the captured output."; fail=1; fi

echo
echo "=================================================================="
if [ "$fail" -eq 0 ]; then echo "SELF-AUDIT: ALL CHECKS PASS"; else echo "SELF-AUDIT: FAILURES PRESENT (see above)"; fi
echo "=================================================================="
exit $fail
