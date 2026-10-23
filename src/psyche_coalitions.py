"""
Psyche — Coalition Formation  (the ATTEND phase, step two of the cognitive cycle)

Spreading activation says WHAT lit up and how strongly. Coalition formation is the
next step: group the co-activated, associatively-linked nodes into candidate
COALITIONS — clusters that hang together — which then compete in the BROADCAST phase
for the global workspace. This is the bridge between raw activation and the workspace
competition (Global Workspace Theory; LIDA's attention-codelet coalition forming).

DESIGN STANCE (and what is deliberately left for execution to decide):

  The three real design forks — what BINDS a coalition, how its STRENGTH is scored,
  and whether an intrusive (breakthrough) node forms its own coalition or attaches —
  are NOT settled speculatively here. This file makes the simplest defensible FIRST
  choice for each and lets behavior correct it. What is NOT left to chance is
  determinism: clustering is the classic home of hidden order-dependence, so the
  approach is chosen to be deterministic BY CONSTRUCTION, and the adversarial
  determinism test ships with this first commit.

  BINDING (redesigned — flow-based segmentation): connectivity-based binding was
    structurally degenerate. Every co-activated node got its activation by being
    reached from the seed through carried edges, so the co-activated subgraph is
    connected BY CONSTRUCTION (seed-rooted) — and connected-components on a connected
    graph is always ONE component. A single-seed spread would therefore essentially
    always yield one coalition, leaving the downstream workspace competition with one
    contestant and nothing to compare. So binding must SUBDIVIDE the connected
    activated region, not merely find its (single) component.

    The new principle: a coalition is a group of co-activated nodes connected by STRONG
    carried FLOW. The activated region is cut at its WEAK flow edges. Concretely:
      - read the spread's `flow` (RoadID -> activation transmitted), NOT static store
        topology — this is what Finding 2 requires, and it respects closure for free
        (a blocked road carries no flow, so it never binds; a leaked road carries
        attenuated flow, so it binds weakly);
      - keep only flow edges at or above a cut threshold set RELATIVE to the spread
        (a fraction of the maximum observed flow), so the principle scales with the
        spread rather than depending on an absolute magic value;
      - coalitions are the connected components OF THAT THINNED graph. Cutting weak
        edges breaks the one big component into several — subdividing a connected
        region, which is exactly what was needed. Components remain order-independent,
        so this stays deterministic by construction.
    This must demonstrably produce MORE THAN ONE coalition on a real single-seed
    spread; that property is shipped as an explicit test, because the whole competition
    downstream depends on it.

  STRENGTH (first choice): the sum of member activations. A coalition is strong if it
    has many active members or a few very active ones — the comparison the workspace
    competition will want. Refinable once the competition exists and says what it needs.

  INTRUSIVE NODES (flagged, not forced): a node reached ONLY via a closed-road
    breakthrough arrived against resistance — it is structurally different from a node
    reached over open roads. We MARK which nodes are breakthrough-reached and let the
    build reveal whether they cluster with their neighbors or stand apart. We do not
    decide their coalition membership by fiat here.

  DETERMINISM (settled, non-negotiable): the output is a deterministic function of the
    ActivationResult. Component discovery uses no hash-randomized iteration order to
    decide membership (membership is topological); any ordering that affects OUTPUT
    (e.g. sorting coalitions for presentation, choosing a representative) is done by an
    EXPLICIT total order — activation then a stable tiebreak — never by set iteration.

Pure Python standard library. Reads the SubstrateStore and an ActivationResult; the
store is read PURELY (it is already a pure-read consumer — coalition formation mutates
nothing, preserving the plasticity-budget separation activation established).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Dict, List, Set, Optional

from psyche_store import SubstrateStore
from psyche_activation import ActivationResult
from psyche_field import ActivationField


# ─────────────────────────────────────────────────────────────────────────────
# Tunable parameters — FIRST-PASS VALUES, NOT CALIBRATED
# ─────────────────────────────────────────────────────────────────────────────
# As with activation, these produce the right qualitative behavior and await a real
# cognitive cycle for calibration. Do not let later layers depend on the magnitudes.

DEFAULT_COHERENCE_FLOOR = 0.05   # min activation for a node to join a coalition at all
DEFAULT_FLOW_CUT_FRACTION = 0.35 # flow edges below this fraction of MAX flow are cut
                                 # (relative, so it scales with the spread; uncalibrated)


# ─────────────────────────────────────────────────────────────────────────────
# Coalition
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Coalition:
    """A candidate cluster competing for the workspace. `members` are NodeIDs with
    their activation. `strength` is the score the competition compares. `intrusive`
    flags whether any member was reached only via a closed-road breakthrough — the
    structural mark of avoided material that surfaced anyway.

    `_seq` maps each member NodeID -> its creation_seq (the stable formation-order
    integer from Layer 1). This is what tiebreaks use, NOT the NodeID itself: NodeIDs
    are uuid4 and are regenerated every process run, so any ordering that fell back to
    the id would be nondeterministic across processes. creation_seq is stable (it is
    part of persisted store state), so ordering on it is reproducible.
    """
    members: Dict[str, float]                 # NodeID -> activation
    strength: float
    intrusive: bool = False
    breakthrough_members: Set[str] = field(default_factory=set)  # NodeIDs reached via leak
    _seq: Dict[str, int] = field(default_factory=dict)           # NodeID -> creation_seq

    def representative(self) -> str:
        """The most-active member, by an EXPLICIT total order: activation desc, then
        creation_seq asc as a STABLE tiebreak (never the random uuid). Deterministic
        across processes. This is the node that would 'name' the coalition."""
        return min(
            self.members,
            key=lambda n: (-self.members[n], self._seq.get(n, 0)),
        )

    def canonical_member_order(self) -> List[str]:
        """Members in a stable order (creation_seq asc) — for deterministic display
        and serialization, independent of uuid values."""
        return sorted(self.members, key=lambda n: self._seq.get(n, 0))

    def size(self) -> int:
        return len(self.members)


# ─────────────────────────────────────────────────────────────────────────────
# Coalition formation
# ─────────────────────────────────────────────────────────────────────────────

def form_coalitions(
    store: SubstrateStore,
    result: ActivationResult,
    *,
    coherence_floor: float = DEFAULT_COHERENCE_FLOOR,
    flow_cut_fraction: float = DEFAULT_FLOW_CUT_FRACTION,
) -> List[Coalition]:
    """Group the co-activated, linked nodes of an ActivationResult into coalitions.

    Pure read. Deterministic function of `result` (and the store's topology).

    Returns coalitions sorted strongest-first by an explicit total order, so the list
    order itself is deterministic and ready for the workspace competition to consume.
    """
    activation = result.activation

    # 1. The co-activated set: nodes at or above the coherence floor. Sorted into an
    #    explicit order so nothing downstream depends on dict/set iteration order.
    co_activated: List[str] = sorted(
        (n for n, a in activation.items() if a >= coherence_floor)
    )
    co_set: Set[str] = set(co_activated)
    if not co_set:
        return []

    # 2. Which nodes were reached ONLY via a closed-road breakthrough. A breakthrough
    #    road's TARGET is the node that was reached against resistance. (A node also
    #    reachable by an open road is not purely intrusive; we mark membership of the
    #    breakthrough target set and resolve "purely intrusive" structurally below.)
    breakthrough_targets: Set[str] = set()
    for road_id in result.broke_through:
        # the road still exists and we only need its target id; read purely
        try:
            road = store.get_road(road_id, apply_decay=False)
        except Exception:
            continue
        breakthrough_targets.add(road.target_id)

    # 3. Build the binding graph from FLOW, not static topology. Two co-activated nodes
    #    bind only if a road between them carried flow AT OR ABOVE the cut threshold.
    #    The threshold is RELATIVE: a fraction of the maximum observed flow, so it
    #    scales with the spread. This respects closure for free (a blocked road has no
    #    flow entry, so it can never bind) and is driven by what the spread actually did.
    #    Cutting the weak-flow edges is what subdivides the otherwise-connected region.
    flow = result.flow
    # consider only flow edges whose BOTH endpoints are co-activated
    relevant: List[tuple] = []  # (road_id, src, tgt, flow_value)
    max_flow = 0.0
    for road_id in sorted(flow.keys()):             # sorted → deterministic
        try:
            road = store.get_road(road_id, apply_decay=False)
        except Exception:
            continue
        if road.source_id in co_set and road.target_id in co_set:
            fv = flow[road_id]
            relevant.append((road_id, road.source_id, road.target_id, fv))
            if fv > max_flow:
                max_flow = fv

    cut = flow_cut_fraction * max_flow if max_flow > 0 else 0.0

    adj: Dict[str, Set[str]] = {n: set() for n in co_set}
    for road_id, src, tgt, fv in relevant:
        if fv >= cut and fv > 0.0:
            adj[src].add(tgt)
            adj[tgt].add(src)                       # undirected for binding purposes

    # 4. Connected components = coalitions. Order-INDEPENDENT: the partition into
    #    components is a function of the graph alone. We iterate seeds in sorted order
    #    purely so the RETURNED structure is built deterministically; the partition
    #    itself would be identical under any iteration order.
    seen: Set[str] = set()
    coalitions: List[Coalition] = []
    for seed in co_activated:                   # sorted → deterministic build order
        if seed in seen:
            continue
        # iterative DFS/BFS over the undirected co-activated subgraph
        stack = [seed]
        component: Set[str] = set()
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            seen.add(node)
            # push neighbors in sorted order for a deterministic traversal sequence
            for nb in sorted(adj[node]):
                if nb not in component:
                    stack.append(nb)

        members = {n: activation[n] for n in component}
        seq = {n: store.get_node(n).creation_seq for n in component}
        strength = math.fsum(members.values())
        bt_here = component & breakthrough_targets
        coalitions.append(Coalition(
            members=members,
            strength=strength,
            intrusive=bool(bt_here),
            breakthrough_members=bt_here,
            _seq=seq,
        ))

    # 5. Sort coalitions strongest-first by an EXPLICIT, FULLY STABLE total order:
    #    strength desc, then size desc, then the coalition's minimum member
    #    creation_seq asc. Every key is intrinsic and reproducible — none falls back
    #    to a uuid, so the ordering is identical across process runs. (creation_seq is
    #    the stable formation-order integer from Layer 1, precisely so identity-by-uuid
    #    never has to carry ordering.)
    def _coalition_sort_key(c: Coalition):
        min_seq = min(c._seq.values()) if c._seq else 0
        return (-c.strength, -c.size(), min_seq)

    coalitions.sort(key=_coalition_sort_key)
    return coalitions


# ─────────────────────────────────────────────────────────────────────────────
# Coalition formation from a MULTI-SOURCE field (the non-degenerate path)
# ─────────────────────────────────────────────────────────────────────────────

def form_coalitions_from_field(
    field_: ActivationField,
    store: SubstrateStore,
    *,
    coherence_floor: float = DEFAULT_COHERENCE_FLOOR,
) -> List[Coalition]:
    """Form coalitions from a multi-source ActivationField by BASIN.

    This is the non-degenerate coalition formation. Each source's basin (the nodes it
    dominates) becomes a candidate coalition — a coalition is the territory of one
    active concern (a percept, a goal, an emotional pull). A node bridging two concerns
    belongs to whichever pulled it harder, so seams fall naturally between centers
    rather than being artificial distance-cuts in one blob.

    Why this avoids the single-seed degeneracy: with multiple sources there are
    multiple genuine activation peaks, so basins correspond to real competing centers
    — not to concentric distance-shells around one peak. Validated on the adversarial
    two-community input that defeated single-seed segmentation.

    Members carry their TOTAL (summed-across-sources) activation. Strength is the sum
    of member totals. A coalition is marked intrusive if any member was reached via a
    closed-road breakthrough in any source spread. Deterministic given store state
    (basin assignment ties break on creation_seq; ordering uses creation_seq).

    Pure read.
    """
    # nodes that clear the coherence floor on their TOTAL activation
    eligible: Set[str] = {
        n for n, a in field_.total.items() if a >= coherence_floor
    }
    if not eligible:
        return []

    # breakthrough targets across all source spreads (reached against resistance)
    breakthrough_targets: Set[str] = set()
    for road_id in field_.broke_through:
        try:
            road = store.get_road(road_id, apply_decay=False)
        except Exception:
            continue
        breakthrough_targets.add(road.target_id)

    # group eligible nodes by their dominant source (basin)
    by_basin: Dict[str, Set[str]] = {}
    for node in eligible:
        src = field_.dominant.get(node)
        if src is None:
            continue
        by_basin.setdefault(src, set()).add(node)

    coalitions: List[Coalition] = []
    for src in sorted(by_basin.keys(), key=lambda s: store.get_node(s).creation_seq):
        members_set = by_basin[src]
        members = {n: field_.total[n] for n in members_set}
        seq = {n: store.get_node(n).creation_seq for n in members_set}
        strength = math.fsum(members.values())
        bt_here = members_set & breakthrough_targets
        coalitions.append(Coalition(
            members=members,
            strength=strength,
            intrusive=bool(bt_here),
            breakthrough_members=bt_here,
            _seq=seq,
        ))

    # strongest-first, fully stable order (same key as the single-source path)
    def _key(c: Coalition):
        min_seq = min(c._seq.values()) if c._seq else 0
        return (-c.strength, -c.size(), min_seq)

    coalitions.sort(key=_key)
    return coalitions
