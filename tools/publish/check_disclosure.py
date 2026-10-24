#!/usr/bin/env python3
"""check_disclosure.py — no private term reaches a public surface, and no log names one.

The research line's rule is "summary public, detail private" (D-031). The words that would
give the detail away (mechanism vocabulary, thresholds, working titles, identity tokens)
cannot be listed in this repository, because the list would itself be the leak. So the list lives in
the private companion, and in CI as a secret, and this script only ever reports WHERE a
term was found and WHICH entry matched, by number. It never prints the term, the matched
text or the line, so its output is safe in a public CI log.

Denylist format (UTF-8 text, one entry per line):

    # a comment                    lines starting with '#' are ignored, as are blank lines
    some phrase                    plain entry: case-insensitive, whole word or phrase;
                                   the words may be separated by any run of whitespace
                                   (line breaks included), '-', '_' or a Unicode hyphen
                                   or dash (U+2010..U+2015)
    re:pattern                     a Python regular expression, compiled as written
                                   (MULTILINE; add (?i) yourself for case-insensitivity)

A plain entry is split into words on that same separator class, so the normalisation is
two-sided: the entries "zephyr-moss", "zephyr_moss" and "zephyr moss" are the same entry, and
each matches all three spellings, the phrase wrapped across lines, and a directory named
zephyr_moss/. A Turkish letter in a plain entry also matches its ASCII letter (c-cedilla
also c, g-breve also g, dotless and dotted i also i, o- and u-diaeresis also o and u,
s-cedilla also s), so the transliterated spelling, which the LANGUAGE rules elsewhere do not
block, is caught as well. A plain entry made only of separators is refused (exit 2). A re:
entry gets none of this: it is matched exactly as written.

Entries are numbered 1, 2, 3 ... in file order, counting entries only (comments and blank
lines do not take a number). Entries and scanned text are both compared in Unicode NFC, so a
term typed with combining marks (NFD, common in text that comes from macOS) matches the same
term typed precomposed. A hit prints as

    path:line: private term #K

A hit in a path is reported at line 0. For a file found by walking a directory, the path
below the PATH argument is matched, as a whole and one component at a time, directories
included: once built and published, a directory name is a URL segment. (A file named
explicitly is matched by its file name.) A path is matched as written and with "-", "_",
"." and "/" read as spaces, so a slug such as zephyr-moss/ matches the entry "Zephyr Moss".
A printed path has every matched span masked as [#K]; overlapping matches are merged, so no
tail of a longer match is left showing. Masking runs on exactly the strings the hits were
computed on (the PATH argument is printed in front of them, masked on its own), so an
anchored or look-behind entry is masked where it matched. It fails closed: if a hit leaves
nothing masked, or the masked name still matches an entry, the whole name prints as [#K].

What is scanned: every PATH given. A file named explicitly is always scanned. A directory is
walked recursively, and a walked file is scanned when its suffix is a known text type
(TEXT_SUFFIXES: .md .html .txt .json .js .css .svg .xml .mmd .astro .tsx .ts and their
neighbours, .bib .ipynb .rst .sh .cfg .ini among them) or, whatever its name, when it looks
like text: its first 8 KiB hold no NUL byte and decode as UTF-8, or it starts with a UTF-16
or UTF-32 byte-order mark. So a NOTES, CNAME or Makefile is scanned too. Any other walked
file is binary, and only its printable runs are read, as `strings` reads them (ASCII,
UTF-16LE or UTF-16BE, six characters or more, BINARY_RUN_MIN): that is where uncompressed
metadata sits (PNG tEXt/iTXt chunks, a PDF Info dictionary, XMP). A hit there is reported at
line 0, like a hit in the path; the two are told apart by the printed path, which is masked
only when the name itself hit. Two limits are kept and asserted in test_checks.py:
compressed content (PNG image data, a PDF FlateDecode stream, a woff2 font) cannot be read
at all, and a run shorter than six characters standing alone between non-printable bytes is
not read (the floor keeps random bytes from reading as words). A file named explicitly is
read as text whatever it is, and as binary as well when it is not text.

The walk skips .git, node_modules and __pycache__, and a directory named .venv or venv that
is a Python virtual environment (it holds pyvenv.cfg): a local environment is never
published. A directory named build is NOT skipped: build output is what gets published. A
directory reached through a symbolic link is followed, as a site build or a wiki publish
follows it; a link back to a directory the walk is already inside is not entered again (its
content is scanned there) but its name is still checked. A directory or file the walk cannot
read is exit 2, never a skipped one.

Each file is scanned in several renderings, all of which keep its line numbers:

    the raw text, and its NFC form;
    every rendering below also with "-" and "_" read as spaces, so a phrase written as a
        slug inside a file (a URL, a link target, an #anchor, an id, class or href value)
        is caught as it is in a path;
    markup (HTML, SVG, XML, Astro, JSX, TSX, MDX, Markdown, Mermaid): tags removed and
        entities decoded, so a phrase split by an inline tag (a Mermaid <br/> included) is
        caught (a newline entity reads as a space, so no line number shifts); Mermaid's
        own #name; and #NNN; entities are decoded too;
    JSX, TSX, Astro, MDX and Svelte: also with string-literal expressions unwrapped, so
        {"Zephyr"} Moss and Zephyr{" "} on one line and Moss on the next read as the text
        they render;
    Markdown and MDX: also emphasis, code, strike-through and link punctuation, link
        targets and blockquote markers read as spaces, so **Zephyr** Moss, Zephyr [Moss](x)
        and a phrase wrapped inside a blockquote are caught;
    JS, TS, JSX, TSX, Astro, MDX, JSON, notebooks and Python: string escapes decoded
        (\\xNN, \\uXXXX, \\u{X...}, \\UXXXXXXXX, \\N{NAME} and octal);
    CSS: CSS escapes decoded.

Exit 0 = clean. Exit 1 = at least one hit. Exit 2 = the check could not run: the denylist is
missing, unreadable, empty or holds an invalid regex; a PATH does not exist, or a file or
directory under it cannot be read; or nothing was scanned (a directory PATH that holds no
text file, such as an empty or not-yet-built output directory; binary files alone do not
count). A gate that silently passes
when its list is missing, or when there is nothing to look at, guards nothing, so neither is
ever exit 0.

This module also holds the text helpers that leak_check.py and check_copy.py share with it
(NFC normalisation, the Turkish-letter test, string-escape decoding and the reading of
printable runs in binary content), so the three checks agree on what they match.

Usage:
    python3 tools/publish/check_disclosure.py --denylist ../companion/denylist.txt docs/research website/dist
    python3 tools/publish/check_disclosure.py --denylist-env DISCLOSURE_DENYLIST build/publish/wiki

Stdlib only.
"""

from __future__ import annotations

import argparse
import codecs
import html
import os
import re
import sys
import unicodedata
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Set, Tuple, Union

TEXT_SUFFIXES = {
    # the required set
    ".md", ".html", ".txt", ".json", ".js", ".css", ".svg", ".xml", ".mmd", ".astro",
    ".tsx", ".ts",
    # neighbours that are published or staged the same way
    ".htm", ".mjs", ".cjs", ".mts", ".cts", ".jsx", ".mdx", ".vue", ".svelte", ".map",
    ".webmanifest", ".yml", ".yaml", ".toml", ".tex", ".bib", ".csv", ".tsv", ".cff",
    ".py", ".ipynb", ".rst", ".sh", ".bash", ".zsh", ".cfg", ".ini", ".conf", ".scss",
    ".less", ".log", ".env",
}
MARKUP_SUFFIXES = {".html", ".htm", ".svg", ".xml", ".astro", ".jsx", ".tsx", ".mdx", ".md",
                   ".vue", ".svelte", ".mmd"}
MARKDOWN_SUFFIXES = {".md", ".mdx"}
MERMAID_SUFFIXES = {".mmd"}
JSX_SUFFIXES = {".astro", ".jsx", ".tsx", ".mdx", ".svelte"}
ESCAPED_SUFFIXES = {".js", ".mjs", ".cjs", ".mts", ".cts", ".ts", ".tsx", ".jsx", ".astro",
                    ".mdx", ".vue", ".svelte", ".json", ".map", ".webmanifest", ".ipynb",
                    ".py"}
CSS_SUFFIXES = {".css", ".scss", ".less"}
SKIP_DIRS = {".git", "node_modules", "__pycache__"}
# skipped only when it is a virtual environment (holds pyvenv.cfg); see the module docstring
VENV_DIRS = {".venv", "venv"}
SNIFF_BYTES = 8192

PLAIN_FLAGS = re.IGNORECASE | re.MULTILINE
REGEX_FLAGS = re.MULTILINE


# ─────────────────────────────────────────────────────────────────────────────
# text helpers shared by the publish checks
# ─────────────────────────────────────────────────────────────────────────────

def nfc(text: str) -> str:
    """Unicode NFC. It never composes across a newline, so line numbers survive it."""
    return unicodedata.normalize("NFC", text)


# Escaped on purpose: this file sits on an English-only path, and a literal letter in it
# would trip the very rule it defines. The same twelve letters as leak_check and check_copy.
TURKISH_RE = re.compile("[\u00e7\u011f\u0131\u00f6\u015f\u00fc\u00c7\u011e\u0130\u00d6\u015e\u00dc]")
# What NFC leaves decomposed: a breve, dot above, diaeresis or cedilla on an ASCII letter
# that has no precomposed form (a dotted small i is the common one: it is what lower-casing
# a capital dotted I produces).
TURKISH_MARK_RE = re.compile("(?<=[A-Za-z])[\u0306\u0307\u0308\u0327]")


def turkish_letter(text: str) -> Optional[str]:
    """The first Turkish letter in `text` as 'U+XXXX', or None. Compared in NFC, so a letter
    written as a base letter plus a combining mark is found as well."""
    t = nfc(text)
    m = TURKISH_RE.search(t) or TURKISH_MARK_RE.search(t)
    return f"U+{ord(m.group(0)):04X}" if m else None


_BOMS = (
    (codecs.BOM_UTF32_LE, "utf-32"), (codecs.BOM_UTF32_BE, "utf-32"),   # before UTF-16
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF16_LE, "utf-16"), (codecs.BOM_UTF16_BE, "utf-16"),
)


def _utf16_guess(head: bytes) -> Optional[str]:
    """'utf-16-le' or 'utf-16-be' for BOM-less UTF-16 text (mostly ASCII, so every other
    byte is NUL), else None."""
    if len(head) < 8:
        return None
    even, odd = head[0::2], head[1::2]
    zero_even, zero_odd = even.count(0) / len(even), odd.count(0) / len(odd)
    if zero_odd > 0.6 and zero_even < 0.1:
        return "utf-16-le"
    if zero_even > 0.6 and zero_odd < 0.1:
        return "utf-16-be"
    return None


def text_encoding(data: bytes) -> Optional[str]:
    """The encoding `data` is text in, judged on its first block, or None for binary."""
    head = data[:SNIFF_BYTES]
    for bom, enc in _BOMS:
        if head.startswith(bom):
            return enc
    guess = _utf16_guess(head)
    if guess:
        return guess
    if b"\x00" in head:
        return None
    try:
        codecs.getincrementaldecoder("utf-8")().decode(head, final=False)
    except UnicodeDecodeError:
        return None
    return "utf-8"


def decode_bytes(data: bytes) -> str:
    """Text from bytes: a byte-order mark or a UTF-16 pattern picks the codec, UTF-8
    otherwise. Undecodable bytes become U+FFFD; nothing raises."""
    enc = text_encoding(data) or "utf-8"
    return data.decode(enc, errors="replace")


# Printable runs in binary content, as `strings` reads them (ASCII, UTF-16LE, UTF-16BE), at
# least BINARY_RUN_MIN characters long. Uncompressed metadata (PNG tEXt/iTXt chunks, a PDF
# Info dictionary, XMP) is read this way. The floor keeps random bytes from reading as
# words; its cost is that a run shorter than the floor, standing alone between
# non-printable bytes, is not read. Shared with leak_check.py, so both read binary alike.
BINARY_RUN_MIN = 6
_ASCII_RUN_RE = re.compile(rb"[\t\x20-\x7e]{%d,}" % BINARY_RUN_MIN)
_U16LE_RUN_RE = re.compile(rb"(?:[\t\x20-\x7e]\x00){%d,}" % BINARY_RUN_MIN)
_U16BE_RUN_RE = re.compile(rb"(?:\x00[\t\x20-\x7e]){%d,}" % BINARY_RUN_MIN)


def binary_strings(data: bytes) -> List[str]:
    """Every printable run in `data` (see BINARY_RUN_MIN), decoded."""
    out = [m.group(0).decode("ascii") for m in _ASCII_RUN_RE.finditer(data)]
    out += [m.group(0).decode("utf-16-le") for m in _U16LE_RUN_RE.finditer(data)]
    out += [m.group(0).decode("utf-16-be") for m in _U16BE_RUN_RE.finditer(data)]
    return out


# ─────────────────────────────────────────────────────────────────────────────
# the denylist
# ─────────────────────────────────────────────────────────────────────────────

class DenylistError(Exception):
    """The denylist could not be used. Always exit 2, never a finding and never clean."""


class NothingToScan(Exception):
    """A PATH yielded no file to scan. Exit 2: an empty directory is not a clean one."""


class Unreadable(Exception):
    """A file or directory under a PATH could not be read. Exit 2: content the walk could
    not read is never reported as clean. Carries the path and the name below its PATH, so
    the caller can print it masked exactly as a hit's path is."""

    def __init__(self, path: Path, name: str, reason: str):
        super().__init__(reason)
        self.path = path
        self.name = name
        self.reason = reason


@dataclass(frozen=True)
class Entry:
    index: int            # 1-based, counting entries only
    pattern: "re.Pattern[str]"


@dataclass(frozen=True)
class Hit:
    path: str             # already masked
    line: int
    index: int

    def render(self) -> str:
        return f"{self.path}:{self.line}: private term #{self.index}"


# What separates the words of a plain entry, in the entry and in the text alike: whitespace
# (a line break included), "-", "_", and the Unicode hyphens and dashes U+2010..U+2015. An
# entry is split on the same class it is matched with, so the normalisation is two-sided:
# "zephyr-moss", "zephyr_moss" and "zephyr moss" are one entry, whichever way it is written.
_SEP_CLASS = "[\\s\\-_\u2010-\u2015]"
_SEP_SPLIT_RE = re.compile(_SEP_CLASS + "+")
# A Turkish letter in a plain entry also matches its ASCII letter, so the transliterated
# spelling (the one the LANGUAGE rule does not block) is caught. Written as escapes, as above.
_ASCII_FOLD = {
    "\u00e7": "c", "\u00c7": "c", "\u011f": "g", "\u011e": "g", "\u0131": "i", "\u0130": "i",
    "\u00f6": "o", "\u00d6": "o", "\u015f": "s", "\u015e": "s", "\u00fc": "u", "\u00dc": "u",
}
# a combining mark NFC leaves decomposed (the dot of a dotted small i): optional when matched
_COMBINING_MARKS = "\u0306\u0307\u0308\u0327"


def _plain_word(word: str) -> str:
    out = []
    for ch in word:
        if ch in _ASCII_FOLD:
            out.append("[" + re.escape(ch) + _ASCII_FOLD[ch] + "]")
        elif ch in _COMBINING_MARKS:
            out.append("(?:" + re.escape(ch) + ")?")
        else:
            out.append(re.escape(ch))
    return "".join(out)


def _plain_pattern(phrase: str) -> "re.Pattern[str]":
    """A plain entry: case-insensitive, whole words, the words separated by any run of
    _SEP_CLASS, each Turkish letter also matching its ASCII letter. Raises DenylistError for
    an entry with no word in it (it would match nothing, silently)."""
    words = [w for w in _SEP_SPLIT_RE.split(nfc(phrase)) if w]
    if not words:
        raise DenylistError("a plain denylist entry holds no word")
    body = (_SEP_CLASS + "+").join(_plain_word(w) for w in words)
    return re.compile(r"(?<!\w)" + body + r"(?!\w)", PLAIN_FLAGS)


def parse_denylist(text: str) -> List[Entry]:
    """Parse the denylist text. Raises DenylistError; the message never quotes an entry."""
    entries: List[Entry] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        index = len(entries) + 1
        if line.startswith("re:"):
            source = nfc(line[3:])
            if not source.strip():
                raise DenylistError(f"denylist entry #{index} is an empty regex")
            try:
                pattern = re.compile(source, REGEX_FLAGS)
            except re.error:
                raise DenylistError(f"denylist entry #{index} is not a valid regex") from None
            if pattern.search("") is not None:
                raise DenylistError(
                    f"denylist entry #{index} matches the empty string, so it would match "
                    f"everywhere")
        else:
            try:
                pattern = _plain_pattern(line)
            except DenylistError:
                raise DenylistError(f"denylist entry #{index} holds no word (only separators)") \
                    from None
        entries.append(Entry(index, pattern))
    if not entries:
        raise DenylistError("the denylist has no entries (only comments or blank lines)")
    return entries


def load_denylist(path: Optional[str] = None, env: Optional[str] = None) -> List[Entry]:
    """Load from a file, or from an environment variable (the CI secret)."""
    if env is not None:
        text = os.environ.get(env)
        if text is None:
            raise DenylistError(f"environment variable {env} is not set")
        if not text.strip():
            raise DenylistError(f"environment variable {env} is empty")
        return parse_denylist(text)
    if path is None:
        raise DenylistError("no denylist given")
    p = Path(path)
    if not p.is_file():
        raise DenylistError(f"denylist file not found: {path}")
    try:
        text = p.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as e:
        raise DenylistError(f"denylist file unreadable: {path} ({type(e).__name__})") from None
    return parse_denylist(text)


# ─────────────────────────────────────────────────────────────────────────────
# renderings
# ─────────────────────────────────────────────────────────────────────────────

_TAG_RE = re.compile(r"<[^<>]*>")
# the character references html.unescape decodes (the html module's own pattern)
_CHARREF_RE = re.compile(r"&(#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[^\t\n\f <&#;]{1,32};?)")
_MD_TARGET_RE = re.compile(r"\]\((?:[^()\n]|\([^()\n]*\))*\)")
_MD_QUOTE_RE = re.compile(r"^[ \t]*(?:>[ \t]?)+", re.MULTILINE)
_MD_PUNCT_RE = re.compile(r"[*_`~\[\]\\]")
_ESCAPE_RE = re.compile(
    r"\\(?:u\{([0-9a-fA-F]{1,6})\}|u([0-9a-fA-F]{4})|U([0-9a-fA-F]{8})|x([0-9a-fA-F]{2})"
    r"|N\{([A-Za-z0-9 \-]{1,80})\}|([0-7]{1,3}))")
_CSS_ESCAPE_RE = re.compile(r"\\(?:([0-9a-fA-F]{1,6})[ \t]?|([^0-9a-fA-F\r\n]))")


def _unescape_keep_lines(text: str) -> str:
    """html.unescape, one reference at a time, with a decoded newline or carriage return
    read as a space: '&#10;' must not add a line."""
    def one(m: "re.Match[str]") -> str:
        return html.unescape(m.group(0)).replace("\r", " ").replace("\n", " ")
    return _CHARREF_RE.sub(one, text)


def _strip_markup(text: str) -> str:
    """Tags become a space; entities are decoded. Newlines are kept in order, so a line
    number computed on the result is the line number in the original."""
    def tag(m: "re.Match[str]") -> str:
        return " " + "\n" * m.group(0).count("\n")
    return _unescape_keep_lines(_TAG_RE.sub(tag, text))


def _strip_markdown(text: str) -> str:
    """Markdown inline syntax read as spaces: link targets, blockquote markers, and the
    emphasis, code, strike-through, link and escape punctuation. Newlines are kept."""
    text = _MD_TARGET_RE.sub(" ", text)
    text = _MD_QUOTE_RE.sub(lambda m: " " * len(m.group(0)), text)
    return _MD_PUNCT_RE.sub(" ", text)


def _decode_escapes(text: str) -> str:
    """String escapes of JS/TS, JSON and Python decoded. An escape that decodes to a line
    break, or does not decode, is left as written."""
    def esc(m: "re.Match[str]") -> str:
        hexes = m.group(1) or m.group(2) or m.group(3) or m.group(4)
        try:
            if hexes is not None:
                ch = chr(int(hexes, 16))
            elif m.group(5) is not None:
                ch = unicodedata.lookup(m.group(5))
            else:
                ch = chr(int(m.group(6), 8))
        except (ValueError, KeyError, OverflowError):
            return m.group(0)
        return m.group(0) if ch in ("\r", "\n") else ch
    return _ESCAPE_RE.sub(esc, text)


def decode_escapes(text: str) -> str:
    """The public name of _decode_escapes; check_copy.py reads the same escapes with it."""
    return _decode_escapes(text)


def _decode_js_escapes(text: str) -> str:
    """Kept for callers of the earlier name."""
    return _decode_escapes(text)


def _decode_css_escapes(text: str) -> str:
    def esc(m: "re.Match[str]") -> str:
        if m.group(2) is not None:
            return m.group(2)
        try:
            ch = chr(int(m.group(1), 16))
        except (ValueError, OverflowError):
            return m.group(0)
        return m.group(0) if ch in ("\r", "\n") else ch
    return _CSS_ESCAPE_RE.sub(esc, text)


# A JSX/Astro expression that is only a string literal: {" "}, {"text"}, {'text'}, {`text`}
# (a template literal with no ${...} in it). The literal holds no quote of its own kind, no
# backslash and no brace, and stays on one line; the braces may have whitespace, newlines
# included, around it.
_JSX_STRING_RE = re.compile(
    r"\{\s*(?:\"([^\"\\{}\n]*)\"|'([^'\\{}\n]*)'|`([^`\\{}$\n]*)`)\s*\}")
# Mermaid's entity syntax: #quot; #9829; (a CSS colour such as #fff; is not an entity and
# is left as written)
_MERMAID_ENTITY_RE = re.compile(r"#([0-9]{1,7}|[A-Za-z][A-Za-z0-9]{1,31});")
_DASH_RE = re.compile(r"[-_]")


def _unwrap_jsx(text: str) -> str:
    """Every string-literal expression replaced by the text it renders, exactly (no padding:
    Zeph{"yr"} renders one word). Newlines inside the braces are kept, after the text, so
    every later line keeps its number."""
    def one(m: "re.Match[str]") -> str:
        inner = next(g for g in m.groups() if g is not None)
        return inner + "\n" * m.group(0).count("\n")
    return _JSX_STRING_RE.sub(one, text)


def _decode_mermaid_entities(text: str) -> str:
    """Mermaid's #name; and #NNN; entities decoded; one that decodes to a line break reads
    as a space, and one that is not an entity is left as written."""
    def one(m: "re.Match[str]") -> str:
        body = m.group(1)
        ref = "&#" + body + ";" if body.isdigit() else "&" + body + ";"
        try:
            out = html.unescape(ref)
        except (ValueError, OverflowError):
            return m.group(0)
        if out == ref:
            return m.group(0)
        return out.replace("\r", " ").replace("\n", " ")
    return _MERMAID_ENTITY_RE.sub(one, text)


def _dashes_as_spaces(text: str) -> str:
    """'-' and '_' read as spaces (same length), so a slug in a file reads as a phrase."""
    return _DASH_RE.sub(" ", text)


def markup_forms(text: str, suffix: str) -> List[str]:
    """The markup renderings of `text` (empty for a suffix that is not markup): tags removed
    and entities decoded; for JSX-like files also with string-literal expressions unwrapped
    first; for Mermaid also with its own entities decoded; for Markdown also with inline
    syntax read as spaces. Every one keeps the line count of `text`. Shared with
    check_copy.py, so the two read a page the same way."""
    if suffix not in MARKUP_SUFFIXES:
        return []
    bases = [text]
    if suffix in JSX_SUFFIXES:
        unwrapped = _unwrap_jsx(text)
        if unwrapped != text:
            bases.append(unwrapped)
    out: List[str] = []
    for base in bases:
        stripped = _strip_markup(base)
        if suffix in MERMAID_SUFFIXES:
            stripped = _decode_mermaid_entities(stripped)
        out.append(stripped)
        if suffix in MARKDOWN_SUFFIXES:
            out.append(_strip_markdown(stripped))
    return out


def variants(text: str, suffix: str) -> List[str]:
    """The renderings of one file that are scanned, de-duplicated. Every one has the same
    number of lines as `text`."""
    forms = [text]
    forms += markup_forms(text, suffix)
    if suffix in ESCAPED_SUFFIXES:
        forms += [_decode_escapes(f) for f in list(forms)]
    if suffix in CSS_SUFFIXES:
        forms.append(_decode_css_escapes(text))
    forms += [_dashes_as_spaces(f) for f in list(forms)]
    forms += [nfc(f) for f in list(forms)]
    out: List[str] = []
    seen: Set[str] = set()
    for f in forms:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# matching
# ─────────────────────────────────────────────────────────────────────────────

_PATH_SEP_RE = re.compile(r"[-_./\\]")


def find_hits(entries: Sequence[Entry], text: str) -> List[Tuple[int, int]]:
    """(line, entry index) pairs, deduplicated, in order."""
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    found: Set[Tuple[int, int]] = set()
    for e in entries:
        for m in e.pattern.finditer(text):
            if m.end() == m.start():
                continue
            found.add((bisect_right(starts, m.start()), e.index))
    return sorted(found)


def matching_indices(entries: Sequence[Entry], text: str) -> List[int]:
    """The entry numbers that match anywhere in `text`: as written, with '-' and '_' read as
    spaces, and in NFC."""
    found: Set[int] = set()
    for form in variants(text, ""):
        found.update(index for _, index in find_hits(entries, form))
    return sorted(found)


def path_forms(path: str) -> List[str]:
    """A path as matched: NFC, and the same with - _ . / and backslash read as spaces (so a
    slug matches a phrase). Both forms have the same length."""
    t = nfc(path)
    slug = _PATH_SEP_RE.sub(" ", t)
    return [t] if slug == t else [t, slug]


def _path_spans(entries: Sequence[Entry], path: str) -> List[Tuple[int, int, int]]:
    """(start, end, entry index) of every match in `path` (NFC offsets): over the whole
    path and over each '/'-separated component on its own, in every path form. A component
    is matched alone so that an anchored entry (^, \\A) or a look-behind reads a directory
    name as it reads a URL segment."""
    t = nfc(path)
    pieces: List[Tuple[int, str]] = [(0, t)]
    if "/" in t:
        pos = 0
        for comp in t.split("/"):
            if comp:
                pieces.append((pos, comp))
            pos += len(comp) + 1
    spans: List[Tuple[int, int, int]] = []
    for offset, piece in pieces:
        for form in path_forms(piece):
            for e in entries:
                for m in e.pattern.finditer(form):
                    if m.end() > m.start():
                        spans.append((offset + m.start(), offset + m.end(), e.index))
    return spans


def path_indices(entries: Sequence[Entry], path: str) -> List[int]:
    """The entry numbers that match a path, in any of its forms, as a whole or in any one
    component."""
    return sorted({index for _, _, index in _path_spans(entries, path)})


def mask(entries: Sequence[Entry], text: str) -> str:
    """`text` (in NFC) with every denylisted span replaced by [#K], so a path can be printed
    safely. Spans are exactly those path_indices() finds on the same string (slug forms and
    single components included), and overlapping spans are merged."""
    t = nfc(text)
    spans = _path_spans(entries, text)
    if not spans:
        return t
    spans.sort()
    merged: List[List[int]] = []
    for start, end, index in spans:
        if merged and start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end, index])
    out, pos = [], 0
    for start, end, index in merged:
        out.append(t[pos:start])
        out.append(f"[#{index}]")
        pos = end
    out.append(t[pos:])
    return "".join(out)


_MASK_TOKEN_RE = re.compile(r"\[#\d+\]")


def _residue(entries: Sequence[Entry], shown: str) -> List[int]:
    """The entries that still match a masked string, outside its [#K] tokens (each read as
    blanks of its length, so a match the masking itself created, by changing what precedes
    or follows a span, is found; one inside a token is not)."""
    return path_indices(entries, _MASK_TOKEN_RE.sub(lambda m: " " * len(m.group(0)), shown))


def mask_name(entries: Sequence[Entry], name: str) -> str:
    """`name` masked for printing, failing closed: when `name` matches an entry but masking
    changed nothing, or the masked text still matches one, the whole name becomes [#K]."""
    hit = path_indices(entries, name)
    masked = mask(entries, name)
    if not hit:
        return masked
    if masked == nfc(name) or _residue(entries, masked):
        return f"[#{hit[0]}]"
    return masked


def display_path(entries: Sequence[Entry], full: str, name: str) -> str:
    """The printable form of `full`, whose last part is `name` (the string a path hit is
    computed on): the prefix (the PATH argument) masked on its own, then `name` masked by
    mask_name(), so the mask is computed on the same string as the hit."""
    full_n, name_n = nfc(full), nfc(name)
    if not name_n:
        shown = mask(entries, full_n)
    elif full_n == name_n:
        shown = mask_name(entries, name_n)
    elif full_n.endswith("/" + name_n):
        prefix = full_n[:len(full_n) - len(name_n)]
        shown = mask(entries, prefix) + mask_name(entries, name_n)
    else:
        # cannot happen for a path this module built; never print a hit unmasked if it does
        hit = path_indices(entries, name_n)
        shown = f"[#{hit[0]}]" if hit else mask(entries, full_n)
    # a match that spans the prefix and the name is masked too; failing that, nothing shows
    if _residue(entries, shown):
        shown = mask(entries, shown)
        rest = _residue(entries, shown)
        if rest:
            shown = f"[#{rest[0]}]"
    return shown


# ─────────────────────────────────────────────────────────────────────────────
# scanning
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Target:
    path: Path
    name: str             # what is matched as a path: below the PATH argument, or the name
    content: bool = True  # False: a link back into the walk; only its name is checked
    binary: bool = False  # True: content that is not text; its printable runs are read
    explicit: bool = False  # named as a PATH: always read as text too, and always counted


def is_text_file(path: Path) -> bool:
    """A known text suffix, or content that looks like text. Raises OSError."""
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    with open(path, "rb") as fh:
        head = fh.read(SNIFF_BYTES)
    return text_encoding(head) is not None


def _is_venv(path: str) -> bool:
    return os.path.isfile(os.path.join(path, "pyvenv.cfg"))


def _walk_dir(p: Path) -> Iterator[Target]:
    """Every target under the directory `p`. Directories reached through a link are
    followed; a link back to a directory the walk is inside is yielded as a name-only
    target. Raises Unreadable for a directory or file that cannot be read."""
    top = str(p)

    def rel(full: str) -> str:
        r = os.path.relpath(full, top)
        return "" if r == "." else Path(r).as_posix()

    def fail(err: OSError) -> None:
        where = err.filename if isinstance(err.filename, str) else top
        raise Unreadable(Path(where), rel(where), type(err).__name__)

    # the real paths of the directories above each walked directory, itself included:
    # a link to one of them is a loop
    chains = {top: frozenset({os.path.realpath(top)})}
    for dirpath, dirnames, filenames in os.walk(top, onerror=fail, followlinks=True):
        chain = chains.get(dirpath) or frozenset({os.path.realpath(dirpath)})
        keep = []
        for d in sorted(dirnames):
            full = os.path.join(dirpath, d)
            if d in SKIP_DIRS or (d in VENV_DIRS and _is_venv(full)):
                continue
            real = os.path.realpath(full)
            if real in chain:
                yield Target(Path(full), rel(full), content=False)
                continue
            chains[full] = chain | {real}
            keep.append(d)
        dirnames[:] = keep
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            try:
                text = is_text_file(Path(full))
            except OSError as e:
                raise Unreadable(Path(full), rel(full), type(e).__name__) from None
            yield Target(Path(full), rel(full), binary=not text)


def _counts_as_text(t: Target) -> bool:
    """A target that makes a PATH 'not empty': content read as text (every file named
    explicitly is). A directory holding only binary files is still nothing to scan: an
    unbuilt or half-built site can hold only images."""
    return t.content and (t.explicit or not t.binary)


def iter_targets(paths: Iterable[str]) -> Iterator[Target]:
    """Explicit files always; directories walked. Raises FileNotFoundError for a missing
    PATH, NothingToScan for a directory that yields no text file, and Unreadable for a
    directory or file under a PATH that cannot be read."""
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            try:
                text = is_text_file(p)
            except OSError as e:
                raise Unreadable(p, p.name, type(e).__name__) from None
            # named explicitly: read as text whatever it is, and also as binary if it is not
            yield Target(p, p.name, binary=not text, explicit=True)
        elif p.is_dir():
            n = 0
            for t in _walk_dir(p):
                n += _counts_as_text(t)
                yield t
            if n == 0:
                raise NothingToScan(raw)
        else:
            raise FileNotFoundError(raw)


def iter_files(paths: Iterable[str]) -> Iterator[Path]:
    """The files iter_targets yields with content, as paths (binary ones included)."""
    for t in iter_targets(paths):
        if t.content:
            yield t.path


def scan_file(entries: Sequence[Entry], target: Union[Target, Path]) -> List[Hit]:
    """Hits in one target's name (line 0) and content. A walked binary file's printable runs
    are reported at line 0 too (its name is then printed unmasked unless the name itself
    hit); a file named explicitly is read as text as well. Raises Unreadable."""
    if isinstance(target, Path):
        target = Target(target, target.name)
    path = target.path
    shown = display_path(entries, path.as_posix(), target.name)
    hits: Set[Tuple[int, int]] = set()
    for index in path_indices(entries, target.name):
        hits.add((0, index))          # line 0: the hit is in the path
    if target.content:
        try:
            data = path.read_bytes()
        except OSError as e:
            raise Unreadable(path, target.name, type(e).__name__) from None
        if target.binary:
            for run in binary_strings(data):
                hits.update((0, index) for index in matching_indices(entries, run))
        if not target.binary or target.explicit:
            text = decode_bytes(data)
            for variant in variants(text, path.suffix.lower()):
                hits.update(find_hits(entries, variant))
    return [Hit(shown, line, index) for line, index in sorted(hits)]


def scan(entries: Sequence[Entry], paths: Sequence[str]) -> Tuple[List[Hit], int, int]:
    """(hits, text files scanned, binary files read as printable runs). Raises
    FileNotFoundError, NothingToScan and Unreadable."""
    out: List[Hit] = []
    n_text = n_binary = 0
    for t in iter_targets(paths):
        n_text += _counts_as_text(t)
        n_binary += t.content and t.binary and not t.explicit
        out.extend(scan_file(entries, t))
    if n_text == 0:
        raise NothingToScan(" ".join(paths))
    return out, n_text, n_binary


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--denylist", metavar="FILE", help="the private denylist file")
    src.add_argument("--denylist-env", metavar="NAME",
                     help="read the denylist from this environment variable (CI secret)")
    ap.add_argument("--quiet", action="store_true", help="hits only, no summary line")
    ap.add_argument("paths", nargs="+", metavar="PATH", help="files or directories to scan")
    args = ap.parse_args(argv)

    try:
        entries = load_denylist(args.denylist, args.denylist_env)
    except DenylistError as e:
        print(f"check_disclosure: cannot run: {e}", file=sys.stderr)
        return 2

    try:
        hits, scanned, binaries = scan(entries, args.paths)
    except FileNotFoundError as e:
        print(f"check_disclosure: cannot run: path not found: {mask(entries, str(e))}",
              file=sys.stderr)
        return 2
    except NothingToScan as e:
        print(f"check_disclosure: cannot run: nothing to scan in {mask(entries, str(e))}: "
              f"no text file there (an empty or unbuilt directory is never clean)",
              file=sys.stderr)
        return 2
    except Unreadable as e:
        shown = display_path(entries, e.path.as_posix(), e.name)
        print(f"check_disclosure: cannot run: cannot read {shown} ({e.reason}); content "
              f"the scan could not read is never reported as clean", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"check_disclosure: cannot run: unreadable file ({type(e).__name__})",
              file=sys.stderr)
        return 2

    for h in hits:
        print(h.render())
    if not args.quiet:
        files_hit = len({h.path for h in hits})
        print(f"check_disclosure: {len(hits)} hit(s) in {files_hit} file(s); "
              f"{scanned} text file(s) scanned and {binaries} binary file(s) read as "
              f"printable runs, against {len(entries)} entr"
              f"{'y' if len(entries) == 1 else 'ies'}", file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
