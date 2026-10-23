"""
Psyche — Multi-Source Activation Field

WHY THIS EXISTS (the reframe that dissolves a structural dead-end):

Coalition formation first tried to segment a SINGLE-seed spread into coalitions. Two
segmentation rules were tried — connected-components, then flow-magnitude cut — and
both collapsed to the same failure: they keyed off DISTANCE FROM THE SEED rather than
community structure. The reason is structural, not tunable: a single seed produces ONE
activation peak and monotonically-decaying flow, so distance is the only strong signal
present, and every segmentation principle applied to one monotonic peak keys off it.
Flow-magnitude is even actively anti-correlated with community membership near the seed
(a bridge edge adjacent to the seed carries MORE flow than distant intra-cluster edges,
so it is never cut while genuine internal edges are).

The real cognitive architecture (GWT/LIDA) never has a single activation source. The
ATTEND phase consumes what is active across MULTIPLE simultaneous sources at once — the
current percept, the active goals, the prevailing emotional salience. Multiple sources
produce multiple GENUINE activation peaks, and segmentation-around-peaks then becomes
natural and meaningful: a coalition is the territory of one active concern, and a node
bridging two concerns goes to whichever pulls it harder — so the seam falls naturally
BETWEEN centers instead of being an artificial cut in one blob.

So the question upstream of the segmentation algorithm was "single seed or multi-source
field?", and the answer is multi-source. This module builds that field, reusing the
proven, deterministic single-source `spread_activation` primitive unchanged.

WHAT IT DOES:
  - Run `spread_activation` once per source (each result is a pure, deterministic
    function of its seed; the per-source attribution is exactly what we need).
  - Assemble a FIELD: for each node, how strongly each source activated it, and which
    source DOMINATES (activates it most). The dominant source is the node's "basin".
  - Total activation at a node is the sum across sources (genuine convergence: a node
    pulled by several concerns is more active — the same summation principle as within
    a single spread, now across sources).

This is multi-source watershed in spirit: basins around peaks, seams where influence is
balanced. Coalition formation then groups by basin instead of cutting by distance.

DETERMINISM: each per-source spread is already deterministic (hop-layered, frozen
layers). Dominant-source assignment ties are broken on the source's `creation_seq`
(stable, never the random uuid) — so the whole field is deterministic given store state.

PURE READ: composes pure-read spreads; mutates nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional

from psyche_store import SubstrateStore
from psyche_activation import (
    spread_activation, ActivationResult,
    DEFAULT_SEED_ENERGY, DEFAULT_DECAY_PER_HOP, DEFAULT_FLOOR, DEFAULT_HOP_BUDGET,
)


@dataclass
class ActivationField:
    """The multi-source activation field. The input coalition formation consumes when
    it groups by basin rather than cutting one spread by distance.

    per_source : SourceID -> (NodeID -> activation from that source)
    total      : NodeID -> summed activation across all sources (convergence)
    dominant   : NodeID -> the SourceID that activated it most (its basin)
    sources    : the source NodeIDs, in the order given
    flow       : merged per-edge flow across all source spreads (RoadID -> summed flow),
                 carried through for any consumer that needs what actually transmitted
    broke_through : merged breakthrough RoadIDs across all source spreads
    results    : the underlying per-source ActivationResults (for inspection)
    """
    per_source: Dict[str, Dict[str, float]]
    total: Dict[str, float]
    dominant: Dict[str, str]
    sources: List[str]
    flow: Dict[str, float] = field(default_factory=dict)
    broke_through: List[str] = field(default_factory=list)
    results: Dict[str, ActivationResult] = field(default_factory=dict)

    def basin(self, source_id: str) -> Set[str]:
        """The set of nodes whose dominant source is `source_id`."""
        return {n for n, d in self.dominant.items() if d == source_id}


def build_activation_field(
    store: SubstrateStore,
    sources: List[str],
    *,
    energy: float = DEFAULT_SEED_ENERGY,
    decay_per_hop: float = DEFAULT_DECAY_PER_HOP,
    floor: float = DEFAULT_FLOOR,
    hop_budget: int = DEFAULT_HOP_BUDGET,
    source_energies: Optional[Dict[str, float]] = None,
) -> ActivationField:
    """Run a spread from each source and assemble the multi-source field.

    `source_energies` optionally gives per-source starting energy (a percept may be
    more insistent than a background goal); absent, every source gets `energy`. Pure
    read; deterministic given store state.
    """
    # de-duplicate sources while preserving order (a node given twice is one source)
    seen_src: Set[str] = set()
    ordered_sources: List[str] = []
    for s in sources:
        if s not in seen_src and store.exists(s):
            seen_src.add(s)
            ordered_sources.append(s)

    per_source: Dict[str, Dict[str, float]] = {}
    results: Dict[str, ActivationResult] = {}
    merged_flow: Dict[str, float] = {}
    merged_breakthrough: List[str] = []

    for src in ordered_sources:
        e = (source_energies or {}).get(src, energy)
        res = spread_activation(
            store, src, energy=e, decay_per_hop=decay_per_hop,
            floor=floor, hop_budget=hop_budget,
        )
        per_source[src] = dict(res.activation)
        results[src] = res
        for rid, fv in res.flow.items():
            merged_flow[rid] = merged_flow.get(rid, 0.0) + fv
        merged_breakthrough.extend(res.broke_through)

    # total activation per node = sum across sources (convergence across concerns)
    total: Dict[str, float] = {}
    for src in ordered_sources:
        for node, act in per_source[src].items():
            total[node] = total.get(node, 0.0) + act

    # dominant source per node: the source that activated it most. Ties broken on the
    # source's creation_seq (stable), never the uuid — so assignment is deterministic.
    src_seq: Dict[str, int] = {
        s: store.get_node(s).creation_seq for s in ordered_sources
    }
    dominant: Dict[str, str] = {}
    for node in total:
        best_src: Optional[str] = None
        best_act = -1.0
        best_seq = 0
        # iterate sources in a deterministic order (by creation_seq) for tie stability
        for src in sorted(ordered_sources, key=lambda s: src_seq[s]):
            a = per_source[src].get(node, 0.0)
            if a > best_act or (a == best_act and (best_src is None or src_seq[src] < best_seq)):
                best_src = src
                best_act = a
                best_seq = src_seq[src]
        if best_src is not None:
            dominant[node] = best_src

    return ActivationField(
        per_source=per_source,
        total=total,
        dominant=dominant,
        sources=ordered_sources,
        flow=merged_flow,
        broke_through=merged_breakthrough,
        results=results,
    )
