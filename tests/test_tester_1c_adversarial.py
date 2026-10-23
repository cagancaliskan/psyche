"""
INDEPENDENT ADVERSARIAL TEST SUITE for step 1c (source-clustering).

Author: tester (independent adversary). These tests are written from scratch against the
spec's acceptance PROPERTIES, NOT adapted from the builder's suite. The goal is to break
the mechanism, expose happy-path bias, and prove the §6.1 acceptance holds (or does not)
through the closed loop on system-generated input.

What this verifies (mechanism only — never meaning):
  P1  §6.1 acceptance LOOP-CLOSED on the spec input: merge + no-stranding through think().
  P1b Mechanism-dependence: a HAND-ASSIGNED grouping would NOT satisfy the property by
      construction (the property genuinely depends on the substrate's grouping).
  P2  Cross-process determinism across >=6 PYTHONHASHSEED values (our OWN probe).
  P3  Integrity unchanged before/after clustering, including adversarial graphs.
  P4  Read-purity: strengths AND traversal counts unchanged after repeated passes.
  P5  Scale-invariance under tiny/huge adversarial constants.
  P6  A1 purity (anti-circularity): clustering output cannot be changed by touching the
      field; it depends only on perception.sources + graph state.
  P7  Edge cases: 0 sources, 1 source, source-not-in-store, all-zero proximity, ties in
      energy AND creation_seq, single-link chaining, self-loops, duplicate content,
      high-degree fan nodes, closed/traumatic roads.
  P8  Loop-closure generalization of no-stranding: drive think() on a SYSTEM-GENERATED
      multi-cluster utterance and check whether an isolated perceived source strands.
      (This probes beyond the single spec input; a failure here is reported as a
      generalization gap relative to the literal §6.1 scope, with the exact input.)

Run directly:
    PYTHONPATH=<repo>/src python3 tests/test_tester_1c_adversarial.py
"""

import os
import sys
import subprocess
import textwrap

from psyche_store import SubstrateStore, Clock, NodeType
from psyche_perceive import perceive, think
from psyche_field import build_activation_field
from psyche_coalitions import form_coalitions_from_field
from psyche_source_clustering import (
    cluster_sources, SourceClustering, SourceGroup,
    DEFAULT_PROXIMITY_FRACTION, _pair_proximity,
)

_passed = 0
_failed = 0
_fail_msgs = []


def check(cond, msg):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        _fail_msgs.append(msg)
        print(f"  FAIL: {msg}")


def section(name):
    print(f"\n{name}")


def _worn(s, a, b, n=30):
    for _ in range(n):
        s.traverse(a, b)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures — rebuilt independently (NOT imported from the builder's suite)
# ─────────────────────────────────────────────────────────────────────────────

def _small_mind():
    """Rebuilt independently to match the spec's _small_mind: two loose domains with a
    coffee->work bridge (n=8). Identical topology to the acceptance fixture so we exercise
    1c on the exact graph the closed loop surfaced the bug on."""
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    coffee = s.add_node("coffee", NodeType.ENTITY)
    warmth = s.add_node("warmth", NodeType.SENSATION)
    morning = s.add_node("morning routine", NodeType.CONCEPT)
    cozy = s.add_node("cozy feeling", NodeType.CONCEPT)
    kitchen = s.add_node("kitchen", NodeType.ENTITY)
    work = s.add_node("work", NodeType.CONCEPT)
    desk = s.add_node("desk", NodeType.ENTITY)
    deadline = s.add_node("deadline pressure", NodeType.CONCEPT)
    code = s.add_node("writing code", NodeType.CONCEPT)
    _worn(s, coffee, warmth); _worn(s, coffee, morning); _worn(s, morning, cozy)
    _worn(s, coffee, kitchen); _worn(s, kitchen, morning)
    _worn(s, work, desk); _worn(s, work, deadline); _worn(s, work, code); _worn(s, desk, code)
    _worn(s, coffee, work, n=8)
    return s, dict(coffee=coffee, warmth=warmth, morning=morning, cozy=cozy,
                   kitchen=kitchen, work=work, desk=desk, deadline=deadline, code=code)


def _snapshot_roads(s):
    """Canonical (decay-free) strength + traversal_count for every road, by ROAD ID."""
    return {rid: (s.get_road(rid, apply_decay=False).strength,
                  s.get_road(rid, apply_decay=False).traversal_count)
            for rid in s.all_road_ids()}


def _snapshot_full(s):
    """A deeper snapshot: roads (strength/charges/closed/traversal) + node access stats."""
    roads = {}
    for rid in s.all_road_ids():
        r = s.get_road(rid, apply_decay=False)
        roads[rid] = (round(r.strength, 12), tuple(sorted(r.charges.items())),
                      r.closed, r.traversal_count, r.last_touched)
    nodes = {}
    for nid in s.all_node_ids():
        nd = s.get_node(nid)
        nodes[nid] = (nd.access_count, nd.last_accessed)
    return roads, nodes


def _partition_by_content(s, clustering):
    """Serialize a clustering by STABLE keys (content), never uuids."""
    out = []
    for g in clustering.groups:
        members = tuple(sorted(s.get_node(m).content for m in g.members))
        rep = s.get_node(g.representative).content
        seed = round(clustering.group_seeds[g.representative], 9)
        out.append((members, rep, seed))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# P1 — §6.1 acceptance, loop-closed on the spec input
# ─────────────────────────────────────────────────────────────────────────────

def test_P1_acceptance_merge_and_no_stranding_loop_closed():
    section("P1 §6.1 LOOP-CLOSED: merge(coffee/kitchen/morning) + no-stranding via think()")
    s, n = _small_mind()
    # sources are produced by perceive() from TEXT inside think() — never hand-placed.
    r = think(s, "coffee in the kitchen this morning")
    perceived = set(r.perception.sources)

    # precondition: the real input genuinely named the three warm sources
    check({n["coffee"], n["kitchen"], n["morning"]} <= perceived,
          "precondition: perceive() lit coffee, kitchen, morning from the text")

    # (a) MERGE: the three same-domain sources land in exactly ONE group together
    warm = {n["coffee"], n["kitchen"], n["morning"]}
    groups_touching_warm = [g for g in r.clustering.groups if warm & set(g.members)]
    check(len(groups_touching_warm) == 1,
          f"(a) merge: the three warm sources occupy ONE group "
          f"(touched {len(groups_touching_warm)})")
    if groups_touching_warm:
        check(warm <= set(groups_touching_warm[0].members),
              "(a) merge: all three warm sources are members of that single group")

    # (b) NO STRANDING: no perceived source ends up as a singleton basin/coalition
    singleton_coalitions = [c for c in r.coalitions if c.size() == 1]
    stranded = [c for c in singleton_coalitions if (set(c.members) & perceived)]
    check(len(stranded) == 0,
          f"(b) no-stranding: no perceived source is a singleton coalition "
          f"(stranded={len(stranded)})")


def test_P1b_hand_assigned_grouping_would_NOT_satisfy_merge():
    section("P1b mechanism-dependence: a HAND-ASSIGNED (everyone-singleton) grouping FAILS "
            "the merge property — so the property is not trivially true")
    # The acceptance property must DEPEND on the substrate's grouping. We construct the
    # null grouping a hand-encoded answer might use (every source its own group, the pre-1c
    # state) and confirm it does NOT satisfy merge — proving P1 is load-bearing, not
    # vacuously true regardless of mechanism.
    s, n = _small_mind()
    p = perceive(s, "coffee in the kitchen this morning")
    warm = {n["coffee"], n["kitchen"], n["morning"]}

    # NULL "grouping": every perceived source is its own singleton group.
    null_groups = [{src} for src in p.sources]
    touched = [grp for grp in null_groups if warm & grp]
    check(len(touched) == 3,
          "the everyone-singleton grouping touches THREE groups with the warm set — "
          "i.e. it FAILS merge; the real mechanism is required to pass P1")

    # And the real mechanism passes where the null grouping fails (sanity, same input).
    real = cluster_sources(s, p.sources)
    real_touched = [g for g in real.groups if warm & set(g.members)]
    check(len(real_touched) == 1,
          "the real substrate grouping merges the warm set into ONE group (P1 holds only "
          "because of the mechanism, not the test's own encoding)")


def test_P1c_no_stranding_is_load_bearing_vs_pre_1c_counterfactual():
    section("P1c anti-circularity: the PRE-1c path (field seeded from RAW sources) DOES "
            "strand a same-domain sibling; 1c (group reps) removes it — so no-stranding "
            "genuinely depends on the mechanism")
    s, n = _small_mind()
    p = perceive(s, "coffee in the kitchen this morning")
    perceived = set(p.sources)

    # COUNTERFACTUAL pre-1c: build the field from EVERY raw perceived source (no clustering)
    # — exactly what the loop did before 1c — and form coalitions.
    raw_field = build_activation_field(
        s, list(p.sources.keys()), source_energies=p.sources)
    raw_coalitions = form_coalitions_from_field(raw_field, s)
    raw_singletons = [c for c in raw_coalitions if c.size() == 1]
    raw_stranded = [c for c in raw_singletons if (set(c.members) & perceived)]

    # WITH 1c: build the field from the group representatives only.
    cl = cluster_sources(s, p.sources)
    field_1c = build_activation_field(
        s, list(cl.group_seeds.keys()), source_energies=cl.group_seeds)
    co_1c = form_coalitions_from_field(field_1c, s)
    singletons_1c = [c for c in co_1c if c.size() == 1]
    stranded_1c = [c for c in singletons_1c if (set(c.members) & perceived)]

    # The counterfactual must strand at least one perceived source (otherwise no-stranding
    # would be vacuous on this input and 1c would not be doing the work it claims).
    check(len(raw_stranded) >= 1,
          f"pre-1c counterfactual strands >=1 perceived source "
          f"(raw_stranded={len(raw_stranded)}) — proves the failure 1c fixes is real")
    # And 1c removes the stranding.
    check(len(stranded_1c) == 0,
          f"1c removes the stranding (stranded_1c={len(stranded_1c)}) — no-stranding is "
          f"a real effect of the mechanism, not encoded by the test")


# ─────────────────────────────────────────────────────────────────────────────
# P2 — Cross-process determinism (our OWN probe, >=6 hash seeds)
# ─────────────────────────────────────────────────────────────────────────────

def _det_probe(driver_body):
    """Run `driver_body` (a string) under 6 distinct PYTHONHASHSEED values in fresh
    interpreters; return the list of stdout strings."""
    outs = []
    # the tests directory is on the import path via run_tests.py PYTHONPATH; for direct
    # runs we also add src so the child resolves bare imports regardless of cwd.
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(os.path.dirname(here), "src")
    for seed in ("0", "1", "3", "8", "101", "65535"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"]
                                   if env.get("PYTHONPATH") else "")
        rr = subprocess.run([sys.executable, "-c", driver_body],
                            cwd=here, capture_output=True, text=True, env=env)
        if rr.returncode != 0:
            print("  (subprocess error)\n", rr.stderr)
            outs.append("ERROR:" + rr.stderr.strip()[-200:])
        else:
            outs.append(rr.stdout.strip())
    return outs


def test_P2_cross_process_determinism_full_clustering():
    section("P2 cross-process determinism: full clustering byte-identical across 6 seeds "
            "(our own probe; ties everywhere)")
    # Adversarial graph: a symmetric ring of 4 equal-strength sources (ties EVERYWHERE in
    # proximity), all equal energy (ties in representative election), PLUS an unconnected
    # equal-energy pair. Serialized by stable content keys. If any iteration order leaked,
    # group order / representatives / group_seeds would differ across seeds.
    # SPEC-0c §5.1: the payload serialises BIT PATTERNS, never round(x, 9). round() is
    # structurally blind to everything below 1e-9, and 1 ULP is exactly what BUG-0b1 was;
    # a determinism probe that rounds is not a determinism probe.
    driver = textwrap.dedent('''
        import struct
        from psyche_store import SubstrateStore, Clock, NodeType
        from psyche_perceive import perceive
        from psyche_source_clustering import cluster_sources
        s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
        def add(c, t=NodeType.CONCEPT): return s.add_node(c, t)
        # ring p-q-r-s-p, all n=30 (equal strengths -> ties); plus pair u-v (n=30)
        p=add("pp"); q=add("qq"); r=add("rr"); ss=add("sx"); u=add("uu"); v=add("vv")
        def w(a,b,k=30):
            for _ in range(k): s.traverse(a,b)
        w(p,q); w(q,r); w(r,ss); w(ss,p); w(u,v)
        # all named by exactly one token each -> equal energies -> election ties on seq
        per = perceive(s, "pp qq rr sx uu vv")
        cl = cluster_sources(s, per.sources)
        out = []
        for g in cl.groups:
            members = tuple(sorted(s.get_node(m).content for m in g.members))
            rep = s.get_node(g.representative).content
            seed = struct.pack("<d", cl.group_seeds[g.representative]).hex()
            out.append((members, rep, seed))
        print(repr(out))
    ''')
    outs = _det_probe(driver)
    check(len(set(outs)) == 1,
          f"clustering identical across 6 hash seeds (distinct outputs: {len(set(outs))}); "
          f"sample={outs[0][:120] if outs else None}")


def test_P2b_cross_process_determinism_full_think_pipeline():
    section("P2b cross-process determinism: full think() coalitions + clustering across 6 "
            "seeds (loop-closed end to end)")
    # SPEC-0c §5.1: BIT PATTERNS, never round(x, 9).
    driver = textwrap.dedent('''
        import struct
        from psyche_store import SubstrateStore, Clock, NodeType
        from psyche_perceive import think
        s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
        def add(c, t=NodeType.CONCEPT): return s.add_node(c, t)
        coffee=add("coffee",NodeType.ENTITY); warmth=add("warmth",NodeType.SENSATION)
        morning=add("morning routine"); cozy=add("cozy feeling"); kitchen=add("kitchen",NodeType.ENTITY)
        work=add("work"); desk=add("desk",NodeType.ENTITY); deadline=add("deadline pressure"); code=add("writing code")
        def w(a,b,n):
            for _ in range(n): s.traverse(a,b)
        w(coffee,warmth,30); w(coffee,morning,30); w(morning,cozy,30); w(coffee,kitchen,30); w(kitchen,morning,30)
        w(work,desk,30); w(work,deadline,30); w(work,code,30); w(desk,code,30); w(coffee,work,8)
        r = think(s, "coffee in the kitchen this morning")
        clu = []
        for g in r.clustering.groups:
            clu.append((tuple(sorted(s.get_node(m).content for m in g.members)),
                        s.get_node(g.representative).content,
                        struct.pack("<d", r.clustering.group_seeds[g.representative]).hex()))
        co = []
        for c in r.coalitions:
            co.append((tuple(sorted(s.get_node(m).content for m in c.members)),
                       struct.pack("<d", c.strength).hex(),
                       s.get_node(c.representative()).content))
        print(repr((clu, co, s.get_node(r.thought.representative()).content if r.thought else None)))
    ''')
    outs = _det_probe(driver)
    check(len(set(outs)) == 1,
          f"full think() pipeline identical across 6 hash seeds "
          f"(distinct outputs: {len(set(outs))})")


# ─────────────────────────────────────────────────────────────────────────────
# P3 — Integrity unchanged, including adversarial graphs
# ─────────────────────────────────────────────────────────────────────────────

def _integrity_holds(s):
    try:
        s.check_integrity()
        return True
    except Exception as e:
        print("   integrity error:", e)
        return False


def test_P3_integrity_unchanged_small_mind():
    section("P3 integrity unchanged before/after clustering (small_mind)")
    s, n = _small_mind()
    check(_integrity_holds(s), "precondition: integrity holds before")
    p = perceive(s, "coffee in the kitchen this morning")
    for _ in range(4):
        cluster_sources(s, p.sources)
    check(_integrity_holds(s), "integrity holds after repeated clustering")


def test_P3b_integrity_adversarial_cycles_selfloops_closed_dupes():
    section("P3b integrity unchanged on an ADVERSARIAL graph (cycle, self-loop, closed/"
            "traumatic road, duplicate-content nodes, high-degree fan)")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    # cycle a->b->c->a
    a = s.add_node("alpha", NodeType.CONCEPT)
    b = s.add_node("alpha", NodeType.CONCEPT)   # DUPLICATE content of a
    c = s.add_node("gamma", NodeType.CONCEPT)
    _worn(s, a, b); _worn(s, b, c); _worn(s, c, a)
    # self-loop on a
    _worn(s, a, a)
    # high-degree fan: hub -> 12 leaves
    hub = s.add_node("hub", NodeType.CONCEPT)
    leaves = [s.add_node(f"leaf alpha {i}", NodeType.CONCEPT) for i in range(12)]
    for lf in leaves:
        _worn(s, hub, lf)
    # closed/traumatic road: drive a strongly-negative crossing to close it
    x = s.add_node("xeno", NodeType.CONCEPT)
    y = s.add_node("yotta", NodeType.CONCEPT)
    for _ in range(5):
        s.traverse(x, y, charge={"fear": -0.95})   # one-shot trauma closes it
    check(_integrity_holds(s), "precondition: adversarial graph is integral before")

    # cluster on a perceived set that touches the duplicate-content and fan nodes
    p = perceive(s, "alpha gamma hub xeno yotta")
    snap = _snapshot_full(s)
    for _ in range(4):
        cluster_sources(s, p.sources)
    check(_integrity_holds(s), "integrity holds after clustering an adversarial graph")
    check(_snapshot_full(s) == snap,
          "adversarial graph byte-identical after clustering (deep snapshot)")


# ─────────────────────────────────────────────────────────────────────────────
# P4 — Read-purity (strengths AND traversal counts), repeated passes
# ─────────────────────────────────────────────────────────────────────────────

def test_P4_read_purity_deep_snapshot():
    section("P4 read-purity: deep snapshot (strength/charges/closed/traversal + node "
            "access stats) unchanged after many clustering passes")
    s, n = _small_mind()
    before = _snapshot_full(s)
    p1 = perceive(s, "coffee in the kitchen this morning")
    p2 = perceive(s, "coffee in the kitchen, writing code")
    p3 = perceive(s, "work and the deadline")
    for _ in range(8):
        cluster_sources(s, p1.sources)
        cluster_sources(s, p2.sources)
        cluster_sources(s, p3.sources)
    after = _snapshot_full(s)
    check(before == after, "deep store snapshot unchanged after 24 clustering passes")


def test_P4b_read_purity_through_full_think():
    section("P4b read-purity: full think() (perceive->cluster->field->coalitions) mutates "
            "nothing across repeated cycles")
    s, n = _small_mind()
    before = _snapshot_full(s)
    for _ in range(5):
        think(s, "coffee in the kitchen this morning")
        think(s, "coffee in the kitchen, writing code")
    after = _snapshot_full(s)
    check(before == after, "store byte-identical after 10 full think() cycles")


# ─────────────────────────────────────────────────────────────────────────────
# P5 — Scale-invariance under tiny/huge adversarial constants
# ─────────────────────────────────────────────────────────────────────────────

def test_P5_scale_invariance_energies_extreme_constants():
    section("P5 scale-invariance: partition + representatives identical under tiny/huge "
            "energy scaling (1e-12 .. 1e12)")
    s, n = _small_mind()
    p = perceive(s, "coffee in the kitchen this morning")
    base = cluster_sources(s, p.sources)
    base_part = sorted(tuple(sorted(g.members)) for g in base.groups)
    base_reps = set(base.representatives())
    for k in (1e-12, 1e-6, 1e6, 1e12, 0.0):
        scaled = {nid: e * k for nid, e in p.sources.items()}
        c = cluster_sources(s, scaled)
        part = sorted(tuple(sorted(g.members)) for g in c.groups)
        check(part == base_part, f"partition identical when energies scaled by {k}")
        # representatives: when k==0 every energy is 0 -> all tie -> election falls to
        # creation_seq, which is the SAME tiebreak as the non-degenerate case here
        # (the warm group's min-seq member). So reps must still match.
        check(set(c.representatives()) == base_reps,
              f"representatives identical when energies scaled by {k}")


def test_P5b_scale_invariance_road_strength_structural():
    section("P5b scale-invariance: identical STRUCTURE at different absolute road strengths "
            "yields identical partition shape (relative threshold)")
    def two_pair(strength_traversals):
        st = SubstrateStore(clock=Clock(simulated=True, start=0.0))
        a = st.add_node("aa", NodeType.CONCEPT); b = st.add_node("bb", NodeType.CONCEPT)
        c = st.add_node("cc", NodeType.CONCEPT); d = st.add_node("dd", NodeType.CONCEPT)
        for _ in range(strength_traversals):
            st.traverse(a, b); st.traverse(c, d)
        return st, {a: 1.0, b: 1.0, c: 1.0, d: 1.0}
    parts = []
    for k in (3, 10, 30, 100):
        st, e = two_pair(k)
        c = cluster_sources(st, e)
        parts.append(sorted(len(g.members) for g in c.groups))
    check(all(pt == [2, 2] for pt in parts),
          f"same structure across absolute strengths -> same partition shape (got {parts})")


# ─────────────────────────────────────────────────────────────────────────────
# P6 — A1 purity / anti-circularity: clustering cannot depend on the field
# ─────────────────────────────────────────────────────────────────────────────

def test_P6_clustering_independent_of_field():
    section("P6 A1 purity: clustering output is unchanged no matter what the activation "
            "field does (the field cannot leak back into the grouping)")
    s, n = _small_mind()
    p = perceive(s, "coffee in the kitchen this morning")

    baseline = _partition_by_content(s, cluster_sources(s, p.sources))

    # Build a field with the RAW perceived sources (different sources, different energies
    # than the group seeds) — an adversarial alternate field — then cluster again.
    _ = build_activation_field(s, list(p.sources.keys()), source_energies=p.sources)
    after_field_1 = _partition_by_content(s, cluster_sources(s, p.sources))

    # Build a field seeded with WILDLY different energies on a single source.
    if p.sources:
        one = next(iter(p.sources))
        _ = build_activation_field(s, [one], source_energies={one: 1e9})
    after_field_2 = _partition_by_content(s, cluster_sources(s, p.sources))

    # Build a field on a DISJOINT set of nodes entirely.
    work_nodes = [n["work"], n["desk"], n["code"]]
    _ = build_activation_field(s, work_nodes, source_energies={x: 5.0 for x in work_nodes})
    after_field_3 = _partition_by_content(s, cluster_sources(s, p.sources))

    check(baseline == after_field_1 == after_field_2 == after_field_3,
          "clustering identical regardless of any field built before it (no field leakage)")


def test_P6b_clustering_signature_takes_no_field():
    section("P6b A1 purity (structural): cluster_sources has NO field/per_source parameter")
    import inspect
    sig = inspect.signature(cluster_sources)
    params = set(sig.parameters.keys())
    # it must take only the store, source energies, and the threshold knob — nothing that
    # could carry the activation field (per_source / field_ / activation).
    forbidden = {"field_", "field", "per_source", "activation", "activation_field"}
    check(params & forbidden == set(),
          f"cluster_sources accepts no field-derived parameter (params={sorted(params)})")
    check("store" in params and "source_energies" in params,
          "cluster_sources reads only store + source_energies (+ threshold knob)")


# ─────────────────────────────────────────────────────────────────────────────
# P7 — Edge cases the builder may have under-tested
# ─────────────────────────────────────────────────────────────────────────────

def test_P7_zero_sources():
    section("P7 edge: zero sources -> empty clustering, no crash")
    s, n = _small_mind()
    c = cluster_sources(s, {})
    check(c.groups == [] and c.group_seeds == {},
          "empty source map yields empty groups and empty seeds")


def test_P7_single_source():
    section("P7 edge: a single source -> one singleton group, rep = itself, seed = energy")
    s, n = _small_mind()
    c = cluster_sources(s, {n["coffee"]: 0.73})
    check(len(c.groups) == 1, "one source -> exactly one group")
    g = c.groups[0]
    check(set(g.members) == {n["coffee"]} and g.representative == n["coffee"],
          "the lone source is its own group's representative")
    check(abs(c.group_seeds[n["coffee"]] - 0.73) < 1e-12,
          "single-group seed energy is the source's own energy")


def test_P7_source_not_in_store_is_dropped():
    section("P7 edge: a source id NOT present in the store is silently dropped (filtered)")
    s, n = _small_mind()
    ghost = "ffffffffffffffffffffffffffffffff"  # not a real node id
    check(not s.exists(ghost), "precondition: ghost id is not in the store")
    c = cluster_sources(s, {ghost: 1.0, n["coffee"]: 1.0})
    members = set()
    for g in c.groups:
        members |= set(g.members)
    check(ghost not in members, "the non-existent source does not appear in any group")
    check(members == {n["coffee"]}, "only the real source is clustered")


def test_P7_all_zero_proximity_no_roads():
    section("P7 edge: sources with NO roads between them -> each is its own singleton group")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    a = s.add_node("aaa", NodeType.CONCEPT)
    b = s.add_node("bbb", NodeType.CONCEPT)
    c = s.add_node("ccc", NodeType.CONCEPT)
    # no roads at all
    check(_pair_proximity(s, a, b) == 0.0 and _pair_proximity(s, a, c) == 0.0,
          "precondition: all pairwise proximities are zero")
    cl = cluster_sources(s, {a: 1.0, b: 1.0, c: 1.0})
    check(len(cl.groups) == 3,
          f"three roadless sources -> three singleton groups (got {len(cl.groups)})")
    check(all(g.size() == 1 for g in cl.groups),
          "every group is a singleton when no proximity binds anything")


def test_P7_ties_in_energy_and_creation_seq_are_resolved():
    section("P7 edge: ties in BOTH energy and creation_seq -> still deterministic, no uuid "
            "fallback (single in-process check + cross-process check)")
    # Two nodes can never share a creation_seq (the counter is strictly increasing), so a
    # true (energy, seq) double-tie is impossible by construction — the seq breaks every
    # energy tie. We assert that invariant AND that the rep is the lower-seq node.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    a = s.add_node("aaa", NodeType.CONCEPT)   # earlier seq
    b = s.add_node("bbb", NodeType.CONCEPT)   # later seq
    _worn(s, a, b)                            # linked -> one group, energies tie
    p = perceive(s, "aaa bbb")
    check(abs(p.sources[a] - p.sources[b]) < 1e-12, "precondition: energies tie")
    check(s.get_node(a).creation_seq != s.get_node(b).creation_seq,
          "creation_seq is unique per node (no true double-tie is possible)")
    cl = cluster_sources(s, p.sources)
    check(len(cl.groups) == 1 and cl.groups[0].representative == a,
          "the lower-creation_seq node wins the energy tie (no uuid fallback)")


def test_P7_chaining_single_link():
    section("P7 edge: single-link CHAINING A-B-C grouped though A-C not directly near")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    A = s.add_node("aaa", NodeType.CONCEPT)
    B = s.add_node("bbb", NodeType.CONCEPT)
    C = s.add_node("ccc", NodeType.CONCEPT)
    _worn(s, A, B); _worn(s, B, C)   # A-B, B-C linked; A-C NOT
    check(_pair_proximity(s, A, C) == 0.0, "precondition: A and C are not directly near")
    cl = cluster_sources(s, {A: 1.0, B: 1.0, C: 1.0})
    check(len(cl.groups) == 1 and {A, B, C} <= set(cl.groups[0].members),
          "A-B-C chain into ONE group via the shared neighbor B (single-link)")


def test_P7_chaining_long_transitive_closure():
    section("P7 edge: a long single-link chain A-B-C-D-E all merges (transitive closure)")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    ids = [s.add_node(f"n{i:02d}", NodeType.CONCEPT) for i in range(5)]
    for i in range(4):
        _worn(s, ids[i], ids[i + 1])   # path graph, no skip edges
    cl = cluster_sources(s, {x: 1.0 for x in ids})
    check(len(cl.groups) == 1 and set(cl.groups[0].members) == set(ids),
          "a 5-node path collapses into a single chained group")


def test_P7_self_loop_does_not_corrupt():
    section("P7 edge: a self-loop on a source does not corrupt grouping or representative")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    a = s.add_node("aaa", NodeType.CONCEPT)
    b = s.add_node("bbb", NodeType.CONCEPT)
    _worn(s, a, a)        # self-loop
    _worn(s, a, b)        # a-b link
    # proximity(a,a) is never queried (pairs are i<j of distinct sources); the self-loop
    # must not change the a-b grouping.
    cl = cluster_sources(s, {a: 1.0, b: 1.0})
    check(len(cl.groups) == 1 and {a, b} <= set(cl.groups[0].members),
          "self-loop on a leaves the a-b group intact")


def test_P7_high_degree_fan_node_as_source():
    section("P7 edge: a high-degree fan hub as a source groups only with its perceived "
            "spokes, not with the whole fan")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    hub = s.add_node("hub", NodeType.CONCEPT)
    spokes = [s.add_node(f"spoke{i:02d}", NodeType.CONCEPT) for i in range(20)]
    for sp in spokes:
        _worn(s, hub, sp)
    # only hub + two spokes are sources; the other 18 spokes are NOT perceived
    srcs = {hub: 1.0, spokes[0]: 1.0, spokes[1]: 1.0}
    cl = cluster_sources(s, srcs)
    members = set()
    for g in cl.groups:
        members |= set(g.members)
    check(members == set(srcs),
          "only perceived sources are clustered even when the hub has 20 roads")
    # hub links to both spokes directly -> all three in one group
    check(len(cl.groups) == 1, "hub + its two perceived spokes form one group")


def test_P7_closed_road_proximity_uses_canonical_strength():
    section("P7 edge: a CLOSED (traumatic) road still contributes its canonical strength to "
            "proximity (clustering reads strength, independent of closure/breakthrough)")
    # Clustering reads canonical road strength via _pair_proximity, NOT the activation
    # field's breakthrough logic. A closed road with high strength must still bind its
    # endpoints in the proximity graph (1c is topology/strength only, A1).
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    a = s.add_node("aaa", NodeType.CONCEPT)
    b = s.add_node("bbb", NodeType.CONCEPT)
    # build strength first, THEN traumatize to close (closure doesn't zero strength)
    for _ in range(30):
        s.traverse(a, b)
    strength_open = s.get_road(s.find_road(a, b), apply_decay=False).strength
    s.traverse(a, b, charge={"fear": -0.95})  # one-shot trauma -> closed
    rid = s.find_road(a, b)
    check(s.get_road(rid, apply_decay=False).closed, "precondition: the a-b road is closed")
    prox = _pair_proximity(s, a, b)
    check(prox >= strength_open * 0.5,
          f"closed road still yields positive proximity from canonical strength "
          f"(prox={round(prox,4)})")
    cl = cluster_sources(s, {a: 1.0, b: 1.0})
    check(len(cl.groups) == 1,
          "endpoints of a strong CLOSED road still group (1c is topology/strength, not "
          "field breakthrough)")


def test_P7_duplicate_content_unlinked_do_not_merge():
    section("P7 edge: two nodes with IDENTICAL content but NO road do not merge "
            "(membership is topological, not content-based)")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    a = s.add_node("samecontent", NodeType.CONCEPT)
    b = s.add_node("samecontent", NodeType.CONCEPT)   # duplicate content, no road
    p = perceive(s, "samecontent")
    check(set(p.sources) == {a, b}, "precondition: both duplicate-content nodes perceived")
    cl = cluster_sources(s, p.sources)
    check(len(cl.groups) == 2,
          "duplicate-content but unlinked nodes form TWO groups (topology, not content)")


# ─────────────────────────────────────────────────────────────────────────────
# P8 — Loop-closure generalization of NO-STRANDING beyond the single spec input
# ─────────────────────────────────────────────────────────────────────────────

def test_P8_no_stranding_generalization_two_clusters_loop_closed():
    section("P8 loop-closure: no-stranding on a SYSTEM-GENERATED two-cluster utterance "
            "(two internally-linked domains, no cross bridge)")
    # Two clean clusters, each internally fully linked, NO cross edges. Perception lights
    # all six from one utterance; 1c should yield two groups (one rep each); each basin is
    # multi-node, so NO perceived source should strand as a singleton. Loop-closed.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    # cluster 1: apple-banana-cherry (triangle)
    a1 = s.add_node("apple", NodeType.CONCEPT)
    a2 = s.add_node("banana", NodeType.CONCEPT)
    a3 = s.add_node("cherry", NodeType.CONCEPT)
    _worn(s, a1, a2); _worn(s, a2, a3); _worn(s, a3, a1)
    # cluster 2: piston-engine-gearbox (triangle)
    b1 = s.add_node("piston", NodeType.CONCEPT)
    b2 = s.add_node("engine", NodeType.CONCEPT)
    b3 = s.add_node("gearbox", NodeType.CONCEPT)
    _worn(s, b1, b2); _worn(s, b2, b3); _worn(s, b3, b1)
    r = think(s, "apple banana cherry piston engine gearbox")
    perceived = set(r.perception.sources)
    check({a1, a2, a3, b1, b2, b3} <= perceived,
          "precondition: perception lit all six nodes from the utterance")
    # 1c should produce exactly two groups
    check(len(r.clustering.groups) == 2,
          f"two internally-linked, mutually-unlinked domains -> two groups "
          f"(got {len(r.clustering.groups)})")
    singleton_coalitions = [c for c in r.coalitions if c.size() == 1]
    stranded = [c for c in singleton_coalitions if (set(c.members) & perceived)]
    check(len(stranded) == 0,
          f"no perceived source strands as a singleton (stranded={len(stranded)})")


def test_P8b_isolated_perceived_source_stranding_probe_loop_closed():
    section("P8b loop-closure PROBE: does an ISOLATED perceived source strand as a "
            "singleton basin through the real think() loop? (reports the exact behavior)")
    # ADVERSARIAL loop-closed input that the builder never tested: one utterance names BOTH
    # a connected cluster AND a totally isolated node. After 1c the isolated node is its own
    # group -> its own representative -> a single-node spread -> a SINGLETON basin whose
    # member is a perceived source. We report exactly what think() does. This is outside the
    # literal §6.1 acceptance scope (which is fixed to the coffee/kitchen/morning input on
    # _small_mind), but it tests whether the no-stranding PROPERTY generalizes.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    # connected cluster
    a1 = s.add_node("apple", NodeType.CONCEPT)
    a2 = s.add_node("banana", NodeType.CONCEPT)
    _worn(s, a1, a2)
    # isolated node — NO roads at all
    lone = s.add_node("zucchini", NodeType.CONCEPT)
    r = think(s, "apple banana zucchini")
    perceived = set(r.perception.sources)
    check({a1, a2, lone} <= perceived,
          "precondition: perception lit the cluster AND the isolated node")
    # is the isolated source its own group?
    lone_groups = [g for g in r.clustering.groups if lone in set(g.members)]
    isolated_is_singleton_group = (len(lone_groups) == 1 and lone_groups[0].size() == 1)
    singleton_coalitions = [c for c in r.coalitions if c.size() == 1]
    stranded = [c for c in singleton_coalitions if (set(c.members) & perceived)]
    # We do NOT assert no-stranding here (it is expected to strand). We assert the MECHANISM
    # is internally consistent: an isolated source IS its own singleton group, and IF it
    # strands, the stranded member is exactly that isolated source — i.e. the behavior is
    # the predictable consequence of an isolated seed, not a nondeterministic glitch.
    print(f"      → isolated source its own group: {isolated_is_singleton_group}; "
          f"stranded singleton coalitions touching a perceived source: {len(stranded)}")
    if stranded:
        stranded_members = set()
        for c in stranded:
            stranded_members |= set(c.members)
        check(lone in stranded_members,
              "the (expected) stranded singleton is exactly the isolated source — "
              "predictable, not a glitch (generalization gap vs literal §6.1 scope; "
              "reported, not a §6.1 FAIL)")
    else:
        check(True, "no stranding even with an isolated source (stronger than required)")
    # the connected pair must NOT strand regardless
    pair_singletons = [c for c in singleton_coalitions
                       if (set(c.members) & {a1, a2})]
    check(len(pair_singletons) == 0,
          "the connected cluster's sources do not strand (they share one basin)")


def test_P8c_merge_holds_on_independently_built_isomorphic_graph():
    section("P8c loop-closure: merge property holds on an INDEPENDENTLY built graph "
            "isomorphic to _small_mind but with different content/order")
    # Rebuild the same TOPOLOGY with different node contents and creation order, drive with
    # the matching utterance, and confirm merge still holds — proving the property is about
    # structure, not the specific strings the builder used.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    # build the work domain FIRST (different creation order than _small_mind)
    job = s.add_node("project", NodeType.CONCEPT)
    table = s.add_node("table surface", NodeType.ENTITY)
    due = s.add_node("due date", NodeType.CONCEPT)
    prog = s.add_node("programming task", NodeType.CONCEPT)
    # warm domain
    tea = s.add_node("tea", NodeType.ENTITY)
    heat = s.add_node("heat", NodeType.SENSATION)
    dawn = s.add_node("dawn ritual", NodeType.CONCEPT)
    snug = s.add_node("snug mood", NodeType.CONCEPT)
    galley = s.add_node("galley", NodeType.ENTITY)
    _worn(s, tea, heat); _worn(s, tea, dawn); _worn(s, dawn, snug)
    _worn(s, tea, galley); _worn(s, galley, dawn)
    _worn(s, job, table); _worn(s, job, due); _worn(s, job, prog); _worn(s, table, prog)
    _worn(s, tea, job, n=8)   # bridge
    r = think(s, "tea in the galley at dawn")
    perceived = set(r.perception.sources)
    warm = {tea, galley, dawn}
    check(warm <= perceived, "precondition: perception lit tea, galley, dawn")
    touching = [g for g in r.clustering.groups if warm & set(g.members)]
    check(len(touching) == 1 and warm <= set(touching[0].members),
          "merge holds on an independently-built isomorphic graph (structure, not strings)")
    singleton_coalitions = [c for c in r.coalitions if c.size() == 1]
    stranded = [c for c in singleton_coalitions if (set(c.members) & perceived)]
    check(len(stranded) == 0, "no-stranding also holds on the isomorphic graph")


# ─────────────────────────────────────────────────────────────────────────────
# P9 — Over-swallow asserted-negative is a TRUE residual (not green-washing)
# ─────────────────────────────────────────────────────────────────────────────

def test_P9_over_swallow_FLIPPED_by_1d_i():
    section("P9 (was: over-swallow residual is real) — FLIPPED by 1d-i: the bridged, "
            "unperceived work/code domain is now PRUNED from the winning thought")
    # NOTE FOR THE TESTER (lane honesty): this was a 1c-era tester assertion that
    # over-swallow PERSISTED (over == True). The 1d-i builder converted it to the positive
    # assertion because SPEC-1c §6.1/§7.7 and SPEC-1d §6.1/§7.1 explicitly hand this exact
    # residual to 1d to flip, and 1d-i now makes `over == True` factually false through the
    # live loop. This is a coverage UPDATE to the fixed behavior, not a weakening to pass a
    # defect; the tester should independently re-verify and re-own it for 1d-i.
    s, n = _small_mind()
    r = think(s, "coffee in the kitchen this morning")
    # the 1c stage is unchanged: still exactly one group, coffee represents it, and the
    # field still REACHES the bridged work/code domain (the spread is unchanged).
    check(len(r.clustering.groups) == 1, "only one group on this utterance (warm only)")
    check(r.clustering.groups[0].representative == n["coffee"],
          "coffee is the elected representative")
    reached = set(r.field_.total.keys())
    check(n["work"] in reached and n["code"] in reached,
          "precondition: the single-source spread still REACHES work/code over the n=8 "
          "bridge — 1d-i prunes at the workspace, it does not change the field")
    # FIXED behavior: the winning thought excludes the unperceived work/code domain
    thought_members = set(r.thought.members) if r.thought else set()
    check(n["work"] not in thought_members and n["code"] not in thought_members,
          "1d-i: the winning thought no longer over-swallows work/code")
    check(r.workspace is not None and
          {n["work"], n["code"]} <= set(r.workspace.pruned_members),
          "work and code are recorded in workspace.pruned_members")
    # AND the §6.1 merge/no-stranding properties still HOLD alongside the flip.
    warm = {n["coffee"], n["kitchen"], n["morning"]}
    touching = [g for g in r.clustering.groups if warm & set(g.members)]
    perceived = set(r.perception.sources)
    singletons = [c for c in r.coalitions if c.size() == 1 and (set(c.members) & perceived)]
    check(len(touching) == 1 and len(singletons) == 0,
          "§6.1 (merge + no-stranding) still HOLDS alongside the over-swallow flip")


# ─────────────────────────────────────────────────────────────────────────────
# P10 — no over-merge: a real loop input must yield MORE THAN ONE group sometimes
# ─────────────────────────────────────────────────────────────────────────────

def test_P10_partition_can_yield_multiple_groups_loop_closed():
    section("P10 anti-degeneracy: clustering is not an 'everything always merges' branch — "
            "a real utterance yields >1 group when domains are unlinked")
    s, n = _small_mind()
    # 'writing code' has no direct road to coffee/kitchen, so it must split off.
    r = think(s, "coffee in the kitchen, writing code")
    perceived = set(r.perception.sources)
    check({n["coffee"], n["kitchen"], n["code"]} <= perceived,
          "precondition: coffee, kitchen, code all perceived")
    def group_of(node):
        for g in r.clustering.groups:
            if node in g.members:
                return frozenset(g.members)
        return None
    g_coffee = group_of(n["coffee"]); g_code = group_of(n["code"])
    check(g_coffee is not None and g_code is not None and n["code"] not in g_coffee,
          "the code node splits into a different group than coffee")
    check(len(r.clustering.groups) >= 2,
          f"partition yields >=2 groups (got {len(r.clustering.groups)})")


def run_all():
    print("=" * 70)
    print("  TESTER — INDEPENDENT ADVERSARIAL SUITE for 1c (source-clustering)")
    print("=" * 70)
    for t in [
        test_P1_acceptance_merge_and_no_stranding_loop_closed,
        test_P1b_hand_assigned_grouping_would_NOT_satisfy_merge,
        test_P1c_no_stranding_is_load_bearing_vs_pre_1c_counterfactual,
        test_P2_cross_process_determinism_full_clustering,
        test_P2b_cross_process_determinism_full_think_pipeline,
        test_P3_integrity_unchanged_small_mind,
        test_P3b_integrity_adversarial_cycles_selfloops_closed_dupes,
        test_P4_read_purity_deep_snapshot,
        test_P4b_read_purity_through_full_think,
        test_P5_scale_invariance_energies_extreme_constants,
        test_P5b_scale_invariance_road_strength_structural,
        test_P6_clustering_independent_of_field,
        test_P6b_clustering_signature_takes_no_field,
        test_P7_zero_sources,
        test_P7_single_source,
        test_P7_source_not_in_store_is_dropped,
        test_P7_all_zero_proximity_no_roads,
        test_P7_ties_in_energy_and_creation_seq_are_resolved,
        test_P7_chaining_single_link,
        test_P7_chaining_long_transitive_closure,
        test_P7_self_loop_does_not_corrupt,
        test_P7_high_degree_fan_node_as_source,
        test_P7_closed_road_proximity_uses_canonical_strength,
        test_P7_duplicate_content_unlinked_do_not_merge,
        test_P8_no_stranding_generalization_two_clusters_loop_closed,
        test_P8b_isolated_perceived_source_stranding_probe_loop_closed,
        test_P8c_merge_holds_on_independently_built_isomorphic_graph,
        test_P9_over_swallow_FLIPPED_by_1d_i,
        test_P10_partition_can_yield_multiple_groups_loop_closed,
    ]:
        t()
    print("\n" + "=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    if _fail_msgs:
        print("  FAILURES:")
        for m in _fail_msgs:
            print("   -", m)
    print("=" * 70)
    return _failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run_all() else 1)
