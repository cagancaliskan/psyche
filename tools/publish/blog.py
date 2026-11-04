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
reserved: it would collide with the blog's own index route. Anything else is
refused and named: a stray file would otherwise be staged as, or silently left out of, the site.

Front matter. The block between the first line `---` and the next line `---` is read by a
parser of its own, because the standard library has no YAML reader and a library is not allowed
here. The parser accepts exactly the shapes that the CMS writes and a person is likely to
write, and refuses everything else with the line number, so a post never means two things to two
readers:

    key: "double quoted"      the escapes \\" \\\\ \\/ \\n \\t and \\uXXXX
    key: 'single quoted'      '' for a quote
    key: plain text           one line, no leading quote, bracket, brace or any of & * ! | > % @,
                              no ' #' and no ': ', not one of null ~ yes no on off, not a number
                              (12, 0x1F, 1e3, .inf, .nan), not a lone - ? or :; a plain day
                              YYYY-MM-DD is read for `date` and `updated`
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
before `date`, and `draft` a boolean. A draft is read only far enough to see that it is one (its
other keys are not validated): it is not staged, its pictures are not read, and the guard is not
asked about it, so an unfinished draft does not stop a stage. The body must hold no level-one
ATX heading outside code (core.scan_blocks reads block quotes, list items and HTML blocks, so
`> # x` is a heading and a `# x` inside a comment or <pre> is not), because the title comes from
the front matter, and no image without alt text: a Markdown image whose alt is empty or an <img>
tag with no alt, outside code, because the alt is one sentence saying what the picture shows.

SVG pictures are served from the site's own origin, which is also the CMS's origin, and the
CMS keeps its access token in the browser's local storage. An SVG that could run a script
there would be a way to that token, so svg_problems refuses an SVG with a script, event
attribute, foreignObject, iframe, embed or object element, a javascript: URL, a DOCTYPE or
ENTITY declaration, any processing instruction (<?xml-stylesheet?> and so XSLT; the XML
declaration is not one), an element or attribute of the XSLT namespace, a root that is not an svg
element of the SVG namespace, an animation that sets an href or src, a href, xlink:href or src
that is not a #fragment or a data:image/ URL of a raster format, or CSS (a <style> element, a
style attribute or any attribute value) with @import, image-set(), expression() or a url() that
is not a #fragment or such a data URL. Names are read with namespaces, so a prefix hides
nothing, and CSS is read after its comments and escapes are undone. A raster picture is not parsed.

Order. Newest first: date descending, then `updated` descending (a post without one last), then
slug ascending. Each post's `prev` is the next older one and its `next` the next newer one.

Public functions: parse_front_matter, validate_front, svg_problems, layout, discover,
sources, order, neighbours, post_route, link_mapping, staged_front_matter, blog_json.

Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
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

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_MAX = 80
MEDIA_EXT = ("png", "jpg", "jpeg", "webp", "avif", "gif", "svg")
MEDIA_NAME_RE = re.compile(r"^[A-Za-z0-9_~][A-Za-z0-9._~-]*$")
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


def _plain(raw: str, *, in_list: bool = False) -> str:
    """A plain one-line scalar, checked; `in_list` also stops it at a comma or bracket."""
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
    return raw


def _scalar(raw: str, *, in_list: bool = False) -> object:
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
    return _plain(raw, in_list=in_list)


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
                fields[key] = (_scalar(raw), n)
        except _Bad as e:
            raise core.PublishError(f"{src}:{n}: {e}") from None
    flush()
    if end is None:
        raise core.PublishError(f"{src}:1: the front matter is not closed by a line `---`")
    body = "".join(lines[end + 1:])
    return fields, body, end + 2


def _one_line(value: str, what: str, limit: int) -> Optional[str]:
    if "\n" in value or "\r" in value or any(unicodedata.category(c) in ("Cc", "Zl", "Zp") for c in value):
        return f"{what} must be one line with no control character"
    if value != value.strip():
        return f"{what} must have no leading or trailing space"
    if not 1 <= len(value) <= limit:
        return f"{what} must be 1 to {limit} characters, not {len(value)}"
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
    why = _one_line(title, "the title", TITLE_MAX)
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
        why = _one_line(author, "the author", AUTHOR_MAX)
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
_ALT_ATTR = re.compile(r"""\balt\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""", re.I)
_CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.S)
_HTML_COMMENT = re.compile(r"<!--.*?(?:-->|$)", re.S)


def _blank(m: "re.Match") -> str:
    return re.sub(r"[^\n]", " ", m.group(0))


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
                if not m.group(1).strip():
                    found.append((body_line + text.count("\n", 0, m.start()), alt))
            for m in _IMG_TAG.finditer(text):
                a = _ALT_ATTR.search(m.group(0))
                if not a or not next(g for g in a.groups() if g is not None).strip():
                    found.append((body_line + text.count("\n", 0, m.start()), alt))
    return min(found) if found else None


# ─────────────────────────────────────────────────────────────────────────────
# media
# ─────────────────────────────────────────────────────────────────────────────

_SVG_FORBIDDEN = {"script", "foreignobject", "iframe", "embed", "object"}
_SVG_DECL = re.compile(r"<!\s*(?:doctype|entity)\b", re.I)
_DATA_IMAGE = re.compile(r"^data:image/(?:png|jpeg|webp|gif)(?:;[^,]*)?,", re.I)
SVG_NS = "http://www.w3.org/2000/svg"
XSL_NS = "http://www.w3.org/1999/XSL/Transform"
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
            if low.startswith("on"):
                flag(f"holds the event attribute {shown}")
            if "javascript:" in _compact(v):
                flag("holds a javascript: URL")
            if low in ("href", "src"):
                val = v.strip()
                if not (val.startswith("#") or _DATA_IMAGE.match(val)):
                    flag(f"has a {shown} that is neither a #fragment nor a data:image/ URL of a raster format")
            if low == "attributename" and v.strip().rsplit(":", 1)[-1].lower() in ("href", "src"):
                flag("animates a href or src")
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
    return problems


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


def layout(paths: List[str]) -> Dict[str, List[str]]:
    """slug -> the media file names of its folder, for every post folder among `paths` (paths
    relative to the repository, all under docs/blog/). PublishError, naming the path, for a file
    directly in docs/blog/ other than README.md, a folder that is not a slug, a subfolder, a file
    that is neither index.md nor allowed media, and a folder with no index.md."""
    posts: Dict[str, List[str]] = {}
    has_index: Dict[str, bool] = {}
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
    for slug in sorted(names):
        src = post_src(slug)
        fields, _b, _l = parse_front_matter(core.committed_text(root, sha, src), src)
        if _is_draft(fields, src):
            continue
        text = core.published_text(root, src, manifest=manifest, ledger=ledger, rev=sha)
        fields, body, body_line = parse_front_matter(text, src)
        meta = validate_front(fields, src, author)
        bad = body_problem(body, body_line)
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
