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
import re
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
    # 2f-i temporal credit assignment (SPEC-2f Design C) — the episodic trace and the
    # eligibility kernel, plus think()'s default-off `credit_trace` hook. MECHANISM only:
    # it verifies that an outcome at cycle t+k moves a weight at t in a bounded, decaying,
    # reproducible way, against a control matched by construction and a shuffle that
    # preserves both marginals. It makes NO cognitive claim.
    "test_nous_credit.py",
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
    # 0d float-accumulation detector — TESTER-authored adversarial verification of SPEC-0d §4
    # (F-1..F-8). Its F-1 leg is loop-closed on the project's OWN git history: it extracts src/ at
    # three pre-fix commits and shows the detector would have caught all three manual hunts on the
    # day the code was written. Registered by architect-pm (fact-of-record change; C5 enforces it).
    "test_tester_0d_adversarial.py",
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
    # 2f-i credit assignment + the 0e runner fix — TESTER-authored adversarial verification,
    # written from scratch. Registered by architect-pm (a fact-of-record change the lane hook
    # blocks the tester from) AFTER its conversion landed: registering it while it still
    # aborted would have added a second aborting suite to the canonical run.
    "test_tester_2f_adversarial.py",
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


RESULT_RE = re.compile(r"^\s*RESULT:\s+(\d+)\s+passed,\s+(\d+)\s+failed\s*$", re.M)


def classify(output: str) -> dict:
    """Decide what a suite's transcript actually says — BRICK 0e.

    Three outcomes, and the third is the one that used to be invisible:

      passed  — a RESULT line with zero failures
      failed  — a RESULT line with failures
      ABORTED — NO RESULT line at all, because the suite raised and died partway

    An aborted suite's assertion count is reported as **UNKNOWN, never zero**. That
    choice is deliberate and this is the reason: the count lives in the RESULT line the
    suite never printed, so any number produced here would be invented. Zero is not a
    safe default — it is a wrong number that SUMS SILENTLY into the headline total, which
    is exactly how this defect hid an entire 334-assertion file three times. A partial
    count reconstructed from the `FAIL:` lines was considered and rejected: it would
    report a figure the suite never asserted, and would understate by exactly the amount
    nobody can see.
    """
    # FIRST RESULT wins, matching capture_run.parse_full and ledger_check.parse_capture
    # exactly. A suite printing two RESULT lines is malformed either way; what matters is
    # that all three readers of this format agree on which one counts, because a runner
    # that summed the last while the capture parser summed the first would disagree only
    # on malformed input — the case nobody tests.
    m = RESULT_RE.search(output)
    if m is not None:
        return {"aborted": False, "passed": int(m.group(1)), "failed": int(m.group(2)),
                "detail": ""}
    # No RESULT: reconstruct what killed it, so the failure list can name it.
    exc, where = "no RESULT line", ""
    lines = [ln for ln in output.splitlines() if ln.strip()]
    for ln in reversed(lines):
        s = ln.strip()
        if re.match(r"^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception|Exit|Interrupt)\b", s):
            exc = s
            break
    for ln in reversed(lines):
        m2 = re.match(r'^\s*File "(.+)", line (\d+), in (\S+)', ln)
        if m2:
            where = f"{os.path.basename(m2.group(1))}:{m2.group(2)} in {m2.group(3)}"
            break
    return {"aborted": True, "passed": None, "failed": None,
            "detail": f"{exc}" + (f"  [{where}]" if where else "")}


def main() -> int:
    env = dict(os.environ)
    # absolute paths so inherited subprocess probes resolve imports regardless of cwd.
    # Both src/ (frozen library, bare-name imports) and experiments/ (harness, instrument,
    # bare-name imports) are needed for the experiment-layer mechanism suites.
    extra = SRC + os.pathsep + EXPERIMENTS
    env["PYTHONPATH"] = extra + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

    failed_suites = []
    aborted_suites = []          # BRICK 0e: raised and never reported — count UNKNOWN
    all_suites = [(TESTS, s) for s in SUITES] + [(EXPERIMENTS, s) for s in EXPERIMENT_SUITES]
    for directory, suite in all_suites:
        path = os.path.join(directory, suite)
        print("#" * 70)
        print(f"# {suite}")
        print("#" * 70)
        # Flush our own buffered output before emitting the child's, so headers stay
        # correctly ordered even when stdout is redirected to a file (block-buffered)
        # rather than a terminal (line-buffered).
        sys.stdout.flush()
        # stderr is MERGED into stdout rather than inherited. A suite that dies writes
        # its traceback to stderr, and with stderr inherited that traceback reached the
        # terminal but never the captured transcript — so the capture recorded a suite
        # that simply stopped, with no evidence of why. The traceback belongs in the
        # record, because it is the whole explanation for a missing RESULT line.
        result = subprocess.run([sys.executable, path], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True)
        out = result.stdout or ""
        sys.stdout.write(out)
        verdict = classify(out)
        if verdict["aborted"]:
            aborted_suites.append((suite, verdict["detail"]))
            # Stated in the transcript itself, not only in the summary, so a reader
            # scrolling the capture cannot mistake the gap for a suite that ran clean.
            print(f"\n  ABORTED: {suite} raised and never reported a RESULT line.")
            print(f"           {verdict['detail']}")
            print(f"           Assertion count for this suite is UNKNOWN, not zero — "
                  f"it is excluded from the total rather than summed as 0.")
        elif result.returncode != 0 or verdict["failed"]:
            failed_suites.append(suite)
        print()
        sys.stdout.flush()

    ran = len(all_suites)
    print("=" * 70)
    if aborted_suites or failed_suites:
        # "N suites ran, M failed" and "N suites ran, M aborted" are DIFFERENT outcomes
        # and are printed differently. An aborted suite is not a failing suite: a failing
        # suite reported a number and the number was bad; an aborted suite reported no
        # number at all, so the total below is INCOMPLETE and says so.
        print(f"  OVERALL: FAILED — {ran} suite(s) ran, "
              f"{len(failed_suites)} failed, {len(aborted_suites)} ABORTED")
        if failed_suites:
            print(f"    failed : {', '.join(failed_suites)}")
        for suite, detail in aborted_suites:
            print(f"    ABORTED: {suite} — {detail}")
        if aborted_suites:
            print(f"  THE TOTAL IS INCOMPLETE: {len(aborted_suites)} suite(s) contributed "
                  f"no assertion count. Any figure derived from this run understates the "
                  f"repository by an unknown amount (brick 0e).")
        print("=" * 70)
        return 1
    print(f"  OVERALL: all {ran} suites passed (0 failures, 0 aborted)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
