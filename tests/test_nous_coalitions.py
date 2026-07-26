"""
Test suite for Nous coalition formation.

Per the method established over the last rounds, the ADVERSARIAL determinism test
ships with this first commit — clustering is the classic home of hidden
order-dependence, so the claim "output is a deterministic function of the activation
result" is tested on inputs built to break it (many co-activated nodes with
tie-strength bindings, across multiple hash seeds in fresh interpreters), not on a
friendly graph under one run.

Run directly:
    python3 test_nous_coalitions.py
"""

from nous_store import SubstrateStore, Clock, NodeType
from nous_activation import spread_activation, CLOSED_BREAKTHROUGH_THRESHOLD
from nous_coalitions import form_coalitions, Coalition, DEFAULT_COHERENCE_FLOOR

_passed = 0
_failed = 0

def check(cond, msg):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {msg}")

def section(name):
    print(f"\n{name}")

def _worn(s, a, b, n=30, ch=None):
    for _ in range(n):
        s.traverse(a, b, charge=ch)


# ─────────────────────────────────────────────────────────────────────────────

def test_empty_when_nothing_co_activated():
    section("no coalitions when nothing clears the coherence floor")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("alone", NodeType.CONCEPT)
    res = spread_activation(s, a)
    # seed alone, with a high floor nothing (not even seed) clears → no coalitions
    cs = form_coalitions(s, res, coherence_floor=2.0)
    check(cs == [], "nothing above an impossibly high floor → no coalitions")


def test_seed_neighborhood_forms_one_coalition():
    section("a connected co-activated neighborhood forms a single coalition")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    _worn(s, a, b); _worn(s, b, c)
    res = spread_activation(s, a)
    cs = form_coalitions(s, res)
    check(len(cs) == 1, "one connected component → one coalition")
    check(set(cs[0].members) >= {a, b}, "the coalition contains the connected members")


def test_disconnected_groups_form_separate_coalitions():
    section("disconnected co-activated groups form separate coalitions")
    # Two separate chains off the seed that DON'T connect to each other:
    #   seed → x → y   (one branch)
    #   seed → p → q   (another branch)
    # x-y and p-q are each connected to seed, so all in one component via seed.
    # To get TWO components we need two co-activated islands. Build the seed linking
    # to two branches but then test the SUBGRAPH structure by activating from a node
    # that reaches both only weakly — simpler: build two components by seeding twice.
    s = SubstrateStore(clock=Clock(simulated=True))
    # component 1
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    _worn(s, a, b)
    # component 2 (entirely unconnected to component 1)
    p = s.add_node("p", NodeType.CONCEPT)
    q = s.add_node("q", NodeType.CONCEPT)
    _worn(s, p, q)
    # Craft an activation result lighting BOTH islands, with FLOW on each island's
    # internal edge (equal flow, so the relative cut keeps both). The two islands share
    # no edge, so they must form two coalitions.
    from nous_activation import ActivationResult
    r_ab = s.find_road(a, b)
    r_pq = s.find_road(p, q)
    res = ActivationResult(
        seed=a,
        activation={a: 1.0, b: 0.5, p: 0.9, q: 0.4},
        hops={a: 0, b: 1, p: 0, q: 1},
        broke_through=[],
        flow={r_ab: 0.5, r_pq: 0.5},
    )
    cs = form_coalitions(s, res)
    check(len(cs) == 2, "two disconnected co-activated islands → two coalitions")
    # strongest first: {a,b} sums to 1.5, {p,q} sums to 1.3 → a-coalition first
    check(cs[0].strength >= cs[1].strength, "coalitions sorted strongest-first")
    members_sets = [frozenset(c.members) for c in cs]
    check(frozenset({a, b}) in members_sets and frozenset({p, q}) in members_sets,
          "each island is its own coalition")


def test_unlinked_coactivated_nodes_do_not_bind():
    section("co-activated but UNLINKED nodes do not share a coalition")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)  # no road between a and b
    from nous_activation import ActivationResult
    res = ActivationResult(
        seed=a, activation={a: 1.0, b: 1.0}, hops={a: 0, b: 0}, broke_through=[])
    cs = form_coalitions(s, res)
    check(len(cs) == 2, "two unlinked co-activated nodes → two separate coalitions")


def test_strength_is_sum_of_member_activation():
    section("coalition strength is the sum of member activations")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    _worn(s, a, b)
    from nous_activation import ActivationResult
    r_ab = s.find_road(a, b)
    res = ActivationResult(
        seed=a, activation={a: 0.7, b: 0.4}, hops={a: 0, b: 1}, broke_through=[],
        flow={r_ab: 0.4})   # the edge carried flow → a and b bind into one coalition
    cs = form_coalitions(s, res)
    check(len(cs) == 1 and abs(cs[0].strength - 1.1) < 1e-9,
          "strength = 0.7 + 0.4 = 1.1")


def test_intrusive_node_is_marked():
    section("a breakthrough-reached node marks its coalition intrusive")
    # coffee → burnt tongue, strong then closed by trauma; a strong cue leaks across.
    s = SubstrateStore(clock=Clock(simulated=True))
    coffee = s.add_node("coffee", NodeType.ENTITY)
    burnt = s.add_node("burnt tongue", NodeType.EVENT)
    _worn(s, coffee, burnt, n=30)
    s.traverse(coffee, burnt, charge={"pain": -0.95})  # closes the road
    res = spread_activation(s, coffee, energy=1.0)
    check(len(res.broke_through) > 0, "the spread recorded a breakthrough (precondition)")
    cs = form_coalitions(s, res)
    # find the coalition containing burnt tongue
    intruded = [c for c in cs if burnt in c.members]
    check(len(intruded) == 1, "burnt tongue landed in a coalition")
    check(intruded[0].intrusive is True,
          "the coalition containing the breakthrough node is marked intrusive")
    check(burnt in intruded[0].breakthrough_members,
          "the breakthrough node is recorded in breakthrough_members")


def test_non_intrusive_coalition_not_marked():
    section("an ordinary coalition is not marked intrusive")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    _worn(s, a, b)
    res = spread_activation(s, a)
    cs = form_coalitions(s, res)
    check(all(c.intrusive is False for c in cs),
          "no breakthrough anywhere → no coalition marked intrusive")


def test_representative_is_most_active_deterministically():
    section("coalition representative is the most-active member, deterministically")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    _worn(s, a, b); _worn(s, a, c)
    from nous_activation import ActivationResult
    r_ab = s.find_road(a, b); r_ac = s.find_road(a, c)
    res = ActivationResult(
        seed=a, activation={a: 0.9, b: 0.5, c: 0.3}, hops={a: 0, b: 1, c: 1},
        broke_through=[], flow={r_ab: 0.5, r_ac: 0.5})  # both edges bind → one coalition
    cs = form_coalitions(s, res)
    check(cs[0].representative() == a, "the most-active node represents the coalition")


def test_coalition_formation_is_pure_read():
    section("coalition formation mutates NOTHING in the store (pure read)")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    _worn(s, a, b, ch={"interest": 0.4}); _worn(s, b, c)
    res = spread_activation(s, a)
    before = {
        rid: (s.get_road(rid, apply_decay=False).strength,
              dict(s.get_road(rid, apply_decay=False).charges),
              s.get_road(rid, apply_decay=False).closed,
              s.get_road(rid, apply_decay=False).traversal_count)
        for rid in s.all_road_ids()
    }
    for _ in range(5):
        form_coalitions(s, res)
    after = {
        rid: (s.get_road(rid, apply_decay=False).strength,
              dict(s.get_road(rid, apply_decay=False).charges),
              s.get_road(rid, apply_decay=False).closed,
              s.get_road(rid, apply_decay=False).traversal_count)
        for rid in s.all_road_ids()
    }
    check(before == after, "five rounds of coalition formation changed no road")


def test_determinism_adversarial_across_hash_seeds():
    section("ADVERSARIAL determinism: clustering identical across hash seeds")
    # Clustering's nondeterminism seams are seed-choice, merge order, and tie-breaks
    # over hash-randomized set iteration. Build an input designed to stress all three:
    # a RING of co-activated nodes (every node linked to two neighbors, so component
    # discovery has many equally-valid traversal orders) PLUS several tie-strength
    # members (equal activation, so any sort that leaks set order would diverge). Then
    # run in fresh interpreters under different PYTHONHASHSEED values and assert the
    # full coalition structure — partition, strengths, ordering, representatives — is
    # byte-identical. This is the test that catches the whole family proactively.
    import subprocess, sys, os, textwrap
    # SPEC-0c §5.1: the payload serialises BIT PATTERNS, never round(x, 9) — a rounded
    # determinism probe is structurally blind to the 1-ULP class BUG-0b1 was.
    probe = textwrap.dedent('''
        import struct
        def _b(x): return struct.pack("<d", x).hex()
        from nous_store import SubstrateStore, Clock, NodeType
        from nous_activation import ActivationResult
        from nous_coalitions import form_coalitions
        s = SubstrateStore(clock=Clock(simulated=True))
        # a ring n0..n5, each linked to the next, last back to first
        ids = [s.add_node("n%d" % i, NodeType.CONCEPT) for i in range(6)]
        for i in range(6):
            for _ in range(20):
                s.traverse(ids[i], ids[(i + 1) % 6])
        # plus two unconnected tie-strength singletons elsewhere
        x = s.add_node("x", NodeType.CONCEPT)
        y = s.add_node("y", NodeType.CONCEPT)
        # all ring nodes equal activation (ties everywhere); x and y equal to each other
        act = {nid: 0.5 for nid in ids}
        act[x] = 0.5
        act[y] = 0.5
        res = ActivationResult(seed=ids[0], activation=act,
                               hops={nid: 0 for nid in act}, broke_through=[])
        cs = form_coalitions(s, res)
        # Serialize the FULL structure by STABLE keys (content + creation_seq), NOT by
        # uuid — uuids are regenerated per process, so a uuid-based serialization would
        # show spurious differences even if the coalition structure were identical.
        # We want to measure whether the STRUCTURE is the same, by stable identity.
        out = []
        for c in cs:
            members_by_content = tuple(sorted(s.get_node(m).content for m in c.members))
            rep_content = s.get_node(c.representative()).content
            out.append((members_by_content, _b(c.strength), rep_content, c.intrusive))
        print(repr(out))
    ''')
    outputs = []
    cwd = os.path.dirname(__file__) or "."
    for seed in ("0", "1", "2", "3", "7", "42", "123", "999"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        r = subprocess.run([sys.executable, "-c", probe], cwd=cwd,
                           capture_output=True, text=True, env=env)
        if r.returncode != 0:
            print("  (subprocess error)\n", r.stderr)
        outputs.append(r.stdout.strip())
    check(len(set(outputs)) == 1,
          f"coalition structure identical across 8 hash seeds "
          f"(distinct outputs: {len(set(outputs))})")


def test_single_seed_spread_yields_multiple_coalitions():
    section("DECISIVE: a real single-seed spread subdivides into MORE THAN ONE coalition")
    # This is the property Finding 1 proved connectivity-binding could never satisfy:
    # the workspace competition downstream needs more than one contestant, and a
    # seed-rooted spread's co-activated subgraph is connected by construction. Flow-based
    # segmentation must cut the connected region into multiple coalitions from a REAL
    # spread (not a hand-built ActivationResult). Two tight clusters joined by a thin
    # bridge, seeded from inside one cluster.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    coffee = s.add_node("coffee", NodeType.ENTITY)
    warmth = s.add_node("warmth", NodeType.SENSATION)
    cozy = s.add_node("cozy", NodeType.CONCEPT)
    work = s.add_node("work", NodeType.CONCEPT)
    desk = s.add_node("desk", NodeType.ENTITY)
    deadline = s.add_node("deadline", NodeType.CONCEPT)
    for _ in range(30):
        s.traverse(coffee, warmth); s.traverse(warmth, cozy); s.traverse(coffee, cozy)
        s.traverse(work, desk); s.traverse(desk, deadline); s.traverse(work, deadline)
    for _ in range(3):
        s.traverse(coffee, work)   # thin bridge between the clusters

    res = spread_activation(s, coffee, energy=1.0, hop_budget=8)
    cs = form_coalitions(s, res)
    check(len(cs) > 1,
          f"flow-based binding yields >1 coalition on a real single-seed spread "
          f"(got {len(cs)}) — the property the whole competition depends on")
    # the tightly-linked warm core should stay together in one coalition
    warm_coal = [c for c in cs if coffee in c.members][0]
    check(warmth in warm_coal.members and cozy in warm_coal.members,
          "the tight warm cluster stays bound together")


def test_binding_respects_closure():
    section("binding respects closure: a blocked road does NOT bind two nodes")
    # Two nodes joined ONLY by a closed, blocked (no-breakthrough) road. The mind walled
    # this connection off; binding must not merge them. With flow-based binding this is
    # automatic: a blocked road carries no flow, so it never appears as a binding edge.
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.ENTITY)
    b = s.add_node("b", NodeType.EVENT)
    for _ in range(30):
        s.traverse(a, b)
    s.traverse(a, b, charge={"pain": -0.95})  # closes a→b

    # weak cue: the closed road blocks; a reaches b not at all → b not even co-activated,
    # OR if we force both active via a separate path, they still must not bind via a→b.
    res = spread_activation(s, a, energy=CLOSED_BREAKTHROUGH_THRESHOLD * 0.5)
    cs = form_coalitions(s, res)
    # a and b must not be in the same coalition through the blocked road
    same = any(a in c.members and b in c.members for c in cs)
    check(not same,
          "a and b are NOT bound into one coalition across a blocked, no-flow road")


def run_all():
    print("=" * 70)
    print("  NOUS COALITION FORMATION — TEST SUITE")
    print("=" * 70)
    for t in [
        test_empty_when_nothing_co_activated,
        test_seed_neighborhood_forms_one_coalition,
        test_disconnected_groups_form_separate_coalitions,
        test_unlinked_coactivated_nodes_do_not_bind,
        test_strength_is_sum_of_member_activation,
        test_single_seed_spread_yields_multiple_coalitions,
        test_binding_respects_closure,
        test_intrusive_node_is_marked,
        test_non_intrusive_coalition_not_marked,
        test_representative_is_most_active_deterministically,
        test_coalition_formation_is_pure_read,
        test_determinism_adversarial_across_hash_seeds,
    ]:
        t()
    print("\n" + "=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    print("=" * 70)
    return _failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run_all() else 1)
