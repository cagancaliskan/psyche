#!/usr/bin/env python3
"""test_ledger.py — suite for the ledger tools.

Uses the project's own harness convention: no pytest, prints
`RESULT: N passed, M failed`, exits non-zero on any failure. Run as a script.

    python3 tools/test_ledger.py

These tests build throwaway repositories in a temp directory, so they never touch
the real one, and they assert on the *findings*, not on printed text.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_check as LC          # noqa: E402
import ledger_sync as LS           # noqa: E402

REPO = Path(__file__).resolve().parent.parent

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


# ─────────────────────────────────────────────────────────────────────────────
# C6 fixtures — the float-accumulation census (brick 0d)
# ─────────────────────────────────────────────────────────────────────────────
#
# The census of src/ below was derived BY HAND from the source, with grep, before the AST
# scanner existed. That is the point: if the list were read off the scanner's own output
# it would assert nothing except that the scanner agrees with itself.
#
# path:scope.symbol -> True if the site is math.fsum (exactly rounded), False if naive.
KNOWN_SITES = {
    "src/psyche_activation.py:spread_activation.frozen": True,
    "src/psyche_activation.py:spread_activation.out_total": True,
    "src/psyche_activation.py:spread_activation.activation": True,
    "src/psyche_activation.py:spread_activation.flow": False,
    "src/psyche_coalitions.py:form_coalitions.strength": True,
    "src/psyche_coalitions.py:form_coalitions_from_field.strength": True,
    "src/psyche_field.py:build_activation_field.merged_flow": False,
    "src/psyche_field.py:build_activation_field.total": False,
    "src/psyche_store.py:Clock.advance._t": False,
    "src/psyche_store.py:Road.valence.<return>": True,
    "src/psyche_store.py:SubstrateStore.strengthen.road.strength": False,
    "src/psyche_store.py:SubstrateStore.strengthen.road.charges": False,
    "src/psyche_workspace.py:Broadcast.total_strength_after.<return>": True,
    "src/psyche_workspace.py:select_winner.strength": True,
}

# THE ACCEPTANCE TEST (SPEC-0d F-3). A detector that passes because it found nothing is
# indistinguishable from a detector that is broken, so the only evidence that C6 works is
# a planted defect it catches. Three distinct shapes, because one that catches one shape
# and misses two is worse than none — it will be trusted.
INJECT_DICT_ADD = '''

def _injected_dict_add(items):
    """+= into a dict — psyche_field's shape."""
    bucket = {}
    for k, v in items:
        bucket[k] = bucket.get(k, 0.0) + v
    return bucket
'''

INJECT_RUNNING_LOCAL = '''

def _injected_running_local(values):
    """A running local — the shape the activation engine used to carry."""
    running = 0.0
    for v in values:
        running += v
    return running
'''

INJECT_BUILTIN_SUM = '''

def _injected_builtin_sum(values):
    """The builtin — BUG-0b1's shape, at zero in src/ since 0c."""
    return sum(values)
'''

# adversarial variants: a brand-new module, and a site buried in a nested scope
INJECT_NEW_MODULE = '''"""A module the census has never seen."""


class Accumulator:
    def fold(self, values):
        acc = 0.0
        for v in values:
            acc = acc + v
        return acc
'''

INJECT_LAUNDERED = '''

def _injected_laundered(items):
    """The accumulation hidden by the most natural refactor there is: pull the previous
    value onto its own line, then rename it once."""
    out = {}
    for k, v in items:
        prior = out.get(k, 0.0)
        same = prior
        out[k] = same + v
    return out
'''

# F-4: integer accumulation. math.fsum over ints returns a float and would silently change
# the type, so these must NOT be reported. Every exemption below is STRUCTURAL — an
# int-literal or len() addend — never the identifier's name.
INJECT_INTEGER_TALLIES = '''

def _injected_int_tallies(items):
    creation_seq = 0
    access_count = 0
    traversal_count = {}
    for k in items:
        creation_seq += 1
        access_count += len(k)
        traversal_count[k] = traversal_count.get(k, 0) + 1
    return creation_seq, access_count, traversal_count, sum(1 for _ in items), sum(range(3))
'''

# documented limitations, asserted as negatives so "clean" never quietly means "did not look"
INJECT_MULTIPLICATIVE = '''

def _injected_multiplicative(values):
    scale = 1.0
    for v in values:
        scale *= v
    return scale
'''

INJECT_INTERPROCEDURAL = '''

def _blend_helper(a, b):
    return a + b


def _injected_interprocedural(items):
    out = {}
    for k, v in items:
        prior = out.get(k, 0.0)
        out[k] = _blend_helper(prior, v)
    return out
'''


def make_src_repo(tmp: Path, *, appended: str = "", extra: dict = None,
                  registry=Ellipsis) -> Path:
    """A scratch repository carrying a COPY of the real src/ and the real registry.

    Loop-closure: the detector is driven by the tree the project actually produced, not by
    a hand-written toy. src/ itself is never edited to prove a point."""
    root = tmp / f"srcrepo{len(list(tmp.iterdir()))}"
    (root / "tools").mkdir(parents=True)
    shutil.copytree(REPO / "src", root / "src",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    real = json.loads((REPO / "tools" / "ledger.json").read_text(encoding="utf-8"))
    led = json.loads(json.dumps(BASE_LEDGER))
    led[LC.ACCUM_KEY] = real[LC.ACCUM_KEY] if registry is Ellipsis else registry
    if registry is None:
        led.pop(LC.ACCUM_KEY, None)
    (root / "tools" / "ledger.json").write_text(json.dumps(led, indent=2), encoding="utf-8")
    if appended:
        # APPEND, so no existing line number moves and the only new finding is the planted one
        p = root / "src" / "psyche_field.py"
        p.write_text(p.read_text(encoding="utf-8") + appended, encoding="utf-8")
    for rel, body in (extra or {}).items():
        q = root / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(body, encoding="utf-8")
    return root


def c6(root: Path):
    return LC.check_float_accumulation(root, LC.load_ledger(root))


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

    section("C2 checks the paper, not only Markdown")
    r = make_repo(tmp, files={"docs/paper/paper.tex":
                              "a suite of 618 assertions across 12 suites\n"})
    f = LC.check_prose_vs_ledger(r, LC.load_ledger(r))
    check(len(f) >= 1 and f[0].path.endswith(".tex"), "LaTeX scanned")

    section("C2 reads LaTeX's thin-space comma as the same number")
    led2 = json.loads(json.dumps(BASE_LEDGER))
    led2["tests"]["assertions"] = 1372
    led2["tests"]["per_suite"] = {"test_a.py": 1372}
    led2["tests"]["suites"] = 1
    cap2 = CAPTURE.replace("RESULT: 10 passed, 0 failed", "RESULT: 1372 passed, 0 failed")
    cap2 = cap2.split("# test_b.py")[0]
    r = make_repo(tmp, ledger=led2, capture=cap2,
                  files={"docs/paper/p.tex": "1{,}372 assertions in 1 suite\n"})
    check(LC.check_prose_vs_ledger(r, LC.load_ledger(r)) == [], "1{,}372 parsed as 1372")

    section("C2 honours a LaTeX-comment pragma")
    r = make_repo(tmp, files={"docs/paper/p.tex":
                              "% ledger:allow-count\n618 assertions (historical)\n"})
    check(LC.check_prose_vs_ledger(r, LC.load_ledger(r)) == [], "LaTeX pragma honoured")

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
    r = make_repo(tmp, files={"docs/psyche_roadmap.md": "Step 1c is PROVEN.\n"})
    check(LC.check_status_vocabulary(r, LC.load_ledger(r)) == [], "roadmap exempt")

    # ── C4 ───────────────────────────────────────────────────────────────────
    section("C4 does NOT flag a disclaimer — the real false-positive risk")
    r = make_repo(tmp, files={"R.md": (
        "Psyche is not a validated cognitive model and is not a mind.\n"
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

    section("C2/C4 skip every hidden directory by rule, at any depth, and .git by name")
    r = make_repo(tmp, files={
        ".git/x.md": "It is conscious.\n",
        ".local-tool/notes.md": "It is conscious. The run had 618 assertions.\n",
        ".local-tool/sub/tool.py": '"""This module is a mind."""\n',
        "docs/.cache/y.md": "It is a mind.\n",
    })
    check(LC.check_forbidden_claims(r, LC.load_ledger(r)) == [],
          "no Markdown or Python file under a hidden directory is read by C4")
    check(LC.check_prose_vs_ledger(r, LC.load_ledger(r)) == [],
          "and none is read by C2")
    check(".git" in LC.SKIP_DIRS and LC.in_skipped_dir((".git", "x.md"))
          and LC.in_skipped_dir(("docs", ".cache", "y.md"))
          and not LC.in_skipped_dir(("docs", "y.md")),
          ".git stays named; any hidden component skips; a plain path does not")

    section("C4 still reads a hidden FILE that sits in no hidden directory")
    r = make_repo(tmp, files={"docs/.draft.md": "It is conscious.\n"})
    f = LC.check_forbidden_claims(r, LC.load_ledger(r))
    check(len(f) == 1 and f[0].path == "docs/.draft.md",
          "the rule is about directories: a dot-named file is still governed")

    # ── C5 ───────────────────────────────────────────────────────────────────
    section("C5 passes when every suite on disk is registered")
    r = make_repo(tmp, files={"run_tests.py": 'S = ["test_a.py", "test_b.py"]\n',
                              "tests/test_a.py": "", "tests/test_b.py": ""})
    check(LC.check_runner_completeness(r, LC.load_ledger(r)) == [], "clean C5")

    section("C5 catches the real hole — a suite on disk the runner never runs")
    r = make_repo(tmp, files={"run_tests.py": 'S = ["test_a.py"]\n',
                              "tests/test_a.py": "",
                              "tests/test_tester_0c_adversarial.py": ""})
    f = LC.check_runner_completeness(r, LC.load_ledger(r))
    check(len(f) == 1 and "0c_adversarial" in f[0].message, "unregistered suite caught")

    section("C5 honours a deliberately-excused suite")
    led5 = json.loads(json.dumps(BASE_LEDGER))
    led5["unregistered_suites"] = {"test_priming.py": "needs the uncommitted SWOW file"}
    r = make_repo(tmp, ledger=led5,
                  files={"run_tests.py": 'S = ["test_a.py"]\n', "tests/test_a.py": "",
                         "experiments/test_priming.py": ""})
    check(LC.check_runner_completeness(r, LC.load_ledger(r)) == [], "excused suite honoured")

    section("C5 catches a registered suite that no longer exists")
    r = make_repo(tmp, files={"run_tests.py": 'S = ["test_a.py", "test_gone.py"]\n',
                              "tests/test_a.py": ""})
    f = LC.check_runner_completeness(r, LC.load_ledger(r))
    check(any("does not exist" in x.message for x in f), "phantom registration caught")

    section("C5 catches a stale excuse")
    led5 = json.loads(json.dumps(BASE_LEDGER))
    led5["unregistered_suites"] = {"test_vanished.py": "reason"}
    r = make_repo(tmp, ledger=led5,
                  files={"run_tests.py": 'S = ["test_a.py"]\n', "tests/test_a.py": ""})
    f = LC.check_runner_completeness(r, LC.load_ledger(r))
    check(any("stale" in (x.fix or "") for x in f), "stale excuse caught")

    # ── C6 — the float-accumulation census (brick 0d) ────────────────────────
    section("C6/F-1 the census finds every accumulation known to be in src/")
    sites, problems = LC.scan_float_accumulations(REPO)
    check(problems == [], "every module under src/ parsed")
    by_key = {s.key: s for s in sites}
    for key, is_fsum in sorted(KNOWN_SITES.items()):
        check(key in by_key, f"census reports {key}")
        if key in by_key:
            check(by_key[key].exact is is_fsum,
                  f"{key} classified {'fsum' if is_fsum else 'naive'}")
    check(sum(1 for s in sites if not s.exact) >= 6, "at least the six naive sites found")

    section("C6/F-1 the census is not keyed by line number (it must survive an insertion)")
    check(bool(sites) and all(":" in s.key and not s.key.rsplit(":", 1)[1].isdigit()
                              for s in sites),
          "keys are <path>:<scope>.<symbol>, not <path>:<line>")

    section("C6/F-2 with the registry populated, the real repository reports nothing")
    check(c6(REPO) == [], "zero unregistered candidates in src/")

    section("C6/F-2 the scratch copy of src/ is clean too (the fixture is trustworthy)")
    base = make_src_repo(tmp)
    check(c6(base) == [], "copied tree with the copied registry is clean")

    # ── F-3: THE ACCEPTANCE TEST. Everything above can be satisfied by a check that
    # always returns 'clean'; only a planted defect distinguishes a detector from a ritual.
    section("C6/F-3 INJECTION shape 1 of 3 — += into a dict")
    r = make_src_repo(tmp, appended=INJECT_DICT_ADD)
    f = c6(r)
    check(len(f) == 1, f"exactly one finding, got {len(f)}")
    check(any("_injected_dict_add.bucket" in x.message for x in f), "names the planted site")
    check(bool(f) and all(x.check == "C6" for x in f), "reported under C6")
    check(LC.main(["--root", str(r), "--only", "C6", "--quiet"]) == 1, "the build goes RED")

    section("C6/F-3 INJECTION shape 2 of 3 — a running local")
    r = make_src_repo(tmp, appended=INJECT_RUNNING_LOCAL)
    f = c6(r)
    check(len(f) == 1, f"exactly one finding, got {len(f)}")
    check(any("_injected_running_local.running" in x.message for x in f), "names the site")
    check(LC.main(["--root", str(r), "--only", "C6", "--quiet"]) == 1, "the build goes RED")

    section("C6/F-3 INJECTION shape 3 of 3 — the builtin sum over floats")
    r = make_src_repo(tmp, appended=INJECT_BUILTIN_SUM)
    f = c6(r)
    check(len(f) == 1, f"exactly one finding, got {len(f)}")
    check(any("_injected_builtin_sum.<return>" in x.message for x in f), "names the site")
    check(any("builtin-sum" in x.message for x in f), "reported as the builtin shape")
    check(LC.main(["--root", str(r), "--only", "C6", "--quiet"]) == 1, "the build goes RED")

    section("C6/F-3 all three shapes at once are all three reported")
    r = make_src_repo(tmp,
                      appended=INJECT_DICT_ADD + INJECT_RUNNING_LOCAL + INJECT_BUILTIN_SUM)
    f = c6(r)
    check(len(f) == 3, f"three findings, got {len(f)}")
    check(len({x.line for x in f}) == 3, "three distinct sites, not one counted thrice")

    section("C6/F-3 a brand-new module, and a site nested in a method")
    r = make_src_repo(tmp, extra={"src/psyche_injected.py": INJECT_NEW_MODULE})
    f = c6(r)
    check(len(f) == 1, f"the census is not limited to the modules it knows, got {len(f)}")
    check(any("Accumulator.fold.acc" in x.message for x in f),
          "nested class/method scope is keyed correctly")

    section("C6/F-3 an accumulation laundered through a renamed temporary")
    r = make_src_repo(tmp, appended=INJECT_LAUNDERED)
    f = c6(r)
    check(len(f) == 1, f"one-hop laundering does not evade the census, got {len(f)}")
    check(any("_injected_laundered.out" in x.message for x in f), "names the site")

    section("C6/F-3 the gate is red for a MISSING registry as well as a missing entry")
    r = make_src_repo(tmp, registry=None)
    f = c6(r)
    check(len(f) >= len(KNOWN_SITES), "no registry at all reports every site")
    check(any("no 'float_accumulations' key" in x.message.replace('"', "'") for x in f),
          "the absent key is itself the finding")

    # ── F-4: no false positives on integer accumulation ──────────────────────
    section("C6/F-4 integer tallies are NOT reported (fsum over ints would change the type)")
    r = make_src_repo(tmp, appended=INJECT_INTEGER_TALLIES)
    check(c6(r) == [], "creation_seq / access_count / traversal_count / sum(1 ...) all clean")

    section("C6/F-4 the integer counters already in src/ are absent from the census")
    names = {s.key for s in sites}
    for banned in ("traversal_count", "access_count", "_cursor"):
        check(bool(names) and not any(banned in k for k in names),
              f"{banned} not a candidate")

    section("C6/F-4 the exemption is structural, not name-based")
    r = make_src_repo(tmp, appended=(
        "\n\ndef _injected_float_named_count(items):\n"
        "    access_count = 0.0\n"
        "    for v in items:\n"
        "        access_count += v\n"
        "    return access_count\n"))
    f = c6(r)
    check(len(f) == 1, "a FLOAT accumulator named like a counter is still reported")

    # ── F-5: a registry that can rot silently is a note again ────────────────
    section("C6/F-5 a stale entry naming a site that no longer exists is a finding")
    reg = dict(json.loads((REPO / "tools" / "ledger.json").read_text())[LC.ACCUM_KEY])
    reg["src/psyche_gone.py:vanished.total"] = {"verdict": "registered",
                                              "reason": "a site that was deleted long ago"}
    r = make_src_repo(tmp, registry=reg)
    f = c6(r)
    check(len(f) == 1 and "no longer exists" in f[0].message, "stale entry caught")

    section("C6/F-5 a verdict that no longer matches the source is a finding")
    reg = dict(json.loads((REPO / "tools" / "ledger.json").read_text())[LC.ACCUM_KEY])
    reg["src/psyche_field.py:build_activation_field.total"] = {
        "verdict": "fsum", "reason": "claims to be exactly rounded, and is not"}
    r = make_src_repo(tmp, registry=reg)
    f = c6(r)
    check(any("no longer describes the code" in x.message for x in f),
          "a naive site registered as fsum is caught")

    section("C6/F-5 a site converted to fsum but still registered as naive is a finding")
    reg = dict(json.loads((REPO / "tools" / "ledger.json").read_text())[LC.ACCUM_KEY])
    reg["src/psyche_coalitions.py:form_coalitions.strength"] = {
        "verdict": "registered", "reason": "stale: this site was converted by BUG-0b1"}
    r = make_src_repo(tmp, registry=reg)
    f = c6(r)
    check(any("but the site is now math.fsum" in x.message for x in f),
          "an fsum site registered as naive is caught")

    section("C6/F-5 an empty or decorative reason is a finding")
    reg = dict(json.loads((REPO / "tools" / "ledger.json").read_text())[LC.ACCUM_KEY])
    reg["src/psyche_field.py:build_activation_field.total"] = {"verdict": "registered",
                                                            "reason": "it is fine"}
    r = make_src_repo(tmp, registry=reg)
    f = c6(r)
    check(any("is an approval, not an adjudication" in x.message for x in f),
          "a reason too short to be checkable is caught")

    section("C6/F-5 an unknown verdict is a finding")
    reg = dict(json.loads((REPO / "tools" / "ledger.json").read_text())[LC.ACCUM_KEY])
    reg["src/psyche_field.py:build_activation_field.total"] = {
        "verdict": "safe", "reason": "there is no 'safe' verdict; shape-present is not safe"}
    r = make_src_repo(tmp, registry=reg)
    f = c6(r)
    check(any("is not one of" in x.message for x in f), "vocabulary enforced")

    # ── F-7: ASSERTED NEGATIVE — 0d fixed nothing, and the record must not drift ──
    section("C6/F-7 ASSERTED NEGATIVE: psyche_field.py's two sites are STILL naive after 0d")
    field_src = (REPO / "src" / "psyche_field.py").read_text(encoding="utf-8")
    check("total[node] = total.get(node, 0.0) + act" in field_src,
          "field.total is still a naive accumulation in the source")
    check("merged_flow[rid] = merged_flow.get(rid, 0.0) + fv" in field_src,
          "field.merged_flow is still a naive accumulation in the source")
    total_site = by_key.get("src/psyche_field.py:build_activation_field.total")
    check(total_site is not None and total_site.exact is False,
          "the census still classifies field.total as naive")
    entry = (LC.load_ledger(REPO)[LC.ACCUM_KEY] or {}).get(
        "src/psyche_field.py:build_activation_field.total") or {}
    check(entry.get("verdict") == "registered", "field.total is registered, not converted")
    check("order-PINNED" in (entry.get("reason") or ""),
          "its reason states the order-pinned argument, not a safety claim")
    # This block goes RED when a later brick converts the site. That is the correct signal:
    # that brick re-verifies here rather than silently inheriting 0d's record.

    # ── F-8: ASSERTED NEGATIVE — the scope boundary, stated so it is never overread ──
    section("C6/F-8 ASSERTED NEGATIVE: the census scans src/ ONLY")
    r = make_src_repo(tmp, extra={
        "tools/helper.py": INJECT_RUNNING_LOCAL,
        "tests/test_thing.py": INJECT_DICT_ADD,
        "experiments/harness.py": INJECT_BUILTIN_SUM})
    check(c6(r) == [],
          "accumulations in tools/, tests/ and experiments/ are NOT claimed by this gate")

    section("C6/F-8 ASSERTED NEGATIVE: multiplicative folds are not detected")
    r = make_src_repo(tmp, appended=INJECT_MULTIPLICATIVE)
    check(c6(r) == [], "`scale *= v` is equally order-sensitive and is out of scope")

    section("C6/F-8 ASSERTED NEGATIVE: an add moved into a helper is not detected")
    r = make_src_repo(tmp, appended=INJECT_INTERPROCEDURAL)
    check(c6(r) == [], "the census does no interprocedural analysis")

    # ── D-021 FIX 4: the remaining eight holes, each ASSERTED so that "the detector
    # is clean" can never quietly mean "the detector did not look". None is implemented
    # in this cycle BY DECISION: whether any is worth detecting is a scoping call, and a
    # gate that never ships because it is still being perfected guarded nothing. Each
    # carries the falsifier from ledger_check.py's scope block.
    section("C6/F-8 ASSERTED NEGATIVES: the known holes — L3 CONVERTED OUT of this list")
    # L3 was here. It is gone from this block because the hole is CLOSED (D-025), not
    # because the assertion was inconvenient: its replacement is the POSITIVE assertion
    # above, which fails if the capability regresses. A limitation leaves this list only
    # by being closed and asserted positively somewhere else.
    for label, src in (
        ("L2 walrus",
         "def f(xs):\n    a = 0.0\n    for x in xs:\n        if (a := a + x) > 1.0:\n"
         "            pass\n    return a\n"),
        ("L4 itertools.accumulate",
         "import itertools\ndef f(xs):\n    return list(itertools.accumulate(xs))\n"),
        ("L5 operator.add called directly in a loop",
         "import operator\ndef f(xs):\n    a = 0.0\n    for x in xs:\n"
         "        a = operator.add(a, x)\n    return a\n"),
        ("L6 reduce with the __add__ dunder spelling",
         "import functools, operator\ndef f(xs):\n"
         "    return functools.reduce(operator.__add__, xs, 0.0)\n"),
        ("L7 float accumulator with an int-literal addend",
         "def f(n):\n    weight = 0.0\n    for _ in range(n):\n        weight += 1\n"
         "    return weight\n"),
        ("L9 math.sumprod",
         "import math\ndef f(xs, ys):\n    return math.sumprod(xs, ys)\n"),
        ("L10 Counter.update",
         "import collections\ndef f(xs):\n    c = collections.Counter()\n"
         "    for x in xs:\n        c.update({'k': x})\n    return c\n"),
    ):
        found = LC.scan_source(src, "src/p.py")
        check(found == [],
              f"{label} is NOT detected — a documented hole with a falsifier, asserted here "
              f"so the gate's silence about it is deliberate rather than accidental")
    # and the one that IS now detected, so this block cannot rot into covering everything
    check([s.kind for s in LC.scan_source(
        "def f(xs):\n    a = 0.0\n    for x in xs:\n        a -= x\n    return a\n",
        "src/p.py")] == ["aug-sub"],
        "L-subtraction is NOT in this list because D-021 FIX 1 closed it — the block "
        "asserts holes, and a hole that has been filled must leave it")

    # ── D-021 FIX 1: subtraction is DETECTED, and the reflection form is not ────
    section("C6 subtraction is an additive fold and IS detected (D-021 FIX 1)")
    check([s.kind for s in LC.scan_source(
        "def f(xs):\n    a = 0.0\n    for x in xs:\n        a -= x\n    return a\n",
        "src/p.py")] == ["aug-sub"],
        "`a -= x` is `a += (-x)` and is exactly as order-sensitive — detected as aug-sub")
    check([s.kind for s in LC.scan_source(
        "def f(d, k, v):\n    d[k] = d.get(k, 0.0) - v\n", "src/p.py")] == ["self-sub"],
        "the self-referential subtraction form is detected too")
    check(LC.scan_source(
        "def f(v, x):\n    x = v - x\n    return x\n", "src/p.py") == [],
        "`x = v - x` REFLECTS rather than accumulates — deliberately not counted, and this "
        "is the asymmetry that makes subtraction left-operand-only")
    check(LC.scan_source(
        "def f(xs):\n    n = 0\n    for x in xs:\n        n -= 1\n    return n\n",
        "src/p.py") == [],
        "an integer tally that subtracts is still exempt — the structural rule holds for Sub")

    # ── D-025 / SPEC-2f STEP ZERO: tuple-target accumulation is DETECTED ───────
    section("C6 tuple-target accumulation is seen (SPEC-2f STEP ZERO, L3 CLOSED)")
    # THE line brick 2f will write. Before this it scored ZERO while the same accumulation
    # split over two statements was caught — the gate was blind at the point of use.
    IDIOM = ("def f(trace, counts, rid, e):\n"
             "    trace[rid], counts[rid] = trace[rid] + e, counts[rid] + 1\n")
    got = LC.scan_source(IDIOM, "src/p.py")
    check([(s.kind, s.symbol) for s in got] == [("self-add", "trace")],
          "the idiomatic 2f line is SEEN: the float accumulation into `trace` is reported, "
          "and the integer counter stays out of scope (L7 — not a hole)")
    split = ("def f(trace, counts, rid, e):\n"
             "    trace[rid] = trace[rid] + e\n"
             "    counts[rid] = counts[rid] + 1\n")
    check([(s.kind, s.symbol) for s in LC.scan_source(split, "src/p.py")]
          == [(s.kind, s.symbol) for s in got],
          "and it now agrees with the same computation split across two statements — the "
          "syntax no longer decides whether the gate can see the arithmetic")
    check([(s.kind, s.symbol) for s in LC.scan_source(
        "def f(xs):\n    a=b=0.0\n    for x, y in xs:\n        a, b = a + x, b + y\n",
        "src/p.py")] == [("self-add", "a"), ("self-add", "b")],
        "TWO accumulating targets on one line are TWO findings, not one — each element is "
        "an independent site")
    check([(s.kind, s.symbol) for s in LC.scan_source(
        "def f(xs):\n    a=b=0.0\n    for x, y in xs:\n        [a, b] = [a + x, b - y]\n",
        "src/p.py")] == [("self-add", "a"), ("self-sub", "b")],
        "list-target syntax is the same shape and is covered; the Sub asymmetry carries "
        "through the elementwise path unchanged")
    check(LC.scan_source(
        "def f(xs):\n    a=b=0.0\n    for x, y in xs:\n        a, b = x - a, y + b\n",
        "src/p.py") == [("self-add", "b")] or
        [s.kind for s in LC.scan_source(
            "def f(xs):\n    a=b=0.0\n    for x, y in xs:\n        a, b = x - a, y + b\n",
            "src/p.py")] == ["self-add"],
        "`a` REFLECTS (x - a) and is correctly not counted while `b` accumulates — the "
        "left-operand-only rule for Sub is enforced per ELEMENT, not per statement")

    section("C6 the tuple path cannot double-count (self-audit item 2, asserted)")
    # A chained assignment gives the tuple path TWO target lists against ONE value tuple.
    # `a` and `b` self-read; `c` and `d` do not. Two findings, not four, and not two-of-the-
    # same — the risk a list-returning accumulator introduces is exactly this.
    chained = LC.scan_source(
        "def f(x, y):\n    a=b=c=d=0.0\n    a, b = c, d = x + a, y + b\n", "src/p.py")
    keys = [(s.line, s.col, s.kind, s.symbol) for s in chained]
    check(sorted(s.symbol for s in chained) == ["a", "b"],
          "chained tuple targets report only the elements that self-read (a, b) — c and d "
          "receive the same values but read nothing of their own")
    check(len(set(keys)) == len(keys),
          "and no (line, col, kind, symbol) is emitted twice — the list-returning form "
          "introduced the double-count risk and this is the guard against it")
    check(len(LC.scan_source("def f(d, k, v):\n    d[k] = d.get(k, 0.0) + v\n",
                             "src/p.py")) == 1,
          "the single-target path is untouched and still first-match-wins: the tuple path "
          "is ADDITIVE, and a statement takes one path or the other, never both")

    # FINDING 2f-0-1 (tester). The guard above was verified on a fixture with DISTINCT names
    # and holds only for that. When the names repeat, one accumulation was emitted twice —
    # and `scan_source`'s dedup renamed the surplus to `<key>#2`, so the census grew a
    # PHANTOM SITE that someone would then write a reason for. A registry that invents work
    # is worse than one that misses it, because a false reason enters the record.
    repeated = LC.scan_source(
        "def f(x, y):\n    a=b=0.0\n    a, b = a, b = x + a, y + b\n", "src/p.py")
    rkeys = [(s.line, s.col, s.kind, s.symbol) for s in repeated]
    check(len(repeated) == 2 and len(set(rkeys)) == 2,
          f"REPEATED names across chained sequence targets are folded ONCE: "
          f"`a, b = a, b = ...` reports {len(repeated)} (was 4, at 2 distinct keys)")
    dup_sub = LC.scan_source("def f(d, k, x, y):\n    d[k], d[k] = d[k] + x, d[k] + y\n",
                             "src/p.py")
    check(len(dup_sub) == 1,
          f"and a repeated SUBSCRIPT inside one target list is one site, not two "
          f"(got {len(dup_sub)}) — the same write spelled twice is one adjudication")
    check(not any(s.key.endswith("#2") for s in
                  LC.scan_source("def f(x, y):\n    a=b=0.0\n"
                                 "    a, b = a, b = x + a, y + b\n", "src/p.py")),
          "THE DAMAGE, asserted directly: no `#2` phantom key survives into the census")
    # The dedup is on the target's STRUCTURE, not on its symbol — the distinction that keeps
    # this fix from becoming a coverage loss.
    distinct = LC.scan_source("def f(d, i, j, x, y):\n    d[i], d[j] = d[i] + x, d[j] + y\n",
                              "src/p.py")
    split_eq = LC.scan_source("def f(d, i, j, x, y):\n    d[i] = d[i] + x\n"
                              "    d[j] = d[j] + y\n", "src/p.py")
    check(len(distinct) == 2 and len(distinct) == len(split_eq),
          f"`d[i], d[j] = ...` stays TWO sites ({len(distinct)}) and still agrees with the "
          f"same code split across two statements ({len(split_eq)}) — deduping on the symbol "
          f"alone would have collapsed these and made the tuple form report less than the "
          f"split form, which is the exact property closing L3 existed to establish")

    section("C6 refusals are VISIBLE, not silent (FINDING 2f-0-2)")
    # THE LINE: anything the scanner KNOWINGLY DECLINES is recorded; anything it simply
    # never matched stays a documented limitation. L1's multiplicative shape never matches
    # and is unchanged. L11-L13 and arity are decisions taken with full sight of a sequence
    # assignment, and those are recorded.
    for label, src, rule in (
        ("L11 starred", "def f(x, r):\n    a=b=0.0\n    a, *b = x + a, r\n", "L11"),
        ("L12 nested",
         "def f(x, y):\n    a=b=c=0.0\n    (a, b), c = (a + x, b + y), c + x\n", "L12"),
        ("L13 non-literal RHS", "def f(x):\n    a=b=0.0\n    a, b = g(a + x, b + x)\n", "L13"),
        ("arity mismatch", "def f(x):\n    a=b=0.0\n    a, b = (a + x,)\n", "arity"),
    ):
        refs = LC.scan_source_refusals(src, "src/p.py")
        check([r.rule for r in refs] == [rule],
              f"the decline is RECORDED and named: {label} -> {rule}")
        check(LC.scan_source(src, "src/p.py") == [],
              f"and it is still not a SITE — a refusal is not a finding: {label}")
        check(refs[0].line == 3 or refs[0].line == 2,
              f"with a line number a reader can go to: {label} at line {refs[0].line}")
    # The discriminator that motivated the finding: silence must no longer be ambiguous.
    empty = "def f():\n    pass\n"
    check(LC.scan_source_refusals(empty, "src/p.py") == [],
          "a file with NOTHING in it records NO refusal — so `[]` from the refusal scan "
          "now means 'nothing here' and never 'I could not look'")
    check(LC.scan_source_refusals("def f():\n    a = g()\n", "src/p.py") == [],
          "and a plain `a = g()` is NOT a decline — it is the ordinary single-target path. "
          "Recording it would make every assignment in src/ a refusal and the signal would "
          "be worthless within one commit")
    check(LC.scan_source_refusals(
        "def f(xs):\n    a=1.0\n    for x in xs:\n        a = a * x\n", "src/p.py") == [],
        "L1's multiplicative shape records NOTHING: the scanner never matched it, so it has "
        "nothing to declare. That is the line, and it is held exactly here")

    section("C6 --list-accumulations SURFACES refusals without polluting the census")
    # SELF-AUDIT ITEM 7, and it caught a real break. This CLI contract was asserted ONLY in
    # the tester's suite, so when the first version of this fix printed refusal lines
    # beginning with their path, nothing here went red — the tester's loop-closed test found
    # it. The listing is CONSUMED, not merely read: it is fed back as a registry, and every
    # line starting with `src/` is taken as a key. A refusal printed into that namespace
    # would have handed the census two phantom keys, which is the very defect being fixed.
    proc = subprocess.run([sys.executable, str(REPO / "tools" / "ledger_check.py"),
                           "--root", str(REPO), "--list-accumulations"],
                          capture_output=True, text=True)
    check(proc.returncode == 0, f"the listing exits 0 (got {proc.returncode})")
    lines = proc.stdout.splitlines()
    site_lines = [ln for ln in lines if ln.startswith("src/")]
    ref_lines = [ln for ln in lines if ln.startswith("REFUSED")]
    check(len(site_lines) == len(LC.scan_float_accumulations(REPO)[0]),
          f"every `src/`-prefixed line is a SITE and there are exactly as many as the census "
          f"has ({len(site_lines)}) — the consumed namespace belongs to sites alone")
    check(all(not ln.startswith("src/") for ln in ref_lines) and len(ref_lines) >= 1,
          f"refusals are printed ({len(ref_lines)}) and NONE of them begins with `src/`, so "
          f"feeding this output back as a registry cannot invent a key")
    census_keys = {s.key for s in LC.scan_float_accumulations(REPO)[0]}
    check({ln.split()[-1] for ln in site_lines} == census_keys,
          "the last token of every site line IS a census key — which is the contract the "
          "loop-closed feed-back relies on, asserted here rather than only downstream")
    check(all(any(f"{r.path}:{r.line}" in ln for r in LC.scan_float_refusals(REPO))
              for ln in ref_lines),
          "and each refusal line names a real file:line a reader can open")
    summary = [ln for ln in lines if "site(s) in" in ln]
    check(len(summary) == 1 and "refusal(s)" in summary[0],
          f"the summary line reports BOTH counts: {summary[0] if summary else '<missing>'}")
    check(f"{len(ref_lines)} refusal(s)" in summary[0],
          "and the refusal count in the summary matches the lines printed — a count that "
          "disagreed with the list would be worse than no count")
    check(any("never fail the build" in ln for ln in lines),
          "the listing states in words that a refusal is not a finding, so the reader who "
          "sees REFUSED does not go looking for a broken build")

    section("C6/L11-L13 ASSERTED NEGATIVES: the pairings that are REFUSED, not guessed")
    # Pairing is positional, so it is sound only for literal sequences of equal length.
    # Each refusal below is a stated limitation; the flattened control proves it is a REAL
    # hole rather than a property of the computation.
    for label, src in (
        ("L11 starred target",
         "def f(xs):\n    a=0.0\n    b=[]\n    for x in xs:\n        a, *b = a + x, 1, 2\n"),
        ("L11 starred value",
         "def f(xs, r):\n    a=0.0\n    b=0.0\n    for x in xs:\n        a, b = *r, a + x\n"),
        ("L12 nested target",
         "def f(xs):\n    a=b=c=0.0\n    for x in xs:\n"
         "        (a, (b, c)) = (a + x, (b + x, c + x))\n"),
        ("L13 non-literal RHS",
         "def f(xs, g):\n    a=b=0.0\n    for x in xs:\n        a, b = g(a, b, x)\n"),
        ("arity mismatch (a runtime error, NOT a limitation)",
         "def f(xs):\n    a=b=0.0\n    for x in xs:\n        a, b = (a + x,)\n"),
    ):
        check(LC.scan_source(src, "src/p.py") == [],
              f"REFUSED rather than guessed: {label}")
    check([s.symbol for s in LC.scan_source(
        "def f(xs):\n    a=b=0.0\n    for x in xs:\n        a, b = a + x, b + x\n",
        "src/p.py")] == ["a", "b"],
        "and the flattened equivalent IS detected — so L11-L13 are real holes in the "
        "pairing, not properties of the computation being refused")

    # ── D-021 FIX 2: match cases are walked ────────────────────────────────────
    section("C6 statements inside a `match` case are walked (D-021 FIX 2)")
    MATCH_SRC = (
        "def f(cmd, d, k, v):\n"
        "    match cmd:\n"
        "        case 'add':\n"
        "            d[k] = d.get(k, 0.0) + v\n"
        "        case _:\n"
        "            acc = 0.0\n"
        "            for x in v:\n"
        "                acc += x\n"
        "            return acc\n"
    )
    kinds = sorted(s.kind for s in LC.scan_source(MATCH_SRC, "src/p.py"))
    check(kinds == ["aug-add", "self-add"],
          "both accumulations inside match cases are found; before D-021 the walker never "
          "descended into match_case.body and BOTH were invisible")
    check(all(s.scope == "f" for s in LC.scan_source(MATCH_SRC, "src/p.py")),
          "and they are attributed to the enclosing function, not to a phantom scope")
    check([s.kind for s in LC.scan_source(
        "def f(x, xs):\n    match x:\n        case int():\n            return sum(xs)\n",
        "src/p.py")] == ["builtin-sum"],
        "a reducer CALL inside a match case is found (it always was, via the expression "
        "scan — which is exactly why the statement hole was easy to miss)")

    section("C6 every other statement-bearing construct is walked (D-021 FIX 2 audit)")
    for label, body in (
        ("with",        "    with open('x') as fh:\n        a += 1.0\n"),
        ("try",         "    try:\n        a += 1.0\n    except ValueError:\n        pass\n"),
        ("except",      "    try:\n        pass\n    except ValueError:\n        a += 1.0\n"),
        ("try/else",    "    try:\n        pass\n    except ValueError:\n        pass\n    else:\n        a += 1.0\n"),
        ("finally",     "    try:\n        pass\n    finally:\n        a += 1.0\n"),
        ("for/else",    "    for _ in xs:\n        pass\n    else:\n        a += 1.0\n"),
        ("while",       "    while xs:\n        a += 1.0\n"),
        ("if/elif",     "    if xs:\n        pass\n    elif xs:\n        a += 1.0\n"),
        ("nested def",  "    def g():\n        b = 0.0\n        b += 1.0\n        return b\n"),
        ("nested class","    class K:\n        def m(self):\n            c = 0.0\n            c += 1.0\n"),
    ):
        src = f"def f(xs):\n    a = 0.0\n{body}    return a\n"
        check(len(LC.scan_source(src, "src/p.py")) >= 1,
              f"an accumulation inside `{label}` is reached by the walker")
    ASYNC = ("async def f(xs):\n    a = 0.0\n    async with xs as h:\n        a += 1.0\n"
             "    async for x in xs:\n        a += 2.0\n    return a\n")
    check(len(LC.scan_source(ASYNC, "src/p.py")) == 2,
          "async with / async for bodies are walked (async def is handled with def)")

    # ── D-021 FIX 3: unreadable source is exit 2, never a finding, never clean ──
    section("C6 unreadable source is 'the tool could not run' (exit 2), never clean")
    for label, blob in (("NUL byte", b"x = 1\n\x00bad\n"),
                        ("non-UTF-8", b'x = "\xff\xfe"\n'),
                        ("unparseable", b"def f(:\n")):
        r = make_src_repo(tmp)
        (r / "src" / "psyche_bad.py").write_bytes(blob)
        raised = None
        try:
            LC.scan_float_accumulations(r)
        except LC.CensusUnreadable as e:
            raised = e
        check(raised is not None,
              f"{label}: raises CensusUnreadable rather than returning a clean census")
        check(LC.main(["--root", str(r), "--only", "C6", "--quiet"]) == 2,
              f"{label}: exits 2 — NOT 0 (indistinguishable from clean) and NOT 1 (a finding)")

    # ── D-021 ADDITION: absence bounds are machine-verified ────────────────────
    section("C6 a reason resting on an ABSENCE is enforced, not trusted")
    r = make_src_repo(tmp)
    led = json.loads((r / "tools" / "ledger.json").read_text())
    key = next(iter(led["float_accumulations"]))
    led["float_accumulations"][key]["bound_on_absence"] = [
        {"kind": "call", "symbol": "_absent_helper"}]
    (r / "tools" / "ledger.json").write_text(json.dumps(led, indent=2))
    check(not any("RESTS ON THE ABSENCE" in f.message for f in c6(r)),
          "a bound on a symbol that is genuinely absent is silent")
    (r / "src" / "psyche_new.py").write_text("def g():\n    return _absent_helper(1)\n")
    fs = [f for f in c6(r) if "RESTS ON THE ABSENCE" in f.message]
    check(len(fs) == 1 and "the reason is now FALSE" in fs[0].message,
          "the moment the symbol appears, the entry's reason is declared FALSE — the "
          "registry stops being able to hold a silently-stale absence claim")
    led["float_accumulations"][key]["bound_on_absence"][0]["dismissed"] = ["src/psyche_new.py:2"]
    (r / "tools" / "ledger.json").write_text(json.dumps(led, indent=2))
    check(not any("RESTS ON THE ABSENCE" in f.message for f in c6(r)),
          "and a human can dismiss an occurrence only by RECORDING it, in writing")
    check(len(LC._absence_occurrences(REPO, "attribute_read", "ActivationField.flow")) == 2,
          "the real registry's .flow bound over-reports 2 occurrences by design — both "
          "ActivationResult.flow — and both are dismissed in writing (bias: a false "
          "positive costs a sentence, a false negative is a silently false reason)")
    check(LC._absence_occurrences(REPO, "call", "form_coalitions") == []
          and LC._absence_occurrences(REPO, "call", "advance") == [],
          "and the two bounds the registry actually rests on hold today")

    # ── the census's own mechanical properties ───────────────────────────────
    section("C6 the census is deterministic and pure")
    again = {s.key: (s.kind, s.line) for s in LC.scan_float_accumulations(REPO)[0]}
    check(again == {s.key: (s.kind, s.line) for s in sites}, "two scans agree exactly")
    order_a = [s.key for s in sites]
    order_b = [s.key for s in LC.scan_float_accumulations(REPO)[0]]
    check(order_a == order_b, "and agree on ORDER, not just on membership")
    digest = hashlib.sha256(
        (REPO / "tools" / "ledger.json").read_bytes()).hexdigest()
    c6(REPO)
    check(hashlib.sha256((REPO / "tools" / "ledger.json").read_bytes()).hexdigest()
          == digest, "running the check writes nothing to the ledger")

    section("C6 two sites sharing one name stay separately adjudicable")
    twice = LC.scan_source(
        "def f(xs, ys):\n"
        "    t = 0.0\n"
        "    for x in xs:\n"
        "        t += x\n"
        "    for y in ys:\n"
        "        t += y\n"
        "    return t\n", "src/x.py")
    check([s.key for s in twice] == ["src/x.py:f.t", "src/x.py:f.t#2"],
          "the second occurrence is not swallowed by the first")

    section("C6 a src/ module that does not parse is reported, never skipped")
    r = make_src_repo(tmp, extra={"src/psyche_broken.py": "def f(:\n    pass\n"})
    # CONTRACT CHANGED BY D-021 FIX 3. This previously expected a C6 FINDING, i.e. exit 1:
    # "the census ran and the repository is inconsistent". That was wrong — the census did
    # not run. An unparseable module is "the tool could not run", which is exit 2, and the
    # distinction matters because exit 1 quietly asserts that the scan happened.
    raised = None
    try:
        c6(r)
    except LC.CensusUnreadable as e:
        raised = e
    check(raised is not None and "cannot parse" in str(raised),
          "an unparseable module raises CensusUnreadable rather than being reported as a "
          "finding — the census cannot certify a module it never read")
    check(LC.main(["--root", str(r), "--only", "C6", "--quiet"]) == 2,
          "and the process exits 2, never 0 (indistinguishable from clean) and never 1")

    # ── every branch the check owns must be reachable, and shown to be ───────
    section("C6 no statement is visited twice, however deeply it is nested")
    nested = LC.scan_source(
        "import math, statistics\n"
        "class C:\n"
        "    def m(self, rows, xs):\n"
        "        for r in rows:\n"
        "            with open(r) as fh:\n"
        "                try:\n"
        "                    if math.fsum(xs) > 0:\n"
        "                        acc = 0.0\n"
        "                        acc += fh.tell()\n"
        "                except ValueError:\n"
        "                    acc = sum(xs)\n"
        "        return acc\n", "src/n.py")
    check(len(nested) == 3, f"three sites in the nested block, got {len(nested)}")
    check(len({(s.line, s.col, s.kind) for s in nested}) == 3,
          "no site counted twice by the expression scan and the body recursion")
    check({s.kind for s in nested} == {"fsum", "aug-add", "builtin-sum"},
          "each nesting level attributed to the right shape")
    check(len(nested) == 3 and all(s.scope == "C.m" for s in nested),
          "all keyed to the enclosing method")

    section("C6 the other naive reducers are reachable, not just the builtin")
    other = LC.scan_source(
        "import functools, operator, statistics\n"
        "def f(xs):\n"
        "    a = statistics.mean(xs)\n"
        "    b = statistics.fmean(xs)\n"
        "    c = functools.reduce(operator.add, xs, 0.0)\n"
        "    d = functools.reduce(lambda p, q: p + q, xs)\n"
        "    return a, b, c, d\n", "src/n.py")
    check([s.kind for s in other] == ["mean", "fmean", "reduce-add", "reduce-add"],
          f"mean/fmean/reduce-add all detected, got {[s.kind for s in other]}")

    section("C6 a reduce that is not an addition is not an accumulation")
    check(LC.scan_source(
        "import functools\n"
        "def f(ds):\n"
        "    return functools.reduce(lambda a, b: {**a, **b}, ds)\n", "src/n.py") == [],
        "reduce over a non-additive operator is left alone")

    section("C6 more integer evidence: unary, literal arithmetic, literal sequences")
    ints = LC.scan_source(
        "def f(xs):\n"
        "    a = 0\n"
        "    a += -1\n"
        "    a += 2 + 3\n"
        "    b = sum([1, 2, 3])\n"
        "    return a, b\n", "src/n.py")
    check(ints == [], f"integer forms all exempt, got {[s.kind for s in ints]}")

    section("C6 an alias invalidated by reassignment stops being a self-read")
    check(LC.scan_source(
        "def f(items, elsewhere):\n"
        "    out = {}\n"
        "    for k, v in items:\n"
        "        prior = out.get(k, 0.0)\n"
        "        prior = elsewhere\n"
        "        out[k] = prior + v\n"
        "    return out\n", "src/n.py") == [],
        "a rebound temporary no longer stands in for the accumulator")

    section("C6 reducers in a signature default and in an except body are attributed")
    odd = LC.scan_source(
        "W = [1.0]\n"
        "def f(n=sum(W)):\n"
        "    try:\n"
        "        return n\n"
        "    except ValueError:\n"
        "        return sum(W)\n", "src/n.py")
    check(len(odd) == 2, f"both reached, got {len(odd)}")
    check(len(odd) == 2 and odd[0].scope == "" and odd[1].scope == "f",
          "the default is scoped to the module, the handler to the function")

    section("C6 a NESTED subscript accumulator is detected, not dropped for want of a name")
    # This assertion was vacuously true when first written — the site was invisible and
    # `all(... for s in [])` passed. It is now written so an empty census fails it.
    weird = LC.scan_source(
        "def f(xs, d):\n"
        "    (a, b) = (1.0, 2.0)\n"
        "    d[0][1] = d[0][1] + xs[0]\n"
        "    return a, b\n", "src/n.py")
    check([(s.key, s.kind) for s in weird] == [("src/n.py:f.d[]", "self-add")],
          f"grid[i][j] += v is reported, got {[(s.key, s.kind) for s in weird]}")

    section("C6 a tuple target neither crashes nor invents a site")
    check(LC.scan_source("def f():\n    (a, b) = (1.0, 2.0)\n    return a + b\n",
                         "src/n.py") == [], "unnameable target handled")

    section("C6 a malformed registry is a finding, not a crash")
    r = make_src_repo(tmp, registry=["not", "an", "object"])
    f = c6(r)
    check(len(f) == 1 and "must be an object" in f[0].message, "list registry rejected")
    r = make_src_repo(tmp, registry={"src/psyche_field.py:build_activation_field.total":
                                     "a bare string instead of an entry"})
    f = c6(r)
    check(any("must be an object with verdict and reason" in x.message for x in f),
          "a bare-string entry rejected")

    section("C6 a repository with no src/ reports nothing rather than failing")
    r = make_repo(tmp)
    check(LC.scan_float_accumulations(r) == ([], []), "absent src/ handled")

    # ── integrity under a randomized mutation battery ────────────────────────
    section("C6 INTEGRITY: census and registry stay in bijection under 30 mutations")
    import random
    rng = random.Random(20260726)          # fixed seed: the battery is reproducible
    shapes = [("dict-add", INJECT_DICT_ADD, "_injected_dict_add"),
              ("running", INJECT_RUNNING_LOCAL, "_injected_running_local"),
              ("builtin", INJECT_BUILTIN_SUM, "_injected_builtin_sum"),
              ("laundered", INJECT_LAUNDERED, "_injected_laundered"),
              ("integer", INJECT_INTEGER_TALLIES, None),      # contributes 0 findings
              ("multiplicative", INJECT_MULTIPLICATIVE, None)]
    modules = ["psyche_store.py", "psyche_field.py", "psyche_activation.py",
               "psyche_coalitions.py", "psyche_workspace.py", "psyche_perceive.py"]
    battery_ok = True
    battery_planted = 0
    for round_no in range(30):
        r = make_src_repo(tmp)
        expected = 0
        planted = []
        for _ in range(rng.randint(1, 4)):
            name, body, symbol = shapes[rng.randrange(len(shapes))]
            mod = modules[rng.randrange(len(modules))]
            p = r / "src" / mod
            suffix = f"_r{round_no}_{len(planted)}"
            p.write_text(p.read_text(encoding="utf-8")
                         + body.replace("_injected_", f"_injected{suffix}_"),
                         encoding="utf-8")
            if symbol:
                expected += 1
                planted.append(f"_injected{suffix}_{symbol[len('_injected_'):]}")
        battery_planted += expected
        f = c6(r)
        if len(f) != expected or not all(any(s in x.message for x in f) for s in planted):
            battery_ok = False
            print(f"  round {round_no}: expected {expected}, got {len(f)}; planted {planted}")
            break
    check(battery_ok, "every planted accumulation reported exactly once, every round")
    check(battery_planted >= 20,
          f"the battery actually planted accumulations ({battery_planted}); "
          f"a battery that plants nothing proves nothing")

    section("C6 INTEGRITY: the battery actually planted things (a no-op battery proves nothing)")
    r = make_src_repo(tmp)
    for i, (_, body, symbol) in enumerate(shapes):
        p = r / "src" / "psyche_store.py"
        p.write_text(p.read_text(encoding="utf-8") + body.replace("_injected_", f"_i{i}_"),
                     encoding="utf-8")
    f = c6(r)
    check(len(f) == 4, f"the four float shapes fire and the two exempt ones do not, got {len(f)}")

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

    section("ledger_sync does not drop the float-accumulation registry")
    # architect-pm runs the sync at every close-out. If it dropped this key the gate would
    # go red rather than silent, but a gate that trips on its own housekeeping is a gate
    # people route around.
    led6 = json.loads(json.dumps(BASE_LEDGER))
    led6["tests"]["assertions"] = 1
    led6[LC.ACCUM_KEY] = {"src/x.py:f.total": {"verdict": "registered",
                                               "reason": "a reason long enough to be read"}}
    r = make_repo(tmp, ledger=led6)
    check(LS.sync(r, "write") == 0, "sync wrote")
    kept = json.loads((r / "tools" / "ledger.json").read_text(encoding="utf-8"))
    check(kept.get(LC.ACCUM_KEY) == led6[LC.ACCUM_KEY], "the registry survived the sync")

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


    # ═══════════════════════════════════════════════════════════════════════════
    # BRICK 0e — an aborted suite must be VISIBLE, and must never contribute zero
    # ═══════════════════════════════════════════════════════════════════════════
    section("0e  a suite that raises is named, and its count is UNKNOWN not zero")
    import importlib.util
    rt_spec = importlib.util.spec_from_file_location("runner_0e", REPO / "run_tests.py")
    RT = importlib.util.module_from_spec(rt_spec)
    sys.modules["runner_0e"] = RT
    rt_spec.loader.exec_module(RT)

    # THE FIXTURE: a synthetic suite that raises partway. Deliberately synthetic — the
    # live specimen (the tester's 0d suite) is NOT repaired here, because repairing the
    # only reproducer to make one's own work look green destroys the evidence.
    fixture = tmp / "raising_suite.py"
    fixture.write_text(
        "print('  RESULT-ish noise that is not a RESULT line')\n"
        "def a():\n    print('ok')\n"
        "def b():\n    raise KeyError('planted')\n"
        "a()\nb()\n"
        "print('  RESULT: 99 passed, 0 failed')\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(fixture)], capture_output=True, text=True)
    transcript = (r.stdout or "") + (r.stderr or "")
    v = RT.classify(transcript)
    check(v["aborted"] is True,
          "a suite that raises before printing RESULT is classified ABORTED")
    check(v["passed"] is None and v["failed"] is None,
          f"and its counts are None — UNKNOWN, never 0 "
          f"(passed={v['passed']}, failed={v['failed']}). Zero is not a safe default: it "
          f"is a wrong number that sums silently into the headline total, which is how "
          f"this defect hid an entire 334-assertion file")
    check("KeyError" in v["detail"],
          f"the exception TYPE is named: {v['detail']!r}")
    check("raising_suite.py" in v["detail"] and "in b" in v["detail"],
          f"and where it died: {v['detail']!r}")

    clean = RT.classify("stuff\n  RESULT: 12 passed, 3 failed\n")
    check(clean["aborted"] is False and clean["passed"] == 12 and clean["failed"] == 3,
          "a suite that DOES report is unaffected — passed/failed read as before")

    section("0e  neither parser can lose a suite (both arms)")
    GOOD = ("#" * 70 + "\n# test_a.py\n" + "#" * 70 + "\n  RESULT: 10 passed, 0 failed\n"
            + "#" * 70 + "\n# test_b.py\n" + "#" * 70 + "\n  RESULT: 5 passed, 0 failed\n")
    MID = ("#" * 70 + "\n# test_a.py\n" + "#" * 70 + "\nKeyError: boom\n"
           + "#" * 70 + "\n# test_b.py\n" + "#" * 70 + "\n  RESULT: 5 passed, 0 failed\n")
    LAST = ("#" * 70 + "\n# test_a.py\n" + "#" * 70 + "\n  RESULT: 10 passed, 0 failed\n"
            + "#" * 70 + "\n# test_b.py\n" + "#" * 70 + "\nRuntimeError: died late\n")

    import capture_run as CR
    per, ab = CR.parse_full(GOOD)
    check(per == {"test_a.py": 10, "test_b.py": 5} and ab == [],
          "capture_run: a clean capture parses unchanged")
    per, ab = CR.parse_full(MID)
    check(ab == ["test_a.py"],
          f"capture_run: a MID-FILE abort is reported, not overwritten by the next "
          f"header (got {ab})")
    per, ab = CR.parse_full(LAST)
    check(ab == ["test_b.py"],
          f"capture_run: a LAST-SUITE abort is reported too — the arm no later header "
          f"can reveal, and the one a mid-file-only fix would still lose (got {ab})")

    section("0e  a malformed capture is EXIT 2, not a finding and never exit 0")
    def cap_root(text):
        d = Path(tempfile.mkdtemp(prefix="cap0e-"))
        (d / "docs").mkdir(); (d / "tools").mkdir()
        (d / "docs" / "TEST_OUTPUT.txt").write_text(text, encoding="utf-8")
        (d / "tools" / "ledger.json").write_text(json.dumps(
            {"tests": {"suites": 2, "assertions": 15, "failures": 0,
                       "per_suite": {"test_a.py": 10, "test_b.py": 5}}}), encoding="utf-8")
        return d
    ok = LC.parse_capture(cap_root(GOOD))
    check(ok["suites"] == 2 and ok["assertions"] == 15,
          "a clean capture still parses to the same numbers")
    for label, text, missing in (("mid-file", MID, "test_a.py"), ("last", LAST, "test_b.py")):
        try:
            LC.parse_capture(cap_root(text))
            check(False, f"{label} abort should raise CaptureMalformed")
        except LC.CaptureMalformed as e:
            check(missing in str(e),
                  f"{label} abort raises CaptureMalformed naming {missing}")
    # and the exit code, end to end through the CLI
    d = cap_root(MID)
    rc = subprocess.run([sys.executable, str(REPO / "tools" / "ledger_check.py"),
                         "--root", str(d), "--only", "C1"],
                        capture_output=True, text=True)
    check(rc.returncode == 2,
          f"ledger_check exits 2 on a malformed capture (got {rc.returncode}) — the "
          f"CensusUnreadable ruling, for the same reason: a finding would claim the "
          f"tool's numbers are sound and the repo is not, but here the NUMBERS are what "
          f"cannot be trusted. Exit 0 was the old behaviour and was the worst of the three")
    check("malformed" in (rc.stderr or "").lower(), "and says so on stderr")
    rs = subprocess.run([sys.executable, str(REPO / "tools" / "ledger_sync.py"),
                         "--root", str(d)], capture_output=True, text=True)
    check(rs.returncode == 2,
          f"ledger_sync REFUSES too (got {rs.returncode}) — it writes the headline "
          f"figure, so syncing from an incomplete capture is how a wrong number becomes "
          f"canonical")

    section("0e  all THREE readers of the format agree on the same line")
    # A runner that summed the last RESULT while the capture parser summed the first
    # would disagree only on malformed input — precisely the case nobody exercises, and
    # precisely the input this brick is about. Pinned so they cannot drift apart.
    twice = ("#" * 70 + "\n# test_a.py\n" + "#" * 70
             + "\n  RESULT: 3 passed, 0 failed\n  RESULT: 7 passed, 0 failed\n")
    check(RT.classify(twice)["passed"] == 3, "run_tests.classify takes the FIRST RESULT")
    check(CR.parse_full(twice)[0] == {"test_a.py": 3},
          "capture_run.parse_full takes the FIRST RESULT")
    d2 = cap_root(twice)
    check(LC.parse_capture(d2)["assertions"] == 3,
          "ledger_check.parse_capture takes the FIRST RESULT — all three agree, so no "
          "malformed input can make the runner and the capture disagree on a count")

    section("0e  RULE FOUR: every assertion above FAILS against the pre-fix code")
    # An assertion that passes on both sides of a fix is evidence for nothing. Each claim
    # is re-run against the tools as they stood at HEAD~ (the commit before this fix) and
    # is required to fail there.
    old_dir = Path(tempfile.mkdtemp(prefix="prefix0e-"))
    got_old = {}
    for name in ("run_tests.py", "tools/capture_run.py", "tools/ledger_check.py"):
        g = subprocess.run(["git", "show", f"a336d2e:{name}"], cwd=str(REPO),
                           capture_output=True, text=True)
        if g.returncode == 0:
            (old_dir / Path(name).name).write_text(g.stdout, encoding="utf-8")
            got_old[Path(name).name] = True
    if len(got_old) == 3:
        def load_old(fname, modname):
            sp = importlib.util.spec_from_file_location(modname, old_dir / fname)
            m = importlib.util.module_from_spec(sp); sys.modules[modname] = m
            sp.loader.exec_module(m); return m
        old_rt = load_old("run_tests.py", "old_rt_0e")
        check(not hasattr(old_rt, "classify"),
              "LIVE: the pre-fix runner has no classify() at all — an aborted suite was "
              "never classified, only silently skipped")
        old_cr = load_old("capture_run.py", "old_cr_0e")
        check(not hasattr(old_cr, "parse_full"),
              "LIVE: the pre-fix capture_run has no parse_full()")
        check(old_cr.parse(MID) == {"test_b.py": 5},
              f"LIVE: and its parse() SILENTLY DROPS the aborted suite — "
              f"{old_cr.parse(MID)}, with test_a.py simply gone and no error")
        check(old_cr.parse(LAST) == {"test_a.py": 10},
              "LIVE: the last-suite arm is lost too, with nothing to notice it")
        old_lc = load_old("ledger_check.py", "old_lc_0e")
        check(not hasattr(old_lc, "CaptureMalformed"),
              "LIVE: the pre-fix ledger_check has no CaptureMalformed")
        old_cap = old_lc.parse_capture(cap_root(MID))
        check(old_cap["suites"] == 1 and old_cap["assertions"] == 5,
              f"LIVE, AND THIS IS THE DEFECT ITSELF: the pre-fix parser returns "
              f"{old_cap['suites']} suite / {old_cap['assertions']} assertions for a "
              f"capture that names two — a clean, confident, WRONG number, with no error "
              f"and no way for any caller to tell")
    else:
        check(False, "could not recover the pre-fix tools from git for the two-sided proof")
    shutil.rmtree(old_dir, ignore_errors=True)


    # ═══════════════════════════════════════════════════════════════════════════
    # BRICK 0g — the dismissal key is stable under irrelevant edits, unstable
    #            under relevant ones. Both halves asserted; neither assumed.
    # ═══════════════════════════════════════════════════════════════════════════
    section("0g  dismissal keys: STABLE under irrelevant edits, UNSTABLE under relevant")

    def c6_on(mutate, use_rev=None):
        """Run C6 over a copied tree, optionally with a tool recovered from `use_rev`."""
        d = Path(tempfile.mkdtemp(prefix="0g-"))
        shutil.copytree(REPO / "src", d / "src")
        (d / "tools").mkdir()
        shutil.copy(REPO / "tools" / "ledger.json", d / "tools" / "ledger.json")
        mutate(d)
        tool = str(REPO / "tools" / "ledger_check.py")
        if use_rev:
            g = subprocess.run(["git", "show", f"{use_rev}:tools/ledger_check.py"],
                               cwd=str(REPO), capture_output=True, text=True)
            if g.returncode != 0:
                shutil.rmtree(d, ignore_errors=True)
                return None
            (d / "old_lc.py").write_text(g.stdout, encoding="utf-8")
            tool = str(d / "old_lc.py")
        r = subprocess.run([sys.executable, tool, "--root", str(d), "--only", "C6"],
                           capture_output=True, text=True)
        shutil.rmtree(d, ignore_errors=True)
        return r

    def add_comment(d):
        f = d / "src" / "psyche_field.py"
        f.write_text("# a harmless comment\n" + f.read_text(encoding="utf-8"),
                     encoding="utf-8")

    # CONTROL FIRST. Without it every result below is unreadable.
    base = c6_on(lambda d: None)
    check(base.returncode == 0,
          f"CONTROL: an unmutated tree is clean (exit {base.returncode}) — otherwise every "
          f"mutation result below would be noise")

    # DIRECTION 1 — irrelevant edit: dismissals must HOLD.
    r = c6_on(add_comment)
    check(r.returncode == 0 and "RESTS ON THE ABSENCE" not in r.stdout,
          f"a comment inserted at the top of psyche_field.py produces NO finding "
          f"(exit {r.returncode}) — the key ignores line position, which is the whole "
          f"defect this brick closes")
    # RULE FOUR: the same edit against the pre-fix tool must go RED, or the assertion
    # above is not evidence of anything.
    old = c6_on(add_comment, use_rev="62f2382")
    if old is None:
        note("pre-fix tool unavailable from git; the two-sided proof was skipped")
    else:
        check(old.returncode == 1 and "RESTS ON THE ABSENCE" in old.stdout,
              "LIVE: the SAME one-comment edit fires a false [C6] on the pre-fix tool "
              "(62f2382). One comment line was the entire reproducer")

    # DIRECTION 2 — the dismissed EXPRESSION changes: the dismissal must STOP applying.
    def change_expr(d):
        f = d / "src" / "psyche_field.py"
        t = f.read_text(encoding="utf-8")
        f.write_text(t.replace("        for rid, fv in res.flow.items():",
                               "        res_alias = res\n"
                               "        for rid, fv in res_alias.flow.items():", 1),
                     encoding="utf-8")
    r = c6_on(change_expr)
    check(r.returncode == 1 and "RESTS ON THE ABSENCE" in r.stdout,
          "changing `res.flow` to `res_alias.flow` in the SAME scope makes the dismissal "
          "stop applying and the finding return. A key that cannot go stale cannot be "
          "trusted to be fresh")

    # DIRECTION 3 — the enclosing SCOPE is renamed: must not silently carry over.
    def rename_scope(d):
        f = d / "src" / "psyche_field.py"
        f.write_text(f.read_text(encoding="utf-8").replace(
            "def build_activation_field(", "def build_activation_field_v2(", 1),
            encoding="utf-8")
    r = c6_on(rename_scope)
    check(r.returncode == 1,
          "renaming build_activation_field turns the build RED — a rename is a RELEVANT "
          "change and is not survived silently")
    check("unregistered" in r.stdout and "build_activation_field_v2" in r.stdout,
          "AND THE MECHANISM IS WORTH STATING PRECISELY, because it is not the one a "
          "reader would assume: the finding is 'unregistered accumulation', not a revived "
          "absence-bound. The REGISTRY's own key is scope-anchored too, so renaming the "
          "scope unmatches the whole entry and the bound is never evaluated. The build "
          "still goes red, which is the property that matters — but by the registration "
          "path, not the dismissal path")

    section("0g  the legacy line-number format is REFUSED, never silently ignored")
    def legacy(d):
        import json as _j
        f = d / "tools" / "ledger.json"
        led = _j.loads(f.read_text(encoding="utf-8"))
        e = led["float_accumulations"]["src/psyche_field.py:build_activation_field.merged_flow"]
        e["bound_on_absence"][0]["dismissed"] = ["src/psyche_field.py:123 — old format"]
        f.write_text(_j.dumps(led, indent=2, ensure_ascii=False), encoding="utf-8")
    r = c6_on(legacy)
    check(r.returncode == 1 and "LINE-NUMBER format" in r.stdout,
          "a dismissal still written as `path:NNN` is REFUSED with its own finding — a "
          "half-migrated ledger cannot pass while its old entries silently excuse nothing")

    section("0g  keys are whitespace-free, and that is a contract not a nicety")
    for kind, sym in (("attribute_read", "ActivationField.flow"),
                      ("call", "advance"), ("binding", "get_road")):
        for rel, line, site in LC._absence_occurrences(REPO, kind, sym):
            check(site == "".join(site.split()),
                  f"key contains no whitespace: {site!r}")
            check(site.split(" ", 1)[0] == site,
                  f"and survives the `split(' ', 1)[0]` every dismissal is parsed with — "
                  f"the first version of this brick produced `road = store.get_road`, "
                  f"which truncated at the space and matched nothing: {site!r}")


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
