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

SUITES = [
    "test_nous_store.py",
    "test_nous_activation.py",
    "test_nous_coalitions.py",
    "test_nous_field.py",
    "test_nous_source_clustering.py",
    "test_nous_workspace.py",
    "test_nous_perceive.py",
    # independent adversarial verification (tester-authored) — kept in the one runner so the
    # canonical captured output reflects the full verification, not just the builder's suites.
    "test_tester_1c_adversarial.py",
    "test_tester_1c_mutation_battery.py",
    "test_tester_1d_i_adversarial.py",
]


def main() -> int:
    env = dict(os.environ)
    # absolute path so inherited subprocess probes resolve imports regardless of cwd
    env["PYTHONPATH"] = SRC + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

    failed_suites = []
    for suite in SUITES:
        path = os.path.join(TESTS, suite)
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
    print(f"  OVERALL: all {len(SUITES)} suites passed (0 failures)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
