"""
EXP-2c CAPTURE — the BLIND realistic stimulus-construction script for the 2c graded
MEANING run (the 1e-selector analogue).

╔══════════════════════════════════════════════════════════════════════════════╗
║ WHAT THIS IS (and, with equal weight, what it is NOT)                           ║
║                                                                                ║
║   This script builds the FROZEN realistic STIMULI for the 2c graded meaning     ║
║   run, faithfully to the frozen pre-registration                                ║
║   docs/experiments/EXP-2c-interoception.md §5 (realistic percept battery) and   ║
║   §6 (realistic telemetry trace). It is the analogue of EXP-1e's blind, seeded, ║
║   hashed pair-list selector.                                                    ║
║                                                                                ║
║   It computes NO flip-rate and NO graded number of ANY kind. It builds the      ║
║   stimuli only: a fixed-seed realistic percept battery and a real-telemetry     ║
║   trace, serializes both to canonical sorted JSON, and SHA-256-hashes them so   ║
║   the two digests can be frozen into the §6.4 reserved slots — BEFORE any        ║
║   graded number exists (the EXP-1e §10 / EXP-1c deferred-hash discipline).      ║
║                                                                                ║
║   It reads ONLY the §5/§6 procedure. It NEVER reads activation, a winner, a      ║
║   coalition, a flip, or any result-side signal. It exposes NO grading / flip /  ║
║   winner / effect-size function. The graded run — winner-set flips over the     ║
║   frozen trace, the direction test, the control, the verdict — is the           ║
║   VALIDATOR'S separate later step, on the human's go-ahead. It is NOT here.      ║
║                                                                                ║
║ WHAT THIS IS NOT (honest framing — CONTRIBUTING.md rules 1-2; EXP-2c §1.1)            ║
║   Building these stimuli establishes NO meaning. It does NOT claim the system    ║
║   feels, has a body, has emotions, interoception in the human sense, awareness, ║
║   or consciousness. "friction" is a derived telemetry signal (wall-vs-CPU       ║
║   timing), nothing more. Whether the stimuli, once graded, MEAN anything is the ║
║   validator's call against the frozen trace — never asserted here.              ║
╚══════════════════════════════════════════════════════════════════════════════╝

BLINDNESS, CONCRETELY (the anti-circularity guard at the construction layer):
  - The battery is generated from a FIXED SEED over a FIXED structural parameter space —
    NEVER from any Psyche activation. Its serialized form records ONLY the structural
    description (anchors, domain sizes, integer traversal counts, bridge presence/target/
    bridge_n, depth_extra), so it is built from the seed and the parameter space alone.
  - The trace is captured from REAL perf_counter/process_time telemetry while the substrate
    does real mixed work (think()), with friction computed by the SAME psyche_bodysensor.
    compute_friction the cycle uses. think() runs ONLY to make real CPU work for the timing
    measurement; its winner/field/thought is NEVER read.
  - This module imports psyche_bodysensor (the permitted §6 telemetry surface) and the store/
    perceive surface (to construct stimuli + generate workload). It does NOT import the
    workspace-competition module that produces the graded winner, and it does not otherwise
    grade. (The blindness tests assert this statically.)

THE REALISTIC BATTERY vs THE PILOT (EXP-2c §5.1/§5.3 — why this is NOT the pilot):
  The pilot (experiments/pilot_2c_populability.py) engineers, for EVERY percept, a contested
  'midnode' at asymmetric distances (1 medium hop from one anchor, 2 strong hops from the
  other) to POSITION a basin-allegiance crossover d* — so "every percept is movable IN
  PRINCIPLE." That is correct for a feasibility pilot and WRONG for a meaning run. This
  realistic battery has NO contested node, NO 'midnode', and NO positioned crossover: small
  multi-domain neighborhoods grown from INDEPENDENT random structural draws, with bridge
  presence a real p=0.5 coin flip and bridge_n a FREE uniform draw over [1..30] (not the
  pilot's [1..6] crossover window). Whether any percept's winner moves under the realistic
  friction range is then an HONEST, UNBIASED measurement (the graded run's job), not a
  built-in property.

  *** DO NOT RUN THE CAPTURE-AND-FREEZE HERE. *** Producing the actual frozen trace/battery
  artifacts + filling the §6.4 slots is gated on the tester's PASS and the human's word
  (EXP-2c §6.5 step 6). The data-free tests (test_exp2c_capture.py) run in run_tests.py; the
  live capture RUN stays OUT, exactly like the pilot.

Run (capture a fresh real trace, serialize+hash the trace AND the battery, print provenance):
    python3 experiments/exp2c_capture.py
  Re-serialize+hash the deterministic battery only, without a fresh live capture:
    BATTERY_ONLY=1 python3 experiments/exp2c_capture.py

Pure Python standard library (CONTRIBUTING.md rule 8).
"""

from __future__ import annotations

import os
import sys
import json
import time
import hashlib
import random
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

# bring src/ onto the path (mirrors the experiment scripts' self-bootstrap)
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from psyche_store import SubstrateStore, Clock, NodeType
from psyche_perceive import think
# the SAME telemetry surface the cycle uses (the ONLY permitted §6 imports). compute_friction
# and BodySensor are re-exported by NAME so tests can assert object identity (they must be the
# library objects, never re-implementations).
from psyche_bodysensor import BodySensor, TelemetrySample, compute_friction


# ══════════════════════════════════════════════════════════════════════════════
# PRE-REGISTRATION — the §6.4 FIXED constants. These are fixed HERE, before any number.
# Do NOT tune any of them to a flip outcome (the capture is blind to grading).
# ══════════════════════════════════════════════════════════════════════════════

# -- §5.2 realistic battery (FIXED; distinct from the pilot's contested-by-design set) --
BATTERY_SEED_REALISTIC = 20260622     # independent draw; != pilot's 20260621, EXP-1e/1c seeds
PERCEPT_COUNT_REALISTIC = 60          # >= 30 (powered proportion), larger than the pilot's 40

# the §5.2 documented random parameter space (inclusive integer ranges unless noted):
DOMAIN_SIZE_RANGE = (2, 5)            # near neighbors per anchor (drawn independently per anchor)
INTERNAL_N_RANGE = (8, 30)            # traversal count per anchor->neighbor road (per road)
BRIDGE_PRESENT_P = 0.5                # cross-domain bridge present with this probability
BRIDGE_N_RANGE = (1, 30)             # bridge traversal count — a FREE uniform draw (NOT [1..6])
DEPTH_EXTRA_RANGE = (0, 1)           # 0 or 1 second-hop tail on anchorA's first neighbor

# -- §6 realistic telemetry capture (FIXED; NOT the pilot's busy-vs-idle extremes) --
CAPTURE_SAMPLES_REALISTIC = 300       # boundary reads (characterize the band + supply the sweep)
REALISTIC_YIELD_S = 0.0005            # 0.5 ms cooperative yield (NOT the pilot's 4 ms stall)
SWEEP_LEVELS_REALISTIC = 9            # friction levels at evenly-spaced quantiles of the range

# -- a fixed rotation of short realistic utterances: the WORKLOAD GENERATOR only --
# These drive real CPU work on a small fixed workload substrate (built below). They are NOT
# the graded percept battery (§6.1: the trace must not be co-constructed with the battery).
WORK_UTTERANCES = (
    "coffee morning kitchen",
    "river water stone",
    "music sound rhythm",
    "garden flower soil",
    "letter paper words",
)

# -- frozen artifact paths (filled only by the gated freeze commit; NOT run here) --
RESULTS_DIR = os.path.join(_HERE, "results")
TRACE_PATH = os.path.join(RESULTS_DIR, "exp2c_realistic_telemetry_trace.json")
PERCEPTS_PATH = os.path.join(RESULTS_DIR, "exp2c_realistic_percepts.json")

# ══════════════════════════════════════════════════════════════════════════════
# §5.2 ANCHOR VOCABULARY — non-substring-overlapping content words.
# Perception lights up a node iff an input token is a substring of the node's content
# (psyche_perceive.perceive). To keep perception CLEAN (each percept lights up exactly its two
# anchors and their neighbors, never a stray anchor), no anchor word may be a substring of
# another. This is a structural cleanliness requirement (as in the pilot's two clean anchors),
# NOT a flip-engineering choice — the anchors are drawn at random from this fixed vocabulary.
# Neighbor / tail node contents are namespaced ("nbr_<anchor>_<k>", "tail_<anchor>") so they
# never collide with an anchor token and are never themselves perceived.
# ══════════════════════════════════════════════════════════════════════════════
ANCHOR_VOCAB = (
    "alpha", "bravo", "delta", "echo", "foxtrot", "golf", "hotel", "india",
    "juliet", "kilo", "lima", "november", "oscar", "papa", "quebec", "romeo",
    "sierra", "tango", "uniform", "victor", "whiskey", "xray", "yankee", "zulu",
)
# (24 words; all mutually non-substring-overlapping — verified by an asserted check at import.)


def _assert_vocab_clean() -> None:
    """Fail loudly at import if any anchor word is a substring of another (would let one
    percept's perception light up a second anchor — a perception-cleanliness violation, not a
    flip-engineering one). This is a structural guard, not a graded computation."""
    for a in ANCHOR_VOCAB:
        for b in ANCHOR_VOCAB:
            if a is not b and (a in b or b in a):
                raise ValueError(
                    f"ANCHOR_VOCAB not substring-clean: {a!r} overlaps {b!r}. Two-anchor "
                    "perception requires non-overlapping anchor words."
                )


_assert_vocab_clean()


# ══════════════════════════════════════════════════════════════════════════════
# 1) THE REALISTIC PERCEPT BATTERY (§5.2) — fixed-seed, NOT flip-pre-selected
# ══════════════════════════════════════════════════════════════════════════════

# THE DOCUMENTED DRAW ORDER (frozen; the determinism test re-derives this EXACT order):
#   per percept, from a single seeded random.Random(BATTERY_SEED_REALISTIC), in order:
#     1. anchor A index   = rng.randrange(len(ANCHOR_VOCAB))
#     2. anchor B index   = rng.randrange(len(ANCHOR_VOCAB))   [re-drawn until != A]
#     3. domain_size_a    = rng.randint(*DOMAIN_SIZE_RANGE)
#     4. domain_size_b    = rng.randint(*DOMAIN_SIZE_RANGE)
#     5. internal_n_a[k]  = rng.randint(*INTERNAL_N_RANGE)  for k in range(domain_size_a)
#     6. internal_n_b[k]  = rng.randint(*INTERNAL_N_RANGE)  for k in range(domain_size_b)
#     7. bridge_present   = rng.random() < BRIDGE_PRESENT_P
#     8. if bridge_present: bridge_target_index = rng.randrange(domain_size_b)
#                           bridge_n            = rng.randint(*BRIDGE_N_RANGE)
#     9. depth_extra      = rng.randint(*DEPTH_EXTRA_RANGE)
# No draw is conditioned on any outcome; the order is fixed so the battery is reproducible.
DRAW_ORDER = (
    "anchor_a_index", "anchor_b_index(redraw_if_equal)", "domain_size_a", "domain_size_b",
    "internal_n_a[per-road]", "internal_n_b[per-road]", "bridge_present",
    "bridge_target_index(if bridge)", "bridge_n(if bridge)", "depth_extra",
)


@dataclass
class RealisticPercept:
    """One realistic two-anchor percept — a STRUCTURAL description (the §5.2 draws) plus a
    runnable store builder. It carries NO crossover field (no d*, no 'midnode', no contested
    node): the topology is grown from independent random draws, never positioned to flip.

    Fields (all the structural description the §6.4 serialization records):
      anchor_a_content / anchor_b_content : the two anchor words (perception lights up these)
      percept_text                        : "anchorA anchorB" (the utterance)
      domain_size_a / domain_size_b       : near-neighbor counts (independent draws)
      internal_n_a / internal_n_b         : per-road traversal counts (anchor->neighbor)
      bridge_present                      : whether a single cross-domain bridge exists (p=0.5)
      bridge_target_index                 : which B-neighbor the bridge targets (None if absent)
      bridge_n                            : the bridge traversal count (None if absent)
      depth_extra                         : 0/1 second-hop tail on anchorA's first neighbor
    """
    anchor_a_content: str
    anchor_b_content: str
    percept_text: str
    domain_size_a: int
    domain_size_b: int
    internal_n_a: List[int]
    internal_n_b: List[int]
    bridge_present: bool
    bridge_target_index: Optional[int]
    bridge_n: Optional[int]
    depth_extra: int

    def build_store(self) -> SubstrateStore:
        """Build the substrate topology this percept describes. Deterministic (the simulated
        clock starts at 0.0 so no decay fires; node creation order is fixed by the draws).
        NO contested 'midnode' is created; the optional bridge goes anchorA -> an EXISTING
        B-domain neighbor (a real 1-hop edge), never via a 2-hop constructed sink."""
        s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
        a = s.add_node(self.anchor_a_content, NodeType.CONCEPT)
        b = s.add_node(self.anchor_b_content, NodeType.CONCEPT)
        # grow each anchor's near neighborhood. CRITICAL: neighbor/tail contents must NOT embed
        # an anchor word (perception matches a token as a SUBSTRING of node content; if a
        # neighbor contained the anchor word it would ALSO light up as a source, breaking the
        # §5.2 "perception lights up exactly the two anchors" property). So neighbors use an
        # anchor-FREE namespace ("nbr_a_<k>", "nbr_b_<k>", "tail_a") that no NATO anchor word is
        # a substring of. (Names need only be unique WITHIN this fresh per-percept store.)
        a_nbrs: List[str] = []
        for k in range(self.domain_size_a):
            nid = s.add_node(f"nbr_a_{k}", NodeType.CONCEPT)
            a_nbrs.append(nid)
            _worn(s, a, nid, self.internal_n_a[k])
        b_nbrs: List[str] = []
        for k in range(self.domain_size_b):
            nid = s.add_node(f"nbr_b_{k}", NodeType.CONCEPT)
            b_nbrs.append(nid)
            _worn(s, b, nid, self.internal_n_b[k])
        # optional second-hop tail on anchorA's first neighbor (distance-2 structure a
        # decay_per_hop change can reach or not — drawn at random, not positioned to flip)
        if self.depth_extra == 1 and a_nbrs:
            tail = s.add_node("tail_a", NodeType.CONCEPT)
            _worn(s, a_nbrs[0], tail, self.internal_n_a[0])
        # optional single cross-domain bridge: anchorA -> an existing B-neighbor (1 hop),
        # strength set by a FREE uniform bridge_n draw. No contested sink, no positioned d*.
        if self.bridge_present and b_nbrs:
            target = b_nbrs[self.bridge_target_index]
            _worn(s, a, target, self.bridge_n)
        return s


def _worn(s: SubstrateStore, src: str, tgt: str, n: int) -> None:
    """Wear in a road by traversing it n times (the pilot's _worn helper, same semantics)."""
    for _ in range(n):
        s.traverse(src, tgt)


def build_realistic_battery(seed: int, count: int) -> List[RealisticPercept]:
    """Generate `count` realistic two-anchor percepts from a FIXED-SEED RNG over the §5.2
    parameter space, in the documented DRAW_ORDER. Deterministic and reproducible; NOT
    hand-picked for flippability and NOT the pilot's contested-by-design set.

    Each percept names two non-substring-overlapping anchors (clean perception) and grows a
    small multi-node neighborhood per anchor from INDEPENDENT random structural draws. No
    contested node, no positioned crossover.
    """
    rng = random.Random(seed)
    vocab_n = len(ANCHOR_VOCAB)
    battery: List[RealisticPercept] = []
    for _ in range(count):
        ia = rng.randrange(vocab_n)
        ib = rng.randrange(vocab_n)
        while ib == ia:
            ib = rng.randrange(vocab_n)
        anchor_a = ANCHOR_VOCAB[ia]
        anchor_b = ANCHOR_VOCAB[ib]
        ds_a = rng.randint(*DOMAIN_SIZE_RANGE)
        ds_b = rng.randint(*DOMAIN_SIZE_RANGE)
        internal_n_a = [rng.randint(*INTERNAL_N_RANGE) for _ in range(ds_a)]
        internal_n_b = [rng.randint(*INTERNAL_N_RANGE) for _ in range(ds_b)]
        bridge_present = rng.random() < BRIDGE_PRESENT_P
        if bridge_present:
            bridge_target_index = rng.randrange(ds_b)
            bridge_n = rng.randint(*BRIDGE_N_RANGE)
        else:
            bridge_target_index = None
            bridge_n = None
        depth_extra = rng.randint(*DEPTH_EXTRA_RANGE)
        battery.append(RealisticPercept(
            anchor_a_content=anchor_a,
            anchor_b_content=anchor_b,
            percept_text=f"{anchor_a} {anchor_b}",
            domain_size_a=ds_a,
            domain_size_b=ds_b,
            internal_n_a=internal_n_a,
            internal_n_b=internal_n_b,
            bridge_present=bridge_present,
            bridge_target_index=bridge_target_index,
            bridge_n=bridge_n,
            depth_extra=depth_extra,
        ))
    return battery


# ══════════════════════════════════════════════════════════════════════════════
# 2) SERIALIZE + HASH THE BATTERY (structural description only — §6.4 step 4)
# ══════════════════════════════════════════════════════════════════════════════

def _percept_to_jsonable(p: RealisticPercept) -> dict:
    """The STRUCTURAL description of one percept (the §6.4-required fields). NO Psyche output —
    no activation, no winner, no friction. Built from the seed + parameter space alone."""
    return {
        "anchor_a": p.anchor_a_content,
        "anchor_b": p.anchor_b_content,
        "percept_text": p.percept_text,
        "domain_size_a": p.domain_size_a,
        "domain_size_b": p.domain_size_b,
        "internal_n_a": list(p.internal_n_a),
        "internal_n_b": list(p.internal_n_b),
        "bridge_present": p.bridge_present,
        "bridge_target_index": p.bridge_target_index,
        "bridge_n": p.bridge_n,
        "depth_extra": p.depth_extra,
    }


def serialize_battery(battery: List[RealisticPercept]) -> str:
    """Serialize the battery to a CANONICAL sorted-JSON string (the form the SHA-256 is taken
    over). Deterministic function of the structural description only."""
    payload = {
        "spec": "EXP-2c realistic percept battery (structural description only; seed-generated)",
        "battery_seed": BATTERY_SEED_REALISTIC,
        "percept_count": PERCEPT_COUNT_REALISTIC,
        "parameter_space": {
            "domain_size_range": list(DOMAIN_SIZE_RANGE),
            "internal_n_range": list(INTERNAL_N_RANGE),
            "bridge_present_p": BRIDGE_PRESENT_P,
            "bridge_n_range": list(BRIDGE_N_RANGE),
            "depth_extra_range": list(DEPTH_EXTRA_RANGE),
        },
        "draw_order": list(DRAW_ORDER),
        "anchor_vocab": list(ANCHOR_VOCAB),
        "percepts": [_percept_to_jsonable(p) for p in battery],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def sha256_of_canonical(canonical_json: str) -> str:
    """SHA-256 of a canonical-JSON string (the deferred-hash digest). Deterministic function
    of the content, exactly as the pilot's save_and_hash_trace hashes the canonical sorted
    form."""
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════
# 3) THE REALISTIC TELEMETRY TRACE (§6.1) — captured from real mixed work
#    *** the ONLY non-determinism; do NOT run as part of grading ***
# ══════════════════════════════════════════════════════════════════════════════

def build_workload_store() -> SubstrateStore:
    """Build the small fixed WORKLOAD substrate (§6.1) — the workload generator, ENTIRELY
    separate from the graded percept battery. It exists only to give think() real nodes to
    spread activation over, so the timing measurement reflects real CPU work. Its contents
    deliberately match the WORK_UTTERANCES tokens so perception lights up real sources and the
    cycle does genuine work."""
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    # a few small linked domains whose contents the WORK_UTTERANCES name
    domains = [
        ["coffee", "morning", "kitchen", "mug", "warm"],
        ["river", "water", "stone", "bank", "flow"],
        ["music", "sound", "rhythm", "note", "song"],
        ["garden", "flower", "soil", "seed", "leaf"],
        ["letter", "paper", "words", "ink", "page"],
    ]
    for words in domains:
        ids = [s.add_node(w, NodeType.CONCEPT) for w in words]
        # link each domain into a small connected neighborhood (real spread structure)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                _worn(s, ids[i], ids[j], 12)
    return s


def capture_real_telemetry() -> List[TelemetrySample]:
    """Capture a REAL telemetry trace as a list of TelemetrySample(perf, proc) pairs from the
    §6.1 realistic continuous mixed workload (NOT the pilot's busy-spin-vs-sleep extremes).

    *** This is the ONE-TIME live boundary step — the single point of non-determinism. It is
    NOT on the deterministic test surface and must NOT be run as part of grading. ***

    Each boundary read takes time.perf_counter() and time.process_time() at the same instant.
    Between reads, ONE realistic work interval runs: the substrate think() (real cognitive
    work) on a rotating WORK_UTTERANCE, then a SMALL cooperative time.sleep(REALISTIC_YIELD_S)
    that models an ordinary scheduling pause (NOT a deliberate stall). This produces friction
    from REAL contention during REAL work (GC, allocation, OS scheduling, the small yield),
    spanning a moderate continuous band. think()'s RESULT IS NEVER READ — it is run only to
    generate work; no winner / field / thought / friction is inspected here (the script is
    blind to grading).
    """
    workload_store = build_workload_store()
    samples: List[TelemetrySample] = []
    # prime: the very first read has no predecessor (BodySensor returns neutral for it)
    samples.append(TelemetrySample(perf=time.perf_counter(), proc=time.process_time()))
    for i in range(CAPTURE_SAMPLES_REALISTIC):
        # ONE realistic work interval = real cognitive work (the cycle). The returned
        # ThoughtResult is intentionally discarded: we measure TIMING, never read its winner.
        think(workload_store, WORK_UTTERANCES[i % len(WORK_UTTERANCES)])
        time.sleep(REALISTIC_YIELD_S)  # small cooperative yield (NOT a deliberate stall)
        samples.append(TelemetrySample(perf=time.perf_counter(), proc=time.process_time()))
    return samples


def frictions_from_trace(samples: List[TelemetrySample]) -> List[float]:
    """Replay a frozen trace through a BodySensor and collect the friction value each read
    produces (dropping the first, the neutral baseline) — EXACTLY how the cycle would consume
    it. Uses the library BodySensor + the SAME compute_friction (inside read()). Deterministic
    over a fixed sample sequence."""
    sensor = BodySensor(simulated=True, trace=samples)
    out: List[float] = []
    for _ in range(len(samples)):
        try:
            out.append(sensor.read())
        except IndexError:
            break
    return out[1:]  # drop the baseline / neutral read


def sweep_levels_from_frictions(frictions: List[float], n_levels: int) -> List[float]:
    """Pick `n_levels` friction values evenly spaced across the REAL observed min..max range.
    Uses ONLY the actual recorded span — no inflation beyond what the machine produced (§6.2).
    Mirrors the pilot's sweep_levels_from_frictions, over the realistic band."""
    if not frictions:
        return []
    ordered = sorted(frictions)
    lo, hi = ordered[0], ordered[-1]
    if hi <= lo:
        return [lo]
    return [lo + (hi - lo) * (k / (n_levels - 1)) for k in range(n_levels)]


def _trace_to_jsonable(samples: List[TelemetrySample]) -> dict:
    return {
        "spec": "EXP-2c realistic telemetry trace (real mixed-workload capture; NOT pilot extremes)",
        "capture_samples": CAPTURE_SAMPLES_REALISTIC,
        "realistic_yield_s": REALISTIC_YIELD_S,
        "work_utterances": list(WORK_UTTERANCES),
        "samples": [[s.perf, s.proc] for s in samples],
    }


def serialize_trace(samples: List[TelemetrySample]) -> str:
    """Canonical sorted-JSON string of the trace (the form the SHA-256 is taken over)."""
    return json.dumps(_trace_to_jsonable(samples), sort_keys=True, separators=(",", ":"))


# ══════════════════════════════════════════════════════════════════════════════
# 4) FREEZE-COMMIT HELPERS (write artifacts + print provenance). These WRITE files; the
#    main() that calls the live capture is GATED — see the module docstring. The data-free
#    tests never call main() / capture_real_telemetry().
# ══════════════════════════════════════════════════════════════════════════════

def _write_canonical(path: str, canonical_json: str) -> None:
    """Write the on-disk artifact as indent=2 sorted JSON (human-diffable), while the HASH is
    taken over the canonical compact form (sha256_of_canonical) — exactly the pilot's split."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    payload = json.loads(canonical_json)
    with open(path, "w") as f:
        f.write(json.dumps(payload, sort_keys=True, indent=2))


def main() -> int:
    """Capture the realistic trace, serialize+hash BOTH stimuli, print provenance for the
    §6.4 slots. Computes NO flip-rate, NO winner, NO effect size — grading is deferred.

    *** This produces the frozen artifacts. Per EXP-2c §6.5 it is run ONLY in the gated freeze
    step (after the tester's PASS and on the human's word), NEVER as part of grading and NEVER
    by the test suite. ***
    """
    battery_only = os.environ.get("BATTERY_ONLY", "") == "1"

    print("=" * 78)
    print("  EXP-2c CAPTURE — BLIND realistic stimulus construction (NO graded number)")
    print("=" * 78)
    print("  This builds the FROZEN stimuli only (the 1e-selector analogue). It computes NO")
    print("  flip-rate, NO winner, NO effect size. The graded MEANING run is the validator's")
    print("  separate later step, on the human's go-ahead. (EXP-2c §0 / §6.)")
    print("=" * 78)

    # -- the deterministic battery (always; no live read) --
    battery = build_realistic_battery(BATTERY_SEED_REALISTIC, PERCEPT_COUNT_REALISTIC)
    battery_canon = serialize_battery(battery)
    battery_hash = sha256_of_canonical(battery_canon)
    n_bridged = sum(1 for p in battery if p.bridge_present)
    _write_canonical(PERCEPTS_PATH, battery_canon)
    print(f"\n  [BATTERY] realistic percept battery: {len(battery)} percepts, "
          f"seed {BATTERY_SEED_REALISTIC}")
    print(f"            bridged (p=0.5): {n_bridged}/{len(battery)}   "
          f"unbridged: {len(battery) - n_bridged}/{len(battery)}")
    print(f"            structural description serialized -> "
          f"{os.path.relpath(PERCEPTS_PATH, _HERE)}")
    print(f"  REALISTIC PERCEPT BATTERY SHA-256: {battery_hash}")

    if battery_only:
        print("\n  [BATTERY_ONLY] skipped the live trace capture. The battery hash above is the"
              " deterministic §6.4 battery digest; re-run without BATTERY_ONLY to also capture"
              " the live trace.")
        print("=" * 78)
        return 0

    # -- the realistic telemetry trace (the ONE-TIME live boundary capture) --
    samples = capture_real_telemetry()
    trace_canon = serialize_trace(samples)
    trace_hash = sha256_of_canonical(trace_canon)
    _write_canonical(TRACE_PATH, trace_canon)

    frictions = frictions_from_trace(samples)
    if not frictions:
        print("\n  ERROR: the captured trace produced no friction values.")
        return 2
    observed_min, observed_max = min(frictions), max(frictions)
    sweep = sweep_levels_from_frictions(frictions, SWEEP_LEVELS_REALISTIC)

    print(f"\n  [TRACE] realistic telemetry trace: {len(samples)} samples "
          f"({CAPTURE_SAMPLES_REALISTIC} intervals + 1 baseline)")
    print(f"          serialized -> {os.path.relpath(TRACE_PATH, _HERE)}")
    print(f"  REALISTIC TELEMETRY TRACE SHA-256: {trace_hash}")
    print(f"  OBSERVED REAL FRICTION RANGE [min..max]: [{observed_min:.6f} .. {observed_max:.6f}]")
    print(f"  SWEPT FRICTION LEVELS ({len(sweep)}): {[round(f, 6) for f in sweep]}")

    if observed_max <= observed_min:
        print("\n  NOTE (degenerate capture, §6.2): the realistic friction band collapsed to a"
              " single value on this machine/run. Per §6.2 this is an HONEST instrument/"
              "environment finding for the validator's graded run to report as NOT-YET — it is"
              " NOT a license to widen to the pilot's extremes. (This capture step itself still"
              " computes no graded number.)")

    # provenance line for the §6.4 slot
    prov = (
        f"machine={platform.platform()} · python={platform.python_version()} · "
        f"CAPTURE_SAMPLES_REALISTIC={CAPTURE_SAMPLES_REALISTIC} · "
        f"REALISTIC_YIELD_S={REALISTIC_YIELD_S} · SWEEP_LEVELS_REALISTIC={SWEEP_LEVELS_REALISTIC} · "
        f"captured_at={datetime.now(timezone.utc).isoformat()}"
    )
    print(f"  CAPTURE PROVENANCE: {prov}")

    print("\n" + "=" * 78)
    print("  CAPTURE COMPLETE — stimuli built + hashed. NO flip-rate, NO winner, NO effect")
    print("  size was computed. Paste the two SHA-256 digests, the observed range, the swept")
    print("  levels, and the provenance into the EXP-2c §6.4 reserved slots in the gated freeze")
    print("  commit (BEFORE any graded number). The graded run is the validator's next step.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
