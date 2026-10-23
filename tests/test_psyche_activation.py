"""
Test suite for Psyche spreading activation.

Pins the QUALITATIVE behavior, not specific magnitudes (the constants are
uncalibrated and will change). Run directly:
    python3 test_psyche_activation.py
"""

from psyche_store import SubstrateStore, Clock, NodeType, NotFound
from psyche_activation import (
    spread_activation, closed_transmission,
    CLOSED_BREAKTHROUGH_THRESHOLD, CLOSED_LEAK_FRACTION,
)

_passed = 0
_failed = 0

def check(cond, msg):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {msg}")

def expect_raises(exc, fn, msg):
    global _passed, _failed
    try:
        fn()
    except exc:
        _passed += 1
    except Exception as e:
        _failed += 1
        print(f"  FAIL: {msg} — raised {type(e).__name__}, expected {exc.__name__}")
    else:
        _failed += 1
        print(f"  FAIL: {msg} — nothing raised, expected {exc.__name__}")

def section(name):
    print(f"\n{name}")


def _well_worn(store, src, tgt, n=40, charge=None):
    """Helper: build a strong (highway-ish) road by repeated traversal."""
    for _ in range(n):
        store.traverse(src, tgt, charge=charge)


# ─────────────────────────────────────────────────────────────────────────────

def test_seed_must_exist():
    section("a missing seed raises NotFound")
    s = SubstrateStore(clock=Clock(simulated=True))
    expect_raises(NotFound, lambda: spread_activation(s, "nope"),
                  "spreading from a non-existent seed raises NotFound")


def test_isolated_seed_lights_only_itself():
    section("an isolated seed lights only itself")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("alone", NodeType.CONCEPT)
    r = spread_activation(s, a)
    check(r.activation.get(a, 0) > 0, "seed has activation")
    check(len(r.ranked()) == 0, "nothing else lit (no roads to anywhere)")


def test_activation_attenuates_with_distance():
    section("activation attenuates with distance (near > far)")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    _well_worn(s, a, b)
    _well_worn(s, b, c)
    r = spread_activation(s, a)
    check(r.activation[b] > r.activation[c],
          "nearer node (b, 1 hop) is more active than farther (c, 2 hops)")
    check(r.hops[b] == 1 and r.hops[c] == 2, "hop distances recorded correctly")


def test_stronger_road_carries_more():
    section("edge conductance: a stronger road carries more activation")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    strong_t = s.add_node("strong_target", NodeType.CONCEPT)
    weak_t = s.add_node("weak_target", NodeType.CONCEPT)
    _well_worn(s, a, strong_t, n=40)        # highway
    s.traverse(a, weak_t)                    # single crossing: dirt
    r = spread_activation(s, a)
    check(r.activation[strong_t] > r.activation[weak_t],
          "activation through the strong road exceeds the weak road")


def test_convergent_activation_sums():
    section("convergent activation SUMS (the cognitive property)")
    # Diamond: a→b, a→c, b→d, c→d. d is reached by two paths and must sum.
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    d = s.add_node("d", NodeType.CONCEPT)
    e = s.add_node("e", NodeType.CONCEPT)   # control: reached by ONE path of same depth
    for src, tgt in [(a, b), (a, c), (b, d), (c, d), (b, e)]:
        _well_worn(s, src, tgt)
    r = spread_activation(s, a)
    # d (two converging 2-hop paths) should be more active than e (one 2-hop path)
    check(r.activation[d] > r.activation[e],
          "node reached by two converging paths is more active than one of equal depth")


def test_no_double_count_downstream_of_convergence():
    section("convergence node with a downstream child is NOT double-counted")
    # Diamond WITH A TAIL: a→b, a→c, b→d, c→d, d→f.  Both paths to d are EQUAL LENGTH
    # (2 hops). Under hop-layered expansion, d expands at hop 2 carrying the full sum
    # of BOTH equal-length paths, and propagates that full value to f exactly once.
    # So for EQUAL-LENGTH convergence the exact-match below is a genuine invariant —
    # NOT a coincidence of edge strengths (that was the earlier bug). Determinism and
    # the partial-vs-full distinction for UNEQUAL paths are covered by the next test.
    from psyche_activation import DEFAULT_DECAY_PER_HOP as DPH
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    d = s.add_node("d", NodeType.CONCEPT)
    f = s.add_node("f", NodeType.CONCEPT)
    _well_worn(s, a, b, n=40)   # deliberately lopsided strengths...
    _well_worn(s, a, c, n=8)    # ...to prove the RESULT does not depend on them
    _well_worn(s, b, d, n=40)
    _well_worn(s, c, d, n=40)
    _well_worn(s, d, f, n=40)

    res = spread_activation(s, a, energy=1.0, floor=0.0, hop_budget=10)

    def s_of(x, y):
        return s.get_road(s.find_road(x, y), apply_decay=False).strength
    energy = 1.0
    act_b = energy * s_of(a, b) * DPH
    act_c = energy * s_of(a, c) * DPH
    # d accumulates from BOTH equal-length in-paths
    act_d = act_b * s_of(b, d) * DPH + act_c * s_of(c, d) * DPH
    # f receives d's FULL value exactly once (equal-length convergence → exact)
    expected_f = act_d * s_of(d, f) * DPH

    check(abs(res.activation[d] - act_d) < 1e-9,
          f"d sums both equal-length in-paths (got {res.activation[d]:.6f}, "
          f"expected {act_d:.6f})")
    check(abs(res.activation[f] - expected_f) < 1e-9,
          f"f gets d's full value exactly once for equal-length convergence "
          f"(got {res.activation[f]:.6f}, expected {expected_f:.6f})")
    # guard against the OLD double-count signature
    double_counted_f = (act_b * s_of(b, d) * DPH) * s_of(d, f) * DPH + expected_f
    check(res.activation[f] < double_counted_f - 1e-9,
          "f is strictly below what additive re-expansion would have produced")


def test_expansion_is_deterministic_under_edge_strength():
    section("post-convergence activation is DETERMINISTIC, not order-dependent")
    # This is the test the previous round was missing. Build the SAME diamond-with-tail
    # topology twice, differing ONLY in how lopsided the a→b vs a→c strengths are.
    # With the old activation-priority heap, the parent that popped first decided
    # whether f got d's partial or full value, so f wobbled with edge strength. With
    # hop-layering, d is reached at hop 2 by BOTH paths regardless of their strength,
    # so f's relationship to d's full value is invariant. We assert that in BOTH graphs
    # f equals (d_full × s(d,f) × decay) exactly — the property that must NOT depend on
    # which parent is stronger.
    from psyche_activation import DEFAULT_DECAY_PER_HOP as DPH

    def build_and_check(n_ab, n_ac, label):
        s = SubstrateStore(clock=Clock(simulated=True))
        a = s.add_node("a", NodeType.CONCEPT)
        b = s.add_node("b", NodeType.CONCEPT)
        c = s.add_node("c", NodeType.CONCEPT)
        d = s.add_node("d", NodeType.CONCEPT)
        f = s.add_node("f", NodeType.CONCEPT)
        _well_worn(s, a, b, n=n_ab)
        _well_worn(s, a, c, n=n_ac)
        _well_worn(s, b, d, n=40)
        _well_worn(s, c, d, n=40)
        _well_worn(s, d, f, n=40)
        res = spread_activation(s, a, energy=1.0, floor=0.0, hop_budget=10)

        def s_of(x, y):
            return s.get_road(s.find_road(x, y), apply_decay=False).strength
        act_d = (1.0 * s_of(a, b) * DPH * s_of(b, d) * DPH
                 + 1.0 * s_of(a, c) * DPH * s_of(c, d) * DPH)
        expected_f = act_d * s_of(d, f) * DPH
        check(abs(res.activation[f] - expected_f) < 1e-9,
              f"[{label}] f = d_full × s(d,f) × decay regardless of edge lopsidedness "
              f"(got {res.activation[f]:.6f}, expected {expected_f:.6f})")

    # the reviewer's two parameter sets: strongly lopsided vs near-balanced
    build_and_check(n_ab=60, n_ac=3, label="lopsided")     # heap would drop c's ripple
    build_and_check(n_ab=40, n_ac=8, label="moderate")
    build_and_check(n_ab=20, n_ac=20, label="balanced")    # heap might keep it
    # all three must yield the SAME relationship of f to d's full value → determinism


def test_determinism_with_same_hop_edge_adversarial():
    section("ADVERSARIAL determinism: a same-hop edge must not leak into the result")
    # The PREVIOUS determinism test cannot expose intra-layer order-dependence: its two
    # hop-1 nodes (b, c) have no edge between them. This one is built to BREAK the claim.
    #
    # Topology: a→b, a→c (b and c both hop-1), b→c (an INTRA-LAYER edge), c→f.
    #   The legitimate, short path to f is: a→c→f (length 2).
    #   The longer path that must NOT be propagated as if short: a→b→c→f (length 3).
    # Without the layer-freeze, whether b expands before c (decided by uuid hash order,
    # which varies per process) determines whether c expands carrying the extra a→b→c
    # contribution — making f swing across process runs. With the freeze, c expands from
    # its hop-1 value (a→c only); the b→c contribution lands in c's accumulation but
    # propagates onward only in the NEXT layer, i.e. the length-3 path to f is correctly
    # dropped. So f must equal the SHORTER-PATH-ONLY value, deterministically.
    from psyche_activation import DEFAULT_DECAY_PER_HOP as DPH

    def build():
        s = SubstrateStore(clock=Clock(simulated=True))
        a = s.add_node("a", NodeType.CONCEPT)
        b = s.add_node("b", NodeType.CONCEPT)
        c = s.add_node("c", NodeType.CONCEPT)
        f = s.add_node("f", NodeType.CONCEPT)
        _well_worn(s, a, b, n=50)
        _well_worn(s, a, c, n=10)
        _well_worn(s, b, c, n=50)   # the adversarial intra-layer (hop-1 → hop-1) edge
        _well_worn(s, c, f, n=40)
        return s, a, b, c, f

    s, a, b, c, f = build()
    res = spread_activation(s, a, energy=1.0, floor=0.0, hop_budget=10)

    def s_of(x, y):
        return s.get_road(s.find_road(x, y), apply_decay=False).strength

    # c's value at its settle hop (hop 1) is the a→c path only; the a→b→c contribution
    # arrives but is a longer path and does not change c's hop-1 expansion.
    act_c_hop1 = 1.0 * s_of(a, c) * DPH
    expected_f = act_c_hop1 * s_of(c, f) * DPH
    check(abs(res.activation[f] - expected_f) < 1e-9,
          f"f reflects ONLY the short path a→c→f, not a→b→c→f "
          f"(got {res.activation[f]:.6f}, expected {expected_f:.6f})")
    # c still ACCUMULATES the b→c contribution into its own value (just doesn't re-propagate)
    act_c_full = act_c_hop1 + (1.0 * s_of(a, b) * DPH) * s_of(b, c) * DPH
    check(abs(res.activation[c] - act_c_full) < 1e-9,
          "c's own value still SUMS the intra-layer contribution (accumulation is complete)")

    # Now the cross-PROCESS check: run the same spread under different hash seeds and
    # confirm f is byte-identical. This is the part that would actually catch the
    # per-process uuid-hash nondeterminism. We invoke fresh interpreters with
    # PYTHONHASHSEED set, so set ordering differs but the result must not.
    import subprocess, sys, os, textwrap
    # SPEC-0c §5.1: the payload serialises the BIT PATTERN. round(x, 12) is blind to
    # everything below 1e-12, and the difference this class of defect produces is 1 ULP.
    probe = textwrap.dedent('''
        import struct
        from psyche_store import SubstrateStore, Clock, NodeType
        from psyche_activation import spread_activation
        s = SubstrateStore(clock=Clock(simulated=True))
        a=s.add_node("a",NodeType.CONCEPT); b=s.add_node("b",NodeType.CONCEPT)
        c=s.add_node("c",NodeType.CONCEPT); f=s.add_node("f",NodeType.CONCEPT)
        for _ in range(50): s.traverse(a,b)
        for _ in range(10): s.traverse(a,c)
        for _ in range(50): s.traverse(b,c)
        for _ in range(40): s.traverse(c,f)
        r = spread_activation(s, a, energy=1.0, floor=0.0, hop_budget=10)
        print(struct.pack("<d", r.activation[f]).hex())
    ''')
    results = []
    for seed in ("0", "1", "3", "7", "42"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        out = subprocess.run([sys.executable, "-c", probe], cwd=os.path.dirname(__file__) or ".",
                             capture_output=True, text=True, env=env)
        results.append(out.stdout.strip())
    check(len(set(results)) == 1,
          f"f is identical across hash seeds 0/1/3/7/42 (got {set(results)}) "
          f"— no per-process nondeterminism from uuid set ordering")


def test_cycle_terminates():
    section("a cycle terminates (no infinite loop, no re-expansion blowup)")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    _well_worn(s, a, b)
    _well_worn(s, b, c)
    _well_worn(s, c, a)   # cycle a→b→c→a
    r = spread_activation(s, a)   # must return, not hang
    check(len(r.activation) >= 3, "all nodes in the cycle were reached")
    check(True, "spread over a cycle terminated")


def test_locality_hop_budget():
    section("locality: a long chain is cut off by the hop budget")
    s = SubstrateStore(clock=Clock(simulated=True))
    ids = [s.add_node(f"n{i}", NodeType.CONCEPT) for i in range(20)]
    for i in range(19):
        _well_worn(s, ids[i], ids[i + 1])
    r = spread_activation(s, ids[0], hop_budget=3, floor=0.0)
    # nothing beyond hop 3 should be settled
    max_hop = max(r.hops.values())
    check(max_hop <= 3, f"no node settled beyond hop budget (max hop = {max_hop})")
    check(ids[19] not in r.activation or r.activation.get(ids[19], 0) == 0,
          "far end of the chain never lit")


def test_floor_keeps_it_local():
    section("locality: the activation floor stops faint propagation")
    s = SubstrateStore(clock=Clock(simulated=True))
    ids = [s.add_node(f"n{i}", NodeType.CONCEPT) for i in range(20)]
    for i in range(19):
        s.traverse(ids[i], ids[i + 1])   # weak (dirt) chain
    r = spread_activation(s, ids[0], hop_budget=100)  # big budget; floor must stop it
    check(len(r.ranked()) < 19,
          "faint chain dies out at the floor well before the end")


def test_spread_is_pure_read():
    section("spreading activation mutates NOTHING in the store (pure read)")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    _well_worn(s, a, b, charge={"interest": 0.4})
    _well_worn(s, b, c)
    s.clock.advance(5.0)
    # snapshot canonical (un-decayed) stored state of every road
    before = {
        rid: (s.get_road(rid, apply_decay=False).strength,
              dict(s.get_road(rid, apply_decay=False).charges),
              s.get_road(rid, apply_decay=False).closed,
              s.get_road(rid, apply_decay=False).last_touched,
              s.get_road(rid, apply_decay=False).traversal_count)
        for rid in s.all_road_ids()
    }
    node_access_before = {n: s.get_node(n).access_count for n in s.all_node_ids()}
    # spread several times
    for _ in range(5):
        spread_activation(s, a)
    after = {
        rid: (s.get_road(rid, apply_decay=False).strength,
              dict(s.get_road(rid, apply_decay=False).charges),
              s.get_road(rid, apply_decay=False).closed,
              s.get_road(rid, apply_decay=False).last_touched,
              s.get_road(rid, apply_decay=False).traversal_count)
        for rid in s.all_road_ids()
    }
    node_access_after = {n: s.get_node(n).access_count for n in s.all_node_ids()}
    check(before == after, "no road changed (strength/charge/closed/touch/count)")
    check(node_access_before == node_access_after,
          "no node access_count changed — activation did not 'touch' nodes")


def test_closed_transmission_regime():
    section("closed-road policy: weak cue blocked, strong cue leaks (qualitative)")
    # Test the policy function directly at the regime boundaries — not magnitudes.
    weak = CLOSED_BREAKTHROUGH_THRESHOLD * 0.5
    strong = CLOSED_BREAKTHROUGH_THRESHOLD + (1.0 - CLOSED_BREAKTHROUGH_THRESHOLD) * 0.5
    check(closed_transmission(weak, None) == 0.0,
          "below threshold: a closed road transmits nothing (barrier holds)")
    check(0.0 < closed_transmission(strong, None) < 1.0,
          "above threshold: a closed road leaks an attenuated fraction (intrusion)")


def test_closed_road_blocks_weak_passes_strong():
    section("closed road in a spread: blocks a weak cue, leaks a strong one")
    # Build a→b strong, then close it. Then drive spread with low vs high seed energy.
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("coffee", NodeType.ENTITY)
    b = s.add_node("burnt tongue", NodeType.EVENT)
    _well_worn(s, a, b, n=30)                       # strong road first
    s.traverse(a, b, charge={"pain": -0.95})        # one-shot trauma → closed
    closed_road = s.find_road(a, b)
    check(s.get_road(closed_road, apply_decay=False).closed is True, "road is closed")

    # weak cue: seed energy below breakthrough threshold → b should not light
    weak = spread_activation(s, a, energy=CLOSED_BREAKTHROUGH_THRESHOLD * 0.5)
    check(b not in weak.activation or weak.activation.get(b, 0) == 0,
          "a weak cue does not reach the avoided memory (barrier holds)")
    check(len(weak.broke_through) == 0, "no breakthrough recorded for the weak cue")

    # strong cue: seed energy well above threshold → b lights via leak, breakthrough logged
    strong = spread_activation(s, a, energy=1.0)
    check(strong.activation.get(b, 0) > 0,
          "a strong cue reaches the avoided memory anyway (intrusive recall)")
    check(closed_road in strong.broke_through,
          "the breakthrough is observable (logged as an intrusive-recall event)")
    # and the leaked activation should be heavily attenuated vs an equivalent open road
    s2 = SubstrateStore(clock=Clock(simulated=True))
    x = s2.add_node("x", NodeType.ENTITY)
    y = s2.add_node("y", NodeType.EVENT)
    _well_worn(s2, x, y, n=30)   # same strength, left OPEN
    open_strong = spread_activation(s2, x, energy=1.0)
    check(strong.activation[b] < open_strong.activation[y],
          "leaked activation through a closed road is far weaker than through an open one")


def test_flow_records_what_transmitted():
    section("flow records which edges actually carried activation (and respects closure)")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.ENTITY)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.EVENT)
    _well_worn(s, a, b, n=30)               # open road, will carry flow
    _well_worn(s, a, c, n=30)
    s.traverse(a, c, charge={"pain": -0.95})  # closes a→c
    r_ab = s.find_road(a, b)
    r_ac = s.find_road(a, c)

    # weak cue: the closed road blocks, so a→c carries NO flow; a→b does
    weak = spread_activation(s, a, energy=CLOSED_BREAKTHROUGH_THRESHOLD * 0.5)
    check(r_ab in weak.flow and weak.flow[r_ab] > 0,
          "open road appears in flow with positive value")
    check(r_ac not in weak.flow,
          "a blocked closed road carries NO flow (binding must not bind across it)")

    # strong cue: the closed road leaks, so a→c now carries (attenuated) flow
    strong = spread_activation(s, a, energy=1.0)
    check(r_ac in strong.flow and strong.flow[r_ac] > 0,
          "a leaked closed road DOES appear in flow (the breakthrough transmitted)")
    check(strong.flow[r_ac] < strong.flow[r_ab],
          "leaked flow is weaker than open flow")


# ═════════════════════════════════════════════════════════════════════════════
# 0c — ORDER-INDEPENDENCE, SINGLE-READ EXPANSION, AND THE NON-FINITE GUARDS
#
# Everything below compares BIT PATTERNS. `round(x, 9)` is structurally blind to a
# 1-ULP difference, and 1 ULP is exactly what BUG-0b1 was; a determinism probe that
# rounds is not a determinism probe (SPEC-0c §5.1).
# ═════════════════════════════════════════════════════════════════════════════

import dataclasses
import functools
import itertools
import math
import operator
import struct

from psyche_activation import (
    DEFAULT_SEED_ENERGY, DEFAULT_DECAY_PER_HOP, DEFAULT_FLOOR,
)


def bits(x):
    """The exact IEEE-754 payload. Two floats are equal here only if every bit is."""
    return struct.pack("<d", x).hex()


def signature(result):
    """A bit-exact, uuid-free description of everything a spread returns."""
    return (
        tuple(sorted((n, bits(v)) for n, v in result.activation.items())),
        tuple(sorted(result.hops.items())),
        tuple(result.broke_through),
        tuple(sorted((r, bits(v)) for r, v in result.flow.items())),
    )


class PermutingStore:
    """A read-only proxy that hands `roads_from` back in a caller-chosen order.

    This tests the property DIRECTLY instead of sampling an axis that may or may not
    perturb it: if the engine is genuinely order-INDEPENDENT (and not merely
    order-pinned by the store), every permutation must produce identical bits.
    """

    def __init__(self, store, reorder):
        self._store = store
        self._reorder = reorder

    def __getattr__(self, name):          # everything else delegates untouched
        return getattr(self._store, name)

    def roads_from(self, node_id):
        return iter(self._reorder(list(self._store.roads_from(node_id))))


class RecordingStore:
    """A read-only proxy that records every `get_road` the engine performs, with the
    strength the engine actually saw. DEFECT-B was two reads of one road at two
    `clock.now()` instants, so the read COUNT is the structural fact to assert."""

    def __init__(self, store):
        self._store = store
        self.reads = []                   # [(road_id, strength_seen)]

    def __getattr__(self, name):
        return getattr(self._store, name)

    def get_road(self, road_id, apply_decay=True):
        road = self._store.get_road(road_id, apply_decay=apply_decay)
        self.reads.append((road_id, road.strength))
        return road


class StrengthInjectingStore:
    """A read-only proxy that hands the engine a road VIEW whose strength has been
    replaced by a caller-chosen value — including a non-finite one.

    This exists to drive the engine's `transmitted` non-finite guard from BELOW the
    public boundary. Since D-015, `energy` and `normalization_sigma` are both validated
    for finiteness at the boundary, so within the documented parameter domain (every
    multiplier <= 1) no public input can manufacture a non-finite `transmitted` any more.
    The guard stays as a BACKSTOP for the case it was written against: an internal value
    going non-finite while every caller-supplied parameter is finite and in range. This
    proxy IS that case — a road whose strength is not a number, reached through the
    store's ordinary read surface, with the caller's arguments untouched.

    It cannot disturb stored state: `get_road(apply_decay=True)` already returns a
    decayed COPY, and `dataclasses.replace` builds a further copy of that.
    """

    def __init__(self, store, strength):
        self._store = store
        self._strength = strength

    def __getattr__(self, name):          # everything else delegates untouched
        return getattr(self._store, name)

    def get_road(self, road_id, apply_decay=True):
        road = self._store.get_road(road_id, apply_decay=apply_decay)
        return dataclasses.replace(road, strength=self._strength)


class TickingClock(Clock):
    """A clock that ADVANCES on every read — deterministically, and by a large step.

    `Clock(simulated=False)` is the library default and is what DEFECT-B needed: with a
    frozen clock `dt <= 0` makes lazy decay a no-op, so reading a road twice is
    indistinguishable from reading it once, and every existing test froze the clock.
    This clock moves, so a double read is loud instead of a 1e-9 residue; `mark()` and
    `rewind()` let two runs be driven over the identical time sequence, which is what
    makes a byte-exact comparison meaningful on a moving clock at all.
    """

    def __init__(self, dt=1.0, start=0.0):
        super().__init__(simulated=False, start=start)
        self._dt = dt
        self._origin = start
        self.ticks = 0

    def now(self):
        t = self._origin + self.ticks * self._dt
        self.ticks += 1
        return t

    def mark(self):
        return self.ticks

    def rewind(self, mark):
        self.ticks = mark


# The SPEC-0c §1 reproduction, verbatim: five nodes, built by traverse() alone, at
# library defaults. in-degree(T) = 3, and three is the smallest number of terms whose
# addition can be non-associative (a + b == b + a is exact). Before 0c this graph gave
# two distinct results — 0.10145973529004966 and 0.10145973529004967 — across fresh
# processes. Nothing here is hand-placed: the counts drive traverse(), and every float
# in the test comes out of the store.
DEFECT_A_COUNTS = ((1, 2), (1, 3), (1, 9))


def _defect_a_store(counts=DEFECT_A_COUNTS):
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    S = s.add_node("S", NodeType.CONCEPT)
    T = s.add_node("T", NodeType.CONCEPT)
    for i, (a, b) in enumerate(counts):
        M = s.add_node(f"M{i}", NodeType.CONCEPT)
        for _ in range(a):
            s.traverse(S, M)
        for _ in range(b):
            s.traverse(M, T)
    return s, S, T


def test_convergent_accumulation_is_order_independent():
    section("0c: convergent accumulation is ORDER-INDEPENDENT, not merely order-pinned")
    s, S, T = _defect_a_store()
    seen = {}
    for perm in itertools.permutations(range(3)):
        def reorder(roads, p=perm):
            return [roads[i] for i in p] if len(roads) == 3 else roads
        r = spread_activation(PermutingStore(s, reorder), S)      # LIBRARY DEFAULTS
        seen.setdefault(bits(r.activation[T]), []).append(perm)

    # SENSITIVITY CONTROL, so this cannot pass vacuously: the three contributions the
    # engine itself recorded must be terms whose NAIVE sequential sum really does depend
    # on order. If they did not, the invariance above would be a fact about the input
    # rather than about the engine.
    base = spread_activation(s, S)
    contribs = [base.flow[rid] for rid in s.roads_into(T)]
    naive = {bits(functools.reduce(operator.add, p, 0.0))
             for p in itertools.permutations(contribs)}
    check(len(naive) > 1,
          f"the probe is SENSITIVE: naively summing the engine's own three contributions "
          f"in different orders gives {len(naive)} distinct bit patterns "
          f"(so the input genuinely breaks associativity)")
    check(len(seen) == 1,
          f"yet the ENGINE returns one bit pattern over all 3! out-road orders "
          f"(distinct = {len(seen)}) — order-independence, not order-pinning")
    print(f"    activation[T] = {next(iter(seen))} "
          f"= {struct.unpack('<d', bytes.fromhex(next(iter(seen))))[0]!r}")


def test_accumulation_is_the_exactly_rounded_sum_of_the_recorded_flows():
    section("0c: activation[T] is the EXACTLY ROUNDED sum of the flows into T")
    # `flow` is the engine's own per-edge record of what each road transmitted, and
    # `activation` is its accumulation of those same values. The invariant is that the
    # second is the exactly-rounded sum of the first — which a naive sequential add
    # satisfies only by luck (see the sensitivity control above, where it does not).
    s, S, T = _defect_a_store()
    # over EVERY out-road order, not one lucky draw: a single order can satisfy this by
    # coincidence (a naive fold agrees with fsum for some orders and not others), and a
    # test that passes by coincidence is the failure mode this project exists to avoid.
    mismatches = []
    incoming = None
    for perm in itertools.permutations(range(3)):
        def reorder(roads, p=perm):
            return [roads[i] for i in p] if len(roads) == 3 else roads
        r = spread_activation(PermutingStore(s, reorder), S)
        incoming = [r.flow[rid] for rid in s.roads_into(T) if rid in r.flow]
        if len(incoming) != 3:
            mismatches.append((perm, "in-degree", len(incoming)))
            continue
        if bits(r.activation[T]) != bits(math.fsum(incoming)):
            mismatches.append((perm, bits(r.activation[T]), bits(math.fsum(incoming))))
    check(not mismatches,
          f"activation[T] == fsum(the flows into T) to the bit, in all 3! out-road orders "
          f"(mismatches: {mismatches})")

    # NON-VACUITY, stated as a fact about the TERMS: these three contributions are terms
    # whose naive sequential summation genuinely depends on the order they arrive in. So
    # the invariant above is a fact about the engine, not a coincidence of the input.
    naive = {bits(functools.reduce(operator.add, p, 0.0))
             for p in itertools.permutations(incoming)}
    check(len(naive) > 1,
          f"non-vacuous: a naive left-fold of these same three contributions gives "
          f"{len(naive)} distinct bit patterns over 3! arrival orders")
    # Worth printing rather than asserting: in ONE particular order the naive fold happens
    # to agree with fsum. That is precisely why a single hand-picked order is not evidence.
    print(f"    naive fold in creation order = "
          f"{bits(functools.reduce(operator.add, incoming, 0.0))}, "
          f"fsum = {bits(math.fsum(incoming))}, distinct naive results over 3! = {len(naive)}")


def test_high_in_degree_fan_is_order_independent():
    section("0c: a 12-way convergent fan is order-independent under shuffled expansion")
    # in-degree 3 is the minimum; this is the load case. Driven by traverse() only.
    import random
    rng = random.Random(4711)
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    S = s.add_node("S", NodeType.CONCEPT)
    T = s.add_node("T", NodeType.CONCEPT)
    for i in range(12):
        M = s.add_node(f"M{i}", NodeType.CONCEPT)
        for _ in range(1 + (i % 3)):
            s.traverse(S, M)
        for _ in range(2 + i):
            s.traverse(M, T)
    seen = set()
    for trial in range(24):
        def reorder(roads, k=trial):
            rr = list(roads)
            random.Random(k).shuffle(rr)
            return rr
        for sigma in (None, 0.25, 1.0):
            r = spread_activation(PermutingStore(s, reorder), S,
                                  normalization_sigma=sigma, floor=0.0)
            seen.add((sigma, signature(r)))
    check(len(seen) == 3,
          f"24 shuffles x 3 sigmas collapse to exactly one signature per sigma "
          f"(distinct = {len(seen)}, expected 3)")


DEFECT_A_PROBE = '''
import struct
from psyche_store import SubstrateStore, Clock, NodeType
from psyche_activation import spread_activation
s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
S = s.add_node("S", NodeType.CONCEPT); T = s.add_node("T", NodeType.CONCEPT)
for i, (a, b) in enumerate(((1, 2), (1, 3), (1, 9))):
    M = s.add_node("M%d" % i, NodeType.CONCEPT)
    for _ in range(a): s.traverse(S, M)
    for _ in range(b): s.traverse(M, T)
r = spread_activation(s, S)                      # LIBRARY DEFAULTS, real store
print(struct.pack("<d", r.activation[T]).hex())
'''


def test_defect_a_reproduction_is_one_bit_pattern_across_fresh_processes():
    section("0c: the DEFECT-A reproduction yields ONE bit pattern in fresh processes")
    # uuid4 ids are freshly random in every process, so this varies even at a FIXED
    # PYTHONHASHSEED — which is why the seed axis never controlled this defect. Fresh
    # processes are the only axis that can perturb it, so fresh processes are what we run.
    import subprocess, sys, os
    cwd = os.path.dirname(__file__) or "."
    outs = []
    for seed in ("0", "1", "2", "3", "7", "42"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        for _ in range(5):                       # 6 seeds x 5 reps = 30 fresh processes
            rr = subprocess.run([sys.executable, "-c", DEFECT_A_PROBE], cwd=cwd,
                                capture_output=True, text=True, env=env)
            outs.append(rr.stdout.strip() if rr.returncode == 0 else f"ERROR {rr.stderr[-200:]}")
    distinct = sorted(set(outs))
    for d in distinct:
        print(f"    {d}  = {struct.unpack('<d', bytes.fromhex(d))[0]!r}  "
              f"({outs.count(d)} of {len(outs)})")
    check(len(distinct) == 1,
          f"one bit pattern over {len(outs)} fresh processes at library defaults "
          f"(distinct = {len(distinct)})")


def test_the_reproduction_agrees_across_every_interpreter_on_this_machine():
    section("0c: the same graph gives the same bits on every CPython on this machine")
    # Scoped honestly: this is a claim about INTERPRETERS on ONE machine, not about
    # platforms. The graph carries no charges and uses a frozen clock, so `math.exp`
    # (platform libm) is never entered; what is being compared is pure IEEE-754
    # arithmetic plus whatever summation semantics the interpreter supplies. CPython
    # 3.12 changed builtin sum() to Neumaier compensated summation, so a naive float
    # sum anywhere on this path would show up here and nowhere else in the suite.
    import subprocess, sys, os, shutil
    cwd = os.path.dirname(__file__) or "."
    interps = [p for p in ("python3.10", "python3.11", "python3.12", "python3.13",
                           "python3.14") if shutil.which(p)]
    # include the running interpreter too, but only if it is not already one of the named
    # five — resolved through realpath, so `python3.14` and the absolute path it resolves
    # to are not counted as two interpreters.
    _real = {os.path.realpath(shutil.which(p)) for p in interps}
    if os.path.realpath(sys.executable) not in _real:
        interps.append(sys.executable)
    outs = {}
    for py in interps:
        rr = subprocess.run([py, "-c", DEFECT_A_PROBE], cwd=cwd,
                            capture_output=True, text=True)
        outs[py] = rr.stdout.strip() if rr.returncode == 0 else f"ERROR {rr.stderr[-200:]}"
    for py, o in outs.items():
        print(f"    {os.path.basename(py):<12} {o}")
    check(len(set(outs.values())) == 1,
          f"identical bits on {len(outs)} interpreters (distinct = {len(set(outs.values()))})")


# ── DEFECT-B: one read per road per expansion, on a clock that moves ──────────

SIGMA_LADDER = (1e-12, 1e-3, 0.25, 1.0, 7.5, 1e3, 1e300)


def test_each_road_is_read_exactly_once_per_expansion():
    section("0c/DEFECT-B: each road is read exactly ONCE per expansion, at every sigma")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    S = s.add_node("S", NodeType.CONCEPT)
    for i in range(5):
        T = s.add_node(f"T{i}", NodeType.CONCEPT)
        _well_worn(s, S, T, n=4 + i)
    worst = []
    for sigma in (None,) + SIGMA_LADDER:
        rec = RecordingStore(s)
        r = spread_activation(rec, S, normalization_sigma=sigma, floor=0.0)
        counts = {}
        for rid, _ in rec.reads:
            counts[rid] = counts.get(rid, 0) + 1
        if set(counts.values()) != {1}:
            worst.append((sigma, sorted(counts.values())))
        # and each road therefore transmits at most once: the `flow.get(rid, 0.0) + ...`
        # defensive branch in the engine is DEAD under hop-layered single expansion.
        if any(v > 1 for v in counts.values()):
            worst.append((sigma, "flow"))
    check(not worst,
          f"exactly one get_road per road per expansion at sigma in "
          f"{(None,) + SIGMA_LADDER} (violations: {worst})")


def test_lone_out_road_factor_is_exactly_one_on_the_real_wall_clock():
    section("0c/DEFECT-B: a lone out-road is unattenuated on a MOVING clock (factor 1.0)")
    # SubstrateStore() with no clock argument is the library default: Clock(simulated=False),
    # the real wall clock. Every existing test froze the clock, which is exactly how this
    # stayed invisible. The expected value uses the strength THE ENGINE ITSELF READ
    # (captured by the proxy), so nothing here re-derives lazy decay — the assertion is
    # that no extra factor was applied, which is N-5 as written.
    bad = []
    for sigma in SIGMA_LADDER:
        s = SubstrateStore()                       # moving clock, library default
        A = s.add_node("A", NodeType.CONCEPT)
        B = s.add_node("B", NodeType.CONCEPT)
        _well_worn(s, A, B, n=6)
        rid = next(iter(s.roads_from(A)))
        rec = RecordingStore(s)
        r = spread_activation(rec, A, normalization_sigma=sigma, floor=0.0)
        reads = [st for (rr, st) in rec.reads if rr == rid]
        if len(reads) != 1:
            bad.append((sigma, f"{len(reads)} reads"))
            continue
        expected = DEFAULT_SEED_ENERGY * reads[0] * DEFAULT_DECAY_PER_HOP
        if bits(r.flow[rid]) != bits(expected):
            bad.append((sigma, bits(r.flow[rid]), bits(expected)))
    check(not bad,
          f"on the real wall clock a lone out-road transmits energy*strength*decay "
          f"exactly — factor 1.0, competing exactly 0.0 — at every sigma in "
          f"{SIGMA_LADDER} (deviations: {bad})")


def test_single_out_road_chain_is_byte_identical_on_a_ticking_clock():
    section("0c/DEFECT-B: a one-out-road chain is byte-identical on/off on a MOVING clock")
    # A clock that advances a full second on every read. Both runs are driven over the
    # IDENTICAL time sequence (rewind), which is only possible because the fixed engine
    # performs the same number of reads with normalization on and off — that equality of
    # read counts is itself DEFECT-B's absence, and before the fix the sigma run consumed
    # twice as many ticks and diverged for that reason as well.
    clk = TickingClock(dt=1.0)
    s = SubstrateStore(clock=clk)
    ids = [s.add_node(f"c{i}", NodeType.CONCEPT) for i in range(7)]
    for i in range(6):
        _well_worn(s, ids[i], ids[i + 1], n=2 + i)
    mark = clk.mark()
    base = signature(spread_activation(s, ids[0], normalization_sigma=None, floor=0.0))
    ticks_off = clk.mark() - mark
    bad = []
    ticks = {}
    for sigma in SIGMA_LADDER:
        clk.rewind(mark)
        got = signature(spread_activation(s, ids[0], normalization_sigma=sigma, floor=0.0))
        ticks[sigma] = clk.mark() - mark
        if got != base:
            bad.append(sigma)
    check(ticks_off > 0, f"the clock genuinely moved during the spread ({ticks_off} ticks)")
    check(all(v == ticks_off for v in ticks.values()),
          f"normalization on and off read the store the same number of times "
          f"({ticks_off} off, {sorted(set(ticks.values()))} on)")
    check(not bad,
          f"the chain is byte-identical with normalization on at every sigma, on a clock "
          f"that advances (deviating sigmas: {bad})")


# ── DEFECT-C: sigma validation, and the general non-finite guard ──────────────

def test_normalization_sigma_is_validated_at_the_boundary():
    section("0c/DEFECT-C: non-finite and non-positive sigma raise ValueError, naming it")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    S = s.add_node("S", NodeType.CONCEPT)
    for i in range(3):
        T = s.add_node(f"T{i}", NodeType.CONCEPT)
        _well_worn(s, S, T, n=5)
    rejected = [float("inf"), float("-inf"), float("nan"), 0.0, -0.0, -1.0, -1e-300]
    for bad in rejected:
        expect_raises(ValueError,
                      lambda b=bad: spread_activation(s, S, normalization_sigma=b),
                      f"sigma={bad!r} is rejected")
    # the message must NAME the offending value, or the caller cannot act on it
    named = 0
    for bad in rejected:
        try:
            spread_activation(s, S, normalization_sigma=bad)
        except ValueError as e:
            if repr(bad) in str(e):
                named += 1
    check(named == len(rejected),
          f"every rejection names the offending value ({named}/{len(rejected)})")
    # None stays neutral, and valid finite-positive sigma still works
    ok = True
    try:
        spread_activation(s, S, normalization_sigma=None)
        for good in SIGMA_LADDER:
            spread_activation(s, S, normalization_sigma=good)
    except Exception as e:
        ok = False
        print("   unexpected:", e)
    check(ok, f"None and every finite positive sigma in {SIGMA_LADDER} are accepted")


def test_non_finite_energy_is_refused_at_the_boundary():
    section("0c/DEFECT-C part 3 (D-015): non-finite ENERGY is refused at the boundary, "
            "on every graph shape")
    # WHY THIS IS A BOUNDARY CHECK AND NOT A GUARD. The engine seeds
    # `contributions = {seed_node: [energy]}`, so the SEED's own activation is unguarded on
    # EVERY graph, connected or not: the part-2 guard is on `transmitted`, which only ever
    # sees downstream values. A NaN seed therefore lands in the RETURNED activation map, is
    # consumed by psyche_field, accumulated into basins, and reaches Coalition.strength and
    # thence _competition_key — where every NaN comparison is False and the ordering
    # silently degrades. The isolated node below is the VISIBLE instance, not the risk.
    #
    # FINITENESS ONLY. The SIGN of energy is a separate question with a separate record
    # (D-014): negative energy is NOT rejected, and the assertions below hold the two apart
    # deliberately, so a later reader cannot mistake one ruling for the other.
    bad = [float("nan"), float("inf"), float("-inf")]

    # shape 1: an isolated seed — nothing transmits, so no guard can ever see the value
    iso = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    lone = iso.add_node("lone", NodeType.CONCEPT)
    # shape 2 and 3: a seed WITH out-roads, at hop_budget=0 (settles without expanding)
    # and at the default budget (expands normally)
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    A = s.add_node("A", NodeType.CONCEPT)
    B = s.add_node("B", NodeType.CONCEPT)
    _well_worn(s, A, B, n=6)
    shapes = [("isolated seed", lambda e: spread_activation(iso, lone, energy=e)),
              ("out-roads, hop_budget=0",
               lambda e: spread_activation(s, A, energy=e, hop_budget=0)),
              ("out-roads, default budget",
               lambda e: spread_activation(s, A, energy=e, floor=0.0))]
    for label, call in shapes:
        for e in bad:
            expect_raises(ValueError, lambda c=call, x=e: c(x),
                          f"energy={e!r} is refused on a {label}")
    # the message must NAME the offending value, or the caller cannot act on it
    named = 0
    for e in bad:
        try:
            spread_activation(iso, lone, energy=e)
        except ValueError as exc:
            if repr(e) in str(exc):
                named += 1
    check(named == len(bad),
          f"every energy rejection names the offending value ({named}/{len(bad)})")

    # THE RULING IS FINITENESS, NOT SIGN (D-014 stands, untouched). If any of these is
    # rejected, the wrong decision has been implemented.
    negatives = [-0.0, -1e-300, -1.0, -1e300]
    ok = []
    for e in negatives:
        try:
            r = spread_activation(s, A, energy=e, floor=-1e9)
            ok.append(bits(r.activation[A]))
        except Exception as exc:                                   # noqa: BLE001
            ok.append(f"REJECTED {type(exc).__name__}")
    check(all(not str(v).startswith("REJECTED") for v in ok),
          f"negative FINITE energy is still accepted — finiteness and sign are different "
          f"decisions with different records ({list(zip(negatives, ok))})")
    # and the value is carried through unaltered, except for the one documented
    # normalisation of -0.0 that test_activation_energy_has_no_signed_zero_by_design owns
    r_neg = spread_activation(s, A, energy=-1.0, floor=-1e9)
    rid = next(iter(s.roads_from(A)))
    check(bits(r_neg.activation[A]) == bits(-1.0),
          f"a negative seed energy is reported verbatim ({bits(r_neg.activation[A])})")
    check(bits(r_neg.flow[rid])
          == bits(-1.0 * s.get_road(rid).strength * DEFAULT_DECAY_PER_HOP),
          "and transmits through the ordinary rule with no special-casing")

    # LOOP-CLOSED: the energies the PREVIOUS STAGE actually produces must all be accepted.
    # perceive() is where spread_activation's energies come from in the assembled system
    # (via build_activation_field), so this drives the new boundary with input generated
    # upstream rather than with hand-picked values — and it is the check that the boundary
    # refuses nothing the system itself can generate.
    from psyche_perceive import perceive
    ls = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    words = ("coffee", "kitchen", "morning", "mug", "toast", "work", "code", "deadline")
    ids = [ls.add_node(w, NodeType.CONCEPT) for w in words]
    for i in range(len(ids) - 1):
        _well_worn(ls, ids[i], ids[i + 1], n=3 + i)
    percept = perceive(ls, "coffee kitchen morning mug toast work code deadline")
    energies = list(percept.sources.values())
    accepted = 0
    for src, e in percept.sources.items():
        try:
            spread_activation(ls, src, energy=e, floor=0.0)
            accepted += 1
        except Exception as exc:                                   # noqa: BLE001
            print(f"   unexpected: perceive() energy {e!r} rejected: {exc}")
    check(len(energies) >= 5,
          f"loop-closure is non-vacuous: perceive() produced {len(energies)} source "
          f"energies to drive the boundary with")
    check(accepted == len(energies),
          f"every energy the previous stage generated is accepted ({accepted}/"
          f"{len(energies)}) — the new boundary refuses nothing the system produces")


def test_non_finite_transmission_is_refused_not_silently_floored():
    section("0c/DEFECT-C part 2: the BACKSTOP guard — a non-finite transmitted value can "
            "never pass the floor test, driven from below the boundary")
    # WHY THIS TEST NOW INJECTS BELOW THE BOUNDARY (D-015, SPEC-0c §4). With `energy` and
    # `normalization_sigma` both finiteness-validated, and every multiplier in the
    # transmission chain <= 1 inside the documented parameter domain, no in-domain public
    # input can manufacture a non-finite `transmitted` any more. Driving this guard through
    # the public API — as the previous version of this test did with `energy=nan` — now
    # stops at the boundary and never reaches the guard, so it would silently stop being
    # evidence that the guard works while continuing to pass.
    #
    # The guard is NOT dead code and must not be deleted. It protects against a term that
    # manufactures a non-finite value from finite inputs, which is exactly the class it was
    # written for, and the injection below is that class in miniature.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    A = s.add_node("A", NodeType.CONCEPT)
    B = s.add_node("B", NodeType.CONCEPT)
    _well_worn(s, A, B, n=6)

    # (1) THE HAZARD IS REAL AND IS A PROPERTY OF THE COMPARISON. Stated first, so the
    # guard's necessity is asserted rather than assumed.
    check(not (float("nan") < DEFAULT_FLOOR) and not (float("inf") < DEFAULT_FLOOR),
          "`nan < floor` and `inf < floor` are both False, so absent the guard a "
          "non-finite transmitted value walks straight past the floor into the result")

    # (2) INJECTED BELOW THE BOUNDARY: every caller-supplied parameter is finite and in the
    # documented range; the non-finite value is manufactured inside the transmission chain.
    for injected in (float("inf"), float("-inf"), float("nan")):
        for sigma in (None, 1.0):
            expect_raises(
                ValueError,
                lambda v=injected, sg=sigma: spread_activation(
                    StrengthInjectingStore(s, v), A, normalization_sigma=sg),
                f"an internally non-finite road strength ({injected!r}, sigma={sigma}) is "
                f"refused by the backstop guard")
    # the guard's message must identify the road and the inputs, or it is not diagnostic
    try:
        spread_activation(StrengthInjectingStore(s, float("nan")), A)
    except ValueError as exc:
        rid = next(iter(s.roads_from(A)))
        check("non-finite transmitted" in str(exc) and rid in str(exc),
              f"the guard names both the condition and the road ({str(exc)[:60]}...)")

    # (3) NON-VACUITY / the guard keys on FINITENESS, not on the proxy. The same injection
    # with a finite (even out-of-range) strength passes straight through.
    r_finite = spread_activation(StrengthInjectingStore(s, 3.0), A, floor=0.0)
    check(math.isfinite(r_finite.activation[B]) and r_finite.activation[B] > 0,
          f"a FINITE injected strength is not refused ({r_finite.activation[B]!r}) — the "
          f"guard tests the value, not the proxy")

    # (4) THE ONE PUBLIC ROUTE THAT REMAINS, asserted so its status is on the record.
    # `decay_per_hop` is a multiplier the docstring documents as 0..1 but which is NOT
    # validated — D-015 scoped the boundary work to `energy` alone, and widening it is a
    # separate decision with its own record. Out-of-domain decay therefore still reaches
    # the guard, which is precisely the guard doing its job.
    for kwargs in ({"decay_per_hop": float("nan")}, {"decay_per_hop": float("inf")}):
        expect_raises(ValueError,
                      lambda k=kwargs: spread_activation(s, A, floor=0.0, **k),
                      f"non-finite transmission via {kwargs} is refused by the guard")

    # (5) THE ENERGY ROUTE NOW STOPS EARLIER, and the two refusals are distinguished
    # STRUCTURALLY rather than by matching the message text: the boundary refuses before
    # the engine has read a single road, the guard refuses only after it has read one.
    # This is what proves the test had to be re-based rather than left driving the guard
    # through the public API — where it would keep passing while testing nothing.
    reads_at_refusal = {}
    for label, kwargs in (("energy=nan", {"energy": float("nan")}),
                          ("energy=inf", {"energy": float("inf")}),
                          ("energy=-inf", {"energy": float("-inf")}),
                          ("decay=inf", {"decay_per_hop": float("inf")})):
        rec = RecordingStore(s)
        try:
            spread_activation(rec, A, floor=0.0, **kwargs)
        except ValueError:
            reads_at_refusal[label] = len(rec.reads)
    check(all(reads_at_refusal[k] == 0 for k in
              ("energy=nan", "energy=inf", "energy=-inf")),
          f"non-finite energy is refused at the BOUNDARY — before the engine reads any "
          f"road at all ({reads_at_refusal})")
    check(reads_at_refusal.get("decay=inf", 0) > 0,
          f"whereas the guard can only refuse after a road has been read and a value "
          f"computed ({reads_at_refusal}) — the two refusals are different code, so the "
          f"guard has to be driven from below the boundary")

    # (6) PURITY AND INTEGRITY ACROSS THE RAISING PATHS. A validation that raised after
    # partial work, or a guard that raised mid-expansion having written something, would
    # be a purity defect that only the failing path can show.
    def snap():
        rows = sorted(
            (rd.creation_seq, bits(rd.strength), bits(rd.last_touched), rd.closed,
             rd.traversal_count)
            for rd in (s.get_road(rid, apply_decay=False) for rid in s.all_road_ids()))
        nodes = sorted((s.get_node(n).creation_seq, s.get_node(n).content,
                        s.get_node(n).access_count) for n in s.all_node_ids())
        return (tuple(rows), tuple(nodes))

    before = snap()
    refused = 0
    calls = ([lambda x=e: spread_activation(s, A, energy=x, floor=0.0)
              for e in (float("nan"), float("inf"), float("-inf"))]
             + [lambda v=i: spread_activation(StrengthInjectingStore(s, v), A, floor=0.0)
                for i in (float("inf"), float("nan"))]
             + [lambda: spread_activation(s, A, decay_per_hop=float("inf"), floor=0.0)])
    for call in calls:
        try:
            call()
        except ValueError:
            refused += 1
    check(refused == len(calls) and snap() == before,
          f"all {refused}/{len(calls)} refused spreads (three at the boundary, three at "
          f"the guard) left the store bit-identical — a raising read is still a pure read")
    s.check_integrity()
    check(True, "check_integrity() clean after the refused spreads")

    # (7) and nothing non-finite ever reaches activation or flow on the ordinary path
    leaked = 0
    for sigma in (None,) + SIGMA_LADDER:
        r = spread_activation(s, A, normalization_sigma=sigma, floor=0.0)
        leaked += sum(1 for v in list(r.activation.values()) + list(r.flow.values())
                      if not math.isfinite(v))
    check(leaked == 0,
          f"no non-finite value in activation or flow on the ordinary path ({leaked} leaks)")


def test_known_limitation_extreme_energy_overflows_as_OverflowError_not_ValueError():
    section("0c KNOWN LIMITATION, asserted (SPEC-0c §2.8): extreme-but-FINITE energy "
            "overflows out of math.fsum as OverflowError, not as the engine's ValueError")
    # SPEC-0c §2.8 asked whether validating `energy` closes this, and if not, whether it
    # should be re-raised as the engine's own ValueError. Answers, asserted below rather
    # than described in prose:
    #
    #   1. IT IS STILL REACHABLE. 1e308 is a perfectly finite double, so the D-015
    #      boundary check passes it; the overflow happens in the REDUCTION of finite
    #      terms, which is a different event from a non-finite input.
    #   2. IT IS LEFT AS OverflowError, deliberately. The part-2 guard exists because a
    #      NaN is SILENT — it passes `transmitted < floor` and poisons the result with no
    #      exception. Nothing here is silent: the operation refuses, loudly and with the
    #      correct type (OverflowError is ArithmeticError; "this arithmetic result is too
    #      large" is what it means, and it is what math.exp and friends raise). Re-labelling
    #      an arithmetic overflow as a caller-input error would make the type LESS accurate,
    #      and it would put a try/except around the hot loop's reduction to do it. O-12's
    #      property — no non-finite value reaches `activation` or `flow` — is upheld either
    #      way, because a raising call returns nothing at all.
    #   3. THE COST, stated: OverflowError is NOT a subclass of ValueError, so a caller
    #      writing `except ValueError` to handle bad input will not catch this one. That is
    #      the limitation, it is asserted below, and a future decision to change it has to
    #      come back through this test.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    S = s.add_node("S", NodeType.CONCEPT)
    T = s.add_node("T", NodeType.CONCEPT)
    for i in range(12):
        M = s.add_node(f"M{i}", NodeType.CONCEPT)
        _well_worn(s, S, M, n=40)
        _well_worn(s, M, T, n=40)

    check(math.isfinite(1e308),
          "1e308 is a finite double, so the D-015 finiteness boundary does not reject it")
    ok = spread_activation(s, S, energy=1e307, decay_per_hop=1.0, floor=0.0)
    check(math.isfinite(ok.activation[T]),
          f"one decade lower every term AND the total are finite ({ok.activation[T]!r}) — "
          f"so the overflow below is about the sum, not about the input")

    raised = None
    try:
        spread_activation(s, S, energy=1e308, decay_per_hop=1.0, floor=0.0)
    except Exception as exc:                                       # noqa: BLE001
        raised = exc
    check(isinstance(raised, OverflowError),
          f"at energy=1e308 the fsum reduction raises OverflowError "
          f"(got {type(raised).__name__ if raised else None})")
    check(not isinstance(raised, ValueError),
          f"KNOWN LIMITATION, asserted: it is NOT the engine's own ValueError, so a caller "
          f"catching ValueError to handle bad input does not catch it ({raised!r})")

    # WHAT CHANGED AND WHY, derived from the store rather than asserted from memory: the
    # pre-0c engine accumulated these same terms naively, and a naive running total
    # SATURATES to inf where the exactly-rounded sum refuses. Refusing is the better of the
    # two, which is why the change is accepted rather than reverted.
    terms = []
    for rid in s.roads_into(T):
        road = s.get_road(rid)                            # M -> T
        up = s.get_road(s.find_road(S, road.source_id))   # S -> M
        terms.append(1e308 * up.strength * 1.0 * road.strength * 1.0)
    check(len(terms) == 12 and all(math.isfinite(t) for t in terms),
          f"all {len(terms)} incoming terms are individually finite "
          f"(max {max(terms):.3e}) — only their sum overflows")
    check(math.isinf(functools.reduce(operator.add, terms, 0.0)),
          "a naive running total of those same terms returns inf — the pre-0c behaviour")
    over = False
    try:
        math.fsum(terms)
    except OverflowError:
        over = True
    check(over,
          "and math.fsum refuses them, which is where the OverflowError comes from: the "
          "layer-boundary freeze, before any `transmitted` value exists for the guard to see")


# ── purity and the known limitation ──────────────────────────────────────────

def test_spread_is_still_a_pure_read_after_the_restructure():
    section("0c: the deferred-accumulation restructure is still a PURE read")
    s, S, T = _defect_a_store()

    def snap():
        rows = []
        for rid in s.all_road_ids():
            rd = s.get_road(rid, apply_decay=False)      # CANONICAL, not the decayed view
            rows.append((rd.creation_seq, bits(rd.strength), bits(rd.last_touched),
                         rd.closed, rd.traversal_count,
                         tuple(sorted((k, bits(v)) for k, v in rd.charges.items()))))
        rows.sort()
        nodes = sorted((s.get_node(n).creation_seq, s.get_node(n).content,
                        s.get_node(n).access_count) for n in s.all_node_ids())
        return (tuple(rows), tuple(nodes))

    before = snap()
    for sigma in (None,) + SIGMA_LADDER:
        spread_activation(s, S, normalization_sigma=sigma)
        spread_activation(s, S, normalization_sigma=sigma, floor=0.0, hop_budget=12)
    check(snap() == before,
          "no stored strength / charge / closure / traversal_count / last_touched / "
          "access_count changed across 16 spreads")
    s.check_integrity()
    check(True, "check_integrity() clean after the spreads")


def test_activation_energy_has_no_signed_zero_by_design():
    section("0c DESIGN DECISION (D-014): activation energy has no signed zero — "
            "-0.0 normalises to +0.0")
    # THE SEMANTICS THIS ASSERTS ARE OURS, not the standard library's. Activation is an
    # ENERGY: a magnitude with no direction, for which "negative zero" names nothing the
    # engine can act on. So the engine carries exactly one zero, and a caller who passes
    # -0.0 gets +0.0 back. That is the intended contract, and this test fails if the
    # intent is violated.
    #
    # It is stated this way deliberately. Phrasing it as "we agree with math.fsum's
    # treatment of -0.0" would turn a CPython implementation detail into this project's
    # specification: the test would then break if the standard library moved, for a reason
    # that has nothing to do with what Psyche intends. (D-014, SPEC-0c §2.6.)
    #
    # Recorded as an explicit assertion rather than a comment because it is the ONE input
    # at which "byte-identical at the neutral value" acquires an exception — only a
    # bit-pattern comparison can see it, and bit-pattern comparisons are exactly what the
    # 0c determinism probes perform.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    _well_worn(s, a, b, n=5)
    r = spread_activation(s, a, energy=-0.0, floor=-1.0)
    check(bits(r.activation[a]) == bits(0.0),
          f"energy=-0.0 is reported as +0.0 ({bits(r.activation[a])}), not as -0.0 "
          f"({bits(-0.0)}) — the engine carries one zero, by design")
    # ...and the normalisation is total, not just at the seed: a -0.0 seed and a +0.0
    # seed produce byte-identical results everywhere, so no downstream consumer can
    # observe a sign on zero energy.
    r_pos = spread_activation(s, a, energy=0.0, floor=-1.0)
    check(signature(r) == signature(r_pos),
          "a -0.0 seed and a +0.0 seed give byte-identical activation, flow, hops and "
          "breakthrough — the sign is not observable anywhere downstream")


def test_known_limitation_isomorphic_graphs_differ_in_output_ORDER():
    section("0c ASSERTED-NEGATIVE (known limitation): the guarantee is per construction "
            "program, NOT per isomorphism class")
    # SPEC-0c §1 scopes the claim to "a fixed store state", i.e. process runs of the SAME
    # construction program. Two stores holding the same LOGICAL graph, built by different
    # insertion sequences, are not covered — and here is a concrete witness. The float
    # VALUES coincide, but `activation` is insertion-ordered, so `ranked()` — whose sort
    # is stable — resolves an exact tie in construction order. A consumer that reads
    # ranked()[0] on a tie is reading the construction program, not the graph.
    #
    # This is asserted rather than described so that nobody can read the §1 guarantee as
    # isomorphism-invariance, and so that a future change that DOES make it invariant has
    # to come back through this test.
    def build(order):
        s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
        S = s.add_node("S", NodeType.CONCEPT)
        leaves = {name: s.add_node(name, NodeType.CONCEPT) for name in ("P", "Q")}
        for name in order:                       # SAME roads, different insertion order
            _well_worn(s, S, leaves[name], n=7)
        return s, S, leaves

    s1, S1, l1 = build(("P", "Q"))
    s2, S2, l2 = build(("Q", "P"))
    r1 = spread_activation(s1, S1, floor=0.0)
    r2 = spread_activation(s2, S2, floor=0.0)

    v1 = {s1.get_node(n).content: bits(v) for n, v in r1.activation.items()}
    v2 = {s2.get_node(n).content: bits(v) for n, v in r2.activation.items()}
    check(v1 == v2,
          "the two isomorphic graphs agree on every activation VALUE, bit for bit")
    check(v1["P"] == v1["Q"],
          "P and Q are an exact tie (the condition under which order becomes visible)")

    order1 = [s1.get_node(n).content for n, _ in r1.ranked()]
    order2 = [s2.get_node(n).content for n, _ in r2.ranked()]
    check(order1 != order2,
          f"KNOWN LIMITATION, asserted: ranked() order differs between isomorphic graphs "
          f"built in different insertion orders ({order1} vs {order2}). Determinism is "
          f"guaranteed per construction program, not per isomorphism class.")
    keys1 = [s1.get_node(n).content for n in r1.activation]
    keys2 = [s2.get_node(n).content for n in r2.activation]
    check(keys1 != keys2,
          f"and the activation dict's KEY order differs too ({keys1} vs {keys2}) — "
          f"the values are invariant here, the ordering of the mapping is not")


def run_all():
    print("=" * 70)
    print("  PSYCHE SPREADING ACTIVATION — TEST SUITE")
    print("=" * 70)
    for t in [
        test_seed_must_exist,
        test_isolated_seed_lights_only_itself,
        test_activation_attenuates_with_distance,
        test_stronger_road_carries_more,
        test_convergent_activation_sums,
        test_no_double_count_downstream_of_convergence,
        test_expansion_is_deterministic_under_edge_strength,
        test_determinism_with_same_hop_edge_adversarial,
        test_cycle_terminates,
        test_locality_hop_budget,
        test_floor_keeps_it_local,
        test_spread_is_pure_read,
        test_closed_transmission_regime,
        test_closed_road_blocks_weak_passes_strong,
        test_flow_records_what_transmitted,
        # 0c — order-independence, single-read expansion, non-finite guards
        test_convergent_accumulation_is_order_independent,
        test_accumulation_is_the_exactly_rounded_sum_of_the_recorded_flows,
        test_high_in_degree_fan_is_order_independent,
        test_defect_a_reproduction_is_one_bit_pattern_across_fresh_processes,
        test_the_reproduction_agrees_across_every_interpreter_on_this_machine,
        test_each_road_is_read_exactly_once_per_expansion,
        test_lone_out_road_factor_is_exactly_one_on_the_real_wall_clock,
        test_single_out_road_chain_is_byte_identical_on_a_ticking_clock,
        test_normalization_sigma_is_validated_at_the_boundary,
        test_non_finite_energy_is_refused_at_the_boundary,
        test_non_finite_transmission_is_refused_not_silently_floored,
        test_known_limitation_extreme_energy_overflows_as_OverflowError_not_ValueError,
        test_spread_is_still_a_pure_read_after_the_restructure,
        test_activation_energy_has_no_signed_zero_by_design,
        test_known_limitation_isomorphic_graphs_differ_in_output_ORDER,
    ]:
        t()
    print("\n" + "=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    print("=" * 70)
    return _failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run_all() else 1)
