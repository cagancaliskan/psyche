#!/usr/bin/env python3
"""leak_check.py — inspect every commit about to become public, not just the end state.

A push publishes history, not a diff. A file added in one commit and deleted in the next is
still downloadable; so is a commit message, an author field, a file name. An end-state scan
misses all of those, so this walks the whole range (D-031, the disclosure rule):

  added lines    `git show -p --cc --text` for each commit; removed and context lines are
                 ignored. --text, because a .gitattributes `-diff` or `binary` attribute
                 (even one committed inside the range) or a NUL byte would otherwise reduce
                 the content to "Binary files differ". A merge is read as a combined diff,
                 so only lines that are new relative to EVERY parent count: content a merge
                 brings in from an already-public parent is not re-reported, an edit made in
                 the merge is.
                 A file whose added lines are not all valid UTF-8, or hold a NUL byte, is
                 looked at whole, as committed. The NUL matters: UTF-16 text is often
                 valid UTF-8 byte by byte (ASCII becomes the character and a NUL, and six
                 Turkish letters encode as two bytes below 0x80), so its diff lines would
                 be read as NUL-interleaved text that no rule matches. UTF-16 or UTF-32
                 text (a byte-order mark, or the NUL pattern of mostly-ASCII UTF-16) is
                 decoded and every line checked. Known limit: BOM-less UTF-16 is known
                 only by that NUL pattern (check_disclosure.text_encoding), so a file with
                 almost no ASCII in its first block is not recognised as UTF-16. Valid
                 UTF-8 added lines with a NUL, in a file that is not UTF-16 or UTF-32, are
                 read as they are, every rule at its line. Content with no NUL byte
                 anywhere (UTF-8 with a stray invalid byte, wherever it sits, or a one-byte
                 encoding) is text: its added lines are read with each invalid byte
                 replaced, and every rule applies, LANGUAGE included. Anything else is
                 binary: only its printable runs (ASCII or UTF-16, six characters or more,
                 read by check_disclosure.binary_strings, as `strings` reads them) are
                 checked, for HOME-PATH, PRIVATE-ID and DENYLIST, and reported as "binary
                 content". LANGUAGE does not apply to binary content, and compressed content
                 (a PNG, a PDF stream) cannot be read at all.
  messages       every line of every commit message
  author fields  author and committer name and email
  file names     every path each commit adds or changes, taken from the commit itself
                 (`git diff-tree` against each parent; for a merge, only the paths that
                 differ from every parent), plus every path `git rev-list --objects` lists
                 for the range. Each path and every directory above it is checked. Taking
                 paths from the commits and not only from new objects matters: an empty
                 file, a copy or a rename of a public file adds no new object but still
                 publishes a new name.

A denylist phrase is matched across line breaks: over each run of lines a hunk leaves in the
file (a hit counts when it touches an added line, and is reported at the first added line it
touches), and over the whole commit message. It is matched in every rendering
check_disclosure.py scans for a file of that suffix (check_disclosure.variants): the raw
text, the text with "-" and "_" read as spaces, tags stripped and entities decoded,
Markdown punctuation removed, JSX string expressions unwrapped, string and CSS escapes
decoded. So a term written as **Zephyr** Moss, <em>zephyr</em> moss, zephyr-moss or behind
a \\u escape, added and removed again inside the range, is caught here although the
end-state scan no longer sees it. A path is matched as check_disclosure matches one (whole,
and component by component). All text is compared in Unicode NFC, so a letter written as a
base letter plus a combining mark is the same letter.

Rules:

  LANGUAGE        a Turkish letter in an English-only path: README.md, MOC.md, CLAUDE.md,
                  docs/PSYCHE.md, tools/thesis_plan.json, and everything under docs/thesis/,
                  thesis/, website/, tools/publish/ and .github/, compared case-folded as
                  guard_public_boundary.py compares them (a root readme.md is the README
                  GitHub renders). Commit messages are English-only too. Author fields are
                  names, so this rule skips them.
  HOME-PATH       an absolute home-directory path (macOS slash-Users-slash, or the Windows
                  form), which names the machine's user and its folder layout.
  UNVERIFIED-TAG  the shape of a private working-note tag: a bracket that opens with an
                  upper-case token holding an upper-case Turkish letter, and either closes
                  at once or goes on, after a separator (a colon, semicolon, space, dash or
                  the like), with any content up to the closing bracket on that line. The
                  tag words themselves are private, so they are not spelled here; the
                  denylist carries them, and the DENYLIST rule reports them by number.
                  Known limit, asserted in test_checks.py: a tag whose token holds no
                  Turkish letter is not this rule's shape (an all-ASCII shape would also
                  flag English labels, such as a bracketed upper-case note in a log
                  message), so it is caught only through the denylist. A denylist entry
                  written as a prefix regex (re:\\[WORD\\b) catches such a tag whatever
                  content follows the word; an entry that spells one exact tag does not.
  PRIVATE-ID      a private identifier: experiment ids (E- and two digits), decision
                  records (ADR- and three digits), open questions (Q-ADM-, Q-M-, Q-E- and a
                  number), in any letter case; not when glued to a preceding letter or
                  digit, but also after "-" or "_", exactly as guard_public_boundary.py
                  matches them.
  DENYLIST        an entry of the private denylist (--denylist FILE or --denylist-env NAME),
                  in the format check_disclosure.py reads. Reported by entry number only.

A denylist is required. Running without one needs --no-denylist, said explicitly: a push
check that silently skips its main rule guards very little.

Nothing matched is ever printed: a finding names the commit, the path, the line and the
rule, never the text, because this output lands in public CI logs. In a printed path every
span a rule matches is masked: a denylisted span as [#K], a home directory as [HOME], a tag
as [TAG], an identifier as [ID], a Turkish letter as [U+XXXX].

git runs with the settings that change its output pinned (log.showRoot,
diff.suppressBlankEmpty, diff.relative, diff.context and diff.interHunkContext (and -U on
git show), the diff prefixes, colour, path quoting, and replace refs off), so neither the
user's nor the repository's configuration can hide a commit's content. The context matters:
with diff.context=0 a hunk would hold only its added lines, and a denylisted phrase that an
added line completes next to an unchanged line would never be read whole.

Exit 0 = clean. Exit 1 = at least one finding. Exit 2 = the check could not run: the range
is invalid, git failed, no denylist was given (and --no-denylist was not), a named
denylist cannot be used, or check_disclosure.py (whose matching this reuses) cannot be
imported.

Usage:
    python3 tools/publish/leak_check.py --range origin/main..HEAD --denylist PRIVATE/denylist.txt
    python3 tools/publish/leak_check.py --range origin/main..HEAD --denylist-env DISCLOSURE_DENYLIST
    python3 tools/publish/leak_check.py --root PATH --range A..B --no-denylist [--quiet]

Stdlib only.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent


def _load_sibling(name: str):
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    path = HERE / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return mod


CD = None
LOAD_ERROR: Optional[str] = None
try:
    CD = _load_sibling("check_disclosure")
except Exception as _e:          # reported by main() as exit 2, never as a traceback
    # no str(_e): an OSError carries the absolute path of this checkout
    _line = f", line {_e.lineno}" if isinstance(_e, SyntaxError) and _e.lineno else ""
    LOAD_ERROR = f"tools/publish/check_disclosure.py ({type(_e).__name__}{_line})"

ENGLISH_ONLY_FILES = {
    "README.md", "MOC.md", "CLAUDE.md", "docs/PSYCHE.md", "tools/thesis_plan.json",
}
ENGLISH_ONLY_DIRS = ("docs/thesis/", "thesis/", "website/", "tools/publish/", ".github/")

# Escaped on purpose: this file is on an English-only path.
TURKISH_RE = re.compile("[\u00e7\u011f\u0131\u00f6\u015f\u00fc\u00c7\u011e\u0130\u00d6\u015e\u00dc]")
_TR_UPPER = "\u00c7\u011e\u0130\u00d6\u015e\u00dc"
HOME_RE = re.compile("/" + "Users" + "/" + "|" + r"\\" + "Users" + r"\\")
HOME_MASK_RE = re.compile("(?:/" + "Users" + "/|" + r"\\" + "Users" + r"\\" + r")[^/\\\s]*")
# A tag's shape, never its words: a bracket that opens with an upper-case token holding an
# upper-case Turkish letter, then either closes or goes on, after a separator, with any
# content up to the closing bracket on that line: [TOKEN], [TOKEN: lower-case text],
# [TOKEN; a b], [TOKEN - note]. A bracket whose token holds no Turkish letter is not this
# rule's: the denylist carries those tag words (see the module docstring).
_TAG_TOKEN = r"[A-Z0-9 _\-" + _TR_UPPER + r"]"
_TAG_SEP = "[:;,.'\"/( \\t\\-\u2010-\u2015]"
TAG_RE = re.compile(r"\[" + _TAG_TOKEN + r"*[" + _TR_UPPER + r"]" + _TAG_TOKEN + r"*"
                    r"(?:" + _TAG_SEP + r"[^\]\n]*)?\]")
# Not glued to a preceding letter or digit (that keeps 1E-12 and TYPE-12 out), but matched
# after "-" or "_", as in a file name such as notes-E-.., and in any letter case, exactly as
# guard_public_boundary.py's PRIVATE_ID_RE matches them (re.IGNORECASE there too).
PRIVATE_ID_RES = (
    ("experiment id", re.compile(r"(?<![A-Za-z0-9])E-\d{2}", re.IGNORECASE)),
    ("decision-record id", re.compile(r"(?<![A-Za-z0-9])ADR-\d{3}", re.IGNORECASE)),
    ("open-question id", re.compile(r"(?<![A-Za-z0-9])Q-(?:ADM|M|E)-\d+", re.IGNORECASE)),
)

# diff.context and diff.interHunkContext are pinned as well (and -U is passed to git show):
# with diff.context=0 a hunk holds only its added lines, and a denylisted phrase that an
# added line completes next to an unchanged line would never be read whole.
DIFF_CONTEXT = 3
GIT = ["git", "--no-replace-objects",
       "-c", "core.quotepath=false", "-c", "color.ui=never",
       "-c", "log.showSignature=false", "-c", "log.showRoot=true",
       "-c", "diff.noprefix=false", "-c", "diff.mnemonicPrefix=false",
       "-c", "diff.relative=false", "-c", "diff.suppressBlankEmpty=false",
       "-c", f"diff.context={DIFF_CONTEXT}", "-c", "diff.interHunkContext=0",
       "-c", "i18n.logOutputEncoding=UTF-8"]


class GitFailed(Exception):
    """git could not answer. Exit 2."""


@dataclass(frozen=True)
class Leak:
    where: str
    rule: str
    message: str

    def render(self) -> str:
        return f"{self.where}: [{self.rule}] {self.message}"


_ENGLISH_ONLY_FILES_CF = {f.casefold() for f in ENGLISH_ONLY_FILES}
_ENGLISH_ONLY_DIRS_CF = tuple(d.casefold() for d in ENGLISH_ONLY_DIRS)


def english_only(path: str) -> bool:
    """Case-folded, as guard_public_boundary.py compares it: a root readme.md is the README
    GitHub renders, and on a case-insensitive file system docs/Thesis/ is docs/thesis/."""
    key = path.casefold()
    return key in _ENGLISH_ONLY_FILES_CF or key.startswith(_ENGLISH_ONLY_DIRS_CF)


# ─────────────────────────────────────────────────────────────────────────────
# rules
# ─────────────────────────────────────────────────────────────────────────────

def _turkish(text: str) -> Optional["re.Match[str]"]:
    return TURKISH_RE.search(text) or CD.TURKISH_MARK_RE.search(text)


def check_text(text: str, *, language: bool,
               denylist: Optional[Sequence["CD.Entry"]]) -> List[Tuple[str, str]]:
    """(rule, message) pairs for one line of text. Messages never quote the text."""
    t = CD.nfc(text)
    out: List[Tuple[str, str]] = []
    if language:
        m = _turkish(t)
        if m:
            out.append(("LANGUAGE", f"Turkish letter U+{ord(m.group(0)):04X} in an "
                                    f"English-only place (D-031)"))
    if HOME_RE.search(t):
        out.append(("HOME-PATH", "an absolute home-directory path"))
    if TAG_RE.search(t):
        out.append(("UNVERIFIED-TAG", "the shape of a private working-note tag (a bracketed "
                                      "upper-case token with a Turkish letter)"))
    for label, rx in PRIVATE_ID_RES:
        if rx.search(t):
            out.append(("PRIVATE-ID", f"a private {label}"))
    if denylist:
        for index in CD.matching_indices(denylist, t):
            out.append(("DENYLIST", f"private term #{index}"))
    return out


def denylist_spans(entries: Sequence["CD.Entry"],
                   lines: Sequence[str]) -> List[Tuple[int, int, int]]:
    """(first line, last line, entry index), 0-based, for every hit over `lines` joined by
    newlines, so a phrase wrapped across lines is found."""
    text = "\n".join(lines)
    starts = [0]
    for ln in lines[:-1]:
        starts.append(starts[-1] + len(ln) + 1)
    out: List[Tuple[int, int, int]] = []
    for e in entries:
        for m in e.pattern.finditer(text):
            if m.end() == m.start():
                continue
            first = bisect_right(starts, m.start()) - 1
            last = bisect_right(starts, m.end() - 1) - 1
            out.append((first, last, e.index))
    return out


def denylist_hits(entries: Sequence["CD.Entry"], lines: Sequence[str],
                  suffix: str) -> List[Tuple[int, int, int]]:
    """denylist_spans over every rendering check_disclosure scans for a file of this suffix
    (raw, '-' and '_' read as spaces, tags stripped, Markdown punctuation removed, string
    escapes decoded, NFC), so a term an end-state scan would catch is caught in history
    too. Every rendering keeps the line count; one that did not would be mapped to the
    first line, never dropped."""
    joined = "\n".join(lines)
    out: Set[Tuple[int, int, int]] = set()
    for form in CD.variants(joined, suffix):
        form_lines = form.split("\n")
        if len(form_lines) == len(lines):
            out.update(denylist_spans(entries, form_lines))
        else:                                            # cannot happen
            out.update((0, len(lines) - 1, index)
                       for _, _, index in denylist_spans(entries, form_lines))
    return sorted(out)


def shown(path: str, denylist: Optional[Sequence["CD.Entry"]]) -> str:
    """A path that is safe to print: every span any rule matches is masked (a denylisted
    span failing closed, as check_disclosure prints a path)."""
    t = CD.display_path(denylist, path, path) if denylist else CD.nfc(path)
    t = HOME_MASK_RE.sub("[HOME]", t)
    t = TAG_RE.sub("[TAG]", t)
    for _, rx in PRIVATE_ID_RES:
        t = rx.sub("[ID]", t)
    t = TURKISH_RE.sub(lambda m: f"[U+{ord(m.group(0)):04X}]", t)
    return CD.TURKISH_MARK_RE.sub(lambda m: f"[U+{ord(m.group(0)):04X}]", t)


def binary_strings(data: bytes) -> List[str]:
    """Printable runs, read exactly as check_disclosure reads walked binary files."""
    return CD.binary_strings(data)


# ─────────────────────────────────────────────────────────────────────────────
# git
# ─────────────────────────────────────────────────────────────────────────────

def git_bytes(root: Path, *args: str) -> bytes:
    try:
        r = subprocess.run(GIT + list(args), cwd=root, capture_output=True)
    except OSError as e:
        raise GitFailed(f"cannot run git ({e})") from None
    if r.returncode != 0:
        err = r.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise GitFailed(f"git {args[0]} failed: {err[-1] if err else r.returncode}")
    return r.stdout


def git(root: Path, *args: str) -> str:
    return git_bytes(root, *args).decode("utf-8", errors="replace")


_ESCAPES = {"n": 10, "t": 9, '"': 34, "\\": 92, "a": 7, "b": 8, "f": 12, "r": 13, "v": 11}


def unquote_path(s: str) -> str:
    """Undo git's C-style quoting of a path ("b/we\\"ird" or octal UTF-8 bytes)."""
    if not (len(s) >= 2 and s[0] == '"' and s[-1] == '"'):
        return s
    body, out, i = s[1:-1], bytearray(), 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            n = body[i + 1]
            if n in "01234567":
                j = i + 1
                while j < len(body) and j < i + 4 and body[j] in "01234567":
                    j += 1
                out.append(int(body[i + 1:j], 8) & 0xFF)
                i = j
                continue
            out.append(_ESCAPES.get(n, ord(n)))
            i += 2
            continue
        out += c.encode("utf-8")
        i += 1
    return out.decode("utf-8", errors="replace")


_HUNK_RE = re.compile(r"^(@{2,}) .*?\+(\d+)(?:,\d+)? @{2,}")

# one line a hunk leaves in the file: (line number in the result, raw text, added?)
HunkLine = Tuple[int, bytes, bool]


@dataclass
class FileDiff:
    path: str
    hunks: List[List[HunkLine]] = field(default_factory=list)

    def has_added(self) -> bool:
        return any(added for h in self.hunks for _, _, added in h)

    def added_is_utf8(self) -> bool:
        for h in self.hunks:
            for _, text, added in h:
                if added:
                    try:
                        text.decode("utf-8")
                    except UnicodeDecodeError:
                        return False
        return True

    def added_has_nul(self) -> bool:
        """A NUL byte in an added line. UTF-16 text is often valid UTF-8 byte by byte (ASCII
        becomes the character and a NUL; six Turkish letters encode as two bytes below
        0x80), so passing added_is_utf8 does not make the diff's lines the file's lines.
        A NUL is the sign that they may not be, and sends the caller to the blob."""
        return any(added and b"\x00" in text for h in self.hunks for _, text, added in h)


def parse_diff(diff: bytes) -> List[FileDiff]:
    """Every file of a (plain or combined) diff, with the lines each hunk leaves in the
    result. Plain diffs: '+' lines are added. Combined (merge) diffs: a line is added when
    every parent column is '+', i.e. it is new relative to all parents; a line with '-' in
    any column is not in the result and is dropped. Removed lines are never returned."""
    files: List[FileDiff] = []
    cur: Optional[FileDiff] = None
    hunk: Optional[List[HunkLine]] = None
    in_hunk = False
    parents = 1
    lineno = 0
    for raw in diff.split(b"\n"):
        if raw.startswith(b"diff "):
            cur, hunk, in_hunk = None, None, False
            continue
        if raw.startswith(b"@@"):
            m = _HUNK_RE.match(raw.decode("utf-8", errors="replace"))
            if m is None:
                in_hunk = False
                continue
            parents = len(m.group(1)) - 1
            lineno = int(m.group(2))
            in_hunk = True
            hunk = None
            if cur is not None:
                hunk = []
                cur.hunks.append(hunk)
            continue
        if not in_hunk:
            if raw.startswith(b"+++ "):
                target = raw[4:].decode("utf-8", errors="replace").rstrip("\t")
                if target == "/dev/null":
                    cur = None
                else:
                    target = unquote_path(target)
                    cur = FileDiff(target[2:] if target.startswith("b/") else target)
                    files.append(cur)
            continue
        if raw.startswith(b"\\"):
            continue                       # "\ No newline at end of file"
        if not raw:
            # a blank context line written bare (diff.suppressBlankEmpty): still a line
            if hunk is not None:
                hunk.append((lineno, b"", False))
            lineno += 1
            continue
        prefix, text = raw[:parents], raw[parents:]
        if b"-" in prefix:
            continue                       # not in the result
        if hunk is not None:
            hunk.append((lineno, text, prefix == b"+" * parents))
        lineno += 1
    return files


def added_lines(diff) -> List[Tuple[str, int, str]]:
    """(path, new line number, text) for every line that is new in the result."""
    data = diff.encode("utf-8") if isinstance(diff, str) else diff
    return [(f.path, n, text.decode("utf-8", errors="replace"))
            for f in parse_diff(data) for h in f.hunks for n, text, added in h if added]


@dataclass(frozen=True)
class Commit:
    sha: str
    parents: Tuple[str, ...]
    author_name: str
    author_email: str
    committer_name: str
    committer_email: str
    message: str


def read_commit(root: Path, sha: str) -> Commit:
    raw = git(root, "show", "-s", "--format=%P%x00%an%x00%ae%x00%cn%x00%ce%x00%B", sha)
    parts = raw.split("\x00", 5)
    while len(parts) < 6:
        parts.append("")
    return Commit(sha, tuple(parts[0].split()), parts[1], parts[2], parts[3], parts[4],
                  parts[5])


def commit_diff(root: Path, sha: str) -> bytes:
    return git_bytes(root, "show", "--format=", "-p", "--cc", "--text", "--no-renames",
                     f"-U{DIFF_CONTEXT}", "--no-color", "--no-ext-diff", "--no-textconv",
                     "--src-prefix=a/", "--dst-prefix=b/", sha)


def commit_paths(root: Path, sha: str, parents: Sequence[str]) -> Set[str]:
    """The paths a commit adds or changes (not those it deletes). For a merge, only the
    paths that differ from every parent: one that equals a parent's is in that parent."""
    base = ["diff-tree", "-r", "--no-renames", "--no-commit-id", "--name-only", "-z",
            "--diff-filter=d"]
    if not parents:
        runs = [git(root, *base, "--root", sha)]
    else:
        runs = [git(root, *base, p, sha) for p in parents]
    sets = [{p for p in out.split("\x00") if p} for out in runs]
    result = sets[0]
    for s in sets[1:]:
        result &= s
    return result


# ─────────────────────────────────────────────────────────────────────────────
# the scan
# ─────────────────────────────────────────────────────────────────────────────

def check_hunks(hunks: Sequence[Sequence[Tuple[int, str, bool]]], *, language: bool,
                denylist: Optional[Sequence["CD.Entry"]],
                suffix: str = "") -> List[Tuple[int, str, str]]:
    """(line, rule, message) for decoded hunks: every rule on each added line, and the
    denylist over each hunk's lines joined, in every rendering check_disclosure reads for
    `suffix`, counted when a hit touches an added line."""
    found: Set[Tuple[int, str, str]] = set()
    for h in hunks:
        for n, text, added in h:
            if added:
                for rule, msg in check_text(text, language=language, denylist=None):
                    found.add((n, rule, msg))
        if denylist and h:
            lines = [text for _, text, _ in h]
            for first, last, index in denylist_hits(denylist, lines, suffix):
                touched = [k for k in range(first, last + 1) if h[k][2]]
                if touched:
                    found.add((h[touched[0]][0], "DENYLIST", f"private term #{index}"))
    return sorted(found)


def check_commit_diff(root: Path, sha: str, short: str,
                      denylist: Optional[Sequence["CD.Entry"]]) -> List[Leak]:
    out: List[Leak] = []
    for f in parse_diff(commit_diff(root, sha)):
        if not f.has_added():
            continue
        lang = english_only(f.path)
        suffix = Path(f.path).suffix.lower()
        where = f"{short}:{shown(f.path, denylist)}"

        def report_hunks(byte_hunks) -> None:
            hunks = [[(n, CD.nfc(text.decode("utf-8", errors="replace")), added)
                      for n, text, added in h] for h in byte_hunks]
            for n, rule, msg in check_hunks(hunks, language=lang, denylist=denylist,
                                            suffix=suffix):
                out.append(Leak(f"{where}:{n}", rule, msg))

        is_utf8 = f.added_is_utf8()
        if is_utf8 and not f.added_has_nul():
            report_hunks(f.hunks)
            continue
        # not UTF-8 in the diff, or a NUL in an added line: read the file as committed
        data = git_bytes(root, "cat-file", "blob", f"{sha}:{f.path}")
        enc = CD.text_encoding(data)
        wide = enc is not None and enc.startswith(("utf-16", "utf-32"))
        if wide or (not is_utf8 and enc is not None and enc != "utf-8"):
            # UTF-16 or UTF-32 (a BOM, or the NUL pattern of mostly-ASCII UTF-16), or (when
            # the added bytes are not UTF-8) UTF-8 behind a BOM: the diff's lines are not its
            # lines, so every line of the file is checked
            lines = CD.nfc(CD.decode_bytes(data)).replace("\r\n", "\n").split("\n")
            whole = [[(i, ln, True) for i, ln in enumerate(lines, 1)]]
            for n, rule, msg in check_hunks(whole, language=lang, denylist=denylist,
                                            suffix=suffix):
                out.append(Leak(f"{where}:{n}", rule, msg))
            continue
        if is_utf8:
            # a NUL in valid UTF-8 added lines of a file that is not UTF-16 or UTF-32 (a stray
            # NUL in text, or binary content whose added bytes happen to decode): the added
            # lines are read as they are, every rule at its line, as before the NUL check
            report_hunks(f.hunks)
            continue
        if enc == "utf-8" or b"\x00" not in data:
            # UTF-8 text with an invalid byte (in its first block or later), or text in a
            # one-byte encoding: no NUL anywhere, so it is text, not binary. Its added lines
            # are read with each invalid byte replaced, and every rule applies, LANGUAGE
            # included; one stray byte must not turn a page into "binary content".
            report_hunks(f.hunks)
            continue
        seen: Set[Tuple[str, str]] = set()
        for s in binary_strings(data):
            for rule, msg in check_text(s, language=False, denylist=denylist):
                if (rule, msg) not in seen:
                    seen.add((rule, msg))
                    out.append(Leak(f"{where}: binary content", rule, msg))
    return out


def check_names(names: Set[str],
                denylist: Optional[Sequence["CD.Entry"]]) -> List[Leak]:
    """Every path and every directory above it. A finding a directory already reported is
    not repeated for the paths beneath it."""
    every: Set[str] = set()
    dirs: Set[str] = set()
    for p in names:
        parts = p.split("/")
        for k in range(1, len(parts)):
            d = "/".join(parts[:k])
            dirs.add(d)
            every.add(d)
        every.add(p)
    out: List[Leak] = []
    reported: Dict[str, Set[Tuple[str, str]]] = {}
    for name in sorted(every, key=lambda n: (n.count("/"), n)):
        is_dir = name in dirs
        lang = english_only(name + "/" if is_dir else name)
        found = set(check_text(name, language=lang, denylist=None))
        if denylist:
            found |= {("DENYLIST", f"private term #{i}")
                      for i in CD.path_indices(denylist, name)}
        parts = name.split("/")
        inherited: Set[Tuple[str, str]] = set()
        for k in range(1, len(parts)):
            inherited |= reported.get("/".join(parts[:k]), set())
        reported[name] = found
        for rule, msg in sorted(found - inherited):
            out.append(Leak(f"{shown(name, denylist)}: file name", rule, msg))
    return out


def scan(root: Path, rng: str,
         denylist: Optional[Sequence["CD.Entry"]] = None) -> Tuple[List[Leak], int]:
    """(findings, commits inspected). Raises GitFailed."""
    shas = [s for s in git(root, "rev-list", "--reverse", rng, "--").split() if s]
    out: List[Leak] = []
    names: Set[str] = set()

    for sha in shas:
        short = sha[:10]
        c = read_commit(root, sha)

        msg_lines = [CD.nfc(ln) for ln in c.message.splitlines()]
        found: Set[Tuple[int, str, str]] = set()
        for i, line in enumerate(msg_lines, 1):
            for rule, msg in check_text(line, language=True, denylist=None):
                found.add((i, rule, msg))
        if denylist and msg_lines:
            for first, _, index in denylist_hits(denylist, msg_lines, ".txt"):
                found.add((first + 1, "DENYLIST", f"private term #{index}"))
        for i, rule, msg in sorted(found):
            out.append(Leak(f"{short}: message line {i}", rule, msg))

        for label, value in (("author name", c.author_name),
                             ("author email", c.author_email),
                             ("committer name", c.committer_name),
                             ("committer email", c.committer_email)):
            for rule, msg in check_text(value, language=False, denylist=denylist):
                out.append(Leak(f"{short}: {label}", rule, msg))

        out += check_commit_diff(root, sha, short, denylist)
        names |= commit_paths(root, sha, c.parents)

    # also every path rev-list names for a new object (a tree or a blob) in the range
    for line in git(root, "rev-list", "--objects", rng, "--").splitlines():
        _, _, path = line.partition(" ")
        if path:
            names.add(path)
    out += check_names(names, denylist)
    return out, len(shas)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--range", required=True, metavar="A..B",
                    help="the commits to inspect, as git rev-list reads them")
    ap.add_argument("--root", default=".", help="the repository (default: .)")
    deny = ap.add_mutually_exclusive_group()
    deny.add_argument("--denylist", metavar="FILE", help="the private denylist file")
    deny.add_argument("--denylist-env", metavar="NAME",
                      help="read the denylist from this environment variable")
    deny.add_argument("--no-denylist", action="store_true",
                      help="run without the DENYLIST rule (private terms are then not "
                           "checked; say so explicitly)")
    ap.add_argument("--quiet", action="store_true", help="findings only, no summary")
    args = ap.parse_args(argv)

    if CD is None:
        print(f"leak_check: cannot run: a sibling check cannot be imported: {LOAD_ERROR}",
              file=sys.stderr)
        return 2
    if args.range.startswith("-"):
        print("leak_check: cannot run: the range must not start with '-'", file=sys.stderr)
        return 2

    denylist = None
    if args.denylist is not None or args.denylist_env is not None:
        try:
            denylist = CD.load_denylist(args.denylist, args.denylist_env)
        except CD.DenylistError as e:
            print(f"leak_check: cannot run: {e}", file=sys.stderr)
            return 2
    elif not args.no_denylist:
        print("leak_check: cannot run: no denylist given; pass --denylist FILE or "
              "--denylist-env NAME, or --no-denylist to run without the DENYLIST rule",
              file=sys.stderr)
        return 2

    root = Path(args.root).resolve()
    try:
        findings, n = scan(root, args.range, denylist)
    except GitFailed as e:
        # git's own message can quote a path or a ref; it is masked like any printed path
        print(f"leak_check: cannot run: {shown(str(e), denylist)}", file=sys.stderr)
        return 2

    for f in findings:
        print(f.render())
    if not args.quiet:
        if denylist is None:
            print("leak_check: notice: --no-denylist; the DENYLIST rule did not run",
                  file=sys.stderr)
        state = f"{len(findings)} finding(s)" if findings else "clean"
        print(f"leak_check: {state}; {n} commit(s) inspected", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
