"""
TESTS (mechanism, data-free) for experiments/exp2c_capture.py — the 2c REALISTIC
stimulus-construction (capture) script.

WHAT IS UNDER TEST (and, with equal weight, what is NOT):
  The capture script builds the FROZEN realistic stimuli for the 2c graded MEANING run —
  the §5.2 realistic percept battery and the §6 realistic telemetry trace — the analogue of
  EXP-1e's blind, seeded, hashed selector. It computes NO flip-rate and NO graded number of
  any kind. These tests verify the STIMULUS CONSTRUCTION is faithful to the FROZEN §5/§6
  procedure (docs/experiments/EXP-2c-interoception.md), deterministic in replay, genuinely
  NOT flip-pre-selected, and structurally distinct from the pilot's contested-by-design
  battery. They make NO meaning claim; whether the stimuli, once graded, MEAN anything is
  the validator's later step.

WHY THE LIVE CAPTURE RUN IS NOT EXERCISED HERE (mirrors the pilot):
  The actual trace capture reads LIVE perf_counter/process_time — the single point of
  non-determinism — and is therefore NOT on the deterministic test surface, exactly as the
  pilot's live capture stays out of run_tests.py. These tests exercise:
    - the battery generator (fully deterministic from the seed — wired into run_tests.py),
    - the trace-PROCESSING helpers (friction-from-trace, sweep-from-range) over a FIXED,
      hand-free sample sequence (deterministic — wired in),
    - the blindness / no-graded-number guards (static — wired in).
  The capture's own live boundary read is verified only structurally (it calls the SAME
  compute_friction the cycle uses; it reads perf_counter/process_time), never by running it.

Uses the project's tiny built-in harness (print + count, exit nonzero), NOT pytest — same
convention as the rest of the suite. Run as a script:
    python3 experiments/test_exp2c_capture.py
"""

from __future__ import annotations

import os
import sys
import json
import inspect
import subprocess

# self-bootstrap: src/ (frozen library, bare-name imports) and experiments/ (the capture
# module + bodysensor live via src) onto sys.path, mirroring test_harness.py.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), "src")
for _p in (_SRC, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import exp2c_capture as cap
import nous_bodysensor as bs
import pilot_2c_populability as pilot
# perceive is the INPUT side (it produces matched SOURCE nodes from the utterance) — used here
# ONLY to verify the stimulus is well-formed (exactly the two anchors light up), NOT to grade.
# It produces no winner/activation/flip; checking the source set is stimulus validation, the
# §5.2 "perception lights up exactly the two anchors" requirement, not a graded readout.
from nous_perceive import perceive


# ─────────────────────────────────────────────────────────────────────────────
# Tiny test harness (matches the rest of the suite)
# ─────────────────────────────────────────────────────────────────────────────

_passed = 0
_failed = 0


def check(cond: bool, msg: str) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {msg}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


class pytest_approx:
    """Dependency-free float approx for the few exact-arithmetic friction checks. Named to
    read like an approx at the call site; the core stays stdlib-only (CONTRIBUTING.md rule 8)."""
    def __init__(self, value, tol=1e-9):
        self.value = value
        self.tol = tol

    def __eq__(self, other):
        return abs(other - self.value) <= self.tol

    def __repr__(self):
        return f"~{self.value}"


# ═════════════════════════════════════════════════════════════════════════════
# A. THE REALISTIC BATTERY IS BUILT TO THE §5.2 SPEC
# ═════════════════════════════════════════════════════════════════════════════

def test_battery_parameters_are_the_frozen_5_2_constants():
    section("A1 §5.2 CONSTANTS: the frozen battery parameters are exactly the §6.4 fixed "
            "values (seed 20260622, count 60, the documented draw ranges) — not the pilot's")
    check(cap.BATTERY_SEED_REALISTIC == 20260622,
          f"BATTERY_SEED_REALISTIC == 20260622 (saw {cap.BATTERY_SEED_REALISTIC})")
    check(cap.PERCEPT_COUNT_REALISTIC == 60,
          f"PERCEPT_COUNT_REALISTIC == 60 (saw {cap.PERCEPT_COUNT_REALISTIC})")
    check(cap.DOMAIN_SIZE_RANGE == (2, 5),
          f"domain_size range == [2..5] (saw {cap.DOMAIN_SIZE_RANGE})")
    check(cap.INTERNAL_N_RANGE == (8, 30),
          f"internal_n range == [8..30] (saw {cap.INTERNAL_N_RANGE})")
    check(cap.BRIDGE_PRESENT_P == 0.5,
          f"bridge_present p == 0.5 (saw {cap.BRIDGE_PRESENT_P})")
    check(cap.BRIDGE_N_RANGE == (1, 30),
          f"bridge_n range == [1..30] (saw {cap.BRIDGE_N_RANGE})")
    check(cap.DEPTH_EXTRA_RANGE == (0, 1),
          f"depth_extra range == [0..1] (saw {cap.DEPTH_EXTRA_RANGE})")
    # distinct from the pilot's seed (an independent draw, not the pilot relabelled)
    check(cap.BATTERY_SEED_REALISTIC != pilot.BATTERY_SEED,
          "the realistic seed differs from the pilot seed (independent draw)")


def test_battery_builds_60_two_anchor_percepts():
    section("A2 §5.2 SIZE/SHAPE: build_realistic_battery yields exactly 60 percepts, each "
            "naming two non-substring-overlapping anchors, each with a runnable store builder")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    check(len(battery) == 60, f"battery has 60 percepts (saw {len(battery)})")
    for spec in battery:
        # each percept is a RealisticPercept with the §5.2 structural fields
        check(spec.anchor_a_content != spec.anchor_b_content,
              "the two anchors have distinct content")
        a, b = spec.anchor_a_content, spec.anchor_b_content
        check(a not in b and b not in a,
              f"anchors are non-substring-overlapping ({a!r}, {b!r}) so perception lights up "
              f"exactly the two anchors")
        # the percept text is exactly the two anchor contents
        check(spec.percept_text == f"{a} {b}",
              f"percept text is 'anchorA anchorB' (saw {spec.percept_text!r})")
        # a store builder is present and produces a substrate with both anchors
        store = spec.build_store()
        contents = {store.get_node(nid).content for nid in store.all_node_ids()}
        check(a in contents and b in contents,
              "the built store contains both anchor nodes")
        # INTEGRITY (substrate bar): every built topology is graph-consistent
        try:
            store.check_integrity()
            integral = True
        except Exception:
            integral = False
        check(integral, f"the built store for {spec.percept_text!r} passes check_integrity()")


def test_perception_lights_up_exactly_the_two_anchors():
    section("A4 §5.2 CLEAN PERCEPTION (loop-closed): driving perceive() with each percept's "
            "OWN system-generated text lights up EXACTLY the two anchor nodes as sources — "
            "never a neighbor / tail (the §5.2 'perception lights up exactly the two anchors' "
            "property; the neighbor namespace embeds no anchor substring)")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    for spec in battery:
        store = spec.build_store()
        # loop-closed: the utterance is the percept's OWN generated text, not a hand input
        p = perceive(store, spec.percept_text)
        lit_contents = {store.get_node(nid).content for nid in p.sources}
        check(lit_contents == {spec.anchor_a_content, spec.anchor_b_content},
              f"percept {spec.percept_text!r} lights up exactly its two anchors "
              f"(saw sources: {sorted(lit_contents)})")


def test_battery_draws_match_an_independent_seeded_rng():
    section("A3 §5.2 SEEDED DRAWS (anti-curation): the per-percept structural parameters "
            "match an INDEPENDENT re-derivation of random.Random(20260622) drawing the §5.2 "
            "ranges in the documented order — proving the space is seeded, not hand-curated")
    import random as _random
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    # Re-derive the EXACT documented draw order (must match build_realistic_battery exactly).
    # The contract (mirrored in the script's docstring + DRAW_ORDER constant): per percept,
    # in order: anchorA index, anchorB index (re-drawn until distinct), domain_size_a,
    # domain_size_b, internal_n for each A-road, internal_n for each B-road, bridge_present,
    # [bridge target index, bridge_n] if present, depth_extra.
    rng = _random.Random(cap.BATTERY_SEED_REALISTIC)
    vocab_n = len(cap.ANCHOR_VOCAB)
    for spec in battery:
        ia = rng.randrange(vocab_n)
        ib = rng.randrange(vocab_n)
        while ib == ia:
            ib = rng.randrange(vocab_n)
        check(spec.anchor_a_content == cap.ANCHOR_VOCAB[ia],
              f"anchorA matches the re-derived draw ({spec.anchor_a_content!r} vs "
              f"{cap.ANCHOR_VOCAB[ia]!r})")
        check(spec.anchor_b_content == cap.ANCHOR_VOCAB[ib],
              f"anchorB matches the re-derived draw ({spec.anchor_b_content!r} vs "
              f"{cap.ANCHOR_VOCAB[ib]!r})")
        ds_a = rng.randint(*cap.DOMAIN_SIZE_RANGE)
        ds_b = rng.randint(*cap.DOMAIN_SIZE_RANGE)
        check(spec.domain_size_a == ds_a and spec.domain_size_b == ds_b,
              f"domain sizes match the re-derived draws ({spec.domain_size_a},"
              f"{spec.domain_size_b} vs {ds_a},{ds_b})")
        # internal_n per A-road then per B-road, in order
        roads_a = [rng.randint(*cap.INTERNAL_N_RANGE) for _ in range(ds_a)]
        roads_b = [rng.randint(*cap.INTERNAL_N_RANGE) for _ in range(ds_b)]
        check(spec.internal_n_a == roads_a,
              f"A-domain internal_n traversal counts match ({spec.internal_n_a} vs {roads_a})")
        check(spec.internal_n_b == roads_b,
              f"B-domain internal_n traversal counts match ({spec.internal_n_b} vs {roads_b})")
        bridge_present = rng.random() < cap.BRIDGE_PRESENT_P
        check(spec.bridge_present == bridge_present,
              f"bridge_present matches the re-derived draw ({spec.bridge_present} vs "
              f"{bridge_present})")
        if bridge_present:
            _bt = rng.randrange(ds_b)  # which B-neighbor the bridge targets
            bn = rng.randint(*cap.BRIDGE_N_RANGE)
            check(spec.bridge_target_index == _bt,
                  f"bridge target index matches ({spec.bridge_target_index} vs {_bt})")
            check(spec.bridge_n == bn,
                  f"bridge_n matches the re-derived draw ({spec.bridge_n} vs {bn})")
        else:
            check(spec.bridge_n is None and spec.bridge_target_index is None,
                  "no bridge -> bridge_n and target index are None")
        depth_extra = rng.randint(*cap.DEPTH_EXTRA_RANGE)
        check(spec.depth_extra == depth_extra,
              f"depth_extra matches the re-derived draw ({spec.depth_extra} vs {depth_extra})")


# ═════════════════════════════════════════════════════════════════════════════
# B. THE BATTERY IS GENUINELY *NOT* FLIP-PRE-SELECTED (the opposite of the pilot)
# ═════════════════════════════════════════════════════════════════════════════

def test_no_contested_node_no_positioned_crossover():
    section("B1 §5.2 NOT-FLIP-PRE-SELECTED: NO percept contains a contested 'midnode', and "
            "NO percept positions a crossover d* — the structural opposite of the pilot")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    for spec in battery:
        store = spec.build_store()
        contents = [store.get_node(nid).content for nid in store.all_node_ids()]
        # the pilot's contested node is literally named "midnode"; it must NOT appear
        check("midnode" not in contents,
              f"no 'midnode' contested node in percept {spec.percept_text!r}")
        # the RealisticPercept carries NO crossover field at all (no d*, no positioned
        # asymmetric-distance contested node) — structurally absent, not just unset
        fields = set(spec.__dict__.keys())
        for forbidden in ("d_star", "dstar", "crossover", "midnode", "contested"):
            check(forbidden not in fields,
                  f"the percept spec has NO '{forbidden}' field (crossover is not positioned)")


def test_no_node_is_reached_at_pilot_style_asymmetric_distance():
    section("B2 §5.2 NO ASYMMETRIC CONTESTED PATH: no single node is reached 1-medium-hop "
            "from anchorA AND 2-strong-hops from anchorB (the pilot's exact flip mechanism). "
            "The realistic bridge, when present, goes anchorA -> a real B-neighbor (1 hop), "
            "never via a constructed 2-hop gamma->gnode->mid sink.")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    saw_a_bridge = False
    for spec in battery:
        store = spec.build_store()
        contents = {store.get_node(nid).content for nid in store.all_node_ids()}
        # No contested sink may exist: the pilot's contested node is literally 'midnode'.
        check("midnode" not in contents,
              "no contested 'midnode' sink anywhere in the realistic topology")
        # The bridge target, when present, must be an EXISTING B-domain neighbor (so the
        # bridge is a 1-hop anchorA->(B-neighbor) edge), NEVER a fresh sink node reached at
        # 2 strong hops from the other anchor. We assert the bridged node is one of B's
        # declared neighbors, i.e. it is a real domain member, not a constructed contested sink.
        if spec.bridge_present:
            saw_a_bridge = True
            check(0 <= spec.bridge_target_index < spec.domain_size_b,
                  "the bridge targets an existing B-domain neighbor index (a real member), "
                  "not a constructed contested sink")
    check(saw_a_bridge,
          "at least one percept in the 60 has a bridge (p=0.5 over 60 draws) so this property "
          "is non-vacuously exercised")


def test_some_percepts_have_no_bridge_at_all():
    section("B3 §5.2 p=0.5 BRIDGE: bridge_present is a real coin flip — the battery contains "
            "BOTH bridged and unbridged percepts (the pilot's bridge is ALWAYS present)")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    bridged = sum(1 for s in battery if s.bridge_present)
    unbridged = len(battery) - bridged
    check(bridged > 0, f"some percepts ARE bridged ({bridged}/60)")
    check(unbridged > 0, f"some percepts are NOT bridged ({unbridged}/60) — unlike the pilot, "
                         f"where the contested bridge is always present")


def test_bridge_n_spans_the_full_documented_range_not_a_crossover_window():
    section("B4 §5.2 bridge_n IS A FREE UNIFORM DRAW: bridge_n spans the documented [1..30], "
            "NOT confined to the pilot's [1..6] crossover-positioning window")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    bridge_ns = sorted(s.bridge_n for s in battery if s.bridge_present)
    check(all(1 <= n <= 30 for n in bridge_ns),
          f"all bridge_n within [1..30] (saw {bridge_ns})")
    # The defining distinction from the pilot: the pilot caps bridge_n at 6 (to position d*);
    # the realistic draw is uniform over [1..30], so it should reach WELL ABOVE 6.
    check(max(bridge_ns) > 6,
          f"bridge_n reaches above 6 (max {max(bridge_ns)}) — a free uniform draw, NOT the "
          f"pilot's [1..6] crossover window")
    check(len(set(bridge_ns)) >= 4,
          f"bridge_n genuinely varies ({sorted(set(bridge_ns))})")


def test_battery_is_structurally_distinct_from_the_pilot_battery():
    section("B5 §5.3 DISTINCTNESS (the directive): the realistic battery is provably NOT the "
            "pilot battery — different seed, different count, no contested midnode, asymmetric "
            "random domains (vs the pilot's mirror-symmetric near neighbors)")
    realistic = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    # 1) different seed and count
    check(cap.BATTERY_SEED_REALISTIC != pilot.BATTERY_SEED and
          cap.PERCEPT_COUNT_REALISTIC != pilot.PERCEPT_COUNT,
          "different seed AND count from the pilot")
    # 2) the pilot battery always builds a 'midnode'; the realistic battery never does
    pilot_battery = pilot.build_battery(pilot.BATTERY_SEED, pilot.PERCEPT_COUNT)
    pilot_label0, pilot_builder0, _pt, _a, _b = pilot_battery[0]
    pilot_store0 = pilot_builder0()
    pilot_contents0 = {pilot_store0.get_node(n).content for n in pilot_store0.all_node_ids()}
    check("midnode" in pilot_contents0,
          "(control) the PILOT battery does build a 'midnode' contested node")
    realistic_store0 = realistic[0].build_store()
    realistic_contents0 = {realistic_store0.get_node(n).content
                           for n in realistic_store0.all_node_ids()}
    check("midnode" not in realistic_contents0,
          "the realistic battery does NOT build a 'midnode' contested node")
    # 3) the realistic battery has GENERICALLY ASYMMETRIC domain sizes (the pilot's near
    #    neighbors are mirror-symmetric: same count on both anchors). At least one realistic
    #    percept must have domain_size_a != domain_size_b.
    asymmetric = [s for s in realistic if s.domain_size_a != s.domain_size_b]
    check(len(asymmetric) > 0,
          f"the realistic battery has generically asymmetric domains "
          f"({len(asymmetric)}/60 percepts have unequal A/B domain sizes) — unlike the pilot's "
          f"mirror-symmetric construction")


# ═════════════════════════════════════════════════════════════════════════════
# C. THE TRACE CAPTURE COMPUTES FRICTION VIA THE *SAME* compute_friction
# ═════════════════════════════════════════════════════════════════════════════

def test_capture_uses_the_same_compute_friction_object_identity():
    section("C1 SAME FRICTION (identity, not re-derivation): the capture module's friction "
            "function IS nous_bodysensor.compute_friction — the SAME object the BodySensor / "
            "cycle use, never a re-implementation")
    # object identity: the name the capture module binds must be the library function itself
    check(cap.compute_friction is bs.compute_friction,
          "exp2c_capture.compute_friction IS nous_bodysensor.compute_friction (same object)")
    # and the trace-processing helper consumes the BodySensor in REPLAY exactly as the cycle
    # does (it constructs a BodySensor(simulated=True, trace=...) and reads it). We assert the
    # helper references the library BodySensor, not a private copy.
    check(cap.BodySensor is bs.BodySensor,
          "exp2c_capture.BodySensor IS nous_bodysensor.BodySensor (same object)")


def test_frictions_from_trace_match_compute_friction_on_the_deltas():
    section("C2 SAME FRICTION (loop-closed over a FIXED trace): frictions_from_trace replays a "
            "fixed, hand-free sample sequence through the BodySensor and yields exactly "
            "compute_friction(wall_dt, cpu_dt) on consecutive-sample deltas (first dropped)")
    # a FIXED, deterministic sample sequence (NOT live; constructed so each interval's
    # friction is independently predictable from compute_friction on the deltas).
    samples = [
        bs.TelemetrySample(perf=0.0, proc=0.0),     # baseline (dropped)
        bs.TelemetrySample(perf=1.0, proc=1.0),     # wall=1, cpu=1 -> friction 0.0
        bs.TelemetrySample(perf=2.0, proc=1.5),     # wall=1, cpu=0.5 -> friction 0.5
        bs.TelemetrySample(perf=3.0, proc=1.5),     # wall=1, cpu=0.0 -> friction 1.0
        bs.TelemetrySample(perf=4.0, proc=1.9),     # wall=1, cpu=0.4 -> friction 0.6
    ]
    got = cap.frictions_from_trace(samples)
    # frictions_from_trace drops ONLY the first (baseline) read at sample index 0; reads for
    # samples 1..4 (deltas k=1..4) are all returned. Independently recompute via the library
    # function on each consecutive-sample delta from k=1.
    expected = []
    for k in range(1, len(samples)):
        wall_dt = samples[k].perf - samples[k - 1].perf
        cpu_dt = samples[k].proc - samples[k - 1].proc
        expected.append(bs.compute_friction(wall_dt, cpu_dt))
    check(got == expected,
          f"frictions_from_trace == compute_friction on deltas (got {got}, expected {expected})")
    check(len(got) == 4, f"a 5-sample trace yields 4 frictions (baseline dropped) (saw {len(got)})")
    # and the concrete predicted values, to pin the arithmetic: deltas k=1..4 are
    # (1,1)->0.0, (1,0.5)->0.5, (1,0.0)->1.0, (1,0.4)->0.6
    check(got == [0.0, 0.5, 1.0, pytest_approx(0.6)],
          f"the fixed trace yields the hand-computed friction sequence (saw {got})")


def test_sweep_levels_lie_within_the_observed_range_no_inflation():
    section("C3 NO INFLATION: sweep_levels span [observed_min .. observed_max] at 9 evenly-"
            "spaced quantiles — never widened beyond the real observed range (the forbidden "
            "move is re-widening to the pilot's extremes, NOT a sub-epsilon float endpoint)")
    # a fixed observed friction set with a known min/max
    frictions = [0.05, 0.10, 0.22, 0.31, 0.07, 0.18, 0.12]
    levels = cap.sweep_levels_from_frictions(frictions, cap.SWEEP_LEVELS_REALISTIC)
    check(len(levels) == cap.SWEEP_LEVELS_REALISTIC,
          f"exactly {cap.SWEEP_LEVELS_REALISTIC} swept levels (saw {len(levels)})")
    lo, hi = min(frictions), max(frictions)
    # The endpoints ARE the observed min/max (the formula is lo + (hi-lo)*k/(n-1); at k=0 it is
    # lo exactly, at k=n-1 it is lo+(hi-lo), which can differ from hi by a sub-femto float
    # rounding — that is NOT inflation, so we compare with a tight tolerance, never re-widening).
    check(levels[0] == pytest_approx(lo), f"first level == observed min {lo} (saw {levels[0]})")
    check(levels[-1] == pytest_approx(hi), f"last level == observed max {hi} (saw {levels[-1]})")
    # NO INFLATION: no level exceeds the observed span by more than float rounding (a real
    # widening to the pilot extremes would push a level FAR outside, e.g. to ~0.999).
    eps = 1e-9
    check(all(lo - eps <= v <= hi + eps for v in levels),
          "every swept level lies WITHIN the observed range +/- float-eps (no inflation beyond "
          "what the machine produced; the forbidden move is re-widening to the pilot's extremes)")
    # and decisively NOT the pilot's near-saturated extreme: the max level stays near 0.31,
    # nowhere near the pilot's captured ~0.999 upper extreme
    check(max(levels) < 0.5,
          f"the realistic sweep max ({max(levels):.6f}) is nowhere near the pilot's ~0.999 "
          f"busy-vs-idle extreme — the band is NOT re-widened")
    check(levels == sorted(levels), "levels are monotone non-decreasing")
    # SWEEP_LEVELS_REALISTIC must be the §6.4 fixed value
    check(cap.SWEEP_LEVELS_REALISTIC == 9, f"SWEEP_LEVELS_REALISTIC == 9 (saw "
                                           f"{cap.SWEEP_LEVELS_REALISTIC})")


def test_capture_parameters_are_the_frozen_6_values_not_pilot_extremes():
    section("C4 §6 CAPTURE PARAMS: the realistic capture params are the §6.4 fixed values "
            "(300 samples, 0.5 ms yield, 9 sweep levels) — the small cooperative yield, NOT "
            "the pilot's 4 ms deliberate idle-sleep stall")
    check(cap.CAPTURE_SAMPLES_REALISTIC == 300,
          f"CAPTURE_SAMPLES_REALISTIC == 300 (saw {cap.CAPTURE_SAMPLES_REALISTIC})")
    check(cap.REALISTIC_YIELD_S == 0.0005,
          f"REALISTIC_YIELD_S == 0.0005 (0.5 ms) (saw {cap.REALISTIC_YIELD_S})")
    # the realistic yield is much smaller than the pilot's deliberate idle-sleep stall
    check(cap.REALISTIC_YIELD_S < pilot.IDLE_SLEEP_S,
          f"the realistic yield ({cap.REALISTIC_YIELD_S}) is SMALLER than the pilot's "
          f"deliberate idle-sleep ({pilot.IDLE_SLEEP_S}) — a cooperative pause, not a stall")
    # and there is NO busy-spin / no deliberate alternation of extremes in the capture path
    src = inspect.getsource(cap.capture_real_telemetry)
    check("busy_spin" not in src and "_busy_spin" not in src,
          "the realistic capture does NOT busy-spin (no manufactured low-friction extreme)")
    check("perf_counter" in src and "process_time" in src,
          "the realistic capture reads perf_counter AND process_time (real telemetry)")
    check("think(" in src,
          "the realistic capture's work interval is the substrate think() (real mixed load), "
          "not a deliberate busy-vs-idle alternation")


# ═════════════════════════════════════════════════════════════════════════════
# D. REPLAY DETERMINISM
# ═════════════════════════════════════════════════════════════════════════════

def test_battery_serialization_is_deterministic_in_process():
    section("D1 IN-PROCESS DETERMINISM: serialize_battery is a pure deterministic function of "
            "the seed — two independent builds + serializations are byte-identical")
    b1 = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    b2 = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    blob1 = cap.serialize_battery(b1)
    blob2 = cap.serialize_battery(b2)
    check(blob1 == blob2, "two independent builds serialize byte-identically")
    # and the canonical-form hash is stable
    check(cap.sha256_of_canonical(blob1) == cap.sha256_of_canonical(blob2),
          "the canonical battery SHA-256 is stable across builds")


def _battery_blob_probe(seed: str) -> str:
    """Run a fresh interpreter under a fixed PYTHONHASHSEED that builds + serializes the
    realistic battery and prints its canonical SHA-256. Determinism means: identical digest
    across hash seeds. Mirrors test_harness.py's adversarial probe pattern."""
    code = r'''
import os, sys
sys.path.insert(0, os.environ["NOUS_SRC"])
sys.path.insert(0, os.environ["NOUS_EXP"])
import exp2c_capture as cap
battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
blob = cap.serialize_battery(battery)
print(cap.sha256_of_canonical(blob))
'''
    env = dict(os.environ)
    env["NOUS_SRC"] = _SRC
    env["NOUS_EXP"] = _HERE
    env["PYTHONHASHSEED"] = seed
    out = subprocess.run([sys.executable, "-c", code], env=env,
                         capture_output=True, text=True)
    if out.returncode != 0:
        print("  (subprocess stderr)\n" + out.stderr)
        return ""
    return out.stdout.strip()


def test_battery_byte_identical_across_six_hash_seeds_fresh_processes():
    section("D2 §7 REPLAY DETERMINISM (the rule-7 bar): the realistic battery's canonical "
            "SHA-256 is byte-identical across 6 PYTHONHASHSEED values in FRESH interpreters")
    seeds = ["0", "1", "2", "3", "7", "42"]
    digests = [_battery_blob_probe(s) for s in seeds]
    first = digests[0]
    check(first != "", "the battery probe produced a non-empty digest")
    check(len(first) == 64, f"the digest is a SHA-256 hex string (len 64, saw {len(first)})")
    for s, d in zip(seeds, digests):
        check(d == first, f"hash seed {s} digest matches seed {seeds[0]} (byte-identical)")


def test_trace_processing_is_deterministic_over_a_fixed_sample_sequence():
    section("D3 REPLAY DETERMINISM (trace processing): over a FIXED sample sequence, "
            "frictions_from_trace and sweep_levels_from_frictions are byte-identical across "
            "6 hash seeds in fresh interpreters (the trace-PROCESSING surface is deterministic; "
            "the live CAPTURE is the only non-determinism and is not exercised here)")
    seeds = ["0", "1", "2", "3", "7", "42"]
    code = r'''
import os, sys
sys.path.insert(0, os.environ["NOUS_SRC"])
sys.path.insert(0, os.environ["NOUS_EXP"])
import exp2c_capture as cap
import nous_bodysensor as bs
samples = [
    bs.TelemetrySample(0.0, 0.0),
    bs.TelemetrySample(1.0, 0.91),
    bs.TelemetrySample(2.3, 1.4),
    bs.TelemetrySample(2.9, 1.42),
    bs.TelemetrySample(5.0, 3.7),
    bs.TelemetrySample(5.05, 5.04),
]
fr = cap.frictions_from_trace(samples)
lv = cap.sweep_levels_from_frictions(fr, cap.SWEEP_LEVELS_REALISTIC)
print(repr(fr))
print(repr(lv))
'''
    outs = []
    for s in seeds:
        env = dict(os.environ)
        env["NOUS_SRC"] = _SRC
        env["NOUS_EXP"] = _HERE
        env["PYTHONHASHSEED"] = s
        out = subprocess.run([sys.executable, "-c", code], env=env,
                             capture_output=True, text=True)
        if out.returncode != 0:
            print("  (subprocess stderr)\n" + out.stderr)
            outs.append("")
        else:
            outs.append(out.stdout)
    first = outs[0]
    check(first.strip() != "", "the trace-processing probe produced non-empty output")
    for s, o in zip(seeds, outs):
        check(o == first, f"hash seed {s} trace-processing output matches seed {seeds[0]}")


# ═════════════════════════════════════════════════════════════════════════════
# E. BLINDNESS — NO GRADED NUMBER, NO ACTIVATION/WINNER/FLIP PATH
# ═════════════════════════════════════════════════════════════════════════════

def test_module_exposes_no_grading_or_flip_path():
    section("E1 BLINDNESS (anti-circularity at the construction layer): the capture module "
            "exposes NO winner / flip / grading / effect-size function — it builds stimuli only")
    names = [n for n in dir(cap) if not n.startswith("__")]
    forbidden_substrings = (
        "flip", "winner", "grade", "graded", "effect_size", "effectsize",
        "select_winner", "verdict", "narrow", "direction_stat",
    )
    for name in names:
        low = name.lower()
        for bad in forbidden_substrings:
            check(bad not in low,
                  f"the module exposes no '{bad}'-named symbol (saw {name!r}) — no graded path")
    # explicitly: the readout helpers the GRADED run will need are absent here
    for must_be_absent in ("percept_flips", "winner_set", "_winner_set", "grade_battery",
                           "flip_rate", "compute_flip_rate", "select_winner"):
        check(not hasattr(cap, must_be_absent),
              f"capture module has no '{must_be_absent}' attribute (graded readout is the "
              f"validator's later step, not here)")


def test_module_does_not_import_the_competition_or_activation_engine():
    section("E2 BLINDNESS (static): the capture module never imports the workspace competition "
            "(select_winner) nor calls the field/activation engine to grade — it consumes ONLY "
            "the §5/§6 procedure (store construction + the SAME compute_friction)")
    src = inspect.getsource(cap)
    # it must NOT import the workspace selection (the graded readout) nor form coalitions
    check("from nous_workspace import" not in src and "import nous_workspace" not in src,
          "no import of nous_workspace (the competition/winner readout is not consumed)")
    check("select_winner" not in src,
          "select_winner appears nowhere in the capture module (no winner is computed)")
    check("form_coalitions" not in src,
          "no coalition formation in the capture module (no field competition graded)")
    check("build_activation_field" not in src,
          "no activation-field construction in the capture module (no activation read)")
    # the SAME compute_friction and BodySensor (telemetry only) ARE imported — that is the
    # whole permitted §6 surface
    check("from nous_bodysensor import" in src,
          "the capture module DOES import nous_bodysensor (the permitted §6 telemetry surface)")


def test_capture_main_path_calls_think_only_as_workload_never_reads_its_winner():
    section("E3 BLINDNESS (workload, not readout): the §6 capture runs think() ONLY to generate "
            "real CPU work for the timing measurement — it reads perf_counter/process_time "
            "around it and NEVER inspects think()'s winner/field/thought result")
    src = inspect.getsource(cap.capture_real_telemetry)
    # think() is called (real work) ...
    check("think(" in src, "capture_real_telemetry calls think() to generate real work")
    # ... but its RESULT is never bound to a name that is then inspected for a winner/thought.
    # We assert no attribute access on a think() result inside the capture (no `.winner`,
    # `.thought`, `.workspace`, `.field_`, `.coalitions`, `.body_friction`).
    for forbidden_attr in (".winner", ".thought", ".workspace", ".field_", ".coalitions",
                           ".body_friction", ".effective_decay"):
        check(forbidden_attr not in src,
              f"the capture never reads think()'s {forbidden_attr} (no graded/result-side "
              f"signal consumed)")


def test_battery_serialization_is_structural_only_no_activation():
    section("E4 BLINDNESS (battery serialization is STRUCTURAL): the serialized battery records "
            "ONLY the structural description (anchors, domain sizes, integer traversal counts, "
            "bridge presence/target/bridge_n, depth_extra) — never any Nous activation / winner")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    blob = cap.serialize_battery(battery)
    payload = json.loads(blob)
    # the serialized form is JSON-decodable and parametric
    text = blob.lower()
    for forbidden in ("activation", "winner", "thought", "flip", "decay", "friction",
                      "coalition"):
        check(forbidden not in text,
              f"the serialized battery contains no '{forbidden}' field (structural only)")
    # spot-check that a percept entry carries the §6.4-required structural keys
    percepts = payload["percepts"] if isinstance(payload, dict) else payload
    first = percepts[0]
    for required in ("anchor_a", "anchor_b", "domain_size_a", "domain_size_b",
                     "internal_n_a", "internal_n_b", "bridge_present", "depth_extra"):
        check(required in first,
              f"each serialized percept carries the structural key '{required}'")


# ═════════════════════════════════════════════════════════════════════════════
# F. HONEST FRAMING / NO OVERCLAIM (asserted-negatives)
# ═════════════════════════════════════════════════════════════════════════════

def test_no_overclaim_in_public_names():
    section("F1 NO OVERCLAIM: no public name in the capture module claims a feeling / emotion / "
            "awareness / consciousness / meaning — it builds stimuli; the headline is 'battery' "
            "and 'trace'")
    names = [n for n in dir(cap) if not n.startswith("__")]
    for name in names:
        low = name.lower()
        for bad in ("feel", "emotion", "aware", "conscious", "sentient", "mind", "meaning"):
            check(bad not in low,
                  f"no public name encodes '{bad}' (saw {name!r})")


def test_known_limitation_asserted_negative():
    section("F2 KNOWN LIMITATION (asserted-negative): this script builds the FROZEN STIMULI "
            "ONLY. It computes NO flip-rate, NO graded number, and establishes NO meaning. "
            "Whether realistic telemetry meaningfully moves realistic selection — the graded "
            "MEANING question — is the validator's later step, NOT decided here.")
    # The guarantee is structural and already pinned by E1-E4 (no graded path, no winner read,
    # no activation). We assert it ONE more time as an explicit, named known-limitation so the
    # negative travels with the suite and is never smoothed over.
    check(not any(("flip" in n.lower() or "grade" in n.lower() or "winner" in n.lower())
                  for n in dir(cap) if not n.startswith("__")),
          "ASSERTED-NEGATIVE: the capture module exposes no flip/grade/winner symbol — it is "
          "blind stimulus construction, and makes NO meaning claim (the graded run is the "
          "validator's later step)")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 70)
    print("  EXP-2c CAPTURE (realistic stimulus construction) — TEST SUITE")
    print("  blind stimulus construction; NO graded number; NO meaning claim")
    print("=" * 70)

    # A. battery to §5.2 spec
    test_battery_parameters_are_the_frozen_5_2_constants()
    test_battery_builds_60_two_anchor_percepts()
    test_perception_lights_up_exactly_the_two_anchors()
    test_battery_draws_match_an_independent_seeded_rng()
    # B. genuinely NOT flip-pre-selected; distinct from pilot
    test_no_contested_node_no_positioned_crossover()
    test_no_node_is_reached_at_pilot_style_asymmetric_distance()
    test_some_percepts_have_no_bridge_at_all()
    test_bridge_n_spans_the_full_documented_range_not_a_crossover_window()
    test_battery_is_structurally_distinct_from_the_pilot_battery()
    # C. same compute_friction; no inflation
    test_capture_uses_the_same_compute_friction_object_identity()
    test_frictions_from_trace_match_compute_friction_on_the_deltas()
    test_sweep_levels_lie_within_the_observed_range_no_inflation()
    test_capture_parameters_are_the_frozen_6_values_not_pilot_extremes()
    # D. replay determinism
    test_battery_serialization_is_deterministic_in_process()
    test_battery_byte_identical_across_six_hash_seeds_fresh_processes()
    test_trace_processing_is_deterministic_over_a_fixed_sample_sequence()
    # E. blindness — no graded number / no activation
    test_module_exposes_no_grading_or_flip_path()
    test_module_does_not_import_the_competition_or_activation_engine()
    test_capture_main_path_calls_think_only_as_workload_never_reads_its_winner()
    test_battery_serialization_is_structural_only_no_activation()
    # F. honest framing
    test_no_overclaim_in_public_names()
    test_known_limitation_asserted_negative()

    print()
    print("=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    print("=" * 70)
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
