"""
Tests for the Phase 2B priming pipeline (swow.py + harness.read_targets + priming.py).

Guards the properties the study depends on, in the project's tiny check() style (NOT pytest):
  - BUILD DETERMINISM: building the SWOW graph twice yields identical readouts (values, not
    uuids) for the same blindly-selected pairs.
  - read_targets PURITY: it is a pure read — the store is byte-identical afterwards — AND it
    returns the IDENTICAL value retrieval_strength would for a single target (equivalence).
  - BLIND SELECTION: selecting pairs twice (same seed) is identical and never touches the
    engine; selection depends only on topology + strength.
  - ADVERSARIAL cross-process determinism: the FULL priming summary is byte-identical across
    PYTHONHASHSEED in {0,1,2,3,7,42,123,999}, run in fresh subprocesses (reuses the 2A
    pattern). To stay tractable on the large graph it runs a REDUCED-but-faithful config
    (PSYCHE_PRIMING_MAXROWS + small PSYCHE_PRIMING_NPRIMES) exercising the identical
    load→build→select→spread→summarize code path.

If the SWOW data file is absent, the data-dependent tests are SKIPPED with a clear notice
(counted as skipped, not passed/failed); the determinism subprocess test is skipped too.
The pure-logic test (stats helpers) always runs.

Run:
    python3 experiments/test_priming.py
"""

from __future__ import annotations

import os
import sys
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import swow
from harness import build_graph_from_spec, read_targets, retrieval_strength, SRC_DIR
import priming

_passed = 0
_failed = 0
_skipped = 0


def check(cond, msg):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {msg}")


def section(name):
    print(f"\n=== {name} ===")


def skip(msg):
    global _skipped
    _skipped += 1
    print(f"  SKIP: {msg}")


DATA_PRESENT = os.path.exists(swow.DEFAULT_DATA_PATH)

# A reduced edge set for fast, deterministic data-dependent tests. We take the first
# REDUCED_ROWS edges (the file is a fixed artifact, so this slice is fixed) — enough to
# exercise the real pipeline without building the full 1.39M-edge graph in every test.
REDUCED_ROWS = 60000
REDUCED_PRIMES = 8
REDUCED_SEED = 4242


def _reduced_setup():
    edges = swow.load_edges()[:REDUCED_ROWS]
    topo = swow.Topology(edges)
    pairs = swow.select_pairs(topo, REDUCED_PRIMES, seed=REDUCED_SEED)
    spec = swow.build_spec(edges)
    return edges, topo, pairs, spec


def _canonical_readout(pairs, inst):
    """Content-keyed (ID-independent) readout, so two builds can be compared for equal MEANING."""
    rows = []
    ids = inst.ids
    for d in pairs:
        res = read_targets(inst.store, ids[d["prime"]],
                           [ids[d["direct"]], ids[d["mediated"]], ids[d["unrelated"]]])
        a = res["activation"]
        rows.append((d["prime"], d["direct"], repr(a[ids[d["direct"]]]),
                     d["mediated"], repr(a[ids[d["mediated"]]]),
                     d["unrelated"], repr(a[ids[d["unrelated"]]]),
                     repr(res["outgoing_total"])))
    rows.sort()
    return tuple(rows)


def _store_snapshot(store):
    rows = []
    for rid in store.all_road_ids():
        r = store.get_road(rid, apply_decay=False)
        rows.append((r.source_id, r.target_id, repr(r.strength), r.traversal_count, r.closed))
    rows.sort()
    return (store.node_count(), store.road_count(), tuple(rows))


# ─────────────────────────────────────────────────────────────────────────────
# 1) pure-logic: stats helpers (always runs, no data needed)
# ─────────────────────────────────────────────────────────────────────────────

def test_stats_helpers():
    section("stats helpers (pure, deterministic)")
    check(priming._median([3, 1, 2]) == 2, "median odd")
    check(priming._median([4, 1, 2, 3]) == 2.5, "median even")
    check(abs(priming._spearman([1, 2, 3, 4], [1, 2, 3, 4]) - 1.0) < 1e-12, "spearman perfect +1")
    check(abs(priming._spearman([1, 2, 3, 4], [4, 3, 2, 1]) + 1.0) < 1e-12, "spearman perfect -1")
    check(priming._spearman([1, 1, 1], [1, 2, 3]) == 0.0, "spearman undefined -> 0")


# ─────────────────────────────────────────────────────────────────────────────
# 2) blind selection determinism (no engine)
# ─────────────────────────────────────────────────────────────────────────────

def test_selection_blind_and_deterministic():
    section("pair selection is deterministic and blind (topology only)")
    if not DATA_PRESENT:
        skip("SWOW data absent; selection test skipped")
        return
    edges = swow.load_edges()[:REDUCED_ROWS]
    topo = swow.Topology(edges)
    p1 = swow.select_pairs(topo, REDUCED_PRIMES, seed=REDUCED_SEED)
    p2 = swow.select_pairs(topo, REDUCED_PRIMES, seed=REDUCED_SEED)
    check(p1 == p2, "same seed -> identical pair selection")
    # selection used only topology/strength: every direct edge is a real SWOW edge
    okdirect = all(topo.index[d["direct"]] in topo.out_set[topo.index[d["prime"]]] for d in p1)
    check(okdirect, "every DIRECT target is a true 1-hop SWOW response of its prime")
    # mediated is NOT a direct edge but is 2-hop
    def is_two_hop(prime, tgt):
        pi = topo.index[prime]
        for m in topo.out[pi]:
            if topo.index[tgt] in topo.out_set[m]:
                return True
        return False
    okmed = all((topo.index[d["mediated"]] not in topo.out_set[topo.index[d["prime"]]])
                and is_two_hop(d["prime"], d["mediated"]) for d in p1)
    check(okmed, "every MEDIATED target is 2-hop and not direct")


# ─────────────────────────────────────────────────────────────────────────────
# 3) build determinism (values, not uuids)
# ─────────────────────────────────────────────────────────────────────────────

def test_build_determinism():
    section("build_graph_from_spec on SWOW: identical readout across rebuilds")
    if not DATA_PRESENT:
        skip("SWOW data absent; build determinism test skipped")
        return
    edges, topo, pairs, spec = _reduced_setup()
    a = _canonical_readout(pairs, build_graph_from_spec(spec))
    b = _canonical_readout(pairs, build_graph_from_spec(spec))
    check(a == b, "two SWOW builds give identical content-keyed readouts")
    check(len(a) == len(pairs), "readout covers all selected pairs")


# ─────────────────────────────────────────────────────────────────────────────
# 4) read_targets purity + equivalence to retrieval_strength
# ─────────────────────────────────────────────────────────────────────────────

def test_read_targets_pure_and_equivalent():
    section("read_targets: pure read + equals retrieval_strength per target")
    if not DATA_PRESENT:
        skip("SWOW data absent; purity test skipped")
        return
    edges, topo, pairs, spec = _reduced_setup()
    inst = build_graph_from_spec(spec)
    d = pairs[0]
    cue = inst.ids[d["prime"]]
    tgts = [inst.ids[d["direct"]], inst.ids[d["mediated"]], inst.ids[d["unrelated"]]]

    before = _store_snapshot(inst.store)
    for _ in range(3):
        read_targets(inst.store, cue, tgts)
    after = _store_snapshot(inst.store)
    check(before == after, "store byte-identical after repeated read_targets")

    # equivalence: each target value equals retrieval_strength for that target
    many = read_targets(inst.store, cue, tgts)["activation"]
    eq = all(many[t] == retrieval_strength(inst.store, cue, t) for t in tgts)
    check(eq, "read_targets per-target == retrieval_strength (same engine call)")


# ─────────────────────────────────────────────────────────────────────────────
# 5) ADVERSARIAL cross-process determinism of the FULL priming summary
# ─────────────────────────────────────────────────────────────────────────────

def _hash_seed_probe(seed: str) -> str:
    code = r'''
import os, sys
sys.path.insert(0, os.environ["PSYCHE_SRC"])
sys.path.insert(0, os.environ["PSYCHE_EXP"])
import priming
raise SystemExit(priming.main())
'''
    env = dict(os.environ)
    env["PSYCHE_SRC"] = SRC_DIR
    env["PSYCHE_EXP"] = _HERE
    env["PYTHONHASHSEED"] = seed
    # reduced-but-faithful: same code path, smaller graph + fewer primes
    env["PSYCHE_PRIMING_MAXROWS"] = str(REDUCED_ROWS)
    env["PSYCHE_PRIMING_NPRIMES"] = str(REDUCED_PRIMES)
    out = subprocess.run([sys.executable, "-c", code], env=env,
                         capture_output=True, text=True)
    if out.returncode != 0:
        print("  (subprocess stderr)\n" + out.stderr)
        return ""
    return out.stdout


def test_priming_deterministic_across_hash_seeds():
    section("ADVERSARIAL determinism: priming summary byte-identical across PYTHONHASHSEED")
    if not DATA_PRESENT:
        skip("SWOW data absent; cross-process determinism test skipped")
        return
    seeds = ["0", "1", "2", "3", "7", "42", "123", "999"]
    outputs = [_hash_seed_probe(s) for s in seeds]
    first = outputs[0]
    check(first.strip() != "", "probe produced non-empty output")
    check("VERDICTS" in first, "probe output contains verdicts")
    for s, o in zip(seeds, outputs):
        check(o == first, f"hash seed {s} matches seed {seeds[0]} (byte-identical)")


def main() -> int:
    test_stats_helpers()
    test_selection_blind_and_deterministic()
    test_build_determinism()
    test_read_targets_pure_and_equivalent()
    test_priming_deterministic_across_hash_seeds()
    print()
    print(f"RESULT: {_passed} passed, {_failed} failed, {_skipped} skipped")
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
