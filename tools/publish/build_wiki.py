#!/usr/bin/env python3
"""build_wiki.py — generate the GitHub wiki from the governed documents (D-031).

The wiki is a separate git repository that no check in this repository can see, so it is
never edited by hand: every page is generated here from a document listed in
docs/publish.json, read from a COMMIT (core.published_text), with relative links rewritten
to wiki page names or to files pinned at that commit (core.rewrite_links). The workflow
.github/workflows/wiki.yml mirrors the output into the wiki repository, deleting anything
else, so a page edited in the web UI is overwritten at the next run.

    python3 tools/publish/build_wiki.py                      # from HEAD into build/publish/wiki
    python3 tools/publish/build_wiki.py --rev <sha> --out DIR

Pages: Home (the project, the research line's status line and roadmap chart, the page
index), one page per manifest entry under its `wiki` name, Substrate-Status (from the public
projection of the ledger), _Sidebar and _Footer.
Output is deterministic for a given commit. The output directory must be outside the
repository or under its ignored build/ directory, and it is emptied first.

Standard library only.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402
import render_plan  # noqa: E402
from stage import committed_json, split_title  # noqa: E402

DEFAULT_OUT = Path("build") / "publish" / "wiki"

STATUS_ORDER = ["PROVEN", "BUILT-UNVALIDATED", "NO-GO", "DESIGNED"]
STATUS_HEADING = {
    "PROVEN": "Proven",
    "BUILT-UNVALIDATED": "Built; meaning not validated",
    "NO-GO": "Stopped before a graded run",
    "DESIGNED": "Designed, not built",
}


def safe_out(root: Path, out: Path) -> Path:
    out = (root / out).resolve() if not out.is_absolute() else out.resolve()
    try:
        rel = out.relative_to(root)
    except ValueError:
        return out
    if not rel.parts or rel.parts[0] != "build":
        raise core.PublishError(f"refusing to write the wiki to {rel}: use build/ or a path outside the repository")
    return out


def _program_phrase(p: dict) -> str:
    """'paused (since 2026-10-23, decision D-031)', from one public program entry."""
    return f"{p['state']} (since {p['since']}, decision {p['decision']})"


def substrate_status(public: dict) -> str:
    t = public["tests"]
    det = public["determinism"]
    sub = public["program"]["substrate"]
    lines = [
        "# Substrate status",
        "",
        f"> The substrate, stage 1 of Psyche and its foundation, is {_program_phrase(sub)}. "
        "Its tests and checks stay maintained.",
        "",
        f"The captured run has {t['suites']} suites, {t['assertions']:,} assertions and {t['failures']} failures, "
        f"with identical counts on CPython {', '.join(det['interpreters'])} and determinism probed under "
        f"{len(det['hash_seeds'])} hash seeds. The meaning bar is {str(public['meaning_bar']['status']).lower()}.",
        "",
    ]
    bricks = public["bricks"]
    order = STATUS_ORDER + sorted({b["status"] for b in bricks} - set(STATUS_ORDER))
    for status in order:
        group = [b for b in bricks if b["status"] == status]
        if not group:
            continue
        lines += [f"## {STATUS_HEADING.get(status, status.title())} ({len(group)})", "",
                  "| Brick | Name |", "|---|---|"]
        lines += [f"| `{b['id']}` | {render_plan.md(b['name'])} |" for b in group]
        lines.append("")
    return "\n".join(lines)


def build(root: Path, rev: str, out: Path) -> Dict[str, object]:
    root = root.resolve()
    core.git_check_toplevel(root)
    sha = core.resolve_commit(root, rev)
    if core.git_differs(root, sha, [core.PLAN_REL.as_posix(), core.LEDGER_REL.as_posix(),
                                    core.MANIFEST_REL.as_posix()]):
        raise core.PublishError(f"the plan, the ledger or the manifest on disk differs from commit {sha[:12]}")
    out = safe_out(root, out)
    manifest = core.load_manifest(root)
    ledger = core.load_ledger(root)
    plan = core.validate_plan(committed_json(root, sha, core.PLAN_REL.as_posix()))
    rendered = render_plan.render_checked(plan)
    mapping = core.link_mapping(manifest, "wiki")
    tracked = core.git_tracked(root, rev=sha)
    repo = manifest["repo"]
    short = sha[:12]

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    written: List[str] = []

    def write(name: str, text: str) -> None:
        (out / f"{name}.md").write_text(text.rstrip("\n") + "\n", encoding="utf-8")
        written.append(name)

    stamp = f"<!-- generated from {repo}@{short} by tools/publish/build_wiki.py; edit the repository, not the wiki -->\n"
    titles: Dict[str, str] = {}
    for page in core.manifest_pages(manifest):
        text = core.published_text(root, page["src"], manifest=manifest, ledger=ledger, rev=sha)
        title, body = split_title(text, page["src"])
        titles[page["wiki"]] = page.get("title") or title
        body = core.rewrite_links(body, page["src"], mapping, sha, repo, root=root, tracked=tracked)
        write(page["wiki"], stamp + f"# {titles[page['wiki']]}\n\n" + body)

    public = core.ledger_public(root)
    write("Substrate-Status", stamp + substrate_status(public))

    index: List[str] = []
    for section in manifest["sections"]:
        index += [f"## {section['title']}", ""]
        index += [f"- [{titles[p['wiki']]}]({p['wiki']})" for p in section["pages"]]
        index.append("")
    index += ["## Status", "", "- [Substrate status](Substrate-Status)", ""]

    sub, cmap = public["program"]["substrate"], public["program"]["cognitive_map"]
    write("Home", stamp + "\n".join([
        "# Psyche",
        "",
        "Psyche is an open research project building toward artificial general intelligence (AGI) "
        "from original, brain-inspired components. It grows in stages, each built test-first and kept "
        f"as a citable artifact. Stage 1, the substrate, is the foundation; its development is "
        f"{_program_phrase(sub)}. "
        f"Stage 2, spiking cognitive maps, is {_program_phrase(cmap)}.",
        "",
        "This wiki is generated from the repository. The research line's detail stays private until "
        "its release under the disclosure policy.",
        "",
        f"## Current research line: {render_plan.md(plan['line']['title'])}",
        "",
        rendered["status-line"],
        "",
        "## Roadmap",
        "",
        rendered["plan-gantt"],
        "",
        *index,
    ]))
    sidebar = ["**[Home](Home)**", ""]
    for section in manifest["sections"]:
        sidebar += [f"**{section['title']}**", ""]
        sidebar += [f"- [{titles[p['wiki']]}]({p['wiki']})" for p in section["pages"]]
        sidebar.append("")
    sidebar += ["**Status**", "", "- [Substrate status](Substrate-Status)"]
    write("_Sidebar", "\n".join(sidebar))
    write("_Footer", f"Generated from [{repo}@{short}](https://github.com/{repo}/tree/{sha}) by "
                     "`tools/publish/build_wiki.py`. Do not edit the wiki: every run overwrites it. Edit the repository instead.")
    return {"commit": sha, "out": out, "pages": sorted(written)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--root", default=str(core.REPO))
    args = ap.parse_args(argv)
    try:
        res = build(Path(args.root), args.rev, Path(args.out))
    except core.PublishError as e:
        print(f"build_wiki: {e}", file=sys.stderr)
        return 1
    print(f"build_wiki: {len(res['pages'])} page(s) from {res['commit'][:12]} into {res['out']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
