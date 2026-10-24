#!/usr/bin/env python3
"""PreToolUse hook - keep private and non-English text out of the public, English-only paths.

D-031 split the thesis into a public summary (this repository) and private detail (a companion
repository that is never named here). The split is only as good as the moment of writing: once
a private identifier or a Turkish sentence is committed to a public path, history keeps it even
after the file is fixed. So this hook looks at the new text of a write made through one of the
tools under "Which tools" below, before it lands. Writes made any other way are not seen.

Two sets of paths, two rule sets:

    PUBLIC (the D-031 public summary):
        README.md  MOC.md  docs/PSYCHE.md  tools/thesis_plan.json
        docs/thesis/**  thesis/**  website/src/**
      refused: a letter of the Turkish alphabet outside ASCII (D-031 item 7); a private
      identifier (E-NN, ADR-NNN, or a Q-ADM-/Q-M-/Q-E- question id, in any letter case); the
      private marker (see PRIVATE_MARKER below).

    ENGLISH-ONLY, the rest of the push-time rule in tools/publish/leak_check.py
    (ENGLISH_ONLY_FILES / ENGLISH_ONLY_DIRS, mirrored below; test_hooks.py fails if the two
    drift): CLAUDE.md, website/**, tools/publish/**, .github/**
      refused: a Turkish letter only. Identifiers and the marker are judged there by the
      push-time leak check, not here.

It also refuses every write under thesis/src/ and thesis/tests/, whatever the content, and a
move out of them, including the move of a directory that holds one (thesis/ itself, say): the
thesis package arrives here only through a release export that Cagan runs (D-031 item 6, 9).
A nested worktree's root, .claude/worktrees/ and .claude/ count as holding one, since each
holds a checkout's thesis/src/. The repository root is not judged as a source: moving the
whole checkout moves the package with it.

Which tools
    Claude Code's Write, Edit, MultiEdit and NotebookEdit, and the file-writing tools of MCP
    servers whose tool names end in write_file, edit_file, edit_block, create_file,
    move_file, create_directory or write_pdf (Desktop Commander and the reference filesystem
    server name theirs this way). The matcher in .claude/settings.json names exactly these.

What it reads
    Write, write_file, create_file: `content`, the whole file. NotebookEdit: `new_source`.
    write_pdf: `content`, or the `markdown` of each of its operations, as the text of
    `outputPath` (else `path`). create_directory: the path alone.
    Edit, MultiEdit, edit_block, edit_file, and write_file in append mode: the current file is
    read with CRLF line endings read as LF (the Edit tool matches "\\n" against CRLF text the
    same way), the change is applied in memory as the tool applies it, and the lines that
    differ in the result are judged. How each tool applies an edit:
      - Claude Code's Edit and MultiEdit replace the exact text. When it is not in the file,
        straight quotes in old_string match the curly quotes U+2018, U+2019, U+201C and
        U+201D in the file, and that slice of the file is replaced. An empty new_string whose
        old_string does not end in a newline also removes the newline after it, when the
        file has old_string followed by one (with replace_all, only those occurrences).
        Confirmed on Claude Code 2.1.246 by real edits on scratch files. The straight quotes
        it then writes back as curly ones are not converted here: no rule involves a quote.
      - edit_file (the reference filesystem server) replaces the first occurrence (an empty
        oldText inserts at the start). When there is none, it matches line by line with the
        whitespace around each line ignored, and writes the new lines with the matched
        line's indentation. Older releases passed the new text to String.prototype.replace
        as a string, which reads $$, $&, $` and $' in it as patterns ($' is the text after
        the match), so when the new text holds a "$" both readings are judged.
      - edit_block (Desktop Commander) replaces the exact text, expected_replacements times,
        literally (its source, 0.2.46, splices the text in; no fuzzy match is applied).
      - Any other tool name, or none, is judged under every one of these readings.
    So an edit cannot complete an identifier or the marker out of text already in the file.
    Which lines differ is found in time linear in the file (there is no line diff, whose cost
    grows with the square of how often a line repeats): the leading and trailing lines the
    two versions share are set aside, and of the rest a line of the result is judged unless
    an identical line is among the lines it replaces (counted with multiplicity). Lines the
    edit does not touch, moves or reorders are not judged, so an older line is not a reason
    to refuse a new one.
      Fallback: if the file cannot be read, holds a NUL byte, is larger than
      MAX_SIMULATED_BYTES (32 MB), or a replacement does not apply, every new string is
      judged on its own. For a file over the
      size cap an edit can then complete an identifier out of existing text (pinned below).
      A "$" pattern that would expand the file past MAX_SIMULATED_BYTES is refused.
    move_file: the destination is judged as the target, with the text of the moved file as its
    content. A moved directory is walked: every name inside it is judged, and the text of
    every file in it. A file holding a NUL byte (an image, say) is judged by its name only.
    What cannot be judged in full is refused rather than judged in part: a moved file larger
    than MAX_SIMULATED_BYTES, a tree of more than MAX_MOVED_NAMES entries, more than
    MAX_MOVED_FILES files of text or more than MAX_SIMULATED_BYTES of text in all, and a file
    that cannot be read. A move whose destination cannot hold an English-only path is not
    walked and never refused for its size.
    The repository-relative path is judged too, with the same rules: a file name carries text.

Lines are split at LF only, after CRLF is read as LF, which is where Markdown and HTML end a
line. str.splitlines() is not used: it also splits at VT, FF, \\x1c-\\x1e, NEL and
U+2028/U+2029, which end no line there, so an identifier split by one would be judged as two
harmless halves. A lone CR is kept in its line and never dropped, so no identifier or marker
matches across it, as none renders across it (a tag may still span it, as Markdown allows).

Before matching, text is NFKC-normalised, and then:
    - the Unicode hyphens and dashes in _HYPHENS read as "-";
    - every format character (Unicode category Cf: zero-width spaces and joiners, the soft
      hyphen, invisible operators and separators, direction marks, tag characters), every
      control character (category Cc) except tab, LF and CR, the line and paragraph
      separators U+2028 and U+2029, the combining grapheme joiner, the variation selectors
      and the Hangul and Khmer fillers are dropped, and the text is normalised again, so a
      letter split by one recombines;
    - look-alike letters from the Greek, Cyrillic, Cherokee and Lisu scripts and the Latin
      small capitals (_LOOKALIKES) read as the ASCII letters of the identifiers and the
      marker, and three colon look-alikes as ":";
    - a backslash before ASCII punctuation (a Markdown escape) is dropped.
On the PUBLIC paths HTML entities are also decoded (Markdown and HTML render them), and the
text is read once more with inline markup removed: HTML tags, the characters * _ ~ ` of
emphasis, strike-through and code spans, and the brackets and target of a link or an image.
A tag is read two ways, and what either reading finds is removed: as HTML, CommonMark inline
HTML, JSX and Astro read it, where a quoted attribute value or a {...} attribute expression
may hold "<" and ">" (<span title="a>b"> and <b onClick={() => go()}> render as nothing), and
plainly, as < ... > with no < or > inside, so an unclosed quote or brace cannot hide a tag.
On tools/thesis_plan.json and website/src/** the \\uXXXX, \\u{...} and \\xXX escapes of JSON
and JavaScript are decoded as well. Every reading is judged; the raw text always is.
Those readings are line-local. An HTML comment or tag can also span a line break (CommonMark
inline HTML, .astro and .html files) and show what it splits as one line, so on the PUBLIC
paths the written text is read once more as a whole: every HTML comment (<!-- ... -->) and
every tag (in either reading above; a quoted value may itself span the break) that spans a
line break is removed, and each line it joins is judged with all the readings above. For an
edit, a joined line of the result is judged unless the same joined line is in the file before
the edit (counted with multiplicity), as for ordinary lines. The tag reading is the strict
one: any < ... > pair counts, so text between a "<" and a ">" lines apart is read as removed.
Both readings run in time linear in the text (see _spans_across). One hook call joins
at most MAX_JOINED_LINES lines (the file before an edit counts too); a write that would join
more is refused as too large to judge, since a hook past its timeout is let through.

Known limitations (each of the first eight is pinned by an asserted-negative case in
tools/publish/test_hooks.py):
    - An identifier glued to a preceding letter or digit (xE-07) is not matched. That is what
      keeps 1E-12 and TYPE-12 out of the net. One after an underscore or a hyphen is matched.
    - The Turkish letters judged are the twelve of leak_check and check_copy. The circumflex
      vowels used in some Turkish words are not, because they are also ordinary French and
      English-loan letters; a Turkish sentence almost always carries one of the twelve.
    - Escapes are decoded only where they render: entities on the PUBLIC paths, \\u escapes
      on the plan and website/src/**. CSS escapes, and \\u escapes elsewhere (Python source in
      tools/publish/ legitimately holds them as detection patterns), are not decoded.
    - Look-alikes are folded only from the scripts named above. One from another script (a
      Canadian syllabics letter that looks like A, say) is not.
    - Text assembled by code is not judged as it renders: E{"-"}07 in JSX, or a string built
      by concatenation, displays an identifier that no line of the source contains.
    - An attribute expression is read as one group only to two braces deep, and a brace
      inside a string in it is counted as a brace. One nested deeper that holds ">"
      (x={() => ({a: {b: c > d}})}), or one whose string holds a brace (x={"}" + (a > b)}),
      is read as ending at that ">", so an identifier the tag splits passes.
    - An Edit to a file over MAX_SIMULATED_BYTES is judged by its new strings alone (above).
    - A moved file that holds a NUL byte is judged by its name only, so a text file written
      in UTF-16 (which holds NUL bytes) moves in with its text unread.
    - Writes made through the shell are not seen, including `render_plan.py --write`, which
      fills the public documents from tools/thesis_plan.json; the plan itself is guarded here.
    - Writes made through any tool the matcher does not name are not seen: an MCP file tool
      named otherwise, or a tool that writes elsewhere and syncs here.
    - Disclosure by meaning (a threshold, a hypothesis, a mechanism) is not judged; that is
      /psyche-claim-check Step 4.

Which file is the target: the path as the tool resolves it. It is made absolute against the
session cwd, a leading "~" is read as the home directory, ".." is removed lexically, and then
symlinks are resolved: realpath(normpath(path)), which is the file Claude Code writes. The
spelling that resolves symlinks first, realpath(path), and the literal "~" are judged as well,
and the strictest judgment wins, so <repo>/link/../README.md is README.md wherever the link
points.

Which directory is the repository: a directory that holds tools/ledger.json. Every such
ancestor of the target is a root, and the strictest judgment among them wins, so a stray
tools/ledger.json planted inside docs/thesis/ cannot narrow what is judged. CLAUDE_PROJECT_DIR
and the session cwd count only if they hold tools/ledger.json themselves. An unmarked
directory is never treated as this repository: a session that changes into a sibling
repository writes there unjudged, which is the point. A path inside a nested worktree,
.claude/worktrees/<name>/..., is also judged as the same path of that checkout, whether or not
the checkout holds its own ledger.

Wired in .claude/settings.json (see "Which tools"). It therefore binds only sessions whose
project directory is this repository root; a session launched in a parent folder loads no
settings from here and runs none of this repository's hooks. Exit 2 blocks the tool call and
shows stderr to Claude. Any failure of the hook itself exits 0: a broken guard must not make
the repository unusable, the same rule as the other hooks. The command in settings.json also
exits 0 when this file is missing, for the same reason.

stdin is read as bytes and decoded as UTF-8, which is what Claude Code sends, whatever
PYTHONIOENCODING or the locale say. Decoded through a Latin-1 or ASCII locale, every Turkish
letter would turn into something this check does not recognise and the guard would allow it.

Paths are compared after Unicode NFC normalisation and case folding. The NFC step is not
cosmetic: this checkout lives under a directory whose name the filesystem stores decomposed
(NFD), while a path typed into a tool call is usually composed (NFC). Compared raw, the two
spellings of the same directory never match and a guard silently allows everything.
"""

from __future__ import annotations

import html
import itertools
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from typing import Callable, Iterable, Iterator, List, Optional, Tuple

# -- paths (compared case-folded, relative to the repository root) ----------------------------
PUBLIC_EXACT = (
    "readme.md",
    "moc.md",
    "docs/psyche.md",
    "tools/thesis_plan.json",
)
PUBLIC_PREFIXES = (
    "docs/thesis/",
    "thesis/",
    "website/src/",
)
EXPORT_ONLY_PREFIXES = (
    "thesis/src/",
    "thesis/tests/",
)
# Mirror of tools/publish/leak_check.py ENGLISH_ONLY_FILES / ENGLISH_ONLY_DIRS, case-folded.
ENGLISH_ONLY_EXACT = (
    "readme.md",
    "moc.md",
    "claude.md",
    "docs/psyche.md",
    "tools/thesis_plan.json",
)
ENGLISH_ONLY_PREFIXES = (
    "docs/thesis/",
    "thesis/",
    "website/",
    "tools/publish/",
    ".github/",
)
# Where \u escapes are decoded before judging (they render there).
UNESCAPE_EXACT = ("tools/thesis_plan.json",)
UNESCAPE_PREFIXES = ("website/src/",)

WORKTREES = ".claude/worktrees/"
MARKER_FILE = os.path.join("tools", "ledger.json")

# -- what may not appear ----------------------------------------------------------------------
# Written as escapes so this file stays pure ASCII:
#   c-cedilla, g-breve, dotless i, dotted capital I, o-diaeresis, s-cedilla, u-diaeresis.
TURKISH_LETTERS = (
    "\u00e7\u00c7"   # c cedilla
    "\u011f\u011e"   # g breve
    "\u0131\u0130"   # dotless i, dotted capital I
    "\u00f6\u00d6"   # o diaeresis
    "\u015f\u015e"   # s cedilla
    "\u00fc\u00dc"   # u diaeresis
)
# Lower-casing a dotted capital I yields "i" + COMBINING DOT ABOVE, which NFC leaves decomposed.
TURKISH_SEQUENCES = ("i\u0307",)
_TURKISH_RE = re.compile("[" + TURKISH_LETTERS + "]")

# Not glued to a preceding letter or digit (keeps 1E-12 and TYPE-12 out); any letter case.
PRIVATE_ID_RE = re.compile(r"(?<![A-Za-z0-9])(?:E-\d{2}|ADR-\d{3}|Q-(?:ADM|M|E)-\d+)",
                           re.IGNORECASE)

# Assembled from parts so this file does not itself carry the marker it looks for.
PRIVATE_MARKER = "scm" + ":" + "private"

# -- normalisation ----------------------------------------------------------------------------
# Read as "-" before matching.
_HYPHENS = (0x02D7, 0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2043, 0x2212, 0x2E3A,
            0x2E3B, 0xFE58, 0xFE63, 0xFF0D)
# Dropped before matching, besides every character of Unicode category Cf or Cc (the C0
# controls other than tab, LF and CR, DEL, the C1 controls): the line and paragraph
# separators, the combining grapheme joiner, the Hangul and Khmer fillers, and the variation
# selectors.
_INVISIBLE = ((0x034F, 0x115F, 0x1160, 0x17B4, 0x17B5, 0x2028, 0x2029, 0x3164, 0xFFA0)
              + tuple(range(0xFE00, 0xFE10)) + tuple(range(0xE0100, 0xE01F0)))
_ASCII_CONTROLS_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Look-alikes of the letters of the identifiers (E A D R Q M) and of the marker
# (s c m p r i v a t e), read as those ASCII letters; and three colon look-alikes.
# Greek, Cyrillic, Cherokee, Lisu, Latin small capitals.
_LOOKALIKES = {
    "A": "\u0391\u0410\u13aa\ua4ee",
    "a": "\u0430\u1d00",
    "C": "\u03f9\u0421\ua4da",
    "c": "\u03f2\u0441",
    "D": "\u13a0\ua4d3",
    "d": "\u0501\u1d05",
    "E": "\u0395\u0415\u13ac\ua4f0",
    "e": "\u0435\u1d07",
    "I": "\u0399\u0406\ua4f2",
    "i": "\u03b9\u0456",
    "M": "\u039c\u041c\u13b7\ua4df",
    "m": "\u043c\u1d0d",
    "P": "\u03a1\u0420\u13e2\ua4d1",
    "p": "\u03c1\u0440",
    "Q": "\u051a",
    "q": "\u051b",
    "R": "\u13a1\u13d2\ua4e3",
    "r": "\u0433\u0280",
    "S": "\u0405\u13da\ua4e2",
    "s": "\u0455",
    "T": "\u03a4\u0422\u13a2\ua4d4",
    "t": "\u03c4",
    "V": "\u13d9\ua4e6",
    "v": "\u03bd\u0475",
    ":": "\u02d0\u2236\ua789",
}
_TRANSLATE = {**{cp: "-" for cp in _HYPHENS}, **{cp: None for cp in _INVISIBLE},
              **{ord(c): k for k, cs in _LOOKALIKES.items() for c in cs}}
_MD_ESCAPE_RE = re.compile(r"\\([!-/:-@\[-`{-~])")

# Inline markup, removed for one more reading of the PUBLIC paths. A tag is read two ways and
# either counts (see the module docstring): as HTML, CommonMark, JSX and Astro read it, where
# a quoted attribute value or a {...} attribute expression (nested up to two deep) may hold
# "<" and ">", and plainly, as < ... > with neither inside, so an unclosed quote or brace
# cannot hide a tag. The first form is an unrolled loop, plain* (group plain*)*: each
# repetition starts with a quote or a brace, which `plain` excludes, so no text can be matched
# two ways and a failed match costs time linear in what it read.
def _tag_pattern(eol: str) -> str:
    plain = rf"[^<>\"'{{}}{eol}]*"
    brace = rf"\{{[^{{}}{eol}]*(?:\{{[^{{}}{eol}]*\}}[^{{}}{eol}]*)*\}}"
    group = rf"\"[^\"{eol}]*\"|'[^'{eol}]*'|{brace}"
    return rf"<{plain}(?:(?:{group}){plain})*>"


_TAG_RE = re.compile(_tag_pattern(r"\n") + r"|<[^<>\n]*>")
# The same two readings with line breaks allowed, for a tag that spans one (_spans_across).
_TAG_GROUPED_ACROSS_RE = re.compile(_tag_pattern(""))
_TAG_PLAIN_ACROSS_RE = re.compile(r"<[^<>\n]*\n[^<>]*>")
_LINK_RE = re.compile(r"!?\[([^\[\]\n]*)\](?:\([^()\n]*\)|\[[^\[\]\n]*\])")
_MARKUP_CHARS_RE = re.compile(r"[*_~`]")

_U_ESCAPE_RE = re.compile(r"\\u\{([0-9A-Fa-f]{1,6})\}|\\u([0-9A-Fa-f]{4})|\\x([0-9A-Fa-f]{2})")

MAX_REPORTED = 10
MAX_SIMULATED_BYTES = 32_000_000
CHUNK_LINES = 1_000
MAX_MOVED_FILES = 2_000
MAX_MOVED_NAMES = 20_000
MAX_JOINED_LINES = 200_000
_JOINED_BUDGET = [MAX_JOINED_LINES]   # for one hook call; a hook runs once per process


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _canon(path: str) -> str:
    return _nfc(os.path.realpath(path))


def _is_marked(d: str) -> bool:
    return os.path.isfile(os.path.join(d, MARKER_FILE))


def _starts(key: str, prefixes: Iterable[str]) -> bool:
    return any(key.startswith(p) for p in prefixes)


# -- where the target sits --------------------------------------------------------------------

def resolve_target(target: str, cwd: str) -> List[str]:
    """Every absolute spelling of the target to judge; the file the tool writes comes first.

    See "Which file is the target" in the module docstring."""
    project = os.environ.get("CLAUDE_PROJECT_DIR") or ""
    base = cwd or project or os.getcwd()
    spellings = [os.path.expanduser(target)] if target.startswith("~") else []
    spellings.append(target)
    out: List[str] = []
    for t in spellings:
        p = t if os.path.isabs(t) else os.path.join(base, t)
        for c in (os.path.realpath(os.path.normpath(p)), os.path.realpath(p)):
            if c not in out:
                out.append(c)
    return out


def _spellings(rel: str) -> List[str]:
    """`rel`, and for a path inside .claude/worktrees/<name>/, the same path of that checkout."""
    out: List[str] = []
    while True:
        out.append(rel)
        if not rel.casefold().startswith(WORKTREES):
            return out
        parts = rel[len(WORKTREES):].split("/", 1)
        if len(parts) < 2 or not parts[1]:
            return out
        rel = parts[1]


def repo_relatives(raw: str, cwd: str) -> List[str]:
    """Every repository-relative spelling of one resolved path, NFC-normalised.

    One per marked root that contains it (see the module docstring), plus, for a path inside
    .claude/worktrees/<name>/, the same path relative to that nested checkout."""
    t = _nfc(raw)
    roots: List[str] = []
    d = os.path.dirname(raw)
    while True:
        if _is_marked(d):
            roots.append(d)
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    project = os.environ.get("CLAUDE_PROJECT_DIR") or ""
    roots += [r for r in (project, cwd) if r and _is_marked(r)]

    rels: List[str] = []
    for r in roots:
        rn = _canon(r).rstrip("/")
        if not t.startswith(rn + "/"):
            continue
        rels += [s for s in _spellings(t[len(rn) + 1:]) if s not in rels]
    return rels


def all_relatives(candidates: List[str], cwd: str) -> List[str]:
    rels: List[str] = []
    for c in candidates:
        rels += [r for r in repo_relatives(c, cwd) if r not in rels]
    return rels


def is_public(rel: str) -> bool:
    key = rel.casefold()
    return key in PUBLIC_EXACT or _starts(key, PUBLIC_PREFIXES)


def is_english_only(rel: str) -> bool:
    key = rel.casefold()
    return key in ENGLISH_ONLY_EXACT or _starts(key, ENGLISH_ONLY_PREFIXES)


def is_export_only(rel: str) -> bool:
    # "thesis/src" itself counts: a directory created or moved there is a write under it
    return _starts(rel.casefold() + "/", EXPORT_ONLY_PREFIXES)


def _dir_key(rel: str) -> str:
    return rel.casefold().rstrip("/") + "/"


def holds_export_only(rel: str) -> bool:
    """Whether the directory `rel` holds thesis/src/ or thesis/tests/ of a checkout: thesis/,
    and a nested worktree's root, .claude/worktrees/ and .claude/ (see the module docstring)."""
    key = _dir_key(rel)
    if any(p.startswith(key) for p in EXPORT_ONLY_PREFIXES) or WORKTREES.startswith(key):
        return True
    return key.startswith(WORKTREES) and key[len(WORKTREES):].count("/") == 1


def may_hold_guarded(rel: str) -> bool:
    """Whether a path at or below `rel` can be English-only (every public and export-only path
    is): it is inside such a directory, holds one, or is or holds a nested checkout."""
    for r in _spellings(rel):
        key = _dir_key(r)
        if is_english_only(r) or _starts(key, ENGLISH_ONLY_PREFIXES):
            return True
        if any(p.startswith(key) for p in ENGLISH_ONLY_PREFIXES + ENGLISH_ONLY_EXACT):
            return True
        if WORKTREES.startswith(key) or key.startswith(WORKTREES):
            return True
    return False


def decodes_u_escapes(rel: str) -> bool:
    key = rel.casefold()
    return key in UNESCAPE_EXACT or _starts(key, UNESCAPE_PREFIXES)


# -- what would be written --------------------------------------------------------------------

Piece = Tuple[str, int, str]   # (label, line number, line)
# What a unit would write: called with True, it adds the lines read across markup (_joined).
Loader = Callable[[bool], List[Piece]]
ACROSS = "read across lines (an HTML comment or tag spans the line break), "


class Unjudgeable(Exception):
    """A write this hook cannot judge in full. It is refused, never judged in part."""


def _crlf(s: str) -> str:
    return s.replace("\r\n", "\n")


def _split(text: str) -> List[str]:
    """Lines as Markdown and HTML end them (see "Lines are split" in the module docstring)."""
    return _crlf(text).split("\n")


def _lines(label: str, text: str) -> List[Piece]:
    return [(label, n, line) for n, line in enumerate(_split(text), 1)]


def _spans_across(text: str) -> Iterator[Tuple[int, int]]:
    """(start, end) of every HTML comment and tag in `text` that spans a line break, in order,
    in time linear in the text.

    Read left to right, as a regular expression search would, from each "<" in turn; after a
    span, the search goes on from its end. At a "<", in this order:
      - a comment, <!-- ... --> with a line break before its first "-->" (the short <!--> and
        <!---> never span one). An opener with no "-->" after it is never closed and is read
        on as an ordinary "<".
      - a tag with a line break in it, in the grouped reading (a quoted attribute value or a
        {...} expression may hold "<", ">" and line breaks), then in the plain one (no "<" or
        ">" inside), so an unclosed quote or brace does not hide a tag. A tag on one line is
        left to the line readings.
    The next "-->" and the next line break are looked up once and reused until the search
    passes them, so many openers before one far close cost no rescans. Each tag match reads
    forward from its own "<" and can pass a later "<" only inside a group. A reading is in one
    of five states (outside, in '"', in "'", one or two braces deep), and every character
    moves the readings that survive it between those states one-to-one (outside, a "<" or a
    "}" ends a reading; two braces deep, a "{" does). Two readings in different states
    therefore never meet, a new one starts outside where no older one can be, and at most
    five pass any point of the text: the whole search is linear. A tag inside a comment that
    ends on its own line is not seen as inside it; that only removes more text from this one
    reading."""
    i = 0
    close = nl = -2       # cached: the next "-->" and the next "\n" at or after a search point
    while True:
        i = text.find("<", i)
        if i < 0:
            return
        if text.startswith("<!--", i) and not text.startswith(("<!-->", "<!--->"), i):
            if close == -2 or 0 <= close < i + 4:
                close = text.find("-->", i + 4)
            if nl == -2 or 0 <= nl < i + 4:
                nl = text.find("\n", i + 4)
            if close >= 0 and 0 <= nl < close:
                yield i, close + 3
                i = close + 3
                continue
        m = _TAG_GROUPED_ACROSS_RE.match(text, i)
        if m is None or text.find("\n", i, m.end()) < 0:
            m = _TAG_PLAIN_ACROSS_RE.match(text, i)
        if m is not None:
            yield m.span()
            i = m.end()
        else:
            i += 1


def _joined(text: str) -> List[Tuple[int, str]]:
    """(line number, line) for every line that an HTML comment or tag spanning a line break
    joins, with those spans removed: the line as it renders. Linear in the text.

    Raises Unjudgeable once a hook call has joined more than MAX_JOINED_LINES lines: each
    costs Python-level work, and a hook that runs past its timeout is let through."""
    spans = list(itertools.islice(_spans_across(text), _JOINED_BUDGET[0] + 1))
    _JOINED_BUDGET[0] -= len(spans)
    if _JOINED_BUDGET[0] < 0:
        raise Unjudgeable(f"more than {MAX_JOINED_LINES} lines are joined by HTML comments or "
                          f"tags that span a line break")
    out: List[Tuple[int, str]] = []
    line_no, counted, i = 1, 0, 0
    while i < len(spans):
        a, b = spans[i]
        start = text.rfind("\n", 0, a) + 1
        parts = [text[start:a]]
        end = b
        i += 1
        while True:
            eol = text.find("\n", end)
            eol = len(text) if eol < 0 else eol
            if i < len(spans) and spans[i][0] < eol:
                parts.append(text[end:spans[i][0]])
                end = spans[i][1]
                i += 1
            else:
                parts.append(text[end:eol])
                break
        line_no += text.count("\n", counted, start)
        counted = start
        out.append((line_no, "".join(parts)))
    return out


def _text_pieces(label: str, text: str, across: bool) -> List[Piece]:
    out = _lines(label, text)
    if across:
        out += [(label + ACROSS, n, line) for n, line in _joined(_crlf(text))]
    return out


def _edit_strings(e: dict) -> Tuple[object, object]:
    """(old, new) of one edit, in Claude Code's and the MCP servers' spellings."""
    old = e.get("old_string", e.get("oldText"))
    new = e.get("new_string", e.get("newText"))
    return old, new


def _count(e: dict) -> int:
    """How many occurrences one edit replaces: -1 for all."""
    if e.get("replace_all") is True:
        return -1
    n = e.get("expected_replacements")
    if isinstance(n, (int, float)) and not isinstance(n, bool) and n >= 1 and n == int(n):
        return int(n)
    return 1


# -- how each tool applies an edit (see "How each tool applies an edit") ----------------------

def _readings(tool_name: object, dollar: bool) -> List[str]:
    """The ways the tool that made the call may apply an edit; "_js" readings only when a new
    string holds a "$" (without one they equal the plain reading)."""
    name = tool_name if isinstance(tool_name, str) else ""
    if name in ("Edit", "MultiEdit"):
        out = ["edit"]
    elif name.endswith("edit_file"):
        out = ["edit_file", "edit_file_js"]
    elif name.endswith("edit_block"):
        out = ["edit_block"]
    else:
        out = ["edit", "edit_file", "edit_file_js", "edit_block"]
    return [r for r in out if dollar or not r.endswith("_js")]


def _unquote(s: str) -> str:
    """Curly quotes read as straight ones, one character for one, so indices stay aligned."""
    return (s.replace("\u2018", "'").replace("\u2019", "'")
            .replace("\u201c", '"').replace("\u201d", '"'))


# JavaScript's whitespace and line terminators: what String.prototype.trim removes.
_JS_SPACE = ("\t\n\x0b\x0c\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007"
             "\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff")
_JS_INDENT_RE = re.compile("[" + re.escape(_JS_SPACE) + "]*")
_JS_PATTERN_RE = re.compile(r"\$([$&`'])")


def _js_replacement(new: str, s: str, i: int, j: int) -> str:
    """`new` as String.prototype.replace reads a replacement string for the match s[i:j]:
    $$ is "$", $& the match, $` the text before it, $' the text after it."""
    sizes = {"$": 1, "&": j - i, "`": i, "'": len(s) - j}
    size = len(new) + sum(sizes[m.group(1)] - 2 for m in _JS_PATTERN_RE.finditer(new))
    if size > MAX_SIMULATED_BYTES:
        raise Unjudgeable(f"its new text, read as a JavaScript replacement pattern, would "
                          f"write more than {MAX_SIMULATED_BYTES // 1_000_000} MB")

    def rep(m: "re.Match[str]") -> str:
        k = m.group(1)
        return "$" if k == "$" else s[i:j] if k == "&" else s[:i] if k == "`" else s[j:]
    return _JS_PATTERN_RE.sub(rep, new)


def _flex(current: str, old: str, new: str) -> Optional[str]:
    """edit_file's fallback: `old`'s lines matched against the file's with the whitespace
    around each line ignored, and the first match replaced by `new`'s lines, indented as the
    matched line is. None if nothing matches. One substring search, so linear in the file:
    the stripped lines are joined with LF and searched with LF on both sides, which aligns a
    match with whole lines."""
    old_lines = old.split("\n")
    lines = current.split("\n")
    hay = "\n" + "\n".join(line.strip(_JS_SPACE) for line in lines) + "\n"
    at = hay.find("\n" + "\n".join(line.strip(_JS_SPACE) for line in old_lines) + "\n")
    if at < 0:
        return None
    i = hay.count("\n", 0, at)
    indent = _JS_INDENT_RE.match(lines[i]).group(0)
    out: List[str] = []
    for j, line in enumerate(new.split("\n")):
        old_indent = _JS_INDENT_RE.match(old_lines[j]).group(0) if j < len(old_lines) else ""
        new_indent = _JS_INDENT_RE.match(line).group(0)
        if j == 0:
            out.append(indent + line.lstrip(_JS_SPACE))
        elif old_indent and new_indent:
            out.append(indent + " " * max(0, len(new_indent) - len(old_indent))
                       + line.lstrip(_JS_SPACE))
        else:
            out.append(line)
    return "\n".join(lines[:i] + out + lines[i + len(old_lines):])


def _apply(current: str, edits: List[dict], reading: str) -> Optional[str]:
    """The file after the edits, applied as `reading` applies them, or None if one of them
    does not apply."""
    for e in edits:
        old, new = _edit_strings(e)
        if not isinstance(old, str) or not isinstance(new, str):
            return None
        old, new = _crlf(old), _crlf(new)
        if reading == "edit":
            if not old:
                return None
            if old not in current:
                at = _unquote(current).find(_unquote(old))
                if at < 0:
                    return None
                old = current[at:at + len(old)]
            if not new and not old.endswith("\n") and old + "\n" in current:
                old += "\n"
            current = current.replace(old, new, _count(e))
        elif reading == "edit_block":
            if not old or old not in current:
                return None
            current = current.replace(old, new, _count(e))
        elif old in current:   # edit_file; an empty oldText is found at the start
            at = current.find(old)
            if reading == "edit_file_js":
                new = _js_replacement(new, current, at, at + len(old))
            current = current[:at] + new + current[at + len(old):]
        else:
            flexed = _flex(current, old, new)
            if flexed is None:
                return None
            current = flexed
    return current


def _changed(before: str, after: str) -> List[Piece]:
    """The lines of `after` that the change wrote, in time linear in the file.

    The leading and trailing lines both versions share are set aside; of the rest, a line of
    `after` counts as written unless an identical line, not already counted, is among the
    lines it replaces. Moving or reordering lines therefore writes nothing new; repeating an
    existing line one time more than before writes that line."""
    a, b = _split(before), _split(after)
    n = min(len(a), len(b))
    lo = 0
    while lo < n and a[lo] == b[lo]:
        lo += 1
    hi = 0
    while hi < n - lo and a[-1 - hi] == b[-1 - hi]:
        hi += 1
    replaced = Counter(a[lo:len(a) - hi])
    out: List[Piece] = []
    for j, line in enumerate(b[lo:len(b) - hi]):
        if replaced[line] > 0:
            replaced[line] -= 1
        else:
            out.append(("after the edit, ", lo + j + 1, line))
    return out


def _changed_joined(before_joined: "Counter[str]", after: str) -> List[Piece]:
    """The joined lines (_joined) of `after` that are not in the file before, with
    multiplicity: an edit is judged by what it makes render, not by what already did."""
    seen = Counter(before_joined)
    out: List[Piece] = []
    for n, line in _joined(after):
        if seen[line] > 0:
            seen[line] -= 1
        else:
            out.append(("after the edit, " + ACROSS, n, line))
    return out


def _read_text(path: str, limit: int) -> Optional[str]:
    """The file as text, or None if it is missing, larger than `limit`, or holds a NUL byte."""
    try:
        if not os.path.isfile(path) or os.path.getsize(path) > limit:
            return None
        with open(path, "rb") as fh:
            data = fh.read()
        if b"\x00" in data:
            return None
        return data.decode("utf-8", errors="replace")
    except Exception:
        return None


def _simulated(raw: str, tool_input: dict, edits: Optional[List[dict]], readings: List[str],
               across: bool) -> Optional[Tuple[List[Piece], bool]]:
    """(the lines the call writes, whether every reading applied), or None if the file cannot
    be read. Without `edits` the call is an append."""
    try:
        before = _read_text(raw, MAX_SIMULATED_BYTES)
        if before is None:
            return None
        before = _crlf(before)
        afters: List[str] = []
        complete = True
        if edits is None:
            afters.append(before + _crlf(tool_input["content"]))
        else:
            for reading in readings:
                after = _apply(before, edits, reading)
                if after is None:
                    complete = False
                elif after not in afters:
                    afters.append(after)
        before_joined = Counter(line for _, line in _joined(before)) if across else Counter()
        pieces: List[Piece] = []
        for after in afters:
            pieces += _changed(before, after)
            if across:
                pieces += _changed_joined(before_joined, after)
        return pieces, complete
    except Unjudgeable:
        raise
    except Exception:
        return None


def _dedupe(pieces: List[Piece]) -> List[Piece]:
    seen = set()
    out: List[Piece] = []
    for p in pieces:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def pieces_to_judge(tool_input: dict, raw: str, tool_name: object = None,
                    across: bool = False) -> List[Piece]:
    """(label, line number, line) for every line of text the tool call would write; with
    `across`, also every line it would join across markup (_joined)."""
    edits: Optional[List[dict]] = None
    if isinstance(tool_input.get("edits"), list):
        edits = [e for e in tool_input["edits"] if isinstance(e, dict)]
    elif any(isinstance(tool_input.get(k), str) for k in ("old_string", "oldText")):
        edits = [tool_input]
    appending = (tool_input.get("mode") == "append"
                 and isinstance(tool_input.get("content"), str))
    out: List[Piece] = []
    if edits or appending:
        dollar = any(isinstance(_edit_strings(e)[1], str) and "$" in _edit_strings(e)[1]
                     for e in edits or [])
        sim = _simulated(raw, tool_input, edits or None, _readings(tool_name, dollar), across)
        if sim is not None:
            out, complete = sim
            if complete:
                return _dedupe(out)

    # every new string on its own (also when a reading of the edit did not apply)
    for key in ("content", "new_string", "newText", "new_source"):
        v = tool_input.get(key)
        if isinstance(v, str):
            out += _text_pieces("", v, across)
    content = tool_input.get("content")
    if isinstance(content, list):   # write_pdf operations
        for n, op in enumerate(content, 1):
            if isinstance(op, dict) and isinstance(op.get("markdown"), str):
                out += _text_pieces(f"operation {n}, ", op["markdown"], across)
    if isinstance(tool_input.get("edits"), list):
        for n, e in enumerate(tool_input["edits"], 1):
            if isinstance(e, dict):
                new = _edit_strings(e)[1]
                if isinstance(new, str):
                    out += _text_pieces(f"edit {n}, ", new, across)
    return _dedupe(out)


Unit = Tuple[List[str], Loader]   # (repository-relative spellings, text)


def _nothing(across: bool) -> List[Piece]:
    return []


def _moved_text(path: str, limit: int) -> Tuple[Optional[str], int]:
    """(text, size in bytes) of a moved file; text is None when there is none to judge (not a
    regular file, or one holding a NUL byte: an image, say). Raises Unjudgeable when the file
    is larger than `limit` or cannot be read."""
    if not os.path.isfile(path):
        return None, 0
    try:
        size = os.path.getsize(path)
        if size > limit:
            raise Unjudgeable(f"a moved file, {os.path.basename(path)!r}, is {size} bytes, more "
                              f"than the {limit} left to judge")
        with open(path, "rb") as fh:
            data = fh.read(limit + 1)
    except OSError as e:
        raise Unjudgeable(f"a moved file, {os.path.basename(path)!r}, cannot be read "
                          f"({type(e).__name__})")
    if len(data) > limit:
        raise Unjudgeable(f"a moved file, {os.path.basename(path)!r}, is larger than the "
                          f"{limit} bytes left to judge")
    if b"\x00" in data:
        return None, len(data)
    return data.decode("utf-8", errors="replace"), len(data)


def moved_units(rels: List[str], src: str) -> List[Unit]:
    """What a move writes: the destination, and for a directory every name inside it.

    Raises Unjudgeable for a tree too large to judge in full, and its loaders do for a file
    too large or unreadable, but only for a destination that can hold an English-only path."""
    if os.path.isfile(src):
        def single(across: bool) -> List[Piece]:
            text = _moved_text(src, MAX_SIMULATED_BYTES)[0]
            return _text_pieces("the moved file, ", text or "", across)
        return [(rels, single)]
    units: List[Unit] = [(rels, _nothing)]
    if not os.path.isdir(src) or not any(may_hold_guarded(r) for r in rels):
        return units
    budget = [MAX_SIMULATED_BYTES, MAX_MOVED_FILES]

    def text_of(path: str, inner: str, across: bool) -> List[Piece]:
        text, size = _moved_text(path, budget[0])
        if text is None:
            return []
        if budget[1] <= 0:
            raise Unjudgeable(f"the moved directory holds more than {MAX_MOVED_FILES} files "
                              f"of text")
        budget[0] -= size
        budget[1] -= 1
        return _text_pieces(f"{inner}, ", text, across)

    names = 0
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames.sort()
        here = os.path.relpath(dirpath, src)
        for name in dirnames + sorted(filenames):
            names += 1
            if names > MAX_MOVED_NAMES:
                raise Unjudgeable(f"the moved directory holds more than {MAX_MOVED_NAMES} "
                                  f"entries")
            inner = _nfc(name if here == os.curdir else os.path.join(here, name)).replace(
                os.sep, "/")
            full = os.path.join(dirpath, name)
            loader: Loader = _nothing
            if name in filenames:
                loader = (lambda across, p=full, i=inner: text_of(p, i, across))
            inner_rels: List[str] = []
            for r in rels:
                inner_rels += [s for s in _spellings(r + "/" + inner) if s not in inner_rels]
            units.append((inner_rels, loader))
    return units


# -- judging ----------------------------------------------------------------------------------

def _fold(s: str) -> str:
    """Apply _TRANSLATE and drop format and control characters.

    One str.replace per distinct character that needs it, rather than str.translate, which
    looks every character of a non-ASCII text up in a dict and is many times slower on a large
    write. The ASCII controls are dropped in _prep, by a regular expression."""
    for c in set(s):
        cp = ord(c)
        if cp < 0x80:
            continue
        if cp in _TRANSLATE:
            s = s.replace(c, _TRANSLATE[cp] or "")
        elif unicodedata.category(c) in ("Cf", "Cc"):
            s = s.replace(c, "")
    return s


def _prep(s: str) -> str:
    s = unicodedata.normalize("NFKC", _ASCII_CONTROLS_RE.sub("", s))
    if not s.isascii():
        # normalised again after the drops, so a letter split by an invisible one recombines
        s = _fold(unicodedata.normalize("NFKC", _fold(s)))
    return _MD_ESCAPE_RE.sub(r"\1", s)


def _unescape_u(s: str) -> str:
    def rep(m: "re.Match[str]") -> str:
        cp = int(m.group(1) or m.group(2) or m.group(3), 16)
        return chr(cp) if cp <= 0x10FFFF else m.group(0)
    out = _U_ESCAPE_RE.sub(rep, s)
    # rejoin surrogate pairs written as two escapes; a lone one stays harmless
    return out.encode("utf-16", "surrogatepass").decode("utf-16", "replace")


def _strip_markup(s: str) -> str:
    s = _TAG_RE.sub("", s)
    s = _LINK_RE.sub(r"\1", s)
    return _MARKUP_CHARS_RE.sub("", s)


def _variants(line: str, entities: bool, u_escapes: bool, markup: bool) -> List[Tuple[str, str]]:
    out = [("", line)]
    try:
        dec = html.unescape(line) if entities else line
        if u_escapes:
            dec = _unescape_u(dec)
        if dec != line:
            out.append((", written as an escape or entity", dec))
        if markup:
            # after normalisation, so a fullwidth or escaped marker character is removed too
            p = _prep(dec)
            bare = _strip_markup(p)
            if bare != p:
                out.append((", split by inline markup", bare))
    except Exception:
        pass
    return out


def judge_line(line: str, *, ids: bool, entities: bool, u_escapes: bool,
               markup: bool = False) -> List[str]:
    found: List[str] = []
    seen = set()
    for suffix, text in _variants(line, entities, u_escapes, markup):
        s = _prep(text)
        hits: List[str] = []
        ch = _TURKISH_RE.search(s)
        if ch is not None:
            hits.append(f"Turkish letter U+{ord(ch.group(0)):04X}")
        elif any(seq in s for seq in TURKISH_SEQUENCES):
            hits.append("Turkish dotted i (i + U+0307)")
        if ids:
            hits += [f"private identifier {m.group(0)!r}" for m in PRIVATE_ID_RE.finditer(s)]
            if PRIVATE_MARKER in s.casefold():
                hits.append("the private marker")
        for h in hits:
            if h not in seen:
                seen.add(h)
                found.append(h + suffix)
    return found


def judge_pieces(pieces: List[Piece], *, ids: bool, u_escapes: bool) -> List[str]:
    """Findings for the written lines, each naming its line.

    Lines are first judged CHUNK_LINES at a time, joined by newlines, and one by one only in a
    chunk that has a finding. Every reading in judge_line is line-local (no pattern, entity,
    escape or tag it reads spans a newline, and a newline is never dropped), so a chunk has a
    finding whenever one of its lines does; the chunk pass only keeps a large clean write
    fast. A comment or tag that does span a line break is read before this, by _joined: the
    lines it joins arrive here as pieces of their own. Judging stops once there are more
    findings than the message reports, which keeps a large write that is wrong on every line
    fast too."""
    out: List[str] = []
    for i in range(0, len(pieces), CHUNK_LINES):
        if len(out) > MAX_REPORTED:
            break
        chunk = pieces[i:i + CHUNK_LINES]
        if len(chunk) > 1 and not judge_line("\n".join(p[2] for p in chunk), ids=ids,
                                             entities=ids, u_escapes=u_escapes, markup=ids):
            continue
        for label, n, line in chunk:
            out += [f"{label}line {n}: {h}"
                    for h in judge_line(line, ids=ids, entities=ids, u_escapes=u_escapes,
                                        markup=ids)]
    return out


def block(msg: str) -> int:
    sys.stderr.write(f"PUBLIC BOUNDARY: blocked.\n\n{msg}")
    return 2


def _listing(findings: List[str]) -> str:
    shown = findings[:MAX_REPORTED]
    listing = "\n".join(f"  - {f}" for f in shown)
    if len(findings) > len(shown):
        listing += "\n  - and more"
    return listing


def judge_unit(rels: List[str], pieces: Loader) -> Optional[str]:
    """The block message for one written path, or None if it may be written."""
    public = next((r for r in rels if is_public(r)), None)
    english = public or next((r for r in rels if is_english_only(r)), None)
    if english is None:
        return None
    ids = public is not None
    u_escapes = ids and any(decodes_u_escapes(r) for r in rels)

    findings: List[str] = []
    for r in rels:
        if not is_english_only(r):
            continue
        for h in judge_line(r, ids=ids, entities=False, u_escapes=False):
            f = f"the file name {ascii(r)}: {h}"
            if f not in findings:
                findings.append(f)
    findings += judge_pieces(pieces(ids), ids=ids, u_escapes=u_escapes)
    if not findings:
        return None

    if public is not None:
        return (
            f"{public} is a public, English-only path (D-031). The new text contains:\n"
            f"{_listing(findings)}\n\n"
            f"Write it in English, with no private identifiers and no private marker. Private\n"
            f"detail stays in the private companion and moves here only under\n"
            f"docs/thesis/disclosure-policy.md. Proper names are written in ASCII, as\n"
            f"CITATION.cff writes the author's. If a Turkish letter is genuinely required,\n"
            f"stop and ask Cagan; do not route the text around this check.\n")
    return (
        f"{english} is English-only (D-031; the push-time leak check in\n"
        f"tools/publish/leak_check.py refuses the same). The new text contains:\n"
        f"{_listing(findings)}\n\n"
        f"Write it in English. Proper names are written in ASCII. Detection patterns in\n"
        f"source code are written as \\u escapes, as leak_check.py and check_copy.py do.\n"
        f"If a Turkish letter is genuinely required, stop and ask Cagan.\n")


def _export_only_message(rel: str, moving_out: bool) -> str:
    if moving_out and not is_export_only(rel):
        what = f"{rel}: this moves a directory that holds thesis/src/ or thesis/tests/"
    else:
        verb = "moves a file out of" if moving_out else "writes under"
        what = f"{rel}: this {verb} thesis/src/ or thesis/tests/"
    return (
        f"{what}, which are export-only (D-031).\n"
        f"No agent writes there. The thesis package changes only through a release\n"
        f"export that Cagan runs, under docs/thesis/disclosure-policy.md.\n")


def _unjudgeable_message(rel: str, why: str) -> str:
    return (
        f"{rel}: {why}. This hook judges a write in full or not at all, so it refuses\n"
        f"what it cannot read whole rather than pass it half-judged. Move or write it in\n"
        f"smaller parts, or ask Cagan.\n")


def _target_and_source(tool_input: dict) -> Tuple[Optional[str], Optional[str]]:
    """The path the call writes, and for a move the path it takes the content from."""
    for key in ("file_path", "notebook_path", "outputPath", "destination", "path"):
        v = tool_input.get(key)
        if isinstance(v, str) and v:
            src = tool_input.get("source") if key == "destination" else None
            return v, (src if isinstance(src, str) and src else None)
    return None, None


def main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        if not isinstance(payload, dict):
            return 0
        tool_input = payload.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            return 0
        target, source = _target_and_source(tool_input)
        if target is None:
            return 0
        cwd = payload.get("cwd") or ""
        cwd = cwd if isinstance(cwd, str) else ""
        tool_name = payload.get("tool_name")

        if source is not None:
            src_cands = resolve_target(source, cwd)
            out_of = next((r for r in all_relatives(src_cands, cwd)
                           if is_export_only(r) or holds_export_only(r)), None)
            if out_of is not None:
                return block(_export_only_message(out_of, moving_out=True))

        cands = resolve_target(target, cwd)
        rels = all_relatives(cands, cwd)
        if not rels:
            return 0
        try:
            if source is not None:
                units = moved_units(rels, src_cands[0])
            else:
                units = [(rels, lambda across: pieces_to_judge(tool_input, cands[0], tool_name,
                                                               across))]
            for unit_rels, _pieces in units:
                export = next((r for r in unit_rels if is_export_only(r)), None)
                if export is not None:
                    return block(_export_only_message(export, moving_out=False))
            for unit_rels, pieces in units:
                msg = judge_unit(unit_rels, pieces)
                if msg is not None:
                    return block(msg)
        except Unjudgeable as e:
            return block(_unjudgeable_message(rels[0], str(e)))
        return 0
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
