#!/usr/bin/env python3
"""check_copy.py — govern the public copy that tools/ledger_check.py never reads.

ledger_check scans Markdown, LaTeX and Python. The thesis-first restructure (D-031) adds
public surfaces in other formats: docs-site components and pages, Mermaid sources, SVG
assets, the string values of the thesis plan and those of the publication manifest. A count,
a claim or a stray Turkish word in any of them would publish ungoverned. This script applies
the same rules to them, by importing ledger_check rather than re-implementing it, so a rule
tightened there tightens here too.

Surfaces and the rules applied to each:

  copy surfaces                                   COUNT  CLAIM  THESIS  ENERGY  LANGUAGE
    website/src/**/*.{astro,tsx,ts,jsx,mdx,         x      x      x       x       x
                      js,mjs,cjs,json,mmd}
      (not website/src/content/docs/, which holds staged copies of governed docs, never
       node_modules, and not package*.json)
    website/astro.config.{mjs,ts,js,cjs,mts}        x      x      x       x       x
      (the site title and description shown on every page; the sidebar it loads,
       website/src/data/sidebar.json, is staged from docs/publish.json, is gitignored and
       does not exist where governance runs, so its labels are read at their source, the
       manifest, below)
    docs/assets/*.svg, website/src/**/*.svg,
      website/public/**/*.svg  (text nodes, plus
      aria-label / alt / title attributes)          x      x      x       x       x
    every string value in tools/thesis_plan.json    x      x      x       x       x
    every string value in docs/publish.json         x      x      x       x       x
      (tools/publish/stage.py makes each section title a site sidebar label and each page
       title, where one is given, a page's title; build_wiki.py puts both in the wiki's
       Home index and _Sidebar, inside Markdown, and each wiki value is a wiki page name,
       which GitHub shows with its hyphens as spaces. So every value is read as written,
       with "-" and "_" read as spaces, and as Markdown (check_disclosure.markup_forms of
       a .md), so a count or a term split by a hyphen, by emphasis ("618 **assertions**")
       or by an inline tag is seen as it renders. Every value
       is read, the _README lines, sources, slugs and never_publish entries too: they are
       public text in a public file, and reading only the rendered keys would let a new
       rendered key in unread.)

  prose (also read by ledger_check C2-C4)
    README.md, MOC.md, docs/thesis/**/*.md,
    thesis/**/*.md, website/**/*.md (not the
    staged copies, node_modules or dist)            *      *      x       x       x
    every page src in docs/publish.json not
      listed above (read through
      core.load_manifest), in the section
      titled "Thesis"                               *      *      x       x       x
      in any other section                          *      *      -       x       x

      Every page the manifest publishes is read, whatever the manifest adds later: the
      site's staged copy of a page (website/src/content/docs/) is not read, so the page is
      read at its source. THESIS applies to the public thesis surfaces (the list above,
      which is the thesis term list's own scope, and the pages of the section titled
      "Thesis"), not to a page in another section: Psyche's own pages (docs/PSYCHE.md,
      docs/ARCHITECTURE.md, docs/METHODOLOGY.md) are Psyche's record, ledger_check C4
      governs their claims, and the thesis term list is about thesis claims. A manifest
      core refuses still has its page sources read, as far as its shape allows; a source
      that does not exist is left out (publishable_guard refuses it wherever it is
      published), and a dangling link is exit 2.

      * ledger_check's C2 and C4 already apply COUNT and CLAIM to the raw lines of these
        files. Here COUNT and CLAIM run on every reading of them (raw included), and a
        finding C2 or C4 itself reports is dropped, so nothing is reported twice. What
        C2 and C4 report is reproduced exactly as they compute it: only on the files
        ledger_check's own walk_markdown yields (so a file reached through a symbolic link
        that its walk does not follow is never assumed read), on the text as it reads it
        (UTF-8 with replacement, universal newlines) split by str.splitlines() as it splits
        it (which also breaks at U+2028, U+2029, form feed, vertical tab, \\x1c-\\x1e and
        \\x85), with its own matching, pragmas and negation. A finding is dropped only on
        a line that the two splits agree on; anywhere else it is kept, even if that means
        reporting it twice. What is left is what they cannot see: a count or term split by
        inline markup (618<br/>assertions, 618 **assertions**, a term inside a Mermaid
        fence), a count or term wrapped across a line, a second term on one line, a
        negation C4 reads into a word ("Another"). A file that carries ledger_check's
        whole-file ignore token is skipped by C2 and C4, so every COUNT and CLAIM finding in
        it is reported here.

  not surfaces
    docs/diagrams/*.mmd are the archived report figures: D-030 keeps their render, they
    reach neither the docs site nor the wiki (the manifest publishes only Markdown pages,
    and nothing stages a .mmd from there), and the figures in them are historical by
    design, as docs/diagrams/README.md records; they stay in the repository as the record
    of that report. A stale figure in them is a record, not current copy, so they are not
    read here. A Mermaid source that the site itself carries (under website/src) is a copy
    surface like any other, and a Mermaid fence in governed Markdown is read with its page.

  COUNT     ledger_check's COUNT_RE against the ledger: a suite count must equal
            tests.suites; an assertion or "passed" figure must equal tests.assertions or
            one per-suite count (exactly C2's rule). Pragma: ledger:allow-count.
  CLAIM     ledger.json forbidden_claim_terms, asserted without negation (C4's rule).
            Pragma: ledger:allow-claim.
  THESIS    ledger.json thesis_forbidden_claim_terms (D-031), same negation logic.
            Pragma: ledger:allow-claim.
  ENERGY    an energy figure or an efficiency multiple: "<n> pJ" (also fJ, nJ, uJ, mJ and
            the micro sign), "<n>x fewer", "<n> times less", "<n>% fewer". The number may
            follow a letter or a dot, so "1e3 pJ", ".5 pJ" and "x10pJ" are caught. Energy
            appears only as an analytic estimate traced to a released result, so a bare
            number on a public surface is a finding. Pragma: ledger:allow-claim.
  LANGUAGE  any Turkish letter: everything public in this repository is English (D-031).
            Text is compared in Unicode NFC, so a letter written as a base letter plus a
            combining mark is caught. No pragma.

How text is read. Every surface is decoded as check_disclosure.decode_bytes decodes it (a
byte-order mark or the NUL pattern of UTF-16 picks the codec, UTF-8 otherwise), so a UTF-16
file is read as text, never as mojibake that passes every rule. Every surface is compared in
NFC. A multi-word term, a count and its unit, and an energy figure and its unit all match
across any run of whitespace, a line break included, and are reported at the line where they
start: Prettier often wraps "25\\n  suites" or "3.2\\n  pJ", and SVG tspans on separate lines
render as one phrase. LANGUAGE is judged line by line. Markup surfaces (.astro, .tsx, .jsx,
.mdx, .md, .mmd) are also read with tags removed and HTML entities decoded (Mermaid's own
#name; entities too), JSX-like files (.astro, .tsx, .jsx, .mdx) also with string-literal
expressions such as {" "} unwrapped first, and Markdown (.md, .mdx) also with emphasis, code
and link punctuation read as spaces, line numbers kept, so "3&nbsp;pJ", "618<br/>assertions"
or a term split by an inline tag or by {" "} is seen as it renders. These readings are
check_disclosure.markup_forms, so both checks read a page alike. Files whose string escapes
render (check_disclosure.ESCAPED_SUFFIXES: .ts, .tsx, .js, .json, .astro, .mdx and the
rest) are also read with \\xNN, \\uXXXX, \\u{...}, \\N{...} and octal escapes decoded, in
the raw text and in every markup reading, so a Turkish letter, a count or a term written
as an escape (as Python's json.dump writes generated data by default) is seen as it renders.
An escape that decodes to a line break is left as written, so line numbers hold.

Negation. A term counts only when asserted: no negation cue in the window before it. The
cues and the window are ledger_check's (NEGATION_CUES, NEGATION_WINDOW), but here each cue
must stand as a word: ledger_check matches cues as substrings, so "not" inside "Another",
"Notably" or "note" and "nor" inside "Minor" would negate a term. Otherwise each cue is
matched literally, as C4 matches it. Where ledger_check writes a cue with a trailing space
("no ", "nor "), an ASCII space must follow it here too, so "no.", "no-op", "no-one" and
"(no)" negate nothing, exactly as in C4 ("Phase no. 2" does not exempt a term). A
multi-word cue ("rather than", "instead of", "none of") counts only with its words joined
by one ASCII space, as C4's substring test requires: two spaces, a tab, or a non-breaking
space (written as U+00A0 or as &nbsp;) between them negate nothing. "n't" counts only with
the ASCII apostrophe: a typographic don't (U+2019), common in site copy, negates nothing
here, as in C4. Every cue is therefore at least as strict here as in C4, never looser, and
test_checks.py asserts each of these cases against C4's own test. tools/ledger_check.py
itself is unchanged; its C4 keeps its own matching on the files it reads.

Quarantine. The ledger's count_quarantine_paths exempt a path from COUNT, and its
claim_quarantine_paths from CLAIM, THESIS and ENERGY, matched exactly as C2 and C4 match
them (a path prefix, or the path itself). LANGUAGE has no exemption.

Pragmas count on their own line or the line above, as in ledger_check, read from the source
lines. A pragma inside an HTML or XML comment also counts on the line where that comment
closes and the line after it, wherever the comment opens: a comment that runs over several
lines (a pragma with its reason) and closes right before a figure immediately precedes it,
as a one-line pragma does. A comment that closed two or more lines earlier covers nothing.
(ledger_check C2 and C4 do not read a comment this way; a raw-line finding they report
stays theirs.) In an SVG they are read from the source lines too, by the line a text node
sits on, so an XML comment <!-- ledger:allow-count --> on the line above a <text> node
works. The
whole-file ignore pragma that ledger_check honours is NOT honoured here: these are public
surfaces, and a whole-file exemption has no legitimate use on one. A string in
tools/thesis_plan.json or docs/publish.json cannot carry a pragma (anything written in it
would render as copy): a plan or manifest finding is fixed by rewording, or by the
quarantine lists.

Walking. Directories skipped: node_modules, .git, __pycache__, .astro, dist, and .venv, venv
and build (as ledger_check skips them). A directory reached through a symbolic link is
followed, as the site build follows it; a link back to a directory the walk is already
inside is not entered twice (its content is read there). ledger_check's own walk may not
follow such a link, so a prose file reached through one keeps every COUNT and CLAIM finding
here (see the prose note above).

Known limit: a term is matched as a substring, as C4 matches it, so a benign phrase that
contains one is a finding (THESIS "is the first" inside "Gate A is the first of three
gates"); reword it.

Output: one finding per line, `path:line: [RULE] message`. Exit 0 = clean, 1 = findings,
2 = the check could not run: no ledger or a ledger of the wrong shape, ledger_check or
check_disclosure not importable, or a surface that cannot be read or parsed (a dangling
link, a directory the walk cannot list, a malformed SVG, a plan or manifest that is not JSON
or repeats a key). A surface nobody read is never reported as clean. Missing directories and
a missing plan or manifest file are fine (core.load_manifest refuses a missing manifest
wherever one is needed). A ledger whose forbidden_claim_terms or thesis_forbidden_claim_terms
(required since D-031) is absent, holds no term, or holds a blank term is of the wrong
shape: one ledger edit must not switch the CLAIM or THESIS rule off unseen, so the check
refuses to run rather than pass.

Usage:
    python3 tools/publish/check_copy.py
    python3 tools/publish/check_copy.py --root PATH [--quiet] [--list]

Stdlib only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
from xml.parsers import expat

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent


def _load(name: str, path: Path):
    """Import a module by path, whatever the current directory."""
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    # registered before exec: dataclasses resolve their module through sys.modules
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return mod


def _load_error(label: str, e: BaseException) -> str:
    """Why a sibling could not be imported, without the absolute path an OSError carries."""
    where = f", line {e.lineno}" if isinstance(e, SyntaxError) and e.lineno else ""
    return f"{label} ({type(e).__name__}{where})"


LC = None
CD = None
CORE = None
LOAD_ERROR: Optional[str] = None
_loading = "tools/ledger_check.py"
try:
    LC = _load("ledger_check", HERE.parent / "ledger_check.py")
    _loading = "tools/publish/check_disclosure.py"
    CD = _load("check_disclosure", HERE / "check_disclosure.py")
    _loading = "tools/publish/core.py"
    CORE = _load("core", HERE / "core.py")
except Exception as _e:          # reported by main() as exit 2, never as a finding
    LOAD_ERROR = _load_error(_loading, _e)

PLAN_REL = "tools/thesis_plan.json"
MANIFEST_REL = "docs/publish.json"
STAGED_REL = "website/src/content/docs/"
# ledger_check skips .venv, venv and build as well; a local virtual environment under
# thesis/ would otherwise have its site-packages read as thesis prose
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".astro", "dist", ".venv", "venv", "build"}
CODE_SUFFIXES = {".astro", ".tsx", ".ts", ".jsx", ".mdx", ".js", ".mjs", ".cjs", ".json",
                 ".mmd"}
# read through check_disclosure.markup_forms (tags stripped, entities decoded); kept here so
# the set of surfaces read as markup is visible, and checked against CD's set in main()
MARKUP_SUFFIXES = {".astro", ".tsx", ".jsx", ".mdx", ".md", ".mmd"}
MARKDOWN_SUFFIXES = {".mdx", ".md"}
SITE_CONFIGS = ("astro.config.mjs", "astro.config.ts", "astro.config.js", "astro.config.cjs",
                "astro.config.mts")
# xlink:title is the SVG 1.1 tooltip a browser shows; read as copy like title
SVG_ATTRS = ("aria-label", "alt", "title", "xlink:title")

# Escaped on purpose: this file sits on an English-only path, and a literal letter in it
# would trip the very rule it defines.
TURKISH_RE = re.compile("[\u00e7\u011f\u0131\u00f6\u015f\u00fc\u00c7\u011e\u0130\u00d6\u015e\u00dc]")

# (?<!\d) only keeps a match from starting inside a number; a letter or a dot before the
# number is allowed, so scientific notation ("1e3 pJ", "2.3e2 pJ"), a leading-dot decimal
# (".5 pJ") and a glued figure ("x10pJ", "a10x fewer") are all caught, as the spec regexes
# \d+(\.\d+)?\s*(pJ|nJ|mJ)\b and \d+\s*[x\u00d7]\s*(fewer|less) catch them. "fewer|less"
# carries no trailing \b, as the spec regex carries none, so "10x lesser" and "10\u00d7
# lessened" are caught too. \s* also crosses a line break: these run over a surface's lines
# joined (see Rules.energy_at).
ENERGY_RES = (
    re.compile(r"(?<!\d)\d+(?:[.,]\d+)?\s*(?:fJ|pJ|nJ|uJ|\u00b5J|\u03bcJ|mJ)\b"),
    re.compile(r"(?<!\d)\d+(?:\.\d+)?\s*(?:[x\u00d7]|times)\s*(?:fewer|less)",
               re.IGNORECASE),
    re.compile(r"(?<!\d)\d+(?:\.\d+)?\s*%\s*(?:fewer|less)", re.IGNORECASE),
)

ALL_RULES = ("COUNT", "CLAIM", "THESIS", "ENERGY", "LANGUAGE")
PROSE_RULES = ("THESIS", "ENERGY", "LANGUAGE")
# a published page outside the thesis surfaces (a manifest page outside the section titled
# "Thesis"): Psyche's own pages are Psyche's record, and the thesis term list is about
# thesis claims, so THESIS does not apply; ledger_check C4 governs their claims
PAGE_RULES = ("ENERGY", "LANGUAGE")
THESIS_SECTION = "Thesis"
# on prose, ledger_check C2 and C4 apply these to the raw lines already
LEDGER_RULES = ("COUNT", "CLAIM")

CLAIM_TEXT = "forbidden claim term {!r} asserted without negation (CLAUDE.md rule 1)"
THESIS_TEXT = "thesis claim term {!r} asserted without negation (D-031, CLAUDE.md rule 1)"

# A negation cue whose last word is one of these must end at a word boundary ("not" is not
# "note"); the others may take a suffix ("avoid" also reads "avoided", "disclaim" also reads
# "disclaimer").
WHOLE_WORD_CUE_ENDS = {"not", "no", "nor", "never", "of", "than", "deny"}


class SurfaceUnreadable(Exception):
    """A surface could not be read or parsed. Exit 2: a surface nobody read is not clean."""


class LedgerInvalid(Exception):
    """tools/ledger.json has the wrong shape. Exit 2."""


@dataclass(frozen=True)
class CopyFinding:
    path: str
    line: int
    rule: str
    message: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: [{self.rule}] {self.message}"


@dataclass
class Unit:
    """Lines to check. `numbers[i]` is the source line of line i; `raw[i]` is what pragmas
    are read from (unless `allow_count` / `allow_claim` give them, as for an SVG, whose
    pragmas sit on source lines that hold no text); every list in `variants` is a rendering
    with one entry per line, `variants[0]` being `raw`."""
    path: str
    raw: List[str]
    numbers: List[int]
    variants: List[List[str]]
    rules: Tuple[str, ...]
    where: List[str]          # per-line suffix for the message ('' or ' (at /json/path)')
    allow_count: Optional[List[bool]] = None
    allow_claim: Optional[List[bool]] = None
    # prose that ledger_check C2/C4 read: the text exactly as ledger_check reads it (None
    # when it does not read the file); their own findings on it are dropped here
    ledger_text: Optional[str] = None
    # the text `raw` was split from (\n line breaks only), to place ledger_check's lines
    text: str = ""

    @property
    def ledger_reads(self) -> bool:
        return self.ledger_text is not None


# ─────────────────────────────────────────────────────────────────────────────
# rules
# ─────────────────────────────────────────────────────────────────────────────

def _negation_re() -> "re.Pattern[str]":
    """ledger_check's NEGATION_CUES, each required to stand as a word, and otherwise read
    exactly as C4 reads it: C4 tests each cue as a literal substring, so a looser cue here
    would exempt a term C4's own rule asserts. A multi-word cue is its own text, its words
    joined by one ASCII space ("rather  than", a tab, or "instead&nbsp;of" read as U+00A0
    negate nothing, as in C4); "n't" takes only the ASCII apostrophe (a typographic don't
    with U+2019 negates nothing, as in C4); a cue ledger_check writes with a trailing space
    ("no ", "nor ") must be followed by an ASCII space ("no.", "no-op" and "no" before a
    tab or U+00A0 negate nothing). The window joins the previous line to this one with an
    ASCII space, as C4's does, so a cue wrapped across a line break still reads whole."""
    parts = []
    for cue in LC.NEGATION_CUES:
        low = cue.lower()
        c = low.strip()
        if not c:
            continue
        if c == "n't":
            parts.append(r"(?<=[a-z])n't(?!\w)")
            continue
        words = c.split()
        body = re.escape(c)
        if low != low.rstrip():
            tail = r"(?= )"
        elif words[-1] in WHOLE_WORD_CUE_ENDS:
            tail = r"(?!\w)"
        else:
            tail = ""
        parts.append(r"(?<!\w)" + body + tail)
    return re.compile("|".join(parts))


def _term_re(term: str) -> "re.Pattern[str]":
    return re.compile(r"\s+".join(re.escape(w) for w in term.split()))


def _int_or_none(v) -> bool:
    return v is None or (isinstance(v, int) and not isinstance(v, bool))


def _str_list(ledger: dict, key: str) -> List[str]:
    v = ledger.get(key)
    if v is None:
        return []
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise LedgerInvalid(f"tools/ledger.json: {key} must be a list of strings")
    return v


def _quarantined(rel: str, paths: Sequence[str]) -> bool:
    """C2's and C4's own test."""
    return any(rel.startswith(q) or rel == q.rstrip("/") for q in paths)


class Rules:
    def __init__(self, ledger):
        if not isinstance(ledger, dict):
            raise LedgerInvalid("tools/ledger.json is not a JSON object")
        tests = ledger.get("tests")
        tests = {} if tests is None else tests
        if not isinstance(tests, dict):
            raise LedgerInvalid("tools/ledger.json: tests must be an object")
        self.true_suites = tests.get("suites")
        self.true_assertions = tests.get("assertions")
        if not (_int_or_none(self.true_suites) and _int_or_none(self.true_assertions)):
            raise LedgerInvalid("tools/ledger.json: tests.suites and tests.assertions must "
                                "be integers")
        per_suite = tests.get("per_suite")
        per_suite = {} if per_suite is None else per_suite
        if not isinstance(per_suite, dict) or not all(
                _int_or_none(v) and v is not None for v in per_suite.values()):
            raise LedgerInvalid("tools/ledger.json: tests.per_suite must map suites to "
                                "integers")
        self.per_suite = set(per_suite.values())
        # Both term lists must be present and hold at least one non-blank term: an absent
        # key, an empty list, a misspelt "terms" key, a null or a blank term would switch a
        # rule off (or, for a blank term, make it meaningless) with one unseen ledger edit.
        # D-031 made thesis_forbidden_claim_terms part of the ledger, so its absence is an
        # invalid ledger too, never a notice.
        if "forbidden_claim_terms" not in ledger:
            raise LedgerInvalid("tools/ledger.json has no forbidden_claim_terms; without "
                                "them the CLAIM rule would not run")
        self.claim_terms = [t.lower() for t in _str_list(ledger, "forbidden_claim_terms")]
        if not self.claim_terms or any(not t.strip() for t in self.claim_terms):
            raise LedgerInvalid("tools/ledger.json: forbidden_claim_terms must hold at least "
                                "one term, and no blank term")
        if "thesis_forbidden_claim_terms" not in ledger:
            raise LedgerInvalid("tools/ledger.json has no thesis_forbidden_claim_terms "
                                "(required since D-031); without them the THESIS rule "
                                "would not run")
        raw = ledger.get("thesis_forbidden_claim_terms")
        if isinstance(raw, dict):
            raw = raw.get("terms")
        if not isinstance(raw, list) or not all(isinstance(t, str) for t in raw):
            raise LedgerInvalid("tools/ledger.json: thesis_forbidden_claim_terms must be "
                                "a list of strings, or an object whose 'terms' is one")
        if not raw or any(not t.strip() for t in raw):
            raise LedgerInvalid("tools/ledger.json: thesis_forbidden_claim_terms must hold "
                                "at least one term, and no blank term")
        self.thesis_terms = [t.lower() for t in raw]
        self.count_quarantine = _str_list(ledger, "count_quarantine_paths")
        self.claim_quarantine = _str_list(ledger, "claim_quarantine_paths")
        self.term_res: Dict[str, "re.Pattern[str]"] = {
            t: _term_re(t) for t in self.claim_terms + self.thesis_terms if t.strip()}
        self.negation = _negation_re()

    # COUNT ───────────────────────────────────────────────────────────────────
    def counts_at(self, text: str) -> List[Tuple[int, str]]:
        """(start, message) for every count in `text` (already normalised) that disagrees
        with the ledger. COUNT_RE's \\s* crosses a line break, so `text` may be a surface's
        lines joined: "25\\n  suites" is one count."""
        out: List[Tuple[int, str]] = []
        for m in LC.COUNT_RE.finditer(text):
            value, unit = LC._num(m.group(1)), m.group(2).lower()
            if unit.startswith("suite"):
                if self.true_suites is not None and value != self.true_suites:
                    out.append((m.start(),
                                f"says {value} suites; the ledger says {self.true_suites}"))
            elif self.true_assertions is not None:
                if value == self.true_assertions or value in self.per_suite:
                    continue
                out.append((m.start(), f"says {value} {unit}; that is neither the total "
                                       f"({self.true_assertions}) nor any per-suite count"))
        return out

    def counts(self, line: str) -> List[str]:
        """C2's per-line rule, in check_copy's wording."""
        return [msg for _, msg in self.counts_at(LC.normalise(line))]

    # CLAIM / THESIS ──────────────────────────────────────────────────────────
    def negated(self, lines_low: List[str], idx: int, start: int) -> bool:
        """ledger_check's window (the previous line's tail and this line up to the term),
        searched for a cue that stands as a word."""
        prev = lines_low[idx - 1] if idx > 0 else ""
        context = prev + " " + lines_low[idx][:start]
        return self.negation.search(context, max(0, len(context) - LC.NEGATION_WINDOW)) \
            is not None

    def term_hits(self, terms: Sequence[str], lines_low: List[str]) -> Set[Tuple[int, str]]:
        """(line index, term) for every asserted term; a term may span a line break."""
        text = "\n".join(lines_low)
        starts = [0]
        for ln in lines_low[:-1]:
            starts.append(starts[-1] + len(ln) + 1)
        out: Set[Tuple[int, str]] = set()
        for term in terms:
            rx = self.term_res.get(term)
            if rx is None:
                continue
            for m in rx.finditer(text):
                idx = bisect_right(starts, m.start()) - 1
                if not self.negated(lines_low, idx, m.start() - starts[idx]):
                    out.add((idx, term))
        return out

    # ENERGY ──────────────────────────────────────────────────────────────────
    @staticmethod
    def energy_at(text: str) -> List[int]:
        """The start of every energy figure or multiple in `text`, which may be a surface's
        lines joined ("3.2\\n  pJ" is one figure)."""
        return sorted({m.start() for rx in ENERGY_RES for m in rx.finditer(text)})

    @staticmethod
    def energy(line: str) -> bool:
        return any(rx.search(line) for rx in ENERGY_RES)

    # LANGUAGE ────────────────────────────────────────────────────────────────
    @staticmethod
    def language(line: str) -> Optional[str]:
        t = CD.nfc(line)
        m = TURKISH_RE.search(t) or CD.TURKISH_MARK_RE.search(t)
        return f"U+{ord(m.group(0)):04X}" if m else None

    def count_quarantined(self, rel: str) -> bool:
        return _quarantined(rel, self.count_quarantine)

    def claim_quarantined(self, rel: str) -> bool:
        return _quarantined(rel, self.claim_quarantine)


def _line_map(ledger_text: str, text: str) -> Dict[int, int]:
    """{ledger_check line index: check_copy line number} for every line the two splits agree
    on: ledger_check splits its text with str.splitlines() (which also breaks at U+2028,
    U+2029, form feed, vertical tab, \\x1c-\\x1e and \\x85), check_copy splits `text` on \\n
    only. A line maps when it starts at the same offset and holds the same characters in
    both. A leading byte-order mark, which ledger_check keeps and check_copy's decoder
    strips, is set aside first (it changes no C2 or C4 result). If the two texts differ
    otherwise (a UTF-16 file, which ledger_check reads as UTF-8), nothing maps, so nothing
    is dropped."""
    lc = ledger_text[1:] if ledger_text.startswith("\ufeff") and \
        not text.startswith("\ufeff") else ledger_text
    if lc != text:
        return {}
    cc_lines = text.split("\n")
    cc_index: Dict[int, int] = {}
    pos = 0
    for n, ln in enumerate(cc_lines):
        cc_index[pos] = n
        pos += len(ln) + 1
    out: Dict[int, int] = {}
    pos = 0
    for k, piece in enumerate(lc.splitlines(keepends=True)):
        body = piece.splitlines()[0] if piece.splitlines() else ""
        n = cc_index.get(pos)
        if n is not None and cc_lines[n] == body:
            out[k] = n + 1
        pos += len(piece)
    return out


def ledger_check_reports(rules: Rules, unit: Unit) -> Set[CopyFinding]:
    """The COUNT and CLAIM findings ledger_check C2 and C4 themselves report on this unit,
    in check_copy's wording: computed on ledger_check's own text and its own line split
    (C2's per-line count rule; C4's per-line rule: substring term, its own negation test,
    at most the first asserted term on a line), and kept only on lines where its split and
    check_copy's agree, so a finding is dropped here only when ledger_check reports that
    very line. Empty when ledger_check does not read the file."""
    out: Set[CopyFinding] = set()
    if unit.ledger_text is None:
        return out
    mapping = _line_map(unit.ledger_text, unit.text)
    if not mapping:
        return out
    path = unit.path
    lc = unit.ledger_text[1:] if unit.ledger_text.startswith("\ufeff") and \
        not unit.text.startswith("\ufeff") else unit.ledger_text
    lines = lc.splitlines()
    low = [x.lower() for x in lines]
    count_ok = not rules.count_quarantined(path)
    claim_ok = not rules.claim_quarantined(path)
    for i, raw in enumerate(lines):
        n = mapping.get(i)
        if n is None:
            continue
        where = unit.where[n - 1]
        if count_ok and not LC.has_pragma(lines, i, LC.ALLOW_COUNT):
            for msg in rules.counts(raw):
                out.add(CopyFinding(path, n, "COUNT", msg + where))
        if claim_ok and not LC.has_pragma(lines, i, LC.ALLOW_CLAIM):
            for term in rules.claim_terms:
                pos = low[i].find(term)
                if pos < 0 or LC._is_negated(low, i, pos):
                    continue
                out.add(CopyFinding(path, n, "CLAIM", CLAIM_TEXT.format(term) + where))
                break
    return out


def _joined(lines: List[str]) -> Tuple[str, List[int]]:
    """`lines` joined by \\n, and the offset at which each line starts."""
    starts = [0]
    for ln in lines[:-1]:
        starts.append(starts[-1] + len(ln) + 1)
    return "\n".join(lines), starts


# an HTML or XML comment, which closes at the first "-->" after it opens
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def pragma_lines(lines: List[str], pragma: str) -> List[bool]:
    """For each of `lines`, whether `pragma` covers it: ledger_check's rule (the token on the
    line or the line above, LC.has_pragma), or the token inside an HTML or XML comment that
    closes on the line or the line above, wherever that comment opens. A comment that runs
    over several lines and closes right before a figure is a pragma that immediately
    precedes it; a comment that closed two or more lines earlier covers nothing."""
    out = [LC.has_pragma(lines, i, pragma) for i in range(len(lines))]
    text, starts = _joined(lines)
    for m in _COMMENT_RE.finditer(text):
        if pragma not in m.group():
            continue
        end = bisect_right(starts, m.end() - 1) - 1     # the line holding the "-->"
        for i in (end, end + 1):
            if i < len(out):
                out[i] = True
    return out


ENERGY_TEXT = ("an energy figure or efficiency multiple on a public surface; energy appears "
               "only as an analytic estimate traced to a released result")


def check_unit(rules: Rules, unit: Unit) -> List[CopyFinding]:
    found: Set[CopyFinding] = set()
    path = unit.path
    do_count = "COUNT" in unit.rules and not rules.count_quarantined(path)
    claims_ok = not rules.claim_quarantined(path)
    allow_count = unit.allow_count if unit.allow_count is not None else \
        pragma_lines(unit.raw, LC.ALLOW_COUNT)
    allow_claim = unit.allow_claim if unit.allow_claim is not None else \
        pragma_lines(unit.raw, LC.ALLOW_CLAIM)

    for variant in unit.variants:
        lines = [CD.nfc(x) for x in variant]
        # COUNT and ENERGY over the lines joined, so a figure wrapped away from its unit is
        # seen; each is reported, and its pragma read, at the line where it starts
        if do_count:
            text, starts = _joined([LC.normalise(x) for x in lines])
            for pos, msg in rules.counts_at(text):
                i = bisect_right(starts, pos) - 1
                if not allow_count[i]:
                    found.add(CopyFinding(path, unit.numbers[i], "COUNT", msg + unit.where[i]))
        if "ENERGY" in unit.rules and claims_ok:
            text, starts = _joined(lines)
            for pos in rules.energy_at(text):
                i = bisect_right(starts, pos) - 1
                if not allow_claim[i]:
                    found.add(CopyFinding(path, unit.numbers[i], "ENERGY",
                                          ENERGY_TEXT + unit.where[i]))
        for i, line in enumerate(lines):
            n, where = unit.numbers[i], unit.where[i]
            if "LANGUAGE" in unit.rules:
                cp = rules.language(line)
                if cp:
                    found.add(CopyFinding(
                        path, n, "LANGUAGE",
                        f"Turkish letter {cp} on an English-only surface (D-031){where}"))
        if not claims_ok:
            continue
        lines_low = [x.lower() for x in lines]
        for rule, terms, text in (("CLAIM", rules.claim_terms, CLAIM_TEXT),
                                  ("THESIS", rules.thesis_terms, THESIS_TEXT)):
            if rule not in unit.rules:
                continue
            for i, term in rules.term_hits(terms, lines_low):
                if allow_claim[i]:
                    continue
                found.add(CopyFinding(path, unit.numbers[i], rule,
                                      text.format(term) + unit.where[i]))
    found -= ledger_check_reports(rules, unit)
    return sorted(found, key=lambda f: (f.line, f.rule, f.message))


# ─────────────────────────────────────────────────────────────────────────────
# surfaces
# ─────────────────────────────────────────────────────────────────────────────

def _rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


def _walk(root: Path, base_rel: str, suffixes: Iterable[str],
          exclude_prefix: str = "") -> List[Path]:
    base = root / base_rel
    if not base.is_dir():
        return []
    want = {s.lower() for s in suffixes}
    found: List[Path] = []
    top = str(base)

    def fail(err: OSError) -> None:
        where = err.filename if isinstance(err.filename, str) else top
        try:
            shown = _rel(root, Path(where))
        except ValueError:
            shown = base_rel
        raise SurfaceUnreadable(f"{shown}: cannot be read ({type(err).__name__})")

    # Directories reached through a link are followed (the site build follows them). The
    # real paths of the directories above each walked one, itself included, stop a loop.
    chains = {top: frozenset({os.path.realpath(top)})}
    for dirpath, dirnames, filenames in os.walk(top, onerror=fail, followlinks=True):
        chain = chains.get(dirpath) or frozenset({os.path.realpath(dirpath)})
        d_rel = _rel(root, Path(dirpath))
        keep = []
        for d in sorted(dirnames):
            if d in SKIP_DIRS:
                continue
            sub = f"{d_rel}/{d}/"
            if exclude_prefix and sub.startswith(exclude_prefix):
                continue
            full = os.path.join(dirpath, d)
            real = os.path.realpath(full)
            if real in chain:
                continue          # a link back to a directory being walked: read there
            chains[full] = chain | {real}
            keep.append(d)
        dirnames[:] = keep
        for name in sorted(filenames):
            p = Path(dirpath) / name
            if p.suffix.lower() in want:
                found.append(p)
    return found


def _glob(root: Path, base_rel: str, suffix: str) -> List[Path]:
    base = root / base_rel
    if not base.is_dir():
        return []
    # is_symlink too: a dangling link is a surface that cannot be read, never a skipped one
    return sorted(p for p in base.glob(f"*{suffix}") if p.is_file() or p.is_symlink())


def _read_bytes(root: Path, p: Path) -> bytes:
    try:
        return p.read_bytes()
    except OSError as e:
        raise SurfaceUnreadable(f"{_rel(root, p)}: cannot be read ({type(e).__name__})") \
            from None


def _read(root: Path, p: Path) -> str:
    """The surface as text, decoded as check_disclosure decodes it: a byte-order mark or the
    NUL pattern of UTF-16 picks the codec. Read as UTF-8 only, a UTF-16 page would be
    mojibake that passes every rule."""
    return CD.decode_bytes(_read_bytes(root, p))


def _ledger_text(root: Path, p: Path) -> str:
    """The file exactly as ledger_check reads it (UTF-8 with replacement, universal
    newlines), so its C2 and C4 can be reproduced on the very text they see."""
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise SurfaceUnreadable(f"{_rel(root, p)}: cannot be read ({type(e).__name__})") \
            from None


def ledger_reads(root: Path) -> Set[str]:
    """The prose files ledger_check's C2 and C4 read: its own walk_markdown, run once, so
    whether it follows a symbolic link, which directories it skips and how it matches a
    file name are ledger_check's answers on this interpreter, never an emulation of them."""
    return {p.relative_to(root).as_posix() for p in LC.walk_markdown(root)}


def _split(form: str, source: str) -> List[str]:
    """`form` split into lines exactly as its `source` is: on \\n only (the caller has
    already turned \\r\\n and \\r into \\n), dropping the empty tail when the source ends
    with a newline, as splitlines() does. A rendering keeps every newline of its source, so
    the two always have the same number of lines."""
    lines = form.split("\n")
    if source.endswith("\n"):
        lines.pop()
    return lines


def _renderings(text: str, suffix: str) -> List[str]:
    """Every reading of `text` besides the raw one: the markup readings, and, where string
    escapes render (check_disclosure.ESCAPED_SUFFIXES), the raw text and each markup reading
    with escapes decoded, plus the markup readings of the decoded text (so {"..."} holding
    an escape is unwrapped once the escape is gone). Each keeps the line count of `text`."""
    forms: List[str] = []
    if suffix in MARKUP_SUFFIXES:
        forms += CD.markup_forms(text, suffix)
    if suffix in CD.ESCAPED_SUFFIXES:
        decoded = CD.decode_escapes(text)
        forms += [CD.decode_escapes(f) for f in [text] + forms]
        if suffix in MARKUP_SUFFIXES and decoded != text:
            forms += CD.markup_forms(decoded, suffix)
    return forms


def _text_unit(root: Path, p: Path, rules: Tuple[str, ...], prose: bool = False,
               lc_reads: Optional[Set[str]] = None) -> Unit:
    """A text surface. `prose`: a Markdown file ledger_check may also read (README.md,
    MOC.md, docs/thesis, thesis, website): every rule runs, and the findings C2/C4
    themselves report are dropped, if `rel` is among `lc_reads` (the files ledger_check's
    own walk yields)."""
    rel = _rel(root, p)
    text = _read(root, p).replace("\r\n", "\n").replace("\r", "\n")
    raw = _split(text, text)
    variants = [raw]
    suffix = p.suffix.lower()
    for form in _renderings(text, suffix):
        lines = _split(form, text)
        if len(lines) != len(raw):              # cannot happen; never pass silently if it does
            raise SurfaceUnreadable(f"{rel}: its rendered text does not keep its lines")
        if lines not in variants:
            variants.append(lines)
    ledger_text = None
    if prose:
        rules = tuple(dict.fromkeys(rules + LEDGER_RULES))
        if lc_reads is not None and rel in lc_reads:
            lc_text = _ledger_text(root, p)
            if LC.IGNORE_FILE not in lc_text:
                ledger_text = lc_text
    return Unit(rel, raw, list(range(1, len(raw) + 1)), variants, rules, [""] * len(raw),
                ledger_text=ledger_text, text=text)


def svg_text(data: bytes, label: str) -> List[Tuple[int, str]]:
    """(line, text) for every line of rendered text in an SVG: text nodes plus the
    accessible-name attributes. Element boundaries become spaces so adjacent nodes on
    one line read as they render."""
    per_line: Dict[int, List[str]] = {}
    parser = expat.ParserCreate()

    def add(line: int, text: str) -> None:
        per_line.setdefault(line, []).append(text)

    def start(name, attrs):
        line = parser.CurrentLineNumber
        add(line, " ")
        for key in SVG_ATTRS:
            if attrs.get(key):
                add(line, " " + attrs[key] + " ")

    def end(name):
        add(parser.CurrentLineNumber, " ")

    def chars(data_):
        line = parser.CurrentLineNumber
        for k, piece in enumerate(data_.split("\n")):
            if piece:
                add(line + k, piece)

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = chars
    try:
        parser.Parse(data, True)
    except expat.ExpatError as e:
        raise SurfaceUnreadable(f"{label}: not well-formed XML ({e})") from None
    out = []
    for line in sorted(per_line):
        text = " ".join("".join(per_line[line]).split())
        if text:
            out.append((line, text))
    return out


def _svg_unit(root: Path, p: Path) -> Unit:
    """An SVG's rendered text, one entry per source line that holds any. Pragmas are read
    from the source lines (an XML comment is not text), by each entry's source line."""
    rel = _rel(root, p)
    data = _read_bytes(root, p)
    pairs = svg_text(data, rel)
    lines = [t for _, t in pairs]
    numbers = [n for n, _ in pairs]
    source = CD.decode_bytes(data).replace("\r\n", "\n").replace("\r", "\n").split("\n")

    def allowed(pragma: str) -> List[bool]:
        covered = pragma_lines(source, pragma)
        return [0 < n <= len(source) and covered[n - 1] for n in numbers]
    return Unit(rel, lines, numbers, [lines], ALL_RULES, [""] * len(pairs),
                allow_count=allowed(LC.ALLOW_COUNT), allow_claim=allowed(LC.ALLOW_CLAIM))


_JSON_SCALAR_RE = re.compile(r"[^\s,\]\}]+")


def _pointer_token(tok) -> str:
    return str(tok).replace("~", "~0").replace("/", "~1")


def plan_strings(text: str, label: str) -> List[Tuple[int, str, str]]:
    """(line, JSON pointer, value) for every string value in the plan, in document order.
    Keys are not values and are not returned. Values are located by reading the JSON's own
    tokens, so an escape written any way, or a value equal to some key, is placed on its
    true line. A key repeated inside one object raises SurfaceUnreadable: JSON keeps only
    the last value, so the others would publish unchecked."""
    try:
        json.loads(text)
    except ValueError as e:
        raise SurfaceUnreadable(f"{label}: not valid JSON ({e})") from None
    out: List[Tuple[int, str, str]] = []
    # a frame: [kind, current key or index, keys seen, expecting a key]
    stack: List[list] = []
    i, n, line = 0, len(text), 1

    def pointer() -> str:
        toks = [_pointer_token(fr[1]) for fr in stack if fr[1] is not None]
        return "/" + "/".join(toks) if toks else "/"

    def begin_value() -> None:
        if stack and stack[-1][0] == "arr":
            stack[-1][1] += 1

    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            i += 1
        elif ch in " \t\r":
            i += 1
        elif ch == ",":
            if stack and stack[-1][0] == "obj":
                stack[-1][3] = True
            i += 1
        elif ch == ":":
            if stack:
                stack[-1][3] = False
            i += 1
        elif ch in "{[":
            begin_value()
            stack.append(["obj", None, set(), True] if ch == "{" else ["arr", -1, None, False])
            i += 1
        elif ch in "}]":
            if stack:
                stack.pop()
            i += 1
        elif ch == '"':
            value, end = json.decoder.scanstring(text, i + 1)
            top = stack[-1] if stack else None
            if top is not None and top[0] == "obj" and top[3]:
                if value in top[2]:
                    raise SurfaceUnreadable(
                        f"{label}:{line}: a key repeats inside one object; JSON keeps only "
                        f"the last value, so the others would publish unchecked")
                top[2].add(value)
                top[1] = value
            else:
                begin_value()
                out.append((line, pointer(), value))
            i = end
        else:
            begin_value()
            m = _JSON_SCALAR_RE.match(text, i)
            i = m.end() if m else i + 1
    return out


_SLUG_SEP_RE = re.compile(r"[-_]")


def _manifest_readings(value: str) -> List[str]:
    """Every reading of one manifest string besides the value itself: "-" and "_" read as
    spaces (GitHub shows a wiki page name with its hyphens as spaces), and the Markdown
    readings of both (build_wiki.py writes section and page titles into Markdown), so a
    count or a term split by a hyphen, by emphasis or by an inline tag is seen as it
    renders."""
    spaced = _SLUG_SEP_RE.sub(" ", value)
    forms = [spaced]
    for form in (value, spaced):
        forms += CD.markup_forms(form, ".md")
    return forms


def check_json_strings(rules: Rules, root: Path, rel: str,
                       readings=None) -> List[CopyFinding]:
    """Every string value of the JSON file `rel` (absent: nothing to read), each as its own
    unit: no negation carries over from a sibling, and no pragma applies (raw is empty),
    since anything in such a string renders as copy. `readings(value)` gives the renderings
    to read besides the value itself."""
    p = root / rel
    if not (p.is_file() or p.is_symlink()):
        return []
    out: List[CopyFinding] = []
    for line, pointer, value in plan_strings(_read(root, p), rel):
        variants = [[value]]
        for form in (readings(value) if readings else []):
            if [form] not in variants:
                variants.append([form])
        unit = Unit(rel, [""], [line], variants, ALL_RULES, [f" (at {pointer})"])
        out.extend(check_unit(rules, unit))
    return out


def check_plan(rules: Rules, root: Path) -> List[CopyFinding]:
    return check_json_strings(rules, root, PLAN_REL)


def check_manifest(rules: Rules, root: Path) -> List[CopyFinding]:
    """docs/publish.json: every string value, as written and as the site and the wiki show
    it (see _manifest_readings)."""
    return check_json_strings(rules, root, MANIFEST_REL, _manifest_readings)


def surfaces(root: Path) -> Tuple[List[Path], List[Path], List[Path]]:
    """(copy files, svg files, prose files), each sorted and de-duplicated."""
    code = [p for p in _walk(root, "website/src", CODE_SUFFIXES, exclude_prefix=STAGED_REL)
            if not (p.suffix.lower() == ".json" and p.name.startswith("package"))]
    code += [root / "website" / name for name in SITE_CONFIGS
             if (root / "website" / name).is_file() or (root / "website" / name).is_symlink()]
    # docs/diagrams/*.mmd is not read: archived report figures (see the module docstring)
    svgs = _glob(root, "docs/assets", ".svg")
    svgs += _walk(root, "website/src", {".svg"}, exclude_prefix=STAGED_REL)
    svgs += _walk(root, "website/public", {".svg"})
    prose = [root / name for name in ("README.md", "MOC.md")
             if (root / name).is_file() or (root / name).is_symlink()]
    prose += _walk(root, "docs/thesis", {".md"})
    prose += _walk(root, "thesis", {".md"})
    prose += _walk(root, "website", {".md"}, exclude_prefix=STAGED_REL)

    def uniq(ps: List[Path]) -> List[Path]:
        return sorted(set(ps), key=lambda q: _rel(root, q))
    return uniq(code), uniq(svgs), uniq(prose)


def _thesis_section(title) -> bool:
    return isinstance(title, str) and title.strip().casefold() == THESIS_SECTION.casefold()


def manifest_sources(root: Path) -> Dict[str, bool]:
    """{src: in the section titled "Thesis"} for every page docs/publish.json publishes,
    read through core.load_manifest, so the pages are the ones stage.py and build_wiki.py
    publish. A manifest core refuses publishes nothing until it is fixed, but its page
    sources are still taken from its JSON as far as its shape allows (a source that is not
    a canonical repository path is left out, so nothing outside the repository is read):
    a page named in it is not left unread meanwhile. A manifest that is not JSON gives
    nothing here; check_manifest refuses it (exit 2)."""
    p = root / MANIFEST_REL
    if not (p.is_file() or p.is_symlink()):
        return {}
    try:
        sections = CORE.load_manifest(root)["sections"]
    except CORE.PublishError:
        try:
            data = json.loads(_read(root, p))
        except ValueError:
            return {}
        sections = data.get("sections") if isinstance(data, dict) else None
        if not isinstance(sections, list):
            return {}
    out: Dict[str, bool] = {}
    for sec in sections:
        if not isinstance(sec, dict) or not isinstance(sec.get("pages"), list):
            continue
        thesis = _thesis_section(sec.get("title"))
        for page in sec["pages"]:
            src = page.get("src") if isinstance(page, dict) else None
            try:
                rel = CORE.canonical_rel(src)
            except CORE.PublishError:
                continue
            out[rel] = out.get(rel, False) or thesis
    return out


def published_pages(root: Path, prose: List[Path]) -> List[Tuple[Path, bool]]:
    """(page, THESIS applies) for every prose surface: the hard-coded prose list (README.md,
    MOC.md, docs/thesis, thesis, website: all public thesis surfaces, so THESIS applies),
    then every manifest page source not already in it (THESIS only for a page in the
    section titled "Thesis"). A manifest source that does not exist is left out here:
    publishable_guard refuses a missing source wherever one is published. A dangling link
    is kept, and reading it is exit 2."""
    out = [(p, True) for p in prose]
    have = {_rel(root, p) for p in prose}
    for rel, thesis in sorted(manifest_sources(root).items()):
        if rel in have:
            continue
        p = root / rel
        if p.is_file() or p.is_symlink():
            out.append((p, thesis))
    return out


def run(root: Path) -> Tuple[List[CopyFinding], List[str], List[str]]:
    """(findings, scanned paths, notices). Raises SurfaceUnreadable and LedgerInvalid;
    SystemExit if the ledger is missing or not JSON (ledger_check.load_ledger's contract)."""
    ledger = LC.load_ledger(root)
    rules = Rules(ledger)
    # no notice can stand in for a rule any more (a ledger missing a term list is
    # LedgerInvalid); the list stays in the return value for callers
    notices: List[str] = []
    code, svgs, prose = surfaces(root)
    findings: List[CopyFinding] = []
    scanned: List[str] = []
    for p in code:
        findings += check_unit(rules, _text_unit(root, p, ALL_RULES))
        scanned.append(_rel(root, p))
    for p in svgs:
        findings += check_unit(rules, _svg_unit(root, p))
        scanned.append(_rel(root, p))
    pages = published_pages(root, prose)
    lc_reads = ledger_reads(root) if pages else set()
    for p, thesis in pages:
        findings += check_unit(rules, _text_unit(root, p,
                                                 PROSE_RULES if thesis else PAGE_RULES,
                                                 prose=True, lc_reads=lc_reads))
        scanned.append(_rel(root, p))
    for rel, check in ((PLAN_REL, check_plan), (MANIFEST_REL, check_manifest)):
        p = root / rel
        if p.is_file() or p.is_symlink():
            findings += check(rules, root)
            scanned.append(rel)
    findings = sorted(set(findings), key=lambda f: (f.path, f.line, f.rule, f.message))
    return findings, scanned, notices


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(REPO),
                    help="repository root (default: this checkout)")
    ap.add_argument("--quiet", action="store_true", help="findings only, no summary")
    ap.add_argument("--list", action="store_true", help="also list every surface scanned")
    args = ap.parse_args(argv)

    if LC is None or CD is None or CORE is None:
        print(f"check_copy: cannot run: a sibling check cannot be imported: {LOAD_ERROR}",
              file=sys.stderr)
        return 2
    if not MARKUP_SUFFIXES <= CD.MARKUP_SUFFIXES:
        print("check_copy: cannot run: check_disclosure.markup_forms does not read every "
              "suffix check_copy treats as markup", file=sys.stderr)
        return 2
    root = Path(args.root).resolve()
    if not (root / "tools" / "ledger.json").is_file():
        print(f"check_copy: tools/ledger.json not found under {root}", file=sys.stderr)
        return 2
    try:
        findings, scanned, notices = run(root)
    except (SurfaceUnreadable, LedgerInvalid) as e:
        print(f"check_copy: cannot run: {e}", file=sys.stderr)
        return 2
    except SystemExit as e:          # ledger_check.load_ledger reports a bad ledger this way
        print(f"check_copy: cannot run: {e}", file=sys.stderr)
        return 2

    for note in notices:
        print(f"check_copy: notice: {note}", file=sys.stderr)
    if args.list:
        for s in scanned:
            print(f"scanned  {s}", file=sys.stderr)
    for f in findings:
        print(f.render())
    if not args.quiet:
        state = f"{len(findings)} finding(s)" if findings else "clean"
        print(f"check_copy: {state}; {len(scanned)} surface(s) scanned", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
