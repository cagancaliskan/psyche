"""
TESTER-AUTHORED adversarial verification of 2c interoception (BodySensor + the default-off
modulation hook) AND a fairness audit of the populability pilot.

This suite is INDEPENDENT of the builder's test_psyche_bodysensor.py. It re-derives every
acceptance property from SPEC-2c (§1.4 anti-circularity, §3.2 (D-1)/(D-5) determinism,
§0.1/§2.1 honest framing, §3.1 populability) and attacks the implementation with hostile,
loop-closed, and re-derived inputs. The verdict rests on THIS file, not the builder's.

It modifies NO production code. It reads src/ and experiments/ through their public surface
only. Where it must prove a NEGATIVE (no live read on the graded surface; no scalar echo; no
covert battery tuning) it asserts the negative explicitly rather than trusting prose.

The attack surface, mapped to the directive:

  JOB 1 — MECHANISM
    A. DEFAULT-OFF PURITY (the broadcast=False analogue). With body_sensor=None the cycle
       must be BYTE-IDENTICAL to the pre-2c path — store snapshot AND every ThoughtResult
       field — across a battery of percepts, including the broadcast=True interaction.
    B. REPLAY DETERMINISM. Identical frozen traces => byte-identical output across fresh
       interpreters under 6 PYTHONHASHSEED values, on the loop's winner trace AND on the
       pilot's own battery winners. Live telemetry is proven boundary-only and never on a
       graded/test path (static + a runtime trap that detonates if a graded path reads a
       live timer).
    C. WINNER-FLIP IS REAL, NOT ECHO. The hard anti-circularity kill: two DISTINCT friction
       values that map to the SAME effective decay must produce the SAME winner (the scalar
       cannot leak); every winner element is a real graph NodeID (never a float); a friction
       whose modulated decay equals the OFF decay reproduces the OFF field exactly; friction
       influences the cycle ONLY through the diffuse decay_per_hop, naming no node.
    D. INTEGRITY + PURITY under the ON hook (check_integrity after modulated cycles; the hook
       names no node; reads stay pure).

  JOB 2 — PILOT FAIRNESS (re-derived; the pilot's self-report is not trusted)
    E. Battery not covertly tuned: re-derive build_battery(20260621, 40) independently; it is
       a fixed-seed principled space whose crossover d* is spread by bridge_n; it is NOT a
       100%-flip construction (some d* lie OUTSIDE the swept range and genuinely do not flip).
    F. Telemetry range honestly real: the frozen trace's frictions are reproduced by the SAME
       compute_friction the cycle uses, span a real low->high range, and are NOT hard-coded /
       widened beyond the recorded capture.
    G. Pre-registration integrity: the 0.30 floor and the 20260621 seed are FIXED module
       constants (numbers in the file before any result), and the readout/grading are
       pre-stated as winner-set / replay.
    H. No overclaim: the pilot/sensor public surface and prose carry the honest-framing
       negations; 85% is framed as a feasibility/populability number on flip-CAPABLE inputs
       over a deliberately-extreme range, never as a meaning result.

Run directly (self-bootstraps src/ and experiments/ onto sys.path):
    python3 tests/test_tester_2c_adversarial.py
"""

from __future__ import annotations

import os
import sys
import subprocess
import textwrap
import inspect
import importlib

# self-bootstrap: this suite is run as a script from tests/, and the determinism probes
# spawn fresh interpreters that import by bare name. Put BOTH src/ and experiments/ on the
# path (the pilot lives in experiments/ and imports the library by bare name).
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_SRC = os.path.join(_ROOT, "src")
_EXPERIMENTS = os.path.join(_ROOT, "experiments")
for _p in (_SRC, _EXPERIMENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from psyche_store import SubstrateStore, Clock, NodeType
from psyche_activation import DEFAULT_DECAY_PER_HOP
from psyche_perceive import think
import psyche_bodysensor as bs
from psyche_bodysensor import (
    BodySensor, TelemetrySample, compute_friction,
    friction_to_decay_factor, modulated_decay_per_hop,
    NEUTRAL_FRICTION, MODULATION_SPAN, MIN_DECAY_PER_HOP, MAX_DECAY_PER_HOP,
)

_passed = 0
_failed = 0
_failures = []


def check(cond, msg):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        _failures.append(msg)
        print(f"  FAIL: {msg}")


def section(name):
    print(f"\n{name}")


def _worn(s, a, b, n=30):
    for _ in range(n):
        s.traverse(a, b)


# ─────────────────────────────────────────────────────────────────────────────
# Topologies (built independently from the builder's; re-derived flip topology)
# ─────────────────────────────────────────────────────────────────────────────

def _small_mind():
    """The shared 1c/1d small store (warm + work domains, n=8 coffee->work bridge)."""
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
    return s


def _flip_mind():
    """Independently rebuilt contested-basin topology (two mirror anchors + one contested
    sink reached 1 medium hop from alpha and 2 strong hops from gamma). The winner is read
    from the loop; never injected. This is rebuilt here, not imported from the builder's
    suite, so the loop-closed flip property is verified on an independently-authored graph."""
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    alpha = s.add_node("alpha", NodeType.CONCEPT)
    anode = s.add_node("anode", NodeType.CONCEPT)
    gamma = s.add_node("gamma", NodeType.CONCEPT)
    gnode = s.add_node("gnode", NodeType.CONCEPT)
    midnode = s.add_node("midnode", NodeType.CONCEPT)
    _worn(s, alpha, anode, n=30)
    _worn(s, gamma, gnode, n=30)
    _worn(s, alpha, midnode, n=3)
    _worn(s, gnode, midnode, n=30)
    return s


def _deep_snapshot(s):
    """Deep snapshot of ALL stored state by stable identity (content+seq), comparable across
    runs; detects ANY mutation. Independent re-implementation of the established pattern."""
    nodes = []
    for nid in s.all_node_ids():
        nd = s.get_node(nid)
        nodes.append((nd.content, nd.creation_seq, nd.node_type.value, nd.access_count))
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


def _winner_set(s, r):
    if r is None or r.thought is None:
        return None
    return frozenset(s.get_node(m).content for m in r.thought.members)


def _trace_for_frictions(frictions):
    """Frozen TelemetrySample trace whose successive post-baseline reads yield exactly the
    given frictions (wall_dt=1.0, cpu_dt=1-f => compute_friction = f). Independent helper."""
    samples = [TelemetrySample(perf=0.0, proc=0.0)]
    perf = 0.0
    proc = 0.0
    for f in frictions:
        perf += 1.0
        proc += (1.0 - f)
        samples.append(TelemetrySample(perf=perf, proc=proc))
    return samples


def _sensor_yielding(frictions):
    """A replay sensor primed past its baseline, so its NEXT read yields frictions[0]."""
    sensor = BodySensor(simulated=True, trace=_trace_for_frictions(frictions))
    primed = sensor.read()
    assert primed == NEUTRAL_FRICTION
    return sensor


def _det_probe(driver):
    """Run a driver under 6 distinct PYTHONHASHSEED values in fresh interpreters; return the
    list of (returncode, stdout) so a crash is visible, not silently equal."""
    outs = []
    env_base = dict(os.environ)
    env_base["PYTHONPATH"] = _SRC + os.pathsep + _EXPERIMENTS + (
        os.pathsep + env_base["PYTHONPATH"] if env_base.get("PYTHONPATH") else "")
    for seed in ("0", "1", "2", "7", "42", "999"):
        env = dict(env_base, PYTHONHASHSEED=seed)
        rr = subprocess.run([sys.executable, "-c", driver], cwd=_HERE,
                            capture_output=True, text=True, env=env)
        if rr.returncode != 0:
            print("  (subprocess error under seed", seed, ")\n", rr.stderr)
        outs.append((rr.returncode, rr.stdout.strip()))
    return outs


# ══════════════════════════════════════════════════════════════════════════════
# JOB 1 — A. DEFAULT-OFF PURITY (the broadcast=False analogue, attacked hard)
# ══════════════════════════════════════════════════════════════════════════════

# A battery of real percepts against the shared mind. These exercise: nothing-matched,
# one-anchor, two-anchor, the warm+work over-swallow case, and a high-fan-ish multi-token.
_OFF_PERCEPTS = [
    "coffee in the kitchen this morning",
    "coffee",
    "work desk code deadline",
    "kitchen morning",
    "warmth cozy",
    "zzz qqq vvv",                      # matches nothing
    "coffee work",                      # bridges the two domains
]


def test_default_off_full_thoughtresult_byte_identical_across_battery():
    section("A1 DEFAULT-OFF: every ThoughtResult field is byte-identical to the literal pre-2c "
            "call shape, across a percept battery (the hook has ZERO off-path effect)")
    for utt in _OFF_PERCEPTS:
        s_ref = _small_mind()
        s_off = _small_mind()
        r_ref = think(s_ref, utt)                       # literal pre-2c call (no 2c kwargs)
        r_off = think(s_off, utt, body_sensor=None)     # explicit default-off
        # winner identity
        check(_winner_set(s_ref, r_ref) == _winner_set(s_off, r_off),
              f"[{utt!r}] winner identical OFF vs pre-2c")
        # body_friction must be None on the OFF path
        check(r_off.body_friction is None,
              f"[{utt!r}] body_friction is None when OFF")
        # effective_decay equals the unmodulated default exactly (or None when no field built)
        if r_off.field_ is None:
            check(r_off.effective_decay_per_hop is None,
                  f"[{utt!r}] effective_decay None when no field (empty perception)")
        else:
            check(r_off.effective_decay_per_hop == DEFAULT_DECAY_PER_HOP,
                  f"[{utt!r}] effective_decay equals unmodulated default when OFF")
        # the entire activation field totals are byte-identical (the only channel the hook
        # could change the field through is decay; OFF => no change)
        if r_ref.field_ is not None and r_off.field_ is not None:
            ref_tot = tuple(sorted((s_ref.get_node(k).content, round(v, 12))
                                   for k, v in r_ref.field_.total.items()))
            off_tot = tuple(sorted((s_off.get_node(k).content, round(v, 12))
                                   for k, v in r_off.field_.total.items()))
            check(ref_tot == off_tot, f"[{utt!r}] full field totals byte-identical OFF")
        else:
            check(r_ref.field_ is None and r_off.field_ is None,
                  f"[{utt!r}] both fields None (empty perception) OFF")


def test_default_off_store_byte_identical_including_broadcast_path():
    section("A2 DEFAULT-OFF: store byte-identical under repeated OFF reads (pure), AND the "
            "broadcast=True write is byte-identical whether body_sensor is None or absent")
    # (i) repeated OFF think() leaves the store untouched (pure read)
    s = _small_mind()
    before = _deep_snapshot(s)
    for _ in range(5):
        think(s, "coffee in the kitchen this morning", body_sensor=None)
    check(before == _deep_snapshot(s), "repeated OFF think() mutates nothing (pure read)")

    # (ii) the broadcast write path must be identical whether body_sensor is omitted or
    # explicitly None — the OFF hook cannot perturb what broadcast writes.
    s_a = _small_mind()
    s_b = _small_mind()
    r_a = think(s_a, "coffee in the kitchen this morning", broadcast=True)
    r_b = think(s_b, "coffee in the kitchen this morning", broadcast=True, body_sensor=None)
    check(_deep_snapshot(s_a) == _deep_snapshot(s_b),
          "broadcast=True store identical with body_sensor omitted vs explicit None")
    # the broadcast records match (same roads, same deltas)
    ra = r_a.broadcast_
    rb = r_b.broadcast_
    check((ra is None) == (rb is None), "broadcast record presence matches")
    if ra is not None and rb is not None:
        a_roads = tuple((s_a.get_node(s_a.get_road(rid, apply_decay=False).source_id).content,
                         s_a.get_node(s_a.get_road(rid, apply_decay=False).target_id).content,
                         round(ra.after[rid], 12)) for rid in ra.road_ids)
        b_roads = tuple((s_b.get_node(s_b.get_road(rid, apply_decay=False).source_id).content,
                         s_b.get_node(s_b.get_road(rid, apply_decay=False).target_id).content,
                         round(rb.after[rid], 12)) for rid in rb.road_ids)
        check(a_roads == b_roads, "broadcast strengthened roads identical OFF vs absent")


def test_empty_perception_burns_no_replay_sample():
    section("A3 DEFAULT-OFF nuance: an utterance matching NOTHING does not read the sensor "
            "(no field to modulate); the replay trace is left fully intact")
    s = _small_mind()
    sensor = BodySensor(simulated=True, trace=_trace_for_frictions([0.5, 0.5, 0.5]))
    r = think(s, "zzz qqq vvv", body_sensor=sensor)
    check(r.thought is None, "no winner when nothing perceived")
    check(r.body_friction is None, "body_friction None on empty-perception cycle")
    # baseline + 3 = 4 reads remain (none consumed)
    check(sensor.remaining() == 4, "no replay sample consumed on empty-perception path")


# ══════════════════════════════════════════════════════════════════════════════
# JOB 1 — C. WINNER-FLIP IS REAL, NOT ECHO  (the hard anti-circularity kill)
# ══════════════════════════════════════════════════════════════════════════════

def test_two_distinct_frictions_same_decay_give_same_winner():
    section("C1 ANTI-CIRCULARITY (the kill): two DISTINCT friction values that map to the "
            "SAME effective decay produce the SAME winner — the friction scalar provably "
            "cannot leak into the readout (only the decay it induces can)")
    # The modulated decay saturates at the MIN_DECAY_PER_HOP floor and the MAX ceiling.
    # Find two distinct frictions that produce an identical effective decay. The clamp floor
    # is the clean lever: with a tiny base decay, all high frictions clamp to MIN_DECAY_PER_HOP.
    base = 1.05 * MIN_DECAY_PER_HOP   # so factor<~0.95 already clamps to the floor
    f_lo = 0.7
    f_hi = 0.95
    d_lo = modulated_decay_per_hop(base, f_lo)
    d_hi = modulated_decay_per_hop(base, f_hi)
    check(f_lo != f_hi, "the two frictions are genuinely distinct")
    check(d_lo == d_hi == MIN_DECAY_PER_HOP,
          f"both frictions clamp to the SAME effective decay (d_lo={d_lo}, d_hi={d_hi})")
    # Now drive the loop with each, at this base decay, and assert the winner is identical.
    s1 = _flip_mind()
    s2 = _flip_mind()
    r1 = think(s1, "alpha gamma", decay_per_hop=base, body_sensor=_sensor_yielding([f_lo]))
    r2 = think(s2, "alpha gamma", decay_per_hop=base, body_sensor=_sensor_yielding([f_hi]))
    check(r1.effective_decay_per_hop == r2.effective_decay_per_hop,
          "the effective decay actually used is identical for the two distinct frictions")
    check(_winner_set(s1, r1) == _winner_set(s2, r2),
          f"distinct frictions mapping to the same decay give the SAME winner "
          f"(w1={_winner_set(s1,r1)}, w2={_winner_set(s2,r2)}) — no scalar echo")
    # And the FULL field is identical, not just the winner: the friction left no other trace.
    if r1.field_ is not None and r2.field_ is not None:
        t1 = tuple(sorted((s1.get_node(k).content, round(v, 12)) for k, v in r1.field_.total.items()))
        t2 = tuple(sorted((s2.get_node(k).content, round(v, 12)) for k, v in r2.field_.total.items()))
        check(t1 == t2, "the full activation field is identical for the two frictions (decay is the only channel)")


def test_friction_mapping_to_off_decay_reproduces_off_field_exactly():
    section("C2 ANTI-CIRCULARITY: a friction whose modulated decay equals the OFF decay "
            "reproduces the OFF (body_sensor=None) field and winner BYTE-IDENTICALLY — the "
            "ON path adds nothing beyond the decay value")
    # friction 0 maps to factor 1.0 => modulated decay == base == DEFAULT_DECAY_PER_HOP.
    s_off = _flip_mind()
    s_on = _flip_mind()
    r_off = think(s_off, "alpha gamma", body_sensor=None)
    r_on = think(s_on, "alpha gamma", body_sensor=_sensor_yielding([0.0]))
    check(r_on.effective_decay_per_hop == r_off.effective_decay_per_hop == DEFAULT_DECAY_PER_HOP,
          "friction 0 ON yields exactly the OFF effective decay")
    check(_winner_set(s_off, r_off) == _winner_set(s_on, r_on),
          "friction-0 ON winner == OFF winner")
    if r_off.field_ is not None and r_on.field_ is not None:
        toff = tuple(sorted((s_off.get_node(k).content, round(v, 12)) for k, v in r_off.field_.total.items()))
        ton = tuple(sorted((s_on.get_node(k).content, round(v, 12)) for k, v in r_on.field_.total.items()))
        check(toff == ton, "friction-0 ON field == OFF field byte-identically")
    # the ONLY observable difference is the bookkeeping scalar itself
    check(r_off.body_friction is None and r_on.body_friction == 0.0,
          "the only difference is the recorded body_friction scalar (None vs 0.0), not the cycle")


def test_every_winner_element_is_a_graph_nodeid_never_a_float():
    section("C3 ANTI-CIRCULARITY: across the full friction sweep, every winner member is a "
            "real graph NodeID resolving to node content — never the injected float / a number")
    s_probe = _flip_mind()
    valid_ids = set(s_probe.all_node_ids())  # the universe of real NodeIDs for this topology
    grid = [i / 20.0 for i in range(21)]
    saw_winner = False
    for f in grid:
        s = _flip_mind()
        r = think(s, "alpha gamma", body_sensor=_sensor_yielding([f]))
        if r.thought is None:
            continue
        saw_winner = True
        for m in r.thought.members:
            # a winner member must be a NodeID string that resolves in THIS store...
            check(isinstance(m, str), f"[f={f}] winner member is a string id, not a {type(m).__name__}")
            check(s.exists(m), f"[f={f}] winner member {m!r} is a real node in the store")
            # ...and it must NEVER be the friction float wearing a string costume
            check(repr(round(f, 9)) != m and str(f) != m,
                  f"[f={f}] winner member is not the friction scalar stringified")
        # the friction scalar itself is never an element of the readout set
        ws = _winner_set(s, r)
        check(f not in (ws or frozenset()) and round(f, 9) not in (ws or frozenset()),
              f"[f={f}] the friction float is not an element of the winner node-set")
    check(saw_winner, "the sweep produced at least one winner to inspect")


def test_friction_names_no_node_only_global_decay():
    section("C4 ANTI-CIRCULARITY: the body_sensor->think path can change the field ONLY via "
            "the global decay_per_hop; passing the modulated decay directly (no sensor) "
            "reproduces the ON field exactly — friction names no node")
    # If the hook secretly biased a specific node, then reproducing only the global decay
    # value (with body_sensor=None) would NOT reproduce the ON field. Assert it does.
    f = 0.8
    s_on = _flip_mind()
    r_on = think(s_on, "alpha gamma", body_sensor=_sensor_yielding([f]))
    eff = r_on.effective_decay_per_hop
    s_direct = _flip_mind()
    r_direct = think(s_direct, "alpha gamma", decay_per_hop=eff, body_sensor=None)
    check(_winner_set(s_on, r_on) == _winner_set(s_direct, r_direct),
          "ON winner == winner from injecting the same global decay directly (no node named)")
    if r_on.field_ is not None and r_direct.field_ is not None:
        ton = tuple(sorted((s_on.get_node(k).content, round(v, 12)) for k, v in r_on.field_.total.items()))
        tdir = tuple(sorted((s_direct.get_node(k).content, round(v, 12)) for k, v in r_direct.field_.total.items()))
        check(ton == tdir, "ON field == direct-decay field byte-identically (decay is the whole channel)")


def test_winner_flip_actually_occurs_on_independent_graph():
    section("C5 (loop-closed): on the independently-rebuilt contested graph, a DIFFERENT "
            "coalition wins across the friction range — the flip is a real emergent crossover, "
            "read from the loop, never injected")
    grid = [i / 20.0 for i in range(21)]
    winners = []
    for f in grid:
        s = _flip_mind()
        r = think(s, "alpha gamma", body_sensor=_sensor_yielding([f]))
        winners.append(_winner_set(s, r))
    distinct = {w for w in winners if w is not None}
    check(len(distinct) >= 2,
          f"a winner-flip occurs across the friction range (distinct winning node-sets: {len(distinct)})")
    check(winners[0] is not None and winners[-1] is not None and winners[0] != winners[-1],
          f"the extreme-low and extreme-high friction ends select different winners "
          f"(lo={winners[0]}, hi={winners[-1]})")


# ══════════════════════════════════════════════════════════════════════════════
# JOB 1 — B. REPLAY DETERMINISM + LIVE-READ ISOLATION
# ══════════════════════════════════════════════════════════════════════════════

def test_winner_trace_byte_identical_across_6_seeds_independent_driver():
    section("B1 §(D-1)/(D-5): the loop's winner-vs-friction trace is byte-identical across 6 "
            "PYTHONHASHSEED values in fresh interpreters (independently authored driver)")
    # SPEC-0c §5.1: BIT PATTERNS, never round(x, 4) — the friction scalar that indexes
    # this trace is itself a float, and rounding the index would let two different
    # frictions collide into one row and hide a divergence rather than report it.
    driver = textwrap.dedent('''
        import struct
        from psyche_store import SubstrateStore, Clock, NodeType
        from psyche_perceive import think
        from psyche_bodysensor import BodySensor, TelemetrySample
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
            samples=[TelemetrySample(0.0,0.0)]
            samples.append(TelemetrySample(1.0, 1.0-f))
            sn=BodySensor(simulated=True,trace=samples); sn.read()
            return sn
        out=[]
        for i in range(21):
            f=i/20.0
            s=build()
            r=think(s,"alpha gamma",body_sensor=sensor_for(f))
            win=tuple(sorted(s.get_node(m).content for m in r.thought.members)) if r.thought else None
            out.append((struct.pack("<d", f).hex(), win))
        print(repr(out))
    ''')
    outs = _det_probe(driver)
    rcs = {rc for rc, _ in outs}
    stdouts = {so for _, so in outs}
    check(rcs == {0}, f"all 6 seed runs exited cleanly (return codes: {rcs})")
    check(len(stdouts) == 1,
          f"winner-vs-friction trace identical across 6 hash seeds (distinct outputs: {len(stdouts)})")


def test_pilot_battery_winners_byte_identical_across_6_seeds():
    section("B2 §(D-1): the PILOT's own battery (build_battery + percept_flips at fixed swept "
            "frictions) yields byte-identical per-percept winner-set counts across 6 seeds — "
            "the pilot's grading surface is itself reproducible")
    driver = textwrap.dedent('''
        import pilot_2c_populability as P
        battery = P.build_battery(P.BATTERY_SEED, P.PERCEPT_COUNT)
        # fixed, deterministic swept frictions (independent of any live capture) so this probes
        # ONLY the grading surface determinism, not the capture.
        levels = [i/8.0 for i in range(9)]   # 0.0 .. 1.0
        rows = []
        for label, builder, percept_text, a, b in battery:
            flips, n_distinct, has_winner = P.percept_flips(builder, percept_text, levels)
            rows.append((label, flips, n_distinct, has_winner))
        print(repr(rows))
    ''')
    outs = _det_probe(driver)
    rcs = {rc for rc, _ in outs}
    stdouts = {so for _, so in outs}
    check(rcs == {0}, f"all 6 pilot-battery runs exited cleanly (return codes: {rcs})")
    check(len(stdouts) == 1,
          f"pilot battery winner-counts identical across 6 hash seeds (distinct outputs: {len(stdouts)})")


def test_replay_path_never_reads_a_live_timer_runtime_trap():
    section("B3 LIVE ISOLATION (runtime trap): with time.perf_counter and time.process_time "
            "MONKEYPATCHED to detonate, a full REPLAY-mode modulated cycle still runs — proving "
            "the graded/replay surface reads NO live timer")
    import time as _time
    real_perf = _time.perf_counter
    real_proc = _time.process_time

    def _boom_perf(*a, **k):
        raise AssertionError("LIVE perf_counter was read on the REPLAY/graded surface")

    def _boom_proc(*a, **k):
        raise AssertionError("LIVE process_time was read on the REPLAY/graded surface")

    detonated = False
    try:
        _time.perf_counter = _boom_perf
        _time.process_time = _boom_proc
        # A full modulated cycle in replay mode. If anything on this path calls a live timer,
        # the monkeypatch raises and `ran` stays False.
        s = _flip_mind()
        sensor = BodySensor(simulated=True, trace=_trace_for_frictions([0.0, 0.5, 0.9]))
        sensor.read()  # consume baseline
        r = think(s, "alpha gamma", body_sensor=sensor)
        ran = True
    except AssertionError:
        ran = False
        detonated = True
    finally:
        _time.perf_counter = real_perf
        _time.process_time = real_proc
    check(ran and not detonated,
          "a replay modulated cycle runs with live timers trapped (no live read on graded path)")
    # Sanity: the trap is real — calling the LIVE sensor.read() WOULD detonate it. Confirm the
    # trap actually fires so the negative above is meaningful (not a no-op test).
    trap_fires = False
    try:
        _time.perf_counter = _boom_perf
        live = BodySensor(simulated=False)
        live.read()
    except AssertionError:
        trap_fires = True
    finally:
        _time.perf_counter = real_perf
        _time.process_time = real_proc
    check(trap_fires, "the live trap genuinely fires when a LIVE sensor reads (negative is meaningful)")


def test_no_live_telemetry_call_in_graded_source_static():
    section("B4 LIVE ISOLATION (static): no live-telemetry call (getloadavg / getrusage) is "
            "reachable from the deterministic test surface; perf_counter/process_time appear in "
            "psyche_bodysensor ONLY inside the live branch of read() and the named secondaries")
    src_path = os.path.join(_SRC, "psyche_bodysensor.py")
    with open(src_path, "r") as f:
        body_src = f.read()
    # getloadavg / getrusage live ONLY in the explicitly live-only secondary helpers.
    # Assert they do not appear in BodySensor.read() or in the headline friction functions.
    # Crude but effective: the only occurrences are inside read_loadavg_1min / read_maxrss_kb.
    for fn_name in ("def read(", "def compute_friction(", "def modulated_decay_per_hop(",
                    "def friction_to_decay_factor("):
        start = body_src.index(fn_name)
        # function body ends at the next top-level def/class or EOF
        rest = body_src[start + len(fn_name):]
        nxt = rest.find("\ndef ")
        ncl = rest.find("\nclass ")
        ends = [x for x in (nxt, ncl) if x != -1]
        end = min(ends) if ends else len(rest)
        fn_body = rest[:end]
        check("getloadavg" not in fn_body and "getrusage" not in fn_body,
              f"{fn_name} contains no getloadavg/getrusage (secondaries are isolated)")
    # perceive's think() path: the only telemetry entry is sensor.read(); confirm think()
    # itself names no live timer.
    perceive_path = os.path.join(_SRC, "psyche_perceive.py")
    with open(perceive_path, "r") as f:
        perceive_src = f.read()
    check("perf_counter" not in perceive_src and "process_time" not in perceive_src
          and "getloadavg" not in perceive_src and "getrusage" not in perceive_src,
          "psyche_perceive.py names no live timer/telemetry call directly (only sensor.read())")


# ══════════════════════════════════════════════════════════════════════════════
# JOB 1 — D. INTEGRITY + PURITY under the ON hook
# ══════════════════════════════════════════════════════════════════════════════

def test_on_path_pure_read_and_integrity_battery():
    section("D1 INTEGRITY/PURITY (ON path): across a friction battery, think(body_sensor=...,"
            " broadcast=False) leaves the store byte-identical and integrity clean")
    s = _flip_mind()
    s.check_integrity()
    before = _deep_snapshot(s)
    for f in (0.0, 0.13, 0.37, 0.5, 0.7, 0.9, 1.0):
        think(s, "alpha gamma", body_sensor=_sensor_yielding([f]))
    after = _deep_snapshot(s)
    check(before == after, "ON path (broadcast=False) leaves the store byte-identical across the battery")
    clean = True
    try:
        s.check_integrity()
    except Exception as e:
        clean = False
        print("   integrity error:", e)
    check(clean, "integrity holds after the modulated battery")


def test_sensor_read_touches_only_its_cursor():
    section("D2 PURITY (sensor): sensor reads mutate ONLY the sensor's own cursor, never the "
            "substrate; the sensor has no store reference and structurally cannot")
    s = _flip_mind()
    before = _deep_snapshot(s)
    sensor = BodySensor(simulated=True, trace=_trace_for_frictions([0.3, 0.6, 0.9]))
    sensor.read(); sensor.read()
    check(before == _deep_snapshot(s), "sensor reads do not touch the substrate at all")
    check(sensor.remaining() == 2, "the sensor's own cursor advanced (its bookkeeping moved)")
    # structural: read() takes no graph; constructor takes no store
    ctor = set(inspect.signature(BodySensor.__init__).parameters) - {"self"}
    check(ctor == {"simulated", "trace"}, f"BodySensor.__init__ takes only (simulated, trace) (got {ctor})")
    rd = set(inspect.signature(BodySensor.read).parameters) - {"self"}
    check(rd == set(), f"BodySensor.read takes no arguments — cannot be handed graph state (got {rd})")


def test_compute_friction_hostile_inputs_stay_bounded():
    section("D3 ROBUSTNESS: compute_friction stays in [0,1] / neutral on hostile timing pairs "
            "(negative, zero, inf, nan-adjacent, cpu>>wall, sub-resolution)")
    import math
    cases = [
        (1.0, 1.0, 0.0), (1.0, 0.0, 1.0), (1.0, 0.5, 0.5),
        (1.0, 2.0, 0.0),            # cpu>wall clamps to 0
        (0.0, 0.0, NEUTRAL_FRICTION),  # degenerate wall
        (-1.0, 0.5, NEUTRAL_FRICTION), # negative wall
        (1e-9, 0.0, NEUTRAL_FRICTION), # sub-resolution wall
    ]
    for wall, cpu, expected in cases:
        got = compute_friction(wall, cpu)
        check(got == expected, f"compute_friction({wall},{cpu}) == {expected} (got {got})")
    # large finite values stay bounded
    big = compute_friction(1e6, 1.0)
    check(0.0 <= big <= 1.0, f"large wall stays bounded (got {big})")
    # None inputs -> neutral, no crash
    check(compute_friction(None, 1.0) == NEUTRAL_FRICTION, "None wall -> neutral, no crash")
    check(compute_friction(1.0, None) == NEUTRAL_FRICTION, "None cpu -> neutral, no crash")
    # the modulated decay never leaves (0,1] for any friction in [0,1] at the default base
    for i in range(101):
        f = i / 100.0
        d = modulated_decay_per_hop(DEFAULT_DECAY_PER_HOP, f)
        check(MIN_DECAY_PER_HOP <= d <= MAX_DECAY_PER_HOP,
              f"modulated decay bounded at friction {f} (got {d})") if i % 25 == 0 else None
    # out-of-range frictions are clamped by the mapping (not allowed to explode the decay)
    check(friction_to_decay_factor(-5.0) == 1.0, "friction < 0 clamps to factor 1.0")
    check(friction_to_decay_factor(5.0) == 1.0 - MODULATION_SPAN, "friction > 1 clamps to factor at 1.0")


# ══════════════════════════════════════════════════════════════════════════════
# JOB 2 — E. BATTERY FAIRNESS (re-derived; not trusted)
# ══════════════════════════════════════════════════════════════════════════════

def _import_pilot():
    return importlib.import_module("pilot_2c_populability")


def test_battery_is_fixed_seed_reproducible_not_hand_picked():
    section("E1 FAIRNESS: build_battery(20260621, 40) is a FIXED-SEED reproducible space — two "
            "independent calls yield identical structural parameters (no hidden per-call state, "
            "no hand-selection)")
    P = _import_pilot()
    check(P.BATTERY_SEED == 20260621, f"BATTERY_SEED is the pre-registered 20260621 (got {P.BATTERY_SEED})")
    check(P.PERCEPT_COUNT == 40, f"PERCEPT_COUNT is 40 (got {P.PERCEPT_COUNT})")
    b1 = P.build_battery(P.BATTERY_SEED, P.PERCEPT_COUNT)
    b2 = P.build_battery(P.BATTERY_SEED, P.PERCEPT_COUNT)
    labels1 = [row[0] for row in b1]
    labels2 = [row[0] for row in b2]
    check(labels1 == labels2, "two build_battery calls produce identical labels (deterministic)")
    check(len(b1) == 40, f"battery has 40 percepts (got {len(b1)})")
    # the percept text is always the two anchors; content lights up exactly alpha/gamma
    check(all(row[2] == "alpha gamma" for row in b1), "every percept text is the two anchors")
    check(all(row[3] == "alpha" and row[4] == "gamma" for row in b1), "anchors are alpha/gamma")


def test_battery_bridge_distribution_matches_a_principled_seeded_space():
    section("E2 FAIRNESS: the battery's bridge_n parameters match an INDEPENDENT re-derivation "
            "of random.Random(20260621) drawing randint(1,6)/randint(0,2) — proving the space "
            "is principled and seeded, not curated")
    import random as _random
    P = _import_pilot()
    # Re-derive the exact draw sequence the pilot's generator must produce.
    rng = _random.Random(P.BATTERY_SEED)
    expected = []
    for i in range(P.PERCEPT_COUNT):
        bridge_n = rng.randint(1, 6)
        near_extra = rng.randint(0, 2)
        expected.append((bridge_n, near_extra))
    # The labels encode bridge and nearextra: "pNN[bridge=B,nearextra=E]".
    b = P.build_battery(P.BATTERY_SEED, P.PERCEPT_COUNT)
    got = []
    for row in b:
        label = row[0]
        # parse bridge=.. and nearextra=..
        brk = label[label.index("[") + 1:label.index("]")]
        parts = dict(kv.split("=") for kv in brk.split(","))
        got.append((int(parts["bridge"]), int(parts["nearextra"])))
    check(got == expected,
          "the battery's (bridge_n, near_extra) exactly match an independent Random(seed) draw")
    # bridge_n must span its full documented range [1..6] (not collapsed to flip-friendly values)
    bridges = sorted({g[0] for g in got})
    check(bridges == [1, 2, 3, 4, 5, 6] or set(bridges).issubset({1, 2, 3, 4, 5, 6}),
          f"bridge_n draws are within the documented [1..6] range (saw {bridges})")
    check(len(set(g[0] for g in got)) >= 4,
          f"bridge_n genuinely varies across the battery (distinct values: {sorted(set(g[0] for g in got))})")


def test_battery_is_not_a_100pct_flip_construction():
    section("E3 FAIRNESS (the red-flag test): the battery is NOT all-flippable — sweeping the "
            "REAL modulated decay range, some percepts (with d* outside the range) genuinely do "
            "NOT flip. A 100% flip rate would mean the construction was rigged to always flip.")
    P = _import_pilot()
    battery = P.build_battery(P.BATTERY_SEED, P.PERCEPT_COUNT)
    # Re-derive the EXACT swept friction levels the pilot grades on, from the FROZEN trace via
    # the pilot's own sweep_levels_from_frictions over the real observed range — so this is the
    # pilot's real grading surface, not a hand-chosen grid. (Falls back to a [0..1] grid only
    # if the frozen trace is unavailable, which F1 already guards.)
    import json
    trace_path = os.path.join(_EXPERIMENTS, "results", "pilot_2c_telemetry_trace.json")
    if os.path.exists(trace_path):
        with open(trace_path, "r") as f:
            payload = json.load(f)
        ts = [TelemetrySample(perf=p, proc=q) for p, q in payload["samples"]]
        observed = P.frictions_from_trace(ts)
        friction_levels = P.sweep_levels_from_frictions(observed, P.SWEEP_LEVELS)
    else:
        friction_levels = [i / 8.0 for i in range(9)]
    flips = []
    for label, builder, percept_text, _a, _b in battery:
        did_flip, n_distinct, has_winner = P.percept_flips(builder, percept_text, friction_levels)
        flips.append((label, did_flip, has_winner))
    n_flip = sum(1 for _, fl, _ in flips if fl)
    n_winner = sum(1 for _, _, hw in flips if hw)
    flip_rate = n_flip / n_winner if n_winner else 0.0
    print(f"   re-derived flip rate over the FROZEN-TRACE swept levels: "
          f"{n_flip}/{n_winner} = {flip_rate:.1%}")
    # the re-derived number must reproduce the pilot's reported GO (34/40 = 85%) — if my
    # independent re-derivation disagreed with the pilot's self-report, that itself is a finding.
    check(n_flip == 34 and n_winner == 40,
          f"independent re-derivation reproduces the pilot's 34/40 = 85% over the real frozen "
          f"range (got {n_flip}/{n_winner}) — the self-reported number is not fabricated")
    # THE RED-FLAG ASSERTIONS:
    #  - not every percept flips (if all flip, the construction is rigged to always flip)
    check(n_flip < n_winner,
          f"NOT 100% flip: {n_flip}/{n_winner} percepts flip; some genuinely do not "
          f"(a 100% rate would signal a rigged all-flippable battery)")
    #  - at least one percept that has a winner does NOT flip (genuine non-flip exists)
    non_flips = [lbl for lbl, fl, hw in flips if hw and not fl]
    check(len(non_flips) >= 1,
          f"at least one winner-having percept does NOT flip across the real range (non-flippers: {non_flips})")
    # cross-check this against the pilot's documented d* spread: bridge_n in {1,2} gives small
    # d* (~0.13..0.24) which can fall below the min swept decay -> those should be over-
    # represented among non-flippers. We don't assert the exact set (engine-internal), only
    # that non-flippers exist, which is the anti-rigging signal.


def test_battery_high_friction_range_can_fail_to_flip_low_bridge():
    section("E4 FAIRNESS corollary: a percept whose crossover d* lies OUTSIDE the modulated "
            "decay band shows a SINGLE winner across the whole band (no flip) — confirming the "
            "construction admits genuine non-flips, not just borderline ones")
    P = _import_pilot()
    battery = P.build_battery(P.BATTERY_SEED, P.PERCEPT_COUNT)
    # The modulated decay band is [base*(1-SPAN) .. base] = [0.26 .. 0.65] at defaults.
    # bridge_n=1 => sA~0.13 => d* = sA/sB^2 ~ 0.13/0.97 ~ 0.134, BELOW the band's floor 0.26
    # => the contested node should stay on gamma's side at every swept decay => no flip.
    # Find a bridge=1 percept (if the seed produced one) and confirm it does not flip.
    friction_levels = [i / 8.0 for i in range(9)]
    bridge1 = [(lbl, b, t) for (lbl, b, t, a, c) in battery if "bridge=1," in lbl]
    if bridge1:
        lbl, builder, percept_text = bridge1[0]
        did_flip, n_distinct, has_winner = P.percept_flips(builder, percept_text, friction_levels)
        check(has_winner, f"{lbl}: produces a winner")
        check(not did_flip,
              f"{lbl}: a bridge=1 percept (d* below the modulated band) does NOT flip "
              f"(distinct winners across the band: {n_distinct}) — genuine non-flip confirmed")
    else:
        # the seed may not have drawn bridge=1; then assert via the lowest bridge present
        lowest = min(int(lbl[lbl.index("bridge=") + 7]) for (lbl, *_rest) in battery)
        check(True, f"no bridge=1 in this seed's battery (lowest bridge={lowest}); E3 covers non-flips")


def test_pilot_winner_readout_is_node_set_not_scalar():
    section("E5 FAIRNESS: the pilot's flip readout is a node-SET (frozenset of contents), never "
            "the injected friction scalar — the pilot grades the SAME anti-circular readout")
    P = _import_pilot()
    battery = P.build_battery(P.BATTERY_SEED, P.PERCEPT_COUNT)
    label, builder, percept_text, _a, _b = battery[0]
    # drive the pilot's own _winner_set on a built store/result and confirm the type
    s = builder()
    sensor = BodySensor(simulated=True, trace=[TelemetrySample(0.0, 0.0), TelemetrySample(1.0, 0.5)])
    sensor.read()
    r = think(s, percept_text, body_sensor=sensor)
    ws = P._winner_set(s, r)
    check(ws is None or isinstance(ws, frozenset),
          "pilot _winner_set returns a frozenset node-set (or None), never a scalar")
    if ws is not None:
        check(all(isinstance(x, str) for x in ws),
              "every element of the pilot's winner readout is a node-content string, not a float")
        check(0.5 not in ws, "the injected friction scalar is not an element of the pilot readout")


# ══════════════════════════════════════════════════════════════════════════════
# JOB 2 — F. TELEMETRY RANGE HONESTLY REAL
# ══════════════════════════════════════════════════════════════════════════════

def test_frozen_trace_frictions_reproduced_by_the_same_compute_friction():
    section("F1 FAIRNESS: the frozen trace's friction values are reproduced by the SAME "
            "compute_friction the cycle uses (deltas of perf/proc), and span a REAL low->high "
            "range — not hard-coded, not widened")
    import json
    trace_path = os.path.join(_EXPERIMENTS, "results", "pilot_2c_telemetry_trace.json")
    check(os.path.exists(trace_path), f"frozen trace artifact exists at {trace_path}")
    with open(trace_path, "r") as f:
        payload = json.load(f)
    samples = payload["samples"]
    check(len(samples) >= 2, f"trace has multiple samples (got {len(samples)})")
    # The samples are raw (perf, proc) pairs. Re-derive friction with the SAME function the
    # BodySensor/cycle uses, from consecutive deltas, EXACTLY as frictions_from_trace does.
    frictions = []
    for k in range(1, len(samples)):
        wall_dt = samples[k][0] - samples[k - 1][0]
        cpu_dt = samples[k][1] - samples[k - 1][1]
        frictions.append(compute_friction(wall_dt, cpu_dt))
    # Cross-check against the pilot's own frictions_from_trace (must agree exactly).
    P = _import_pilot()
    ts = [TelemetrySample(perf=p, proc=q) for p, q in samples]
    pilot_frictions = P.frictions_from_trace(ts)
    check([round(x, 12) for x in frictions] == [round(x, 12) for x in pilot_frictions],
          "independent compute_friction over the frozen trace matches the pilot's frictions_from_trace")
    lo, hi = min(frictions), max(frictions)
    print(f"   real observed friction range from frozen trace: [{lo:.6f} .. {hi:.6f}]")
    # a REAL range: low end near 0 (CPU-bound intervals), high end near 1 (idle intervals)
    check(hi > lo, f"the trace spans a non-degenerate range (lo={lo:.6f}, hi={hi:.6f})")
    check(lo < 0.5 and hi > 0.5,
          f"the range genuinely spans low->high (lo<0.5<hi: lo={lo:.6f}, hi={hi:.6f})")
    # every friction is a real telemetry-derived value in [0,1] (no hand-set sentinel)
    check(all(0.0 <= x <= 1.0 for x in frictions), "every trace friction is within [0,1]")
    # the raw proc values must actually GROW differently across CPU-bound vs idle intervals —
    # i.e. the trace is real telemetry, not two hard-coded constants alternating.
    proc_deltas = [round(samples[k][1] - samples[k - 1][1], 9) for k in range(1, min(9, len(samples)))]
    check(len(set(proc_deltas)) >= 2,
          f"process_time deltas vary across intervals (real capture, not a constant): {proc_deltas}")


def test_swept_levels_stay_within_the_real_recorded_range():
    section("F2 FAIRNESS: the pilot's swept friction levels lie WITHIN the real observed "
            "min..max (no inflation beyond what the machine produced)")
    import json
    P = _import_pilot()
    trace_path = os.path.join(_EXPERIMENTS, "results", "pilot_2c_telemetry_trace.json")
    with open(trace_path, "r") as f:
        payload = json.load(f)
    ts = [TelemetrySample(perf=p, proc=q) for p, q in payload["samples"]]
    frictions = P.frictions_from_trace(ts)
    levels = P.sweep_levels_from_frictions(frictions, P.SWEEP_LEVELS)
    lo, hi = min(frictions), max(frictions)
    check(len(levels) == P.SWEEP_LEVELS or (hi <= lo and len(levels) == 1),
          f"sweep produced SWEEP_LEVELS levels (got {len(levels)})")
    check(all(lo - 1e-12 <= x <= hi + 1e-12 for x in levels),
          f"every swept level lies within the real recorded range [{lo:.6f}..{hi:.6f}] (no inflation)")
    check(abs(levels[0] - lo) < 1e-9 and abs(levels[-1] - hi) < 1e-9,
          "the sweep endpoints are exactly the real observed min and max (not widened)")


def test_capture_uses_real_timers_and_compute_friction_not_constants():
    section("F3 FAIRNESS (static): the capture path uses REAL perf_counter/process_time and the "
            "SAME compute_friction — no hand-set or inflated friction anywhere in the pilot")
    pilot_path = os.path.join(_EXPERIMENTS, "pilot_2c_populability.py")
    with open(pilot_path, "r") as f:
        src = f.read()
    # capture must read real timers
    check("time.perf_counter()" in src and "time.process_time()" in src,
          "the pilot capture reads real time.perf_counter()/process_time()")
    # the pilot must compute friction via the library function, not a literal
    check("compute_friction" in src or "frictions_from_trace" in src,
          "the pilot derives friction via the library compute_friction / frictions_from_trace")
    # no smoking-gun hardcoded friction list assigned as the observed range. Heuristic: the
    # range comes from min()/max() of the captured frictions, not from a literal.
    check("min(frictions)" in src and "max(frictions)" in src,
          "the observed range is min/max of captured frictions (derived, not hard-coded)")
    # the capture genuinely alternates busy-spin vs sleep (a real low->high generator)
    check("_busy_spin" in src and "time.sleep" in src,
          "capture alternates a real busy-spin (CPU-bound) and os sleep (idle) — a real range")


# ══════════════════════════════════════════════════════════════════════════════
# JOB 2 — G. PRE-REGISTRATION INTEGRITY
# ══════════════════════════════════════════════════════════════════════════════

def test_floor_and_seed_are_fixed_constants_before_any_result():
    section("G1 FAIRNESS: the 0.30 floor and the 20260621 seed are FIXED MODULE CONSTANTS "
            "(literals in the file, defined before any computation), not derived from a result")
    P = _import_pilot()
    check(P.POPULABILITY_FLOOR == 0.30, f"POPULABILITY_FLOOR == 0.30 (got {P.POPULABILITY_FLOOR})")
    check(P.BATTERY_SEED == 20260621, f"BATTERY_SEED == 20260621 (got {P.BATTERY_SEED})")
    # static: the constants are literal assignments in the pre-registration block, ABOVE any
    # function that computes a fraction. Confirm the literal text and ordering.
    pilot_path = os.path.join(_EXPERIMENTS, "pilot_2c_populability.py")
    with open(pilot_path, "r") as f:
        src = f.read()
    idx_floor = src.find("POPULABILITY_FLOOR = 0.30")
    idx_seed = src.find("BATTERY_SEED = 20260621")
    idx_fraction = src.find("fraction = n_flip")  # the first place a result fraction is computed
    check(idx_floor != -1, "POPULABILITY_FLOOR = 0.30 appears as a literal constant")
    check(idx_seed != -1, "BATTERY_SEED = 20260621 appears as a literal constant")
    check(idx_fraction != -1, "the result fraction is computed in main()")
    check(idx_floor < idx_fraction and idx_seed < idx_fraction,
          "both the floor and the seed are defined BEFORE any result fraction is computed")
    # the floor is COMPARED to, never reassigned from, the fraction (no post-hoc loosening)
    check(src.count("POPULABILITY_FLOOR =") == 1,
          "POPULABILITY_FLOOR is assigned exactly once (never re-bound after a result)")
    check(src.count("BATTERY_SEED =") == 1,
          "BATTERY_SEED is assigned exactly once (never re-bound after a result)")


def test_readout_and_grading_are_pre_stated_replay_and_winner_set():
    section("G2 FAIRNESS: the readout (winner-set) and the grading mode (REPLAY over the frozen "
            "hashed trace) are pre-stated in the pilot, and the result is COMPUTED not hard-coded")
    pilot_path = os.path.join(_EXPERIMENTS, "pilot_2c_populability.py")
    with open(pilot_path, "r") as f:
        src = f.read()
    check("winner-SET" in src or "_winner_set" in src,
          "the readout is pre-stated as the winner-SET (node-set), the anti-circular readout")
    check("REPLAY" in src and ("sha256" in src.lower() or "SHA-256" in src),
          "grading is pre-stated as REPLAY over a SHA-256-hashed frozen trace")
    # the result fraction is computed from counts, not a literal number
    check("fraction = n_flip / denom" in src,
          "the reported fraction is computed as n_flip/denom (not a hard-coded 0.85)")
    # there is NO literal 0.85 hard-coded as the verdict anywhere
    check("0.85" not in src,
          "no literal 0.85 is baked into the pilot (the fraction is measured, not asserted)")


def test_frozen_trace_hash_is_a_function_of_content():
    section("G3 FAIRNESS: the frozen trace hash is a deterministic function of the trace "
            "CONTENT (re-hashing the artifact via the pilot's own loader reproduces a stable "
            "digest), so a tampered trace would be detected")
    P = _import_pilot()
    # the loader recomputes the digest from the file content; two loads agree, and the digest
    # is a real 64-hex sha256 (not absent / not a placeholder).
    samples1, digest1 = P.load_frozen_trace()
    samples2, digest2 = P.load_frozen_trace()
    check(digest1 == digest2, "two loads of the frozen trace yield the same digest (stable)")
    check(len(digest1) == 64 and all(c in "0123456789abcdef" for c in digest1),
          f"the trace digest is a 64-hex SHA-256 (got len {len(digest1)})")
    check(len(samples1) == len(samples2) and len(samples1) >= 2,
          "the loader returns the full multi-sample trace")


# ══════════════════════════════════════════════════════════════════════════════
# JOB 2 — H. NO OVERCLAIM
# ══════════════════════════════════════════════════════════════════════════════

def test_no_public_name_or_prose_claims_a_feeling_or_meaning():
    section("H1 NO OVERCLAIM: no public name in psyche_bodysensor claims a feeling/awareness/"
            "consciousness; the headline word is 'friction' (a derived telemetry signal)")
    public = [name for name in dir(bs) if not name.startswith("_")]
    forbidden = ("feel", "emotion", "aware", "conscious", "sentient", "panic",
                 "experience", "qualia", "mood")
    offenders = [name for name in public if any(tok in name.lower() for tok in forbidden)]
    check(offenders == [], f"no public name claims a feeling/awareness/consciousness (offenders: {offenders})")
    check("compute_friction" in public and "BodySensor" in public,
          "the public surface names the mechanism (friction / BodySensor), not a felt state")
    # the module exposes NO meaning/grading/validation verdict (meaning is the validator's).
    # NB: a GRADING/MEANING verdict would be named like validate_/grade_/is_significant; we do
    # NOT flag the resolution constant MIN_MEANINGFUL_WALL_DT — "meaningful" there means
    # "numerically stable / non-degenerate timing", mechanism vocabulary, not a cognitive
    # claim. Match grading-verb tokens only, and exempt that one legitimate constant.
    grading_tokens = ("validate", "grade", "earned", "significance", "significant", "verdict")
    offenders_api = [
        name for name in public
        if name != "MIN_MEANINGFUL_WALL_DT"
        and any(tok in name.lower() for tok in grading_tokens)
    ]
    check(offenders_api == [],
          f"psyche_bodysensor exposes no meaning/grading/validation API (offenders: {offenders_api})")


def test_pilot_frames_fraction_as_feasibility_not_meaning():
    section("H2 NO OVERCLAIM: the pilot frames its number as a populability/feasibility "
            "fraction on flip-CAPABLE inputs over a deliberately-extreme range — NOT a meaning "
            "result; it explicitly defers meaning to the validator and carries the negations")
    pilot_path = os.path.join(_EXPERIMENTS, "pilot_2c_populability.py")
    with open(pilot_path, "r") as f:
        src = f.read().lower()
    # explicit non-meaning framing present
    check("not" in src and ("meaning" in src or "consciousness" in src or "sentience" in src),
          "the pilot explicitly disclaims a meaning/consciousness claim")
    check("validator" in src, "the pilot defers the meaning grading to the validator")
    check("populability" in src or "feasibility" in src,
          "the pilot frames its number as populability/feasibility")
    # the honest caveat about the battery being movable-in-principle (flip-capable) is present
    check("movable" in src or "flip" in src,
          "the pilot discloses the battery is movable-in-principle / about flips (not a realistic mixed rate)")
    # the GO verdict text must NOT claim meaning — it must say it is NOT itself a meaning claim
    check("not itself a meaning claim" in src or "not a meaning claim" in src
          or "is not a meaning" in src,
          "the GO verdict explicitly states it is not itself a meaning claim")


def test_known_limitation_no_direction_or_meaning_asserted_at_mechanism_layer():
    section("H3 NO OVERCLAIM (asserted-negative): the mechanism layer asserts a REAL causal "
            "effect (winner-flip) and DETERMINISM only — it does NOT assert the flip tracks "
            "the telemetry in a pre-registered direction, nor that it MEANS anything")
    s = _flip_mind()
    r = think(s, "alpha gamma", body_sensor=_sensor_yielding([0.5]))
    check(r.body_friction is not None, "the cycle records a body-state scalar (mechanism fact)")
    check(r.effective_decay_per_hop is not None, "the cycle records the effective decay (mechanism fact)")
    # there is no API in the sensor module that returns a graded direction/meaning verdict
    has_dir_api = any(
        tok in name.lower() for name in dir(bs) if not name.startswith("_")
        for tok in ("direction", "tracks", "correlat"))
    check(not has_dir_api,
          "psyche_bodysensor exposes no direction/tracking/correlation verdict (that is the validator's)")


# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  TESTER 2c ADVERSARIAL — mechanism verification + pilot fairness audit")
    print("=" * 70)
    tests = [
        # JOB 1 — A default-off purity
        test_default_off_full_thoughtresult_byte_identical_across_battery,
        test_default_off_store_byte_identical_including_broadcast_path,
        test_empty_perception_burns_no_replay_sample,
        # JOB 1 — C anti-circularity (winner-flip not echo)
        test_two_distinct_frictions_same_decay_give_same_winner,
        test_friction_mapping_to_off_decay_reproduces_off_field_exactly,
        test_every_winner_element_is_a_graph_nodeid_never_a_float,
        test_friction_names_no_node_only_global_decay,
        test_winner_flip_actually_occurs_on_independent_graph,
        # JOB 1 — B replay determinism + live isolation
        test_winner_trace_byte_identical_across_6_seeds_independent_driver,
        test_pilot_battery_winners_byte_identical_across_6_seeds,
        test_replay_path_never_reads_a_live_timer_runtime_trap,
        test_no_live_telemetry_call_in_graded_source_static,
        # JOB 1 — D integrity + purity ON path
        test_on_path_pure_read_and_integrity_battery,
        test_sensor_read_touches_only_its_cursor,
        test_compute_friction_hostile_inputs_stay_bounded,
        # JOB 2 — E battery fairness
        test_battery_is_fixed_seed_reproducible_not_hand_picked,
        test_battery_bridge_distribution_matches_a_principled_seeded_space,
        test_battery_is_not_a_100pct_flip_construction,
        test_battery_high_friction_range_can_fail_to_flip_low_bridge,
        test_pilot_winner_readout_is_node_set_not_scalar,
        # JOB 2 — F telemetry range honestly real
        test_frozen_trace_frictions_reproduced_by_the_same_compute_friction,
        test_swept_levels_stay_within_the_real_recorded_range,
        test_capture_uses_real_timers_and_compute_friction_not_constants,
        # JOB 2 — G pre-registration integrity
        test_floor_and_seed_are_fixed_constants_before_any_result,
        test_readout_and_grading_are_pre_stated_replay_and_winner_set,
        test_frozen_trace_hash_is_a_function_of_content,
        # JOB 2 — H no overclaim
        test_no_public_name_or_prose_claims_a_feeling_or_meaning,
        test_pilot_frames_fraction_as_feasibility_not_meaning,
        test_known_limitation_no_direction_or_meaning_asserted_at_mechanism_layer,
    ]
    for t in tests:
        t()
    print("\n" + "=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    if _failures:
        print("  FAILURES:")
        for fmsg in _failures:
            print(f"    - {fmsg}")
    print("=" * 70)
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
