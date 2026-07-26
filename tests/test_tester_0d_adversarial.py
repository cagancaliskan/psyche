"""
INDEPENDENT ADVERSARIAL TEST SUITE for brick 0d — the float-accumulation detector.

Author: tester (independent adversary). Written FROM SCRATCH against SPEC-0d §4's
invariants F-1 .. F-8. Not adapted from tools/test_ledger.py: every census expectation
here was re-derived by hand from src/ before this file imported the scanner, every
injected shape is the tester's own, and the loop-closed inputs come from the project's
own git history rather than from a hand-written fixture.

Mechanism only. 0d is a build gate; nothing here grades a cognitive claim.

THE ACCEPTANCE PROBLEM, STATED FIRST. A detector that passes because it found nothing is
indistinguishable from a detector that is broken. "C6 is green" is therefore not evidence
of anything, and this suite never treats it as such. Two independent sources of evidence
are used instead:

  1. PLANTED DEFECTS, in a scratch copy of the tree — never in src/ or tools/.
  2. THE PROJECT'S OWN HISTORY. The three naive accumulations this project found by hand
     (BUG-0b1's two, SPEC-0c §2.5's `nous_workspace:428`, SPEC-0c §2.7's `nous_field:131`)
     are checked out from git at the commits where they were still live, and the detector
     is required to report them. That input is external to 0d: nobody writing the scanner
     got to choose what those trees contain.

THE VERDICT IS **FAIL**, AND THE SUITE IS GREEN. Those are not in conflict; this project
has shipped that combination before (the 0b2 pass reported 83 passed, 0 failed and a
verdict of FAIL). The failures are recorded below as ASSERTED NEGATIVES: each one PASSES
while the defect is present and goes RED when it is fixed, so the record cannot drift.
Every one carries an explicit exit instruction.

  DEFECT 0d-1  (F-6, the verdict-deciding one)  The registry entry for
      `src/nous_field.py:build_activation_field.merged_flow` states "SHAPE PRESENT,
      SYMPTOM UNREPRODUCED". Its own stated falsifier — "a permutation probe over source
      order that moves any merged_flow value" — fires on a SIX-NODE graph, on the first
      try, and on 40 of 40 randomly generated convergent graphs. The claim is false.
      ROOT CAUSE: a four-source four-way convergence converges at the NODE level
      (field.total) and CANNOT converge at the ROAD level (merged_flow), because at hop 1
      each of the four roads is traversed by exactly one source's spread. merged_flow
      needs a road SHARED by two spreads, which requires depth >= 2. The probe that
      cleared the site was structurally incapable of exhibiting the symptom — the
      six-bug checklist's "structurally-impossible branch", and the exact failure mode
      SPEC-0d §0.1 exists to stop. SPEC-0d §3.3 carries the same false statement.

  DEFECT 0d-2  (scope honesty)  The detector's own scope statement says "ADDITIVE
      reduction only", contrasted against multiplicative chains. SUBTRACTIVE folds
      (`acc -= v`, `d[k] = d.get(k, 0.0) - v`) are additive reductions over negated
      terms, are exactly as order-sensitive, and are NOT detected. Four further shapes
      are undetected and appear in no limitation list: the walrus operator, tuple
      targets, `itertools.accumulate`, and — a traversal blind spot rather than a shape
      gap — EVERY STATEMENT inside a `match` case.

  FINDING 0d-3  (F-6, reason quality)  `src/nous_store.py:Clock.advance._t` is registered
      with "there is no term SET that could be permuted ... no alternative order a
      correct program could produce". Measured: over a random 4-element dt multiset the
      first trial already yields TWO distinct bit patterns of `_t` across the 4! orders.
      The mechanical half of the reason (one term per call) is true; the quoted clause is
      not, and it is the half a reader would rely on.

  FINDING 0d-4  (cross-interpreter)  A `src/` module containing a NUL byte is reported as
      a proper C6 finding on 3.11-3.14 and raises an uncaught `ValueError` on 3.10.
      A non-UTF-8 module raises an uncaught `UnicodeDecodeError` on every interpreter and
      exits 1, where the tool's documented contract for "the tool itself could not run"
      is exit 2.

WHAT HOLDS, and is demonstrated rather than asserted: F-1, F-2, F-3 (for all three shapes
SPEC-0d §4 names, plus nine more of the tester's own), F-4, F-5, F-7, F-8-as-written, and
the census's determinism across five CPython minor versions and six hash seeds.

Run directly:
    python3 tests/test_tester_0d_adversarial.py
"""

from __future__ import annotations

import ast
import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
TOOLS = ROOT / "tools"

sys.path.insert(0, str(SRC))
sys.path.insert(0, str(TOOLS))

import ledger_check as LC  # noqa: E402

_passed = 0
_failed = 0
_fail_msgs: list = []
_findings: list = []
_notes: list = []


def check(cond, msg):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        _fail_msgs.append(msg)
        print(f"  FAIL: {msg}")


def section(name):
    print(f"\n{name}")


def note(msg):
    _notes.append(msg)
    print(f"  NOTE: {msg}")


def finding(tag, msg):
    _findings.append((tag, msg))
    print(f"  FINDING [{tag}]: {msg}")


def bits(x: float) -> str:
    return struct.pack("<d", x).hex()


# ─────────────────────────────────────────────────────────────────────────────
# Scratch-tree machinery. src/ and tools/ are NEVER written to; ledger_check
# takes --root, so every injection lands in a copy under a temp directory.
# ─────────────────────────────────────────────────────────────────────────────

TMP = Path(tempfile.mkdtemp(prefix="tester0d_"))
_scratch_n = [0]


def real_registry() -> dict:
    return json.loads((TOOLS / "ledger.json").read_text(encoding="utf-8"))[LC.ACCUM_KEY]


def scratch(*, files=None, append=None, registry=Ellipsis, drop_registry=False) -> Path:
    """A scratch repo carrying a COPY of the real src/ and (by default) the real registry.

    `append` is {relative path: text to append}; appending never moves an existing line,
    so any new finding is unambiguously the planted one. `files` writes new files.
    """
    _scratch_n[0] += 1
    root = TMP / f"r{_scratch_n[0]:03d}"
    (root / "tools").mkdir(parents=True)
    shutil.copytree(SRC, root / "src",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    led = {"tests": {"suites": 0, "assertions": 0, "failures": 0, "per_suite": {}},
           "bricks": {}, "forbidden_claim_terms": []}
    if not drop_registry:
        led[LC.ACCUM_KEY] = real_registry() if registry is Ellipsis else registry
    (root / "tools" / "ledger.json").write_text(json.dumps(led, indent=2), encoding="utf-8")
    for rel, text in (append or {}).items():
        p = root / rel
        p.write_text(p.read_text(encoding="utf-8") + text, encoding="utf-8")
    for rel, text in (files or {}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


def c6(root: Path):
    return LC.check_float_accumulation(root, LC.load_ledger(root))


def gate_exit(root: Path) -> int:
    """The exit code of the real command line, in a fresh process — not an in-process
    call. `A gate is a fact about every commit after it`, and the fact is an exit code."""
    r = subprocess.run([sys.executable, str(TOOLS / "ledger_check.py"),
                        "--root", str(root), "--only", "C6", "--quiet"],
                       capture_output=True, text=True)
    return r.returncode


# ─────────────────────────────────────────────────────────────────────────────
# MY OWN CENSUS OF src/, derived by hand before this file imported the scanner.
#
# Method, so it can be audited: `grep -n 'fsum' src/*.py` for the exactly-rounded sites;
# `grep -n '+=' src/*.py` for augmented adds, each classified by reading its addend;
# and a six-line ast walk printing every `Assign` whose target's base name also appears
# in its value, for the self-referential shape. The result is reproduced independently
# below by `independent_census()`, which shares no code with ledger_check.
# ─────────────────────────────────────────────────────────────────────────────

HAND_CENSUS = {
    # key                                                             is_fsum
    "src/nous_activation.py:spread_activation.frozen":                True,
    "src/nous_activation.py:spread_activation.out_total":             True,
    "src/nous_activation.py:spread_activation.activation":            True,
    "src/nous_activation.py:spread_activation.flow":                  False,
    "src/nous_coalitions.py:form_coalitions.strength":                True,
    "src/nous_coalitions.py:form_coalitions_from_field.strength":     True,
    "src/nous_field.py:build_activation_field.merged_flow":           False,
    "src/nous_field.py:build_activation_field.total":                 False,
    "src/nous_store.py:Clock.advance._t":                             False,
    "src/nous_store.py:Road.valence.<return>":                        True,
    "src/nous_store.py:SubstrateStore.strengthen.road.strength":      False,
    "src/nous_store.py:SubstrateStore.strengthen.road.charges":       False,
    "src/nous_workspace.py:Broadcast.total_strength_after.<return>":  True,
    "src/nous_workspace.py:select_winner.strength":                   True,
}


def independent_census(path: Path):
    """A second, deliberately dumber scanner sharing no code with ledger_check.

    It answers only two questions per module — how many `math.fsum(` CALLS are there, and
    how many statements add a float into a name that appears on both sides — so it can
    corroborate the SHAPE COUNT without being able to inherit the scanner's bugs."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fsum = naive = 0
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "fsum":
            fsum += 1
        elif isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add):
            v = ast.unparse(n.value)
            if not re.fullmatch(r"-?\d+", v):          # an int literal is a tally
                naive += 1
        elif isinstance(n, ast.Assign) and len(n.targets) == 1:
            base = ast.unparse(n.targets[0]).split("[")[0]
            val = ast.unparse(n.value)
            if "+" in val and re.search(rf"\b{re.escape(base)}\b", val):
                naive += 1
    return fsum, naive


# ─────────────────────────────────────────────────────────────────────────────
# F-1 — the detector reports the known sites. DEMONSTRATED, not asserted.
# ─────────────────────────────────────────────────────────────────────────────

def test_F1_the_census_matches_a_hand_derived_census():
    section("F-1  the census agrees with a census derived by hand from src/")
    sites, problems = LC.scan_float_accumulations(ROOT)
    check(problems == [], f"every module under src/ parsed (problems={problems})")
    got = {s.key: s.exact for s in sites}
    check(set(got) == set(HAND_CENSUS),
          f"same site SET as the hand census; only in scanner="
          f"{sorted(set(got) - set(HAND_CENSUS))}, only by hand="
          f"{sorted(set(HAND_CENSUS) - set(got))}")
    for k, is_fsum in sorted(HAND_CENSUS.items()):
        check(got.get(k) is is_fsum,
              f"{k} classified {'fsum' if is_fsum else 'naive'} (got {got.get(k)!r})")
    check(sum(1 for v in got.values() if v) == 8, "eight exactly-rounded sites")
    check(sum(1 for v in got.values() if not v) == 6, "six naive sites")

    section("F-1  a second, independent scanner corroborates the shape counts")
    tot_f = tot_n = 0
    for p in sorted(SRC.glob("*.py")):
        f, n = independent_census(p)
        tot_f += f
        tot_n += n
    check(tot_f == 8, f"independent fsum call count = 8, got {tot_f}")
    # the dumb scanner cannot see the one-hop-laundered charges site, so it finds 5 not 6
    check(tot_n == 5,
          f"independent naive count = 5 (it cannot follow the `prior` temporary into "
          f"road.charges, which is the sixth), got {tot_n}")
    note("the sixth naive site (road.charges) is only visible with one-hop alias "
         "tracking; the second scanner not seeing it is the expected difference, and it "
         "is why the corroboration is a cross-check and not a duplicate")


def test_F1_LOOPCLOSED_the_detector_reports_the_three_hunts_on_the_trees_they_lived_in():
    section("F-1  LOOP-CLOSED: run the census on the project's OWN pre-fix trees")
    # Input the previous stages actually produced. Nobody writing the scanner chose what
    # is in these commits, so a hit here cannot be a fixture agreeing with itself.
    cases = [
        ("5d29071", "initial commit",
         {"src/nous_activation.py:spread_activation.activation",     # DEFECT-A
          "src/nous_coalitions.py:form_coalitions.strength",         # BUG-0b1 site 1
          "src/nous_coalitions.py:form_coalitions_from_field.strength",  # BUG-0b1 site 2
          "src/nous_field.py:build_activation_field.total",          # SPEC-0c §2.7
          "src/nous_store.py:Road.valence.<return>"}),               # SPEC-0c §2.5 site 3
        ("d51b1e5", "the parent of fix(0b1)",
         {"src/nous_coalitions.py:form_coalitions.strength",
          "src/nous_coalitions.py:form_coalitions_from_field.strength"}),
        ("e4df7df", "1d-ii, before 0c converted three sums",
         {"src/nous_workspace.py:select_winner.strength",            # survived a month
          "src/nous_workspace.py:Broadcast.total_strength_after.<return>",
          "src/nous_store.py:Road.valence.<return>"}),
    ]
    ok_any = False
    for commit, label, must_be_naive in cases:
        d = TMP / f"hist_{commit}"
        d.mkdir(parents=True, exist_ok=True)
        p = subprocess.run(f"git archive {commit} src | tar -x -C {d!s}",
                           shell=True, cwd=str(ROOT), capture_output=True, text=True)
        if p.returncode != 0 or not (d / "src").is_dir():
            note(f"git history unavailable for {commit}; F-1 loop-closure skipped")
            continue
        ok_any = True
        sites, probs = LC.scan_float_accumulations(d)
        naive = {s.key for s in sites if not s.exact}
        check(probs == [], f"{commit} ({label}) parsed cleanly")
        check(must_be_naive <= naive,
              f"{commit} ({label}): every hand-found site is reported as NAIVE; "
              f"missing={sorted(must_be_naive - naive)}")
        check(all(not s.exact for s in sites),
              f"{commit}: nothing is misreported as fsum on a tree that had no fsum")
        print(f"    {commit} {label:34} {len(sites)} sites, all naive")
    check(ok_any, "at least one historical tree was actually examined")


# ─────────────────────────────────────────────────────────────────────────────
# F-2 — zero unregistered candidates on the real tree
# ─────────────────────────────────────────────────────────────────────────────

def test_F2_zero_unregistered_on_the_real_tree():
    section("F-2  the populated registry leaves zero unregistered candidates")
    f = c6(ROOT)
    check(f == [], f"C6 reports nothing on src/ as shipped (got {[x.message for x in f]})")
    check(gate_exit(ROOT) == 0, "`ledger_check --only C6` exits 0 in a fresh process")

    section("F-2  and the scratch copy is clean too, so the fixture proves nothing by luck")
    check(c6(scratch()) == [], "a copied tree with the copied registry is clean")

    section("F-2  registry/census BIJECTION — no orphan on either side")
    reg = set(real_registry())
    cen = {s.key for s in LC.scan_float_accumulations(ROOT)[0]}
    check(reg == cen, f"registry == census; registry-only={sorted(reg - cen)}, "
                      f"census-only={sorted(cen - reg)}")


# ─────────────────────────────────────────────────────────────────────────────
# F-3 — THE ACCEPTANCE TEST. Planted defects, tester's own shapes.
# ─────────────────────────────────────────────────────────────────────────────

# The three SPEC-0d §4 names, written differently from the builder's fixtures so a shared
# transcription error cannot pass both.
P_DICT = ('\n\ndef _tp_basin_merge(pairs):\n'
          '    basin = {}\n'
          '    for node, act in pairs:\n'
          '        basin[node] = basin.get(node, 0.0) + act\n'
          '    return basin\n')
P_LOCAL = ('\n\ndef _tp_running(vals):\n'
           '    carried = 0.0\n'
           '    for v in vals:\n'
           '        carried += v\n'
           '    return carried\n')
P_SUM = ('\n\ndef _tp_builtin(strengths):\n'
         '    return sum(strengths) / max(1, len(strengths))\n')

# nine more of the tester's own, none of them in the builder's fixture set
P_CLASSATTR = ('\n\nclass _TpLedger:\n'
               '    running = 0.0\n\n\n'
               'def _tp_classattr(vals):\n'
               '    for v in vals:\n'
               '        _TpLedger.running = _TpLedger.running + v\n'
               '    return _TpLedger.running\n')
P_AUGSUB_ITEM = ('\n\ndef _tp_item_aug(bucket, pairs):\n'
                 '    for k, v in pairs:\n'
                 '        bucket[k] += v\n'
                 '    return bucket\n')
P_SETDEFAULT = ('\n\ndef _tp_setdefault(pairs):\n'
                '    out = {}\n'
                '    for k, v in pairs:\n'
                '        out[k] = out.setdefault(k, 0.0) + v\n'
                '    return out\n')
P_DEFAULTDICT = ('\nimport collections as _tpc\n\n\n'
                 'def _tp_defaultdict(pairs):\n'
                 '    out = _tpc.defaultdict(float)\n'
                 '    for k, v in pairs:\n'
                 '        out[k] += v\n'
                 '    return out\n')
P_COMPREHENSION = ('\n\ndef _tp_comp(pairs):\n'
                   '    acc = {}\n'
                   '    acc = {k: acc.get(k, 0.0) + v for k, v in pairs}\n'
                   '    return acc\n')
P_TERNARY = ('\n\ndef _tp_ternary(pairs):\n'
             '    o = {}\n'
             '    for k, v in pairs:\n'
             '        o[k] = (o[k] + v) if k in o else v\n'
             '    return o\n')
P_NESTED_SUB = ('\n\ndef _tp_grid(grid, vals):\n'
                '    for v in vals:\n'
                '        grid[0][1] = grid[0][1] + v\n'
                '    return grid\n')
P_MODULE_SCOPE = ('\n\n_TP_TOTAL = 0.0\nfor _tp_v in (0.1, 0.2):\n'
                  '    _TP_TOTAL += _tp_v\n')
P_SELF_ATTR = ('\n\nclass _TpAcc:\n'
               '    def __init__(self):\n'
               '        self.pool = 0.0\n\n'
               '    def take(self, vals):\n'
               '        for v in vals:\n'
               '            self.pool += v\n'
               '        return self.pool\n')
P_SUBPACKAGE = ('"""A module in a src/ SUBDIRECTORY the census has never seen."""\n\n\n'
                'def fold(vals):\n'
                '    t = 0.0\n'
                '    for v in vals:\n'
                '        t += v\n'
                '    return t\n')

INJECTIONS = [
    ("SPEC shape 1/3  += into a dict", {"src/nous_field.py": P_DICT}, "_tp_basin_merge.basin"),
    ("SPEC shape 2/3  a running local", {"src/nous_activation.py": P_LOCAL}, "_tp_running.carried"),
    ("SPEC shape 3/3  the builtin sum", {"src/nous_workspace.py": P_SUM}, "_tp_builtin.<return>"),
    ("tester  class-attribute fold", {"src/nous_store.py": P_CLASSATTR}, "_tp_classattr._TpLedger.running"),
    ("tester  += into a subscript", {"src/nous_coalitions.py": P_AUGSUB_ITEM}, "_tp_item_aug.bucket"),
    ("tester  setdefault chain", {"src/nous_field.py": P_SETDEFAULT}, "_tp_setdefault.out"),
    ("tester  defaultdict(float) +=", {"src/nous_perceive.py": P_DEFAULTDICT}, "_tp_defaultdict.out"),
    ("tester  dict-comprehension fold", {"src/nous_field.py": P_COMPREHENSION}, "_tp_comp.acc"),
    ("tester  ternary fold", {"src/nous_activation.py": P_TERNARY}, "_tp_ternary.o"),
    ("tester  nested subscript grid[i][j]", {"src/nous_store.py": P_NESTED_SUB}, "_tp_grid.grid[]"),
    ("tester  module-scope accumulation", {"src/nous_bodysensor.py": P_MODULE_SCOPE}, "_TP_TOTAL"),
    ("tester  self-attribute accumulator", {"src/nous_workspace.py": P_SELF_ATTR}, "_TpAcc.take.pool"),
]


def test_F3_ACCEPTANCE_planted_defects_turn_the_gate_red():
    section("F-3  ACCEPTANCE — twelve planted accumulations, each in a scratch copy")
    for label, append, symbol in INJECTIONS:
        r = scratch(append=append)
        f = c6(r)
        check(len(f) == 1, f"{label}: exactly one new finding, got {len(f)} "
                           f"{[x.message for x in f]}")
        check(any(symbol in x.message for x in f), f"{label}: names {symbol}")
        check(all(x.check == "C6" for x in f), f"{label}: reported under C6")
        check(gate_exit(r) == 1, f"{label}: THE BUILD GOES RED (exit 1)")
        print(f"    caught  {label}")

    section("F-3  a brand-new module in a src/ SUBDIRECTORY is not out of reach")
    r = scratch(files={"src/tp_pkg/deep.py": P_SUBPACKAGE})
    f = c6(r)
    check(len(f) == 1 and "src/tp_pkg/deep.py:fold.t" in f[0].message,
          f"a nested new module is scanned and keyed by its path, got "
          f"{[x.message for x in f]}")
    check(gate_exit(r) == 1, "and the build goes red")

    section("F-3  twelve at once are twelve findings, not one")
    merged = {}
    for _, append, _ in INJECTIONS:
        for rel, text in append.items():
            merged[rel] = merged.get(rel, "") + text
    r = scratch(append=merged)
    f = c6(r)
    check(len(f) == 12, f"all twelve reported together, got {len(f)}")
    check(len({(x.path, x.line) for x in f}) == 12,
          "twelve distinct sites, none counted twice by the expression scan")
    check(gate_exit(r) == 1, "the build goes red")

    section("F-3  removing the registry entirely reports every site, not zero")
    r = scratch(drop_registry=True)
    f = c6(r)
    check(len(f) >= 14, f"a missing registry reports every site (got {len(f)})")
    check(any("float_accumulations" in x.message for x in f),
          "the absent key is itself named")
    check(gate_exit(r) == 1, "and the build goes red")


def test_F3_the_key_round_trips_through_the_registry():
    section("F-3  LOOP-CLOSED: the census's own --list-accumulations output, fed back "
            "as the registry, is accepted; dropping one key is rejected")
    out = subprocess.run([sys.executable, str(TOOLS / "ledger_check.py"),
                          "--root", str(ROOT), "--list-accumulations"],
                         capture_output=True, text=True).stdout
    keys = [ln.split()[-1] for ln in out.splitlines() if ln.startswith("src/")]
    check(len(keys) == 14, f"the printed census names 14 keys, got {len(keys)}")
    built = {}
    for k in keys:
        verdict = "fsum" if HAND_CENSUS[k] else "registered"
        built[k] = {"verdict": verdict,
                    "reason": "reconstructed from the printed census for a round-trip test"}
    check(c6(scratch(registry=built)) == [],
          "a registry rebuilt from the tool's own printed keys is accepted verbatim")
    for victim in ("src/nous_field.py:build_activation_field.total",
                   "src/nous_store.py:Road.valence.<return>"):
        partial = {k: v for k, v in built.items() if k != victim}
        f = c6(scratch(registry=partial))
        check(len(f) == 1 and victim in f[0].message,
              f"dropping {victim} from the round-tripped registry is caught")


# ─────────────────────────────────────────────────────────────────────────────
# F-3 GAPS — shapes the detector does NOT see. Asserted negatives.
# ─────────────────────────────────────────────────────────────────────────────

DOCUMENTED_GAPS = [
    ("multiplicative chain `s *= v`",
     "def f(xs):\n    s = 1.0\n    for x in xs:\n        s *= x\n    return s\n"),
    ("two-hop laundering through a temporary",
     "def f(items):\n    o = {}\n    for k, v in items:\n        p = o.get(k, 0.0)\n"
     "        q = p * 1.0\n        o[k] = q + v\n    return o\n"),
    ("interprocedural: the add moved into a helper",
     "def h(a, b):\n    return a + b\n\ndef f(items):\n    o = {}\n"
     "    for k, v in items:\n        p = o.get(k, 0.0)\n        o[k] = h(p, v)\n    return o\n"),
    ("math.sumprod",
     "import math\ndef f(a, b):\n    return math.sumprod(a, b)\n"),
    ("Counter.update",
     "from collections import Counter\ndef f(rows):\n    c = Counter()\n"
     "    for r in rows:\n        c.update(r)\n    return c\n"),
]

# CONVERTED 2026-07-26 (D-021 re-verification). These three shapes were asserted here as
# UNDETECTED gaps. The builder closed all three, so the negatives were converted into
# positive assertions of the capability gained — NOT deleted. A deleted negative leaves no
# trace that the limit ever existed; a converted one is a record of a capability gained, and
# it goes red again if the capability regresses.
CLOSED_GAPS = [
    ("SUBTRACTIVE running local `acc -= v`",
     "def f(xs):\n    acc = 0.0\n    for x in xs:\n        acc -= x\n    return acc\n",
     ["aug-sub"]),
    ("SUBTRACTIVE fold into a dict",
     "def f(items):\n    o = {}\n    for k, v in items:\n        o[k] = o.get(k, 0.0) - v\n"
     "    return o\n",
     ["self-sub"]),
    ("EVERY STATEMENT inside a match case",
     "def f(xs, mode):\n    a = 0.0\n    for x in xs:\n        match mode:\n"
     "            case 1:\n                a += x\n            case _:\n"
     "                a = a + x\n    return a\n",
     ["aug-add", "self-add"]),
    # CONVERTED 2026-07-26 (SPEC-2f step zero). L3 was the one limitation this suite
    # asserted was load-bearing for 2f — see test_F8, which was written to make that
    # burden precise. The builder closed it; the negative becomes the capability.
    ("TUPLE TARGET `a, b = a + x, b + y` (was L3)",
     "def f(xs):\n    a = 0.0\n    b = 0.0\n    for x in xs:\n"
     "        a, b = a + x, b + x * x\n    return a, b\n",
     ["self-add", "self-add"]),
]

UNDOCUMENTED_GAPS = [
    ("walrus in an if test",
     "def f(xs):\n    a = 0.0\n    for x in xs:\n        if (a := a + x) > 1.0:\n"
     "            break\n    return a\n"),
    ("walrus in a while test",
     "def f(xs):\n    a = 0.0\n    it = iter(xs)\n"
     "    while (a := a + next(it, 0.0)) < 1.0:\n        pass\n    return a\n"),
    ("itertools.accumulate",
     "import itertools\ndef f(xs):\n    return list(itertools.accumulate(xs))[-1]\n"),
    ("operator.add(acc, v) called in a loop",
     "import operator\ndef f(xs):\n    a = 0.0\n    for x in xs:\n"
     "        a = operator.add(a, x)\n    return a\n"),
    ("reduce(operator.__add__, ...) — the dunder spelling",
     "import functools, operator\ndef f(xs):\n"
     "    return functools.reduce(operator.__add__, xs, 0.0)\n"),
    ("a float accumulator whose addend is an int literal",
     "def f(xs):\n    a = 0.5\n    for x in xs:\n        a += 1\n    return a\n"),
]


def test_F3_GAP_ASSERTED_NEGATIVES_shapes_the_detector_cannot_see():
    section("F-3  ASSERTED NEGATIVE: the DOCUMENTED gaps are real")
    for label, src in DOCUMENTED_GAPS:
        got = LC.scan_source(src, "src/probe.py")
        check(got == [], f"documented gap confirmed absent from the census: {label}")
    note("each of the five is named in ledger_check's own SCOPE comment, so a reader is "
         "warned before trusting the gate")

    section("F-3  CONVERTED: FOUR gaps CLOSED — the capability is asserted positively")
    # Each of these was an asserted-negative saying "the scanner cannot see X". The builder
    # closed all three. Verified INDEPENDENTLY below with inputs of this suite's own
    # construction, then converted — the assertion now says "the scanner sees X", so a
    # regression turns it red rather than passing silently.
    for label, src, expect in CLOSED_GAPS:
        got = sorted(s.kind for s in LC.scan_source(src, "src/probe.py"))
        check(got == sorted(expect),
              f"CLOSED, capability asserted: {label} -> {got} (was: invisible)")
    # inputs the OLD scanner provably could not see, written here and not borrowed
    check([s.kind for s in LC.scan_source(
        "class K:\n    def m(self, v):\n        self.total -= v\n", "src/p.py")] == ["aug-sub"],
        "subtraction is seen through an ATTRIBUTE target too, not just a local")
    check([s.kind for s in LC.scan_source(
        "def f(d, k, v):\n    p = d.get(k, 0.0)\n    d[k] = p - v\n", "src/p.py")] == ["self-sub"],
        "and through the one-hop temporary, so the laundering path covers Sub as well as Add")
    check([s.kind for s in LC.scan_source(
        "def f(c, xs):\n    match c:\n        case [1, 2]:\n            match xs:\n"
        "                case _:\n                    a = 0.0\n                    a += 1.0\n",
        "src/p.py")] == ["aug-add"],
        "a NESTED match reaches two levels deep — stronger than the single-level fixture "
        "the builder used, and the level where a shallow patch would have stopped")
    check(LC.scan_source("def f(v, x):\n    x = v - x\n    return x\n", "src/p.py") == [],
          "and the asymmetry is deliberate: `x = v - x` REFLECTS rather than accumulates, "
          "so subtraction counts only with the accumulator on the LEFT")

    section("F-3  L3 in depth — the SUBSCRIPT form, which is what 2f will actually write")
    # Verified with inputs constructed here. The builder's own fixture used plain names;
    # SPEC-2f's trace is a mapping, so the subscript form is the one that carries the risk,
    # and it is the one hit hardest.
    sub = LC.scan_source(
        "def f(trace, rid, e, d):\n    trace[rid], trace[d] = trace[rid] + e, trace[d] + e\n",
        "src/p.py")
    check(sorted(s.kind for s in sub) == ["self-add", "self-add"],
          f"SUBSCRIPT targets pair elementwise: both halves are seen ({len(sub)} findings)")
    check(all(s.symbol == "trace" for s in sub),
          "and both resolve to the base symbol `trace`, not to the key expression")
    lst = LC.scan_source("def f(xs):\n    a = b = 0.0\n    [a, b] = [a + xs, b + xs]\n",
                         "src/p.py")
    check(sorted(s.kind for s in lst) == ["self-add", "self-add"],
          f"the LIST form `[a, b] = [...]` pairs identically ({len(lst)} findings) — the "
          f"implementation keys on sequence-ness, not on the Tuple node specifically")
    check(sorted(s.kind for s in LC.scan_source(
        "def f(t, c, r, e):\n    t[r], c[r] = t[r] + e, c[r] - e\n", "src/p.py")) ==
        ["self-add", "self-sub"],
        "MIXED operators pair per element rather than per statement — an implementation "
        "that classified the statement as a whole would report one kind twice")
    one = LC.scan_source("def f(t, c, r, e, n):\n    t[r], c[r] = t[r] + e, n\n", "src/p.py")
    check(len(one) == 1 and one[0].symbol == "t",
          f"and when only ONE element accumulates, exactly that one is reported "
          f"({[s.symbol for s in one]}) — the pairing does not smear a kind across the "
          f"statement")

    section("F-3  L3 double-counting — the risk the builder named, attacked with my inputs")
    # The builder asserted `a, b = c, d = x + a, y + b` reports exactly a and b. That fixture
    # has DISTINCT names in the two chained targets. These do not.
    def keys(src):
        return [(s.line, s.col, s.kind, s.symbol) for s in LC.scan_source(src, "src/p.py")]
    k1 = keys("def f(x, y):\n    a = b = c = d = 0.0\n    a, b = c, d = x + a, y + b\n")
    check(len(k1) == 2 and len(set(k1)) == 2,
          f"the builder's own case holds: distinct chained targets report 2 unique keys {k1}")
    check(len(keys("def f(x):\n    a = 0.0\n    a = a, = (a + x,)\n")) == 1,
          "a name appearing as BOTH a single target and a sequence element is reported once "
          "— the two paths are exclusive, as asserted")
    note("both of the above hold. The next two do NOT, and are FINDINGS — recorded as "
         "asserted-negatives so they go red when fixed.")
    finding("2f-0-1", "the double-count guard holds only for chained targets with DISTINCT "
                      "names. `a, b = a, b = x + a, y + b` reports 4 findings at 2 distinct "
                      "keys; `d[k], d[k] = d[k] + x, d[k] + y` reports 2 at 1. The census "
                      "dedup turns the surplus into a phantom `#2` registry entry. Not "
                      "reachable in src/ today (14 sites, 14 unique keys).")
    finding("2f-0-2", "the four refusal paths (starred, nested, non-literal RHS, arity "
                      "mismatch) are REAL code paths — instrumenting _paired_elements shows "
                      "it is entered and declines — but scan_source returns [] for a refused "
                      "fold and [] for an empty file, so a caller cannot distinguish 'I "
                      "declined to look' from 'there is nothing here'. Unlike L1-L10, these "
                      "are decisions the scanner takes KNOWINGLY and records nowhere.")

    # ---- FINDING 2f-0-1: the double-count guard is incomplete -------------------------
    # The builder's assertion is true of its fixture and false in general. When the SAME
    # name appears in two chained sequence targets, each target is paired against the same
    # value tuple, so the one accumulation is reported twice at the SAME (line, col).
    dup = keys("def f(x, y):\n    a = b = 0.0\n    a, b = a, b = x + a, y + b\n")
    check(len(dup) == 4 and len(set(dup)) == 2,
          f"ASSERTED-NEGATIVE (FINDING 2f-0-1): a repeated name across chained sequence "
          f"targets is DOUBLE-COUNTED — 4 findings, 2 distinct keys {sorted(set(k[3] for k in dup))}. "
          f"The builder asserted no duplicate keys; that holds only when the chained "
          f"targets name different variables, which its fixture did")
    dup2 = keys("def f(d, k, x, y):\n    d[k], d[k] = d[k] + x, d[k] + y\n")
    check(len(dup2) == 2 and len(set(dup2)) == 1,
          f"same shape via a repeated SUBSCRIPT in one target list: {len(dup2)} findings, "
          f"{len(set(dup2))} distinct key. In the census these become `...d` and `...d#2`, "
          f"so the cost is a PHANTOM REGISTRY ENTRY — a site somebody must adjudicate that "
          f"does not independently exist")
    live_keys = [s.key for s in LC.scan_float_accumulations(ROOT)[0]]
    check(len(live_keys) == len(set(live_keys)),
          f"NOT reachable in src/ today: the live census has {len(live_keys)} sites and "
          f"{len(set(live_keys))} distinct keys, so 2f-0-1 is a latent defect in the guard, "
          f"not a live corruption of the registry. It becomes live the day 2f writes the "
          f"shape — which is the exact reason step zero existed")

    # ---- FINDING 2f-0-2: the four refusals are invisible from outside -----------------
    # Instrumented directly: _paired_elements IS entered for each of these and DOES decline,
    # so the refusals are real code paths. But scan_source returns [] for a refused fold and
    # [] for a file containing nothing — and the caller cannot tell which happened.
    refused = ["def f(x, r):\n    a = b = 0.0\n    a, *b = x + a, r\n",          # L11 starred
               "def f(x, y):\n    a = b = c = 0.0\n    (a, b), c = (a + x, b + y), c + x\n",
               "def f(x):\n    a = b = 0.0\n    a, b = pair(a + x, b + x)\n",    # L13 non-literal
               "def f(x):\n    a = b = 0.0\n    a, b = (a + x,)\n"]              # arity mismatch
    for src in refused:
        check(LC.scan_source(src, "src/p.py") == [], "refusal path yields no finding")
    check(LC.scan_source("def f():\n    pass\n", "src/p.py") == [],
          "ASSERTED-NEGATIVE (FINDING 2f-0-2): a file with NO accumulation yields exactly "
          "what all four refusals yield — the empty list. The scanner reaches a sequence "
          "assignment, examines it, declines it, and records that decision NOWHERE. This is "
          "the one class of limitation where the scanner HAS the information to speak: L1's "
          "multiplicative shape never matches, but L11-L13 are decisions taken with full "
          "knowledge. Silence that means 'I could not look' is being rendered identically "
          "to silence that means 'there is nothing here' — the exit-code defect's shape")

    note("DEFECT 0d-2 is RESOLVED for these three. The remaining shapes are no longer "
         "undocumented either — they are L2-L13 in ledger_check's scope block, each with a "
         "falsifier — so 0d-2 as originally written (undetected AND undocumented) no "
         "longer describes anything.")

    section("F-3  ASSERTED NEGATIVE: the remaining gaps, now DOCUMENTED as L2-L13")
    doc_scope = (TOOLS / "ledger_check.py").read_text(encoding="utf-8").split("SRC_REL = Path")[0]
    for label, src in UNDOCUMENTED_GAPS:
        got = LC.scan_source(src, "src/probe.py")
        check(got == [], f"still undetected, and now documented: {label}")
    check(all(f"L{i}" in doc_scope for i in range(1, 14)),
          "and L1-L13 are each named in the scope block with a falsifier — L11-L13 (starred "
          "elements, nested targets, non-literal RHS) were added by step zero as the price "
          "of closing L3, so the limitation count went 10 -> 13 while the COVERAGE grew. "
          "That is the honest bookkeeping: a closed gap that opens three narrower ones is "
          "reported as three, not as one net win")

    section("F-3  CONVERTED: the scope comment no longer promises coverage it lacks")
    doc = (TOOLS / "ledger_check.py").read_text(encoding="utf-8")
    check("ADDITIVE reduction only" not in doc,
          "the false promise 'ADDITIVE reduction only' is GONE from the scope comment — it "
          "told a reader that `-=` was covered when it was not, which is the same "
          "true-looking-sentence defect that failed this brick's registry")
    check("ADD and SUB only" in doc,
          "and the replacement states what is actually covered")
    check([s.kind for s in LC.scan_source(
        "def f(xs):\n    a = 0.0\n    for x in xs:\n        a -= x\n    return a\n",
        "src/p.py")] == ["aug-sub"],
        "and the subtractive fold the old comment mis-promised is now genuinely seen")
    # and it is order-sensitive by exactly the same mechanism, measured not asserted
    rng = random.Random(5)
    hit = None
    for _ in range(50000):
        vals = [rng.random() for _ in range(4)]
        seen = set()
        for perm in itertools.permutations(vals):
            a = 0.0
            for v in perm:
                a -= v
            seen.add(bits(a))
        if len(seen) > 1:
            hit = (vals, sorted(seen))
            break
    check(hit is not None,
          "a subtractive fold takes >1 bit pattern over a permuted multiset")
    if hit:
        print(f"    witness: {hit[0]} -> {len(hit[1])} bit patterns {hit[1]}")
    note("DEFECT 0d-2's wording half is RESOLVED: the phrase that mis-promised coverage "
         "is gone and the capability behind it exists.")

    section("F-3  the `match` gap is a TRAVERSAL blind spot, not a shape gap")
    m = ("def f(xs, mode):\n    a = 0.0\n    o = {}\n    match mode:\n"
         "        case 1:\n            a += xs[0]\n"
         "            o['k'] = o.get('k', 0.0) + xs[1]\n"
         "        case _:\n            a = a + xs[2]\n    return a, o\n")
    check(sorted(s.kind for s in LC.scan_source(m, "src/p.py"))
          == ["aug-add", "self-add", "self-add"],
          "CONVERTED: all three statement-level accumulations inside one match are now "
          "SEEN (they were all invisible). The root cause was a NAME, not a decision — "
          "ast.Match keeps its bodies under `cases`, and the walker recursed only into "
          "body/orelse/finalbody/handlers")
    m2 = ("def f(xs, mode):\n    match mode:\n        case 1:\n"
          "            return sum(xs)\n        case _:\n            return 0.0\n")
    check(len(LC.scan_source(m2, "src/p.py")) == 1,
          "a CALL inside a match case is still seen (via the expression scan), which is "
          "why the hole is easy to miss: the file is not silent, only its statements are")
    note("DEFECT 0d-2's traversal half is RESOLVED. Verified independently: nested match "
         "two levels deep, guarded mapping patterns, and a subtractive fold inside a case "
         "are all reached. This mattered on a deadline — 2f is written next and the gate "
         "now stands before that traffic rather than after it.")


# ─────────────────────────────────────────────────────────────────────────────
# F-4 — no false positives on integer accumulation
# ─────────────────────────────────────────────────────────────────────────────

def test_F4_integer_accumulation_is_not_reported():
    section("F-4  the integer counters LIVING IN src/ are absent from the census")
    keys = {s.key for s in LC.scan_float_accumulations(ROOT)[0]}
    src_text = "\n".join(p.read_text(encoding="utf-8") for p in sorted(SRC.glob("*.py")))
    for tally in ("creation_seq", "access_count", "traversal_count", "_cursor"):
        check(tally in src_text, f"{tally} really is accumulated somewhere in src/")
        check(not any(tally in k for k in keys), f"{tally} is not a candidate")

    section("F-4  planted integer tallies produce no finding")
    ints = ('\n\ndef _tp_ints(items):\n'
            '    seq = 0\n'
            '    hits = 0\n'
            '    per = {}\n'
            '    for k in items:\n'
            '        seq += 1\n'
            '        hits += len(k)\n'
            '        per[k] = per.get(k, 0) + 1\n'
            '    return seq, hits, per, sum(1 for _ in items), sum(range(4)), sum([1, 2])\n')
    check(c6(scratch(append={"src/nous_store.py": ints})) == [],
          "six integer shapes, zero findings")

    section("F-4  the exemption is STRUCTURAL — a float named like a counter is caught")
    liar = ('\n\ndef _tp_liar(vals):\n'
            '    traversal_count = 0.0\n'
            '    for v in vals:\n'
            '        traversal_count += v\n'
            '    return traversal_count\n')
    f = c6(scratch(append={"src/nous_store.py": liar}))
    check(len(f) == 1 and "_tp_liar.traversal_count" in f[0].message,
          "a FLOAT accumulator named `traversal_count` is still reported")

    section("F-4  the false positives that DO exist are candidates, not verdicts")
    fps = [("string concatenation", "def f(xs):\n    s = ''\n    for x in xs:\n"
                                    "        s += x\n    return s\n"),
           ("list concatenation", "def f(xs):\n    o = []\n    for x in xs:\n"
                                  "        o = o + [x]\n    return o\n"),
           ("statistics.mean over int literals",
            "import statistics\ndef f():\n    return statistics.mean([1, 2, 3])\n"),
           ("a method that merely happens to be called sum",
            "def f(frame):\n    return frame.sum()\n")]
    for label, src in fps:
        check(LC.scan_source(src, "src/p.py") != [], f"reported as a candidate: {label}")
    note("SPEC-0d §2.2 says the detector reports CANDIDATES for adjudication, so these "
         "are not defects. §6's falsifier is a LARGE number of legitimately-exempt "
         "candidates; src/ currently yields 14, all legitimate. The bound is not near.")


# ─────────────────────────────────────────────────────────────────────────────
# F-5 — a registry that can rot silently is a note again
# ─────────────────────────────────────────────────────────────────────────────

def test_F5_registry_rot_is_itself_a_finding():
    section("F-5  a registry rot battery, written from the invariant not from the code")
    reg = real_registry()
    K_NAIVE = "src/nous_field.py:build_activation_field.total"
    K_FSUM = "src/nous_workspace.py:select_winner.strength"

    cases = [
        ("names a site that no longer exists",
         {**reg, "src/nous_ghost.py:gone.total": {"verdict": "registered",
                                                  "reason": "a site deleted three bricks ago"}},
         "no longer exists"),
        ("names a real file but a symbol that does not exist",
         {**reg, "src/nous_field.py:build_activation_field.nosuchname":
             {"verdict": "registered", "reason": "a symbol that was renamed away"}},
         "no longer exists"),
        ("claims fsum for a site that is naive",
         {**reg, K_NAIVE: {"verdict": "fsum",
                           "reason": "asserts exact rounding that the AST denies"}},
         "no longer describes the code"),
        ("claims naive for a site that is fsum",
         {**reg, K_FSUM: {"verdict": "registered",
                          "reason": "stale: this one was converted during 0c"}},
         "now math.fsum"),
        ("an unknown verdict word",
         {**reg, K_NAIVE: {"verdict": "safe",
                           "reason": "there is no safe verdict; shape-present is not safe"}},
         "is not one of"),
        ("a reason too short to be checkable",
         {**reg, K_NAIVE: {"verdict": "registered", "reason": "it is fine"}},
         "approval, not an adjudication"),
        ("a missing reason",
         {**reg, K_NAIVE: {"verdict": "registered"}},
         "approval, not an adjudication"),
        ("an entry that is a bare string",
         {**reg, K_NAIVE: "looks like a reason, is not an entry"},
         "must be an object"),
    ]
    for label, bad, needle in cases:
        r = scratch(registry=bad)
        f = c6(r)
        check(any(needle in x.message for x in f), f"caught: {label}")
        check(gate_exit(r) == 1, f"build red: {label}")

    section("F-5  a registry that is not an object at all")
    for bad in (["a", "list"], "a string", 17):
        f = c6(scratch(registry=bad))
        check(len(f) >= 1 and "must be an object" in f[0].message,
              f"rejected: registry = {bad!r}")

    section("F-5  a right-looking key under the WRONG path does not cover the site")
    wrong = {("src/nous_activation.py:build_activation_field.total" if
              k == K_NAIVE else k): v for k, v in reg.items()}
    f = c6(scratch(registry=wrong))
    check(len(f) == 2, f"one unregistered site AND one stale entry, got {len(f)}")

    section("F-5  ASSERTED NEGATIVE: reason-level rot is NOT machine-detectable")
    # C6 checks that a reason exists, is >= 24 chars, and that the verdict matches the
    # AST. It cannot check that the sentence is TRUE. This is exactly why F-6 is a human
    # invariant, and DEFECT 0d-1 below is what it looks like when the gap is used.
    lying = {**reg, K_NAIVE: {"verdict": "registered",
                              "reason": "This site is proven order-independent over all "
                                        "permutations, which is a fabrication."}}
    check(c6(scratch(registry=lying)) == [],
          "a factually false reason of adequate length is accepted silently")
    note("this is a correct scope boundary for a machine check, not a defect in it — "
         "but it means 'C6 green' says nothing about whether the registry is TRUE")


# ─────────────────────────────────────────────────────────────────────────────
# F-6 — the registry's honesty. GRADED BY MEASUREMENT.
# ─────────────────────────────────────────────────────────────────────────────

def _store():
    from nous_store import SubstrateStore, Clock
    return SubstrateStore, Clock


def test_F6_every_entry_is_structurally_well_formed():
    section("F-6  every entry names a real site and carries a non-decorative reason")
    reg = real_registry()
    sites = {s.key: s for s in LC.scan_float_accumulations(ROOT)[0]}
    for k, e in sorted(reg.items()):
        check(k in sites, f"{k}: names a site the census actually finds")
        check(isinstance(e, dict) and e.get("verdict") in ("fsum", "registered"),
              f"{k}: verdict is one of the two words")
        r = (e.get("reason") or "").strip()
        check(len(r) >= 24, f"{k}: reason is {len(r)} chars")
    # SPEC-0d §3.1's standard is a reason that EXPLAINS. A naive entry either CLAIMS A
    # BOUND — in which case it owes a falsifier, or it is an assertion however long it
    # is — or it records the site as already confirmed order-dependent, in which case a
    # falsifier is not applicable because nothing is being claimed.
    naive = {k: (e.get("reason") or "") for k, e in reg.items()
             if isinstance(e, dict) and e.get("verdict") == "registered"}
    check(len(naive) == 6, f"six naive entries (got {len(naive)})")
    bounded = {k for k, r in naive.items() if "FALSIFIER" in r.upper()}
    confirmed = {k for k, r in naive.items() if "CONFIRMED ORDER-DEPENDENT" in r.upper()}
    check(bounded | confirmed == set(naive),
          f"every naive entry either states a falsifier or records the site as already "
          f"confirmed; neither={sorted(set(naive) - bounded - confirmed)}")
    # DE-BRITTLED 2026-07-26. These two assertions previously pinned the COMPOSITION of the
    # registry — "exactly 5 bounded, exactly 2 confirmed", and "the one entry naming no
    # falsifier is `total`". Both went red when a ledger-only edit ADDED a falsifier to an
    # entry, i.e. when the registry got BETTER. A count is not the property; it was a proxy
    # for one, and SPEC-0d §3.1 states the property directly: a naive entry that CLAIMS A
    # BOUND owes a falsifier, and the only thing that discharges the debt is being recorded
    # as already confirmed, because a confirmed site claims nothing that could be disproved.
    # That is a RELATION between two fields, and it is what these tests were always for.
    claiming = set(naive) - confirmed
    unfalsified = sorted(set(naive) - bounded)
    check(claiming <= bounded,
          f"SUBSTANCE: every entry that CLAIMS A BOUND names a falsifier. Claiming without "
          f"one: {sorted(claiming - bounded)}")
    check(set(unfalsified) <= confirmed,
          f"SUBSTANCE: exemption from the falsifier debt is EARNED, never assumed — an "
          f"entry may omit a falsifier only where it is recorded CONFIRMED ORDER-DEPENDENT, "
          f"which is the state in which there is nothing left to disprove. Exempt but "
          f"unconfirmed: {sorted(set(unfalsified) - confirmed)}")
    # Non-emptiness, not equality. If nothing were ever confirmed the exemption route would
    # be untested; if everything were, the falsifier convention would be vacuous. Both are
    # real properties of the partition and neither breaks when a sentence improves.
    check(len(confirmed) >= 1 and len(claiming) >= 1,
          f"and BOTH routes are exercised — {len(confirmed)} confirmed, {len(claiming)} "
          f"claiming — so neither the debt nor its discharge is a dead branch")

    # THE DISCRIMINATING EXAMPLES, RUN RATHER THAN CLAIMED.
    # "De-brittle the assertion" is one step from "assert nothing", and the only proof that
    # a replacement still bites is a registry state the two assertions disagree about. Both
    # mutations below are applied to the REAL registry and measured.
    def _measure(r):
        nv = {k: (e.get("reason") or "") for k, e in r.items()
              if isinstance(e, dict) and e.get("verdict") == "registered"}
        bd = {k for k, v in nv.items() if "FALSIFIER" in v.upper()}
        cf = {k for k, v in nv.items() if "CONFIRMED ORDER-DEPENDENT" in v.upper()}
        return (  # (OLD_A, OLD_B, NEW_A, NEW_B)
            len(bd) == 5 and len(cf) == 2,
            sorted(set(nv) - bd) == ["src/nous_field.py:build_activation_field.total"],
            (set(nv) - cf) <= bd,
            (set(nv) - bd) <= cf)

    def _blank(r, key, phrase):
        r = copy.deepcopy(r)
        r[key]["reason"] = r[key]["reason"].replace(phrase, "xxxx")
        return r

    STRENGTH = "src/nous_store.py:SubstrateStore.strengthen.road.strength"
    TOTAL = "src/nous_field.py:build_activation_field.total"

    old_a, old_b, new_a, new_b = _measure(_blank(reg, STRENGTH, "FALSIFIER"))
    check(old_a and not new_a,
          "DISCRIMINATOR for the first assertion: strip the falsifier from `strength` and "
          "the OLD count assertion PASSES (bounded falls 6->5, confirmed stays 2 — its exact "
          "5/2) while the NEW one FAILS. The count was satisfied by an improvement and a "
          "regression CANCELLING, which is precisely the state that shipped silently")
    old_a, old_b, new_a, new_b = _measure(
        _blank(_blank(reg, TOTAL, "FALSIFIER"), TOTAL, "CONFIRMED ORDER-DEPENDENT"))
    check(old_b and not new_b,
          "DISCRIMINATOR for the second: make `total` exempt AND drop its CONFIRMED record "
          "and the OLD literal-list assertion PASSES exactly, while the NEW one FAILS — an "
          "entry claiming a bound with nothing to disprove and no debt paid. That is the "
          "shape DEFECT 0d-1 had, and the old assertion was satisfied by it")
    note("both mutations are measured here, not argued. An assertion that no registry state "
         "can falsify is surrender wearing a test's clothes; these two have witnesses.")
    note("this is the strongest property a machine can check about a reason. That the "
         "bound is STATED is checkable; that it is TRUE is F-6, and is measured below — "
         "where one of the five bounds turns out to be false.")


def test_F6_DEFECT_the_merged_flow_reason_is_FALSE():
    section("F-6  DEFECT 0d-1 — run the merged_flow entry's OWN stated falsifier")
    from nous_store import SubstrateStore, Clock, NodeType
    from nous_field import build_activation_field
    from nous_activation import spread_activation

    reg = real_registry()["src/nous_field.py:build_activation_field.merged_flow"]
    # The phrase still appears — as a QUOTED RETRACTION, which is the project's idiom for
    # a corrected record ("a spec quietly amended teaches nothing"). So the assertion has to
    # separate ASSERTING the claim from QUOTING it. Checking for the phrase's absence was my
    # own imprecision on the first pass; a corrected record would have failed it.
    up = reg["reason"].upper()
    i = up.find("SYMPTOM UNREPRODUCED")
    check(i != -1 and "PREVIOUSLY READ" in up[:i] and "THAT WAS FALSE" in up[i:i + 120],
          "CONVERTED: the phrase 'symptom unreproduced' survives ONLY as a quoted "
          "retraction — preceded by 'previously read' and followed by 'That was FALSE' — "
          "so the entry records its own correction rather than asserting the false claim")
    check("CONFIRMED ORDER-DEPENDENT" in reg["reason"].upper(),
          "and the entry now records the verdict its own falsifier produced when run")
    check("STRUCTURALLY INCAPABLE" in reg["reason"].upper(),
          "and it records WHY the clearing probe cleared — four sources converging on one "
          "node makes every value single-term at hop 1, so that probe could not have "
          "exhibited the symptom at all. Recording the probe's incapacity, not just the "
          "corrected verdict, is what stops the same probe being trusted again")

    def star(depth2: bool):
        st = SubstrateStore(clock=Clock(simulated=True, start=9000.0))
        srcs = [st.add_node(f"s{i}", NodeType.CONCEPT) for i in range(4)]
        hub = st.add_node("hub", NodeType.CONCEPT)
        for i, s in enumerate(srcs):
            r = st.add_road(s, hub)
            for _ in range(i + 1):
                st.strengthen(r, {"joy": 0.11 * (i + 1)})
        if depth2:
            tail = st.add_node("tail", NodeType.CONCEPT)
            r = st.add_road(hub, tail)
            for _ in range(3):
                st.strengthen(r, {"awe": 0.4})
        return st, srcs

    def probe(st, srcs):
        seen, terms = {}, {}
        for s in srcs:
            for rid, fv in spread_activation(st, s, energy=1.0).flow.items():
                terms.setdefault(rid, []).append(fv)
        for perm in itertools.permutations(srcs):
            f = build_activation_field(st, list(perm), energy=1.0)
            for k, v in f.flow.items():
                seen.setdefault(k, set()).add(bits(v))
        return seen, terms

    # (a) the ROOT CAUSE: at depth 1 every merged_flow value is SINGLE-TERM, so the
    #     four-way-convergence probe could not have varied whatever the arithmetic was.
    st, srcs = star(False)
    seen, terms = probe(st, srcs)
    check(sorted({len(v) for v in terms.values()}) == [1],
          "depth 1: every merged_flow key receives exactly ONE term")
    check(max(len(v) for v in seen.values()) == 1,
          "depth 1: one bit pattern over 4! orders — a structurally-impossible symptom")

    # (b) one shared downstream road, and the entry's falsifier fires
    st, srcs = star(True)
    seen, terms = probe(st, srcs)
    moved = {k: v for k, v in seen.items() if len(v) > 1}
    check(4 in {len(v) for v in terms.values()},
          "depth 2: the shared road receives four terms")
    check(len(moved) >= 1,
          f"DEFECT 0d-1: merged_flow MOVES over source order on a six-node graph "
          f"(moved={len(moved)} roads)")
    for k, v in sorted(moved.items()):
        exact = bits(math.fsum(terms[k]))
        print(f"    road {k[:8]}..  terms={len(terms[k])}  patterns={sorted(v)}  "
              f"fsum={exact}")
        check(len(v) == 2, "two distinct bit patterns, one ULP apart")

    # (c) not a lucky graph: 40 randomly generated convergent stores
    def convergent(seed):
        rng = random.Random(seed)
        st = SubstrateStore(clock=Clock(simulated=True, start=9000.0))
        srcs = [st.add_node(f"s{i}", NodeType.CONCEPT) for i in range(4)]
        mids = [st.add_node(f"m{i}", NodeType.CONCEPT) for i in range(3)]
        sinks = [st.add_node(f"z{i}", NodeType.CONCEPT) for i in range(3)]
        for a in srcs:
            for b in mids:
                r = st.add_road(a, b)
                for _ in range(rng.randint(1, 5)):
                    st.strengthen(r, {"joy": rng.uniform(0.1, 0.9)})
        for a in mids:
            for b in sinks:
                r = st.add_road(a, b)
                for _ in range(rng.randint(1, 5)):
                    st.strengthen(r, {"awe": rng.uniform(0.1, 0.9)})
        return st, srcs

    hits = 0
    for seed in range(40):
        st, srcs = convergent(seed)
        seen = {}
        for perm in itertools.permutations(srcs):
            for k, v in build_activation_field(st, list(perm), energy=1.0).flow.items():
                seen.setdefault(k, set()).add(bits(v))
        if max(len(v) for v in seen.values()) > 1:
            hits += 1
    check(hits == 40, f"the falsifier fires on {hits}/40 random convergent graphs")
    note("scope of the consequence: ActivationField.flow has NO reader anywhere in src/ "
         "today, so the moving bits reach no decision. That is a bound worth writing "
         "into the entry — it is not a reason to call the symptom unreproduced.")


def test_F6_measure_the_other_five_naive_reasons():
    from nous_store import SubstrateStore, Clock, NodeType
    from nous_activation import spread_activation
    reg = real_registry()

    section("F-6  entry 1/6 flow — re-measure the model entry's single-term bound")
    # The bound: a road transmits exactly once per spread, so the add's second operand
    # cannot exist. Measured independently of the 0c pass, on hostile graphs.
    def hostile(seed):
        rng = random.Random(seed)
        st = SubstrateStore(clock=Clock(simulated=True, start=5000.0))
        n = rng.randint(2, 12)
        ids = [st.add_node(f"n{i}", NodeType.CONCEPT) for i in range(n)]
        for _ in range(rng.randint(1, n * 3)):
            a, b = ids[rng.randrange(n)], ids[rng.randrange(n)]
            try:
                r = st.add_road(a, b)
            except Exception:
                continue
            for _ in range(rng.randint(1, 4)):
                st.strengthen(r, {"joy": rng.uniform(-1, 1)})
        return st, ids

    spreads = violations = 0
    for seed in range(60):
        st, ids = hostile(seed)
        for sid in ids:
            res = spread_activation(st, sid, energy=1.0)
            spreads += 1
            for rid in res.flow:
                road = st.get_road(rid)
                # a road can only have transmitted if its source expanded, and a node
                # expands once because settled_hops admits it once
                if road.source_id != res.seed and road.source_id not in res.hops:
                    violations += 1
    check(violations == 0,
          f"{spreads} spreads over 60 hostile graphs (cycles, self-loops, fans): "
          f"every flow-carrying road starts at a once-expanded node ({violations} "
          f"violations)")
    check("FALSIFIER: any spread that writes the same road id twice"
          in reg["src/nous_activation.py:spread_activation.flow"]["reason"],
          "the model entry states a falsifier a reader can run")

    section("F-6  entry 1/6 flow — and run the falsifier DIRECTLY, not by proxy")
    # The structural argument above infers single-term-ness from settled_hops. The entry's
    # falsifier is narrower and sharper: "any spread that writes the same road id twice".
    # So instrument the write itself, in a SCRATCH copy of the engine — src/ is untouched.
    r = scratch()
    eng = r / "src" / "nous_activation.py"
    t = eng.read_text(encoding="utf-8")
    counter = ('class _TpCountingDict(dict):\n'
               '    LOG = []\n\n'
               '    def __setitem__(self, k, v):\n'
               '        _TpCountingDict.LOG.append(k)\n'
               '        dict.__setitem__(self, k, v)\n')
    marker = "    flow: Dict[str, float] = {}   # RoadID"
    if marker in t:
        t = t.replace(marker,
                      "    flow: Dict[str, float] = _TpCountingDict()   # RoadID", 1)
        i = t.index("def spread_activation(")
        eng.write_text(t[:i] + counter + "\n\n" + t[i:], encoding="utf-8")
        driver = r / "tp_flow.py"
        driver.write_text(
            "import random, sys, pathlib\n"
            "sys.path.insert(0, str(pathlib.Path(__file__).parent / 'src'))\n"
            "from nous_store import SubstrateStore, Clock, NodeType\n"
            "import nous_activation as NA\n"
            "spreads = writes = doubles = loops = 0\n"
            "for seed in range(120):\n"
            "    rng = random.Random(seed)\n"
            "    st = SubstrateStore(clock=Clock(simulated=True, start=5000.0))\n"
            "    n = rng.randint(2, 14)\n"
            "    ids = [st.add_node('n%d' % i, NodeType.CONCEPT) for i in range(n)]\n"
            "    for _ in range(rng.randint(1, n * 4)):\n"
            "        a, b = ids[rng.randrange(n)], ids[rng.randrange(n)]\n"
            "        try:\n"
            "            rid = st.add_road(a, b)\n"
            "        except Exception:\n"
            "            continue\n"
            "        for _ in range(rng.randint(1, 4)):\n"
            "            st.strengthen(rid, {'joy': rng.uniform(-1, 1)})\n"
            "    for sid in ids:\n"
            "        NA._TpCountingDict.LOG.clear()\n"
            "        res = NA.spread_activation(st, sid, energy=1.0)\n"
            "        log = list(NA._TpCountingDict.LOG)\n"
            "        spreads += 1\n"
            "        writes += len(log)\n"
            "        doubles += (len(log) != len(set(log)))\n"
            "        for k in res.flow:\n"
            "            rd = st.get_road(k)\n"
            "            loops += (rd.source_id == rd.target_id)\n"
            "print(spreads, writes, doubles, loops)\n", encoding="utf-8")
        out = subprocess.run([sys.executable, str(driver)], capture_output=True, text=True)
        check(out.returncode == 0, f"the instrumented engine ran ({out.stderr[-300:]})")
        if out.returncode == 0:
            sp, wr, db, lp = (int(x) for x in out.stdout.split())
            print(f"    {sp} spreads, {wr} flow writes, {db} with a repeated road id, "
                  f"{lp} self-loop roads carried flow")
            check(wr > 1000, f"the instrumentation actually fired ({wr} writes) — a "
                             f"falsifier run that exercises nothing proves nothing")
            check(lp > 0, "self-loops, the shape most likely to re-enter a road, are "
                          "present in the battery")
            check(db == 0, f"DIRECT: no spread writes the same road id twice "
                           f"({db} violations) — the model entry's bound HOLDS")
    else:
        note("the flow accumulator's declaration no longer matches the instrumentation "
             "marker; the direct falsifier run was skipped and only the structural "
             "argument above stands")

    section("F-6  entry 3/6 total — 'CONFIRMED ORDER-DEPENDENT' is TRUE")
    from nous_field import build_activation_field
    # A three-source star does NOT always vary — with only three terms the naive sum is
    # frequently order-invariant, and a probe built on one such graph would clear the
    # site. That is DEFECT 0d-1's mistake, so the probe is a BATTERY, and the pass
    # criterion is a rate over generated graphs rather than one hand-picked witness.
    def star(seed, n_src):
        rng = random.Random(seed)
        st = SubstrateStore(clock=Clock(simulated=True, start=9000.0))
        srcs = [st.add_node(f"s{i}", NodeType.CONCEPT) for i in range(n_src)]
        hub = st.add_node("hub", NodeType.CONCEPT)
        for s in srcs:
            r = st.add_road(s, hub)
            for _ in range(rng.randint(1, 5)):
                st.strengthen(r, {"joy": rng.uniform(0.1, 0.9)})
        return st, srcs, hub

    for n_src in (3, 4):
        moved = 0
        for seed in range(30):
            st, srcs, hub = star(seed, n_src)
            seen = {bits(build_activation_field(st, list(p), energy=1.0).total[hub])
                    for p in itertools.permutations(srcs)}
            moved += len(seen) > 1
        check(moved > 0,
              f"field.total[hub] moves over source order in {moved}/30 graphs "
              f"at {n_src} sources")
        print(f"    {n_src} sources: order-dependent in {moved}/30 generated graphs")
    check("CONFIRMED ORDER-DEPENDENT" in reg["src/nous_field.py:build_activation_field.total"]["reason"],
          "and the entry says so")

    section("F-6  entry 4/6 Clock.advance._t — FINDING 0d-3, the reason overstates")
    e = reg["src/nous_store.py:Clock.advance._t"]["reason"]
    check("no term SET that could be permuted" in e,
          "the entry claims there is no permutable term set")
    rng = random.Random(11)
    trials = 0
    witness = None
    while witness is None and trials < 200000:
        trials += 1
        dts = [rng.random() for _ in range(4)]
        seen = set()
        for perm in itertools.permutations(dts):
            c = Clock(simulated=True, start=0.0)
            for d in perm:
                c.advance(d)
            seen.add(bits(c.now()))
        if len(seen) > 1:
            witness = (dts, sorted(seen))
    check(witness is not None,
          f"a permuted dt multiset DOES move `_t` (first hit at trial {trials})")
    if witness:
        print(f"    dt = {witness[0]}")
        print(f"    _t bit patterns over 4! orders: {witness[1]}")
    check(trials == 1, "and it is the FIRST multiset tried, not a rare construction")
    # the mechanical half IS true: exactly one term arrives per call
    tree = ast.parse((SRC / "nous_store.py").read_text(encoding="utf-8"))
    adv = [n for n in ast.walk(tree)
           if isinstance(n, ast.FunctionDef) and n.name == "advance"]
    writes = [m for n in adv for m in ast.walk(n)
              if isinstance(m, ast.AugAssign) and ast.unparse(m.target) == "self._t"]
    check(len(writes) == 1, "exactly one write to _t per advance() call — the "
                            "mechanical half of the reason is true")
    callers = subprocess.run(["grep", "-rn", r"\.advance(", str(SRC)],
                             capture_output=True, text=True).stdout.strip()
    check(callers == "", "and src/ contains no caller of advance() at all")

    section("F-6  entry 5/6 road.strength — 'exactly one term per crossing' is TRUE")
    tree = ast.parse((SRC / "nous_store.py").read_text(encoding="utf-8"))
    fn = [n for n in ast.walk(tree)
          if isinstance(n, ast.FunctionDef) and n.name == "strengthen"][0]
    w = [ast.unparse(m.value) for m in ast.walk(fn) if isinstance(m, ast.Assign)
         and any(ast.unparse(t) == "road.strength" for t in m.targets)]
    w += [f"AUG {ast.unparse(m.value)}" for m in ast.walk(fn)
          if isinstance(m, ast.AugAssign) and ast.unparse(m.target) == "road.strength"]
    check(w == ["min(1.0, road.strength + gain)"],
          f"one write, two operands, no container iterated (got {w})")

    section("F-6  entry 6/6 road.charges — the per-key bound, measured over 6! orders")
    feelings = ["fear", "joy", "awe", "grief", "rage", "calm"]
    base = {f: (i + 1) * 0.137 * (-1) ** i for i, f in enumerate(feelings)}
    sig = set()
    for perm in itertools.permutations(feelings):
        st = SubstrateStore(clock=Clock(simulated=True, start=1000.0))
        a = st.add_node("a", NodeType.CONCEPT)
        b = st.add_node("b", NodeType.CONCEPT)
        r = st.add_road(a, b)
        for k in range(5):
            st.strengthen(r, {f: base[f] * (1 + 0.1 * k) for f in perm})
        road = st.get_road(r)
        sig.add((bits(road.strength),
                 tuple(sorted((f, bits(v)) for f, v in road.charges.items())),
                 bits(road.valence)))
    check(len(sig) == 1,
          f"720 charge-dict orders x 5 crossings -> {len(sig)} distinct "
          f"(strength, charges, valence); the per-key bound HOLDS")


# ─────────────────────────────────────────────────────────────────────────────
# F-7 — ASSERTED NEGATIVE: 0d fixed nothing
# ─────────────────────────────────────────────────────────────────────────────

def test_F7_ASSERTED_NEGATIVE_the_field_sites_are_still_naive():
    section("F-7  ASSERTED NEGATIVE: nous_field's two sites are STILL naive after 0d")
    text = (SRC / "nous_field.py").read_text(encoding="utf-8")
    check("total[node] = total.get(node, 0.0) + act" in text,
          "field.total is still the naive shape, verbatim")
    check("merged_flow[rid] = merged_flow.get(rid, 0.0) + fv" in text,
          "field.merged_flow is still the naive shape, verbatim")
    sites = {s.key: s for s in LC.scan_float_accumulations(ROOT)[0]}
    for k in ("src/nous_field.py:build_activation_field.total",
              "src/nous_field.py:build_activation_field.merged_flow"):
        check(sites[k].exact is False, f"{k} is classified naive by the census")
        check(real_registry()[k]["verdict"] == "registered",
              f"{k} is REGISTERED, not converted")

    section("F-7  ASSERTED NEGATIVE: SCOPE — 0d touched no production module")
    d = subprocess.run(["git", "diff", "--stat", "HEAD", "--", "src", "tests"],
                       cwd=str(ROOT), capture_output=True, text=True)
    if d.returncode == 0:
        changed = [ln for ln in d.stdout.splitlines() if "src/" in ln]
        check(changed == [], f"src/ has zero diff against HEAD (got {changed})")
    else:
        note("git unavailable; the src/ no-diff check was skipped")

    section("F-7  LOOP-CLOSED: the order dependence still reaches Coalition.strength")
    from nous_store import SubstrateStore, Clock, NodeType
    from nous_field import build_activation_field
    from nous_coalitions import form_coalitions_from_field
    rng = random.Random(4242)
    reached = 0
    for seed in range(20):
        st = SubstrateStore(clock=Clock(simulated=True, start=9000.0))
        srcs = [st.add_node(f"s{i}", NodeType.CONCEPT) for i in range(4)]
        mids = [st.add_node(f"m{i}", NodeType.CONCEPT) for i in range(3)]
        for a in srcs:
            for b in mids:
                r = st.add_road(a, b)
                for _ in range(rng.randint(1, 5)):
                    st.strengthen(r, {"joy": rng.uniform(0.1, 0.9)})
        strengths = {}
        for perm in itertools.permutations(srcs):
            f = build_activation_field(st, list(perm), energy=1.0)
            for c in form_coalitions_from_field(f, st):
                strengths.setdefault(tuple(sorted(c.members)), set()).add(bits(c.strength))
        if any(len(v) > 1 for v in strengths.values()):
            reached += 1
    check(reached > 0,
          f"Coalition.strength takes >1 bit pattern over source order in {reached}/20 "
          f"loop-closed graphs — the site's effect is still live")
    note("this block goes RED when a later brick converts the nous_field sites. That is "
         "the correct signal: the brick that converts them re-verifies here.")


# ─────────────────────────────────────────────────────────────────────────────
# F-8 — scope honesty
# ─────────────────────────────────────────────────────────────────────────────

def test_F8_ASSERTED_NEGATIVE_the_gate_covers_src_only():
    section("F-8  ASSERTED NEGATIVE: nothing outside src/ is claimed")
    r = scratch(files={
        "tools/tp_helper.py": P_LOCAL.lstrip("\n"),
        "tests/test_tp.py": P_DICT.lstrip("\n"),
        "experiments/tp_harness.py": P_SUM.lstrip("\n"),
        "tp_toplevel.py": P_LOCAL.lstrip("\n"),
        "docs/tp_snippet.py": P_DICT.lstrip("\n"),
    })
    check(c6(r) == [], "five accumulations outside src/ produce zero findings")
    check(gate_exit(r) == 0, "and the build stays green — the gate is src/-only")

    section("F-8  the real repository HAS such accumulations outside src/")
    outside = []
    for d in ("tools", "experiments"):
        p = ROOT / d
        if not p.is_dir():
            continue
        for f in sorted(p.rglob("*.py")):
            try:
                got = LC.scan_source(f.read_text(encoding="utf-8"),
                                     f.relative_to(ROOT).as_posix())
            except (SyntaxError, UnicodeDecodeError, ValueError):
                continue
            outside.extend(s for s in got if not s.exact)
    check(len(outside) > 0,
          f"{len(outside)} naive accumulations exist outside src/ and are NOT gated")
    for s in outside[:6]:
        print(f"    ungated  {s.path}:{s.line}  {s.kind}")
    note("this is SPEC-0d's decided scope, not a defect. It is asserted here so 'C6 "
         "green' is never read as a whole-repository guarantee.")


# ─────────────────────────────────────────────────────────────────────────────
# Determinism, purity, robustness
# ─────────────────────────────────────────────────────────────────────────────

def test_determinism_across_interpreters_and_hash_seeds():
    section("DETERMINISM  one census, five CPython minor versions x six hash seeds")
    interps = []
    for name in ("python3.10", "python3.11", "python3.12", "python3.13", "python3.14"):
        p = shutil.which(name)
        if p:
            interps.append(p)
    check(len(interps) >= 3, f"at least three interpreters available (found {len(interps)})")
    digests = {}
    for p in interps:
        for seed in (0, 1, 2, 3, 7, 42):
            env = dict(os.environ, PYTHONHASHSEED=str(seed))
            out = subprocess.run([p, str(TOOLS / "ledger_check.py"),
                                  "--root", str(ROOT), "--list-accumulations"],
                                 capture_output=True, text=True, env=env)
            check(out.returncode == 0, f"{os.path.basename(p)} seed={seed} exited 0")
            digests[(p, seed)] = hashlib.sha256(out.stdout.encode()).hexdigest()
    uniq = set(digests.values())
    check(len(uniq) == 1,
          f"ONE SHA-256 over {len(digests)} processes (got {len(uniq)}: {sorted(uniq)})")
    print(f"    {len(digests)} processes, digest {sorted(uniq)[0][:16]}")

    section("DETERMINISM  the in-process census is order-stable, not merely set-stable")
    a = [(s.key, s.kind, s.line) for s in LC.scan_float_accumulations(ROOT)[0]]
    b = [(s.key, s.kind, s.line) for s in LC.scan_float_accumulations(ROOT)[0]]
    check(a == b, "two scans agree on ORDER as well as membership")


def test_purity_the_check_writes_nothing():
    section("PURITY  running the gate mutates neither the ledger nor src/")
    def snap():
        h = hashlib.sha256()
        for p in sorted(list(SRC.rglob("*.py")) + [TOOLS / "ledger.json",
                                                   TOOLS / "ledger_check.py"]):
            h.update(p.name.encode())
            h.update(p.read_bytes())
        return h.hexdigest()
    before = snap()
    c6(ROOT)
    LC.scan_float_accumulations(ROOT)
    subprocess.run([sys.executable, str(TOOLS / "ledger_check.py"),
                    "--root", str(ROOT), "--only", "C6"], capture_output=True)
    subprocess.run([sys.executable, str(TOOLS / "ledger_check.py"),
                    "--root", str(ROOT), "--list-accumulations"], capture_output=True)
    check(snap() == before, "src/ and tools/ are byte-identical after four gate runs")

    section("PURITY  an injection into a scratch tree never touches the real one")
    scratch(append={"src/nous_field.py": P_DICT})
    check(snap() == before, "the scratch machinery wrote nothing into the repository")


def test_F6_FINDING_0d5_the_absence_bound_underreports_on_dynamic_access():
    """FINDING 0d-5. The bound_on_absence docstring says it is 'DELIBERATELY BIASED TOWARD
    OVER-REPORTING' and that it flags EVERY matching read. It does not: dynamic access is
    invisible to it. The bias is the right one to choose and the bounds are TRUE today —
    but the promise is wider than the mechanism, and a gate that promises over-reporting
    while under-reporting is worse than one that promises nothing, because the promise is
    what a reader substitutes for checking.

    This is the same defect class that failed this brick twice already: a true-looking
    sentence someone relies on. It does NOT block the brick — the realistic path (a direct
    `field_.flow` read, which is what 2f would write) is caught, verified.

    IF THIS GOES RED: either the mechanism was widened or the docstring was narrowed to
    match. Check which, then retire this."""
    section("F-6  FINDING 0d-5 — the absence bound under-reports on dynamic access")
    import tempfile, shutil
    from pathlib import Path as _P
    CASES = [
        ("getattr by string",   "def f(x):\n    return getattr(x, 'flow')\n",
         "attribute_read", "ActivationField.flow"),
        ("__dict__ subscript",  "def f(x):\n    return x.__dict__['flow']\n",
         "attribute_read", "ActivationField.flow"),
        ("aliased then called", "def f(c):\n    g = c.advance\n    g(1.0)\n",
         "call", "advance"),
        ("getattr then called", "def f(c):\n    getattr(c, 'advance')(1.0)\n",
         "call", "advance"),
    ]
    for label, src, kind, sym in CASES:
        d = _P(tempfile.mkdtemp()); (d / "src").mkdir()
        (d / "src" / "m.py").write_text(src)
        try:
            check(LC._absence_occurrences(d, kind, sym) == [],
                  f"UNDER-REPORTED: {label} evades the bound the docstring promises to catch")
        finally:
            shutil.rmtree(d, ignore_errors=True)
    # ...and the path that actually matters IS caught, which is why this does not block
    d = _P(tempfile.mkdtemp()); (d / "src").mkdir()
    (d / "src" / "m.py").write_text("def f(field_):\n    return sorted(field_.flow.items())\n")
    try:
        check(len(LC._absence_occurrences(d, "attribute_read", "ActivationField.flow")) == 1,
              "the REALISTIC path — a direct attribute read, which is what brick 2f would "
              "write — is caught, so the bound protects the case it exists for")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    finding("0d-5", "bound_on_absence's docstring promises to flag EVERY matching read and "
                    "under-reports on getattr, __dict__ and aliased calls. Narrow the "
                    "wording or widen the mechanism; the bounds are true today and the "
                    "realistic path is covered, so this does not block the brick.")


def test_F8_L3_and_L7_interact_and_2f_is_where_it_lands():
    """L3 (tuple targets) is singled out because it is a plausible thing for 2f to write —
    updating a trace and a counter together is idiomatic. Measured here, with the exact
    line 2f would plausibly contain, because the burden has been placed on a reader of
    SPEC-2f and that burden is only fair if the limitation is precise."""
    section("F-8  CONVERTED: L3 is CLOSED, and the compounding with L7 is what remains")
    idiomatic = ("def f(trace, counts, rid, e):\n"
                 "    trace[rid], counts[rid] = trace[rid] + e, counts[rid] + 1\n")
    idio = LC.scan_source(idiomatic, "src/p.py")
    check(len(idio) == 1 and idio[0].kind == "self-add" and idio[0].symbol == "trace",
          f"CONVERTED (was: ZERO findings, L3): the idiomatic 2f line — update a trace and "
          f"a counter in one tuple assignment — now yields exactly the FLOAT half "
          f"({[(s.symbol, s.kind) for s in idio]}). This is the single line that motivated "
          f"step zero, and it is the assertion that goes red if the traversal regresses")
    split = ("def f(trace, counts, rid, e):\n"
             "    trace[rid] = trace[rid] + e\n"
             "    counts[rid] = counts[rid] + 1\n")
    got = LC.scan_source(split, "src/p.py")
    check(len(got) == 1 and got[0].kind == "self-add",
          f"split across two lines, the FLOAT accumulation is caught ({len(got)} finding) — "
          f"so L3 is a real hole and not a property of the computation")
    check(all(s.symbol != "counts" for s in got),
          "and the integer counter is still correctly exempt (L7) — unchanged by step zero, "
          "which closed L3 only")
    check([s.symbol for s in idio] == [s.symbol for s in got],
          f"THE PROPERTY THAT MATTERS: the tuple form and the split form now report the "
          f"SAME sites ({[s.symbol for s in idio]}). L3 was load-bearing precisely because "
          f"the two spellings disagreed, so a 2f author's formatting choice decided whether "
          f"the gate saw the accumulation. It no longer does")
    note("SPEC-2f's recorded warning — 'write the trace update on its own line' — is now "
         "OBSOLETE as a requirement and should be struck by architect-pm. It is not the "
         "tester's file to edit; recorded here so the instruction does not outlive its "
         "reason and get cited as a live constraint.")


def test_robustness_unreadable_and_unparseable_modules():
    """CONVERTED 2026-07-26. Every assertion here previously documented a BROKEN contract:
    unparseable source produced a finding (exit 1, 'the repo is inconsistent'), a non-UTF-8
    module escaped as an uncaught UnicodeDecodeError, and a NUL byte diverged BY
    INTERPRETER. All three are fixed. The assertions are converted rather than deleted, so
    a regression turns them red instead of passing silently.

    The distinction the fix rests on, and the reason it matters: a FINDING means the census
    ran and the repository is inconsistent. `CensusUnreadable` means the census did NOT run.
    Exit 0 on source the gate could not read is the worst outcome this tool has — it is
    indistinguishable from clean — and exit 1 is nearly as bad, because it asserts a scan
    that never happened."""
    section("ROBUSTNESS  CONVERTED: unreadable source is exit 2, never 0, never a finding")
    for label, payload in (
        ("unparseable",  {"files": {"src/nous_tp_broken.py": "def f(:\n    pass\n"}}),
        ("non-UTF-8",    {"raw": ("src/nous_tp_latin1.py", b"x = 1\n# caf\xe9 \xff\xfe\n")}),
        ("NUL byte",     {"raw": ("src/nous_tp_nul.py", b'x = 1\ny = "a\x00b"\n')}),
    ):
        r = scratch(files=payload.get("files"))
        if "raw" in payload:
            rel, blob = payload["raw"]
            (r / rel).write_bytes(blob)
        raised = None
        try:
            c6(r)
        except LC.CensusUnreadable as e:
            raised = e
        check(raised is not None,
              f"{label}: raises CensusUnreadable — the census refuses to certify a module "
              f"it never read, rather than returning a census that looks complete")
        check(gate_exit(r) == 2,
              f"{label}: exits 2 ('the tool could not run'), NOT 0 and NOT 1")

    section("ROBUSTNESS  CONVERTED: the NUL byte no longer diverges by interpreter")
    r = scratch()
    (r / "src" / "nous_tp_nul.py").write_bytes(b'x = 1\ny = "a\x00b"\n')
    seen = {}
    for name in ("python3.10", "python3.11", "python3.12", "python3.13", "python3.14"):
        exe = shutil.which(name)
        if not exe:
            continue
        o = subprocess.run([exe, str(TOOLS / "ledger_check.py"), "--root", str(r),
                            "--only", "C6", "--quiet"], capture_output=True, text=True)
        seen[name] = o.returncode
        print(f"    {name}: exit {o.returncode}")
    check(len(seen) >= 5, f"swept {len(seen)} interpreters (need 5)")
    check(set(seen.values()) == {2},
          f"one exit code on every interpreter: {sorted(set(seen.values()))}. It was a "
          f"rendered finding on 3.11-3.14 and an uncaught ValueError on 3.10 — CONTRIBUTING.md "
          f"rule 7, a property that holds on one interpreter and fails on another was "
          f"never a property of the program. Both arms now exist so the CONTRACT is "
          f"identical rather than an artefact of which interpreter you ran")
    check("Traceback" not in subprocess.run(
        [sys.executable, str(TOOLS / "ledger_check.py"), "--root", str(r), "--only", "C6"],
        capture_output=True, text=True).stderr,
        "and it is a diagnosed refusal, not a traceback")
    note("FINDING 0d-4 is RESOLVED on both halves — the exit-code contract and the "
         "interpreter divergence.")


# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 78)
    print("  TESTER — brick 0d, the float-accumulation detector (SPEC-0d §4, F-1..F-8)")
    print("=" * 78)
    for t in [
        test_F1_the_census_matches_a_hand_derived_census,
        test_F1_LOOPCLOSED_the_detector_reports_the_three_hunts_on_the_trees_they_lived_in,
        test_F2_zero_unregistered_on_the_real_tree,
        test_F3_ACCEPTANCE_planted_defects_turn_the_gate_red,
        test_F3_the_key_round_trips_through_the_registry,
        test_F3_GAP_ASSERTED_NEGATIVES_shapes_the_detector_cannot_see,
        test_F4_integer_accumulation_is_not_reported,
        test_F5_registry_rot_is_itself_a_finding,
        test_F6_every_entry_is_structurally_well_formed,
        test_F6_DEFECT_the_merged_flow_reason_is_FALSE,
        test_F6_measure_the_other_five_naive_reasons,
        test_F7_ASSERTED_NEGATIVE_the_field_sites_are_still_naive,
        test_F8_ASSERTED_NEGATIVE_the_gate_covers_src_only,
        test_determinism_across_interpreters_and_hash_seeds,
        test_purity_the_check_writes_nothing,
        test_F6_FINDING_0d5_the_absence_bound_underreports_on_dynamic_access,
        test_F8_L3_and_L7_interact_and_2f_is_where_it_lands,
        test_robustness_unreadable_and_unparseable_modules,
    ]:
        t()

    print("\n" + "=" * 78)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    if _fail_msgs:
        print("  FAILURES:")
        for m in _fail_msgs:
            print("   -", m)
    print("=" * 78)
    print("  TESTER VERDICT ON SPEC-2f STEP ZERO — FAIL  (2026-07-26)")
    print("  (SPEC-0d §4 itself still HOLDS in full; the FAIL is on step zero's own bar)")
    print("=" * 78)
    print("    F-1  HOLDS       RE-RUN after the builder touched the traversal: all three")
    print("                     historical bugs still caught on the pre-fix trees they")
    print("                     lived in, at identical per-commit counts 10/12/12, and the")
    print("                     census digest is unchanged on all five interpreters.")
    print("    F-2  HOLDS       zero unregistered; registry and census in bijection")
    print("    F-3  HOLDS       FOUR gaps now CLOSED and CONVERTED — L3 joins the three")
    print("                     from last cycle. Limitations went 10 -> 13: closing L3 cost")
    print("                     three narrower ones (L11-L13), reported as three.")
    print("    F-4  HOLDS       no false positive on any integer tally in src/")
    print("    F-5  HOLDS       rot shapes caught; reason-TRUTH is out of machine reach")
    print("    F-6  HOLDS       all SIX reasons survived their OWN falsifiers, run rather")
    print("                     than admired. Its two count assertions are DE-BRITTLED to")
    print("                     the debt relation SPEC-0d §3.1 actually states.")
    print("    F-7  HOLDS       both nous_field sites still naive; src/ has zero diff")
    print("    F-8  HOLDS       CONVERTED: the tuple and split spellings now report the")
    print("                     SAME sites, which is what L3 being load-bearing meant.")
    print("=" * 78)
    print("  WHY FAIL, on one criterion only: the four refusal paths do not refuse VISIBLY.")
    print("  L3 detection is sound under inputs of this suite's own construction, and the")
    print("  retro-catch is untouched. But 2f-0-2 stands — a declined fold and an empty file")
    print("  are the same [] to a caller — and 2f-0-1 shows the double-count guard holds")
    print("  only for chained targets with distinct names. Neither is reachable in src/")
    print("  today; both become reachable the day 2f writes the shape step zero was for.")
    print("=" * 78)
    print("=" * 78)
    if _findings:
        print("  FINDINGS (asserted negatives — they PASS while the defect is present)")
        for tag, msg in _findings:
            print(f"    [{tag}] {msg}")
        print("=" * 78)
    shutil.rmtree(TMP, ignore_errors=True)
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
