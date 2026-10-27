#!/usr/bin/env python3
"""diagrams.py — the Mermaid diagrams of the published pages, as committed SVG (D-031).

The governed Markdown keeps its ```mermaid fences: GitHub draws them there. The docs site
does not draw them in the browser. Each fence is drawn once, ahead of time, by
website/scripts/render-diagrams.mjs, into website/src/diagrams/<key>.svg, and tools/publish/
stage.py puts that SVG inline in place of the fence. The reader's browser runs no Mermaid.

    key = first 16 hex digits of sha256(renderer id, fence source)

The renderer id is the sha256 of the render script itself, so a changed fence AND a changed
renderer (its pinned Mermaid, its configuration, its post-processing) both name new keys.
A committed SVG is therefore current exactly when a file with the key of its source exists,
and a fence or a renderer changed without a re-render fails here, in CI, with nothing
installed beyond the interpreter. Each SVG also carries its key (data-key on the root), so a
file copied under another name is caught.

    python3 tools/publish/diagrams.py --check          fail if any fence has no current SVG, an
                                                       SVG matches no fence, or an SVG is not
                                                       the plain drawing the site may inline
    python3 tools/publish/diagrams.py --list           the fences as JSON (what the render
                                                       script draws); reads the working tree

Used by stage.py (inline_fences, orphans, svg_problems) and by the render script (--list).
A fence is replaced only when it stands at the left margin of the page, closed, and every
reading of Markdown agrees it is a fence; any other Mermaid fence in a published page stops
staging, because the stager would have to guess what the page meant.

Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Callable, Dict, List, NamedTuple, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402

DIR_REL = "website/src/diagrams"
SCRIPT_REL = "website/scripts/render-diagrams.mjs"
INFO = "mermaid"
KEY_LEN = 16

# What an SVG the site inlines may contain: drawing, text and a title. Nothing that runs,
# loads or links. The set is the one the render script emits.
ALLOWED_TAGS = frozenset({
    "svg", "g", "path", "rect", "circle", "ellipse", "polygon", "polyline", "line",
    "text", "tspan", "marker", "title", "desc",
})
_TAG_RE = re.compile(r"<\s*/?\s*([A-Za-z][A-Za-z0-9:_.-]*)")
_ATTR_ON_RE = re.compile(r"""[\s"'/]on[a-z]+\s*=""", re.I)
_URL_RE = re.compile(r"url\(\s*([^)]*)\)", re.I)


class Fence(NamedTuple):
    first: int        # index of the opening fence line
    last: int         # index of the closing fence line
    source: str       # the lines between them, joined by "\n"
    line: int         # 1-based line number of the opening fence, for messages


def renderer_id(script: bytes) -> str:
    """The id of a renderer: the sha256 of the render script's bytes."""
    return hashlib.sha256(script).hexdigest()


def diagram_key(renderer: str, source: str) -> str:
    h = hashlib.sha256()
    h.update(b"psyche-diagram/1\0")
    h.update(renderer.encode("ascii"))
    h.update(b"\0")
    h.update(source.encode("utf-8"))
    return h.hexdigest()[:KEY_LEN]


def fences(text: str, where: str = "page") -> List[Fence]:
    """The Mermaid fences of a Markdown document, read the way core.scan_blocks reads it
    (so a fence inside a list item, a block quote or an HTML block is not mistaken for one
    on the page). PublishError for a Mermaid fence that cannot be replaced safely."""
    lines = core.split_lines(text)
    info, blocks = core.scan_blocks(lines)
    states = core.code_fences(lines)
    out: List[Fence] = []
    i = 0
    while i < len(lines):
        li = info[i]
        if li.kind != "fence" or li.role != "open":
            i += 1
            continue
        j = i
        while j + 1 < len(lines) and info[j + 1].block == li.block and info[j + 1].kind == "fence":
            j += 1
        # the fence marker may follow a block quote's '>' or a list item's marker
        m = re.match(r"^[ \t>]*(?:(?:[-*+]|[0-9]{1,9}[.)])[ \t]+)*(?:`{3,}|~{3,})[ \t]*([^\s`]*)", lines[i])
        if m and m.group(1).lower() == INFO:
            where_line = f"{where}, line {i + 1}"
            if not lines[i].startswith(("```", "~~~")) or li.col != 0:
                raise core.PublishError(
                    f"{where_line}: a Mermaid fence must stand at the left margin of the page "
                    f"(not in a list item, a block quote or an indent): the stager replaces whole lines")
            closed = blocks[li.block].closed and info[j].role == "close"
            if not closed or any(states[k] != core.FENCE_CLOSED for k in range(i, j + 1)):
                raise core.PublishError(
                    f"{where_line}: this Mermaid fence is not closed, or the Markdown parsers disagree "
                    f"about it; close it with a fence line of its own")
            if any(info[k].col != 0 for k in range(i, j + 1)):
                raise core.PublishError(f"{where_line}: a Mermaid fence line is indented or quoted")
            out.append(Fence(i, j, "\n".join(lines[i + 1:j]), i + 1))
        i = j + 1
    return out


# ─────────────────────────────────────────────────────────────────────────────
# the SVG files
# ─────────────────────────────────────────────────────────────────────────────

def svg_rel(key: str) -> str:
    return f"{DIR_REL}/{key}.svg"


def svg_problems(text: str, key: str) -> List[str]:
    """Why this text may not be inlined as the diagram `key`, or []. The site puts the file
    in the page as written, so it must be a plain drawing: the tags the renderer emits, no
    event attribute, no reference except to an id inside the file, and its own key."""
    out: List[str] = []
    if not text.startswith("<svg"):
        out.append("does not start with <svg>")
    if len(text.encode("utf-8")) > 200_000:
        out.append("is larger than 200 kB")
    if text.count(f'data-key="{key}"') != 1:
        out.append(f"does not carry data-key=\"{key}\" exactly once (it was drawn for another source)")
    tags = {m.group(1).lower() for m in _TAG_RE.finditer(text)}
    bad = sorted(tags - ALLOWED_TAGS)
    if bad:
        out.append("uses tags the site does not inline: " + ", ".join(bad))
    if _ATTR_ON_RE.search(text):
        out.append("has an event-handler attribute")
    if re.search(r"""["'(]\s*(?:javascript|data)\s*:|<!|<\?""", text, re.I):
        out.append("has a script or data URL, a comment, a declaration or a processing instruction")
    for m in _URL_RE.finditer(text):
        ref = m.group(1).strip().strip("'\"")
        if not re.match(r"^#[A-Za-z0-9_:.-]+$", ref):
            out.append(f"references something outside the file: url({m.group(1)})")
    if re.search(r"\b(?:xlink:)?href\s*=", text, re.I) or re.search(r"\bstyle\s*=", text, re.I):
        out.append("has an href or a style attribute")
    return out


def _bytes(root: Path, rev: Optional[str], rel: str) -> Optional[bytes]:
    if rev is None:
        p = root / rel
        return p.read_bytes() if p.is_file() else None
    entry = core.git_entry(root, rev, rel)
    return None if entry is None or entry[0] == "120000" else entry[1]


def read_renderer(root: Path, rev: Optional[str]) -> str:
    data = _bytes(root, rev, SCRIPT_REL)
    if data is None:
        raise core.PublishError(f"{SCRIPT_REL} is missing{'' if rev is None else ' at ' + rev[:12]}: "
                                f"the diagrams cannot be matched to a renderer")
    return renderer_id(data)


def committed_keys(root: Path, rev: Optional[str]) -> Set[str]:
    """The keys of the .svg files in the diagram directory (the commit's, or the disk's)."""
    if rev is None:
        d = root / DIR_REL
        names = [p.name for p in d.iterdir()] if d.is_dir() else []
    else:
        names = [Path(p).name for p in core.git_lines(
            root, ["ls-tree", "-r", "-z", "--name-only", core.resolve_commit(root, rev), "--", DIR_REL])]
    return {n[:-4] if n.endswith(".svg") else n for n in names}


def read_svg(root: Path, rev: Optional[str], key: str) -> Optional[str]:
    data = _bytes(root, rev, svg_rel(key))
    if data is None:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def inline_fences(text: str, where: str, renderer: str, get_svg: Callable[[str], Optional[str]],
                  seen: Dict[str, int]) -> Tuple[str, List[str]]:
    """`text` with every Mermaid fence replaced by its figure. get_svg(key) is the SVG file's
    text or None. Returns (new text, the keys used). `seen` counts the uses of each key on the
    page so far, so a fence repeated on one page keeps its ids unique."""
    found = fences(text, where)
    if not found:
        return text, []
    lines = core.split_lines(text, keepends=True)
    out: List[str] = []
    used: List[str] = []
    cursor = 0
    for f in found:
        key = diagram_key(renderer, f.source)
        svg = get_svg(key)
        if svg is None:
            raise core.PublishError(
                f"{where}, line {f.line}: no drawing of this Mermaid diagram (key {key}); the diagram "
                f"or the renderer changed. Run `npm run diagrams` in website/ and commit "
                f"{DIR_REL}/")
        problems = svg_problems(svg, key)
        if problems:
            raise core.PublishError(f"{svg_rel(key)}: " + "; ".join(problems))
        n = seen.get(key, 0)
        seen[key] = n + 1
        if n:
            svg = svg.replace(f"dg-{key}", f"dg-{key}-{n + 1}")
        eol = "\r\n" if lines[f.first].endswith("\r\n") else "\n"
        before = "".join(lines[cursor:f.first])
        out.append(before)
        # one blank line on each side of the figure: Markdown ends an HTML block at a blank line
        if before and not before.endswith((eol + eol, "\n\n")):
            out.append(eol)
        out.append(figure(svg) + eol)
        after = lines[f.last + 1] if f.last + 1 < len(lines) else ""
        if after.strip():
            out.append(eol)
        cursor = f.last + 1
        used.append(key)
    out.append("".join(lines[cursor:]))
    return "".join(out), used


def figure(svg: str) -> str:
    """The HTML that stands in for a fence: one line, so it is one Markdown HTML block. The
    scroll box takes keyboard focus because a diagram wider than a phone scrolls sideways
    there, and a scrolling region nobody can reach with a key is an accessibility fault. It is
    named after the drawing (a group labelled by the drawing's title), so the stop is not an
    unnamed one; at widths where nothing scrolls it is a harmless extra stop, since whether a
    box scrolls is a fact of the reader's screen that no static markup can know."""
    flat = "".join(line.strip() for line in svg.splitlines())
    m = re.search(r'viewBox="-?[0-9.]+ -?[0-9.]+ ([0-9.]+) [0-9.]+"', flat)
    width = f' style="--dg-w:{m.group(1)}"' if m else ""
    t = re.search(r'<svg\b[^>]*\saria-labelledby="([A-Za-z0-9_:.-]+)"', flat)
    name = f' role="group" aria-labelledby="{t.group(1)}"' if t else ""
    return ('<figure class="sx-diagram not-content" data-pagefind-ignore>'
            f'<div class="sx-diagram__scroll"{name} tabindex="0"{width}>{flat}</div></figure>')


# ─────────────────────────────────────────────────────────────────────────────
# what the pages need, and the check
# ─────────────────────────────────────────────────────────────────────────────

def needed(root: Path, manifest: dict, renderer: str, read: Callable[[dict], str]
           ) -> Dict[str, List[str]]:
    """key -> where the fence stands ("src:line"), for every fence of every published page."""
    out: Dict[str, List[str]] = {}
    for page in core.manifest_pages(manifest):
        for f in fences(read(page), page["src"]):
            out.setdefault(diagram_key(renderer, f.source), []).append(f"{page['src']}:{f.line}")
    return out


def orphans(root: Path, rev: Optional[str], used: Set[str]) -> List[str]:
    return sorted(k for k in committed_keys(root, rev) if k not in used)


def check(root: Path, rev: Optional[str] = None) -> List[str]:
    """Every problem, or []. rev=None reads the working tree (what CI has checked out)."""
    root = Path(root).resolve()
    problems: List[str] = []
    try:
        manifest = core.load_manifest(root)
        renderer = read_renderer(root, rev)

        def read(page: dict) -> str:
            data = _bytes(root, rev, page["src"])
            if data is None:
                raise core.PublishError(f"{page['src']}: listed in the manifest but not found")
            return data.decode("utf-8")

        want = needed(root, manifest, renderer, read)
    except core.PublishError as e:
        return [str(e)]
    for key, places in sorted(want.items()):
        svg = read_svg(root, rev, key)
        where = ", ".join(places)
        if svg is None:
            problems.append(f"{where}: no drawing for this Mermaid diagram (key {key}); the diagram or "
                            f"the renderer changed: run `npm run diagrams` in website/ and commit "
                            f"{DIR_REL}/")
            continue
        problems += [f"{svg_rel(key)}: {p}" for p in svg_problems(svg, key)]
    for key in orphans(root, rev, set(want)):
        problems.append(f"{svg_rel(key)}: matches no Mermaid diagram of any published page; run "
                        f"`npm run diagrams` in website/ to drop it")
    return problems


def listing(root: Path) -> dict:
    """What the render script draws: every fence of every published page, from the working
    tree, with the key the stager will look for."""
    root = Path(root).resolve()
    manifest = core.load_manifest(root)
    renderer = read_renderer(root, None)
    items: Dict[str, dict] = {}
    for page in core.manifest_pages(manifest):
        text = (root / page["src"]).read_text(encoding="utf-8")
        for f in fences(text, page["src"]):
            key = diagram_key(renderer, f.source)
            item = items.setdefault(key, {"key": key, "source": f.source, "where": []})
            item["where"].append(f"{page['src']}:{f.line}")
    return {"directory": DIR_REL, "renderer": renderer, "diagrams": list(items.values())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail unless every diagram has a current drawing")
    mode.add_argument("--list", action="store_true", help="print the diagrams as JSON")
    ap.add_argument("--rev", default=None, help="check a commit instead of the working tree")
    ap.add_argument("--root", default=str(core.REPO), help="repository root")
    args = ap.parse_args(argv)
    root = Path(args.root)
    try:
        if args.list:
            print(json.dumps(listing(root), ensure_ascii=False, indent=1))
            return 0
        problems = check(root, args.rev)
    except core.PublishError as e:
        print(f"diagrams: {e}", file=sys.stderr)
        return 2
    for p in problems:
        print(f"diagrams: {p}", file=sys.stderr)
    if problems:
        print(f"diagrams: {len(problems)} problem(s)", file=sys.stderr)
        return 1
    n = len(committed_keys(root, args.rev))
    print(f"diagrams: {n} drawing(s), each current for its Mermaid source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
