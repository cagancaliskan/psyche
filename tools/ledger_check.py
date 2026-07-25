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
  C4 FORBIDDEN-CLAIMS    CONTRIBUTING.md rule 1 terms may not appear outside the quarantined
                         paths, unless the line carries an explicit allow pragma.

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
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

LEDGER_REL = Path("tools/ledger.json")
CAPTURE_REL = Path("docs/TEST_OUTPUT.txt")

SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build",
    ".obsidian",
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

    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = suite_re.match(raw)
        if m:
            current = m.group(1)
            continue
        m = result_re.match(raw)
        if m:
            passed, failed = int(m.group(1)), int(m.group(2))
            failures += failed
            if current:
                # a suite may print RESULT more than once only if malformed; last wins
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
                    f"(CONTRIBUTING.md rule 1)",
                    f"rephrase, or add <!-- {ALLOW_CLAIM} --> if this is a quotation "
                    f"of a vision document"))
                break
    return out


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────

CHECKS = {
    "C1": ("ledger agrees with the captured test run", check_ledger_vs_capture),
    "C2": ("prose counts agree with the ledger",       check_prose_vs_ledger),
    "C3": ("status labels are valid and agree",        check_status_vocabulary),
    "C4": ("no forbidden claims outside quarantine",   check_forbidden_claims),
}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="repository root (default: .)")
    ap.add_argument("--only", default="", help="comma-separated check ids, e.g. C2,C4")
    ap.add_argument("--quiet", action="store_true", help="print findings only")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not (root / LEDGER_REL).exists():
        print(f"ledger_check: {LEDGER_REL} not found under {root}", file=sys.stderr)
        return 2

    ledger = load_ledger(root)
    selected = [c.strip().upper() for c in args.only.split(",") if c.strip()] or list(CHECKS)

    findings: List[Finding] = []
    for cid in selected:
        if cid not in CHECKS:
            print(f"ledger_check: unknown check {cid!r}", file=sys.stderr)
            return 2
        label, fn = CHECKS[cid]
        got = fn(root, ledger)
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
