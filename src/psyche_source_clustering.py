"""
Psyche — Source-clustering  (step 1c: a pure-read pre-processing stage)

WHAT THIS IS (and is not):

1c is a deterministic, pure-read pre-processing stage inserted BETWEEN perception and
field construction. It takes the set of sources perception emits and partitions it into
GROUPS — "merge near sources, keep far sources apart" — then hands the field builder ONE
representative seed per group instead of every raw source. It changes WHAT sources reach
the field, not the field builder's signature and not the perception surface.

WHY IT EXISTS (a structural problem the closed loop surfaced, not a guess): on real input
like "coffee in the kitchen this morning", perception lights up several same-domain
sources (coffee, kitchen, morning). When every one of those becomes its own field source,
the multi-source field fractures: the same-domain siblings split a single warm region into
competing basins. Grouping nearby sources first is the missing step.

BIOLOGICAL INSPIRATION ONLY (no fidelity claimed): nearby cues in one utterance tend to
name one concern, and a cognitive cycle should treat them as one pull rather than several
competing ones. This is loose inspiration. No biological fidelity and NO cognitive
achievement is claimed by 1c on its own (see the asserted-negative tests in the suite).

MECHANISM, NOT MEANING: this module's correctness claim is purely mechanical — the
grouping is a deterministic, pure function of stable graph state, integrity-preserving,
and scale-invariant. Whether the grouping CORRESPONDS to any externally-defined structure
(e.g. word-association communities) is a SEPARATE claim, graded by the validator against
external data, and is NOT asserted here.

ALGORITHM (single-link agglomerative clustering on a source-source proximity graph):
  1. For every unordered pair of perceived sources, compute a symmetric PROXIMITY from
     graph topology / road-strength only (the A1 signal): the maximum of the two directed
     road strengths between them, read from canonical stored state (apply_decay=False) so
     the result is a stable function of graph state, independent of wall-clock time and of
     the activation field this stage will later feed (the cleanest anti-circularity story).
  2. Keep an edge between two sources iff their proximity clears a RELATIVE threshold — a
     fraction of the maximum proximity observed in THIS run — never an absolute constant.
     Relative thresholding is what makes the partition scale-invariant.
  3. The CONNECTED COMPONENTS of the thinned graph are the source groups. This is
     single-link / transitive merging: chaining (A-B-C grouped though A-C are not directly
     near) is INTENTIONAL and documented as a limitation, with an explicit test.
  4. Each group elects one REPRESENTATIVE: highest source energy, ties broken on
     creation_seq ascending (never the uuid — uuids are regenerated per process, so any
     fallback to the id would be nondeterministic across processes; creation_seq is stable
     persisted state, so ordering on it is reproducible).

This reuses the proven determinism pattern already shipped in psyche_coalitions /
psyche_activation (sorted iteration everywhere, connected-components of a thinned graph,
every tie broken on creation_seq). The novelty budget is spent only on WHICH sources are
near each other, not on the clustering scaffolding.

Prior art (cited, not reinvented):
  - Sibson, R. (1973). SLINK: an optimally efficient algorithm for the single-link cluster
    method. (Single-link agglomerative clustering, realized here as
    connected-components-of-a-thinned-graph.)

SCOPE (asserted-negative tests pin each of these):
  - Clusters ONLY the perceived source set, never the whole substrate graph.
  - Makes NO cognitive claim on its own.
  - Chaining is intentional and documented.
  - Does NOT alter perceive() / Perception, nor build_activation_field's signature.
  - Does NOT broadcast or feed anything back into a next cycle (that is 1d).
  - The relative threshold is an UNCALIBRATED design constant; tuning it against external
    data would be circular and is forbidden.

Pure Python standard library. Reads the SubstrateStore through its public surface only;
mutates nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, FrozenSet

from psyche_store import SubstrateStore


# ─────────────────────────────────────────────────────────────────────────────
# Tunable parameter — FIRST-PASS VALUE, NOT CALIBRATED
# ─────────────────────────────────────────────────────────────────────────────
# A documented design constant, mirroring the uncalibrated relative thresholds elsewhere
# (e.g. DEFAULT_FLOW_CUT_FRACTION in psyche_coalitions). It is RELATIVE — a fraction of the
# per-run maximum proximity — so the partition is scale-invariant. It is NOT tuned against
# any external dataset; doing so against the §6.2 meaning set would be circular (forbidden
# by the spec). Nothing downstream may depend on this magnitude, only on the qualitative
# behavior "near sources merge, far sources stay apart."
DEFAULT_PROXIMITY_FRACTION = 0.35


# ─────────────────────────────────────────────────────────────────────────────
# Immutable result types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SourceGroup:
    """One group of perceived sources that clustered together.

    members        : the source NodeIDs in this group (a frozenset; order-free identity).
    representative : the elected seed for this group — highest source energy, ties broken
                     on creation_seq ascending (never the uuid).
    _seq           : NodeID -> creation_seq for the members (the stable formation-order
                     integer from Layer 1), the same convention Coalition uses so any
                     ordering is reproducible across processes.
    """
    members: FrozenSet[str]
    representative: str
    _seq: Dict[str, int] = field(default_factory=dict)

    def size(self) -> int:
        return len(self.members)

    def canonical_member_order(self) -> List[str]:
        """Members in a stable order (creation_seq asc) — deterministic display/
        serialization, independent of uuid values."""
        return sorted(self.members, key=lambda n: self._seq.get(n, 0))


@dataclass(frozen=True)
class SourceClustering:
    """The result of 1c: the ordered groups plus the seed map for the field.

    groups      : the SourceGroups, in a stable order (by representative creation_seq asc).
    group_seeds : representative NodeID -> seed energy for that group. The seed energy is a
                  FIXED, documented aggregation of the group's source energies — here the
                  MAX of the member source energies (the most insistent cue in the group
                  sets the group's pull). This map is what feeds the UNCHANGED field
                  builder; 1c changes which sources reach the field, not the builder's
                  signature.
    """
    groups: List[SourceGroup]
    group_seeds: Dict[str, float] = field(default_factory=dict)

    def representatives(self) -> List[str]:
        """Representative NodeIDs in the groups' stable order."""
        return [g.representative for g in self.groups]


# ─────────────────────────────────────────────────────────────────────────────
# Proximity (the A1 signal: graph topology / road-strength only)
# ─────────────────────────────────────────────────────────────────────────────

def _pair_proximity(store: SubstrateStore, a: str, b: str) -> float:
    """Symmetric proximity between two sources from canonical road strength only.

    proximity(a, b) = max(strength(a->b), strength(b->a)), where each strength is the
    canonical stored value (apply_decay=False) — so proximity is a stable function of
    graph state, independent of wall-clock time and of the activation field this stage
    feeds. If neither directed road exists, proximity is 0.0 (the sources are not directly
    near). Pure read.
    """
    prox = 0.0
    rid_ab = store.find_road(a, b)
    if rid_ab is not None:
        prox = max(prox, store.get_road(rid_ab, apply_decay=False).strength)
    rid_ba = store.find_road(b, a)
    if rid_ba is not None:
        prox = max(prox, store.get_road(rid_ba, apply_decay=False).strength)
    return prox


# ─────────────────────────────────────────────────────────────────────────────
# The clustering (single-link / connected-components of a thinned proximity graph)
# ─────────────────────────────────────────────────────────────────────────────

def cluster_sources(
    store: SubstrateStore,
    source_energies: Dict[str, float],
    *,
    proximity_fraction: float = DEFAULT_PROXIMITY_FRACTION,
) -> SourceClustering:
    """Partition the perceived sources into single-link groups by graph proximity.

    Inputs are loop-closed: `source_energies` is `perception.sources` (NodeID -> source
    energy) produced by perceive(); `store` is the substrate. No hand-placed sources, no
    hand-placed groupings.

    Pure read. Deterministic function of stable graph state: all iteration is sorted, and
    every tie is broken on creation_seq (never the uuid, never set/dict iteration order).

    Returns a SourceClustering: the groups in a stable order plus the `group_seeds` map
    (representative -> seed energy) that feeds the UNCHANGED field builder.
    """
    # Only sources that actually exist in the store can be clustered. Sort by creation_seq
    # so every downstream step has a stable, reproducible iteration order.
    sources: List[str] = sorted(
        (s for s in source_energies if store.exists(s)),
        key=lambda s: store.get_node(s).creation_seq,
    )

    seq: Dict[str, int] = {s: store.get_node(s).creation_seq for s in sources}

    # Degenerate sizes: 0 or 1 source needs no proximity graph.
    if not sources:
        return SourceClustering(groups=[], group_seeds={})
    if len(sources) == 1:
        only = sources[0]
        group = SourceGroup(
            members=frozenset({only}),
            representative=only,
            _seq={only: seq[only]},
        )
        return SourceClustering(
            groups=[group],
            group_seeds={only: source_energies[only]},
        )

    # 1. Proximity for every unordered pair (sorted pair iteration → deterministic).
    pair_prox: Dict[tuple, float] = {}
    max_prox = 0.0
    for i in range(len(sources)):
        for j in range(i + 1, len(sources)):
            a, b = sources[i], sources[j]
            p = _pair_proximity(store, a, b)
            pair_prox[(a, b)] = p
            if p > max_prox:
                max_prox = p

    # 2. Thin the graph: keep an edge iff proximity clears a RELATIVE threshold (a fraction
    #    of the per-run maximum proximity). Relative → scale-invariant. A zero-proximity
    #    pair (no road between them) never binds; if no pair has any proximity at all
    #    (max_prox == 0), no edges survive and every source is its own group.
    cut = proximity_fraction * max_prox  # 0.0 when max_prox == 0.0
    adj: Dict[str, Set[str]] = {s: set() for s in sources}
    for (a, b), p in pair_prox.items():
        # require strictly-positive proximity AND clearing the cut, so a no-road pair
        # (p == 0) cannot bind even when the cut degenerates to 0.0.
        if p > 0.0 and p >= cut:
            adj[a].add(b)
            adj[b].add(a)

    # 3. Connected components = groups. Order-INDEPENDENT as a partition; we iterate seeds
    #    in sorted (creation_seq) order purely so the RETURNED structure is built
    #    deterministically. (Same shape as coalition/basin formation.)
    seen: Set[str] = set()
    groups: List[SourceGroup] = []
    for seed_node in sources:                      # sorted by creation_seq
        if seed_node in seen:
            continue
        # iterative traversal over the undirected proximity subgraph
        stack = [seed_node]
        component: Set[str] = set()
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            seen.add(node)
            for nb in sorted(adj[node], key=lambda n: seq[n]):
                if nb not in component:
                    stack.append(nb)

        # 4. Representative: highest source energy, ties broken on creation_seq ascending.
        #    Realized as a min over an EXPLICIT total order (energy desc, then seq asc) so
        #    the choice never falls back to the uuid.
        representative = min(
            component,
            key=lambda n: (-source_energies[n], seq[n]),
        )
        comp_seq = {n: seq[n] for n in component}
        groups.append(SourceGroup(
            members=frozenset(component),
            representative=representative,
            _seq=comp_seq,
        ))

    # Stable group order: by representative creation_seq ascending (never the uuid).
    groups.sort(key=lambda g: seq[g.representative])

    # group_seeds: representative -> seed energy = MAX of the group's source energies
    # (documented aggregation; the most insistent cue sets the group's pull). Built in the
    # groups' stable order so the dict's insertion order is itself reproducible.
    group_seeds: Dict[str, float] = {}
    for g in groups:
        group_seeds[g.representative] = max(source_energies[m] for m in g.members)

    return SourceClustering(groups=groups, group_seeds=group_seeds)
