#!/usr/bin/env bash
# STEP 5 — Phase 2A self-audit. Prints evidence for each integrity claim.
# Run from anywhere; it resolves the repo root (psyche/) from its own location.
set -u
cd "$(dirname "$0")/.."   # -> repo root (psyche/)

echo "=================================================================="
echo "PHASE 2A SELF-AUDIT  (evidence, not assertion)"
echo "=================================================================="

fail=0

echo
echo "[1] No file under src/ or tests/ was modified (git porcelain, path-scoped):"
changed=$(git status --porcelain src tests)
if [ -z "$changed" ]; then
  echo "    PASS — src/ and tests/ are clean."
else
  echo "    FAIL — modifications detected:"; echo "$changed"; fail=1
fi

echo
echo "[2] The engine src/psyche_activation.py was NOT altered to force an effect:"
if [ -n "$(git status --porcelain src/psyche_activation.py)" ]; then
  echo "    FAIL — psyche_activation.py shows as modified."; fail=1
else
  echo "    PASS — psyche_activation.py unchanged in git."
fi

echo
echo "[3] The PREDICTION is printed BEFORE any result is computed (fan_effect.py main):"
pred=$(grep -n "print_preregistration()" experiments/fan_effect.py | tail -1 | cut -d: -f1)
comp=$(grep -n "compute_fan_table()" experiments/fan_effect.py | tail -1 | cut -d: -f1)
echo "    print_preregistration() call at line $pred ; compute_fan_table() call at line $comp"
if [ "$pred" -lt "$comp" ]; then
  echo "    PASS — prediction is emitted before the result is computed."
else
  echo "    FAIL — ordering is wrong."; fail=1
fi

echo
echo "[4] All reported numbers match results/fan_effect_output.txt (captured literally):"
val=$(awk '/^[[:space:]]+[0-9]+[[:space:]]+0\./{print $2; exit}' experiments/results/fan_effect_output.txt)
echo "    activation value in captured output: ${val:-<none found>}"
if [ -n "${val:-}" ] && grep -q "$val" experiments/FAN_EFFECT.md; then
  echo "    PASS — FAN_EFFECT.md cites the captured value $val."
else
  echo "    FAIL — FAN_EFFECT.md does not cite the captured value."; fail=1
fi
if grep -q "0.24337376814062497" experiments/FAN_EFFECT.md experiments/EXPERIMENT_NOTES.md; then
  echo "    FAIL — a non-captured (earlier hand-written) value is still present in the write-ups."; fail=1
else
  echo "    PASS — no non-captured value in the write-ups (FAN_EFFECT.md, EXPERIMENT_NOTES.md)."
fi

echo
echo "=================================================================="
if [ "$fail" -eq 0 ]; then
  echo "SELF-AUDIT: ALL CHECKS PASS"
else
  echo "SELF-AUDIT: FAILURES PRESENT (see above)"
fi
echo "=================================================================="
exit $fail
