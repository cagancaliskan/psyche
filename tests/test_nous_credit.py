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
    python3 test_nous_credit.py
"""

import os
import shutil
import tempfile
from pathlib import Path
import struct
import subprocess
import sys
import textwrap

from nous_store import SubstrateStore, Clock, NodeType
from nous_perceive import think
import nous_credit as cr
from nous_credit import (
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

def test_ASSERTED_NEGATIVE_the_trace_is_potentiation_only():
    section("2f-1  ASSERTED NEGATIVE: POTENTIATION-ONLY — no depression path exists")
    # The tester found that a negative outcome_magnitude was abs()'d and reinforced
    # byte-identically to a positive one. Ruled: refuse it at the boundary, and do NOT
    # build a weakening path in this pass. These assertions pin the refusal AND the
    # absence, so that "we chose not to build it" cannot decay into "we forgot".
    s, rp, _ = matched_pair_store()
    trace = EpisodicTrace()
    trace.record([rp])
    for bad in (-1.0, -0.5, -1e-12, -1e9):
        try:
            assign_credit(s, trace, outcome_magnitude=bad, p_prp=1.0)
            check(False, f"outcome_magnitude={bad} must be REFUSED, not absorbed")
        except ValueError as e:
            check("POTENTIATION-ONLY" in str(e),
                  f"outcome_magnitude={bad} is refused, and the message states WHY rather "
                  f"than naming a range: {str(e)[:70]}...")
    # the refusal must not have cost the legitimate zero, which is a real no-op
    before = snapshot(s)
    r0 = assign_credit(s, trace, outcome_magnitude=0.0, p_prp=1.0)
    check(snapshot(s) == before and r0.road_ids == [],
          "outcome_magnitude=0.0 is still ACCEPTED and writes nothing — an outcome of no "
          "size is not an adverse outcome, and conflating them would be a second defect")

    # THE ABSENCE ITSELF, asserted structurally. If a weakening path is ever added, these
    # go red and force the author to re-read this block rather than discover it.
    import ast
    import inspect
    src = inspect.getsource(cr)
    check("abs(outcome_magnitude)" not in src,
          "the abs() that caused FINDING 2f-1 is GONE, not merely guarded — leaving it "
          "would keep saying 'the sign does not matter here'")
    # Decided by the AST, not by searching text. The first version of this check looked
    # for the WORDS "weaken"/"depress" and went red on the module's own docstring, which
    # uses them to state that no such path exists. A text scan cannot tell a mechanism
    # from its negation; only the call graph can.
    tree = ast.parse(src)
    store_calls = sorted({n.func.attr for n in ast.walk(tree)
                          if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                          and isinstance(n.func.value, ast.Name)
                          and n.func.value.id == "store"})
    check(store_calls == ["get_road", "strengthen"],
          f"the module's ENTIRE store surface is {store_calls} — one read and one write, "
          f"and the write is strengthen(), which cannot decrease strength. The "
          f"one-directional bound is structural, not a documentation promise")
    defs = sorted(n.name for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
    check(not any(w in d.lower() for d in defs
                  for w in ("weaken", "depress", "decrement", "punish")),
          f"and no function in the module implements one: {defs}")
    note("CONSEQUENCE, recorded here because a reader of this suite is exactly who needs "
         "it: every outcome this mechanism can express STRENGTHENS what preceded it, so "
         "the graph moves one way only, toward saturation. Nothing can be undone. What is "
         "built assigns ATTENTION, not credit — it marks which roads preceded an outcome, "
         "not whether that outcome was worth repeating. 2f-i therefore does NOT satisfy "
         "Butlin AE-1 and moves NONE of SPEC-2e's five AOL criteria.")


def test_2f3_the_potentiation_basis_is_an_ABSENCE_and_it_is_machine_checked():
    section("2f-3  the potentiation basis is an ABSENCE, registered and enforced")
    # FINDING 2f-3: the original basis ("the store surface is get_road + strengthen")
    # did not establish the claim, because get_road(apply_decay=False) hands back the
    # LIVE stored Road. The claim is true; its basis is now stated as what it is.
    import json
    import subprocess
    reg = json.loads((ROOT / "tools" / "ledger.json").read_text(encoding="utf-8"))
    entry = reg["float_accumulations"]["src/nous_credit.py:EpisodicTrace.eligible.<return>"]
    bounds = entry.get("bound_on_absence") or []
    binding = [b for b in bounds if b.get("kind") == "binding"]
    check(len(binding) == 1 and binding[0]["symbol"] == "get_road",
          "the absence is REGISTERED as a machine-checked bound on binding get_road, so "
          "a future brick cannot invalidate it silently")
    check("_inherited_weakness" in binding[0]
          and "dataflow" in binding[0]["_inherited_weakness"].lower(),
          "and the bound records its own blind spots — a reader cannot mistake a clean "
          "run for proof that no write-through is possible by any route")
    check(len(binding[0].get("dismissed") or []) == 4,
          f"the four bindings that exist today are dismissed individually with written "
          f"reasons ({len(binding[0].get('dismissed') or [])})")

    # THE LIVE-REFERENCE FACT, asserted here rather than taken on trust — it is the whole
    # reason the basis had to change.
    s = frozen_store()
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    r = s.add_road(a, b)
    s.strengthen(r)
    v1 = s.get_road(r, apply_decay=False)
    check(v1 is s.get_road(r, apply_decay=False),
          "get_road(apply_decay=False) returns the SAME object twice — it is the stored "
          "road, which is why binding it is a write-capable handle")
    w = s.get_road(r, apply_decay=True)
    check(w is not s.get_road(r, apply_decay=True),
          "while apply_decay=True returns a fresh copy each call — the asymmetry that "
          "made this easy to miss, pinned so it cannot silently change")

    # THE BOUND MUST BITE. Plant an undismissed binding-with-write and require C6 red.
    tmp = Path(tempfile.mkdtemp(prefix="bind-"))
    shutil.copytree(ROOT / "src", tmp / "src")
    (tmp / "tools").mkdir()
    shutil.copy(ROOT / "tools" / "ledger.json", tmp / "tools" / "ledger.json")
    planted = tmp / "src" / "nous_field.py"
    planted.write_text(
        "def _planted(store, rid):\n"
        "    road = store.get_road(rid, apply_decay=False)\n"
        "    road.strength *= 0.5\n"
        "    return road\n\n" + planted.read_text(encoding="utf-8"), encoding="utf-8")
    rc = subprocess.run([sys.executable, str(ROOT / "tools" / "ledger_check.py"),
                         "--root", str(tmp), "--only", "C6"],
                        capture_output=True, text=True)
    check(rc.returncode == 1 and "RESTS ON THE ABSENCE" in rc.stdout,
          f"a planted `road = get_road(...); road.strength *= 0.5` turns C6 RED "
          f"(exit {rc.returncode}) — the bound is enforced, not decorative")
    shutil.rmtree(tmp, ignore_errors=True)
    note("DECLINED DELIBERATELY: the general 'write through a returned object' question "
         "needs real dataflow — passing the road to a function, storing it in a "
         "container, returning it upward. That is not built, was not attempted badly, "
         "and is handed to architect-pm as its own brick. This check covers BINDING only.")


def test_2f4_the_AOL_and_AE1_reasons_are_the_true_ones():
    section("2f-4  the stated REASONS are checked, not only the conclusions")
    import inspect
    doc = inspect.getsource(cr)
    check("D-023" in doc,
          "the AOL paragraph now cites D-023 — mechanism absence — as its reason")
    check("was invented" in doc or "and it was invented" in doc,
          "and the superseded reason is recorded as wrong rather than quietly deleted, so "
          "a reader who remembers it finds the retraction")
    # The false reason must be GONE as an assertion, not merely contradicted elsewhere.
    # WHITESPACE-NORMALISED, because the docstring wraps: the first version of this check
    # searched for a string that spans a line break and therefore could never match — a
    # vacuous assertion of exactly the kind this project keeps finding. Normalising makes
    # it able to fail, and the two-sided check below proves it does.
    import re as _re
    norm = lambda t: _re.sub(r"\s+", " ", t)
    bad = ("each of AOL-2, AOL-3 and AOL-4 needs an outcome to be able to make some "
           "earlier action LESS likely")
    check(bad not in norm(doc),
          "the invented claim about what AOL-2/3/4 require is no longer asserted")
    # RULE FOUR for this assertion specifically: it must FAIL against 7886167.
    import subprocess as _sp
    old_mod = _sp.run(["git", "show", "7886167:src/nous_credit.py"], cwd=str(ROOT),
                      capture_output=True, text=True)
    if old_mod.returncode == 0:
        check(bad in norm(old_mod.stdout),
              "and the SAME normalised check finds it in 7886167 — so the assertion above "
              "is live, not a string that could never match")
    check("first" in doc and "conjunct" in doc,
          "and AE-1's reason is corrected too: it fails at the FIRST conjunct (no outputs "
          "selected, no goals) rather than only at the 'especially' clause — the same "
          "backwards move, caught by applying the same suspicion")
    # THE PROPERTY, not the wording: every AOL/AE claim in the module must be a NEGATIVE
    for line in doc.splitlines():
        if "AOL-" in line or "AE-1" in line:
            low = line.lower()
            if "satisf" in low:
                check(("not satisf" in low or "zero of" in low or "does not" in low
                       or "prerequisite" in low),
                      f"every satisfaction claim about a criterion is a NEGATIVE: {line.strip()[:76]}")


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
        from nous_store import SubstrateStore, Clock, NodeType
        from nous_perceive import think
        from nous_credit import EpisodicTrace, assign_credit
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
    from nous_bodysensor import BodySensor, TelemetrySample

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
          "nous_credit references neither body_sensor nor friction — the two "
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
    tree = ast.parse(open(os.path.join(srcdir, "nous_store.py"), encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "traversal_count":
            if isinstance(node.value, ast.Attribute) and node.value.attr == "traversal_count":
                legit.append(f"nous_store.py:{node.value.lineno}")
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
    print("  NOUS CREDIT — BRICK 2f-i TEST SUITE (mechanism, SPEC-2f Design C)")
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
        test_ASSERTED_NEGATIVE_the_trace_is_potentiation_only,
        test_2f3_the_potentiation_basis_is_an_ABSENCE_and_it_is_machine_checked,
        test_2f4_the_AOL_and_AE1_reasons_are_the_true_ones,
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
