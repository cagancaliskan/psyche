#!/usr/bin/env python3
"""core.py — the governed boundary between this repository and its public surfaces.

D-031 adds public surfaces this repository never had: a docs site and a generated wiki,
both built from repository documents. The danger is not that a page is badly rendered. It
is that a page escapes the checks every document here is held to: ledger_check's C2
(quoted counts), C3 (status labels) and C4 (forbidden claims) govern only the files they
walk, and a copy published from a quarantined, ignored or exempt file is text nothing
governs.

So nothing is published by being listed. A page is published only if this module's guard
accepts it, and the guard accepts only text the checks actually see, as a commit holds it.

What lives here, used by render_plan.py, ci_c2.py and the later site and wiki builders:

  load_manifest(root)        docs/publish.json, validated against a key allowlist; every
                             never_publish entry must be a canonical path. Every JSON file
                             here is parsed by parse_json (on disk through _read_json, as a
                             commit holds it by the caller), which refuses a key given twice
                             in one object (JSON would keep only the last) and a lone
                             surrogate.
  publishable_guard(root, s) refuses a source unless it exists, is Markdown, is not under
                             never_publish, is not one of the files C3 skips by name
                             (c3_exempt_suffixes), lies outside ledger_check's SKIP_DIRS,
                             is in neither quarantine list of tools/ledger.json, carries no
                             ignore-file pragma, is in the tree of the commit being
                             published (HEAD by default) and does not differ from it on
                             disk, byte for byte (never through the index or a filter).
                             Fails CLOSED: if git cannot answer, the answer is no.
  published_text(root, s)    the guard, then the text as the commit holds it: what a
                             publisher publishes, never the disk.
  load_plan / validate_plan  tools/thesis_plan.json, the only source of thesis dates. A
                             strict KEY ALLOWLIST at every level, so no threshold or
                             criterion field can ever exist in the public plan, and a
                             changelog that may only record fields the plan already has.
                             load_plan validates unless told not to.
  ledger_public(root)        the public projection of tools/ledger.json. Never a fact the
                             ledger does not hold, never a field it was not asked for.
  rewrite_links(...)         relative links to manifest pages become their published
                             targets; links to files in the pinned commit become GitHub
                             links to that commit; a dead relative link, or a link shape
                             this module cannot parse, is a hard failure.
  scan_blocks / code_fences  which lines of a Markdown document are code, read the way
                             CommonMark reads them (block quotes, list items, lazy
                             continuation, fenced and indented code, HTML blocks), so a
                             fence opened on a list-item line is seen; render_plan and
                             rewrite_links share it and cannot disagree.

The ledger tool itself (tools/ledger_check.py) is loaded by path through importlib and is
never modified (D-031 §2.8). Its constants are reused rather than copied, and the one rule
that lives only inside a function body (C3's skip-by-name) is read from its source, so the
guard and the checks cannot drift apart.

Every git call runs with the caller's GIT_DIR, GIT_WORK_TREE, GIT_INDEX_FILE and their
relatives removed from the environment, and the guard first proves that `root` is the top
of its own repository: a variable or a parent repository must never answer for it.

Stdlib only, Python 3.10+, in keeping with the project's dependency rule. Plain script
directory: siblings import this file after putting tools/publish on sys.path.
"""

from __future__ import annotations

import ast
import functools
import html
import importlib.util
import json
import os
import posixpath
import re
import stat
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Set, Tuple
from urllib.parse import quote, unquote

HERE = Path(__file__).resolve().parent          # tools/publish
TOOLS = HERE.parent                             # tools
REPO = TOOLS.parent                             # the repository this checkout belongs to

MANIFEST_REL = Path("docs/publish.json")
PLAN_REL = Path("tools/thesis_plan.json")
LEDGER_REL = Path("tools/ledger.json")
LEDGER_CHECK_PATH = TOOLS / "ledger_check.py"


# ─────────────────────────────────────────────────────────────────────────────
# errors
# ─────────────────────────────────────────────────────────────────────────────

class PublishError(Exception):
    """Something would reach a public surface that must not, or the input is unusable."""


class GuardRefusal(PublishError):
    """publishable_guard said no. `reason` is a stable code, so callers and tests can
    assert on WHY without parsing prose:

        path  missing  outside  not-markdown  never-publish  c3-exempt  skip-dir
        quarantined  ignore-file  untracked  modified  git
    """

    def __init__(self, src: str, reason: str, detail: str):
        self.src = src
        self.reason = reason
        self.detail = detail
        super().__init__(f"{src}: refused ({reason}) — {detail}")


class PlanError(PublishError):
    """tools/thesis_plan.json failed validation. Every problem is collected, not only the
    first, so one run shows the whole repair."""

    def __init__(self, problems: List[str]):
        self.problems = list(problems)
        body = "\n  ".join(self.problems)
        super().__init__(f"{PLAN_REL.as_posix()} is invalid ({len(self.problems)} "
                         f"problem(s)):\n  {body}")


# ─────────────────────────────────────────────────────────────────────────────
# the ledger tool, loaded by path
# ─────────────────────────────────────────────────────────────────────────────

_LC_NAME = "_publish_ledger_check"


def ledger_check():
    """Return tools/ledger_check.py as a module, loaded once by path.

    Registered in sys.modules BEFORE it executes: its Finding is a dataclass, and the
    dataclass machinery looks its module up there while the class is being built."""
    mod = sys.modules.get(_LC_NAME)
    if mod is not None:
        return mod
    spec = importlib.util.spec_from_file_location(_LC_NAME, LEDGER_CHECK_PATH)
    if spec is None or spec.loader is None:
        raise PublishError(f"cannot load {LEDGER_CHECK_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_LC_NAME] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(_LC_NAME, None)
        raise
    return mod


# C3 (check_status_vocabulary) skips every path that ENDS WITH one of these, anywhere in
# the tree. The literals live inside the function body, so they cannot be imported; they
# are read from the source instead (c3_exempt_suffixes). The baseline stays in the union,
# so a parse that finds nothing can only make the guard refuse more, never less.
C3_EXEMPT_BASELINE = ("psyche_roadmap.md", "DECISIONS.md")


def c3_suffixes_from_source(source: str) -> Set[str]:
    """Every string passed to `rel.endswith(...)` inside check_status_vocabulary."""
    found: Set[str] = set()
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return found
    for fn in ast.walk(tree):
        if not (isinstance(fn, ast.FunctionDef) and fn.name == "check_status_vocabulary"):
            continue
        for node in ast.walk(fn):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "endswith"
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == "rel"):
                continue
            for arg in node.args:
                for el in (arg.elts if isinstance(arg, ast.Tuple) else [arg]):
                    if isinstance(el, ast.Constant) and isinstance(el.value, str) and el.value:
                        found.add(el.value)
    return found


@functools.lru_cache(maxsize=1)
def c3_exempt_suffixes() -> Tuple[str, ...]:
    try:
        source = LEDGER_CHECK_PATH.read_text(encoding="utf-8")
    except (OSError, ValueError):
        source = ""
    return tuple(sorted(set(C3_EXEMPT_BASELINE) | c3_suffixes_from_source(source)))


# ─────────────────────────────────────────────────────────────────────────────
# small readers
# ─────────────────────────────────────────────────────────────────────────────

class _DuplicateKey(ValueError):
    """A JSON object names the same key twice."""


def _no_duplicates(pairs: List[Tuple[str, object]]) -> dict:
    """object_pairs_hook for json.loads: a key given twice in one object is an error.

    json.loads keeps the LAST value of a repeated key, so every validator here would see
    only that one while the file a reviewer reads still shows the first: a second
    "never_publish": [] would empty the list behind a full-looking one, and a second
    "baseline_date" would ship text in a public file that no check ever read."""
    obj: dict = {}
    for k, v in pairs:
        if k in obj:
            raise _DuplicateKey(f"the key {k!r} appears twice in one object")
        obj[k] = v
    return obj


def unencodable_at(v: object, where: str) -> Optional[str]:
    """Where `v` (keys included) holds a string that cannot be written as UTF-8, or None.

    JSON's escapes can spell a lone surrogate ("\\ud800"), which no UTF-8 file can hold:
    such a value can never be rendered or published, so it is refused where it is read,
    as an invalid input, never discovered later as a crash half way through a write."""
    if isinstance(v, str):
        try:
            v.encode("utf-8")
        except UnicodeEncodeError:
            return where
        return None
    if isinstance(v, list):
        for i, x in enumerate(v):
            hit = unencodable_at(x, f"{where}[{i}]")
            if hit:
                return hit
    elif isinstance(v, dict):
        for k, x in v.items():
            # a key is tested first, so a key that reaches a location string is writable
            hit = unencodable_at(k, f"a key of {where}") or unencodable_at(x, f"{where}.{k}")
            if hit:
                return hit
    return None


def parse_json(text: str, what: str) -> object:
    """JSON text, with every key unique and every string writable as UTF-8, or
    PublishError naming `what` (a file, or a file at a commit).

    The one JSON parser for anything this package validates or publishes. _read_json
    reads a file on disk through it; a publisher that reads a file as a commit holds it
    (core.committed_text) must parse it here too. A plain json.loads there would hand
    validate_plan only the LAST value of a key given twice, so the site would render from
    a plan whose first value, the one a reviewer reads, no check ever saw. Only str is
    accepted: json.loads would also take bytes in UTF-16 or UTF-32, and every JSON file
    here is UTF-8."""
    if not isinstance(text, str):
        raise PublishError(f"{what}: JSON must be given as decoded UTF-8 text, not "
                           f"{type(text).__name__}")
    try:
        data = json.loads(text, object_pairs_hook=_no_duplicates)
    except _DuplicateKey as e:
        raise PublishError(f"{what}: {e}; JSON keeps only the last of them, so the first "
                           f"would never be checked")
    except (ValueError, RecursionError) as e:
        raise PublishError(f"{what} is not valid JSON ({type(e).__name__}: {e})")
    bad = unencodable_at(data, "document")
    if bad:
        raise PublishError(f"{what}: {bad} holds a lone surrogate, which no UTF-8 text can "
                           f"carry")
    return data


def _read_json(path: Path, what: str) -> object:
    """A JSON file as UTF-8, parsed by parse_json (every key unique, every string
    writable as UTF-8)."""
    if not path.is_file():
        raise PublishError(f"{what}: no file at {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, ValueError) as e:
        # ValueError covers UnicodeDecodeError
        raise PublishError(f"{what}: {path} is not readable UTF-8 JSON "
                           f"({type(e).__name__}: {e})")
    return parse_json(text, f"{what}: {path}")


def load_ledger(root) -> dict:
    led = _read_json(Path(root) / LEDGER_REL, "the ledger")
    if not isinstance(led, dict):
        raise PublishError(f"{LEDGER_REL.as_posix()} is not a JSON object")
    return led


def canonical_rel(src) -> str:
    """A repository-relative POSIX path in canonical form, or GuardRefusal('path').

    Canonical means: relative, forward slashes, no '.', '..' or empty segments. A path
    that needs normalising is refused rather than normalised, because two spellings of
    one path are two chances for a prefix rule to miss."""
    if not isinstance(src, str) or not src:
        raise GuardRefusal(repr(src), "path", "a source must be a non-empty string")
    if "\\" in src or "\0" in src:
        raise GuardRefusal(src, "path", "backslashes and NUL are not allowed")
    if src.startswith("/") or re.match(r"^[A-Za-z]:", src):
        raise GuardRefusal(src, "path", "absolute paths are not allowed")
    parts = src.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise GuardRefusal(src, "path", "the path must be canonical: no '.', '..' or "
                                        "empty segments, no trailing slash")
    return src


def _prefix_hit(rel: str, entries: Iterable[str]) -> Optional[str]:
    """ledger_check's own prefix rule (`rel.startswith(q) or rel == q.rstrip('/')`),
    applied case-insensitively. Case-folding can only make a refusal MORE likely, which is
    the safe direction on a case-insensitive filesystem. Used for never_publish, whose
    entries manifest_problems has already proved canonical and non-empty."""
    low = rel.casefold()
    for e in entries:
        if not isinstance(e, str) or not e:
            continue
        q = e.casefold()
        if low.startswith(q) or low == q.rstrip("/"):
            return e
    return None


_MISSING = object()


def _quarantine_hit(rel: str, entries: object) -> Optional[str]:
    """ledger_check's rule for a quarantine list, failing closed wherever a looser copy
    would let text out that the check never read.

    ledger_check tests `rel.startswith(q)` for every entry: an empty entry is a prefix of
    EVERY path, so it quarantines everything, and here it does too. A non-string entry, a
    null list or a value that is not a list would crash the check or make it iterate
    something else; here each of those quarantines everything, never nothing. An absent
    key is ledger_check's default, the empty list."""
    if entries is _MISSING:
        return None
    if not isinstance(entries, list):
        return f"<malformed {type(entries).__name__}: quarantines everything>"
    for e in entries:
        if not isinstance(e, str) or not e:
            return f"<entry {e!r}: quarantines everything>"
        hit = _prefix_hit(rel, [e])
        if hit:
            return hit
    return None


def _skip_dir_hit(rel: str, skip_dirs: Iterable[str]) -> Optional[str]:
    """ledger_check.walk_markdown's two SKIP_DIRS rules: a multi-segment entry
    ('.claude/worktrees') is a prefix, a single name excludes any path component."""
    parts = rel.split("/")[:-1]
    for d in sorted(skip_dirs):
        if rel == d or rel.startswith(d.rstrip("/") + "/"):
            return d
        if d in parts:
            return d
    return None


# ─────────────────────────────────────────────────────────────────────────────
# git, with nothing inherited that could make it answer for another repository
# ─────────────────────────────────────────────────────────────────────────────

# Each of these redirects `git -C root` to some other repository, index or object store,
# or changes how a pathspec is read. A hook, a worktree or a hostile caller can set them;
# the guard's answer must be about `root` and nothing else.
GIT_ENV_DROP = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_NAMESPACE",
                "GIT_PREFIX", "GIT_LITERAL_PATHSPECS", "GIT_GLOB_PATHSPECS",
                "GIT_NOGLOB_PATHSPECS", "GIT_ICASE_PATHSPECS")
REV_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./^~@{}-]*$")


def git_env() -> Dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in GIT_ENV_DROP}


def _git_run(root, args: List[str]) -> subprocess.CompletedProcess:
    """Literal pathspecs, so a '*' or '[' in a path is a character and not a glob."""
    cmd = ["git", "--literal-pathspecs", "-C", str(root), *args]
    try:
        return subprocess.run(cmd, capture_output=True, timeout=60, env=git_env())
    except (OSError, subprocess.SubprocessError) as e:
        raise PublishError(f"git is unavailable ({type(e).__name__}: {e})")


def _git_out(root, args: List[str]) -> str:
    r = _git_run(root, args)
    if r.returncode != 0:
        msg = r.stderr.decode("utf-8", "replace").strip().splitlines()
        raise PublishError(f"git {args[0]} failed under {root}: "
                           f"{msg[0] if msg else 'exit ' + str(r.returncode)}")
    return r.stdout.decode("utf-8", "surrogateescape")


def git_lines(root, args: List[str]) -> List[str]:
    """The NUL-separated output of a `git ... -z` command, as a list. No quoting."""
    return [p for p in _git_out(root, args).split("\0") if p]


def git_check_toplevel(root) -> None:
    """PublishError unless `root` is the top level of its own git repository. Without
    this, a plain directory inside some other repository would be answered for by that
    repository. Compared with samefile, so no path spelling (symlinks, Unicode
    normalisation) can make two names for one directory disagree."""
    top = _git_out(root, ["rev-parse", "--show-toplevel"]).strip()
    try:
        same = bool(top) and os.path.samefile(top, str(root))
    except OSError:
        same = False
    if not same:
        raise PublishError(f"{root} is not the top level of a git repository "
                           f"(git answers for {top or 'nothing'})")


def resolve_commit(root, rev: str) -> str:
    """The full commit id `rev` names in `root`, or PublishError. A revision may not begin
    with '-', so it can never be read as an option."""
    if not (isinstance(rev, str) and REV_RE.match(rev)):
        raise PublishError(f"revision {rev!r} is not a plain revision name")
    sha = _git_out(root, ["rev-parse", "--verify", "--quiet", rev + "^{commit}"]).strip()
    if not re.match(r"^[0-9a-f]{40,64}$", sha):
        raise PublishError(f"{rev!r} names no commit under {root}")
    return sha


def git_tracked(root, paths: Optional[List[str]] = None, *,
                rev: Optional[str] = None) -> Set[str]:
    """The set of paths (relative to root) among `paths`, or all paths, that git holds.

    rev=None asks the INDEX (`git ls-files`): staged counts, committed or not. Given a
    revision, it asks that COMMIT's tree (`git ls-tree -r`): only what a commit holds.
    Raises PublishError if git cannot answer, or if root is not the top of its own
    repository — the caller must then refuse, never assume."""
    if paths is not None and not paths:
        return set()
    git_check_toplevel(root)
    if rev is None:
        args = ["ls-files", "-z"]
    else:
        args = ["ls-tree", "-r", "-z", "--name-only", resolve_commit(root, rev)]
    if paths is not None:
        args += ["--", *paths]
    return set(git_lines(root, args))


def git_entry(root, rev: str, path: str) -> Optional[Tuple[str, bytes]]:
    """(mode, blob bytes) of `path` in commit `rev`, or None when the commit does not
    hold it as a file or a symbolic link. Read from the object store: `git ls-tree` and
    `git cat-file blob` consult neither the index nor any filter."""
    sha = resolve_commit(root, rev)
    found = [e for e in git_lines(root, ["ls-tree", "-z", sha, "--", path])
             if e.partition("\t")[2] == path]
    if len(found) != 1:
        return None
    mode, kind, oid = found[0].partition("\t")[0].split(" ")
    if kind != "blob" or mode not in ("100644", "100755", "120000"):
        return None
    r = _git_run(root, ["cat-file", "blob", oid])
    if r.returncode != 0:
        raise PublishError(f"git cat-file failed under {root} for {path}")
    return mode, r.stdout


def git_differs(root, rev: str, paths: List[str]) -> bool:
    """True if any of `paths` on disk differs, byte for byte, from what commit `rev`
    holds: the file's bytes against the blob's, a symbolic link's target against the
    link blob's, and a link where the commit holds a file (or the reverse) differs.

    `git diff` is NOT used: it compares through the index, so a file flagged
    skip-worktree or assume-unchanged is never read, and through the repository's clean
    filters, which are programs the repository's configuration names. Here neither the
    index nor any filter, driver or textconv is consulted, so no flag can make an edited
    file look committed and no repository configuration runs a program."""
    root = Path(root)
    for rel in paths:
        entry = git_entry(root, rev, rel)
        if entry is None:
            return True
        mode, blob = entry
        p = root / rel
        try:
            st = p.lstat()
            if mode == "120000":
                if not stat.S_ISLNK(st.st_mode) or os.fsencode(os.readlink(p)) != blob:
                    return True
            elif not stat.S_ISREG(st.st_mode) or p.read_bytes() != blob:
                return True
        except OSError:
            return True
    return False


def committed_text(root, rev: str, rel: str) -> str:
    """The UTF-8 text of `rel` as commit `rev` holds it. A publisher reads THIS, never the
    disk: what the commit holds is what was reviewed."""
    entry = git_entry(root, rev, rel)
    if entry is None or entry[0] == "120000":
        raise PublishError(f"{rel}: commit {rev} holds no regular file at that path")
    try:
        return entry[1].decode("utf-8")
    except UnicodeDecodeError as e:
        raise PublishError(f"{rel}: not UTF-8 in commit {rev} ({e})")


# ─────────────────────────────────────────────────────────────────────────────
# the manifest
# ─────────────────────────────────────────────────────────────────────────────

MANIFEST_KEYS = {"site_base", "repo", "sections", "never_publish"}
MANIFEST_OPTIONAL = {"_README"}
SECTION_KEYS = {"title", "pages"}
PAGE_KEYS = {"src", "slug", "wiki"}
PAGE_OPTIONAL = {"title"}
RESERVED_WIKI = {"home", "_sidebar", "_footer"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*$")
WIKI_RE = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def manifest_problems(m: object) -> List[str]:
    out: List[str] = []
    if not isinstance(m, dict):
        return ["the manifest is not a JSON object"]
    bad = unencodable_at(m, "manifest")
    if bad:
        out.append(f"{bad} holds a lone surrogate, which no UTF-8 text (and no path) can "
                   f"carry")
    _keyset(m, "manifest", MANIFEST_KEYS, MANIFEST_OPTIONAL, out)
    base = m.get("site_base")
    if not (isinstance(base, str) and base.startswith("/") and base.endswith("/")):
        out.append("site_base must be a path that starts and ends with '/'")
    if not (isinstance(m.get("repo"), str) and REPO_RE.match(m["repo"])):
        out.append("repo must be 'owner/name'")
    if "_README" in m and not _str_list(m["_README"]):
        out.append("_README must be a list of strings")
    never = m.get("never_publish")
    if not (isinstance(never, list) and never):
        out.append("never_publish must be a non-empty list of canonical paths")
    else:
        # A prefix that is spelled '/docs/x/', './docs/x/' or 'docs\\x\\' matches nothing,
        # which would silently switch that protection off. Only the canonical spelling
        # (with at most one trailing '/' for a directory) is accepted.
        for i, e in enumerate(never):
            if not (isinstance(e, str) and e):
                out.append(f"never_publish[{i}] must be a non-empty string")
                continue
            try:
                canonical_rel(e[:-1] if e.endswith("/") else e)
            except GuardRefusal as g:
                out.append(f"never_publish[{i}] = {e!r} is not canonical: {g.detail}")

    sections = m.get("sections")
    if not (isinstance(sections, list) and sections):
        out.append("sections must be a non-empty list")
        return out
    seen: Dict[str, Set[str]] = {"src": set(), "slug": set(), "wiki": set()}
    for si, sec in enumerate(sections):
        where = f"sections[{si}]"
        if not isinstance(sec, dict):
            out.append(f"{where} is not an object")
            continue
        _keyset(sec, where, SECTION_KEYS, set(), out)
        if not (isinstance(sec.get("title"), str) and sec["title"].strip()):
            out.append(f"{where}.title must be a non-empty string")
        pages = sec.get("pages")
        if not (isinstance(pages, list) and pages):
            out.append(f"{where}.pages must be a non-empty list")
            continue
        for pi, page in enumerate(pages):
            pw = f"{where}.pages[{pi}]"
            if not isinstance(page, dict):
                out.append(f"{pw} is not an object")
                continue
            _keyset(page, pw, PAGE_KEYS, PAGE_OPTIONAL, out)
            src, slug, wiki = page.get("src"), page.get("slug"), page.get("wiki")
            try:
                canonical_rel(src)
            except GuardRefusal as e:
                out.append(f"{pw}.src: {e.detail}")
            if not (isinstance(slug, str) and SLUG_RE.match(slug)):
                out.append(f"{pw}.slug must be lowercase words joined by '-' and '/'")
            if not (isinstance(wiki, str) and WIKI_RE.match(wiki)):
                out.append(f"{pw}.wiki must be letters and digits joined by '-'")
            elif wiki.casefold() in RESERVED_WIKI:
                out.append(f"{pw}.wiki {wiki!r} is a reserved wiki page name")
            if "title" in page and not (isinstance(page["title"], str) and page["title"].strip()):
                out.append(f"{pw}.title must be a non-empty string")
            for key, val in (("src", src), ("slug", slug), ("wiki", wiki)):
                if not isinstance(val, str):
                    continue
                folded = val.casefold()
                if folded in seen[key]:
                    out.append(f"{pw}.{key} {val!r} is listed twice")
                seen[key].add(folded)
    return out


def load_manifest(root) -> dict:
    m = _read_json(Path(root) / MANIFEST_REL, "the publication manifest")
    problems = manifest_problems(m)
    if problems:
        raise PublishError(f"{MANIFEST_REL.as_posix()} is invalid:\n  " + "\n  ".join(problems))
    return m  # type: ignore[return-value]


def manifest_pages(manifest: dict) -> List[dict]:
    """Every page, in manifest order (sections first to last)."""
    return [p for sec in manifest["sections"] for p in sec["pages"]]


def site_route(manifest: dict, page: dict) -> str:
    return f"{manifest['site_base']}{page['slug']}/"


def link_mapping(manifest: dict, target: str) -> Dict[str, str]:
    """src -> published target, for rewrite_links. target is 'site' or 'wiki'."""
    if target == "site":
        return {p["src"]: site_route(manifest, p) for p in manifest_pages(manifest)}
    if target == "wiki":
        return {p["src"]: p["wiki"] for p in manifest_pages(manifest)}
    raise PublishError(f"unknown link target {target!r} (expected 'site' or 'wiki')")


def never_publish_hit(manifest: dict, src: str) -> Optional[str]:
    return _prefix_hit(src, manifest.get("never_publish") or [])


# ─────────────────────────────────────────────────────────────────────────────
# the guard
# ─────────────────────────────────────────────────────────────────────────────

def publishable_guard(root, src, *, manifest: Optional[dict] = None,
                      ledger: Optional[dict] = None, rev: Optional[str] = "HEAD") -> str:
    """Return the canonical relative path of `src` if it may be published; otherwise
    raise GuardRefusal. Checked in a fixed order, so the reported reason is stable.

    A symlink is judged twice, by its own path and by the path it resolves to, so a link
    cannot carry a quarantined file out under a governed name.

    `rev` is the commit being published (HEAD by default): the file must be in that
    commit's tree and must not differ from it on disk, so the text read here is text a
    commit holds. rev=None relaxes this to the git index and the working tree, for a
    local preview only; nothing built that way may be pushed."""
    root = Path(root).resolve()
    rel = canonical_rel(src)
    if manifest is None:
        manifest = load_manifest(root)
    else:
        problems = manifest_problems(manifest)
        if problems:
            raise PublishError("the manifest given to the guard is invalid:\n  "
                               + "\n  ".join(problems))
    if ledger is None:
        ledger = load_ledger(root)
    elif not isinstance(ledger, dict):
        raise PublishError("the ledger given to the guard is not an object")
    lc = ledger_check()

    path = root / rel
    if not path.is_file():
        raise GuardRefusal(rel, "missing", "no such file")
    try:
        real_rel = path.resolve().relative_to(root).as_posix()
    except ValueError:
        raise GuardRefusal(rel, "outside", "the path resolves outside the repository")

    exempt = [s.casefold() for s in c3_exempt_suffixes()]
    for cand in dict.fromkeys((rel, real_rel)):
        if not cand.endswith(".md"):
            raise GuardRefusal(rel, "not-markdown",
                               f"{cand} is not Markdown; only .md is governed by C2/C3/C4")
        hit = never_publish_hit(manifest, cand)
        if hit:
            raise GuardRefusal(rel, "never-publish", f"{cand} is under never_publish ({hit})")
        low = cand.casefold()
        for suffix in exempt:
            if low.endswith(suffix):
                raise GuardRefusal(rel, "c3-exempt",
                                   f"{cand} ends with {suffix!r}, a name ledger_check's C3 "
                                   f"never reads, so its status labels are ungoverned")
        hit = _skip_dir_hit(cand, lc.SKIP_DIRS)
        if hit:
            raise GuardRefusal(rel, "skip-dir",
                               f"{cand} is under {hit}, which ledger_check never walks")
        for key in ("claim_quarantine_paths", "count_quarantine_paths"):
            hit = _quarantine_hit(cand, ledger.get(key, _MISSING))
            if hit:
                raise GuardRefusal(rel, "quarantined",
                                   f"{cand} is in the ledger's {key} ({hit})")

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise GuardRefusal(rel, "missing", f"unreadable ({type(e).__name__})")
    if lc.IGNORE_FILE in text:
        raise GuardRefusal(rel, "ignore-file",
                           "the file opts out of ledger_check, so nothing governs its text")

    wanted = list(dict.fromkeys((rel, real_rel)))
    where = f"the tree of commit {rev}" if rev is not None else "the git index"
    try:
        tracked = git_tracked(root, wanted, rev=rev)
    except PublishError as e:
        raise GuardRefusal(rel, "git", f"cannot prove the file is in {where}: {e}")
    for cand in wanted:
        if cand not in tracked:
            raise GuardRefusal(rel, "untracked",
                               f"{cand} is not in {where}, so no reviewed commit holds it")
    if rev is not None:
        try:
            differs = git_differs(root, rev, wanted)
        except PublishError as e:
            raise GuardRefusal(rel, "git", f"cannot compare the file with {rev}: {e}")
        if differs:
            raise GuardRefusal(rel, "modified",
                               f"{rel} on disk differs from {rev}: the text that would be "
                               f"published is not the text the commit holds")
    return rel


def published_text(root, src, *, manifest: Optional[dict] = None,
                   ledger: Optional[dict] = None, rev: Optional[str] = "HEAD") -> str:
    """The text a publisher may publish for `src`: refused by the guard, or read from
    commit `rev` (never from disk, so nothing that changes after the guard has looked can
    reach a page). rev=None reads the disk, for a local preview only."""
    rel = publishable_guard(root, src, manifest=manifest, ledger=ledger, rev=rev)
    root = Path(root).resolve()
    real = (root / rel).resolve().relative_to(root).as_posix()
    if rev is None:
        return (root / real).read_text(encoding="utf-8")
    return committed_text(root, rev, real)


# ─────────────────────────────────────────────────────────────────────────────
# the thesis plan
# ─────────────────────────────────────────────────────────────────────────────
#
# THE ALLOWLIST IS THE POINT. The plan is public; the criteria behind it are not. A field
# the validator does not know cannot exist, so a threshold cannot be added by accident,
# and adding a new kind of field is a change to this file, which is reviewed. The same
# holds for VALUES that could carry a field in disguise: the changelog may only record
# fields the plan already has, with values of that field's type.

TOP_KEYS = {"schema_version", "as_of", "timezone", "thesis", "vocabulary", "phases",
            "gates", "deadlines", "layers", "commitments", "changelog"}
TOP_OPTIONAL = {"_README"}
THESIS_KEYS = {"title", "short_name", "level"}
VOCAB_KEYS = {"phase", "gate", "deadline"}
PHASE_KEYS = {"id", "title", "start", "end", "gate", "status", "outputs"}
PHASE_OPTIONAL = {"start_rule", "end_rule"}
GATE_KEYS = {"id", "title", "baseline_date", "date", "status", "question", "if_missed"}
GATE_OPTIONAL = {"date_rule"}
DEADLINE_KEYS = {"id", "title", "due", "estimate", "status"}
LAYER_KEYS = {"id", "title", "summary"}
COMMITMENT_KEYS = {"id", "date", "subject", "sha256", "reveal"}
CHANGELOG_KEYS = {"date", "item", "field", "from", "to", "reason", "ref"}

SCHEMA_VERSION = 1

# The status words render_plan gives a meaning to, shared so the two files cannot drift.
PHASE_ACTIVE = "active"      # the status line's "Now", the gantt's active bar
PHASE_DONE = "done"          # the gantt's done bar
GATE_UPCOMING = "upcoming"   # the status line's "Next gate"
GATE_DECIDED = "decided"     # a gantt milestone drawn as done
ACTIVE = PHASE_ACTIVE        # kept for callers of the earlier name
# A vocabulary may use only words the renderer knows how to treat, and must hold the ones
# its statements depend on: a plan whose gates are all 'open' would otherwise render
# "Next gate: none upcoming" and validate cleanly.
VOCAB_KNOWN = {"phase": ("planned", PHASE_ACTIVE, PHASE_DONE),
               "gate": (GATE_UPCOMING, GATE_DECIDED),
               "deadline": ("upcoming", "met", "missed")}
VOCAB_REQUIRED = {"phase": (PHASE_ACTIVE,), "gate": (GATE_UPCOMING, GATE_DECIDED),
                  "deadline": ()}

# What a changelog entry may record about each kind of item, and the type of its
# from/to values. A field that is not here cannot be logged, so no criterion can be
# published through a changelog value either.
CHANGE_FIELDS: Dict[str, Dict[str, str]] = {
    "phase": {"start": "date", "end": "date", "start_rule": "text", "end_rule": "text",
              "status": "status", "title": "text", "gate": "gate"},
    "gate": {"date": "date", "baseline_date": "date", "date_rule": "text",
             "status": "status", "title": "text"},
    "deadline": {"due": "date", "estimate": "text", "status": "status", "title": "text"},
    "layer": {"title": "text", "summary": "text"},
    "commitment": {"reveal": "text"},
}
ALL_CHANGE_FIELDS = sorted({f for fields in CHANGE_FIELDS.values() for f in fields})

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# No plan date may be later than this. render_plan draws open ends a margin past the
# plan's latest date (and one margin per undated phase after that), and date arithmetic
# beyond 9999-12-31 raises; nine centuries of room keeps every drawing representable.
LATEST_DATE = date(9000, 12, 31)
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
WORD_RE = re.compile(r"^[a-z][a-z-]*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TZ_RE = re.compile(r"^(?:UTC|[A-Za-z_]+(?:/[A-Za-z0-9_+-]+)+)$")


def _keyset(obj: dict, where: str, required: Set[str], optional: Set[str],
            out: List[str]) -> None:
    for k in sorted(set(obj) - required - optional):
        out.append(f"{where}: unknown key {k!r} (the plan uses a key allowlist)")
    for k in sorted(required - set(obj)):
        out.append(f"{where}: missing key {k!r}")


def _str_list(v: object) -> bool:
    return isinstance(v, list) and all(isinstance(s, str) for s in v)


def _nonempty_str(v: object) -> bool:
    return isinstance(v, str) and bool(v.strip())


def parse_iso_date(v: object) -> Optional[date]:
    """A strict YYYY-MM-DD calendar date, or None. date.fromisoformat alone is too lenient
    on 3.11+ (it accepts '20261023'), so the shape is checked first."""
    if not isinstance(v, str) or not DATE_RE.match(v):
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


def _date_field(obj: dict, key: str, where: str, out: List[str], *,
                nullable: bool) -> Optional[date]:
    v = obj.get(key)
    if v is None:
        if not nullable and key in obj:
            out.append(f"{where}.{key} may not be null")
        return None
    d = parse_iso_date(v)
    if d is None:
        out.append(f"{where}.{key} = {v!r} is not an ISO date (YYYY-MM-DD)")
    elif d > LATEST_DATE:
        out.append(f"{where}.{key} = {v!r} is after {LATEST_DATE.isoformat()}; the gantt "
                   f"draws open ends past the plan's latest date, and a calendar ends at "
                   f"9999-12-31")
        return None
    return d


def _fixed_or_rule(obj: dict, key: str, rule: str, where: str, out: List[str]) -> Optional[date]:
    """A date OR a rule, never both and never neither: an open date must say why."""
    d = _date_field(obj, key, where, out, nullable=True)
    has_rule = rule in obj
    if has_rule and not _nonempty_str(obj[rule]):
        out.append(f"{where}.{rule} must be a non-empty string")
    if obj.get(key) is None and key in obj and not has_rule:
        out.append(f"{where}.{key} is null without a {rule}")
    if obj.get(key) is not None and has_rule:
        out.append(f"{where}: {rule} is given although {key} is fixed")
    return d


def _status_labels() -> List[str]:
    lc = ledger_check()
    return sorted(set(lc.BUILD_STATUS_ALIASES) | set(lc.MEANING_VERDICTS), key=len, reverse=True)


def _walk_strings(v: object, where: str) -> Iterable[Tuple[str, str]]:
    if isinstance(v, str):
        yield where, v
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from _walk_strings(x, f"{where}[{i}]")
    elif isinstance(v, dict):
        for k, x in v.items():
            yield from _walk_strings(x, f"{where}.{k}")


def _records(plan: dict, key: str, required: Set[str], optional: Set[str],
             out: List[str], *, nonempty: bool = False) -> List[Tuple[str, dict]]:
    v = plan.get(key)
    if not isinstance(v, list):
        if key in plan:
            out.append(f"{key} must be a list")
        return []
    if nonempty and not v:
        out.append(f"{key} must not be empty")
    recs: List[Tuple[str, dict]] = []
    for i, r in enumerate(v):
        where = f"{key}[{i}]"
        if not isinstance(r, dict):
            out.append(f"{where} is not an object")
            continue
        _keyset(r, where, required, optional, out)
        recs.append((where, r))
    return recs


def _ids(recs: List[Tuple[str, dict]], kind: str, out: List[str]) -> List[str]:
    ids: List[str] = []
    for where, r in recs:
        if "id" not in r:
            continue
        i = r.get("id")
        if not (isinstance(i, str) and ID_RE.match(i)):
            out.append(f"{where}.id = {i!r} must be letters, digits, '-' or '_'")
            continue
        if i in ids:
            out.append(f"{where}.id {i!r} is a duplicate {kind} id")
        ids.append(i)
    return ids


def _texts(r: dict, where: str, keys: Iterable[str], out: List[str], *,
           nullable: Iterable[str] = ()) -> None:
    for k in keys:
        if k not in r:
            continue
        if r[k] is None and k in nullable:
            continue
        if not _nonempty_str(r[k]):
            out.append(f"{where}.{k} must be a non-empty string")


def plan_problems(plan: object) -> List[str]:
    """Every reason the plan is invalid; [] when it is valid. Any input, however
    malformed, yields a list: a value of the wrong type is a problem, never a crash."""
    out: List[str] = []
    if not isinstance(plan, dict):
        return ["the plan is not a JSON object"]
    # A plan that holds a lone surrogate validates in every other respect and can never be
    # written: --check would call it "stale" (exit 1) and --write would crash while
    # staging. It is an unusable input, so it is a problem here (exit 2).
    bad = unencodable_at(plan, "plan")
    if bad:
        out.append(f"{bad} holds a lone surrogate, which no UTF-8 document can carry")
    _keyset(plan, "plan", TOP_KEYS, TOP_OPTIONAL, out)

    if "_README" in plan and not _str_list(plan["_README"]):
        out.append("_README must be a list of strings")
    sv = plan.get("schema_version")
    if "schema_version" in plan and not (type(sv) is int and sv == SCHEMA_VERSION):
        out.append(f"schema_version must be the integer {SCHEMA_VERSION}")
    if "as_of" in plan:
        _date_field(plan, "as_of", "plan", out, nullable=False)
    if "timezone" in plan and not (isinstance(plan["timezone"], str)
                                   and TZ_RE.match(plan["timezone"])):
        out.append("timezone must be an IANA zone name such as Area/City")

    thesis = plan.get("thesis")
    if "thesis" in plan:
        if isinstance(thesis, dict):
            _keyset(thesis, "thesis", THESIS_KEYS, set(), out)
            _texts(thesis, "thesis", THESIS_KEYS, out)
        else:
            out.append("thesis must be an object")

    vocab: Dict[str, List[str]] = {}
    v = plan.get("vocabulary")
    if "vocabulary" in plan:
        if isinstance(v, dict):
            _keyset(v, "vocabulary", VOCAB_KEYS, set(), out)
            for k in sorted(VOCAB_KEYS & set(v)):
                words = v[k]
                if not (isinstance(words, list) and words
                        and all(isinstance(w, str) and WORD_RE.match(w) for w in words)):
                    out.append(f"vocabulary.{k} must be a non-empty list of lowercase words")
                    continue
                if len(set(words)) != len(words):
                    out.append(f"vocabulary.{k} lists a word twice")
                unknown = [w for w in words if w not in VOCAB_KNOWN[k]]
                if unknown:
                    out.append(f"vocabulary.{k} uses {unknown}, which render_plan gives no "
                               f"meaning to (known: {list(VOCAB_KNOWN[k])})")
                lacking = [w for w in VOCAB_REQUIRED[k] if w not in words]
                if lacking:
                    out.append(f"vocabulary.{k} lacks {lacking}, which render_plan's "
                               f"statements depend on")
                vocab[k] = list(words)
        else:
            out.append("vocabulary must be an object")

    phases = _records(plan, "phases", PHASE_KEYS, PHASE_OPTIONAL, out, nonempty=True)
    gates = _records(plan, "gates", GATE_KEYS, GATE_OPTIONAL, out)
    deadlines = _records(plan, "deadlines", DEADLINE_KEYS, set(), out)
    layers = _records(plan, "layers", LAYER_KEYS, set(), out)
    commitments = _records(plan, "commitments", COMMITMENT_KEYS, set(), out)
    changelog = _records(plan, "changelog", CHANGELOG_KEYS, set(), out)

    phase_ids = _ids(phases, "phase", out)
    gate_ids = _ids(gates, "gate", out)
    deadline_ids = _ids(deadlines, "deadline", out)
    layer_ids = _ids(layers, "layer", out)
    commitment_ids = _ids(commitments, "commitment", out)

    def status(where: str, r: dict, kind: str) -> None:
        if "status" not in r:
            return
        if kind not in vocab:
            return  # the vocabulary problem is already reported
        s = r["status"]
        if not (isinstance(s, str) and s in vocab[kind]):
            out.append(f"{where}.status = {s!r} is not in vocabulary.{kind} {vocab[kind]}")

    # gates first: phases are checked against their dates -----------------------
    moves: Dict[str, List[dict]] = {}
    for _, c in changelog:
        if c.get("field") == "date" and isinstance(c.get("item"), str):
            moves.setdefault(c["item"], []).append(c)
    gate_date: Dict[str, date] = {}
    gate_order: Dict[str, int] = {}
    latest: Optional[Tuple[str, date]] = None
    for gi, (where, g) in enumerate(gates):
        _texts(g, where, ("title", "question", "if_missed"), out)
        _date_field(g, "baseline_date", where, out, nullable=True)
        d = _fixed_or_rule(g, "date", "date_rule", where, out)
        status(where, g, "gate")
        gid = g.get("id")
        if isinstance(gid, str):
            gate_order.setdefault(gid, gi)
            if d is not None:
                gate_date.setdefault(gid, d)
        # Dated gates come in date order: the gate flow, "Next gate" and the gantt all
        # read gates[] in list order, and a list that disagrees with its dates misleads.
        if d is not None:
            if latest is not None and d < latest[1]:
                out.append(f"gates are out of order: {where} is dated {d.isoformat()}, "
                           f"before {latest[0]} ({latest[1].isoformat()})")
            if latest is None or d >= latest[1]:
                latest = (where, d)
        if "date" in g and "baseline_date" in g and g["date"] != g["baseline_date"]:
            # an id that is not a string is already reported by _ids, and cannot key a move
            entries = moves.get(gid, []) if isinstance(gid, str) else []
            if not any(c.get("to") == g["date"] for c in entries):
                out.append(f"{where}: date {g['date']!r} differs from baseline_date "
                           f"{g['baseline_date']!r} with no changelog entry "
                           f"(item {gid!r}, field 'date', to {g['date']!r})")

    # phases ------------------------------------------------------------------
    spans: List[Tuple[str, Optional[date], Optional[date]]] = []
    active = []
    reached: Optional[Tuple[str, str, int]] = None
    for where, p in phases:
        _texts(p, where, ("title",), out)
        start = _fixed_or_rule(p, "start", "start_rule", where, out)
        end = _fixed_or_rule(p, "end", "end_rule", where, out)
        if start and end and start > end:
            out.append(f"{where}: start {p['start']} is after end {p['end']}")
        g = p.get("gate")
        if "gate" in p and g is not None and not isinstance(g, str):
            out.append(f"{where}.gate must be a gate id or null")
        elif isinstance(g, str) and g not in gate_ids:
            out.append(f"{where}.gate = {g!r} names no gate in gates[]")
        elif isinstance(g, str):
            if start and g in gate_date and gate_date[g] < start:
                out.append(f"{where}: its gate {g} is dated {gate_date[g].isoformat()}, "
                           f"before the phase starts ({start.isoformat()})")
            # phases reach the gates in the order gates[] lists them
            idx = gate_order.get(g)
            if idx is not None:
                if reached is not None and idx < reached[2]:
                    out.append(f"{where}.gate = {g!r} comes before gate {reached[1]!r} "
                               f"(reached by {reached[0]}) in gates[]; phases must reach "
                               f"the gates in the order gates[] lists them")
                if reached is None or idx >= reached[2]:
                    reached = (where, g, idx)
        status(where, p, "phase")
        if p.get("status") == PHASE_ACTIVE:
            active.append(p.get("id"))
        if "outputs" in p and not (isinstance(p["outputs"], list)
                                   and all(_nonempty_str(o) for o in p["outputs"])):
            out.append(f"{where}.outputs must be a list of non-empty strings")
        spans.append((where, start, end))
    if len(active) > 1:
        out.append(f"at most one phase may be {PHASE_ACTIVE!r}; these are: {active}")
    # Ordered in list order: every known date of a later phase is on or after every known
    # date of an earlier one. Pairwise, not just neighbours, so an undated phase in between
    # hides nothing, and every pairing of start and end is compared, so a phase with an
    # undated start cannot hide a fixed end. A shared boundary day is allowed.
    for i in range(len(spans)):
        wi, si, ei = spans[i]
        for j in range(i + 1, len(spans)):
            wj, sj, ej = spans[j]
            if si and sj and sj < si:
                out.append(f"phases are out of order: {wj} starts before {wi} starts")
            if ei and sj and sj < ei:
                out.append(f"phases overlap: {wj} starts before {wi} ends")
            if si and ej and ej < si:
                out.append(f"phases are out of order: {wj} ends before {wi} starts")
            if ei and ej and ej < ei:
                out.append(f"phases are out of order: {wj} ends before {wi} ends")

    # deadlines, layers, commitments -----------------------------------------
    for where, d in deadlines:
        _texts(d, where, ("title",), out)
        _texts(d, where, ("estimate",), out, nullable=("estimate",))
        _date_field(d, "due", where, out, nullable=True)
        if d.get("due") is None and "due" in d and not _nonempty_str(d.get("estimate")):
            out.append(f"{where}: due is null, so estimate must say when")
        status(where, d, "deadline")
    for where, layer in layers:
        _texts(layer, where, ("title", "summary"), out)
    for where, c in commitments:
        _texts(c, where, ("subject", "reveal"), out)
        _date_field(c, "date", where, out, nullable=False)
        if "sha256" in c and not (isinstance(c["sha256"], str) and SHA256_RE.match(c["sha256"])):
            out.append(f"{where}.sha256 must be 64 lowercase hex characters")

    # changelog: a field the item has, with a value of that field's type ----------
    kinds_of: Dict[str, List[str]] = {}
    for kind, ids in (("phase", phase_ids), ("gate", gate_ids), ("deadline", deadline_ids),
                      ("layer", layer_ids), ("commitment", commitment_ids)):
        for i in ids:
            if kind not in kinds_of.setdefault(i, []):
                kinds_of[i].append(kind)
    for where, c in changelog:
        _texts(c, where, ("item", "field", "reason", "ref"), out)
        _date_field(c, "date", where, out, nullable=False)
        item, field = c.get("item"), c.get("field")
        kinds = kinds_of.get(item, []) if isinstance(item, str) else []
        if isinstance(item, str) and not kinds:
            out.append(f"{where}.item = {item!r} names nothing in the plan")
        elif len(kinds) > 1:
            out.append(f"{where}.item = {item!r} is ambiguous: it names a {' and a '.join(kinds)}")
        kind = kinds[0] if len(kinds) == 1 else None
        ftype: Optional[str] = None
        if isinstance(field, str):
            if field not in ALL_CHANGE_FIELDS:
                out.append(f"{where}.field = {field!r} is not a field the changelog may "
                           f"record (allowed: {ALL_CHANGE_FIELDS})")
            elif kind is not None and field not in CHANGE_FIELDS[kind]:
                out.append(f"{where}.field = {field!r} is not a field a {kind} has that the "
                           f"changelog may record (allowed: {sorted(CHANGE_FIELDS[kind])})")
            elif kind is not None:
                ftype = CHANGE_FIELDS[kind][field]
        for k in ("from", "to"):
            if k not in c:
                continue
            val = c[k]
            if val is not None and not isinstance(val, str):
                out.append(f"{where}.{k} must be a string or null")
            elif ftype == "date" and val is not None and parse_iso_date(val) is None:
                out.append(f"{where}.{k} = {val!r} is not an ISO date")
            elif ftype == "status" and not (isinstance(val, str) and kind in vocab
                                            and val in vocab[kind]):
                if kind in vocab:
                    out.append(f"{where}.{k} = {val!r} is not in vocabulary.{kind}")
            elif ftype == "gate" and val is not None and val not in gate_ids:
                out.append(f"{where}.{k} = {val!r} names no gate in gates[]")
            elif ftype == "text" and val is not None and not val.strip():
                out.append(f"{where}.{k} must be a non-empty string or null")

    # no capitalised status label anywhere: rendered text lands in governed Markdown, and
    # C3 adjudicates any line that pairs a brick-like token with one of these labels.
    # Read as the renderer writes it: whitespace runs (tabs, newlines, no-break spaces)
    # collapse to one space, and an id is written before its title ("BUILT" and
    # "UNVALIDATED x" render "BUILT UNVALIDATED x"). render_plan also scans what it
    # actually rendered; this is the earlier, plan-level half of that check.
    texts = [(where, s) for where, s in _walk_strings(plan, "plan")]
    for key in ("phases", "gates", "deadlines", "layers", "commitments"):
        recs = plan.get(key)
        for i, r in enumerate(recs if isinstance(recs, list) else []):
            if isinstance(r, dict) and isinstance(r.get("id"), str):
                for field in ("title", "subject"):
                    if isinstance(r.get(field), str):
                        texts.append((f"plan.{key}[{i}].id + {field}",
                                      f"Gate {r['id']} {r[field]}"))
    out.extend(label_problems(texts))
    return out


# The default-ignorable code points that are not format characters (Cf): the combining
# grapheme joiner, the Hangul fillers, the Khmer inherent vowels, the Mongolian variation
# selectors and the variation selectors. A reader sees none of them.
_IGNORABLE_NOT_CF = re.compile("[" + "".join(
    chr(a) if a == b else chr(a) + "-" + chr(b)
    for a, b in ((0x034F, 0x034F), (0x115F, 0x1160), (0x17B4, 0x17B5), (0x180B, 0x180D),
                 (0x180F, 0x180F), (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFFA0, 0xFFA0),
                 (0xE0100, 0xE01EF))) + "]")


def reader_view(s: str) -> str:
    """`s` as a reader of the rendered page sees it, as far as a status label goes.

    HTML character references are decoded, because Markdown decodes them and plan text
    reaches tables unescaped ('&#x50;ROVEN' reads 'PROVEN'). Invisible characters are
    dropped: every format character (category Cf: zero-width space, soft hyphen, word
    joiner, bidirectional controls) and the other default-ignorable code points
    (_IGNORABLE_NOT_CF). Compatibility forms are folded (NFKC: fullwidth letters).
    Decoding comes first, so a reference to an invisible character is dropped too.

    KNOWN LIMIT, asserted in test_core.py: a label spelled with letters of another script
    that only look Latin (a Cyrillic or Greek capital in place of 'O' or 'P') is not
    folded; Unicode's confusables table is not in the standard library, and C3, which the
    label check protects, reads only the ASCII labels."""
    t = "".join(c for c in html.unescape(s) if unicodedata.category(c) != "Cf")
    return unicodedata.normalize("NFKC", _IGNORABLE_NOT_CF.sub("", t))


def label_problems(texts: Iterable[Tuple[str, str]]) -> List[str]:
    """A problem for every text that holds a capitalised status label once its
    whitespace is collapsed, as written or as a reader sees it (reader_view). `texts` are
    (where, text) pairs."""
    labels = _status_labels()
    out: List[str] = []
    for where, s in texts:
        flats = (" ".join(s.split()), " ".join(reader_view(s).split()))
        for lab in labels:
            if any(lab in flat for flat in flats):
                out.append(f"{where} contains the status label {lab!r}; plan text is "
                           f"lowercase prose (C3 would read it as a brick status)")
                break
    return out


def validate_plan(plan: object) -> dict:
    """The plan, or PlanError. Nothing else escapes: a validator that crashed on some
    input must still say 'invalid' (exit 2 in render_plan), never 'stale' (exit 1)."""
    try:
        problems = plan_problems(plan)
    except Exception as e:  # noqa: BLE001 — plan_problems is meant to collect, not raise
        raise PlanError([f"the plan could not be validated ({type(e).__name__}: {e})"])
    if problems:
        raise PlanError(problems)
    return plan  # type: ignore[return-value]


def load_plan(root, *, validate: bool = True) -> dict:
    """tools/thesis_plan.json, validated. An unvalidated read must be asked for
    (validate=False), so no consumer can publish a field outside the allowlist by
    forgetting a second call."""
    plan = _read_json(Path(root) / PLAN_REL, "the thesis plan")
    if not isinstance(plan, dict):
        raise PlanError(["the plan is not a JSON object"])
    return validate_plan(plan) if validate else plan


# ─────────────────────────────────────────────────────────────────────────────
# the ledger's public projection
# ─────────────────────────────────────────────────────────────────────────────

PUBLIC_TEST_FIELDS = ("suites", "assertions", "failures", "captured_at", "captured_python")
PUBLIC_PROGRAM_FIELDS = ("state", "since", "decision")


def ledger_public(root) -> dict:
    """The only ledger facts a public surface may show, copied, never computed.

    determinism.interpreters is the ledger's interpreters_swept: what was actually swept,
    not what is required. Brick notes are not projected; their names and statuses are."""
    led = load_ledger(root)
    try:
        t = led["tests"]
        det = led["determinism"]
        tests = {k: t[k] for k in PUBLIC_TEST_FIELDS}
        for k in ("suites", "assertions", "failures"):
            if type(tests[k]) is not int:
                raise PublishError(f"ledger tests.{k} is not an integer")
        out = {
            "tests": tests,
            "determinism": {"interpreters": list(det["interpreters_swept"]),
                            "hash_seeds": list(det["hash_seeds"])},
            "bricks": [{"id": bid, "name": b["name"], "status": b["status"]}
                       for bid, b in led["bricks"].items()],
            "meaning_bar": {"status": led["meaning_bar"]["status"]},
            "program": {who: {f: led["program"][who][f] for f in PUBLIC_PROGRAM_FIELDS}
                        for who in ("psyche", "thesis")},
        }
    except (KeyError, TypeError, AttributeError) as e:
        raise PublishError(f"{LEDGER_REL.as_posix()} lacks a field the public projection "
                           f"needs: {type(e).__name__}: {e}")
    states = led.get("program_states")
    if isinstance(states, list):
        for who, p in out["program"].items():
            if p["state"] not in states:
                raise PublishError(f"program.{who}.state {p['state']!r} is not in "
                                   f"program_states {states}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Markdown block structure (shared with render_plan, so the two readers agree)
# ─────────────────────────────────────────────────────────────────────────────
#
# Both readers must know which lines are code, and a guess is a leak. A fence opened on a
# list-item line ("- ```") that is not seen as opened makes its closing line ("  ```")
# look like an opener, and every line after it then reads as code: generated markers that
# are real comments, links that are real links. Whether a line is code depends on its
# containers (block quotes and list items), on lazy continuation and on the leaf blocks
# before it, so it is decided the way CommonMark decides it: scan_blocks is a port of the
# block phase of the reference parser (commonmark.js, incorporateLine and its block
# starts), limited to what decides which lines are code — block quotes, list items,
# fenced and indented code, HTML blocks, paragraphs, headings and thematic breaks.
#
# Tabs count to the next multiple of four, as CommonMark counts them in block structure.
# Only \n, \r and \r\n end a line (str.splitlines also breaks at \v, \f, \x1c-\x1e, \x85,
# \u2028 and \u2029, which would make a line Markdown reads as text look like a fence).

_LINE_END = re.compile(r"\r\n|\r|\n")


def split_lines(text: str, *, keepends: bool = False) -> List[str]:
    """The lines of `text` as CommonMark reads them. No empty last line after a final
    line ending, as with str.splitlines."""
    out: List[str] = []
    pos = 0
    for m in _LINE_END.finditer(text):
        out.append(text[pos:m.end() if keepends else m.start()])
        pos = m.end()
    if pos < len(text):
        out.append(text[pos:])
    return out


def line_body(line: str) -> str:
    """A line from split_lines(keepends=True) without its line ending."""
    if line.endswith("\r\n"):
        return line[:-2]
    if line.endswith(("\r", "\n")):
        return line[:-1]
    return line


class MdLine(NamedTuple):
    """How CommonMark reads one line.

    kind   'fence' (opening line, content or closing line of a fenced code block),
           'icode' (indented code), 'html' (an HTML block), 'para' (paragraph text,
           lazy continuation included), 'other' (an ATX heading, a thematic break or a
           setext underline) or 'blank' (a line that adds nothing to a leaf block).
    block  the leaf block the line belongs to; lines of one block are consecutive.
    role   for a fence line: 'open', 'body' or 'close'; '' otherwise.
    col    the column (tabs expanded) at which the line's content starts, after the
           markers of its block quotes and the indentation of its list items."""
    kind: str
    block: int
    role: str
    col: int


class MdBlock(NamedTuple):
    kind: str
    closed: bool    # a fence ended by its own closing fence line (not by EOF or its container)


_ATX_RE = re.compile(r"#{1,6}(?:[ \t]+|$)")
_FENCE_START = re.compile(r"`{3,}(?!.*`)|~{3,}")      # an info string holds no backtick
_FENCE_END = re.compile(r"(?:`{3,}|~{3,})(?=[ \t]*$)")
_SETEXT_RE = re.compile(r"(?:=+|-+)[ \t]*$")
_HR_RE = re.compile(r"(?:\*[ \t]*){3,}$|(?:_[ \t]*){3,}$|(?:-[ \t]*){3,}$")
_BULLET_RE = re.compile(r"[*+-]")
# A GFM footnote definition opens a container whose content is indented four columns.
# GitHub's parser takes any label without spaces or ']' (cmark-gfm's scanner); micromark
# takes no '[' either, and lets '\\' escape '[', '\\' and ']'.
_NOTE_RE = re.compile(r"\[\^[^\] \t\r\n\x00]+\]:")
_NOTE_RE_MM = re.compile(r"\[\^(?:\\[\[\\\]]|\\(?![\[\\\]])|[^\[\]\\\s]){1,999}\]:")
_ORDERED_RE = re.compile(r"(\d{1,9})([.)])")

_TAGNAME = r"[A-Za-z][A-Za-z0-9-]*"
_ATTRNAME = r"[A-Za-z_:][A-Za-z0-9:._-]*"
_ATTRVALUE = r"(?:[^\"'=<>`\x00-\x20]+|'[^'\x00]*'|\"[^\"\x00]*\")"
_OPENTAG = (r"<" + _TAGNAME + r"(?:\s+" + _ATTRNAME + r"(?:\s*=\s*" + _ATTRVALUE + r")?)*"
            r"\s*/?>")
_CLOSETAG = r"</" + _TAGNAME + r"\s*>"
_BLOCK_TAGS = ("address|article|aside|base|basefont|blockquote|body|caption|center|col|"
               "colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|"
               "form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|"
               "menu|menuitem|nav|noframes|ol|optgroup|option|p|param|search|section|"
               "summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul")
_HTML_OPEN = (None,
              re.compile(r"<(?:script|pre|textarea|style)(?:\s|>|$)", re.I),
              re.compile(r"<!--"),
              re.compile(r"<\?"),
              re.compile(r"<![A-Za-z]"),
              re.compile(r"<!\[CDATA\["),
              re.compile(r"</?(?:" + _BLOCK_TAGS + r")(?:\s|/?>|$)", re.I),
              re.compile(r"(?:" + _OPENTAG + r"|" + _CLOSETAG + r")\s*$", re.I))
_HTML_CLOSE = (None,
               re.compile(r"</(?:script|pre|textarea|style)>", re.I),
               re.compile(r"-->"),
               re.compile(r"\?>"),
               re.compile(r">"),
               re.compile(r"\]\]>"))
_LEAVES = ("para", "fence", "icode", "html")


def _skip_ws(s: str, j: int, newline: bool) -> int:
    """Past spaces and tabs, and (if `newline`) at most one line ending and the spaces
    and tabs after it."""
    while j < len(s) and s[j] in " \t":
        j += 1
    if newline and j < len(s) and s[j] == "\n":
        j += 1
        while j < len(s) and s[j] in " \t":
            j += 1
    return j


def _dest_end(s: str, j: int) -> int:
    """End of a link destination starting at j, or -1 (CommonMark's two forms)."""
    if j < len(s) and s[j] == "<":
        k = j + 1
        while k < len(s) and s[k] not in "<>\n":
            k += 2 if s[k] == "\\" and k + 1 < len(s) and s[k + 1] in _ASCII_PUNCT else 1
        return k + 1 if k < len(s) and s[k] == ">" else -1
    k, depth = j, 0
    while k < len(s):
        c = s[k]
        if c == "\\" and k + 1 < len(s) and s[k + 1] in _ASCII_PUNCT:
            k += 2
            continue
        if c.isspace() or ord(c) < 0x20 or c == "\x7f":
            break
        if c == "(":
            depth += 1
            if depth > 32:
                return -1
        elif c == ")":
            if depth == 0:
                break
            depth -= 1
        k += 1
    return k if k > j and depth == 0 else -1


def _title_end(s: str, j: int) -> int:
    close = {'"': '"', "'": "'", "(": ")"}.get(s[j])
    k = j + 1
    while k < len(s):
        c = s[k]
        if c == "\\" and k + 1 < len(s) and s[k + 1] in _ASCII_PUNCT:
            k += 2
            continue
        if c == close:
            return k + 1
        if close == ")" and c == "(":
            return -1
        k += 1
    return -1


def _refdef_end(s: str, pos: int) -> int:
    """Where a CommonMark link reference definition that starts at `pos` of paragraph
    text `s` ends (after its line ending), or -1 if none starts there."""
    i = pos
    while i < len(s) and i - pos < 3 and s[i] == " ":
        i += 1
    if i >= len(s) or s[i] != "[":
        return -1
    j, data = i + 1, False
    while j < len(s) and s[j] != "]":
        if s[j] == "\\" and j + 1 < len(s) and s[j + 1] in _ASCII_PUNCT:
            j, data = j + 2, True
            continue
        if s[j] == "[":
            return -1
        data = data or not s[j].isspace()
        j += 1
    if j >= len(s) or j - i - 1 > 999 or not data or s[j + 1:j + 2] != ":":
        return -1
    d0 = _skip_ws(s, j + 2, True)
    d1 = _dest_end(s, d0)
    if d1 < 0:
        return -1
    e = _skip_ws(s, d1, False)
    plain = e >= len(s) or s[e] == "\n"
    t0 = _skip_ws(s, d1, True)
    if t0 > d1 and t0 < len(s) and s[t0] in "\"'(":
        t1 = _title_end(s, t0)
        if t1 > 0:
            e2 = _skip_ws(s, t1, False)
            if e2 >= len(s) or s[e2] == "\n":
                return min(e2 + 1, len(s))
    return min(e + 1, len(s)) if plain else -1


def _refdefs_only(lines: List[str]) -> bool:
    """True if paragraph text made of `lines` is nothing but link reference definitions;
    such a paragraph cannot become a setext heading."""
    s = "\n".join(lines)
    pos = 0
    while pos < len(s):
        end = _refdef_end(s, pos)
        if end <= pos:
            return False
        pos = end
    return bool(s)


class _Blk:
    __slots__ = ("kind", "id", "w", "child", "fchar", "flen", "foff", "htype", "lazy",
                 "text")

    def __init__(self, kind: str, bid: int, w: int = 0, fchar: str = "", flen: int = 0,
                 foff: int = 0, htype: int = 0):
        self.kind, self.id, self.w, self.child = kind, bid, w, False
        self.lazy = False      # micromark: an indented code block's latest line was lazy
        self.text: List[str] = []   # a paragraph's lines, for the setext rule
        self.fchar, self.flen, self.foff, self.htype = fchar, flen, foff, htype


class _BlockScanner:
    """commonmark.js's incorporateLine, for the block kinds MdLine distinguishes. There
    are no list blocks, only items: a list wrapper changes nothing about which lines are
    code. Link reference definitions are read as the paragraph text they start as.

    mode 'cmark' reads as GitHub's parser (cmark-gfm, the same algorithm) does. Mode
    'micromark' reads as the site's parser does, which differs in two rules found by
    testing it against micromark 4:
      - while a paragraph or an indented code block is still open and every container
        continues, a new list item may not be an ordered item other than 1, nor start
        empty, even after a block quote or list item opened earlier on the same line
        (CommonMark restricts this only directly after a paragraph);
      - on a lazy continuation line, a lone HTML tag (HTML block type 7) starts an HTML
        block (CommonMark keeps the line in the paragraph).
    Both modes read GFM footnote definitions, which GitHub and the site both render: a
    container continued by four columns of indentation or by a blank line (GitHub: an
    empty line only), so a footnote's indented paragraph is not indented code."""

    def __init__(self, mode: str = "cmark") -> None:
        if mode not in MD_MODES:
            raise ValueError(f"unknown Markdown mode {mode!r}")
        self.micromark = mode == "micromark"
        self.stack: List[_Blk] = [_Blk("doc", -1)]
        self.lines: List[MdLine] = []
        self.blocks: Dict[int, MdBlock] = {}
        self.ln, self.n, self.offset = "", 0, 0
        self.last_matched, self.all_closed = 0, True

    # helpers ------------------------------------------------------------------
    def _nonspace(self) -> Tuple[int, int, bool]:
        i = self.offset
        while i < self.n and self.ln[i] == " ":
            i += 1
        return i, i - self.offset, i >= self.n

    def _record(self, kind: str, bid: int, role: str = "") -> None:
        self.lines.append(MdLine(kind, bid, role, self.offset))

    def _close_unmatched(self) -> None:
        if not self.all_closed:
            del self.stack[self.last_matched + 1:]
            self.all_closed = True

    def _add(self, kind: str, **kw) -> _Blk:
        while self.stack[-1].kind in _LEAVES:     # a leaf contains no block
            self.stack.pop()
        if self.stack[-1].kind == "item":
            self.stack[-1].child = True
        b = _Blk(kind, len(self.blocks), **kw)
        self.blocks[b.id] = MdBlock(kind, False)
        if kind != "other":
            self.stack.append(b)
        return b

    def _list_marker(self, i: int, indent: int, container: _Blk,
                     interrupt: bool) -> Optional[Tuple[int, int]]:
        """(content indent W, offset after the marker) if a list item starts at i."""
        if indent >= 4:
            return None
        interrupt = interrupt or container.kind == "para"
        ln, n = self.ln, self.n
        m = _BULLET_RE.match(ln, i)
        if not m:
            m = _ORDERED_RE.match(ln, i)
            if not m or (interrupt and int(m.group(1)) != 1):
                return None
        j = m.end()
        if j < n and ln[j] != " ":
            return None
        if interrupt and not ln[j:].strip(" "):
            return None         # an empty item cannot interrupt a paragraph
        k = j + 1 if j < n else j
        while k - j < 5 and k < n and ln[k] == " ":
            k += 1
        mlen = j - i
        if k - j >= 5 or k - j < 1 or k >= n:
            return indent + mlen + 1, (j + 1 if j < n else j)
        return indent + mlen + (k - j), k

    # one line -----------------------------------------------------------------
    def feed(self, raw: str) -> None:
        self.ln = ln = raw.expandtabs(4)
        self.n = n = len(ln)
        self.offset = 0
        stack = self.stack
        matched = 0
        for depth in range(1, len(stack)):
            b = stack[depth]
            i, indent, blank = self._nonspace()
            if b.kind == "quote":
                if indent > 3 or blank or ln[i] != ">":
                    break
                self.offset = i + 1
                if self.offset < n and ln[self.offset] == " ":
                    self.offset += 1
            elif b.kind == "item":
                if blank:
                    if not b.child:
                        break       # a list item begins with at most one blank line
                    self.offset = i
                elif indent >= b.w:
                    self.offset += b.w
                else:
                    break
            elif b.kind == "note":
                if blank and (self.micromark or n == 0):
                    self.offset = i
                elif indent >= 4:
                    self.offset += 4
                else:
                    break
            elif b.kind == "fence":
                if indent <= 3 and not blank and ln[i] == b.fchar:
                    m = _FENCE_END.match(ln, i)
                    if m and len(m.group(0)) >= b.flen:
                        self._record("fence", b.id, "close")
                        self.blocks[b.id] = MdBlock("fence", True)
                        del stack[depth:]
                        return
                k = b.foff
                while k > 0 and self.offset < n and ln[self.offset] == " ":
                    self.offset += 1
                    k -= 1
            elif b.kind == "icode":
                if indent >= 4:
                    self.offset += 4
                elif blank:
                    self.offset = i
                else:
                    break
            elif b.kind == "html":
                if blank and b.htype in (6, 7):
                    break
            elif blank:          # a paragraph
                break
            matched = depth
        self.last_matched = matched
        self.all_closed = matched == len(stack) - 1
        container = stack[matched]
        _, _, blank = self._nonspace()
        # micromark reads a new list item as interrupting when every container (not
        # counting the leaf) continued and its flow has a construct in progress: a
        # paragraph, or an indented code block whose latest line was not lazy (a lazy
        # line ends one). A container opened on a line closes the flow before its leaf.
        tip = stack[-1]
        containers = len(stack) - 1 - (1 if tip.kind in _LEAVES else 0)
        continued = matched >= containers
        mm_interrupt = self.micromark and continued and (
            tip.kind == "para" or (tip.kind == "icode" and not tip.lazy))
        opened = False
        if container.kind not in ("fence", "icode", "html"):
            while True:
                i, indent, blank = self._nonspace()
                indented = indent >= 4
                c = ln[i] if i < n else ""
                if not indented and c == ">":
                    self.offset = i + 1
                    if self.offset < n and ln[self.offset] == " ":
                        self.offset += 1
                    self._close_unmatched()
                    container = self._add("quote")
                    opened = True
                    continue
                if not indented and _ATX_RE.match(ln, i):
                    self._close_unmatched()
                    self.offset = i
                    self._record("other", self._add("other").id)
                    return
                m = None if indented else _FENCE_START.match(ln, i)
                if m:
                    self._close_unmatched()
                    b = self._add("fence", fchar=m.group(0)[0], flen=len(m.group(0)),
                                  foff=indent)
                    self.offset = i
                    self._record("fence", b.id, "open")
                    return
                if not indented and c == "<":
                    tip = stack[-1]
                    for t in range(1, 8):
                        if not _HTML_OPEN[t].match(ln, i):
                            continue
                        lazy = not self.all_closed and not blank and tip.kind == "para"
                        if t == 7 and (container.kind == "para"
                                       or (lazy and not self.micromark)):
                            continue      # type 7 cannot interrupt a paragraph
                        if not (lazy and t == 7):
                            self._close_unmatched()
                        # (micromark, type 7 on a lazy line: the block replaces the
                        # paragraph inside the containers the line did not continue)
                        b = self._add("html", htype=t)
                        self._record("html", b.id)
                        if t <= 5 and _HTML_CLOSE[t].search(ln, self.offset):
                            stack.pop()
                        return
                if (not indented and container.kind == "para" and _SETEXT_RE.match(ln, i)
                        and not _refdefs_only(container.text)):
                    self._close_unmatched()
                    stack.pop()           # the paragraph becomes a heading
                    self.offset = i
                    self._record("other", self._add("other").id)
                    return
                if not indented and _HR_RE.match(ln, i):
                    self._close_unmatched()
                    self.offset = i
                    self._record("other", self._add("other").id)
                    return
                m = None if indented else (_NOTE_RE_MM if self.micromark else _NOTE_RE).match(ln, i)
                if m:
                    self._close_unmatched()
                    self.offset = m.end()
                    while self.offset < n and ln[self.offset] == " ":
                        self.offset += 1
                    container = self._add("note")
                    opened = True
                    continue
                item = self._list_marker(i, indent, container, mm_interrupt)
                if item:
                    self._close_unmatched()
                    self.offset = item[1]
                    container = self._add("item", w=item[0])
                    opened = True
                    continue
                if indented and stack[-1].kind != "para" and not blank:
                    self.offset += 4
                    self._close_unmatched()
                    b = self._add("icode")
                    b.lazy = not continued and not opened
                    self._record("icode", b.id)
                    return
                self.offset = i
                break
        tip = stack[-1]
        if not self.all_closed and not blank and tip.kind == "para":
            tip.text.append(ln[self.offset:])
            self._record("para", tip.id)          # lazy continuation
            return
        self._close_unmatched()
        tip = stack[-1]
        if tip.kind in _LEAVES:
            if tip.kind == "icode":
                tip.lazy = False           # continued: every container matched
            elif tip.kind == "para":
                tip.text.append(ln[self.offset:])
            self._record(tip.kind, tip.id, "body" if tip.kind == "fence" else "")
            if (tip.kind == "html" and tip.htype <= 5
                    and _HTML_CLOSE[tip.htype].search(ln, self.offset)):
                stack.pop()
        elif not blank:
            b = self._add("para")
            b.text.append(ln[self.offset:])
            self._record("para", b.id)
        else:
            self._record("blank", -1)


MD_MODES = ("cmark", "micromark")


def scan_blocks(lines: List[str], mode: str = "cmark"
                ) -> Tuple[List[MdLine], Dict[int, MdBlock]]:
    """How CommonMark reads each line of a document (lines without their endings, as
    split_lines gives them), and what became of each block. `mode` picks the parser
    whose reading is wanted where parsers differ (see _BlockScanner)."""
    s = _BlockScanner(mode)
    for raw in lines:
        s.feed(raw)
    return s.lines, s.blocks


FENCE_CLOSED, FENCE_UNCLOSED, FENCE_DISPUTED = "closed", "unclosed", "disputed"


def code_fences(lines: List[str]) -> List[Optional[str]]:
    """For each line, read in every mode: None when no reading puts it in fenced code;
    FENCE_CLOSED when every reading puts it in a fenced code block that its own closing
    line ends; FENCE_UNCLOSED when every reading puts it in fenced code but some reading's
    block runs to the end of the document, list item or block quote instead; and
    FENCE_DISPUTED when the readings disagree whether it is fenced code at all."""
    readings = [scan_blocks(lines, mode) for mode in MD_MODES]
    out: List[Optional[str]] = []
    for idx in range(len(lines)):
        states = [li[idx].kind == "fence" and blocks[li[idx].block].closed
                  if li[idx].kind == "fence" else None for li, blocks in readings]
        if all(s is None for s in states):
            out.append(None)
        elif any(s is None for s in states):
            out.append(FENCE_DISPUTED)
        else:
            out.append(FENCE_CLOSED if all(states) else FENCE_UNCLOSED)
    return out


def _col_index(raw: str, col: int) -> int:
    """The index in `raw` of tab-expanded column `col`. A column inside a tab gives the
    tab, so content never starts past a character it may hold."""
    if "\t" not in raw:
        return min(col, len(raw))
    c = 0
    for idx, ch in enumerate(raw):
        if c >= col:
            return idx
        c = c + 4 - c % 4 if ch == "\t" else c + 1
        if c > col:
            return idx
    return len(raw)


# ─────────────────────────────────────────────────────────────────────────────
# inline code and comments
# ─────────────────────────────────────────────────────────────────────────────
#
# A code span or an HTML comment is masked only when it is one for certain, because a
# mask that is too wide hides a real link from the dead-link check. Left to right, as the
# reference inline parser goes: a backslash escapes the punctuation after it (so "\`"
# opens nothing), a backtick run opens a span that the next run of the same length
# closes, and a raw HTML tag or an autolink is atomic (a backtick inside one opens
# nothing).
#
# Where the parsers this text reaches disagree, the text is read every way and only what
# every reading masks is masked:
#   comments  GitHub's parser (CommonMark 0.29) takes an inline comment only in the
#             strict form (no "--" inside, not ending in "-", not starting with ">" or
#             "->"); CommonMark 0.31, which the site's parser follows, takes any
#             "<!--" ... "-->". Inside a lenient-only comment, a backtick opens a span
#             for one parser and is comment text for the other.
#   tables    in a paragraph where a GFM table could start (a line that could be its
#             delimiter row), each row and each cell is read on its own.

_ASCII_PUNCT = frozenset("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
_INLINE_COMMENT = re.compile(r"<!--(?!-?>)(?:[^-]|-(?!-))*-->")
_LENIENT_COMMENT = re.compile(r"<!--(?:>|->|[\s\S]*?-->)")
_INLINE_ATOM = re.compile(
    r"<[A-Za-z][A-Za-z0-9.+-]{1,31}:[^<>\x00-\x20]*>"                    # autolink
    r"|<[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*>"              # email autolink
    r"|" + _OPENTAG + r"|" + _CLOSETAG +
    r"|<\?[\s\S]*?\?>|<![A-Za-z][^>]*>|<!\[CDATA\[[\s\S]*?\]\]>")
# what an HTML parser reads as a comment inside raw HTML: it ends at the first --> or --!>
_RAW_COMMENT = re.compile(r"<!--(?:>|->|[\s\S]*?(?:-->|--!>))")
_DELIM_ROW = re.compile(r"[ \t|:-]*-[ \t|:-]*")
_CELL_SPLIT = re.compile(r"(?<!\\)\|")


def _inline_spans(s: str, lenient: bool) -> Set[Tuple[int, int]]:
    """(start, end) of every code span and inline comment in `s`, reading comments the
    lenient (CommonMark 0.31) or the strict (GitHub) way."""
    comment = _LENIENT_COMMENT if lenient else _INLINE_COMMENT
    spans: Set[Tuple[int, int]] = set()
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2 if i + 1 < n and s[i + 1] in _ASCII_PUNCT else 1
        elif c == "`":
            j = i
            while j < n and s[j] == "`":
                j += 1
            run, k, close = j - i, j, -1
            while True:
                k = s.find("`", k)
                if k < 0:
                    break
                e = k
                while e < n and s[e] == "`":
                    e += 1
                if e - k == run:
                    close = k
                    break
                k = e
            if close < 0:
                i = j
            else:
                spans.add((i, close + run))
                i = close + run
        elif c == "<":
            m = comment.match(s, i)
            if m:
                spans.add((i, m.end()))
                i = m.end()
                continue
            m = _INLINE_ATOM.match(s, i)
            i = m.end() if m else i + 1
        else:
            i += 1
    return spans


def _cell_spans(pieces: List[Tuple[int, str]], lenient: bool) -> Set[Tuple[int, int]]:
    """The spans of _inline_spans read as GFM table rows: each line on its own, split
    into cells at every pipe that is not escaped. `pieces` are (offset, line content)."""
    spans: Set[Tuple[int, int]] = set()
    for off, piece in pieces:
        start = 0
        for m in list(_CELL_SPLIT.finditer(piece)) + [None]:
            end = m.start() if m else len(piece)
            base = off + start
            spans |= {(base + a, base + b)
                      for a, b in _inline_spans(piece[start:end], lenient)}
            start = end + 1
    return spans


def inline_code_spans(pieces: List[Tuple[int, str]], text: str, *,
                      table: bool = False) -> Set[Tuple[int, int]]:
    """The spans of `text` — the content of one paragraph, made of `pieces` (offset, line
    content) joined by line endings — that are code or comments however it is read.
    `table`: the line after the paragraph could be a table's delimiter row (a parser that
    reads "| a |" over "---" as a table rather than a heading)."""
    spans = _inline_spans(text, False) & _inline_spans(text, True)
    if table or any(_DELIM_ROW.fullmatch(p) for _, p in pieces) or (
            len(pieces) == 1 and _CELL_SPLIT.search(text)):
        spans &= _cell_spans(pieces, False) & _cell_spans(pieces, True)
    return spans


def mask_inline(line: str, *, comments: bool = True) -> str:
    """One line with its certain code spans (and, unless comments=False, its certain
    inline comments) blanked to NUL."""
    buf = list(line)
    for a, b in inline_code_spans([(0, line)], line):
        if comments or line[a] == "`":
            buf[a:b] = "\0" * (b - a)
    return "".join(buf)


# ─────────────────────────────────────────────────────────────────────────────
# link rewriting
# ─────────────────────────────────────────────────────────────────────────────

NEST_DEPTH = 4    # brackets in link text and parentheses in a destination, nested this deep
_NL = r"\n(?![ \t]*\n)"          # a line ending that is not a blank line
_EOL = r"(?:\n[ \t]*)?"          # at most one line ending inside a link's parentheses


def _nest(atom: str, open_: str, close: str, depth: int) -> str:
    """A pattern for a run of `atom`s and balanced open_/close groups, `depth` deep."""
    inner = f"(?:{atom})*"
    for _ in range(depth):
        inner = f"(?:{atom}|{open_}{inner}{close})*"
    return inner


# Link text: any character but brackets, balanced brackets NEST_DEPTH deep, line endings
# allowed (documents here are hard-wrapped) but never a blank line.
_TXT_ATOM = r"[^\[\]\\\n]|\\(?:[^\n]|" + _NL + r")|" + _NL
_TEXT = _nest(_TXT_ATOM, r"\[", r"\]", NEST_DEPTH)
_DEST_ATOM = r"[^\s()\\]|\\."
_DEST = (r"(?:<[^<>\n]*>|(?:" + _DEST_ATOM + r"|\(" + _nest(_DEST_ATOM, r"\(", r"\)", NEST_DEPTH - 1)
         + r"\))+)")
_TITLE = (r"(?:(?:[ \t]+" + _EOL + r"|\n[ \t]*)"
          r"(?:\"[^\"\n]*\"|'[^'\n]*'|\([^()\n]*\)))?")
# A reference definition may sit inside block quotes and list items, and its destination
# may be on the next line. It is one only if the destination ends the line or a title
# follows; "[Gate A]: novelty review" is prose, not a definition.
_REF_PREFIX = r"(?:[ \t]*(?:>|(?:[-+*]|\d{1,9}[.)])(?=[ \t])))*[ \t]*"
# A line ending inside a definition's label that is not a blank line; in a block quote a
# line that holds only '>' markers is blank too.
_REF_NL = r"\n(?!(?:[ \t]*>)*[ \t]*(?:\n|$))"
# One character of a link label (CommonMark): anything but a bracket or a backslash, a
# backslash and the character it escapes ('\]' is part of the label), or a line ending
# that is not a blank line. A label holds at most 999 characters; counting atoms, each
# one or two characters, can only accept more than that, never miss a real label.
_LABEL_ATOM = r"[^\[\]\\\n]|\\[^\n]|\\?" + _REF_NL
# At most one line ending between a definition's ':' and its destination, and the
# block-quote markers that start the destination's line.
_REF_EOL = r"(?:\n(?:[ \t]*>)*[ \t]*)?"
# HTML whitespace inside a tag: spaces and tabs, and at most one line ending (CommonMark)
_HWS0 = r"[ \t]*(?:(?:\r\n|\r|\n)[ \t]*)?"
_HWS1 = r"(?:[ \t]+(?:(?:\r\n|\r|\n)[ \t]*)?|(?:\r\n|\r|\n)[ \t]*)"
_DQ, _SQ, _UQ = r"[^\"\x00]*", r"[^'\x00]*", r"[^\"'=<>`\x00-\x20]+"
_TAG_ATTR_RE = re.compile(
    r"(?P<ws>" + _HWS1 + r")(?P<name>" + _ATTRNAME + r")(?:" + _HWS0 + r"=" + _HWS0
    + r"(?:\"(?P<dq>" + _DQ + r")\"|'(?P<sq>" + _SQ + r")'|(?P<uq>" + _UQ + r")))?")
_TAG_ATTR_ANY = (r"(?:" + _HWS1 + _ATTRNAME + r"(?:" + _HWS0 + r"=" + _HWS0
                 + r"(?:\"" + _DQ + r"\"|'" + _SQ + r"'|" + _UQ + r"))?)")
_LINK_RE = re.compile(
    r"(?P<inline>(?P<bang>!?)\[(?P<text>" + _TEXT + r")\]\((?P<pre>[ \t]*" + _EOL + r")"
    r"(?P<dest>" + _DEST + r")(?P<post>" + _TITLE + r"[ \t]*" + _EOL + r")\))"
    # an open tag, the only place an href/src/srcset/poster attribute is one
    r"|(?P<tag><" + _TAGNAME + _TAG_ATTR_ANY + r"*" + _HWS0 + r"/?>)")
# The label is read with CommonMark's grammar (_LABEL_ATOM): '[a\]b]', a label that runs
# over several lines and '[\nfoo\n]' are labels, and a label of whitespace alone is not.
# A label that begins with '^' is a GFM footnote's, read by _LEFT_REFDEF's caller.
_REFDEF_RE = re.compile(
    r"^(?P<rpre>" + _REF_PREFIX + r")\[(?!\^)(?=\s*[^\s\]])(?P<label>(?:" + _LABEL_ATOM
    + r"){1,999})\]:[ \t]*" + _REF_EOL
    + r"(?P<rdest><[^<>\n]*>|\S+)(?=[ \t]*(?:$|[\"'(]))", re.M)
# The leftover scan's reading of a definition, looser than _REFDEF_RE: a '[' at the start
# of a line (after its container markers), anything up to the first ']:' that is not a
# blank line away (an unescaped '[' excepted, which no label holds), and a
# destination-shaped token after it. One that _REFDEF_RE did not take is refused unless
# it is a GFM footnote or its token is external (_check_leftover_refdefs).
_LEFT_REFDEF = re.compile(
    r"^" + _REF_PREFIX + r"\[(?=\s*[^\s\]])(?P<l>(?:[^\[\\\n]|\\[^\n]|\\?" + _REF_NL
    + r")*?)\]:[ \t]*"
    + _REF_EOL + r"(?P<d><[^<>\n]*>|\S+)(?=[ \t]*(?:$|[\"'(]))", re.M)
_LINK_ATTRS = ("href", "src", "srcset", "poster")
# images used by reference: ![text][label], ![label][] and ![label]
_IMG_REF_RE = re.compile(r"!\[(?P<t>" + _TEXT + r")\](?:\[(?P<l>(?:" + _LABEL_ATOM
                         + r"){0,999})\]|(?![(\[]))")
# What is left between the matches above must hold no link the patterns did not take:
# a '](' that survives, or a tag carrying one of _LINK_ATTRS that the tag pattern could
# not read, is a shape this module cannot parse. Only a tag: an attribute-like word in
# prose or in a bare URL ("?src=abc") is text, not an attribute.
_LEFT_INLINE = re.compile(r"\]\([ \t]*" + _EOL + r"(?P<d><[^<>\n]*>|[^\s)]*)")
_LEFT_TAG = re.compile(r"<" + _TAGNAME + r"(?=[\s/>])(?:[^<>]|\n[ \t]*>)*?"
                       r"(?<![\w-])(srcset|href|src|poster)\s*=", re.I)
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
# External means a full http(s) URL or a mailto. 'https:missing.md' has the scheme but no
# '//': a browser resolves it against the page (WHATWG URL: the scheme is the page's, so
# it is a relative path), so it is dead once published and is refused, not skipped.
_EXTERNAL_RE = re.compile(r"^(?:https?://|mailto:)", re.I)
_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif", ".bmp", ".ico")


def _masks_in(text: str, starts: List[int], bodies: List[str], mode: str
              ) -> Tuple[List[str], List[str], List[int]]:
    """One reading of _masks: (inline mask, block mask, leaf block of each line)."""
    info, _ = scan_blocks(bodies, mode)
    buf = list(text)

    def blank(at: List[int], spans: Iterable[Tuple[int, int]], into: List[str]) -> None:
        for a, b in spans:
            for k in range(a, b):
                o = at[k]
                if text[o] not in "\r\n":
                    into[o] = "\0"

    for idx, li in enumerate(info):
        if li.kind in ("fence", "icode"):
            buf[starts[idx]:starts[idx] + len(bodies[idx])] = "\0" * len(bodies[idx])

    # the leaf blocks whose text is not code: consecutive lines of one block
    groups: List[Tuple[Tuple[str, int], List[int]]] = []
    for idx, li in enumerate(info):
        if li.kind in ("para", "other", "html"):
            if groups and groups[-1][0] == (li.kind, li.block):
                groups[-1][1].append(idx)
            else:
                groups.append(((li.kind, li.block), [idx]))
    inline_jobs = []
    for (kind, _), idxs in groups:
        parts: List[str] = []
        at: List[int] = []
        pieces: List[Tuple[int, str]] = []
        for n, idx in enumerate(idxs):
            if n:
                parts.append("\n")
                at.append(starts[idx] - 1)      # the previous line's ending
            k = _col_index(bodies[idx], info[idx].col)
            pieces.append((len(at), bodies[idx][k:]))
            parts.append(bodies[idx][k:])
            at.extend(range(starts[idx] + k, starts[idx] + len(bodies[idx])))
        content = "".join(parts)
        if kind == "html":
            blank(at, [m.span() for m in _RAW_COMMENT.finditer(content)], buf)
        else:
            nxt = idxs[-1] + 1
            table = nxt < len(info) and info[nxt].kind == "other" and bool(
                _DELIM_ROW.fullmatch(bodies[nxt][_col_index(bodies[nxt], info[nxt].col):]))
            inline_jobs.append((at, inline_code_spans(pieces, content, table=table)))
    blocks = list(buf)
    for at, spans in inline_jobs:
        blank(at, spans, buf)
    return buf, blocks, [li.block for li in info]


class _Masked(NamedTuple):
    inline: str
    blocks: str
    regions: List[Tuple[int, int]]


def _masks(text: str) -> _Masked:
    """Copies of `text`, each the same length, with what is not Markdown link syntax
    blanked to NUL (line endings kept), so match positions still index the original.

    `blocks` blanks the lines of fenced and indented code and the comments inside HTML
    blocks; `inline` also blanks code spans and inline comments. Reference definitions
    are block syntax, read from `blocks`: a backtick in a label or a destination opens no
    code span. Every reading (MD_MODES) is made, and a character is blanked only if
    every reading blanks it: a parser that reads it as text must find its links checked.

    `regions` are the (start, end) of runs of lines that every reading puts in one leaf
    block. Inline syntax never crosses a leaf block, so no link, tag or attribute value
    is matched across a region's edge (a quoted attribute running from a list item into
    the next block would otherwise swallow the links there)."""
    lines = split_lines(text, keepends=True)
    bodies = [line_body(x) for x in lines]
    starts: List[int] = []
    pos = 0
    for x in lines:
        starts.append(pos)
        pos += len(x)
    readings = [_masks_in(text, starts, bodies, mode) for mode in MD_MODES]
    inline = "".join("\0" if all(r[0][k] == "\0" for r in readings) else c
                     for k, c in enumerate(text))
    blocks = "".join("\0" if all(r[1][k] == "\0" for r in readings) else c
                     for k, c in enumerate(text))
    regions: List[Tuple[int, int]] = []
    first = 0
    for idx in range(len(lines)):
        last = idx + 1 == len(lines) or any(
            r[2][idx] < 0 or r[2][idx] != r[2][idx + 1] for r in readings)
        if last:
            regions.append((starts[first], starts[idx] + len(bodies[idx])))
            first = idx + 1
    return _Masked(_lf(inline), _lf(blocks), regions)


def _lf(mask: str) -> str:
    """A mask with every line ending spelled '\\n', length kept: CRLF becomes ' \\n' and a
    lone CR '\\n'. The link patterns end lines at '\\n' only ('$', _NL, _REF_EOL), and
    CommonMark ends them at CR too, so without this a definition ending in CRLF inside a
    paragraph, or anything in a CR-only file, was never matched and never checked."""
    return mask.replace("\r\n", " \n").replace("\r", "\n")


def _norm_label(s: str) -> str:
    """CommonMark label matching: case-insensitive, runs of whitespace as one space."""
    return " ".join(s.split()).casefold()


def _image_labels(masked: str) -> Set[str]:
    labels: Set[str] = set()
    for m in _IMG_REF_RE.finditer(masked):
        lab = m.group("l")
        labels.add(_norm_label(lab if lab and lab.strip() else m.group("t")))
    return labels


def _is_image(raw: str) -> bool:
    path = raw[1:-1] if raw.startswith("<") and raw.endswith(">") else raw
    path = path.split("#", 1)[0].split("?", 1)[0]
    return path.lower().endswith(_IMAGE_EXT)


def _is_external(raw: str) -> bool:
    return raw == "" or raw.startswith("#") or bool(_EXTERNAL_RE.match(raw))


class _Ctx:
    def __init__(self, src: str, mapping: Dict[str, str], sha: str, repo: str,
                 root: Path, tracked: Set[str], image_labels: Set[str]):
        self.src, self.mapping, self.sha, self.repo = src, mapping, sha, repo
        self.root, self.tracked, self.image_labels = root, tracked, image_labels
        self.dirs = {posixpath.dirname(t) for t in tracked}
        for t in list(self.dirs):
            while t:
                t = posixpath.dirname(t)
                self.dirs.add(t)


def _resolve(raw: str, image: bool, ctx: _Ctx) -> str:
    """The rewritten target for one link destination, or the destination unchanged when
    it is external. Raises PublishError for anything that would be dead once published."""
    if raw.startswith("#") or _EXTERNAL_RE.match(raw):
        return raw
    m = _SCHEME_RE.match(raw)
    if m:
        scheme = m.group(0)[:-1].lower()
        if scheme in ("http", "https"):
            raise PublishError(f"{ctx.src}: link {raw!r} has the scheme {scheme!r} but no "
                               f"'//', so a browser resolves it as a path relative to the "
                               f"page; write a full URL or a relative link")
        raise PublishError(f"{ctx.src}: link {raw!r} uses the scheme {scheme!r}; only "
                           f"http(s) URLs and mailto may leave the repository")
    if raw.startswith("/"):
        raise PublishError(f"{ctx.src}: link {raw!r} is absolute; GitHub resolves it "
                           f"outside the repository, so write it relative")
    path, hsep, frag = raw.partition("#")
    path, qsep, query = path.partition("?")
    if not path:
        raise PublishError(f"{ctx.src}: link {raw!r} has no path")
    suffix = (f"?{query}" if qsep else "") + (f"#{frag}" if hsep else "")
    plain = unquote(re.sub(r"\\(.)", r"\1", path))
    joined = posixpath.normpath(posixpath.join(posixpath.dirname(ctx.src), plain))
    if joined == ".." or joined.startswith("../"):
        raise PublishError(f"{ctx.src}: dead relative link {raw!r} — it leaves the repository")
    if joined in ctx.mapping:
        return ctx.mapping[joined] + suffix
    fs = ctx.root / joined
    if joined != "." and joined in ctx.tracked and fs.is_file():
        kind = "raw" if image else "blob"
    elif (joined == "." and ctx.tracked) or (joined in ctx.dirs and fs.is_dir()):
        kind = "tree"
    else:
        why = "not in the pinned commit" if fs.exists() else "missing"
        raise PublishError(f"{ctx.src}: dead relative link {raw!r} -> {joined} ({why})")
    tail = "" if joined == "." else "/" + quote(joined, safe="/-_.~")
    return f"https://github.com/{ctx.repo}/{kind}/{ctx.sha}{tail}{suffix}"


def _rewrite_dest(dest: str, image: bool, ctx: _Ctx) -> str:
    if dest.startswith("<") and dest.endswith(">"):
        return "<" + _resolve(dest[1:-1], image, ctx) + ">"
    return _resolve(dest, image, ctx)


def _rewrite_srcset(value: str, ctx: _Ctx) -> str:
    """Each comma-separated candidate is 'URL [descriptor]'; every URL is an image."""
    out = []
    for part in value.split(","):
        m = re.match(r"^(\s*)(\S+)(.*)$", part, re.S)
        out.append(part if not m else m.group(1) + _resolve(m.group(2), True, ctx) + m.group(3))
    return ",".join(out)


def _snippet(text: str, at: int) -> str:
    return text[max(0, at - 30):at + 40]


def _check_leftovers(text: str, masked: str, a: int, b: int, ctx: _Ctx) -> None:
    """Fail closed on anything link-shaped the patterns did not take in text[a:b]: a
    destination this module did not parse must not be published unchecked."""
    seg = masked[a:b]
    for m in _LEFT_INLINE.finditer(seg):
        d = m.group("d")
        if d.startswith("<") and d.endswith(">"):
            d = d[1:-1]
        if _is_external(d):
            continue
        raise PublishError(
            f"{ctx.src}: a link this tool cannot parse, near {_snippet(text, a + m.start())!r}; "
            f"nest brackets and parentheses at most {NEST_DEPTH} deep and keep the "
            f"destination within one line of '('")
    m = _LEFT_TAG.search(seg)
    if m:
        raise PublishError(
            f"{ctx.src}: an HTML tag with a {m.group(1)}= attribute this tool cannot parse, "
            f"near {_snippet(text, a + m.start())!r}; write it as name=\"value\"")


def _check_leftover_refdefs(text: str, refmask: str, taken: List[Tuple[int, int]],
                            ctx: _Ctx) -> None:
    """Fail closed on a reference definition _REFDEF_RE did not take: any '[...]:' at the
    start of a line, with a destination-shaped token after it, whose '[' lies in no match
    already rewritten. A GFM footnote ('[^name]:') is not a link, and an external token
    needs no check; anything else is a definition this module cannot read, and its
    destination would be published unchecked."""
    for m in _LEFT_REFDEF.finditer(refmask):
        at = m.start("l") - 1
        if any(s <= at < e for s, e in taken):
            continue
        note = "[" + m.group("l") + "]:"
        if _NOTE_RE.match(note) and _NOTE_RE_MM.match(note):   # a footnote to both parsers
            continue
        d = m.group("d")
        if _is_external(d[1:-1] if d.startswith("<") and d.endswith(">") else d):
            continue
        raise PublishError(
            f"{ctx.src}: a reference definition this tool cannot parse, near "
            f"{_snippet(text, at)!r}; write the label on one line without brackets in it")


def _rewrite_tag(tag: str, ctx: _Ctx) -> str:
    """One open tag with its href/src/srcset/poster values rewritten, the rest as is."""
    head = re.match(r"<" + _TAGNAME, tag).end()       # type: ignore[union-attr]
    out = [tag[:head]]
    pos = head
    for m in _TAG_ATTR_RE.finditer(tag, head):
        if m.start() != pos:
            break                 # the closing whitespace and '/>' or '>'
        vg = next((g for g in ("dq", "sq", "uq") if m.group(g) is not None), None)
        name = m.group("name").lower()
        if vg is None or name not in _LINK_ATTRS:
            out.append(m.group(0))
        else:
            value = m.group(vg)
            if name == "srcset":
                new = _rewrite_srcset(value, ctx)
            else:
                new = _resolve(value, name in ("src", "poster"), ctx)
            out.append(tag[m.start():m.start(vg)] + new + tag[m.end(vg):m.end()])
        pos = m.end()
    out.append(tag[pos:])
    return "".join(out)


def _rewrite(text: str, m: _Masked, ctx: _Ctx) -> str:
    """Rewrite a whole document, one region (leaf block) at a time."""
    out: List[str] = []
    last = 0
    for a, b in m.regions:
        out.append(text[last:a])          # the line endings between regions
        out.append(_rewrite_segment(text[a:b], m.inline[a:b], m.blocks[a:b], ctx))
        last = b
    out.append(text[last:])
    return "".join(out)


def _rewrite_segment(text: str, masked: str, refmask: Optional[str], ctx: _Ctx) -> str:
    """Rewrite text, locating links in `masked` (inline links, tags) and in `refmask`
    (reference definitions; None inside link text, where none can be)."""
    found = [(m.start(), m.end(), m) for m in _LINK_RE.finditer(masked)]
    if refmask is not None:
        found += [(m.start(), m.end(), m) for m in _REFDEF_RE.finditer(refmask)]
    found.sort(key=lambda t: (t[0], -t[1]))
    out: List[str] = []
    last = 0
    taken: List[Tuple[int, int]] = []

    def orig(m, group: str) -> str:
        # every piece is cut from the ORIGINAL text; the masks only locate them
        return text[m.start(group):m.end(group)]

    for start, end, m in found:
        if start < last:
            continue      # inside a link already taken; its own text was handled there
        _check_leftovers(text, masked, last, start, ctx)
        out.append(text[last:start])
        last = end
        taken.append((start, end))
        groups = m.groupdict()
        if groups.get("inline") is not None:
            image = bool(m.group("bang"))
            a, b = m.start("text"), m.end("text")
            inner = _rewrite_segment(text[a:b], masked[a:b], None, ctx)
            out.append(f"{orig(m, 'bang')}[{inner}]({orig(m, 'pre')}"
                       f"{_rewrite_dest(orig(m, 'dest'), image, ctx)}{orig(m, 'post')})")
        elif groups.get("tag") is not None:
            out.append(_rewrite_tag(orig(m, "tag"), ctx))
        else:
            dest = orig(m, "rdest")
            # a definition used by an image (or naming one) must stay an image: raw/
            image = _norm_label(orig(m, "label")) in ctx.image_labels or _is_image(dest)
            out.append(text[start:m.start("rdest")] + _rewrite_dest(dest, image, ctx))
    _check_leftovers(text, masked, last, len(text), ctx)
    if refmask is not None:
        _check_leftover_refdefs(text, refmask, taken, ctx)
    out.append(text[last:])
    return "".join(out)


def rewrite_links(markdown: str, src_path: str, mapping: Dict[str, str], sha: str,
                  repo: str, *, root=None, tracked: Optional[Set[str]] = None) -> str:
    """Rewrite the relative links of one published document.

    - a link to a manifest source becomes mapping[src] (a site route or a wiki page),
      keeping its #fragment;
    - a link to any other file IN THE COMMIT `sha` becomes
      https://github.com/<repo>/blob/<sha>/<path> (raw/ for images, including reference
      definitions an image uses, so they still render; tree/ for directories);
    - inline links, reference definitions (also inside block quotes and list items) and
      the href/src/srcset/poster attributes of HTML open tags (quoted or not) are
      rewritten; the same words in prose or in a URL's query are text;
    - full http(s) URLs ('//' after the scheme), mailto and bare #anchors are left
      alone; links inside code (fenced and indented code, also in list items and block
      quotes, and code spans) and inside HTML comments are not links;
    - reference definitions are read with CommonMark's label grammar (escaped brackets,
      labels over several lines, a destination on the next line of a block quote), and
      every line ending CommonMark knows (LF, CRLF, CR) ends a line;
    - anything else relative that will not resolve once published — missing, not in the
      commit, outside the repository, absolute, 'https:' without '//', or another
      scheme — raises PublishError, and so does any link-shaped text the patterns could
      not parse, a '[...]:' definition at the start of a line among it.

    `root` defaults to this checkout; `tracked` defaults to the tree of commit `sha`
    under root, the same commit the links are pinned to."""
    src = canonical_rel(src_path)
    if not (isinstance(sha, str) and SHA_RE.match(sha)):
        raise PublishError(f"sha {sha!r} must be 7-40 lowercase hex characters")
    if not (isinstance(repo, str) and REPO_RE.match(repo)):
        raise PublishError(f"repo {repo!r} must be 'owner/name'")
    root = Path(root).resolve() if root is not None else REPO
    if tracked is None:
        tracked = git_tracked(root, rev=sha)
    m = _masks(markdown)
    ctx = _Ctx(src, dict(mapping), sha, repo, root, set(tracked), _image_labels(m.inline))
    return _rewrite(markdown, m, ctx)
