"""
Psyche — Workspace selection  (step 1d-i: competition + over-swallow pruning)

WHAT THIS IS (and, just as importantly, what it is NOT):

This module replaces the `think()` placeholder "the strongest coalition IS the thought"
(`coalitions[0]` in psyche_perceive.py) with a real, deterministic, PURE-READ selection
step that does two things:

  1. COMPETITION (Decision A2): score the candidate coalitions by activation density
     (total activation normalized by coalition size, with a minimum-size guard so a tiny
     1-2 node coalition cannot win on density alone) and select exactly ONE winner. Ties
     break on the same fully-stable key the rest of the project uses
     (`(-score, -size, min creation_seq)`), reusing the psyche_coalitions pattern — never a
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

SCOPE — 1d-i (selection) + 1d-ii (the single bounded broadcast write):

  - 1d-i is PURE SELECTION. `select_winner` mutates NOTHING: no broadcast, no feedback,
    no writes of any kind — a pure read, exactly like the layers beneath it. Its logic is
    unchanged by 1d-ii.
  - 1d-ii adds ONE explicit, named write — `broadcast()` (Decision B1) — and nothing
    else. It strengthens the roads that already exist AMONG THE WINNER'S SURVIVING MEMBERS
    (its "internal roads") through the existing proven `strengthen()` primitive, so that on
    the next cycle those associations conduct activation slightly more ("what just won is
    slightly easier to think next"). It creates NO new roads and touches NO nodes (nodes
    stay neutral). This is the ONLY mutation 1d introduces; no read in 1d may call it.
  - BOUNDEDNESS IS STRUCTURAL, NOT A CLAMP. `broadcast()` adds no cap, no ceiling, no
    tunable magnitude of its own: it calls `strengthen()` with its default gain, whose
    `gain ∝ (1 − strength)` saturation makes repeated broadcasts on one winner converge
    toward strength 1.0 rather than grow without bound (each call closes a fixed FRACTION
    of the remaining distance to 1.0, so per-cycle deltas shrink geometrically). The
    no-divergence direction (§6.3) is a property of `strengthen`, inherited here for free.
  - NO LOCK-IN, STRUCTURALLY (§6.3). The broadcast biases CONDUCTANCE within the winner's
    own roads; it does NOT seed activation. Selection is dominated by which sources the
    CURRENT percept lights up (the field is seeded from the perceived sources). A
    sufficiently strong fresh percept for a different domain seeds THAT domain directly and
    wins, regardless of accumulated road bias on the prior winner — so the system does not
    freeze on the first thing it settled on. This is demonstrated, not assumed, by the
    no-lock-in acceptance test (escape through the live loop).
  - `broadcast()` is wired behind `think(..., broadcast=True)`. `think(..., broadcast=
    False)` (the default) remains EXACTLY the pure-read selection path 1d-i shipped — zero
    mutation — so the existing purity guarantee is preserved and meaningful.

HONEST FRAMING OF THE BROADCAST (hard — CLAUDE.md rule 1; SPEC-1d §1, §7 items 1–2):

  - "broadcast biases the next cycle" is an INTERNAL MECHANISM PROPERTY of the substrate:
    a measurable change in the next cycle's conduction in a pre-stated direction. It is
    NOT a claim that the system attends, notices, primes, or experiences anything. It is
    NOT the 1e priming effect (which is measured against external human data by the
    validator). 1d-ii closes the information loop that 1e needs; it makes NO cognitive or
    meaning claim itself. Passing this module's tests proves the FEEDBACK MECHANISM is
    correct, deterministic, integrity-preserving, and bounded — nothing about meaning.

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

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, FrozenSet, Set

from psyche_store import SubstrateStore
from psyche_field import ActivationField
from psyche_coalitions import Coalition
from psyche_source_clustering import SourceClustering


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


@dataclass(frozen=True)
class Broadcast:
    """A record of the single bounded write 1d-ii applied to the substrate (Decision B1).

    This is the description of EXACTLY what `broadcast()` did: which roads it strengthened
    and by how much. It is produced only by the explicit write path; no pure read ever
    produces a non-empty Broadcast, because no pure read calls `broadcast()`.

    It is an INTERNAL MECHANISM RECORD — "these associations just won, so they are now
    slightly easier to conduct next cycle." It is NOT a cognitive/awareness/priming claim
    (see the module honest-framing note); meaning is the validator's call at 1e.

    road_ids        : the distinct RoadIDs strengthened, in the deterministic order they
                      were strengthened (by road creation_seq asc — never a uuid, never
                      set/dict iteration order), so the write is byte-identical across
                      processes.
    before          : RoadID -> canonical (apply_decay=False) strength immediately BEFORE
                      the write, for inspection / the exactly-these-roads-changed test.
    after           : RoadID -> canonical strength immediately AFTER the write.
    winner_member_count : the number of surviving winner members the internal roads were
                      drawn from (0 if there was no winner, in which case nothing was
                      written and road_ids is empty).
    """
    road_ids: List[str]
    before: Dict[str, float]
    after: Dict[str, float]
    winner_member_count: int

    def delta(self, road_id: str) -> float:
        """How much a given broadcast road's canonical strength moved (after - before)."""
        return self.after.get(road_id, 0.0) - self.before.get(road_id, 0.0)

    def total_strength_after(self) -> float:
        """Sum of the broadcast roads' canonical strengths after the write — the bounded
        aggregate the no-divergence test watches converge across cycles.

        math.fsum, not sum(): this statistic feeds an assertion, and a convergence test
        whose statistic depends on road iteration order or on which CPython runs it
        (3.12+ compensates builtin sum(); 3.10/3.11 do not) is a weak test. fsum is
        exactly rounded, so the aggregate is a function of the strength MULTISET alone.
        SPEC-0c §2.5 site 2."""
        return math.fsum(self.after.values())


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
    psyche_coalitions' coalition sort key, with density swapped for raw strength."""
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
    no road. Mirrors psyche_source_clustering._pair_proximity — the same A1 signal. Pure."""
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

    # Build the pruned winner. Strength is recomputed as math.fsum over the surviving
    # members' activations — literally the same rule coalition formation uses
    # (psyche_coalitions.py, both Coalition construction sites), so the winner remains
    # internally consistent after pruning. Intrusive/breakthrough marks are carried for
    # surviving members only.
    #
    # This is the THIRD Coalition construction site in src/, and BUG-0b1 converted only
    # the other two while its report claimed there were two in total. So for a month this
    # comment's "same rule" claim was false and the pruned winner's strength — the value
    # _competition_key compares — was computed by the naive, version-dependent rule on the
    # very path BUG-0b1's flip occurred on. Members inherit their order from a set of uuid4
    # NodeIDs built in the coalition layer, which the store's ordering contract does not
    # reach, so this had to be fixed at the arithmetic. SPEC-0c §2.5 site 1 / §2.5.1.
    pruned_members = {n: a for n, a in raw_winner.members.items() if n in kept}
    pruned_seq = {n: raw_winner._seq[n] for n in pruned_members if n in raw_winner._seq}
    surviving_bt = set(raw_winner.breakthrough_members) & set(pruned_members)
    pruned_winner = Coalition(
        members=pruned_members,
        strength=math.fsum(pruned_members.values()),
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


# ─────────────────────────────────────────────────────────────────────────────
# Broadcast (Decision B1) — the SINGLE bounded write (1d-ii). Closes the loop.
# ─────────────────────────────────────────────────────────────────────────────

def _internal_road_ids(store: SubstrateStore, winner: Coalition) -> List[str]:
    """The DISTINCT RoadIDs of roads that already exist among the winner's members — the
    winner's "internal roads." A road is internal iff BOTH its endpoints are winner members.

    Pure read. Deterministic and convergence-safe:
      - It collects EXISTING roads only (via `find_road`); it never creates a road.
      - It considers both ordered directions (a->b and b->a are distinct directed roads in
        this graph), but DEDUPES BY RoadID, so each underlying road appears AT MOST ONCE —
        a road can never be counted (and therefore never strengthened) twice in one cycle.
      - The returned order is by the road's `creation_seq` ascending (a stable, persisted
        integer), never the uuid and never set/dict iteration order — so the sequence of
        roads strengthened, and hence the resulting store state, is byte-identical across
        processes and across hash seeds.
    """
    members = sorted(winner.members)  # sorted ids only for a deterministic build scan
    seen: Set[str] = set()
    rid_seq: Dict[str, int] = {}
    for i in range(len(members)):
        for j in range(len(members)):
            if i == j:
                continue
            rid = store.find_road(members[i], members[j])
            if rid is None or rid in seen:
                continue
            seen.add(rid)
            # read the stable creation_seq for deterministic ordering (apply_decay
            # irrelevant: creation_seq is identity-order metadata, not a decaying value)
            rid_seq[rid] = store.get_road(rid, apply_decay=False).creation_seq
    return sorted(seen, key=lambda r: rid_seq[r])


def broadcast(store: SubstrateStore, winner: Optional[Coalition]) -> Broadcast:
    """Apply the SINGLE bounded broadcast write (Decision B1): strengthen the winner's
    internal roads so they conduct slightly more on the next cycle. This is the ONLY
    mutation 1d introduces, and the ONLY writing path; no pure read calls it.

    Mechanism (in-grain with the substrate, reusing the proven write path):
      - Find the distinct roads that already exist among the winner's surviving members
        (`_internal_road_ids`). Create NOTHING new.
      - Strengthen each such road EXACTLY ONCE, in a deterministic order, via the existing
        `store.strengthen(rid)` primitive with its DEFAULT gain and NO charge (so nodes
        stay neutral, closure is untouched, and the emotional life of the road is not
        altered by this structural bias).

    BOUNDEDNESS IS STRUCTURAL — there is deliberately NO clamp, cap, or tunable magnitude
    here. `strengthen`'s `gain ∝ (1 − strength)` makes each call close a fixed FRACTION of
    the remaining distance to the saturation ceiling 1.0, so repeated broadcasts on one
    winner CONVERGE toward (and never exceed) 1.0; the per-cycle increments shrink
    geometrically. The §6.3 no-divergence property is therefore inherited from `strengthen`,
    not added here.

    This biases CONDUCTANCE only; it does not seed activation, so it cannot lock the system
    onto the prior winner — a strong fresh percept seeds its own domain and can still win
    (the §6.3 no-lock-in property, demonstrated through the live loop).

    Returns a `Broadcast` describing exactly what changed (the roads, and their canonical
    strength before/after). If there is no winner (or the winner has no internal roads),
    NOTHING is written and the returned Broadcast is empty — a no-op write is still a
    legitimate, recorded outcome.

    NOT a cognitive claim: "what won is easier to think next" is an internal mechanism
    property, distinct from the 1e priming effect measured against human data. See the
    module honest-framing note.
    """
    if winner is None or not winner.members:
        return Broadcast(road_ids=[], before={}, after={}, winner_member_count=0)

    road_ids = _internal_road_ids(store, winner)

    before: Dict[str, float] = {
        rid: store.get_road(rid, apply_decay=False).strength for rid in road_ids
    }

    # the single write: strengthen each internal road exactly once, in deterministic order
    for rid in road_ids:
        store.strengthen(rid)  # default gain; no charge => nodes neutral, closure untouched

    after: Dict[str, float] = {
        rid: store.get_road(rid, apply_decay=False).strength for rid in road_ids
    }

    return Broadcast(
        road_ids=road_ids,
        before=before,
        after=after,
        winner_member_count=len(winner.members),
    )
