"""
Fan-effect experiment (Phase 2A) — pre-registered, honest, deterministic.

╔══════════════════════════════════════════════════════════════════════════════╗
║ PRE-REGISTERED PREDICTION                                                       ║
║   Retrieval strength DECREASES as source fan (out-degree) increases.           ║
║   (This is the direction of the HUMAN fan effect: the more facts associated     ║
║    with a cue, the slower/weaker the retrieval of any one of them.)             ║
║                                                                                ║
║ BRIDGE ASSUMPTION (how a human latency effect maps onto Nous)                  ║
║   The human fan effect is measured as retrieval LATENCY (reaction time). Nous   ║
║   has no latency — it has activation magnitude. We therefore bridge the two by  ║
║   mapping HIGHER ACTIVATION = FASTER / STRONGER retrieval. Under this mapping a  ║
║   human "slower with higher fan" predicts "LOWER activation with higher fan".   ║
╚══════════════════════════════════════════════════════════════════════════════╝

The prediction and bridge above are FIXED before any measurement and are printed to
stdout (see `print_preregistration`) BEFORE a single number is computed. The verdict at
the end is COMPUTED from the measured table — it is not hard-coded — and may falsify the
prediction. A flat (null) result is an honest finding, reported as such; the engine is
never altered to force the effect.

Design (all held constant across conditions except the one varied factor, fan F):
  - Topology: a star — one source S with F equal-strength out-roads to leaf targets
    T1..TF. Readout taken at the designated target T1.
  - Edge strength: every edge crossed the same number of times (STRENGTH_COUNT) on a
    simulated clock, so all edges are exactly equal-strength (no decay drift).
  - Activation knobs: energy, decay_per_hop, floor, hop_budget held at library defaults.
  - The ONLY thing that changes between conditions is F (the source's out-degree).

Run:
    python3 experiments/fan_effect.py
"""

from __future__ import annotations

from harness import (
    build_graph_from_spec,
    retrieval_strength,
    run_trials,
    star_spec,
    DEFAULT_SEED_ENERGY,
    DEFAULT_DECAY_PER_HOP,
    DEFAULT_FLOOR,
    DEFAULT_HOP_BUDGET,
)

# ── fixed experimental parameters ────────────────────────────────────────────────────
FAN_LEVELS = (1, 2, 4, 8, 16)     # source out-degrees to compare
STRENGTH_COUNT = 3                # traverse count per edge → equal edge strength
N_TRIALS = 5                      # fresh instances per condition (determinism ⇒ spread 0)
DESIGNATED_TARGET = "T1"          # which target we read (controlled to be symmetric)
SOURCE = "S"

# activation knobs, held constant across every condition (library defaults)
ENERGY = DEFAULT_SEED_ENERGY
DECAY_PER_HOP = DEFAULT_DECAY_PER_HOP
FLOOR = DEFAULT_FLOOR
HOP_BUDGET = DEFAULT_HOP_BUDGET

# verdict tolerance: differences below this are treated as "no difference". Floats that
# are genuinely identical compare exactly equal; EPS only guards against ULP-scale noise.
EPS = 1e-9

# The pre-registered statements, as data (so the same strings are printed and quotable).
PREDICTION = "Retrieval strength DECREASES as source fan (out-degree) increases."
BRIDGE = ("Human fan effect is retrieval LATENCY; Nous has no latency, so we map "
          "higher activation = faster/stronger retrieval. Thus 'slower with higher "
          "fan' (human) predicts 'LOWER activation with higher fan' (Nous).")


def _knobs() -> dict:
    return dict(energy=ENERGY, decay_per_hop=DECAY_PER_HOP, floor=FLOOR, hop_budget=HOP_BUDGET)


# ─────────────────────────────────────────────────────────────────────────────
# Pre-registration banner — PRINTED BEFORE ANY RESULT IS COMPUTED
# ─────────────────────────────────────────────────────────────────────────────

def print_preregistration() -> None:
    print("=" * 78)
    print("FAN-EFFECT EXPERIMENT (Phase 2A) — pre-registered")
    print("=" * 78)
    print("PRE-REGISTERED PREDICTION:")
    print(f"  {PREDICTION}")
    print()
    print("BRIDGE ASSUMPTION:")
    print(f"  {BRIDGE}")
    print()
    print("This prediction is fixed BEFORE any measurement below. The verdict is computed")
    print("from the data and may falsify it; a flat/null result is an honest finding.")
    print("=" * 78)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Controls
# ─────────────────────────────────────────────────────────────────────────────

def print_held_constant() -> None:
    """Control: make it explicit that ONLY fan varies; everything else is pinned."""
    print("CONTROL — only-varied-factor (fan F). Held constant across all conditions:")
    print(f"  edge strength (traverse count per edge) = {STRENGTH_COUNT}")
    print(f"  seed energy                             = {ENERGY!r}")
    print(f"  decay_per_hop                           = {DECAY_PER_HOP!r}")
    print(f"  floor                                   = {FLOOR!r}")
    print(f"  hop_budget                              = {HOP_BUDGET}")
    print(f"  trials per condition                    = {N_TRIALS}")
    print(f"  designated readout target               = {DESIGNATED_TARGET}")
    print()


def print_target_symmetry_control(fan: int = 8) -> None:
    """Control: confirm WHICH target we read does not matter — all F targets of a source
    receive identical activation (the star is symmetric). If this failed, picking T1
    would be an uncontrolled choice."""
    inst = build_graph_from_spec(star_spec(fan, strength_count=STRENGTH_COUNT))
    vals = [
        retrieval_strength(inst.store, inst.ids[SOURCE], inst.ids[f"T{i}"], **_knobs())
        for i in range(1, fan + 1)
    ]
    lo, hi = min(vals), max(vals)
    symmetric = (hi - lo) <= EPS
    print(f"CONTROL — target symmetry (F={fan}): every target's activation should be equal.")
    print(f"  distinct values observed = {sorted(set(vals))!r}")
    print(f"  spread across targets    = {hi - lo!r}  ->  {'SYMMETRIC' if symmetric else 'ASYMMETRIC'}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# The sweep
# ─────────────────────────────────────────────────────────────────────────────

def compute_fan_table():
    """Measure retrieval strength at the designated target as fan F varies.

    Returns a list of (F, trials_dict) where trials_dict is run_trials' aggregate.
    Pure read; deterministic by construction.
    """
    table = []
    for fan in FAN_LEVELS:
        def factory(_fan=fan):
            return build_graph_from_spec(star_spec(_fan, strength_count=STRENGTH_COUNT))
        agg = run_trials(
            factory, N_TRIALS,
            cue_name=SOURCE, target_name=DESIGNATED_TARGET, **_knobs(),
        )
        table.append((fan, agg))
    return table


def print_table(table) -> None:
    print("RESULT — fan F vs mean activation at target", DESIGNATED_TARGET)
    print(f"  {'F':>3}   {'mean target activation':<26}  {'spread (max-min)':<18}")
    print(f"  {'-'*3}   {'-'*26}  {'-'*18}")
    for fan, agg in table:
        print(f"  {fan:>3}   {agg['mean']!r:<26}  {agg['spread']!r:<18}")
    print()


def verdict(table) -> str:
    """Compute the verdict from the measured means. Honest: it reads the data."""
    means = [agg["mean"] for _, agg in table]
    delta = max(means) - min(means)
    flat = delta <= EPS
    decreasing = all(means[i] > means[i + 1] + EPS for i in range(len(means) - 1))
    if flat:
        return ("DOES NOT MATCH: activation is flat across fan — the engine does not "
                "normalize by out-degree (see EXPERIMENT_NOTES.md).")
    if decreasing:
        return "MATCHES human direction (activation decreases with fan)."
    return ("DOES NOT MATCH: activation varies with fan but not in the human direction "
            "(not monotonically decreasing).")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    # 1) PRE-REGISTRATION FIRST — before any measurement.
    print_preregistration()

    # 2) Controls.
    print_held_constant()
    print_target_symmetry_control(fan=8)

    # 3) The measurement.
    table = compute_fan_table()
    print_table(table)

    # 4) Verdict computed from the data.
    print("VERDICT:")
    print(f"  {verdict(table)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
