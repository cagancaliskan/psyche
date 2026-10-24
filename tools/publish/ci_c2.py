#!/usr/bin/env python3
"""ci_c2.py — C2 (prose counts vs the ledger) with the held paper as its only exception.

D-012 holds the paper: its LaTeX sources quote counts from the run they were written
against and are not rewritten until the paper is unheld. So a plain `ledger_check.py` run
always exits 1 on them, and a gate that always fails is a gate nobody reads. D-031 §2.8
sets the commit gate while the paper is held:

    python3 tools/ledger_check.py --only C1,C3,C4,C5,C6     exits 0, and
    python3 tools/publish/ci_c2.py                          exits 0.

This file is the second half. It runs ledger_check's OWN C2 — the module is loaded by path
through importlib and is not modified — and tolerates exactly one class of finding: a path
under docs/paper/ ending in .tex. Everything else is printed and fails the run, so the
exception cannot grow by a single Markdown file.

    tolerated   check == C2, path starts with docs/paper/, path ends with .tex
    reported    every other finding, with ledger_check's own rendering

When no held finding remains, it says so: the exception should then be retired.

Every tolerated finding is listed by path and line under the count, so a reviewer can see
which paper lines are being excused and notice when a new one joins them.

Exit 0 = only held-paper findings (or none). Exit 1 = any other finding. Exit 2 = the tool
could not run, mapped as ledger_check's main() maps it: CaptureMalformed and
CensusUnreadable are exit 2, never 1, because then the numbers themselves are unusable. A
ledger that is missing, unreadable, not UTF-8, not JSON, not an object, or shaped so that
C2 cannot read it (tests, tests.per_suite or count_quarantine_paths of the wrong type) is
exit 2 as well, and so is any other exception C2 raises: "could not run" must never look
like "found something". So is a ledger without integer tests.suites and tests.assertions:
C2 silently skips the comparison a missing total would anchor, and a check that compared
nothing must never look like "clean".

Stdlib only.

Usage:
    python3 tools/publish/ci_c2.py
    python3 tools/publish/ci_c2.py --root PATH
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402

HELD_PREFIX = "docs/paper/"
HELD_SUFFIX = ".tex"


def is_held(finding) -> bool:
    """D-012: a C2 finding in the held paper's LaTeX sources, and nothing else."""
    path = getattr(finding, "path", "")
    return (getattr(finding, "check", None) == "C2"
            and isinstance(path, str)
            and path.startswith(HELD_PREFIX)
            and path.endswith(HELD_SUFFIX))


def partition(findings: Iterable) -> Tuple[List, List]:
    held: List = []
    other: List = []
    for f in findings:
        (held if is_held(f) else other).append(f)
    return held, other


def ledger_shape_problem(ledger) -> Optional[str]:
    """What would make ledger_check's C2 crash, or answer without checking, or None.

    C2 reads tests.assertions, tests.suites, tests.per_suite (its values go into a set)
    and count_quarantine_paths (each entry is a str.startswith prefix). It SKIPS every
    suites comparison when tests.suites is missing or null, and every assertions
    comparison when tests.assertions is: a run that then finds nothing has checked
    nothing, and must not read as clean. So both totals must be integers (not bools)."""
    if not isinstance(ledger, dict):
        return f"the ledger is a JSON {type(ledger).__name__}, not an object"
    tests = ledger.get("tests", {})
    if not isinstance(tests, dict):
        return "tests is not an object"
    for key in ("suites", "assertions"):
        if key not in tests:
            return f"tests.{key} is missing, so C2 would compare nothing against it"
        if type(tests[key]) is not int:
            return (f"tests.{key} is {json.dumps(tests[key])[:40]}, not an integer, so C2 "
                    f"would compare nothing against it")
    per_suite = tests.get("per_suite")
    if per_suite is not None:
        if not isinstance(per_suite, dict):
            return "tests.per_suite is not an object"
        try:
            set(per_suite.values())
        except TypeError:
            return "tests.per_suite holds a value that is not a plain number"
    quarantine = ledger.get("count_quarantine_paths", [])
    if not (isinstance(quarantine, list) and all(isinstance(q, str) for q in quarantine)):
        return "count_quarantine_paths is not a list of strings"
    return None


def run(root: Path, lc=None) -> int:
    """Run C2 under `root` and report. `lc` is the ledger_check module (injectable so
    the tolerance logic can be tested against fabricated findings)."""
    if lc is None:
        lc = core.ledger_check()
    if not (root / lc.LEDGER_REL).exists():
        print(f"ci_c2: {lc.LEDGER_REL} not found under {root}", file=sys.stderr)
        return 2
    try:
        ledger = lc.load_ledger(root)
    except SystemExit as e:
        # load_ledger signals a missing or non-JSON ledger with SystemExit(message); here
        # that is "the tool could not run", which is exit 2.
        print(f"ci_c2: {e}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as e:
        # a directory, an unreadable file, bytes that are not UTF-8 (UnicodeDecodeError is
        # a ValueError): Python would exit 1 on these, which is the "findings" code
        print(f"ci_c2: {lc.LEDGER_REL} is unreadable ({type(e).__name__}: {e})",
              file=sys.stderr)
        return 2
    problem = ledger_shape_problem(ledger)
    if problem:
        print(f"ci_c2: {lc.LEDGER_REL}: {problem}; C2 cannot read it", file=sys.stderr)
        return 2
    try:
        findings = lc.check_prose_vs_ledger(root, ledger)
    except lc.CensusUnreadable as e:
        print(f"ci_c2: the census could not run — {e}", file=sys.stderr)
        return 2
    except lc.CaptureMalformed as e:
        print(f"ci_c2: the capture is malformed — {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 — any crash is "could not run", never "found"
        print(f"ci_c2: C2 could not run ({type(e).__name__}: {e})", file=sys.stderr)
        return 2

    held, other = partition(findings)
    print(f"C2: {len(held)} finding(s) tolerated under D-012 (held paper)")
    for f in held:
        print(f"  tolerated  {f.path}:{f.line}" if f.line else f"  tolerated  {f.path}")
    if not held:
        print("notice: no held-paper finding remains; the D-012 exception can be retired")
    if other:
        print(f"\n{len(other)} other C2 finding(s):\n")
        for f in other:
            print(f.render())
            print()
        return 1
    print("ci_c2: clean outside the held paper")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(core.REPO), help="repository root")
    args = ap.parse_args(argv)
    try:
        lc = core.ledger_check()
    except Exception as e:  # the checker itself would not load: the tool cannot run
        print(f"ci_c2: cannot load tools/ledger_check.py ({type(e).__name__}: {e})",
              file=sys.stderr)
        return 2
    return run(Path(args.root).resolve(), lc)


if __name__ == "__main__":
    sys.exit(main())
