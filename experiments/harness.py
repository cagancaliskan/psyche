"""
Psyche — Phase 2 experiments — the measurement harness.

This is the reusable instrument for the empirical-validation phase. It imports the
PROVEN, FROZEN library from ../src UNCHANGED and never writes to it. Everything here
is pure-read and deterministic by construction; no experiment is allowed to modify the
engine to manufacture an effect.

Three pieces:

  build_graph_from_spec(spec)        construct a SubstrateStore from a declarative spec.
  retrieval_strength(store, cue, t)  THE readout/instrument: one designated target's
                                     activation under a spread from `cue`. Pure read.
  run_trials(spec_factory, n, ...)   aggregate the readout over n fresh instances;
                                     report mean and spread.

WHY A SIMULATED CLOCK IS MANDATORY (the load-bearing determinism decision)
--------------------------------------------------------------------------
The substrate store applies LAZY, WALL-CLOCK time-decay on every `traverse()` (via
`strengthen` → `_persist_decay`). If we built graphs against the real clock, the few
microseconds that elapse between calls would (a) make each edge decay a different,
unrepeatable amount and (b) make two edges built "equally" actually have DIFFERENT
strengths. Both would wreck the experiment: it would no longer be deterministic, and
the "all edges equal strength" control would be a lie.

We therefore build every graph against `Clock(simulated=True)`, which starts at t=0 and
is NEVER advanced here. With elapsed time fixed at zero, decay is a no-op (dt=0), so an
edge crossed the same number of times always has byte-identical strength. This is what
"deterministic by construction" means for these experiments, and it is achieved purely
by *how we call* the frozen library — not by changing it.

(The only remaining nondeterminism source — uuid4 node/road IDs and hash-seeded set
iteration over them — is exactly what the library is PROVEN invariant to. So rebuilding
the same spec yields different internal IDs but identical activation values; `run_trials`
makes that visible as spread == 0.0.)

Pure Python standard library. Reads the library through its public surface only.
"""

from __future__ import annotations

import os
import sys

# ── bootstrap: make the FROZEN library importable by bare name ───────────────────────
# The library modules live in ../src and are imported by BARE name (`psyche_store`,
# `psyche_activation`) — the project's convention (see run_tests.py). We insert the
# ABSOLUTE path to src at the front of sys.path so those imports resolve regardless of
# the caller's working directory. This reads src/; it never modifies it.
_HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(os.path.dirname(_HERE), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

from psyche_store import SubstrateStore, Clock, NodeType
from psyche_activation import (
    spread_activation,
    DEFAULT_SEED_ENERGY,
    DEFAULT_DECAY_PER_HOP,
    DEFAULT_FLOOR,
    DEFAULT_HOP_BUDGET,
)


# ─────────────────────────────────────────────────────────────────────────────
# Declarative graph spec
# ─────────────────────────────────────────────────────────────────────────────
#
# A spec is a plain dict:
#
#     {
#         "nodes": ["S", "T1", "T2", ...],                 # content names (unique)
#         "edges": [("S", "T1", 3), ("S", "T2", 3), ...],  # (src, tgt, traverse_count)
#     }
#
# The third element of each edge is the number of times the edge is `traverse`d. Because
# we build against a frozen simulated clock (dt=0, no decay), traverse_count is a pure
# STRENGTH knob: equal counts ⇒ equal strength, exactly. This is how the fan experiment
# holds "all edges equal strength" as a hard control rather than an approximation.

Spec = Dict[str, object]


@dataclass
class GraphInstance:
    """A built graph plus the name→ID map needed to address it.

    `store` is a SubstrateStore on a simulated clock; `ids` maps each spec content name
    to the uuid4 NodeID the store assigned it. Callers translate names→IDs through `ids`
    and never interpret the IDs themselves (the IDs differ on every build; that is fine —
    the library is invariant to them)."""
    store: SubstrateStore
    ids: Dict[str, str]


def build_graph_from_spec(spec: Spec, *, node_type: NodeType = NodeType.CONCEPT) -> GraphInstance:
    """Construct a SubstrateStore from a declarative spec. Deterministic by construction.

    Builds against `Clock(simulated=True)` (see module docstring) so that edges with
    equal traverse counts have byte-identical strength and nothing decays mid-build.
    Each node in spec["nodes"] is added once; each edge (src, tgt, count) is `traverse`d
    exactly `count` times. Returns a GraphInstance carrying the store and the name→ID map.

    Pure with respect to the frozen library: it only calls the library's public
    constructors/mutators on a NEW store it owns; it touches nothing under src/.
    """
    store = SubstrateStore(clock=Clock(simulated=True), debug=True)

    ids: Dict[str, str] = {}
    for name in spec["nodes"]:                      # type: ignore[index]
        ids[name] = store.add_node(name, node_type)

    for edge in spec["edges"]:                      # type: ignore[index]
        src_name, tgt_name, count = edge
        for _ in range(count):
            store.traverse(ids[src_name], ids[tgt_name])

    return GraphInstance(store=store, ids=ids)


# ─────────────────────────────────────────────────────────────────────────────
# THE READOUT / INSTRUMENT
# ─────────────────────────────────────────────────────────────────────────────

def retrieval_strength(
    store: SubstrateStore,
    cue: str,
    target: str,
    *,
    energy: float = DEFAULT_SEED_ENERGY,
    decay_per_hop: float = DEFAULT_DECAY_PER_HOP,
    floor: float = DEFAULT_FLOOR,
    hop_budget: int = DEFAULT_HOP_BUDGET,
) -> float:
    """THE instrument. Spread activation from `cue` and report the `target` node's
    accumulated activation. This single function is the operational definition of
    "retrieval strength" for every experiment in this phase — defined once, here, so
    that every study measures the same thing.

    Operationalization: we run the library's deterministic `spread_activation` from the
    cue node and read the target's final activation out of the result. A target that is
    not reached at all has activation 0.0 (returned as such, not an error) — that is a
    meaningful readout ("the cue does not retrieve it"), not a missing value.

    PURE READ. `spread_activation` is a proven pure read (it mutates nothing in the
    store), and a dict `.get` is a read. Calling this never changes the graph, so the
    same store can be probed any number of times with identical results. `cue` and
    `target` are NodeIDs (resolve them via GraphInstance.ids).

    The activation knobs (energy / decay_per_hop / floor / hop_budget) default to the
    library's own defaults and are exposed so an experiment can hold them constant across
    conditions — which is itself a control we assert.

    READOUT SEMANTICS — RAW magnitude, NOT a normalized share (read this before 2B).
    This returns the target's RAW accumulated activation. For a hop-1 target on an
    equal-strength edge that is exactly `energy * strength * decay_per_hop`, and — because
    the engine does NOT divide a source's energy among its out-roads (EXPERIMENT_NOTES.md,
    STEP 0) — it is INDEPENDENT of the source's fan. So this instrument measures "how much
    activation arrived", not "what SHARE of the cue's outgoing activation this target
    captured." That distinction is precisely why the fan curve is flat, and it is a choice
    the priming study (2B) must make ON THE RECORD, in advance: either keep this RAW readout
    (then the registrable contrast is presence/absence — a related/reachable target lights
    up, an unrelated/unreachable one does not) OR layer a NORMALIZED / graded readout on top
    (then relatedness strength maps to activation magnitude). This is flagged, not resolved
    here, so that 2B's prediction is pre-registered before any priming run.
    """
    result = spread_activation(
        store, cue,
        energy=energy, decay_per_hop=decay_per_hop, floor=floor, hop_budget=hop_budget,
    )
    return result.activation.get(target, 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Aggregation over fresh instances
# ─────────────────────────────────────────────────────────────────────────────

def run_trials(
    spec_factory: Callable[[], GraphInstance],
    n: int,
    *,
    cue_name: str,
    target_name: str,
    **knobs,
) -> Dict[str, object]:
    """Aggregate the readout over `n` freshly-built instances of the same spec.

    `spec_factory` is a zero-argument callable that returns a NEW GraphInstance each time
    (a fresh store with fresh uuid4 IDs). For each instance we translate the cue/target
    content names to that instance's IDs and measure `retrieval_strength` (forwarding any
    activation `knobs`). We return per-condition aggregates:

        {"n", "values", "mean", "min", "max", "spread"}    (spread = max - min)

    Because the graph is built deterministically (simulated clock) and the engine is
    proven invariant to the uuid4/set-order randomness that DOES differ between builds,
    every trial returns the same value: `spread` should be exactly 0.0. We report it
    rather than assume it — a non-zero spread would be a determinism leak to surface, not
    hide. This makes `run_trials` double as a determinism probe while serving as the
    means/spread aggregator the experiments report.
    """
    values: List[float] = []
    for _ in range(n):
        inst = spec_factory()
        v = retrieval_strength(inst.store, inst.ids[cue_name], inst.ids[target_name], **knobs)
        values.append(v)

    if not values:
        return {"n": 0, "values": [], "mean": 0.0, "min": 0.0, "max": 0.0, "spread": 0.0}

    lo, hi = min(values), max(values)
    return {
        "n": n,
        "values": values,
        "mean": sum(values) / len(values),
        "min": lo,
        "max": hi,
        "spread": hi - lo,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Small spec builders shared by the experiments (kept here so the readout, the
# construction, and the topology all live behind one reusable surface)
# ─────────────────────────────────────────────────────────────────────────────

def star_spec(fan: int, *, source: str = "S", strength_count: int = 3,
              target_prefix: str = "T") -> Spec:
    """A single source `source` linked to `fan` target leaves, ALL edges crossed
    `strength_count` times (equal strength). Targets are named T1..T{fan}. This is the
    controlled fan stimulus: the only thing that varies with `fan` is the number of
    out-roads on the source; every edge is identical and every target is a leaf."""
    targets = [f"{target_prefix}{i}" for i in range(1, fan + 1)]
    return {
        "nodes": [source] + targets,
        "edges": [(source, t, strength_count) for t in targets],
    }


# ─────────────────────────────────────────────────────────────────────────────
# ADDITIVE (Phase 2B): one-spread, many-reads readout.
#
# This is added for the priming study and does NOT change any 2A function above.
# `retrieval_strength` answers "activation at ONE target"; on a large graph (SWOW),
# a priming prime has several targets (one per condition) and re-spreading once per
# target would be wasteful AND would re-do identical work. `read_targets` runs the
# SAME `spread_activation` call exactly ONCE from the cue and reads several targets
# out of the one result — so for any single target it returns the IDENTICAL value
# `retrieval_strength` would (a test asserts this equivalence). Still a pure read.
# ─────────────────────────────────────────────────────────────────────────────

def read_targets(
    store: SubstrateStore,
    cue: str,
    targets,
    *,
    energy: float = DEFAULT_SEED_ENERGY,
    decay_per_hop: float = DEFAULT_DECAY_PER_HOP,
    floor: float = DEFAULT_FLOOR,
    hop_budget: int = DEFAULT_HOP_BUDGET,
):
    """Spread once from `cue`; read each NodeID in `targets`. Pure read.

    Returns a dict:
        {
          "activation":      {target_id: activation_float, ...},  # 0.0 if unreached
          "outgoing_total":  float,   # sum of activation transmitted on the cue's own
                                      # out-roads (the prime's total outgoing activation),
                                      # used as the denominator for the SECONDARY normalized
                                      # readout. Read from result.flow on the cue's out-roads.
          "reached":         int,     # size of the reached set (observability)
        }

    The single per-target value equals exactly what `retrieval_strength(store, cue,
    target, ...)` returns for the same knobs — `read_targets` just amortizes one spread
    over many targets. `outgoing_total` is computed from the spread's recorded per-edge
    `flow` (what each out-road actually transmitted), so it reflects the same event, not a
    separate recomputation.
    """
    result = spread_activation(
        store, cue,
        energy=energy, decay_per_hop=decay_per_hop, floor=floor, hop_budget=hop_budget,
    )
    activation = {t: result.activation.get(t, 0.0) for t in targets}

    # outgoing_total = sum of activation transmitted on the cue's own out-roads.
    #
    # DETERMINISM. This comment named the wrong cause for a month and the error was
    # load-bearing, so it is corrected here rather than deleted (D-014, SPEC-0c §2.4).
    #
    #   WRONG, as originally written: "roads_from yields road IDs in set-iteration order
    #   over uuids, WHICH DEPENDS ON PYTHONHASHSEED."
    #
    #   RIGHT: the order depended on the uuid4 values themselves, which are freshly random
    #   in every process. Pinning PYTHONHASHSEED therefore never controlled it — the
    #   nondeterminism reproduces at a FIXED seed. That misattribution is why the project
    #   swept a hash-seed axis for a month against a defect no seed could perturb, and why
    #   this file's local workaround was never promoted into the engine: the hazard looked
    #   like it belonged to an environment variable rather than to the substrate.
    #
    # The hazard itself was real and is stated correctly below: float addition is not
    # associative, so summing in an unstable order can differ in the last ULP across
    # processes. Brick 0c fixes it at the source — store adjacency is now insertion-ordered
    # and the engine's accumulator uses math.fsum — which makes the sort below unnecessary.
    # It is kept because it is harmless and because removing experiment code is not that
    # brick's business. The multiset of flow values is identical across builds (equal edge
    # strengths on a simulated clock), so this sum is byte-identical regardless.
    flows = [result.flow.get(road_id, 0.0) for road_id in store.roads_from(cue)]
    flows.sort()
    outgoing_total = sum(flows)
    return {
        "activation": activation,
        "outgoing_total": outgoing_total,
        "reached": len(result.activation),
    }
