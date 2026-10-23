"""
Psyche — Substrate Store  (Layer 1)

The one component every system touches. It holds the graph, mutates it safely,
resolves stable IDs, maintains indices, and exposes a narrow read/write surface.
It contains NO brain logic — it is the tissue, not the thought. What to remember,
what to strengthen, what to prune: all of that lives in the systems above.

Design decisions, settled in Layer 1 planning and realized here:

  IDENTITY      Every node and road has a stable uuid4 ID. Nothing is ever
                addressed by position. uuid4 (not a counter) so a bad reload can
                never reissue an old ID and resolve a stale reference to the wrong
                object — a stale ID resolves to NotFound, never to corruption.
  ORDER         Formation order is data, not identity: an explicit `creation_seq`
                integer, separate from the ID. The adjacency indices honour it: `_out`
                and `_in` are INSERTION-ORDERED MAPPINGS used as ordered sets, so
                `roads_from()` and `roads_into()` yield in road-creation order — the
                same in every process. They were sets of uuid4 hex strings, whose
                iteration order is freshly random per process; a consumer that summed
                floats in that order therefore had no single answer (see 0c). The store
                owns the ordering contract, so the store is where it is stated once,
                rather than worked around per consumer.
  ONE ROAD/PAIR A simple graph: at most one road per (source, target). A road has
                an emotional life (structured, possibly multi-valued charge); the
                same path carrying two feelings is ONE road, not two. A
                (src,tgt)->RoadID dedup index keeps get-or-add O(1).
  LAZY DECAY    Roads carry `last_touched`; decay is computed ON ACCESS as a
                function of elapsed time, not by a global sweep. Untouched roads
                cost nothing until the pruner examines them offline.
  PRIMITIVES    add_road creates; strengthen only strengthens (NotFound if absent).
                The biological "first traversal lays the path" lives in traverse(),
                a synchronous get-or-add-then-strengthen.
  PIN GUARD     remove_node refuses to delete a pinned node (e.g. the one the
                spotlight is on). Pruning POLICY is Layer 2; the MECHANISM is here.
  ATOMICITY     Every mutation is a synchronous method. No `await` inside a
                mutation, ever. Under single-threaded asyncio that makes each
                mutation atomic by construction; there are no locks because there
                is no preemption to lock against.
  INTEGRITY     Adjacency consistency is asserted incrementally on every mutation
                (cheap). A full orphan/drift scan is available for the offline pass.
                Both gated by a debug flag; on in development.
  QUIESCENCE    Compaction (future hybrid) is correct only with no concurrent awake
                mutators. Sleep-mode guarantees quiescence; that is why compaction
                would live there. (Compaction itself is future work; recorded.)

Pure Python standard library. No dependencies. Runs anywhere — laptop, Colab.
"""

from __future__ import annotations

import uuid
import time
import math
import itertools
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Set, Iterable, Iterator, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Identity, errors, time
# ─────────────────────────────────────────────────────────────────────────────

NodeID = str   # an opaque uuid4 hex string; callers must not interpret it
RoadID = str


class NotFound(Exception):
    """Raised (or signalled) when an ID does not resolve. This is the safe
    failure: a stale handle yields NotFound, never a wrong object."""


class IntegrityError(Exception):
    """Raised when an invariant check fails. Indicates a bug in the STORE itself,
    not in caller data."""


class Clock:
    """The substrate's sense of time. Real mode uses the wall clock; simulated
    mode lets tests advance time by hand so decay is observable instantly."""

    def __init__(self, simulated: bool = False, start: float = 0.0):
        self.simulated = simulated
        self._t = start

    def now(self) -> float:
        return self._t if self.simulated else time.time()

    def advance(self, dt: float) -> None:
        """Advance simulated time by dt. Simulated-mode only: in real mode there is
        nothing to advance, and blocking the event loop with time.sleep would be a
        bug (it would freeze every coroutine). Real time advances on its own."""
        if not self.simulated:
            raise RuntimeError(
                "Clock.advance is simulated-only; real time cannot be advanced by hand "
                "(and sleeping here would block the event loop).")
        self._t += dt


# ─────────────────────────────────────────────────────────────────────────────
# Nodes and roads (data only — no behavior beyond their own fields)
# ─────────────────────────────────────────────────────────────────────────────

class NodeType(Enum):
    EVENT = "event"
    CONCEPT = "concept"
    ENTITY = "entity"
    SENSATION = "sensation"
    ABSTRACT = "abstract"


class RoadQuality(Enum):
    CLOSED = "closed"
    DIRT = "dirt"
    GRAVEL = "gravel"
    ROAD = "road"
    HIGHWAY = "highway"


# Strength → quality thresholds (for OPEN roads). CLOSED is a state, not a band.
DIRT_CEILING = 0.20
GRAVEL_CEILING = 0.50
ROAD_CEILING = 0.80


@dataclass
class Node:
    """The atomic unit of information. Always emotionally neutral. Emotion lives
    in roads, never here. Identity is `id`; order is `creation_seq`."""
    id: NodeID
    content: str
    node_type: NodeType
    creation_seq: int
    formation_time: float
    last_accessed: float
    access_count: int = 0


@dataclass
class Road:
    """A directed connection from source to target. Carries the access quality
    (via strength) and the emotional life (via charge). Decay is lazy: it is
    computed from `last_touched` when the road is accessed, not by a sweep.

    `charge` is structured to honor the design's multi-valued emotional life:
    a single road can hold several named feelings at once (anger AND grief on the
    same path). The aggregate signed valence is derived from them. Layer 2 (MEMORY)
    defines the feeling vocabulary and dynamics; the STORE only stores and decays.
    """
    id: RoadID
    source_id: NodeID
    target_id: NodeID
    creation_seq: int
    formation_time: float
    last_touched: float

    strength: float = 0.05            # a new road is the faintest dirt track
    charges: Dict[str, float] = field(default_factory=dict)  # feeling -> intensity[-1,1]
    closed: bool = False
    traversal_count: int = 0

    # ── derived: aggregate valence across the road's several feelings ──────────
    @property
    def valence(self) -> float:
        if not self.charges:
            return 0.0
        # math.fsum, not sum(): this aggregate is compared against _CLOSURE_THRESHOLD and
        # _REOPEN_THRESHOLD, so a CATEGORICAL decision (is this road closed?) is resolved
        # on it. The project's float rule forbids deciding a category on an
        # independently-accumulated float — a naive fold makes the answer a function of
        # the order the feelings were recorded in and of which CPython runs it (3.12+
        # compensates builtin sum(); 3.10/3.11 do not). fsum is exactly rounded, so the
        # valence is a function of the charge MULTISET alone. SPEC-0c §2.5 site 3.
        return _clamp(math.fsum(self.charges.values()) / max(1, len(self.charges)),
                      -1.0, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Decay dynamics (pure functions; lazy, applied on access)
# ─────────────────────────────────────────────────────────────────────────────

# Strength decays exponentially; the time constant scales steeply with strength so
# a highway is dramatically more stable than a dirt path. Charge mellows toward
# neutral on a slower clock. Charge fades with time, but closure is STICKY: a closed
# road does not reopen from time alone — only an active positive crossing reopens it.
_BASE_TAU = 45.0
_CHARGE_TAU = 90.0
_DECAY_K = 4.2
_CLOSURE_THRESHOLD = -0.75
_REOPEN_THRESHOLD = -0.30


def _compute_decay(road: Road, now: float) -> Tuple[float, Dict[str, float]]:
    """Compute elapsed-time decay for a road as of `now`.

    Pure computation: returns (strength, charges) decayed to `now` WITHOUT mutating
    the road. This is what reads use, so a read never changes stored state — the
    atomicity model's interleave-safe-reads assumption depends on this.

    Note: decay does NOT re-evaluate closure. Closure is sticky — a closed road does
    not passively reopen from the mere passage of time (avoidance preserves trauma;
    it does not dissolve it). Only an active positive crossing reopens a road, and
    that logic lives in `strengthen`, never here.
    """
    dt = now - road.last_touched
    if dt <= 0:
        return road.strength, dict(road.charges)
    tau = _BASE_TAU * math.exp(road.strength * _DECAY_K)
    new_strength = road.strength * math.exp(-dt / tau)
    new_charges: Dict[str, float] = {}
    if road.charges:
        factor = math.exp(-dt / _CHARGE_TAU)
        for k, v in road.charges.items():
            faded = v * factor
            if abs(faded) >= 1e-4:
                new_charges[k] = faded   # a feeling that fully fades leaves the road
    return new_strength, new_charges


def _persist_decay(road: Road, now: float) -> None:
    """Apply elapsed-time decay to a road IN PLACE and advance its clock. Used only
    by mutations (strengthen/traverse) and the offline pass — never by a read.
    Does not touch closure (sticky; see _compute_decay)."""
    new_strength, new_charges = _compute_decay(road, now)
    road.strength = new_strength
    road.charges = new_charges
    road.last_touched = now


def _open_close_on_crossing(road: Road, one_shot_trauma: bool) -> None:
    """Re-evaluate closure — ONLY called on an active crossing (strengthen/traverse),
    never on a passive read or time-decay. This is what makes closure sticky:
      - a strongly negative crossing closes the road (or one-shot trauma closes it),
      - a positive crossing that lifts valence past the reopen threshold reopens it.
    Time alone does neither."""
    if one_shot_trauma:
        road.closed = True
        return
    v = road.valence
    if not road.closed and v <= _CLOSURE_THRESHOLD:
        road.closed = True
    elif road.closed and v >= _REOPEN_THRESHOLD:
        road.closed = False


# ─────────────────────────────────────────────────────────────────────────────
# The Substrate Store
# ─────────────────────────────────────────────────────────────────────────────

class SubstrateStore:
    """The authoritative home of the graph. Narrow surface, ID-addressed, no brain
    logic. All mutations are synchronous and atomic-by-construction under asyncio."""

    def __init__(self, clock: Optional[Clock] = None, debug: bool = True):
        self.clock = clock or Clock()
        self.debug = debug

        # authoritative tables
        self._nodes: Dict[NodeID, Node] = {}
        self._roads: Dict[RoadID, Road] = {}

        # indices (all keyed by stable ID, never by position).
        # _out/_in are INSERTION-ORDERED MAPPINGS USED AS ORDERED SETS (the value is
        # always None). See the ORDER note in the module docstring: this is what makes
        # roads_from()/roads_into() yield in road-creation order rather than in the
        # iteration order of a set of uuid4 hex strings, which is freshly random in
        # every process.
        self._out: Dict[NodeID, Dict[RoadID, None]] = {}
        self._in: Dict[NodeID, Dict[RoadID, None]] = {}
        self._pair: Dict[Tuple[NodeID, NodeID], RoadID] = {}  # dedup: one road/pair

        # designations & guards (all sets of IDs)
        self._self_region: Set[NodeID] = set()
        self._pinned: Set[NodeID] = set()

        # formation-order counter (data, not identity)
        self._seq = itertools.count()

    # ── id generation ─────────────────────────────────────────────────────────

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex

    # ── WRITE: nodes ──────────────────────────────────────────────────────────

    def add_node(self, content: str, node_type: NodeType) -> NodeID:
        now = self.clock.now()
        nid = self._new_id()
        self._nodes[nid] = Node(
            id=nid, content=content, node_type=node_type,
            creation_seq=next(self._seq),
            formation_time=now, last_accessed=now,
        )
        self._out[nid] = {}
        self._in[nid] = {}
        if self.debug:
            self._assert_node_indices(nid)
        return nid

    def remove_node(self, node_id: NodeID) -> None:
        """Delete a node and every road touching it. Refuses a pinned node — you do
        not prune what is currently in use. Leaves no dangling index entry."""
        node = self._nodes.get(node_id)
        if node is None:
            raise NotFound(f"node {node_id}")
        if node_id in self._pinned:
            raise IntegrityError(f"refusing to remove pinned node {node_id}")
        # remove all incident roads (copy: we mutate the indices as we go)
        for rid in list(self._out.get(node_id, {})) + list(self._in.get(node_id, {})):
            if rid in self._roads:
                self.remove_road(rid)
        self._out.pop(node_id, None)
        self._in.pop(node_id, None)
        self._self_region.discard(node_id)
        self._nodes.pop(node_id, None)

    # ── WRITE: roads ──────────────────────────────────────────────────────────

    def add_road(self, source_id: NodeID, target_id: NodeID) -> RoadID:
        """Create a faint dirt road from source to target. If one already exists for
        this exact pair, return it (one road per pair). Creation only — no
        strengthening here."""
        if source_id not in self._nodes:
            raise NotFound(f"source node {source_id}")
        if target_id not in self._nodes:
            raise NotFound(f"target node {target_id}")
        existing = self._pair.get((source_id, target_id))
        if existing is not None:
            return existing
        now = self.clock.now()
        rid = self._new_id()
        self._roads[rid] = Road(
            id=rid, source_id=source_id, target_id=target_id,
            creation_seq=next(self._seq),
            formation_time=now, last_touched=now,
        )
        # ordered-set insert: a NEW road always appends, so iteration is creation order.
        # (The dedup check above returns early for an existing pair, so a re-get never
        # re-inserts and therefore never reorders.)
        self._out[source_id][rid] = None
        self._in[target_id][rid] = None
        self._pair[(source_id, target_id)] = rid
        if self.debug:
            self._assert_road_indices(rid)
        return rid

    def remove_road(self, road_id: RoadID) -> None:
        road = self._roads.get(road_id)
        if road is None:
            raise NotFound(f"road {road_id}")
        self._out.get(road.source_id, {}).pop(road_id, None)
        self._in.get(road.target_id, {}).pop(road_id, None)
        self._pair.pop((road.source_id, road.target_id), None)
        self._roads.pop(road_id, None)

    def strengthen(self, road_id: RoadID, charge: Optional[Dict[str, float]] = None,
                   base_gain: float = 0.13) -> None:
        """Strengthen an EXISTING road (NotFound if absent — creation is add_road).
        Lazy decay is applied first, so strength/charge are current before the
        crossing deepens them. `charge` is a mapping of feeling -> intensity blended
        into the road's emotional life; intense feelings imprint harder."""
        road = self._roads.get(road_id)
        if road is None:
            raise NotFound(f"road {road_id}")
        now = self.clock.now()
        _persist_decay(road, now)  # bring the road to the present (a mutation may persist decay)

        # peak intensity of this crossing modulates how much the path deepens
        peak = max((abs(v) for v in (charge or {}).values()), default=0.0)
        gain = base_gain * (1.0 + peak * 1.5) * (1.0 - road.strength)
        road.strength = min(1.0, road.strength + gain)

        if charge:
            for feeling, intensity in charge.items():
                blend = 0.30 + 0.45 * abs(intensity)
                prior = road.charges.get(feeling, 0.0)
                road.charges[feeling] = _clamp(
                    (1.0 - blend) * prior + blend * intensity, -1.0, 1.0)

        road.traversal_count += 1
        road.last_touched = now
        # closure is re-evaluated ONLY here, on an active crossing — never on a read
        _open_close_on_crossing(road, one_shot_trauma=(peak >= 0.85 and road.valence < 0))

    def weaken(self, road_id: RoadID, base_loss: float = 0.0) -> None:
        """Lower an EXISTING road's strength — BRICK 2g, the mirror of `strengthen`.

        `loss = base_loss * road.strength`, so the decrement is proportional to what is
        there, exactly as `strengthen`'s gain is proportional to `(1 - strength)`. The
        effect therefore saturates at the FLOOR the same way potentiation saturates at
        the ceiling, and the bound is structural rather than a clamp bolted on: a road
        approaching 0.0 loses geometrically less, so repeated weakening converges toward
        0.0 and never passes it.

        WHAT THIS DELIBERATELY DOES NOT DO, and each omission is the mirror of something
        `strengthen` does for a reason:
          - it does NOT touch `charges`. Weakening a path's conductance is not the same
            event as changing what it feels like, and conflating them would make one
            constant do two jobs.
          - it does NOT advance `traversal_count`. That field counts crossings, and an
            outcome arriving later is not a crossing.
          - it does NOT re-evaluate closure. Closure is sticky and changes only on an
            active crossing (`_open_close_on_crossing`); a road must not be closed by
            bookkeeping that no traversal caused.
        Lazy decay IS applied first, exactly as `strengthen` does, so the road is current
        before the decrement lands.

        `base_loss = 0.0` is a no-op that still persists decay — the same shape
        `strengthen(base_gain=0.0)` has, and callers wanting byte-identity must skip the
        call rather than pass zero."""
        road = self._roads.get(road_id)
        if road is None:
            raise NotFound(f"road {road_id}")
        if not math.isfinite(base_loss):
            raise ValueError(f"base_loss must be finite, got {base_loss!r}")
        if base_loss < 0.0:
            raise ValueError(
                f"base_loss must be >= 0, got {base_loss}. `weaken` takes the MAGNITUDE of "
                f"the decrement; a negative would strengthen, and strengthening has its "
                f"own method with its own saturation. One direction per method.")
        now = self.clock.now()
        _persist_decay(road, now)
        road.strength = max(0.0, road.strength - base_loss * road.strength)
        road.last_touched = now

    # ── WRITE: convenience (biology lives here, not in the primitives) ─────────

    def traverse(self, source_id: NodeID, target_id: NodeID,
                 charge: Optional[Dict[str, float]] = None) -> RoadID:
        """The biological act: experiencing an association. Get-or-add the road,
        then strengthen it. One synchronous method, so it is atomic as a unit.
        This is where 'the first traversal lays the path' lives — at the behavior
        level, keeping the primitives orthogonal."""
        rid = self.add_road(source_id, target_id)
        self.strengthen(rid, charge)
        # touch endpoints
        now = self.clock.now()
        self._nodes[source_id].last_accessed = now
        self._nodes[source_id].access_count += 1
        self._nodes[target_id].last_accessed = now
        self._nodes[target_id].access_count += 1
        return rid

    # ── WRITE: designations & pins ────────────────────────────────────────────

    def designate_self(self, node_id: NodeID) -> None:
        if node_id not in self._nodes:
            raise NotFound(f"node {node_id}")
        self._self_region.add(node_id)

    def undesignate_self(self, node_id: NodeID) -> None:
        self._self_region.discard(node_id)

    def pin(self, node_id: NodeID) -> None:
        if node_id not in self._nodes:
            raise NotFound(f"node {node_id}")
        self._pinned.add(node_id)

    def unpin(self, node_id: NodeID) -> None:
        self._pinned.discard(node_id)

    # ── READ: resolution ──────────────────────────────────────────────────────

    def get_node(self, node_id: NodeID) -> Node:
        node = self._nodes.get(node_id)
        if node is None:
            raise NotFound(f"node {node_id}")
        return node

    def get_road(self, road_id: RoadID, apply_decay: bool = True) -> Road:
        """Resolve a road. This is a PURE READ: it never mutates stored state.

        With apply_decay=True (default) the caller sees the road as it is *now* —
        but the decayed values are computed into a returned COPY; the stored road is
        left untouched. The canonical stored value is "as of last write or last
        offline sweep," and reads compute forward from there without writing. This is
        what keeps reads safe to interleave under asyncio: a read changes nothing.

        With apply_decay=False the caller sees the raw stored road (as of its last
        write) — used by mutations and tests that want the canonical value.
        """
        road = self._roads.get(road_id)
        if road is None:
            raise NotFound(f"road {road_id}")
        if not apply_decay:
            return road
        new_strength, new_charges = _compute_decay(road, self.clock.now())
        # a decayed VIEW — a copy, so the read does not persist anything
        return Road(
            id=road.id, source_id=road.source_id, target_id=road.target_id,
            creation_seq=road.creation_seq, formation_time=road.formation_time,
            last_touched=road.last_touched,  # unchanged: this is a view, not a write
            strength=new_strength, charges=new_charges,
            closed=road.closed,            # closure is sticky; reads never change it
            traversal_count=road.traversal_count,
        )

    def exists(self, an_id: str) -> bool:
        return an_id in self._nodes or an_id in self._roads

    # ── READ: structure ───────────────────────────────────────────────────────

    def roads_from(self, node_id: NodeID) -> Iterator[RoadID]:
        """Out-roads of `node_id`, in ROAD-CREATION ORDER.

        The ordering is part of the contract, not an accident of the container: the
        index is an insertion-ordered mapping, insertion order is creation order, and
        creation order is program order, so the sequence is identical in every process.
        The intrinsic integer behind it is `creation_seq` — the same stable ordering
        integer the rest of the project resolves ties on.
        """
        if node_id not in self._nodes:
            raise NotFound(f"node {node_id}")
        return iter(tuple(self._out.get(node_id, {})))

    def roads_into(self, node_id: NodeID) -> Iterator[RoadID]:
        """In-roads of `node_id`, in ROAD-CREATION ORDER (see `roads_from`)."""
        if node_id not in self._nodes:
            raise NotFound(f"node {node_id}")
        return iter(tuple(self._in.get(node_id, {})))

    def neighbors(self, node_id: NodeID) -> Iterator[NodeID]:
        """Out-neighbours, in the order of the roads that reach them (see `roads_from`)."""
        return iter(tuple(self._roads[r].target_id
                          for r in self._out.get(node_id, {})))

    def find_road(self, source_id: NodeID, target_id: NodeID) -> Optional[RoadID]:
        return self._pair.get((source_id, target_id))

    def quality_of(self, road_id: RoadID) -> RoadQuality:
        road = self.get_road(road_id)  # decays first → quality reflects the present
        if road.closed:
            return RoadQuality.CLOSED
        s = road.strength
        if s < DIRT_CEILING:
            return RoadQuality.DIRT
        if s < GRAVEL_CEILING:
            return RoadQuality.GRAVEL
        if s < ROAD_CEILING:
            return RoadQuality.ROAD
        return RoadQuality.HIGHWAY

    # ── READ: designations ────────────────────────────────────────────────────

    def self_region(self) -> frozenset:
        return frozenset(self._self_region)

    def is_self(self, node_id: NodeID) -> bool:
        return node_id in self._self_region

    def is_pinned(self, node_id: NodeID) -> bool:
        return node_id in self._pinned

    # ── stats ─────────────────────────────────────────────────────────────────

    def node_count(self) -> int:
        return len(self._nodes)

    def road_count(self) -> int:
        return len(self._roads)

    def all_node_ids(self) -> Iterator[NodeID]:
        return iter(tuple(self._nodes.keys()))

    def all_road_ids(self) -> Iterator[RoadID]:
        return iter(tuple(self._roads.keys()))

    # ── INTEGRITY ─────────────────────────────────────────────────────────────

    def _assert_node_indices(self, node_id: NodeID) -> None:
        if node_id not in self._out or node_id not in self._in:
            raise IntegrityError(f"node {node_id} missing adjacency index")

    def _assert_road_indices(self, road_id: RoadID) -> None:
        road = self._roads[road_id]
        if road_id not in self._out.get(road.source_id, {}):
            raise IntegrityError(f"road {road_id} missing from out-index of source")
        if road_id not in self._in.get(road.target_id, {}):
            raise IntegrityError(f"road {road_id} missing from in-index of target")
        if self._pair.get((road.source_id, road.target_id)) != road_id:
            raise IntegrityError(f"road {road_id} missing from pair-index")

    def check_integrity(self) -> None:
        """Full-graph invariant scan. Cheap enough for an offline pass; the costly
        one relative to incremental checks. Raises IntegrityError on any drift."""
        # every road's endpoints exist; indices contain it; pair-index agrees
        for rid, road in self._roads.items():
            if road.source_id not in self._nodes:
                raise IntegrityError(f"road {rid} has orphan source {road.source_id}")
            if road.target_id not in self._nodes:
                raise IntegrityError(f"road {rid} has orphan target {road.target_id}")
            self._assert_road_indices(rid)
        # every index entry points to a live road
        for nid, rids in self._out.items():
            for rid in rids:
                if rid not in self._roads:
                    raise IntegrityError(f"out-index of {nid} has dead road {rid}")
        for nid, rids in self._in.items():
            for rid in rids:
                if rid not in self._roads:
                    raise IntegrityError(f"in-index of {nid} has dead road {rid}")
        # pair-index matches road tables exactly
        for (s, t), rid in self._pair.items():
            if rid not in self._roads:
                raise IntegrityError(f"pair-index ({s},{t}) has dead road {rid}")
        # designations & pins reference live nodes
        for nid in self._self_region:
            if nid not in self._nodes:
                raise IntegrityError(f"self-region has dead node {nid}")
        for nid in self._pinned:
            if nid not in self._nodes:
                raise IntegrityError(f"pin-set has dead node {nid}")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))
