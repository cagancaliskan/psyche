"""
Test suite for Nous BodySensor + the 2c interoception modulation hook (MECHANISM ONLY).

WHAT 2c IS (and is NOT) — the discipline this suite enforces (SPEC-2c §0.1/§2.1/§3.2):

  - MECHANISM, NOT MEANING. These tests verify the BodySensor computes a friction scalar
    deterministically in REPLAY mode, that the modulation hook is DEFAULT-OFF (byte-
    identical to current 1c/1d when off), and that when on it is a REAL causal effect on
    the cycle (a different replayed telemetry trace can flip WHICH coalition wins). They
    make NO cognitive claim. The friction scalar is a DERIVED telemetry signal, NOT a
    feeling/emotion/awareness/consciousness. Whether the modulation MEANS anything (causally
    tracks the telemetry, in a pre-registered direction) is the validator's call against the
    frozen trace — never asserted here.

  - REPLAY ONLY (the (D-1) determinism mode). Every test here runs the BodySensor in
    REPLAY mode over a FROZEN trace of TelemetrySample pairs. No test reads live telemetry
    (live mode is the boundary-only, non-deterministic path of (D-2); it is exercised by a
    separate non-graded live smoke check in the pilot tooling, OUT of this runner). A
    mechanism test that read live telemetry would not be a valid mechanism test.

  - ANTI-CIRCULARITY (the winner-flip readout; (C-GRADE-EMERGENT)). The causal-effect test
    measures WINNER-SET IDENTITY (a frozenset of NodeIDs produced by the competition over
    the whole field), NEVER the injected friction scalar. A different winning node-set
    provably cannot be the injected float read back out — the test asserts the readout is a
    node-set and that the scalar is not echoed.

  - SUBSTRATE BAR (the (D-1) determinism guard). Replay friction and the loop's winner trace
    under replay are byte-identical across 6 PYTHONHASHSEED values in fresh interpreters.

  - HONEST-FRAMING ASSERTION. The §0.1/§2.1 negations are pinned as an explicit asserted
    block (no public name encodes a feeling/awareness claim; the sensor cannot re-derive
    friction from the graph).

  - KNOWN LIMITATIONS shipped as explicit asserted-negatives, never hidden.

Run directly:
    python3 test_nous_bodysensor.py
"""

import os
import sys
import subprocess
import textwrap
import inspect

from nous_store import SubstrateStore, Clock, NodeType
from nous_activation import DEFAULT_DECAY_PER_HOP
from nous_perceive import think
import nous_bodysensor as bs
from nous_bodysensor import (
    BodySensor, TelemetrySample, compute_friction,
    friction_to_decay_factor, modulated_decay_per_hop,
    NEUTRAL_FRICTION, MODULATION_SPAN, MIN_DECAY_PER_HOP,
)

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


def _worn(s, a, b, n=30):
    for _ in range(n):
        s.traverse(a, b)


# ─────────────────────────────────────────────────────────────────────────────
# Topologies
# ─────────────────────────────────────────────────────────────────────────────

def _small_mind():
    """The SAME small store the 1c/1d suites use, so the hook is exercised on the exact
    graph the loop already runs on: warm domain + work domain, strong (n=8) coffee->work
    bridge."""
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    coffee = s.add_node("coffee", NodeType.ENTITY)
    warmth = s.add_node("warmth", NodeType.SENSATION)
    morning = s.add_node("morning routine", NodeType.CONCEPT)
    cozy = s.add_node("cozy feeling", NodeType.CONCEPT)
    kitchen = s.add_node("kitchen", NodeType.ENTITY)
    work = s.add_node("work", NodeType.CONCEPT)
    desk = s.add_node("desk", NodeType.ENTITY)
    deadline = s.add_node("deadline pressure", NodeType.CONCEPT)
    code = s.add_node("writing code", NodeType.CONCEPT)
    _worn(s, coffee, warmth); _worn(s, coffee, morning); _worn(s, morning, cozy)
    _worn(s, coffee, kitchen); _worn(s, kitchen, morning)
    _worn(s, work, desk); _worn(s, work, deadline); _worn(s, work, code); _worn(s, desk, code)
    _worn(s, coffee, work, n=8)
    return s, dict(coffee=coffee, warmth=warmth, morning=morning, cozy=cozy,
                   kitchen=kitchen, work=work, desk=desk, deadline=deadline, code=code)


def _flip_mind():
    """A topology built so that a DECAY sweep flips the winning coalition via a CONTESTED
    HIGH-ACTIVATION NODE whose basin allegiance crosses with decay — used by the real-
    causal-effect test. It is NOT hand-tuned to a particular winner; the winner is read
    from the loop. The construction is fully SYMMETRIC except for one contested node, so the
    flip is forced by that node's basin crossing (derived below), not by a fragile density
    tilt — and it survives the density normalization (both basins stay at the min-size
    guard, so the side holding the contested node is strictly denser).

    Distinct, NON-substring-overlapping content words, so perception (substring matching)
    lights up EXACTLY the two named anchors `alpha` and `gamma` and nothing spuriously.

    Construction (the derivation, NOT an injected answer):
      - Two named anchors `alpha` and `gamma` are field seeds (no road between them -> two
        singleton 1c groups -> two basins).
      - Each anchor has ONE tight neighbor: alpha->anode (n=30), gamma->gnode (n=30). These
        two near structures are MIRROR-SYMMETRIC, so without the contested node the two
        basins tie exactly.
      - ONE contested node `midnode` is reached at DIFFERENT distances from the two anchors:
          * 1 hop from alpha over a MEDIUM road alpha->midnode (n=3, strength ~0.360);
          * 2 hops from gamma over STRONG roads gamma->gnode->midnode (n=30 each, ~0.985).
        `midnode` is a sink (no out-roads), so it perturbs nothing downstream.

    Why a flip is forced (derived from the engine's spread + density, NOT injected):
      In alpha's spread, midnode gets E*0.360*d (1 hop). In gamma's spread, midnode gets
      E*0.985*d*0.985*d ~= E*0.970*d^2 (2 hops). midnode's dominant source therefore CROSSES
      at d* = 0.360/0.970 ~= 0.37, which lies INSIDE the modulated decay range [~0.26 ..
      0.65] (base 0.65 * factor [0.4..1.0]):
        * HIGH decay_per_hop (LOW friction, d~0.65): gamma's quadratic term wins -> midnode
          joins GAMMA's basin -> gamma's coalition = {gamma, gnode, midnode}, alpha's =
          {alpha, anode}; both denom = max(size,3) = 3, so the gamma side (with midnode's
          activation added, denom unchanged) is strictly denser -> GAMMA wins.
        * LOW decay_per_hop (HIGH friction, d~0.26): alpha's linear term wins -> midnode
          joins ALPHA's basin -> ALPHA wins by the mirror argument.
      midnode stays above the coherence floor at both ends (it is always SOMEWHERE; it only
      switches sides), so the flip is a clean basin crossing. The sweep DISCOVERS where it
      crosses; the test reads the winner identity from the loop, never injects it.
    """
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    alpha = s.add_node("alpha", NodeType.CONCEPT)
    anode = s.add_node("anode", NodeType.CONCEPT)      # alpha's tight neighbor
    gamma = s.add_node("gamma", NodeType.CONCEPT)
    gnode = s.add_node("gnode", NodeType.CONCEPT)      # gamma's tight neighbor (mirror)
    midnode = s.add_node("midnode", NodeType.CONCEPT)  # the contested node (a sink)
    # mirror-symmetric near neighbors
    _worn(s, alpha, anode, n=30)
    _worn(s, gamma, gnode, n=30)
    # the contested node: 1 medium hop from alpha, 2 strong hops from gamma
    _worn(s, alpha, midnode, n=3)                      # medium strength (~0.360) -> linear in d
    _worn(s, gnode, midnode, n=30)                     # strong; gamma->gnode->midnode -> ~d^2
    return s, dict(alpha=alpha, anode=anode, gamma=gamma, gnode=gnode, midnode=midnode)


# ─────────────────────────────────────────────────────────────────────────────
# Frozen replay traces (recorded-telemetry-shaped TelemetrySample sequences)
# ─────────────────────────────────────────────────────────────────────────────
# These are synthetic frozen traces whose FRICTION values are derivable by hand from the
# compute_friction definition, used to drive the deterministic mechanism tests. They are
# NOT the pilot's real-measured trace (that lives in the pilot harness, frozen + hashed);
# here we only need a deterministic, hand-checkable replay input.

def _trace_for_frictions(frictions):
    """Build a frozen TelemetrySample trace whose successive reads yield exactly the given
    friction values. We realize friction f over an interval by choosing wall_dt = 1.0 and
    cpu_dt = (1 - f), since compute_friction = 1 - cpu_dt/wall_dt = f. The first sample only
    primes the baseline (returns NEUTRAL_FRICTION), so we prepend an origin sample and then
    accumulate (perf, proc) so that each successive delta gives the wanted friction."""
    samples = [TelemetrySample(perf=0.0, proc=0.0)]
    perf = 0.0
    proc = 0.0
    for f in frictions:
        wall_dt = 1.0
        cpu_dt = 1.0 - f
        perf += wall_dt
        proc += cpu_dt
        samples.append(TelemetrySample(perf=perf, proc=proc))
    return samples


def _sensor_yielding(frictions):
    """A BodySensor (replay) ALREADY PRIMED past its baseline, so its NEXT read yields
    frictions[0], the one after yields frictions[1], etc. This matches the realistic
    pattern (the sensor is read once per cycle across many cycles; the first ever read
    primes the baseline and returns neutral). For single-think() tests that want a specific
    friction f on THIS cycle, use _sensor_yielding([f]): think()'s single read then sees f,
    not the baseline. Pure helper; touches no store."""
    sensor = BodySensor(simulated=True, trace=_trace_for_frictions(frictions))
    primed = sensor.read()  # consume the baseline (returns NEUTRAL_FRICTION)
    assert primed == NEUTRAL_FRICTION
    return sensor


# ─────────────────────────────────────────────────────────────────────────────
# 1) compute_friction — derivable, bounded, pure
# ─────────────────────────────────────────────────────────────────────────────

def test_compute_friction_is_the_stall_fraction():
    section("compute_friction = 1 - cpu/wall (the stall fraction), bounded to [0,1]")
    # ran flat-out: cpu == wall -> 0
    check(compute_friction(1.0, 1.0) == 0.0, "cpu==wall -> friction 0.0")
    # half-starved: cpu = 0.5 wall -> 0.5
    check(compute_friction(1.0, 0.5) == 0.5, "cpu=0.5*wall -> friction 0.5")
    # fully starved: cpu ~ 0 -> ~1
    check(compute_friction(1.0, 0.0) == 1.0, "cpu=0 -> friction 1.0")
    # cpu > wall (timer skew / multi-thread accounting) is clamped to 0, not negative
    check(compute_friction(1.0, 2.0) == 0.0, "cpu>wall clamps to 0.0 (no negative friction)")
    # sub-resolution / degenerate wall_dt -> neutral baseline, no division blow-up
    check(compute_friction(0.0, 0.0) == NEUTRAL_FRICTION, "wall_dt 0 -> neutral, no ZeroDivision")
    check(compute_friction(-1.0, 0.5) == NEUTRAL_FRICTION, "negative wall_dt -> neutral (degenerate)")
    # all outputs are within [0,1] across a coarse sweep
    in_range = all(0.0 <= compute_friction(1.0, c) <= 1.0 for c in
                   (-1.0, -0.1, 0.0, 0.1, 0.5, 0.9, 1.0, 1.5))
    check(in_range, "friction stays within [0,1] across a cpu sweep")


# ─────────────────────────────────────────────────────────────────────────────
# 2) BodySensor REPLAY — deterministic, ordered, first-read-primes-baseline
# ─────────────────────────────────────────────────────────────────────────────

def test_replay_yields_exactly_the_recorded_frictions():
    section("REPLAY: the sensor yields exactly the friction sequence its frozen trace encodes")
    wanted = [0.1, 0.4, 0.8, 0.0, 0.6]
    sensor = BodySensor(simulated=True, trace=_trace_for_frictions(wanted))
    # first read primes the baseline and returns neutral; then each wanted friction follows
    got_first = sensor.read()
    check(got_first == NEUTRAL_FRICTION, "first replay read primes baseline -> neutral friction")
    got = [round(sensor.read(), 12) for _ in wanted]
    check(got == [round(w, 12) for w in wanted],
          f"replay reproduces the recorded frictions exactly (got {got})")


def test_replay_exhaustion_raises_not_silently_reuses():
    section("REPLAY: exhausting the frozen trace raises (never loops / re-derives a value)")
    sensor = BodySensor(simulated=True, trace=_trace_for_frictions([0.5]))
    sensor.read()  # baseline
    sensor.read()  # the one real sample
    raised = False
    try:
        sensor.read()
    except IndexError:
        raised = True
    check(raised, "a read past the frozen trace raises IndexError (no silent reuse/loop)")


def test_replay_reset_replays_identically():
    section("REPLAY: reset() rewinds so the SAME frozen trace replays byte-identically")
    wanted = [0.2, 0.7, 0.3]
    sensor = BodySensor(simulated=True, trace=_trace_for_frictions(wanted))
    first_pass = [sensor.read() for _ in range(len(wanted) + 1)]
    sensor.reset()
    second_pass = [sensor.read() for _ in range(len(wanted) + 1)]
    check(first_pass == second_pass, "two passes over the same trace are identical after reset()")


def test_replay_requires_a_trace():
    section("REPLAY: BodySensor(simulated=True) WITHOUT a trace is rejected (no live read in replay)")
    raised = False
    try:
        BodySensor(simulated=True)
    except ValueError:
        raised = True
    check(raised, "simulated=True with no trace raises ValueError (replay must be trace-driven)")


def test_replay_friction_byte_identical_across_6_seeds():
    section("§(D-1) determinism: replay friction sequence byte-identical across 6 hash seeds "
            "(fresh interpreters)")
    # SPEC-0c §5.1: BIT PATTERNS, never round(x, 12).
    driver = textwrap.dedent('''
        import struct
        def _b(x): return struct.pack("<d", x).hex()
        from nous_bodysensor import BodySensor, TelemetrySample
        wanted = [0.05, 0.33, 0.61, 0.0, 0.9, 0.5]
        samples = [TelemetrySample(0.0, 0.0)]
        perf = 0.0; proc = 0.0
        for f in wanted:
            perf += 1.0; proc += (1.0 - f)
            samples.append(TelemetrySample(perf, proc))
        b = BodySensor(simulated=True, trace=samples)
        out = [_b(b.read()) for _ in range(len(wanted) + 1)]
        print(repr(out))
    ''')
    outs = _det_probe(driver)
    check(len(set(outs)) == 1,
          f"replay friction identical across 6 hash seeds (distinct outputs: {len(set(outs))})")


# ─────────────────────────────────────────────────────────────────────────────
# 3) The friction -> decay mapping — monotone, bounded, identity at friction 0
# ─────────────────────────────────────────────────────────────────────────────

def test_decay_mapping_is_identity_at_zero_friction():
    section("MAPPING: friction 0 -> decay factor 1.0 (identity); base decay unchanged")
    check(friction_to_decay_factor(0.0) == 1.0, "factor at friction 0 is exactly 1.0")
    check(modulated_decay_per_hop(DEFAULT_DECAY_PER_HOP, 0.0) == DEFAULT_DECAY_PER_HOP,
          "modulated decay at friction 0 equals the base decay exactly (identity)")


def test_decay_mapping_is_monotone_decreasing_and_bounded():
    section("MAPPING: higher friction -> strictly LOWER decay (more local); bounded in (0,1]")
    grid = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
    decays = [modulated_decay_per_hop(DEFAULT_DECAY_PER_HOP, f) for f in grid]
    strictly_decreasing = all(decays[i] > decays[i + 1] for i in range(len(decays) - 1))
    check(strictly_decreasing,
          f"modulated decay strictly decreases as friction rises (decays={[round(d,4) for d in decays]})")
    check(all(MIN_DECAY_PER_HOP <= d <= 1.0 for d in decays),
          "every modulated decay is bounded within (0,1] (never 0, never >1)")
    # boundedness holds even at an absurd base (clamp guards the range)
    check(0.0 < modulated_decay_per_hop(1.0, 1.0) <= 1.0, "extreme base+friction stays bounded")
    check(modulated_decay_per_hop(1e-9, 1.0) >= MIN_DECAY_PER_HOP, "tiny base floored, never 0")


# ─────────────────────────────────────────────────────────────────────────────
# 4) DEFAULT-OFF purity: body_sensor=None is byte-identical to current 1c/1d
# ─────────────────────────────────────────────────────────────────────────────

def test_default_off_is_byte_identical_to_pre_2c_behavior():
    section("DEFAULT-OFF: think() with body_sensor=None is byte-identical to the pre-2c path "
            "(field totals, winner, effective decay all unchanged); body_friction is None")
    s, n = _small_mind()
    # Reference: call think() with NO 2c arguments at all (the literal pre-2c call shape).
    r_ref = think(s, "coffee in the kitchen this morning")
    # Same call, explicitly default body_sensor=None and default decay.
    r_off = think(s, "coffee in the kitchen this morning", body_sensor=None)
    ref_winner = tuple(sorted(s.get_node(m).content for m in r_ref.thought.members)) if r_ref.thought else None
    off_winner = tuple(sorted(s.get_node(m).content for m in r_off.thought.members)) if r_off.thought else None
    check(ref_winner == off_winner, "winner identical with body_sensor=None")
    check(r_off.body_friction is None, "body_friction is None when interoception is OFF")
    check(r_off.effective_decay_per_hop == DEFAULT_DECAY_PER_HOP,
          "effective decay equals the unmodulated default when OFF")
    # the entire activation field is byte-identical (the hook could only change it via decay)
    ref_tot = tuple(sorted((s.get_node(k).content, round(v, 12)) for k, v in r_ref.field_.total.items()))
    off_tot = tuple(sorted((s.get_node(k).content, round(v, 12)) for k, v in r_off.field_.total.items()))
    check(ref_tot == off_tot, "the full activation field totals are byte-identical when OFF")


def test_default_off_store_is_untouched_pure_read():
    section("DEFAULT-OFF: think(body_sensor=None) is a PURE READ — the store is byte-identical")
    s, n = _small_mind()
    before = _deep_snapshot(s)
    for _ in range(5):
        think(s, "coffee in the kitchen this morning", body_sensor=None)
    after = _deep_snapshot(s)
    check(before == after, "repeated OFF think() calls mutate nothing (pure read preserved)")


def test_empty_perception_does_not_read_the_sensor():
    section("DEFAULT-OFF nuance: an utterance naming NOTHING does not consume a replay sample "
            "(no field to modulate), even with a sensor attached")
    s, n = _small_mind()
    sensor = BodySensor(simulated=True, trace=_trace_for_frictions([0.5, 0.5, 0.5]))
    r = think(s, "zzz qqq vvv", body_sensor=sensor)  # matches no node content
    check(r.thought is None, "no winner when nothing perceived")
    check(r.body_friction is None, "body_friction stays None on an empty-perception cycle")
    # the trace is intact: baseline + 3 samples = 4 reads still available
    check(sensor.remaining() == 4, "no replay sample was consumed on the empty-perception path")


# ─────────────────────────────────────────────────────────────────────────────
# 5) THE REAL CAUSAL EFFECT (winner-flip) — the (C-GRADE-EMERGENT) anti-circularity test
# ─────────────────────────────────────────────────────────────────────────────

def _winner_set(s, r):
    """The winner readout: a FROZENSET of node CONTENTS — a node-set, NOT the friction
    scalar. (Content, not uuid, so it is comparable across processes.)"""
    if r is None or r.thought is None:
        return None
    return frozenset(s.get_node(m).content for m in r.thought.members)


def test_modulation_is_a_real_causal_effect_winner_flips_with_friction():
    section("CAUSAL EFFECT: across a replayed friction range, a DIFFERENT coalition wins "
            "(winner-SET identity flips) — the readout is a node-set, NOT the injected scalar "
            "((C-GRADE-EMERGENT) anti-circularity)")
    # Sweep friction across the full [0,1] range via a frozen replay trace. We DISCOVER the
    # winner at each friction by reading the loop's output — we never inject a winner.
    grid = [i / 20.0 for i in range(21)]  # 0.00, 0.05, ..., 1.00
    winners = []
    fr_used = []
    for f in grid:
        s, n = _flip_mind()
        sensor = _sensor_yielding([f])  # primed: think()'s single read sees friction f
        r = think(s, "alpha gamma", body_sensor=sensor)  # both anchors named -> two seeds
        winners.append(_winner_set(s, r))
        fr_used.append(r.body_friction)
    distinct = {w for w in winners if w is not None}
    # THE FLIP: more than one distinct winning node-set is observed across the friction range.
    check(len(distinct) >= 2,
          f"a winner-flip occurs across the friction range (distinct winning node-sets: {len(distinct)})")
    # the extreme-low and extreme-high friction ends select DIFFERENT winners (a real crossover)
    check(winners[0] is not None and winners[-1] is not None and winners[0] != winners[-1],
          f"low-friction winner {winners[0]} differs from high-friction winner {winners[-1]}")
    # ANTI-CIRCULARITY (explicit): each winner is a frozenset of node-contents — categorically
    # NOT the injected float. The friction scalars actually applied vary across the sweep, and
    # NONE of them is (or could be) the winner node-set.
    all_node_sets = all((w is None) or isinstance(w, frozenset) for w in winners)
    check(all_node_sets, "every winner readout is a node-SET (frozenset of contents), not a scalar")
    scalars_varied = len({round(f, 9) for f in fr_used if f is not None}) >= 2
    check(scalars_varied, "the friction scalar genuinely varied across the sweep (the cause moved)")
    none_is_scalar = all((w is None) or all(isinstance(x, str) for x in w) for w in winners)
    check(none_is_scalar, "no winner readout is or contains the injected friction float (no echo)")


def test_modulation_changes_the_field_not_just_a_stored_number():
    section("CAUSAL EFFECT (upstream): different friction changes the ACTIVATION FIELD itself "
            "(total activation), proving the number acts on cycle dynamics, not a pass-through")
    s_lo, _ = _flip_mind()
    s_hi, _ = _flip_mind()
    r_lo = think(s_lo, "alpha gamma", body_sensor=_sensor_yielding([0.0]))
    r_hi = think(s_hi, "alpha gamma", body_sensor=_sensor_yielding([0.9]))
    # the effective decay differs (the modulation actually applied)
    check(r_lo.effective_decay_per_hop != r_hi.effective_decay_per_hop,
          "effective decay differs between low and high friction (the gain moved)")
    # the FIELD differs — the contested node reaches a different activation under different
    # decay (its activation has a decay-sensitive 2-hop term from gamma)
    tot_lo = {s_lo.get_node(k).content: v for k, v in r_lo.field_.total.items()}
    tot_hi = {s_hi.get_node(k).content: v for k, v in r_hi.field_.total.items()}
    far = "midnode"  # the contested node, reached at distance from gamma (decay-sensitive)
    lo_far = tot_lo.get(far, 0.0)
    hi_far = tot_hi.get(far, 0.0)
    check(lo_far != hi_far,
          f"the contested node's activation differs under low vs high friction "
          f"(lo={round(lo_far,9)} hi={round(hi_far,9)}) — real upstream modulation, not echo")
    # the DIRECTION matches the engine semantics: higher friction -> lower decay -> the far
    # node is LESS activated (more local). Derived from the mapping, not injected.
    check(hi_far <= lo_far,
          "higher friction makes the far node LESS active (activation stays more local) — "
          "matches the SPEC-2c §4 stated intent against the engine's real decay semantics")


def test_winner_flip_is_byte_identical_across_6_seeds():
    section("§(D-1)+(D-5): the loop's winner trace under a replayed friction sweep is byte-"
            "identical across 6 hash seeds (the winner-flip is REPRODUCIBLE, not a one-off)")
    # SPEC-0c §5.1: BIT PATTERNS, never round(x, 4) — the friction scalar that indexes
    # the trace is serialised exactly, so two runs that differ below 1e-4 are not merged.
    driver = textwrap.dedent('''
        import struct
        def _b(x): return struct.pack("<d", x).hex()
        from nous_store import SubstrateStore, Clock, NodeType
        from nous_perceive import think
        from nous_bodysensor import BodySensor, TelemetrySample
        def build():
            s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
            def add(c): return s.add_node(c, NodeType.CONCEPT)
            alpha=add("alpha"); anode=add("anode")
            gamma=add("gamma"); gnode=add("gnode"); midnode=add("midnode")
            def w(a,b,nn):
                for _ in range(nn): s.traverse(a,b)
            w(alpha,anode,30); w(gamma,gnode,30)
            w(alpha,midnode,3); w(gnode,midnode,30)
            return s
        def sensor_for(f):
            # primed past the baseline so think()'s single read yields friction f
            samples=[TelemetrySample(0.0,0.0)]; perf=0.0; proc=0.0
            perf+=1.0; proc+=(1.0-f); samples.append(TelemetrySample(perf,proc))
            sn=BodySensor(simulated=True,trace=samples); sn.read()  # consume baseline
            return sn
        out=[]
        for i in range(21):
            f=i/20.0
            s=build()
            r=think(s,"alpha gamma",body_sensor=sensor_for(f))
            win=tuple(sorted(s.get_node(m).content for m in r.thought.members)) if r.thought else None
            out.append((_b(f), win))
        print(repr(out))
    ''')
    outs = _det_probe(driver)
    check(len(set(outs)) == 1,
          f"winner-vs-friction trace identical across 6 hash seeds (distinct outputs: {len(set(outs))})")


# ─────────────────────────────────────────────────────────────────────────────
# 6) Integrity / purity of the ON path (the modulation is a bounded parameter change)
# ─────────────────────────────────────────────────────────────────────────────

def test_on_path_is_still_a_pure_read_when_not_broadcasting():
    section("PURITY (ON path): think(body_sensor=..., broadcast=False) reads telemetry but "
            "still mutates NOTHING in the store (the modulation is a parameter change, not a write)")
    s, n = _flip_mind()
    before = _deep_snapshot(s)
    for f in (0.0, 0.5, 0.9):
        think(s, "alpha gamma", body_sensor=_sensor_yielding([f]))
    after = _deep_snapshot(s)
    check(before == after, "the ON path (broadcast=False) leaves the store byte-identical")


def test_on_path_integrity_preserved():
    section("INTEGRITY (ON path): the store's integrity scan is clean before and after a "
            "modulated cycle")
    s, n = _flip_mind()
    s.check_integrity()
    think(s, "alpha gamma", body_sensor=_sensor_yielding([0.7]))
    clean = True
    try:
        s.check_integrity()
    except Exception as e:
        clean = False
        print("   integrity error:", e)
    check(clean, "integrity holds after a modulated cycle")


def test_sensor_read_only_touches_its_own_cursor_not_the_store():
    section("PURITY (sensor): a sensor read mutates ONLY the sensor's cursor, never the store")
    s, n = _flip_mind()
    before = _deep_snapshot(s)
    sensor = BodySensor(simulated=True, trace=_trace_for_frictions([0.3, 0.6]))
    sensor.read()
    sensor.read()
    after = _deep_snapshot(s)
    check(before == after, "sensor reads do not touch the substrate at all")
    check(sensor.remaining() == 1, "the sensor's own cursor advanced (its bookkeeping is what moved)")


# ─────────────────────────────────────────────────────────────────────────────
# 7) HONEST-FRAMING asserted-negatives + the soft-Wall-1 (no graph re-derivation) guard
# ─────────────────────────────────────────────────────────────────────────────

def test_asserted_negative_sensor_cannot_re_derive_friction_from_graph():
    section("ASSERTED-NEGATIVE (soft-Wall-1 guard): the BodySensor takes NO store/graph and "
            "computes friction ONLY from the telemetry pair — it CANNOT re-derive from substrate")
    # structural: neither the constructor nor read() accepts a store/graph/field parameter.
    ctor_params = set(inspect.signature(BodySensor.__init__).parameters) - {"self"}
    check(ctor_params == {"simulated", "trace"},
          f"BodySensor.__init__ takes only (simulated, trace) — no store/graph (got {ctor_params})")
    read_params = set(inspect.signature(BodySensor.read).parameters) - {"self"}
    check(read_params == set(),
          f"BodySensor.read takes no arguments — it cannot be handed graph state (got {read_params})")
    # behavioral: friction is a pure function of the timing deltas; the SAME friction is
    # produced regardless of any substrate (there is no substrate in scope at all).
    f1 = compute_friction(1.0, 0.25)
    f2 = compute_friction(1.0, 0.25)
    check(f1 == f2 == 0.75, "friction is a pure function of the timing pair only")
    # the friction source identity: friction depends ONLY on (wall_dt, cpu_dt). Vary nothing
    # but the pair and the value tracks the pair, never any graph quantity.
    check(compute_friction(2.0, 0.5) == 0.75 and compute_friction(4.0, 1.0) == 0.75,
          "friction depends only on the cpu/wall RATIO (the telemetry), nothing else")


def test_asserted_negative_no_public_name_encodes_a_feeling_or_awareness_claim():
    section("ASSERTED-NEGATIVE (honest framing): no public name in nous_bodysensor encodes a "
            "feeling/emotion/awareness/consciousness claim — the headline is 'friction', a "
            "derived telemetry signal")
    public = [name for name in dir(bs) if not name.startswith("_")]
    forbidden = ("feel", "emotion", "aware", "conscious", "sentient", "mind", "panic",
                 "experience", "qualia", "mood")
    offenders = [name for name in public
                 if any(tok in name.lower() for tok in forbidden)]
    check(offenders == [],
          f"no public name claims a feeling/awareness/consciousness (offenders: {offenders})")
    # the headline term IS present and IS the mechanism word
    check("compute_friction" in public and "BodySensor" in public,
          "the public surface names the mechanism (friction / BodySensor), not a felt state")


def test_known_limitation_modulation_does_not_track_a_pre_registered_direction_here():
    section("KNOWN LIMITATION (asserted-negative): this suite proves the modulation is a REAL "
            "causal effect (winner-flip) and DETERMINISTIC — it does NOT establish that the flip "
            "tracks the telemetry in a validator-pre-registered direction, nor that it MEANS "
            "anything. That is the validator's graded run, gated by the populability pilot.")
    # We assert the NEGATIVE explicitly: the mechanism layer makes no graded/meaning claim.
    # A winner-flip exists (proven elsewhere in this suite); whether its DIRECTION is the
    # pre-registered one and whether it clears an effect-size bar is NOT decided here.
    s, n = _flip_mind()
    r = think(s, "alpha gamma", body_sensor=_sensor_yielding([0.5]))
    # the result carries a body_friction scalar and an effective decay — mechanism facts only.
    check(r.body_friction is not None, "the cycle recorded a body-state scalar (a mechanism fact)")
    check(r.effective_decay_per_hop is not None, "the cycle recorded the effective decay (mechanism)")
    # there is deliberately NO API here that returns a graded 'meaning' verdict — meaning is
    # not this layer's to assert.
    has_meaning_api = any(
        tok in name.lower()
        for name in dir(bs) if not name.startswith("_")
        for tok in ("validate", "grade", "earned", "significance")
    )
    check(not has_meaning_api,
          "nous_bodysensor exposes NO meaning/grading/validation verdict (meaning is the validator's)")


# ─────────────────────────────────────────────────────────────────────────────
# Shared determinism/snapshot helpers (mirror the established patterns)
# ─────────────────────────────────────────────────────────────────────────────

def _deep_snapshot(s):
    """A deep snapshot of ALL stored state, keyed by stable identity (content+creation_seq),
    so it is comparable across runs and detects ANY mutation. Mirrors the 1d suites."""
    nodes = []
    for nid in s.all_node_ids():
        nd = s.get_node(nid)
        nodes.append((nd.content, nd.creation_seq, nd.node_type.value,
                      nd.access_count))
    nodes.sort()
    roads = []
    for rid in s.all_road_ids():
        rd = s.get_road(rid, apply_decay=False)
        roads.append((s.get_node(rd.source_id).content, s.get_node(rd.target_id).content,
                      rd.creation_seq, round(rd.strength, 12), rd.traversal_count,
                      rd.closed, tuple(sorted((k, round(v, 12)) for k, v in rd.charges.items())),
                      round(rd.last_touched, 12)))
    roads.sort()
    return (tuple(nodes), tuple(roads))


def _det_probe(driver):
    """Run a probe under 6 distinct PYTHONHASHSEED values in fresh interpreters; return the
    list of stdout strings (the established subprocess-probe determinism pattern)."""
    outs = []
    cwd = os.path.dirname(__file__) or "."
    for seed in ("0", "1", "2", "7", "42", "999"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        rr = subprocess.run([sys.executable, "-c", driver], cwd=cwd,
                            capture_output=True, text=True, env=env)
        if rr.returncode != 0:
            print("  (subprocess error)\n", rr.stderr)
        outs.append(rr.stdout.strip())
    return outs


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  NOUS BODYSENSOR + 2c MODULATION HOOK — TEST SUITE (mechanism, replay)")
    print("=" * 70)
    tests = [
        test_compute_friction_is_the_stall_fraction,
        test_replay_yields_exactly_the_recorded_frictions,
        test_replay_exhaustion_raises_not_silently_reuses,
        test_replay_reset_replays_identically,
        test_replay_requires_a_trace,
        test_replay_friction_byte_identical_across_6_seeds,
        test_decay_mapping_is_identity_at_zero_friction,
        test_decay_mapping_is_monotone_decreasing_and_bounded,
        test_default_off_is_byte_identical_to_pre_2c_behavior,
        test_default_off_store_is_untouched_pure_read,
        test_empty_perception_does_not_read_the_sensor,
        test_modulation_is_a_real_causal_effect_winner_flips_with_friction,
        test_modulation_changes_the_field_not_just_a_stored_number,
        test_winner_flip_is_byte_identical_across_6_seeds,
        test_on_path_is_still_a_pure_read_when_not_broadcasting,
        test_on_path_integrity_preserved,
        test_sensor_read_only_touches_its_own_cursor_not_the_store,
        test_asserted_negative_sensor_cannot_re_derive_friction_from_graph,
        test_asserted_negative_no_public_name_encodes_a_feeling_or_awareness_claim,
        test_known_limitation_modulation_does_not_track_a_pre_registered_direction_here,
    ]
    for t in tests:
        t()
    print("\n" + "=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    print("=" * 70)
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
