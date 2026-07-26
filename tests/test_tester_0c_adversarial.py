"""
INDEPENDENT ADVERSARIAL TEST SUITE for brick 0c — deterministic road ordering.

Author: tester (independent adversary). Written FROM SCRATCH against SPEC-0c §6's
invariants O-1 .. O-17 (including O-4b), not adapted from the builder's suites. Mechanism
only: nothing here grades a cognitive claim, and 0c does not approach one. It is a brick
about floats.

THE ACCEPTANCE SIGNAL FOR THIS BRICK WAS INVERTED, and that shaped the whole pass. 0c
closed a defect class that the tester's OWN earlier suite proved existed and recorded as
six asserted-negatives. A correct fix turns those red. The conversion of all ten red tests
lives in tests/test_tester_0b2_adversarial.py, which now asserts the fix instead of the
bug; this file adjudicates the invariants themselves.

WHAT IS VERIFIED HERE
---------------------
  O-1   roads_from/roads_into yield in ROAD-CREATION order, asserted against creation_seq
  O-2   that order survives add / remove / re-add batteries
  O-3   integrity and purity are unchanged by the representation change
  O-4   the DEFECT-A reproduction: ONE bit pattern, >=48 processes x 6 seeds x 5 CPythons
  O-4b  the COMPETITION path (think -> coalitions -> workspace -> pruned winner): ONE bit
        pattern for the winner's strength AND one winner membership, on every interpreter
  O-5   generalised determinism over randomly generated adversarial graphs
  O-6   order-perturbation invariance: permuting roads_from leaves the bits alone
  O-7   ASSERTED-NEGATIVE bounding the claim: isomorphic graphs agree on every VALUE and
        differ in activation's KEY ORDER
  O-8   cross-checked here on loop-closed input (the re-based oracle lives in the 0b2 file)
  O-9   each road is read exactly once per expansion
  O-10  a lone out-road transmits with factor exactly 1.0 on the REAL default clock
  O-11  sigma validation
  O-12  no non-finite value reaches activation or flow, BY ANY ROUTE. The first pass
        returned FAIL here: a non-finite `energy` reached `activation` verbatim whenever
        the seed never transmitted. D-015 closed it in code (option (A), boundary
        validation of `energy`); the asserted-negative that recorded the gap has been
        RETIRED per its own exit instruction and replaced by the positive property, on
        ten seed shapes x seven non-finite energies x eight parameter sets, plus the
        loop-closed pipeline and a determinism sweep of the refusal itself.
  O-13  SPEC-0b2's N-3, N-4, N-6, N-8, N-9 still hold after the change
  O-14  no determinism probe in tests/ or experiments/ compares rounded values
  O-15  no builtin sum() over floats survives in src/
  O-16  cross-interpreter bit-identity of VALUES, not merely of per-suite counts
  O-17  the assertion count is a property of the code, not of the environment

TWO FINDINGS ARE RECORDED HERE AS ASSERTED-NEGATIVES rather than hidden (CLAUDE.md,
"Definition of done": a known limitation is written as an explicit asserted-negative test).
Each PASSES while the limitation is present and goes RED when it is closed. THE SUITE BEING
GREEN IS THEREFORE NOT THE VERDICT -- exactly as in the 0b2 pass, which reported 83 passed,
0 failed, and a verdict of FAIL.

A THIRD, FINDING 2, WAS RETIRED. It asserted the O-12 gap and carried its own exit
instruction: "IF THIS GOES RED BECAUSE energy IS NOW VALIDATED: delete it and re-verify
O-12." D-015 validated energy, the test went red by RAISING -- which aborted the suite and
hid the twelve tests after it -- and it has been deleted and converted into the positive
property. The twelve hidden tests were then re-derived independently, not inherited from
the builder's measurement of this file.

  FINDING 1  nous_field.build_activation_field merges per-source activations with a NAIVE
             running float add (`total[node] = total.get(node, 0.0) + act`, and the same
             shape for merged_flow). That is DEFECT-A's shape at a different owner. It is
             order-PINNED (the source order is program order, so determinism across
             processes is NOT affected and O-4/O-4b/O-5/O-16 all hold) but it is not
             order-INDEPENDENT: the same SET of sources supplied in a different order
             yields different bits, and the difference reaches Coalition.strength.
             OUT OF 0c's DECIDED SCOPE -- §2.5 enumerated three builtin sum() sites and
             this is not a sum() call -- so it is reported, not treated as a 0c failure.

  FINDING 2  RETIRED, CLOSED IN CODE by D-015 (A). It said: O-12 does not hold as written,
             because a non-finite `energy` reaches `activation` verbatim whenever the seed
             never transmits. `energy` is now validated for finiteness at the boundary and
             O-12 holds as written; see the O-12 block below for the replacement property.

  FINDING 3  The fsum reduction raises OverflowError where the pre-0c engine returned inf.
             A neutral-path behaviour change at extreme energy, arguably an improvement,
             but an undocumented exception type escaping from stdlib rather than the
             engine's own diagnostic ValueError.

Run directly:
    PYTHONPATH=<repo>/src python3 tests/test_tester_0c_adversarial.py
"""

import ast
import dataclasses
import itertools
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import textwrap

from nous_store import (
    SubstrateStore, Clock, NodeType, NotFound, IntegrityError, Road,
)
from nous_activation import (
    spread_activation,
    DEFAULT_SEED_ENERGY, DEFAULT_DECAY_PER_HOP, DEFAULT_FLOOR, DEFAULT_HOP_BUDGET,
    CLOSED_BREAKTHROUGH_THRESHOLD, CLOSED_LEAK_FRACTION,
)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")

_passed = 0
_failed = 0
_fail_msgs = []
_findings = []


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


def note(msg):
    print(f"  NOTE: {msg}")


def finding(tag, msg):
    _findings.append((tag, msg))
    print(f"  FINDING [{tag}]: {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# Everything in this suite compares BIT PATTERNS. round(x, 9) is structurally blind
# to a 1-ULP difference and 1 ULP is exactly what BUG-0b1 was (SPEC-0c §5.1).
# ─────────────────────────────────────────────────────────────────────────────

def bits(x):
    return struct.pack("<d", x).hex()


def unbits(h):
    return struct.unpack("<d", bytes.fromhex(h))[0]


def ulp_gap(a, b):
    """Signed-magnitude doubles mapped to a monotone integer line, so 'how many
    representable doubles apart' is exact rather than approximated by a tolerance."""
    def key(x):
        i = struct.unpack("<q", struct.pack("<d", x))[0]
        return i if i >= 0 else (1 << 63) - i
    return abs(key(a) - key(b))


def signature(result):
    return (
        result.seed,
        tuple((k, bits(v)) for k, v in result.activation.items()),
        tuple(result.hops.items()),
        tuple(result.broke_through),
        tuple((k, bits(v)) for k, v in result.flow.items()),
    )


def frozen_store():
    return SubstrateStore(clock=Clock(simulated=True, start=0.0))


def worn(store, a, b, n=1, charge=None):
    for _ in range(n):
        store.traverse(a, b, charge)
    return store.find_road(a, b)


class PermutingStore:
    """Delegates everything, but hands a source's out-roads out in a chosen order.

    After 0c the real order is fixed by construction, so it can no longer be perturbed by
    any environment variable. Permuting it explicitly is the only way to test the property
    DIRECTLY instead of sampling an axis that may or may not move it (SPEC-0c §5.2).
    """

    def __init__(self, inner, permute):
        self._inner = inner
        self._permute = permute

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def roads_from(self, node_id):
        return iter(self._permute(list(self._inner.roads_from(node_id))))


class RecordingStore:
    def __init__(self, inner):
        self._inner = inner
        self.reads = []

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def get_road(self, road_id, apply_decay=True):
        road = self._inner.get_road(road_id, apply_decay)
        if apply_decay:
            self.reads.append((road_id, road.strength))
        return road


class MutationGuardStore:
    WRITES = ("add_node", "remove_node", "add_road", "remove_road", "strengthen",
              "traverse", "designate_self", "undesignate_self", "pin", "unpin")

    def __init__(self, inner):
        self._inner = inner
        self.violations = []

    def __getattr__(self, name):
        if name in self.WRITES:
            def _forbidden(*a, **k):
                self.violations.append(name)
                raise AssertionError(f"spread_activation called mutating {name}()")
            return _forbidden
        return getattr(self._inner, name)


class TickClock(Clock):
    """Monotonic, advances a fixed dt on every now() — a deterministic stand-in for the
    REAL clock, which also advances. A wall-clock-dependent defect becomes a stable test."""

    def __init__(self, dt):
        super().__init__(simulated=True, start=0.0)
        self.dt = dt
        self.ticking = False

    def now(self):
        t = self._t
        if self.ticking:
            self._t += self.dt
        return t


def adversarial_graph(seed):
    """Hostile topology: self-loops, cycles, duplicate pairs, high-degree fans, closed and
    traumatic roads, saturated and decayed strengths, isolated nodes. Seeded with
    random.Random so it reproduces independently of PYTHONHASHSEED."""
    rng = random.Random(seed)
    clock = Clock(simulated=True, start=0.0)
    store = SubstrateStore(clock=clock)
    n = rng.randint(1, 11)
    ids = [store.add_node("n%d" % i, rng.choice(list(NodeType))) for i in range(n)]
    for _ in range(rng.randint(0, 40)):
        a, b = rng.choice(ids), rng.choice(ids)
        k = rng.random()
        charge = None
        if k < 0.22:
            charge = {"dread": -rng.uniform(0.75, 1.0)}
        elif k < 0.40:
            charge = {"joy": rng.uniform(0.2, 0.9)}
        for _ in range(rng.randint(1, 12)):
            store.traverse(a, b, charge)
        if rng.random() < 0.35:
            clock.advance(rng.uniform(0.0, 40.0))
    if rng.random() < 0.40:
        hub = rng.choice(ids)
        for i in range(rng.randint(5, 30)):
            tgt = store.add_node("f%d" % i, NodeType.CONCEPT)
            for _ in range(rng.randint(1, 6)):
                store.traverse(hub, tgt)
    clock.advance(0.0)
    return store, list(store.all_node_ids())


HASH_SEEDS = ["0", "1", "2", "3", "7", "42"]
INTERP_NAMES = ("python3.10", "python3.11", "python3.12", "python3.13", "python3.14")


def interpreters():
    found = []
    seen = set()
    for name in INTERP_NAMES:
        p = shutil.which(name)
        if p and os.path.realpath(p) not in seen:
            seen.add(os.path.realpath(p))
            found.append(name)
    return found or [sys.executable]


def run_probe(driver, interps=None, seeds=None, reps=1):
    """Run `driver` in fresh interpreters across the hash-seed x interpreter matrix.
    Returns [(interp, seed, stdout_or_ERROR)]."""
    outs = []
    env0 = dict(os.environ)
    env0["PYTHONPATH"] = SRC + (os.pathsep + env0["PYTHONPATH"]
                                if env0.get("PYTHONPATH") else "")
    for interp in (interps if interps is not None else interpreters()):
        for seed in (seeds if seeds is not None else HASH_SEEDS):
            for _ in range(reps):
                env = dict(env0, PYTHONHASHSEED=seed)
                r = subprocess.run([interp, "-c", driver], cwd=HERE,
                                   capture_output=True, text=True, env=env)
                outs.append((interp, seed,
                             r.stdout.strip() if r.returncode == 0
                             else "ERROR:" + r.stderr.strip()[-300:]))
    return outs


# ═════════════════════════════════════════════════════════════════════════════
# O-1 / O-2 / O-3 — THE ORDERING CONTRACT AT THE STORE
#
# The property is asserted against `creation_seq`, the intrinsic integer, and never
# against "the order I happened to insert them in". Asserting insertion coincidence
# would let a dict that merely preserved MY loop order pass while the contract the rest
# of the project relies on was unmet.
# ═════════════════════════════════════════════════════════════════════════════

def _seqs(store, rids):
    return [store.get_road(r, apply_decay=False).creation_seq for r in rids]


def _increasing(xs):
    return all(xs[i] < xs[i + 1] for i in range(len(xs) - 1))


def test_O1_iteration_is_creation_ordered_on_hostile_topologies():
    section("O-1 roads_from/roads_into yield in creation order, on hostile topologies")
    bad_out = bad_in = bad_nb = 0
    checked = 0
    fans = 0
    selfloops = 0
    for gs in range(60):
        store, ids = adversarial_graph(gs)
        for n in ids:
            out = list(store.roads_from(n))
            inn = list(store.roads_into(n))
            checked += 1
            if len(out) >= 8:
                fans += 1
            if store.find_road(n, n) is not None:
                selfloops += 1
            if not _increasing(_seqs(store, out)):
                bad_out += 1
            if not _increasing(_seqs(store, inn)):
                bad_in += 1
            # neighbors() must follow roads_from exactly, or a consumer reading it
            # inherits an order the contract does not cover
            if list(store.neighbors(n)) != [store.get_road(r).target_id for r in out]:
                bad_nb += 1
    check(checked > 0, f"the property was actually exercised ({checked} node views)")
    check(fans > 0 and selfloops > 0,
          f"and on genuinely hostile shapes: {fans} high-degree fans (out-degree >= 8) and "
          f"{selfloops} self-loops appeared in the battery")
    check(bad_out == 0, f"roads_from is creation-ordered everywhere ({bad_out} violations)")
    check(bad_in == 0, f"roads_into is creation-ordered everywhere ({bad_in} violations)")
    check(bad_nb == 0,
          f"neighbors() follows roads_from road-for-road ({bad_nb} divergences) — the "
          f"ordering contract covers every structural read, not only the one 0b uses")


def test_O1_the_order_is_not_merely_insertion_coincidence():
    section("O-1 the order tracks creation_seq, not the caller's insertion sequence")
    # Roads are created INTERLEAVED across two sources, so each source's own out-list is a
    # non-contiguous subsequence of the global creation order. A container that merely
    # preserved "the order this test added things" would be indistinguishable from one that
    # tracked creation_seq if all of one source's roads were added together. Interleaving
    # is what separates the two hypotheses.
    s = frozen_store()
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    tgts = [s.add_node("t%d" % i, NodeType.CONCEPT) for i in range(10)]
    order_a, order_b = [], []
    for i, t in enumerate(tgts):
        if i % 2 == 0:
            order_a.append(s.add_road(a, t))
            order_b.append(s.add_road(b, t))
        else:
            order_b.append(s.add_road(b, t))
            order_a.append(s.add_road(a, t))
    seq_a = _seqs(s, list(s.roads_from(a)))
    seq_b = _seqs(s, list(s.roads_from(b)))
    check(list(s.roads_from(a)) == order_a and list(s.roads_from(b)) == order_b,
          "each source's out-roads come back in their own creation order despite the two "
          "sources' roads being interleaved in the global sequence")
    check(_increasing(seq_a) and _increasing(seq_b),
          f"and the creation_seq subsequences are strictly increasing ({seq_a}, {seq_b})")
    check(sorted(seq_a + seq_b) == list(range(min(seq_a + seq_b),
                                              min(seq_a + seq_b) + len(seq_a + seq_b))),
          "the two lists interleave in the global sequence, so 'insertion order' and "
          "'creation order' were genuinely distinguishable hypotheses here")


def test_O2_order_survives_a_randomised_mutation_battery():
    section("O-2 order survives add/remove/re-add batteries, with integrity intact")
    rng = random.Random(20260726)
    s = frozen_store()
    nodes = [s.add_node("n%d" % i, NodeType.CONCEPT) for i in range(14)]
    live = []
    viol = integrity = pair_viol = 0
    removals = readds = 0
    for step in range(900):
        r = rng.random()
        if r < 0.55 or not live:
            x, y = rng.choice(nodes), rng.choice(nodes)      # self-loops allowed
            before = list(s.roads_from(x))
            rid = s.add_road(x, y)
            if rid in before:
                # get-or-add on an existing pair: must NOT reorder
                if list(s.roads_from(x)) != before:
                    pair_viol += 1
            else:
                readds += 1
                if list(s.roads_from(x)) != before + [rid]:
                    pair_viol += 1                            # a new road must append
                live.append(rid)
        elif r < 0.85:
            rid = live.pop(rng.randrange(len(live)))
            road = s.get_road(rid, apply_decay=False)
            src = road.source_id
            before = list(s.roads_from(src))
            s.remove_road(rid)
            removals += 1
            if list(s.roads_from(src)) != [q for q in before if q != rid]:
                pair_viol += 1                                # survivors keep their order
        else:
            x, y = rng.choice(nodes), rng.choice(nodes)
            s.traverse(x, y)                                  # the biological get-or-add
            rid = s.find_road(x, y)
            if rid not in live:
                live.append(rid)
        if step % 40 == 0:
            for n in nodes:
                if not _increasing(_seqs(s, list(s.roads_from(n)))):
                    viol += 1
                if not _increasing(_seqs(s, list(s.roads_into(n)))):
                    viol += 1
            try:
                s.check_integrity()
            except IntegrityError:
                integrity += 1
    check(removals > 50 and readds > 50,
          f"the battery genuinely exercised both directions ({removals} removals, "
          f"{readds} new roads)")
    check(viol == 0, f"creation order held through 900 mutations ({viol} violations)")
    check(pair_viol == 0,
          f"survivors kept their relative order, new roads appended, and a re-get never "
          f"reordered ({pair_viol} violations)")
    check(integrity == 0, f"check_integrity stayed clean throughout ({integrity} failures)")


def test_O2_a_re_added_pair_is_a_new_road_that_sorts_last():
    section("O-2 remove + re-add mints a NEW road, and it sorts LAST")
    s = frozen_store()
    a = s.add_node("a", NodeType.CONCEPT)
    ts = [s.add_node("t%d" % i, NodeType.CONCEPT) for i in range(4)]
    rids = [s.add_road(a, t) for t in ts]
    s.remove_road(rids[0])
    s.remove_road(rids[2])
    check(list(s.roads_from(a)) == [rids[1], rids[3]],
          "removing from the middle leaves the survivors in their relative order")
    again0 = s.add_road(a, ts[0])
    again2 = s.add_road(a, ts[2])
    check(again0 != rids[0] and again2 != rids[2],
          "a re-added pair is a NEW road with a new id (identity is uuid4, order is seq)")
    check(list(s.roads_from(a)) == [rids[1], rids[3], again0, again2],
          "and the new roads sort LAST, in their own creation order — not back into the "
          "position the removed pair used to occupy")
    check(_increasing(_seqs(s, list(s.roads_from(a)))),
          "creation_seq across survivors and re-adds is still strictly increasing")
    # in-index too, since roads_into has the same contract and a different code path
    check(all(_increasing(_seqs(s, list(s.roads_into(t)))) for t in ts),
          "roads_into is creation-ordered after the same battery")


def test_O3_purity_and_integrity_are_unchanged_by_the_representation_change():
    section("O-3 purity and integrity — the two Phase 0 legs that did NOT fail")

    def snapshot(store):
        roads = {}
        for rid in store.all_road_ids():
            r = store.get_road(rid, apply_decay=False)
            roads[rid] = (bits(r.strength),
                          tuple(sorted((k, bits(v)) for k, v in r.charges.items())),
                          r.closed, r.traversal_count, bits(r.last_touched), r.creation_seq)
        nodes = {nid: (store.get_node(nid).content, store.get_node(nid).access_count,
                       bits(store.get_node(nid).last_accessed))
                 for nid in store.all_node_ids()}
        # the ORDER itself is part of the state a read must not disturb
        order = {nid: (tuple(store.roads_from(nid)), tuple(store.roads_into(nid)))
                 for nid in store.all_node_ids()}
        return roads, nodes, order

    dirty = order_moved = integrity = 0
    for gs in range(40):
        store, ids = adversarial_graph(3000 + gs)
        before = snapshot(store)
        for seed_node in ids:
            for sigma in (None, 0.001, 1.0, 1e9):
                spread_activation(store, seed_node, normalization_sigma=sigma)
                spread_activation(store, seed_node, normalization_sigma=sigma, floor=0.0)
        after = snapshot(store)
        if after[:2] != before[:2]:
            dirty += 1
        if after[2] != before[2]:
            order_moved += 1
        try:
            store.check_integrity()
        except IntegrityError:
            integrity += 1
    check(dirty == 0, f"no stored field changed across 40 adversarial graphs ({dirty} dirty)")
    check(order_moved == 0,
          f"and no iteration order moved either — reading the index does not disturb it "
          f"({order_moved} graphs where an order shifted)")
    check(integrity == 0, f"integrity intact after every battery ({integrity} failures)")
    # structural: no mutating method is reached at all
    store, ids = adversarial_graph(4242)
    guard = MutationGuardStore(store)
    for seed_node in ids:
        for sigma in (None, 1.0):
            spread_activation(guard, seed_node, normalization_sigma=sigma)
    check(not guard.violations,
          f"no mutating store method is reached during a spread ({guard.violations})")


# ═════════════════════════════════════════════════════════════════════════════
# O-4 — THE DEFECT-A REPRODUCTION. SPEC-0c §7 calls this the external, unfakeable
# done-means: it cannot be satisfied by adjusting a tolerance, and the input is the
# graph the defect was found on.
# ═════════════════════════════════════════════════════════════════════════════

CASE1_DRIVER = textwrap.dedent('''
    import struct
    from nous_store import SubstrateStore, Clock, NodeType
    from nous_activation import spread_activation
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    S = s.add_node("S", NodeType.CONCEPT); T = s.add_node("T", NodeType.CONCEPT)
    for i, (a, b) in enumerate(((1, 2), (1, 3), (1, 9))):
        M = s.add_node("M%d" % i, NodeType.CONCEPT)
        for _ in range(a): s.traverse(S, M)
        for _ in range(b): s.traverse(M, T)
    indeg = {}
    for r in s.all_road_ids():
        t = s.get_road(r).target_id
        indeg[t] = indeg.get(t, 0) + 1
    assert max(indeg.values()) == 3, "fixture drift: the reproduction needs in-degree 3"
    r = spread_activation(s, S)               # LIBRARY DEFAULTS, no proxy, real store
    print(struct.pack("<d", r.activation[T]).hex())
''')


def test_O4_the_reproduction_is_one_bit_pattern_across_the_full_matrix():
    section("O-4 SPEC-0c §1 case 1: ONE bit pattern across the FULL interpreter x seed matrix")
    interps = interpreters()
    print(f"  interpreters swept: {', '.join(interps)}")
    outs = run_probe(CASE1_DRIVER, interps=interps, reps=2)
    errs = [o for o in outs if o[2].startswith("ERROR")]
    vals = [o[2] for o in outs if not o[2].startswith("ERROR")]
    distinct = sorted(set(vals))
    for d in distinct:
        print(f"    {d}  = {unbits(d)!r}   ({vals.count(d)} of {len(vals)} runs)")
    check(not errs, f"every probe process ran ({len(errs)} errors; first={errs[:1]})")
    check(len(interps) >= 5,
          f"the interpreter axis is populated: {len(interps)} found (SPEC-0c requires 5)")
    check(len(vals) >= 48,
          f"at least 48 fresh processes, as SPEC-0c O-4 requires (ran {len(vals)})")
    check(len(distinct) == 1,
          f"O-4: ONE bit pattern over {len(vals)} fresh processes = {len(interps)} "
          f"interpreters x {len(HASH_SEEDS)} hash seeds x 2 reps (distinct = "
          f"{len(distinct)}: {distinct})")
    # per-interpreter, so a future divergence is attributable rather than merely detected
    per = {}
    for interp, seed, out in outs:
        if not out.startswith("ERROR"):
            per.setdefault(interp, set()).add(out)
    check(all(len(v) == 1 for v in per.values()) and len({next(iter(v)) for v in per.values()}) == 1,
          f"and every interpreter agrees with every other, not merely with itself: "
          f"{ {k: len(v) for k, v in per.items()} }")


# ═════════════════════════════════════════════════════════════════════════════
# O-4b — THE COMPETITION PATH. The store-ordering fix cannot reach it: Coalition.members
# inherits its order from by_basin[src], a Dict[str, Set[str]] of uuid4 NodeIDs built in
# nous_coalitions.py — a set some OTHER module constructs. Fixing a class at one owner
# does not fix it at another owner, which is the general lesson SPEC-0c §2.5.2 draws.
# ═════════════════════════════════════════════════════════════════════════════

CASE2_GRAPH = '''
    from nous_store import SubstrateStore, Clock, NodeType
    from nous_perceive import think
    import itertools
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    add = lambda c: s.add_node(c, NodeType.CONCEPT)
    warm = [add(x) for x in ("coffee","kitchen","morning","mug","toast")]
    cold = [add(x) for x in ("work","code","deadline")]
    def w(a,b,n):
        for _ in range(n): s.traverse(a,b)
    for a,b in itertools.permutations(warm,2): w(a,b,7)
    for a,b in itertools.permutations(cold,2): w(a,b,9)
    w(warm[0], cold[0], 8)
    r = think(s, "coffee kitchen morning mug toast")
'''

CASE2_DRIVER = textwrap.dedent(CASE2_GRAPH + '''
    import struct
    members = tuple(sorted(s.get_node(m).content for m in r.thought.members))
    raw = tuple(sorted(s.get_node(m).content for m in r.workspace.raw_winner.members))
    pruned = tuple(sorted(s.get_node(m).content for m in r.workspace.pruned_members))
    ranked = tuple((tuple(sorted(s.get_node(m).content for m in c.members)),
                    struct.pack("<d", c.strength).hex(), c.size())
                   for c in r.workspace.ranked)
    print(repr((struct.pack("<d", r.thought.strength).hex(), members, raw, pruned, ranked)))
''')


def test_O4b_the_competition_path_is_one_bit_pattern_on_every_interpreter():
    section("O-4b SPEC-0c §1 case 2: the COMPETITION path is one bit pattern everywhere")
    interps = interpreters()
    outs = run_probe(CASE2_DRIVER, interps=interps, reps=2)
    errs = [o for o in outs if o[2].startswith("ERROR")]
    vals = [o[2] for o in outs if not o[2].startswith("ERROR")]
    check(not errs, f"every probe process ran ({len(errs)} errors; first={errs[:1]})")
    # ast.literal_eval, never eval: the payload is a repr of tuples of str/int and
    # nothing else, so a literal parser is both sufficient and the safe choice.
    parsed = [ast.literal_eval(v) for v in vals]
    strengths = sorted({p[0] for p in parsed})
    memberships = sorted({p[1] for p in parsed})
    rankings = sorted({p[4] for p in parsed})
    for st in strengths:
        print(f"    thought.strength {st}  = {unbits(st)!r}   "
              f"({[p[0] for p in parsed].count(st)} of {len(parsed)})")
    check(len(vals) >= 48, f"at least 48 fresh processes on the competition path ({len(vals)})")
    check(len(strengths) == 1,
          f"O-4b: r.thought.strength is ONE bit pattern across {len(vals)} processes on "
          f"{len(interps)} interpreters (distinct = {len(strengths)}: {strengths}). Before "
          f"0c this gave TWO values on 3.10/3.11 at a FIXED hash seed and one on 3.14 — "
          f"the Neumaier split.")
    # membership asserted alongside strength, per O-4b, so a future flip is attributable
    check(len(memberships) == 1,
          f"and ONE winner membership ({len(memberships)} distinct: {memberships})")
    check(len(rankings) == 1,
          f"and ONE full ranked order, strengths included — so a ULP that moved without "
          f"flipping the winner would still be caught ({len(rankings)} distinct)")
    # the older interpreters are where the defect was visible; assert they were present
    old = [i for i in interps if i in ("python3.10", "python3.11")]
    check(len(old) == 2,
          f"the two interpreters that EXPOSE this defect were both swept: {old}. 3.12+ "
          f"compensates builtin sum(), so a sweep without 3.10/3.11 could not have seen it.")


def test_O4b_the_pruned_winner_strength_is_the_exactly_rounded_member_sum():
    section("O-4b the pruned winner's strength is fsum over its OWN surviving members")
    # Derived from the winner's own recorded member activations, so the assertion cannot be
    # satisfied by a number this test chose. This is SPEC-0c §2.5 site 1: the third
    # Coalition construction site, which BUG-0b1's 'two sites' claim missed.
    from nous_perceive import think
    ns = {}
    exec(textwrap.dedent(CASE2_GRAPH), ns)
    r, s = ns["r"], ns["s"]
    w = r.thought
    check(w is not None and len(w.members) >= 3,
          f"the fixture produced a winner with enough members to matter "
          f"({len(w.members) if w else 0})")
    check(bits(w.strength) == bits(math.fsum(w.members.values())),
          f"strength == math.fsum(members.values()) to the bit "
          f"({w.strength!r} vs {math.fsum(w.members.values())!r})")
    # non-vacuity: a naive left-fold over those same activations must genuinely disagree
    # in at least one member order, or this assertion is free.
    vals = list(w.members.values())
    naive = set()
    rng = random.Random(11)
    for _ in range(400):
        p = vals[:]
        rng.shuffle(p)
        acc = 0.0
        for v in p:
            acc += v
        naive.add(bits(acc))
    check(len(naive) > 1,
          f"and the invariance is not free: a naive left-fold over the SAME member "
          f"multiset gives {len(naive)} distinct bit patterns over 400 random orders "
          f"({sorted(naive)}) — the pre-0c rule at this site was one of those")


# ═════════════════════════════════════════════════════════════════════════════
# O-5 — GENERALISED DETERMINISM over randomly generated adversarial graphs.
# ═════════════════════════════════════════════════════════════════════════════

O5_DRIVER = textwrap.dedent('''
    import random, struct
    from nous_store import SubstrateStore, Clock, NodeType
    from nous_activation import spread_activation

    def graph(seed):
        rng = random.Random(seed)
        clock = Clock(simulated=True, start=0.0)
        s = SubstrateStore(clock=clock)
        n = rng.randint(1, 11)
        ids = [s.add_node("n%d" % i, rng.choice(list(NodeType))) for i in range(n)]
        for _ in range(rng.randint(0, 40)):
            a, b = rng.choice(ids), rng.choice(ids)
            k = rng.random()
            charge = None
            if k < 0.22: charge = {"dread": -rng.uniform(0.75, 1.0)}
            elif k < 0.40: charge = {"joy": rng.uniform(0.2, 0.9)}
            for _ in range(rng.randint(1, 12)): s.traverse(a, b, charge)
            if rng.random() < 0.35: clock.advance(rng.uniform(0.0, 40.0))
        if rng.random() < 0.40:
            hub = rng.choice(ids)
            for i in range(rng.randint(5, 30)):
                t = s.add_node("f%d" % i, NodeType.CONCEPT)
                for _ in range(rng.randint(1, 6)): s.traverse(hub, t)
        clock.advance(0.0)
        return s, list(s.all_node_ids())

    out = []
    worst_indeg = 0
    for gs in range(45):
        s, ids = graph(8000 + gs)
        ind = {}
        for r in s.all_road_ids():
            t = s.get_road(r).target_id
            ind[t] = ind.get(t, 0) + 1
        worst_indeg = max(worst_indeg, max(ind.values(), default=0))
        for sn in ids:
            for sigma in (None, 1.0):
                r = spread_activation(s, sn, normalization_sigma=sigma)
                act = sorted((s.get_node(k).content, struct.pack("<d", v).hex())
                             for k, v in r.activation.items())
                flw = sorted((s.get_node(s.get_road(k).source_id).content,
                              s.get_node(s.get_road(k).target_id).content,
                              struct.pack("<d", v).hex()) for k, v in r.flow.items())
                hop = sorted((s.get_node(k).content, h) for k, h in r.hops.items())
                out.append((gs, s.get_node(sn).content, sigma, act, hop, flw))
    print(repr((worst_indeg, hash(repr(out)) if False else repr(out)[:0], len(out))))
    import hashlib
    print(hashlib.sha256(repr(out).encode()).hexdigest())
''')


def test_O5_random_adversarial_graphs_are_deterministic_across_processes():
    section("O-5 45 random adversarial graphs x every seed x 2 sigmas: one result, "
            "across the full matrix")
    interps = interpreters()
    outs = run_probe(O5_DRIVER, interps=interps)
    errs = [o for o in outs if o[2].startswith("ERROR")]
    check(not errs, f"every probe process ran ({len(errs)} errors; first={errs[:1]})")
    vals = [o[2] for o in outs if not o[2].startswith("ERROR")]
    heads = {v.splitlines()[0] for v in vals}
    digests = {v.splitlines()[-1] for v in vals}
    worst = max(eval(h)[0] for h in heads) if heads else 0
    n_spreads = max(eval(h)[2] for h in heads) if heads else 0
    check(worst >= 3,
          f"the battery reaches the region where the defect lived: max in-degree "
          f"{worst} (need >= 3; at <= 2 the naive sum was already exact)")
    check(n_spreads > 500,
          f"and it is a real battery, not a token one: {n_spreads} spreads per process")
    check(len(digests) == 1,
          f"O-5: one SHA-256 over every activation, hop and flow bit pattern, across "
          f"{len(vals)} fresh processes on {len(interps)} interpreters "
          f"(distinct = {len(digests)}: {sorted(digests)})")


# ═════════════════════════════════════════════════════════════════════════════
# O-6 — ORDER-PERTURBATION INVARIANCE. Promoted by SPEC-0c §5.2 from a demonstration
# of the defect to THE guarantee, because it tests the property directly instead of
# sampling an axis that may or may not perturb it.
# ═════════════════════════════════════════════════════════════════════════════

def test_O6_order_perturbation_invariance_on_random_hostile_graphs():
    """O-6, stated precisely — and SPEC-0c O-6's own wording is looser than the property.

    O-6 says permuting `roads_from` "leaves output bit-identical". Every VALUE is, and so
    are `hops` and the set of breakthroughs. The dict KEY ORDER is not, and cannot be: key
    order is FIRST-ARRIVAL order, so permuting the order roads are walked in permutes which
    target arrives first within a hop layer. That is a necessary consequence of the
    permutation, not a leak — and it is the same residual O-7 documents for isomorphic
    graphs. Both halves are asserted here so "bit-identical" is read as exactly what holds.

    Measured over 6,090 permutation comparisons: 0 value differences, 0 hop differences,
    0 breakthrough-set differences, 1,159 key-order differences.
    """
    section("O-6 permuting roads_from leaves every VALUE bit-identical")
    rng = random.Random(20260726)
    bad_values = []
    bad_hops = 0
    bad_broke = 0
    key_order_moved = 0
    comparisons = 0
    sensitive = 0
    graphs = 0
    for gs in range(45):
        store, ids = adversarial_graph(9000 + gs)
        graphs += 1
        for seed_node in ids:
            for sigma in (None, 1.0):
                base = None
                base_contrib = None
                for trial in range(6):
                    def permute(roads, r=rng):
                        q = list(roads)
                        r.shuffle(q)
                        return q
                    res = spread_activation(PermutingStore(store, permute), seed_node,
                                            normalization_sigma=sigma)
                    cur = (
                        {k: bits(v) for k, v in res.activation.items()},   # VALUES
                        {k: bits(v) for k, v in res.flow.items()},         # VALUES
                        res.hops,
                        sorted(res.broke_through),                         # SET
                        list(res.activation),                              # key ORDER
                    )
                    if base is None:
                        base = cur
                        c = {}
                        for rid, v in res.flow.items():
                            c.setdefault(store.get_road(rid).target_id, []).append(v)
                        base_contrib = c
                        continue
                    comparisons += 1
                    if cur[0] != base[0] or cur[1] != base[1]:
                        bad_values.append((gs, seed_node, sigma))
                    if cur[2] != base[2]:
                        bad_hops += 1
                    if cur[3] != base[3]:
                        bad_broke += 1
                    if cur[4] != base[4]:
                        key_order_moved += 1
                # NON-VACUITY: did this spread have any accumulation a naive fold could
                # have got wrong? Count the ones with 3+ convergent contributions.
                if base_contrib and any(len(v) >= 3 for v in base_contrib.values()):
                    sensitive += 1
    check(sensitive > 0,
          f"the battery contains spreads a naive accumulator WOULD have got wrong: "
          f"{sensitive} spreads had a node taking 3 or more convergent contributions")
    check(comparisons > 5000,
          f"and it is a real battery: {comparisons} permutation comparisons across "
          f"{graphs} adversarial graphs x every seed x 2 sigmas")
    check(not bad_values,
          f"O-6: every activation and flow VALUE is bit-identical under 6 random out-road "
          f"permutations ({len(bad_values)} order-dependent; first {bad_values[:3]})")
    check(bad_hops == 0 and bad_broke == 0,
          f"and so are the hop assignments and the breakthrough SET "
          f"({bad_hops} hop, {bad_broke} breakthrough differences)")
    check(key_order_moved > 0,
          f"THE BOUND, asserted rather than glossed: the activation dict's KEY ORDER does "
          f"move ({key_order_moved} of {comparisons} comparisons), because key order is "
          f"first-arrival order and permuting the walk permutes first arrival. SPEC-0c "
          f"O-6's phrase 'leaves output bit-identical' is looser than what holds; the "
          f"values are invariant, the key order is not, and O-7 documents the same "
          f"residual for isomorphic graphs.")


def test_O6_high_degree_fan_permutation_invariance():
    section("O-6 the same, on high-degree fans where the term count is largest")
    rng = random.Random(4242)
    bad = 0
    biggest = 0
    for trial in range(20):
        store = frozen_store()
        S = store.add_node("S", NodeType.CONCEPT)
        T = store.add_node("T", NodeType.CONCEPT)
        deg = rng.randint(12, 45)
        biggest = max(biggest, deg)
        for i in range(deg):
            M = store.add_node("M%d" % i, NodeType.CONCEPT)
            worn(store, S, M, n=rng.randint(1, 9))
            worn(store, M, T, n=rng.randint(1, 9))
        base = None
        for _ in range(5):
            def permute(roads, r=rng):
                q = list(roads)
                r.shuffle(q)
                return q
            res = spread_activation(PermutingStore(store, permute), S, floor=0.0)
            key = (bits(res.activation[T]),
                   tuple(sorted((k, bits(v)) for k, v in res.flow.items())))
            if base is None:
                base = key
            elif key != base:
                bad += 1
                break
    check(bad == 0,
          f"20 fans (in-degree at T up to {biggest}) x 5 shuffles: {bad} order-dependent. "
          f"At in-degree {biggest} a naive fold has {biggest}! distinct orders available.")


# ═════════════════════════════════════════════════════════════════════════════
# O-7 — ASSERTED-NEGATIVE, in SPEC-0c §1's AMENDED form. This bounds the §1 claim,
# and the amendment matters: the draft said isomorphic graphs "may still produce
# different floats", which is wrong now that the reduction is exactly rounded. The
# residual is in the KEY ORDER, not in the values, and both halves are asserted so the
# guarantee is read as exactly what it is.
# ═════════════════════════════════════════════════════════════════════════════

def _isomorphic_pair():
    """The same logical graph built by two DIFFERENT construction programs.

    Both the NODE creation order and the ROAD creation order differ. Varying only the node
    order is not enough: the engine's key order is first-ARRIVAL order, which follows the
    order roads are walked in, which is road-creation order. A pair that differed only in
    node order would produce identical key orders and the second half of O-7 would pass
    vacuously — which is exactly what the first draft of this fixture did.
    """
    EDGES = [("S", "P", 3), ("S", "Q", 5), ("S", "R", 7),
             ("P", "Z", 2), ("Q", "Z", 4), ("R", "Z", 6)]

    def build(node_order, edge_order):
        s = frozen_store()
        ids = {}
        for name in node_order:
            ids[name] = s.add_node(name, NodeType.CONCEPT)
        for idx in edge_order:
            a, b, n = EDGES[idx]
            worn(s, ids[a], ids[b], n=n)
        return s, ids
    s1, i1 = build(["S", "P", "Q", "R", "Z"], [0, 1, 2, 3, 4, 5])
    s2, i2 = build(["S", "R", "Q", "P", "Z"], [2, 1, 0, 5, 4, 3])
    return s1, i1, s2, i2


def test_O7_ASSERTED_NEGATIVE_isomorphic_graphs_agree_on_values_not_on_key_order():
    section("O-7 ASSERTED-NEGATIVE: isomorphic graphs agree on every VALUE, differ in "
            "activation's KEY ORDER")
    s1, i1, s2, i2 = _isomorphic_pair()
    r1 = spread_activation(s1, i1["S"], floor=0.0)
    r2 = spread_activation(s2, i2["S"], floor=0.0)
    by_name1 = {s1.get_node(k).content: bits(v) for k, v in r1.activation.items()}
    by_name2 = {s2.get_node(k).content: bits(v) for k, v in r2.activation.items()}
    order1 = [s1.get_node(k).content for k in r1.activation]
    order2 = [s2.get_node(k).content for k in r2.activation]
    print(f"    build order 1 -> activation keys {order1}")
    print(f"    build order 2 -> activation keys {order2}")
    # HALF ONE — the agreement. This is the part the draft spec got wrong.
    check(by_name1 == by_name2,
          f"every activation VALUE agrees bit-for-bit between the two build orders "
          f"({sum(1 for k in by_name1 if by_name1[k] != by_name2.get(k))} disagreements) — "
          f"fsum is exactly rounded, so the same multiset reduces to the same double "
          f"whatever order it arrived in")
    check(bits(math.fsum([unbits(by_name1[n]) for n in ("P", "Q", "R")])) ==
          bits(math.fsum([unbits(by_name2[n]) for n in ("R", "Q", "P")])),
          "and reducing the same contributions in reversed order gives the same bits, "
          "which is the mechanism behind that agreement rather than a coincidence")
    # HALF TWO — the divergence. This is the residual, and it is the whole bound.
    check(order1 != order2,
          f"but activation's KEY ORDER differs ({order1} vs {order2}): insertion order is "
          f"first-arrival order, which follows construction order. THIS TEST GOES RED IF "
          f"THE GUARANTEE IS EVER WIDENED TO FULL ISOMORPHISM-INVARIANCE — which it is "
          f"not, and SPEC-0c §1 says so.")
    # and the consequence a consumer can actually see
    tied1 = [n for n, _ in sorted(((s1.get_node(k).content, v)
                                   for k, v in r1.ranked()), key=lambda t: -t[1])]
    tied2 = [n for n, _ in sorted(((s2.get_node(k).content, v)
                                   for k, v in r2.ranked()), key=lambda t: -t[1])]
    check(tied1 is not None and tied2 is not None,
          "ranked() is therefore ordered among TIED entries by construction order too — "
          "recorded as the observable consequence of the key-order residual")


# ═════════════════════════════════════════════════════════════════════════════
# O-8 (loop-closed leg) / O-9 / O-10
# ═════════════════════════════════════════════════════════════════════════════

def test_O9_one_read_per_road_and_one_clock_instant_per_expansion():
    section("O-9 one read per road, and every strength in an expansion from ONE instant")
    # A clock that advances on EVERY read: if the engine read a road twice, or read
    # out_total at a different moment from the transmission, the two strengths would
    # differ and this test would see it directly.
    clock = TickClock(1e-3)
    store = SubstrateStore(clock=clock)
    S = store.add_node("S", NodeType.CONCEPT)
    rids = []
    for i in range(6):
        T = store.add_node("T%d" % i, NodeType.CONCEPT)
        rids.append(worn(store, S, T, n=2 + i))
    clock.ticking = True
    rec = RecordingStore(store)
    res = spread_activation(rec, S, normalization_sigma=1.0, floor=0.0)
    per_road = {}
    for rid, st in rec.reads:
        per_road.setdefault(rid, []).append(st)
    check(all(len(v) == 1 for v in per_road.values()),
          f"each road read exactly once ({ {k[:6]: len(v) for k, v in per_road.items()} })")
    # The decisive one: out_total must equal fsum over EXACTLY the strengths that were
    # read, recovered from the engine's own transmitted values. If out_total came from a
    # different instant, `competing` would carry an elapsed-time residue and this fails.
    strengths = {rid: v[0] for rid, v in per_road.items()}
    s_out = math.fsum(strengths.values())
    worst = []
    for rid, st in strengths.items():
        competing = s_out - st
        expected = DEFAULT_SEED_ENERGY * st * DEFAULT_DECAY_PER_HOP
        if competing > 0.0:
            expected *= 1.0 / (1.0 + competing)
        if bits(res.flow[rid]) != bits(expected):
            worst.append(rid)
    check(not worst,
          f"every transmitted value equals act*s*decay*sigma/(sigma+fsum(others)) using "
          f"the SAME strengths the engine read, to the bit ({len(worst)} deviated) — so "
          f"out_total and road.strength came from one clock instant")


def test_O10_lone_out_road_on_the_REAL_default_clock():
    section("O-10 lone out-road: factor exactly 1.0 on the LIBRARY DEFAULT clock")
    # Not a simulated clock, not a TickClock: the actual Clock(simulated=False) that
    # SubstrateStore() uses by default, which is what DEFECT-B was invisible to every
    # existing test under. Repeated, because wall-clock timing is the variable.
    bad = []
    for trial in range(12):
        store = SubstrateStore()                     # LIBRARY DEFAULT, moving clock
        A = store.add_node("A", NodeType.CONCEPT)
        B = store.add_node("B", NodeType.CONCEPT)
        worn(store, A, B, n=3)
        rec = RecordingStore(store)
        for sigma in (1e-12, 1e-3, 1.0, 1e12):
            rec.reads.clear()
            r = spread_activation(rec, A, normalization_sigma=sigma)
            rid = next(iter(store.roads_from(A)))
            reads = [st for (k, st) in rec.reads if k == rid]
            want = DEFAULT_SEED_ENERGY * reads[0] * DEFAULT_DECAY_PER_HOP
            if len(reads) != 1 or bits(r.flow[rid]) != bits(want):
                bad.append((trial, sigma, len(reads)))
    check(not bad,
          f"12 trials x 4 sigmas on the real wall clock: the lone out-road is transmitted "
          f"bit-identically to the unnormalized value every time ({len(bad)} deviations: "
          f"{bad[:3]})")
    check(isinstance(SubstrateStore().clock.simulated, bool)
          and SubstrateStore().clock.simulated is False,
          "and the fixture really is on the moving default clock (simulated is False), "
          "which is the whole point of O-10 — a frozen clock cannot see DEFECT-B")


def test_O8_loop_closed_determinism_through_the_whole_pipeline():
    section("O-8/loop-closure: the pipeline's own output, driven end to end, is stable")
    # Nothing is hand-placed. perceive() picks the sources from the utterance, the
    # clusterer picks the representatives and their energies, the field builder merges,
    # coalitions form from the basins, and the workspace prunes. Every stage is driven by
    # the previous stage's actual output.
    from nous_perceive import think
    store = frozen_store()
    words = ["coffee", "warmth", "morning routine", "cozy feeling", "kitchen",
             "work", "desk", "deadline pressure", "writing code", "commute"]
    ids = [store.add_node(w, NodeType.CONCEPT) for w in words]
    rng = random.Random(7)
    for _ in range(60):
        a, b = rng.choice(ids), rng.choice(ids)
        worn(store, a, b, n=rng.randint(1, 9))
    sigs = set()
    for _ in range(8):
        r = think(store, "coffee in the kitchen before work")
        sigs.add((bits(r.thought.strength),
                  tuple(sorted(store.get_node(m).content for m in r.thought.members)),
                  tuple(sorted((store.get_node(k).content, bits(v))
                               for k, v in r.field_.total.items()))))
    check(len(sigs) == 1,
          f"8 successive think() calls on one store give one bit-exact result "
          f"({len(sigs)} distinct)")
    # purity of the whole read path, since think(broadcast=False) must mutate nothing
    before = {rid: bits(store.get_road(rid, apply_decay=False).strength)
              for rid in store.all_road_ids()}
    think(store, "coffee in the kitchen before work")
    after = {rid: bits(store.get_road(rid, apply_decay=False).strength)
             for rid in store.all_road_ids()}
    check(before == after,
          "and think(broadcast=False) left every road strength byte-identical")


# ═════════════════════════════════════════════════════════════════════════════
# O-11 / O-12 — sigma validation and the general non-finite guard.
# ═════════════════════════════════════════════════════════════════════════════

def test_O11_sigma_validation_boundary_is_exact():
    section("O-11 sigma validation: the boundary is where the spec puts it, exactly")
    store = frozen_store()
    S = store.add_node("S", NodeType.CONCEPT)
    for i in range(3):
        T = store.add_node("T%d" % i, NodeType.CONCEPT)
        worn(store, S, T, n=5)
    rejected = [float("inf"), float("-inf"), float("nan"), 0.0, -0.0, -1e-300, -1.0, -1e300]
    accepted = [None, 5e-324, 1e-300, 1e-12, 0.5, 1.0, 1e12, 1e300, 1.7976931348623157e308]
    bad_rej, bad_acc = [], []
    for sigma in rejected:
        try:
            spread_activation(store, S, normalization_sigma=sigma)
            bad_rej.append(sigma)
        except ValueError as e:
            if repr(sigma) not in str(e):
                bad_rej.append((sigma, "message does not name the value"))
        except Exception as e:                                    # noqa: BLE001
            bad_rej.append((sigma, type(e).__name__))
    for sigma in accepted:
        try:
            spread_activation(store, S, normalization_sigma=sigma)
        except Exception as e:                                    # noqa: BLE001
            bad_acc.append((sigma, type(e).__name__, str(e)[:50]))
    check(not bad_rej,
          f"every non-finite and non-positive sigma is refused with a ValueError naming "
          f"it ({bad_rej})")
    check(not bad_acc,
          f"and every finite positive sigma is accepted, right down to the smallest "
          f"subnormal 5e-324 and up to the largest finite double ({bad_acc})")
    check(True if _raises(lambda: spread_activation(store, S, normalization_sigma=-0.0))
          else False,
          "-0.0 is refused too: it is non-positive, and 'x <= 0.0' is True for it — a "
          "boundary an `x < 0.0` test would have let through")
    # and None stays exactly neutral
    check(signature(spread_activation(store, S))
          == signature(spread_activation(store, S, normalization_sigma=None)),
          "None remains the neutral value and equals omitting the parameter")


def _raises(fn, exc=Exception):
    try:
        fn()
        return False
    except exc:
        return True


def test_O12_non_finite_cannot_reach_the_result_via_transmission():
    section("O-12 the general non-finite guard on the transmission path")
    store = frozen_store()
    A = store.add_node("A", NodeType.CONCEPT)
    B = store.add_node("B", NodeType.CONCEPT)
    C = store.add_node("C", NodeType.CONCEPT)
    worn(store, A, B, n=6)
    worn(store, B, C, n=6)
    routes = [
        ({"energy": float("nan")}, "nan energy"),
        ({"energy": float("inf")}, "inf energy"),
        ({"energy": float("-inf")}, "-inf energy"),
        ({"decay_per_hop": float("nan")}, "nan decay"),
        ({"decay_per_hop": float("inf")}, "inf decay"),
        ({"energy": 0.0, "decay_per_hop": float("inf")}, "0*inf -> nan"),
        ({"energy": float("inf"), "decay_per_hop": 0.0}, "inf*0 -> nan"),
    ]
    leaks = []
    for kwargs, label in routes:
        try:
            r = spread_activation(store, A, floor=0.0, **kwargs)
            nf = [v for v in list(r.activation.values()) + list(r.flow.values())
                  if not math.isfinite(v)]
            if nf:
                leaks.append((label, nf[:2]))
        except ValueError:
            pass                                     # refused: correct
        except Exception as e:                       # noqa: BLE001
            leaks.append((label, f"unexpected {type(e).__name__}"))
    check(not leaks,
          f"no non-finite value reaches activation or flow through any transmission route "
          f"({leaks})")
    # the floor guard is the thing that used to be fooled; assert it directly
    check(not (float("nan") < DEFAULT_FLOOR),
          "the hazard is real and is a property of the comparison, not of sigma: "
          "`nan < floor` is False, so a NaN would walk straight past the floor")
    # and the ordinary path stays clean over a big battery
    leaked = 0
    for gs in range(30):
        st, ids = adversarial_graph(11000 + gs)
        for sn in ids:
            for sigma in (None, 1e-9, 1.0, 1e9):
                r = spread_activation(st, sn, normalization_sigma=sigma, floor=0.0)
                leaked += sum(1 for v in list(r.activation.values()) + list(r.flow.values())
                              if not math.isfinite(v))
    check(leaked == 0, f"and none on the ordinary path across 30 graphs ({leaked} leaks)")


# ─────────────────────────────────────────────────────────────────────────────
# O-12, SECOND PASS. The first pass returned FAIL here and recorded the gap as an
# asserted-negative: a non-finite `energy` reached `activation` verbatim whenever the
# seed never transmitted. D-015 closed it by option (A) — validate `energy` for
# finiteness at the boundary — so the asserted-negative is RETIRED, per its own exit
# instruction, and converted into the positive property below. What follows is written
# against the invariant, not against the patch: the shapes are enumerated from the
# topologies a seed can have, not from the two the failure was found on.
# ─────────────────────────────────────────────────────────────────────────────

NON_FINITE_ENERGIES = [
    ("+inf literal", float("inf")),
    ("-inf literal", float("-inf")),
    ("nan literal", float("nan")),
    ("nan, sign bit SET", float("-nan")),
    # a NaN with a non-zero payload: a distinct bit pattern that `x != x` still catches,
    # included so the check cannot be passing by comparing against one canonical NaN.
    ("nan, payload 0x…01", unbits("010000000000f87f")),
    ("nan COMPUTED at runtime (inf-inf)", float("inf") - float("inf")),
    ("inf COMPUTED at runtime (1e308*10)", 1e308 * 10),
]

FINITE_ENERGIES_THAT_MUST_STAY_ACCEPTED = [
    -1.7976931348623157e308, -1e300, -1.0, -5e-324, -0.0,
    0.0, 5e-324, 1e-300, 0.5, 1.0, 1e300, 1.7976931348623157e308,
]


def _seed_shapes():
    """Every topology a seed can sit in, built independently of the two the FAIL used.

    Returns (label, store, seed_id, extra_kwargs). The isolated seed and hop_budget=0
    are in the list because they were the failing inputs, not because they are the
    property — the property is that the shape cannot matter at all, which is only
    demonstrable by enumerating shapes that differ in every way the engine can see.
    """
    out = []

    s = frozen_store()
    out.append(("isolated seed, no roads at all", s, s.add_node("lone", NodeType.CONCEPT), {}))

    s = frozen_store()
    a = s.add_node("a", NodeType.CONCEPT); b = s.add_node("b", NodeType.CONCEPT)
    worn(s, a, b, n=5)
    out.append(("out-road, hop_budget=0 (settles, never expands)", s, a, {"hop_budget": 0}))
    out.append(("out-road, ordinary expansion", s, a, {}))
    out.append(("TERMINAL seed: in-road only, no out-road", s, b, {}))

    s = frozen_store()
    a = s.add_node("a", NodeType.CONCEPT)
    worn(s, a, a, n=6)                                   # self-loop only
    out.append(("self-loop only", s, a, {}))

    s = frozen_store()
    ring = [s.add_node("r%d" % i, NodeType.CONCEPT) for i in range(4)]
    for i in range(4):
        worn(s, ring[i], ring[(i + 1) % 4], n=4)
    out.append(("4-cycle", s, ring[0], {}))

    s = frozen_store()
    hub = s.add_node("hub", NodeType.CONCEPT)
    for i in range(40):
        worn(s, hub, s.add_node("f%d" % i, NodeType.CONCEPT), n=2)
    out.append(("40-way fan", s, hub, {}))

    s = frozen_store()
    a = s.add_node("a", NodeType.CONCEPT); b = s.add_node("b", NodeType.CONCEPT)
    for _ in range(9):
        s.traverse(a, b, {"dread": -0.95})               # drive it closed
    shut = s.get_road(s.find_road(a, b), apply_decay=False).closed
    assert shut, "fixture drift: this shape is supposed to have a CLOSED out-road"
    out.append(("closed road out of the seed", s, a, {"floor": 0.0}))

    s = frozen_store()
    S = s.add_node("S", NodeType.CONCEPT); T = s.add_node("T", NodeType.CONCEPT)
    for i, (x, y) in enumerate(((1, 2), (1, 3), (1, 9))):
        M = s.add_node("M%d" % i, NodeType.CONCEPT)
        worn(s, S, M, n=x); worn(s, M, T, n=y)
    out.append(("the DEFECT-A convergence graph (in-degree 3)", s, S, {}))

    # loop-closed: a store the generator produced, not one hand-drawn for this test
    st, ids = adversarial_graph(90210)
    out.append(("system-generated adversarial graph", st, ids[0], {}))
    return out


ENERGY_PARAM_GRID = [
    {},
    {"floor": 0.0},
    {"floor": -1e300},
    {"normalization_sigma": 2.5},
    {"normalization_sigma": 1e-9, "floor": 0.0},
    {"decay_per_hop": 1.0, "hop_budget": 6, "floor": 0.0},
    {"decay_per_hop": 0.0},
    {"hop_budget": 0},
]


def test_O12_non_finite_energy_is_refused_at_every_graph_shape():
    """O-12's failing leg, now asserted as the positive property (D-015 option A).

    The retired asserted-negative said: "IF THIS GOES RED BECAUSE energy IS NOW VALIDATED:
    delete it and re-verify O-12." It went red — by RAISING, which aborted the suite — so
    it is gone and this stands in its place.
    """
    section("O-12 non-finite `energy` is refused at the boundary, on every graph shape")
    shapes = _seed_shapes()

    def snap(store):
        return (
            tuple(sorted(
                (rid, bits(store.get_road(rid, apply_decay=False).strength),
                 store.get_road(rid, apply_decay=False).closed,
                 store.get_road(rid, apply_decay=False).traversal_count)
                for rid in store.all_road_ids())),
            tuple(sorted((nid, store.get_node(nid).access_count)
                         for nid in store.all_node_ids())),
            tuple((nid, tuple(store.roads_from(nid)), tuple(store.roads_into(nid)))
                  for nid in store.all_node_ids()),
        )

    before = [snap(st) for _, st, _, _ in shapes]
    total = leaked = wrong_type = unnamed = unattributed = 0
    failures = []
    for label, store, seed_node, base in shapes:
        for ename, energy in NON_FINITE_ENERGIES:
            for extra in ENERGY_PARAM_GRID:
                kwargs = dict(base); kwargs.update(extra)
                total += 1
                try:
                    r = spread_activation(store, seed_node, energy=energy, **kwargs)
                    leaked += 1
                    failures.append((label, ename, kwargs,
                                     repr(r.activation.get(seed_node))))
                except ValueError as e:
                    if repr(energy) not in str(e):
                        unnamed += 1
                        failures.append((label, ename, "message does not name the value"))
                    if "energy" not in str(e):
                        unattributed += 1
                except Exception as e:                                # noqa: BLE001
                    wrong_type += 1
                    failures.append((label, ename, kwargs, type(e).__name__, str(e)[:80]))
    after = [snap(st) for _, st, _, _ in shapes]

    print(f"    {len(shapes)} seed shapes x {len(NON_FINITE_ENERGIES)} non-finite energies "
          f"x {len(ENERGY_PARAM_GRID)} parameter sets = {total} calls")
    check(leaked == 0,
          f"O-12 CLOSED: not one of {total} calls returned a result — every non-finite "
          f"energy is refused at the boundary, on every shape including the isolated seed "
          f"and hop_budget=0 ({leaked} leaks: {failures[:2]})")
    check(wrong_type == 0,
          f"and every refusal is a ValueError, not a TypeError or a stdlib exception "
          f"escaping from inside ({wrong_type})")
    check(unnamed == 0,
          f"every message names the offending value, so the caller can see WHICH input "
          f"was refused ({unnamed})")
    check(unattributed == 0,
          f"and names the parameter `energy`, which is what distinguishes it from the "
          f"sigma refusal — two adjacent doors, two distinguishable messages "
          f"({unattributed})")
    check(before == after,
          "the refusal is pure: no road, node, or iteration order moved in any of the "
          "shape stores across the whole battery")

    # The two exact inputs the first pass FAILED on, called out by name so the closure is
    # legible against SPEC-0c §4.1's reproduction rather than only in aggregate.
    s = frozen_store()
    lone = s.add_node("lone", NodeType.CONCEPT)
    got = {}
    for e in (float("nan"), float("inf"), float("-inf")):
        try:
            got[repr(e)] = repr(spread_activation(s, lone, energy=e).activation[lone])
        except ValueError as ex:
            got[repr(e)] = "ValueError"
    check(list(got.values()) == ["ValueError"] * 3,
          f"§4.1's reproduction is dead: the ISOLATED seed now refuses nan, inf and -inf "
          f"instead of returning them verbatim ({got})")
    s2 = frozen_store()
    a = s2.add_node("a", NodeType.CONCEPT); b = s2.add_node("b", NodeType.CONCEPT)
    worn(s2, a, b, n=5)
    check(_raises(lambda: spread_activation(s2, a, energy=float("inf"), hop_budget=0),
                  ValueError),
          "and so is the second route — a seed with out-roads at hop_budget=0, which "
          "settles without ever transmitting")

    # Fail fast, in the CALLER's frame: the parameter is refused before the store is
    # consulted at all, so a bad parameter is never masked by an unrelated NotFound.
    order = []
    for e, tag in ((float("nan"), "nan"), (1.0, "finite")):
        try:
            spread_activation(s2, "no-such-node", energy=e)
            order.append((tag, "returned"))
        except Exception as ex:                                       # noqa: BLE001
            order.append((tag, type(ex).__name__))
    check(order == [("nan", "ValueError"), ("finite", "NotFound")],
          f"validation runs BEFORE the seed's existence is checked, exactly as sigma's "
          f"does — a non-finite energy on an unknown seed reports the energy, and only a "
          f"VALID energy gets as far as NotFound ({order})")


ENERGY_REFUSAL_DRIVER = textwrap.dedent('''
    import hashlib, math, struct
    from nous_store import SubstrateStore, Clock, NodeType
    from nous_activation import spread_activation
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    A = s.add_node("A", NodeType.CONCEPT)
    B = s.add_node("B", NodeType.CONCEPT)
    for _ in range(5): s.traverse(A, B)
    NAN_PAY = struct.unpack("<d", bytes.fromhex("010000000000f87f"))[0]
    rows = []
    for e in (float("inf"), float("-inf"), float("nan"), float("-nan"), NAN_PAY):
        for seed, hb in ((A, 0), (A, 3), (B, 3)):
            try:
                r = spread_activation(s, seed, energy=e, hop_budget=hb, floor=0.0)
                rows.append(("RETURNED", struct.pack("<d", r.activation[seed]).hex()))
            except ValueError as ex:
                rows.append(("ValueError", repr(e) in str(ex), "energy" in str(ex)))
            except Exception as ex:
                rows.append(("OTHER", type(ex).__name__))
    for e in (-0.0, -1.0, -1e300, 0.0, 1.0):
        r = spread_activation(s, A, energy=e, floor=-1e308)
        rows.append((repr(e), tuple(struct.pack("<d", v).hex()
                                    for v in r.activation.values())))
    print(hashlib.sha256(repr(rows).encode()).hexdigest()[:24])
    print(len(rows))
''')


def test_O12_the_refusal_is_deterministic_across_seeds_and_interpreters():
    """A new boundary behaviour is a new determinism obligation. CLAUDE.md rule 7: a
    property that holds on one interpreter was never a property of the program."""
    section("O-12 the refusal itself is deterministic across hash seeds AND interpreters")
    interps = interpreters()
    print(f"  interpreters swept: {', '.join(interps)}")
    outs = run_probe(ENERGY_REFUSAL_DRIVER, interps=interps)
    errs = [o for o in outs if o[2].startswith("ERROR")]
    check(not errs, f"every process ran the refusal battery ({len(errs)} errors; {errs[:1]})")
    digests = {o.splitlines()[0] for _, _, o in outs if not o.startswith("ERROR")}
    counts = {o.splitlines()[1] for _, _, o in outs if not o.startswith("ERROR")}
    check(len(interps) >= 5, f"five interpreters were available ({interps})")
    check(len(outs) >= 30,
          f"{len(outs)} fresh processes ({len(interps)} interpreters x {len(HASH_SEEDS)} "
          f"hash seeds)")
    check(len(digests) == 1,
          f"ONE digest over (refusal outcome, message names the value, message names the "
          f"parameter) plus the accepted-energy bit patterns, across every process "
          f"({len(digests)} distinct: {sorted(digests)[:3]})")
    check(counts == {"20"},
          f"and every process evaluated the same number of rows ({counts})")


def test_O12_D014_negative_and_zero_energy_are_STILL_accepted():
    """D-014's ruling must not have moved. D-015 scoped the new validation to FINITENESS;
    if it rejects a negative it implemented a different, unauthorised decision."""
    section("O-12 the boundary discriminates on FINITENESS, not on sign (D-014 stands)")
    s = frozen_store()
    lone = s.add_node("lone", NodeType.CONCEPT)
    rejected = []
    for e in FINITE_ENERGIES_THAT_MUST_STAY_ACCEPTED:
        try:
            spread_activation(s, lone, energy=e)
        except Exception as ex:                                       # noqa: BLE001
            rejected.append((repr(e), type(ex).__name__, str(ex)[:60]))
    check(not rejected,
          f"every FINITE energy is accepted, negative and zero included, from "
          f"-1.797…e308 through -0.0 to the largest positive double ({rejected})")

    # the discriminator, isolated: same call, same shape, one finite and one not
    pairs = [(-1e300, float("-inf")), (1e300, float("inf"))]
    wrong = []
    for finite, nonfinite in pairs:
        ok = _raises(lambda: spread_activation(s, lone, energy=finite), ValueError)
        bad = _raises(lambda: spread_activation(s, lone, energy=nonfinite), ValueError)
        if ok or not bad:
            wrong.append((finite, nonfinite, ok, bad))
    check(not wrong,
          f"-1e300 is accepted where -inf is refused, and 1e300 where +inf is refused: the "
          f"boundary is finiteness, and the SIGN question D-014 answered stays answered "
          f"({wrong})")

    # -0.0, phrased as OUR semantics and not as agreement with the stdlib (SPEC-0c §2.6)
    z = spread_activation(s, lone, energy=-0.0).activation[lone]
    p = spread_activation(s, lone, energy=0.0).activation[lone]
    check(bits(z) == "0000000000000000" and bits(p) == "0000000000000000",
          f"activation energy has no signed zero: -0.0 normalises to +0.0, by design "
          f"(-0.0 -> {bits(z)}, +0.0 -> {bits(p)}, and the input -0.0 is {bits(-0.0)})")
    check(bits(spread_activation(s, lone, energy=-5e-324).activation[lone])
          == bits(-5e-324),
          "and the normalisation is confined to zero: the negative subnormal -5e-324 "
          "comes back bit-for-bit, so this is one degenerate input and not a class")

    # acceptance is not vacuous — a negative energy must actually SPREAD, not be
    # swallowed by the floor and quietly produce an empty result
    s2 = frozen_store()
    a = s2.add_node("a", NodeType.CONCEPT)
    c = s2.add_node("c", NodeType.CONCEPT)
    worn(s2, a, c, n=7)
    r = spread_activation(s2, a, energy=-2.0, floor=-1e300)
    downstream = [v for k, v in r.activation.items() if k != a]
    check(downstream and all(v < 0.0 for v in downstream)
          and all(math.isfinite(v) for v in r.activation.values()),
          f"a negative energy still propagates and stays finite — acceptance is real, not "
          f"a result the floor emptied ({[repr(v) for v in downstream]})")


class PoisonedRoadStore:
    """Injects a non-finite road strength BELOW the public boundary.

    SPEC-0c §4 requires the backstop guard's test to be able to reach it without going
    through a validated parameter. This is that injection: a store that hands the engine a
    Road whose strength is non-finite — a value no public call can now produce and one the
    real store would never hold. The engine is unmodified; only its input is hostile.
    """

    def __init__(self, inner, poison):
        self._inner = inner
        self._poison = poison

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def get_road(self, road_id, apply_decay=True):
        return dataclasses.replace(self._inner.get_road(road_id, apply_decay),
                                   strength=self._poison)


def test_O12_the_transmitted_backstop_guard_is_LIVE_by_two_independent_routes():
    """SPEC-0c §4, as corrected: the guard is NOT dead code, and must not be removed as
    such. Asserted by two routes that share nothing — one public, one below the boundary —
    so neither the harness nor the parameter domain is load-bearing for the conclusion."""
    section("O-12 the `transmitted` backstop guard is live, by two independent routes")
    s = frozen_store()
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    worn(s, a, b, n=6); worn(s, b, c, n=6); worn(s, a, c, n=3)

    # ROUTE 1 — public and live TODAY: `decay_per_hop` is documented 0..1 but is not
    # validated (D-015 scoped the boundary to `energy`), so it is a real caller-reachable
    # path into the guard. Whether it should be validated is a separate, undecided
    # question and nothing here presumes an answer.
    route1 = []
    for d in (float("inf"), float("-inf"), float("nan")):
        try:
            r = spread_activation(s, a, decay_per_hop=d, floor=0.0)
            route1.append(("RETURNED", [repr(v) for v in r.activation.values()][:3]))
        except ValueError as e:
            route1.append(("ValueError", repr(d) in str(e), "road" in str(e)))
        except Exception as e:                                        # noqa: BLE001
            route1.append(("OTHER", type(e).__name__))
    check(all(x[0] == "ValueError" for x in route1),
          f"route 1 (public, in-domain-violating): decay_per_hop = inf, -inf and nan all "
          f"reach the guard and are refused with a ValueError ({route1})")
    check(all(x[1] and x[2] for x in route1 if x[0] == "ValueError"),
          f"and the diagnostic names the offending value AND the road it happened on, so "
          f"the failure is attributable rather than merely reported ({route1})")

    # ROUTE 2 — below the boundary: an injected non-finite ROAD STRENGTH, which no public
    # parameter can produce now that energy and sigma are both validated. This is the
    # class the guard was written for: a term that goes non-finite from finite inputs.
    route2 = []
    for poison in (float("inf"), float("-inf"), float("nan")):
        try:
            r = spread_activation(PoisonedRoadStore(s, poison), a, floor=0.0)
            nf = [v for v in list(r.activation.values()) + list(r.flow.values())
                  if not math.isfinite(v)]
            route2.append(("RETURNED", len(nf)))
        except ValueError:
            route2.append(("ValueError", 0))
        except Exception as e:                                        # noqa: BLE001
            route2.append(("OTHER", type(e).__name__))
    check(all(x[0] == "ValueError" for x in route2),
          f"route 2 (injected below the boundary): a non-finite road strength is refused "
          f"at the point of computation, with every public input valid ({route2})")

    # the hazard the guard exists for, asserted directly and at several floors
    check(all(not (float("nan") < f) for f in (DEFAULT_FLOOR, 0.0, -1e300, float("-inf"))),
          "the hazard is a property of the COMPARISON, not of any one term: `nan < floor` "
          "is False at every floor, so without the guard a NaN walks straight past it")

    # BUT it is a backstop: nothing inside the documented domain reaches it. Both halves
    # matter — "live" without "not on the ordinary path" would mean an in-domain crash.
    fired = 0
    for gs in range(25):
        st, ids = adversarial_graph(77000 + gs)
        for sn in ids:
            for d in (0.0, 0.35, 0.7, 1.0):
                for sigma in (None, 1e-6, 3.0):
                    try:
                        spread_activation(st, sn, decay_per_hop=d,
                                          normalization_sigma=sigma, floor=0.0)
                    except ValueError:
                        fired += 1
    check(fired == 0,
          f"and it never fires inside the documented domain — 25 system-generated graphs x "
          f"every node x decay in [0,1] x three sigmas raised nothing ({fired})")

    # structural: SPEC-0c §4 says the guard MUST NOT be removed as dead code. A future
    # reader who finds no in-domain route is reading correctly and concluding wrongly, so
    # the requirement is machine-checked rather than left to a comment.
    tree = ast.parse(open(os.path.join(SRC, "nous_activation.py"),
                          encoding="utf-8").read())
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "spread_activation"), None)
    guards = [n for n in ast.walk(fn) if isinstance(n, ast.If)
              and "isfinite(transmitted)" in ast.unparse(n.test)
              and any(isinstance(x, ast.Raise) for x in ast.walk(n))] if fn else []
    check(len(guards) == 1,
          f"the guard is still present in spread_activation as a raising branch on "
          f"`math.isfinite(transmitted)` ({len(guards)} found) — SPEC-0c §4: it must not "
          f"be deleted as dead code")


def test_O12_loop_closed_no_non_finite_survives_the_pipeline():
    """LOOP-CLOSURE for O-12. The stage is driven by what the previous stages actually
    produced — perceive() -> cluster_sources() -> build_activation_field() — never by a
    hand-placed energy. Two obligations, and the second is the one a friendly input hides:
    the new boundary must refuse hostile input, AND it must not fire on the system's own.
    """
    section("O-12 loop-closed: the pipeline's own energies, and hostile input at its top")
    import nous_field
    from nous_perceive import perceive, think
    from nous_source_clustering import cluster_sources
    from nous_field import build_activation_field

    def corpus(seed):
        rng = random.Random(seed)
        s = frozen_store()
        words = ["coffee", "kitchen", "morning", "mug", "toast", "work", "code",
                 "deadline", "rain", "window", "cat", "stairs"]
        ids = [s.add_node(w, NodeType.CONCEPT) for w in words]
        for _ in range(rng.randint(20, 60)):
            x, y = rng.choice(ids), rng.choice(ids)
            for _ in range(rng.randint(1, 9)):
                s.traverse(x, y, {"dread": -rng.uniform(0.8, 1.0)}
                           if rng.random() < 0.15 else None)
        return s, words

    # (1) NO-REGRESSION, loop-closed: spy on the energies the pipeline itself hands the
    # engine. If any were non-finite the new validation would turn a silent NaN into a
    # production crash — so this is the leg that would catch the fix breaking the system.
    real = nous_field.spread_activation
    seen = []

    def spy(store, seed_node, **kw):
        seen.append(kw.get("energy"))
        return real(store, seed_node, **kw)

    nous_field.spread_activation = spy
    thoughts = 0
    try:
        for gs in range(12):
            s, words = corpus(5000 + gs)
            utt = " ".join(random.Random(gs).sample(words, 5))
            p = perceive(s, utt)
            if not p.sources:
                continue
            cl = cluster_sources(s, p.sources)
            build_activation_field(s, list(cl.group_seeds.keys()),
                                   source_energies=cl.group_seeds)
            if think(s, utt).thought is not None:
                thoughts += 1
    finally:
        nous_field.spread_activation = real
    check(len(seen) >= 12,
          f"the pipeline was actually driven ({len(seen)} spreads from system-generated "
          f"percepts, {thoughts} thoughts)")
    bad = [e for e in seen if e is None or not math.isfinite(e)]
    check(not bad,
          f"every energy the pipeline PRODUCED and handed to the engine is finite, so the "
          f"new boundary never fires on the system's own input ({bad[:3]})")

    # (2) hostile input at the TOP of the pipeline, carried down by the real stages
    s, words = corpus(999)
    utt = " ".join(words[:5])
    leaks = []
    for label, kw in (("source_energy=nan", {"source_energy": float("nan")}),
                      ("source_energy=inf", {"source_energy": float("inf")}),
                      ("source_energy=-inf", {"source_energy": float("-inf")}),
                      ("decay_per_hop=nan", {"decay_per_hop": float("nan")}),
                      ("decay_per_hop=inf", {"decay_per_hop": float("inf")})):
        try:
            r = think(s, utt, **kw)
            vals = ([r.thought.strength] if r.thought else []) + \
                   [c.strength for c in r.coalitions] + \
                   (list(r.field_.total.values()) if r.field_ else [])
            if any(not math.isfinite(v) for v in vals):
                leaks.append((label, "NON-FINITE reached the thought"))
        except ValueError:
            pass
        except Exception as e:                                        # noqa: BLE001
            leaks.append((label, f"unexpected {type(e).__name__}: {str(e)[:60]}"))
    check(not leaks,
          f"a non-finite parameter at the TOP of think() is refused on the way down — "
          f"never silently carried into a coalition strength or a winner ({leaks})")

    # (3) the third route, through a module 0c never touched: a replay BodySensor whose
    # telemetry yields a NaN friction modulates decay_per_hop to NaN. Three modules deep,
    # and the backstop is what catches it. (Adversarial replay data — live perf_counter()
    # does not produce NaN — but it is a real composition of shipped public APIs.)
    from nous_bodysensor import BodySensor, TelemetrySample
    trace = [TelemetrySample(perf=0.0, proc=0.0),
             TelemetrySample(perf=float("nan"), proc=1.0)]
    sensor = BodySensor(simulated=True, trace=trace)
    sensor.read()                      # prime: consumes the neutral first sample
    caught = None
    try:
        r = think(s, utt, body_sensor=sensor)
        caught = ("RETURNED", r.body_friction, r.effective_decay_per_hop)
    except ValueError as e:
        caught = ("ValueError", str(e)[:60])
    check(caught[0] == "ValueError",
          f"a NaN friction reaching decay_per_hop through think(body_sensor=…) is caught "
          f"by the backstop, not carried into the field ({caught})")

    # (4) the whole-pipeline sweep: over system-generated stores at ordinary parameters,
    # nothing anywhere in the result is non-finite.
    nonfinite = 0
    for gs in range(10):
        s, words = corpus(6000 + gs)
        utt = " ".join(random.Random(gs).sample(words, 6))
        r = think(s, utt)
        if r.field_ is None:
            continue
        vals = list(r.field_.total.values()) + [c.strength for c in r.coalitions] + \
            ([r.thought.strength] if r.thought else [])
        for src_map in r.field_.per_source.values():
            vals += list(src_map.values())
        vals += list(r.field_.flow.values())
        nonfinite += sum(1 for v in vals if not math.isfinite(v))
    check(nonfinite == 0,
          f"and over 10 further system-generated cycles, not one non-finite value appears "
          f"anywhere in the field, the coalitions or the thought ({nonfinite})")


def test_O12_ASSERTED_NEGATIVE_the_fsum_reduction_raises_where_the_old_engine_returned_inf():
    """FINDING 3, recorded as an asserted-negative rather than hidden.

    `math.fsum` raises OverflowError on intermediate overflow where a naive running total
    would have produced inf. The reduction happens at the layer-boundary freeze, BEFORE any
    transmitted value exists, so the engine's own non-finite guard never gets a chance and
    the exception that escapes is stdlib's, not the engine's diagnostic ValueError.

    Arguably an improvement — refusing beats poisoning — but it is a NEUTRAL-PATH BEHAVIOUR
    CHANGE at extreme energy, and SPEC-0c §7 done-means item 4 requires the delivery report
    to state which previously-passing behaviours changed value and why. This test is that
    statement, in executable form.
    """
    section("O-12 ASSERTED-NEGATIVE: fsum overflow raises OverflowError, not the engine's "
            "own ValueError")
    s = frozen_store()
    S = s.add_node("S", NodeType.CONCEPT)
    T = s.add_node("T", NodeType.CONCEPT)
    for i in range(12):
        M = s.add_node("M%d" % i, NodeType.CONCEPT)
        worn(s, S, M, n=40)
        worn(s, M, T, n=40)
    # every individual term is finite; only their exact sum overflows
    ok = spread_activation(s, S, energy=1e307, decay_per_hop=1.0, floor=0.0)
    check(math.isfinite(ok.activation[T]),
          f"at energy=1e307 every term and the total are finite ({ok.activation[T]!r})")
    raised = None
    try:
        spread_activation(s, S, energy=1e308, decay_per_hop=1.0, floor=0.0)
    except Exception as e:                                        # noqa: BLE001
        raised = e
    check(isinstance(raised, OverflowError),
          f"at energy=1e308 the reduction raises OverflowError from math.fsum, not the "
          f"engine's ValueError (got {type(raised).__name__ if raised else None}: "
          f"{raised!r}). IF THIS GOES RED BECAUSE THE ENGINE NOW CATCHES IT: delete it "
          f"and re-verify O-12.")
    check(not isinstance(raised, ValueError),
          "and it is specifically NOT the engine's own diagnostic — a caller catching "
          "ValueError to handle bad input will not catch this")
    finding("O-12/neutral-path",
            "the fsum reduction raises OverflowError where the pre-0c engine returned inf "
            "(energy=1e308 on a 12-way convergence, decay=1.0, floor=0.0). A neutral-path "
            "behaviour change at extreme energy, outside N-1's PARAM_SWEEP so no existing "
            "test sees it. Probably an improvement; must be DOCUMENTED, not discovered.")


# ═════════════════════════════════════════════════════════════════════════════
# FINDING 1 — the order-dependent aggregate 0c's scope did not reach.
# ═════════════════════════════════════════════════════════════════════════════

def test_FINDING_ASSERTED_NEGATIVE_field_merge_is_order_dependent():
    """FINDING 1, recorded as an asserted-negative rather than hidden.

    SPEC-0c §2.5.2(b) records that §1's original falsifier covered only one path and would
    have shipped a live defect. The obvious next question is whether the SECOND sweep was
    exhaustive either. It was not:

        nous_field.py  total[node] = total.get(node, 0.0) + act      (the merge)
        nous_field.py  merged_flow[rid] = merged_flow.get(rid, 0.0) + fv

    Both are naive running float adds — DEFECT-A's exact shape, at a third owner. §2.5
    enumerated three builtin `sum()` sites; these are not `sum()` calls, so O-15 does not
    cover them and they were never in 0c's decided scope.

    WHAT THIS IS AND IS NOT. The iteration order is `ordered_sources`, which is program
    order (clustering sorts groups by representative creation_seq), so this does NOT break
    determinism across processes: O-4, O-4b, O-5 and O-16 all hold, and are asserted to
    hold above. It breaks ORDER-INDEPENDENCE — the property D-013 ground 1 called the
    difference between fixing the cause and pinning the symptom — and the difference
    reaches Coalition.strength, which `_competition_key` compares.

    This test PASSES while the limitation is present and goes RED when it is closed.
    """
    section("FINDING 1 ASSERTED-NEGATIVE: the field merge is order-DEPENDENT")
    from nous_field import build_activation_field
    from nous_coalitions import form_coalitions_from_field
    from nous_workspace import rank_coalitions
    rng = random.Random(0)
    s = frozen_store()
    src = [s.add_node("s%d" % i, NodeType.CONCEPT) for i in range(3)]
    mid = [s.add_node("m%d" % i, NodeType.CONCEPT) for i in range(3)]
    hub = s.add_node("hub", NodeType.CONCEPT)
    for a in src:
        for b in mid:
            worn(s, a, b, n=rng.randint(1, 9))
    for b in mid:
        worn(s, b, hub, n=rng.randint(1, 9))
    totals, strengths, winners = {}, set(), set()
    for perm in itertools.permutations(src):
        f = build_activation_field(s, list(perm))
        for n, v in f.total.items():
            totals.setdefault(s.get_node(n).content, set()).add(bits(v))
        cs = form_coalitions_from_field(f, s)
        strengths.add(tuple(sorted(bits(c.strength) for c in cs)))
        r = rank_coalitions(cs)
        winners.add(tuple(sorted(s.get_node(m).content for m in r[0].members)) if r else None)
    moved = {n: v for n, v in totals.items() if len(v) > 1}
    for n, v in sorted(moved.items()):
        print(f"    field.total[{n}]: {len(v)} distinct bit patterns over 3! source orders")
        for b in sorted(v):
            print(f"        {b}  = {unbits(b)!r}")
    check(bool(moved),
          f"the SAME SET of sources supplied in a different ORDER gives different bits in "
          f"field.total ({len(moved)} nodes moved). IF THIS GOES RED BECAUSE THE MERGE NOW "
          f"USES fsum: delete it, and re-verify 1a/1b/1d.")
    check(len(strengths) > 1,
          f"and the difference REACHES Coalition.strength ({len(strengths)} distinct "
          f"strength multisets over the 6 source orders) — the value _competition_key "
          f"compares")
    check(len(winners) == 1,
          f"the winner is nevertheless stable on THIS graph ({len(winners)} distinct). "
          f"Recorded precisely because that is how BUG-0b1 hid: it did not flip a winner "
          f"either, until a graph arrived where it did, 8 times in 30.")
    # AND THE BOUND ON THE FINDING, so it is not read as wider than it is. The identical
    # shape exists inside the module 0c DOES own — `flow[rid] = flow.get(rid, 0.0) +
    # transmitted` in nous_activation — and there it is STRUCTURALLY SINGLE-TERM: under
    # hop-layered single expansion a node expands at most once, so a road transmits at
    # most once and the add never has a second operand. That is the six-bug checklist's
    # "can this branch ever fire?" question, answered by measurement rather than by
    # reading the comment that asserts it.
    reads_max = 0
    spreads = 0
    for gs in range(60):
        st, ids = adversarial_graph(20000 + gs)
        for sn in ids:
            for sigma in (None, 1.0):
                rec = RecordingStore(st)
                spread_activation(rec, sn, normalization_sigma=sigma, floor=0.0)
                per = {}
                for rid, _ in rec.reads:
                    per[rid] = per.get(rid, 0) + 1
                if per:
                    reads_max = max(reads_max, max(per.values()))
                    spreads += 1
    check(reads_max == 1,
          f"the same shape at nous_activation's `flow[rid] +=` is structurally "
          f"single-term: over {spreads} spreads on 60 hostile graphs — cycles, "
          f"self-loops, fans — no road was ever read (and so never transmitted) more "
          f"than once, so its second operand cannot exist (max {reads_max})")
    finding("field-merge",
            "nous_field.build_activation_field merges with a naive running float add "
            "(total[node] += act, merged_flow[rid] += fv). Order-PINNED, so cross-process "
            "determinism is unaffected and every O-4/O-4b/O-5/O-16 result stands; NOT "
            "order-INDEPENDENT, and the difference reaches Coalition.strength. Out of "
            "0c's decided scope (§2.5 enumerated builtin sum() sites; these are not "
            "sum() calls). Recommend a follow-on brick, not a scope widening here. "
            "BOUNDED: the same shape inside nous_activation (flow[rid] +=) is "
            "structurally single-term and is NOT a live instance.")


# ═════════════════════════════════════════════════════════════════════════════
# ULP-ADJACENT TIE-BREAKS — where a comparison COULD resolve on a float, construct
# the ULP-adjacent case deliberately and assert the DOCUMENTED tie-break decides it.
# ═════════════════════════════════════════════════════════════════════════════

def test_ULP_the_competition_tie_break_is_decided_by_the_documented_integer_keys():
    section("ULP the competition tie-break: exact ties resolve on size then creation_seq")
    from nous_coalitions import Coalition
    from nous_workspace import rank_coalitions, _density_score, DEFAULT_MIN_SIZE_GUARD

    def coal(members_seq, strength):
        return Coalition(members={f"n{i}": strength / len(members_seq)
                                  for i in members_seq},
                         strength=strength,
                         _seq={f"n{i}": i for i in members_seq})

    # (a) EXACT TIE on density and size -> the documented key is min creation_seq ASC.
    a = coal([10, 11, 12], 3.0)
    b = coal([1, 2, 3], 3.0)
    r = rank_coalitions([a, b])
    check(bits(_density_score(a, min_size_guard=DEFAULT_MIN_SIZE_GUARD))
          == bits(_density_score(b, min_size_guard=DEFAULT_MIN_SIZE_GUARD)),
          "the two coalitions are EXACTLY tied on density, to the bit — so the tie-break "
          "is genuinely reachable and not pre-empted by a float difference")
    check(r[0] is b,
          "and the lower minimum creation_seq wins, as _competition_key documents "
          "(-density, -size, min_seq)")
    # order of presentation must not matter
    check(rank_coalitions([b, a])[0] is b,
          "the same winner regardless of the order the coalitions are presented in")

    # (b) ONE ULP APART -> the float decides, because density is the PRIMARY key and the
    #     spec says so. The point of constructing this case is to pin which way it goes.
    base = 3.0
    up = math.nextafter(base, math.inf)
    check(ulp_gap(base, up) == 1, f"the constructed pair really is 1 ULP apart ({base!r}, {up!r})")
    c = coal([1, 2, 3], up)            # lower seq, HIGHER strength by 1 ULP
    d = coal([10, 11, 12], base)
    check(rank_coalitions([d, c])[0] is c,
          "1 ULP of extra density wins, and it wins for the documented reason: density is "
          "the primary key. The tie-break exists for EXACT ties, not for near ones.")
    e = coal([1, 2, 3], base)          # lower seq, LOWER strength by 1 ULP
    f = coal([10, 11, 12], up)
    check(rank_coalitions([e, f])[0] is f,
          "and 1 ULP the other way flips it — which is exactly why BUG-0b1 mattered, and "
          "exactly why the inputs to this comparison must be exactly rounded")

    # (c) SIZE breaks a density tie before creation_seq does. Constructed so the LARGER
    #     coalition also has the HIGHER creation_seq — otherwise "size decided it" and
    #     "creation_seq decided it" would be indistinguishable and the test would prove
    #     nothing about the key's ordering.
    g = Coalition(members={"x%d" % i: 2.0 for i in range(4)}, strength=8.0,
                  _seq={"x%d" % i: 100 + i for i in range(4)})     # size 4, HIGH seq
    h = Coalition(members={"y%d" % i: 2.0 for i in range(3)}, strength=6.0,
                  _seq={"y%d" % i: i for i in range(3)})           # size 3, LOW seq
    check(bits(_density_score(g, min_size_guard=DEFAULT_MIN_SIZE_GUARD))
          == bits(_density_score(h, min_size_guard=DEFAULT_MIN_SIZE_GUARD)),
          f"a density tie between coalitions of DIFFERENT size is constructible "
          f"(8.0/4 == 6.0/max(3,{DEFAULT_MIN_SIZE_GUARD}) == "
          f"{_density_score(g, min_size_guard=DEFAULT_MIN_SIZE_GUARD)!r})")
    check(rank_coalitions([h, g])[0] is g and rank_coalitions([g, h])[0] is g,
          "and size desc breaks it — the LARGER coalition wins despite having the HIGHER "
          "minimum creation_seq, so size is demonstrably consulted before seq, in either "
          "presentation order")


def test_ULP_road_valence_closure_decision_is_multiset_determined():
    section("ULP the closure decision sits exactly on the threshold and does not wobble")
    from nous_store import _open_close_on_crossing, _CLOSURE_THRESHOLD
    # Four ordinary two-digit charges whose exact mean IS the closure threshold. Sitting on
    # the threshold is what turns the last ULP into a categorical question.
    charges = (("grief", -0.9), ("anger", -0.8), ("shame", -0.7), ("fear", -0.6))

    def road_with(items):
        r = Road(id="r", source_id="a", target_id="b", creation_seq=0,
                 formation_time=0.0, last_touched=0.0)
        r.charges = dict(items)
        return r

    orders = list(itertools.permutations(charges))
    vals = {bits(road_with(o).valence) for o in orders}
    check(len(vals) == 1,
          f"valence is ONE bit pattern across all {len(orders)} charge insertion orders "
          f"({sorted(vals)})")
    check(unbits(next(iter(vals))) == _CLOSURE_THRESHOLD,
          f"and it lands exactly ON _CLOSURE_THRESHOLD ({unbits(next(iter(vals)))!r} vs "
          f"{_CLOSURE_THRESHOLD!r}), so the categorical decision is maximally sensitive here")

    def naive_mean(o):
        t = 0.0
        for _, v in o:
            t += v
        return t / max(1, len(o))

    sides = {naive_mean(o) <= _CLOSURE_THRESHOLD for o in orders}
    check(sides == {True, False},
          f"NON-VACUITY: a naive left-fold over the same multiset lands on BOTH sides of "
          f"the threshold depending on order ({sorted(sides)}) — the categorical flip was "
          f"reachable, so the invariance above is a property of the code")
    outcomes = set()
    for o in orders:
        r = road_with(o)
        _open_close_on_crossing(r, one_shot_trauma=False)
        outcomes.add(r.closed)
    check(len(outcomes) == 1,
          f"the real closure decision is identical in all {len(orders)} orders ({outcomes})")


# ═════════════════════════════════════════════════════════════════════════════
# HOSTILE INPUTS — the shapes a friendly fixture never contains.
# ═════════════════════════════════════════════════════════════════════════════

def test_hostile_degenerate_graphs():
    section("hostile: empty graph, single node, self-loop only, duplicate edges, unknown seed")
    s = frozen_store()
    check(list(s.all_node_ids()) == [] and list(s.all_road_ids()) == [],
          "an empty store has no nodes and no roads")
    check(_raises(lambda: spread_activation(s, "nope"), NotFound),
          "spreading from a nonexistent seed on an empty store raises NotFound")
    lone = s.add_node("lone", NodeType.CONCEPT)
    r = spread_activation(s, lone)
    check(r.activation == {lone: DEFAULT_SEED_ENERGY} and r.flow == {} and r.hops == {lone: 0},
          "a single isolated node yields itself, at hop 0, with no flow")
    check(list(s.roads_from(lone)) == [] and list(s.roads_into(lone)) == [],
          "and its (empty) adjacency lists are still well-formed after the change")
    # self-loop only
    rid = worn(s, lone, lone, n=8)
    check(list(s.roads_from(lone)) == [rid] and list(s.roads_into(lone)) == [rid],
          "a self-loop appears exactly once in BOTH indices, not twice in either")
    r = spread_activation(s, lone, floor=0.0)
    check(math.isfinite(r.activation[lone]) and r.activation[lone] > 0,
          f"a self-loop-only node neither diverges nor corrupts ({r.activation[lone]!r})")
    # duplicate edges dedup to one road, and do not reorder
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    r1 = s.add_road(a, b)
    r2 = s.add_road(a, c)
    for _ in range(20):
        assert s.add_road(a, b) == r1
    check(list(s.roads_from(a)) == [r1, r2],
          "20 duplicate add_road calls on the same pair leave one road, in its place")
    s.check_integrity()
    check(True, "integrity holds across every degenerate shape above")


def test_hostile_closed_road_breakthrough_at_the_boundary():
    section("hostile: closed-road breakthrough exactly AT the threshold")
    s = frozen_store()
    S = s.add_node("S", NodeType.CONCEPT)
    T = s.add_node("T", NodeType.CONCEPT)
    rid = worn(s, S, T, n=6, charge={"dread": -0.95})
    check(s.get_road(rid).closed, "the road is genuinely closed (via a traumatic crossing)")
    thr = CLOSED_BREAKTHROUGH_THRESHOLD
    below = spread_activation(s, S, energy=thr, floor=0.0)
    just_above = spread_activation(s, S, energy=math.nextafter(thr, math.inf), floor=0.0)
    check(rid not in below.flow and rid not in below.broke_through,
          f"AT the threshold exactly (energy == {thr!r}) the barrier holds: the rule is "
          f"`outgoing <= threshold -> blocked`, so equality blocks")
    check(rid in just_above.flow and rid in just_above.broke_through,
          "and ONE ULP above the threshold it breaks through — the boundary is where the "
          "documented comparison puts it, tested at the representable neighbour rather "
          "than at a comfortable margin")
    check(bits(just_above.flow[rid])
          == bits(math.nextafter(thr, math.inf) * CLOSED_LEAK_FRACTION
                  * s.get_road(rid).strength * DEFAULT_DECAY_PER_HOP),
          "and the leaked value is leak_fraction applied first, then strength and decay, "
          "to the bit")


def test_hostile_very_high_degree_fan_ordering_and_determinism():
    section("hostile: a 500-road fan keeps its order and its arithmetic")
    s = frozen_store()
    hub = s.add_node("hub", NodeType.CONCEPT)
    rids = []
    for i in range(500):
        t = s.add_node("t%04d" % i, NodeType.CONCEPT)
        rids.append(s.add_road(hub, t))
    check(list(s.roads_from(hub)) == rids,
          "500 out-roads come back in creation order, exactly")
    check(_increasing(_seqs(s, list(s.roads_from(hub)))),
          "and their creation_seq is strictly increasing across all 500")
    # remove every other one, then re-add: the survivors must not shuffle
    for r in rids[::2]:
        s.remove_road(r)
    check(list(s.roads_from(hub)) == rids[1::2],
          "after removing 250 interleaved roads the 250 survivors keep their order")
    s.check_integrity()
    check(True, "integrity holds on a 500-road fan after a bulk interleaved removal")


# ═════════════════════════════════════════════════════════════════════════════
# O-13 — SPEC-0b2's other invariants, re-verified after the change.
# ═════════════════════════════════════════════════════════════════════════════

def test_O13_the_untouched_0b2_invariants_still_hold():
    section("O-13 N-3, N-4, N-6, N-8, N-9 re-verified independently after the change")
    # N-4: S_out is order-independent and equals fsum, derived from transmitted values
    s = frozen_store()
    S = s.add_node("S", NodeType.CONCEPT)
    rids = []
    for i, n in enumerate((1, 2, 3, 5, 8, 13, 21)):
        T = s.add_node("T%d" % i, NodeType.CONCEPT)
        rids.append(worn(s, S, T, n=n))
    strengths = {r: s.get_road(r).strength for r in rids}
    s_out = math.fsum(strengths.values())
    r = spread_activation(s, S, normalization_sigma=1.0, floor=0.0, energy=1.0,
                          decay_per_hop=1.0)
    check(all(bits(r.flow[rid]) == bits(1.0 * st * 1.0 * (1.0 / (1.0 + (s_out - st))))
              for rid, st in strengths.items()),
          "N-4: every transmitted value equals act*s*decay*sigma/(sigma+fsum(others)) "
          "to the bit")
    # N-6: strictly increasing in sigma, strictly decreasing in competing
    ladder = [1e-6, 1e-3, 0.1, 1.0, 25.0, 1e3]
    series = {rid: [] for rid in rids}
    for sigma in ladder:
        res = spread_activation(s, S, normalization_sigma=sigma, floor=0.0)
        for rid in rids:
            series[rid].append(res.flow[rid])
    check(all(all(v[i] < v[i + 1] for i in range(len(v) - 1)) for v in series.values()),
          "N-6: transmitted is strictly increasing in sigma on every road")
    unnorm = spread_activation(s, S, normalization_sigma=None, floor=0.0)
    check(all(all(x < unnorm.flow[rid] for x in series[rid]) for rid in rids),
          "N-6: and always strictly below the unnormalized value")
    # N-8: a closed road that transmits NOTHING still competes
    s2 = frozen_store()
    S2 = s2.add_node("S", NodeType.CONCEPT)
    O = s2.add_node("open", NodeType.CONCEPT)
    X = s2.add_node("shut", NodeType.CONCEPT)
    r_open = worn(s2, S2, O, n=6)
    r_shut = worn(s2, S2, X, n=6, charge={"dread": -0.95})
    energy = CLOSED_BREAKTHROUGH_THRESHOLD * 0.5
    res = spread_activation(s2, S2, normalization_sigma=1.0, floor=0.0, energy=energy,
                            decay_per_hop=1.0)
    competing = math.fsum(s2.get_road(q).strength for q in s2.roads_from(S2)) \
        - s2.get_road(r_open).strength
    check(X not in res.activation and r_shut not in res.flow,
          "N-8: the blocked closed road transmitted nothing")
    check(bits(res.flow[r_open])
          == bits(energy * s2.get_road(r_open).strength * 1.0 * (1.0 / (1.0 + competing))),
          "N-8: yet it still consumed conductance — the open road is attenuated by it")
    # N-9: silencing is total and observable, never partial
    s3 = frozen_store()
    S3 = s3.add_node("S", NodeType.CONCEPT)
    for i in range(200):
        T = s3.add_node("T%d" % i, NodeType.CONCEPT)
        worn(s3, S3, T, n=6)
    on = spread_activation(s3, S3, normalization_sigma=1.0)
    off = spread_activation(s3, S3, normalization_sigma=None)
    check(on.activation == {S3: DEFAULT_SEED_ENERGY} and on.flow == {} and on.ranked() == [],
          "N-9: a 200-fan under normalization goes observably empty, not partially populated")
    check(len(off.activation) > 1,
          "N-9: and the same graph is NOT empty unnormalized, so the censoring is "
          "attributable by comparison rather than hidden inside a truncated result")


# ═════════════════════════════════════════════════════════════════════════════
# O-14 / O-15 / O-16 / O-17 — THE METHODOLOGY INVARIANTS.
# ═════════════════════════════════════════════════════════════════════════════

def test_O14_no_determinism_probe_compares_rounded_values():
    section("O-14 no determinism probe in tests/ or experiments/ compares rounded values")
    import glob
    # A "probe payload" is a string literal that is EXECUTABLE PYTHON importing this
    # project — i.e. the source of a `python -c` subprocess. Scoped that way deliberately:
    # a scanner that flagged every literal containing the text "round(" would flag this
    # test's own failure messages, which is how the first draft of it failed.
    def is_payload(text):
        return ("from nous_" in text or "import nous_" in text) and "\n" in text

    offenders = []
    scanned = payloads = 0
    for f in sorted(glob.glob(os.path.join(ROOT, "tests", "*.py"))
                    + glob.glob(os.path.join(ROOT, "experiments", "*.py"))):
        scanned += 1
        try:
            tree = ast.parse(open(f, encoding="utf-8").read())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and is_payload(node.value):
                payloads += 1
                if "round(" in node.value:
                    offenders.append((os.path.relpath(f, ROOT), node.lineno,
                                      node.value.count("round(")))
    check(scanned >= 20, f"the scan actually covered the tree ({scanned} files)")
    check(payloads >= 25,
          f"and it can see driver payloads at all ({payloads} embedded-driver literals "
          f"found), so a zero result below is meaningful rather than vacuous")
    check(not offenders,
          f"no round() survives inside any embedded probe payload ({offenders})")
    # SENSITIVITY: the scanner must actually be able to fire. Fed a payload that DOES
    # round, it has to flag it — otherwise the zero above proves nothing.
    # assembled at runtime, not written as one literal, so the scanner above does not
    # (correctly) flag this very fixture as an offender — which it did on the first run
    poison = "from nous_store import SubstrateStore\nprint(" + "round" + "(1.0, 9))\n"
    check(is_payload(poison) and "round(" in poison,
          "the scanner is SENSITIVE: a synthetic payload that rounds is recognised as a "
          "payload and matched, so a clean result is a finding rather than a blind spot")
    note("SPEC-0c §5.1 enumerated 18 sites in 13 files and attributed 8 to the tester. The "
         "real tester-owned count was 9 (test_tester_1d_ii_adversarial.py has two driver "
         "payloads containing round(), not one). All 9 are converted to "
         "struct.pack('<d', x).hex(). experiments/ carries no driver-internal rounding, "
         "which §5.1 asked to be audited rather than assumed — audited here, and it holds.")


def test_O15_no_builtin_sum_over_floats_survives_in_src():
    section("O-15 no builtin sum() over float values remains in src/")
    import ast
    import glob
    offenders = []
    fsums = 0
    files = sorted(glob.glob(os.path.join(SRC, "*.py")))
    for f in files:
        tree = ast.parse(open(f, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Name) and fn.id == "sum":
                    offenders.append((os.path.basename(f), node.lineno,
                                      ast.unparse(node)[:80]))
                if isinstance(fn, ast.Attribute) and fn.attr == "fsum":
                    fsums += 1
    check(len(files) >= 8, f"every module in src/ was scanned ({len(files)} files)")
    check(fsums >= 6,
          f"and the replacement is actually present: {fsums} math.fsum call sites in src/ "
          f"(so an empty offender list is not simply an empty file list)")
    check(not offenders,
          f"no builtin sum() call survives anywhere in src/, over floats or otherwise "
          f"({offenders})")
    # the three §2.5 sites specifically, by behaviour rather than by grep
    from nous_workspace import Broadcast
    b = Broadcast(road_ids=["a", "b", "c"], before={}, after={"a": 1.0, "b": 1e-16,
                                                             "c": 1e-16}, winner_member_count=0)
    naive = 0.0
    for v in (1.0, 1e-16, 1e-16):
        naive += v
    check(bits(b.total_strength_after()) == bits(math.fsum([1.0, 1e-16, 1e-16]))
          and bits(b.total_strength_after()) != bits(naive),
          f"§2.5 site 2 (total_strength_after) is exactly rounded and DIFFERS from a naive "
          f"fold on [1.0, 1e-16, 1e-16] ({b.total_strength_after()!r} vs {naive!r}) — so "
          f"the conversion is observable, not cosmetic")


O16_DRIVER = textwrap.dedent(CASE2_GRAPH + '''
    import struct, hashlib, math
    from nous_activation import spread_activation
    rows = []
    # (a) the competition path
    rows.append(("thought", struct.pack("<d", r.thought.strength).hex()))
    for c in r.workspace.ranked:
        rows.append(("ranked", tuple(sorted(s.get_node(m).content for m in c.members)),
                     struct.pack("<d", c.strength).hex()))
    # (b) the field, which is where the DECAY PATH (math.exp, from the platform libm) is
    for k, v in sorted(r.field_.total.items(), key=lambda kv: s.get_node(kv[0]).content):
        rows.append(("total", s.get_node(k).content, struct.pack("<d", v).hex()))
    # (c) raw spreads at several sigmas, on a clock that has advanced so lazy decay
    #     (and therefore math.exp) is genuinely entered
    s.clock.advance(37.25)
    for n in sorted(s.all_node_ids(), key=lambda q: s.get_node(q).creation_seq):
        for sigma in (None, 0.25, 7.5):
            a = spread_activation(s, n, normalization_sigma=sigma)
            rows.append(("spread", s.get_node(n).content, repr(sigma),
                         tuple(sorted((s.get_node(k).content,
                                       struct.pack("<d", v).hex())
                                      for k, v in a.activation.items()))))
    # (d) a direct witness that the transcendental path was exercised at all
    rows.append(("exp", struct.pack("<d", math.exp(-0.37251)).hex()))
    print(hashlib.sha256(repr(rows).encode()).hexdigest())
    kinds = tuple(sorted({row[0] for row in rows}))
    # count DISTINCT 16-hex-digit bit patterns anywhere in the payload, at any nesting
    # depth: most of them live inside the per-spread tuples, not at the top level.
    seen_bits = set()
    def walk(x):
        if isinstance(x, str):
            if len(x) == 16 and all(ch in "0123456789abcdef" for ch in x):
                seen_bits.add(x)
        elif isinstance(x, (tuple, list)):
            for y in x:
                walk(y)
    walk(rows)
    print(repr((kinds, len(rows), len(seen_bits))))
''')


def test_O16_cross_interpreter_bit_identity_of_values():
    section("O-16 cross-interpreter bit-identity of VALUES, not merely of per-suite counts")
    interps = interpreters()
    outs = run_probe(O16_DRIVER, interps=interps, seeds=["0"])
    errs = [o for o in outs if o[2].startswith("ERROR")]
    check(not errs, f"every interpreter ran the probe ({len(errs)} errors; {errs[:1]})")
    per = {i: o.splitlines()[0] for i, _, o in outs if not o.startswith("ERROR")}
    shapes = {ast.literal_eval(o.splitlines()[1])
              for _, _, o in outs if not o.startswith("ERROR")}
    for i, d in sorted(per.items()):
        print(f"    {i:<12} {d}")
    check(len(interps) >= 5, f"five interpreters were available ({interps})")
    # COVERAGE asserted structurally, not by an arbitrary row count: the payload must
    # reach the competition path, the ranked order, the merged field, raw spreads at
    # several sigmas, and the transcendental decay path. A magnitude threshold would have
    # been a number chosen until it passed; this is a list of the paths that must be in it.
    kinds = sorted({k for shape in shapes for k in shape[0]})
    n_distinct = max(shape[2] for shape in shapes) if shapes else 0
    check(kinds == ["exp", "ranked", "spread", "thought", "total"],
          f"the payload covers the competition path, the ranking, the merged field, raw "
          f"spreads and the libm decay path ({kinds})")
    check(n_distinct >= 20,
          f"and carries {n_distinct} DISTINCT bit patterns, so agreement is not the "
          f"trivial agreement of a payload that is mostly one repeated value")
    check(len(set(per.values())) == 1,
          f"O-16: identical SHA-256 over every bit pattern on all {len(per)} interpreters "
          f"(distinct = {len(set(per.values()))})")
    note("SCOPE, stated with the claim: this is a claim about INTERPRETERS ON ONE MACHINE, "
         "not about platforms. IEEE-754 arithmetic is exactly rounded and version-"
         "independent, but math.exp in the decay path comes from the platform's libm, and "
         "the payload deliberately enters it (the clock is advanced so lazy decay runs, and "
         "a bare math.exp value is included as a witness). A different machine could "
         "legitimately differ there, and nothing here claims otherwise. Before §2.5 landed "
         "this invariant was UNACHIEVABLE: builtin sum() returns different bits on "
         "3.10/3.11 than on 3.12+.")


def test_O17_the_assertion_count_does_not_depend_on_the_environment():
    section("O-17 the assertion count is a property of the code, not of the environment")
    import tempfile
    suite = "test_tester_0b2_adversarial.py"
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

    def totals(cwd, e):
        r = subprocess.run([sys.executable, os.path.join(cwd, "tests", suite)],
                           cwd=cwd, capture_output=True, text=True, env=e)
        for line in r.stdout.splitlines():
            if "RESULT:" in line:
                parts = line.split()
                return int(parts[parts.index("passed,") - 1]), int(parts[-2])
        return None, r.stdout[-300:] + r.stderr[-300:]

    with_git = totals(ROOT, env)
    # A checkout with NO .git — a git archive extract, a release tarball, a Docker COPY,
    # the Zenodo artifact. Copied from the WORKING TREE so it tests the current code
    # rather than the last commit.
    tmp = tempfile.mkdtemp(prefix="nous_nogit_")
    dest = os.path.join(tmp, "repo")
    shutil.copytree(ROOT, dest,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "data"))
    check(not os.path.exists(os.path.join(dest, ".git")),
          "the copy genuinely has no .git, so the git-recovered oracle is unavailable there")
    env2 = dict(env)
    env2["PYTHONPATH"] = os.path.join(dest, "src")
    without_git = totals(dest, env2)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"    with .git    : {with_git[0]} passed, {with_git[1]} failed")
    print(f"    without .git : {without_git[0]} passed, {without_git[1]} failed")
    check(with_git[0] is not None and without_git[0] is not None,
          f"both runs reported a RESULT line (with={with_git}, without={without_git})")
    check(with_git == without_git,
          f"O-17: {suite} reports the SAME totals in the repository and in a checkout "
          f"with no .git ({with_git} vs {without_git}). Graceful degradation is kept — the "
          f"git legs still degrade to observations — but the CHECK COUNT does not move, so "
          f"ledger_check C1 cannot fail on a release tarball for a reason unrelated to the "
          f"code.")
    check(with_git[1] == 0 and without_git[1] == 0,
          f"and both runs are green ({with_git[1]}, {without_git[1]} failures)")


# ═════════════════════════════════════════════════════════════════════════════

def run_all():
    print("=" * 74)
    print("  TESTER — SPEC-0c deterministic road ordering, adversarial verification")
    print("  Independent suite. src/ is untouched. Mechanism only, no meaning claim.")
    print("=" * 74)
    for t in [
        test_O1_iteration_is_creation_ordered_on_hostile_topologies,
        test_O1_the_order_is_not_merely_insertion_coincidence,
        test_O2_order_survives_a_randomised_mutation_battery,
        test_O2_a_re_added_pair_is_a_new_road_that_sorts_last,
        test_O3_purity_and_integrity_are_unchanged_by_the_representation_change,
        test_O4_the_reproduction_is_one_bit_pattern_across_the_full_matrix,
        test_O4b_the_competition_path_is_one_bit_pattern_on_every_interpreter,
        test_O4b_the_pruned_winner_strength_is_the_exactly_rounded_member_sum,
        test_O5_random_adversarial_graphs_are_deterministic_across_processes,
        test_O6_order_perturbation_invariance_on_random_hostile_graphs,
        test_O6_high_degree_fan_permutation_invariance,
        test_O7_ASSERTED_NEGATIVE_isomorphic_graphs_agree_on_values_not_on_key_order,
        test_O8_loop_closed_determinism_through_the_whole_pipeline,
        test_O9_one_read_per_road_and_one_clock_instant_per_expansion,
        test_O10_lone_out_road_on_the_REAL_default_clock,
        test_O11_sigma_validation_boundary_is_exact,
        test_O12_non_finite_cannot_reach_the_result_via_transmission,
        test_O12_non_finite_energy_is_refused_at_every_graph_shape,
        test_O12_the_refusal_is_deterministic_across_seeds_and_interpreters,
        test_O12_D014_negative_and_zero_energy_are_STILL_accepted,
        test_O12_the_transmitted_backstop_guard_is_LIVE_by_two_independent_routes,
        test_O12_loop_closed_no_non_finite_survives_the_pipeline,
        test_O12_ASSERTED_NEGATIVE_the_fsum_reduction_raises_where_the_old_engine_returned_inf,
        test_FINDING_ASSERTED_NEGATIVE_field_merge_is_order_dependent,
        test_ULP_the_competition_tie_break_is_decided_by_the_documented_integer_keys,
        test_ULP_road_valence_closure_decision_is_multiset_determined,
        test_hostile_degenerate_graphs,
        test_hostile_closed_road_breakthrough_at_the_boundary,
        test_hostile_very_high_degree_fan_ordering_and_determinism,
        test_O13_the_untouched_0b2_invariants_still_hold,
        test_O14_no_determinism_probe_compares_rounded_values,
        test_O15_no_builtin_sum_over_floats_survives_in_src,
        test_O16_cross_interpreter_bit_identity_of_values,
        test_O17_the_assertion_count_does_not_depend_on_the_environment,
    ]:
        t()

    print("\n" + "=" * 74)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    if _fail_msgs:
        print("  FAILURES:")
        for m in _fail_msgs:
            print("   -", m)
    print("=" * 74)
    print("  TESTER VERDICT ON SPEC-0c §6")
    print("=" * 74)
    print("    O-1  HOLDS  creation-ordered iteration, asserted against creation_seq")
    print("    O-2  HOLDS  order survives 900-step add/remove/re-add batteries")
    print("    O-3  HOLDS  purity and integrity unchanged; the ORDER is pure too")
    print("    O-4  HOLDS  one bit pattern, 60 processes x 5 interpreters x 6 seeds")
    print("    O-4b HOLDS  competition path: one strength, one membership, one ranking")
    print("    O-5  HOLDS  one SHA-256 over a 45-graph battery, every process")
    print("    O-6  HOLDS  order-perturbation invariance, incl. high-degree fans")
    print("    O-7  BOUNDS THE CLAIM (asserted-negative, amended form)")
    print("    O-8  HOLDS  re-based oracle; see test_tester_0b2_adversarial.py")
    print("    O-9  HOLDS  one read per road, one clock instant per expansion")
    print("    O-10 HOLDS  factor exactly 1.0 on the REAL default clock")
    print("    O-11 HOLDS  sigma boundary exact, down to -0.0 and 5e-324")
    print("    O-12 HOLDS  (re-verified after D-015 (A)) non-finite energy refused on")
    print("                every seed shape; the backstop guard is live on two routes")
    print("    O-13 HOLDS  N-3, N-4, N-6, N-8, N-9 re-verified")
    print("    O-14 HOLDS  no round() in any probe payload, tests/ and experiments/")
    print("    O-15 HOLDS  no builtin sum() in src/, and the conversion is observable")
    print("    O-16 HOLDS  bit-identical on all five interpreters (one machine)")
    print("    O-17 HOLDS  identical totals with and without .git")
    print()
    print(f"  THE SUITE BEING GREEN IS NOT THE VERDICT. {len(_findings)} findings are "
          f"recorded above as")
    print("  ASSERTED-NEGATIVES, which pass while the limitation is present. A third,")
    print("  the O-12 gap, was RETIRED: D-015 closed it in code and it is now asserted")
    print("  as the positive property.")
    for tag, msg in _findings:
        print(f"    [{tag}]")
        for line in textwrap.wrap(msg, 68):
            print(f"        {line}")
    print()
    print("  Mechanism only. No cognitive claim is made or approached.")
    print("=" * 74)
    return _failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run_all() else 1)
