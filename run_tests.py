#!/usr/bin/env python3
"""
Run every Nous test suite from the src-layout and report real pass/fail counts.

Why this script exists
----------------------
The modules live in ``src/`` and the suites in ``tests/``, but each suite imports
the modules by bare name (``from nous_store import ...``) and the determinism tests
additionally spawn fresh ``python -c`` subprocesses that *also* import by bare name.
Those subprocesses set their own working directory to ``tests/`` and inherit this
process's environment, so the only thing that makes their imports resolve is an
**absolute** ``PYTHONPATH`` pointing at ``src/``. A relative ``PYTHONPATH=src`` would
be re-resolved against the subprocess's ``tests/`` cwd and fail. This script sets the
absolute path once and runs each suite as its own process.

The suites use a tiny built-in harness (not pytest): each prints "N passed, M failed"
and exits non-zero if anything failed. Do NOT run them under pytest — pytest would
collect the ``test_*`` functions but would not see a logical ``check(...)`` failure as
a failed assertion, so it could report green on a real failure. Run them as scripts.

Usage:
    python3 run_tests.py
Exit code is 0 only if every suite reported 0 failures.
"""

import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
TESTS = os.path.join(ROOT, "tests")
EXPERIMENTS = os.path.join(ROOT, "experiments")

SUITES = [
    "test_nous_store.py",
    "test_nous_activation.py",
    "test_nous_coalitions.py",
    "test_nous_field.py",
    "test_nous_source_clustering.py",
    "test_nous_workspace.py",
    "test_nous_workspace_broadcast.py",
    "test_nous_perceive.py",
    # 2c interoception: BodySensor + default-off modulation hook — REPLAY-deterministic
    # mechanism only (no live telemetry here; the live smoke + populability pilot are
    # data/telemetry-dependent and stay OUT of the canonical runner, like the 1e selection
    # runner). Makes NO meaning claim.
    "test_nous_bodysensor.py",
    # independent adversarial verification (tester-authored) — kept in the one runner so the
    # canonical captured output reflects the full verification, not just the builder's suites.
    "test_tester_1c_adversarial.py",
    "test_tester_1c_mutation_battery.py",
    "test_tester_1d_i_adversarial.py",
    "test_tester_1d_ii_adversarial.py",
    # 1e measurement-instrument + selector — TESTER-authored adversarial verification.
    # These self-bootstrap src/ and experiments/ onto sys.path; they are DATA-FREE
    # (synthetic adversarial topologies only) and make no meaning claim.
    "test_tester_1e_selector_adversarial.py",
    "test_tester_1e_instrument_adversarial.py",
    "test_tester_1e_loopclosed.py",
    # 0b2 conserved activation — TESTER-authored adversarial verification of SPEC-0b2 §6
    # (N-1..N-9). Data-free (synthetic adversarial topologies only) and makes no meaning
    # claim. It spawns its own hash-seed x interpreter determinism probes, and it recovers
    # the pre-change engine from git to prove neutral byte-identity against the real
    # thing rather than against a transcription. Three defects are recorded here as
    # asserted-negatives — they PASS while the defect is present, and go red on a fix.
    "test_tester_0b2_adversarial.py",
    # 0b2 MECHANISM RE-VERIFICATION — TESTER-authored, written from scratch (not an extension of
    # test_tester_0b2_adversarial.py) after 0c fixed all three defects the original FAIL verdict
    # recorded. Adjudicates SPEC-0b2 §6's N-1..N-9 in full. Its P-0 block asserts the measurement
    # NOISE FLOOR: on a live clock two identical sigma=None calls differ by ~1e9 ULP through lazy
    # decay, which is larger than DEFECT-B's effect — so the frozen clock is a requirement, and the
    # suite proves it rather than asserting it in a comment.
    "test_tester_0b2_reverify.py",
    # 0c deterministic road ordering — TESTER-authored adversarial verification of SPEC-0c §6
    # (O-1..O-17 incl. O-4b). Data-free synthetic topologies; makes no meaning claim. Registered
    # by architect-pm, NOT by the tester: run_tests.py decides what the canonical count includes,
    # so registration is a fact-of-record change and the lane hook blocks the tester from it —
    # correctly. ledger_check C5 fails if a suite on disk is neither registered here nor excused
    # in ledger.unregistered_suites.
    "test_tester_0c_adversarial.py",
    # 2c interoception — TESTER-authored adversarial verification + pilot fairness audit.
    # Self-bootstraps src/ and experiments/ onto sys.path; DATA-FREE on the mechanism side
    # (synthetic adversarial topologies) and reads the ALREADY-FROZEN pilot trace artifact
    # for the fairness audit (no live capture). Makes no meaning claim.
    "test_tester_2c_adversarial.py",
]

# Experiment-layer MECHANISM suites (SPEC-1e §10 / decision 5): the instrument(s) 1e
# depends on are brought into the canonical runner so they are tester-grade, not just
# self-tested. These live in experiments/ and import the harness by bare name, so they
# need experiments/ on PYTHONPATH too. They are DATA-FREE (synthetic graphs only) — the
# data-dependent experiment-RESULT scripts (priming.py, priming_1e.py's selection run,
# exp1c_*.py) stay OUT of the canonical runner: they need the ~53 MB SWOW file and make
# meaning claims, which are the validator's, not the mechanism the runner certifies.
EXPERIMENT_SUITES = [
    "test_harness.py",              # 2A/2B harness mechanism (determinism/purity)
    "test_priming_instrument.py",   # SPEC-1e §9 broadcast-Δ instrument (B-i) mechanism
    "test_priming_1e.py",           # SPEC-1e §10 blind three-arm selector mechanism
]


def main() -> int:
    env = dict(os.environ)
    # absolute paths so inherited subprocess probes resolve imports regardless of cwd.
    # Both src/ (frozen library, bare-name imports) and experiments/ (harness, instrument,
    # bare-name imports) are needed for the experiment-layer mechanism suites.
    extra = SRC + os.pathsep + EXPERIMENTS
    env["PYTHONPATH"] = extra + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

    failed_suites = []
    all_suites = [(TESTS, s) for s in SUITES] + [(EXPERIMENTS, s) for s in EXPERIMENT_SUITES]
    for directory, suite in all_suites:
        path = os.path.join(directory, suite)
        print("#" * 70)
        print(f"# {suite}")
        print("#" * 70)
        # Flush our own buffered output before handing the shared stdout fd to the
        # child, so headers stay correctly ordered even when stdout is redirected to
        # a file (block-buffered) rather than a terminal (line-buffered).
        sys.stdout.flush()
        result = subprocess.run([sys.executable, path], env=env)
        if result.returncode != 0:
            failed_suites.append(suite)
        print()
        sys.stdout.flush()

    print("=" * 70)
    if failed_suites:
        print(f"  OVERALL: FAILED — {len(failed_suites)} suite(s): {', '.join(failed_suites)}")
        print("=" * 70)
        return 1
    print(f"  OVERALL: all {len(all_suites)} suites passed (0 failures)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
