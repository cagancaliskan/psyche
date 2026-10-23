"""
TESTER — SPEC-0b2 §6 RE-ADJUDICATION (N-1 … N-9), written from scratch 2026-07-26.

Author: tester (independent adversary). This is a SECOND, INDEPENDENT pass on the nine
invariants, written after brick 0c landed and after the first pass returned FAIL. It does
not extend, adapt or re-run `tests/test_tester_0b2_adversarial.py`; every fixture, oracle
and assertion below was re-derived from SPEC-0b2 §2/§6 and the module's own documented
design. The two suites are deliberately allowed to overlap in what they claim and to
disagree in how they establish it — that is the only way a second pass is worth running.

Mechanism only. Nothing here grades a cognitive claim, and nothing here should be read as
one. `src/` is untouched.

WHY A SECOND PASS EXISTS
------------------------
The first pass found three defects. All three are reported fixed:
  DEFECT-A (N-2) by brick 0c — creation-ordered `_out`/`_in` plus an fsum accumulator;
  DEFECT-B (N-5) by the single-read materialisation of an expanding node's roads;
  DEFECT-C (N-7) by sigma validation at the boundary, later widened to `energy` (D-015).
This pass asks whether §6 now holds *in full*, adversarially and loop-closed. It re-derives
rather than inherits: the reference numbers quoted in the handoff are treated as claims to
be reproduced, not as inputs.

THE NOISE FLOOR COMES FIRST, AND IT IS A TEST, NOT A COMMENT
------------------------------------------------------------
N-5 ("a lone out-road is never attenuated") is a bit-exact claim. On the library-default
clock (`Clock(simulated=False)`) two IDENTICAL `sigma=None` calls already differ, because
0a's lazy decay is applied at `clock.now()` and the second call happens later. The
measurement therefore has a noise floor LARGER than the effect, and any "deviation"
attributed to normalization on a live clock is the probe's fault.

That is not hypothetical: it produced a false defect report against a working engine. So
section P-0 below ASSERTS the noise floor — it measures the spread of repeated identical
live-clock calls, shows it is non-zero, and shows that freezing the clock removes it. Every
bit-exact assertion in this file that could be contaminated by it runs on a frozen clock,
and the two that deliberately run on a MOVING clock (N-5c, N-5d) are written as
WITHIN-CALL identities, which the noise floor cannot reach.

WHAT IS OUT OF SCOPE, ON INSTRUCTION
------------------------------------
  * the §5 default-flip decision (Cagan's, open);
  * D-008's SCALE-INVARIANCE question about `floor` under conservation (open);
  * brick 0c-ii's FINITENESS question about `floor` (registered, blocks nothing).
These last two are independent of each other. Nothing below tests as though either is
decided, and in particular `floor` is never passed a non-finite value here.

Run directly:
    PYTHONPATH=<repo>/src python3 tests/test_tester_0b2_reverify.py
"""

import hashlib
import inspect
import itertools
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import textwrap

from psyche_store import SubstrateStore, Clock, NodeType, NotFound
from psyche_activation import (
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
# Bit-level comparison. Never rounded: 1 ULP is exactly the size of the defect
# class this project has been bitten by twice (BUG-0b1, DEFECT-A).
# ─────────────────────────────────────────────────────────────────────────────

def bits(x):
    return struct.pack("<d", float(x)).hex()


def sig_of(res):
    """Complete byte-level fingerprint of an ActivationResult, dict ORDER included."""
    return (
        res.seed,
        tuple((k, bits(v)) for k, v in res.activation.items()),
        tuple(res.hops.items()),
        tuple(res.broke_through),
        tuple((k, bits(v)) for k, v in res.flow.items()),
    )


def sig_unordered(res, store):
    """Fingerprint keyed by CONTENT and insensitive to mapping order.

    Used where out-road iteration order is deliberately permuted: permuting the
    iteration legitimately reorders first-arrival keys, so an order-sensitive
    signature would flag a non-defect. The VALUES must still match to the bit.
    """
    def c(n):
        return store.get_node(n).content
    return (
        c(res.seed),
        tuple(sorted((c(k), bits(v)) for k, v in res.activation.items())),
        tuple(sorted((c(k), h) for k, h in res.hops.items())),
        tuple(sorted(c(store.get_road(r).source_id) + "->" +
                     c(store.get_road(r).target_id) for r in res.broke_through)),
        tuple(sorted((c(store.get_road(k).source_id),
                      c(store.get_road(k).target_id), bits(v))
                     for k, v in res.flow.items())),
    )


def call_or_exc(fn, *a, **k):
    """Run and return either ('ok', signature) or ('raised', type, message).

    Neutral byte-identity has to cover the EXCEPTION path too: an overlay that
    silently changed which inputs raise would not be neutral, and comparing only
    successful returns would never see it.
    """
    try:
        return ("ok", sig_of(fn(*a, **k)))
    except Exception as exc:                      # noqa: BLE001 - deliberate
        return ("raised", type(exc).__name__, str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Clocks and stores
# ─────────────────────────────────────────────────────────────────────────────

def frozen_store():
    """Clock never advances, so lazy decay is a no-op and road strengths are
    exactly what was written. REQUIRED for any bit-exact comparison across calls
    (see P-0)."""
    return SubstrateStore(clock=Clock(simulated=True, start=0.0))


class SteppingClock(Clock):
    """Advances a fixed dt on every now() once armed. A reproducible stand-in for
    the library default clock, which also advances but irreproducibly."""

    def __init__(self, dt):
        super().__init__(simulated=True, start=0.0)
        self.dt = dt
        self.armed = False

    def now(self):
        t = self._t
        if self.armed:
            self._t += self.dt
        return t


class RoadReadCounter:
    """Delegating proxy that counts decayed get_road calls and records what each
    returned. Public surface only — no monkeypatching of src/."""

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


class OutRoadPermuter:
    """Delegating proxy that hands a source's out-roads back in a chosen order.

    The real store's order is creation order and is not caller-controllable, so
    the only way to attack order-INDEPENDENCE (as distinct from order-pinning) is
    to perturb it from outside.
    """

    def __init__(self, inner, permute):
        self._inner = inner
        self._permute = permute

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def roads_from(self, node_id):
        return iter(self._permute(list(self._inner.roads_from(node_id))))


class WriteTrap:
    """Raises if the engine calls any mutating store method. Structural proof of
    purity, independent of any snapshot comparison."""

    MUTATORS = ("add_node", "remove_node", "add_road", "remove_road", "strengthen",
                "traverse", "designate_self", "undesignate_self", "pin", "unpin")

    def __init__(self, inner):
        self._inner = inner
        self.violations = []

    def __getattr__(self, name):
        if name in self.MUTATORS:
            def _trap(*a, **k):
                self.violations.append(name)
                raise AssertionError(f"spread_activation called mutating {name}()")
            return _trap
        return getattr(self._inner, name)


def substrate_snapshot(store):
    """Every mutable byte of stored state, taken through the public surface with
    apply_decay=False so the snapshot is of what is STORED, not of a decayed view."""
    nodes = []
    for nid in sorted(store.all_node_ids()):
        n = store.get_node(nid)
        nodes.append((n.content, n.node_type.name, n.creation_seq,
                      bits(n.formation_time), bits(n.last_accessed), n.access_count))
    roads = []
    for rid in sorted(store.all_road_ids()):
        r = store.get_road(rid, apply_decay=False)
        roads.append((store.get_node(r.source_id).content,
                      store.get_node(r.target_id).content,
                      r.creation_seq, bits(r.formation_time), bits(r.last_touched),
                      bits(r.strength), r.closed, r.traversal_count,
                      tuple(sorted((k, bits(v)) for k, v in r.charges.items()))))
    return (tuple(nodes), tuple(roads),
            tuple(sorted(store.self_region())) and "self", store.node_count(),
            store.road_count())


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures. Everything is built with traverse() — the substrate's own primitive —
# so no strength is hand-placed and no test rests on a value the system could not
# produce. `add_road` without `strengthen` is used ONLY where a deliberately
# never-worn road is the point, and it is called out there.
# ─────────────────────────────────────────────────────────────────────────────

def worn(store, a, b, n=1, charge=None):
    for _ in range(n):
        store.traverse(a, b, charge)
    return store.find_road(a, b)


def star(k, counts=None, charges=None, store=None):
    """Hub with k out-roads. Returns (store, hub, [targets])."""
    s = store or frozen_store()
    hub = s.add_node("hub", NodeType.CONCEPT)
    tgts = []
    for i in range(k):
        t = s.add_node("t%02d" % i, NodeType.CONCEPT)
        worn(s, hub, t, n=(counts[i] if counts else 3),
             charge=(charges[i] if charges else None))
        tgts.append(t)
    return s, hub, tgts


def hostile_graph(seed):
    """Self-loops, cycles, duplicate pairs (which dedup at the store), closed and
    traumatic roads, high-degree fans, saturated and decayed strengths, isolated
    nodes, and single-node graphs. Seeded with random.Random so the topology does
    not depend on PYTHONHASHSEED."""
    rng = random.Random(seed)
    clock = Clock(simulated=True, start=0.0)
    s = SubstrateStore(clock=clock)
    n = rng.randint(1, 10)
    ids = [s.add_node("n%02d" % i, rng.choice(list(NodeType))) for i in range(n)]
    for _ in range(rng.randint(0, 34)):
        a, b = rng.choice(ids), rng.choice(ids)          # self-loops allowed
        k = rng.random()
        charge = None
        if k < 0.24:
            charge = {"dread": -rng.uniform(0.78, 1.0)}  # closes the road
        elif k < 0.42:
            charge = {"joy": rng.uniform(0.2, 0.9), "awe": rng.uniform(0.0, 0.5)}
        for _ in range(rng.randint(1, 11)):
            s.traverse(a, b, charge)                     # duplicate pairs dedup
        if rng.random() < 0.33:
            clock.advance(rng.uniform(0.0, 40.0))        # exercise lazy decay
    if rng.random() < 0.45:
        hub = rng.choice(ids)
        for i in range(rng.randint(4, 26)):
            t = s.add_node("f%02d" % i, NodeType.CONCEPT)
            for _ in range(rng.randint(1, 5)):
                s.traverse(hub, t)
    if rng.random() < 0.25:
        s.add_node("isolated", NodeType.CONCEPT)         # never connected
    clock.advance(0.0)
    return s, list(s.all_node_ids())


PARAMS = [
    dict(),
    dict(energy=0.05),
    dict(energy=1e6),
    dict(energy=0.0),
    dict(energy=-1.5),                       # negative energy is accepted (D-014)
    dict(decay_per_hop=1.0),
    dict(decay_per_hop=0.0),
    dict(floor=0.0),
    dict(floor=1e9),
    dict(hop_budget=0),
    dict(hop_budget=1),
    dict(hop_budget=25),
    dict(energy=1e6, floor=0.0, decay_per_hop=1.0, hop_budget=9),
]

SIGMA_LADDER = [5e-324, 1e-12, 1e-3, 0.25, 1.0, 7.5, 1e3, 1e12, 1e100, 1e300]


# ═════════════════════════════════════════════════════════════════════════════
# THE INDEPENDENT ORACLE, and the mutant battery that proves it has teeth.
#
# Derived from the documented algorithm, not transcribed from src/:
#   - SPEC-0b2 §2's three-line transmission rule;
#   - the module docstring's hop-layered single-expansion design (freeze the
#     layer, expand once, strictly-longer ripples dropped);
#   - SPEC-0c §2.2 (roads_from yields creation order) and §2.3 (per-target
#     contribution lists reduced with math.fsum, whole list each time);
#   - SPEC-0c §3 (materialise the expanding node's roads once);
#   - SPEC-0c §4 / D-015 (validate sigma and energy at the boundary; refuse a
#     non-finite `transmitted` before the floor comparison).
#
# A reference copied from the module under test is a mirror, not an oracle, and
# would make N-1 vacuous. Copying is impossible to disprove by inspection, so it
# is disproved by CONSEQUENCE instead: `MUTANTS` below are deliberately-wrong
# variants of this same reference, and N-1d requires every one of them to be
# CAUGHT. A mirror would fail that test, because a mirror agrees with whatever
# the engine does.
# ═════════════════════════════════════════════════════════════════════════════

def oracle_spread(store, seed_node, *, energy=DEFAULT_SEED_ENERGY,
                  decay_per_hop=DEFAULT_DECAY_PER_HOP, floor=DEFAULT_FLOOR,
                  hop_budget=DEFAULT_HOP_BUDGET, normalization_sigma=None,
                  mutant=None):
    m = mutant or ()
    if normalization_sigma is not None and (
            not math.isfinite(normalization_sigma) or normalization_sigma <= 0.0):
        raise ValueError("normalization_sigma must be finite and strictly positive")
    if not math.isfinite(energy):
        raise ValueError("energy must be finite")
    if not store.exists(seed_node):
        raise NotFound(f"seed node {seed_node}")

    arriving = {seed_node: [energy]}
    hop_of = {seed_node: 0}
    leaked = []
    edge_flow = {}
    layer = [seed_node]
    depth = 0
    while layer and depth < hop_budget:
        # freeze: reduce each expanding node's WHOLE contribution list, exactly rounded
        if "naive_accumulator" in m:
            expand_value = {}
            for nid in layer:
                acc = 0.0
                for term in arriving[nid]:
                    acc = acc + term
                expand_value[nid] = acc
        else:
            expand_value = {nid: math.fsum(arriving[nid]) for nid in layer}
        newly = []
        for nid in layer:
            here = expand_value[nid]
            # one materialisation => one clock instant for the whole expansion
            if "double_read" in m:
                out_ids = list(store.roads_from(nid))
                seen = [(rid, store.get_road(rid)) for rid in out_ids]
                conductances = [store.get_road(rid).strength for rid in out_ids]
            else:
                seen = [(rid, store.get_road(rid)) for rid in store.roads_from(nid)]
                conductances = [rd.strength for _, rd in seen]
            if normalization_sigma is None:
                total_out = 0.0
            elif "builtin_sum" in m:
                acc = 0.0
                for c in conductances:
                    acc = acc + c
                total_out = acc
            else:
                total_out = math.fsum(conductances)
            for idx, (rid, road) in enumerate(seen):
                carried = here
                if road.closed:
                    over = (carried < CLOSED_BREAKTHROUGH_THRESHOLD
                            if "breakthrough_strict" in m
                            else carried <= CLOSED_BREAKTHROUGH_THRESHOLD)
                    if over:
                        continue
                    carried = carried * CLOSED_LEAK_FRACTION
                    leaked.append(rid)
                sent = carried * road.strength * decay_per_hop
                if normalization_sigma is not None:
                    if "competing_includes_self" in m:
                        rival = total_out
                    elif "competing_exact_others" in m:
                        rival = math.fsum(c for j, c in enumerate(conductances)
                                          if j != idx)
                    else:
                        rival = total_out - road.strength
                    if rival > 0.0:
                        sent = sent * (normalization_sigma
                                       / (normalization_sigma + rival))
                if not math.isfinite(sent):
                    raise ValueError(f"non-finite transmitted activation on road {rid}")
                below = (sent <= floor) if "floor_inclusive" in m else (sent < floor)
                if below:
                    continue
                tgt = road.target_id
                arriving.setdefault(tgt, []).append(sent)
                edge_flow[rid] = edge_flow.get(rid, 0.0) + sent
                if tgt not in hop_of:
                    hop_of[tgt] = depth + 1
                    newly.append(tgt)
        layer = newly
        depth += 1
    if "naive_accumulator" in m:
        final = {}
        for nid, terms in arriving.items():
            acc = 0.0
            for term in terms:
                acc = acc + term
            final[nid] = acc
    else:
        final = {nid: math.fsum(terms) for nid, terms in arriving.items()}
    return ActivationResult(seed=seed_node, activation=final, hops=hop_of,
                            broke_through=leaked, flow=edge_flow)


MUTANTS = [
    ("naive_accumulator",
     "convergence accumulated with a running += instead of an exactly-rounded fsum "
     "(DEFECT-A's exact shape)"),
    ("competing_includes_self",
     "the road's own conductance left inside `competing`"),
    ("competing_exact_others",
     "`competing` computed as the exact sum of the OTHER roads instead of "
     "S_out - strength (SPEC-0b2 §2: these differ by up to 1 ULP of S_out)"),
    ("builtin_sum",
     "S_out folded left-to-right instead of math.fsum"),
    ("floor_inclusive",
     "the floor guard written `<=` instead of `<`"),
    ("breakthrough_strict",
     "the breakthrough guard written `<` instead of `<=`"),
    ("double_read",
     "each road read twice per expansion (DEFECT-B's exact shape)"),
]


# ═════════════════════════════════════════════════════════════════════════════
# ORACLE 2 — the ACTUAL pre-0b2 engine, recovered from git.
#
# Resolved by CONTENT (newest revision of src/psyche_activation.py that does not
# mention normalization_sigma), so a rebase cannot stale it. It is a historical
# artifact and cannot be re-based: it accumulates convergent contributions with a
# naive running float add, so it has a SINGLE WELL-DEFINED ANSWER only where no
# node accumulates three or more terms. a+b == b+a is exact; a+b+c is not.
#
# THE SEED'S OWN ENERGY IS ONE OF THOSE TERMS — `activation` starts as
# {seed: energy} — so the boundary is stated on CONTRIBUTIONS, not on in-degree.
# It is MEASURED here from the engine's own recorded flow, per comparison, rather
# than enforced by restricting the generator: that keeps the graphs as hostile as
# they were and cannot silently drift.
# ═════════════════════════════════════════════════════════════════════════════

_PRE_CACHE = []


def pre_overlay_engine():
    if _PRE_CACHE:
        return _PRE_CACHE[0]
    out = None
    try:
        # Historical path and store alias: the pre-overlay engine predates the Psyche rename.
        log = subprocess.run(["git", "log", "--format=%H", "--",
                              "src/nous_activation.py"],
                             cwd=ROOT, capture_output=True, text=True, timeout=60)
        if log.returncode == 0:
            for sha in log.stdout.split():
                blob = subprocess.run(["git", "show", f"{sha}:src/nous_activation.py"],
                                      cwd=ROOT, capture_output=True, text=True,
                                      timeout=60)
                if blob.returncode != 0 or "normalization_sigma" in blob.stdout:
                    continue
                import importlib
                import importlib.util
                import tempfile
                tmp = tempfile.mkdtemp(prefix="psyche_pre0b2_reverify_")
                path = os.path.join(tmp, "_pre0b2_engine.py")
                try:
                    with open(path, "w", encoding="utf-8") as fh:
                        fh.write(blob.stdout)
                    spec = importlib.util.spec_from_file_location(
                        "_pre0b2_engine_reverify", path)
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules["_pre0b2_engine_reverify"] = mod
                    sys.modules.setdefault("nous_store", importlib.import_module("psyche_store"))
                    spec.loader.exec_module(mod)
                    mod.__psyche_sha__ = sha
                    out = mod
                    break
                finally:
                    shutil.rmtree(tmp, ignore_errors=True)
    except (OSError, subprocess.SubprocessError):
        out = None
    _PRE_CACHE.append(out)
    return out


def contribution_counts(store, res):
    """How many terms each accumulation actually took, read off the engine's own
    recorded flow. The seed's energy counts as one."""
    counts = {}
    for rid in res.flow:
        tgt = store.get_road(rid, apply_decay=False).target_id
        counts[tgt] = counts.get(tgt, 0) + 1
    counts[res.seed] = counts.get(res.seed, 0) + 1
    return counts


# ═════════════════════════════════════════════════════════════════════════════
# P-0  THE NOISE FLOOR. Establish it before believing any signal.
# ═════════════════════════════════════════════════════════════════════════════

def test_P0_the_live_clock_has_a_noise_floor_larger_than_the_effect():
    """A live clock makes repeated IDENTICAL calls disagree, so a bit-exact N-5
    probe run on one measures its own instrument. Asserted, not commented."""
    section("P-0 noise floor: on a LIVE clock, identical sigma=None calls DISAGREE")
    s = SubstrateStore()                                  # library default: live clock
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    worn(s, a, b, n=3)
    vals = [spread_activation(s, a, normalization_sigma=None).activation[b]
            for _ in range(60)]
    distinct = {bits(v) for v in vals}
    check(len(distinct) > 1,
          f"the live clock produces more than one bit pattern for the SAME call "
          f"({len(distinct)} distinct over 60 calls)")
    spread = max(vals) - min(vals)
    rel = spread / abs(vals[0]) if vals[0] else float("inf")
    print(f"  live-clock spread over 60 identical calls: {spread!r}  "
          f"({rel:.3e} relative, ~{spread / math.ulp(vals[0]):.0f} ULP)")
    check(spread > 0.0, "the noise floor is strictly positive, so any bit-exact "
                        "claim measured on a live clock is unattributable")

    # the same measurement with the clock held still
    f = frozen_store()
    fa = f.add_node("a", NodeType.CONCEPT)
    fb = f.add_node("b", NodeType.CONCEPT)
    worn(f, fa, fb, n=3)
    fvals = [spread_activation(f, fa, normalization_sigma=None).activation[fb]
             for _ in range(60)]
    check(len({bits(v) for v in fvals}) == 1,
          "freezing the clock collapses the noise floor to exactly zero "
          f"({len({bits(v) for v in fvals})} distinct over 60 calls)")

    # and the punchline: on a live clock the sigma on/off difference for a LONE
    # out-road is INSIDE the noise, so it cannot be attributed to normalization.
    on = spread_activation(s, a, normalization_sigma=1.0).activation[b]
    off = spread_activation(s, a, normalization_sigma=None).activation[b]
    delta = abs(on - off)
    check(delta <= spread,
          f"on a live clock the |sigma on - off| difference ({delta!r}) does not "
          f"exceed the noise floor ({spread!r}) — a false-defect trap, and the "
          f"reason every bit-exact test below freezes the clock")
    note("N-5 and all byte-identity claims below run on Clock(simulated=True). "
         "This is a property of 0a's lazy decay, not of the 0b2 overlay.")


# ═════════════════════════════════════════════════════════════════════════════
# N-1  NEUTRAL BYTE-IDENTITY — the gate. If this fails nothing else matters.
# ═════════════════════════════════════════════════════════════════════════════

def test_N1a_explicit_none_equals_the_omitted_parameter():
    section("N-1a the neutral value is byte-identical to omitting the parameter "
            "(exception path included)")
    compared = 0
    raised = 0
    mismatch = []
    for gseed in range(40):
        store, ids = hostile_graph(gseed)
        for seed_node in ids[:4]:
            for params in PARAMS:
                a = call_or_exc(spread_activation, store, seed_node, **params)
                b = call_or_exc(spread_activation, store, seed_node,
                                normalization_sigma=None, **params)
                compared += 1
                if a[0] == "raised":
                    raised += 1
                if a != b:
                    mismatch.append((gseed, params, a[0], b[0]))
    check(not mismatch,
          f"{compared} (graph x seed x parameter) comparisons agree bit-for-bit; "
          f"mismatches={mismatch[:2]}")
    check(compared >= 1000, f"the surface is real: {compared} comparisons")
    print(f"  compared {compared}; {raised} of them exercised the EXCEPTION path")


def test_N1b_neutral_matches_the_actual_pre_overlay_engine_from_git():
    """Oracle 2, bounded to the region where it had a single well-defined answer.

    The bound is measured per comparison from the engine's own flow, and the test
    asserts that the boundary value (exactly 2 contributions) is actually reached,
    so it cannot pass by quietly only ever comparing trivial graphs.
    """
    section("N-1b byte-identity vs the ACTUAL pre-overlay engine recovered from git")
    mod = pre_overlay_engine()
    if mod is None:
        note("git unavailable — oracle 2 skipped; N-1 still rests on N-1a/N-1c/N-1d")
        check(True, "oracle 2 skipped cleanly rather than passing vacuously")
        # SPEC-0c O-17: the assertion COUNT must not depend on the environment, or
        # the ledger's figure becomes a fact about the machine that captured it.
        check(True, "(placeholder so the assertion count does not depend on git)")
        check(True, "(placeholder so the assertion count does not depend on git)")
        return
    print(f"  recovered pre-overlay engine at {mod.__psyche_sha__[:12]}")
    compared = 0
    at_boundary = 0
    skipped = 0
    mismatch = []
    for gseed in range(60):
        store, ids = hostile_graph(gseed)
        for seed_node in ids[:4]:
            for params in PARAMS:
                if not math.isfinite(params.get("energy", DEFAULT_SEED_ENERGY)):
                    continue
                try:
                    cur = spread_activation(store, seed_node,
                                            normalization_sigma=None, **params)
                except Exception:                          # noqa: BLE001
                    skipped += 1
                    continue
                counts = contribution_counts(store, cur)
                worst = max(counts.values(), default=0)
                if worst >= 3:
                    skipped += 1
                    continue                    # outside the oracle's valid region
                if worst == 2:
                    at_boundary += 1
                old = mod.spread_activation(store, seed_node, **params)
                compared += 1
                if sig_of(cur) != sig_of(old):
                    mismatch.append((gseed, params,
                                     [(k, bits(v)) for k, v in cur.activation.items()],
                                     [(k, bits(v)) for k, v in old.activation.items()]))
    check(not mismatch,
          f"{compared} comparisons inside the oracle's valid region agree bit-for-bit; "
          f"first mismatch={mismatch[:1]}")
    check(compared >= 300, f"the valid region is populated: {compared} comparisons")
    check(at_boundary >= 20,
          f"the boundary itself is exercised, not dodged: {at_boundary} comparisons "
          f"had a node accumulating exactly 2 contributions")
    print(f"  compared {compared}, of which {at_boundary} at the 2-contribution "
          f"boundary; {skipped} skipped as outside the oracle's valid region")


def test_N1i_every_divergence_from_the_pre_overlay_engine_is_owned_by_0c():
    """N-1b compares only inside the pre-overlay engine's valid region and SKIPS
    the rest. A skip is not evidence, so this test refuses to skip: it drives the
    same comparison over the WHOLE surface, classifies every divergence, and
    requires each one to fall into a decided, recorded, 0c-owned class:

      (1) `energy` non-finite  -> the current engine raises ValueError   (D-015)
      (2) `decay_per_hop` non-finite -> the non-finite-`transmitted` backstop
          raises ValueError                                              (D-015)
      (3) `energy` is -0.0     -> fsum([-0.0]) is +0.0, by design         (D-014)
      (4) three or more contributions converge -> exactly-rounded vs naive
          accumulation differ in the last bits                            (D-013)

    An UNCLASSIFIED divergence would be the overlay's, and would sink N-1. The
    test also requires every class to actually FIRE, so the taxonomy cannot pass
    by describing a surface it never reaches.
    """
    section("N-1i exhaustive: every divergence from the pre-overlay engine is one "
            "of four DECIDED 0c changes — none is the overlay's")
    mod = pre_overlay_engine()
    if mod is None:
        note("git unavailable — N-1i skipped")
        check(True, "N-1i skipped cleanly rather than passing vacuously")
        check(True, "(placeholder so the assertion count does not depend on git)")
        check(True, "(placeholder so the assertion count does not depend on git)")
        check(True, "(placeholder so the assertion count does not depend on git)")
        check(True, "(placeholder so the assertion count does not depend on git)")
        check(True, "(placeholder so the assertion count does not depend on git)")
        return
    wide = PARAMS + [dict(energy=float("nan")), dict(energy=float("inf")),
                     dict(energy=float("-inf")), dict(energy=-0.0),
                     dict(decay_per_hop=float("inf")),
                     dict(decay_per_hop=float("nan")),
                     dict(decay_per_hop=2.0, energy=1e30, floor=0.0)]
    tally = {"energy_finiteness_D015": 0, "transmitted_backstop_D015": 0,
             "signed_zero_D014": 0, "fsum_accumulation_D013": 0}
    unclassified = []
    identical = 0
    total = 0
    for gseed in range(60):
        store, ids = hostile_graph(gseed)
        for seed_node in ids[:4]:
            for params in wide:
                total += 1
                cur = call_or_exc(spread_activation, store, seed_node,
                                  normalization_sigma=None, **params)
                old = call_or_exc(mod.spread_activation, store, seed_node, **params)
                if cur == old:
                    identical += 1
                    continue
                e = params.get("energy", DEFAULT_SEED_ENERGY)
                d = params.get("decay_per_hop", DEFAULT_DECAY_PER_HOP)
                if cur[0] == "raised" and old[0] == "ok":
                    if not math.isfinite(e):
                        tally["energy_finiteness_D015"] += 1
                    elif not math.isfinite(d):
                        tally["transmitted_backstop_D015"] += 1
                    else:
                        unclassified.append((gseed, params, cur[:2], "old ok"))
                    continue
                if cur[0] != "ok" or old[0] != "ok":
                    unclassified.append((gseed, params, cur[0], old[0]))
                    continue
                if e == 0.0 and math.copysign(1.0, e) < 0:
                    tally["signed_zero_D014"] += 1
                    continue
                try:
                    r = spread_activation(store, seed_node,
                                          normalization_sigma=None, **params)
                    worst = max(contribution_counts(store, r).values(), default=0)
                except Exception:                          # noqa: BLE001
                    worst = -1
                if worst >= 3:
                    tally["fsum_accumulation_D013"] += 1
                else:
                    unclassified.append((gseed, params, "values differ",
                                         f"max_contributions={worst}"))
    print(f"  {total} comparisons; {identical} byte-identical; "
          f"divergences by class: {tally}")
    check(not unclassified,
          f"every divergence is classified — none is attributable to the 0b2 "
          f"overlay; unclassified={unclassified[:3]}")
    for name, n in tally.items():
        check(n > 0, f"class '{name}' actually fires ({n} occurrences), so the "
                     f"taxonomy is not describing a surface it never reaches")
    check(identical >= 1500,
          f"and the identical majority is real: {identical} byte-identical "
          f"comparisons out of {total}")


def test_N1c_neutral_matches_the_independent_oracle_everywhere():
    section("N-1c byte-identity vs the independent oracle (no in-degree bound)")
    compared = 0
    mismatch = []
    for gseed in range(45):
        store, ids = hostile_graph(gseed)
        for seed_node in ids[:4]:
            for params in PARAMS:
                a = call_or_exc(spread_activation, store, seed_node,
                                normalization_sigma=None, **params)
                b = call_or_exc(oracle_spread, store, seed_node,
                                normalization_sigma=None, **params)
                compared += 1
                # exception TYPE must agree; message wording is the module's own
                if a[0] != b[0] or (a[0] == "ok" and a[1] != b[1]) or \
                        (a[0] == "raised" and a[1] != b[1]):
                    mismatch.append((gseed, params, a[:2], b[:2]))
    check(not mismatch,
          f"{compared} comparisons agree bit-for-bit at every in-degree; "
          f"first mismatch={mismatch[:1]}")
    # the overlay ON must also match the oracle, or the oracle is only checking the
    # branch that does nothing
    on_compared = 0
    on_mismatch = []
    for gseed in range(45):
        store, ids = hostile_graph(gseed)
        for seed_node in ids[:3]:
            for sg in (0.25, 1.0, 7.5, 1e300):
                a = call_or_exc(spread_activation, store, seed_node,
                                floor=0.0, normalization_sigma=sg)
                b = call_or_exc(oracle_spread, store, seed_node,
                                floor=0.0, normalization_sigma=sg)
                on_compared += 1
                if a != b:
                    on_mismatch.append((gseed, sg))
    check(not on_mismatch,
          f"{on_compared} comparisons with the overlay ON also agree bit-for-bit; "
          f"first mismatch={on_mismatch[:1]}")


def test_N1d_the_oracle_catches_every_deliberate_mutation():
    """Anti-mirror proof BY CONSEQUENCE.

    A reference transcribed from src/ agrees with the engine no matter what the
    engine does, so it can never fail — and neither can N-1. Here the same
    reference is deliberately broken seven ways, each way being a defect this
    project has actually shipped or a boundary the spec actually pins, and every
    one must be CAUGHT. A mirror could not do that.
    """
    section("N-1d the oracle is not a mirror: seven deliberate mutations, all caught")
    caught = {}
    # Fixtures chosen so each mutation has somewhere to show. Three of the seven
    # are 1-ULP mutations, and a 1-ULP mutation is invisible on a friendly input —
    # which is exactly the failure mode this project exists to catch, so the
    # fixtures were SEARCHED for rather than assumed (see the search that produced
    # each tuple, reproduced in N-4a for the fold case).
    fixtures = []

    # (a) three convergent contributions whose left-fold total, IN CREATION ORDER,
    #     differs from their exactly-rounded sum by 1 ULP. Traverse counts
    #     S->Mi = (1,1,1), Mi->T = (1,2,4): terms 0.012718200625, 0.020594322043750002,
    #     0.033407983979914374 fold to ...438 and fsum to ...437.
    conv = frozen_store()
    S = conv.add_node("S", NodeType.CONCEPT)
    T = conv.add_node("T", NodeType.CONCEPT)
    for i, (x, y) in enumerate(((1, 1), (1, 2), (1, 4))):
        M = conv.add_node("M%d" % i, NodeType.CONCEPT)
        worn(conv, S, M, n=x)
        worn(conv, M, T, n=y)
    fixtures.append((conv, S, dict(normalization_sigma=None, floor=0.0)))
    fixtures.append((conv, S, dict(normalization_sigma=1.0, floor=0.0)))

    # (b) a fan whose out-road conductances left-fold, in creation order, to a
    #     different total than math.fsum gives — traverse counts (1,4,4).
    fold_store, fold_hub, _ = star(3, counts=(1, 4, 4))
    fixtures.append((fold_store, fold_hub, dict(normalization_sigma=1.0, floor=0.0)))

    # (c) a fan where S_out - strength differs from the exact sum of the OTHER
    #     roads by 1 ULP — traverse counts (1,1,4), third road: 0.34700000000000003
    #     vs 0.347. SPEC-0b2 §2 names this residue explicitly; here it is made to
    #     bite, so the oracle is shown to resolve at ULP scale.
    resid_store, resid_hub, _ = star(3, counts=(1, 1, 4))
    fixtures.append((resid_store, resid_hub, dict(normalization_sigma=1e-3, floor=0.0)))
    fixtures.append((resid_store, resid_hub, dict(normalization_sigma=1.0, floor=0.0)))

    lone, lone_hub, lone_t = star(1)
    exact = spread_activation(lone, lone_hub).activation[lone_t[0]]
    fixtures.append((lone, lone_hub, dict(floor=exact, normalization_sigma=1.0)))
    fixtures.append((lone, lone_hub, dict(floor=exact, normalization_sigma=None)))

    shut = frozen_store()
    ca = shut.add_node("ca", NodeType.CONCEPT)
    cb = shut.add_node("cb", NodeType.CONCEPT)
    worn(shut, ca, cb, n=6, charge={"dread": -0.95})
    fixtures.append((shut, ca, dict(energy=CLOSED_BREAKTHROUGH_THRESHOLD, floor=0.0,
                                    normalization_sigma=1.0)))

    tick = SteppingClock(1e-6)
    tstore = SubstrateStore(clock=tick)
    ta = tstore.add_node("ta", NodeType.CONCEPT)
    for i in range(4):
        tb = tstore.add_node("tb%d" % i, NodeType.CONCEPT)
        worn(tstore, ta, tb, n=3)

    for flag, why in MUTANTS:
        hit = False
        if flag == "double_read":
            tick.armed = True
            good = oracle_spread(tstore, ta, normalization_sigma=1.0, floor=0.0)
            bad = oracle_spread(tstore, ta, normalization_sigma=1.0, floor=0.0,
                                mutant=(flag,))
            tick.armed = False
            hit = sig_of(good) != sig_of(bad)
        else:
            for store, seed_node, kw in fixtures:
                good = call_or_exc(oracle_spread, store, seed_node, **kw)
                bad = call_or_exc(oracle_spread, store, seed_node, mutant=(flag,), **kw)
                if good != bad:
                    hit = True
                    break
        caught[flag] = hit
        check(hit, f"mutation '{flag}' is DETECTED ({why})")
    print(f"  mutations caught: {sum(caught.values())}/{len(MUTANTS)}")


def test_N1e_loop_closed_on_a_substrate_the_system_itself_built():
    """Loop closure. The substrate is built by traverse() alone, the seeds come
    from perceive(), and the SECOND seed comes from the FIRST spread's own
    ranking — never a hand-placed node id."""
    section("N-1e LOOP-CLOSED: seeds from perceive(), then from the previous "
            "spread's own ranking")
    from psyche_perceive import perceive

    s = frozen_store()
    vocab = ["harbour lantern", "lantern glass", "glass tide", "tide harbour",
             "salt lantern", "night harbour", "night glass", "harbour rope",
             "rope tide", "salt rope", "night salt", "glass rope"]
    ids = [s.add_node(v, NodeType.CONCEPT) for v in vocab]
    rng = random.Random(9091)
    for _ in range(70):
        a, b = rng.choice(ids), rng.choice(ids)
        for _ in range(rng.randint(1, 6)):
            s.traverse(a, b)

    p = perceive(s, "the lantern over the harbour at night")
    check(len(p.sources) >= 3,
          f"perceive() produced real sources to drive the stage ({len(p.sources)})")

    stage1 = 0
    stage2 = 0
    bad = []
    for src, e in sorted(p.sources.items()):
        a = call_or_exc(spread_activation, s, src, energy=e)
        b = call_or_exc(spread_activation, s, src, energy=e, normalization_sigma=None)
        stage1 += 1
        if a != b:
            bad.append(("stage1", src))
        r = spread_activation(s, src, energy=e)
        for nxt, act in r.ranked()[:3]:
            # the NEXT stage is driven by the previous stage's own output, value
            # and node alike
            c = call_or_exc(spread_activation, s, nxt, energy=act)
            d = call_or_exc(spread_activation, s, nxt, energy=act,
                            normalization_sigma=None)
            stage2 += 1
            if c != d:
                bad.append(("stage2", nxt))
    check(not bad, f"neutral identity holds on system-generated input "
                   f"({stage1} first-stage + {stage2} second-stage comparisons); "
                   f"failures={bad[:2]}")
    check(stage2 >= 5, f"the second stage is actually populated ({stage2})")

    # and against the independent oracle on the same system-built input
    orc_bad = [src for src in p.sources
               if call_or_exc(spread_activation, s, src, energy=p.sources[src],
                              normalization_sigma=None)
               != call_or_exc(oracle_spread, s, src, energy=p.sources[src],
                              normalization_sigma=None)]
    check(not orc_bad, f"the same loop-closed input matches the independent oracle "
                       f"({len(p.sources)} sources); failures={orc_bad[:2]}")


def test_N1f_the_field_builder_consumes_the_neutral_path_unchanged():
    """Loop closure one layer up: 1a's field builder calls the engine with no
    sigma at all. Its per-source results must be byte-identical to an explicit
    `normalization_sigma=None` call, or the neutrality is not the one downstream
    actually gets."""
    section("N-1f LOOP-CLOSED through build_activation_field(): the consumer's "
            "results equal explicit sigma=None")
    from psyche_perceive import perceive
    from psyche_field import build_activation_field

    s = frozen_store()
    vocab = ["copper wire", "wire spool", "spool copper", "amber wire",
             "amber glass", "glass spool", "copper amber", "wire glass"]
    ids = [s.add_node(v, NodeType.CONCEPT) for v in vocab]
    rng = random.Random(4242)
    for _ in range(50):
        a, b = rng.choice(ids), rng.choice(ids)
        for _ in range(rng.randint(1, 5)):
            s.traverse(a, b)
    p = perceive(s, "amber glass on copper wire")
    check(bool(p.sources), "perceive() produced sources for the field builder")
    fld = build_activation_field(s, sorted(p.sources), source_energies=p.sources)
    bad = []
    for src, res in fld.results.items():
        direct = spread_activation(s, src, energy=p.sources[src],
                                   normalization_sigma=None)
        if sig_of(res) != sig_of(direct):
            bad.append(src)
    check(not bad, f"every one of {len(fld.results)} per-source field results is "
                   f"byte-identical to an explicit sigma=None spread; failures={bad}")
    check(len(fld.results) >= 2, f"more than one source drove the field "
                                 f"({len(fld.results)})")


def test_N1g_the_parameter_is_keyword_only_and_defaults_to_None():
    section("N-1g the neutrality lives in the SIGNATURE, not only at a call site")
    params = inspect.signature(spread_activation).parameters
    check("normalization_sigma" in params, "the parameter exists")
    p = params["normalization_sigma"]
    check(p.default is None, f"its default is None (got {p.default!r})")
    check(p.kind is inspect.Parameter.KEYWORD_ONLY,
          f"it is keyword-only, so no positional caller can enable it by accident "
          f"(kind={p.kind})")
    s, hub, _ = star(2)
    try:
        spread_activation(s, hub, 1.0)                     # type: ignore[misc]
        check(False, "a positional third argument is refused")
    except TypeError:
        check(True, "a positional third argument is refused (TypeError)")


def test_N1h_the_neutral_path_does_not_change_the_store_read_pattern():
    """Byte-identity of the RESULT is not the whole of neutrality: if the neutral
    path read the store differently it would be neutral only on a frozen clock,
    which is exactly how DEFECT-B hid."""
    section("N-1h the neutral path reads the store exactly as the omitted "
            "parameter does — and the overlay ON adds no reads either")
    s, hub, tg = star(6)
    worn(s, tg[0], tg[1], n=4)
    worn(s, tg[1], tg[2], n=2)

    def reads_for(**kw):
        proxy = RoadReadCounter(s)
        spread_activation(proxy, hub, **kw)
        return [r[0] for r in proxy.reads]

    omitted = reads_for()
    explicit = reads_for(normalization_sigma=None)
    enabled = reads_for(normalization_sigma=1.0)
    check(omitted == explicit,
          f"identical read sequence with the parameter omitted vs explicit None "
          f"({len(omitted)} vs {len(explicit)} reads)")
    check(omitted == enabled,
          f"identical read sequence with the overlay ON — one read per road per "
          f"expansion, which is DEFECT-B's fix ({len(omitted)} vs {len(enabled)})")
    from collections import Counter
    per_road = Counter(enabled)
    check(set(per_road.values()) == {1},
          f"no road is read twice in an expansion (counts={sorted(set(per_road.values()))})")

    # And the sharpest form of the neutrality claim: on a clock that ADVANCES,
    # driven over the IDENTICAL tick sequence, the neutral path is byte-identical.
    # This is the one place neutrality could still break after DEFECT-B, because
    # unequal read counts would consume unequal amounts of clock.
    clk = SteppingClock(0.25)
    ts = SubstrateStore(clock=clk)
    chain = [ts.add_node("c%d" % i, NodeType.CONCEPT) for i in range(6)]
    for i in range(5):
        worn(ts, chain[i], chain[i + 1], n=2 + i)
    clk.armed = True
    start = clk._t
    runs = {}
    ticks = {}
    for label, kw in (("omitted", {}), ("none", dict(normalization_sigma=None)),
                      ("1e300", dict(normalization_sigma=1e300)),
                      ("1.0", dict(normalization_sigma=1.0))):
        clk._t = start                                     # rewind to the same instant
        runs[label] = sig_of(spread_activation(ts, chain[0], floor=0.0, **kw))
        ticks[label] = clk._t - start
    check(ticks["omitted"] > 0.0,
          f"the clock genuinely advanced during the spread ({ticks['omitted']})")
    check(len(set(ticks.values())) == 1,
          f"every sigma consumes the same number of clock ticks {ticks} — unequal "
          f"read counts are DEFECT-B's cause, and they are gone")
    check(runs["omitted"] == runs["none"],
          "on a MOVING clock over an identical tick sequence, omitted == None "
          "byte-for-byte")
    check(runs["omitted"] == runs["1e300"],
          "and sigma=1e300 recovers it byte-for-byte there too")
    check(runs["omitted"] == runs["1.0"],
          "and on a single-out-road chain sigma=1.0 is byte-identical as well "
          "(N-5 on a clock that advances)")


# ═════════════════════════════════════════════════════════════════════════════
# N-2  DETERMINISM — hash seeds AND every CPython minor version on this machine.
# ═════════════════════════════════════════════════════════════════════════════

HASH_SEEDS = ["0", "1", "2", "3", "7", "42"]

_EXTRA_BUILD_CANDIDATES = [
    "/opt/homebrew/bin/python3.14", "/opt/homebrew/bin/python3.10",
    "/opt/homebrew/bin/python3.11", "/opt/homebrew/bin/python3.13",
    "/usr/local/bin/python3.10", "/opt/local/bin/python3.10",
    "/opt/local/bin/python3.11", "/opt/local/bin/python3.12",
    "/opt/anaconda3/bin/python3.12",
]


def _version_of(path):
    try:
        r = subprocess.run([path, "-c", "import sys;print('%d.%d.%d' % sys.version_info[:3])"],
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def interpreters():
    """Every CPython MINOR version reachable on this machine, plus any additional
    BUILD of the same minor version found at a different prefix. A build split
    (3.14.4 vs 3.14.5) is free extra coverage and costs one subprocess."""
    found = {}
    for name in ("python3.10", "python3.11", "python3.12", "python3.13", "python3.14"):
        path = shutil.which(name)
        if path:
            v = _version_of(path)
            if v:
                found[path] = v
    for path in _EXTRA_BUILD_CANDIDATES:
        if path in found or not os.path.exists(path):
            continue
        v = _version_of(path)
        if v and v not in found.values():
            found[path] = v
    if not found:
        found[sys.executable] = _version_of(sys.executable) or "?"
    return found


_INTERPS = None


def all_interpreters():
    global _INTERPS
    if _INTERPS is None:
        _INTERPS = interpreters()
    return _INTERPS


def run_matrix(driver, reps=1, seeds=None):
    outs = []
    base = dict(os.environ)
    base["PYTHONPATH"] = SRC + (os.pathsep + base["PYTHONPATH"]
                                if base.get("PYTHONPATH") else "")
    for path in all_interpreters():
        for seed in (seeds if seeds is not None else HASH_SEEDS):
            for _ in range(reps):
                env = dict(base, PYTHONHASHSEED=seed)
                r = subprocess.run([path, "-c", driver], cwd=HERE,
                                   capture_output=True, text=True, env=env)
                if r.returncode != 0:
                    outs.append(("ERROR", path, seed, r.stderr.strip()[-400:]))
                else:
                    outs.append(("OK", path, seed, r.stdout.strip()))
    return outs


# The determinism fixture is deliberately the SHAPE THAT BROKE: a node with three
# convergent contributions, which is the smallest number that can break float
# associativity (a+b == b+a is exact). It also carries a self-loop, a cycle back
# to the seed, a leaking closed road and a high-degree fan. Built with traverse()
# only, at library defaults, on a frozen clock so the run is a function of the
# graph alone. Node ids are uuid4 and differ per process, so the digest is keyed
# by node CONTENT.
DET_DRIVER = textwrap.dedent('''
    import hashlib, struct, math
    from psyche_store import SubstrateStore, Clock, NodeType
    from psyche_activation import spread_activation

    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    def add(c): return s.add_node(c, NodeType.CONCEPT)
    def w(a, b, n, ch=None):
        for _ in range(n): s.traverse(a, b, ch)

    S = add("S"); T = add("T"); Z = add("Z")
    mids = [add("M%d" % i) for i in range(5)]
    for i, m in enumerate(mids):
        w(S, m, 1 + (i % 3))
        w(m, T, 2 + (i * 3) % 11)        # T accumulates FIVE contributions
    w(S, S, 3)                            # self-loop
    w(T, S, 4)                            # cycle back to the seed
    w(S, Z, 5, {"dread": -0.95})          # closed road, leaks above threshold
    fan = [add("f%02d" % i) for i in range(12)]
    for i, f in enumerate(fan):
        w(mids[i % 5], f, 1 + (i % 7))

    indeg = {}
    for r in s.all_road_ids():
        rd = s.get_road(r, apply_decay=False)
        indeg[rd.target_id] = indeg.get(rd.target_id, 0) + 1
    assert max(indeg.values()) >= 3, "fixture drift: the convergence node is gone"

    def bits(x): return struct.pack("<d", x).hex()
    lines = []
    for sigma in (None, 0.25, 1.0, 7.5, 1e300):
        for energy in (1.0, 3.0):
            r = spread_activation(s, S, energy=energy, floor=0.0,
                                  normalization_sigma=sigma)
            act = sorted((s.get_node(n).content, bits(v))
                         for n, v in r.activation.items())
            hop = sorted((s.get_node(n).content, h) for n, h in r.hops.items())
            flw = sorted((s.get_node(s.get_road(k, apply_decay=False).source_id).content,
                          s.get_node(s.get_road(k, apply_decay=False).target_id).content,
                          bits(v)) for k, v in r.flow.items())
            brk = sorted(s.get_node(s.get_road(k, apply_decay=False).source_id).content +
                         "->" +
                         s.get_node(s.get_road(k, apply_decay=False).target_id).content
                         for k in r.broke_through)
            lines.append(repr((sigma, energy, act, hop, flw, brk)))
    payload = "\\n".join(lines)
    print(hashlib.sha256(payload.encode()).hexdigest())
''')


def test_N2a_bit_exact_across_hash_seeds_and_every_cpython_on_this_machine():
    section("N-2a determinism: one bit pattern across 6 hash seeds x every CPython "
            "minor version present, overlay OFF and ON, on the shape that broke")
    interps = all_interpreters()
    for path, ver in sorted(interps.items(), key=lambda kv: kv[1]):
        print(f"    {ver:10s} {path}")
    outs = run_matrix(DET_DRIVER, reps=2)
    errors = [o for o in outs if o[0] == "ERROR"]
    check(not errors, f"every probe process ran ({len(errors)} errors; "
                      f"first={errors[:1]})")
    digests = {o[3] for o in outs if o[0] == "OK"}
    check(len(digests) == 1,
          f"one SHA-256 over {len(outs)} fresh processes "
          f"({len(interps)} interpreters x {len(HASH_SEEDS)} seeds x 2 reps); "
          f"distinct={len(digests)} {sorted(digests)[:3]}")
    minors = {v.rsplit(".", 1)[0] for v in interps.values()}
    check(len(minors) >= 5,
          f"the interpreter axis is populated with >=5 CPython MINOR versions "
          f"(found {sorted(minors)})")
    print(f"  digest: {sorted(digests)[0] if digests else 'n/a'}")


def test_N2b_order_independence_not_merely_order_pinning():
    """Determinism that rests on the container happening to iterate in a fixed
    order is order-PINNING; it dies the moment anything reorders. Order-
    INDEPENDENCE is the stronger property and is what fsum buys. Attack it by
    permuting the out-road iteration from outside the engine."""
    section("N-2b order-INDEPENDENCE: permuting out-road iteration changes no value")
    # a node with 3+ convergent contributions AND a hub with 5 out-roads
    s = frozen_store()
    S = s.add_node("S", NodeType.CONCEPT)
    T = s.add_node("T", NodeType.CONCEPT)
    ms = []
    for i, (x, y) in enumerate(((1, 2), (1, 3), (1, 9), (2, 5), (1, 14))):
        m = s.add_node("M%d" % i, NodeType.CONCEPT)
        worn(s, S, m, n=x)
        worn(s, m, T, n=y)
        ms.append(m)
    base_ids = list(s.roads_from(S))
    check(len(base_ids) == 5, f"the hub really has 5 out-roads ({len(base_ids)})")

    for sigma in (None, 1.0):
        seen = set()
        for perm in itertools.permutations(range(5)):
            def permute(lst, perm=perm):
                return [lst[i] for i in perm] if len(lst) == 5 else lst
            r = spread_activation(OutRoadPermuter(s, permute), S,
                                  floor=0.0, normalization_sigma=sigma)
            seen.add(sig_unordered(r, s))
        check(len(seen) == 1,
              f"sigma={sigma!r}: all {math.factorial(5)} out-road orders give one "
              f"result to the bit (distinct={len(seen)})")

    # non-vacuity: the SAME contributions summed by an explicit left fold DO
    # disagree across orders, so the assertion above would catch a naive engine.
    r = spread_activation(s, S, floor=0.0)
    terms = [r.flow[s.find_road(m, T)] for m in ms]
    folds = set()
    for perm in itertools.permutations(terms):
        acc = 0.0
        for t in perm:
            acc = acc + t
        folds.add(bits(acc))
    check(len(folds) > 1,
          f"non-vacuity: a naive left fold over the very same {len(terms)} "
          f"contributions yields {len(folds)} distinct totals, so N-2b would "
          f"genuinely catch a naive accumulator")
    check(len({bits(math.fsum(p)) for p in itertools.permutations(terms)}) == 1,
          "math.fsum over the same terms is invariant under all orders")


def test_N2c_repeated_runs_in_one_process_are_bit_identical():
    section("N-2c repeated identical calls in one process are bit-identical "
            "(overlay ON, frozen clock)")
    for gseed in range(12):
        store, ids = hostile_graph(gseed)
        if not ids:
            continue
        seed_node = ids[0]
        sigs = {sig_of(spread_activation(store, seed_node, floor=0.0,
                                         normalization_sigma=1.0)) for _ in range(6)}
        check(len(sigs) == 1, f"graph {gseed}: {len(sigs)} distinct results over 6 "
                              f"identical calls")


# ═════════════════════════════════════════════════════════════════════════════
# N-3  PURITY
# ═════════════════════════════════════════════════════════════════════════════

def test_N3a_substrate_is_byte_identical_after_normalized_spreads():
    section("N-3a purity: the stored substrate is byte-identical after normalized "
            "spreads over 40 hostile graphs")
    bad = []
    for gseed in range(40):
        store, ids = hostile_graph(gseed)
        before = substrate_snapshot(store)
        for seed_node in ids[:4]:
            for sg in (None, 0.25, 1.0, 1e300):
                for params in (dict(), dict(floor=0.0), dict(energy=1e6, floor=0.0)):
                    try:
                        spread_activation(store, seed_node, normalization_sigma=sg,
                                          **params)
                    except Exception:                      # noqa: BLE001
                        pass
        if substrate_snapshot(store) != before:
            bad.append(gseed)
    check(not bad, f"no stored byte changed on any of 40 graphs; failures={bad}")


def test_N3b_no_mutating_store_method_is_ever_called():
    section("N-3b purity: structurally, the engine never calls a mutating method")
    for gseed in range(20):
        store, ids = hostile_graph(gseed)
        trap = WriteTrap(store)
        for seed_node in ids[:3]:
            for sg in (None, 1.0):
                try:
                    spread_activation(trap, seed_node, floor=0.0,
                                      normalization_sigma=sg)
                except AssertionError:
                    break
                except Exception:                          # noqa: BLE001
                    pass
        check(not trap.violations,
              f"graph {gseed}: mutating methods called = {trap.violations}")


def test_N3c_lazy_decay_is_never_persisted_even_on_a_moving_clock():
    """`last_touched` is the witness. If _persist_decay were entered, the stored
    road would advance; a pure read leaves it exactly where the last write put it.
    Run on a MOVING clock, which is the only place this could go wrong."""
    section("N-3c purity: _persist_decay is never entered, on a clock that advances")
    clock = SteppingClock(5e-4)
    s = SubstrateStore(clock=clock)
    hub = s.add_node("hub", NodeType.CONCEPT)
    tg = [s.add_node("t%d" % i, NodeType.CONCEPT) for i in range(5)]
    for t in tg:
        worn(s, hub, t, n=4)
    worn(s, tg[0], tg[1], n=3)
    clock.armed = True
    before = substrate_snapshot(s)
    for _ in range(6):
        for sg in (None, 1.0, 1e300):
            spread_activation(s, hub, floor=0.0, normalization_sigma=sg)
    after = substrate_snapshot(s)
    check(before == after,
          "the stored substrate (strength, charges, closure, traversal_count, "
          "last_touched, access_count) is unchanged after 18 spreads on a moving clock")
    check(s.clock.now() > 0.0, "the clock genuinely advanced during those spreads")


def test_N3d_integrity_survives_a_randomized_mutation_battery():
    section("N-3d integrity: indices stay mutually consistent through a randomized "
            "mutation battery interleaved with normalized spreads")
    rng = random.Random(777)
    clock = Clock(simulated=True, start=0.0)
    s = SubstrateStore(clock=clock)
    ids = [s.add_node("b%02d" % i, NodeType.CONCEPT) for i in range(12)]
    errors = []
    for step in range(320):
        op = rng.random()
        try:
            if op < 0.42 and ids:
                a, b = rng.choice(ids), rng.choice(ids)
                s.traverse(a, b, {"dread": -0.9} if rng.random() < 0.2 else None)
            elif op < 0.55:
                ids.append(s.add_node("x%03d" % step, NodeType.CONCEPT))
            elif op < 0.65 and len(ids) > 3:
                victim = rng.choice(ids)
                ids.remove(victim)
                s.remove_node(victim)
            elif op < 0.72:
                rid_list = list(s.all_road_ids())
                if rid_list:
                    s.remove_road(rng.choice(rid_list))
            elif op < 0.80 and ids:
                s.pin(rng.choice(ids))
            elif op < 0.86 and ids:
                s.unpin(rng.choice(ids))
            elif op < 0.93:
                clock.advance(rng.uniform(0.0, 12.0))
            elif ids:
                spread_activation(s, rng.choice(ids), floor=0.0,
                                  normalization_sigma=rng.choice([None, 0.3, 1.0]))
        except Exception as exc:                           # noqa: BLE001
            # NotFound / ValueError / "refusing to remove pinned node" are the
            # store's OWN documented refusals and are correct outcomes of a random
            # battery. Anything else is a real failure.
            refusal = (isinstance(exc, (NotFound, ValueError))
                       or (type(exc).__name__ == "IntegrityError"
                           and "refusing to remove pinned node" in str(exc)))
            if not refusal:
                errors.append((step, type(exc).__name__, str(exc)[:120]))
        try:
            s.check_integrity()
        except Exception as exc:                           # noqa: BLE001
            errors.append((step, "integrity", str(exc)[:160]))
            break
    check(not errors, f"320 mutation steps left every index mutually consistent; "
                      f"errors={errors[:2]}")
    check(s.node_count() >= 1, "the battery left a non-empty store to check")


# ═════════════════════════════════════════════════════════════════════════════
# N-4  ORDER-INDEPENDENCE OF S_out, and S_out's VALUE pinned exactly.
# ═════════════════════════════════════════════════════════════════════════════

def _fold(xs):
    acc = 0.0
    for x in xs:
        acc = acc + x
    return acc


def test_N4a_the_probe_is_sensitive_to_the_bug_it_claims_to_catch():
    """Search traverse-count multisets for one whose LEFT FOLD is genuinely
    order-dependent. If none existed, every N-4 assertion below would pass
    vacuously against a naive engine. Searched, not hardcoded."""
    section("N-4a sensitivity: a left fold over these out-road strengths IS "
            "order-dependent (else N-4 is vacuous)")
    strengths = {}
    for n in range(1, 16):
        s = frozen_store()
        a = s.add_node("a", NodeType.CONCEPT)
        b = s.add_node("b", NodeType.CONCEPT)
        worn(s, a, b, n=n)
        strengths[n] = s.get_road(s.find_road(a, b)).strength
    # The tuple must satisfy BOTH: (i) its left fold IN CREATION ORDER differs from
    # math.fsum — otherwise N-4b cannot distinguish the two implementations; and
    # (ii) its left fold depends on the order — otherwise "order-independence" is
    # not being tested at all. Searched over ORDERED tuples, not multisets, because
    # the engine iterates in creation order and that is the order that matters.
    found = None
    for k in (3, 4):
        for combo in itertools.product(range(1, 16), repeat=k):
            vals = [strengths[c] for c in combo]
            if bits(_fold(vals)) == bits(math.fsum(vals)):
                continue
            if len({bits(_fold(p)) for p in itertools.permutations(vals)}) > 1:
                found = combo
                break
        if found:
            break
    check(found is not None,
          "a traverse-count TUPLE exists whose creation-order left fold both "
          "differs from math.fsum and depends on the order")
    globals()["_FOLD_SENSITIVE_COUNTS"] = found
    if found:
        vals = [strengths[c] for c in found]
        folds = {bits(_fold(p)) for p in itertools.permutations(vals)}
        fsums = {bits(math.fsum(p)) for p in itertools.permutations(vals)}
        print(f"  traverse counts {found} -> creation-order fold {_fold(vals)!r} vs "
              f"fsum {math.fsum(vals)!r}; {len(folds)} distinct fold totals across "
              f"orders, {len(fsums)} distinct fsum totals")
        check(bits(_fold(vals)) != bits(math.fsum(vals)),
              "the creation-order fold and the exactly-rounded sum genuinely differ")
        check(len(folds) > 1, f"the left fold really is order-dependent ({len(folds)})")
        check(len(fsums) == 1, f"math.fsum really is not ({len(fsums)})")


def test_N4b_S_out_equals_fsum_and_not_the_left_fold():
    """Pins S_out's VALUE, not merely its stability. On the fold-sensitive fixture
    the two candidate totals differ, so this distinguishes an fsum implementation
    from a folding one rather than merely observing that the answer is stable."""
    section("N-4b S_out equals math.fsum of the out-road strengths, to the bit, and "
            "is NOT the left-fold value")
    counts = globals().get("_FOLD_SENSITIVE_COUNTS")
    check(counts is not None, "the sensitive fixture is available")
    if not counts:
        return
    s, hub, tgts = star(len(counts), counts=counts)
    strengths = [s.get_road(s.find_road(hub, t)).strength for t in tgts]
    total_fsum = math.fsum(strengths)
    sigma = 1.0
    r = spread_activation(s, hub, floor=0.0, normalization_sigma=sigma)
    ok_fsum = True
    distinguishes = False
    for t, st in zip(tgts, strengths):
        rid = s.find_road(hub, t)
        want = DEFAULT_SEED_ENERGY * st * DEFAULT_DECAY_PER_HOP
        comp = total_fsum - st
        if comp > 0.0:
            want *= sigma / (sigma + comp)
        if bits(r.flow[rid]) != bits(want):
            ok_fsum = False
        alt = DEFAULT_SEED_ENERGY * st * DEFAULT_DECAY_PER_HOP
        comp_alt = _fold(strengths) - st
        if comp_alt > 0.0:
            alt *= sigma / (sigma + comp_alt)
        if bits(alt) != bits(want):
            distinguishes = True
    check(ok_fsum, "every transmitted value equals act*s*decay*sigma/(sigma+S_out-s) "
                   "computed with math.fsum, bit for bit")
    check(distinguishes,
          "and the left-fold alternative would have given a DIFFERENT answer on this "
          "fixture, so the assertion discriminates rather than merely agreeing")


def test_N4c_S_out_is_order_independent_on_high_degree_fans():
    section("N-4c S_out order-independence on random high-degree fans "
            "(property-based, shuffled through a proxy)")
    rng = random.Random(31337)
    bad = []
    for trial in range(22):
        k = rng.randint(8, 40)
        counts = [rng.randint(1, 14) for _ in range(k)]
        s, hub, _ = star(k, counts=counts)
        seen = set()
        for _ in range(6):
            order = list(range(k))
            rng.shuffle(order)

            def permute(lst, order=order):
                return [lst[i] for i in order] if len(lst) == len(order) else lst
            r = spread_activation(OutRoadPermuter(s, permute), hub, floor=0.0,
                                  normalization_sigma=0.75)
            seen.add(sig_unordered(r, s))
        if len(seen) != 1:
            bad.append((trial, k, len(seen)))
    check(not bad, f"22 fans of out-degree 8..40, 6 shuffles each, one result "
                   f"apiece; failures={bad[:2]}")


# ═════════════════════════════════════════════════════════════════════════════
# N-5  LIMITING CASE — a lone out-road is never attenuated, at any sigma.
#      FROZEN CLOCK for cross-call comparison; MOVING CLOCK for the within-call
#      identity, which the noise floor cannot reach.
# ═════════════════════════════════════════════════════════════════════════════

def test_N5a_lone_out_road_is_byte_identical_at_every_sigma_frozen_clock():
    section("N-5a a lone out-road: sigma ON is byte-identical to sigma OFF at every "
            "sigma on the ladder (frozen clock)")
    # a CHAIN, so the property is tested at every hop, not only the first
    s = frozen_store()
    chain = [s.add_node("c%02d" % i, NodeType.CONCEPT) for i in range(7)]
    for i in range(6):
        worn(s, chain[i], chain[i + 1], n=2 + i)
    off = sig_of(spread_activation(s, chain[0], floor=0.0))
    bad = []
    for sg in SIGMA_LADDER:
        if sig_of(spread_activation(s, chain[0], floor=0.0,
                                    normalization_sigma=sg)) != off:
            bad.append(sg)
    check(not bad, f"identical at all {len(SIGMA_LADDER)} sigmas on a 6-hop "
                   f"single-out-road chain; deviations at {bad}")

    # a lone out-road that is a SELF-LOOP: competing is still exactly 0
    s2 = frozen_store()
    n0 = s2.add_node("solo", NodeType.CONCEPT)
    worn(s2, n0, n0, n=5)
    off2 = sig_of(spread_activation(s2, n0, floor=0.0))
    bad2 = [sg for sg in SIGMA_LADDER
            if sig_of(spread_activation(s2, n0, floor=0.0,
                                        normalization_sigma=sg)) != off2]
    check(not bad2, f"a lone SELF-LOOP out-road is also unattenuated at every sigma; "
                    f"deviations at {bad2}")


def test_N5b_the_negative_control_a_second_road_DOES_attenuate():
    section("N-5b negative control: adding one sibling road DOES attenuate, so "
            "N-5a is not passing because the overlay does nothing")
    s, hub, tg = star(1)
    lone = spread_activation(s, hub, floor=0.0,
                             normalization_sigma=1.0).activation[tg[0]]
    lone_off = spread_activation(s, hub, floor=0.0).activation[tg[0]]
    check(bits(lone) == bits(lone_off), "one out-road: unattenuated")
    s2, hub2, tg2 = star(2)
    two_on = spread_activation(s2, hub2, floor=0.0,
                               normalization_sigma=1.0).activation[tg2[0]]
    two_off = spread_activation(s2, hub2, floor=0.0).activation[tg2[0]]
    check(two_on < two_off,
          f"two out-roads: attenuated ({two_on!r} < {two_off!r})")


def test_N5c_lone_out_road_factor_is_exactly_one_on_a_MOVING_clock():
    """DEFECT-B's home. Written as a WITHIN-CALL identity: the road's decayed
    strength is observed at the single instant the engine read it, and the
    transmitted value must equal act*s*decay exactly. That identity is immune to
    the P-0 noise floor, which only contaminates comparisons ACROSS calls."""
    section("N-5c a lone out-road transmits with factor exactly 1.0 on a clock that "
            "ADVANCES (within-call identity, immune to the noise floor)")
    for dt in (1e-9, 1e-6, 1e-3, 0.5):
        clock = SteppingClock(dt)
        s = SubstrateStore(clock=clock)
        a = s.add_node("a", NodeType.CONCEPT)
        b = s.add_node("b", NodeType.CONCEPT)
        worn(s, a, b, n=3)
        clock.armed = True
        for sg in (1e-12, 1.0, 1e12):
            proxy = RoadReadCounter(s)
            res = spread_activation(proxy, a, floor=0.0, normalization_sigma=sg)
            rid = s.find_road(a, b)
            reads = [x for x in proxy.reads if x[0] == rid]
            observed = reads[0][1]
            want = DEFAULT_SEED_ENERGY * observed * DEFAULT_DECAY_PER_HOP
            check(len(reads) == 1,
                  f"dt={dt} sigma={sg}: the road is read exactly once in the "
                  f"expansion (got {len(reads)})")
            check(bits(res.flow[rid]) == bits(want),
                  f"dt={dt} sigma={sg}: transmitted == act*s*decay to the bit "
                  f"({res.flow[rid]!r} vs {want!r})")


def test_N5d_competing_is_exactly_zero_for_a_lone_road_at_every_worn_strength():
    """`competing = S_out - strength`. For one road that is fsum([s]) - s, which
    must be exactly 0.0 for every representable s — including a heavily decayed
    one, which is where an elapsed-time residue would show."""
    section("N-5d competing is exactly 0.0 for a lone out-road at every strength "
            "the substrate can produce, decayed or saturated")
    bad = []
    for n in (1, 2, 3, 5, 9, 14, 30, 90):
        for decay_secs in (0.0, 3.5, 40.0, 500.0):
            clock = Clock(simulated=True, start=0.0)
            s = SubstrateStore(clock=clock)
            a = s.add_node("a", NodeType.CONCEPT)
            b = s.add_node("b", NodeType.CONCEPT)
            worn(s, a, b, n=n)
            clock.advance(decay_secs)
            st = s.get_road(s.find_road(a, b)).strength
            if math.fsum([st]) - st != 0.0:
                bad.append((n, decay_secs, st))
            on = spread_activation(s, a, floor=0.0, normalization_sigma=1.0)
            off = spread_activation(s, a, floor=0.0)
            if sig_of(on) != sig_of(off):
                bad.append((n, decay_secs, "engine"))
    check(not bad, f"32 (wear x decay) combinations give competing exactly 0.0 and "
                   f"an unattenuated transmission; failures={bad[:3]}")


# ═════════════════════════════════════════════════════════════════════════════
# N-6  MONOTONICITY
# ═════════════════════════════════════════════════════════════════════════════

def test_N6a_strictly_decreasing_in_competing_conductance():
    section("N-6a transmitted activation is strictly decreasing in the competing "
            "conductance")
    prev = None
    vals = []
    for k in range(1, 13):
        s, hub, tg = star(k)
        v = spread_activation(s, hub, floor=0.0,
                              normalization_sigma=1.0).activation[tg[0]]
        vals.append(v)
        if prev is not None:
            check(v < prev, f"out-degree {k}: {v!r} < {prev!r}")
        prev = v
    # and with competing raised by STRENGTH rather than by count
    s, hub, tg = star(2, counts=(3, 1))
    weak = spread_activation(s, hub, floor=0.0,
                             normalization_sigma=1.0).activation[tg[0]]
    s2, hub2, tg2 = star(2, counts=(3, 14))
    strong = spread_activation(s2, hub2, floor=0.0,
                               normalization_sigma=1.0).activation[tg2[0]]
    check(strong < weak,
          f"a STRONGER sibling attenuates more than a weaker one ({strong!r} < {weak!r})")


def test_N6b_increasing_in_sigma_and_the_exact_point_where_strictness_ends():
    section("N-6b transmitted activation increases with sigma — strictly until it "
            "saturates at the unnormalized value, then exactly equal")
    s, hub, tg = star(4)
    coarse = [1e-6, 1e-3, 0.1, 0.5, 1.0, 2.0, 10.0, 1e3, 1e6, 1e12]
    vals = [spread_activation(s, hub, floor=0.0,
                              normalization_sigma=v).activation[tg[0]]
            for v in coarse]
    check(all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)),
          f"strictly increasing over the unsaturated regime: {[repr(v) for v in vals]}")
    off = spread_activation(s, hub, floor=0.0).activation[tg[0]]
    check(all(v < off for v in vals),
          "and every one is strictly below the unnormalized value")
    sat = [spread_activation(s, hub, floor=0.0,
                             normalization_sigma=v).activation[tg[0]]
           for v in (1e100, 1e300)]
    check(all(bits(v) == bits(off) for v in sat),
          "at 1e100 and 1e300 it has saturated to the unnormalized value exactly")
    note("SPEC-0b2 N-6 says 'strictly increasing in sigma'. In float arithmetic that "
         "is true only until saturation: past ~1e13 the factor rounds to exactly 1.0 "
         "and further sigma changes nothing. That is N-7's convergence, and the two "
         "statements are in tension only if 'strictly' is read past the limit. "
         "Recorded, not counted as a failure — the engine cannot do better and the "
         "saturating behaviour is the one the spec wants.")
    # ULP-adjacent: never DEcreasing as sigma increases by one ULP
    ladder = [1.0]
    for _ in range(80):
        ladder.append(math.nextafter(ladder[-1], math.inf))
    fine = [spread_activation(s, hub, floor=0.0,
                              normalization_sigma=v).activation[tg[0]]
            for v in ladder]
    check(all(fine[i] <= fine[i + 1] for i in range(len(fine) - 1)),
          "monotone NON-DECREASING across 80 ULP-adjacent sigmas — no rounding "
          "inversion")
    check(len({bits(v) for v in fine}) > 1,
          f"and the ULP ladder is not flat, so the check has resolution "
          f"({len({bits(v) for v in fine})} distinct values)")


def test_N6c_normalized_never_exceeds_unnormalized_property_based():
    section("N-6c property-based: normalized transmission never exceeds "
            "unnormalized, on 35 random hostile graphs")
    bad = []
    for gseed in range(35):
        store, ids = hostile_graph(gseed)
        for seed_node in ids[:3]:
            off = spread_activation(store, seed_node, floor=0.0)
            for sg in (0.05, 1.0, 25.0):
                on = spread_activation(store, seed_node, floor=0.0,
                                       normalization_sigma=sg)
                for rid, v in on.flow.items():
                    ov = off.flow.get(rid)
                    if ov is None:
                        bad.append((gseed, "road present ON but absent OFF", rid))
                    elif not (abs(v) <= abs(ov) or bits(v) == bits(ov)):
                        bad.append((gseed, sg, rid, v, ov))
    check(not bad, f"no normalized flow exceeds its unnormalized counterpart; "
                   f"failures={bad[:3]}")


# ═════════════════════════════════════════════════════════════════════════════
# N-7  sigma -> infinity CONVERGENCE, and sigma's DOMAIN
# ═════════════════════════════════════════════════════════════════════════════

def test_N7a_gap_to_the_unnormalized_engine_is_monotone_non_increasing():
    section("N-7a the gap to the unnormalized engine shrinks monotonically along a "
            "sigma ladder, on hostile graphs")
    bad = []
    checked = 0
    for gseed in range(25):
        store, ids = hostile_graph(gseed)
        for seed_node in ids[:2]:
            off = spread_activation(store, seed_node, floor=0.0)
            gaps = []
            for sg in (1e-3, 0.1, 1.0, 10.0, 1e3, 1e6, 1e12, 1e300):
                on = spread_activation(store, seed_node, floor=0.0,
                                       normalization_sigma=sg)
                gaps.append(math.fsum(abs(off.activation.get(n, 0.0) -
                                          on.activation.get(n, 0.0))
                                      for n in set(off.activation) | set(on.activation)))
            checked += 1
            if any(gaps[i + 1] > gaps[i] for i in range(len(gaps) - 1)):
                bad.append((gseed, gaps))
    check(not bad, f"{checked} (graph, seed) ladders are monotone non-increasing; "
                   f"failures={bad[:2]}")


def test_N7b_large_finite_sigma_recovers_the_unnormalized_engine_byte_for_byte():
    section("N-7b sigma = 1e100 and 1e300 recover sigma=None BYTE-FOR-BYTE on "
            "hostile graphs")
    bad = []
    compared = 0
    for gseed in range(35):
        store, ids = hostile_graph(gseed)
        for seed_node in ids[:3]:
            off = call_or_exc(spread_activation, store, seed_node, floor=0.0)
            for sg in (1e100, 1e300):
                on = call_or_exc(spread_activation, store, seed_node, floor=0.0,
                                 normalization_sigma=sg)
                compared += 1
                if on != off:
                    bad.append((gseed, sg))
    check(not bad, f"{compared} comparisons recover the unnormalized engine exactly; "
                   f"failures={bad[:3]}")


def test_N7c_sigmas_domain_is_validated_at_the_boundary():
    """DEFECT-C's regression guard. SPEC-0b2 §2 originally named float('inf') as
    'the value that analytically recovers the current engine'; it computes
    inf/inf = NaN, and NaN passes `transmitted < floor` silently because every
    comparison with NaN is False. The domain must be refused, loudly."""
    section("N-7c sigma's domain: inf / -inf / nan / 0.0 / -0.0 / negative are all "
            "REFUSED with ValueError, before any work")
    s, hub, tg = star(3)
    before = substrate_snapshot(s)
    for bad_sigma in (float("inf"), float("-inf"), float("nan"), 0.0, -0.0,
                      -1.0, -1e-300, -1e300):
        try:
            r = spread_activation(s, hub, floor=0.0, normalization_sigma=bad_sigma)
            nans = [n for n, v in r.activation.items() if not math.isfinite(v)]
            check(False, f"sigma={bad_sigma!r} was ACCEPTED and returned "
                         f"{len(r.activation)} nodes ({len(nans)} non-finite)")
        except ValueError:
            check(True, f"sigma={bad_sigma!r} refused with ValueError")
        except Exception as exc:                           # noqa: BLE001
            check(False, f"sigma={bad_sigma!r} raised {type(exc).__name__}, "
                         f"expected ValueError")
    check(substrate_snapshot(s) == before,
          "a refused sigma leaves the substrate untouched")

    # refused BEFORE the seed is resolved: the error belongs to the caller's frame
    try:
        spread_activation(s, "not-a-node", normalization_sigma=float("inf"))
        check(False, "an invalid sigma with an unknown seed raises")
    except ValueError:
        check(True, "an invalid sigma is refused BEFORE the unknown seed is "
                    "reported (ValueError, not NotFound)")
    except NotFound:
        check(False, "sigma validation happens AFTER seed resolution — the spec "
                     "says 'at the boundary, before any work'")

    # the accepted edge of the domain
    for good in (5e-324, 1e-300, 1, True, 1e308):
        try:
            spread_activation(s, hub, floor=0.0, normalization_sigma=good)
            check(True, f"sigma={good!r} is accepted (finite and strictly positive)")
        except Exception as exc:                           # noqa: BLE001
            check(False, f"sigma={good!r} was refused with "
                         f"{type(exc).__name__}: {exc}")
    intish = spread_activation(s, hub, floor=0.0, normalization_sigma=1)
    floatish = spread_activation(s, hub, floor=0.0, normalization_sigma=1.0)
    check(sig_of(intish) == sig_of(floatish),
          "an int sigma of 1 is byte-identical to a float sigma of 1.0")


def test_N7d_no_reachable_input_makes_the_overlay_emit_a_non_finite_value():
    """The overlay's factor is sigma/(sigma+competing) with sigma finite positive
    and competing >= 0, so it lies in (0, 1]. It can never manufacture a
    non-finite value from finite inputs. Attacked over hostile graphs at the
    extremes of the accepted domain."""
    section("N-7d the overlay never emits a non-finite value from finite inputs")
    bad = []
    for gseed in range(30):
        store, ids = hostile_graph(gseed)
        for seed_node in ids[:3]:
            for sg in (5e-324, 1e-300, 1e-6, 1.0, 1e12, 1e308):
                try:
                    r = spread_activation(store, seed_node, floor=0.0, energy=1e6,
                                          normalization_sigma=sg)
                except ValueError:
                    bad.append((gseed, sg, "raised on finite inputs"))
                    continue
                for n, v in r.activation.items():
                    if not math.isfinite(v):
                        bad.append((gseed, sg, n, v))
                for rid, v in r.flow.items():
                    if not math.isfinite(v):
                        bad.append((gseed, sg, rid, v))
    check(not bad, f"no non-finite activation or flow anywhere; failures={bad[:3]}")


def test_N7e_competing_is_never_negative_so_the_guard_cannot_be_skipped_wrongly():
    """`if competing > 0.0` is the branch guard. Since fsum is exactly rounded and
    every strength is >= 0, S_out - s is >= 0 always — so the guard can only skip
    normalization when there is genuinely nothing competing. Verified over hostile
    graphs by reconstructing S_out from the reads the engine actually made."""
    section("N-7e competing = S_out - strength is never negative on any reachable "
            "substrate state")
    bad = []
    samples = 0
    for gseed in range(30):
        store, ids = hostile_graph(gseed)
        for node in ids:
            strengths = [store.get_road(r).strength for r in store.roads_from(node)]
            if not strengths:
                continue
            total = math.fsum(strengths)
            for st in strengths:
                samples += 1
                if total - st < 0.0:
                    bad.append((gseed, node, st, total))
                if len(strengths) == 1 and total - st != 0.0:
                    bad.append((gseed, node, "lone road residue", total - st))
    check(not bad, f"{samples} (node, road) pairs: competing >= 0 always, and "
                   f"exactly 0 for a lone road; failures={bad[:3]}")


# ═════════════════════════════════════════════════════════════════════════════
# N-8  CLOSED ROADS COMPETE
# ═════════════════════════════════════════════════════════════════════════════

def _closed_pair():
    """One open road and one CLOSED road out of the same source. The closed road
    is closed by traverse() with a dread charge — the substrate's own route to
    closure, never by hand."""
    s = frozen_store()
    src = s.add_node("src", NodeType.CONCEPT)
    open_t = s.add_node("open", NodeType.CONCEPT)
    shut_t = s.add_node("shut", NodeType.CONCEPT)
    worn(s, src, open_t, n=3)
    worn(s, src, shut_t, n=6, charge={"dread": -0.95})
    shut_road = s.get_road(s.find_road(src, shut_t))
    return s, src, open_t, shut_t, shut_road


def test_N8a_a_BLOCKED_closed_road_still_consumes_budget():
    section("N-8a the sharpest case: a closed road BELOW the breakthrough threshold "
            "transmits nothing, is absent from flow, and still attenuates its sibling")
    s, src, open_t, shut_t, shut_road = _closed_pair()
    check(shut_road.closed, "the dread-charged road really is closed")
    energy = 0.4                                  # below CLOSED_BREAKTHROUGH_THRESHOLD
    r = spread_activation(s, src, energy=energy, floor=0.0, normalization_sigma=1.0)
    check(s.find_road(src, shut_t) not in r.flow,
          "the blocked closed road transmitted nothing (absent from flow)")
    check(shut_t not in r.activation, "and its target was never reached")
    s_open = s.get_road(s.find_road(src, open_t)).strength
    s_shut = shut_road.strength
    want = energy * s_open * DEFAULT_DECAY_PER_HOP * (1.0 / (1.0 + s_shut))
    check(bits(r.activation[open_t]) == bits(want),
          f"the open road is attenuated by the closed road's conductance exactly: "
          f"{r.activation[open_t]!r} == {want!r}")
    excluded = energy * s_open * DEFAULT_DECAY_PER_HOP
    check(bits(want) != bits(excluded),
          f"and the EXCLUDED alternative (closed roads not counted in S_out) would "
          f"have given {excluded!r} — the decision is asserted, not assumed")


def test_N8b_a_LEAKING_closed_road_is_normalized_like_any_other():
    section("N-8b a closed road that breaks through is normalized like any other")
    s, src, open_t, shut_t, shut_road = _closed_pair()
    energy = 0.9                                  # above the breakthrough threshold
    r = spread_activation(s, src, energy=energy, floor=0.0, normalization_sigma=1.0)
    rid_shut = s.find_road(src, shut_t)
    check(rid_shut in r.broke_through, "breakthrough is recorded")
    check(rid_shut in r.flow, "and the leaking road is in flow")
    s_open = s.get_road(s.find_road(src, open_t)).strength
    s_shut = shut_road.strength
    want_shut = (energy * CLOSED_LEAK_FRACTION * s_shut * DEFAULT_DECAY_PER_HOP
                 * (1.0 / (1.0 + s_open)))
    check(bits(r.flow[rid_shut]) == bits(want_shut),
          f"the leaked transmission is normalized by the sibling's conductance "
          f"exactly: {r.flow[rid_shut]!r} == {want_shut!r}")
    want_open = energy * s_open * DEFAULT_DECAY_PER_HOP * (1.0 / (1.0 + s_shut))
    check(bits(r.flow[s.find_road(src, open_t)]) == bits(want_open),
          "and the open road is normalized by the closed road's conductance")


def test_N8c_the_breakthrough_boundary_resolves_as_documented_with_sigma_on():
    """`incoming <= CLOSED_BREAKTHROUGH_THRESHOLD` blocks. Constructed at the exact
    boundary and at both ULP-adjacent values, with the overlay on and off — the
    overlay must not move the boundary."""
    section("N-8c closed-road breakthrough at the EXACT boundary: <= blocks, and the "
            "overlay does not move it")
    s, src, open_t, shut_t, shut_road = _closed_pair()
    rid = s.find_road(src, shut_t)
    thr = CLOSED_BREAKTHROUGH_THRESHOLD
    cases = [(math.nextafter(thr, -math.inf), False),
             (thr, False),
             (math.nextafter(thr, math.inf), True)]
    for energy, should_break in cases:
        for sg in (None, 1.0):
            r = spread_activation(s, src, energy=energy, floor=0.0,
                                  normalization_sigma=sg)
            broke = rid in r.broke_through
            check(broke == should_break,
                  f"energy={energy!r} sigma={sg!r}: broke_through={broke}, "
                  f"expected {should_break}")


def test_N8d_broke_through_can_still_list_a_road_absent_from_flow():
    """A recorded limitation, asserted so it cannot be silently claimed fixed:
    `broke_through` is appended BEFORE the floor guard. Any consumer reading it as
    'intrusive recall happened' over-reports. Pre-existing; the overlay widens it."""
    section("N-8d recorded wart: broke_through can list a road absent from flow "
            "(appended before the floor guard)")
    s, src, open_t, shut_t, shut_road = _closed_pair()
    rid = s.find_road(src, shut_t)
    r = spread_activation(s, src, energy=0.9, floor=1e9, normalization_sigma=1.0)
    check(rid in r.broke_through, "the breakthrough is recorded")
    check(rid not in r.flow, "while the road is absent from flow (floor rejected it)")
    check(shut_t not in r.activation, "and its target was never reached")
    note("N-8d asserts a KNOWN LIMITATION, not a desired behaviour. It turns red if "
         "the ordering is ever changed, which is the point.")


def test_N8e_a_source_whose_only_roads_are_closed_and_blocked():
    section("N-8e a source with only blocked closed roads: nothing transmits, "
            "nothing raises, the seed still stands")
    s = frozen_store()
    src = s.add_node("src", NodeType.CONCEPT)
    for i in range(4):
        t = s.add_node("t%d" % i, NodeType.CONCEPT)
        worn(s, src, t, n=5, charge={"dread": -0.95})
    for sg in (None, 1.0):
        r = spread_activation(s, src, energy=0.2, floor=0.0, normalization_sigma=sg)
        check(r.flow == {}, f"sigma={sg!r}: flow is empty")
        check(list(r.activation) == [src], f"sigma={sg!r}: only the seed is present")
        check(r.broke_through == [], f"sigma={sg!r}: no breakthrough recorded")


# ═════════════════════════════════════════════════════════════════════════════
# N-9  NO SILENT SILENCING
# ═════════════════════════════════════════════════════════════════════════════

def test_N9a_out_degree_200_goes_observably_empty():
    section("N-9a a source at out-degree 200 with sigma=1.0 and the default floor "
            "goes OBSERVABLY empty — not quietly truncated")
    s, hub, tg = star(200)
    before = substrate_snapshot(s)
    r = spread_activation(s, hub, normalization_sigma=1.0)
    check(list(r.activation) == [hub],
          f"activation is exactly {{seed: energy}} ({len(r.activation)} entries)")
    check(bits(r.activation[hub]) == bits(DEFAULT_SEED_ENERGY),
          "the seed still carries its energy")
    check(r.flow == {}, "flow is empty")
    check(r.hops == {hub: 0}, f"hops is {{seed: 0}} (got {r.hops})")
    check(r.ranked() == [], "ranked() is empty")
    check(r.broke_through == [], "no breakthrough recorded")
    check(substrate_snapshot(s) == before, "the substrate is byte-identical")
    s.check_integrity()
    check(True, "check_integrity() passes after the silenced spread")


def test_N9b_the_silencing_is_attributable_not_hidden():
    section("N-9b the same graph is NOT silent unnormalized, and NOT silent at "
            "floor=0.0 — so the horizon change is visible as a DIFFERENCE")
    s, hub, tg = star(200)
    off = spread_activation(s, hub)
    check(len(off.activation) == 201,
          f"unnormalized, all 200 targets are reached ({len(off.activation) - 1})")
    zero_floor = spread_activation(s, hub, floor=0.0, normalization_sigma=1.0)
    check(len(zero_floor.activation) == 201,
          f"normalized with floor=0.0, all 200 are reached "
          f"({len(zero_floor.activation) - 1}) — the FLOOR is the cause, not the "
          f"overlay silently dropping work")
    big_sigma = spread_activation(s, hub, normalization_sigma=1e300)
    check(sig_of(big_sigma) == sig_of(off),
          "and at sigma=1e300 the unnormalized result returns exactly")


def test_N9c_the_horizon_cliffs_rather_than_tapers():
    section("N-9c the horizon on equal-strength fans is a CLIFF, not a taper "
            "(equal roads cross the floor together)")
    obs = []
    for k in (1, 2, 4, 8, 16, 24, 32, 64, 128, 200):
        s, hub, tg = star(k)
        r = spread_activation(s, hub, normalization_sigma=1.0)
        obs.append((k, len(r.activation) - 1))
    print("  (out_degree, reached) =", " ".join(f"({a},{b})" for a, b in obs))
    survived = [k for k, n in obs if n > 0]
    died = [k for k, n in obs if n == 0]
    check(survived and died,
          f"the horizon closes somewhere in the swept range "
          f"(survived up to {max(survived)}, empty from {min(died)})")
    check(max(survived) < min(died),
          "the transition is monotone: no out-degree above the cliff survives")
    partial = [(k, n) for k, n in obs if 0 < n < k]
    check(not partial,
          f"and it is a CLIFF, not a taper: no out-degree reaches only SOME of its "
          f"targets (partial={partial})")
    note(f"measured cliff: every target survives to out-degree {max(survived)}, "
         f"none from {min(died)}. Any floor design in a later brick must reckon "
         f"with a step, not a slope. This is a mechanism observation only.")


def test_N9e_partial_silencing_is_exactly_the_documented_rule_not_arbitrary():
    """N-9 is about silencing being OBSERVABLE. The all-or-nothing case (N-9a/c)
    is the easy one. The hard one is a fan of UNEQUAL strengths, where some roads
    survive and some do not — there, "observable" has to mean the surviving set is
    exactly the set the documented formula predicts, with nothing dropped for any
    other reason."""
    section("N-9e on an UNEQUAL-strength fan the silencing is partial, and the "
            "survivors are exactly those the §2 formula puts at or above the floor")
    rng = random.Random(606)
    partial_trials = 0
    for trial in range(6):
        k = rng.randint(20, 40)
        counts = [rng.randint(1, 15) for _ in range(k)]
        s, hub, tg = star(k, counts=counts)
        strengths = {t: s.get_road(s.find_road(hub, t)).strength for t in tg}
        total = math.fsum(strengths.values())
        sigma = 1.0
        r = spread_activation(s, hub, normalization_sigma=sigma)
        predicted = set()
        for t in tg:
            v = DEFAULT_SEED_ENERGY * strengths[t] * DEFAULT_DECAY_PER_HOP
            comp = total - strengths[t]
            if comp > 0.0:
                v *= sigma / (sigma + comp)
            if not (v < DEFAULT_FLOOR):
                predicted.add(t)
        actual = set(r.activation) - {hub}
        check(actual == predicted,
              f"trial {trial} (out-degree {k}): survivors match the formula exactly "
              f"(predicted {len(predicted)}, actual {len(actual)}, "
              f"symmetric difference {len(actual ^ predicted)})")
        if 0 < len(predicted) < k:
            partial_trials += 1
        print(f"    trial {trial}: out-degree {k}, survivors {len(actual)}/{k}")
    check(partial_trials >= 4,
          f"the PARTIAL case — some roads survive and some do not — is genuinely "
          f"exercised in {partial_trials}/6 trials. Without this the test would be "
          f"re-running the all-or-nothing cliff under another name.")


def test_N9d_silencing_raises_nothing_across_hostile_graphs():
    section("N-9d silencing never raises and never leaves a partial result")
    bad = []
    for gseed in range(25):
        store, ids = hostile_graph(gseed)
        for seed_node in ids[:3]:
            for sg in (1e-9, 1e-3, 1.0):
                try:
                    r = spread_activation(store, seed_node, normalization_sigma=sg)
                except Exception as exc:                   # noqa: BLE001
                    bad.append((gseed, sg, type(exc).__name__, str(exc)[:100]))
                    continue
                if seed_node not in r.activation:
                    bad.append((gseed, sg, "seed missing from activation"))
                for rid in r.flow:
                    tgt = store.get_road(rid, apply_decay=False).target_id
                    if tgt not in r.activation:
                        bad.append((gseed, sg, "flow to an unrecorded node"))
                for n in r.activation:
                    if n not in r.hops:
                        bad.append((gseed, sg, "activation without a settle hop"))
    check(not bad, f"no exception and no partial result on 25 hostile graphs; "
                   f"failures={bad[:3]}")

    # A SELF-LOOP on the seed is the one shape where flow is non-empty while no NEW
    # node was reached: the road transmits back into the seed's own accumulation.
    # An earlier draft of this test called that a partial result. It is not — it is
    # the documented convergence rule, and asserting it positively is worth more
    # than removing the wrong assertion silently.
    loop = frozen_store()
    solo = loop.add_node("solo", NodeType.CONCEPT)
    worn(loop, solo, solo, n=5)
    st = loop.get_road(loop.find_road(solo, solo)).strength
    for sg in (None, 1.0):
        r = spread_activation(loop, solo, floor=0.0, normalization_sigma=sg)
        check(len(r.flow) == 1 and set(r.activation) == {solo},
              f"sigma={sg!r}: a seed self-loop yields flow with no NEW node reached")
        want = math.fsum([DEFAULT_SEED_ENERGY,
                          DEFAULT_SEED_ENERGY * st * DEFAULT_DECAY_PER_HOP])
        check(bits(r.activation[solo]) == bits(want),
              f"sigma={sg!r}: and the seed's own activation is energy + the "
              f"looped-back transmission, exactly ({r.activation[solo]!r})")
        check(r.hops == {solo: 0},
              f"sigma={sg!r}: the seed does not re-settle at a later hop")


# ═════════════════════════════════════════════════════════════════════════════
# BOUNDARY AND STRUCTURE — things the spec's nine invariants do not enumerate
# but which decide whether they mean anything.
# ═════════════════════════════════════════════════════════════════════════════

def test_B1_the_floor_comparison_resolves_as_documented_at_its_exact_boundary():
    """`transmitted < floor` skips. At transmitted == floor the value PROPAGATES,
    which is what "below this, activation is not propagated" says. Constructed at
    the exact boundary and both ULP neighbours, overlay on and off."""
    section("B-1 the floor guard at its EXACT boundary: transmitted == floor "
            "propagates; one ULP below does not")
    s, hub, tg = star(1)
    exact = spread_activation(s, hub).activation[tg[0]]
    for sg in (None, 1.0, 1e300):
        r_eq = spread_activation(s, hub, floor=exact, normalization_sigma=sg)
        r_up = spread_activation(s, hub, floor=math.nextafter(exact, math.inf),
                                 normalization_sigma=sg)
        r_dn = spread_activation(s, hub, floor=math.nextafter(exact, -math.inf),
                                 normalization_sigma=sg)
        check(tg[0] in r_eq.activation,
              f"sigma={sg!r}: floor == transmitted -> propagates")
        check(tg[0] not in r_up.activation,
              f"sigma={sg!r}: floor one ULP above -> blocked")
        check(tg[0] in r_dn.activation,
              f"sigma={sg!r}: floor one ULP below -> propagates")


def test_B2_degenerate_graphs_and_seeds():
    section("B-2 degenerate inputs: empty graph, single node, isolated seed, "
            "hop_budget 0, unknown seed, road id as seed")
    empty = frozen_store()
    try:
        spread_activation(empty, "nope", normalization_sigma=1.0)
        check(False, "an unknown seed on an empty store raises NotFound")
    except NotFound:
        check(True, "an unknown seed on an empty store raises NotFound")

    solo = frozen_store()
    only = solo.add_node("only", NodeType.CONCEPT)
    for sg in (None, 5e-324, 1.0, 1e300):
        r = spread_activation(solo, only, normalization_sigma=sg)
        check(list(r.activation) == [only] and r.flow == {} and r.hops == {only: 0},
              f"single-node graph, sigma={sg!r}: seed only, nothing else")

    s, hub, tg = star(3)
    r0 = spread_activation(s, hub, hop_budget=0, normalization_sigma=1.0)
    check(list(r0.activation) == [hub] and r0.flow == {},
          "hop_budget=0 settles the seed and expands nothing")
    check(sig_of(r0) == sig_of(spread_activation(s, hub, hop_budget=0)),
          "and it is byte-identical to the unnormalized run")

    # A ROAD id passed as the seed. `store.exists()` is true for road ids as well as
    # node ids, so the boundary check does not discriminate. Recorded exactly as
    # measured, because "either outcome is fine" is not a test.
    rid = s.find_road(hub, tg[0])
    check(s.exists(rid), "store.exists() is true for a ROAD id, so the seed guard "
                         "does not discriminate node from road")
    try:
        spread_activation(s, rid, normalization_sigma=1.0)
        check(False, "a road id as seed at the default hop budget raises NotFound")
    except NotFound:
        check(True, "a road id as seed raises NotFound — but from INSIDE the "
                    "expansion (roads_from), not at the boundary")
    degenerate = spread_activation(s, rid, hop_budget=0, normalization_sigma=1.0)
    check(list(degenerate.activation) == [rid]
          and bits(degenerate.activation[rid]) == bits(DEFAULT_SEED_ENERGY),
          "and at hop_budget=0 it returns a well-formed result seeded on a ROAD, "
          "with no error at all")
    pre = pre_overlay_engine()
    if pre is not None:
        old = pre.spread_activation(s, rid, hop_budget=0)
        check(list(old.activation) == [rid],
              "PRE-EXISTING: the pre-overlay engine does the same, so this is 0a/0b's "
              "seed guard, not the 0b2 overlay's")
    else:
        check(True, "(placeholder so the assertion count does not depend on git)")
    note("OUT OF SCOPE OBSERVATION for architect-pm, not a 0b2 defect and not one of "
         "N-1..N-9: spread_activation's seed guard is `store.exists(seed_node)`, which "
         "is true for ROAD ids. At hop_budget=0 a road id therefore yields a "
         "well-formed ActivationResult with no error; at any larger budget it raises "
         "NotFound from inside the expansion rather than at the boundary. Same class "
         "as O-12 and DEFECT-C (silent acceptance where a loud refusal was intended), "
         "pre-existing, unreachable from any internal caller. Registering it is "
         "architect-pm's call.")

    # duplicate pair: the store dedups, so out-degree is 1 and N-5 applies
    dup = frozen_store()
    a = dup.add_node("a", NodeType.CONCEPT)
    b = dup.add_node("b", NodeType.CONCEPT)
    for _ in range(8):
        dup.traverse(a, b)
    check(len(list(dup.roads_from(a))) == 1,
          "duplicate traversals of the same pair produce ONE road")
    check(sig_of(spread_activation(dup, a, normalization_sigma=1.0))
          == sig_of(spread_activation(dup, a)),
          "so the deduped pair is a lone out-road and is unattenuated")


def test_B3_a_never_worn_road_contributes_its_default_conductance():
    """`add_road` without `strengthen` leaves strength at the dirt-track default.
    Deliberately the one fixture built without traverse(), because a road that
    exists but was never crossed is a reachable substrate state and it still
    competes."""
    section("B-3 a never-worn road (add_road only) still competes for budget")
    s = frozen_store()
    src = s.add_node("src", NodeType.CONCEPT)
    strong = s.add_node("strong", NodeType.CONCEPT)
    faint = s.add_node("faint", NodeType.CONCEPT)
    worn(s, src, strong, n=6)
    rid_faint = s.add_road(src, faint)                     # never strengthened
    s_strong = s.get_road(s.find_road(src, strong)).strength
    s_faint = s.get_road(rid_faint).strength
    check(s_faint > 0.0, f"the never-worn road has a positive conductance "
                         f"({s_faint!r})")
    r = spread_activation(s, src, floor=0.0, normalization_sigma=1.0)
    want = DEFAULT_SEED_ENERGY * s_strong * DEFAULT_DECAY_PER_HOP * \
        (1.0 / (1.0 + s_faint))
    check(bits(r.activation[strong]) == bits(want),
          f"and it attenuates its sibling exactly: {r.activation[strong]!r} "
          f"== {want!r}")


def test_S1_the_overlay_is_still_not_plumbed_past_spread_activation():
    """SPEC-0b2 §6.10. This BOUNDS the blast radius: no downstream consumer can
    enable normalization today, so the default-off claim is structural and not
    merely a default value. It also means the §5 default flip needs plumbing
    first — a re-validation surface for 1a/1b/1c/1d."""
    section("S-1 structural: build_activation_field() and think() still expose no "
            "normalization_sigma")
    from psyche_field import build_activation_field
    from psyche_perceive import think
    for fn in (build_activation_field, think):
        params = inspect.signature(fn).parameters
        check("normalization_sigma" not in params,
              f"{fn.__name__}() has no normalization_sigma parameter "
              f"(params={list(params)})")
    src_text = open(os.path.join(SRC, "psyche_field.py"), encoding="utf-8").read()
    check("normalization_sigma" not in src_text,
          "and psyche_field.py never mentions it, so the field builder cannot pass "
          "it through positionally either")
    note("The default flip therefore requires plumbing the parameter through the "
         "field builder first. That is a separate brick and is Cagan's call; "
         "nothing here tests as though it were decided.")


def test_S2_the_documented_transmission_formula_holds_on_a_high_degree_fan():
    section("S-2 the §2 transmission rule reproduces every transmitted value on a "
            "128-way fan, at four sigmas")
    rng = random.Random(20260726)
    counts = [rng.randint(1, 14) for _ in range(128)]
    s, hub, tg = star(128, counts=counts)
    strengths = {t: s.get_road(s.find_road(hub, t)).strength for t in tg}
    total = math.fsum(strengths.values())
    for sg in (0.5, 1.0, 25.0, 1e12):
        r = spread_activation(s, hub, floor=0.0, normalization_sigma=sg)
        bad = []
        for t in tg:
            rid = s.find_road(hub, t)
            st = strengths[t]
            want = DEFAULT_SEED_ENERGY * st * DEFAULT_DECAY_PER_HOP
            comp = total - st
            if comp > 0.0:
                want *= sg / (sg + comp)
            if bits(r.flow[rid]) != bits(want):
                bad.append((t, r.flow[rid], want))
        check(not bad, f"sigma={sg!r}: all 128 transmitted values match the "
                       f"documented formula to the bit; failures={bad[:2]}")


# ═════════════════════════════════════════════════════════════════════════════

TESTS = [
    test_P0_the_live_clock_has_a_noise_floor_larger_than_the_effect,
    test_N1a_explicit_none_equals_the_omitted_parameter,
    test_N1b_neutral_matches_the_actual_pre_overlay_engine_from_git,
    test_N1i_every_divergence_from_the_pre_overlay_engine_is_owned_by_0c,
    test_N1c_neutral_matches_the_independent_oracle_everywhere,
    test_N1d_the_oracle_catches_every_deliberate_mutation,
    test_N1e_loop_closed_on_a_substrate_the_system_itself_built,
    test_N1f_the_field_builder_consumes_the_neutral_path_unchanged,
    test_N1g_the_parameter_is_keyword_only_and_defaults_to_None,
    test_N1h_the_neutral_path_does_not_change_the_store_read_pattern,
    test_N2a_bit_exact_across_hash_seeds_and_every_cpython_on_this_machine,
    test_N2b_order_independence_not_merely_order_pinning,
    test_N2c_repeated_runs_in_one_process_are_bit_identical,
    test_N3a_substrate_is_byte_identical_after_normalized_spreads,
    test_N3b_no_mutating_store_method_is_ever_called,
    test_N3c_lazy_decay_is_never_persisted_even_on_a_moving_clock,
    test_N3d_integrity_survives_a_randomized_mutation_battery,
    test_N4a_the_probe_is_sensitive_to_the_bug_it_claims_to_catch,
    test_N4b_S_out_equals_fsum_and_not_the_left_fold,
    test_N4c_S_out_is_order_independent_on_high_degree_fans,
    test_N5a_lone_out_road_is_byte_identical_at_every_sigma_frozen_clock,
    test_N5b_the_negative_control_a_second_road_DOES_attenuate,
    test_N5c_lone_out_road_factor_is_exactly_one_on_a_MOVING_clock,
    test_N5d_competing_is_exactly_zero_for_a_lone_road_at_every_worn_strength,
    test_N6a_strictly_decreasing_in_competing_conductance,
    test_N6b_increasing_in_sigma_and_the_exact_point_where_strictness_ends,
    test_N6c_normalized_never_exceeds_unnormalized_property_based,
    test_N7a_gap_to_the_unnormalized_engine_is_monotone_non_increasing,
    test_N7b_large_finite_sigma_recovers_the_unnormalized_engine_byte_for_byte,
    test_N7c_sigmas_domain_is_validated_at_the_boundary,
    test_N7d_no_reachable_input_makes_the_overlay_emit_a_non_finite_value,
    test_N7e_competing_is_never_negative_so_the_guard_cannot_be_skipped_wrongly,
    test_N8a_a_BLOCKED_closed_road_still_consumes_budget,
    test_N8b_a_LEAKING_closed_road_is_normalized_like_any_other,
    test_N8c_the_breakthrough_boundary_resolves_as_documented_with_sigma_on,
    test_N8d_broke_through_can_still_list_a_road_absent_from_flow,
    test_N8e_a_source_whose_only_roads_are_closed_and_blocked,
    test_N9a_out_degree_200_goes_observably_empty,
    test_N9b_the_silencing_is_attributable_not_hidden,
    test_N9c_the_horizon_cliffs_rather_than_tapers,
    test_N9e_partial_silencing_is_exactly_the_documented_rule_not_arbitrary,
    test_N9d_silencing_raises_nothing_across_hostile_graphs,
    test_B1_the_floor_comparison_resolves_as_documented_at_its_exact_boundary,
    test_B2_degenerate_graphs_and_seeds,
    test_B3_a_never_worn_road_contributes_its_default_conductance,
    test_S1_the_overlay_is_still_not_plumbed_past_spread_activation,
    test_S2_the_documented_transmission_formula_holds_on_a_high_degree_fan,
]


def run_all():
    print("=" * 74)
    print("  TESTER — SPEC-0b2 §6 RE-ADJUDICATION (N-1 … N-9), independent second pass")
    print("  src/ untouched. Mechanism only; no cognitive claim is made or approached.")
    print("=" * 74)
    for t in TESTS:
        t()
    print("\n" + "=" * 74)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    if _fail_msgs:
        print("  FAILURES:")
        for m in _fail_msgs:
            print("   -", m)
    if _notes:
        print("  NOTES CARRIED TO THE REPORT:")
        for m in _notes:
            print("   -", m)
    print("=" * 74)
    verdict = "all nine hold" if _failed == 0 else "SEE FAILURES ABOVE"
    print(f"  TESTER VERDICT ON SPEC-0b2 §6, SECOND INDEPENDENT PASS: {verdict}")
    print("=" * 74)
    print("    N-1 neutral byte-identity ....... omitted == None over the whole")
    print("        parameter surface, exception path included; every divergence from")
    print("        the git-recovered pre-overlay engine classified and shown to be")
    print("        0c-owned (N-1i); oracle proven to discriminate at 1 ULP (N-1d);")
    print("        loop-closed through perceive() and build_activation_field().")
    print("    N-2 determinism ................. one SHA-256 across fresh processes,")
    print("        6 hash seeds x every CPython minor version present, on a graph with")
    print("        three or more convergent contributions; and order-INDEPENDENT under")
    print("        externally permuted out-road iteration, proven non-vacuous.")
    print("    N-3 purity ...................... byte-identical substrate, structural")
    print("        write-trap, and last_touched unchanged on a MOVING clock.")
    print("    N-4 S_out order-independence .... equals math.fsum and NOT the left")
    print("        fold, on a fixture searched to make the two differ.")
    print("    N-5 lone out-road ............... exactly 1.0 on a frozen clock at ten")
    print("        sigmas, and as a WITHIN-CALL identity on a clock that advances.")
    print("    N-6 monotonicity ................ strict in competing; strict in sigma")
    print("        until saturation, non-decreasing across 80 ULP-adjacent sigmas.")
    print("    N-7 sigma -> infinity ........... monotone convergence, 1e100/1e300")
    print("        byte-identical to None, and the domain refused at the boundary.")
    print("    N-8 closed roads compete ........ exact arithmetic, the excluded")
    print("        alternative asserted, breakthrough pinned at its exact boundary.")
    print("    N-9 no silent silencing ......... observable at out-degree 200, a CLIFF")
    print("        on equal fans, and exactly the documented survivors on unequal ones.")
    print()
    print("  Mechanism only. No cognitive claim is made, implied or approached.")
    print("  0b2 remains BUILT-UNVALIDATED whatever this file reports; a pass here")
    print("  closes the MECHANISM bar and nothing else.")
    print("=" * 74)
    return _failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run_all() else 1)
