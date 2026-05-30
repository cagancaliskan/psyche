"""
Test suite for the Nous Substrate Store (Layer 1).

Each test exercises a specific Layer-1 decision. Run directly:
    python3 test_nous_store.py
A passing run prints a summary; any violation raises and stops.
"""

from nous_store import (
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


def run_all():
    print("=" * 70)
    print("  NOUS SUBSTRATE STORE — TEST SUITE (Layer 1)")
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
    ]:
        t()
    print("\n" + "=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    print("=" * 70)
    return _failed == 0


if __name__ == "__main__":
    ok = run_all()
    raise SystemExit(0 if ok else 1)
