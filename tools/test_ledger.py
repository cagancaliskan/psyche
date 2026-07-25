#!/usr/bin/env python3
"""test_ledger.py — suite for the ledger tools.

Uses the project's own harness convention: no pytest, prints
`RESULT: N passed, M failed`, exits non-zero on any failure. Run as a script.

    python3 tools/test_ledger.py

These tests build throwaway repositories in a temp directory, so they never touch
the real one, and they assert on the *findings*, not on printed text.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_check as LC          # noqa: E402
import ledger_sync as LS           # noqa: E402

PASSED = 0
FAILED = 0


def check(cond: bool, label: str) -> None:
    global PASSED, FAILED
    if cond:
        PASSED += 1
    else:
        FAILED += 1
        print(f"  FAIL: {label}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


BASE_LEDGER = {
    "schema_version": 1,
    "tests": {"_GENERATED": ("by tools/ledger_sync.py from docs/TEST_OUTPUT.txt "
                             "— do not hand-edit"),
              "suites": 2, "assertions": 30, "failures": 0,
              "captured_at": "2026-07-25 10:00:00 +0300", "captured_python": "3.12.4",
              "per_suite": {"test_a.py": 10, "test_b.py": 20}},
    "bricks": {"1c": {"name": "source clustering", "status": "BUILT-UNVALIDATED"}},
    "valid_statuses": ["PROVEN", "BUILT-UNVALIDATED", "DESIGNED", "NO-GO"],
    "forbidden_claim_terms": ["is conscious", "is a mind"],
    "claim_quarantine_paths": ["docs/design/"],
    "count_quarantine_paths": ["docs/experiments/"],
}

CAPTURE = """\
======================================================================
Generated : 2026-07-25 10:00:00 +0300
Python    : Python 3.12.4
======================================================================

######################################################################
# test_a.py
######################################################################
  RESULT: 10 passed, 0 failed

######################################################################
# test_b.py
######################################################################
  RESULT: 20 passed, 0 failed
"""


def make_repo(tmp: Path, *, ledger=None, capture=CAPTURE, files=None) -> Path:
    root = tmp / f"repo{len(list(tmp.iterdir()))}"
    (root / "tools").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "tools" / "ledger.json").write_text(
        json.dumps(ledger or BASE_LEDGER, indent=2), encoding="utf-8")
    if capture is not None:
        (root / "docs" / "TEST_OUTPUT.txt").write_text(capture, encoding="utf-8")
    for rel, body in (files or {}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return root


def run(tmp: Path) -> None:
    # ── C1 ───────────────────────────────────────────────────────────────────
    section("C1 passes when the ledger matches the capture")
    r = make_repo(tmp)
    check(LC.check_ledger_vs_capture(r, LC.load_ledger(r)) == [], "clean C1")

    section("C1 catches a stale total")
    led = json.loads(json.dumps(BASE_LEDGER))
    led["tests"]["assertions"] = 618
    r = make_repo(tmp, ledger=led)
    f = LC.check_ledger_vs_capture(r, LC.load_ledger(r))
    check(len(f) == 1 and "assertions" in f[0].message, "stale total flagged once")

    section("C1 catches a per-suite drift")
    led = json.loads(json.dumps(BASE_LEDGER))
    led["tests"]["per_suite"]["test_b.py"] = 19
    led["tests"]["assertions"] = 29
    r = make_repo(tmp, ledger=led)
    f = LC.check_ledger_vs_capture(r, LC.load_ledger(r))
    check(any("per_suite[test_b.py]" in x.message for x in f), "per-suite drift flagged")

    section("C1 reports a capture containing failures")
    bad = CAPTURE.replace("RESULT: 20 passed, 0 failed", "RESULT: 19 passed, 1 failed")
    led = json.loads(json.dumps(BASE_LEDGER))
    led["tests"].update({"assertions": 29, "failures": 1,
                         "per_suite": {"test_a.py": 10, "test_b.py": 19}})
    r = make_repo(tmp, ledger=led, capture=bad)
    f = LC.check_ledger_vs_capture(r, LC.load_ledger(r))
    check(any("failure(s)" in x.message for x in f), "failing capture flagged")

    section("C1 reports a missing capture rather than crashing")
    r = make_repo(tmp, capture=None)
    f = LC.check_ledger_vs_capture(r, LC.load_ledger(r))
    check(len(f) == 1 and "missing" in f[0].message, "missing capture handled")

    # ── C2 ───────────────────────────────────────────────────────────────────
    section("C2 accepts the true total and true per-suite counts")
    r = make_repo(tmp, files={"README.md": (
        "The suite is 30 assertions across 2 suites.\n"
        "The store contributes 10 assertions and the engine 20 assertions.\n")})
    check(LC.check_prose_vs_ledger(r, LC.load_ledger(r)) == [], "true counts accepted")

    section("C2 catches the real historical bug — a stale total in prose")
    r = make_repo(tmp, files={"README.md": "618 assertions across 12 suites\n"})
    f = LC.check_prose_vs_ledger(r, LC.load_ledger(r))
    check(any("618" in x.message for x in f), "stale assertion total caught")
    check(any("12 suites" in x.message or "12 suites" in x.message.replace("says ", "")
              or "says 12 suites" in x.message for x in f), "stale suite count caught")

    section("C2 respects the allow-count pragma")
    r = make_repo(tmp, files={"README.md":
                              "<!-- ledger:allow-count -->\n618 assertions (historical)\n"})
    check(LC.check_prose_vs_ledger(r, LC.load_ledger(r)) == [], "pragma honoured")

    section("C2 respects ignore-file")
    r = make_repo(tmp, files={"OLD.md": "<!-- ledger:ignore-file -->\n618 assertions\n"})
    check(LC.check_prose_vs_ledger(r, LC.load_ledger(r)) == [], "ignore-file honoured")

    section("C2 exempts frozen documents by path")
    r = make_repo(tmp, files={"docs/experiments/EXP-frozen.md":
                              "at freezing this was 8 suites / 254 assertions\n"})
    check(LC.check_prose_vs_ledger(r, LC.load_ledger(r)) == [],
          "frozen pre-registration not rewritten")

    section("C2 still checks documents outside the count quarantine")
    r = make_repo(tmp, files={"docs/OTHER.md": "618 assertions\n"})
    check(len(LC.check_prose_vs_ledger(r, LC.load_ledger(r))) == 1,
          "non-quarantined doc still checked")

    section("C2 handles thousands separators")
    led = json.loads(json.dumps(BASE_LEDGER))
    led["tests"]["assertions"] = 1372
    led["tests"]["per_suite"] = {"test_a.py": 1372}
    led["tests"]["suites"] = 1
    cap = CAPTURE.replace("RESULT: 10 passed, 0 failed", "RESULT: 1372 passed, 0 failed")
    cap = cap.split("# test_b.py")[0]
    r = make_repo(tmp, ledger=led, capture=cap,
                  files={"P.md": "1,372 assertions in 1 suite\n"})
    check(LC.check_prose_vs_ledger(r, LC.load_ledger(r)) == [], "1,372 parsed as 1372")

    # ── C3 ───────────────────────────────────────────────────────────────────
    section("C3 accepts an agreeing status")
    r = make_repo(tmp, files={"S.md": "Step 1c is BUILT-UNVALIDATED.\n"})
    check(LC.check_status_vocabulary(r, LC.load_ledger(r)) == [], "agreeing status ok")

    section("C3 accepts the middot spelling as the same status")
    r = make_repo(tmp, files={"S.md": "Step 1c is BUILT · UNVALIDATED.\n"})
    check(LC.check_status_vocabulary(r, LC.load_ledger(r)) == [], "middot alias ok")

    section("C3 catches a document promoting a brick past the ledger")
    r = make_repo(tmp, files={"S.md": "Step 1c is PROVEN.\n"})
    f = LC.check_status_vocabulary(r, LC.load_ledger(r))
    check(any("1c" in x.message and "BUILT-UNVALIDATED" in x.message for x in f),
          "over-promotion caught")

    section("C3 does NOT conflate a meaning verdict with a build status")
    r = make_repo(tmp, files={"S.md": "1c mechanism BUILT-UNVALIDATED; meaning NOT-YET.\n"})
    check(LC.check_status_vocabulary(r, LC.load_ledger(r)) == [],
          "two axes coexist without a finding")

    section("C3 stays silent on a line naming several bricks")
    led3 = json.loads(json.dumps(BASE_LEDGER))
    led3["bricks"]["2c"] = {"name": "interoception", "status": "BUILT-UNVALIDATED"}
    r = make_repo(tmp, ledger=led3,
                  files={"S.md": "Phase 0 is PROVEN; this covers 1c and 2c downstream.\n"})
    check(LC.check_status_vocabulary(r, LC.load_ledger(r)) == [],
          "multi-brick narration not adjudicated")

    section("C3 leaves the roadmap alone (it narrates history)")
    r = make_repo(tmp, files={"docs/nous_roadmap.md": "Step 1c is PROVEN.\n"})
    check(LC.check_status_vocabulary(r, LC.load_ledger(r)) == [], "roadmap exempt")

    # ── C4 ───────────────────────────────────────────────────────────────────
    section("C4 does NOT flag a disclaimer — the real false-positive risk")
    r = make_repo(tmp, files={"R.md": (
        "Nous is not a validated cognitive model and is not a mind.\n"
        "The winner is never 'what the system is conscious of'.\n"
        "No claim is made that the system is conscious.\n"
        "It does not follow that it is a mind.\n")})
    check(LC.check_forbidden_claims(r, LC.load_ledger(r)) == [],
          "negated mentions pass clean")

    section("C4 sees a negation that wrapped onto the previous line")
    r = make_repo(tmp, files={"W.md": (
        "Using that vocabulary is NOT a\n"
        "claim that the system is conscious, or that it is a mind.\n")})
    check(LC.check_forbidden_claims(r, LC.load_ledger(r)) == [],
          "cross-line negation honoured")

    section("C4 still fires when the previous line carries no negation")
    r = make_repo(tmp, files={"W.md": (
        "The architecture has eight modules and a closed loop.\n"
        "On any reasonable reading the system is conscious.\n")})
    check(len(LC.check_forbidden_claims(r, LC.load_ledger(r))) == 1,
          "unnegated wrap still caught")

    section("C4 catches a forbidden claim in prose")
    r = make_repo(tmp, files={"R.md": "The system is conscious in a real sense.\n"})
    f = LC.check_forbidden_claims(r, LC.load_ledger(r))
    check(len(f) == 1 and "is conscious" in f[0].message, "forbidden claim caught")

    section("C4 catches a forbidden claim in a Python docstring")
    r = make_repo(tmp, files={"src/x.py": '"""This module is a mind."""\n'})
    f = LC.check_forbidden_claims(r, LC.load_ledger(r))
    check(len(f) == 1, "python source scanned too")

    section("C4 exempts the quarantined vision folder")
    r = make_repo(tmp, files={"docs/design/vision.md": "This is a mind. It is conscious.\n"})
    check(LC.check_forbidden_claims(r, LC.load_ledger(r)) == [], "quarantine honoured")

    section("C4 respects allow-claim on the line above")
    r = make_repo(tmp, files={"S.md":
                              "<!-- ledger:allow-claim -->\n> quoting: it is a mind\n"})
    check(LC.check_forbidden_claims(r, LC.load_ledger(r)) == [], "allow-claim honoured")

    section("C4 flags each offending line only once")
    r = make_repo(tmp, files={"R.md": "it is a mind and is conscious\n"})
    f = LC.check_forbidden_claims(r, LC.load_ledger(r))
    check(len(f) == 1, "one finding per line")

    # ── sync ─────────────────────────────────────────────────────────────────
    section("ledger_sync --check passes on a current ledger")
    r = make_repo(tmp)
    check(LS.sync(r, "check") == 0, "current ledger reports 0")

    section("ledger_sync --check fails on a stale ledger")
    led = json.loads(json.dumps(BASE_LEDGER))
    led["tests"]["assertions"] = 1
    r = make_repo(tmp, ledger=led)
    check(LS.sync(r, "check") == 1, "stale ledger reports 1")

    section("ledger_sync writes, and the result then passes C1")
    check(LS.sync(r, "write") == 0, "sync wrote")
    check(LC.check_ledger_vs_capture(r, LC.load_ledger(r)) == [], "C1 clean after sync")

    section("ledger_sync preserves hand-maintained fields")
    data = json.loads((r / "tools" / "ledger.json").read_text())
    check(data["bricks"]["1c"]["status"] == "BUILT-UNVALIDATED", "bricks preserved")
    check(data["forbidden_claim_terms"] == ["is conscious", "is a mind"], "terms preserved")

    section("ledger_sync refuses to sync from a capture with failures")
    bad = CAPTURE.replace("RESULT: 20 passed, 0 failed", "RESULT: 19 passed, 1 failed")
    r = make_repo(tmp, capture=bad)
    check(LS.sync(r, "write") == 2, "refused a failing capture")

    section("parse_capture derives the totals independently")
    r = make_repo(tmp)
    cap = LC.parse_capture(r)
    check(cap["suites"] == 2 and cap["assertions"] == 30 and cap["failures"] == 0,
          "capture parsed")
    check(cap["captured_python"] == "3.12.4", "python version parsed")


def main() -> int:
    print("=" * 70)
    print("  LEDGER TOOLS — TEST SUITE")
    print("=" * 70)
    tmp = Path(tempfile.mkdtemp(prefix="ledger-test-"))
    try:
        run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nRESULT: {PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
