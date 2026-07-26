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
    "src/nous_activation.py:spread_activation.frozen": True,
    "src/nous_activation.py:spread_activation.out_total": True,
    "src/nous_activation.py:spread_activation.activation": True,
    "src/nous_activation.py:spread_activation.flow": False,
    "src/nous_coalitions.py:form_coalitions.strength": True,
    "src/nous_coalitions.py:form_coalitions_from_field.strength": True,
    "src/nous_field.py:build_activation_field.merged_flow": False,
    "src/nous_field.py:build_activation_field.total": False,
    "src/nous_store.py:Clock.advance._t": False,
    "src/nous_store.py:Road.valence.<return>": True,
    "src/nous_store.py:SubstrateStore.strengthen.road.strength": False,
    "src/nous_store.py:SubstrateStore.strengthen.road.charges": False,
    "src/nous_workspace.py:Broadcast.total_strength_after.<return>": True,
    "src/nous_workspace.py:select_winner.strength": True,
}

# THE ACCEPTANCE TEST (SPEC-0d F-3). A detector that passes because it found nothing is
# indistinguishable from a detector that is broken, so the only evidence that C6 works is
# a planted defect it catches. Three distinct shapes, because one that catches one shape
# and misses two is worse than none — it will be trusted.
INJECT_DICT_ADD = '''

def _injected_dict_add(items):
    """+= into a dict — nous_field's shape."""
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
        p = root / "src" / "nous_field.py"
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
    r = make_src_repo(tmp, extra={"src/nous_injected.py": INJECT_NEW_MODULE})
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
    reg["src/nous_gone.py:vanished.total"] = {"verdict": "registered",
                                              "reason": "a site that was deleted long ago"}
    r = make_src_repo(tmp, registry=reg)
    f = c6(r)
    check(len(f) == 1 and "no longer exists" in f[0].message, "stale entry caught")

    section("C6/F-5 a verdict that no longer matches the source is a finding")
    reg = dict(json.loads((REPO / "tools" / "ledger.json").read_text())[LC.ACCUM_KEY])
    reg["src/nous_field.py:build_activation_field.total"] = {
        "verdict": "fsum", "reason": "claims to be exactly rounded, and is not"}
    r = make_src_repo(tmp, registry=reg)
    f = c6(r)
    check(any("no longer describes the code" in x.message for x in f),
          "a naive site registered as fsum is caught")

    section("C6/F-5 a site converted to fsum but still registered as naive is a finding")
    reg = dict(json.loads((REPO / "tools" / "ledger.json").read_text())[LC.ACCUM_KEY])
    reg["src/nous_coalitions.py:form_coalitions.strength"] = {
        "verdict": "registered", "reason": "stale: this site was converted by BUG-0b1"}
    r = make_src_repo(tmp, registry=reg)
    f = c6(r)
    check(any("but the site is now math.fsum" in x.message for x in f),
          "an fsum site registered as naive is caught")

    section("C6/F-5 an empty or decorative reason is a finding")
    reg = dict(json.loads((REPO / "tools" / "ledger.json").read_text())[LC.ACCUM_KEY])
    reg["src/nous_field.py:build_activation_field.total"] = {"verdict": "registered",
                                                            "reason": "it is fine"}
    r = make_src_repo(tmp, registry=reg)
    f = c6(r)
    check(any("is an approval, not an adjudication" in x.message for x in f),
          "a reason too short to be checkable is caught")

    section("C6/F-5 an unknown verdict is a finding")
    reg = dict(json.loads((REPO / "tools" / "ledger.json").read_text())[LC.ACCUM_KEY])
    reg["src/nous_field.py:build_activation_field.total"] = {
        "verdict": "safe", "reason": "there is no 'safe' verdict; shape-present is not safe"}
    r = make_src_repo(tmp, registry=reg)
    f = c6(r)
    check(any("is not one of" in x.message for x in f), "vocabulary enforced")

    # ── F-7: ASSERTED NEGATIVE — 0d fixed nothing, and the record must not drift ──
    section("C6/F-7 ASSERTED NEGATIVE: nous_field.py's two sites are STILL naive after 0d")
    field_src = (REPO / "src" / "nous_field.py").read_text(encoding="utf-8")
    check("total[node] = total.get(node, 0.0) + act" in field_src,
          "field.total is still a naive accumulation in the source")
    check("merged_flow[rid] = merged_flow.get(rid, 0.0) + fv" in field_src,
          "field.merged_flow is still a naive accumulation in the source")
    total_site = by_key.get("src/nous_field.py:build_activation_field.total")
    check(total_site is not None and total_site.exact is False,
          "the census still classifies field.total as naive")
    entry = (LC.load_ledger(REPO)[LC.ACCUM_KEY] or {}).get(
        "src/nous_field.py:build_activation_field.total") or {}
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
    r = make_src_repo(tmp, extra={"src/nous_broken.py": "def f(:\n    pass\n"})
    f = c6(r)
    check(any("could not parse" in x.message for x in f), "unparseable module reported")

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
    r = make_src_repo(tmp, registry={"src/nous_field.py:build_activation_field.total":
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
    modules = ["nous_store.py", "nous_field.py", "nous_activation.py",
               "nous_coalitions.py", "nous_workspace.py", "nous_perceive.py"]
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
        p = r / "src" / "nous_store.py"
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
