"""
Test suite for the multi-source activation field and field-based coalition formation.

The ACCEPTANCE test here uses the ADVERSARIAL two-community input that defeated
single-seed segmentation — not a friendly graph. The whole point of the multi-source
reframe is that it recovers genuine community structure where single-seed could not,
so that is exactly the input the acceptance test must run on. Determinism is verified
across hash seeds in fresh interpreters, as established.

Run directly:
    python3 test_nous_field.py
"""

from nous_store import SubstrateStore, Clock, NodeType
from nous_field import build_activation_field, ActivationField
from nous_coalitions import form_coalitions_from_field

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


def _two_communities():
    """The adversarial input: two dense communities joined by a thin bridge.
    Returns (store, names-dict)."""
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    coffee = s.add_node("coffee", NodeType.ENTITY)
    warmth = s.add_node("warmth", NodeType.SENSATION)
    morning = s.add_node("morning", NodeType.CONCEPT)
    cozy = s.add_node("cozy", NodeType.CONCEPT)
    work = s.add_node("work", NodeType.CONCEPT)
    desk = s.add_node("desk", NodeType.ENTITY)
    deadline = s.add_node("deadline", NodeType.CONCEPT)
    stress = s.add_node("stress", NodeType.SENSATION)
    # warm community: dense internal links
    _worn(s, coffee, warmth); _worn(s, warmth, cozy); _worn(s, coffee, cozy)
    _worn(s, coffee, morning); _worn(s, morning, cozy)
    # work community: dense internal links
    _worn(s, work, desk); _worn(s, desk, deadline); _worn(s, work, deadline)
    _worn(s, deadline, stress); _worn(s, work, stress)
    # THIN bridge between communities
    _worn(s, coffee, work, n=3)
    return s, dict(coffee=coffee, warmth=warmth, morning=morning, cozy=cozy,
                   work=work, desk=desk, deadline=deadline, stress=stress)


# ─────────────────────────────────────────────────────────────────────────────

def test_field_sums_across_sources():
    section("field: total activation sums across sources at a shared node")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    shared = s.add_node("shared", NodeType.CONCEPT)
    _worn(s, a, shared); _worn(s, b, shared)
    field = build_activation_field(s, [a, b], energy=1.0)
    # shared is reached by both sources; its total must exceed either single contribution
    check(field.total[shared] > field.per_source[a].get(shared, 0),
          "shared node's total exceeds source a's contribution alone")
    check(field.total[shared] > field.per_source[b].get(shared, 0),
          "shared node's total exceeds source b's contribution alone")


def test_dominant_source_assignment():
    section("field: each node assigned to the source that activates it most")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    near_a = s.add_node("near_a", NodeType.CONCEPT)
    _worn(s, a, near_a, n=40)        # strongly tied to a
    _worn(s, b, near_a, n=2)         # weakly tied to b
    field = build_activation_field(s, [a, b], energy=1.0)
    check(field.dominant[near_a] == a,
          "a node more strongly activated by a is in a's basin")
    check(field.dominant[a] == a, "a source dominates itself")
    check(field.dominant[b] == b, "the other source dominates itself")


def test_acceptance_multisource_recovers_communities():
    section("ACCEPTANCE: multi-source recovers communities on the adversarial input")
    # This is THE test: the two-community-with-bridge graph that single-seed
    # segmentation could not handle. One source seeded in each community.
    s, n = _two_communities()
    field = build_activation_field(s, [n["coffee"], n["work"]], energy=1.0, hop_budget=8)

    warm = {n["coffee"], n["warmth"], n["morning"], n["cozy"]}
    work_c = {n["work"], n["desk"], n["deadline"], n["stress"]}
    coffee_basin = field.basin(n["coffee"])
    work_basin = field.basin(n["work"])
    check(coffee_basin == warm,
          f"coffee's basin is exactly the warm community "
          f"(got {sorted(s.get_node(x).content for x in coffee_basin)})")
    check(work_basin == work_c,
          f"work's basin is exactly the work community "
          f"(got {sorted(s.get_node(x).content for x in work_basin)})")

    # and the coalitions formed from the field are the two communities
    cs = form_coalitions_from_field(field, s)
    check(len(cs) == 2, f"two basins → two coalitions (got {len(cs)})")
    member_sets = [frozenset(c.members) for c in cs]
    check(frozenset(warm) in member_sets and frozenset(work_c) in member_sets,
          "the two coalitions are exactly the two communities")


def test_field_coalitions_are_pure_read():
    section("field-based coalition formation mutates NOTHING (pure read)")
    s, n = _two_communities()
    before = {
        rid: (s.get_road(rid, apply_decay=False).strength,
              s.get_road(rid, apply_decay=False).traversal_count)
        for rid in s.all_road_ids()
    }
    for _ in range(3):
        field = build_activation_field(s, [n["coffee"], n["work"]], energy=1.0)
        form_coalitions_from_field(field, s)
    after = {
        rid: (s.get_road(rid, apply_decay=False).strength,
              s.get_road(rid, apply_decay=False).traversal_count)
        for rid in s.all_road_ids()
    }
    check(before == after, "building the field and coalitions changed no road")


def test_intrusive_node_in_field_coalition():
    section("a breakthrough node marks its basin's coalition intrusive")
    # a third source whose only strong route to a node is a closed (leaky) road
    s = SubstrateStore(clock=Clock(simulated=True))
    safe = s.add_node("safe topic", NodeType.CONCEPT)
    neutral = s.add_node("neutral", NodeType.CONCEPT)
    _worn(s, safe, neutral, n=30)
    coffee = s.add_node("coffee", NodeType.ENTITY)
    burnt = s.add_node("burnt tongue", NodeType.EVENT)
    _worn(s, coffee, burnt, n=30)
    s.traverse(coffee, burnt, charge={"pain": -0.95})  # closes coffee→burnt
    # sources: safe-topic and coffee; coffee strongly cued so it breaks through
    field = build_activation_field(s, [safe, coffee], energy=1.0)
    check(len(field.broke_through) > 0, "a breakthrough occurred (precondition)")
    cs = form_coalitions_from_field(field, s)
    intruded = [c for c in cs if burnt in c.members]
    check(len(intruded) == 1 and intruded[0].intrusive is True,
          "the coalition containing the breakthrough node is marked intrusive")


def test_field_determinism_adversarial_across_hash_seeds():
    section("ADVERSARIAL determinism: field coalitions identical across hash seeds")
    import subprocess, sys, os, textwrap
    # SPEC-0c §5.1: BIT PATTERNS, never round(x, 9).
    probe = textwrap.dedent('''
        import struct
        def _b(x): return struct.pack("<d", x).hex()
        from nous_store import SubstrateStore, Clock, NodeType
        from nous_field import build_activation_field
        from nous_coalitions import form_coalitions_from_field
        s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
        def add(l, t=NodeType.CONCEPT): return s.add_node(l, t)
        coffee=add("coffee",NodeType.ENTITY); warmth=add("warmth",NodeType.SENSATION)
        morning=add("morning"); cozy=add("cozy")
        work=add("work"); desk=add("desk",NodeType.ENTITY); deadline=add("deadline")
        stress=add("stress",NodeType.SENSATION)
        def w(a,b,n):
            for _ in range(n): s.traverse(a,b)
        w(coffee,warmth,30); w(warmth,cozy,30); w(coffee,cozy,28); w(coffee,morning,26); w(morning,cozy,24)
        w(work,desk,30); w(desk,deadline,30); w(work,deadline,28); w(deadline,stress,26); w(work,stress,24)
        w(coffee,work,3)
        field = build_activation_field(s, [coffee, work], energy=1.0, hop_budget=8)
        cs = form_coalitions_from_field(field, s)
        out = []
        for c in cs:
            out.append((tuple(sorted(s.get_node(m).content for m in c.members)),
                        _b(c.strength),
                        s.get_node(c.representative()).content,
                        c.intrusive))
        print(repr(out))
    ''')
    outs = []
    cwd = os.path.dirname(__file__) or "."
    for seed in ("0", "1", "2", "3", "7", "42", "123", "999"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        r = subprocess.run([sys.executable, "-c", probe], cwd=cwd,
                           capture_output=True, text=True, env=env)
        if r.returncode != 0:
            print("  (subprocess error)\n", r.stderr)
        outs.append(r.stdout.strip())
    check(len(set(outs)) == 1,
          f"field coalition structure identical across 8 hash seeds "
          f"(distinct outputs: {len(set(outs))})")


def run_all():
    print("=" * 70)
    print("  NOUS MULTI-SOURCE FIELD + FIELD COALITIONS — TEST SUITE")
    print("=" * 70)
    for t in [
        test_field_sums_across_sources,
        test_dominant_source_assignment,
        test_acceptance_multisource_recovers_communities,
        test_field_coalitions_are_pure_read,
        test_intrusive_node_in_field_coalition,
        test_field_determinism_adversarial_across_hash_seeds,
    ]:
        t()
    print("\n" + "=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    print("=" * 70)
    return _failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run_all() else 1)
