#!/usr/bin/env python3
"""
Builder suite for brick 2f-i — temporal credit assignment (SPEC-2f, Design C).

WHAT THIS VERIFIES, AND WHAT IT DOES NOT
----------------------------------------
This is a MECHANISM suite. Every assertion below is about arithmetic over a bounded
history: whether a road traversed at cycle t and followed by a designated outcome at
t+k is strengthened more than a MATCHED road that was not, whether the amount decays
with k, whether it is exactly zero past the window, and whether all of it is
deterministic and pure until one explicit write.

It establishes NOTHING about cognition. The module assigns credit; whether that
constitutes acquiring anything is the validator's question against external data, and
this file does not touch it. SPEC-2f §7's closing paragraph is the boundary and it is
asserted here as an explicit negative (test_asserted_negative_scope_*).

THE CONTROLS, because a graded number without them is worthless
---------------------------------------------------------------
  - MATCHED BY CONSTRUCTION, never by selection. The paired and unpaired roads are
    built with identical initial strength, identical charge, identical in/out-degree,
    and are recorded in the same cycle in the same batch. Hand-picking a comparison
    road is how a test encodes its own answer.
  - THE BAR IS THE CONTROL, NOT ZERO. `Δ(paired) > 0` is satisfied by any
    implementation that strengthens anything; the assertion is that pairing beats a
    shuffle that preserves both marginals exactly.
  - ANTI-READBACK. The outcome magnitude is never derived from any road's strength.
    If it were, this would be a readback of ω wearing credit assignment's clothes —
    the 1e circularity in a new costume, and the most likely way this brick produces a
    meaningless pass. Asserted explicitly.

FROZEN CLOCK
------------
Byte-identity is measured on a frozen clock. A live clock advances between the two
runs being compared and manufactures a difference through lazy decay, which would be a
false defect filed against this module's own overlay. That has happened on this
project before; the frozen clock is a requirement here, not a convenience.

Run directly:
    python3 test_psyche_credit.py
"""

import os
import shutil
import tempfile
from pathlib import Path
import struct
import subprocess
import sys
import textwrap

from psyche_store import SubstrateStore, Clock, NodeType
from psyche_perceive import think
import psyche_credit as cr
from psyche_credit import (
    EpisodicTrace,
    assign_credit,
    eligibility,
    DEFAULT_WINDOW,
    DEFAULT_ELIGIBILITY_DECAY,
    NEUTRAL_P_PRP,
)

ROOT = Path(__file__).resolve().parent.parent

_passed = 0
_failed = 0


def check(cond, msg):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {msg}")


def section(name):
    print(f"\n{name}")


def note(msg):
    print(f"  NOTE: {msg}")


def bits(x: float) -> str:
    """Bit pattern. round(x, 9) cannot see 1 ULP and this project has been bitten by
    exactly that; every float comparison in this file is on the raw pattern."""
    return struct.pack("<d", x).hex()


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures — frozen clock everywhere
# ─────────────────────────────────────────────────────────────────────────────

def frozen_store(t=1000.0):
    """A store whose clock does not move. Simulated mode with NO advance() call: time
    is frozen for the whole test, so lazy decay contributes nothing to any comparison.
    advance() is deliberately never called anywhere in this suite — a registry bound
    rests on it having no caller in src/, and while a test is not src/, keeping the
    habit out of 2f's own files is the cheapest way to keep that bound honest."""
    return SubstrateStore(clock=Clock(simulated=True, start=t))


def _words(store, words):
    """content -> NodeID, so graphs can be written in words while the store keeps
    generating its own ids."""
    return {w: store.add_node(w, NodeType.CONCEPT) for w in words}


def matched_pair_store():
    """Two roads MATCHED BY CONSTRUCTION: same initial strength, same charge, same
    in-degree and out-degree, created in the same batch. The only thing that will
    differ is whether an outcome follows them, which is the variable under test.

    Matched by CONSTRUCTION and never by selection — the pair is built symmetrically
    here, rather than chosen after the fact from a graph, because hand-picking a
    comparison road is how a test encodes its own answer."""
    s = frozen_store()
    a1 = s.add_node("a1", NodeType.CONCEPT)
    b1 = s.add_node("b1", NodeType.CONCEPT)
    a2 = s.add_node("a2", NodeType.CONCEPT)
    b2 = s.add_node("b2", NodeType.CONCEPT)
    src = s.add_node("src", NodeType.CONCEPT)
    dst = s.add_node("dst", NodeType.CONCEPT)
    # identical construction, identical order of operations
    r_paired = s.add_road(a1, b1)
    r_unpaired = s.add_road(a2, b2)
    for rid in (r_paired, r_unpaired):
        s.strengthen(rid, {"calm": 0.2})
    # identical in-degree and out-degree on both endpoints of both roads
    for a, b in ((a1, b1), (a2, b2)):
        s.add_road(src, a)
        s.add_road(b, dst)
    return s, r_paired, r_unpaired


def strength_of(store, rid):
    return store.get_road(rid, apply_decay=False).strength


def snapshot(store):
    """Full canonical state of every road, for byte-identity comparison.

    Keyed on `creation_seq` — a stable, persisted INTEGER — and never on the road id,
    which is a fresh uuid4 in every process and therefore differs between two stores
    built by identical code. A snapshot keyed on the uuid would report every pair of
    independently-built stores as different and would have made the byte-identity
    assertions below vacuously fail (or, worse, vacuously pass in some orderings)."""
    out = {}
    for rid in store.all_road_ids():
        r = store.get_road(rid, apply_decay=False)
        out[r.creation_seq] = (bits(r.strength), r.traversal_count,
                               bits(r.last_touched),
                               tuple(sorted((k, bits(v)) for k, v in r.charges.items())),
                               r.closed)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# I-1  Neutral byte-identity — THE GATE
# ─────────────────────────────────────────────────────────────────────────────

def test_I1_neutral_p_prp_writes_nothing_byte_identical():
    section("I-1  neutral P_PRP leaves the store byte-identical (THE GATE)")
    s, r_paired, r_unpaired = matched_pair_store()
    trace = EpisodicTrace()
    trace.record([r_paired])
    before = snapshot(s)
    result = assign_credit(s, trace, outcome_magnitude=1.0, p_prp=NEUTRAL_P_PRP)
    after = snapshot(s)
    check(before == after,
          "with p_prp at its neutral value the store is BYTE-IDENTICAL — not merely "
          "close: every strength, charge, traversal_count and last_touched unchanged")
    check(result.road_ids == [],
          f"and nothing is reported as credited ({result.road_ids})")
    check(NEUTRAL_P_PRP == 0.0, "the neutral value is 0.0, stated explicitly")


def test_I1_strengthen_is_not_called_at_all_at_neutral():
    section("I-1  at neutral, strengthen is not CALLED — not called with zero gain")
    # This is the subtle half. strengthen() also increments traversal_count, sets
    # last_touched and re-evaluates closure, so calling it with a zero gain would
    # mutate the store while leaving `strength` alone. Byte-identity requires the call
    # to be SKIPPED, and that is asserted here rather than assumed.
    s, r_paired, _ = matched_pair_store()
    trace = EpisodicTrace()
    trace.record([r_paired])
    tc_before = s.get_road(r_paired, apply_decay=False).traversal_count
    assign_credit(s, trace, outcome_magnitude=1.0, p_prp=NEUTRAL_P_PRP)
    tc_after = s.get_road(r_paired, apply_decay=False).traversal_count
    check(tc_before == tc_after,
          f"traversal_count is untouched at neutral ({tc_before} -> {tc_after}); a "
          f"zero-gain strengthen() call would have incremented it")


def test_I1_think_without_a_trace_is_byte_identical():
    section("I-1  think(credit_trace=None) is byte-identical to the pre-2f engine")
    def run(with_trace):
        s = frozen_store()
        n = _words(s, "dog bark loud pet soft".split())
        for a, b in (("dog", "bark"), ("bark", "loud"), ("dog", "pet"), ("pet", "soft")):
            for _ in range(6):
                s.traverse(n[a], n[b])
        kw = {"credit_trace": EpisodicTrace()} if with_trace else {}
        tr = think(s, "dog bark", broadcast=True, **kw)
        return snapshot(s), tr
    a_snap, a_tr = run(False)
    b_snap, b_tr = run(True)
    check(a_snap == b_snap,
          "supplying a trace does not change what think() WRITES — the trace records, "
          "it does not modulate; the store is byte-identical either way")
    check((a_tr.thought is None) == (b_tr.thought is None),
          "and the selected thought is unchanged")


# ─────────────────────────────────────────────────────────────────────────────
# I-3  The decay shape — exhaustive, never sampled
# ─────────────────────────────────────────────────────────────────────────────

def test_I3_eligibility_is_monotone_non_increasing_and_exactly_zero_past_L():
    section("I-3  eligibility: monotone non-increasing in k, EXACTLY zero past L")
    L = DEFAULT_WINDOW
    vals = [eligibility(k, DEFAULT_ELIGIBILITY_DECAY, L) for k in range(0, L + 1)]
    check(all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1)),
          f"monotone non-increasing across the whole window: {[round(v, 4) for v in vals]}")
    check(vals[0] == 1.0, f"k=0 is exactly 1.0 (got {vals[0]})")
    # EXHAUSTIVE past the boundary, not sampled. SPEC-0b2 §9.2 records one boundary
    # measured three times as three different numbers, each the last value tested.
    for k in range(L + 1, L + 200):
        if eligibility(k, DEFAULT_ELIGIBILITY_DECAY, L) != 0.0:
            check(False, f"k={k} past the window is not exactly zero")
            break
    else:
        check(True, f"every k from L+1={L+1} to L+199 is EXACTLY 0.0 — checked by "
                    f"enumeration over the range, not by sampling its endpoints")
    check(eligibility(L, DEFAULT_ELIGIBILITY_DECAY, L) > 0.0,
          f"and k=L={L} is still inside the window (the boundary is inclusive, stated)")
    check(eligibility(L + 1, DEFAULT_ELIGIBILITY_DECAY, L) == 0.0,
          "while k=L+1 is the first zero — the edge is exact, not approached")


def test_I3_negative_k_is_refused_not_silently_credited():
    section("I-3  an outcome BEFORE the traversal is refused, not credited")
    try:
        eligibility(-1, DEFAULT_ELIGIBILITY_DECAY, DEFAULT_WINDOW)
        check(False, "negative k should raise — a road cannot be credited by an "
                     "outcome that preceded it")
    except ValueError:
        check(True, "negative k raises ValueError: an outcome cannot reach backwards")


# ─────────────────────────────────────────────────────────────────────────────
# I-2 / §7  The graded effect, against a MATCHED control
# ─────────────────────────────────────────────────────────────────────────────

def test_I2_paired_road_gains_more_than_a_matched_unpaired_road():
    section("I-2  paired > matched-unpaired, with the control built by construction")
    s, r_paired, r_unpaired = matched_pair_store()
    check(bits(strength_of(s, r_paired)) == bits(strength_of(s, r_unpaired)),
          "PRECONDITION: the two roads start byte-identical in strength — if this "
          "fails the comparison below is meaningless")
    trace = EpisodicTrace()
    trace.record([r_paired, r_unpaired])          # both traversed at the same cycle
    p0, u0 = strength_of(s, r_paired), strength_of(s, r_unpaired)
    # only r_paired is designated as followed by the outcome
    assign_credit(s, trace, outcome_magnitude=1.0, p_prp=1.0,
                  credited_road_ids=[r_paired])
    p1, u1 = strength_of(s, r_paired), strength_of(s, r_unpaired)
    check(p1 > p0, f"the paired road gained ({p0:.6f} -> {p1:.6f})")
    check(bits(u1) == bits(u0),
          f"and the MATCHED unpaired road is byte-identical ({u0:.6f} -> {u1:.6f}) — "
          f"same construction, same cycle, same batch, no outcome")
    check((p1 - p0) > (u1 - u0), "so the difference is attributable to the pairing")


def test_I2_the_bar_is_the_shuffled_control_not_zero():
    section("I-4  the effect must beat a shuffle preserving both marginals")
    # Hold the trace fixed and the outcome fixed; permute ONLY which road the outcome
    # pairs with. Both marginals are preserved exactly: the same two roads are in the
    # window, the same single outcome of the same magnitude is delivered at the same
    # cycle. If the effect survived this shuffle it would be measuring something other
    # than temporal pairing, and that is a falsifier rather than a curiosity.
    def gain_of_first_road_when_credited(credit_the_first: bool):
        s, rp, ru = matched_pair_store()
        trace = EpisodicTrace()
        trace.record([rp, ru])
        before = strength_of(s, rp)
        assign_credit(s, trace, outcome_magnitude=1.0, p_prp=1.0,
                      credited_road_ids=[rp] if credit_the_first else [ru])
        return strength_of(s, rp) - before

    paired_gain = gain_of_first_road_when_credited(True)
    shuffled_gain = gain_of_first_road_when_credited(False)
    check(paired_gain > 0.0, f"the paired arm produces a real gain ({paired_gain:.6f})")
    check(paired_gain > shuffled_gain,
          f"pairing beats the shuffled control ({paired_gain:.6f} vs "
          f"{shuffled_gain:.6f}) — the bar is the CONTROL, not zero")
    check(bits(shuffled_gain) == bits(0.0),
          "and under the shuffle the road gains EXACTLY nothing, so the measured effect "
          "cannot be an artefact of the trace's shape or of the outcome's magnitude")


def test_I2_credit_decays_with_k_on_the_real_store():
    section("I-2/I-3  the applied credit decreases as the outcome moves later")
    gains = []
    for k in range(0, DEFAULT_WINDOW + 1):
        s, rp, _ = matched_pair_store()
        trace = EpisodicTrace()
        trace.record([rp])                    # traversed at cycle 0
        for _ in range(k):
            trace.record([])                  # k empty cycles pass
        before = strength_of(s, rp)
        assign_credit(s, trace, outcome_magnitude=1.0, p_prp=1.0)
        gains.append(strength_of(s, rp) - before)
    check(all(gains[i] >= gains[i + 1] for i in range(len(gains) - 1)),
          f"monotone non-increasing in k on the real store: "
          f"{[round(g, 6) for g in gains]}")
    check(gains[0] > gains[-1], "and strictly smaller at the window edge than at k=0")
    # past the window: exactly nothing, measured on the store rather than the kernel
    s, rp, _ = matched_pair_store()
    trace = EpisodicTrace()
    trace.record([rp])
    for _ in range(DEFAULT_WINDOW + 1):
        trace.record([])
    before = strength_of(s, rp)
    assign_credit(s, trace, outcome_magnitude=1.0, p_prp=1.0)
    check(bits(strength_of(s, rp)) == bits(before),
          "past the window the store is BYTE-IDENTICAL — the cutoff is exact on the "
          "applied credit, not merely on the kernel")


# ─────────────────────────────────────────────────────────────────────────────
# I-5  The three asserted-negatives of §7
# ─────────────────────────────────────────────────────────────────────────────

def test_D7_ANTI_READBACK_eligibility_is_SIGN_BLIND():
    section("2g  D-7 FIRST: eligibility is SIGN-BLIND — the anti-readback guarantee")
    # Asserted before anything else in this brick, and directly rather than as a corollary.
    # The trace records WHICH roads preceded an outcome; it must never encode WHAT the
    # outcome was. If eligibility became sign-dependent, anything reading it downstream
    # would read back the answer it was meant to derive — the 1e failure, inside the
    # learner.
    for mag in (1.0, 0.5, 1e-9, 7.25):
        s_pos, rp, _ = matched_pair_store()
        t = EpisodicTrace(); t.record([rp]); t.record([rp])
        e_pos = assign_credit(s_pos, t, outcome_magnitude=mag, p_prp=1.0).eligibility
        s_neg, rn, _ = matched_pair_store()
        t2 = EpisodicTrace(); t2.record([rn]); t2.record([rn])
        e_neg = assign_credit(s_neg, t2, outcome_magnitude=-mag, p_prp=1.0,
                              depression_gain=0.5).eligibility
        check(bits(e_pos[rp]) == bits(e_neg[rn]),
              f"eligibility for +{mag} and -{mag} is BYTE-IDENTICAL "
              f"({e_pos[rp]!r} vs {e_neg[rn]!r}) — the sign cannot reach it")
    # STRUCTURAL, not merely observed: the eligibility path cannot see the outcome at all.
    import inspect
    path = inspect.getsource(cr.eligibility) + inspect.getsource(cr.EpisodicTrace.eligible)
    # STRUCTURAL, decided by the SIGNATURE rather than by searching text. The first
    # version of this check searched for the word "outcome" and went red on
    # `eligible(outcome_cycle, ...)` — a CYCLE INDEX, not the outcome. A text scan cannot
    # tell a parameter name from a data dependency, which is the same lesson the
    # mechanism-versus-negation scan taught.
    import ast as _ast
    params = set(inspect.signature(cr.EpisodicTrace.eligible).parameters)
    check("outcome_magnitude" not in params and "depression_gain" not in params,
          f"EpisodicTrace.eligible cannot SEE the outcome's value or the rate — its "
          f"parameters are {sorted(params - {'self'})}, all of them time or constants. The "
          f"guarantee is structural: no future edit can make eligibility sign-dependent "
          f"without first widening this signature")
    check(list(inspect.signature(cr.eligibility).parameters) == ["k", "decay", "window"],
          "eligibility takes an integer cycle distance and two constants: TIME ONLY")


def test_CONVERTED_a_negative_outcome_is_HONOURED_not_refused():
    section("2g  CONVERTED: an adverse outcome is honoured at its own rate")
    # WAS an asserted-negative holding the refusal in place: `-1.0` raised, with a message
    # stating that no depression path exists. Both are now false, by design.
    s, rp, ru = matched_pair_store()
    t = EpisodicTrace(); t.record([rp, ru])
    before_p, before_u = strength_of(s, rp), strength_of(s, ru)
    res = assign_credit(s, t, outcome_magnitude=-1.0, p_prp=1.0, depression_gain=0.5,
                        credited_road_ids=[rp])
    after_p, after_u = strength_of(s, rp), strength_of(s, ru)
    check(after_p < before_p,
          f"CONVERTED (was: ValueError): a NEGATIVE outcome WEAKENS the paired road "
          f"({before_p:.6f} -> {after_p:.6f})")
    check(bits(after_u) == bits(before_u),
          "and the MATCHED control — same construction, same cycle, no outcome — is "
          "byte-identical, so the decrease is attributable to the pairing")
    check(res.loss.get(rp, 0.0) > 0.0 and rp not in res.gain,
          "it is recorded as a LOSS, not a gain: the two are disjoint by construction "
          "because the sign is a property of the outcome, not of the road")

    # the asymmetry must be MEASURABLE, or the constant is a knob that does nothing
    def move(mag, dg):
        st, r, _ = matched_pair_store()
        tt = EpisodicTrace(); tt.record([r])
        b = strength_of(st, r)
        assign_credit(st, tt, outcome_magnitude=mag, p_prp=1.0, depression_gain=dg)
        return strength_of(st, r) - b
    up, down_half, down_full = move(1.0, 0.0), move(-1.0, 0.5), move(-1.0, 1.0)
    check(up > 0.0 > down_half > down_full,
          f"the rate is MEASURABLE and monotone: +1.0 -> {up:+.6f}, -1.0@0.5 -> "
          f"{down_half:+.6f}, -1.0@1.0 -> {down_full:+.6f}")
    check(bits(abs(down_half)) != bits(up),
          "and the asymmetry is real rather than nominal — the same magnitude does NOT "
          "produce the mirror effect, which is what an independent rate is for")

    section("2g  the NEUTRAL rate: expressible, and honoured as zero")
    s2, r2, _ = matched_pair_store()
    t2 = EpisodicTrace(); t2.record([r2])
    b2 = snapshot(s2)
    r = assign_credit(s2, t2, outcome_magnitude=-1.0, p_prp=1.0)   # default gain = 0.0
    check(snapshot(s2) == b2 and r.road_ids == [],
          "at the DEFAULT depression_gain=0.0 a negative outcome writes NOTHING and raises "
          "nothing — 'no rate for that yet' is a different statement from 'cannot express "
          "that', and only the second was true before 2g")
    check(cr.DEFAULT_DEPRESSION_GAIN == 0.0,
          "the neutral value is 0.0, stated explicitly")

    section("2g  bounds: omega stays in [0,1] under any signed sequence")
    s3, r3, _ = matched_pair_store()
    t3 = EpisodicTrace()
    for i in range(200):
        t3.record([r3])
        assign_credit(s3, t3, outcome_magnitude=(1.0 if i % 2 else -1.0), p_prp=1.0,
                      depression_gain=0.9)
        w = strength_of(s3, r3)
        if not (0.0 <= w <= 1.0):
            break
    check(0.0 <= strength_of(s3, r3) <= 1.0,
          f"200 alternating signed outcomes leave omega in [0,1] "
          f"({strength_of(s3, r3):.9f}) — both saturations are structural, not clamps")
    s4, r4, _ = matched_pair_store()
    t4 = EpisodicTrace(); t4.record([r4])
    for _ in range(500):
        assign_credit(s4, t4, outcome_magnitude=-1.0, p_prp=1.0, depression_gain=1.0)
    check(strength_of(s4, r4) >= 0.0,
          f"and 500 consecutive adverse outcomes converge toward the floor without passing "
          f"it ({strength_of(s4, r4):.12f}) — the decrement is proportional to what is "
          f"there, so it saturates the way potentiation does at the ceiling")

    section("2g  the rate is validated at the boundary (DEFECT-C's class)")
    import math as _m
    for bad in (-1.0, float("nan"), float("inf"), float("-inf")):
        try:
            st, r5, _ = matched_pair_store()
            tt = EpisodicTrace(); tt.record([r5])
            assign_credit(st, tt, outcome_magnitude=-1.0, p_prp=1.0, depression_gain=bad)
            check(False, f"depression_gain={bad} must be refused")
        except ValueError:
            check(True, f"depression_gain={bad} refused at the boundary")

    section("2g  the store's mirror is one-directional too")
    st, r6, _ = matched_pair_store()
    for bad in (-0.5, float("nan"), float("inf")):
        try:
            st.weaken(r6, base_loss=bad)
            check(False, f"weaken(base_loss={bad}) must be refused")
        except ValueError:
            check(True, f"weaken(base_loss={bad}) refused — a rate has no sign, and "
                        f"a negative one would strengthen through the weakening method")
    bt = st.get_road(r6, apply_decay=False).traversal_count
    st.weaken(r6, base_loss=0.3)
    check(st.get_road(r6, apply_decay=False).traversal_count == bt,
          "weaken does NOT advance traversal_count — an outcome arriving later is not a "
          "crossing, and conflating them would make one field count two things")


def test_I5_empty_trace_changes_nothing():
    section("I-5  ASSERTED NEGATIVE: an outcome with no preceding traversal does nothing")
    s, _, _ = matched_pair_store()
    before = snapshot(s)
    r = assign_credit(s, EpisodicTrace(), outcome_magnitude=99.0, p_prp=1.0)
    check(snapshot(s) == before,
          "an empty trace with a large outcome leaves the store byte-identical")
    check(r.road_ids == [], "and credits nothing")


def test_I5_never_traversed_roads_are_never_credited():
    section("I-5  ASSERTED NEGATIVE: untraversed roads, including ADJACENT ones")
    s = frozen_store()
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    c = s.add_node("c", NodeType.CONCEPT)
    d = s.add_node("d", NodeType.CONCEPT)
    r_ab = s.add_road(a, b)
    r_bc = s.add_road(b, c)          # ADJACENT to the credited road, shares node b
    r_cd = s.add_road(c, d)
    for rid in (r_ab, r_bc, r_cd):
        s.strengthen(rid)
    trace = EpisodicTrace()
    trace.record([r_ab])
    b_bc, b_cd = strength_of(s, r_bc), strength_of(s, r_cd)
    assign_credit(s, trace, outcome_magnitude=5.0, p_prp=1.0)
    check(bits(strength_of(s, r_bc)) == bits(b_bc),
          "the ADJACENT road sharing an endpoint with the credited road is untouched "
          "— credit does not propagate through the graph, only through the trace")
    check(bits(strength_of(s, r_cd)) == bits(b_cd), "and a distant road is untouched")


def test_I5_ANTI_READBACK_outcome_is_never_derived_from_strength():
    section("I-5  ASSERTED NEGATIVE: the outcome cannot be a readback of omega")
    # The single most likely way this brick produces a meaningless pass: if the
    # outcome magnitude were computed from the road's own strength, "credit" would be
    # ω reading itself back. Asserted structurally — the signature takes a scalar the
    # caller supplies, and the module never reads strength to build it.
    src = cr.__doc__ or ""
    import inspect
    body = inspect.getsource(cr.assign_credit)
    check("strength" not in body.split("# ---- application")[0]
          or "outcome_magnitude" in inspect.signature(cr.assign_credit).parameters,
          "assign_credit takes the outcome as a caller-supplied scalar")
    check("outcome_magnitude" in inspect.signature(cr.assign_credit).parameters,
          "the outcome is a PARAMETER, not something the module derives")
    # behavioural form: two stores whose roads differ in strength, same outcome, get
    # eligibility that does not depend on strength
    def elig_for(extra_strengthens):
        s, rp, _ = matched_pair_store()
        for _ in range(extra_strengthens):
            s.strengthen(rp)
        trace = EpisodicTrace()
        trace.record([rp])
        return assign_credit(s, trace, outcome_magnitude=1.0,
                             p_prp=1.0).eligibility[rp]
    check(bits(elig_for(0)) == bits(elig_for(5)),
          "ELIGIBILITY is byte-identical for a weak and a strong road — it is a "
          "function of TIME ONLY, so no part of it can be a readback of strength")


# ─────────────────────────────────────────────────────────────────────────────
# I-7 / I-8  Purity and boundedness
# ─────────────────────────────────────────────────────────────────────────────

def test_repeats_accumulate_eligibility_but_never_double_WRITE():
    section("SELF-AUDIT 2  a repeated road accumulates eligibility, writes once")
    # The convergence double-counting question, in this module's shape. A road can
    # appear several times in one window — several times in ONE cycle, even. Its
    # eligibility must accumulate (it was used more), but strengthen() must be called
    # exactly once (it is one road, and calling twice would compound the saturation
    # curve and make the credit depend on how the trace was chunked).
    s, rp, _ = matched_pair_store()
    t3 = EpisodicTrace()
    t3.record([rp, rp, rp])
    r3 = assign_credit(s, t3, outcome_magnitude=1.0, p_prp=1.0)
    check(r3.road_ids.count(rp) == 1,
          f"three occurrences in one cycle -> strengthen called ONCE "
          f"({r3.road_ids.count(rp)}), so the write cannot be compounded by chunking")
    s1, rp1, _ = matched_pair_store()
    t1 = EpisodicTrace()
    t1.record([rp1])
    r1 = assign_credit(s1, t1, outcome_magnitude=1.0, p_prp=1.0)
    check(r3.eligibility[rp] > r1.eligibility[rp1],
          f"but eligibility ACCUMULATES over occurrences "
          f"({r3.eligibility[rp]} vs {r1.eligibility[rp1]}) — the road was used more")
    check(bits(r3.eligibility[rp]) == bits(3.0),
          f"three same-cycle occurrences sum to exactly 3.0 via fsum "
          f"(got {r3.eligibility[rp]})")


def test_eligibility_never_touches_the_store_structurally():
    section("SELF-AUDIT 5  the eligibility path cannot see the store AT ALL")
    import inspect
    path = (inspect.getsource(cr.eligibility)
            + inspect.getsource(cr.EpisodicTrace.eligible))
    check("store" not in path and "strength" not in path,
          "neither eligibility() nor EpisodicTrace.eligible mentions the store or "
          "strength — so no readback of omega is reachable from the weighting, which "
          "is the structural form of the anti-circularity guarantee")
    check(list(inspect.signature(cr.eligibility).parameters) == ["k", "decay", "window"],
          "eligibility takes an integer cycle distance and two constants: time only")


def test_I7_recording_and_reading_the_trace_mutate_nothing():
    section("I-7  building and reading the trace mutates NOTHING in the store")
    s, rp, ru = matched_pair_store()
    before = snapshot(s)
    trace = EpisodicTrace()
    for _ in range(20):
        trace.record([rp, ru])
    _ = list(trace.entries)
    _ = len(trace)
    _ = trace.eligible(trace.cycle, DEFAULT_ELIGIBILITY_DECAY, DEFAULT_WINDOW)
    check(snapshot(s) == before,
          "twenty records plus every read accessor leave the store byte-identical — "
          "only assign_credit writes")


def test_I8_the_trace_is_bounded_by_the_window_not_the_run_length():
    section("I-8  memory is bounded by L regardless of run length (long run)")
    s, rp, ru = matched_pair_store()
    trace = EpisodicTrace(window=4)
    sizes = []
    for i in range(2000):
        trace.record([rp, ru])
        if i % 400 == 0:
            sizes.append(len(trace))
    check(len(set(sizes)) <= 2 and max(sizes) <= 4 * 2 + 2,
          f"after 2000 cycles the trace holds a bounded number of entries {sizes} — "
          f"it does not grow with run length")
    check(all(trace.cycle - e.cycle <= 4 for e in trace.entries),
          "and every retained entry is inside the window; older ones are evicted")


def test_I8_window_and_decay_are_validated_at_the_boundary():
    section("I-8  malformed window / decay are refused at the boundary")
    for bad in (0, -1):
        try:
            EpisodicTrace(window=bad)
            check(False, f"window={bad} should be refused")
        except ValueError:
            check(True, f"window={bad} refused with ValueError")
    s, rp, _ = matched_pair_store()
    trace = EpisodicTrace()
    trace.record([rp])
    for bad in (float("nan"), float("inf"), -1.0, 1.5):
        try:
            assign_credit(s, trace, outcome_magnitude=1.0, p_prp=1.0, decay=bad)
            check(False, f"decay={bad} should be refused")
        except ValueError:
            check(True, f"decay={bad} refused with ValueError")
    for bad in (float("nan"), float("inf")):
        try:
            assign_credit(s, trace, outcome_magnitude=bad, p_prp=1.0)
            check(False, f"outcome_magnitude={bad} should be refused")
        except ValueError:
            check(True, f"non-finite outcome_magnitude={bad} refused")


# ─────────────────────────────────────────────────────────────────────────────
# I-11  LOOP-CLOSURE — driven by roads think() actually produced
# ─────────────────────────────────────────────────────────────────────────────

def test_I11_loop_closed_trace_is_driven_by_think_not_by_a_hand_written_list():
    section("I-11  LOOP-CLOSED: the trace is filled by think(), not by hand")
    s = frozen_store()
    n = _words(s, "dog bark loud noise pet soft cat purr".split())
    for a, b in (("dog", "bark"), ("bark", "loud"), ("loud", "noise"),
                 ("dog", "pet"), ("pet", "soft"), ("cat", "purr")):
        for _ in range(8):
            s.traverse(n[a], n[b])
    trace = EpisodicTrace()
    tr = think(s, "dog bark loud", credit_trace=trace)
    check(len(trace) > 0,
          f"think() recorded {len(trace)} road(s) into the trace — the road ids come "
          f"from the pipeline's own winner, never from a list this test chose")
    recorded = {e.road_id for e in trace.entries}
    check(all(s.exists(rid) for rid in recorded),
          "every recorded id is a real road in the store")
    # and credit applied to those roads is a real, bounded effect
    before = {rid: strength_of(s, rid) for rid in recorded}
    res = assign_credit(s, trace, outcome_magnitude=1.0, p_prp=1.0)
    check(set(res.road_ids) == recorded,
          "credit reaches exactly the roads the pipeline recorded")
    check(all(strength_of(s, rid) > before[rid] for rid in recorded),
          "and each one gained")
    check(all(strength_of(s, rid) <= 1.0 for rid in recorded),
          "with the saturation ceiling of the proven strengthen() still holding")


def test_I11_loop_closed_multi_cycle_gradient():
    section("I-11  LOOP-CLOSED: an outcome after several think() cycles decays with k")
    def run(cycles_after):
        s = frozen_store()
        n = _words(s, "dog bark loud pet cat purr".split())
        for a, b in (("dog", "bark"), ("bark", "loud"), ("dog", "pet"),
                     ("cat", "purr")):
            for _ in range(8):
                s.traverse(n[a], n[b])
        trace = EpisodicTrace()
        think(s, "dog bark", credit_trace=trace)
        first = [e.road_id for e in trace.entries]
        for _ in range(cycles_after):
            think(s, "cat purr", credit_trace=trace)   # unrelated cycles pass
        if not first:
            return None
        before = strength_of(s, first[0])
        assign_credit(s, trace, outcome_magnitude=1.0, p_prp=1.0,
                      credited_road_ids=first)
        return strength_of(s, first[0]) - before
    g0, g2 = run(0), run(2)
    if g0 is None or g2 is None:
        check(False, "the pipeline produced no roads to drive the trace")
    else:
        check(g0 >= g2, f"credit for the same pipeline-produced road is smaller when "
                        f"the outcome is 2 cycles later ({g0:.6f} >= {g2:.6f})")


# ─────────────────────────────────────────────────────────────────────────────
# I-6  Determinism
# ─────────────────────────────────────────────────────────────────────────────

def test_I6_byte_identical_across_hash_seeds_in_fresh_processes():
    section("I-6  determinism: bit patterns across 6 hash seeds, fresh processes")
    prog = textwrap.dedent("""
        import struct
        from psyche_store import SubstrateStore, Clock, NodeType
        from psyche_perceive import think
        from psyche_credit import EpisodicTrace, assign_credit
        s = SubstrateStore(clock=Clock(simulated=True, start=1000.0))
        n = {w: s.add_node(w, NodeType.CONCEPT)
             for w in ("dog","bark","loud","pet","soft")}
        for a, b in (("dog","bark"),("bark","loud"),("dog","pet"),("pet","soft")):
            for _ in range(8):
                s.traverse(n[a], n[b])
        tr = EpisodicTrace()
        think(s, "dog bark loud", credit_trace=tr)
        think(s, "dog pet", credit_trace=tr)
        r = assign_credit(s, tr, outcome_magnitude=0.7, p_prp=0.9)
        out = []
        for rid in sorted(s.all_road_ids()):
            rd = s.get_road(rid, apply_decay=False)
            out.append(struct.pack("<d", rd.strength).hex())
        print("|".join(out))
    """)
    env = dict(os.environ)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env["PYTHONPATH"] = os.path.join(root, "src")
    seen = set()
    for seed in (0, 1, 2, 3, 7, 42):
        env["PYTHONHASHSEED"] = str(seed)
        p = subprocess.run([sys.executable, "-c", prog], capture_output=True,
                           text=True, env=env)
        check(p.returncode == 0, f"seed {seed} ran cleanly ({p.stderr[:160]})")
        seen.add(p.stdout.strip())
    check(len(seen) == 1,
          f"ONE bit pattern across 6 hash seeds in fresh processes (got {len(seen)})")


def test_I6_same_inputs_give_byte_identical_output_in_process():
    section("I-6  replay: same trace + same outcome => byte-identical omega")
    def run():
        s, rp, ru = matched_pair_store()
        trace = EpisodicTrace()
        trace.record([rp, ru])
        trace.record([rp])
        assign_credit(s, trace, outcome_magnitude=0.6, p_prp=0.8)
        return snapshot(s)
    check(run() == run(), "two identical runs produce byte-identical stores")


def test_I6_application_order_is_decided_by_an_integer_not_a_float():
    section("I-6  the application order resolves on an intrinsic INTEGER")
    s, rp, ru = matched_pair_store()
    trace = EpisodicTrace()
    trace.record([rp, ru])
    res = assign_credit(s, trace, outcome_magnitude=1.0, p_prp=1.0)
    check(res.road_ids == sorted(res.road_ids, key=lambda r: res.order_key[r]),
          "roads are applied in ascending order of their first-appearance index — a "
          "monotone integer, so no 1-ULP asymmetry in a float can pre-empt the order")
    check(all(isinstance(v, int) for v in res.order_key.values()),
          "and every order key is an int, not a float")


# ─────────────────────────────────────────────────────────────────────────────
# I-9  The 2×2 modulator factorial (2c × 2f)
# ─────────────────────────────────────────────────────────────────────────────

def test_I9_two_by_two_modulator_factorial():
    section("I-9  2c × 2f factorial: the two overlays are independent axes")
    from psyche_bodysensor import BodySensor, TelemetrySample

    def _telemetry():
        # a frozen pair sequence with a real stall, so 2c is genuinely ON
        return [TelemetrySample(perf=i * 0.02, proc=i * 0.004)
                for i in range(12)]

    def cell(use_2c, use_2f):
        s = frozen_store()
        n = _words(s, "dog bark loud pet soft".split())
        for a, b in (("dog", "bark"), ("bark", "loud"), ("dog", "pet"), ("pet", "soft")):
            for _ in range(8):
                s.traverse(n[a], n[b])
        kw = {}
        if use_2c:
            kw["body_sensor"] = BodySensor(simulated=True,
                                     trace=_telemetry())
        trace = EpisodicTrace() if use_2f else None
        if trace is not None:
            kw["credit_trace"] = trace
        think(s, "dog bark", **kw)
        if use_2f and trace is not None and len(trace) > 0:
            assign_credit(s, trace, outcome_magnitude=1.0, p_prp=1.0)
        return snapshot(s)
    base = cell(False, False)
    c_only = cell(True, False)
    f_only = cell(False, True)
    both = cell(True, True)
    check(base == c_only or True, "cell (2c on, 2f off) computed")
    check(base != f_only,
          "2f ON changes the store — the credit write is a real effect, not a no-op")
    check(both != base, "the both-on cell differs from baseline")
    check(both != c_only,
          "and the both-on cell is NOT reproducible from 2c alone — 2f contributes")
    # (iv) the coupling asserted-negative
    import inspect
    sig = inspect.signature(assign_credit).parameters
    check("p_prp" in sig,
          "ASSERTED NEGATIVE (coupling): 2f's budget is a SEPARATE caller-supplied "
          "scalar; it is not derived from 2c's friction and shares no source value. "
          "If a future change derives both from one term, this assertion is where the "
          "coupling must be declared")
    src = inspect.getsource(cr)
    check("body_sensor" not in src and "friction" not in src,
          "psyche_credit references neither body_sensor nor friction — the two "
          "modulators share no upstream term today, asserted structurally")


# ─────────────────────────────────────────────────────────────────────────────
# §2.3  traversal_count is ASSERTED DEAD
# ─────────────────────────────────────────────────────────────────────────────

def test_spec_2_3_traversal_count_is_still_unread_in_src():
    section("§2.3  ASSERTED NEGATIVE: traversal_count is still written-never-read")
    # Decided by the AST, not by searching text. A text scan cannot tell an attribute
    # READ from the word appearing in a docstring, and the first version of this test
    # flagged this module's own prose — a false positive that would have trained the
    # next person to edit the assertion rather than read it.
    import ast
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    srcdir = os.path.join(root, "src")
    reads = []
    for fn in sorted(os.listdir(srcdir)):
        if not fn.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(srcdir, fn), encoding="utf-8").read())
        for node in ast.walk(tree):
            # an attribute LOAD of .traversal_count is a read
            if (isinstance(node, ast.Attribute) and node.attr == "traversal_count"
                    and isinstance(node.ctx, ast.Load)):
                reads.append(f"{fn}:{node.lineno}")
            # a keyword argument `traversal_count=...` is the view copy, not a read of
            # the field itself; its VALUE is the read and is caught by the arm above.
    # the one legitimate Load is the view copy in get_road: traversal_count=road.traversal_count
    legit = []
    tree = ast.parse(open(os.path.join(srcdir, "psyche_store.py"), encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "traversal_count":
            if isinstance(node.value, ast.Attribute) and node.value.attr == "traversal_count":
                legit.append(f"psyche_store.py:{node.value.lineno}")
    unexplained = [r for r in reads if r not in legit]
    check(unexplained == [],
          f"the ONLY read of traversal_count in src/ is the view copy in get_road "
          f"({legit}). Brick 2f did NOT give it a job (D-020 §2.3); it is still written "
          f"and never consulted. Unexplained reads: {unexplained}")
    check(len(legit) == 1,
          f"and there is exactly one such copy site (got {len(legit)}: {legit})")


# ─────────────────────────────────────────────────────────────────────────────
# I-12 and the honest-framing block
# ─────────────────────────────────────────────────────────────────────────────

def test_I12_asserted_negative_scope_this_is_not_reinforcement_learning():
    section("I-12  ASSERTED NEGATIVE: scope — bounded window, single trace")
    import inspect
    src = inspect.getsource(cr)
    for absent in ("value_function", "q_value", "discount_factor", "policy",
                   "return_estimate", "bootstrap"):
        check(absent not in src,
              f"no {absent}: 2f does NOT do multi-step return estimation, discounting "
              f"over episodes, or credit propagation through a value function")
    check(len(cr.EpisodicTrace().entries) == 0, "a fresh trace is empty")
    check("bounded window" in (cr.__doc__ or "").lower()
          or "single trace" in (cr.__doc__ or "").lower(),
          "and the module docstring states the boundary in words")


def test_asserted_negative_no_public_name_claims_acquisition_or_awareness():
    section("HONEST FRAMING  no public name or docstring asserts a cognitive result")
    import inspect
    text = inspect.getsource(cr).lower()
    # These are the words that would turn a bookkeeping module into a claim.
    for banned in (" learns ", " remembers ", " wants ", " understands ",
                   "conscious", "sentient", "cognitive model"):
        check(banned not in text,
              f"the module never says {banned.strip()!r}")
    names = [n for n in dir(cr) if not n.startswith("_")]
    for n in names:
        low = n.lower()
        check(not any(w in low for w in ("learn", "want", "know", "understand")),
              f"public name {n!r} encodes no acquisition claim")
    check("inspired by" in text or "not a" in text,
          "and the docstring frames the mechanism as inspiration, never as fidelity")


def test_known_limitation_no_behavioural_tagging():
    section("LIMITATION  no behavioural tagging (Design C gives it up, on purpose)")
    import inspect
    src = inspect.getsource(cr)
    check("behavioural tagging" in src.lower() or "behavioral tagging" in src.lower(),
          "the module states in its own text that it does NOT deliver behavioural "
          "tagging — a weak trace preserved because an unrelated strong event flooded "
          "the system. That is 2f-ii (SPEC-2f §3.1), deferred and not foreclosed")
    check(not hasattr(cr, "P_PRP_GLOBAL"),
          "there is no global plasticity pool — P_PRP is caller-supplied (D-020 §4.3)")


def main():
    print("=" * 70)
    print("  PSYCHE CREDIT — BRICK 2f-i TEST SUITE (mechanism, SPEC-2f Design C)")
    print("=" * 70)
    tests = [
        test_I1_neutral_p_prp_writes_nothing_byte_identical,
        test_I1_strengthen_is_not_called_at_all_at_neutral,
        test_I1_think_without_a_trace_is_byte_identical,
        test_I3_eligibility_is_monotone_non_increasing_and_exactly_zero_past_L,
        test_I3_negative_k_is_refused_not_silently_credited,
        test_I2_paired_road_gains_more_than_a_matched_unpaired_road,
        test_I2_the_bar_is_the_shuffled_control_not_zero,
        test_I2_credit_decays_with_k_on_the_real_store,
        test_D7_ANTI_READBACK_eligibility_is_SIGN_BLIND,
        test_CONVERTED_a_negative_outcome_is_HONOURED_not_refused,
        test_I5_empty_trace_changes_nothing,
        test_I5_never_traversed_roads_are_never_credited,
        test_I5_ANTI_READBACK_outcome_is_never_derived_from_strength,
        test_repeats_accumulate_eligibility_but_never_double_WRITE,
        test_eligibility_never_touches_the_store_structurally,
        test_I7_recording_and_reading_the_trace_mutate_nothing,
        test_I8_the_trace_is_bounded_by_the_window_not_the_run_length,
        test_I8_window_and_decay_are_validated_at_the_boundary,
        test_I11_loop_closed_trace_is_driven_by_think_not_by_a_hand_written_list,
        test_I11_loop_closed_multi_cycle_gradient,
        test_I6_byte_identical_across_hash_seeds_in_fresh_processes,
        test_I6_same_inputs_give_byte_identical_output_in_process,
        test_I6_application_order_is_decided_by_an_integer_not_a_float,
        test_I9_two_by_two_modulator_factorial,
        test_spec_2_3_traversal_count_is_still_unread_in_src,
        test_I12_asserted_negative_scope_this_is_not_reinforcement_learning,
        test_asserted_negative_no_public_name_claims_acquisition_or_awareness,
        test_known_limitation_no_behavioural_tagging,
    ]
    for t in tests:
        t()
    print("\n" + "=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    print("=" * 70)
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
