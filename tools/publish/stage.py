#!/usr/bin/env python3
"""stage.py — stage the governed documents and the public data for the docs site (D-031).

The site never holds prose of its own. Every page it shows is a document listed in
docs/publish.json, read from a COMMIT by core.published_text (never from disk, so nothing
that changes after the guard has looked can reach a page), with its relative links rewritten
for the site by core.rewrite_links. The data the custom pages draw from — the research plan
and the public projection of the ledger — comes from the same commit, and staging refuses
if either file on disk differs from it. So one commit id names everything a build shows.

    python3 tools/publish/stage.py --target site              # stage from HEAD
    python3 tools/publish/stage.py --target site --rev <sha>  # stage from a given commit

Output (both directories are gitignored, and CI fails if a staged copy is ever tracked):

    website/src/content/docs/<slug>.md   or  <slug>/index.md when other pages nest under it
    website/src/content/docs/blog/<slug>/index.md   a blog post, with its pictures beside it
    website/src/data/plan.json           tools/research_plan.json, validated
    website/src/data/ledger.public.json  core.ledger_public
    website/src/data/docs.json           the documentation list: "Start here", then the manifest's sections
    website/src/data/progress.json       the plan's public events and the author, for the Atom feed
    website/src/data/blog.json           the published posts, newest first, and the author
    website/src/data/stage.json          which commit was staged, and how many pages and posts

The events in progress.json come from render_plan.progress_events, the one place that derives them,
and the author from CITATION.cff; website/src/pages/progress.xml.ts writes the feed from that file
with a serialiser of its own (website/src/lib/feed.ts), and the feed's dates are the events' days,
never the build time.

docs.json is the list the documentation section of the site draws its navigation, its previous and
next links and its index from (build_docs_index). Its first group is "Start here": the documents of
the manifest section of that title, then the hand-written pages of DOCS_PAGES; every other manifest
section follows as a group of its own. Neither the home page nor the blog is in it. A document item is
{"kind": "doc", "slug", "title", "description"}, with the title the page shows and the manifest's
description; a hand-written page item is {"kind": "page", "route", "title"}, and its description is
the one the site states with the page itself, so it is written once. A new first entry of the list (a page to
get started, say) is a document listed first in the Start here section of docs/publish.json: it then
leads the list with the same item shape and no change here.

The blog's posts are not in the manifest. Each folder docs/blog/<slug>/ of the commit that holds an
index.md which is not a draft is a post (blog.py: layout, front matter, pictures, order). A post is
read through the same guard as a page, staged with a front matter of its own (title, date, author,
tags and its neighbours in date order, besides the description) and the GENERATED line, and its
pictures are copied beside it byte for byte from the commit. A relative link or image in a post that
names a picture of the same post becomes ./<file>; a link from a post or from a page to another post
becomes /blog/<slug>/, through the same mapping that core.rewrite_links uses for pages.

Each staged page starts with `<!-- ledger:ignore-file -->`, so a local ledger_check does not
report the copy a second time (the governed source is still checked), and a GENERATED line
naming its source and commit. Its front matter takes the title and the description from
docs/publish.json; the description is required, so a docs page never falls back to the site's
general one in search results and link previews. The output directories are emptied first: a page
removed from the manifest disappears from the site at the next stage.

Each ```mermaid fence of a page is replaced by the drawing of it that the commit holds under
website/src/diagrams/ (diagrams.py; drawn ahead of time by website/scripts/render-diagrams.mjs),
so the site runs no Mermaid in the browser. A fence with no current drawing, and a drawing no
fence uses, stop staging.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blog  # noqa: E402
import core  # noqa: E402
import diagrams  # noqa: E402
import render_plan  # noqa: E402

SITE_DIR = Path("website")
DOCS_OUT = SITE_DIR / "src" / "content" / "docs"
DATA_OUT = SITE_DIR / "src" / "data"

# Hand-written pages of the documentation (website/src/pages/*.astro), listed at the end of the
# documentation list's first group. Each page's own title is its label here (the title in its .astro
# front matter), and no label may be, or contain, the title of a staged document: "Roadmap", "Decision
# gates" and "Test battery" are the documents, so the two interactive pages say what a reader does with
# them instead (test_core.py checks this).
CUSTOM_PAGES: List[Tuple[str, str]] = [
    ("Explore the timeline", "roadmap/"),
    ("Step through the paradigms", "battery/"),
    ("Substrate status", "status/"),
]

# The documentation list's first group. The pages of the manifest section with exactly this title stand
# in it, before the hand-written pages, so the list has one group of this name.
START_GROUP = "Start here"

# The blog's index page (website/src/pages). It is not in the documentation list, but like the labels
# above its title may be neither a document's title nor contain one (test_core.py checks this).
BLOG_PAGE: Tuple[str, str] = ("Blog", "blog/")

# The hand-written pages of the documentation list (docs.json), each with its route as the site states
# it (no slashes). The home page and the blog are pages of the site, not of its documentation, so the
# list holds neither.
DOCS_PAGES: List[Tuple[str, str]] = [(label, path.strip("/")) for label, path in CUSTOM_PAGES]


def split_title(text: str, src: str) -> Tuple[str, str]:
    """The first ATX level-one heading outside fenced code, and the text without it.
    A page with no H1 is refused: every page shows a title, and inventing one would be the
    stager writing prose."""
    lines = text.splitlines(keepends=True)
    fence = None
    for i, line in enumerate(lines):
        stripped = line.lstrip(" ")
        if fence is None and (stripped.startswith("```") or stripped.startswith("~~~")):
            fence = stripped[:3]
            continue
        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            continue
        if stripped.startswith("# ") and len(line) - len(stripped) <= 3:
            title = stripped[2:].strip().rstrip("#").strip()
            if not title:
                break
            return title, "".join(lines[:i] + lines[i + 1:]).lstrip("\n")
    raise core.PublishError(f"{src}: no level-one heading to use as the page title")


def yaml_str(s: str) -> str:
    """A JSON string literal is a valid YAML double-quoted scalar."""
    return json.dumps(s, ensure_ascii=False)


def out_path(slug: str, all_slugs: List[str]) -> Path:
    nested = any(other.startswith(slug + "/") for other in all_slugs)
    return Path(slug) / "index.md" if nested else Path(slug + ".md")


def start_section(manifest: dict) -> Optional[dict]:
    """The manifest section titled exactly START_GROUP, or None. A section whose title differs
    from it only in case would make a second group of the same name, so it is refused."""
    found = None
    for section in manifest["sections"]:
        if section["title"] == START_GROUP:
            found = section
        elif section["title"].casefold() == START_GROUP.casefold():
            raise core.PublishError(
                f"docs/publish.json: the section {section['title']!r} differs from {START_GROUP!r} "
                f"only in case; the documentation list would show two groups of that name")
    return found


def build_docs_index(manifest: dict, titles: Dict[str, str]) -> Dict[str, List[dict]]:
    """The documentation list (docs.json). Its first group is START_GROUP: the documents of the
    manifest section of that title, in manifest order, then the hand-written pages of DOCS_PAGES.
    Every other manifest section follows as a group of its own, in manifest order. A document item
    carries its slug, the title the page shows (titles) and the manifest's description; a page item
    carries its route and its title only. Routes and slugs carry no site base and no slashes at
    either end: the site adds both when it writes a link."""
    start = start_section(manifest)

    def doc(page: dict) -> dict:
        description = page.get("description")
        if not description:
            raise core.PublishError(
                f"{page['src']}: its entry in docs/publish.json has no description, which the "
                f"documentation list shows under its title")
        return {"kind": "doc", "slug": page["slug"], "title": titles[page["slug"]],
                "description": description}

    first = [doc(p) for p in start["pages"]] if start is not None else []
    first += [{"kind": "page", "route": route, "title": label} for label, route in DOCS_PAGES]
    groups: List[dict] = [{"title": START_GROUP, "items": first}]
    for section in manifest["sections"]:
        if section is start:
            continue
        groups.append({"title": section["title"], "items": [doc(p) for p in section["pages"]]})
    return {"groups": groups}


def committed_json(root: Path, sha: str, rel: str) -> object:
    try:
        return json.loads(core.committed_text(root, sha, rel))
    except json.JSONDecodeError as e:
        raise core.PublishError(f"{rel} at {sha[:12]} is not valid JSON: {e}")


def stage_site(root: Path, rev: str) -> Dict[str, object]:
    root = root.resolve()
    core.git_check_toplevel(root)
    sha = core.resolve_commit(root, rev)
    data_sources = [core.PLAN_REL.as_posix(), core.LEDGER_REL.as_posix(), core.MANIFEST_REL.as_posix(),
                    core.CITATION_REL.as_posix()]
    if core.git_differs(root, sha, data_sources):
        raise core.PublishError(
            "the plan, the ledger, the manifest or the citation file on disk differs from commit "
            f"{sha[:12]}; commit them first so the site shows one commit's facts")

    manifest = core.load_manifest(root)
    ledger = core.load_ledger(root)
    plan = core.validate_plan(committed_json(root, sha, core.PLAN_REL.as_posix()))
    public = core.ledger_public(root)
    # what the feed needs, read before anything is emptied: a plan or a citation file it cannot read
    # stops staging with the staged site as it was
    events = render_plan.progress_events(plan)
    author = core.citation_author(core.committed_text(root, sha, core.CITATION_REL.as_posix()))
    mapping = core.link_mapping(manifest, "site")
    # the posts are read before anything is emptied: a post the guard or a rule refuses stops
    # staging with the staged site as it was. Their routes join the mapping, so a page can link to one.
    posts = blog.discover(root, sha, manifest=manifest, ledger=ledger, author=author)
    mapping.update(blog.link_mapping(manifest, posts))
    tracked = core.git_tracked(root, rev=sha)
    repo = manifest["repo"]
    pages = core.manifest_pages(manifest)
    slugs = [p["slug"] for p in pages]

    docs_dir = root / DOCS_OUT
    data_dir = root / DATA_OUT
    for d in (docs_dir, data_dir):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    renderer = diagrams.read_renderer(root, sha)
    drawn: Dict[str, Optional[str]] = {}

    def drawing(key: str) -> Optional[str]:
        if key not in drawn:
            drawn[key] = diagrams.read_svg(root, sha, key)
        return drawn[key]

    used_keys: Set[str] = set()
    titles: Dict[str, str] = {}
    for page in pages:
        src = page["src"]
        text = core.published_text(root, src, manifest=manifest, ledger=ledger, rev=sha)
        title, body = split_title(text, src)
        title = page.get("title") or title
        titles[page["slug"]] = title
        description = page.get("description")
        if not description:
            raise core.PublishError(
                f"{src}: its entry in docs/publish.json has no description; the page would show the "
                f"site's general one in search results and link previews (add one sentence of "
                f"{core.DESCRIPTION_MIN} to {core.DESCRIPTION_MAX} characters)")
        body = core.rewrite_links(body, src, mapping, sha, repo, root=root, tracked=tracked)
        body, keys = diagrams.inline_fences(body, src, renderer, drawing, {})
        used_keys.update(keys)
        front = (
            "---\n"
            f"title: {yaml_str(title)}\n"
            f"description: {yaml_str(description)}\n"
            f"editUrl: {yaml_str(f'https://github.com/{repo}/blob/main/{src}')}\n"
            "---\n"
            "<!-- ledger:ignore-file -->\n"
            f"<!-- GENERATED by tools/publish/stage.py from {src} at {sha[:12]}; do not edit -->\n\n"
        )
        target = docs_dir / out_path(page["slug"], slugs)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(front + body, encoding="utf-8")

    for i, post in enumerate(posts):
        prev, nxt = blog.neighbours(posts, i)
        body = core.rewrite_links(post.body, post.src, {**mapping, **blog.link_mapping(manifest, posts, post)},
                                  sha, repo, root=root, tracked=tracked)
        body, keys = diagrams.inline_fences(body, post.src, renderer, drawing, {})
        used_keys.update(keys)
        out_dir = docs_dir / "blog" / post.slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.md").write_text(
            blog.staged_front_matter(manifest, post, prev, nxt, sha) + body.lstrip("\n"), encoding="utf-8")
        for name, data in post.media:
            (out_dir / name).write_bytes(data)

    unused = diagrams.orphans(root, sha, used_keys)
    if unused:
        raise core.PublishError(
            f"{diagrams.DIR_REL}/ holds {len(unused)} drawing(s) no published page uses ("
            f"{', '.join(unused[:3])}{', ...' if len(unused) > 3 else ''}); run `npm run diagrams` in "
            f"website/ to drop them")

    docs_index = build_docs_index(manifest, titles)

    def dump(name: str, obj: object) -> None:
        (data_dir / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
                                     encoding="utf-8")

    dump("plan.json", plan)
    dump("ledger.public.json", public)
    dump("docs.json", docs_index)
    dump("progress.json", {"as_of": plan["as_of"], "timezone": plan["timezone"], "author": author,
                           "events": events})
    dump("blog.json", blog.blog_json(manifest, posts, author))
    dump("stage.json", {"commit": sha, "repo": repo, "pages": len(pages), "posts": len(posts)})
    return {"commit": sha, "pages": len(pages), "posts": len(posts), "diagrams": len(used_keys), "events": len(events)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", choices=["site"], required=True)
    ap.add_argument("--rev", default="HEAD", help="commit to stage from (default: HEAD)")
    ap.add_argument("--root", default=str(core.REPO), help="repository root")
    args = ap.parse_args(argv)
    try:
        res = stage_site(Path(args.root), args.rev)
    except core.PublishError as e:
        print(f"stage: {e}", file=sys.stderr)
        return 1
    print(f"stage: {res['pages']} page(s), {res['posts']} post(s), {res['diagrams']} diagram(s), {res['events']} progress "
          f"event(s) and the site data staged from {res['commit'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
