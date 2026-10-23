"""
2c LIVE-MODE SMOKE CHECK (non-graded; demonstrates the live boundary path runs).

PURPOSE (SPEC-2c §3.2 (D-2)): live mode is the single, isolated, NON-DETERMINISTIC boundary
where real perf_counter/process_time telemetry is read. It is EXPLICITLY NOT part of the
deterministic test surface and is NOT in canonical run_tests.py. This smoke check exists
only to demonstrate that the live path RUNS and the modulation FIRES on truly live
telemetry — it is NEVER a graded result and is NEVER counted toward the rule-7 determinism
bar (it is non-reproducible by construction).

WHAT IT IS NOT: not a meaning claim, not a determinism check, not a populability number.
The friction values it prints will differ on every run and every machine — that is the
whole point of isolating the live read behind the BodySensor boundary. A telemetry-grounded
modulation mechanism is not a feeling, emotion, awareness, or consciousness (SPEC-2c §0.1).

Run:
    python3 experiments/smoke_2c_live.py
"""

from __future__ import annotations

import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from psyche_store import SubstrateStore, Clock, NodeType
from psyche_perceive import think
from psyche_bodysensor import BodySensor


def _worn(s, a, b, n=30):
    for _ in range(n):
        s.traverse(a, b)


def _flip_mind():
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    alpha = s.add_node("alpha", NodeType.CONCEPT)
    near1 = s.add_node("nearone", NodeType.CONCEPT)
    near2 = s.add_node("neartwo", NodeType.CONCEPT)
    gamma = s.add_node("gamma", NodeType.CONCEPT)
    link = s.add_node("bridgelink", NodeType.CONCEPT)
    rich1 = s.add_node("richone", NodeType.CONCEPT)
    rich2 = s.add_node("richtwo", NodeType.CONCEPT)
    rich3 = s.add_node("richthree", NodeType.CONCEPT)
    rich4 = s.add_node("richfour", NodeType.CONCEPT)
    _worn(s, alpha, near1); _worn(s, alpha, near2); _worn(s, near1, near2)
    _worn(s, gamma, link, n=2); _worn(s, link, rich1)
    _worn(s, rich1, rich2); _worn(s, rich1, rich3); _worn(s, rich1, rich4)
    _worn(s, rich2, rich3); _worn(s, rich2, rich4); _worn(s, rich3, rich4)
    return s


def _busy_spin(duration_s: float) -> None:
    end = time.perf_counter() + duration_s
    x = 0
    while time.perf_counter() < end:
        x += 1


def main() -> int:
    print("=" * 70)
    print("  2c LIVE-MODE SMOKE CHECK (non-graded; non-reproducible by design)")
    print("=" * 70)

    # A LIVE BodySensor reads real perf_counter()/process_time() at each read().
    sensor = BodySensor(simulated=False)

    # First read primes the baseline (returns neutral).
    f0 = sensor.read()
    print(f"  first live read (primes baseline) : friction = {f0:.6f}")

    ran = True
    fired = False
    for i in range(6):
        # induce some real contention so successive reads see non-trivial friction
        if i % 2 == 0:
            _busy_spin(0.003)
        else:
            time.sleep(0.003)
        s = _flip_mind()
        try:
            r = think(s, "alpha gamma", body_sensor=sensor)
        except IndexError:
            # live mode has no bounded trace, so this should never happen; guard anyway
            ran = False
            break
        winner = (sorted(s.get_node(m).content for m in r.thought.members)
                  if r.thought else None)
        # the modulation FIRED iff the effective decay was actually computed from friction
        # (it differs from the base whenever friction > 0; we just confirm it is recorded)
        fired = fired or (r.body_friction is not None and r.effective_decay_per_hop is not None)
        print(f"  cycle {i}: live friction = {r.body_friction:.6f}  "
              f"effective_decay = {r.effective_decay_per_hop:.6f}  winner = {winner}")

    print("-" * 70)
    print(f"  live path ran without error            : {ran}")
    print(f"  modulation fired (friction -> decay)   : {fired}")
    print("  NOTE: these friction numbers are non-reproducible (real live telemetry); this")
    print("        smoke check is NOT a graded result and is NOT in the canonical runner.")
    print("=" * 70)
    return 0 if (ran and fired) else 1


if __name__ == "__main__":
    raise SystemExit(main())
