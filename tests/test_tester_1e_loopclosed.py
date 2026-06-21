"""
TESTER-authored DEEPEST adversarial + LOOP-CLOSED suite for SPEC-1e mechanism.

This is the suite that targets the make-or-break corners and the project's signature failure
mode: a component that passes on a friendly, hand-placed input but falls apart on a
system-generated one. Here the instrument is driven by pairs the SELECTOR produced (not
hand-placed targets), on a synthetic SWOW-like topology — loop-closure at the mechanism level.

DATA-FREE: the "SWOW-like" graph is a synthetic adversarial fixture (legitimate mechanism
testing per the task), NOT the real SWOW file (that is the validator's later graded run).

Properties attacked:
  - S0 integer-boundary: a W_gap = 1 (off-by-one) pair is NEVER admitted (no boundary leak);
    only a genuine W_gap = 0 collapse is admitted.
  - RESTORE exactness under a HOSTILE broadcast (saturating roads near strength 1.0; many
    reinforcing cycles before the measured prime) — the before/after restore is still exact.
  - last_touched is genuinely UNCHANGED by the broadcast on the simulated clock (so the
    instrument's choice not to revert it is provably safe, not merely asserted in a comment).
  - SELECTOR PURITY: select() does not mutate the Topology it reads.
  - LOOP-CLOSURE: feed selector-produced (prime, high, low) WORD pairs into the instrument
    built on the SAME synthetic graph; restore/determinism/purity hold on system-generated
    targets, not just hand-chosen ones.
  - all-zero-in-degree decile degeneracy: decile cuts collapsing to 0.0 do not crash matching.

Tiny built-in harness (print + count, exit nonzero), NOT pytest. Run as a script:
    python3 tests/test_tester_1e_loopclosed.py
"""

from __future__ import annotations

import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_EXP = os.path.join(_ROOT, "experiments")
_SRC = os.path.join(_ROOT, "src")
for _p in (_EXP, _SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from harness import build_graph_from_spec, read_targets
from nous_perceive import think
import priming_instrument as PI
from swow import Topology, traverse_count_for_strength as tcs
import priming_1e as S


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


def approx(a: float, b: float, tol: float = 1e-12) -> bool:
    return abs(a - b) <= tol


def topo(edges):
    return Topology(edges)


# ─────────────────────────────────────────────────────────────────────────────
# 1) S0 INTEGER BOUNDARY — a W_gap = 1 pair must NEVER be admitted (no off-by-one leak).
#    Build a prime whose HIGH-band and LOW-band members differ by EXACTLY one weight unit.
# ─────────────────────────────────────────────────────────────────────────────

def test_s0_rejects_w_gap_exactly_one():
    section("S0: a W_gap = 1 (off-by-one) HIGH/LOW pair is NEVER admitted (no boundary leak)")
    # Strengths chosen so the HIGH-band member maps to w=k and the LOW-band member to w=k-1.
    # 0.02 -> w3, 0.01 -> w2. Put a clean gap: low members ~0.01 (w2), high members ~0.02 (w3).
    # Use 5 direct edges with two distinct weight levels so bands separate and W_gap = 1.
    edges = [
        ("p", "lo1", 0.010), ("p", "lo2", 0.011), ("p", "lo3", 0.012),
        ("p", "hi1", 0.020), ("p", "hi2", 0.021),
    ]
    t = topo(edges)
    p = t.index["p"]
    high, low = S.high_low_bands(t, p)
    check(bool(high) and bool(low), "bands populate")
    # confirm EVERY weight-blind candidate is absent (all cross-pairs have W_gap == 1)
    gaps = set()
    for h in high:
        for l in low:
            if h != l:
                gaps.add(S.w_of(t, p, h) - S.w_of(t, p, l))
    check(gaps == {1}, f"every HIGH/LOW cross-pair has W_gap exactly 1 (got {gaps})")
    cuts = S.indegree_decile_cuts(t)
    check(S.select_s0_pair(t, p, cuts) is None, "W_gap=1 prime is NOT admitted to S0 (no leak)")
    check(S._has_weight_blind_pair(t, p) is False, "_has_weight_blind_pair False (no W_gap=0 pair)")


def test_s0_admitted_pair_is_always_weight_blind_invariant():
    section("S0 INVARIANT (randomized): EVERY admitted S0 pair is weight-blind (W_gap=0), never W_gap!=0")
    # Rather than hand-tune one fragile percentile window, sweep MANY random adversarial primes
    # and assert the cross-cutting invariant the meaning bar depends on: whenever select_s0_pair
    # admits a pair, that pair's W_gap is EXACTLY 0 — no W_gap!=0 pair ever leaks into S0,
    # across a wide range of strength distributions (floor, cap, mid, mixed).
    import random
    rng = random.Random(20260621)
    admitted = 0
    rejected_with_blind_pair = 0
    for trial in range(400):
        nresp = rng.randint(4, 9)
        # mix strengths across the floor (<0.01 -> w1), boundary, mid, and cap (>=0.09 -> w10)
        strengths = []
        for _ in range(nresp):
            bucket = rng.random()
            if bucket < 0.3:
                strengths.append(round(rng.uniform(0.001, 0.03), 4))   # low / boundary
            elif bucket < 0.6:
                strengths.append(round(rng.uniform(0.03, 0.09), 4))    # mid
            else:
                strengths.append(round(rng.uniform(0.09, 0.99), 4))    # cap region
        edges = [("p", f"r{i}", s) for i, s in enumerate(strengths)]
        # random in-degrees so matching sometimes passes, sometimes fails
        for i in range(nresp):
            for _ in range(rng.randint(0, 4)):
                edges.append((f"cue_{i}_{rng.random()}", f"r{i}", 0.5))
        # filler to give the global decile distribution some spread
        for k in range(rng.randint(0, 20)):
            edges.append((f"f{trial}_{k}", f"z{trial}_{k}", 0.5))
        t = topo(edges)
        p = t.index["p"]
        cuts = S.indegree_decile_cuts(t)
        pair = S.select_s0_pair(t, p, cuts)
        if pair is not None:
            h, l = pair
            # THE invariant: an admitted S0 pair is ALWAYS weight-blind
            check(S.w_of(t, p, h) == S.w_of(t, p, l),
                  f"trial {trial}: admitted S0 pair is weight-blind (W_gap=0)")
            # AND it is a genuine HIGH x LOW pair
            high, low = S.high_low_bands(t, p)
            check(h in high and l in low, f"trial {trial}: admitted pair is HIGH x LOW")
            # AND it is in-degree-matched
            check(S.decile_of(t.indeg[h], cuts) == S.decile_of(t.indeg[l], cuts),
                  f"trial {trial}: admitted pair shares a decile")
            admitted += 1
        else:
            if S._has_weight_blind_pair(t, p):
                rejected_with_blind_pair += 1
    # the sweep must have EXERCISED both branches to be non-vacuous
    check(admitted >= 1, f"the sweep admitted at least one S0 pair (non-vacuous; got {admitted})")
    check(rejected_with_blind_pair >= 1,
          f"the sweep also rejected >=1 prime that HAD a weight-blind pair (in-degree unmatched; "
          f"got {rejected_with_blind_pair}) — both branches fired")


# ─────────────────────────────────────────────────────────────────────────────
# 2) RESTORE EXACTNESS UNDER A HOSTILE BROADCAST (saturating roads + prior reinforcement).
# ─────────────────────────────────────────────────────────────────────────────

def _river_spec():
    return {
        "nodes": ["river", "water", "flow", "stream", "island", "lake"],
        "edges": [
            ("river", "water", 8), ("river", "flow", 8), ("river", "stream", 6),
            ("water", "flow", 7), ("water", "stream", 6), ("flow", "stream", 6),
            ("island", "lake", 8),
        ],
    }


def _full_snapshot(store):
    rows = []
    for rid in store.all_road_ids():
        r = store.get_road(rid, apply_decay=False)
        rows.append((r.source_id, r.target_id, r.creation_seq, repr(r.strength),
                     r.traversal_count, repr(r.last_touched), r.closed,
                     tuple(sorted((k, repr(v)) for k, v in r.charges.items()))))
    rows.sort()
    return (store.node_count(), store.road_count(), tuple(rows))


def test_restore_exact_after_prior_reinforcement():
    section("RESTORE: exact even after the winner's roads were reinforced toward saturation")
    spec = _river_spec()
    inst = build_graph_from_spec(spec)
    store = inst.store
    # First, hammer the winner with many broadcast cycles WITHOUT restoring (drive roads up
    # toward 1.0), to create a hostile near-saturation baseline. We use think directly.
    for _ in range(30):
        think(store, "river", broadcast=True)
    # NOW snapshot this hostile baseline and measure a prime with restore.
    baseline = _full_snapshot(store)
    tids = [inst.ids[c] for c in ("water", "flow", "stream")]
    res = PI.measure_ma_restore(store, "river", inst.ids["river"], tids)
    after = _full_snapshot(store)
    check(baseline == after, "store byte-identical after a restore on a near-saturated baseline")
    check(len(res.broadcast_road_ids) >= 1, "broadcast still fired (non-vacuous)")
    # and the strengths really were high (the hostile condition was real)
    max_str = max(store.get_road(rid, apply_decay=False).strength
                  for rid in store.all_road_ids())
    check(max_str > 0.9, f"baseline genuinely near saturation (max road strength {max_str:.4f})")


def test_last_touched_unchanged_by_broadcast_on_sim_clock():
    section("RESTORE-safety: the broadcast does NOT change last_touched on the simulated clock")
    # The instrument deliberately does not revert last_touched; this proves that omission safe.
    spec = _river_spec()
    inst = build_graph_from_spec(spec)
    store = inst.store
    before_lt = {rid: store.get_road(rid, apply_decay=False).last_touched
                 for rid in store.all_road_ids()}
    res = think(store, "river", broadcast=True)
    check(res.broadcast_ is not None and len(res.broadcast_.road_ids) >= 1, "broadcast fired")
    # the broadcast strengthened roads; their last_touched must equal the pre-broadcast value
    for rid in res.broadcast_.road_ids:
        check(store.get_road(rid, apply_decay=False).last_touched == before_lt[rid],
              "a strengthened road's last_touched is unchanged (sim clock now is constant)")


# ─────────────────────────────────────────────────────────────────────────────
# 3) SELECTOR PURITY — select() does not mutate the Topology it reads.
# ─────────────────────────────────────────────────────────────────────────────

def _topo_snapshot(t):
    """A hashable snapshot of all read-relevant Topology state."""
    return (
        t.n,
        tuple(t.words),
        tuple(tuple(o) for o in t.out),
        tuple(t.indeg),
        tuple(sorted((k, repr(v)) for k, v in t.strength.items())),
    )


def test_selector_does_not_mutate_topology():
    section("SELECTOR PURITY: select() leaves the Topology byte-identical (pure read)")
    edges = []
    for pn in ("p1", "p2", "p3", "p4"):
        edges += [(pn, f"{pn}_a", 0.2), (pn, f"{pn}_b", 0.3), (pn, f"{pn}_c", 0.4),
                  (pn, f"{pn}_d", 0.7), (pn, f"{pn}_e", 0.99), (pn, f"{pn}_f", 0.01)]
    edges += [("p1_e", "shared", 0.5), ("p2_e", "shared", 0.5), ("zz", "shared", 0.5)]
    t = topo(edges)
    before = _topo_snapshot(t)
    sel = S.select(t, n_primes=50)
    after = _topo_snapshot(t)
    check(before == after, "Topology unchanged by select() (pure read)")
    # also persisting pair lists must not mutate the selection or topology
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        S.save_pair_lists(sel, d)
    check(_topo_snapshot(t) == before, "Topology unchanged by save_pair_lists")


# ─────────────────────────────────────────────────────────────────────────────
# 4) LOOP-CLOSURE — drive the instrument with SELECTOR-PRODUCED pairs (system-generated),
#    on the SAME synthetic graph. Restore/purity/determinism must hold on these.
# ─────────────────────────────────────────────────────────────────────────────

def _swow_like_spec_and_topo():
    """A synthetic 'SWOW-like' graph: several dense word-clusters with cross-bridges, built so
    (a) the selector finds real arm-(b) primes/targets, and (b) think() yields winners whose
    broadcast fires. The SAME edge list (as integer traverse-counts) feeds BOTH the harness
    store (for the instrument) and the Topology (for the selector), so the selector's targets
    are addressable in the instrument's store. Returns (spec, topo, edges_float)."""
    # cluster A around 'maple' (a tree cluster); cluster B around 'piano' (a music cluster).
    # strengths chosen to populate HIGH (>=0.09 saturating) and LOW (low non-zero) bands.
    edges_float = [
        # 'maple' prime: 6 direct responses spanning strength
        ("maple", "leaf", 0.50), ("maple", "tree", 0.40), ("maple", "syrup", 0.30),
        ("maple", "wood", 0.20), ("maple", "branch", 0.02), ("maple", "twig", 0.01),
        # interconnect the maple cluster so a coalition forms and has internal roads
        ("leaf", "tree", 0.40), ("tree", "wood", 0.35), ("wood", "branch", 0.30),
        ("leaf", "branch", 0.25), ("tree", "syrup", 0.20),
        # 'piano' prime: 6 direct responses
        ("piano", "music", 0.55), ("piano", "key", 0.45), ("piano", "note", 0.35),
        ("piano", "song", 0.25), ("piano", "chord", 0.02), ("piano", "tune", 0.01),
        ("music", "key", 0.40), ("key", "note", 0.35), ("note", "song", 0.30),
        ("music", "chord", 0.25), ("song", "tune", 0.20),
        # a weak cross-bridge (keeps clusters mostly separate)
        ("syrup", "music", 0.02),
    ]
    words = sorted({w for c, r, _ in edges_float for w in (c, r)})
    spec_edges = [(c, r, tcs(s)) for (c, r, s) in edges_float]
    spec = {"nodes": words, "edges": spec_edges}
    return spec, Topology(edges_float), edges_float


def test_loop_closed_instrument_on_selector_pairs():
    section("LOOP-CLOSURE: instrument restore/purity hold on SELECTOR-produced (prime,high,low) pairs")
    spec, t, _ = _swow_like_spec_and_topo()
    sel = S.select(t, n_primes=20)
    check(len(sel.arm_b_d1) >= 1, "selector produced >=1 arm-(b)-d1 pair on the synthetic graph")

    # Build the instrument store from the SAME spec; addr targets by content (word).
    inst = build_graph_from_spec(spec)
    store = inst.store
    baseline = _full_snapshot(store)

    measured = 0
    for d in sel.arm_b_d1:
        prime_w, high_w, low_w = d["prime"], d["high"], d["low"]
        # all three words exist as nodes in the store (same spec)
        if prime_w not in inst.ids or high_w not in inst.ids or low_w not in inst.ids:
            continue
        tids = [inst.ids[high_w], inst.ids[low_w]]
        # drive the instrument with the SYSTEM-GENERATED prime utterance + targets
        res = PI.measure_ma_restore(store, prime_w, inst.ids[prime_w], tids)
        # restore must leave the shared store byte-identical after EACH selector-driven prime
        check(_full_snapshot(store) == baseline,
              f"store byte-identical after selector-pair prime '{prime_w}' (loop-closed restore)")
        measured += 1
    check(measured >= 1, "at least one selector-produced pair was measured through the instrument")


def test_loop_closed_restore_equals_rebuild_on_selector_pair():
    section("LOOP-CLOSURE: RESTORE == REBUILD on a selector-produced prime (system-generated)")
    spec, t, _ = _swow_like_spec_and_topo()
    sel = S.select(t, n_primes=20)
    # pick the first arm-b pair whose prime actually perceives (its content is a token)
    chosen = None
    inst0 = build_graph_from_spec(spec)
    for d in sel.arm_b_d1:
        if d["prime"] in inst0.ids and d["high"] in inst0.ids and d["low"] in inst0.ids:
            # verify think on this prime yields a winner with a non-empty broadcast
            probe = build_graph_from_spec(spec)
            r = think(probe.store, d["prime"], broadcast=True)
            if r.broadcast_ is not None and len(r.broadcast_.road_ids) >= 1:
                chosen = d
                break
    check(chosen is not None, "found a selector pair whose prime drives a non-empty broadcast")
    if chosen is None:
        return

    prime_w, high_w, low_w = chosen["prime"], chosen["high"], chosen["low"]
    targets = [high_w, low_w]

    def prime_id(store):
        for nid in store.all_node_ids():
            if store.get_node(nid).content == prime_w:
                return nid
        raise KeyError(prime_w)

    def targets_in(store):
        by = {store.get_node(nid).content: nid for nid in store.all_node_ids()}
        return [by[c] for c in targets]

    factory = lambda: build_graph_from_spec(spec).store
    rebuilt = PI.measure_ma_rebuild(factory, prime_w, prime_id, targets_in)

    inst = build_graph_from_spec(spec)
    store = inst.store
    tids = [inst.ids[c] for c in targets]
    restored = PI.measure_ma_restore(store, prime_w, inst.ids[prime_w], tids)

    reb_vals = list(rebuilt.delta.values())
    res_vals = [restored.delta[t] for t in tids]
    for i, (rv, sv) in enumerate(zip(reb_vals, res_vals)):
        check(approx(rv, sv, 1e-12),
              f"selector-pair target #{i}: REBUILD Δ ({rv!r}) == RESTORE Δ ({sv!r})")


# ─────────────────────────────────────────────────────────────────────────────
# 5) DECILE DEGENERACY — many in-degree-0 nodes collapse the cuts to 0.0; matching must not
#    crash and must still partition by the (degenerate) deciles deterministically.
# ─────────────────────────────────────────────────────────────────────────────

def test_decile_cuts_all_zero_does_not_crash():
    section("DEGENERACY: in-degree distribution collapsing cuts to 0.0 does not crash matching")
    # A graph where most nodes are leaves with in-degree 1 and the global decile cuts are tiny.
    edges = []
    for pn in ("p1", "p2"):
        edges += [(pn, f"{pn}_a", 0.2), (pn, f"{pn}_b", 0.3), (pn, f"{pn}_c", 0.4),
                  (pn, f"{pn}_d", 0.7), (pn, f"{pn}_e", 0.99)]
    # add many in-degree-0 pure-source nodes (they only point out) to drag deciles to 0.0
    for k in range(50):
        edges.append((f"orphan{k}", f"sink{k}", 0.5))
    t = topo(edges)
    cuts = S.indegree_decile_cuts(t)
    # with a flood of in-degree-0 sources, low deciles should be 0.0 (degenerate)
    check(cuts[0] == 0.0, "lowest decile cut is 0.0 under heavy in-degree-0 mass")
    # selection must not crash and must produce a consistent result
    sel = S.select(t, n_primes=50)
    check(isinstance(sel.s0, list), "select() handled degenerate deciles without crashing")
    # every S0 pair is still genuinely matched under the degenerate cuts
    for d in sel.s0:
        hi, lo = t.index[d["high"]], t.index[d["low"]]
        check(S.decile_of(t.indeg[hi], cuts) == S.decile_of(t.indeg[lo], cuts),
              "S0 pair shares a decile even under degenerate cuts")


def test_self_loop_and_duplicate_edges_handled():
    section("HOSTILE INPUT: self-loops and duplicate edges in the float edge list are tolerated")
    # The Topology dedups duplicate directed edges (keeps max strength) and the SWOW loader
    # drops self-loops; but Topology itself is fed (cue,resp,strength) — feed it a self-loop and
    # duplicates directly and confirm no double-counting and no crash.
    edges = [
        ("p", "a", 0.5), ("p", "a", 0.9),   # duplicate p->a: keep max (0.9)
        ("p", "p", 0.5),                       # self-loop (Topology will store it)
        ("p", "b", 0.3), ("p", "c", 0.4), ("p", "d", 0.7),
    ]
    t = topo(edges)
    p = t.index["p"]
    # duplicate did not inflate out-degree beyond distinct targets
    check(len(t.out[p]) == len({t.index["a"], t.index["b"], t.index["c"], t.index["d"],
                                t.index["p"]}),
          "duplicate p->a counted once (distinct out-neighbors)")
    # kept the MAX strength on the duplicate
    check(approx(t.strength[(p, t.index["a"])], 0.9), "duplicate edge kept max strength (0.9)")
    # selection runs without crashing on this hostile topology
    sel = S.select(t, n_primes=10)
    check(isinstance(sel.arm_b_d1, list), "select tolerated self-loop + duplicate without crash")


# ─────────────────────────────────────────────────────────────────────────────
# 6) LOOP-CLOSED DETERMINISM — selector pairs + instrument together, byte-identical across
#    processes. This is the strongest determinism claim: the full mechanism chain.
# ─────────────────────────────────────────────────────────────────────────────

_CHAIN_CHILD = r'''
import os, sys, hashlib
_EXP = os.environ["E1E_EXP"]; _SRC = os.environ["E1E_SRC"]
for p in (_EXP, _SRC):
    if p not in sys.path:
        sys.path.insert(0, p)
from harness import build_graph_from_spec
from swow import Topology, traverse_count_for_strength as tcs
import priming_1e as S
import priming_instrument as PI

edges_float = [
    ("maple", "leaf", 0.50), ("maple", "tree", 0.40), ("maple", "syrup", 0.30),
    ("maple", "wood", 0.20), ("maple", "branch", 0.02), ("maple", "twig", 0.01),
    ("leaf", "tree", 0.40), ("tree", "wood", 0.35), ("wood", "branch", 0.30),
    ("leaf", "branch", 0.25), ("tree", "syrup", 0.20),
    ("piano", "music", 0.55), ("piano", "key", 0.45), ("piano", "note", 0.35),
    ("piano", "song", 0.25), ("piano", "chord", 0.02), ("piano", "tune", 0.01),
    ("music", "key", 0.40), ("key", "note", 0.35), ("note", "song", 0.30),
    ("music", "chord", 0.25), ("song", "tune", 0.20),
    ("syrup", "music", 0.02),
]
words = sorted({w for c, r, _ in edges_float for w in (c, r)})
spec = {"nodes": words, "edges": [(c, r, tcs(s)) for (c, r, s) in edges_float]}
t = Topology(edges_float)
sel = S.select(t, n_primes=20)

inst = build_graph_from_spec(spec)
store = inst.store
blob = ""
for d in sel.arm_b_d1:
    pw, hw, lw = d["prime"], d["high"], d["low"]
    if pw in inst.ids and hw in inst.ids and lw in inst.ids:
        tids = [inst.ids[hw], inst.ids[lw]]
        res = PI.measure_ma_restore(store, pw, inst.ids[pw], tids)
        blob += "%s|%s=%r|%s=%r\n" % (pw, hw, res.delta[inst.ids[hw]],
                                      lw, res.delta[inst.ids[lw]])
sys.stdout.write(hashlib.sha256(blob.encode("utf-8")).hexdigest())
'''


def test_loop_closed_determinism_across_processes():
    section("LOOP-CLOSED DETERMINISM: selector+instrument chain byte-identical across 6 seeds")
    env = dict(os.environ)
    env["E1E_EXP"] = _EXP
    env["E1E_SRC"] = _SRC
    digests = []
    for seed in ("0", "1", "3", "97", "65537", "2147483647"):
        e = dict(env)
        e["PYTHONHASHSEED"] = seed
        out = subprocess.run([sys.executable, "-c", _CHAIN_CHILD],
                             env=e, capture_output=True, text=True)
        if out.returncode != 0:
            print("    child stderr:", out.stderr[-800:])
        check(out.returncode == 0, f"chain child (seed {seed}) ran cleanly")
        digests.append(out.stdout.strip())
    check(len(set(digests)) == 1,
          f"selector+instrument chain digest identical across seeds (got {len(set(digests))})")
    check(all(d for d in digests), "every chain child produced a non-empty digest")


def main() -> int:
    test_s0_rejects_w_gap_exactly_one()
    test_s0_admitted_pair_is_always_weight_blind_invariant()
    test_restore_exact_after_prior_reinforcement()
    test_last_touched_unchanged_by_broadcast_on_sim_clock()
    test_selector_does_not_mutate_topology()
    test_loop_closed_instrument_on_selector_pairs()
    test_loop_closed_restore_equals_rebuild_on_selector_pair()
    test_decile_cuts_all_zero_does_not_crash()
    test_self_loop_and_duplicate_edges_handled()
    test_loop_closed_determinism_across_processes()

    print("\n" + "=" * 60)
    print(f"RESULT: {_passed} passed, {_failed} failed")
    print("=" * 60)
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
