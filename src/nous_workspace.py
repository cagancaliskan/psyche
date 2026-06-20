"""
Nous — Workspace selection  (step 1d-i: competition + over-swallow pruning)

WHAT THIS IS (and, just as importantly, what it is NOT):

This module replaces the `think()` placeholder "the strongest coalition IS the thought"
(`coalitions[0]` in nous_perceive.py) with a real, deterministic, PURE-READ selection
step that does two things:

  1. COMPETITION (Decision A2): score the candidate coalitions by activation density
     (total activation normalized by coalition size, with a minimum-size guard so a tiny
     1-2 node coalition cannot win on density alone) and select exactly ONE winner. Ties
     break on the same fully-stable key the rest of the project uses
     (`(-score, -size, min creation_seq)`), reusing the nous_coalitions pattern — never a
     uuid, never set/dict iteration order.

  2. PRUNING (Decision C1): from the winning coalition, drop members that are NOT pulled
     toward the perceived (named) region at least as strongly as toward the unperceived
     region — a parameter-free COHESION-VALLEY / RELATIVE-ATTACHMENT WATERSHED, NOT a
     pure domain-membership rule (see "THE C1 PRUNING PRINCIPLE" below for the exact rule
     and its documented limitation). This is the over-swallow fix re-scoped from 1c: on
     "coffee in the kitchen this morning", a single warm basin reaches the work/code
     domain over the strong (n=8) coffee->work bridge; those nodes are kept OUT of the
     winning structure because work's internal cohesion (n=30) far exceeds its bridge to
     the named region (n=8) — there is a cohesion valley at the seam, so the watershed
     cuts there.

HONEST FRAMING (hard, non-negotiable — CLAUDE.md rule 1; SPEC-1d §1):

The vocabulary here — workspace, coalition, winner — is borrowed from Global Workspace
Theory (Baars 1988) and its computational descendant LIDA (Franklin et al. 2014). That
vocabulary is the ENGINEERING LINEAGE for the routing/selection structure. It is NOT a
claim of consciousness, awareness, subjective experience, or "ignition."

  - The winning coalition is A SELECTED INFORMATION STRUCTURE. It is NEVER "what the
    system is conscious of," "what the system is aware of," or "the system's experience."
  - Nothing here is a cognitive claim. Passing this module's tests proves a SELECTION
    mechanism is correct, deterministic, and pure — it proves nothing about meaning. The
    project's meaning bar lives at 1e and is graded by the validator against external
    human data, never asserted here.

SCOPE — 1d-i ONLY (the split, locked SPEC-1d §8/E):

  - 1d-i is PURE SELECTION. It mutates NOTHING: no broadcast, no feedback, no writes of
    any kind. `select_winner` is a pure read, exactly like the layers beneath it.
  - The broadcast / bounded-feedback write (Decision B1) is 1d-ii and is deliberately
    NOT implemented here. `think(..., broadcast=True)` raises NotImplementedError so the
    absence of feedback is explicit and cannot be mistaken for a built feature.

THE C1 PRUNING PRINCIPLE — a parameter-free COHESION-VALLEY / RELATIVE-ATTACHMENT
WATERSHED (and, precisely, what it is NOT):

Read this carefully, because the rule's NAME matters for honesty. 1d-i pruning is a
parameter-free cohesion-valley / relative-attachment watershed: KEEP a reached member iff
it is pulled toward the named (perceived) region AT LEAST AS STRONGLY as toward the
unnamed region; else prune. It is genuinely threshold-free and generalizes.

It is NOT pure domain-membership ("prune any domain no source named"). The two rules
agree on the locked acceptance cases but are not the same rule (see the limitation below).
The inherited 1c subtlety (SPEC-1c §7.7) is why a membership-shaped intuition is tempting:
the coffee->work bridge is STRONG (n=8), so "cut weak roads" by an absolute threshold
cannot flip this case, and tuning any threshold to make this one case pass is forbidden
(CLAUDE.md rule 5). The flip comes instead from the RELATIVE comparison below.

It is realized as a deterministic, scale-invariant WATERSHED over the winner's members,
seeded from the perceived sources (equivalently, the 1c groups, which are made of
perceived sources). This restores at the domain level the basin competition that
collapsed when 1c handed the field a single representative seed:

  - The perceived sources start labeled PERCEIVED.
  - A member adopts PERCEIVED iff its STRONGEST road (canonical road strength, either
    direction) to an already-PERCEIVED member is at least as strong as its strongest road
    to any NON-perceived member — i.e. it is pulled toward the named region at least as
    strongly as away from it. Propagation runs to a fixpoint, frozen per pass so the
    result is order-independent (the same determinism discipline the activation engine
    uses).
  - Members still unlabeled at the fixpoint were never pulled toward the named region as
    strongly as toward the unnamed region (there is a cohesion valley separating them from
    it), and are pruned.

Why this flips _small_mind without tuning: work's internal cohesion (n=30 ties to desk,
deadline, code) is far stronger than its single n=8 bridge to the perceived region, so
there is a cohesion VALLEY at the seam — work is pulled into its OWN (unnamed) community
and never reaches PERCEIVED. Why it does NOT over-correct (the anti-overcorrection
control): when the input DOES name the work domain, work/desk are perceived seeds and
propagation keeps deadline/code with them — a node in a genuinely perceived domain is
never pruned even if loosely attached.

There is NO new threshold here: pruning is a comparison of road strengths the substrate
already stores, so it inherits scale-invariance for free and adds no calibrated constant.

DOCUMENTED LIMITATION (accepted design, 2026-06-20 — shipped as an explicit asserted-
negative, test_KNOWN_LIMITATION_unnamed_domain_bridged_ge_cohesion_is_kept):

Because the rule is a cohesion valley and NOT pure domain-membership, an unnamed domain
that is bridged into the named region AT LEAST AS STRONGLY AS ITS OWN INTERNAL COHESION
has no valley at the seam and is therefore KEPT — so over-swallow can recur in exactly
that topology. This is a genuine divergence from "prune any domain no source named," and
it is recorded, not smoothed over. The divergence is ALWAYS in the SAFE direction: it is
over-INCLUSION of an unnamed domain, never over-EXCLUSION — a PERCEIVED member is never
pruned (verified across 60 random adversarial graphs in the tester's suite, and asserted
locally by the anti-overcorrection tests here). The locked §6.1 acceptance graphs all have
bridge (n=8) STRICTLY below internal cohesion (n=30), so they sit on the correct side of
the valley and prune as intended; the limitation lies OUTSIDE that acceptance scope.

Prior art (cited as structure/lineage, not as cognitive validation — SPEC-1d §9):
  - Baars (1988), A Cognitive Theory of Consciousness — one coalition wins access.
  - Franklin et al. (2014), LIDA — coalitions compete for the workspace.
  - Dehaene & Changeux (2011) — selective amplification/suppression (the selection
    STRUCTURE only).

Pure Python standard library. Reads the SubstrateStore through its public surface only;
mutates nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, FrozenSet, Set

from nous_store import SubstrateStore
from nous_field import ActivationField
from nous_coalitions import Coalition
from nous_source_clustering import SourceClustering


# ─────────────────────────────────────────────────────────────────────────────
# Tunable parameter — FIRST-PASS VALUE, NOT CALIBRATED
# ─────────────────────────────────────────────────────────────────────────────
# The minimum-size guard for the density-normalized competition (Decision A2). A
# coalition's density score divides its total activation by max(size, this) rather than
# by size, so a tiny 1-2 node coalition cannot win on density alone. This is a documented
# design constant, NOT tuned against external data; nothing downstream may depend on its
# magnitude, only on the qualitative behavior "tight intense coalitions are favored over
# sprawling ones, but a degenerate singleton cannot win purely by being small."
DEFAULT_MIN_SIZE_GUARD = 3


# ─────────────────────────────────────────────────────────────────────────────
# Immutable result type
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class WorkspaceResult:
    """The outcome of competition + pruning. A pure-read product; nothing here implies
    any state was written.

    winner         : the selected coalition AFTER pruning (members already removed), or
                     None if there were no candidates. It is a SELECTED INFORMATION
                     STRUCTURE — see the module honest-framing note; it is never "what the
                     system is conscious/aware of."
    pruned_members : NodeIDs removed from the raw winning coalition by the C1 cohesion-
                     valley watershed (members pulled toward the unnamed region more
                     strongly than toward the named one), recorded for inspection and for
                     the over-swallow test.
    ranked         : the candidate coalitions in competition order (strongest density
                     first), for inspection and determinism checks. Pre-pruning.
    raw_winner     : the top coalition BEFORE pruning (for inspection / so a test can see
                     exactly what pruning removed).
    _seq           : NodeID -> creation_seq for the winner's surviving members, the same
                     stable-ordering convention Coalition/SourceGroup use.
    """
    winner: Optional[Coalition]
    pruned_members: FrozenSet[str]
    ranked: List[Coalition]
    raw_winner: Optional[Coalition]
    _seq: Dict[str, int] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Competition (Decision A2) — density-normalized, min-size guard, stable ties
# ─────────────────────────────────────────────────────────────────────────────

def _density_score(c: Coalition, *, min_size_guard: int) -> float:
    """Activation density: total strength divided by max(size, guard). The guard keeps a
    tiny coalition from winning purely by being small. Pure function of the coalition."""
    denom = max(c.size(), min_size_guard)
    if denom <= 0:
        return 0.0
    return c.strength / denom


def _competition_key(c: Coalition, *, min_size_guard: int):
    """The fully-stable competition order: density desc, then size desc, then the
    coalition's minimum member creation_seq asc. Every key is intrinsic and reproducible;
    none falls back to a uuid — identical across process runs. Same shape as
    nous_coalitions' coalition sort key, with density swapped for raw strength."""
    min_seq = min(c._seq.values()) if c._seq else 0
    return (-_density_score(c, min_size_guard=min_size_guard), -c.size(), min_seq)


def rank_coalitions(
    coalitions: List[Coalition],
    *,
    min_size_guard: int = DEFAULT_MIN_SIZE_GUARD,
) -> List[Coalition]:
    """Rank candidate coalitions by the density competition (strongest first).

    Pure function of the coalitions. Deterministic: explicit total order, ties on
    creation_seq, never on uuid or iteration order.
    """
    return sorted(
        coalitions,
        key=lambda c: _competition_key(c, min_size_guard=min_size_guard),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pruning (Decision C1) — the perceived-domain watershed (pure read)
# ─────────────────────────────────────────────────────────────────────────────

def _strongest_road_strength(store: SubstrateStore, a: str, b: str) -> float:
    """Symmetric strongest canonical road strength between two nodes (either direction),
    read with apply_decay=False so it is a stable function of graph state. 0.0 if there is
    no road. Mirrors nous_source_clustering._pair_proximity — the same A1 signal. Pure."""
    best = 0.0
    rid = store.find_road(a, b)
    if rid is not None:
        best = max(best, store.get_road(rid, apply_decay=False).strength)
    rid = store.find_road(b, a)
    if rid is not None:
        best = max(best, store.get_road(rid, apply_decay=False).strength)
    return best


def _perceived_domain_members(
    store: SubstrateStore,
    member_ids: List[str],
    perceived_sources: Set[str],
) -> Set[str]:
    """Return the subset of `member_ids` on the PERCEIVED side of a cohesion-valley
    watershed seeded from the perceived sources. Deterministic, scale-invariant.

    This is a RELATIVE-ATTACHMENT rule, NOT pure domain-membership: a member is PERCEIVED
    iff it is itself a perceived source, OR it is pulled toward the already-PERCEIVED region
    at least as strongly as toward the not-yet-perceived region (strongest road strength to
    a PERCEIVED member >= strongest road strength to a non-PERCEIVED member). Propagation
    runs to a fixpoint, computed from a FROZEN snapshot each pass so the result is
    independent of iteration order. Pure read.

    Members NOT returned are separated from the named region by a cohesion valley (they are
    pulled toward the unnamed region more strongly). NOTE the documented limitation (module
    docstring): an unnamed community bridged into the named region AT LEAST AS STRONGLY AS
    its internal cohesion has no valley and IS returned (kept) — the watershed diverges from
    membership there, always in the safe direction (it never drops a perceived source).
    """
    members = set(member_ids)
    # seeds: perceived sources that are present among the members
    labeled: Set[str] = {m for m in members if m in perceived_sources}

    # Fixpoint label propagation. Monotone (labels only ever turn PERCEIVED), so it
    # terminates in at most len(members) passes. Each pass reads a frozen snapshot of the
    # current labels, so within-pass order cannot affect the outcome.
    while True:
        snapshot = frozenset(labeled)
        newly: Set[str] = set()
        # iterate candidates in a stable, content-independent order (sorted ids) purely so
        # the BUILD is deterministic; the fixpoint itself is order-independent by freezing.
        for m in sorted(members):
            if m in snapshot:
                continue
            best_to_perceived = 0.0
            best_to_unperceived = 0.0
            for other in sorted(members):
                if other == m:
                    continue
                s = _strongest_road_strength(store, m, other)
                if s <= 0.0:
                    continue
                if other in snapshot:
                    if s > best_to_perceived:
                        best_to_perceived = s
                else:
                    if s > best_to_unperceived:
                        best_to_unperceived = s
            # adopt PERCEIVED iff pulled toward the named region at least as hard as away
            # from it, AND there is some pull toward the named region at all (a member with
            # NO road to any perceived member never adopts — there is no attachment across
            # the valley). This is the relative-attachment comparison, not a membership test.
            if best_to_perceived > 0.0 and best_to_perceived >= best_to_unperceived:
                newly.add(m)
        if not newly:
            break
        labeled |= newly

    return labeled


# ─────────────────────────────────────────────────────────────────────────────
# Selection = competition + pruning (the single public entry, PURE READ)
# ─────────────────────────────────────────────────────────────────────────────

def select_winner(
    store: SubstrateStore,
    coalitions: List[Coalition],
    field_: ActivationField,
    clustering: SourceClustering,
    perception_sources: Dict[str, float],
    *,
    min_size_guard: int = DEFAULT_MIN_SIZE_GUARD,
) -> WorkspaceResult:
    """Select exactly one winning coalition (Decision A2) and prune members separated from
    the named region by a cohesion valley (Decision C1 — the relative-attachment watershed,
    NOT pure domain-membership; see the module docstring and its documented limitation).

    PURE READ — mutates nothing. This is the whole of 1d-i: no broadcast, no feedback, no
    write of any kind. (`field_` and `clustering` are accepted for the loop-closed contract
    and future use; the watershed is seeded from the perceived sources, which the 1c groups
    are built from.)

    Returns a WorkspaceResult. `winner` is the selected coalition AFTER pruning — a
    selected information structure, never a consciousness/awareness claim.
    """
    if not coalitions:
        return WorkspaceResult(
            winner=None, pruned_members=frozenset(), ranked=[], raw_winner=None, _seq={},
        )

    ranked = rank_coalitions(coalitions, min_size_guard=min_size_guard)
    raw_winner = ranked[0]

    perceived: Set[str] = set(perception_sources.keys())
    member_ids = list(raw_winner.members.keys())

    kept = _perceived_domain_members(store, member_ids, perceived)
    pruned = set(member_ids) - kept

    # Safety guard (shipped as an asserted-negative test): never empty the winner. If the
    # winning coalition contains NO perceived source at all, the watershed would prune
    # everything — but we have no grounds to declare an entire winning structure
    # "unperceived," so in that degenerate case we prune nothing and keep the raw winner.
    if not kept:
        return WorkspaceResult(
            winner=raw_winner,
            pruned_members=frozenset(),
            ranked=ranked,
            raw_winner=raw_winner,
            _seq=dict(raw_winner._seq),
        )

    if not pruned:
        # nothing to prune; the winner is the raw winner unchanged
        return WorkspaceResult(
            winner=raw_winner,
            pruned_members=frozenset(),
            ranked=ranked,
            raw_winner=raw_winner,
            _seq=dict(raw_winner._seq),
        )

    # Build the pruned winner. Strength is recomputed as the sum of surviving members'
    # activations (the same "sum of member activations" rule coalition formation uses), so
    # the winner remains internally consistent after pruning. Intrusive/breakthrough marks
    # are carried for surviving members only.
    pruned_members = {n: a for n, a in raw_winner.members.items() if n in kept}
    pruned_seq = {n: raw_winner._seq[n] for n in pruned_members if n in raw_winner._seq}
    surviving_bt = set(raw_winner.breakthrough_members) & set(pruned_members)
    pruned_winner = Coalition(
        members=pruned_members,
        strength=sum(pruned_members.values()),
        intrusive=bool(surviving_bt),
        breakthrough_members=surviving_bt,
        _seq=pruned_seq,
    )

    return WorkspaceResult(
        winner=pruned_winner,
        pruned_members=frozenset(pruned),
        ranked=ranked,
        raw_winner=raw_winner,
        _seq=pruned_seq,
    )
