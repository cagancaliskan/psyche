#!/usr/bin/env python3
"""blog.py — the posts of the docs site's blog: found in a commit, read, validated and ordered.

A post is a folder under docs/blog/ of the repository: docs/blog/<slug>/index.md, with its
pictures beside it. The folder name is the post's address, /psyche/blog/<slug>/. docs/blog/README.md
is the authoring guide and is not a post. tools/publish/stage.py stages the posts that are not
drafts, the way it stages the pages of docs/publish.json: read from a COMMIT through
core.published_text, so the same guard applies (never_publish, the quarantine lists, the
ledger:ignore-file pragma, tracked in the commit, not modified on disk), and media read from the
commit as bytes, never from the disk. A post carries its own title, date and description in a
front matter block; the manifest lists no post.

Layout. Under docs/blog/ only README.md may stand directly, and every other entry is a folder
named like a slug (lower-case words joined by single hyphens, at most 80 characters). A post
folder holds index.md and media files, nothing else and no subfolder. A media file has the
extension png, jpg, jpeg, webp, avif, gif or svg (in any case), a name of letters, digits, dot,
underscore, tilde and hyphen that starts with a letter, digit, underscore or tilde (the CMS
slugifies an upload's name and may keep those), and at most 4 MiB. The folder name `index` is
reserved: it would collide with the blog's own index route. So are build, dist and venv, the
directory names the guard skips (reserved_slugs): a post there would pass every rule here and
then be refused when staged. A slug and a name are matched whole, so a trailing line break is no
part of a valid one, and two names in one folder that differ only in case are refused, because a
case-insensitive file system holds them as one file. Anything else is refused and named: a stray
file would otherwise be staged as, or silently left out of, the site.

Front matter. The file is UTF-8 without a byte-order mark. The block between the first line
`---` and the next line `---` is read by a parser of its own, because the standard library has
no YAML reader and a library is not allowed here. The parser accepts exactly the shapes that the
CMS writes and a person is likely to write, and refuses everything else with the line number, so
a post never means two things to two readers:

    key: "double quoted"      the escapes \\" \\\\ \\/ \\n \\t and \\uXXXX
    key: 'single quoted'      '' for a quote
    key: plain text           one line, no leading quote, bracket, brace or any of & * ! | > % @,
                              no ' #' and no ': ', not one of null ~ yes no on off, not a number
                              (12, 0x1F, 1e3, .inf, .nan), not a lone - ? or :, and not a date
                              or a time as a YAML 1.1 reader takes one (2026-11-04, 2026-11-04 10:30:00),
                              except that a plain day YYYY-MM-DD is read for `date` and `updated`
    key: true | false         lower-case only; True, FALSE and the like are refused
    key: []  /  ["a", "b"]  /  [a, b]        a flow list of scalars, on one line
    key:                      followed by lines "  - item" or "- item" (a block list, every
                              item at one indentation)

No comment, anchor, tag, multi-line scalar, nested mapping or repeated key. Blank lines are
skipped. The keys are an allowlist (FRONT_KEYS); a key that is not on it is refused, so a field
cannot be added by accident. The values are checked against the rules in validate_front:
the title is one line of 1 to 120 characters, the date a real calendar day, the description
core.description_problem's one plain sentence of 120 to 160 characters that no page of the
manifest and no other post repeats, the tags a list of at most four distinct names from TAGS,
the author 1 to 80 characters (CITATION.cff's first author when absent), `updated` a day not
before `date`, and `draft` a boolean. The title and the author hold no < or >, which the page
head would carry as markup. The title, the description and the author hold no control character
and no invisible format character (Unicode categories Cc, Cf, Zl and Zp): a bidirectional
override or a zero-width space would make the text a reviewer reads differ from the text the site
shows. When a commit is staged, `date` and `updated` are no later than the day after its
committer date, read in the committer's own time zone, so that a typo in the year cannot pin a
post to the top of the blog and the feed, and the rule gives the same answer whenever and wherever
the stage runs. A draft is read only far enough to see that it is one (its other keys are not
validated): it is not staged, its pictures are not read, and the guard is not asked about it, so
an unfinished draft does not stop a stage. The body must hold no level-one ATX heading outside
code (core.scan_blocks reads block quotes, list items and HTML blocks, so `> # x` is a heading and
a `# x` inside a comment or <pre> is not), because the title comes from the front matter, and no
image without alt text: a Markdown image whose alt is empty or an <img> tag with no alt, outside
code, because the alt is one sentence saying what the picture shows. An alt made only of spaces,
character references or invisible characters counts as empty.

Raw HTML. A post becomes a page of the site's own origin, which is also the CMS's origin, and the
Markdown renderer passes raw HTML through as written. Outside fenced and indented code (code only
where every reader agrees it is), html_problem lets a post hold markup only as the elements and
attributes of HTML_ALLOWED, a link only to an http, https or mailto address or a relative one, an
image only from an https address or a relative one, every tag whole on the line where it opens,
and an HTML comment only on one line and without `--`. A declaration, a processing instruction,
an autolink to another scheme, a control character inside a tag and a tag that cannot be read are
refused. Inline code is not exempt: telling it apart from markup would mean following the inline
parser's precedence (tags and autolinks before code spans, link destinations, escapes) exactly,
and a misreading would be a way through, so HTML source belongs in a fenced code block. Markdown
link and image destinations are core.rewrite_links's to check: it refuses every scheme but http,
https and mailto when the post is staged.

SVG pictures are served from that origin too, and the CMS keeps its access token in the browser's
local storage. An SVG that could run a script there would be a way to that token, so
svg_problems refuses an SVG with a script, event attribute, foreignObject, iframe, embed, object,
handler or listener element, a javascript: URL, a DOCTYPE or ENTITY declaration, any processing
instruction (<?xml-stylesheet?> and so XSLT; the XML declaration is not one), an XML declaration
of an encoding other than UTF-8, an element or attribute of the XSLT namespace, any other element
outside the SVG namespace (an XHTML element, or the RDF metadata a drawing program writes), an
attribute of a namespace other than XLink, an xml: attribute other than xml:lang and xml:space
(xml:base would move where its links point), a
root that is not an svg element of the SVG namespace, an animation that sets an href, a src or an
event attribute, a href, xlink:href or src that is not a #fragment or a data:image/ URL of a
raster format, or CSS (a <style> element, a style attribute or any attribute value) with
@import, image-set(), expression() or a url() that is not a #fragment or such a data URL. Names
are read with namespaces, so a prefix hides nothing, and CSS is read after its comments and
escapes are undone. A raster picture is not parsed, but raster_problem holds its first bytes to
the format its extension names, so an SVG or an HTML file cannot pass as a PNG.

Order. Newest first: date descending, then `updated` descending (a post without one last), then
slug ascending. Each post's `prev` is the next older one and its `next` the next newer one.

Public functions: parse_front_matter, validate_front, body_problem, html_problem, svg_problems,
raster_problem, reserved_slugs, layout, discover, sources, order, neighbours, post_route,
link_mapping, staged_front_matter, blog_json.

Standard library only.
"""

from __future__ import annotations

import html
import json
import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple
from xml.parsers import expat

import core

BLOG_DIR = "docs/blog"
README_NAME = "README.md"
INDEX_NAME = "index.md"

# The topics a post may carry. The CMS configuration lists the same values, and a test holds the
# two lists equal; this is the one place in code that names them.
TAGS = ("project", "substrate", "cognitive-maps", "methods", "engineering", "reading", "site")
MAX_TAGS = 4

# \Z, not $: `$` also matches before a final line break, so "foo\n" would pass as a slug.
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SLUG_MAX = 80
MEDIA_EXT = ("png", "jpg", "jpeg", "webp", "avif", "gif", "svg")
MEDIA_NAME_RE = re.compile(r"^[A-Za-z0-9_~][A-Za-z0-9._~-]*\Z")
RESERVED_SLUGS = ("index",)
MEDIA_MAX = 4 * 1024 * 1024

TITLE_MAX = 120
AUTHOR_MAX = 80
# key -> required. Every key a post may carry, and nothing else.
FRONT_KEYS = {"title": True, "date": True, "description": True, "tags": False,
              "author": False, "updated": False, "draft": False}

_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]+(.*?))?[ \t]*$")
_ITEM_RE = re.compile(r"^ {0,2}-(?:[ \t]+(.*?))?[ \t]*$")
_PLAIN_BAD_START = set("'\"[]{}&*!|>%@`#,")
_PLAIN_WORDS = {"null", "~", "yes", "no", "on", "off", "y", "n"}
_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "n": "\n", "t": "\t"}
_H1_RE = re.compile(r"#(?:[ \t]|$)")
_YAML_NUMBER = re.compile(
    r"[-+]?(?:[0-9][0-9_]*|0o[0-7]+|0x[0-9a-f]+|0b[01_]+"
    r"|(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:e[-+]?[0-9]+)?|\.inf|\.nan"
    r"|[0-9]+(?::[0-5]?[0-9])+(?:\.[0-9_]*)?)", re.I)
# A plain value that a YAML 1.1 reader, such as js-yaml or PyYAML, takes for a date or a time (the
# patterns of js-yaml's timestamp type), so that the raw file means one thing to every reader. Only
# `date` and `updated` take a plain day.
_YAML_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
    r"|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[Tt]|[ \t]+)[0-9]{1,2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]*)?"
    r"(?:[ \t]*(?:Z|[-+][0-9]{1,2}(?::[0-9]{2})?))?")
_DAY_KEYS = ("date", "updated")
_BOM = chr(0xFEFF)    # a byte-order mark, written as a code point so it stays visible here
# Characters a reviewer cannot see: controls, format characters (bidirectional overrides,
# zero-width spaces, the byte-order mark) and the Unicode line and paragraph separators.
_UNSEEN = ("Cc", "Cf", "Zl", "Zp")


class Post(NamedTuple):
    """One published post. `body` is the Markdown after the front matter; `body_line` the line of
    the file where it starts; `media` the (name, bytes) pairs read from the commit."""
    slug: str
    src: str
    title: str
    date: str
    updated: Optional[str]
    description: str
    tags: List[str]
    author: str
    body: str
    body_line: int
    media: List[Tuple[str, bytes]]


def post_src(slug: str) -> str:
    return f"{BLOG_DIR}/{slug}/{INDEX_NAME}"


def post_route(manifest: dict, slug: str) -> str:
    return f"{manifest['site_base']}blog/{slug}/"


# ─────────────────────────────────────────────────────────────────────────────
# the front matter
# ─────────────────────────────────────────────────────────────────────────────

class _Bad(Exception):
    """A reason, raised inside the scalar readers and given its line number by the caller."""


def _quoted(raw: str, i: int) -> Tuple[str, int]:
    """The quoted scalar that starts at raw[i] (a quote), and the index after its closing quote."""
    q = raw[i]
    out: List[str] = []
    j = i + 1
    while j < len(raw):
        c = raw[j]
        if q == "'":
            if c == "'":
                if raw[j + 1:j + 2] == "'":
                    out.append("'")
                    j += 2
                    continue
                return "".join(out), j + 1
            out.append(c)
            j += 1
            continue
        if c == '"':
            return "".join(out), j + 1
        if c != "\\":
            out.append(c)
            j += 1
            continue
        e = raw[j + 1:j + 2]
        if e in _ESCAPES:
            out.append(_ESCAPES[e])
            j += 2
        elif e == "u":
            hexa = raw[j + 2:j + 6]
            if not re.fullmatch(r"[0-9A-Fa-f]{4}", hexa):
                raise _Bad("a \\u escape needs four hexadecimal digits")
            code = int(hexa, 16)
            if 0xD800 <= code <= 0xDFFF:
                raise _Bad("a \\u escape may not name a surrogate; write the character itself")
            out.append(chr(code))
            j += 6
        else:
            raise _Bad(f"the escape \\{e} is not supported (use \\\" \\\\ \\/ \\n \\t or \\uXXXX)")
    raise _Bad("the quoted text is not closed on this line")


def _plain(raw: str, *, in_list: bool = False, allow_day: bool = False) -> str:
    """A plain one-line scalar, checked; `in_list` also stops it at a comma or bracket, and
    `allow_day` (the value of `date` or `updated`) lets a date through to validate_front."""
    if not raw:
        raise _Bad("the value is empty")
    if raw[0] in _PLAIN_BAD_START:
        raise _Bad(f"a plain value may not start with {raw[0]!r}; put it in double quotes")
    if raw in ("-", "?", ":") or raw.startswith(("- ", "? ", ": ")):
        raise _Bad("a plain value may not be or start with an indicator; put it in double quotes")
    if " #" in raw or raw.startswith("#"):
        raise _Bad("a plain value may not hold ' #' (a comment); put it in double quotes")
    if ": " in raw or raw.endswith(":"):
        raise _Bad("a plain value may not hold ': '; put it in double quotes")
    if "\t" in raw:
        raise _Bad("a plain value may not hold a tab; put it in double quotes")
    if in_list and re.search(r"[\[\]{},]", raw):
        raise _Bad("a plain list item may not hold brackets, braces or commas; put it in double quotes")
    if raw.casefold() in _PLAIN_WORDS or raw.casefold() in ("true", "false"):
        raise _Bad(f"the plain value {raw!r} reads as null or a boolean in YAML; put it in double quotes")
    if _YAML_NUMBER.fullmatch(raw):
        raise _Bad(f"the plain value {raw!r} reads as a number in YAML; put it in double quotes")
    if not allow_day and _YAML_TIMESTAMP.fullmatch(raw):
        raise _Bad(f"the plain value {raw!r} reads as a date or a time in YAML; put it in double quotes")
    return raw


def _scalar(raw: str, *, in_list: bool = False, allow_day: bool = False) -> object:
    """One scalar of a value or of a list item: a string, or a boolean for the plain true / false."""
    raw = raw.strip()
    if not raw:
        raise _Bad("the value is empty")
    if raw[0] in "\"'":
        text, end = _quoted(raw, 0)
        if raw[end:].strip():
            raise _Bad("nothing may follow a quoted value (not even a comment)")
        return text
    if raw in ("true", "false"):
        if in_list:
            raise _Bad("a list item may not be a boolean; quote it")
        return raw == "true"
    return _plain(raw, in_list=in_list, allow_day=allow_day)


def _flow_list(raw: str) -> List[str]:
    """`[]`, `["a", "b"]` or `[a, b]` on one line: a list of string scalars."""
    s = raw.strip()
    if not s.endswith("]"):
        raise _Bad("a list written in brackets must close on the same line")
    inner = s[1:-1]
    items: List[str] = []
    i = 0

    def skip(k: int) -> int:
        while k < len(inner) and inner[k] in " \t":
            k += 1
        return k
    i = skip(0)
    if i >= len(inner):
        return items
    while True:
        i = skip(i)
        if i >= len(inner):
            raise _Bad("a list item is missing after a comma")
        if inner[i] in "\"'":
            text, i = _quoted(inner, i)
        else:
            j = i
            while j < len(inner) and inner[j] != ",":
                j += 1
            val = inner[i:j].strip()
            text = _plain(val, in_list=True)
            i = j
        items.append(text)
        i = skip(i)
        if i >= len(inner):
            return items
        if inner[i] != ",":
            raise _Bad("list items are separated by commas")
        i += 1


def parse_front_matter(text: str, src: str) -> Tuple[Dict[str, Tuple[object, int]], str, int]:
    """(fields, body, body_line) of a post's text. `fields` maps each key to (value, line); a value
    is a string, a boolean or a list of strings. `body` is the text after the closing `---` line,
    byte for byte, and `body_line` its first line number. PublishError, with the line, for a
    missing block or anything outside the subset in the module docstring."""
    if text.startswith(_BOM):
        raise core.PublishError(f"{src}:1: the file starts with a byte-order mark; save it as UTF-8 "
                                f"without one, so that its first line is `---`")
    lines = core.split_lines(text, keepends=True)
    if not lines or core.line_body(lines[0]) != "---":
        raise core.PublishError(f"{src}:1: a post starts with a front matter block: a first line "
                                f"`---`, the keys, and a closing line `---`")
    fields: Dict[str, Tuple[object, int]] = {}
    end = None
    pending: Optional[Tuple[str, int, List[str]]] = None   # a key waiting for its block list
    list_indent = -1                                         # the indentation of its first item

    def flush() -> None:
        nonlocal pending
        if pending is None:
            return
        key, kline, items = pending
        pending = None
        if not items:
            raise core.PublishError(f"{src}:{kline}: the key {key!r} has no value (write the value "
                                    f"after the colon, or a list below it)")
        fields[key] = (items, kline)

    for idx in range(1, len(lines)):
        n = idx + 1
        ln = core.line_body(lines[idx])
        if ln == "---":
            end = idx
            break
        if not ln.strip():
            continue
        try:
            if pending is not None:
                m = _ITEM_RE.match(ln)
                if m:
                    item = m.group(1)
                    indent = len(ln) - len(ln.lstrip(" "))
                    if pending[2] and indent != list_indent:
                        raise _Bad("the items of a block list must all use one indentation")
                    list_indent = indent
                    if item is None:
                        raise _Bad("a list item has no value")
                    val = _scalar(item, in_list=True)
                    if isinstance(val, bool):
                        raise _Bad("a list item may not be a boolean; quote it")
                    pending[2].append(val)           # type: ignore[arg-type]
                    continue
                flush()
            if ln[:1] in (" ", "\t"):
                raise _Bad("indented text outside a list (nested values and continued lines are not read)")
            if ln.lstrip().startswith("#"):
                raise _Bad("comments are not read; remove the line")
            m = _KEY_RE.match(ln)
            if not m:
                raise _Bad("not a `key: value` line")
            key, raw = m.group(1), m.group(2)
            if key in fields or (pending is not None and pending[0] == key):
                raise _Bad(f"the key {key!r} is given twice")
            if raw is None or raw == "":
                pending = (key, n, [])
                continue
            if raw.startswith("["):
                fields[key] = (_flow_list(raw), n)
            else:
                fields[key] = (_scalar(raw, allow_day=key in _DAY_KEYS), n)
        except _Bad as e:
            raise core.PublishError(f"{src}:{n}: {e}") from None
    flush()
    if end is None:
        raise core.PublishError(f"{src}:1: the front matter is not closed by a line `---`")
    body = "".join(lines[end + 1:])
    return fields, body, end + 2


def _unseen(value: str) -> Optional[str]:
    """The first character of `value` that a reviewer cannot see (see _UNSEEN), as U+XXXX."""
    for c in value:
        if unicodedata.category(c) in _UNSEEN:
            return f"U+{ord(c):04X}"
    return None


def _one_line(value: str, what: str, limit: int) -> Optional[str]:
    if "\n" in value or "\r" in value:
        return f"{what} must be one line with no control character"
    unseen = _unseen(value)
    if unseen:
        return (f"{what} must be one line with no control character and no invisible format "
                f"character ({unseen})")
    if value != value.strip():
        return f"{what} must have no leading or trailing space"
    if not 1 <= len(value) <= limit:
        return f"{what} must be 1 to {limit} characters, not {len(value)}"
    return None


def _no_angle(value: str, what: str) -> Optional[str]:
    """The site writes the title and the author into the page head, where a < or > would be
    markup (a title could close <title> and open a script), so neither may hold one."""
    if "<" in value or ">" in value:
        return f"{what} must hold no < or >; the page head shows it as text, so write the words out"
    return None


def validate_front(fields: Dict[str, Tuple[object, int]], src: str, default_author: str) -> dict:
    """The post's metadata as a dict (title, date, description, tags, author, updated, draft), or
    PublishError naming `src` and the line of the key at fault. `date` and `updated` are
    datetime.date; description uniqueness is checked across posts by discover."""
    def fail(key: str, why: str) -> "core.PublishError":
        return core.PublishError(f"{src}:{fields[key][1]}: {key}: {why}")

    for key in fields:
        if key not in FRONT_KEYS:
            raise core.PublishError(f"{src}:{fields[key][1]}: the key {key!r} is not one a post may "
                                    f"carry ({', '.join(FRONT_KEYS)})")
    for key, required in FRONT_KEYS.items():
        if required and key not in fields:
            raise core.PublishError(f"{src}:1: the front matter has no {key!r}")

    def text_of(key: str) -> str:
        v = fields[key][0]
        if not isinstance(v, str):
            raise fail(key, "must be text")
        return v

    out: dict = {}
    title = text_of("title")
    why = _one_line(title, "the title", TITLE_MAX) or _no_angle(title, "the title")
    if why:
        raise fail("title", why)
    out["title"] = title
    for key in ("date", "updated"):
        if key in fields:
            v = text_of(key)
            d = core.parse_iso_date(v)
            if d is None:
                raise fail(key, f"must be a real calendar day written YYYY-MM-DD, not {v!r}")
            out[key] = d
    out.setdefault("updated", None)
    if out["updated"] is not None and out["updated"] < out["date"]:
        raise fail("updated", "must not be before the date")
    description = text_of("description")
    why = core.description_problem(description)
    if why:
        raise fail("description", why)
    unseen = _unseen(description)
    if unseen:
        raise fail("description", f"must hold no control character and no invisible format "
                                  f"character ({unseen})")
    out["description"] = description
    tags: List[str] = []
    if "tags" in fields:
        v = fields["tags"][0]
        if not isinstance(v, list):
            raise fail("tags", "must be a list, for example [project, methods]")
        tags = list(v)
        for t in tags:
            if t not in TAGS:
                raise fail("tags", f"{t!r} is not a known tag ({', '.join(TAGS)})")
        if len(set(tags)) != len(tags):
            raise fail("tags", "a tag is given twice")
        if len(tags) > MAX_TAGS:
            raise fail("tags", f"at most {MAX_TAGS} tags, not {len(tags)}")
    out["tags"] = tags
    if "author" in fields:
        author = text_of("author")
        why = _one_line(author, "the author", AUTHOR_MAX) or _no_angle(author, "the author")
        if why:
            raise fail("author", why)
        out["author"] = author
    else:
        out["author"] = default_author
    draft = fields["draft"][0] if "draft" in fields else False
    if not isinstance(draft, bool):
        raise fail("draft", "must be true or false")
    out["draft"] = draft
    return out


_IMG_MD = re.compile(r"!\[((?:[^\[\]\\]|\\.)*)\]")
_IMG_TAG = re.compile(r"<img\b[^>]*>?", re.I)
# An attribute named exactly alt: not data-alt=, nor the text alt= inside another attribute's
# value (html_problem reads each tag's attributes one by one as well).
_ALT_ATTR = re.compile(r"""(?<![\w-])alt\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""", re.I)
_CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.S)
_HTML_COMMENT = re.compile(r"<!--.*?(?:-->|$)", re.S)


def _blank(m: "re.Match") -> str:
    return re.sub(r"[^\n]", " ", m.group(0))


def _alt_empty(alt: str) -> bool:
    """Whether an alt text says nothing: empty once character references are decoded and
    spaces and invisible characters are dropped (&#32; or a zero-width space is not a sentence)."""
    text = html.unescape(alt)
    return not "".join(c for c in text if unicodedata.category(c) not in _UNSEEN).strip()


def body_problem(body: str, body_line: int) -> Optional[Tuple[int, str]]:
    """(file line, reason) for the first line of a post's body that makes it unfit, or None: a
    level-one ATX heading outside code (the title is the front matter's; block quotes, list
    items and HTML blocks are read as CommonMark reads them), or an image with no alt text
    outside code (fences and code spans)."""
    lines = core.split_lines(body)
    fenced = core.code_fences(lines)
    for i in range(len(lines)):
        if fenced[i] == core.FENCE_DISPUTED:
            return body_line + i, ("a line that Markdown readers disagree is fenced code or not; "
                                   "close or remove the fence")
    found: List[Tuple[int, str]] = []
    for mode in core.MD_MODES:
        read, _blocks = core.scan_blocks(lines, mode)
        for i, (ln, md) in enumerate(zip(lines, read)):
            if md.kind == "other" and fenced[i] is None:
                content = ln.expandtabs(4)[md.col:].lstrip(" ")
                if _H1_RE.match(content):
                    found.append((body_line + i, "a level-one heading; the title comes from the "
                                  "front matter, so start the body at level two (##)"))
        if mode == core.MD_MODES[0]:
            kept = [("" if md.kind in ("fence", "icode") or fenced[i] is not None else ln)
                    for i, (ln, md) in enumerate(zip(lines, read))]
            text = "\n".join(kept)
            text = _HTML_COMMENT.sub(_blank, text)
            text = _CODE_SPAN.sub(_blank, text)
            alt = ("an image with no alt text; write one sentence saying what the image shows "
                   "(![the sentence](picture.png), or alt=\"the sentence\" on an <img>)")
            for m in _IMG_MD.finditer(text):
                if _alt_empty(m.group(1)):
                    found.append((body_line + text.count("\n", 0, m.start()), alt))
            for m in _IMG_TAG.finditer(text):
                a = _ALT_ATTR.search(m.group(0))
                if not a or _alt_empty(next(g for g in a.groups() if g is not None)):
                    found.append((body_line + text.count("\n", 0, m.start()), alt))
    return min(found) if found else None


# ─────────────────────────────────────────────────────────────────────────────
# raw HTML in a body
# ─────────────────────────────────────────────────────────────────────────────

# The only markup a post may write as raw HTML, element -> its allowed attributes. Each is inert
# text-level markup; none takes a script, a style or an event handler. An image must also carry
# alt text, as body_problem asks of every image.
HTML_ALLOWED: Dict[str, Tuple[str, ...]] = {
    "a": ("href", "title"), "abbr": ("title",), "b": (), "br": (), "code": (), "del": (),
    "details": ("open",), "em": (), "i": (), "img": ("src", "alt", "width", "height", "title"),
    "ins": (), "kbd": (), "mark": (), "q": (), "s": (), "samp": (), "small": (), "strong": (),
    "sub": (), "summary": (), "sup": (), "u": (), "var": (), "wbr": (),
}
LINK_SCHEMES = ("http", "https", "mailto")
PICTURE_SCHEMES = ("https",)

# CommonMark's raw HTML, read on one line: spaces and tabs separate, an unquoted value holds no
# space, tab, quote, =, <, > or backtick. A tag that does not end on its line is refused, since
# the renderer may still read it as a tag across lines (and an HTML block's start, such as a lone
# `<script`, needs no `>` at all).
_HTML_START = re.compile(r"<(?=[A-Za-z/!?])")
_HTML_ATTR = r"""[ \t]+([A-Za-z_:][A-Za-z0-9_.:-]*)(?:[ \t]*=[ \t]*(?:"([^"]*)"|'([^']*)'|([^ \t"'=<>`]+)))?"""
_HTML_ATTR_RE = re.compile(_HTML_ATTR)
_HTML_OPEN_RE = re.compile(r"<([A-Za-z][A-Za-z0-9-]*)((?:" + _HTML_ATTR + r")*)[ \t]*/?>")
_HTML_CLOSE_RE = re.compile(r"</([A-Za-z][A-Za-z0-9-]*)[ \t]*>")
# A comment on one line, holding no "--" and not opening with ">" or "->": every reader, the
# browser included, then ends it at the same "-->" (a browser also ends one at "--!>", and reads
# "<!-->" and "<!--->" as whole comments).
_HTML_SIMPLE_COMMENT = re.compile(r"<!--(?!-?>)(?:(?!--).)*-->")
_HTML_URI_AUTOLINK = re.compile(r"<([A-Za-z][A-Za-z0-9+.-]{1,31}):[^<>\x00-\x20]*>")
_HTML_EMAIL_AUTOLINK = re.compile(
    r"<[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*>")
_HTML_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_URL_SCHEME = re.compile(r"([A-Za-z][A-Za-z0-9+.-]*):")


def _snip(text: str) -> str:
    return repr(text[:40] + ("..." if len(text) > 40 else ""))


def url_problem(value: str, *, picture: bool) -> Optional[str]:
    """Why an href or src value may not be served, or None. Character references are decoded and
    every space and control character dropped first, as a browser forgives some of them, so
    `&#106;avascript:` and `java<tab>script:` are read as the javascript: they are."""
    flat = re.sub(r"[\x00-\x20\x7f]", "", html.unescape(value))
    m = _URL_SCHEME.match(flat)
    if not m:
        return None
    scheme = m.group(1).lower()
    allowed = PICTURE_SCHEMES if picture else LINK_SCHEMES
    if scheme in allowed:
        return None
    if picture:
        return f"names a {scheme}: address; a picture is a file of the post's folder or an https address"
    return f"names a {scheme}: address; a link is relative or uses http, https or mailto"


def _html_line_problem(ln: str) -> Optional[str]:
    """Why this line of a body holds markup a post may not, or None (see html_problem)."""
    pos = 0
    while True:
        m = _HTML_START.search(ln, pos)
        if not m:
            return None
        i = m.start()
        rest = ln[i:]
        if rest.startswith("<!--"):
            c = _HTML_SIMPLE_COMMENT.match(rest)
            if not c:
                return (f"an HTML comment that does not close on its own line, or holds '--' "
                        f"({_snip(rest)}); write it on one line as <!-- text --> or leave it out")
            pos = i + c.end()
            continue
        if rest[1] in "!?":
            return f"an HTML declaration or processing instruction ({_snip(rest)}); leave it out"
        auto = _HTML_URI_AUTOLINK.match(rest)
        if auto:
            scheme = auto.group(1).lower()
            if scheme not in LINK_SCHEMES:
                return f"an autolink to a {scheme}: address; a link uses http, https or mailto"
            pos = i + auto.end()
            continue
        auto = _HTML_EMAIL_AUTOLINK.match(rest)
        if auto:
            pos = i + auto.end()
            continue
        if rest[1] == "/" and not re.match(r"</[A-Za-z]", rest):
            pos = i + 2                      # "</" before a non-letter is text to every reader
            continue
        tag = _HTML_CLOSE_RE.match(rest) or _HTML_OPEN_RE.match(rest)
        if not tag:
            return (f"an HTML tag that does not close on its line or cannot be read ({_snip(rest)}); "
                    f"a < that is text is written &lt; or followed by a space")
        if _HTML_CONTROL.search(tag.group(0)):
            return f"an HTML tag holding a control character ({_snip(tag.group(0))})"
        name = tag.group(1).lower()
        if name not in HTML_ALLOWED:
            return (f"the HTML element <{name}>, which a post may not hold; raw HTML in a post is "
                    f"limited to a few inert tags, listed in {BLOG_DIR}/{README_NAME}")
        if tag.re is _HTML_OPEN_RE:
            attrs: Dict[str, str] = {}
            for a in _HTML_ATTR_RE.finditer(tag.group(2)):
                key = a.group(1).lower()
                value = next((g for g in a.groups()[1:] if g is not None), "")
                if key not in HTML_ALLOWED[name]:
                    can = ", ".join(HTML_ALLOWED[name]) or "none"
                    return (f"the attribute {key} on <{name}>; it may carry only: {can} (no event "
                            f"handler, style or other attribute)")
                if key in attrs:
                    return f"the attribute {key} twice on <{name}>"
                attrs[key] = value
                if key in ("href", "src"):
                    why = url_problem(value, picture=name == "img")
                    if why:
                        return f"<{name} {key}=...> {why}"
            if name == "img" and _alt_empty(attrs.get("alt", "")):
                return ("an <img> with no alt text; write one sentence saying what the image shows "
                        "in alt=\"...\"")
        pos = i + tag.end()


def html_problem(body: str, body_line: int) -> Optional[Tuple[int, str]]:
    """(file line, reason) for the first line of a post's body that holds markup a post may not,
    or None. A line is skipped only when every Markdown reader agrees it is fenced or indented
    code; every other line, inline code included, is read for markup (see the module docstring)."""
    lines = core.split_lines(body)
    fenced = core.code_fences(lines)
    reads = [core.scan_blocks(lines, mode)[0] for mode in core.MD_MODES]
    for i, ln in enumerate(lines):
        if fenced[i] in (core.FENCE_CLOSED, core.FENCE_UNCLOSED):
            continue
        if all(read[i].kind in ("fence", "icode") for read in reads):
            continue
        why = _html_line_problem(ln)
        if why:
            return body_line + i, why
    return None


# ─────────────────────────────────────────────────────────────────────────────
# media
# ─────────────────────────────────────────────────────────────────────────────

# handler and listener are SVG Tiny 1.2's script hooks, still in the SVG namespace.
_SVG_FORBIDDEN = {"script", "foreignobject", "iframe", "embed", "object", "handler", "listener"}
_SVG_DECL = re.compile(r"<!\s*(?:doctype|entity)\b", re.I)
_DATA_IMAGE = re.compile(r"^data:image/(?:png|jpeg|webp|gif)(?:;[^,]*)?,", re.I)
_XML_ENCODING = re.compile(r"\s*<\?xml\b[^>]*?\bencoding\s*=\s*([\"'])([^\"']*)\1")
SVG_NS = "http://www.w3.org/2000/svg"
XSL_NS = "http://www.w3.org/1999/XSL/Transform"
XML_NS = "http://www.w3.org/XML/1998/namespace"
XLINK_NS = "http://www.w3.org/1999/xlink"
_CSS_COMMENT = re.compile(r"/\*.*?(?:\*/|$)", re.S)
_CSS_ESCAPE = re.compile(r"\\(?:([0-9a-fA-F]{1,6})[ \t\r\n\f]?|(\r\n|[\n\r\f])|(.))", re.S)
_CSS_BAD = ("@import", "image-set(", "expression(", "-moz-binding", "behavior:")


def _compact(s: str) -> str:
    return re.sub(r"[\s\x00-\x1f\x7f]", "", s).lower()


def _css_escape(m: "re.Match") -> str:
    if m.group(1):
        n = int(m.group(1), 16)
        return chr(n) if 0 < n < 0x110000 and not 0xD800 <= n < 0xE000 else "\ufffd"
    return "" if m.group(2) else m.group(3)


def css_problem(css: str) -> Optional[str]:
    """Why this CSS (a <style> element's text, or an attribute value) may not be served, or None.
    Comments are removed and escapes decoded first, then whitespace dropped, so that nothing can
    spell url( or @import in a way this misses; a url() must name a #fragment or a raster
    data:image/ URL, and anything else, or anything unreadable, is refused."""
    text = _CSS_COMMENT.sub("", css)
    text = _CSS_ESCAPE.sub(_css_escape, text)
    flat = _compact(text)
    for bad in _CSS_BAD:
        if bad in flat:
            return f"holds CSS with {bad.rstrip('(:')}"
    if "url(" not in flat and "src(" not in flat:
        return None
    if "src(" in flat:
        return "holds CSS with src()"
    for part in flat.split("url(")[1:]:
        target = part.split(")", 1)[0].lstrip("'\"")
        if not (target.startswith("#") or _DATA_IMAGE.match(target)) or ")" not in part:
            return "holds CSS with a url() that is neither a #fragment nor a data:image/ URL of a raster format"
    return None


def svg_problems(data: bytes) -> List[str]:
    """Why this SVG may not be served from the site's origin, as a list (empty when it may). See
    the module docstring for the reasons; the rules are the same whatever the picture shows."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ["is not UTF-8 text (other encodings are not read)"]
    problems: List[str] = []
    declared = _XML_ENCODING.match(text)
    if declared and declared.group(2).strip().lower() not in ("utf-8", "utf8"):
        problems.append(f"declares the encoding {declared.group(2)!r} (an SVG is read as UTF-8 only)")
    if _SVG_DECL.search(text):
        problems.append("holds a DOCTYPE or ENTITY declaration")
    if "javascript:" in _compact(text):
        problems.append("holds a javascript: URL")
    parser = expat.ParserCreate(namespace_separator=" ")
    seen: set = set()
    state = {"root": False, "style": 0}
    style_text: List[str] = []

    def flag(msg: str) -> None:
        if msg not in seen:
            seen.add(msg)
            problems.append(msg)

    def start(name, attrs):
        ns, _sep, local = name.rpartition(" ")
        local = local.lower()
        if not state["root"]:
            state["root"] = True
            if name != f"{SVG_NS} svg":
                flag("does not have an svg element of the SVG namespace as its root")
        if ns == XSL_NS:
            flag("holds an XSLT element")
        elif ns != SVG_NS:
            flag(f"holds an element outside the SVG namespace (<{local}> in "
                 f"{ns or 'no namespace'}), which a browser may read as HTML or ignore")
        if local in _SVG_FORBIDDEN:
            flag(f"holds a <{local}> element")
        if local == "style":
            state["style"] += 1
        for k, v in attrs.items():
            ans, _s, alocal = k.rpartition(" ")
            low = alocal.lower()
            shown = alocal if not ans else f"{alocal} (namespace {ans})"
            if ans == XSL_NS:
                flag("holds an XSLT attribute")
            if ans not in ("", XLINK_NS, XML_NS, XSL_NS):
                flag(f"holds the attribute {alocal} of the namespace {ans}; an SVG carries attributes "
                     f"of no namespace, of XLink, and xml:lang and xml:space only")
            if ans == XML_NS and low not in ("lang", "space"):
                flag(f"holds the attribute xml:{alocal}; an SVG may carry only xml:lang and xml:space "
                     f"(xml:base, for one, would move where its links point)")
            if low.startswith("on"):
                flag(f"holds the event attribute {shown}")
            if "javascript:" in _compact(v):
                flag("holds a javascript: URL")
            if low in ("href", "src"):
                val = v.strip()
                if not (val.startswith("#") or _DATA_IMAGE.match(val)):
                    flag(f"has a {shown} that is neither a #fragment nor a data:image/ URL of a raster format")
            if low == "attributename":
                target = v.strip().rsplit(":", 1)[-1].lower()
                if target in ("href", "src"):
                    flag("animates a href or src")
                elif target.startswith("on"):
                    flag("animates an event attribute")
            why = css_problem(v)
            if why:
                flag(why)

    def end(name):
        if name.rpartition(" ")[2].lower() == "style" and state["style"]:
            state["style"] -= 1
            if not state["style"]:
                why = css_problem("".join(style_text))
                style_text.clear()
                if why:
                    flag(why)

    def chars(data_):
        if state["style"]:
            style_text.append(data_)

    def pi(target, _data):
        flag(f"holds a processing instruction (<?{target} ...?>), which could attach a stylesheet "
             f"or a transformation")

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = chars
    parser.ProcessingInstructionHandler = pi
    try:
        parser.Parse(text.encode("utf-8"), True)
    except expat.ExpatError as e:
        problems.append(f"is not well-formed XML ({e})")
    except (ValueError, LookupError, UnicodeError) as e:
        # expat honours the declared encoding, and an unknown or multi-byte one raises here
        problems.append(f"cannot be read as XML ({type(e).__name__}: {e})")
    return problems


# The first bytes of each raster format, by extension. A picture is staged byte for byte and
# served by its name, so its content has to be what the name says.
def raster_problem(name: str, data: bytes) -> Optional[str]:
    """Why a raster picture's content does not match its extension, or None (an SVG is not a
    raster; svg_problems reads it)."""
    ext = name.rsplit(".", 1)[-1].lower()
    if ext == "png":
        ok = data.startswith(b"\x89PNG\r\n\x1a\n")
    elif ext in ("jpg", "jpeg"):
        ok = data.startswith(b"\xff\xd8\xff")
    elif ext == "gif":
        ok = data[:6] in (b"GIF87a", b"GIF89a")
    elif ext == "webp":
        ok = data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    elif ext == "avif":
        # an ISO base media file: a leading ftyp box whose major or compatible brands name AVIF
        size = int.from_bytes(data[:4], "big")
        ok = False
        if data[4:8] == b"ftyp" and 16 <= size <= len(data):
            box = data[8:size]
            brands = {box[0:4]} | {box[j:j + 4] for j in range(8, len(box) - 3, 4)}
            ok = bool(brands & {b"avif", b"avis"})
    else:
        return None
    if ok:
        return None
    return (f"does not start the way {ext.upper()} files do; a picture is named by its format, "
            f"so an SVG, an HTML page or another format cannot pass under this name")


# ─────────────────────────────────────────────────────────────────────────────
# discovery
# ─────────────────────────────────────────────────────────────────────────────

def _tree(root: Path, rev: Optional[str]) -> List[str]:
    """Every file under docs/blog/: the commit's tree, or (rev None, for the diagrams check of
    a working tree) what git lists there, tracked or untracked but not ignored, so a stray
    .DS_Store that .gitignore names does not count."""
    if rev is not None:
        return sorted(p for p in core.git_tracked(root, [BLOG_DIR], rev=rev)
                      if p.startswith(BLOG_DIR + "/"))
    core.git_check_toplevel(root)
    listed = core.git_lines(root, ["ls-files", "-z", "--cached", "--others", "--exclude-standard",
                                   "--", BLOG_DIR])
    return sorted(p for p in set(listed)
                  if p.startswith(BLOG_DIR + "/") and os.path.lexists(root / p))


def reserved_slugs() -> Tuple[str, ...]:
    """The folder names a post may not take: `index` (the blog's own index), then every directory
    name the guard skips (ledger_check.SKIP_DIRS) that is also a slug, such as build and dist.
    Read from ledger_check, so the two lists cannot drift apart."""
    skipped = sorted(d for d in core.ledger_check().SKIP_DIRS if SLUG_RE.match(d))
    return RESERVED_SLUGS + tuple(d for d in skipped if d not in RESERVED_SLUGS)


def layout(paths: List[str]) -> Dict[str, List[str]]:
    """slug -> the media file names of its folder, for every post folder among `paths` (paths
    relative to the repository, all under docs/blog/). PublishError, naming the path, for a file
    directly in docs/blog/ other than README.md, a folder that is not a slug or is reserved, a
    subfolder, a file that is neither index.md nor allowed media, two names that differ only in
    case, and a folder with no index.md."""
    posts: Dict[str, List[str]] = {}
    has_index: Dict[str, bool] = {}
    folded: Dict[str, Dict[str, str]] = {}
    reserved = reserved_slugs()
    for path in sorted(paths):
        parts = path[len(BLOG_DIR) + 1:].split("/")
        if len(parts) == 1:
            if parts[0] != README_NAME:
                raise core.PublishError(
                    f"{path}: only {README_NAME} may stand directly in {BLOG_DIR}/; a post is a "
                    f"folder, {BLOG_DIR}/<slug>/{INDEX_NAME}")
            continue
        slug = parts[0]
        if not SLUG_RE.match(slug) or len(slug) > SLUG_MAX:
            raise core.PublishError(
                f"{path}: the folder {slug!r} is not a slug (lower-case letters and digits joined "
                f"by single hyphens, at most {SLUG_MAX} characters); the folder name is the address")
        if slug in RESERVED_SLUGS:
            raise core.PublishError(f"{path}: the folder name {slug!r} is reserved, because the "
                                    f"address blog/{slug}/ is the blog's own index; pick another slug")
        if slug in reserved:
            raise core.PublishError(f"{path}: the folder name {slug!r} is reserved, because the "
                                    f"publishing guard skips every directory of that name, so the "
                                    f"post would be refused when it is staged; pick another slug")
        if len(parts) > 2:
            raise core.PublishError(f"{path}: a post folder holds no subfolder; keep its pictures "
                                    f"beside {INDEX_NAME}")
        name = parts[1]
        posts.setdefault(slug, [])
        if name == INDEX_NAME:
            has_index[slug] = True
            continue
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in MEDIA_EXT or not MEDIA_NAME_RE.match(name):
            raise core.PublishError(
                f"{path}: not a file a post may hold; besides {INDEX_NAME} only pictures "
                f"({', '.join(MEDIA_EXT)}) named with letters, digits, '.', '_', '~' and '-', "
                f"starting with a letter, digit, '_' or '~'")
        twin = folded.setdefault(slug, {}).get(name.casefold())
        if twin is not None:
            raise core.PublishError(f"{path}: the folder also holds {twin}; two names that differ "
                                    f"only in case are one file on macOS and Windows, so rename one")
        folded[slug][name.casefold()] = name
        posts[slug].append(name)
    for slug in posts:
        if not has_index.get(slug):
            raise core.PublishError(f"{BLOG_DIR}/{slug}/: a post folder with no {INDEX_NAME}")
    return posts


def _read_text(root: Path, rev: Optional[str], rel: str) -> str:
    if rev is not None:
        return core.committed_text(root, rev, rel)
    try:
        return (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise core.PublishError(f"{rel}: cannot be read as UTF-8 text ({type(e).__name__})")


def _is_draft(fields: Dict[str, Tuple[object, int]], src: str) -> bool:
    """Whether the post is a draft, read from `draft` alone: a value that is not a boolean is
    refused, and nothing else is validated."""
    if "draft" not in fields:
        return False
    value, line = fields["draft"]
    if not isinstance(value, bool):
        raise core.PublishError(f"{src}:{line}: draft: must be true or false")
    return value


def sources(root: Path, rev: Optional[str] = None) -> List[Tuple[str, str]]:
    """(src, text) of every post that is not a draft, in slug order: what the Mermaid drawings are
    made for (diagrams.py). rev=None reads the working tree. Front matter is read, so a post that
    cannot be parsed raises PublishError; its other rules are discover's."""
    root = Path(root).resolve()
    out: List[Tuple[str, str]] = []
    for slug in sorted(layout(_tree(root, rev))):
        src = post_src(slug)
        text = _read_text(root, rev, src)
        fields, _body, _line = parse_front_matter(text, src)
        if not _is_draft(fields, src):
            out.append((src, text))
    return out


def latest_day(root: Path, sha: str) -> date:
    """The last day a post of commit `sha` may carry: the day after the commit's committer date,
    in the committer's own time zone. A property of the commit, so staging it gives the same
    answer whenever and wherever it runs, and the day of grace covers every time zone."""
    stamp = core.git_lines(root, ["show", "-s", "--format=%cI%x00", core.resolve_commit(root, sha)])
    when = stamp[0].strip() if stamp else ""
    try:
        day = datetime.fromisoformat(when[:-1] + "+00:00" if when.endswith("Z") else when).date()
    except ValueError:
        raise core.PublishError(f"commit {sha[:12]} has no committer date that can be read ({when!r})")
    return day + timedelta(days=1)


def discover(root: Path, sha: str, *, manifest: dict, ledger: dict, author: str) -> List[Post]:
    """The published posts of commit `sha`, newest first. Each is read through
    core.published_text (the guard), validated, and given its media from the commit. `author`
    is CITATION.cff's first author, the default. Raises PublishError at the first fault, with
    the source path (and the line, for front matter)."""
    root = Path(root).resolve()
    names = layout(_tree(root, sha))
    docs_desc = {p["description"].casefold(): p["src"] for p in core.manifest_pages(manifest)
                 if isinstance(p.get("description"), str)}
    seen_desc: Dict[str, str] = {}
    posts: List[Post] = []
    last_day: Optional[date] = None
    for slug in sorted(names):
        src = post_src(slug)
        fields, _b, _l = parse_front_matter(core.committed_text(root, sha, src), src)
        if _is_draft(fields, src):
            continue
        text = core.published_text(root, src, manifest=manifest, ledger=ledger, rev=sha)
        fields, body, body_line = parse_front_matter(text, src)
        meta = validate_front(fields, src, author)
        if last_day is None:
            last_day = latest_day(root, sha)
        for key in _DAY_KEYS:
            if meta[key] is not None and meta[key] > last_day:
                raise core.PublishError(
                    f"{src}:{fields[key][1]}: {key}: {meta[key].isoformat()} is later than the day "
                    f"after the commit being staged ({last_day.isoformat()}); a post carries the day "
                    f"it is published, so a wrong year cannot pin it to the top of the blog and the feed")
        bad = body_problem(body, body_line) or html_problem(body, body_line)
        if bad:
            raise core.PublishError(f"{src}:{bad[0]}: {bad[1]}")
        key = meta["description"].casefold()
        other = docs_desc.get(key) or seen_desc.get(key)
        if other:
            raise core.PublishError(f"{src}:{fields['description'][1]}: description: the same "
                                    f"description as {other}; each page and post needs its own, "
                                    f"since it is the preview a search result shows")
        seen_desc[key] = src
        media: List[Tuple[str, bytes]] = []
        for name in names[slug]:
            rel = f"{BLOG_DIR}/{slug}/{name}"
            hit = core.never_publish_hit(manifest, rel)
            if hit:
                raise core.PublishError(f"{rel}: is under never_publish ({hit})")
            entry = core.git_entry(root, sha, rel)
            if entry is None or entry[0] == "120000":
                raise core.PublishError(f"{rel}: commit {sha[:12]} holds no regular file at that "
                                        f"path (a symbolic link is not a picture)")
            data = entry[1]
            if len(data) > MEDIA_MAX:
                raise core.PublishError(f"{rel}: {len(data)} bytes; a picture may be at most "
                                        f"{MEDIA_MAX // (1024 * 1024)} MiB")
            if name.lower().endswith(".svg"):
                problems = svg_problems(data)
                if problems:
                    raise core.PublishError(f"{rel}: the SVG {'; it '.join(problems)}; the site "
                                            f"serves it from the same origin as the CMS")
            else:
                why = raster_problem(name, data)
                if why:
                    raise core.PublishError(f"{rel}: the picture {why}")
            media.append((name, data))
        posts.append(Post(slug, src, meta["title"], meta["date"].isoformat(),
                          meta["updated"].isoformat() if meta["updated"] else None,
                          meta["description"], meta["tags"], meta["author"], body, body_line, media))
    return order(posts)


def order(posts: List[Post]) -> List[Post]:
    """Newest first: date descending, then updated descending (none last), then slug ascending."""
    def key(p: Post):
        upd = -core.parse_iso_date(p.updated).toordinal() if p.updated else 1
        return (-core.parse_iso_date(p.date).toordinal(), upd, p.slug)
    return sorted(posts, key=key)


def neighbours(posts: List[Post], i: int) -> Tuple[Optional[Post], Optional[Post]]:
    """(prev, next) of posts[i] in a newest-first list: prev is the next older post, next the next
    newer one; None at either end."""
    older = posts[i + 1] if i + 1 < len(posts) else None
    newer = posts[i - 1] if i > 0 else None
    return older, newer


def link_mapping(manifest: dict, posts: List[Post], post: Optional[Post] = None) -> Dict[str, str]:
    """The extra entries of core.rewrite_links's mapping: every post's index.md to its route, and,
    for `post`, each of its media files to ./<file> so a link or image in the body names the copy
    staged beside the page."""
    out = {p.src: post_route(manifest, p.slug) for p in posts}
    if post is not None:
        for name, _data in post.media:
            out[f"{BLOG_DIR}/{post.slug}/{name}"] = f"./{name}"
    return out


# ─────────────────────────────────────────────────────────────────────────────
# what stage.py writes
# ─────────────────────────────────────────────────────────────────────────────

def _q(s: str) -> str:
    """A JSON string literal, which is a valid YAML double-quoted scalar."""
    return json.dumps(s, ensure_ascii=False)


def _neighbour(manifest: dict, p: Optional[Post]) -> str:
    if p is None:
        return "false"
    return json.dumps({"link": post_route(manifest, p.slug), "label": p.title}, ensure_ascii=False)


def staged_front_matter(manifest: dict, post: Post, prev: Optional[Post], nxt: Optional[Post],
                        sha: str) -> str:
    """The head of a staged post: front matter, the ledger pragma and the GENERATED line, ending
    in a blank line."""
    lines = ["---",
             f"title: {_q(post.title)}",
             f"description: {_q(post.description)}",
             f"editUrl: {_q(f'https://github.com/{manifest['repo']}/blob/main/{post.src}')}",
             f"date: {_q(post.date)}"]
    if post.updated:
        lines.append(f"updated: {_q(post.updated)}")
    lines += [f"author: {_q(post.author)}",
              f"tags: {json.dumps(post.tags, ensure_ascii=False)}",
              f"prev: {_neighbour(manifest, prev)}",
              f"next: {_neighbour(manifest, nxt)}",
              "---",
              "<!-- ledger:ignore-file -->",
              f"<!-- GENERATED by tools/publish/stage.py from {post.src} at {sha[:12]}; do not edit -->",
              "", ""]
    return "\n".join(lines)


def blog_json(manifest: dict, posts: List[Post], author: str) -> dict:
    """The data the blog index, the feed and the landing page draw from, newest first."""
    return {"author": author,
            "posts": [{"slug": p.slug, "route": f"blog/{p.slug}/", "title": p.title, "date": p.date,
                       "updated": p.updated, "description": p.description, "tags": list(p.tags),
                       "author": p.author} for p in posts]}
