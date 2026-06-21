"""
TESTER-authored ADVERSARIAL suite for the SPEC-1e §9 broadcast-Δ instrument
(experiments/priming_instrument.py). Independent of the builder's tests; the verdict rests here.

MECHANISM-only, DATA-FREE: every graph is a synthetic fixture whose driver is the engine's
OWN deterministic output (loop-closed), never a hand-placed activation value. The instrument
makes no cognitive/priming claim and computes no verdict; here we attack only its mechanism:

  - PER-PRIME RESTORE IS EXACT: snapshot the full store (every mutable road field) before and
    after measure_ma_restore — must be BYTE-IDENTICAL. Probe INTERNAL road fields (strength,
    traversal_count, last_touched, closed, charges, creation_seq), not just a top-level equal.
  - MULTI-PRIME SWEEPS ARE ORDER-INDEPENDENT: a prime's Δ is identical regardless of its
    position in the sweep (no cross-contamination), AND the store is byte-identical after a
    full sweep.
  - M-A == REBUILD reference: the fast RESTORE path equals the obviously-correct REBUILD path
    exactly, on graphs where a broadcast genuinely fires.
  - M-A CAPTURES THE BROADCAST: build a case where broadcast vs no-broadcast MUST differ and
    confirm Δ != 0 there (M-A is the closed-loop Δ, not a bare-spread mislabel); and a target
    outside the broadcast's reach has Δ == 0 (the named cost).
  - M-B is the bare spread: equals harness.read_targets / retrieval_strength exactly.
  - PURITY: the pristine "before" reads never mutate the store.
  - DETERMINISM across processes: M-A/M-B byte-identical across 6 randomized PYTHONHASHSEED in
    fresh interpreters.

Tiny built-in harness (print + count, exit nonzero), NOT pytest. Run as a script:
    python3 tests/test_tester_1e_instrument_adversarial.py
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

from harness import build_graph_from_spec, read_targets, retrieval_strength
from nous_perceive import think
from nous_activation import DEFAULT_DECAY_PER_HOP
import priming_instrument as PI


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
# Synthetic fixtures (the prime CONTENT name is matched by perceive() against node
# content; perceive tokenizes alnum>=2 and matches a token IN the lowercased content).
# A dense cluster makes a winner whose internal roads the broadcast strengthens.
# ─────────────────────────────────────────────────────────────────────────────

def dense_spec():
    """A dense 'river/water/flow/stream' cluster (so think('river') yields a winner with
    internal roads the broadcast strengthens), plus a SEPARATE disconnected component
    'island/lake' that the prime cannot reach at all — a target the broadcast provably cannot
    reach (Δ = exactly 0, before=after=0). Distinct from the builder's coffee fixture.

    The disconnected component (rather than a weak bridge) is deliberate: a bridge can be
    swallowed into the winner and then the broadcast DOES raise the far target's activation
    (a legitimate Δ != 0). A disconnected node is the clean, unambiguous out-of-reach case."""
    return {
        "nodes": ["river", "water", "flow", "stream", "island", "lake"],
        "edges": [
            ("river", "water", 8),
            ("river", "flow", 8),
            ("river", "stream", 6),
            ("water", "flow", 7),
            ("water", "stream", 6),
            ("flow", "stream", 6),
            ("island", "lake", 8),   # a SEPARATE component; no path river -> island
        ],
    }


def two_cluster_spec():
    """Two dense clusters sharing no token; used for multi-prime order-independence — each
    prime activates its own cluster, and the two primes must not contaminate each other."""
    return {
        "nodes": ["alpha", "beta", "gamma", "delta",
                  "sun", "moon", "star", "comet"],
        "edges": [
            ("alpha", "beta", 8), ("alpha", "gamma", 8), ("alpha", "delta", 6),
            ("beta", "gamma", 7), ("beta", "delta", 6), ("gamma", "delta", 6),
            ("sun", "moon", 8), ("sun", "star", 8), ("sun", "comet", 6),
            ("moon", "star", 7), ("moon", "comet", 6), ("star", "comet", 6),
        ],
    }


def _store_snapshot(store):
    """Order-independent canonical snapshot of EVERY mutable road field (raw, un-decayed),
    so identical snapshots imply identical stored state. Probes internal structure, not just
    a top-level equality. Includes creation_seq (identity-order) for completeness."""
    rows = []
    for rid in store.all_road_ids():
        r = store.get_road(rid, apply_decay=False)
        rows.append((
            r.source_id, r.target_id, r.creation_seq,
            repr(r.strength), r.traversal_count, repr(r.last_touched), r.closed,
            tuple(sorted((k, repr(v)) for k, v in r.charges.items())),
        ))
    rows.sort()
    return (store.node_count(), store.road_count(), tuple(rows))


def _resolvers(spec, prime_content, target_contents):
    """Build name->id resolvers (content names map to per-build NodeIDs)."""
    def prime_id(store):
        # find the node whose content == prime_content
        for nid in store.all_node_ids():
            if store.get_node(nid).content == prime_content:
                return nid
        raise KeyError(prime_content)

    def targets_in(store):
        by_content = {store.get_node(nid).content: nid for nid in store.all_node_ids()}
        return [by_content[c] for c in target_contents]

    return prime_id, targets_in


# ─────────────────────────────────────────────────────────────────────────────
# 1) PER-PRIME RESTORE IS EXACT — full-store byte-identity before/after RESTORE.
# ─────────────────────────────────────────────────────────────────────────────

def test_restore_is_byte_identical():
    section("RESTORE: the shared store is BYTE-IDENTICAL before and after a measurement")
    spec = dense_spec()
    inst = build_graph_from_spec(spec)
    store = inst.store
    targets = [inst.ids[c] for c in ("water", "flow", "stream", "lake")]

    before_snap = _store_snapshot(store)
    res = PI.measure_ma_restore(store, "river", inst.ids["river"], targets)
    after_snap = _store_snapshot(store)

    check(before_snap == after_snap,
          "store byte-identical after measure_ma_restore (restore exact)")
    # sanity: the broadcast actually fired (else the restore test is vacuous)
    check(len(res.broadcast_road_ids) >= 1,
          "broadcast fired (>=1 internal road) — restore test is non-vacuous")


def test_restore_exact_after_repeated_measurements():
    section("RESTORE: store stays byte-identical after MANY repeated measurements of one prime")
    spec = dense_spec()
    inst = build_graph_from_spec(spec)
    store = inst.store
    targets = [inst.ids[c] for c in ("water", "flow", "stream")]

    baseline = _store_snapshot(store)
    deltas = []
    for _ in range(25):
        res = PI.measure_ma_restore(store, "river", inst.ids["river"], targets)
        deltas.append(tuple(sorted((t, repr(res.delta[t])) for t in targets)))
        check(_store_snapshot(store) == baseline, "store identical after each repeat")
    # every repeat must give the IDENTICAL delta (no drift from imperfect restore)
    check(len(set(deltas)) == 1, "Δ identical across 25 repeats (no cumulative drift)")


def test_restore_internal_fields_probed_individually():
    section("RESTORE: each internal road field (strength/traversal_count/last_touched/closed) reverts")
    spec = dense_spec()
    inst = build_graph_from_spec(spec)
    store = inst.store
    targets = [inst.ids[c] for c in ("water", "flow")]

    # capture per-road field maps before
    rids = list(store.all_road_ids())
    before = {rid: store.get_road(rid, apply_decay=False) for rid in rids}
    before_fields = {
        rid: (repr(r.strength), r.traversal_count, repr(r.last_touched), r.closed,
              tuple(sorted((k, repr(v)) for k, v in r.charges.items())))
        for rid, r in before.items()
    }
    PI.measure_ma_restore(store, "river", inst.ids["river"], targets)
    for rid in rids:
        r = store.get_road(rid, apply_decay=False)
        now_fields = (repr(r.strength), r.traversal_count, repr(r.last_touched), r.closed,
                      tuple(sorted((k, repr(v)) for k, v in r.charges.items())))
        check(now_fields == before_fields[rid],
              f"road {rid[:8]} all fields reverted (strength/trav/touched/closed/charges)")


# ─────────────────────────────────────────────────────────────────────────────
# 2) MULTI-PRIME SWEEP ORDER-INDEPENDENCE — a prime's Δ is independent of its position.
# ─────────────────────────────────────────────────────────────────────────────

def test_multiprime_sweep_order_independent():
    section("SWEEP: each prime's Δ is identical regardless of position (no cross-contamination)")
    spec = two_cluster_spec()
    primes = [("alpha", ["beta", "gamma", "delta"]),
              ("sun", ["moon", "star", "comet"])]

    def sweep(order):
        inst = build_graph_from_spec(spec)
        store = inst.store
        out = {}
        for pc, tcs_ in order:
            tids = [inst.ids[c] for c in tcs_]
            res = PI.measure_ma_restore(store, pc, inst.ids[pc], tids)
            out[pc] = tuple(sorted((c, repr(res.delta[inst.ids[c]])) for c in tcs_))
        return out

    fwd = sweep(primes)
    rev = sweep(list(reversed(primes)))
    for pc, _ in primes:
        check(fwd[pc] == rev[pc],
              f"prime '{pc}' Δ identical in forward vs reversed sweep (order-independent)")


def test_sweep_store_identical_after_full_pass():
    section("SWEEP: shared store is byte-identical after a full multi-prime pass")
    spec = two_cluster_spec()
    inst = build_graph_from_spec(spec)
    store = inst.store
    baseline = _store_snapshot(store)
    for pc, tcs_ in [("alpha", ["beta", "gamma"]), ("sun", ["moon", "star"])]:
        tids = [inst.ids[c] for c in tcs_]
        PI.measure_ma_restore(store, pc, inst.ids[pc], tids)
    check(_store_snapshot(store) == baseline,
          "store byte-identical after a full 2-prime sweep")


# ─────────────────────────────────────────────────────────────────────────────
# 3) M-A == REBUILD reference (the fast path equals the obviously-correct path).
# ─────────────────────────────────────────────────────────────────────────────

def test_ma_restore_equals_rebuild():
    section("M-A: RESTORE fast path equals the REBUILD reference EXACTLY")
    spec = dense_spec()
    prime_id, targets_in = _resolvers(spec, "river", ["water", "flow", "stream", "lake"])
    factory = lambda: build_graph_from_spec(spec).store

    rebuilt = PI.measure_ma_rebuild(factory, "river", prime_id, targets_in)

    inst = build_graph_from_spec(spec)
    store = inst.store
    tids = [inst.ids[c] for c in ("water", "flow", "stream", "lake")]
    restored = PI.measure_ma_restore(store, "river", inst.ids["river"], tids)

    # align by content (different store IDs); compare the Δ values
    reb_by_content = {}
    # rebuild returns ids of its OWN last build; we cannot map them back to content easily,
    # so re-derive: rebuild aligns targets BY ORDER (its docstring), and so do we.
    reb_vals = list(rebuilt.delta.values())
    res_vals = [restored.delta[t] for t in tids]
    # both pipelines processed the SAME content order, so order-aligned values must match
    check(len(reb_vals) == len(res_vals), "same number of targets in both pipelines")
    for i, (rv, sv) in enumerate(zip(reb_vals, res_vals)):
        check(approx(rv, sv, 1e-12),
              f"target #{i}: REBUILD Δ ({rv!r}) == RESTORE Δ ({sv!r})")


# ─────────────────────────────────────────────────────────────────────────────
# 4) M-A CAPTURES THE BROADCAST (not a bare-spread mislabel) + the named-cost Δ=0.
# ─────────────────────────────────────────────────────────────────────────────

def test_ma_nonzero_where_broadcast_reaches():
    section("M-A: Δ != 0 for a winner-internal target (broadcast genuinely raises reachability)")
    spec = dense_spec()
    inst = build_graph_from_spec(spec)
    store = inst.store
    # water/flow/stream are inside the winning 'river' cluster — at least one internal target
    # must see a NON-zero Δ (the broadcast strengthened an internal road on its path).
    tids = [inst.ids[c] for c in ("water", "flow", "stream")]
    res = PI.measure_ma_restore(store, "river", inst.ids["river"], tids)
    nonzero = [t for t in tids if abs(res.delta[t]) > 0.0]
    check(len(nonzero) >= 1,
          "at least one winner-internal target has Δ != 0 (M-A reflects the broadcast)")


def test_ma_is_not_bare_spread():
    section("M-A: the Δ is the broadcast effect, NOT the bare-spread value (they differ)")
    # If M-A were a mislabeled bare spread, Δ would equal the activation itself, not the change.
    # Here we confirm Δ (after-before) is strictly smaller than the bare activation for an
    # internal target — i.e. M-A measures the CHANGE the broadcast caused, a small positive
    # increment, while the bare spread (M-B) is the full activation.
    spec = dense_spec()
    inst = build_graph_from_spec(spec)
    store = inst.store
    tids = [inst.ids[c] for c in ("water", "flow", "stream")]
    res = PI.measure_ma_restore(store, "river", inst.ids["river"], tids)
    mb = PI.measure_mb(store, inst.ids["river"], tids)
    for t in tids:
        if abs(res.delta[t]) > 0.0:
            # the broadcast Δ is a strict increment, far below the full bare activation
            check(abs(res.delta[t]) < mb[t],
                  "Δ (broadcast increment) is strictly less than the bare-spread activation")
            # and Δ == after - before exactly
            check(approx(res.delta[t], res.after[t] - res.before[t], 1e-15),
                  "Δ == after - before (definition)")


def test_ma_zero_outside_broadcast_reach():
    section("M-A named cost: a target OUTSIDE the winner gets Δ == 0 (broadcast cannot reach it)")
    spec = dense_spec()
    inst = build_graph_from_spec(spec)
    store = inst.store
    # 'lake' is in the disconnected island/lake component, unreachable from the 'river' prime;
    # the spread never reaches it (before=after=0), so Δ must be exactly 0 — the named cost.
    tid_lake = inst.ids["lake"]
    res = PI.measure_ma_restore(store, "river", inst.ids["river"], [tid_lake])
    check(res.before[tid_lake] == 0.0 and res.after[tid_lake] == 0.0,
          "unreachable target: before and after activation both exactly 0.0")
    check(res.delta[tid_lake] == 0.0, "out-of-reach target has Δ exactly 0.0")
    check(res.in_winner_reach[tid_lake] is False, "in_winner_reach correctly False for it")


def test_ma_unperceived_prime_is_noop():
    section("M-A: an utterance matching NO node yields an empty broadcast and all-zero Δ (no crash)")
    spec = dense_spec()
    inst = build_graph_from_spec(spec)
    store = inst.store
    baseline = _store_snapshot(store)
    tids = [inst.ids[c] for c in ("water", "flow")]
    # 'zzqq' matches no node content -> perceive finds no sources -> no winner -> empty broadcast
    res = PI.measure_ma_restore(store, "zzqq", inst.ids["river"], tids)
    check(res.broadcast_road_ids == [], "no-perception utterance -> empty broadcast")
    check(all(res.delta[t] == 0.0 for t in tids), "all Δ == 0 for a no-op broadcast")
    check(_store_snapshot(store) == baseline, "store untouched by a no-op measurement")


# ─────────────────────────────────────────────────────────────────────────────
# 5) M-B is exactly the bare spread (equals retrieval_strength / read_targets).
# ─────────────────────────────────────────────────────────────────────────────

def test_mb_equals_retrieval_strength():
    section("M-B: equals harness.retrieval_strength / read_targets exactly (it IS the bare spread)")
    spec = dense_spec()
    inst = build_graph_from_spec(spec)
    store = inst.store
    tids = [inst.ids[c] for c in ("water", "flow", "stream", "lake")]
    mb = PI.measure_mb(store, inst.ids["river"], tids)
    # compare to retrieval_strength one target at a time (incl. the unreachable 'lake' -> 0.0)
    for t in tids:
        rs = retrieval_strength(store, inst.ids["river"], t)
        check(approx(mb[t], rs, 1e-15), f"M-B[{t[:6]}] == retrieval_strength ({mb[t]!r})")
    # and to read_targets directly
    rt = read_targets(store, inst.ids["river"], tids)["activation"]
    for t in tids:
        check(approx(mb[t], rt[t], 1e-15), "M-B == read_targets activation")


def test_mb_is_pure_read():
    section("M-B: a bare-spread measurement does not mutate the store (purity)")
    spec = dense_spec()
    inst = build_graph_from_spec(spec)
    store = inst.store
    baseline = _store_snapshot(store)
    tids = [inst.ids[c] for c in ("water", "flow", "stream")]
    for _ in range(10):
        PI.measure_mb(store, inst.ids["river"], tids)
    check(_store_snapshot(store) == baseline, "store byte-identical after 10 M-B reads (pure)")


# ─────────────────────────────────────────────────────────────────────────────
# 6) PURITY of the pristine "before" path in REBUILD (the before read on the pristine
#    store must not mutate it; the broadcast happens only on the SEPARATE bstore).
# ─────────────────────────────────────────────────────────────────────────────

def test_rebuild_pristine_store_not_mutated():
    section("REBUILD: the pristine 'before' store is never mutated (purity of the baseline read)")
    spec = dense_spec()
    # capture a snapshot of a freshly built store, then run the before-read path on it and
    # confirm no change. We replicate measure_ma_rebuild's pristine branch explicitly.
    inst = build_graph_from_spec(spec)
    store = inst.store
    baseline = _store_snapshot(store)
    tids = [inst.ids[c] for c in ("water", "flow", "stream", "lake")]
    # the before read used inside the instrument:
    read_targets(store, inst.ids["river"], tids)
    check(_store_snapshot(store) == baseline, "pristine baseline read leaves store unchanged")


# ─────────────────────────────────────────────────────────────────────────────
# 7) DETERMINISM across processes (6 randomized PYTHONHASHSEED). M-A/M-B byte-identical.
# ─────────────────────────────────────────────────────────────────────────────

_DET_CHILD = r'''
import os, sys, hashlib
_EXP = os.environ["E1E_EXP"]; _SRC = os.environ["E1E_SRC"]
for p in (_EXP, _SRC):
    if p not in sys.path:
        sys.path.insert(0, p)
from harness import build_graph_from_spec
import priming_instrument as PI

spec = {
    "nodes": ["river", "water", "flow", "stream", "island", "lake"],
    "edges": [
        ("river", "water", 8), ("river", "flow", 8), ("river", "stream", 6),
        ("water", "flow", 7), ("water", "stream", 6), ("flow", "stream", 6),
        ("island", "lake", 8),
    ],
}
inst = build_graph_from_spec(spec)
store = inst.store
tids = [inst.ids[c] for c in ("water", "flow", "stream", "lake")]

# M-A via RESTORE on the live store
ma = PI.measure_ma_restore(store, "river", inst.ids["river"], tids)
# M-B bare spread
mb = PI.measure_mb(store, inst.ids["river"], tids)

# serialize by CONTENT (stable across builds), not by uuid id
id2content = {inst.ids[c]: c for c in inst.ids}
blob = "MA-DELTA\n"
for t in tids:
    blob += "%s=%r\n" % (id2content[t], ma.delta[t])
blob += "MA-BEFORE\n"
for t in tids:
    blob += "%s=%r\n" % (id2content[t], ma.before[t])
blob += "MA-AFTER\n"
for t in tids:
    blob += "%s=%r\n" % (id2content[t], ma.after[t])
blob += "MA-NROADS=%d\nWMC=%d\n" % (len(ma.broadcast_road_ids), ma.winner_member_count)
blob += "MB\n"
for t in tids:
    blob += "%s=%r\n" % (id2content[t], mb[t])
sys.stdout.write(hashlib.sha256(blob.encode("utf-8")).hexdigest())
'''


def test_determinism_across_processes():
    section("DETERMINISM: M-A/M-B byte-identical across 6 randomized PYTHONHASHSEED (fresh procs)")
    env = dict(os.environ)
    env["E1E_EXP"] = _EXP
    env["E1E_SRC"] = _SRC
    digests = []
    for seed in ("0", "1", "7", "42", "131071", "2147483647"):
        e = dict(env)
        e["PYTHONHASHSEED"] = seed
        out = subprocess.run([sys.executable, "-c", _DET_CHILD],
                             env=e, capture_output=True, text=True)
        if out.returncode != 0:
            print("    child stderr:", out.stderr[-800:])
        check(out.returncode == 0, f"determinism child (seed {seed}) ran cleanly")
        digests.append(out.stdout.strip())
    check(len(set(digests)) == 1,
          f"M-A/M-B digest identical across all seeds (got {len(set(digests))} distinct)")
    check(all(d for d in digests), "every child produced a non-empty digest")


# ─────────────────────────────────────────────────────────────────────────────
# 8) RESTORE vs REBUILD agree on the SWEEP (not just a single prime), the deeper isolation
#    guarantee: running primes on a shared+restored store must equal running each on a fresh
#    store. This is the loop-closure of the instrument's own isolation claim.
# ─────────────────────────────────────────────────────────────────────────────

def test_restore_sweep_equals_independent_rebuilds():
    section("ISOLATION: a RESTORE sweep equals INDEPENDENT per-prime REBUILDs (loop-closed)")
    spec = two_cluster_spec()
    primes = [("alpha", ["beta", "gamma", "delta"]),
              ("sun", ["moon", "star", "comet"])]

    # RESTORE sweep on one shared store
    inst = build_graph_from_spec(spec)
    store = inst.store
    restore_out = {}
    for pc, tcs_ in primes:
        tids = [inst.ids[c] for c in tcs_]
        res = PI.measure_ma_restore(store, pc, inst.ids[pc], tids)
        restore_out[pc] = tuple(sorted((c, repr(res.delta[inst.ids[c]])) for c in tcs_))

    # independent REBUILDs (each prime on its own fresh pair of stores)
    rebuild_out = {}
    for pc, tcs_ in primes:
        prime_id, targets_in = _resolvers(spec, pc, tcs_)
        factory = lambda: build_graph_from_spec(spec).store
        res = PI.measure_ma_rebuild(factory, pc, prime_id, targets_in)
        # rebuild aligns by order; pair the ordered deltas with the ordered contents
        rebuild_out[pc] = tuple(sorted((c, repr(v))
                                       for c, v in zip(tcs_, list(res.delta.values()))))

    for pc, _ in primes:
        check(restore_out[pc] == rebuild_out[pc],
              f"prime '{pc}': RESTORE-sweep Δ == independent-REBUILD Δ (isolation holds)")


# ─────────────────────────────────────────────────────────────────────────────
# runner
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    test_restore_is_byte_identical()
    test_restore_exact_after_repeated_measurements()
    test_restore_internal_fields_probed_individually()
    test_multiprime_sweep_order_independent()
    test_sweep_store_identical_after_full_pass()
    test_ma_restore_equals_rebuild()
    test_ma_nonzero_where_broadcast_reaches()
    test_ma_is_not_bare_spread()
    test_ma_zero_outside_broadcast_reach()
    test_ma_unperceived_prime_is_noop()
    test_mb_equals_retrieval_strength()
    test_mb_is_pure_read()
    test_rebuild_pristine_store_not_mutated()
    test_determinism_across_processes()
    test_restore_sweep_equals_independent_rebuilds()

    print("\n" + "=" * 60)
    print(f"RESULT: {_passed} passed, {_failed} failed")
    print("=" * 60)
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
