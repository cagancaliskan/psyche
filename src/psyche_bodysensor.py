"""
Psyche — BodySensor  (step 2c: a telemetry-derived body-state signal at the boundary)

WHAT THIS IS (and, with equal weight, what it is NOT):

This module computes a single scalar "body-state" variable — a FRICTION number in [0,1]
— from real machine TELEMETRY (the wall-clock vs CPU-clock timing pair), and exposes it
through a two-mode boundary object that mirrors the substrate's proven `Clock(simulated=
...)` pattern. It is the sensor half of 2c; the modulation HOOK that lets this number
color the cognitive cycle lives in psyche_perceive.think(..., body_sensor=...) and is
DEFAULT-OFF.

HONEST FRAMING (hard, non-negotiable — CLAUDE.md rules 1-2; SPEC-2c §0.1 / §2.1):

  - The friction number is a DERIVED SIGNAL computed from a timing measurement. It is NOT
    a feeling, an emotion, interoception in the human sense, awareness, "the body," or
    consciousness. The design doc's evocative language ("the brain feels its body,"
    "panic," "muscular tension") is VISION, quarantined to SPEC-2c §0.1, and is never a
    claim this code makes.
  - "FRICTION is high" means, precisely and only: "the wall-clock elapsed time of the
    measured interval was large relative to the CPU time the process actually got" — a
    proxy for scheduling/contention pressure the process suffered. It does NOT mean the
    system experiences effort, stress, or anything at all.
  - The mechanism corresponds, at most, to the NEUROMODULATORY-GAIN shadow: a global
    state scalar that can bias a global spreading parameter. It is NOT a model of emotion,
    of the insula, or of feeling. Passing this module's tests proves the SIGNAL is
    computed correctly and DETERMINISTICALLY in replay; it proves NOTHING about meaning.
    Whether the signal MEANS anything (causally modulates selection, tracks the telemetry)
    is the validator's call against the frozen trace, never asserted here.

THE GENUINELY-TELEMETRY-DERIVED CONTRACT (SPEC-2c §1.1 / decision 1; the soft-Wall-1 guard):

  - The friction value is computed ONLY from the telemetry pair (perf_counter delta,
    process_time delta). It is NEVER re-derived from graph/substrate state (e.g. "number
    of active nodes" wearing a telemetry costume would be a soft re-entry of 1e's readback
    wall). This is structural here: BodySensor takes NO store, NO field, NO graph in its
    constructor or read path — it CANNOT read the substrate, so it cannot re-derive
    friction from it. An asserted-negative test pins this.

THE TWO-MODE DETERMINISM DESIGN (SPEC-2c §3.2, BINDING — mirrors Clock(simulated=...)):

  - LIVE mode (boundary only; the single point of non-determinism; production use):
    reads real `time.perf_counter()` and `time.process_time()` at the moment `read()` is
    called and derives friction from the gap between successive reads. Because real
    telemetry differs on every read and every machine, LIVE mode is intrinsically
    non-deterministic and is EXPLICITLY NOT part of the deterministic test surface. A
    separate, non-graded live SMOKE check (in the pilot/live-mode tooling, not the
    canonical runner) may exercise it; it is never a graded result and never counts toward
    the substrate determinism bar.

  - REPLAY mode (load-bearing; the entire tester-grade mechanism surface): reads from a
    FROZEN, recorded sequence of telemetry samples — a list of (perf_counter, process_time)
    pairs captured once from real live runs and then frozen. Identical replayed input
    yields BYTE-IDENTICAL friction across separate processes and across PYTHONHASHSEED
    values, because the only non-deterministic input has been replaced by a frozen trace.
    ALL mechanism tests run here.

  This generalizes the substrate's already-proven Clock pattern: isolate the single live
  read behind one boundary object, and grade the science on the frozen replay.

SECONDARY SIGNALS (SPEC-2c decision 1 — NOT load-bearing for the headline):

  - os.getloadavg() (Unix-only) and resource.getrusage(...).ru_maxrss (Unix-only) are
    available as SECONDARY robustness signals via explicit boundary helpers, each from its
    NAMED OS call only and never graph-re-derived. They are NOT used to compute the
    headline friction (which is the portable, stdlib-only timing pair), are not on the
    deterministic test surface, and nothing downstream depends on them. They exist only so
    a later robustness re-run can report alongside the headline.

Pure Python standard library. The sensor reads telemetry (live mode) or a frozen trace
(replay mode) and graph-INDEPENDENT state only; it mutates no substrate.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Friction mapping parameters — FIRST-PASS, UNCALIBRATED (documented design constants)
# ─────────────────────────────────────────────────────────────────────────────
# These shape how a raw timing gap becomes a normalized friction scalar in [0,1]. They
# are uncalibrated design constants (the same stance as DEFAULT_DECAY_PER_HOP and the 1c
# proximity fraction): they produce the right QUALITATIVE behavior (no contention -> low
# friction; wall-time far exceeding CPU-time -> high friction), and nothing downstream may
# depend on their magnitudes — only on the qualitative monotonicity. They are NOT tuned
# against any external/cognitive outcome (doing so would be the forbidden move).
#
# The headline definition (decision 1): friction is the fraction of the measured wall-time
# interval during which the process was NOT actually running on CPU — i.e. the "stall
# fraction" wall_dt > cpu_dt implies. This is a pure, bounded, monotone function of the
# timing pair: 0.0 when the process ran flat-out (cpu_dt == wall_dt), approaching 1.0 as
# the process is increasingly starved (cpu_dt << wall_dt). It needs no magic scale.

# Below this wall-clock interval, a sample is too short to carry a meaningful CPU/wall
# ratio (timer quantization dominates) and friction is reported as the neutral baseline.
MIN_MEANINGFUL_WALL_DT = 1e-7   # 100 ns; below the resolution where the ratio is stable

# The neutral baseline friction (used for degenerate/too-short samples and the very first
# LIVE read, which has no predecessor to diff against). Chosen as 0.0 = "no measured
# stall," the identity end of the friction range.
NEUTRAL_FRICTION = 0.0


def compute_friction(wall_dt: float, cpu_dt: float) -> float:
    """The headline body-state mapping (decision 1): turn one timing-pair delta into a
    friction scalar in [0,1]. PURE function of the two deltas — reads NO graph state.

    friction = clamp( 1 - cpu_dt / wall_dt , 0, 1 )

    Interpretation (mechanism, not meaning): the fraction of the measured wall-clock
    interval the process did NOT spend running on CPU — a proxy for scheduling/contention
    pressure the process actually suffered. cpu_dt == wall_dt (ran flat-out) -> 0.0;
    cpu_dt << wall_dt (heavily starved/contended) -> approaches 1.0. cpu_dt > wall_dt can
    occur from timer skew or multi-threaded CPU accounting; it is clamped to 0.0 (no
    measured stall). Degenerate or sub-resolution wall_dt -> NEUTRAL_FRICTION.

    This is genuinely telemetry-derived: both inputs come from time.perf_counter() /
    time.process_time() reads at the boundary (live) or a frozen recording of them
    (replay). The value is NEVER computed from substrate/graph quantities.
    """
    if wall_dt is None or cpu_dt is None:
        return NEUTRAL_FRICTION
    if wall_dt < MIN_MEANINGFUL_WALL_DT:
        return NEUTRAL_FRICTION
    ratio = cpu_dt / wall_dt
    friction = 1.0 - ratio
    if friction < 0.0:
        return 0.0
    if friction > 1.0:
        return 1.0
    return friction


# ─────────────────────────────────────────────────────────────────────────────
# The friction -> decay_per_hop modulation mapping (the (C-INJECT-UPSTREAM) gain)
# ─────────────────────────────────────────────────────────────────────────────
# SPEC-2c decision 2: the body-state friction modulates `decay_per_hop`, the upstream,
# node-naming-free global spreading parameter in spread_activation. This is the ONLY
# place the body-state number touches the cycle; it names NO node and NO coalition (the
# (C-INJECT-UPSTREAM) constraint).
#
# ENGINE SEMANTICS (read from src/psyche_activation.py, line: `transmitted = outgoing *
# road.strength * decay_per_hop`): `decay_per_hop` is a per-hop TRANSMISSION MULTIPLIER.
# A LOWER value attenuates activation faster per hop -> the spread stays MORE LOCAL; a
# HIGHER value lets activation reach FARTHER. (NB: this is the engine's actual semantics.
# SPEC-2c's prose at §4 / decision 2 glosses `decay_per_hop` as a "penalty" — "higher
# decay -> more local" — which is the OPPOSITE labeling. The cognitively-stated INTENT in
# the same sentences is unambiguous: "higher friction => activation stays more local =>
# near, tightly-bound coalitions favored over far, diffuse ones." This mapping implements
# that INTENT against the engine's real semantics: higher friction -> LOWER decay_per_hop
# -> more local. The exact monotone DIRECTION is the validator's to fix and grade in its
# pre-registration; the builder's pilot is direction-AGNOSTIC, so this choice does not
# affect the pilot's pass/fail. This labeling conflict is surfaced, not silently resolved.)
#
# MODULATION_SPAN is an uncalibrated documented design constant (the modulation depth): at
# friction 0 the factor is 1.0 (decay = base); at friction 1 the factor is (1 -
# MODULATION_SPAN). It is NOT tuned to any cognitive outcome. The result is clamped into a
# strict, bounded sub-interval of (0, 1] so the modulated parameter never leaves the
# engine's valid range and the modulation is a bounded, restorable parameter change.
MODULATION_SPAN = 0.6   # at full friction, decay_per_hop is scaled down to 40% of base
MIN_DECAY_PER_HOP = 1e-3  # floor so the parameter never reaches 0 (would kill all spread)
MAX_DECAY_PER_HOP = 1.0   # the engine's natural ceiling for a per-hop multiplier


def friction_to_decay_factor(friction: float) -> float:
    """Map a friction scalar in [0,1] to a multiplicative factor on `decay_per_hop`.

    factor = 1 - MODULATION_SPAN * friction

    Monotone DECREASING in friction (higher friction -> smaller factor -> lower decay ->
    activation stays more local; SPEC-2c §4 intent). At friction 0 the factor is exactly
    1.0 (identity), at friction 1 it is (1 - MODULATION_SPAN). Pure function; reads no
    graph state. The factor itself is in [1 - MODULATION_SPAN, 1.0] for friction in [0,1].
    """
    f = friction
    if f < 0.0:
        f = 0.0
    elif f > 1.0:
        f = 1.0
    return 1.0 - MODULATION_SPAN * f


def modulated_decay_per_hop(base_decay_per_hop: float, friction: float) -> float:
    """Apply the friction modulation to a base `decay_per_hop`, returning a bounded value
    in (0, 1]. Pure function of (base, friction) — reads NO graph state.

    This is the single value the modulation hook injects into the spread. It is a bounded,
    restorable parameter change (the base is unchanged; this returns a new value), NOT
    hidden state and NOT a node-naming command.
    """
    value = base_decay_per_hop * friction_to_decay_factor(friction)
    if value < MIN_DECAY_PER_HOP:
        return MIN_DECAY_PER_HOP
    if value > MAX_DECAY_PER_HOP:
        return MAX_DECAY_PER_HOP
    return value


@dataclass(frozen=True)
class TelemetrySample:
    """One frozen telemetry reading: the raw timing pair captured at one boundary read.

    perf : a time.perf_counter() value (wall-clock seconds, monotone, arbitrary origin).
    proc : the time.process_time() value (CPU seconds for this process) captured at the
           SAME instant.

    A frozen REPLAY trace is a sequence of these. Friction for sample k (k >= 1) is
    computed from the DELTAS (perf_k - perf_{k-1}, proc_k - proc_{k-1}) so it measures the
    contention over the interval between two consecutive boundary reads — exactly what the
    live path measures. The first sample (k == 0) has no predecessor and yields the
    neutral baseline.
    """
    perf: float
    proc: float


class BodySensor:
    """A two-mode boundary object that emits a telemetry-derived friction scalar in [0,1],
    mirroring the substrate's Clock(simulated=...) live/replay split.

    LIVE mode (production; the single non-deterministic boundary):
        BodySensor()                         # simulated=False
        b.read()  -> friction from real perf_counter()/process_time() deltas.
      The FIRST read has no predecessor, so it primes the baseline and returns
      NEUTRAL_FRICTION; each subsequent read returns friction over the interval since the
      previous read. Live mode is NOT on the deterministic test surface.

    REPLAY mode (the entire tester-grade mechanism surface; deterministic):
        BodySensor(simulated=True, trace=[TelemetrySample(perf, proc), ...])
        b.read()  -> friction from the FROZEN trace, one sample per call, in order.
      Replay is byte-identical across processes/seeds because the only non-deterministic
      input (the real timer) has been replaced by the frozen trace.

    PURITY: read() mutates ONLY the sensor's own cursor/baseline (its boundary bookkeeping),
    NEVER any substrate. The sensor has no reference to a store/graph and cannot.
    """

    def __init__(
        self,
        simulated: bool = False,
        trace: Optional[Sequence[TelemetrySample]] = None,
    ):
        self.simulated = simulated
        # frozen replay trace (replay mode only); a tuple so it cannot be mutated in place
        self._trace: Tuple[TelemetrySample, ...] = tuple(trace) if trace is not None else ()
        self._cursor: int = 0
        # the previous sample's raw pair, for delta computation (both modes). None until
        # the first read primes it.
        self._prev_perf: Optional[float] = None
        self._prev_proc: Optional[float] = None

        if simulated and trace is None:
            raise ValueError(
                "BodySensor(simulated=True) requires a frozen `trace` of TelemetrySample; "
                "replay mode is driven by recorded telemetry, never by a live read."
            )

    # ── the headline read ─────────────────────────────────────────────────────

    def read(self) -> float:
        """Return the current friction scalar in [0,1].

        In LIVE mode: reads time.perf_counter() and time.process_time() NOW and returns
        friction over the interval since the previous read (NEUTRAL_FRICTION on the first
        read, which only primes the baseline). This is the single point of
        non-determinism and is not on the deterministic test surface.

        In REPLAY mode: advances through the frozen trace one sample per call and returns
        friction over the interval since the previous trace sample (NEUTRAL_FRICTION on the
        first sample). Deterministic and byte-identical across processes/seeds. Raises
        IndexError if the trace is exhausted (the caller asked for more reads than the
        frozen trace provides — a test/pilot wiring error, surfaced loudly, never silently
        re-deriving a value).
        """
        if self.simulated:
            if self._cursor >= len(self._trace):
                raise IndexError(
                    "BodySensor replay trace exhausted: asked for more reads than the "
                    f"frozen trace has samples ({len(self._trace)}). The trace length must "
                    "cover every cycle; do not loop or re-derive."
                )
            sample = self._trace[self._cursor]
            self._cursor += 1
            perf, proc = sample.perf, sample.proc
        else:
            # the single live boundary read (production only; non-deterministic)
            perf = time.perf_counter()
            proc = time.process_time()

        if self._prev_perf is None:
            # first read: nothing to diff against — prime the baseline, report neutral.
            self._prev_perf = perf
            self._prev_proc = proc
            return NEUTRAL_FRICTION

        wall_dt = perf - self._prev_perf
        cpu_dt = proc - self._prev_proc
        self._prev_perf = perf
        self._prev_proc = proc
        return compute_friction(wall_dt, cpu_dt)

    # ── replay introspection (deterministic; for tests/pilots) ─────────────────

    def remaining(self) -> int:
        """Replay mode: how many unread samples remain in the frozen trace. (Live mode:
        always 0 — live has no bounded trace.)"""
        if not self.simulated:
            return 0
        return len(self._trace) - self._cursor

    def reset(self) -> None:
        """Rewind the sensor to its initial state (replay cursor to 0, baseline cleared),
        so the SAME frozen trace can be replayed again deterministically. Affects only the
        sensor's own bookkeeping; touches no substrate."""
        self._cursor = 0
        self._prev_perf = None
        self._prev_proc = None


# ─────────────────────────────────────────────────────────────────────────────
# LIVE-only boundary helpers for the SECONDARY signals (NOT load-bearing; NOT on the
# deterministic test surface; each from its NAMED OS call, never graph-re-derived).
# ─────────────────────────────────────────────────────────────────────────────
# SPEC-2c decision 1: load-average and memory-pressure are Unix-only secondary robustness
# signals only. They are provided as thin named-OS-call wrappers so a later robustness
# re-run can report them ALONGSIDE the headline. They do NOT feed the headline friction,
# are NOT deterministic, and the binding asserted-negative (no graph re-derivation) holds
# for them too: each reads ONLY its OS call and is given no store.

def read_loadavg_1min() -> Optional[float]:
    """SECONDARY (Unix-only): the 1-minute load average from os.getloadavg(). Returns None
    where unavailable (e.g. Windows). NAMED OS call only — never a graph quantity. Live/
    boundary use only; not deterministic, not on the test surface."""
    import os
    getloadavg = getattr(os, "getloadavg", None)
    if getloadavg is None:
        return None
    try:
        return float(getloadavg()[0])
    except (OSError, ValueError):
        return None


def read_maxrss_kb() -> Optional[float]:
    """SECONDARY (Unix-only): peak resident set size (ru_maxrss) from
    resource.getrusage(RUSAGE_SELF). Returns None where the `resource` module is
    unavailable. NAMED OS call only — never "active-node-count" or any graph quantity
    (that would be the forbidden soft-Wall-1 re-entry). Live/boundary use only; not
    deterministic, not on the test surface."""
    try:
        import resource
    except ImportError:
        return None
    try:
        return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (OSError, ValueError):
        return None
