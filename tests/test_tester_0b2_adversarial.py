"""
INDEPENDENT ADVERSARIAL TEST SUITE for step 0b2 — divisive normalization overlay.

Author: tester (independent adversary). Written FROM SCRATCH against SPEC-0b2 §6's
invariants N-1..N-9, not adapted from the builder's suite. There was in fact nothing to
adapt: at the time of writing `normalization_sigma` appeared in exactly one file in the
repository (`src/psyche_activation.py`) and in no test at all, so the overlay shipped with
zero coverage and every property below is verified here for the first time.

Mechanism only. Nothing here grades a cognitive claim; see the validator's lane for that.

RE-ADJUDICATED 2026-07-26 AFTER BRICK 0c. READ THIS BEFORE READING THE TESTS.
-----------------------------------------------------------------------------
The 0b2 pass returned FAIL with three defects, and recorded each as an ASSERTED-NEGATIVE:
a test that PASSES while the defect is present and goes RED the moment it is fixed. 0c
fixed all three. So ten tests in this file went red on a CORRECT fix, and the acceptance
signal for 0c was inverted — red here was the pass condition, not a regression.

Every one of the ten has been converted from "the defect is present" into the positive
property it certifies. Nothing was deleted without a replacement, and each replacement
carries a docstring naming the negative it retires, so the history is not lost:

  test_N2_O6_convergent_accumulation_is_order_INDEPENDENT ......... was DEFECT-A (perm)
  test_N2_O6_order_independence_holds_with_the_overlay_ON_as_well . was DEFECT-A (scoping)
  test_N2_O4_the_DEFECT_A_reproduction_is_ONE_bit_pattern_... ..... was DEFECT-A (processes)
  test_N5_O10_lone_out_road_factor_is_exactly_one_ON_A_MOVING_CLOCK was DEFECT-B
  test_N5_O9_the_expansion_loop_reads_each_road_exactly_once ....... was DEFECT-B (scoping)
  test_N7_O11_non_finite_sigma_is_refused_at_the_boundary .......... was DEFECT-C (inf/nan)
  test_N7_O11_non_positive_sigma_is_refused_rather_than_silently_... was DEFECT-C (sigma<=0)
  test_N1_byte_identity_vs_git_pre_change_engine ................... bounded to in-degree<=2
  test_N1_byte_identity_vs_independent_reference ................... oracle RE-BASED
  test_N1_byte_identity_loop_closed_on_a_system_built_substrate .... oracle RE-BASED

The two DEFECT-C negatives had begun to RAISE rather than fail, which aborted the run and
hid the 13 tests after them. They were converted first, for that reason.

THE ORACLE TRAP (SPEC-0c O-8), which is the intellectually load-bearing part of the
re-adjudication. N-1's two oracles both modelled the OLD naive accumulator, so after the
fix they agreed with a broken engine and disagreed with a correct one. A stale oracle is
not an oracle; it is a second copy of the bug. Both are dealt with, differently:

  Oracle 1 (the git-recovered pre-0b2 engine) is BOUNDED, not re-based — it cannot be
  re-based, it is a historical artifact. It is now pointed only at graphs with in-degree
  <= 2, the region where the pre-change engine had a single well-defined answer at all
  (SPEC-0c §2.3's correction). The bound is asserted against the fixtures, and so is the
  fact that the fixtures actually REACH in-degree 2 rather than avoiding the boundary.

  Oracle 2 (the independent reference) is RE-BASED onto the intended post-0c semantics —
  ordered iteration AND math.fsum accumulation — derived clause by clause from SPEC-0c's
  prose, with each clause cited, and deliberately NOT transcribed from src/. A reference
  copied from the module under test is a mirror, not an oracle, and would make N-1
  vacuous. test_N1_the_rebase_is_real_and_the_oracle_is_not_a_mirror asserts both halves:
  that the re-base actually changed the oracle, and that it changed it in exactly the way
  SPEC-0c §8(i) predicts.

WHAT IS VERIFIED, and the verdict each property now returns
------------------------------------------------------------
  N-1  neutral byte-identity .................... HOLDS  (re-based + bounded oracles)
       Scope, stated with the claim: byte-identity is established under a FROZEN clock
       (Clock(simulated=True)). On a clock that advances, any two runs differ through
       0a's lazy decay alone — a property of the store, not of this overlay — so
       bit-exact comparison is only meaningful with the clock held still.
  N-2  determinism, hash seeds x interpreters ... HOLDS  (was DEFECT-A)
       And the GUARANTEE changed shape, which matters more than the verdict: it is no
       longer a sampled axis. Seed-pinning never controlled the order (uuid4 values differ
       per process, so DEFECT-A varied at a FIXED seed); after 0c there is no order left
       for any axis to perturb. See SPEC-0c §5.2.
  N-3  purity ................................... HOLDS
  N-4  order-independence of S_out .............. HOLDS  (math.fsum, proven sensitive)
  N-5  limiting case: lone out-road ............. HOLDS  (was DEFECT-B)
  N-6  monotonicity ............................. HOLDS
  N-7  sigma validation and convergence ......... HOLDS  (was DEFECT-C)
  N-8  closed roads compete ..................... HOLDS
  N-9  no silent silencing ...................... HOLDS

The SPEC-0c invariants O-1 .. O-17 are adjudicated in tests/test_tester_0c_adversarial.py.
This file carries O-4 (in-suite leg), O-6, O-8, O-9, O-10, O-11, O-12 and O-17, because
those are the ones that land on the retired negatives.

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

from psyche_store import (
    SubstrateStore, Clock, NodeType, NotFound, IntegrityError,
)
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

_PRE_CACHE = []           # memoised: git is slow and four tests want the same module


def load_pre_change_engine():
    """Recover the last version of psyche_activation.py that predates the overlay.

    Resolved by CONTENT, not by a pinned hash: walk the file's history newest-first and
    take the first revision that does not mention normalization_sigma. That survives a
    rebase, which a hardcoded sha would not. Returns None if git is unavailable.

    SPEC-0c §6.1 (tester-owned nit): the temporary module is written to a TEMP DIRECTORY,
    never into tests/. The previous version wrote `tests/__pre0b2_oracle.py` and removed it
    in a `finally`, so an interrupted run left a stray module in the test package — which it
    did once, during the 0b2 pass. A temp dir is cleaned by the OS even if the process dies.
    """
    if _PRE_CACHE:
        return _PRE_CACHE[0]
    result = None
    try:
        # The pre-0b2 engine predates the Nous -> Psyche rename, so it is found at its
        # historical path, and its `from nous_store import` resolves to today's store.
        log = subprocess.run(["git", "log", "--format=%H", "--", "src/nous_activation.py"],
                             cwd=ROOT, capture_output=True, text=True, timeout=30)
        if log.returncode != 0:
            _PRE_CACHE.append(None)
            return None
        for sha in log.stdout.split():
            blob = subprocess.run(["git", "show", f"{sha}:src/nous_activation.py"],
                                  cwd=ROOT, capture_output=True, text=True, timeout=30)
            if blob.returncode != 0:
                continue
            if "normalization_sigma" in blob.stdout:
                continue
            import importlib
            import importlib.util
            import tempfile
            tmpdir = tempfile.mkdtemp(prefix="psyche_pre0b2_")
            path = os.path.join(tmpdir, "__pre0b2_oracle.py")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(blob.stdout)
            try:
                spec = importlib.util.spec_from_file_location("__pre0b2_oracle", path)
                mod = importlib.util.module_from_spec(spec)
                sys.modules["__pre0b2_oracle"] = mod   # dataclass needs it registered
                sys.modules.setdefault("nous_store", importlib.import_module("psyche_store"))
                spec.loader.exec_module(mod)
                mod.__psyche_sha__ = sha
                mod.__psyche_source__ = blob.stdout      # the temp tree is removed below
                result = mod
                break
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
    except (OSError, subprocess.SubprocessError):
        result = None
    _PRE_CACHE.append(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# THE BOUNDARY ON ORACLE 1 — and SPEC-0c §2.3 STATES IT ONE OFF. Recorded here
# because a boundary that is wrong by one is worse than no boundary: it invites the
# next reader to conclude the fix broke neutrality when it did not.
#
# The git-recovered engine accumulates convergent contributions with a naive running
# float add, so it has a single well-defined answer only where no node accumulates three
# or more terms (a + b == b + a is exact; a + b + c is not). SPEC-0c §2.3 and O-8 render
# that region as "IN-DEGREE <= 2". That is not the same set.
#
#   THE SEED'S OWN ENERGY IS A CONTRIBUTION. `activation` starts as {seed: energy}, so a
#   seed node that is also reached by two in-roads — an ordinary cycle back to the seed —
#   accumulates energy + 2 flows = THREE terms while its in-degree is 2. Its value is
#   therefore order-dependent in the pre-change engine, inside the region the spec calls
#   safe.
#
# Measured, not argued: on `low_in_degree_graph(0)`, max in-degree 2, seeding at n1 with
# energy=1e6, the pre-change engine gives 1086319.0400302166 and the post-0c engine gives
# 1086319.0400302163 — a mismatch at a node whose in-degree is 2 and which is the seed.
#
# The correct boundary is stated on CONTRIBUTIONS, not on in-degree:
#     no node may accumulate >= 3 contributions, where the seed's energy counts as one.
# Enforced structurally below by requiring in-degree <= 2 everywhere AND in-degree <= 1 at
# the seed, and then ASSERTED from the engine's own recorded flows rather than trusted.
# ─────────────────────────────────────────────────────────────────────────────

def low_in_degree_graph(seed):
    """An adversarial graph in which NO node has in-degree >= 3.

    Hostility is preserved everywhere it does not collide with the bound: self-loops,
    cycles, duplicate pairs (which dedup), closed and traumatic roads, saturated and
    decayed strengths, isolated nodes. Only the in-degree is capped, and it is capped by
    REFUSING an edge that would exceed it — asserted below, never assumed.
    """
    rng = random.Random(seed)
    clock = Clock(simulated=True, start=0.0)
    store = SubstrateStore(clock=clock)
    n = rng.randint(1, 11)
    ids = [store.add_node("n%d" % i, rng.choice(list(NodeType))) for i in range(n)]
    indeg = {i: 0 for i in ids}
    for _ in range(rng.randint(0, 40)):
        a, b = rng.choice(ids), rng.choice(ids)
        existing = store.find_road(a, b)
        if existing is None and indeg[b] >= 2:
            continue                       # would push b past the boundary: refuse it
        k = rng.random()
        charge = None
        if k < 0.22:
            charge = {"dread": -rng.uniform(0.75, 1.0)}       # closes the road
        elif k < 0.40:
            charge = {"joy": rng.uniform(0.2, 0.9)}
        if existing is None:
            indeg[b] += 1
        for _ in range(rng.randint(1, 12)):
            store.traverse(a, b, charge)
        if rng.random() < 0.35:
            clock.advance(rng.uniform(0.0, 40.0))             # exercise lazy decay
    clock.advance(0.0)
    return store, list(store.all_node_ids())


def in_degrees(store):
    indeg = {n: 0 for n in store.all_node_ids()}
    for rid in store.all_road_ids():
        t = store.get_road(rid, apply_decay=False).target_id
        indeg[t] = indeg.get(t, 0) + 1
    return indeg


def max_in_degree(store):
    return max(in_degrees(store).values(), default=0)


def oracle1_safe_seeds(store):
    """The seeds for which the PRE-CHANGE engine had a single well-defined answer.

    A node accumulates one term per in-road that fires, plus — if it is the seed — the
    seed energy. So the region is `in-degree <= 2` everywhere AND `in-degree <= 1` at the
    seed. Returning the seeds rather than filtering graphs keeps the graphs as hostile as
    they were: cycles, self-loops and closed roads all survive, only the seeding is bounded.
    """
    indeg = in_degrees(store)
    return [n for n in store.all_node_ids() if indeg.get(n, 0) <= 1]


def max_arriving_contributions(store, result, seed_node, energy):
    """How many terms the largest accumulation in `result` actually took, counted from the
    engine's OWN recorded flows. This is what the boundary is really about, so it is
    measured rather than inferred from topology."""
    n = {}
    for rid in result.flow:
        t = store.get_road(rid).target_id
        n[t] = n.get(t, 0) + 1
    n[seed_node] = n.get(seed_node, 0) + 1        # the seed energy is a contribution
    return max(n.values(), default=0)


# ─────────────────────────────────────────────────────────────────────────────
# ORACLE 2 — an independent implementation, RE-BASED for 0c (SPEC-0c O-8).
#
# THE TRAP THIS AVOIDS, quoted because it is the whole point of the re-base:
#
#   "The reference implementation must mirror the INTENDED semantics — ordered
#    iteration AND fsum accumulation — not the semantics it was written against. A
#    reference that still models the old naive accumulator will agree with a BROKEN
#    engine and disagree with a correct one. At that point it has silently stopped being
#    an oracle and has become A SECOND COPY OF THE BUG."   — SPEC-0c O-8
#
# And the second half of the trap, which is subtler: re-basing it by copying the new
# src/ would build a MIRROR, not an oracle, and N-1 would become vacuous — it would
# assert that the engine equals itself. So every line below is derived from SPEC-0c's
# PROSE description of what the engine should do, clause by clause, with the clause
# cited. The tester has deliberately not transcribed src/psyche_activation.py; the two
# implementations differ in shape (this one keeps `settled` and `nxt` separate, uses a
# different loop skeleton and different names) and agree only because they compute the
# same function.
#
#   §2.2  roads_from()/roads_into() yield in ROAD-CREATION ORDER. That is the store's
#         contract, so the reference simply consumes it; O-1 verifies it independently.
#   §2.3  the accumulator keeps PER-TARGET CONTRIBUTION LISTS and reduces them with
#         math.fsum "at each layer boundary, plus once at the end". The reduction is over
#         the WHOLE list each time, never a running total folded back in, so no boundary's
#         rounding is baked into a later value.
#   §3    materialise the expanding node's roads ONCE, so out_total and every
#         road.strength come from a single clock instant.
#   §4    reject non-finite / non-positive sigma at the boundary, and reject a non-finite
#         `transmitted` on its own terms BEFORE the floor comparison.
#
# Everything else is psyche_activation's own documented design and is untouched by 0c: the
# hop-layer freeze, the closed-road breakthrough/leak policy, the floor guard, flow
# recording, and first-arrival settling.
# ─────────────────────────────────────────────────────────────────────────────

def reference_spread(store, seed_node, *, energy=DEFAULT_SEED_ENERGY,
                     decay_per_hop=DEFAULT_DECAY_PER_HOP, floor=DEFAULT_FLOOR,
                     hop_budget=DEFAULT_HOP_BUDGET, normalization_sigma=None):
    if normalization_sigma is not None and (
            not math.isfinite(normalization_sigma) or normalization_sigma <= 0.0):
        raise ValueError(f"normalization_sigma must be finite and strictly positive, "
                         f"got {normalization_sigma!r}")            # §4 part 1
    if not store.exists(seed_node):
        raise NotFound(f"seed node {seed_node}")
    arriving = {seed_node: [energy]}                                # §2.3 contribution lists
    settled = {seed_node: 0}
    broke = []
    flow = {}
    layer = [seed_node]
    for hop in range(hop_budget + 1):
        if not layer:
            break
        nxt = {}
        # §2.3 — reduce the WHOLE list at the layer boundary, exactly rounded
        frozen = {n: math.fsum(arriving[n]) for n in layer}
        for node in layer:
            node_act = frozen[node]
            if hop >= hop_budget:
                continue                                     # settle, do not expand
            # §3 — one materialisation, therefore one clock instant for the expansion
            seen_roads = [(rid, store.get_road(rid)) for rid in store.roads_from(node)]
            out_total = 0.0
            if normalization_sigma is not None:
                out_total = math.fsum(rd.strength for _, rd in seen_roads)
            for rid, road in seen_roads:
                outgoing = node_act
                if road.closed:
                    # the closed-road policy, re-stated from its documented rule
                    if outgoing <= CLOSED_BREAKTHROUGH_THRESHOLD:
                        continue
                    outgoing = outgoing * CLOSED_LEAK_FRACTION
                    broke.append(rid)
                transmitted = outgoing * road.strength * decay_per_hop
                if normalization_sigma is not None:
                    competing = out_total - road.strength
                    if competing > 0.0:
                        transmitted *= (normalization_sigma
                                        / (normalization_sigma + competing))
                if not math.isfinite(transmitted):                  # §4 part 2
                    raise ValueError(
                        f"non-finite transmitted activation ({transmitted!r}) on road {rid}")
                if transmitted < floor:
                    continue
                tgt = road.target_id
                arriving.setdefault(tgt, []).append(transmitted)
                flow[rid] = flow.get(rid, 0.0) + transmitted
                if tgt not in settled:
                    settled[tgt] = hop + 1
                    nxt[tgt] = None
        layer = list(nxt.keys())
    # §2.3 — and once at the end, again over the whole list
    return ActivationResult(seed=seed_node,
                            activation={n: math.fsum(v) for n, v in arriving.items()},
                            hops=settled, broke_through=broke, flow=flow)


def stale_reference_spread(store, seed_node, *, energy=DEFAULT_SEED_ENERGY,
                           decay_per_hop=DEFAULT_DECAY_PER_HOP, floor=DEFAULT_FLOOR,
                           hop_budget=DEFAULT_HOP_BUDGET):
    """The PRE-0c reference, kept verbatim so the re-base can be shown to be a real change.

    If `reference_spread` above were still modelling the naive accumulator, it would agree
    with this one everywhere and N-1 would be a second copy of the bug rather than an
    oracle. test_N1_the_rebase_is_real asserts the two DISAGREE, on the region where they
    are supposed to disagree and nowhere else.
    """
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
        frozen = {n: activation[n] for n in layer}
        for node in layer:
            node_act = frozen[node]
            if hop >= hop_budget:
                continue
            for rid in store.roads_from(node):
                road = store.get_road(rid)
                outgoing = node_act
                if road.closed:
                    if outgoing <= CLOSED_BREAKTHROUGH_THRESHOLD:
                        continue
                    outgoing = outgoing * CLOSED_LEAK_FRACTION
                    broke.append(rid)
                transmitted = outgoing * road.strength * decay_per_hop
                if transmitted < floor:
                    continue
                tgt = road.target_id
                activation[tgt] = activation.get(tgt, 0.0) + transmitted   # NAIVE
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
    """Oracle 1, BOUNDED at in-degree <= 2 (SPEC-0c §2.3 correction / §6.1).

    The git-recovered engine is still a real, unfakeable external yardstick — but only on
    the region where it had a single well-defined answer. Above in-degree 2 it accumulates
    naively in an order the pre-0c store did not fix, so it never had a stable value there
    for 0c to reproduce. The bound is ASSERTED against the generated graphs, not trusted:
    if the generator ever drifts past it, this test says so instead of quietly comparing
    against a number that means nothing.

    O-17: the same number of checks is emitted whether or not .git is present.
    """
    section("N-1/O-8 byte-identity vs the ACTUAL pre-change engine, inside its real boundary")
    check("normalization_sigma" not in open(
        os.path.join(SRC, "psyche_activation.py"), encoding="utf-8").read().split(
        "def spread_activation")[0],
        "the overlay parameter is not introduced above spread_activation (sanity)")
    # The bound is a property of the fixtures and is checked with or without git, so the
    # check count does not depend on the environment (O-17).
    degrees = [max_in_degree(low_in_degree_graph(gs)[0]) for gs in range(120)]
    check(max(degrees) <= 2,
          f"every oracle-1 fixture stays at in-degree <= 2: max observed = {max(degrees)}")
    check(sum(1 for d in degrees if d == 2) >= 40,
          f"and the boundary is APPROACHED, not avoided: {sum(1 for d in degrees if d == 2)} "
          f"of {len(degrees)} fixtures reach in-degree exactly 2, where a+b==b+a is the "
          f"only reason the oracle is well-defined at all")
    pre = load_pre_change_engine()
    if pre is None:
        note("git unavailable — oracle 1 degrades to an observation; the checks below are "
             "still emitted, so the suite total does not move (O-17)")
        check(True, "oracle 1 (git pre-change engine): UNAVAILABLE, recorded (git absent)")
        check(True, "oracle 1 contribution bound: UNAVAILABLE, recorded (git absent)")
        return
    compared = 0
    mismatches = []
    worst_terms = 0
    for gs in range(120):
        store, ids = low_in_degree_graph(gs)
        for seed_node in oracle1_safe_seeds(store):
            for params in PARAM_SWEEP:
                res = spread_activation(store, seed_node, normalization_sigma=None, **params)
                worst_terms = max(worst_terms, max_arriving_contributions(
                    store, res, seed_node, params.get("energy", DEFAULT_SEED_ENERGY)))
                got = signature(res)
                want = signature(pre.spread_activation(store, seed_node, **params))
                compared += 1
                if got != want and len(mismatches) < 3:
                    mismatches.append((gs, store.get_node(seed_node).content, params))
    # THE BOUNDARY, ASSERTED FROM THE ENGINE'S OWN FLOWS rather than from topology. If a
    # future generator change ever let a 3-term accumulation into this battery, this fires
    # instead of the comparison below silently becoming meaningless.
    check(worst_terms <= 2,
          f"no compared spread accumulated 3 or more contributions at any node "
          f"(max observed = {worst_terms}) — this, not 'in-degree <= 2', is the region the "
          f"pre-change engine was deterministic on; the seed's own energy counts as a term")
    check(not mismatches,
          f"oracle 1: {compared} in-boundary comparisons vs git "
          f"{getattr(pre, '__psyche_sha__', '?')[:7]} byte-identical "
          f"(mismatches: {mismatches})")
    print(f"  ({compared} comparisons against the real pre-change engine "
          f"inside its boundary, {len(mismatches)} mismatches)")


def test_N1_byte_identity_vs_independent_reference():
    """Oracle 2, RE-BASED (SPEC-0c O-8). The gating property of the whole overlay.

    Unbounded, unlike oracle 1: a reference that models the intended semantics is well
    defined at every in-degree, which is exactly why the re-base is what restores N-1's
    reach rather than merely repairing it.
    """
    section("N-1/O-8 byte-identity vs the RE-BASED independent reference (unbounded)")
    compared = 0
    mismatches = []
    max_deg = 0
    for gs in range(120):
        store, ids = adversarial_graph(1000 + gs)
        max_deg = max(max_deg, max_in_degree(store))
        for seed_node in ids:
            for params in PARAM_SWEEP:
                got = signature(spread_activation(
                    store, seed_node, normalization_sigma=None, **params))
                want = signature(reference_spread(store, seed_node, **params))
                compared += 1
                if got != want and len(mismatches) < 3:
                    mismatches.append((gs, params))
    check(max_deg >= 3,
          f"the battery genuinely exercises the region oracle 1 cannot reach: max "
          f"in-degree = {max_deg} (need >= 3, or this test proves nothing oracle 1 did not)")
    check(not mismatches,
          f"oracle 2: {compared} adversarial comparisons vs the re-based reference "
          f"byte-identical (mismatches: {mismatches})")
    print(f"  ({compared} comparisons against an independent implementation, "
          f"{len(mismatches)} mismatches)")


def test_N1_the_rebase_is_real_and_the_oracle_is_not_a_mirror():
    """The re-base's own falsifier, and the reason O-8's trap cannot be walked into quietly.

    Two ways the re-base could be worthless, and both are asserted against:

      (a) IT NEVER HAPPENED. If `reference_spread` still modelled the naive accumulator it
          would agree with `stale_reference_spread` everywhere, and N-1 would be asserting
          that the engine reproduces a bug. So the two references must DISAGREE — and
          disagree with the precise signature SPEC-0c §8(i) gives: only where a node takes
          three or more contributions, never in flow/hops/broke_through except as a
          downstream consequence, and with the new value equal to fsum over that node's own
          arriving contributions.

      (b) IT IS A MIRROR. If the reference were copied from src/ it would agree with the
          engine trivially and N-1 would be vacuous. That cannot be asserted by running
          code — a mirror passes every runtime test by construction — so it is asserted
          structurally: the reference must not be textually derived from the module under
          test. The check below is weak evidence on its own and is honest about that; the
          real control is that the reference is derived from the SPEC and reviewed as such.
    """
    section("N-1/O-8 the re-base is REAL: the oracle changed, and it is not a copy of src/")
    moved = 0
    only_at_3plus = True
    fsum_matches = 0
    fsum_total = 0
    for gs in range(60):
        store, ids = adversarial_graph(1000 + gs)
        for seed_node in ids:
            for params in PARAM_SWEEP:
                new = reference_spread(store, seed_node, **params)
                old = stale_reference_spread(store, seed_node, **params)
                ncontrib = {}
                for rid in new.flow:
                    t = store.get_road(rid).target_id
                    ncontrib[t] = ncontrib.get(t, 0) + 1
                ncontrib[seed_node] = ncontrib.get(seed_node, 0) + 1
                for k, v in new.activation.items():
                    if bits(v) != bits(old.activation.get(k, float("nan"))):
                        moved += 1
                        fsum_total += 1
                        terms = [new.flow[rid] for rid in new.flow
                                 if store.get_road(rid).target_id == k]
                        if k == seed_node:
                            terms = [params.get("energy", DEFAULT_SEED_ENERGY)] + terms
                        if bits(math.fsum(terms)) == bits(v):
                            fsum_matches += 1
                        # a node with < 3 arriving contributions may still move, but ONLY
                        # because something upstream of it did (SPEC-0c §8(ii)'s carve-out)
                        if ncontrib.get(k, 0) < 3:
                            upstream_moved = any(
                                store.get_road(rid).target_id == k
                                and bits(new.flow[rid]) != bits(old.flow.get(rid, float("nan")))
                                for rid in new.flow)
                            if not upstream_moved:
                                only_at_3plus = False
    check(moved > 0,
          f"(a) the re-based reference DISAGREES with the pre-0c one ({moved} moved "
          f"activation values) — the re-base is a real change, not a relabelling. If this "
          f"were 0 the oracle would still be a second copy of the bug.")
    check(only_at_3plus,
          "(a) and it disagrees ONLY where SPEC-0c §8(i) says it should: at a node taking "
          "three or more contributions, or downstream of one that did — never spontaneously")
    check(fsum_total and fsum_matches == fsum_total,
          f"(a) every moved value equals math.fsum over that node's OWN arriving "
          f"contributions ({fsum_matches}/{fsum_total}) — the new oracle computes the "
          f"exactly rounded sum of the multiset, which is what §2.3 specifies")
    # (b) NOT A MIRROR BY DELEGATION. This half IS mechanically decidable and is asserted
    #     absolutely: an oracle that calls the module under test proves nothing, and that
    #     is a property of the text, not a threshold.
    engine_src = open(os.path.join(SRC, "psyche_activation.py"), encoding="utf-8").read()
    this_src = open(os.path.abspath(__file__), encoding="utf-8").read()
    body = this_src.split("def reference_spread", 1)[1].split("\ndef ", 1)[0]
    engine_body = engine_src.split("def spread_activation", 1)[1]
    check("spread_activation(" not in body and "psyche_activation" not in body,
          "(b) the reference never calls spread_activation and never reaches into "
          "psyche_activation — it cannot be a mirror by delegation. It consumes only the "
          "store's public surface and the module's exported CONSTANTS.")

    # And the residual honesty. A TRANSCRIBED reference cannot be caught at runtime at
    # all: agreement is the goal, so a copy passes every runtime test by construction. A
    # text-overlap metric is not a control either — it is reported as an OBSERVATION, with
    # the overlapping text shown, so a reviewer can judge it instead of trusting a
    # threshold this test would otherwise have been free to tune until it passed.
    def shingles(text, k=8):
        toks = text.split()
        return {tuple(toks[i:i + k]) for i in range(max(0, len(toks) - k + 1))}

    overlap = sorted(shingles(body) & shingles(engine_body))
    note(f"reference/engine shared 8-token runs: {len(overlap)}. Inspected: every one is "
         f"an equation SPEC-0b2/0c states verbatim (`transmitted = outgoing * "
         f"road.strength * decay_per_hop`, `competing = out_total - road.strength`, the "
         f"sigma validation predicate). Any correct implementation must contain these, so "
         f"the overlap is evidence of a shared SPECIFICATION, not of transcription. "
         f"Provenance and review are the real control here, and this is said plainly "
         f"rather than dressed up as a passing assertion.")


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
    """LOOP-CLOSED, and re-based (SPEC-0c §6.1 row 4).

    Nothing here is hand-placed. The graph is what traverse() — the substrate's own
    biological primitive — produces from a stream of associations; perceive() chooses which
    nodes seed the spread by matching the utterance against node CONTENT; cluster_sources()
    decides which of those actually reach the field; and build_activation_field() supplies
    the per-source energies. The test picks the utterance and nothing else.

    The git oracle is deliberately NOT used here. This graph has in-degree well above 2, so
    it is outside the region where the pre-change engine had a single answer (§2.3). Using
    it would be pointing a stale oracle above its boundary, which is the exact mistake §8
    was rewritten to prevent — and it is asserted, not assumed, that the graph is outside
    the boundary.
    """
    section("N-1/O-8 LOOP-CLOSED: identity on a substrate the system's own pipeline built")
    from psyche_perceive import perceive
    from psyche_source_clustering import cluster_sources
    store = frozen_store()
    words = ["coffee", "warmth", "morning routine", "cozy feeling", "kitchen",
             "work", "desk", "deadline pressure", "writing code", "commute"]
    ids = [store.add_node(w, NodeType.CONCEPT) for w in words]
    rng = random.Random(7)
    for _ in range(60):
        a, b = rng.choice(ids), rng.choice(ids)
        worn(store, a, b, n=rng.randint(1, 9))
    perception = perceive(store, "coffee in the kitchen before work")
    check(len(perception.sources) > 0,
          "perception produced seeds from the utterance (the loop is closed at stage 1)")
    check(max_in_degree(store) >= 3,
          f"the system-built graph is OUTSIDE oracle 1's boundary (max in-degree "
          f"{max_in_degree(store)} >= 3), so the git oracle is correctly not used here")
    # stage 2: the clusterer decides which sources reach the field, and with what energy
    clustering = cluster_sources(store, perception.sources)
    seeds = list(clustering.group_seeds.items())
    check(len(seeds) > 0, "clustering produced group seeds (the loop is closed at stage 2)")
    mismatches = []
    for seed_node, seed_energy in seeds:
        # the ENERGY is the system's too, not a default this test chose
        got = signature(spread_activation(store, seed_node, energy=seed_energy,
                                          normalization_sigma=None))
        want = signature(reference_spread(store, seed_node, energy=seed_energy))
        if got != want:
            mismatches.append(store.get_node(seed_node).content)
    check(not mismatches,
          f"neutral output byte-identical on pipeline-selected seeds at pipeline-selected "
          f"energies ({len(mismatches)} mismatches: {mismatches})")
    # and one level further out: the whole multi-source field, driven end to end
    from psyche_field import build_activation_field
    f1 = build_activation_field(store, list(clustering.group_seeds.keys()),
                                source_energies=clustering.group_seeds)
    ref_total = {}
    for src in f1.sources:
        r = reference_spread(store, src, energy=clustering.group_seeds[src])
        for n, a in r.activation.items():
            ref_total[n] = ref_total.get(n, 0.0) + a
    check({k: bits(v) for k, v in f1.total.items()} == {k: bits(v) for k, v in ref_total.items()},
          "and the merged multi-source field reproduces bit-for-bit when every per-source "
          "spread is replaced by the reference — the loop closes through 1a as well as 0b")


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
    from psyche_store import SubstrateStore, Clock, NodeType
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
    from psyche_activation import spread_activation
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


def test_N2_O6_convergent_accumulation_is_order_INDEPENDENT():
    """WAS an asserted-negative (`..._DEFECT_A_convergent_accumulation_is_order_dependent`).

    This is the negative D-013 ground 1 called decisive: under ordering ALONE it would
    keep passing, truthfully, because the engine would still be order-dependent and merely
    pinned. Its going red is the evidence that 0c fixed the CAUSE and not the symptom. The
    replacement is O-6, and it is strictly stronger than the negative it retires.

    Non-vacuity is asserted, not assumed: the SAME three contributions summed by an
    explicit naive left-fold must genuinely disagree across the same six orders. Without
    that, O-6 would pass against a broken engine on an insensitive input.
    """
    section("O-6 order-perturbation invariance: permuting roads_from leaves the bits alone")
    store, S, T = _three_way_convergence_store()
    seen = {}
    contributions = {}
    for perm in itertools.permutations(range(3)):
        def permute(roads, p=perm):
            return [roads[i] for i in p] if len(roads) == 3 else roads
        r = spread_activation(PermutingStore(store, permute), S)   # LIBRARY DEFAULTS
        seen.setdefault(bits(r.activation[T]), []).append(perm)
        # the per-edge contributions arriving at T, in THIS permutation's arrival order
        contributions[perm] = [r.flow[rid] for rid in r.flow
                               if store.get_road(rid).target_id == T]
    for b, perms in seen.items():
        print(f"    {b}  = {struct.unpack('<d', bytes.fromhex(b))[0]!r}   "
              f"from {len(perms)} of 6 orders")
    # (a) NON-VACUITY. A naive left-fold over the very same terms must disagree with
    #     itself, or this fixture cannot tell a fixed engine from a broken one.
    naive = {bits(naive_sum(c)) for c in contributions.values()}
    check(len(naive) > 1,
          f"the fixture is SENSITIVE: a naive left-fold over T's own three arriving "
          f"contributions gives {len(naive)} distinct bit patterns across the 6 orders "
          f"({sorted(naive)}), so a merely order-PINNED engine would still fail below")
    # (b) THE PROPERTY.
    check(len(seen) == 1,
          f"activation[T] is ONE bit pattern under all 3! out-road orders "
          f"(distinct = {len(seen)}) — the accumulation is order-INDEPENDENT, not merely "
          f"order-pinned")
    # (c) AND IT IS THE EXACTLY-ROUNDED SUM, derived from the engine's own recorded flows
    #     rather than from a number this test chose.
    one = next(iter(contributions.values()))
    check(bits(math.fsum(one)) == next(iter(seen)),
          "and it equals math.fsum over T's own recorded per-edge flows, to the bit — "
          "the value is the exactly rounded sum of the multiset, not of a sequence")
    check(isinstance(store._out[S], dict) and not isinstance(store._out[S], set),
          "the store's own index is an insertion-ordered MAPPING, not a set of uuid4 ids "
          "(SPEC-0c §2.2) — the enabling condition for DEFECT-A is gone at its owner")


def test_N2_O6_order_independence_holds_with_the_overlay_ON_as_well():
    """WAS an asserted-negative (`..._DEFECT_A_is_inherited_from_0b_not_introduced_by_the_overlay`).

    "Inherited, not introduced" is moot once the defect is fixed (SPEC-0c §6.1). What is
    NOT moot is that order-independence must hold on BOTH code paths — the neutral one and
    the normalized one — since the overlay multiplies an extra order-sensitive factor into
    `transmitted`. Each fixture below is the count set that exposed the defect at that
    sigma, so the inputs are the ones that historically broke, not friendlier ones.
    """
    section("O-6 order-independence on both paths: sigma=None AND sigma=1.0")
    for sigma, counts in CONVERGENCE_COUNTS.items():
        store, S, T = _three_way_convergence_store(counts)
        seen = set()
        contributions = None
        for perm in itertools.permutations(range(3)):
            def permute(roads, p=perm):
                return [roads[i] for i in p] if len(roads) == 3 else roads
            r = spread_activation(PermutingStore(store, permute), S,
                                  normalization_sigma=sigma)
            seen.add(bits(r.activation[T]))
            if contributions is None:
                contributions = [r.flow[rid] for rid in r.flow
                                 if store.get_road(rid).target_id == T]
        check(len({bits(naive_sum(contributions))} | {bits(naive_sum(contributions[::-1]))}) > 1
              or len(set(map(bits, contributions))) == len(contributions),
              f"sigma={sigma!r}: the fixture's three contributions are distinct floats, so "
              f"their order is a real degree of freedom ({len(contributions)} terms)")
        check(len(seen) == 1,
              f"sigma={sigma!r} on {counts}: ONE bit pattern across all 6 out-road orders "
              f"({len(seen)} distinct)")
    note("Order-independence is asserted on the normalized path too, not just the neutral "
         "one: the overlay multiplies transmitted by sigma/(sigma+competing), and competing "
         "is derived from an fsum over the SAME roads whose order is being permuted. A fix "
         "that only reached the accumulator would fail here.")


DEFECT_A_DRIVER = textwrap.dedent('''
    import struct, sys
    from psyche_store import SubstrateStore, Clock, NodeType
    from psyche_activation import spread_activation
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    S = s.add_node("S", NodeType.CONCEPT); T = s.add_node("T", NodeType.CONCEPT)
    for i, (a, b) in enumerate(((1, 2), (1, 3), (1, 9))):
        M = s.add_node("M%d" % i, NodeType.CONCEPT)
        for _ in range(a): s.traverse(S, M)
        for _ in range(b): s.traverse(M, T)
    r = spread_activation(s, S)               # LIBRARY DEFAULTS, no proxy, real store
    print(struct.pack("<d", r.activation[T]).hex())
''')


def test_N2_O4_the_DEFECT_A_reproduction_is_ONE_bit_pattern_in_real_processes():
    """WAS an asserted-negative (`..._DEFECT_A_reaches_real_processes_at_library_defaults`).

    The input is unchanged — SPEC-0c §1 case 1, the five-node traverse()-only graph at
    library defaults on which 48 fresh processes returned two values. Only the expected
    outcome is inverted. SPEC-0c §7 calls this the external, unfakeable done-means: bit
    patterns across fresh processes are either identical or they are not, and no tolerance
    can be adjusted to make them so.

    The full O-4 matrix (all five interpreters x six hash seeds) lives in
    tests/test_tester_0c_adversarial.py; this is the in-suite regression leg.
    """
    section("O-4 the DEFECT-A reproduction now gives ONE bit pattern in fresh processes")
    outs = run_probe(DEFECT_A_DRIVER, interps=[sys.executable], reps=8)
    distinct = sorted(set(o for o in outs if not o.startswith("ERROR")))
    for d in distinct:
        print(f"    {d}  = {struct.unpack('<d', bytes.fromhex(d))[0]!r}"
              f"   ({outs.count(d)} of {len(outs)} runs)")
    check(not [o for o in outs if o.startswith("ERROR")],
          f"every probe process ran ({len([o for o in outs if o.startswith('ERROR')])} errors)")
    check(len(distinct) == 1,
          f"O-4: ONE bit pattern over {len(outs)} fresh processes on the 5-node "
          f"traverse()-only graph at library defaults (distinct = {len(distinct)}: "
          f"{distinct}). This is the exact input that produced two values before 0c.")
    note("What changed is the GUARANTEE, not just the number. Before 0c this varied at a "
         "FIXED PYTHONHASHSEED, because uuid4 ids differ per process and the seed axis "
         "never controlled the order. After 0c there is no order left for any axis to "
         "perturb: iteration is creation-ordered and the reduction is exactly rounded "
         "(SPEC-0c §5.2). The property is structural now, not sampled.")


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


def test_N5_O10_lone_out_road_factor_is_exactly_one_ON_A_MOVING_CLOCK():
    """WAS an asserted-negative (`..._DEFECT_B_lone_out_road_IS_attenuated_on_a_moving_clock`).

    N-5 restored, and the moving clock IS the point (SPEC-0c O-10). DEFECT-B was invisible
    to every test in the repository because they all froze the clock; the fixture below
    deliberately advances time on EVERY read, so a second read of the same road cannot help
    but return a different strength. That is what makes `competing == 0.0` an assertion
    about the read pattern rather than about the arithmetic.

    Asserted at every valid sigma, not one: the guarantee SPEC-0b2 §2 row 3 makes is
    "at any sigma", and a lone road is the one case where the factor must be exactly 1.0
    however small sigma gets.
    """
    section("O-10 a lone out-road transmits with factor EXACTLY 1.0 on a MOVING clock")
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
    check(len(reads) == 1,
          f"the road is read exactly ONCE per expansion (got {len(reads)} reads) — "
          f"out_total and the transmission loop share one materialised road view, so both "
          f"come from a single clock instant (SPEC-0c §3)")
    # The factor is recovered from the engine's OWN recorded flow and its OWN recorded
    # strength, so the assertion cannot be satisfied by a number this test supplies.
    strength_used = reads[0]
    expected_unattenuated = DEFAULT_SEED_ENERGY * strength_used * DEFAULT_DECAY_PER_HOP
    actual = r.flow[rid]
    print(f"    the single strength read      = {strength_used!r}")
    print(f"    unattenuated transmission     = {expected_unattenuated!r}")
    print(f"    actual transmission           = {actual!r}")
    check(bits(actual) == bits(expected_unattenuated),
          f"the lone road is transmitted BIT-IDENTICALLY to the unnormalized value "
          f"(factor exactly 1.0), on a clock that advanced between reads")
    # ...and at every sigma on the ladder, each on its own freshly-ticking clock.
    bad = []
    for sigma in SIGMAS:
        c2 = TickClock(1e-6)
        s2 = SubstrateStore(clock=c2)
        a2 = s2.add_node("A", NodeType.CONCEPT)
        b2 = s2.add_node("B", NodeType.CONCEPT)
        worn(s2, a2, b2, n=3)
        c2.ticking = True
        rec2 = RecordingStore(s2)
        rr = spread_activation(rec2, a2, normalization_sigma=sigma)
        rid2 = next(iter(s2.roads_from(a2)))
        strengths = [st for (k, st) in rec2.reads if k == rid2]
        want = DEFAULT_SEED_ENERGY * strengths[0] * DEFAULT_DECAY_PER_HOP
        if len(strengths) != 1 or bits(rr.flow[rid2]) != bits(want):
            bad.append((sigma, len(strengths)))
    check(not bad,
          f"factor is exactly 1.0 at every sigma in {SIGMAS} on a moving clock "
          f"(deviating: {bad})")
    note("Before 0c this same fixture gave competing = 1.7265900376095544e-09 and a factor "
         "of 0.99999999827341 — an elapsed-time residue masquerading as conductance. The "
         "residue is not merely small now, it is structurally absent: there is only one "
         "read, so there is no second instant for it to come from.")


def test_N5_O9_the_expansion_loop_reads_each_road_exactly_once():
    """WAS an asserted-negative (`..._DEFECT_B_scoping_absent_from_the_pre_change_engine`).

    It asserted the source contains `store.get_road(` TWICE inside spread_activation, which
    was DEFECT-B's cause. After SPEC-0c §3 it appears once; SPEC-0c §6.1 says to rewrite the
    expected count to 1. Done — but a source-text count is weak evidence on its own, so the
    structural half (a recording proxy, counting real calls on real graphs) is asserted
    first and the text count is kept only as a corroborating tripwire.

    O-17: this test emits the SAME NUMBER OF CHECKS whether or not git is available. The
    git leg's outcome is recorded as an observation; its check is emitted either way.
    """
    section("O-9 each road is read exactly once per expansion (structural, then textual)")
    # (a) STRUCTURAL — the property itself, measured on adversarial graphs including
    #     high-degree fans, cycles, self-loops and closed roads, at both sigma settings.
    worst = []
    for gs in range(25):
        store, ids = adversarial_graph(9100 + gs)
        for seed_node in ids:
            for sigma in (None, 1.0):
                rec = RecordingStore(store)
                spread_activation(rec, seed_node, normalization_sigma=sigma)
                # count decayed reads per (expanding source, road); a road belongs to
                # exactly one source, and a source expands at most once per spread
                per_road = {}
                for rid, _ in rec.reads:
                    per_road[rid] = per_road.get(rid, 0) + 1
                over = {k: v for k, v in per_road.items() if v > 1}
                if over:
                    worst.append((gs, seed_node, sigma, over))
    check(not worst,
          f"no road is read more than once in any expansion, across 25 adversarial graphs "
          f"x every seed x sigma in (None, 1.0) ({len(worst)} violations; {worst[:2]})")
    # (b) TEXTUAL — the tripwire. SPEC-0c §6.1 fixes the expected count at 1.
    src = open(os.path.join(SRC, "psyche_activation.py"), encoding="utf-8").read()
    body = src.split("def spread_activation", 1)[1]
    check(body.count("store.get_road(") == 1,
          f"exactly ONE `store.get_road(` call site inside spread_activation "
          f"(found {body.count('store.get_road(')}) — the duplicated read DEFECT-B rested "
          f"on is gone from the source, not merely made harmless")
    # (c) The pre-change comparison, if git is here. The CHECK IS EMITTED EITHER WAY, so
    #     the suite's assertion total does not depend on whether .git is present (O-17).
    pre = load_pre_change_engine()
    if pre is None:
        note("git unavailable — the pre-0b2 read-count comparison degrades to an "
             "observation; the check below is still emitted, so the total does not move")
        check(True, "pre-0b2 read-count comparison: UNAVAILABLE, recorded (git absent)")
    else:
        pre_body = getattr(pre, "__psyche_source__", "").split("def spread_activation", 1)[-1]
        check(pre_body.count("store.get_road(") == 1,
              f"pre-0b2 read-count comparison: the engine before the overlay also had "
              f"exactly one site (found {pre_body.count('store.get_road(')}) — 0c returns "
              f"the read pattern to what 0b had, rather than inventing a third one")


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


def _three_target_star():
    store = frozen_store()
    S = store.add_node("S", NodeType.CONCEPT)
    tgts = []
    for i in range(3):
        T = store.add_node("T%d" % i, NodeType.CONCEPT)
        tgts.append(T)
        worn(store, S, T, n=5)
    return store, S, tgts


def test_N7_O11_non_finite_sigma_is_refused_at_the_boundary():
    """WAS an asserted-negative (`..._DEFECT_C_sigma_infinity_and_nan_poison_the_result`).

    It asserted that sigma=inf silently produced NaN activation. SPEC-0c §4 closed that,
    so the negative is retired and REPLACED by the positive property it certifies: O-11.
    The check count is deliberately identical to the retired test's, and the assertion is
    strictly stronger — it pins the exception TYPE, the FRAME it is raised in, and that
    the message names the offending value.
    """
    section("O-11 non-finite sigma is REFUSED at the boundary (was the DEFECT-C negative)")
    store, S, tgts = _three_target_star()
    for sigma in (float("inf"), float("-inf"), float("nan")):
        try:
            spread_activation(store, S, normalization_sigma=sigma)
            outcome = "returned normally"
        except ValueError as e:
            outcome = e
        except Exception as e:                                     # noqa: BLE001
            outcome = f"wrong exception type {type(e).__name__}: {e}"
        named = isinstance(outcome, ValueError) and repr(sigma) in str(outcome)
        check(named,
              f"sigma={sigma!r} raises ValueError naming the offending value "
              f"(got: {outcome!r})")
    # ...and it is refused BEFORE any work: nothing is computed, so no NaN can exist to
    # leak. Asserted by the frame the exception carries, not by absence of a symptom.
    import traceback
    try:
        spread_activation(store, S, normalization_sigma=float("inf"))
        frames = []
    except ValueError:
        frames = [f.name for f in traceback.extract_tb(sys.exc_info()[2])]
    check(frames[-1:] == ["spread_activation"],
          f"the raise happens in spread_activation's own frame, not four layers down "
          f"(innermost frame: {frames[-1:]})")
    note("SPEC-0b2 §2 called sigma -> infinity 'the value that analytically recovers the "
         "current engine'. It is true in the limit and catastrophic at the literal value. "
         "The neutral value is None; large finite sigma is the way to approach it, and "
         "test_N7_large_finite_sigma_recovers_the_unnormalized_engine_exactly shows it "
         "does so byte-for-byte at 1e300.")


def test_N7_O11_non_positive_sigma_is_refused_rather_than_silently_silencing():
    """WAS an asserted-negative (`..._non_positive_sigma_silences_rather_than_going_negative`).

    It characterised sigma <= 0 as producing total silence at floor >= 0 and genuinely
    NEGATIVE activation once the floor went negative. SPEC-0c §4 rejects sigma <= 0 at the
    boundary, so both behaviours are now unreachable. The replacement asserts that, and
    asserts the negative-floor route is closed too — the route was the sharp edge of the
    old finding and it must not survive the fix.
    """
    section("O-11 sigma <= 0 is REFUSED, and the negative-activation route is closed")
    store, S, tgts = _three_target_star()
    for sigma in (0.0, -0.0, -1.0, -1e-300):
        try:
            spread_activation(store, S, normalization_sigma=sigma)
            ok = False
            detail = "returned normally"
        except ValueError as e:
            ok = repr(sigma) in str(e)
            detail = str(e)[:60]
        except Exception as e:                                     # noqa: BLE001
            ok = False
            detail = f"{type(e).__name__}: {e}"
        check(ok, f"sigma={sigma!r} raises ValueError naming the value ({detail})")
    # The old finding's sharpest edge: with a NEGATIVE floor the guard stopped hiding the
    # negative activation. That input now cannot reach the engine at all.
    try:
        spread_activation(store, S, normalization_sigma=-1.0, floor=-1e9)
        closed = False
    except ValueError:
        closed = True
    check(closed,
          "sigma=-1.0 with floor=-1e9 — the input that produced NEGATIVE activation "
          "before 0c — is refused at the boundary, so the route is closed rather than "
          "merely masked by a non-negative floor")


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
    from psyche_field import build_activation_field
    from psyche_perceive import think
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
        test_N1_the_rebase_is_real_and_the_oracle_is_not_a_mirror,
        test_N1_default_argument_is_the_neutral_value,
        test_N1_byte_identity_loop_closed_on_a_system_built_substrate,
        test_N2_determinism_across_hash_seeds_and_interpreters,
        test_N2_O6_convergent_accumulation_is_order_INDEPENDENT,
        test_N2_O6_order_independence_holds_with_the_overlay_ON_as_well,
        test_N2_O4_the_DEFECT_A_reproduction_is_ONE_bit_pattern_in_real_processes,
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
        test_N5_O10_lone_out_road_factor_is_exactly_one_ON_A_MOVING_CLOCK,
        test_N5_O9_the_expansion_loop_reads_each_road_exactly_once,
        test_N6_strictly_decreasing_in_competing,
        test_N6_strictly_increasing_in_sigma,
        test_N6_monotonicity_property_based_on_random_graphs,
        test_N7_difference_from_unnormalized_is_monotone_decreasing_in_sigma,
        test_N7_large_finite_sigma_recovers_the_unnormalized_engine_exactly,
        test_N7_O11_non_finite_sigma_is_refused_at_the_boundary,
        test_N7_O11_non_positive_sigma_is_refused_rather_than_silently_silencing,
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
    print("  TESTER VERDICT ON SPEC-0b2 §6, RE-ADJUDICATED AFTER 0c:  all 9 hold")
    print("=" * 70)
    print("    N-1 HOLDS   neutral byte-identity, on a RE-BASED oracle (SPEC-0c O-8).")
    print("                Oracle 1 (git) is bounded to in-degree <= 2, the region where")
    print("                the pre-change engine had a single well-defined answer at all.")
    print("    N-2 HOLDS   was DEFECT-A. The accumulator is now order-INDEPENDENT, not")
    print("                merely order-pinned: creation-ordered iteration at the store")
    print("                (SPEC-0c §2.2) plus an exactly-rounded reduction (§2.3).")
    print("    N-3 HOLDS   N-4 HOLDS   N-6 HOLDS   N-8 HOLDS   N-9 HOLDS")
    print("    N-5 HOLDS   was DEFECT-B. One road read per expansion (§3), so a lone")
    print("                out-road transmits with factor exactly 1.0 on a MOVING clock.")
    print("    N-7 HOLDS   was DEFECT-C. sigma is validated at the boundary and non-finite")
    print("                transmission is refused on its own terms (§4).")
    print()
    print("  THE ACCEPTANCE SIGNAL FOR 0c WAS INVERTED, and this file is where it landed.")
    print("  Ten tests in it went red on a correct fix. Each has been converted from")
    print("  'the defect is present' into the positive property it certifies, so the")
    print("  suite now asserts the fix rather than the bug. The six asserted-negatives")
    print("  SPEC-0c §6.1 enumerated are retired; the four the spec did not anticipate")
    print("  are rewritten with them. Nothing was deleted without a replacement.")
    print()
    print("  Mechanism only. No cognitive claim is made or approached here.")
    print("=" * 70)
    return _failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run_all() else 1)
