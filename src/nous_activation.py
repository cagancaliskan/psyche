"""
Nous — Spreading Activation  (first cognitive operation)

The substrate store HOLDS memory. This is the first operation that THINKS across it:
start from a seed node, radiate activation outward along roads, and report what lit
up and how strongly. It is the raw material the cognitive cycle's coalitions will
later be built from — "what is reachable from here, and how alive is each thing."

DESIGN DECISIONS (settled before building, in planning review):

  PURE READ.        Activation never mutates the substrate. This is non-negotiable —
                    and not merely for reads/writes hygiene. Automatic strengthening
                    on activation would BYPASS THE PLASTICITY BUDGET: reinforcement
                    is supposed to be a gated, metabolically-limited event (tagging +
                    capture under neuromodulation). If spreading activation potentiated
                    every road it touched, thinking would reinforce for free and steal
                    the job neuromodulation owns. So activation (what lights up) and
                    consolidation (what gets reinforced) are DIFFERENT EVENTS. This
                    function only reads. Reinforcement is a separate, gated act.

  SETTLING, HOP-LAYERED & DETERMINISTIC. Activation that converges on a node from
                    several paths SUMS — a node lit from three directions is more
                    active, and that convergence is half of what makes this cognitive.
                    Implemented as a radiating wave expanded in HOP LAYERS: all hop-k
                    contributions are accumulated before any hop-k node expands, so each
                    node expands carrying the full sum of all paths of length ≤ its
                    settle hop, and expands exactly once. This is option (a) single-
                    expansion, made DETERMINISTIC: the result depends only on the graph,
                    never on expansion order. The accepted approximation is principled —
                    only STRICTLY LONGER paths' ripples are dropped ("the long way around
                    doesn't propagate further") — not arbitrary. Equal-length convergence
                    is EXACT. Termination: at most hop_budget layers, each node settles
                    once. (Earlier drafts used an activation-priority heap; that made
                    which ripple gets dropped depend on incidental edge-strength ordering
                    — nondeterministic for no cognitive reason. A radiating wave is hop-
                    ordered by nature; this is both the truer model and the stable one.)

  OUT-ROADS ONLY (v1). Spread follows directed out-roads (what the seed points to).
                    Backward spread along in-roads is a deliberate later addition if
                    association turns out to feel too one-way.

  TWO ATTENUATORS, DISTINCT ON PURPOSE:
                    road.strength = EDGE CONDUCTANCE (a property of the connection: a
                      weak road carries less of whatever reaches it).
                    decay_per_hop = GLOBAL DISTANCE PENALTY (a property of the spread:
                      activation weakens with cognitive distance regardless of any
                      single road's strength).
                    Both exist for different reasons; keep the story clear when tuning.

  CLOSED ROADS ARE LEAKY, NOT INERT. A closed road is a high-resistance barrier, not a
                    wall: ordinary activation cannot cross, but activation above a
                    breakthrough threshold leaks through, heavily attenuated. This models
                    intrusive recall — avoided material that a strong enough cue reaches
                    anyway. The whole rule lives behind ONE function, `closed_transmission`,
                    so it is a single swappable policy. Its constants are UNCALIBRATED
                    GUESSES (you cannot calibrate them until activation is driven by real
                    salience from the cognitive cycle); the test pins the qualitative
                    regime, not the magnitudes. PROVISIONAL ON PROBATION: nothing
                    downstream may depend on these numbers, only on "closed = leaky".

  LOCALITY.         The hop budget and activation floor keep the spread in the seed's
                    neighborhood — never a whole-graph wave. This is what makes the
                    operation affordable every cognitive cycle in pure Python.

Pure Python standard library. Reads the SubstrateStore through its public surface only.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional

from nous_store import SubstrateStore, NotFound


# ─────────────────────────────────────────────────────────────────────────────
# Tunable parameters — FIRST-PASS VALUES, NOT CALIBRATED
# ─────────────────────────────────────────────────────────────────────────────
# These produce the right *qualitative* behavior (activation attenuates, converges,
# stays local; closed roads block weak cues and leak strong ones). Real values await
# a running cognitive cycle that drives activation with real salience. Do not let any
# later layer depend on these magnitudes.

DEFAULT_SEED_ENERGY = 1.0      # activation injected at the seed
DEFAULT_DECAY_PER_HOP = 0.65   # global distance penalty per hop (0..1)
DEFAULT_FLOOR = 0.02           # below this, activation is not propagated further
DEFAULT_HOP_BUDGET = 6         # max distance from seed (locality guard)

# Closed-road breakthrough — QUARANTINED uncalibrated guesses.
CLOSED_BREAKTHROUGH_THRESHOLD = 0.50  # incoming activation must exceed this to leak
CLOSED_LEAK_FRACTION = 0.15           # ...and then only this fraction passes


def closed_transmission(incoming: float, road) -> float:
    """The single, swappable policy for what crosses a CLOSED road.

    Closed = leaky, not inert. Below the breakthrough threshold, nothing passes (the
    barrier holds). Above it, a small attenuated fraction leaks through — intrusive
    recall: a strong enough cue reaches avoided material anyway.

    Constants are uncalibrated; this returns a *fraction* of `incoming` that survives
    the closed road, to be further attenuated by conductance/distance like any edge.

    CALIBRATION NOTE (for when a real cognitive cycle drives this, not now): `incoming`
    is absolute activation, which depends on seed energy and the road's distance from
    the seed. So "a strong cue breaks through" currently means, more precisely, "the
    closed road sits near a high-energy seed." That is acceptable under breakthrough-
    on-probation, but at calibration time decide whether the threshold belongs in
    NORMALIZED units (e.g. fraction of the seed energy, or of the node's own activation)
    rather than absolute — otherwise breakthrough is governed more by closed-road
    PLACEMENT than by genuine salience.
    """
    if incoming <= CLOSED_BREAKTHROUGH_THRESHOLD:
        return 0.0
    return CLOSED_LEAK_FRACTION


# ─────────────────────────────────────────────────────────────────────────────
# Result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ActivationResult:
    """What lit up, and how. `activation` maps NodeID -> final accumulated activation.
    `hops` maps NodeID -> the distance at which it was settled (for inspection).
    `broke_through` lists roads where a closed barrier leaked (intrusive recall events),
    for observability — so we can SEE breakthrough happen rather than infer it.

    `flow` records what the spread ACTUALLY DID, edge by edge: RoadID -> the activation
    that road transmitted (after all attenuation, summed if the road's source expanded
    carrying contributions from multiple paths — though under hop-layered single-
    expansion a road transmits once, at its source's settle hop). This is distinct from
    static store topology: a road that exists but carried no activation is NOT in flow;
    a blocked closed road that transmitted nothing is NOT in flow; a closed road that
    leaked IS in flow (with its attenuated value). Downstream consumers that need to
    know "which connections the thought actually used" (e.g. coalition binding) must
    read `flow`, not the store's edges — because binding on raw topology ignores both
    closure and what the spread did."""
    seed: str
    activation: Dict[str, float]
    hops: Dict[str, int]
    broke_through: List[str]            # RoadIDs that leaked despite being closed
    flow: Dict[str, float] = field(default_factory=dict)  # RoadID -> activation transmitted

    def ranked(self) -> List[tuple]:
        """Reached nodes as (node_id, activation), most active first (seed excluded)."""
        return sorted(
            ((n, a) for n, a in self.activation.items() if n != self.seed),
            key=lambda kv: kv[1], reverse=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# The operation
# ─────────────────────────────────────────────────────────────────────────────

def spread_activation(
    store: SubstrateStore,
    seed_node: str,
    *,
    energy: float = DEFAULT_SEED_ENERGY,
    decay_per_hop: float = DEFAULT_DECAY_PER_HOP,
    floor: float = DEFAULT_FLOOR,
    hop_budget: int = DEFAULT_HOP_BUDGET,
    normalization_sigma: Optional[float] = None,
) -> ActivationResult:
    """Radiate activation outward from `seed_node`. Pure read — mutates nothing.

    Returns an ActivationResult: the set of reached nodes with accumulated activation,
    the hop distance each was settled at, and any closed-road breakthroughs observed.
    """
    if not store.exists(seed_node):
        raise NotFound(f"seed node {seed_node}")

    # accumulated activation arriving at each node (convergent paths SUM here)
    activation: Dict[str, float] = {seed_node: energy}
    settled_hops: Dict[str, int] = {}
    broke_through: List[str] = []
    flow: Dict[str, float] = {}   # RoadID -> activation transmitted (what the spread did)

    # HOP-LAYERED single-expansion (option (a), made deterministic).
    #
    # We expand the graph in waves by hop distance: drain ALL hop-k contributions
    # before expanding any hop-k node. Consequence: every node expands carrying the
    # full sum of all paths of length <= its settle hop. A node expands exactly once
    # (at the first hop it is reached), so there is no double-counting — and because a
    # whole layer's accumulation completes before that layer expands, the only ripples
    # ever dropped are from STRICTLY LONGER paths (a node first reached at hop k does
    # not receive, into its onward propagation, contributions that only arrive via
    # hop > k paths).
    #
    # Why hop-layers and not an activation-priority heap? Two reasons, both learned the
    # hard way:
    #   1. Determinism. With a best-first heap, WHICH late ripple gets dropped is
    #      decided by tie-ordering and tiny strength differences — so two near-identical
    #      graphs could yield qualitatively different post-convergence activation for
    #      reasons that are not cognitive. Hop-layering removes that wobble entirely:
    #      the result depends only on the graph, never on pop order.
    #   2. Principled approximation. "Long-way-around contributions don't ripple
    #      further" is a meaningful rule; "whichever parent happened to pop later
    #      doesn't ripple" is an arbitrary one. Equal-length convergence is now EXACT.
    #
    # A radiating wave is hop-ordered by nature, so this is also the truer model. The
    # activation-priority heap was a best-first reflex imported where ordering is not
    # load-bearing for correctness but actively introduces nondeterminism.
    #
    # (If a future locality prune wants "expand only the top-K most active nodes," that
    # can be done WITHIN a hop layer — it does not require global priority ordering.)

    # current_layer: nodes first reached at this hop, with the activation they carried
    # at the moment of first arrival is NOT used; we expand using their FULL accumulated
    # activation, which is complete for paths <= this hop once the layer is assembled.
    current_layer: List[str] = [seed_node]
    settled_hops[seed_node] = 0

    for hop in range(hop_budget + 1):
        if not current_layer:
            break
        next_layer_set: Dict[str, None] = {}  # ordered set of nodes newly reached

        # FREEZE the layer's expansion values before ANY node in the layer expands.
        # This is what makes the spread truly order-independent. Without it, a node
        # expands reading the LIVE activation[node], which a same-hop sibling may have
        # just incremented via an intra-layer edge (b→c with b,c both at this hop). Then
        # whether b or c expands first — which comes from iterating a set of uuid
        # strings, hashed with a per-process random seed — changes the result across
        # process runs. Freezing makes every node in the layer expand from its
        # settled-at-this-hop value; an intra-layer edge's contribution lands in the
        # target's accumulation and only propagates onward in the NEXT layer. That is
        # exactly the documented approximation ("strictly-longer-path ripples are
        # dropped" — a→b→c→f is a length-3 path to f and is correctly not propagated as
        # if it were length-2), now enforced even in the presence of same-hop edges.
        #
        # After this, accumulation is an order-independent commutative sum, and
        # expansion reads only this frozen snapshot — so there is no remaining place
        # where live-mutation order can leak into a result. This closes the
        # order-dependence thread, not merely one more layer of it.
        frozen = {node: activation[node] for node in current_layer}

        for node in current_layer:
            node_act = frozen[node]  # value as settled at THIS hop — not live
            if hop >= hop_budget:
                continue  # locality guard: settle but do not expand past the budget

            # SPEC-0b2 overlay: total outgoing conductance of this source, used only when
            # normalization is enabled. math.fsum so the sum is exactly rounded and
            # therefore order-independent (no ULP leak from container iteration order).
            out_total = 0.0
            if normalization_sigma is not None:
                out_total = math.fsum(
                    store.get_road(r).strength for r in store.roads_from(node)
                )

            for road_id in store.roads_from(node):
                road = store.get_road(road_id)  # pure decayed VIEW; nothing mutated

                outgoing = node_act
                if road.closed:
                    frac = closed_transmission(outgoing, road)
                    if frac <= 0.0:
                        continue  # barrier holds; weak cue blocked
                    outgoing = outgoing * frac
                    broke_through.append(road_id)  # observable intrusive-recall event

                # two distinct attenuators:
                #   edge conductance (road.strength) — property of the connection
                #   global distance penalty (decay_per_hop) — property of the spread
                transmitted = outgoing * road.strength * decay_per_hop
                if normalization_sigma is not None:
                    # Divisive normalization (Carandini & Heeger canonical form):
                    # this road's drive is divided by sigma plus the COMPETING
                    # conductance out of the same source. sigma -> inf recovers the
                    # unnormalized engine exactly; a lone out-road is never attenuated
                    # (competing == 0 => factor 1.0) at any sigma.
                    competing = out_total - road.strength
                    if competing > 0.0:
                        transmitted *= normalization_sigma / (
                            normalization_sigma + competing
                        )
                if transmitted < floor:
                    continue  # too faint to matter (also aids locality)

                target = road.target_id
                # convergent activation SUMS at the target
                activation[target] = activation.get(target, 0.0) + transmitted
                # record what this edge ACTUALLY transmitted — the flow. Under hop-
                # layered single-expansion a road's source expands once, so a road
                # transmits once; we sum defensively in case of any future re-traversal.
                flow[road_id] = flow.get(road_id, 0.0) + transmitted
                # a node settles at the FIRST hop it is reached; later (longer) paths
                # still sum into its value but do not change its settle hop or re-expand
                if target not in settled_hops:
                    settled_hops[target] = hop + 1
                    next_layer_set[target] = None

        current_layer = list(next_layer_set.keys())

    return ActivationResult(
        seed=seed_node, activation=activation, hops=settled_hops,
        broke_through=broke_through, flow=flow,
    )
