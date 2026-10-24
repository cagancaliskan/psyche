#!/usr/bin/env python3
"""stage.py — stage the governed documents and the public data for the docs site (D-031).

The site never holds prose of its own. Every page it shows is a document listed in
docs/publish.json, read from a COMMIT by core.published_text (never from disk, so nothing
that changes after the guard has looked can reach a page), with its relative links rewritten
for the site by core.rewrite_links. The data the custom pages draw from — the thesis plan
and the public projection of the ledger — comes from the same commit, and staging refuses
if either file on disk differs from it. So one commit id names everything a build shows.

    python3 tools/publish/stage.py --target site              # stage from HEAD
    python3 tools/publish/stage.py --target site --rev <sha>  # stage from a given commit

Output (both directories are gitignored, and CI fails if a staged copy is ever tracked):

    website/src/content/docs/<slug>.md   or  <slug>/index.md when other pages nest under it
    website/src/data/plan.json           tools/thesis_plan.json, validated
    website/src/data/ledger.public.json  core.ledger_public
    website/src/data/sidebar.json        Starlight sidebar: the custom pages, then the manifest
    website/src/data/stage.json          which commit was staged

Each staged page starts with `<!-- ledger:ignore-file -->`, so a local ledger_check does not
report the copy a second time (the governed source is still checked), and a GENERATED line
naming its source and commit. The output directories are emptied first: a page removed from
the manifest disappears from the site at the next stage.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402

SITE_DIR = Path("website")
DOCS_OUT = SITE_DIR / "src" / "content" / "docs"
DATA_OUT = SITE_DIR / "src" / "data"

# Hand-written pages of the site (website/src/pages/*.astro), listed first in the sidebar.
CUSTOM_PAGES: List[Tuple[str, str]] = [
    ("Home", ""),
    ("Roadmap and gates", "roadmap/"),
    ("Test battery explorer", "battery/"),
    ("Psyche status", "status/"),
]


def split_title(text: str, src: str) -> Tuple[str, str]:
    """The first ATX level-one heading outside fenced code, and the text without it.
    A page with no H1 is refused: Starlight needs a title, and inventing one would be the
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


def committed_json(root: Path, sha: str, rel: str) -> object:
    try:
        return json.loads(core.committed_text(root, sha, rel))
    except json.JSONDecodeError as e:
        raise core.PublishError(f"{rel} at {sha[:12]} is not valid JSON: {e}")


def stage_site(root: Path, rev: str) -> Dict[str, object]:
    root = root.resolve()
    core.git_check_toplevel(root)
    sha = core.resolve_commit(root, rev)
    data_sources = [core.PLAN_REL.as_posix(), core.LEDGER_REL.as_posix(), core.MANIFEST_REL.as_posix()]
    if core.git_differs(root, sha, data_sources):
        raise core.PublishError(
            "the plan, the ledger or the manifest on disk differs from commit "
            f"{sha[:12]}; commit them first so the site shows one commit's facts")

    manifest = core.load_manifest(root)
    ledger = core.load_ledger(root)
    plan = core.validate_plan(committed_json(root, sha, core.PLAN_REL.as_posix()))
    public = core.ledger_public(root)
    mapping = core.link_mapping(manifest, "site")
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

    titles: Dict[str, str] = {}
    for page in pages:
        src = page["src"]
        text = core.published_text(root, src, manifest=manifest, ledger=ledger, rev=sha)
        title, body = split_title(text, src)
        title = page.get("title") or title
        titles[page["slug"]] = title
        body = core.rewrite_links(body, src, mapping, sha, repo, root=root, tracked=tracked)
        front = (
            "---\n"
            f"title: {yaml_str(title)}\n"
            f"editUrl: {yaml_str(f'https://github.com/{repo}/blob/main/{src}')}\n"
            "---\n"
            "<!-- ledger:ignore-file -->\n"
            f"<!-- GENERATED by tools/publish/stage.py from {src} at {sha[:12]}; do not edit -->\n\n"
        )
        target = docs_dir / out_path(page["slug"], slugs)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(front + body, encoding="utf-8")

    # Starlight prefixes the site base onto every sidebar link that has no protocol
    # (utils/navigation.js makeSidebarLink -> formatPath -> pathWithBase), so these links are
    # site-relative and carry no base; adding it here would produce /psyche/psyche/...
    sidebar: List[dict] = [{
        "label": "Start here",
        "items": [{"label": label, "link": "/" + path} for label, path in CUSTOM_PAGES],
    }]
    for section in manifest["sections"]:
        sidebar.append({
            "label": section["title"],
            "items": [{"label": titles[p["slug"]], "slug": p["slug"]} for p in section["pages"]],
        })

    def dump(name: str, obj: object) -> None:
        (data_dir / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
                                     encoding="utf-8")

    dump("plan.json", plan)
    dump("ledger.public.json", public)
    dump("sidebar.json", sidebar)
    dump("stage.json", {"commit": sha, "repo": repo, "pages": len(pages)})
    return {"commit": sha, "pages": len(pages)}


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
    print(f"stage: {res['pages']} page(s) and the site data staged from {res['commit'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
