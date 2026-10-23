"""
MECHANISM tests for the SPEC-1e §9 broadcast-Δ instrument (experiments/priming_instrument.py).

These verify the INSTRUMENT'S MECHANISM ONLY — never a cognitive/priming claim, never a
verdict. They prove, on small CONTROLLED graphs where the correct answer is derivable from
the engine's OWN deterministic output (loop-closed, never a hand-placed activation value):

  - M-A correctness: the broadcast-trace Δ the instrument reports equals the change a manual
    pristine-vs-broadcast read produces; for a single winner-internal edge it equals exactly
    (after_strength − before_strength) × decay_per_hop, where the strengths come from the
    engine's OWN Broadcast record (not hand-authored).
  - M-A reach / named cost: a target OUTSIDE the broadcast's reach has Δ = 0 (EXP-1e §4).
  - M-B correctness: matches harness.read_targets / retrieval_strength exactly (it IS that).
  - PURITY: the pristine "before" reads never mutate the store.
  - ISOLATION: RESTORE leaves the shared store byte-identical after a full sweep; REBUILD and
    RESTORE agree exactly; a sweep is ORDER-INDEPENDENT (a prime's Δ does not depend on its
    position) — the per-prime isolation EXP-1e §9 requires.
  - DETERMINISM across processes: M-A/M-B for a fixed graph are byte-identical across
    PYTHONHASHSEED in fresh interpreters (the substrate bar).
  - ASSERTED-NEGATIVE known limitation: without the per-prime restore, a prior prime's
    broadcast LEAKS into a later measurement (the compounding the restore exists to stop) —
    pinned so the limitation is explicit, not hidden.

Tiny built-in harness (print + count, exit nonzero), NOT pytest — the project convention.
Run as a script:  python3 experiments/test_priming_instrument.py
"""

from __future__ import annotations

import os
import sys
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from harness import build_graph_from_spec, read_targets, retrieval_strength, SRC_DIR
from psyche_perceive import think
from psyche_activation import DEFAULT_DECAY_PER_HOP
import priming_instrument as PI


# ─────────────────────────────────────────────────────────────────────────────
# Tiny test harness
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


def approx(a: float, b: float, tol: float = 1e-12) -> bool:
    return abs(a - b) <= tol


# ─────────────────────────────────────────────────────────────────────────────
# Controlled graphs (the prime CONTENT name is matched by perceive() against node
# content, so the prime utterance is the prime node's content)
# ─────────────────────────────────────────────────────────────────────────────

def warm_spec():
    """A 'warm' cluster around coffee (coffee/kitchen/morning/mug densely linked), with a
    weak bridge into an UNNAMED domain (work/office). When think('coffee') runs, coffee's
    cluster wins; the broadcast strengthens roads internal to the winner. 'office' is far
    from the prime and outside the winner — a target the broadcast cannot reach (Δ=0)."""
    return {
        "nodes": ["coffee", "kitchen", "morning", "mug", "work", "office"],
        "edges": [
            ("coffee", "kitchen", 8),
            ("coffee", "morning", 8),
            ("coffee", "mug", 6),
            ("kitchen", "morning", 7),
            ("kitchen", "mug", 6),
            ("morning", "mug", 6),
            ("mug", "work", 2),     # weak bridge to the unnamed domain
            ("work", "office", 8),
        ],
    }


def _store_snapshot(store):
    """Order-independent canonical snapshot of every mutable road field a read or a
    restored broadcast could move (raw, un-decayed). Identical snapshots ⇒ identical state."""
    rows = []
    for rid in store.all_road_ids():
        r = store.get_road(rid, apply_decay=False)
        rows.append((
            r.source_id, r.target_id, repr(r.strength),
            r.traversal_count, r.closed,
            tuple(sorted((k, repr(v)) for k, v in r.charges.items())),
        ))
    rows.sort()
    return (store.node_count(), store.road_count(), tuple(rows))


# ─────────────────────────────────────────────────────────────────────────────
# 1) M-A correctness — loop-closed: the Δ equals the engine's own pristine-vs-broadcast
#    change, and for a single winner-internal edge equals (after−before)×decay_per_hop.
# ─────────────────────────────────────────────────────────────────────────────

def test_ma_matches_manual_pristine_vs_broadcast():
    section("M-A equals a manual pristine-vs-broadcast read (loop-closed, engine-derived)")
    spec = warm_spec()
    factory = lambda: build_graph_from_spec(spec).store

    # Resolve content→IDs per store (IDs differ per build; library is invariant).
    def prime_id(store):
        return next(n for n in store.all_node_ids() if store.get_node(n).content == "coffee")

    def target_ids(store):
        wanted = ["kitchen", "morning", "mug", "office"]
        by_content = {store.get_node(n).content: n for n in store.all_node_ids()}
        return [by_content[w] for w in wanted]

    res = PI.measure_ma_rebuild(factory, "coffee", prime_id, target_ids)

    # Independent manual computation of the SAME thing, using the engine directly:
    pristine = factory()
    pj = prime_id(pristine)
    pt = target_ids(pristine)
    before = read_targets(pristine, pj, pt)["activation"]
    before_vals = [before[t] for t in pt]

    bstore = factory()
    think(bstore, "coffee", broadcast=True)
    bj = prime_id(bstore)
    bt = target_ids(bstore)
    after = read_targets(bstore, bj, bt)["activation"]
    after_vals = [after[t] for t in bt]

    manual_delta = [a - b for a, b in zip(after_vals, before_vals)]
    # res.delta is keyed by the instrument's OWN internal broadcast-store IDs (different uuids),
    # but its insertion order matches the target CONTENT order ("kitchen","morning","mug",
    # "office") — same content order as `manual_delta`. So compare the ordered value lists,
    # which is robust to the differing IDs.
    inst_delta_by_order = list(res.delta.values())  # insertion order == content order
    check(len(inst_delta_by_order) == 4, "instrument measured all four targets")
    for i, (md, idv) in enumerate(zip(manual_delta, inst_delta_by_order)):
        check(approx(md, idv),
              f"target#{i}: instrument Δ {idv!r} == manual Δ {md!r}")


def test_ma_single_internal_edge_is_derivable():
    section("M-A single winner-internal edge: Δ == (after−before)×decay_per_hop (derivable)")
    # A minimal graph: prime P with two strong direct targets A,B forming a coalition, and a
    # leaf L reachable ONLY by the single internal edge A→L. Then L's activation from P is
    # the product along P→A→L, and the broadcast changes ONLY A→L's strength among the paths
    # that reach L (P→A is also internal and strengthened, compounding) — so to keep it
    # exactly derivable we read the DIRECT target A, reached from P by the single edge P→A.
    spec = {
        "nodes": ["alpha", "beta", "gamma"],
        "edges": [
            ("alpha", "beta", 8),
            ("alpha", "gamma", 8),
            ("beta", "gamma", 7),
        ],
    }
    store = build_graph_from_spec(spec).store
    by_content = {store.get_node(n).content: n for n in store.all_node_ids()}
    P = by_content["alpha"]
    A = by_content["beta"]

    # pristine activation at A from P, and the canonical strength of P→A before broadcast
    before_act = retrieval_strength(store, P, A)
    rid_PA = store.find_road(P, A)
    s_before = store.get_road(rid_PA, apply_decay=False).strength

    # run the real broadcast and read the engine's OWN after-strength for P→A
    res = think(store, "alpha", broadcast=True)
    # P→A must be an internal road of the winner (alpha+beta+gamma are one dense cluster)
    check(rid_PA in res.broadcast_.road_ids, "P→A is a winner-internal road that was broadcast")
    s_after = store.get_road(rid_PA, apply_decay=False).strength
    after_act = retrieval_strength(store, P, A)

    # A is reached from P by paths P→A (1 hop) AND P→gamma... no: gamma→beta exists, so A=beta
    # is also reached via P→gamma→beta. To keep the single-edge derivation exact we instead
    # assert the engine-consistent identity directly on the measured activations, and check
    # the 1-hop component moved by exactly (s_after − s_before) × decay_per_hop in the LIMIT
    # where A's only inbound from the spread is P→A. Since beta has an inbound gamma→beta,
    # we validate the DERIVABLE law on a clean leaf instead (next test) and here assert the
    # measured before/after are internally consistent with a positive, bounded move.
    check(after_act > before_act, "broadcast raised A's activation (winner-internal edge)")
    check(s_after > s_before, "engine strengthened P→A (its own Broadcast record)")
    # the strengthen law: s_after = s_before + 0.13*(1 - s_before)
    expected_after = s_before + 0.13 * (1.0 - s_before)
    check(approx(s_after, expected_after, tol=1e-9),
          f"engine strengthen law holds: {s_after!r} == {expected_after!r}")


def test_ma_direct_target_delta_law_from_engine_record():
    section("M-A direct-neighbour Δ obeys the strengthen×decay law on the engine's OWN record")
    # Loop-closed (no hand-placed activation): in `warm`, the prime 'coffee' wins and the
    # engine ITSELF reports coffee→kitchen among the broadcast roads (verified below from
    # res.broadcast_.road_ids, not assumed). 'kitchen' has exactly ONE inbound road in the
    # whole graph — coffee→kitchen — so the spread reaches kitchen only via that single 1-hop
    # edge. Therefore its activation is energy×strength×decay, and the closed-loop Δ is
    # EXACTLY (s_after − s_before) × decay_per_hop, with the strengths taken from the engine's
    # OWN Broadcast record. This proves the instrument's Δ is precisely the activation change
    # the broadcast produced, derived from engine output rather than asserted.
    spec = warm_spec()
    knobs = PI.default_knobs()
    decay = knobs["decay_per_hop"]
    energy = knobs["energy"]

    store = build_graph_from_spec(spec).store
    bc = {store.get_node(n).content: n for n in store.all_node_ids()}
    P = bc["coffee"]
    kitchen = bc["kitchen"]

    # confirm kitchen has exactly one inbound road (so the single-path derivation is valid)
    inbound = list(store.roads_into(kitchen))
    check(len(inbound) == 1, f"kitchen has exactly one inbound road; got {len(inbound)}")

    before_k = retrieval_strength(store, P, kitchen, **knobs)
    res = think(store, "coffee", broadcast=True)
    after_k = retrieval_strength(store, P, kitchen, **knobs)

    rid_PK = store.find_road(P, kitchen)
    check(rid_PK in res.broadcast_.road_ids,
          "engine broadcast coffee→kitchen (winner-internal, from its own record)")
    s_before = res.broadcast_.before[rid_PK]
    s_after = res.broadcast_.after[rid_PK]
    expected_delta = energy * (s_after - s_before) * decay
    measured_delta = after_k - before_k
    check(approx(measured_delta, expected_delta, tol=1e-9),
          f"Δ(kitchen) {measured_delta!r} == energy×(Δstrength)×decay {expected_delta!r}")
    # and the absolute before value matches the single-edge law too (sanity on the path model)
    check(approx(before_k, energy * s_before * decay, tol=1e-9),
          "pristine kitchen activation == energy×strength×decay (single 1-hop inbound)")

    # and the instrument reproduces exactly this Δ on a fresh build (rebuild isolation)
    factory = lambda: build_graph_from_spec(spec).store

    def prime_id(s):
        return next(n for n in s.all_node_ids() if s.get_node(n).content == "coffee")

    def target_ids(s):
        b = {s.get_node(n).content: n for n in s.all_node_ids()}
        return [b["kitchen"]]

    mres = PI.measure_ma_rebuild(factory, "coffee", prime_id, target_ids, knobs=knobs)
    check(approx(list(mres.delta.values())[0], measured_delta, tol=1e-9),
          "instrument Δ(kitchen) equals the engine ground-truth Δ(kitchen)")


# ─────────────────────────────────────────────────────────────────────────────
# 2) M-A named cost: a target OUTSIDE the broadcast's reach has Δ = 0 (EXP-1e §4)
# ─────────────────────────────────────────────────────────────────────────────

def test_ma_unreachable_target_delta_zero():
    section("M-A named cost: a target the broadcast cannot reach has Δ = exactly 0")
    # `island` is a fully disconnected node: the prime's spread never reaches it under ANY
    # broadcast, so its before == after == 0.0 and Δ is exactly 0.0. This pins the EXP-1e §4
    # "named cost": the broadcast strengthens only the winner's roads, so a target the spread
    # does not reach gets Δ = 0 regardless of association strength.
    spec = warm_spec()
    spec = dict(spec)
    spec["nodes"] = list(spec["nodes"]) + ["island"]   # disconnected; no edges touch it
    factory = lambda: build_graph_from_spec(spec).store

    def prime_id(s):
        return next(n for n in s.all_node_ids() if s.get_node(n).content == "coffee")

    def target_ids(s):
        bc = {s.get_node(n).content: n for n in s.all_node_ids()}
        return [bc["island"]]

    res = PI.measure_ma_rebuild(factory, "coffee", prime_id, target_ids)
    island_delta = list(res.delta.values())[0]
    check(island_delta == 0.0,
          f"island (unreachable from the prime) has Δ exactly 0.0; got {island_delta!r}")
    check(list(res.in_winner_reach.values())[0] is False,
          "island is flagged NOT in the broadcast's reach (before == after)")


# ─────────────────────────────────────────────────────────────────────────────
# 3) M-B correctness — it IS harness.read_targets / retrieval_strength
# ─────────────────────────────────────────────────────────────────────────────

def test_mb_matches_read_targets():
    section("M-B equals harness.read_targets / retrieval_strength exactly")
    store = build_graph_from_spec(warm_spec()).store
    by_content = {store.get_node(n).content: n for n in store.all_node_ids()}
    P = by_content["coffee"]
    targets = [by_content[c] for c in ("kitchen", "morning", "mug", "office")]

    mb = PI.measure_mb(store, P, targets)
    ref = read_targets(store, P, targets)["activation"]
    for t in targets:
        check(approx(mb[t], ref[t]), f"M-B[{t}] == read_targets[{t}]")
    # and the single-target equivalence to retrieval_strength
    for t in targets:
        check(approx(mb[t], retrieval_strength(store, P, t)),
              f"M-B[{t}] == retrieval_strength single-target")


# ─────────────────────────────────────────────────────────────────────────────
# 4) PURITY — the pristine "before" reads never mutate the store
# ─────────────────────────────────────────────────────────────────────────────

def test_mb_is_pure_read():
    section("M-B purity: the store is byte-identical before and after repeated M-B reads")
    store = build_graph_from_spec(warm_spec()).store
    by_content = {store.get_node(n).content: n for n in store.all_node_ids()}
    P = by_content["coffee"]
    targets = [by_content[c] for c in ("kitchen", "morning", "mug")]
    before = _store_snapshot(store)
    for _ in range(3):
        PI.measure_mb(store, P, targets)
    after = _store_snapshot(store)
    check(before == after, "M-B leaves the store byte-identical (pure read)")


# ─────────────────────────────────────────────────────────────────────────────
# 5) ISOLATION — RESTORE == REBUILD, RESTORE leaves the store byte-identical,
#    a sweep is ORDER-INDEPENDENT (the per-prime isolation EXP-1e §9 requires)
# ─────────────────────────────────────────────────────────────────────────────

def test_restore_equals_rebuild():
    section("Isolation: RESTORE path Δ == REBUILD path Δ (fast path validated vs reference)")
    spec = warm_spec()
    factory = lambda: build_graph_from_spec(spec).store

    def prime_id(s):
        return next(n for n in s.all_node_ids() if s.get_node(n).content == "coffee")

    def target_ids(s):
        bc = {s.get_node(n).content: n for n in s.all_node_ids()}
        return [bc[c] for c in ("kitchen", "morning", "mug", "office")]

    rebuilt = PI.measure_ma_rebuild(factory, "coffee", prime_id, target_ids)

    shared = factory()
    P = prime_id(shared)
    T = target_ids(shared)
    restored = PI.measure_ma_restore(shared, "coffee", P, T)

    rb = list(rebuilt.delta.values())
    rs = [restored.delta[t] for t in T]
    check(len(rb) == len(rs) == 4, "both paths measured four targets")
    for i, (a, b) in enumerate(zip(rb, rs)):
        check(approx(a, b), f"target#{i}: RESTORE Δ {b!r} == REBUILD Δ {a!r}")


def test_restore_leaves_store_byte_identical():
    section("Isolation: RESTORE leaves the shared store byte-identical (per-prime cleanup)")
    spec = warm_spec()
    shared = build_graph_from_spec(spec).store
    by_content = {shared.get_node(n).content: n for n in shared.all_node_ids()}
    P = by_content["coffee"]
    T = [by_content[c] for c in ("kitchen", "morning", "mug", "office")]

    before = _store_snapshot(shared)
    # measure the same prime many times on the SHARED store; each must clean up after itself
    for _ in range(5):
        PI.measure_ma_restore(shared, "coffee", P, T)
    after = _store_snapshot(shared)
    check(before == after,
          "shared store byte-identical after repeated RESTORE measurements (no broadcast leak)")


def test_sweep_is_order_independent():
    section("Isolation: a multi-prime sweep is ORDER-INDEPENDENT (prime Δ ⊥ position)")
    # Two primes that BOTH win clusters and whose broadcasts touch overlapping roads, so a
    # missing restore WOULD make order matter. We measure prime 'coffee' first-then-second
    # in a shared-store sweep and assert its Δ is identical regardless of position.
    spec = {
        "nodes": ["coffee", "tea", "kitchen", "morning", "cup", "leaf"],
        "edges": [
            ("coffee", "kitchen", 8), ("coffee", "morning", 8), ("coffee", "cup", 7),
            ("kitchen", "morning", 7), ("kitchen", "cup", 6), ("morning", "cup", 6),
            ("tea", "kitchen", 8), ("tea", "cup", 8), ("tea", "leaf", 7),
            ("kitchen", "leaf", 6), ("cup", "leaf", 6),
        ],
    }

    def fresh():
        s = build_graph_from_spec(spec).store
        bc = {s.get_node(n).content: n for n in s.all_node_ids()}
        return s, bc

    # sweep order 1: coffee, then tea
    s1, bc1 = fresh()
    Pc1, Tc1 = bc1["coffee"], [bc1["kitchen"], bc1["cup"]]
    Pt1, Tt1 = bc1["tea"], [bc1["kitchen"], bc1["cup"]]
    d_coffee_first = {c: PI.measure_ma_restore(s1, "coffee", Pc1, Tc1).delta[t]
                      for c, t in zip(("kitchen", "cup"), Tc1)}
    _ = PI.measure_ma_restore(s1, "tea", Pt1, Tt1)

    # sweep order 2: tea, then coffee  (coffee now SECOND)
    s2, bc2 = fresh()
    Pc2, Tc2 = bc2["coffee"], [bc2["kitchen"], bc2["cup"]]
    Pt2, Tt2 = bc2["tea"], [bc2["kitchen"], bc2["cup"]]
    _ = PI.measure_ma_restore(s2, "tea", Pt2, Tt2)
    d_coffee_second = {c: PI.measure_ma_restore(s2, "coffee", Pc2, Tc2).delta[t]
                       for c, t in zip(("kitchen", "cup"), Tc2)}

    for c in ("kitchen", "cup"):
        check(approx(d_coffee_first[c], d_coffee_second[c]),
              f"coffee Δ[{c}] identical whether measured first {d_coffee_first[c]!r} or "
              f"second {d_coffee_second[c]!r}")


# ─────────────────────────────────────────────────────────────────────────────
# 6) ASSERTED-NEGATIVE known limitation — WITHOUT restore, a prior prime's broadcast
#    LEAKS into a later measurement (the exact compounding the restore exists to stop).
# ─────────────────────────────────────────────────────────────────────────────

def test_known_limitation_no_restore_leaks():
    section("ASSERTED-NEGATIVE: without per-prime restore, an earlier broadcast LEAKS")
    spec = warm_spec()
    shared = build_graph_from_spec(spec).store
    by_content = {shared.get_node(n).content: n for n in shared.all_node_ids()}
    P = by_content["coffee"]
    T = [by_content["kitchen"]]

    # clean baseline Δ (with restore)
    clean = PI.measure_ma_restore(shared, "coffee", P, T).delta[T[0]]

    # now DELIBERATELY leak: apply a broadcast WITHOUT restoring (simulate the bug)
    think(shared, "coffee", broadcast=True)   # left un-restored on purpose

    # the SAME measurement now starts from a contaminated baseline → its Δ differs
    leaked = PI.measure_ma_restore(shared, "coffee", P, T).delta[T[0]]
    check(not approx(clean, leaked, tol=1e-9),
          "an un-restored prior broadcast changes a later prime's Δ (leak is real) — this is "
          "exactly why measure_ma_restore reverts each prime; the instrument's API does the "
          f"restore (clean={clean!r}, leaked={leaked!r})")


# ─────────────────────────────────────────────────────────────────────────────
# 7) DETERMINISM across processes — M-A/M-B byte-identical across PYTHONHASHSEED
# ─────────────────────────────────────────────────────────────────────────────

_DET_PROBE = r'''
import os, sys
sys.path.insert(0, os.environ["PSYCHE_SRC"])
sys.path.insert(0, os.environ["PSYCHE_EXP"])
from harness import build_graph_from_spec, read_targets
import priming_instrument as PI

spec = {
    "nodes": ["coffee", "kitchen", "morning", "mug", "work", "office"],
    "edges": [
        ("coffee", "kitchen", 8), ("coffee", "morning", 8), ("coffee", "mug", 6),
        ("kitchen", "morning", 7), ("kitchen", "mug", 6), ("morning", "mug", 6),
        ("mug", "work", 2), ("work", "office", 8),
    ],
}
factory = lambda: build_graph_from_spec(spec).store

def prime_id(s):
    return next(n for n in s.all_node_ids() if s.get_node(n).content == "coffee")
def target_ids(s):
    bc = {s.get_node(n).content: n for n in s.all_node_ids()}
    return [bc[c] for c in ("kitchen", "morning", "mug", "work", "office")]

ma = PI.measure_ma_rebuild(factory, "coffee", prime_id, target_ids)
# print Δ in CONTENT order (IDs differ per process; content order is stable)
btargets = target_ids(factory())  # only to fix the order labels
labels = ["kitchen", "morning", "mug", "work", "office"]
vals = [ma.delta[k] for k in ma.delta]   # insertion order == target_ids order == labels
for lab, v in zip(labels, vals):
    print("MA", lab, repr(v))

shared = factory()
P = prime_id(shared); T = target_ids(shared)
mb = PI.measure_mb(shared, P, T)
for lab, t in zip(labels, T):
    print("MB", lab, repr(mb[t]))
'''


def _det_probe(seed: str) -> str:
    env = dict(os.environ)
    env["PSYCHE_SRC"] = SRC_DIR
    env["PSYCHE_EXP"] = _HERE
    env["PYTHONHASHSEED"] = seed
    out = subprocess.run([sys.executable, "-c", _DET_PROBE], env=env,
                         capture_output=True, text=True)
    if out.returncode != 0:
        print("  (subprocess stderr)\n" + out.stderr)
        return ""
    return out.stdout


def test_determinism_across_hash_seeds():
    section("ADVERSARIAL determinism: M-A/M-B byte-identical across PYTHONHASHSEED")
    seeds = ["0", "1", "2", "7", "42", "123"]
    outs = [_det_probe(s) for s in seeds]
    first = outs[0]
    check(first.strip() != "", "determinism probe produced non-empty output")
    check("MA kitchen" in first and "MB kitchen" in first, "probe output has M-A and M-B rows")
    for s, o in zip(seeds, outs):
        check(o == first, f"hash seed {s} matches seed {seeds[0]} (byte-identical M-A/M-B)")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    test_ma_matches_manual_pristine_vs_broadcast()
    test_ma_single_internal_edge_is_derivable()
    test_ma_direct_target_delta_law_from_engine_record()
    test_ma_unreachable_target_delta_zero()
    test_mb_matches_read_targets()
    test_mb_is_pure_read()
    test_restore_equals_rebuild()
    test_restore_leaves_store_byte_identical()
    test_sweep_is_order_independent()
    test_known_limitation_no_restore_leaks()
    test_determinism_across_hash_seeds()

    print()
    print(f"RESULT: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
