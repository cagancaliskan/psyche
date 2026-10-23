"""
SPEC-1e §9 — the broadcast-Δ measurement instrument (builder task B-i).

This is INSTRUMENTATION ONLY. It measures two scalars per (prime, target):

  M-A  (broadcast-trace Δ; the HEADLINE closed-loop metric, EXP-1e §4):
       run think(store, prime_utterance, broadcast=True) so the 1d-ii broadcast
       strengthens the winner's internal roads, then read the target's activation
       under a spread from the prime on the BROADCAST-MODIFIED store and subtract the
       SAME read on a PRISTINE (un-broadcast) store. Δ = activation_after − activation_before.

  M-B  (bare-spread; CORROBORATION, EXP-1e §4): a single spread from the prime, read
       the target's activation — exactly harness.read_targets, no think(), no broadcast.

It makes NO cognitive/priming claim and computes NO verdict. Whether a measured Δ
*means* priming is decided solely by the validator's graded run against the frozen
pre-registration (docs/experiments/EXP-1e-priming.md). This module only guarantees that
the measurement is correct, pure, per-prime isolated, order-independent, and deterministic.

It imports the FROZEN library (src/) and the proven 2A/2B harness UNCHANGED. It adds no
dependency beyond the Python standard library.

────────────────────────────────────────────────────────────────────────────────────
PER-PRIME ISOLATION (a correctness requirement, EXP-1e §9 / SPEC-1e §9 B-i)
────────────────────────────────────────────────────────────────────────────────────
think(broadcast=True) MUTATES the substrate (the broadcast strengthens the winner's
internal roads). If many primes were measured on one shared store without restoring it,
prime k's broadcast would still be present when prime k+1 is measured — exactly the
popularity-/strength-compounding leak EXP-1e §6.2.0 worries about, surfacing here at the
instrument level. The instrument therefore measures each prime from the SAME baseline
substrate, and offers two isolation mechanisms that a test proves identical:

  REBUILD isolation (the reference; obviously correct): every read uses a FRESH store
      from a zero-argument `store_factory()`. The pristine read and the broadcast read are
      on DIFFERENT store objects, so one prime's broadcast cannot touch another prime's
      measurement — isolation is structural and absolute. Order-independence is therefore
      trivial. This is the correctness ground truth, but rebuilding a large substrate per
      prime is expensive.

  RESTORE isolation (the fast path; validated against REBUILD): measure many primes on
      ONE shared store, and after each prime's broadcast UNDO it — reverting exactly the
      roads the Broadcast record says were strengthened, back to their pre-broadcast
      canonical strength / traversal_count / last_touched (the broadcast passes no charge,
      so charge and closure are untouched). Everything in think() before the broadcast is a
      proven pure read, so the broadcast is the ONLY mutation, and undoing it restores the
      store byte-for-byte. A test asserts REBUILD == RESTORE on a controlled graph; a
      second asserts the shared store is byte-identical before and after a full sweep, and
      a third asserts order-independence (a prime's Δ is identical no matter where it sits
      in the sweep).

The activation READS used for the pristine baseline are harness.read_targets /
retrieval_strength, which are PROVEN pure reads — they never mutate stored state (purity).
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from typing import Callable, Dict, List, Optional, Sequence

from harness import read_targets, SRC_DIR  # noqa: F401  (SRC_DIR re-exported for tests)
from psyche_store import SubstrateStore
from psyche_perceive import think
from psyche_activation import (
    DEFAULT_SEED_ENERGY,
    DEFAULT_DECAY_PER_HOP,
    DEFAULT_FLOOR,
    DEFAULT_HOP_BUDGET,
)


# ─────────────────────────────────────────────────────────────────────────────
# Road-state snapshot / restore (the RESTORE isolation primitive)
# ─────────────────────────────────────────────────────────────────────────────
#
# A road's mutable state after a broadcast strengthen() (no charge) differs from before
# in exactly: strength, traversal_count, last_touched. We snapshot those for the roads the
# broadcast will touch and write them back to undo the one sanctioned write. We read the
# LIVE stored road via get_road(apply_decay=False) (which returns the actual stored object,
# not a decayed copy) and mutate its scalar fields back. charges/closed are snapshotted too
# and restored for full safety, though the no-charge broadcast leaves them unchanged.


def _snapshot_roads(store: SubstrateStore, road_ids: Sequence[str]) -> Dict[str, dict]:
    """Snapshot the mutable state of the given roads (canonical, un-decayed)."""
    snap: Dict[str, dict] = {}
    for rid in road_ids:
        r = store.get_road(rid, apply_decay=False)
        snap[rid] = {
            "strength": r.strength,
            "traversal_count": r.traversal_count,
            "last_touched": r.last_touched,
            "closed": r.closed,
            "charges": dict(r.charges),
        }
    return snap


def _restore_roads(store: SubstrateStore, snap: Dict[str, dict]) -> None:
    """Write the snapshotted road state back, undoing the broadcast's single write.

    get_road(apply_decay=False) returns the live stored Road object, so assigning its
    fields reverts the stored state. This is the instrument UNDOING the one sanctioned
    broadcast mutation; it touches nothing else in the store."""
    for rid, s in snap.items():
        r = store.get_road(rid, apply_decay=False)
        r.strength = s["strength"]
        r.traversal_count = s["traversal_count"]
        r.last_touched = s["last_touched"]
        r.closed = s["closed"]
        r.charges = dict(s["charges"])


# ─────────────────────────────────────────────────────────────────────────────
# The knob bundle (library defaults; held identical across all conditions/arms)
# ─────────────────────────────────────────────────────────────────────────────

def default_knobs() -> Dict[str, float]:
    """The library-default activation knobs, held identical across conditions and arms
    (a control, EXP-1e §4). Returned fresh so a caller cannot accidentally mutate a shared
    dict."""
    return {
        "energy": DEFAULT_SEED_ENERGY,
        "decay_per_hop": DEFAULT_DECAY_PER_HOP,
        "floor": DEFAULT_FLOOR,
        "hop_budget": DEFAULT_HOP_BUDGET,
    }


# ─────────────────────────────────────────────────────────────────────────────
# M-B — bare spread (corroboration). Exactly harness.read_targets.
# ─────────────────────────────────────────────────────────────────────────────

def measure_mb(
    store: SubstrateStore,
    prime_id: str,
    target_ids: Sequence[str],
    *,
    knobs: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """M-B (bare-spread): a single spread from `prime_id`; read each target. Pure read.

    This is the 2B metric reused verbatim (no think(), no broadcast). Returns
    {target_id: activation}. A target not reached is 0.0 (a meaningful readout)."""
    k = knobs if knobs is not None else default_knobs()
    res = read_targets(store, prime_id, list(target_ids), **k)
    return dict(res["activation"])


# ─────────────────────────────────────────────────────────────────────────────
# M-A — broadcast-trace Δ (headline). think(broadcast=True) then before/after read.
# ─────────────────────────────────────────────────────────────────────────────

class MAResult:
    """The per-prime M-A measurement record (instrumentation, no verdict).

    delta            : {target_id: activation_after − activation_before}
    before           : {target_id: pristine (un-broadcast) activation}
    after            : {target_id: broadcast-modified activation}
    broadcast_road_ids : the roads the broadcast strengthened (from the Broadcast record)
    winner_member_count: surviving winner members the internal roads were drawn from
    in_winner_reach  : {target_id: bool} — whether the target's before/after differ at all,
                       i.e. whether the broadcast reached it (the EXP-1e §4 "named cost":
                       a target outside the broadcast's reach has Δ = 0 by construction).
    """

    __slots__ = (
        "delta", "before", "after",
        "broadcast_road_ids", "winner_member_count", "in_winner_reach",
    )

    def __init__(self, delta, before, after, broadcast_road_ids,
                 winner_member_count, in_winner_reach):
        self.delta = delta
        self.before = before
        self.after = after
        self.broadcast_road_ids = broadcast_road_ids
        self.winner_member_count = winner_member_count
        self.in_winner_reach = in_winner_reach


def measure_ma_rebuild(
    store_factory: Callable[[], SubstrateStore],
    prime_utterance: str,
    prime_id_in: Callable[[SubstrateStore], str],
    target_ids_in: Callable[[SubstrateStore], List[str]],
    *,
    knobs: Optional[Dict[str, float]] = None,
) -> MAResult:
    """M-A via REBUILD isolation (the reference; obviously correct).

    Two FRESH stores from `store_factory()`:
      pristine  : never broadcast → the "before" target activations (pure read).
      broadcast : think(prime_utterance, broadcast=True), then read the "after".
    Δ = after − before. Because pristine and broadcast are different store objects, no
    prior prime's broadcast can be present in either — isolation is structural.

    `prime_id_in` / `target_ids_in` resolve the prime/target CONTENT names to the freshly
    built store's NodeIDs (the IDs differ per build; the library is invariant to them).
    """
    k = knobs if knobs is not None else default_knobs()

    # pristine store: never broadcast → the "before" activations (pure read). Targets are
    # resolved on the pristine store's own IDs and aligned by ORDER with the broadcast
    # store's targets below (the two stores have different uuid4 IDs but the same content
    # order, since target_ids_in() returns the same content list per store).
    pristine = store_factory()
    pristine_targets = target_ids_in(pristine)
    before_by_id = read_targets(pristine, prime_id_in(pristine), pristine_targets, **k)["activation"]
    before_vals = [before_by_id[t] for t in pristine_targets]

    bstore = store_factory()
    res = think(bstore, prime_utterance, broadcast=True)
    btargets = target_ids_in(bstore)
    after_map = read_targets(bstore, prime_id_in(bstore), btargets, **k)["activation"]
    after_vals = [after_map[t] for t in btargets]

    broadcast_road_ids = list(res.broadcast_.road_ids) if res.broadcast_ is not None else []
    winner_member_count = (
        res.broadcast_.winner_member_count if res.broadcast_ is not None else 0
    )

    delta = {}
    before_out = {}
    after_out = {}
    in_reach = {}
    for t, bv, av in zip(btargets, before_vals, after_vals):
        delta[t] = av - bv
        before_out[t] = bv
        after_out[t] = av
        in_reach[t] = (av != bv)

    return MAResult(
        delta=delta, before=before_out, after=after_out,
        broadcast_road_ids=broadcast_road_ids,
        winner_member_count=winner_member_count,
        in_winner_reach=in_reach,
    )


def measure_ma_restore(
    store: SubstrateStore,
    prime_utterance: str,
    prime_id: str,
    target_ids: Sequence[str],
    *,
    knobs: Optional[Dict[str, float]] = None,
) -> MAResult:
    """M-A via RESTORE isolation (the fast path; validated against measure_ma_rebuild).

    On ONE shared store:
      1. read the targets (pristine "before") — pure read, store unchanged.
      2. think(prime_utterance, broadcast=True) — the single broadcast write.
      3. read the targets again (broadcast "after").
      4. UNDO the broadcast: restore exactly the roads it strengthened, so the store is
         left byte-for-byte as it was before this prime. The NEXT prime then starts from
         the identical baseline — per-prime isolation without a rebuild.

    Δ = after − before. Step 4 is what makes a multi-prime sweep order-independent: every
    prime sees the same baseline regardless of position, because each prime cleans up after
    itself. (A test asserts the store snapshot is identical before and after, and that the
    result equals the REBUILD reference.)
    """
    k = knobs if knobs is not None else default_knobs()

    before_map = read_targets(store, prime_id, list(target_ids), **k)["activation"]
    before_vals = [before_map[t] for t in target_ids]

    res = think(store, prime_utterance, broadcast=True)
    broadcast_road_ids = list(res.broadcast_.road_ids) if res.broadcast_ is not None else []
    winner_member_count = (
        res.broadcast_.winner_member_count if res.broadcast_ is not None else 0
    )

    # The "after" read MUST happen on the broadcast-modified store (before any restore), or
    # the Δ would be identically 0. Read first, THEN undo the broadcast.
    after_map = read_targets(store, prime_id, list(target_ids), **k)["activation"]
    after_vals = [after_map[t] for t in target_ids]

    # Undo the broadcast (per-prime cleanup): the broadcast touched exactly
    # broadcast_road_ids; revert each to its pre-broadcast canonical strength (from the
    # engine's OWN Broadcast record) and undo the single +1 traversal strengthen() applied.
    # On the simulated clock these substrates use, now is fixed, so last_touched is unchanged
    # (no revert needed); a clock advancing between primes would make the run non-deterministic
    # anyway (an EXP-1e §7.1 VOID), so this instrument is used only on the fixed simulated
    # clock. After this, the store is byte-identical to before this prime — the NEXT prime
    # starts from the same baseline (per-prime isolation without a rebuild).
    if res.broadcast_ is not None and broadcast_road_ids:
        for rid in broadcast_road_ids:
            r = store.get_road(rid, apply_decay=False)
            r.strength = res.broadcast_.before[rid]
            r.traversal_count -= 1   # strengthen() did exactly one +1

    delta = {}
    before_out = {}
    after_out = {}
    in_reach = {}
    for t, bv, av in zip(target_ids, before_vals, after_vals):
        delta[t] = av - bv
        before_out[t] = bv
        after_out[t] = av
        in_reach[t] = (av != bv)

    return MAResult(
        delta=delta, before=before_out, after=after_out,
        broadcast_road_ids=broadcast_road_ids,
        winner_member_count=winner_member_count,
        in_winner_reach=in_reach,
    )
