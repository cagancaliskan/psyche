"""
STEP 0 — mechanism probe (run BEFORE any fan experiment, because it decides the outcome).

Question: when activation spreads from a source, does the engine DIVIDE / normalize the
source's energy among its out-roads (so each target gets less as the source's out-degree
rises), or does each out-road INDEPENDENTLY transmit energy*strength*decay regardless of
how many siblings it has?

This probe answers it empirically and minimally: one source, all out-edges at EQUAL
strength, measured at one designated target, with out-degree 1 versus 8. If the target's
activation is the SAME in both cases, the engine does not normalize by out-degree — and
the human fan effect will therefore be ABSENT (a flat curve) under an equal-strength,
connectivity-only manipulation. That flat result is the EXPECTED, informative finding for
the fan experiment, not a failure.

Run:
    python3 experiments/step0_probe.py
    PYTHONPATH="$PWD/src" python3 experiments/step0_probe.py   # (equivalent; harness self-bootstraps)
"""

from __future__ import annotations

from harness import build_graph_from_spec, retrieval_strength, star_spec


def target_activation_for_fan(fan: int) -> float:
    """Build a source with `fan` equal-strength out-roads and read the activation that
    reaches the FIRST target (T1). T1's incoming path is identical in every case; only
    the source's out-degree changes."""
    inst = build_graph_from_spec(star_spec(fan))
    return retrieval_strength(inst.store, inst.ids["S"], inst.ids["T1"])


def main() -> int:
    print("=" * 70)
    print("STEP 0 PROBE — does spreading activation normalize by out-degree?")
    print("=" * 70)
    print("Setup: one source S, all out-edges EQUAL strength (same traverse count),")
    print("       read activation at target T1. Vary only the source's out-degree.")
    print()

    a1 = target_activation_for_fan(1)
    a8 = target_activation_for_fan(8)

    print(f"  out-degree 1  ->  T1 activation = {a1!r}")
    print(f"  out-degree 8  ->  T1 activation = {a8!r}")
    print()

    identical = (a1 == a8)
    if identical:
        print("FINDING: identical. Each out-road transmits the source's FULL activation;")
        print("         energy is NOT divided among out-roads. => NO out-degree normalization.")
        print("CONSEQUENCE: the fan effect will be ABSENT (flat curve) under an equal-strength,")
        print("             connectivity-only manipulation. That is the expected, informative")
        print("             result for the fan experiment — not a bug to fix.")
    else:
        print("FINDING: target activation DEPENDS on out-degree => the engine DOES normalize.")
        print(f"         (1 vs 8 differ by {a8 - a1!r}). A fan effect could then appear.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
