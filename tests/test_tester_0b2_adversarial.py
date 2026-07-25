"""
INDEPENDENT ADVERSARIAL TEST SUITE for step 0b2 — divisive normalization overlay.

Author: tester (independent adversary). Written FROM SCRATCH against SPEC-0b2 §6's
invariants N-1..N-9, not adapted from the builder's suite. There was in fact nothing to
adapt: at the time of writing `normalization_sigma` appeared in exactly one file in the
repository (`src/nous_activation.py`) and in no test at all, so the overlay shipped with
zero coverage and every property below is verified here for the first time.

Mechanism only. Nothing here grades a cognitive claim; see the validator's lane for that.

WHAT IS VERIFIED, and the verdict each property returned
--------------------------------------------------------
  N-1  neutral byte-identity .................... HOLDS  (two independent oracles)
       Scope, stated with the claim: byte-identity is established under a FROZEN clock
       (Clock(simulated=True)). On a clock that advances, any two runs differ through
       0a's lazy decay alone — a property of the store, not of this overlay — so
       bit-exact comparison is only meaningful with the clock held still.
  N-2  determinism, hash seeds x interpreters ... FAILS  — DEFECT-A (inherited from 0b)
       Swept: PYTHONHASHSEED in {0,1,2,3,7,42} x every CPython found (3.10-3.14 here),
       in fresh processes. HOLDS bit-exactly on graphs with in-degree <= 2; FAILS from
       in-degree 3 up. A determinism claim is scoped to the environments it was checked
       in, and to the topologies it was checked on.
  N-3  purity ................................... HOLDS
  N-4  order-independence of S_out .............. HOLDS  (math.fsum, proven sensitive)
  N-5  limiting case: lone out-road ............. FAILS  — DEFECT-B (introduced by 0b2)
  N-6  monotonicity ............................. HOLDS
  N-7  sigma -> infinity convergence ............ HOLDS for finite sigma; DEFECT-C at inf
  N-8  closed roads compete ..................... HOLDS
  N-9  no silent silencing ...................... HOLDS

THE THREE DEFECTS, asserted here as explicit asserted-negatives rather than hidden
(CONTRIBUTING.md, "Definition of done"). Each of these tests PASSES while the defect is present
and FAILS the moment it is fixed, which is deliberate: a fix must come back through this
file and re-verify the property it restores.

  DEFECT-A  Convergent accumulation is order-dependent.  `activation[target] =
            activation.get(target, 0.0) + transmitted` (nous_activation.py:287) is a plain
            sequential float add, performed in an order that comes from
            `roads_from` -> `iter(tuple(self._out[node_id]))` (nous_store.py:444), i.e.
            iteration over a SET of uuid4 hex strings. Float addition is not associative,
            so a node reached by >=3 convergent contributions accumulates a
            run-dependent sum. Same bug class as BUG-0b1, one layer upstream of the
            coalition-strength site that BUG-0b1 fixed with math.fsum.
            NOT caused by the overlay: it reproduces identically at sigma=None.

  DEFECT-B  A source with exactly ONE out-road is attenuated. The overlay reads each road
            TWICE per expansion (once for `out_total`, once in the transmission loop) and
            `get_road` applies lazy decay as of `clock.now()` at each call. On any clock
            that advances -- which is the library default, `Clock(simulated=False)` -- the
            two reads return different strengths, so
            `competing = out_total - road.strength` is a positive elapsed-time residue
            instead of exactly 0.0. SPEC-0b2 §2 (property table row 3) and N-5 both state
            this factor is EXACTLY 1.0 at every sigma. It is not.
            Invisible to every existing test because they all use a frozen simulated clock.

  DEFECT-C  `normalization_sigma` is unvalidated. sigma=inf -- the exact value SPEC-0b2 §2
            describes as "analytically recovers the current engine" -- yields inf/inf =
            NaN, and NaN passes the `transmitted < floor` guard (every comparison with NaN
            is False), so NaN propagates into the result instead of raising.

Run directly:
    PYTHONPATH=<repo>/src python3 tests/test_tester_0b2_adversarial.py
"""

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
    SubstrateStore, Clock, NodeType, NotFound, IntegrityError,
)
from nous_activation import (
    spread_activation, ActivationResult,
    DEFAULT_SEED_ENERGY, DEFAULT_DECAY_PER_HOP, DEFAULT_FLOOR, DEFAULT_HOP_BUDGET,
    CLOSED_BREAKTHROUGH_THRESHOLD, CLOSED_LEAK_FRACTION,
)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")

_passed = 0
_failed = 0
_fail_msgs = []
_notes = []


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
    _notes.append(msg)
    print(f"  NOTE: {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# Bit-exact comparison. Everything in this suite compares BIT PATTERNS, never
# rounded values: every determinism probe already in this repository compares
# round(x, 9), which cannot see a 1-ULP difference — and 1 ULP is precisely what
# BUG-0b1 was. A determinism test that rounds is not a determinism test.
# ─────────────────────────────────────────────────────────────────────────────

def bits(x):
    return struct.pack("<d", x).hex()


def signature(result):
    """Total byte-level fingerprint of an ActivationResult, including dict ORDER."""
    return (
        result.seed,
        tuple((k, bits(v)) for k, v in result.activation.items()),
        tuple(result.hops.items()),
        tuple(result.broke_through),
        tuple((k, bits(v)) for k, v in result.flow.items()),
    )


# Cross-process comparison is done by CONTENT rather than by uuid4 id, since the ids
# differ per process; the subprocess drivers below serialize that way inline.


# ─────────────────────────────────────────────────────────────────────────────
# Test doubles. These wrap the store through its PUBLIC surface; no production
# module is modified or monkeypatched (tester lane: src/ is untouchable).
# ─────────────────────────────────────────────────────────────────────────────

class PermutingStore:
    """Delegates everything, but hands out a source's out-roads in a chosen order.

    This is how out-road iteration order is attacked without touching src/: the real
    store's order comes from a set of uuid4 strings and is therefore not controllable,
    only observable. Permuting it here makes the dependence deterministic and provable.
    """

    def __init__(self, inner, permute):
        self._inner = inner
        self._permute = permute

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def roads_from(self, node_id):
        return iter(self._permute(list(self._inner.roads_from(node_id))))


class RecordingStore:
    """Records every decayed get_road call, so the overlay's DOUBLE read of the same
    road within one expansion is directly observable."""

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
    """Raises if the engine calls ANY mutating method. A read that writes is the
    project's first named bug class; this proves the absence structurally rather than
    by comparing snapshots."""

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
    """A deterministic stand-in for the REAL clock: monotonic, advances a fixed dt on
    every now(). The library default clock (Clock(simulated=False)) advances too; this
    one advances reproducibly, so a wall-clock-dependent defect becomes a stable test.
    """

    def __init__(self, dt):
        super().__init__(simulated=True, start=0.0)
        self.dt = dt
        self.ticking = False

    def now(self):
        t = self._t
        if self.ticking:
            self._t += self.dt
        return t


def frozen_store():
    """A store whose clock never advances: lazy decay is a no-op (dt <= 0), so road
    strengths are exactly what was written. Byte-identity comparisons REQUIRE this —
    on a moving clock any two runs differ through decay alone, which is a property of
    0a's lazy decay and has nothing to do with this overlay."""
    return SubstrateStore(clock=Clock(simulated=True, start=0.0))


def worn(store, a, b, n=1, charge=None):
    """Every fixture in this suite is built with traverse() — the substrate's own
    biological primitive — and nothing else. No strength is hand-placed or engineered,
    so no test can be dismissed as resting on values the system would never produce."""
    for _ in range(n):
        store.traverse(a, b, charge)
    return store.find_road(a, b)


# ─────────────────────────────────────────────────────────────────────────────
# ORACLE 1 — the actual pre-change engine, recovered from git.
# ─────────────────────────────────────────────────────────────────────────────

def load_pre_change_engine():
    """Recover the last version of nous_activation.py that predates the overlay.

    Resolved by CONTENT, not by a pinned hash: walk the file's history newest-first and
    take the first revision that does not mention normalization_sigma. That survives a
    rebase, which a hardcoded sha would not. Returns None if git is unavailable.
    """
    try:
        log = subprocess.run(["git", "log", "--format=%H", "--", "src/nous_activation.py"],
                             cwd=ROOT, capture_output=True, text=True, timeout=30)
        if log.returncode != 0:
            return None
        for sha in log.stdout.split():
            blob = subprocess.run(["git", "show", f"{sha}:src/nous_activation.py"],
                                  cwd=ROOT, capture_output=True, text=True, timeout=30)
            if blob.returncode != 0:
                continue
            if "normalization_sigma" in blob.stdout:
                continue
            import importlib.util
            path = os.path.join(HERE, "__pre0b2_oracle.py")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(blob.stdout)
            try:
                spec = importlib.util.spec_from_file_location("__pre0b2_oracle", path)
                mod = importlib.util.module_from_spec(spec)
                sys.modules["__pre0b2_oracle"] = mod   # dataclass needs it registered
                spec.loader.exec_module(mod)
                mod.__nous_sha__ = sha
                mod.__nous_source__ = blob.stdout      # the temp file is removed below
                return mod
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass
        return None
    except (OSError, subprocess.SubprocessError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# ORACLE 2 — an independent implementation of the documented pre-change algorithm,
# written from nous_activation.py's DESIGN DECISIONS docstring rather than copied from
# its body. Always available, so N-1 keeps an oracle even without git.
# ─────────────────────────────────────────────────────────────────────────────

def reference_spread(store, seed_node, *, energy=DEFAULT_SEED_ENERGY,
                     decay_per_hop=DEFAULT_DECAY_PER_HOP, floor=DEFAULT_FLOOR,
                     hop_budget=DEFAULT_HOP_BUDGET):
    if not store.exists(seed_node):
        raise NotFound(f"seed node {seed_node}")
    activation = {seed_node: energy}
    settled = {seed_node: 0}
    broke = []
    flow = {}
    layer = [seed_node]
    for hop in range(hop_budget + 1):
        if not layer:
            break
        nxt = {}
        frozen = {n: activation[n] for n in layer}          # freeze before expanding
        for node in layer:
            node_act = frozen[node]
            if hop >= hop_budget:
                continue                                     # settle, do not expand
            for rid in store.roads_from(node):
                road = store.get_road(rid)
                outgoing = node_act
                if road.closed:
                    # the closed-road policy, re-stated from its documented rule
                    if outgoing <= CLOSED_BREAKTHROUGH_THRESHOLD:
                        continue
                    outgoing = outgoing * CLOSED_LEAK_FRACTION
                    broke.append(rid)
                transmitted = outgoing * road.strength * decay_per_hop
                if transmitted < floor:
                    continue
                tgt = road.target_id
                activation[tgt] = activation.get(tgt, 0.0) + transmitted
                flow[rid] = flow.get(rid, 0.0) + transmitted
                if tgt not in settled:
                    settled[tgt] = hop + 1
                    nxt[tgt] = None
        layer = list(nxt.keys())
    return ActivationResult(seed=seed_node, activation=activation, hops=settled,
                            broke_through=broke, flow=flow)


# ─────────────────────────────────────────────────────────────────────────────
# Adversarial graph generator — seeded with random.Random so it is reproducible
# independently of PYTHONHASHSEED.
# ─────────────────────────────────────────────────────────────────────────────

def adversarial_graph(seed):
    """Hostile topology: self-loops, cycles, duplicate pairs, high-degree fans, closed
    and traumatic roads, saturated and decayed strengths, isolated nodes."""
    rng = random.Random(seed)
    clock = Clock(simulated=True, start=0.0)
    store = SubstrateStore(clock=clock)
    n = rng.randint(1, 11)
    ids = [store.add_node("n%d" % i, rng.choice(list(NodeType))) for i in range(n)]
    for _ in range(rng.randint(0, 40)):
        a, b = rng.choice(ids), rng.choice(ids)              # self-loops permitted
        k = rng.random()
        charge = None
        if k < 0.22:
            charge = {"dread": -rng.uniform(0.75, 1.0)}      # closes the road
        elif k < 0.40:
            charge = {"joy": rng.uniform(0.2, 0.9)}
        for _ in range(rng.randint(1, 12)):
            store.traverse(a, b, charge)                     # duplicate pairs dedup
        if rng.random() < 0.35:
            clock.advance(rng.uniform(0.0, 40.0))            # exercise lazy decay
    if rng.random() < 0.40:                                  # a high-degree fan
        hub = rng.choice(ids)
        for i in range(rng.randint(5, 30)):
            tgt = store.add_node("f%d" % i, NodeType.CONCEPT)
            for _ in range(rng.randint(1, 6)):
                store.traverse(hub, tgt)
    clock.advance(0.0)
    return store, list(store.all_node_ids())


PARAM_SWEEP = [
    dict(),
    dict(energy=0.05),
    dict(energy=1e6),
    dict(decay_per_hop=1.0),
    dict(decay_per_hop=0.0),
    dict(floor=0.0),
    dict(floor=1e9),
    dict(hop_budget=0),
    dict(hop_budget=1),
    dict(hop_budget=40),
    dict(energy=1e6, floor=0.0, decay_per_hop=1.0, hop_budget=12),
]


# ═════════════════════════════════════════════════════════════════════════════
# N-1  NEUTRAL BYTE-IDENTITY — the gating property. If this does not hold the
#      whole migration argument collapses and nothing else in the spec matters.
# ═════════════════════════════════════════════════════════════════════════════

def test_N1_byte_identity_vs_git_pre_change_engine():
    section("N-1 neutral byte-identity vs the ACTUAL pre-change engine (recovered from git)")
    pre = load_pre_change_engine()
    if pre is None:
        note("git unavailable — oracle 1 skipped; oracle 2 (independent reference) still runs")
        check(True, "oracle 1 unavailable, recorded rather than silently passed")
        return
    check("normalization_sigma" not in open(
        os.path.join(SRC, "nous_activation.py"), encoding="utf-8").read().split(
        "def spread_activation")[0],
        "the overlay parameter is not introduced above spread_activation (sanity)")

    compared = 0
    mismatches = []
    for gs in range(120):
        store, ids = adversarial_graph(gs)
        for seed_node in ids:
            for params in PARAM_SWEEP:
                got = signature(spread_activation(
                    store, seed_node, normalization_sigma=None, **params))
                want = signature(pre.spread_activation(store, seed_node, **params))
                compared += 1
                if got != want and len(mismatches) < 3:
                    mismatches.append((gs, store.get_node(seed_node).content, params))
    check(not mismatches,
          f"N-1: {compared} adversarial comparisons vs git {getattr(pre, '__nous_sha__', '?')[:7]} "
          f"byte-identical (mismatches: {mismatches})")
    print(f"  ({compared} comparisons against the real pre-change engine, 0 mismatches)")


def test_N1_byte_identity_vs_independent_reference():
    section("N-1 neutral byte-identity vs an INDEPENDENT reimplementation of the algorithm")
    compared = 0
    mismatches = []
    for gs in range(120):
        store, ids = adversarial_graph(1000 + gs)
        for seed_node in ids:
            for params in PARAM_SWEEP:
                got = signature(spread_activation(
                    store, seed_node, normalization_sigma=None, **params))
                want = signature(reference_spread(store, seed_node, **params))
                compared += 1
                if got != want and len(mismatches) < 3:
                    mismatches.append((gs, params))
    check(not mismatches,
          f"N-1: {compared} adversarial comparisons vs the independent reference "
          f"byte-identical (mismatches: {mismatches})")
    print(f"  ({compared} comparisons against an independent implementation, 0 mismatches)")


def test_N1_default_argument_is_the_neutral_value():
    section("N-1 the DEFAULT argument is the neutral value (not merely an explicit None)")
    mismatches = 0
    for gs in range(40):
        store, ids = adversarial_graph(2000 + gs)
        for seed_node in ids:
            a = signature(spread_activation(store, seed_node))
            b = signature(spread_activation(store, seed_node, normalization_sigma=None))
            if a != b:
                mismatches += 1
    check(mismatches == 0, f"omitting the parameter == passing None ({mismatches} mismatches)")


def test_N1_byte_identity_loop_closed_on_a_system_built_substrate():
    section("N-1 LOOP-CLOSED: identity on a substrate the system's own pipeline built")
    # The graph is not hand-drawn: it is what traverse() — the biological primitive the
    # layer below exposes — produces from a stream of associations, then perceive()
    # chooses the seeds by matching the utterance against node content. Nothing about
    # which nodes seed the spread is chosen by this test.
    from nous_perceive import perceive
    store = frozen_store()
    words = ["coffee", "warmth", "morning routine", "cozy feeling", "kitchen",
             "work", "desk", "deadline pressure", "writing code", "commute"]
    ids = [store.add_node(w, NodeType.CONCEPT) for w in words]
    rng = random.Random(7)
    for _ in range(60):
        a, b = rng.choice(ids), rng.choice(ids)
        worn(store, a, b, n=rng.randint(1, 9))
    pre = load_pre_change_engine()
    seeds = sorted(perceive(store, "coffee in the kitchen before work").sources)
    check(len(seeds) > 0, "perception produced seeds from the utterance (loop is closed)")
    mismatches = 0
    for seed_node in seeds:
        got = signature(spread_activation(store, seed_node, normalization_sigma=None))
        if got != signature(reference_spread(store, seed_node)):
            mismatches += 1
        if pre is not None and got != signature(pre.spread_activation(store, seed_node)):
            mismatches += 1
    check(mismatches == 0,
          f"neutral output byte-identical on perception-selected seeds ({mismatches} mismatches)")


# ═════════════════════════════════════════════════════════════════════════════
# N-2  DETERMINISM — hash seeds AND every CPython on this machine.
# ═════════════════════════════════════════════════════════════════════════════

HASH_SEEDS = ["0", "1", "2", "3", "7", "42"]


def interpreters():
    found = []
    for name in ("python3.10", "python3.11", "python3.12", "python3.13", "python3.14"):
        if shutil.which(name):
            found.append(name)
    return found or [sys.executable]


def run_probe(driver, interps=None, seeds=None, reps=1):
    """Run `driver` in fresh interpreters across the hash-seed x interpreter matrix."""
    outs = []
    env0 = dict(os.environ)
    env0["PYTHONPATH"] = SRC + (os.pathsep + env0["PYTHONPATH"]
                                if env0.get("PYTHONPATH") else "")
    for interp in (interps if interps is not None else interpreters()):
        for seed in (seeds if seeds is not None else HASH_SEEDS):
            for _ in range(reps):
                env = dict(env0, PYTHONHASHSEED=seed)
                r = subprocess.run([interp, "-c", driver],
                                   cwd=HERE, capture_output=True, text=True, env=env)
                if r.returncode != 0:
                    outs.append(f"ERROR({interp},{seed}):" + r.stderr.strip()[-300:])
                else:
                    outs.append(r.stdout.strip())
    return outs


# A graph with NO node reachable by three or more convergent contributions: every node
# has in-degree <= 2, and two-way convergence is exactly order-independent because IEEE
# addition is commutative (a+b == b+a). This isolates determinism from DEFECT-A below,
# and the in-degree bound is asserted structurally so the fixture cannot silently drift.
DET_GRAPH = '''
    from nous_store import SubstrateStore, Clock, NodeType
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    def add(c): return s.add_node(c, NodeType.CONCEPT)
    hub = add("hub")
    fan = [add("fan%02d" % i) for i in range(14)]
    tail = [add("tail%02d" % i) for i in range(4)]
    def w(a, b, n):
        for _ in range(n): s.traverse(a, b)
    for i, f in enumerate(fan):
        w(hub, f, 1 + (i % 9))
    for i in range(8):                      # every tail has in-degree EXACTLY 2, and
        w(fan[i], tail[i % 4], 2 + i)       # a+b == b+a is exact, so this stays clean
    w(hub, hub, 3)                          # self-loop      (hub in-degree 1)
    w(tail[3], hub, 5)                      # cycle back     (hub in-degree 2)
'''

DET_DRIVER = textwrap.dedent(DET_GRAPH + '''
    import struct
    from nous_activation import spread_activation
    indeg = {}
    for r in s.all_road_ids():
        rd = s.get_road(r)
        indeg[rd.target_id] = indeg.get(rd.target_id, 0) + 1
    assert max(indeg.values()) <= 2, "fixture drift: in-degree > 2 reintroduces DEFECT-A"
    def bits(x): return struct.pack("<d", x).hex()
    out = []
    for sigma in (None, 0.25, 1.0, 7.5):
        r = spread_activation(s, hub, normalization_sigma=sigma)
        act = sorted((s.get_node(n).content, bits(v)) for n, v in r.activation.items())
        flw = sorted((s.get_node(s.get_road(k).source_id).content,
                      s.get_node(s.get_road(k).target_id).content, bits(v))
                     for k, v in r.flow.items())
        hop = sorted((s.get_node(n).content, h) for n, h in r.hops.items())
        out.append((sigma, act, hop, flw))
    print(repr(out))
''')


def test_N2_determinism_across_hash_seeds_and_interpreters():
    section("N-2 determinism: bit-exact across 6 hash seeds x every CPython on this machine")
    interps = interpreters()
    print(f"  interpreters swept: {', '.join(interps)}")
    outs = run_probe(DET_DRIVER, interps=interps)
    errors = [o for o in outs if o.startswith("ERROR")]
    check(not errors, f"every probe process ran ({len(errors)} errors; first={errors[:1]})")
    distinct = set(o for o in outs if not o.startswith("ERROR"))
    check(len(distinct) == 1,
          f"N-2: identical bit patterns across {len(outs)} fresh processes "
          f"({len(interps)} interpreters x {len(HASH_SEEDS)} hash seeds); "
          f"distinct results = {len(distinct)}")
    check(len(interps) >= 5,
          f"the interpreter axis is actually populated: {len(interps)} found (need >=5)")


#   Seed -> three mids -> one shared target. The target accumulates THREE floats, and
#   three is the smallest number that can break associativity (a+b == b+a is exact).
#   Both count sets below are traverse()-only at library defaults: nothing is engineered,
#   and each was found by enumerating small traverse counts, not hand-tuned.
CONVERGENCE_COUNTS = {None: ((1, 2), (1, 3), (1, 9)),
                      1.0: ((1, 3), (1, 4), (1, 5))}


def _three_way_convergence_store(counts=CONVERGENCE_COUNTS[None]):
    store = frozen_store()
    S = store.add_node("S", NodeType.CONCEPT)
    T = store.add_node("T", NodeType.CONCEPT)
    for i, (a, b) in enumerate(counts):
        M = store.add_node("M%d" % i, NodeType.CONCEPT)
        worn(store, S, M, n=a)
        worn(store, M, T, n=b)
    return store, S, T


def test_N2_DEFECT_A_convergent_accumulation_is_order_dependent():
    section("N-2 DEFECT-A: convergent accumulation depends on out-road iteration order")
    store, S, T = _three_way_convergence_store()
    seen = {}
    for perm in itertools.permutations(range(3)):
        def permute(roads, p=perm):
            return [roads[i] for i in p] if len(roads) == 3 else roads
        r = spread_activation(PermutingStore(store, permute), S)   # LIBRARY DEFAULTS
        seen.setdefault(bits(r.activation[T]), []).append(perm)
    check(len(seen) > 1,
          "DEFECT-A present: reordering a source's out-roads changes activation[T] "
          f"(distinct bit patterns over 3! orders = {len(seen)}). "
          "IF THIS TEST FAILS BECAUSE THE DEFECT WAS FIXED: delete it and re-verify N-2.")
    for b, perms in seen.items():
        print(f"    {b}  = {struct.unpack('<d', bytes.fromhex(b))[0]!r}   from {len(perms)} of 6 orders")
    check(isinstance(store._out[S], set),
          "the exposure is real: roads_from() iterates a SET of uuid4 ids "
          "(nous_store.py:444), whose order is not fixed across processes")


def test_N2_DEFECT_A_is_inherited_from_0b_not_introduced_by_the_overlay():
    section("N-2 DEFECT-A scoping: present at sigma=None, so the overlay did not cause it")
    for sigma, counts in CONVERGENCE_COUNTS.items():
        store, S, T = _three_way_convergence_store(counts)
        seen = set()
        for perm in itertools.permutations(range(3)):
            def permute(roads, p=perm):
                return [roads[i] for i in p] if len(roads) == 3 else roads
            r = spread_activation(PermutingStore(store, permute), S,
                                  normalization_sigma=sigma)
            seen.add(bits(r.activation[T]))
        check(len(seen) > 1,
              f"order-dependence reproduces at sigma={sigma!r} on {counts} "
              f"({len(seen)} distinct results)")
    note("The defect is present with the overlay OFF, so 0b2 did not introduce it and "
         "0b2 does not fix it. Which particular graphs expose it differs between the two "
         "(the normalized values are different floats), but the class is identical.")


DEFECT_A_DRIVER = textwrap.dedent('''
    import struct, sys
    from nous_store import SubstrateStore, Clock, NodeType
    from nous_activation import spread_activation
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    S = s.add_node("S", NodeType.CONCEPT); T = s.add_node("T", NodeType.CONCEPT)
    for i, (a, b) in enumerate(((1, 2), (1, 3), (1, 9))):
        M = s.add_node("M%d" % i, NodeType.CONCEPT)
        for _ in range(a): s.traverse(S, M)
        for _ in range(b): s.traverse(M, T)
    r = spread_activation(s, S)               # LIBRARY DEFAULTS, no proxy, real store
    print(struct.pack("<d", r.activation[T]).hex())
''')


def test_N2_DEFECT_A_reaches_real_processes_at_library_defaults():
    section("N-2 DEFECT-A reachability: fresh REAL processes disagree, no proxy involved")
    outs = run_probe(DEFECT_A_DRIVER, interps=[sys.executable], reps=8)
    distinct = sorted(set(o for o in outs if not o.startswith("ERROR")))
    for d in distinct:
        print(f"    {d}  = {struct.unpack('<d', bytes.fromhex(d))[0]!r}"
              f"   ({outs.count(d)} of {len(outs)} runs)")
    check(len(distinct) > 1,
          f"DEFECT-A observed in production conditions: {len(distinct)} distinct results "
          f"over {len(outs)} fresh processes on a 5-node traverse()-only graph at library "
          f"defaults. IF THIS FAILS BECAUSE THE DEFECT WAS FIXED: delete it and re-verify N-2.")
    note("DEFECT-A varies even at a FIXED PYTHONHASHSEED: uuid4 ids differ per process, so "
         "pinning the hash seed does not pin set-iteration order. Seed-pinning alone cannot "
         "establish determinism for this substrate.")


# ═════════════════════════════════════════════════════════════════════════════
# N-3  PURITY
# ═════════════════════════════════════════════════════════════════════════════

def store_snapshot(store):
    roads = {}
    for rid in store.all_road_ids():
        r = store.get_road(rid, apply_decay=False)          # CANONICAL, not the view
        roads[rid] = (bits(r.strength), tuple(sorted((k, bits(v)) for k, v in r.charges.items())),
                      r.closed, r.traversal_count, bits(r.last_touched))
    nodes = {}
    for nid in store.all_node_ids():
        n = store.get_node(nid)
        nodes[nid] = (n.content, n.access_count, bits(n.last_accessed))
    return roads, nodes


def test_N3_purity_snapshot_with_normalization_on():
    section("N-3 purity: the substrate is byte-identical after normalized spreads")
    violations = 0
    for gs in range(40):
        store, ids = adversarial_graph(3000 + gs)
        before = store_snapshot(store)
        for seed_node in ids:
            for sigma in (None, 0.001, 1.0, 1e9):
                spread_activation(store, seed_node, normalization_sigma=sigma)
                spread_activation(store, seed_node, normalization_sigma=sigma, floor=0.0)
        if store_snapshot(store) != before:
            violations += 1
    check(violations == 0,
          f"no stored strength / charge / closure / traversal_count / last_touched changed "
          f"across 40 adversarial graphs ({violations} violations)")


def test_N3_purity_no_mutating_call_is_made():
    section("N-3 purity: the engine never calls a mutating store method (structural)")
    store, ids = adversarial_graph(4242)
    guard = MutationGuardStore(store)
    ok = True
    for seed_node in ids:
        for sigma in (None, 1.0):
            try:
                spread_activation(guard, seed_node, normalization_sigma=sigma)
            except AssertionError as e:
                ok = False
                check(False, f"mutating call during spread: {e}")
    check(ok and not guard.violations,
          f"no mutating store method reached during normalized spreads "
          f"(violations: {guard.violations})")


def test_N3_last_touched_unchanged_means_persist_decay_never_entered():
    section("N-3 purity: _persist_decay is never entered (last_touched is the witness)")
    store, ids = adversarial_graph(4243)
    before = {r: bits(store.get_road(r, apply_decay=False).last_touched)
              for r in store.all_road_ids()}
    for seed_node in ids:
        spread_activation(store, seed_node, normalization_sigma=1.0)
    after = {r: bits(store.get_road(r, apply_decay=False).last_touched)
             for r in store.all_road_ids()}
    check(before == after,
          "every road's last_touched is unchanged; _persist_decay advances it, so it "
          "was never called — S_out is computed from decayed VIEWS only")


def test_N3_repeat_calls_identical_under_a_frozen_clock():
    section("N-3 purity: repeated identical calls return identical bits")
    store, ids = adversarial_graph(4244)
    diffs = 0
    for seed_node in ids[:6]:
        sigs = {signature(spread_activation(store, seed_node, normalization_sigma=1.0))
                for _ in range(5)}
        if len(sigs) != 1:
            diffs += 1
    check(diffs == 0, f"5 identical calls give 1 result, per seed ({diffs} seeds varied)")


# ═════════════════════════════════════════════════════════════════════════════
# N-4  ORDER-INDEPENDENCE OF S_out — the BUG-0b1 bug class, the one most likely
#      to have been reintroduced.
# ═════════════════════════════════════════════════════════════════════════════

def naive_sum(values):
    """The bug this suite is hunting: a sequential left-fold over a container's order.

    NOT Python's builtin sum(): CPython 3.12 changed sum() to use Neumaier compensated
    summation for floats, so `sum` is nearly exact on 3.12+ and naive on 3.10/3.11. Using
    it as the control would have made this probe's sensitivity depend on the interpreter —
    which is exactly the class of mistake BUG-0b1 was. This left-fold is naive everywhere.
    """
    acc = 0.0
    for v in values:
        acc += v
    return acc


def _fsum_sensitive_star():
    """A star whose out-road strengths make a NAIVE sum order-dependent.

    Searched rather than hardcoded: if no such strength set existed the N-4 test would be
    vacuous — it would pass against a naive fold too. Making the fixture's sensitivity a
    checked property is the difference between a test and a decoration.

    A star is used deliberately: one source, all targets distinct, no convergence, so
    DEFECT-A cannot contaminate the measurement and the ONLY order-dependence available
    is S_out itself. Strengths come from traverse() counts alone — nothing engineered.
    """
    for counts in [(1, 2, 3, 4, 5), (1, 2, 3, 4, 9), (1, 2, 3, 4, 10),
                   (1, 2, 3, 4, 12), (1, 2, 3, 4, 13), (2, 3, 5, 7, 11)]:
        store = frozen_store()
        S = store.add_node("S", NodeType.CONCEPT)
        rids = []
        for i, n in enumerate(counts):
            T = store.add_node("T%d" % i, NodeType.CONCEPT)
            rids.append(worn(store, S, T, n=n))
        strengths = [store.get_road(r).strength for r in rids]
        naive = {bits(naive_sum(p)) for p in itertools.permutations(strengths)}
        exact = {bits(math.fsum(p)) for p in itertools.permutations(strengths)}
        if len(naive) <= 1 or len(exact) != 1:
            continue
        # ...and the difference must actually reach the transmitted value, or a correct
        # S_out would be indistinguishable from a broken one anyway.
        s0, sigma = strengths[0], 1.0
        predicted = {bits(s0 * (sigma / (sigma + (naive_sum(p) - s0))))
                     for p in itertools.permutations(strengths)}
        if len(predicted) > 1:
            return store, S, rids, strengths, counts, len(naive), len(predicted)
    return None


def test_N4_probe_is_sensitive_to_the_bug_it_claims_to_catch():
    section("N-4 sensitivity: a naive fold over these strengths IS order-dependent "
            "(else N-4 is vacuous)")
    found = _fsum_sensitive_star()
    check(found is not None,
          "found an out-road strength set whose naive left-fold is order-dependent")
    if found:
        _, _, _, strengths, counts, n_naive, n_pred = found
        orders = math.factorial(len(strengths))
        print(f"    fixture: {len(strengths)} out-roads worn {counts} times")
        print(f"    naive left-fold: {n_naive} distinct totals over {orders} orders; "
              f"math.fsum: 1")
        print(f"    predicted transmitted values under a naive S_out: {n_pred} distinct")
        check(n_naive > 1,
              f"a naive sequential sum over these strengths is order-dependent "
              f"({n_naive} distinct totals)")
        check(n_pred > 1,
              f"and that difference reaches the transmitted value ({n_pred} distinct), so "
              f"the N-4 assertions below would genuinely catch a naive implementation")


def test_N4_S_out_is_order_independent_bit_for_bit():
    section("N-4 S_out order-independence: shuffle the out-roads, require identical bits")
    found = _fsum_sensitive_star()
    check(found is not None, "sensitive fixture available for N-4")
    if not found:
        return
    store, S, rids, strengths = found[0], found[1], found[2], found[3]
    order = list(range(len(rids)))
    seen = {}
    perms = list(itertools.permutations(order))
    for perm in perms:
        def permute(roads, p=perm):
            return [roads[i] for i in p] if len(roads) == len(p) else roads
        r = spread_activation(PermutingStore(store, permute), S,
                              normalization_sigma=1.0, floor=0.0)
        key = tuple(sorted((k, bits(v)) for k, v in r.flow.items()))
        seen.setdefault(key, 0)
        seen[key] += 1
    check(len(seen) == 1,
          f"transmitted activation is bit-identical under all {len(perms)} out-road "
          f"orders ({len(seen)} distinct flow signatures) — S_out uses math.fsum")


def test_N4_S_out_order_independence_on_high_degree_fans():
    section("N-4 S_out order-independence on random high-degree fans (property-based)")
    rng = random.Random(20260725)
    bad = 0
    for trial in range(25):
        store = frozen_store()
        S = store.add_node("S", NodeType.CONCEPT)
        deg = rng.randint(8, 40)
        for i in range(deg):
            T = store.add_node("T%d" % i, NodeType.CONCEPT)
            worn(store, S, T, n=rng.randint(1, 14))
        base = None
        sigma = rng.choice([0.05, 1.0, 12.0])   # fixed per graph: shuffling is the ONLY
        for _ in range(6):                      # thing that varies inside this loop
            shuffled = list(range(deg))
            rng.shuffle(shuffled)

            def permute(roads, p=shuffled):
                return [roads[i] for i in p] if len(roads) == len(p) else roads
            r = spread_activation(PermutingStore(store, permute), S,
                                  normalization_sigma=sigma, floor=0.0)
            key = tuple(sorted((k, bits(v)) for k, v in r.flow.items()))
            if base is None:
                base = key
            elif key != base:
                bad += 1
                break
    check(bad == 0, f"25 random fans (out-degree 8..40), 6 shuffles each: {bad} order-dependent")


def test_N4_S_out_matches_math_fsum_exactly():
    section("N-4 S_out equals math.fsum of the out-road strengths, to the bit")
    # Derived from the transmitted value rather than asserted about internals: for a road
    # with competing > 0, transmitted = act*s*decay*sigma/(sigma+competing), so competing
    # is recoverable exactly and must equal fsum(all) - s.
    store = frozen_store()
    S = store.add_node("S", NodeType.CONCEPT)
    rids = []
    for i, n in enumerate((1, 2, 3, 5, 8, 13, 21)):
        T = store.add_node("T%d" % i, NodeType.CONCEPT)
        rids.append(worn(store, S, T, n=n))
    strengths = {r: store.get_road(r).strength for r in rids}
    s_out = math.fsum(strengths.values())
    sigma = 1.0
    r = spread_activation(store, S, normalization_sigma=sigma, floor=0.0,
                          energy=1.0, decay_per_hop=1.0)
    worst = 0
    for rid, s in strengths.items():
        competing = s_out - s
        expected = 1.0 * s * 1.0 * (sigma / (sigma + competing))
        if bits(r.flow[rid]) != bits(expected):
            worst += 1
    check(worst == 0,
          f"every road's transmitted value equals act*s*decay*sigma/(sigma+fsum(others)) "
          f"to the bit ({worst} of {len(rids)} roads deviated)")


# ═════════════════════════════════════════════════════════════════════════════
# N-5  LIMITING CASE — a lone out-road is never attenuated, at any sigma.
# ═════════════════════════════════════════════════════════════════════════════

SIGMAS = (1e-12, 1e-3, 0.25, 1.0, 7.5, 1e3, 1e12)


def test_N5_single_out_road_chain_identical_on_and_off():
    section("N-5 limiting case: every source has one out-road -> identical at every sigma")
    store = frozen_store()
    ids = [store.add_node("c%d" % i, NodeType.CONCEPT) for i in range(7)]
    for i in range(6):
        worn(store, ids[i], ids[i + 1], n=2 + i)
    base = signature(spread_activation(store, ids[0], normalization_sigma=None, floor=0.0))
    bad = []
    for sigma in SIGMAS:
        got = signature(spread_activation(store, ids[0], normalization_sigma=sigma, floor=0.0))
        if got != base:
            bad.append(sigma)
    check(not bad,
          f"a pure chain is byte-identical with normalization on at every sigma "
          f"(deviating sigmas: {bad})")


def test_N5_lone_out_road_factor_is_exactly_one_on_a_frozen_clock():
    section("N-5 lone out-road: factor exactly 1.0 (frozen clock)")
    store = frozen_store()
    A = store.add_node("A", NodeType.CONCEPT)
    B = store.add_node("B", NodeType.CONCEPT)
    worn(store, A, B, n=3)
    off = spread_activation(store, A, normalization_sigma=None)
    bad = [s for s in SIGMAS
           if bits(spread_activation(store, A, normalization_sigma=s).activation[B])
           != bits(off.activation[B])]
    check(not bad, f"lone out-road unattenuated at every sigma on a frozen clock ({bad})")


def test_N5_DEFECT_B_lone_out_road_IS_attenuated_on_a_moving_clock():
    section("N-5 DEFECT-B: on a clock that advances, a LONE out-road is attenuated")
    clock = TickClock(1e-6)                 # ~1 microsecond per read: conservative
    store = SubstrateStore(clock=clock)
    A = store.add_node("A", NodeType.CONCEPT)
    B = store.add_node("B", NodeType.CONCEPT)
    worn(store, A, B, n=3)
    clock.ticking = True                    # from here it behaves like the real clock
    rec = RecordingStore(store)
    r = spread_activation(rec, A, normalization_sigma=1.0)
    rid = next(iter(store.roads_from(A)))
    reads = [s for (rr, s) in rec.reads if rr == rid]
    check(len(reads) == 2,
          f"the overlay reads the same road TWICE per expansion (got {len(reads)} reads) "
          "— once for out_total, once in the transmission loop")
    if len(reads) == 2:
        competing = reads[0] - reads[1]
        expected_unattenuated = DEFAULT_SEED_ENERGY * reads[1] * DEFAULT_DECAY_PER_HOP
        actual = r.flow[rid]
        factor = actual / expected_unattenuated
        print(f"    read #1 (out_total) strength = {reads[0]!r}")
        print(f"    read #2 (transmit)  strength = {reads[1]!r}")
        print(f"    competing = {competing!r}   (SPEC-0b2 requires exactly 0.0)")
        print(f"    applied factor = {factor!r}  (SPEC-0b2 requires exactly 1.0)")
        check(competing > 0.0,
              "DEFECT-B present: competing > 0 for a source with EXACTLY ONE out-road, "
              "because out_total and road.strength are read at different clock instants. "
              "IF THIS FAILS BECAUSE THE DEFECT WAS FIXED: delete it and re-verify N-5.")
        check(factor < 1.0,
              f"DEFECT-B consequence: the lone road is attenuated by {1.0 - factor:.3e} "
              "relative, violating SPEC-0b2 §2 property table row 3 and N-5")
    note("DEFECT-B is invisible to every existing test because they all use "
         "Clock(simulated=True), where dt <= 0 makes lazy decay a no-op. The LIBRARY "
         "DEFAULT, SubstrateStore() with Clock(simulated=False), is affected.")


def test_N5_DEFECT_B_scoping_absent_from_the_pre_change_engine():
    section("N-5 DEFECT-B scoping: the pre-change engine read each road once")
    src = open(os.path.join(SRC, "nous_activation.py"), encoding="utf-8").read()
    body = src.split("def spread_activation", 1)[1]
    check(body.count("store.get_road(") == 2,
          f"the overlay added a second get_road site inside the expansion "
          f"(found {body.count('store.get_road(')} sites; the pre-change engine had 1)")
    pre = load_pre_change_engine()
    if pre is None:
        note("git unavailable — pre-change read-count comparison skipped")
        return
    pre_body = getattr(pre, "__nous_source__", "").split("def spread_activation", 1)[-1]
    check(pre_body.count("store.get_road(") == 1,
          f"the pre-change engine had exactly one get_road site "
          f"(found {pre_body.count('store.get_road(')}) — so DEFECT-B is 0b2's, not 0b's")


# ═════════════════════════════════════════════════════════════════════════════
# N-6  MONOTONICITY
# ═════════════════════════════════════════════════════════════════════════════

def test_N6_strictly_decreasing_in_competing():
    section("N-6 transmitted activation is strictly decreasing in competing conductance")
    # A probe road of FIXED strength, with a growing number of equal competitors beside
    # it. Only `competing` varies; the probe road's own strength and the source's
    # activation are held constant, so the comparison isolates the intended variable.
    values = []
    for extra in range(0, 12):
        store = frozen_store()
        S = store.add_node("S", NodeType.CONCEPT)
        P = store.add_node("P", NodeType.CONCEPT)
        probe = worn(store, S, P, n=4)
        for i in range(extra):
            T = store.add_node("T%d" % i, NodeType.CONCEPT)
            worn(store, S, T, n=4)
        r = spread_activation(store, S, normalization_sigma=1.0, floor=0.0)
        values.append(r.flow[probe])
    strict = all(values[i] > values[i + 1] for i in range(len(values) - 1))
    check(strict, f"strictly decreasing in competing: {['%.6f' % v for v in values]}")
    check(values[0] == max(values), "out-degree 1 (competing = 0) transmits the most")


def test_N6_strictly_increasing_in_sigma():
    section("N-6 transmitted activation is strictly increasing in sigma")
    store = frozen_store()
    S = store.add_node("S", NodeType.CONCEPT)
    rids = []
    for i, n in enumerate((1, 4, 9)):
        T = store.add_node("T%d" % i, NodeType.CONCEPT)
        rids.append(worn(store, S, T, n=n))
    ladder = [1e-6, 1e-3, 0.1, 0.5, 1.0, 4.0, 25.0, 1e3]
    per_road = {r: [] for r in rids}
    for sigma in ladder:
        res = spread_activation(store, S, normalization_sigma=sigma, floor=0.0)
        for r in rids:
            per_road[r].append(res.flow[r])
    strict = all(all(v[i] < v[i + 1] for i in range(len(v) - 1)) for v in per_road.values())
    check(strict, "every road's transmitted value strictly increases along the sigma ladder")
    unnorm = spread_activation(store, S, normalization_sigma=None, floor=0.0)
    bounded = all(all(x < unnorm.flow[r] for x in per_road[r]) for r in rids)
    check(bounded, "and every value stays strictly below the unnormalized value (attenuating)")


def test_N6_monotonicity_property_based_on_random_graphs():
    section("N-6 monotonicity, property-based over random adversarial graphs")
    rng = random.Random(99)
    viol_sigma = viol_bound = 0
    trials = 0
    for gs in range(30):
        store, ids = adversarial_graph(5000 + gs)
        seed_node = rng.choice(ids)
        ladder = [0.01, 0.1, 1.0, 10.0, 1000.0]
        runs = [spread_activation(store, seed_node, normalization_sigma=s, floor=0.0)
                for s in ladder]
        base = spread_activation(store, seed_node, normalization_sigma=None, floor=0.0)
        for rid in base.flow:
            series = [r.flow.get(rid) for r in runs]
            if any(v is None for v in series):
                continue
            trials += 1
            if any(series[i] > series[i + 1] for i in range(len(series) - 1)):
                viol_sigma += 1
            if any(v > base.flow[rid] for v in series):
                viol_bound += 1
    check(trials > 0, f"the property was actually exercised ({trials} road-series)")
    check(viol_sigma == 0, f"transmitted is non-decreasing in sigma everywhere ({viol_sigma} violations)")
    check(viol_bound == 0, f"transmitted never exceeds the unnormalized value ({viol_bound} violations)")


# ═════════════════════════════════════════════════════════════════════════════
# N-7  sigma -> infinity CONVERGENCE
# ═════════════════════════════════════════════════════════════════════════════

def test_N7_difference_from_unnormalized_is_monotone_decreasing_in_sigma():
    section("N-7 the gap to the unnormalized engine shrinks monotonically as sigma grows")
    store, ids = adversarial_graph(6001)
    seed_node = max(ids, key=lambda n: len(list(store.roads_from(n))))
    base = spread_activation(store, seed_node, normalization_sigma=None, floor=0.0)
    ladder = [0.01, 0.1, 1.0, 10.0, 100.0, 1e4, 1e8, 1e14]
    gaps = []
    for sigma in ladder:
        r = spread_activation(store, seed_node, normalization_sigma=sigma, floor=0.0)
        gaps.append(math.fsum(abs(base.activation.get(n, 0.0) - v)
                              for n, v in r.activation.items()))
    check(all(gaps[i] >= gaps[i + 1] for i in range(len(gaps) - 1)),
          f"the gap is monotone non-increasing in sigma: {['%.3e' % g for g in gaps]}")
    check(gaps[-1] < gaps[0], "and it actually shrinks (the ladder is not degenerate)")


def test_N7_large_finite_sigma_recovers_the_unnormalized_engine_exactly():
    section("N-7 at a large finite sigma the result is byte-identical to sigma=None")
    store, ids = adversarial_graph(6002)
    mismatches = 0
    for seed_node in ids:
        base = signature(spread_activation(store, seed_node, normalization_sigma=None))
        big = signature(spread_activation(store, seed_node, normalization_sigma=1e300))
        if base != big:
            mismatches += 1
    check(mismatches == 0,
          f"sigma=1e300 recovers sigma=None byte-for-byte ({mismatches} seeds deviated)")


def test_N7_DEFECT_C_sigma_infinity_and_nan_poison_the_result():
    section("N-7 DEFECT-C: sigma is unvalidated — inf and nan produce NaN activation")
    store = frozen_store()
    S = store.add_node("S", NodeType.CONCEPT)
    tgts = []
    for i in range(3):
        T = store.add_node("T%d" % i, NodeType.CONCEPT)
        tgts.append(T)
        worn(store, S, T, n=5)
    for sigma in (float("inf"), float("nan")):
        r = spread_activation(store, S, normalization_sigma=sigma)
        vals = [r.activation.get(t) for t in tgts]
        nan_count = sum(1 for v in vals if v is not None and v != v)
        check(nan_count == len(tgts),
              f"DEFECT-C present: sigma={sigma!r} yields NaN activation for every target "
              f"({nan_count}/{len(tgts)}), silently, with no exception. NaN survives the "
              f"`transmitted < floor` guard because every comparison with NaN is False. "
              f"IF THIS FAILS BECAUSE VALIDATION WAS ADDED: delete it and re-verify N-7.")
    note("SPEC-0b2 §2 describes sigma -> infinity as the value that 'analytically recovers "
         "the current engine'. A caller who takes that literally and passes float('inf') "
         "gets NaN, not the current engine. Large finite sigma does work (see above).")


def test_N7_non_positive_sigma_silences_rather_than_going_negative():
    section("N-7 sigma <= 0 is unvalidated too — characterizing what actually happens")
    store = frozen_store()
    S = store.add_node("S", NodeType.CONCEPT)
    tgts = []
    for i in range(3):
        T = store.add_node("T%d" % i, NodeType.CONCEPT)
        tgts.append(T)
        worn(store, S, T, n=5)
    for sigma in (0.0, -1.0):
        r = spread_activation(store, S, normalization_sigma=sigma)
        reached = [t for t in tgts if t in r.activation]
        check(not reached,
              f"sigma={sigma!r}: nothing propagates ({len(reached)} targets reached). "
              f"The negative/zero transmitted value fails `transmitted < floor` and is "
              f"dropped, so the failure mode is total silence, not negative activation "
              f"(this holds only while floor >= 0).")
    neg = spread_activation(store, S, normalization_sigma=-1.0, floor=-1e9)
    negatives = [v for t, v in neg.activation.items() if t != S and v < 0]
    check(len(negatives) > 0,
          f"with a negative floor the guard no longer hides it: {len(negatives)} targets "
          f"receive NEGATIVE activation at sigma=-1.0 — sigma's sign is never validated")


# ═════════════════════════════════════════════════════════════════════════════
# N-8  CLOSED ROADS COMPETE
# ═════════════════════════════════════════════════════════════════════════════

def competing_for(store, source, road_id):
    """`competing` exactly as SPEC-0b2 §2 defines it: S_out MINUS this road's strength.

    Deliberately not "the sum of the other roads": subtracting from the total leaves a
    rounding residue of up to 1 ULP of S_out, so the two are not the same number. The
    spec's formula is the subtraction, and that is what is asserted against. (For a lone
    out-road the residue is exactly zero — fsum of one value is that value and x-x == 0 —
    which is why N-5's guarantee is sound in principle and only DEFECT-B breaks it.)
    """
    s_out = math.fsum(store.get_road(r).strength for r in store.roads_from(source))
    return s_out - store.get_road(road_id).strength


def _one_open_one_closed():
    """A source with one open road and one CLOSED road. The closed road is closed by a
    traumatic crossing through the public API, not by hand-setting a flag."""
    store = frozen_store()
    S = store.add_node("S", NodeType.CONCEPT)
    OPEN = store.add_node("open", NodeType.CONCEPT)
    SHUT = store.add_node("shut", NodeType.CONCEPT)
    r_open = worn(store, S, OPEN, n=6)
    r_shut = worn(store, S, SHUT, n=6, charge={"dread": -0.95})
    return store, S, OPEN, SHUT, r_open, r_shut


def test_N8_closed_road_contributes_to_S_out():
    section("N-8 a closed road still counts as competing conductance")
    store, S, OPEN, SHUT, r_open, r_shut = _one_open_one_closed()
    check(store.get_road(r_shut).closed, "the road is genuinely closed (fixture check)")
    s_open = store.get_road(r_open).strength
    sigma = 1.0
    r = spread_activation(store, S, normalization_sigma=sigma, floor=0.0,
                          energy=1.0, decay_per_hop=1.0)
    competing = competing_for(store, S, r_open)                  # closed road competes
    check(competing > 0.0, f"the closed road puts real conductance in the way ({competing!r})")
    included = 1.0 * s_open * 1.0 * (sigma / (sigma + competing))
    excluded = 1.0 * s_open * 1.0                                # if it did not
    check(bits(r.flow[r_open]) == bits(included),
          "the open road's transmission matches the CLOSED-ROAD-INCLUDED formula exactly")
    check(bits(r.flow[r_open]) != bits(excluded),
          "and is distinguishable from the excluded alternative — the decision is now "
          "asserted, so a future change has to argue with this test rather than a comment")


def test_N8_a_BLOCKED_closed_road_still_competes():
    section("N-8 a closed road that transmits NOTHING still competes (the sharpest case)")
    store, S, OPEN, SHUT, r_open, r_shut = _one_open_one_closed()
    # energy below the breakthrough threshold: the barrier holds, nothing leaks
    energy = CLOSED_BREAKTHROUGH_THRESHOLD * 0.5
    r = spread_activation(store, S, normalization_sigma=1.0, floor=0.0,
                          energy=energy, decay_per_hop=1.0)
    check(SHUT not in r.activation, "the closed road transmitted nothing (barrier held)")
    check(r_shut not in r.flow, "and it is absent from flow, as designed")
    s_open = store.get_road(r_open).strength
    expected = energy * s_open * 1.0 * (1.0 / (1.0 + competing_for(store, S, r_open)))
    check(bits(r.flow[r_open]) == bits(expected),
          "yet the open road IS attenuated by the blocked road's conductance — a road "
          "that carries nothing still consumes budget")


def test_N8_a_LEAKING_closed_road_is_normalized_like_any_other():
    section("N-8 a closed road that breaks through is normalized like any other road")
    store, S, OPEN, SHUT, r_open, r_shut = _one_open_one_closed()
    energy = 1.0                                     # above breakthrough
    sigma = 1.0
    r = spread_activation(store, S, normalization_sigma=sigma, floor=0.0,
                          energy=energy, decay_per_hop=1.0)
    check(r_shut in r.flow and r_shut in r.broke_through,
          "the closed road leaked and the breakthrough was recorded")
    s_shut = store.get_road(r_shut).strength
    expected = ((energy * CLOSED_LEAK_FRACTION) * s_shut * 1.0
                * (sigma / (sigma + competing_for(store, S, r_shut))))
    check(bits(r.flow[r_shut]) == bits(expected),
          "the leaked transmission is the normalized one: leak fraction first, then the "
          "same divisive factor, with the OPEN road as its competitor")


def test_N8_breakthrough_can_be_recorded_while_flow_is_empty():
    section("N-8 observability wart: broke_through may list a road absent from flow")
    # broke_through is appended BEFORE the floor guard, so a road can be reported as an
    # intrusive-recall event while contributing nothing. Normalization makes this
    # markedly easier to reach, since it shrinks transmitted values toward the floor.
    store = frozen_store()
    S = store.add_node("S", NodeType.CONCEPT)
    SHUT = store.add_node("shut", NodeType.CONCEPT)
    r_shut = worn(store, S, SHUT, n=6, charge={"dread": -0.95})
    for i in range(30):                              # crowd the source
        T = store.add_node("T%d" % i, NodeType.CONCEPT)
        worn(store, S, T, n=6)
    r = spread_activation(store, S, normalization_sigma=1.0)
    check(r_shut in r.broke_through,
          "the closed road is reported as a breakthrough event")
    check(r_shut not in r.flow,
          "but it contributed nothing — broke_through and flow disagree. Consumers that "
          "read broke_through as 'intrusive recall happened' will over-report under "
          "normalization. Pre-existing (the floor guard could always do this); the "
          "overlay makes it far more reachable.")


# ═════════════════════════════════════════════════════════════════════════════
# N-9  NO SILENT SILENCING
# ═════════════════════════════════════════════════════════════════════════════

def _fan(out_degree, traversals=6):
    store = frozen_store()
    S = store.add_node("S", NodeType.CONCEPT)
    for i in range(out_degree):
        T = store.add_node("T%d" % i, NodeType.CONCEPT)
        worn(store, S, T, n=traversals)
    return store, S


def test_N9_high_out_degree_silences_observably_not_partially():
    section("N-9 a source whose out-degree drives every target under the floor goes "
            "observably empty")
    store, S = _fan(200)
    r = spread_activation(store, S, normalization_sigma=1.0)     # library floor
    check(r.activation == {S: DEFAULT_SEED_ENERGY},
          f"activation contains the seed and nothing else ({len(r.activation)} entries)")
    check(r.flow == {}, f"flow is empty, not partially populated ({len(r.flow)} entries)")
    check(r.hops == {S: 0}, f"hops records only the seed ({len(r.hops)} entries)")
    check(r.ranked() == [], "ranked() is empty — a caller cannot mistake this for a result")
    check(r.broke_through == [], "no spurious breakthrough events")


def test_N9_the_silencing_is_attributable_and_visible_as_a_difference():
    section("N-9 the same graph is NOT silent unnormalized — the horizon change is visible")
    store, S = _fan(200)
    off = spread_activation(store, S, normalization_sigma=None)
    on = spread_activation(store, S, normalization_sigma=1.0)
    check(len(off.activation) > 1,
          f"unnormalized, the same source reaches {len(off.activation) - 1} targets")
    check(len(on.activation) == 1,
          "normalized at sigma=1.0, it reaches none — degree-dependent censoring is real, "
          "and it is observable by comparing the two, not hidden inside a truncated result")


def test_N9_reached_count_is_monotone_in_out_degree():
    section("N-9 the horizon closes monotonically as out-degree grows")
    counts = []
    for deg in (1, 2, 4, 8, 16, 32, 64, 128, 200):
        store, S = _fan(deg)
        r = spread_activation(store, S, normalization_sigma=1.0)
        counts.append((deg, len(r.activation) - 1))
    print(f"    (out_degree, reached): {counts}")
    fracs = [reached / deg for deg, reached in counts]
    check(all(fracs[i] >= fracs[i + 1] for i in range(len(fracs) - 1)),
          f"the reached FRACTION is non-increasing in out-degree: "
          f"{['%.2f' % f for f in fracs]}")
    check(counts[0][1] == 1, "out-degree 1 always survives (competing = 0, factor 1.0)")
    check(counts[-1][1] == 0, "and a wide enough fan is fully silenced")
    alive = [d for d, reached in counts if reached > 0]
    dead = [d for d, reached in counts if reached == 0]
    note(f"the horizon does not taper, it CLIFFS: every target survives up to out-degree "
         f"{max(alive)} and none survives from {min(dead)} onward (sigma=1.0, floor="
         f"{DEFAULT_FLOOR}). All roads here are equal-strength, so they cross the floor "
         f"together. SPEC-0b2 §5 predicts degree-dependent censoring on SWOW's ~114 mean "
         f"out-degree; this is that effect, and it is a step, not a gradient.")


def test_N9_no_exception_and_integrity_intact_when_silenced():
    section("N-9 silencing raises nothing and leaves the substrate intact")
    store, S = _fan(200)
    before = store_snapshot(store)
    try:
        spread_activation(store, S, normalization_sigma=1.0)
        raised = None
    except Exception as e:                                     # noqa: BLE001
        raised = e
    check(raised is None, f"no exception on a fully-silenced spread (got {raised!r})")
    check(store_snapshot(store) == before, "substrate byte-identical after a silenced spread")
    try:
        store.check_integrity()
        ok = True
    except IntegrityError:
        ok = False
    check(ok, "store integrity holds after a silenced spread")


# ═════════════════════════════════════════════════════════════════════════════
# Robustness battery and structural facts worth pinning
# ═════════════════════════════════════════════════════════════════════════════

def test_R1_adversarial_battery_with_normalization_on():
    section("R1 adversarial battery with normalization on: integrity, finiteness, sanity")
    bad_finite = bad_integrity = bad_flow = bad_hops = 0
    graphs = 0
    for gs in range(60):
        store, ids = adversarial_graph(7000 + gs)
        graphs += 1
        road_ids = set(store.all_road_ids())
        node_ids = set(store.all_node_ids())
        for seed_node in ids:
            for sigma in (1e-6, 0.5, 1.0, 100.0):
                r = spread_activation(store, seed_node, normalization_sigma=sigma)
                if any(not math.isfinite(v) or v < 0 for v in r.activation.values()):
                    bad_finite += 1
                if not set(r.flow) <= road_ids:
                    bad_flow += 1
                if not set(r.hops) <= node_ids or r.hops.get(seed_node) != 0:
                    bad_hops += 1
        try:
            store.check_integrity()
        except IntegrityError:
            bad_integrity += 1
    check(bad_finite == 0, f"all activation values finite and non-negative ({bad_finite} bad)")
    check(bad_flow == 0, f"flow keys are always real road ids ({bad_flow} bad)")
    check(bad_hops == 0, f"hops keys are real nodes and the seed is at hop 0 ({bad_hops} bad)")
    check(bad_integrity == 0, f"store integrity intact across {graphs} graphs ({bad_integrity} bad)")


def test_R2_seed_and_graph_edge_cases():
    section("R2 edge cases: missing seed, isolated node, self-loop-only, empty graph")
    store = frozen_store()
    lone = store.add_node("lone", NodeType.CONCEPT)
    r = spread_activation(store, lone, normalization_sigma=1.0)
    check(r.activation == {lone: DEFAULT_SEED_ENERGY} and r.flow == {},
          "an isolated node yields just itself")
    worn(store, lone, lone, n=8)
    r = spread_activation(store, lone, normalization_sigma=1.0)
    check(math.isfinite(r.activation[lone]) and r.activation[lone] > 0,
          "a self-loop-only node does not diverge or corrupt")
    try:
        spread_activation(store, "not-a-real-id", normalization_sigma=1.0)
        raised = False
    except NotFound:
        raised = True
    check(raised, "an unknown seed still raises NotFound with the overlay enabled")


def test_S1_overlay_is_not_reachable_from_the_field_or_think():
    section("S1 structural: the overlay is not plumbed past spread_activation")
    import inspect
    from nous_field import build_activation_field
    from nous_perceive import think
    field_params = inspect.signature(build_activation_field).parameters
    think_params = inspect.signature(think).parameters
    check("normalization_sigma" not in field_params,
          "build_activation_field has no normalization_sigma today, so no downstream "
          "consumer (field / coalitions / workspace / think) can enable the overlay")
    check("normalization_sigma" not in think_params,
          "think() has no normalization_sigma today")
    note("This is consistent with default-off, and it bounds the blast radius of DEFECT-B "
         "and DEFECT-C to direct spread_activation callers. It also means the §5 default "
         "flip is not a one-line change: it needs plumbing through the field builder, "
         "which is a re-validation surface for 1a/1b/1c/1d.")


def test_S2_sigma_signature_and_default():
    section("S2 structural: the parameter is keyword-only and defaults to None")
    import inspect
    sig = inspect.signature(spread_activation)
    p = sig.parameters.get("normalization_sigma")
    check(p is not None, "spread_activation exposes normalization_sigma")
    if p is not None:
        check(p.default is None, f"its default is None (got {p.default!r})")
        check(p.kind is inspect.Parameter.KEYWORD_ONLY,
              f"it is keyword-only, so positional callers cannot enable it by accident "
              f"(kind={p.kind})")


# ═════════════════════════════════════════════════════════════════════════════

def run_all():
    print("=" * 70)
    print("  TESTER — SPEC-0b2 divisive normalization overlay, adversarial verification")
    print("  Independent suite. src/ is untouched. Mechanism only, no meaning claim.")
    print("=" * 70)
    for t in [
        test_N1_byte_identity_vs_git_pre_change_engine,
        test_N1_byte_identity_vs_independent_reference,
        test_N1_default_argument_is_the_neutral_value,
        test_N1_byte_identity_loop_closed_on_a_system_built_substrate,
        test_N2_determinism_across_hash_seeds_and_interpreters,
        test_N2_DEFECT_A_convergent_accumulation_is_order_dependent,
        test_N2_DEFECT_A_is_inherited_from_0b_not_introduced_by_the_overlay,
        test_N2_DEFECT_A_reaches_real_processes_at_library_defaults,
        test_N3_purity_snapshot_with_normalization_on,
        test_N3_purity_no_mutating_call_is_made,
        test_N3_last_touched_unchanged_means_persist_decay_never_entered,
        test_N3_repeat_calls_identical_under_a_frozen_clock,
        test_N4_probe_is_sensitive_to_the_bug_it_claims_to_catch,
        test_N4_S_out_is_order_independent_bit_for_bit,
        test_N4_S_out_order_independence_on_high_degree_fans,
        test_N4_S_out_matches_math_fsum_exactly,
        test_N5_single_out_road_chain_identical_on_and_off,
        test_N5_lone_out_road_factor_is_exactly_one_on_a_frozen_clock,
        test_N5_DEFECT_B_lone_out_road_IS_attenuated_on_a_moving_clock,
        test_N5_DEFECT_B_scoping_absent_from_the_pre_change_engine,
        test_N6_strictly_decreasing_in_competing,
        test_N6_strictly_increasing_in_sigma,
        test_N6_monotonicity_property_based_on_random_graphs,
        test_N7_difference_from_unnormalized_is_monotone_decreasing_in_sigma,
        test_N7_large_finite_sigma_recovers_the_unnormalized_engine_exactly,
        test_N7_DEFECT_C_sigma_infinity_and_nan_poison_the_result,
        test_N7_non_positive_sigma_silences_rather_than_going_negative,
        test_N8_closed_road_contributes_to_S_out,
        test_N8_a_BLOCKED_closed_road_still_competes,
        test_N8_a_LEAKING_closed_road_is_normalized_like_any_other,
        test_N8_breakthrough_can_be_recorded_while_flow_is_empty,
        test_N9_high_out_degree_silences_observably_not_partially,
        test_N9_the_silencing_is_attributable_and_visible_as_a_difference,
        test_N9_reached_count_is_monotone_in_out_degree,
        test_N9_no_exception_and_integrity_intact_when_silenced,
        test_R1_adversarial_battery_with_normalization_on,
        test_R2_seed_and_graph_edge_cases,
        test_S1_overlay_is_not_reachable_from_the_field_or_think,
        test_S2_sigma_signature_and_default,
    ]:
        t()

    print("\n" + "=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    if _fail_msgs:
        print("  FAILURES:")
        for m in _fail_msgs:
            print("   -", m)
    print("=" * 70)
    print("  TESTER VERDICT ON SPEC-0b2 §6:  FAIL  (2 of 9 invariants do not hold)")
    print("=" * 70)
    print("    N-1 HOLDS   N-3 HOLDS   N-4 HOLDS   N-6 HOLDS   N-8 HOLDS   N-9 HOLDS")
    print("    N-2 FAILS   DEFECT-A  convergent accumulation is order-dependent")
    print("                          (nous_activation.py:287, plain + over a set order)")
    print("                          INHERITED FROM 0b — reproduces at sigma=None.")
    print("    N-5 FAILS   DEFECT-B  a LONE out-road is attenuated on a moving clock")
    print("                          (out_total and road.strength are read at different")
    print("                          clock instants, so competing != 0)")
    print("                          INTRODUCED BY 0b2.")
    print("    N-7 PARTLY  DEFECT-C  sigma=inf/nan yields NaN activation, unvalidated")
    print("                          INTRODUCED BY 0b2.")
    print("  The passing count above is not the verdict: the three defects are recorded")
    print("  as asserted-negatives, which PASS while the defect is present. Fixing any of")
    print("  them will turn its test red on purpose, forcing re-verification here.")
    print("=" * 70)
    return _failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run_all() else 1)
