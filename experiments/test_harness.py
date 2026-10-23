"""
Tests for the Phase 2 measurement harness (experiments/harness.py) and the fan-effect
experiment's reproducibility.

These tests guard the properties the experiments DEPEND ON:
  - DETERMINISM of construction: building the same spec twice yields identical readouts
    (the internal uuid4 IDs differ, but the measured activations do not).
  - PURITY of the readout: `retrieval_strength` is a pure read — the store is byte-for-byte
    unchanged afterwards (no persisted decay, no reopened closure, no strength drift).
  - ADVERSARIAL cross-process determinism: the FULL fan_effect result is byte-identical
    across PYTHONHASHSEED in fresh subprocesses. This reuses the pattern from
    tests/test_psyche_field.py — the natural implementations leak set-iteration order over
    uuid4 keys into results, so this is the test that would catch it.

Uses the project's tiny built-in harness (print + count, exit nonzero), NOT pytest — same
convention as the rest of the suite. Run as a script:
    python3 experiments/test_harness.py
"""

from __future__ import annotations

import os
import sys
import subprocess

from harness import (
    build_graph_from_spec,
    retrieval_strength,
    run_trials,
    star_spec,
    SRC_DIR,
)

_HERE = os.path.dirname(os.path.abspath(__file__))


# ─────────────────────────────────────────────────────────────────────────────
# Tiny test harness (matches the rest of the suite)
# ─────────────────────────────────────────────────────────────────────────────

_passed = 0
_failed = 0


def check(cond: bool, msg: str) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {msg}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: canonical, ID-independent views
# ─────────────────────────────────────────────────────────────────────────────

def _canonical_readout(inst, fan: int):
    """Content-keyed (not ID-keyed) readout from S to every target, so two builds with
    different uuid4 IDs can be compared for equality of MEANING."""
    rows = []
    for i in range(1, fan + 1):
        name = f"T{i}"
        v = retrieval_strength(inst.store, inst.ids["S"], inst.ids[name])
        rows.append((name, repr(v)))
    rows.sort()
    return tuple(rows)


def _store_snapshot(store):
    """A canonical, order-independent snapshot of everything a read could illegitimately
    mutate: counts plus each road's RAW (un-decayed) stored strength / traversal / closure
    and endpoints. Reading with apply_decay=False returns the canonical stored values."""
    rows = []
    for rid in store.all_road_ids():
        r = store.get_road(rid, apply_decay=False)
        rows.append((r.source_id, r.target_id, repr(r.strength), r.traversal_count, r.closed))
    rows.sort()
    return (store.node_count(), store.road_count(), tuple(rows))


# ─────────────────────────────────────────────────────────────────────────────
# 1) build_graph_from_spec is deterministic (same readout across rebuilds)
# ─────────────────────────────────────────────────────────────────────────────

def test_build_is_deterministic():
    section("build_graph_from_spec determinism (rebuild → identical readout)")
    fan = 8
    a = _canonical_readout(build_graph_from_spec(star_spec(fan)), fan)
    b = _canonical_readout(build_graph_from_spec(star_spec(fan)), fan)
    check(a == b, "two builds of the same spec give identical content-keyed readouts")
    check(len(a) == fan, "readout covers all targets")
    # and the values are all equal to each other (equal-strength edges, symmetric star)
    distinct = {v for _, v in a}
    check(len(distinct) == 1, f"all targets equal (equal-strength star); got {distinct!r}")


def test_run_trials_zero_spread():
    section("run_trials reports zero spread (determinism by construction)")
    agg = run_trials(lambda: build_graph_from_spec(star_spec(4)),
                     5, cue_name="S", target_name="T1")
    check(agg["n"] == 5, "n trials recorded")
    check(agg["spread"] == 0.0, f"spread is exactly 0.0; got {agg['spread']!r}")
    check(agg["mean"] == agg["min"] == agg["max"], "mean == min == max (all trials equal)")


# ─────────────────────────────────────────────────────────────────────────────
# 2) retrieval_strength is a PURE READ (store unchanged afterwards)
# ─────────────────────────────────────────────────────────────────────────────

def test_retrieval_strength_is_pure_read():
    section("retrieval_strength purity (store byte-unchanged after a read)")
    inst = build_graph_from_spec(star_spec(8))
    before = _store_snapshot(inst.store)
    # read it several times; a pure read must not accumulate any change
    for _ in range(3):
        retrieval_strength(inst.store, inst.ids["S"], inst.ids["T1"])
    after = _store_snapshot(inst.store)
    check(before == after, "store snapshot identical before and after repeated reads")


# ─────────────────────────────────────────────────────────────────────────────
# 3) ADVERSARIAL: full fan_effect result byte-identical across PYTHONHASHSEED
# ─────────────────────────────────────────────────────────────────────────────

def _hash_seed_probe(seed: str) -> str:
    """Run a fresh interpreter under a fixed PYTHONHASHSEED that runs the WHOLE fan_effect
    experiment and returns its stdout. Determinism means: identical bytes across seeds.
    Mirrors tests/test_psyche_field.py's adversarial probe."""
    code = r'''
import os, sys
sys.path.insert(0, os.environ["PSYCHE_SRC"])   # frozen library (bare-name imports)
sys.path.insert(0, os.environ["PSYCHE_EXP"])   # experiments package (harness, fan_effect)
import fan_effect
raise SystemExit(fan_effect.main())
'''
    env = dict(os.environ)
    env["PSYCHE_SRC"] = SRC_DIR
    env["PSYCHE_EXP"] = _HERE
    env["PYTHONHASHSEED"] = seed
    out = subprocess.run([sys.executable, "-c", code], env=env,
                         capture_output=True, text=True)
    if out.returncode != 0:
        # surface the failure as empty output so the check fails loudly with stderr shown
        print("  (subprocess stderr)\n" + out.stderr)
        return ""
    return out.stdout


def test_fan_effect_deterministic_across_hash_seeds():
    section("ADVERSARIAL determinism: fan_effect byte-identical across PYTHONHASHSEED")
    seeds = ["0", "1", "2", "3", "7", "42", "123", "999"]
    outputs = [_hash_seed_probe(s) for s in seeds]
    first = outputs[0]
    check(first.strip() != "", "probe produced non-empty output")
    check("VERDICT:" in first, "probe output contains the verdict")
    for s, o in zip(seeds, outputs):
        check(o == first, f"hash seed {s} matches seed {seeds[0]} (byte-identical)")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    test_build_is_deterministic()
    test_run_trials_zero_spread()
    test_retrieval_strength_is_pure_read()
    test_fan_effect_deterministic_across_hash_seeds()

    print()
    print(f"RESULT: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
