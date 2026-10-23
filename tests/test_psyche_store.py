"""
Test suite for the Psyche Substrate Store (Layer 1).

Each test exercises a specific Layer-1 decision. Run directly:
    python3 test_psyche_store.py
A passing run prints a summary; any violation raises and stops.
"""

from psyche_store import (
    SubstrateStore, Clock, NodeType, RoadQuality, NotFound, IntegrityError,
)


# tiny test harness (no pytest dependency — runs anywhere)
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
        return
    except Exception as e:
        _failed += 1
        print(f"  FAIL: {msg} — raised {type(e).__name__}, expected {exc.__name__}")
        return
    _failed += 1
    print(f"  FAIL: {msg} — nothing raised, expected {exc.__name__}")


def section(name):
    print(f"\n{name}")


# ─────────────────────────────────────────────────────────────────────────────

def test_identity_and_order():
    section("identity & creation order")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    check(a != b, "distinct nodes get distinct IDs")
    check(len(a) == 32 and all(c in "0123456789abcdef" for c in a),
          "IDs are uuid4 hex (opaque, 32 chars)")
    na, nb = s.get_node(a), s.get_node(b)
    check(na.creation_seq < nb.creation_seq,
          "creation_seq orders nodes by formation (data, not identity)")


def test_notfound_is_safe():
    section("stale IDs resolve to NotFound, never to a wrong object")
    s = SubstrateStore(clock=Clock(simulated=True))
    expect_raises(NotFound, lambda: s.get_node("deadbeef"),
                  "get_node on unknown ID raises NotFound")
    expect_raises(NotFound, lambda: s.get_road("deadbeef"),
                  "get_road on unknown ID raises NotFound")
    a = s.add_node("a", NodeType.CONCEPT)
    s.remove_node(a)
    expect_raises(NotFound, lambda: s.get_node(a),
                  "removed node ID resolves to NotFound, not a stale object")
    check(s.exists(a) is False, "exists() is False after removal")


def test_one_road_per_pair():
    section("simple graph: one road per (src,tgt) pair, deduped")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    r1 = s.add_road(a, b)
    r2 = s.add_road(a, b)
    check(r1 == r2, "second add_road for same pair returns the existing road")
    check(s.road_count() == 1, "no duplicate road created")
    # reverse direction is a different road
    r3 = s.add_road(b, a)
    check(r3 != r1, "reverse-direction road is distinct (directed graph)")
    check(s.road_count() == 2, "reverse road counted separately")
    check(s.find_road(a, b) == r1, "find_road resolves the pair via dedup index")


def test_split_primitives():
    section("split primitives: add_road creates, strengthen only strengthens")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    expect_raises(NotFound, lambda: s.strengthen("no-such-road"),
                  "strengthen on a missing road raises NotFound (does not create)")
    r = s.add_road(a, b)
    before = s.get_road(r, apply_decay=False).strength
    s.strengthen(r)
    after = s.get_road(r, apply_decay=False).strength
    check(after > before, "strengthen increases strength of an existing road")


def test_traverse_lays_path():
    section("traverse(): biology lives here — get-or-add then strengthen")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    check(s.find_road(a, b) is None, "no road before first traversal")
    r = s.traverse(a, b)
    check(s.find_road(a, b) == r, "first traversal lays the path")
    check(s.get_node(a).access_count == 1, "traverse touches the source node")
    check(s.get_node(b).access_count == 1, "traverse touches the target node")


def test_strengthening_and_quality():
    section("strengthening climbs quality dirt → highway; emotion deepens it")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    r = s.add_road(a, b)
    check(s.quality_of(r) == RoadQuality.DIRT, "new road is dirt")
    for _ in range(40):
        s.strengthen(r)  # neutral, repeated
    check(s.quality_of(r) == RoadQuality.HIGHWAY,
          "many crossings build a highway")
    # emotional crossings strengthen faster than neutral ones
    s2 = SubstrateStore(clock=Clock(simulated=True))
    x, y = s2.add_node("x", NodeType.CONCEPT), s2.add_node("y", NodeType.CONCEPT)
    z, w = s2.add_node("z", NodeType.CONCEPT), s2.add_node("w", NodeType.CONCEPT)
    r_neutral = s2.add_road(x, y)
    r_charged = s2.add_road(z, w)
    s2.strengthen(r_neutral)
    s2.strengthen(r_charged, charge={"fear": -0.9})
    check(s2.get_road(r_charged, apply_decay=False).strength >
          s2.get_road(r_neutral, apply_decay=False).strength,
          "an emotionally charged crossing deepens the trace more")


def test_multi_charge_road():
    section("a road has an emotional life: multiple feelings on one road")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.ENTITY)
    b = s.add_node("b", NodeType.EVENT)
    r = s.add_road(a, b)
    s.strengthen(r, charge={"anger": -0.6})
    s.strengthen(r, charge={"grief": -0.5})
    road = s.get_road(r, apply_decay=False)
    check("anger" in road.charges and "grief" in road.charges,
          "the same road carries two feelings at once (one road, not two)")
    check(s.road_count() == 1, "multi-feeling did not create a second road")
    check(road.valence < 0, "aggregate valence reflects the negative feelings")


def test_lazy_decay():
    section("lazy decay: computed on read as a VIEW; stored state untouched")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    weak = s.add_road(a, b)          # left as dirt
    strong = s.add_road(a, c)
    for _ in range(40):
        s.strengthen(strong)        # build a highway
    weak_canonical = s.get_road(weak, apply_decay=False).strength
    strong_canonical = s.get_road(strong, apply_decay=False).strength
    s.clock.advance(60.0)           # time passes; NO global sweep, NO write
    weak_view = s.get_road(weak).strength       # decay computed into the view
    strong_view = s.get_road(strong).strength
    check(weak_view < weak_canonical, "read VIEW shows the weak road decayed")
    check(strong_view < strong_canonical, "read VIEW shows the highway decayed...")
    check((strong_canonical - strong_view) < (weak_canonical - weak_view),
          "...but far less — highways are dramatically more stable")
    # the critical property: the stored (canonical) value did NOT change from reads
    check(s.get_road(weak, apply_decay=False).strength == weak_canonical,
          "stored weak strength unchanged by reads (read is pure)")
    check(s.get_road(strong, apply_decay=False).strength == strong_canonical,
          "stored highway strength unchanged by reads (read is pure)")


def test_reads_are_pure():
    section("reads do not mutate stored state (atomicity model's load-bearing claim)")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    a = s.add_node("a", NodeType.ENTITY)
    b = s.add_node("b", NodeType.EVENT)
    r = s.traverse(a, b, charge={"joy": 0.5})
    s.clock.advance(30.0)
    # snapshot canonical state
    canon = s.get_road(r, apply_decay=False)
    snap = (canon.strength, dict(canon.charges), canon.closed, canon.last_touched)
    # hammer it with reads of every read-path that applies decay
    for _ in range(20):
        s.get_road(r)            # decayed view
        s.quality_of(r)          # reads via get_road
        list(s.neighbors(a))     # structural read
        list(s.roads_from(a))    # structural read
    after = s.get_road(r, apply_decay=False)
    now_snap = (after.strength, dict(after.charges), after.closed, after.last_touched)
    check(snap == now_snap,
          "20 reads (get_road/quality_of/neighbors/roads_from) changed NOTHING stored")


def test_closure_is_sticky():
    section("closure is sticky: time alone does NOT reopen a traumatized road")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    a = s.add_node("coffee", NodeType.ENTITY)
    b = s.add_node("burnt tongue", NodeType.EVENT)
    r = s.traverse(a, b, charge={"pain": -0.95})   # one-shot trauma → closed
    check(s.get_road(r, apply_decay=False).closed is True, "road closed by trauma")
    # let a long time pass with NO positive experience, and read it repeatedly
    s.clock.advance(500.0)
    for _ in range(10):
        s.get_road(r)             # reading must not reopen it
        s.quality_of(r)
    check(s.get_road(r, apply_decay=False).closed is True,
          "time + reading alone does NOT reopen the road (avoidance preserves trauma)")
    check(s.quality_of(r) == RoadQuality.CLOSED, "still reports CLOSED after long time")
    # only active positive return reopens it
    for _ in range(8):
        s.traverse(a, b, charge={"comfort": +0.5})
    check(s.get_road(r, apply_decay=False).closed is False,
          "active positive return DOES reopen it (post-traumatic growth, on purpose)")


def test_clock_advance_is_simulated_only():
    section("Clock.advance is simulated-only (never blocks the event loop)")
    real = Clock(simulated=False)
    expect_raises(RuntimeError, lambda: real.advance(1.0),
                  "advancing a real clock raises rather than sleeping")


def test_pin_guard():
    section("pin guard: cannot prune a node currently in use")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    s.pin(a)
    expect_raises(IntegrityError, lambda: s.remove_node(a),
                  "remove_node refuses a pinned node")
    s.unpin(a)
    s.remove_node(a)  # now allowed
    check(s.exists(a) is False, "node removable after unpin")


def test_deletion_leaves_no_dangling_index():
    section("deletion is complete: no dangling index entries; integrity holds")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    s.traverse(a, b)
    s.traverse(a, c)
    s.traverse(b, c)
    s.check_integrity()  # clean before
    s.remove_node(b)     # removes node b and roads a→b, b→c
    s.check_integrity()  # must still be clean: no orphan roads, no index drift
    check(s.road_count() == 1, "only a→c remains after removing b")
    check(s.find_road(a, b) is None, "pair-index cleaned for removed road")
    # a's out-index must no longer reference the removed a→b road
    check(len(list(s.roads_from(a))) == 1, "a's out-index cleaned")


def test_self_region():
    section("self-region: unowned designated subgraph, separate set")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("I am slow at arithmetic", NodeType.ABSTRACT)
    b = s.add_node("ordinary fact", NodeType.CONCEPT)
    s.designate_self(a)
    check(s.is_self(a) is True, "designated node is in the self-region")
    check(s.is_self(b) is False, "non-designated node is not")
    check(a in s.self_region(), "self_region() enumerates the designation")
    # removing a self node cleans the designation
    s.remove_node(a)
    check(a not in s.self_region(), "self-region cleaned on node removal")
    s.check_integrity()


def test_integrity_catches_nothing_when_clean():
    section("integrity scan passes on a healthy graph of moderate size")
    s = SubstrateStore(clock=Clock(simulated=True))
    ids = [s.add_node(f"n{i}", NodeType.CONCEPT) for i in range(50)]
    for i in range(49):
        s.traverse(ids[i], ids[i + 1], charge={"interest": 0.3})
    s.check_integrity()
    check(s.node_count() == 50 and s.road_count() == 49,
          "graph built cleanly (chain of 50 nodes, 49 roads)")


# ─────────────────────────────────────────────────────────────────────────────
# 0c — the ORDERING CONTRACT of the adjacency indices (SPEC-0c §2.2)
#
# `_out`/`_in` were `Set[RoadID]` over uuid4 hex strings, so `roads_from()` yielded
# in an order that is freshly random in every process. The store owns the ordering
# contract, so the store is where it is stated: the indices are insertion-ordered
# mappings used as ordered sets, and insertion order IS road-creation order IS
# program order. The intrinsic integer these tests assert against is `creation_seq`,
# never "the order I happened to add them in", so a coincidence cannot pass.
# ─────────────────────────────────────────────────────────────────────────────

def _out_seqs(s, node_id):
    """The creation_seq of each out-road, in the order roads_from yields them."""
    return [s.get_road(r, apply_decay=False).creation_seq for r in s.roads_from(node_id)]


def _in_seqs(s, node_id):
    return [s.get_road(r, apply_decay=False).creation_seq for r in s.roads_into(node_id)]


def _strictly_increasing(xs):
    return all(xs[i] < xs[i + 1] for i in range(len(xs) - 1))


def test_road_iteration_is_in_creation_order():
    section("0c: roads_from / roads_into yield in road-creation order (creation_seq)")
    s = SubstrateStore(clock=Clock(simulated=True))
    hub = s.add_node("hub", NodeType.CONCEPT)
    spokes = [s.add_node(f"spoke{i}", NodeType.CONCEPT) for i in range(8)]
    sink = s.add_node("sink", NodeType.CONCEPT)
    for sp in spokes:                      # hub fans OUT to 8 spokes
        s.add_road(hub, sp)
    for sp in spokes:                      # 8 spokes fan IN to one sink
        s.add_road(sp, sink)
    out = _out_seqs(s, hub)
    inn = _in_seqs(s, sink)
    check(len(out) == 8 and _strictly_increasing(out),
          f"roads_from(hub) yields 8 roads in strictly increasing creation_seq ({out})")
    check(len(inn) == 8 and _strictly_increasing(inn),
          f"roads_into(sink) yields 8 roads in strictly increasing creation_seq ({inn})")
    # repeated calls must agree with each other, not merely be internally sorted
    check(list(s.roads_from(hub)) == list(s.roads_from(hub)),
          "two consecutive roads_from() calls yield the identical sequence")
    check(list(s.roads_into(sink)) == list(s.roads_into(sink)),
          "two consecutive roads_into() calls yield the identical sequence")


def test_road_order_survives_a_mutation_battery():
    section("0c: order survives add/remove/re-add batteries (indices stay consistent)")
    import random
    rng = random.Random(20260726)
    s = SubstrateStore(clock=Clock(simulated=True))
    nodes = [s.add_node(f"n{i}", NodeType.CONCEPT) for i in range(12)]
    live = []
    out_violations = 0
    in_violations = 0
    integrity_failures = 0
    for step in range(400):
        act = rng.random()
        if act < 0.6 or not live:
            a, b = rng.sample(nodes, 2)
            rid = s.add_road(a, b)
            if rid not in live:
                live.append(rid)
        else:
            rid = live.pop(rng.randrange(len(live)))
            s.remove_road(rid)
        if step % 25 == 0:
            for n in nodes:
                if not _strictly_increasing(_out_seqs(s, n)):
                    out_violations += 1
                if not _strictly_increasing(_in_seqs(s, n)):
                    in_violations += 1
            try:
                s.check_integrity()
            except IntegrityError:
                integrity_failures += 1
    check(out_violations == 0,
          f"out-road order stayed creation-ordered through 400 mutations "
          f"({out_violations} violations)")
    check(in_violations == 0,
          f"in-road order stayed creation-ordered through 400 mutations "
          f"({in_violations} violations)")
    check(integrity_failures == 0,
          f"check_integrity() stayed clean through the battery ({integrity_failures} failures)")


def test_add_road_on_an_existing_pair_does_not_reorder():
    section("0c: add_road on an existing pair returns it and does NOT move it")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    d = s.add_node("d", NodeType.CONCEPT)
    r_ab = s.add_road(a, b)
    r_ac = s.add_road(a, c)
    r_ad = s.add_road(a, d)
    before = list(s.roads_from(a))
    again = s.add_road(a, b)          # get-or-add: must be a get
    check(again == r_ab, "add_road on an existing pair returns the existing road")
    check(list(s.roads_from(a)) == before,
          "and leaves the iteration order untouched (a re-get is not a re-insert)")
    check(before == [r_ab, r_ac, r_ad], "the order is the order the roads were created in")
    # traverse() is the biological get-or-add-then-strengthen; it must not reorder either
    s.traverse(a, b)
    check(list(s.roads_from(a)) == before,
          "traverse() on an existing road does not move it in the index")


def test_a_re_added_pair_is_a_new_road_that_sorts_last():
    section("0c: remove + re-add yields a NEW road, which sorts last")
    s = SubstrateStore(clock=Clock(simulated=True))
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    d = s.add_node("d", NodeType.CONCEPT)
    r_ab = s.add_road(a, b)
    r_ac = s.add_road(a, c)
    r_ad = s.add_road(a, d)
    s.remove_road(r_ab)
    check(list(s.roads_from(a)) == [r_ac, r_ad],
          "removing the first road leaves the survivors in their relative order")
    r_ab2 = s.add_road(a, b)
    check(r_ab2 != r_ab, "re-adding the same pair mints a NEW road id (identity is uuid4)")
    check(list(s.roads_from(a)) == [r_ac, r_ad, r_ab2],
          "and the new road sorts LAST — creation order, not pair order")
    check(_strictly_increasing(_out_seqs(s, a)),
          "creation_seq of the survivors + the new road is still strictly increasing")
    s.check_integrity()


def test_road_order_is_pure_and_identical_across_fresh_processes():
    section("0c: iteration order is a pure read and is identical in fresh processes")
    s = SubstrateStore(clock=Clock(simulated=True))
    hub = s.add_node("hub", NodeType.CONCEPT)
    tgts = [s.add_node(f"t{i}", NodeType.CONCEPT) for i in range(6)]
    for t in tgts:
        s.traverse(hub, t)
    # PURITY: reading the order must not change the order or the stored roads
    snap_before = [(r, s.get_road(r, apply_decay=False).strength,
                    s.get_road(r, apply_decay=False).last_touched)
                   for r in s.roads_from(hub)]
    for _ in range(5):
        list(s.roads_from(hub))
        list(s.neighbors(hub))
    snap_after = [(r, s.get_road(r, apply_decay=False).strength,
                   s.get_road(r, apply_decay=False).last_touched)
                  for r in s.roads_from(hub)]
    check(snap_before == snap_after,
          "repeated order reads mutate neither the order nor any stored road field")

    # CROSS-PROCESS: uuid4 ids differ per process, so an unordered set index yields a
    # different order in (almost) every process. Serialised by stable identity (content),
    # never by uuid, because uuids are regenerated per process by construction.
    import subprocess, sys, os, textwrap
    probe = textwrap.dedent('''
        from psyche_store import SubstrateStore, Clock, NodeType
        s = SubstrateStore(clock=Clock(simulated=True))
        hub = s.add_node("hub", NodeType.CONCEPT)
        tgts = [s.add_node("t%d" % i, NodeType.CONCEPT) for i in range(6)]
        for t in tgts:
            s.traverse(hub, t)
        order = [s.get_node(s.get_road(r, apply_decay=False).target_id).content
                 for r in s.roads_from(hub)]
        into = [s.get_node(s.get_road(r, apply_decay=False).source_id).content
                for r in s.roads_into(tgts[3])]
        print(repr((order, into)))
    ''')
    outs = []
    cwd = os.path.dirname(__file__) or "."
    for seed in ("0", "1", "2", "3", "7", "42"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        rr = subprocess.run([sys.executable, "-c", probe], cwd=cwd,
                            capture_output=True, text=True, env=env)
        if rr.returncode != 0:
            print("  (subprocess error)\n", rr.stderr)
        outs.append(rr.stdout.strip())
    check(len(set(outs)) == 1,
          f"out/in order identical across 6 fresh processes x hash seeds "
          f"(distinct outputs: {len(set(outs))}; saw {sorted(set(outs))[:1]})")


# ─────────────────────────────────────────────────────────────────────────────
# 0c §2.5 site 3 — Road.valence aggregates charges, and a CATEGORICAL closure
# decision is resolved on that aggregate. The project's float rule forbids
# deciding a category on an independently-accumulated float, so the aggregate
# has to be a function of the charge MULTISET and of nothing else.
# ─────────────────────────────────────────────────────────────────────────────

# One multiset of four feelings whose exact mean is exactly the closure threshold
# (-0.9 + -0.8 + -0.7 + -0.6) / 4 == -3.0 / 4 == -0.75. It is chosen for that
# property, not for its value: sitting exactly ON the threshold is what makes the
# last-ULP question a categorical question rather than a cosmetic one. The values
# are ordinary two-digit charges, not engineered denormals.
_STRADDLING_CHARGES = (("grief", -0.9), ("anger", -0.8), ("shame", -0.7), ("fear", -0.6))


def _road_with(charges):
    """A bare Road carrying `charges` in the given insertion order. Constructed
    directly rather than through strengthen(), so the ONLY thing varying between
    cases is the order the feelings were recorded in."""
    from psyche_store import Road
    r = Road(id="r", source_id="a", target_id="b", creation_seq=0,
             formation_time=0.0, last_touched=0.0)
    r.charges = dict(charges)
    return r


def test_0c_road_valence_is_order_independent_and_so_is_the_closure_decision():
    section("0c/§2.5 site 3: Road.valence — and therefore closure — depends on the "
            "charge MULTISET, never on the order the feelings were recorded in")
    import itertools
    import struct
    from psyche_store import _open_close_on_crossing, _CLOSURE_THRESHOLD

    def bits(x):
        return struct.pack("<d", x).hex()

    orders = list(itertools.permutations(_STRADDLING_CHARGES))   # 24 orders, ONE multiset

    # (a) THE PROPERTY. Same feelings, same intensities, recorded in any order → one
    #     valence, bit for bit. SPEC-0c §5.1: bit patterns, never round().
    seen = {bits(_road_with(o).valence) for o in orders}
    check(len(seen) == 1,
          f"valence is one bit pattern across all {len(orders)} charge insertion orders "
          f"(distinct = {len(seen)}: {sorted(seen)})")

    # (b) THE VACUITY WITNESS. (a) is only worth something if the invariance is not
    #     free. An EXPLICIT naive left-fold — written here, so it is the same arithmetic
    #     on every interpreter and does not depend on what builtin sum() happens to do —
    #     must genuinely disagree with itself across those same orders.
    def naive_mean(o):
        t = 0.0
        for _, v in o:
            t += v
        return t / max(1, len(o))

    naive_bits = {bits(naive_mean(o)) for o in orders}
    check(len(naive_bits) >= 2,
          f"a naive left-fold over the SAME multiset yields {len(naive_bits)} distinct "
          f"bit patterns, so (a)'s invariance is a property of the code and not of the "
          f"input ({sorted(naive_bits)})")

    # (c) THE CATEGORICAL CONSEQUENCE, and proof the flip was REACHABLE. Under the
    #     naive fold this multiset lands on BOTH sides of _CLOSURE_THRESHOLD depending
    #     on order — the road closes or does not close according to which feeling was
    #     written down first. That is the shape the float rule prohibits.
    naive_sides = {naive_mean(o) <= _CLOSURE_THRESHOLD for o in orders}
    check(naive_sides == {True, False},
          f"the naive fold does straddle the closure threshold on this input "
          f"(sides reached: {sorted(naive_sides)}) — the categorical flip is reachable, "
          f"not hypothetical")

    closed = set()
    for o in orders:
        r = _road_with(o)
        _open_close_on_crossing(r, one_shot_trauma=False)
        closed.add(r.closed)
    check(closed == {True},
          f"the real closure decision is the SAME in all {len(orders)} orders "
          f"(outcomes seen: {sorted(closed)})")


def test_0c_road_valence_is_identical_on_every_interpreter():
    section("0c/§2.5 site 3: the same charges give the same valence bits on every "
            "CPython on this machine")
    # The order axis and the interpreter axis are different failure classes. CPython
    # 3.12 changed builtin sum() to Neumaier compensated summation, so a naive float
    # sum returns different bits on 3.11 and 3.12 for a FIXED order — nothing else in
    # this suite can see that. Scoped honestly to interpreters on ONE machine: no
    # transcendental function is entered (no decay, frozen construction), so this is
    # pure IEEE-754 plus whatever summation semantics the interpreter supplies.
    import subprocess
    import sys
    import os
    import shutil
    import textwrap
    probe = textwrap.dedent('''
        import struct
        from psyche_store import Road, _open_close_on_crossing
        r = Road(id="r", source_id="a", target_id="b", creation_seq=0,
                 formation_time=0.0, last_touched=0.0)
        r.charges = {"grief": -0.9, "anger": -0.8, "shame": -0.7, "fear": -0.6}
        v = r.valence
        _open_close_on_crossing(r, one_shot_trauma=False)
        print(struct.pack("<d", v).hex(), r.closed)
    ''')
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
        rr = subprocess.run([py, "-c", probe], cwd=cwd, capture_output=True, text=True)
        outs[py] = rr.stdout.strip() if rr.returncode == 0 else f"ERROR {rr.stderr[-200:]}"
    for py, o in outs.items():
        print(f"    {os.path.basename(py):<12} {o}")
    check(len(set(outs.values())) == 1,
          f"identical valence bits and closure flag on {len(outs)} interpreters "
          f"(distinct = {len(set(outs.values()))})")


def run_all():
    print("=" * 70)
    print("  PSYCHE SUBSTRATE STORE — TEST SUITE (Layer 1)")
    print("=" * 70)
    for t in [
        test_identity_and_order,
        test_notfound_is_safe,
        test_one_road_per_pair,
        test_split_primitives,
        test_traverse_lays_path,
        test_strengthening_and_quality,
        test_multi_charge_road,
        test_lazy_decay,
        test_reads_are_pure,
        test_closure_is_sticky,
        test_clock_advance_is_simulated_only,
        test_pin_guard,
        test_deletion_leaves_no_dangling_index,
        test_self_region,
        test_integrity_catches_nothing_when_clean,
        # 0c — adjacency ordering contract
        test_road_iteration_is_in_creation_order,
        test_road_order_survives_a_mutation_battery,
        test_add_road_on_an_existing_pair_does_not_reorder,
        test_a_re_added_pair_is_a_new_road_that_sorts_last,
        test_road_order_is_pure_and_identical_across_fresh_processes,
        # 0c §2.5 site 3 — the charge aggregate under the closure decision
        test_0c_road_valence_is_order_independent_and_so_is_the_closure_decision,
        test_0c_road_valence_is_identical_on_every_interpreter,
    ]:
        t()
    print("\n" + "=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    print("=" * 70)
    return _failed == 0


if __name__ == "__main__":
    ok = run_all()
    raise SystemExit(0 if ok else 1)
