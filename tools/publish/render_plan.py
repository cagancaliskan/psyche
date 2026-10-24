#!/usr/bin/env python3
"""render_plan.py — render the research plan into the documents that quote it.

tools/research_plan.json is the only source of the research line's dates (D-031 §2.5).
A date typed by hand into a document is a second source, and this project has already
shipped four different assertion counts across five documents because facts were copied
instead of generated. So the documents never hold plan facts of their own: they hold
MARKERS, and this tool fills them.

    <!-- generated:ID:start -->
    ...rendered from the plan, never edited by hand...
    <!-- generated:ID:end -->

A marker is exactly one of those two lines (lowercase id, single spaces), alone on its
line, indented at most three spaces. Generated lines take the start marker's indentation,
so a block inside a list item stays inside it.

FAIL CLOSED. Anything that LOOKS like a marker — an HTML comment whose body begins with
"generated", in any case or spacing, line endings included ('<!--' on one line and
'generated' on the next is one comment to Markdown, inside a block quote too, where the
next line's '>' belongs to the quote and not to the comment) — but is not an exact
marker stops the run (exit 2): a near miss would otherwise be ordinary text, and
whatever was typed by hand between two near misses would pass --check forever. The
same holds for a marker indented four or more columns, a marker inside a code fence that
is never closed, and a marker in any Markdown file this tool does not render. Markers
inside a fenced code block that its own closing line ends, and inside `code spans`, are
text, so a page may show the syntax; that includes an end marker below an open block,
which therefore never closes it (the block is "never closed", exit 2, instead of
swallowing the example). Which lines are fenced code is read the way CommonMark reads
it (core.scan_blocks): a fence opened
on a list-item line ("- ```") or inside a block quote is a fence, and a fence ends with
the list item or block quote that holds it, so its closing line can never be mistaken
for an opener that turns every later line into "code".

Files rendered: README.md, MOC.md, every .md under docs/research/ (recursively) and every
page listed in docs/publish.json. Every other Markdown file in the repository (git's
tracked and untracked-but-not-ignored files; a plain directory walk without git) is
scanned for strays. A rendered path that is a symbolic link, or that resolves outside the
repository, is refused: --write never writes through a link.

IDs:
  status-line        **Now:** the active phase and its dates · **Next gate:** and its date
  phases-table       id, phase, start, end (or the rule that sets it), gate, status
  plan-gantt         a Mermaid gantt: a section per phase, gates as milestones
  layers-table       the safe base, the main goal, the failure analysis
  gates-table        gate, title, date (or rule), status, question
  gate-flow          a Mermaid flowchart of the gates in plan order (A -> B -> C -> D),
                     then a sentence and a list: what follows if each gate is missed
  deadlines-table    deadline, due (or estimate), status
  commitments-table  hash commitments; a "none yet" row while there are none

--check is not satisfied by silence: it fails (exit 1) unless README.md and MOC.md exist
and every id above is placed in some rendered file, so deleting the markers and typing
dates by hand cannot keep the gate green. --allow-unplaced turns that into a notice, for
bootstrapping a repository that has no blocks yet.

DETERMINISM. Rendering reads the plan and nothing else: never the clock, never the
environment. The gantt draws an open-ended phase to a visual horizon DERIVED FROM THE
PLAN (its latest dated point plus OPEN_END_DAYS), never from today, so the same plan
renders the same bytes on any day and any machine. --status is the one place today's
date is read, and it writes nothing.

C3 SAFETY. A gantt milestone is written '0d', which is a brick id in the ledger. C3 only
adjudicates a line that also carries a capitalised status label, and this renderer never
emits one: its status words are the plan's lowercase vocabulary, core.validate_plan
refuses any plan string containing a label (whitespace collapsed, and an id read
together with its title), and check_rendered refuses any rendered line that holds one,
as written or as a reader sees it (escapes, Mermaid entity codes and HTML character
references decoded, invisible characters dropped), before anything is compared or
written. Letters of another script that only look Latin are the one known limit
(core.reader_view, asserted in test_core.py).

GANTT SAFETY. Every gantt task and section name starts with an entity code (gantt_text),
so no Mermaid lexer rule can read the start of a name as a keyword or a date.

FLOWCHART LABELS. GitHub measures a label before its font loads, so an HTML label
overflows its box and is clipped. The gate flow therefore opens with FLOW_INIT (SVG text
labels, which do not clip), quotes every label, keeps every label line to at most
FLOW_LABEL_WIDTH characters and every label to at most FLOW_LABEL_LINES lines (flow_label:
words wrapped, a longer label cut with an ellipsis, never reworded), and draws plain arrows
with no edge labels. Whatever the arrows mean, and every "if missed" note in full, is said
in Markdown under the diagram, so nothing depends on the picture.

WRITES. --write is all or nothing: every changed file is written to a temporary file
beside it first, and only then are they renamed into place.

Exit 0 = clean / written. Exit 1 = --check found stale blocks, unplaced ids or a missing
README.md / MOC.md, and nothing else. Exit 2 = the tool could not run (invalid plan or
manifest, a status label in the rendered text, malformed, unknown or stray markers, a
symlinked or unwritable target, an unreadable file, or any other error).

Stdlib only.

Usage:
    python3 tools/publish/render_plan.py --check     # CI: exit 1 if any block is stale
    python3 tools/publish/render_plan.py --write     # rewrite blocks in place (idempotent)
    python3 tools/publish/render_plan.py --status    # program state and days to the next gate
    python3 tools/publish/render_plan.py --root PATH --check
"""

from __future__ import annotations

import argparse
import os
import re
import stat
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402

TARGET_FILES = ("README.md", "MOC.md")
REQUIRED_FILES = ("README.md", "MOC.md")
TARGET_DIR = "docs/research"

START_RE = re.compile(r"^<!-- generated:([a-z0-9-]+):start -->$")
END_RE = re.compile(r"^<!-- generated:([a-z0-9-]+):end -->$")
# Anything that LOOKS like a marker. A backslash before '<' makes it literal text in
# Markdown (and is how md() escapes plan text), so that is not a comment.
MARKER_HINT = re.compile(r"(?<!\\)<!--\s*generated", re.I)
# The same hint read across lines (split_markers). A comment that opens inside a block
# quote goes on over lines that start with the quote's '>' ('>', '> >', '>\t', or '>   '
# for a list item in a quote). That '>' is the container's, not the comment's body, so
# after a line break it is skipped as whitespace is. A '>' read this way that was really
# the comment's text can only stop the run, never let text through. Every match of
# MARKER_HINT is also a match here, so this is the quick "anything at all?" test too.
SPLIT_HINT = re.compile(r"(?<!\\)<!--[^\S\n]*(?:\n[\s>]*)?generated", re.I)

OPEN_END_DAYS = 61      # how far past the plan's latest dated point an open end is drawn
# The first line inside every generated flowchart fence: SVG text labels, which GitHub
# cannot clip the way it clips HTML labels measured before their font has loaded.
FLOW_INIT = '%%{init: {"htmlLabels": false, "flowchart": {"htmlLabels": false}}}%%'
FLOW_LABEL_WIDTH = 22   # characters per label line, as the reader sees them
FLOW_LABEL_LINES = 3    # lines per label
ELLIPSIS = "\u2026"
DASH = "—"
DOT = "·"


class MarkerError(core.PublishError):
    """A document's markers cannot be rendered: unknown id, unbalanced, nested,
    malformed, over-indented, in an unclosed fence, stray, or behind a symlink."""


# ─────────────────────────────────────────────────────────────────────────────
# text helpers
# ─────────────────────────────────────────────────────────────────────────────

_MD_SPECIAL = re.compile(r"([\\`*_\[\]<>|])")


def md(s: str) -> str:
    """Plan text as inert Markdown: one line, emphasis/link/table syntax escaped."""
    return _MD_SPECIAL.sub(r"\\\1", " ".join(str(s).split()))


def _defang_mermaid(s: str) -> str:
    """Mermaid rewrites 'style ...:...#...;' and 'classDef ...' lines before it parses
    them, which would corrupt an entity code on the same line. Spelling the first letter
    as an entity keeps the word out of those patterns; it renders identically."""
    return s.replace("style", "#115;tyle").replace("classDef", "#99;lassDef")


# '<' and '>' too: a raw '<!--' in a task name would make the gantt line look like a
# marker to the next --check, and Mermaid decodes #lt; and #gt; like any entity code.
_GANTT_ESC = {"#": "#35;", ":": "#58;", ";": "#59;", "%": "#37;", "<": "#lt;", ">": "#gt;"}
_LABEL_ESC = {"#": "#35;", '"': "#quot;", "<": "#lt;", ">": "#gt;", "&": "#amp;",
              "`": "#96;", "%": "#37;"}


def _escape(s: str, table: Dict[str, str]) -> str:
    """One pass over the ORIGINAL characters. Chained str.replace would re-escape the ';'
    of a code it had just written ('#' -> '#35;' -> '#35#59;')."""
    return "".join(table.get(c, c) for c in " ".join(str(s).split()))


def gantt_text(s: str) -> str:
    """A gantt task or section name. ':' separates the name from its data, ';' ends a
    statement, '#' and '%' open comments: each becomes a Mermaid entity code.

    The FIRST character is always an entity code. Mermaid's gantt lexer tries a long list
    of rules before it reads a task name — keywords such as 'call', 'click', 'href',
    'gantt', 'title' and 'section', any of them in any case, and a leading
    YYYY-MM-DD date — and a name that starts like one of them is a parse error that takes
    the whole chart down. A list of those words would have to track every Mermaid
    release; a name that starts with '#NN;' matches none of them, now or later. The
    entity renders as the character it codes."""
    s = " ".join(str(s).split())
    if not s:
        return s
    return f"#{ord(s[0])};" + _defang_mermaid(_escape(s[1:], _GANTT_ESC))


def label_text(s: str) -> str:
    """Text inside a quoted Mermaid flowchart label."""
    return _defang_mermaid(_escape(s, _LABEL_ESC))


def wrap_words(s: str, width: int = FLOW_LABEL_WIDTH) -> List[str]:
    """`s` as lines of at most `width` characters, broken between words; a word longer
    than a line fills the rest of the current line and is broken inside it. Whitespace runs
    collapse to one space."""
    lines: List[str] = []
    cur = ""
    for word in str(s).split():
        if len(word) > width:
            if cur and len(cur) + 1 < width:
                room = width - len(cur) - 1
                cur, word = cur + " " + word[:room], word[room:]
            if cur:
                lines.append(cur)
            while len(word) > width:
                lines.append(word[:width])
                word = word[width:]
            cur = word
        elif not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= width:
            cur += " " + word
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def clip_lines(lines: List[str], n: int, width: int = FLOW_LABEL_WIDTH) -> List[str]:
    """At most `n` lines; when lines are dropped, the last one kept ends in an ellipsis and
    still fits `width`. Nothing is reworded, only cut."""
    if len(lines) <= n:
        return list(lines)
    kept = list(lines[:n])
    kept[-1] = kept[-1][:width - 1].rstrip() + ELLIPSIS
    return kept


def flow_label(head: str, tail: List[str]) -> str:
    """A quoted flowchart label's inner text: `head` wrapped into the lines `tail` leaves
    free, then each line of `tail`, every line escaped by label_text and joined by <br/>.
    Each tail line must already fit FLOW_LABEL_WIDTH; the tail is kept whole, so a long head
    is what gets cut."""
    room = max(1, FLOW_LABEL_LINES - len(tail))
    lines = clip_lines(wrap_words(head), room) + list(tail)
    return "<br/>".join(label_text(x) for x in lines[:FLOW_LABEL_LINES])


def _table(header: List[str], rows: List[List[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# plan readers
# ─────────────────────────────────────────────────────────────────────────────

def active_phase(plan: dict) -> Optional[dict]:
    return next((p for p in plan["phases"] if p["status"] == core.PHASE_ACTIVE), None)


def next_gate(plan: dict) -> Optional[dict]:
    """The first gate in plan order that is still upcoming."""
    return next((g for g in plan["gates"] if g["status"] == core.GATE_UPCOMING), None)


def _start(p: dict) -> str:
    return p["start"] if p["start"] is not None else p.get("start_rule", "")


def _end(p: dict) -> str:
    return p["end"] if p["end"] is not None else p.get("end_rule", "")


def _gate_when(g: dict) -> str:
    if g["date"] is None:
        return g.get("date_rule", "")
    if g["date"] != g["baseline_date"] and g["baseline_date"] is not None:
        return f"{g['date']} (baseline {g['baseline_date']})"
    return g["date"]


# ─────────────────────────────────────────────────────────────────────────────
# renderers — each a pure function of the plan
# ─────────────────────────────────────────────────────────────────────────────

def render_status_line(plan: dict) -> str:
    ph = active_phase(plan)
    now = (f"{md(ph['id'])} {md(ph['title'])} ({md(_start(ph))} to {md(_end(ph))})"
           if ph else "no phase is active")
    g = next_gate(plan)
    nxt = f"{md(g['id'])} {md(g['title'])}, {md(_gate_when(g))}" if g else "none upcoming"
    return f"**Now:** {now} {DOT} **Next gate:** {nxt}"


def render_phases_table(plan: dict) -> str:
    rows = [[md(p["id"]), md(p["title"]), md(_start(p)), md(_end(p)),
             md(p["gate"]) if p["gate"] else DASH, md(p["status"])]
            for p in plan["phases"]]
    return _table(["Phase", "Title", "Start", "End", "Gate", "Status"], rows)


def _latest_dated_point(plan: dict) -> date:
    found = [core.parse_iso_date(plan["as_of"])]
    for p in plan["phases"]:
        found += [core.parse_iso_date(p["start"]), core.parse_iso_date(p["end"])]
    for g in plan["gates"]:
        found += [core.parse_iso_date(g["date"]), core.parse_iso_date(g["baseline_date"])]
    for d in plan["deadlines"]:
        found.append(core.parse_iso_date(d["due"]))
    return max(d for d in found if d is not None)


def gantt_horizon(plan: dict) -> date:
    """Where an open end is drawn: the plan's latest dated point plus OPEN_END_DAYS.
    A function of the plan alone, so it moves only when the plan does."""
    return _latest_dated_point(plan) + timedelta(days=OPEN_END_DAYS)


def _drawn_spans(plan: dict) -> List[Tuple[date, date, str]]:
    """(start, end, label suffix) for each phase as drawn. An undated start follows the
    previous bar; an open end runs to the horizon, or OPEN_END_DAYS past its start when
    it starts at or after the horizon."""
    horizon = gantt_horizon(plan)
    prev_end = core.parse_iso_date(plan["as_of"])
    spans = []
    for p in plan["phases"]:
        s = core.parse_iso_date(p["start"])
        e = core.parse_iso_date(p["end"])
        start = s if s is not None else prev_end
        if e is not None:
            start = min(start, e)
            end = e
        else:
            end = horizon if start < horizon else start + timedelta(days=OPEN_END_DAYS)
        if s is None and e is None:
            note = " (dates not fixed)"
        elif s is None:
            note = " (start not fixed)"
        elif e is None:
            note = " (end not fixed)"
        else:
            note = ""
        spans.append((start, end, note))
        prev_end = end
    return spans


def render_plan_gantt(plan: dict) -> str:
    phases = plan["phases"]
    spans = _drawn_spans(plan)
    gate_index = {g["id"]: i for i, g in enumerate(plan["gates"])}
    placed = set()
    lines = ["```mermaid", "gantt", "    dateFormat YYYY-MM-DD", "    axisFormat %b %Y"]

    def milestone(g: dict, when: date, note: str = "") -> str:
        tags = "done, milestone" if g["status"] == core.GATE_DECIDED else "milestone"
        name = gantt_text(f"Gate {g['id']} {g['title']}{note}")
        return f"    {name} :{tags}, gt{gate_index[g['id']]}, {when.isoformat()}, 0d"

    bar_tag = {core.PHASE_ACTIVE: "active, ", core.PHASE_DONE: "done, "}
    for i, (p, (start, end, note)) in enumerate(zip(phases, spans)):
        lines.append(f"    section {gantt_text(p['id'])}")
        tag = bar_tag.get(p["status"], "")
        lines.append(f"    {gantt_text(p['title'] + note)} :{tag}ph{i}, "
                     f"{start.isoformat()}, {end.isoformat()}")
        gid = p["gate"]
        if gid and gid not in placed:
            g = plan["gates"][gate_index[gid]]
            d = core.parse_iso_date(g["date"])
            lines.append(milestone(g, d) if d else milestone(g, end, " (date not fixed)"))
            placed.add(gid)
    # Every gate is drawn: one no phase leads to sits at its date or, undated, at the
    # horizon with a note, never silently dropped.
    loose = [g for g in plan["gates"] if g["id"] not in placed]
    if loose:
        horizon = gantt_horizon(plan)
        lines.append(f"    section {gantt_text('Gates')}")
        for g in loose:
            d = core.parse_iso_date(g["date"])
            lines.append(milestone(g, d) if d else milestone(g, horizon, " (date not fixed)"))
    due = [(i, d) for i, d in enumerate(plan["deadlines"]) if d["due"] is not None]
    if due:
        lines.append(f"    section {gantt_text('Deadlines')}")
        for i, d in due:
            lines.append(f"    {gantt_text(d['title'])} :crit, milestone, dl{i}, {d['due']}, 0d")
    lines.append("```")
    return "\n".join(lines)


def render_layers_table(plan: dict) -> str:
    rows = [[md(x["id"]), md(x["title"]), md(x["summary"])] for x in plan["layers"]]
    return _table(["Layer", "Title", "Summary"], rows)


def render_gates_table(plan: dict) -> str:
    rows = [[md(g["id"]), md(g["title"]), md(_gate_when(g)), md(g["status"]), md(g["question"])]
            for g in plan["gates"]]
    return _table(["Gate", "Title", "Date", "Status", "Question"], rows)


def _flow_when(g: dict) -> List[str]:
    """The label lines under a gate's name: its date and status on one line when they fit,
    else on two. An undated gate says so; its rule is in the gates table."""
    when = g["date"] if g["date"] is not None else "date not fixed"
    one = f"{when} {DOT} {g['status']}"
    if len(one) <= FLOW_LABEL_WIDTH:
        return [one]
    return clip_lines(wrap_words(when), 1) + clip_lines(wrap_words(g["status"]), 1)


def render_gate_flow(plan: dict) -> str:
    """The gates as a left-to-right chain of short SVG-text labels (see FLOWCHART LABELS
    in the module docstring), then what the arrows mean and, for each gate, what follows
    if it is missed, in Markdown, so nothing depends on the picture."""
    gates = plan["gates"]
    lines = ["```mermaid", FLOW_INIT, "flowchart LR"]
    if not gates:
        lines += ['    none["no gates in the plan"]', "```"]
        return "\n".join(lines)
    for i, g in enumerate(gates):
        label = flow_label(f"Gate {g['id']}: {g['title']}", _flow_when(g))
        lines.append(f'    g{i}["{label}"]')
    if len(gates) > 1:
        lines.append("    " + " --> ".join(f"g{i}" for i in range(len(gates))))
    lines.append("    classDef gate fill:#3f6f9f,stroke:#24476b,color:#ffffff")
    lines.append("    class " + ",".join(f"g{i}" for i in range(len(gates))) + " gate")
    lines.append("```")
    lines += ["", "Each arrow leads to the next gate in plan order. If a gate is missed:", ""]
    lines += [f"- **Gate {md(g['id'])}** ({md(g['title'])}): {md(g['if_missed'])}"
              for g in gates]
    return "\n".join(lines)


def render_deadlines_table(plan: dict) -> str:
    rows = []
    for d in plan["deadlines"]:
        if d["due"] is not None:
            when = md(d["due"])
        else:
            when = f"not set; estimate: {md(d['estimate'])}" if d["estimate"] else "not set"
        rows.append([md(d["title"]), when, md(d["status"])])
    if not rows:
        rows = [["none yet", DASH, DASH]]
    return _table(["Deadline", "Due", "Status"], rows)


def render_commitments_table(plan: dict) -> str:
    rows = [[md(c["id"]), md(c["date"]), md(c["subject"]), f"`{c['sha256']}`", md(c["reveal"])]
            for c in plan["commitments"]]
    if not rows:
        rows = [["none yet", DASH, DASH, DASH, DASH]]
    return _table(["ID", "Date", "Subject", "SHA-256", "Reveal"], rows)


RENDERERS: Dict[str, Callable[[dict], str]] = {
    "status-line": render_status_line,
    "phases-table": render_phases_table,
    "plan-gantt": render_plan_gantt,
    "layers-table": render_layers_table,
    "gates-table": render_gates_table,
    "gate-flow": render_gate_flow,
    "deadlines-table": render_deadlines_table,
    "commitments-table": render_commitments_table,
}


def render_all(plan: dict) -> Dict[str, str]:
    return {bid: fn(plan) for bid, fn in RENDERERS.items()}


# ─────────────────────────────────────────────────────────────────────────────
# markers
# ─────────────────────────────────────────────────────────────────────────────

def _mask_line_spans(body: str) -> str:
    """The line with its one-line `code spans` blanked: a marker shown as code is text.
    core.mask_inline reads spans as rewrite_links does (a backslash-escaped backtick
    opens nothing). Comments stay: a marker is one."""
    return core.mask_inline(body, comments=False)


def _columns(ws: str) -> int:
    col = 0
    for ch in ws:
        col = col + 4 - col % 4 if ch == "\t" else col + 1
    return col


def classify(body: str, rel: str, lineno: int) -> Optional[Tuple[str, str, str]]:
    """('start' | 'end', id, indentation) for a marker line, None for ordinary text.
    MarkerError for a line that looks like a marker and is not exactly one, or one
    indented four or more columns (indented code, or a container this tool cannot
    render into safely)."""
    if not MARKER_HINT.search(_mask_line_spans(body)):
        return None
    stripped = body.strip(" \t")
    ms, me = START_RE.match(stripped), END_RE.match(stripped)
    if not (ms or me):
        raise MarkerError(
            f"{rel}:{lineno}: malformed generated marker {stripped[:90]!r}; a marker is "
            f"exactly '<!-- generated:ID:start -->' or '<!-- generated:ID:end -->' "
            f"(lowercase id, single spaces) alone on its line")
    lead = body[:len(body) - len(body.lstrip(" \t"))]
    if _columns(lead) > 3:
        raise MarkerError(
            f"{rel}:{lineno}: a generated marker indented {_columns(lead)} columns; indent "
            f"a marker at most 3 spaces (to show the syntax, use a fenced code block "
            f"opened at most 3 spaces in)")
    return ("start", ms.group(1), lead) if ms else ("end", me.group(1), lead)


def split_markers(bodies: List[str], fences: List[Optional[str]]) -> List[int]:
    """1-based numbers of the lines where a comment that looks like a marker OPENS while
    its body begins on a later line ('<!--' on one line, 'generated' on the next).

    Markdown reads '<!--' up to '-->' as one comment across lines (an HTML block, or an
    inline comment inside a paragraph), so such a pair hides exactly as a marker does,
    and hand-typed text between two of them would pass --check forever if the scan went
    line by line. So the scan reads the whole document: the lines joined by '\\n', the
    lines of a closed fence blanked (they are code), one-line code spans blanked on the
    other lines, and a line of an unclosed or disputed fence kept whole. A '<!--' that
    sits inside a code span running over several lines is not blanked, so it is refused
    too: a false alarm that can only stop the run, never let text through.

    Inside a block quote every continuation line starts with the quote's '>' ('> <!--',
    '>', '> generated...' is one comment to micromark and to GitHub alike), so the
    search is SPLIT_HINT, which skips '>' as well as whitespace after a line break;
    MARKER_HINT's whitespace alone would stop at the '>' and see nothing."""
    parts = []
    for body, f in zip(bodies, fences):
        if f is None:
            parts.append(_mask_line_spans(body))
        elif f == core.FENCE_CLOSED:
            parts.append("\0" * len(body))
        else:
            parts.append(body)
    joined = "\n".join(parts)
    return [joined.count("\n", 0, m.start()) + 1 for m in SPLIT_HINT.finditer(joined)
            if "\n" in m.group(0)]


def marker_lines(text: str) -> List[int]:
    """1-based numbers of the lines that are, or look like, generated markers: outside
    fenced code, and inside a fence that is never closed, plus every line where a
    marker-like comment opens and continues on a later line (split_markers). Which lines
    are fenced code is core.code_fences's answer: CommonMark's, list items and block
    quotes included."""
    if not SPLIT_HINT.search(text):       # MARKER_HINT would miss a split in a quote
        return []
    lines = core.split_lines(text)
    fences = core.code_fences(lines)
    hits: List[int] = split_markers(lines, fences)
    for n, (line, f) in enumerate(zip(lines, fences), 1):
        if f is None:
            if MARKER_HINT.search(_mask_line_spans(line)):
                hits.append(n)
        elif f != core.FENCE_CLOSED and MARKER_HINT.search(line):
            hits.append(n)
    return sorted(set(hits))


def _in_unclosed_fence(rel: str, lineno: int) -> MarkerError:
    return MarkerError(f"{rel}:{lineno}: a generated marker inside a code fence that is "
                       f"never closed (it runs to the end of the file, or of the list item "
                       f"or block quote that holds it), or on a line that Markdown parsers "
                       f"disagree is code")


def apply_blocks(text: str, rendered: Dict[str, str], rel: str) -> Tuple[str, List[str], List[str]]:
    """Return (new_text, ids_found, ids_whose_content_changed). Text outside the blocks,
    the markers themselves and every line ending are preserved byte for byte; generated
    lines take the line ending and the indentation of their start marker.

    A line inside fenced code is text, markers included, but only in a fence that its
    own closing line ends, and only when every parser this text reaches agrees it is
    code (core.code_fences): a fence that runs to the end of the file, or to the end of
    the list item or block quote holding it, has no edge a reader can see, and a line
    that one parser reads as code and another as text is not code for certain, so a
    marker in either stops the run.

    That holds while a block is open too: an END marker shown in a closed fence is an
    example, never the end of the block above it (taking it as one would delete the text
    between the two and leave the fence's closing line opening a new one), so the block
    is then never closed and the run stops. A marker-like comment split over lines
    (split_markers) stops the run wherever it is, a block quote's '>' prefixes
    included."""
    lines = core.split_lines(text, keepends=True)
    bodies = [core.line_body(x) for x in lines]
    fences = core.code_fences(bodies)
    split = split_markers(bodies, fences)
    if split:
        raise MarkerError(f"{rel}:{split[0]}: a comment that looks like a generated marker "
                          f"runs over several lines ('<!--' and 'generated' on different "
                          f"lines); a marker is exactly '<!-- generated:ID:start -->' or "
                          f"'<!-- generated:ID:end -->' alone on one line")
    out: List[str] = []
    found: List[str] = []
    changed: List[str] = []
    unclosed_hints: List[int] = []
    i = 0
    while i < len(lines):
        line, body = lines[i], bodies[i]
        if fences[i] is not None:
            if fences[i] != core.FENCE_CLOSED and MARKER_HINT.search(body):
                unclosed_hints.append(i + 1)
            out.append(line)
            i += 1
            continue
        kind = classify(body, rel, i + 1)
        if kind is None:
            out.append(line)
            i += 1
            continue
        k, bid, lead = kind
        if k == "end":
            raise MarkerError(f"{rel}:{i + 1}: end marker for {bid!r} has no start")
        if bid not in rendered:
            raise MarkerError(f"{rel}:{i + 1}: unknown generated block {bid!r} "
                              f"(known: {', '.join(sorted(rendered))})")
        j = i + 1
        while j < len(lines):
            if fences[j] is not None:          # code, as in the outer loop
                if fences[j] != core.FENCE_CLOSED and MARKER_HINT.search(bodies[j]):
                    raise _in_unclosed_fence(rel, j + 1)
                j += 1
                continue
            kj = classify(bodies[j], rel, j + 1)
            if kj is not None:
                if kj[0] == "end":
                    if kj[1] != bid:
                        raise MarkerError(f"{rel}:{j + 1}: end marker {kj[1]!r} closes "
                                          f"{bid!r} (opened at line {i + 1})")
                    break
                raise MarkerError(f"{rel}:{j + 1}: a block opens inside {bid!r} "
                                  f"(opened at line {i + 1})")
            j += 1
        else:
            raise MarkerError(f"{rel}:{i + 1}: block {bid!r} is never closed")
        nl = line[len(body):] or "\n"
        new_body = "".join((lead + part if part else part) + nl
                           for part in rendered[bid].split("\n"))
        old_body = "".join(lines[i + 1:j])
        if new_body != old_body:
            changed.append(bid)
        found.append(bid)
        out.append(line if line.endswith(("\n", "\r")) else line + nl)
        out.append(new_body)
        out.append(lines[j])
        i = j + 1
    if unclosed_hints:
        raise _in_unclosed_fence(rel, unclosed_hints[0])
    return "".join(out), found, changed


# ─────────────────────────────────────────────────────────────────────────────
# documents
# ─────────────────────────────────────────────────────────────────────────────

def _manifest_sources(root: Path) -> List[str]:
    """The manifest's Markdown pages. A manifest that exists but is invalid stops the run:
    it decides part of the rendered set, so it cannot be guessed at."""
    if not (root / core.MANIFEST_REL).exists():
        return []
    m = core.load_manifest(root)
    return [p["src"] for p in core.manifest_pages(m) if p["src"].endswith(".md")]


def target_files(root: Path) -> List[Path]:
    """README.md, MOC.md, every .md under docs/research/ (recursively, sorted) and every
    manifest page, in that order, each once, existing files only. A symlink — the file,
    docs/research itself or a directory under it — or a path that resolves outside the
    repository is a MarkerError: --write must never write through a link."""
    root_real = root.resolve()
    rels: List[str] = list(TARGET_FILES)
    d = root / TARGET_DIR
    if d.is_symlink():
        raise MarkerError(f"{TARGET_DIR}: is a symbolic link; render_plan never reads or "
                          f"writes through a link")
    if d.is_dir():
        found: List[str] = []
        for dirpath, dirnames, filenames in os.walk(d, followlinks=False):
            for dn in dirnames:
                if Path(dirpath, dn).is_symlink():
                    rel = Path(dirpath, dn).relative_to(root).as_posix()
                    raise MarkerError(f"{rel}: is a symbolic link; render_plan never reads "
                                      f"or writes through a link")
            found += [Path(dirpath, fn).relative_to(root).as_posix()
                      for fn in filenames if fn.endswith(".md")]
        rels += sorted(found)
    rels += _manifest_sources(root)
    out: List[Path] = []
    for rel in dict.fromkeys(rels):
        p = root / rel
        if p.is_symlink():
            raise MarkerError(f"{rel}: is a symbolic link; render_plan never reads or "
                              f"writes through a link")
        if not p.exists():
            continue
        try:
            p.resolve().relative_to(root_real)
        except ValueError:
            raise MarkerError(f"{rel}: resolves outside the repository")
        if p.is_file():
            out.append(p)
    return out


def _all_markdown(root: Path) -> List[str]:
    """Every Markdown file of the repository: git's tracked and untracked-but-not-ignored
    files, or, where git cannot answer, a walk of the tree. The directories ledger_check
    skips (its SKIP_DIRS and every hidden directory) are left out either way."""
    skip = core.ledger_check().SKIP_DIRS
    try:
        rels = [r for r in core.git_lines(root, ["ls-files", "-z", "-co", "--exclude-standard"])
                if r.lower().endswith(".md")]
    except core.PublishError:
        rels = []
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = sorted(n for n in dirnames
                                 if n not in skip and not n.startswith("."))
            rels += [Path(dirpath, fn).relative_to(root).as_posix()
                     for fn in filenames if fn.lower().endswith(".md")]
    return sorted(r for r in set(rels) if core._skip_dir_hit(r, skip) is None)


def _read(path: Path, rel: str) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise core.PublishError(f"{rel}: cannot read ({type(e).__name__}: {e})")


def stray_markers(root: Path, rendered_rels: Set[str]) -> List[str]:
    """'path:line' for every Markdown file outside the rendered set that carries, or looks
    like it carries, a marker. Such a block would never be rendered or checked."""
    found: List[str] = []
    for rel in _all_markdown(root):
        if rel in rendered_rels:
            continue
        p = root / rel
        if p.is_symlink() or not p.is_file():
            continue
        try:
            text = p.read_bytes().decode("utf-8", "replace")
        except OSError as e:
            raise core.PublishError(f"{rel}: cannot read ({type(e).__name__}: {e})")
        hits = marker_lines(text)
        if hits:
            found.append(f"{rel}:{hits[0]}")
    return found


_ENTITY = re.compile(r"#(\d{1,7}|[A-Za-z][A-Za-z0-9]{1,31});")


def _unescaped(text: str) -> str:
    """Backslash escapes and <br/> removed (any backslash, which can only show more)."""
    return re.sub(r"\\(.)", r"\1", text).replace("<br/>", " ")


def _decoded(text: str) -> List[str]:
    """What a reader sees, in each way a rendered line can be read, each through
    core.reader_view (HTML character references decoded, invisible characters dropped,
    compatibility forms folded):

      as Markdown  backslash escapes removed; '&#x50;' is a character reference;
      as Mermaid   '#NN;' and '#name;' are first turned into '&#NN;' and '&name;', as
                   Mermaid itself does before the browser decodes them.

    Two readings, not one: the Mermaid one would cut '&#x50;' into '&' and '#x50;' and
    hide the reference a Markdown table shows."""
    mermaid = _ENTITY.sub(lambda m: ("&#" if m.group(1).isdigit() else "&") + m.group(1) + ";",
                          text)
    return [core.reader_view(_unescaped(text)), core.reader_view(_unescaped(mermaid))]


def check_rendered(rendered: Dict[str, str]) -> None:
    """PlanError (exit 2) if a rendered block holds a capitalised status label, as
    written or as a reader sees it (_decoded). validate_plan checks the plan's strings;
    this checks what was actually produced from them, so no joining of an id and a
    title, no collapsed whitespace, no escape, no character reference and no invisible
    character can carry a label past the check. Letters of another script that only look
    Latin are the known limit (core.reader_view)."""
    texts = []
    for bid, block in rendered.items():
        for n, line in enumerate(block.split("\n"), 1):
            texts.append((f"generated block {bid!r}, line {n}", line))
            texts += [(f"generated block {bid!r}, line {n} (as rendered)", seen)
                      for seen in _decoded(line)]
    problems = core.label_problems(texts)
    if problems:
        raise core.PlanError(problems)


def render_checked(plan: dict) -> Dict[str, str]:
    rendered = render_all(plan)
    check_rendered(rendered)
    return rendered


def _write_all(root: Path, pending: List[Tuple[Path, str, str]]) -> None:
    """Write every pending (path, old, new) or none. Each file is first written in full to
    a temporary file beside it; only when every one of those succeeded are they moved
    into place, each by an atomic rename. A target that cannot be written stops the run
    before anything is written; a rename that fails puts back the files already moved."""
    for path, _, _ in pending:
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():   # checked in target_files; checked again at the write
            raise MarkerError(f"{rel}: became a symbolic link during the run")
        if not os.access(path, os.W_OK):
            raise core.PublishError(f"{rel}: is not writable; nothing was written")
    temps: List[Tuple[str, Path, str]] = []

    def stage(path: Path, data: str) -> str:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.",
                                   suffix=".render-tmp")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data.encode("utf-8"))
            os.chmod(tmp, stat.S_IMODE(path.stat().st_mode))
        except BaseException:
            os.unlink(tmp)
            raise
        return tmp

    def drop(names: List[str]) -> None:
        for name in names:
            try:
                os.unlink(name)
            except OSError:
                pass

    # Any failure, not only an OSError: text that cannot be encoded raises
    # UnicodeEncodeError while staging, and an interrupt can come at any point. Every
    # temporary file already staged is dropped either way, and anything that is not an
    # interrupt is reported as PublishError (exit 2).
    try:
        for path, old, new in pending:
            temps.append((stage(path, new), path, old))
    except BaseException as e:
        drop([t for t, _, _ in temps])
        if not isinstance(e, Exception):
            raise
        raise core.PublishError(f"cannot stage a write ({type(e).__name__}: {e}); "
                                f"nothing was written") from e
    moved: List[Tuple[Path, str]] = []
    try:
        for tmp, path, old in temps:
            os.replace(tmp, path)
            moved.append((path, old))
    except BaseException as e:
        drop([t for t, p, _ in temps if all(p != m for m, _ in moved)])
        for path, old in moved:
            back: List[str] = []
            try:
                back.append(stage(path, old))
                os.replace(back[0], path)
            except Exception:  # noqa: BLE001 — put back what can be put back
                drop(back)
        if not isinstance(e, Exception):
            raise
        raise core.PublishError(f"a write failed ({type(e).__name__}: {e}); the files "
                                f"already written were put back") from e


def render_documents(root: Path, plan: dict, *, write: bool
                     ) -> Tuple[List[Tuple[str, List[str]]], List[str], List[str]]:
    """Render every target file. Returns ([(rel, changed_ids)] for files that differ,
    sorted ids placed nowhere, required files that are missing). Writes only when
    `write`, only files that changed, and only after EVERY file has rendered: a malformed
    marker in the last file leaves the first one untouched, and the writes themselves are
    all or nothing (_write_all), never half a run applied."""
    rendered = render_checked(plan)
    targets = target_files(root)
    rels = [p.relative_to(root).as_posix() for p in targets]
    strays = stray_markers(root, set(rels))
    if strays:
        raise MarkerError("generated markers in file(s) render_plan does not render "
                          "(README.md, MOC.md, docs/research/**/*.md and the manifest's "
                          "pages): " + ", ".join(strays))
    stale: List[Tuple[str, List[str]]] = []
    pending: List[Tuple[Path, str, str]] = []
    seen: set = set()
    for path, rel in zip(targets, rels):
        text = _read(path, rel)
        new, found, changed = apply_blocks(text, rendered, rel)
        seen.update(found)
        if new != text:
            stale.append((rel, changed or ["(markers)"]))
            pending.append((path, text, new))
    if write and pending:
        _write_all(root, pending)
    unplaced = sorted(set(RENDERERS) - seen)
    missing = [f for f in REQUIRED_FILES if f not in rels]
    return stale, unplaced, missing


# ─────────────────────────────────────────────────────────────────────────────
# --status: the one place today is read
# ─────────────────────────────────────────────────────────────────────────────

def today_in_zone(tz: str) -> Tuple[date, str]:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(tz)).date(), tz
    except Exception:
        return date.today(), f"local time; no zone data for {tz}"


def _days(n: int) -> str:
    if n == 0:
        return "today"
    if n > 0:
        return f"in {n} day{'s' if n != 1 else ''}"
    return f"{-n} day{'s' if n != -1 else ''} ago"


def status_report(plan: dict, public_ledger: dict, today: date, zone_note: str) -> str:
    lines = ["Program state (tools/ledger.json)"]
    for who in core.PUBLIC_PROGRAM_LINES:
        p = public_ledger["program"][who]
        lines.append(f"  {who:<13} {p['state']} since {p['since']} ({p['decision']})")
    if public_ledger.get("aim"):
        lines.append(f"  {'aim':<13} {public_ledger['aim']}")
    lines += ["", f"Research plan (tools/research_plan.json, as of {plan['as_of']})",
              f"  today      {today.isoformat()} ({zone_note})"]
    ph = active_phase(plan)
    if ph:
        end = core.parse_iso_date(ph["end"])
        tail = f"; ends {_days((end - today).days)}" if end else ""
        lines.append(f"  phase      {ph['id']} {ph['title']}, {_start(ph)} to {_end(ph)}"
                     f" ({ph['status']}{tail})")
    else:
        lines.append("  phase      no phase is active")
    g = next_gate(plan)
    if g:
        d = core.parse_iso_date(g["date"])
        when = (f"{g['date']}, {_days((d - today).days)}" if d
                else f"date not fixed ({g.get('date_rule', '')})")
        if d and d < today:
            when += f", still {g['status']}"
        lines.append(f"  next gate  {g['id']} {g['title']}: {when}")
    else:
        lines.append("  next gate  none upcoming")
    for dl in plan["deadlines"]:
        d = core.parse_iso_date(dl["due"])
        when = (f"due {dl['due']}, {_days((d - today).days)}" if d
                else f"due date not set (estimate: {dl['estimate']})")
        lines.append(f"  deadline   {dl['title']}: {when} [{dl['status']}]")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="rewrite stale blocks in place")
    mode.add_argument("--check", action="store_true",
                      help="exit 1 if any block is stale or unplaced, or README.md/MOC.md "
                           "is missing")
    mode.add_argument("--status", action="store_true",
                      help="print program state and days to the next gate (reads today)")
    ap.add_argument("--allow-unplaced", action="store_true",
                    help="with --check: report unplaced ids and missing README.md/MOC.md "
                         "as notices instead of failing (bootstrapping only)")
    ap.add_argument("--root", default=str(core.REPO), help="repository root")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    # Exit 1 means "stale", so nothing else may end the run with 1: any failure that is
    # not a finding — an invalid plan, an unreadable or unwritable file, a bug — is 2.
    try:
        plan = core.load_plan(root)   # validated: load_plan refuses an invalid plan
        if args.status:
            pub = core.ledger_public(root)
            today, note = today_in_zone(plan["timezone"])
            print(status_report(plan, pub, today, note))
            return 0
        stale, unplaced, missing = render_documents(root, plan, write=args.write)
    except core.PublishError as e:
        print(f"render_plan: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 — "could not run" must never look like "stale"
        print(f"render_plan: could not run ({type(e).__name__}: {e})", file=sys.stderr)
        return 2

    for rel, ids in stale:
        verb = "wrote" if args.write else "stale"
        print(f"{verb}  {rel}  ({', '.join(ids)})")
    strict = args.check and not args.allow_unplaced
    label = "error" if strict else "notice"
    if missing:
        print(f"{label}: missing required file(s): {', '.join(missing)}")
    if unplaced:
        print(f"{label}: no rendered file carries the block(s): {', '.join(unplaced)}")
    if args.check and stale:
        print(f"\nrender_plan: {len(stale)} file(s) differ from a fresh render of "
              f"{core.PLAN_REL.as_posix()}; run: python3 tools/publish/render_plan.py --write")
        return 1
    if strict and (missing or unplaced):
        print("\nrender_plan: --check needs README.md, MOC.md and every generated block "
              "placed in a rendered file; a check with nothing to check is not a pass "
              "(--allow-unplaced while bootstrapping)")
        return 1
    if not stale:
        print("render_plan: every generated block matches the plan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
