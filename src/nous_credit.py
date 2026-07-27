"""
nous_credit — brick 2f-i: temporal credit assignment over a bounded window.

WHAT THIS MODULE DOES
---------------------
It answers one narrow, arithmetic question: *when a designated outcome occurs at cycle
`t+k`, which roads traversed at cycle `t` should be strengthened, and by how much?*

The answer is bookkeeping over a bounded history. An `EpisodicTrace` holds a fixed
window of `(cycle_index, road_id)` entries. `assign_credit` computes an eligibility
weight per entry from the integer cycle distance `k`, sums a road's eligibility over
its occurrences in the window, and applies the result through the existing, already
verified `SubstrateStore.strengthen()` — the store's only write path, which this module
does not modify or bypass.

WHAT THIS MODULE DOES NOT DO — stated first, because the vocabulary invites over-reading
------------------------------------------------------------------------------------
The words "credit", "eligibility" and "trace" name arithmetic here. Nothing in this file
acquires, retains, prefers, or comprehends anything, and no such claim is made or
approached. A road whose strength rose because an outcome followed it has been the
subject of a multiplication; that is the whole of it.

Specifically, and asserted in the suite rather than merely written here:

  - **POTENTIATION-ONLY, and this is the largest limitation in the file.** There is no
    depression path. Credit is applied through `strengthen()`, which only increases
    strength, so every outcome this mechanism can express moves a road in ONE direction:
    toward saturation. A negative `outcome_magnitude` is REFUSED at the boundary rather
    than absorbed, because absorbing it would silently reinforce whatever an adverse
    outcome was meant to discourage.

    The consequence, stated rather than left to be inferred: **what is built assigns
    attention, not credit.** It marks which roads preceded a designated outcome and
    strengthens them in proportion to how recently. It cannot distinguish an outcome
    worth repeating from one worth avoiding, because feedback with no sign is not
    feedback. Nothing here can be undone by anything here.

  - **This is a bounded window over a single trace.** No multi-step return estimation,
    no discounting across episodes, no propagation through a learned value estimate.
    "Credit assignment" here must not be read as reinforcement learning.
  - **No behavioural tagging.** Design C (SPEC-2f §3.3) deliberately gives up the one
    property the biology corpus is actually about: a weak trace preserved because an
    unrelated *strong* event flooded the system in the same window. That needs a global
    pool and a capture sweep, and it is brick 2f-ii — deferred, not foreclosed.
  - **The trace is not a synaptic analogue.** It lives outside the substrate. Nothing in
    the store holds it. It is a replay buffer with a decay kernel, and calling it an
    "eligibility trace" invites the reader to imagine a synapse holding something, where
    in fact nothing is.
  - **Zero of the five pre-registered AOL autonomy criteria (SPEC-2e) are satisfied by
    this module**, and the potentiation-only bound above is why none of them moves: each
    of AOL-2, AOL-3 and AOL-4 needs an outcome to be able to make some earlier action
    LESS likely, and nothing here can. It is a prerequisite for those three, and being a
    prerequisite is not partial credit.

  - **It does not satisfy Butlin et al.'s AE-1** — *"learning from feedback and selecting
    outputs so as to pursue goals, especially where this involves flexible responsiveness
    to competing goals."* A one-signed rule cannot select between competing goals, because
    it cannot express a reason to prefer one over another. Stated by name so that a reader
    who reaches for the architectural axis finds the answer already given rather than
    open. The project's standing assessment against that whole list is kept in one
    document and cited from there alone; it is deliberately not repeated here.

The mechanism is *inspired by* the three-factor plasticity framing in the design corpus
(a pre-synaptic trace, a post-synaptic trace, and a third modulatory term). Inspiration
is the only relationship claimed; no biological fidelity is asserted, and none is
verified here.

DESIGN NOTES THAT MATTER FOR CORRECTNESS
----------------------------------------
**Eligibility is a function of TIME ONLY.** `e(k)` reads the integer cycle distance and
nothing else — never a road's strength. If the outcome or the eligibility were derived
from `strength`, this module would be reading ω back out and calling the echo a result.
That is the circularity that produced the 1e NO-GO, wearing new clothes, and the suite
asserts against it directly.

**The window edge is exact, not approached.** `e(k) = 0.0` for `k > window`, by an
integer comparison made before any float arithmetic happens. There is no tail to
mistake for a cutoff.

**Ordering resolves on an integer.** Roads are credited in ascending order of their
first appearance in the window — a monotone `int` — never by eligibility magnitude. A
tie-break that a 1-ULP float asymmetry can pre-empt is not a tie-break.

**Summation is `math.fsum`.** A road may appear several times in one window, so its
eligibility is a fold over a set of terms whose order is not intrinsic. `math.fsum` is
exactly rounded and therefore order-independent.

**`P_PRP` is caller-supplied (D-020 §4.3).** It is a plain scalar, defaulting to the
neutral value `0.0`, at which this module writes nothing at all. NEUROMODULATION becomes
its publisher later with no change to this interface. A caller-supplied scalar can be
held fixed, which is what makes it possible to separate this module's effect from a
modulatory one — no published-state design permits that.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Iterable, List, Optional, Sequence

from nous_store import SubstrateStore, RoadID

# The eligibility window, in CYCLES. An outcome reaches back at most this far.
DEFAULT_WINDOW: int = 8

# Per-cycle eligibility decay. e(k) = decay ** k inside the window.
DEFAULT_ELIGIBILITY_DECAY: float = 0.6

# The neutral plasticity budget. At this value assign_credit writes NOTHING and the
# store is byte-identical — the overlay's off position (SPEC-2f §3, gated-overlay rule).
NEUTRAL_P_PRP: float = 0.0

# Passed through to strengthen() as its base gain, scaled by budget x eligibility.
DEFAULT_CREDIT_GAIN: float = 0.13


def _require_finite(name: str, x: float) -> float:
    if not math.isfinite(x):
        raise ValueError(f"{name} must be finite, got {x!r}")
    return x


@dataclass(frozen=True)
class TraceEntry:
    """One `(cycle, road)` observation. `seq` is a monotone append index — an intrinsic
    integer, and the only thing that ever decides ordering in this module."""
    cycle: int
    road_id: RoadID
    seq: int


class EpisodicTrace:
    """A bounded, append-only record of which roads a cycle used.

    Bounded by the WINDOW, not by the run: entries older than `window` cycles are
    evicted on each `record`, so memory is a function of the window and the graph, never
    of how long the system has been running.

    Recording mutates only this object. It never touches the store — reading and
    building a trace is pure with respect to the substrate, and the single write path is
    `assign_credit`.
    """

    def __init__(self, window: int = DEFAULT_WINDOW) -> None:
        if not isinstance(window, int) or isinstance(window, bool):
            raise ValueError(f"window must be an int, got {window!r}")
        if window < 1:
            raise ValueError(f"window must be >= 1, got {window}")
        self.window: int = window
        self._entries: Deque[TraceEntry] = deque()
        self._cycle: int = -1          # -1 so the first recorded cycle is 0
        self._seq: int = 0

    @property
    def cycle(self) -> int:
        """The index of the most recently recorded cycle (-1 before anything)."""
        return self._cycle

    @property
    def entries(self) -> List[TraceEntry]:
        """The retained entries, oldest first. A copy: callers cannot mutate the trace
        through it."""
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def record(self, road_ids: Iterable[RoadID]) -> int:
        """Append this cycle's roads and return the cycle index used.

        An empty iterable is a legitimate cycle: it advances time without contributing
        eligibility, which is exactly what a cycle that used no roads did.
        """
        self._cycle += 1
        for rid in road_ids:
            self._entries.append(TraceEntry(cycle=self._cycle, road_id=rid,
                                            seq=self._seq))
            self._seq += 1
        self._evict()
        return self._cycle

    def _evict(self) -> None:
        """Drop entries the window can no longer reach. The comparison is between two
        ints, so nothing here can be decided by a float."""
        oldest_reachable = self._cycle - self.window
        while self._entries and self._entries[0].cycle < oldest_reachable:
            self._entries.popleft()

    def eligible(self, outcome_cycle: int, decay: float,
                 window: Optional[int] = None) -> Dict[RoadID, float]:
        """Total eligibility per road at `outcome_cycle`. A pure read.

        A road appearing several times in the window contributes several terms, whose
        order is not intrinsic — so the fold is `math.fsum`, which is exactly rounded and
        therefore order-independent.
        """
        w = self.window if window is None else window
        terms: Dict[RoadID, List[float]] = {}
        for e in self._entries:
            k = outcome_cycle - e.cycle
            if k < 0 or k > w:
                continue
            terms.setdefault(e.road_id, []).append(eligibility(k, decay, w))
        return {rid: math.fsum(vs) for rid, vs in terms.items()}

    def first_seq(self) -> Dict[RoadID, int]:
        """Each road's earliest append index in the window — the integer that decides
        application order."""
        out: Dict[RoadID, int] = {}
        for e in self._entries:
            if e.road_id not in out:
                out[e.road_id] = e.seq
        return out


def eligibility(k: int, decay: float = DEFAULT_ELIGIBILITY_DECAY,
                window: int = DEFAULT_WINDOW) -> float:
    """The eligibility of a traversal `k` cycles before the outcome.

    `e(k) = decay ** k` for `0 <= k <= window`, and EXACTLY `0.0` beyond it. The window
    test is an integer comparison resolved before any float arithmetic, so the edge is
    exact rather than approached — SPEC-0b2 §9.2 records one boundary measured three
    times as three different numbers, each the last value someone happened to sample.

    A single `pow` per entry, never a running product: there is no chain of factors here
    and therefore no term set whose order could change the answer.
    """
    if not isinstance(k, int) or isinstance(k, bool):
        raise ValueError(f"k must be an int cycle distance, got {k!r}")
    if k < 0:
        raise ValueError(
            f"k must be >= 0, got {k}: an outcome cannot reach backwards to credit a "
            f"traversal that had not happened yet")
    if not isinstance(window, int) or isinstance(window, bool) or window < 1:
        raise ValueError(f"window must be an int >= 1, got {window!r}")
    _require_finite("decay", decay)
    if not (0.0 <= decay <= 1.0):
        raise ValueError(f"decay must be in [0, 1], got {decay}")
    if k > window:
        return 0.0
    return decay ** k


@dataclass(frozen=True)
class CreditAssignment:
    """Exactly what `assign_credit` did — the roads it touched, the eligibility it
    computed, and the canonical strength on each side of the write."""
    road_ids: List[RoadID]
    eligibility: Dict[RoadID, float]
    gain: Dict[RoadID, float]
    before: Dict[RoadID, float]
    after: Dict[RoadID, float]
    order_key: Dict[RoadID, int]
    outcome_cycle: int
    p_prp: float


def assign_credit(
    store: SubstrateStore,
    trace: EpisodicTrace,
    *,
    outcome_magnitude: float,
    p_prp: float = NEUTRAL_P_PRP,
    decay: float = DEFAULT_ELIGIBILITY_DECAY,
    window: Optional[int] = None,
    credited_road_ids: Optional[Sequence[RoadID]] = None,
    base_gain: float = DEFAULT_CREDIT_GAIN,
    charge: Optional[Dict[str, float]] = None,
) -> CreditAssignment:
    """Apply credit for one designated outcome, through `store.strengthen`.

    `outcome_magnitude` is supplied by the CALLER and is never derived from any road's
    strength. That is the load-bearing constraint of this function: an outcome computed
    from ω would make this a readback of the substrate rather than credit assignment.

    `p_prp` is the caller-supplied plasticity budget (D-020 §4.3). At `NEUTRAL_P_PRP`
    nothing is written — and `strengthen` is not merely called with a zero gain but is
    NOT CALLED, because `strengthen` also advances `traversal_count`, sets `last_touched`
    and re-evaluates closure. Skipping the call is what makes the neutral value
    byte-identical.

    `credited_road_ids`, when given, restricts credit to those roads — the hook the
    shuffled-outcome control needs, since a control must be able to pair an outcome with
    a different window without altering the trace or the outcome sequence.

    Returns a record of exactly what changed. Roads are applied in ascending order of
    first appearance — an intrinsic integer — so the write sequence, and hence the
    resulting store, cannot be reordered by a float asymmetry.
    """
    _require_finite("outcome_magnitude", outcome_magnitude)
    _require_finite("p_prp", p_prp)
    _require_finite("base_gain", base_gain)
    if outcome_magnitude < 0.0:
        # FINDING 2f-1 (tester). Until this guard, a negative was silently abs()'d, so an
        # adverse outcome strengthened a road byte-identically to a favourable one of the
        # same size. The message states the true reason rather than naming a range,
        # because the range is a symptom and the absence is the fact.
        raise ValueError(
            f"outcome_magnitude must be >= 0, got {outcome_magnitude}. This mechanism is "
            f"POTENTIATION-ONLY: it has no way to represent an adverse outcome, because no "
            f"depression path exists — credit is applied through strengthen(), which only "
            f"increases strength. Passing the magnitude of an adverse outcome would "
            f"silently reinforce exactly what it was meant to discourage. Pass the "
            f"magnitude of a FAVOURABLE outcome, or do not call assign_credit at all. "
            f"Weakening is a separate mechanism that is not built.")
    if p_prp < 0.0:
        raise ValueError(f"p_prp must be >= 0, got {p_prp}")
    w = trace.window if window is None else window
    if not isinstance(w, int) or isinstance(w, bool) or w < 1:
        raise ValueError(f"window must be an int >= 1, got {w!r}")
    _require_finite("decay", decay)
    if not (0.0 <= decay <= 1.0):
        raise ValueError(f"decay must be in [0, 1], got {decay}")

    outcome_cycle = trace.cycle
    elig = trace.eligible(outcome_cycle, decay, w)
    order = trace.first_seq()

    allowed = None if credited_road_ids is None else set(credited_road_ids)

    # ---- application: integer-ordered, and skipped entirely where credit is zero -----
    #
    # No abs() here any more. It used to wrap `outcome_magnitude` and was the whole of
    # FINDING 2f-1: it made an adverse outcome indistinguishable from a favourable one.
    # With the boundary guard above, the value is already known non-negative, so an abs()
    # would now be dead code that still SAYS "the sign does not matter here" — which is
    # exactly the claim the guard exists to deny.
    #
    # DECISION, recorded here rather than left to be inferred (FINDING 2f-2): repeated
    # occurrences of one road inside the window contribute LINEARLY and without a cap.
    # Three traversals in one cycle earn exactly triple eligibility; ten thousand earn
    # ten thousand times. This is deliberate and it is NOT capped.
    #   REASON: a cap means choosing a constant, and this project keeps an
    #   `uncalibrated_constants` list precisely because inventing one without calibration
    #   has cost it before. Unbounded eligibility is not reachable as unbounded strength:
    #   the gain enters strengthen(), whose increment is proportional to (1 - strength),
    #   so the effect saturates at 1.0 no matter how large the eligibility term becomes.
    #   The bound is inherited from a PROVEN mechanism rather than added here.
    #   FALSIFIER: any path where an eligibility value reaches something that is NOT
    #   saturated downstream — a consumer that reads CreditAssignment.eligibility or
    #   .gain directly and acts on the raw magnitude, or a future write path that does
    #   not go through strengthen(). Either makes the missing cap reachable.
    gains: Dict[RoadID, float] = {}
    for rid, e in elig.items():
        if allowed is not None and rid not in allowed:
            continue
        g = base_gain * p_prp * e * outcome_magnitude
        if g > 0.0:
            gains[rid] = g

    applied = sorted(gains, key=lambda r: order[r])

    before: Dict[RoadID, float] = {}
    after: Dict[RoadID, float] = {}
    for rid in applied:
        before[rid] = store.get_road(rid, apply_decay=False).strength
    for rid in applied:
        store.strengthen(rid, charge, base_gain=gains[rid])
    for rid in applied:
        after[rid] = store.get_road(rid, apply_decay=False).strength

    return CreditAssignment(
        road_ids=applied,
        eligibility={r: elig[r] for r in applied} if applied else dict(elig),
        gain=gains,
        before=before,
        after=after,
        order_key={r: order[r] for r in elig},
        outcome_cycle=outcome_cycle,
        p_prp=p_prp,
    )
