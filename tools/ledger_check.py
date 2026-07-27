#!/usr/bin/env python3
"""ledger_check.py — make documentation staleness a build failure.

This project has shipped four different assertion counts across five documents
(README.md: 618, docs/outreach/*: 130, PAPER_CLAIM_INVENTORY: 1372, TEST_OUTPUT: 1372),
and docs/ARCHITECTURE.md still describes a seven-module system that has had eight
modules for a month. None of that was caught, because nothing checks prose against
fact. This does.

Four checks:

  C1 LEDGER-vs-CAPTURE   tools/ledger.json's generated test fields must equal what
                         docs/TEST_OUTPUT.txt actually says. Catches a stale ledger.
  C2 PROSE-vs-LEDGER     any Markdown sentence quoting a suite/assertion count must
                         agree with the ledger. Catches a stale document.
  C3 STATUS-VOCABULARY   status labels applied to a brick must be in valid_statuses
                         and must match the ledger's status for that brick.
  C4 FORBIDDEN-CLAIMS    CLAUDE.md rule 1 terms may not appear outside the quarantined
                         paths, unless the line carries an explicit allow pragma.
  C5 RUNNER-COMPLETENESS every test file on disk is either registered in run_tests.py or
                         listed in the ledger's unregistered_suites with a reason. Catches
                         a capture that silently under-reports because a suite was never
                         wired in.
  C6 FLOAT-ACCUMULATION  every float accumulation in src/ is either math.fsum or registered
                         in the ledger's float_accumulations with a reason. Catches a NEW
                         naive accumulation the moment it is written, instead of on the
                         fourth manual hunt (SPEC-0d).

Exit 0 = clean. Exit 1 = findings. Exit 2 = the tool itself could not run.

Pragmas, for the cases the checker cannot know about:
    <!-- ledger:allow-claim -->      on the line, or the line before, permits one
                                     forbidden term (use when quoting a vision doc)
    <!-- ledger:allow-count -->      permits a count that disagrees with the ledger
                                     (use for explicitly-labelled historical figures)
    <!-- ledger:ignore-file -->      anywhere in a file, skips that file entirely

Stdlib only, in keeping with the project's dependency rule.

Usage:
    python3 tools/ledger_check.py                 # check the repo from its root
    python3 tools/ledger_check.py --root PATH
    python3 tools/ledger_check.py --only C2,C4
    python3 tools/ledger_check.py --quiet         # findings only, no OK lines
    python3 tools/ledger_check.py --list-accumulations
                                                  # print C6's census for adjudication
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

LEDGER_REL = Path("tools/ledger.json")
CAPTURE_REL = Path("docs/TEST_OUTPUT.txt")

SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build",
    ".claude/worktrees", ".obsidian",
}

ALLOW_CLAIM = "ledger:allow-claim"
ALLOW_COUNT = "ledger:allow-count"
IGNORE_FILE = "ledger:ignore-file"


# ─────────────────────────────────────────────────────────────────────────────
# findings
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Finding:
    check: str
    path: str
    line: int
    message: str
    fix: str = ""

    def render(self) -> str:
        loc = f"{self.path}:{self.line}" if self.line else self.path
        out = f"  [{self.check}] {loc}\n        {self.message}"
        if self.fix:
            out += f"\n        fix: {self.fix}"
        return out


# ─────────────────────────────────────────────────────────────────────────────
# loading
# ─────────────────────────────────────────────────────────────────────────────

def load_ledger(root: Path) -> dict:
    p = root / LEDGER_REL
    if not p.exists():
        raise SystemExit(f"ledger_check: no ledger at {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"ledger_check: {LEDGER_REL} is not valid JSON: {e}")


def parse_capture(root: Path) -> Optional[Dict[str, object]]:
    """Read docs/TEST_OUTPUT.txt and derive the true counts.

    The capture format is one block per suite:
        ######################################################################
        # test_nous_store.py
        ######################################################################
        ...
          RESULT: 45 passed, 0 failed
    """
    p = root / CAPTURE_REL
    if not p.exists():
        return None

    suite_re = re.compile(r"^#\s+(test_\S+\.py)\s*$")
    result_re = re.compile(r"^\s*RESULT:\s+(\d+)\s+passed,\s+(\d+)\s+failed\s*$")
    python_re = re.compile(r"^Python\s*:\s*Python\s+(\S+)")
    gen_re = re.compile(r"^Generated\s*:\s*(.+?)\s*$")

    per_suite: Dict[str, int] = {}
    failures = 0
    current: Optional[str] = None
    captured_python = ""
    captured_at = ""

    aborted: List[str] = []
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = suite_re.match(raw)
        if m:
            # BRICK 0e: a header arriving while `current` is still set means the PREVIOUS
            # suite never reported. The old parser just overwrote `current` here and the
            # suite vanished — from the capture, the ledger, C1 and C5 at once, all green.
            if current is not None:
                aborted.append(current)
            current = m.group(1)
            continue
        m = result_re.match(raw)
        if m:
            passed, failed = int(m.group(1)), int(m.group(2))
            failures += failed
            if current:
                # A suite printing RESULT more than once is malformed. The FIRST
                # one wins — `current` is cleared here, so later RESULT lines find
                # no owner and are ignored. (This comment previously said 'last
                # wins', which the code has never done.)
                per_suite[current] = passed
                current = None
            continue
        m = python_re.match(raw)
        if m:
            captured_python = m.group(1)
            continue
        m = gen_re.match(raw)
        if m and not captured_at:
            captured_at = m.group(1)

    # End of file with `current` still set: the LAST suite never reported. This arm is
    # not a special case bolted on — it is the same defect as the mid-file one, and it is
    # the arm the loop above structurally cannot reach, because no later header arrives
    # to notice the gap.
    if current is not None:
        aborted.append(current)

    if aborted:
        raise CaptureMalformed(
            f"{CAPTURE_REL}: {len(aborted)} suite(s) emitted a header and never a RESULT "
            f"line — {', '.join(aborted)}. The capture is incomplete: every total derived "
            f"from it understates the repository by an unknown amount. Re-run "
            f"tools/capture_run.py once the aborting suite reports.")

    return {
        "suites": len(per_suite),
        "assertions": sum(per_suite.values()),
        "failures": failures,
        "per_suite": per_suite,
        "captured_python": captured_python,
        "captured_at": captured_at,
    }


def walk_markdown(root: Path) -> Iterable[Path]:
    """Prose files whose quoted facts are checked: Markdown and LaTeX.

    LaTeX matters more than Markdown here, not less: the paper is the one document where a
    stale count is actually published. It went unchecked until 2026-07-25, during which the
    canonical total moved twice underneath it."""
    for pattern in ("*.md", "*.tex"):
        for p in sorted(root.rglob(pattern)):
            rel = p.relative_to(root).as_posix()
            if any(rel == d or rel.startswith(d.rstrip("/") + "/") for d in SKIP_DIRS):
                continue
            if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
                continue
            yield p


def normalise(line: str) -> str:
    """LaTeX writes a thin-space thousands separator as 1{,}372. Same number, and it must
    be checked the same way."""
    return line.replace("{,}", ",")


def has_pragma(lines: List[str], idx: int, pragma: str) -> bool:
    """True if the pragma is on this line or the line immediately above.

    Written `<!-- ledger:allow-count -->` in Markdown and `% ledger:allow-count` in LaTeX;
    the bare token is what is matched, so both spellings work."""
    if pragma in lines[idx]:
        return True
    if idx > 0 and pragma in lines[idx - 1]:
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# C1 — ledger vs capture
# ─────────────────────────────────────────────────────────────────────────────

def check_ledger_vs_capture(root: Path, ledger: dict) -> List[Finding]:
    out: List[Finding] = []
    cap = parse_capture(root)
    if cap is None:
        return [Finding("C1", CAPTURE_REL.as_posix(), 0,
                        "capture file missing; cannot verify the ledger's test fields",
                        "run the suite and capture it to docs/TEST_OUTPUT.txt")]

    led = ledger.get("tests", {})
    for key in ("suites", "assertions", "failures"):
        if led.get(key) != cap[key]:
            out.append(Finding(
                "C1", LEDGER_REL.as_posix(), 0,
                f"ledger.tests.{key} = {led.get(key)!r} but the capture says {cap[key]!r}",
                "python3 tools/ledger_sync.py"))

    led_suites = led.get("per_suite", {}) or {}
    cap_suites = cap["per_suite"]
    for name in sorted(set(led_suites) | set(cap_suites)):
        a, b = led_suites.get(name), cap_suites.get(name)
        if a != b:
            out.append(Finding(
                "C1", LEDGER_REL.as_posix(), 0,
                f"per_suite[{name}] ledger={a!r} capture={b!r}",
                "python3 tools/ledger_sync.py"))

    if cap["failures"]:
        out.append(Finding("C1", CAPTURE_REL.as_posix(), 0,
                           f"the captured run has {cap['failures']} failure(s)",
                           "do not commit a capture with failures"))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# C2 — prose vs ledger
# ─────────────────────────────────────────────────────────────────────────────

# "1,372 assertions" / "20 suites" / "618 assertions across 12 suites"
COUNT_RE = re.compile(
    r"(?<![\w.])(\d{1,3}(?:,\d{3})*|\d+)\s*"
    r"(assertions?|suites?|checks? passed|passed)\b",
    re.IGNORECASE,
)


def _num(s: str) -> int:
    return int(s.replace(",", ""))


def check_prose_vs_ledger(root: Path, ledger: dict) -> List[Finding]:
    out: List[Finding] = []
    tests = ledger.get("tests", {})
    true_assertions = tests.get("assertions")
    true_suites = tests.get("suites")
    per_suite = set((tests.get("per_suite") or {}).values())
    # Some documents are frozen by design and must NOT be rewritten to match current
    # counts: a pre-registration edited after the fact is not a pre-registration, and the
    # claim inventory's job is to adjudicate historical figures, so it necessarily quotes
    # them. Per-line pragmas do not fit these — the figures span hard-wrapped blockquotes.
    quarantine = ledger.get("count_quarantine_paths", [])

    for path in walk_markdown(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        if IGNORE_FILE in text:
            continue
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(q) or rel == q.rstrip("/") for q in quarantine):
            continue
        lines = text.splitlines()
        for i, raw in enumerate(lines):
            if has_pragma(lines, i, ALLOW_COUNT):
                continue
            line = normalise(raw)
            for m in COUNT_RE.finditer(line):
                value, unit = _num(m.group(1)), m.group(2).lower()
                if unit.startswith("suite"):
                    if true_suites is not None and value != true_suites:
                        out.append(Finding(
                            "C2", rel, i + 1,
                            f"says {value} suites; the ledger says {true_suites}",
                            f"update to {true_suites}, or add <!-- {ALLOW_COUNT} --> "
                            f"if this is a labelled historical figure"))
                else:
                    if true_assertions is None:
                        continue
                    # a per-suite figure is legitimate; only flag totals that are wrong
                    if value == true_assertions or value in per_suite:
                        continue
                    out.append(Finding(
                        "C2", rel, i + 1,
                        f"says {value} {unit}; that is neither the total "
                        f"({true_assertions}) nor any per-suite count",
                        f"update to {true_assertions}, or add <!-- {ALLOW_COUNT} -->"))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# C3 — status vocabulary and agreement
# ─────────────────────────────────────────────────────────────────────────────

# Two ORTHOGONAL axes, and conflating them is a false positive:
#   BUILD status  — is the code written and verified?  PROVEN / BUILT-UNVALIDATED / DESIGNED
#   MEANING verdict — did an external yardstick grade it? NO-GO / NOT-YET / EARNED
# A brick is routinely BUILT-UNVALIDATED *and* NOT-YET at the same time (2c is exactly
# that). Only a BUILD status can contradict the ledger's build status.
BUILD_STATUS_ALIASES = {
    "BUILT · UNVALIDATED": "BUILT-UNVALIDATED",
    "BUILT UNVALIDATED": "BUILT-UNVALIDATED",
    "BUILT-UNVALIDATED": "BUILT-UNVALIDATED",
    "PROVEN": "PROVEN",
    "DESIGNED": "DESIGNED",
    "HORIZON": "HORIZON",
}
MEANING_VERDICTS = {"NO-GO", "NOT-YET", "NOT YET", "EARNED"}

# "1c", "1d-i", "1e-prime", "0b2"
BRICK_RE = re.compile(r"(?<![\w-])(\d[a-z]\d?(?:-i{1,2}|-prime)?)(?![\w-])")


def check_status_vocabulary(root: Path, ledger: dict) -> List[Finding]:
    out: List[Finding] = []
    valid = set(ledger.get("valid_statuses", []))
    bricks = ledger.get("bricks", {})
    build_pattern = re.compile(
        "|".join(re.escape(k) for k in sorted(BUILD_STATUS_ALIASES, key=len, reverse=True)))

    for path in walk_markdown(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        if IGNORE_FILE in text:
            continue
        rel = path.relative_to(root).as_posix()
        # the roadmap and the decision log narrate history, including superseded states
        if rel.endswith("nous_roadmap.md") or rel.endswith("DECISIONS.md"):
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines):
            statuses = {BUILD_STATUS_ALIASES[m.group(0)]
                        for m in build_pattern.finditer(line)}
            if not statuses:
                continue
            for s in statuses:
                if s not in valid:
                    out.append(Finding("C3", rel, i + 1,
                                       f"status {s!r} is not in ledger.valid_statuses"))
            ids = [m.group(1) for m in BRICK_RE.finditer(line) if m.group(1) in bricks]
            # Only adjudicate when the line is unambiguous: exactly ONE brick named and
            # exactly ONE build status asserted. A line discussing several bricks, or
            # listing the status vocabulary, is narration and is left alone.
            if len(set(ids)) != 1 or len(statuses) != 1:
                continue
            bid = ids[0]
            asserted = next(iter(statuses))
            expected = bricks[bid]["status"]
            # a ledger status outside the build axis (e.g. NO-GO) cannot be contradicted
            # by a build label; that pair is the two-axis case, not a conflict
            if expected not in BUILD_STATUS_ALIASES.values():
                continue
            if asserted != expected:
                out.append(Finding(
                    "C3", rel, i + 1,
                    f"brick {bid} is labelled {asserted!r} here but the ledger "
                    f"says {expected!r}",
                    "reconcile the document with tools/ledger.json, or update the "
                    "ledger via a DECISIONS.md entry"))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# C4 — forbidden claims
# ─────────────────────────────────────────────────────────────────────────────

# This project's documents are dense with DISCLAIMERS — "is not a validated cognitive
# model", "never 'what the system is conscious of'". A naive term scan flags the very
# discipline it exists to protect. So a term only counts when it is ASSERTED: no negation
# cue in the text immediately preceding it.
NEGATION_CUES = (
    "not", "never", "no ", "nor ", "n't", "cannot", "can not", "without",
    "rather than", "instead of", "forbidden", "forbid", "avoid", "refuse",
    "may not", "must not", "does not", "do not", "is not", "are not", "were not",
    "neither", "denies", "deny", "disclaim", "unearned", "unvalidated",
    "stop short", "falls short", "makes no", "make no", "none of",
)
NEGATION_WINDOW = 140  # characters before the match to search for a cue


def _is_negated(lines_low: List[str], idx: int, start: int) -> bool:
    """True if a negation cue precedes the match.

    These documents are hard-wrapped at ~90 characters, so the negation that governs a
    term routinely sits on the PREVIOUS line ("Using that vocabulary is NOT a\\nclaim of
    consciousness..."). Searching only the current line produced six false positives on
    the real repository, every one of them a disclaimer. So the window spans the previous
    line's tail as well.
    """
    prev = lines_low[idx - 1] if idx > 0 else ""
    context = prev + " " + lines_low[idx][:start]
    window = context[-NEGATION_WINDOW:]
    return any(cue in window for cue in NEGATION_CUES)


def check_forbidden_claims(root: Path, ledger: dict) -> List[Finding]:
    out: List[Finding] = []
    terms = [t.lower() for t in ledger.get("forbidden_claim_terms", [])]
    quarantine = ledger.get("claim_quarantine_paths", [])
    if not terms:
        return out

    targets = list(walk_markdown(root))
    targets += [p for p in sorted(root.rglob("*.py"))
                if not any(part in SKIP_DIRS for part in p.relative_to(root).parts)]

    for path in targets:
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(q) or rel == q.rstrip("/") for q in quarantine):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if IGNORE_FILE in text:
            continue
        lines = text.splitlines()
        lines_low = [ln.lower() for ln in lines]
        for i, low in enumerate(lines_low):
            if has_pragma(lines, i, ALLOW_CLAIM):
                continue
            for term in terms:
                pos = low.find(term)
                if pos < 0:
                    continue
                if _is_negated(lines_low, i, pos):
                    continue
                out.append(Finding(
                    "C4", rel, i + 1,
                    f"forbidden claim term {term!r} asserted without negation "
                    f"(CLAUDE.md rule 1)",
                    f"rephrase, or add <!-- {ALLOW_CLAIM} --> if this is a quotation "
                    f"of a vision document"))
                break
    return out


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────

RUNNER_REL = Path("run_tests.py")
SUITE_FILE_RE = re.compile(r'"(test_\S+?\.py)"')


def check_runner_completeness(root: Path, ledger: dict) -> List[Finding]:
    """Every suite on disk must be either registered in the runner or explicitly excused.

    The hole this closes: on 2026-07-25 a tester-authored suite sat in tests/ unregistered,
    capture_run captured a run that omitted it, and ledger_sync wrote the under-reported
    total into the ledger. The capture was internally consistent and wrong, which is exactly
    the failure the ledger exists to prevent. Nothing checked that the runner ran everything.
    """
    out: List[Finding] = []
    runner = root / RUNNER_REL
    if not runner.exists():
        return [Finding("C5", RUNNER_REL.as_posix(), 0, "no run_tests.py found")]

    registered = set(SUITE_FILE_RE.findall(runner.read_text(encoding="utf-8")))
    excused = dict(ledger.get("unregistered_suites", {}) or {})

    on_disk: List[Path] = []
    for sub in ("tests", "experiments"):
        d = root / sub
        if d.is_dir():
            on_disk += sorted(d.glob("test_*.py"))

    for p in on_disk:
        name = p.name
        if name in registered or name in excused:
            continue
        out.append(Finding(
            "C5", p.relative_to(root).as_posix(), 0,
            f"{name} exists but is neither registered in run_tests.py nor listed in "
            f"ledger.unregistered_suites",
            "register it in run_tests.py, or add it to unregistered_suites with the reason "
            "it is deliberately excluded"))

    disk_names = {p.name for p in on_disk}
    for name in sorted(set(registered) - disk_names):
        out.append(Finding("C5", RUNNER_REL.as_posix(), 0,
                           f"run_tests.py registers {name}, which does not exist"))
    for name in sorted(set(excused) - disk_names):
        out.append(Finding("C5", LEDGER_REL.as_posix(), 0,
                           f"unregistered_suites lists {name}, which does not exist",
                           "remove the stale entry"))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# C6 — the float-accumulation census
# ─────────────────────────────────────────────────────────────────────────────
#
# WHY THIS EXISTS (SPEC-0d §0.1). This project has met the naive-float-accumulation
# shape three times — nous_coalitions (BUG-0b1), nous_workspace:426 (SPEC-0c §2.5),
# nous_field:131 (SPEC-0c §2.7) — and every one was found by a person looking, never by
# a sweep. Twice the survivor sat in a file the previous fix's author had open. A fourth
# manual hunt has no better prior than the first three, so this is the sweep.
#
# WHAT IT DOES AND DOES NOT DECIDE. It does not rewrite anything and it does not judge
# whether a site is dangerous. It enumerates the sites and requires each one to be
# ADJUDICATED ONCE, in tools/ledger.json, with a reason. `math.fsum` sites are checked
# mechanically (the verdict must match the AST); everything else needs a human sentence.
#
# SCOPE, stated so the gate is never read as a whole-repository guarantee.
#
# A limitation here is a promise about what this tool does NOT do. It has to be exactly
# true, because a reader relies on it: the previous version of this block said "ADDITIVE
# reduction only", which a reader correctly took to include subtraction — and subtraction
# was not detected. `x -= v` is `x += (-v)` and is exactly as order-sensitive. That was a
# true-LOOKING sentence covering a real hole, which is the same defect class that failed
# this brick's own registry (D-021). Subtraction is now DETECTED; the wording below is the
# corrected promise.
#
#   * src/ ONLY. experiments/, tests/ and tools/ are NOT scanned.
#   * ADD and SUB only (`+`, `+=`, `-`, `-=`). Every other operator is out:
#       L1  multiplicative and division chains — `x *= k`, `x /= k` in a loop are equally
#           order-sensitive.            FALSIFIER: a `*=` fold in src/ that moves under permutation.
#   * The remaining shapes, each a KNOWN hole with a falsifier, each asserted as a negative
#     in tools/test_ledger.py so "the detector is clean" can never quietly mean "the
#     detector did not look":
#       L2  walrus — `if (acc := acc + v):`             FALSIFIER: a walrus fold in src/.
#       L3  CLOSED 2026-07-26 by SPEC-2f STEP ZERO (D-025), and CONVERTED rather than
#           deleted — a deleted limitation leaves no trace that the limit ever existed, a
#           converted one is a record of a capability gained. Tuple-target accumulation
#           (`a, b = a + x, b + y`) IS now detected, elementwise, for both plain-name and
#           subscript targets, and for `[a, b] = ...` list-target syntax which is the same
#           shape. Sites report as self-add / self-sub like any other: the kind names the
#           ARITHMETIC, not the syntax that carried it.
#           WHY IT WAS CLOSED BY 2f AND NOT BY 0d: the gate was blind at exactly the point
#           of use — `trace[rid], counts[rid] = trace[rid] + e, counts[rid] + 1` scored ZERO
#           while the same accumulation split over two lines was caught. Ownership belongs
#           to the brick that needs the coverage, and extending the gate is a normal cost of
#           building rather than an interruption to it.
#           POSITIVE ASSERTION, replacing the old negative: tools/test_ledger.py requires
#           the 2f line to be seen. FALSIFIER: a tuple fold in src/ that the census misses.
#       The pairing is POSITIONAL, so it is sound only when both sides are literal sequences
#       of equal length. Every unsound case is REFUSED rather than guessed, and each refusal
#       is a limitation below rather than a silence:
#       L11 STARRED elements on either side — `a, *b = ...`. A star makes position
#           non-positional, so no pairing is sound.  FALSIFIER: a starred fold in src/.
#       L12 NESTED sequence targets — `(a, (b, c)) = ...`. Not recursed into; the outer
#           pairing is refused wholesale rather than partially applied.
#                                                FALSIFIER: a nested-target fold in src/.
#       L13 A right-hand side that is not a literal sequence — `a, b = f()`. The pairing is
#           NOT STATICALLY KNOWABLE: which element of f()'s result lands in which target
#           cannot be read off the syntax, and guessing would be worse than refusing.
#                                                FALSIFIER: a fold through an unpacked call.
#       (Arity mismatch — `a, b = (x,)` — is also refused, but it is a runtime error rather
#        than a hole, so it is not a limitation. Noted so nobody adds it as one.)
#       L4  itertools.accumulate.                        FALSIFIER: an accumulate() over floats.
#       L5  `operator.add(acc, v)` called as a FUNCTION in a loop (the reduce ARGUMENT form
#           is detected; the direct-call form is not).   FALSIFIER: operator.add in a src/ loop.
#       L6  reduce with the DUNDER spelling `operator.__add__` (the plain spelling is
#           detected).                                   FALSIFIER: reduce(operator.__add__, xs).
#       L7  a FLOAT accumulator whose addend is an int literal — `weight += 1` is exempted
#           by the structural integer rule, which cannot see the accumulator's type.
#                                                        FALSIFIER: a float `x += 1` fold in src/.
#       L8  interprocedural laundering — `out[k] = _helper(prior, v)`. One hop through a
#           TEMPORARY is detected; a hop through a FUNCTION is not.
#                                                        FALSIFIER: a helper-based fold in src/.
#       L9  math.sumprod and numpy-style reductions.     FALSIFIER: math.sumprod in src/.
#       L10 Counter.update / dict-merge accumulation.    FALSIFIER: Counter.update over floats.
#     None of L1-L10 is implemented in this cycle by decision, not by oversight: whether any
#     is worth detecting is a scoping call, and a gate that never ships because it is still
#     being perfected is a gate that never guarded anything.

class CensusUnreadable(Exception):
    """src/ contains a module the census could not read.

    This is deliberately NOT a Finding. A Finding means "the repository is inconsistent"
    and exits 1; this means "the tool could not run" and exits 2, which is the documented
    contract at the top of this file. The distinction is the whole point: **exit 0 on
    source C6 could not read is the worst outcome this tool has, because it is
    indistinguishable from clean.** Exiting 1 is nearly as bad — it says the census ran and
    found a problem, when in fact the census did not run."""


class CaptureMalformed(Exception):
    """docs/TEST_OUTPUT.txt contains a suite header with no RESULT line — BRICK 0e.

    Exit 2, NOT a finding, and the reasoning is `CensusUnreadable`'s exactly. A finding
    (exit 1) means "the repository is inconsistent" and carries the implicit promise that
    the tool's own numbers are trustworthy. Here the numbers are precisely what cannot be
    trusted: a suite emitted a header, raised, and never reported, so every total derived
    from this capture understates the repository by an unknown amount.

    **Exit 0 was the old behaviour and it was the worst of the three**, because the parser
    silently dropped the suite and the shortfall was indistinguishable from a clean run —
    which is how this defect hid an unregistered suite, then a stale delta, then an entire
    334-assertion file, with C1 and C5 green throughout."""


SRC_REL = Path("src")
ACCUM_KEY = "float_accumulations"
VALID_VERDICTS = ("fsum", "registered")
# A floor on the reason, not a judgement of it. SPEC-0d §3.1's standard — a reason that
# explains rather than asserts — is a human call and is the tester's F-6, not this check's.
MIN_REASON_CHARS = 24

EXACT_REDUCERS = {"fsum"}                       # exactly rounded, order-independent
NAIVE_REDUCERS = {"sum", "mean", "fmean"}       # order-dependent in the last bits
# names whose result is an integer count, so math.fsum would be the WRONG fix (§2.2)
INT_CALLS = {"len", "int", "ord", "bit_count", "bit_length"}
SELF_READ_METHODS = {"get", "setdefault", "pop"}


@dataclass(frozen=True)
class Accumulation:
    """One adjudicable site. `key` is <path>:<scope>.<symbol> — deliberately NOT a line
    number, because a registry keyed by line rots on every insertion above it and trains
    people to re-key mechanically instead of re-reading."""
    key: str
    path: str
    line: int
    col: int
    kind: str      # fsum | builtin-sum | mean | fmean | reduce-add | aug-add | self-add
    symbol: str
    scope: str

    @property
    def exact(self) -> bool:
        return self.kind == "fsum"


@dataclass(frozen=True)
class Refusal:
    """A sequence assignment the scanner SAW and knowingly declined to fold (L11-L13, or an
    arity mismatch). Not a finding: the repository is not inconsistent because a fold was
    declined, so a refusal never fails the build. It is a countable, surfaced statement that
    the census looked here and chose not to answer."""
    path: str
    line: int
    col: int
    scope: str
    rule: str      # L11 | L12 | L13 | arity

    @property
    def detail(self) -> str:
        return _REFUSAL_RULES.get(self.rule, self.rule)


def _dotted(e) -> Optional[str]:
    """`self._t` -> 'self._t'; `x` -> 'x'; `grid[i]` -> 'grid[]'; anything else -> None.

    The subscript arm collapses the index deliberately. It exists so a nested accumulator —
    `grid[i][j] = grid[i][j] + v` — has a name to be compared under; without it the target
    resolves to None and the site is invisible. That hole was found by an assertion of this
    detector's own that turned out to be vacuously true."""
    if isinstance(e, ast.Name):
        return e.id
    if isinstance(e, ast.Attribute):
        base = _dotted(e.value)
        return f"{base}.{e.attr}" if base else None
    if isinstance(e, ast.Subscript):
        base = _dotted(e.value)
        return f"{base}[]" if base else None
    return None


def _container(e) -> Optional[str]:
    """The dotted name an assignment target writes into: `d[k]` -> 'd'."""
    if isinstance(e, ast.Subscript):
        return _dotted(e.value)
    return _dotted(e)


def _symbol_of(e) -> str:
    d = _container(e)
    if d is None:
        return "<expr>"
    return d[5:] if d.startswith("self.") else d


def _looks_integer(e) -> bool:
    """Integer EVIDENCE, structural — never the identifier's name.

    Exempting by name ('anything called *_count') would be a hole the day someone names a
    float `weight_count`. `road.traversal_count += 1` is exempt because the addend is an
    int literal, which is a fact about the code rather than about the vocabulary."""
    if isinstance(e, ast.Constant):
        return isinstance(e.value, int) and not isinstance(e.value, bool)
    if isinstance(e, ast.Call):
        return (_dotted(e.func) or "").split(".")[-1] in INT_CALLS
    if isinstance(e, ast.UnaryOp):
        return _looks_integer(e.operand)
    if isinstance(e, ast.BinOp):
        return _looks_integer(e.left) and _looks_integer(e.right)
    return False


def _sum_is_integer(call: ast.Call) -> bool:
    """`sum(1 for _ in xs)` and `sum(range(n))` are tallies; fsum would change their type."""
    if not call.args:
        return False
    a = call.args[0]
    if isinstance(a, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
        return _looks_integer(a.elt)
    if isinstance(a, ast.Call) and (_dotted(a.func) or "").split(".")[-1] == "range":
        return True
    if isinstance(a, (ast.List, ast.Tuple, ast.Set)):
        return bool(a.elts) and all(_looks_integer(x) for x in a.elts)
    return False


def _is_add_reduce(call: ast.Call) -> bool:
    """functools.reduce is only an accumulation when the operator is addition."""
    if not call.args:
        return False
    f = call.args[0]
    if (_dotted(f) or "") in {"operator.add", "operator.iadd", "add", "iadd"}:
        return True
    if isinstance(f, ast.Lambda) and isinstance(f.body, ast.BinOp) \
            and isinstance(f.body.op, ast.Add):
        return True
    return False


def _reducer_kind(call: ast.Call) -> Optional[str]:
    name = (_dotted(call.func) or "").split(".")[-1]
    if name in EXACT_REDUCERS:
        return "fsum"
    if name == "sum":
        return None if _sum_is_integer(call) else "builtin-sum"
    if name in NAIVE_REDUCERS:
        return name
    if name == "reduce":
        return "reduce-add" if _is_add_reduce(call) else None
    return None


def _reads_accumulator(e, container: Optional[str], aliases: Dict[str, str]) -> bool:
    """True if the subtree `e` reads the very thing being assigned to.

    Self-reference is what separates an ACCUMULATION from an ordinary two-term add. It is
    also what makes the term count unbounded: `flow[r] = flow.get(r, 0.0) + t` is a
    two-operand add per execution and an N-term reduction over the loop."""
    if container is None:
        return False
    for sub in ast.walk(e):
        if isinstance(sub, (ast.Name, ast.Attribute)) and _dotted(sub) == container:
            return True
        if isinstance(sub, ast.Subscript) and _dotted(sub.value) == container:
            return True
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
                and sub.func.attr in SELF_READ_METHODS \
                and _dotted(sub.func.value) == container:
            return True
        if isinstance(sub, ast.Name) and aliases.get(sub.id) == container:
            return True
    return False


def _self_ref_kind(tgt, value, aliases: Dict[str, str]) -> Optional[str]:
    """The self-referential test, factored out so ONE definition serves both the
    single-target form and the elementwise tuple-target form.

    Returns 'self-add' / 'self-sub' if `value` reads the thing `tgt` writes, under an
    additive operator, with a non-integer addend. Otherwise None."""
    container = _container(tgt)
    if container is None:
        return None
    for sub in ast.walk(value):
        if not (isinstance(sub, ast.BinOp) and isinstance(sub.op, (ast.Add, ast.Sub))):
            continue
        left = _reads_accumulator(sub.left, container, aliases)
        right = _reads_accumulator(sub.right, container, aliases)
        if not (left or right):
            continue
        if isinstance(sub.op, ast.Sub):
            # `x = x - v` accumulates; `x = v - x` REFLECTS (x alternates sign) and is
            # not the same shape, so subtraction only counts when the accumulator is on
            # the LEFT. Addition is commutative and counts on either side.
            if not left:
                continue
            addend = sub.right
        else:
            addend = sub.right if left else sub.left
        if _looks_integer(addend):
            continue
        return "self-add" if isinstance(sub.op, ast.Add) else "self-sub"
    return None


# Tuple-target accumulation. SPEC-2f STEP ZERO (D-025): closed by the brick that needed the
# coverage, before that brick wrote a line of its own mechanism.
#
# The shape that motivated it is the one 2f will write:
#     trace[rid], counts[rid] = trace[rid] + e, counts[rid] + 1
# Before this, C6 reported ZERO findings on that line while catching the identical
# accumulation split across two statements — the gate was blind at exactly the point of use.
#
# Pairing is positional and therefore only sound when both sides are literal sequences of
# equal length. Every case where it is NOT sound is refused rather than guessed, and each
# refusal is a stated limitation (L11-L13) rather than a silence.
_SEQ_TARGETS = (ast.Tuple, ast.List)      # `a, b = ...` and `[a, b] = ...` are one shape


# FINDING 2f-0-2 (tester, 2026-07-26). A refusal used to be indistinguishable from a clean
# pass: `scan_source` returned [] for a declined fold and [] for an empty file, so "I could
# not look" and "there is nothing here" were byte-identical to a caller. That is the
# exit-code contract's defect in a different costume, and it is the third time this project
# has met the shape.
#
# THE LINE, and it is drawn exactly here: **anything the scanner KNOWINGLY DECLINES is
# recorded; anything it simply NEVER MATCHED stays a documented limitation.** L1's
# multiplicative shape never matches — the scanner has nothing to report and L1 is unchanged.
# L11-L13 and the arity case are decisions taken with full knowledge of a sequence
# assignment the scanner could see and chose not to fold. Those, and only those, are
# recorded.
#
# `_NOT_A_SEQUENCE` is the case that must NOT become a refusal: a plain `a = f()` is the
# ordinary single-target path, not a decline. Conflating it would turn every assignment in
# src/ into a refusal record and the signal would be worthless within one commit.
_NOT_A_SEQUENCE = "not-a-sequence"
_REFUSAL_RULES = {
    "L11": "starred element — a star makes position non-positional",
    "L12": "nested sequence target — not recursed into",
    "L13": "right-hand side is not a literal sequence — pairing unknowable statically",
    "arity": "length mismatch — a runtime error, not a coverage hole",
}


def _pairing(tgt, value):
    """(pairs, refusal) for a sequence assignment. Exactly one is non-None.

    Single source of truth for both the fold and the refusal record, so the two can never
    drift into disagreeing about what was declined."""
    if not isinstance(tgt, _SEQ_TARGETS):
        return None, _NOT_A_SEQUENCE      # ordinary single-target form; NOT a decline
    if not isinstance(value, _SEQ_TARGETS):
        return None, "L13"                # `a, b = f()` — seen, and knowingly declined
    if any(isinstance(e, ast.Starred) for e in tgt.elts) \
            or any(isinstance(e, ast.Starred) for e in value.elts):
        return None, "L11"
    if any(isinstance(e, _SEQ_TARGETS) for e in tgt.elts):
        return None, "L12"
    if len(tgt.elts) != len(value.elts):
        return None, "arity"
    return list(zip(tgt.elts, value.elts)), None


def _paired_elements(tgt, value) -> Optional[List[Tuple[ast.AST, ast.AST]]]:
    """Elementwise (target, value) pairs for a sequence assignment, or None if the pairing
    is not statically sound. Returning None is a REFUSAL, not a miss: see L11-L13."""
    return _pairing(tgt, value)[0]


def _statement_refusals(st) -> List[str]:
    """The rules this statement's sequence targets were KNOWINGLY declined under.

    Empty for every statement that is not a sequence assignment — those were never
    matched, which is a limitation, not a decision."""
    if isinstance(st, ast.Assign):
        targets = list(st.targets)
    elif isinstance(st, ast.AnnAssign):
        targets = [st.target]
    else:
        return []
    if st.value is None:
        return []
    out = []
    for tgt in targets:
        rule = _pairing(tgt, st.value)[1]
        if rule is not None and rule != _NOT_A_SEQUENCE:
            out.append(rule)
    return out


def _statement_accumulations(st, aliases: Dict[str, str]) -> List[Tuple[str, str]]:
    """Every (kind, symbol) this statement accumulates into. A LIST because one tuple
    assignment can accumulate into several targets at once — which is precisely the shape
    that was invisible before."""
    if isinstance(st, ast.AugAssign) and isinstance(st.op, (ast.Add, ast.Sub)):
        if _container(st.target) is None or _looks_integer(st.value):
            return []
        kind = "aug-add" if isinstance(st.op, ast.Add) else "aug-sub"
        return [(kind, _symbol_of(st.target))]

    if isinstance(st, ast.Assign):
        targets = list(st.targets)
    elif isinstance(st, ast.AnnAssign):
        targets = [st.target]
    else:
        return []
    if st.value is None:
        return []

    # (1) sequence targets, paired elementwise. Each element is an INDEPENDENT site, so a
    #     line that accumulates into two things is two findings, not one.
    #
    #     FINDING 2f-0-1 (tester, 2026-07-26). The emission is DEDUPED on (kind, symbol).
    #     A chained assignment applies the same value to every target, so `a, b = c, d = ...`
    #     walks two target lists against one value; when the names repeat —
    #     `a, b = a, b = x + a, y + b` — the one accumulation into `a` was emitted twice.
    #     The surplus was not merely a wrong count: `scan_source`'s dedup renames the second
    #     to `<key>#2`, so the census grew a PHANTOM SITE, and a phantom site gets a reason
    #     written for it. A registry that invents work is worse than one that misses it,
    #     because the invented entry puts a false reason into the record — which is the
    #     failure this brick already had once (DEFECT 0d-1).
    #
    #     The dedup key is (kind, STRUCTURE of the target), not (kind, symbol). Symbol alone
    #     would be too coarse and would widen this fix into a coverage loss:
    #     `d[i], d[j] = d[i] + x, d[j] + y` is two genuinely distinct accumulations that both
    #     resolve to the symbol `d`, and collapsing them would make the tuple form report
    #     fewer sites than the identical code split across two statements — breaking the one
    #     property that closing L3 was for. `ast.dump` excludes positions by default, so
    #     `d[k]` written twice is one structure while `d[i]` and `d[j]` are two.
    out: List[Tuple[str, str]] = []
    seen: set = set()
    for tgt in targets:
        pairs = _paired_elements(tgt, st.value)
        if pairs is None:
            continue
        for sub_tgt, sub_val in pairs:
            kind = _self_ref_kind(sub_tgt, sub_val, aliases)
            if not kind:
                continue
            fingerprint = (kind, ast.dump(sub_tgt))
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            out.append((kind, _symbol_of(sub_tgt)))
    if out:
        return out

    # (2) the ordinary single-target form. First match wins, exactly as before — the
    #     tuple path above is additive and changes no existing count.
    for tgt in targets:
        kind = _self_ref_kind(tgt, st.value, aliases)
        if kind:
            return [(kind, _symbol_of(tgt))]
    return []


def _record_alias(st, aliases: Dict[str, str]) -> None:
    """One-hop dataflow: `prior = road.charges.get(f, 0.0)` makes `prior` a read of
    `road.charges`. Without this, an accumulation is hidden from the detector by the most
    natural refactor there is — pulling the previous value onto its own line."""
    if not (isinstance(st, ast.Assign) and len(st.targets) == 1
            and isinstance(st.targets[0], ast.Name)):
        return
    name = st.targets[0].id
    v = st.value
    src = None
    if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) \
            and v.func.attr in SELF_READ_METHODS:
        src = _dotted(v.func.value)
    elif isinstance(v, ast.Subscript):
        src = _dotted(v.value)
    elif isinstance(v, ast.Name) and v.id in aliases:
        src = aliases[v.id]              # a chain of plain renames is still one hop
    if src:
        aliases[name] = src
    else:
        aliases.pop(name, None)


# Fields that hold NESTED STATEMENTS. The expression scan must not descend into them
# (it would attribute a site to the wrong scope) and `walk` must descend into every one of
# them (or a statement there is invisible). `cases` is here because ast.Match keeps its
# bodies under match_case.body rather than under a field named `body` — which is exactly
# how match statements were being skipped: not by a decision, by a name.
_STMT_FIELDS = ("body", "orelse", "finalbody", "handlers", "cases")


def _non_stmt_children(node) -> Iterable[ast.AST]:
    """Every child that is not a nested statement list — so an expression scan can never
    wander into a nested function body and attribute a site to the wrong scope.

    For ast.Match the `cases` field is skipped wholesale here and handled in `walk`, which
    scans each case's pattern and guard as expressions and walks its body as statements."""
    for name, val in ast.iter_fields(node):
        if name in _STMT_FIELDS:
            continue
        for it in (val if isinstance(val, list) else [val]):
            if isinstance(it, ast.AST) and not isinstance(it, ast.stmt):
                yield it


def _scan_module(text: str, relpath: str) -> Tuple[List[Accumulation], List[Refusal]]:
    """One traversal, two products: the sites folded and the sequence assignments knowingly
    declined. They share a walk deliberately — a refusal recorded by a second, parallel
    traversal could disagree with the fold about what was declined, and a disagreement
    between them is exactly the failure the record exists to prevent."""
    tree = ast.parse(text)
    raw: List[Tuple[int, int, str, str, str]] = []   # line, col, kind, symbol, scope
    raw_ref: List[Tuple[int, int, str, str]] = []    # line, col, rule, scope

    def scope_name(scope: List[str]) -> str:
        return ".".join(scope)

    def scan_calls(node, scope: List[str], hint: str) -> None:
        if isinstance(node, ast.keyword) and node.arg:
            hint = node.arg
        if isinstance(node, ast.Call):
            kind = _reducer_kind(node)
            if kind:
                raw.append((node.lineno, node.col_offset, kind, hint, scope_name(scope)))
        for ch in ast.iter_child_nodes(node):
            scan_calls(ch, scope, hint)

    def stmt_hint(st) -> str:
        if isinstance(st, ast.Assign) and st.targets:
            return _symbol_of(st.targets[0])
        if isinstance(st, (ast.AnnAssign, ast.AugAssign)):
            return _symbol_of(st.target)
        if isinstance(st, ast.Return):
            return "<return>"
        return "<expr>"

    def walk(stmts, scope: List[str], aliases: Dict[str, str]) -> None:
        for st in stmts:
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # decorators, defaults and bases are evaluated in the OUTER scope
                for child in _non_stmt_children(st):
                    scan_calls(child, scope, "<signature>")
                walk(st.body, scope + [st.name], {})
                continue
            hint = stmt_hint(st)
            for child in _non_stmt_children(st):
                scan_calls(child, scope, hint)
            for acc in _statement_accumulations(st, aliases):
                raw.append((st.lineno, st.col_offset, acc[0], acc[1], scope_name(scope)))
            for rule in _statement_refusals(st):
                raw_ref.append((st.lineno, st.col_offset, rule, scope_name(scope)))
            _record_alias(st, aliases)
            for field in ("body", "orelse", "finalbody"):
                sub = getattr(st, field, None)
                if isinstance(sub, list):
                    walk([s for s in sub if isinstance(s, ast.stmt)], scope, aliases)
            for h in getattr(st, "handlers", []) or []:
                for child in _non_stmt_children(h):
                    scan_calls(child, scope, "<except>")
                walk(h.body, scope, aliases)
            # ast.Match (3.10+). Its bodies hang off match_case, not off a `body` field, so
            # the loop above cannot reach them. A traversal that silently skips a syntax
            # construct is the same failure as a parser that reads unreadable source as
            # clean — and this tool already treats that one as exit 2. src/ has no `match`
            # today; brick 2f is written next and may introduce one.
            for case in getattr(st, "cases", []) or []:
                for child in _non_stmt_children(case):
                    scan_calls(child, scope, "<case>")
                walk(case.body, scope, aliases)

    walk(tree.body, [], {})

    out: List[Accumulation] = []
    used: Dict[str, int] = {}
    for line, col, kind, symbol, scope in sorted(raw):
        key = f"{relpath}:{scope}.{symbol}" if scope else f"{relpath}:{symbol}"
        used[key] = used.get(key, 0) + 1
        if used[key] > 1:                      # two sites, one name: keep both adjudicable
            key = f"{key}#{used[key]}"
        out.append(Accumulation(key=key, path=relpath, line=line, col=col,
                                kind=kind, symbol=symbol, scope=scope))
    refusals = [Refusal(path=relpath, line=line, col=col, scope=scope, rule=rule)
                for line, col, rule, scope in sorted(raw_ref)]
    return out, refusals


def scan_source(text: str, relpath: str) -> List[Accumulation]:
    """Enumerate every additive float accumulation in one module."""
    return _scan_module(text, relpath)[0]


def scan_source_refusals(text: str, relpath: str) -> List[Refusal]:
    """Enumerate every sequence assignment this module declined to fold.

    A SEPARATE entry point rather than a wider return from `scan_source`, because
    `scan_source`'s contract — a list of sites — is depended on by both suites, and
    widening it to carry refusals would make every existing caller's `== []` mean
    something new without a single line of those callers changing."""
    return _scan_module(text, relpath)[1]


def scan_float_refusals(root: Path) -> List[Refusal]:
    """Every knowingly-declined sequence assignment in src/, in census order."""
    out: List[Refusal] = []
    src = root / SRC_REL
    if not src.is_dir():
        return out
    for p in sorted(src.rglob("*.py")):
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        rel = p.relative_to(root).as_posix()
        try:
            out.extend(scan_source_refusals(p.read_text(encoding="utf-8"), rel))
        except (UnicodeDecodeError, OSError, SyntaxError, ValueError) as e:
            # The census raises CensusUnreadable for these and is the authority on whether
            # the tool can run at all. This helper never invents a second opinion about it.
            raise CensusUnreadable(f"{rel}: cannot scan for refusals "
                                   f"({type(e).__name__})") from e
    return out


def scan_float_accumulations(root: Path) -> Tuple[List[Accumulation], List[Finding]]:
    """The census over src/. Returns (sites, tool-level findings)."""
    sites: List[Accumulation] = []
    problems: List[Finding] = []
    src = root / SRC_REL
    if not src.is_dir():
        return sites, problems
    for p in sorted(src.rglob("*.py")):
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        rel = p.relative_to(root).as_posix()
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            raise CensusUnreadable(f"{rel}: cannot read the file ({type(e).__name__}). "
                                   f"The census cannot certify a module it cannot read.") from e
        try:
            sites.extend(scan_source(text, rel))
        except SyntaxError as e:
            raise CensusUnreadable(f"{rel}:{e.lineno or 0}: cannot parse ({e.msg}). "
                                   f"The census cannot certify a module it cannot parse.") from e
        except ValueError as e:
            # NUL bytes and other malformed input. ast.parse raises ValueError on 3.10 where
            # later versions raise SyntaxError — so this arm is what makes the contract
            # identical on every interpreter rather than an artefact of the one you ran.
            raise CensusUnreadable(f"{rel}: cannot parse ({type(e).__name__}: {e}). "
                                   f"The census cannot certify a module it cannot parse.") from e
    return sites, problems


ABSENCE_KEY = "bound_on_absence"
ABSENCE_KINDS = ("attribute_read", "call")


def _absence_occurrences(root: Path, kind: str, symbol: str) -> List[Tuple[str, int]]:
    """Every place in src/ where `symbol` appears, for a registry reason that rests on it
    NOT appearing.

    DELIBERATELY BIASED TOWARD OVER-REPORTING, and the bias is the design.
    An attribute read cannot be resolved to a type without inference, so a bound on
    `ActivationField.flow` is enforced by flagging EVERY `.flow` read in src/ and making a
    human dismiss the ones that are a different type. That is the correct trade:

        a false positive costs one recorded sentence in the ledger;
        a false negative is a silently FALSE claim in the registry —
        which is precisely the failure that made this brick FAIL (D-021).

    Choosing the other bias is choosing the way we already lost once. If this ever reports
    so many occurrences that people dismiss them without reading, narrow the SYMBOL, never
    the check.
    """
    leaf = symbol.rsplit(".", 1)[-1]
    hits: List[Tuple[str, int]] = []
    src = root / SRC_REL
    if not src.is_dir():
        return hits
    for f in sorted(src.rglob("*.py")):
        if any(part in SKIP_DIRS for part in f.relative_to(root).parts):
            continue
        rel = f.relative_to(root).as_posix()
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (SyntaxError, ValueError, UnicodeDecodeError, OSError) as e:
            raise CensusUnreadable(f"{rel}: cannot read/parse while verifying an "
                                   f"absence bound ({type(e).__name__}).") from e
        for node in ast.walk(tree):
            if kind == "attribute_read":
                if isinstance(node, ast.Attribute) and node.attr == leaf \
                        and isinstance(getattr(node, "ctx", None), ast.Load):
                    hits.append((rel, node.lineno))
            elif kind == "call":
                if isinstance(node, ast.Call):
                    if (_dotted(node.func) or "").rsplit(".", 1)[-1] == leaf:
                        hits.append((rel, node.lineno))
    return hits


def _check_absence_bounds(root: Path, key: str, entry: dict) -> List[Finding]:
    """A reason that rests on an ABSENCE is the most fragile claim a registry can hold,
    because nothing enforces it. This makes the machine enforce it."""
    out: List[Finding] = []
    spec = entry.get(ABSENCE_KEY)
    if spec is None:
        return out
    if not isinstance(spec, list):
        return [Finding("C6", LEDGER_REL.as_posix(), 0,
                        f"{key}: {ABSENCE_KEY!r} must be a list of "
                        f"{{kind, symbol, dismissed?}} objects")]
    for item in spec:
        if not isinstance(item, dict) or item.get("kind") not in ABSENCE_KINDS \
                or not item.get("symbol"):
            out.append(Finding("C6", LEDGER_REL.as_posix(), 0,
                               f"{key}: each {ABSENCE_KEY} item needs a 'symbol' and a "
                               f"'kind' in {list(ABSENCE_KINDS)}"))
            continue
        kind, symbol = item["kind"], item["symbol"]
        dismissed = {str(d).split(" ", 1)[0] for d in (item.get("dismissed") or [])}
        for rel, line in _absence_occurrences(root, kind, symbol):
            if f"{rel}:{line}" in dismissed:
                continue
            out.append(Finding(
                "C6", rel, line,
                f"{key}: this entry's reason RESTS ON THE ABSENCE of {symbol} "
                f"({kind}), and {symbol} now appears here — the reason is now FALSE",
                f"re-adjudicate {key}: either its bound no longer holds and the entry "
                f"needs a new argument, or this occurrence is a different symbol and "
                f"belongs in its 'dismissed' list with the reason it does not count"))
    return out


def check_float_accumulation(root: Path, ledger: dict) -> List[Finding]:
    sites, out = scan_float_accumulations(root)
    registry = ledger.get(ACCUM_KEY)
    if registry is None:
        registry = {}
        if sites:
            out.append(Finding("C6", LEDGER_REL.as_posix(), 0,
                               f"the ledger has no {ACCUM_KEY!r} key, but src/ contains "
                               f"{len(sites)} float accumulation(s)",
                               f"add a {ACCUM_KEY!r} object; see SPEC-0d §2.3"))
    if not isinstance(registry, dict):
        return out + [Finding("C6", LEDGER_REL.as_posix(), 0,
                              f"{ACCUM_KEY!r} must be an object of "
                              f"<path>:<symbol> -> {{verdict, reason}}")]

    seen: Set[str] = set()
    for s in sites:
        seen.add(s.key)
        entry = registry.get(s.key)
        if entry is None:
            out.append(Finding(
                "C6", s.path, s.line,
                f"unregistered {s.kind} accumulation: {s.key}",
                "sum it with math.fsum, or register it in ledger."
                f"{ACCUM_KEY}[{s.key!r}] with a verdict and a reason that explains why "
                "this site cannot break (SPEC-0d §3.1 is the standard)"))
            continue
        if not isinstance(entry, dict):
            out.append(Finding("C6", LEDGER_REL.as_posix(), 0,
                               f"{s.key}: entry must be an object with verdict and reason"))
            continue
        verdict = entry.get("verdict")
        reason = (entry.get("reason") or "").strip()
        if verdict not in VALID_VERDICTS:
            out.append(Finding("C6", LEDGER_REL.as_posix(), 0,
                               f"{s.key}: verdict {verdict!r} is not one of "
                               f"{list(VALID_VERDICTS)}"))
        elif verdict == "fsum" and not s.exact:
            out.append(Finding(
                "C6", s.path, s.line,
                f"{s.key}: the registry says 'fsum' but the site is a {s.kind} "
                f"accumulation — the entry no longer describes the code",
                "re-adjudicate this site; a registry that can rot silently is a note again"))
        elif verdict == "registered" and s.exact:
            out.append(Finding(
                "C6", s.path, s.line,
                f"{s.key}: the registry says 'registered' but the site is now math.fsum",
                "set the verdict to 'fsum'"))
        if len(reason) < MIN_REASON_CHARS:
            out.append(Finding(
                "C6", LEDGER_REL.as_posix(), 0,
                f"{s.key}: the reason is {len(reason)} characters; a registry entry "
                f"without a reason is an approval, not an adjudication",
                "state why this site cannot break, so a later reader can check it"))
        out.extend(_check_absence_bounds(root, s.key, entry))

    for key in sorted(set(registry) - seen):
        out.append(Finding(
            "C6", LEDGER_REL.as_posix(), 0,
            f"{ACCUM_KEY} lists {key!r}, which no longer exists in src/",
            "remove the stale entry — a registry that outlives its sites stops being read"))
    return out


CHECKS = {
    "C1": ("ledger agrees with the captured test run", check_ledger_vs_capture),
    "C2": ("prose counts agree with the ledger",       check_prose_vs_ledger),
    "C3": ("status labels are valid and agree",        check_status_vocabulary),
    "C4": ("no forbidden claims outside quarantine",   check_forbidden_claims),
    "C5": ("every suite on disk is registered or excused", check_runner_completeness),
    "C6": ("every float accumulation in src/ is fsum or registered",
                                                       check_float_accumulation),
}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="repository root (default: .)")
    ap.add_argument("--only", default="", help="comma-separated check ids, e.g. C2,C4")
    ap.add_argument("--quiet", action="store_true", help="print findings only")
    ap.add_argument("--list-accumulations", action="store_true",
                    help="print C6's census of src/ and exit (for adjudication)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not (root / LEDGER_REL).exists():
        print(f"ledger_check: {LEDGER_REL} not found under {root}", file=sys.stderr)
        return 2

    ledger = load_ledger(root)

    if args.list_accumulations:
        try:
            sites, problems = scan_float_accumulations(root)
        except CensusUnreadable as e:
            print(f"ledger_check: the census could not run — {e}", file=sys.stderr)
            return 2
        registry = ledger.get(ACCUM_KEY) or {}
        for s in sites:
            entry = registry.get(s.key) or {}
            mark = entry.get("verdict") or "UNREGISTERED"
            print(f"{s.path}:{s.line:<4} {mark:<12} {s.kind:<12} {s.key}")
        # Refusals are listed ALONGSIDE the census, never mixed into it: a site is something
        # to adjudicate, a refusal is somewhere the census declined to look. Printing them
        # in one list would recreate the confusion the record exists to end.
        #
        # Each refusal line begins with REFUSED, deliberately NOT with the path. This
        # listing is CONSUMED, not merely read — the loop-closed test feeds it back as a
        # registry and takes the last token of every line starting with `src/` as a key. A
        # refusal that began with its path would be read back as a site, which would have
        # made the fix for "refusals are invisible" hand the census two phantom keys. The
        # `src/`-prefixed namespace belongs to sites alone.
        refusals = scan_float_refusals(root)
        if refusals:
            print()
            for r in refusals:
                print(f"REFUSED {r.rule:<6} {r.path}:{r.line:<4} "
                      f"{r.scope} — {r.detail}")
        print(f"\n{len(sites)} site(s) in {SRC_REL}/ "
              f"({sum(1 for s in sites if s.exact)} fsum, "
              f"{sum(1 for s in sites if not s.exact)} naive), "
              f"{len(refusals)} refusal(s)")
        if refusals:
            print("refusals are NOT findings and never fail the build — they are sequence "
                  "assignments the census saw and declined to fold (L11-L13, arity).")
        for f in problems:
            print(f.render())
        return 0
    selected = [c.strip().upper() for c in args.only.split(",") if c.strip()] or list(CHECKS)

    findings: List[Finding] = []
    for cid in selected:
        if cid not in CHECKS:
            print(f"ledger_check: unknown check {cid!r}", file=sys.stderr)
            return 2
        label, fn = CHECKS[cid]
        try:
            got = fn(root, ledger)
        except CensusUnreadable as e:
            # NOT a finding, and never exit 0 or 1: "the tool could not run" is exit 2.
            print(f"ledger_check: the census could not run — {e}", file=sys.stderr)
            return 2
        except CaptureMalformed as e:
            # BRICK 0e, and the same ruling for the same reason. A finding would claim
            # the tool's numbers are sound and the repository is not; here the numbers
            # themselves are unusable, so the honest exit is "could not run".
            print(f"ledger_check: the capture is malformed — {e}", file=sys.stderr)
            return 2
        findings.extend(got)
        if not args.quiet:
            mark = "FAIL" if got else "ok  "
            print(f"{mark}  {cid}  {label}" + (f"  ({len(got)})" if got else ""))

    if findings:
        print()
        print(f"{len(findings)} finding(s):\n")
        for f in findings:
            print(f.render())
            print()
        return 1

    if not args.quiet:
        print("\nledger_check: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
