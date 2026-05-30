"""
Test suite for Nous spreading activation.

Pins the QUALITATIVE behavior, not specific magnitudes (the constants are
uncalibrated and will change). Run directly:
    python3 test_nous_activation.py
"""

from nous_store import SubstrateStore, Clock, NodeType, NotFound
from nous_activation import (
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
    from nous_activation import DEFAULT_DECAY_PER_HOP as DPH
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
    from nous_activation import DEFAULT_DECAY_PER_HOP as DPH

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
    from nous_activation import DEFAULT_DECAY_PER_HOP as DPH

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
    probe = textwrap.dedent('''
        from nous_store import SubstrateStore, Clock, NodeType
        from nous_activation import spread_activation
        s = SubstrateStore(clock=Clock(simulated=True))
        a=s.add_node("a",NodeType.CONCEPT); b=s.add_node("b",NodeType.CONCEPT)
        c=s.add_node("c",NodeType.CONCEPT); f=s.add_node("f",NodeType.CONCEPT)
        for _ in range(50): s.traverse(a,b)
        for _ in range(10): s.traverse(a,c)
        for _ in range(50): s.traverse(b,c)
        for _ in range(40): s.traverse(c,f)
        r = spread_activation(s, a, energy=1.0, floor=0.0, hop_budget=10)
        print(repr(round(r.activation[f], 12)))
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


def run_all():
    print("=" * 70)
    print("  NOUS SPREADING ACTIVATION — TEST SUITE")
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
    ]:
        t()
    print("\n" + "=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    print("=" * 70)
    return _failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run_all() else 1)
