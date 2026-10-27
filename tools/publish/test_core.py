#!/usr/bin/env python3
"""test_core.py — suite for the publishing tools (tools/publish/).

Uses the project's own harness convention: no pytest, prints
`RESULT: N passed, M failed`, exits non-zero on any failure. Run as a script.

    python3 -B tools/publish/test_core.py

Every fixture is a throwaway repository in a temp directory (git-initialised, and
committed, where the guard or the link rewriter needs to ask git), so the real documents,
plan and ledger are only ever READ. The assertions are on refusals, problems, exit codes
and bytes, not on wording, except where the wording is the contract (the status line, the
C2 tolerance line).

Covered:
  guard     refusals for missing, untracked (index and commit), modified, quarantined
            (both lists, and malformed lists that must quarantine everything),
            ignore-file, never_publish, C3's skip-by-name, SKIP_DIRS, non-Markdown,
            non-canonical paths, symlinks, no git, no HEAD, a root that is not the top of
            its repository, and a hostile GIT_DIR; 'modified' by bytes, so neither
            skip-worktree, assume-unchanged nor a clean filter hides an edit, and no
            filter program runs; published_text reads the commit; the real manifest's
            pages are not self-refusing.
  manifest  key allowlist, duplicates, reserved names, non-canonical never_publish; a JSON
            key given twice (a second never_publish) and a lone surrogate stop the guard.
  json      a key given twice at every level of the plan is refused, even unvalidated;
            parse_json, the one parser, refuses it in text and in a plan as a commit
            holds it, and refuses a lone surrogate, non-JSON and bytes.
  plan      unknown keys at every level, missing keys, bad dates, bad statuses, a
            vocabulary the renderer cannot read, two active phases, phase order in every
            pairing of start and end, gate order, gate-before-phase, a moved gate date
            without its changelog entry, a changelog that records a field the item does
            not have or a value of the wrong type, bad sha256, dangling references,
            status labels (also split by any whitespace, or by an id and its title, or
            hidden by a character reference, an invisible character or fullwidth letters;
            letters of another script that look Latin are the asserted known limit), a
            lone surrogate, a date past 9000-12-31, and a fuzz pass: no input raises
            anything but PlanError.
  render    determinism (twice, key order, two processes with different hash seeds),
            idempotence (--write then --check clean, --write twice byte-identical),
            markers in code fences and code spans ignored, CRLF preserved, indentation
            carried, every malformed, near-miss, over-indented, unclosed-fence, stray and
            symlinked marker exits 2 with nothing written, --check fails when it has
            nothing to check, no clock outside --status, and the rendered text passes
            C2/C3/C4 itself (also when the plan's own text spells a marker); fences in
            list items and block quotes (the reviewer's repro), a marker the parsers
            disagree is code exits 2; an end marker shown in a fenced example never ends
            an open block, and a marker comment split over lines is a near miss (both
            exit 2, the reviewer's repro included), inside a block quote too ('>', '>\\t',
            a blank '>' line, a list item in a quote, nested quotes; rendered or stray);
            a label in the rendered text exits 2
            even when the plan check is bypassed; any failure that is not a finding exits
            2, a plan that can never be written included; --write is all or nothing (a
            read-only target, a rename that fails midway, a file that fails to stage),
            keeps modes.
  gantt     ':' '#' ';' '%' '<' '>' escaped, every name's first character an entity code
            (titles that broke Mermaid 11.17.2's lexer: 'Call ...', 'Gantt ...',
            'href "..."', a leading date), open ends drawn to a horizon derived from the
            plan, a gate no phase leads to still drawn.
  markdown  CommonMark line endings; block structure in GitHub's and the site's
            readings (cases checked against micromark 4 with GFM); code_fences states;
            code spans, backslash escapes, atomic tags and comments on one line.
  ci_c2     only C2 findings in docs/paper/**.tex are tolerated, and each is listed;
            exit 2 for every ledger shape C2 cannot read, and for missing or
            non-integer totals (C2 would compare nothing).
  links     manifest targets, pinned GitHub links, images (inline, by reference,
            srcset), directories, reference definitions in quotes and lists, quoted and
            unquoted HTML attributes, nested brackets and parentheses, a destination on
            the next line, code left alone (fences in list items and block quotes,
            indented code, HTML comments), attribute words outside a tag left alone, and
            every dead or unparseable shape raises: the reviewer's repros (a fence on a
            list-item line, an escaped backtick), a tag value across a block edge, the
            shapes where GitHub's parser and the site's disagree, definitions with an
            escaped ']' or a label over several lines, CRLF and CR-only line endings, and
            'https:' without '//'.
  source    this file holds no Turkish letter and no raw invisible character, and every
            character outside ASCII in its test data is built with chr() or an escape.
"""

from __future__ import annotations

import ast
import contextlib
import copy
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import types
import unicodedata
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core                    # noqa: E402
import render_plan as RP       # noqa: E402
import ci_c2                   # noqa: E402

REPO = core.REPO
LC = core.ledger_check()
GIT = shutil.which("git") is not None

# A caller's git environment (a hook, a worktree) must not redirect the fixtures' git.
for _var in core.GIT_ENV_DROP:
    os.environ.pop(_var, None)

PASSED = 0
FAILED = 0


def check(cond: bool, label: str) -> None:
    global PASSED, FAILED
    if cond:
        PASSED += 1
    else:
        FAILED += 1
        print(f"  FAIL: {label}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def note(msg: str) -> None:
    print(f"  note: {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# fixtures
# ─────────────────────────────────────────────────────────────────────────────

FIXTURE_PLAN = {
    "_README": ["fixture plan for tools/publish/test_core.py"],
    "schema_version": 1,
    "as_of": "2026-10-23",
    "timezone": "Europe/Istanbul",
    "line": {"title": "A fixture research line", "short_name": "FX"},
    "vocabulary": {"phase": ["planned", "active", "done"],
                   "gate": ["upcoming", "decided"],
                   "deadline": ["upcoming", "met", "missed"]},
    "phases": [
        {"id": "P0", "title": "Novelty review and setup", "start": "2026-10-23",
         "end": "2026-11-15", "gate": "A", "status": "active", "outputs": ["a decision"]},
        {"id": "P1", "title": "Environments", "start": "2026-11-16", "end": "2026-12-31",
         "gate": "B", "status": "planned", "outputs": ["environments"]},
        {"id": "P2", "title": "Analysis", "start": "2027-01-01", "end": "2027-04-15",
         "gate": None, "status": "planned", "outputs": ["results"]},
        {"id": "P3", "title": "Paper", "start": "2027-04-15", "end": None,
         "end_rule": "the submission deadline", "gate": "C", "status": "planned",
         "outputs": ["a paper"]},
        {"id": "P4", "title": "Write-up", "start": None, "start_rule": "after submission",
         "end": None, "end_rule": "the release calendar", "gate": None,
         "status": "planned", "outputs": ["the write-up"]},
    ],
    "gates": [
        {"id": "A", "title": "Novelty", "baseline_date": "2026-11-15", "date": "2026-11-15",
         "status": "upcoming", "question": "Is it new?", "if_missed": "Reposition."},
        {"id": "B", "title": "Comparisons", "baseline_date": "2026-12-31",
         "date": "2026-12-31", "status": "upcoming", "question": "Do the baselines run?",
         "if_missed": "Narrow the baseline set."},
        {"id": "C", "title": "Paper", "baseline_date": None, "date": None,
         "date_rule": "one week before the deadline", "status": "upcoming",
         "question": "Is it complete?", "if_missed": "A workshop paper."},
    ],
    "deadlines": [{"id": "paper-submission", "title": "Paper submission", "due": None,
                   "estimate": "spring 2027", "status": "upcoming"}],
    "layers": [{"id": "L1", "title": "Safe base", "summary": "Stands on its own."}],
    "commitments": [],
    "changelog": [],
}

GOOD_SHA256 = "ab" * 32
COMMITMENT = {"id": "PC-001", "date": "2026-12-01", "subject": "frozen criteria",
              "sha256": GOOD_SHA256, "reveal": "at submission"}
CHANGE = {"date": "2026-11-01", "item": "A", "field": "date", "from": "2026-11-15",
          "to": "2026-11-22", "reason": "a fixture move", "ref": "fixture"}

GUARD_LEDGER = {
    "claim_quarantine_paths": ["notes/claims/"],
    "count_quarantine_paths": ["notes/counts/", "frozen.md"],
}
GUARD_MANIFEST = {
    "site_base": "/psyche/",
    "repo": "owner/name",
    "sections": [{"title": "Fixture", "pages": [
        {"src": "docs/ok.md", "slug": "ok", "wiki": "Ok"}]}],
    "never_publish": ["docs/design/", "DECISIONS.md"],
}

STATUS_LABELS = sorted(set(LC.BUILD_STATUS_ALIASES) | set(LC.MEANING_VERDICTS))
ALL_IDS = list(RP.RENDERERS)

# A path with letters outside ASCII (c-cedilla, s-cedilla, u-umlaut), built with chr():
# tools/publish/ is an English-only path (D-031 item 7), and leak_check reads the raw
# source, so the letters exist only at run time. Every other character outside ASCII in
# a test's data or expected output is built the same way (chr(), or a \u escape), above
# all the invisible ones: an editor that normalised a raw no-break space to a space would
# turn its case into a copy of the plain-space case, and it would still pass. Only prose
# (comments, docstrings, section and banner titles) keeps raw dashes; test_source_hygiene
# asserts all of this on this file's own source.
NONASCII_MD = "docs/" + chr(0xE7) + chr(0x15F) + "-" + chr(0xFC) + ".md"
MIDDOT = chr(0xB7)      # the status line's separator
EMDASH = chr(0x2014)    # an empty table cell


def plan(**over) -> dict:
    p = copy.deepcopy(FIXTURE_PLAN)
    p.update(over)
    return p


def decided_plan(step: str = "continues", gate: int = 0, on: str = "2026-11-14") -> dict:
    """The fixture plan as of 2026-11-20 with one gate decided (D-034): the date it was
    decided and one word for what follows. A phase its decision closes is marked done."""
    p = plan(as_of="2026-11-20")
    g = p["gates"][gate]
    g.update(status="decided", decided_on=on, next_step=step)
    if step in ("continues", "stops"):
        for ph in p["phases"]:
            if ph["gate"] == g["id"]:
                ph["status"] = "done"
    return p


def problems_of(p: dict) -> list:
    return core.plan_problems(p)


def has(problems: list, needle: str) -> bool:
    return any(needle in x for x in problems)


_N = [0]


def new_root(tmp: Path) -> Path:
    _N[0] += 1
    root = tmp / f"repo{_N[0]}"
    root.mkdir(parents=True)
    return root


def write(root: Path, rel: str, body, *, binary: bool = False) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        p.write_bytes(body)
    else:
        p.write_text(body, encoding="utf-8")
    return p


def git(root: Path, *args: str, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull,
                           "-c", "commit.gpgsign=false", "-C", str(root), *args],
                          capture_output=True, text=True, env=env)


def git_ok(root: Path, *args: str) -> str:
    r = git(root, *args)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in a fixture: {r.stderr}")
    return r.stdout.strip()


def git_repo(root: Path, tracked, *, commit: bool = True) -> str:
    """Initialise a fixture repository, stage `tracked` and (by default) commit it.
    Returns the commit id, or '' when nothing was committed."""
    git_ok(root, "init", "-q")
    if tracked:
        git_ok(root, "add", "--", *tracked)
    if not commit:
        return ""
    git_ok(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
           "commit", "-q", "--no-verify", "--allow-empty", "-m", "fixture")
    return git_ok(root, "rev-parse", "HEAD")


def capture(fn, *args, **kw):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = fn(*args, **kw)
    return rc, out.getvalue(), err.getvalue()


def refusal(fn) -> str:
    """The GuardRefusal reason fn raises, 'ACCEPTED' if it returns, or the type name of
    any other exception (which is itself a failure of the contract)."""
    try:
        fn()
    except core.GuardRefusal as e:
        return e.reason
    except Exception as e:  # noqa: BLE001
        return f"!{type(e).__name__}: {e}"
    return "ACCEPTED"


def raises(fn, exc=core.PublishError) -> bool:
    try:
        fn()
    except exc:
        return True
    except Exception:  # noqa: BLE001 — the wrong exception is a failure too
        return False
    return False


# ─────────────────────────────────────────────────────────────────────────────
# the guard
# ─────────────────────────────────────────────────────────────────────────────

def test_guard(tmp: Path) -> None:
    section("guard: refusals in a throwaway git repository")
    if not GIT:
        check(False, "git is required for the guard tests and was not found")
        return
    root = new_root(tmp)
    write(root, "tools/ledger.json", json.dumps(GUARD_LEDGER))
    write(root, "docs/publish.json", json.dumps(GUARD_MANIFEST))
    files = {
        "docs/ok.md": "# ok\n",
        "docs/edited.md": "# committed text\n",
        "docs/untracked.md": "# not added\n",
        "notes/claims/a.md": "# a\n",
        "notes/counts/b.md": "# b\n",
        "frozen.md": "# frozen\n",
        "docs/ignored.md": f"<!-- {LC.IGNORE_FILE} -->\n# opted out\n",
        "docs/design/v.md": "# vision\n",
        "DECISIONS.md": "# decisions\n",
        "docs/research/DECISIONS.md": "Brick 0a is PROVEN.\n",
        "docs/research/notes-psyche_roadmap.md": "Brick 0a is PROVEN.\n",
        "docs/decisions.md": "# a case variant of a C3-exempt name\n",
        "build/x.md": "# build output\n",
        "docs/node_modules/pkg/readme.md": "# vendored\n",
        ".scratch/w/x.md": "# a copy under a hidden directory\n",
        "docs/.notes/y.md": "# a hidden directory below the root\n",
        "docs/notes.txt": "plain text\n",
    }
    for rel, body in files.items():
        write(root, rel, body)
    git_repo(root, [r for r in files if r != "docs/untracked.md"])
    # after the commit: one file staged but never committed, one committed file edited
    write(root, "docs/staged.md", "# staged only\n")
    git_ok(root, "add", "--", "docs/staged.md")
    write(root, "docs/edited.md", "# edited after the commit\n")

    def guard(src, **kw):
        return lambda: core.publishable_guard(root, src, **kw)

    check(core.publishable_guard(root, "docs/ok.md") == "docs/ok.md",
          "a committed, unmodified, governed Markdown file is accepted")
    expected = {
        "docs/missing.md": "missing",
        "docs/untracked.md": "untracked",
        "docs/staged.md": "untracked",
        "docs/edited.md": "modified",
        "notes/claims/a.md": "quarantined",
        "notes/counts/b.md": "quarantined",
        "frozen.md": "quarantined",
        "docs/ignored.md": "ignore-file",
        "docs/design/v.md": "never-publish",
        "DECISIONS.md": "never-publish",
        "docs/research/DECISIONS.md": "c3-exempt",
        "docs/research/notes-psyche_roadmap.md": "c3-exempt",
        "docs/decisions.md": "c3-exempt",
        "build/x.md": "skip-dir",
        "docs/node_modules/pkg/readme.md": "skip-dir",
        ".scratch/w/x.md": "skip-dir",
        "docs/.notes/y.md": "skip-dir",
        "docs/notes.txt": "not-markdown",
        "../x.md": "path",
        "/abs.md": "path",
        "docs/./ok.md": "path",
        "docs//ok.md": "path",
        "docs/ok.md/": "path",
        "docs\\ok.md": "path",
        "": "path",
    }
    for src, reason in expected.items():
        got = refusal(guard(src))
        check(got == reason, f"guard({src!r}) refuses with {reason!r}, got {got!r}")

    section("guard: 'modified' compares bytes, never through the index or a filter")
    r2 = new_root(tmp)
    write(r2, "tools/ledger.json", json.dumps(GUARD_LEDGER))
    write(r2, "docs/publish.json", json.dumps(GUARD_MANIFEST))
    names = ["docs/ok.md", "docs/sw.md", "docs/au.md", "docs/flt.md", NONASCII_MD]
    for n in names:
        write(r2, n, "# committed\n")
    try:
        os.symlink("ok.md", r2 / "docs" / "link.md")
        names.append("docs/link.md")
    except (OSError, NotImplementedError):
        note("symlinks unavailable here; the symlink comparison was not exercised")
    git_repo(r2, names)
    secret = "# committed\nSECRET ADDED AFTER COMMIT\n"
    git_ok(r2, "update-index", "--skip-worktree", "--", "docs/sw.md")
    write(r2, "docs/sw.md", secret)
    git_ok(r2, "update-index", "--assume-unchanged", "--", "docs/au.md")
    write(r2, "docs/au.md", secret)
    check(git(r2, "diff", "--quiet", "HEAD", "--", "docs/sw.md", "docs/au.md").returncode == 0,
          "(git diff really is blind to both flagged edits, as the reviewer found)")
    for n, flag in (("docs/sw.md", "skip-worktree"), ("docs/au.md", "assume-unchanged")):
        got = refusal(lambda n=n: core.publishable_guard(r2, n))
        check(got == "modified", f"a {flag} file edited after its commit is refused ({got})")
    ran = tmp / "clean-filter-ran"
    write(r2, ".gitattributes", "*.md filter=strip\n")
    git_ok(r2, "config", "filter.strip.clean", f"touch {shlex.quote(str(ran))}; head -n 1")
    write(r2, "docs/flt.md", secret)
    got = refusal(lambda: core.publishable_guard(r2, "docs/flt.md"))
    check(got == "modified", f"an edit a clean filter would hide is refused ({got})")
    check(refusal(lambda: core.publishable_guard(r2, "docs/ok.md")) == "ACCEPTED",
          "an unedited file is still accepted with the filter configured")
    check(not ran.exists(), "no filter program ran while the guard looked")
    check(refusal(lambda: core.publishable_guard(r2, NONASCII_MD)) == "ACCEPTED",
          "a path with non-ASCII characters is compared like any other")
    write(r2, NONASCII_MD, secret)
    check(refusal(lambda: core.publishable_guard(r2, NONASCII_MD)) == "modified",
          "and refused once edited")
    if "docs/link.md" in names:
        check(refusal(lambda: core.publishable_guard(r2, "docs/link.md")) == "ACCEPTED",
              "a committed symlink whose target is unchanged is accepted")
        (r2 / "docs" / "link.md").unlink()
        os.symlink("au.md", r2 / "docs" / "link.md")
        got = refusal(lambda: core.publishable_guard(r2, "docs/link.md"))
        check(got in ("modified", "untracked"),
              f"a committed symlink pointed somewhere else is refused ({got})")
    check(core.committed_text(r2, "HEAD", "docs/sw.md") == "# committed\n",
          "committed_text reads the commit, not the edited disk")
    check(core.published_text(r2, "docs/ok.md") == "# committed\n",
          "published_text returns the commit's text for an accepted page")
    check(refusal(lambda: core.published_text(r2, "docs/sw.md")) == "modified",
          "and refuses where the guard refuses")
    check(not ran.exists(), "(still no filter program run)")

    section("guard: index semantics only when asked for (rev=None, a local preview)")
    check(refusal(guard("docs/staged.md", rev=None)) == "ACCEPTED",
          "with rev=None a staged file is accepted (the index holds it)")
    check(refusal(guard("docs/edited.md", rev=None)) == "ACCEPTED",
          "with rev=None an edited tracked file is accepted (no comparison with a commit)")
    check(refusal(guard("docs/untracked.md", rev=None)) == "untracked",
          "with rev=None an untracked file is still refused")
    check(refusal(guard("docs/ok.md", rev="no-such-branch")) == "git",
          "a revision that names no commit is refused, never assumed")
    check(refusal(guard("docs/ok.md", rev="--output=x")) == "git",
          "a revision that looks like an option is refused before git sees it")

    section("guard: C3's skip-by-name is read from ledger_check's own source")
    suffixes = core.c3_exempt_suffixes()
    check(set(core.C3_EXEMPT_BASELINE) <= set(suffixes), "the baseline is always kept")
    derived = core.c3_suffixes_from_source(core.LEDGER_CHECK_PATH.read_text(encoding="utf-8"))
    check(derived == set(core.C3_EXEMPT_BASELINE),
          f"the real check_status_vocabulary skips exactly the baseline names ({derived})")
    fake = ("def check_status_vocabulary(root, ledger):\n"
            "    for rel in []:\n"
            "        if rel.endswith('psyche_roadmap.md') or rel.endswith(('NEW.md', 'X.md')):\n"
            "            continue\n"
            "        if line.endswith(':'):\n"
            "            pass\n")
    check(core.c3_suffixes_from_source(fake) == {"psyche_roadmap.md", "NEW.md", "X.md"},
          "a suffix added to ledger_check would be picked up; endswith on other names is not")

    section("guard: a quarantine list C2/C4 would misread quarantines everything")
    for name, value in (("an empty entry", [""]), ("a non-string entry", [5]),
                        ("a null list", None), ("a string, not a list", "notes/")):
        led = dict(GUARD_LEDGER, count_quarantine_paths=value)
        got = refusal(lambda led=led: core.publishable_guard(root, "docs/ok.md", ledger=led))
        check(got == "quarantined", f"count_quarantine_paths = {name} refuses docs/ok.md ({got})")
    led = {k: v for k, v in GUARD_LEDGER.items() if k != "claim_quarantine_paths"}
    check(refusal(lambda: core.publishable_guard(root, "docs/ok.md", ledger=led)) == "ACCEPTED",
          "an ABSENT list is ledger_check's default (empty) and quarantines nothing")
    bad_m = dict(GUARD_MANIFEST, never_publish=["/docs/design/"])
    check(raises(lambda: core.publishable_guard(root, "docs/ok.md", manifest=bad_m)),
          "a manifest handed to the guard is validated too")

    got = refusal(guard("DOCS/DESIGN/v.md"))
    check(got in ("never-publish", "missing"),
          f"a case variant of a never_publish path is refused, never accepted (got {got!r})")

    try:
        os.symlink("design/v.md", root / "docs" / "alias.md")
        (tmp / "outside.md").write_text("# outside\n", encoding="utf-8")
        os.symlink(str(tmp / "outside.md"), root / "docs" / "out.md")
        symlinks = True
    except (OSError, NotImplementedError):
        symlinks = False
        note("symlinks unavailable here; the symlink refusals were not exercised")
    if symlinks:
        check(refusal(guard("docs/alias.md")) == "never-publish",
              "a symlink is judged by what it resolves to: a governed name cannot carry a "
              "never_publish file out")
        check(refusal(guard("docs/out.md")) == "outside",
              "a symlink resolving outside the repository is refused")

    section("guard: git answers for root and nothing else")
    bare = new_root(tmp)
    write(bare, "tools/ledger.json", json.dumps(GUARD_LEDGER))
    write(bare, "docs/publish.json", json.dumps(GUARD_MANIFEST))
    write(bare, "docs/ok.md", "# ok\n")
    check(refusal(lambda: core.publishable_guard(bare, "docs/ok.md")) == "git",
          "outside any git repository the answer is 'no', never an assumed 'yes'")
    nohead = new_root(tmp)
    write(nohead, "tools/ledger.json", json.dumps(GUARD_LEDGER))
    write(nohead, "docs/publish.json", json.dumps(GUARD_MANIFEST))
    write(nohead, "docs/ok.md", "# ok\n")
    git_repo(nohead, ["docs/ok.md"], commit=False)
    check(refusal(lambda: core.publishable_guard(nohead, "docs/ok.md")) == "git",
          "a repository with no commit at all proves nothing: refused")
    check(refusal(lambda: core.publishable_guard(nohead, "docs/ok.md", rev=None)) == "ACCEPTED",
          "(the same file is in its index, which rev=None asks)")
    sub = root / "docs"
    check(refusal(lambda: core.publishable_guard(sub, "ok.md", manifest=GUARD_MANIFEST,
                                                 ledger=GUARD_LEDGER)) == "git",
          "a root that is a subdirectory of a repository is refused: its parent may not "
          "answer for it")

    # GIT_DIR names a sibling repository that DOES track the probe path
    sibling = new_root(tmp)
    write(sibling, "docs/probe.md", "# tracked over there\n")
    git_repo(sibling, ["docs/probe.md"])
    write(root, "docs/probe.md", "# untracked here\n")
    saved = {k: os.environ.get(k) for k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")}
    try:
        os.environ["GIT_DIR"] = str(sibling / ".git")
        os.environ["GIT_WORK_TREE"] = str(root)
        os.environ["GIT_INDEX_FILE"] = str(sibling / ".git" / "index")
        hostile_head = refusal(guard("docs/probe.md"))
        hostile_index = refusal(guard("docs/probe.md", rev=None))
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    check(hostile_head == "untracked" and hostile_index == "untracked",
          f"GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE naming another repository do not change "
          f"the answer ({hostile_head}, {hostile_index})")

    section("guard: the real manifest, read only")
    m = core.load_manifest(REPO)
    led = core.load_ledger(REPO)
    pages = core.manifest_pages(m)
    check(len(pages) >= 1, "the real manifest lists pages")
    required = {"docs/design/", "docs/paper/", "docs/report/", "docs/specs/",
                "docs/experiments/", "docs/psyche_roadmap.md", "docs/CONSCIOUSNESS-YARDSTICK.md",
                "DECISIONS.md", "MOC.md"}
    check(required <= set(m["never_publish"]), "never_publish holds every required entry")
    exempt = [s.casefold() for s in core.c3_exempt_suffixes()]
    for p in pages:
        src = p["src"]
        check(core.never_publish_hit(m, src) is None,
              f"manifest page {src} is not itself under never_publish")
        hit = (core._quarantine_hit(src, led.get("claim_quarantine_paths", core._MISSING))
               or core._quarantine_hit(src, led.get("count_quarantine_paths", core._MISSING)))
        check(hit is None, f"manifest page {src} is not quarantined by the real ledger")
        check(core._skip_dir_hit(src, LC.SKIP_DIRS) is None,
              f"manifest page {src} is inside the tree ledger_check walks")
        check(not any(src.casefold().endswith(s) for s in exempt),
              f"manifest page {src} is not a name C3 skips")
    for src in ("DECISIONS.md", "MOC.md", "docs/psyche_roadmap.md",
                "docs/CONSCIOUSNESS-YARDSTICK.md"):
        check(refusal(lambda s=src: core.publishable_guard(REPO, s, manifest=m, ledger=led))
              == "never-publish", f"the real repository refuses {src}")
    site = core.link_mapping(m, "site")
    check(site.get("docs/research/README.md") == "/psyche/research/",
          "the research overview's site route is /psyche/research/")
    check(len(set(site.values())) == len(site), "site routes are unique")

    section("manifest: validation")
    bad = copy.deepcopy(GUARD_MANIFEST)
    bad["extra"] = 1
    bad["sections"][0]["pages"].append({"src": "docs/ok.md", "slug": "Bad Slug", "wiki": "Home"})
    probs = core.manifest_problems(bad)
    check(has(probs, "unknown key 'extra'"), "an unknown manifest key is refused")
    check(has(probs, "listed twice"), "a duplicated src is refused")
    check(has(probs, ".slug"), "a malformed slug is refused")
    check(has(probs, "reserved wiki page"), "a reserved wiki name is refused")
    check(core.manifest_problems(GUARD_MANIFEST) == [], "the fixture manifest is valid")
    for entry in ("/docs/design/", "./docs/paper/", "docs\\report\\", "docs//x/", "docs/../x/",
                  "", 5):
        m2 = dict(GUARD_MANIFEST, never_publish=["docs/design/", entry])
        check(has(core.manifest_problems(m2), "never_publish[1]"),
              f"a non-canonical never_publish entry {entry!r} is refused (it would match nothing)")
    m2 = dict(GUARD_MANIFEST, never_publish=["docs/design/", "docs/paper/", "x.md"])
    check(core.manifest_problems(m2) == [], "canonical files and '/'-ended directories pass")

    section("manifest: a key given twice, or a lone surrogate, stops the run before any guard")
    good = (root / "docs/publish.json").read_bytes()
    check(refusal(lambda: core.publishable_guard(root, "docs/design/v.md")) == "never-publish",
          "(base: docs/design/v.md is refused by never_publish alone)")
    full = json.dumps(GUARD_MANIFEST)
    dup = full[:-1] + ', "never_publish": ["docs/drafts/"]}'
    check(json.loads(dup)["never_publish"] == ["docs/drafts/"]
          and core.manifest_problems(json.loads(dup)) == [],
          "(not vacuous: json.loads keeps the last value, and the validator alone sees a "
          "valid manifest)")
    m3 = copy.deepcopy(GUARD_MANIFEST)
    m3["sections"][0]["title"] = "Fixture " + chr(0xD800)
    check(has(core.manifest_problems(m3), "lone surrogate"),
          "manifest_problems refuses a lone surrogate (no path or page can carry one)")
    try:
        write(root, "docs/publish.json", dup)
        check(raises(lambda: core.load_manifest(root)),
              "load_manifest refuses a never_publish key given twice")
        got = refusal(lambda: core.publishable_guard(root, "docs/design/v.md"))
        check(got.startswith("!PublishError") and "twice" in got,
              f"the guard stops on it before judging a page: docs/design/v.md is never "
              f"accepted ({got[:70]})")
        write(root, "docs/publish.json",
              full.replace('"slug": "ok"', '"slug": "ok", "slug": "ok"'))
        check(raises(lambda: core.load_manifest(root)),
              "a key given twice inside a page object is refused too")
        write(root, "docs/publish.json", json.dumps(m3))
        check(raises(lambda: core.load_manifest(root)),
              "a manifest file whose JSON escapes spell a lone surrogate is refused")
    finally:
        write(root, "docs/publish.json", good, binary=True)
    check(refusal(lambda: core.publishable_guard(root, "docs/ok.md")) == "ACCEPTED",
          "(the fixture manifest is restored)")


# ─────────────────────────────────────────────────────────────────────────────
# plan validation
# ─────────────────────────────────────────────────────────────────────────────

def test_plan() -> None:
    section("plan: valid inputs pass")
    check(problems_of(plan()) == [], f"the fixture plan is valid: {problems_of(plan())}")
    real = core.load_plan(REPO, validate=False)
    check(core.plan_problems(real) == [],
          f"the real tools/research_plan.json is valid: {core.plan_problems(real)}")
    p = plan()
    check(p["phases"][2]["end"] == p["phases"][3]["start"] and problems_of(p) == [],
          "a shared boundary day (end == next start) is allowed")

    section("plan: an unknown key is refused at every level")
    levels = [
        ("top", lambda p: p),
        ("line", lambda p: p["line"]),
        ("vocabulary", lambda p: p["vocabulary"]),
        ("phase", lambda p: p["phases"][0]),
        ("gate", lambda p: p["gates"][0]),
        ("deadline", lambda p: p["deadlines"][0]),
        ("layer", lambda p: p["layers"][0]),
        ("commitment", lambda p: p["commitments"][0]),
        ("changelog", lambda p: p["changelog"][0]),
    ]
    for name, at in levels:
        p = plan(commitments=[dict(COMMITMENT)],
                 changelog=[dict(CHANGE, to="2026-11-15", item="A")])
        check(problems_of(p) == [], f"[{name}] the base for the injection is valid "
                                    f"{problems_of(p)}")
        at(p)["threshold"] = 1
        check(has(problems_of(p), "unknown key 'threshold'"),
              f"[{name}] an unknown key is refused")

    section("plan: missing keys, types")
    p = plan()
    del p["phases"][0]["outputs"]
    check(has(problems_of(p), "missing key 'outputs'"), "a missing required key is refused")
    p = plan()
    del p["gates"]
    check(has(problems_of(p), "missing key 'gates'"), "a missing top-level key is refused")
    check(has(problems_of(plan(schema_version=True)), "schema_version"),
          "schema_version True is not the integer 1")
    check(has(problems_of(plan(schema_version=2)), "schema_version"),
          "an unknown schema_version is refused")
    check(core.plan_problems([]) != [], "a plan that is not an object is refused")

    section("plan: dates")
    for where, setter in (
            ("as_of", lambda p: p.update(as_of="2026-10-32")),
            ("phase start", lambda p: p["phases"][0].update(start="2026-1-5")),
            ("phase end", lambda p: p["phases"][0].update(end="20261115")),
            ("gate date", lambda p: p["gates"][0].update(date="2026-11-15T00:00",
                                                         baseline_date="2026-11-15T00:00")),
            ("deadline due", lambda p: p["deadlines"][0].update(due="next spring")),
            ("commitment date", lambda p: p.update(commitments=[dict(COMMITMENT, date="soon")])),
            ("changelog date", lambda p: p.update(changelog=[dict(CHANGE, date="2026/11/01",
                                                                  to="2026-11-15")])),
    ):
        p = plan()
        setter(p)
        check(has(problems_of(p), "not an ISO date"), f"a bad {where} is refused")
    p = plan()
    p["phases"][1]["start"], p["phases"][1]["end"] = "2026-12-31", "2026-11-16"
    check(has(problems_of(p), "is after end"), "a phase that ends before it starts is refused")
    p = plan()
    del p["phases"][3]["end_rule"]
    check(has(problems_of(p), "null without a end_rule"), "an open end must name its rule")
    p = plan()
    p["phases"][0]["start_rule"] = "whenever"
    check(has(problems_of(p), "start_rule is given although start is fixed"),
          "a fixed date and a rule together are refused")

    section("plan: statuses and the vocabulary the renderer reads")
    for where, setter in (
            ("phase", lambda p: p["phases"][1].update(status="Planned")),
            ("gate", lambda p: p["gates"][0].update(status="passed")),
            ("deadline", lambda p: p["deadlines"][0].update(status="late")),
            ("phase (a list)", lambda p: p["phases"][1].update(status=["planned"])),
    ):
        p = plan()
        setter(p)
        check(has(problems_of(p), "is not in vocabulary"), f"a bad {where} status is refused")
    p = plan()
    p["vocabulary"]["phase"] = ["planned", "Active", "done"]
    check(has(problems_of(p), "lowercase words"), "a capitalised vocabulary word is refused")
    for kind, words, statuses, needle in (
            ("gate", ["open", "closed"], "open", "gives no meaning"),
            ("gate", ["pending", "decided"], "pending", "lacks ['upcoming']"),
            ("gate", ["upcoming"], "upcoming", "lacks ['decided']"),
            ("phase", ["planned", "current", "done"], None, "gives no meaning"),
            ("phase", ["planned", "done"], None, "lacks ['active']"),
            ("deadline", ["upcoming", "slipped"], None, "gives no meaning"),
    ):
        p = plan()
        p["vocabulary"][kind] = words
        if statuses and kind == "gate":
            for g in p["gates"]:
                g["status"] = statuses
        check(has(problems_of(p), needle),
              f"vocabulary.{kind} = {words} is refused ({needle})")
    p = plan()
    p["phases"][1]["status"] = "active"
    check(has(problems_of(p), "at most one phase"), "two active phases are refused")
    p = plan()
    p["phases"][1]["title"] = "Setup " + STATUS_LABELS[0]
    check(has(problems_of(p), "status label"),
          f"a capitalised status label ({STATUS_LABELS[0]}) in plan text is refused")
    # the renderer collapses whitespace and writes an id before its title, so a label
    # split across either still reaches the rendered line (reviewer's repros)
    for desc, mutate in (
            ("two spaces", lambda p: p["gates"][0].update(title="BUILT  UNVALIDATED review")),
            ("a no-break space",
             lambda p: p["gates"][0].update(title="BUILT" + chr(0xA0) + "UNVALIDATED review")),
            ("a tab", lambda p: p["gates"][0].update(title="BUILT\tUNVALIDATED review")),
            ("a newline", lambda p: p["gates"][0].update(title="BUILT\nUNVALIDATED review")),
            ("a gate id and its title",
             lambda p: (p["gates"][0].update(id="BUILT", title="UNVALIDATED review"),
                        p["phases"][0].update(gate="BUILT"))),
            ("a phase id and its title",
             lambda p: p["phases"][1].update(id="NOT", title="YET review"))):
        p = plan()
        mutate(p)
        check(has(problems_of(p), "status label"),
              f"a status label split by {desc} is refused: {problems_of(p)[:2]}")

    section("plan: no date the gantt cannot draw")
    for where, setter in (
            ("a deadline due 9999-12-01", lambda p: p["deadlines"][0].update(due="9999-12-01")),
            ("a phase ending 9500-01-01", lambda p: p["phases"][2].update(end="9500-01-01")),
            ("as_of 9001-01-01", lambda p: p.update(as_of="9001-01-01"))):
        p = plan()
        setter(p)
        check(has(problems_of(p), "is after 9000-12-31"), f"{where} is refused")
    p = plan()
    p["deadlines"][0]["due"] = "9000-12-31"
    check(problems_of(p) == [] and "9001-03-02" in RP.render_all(p)["plan-gantt"],
          "9000-12-31 is accepted and its open ends still draw (9000-12-31 + 61 days)")

    section("plan: phase ordering, every pairing of start and end")
    p = plan()
    p["phases"][1], p["phases"][2] = p["phases"][2], p["phases"][1]
    check(has(problems_of(p), "out of order"), "phases listed out of date order are refused")
    p = plan()
    p["phases"][1]["start"] = "2026-11-10"
    check(has(problems_of(p), "overlap"), "a phase starting before the previous ends is refused")
    p = plan()
    p["phases"][4]["start"], p["phases"][4]["start_rule"] = "2027-01-01", None
    del p["phases"][4]["start_rule"]
    check(has(problems_of(p), "overlap") or has(problems_of(p), "out of order"),
          "an open-ended phase in between does not hide an overlap with an earlier one "
          "(the check is pairwise, not neighbour to neighbour)")
    p = plan()
    p["phases"][1].update(start=None, start_rule="after P0", end="2026-01-01")
    check(has(problems_of(p), "phases[1] ends before phases[0] starts"),
          "an undated start cannot hide a fixed end before an earlier phase starts")
    real = core.load_plan(REPO, validate=False)
    for end in ("2026-01-01", "2027-03-10"):
        r = copy.deepcopy(real)
        r["phases"][-1]["end"] = end
        r["phases"][-1].pop("end_rule", None)
        check(has(problems_of(r), "ends before"),
              f"the real plan's last phase (undated start) ending {end} is refused")
    p = plan()
    p["phases"][0]["end"] = "2026-11-16"   # ends ON the next phase's start: allowed
    check(problems_of(p) == [], f"a shared boundary day still passes {problems_of(p)}")

    section("plan: gates in date order, after their phase starts, reached in list order")
    p = plan()
    p["gates"][1]["date"] = p["gates"][1]["baseline_date"] = "2026-10-30"
    p["phases"][1]["start"] = "2026-10-01"
    check(has(problems_of(p), "gates are out of order"),
          "gate B dated before gate A is refused")
    p = plan()
    p["gates"][1]["date"] = p["gates"][1]["baseline_date"] = "2026-11-15"
    check(has(problems_of(p), "before the phase starts"),
          "a phase's gate dated before the phase starts is refused")
    p = plan()
    p["phases"][0]["gate"], p["phases"][1]["gate"] = "B", "A"
    check(has(problems_of(p), "in the order gates[] lists them"),
          "phases that reach gate B before gate A are refused")

    section("plan: references and ids")
    p = plan()
    p["phases"][0]["gate"] = "Z"
    check(has(problems_of(p), "names no gate"), "a phase naming a missing gate is refused")
    p = plan()
    p["gates"][1]["id"] = "A"
    check(has(problems_of(p), "duplicate gate id"), "a duplicate gate id is refused")
    p = plan(changelog=[dict(CHANGE, item="nothing", to="2026-11-15")])
    check(has(problems_of(p), "names nothing"), "a changelog entry about no item is refused")

    section("plan: a moved gate date needs its changelog entry")
    p = plan()
    p["gates"][0]["date"] = "2026-11-22"
    check(has(problems_of(p), "no changelog entry"), "a moved date without a changelog is refused")
    p["changelog"] = [dict(CHANGE)]
    check(problems_of(p) == [], f"the same move with its changelog entry passes {problems_of(p)}")
    p["changelog"] = [dict(CHANGE, to="2026-11-29")]
    check(has(problems_of(p), "no changelog entry"),
          "a changelog entry recording a DIFFERENT destination does not excuse the move")
    p["changelog"] = [dict(CHANGE, item="B")]
    check(has(problems_of(p), "no changelog entry"),
          "a changelog entry for another gate does not excuse the move")

    section("plan: a decided gate carries only its date and one word for what follows")
    for step in core.NEXT_STEPS:
        check(problems_of(decided_plan(step)) == [],
              f"a gate decided with next_step {step!r} is valid {problems_of(decided_plan(step))}")
    p = decided_plan("continues", gate=1, on="2026-11-19")
    check(problems_of(p) == [], f"a later gate may be decided on its own {problems_of(p)}")
    p["phases"][1]["status"] = "planned"
    check(has(problems_of(p), "its gate B is decided"),
          "gate B decided while its phase P1 is still planned is refused")
    p = decided_plan()
    del p["gates"][0]["decided_on"]
    check(has(problems_of(p), "needs decided_on"), "a decided gate without its date is refused")
    p = decided_plan()
    del p["gates"][0]["next_step"]
    check(has(problems_of(p), "needs next_step"), "a decided gate without its next step is refused")
    p = plan()
    p["gates"][0]["decided_on"] = "2026-10-01"
    check(has(problems_of(p), "decided_on is given although the gate is not decided"),
          "a decision date on an upcoming gate is refused")
    p = plan()
    p["gates"][0]["next_step"] = "continues"
    check(has(problems_of(p), "next_step is given although the gate is not decided"),
          "a next step on an upcoming gate is refused")
    for bad in ("passed", "Continues", "continues because the baselines held", "", None, 1,
                ["continues"], True):
        p = decided_plan()
        p["gates"][0]["next_step"] = bad
        check(has(problems_of(p), "must be one of"),
              f"next_step {bad!r} is refused: the word comes from a fixed list, never free text")
    for key in ("verdict", "evidence", "reason", "outcome"):
        p = decided_plan()
        p["gates"][0][key] = "x"
        check(has(problems_of(p), f"unknown key '{key}'"),
              f"a gate cannot carry a '{key}' field: the record is the date and the next step")
    for bad, needle in (("20261114", "not an ISO date"), ("2026-11-31", "not an ISO date"),
                        (None, "may not be null"), ("2026-11-21", "after the plan's as_of")):
        p = decided_plan()
        p["gates"][0]["decided_on"] = bad
        check(has(problems_of(p), needle), f"decided_on {bad!r} is refused ({needle})")
    p = decided_plan(on="2026-11-20")
    check(problems_of(p) == [], "a gate decided on the plan's own as_of date is valid")
    p = decided_plan(on="2026-11-10")
    check(problems_of(p) == [], "a gate decided before its date is valid")
    p = decided_plan("continues")
    p["phases"][0]["status"] = "active"
    check(has(problems_of(p), "so the phase must be 'done'"),
          "a phase whose gate is decided (the line continues) cannot stay active")
    p = decided_plan("stops")
    p["phases"][0]["status"] = "planned"
    check(has(problems_of(p), "so the phase must be 'done'"),
          "a phase whose gate is decided (the line stops) cannot stay planned")
    p = decided_plan("extends")
    p["phases"][0]["status"] = "active"
    check(problems_of(p) == [], f"a phase stays active when its gate extends it {problems_of(p)}")
    p = decided_plan("continues")
    p["phases"][1]["status"] = "active"
    check(problems_of(p) == [], f"the next phase may be active once the gate is decided "
                                f"{problems_of(p)}")
    for old_plan in (plan(), core.load_plan(REPO, validate=False)):
        check(not any("decided_on" in g or "next_step" in g for g in old_plan["gates"])
              and core.plan_problems(old_plan) == [],
              "a plan with no decided gate stays valid: the new fields are optional")

    section("plan: the changelog records only fields the item has, typed")
    ok = {"date": "2026-11-01", "item": "P1", "field": "end", "from": "2026-12-31",
          "to": "2027-01-05", "reason": "r", "ref": "x"}
    check(problems_of(plan(changelog=[ok])) == [],
          f"a phase end move is a loggable field {problems_of(plan(changelog=[ok]))}")
    for desc, entry, needle in (
            ("field 'threshold'", {"item": "A", "field": "threshold", "from": "0.80", "to": "0.85"},
             "not a field the changelog may record"),
            ("field 'criterion' on a phase", {"item": "P0", "field": "criterion"},
             "not a field the changelog may record"),
            ("a gate's 'start'", {"item": "A", "field": "start", "from": None, "to": "2026-11-01"},
             "not a field a gate has"),
            ("a phase's 'date'", {"item": "P0", "field": "date", "to": "2026-11-01"},
             "not a field a phase has"),
            ("a status outside the vocabulary", {"item": "A", "field": "status",
                                                 "from": "upcoming", "to": "passed"},
             "is not in vocabulary.gate"),
            ("a date field with a non-date value", {"item": "P1", "field": "end",
                                                   "from": "2026-12-31", "to": "soon"},
             "is not an ISO date"),
            ("a gate field naming no gate", {"item": "P2", "field": "gate", "from": None,
                                            "to": "Z"}, "names no gate"),
            ("a value that is not a string", {"item": "L1", "field": "title", "to": 0.85},
             "must be a string or null"),
    ):
        e = dict(ok, **entry)
        check(has(problems_of(plan(changelog=[e])), needle), f"a changelog with {desc} is refused")
    p = plan(changelog=[dict(ok, item="A", field="date", **{"from": "2026-11-15", "to": "2026-11-15"})])
    p["phases"][2]["id"] = "A"   # a phase and a gate now share the id 'A'
    check(has(problems_of(p), "is ambiguous"), "a changelog item naming two kinds is refused")

    section("plan: sha256")
    check(problems_of(plan(commitments=[dict(COMMITMENT)])) == [], "64 lowercase hex passes")
    for bad in (GOOD_SHA256[:-1], GOOD_SHA256.upper(), "g" * 64, GOOD_SHA256 + "0", 12):
        check(has(problems_of(plan(commitments=[dict(COMMITMENT, sha256=bad)])), "sha256"),
              f"sha256 {str(bad)[:12]}... is refused")

    section("plan: a label a reader sees is refused however it is spelled")
    fullwidth = "".join(chr(0xFF00 + ord(c) - 0x20) for c in "PROVEN")
    hidden = {
        "a hex character reference": "Is it &#x50;ROVEN?",
        "a decimal character reference": "Is it &#80;ROVEN?",
        "a named character reference": "Is it PRO&shy;VEN?",
        "a zero-width space": "Is it P" + chr(0x200B) + "ROVEN?",
        "a soft hyphen": "Is it PRO" + chr(0xAD) + "VEN?",
        "a word joiner": "Is it P" + chr(0x2060) + "ROVEN?",
        "a variation selector": "Is it P" + chr(0xFE0F) + "ROVEN?",
        "a reference to an invisible character": "Is it P&#x200B;ROVEN?",
        "fullwidth letters": "Is it " + fullwidth + "?",
    }
    for name, text in hidden.items():
        p = plan()
        p["gates"][0]["question"] = text
        check(has(problems_of(p), "status label"), f"{name} ({text!a}): refused")
    p = plan()
    p["gates"][0]["question"] = "Is it &#x50;roven, and P&amp;L in order?"
    check(problems_of(p) == [], f"references that spell no label pass {problems_of(p)}")
    # KNOWN LIMIT (core.reader_view): a capital of another script that only looks Latin
    # (Cyrillic O, U+041E) is not folded. Asserted, so a change in either direction is seen.
    p = plan()
    p["gates"][0]["question"] = "Is it PR" + chr(0x41E) + "VEN?"
    check(problems_of(p) == [],
          "KNOWN LIMIT: a Cyrillic capital in place of a Latin one is not caught")

    section("plan: a lone surrogate is an invalid plan, never 'stale' or a crash")
    p = plan()
    p["gates"][0]["if_missed"] = "Reposition " + chr(0xD800) + " the contribution."
    check(has(problems_of(p), "lone surrogate") and has(problems_of(p), "gates[0].if_missed"),
          f"a lone surrogate in a value is refused and located {problems_of(p)}")
    p = plan()
    p["layers"][0]["x" + chr(0xDC00)] = "y"
    check(has(problems_of(p), "lone surrogate"), "and in a key")
    check(raises(lambda: core.validate_plan(p), core.PlanError), "validate_plan raises PlanError")

    section("plan: validate_plan raises only PlanError")
    try:
        core.validate_plan(plan(as_of="nope"))
        check(False, "validate_plan raises on an invalid plan")
    except core.PlanError as e:
        check(bool(e.problems) and isinstance(e, core.PublishError),
              "PlanError carries the problem list and is a PublishError")
    for bad_id in (["A"], {"k": "A"}, 7, None):
        p = plan()
        p["gates"][0]["id"] = bad_id
        p["gates"][0]["date"] = "2026-11-20"
        try:
            probs = core.plan_problems(p)
            ok_list = isinstance(probs, list) and bool(probs)
        except Exception as e:  # noqa: BLE001
            ok_list = False
            note(f"plan_problems raised {type(e).__name__}: {e}")
        check(ok_list, f"a gate id {bad_id!r} with a moved date is a problem, not a crash")
    p = plan(changelog=[dict(CHANGE, field=["date"], item={"A": 1})])
    check(isinstance(core.plan_problems(p), list), "unhashable changelog values are problems")
    real_problems = core.plan_problems
    try:
        def boom(_plan):
            raise TypeError("a validator bug")
        core.plan_problems = boom
        check(raises(lambda: core.validate_plan(plan()), core.PlanError),
              "were plan_problems ever to crash, validate_plan still raises only PlanError")
    finally:
        core.plan_problems = real_problems


# A fuzz pass: every node of a plan replaced by every value of the wrong shape. No input
# may make plan_problems raise; an input it accepts must render.
WEIRD = [None, True, 0, 1.5, "", "x", "2026-11-20", [], ["A"], {}, {"k": 1}, [{"id": []}],
         "x" + chr(0xD800)]


def _paths(obj, path=()):
    yield path
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _paths(v, path + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _paths(v, path + (i,))


def _set_at(obj, path, value):
    if not path:
        return value
    cur = obj
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = value
    return obj


def test_plan_fuzz() -> None:
    section("plan: fuzz — no shape of input escapes as anything but a problem list")
    base = plan(commitments=[dict(COMMITMENT)], changelog=[dict(CHANGE)])
    base["gates"][0]["date"] = "2026-11-22"
    check(problems_of(base) == [], f"the fuzz base is valid {problems_of(base)}")
    crashes, render_crashes, runs = [], [], 0
    for path in list(_paths(base)):
        for value in WEIRD:
            p = _set_at(copy.deepcopy(base), path, copy.deepcopy(value))
            runs += 1
            try:
                probs = core.plan_problems(p)
                assert isinstance(probs, list)
            except Exception as e:  # noqa: BLE001
                crashes.append(f"{path}={value!r}: {type(e).__name__}: {e}")
                continue
            try:
                core.validate_plan(p)
            except core.PlanError:
                continue
            except Exception as e:  # noqa: BLE001
                crashes.append(f"validate {path}={value!r}: {type(e).__name__}")
                continue
            try:
                RP.render_all(p)
            except Exception as e:  # noqa: BLE001
                render_crashes.append(f"{path}={value!r}: {type(e).__name__}: {e}")
    check(runs > 500, f"the fuzz ran {runs} mutations")
    check(crashes == [], f"plan_problems never raises: {crashes[:3]}")
    check(render_crashes == [], f"a plan that validates always renders: {render_crashes[:3]}")


def test_load_plan_errors(tmp: Path) -> None:
    section("plan: load_plan validates unless told not to")
    root = new_root(tmp)
    write(root, "tools/research_plan.json", "{ not json")
    check(raises(lambda: core.load_plan(root)), "load_plan refuses invalid JSON")
    write(root, "tools/research_plan.json", b"\xff\xfe{}", binary=True)
    check(raises(lambda: core.load_plan(root)), "load_plan refuses bytes that are not UTF-8")
    write(root, "tools/research_plan.json", "[]")
    check(raises(lambda: core.load_plan(root), core.PlanError),
          "load_plan refuses a JSON array with PlanError")
    p = plan()
    p["gates"][0]["threshold"] = 0.85
    write(root, "tools/research_plan.json", json.dumps(p))
    check(raises(lambda: core.load_plan(root), core.PlanError),
          "load_plan alone refuses a field outside the allowlist")
    check(core.load_plan(root, validate=False)["gates"][0]["threshold"] == 0.85,
          "the unvalidated read exists, but must be asked for")

    section("plan: a key given twice is refused at every level, even unvalidated")
    # The first value is the one a reader of the file sees; json.loads keeps the last.
    levels = [
        ("top", lambda p: p, "timezone", "PROVEN by 0a, see threshold"),
        ("line", lambda p: p["line"], "title", "PROVEN by 0a, see threshold"),
        ("vocabulary", lambda p: p["vocabulary"], "phase", ["PROVEN"]),
        ("phase", lambda p: p["phases"][0], "title", "PROVEN by 0a, see threshold"),
        ("gate", lambda p: p["gates"][0], "baseline_date", "PROVEN by 0a, see threshold"),
        ("deadline", lambda p: p["deadlines"][0], "title", "PROVEN by 0a, see threshold"),
        ("layer", lambda p: p["layers"][0], "summary", "PROVEN by 0a, see threshold"),
        ("commitment", lambda p: p["commitments"][0], "subject", "PROVEN by 0a, see threshold"),
        ("changelog", lambda p: p["changelog"][0], "reason", "PROVEN by 0a, see threshold"),
    ]
    for name, at, key, hidden in levels:
        p = plan(commitments=[dict(COMMITMENT)],
                 changelog=[dict(CHANGE, to="2026-11-15", item="A")])
        obj = at(p)
        obj["__DUP__"] = obj[key]          # the last occurrence: valid
        obj[key] = hidden                  # the first occurrence: what a reader sees
        text = json.dumps(p).replace('"__DUP__"', json.dumps(key))
        seen = json.loads(text)
        check(core.plan_problems(seen) == [],
              f"[{name}] (not vacuous: parsed, the plan shows only the last value and is valid)")
        write(root, "tools/research_plan.json", text)
        check(raises(lambda: core.load_plan(root)), f"[{name}] load_plan refuses {key!r} twice")
        check(raises(lambda: core.load_plan(root, validate=False)),
              f"[{name}] so does the unvalidated read")
    rc, _, err = capture(RP.main, ["--root", str(root), "--check"])
    check(rc == 2 and "twice" in err, f"render_plan stops on it before rendering: exit 2 ({rc})")
    write(root, "tools/research_plan.json", json.dumps(plan()).replace(
        '"if_missed": "Reposition."', '"if_missed": "Reposition ' + "\\" + 'ud800 now."'))
    check(raises(lambda: core.load_plan(root, validate=False)),
          "a plan file whose JSON escapes spell a lone surrogate is refused, even unvalidated")

    section("json: parse_json is the one parser, for a file on disk or as a commit holds it")
    good_text = json.dumps(plan())
    check(core.parse_json(good_text, "fixture") == json.loads(good_text),
          "parse_json reads a valid plan exactly as json.loads does")
    dup_top = good_text[:-1] + ', "timezone": "UTC"}'
    dup_deep = good_text.replace('"title": "Novelty", ', '"title": "Novelty", "title": "N", ', 1)
    check(json.loads(dup_top)["timezone"] == "UTC" and dup_deep != good_text,
          "(not vacuous: json.loads keeps the last value, and the nested fixture changed)")
    for desc, text in (("at the top", dup_top), ("inside a gate", dup_deep)):
        try:
            core.parse_json(text, "the plan at abc123")
            check(False, f"parse_json refuses a key given twice {desc} (it returned)")
        except core.PublishError as e:
            check("twice" in str(e) and "the plan at abc123" in str(e),
                  f"parse_json refuses a key given twice {desc}, naming what it read: {e}")
    check(raises(lambda: core.parse_json('{"a": "x' + "\\" + 'ud800"}', "fixture")),
          "parse_json refuses a lone surrogate spelled by an escape")
    check(raises(lambda: core.parse_json("{ not json", "fixture")),
          "parse_json refuses text that is not JSON")
    utf16 = good_text.encode("utf-16")
    check(json.loads(utf16) == json.loads(good_text)
          and raises(lambda: core.parse_json(utf16, "fixture")),
          "parse_json refuses bytes, which json.loads would read even as UTF-16")
    if GIT:
        rc_root = new_root(tmp)
        write(rc_root, "tools/research_plan.json", dup_deep)
        git_repo(rc_root, ["tools/research_plan.json"])
        committed = core.committed_text(rc_root, "HEAD", core.PLAN_REL.as_posix())
        check(core.plan_problems(json.loads(committed)) == [],
              "(not vacuous: a plain json.loads of the committed plan validates)")
        check(raises(lambda: core.parse_json(committed, "tools/research_plan.json at HEAD")),
              "a committed plan with a key given twice is refused through parse_json, the "
              "route a site builder reading a commit must take (stage.committed_json, owned "
              "by stage.py, is the caller to switch)")
    else:
        note("git not found: the committed-plan case of parse_json was skipped")


# ─────────────────────────────────────────────────────────────────────────────
# rendering
# ─────────────────────────────────────────────────────────────────────────────

EXPECTED_STATUS = ("**Now:** P0 Novelty review and setup (2026-10-23 to 2026-11-15) "
                   + MIDDOT + " **Next gate:** A Novelty, 2026-11-15")


def _gantt_tasks(gantt: str) -> list:
    directives = ("```", "gantt", "dateFormat", "axisFormat", "section")
    return [ln.strip() for ln in gantt.splitlines()
            if ln.strip() and not ln.strip().startswith(directives)]


_NAMED_ENTITIES = {"lt": "<", "gt": ">", "quot": '"', "amp": "&"}


def _decode(s: str) -> str:
    """Mermaid entity codes (#NN; and #name;) decoded, as the chart shows them."""
    return re.sub(r"#(\d+|[a-z]+);", lambda m: chr(int(m.group(1))) if m.group(1).isdigit()
                  else _NAMED_ENTITIES[m.group(1)], s)


def _decoded_lines(gantt: str) -> list:
    return [_decode(ln) for ln in gantt.splitlines()]


def test_render_pure(tmp: Path) -> None:
    section("render: pure, deterministic, order-independent")
    a = RP.render_all(plan())
    b = RP.render_all(plan())
    check(a == b, "rendering twice gives identical output")
    shuffled = json.loads(json.dumps(plan(), sort_keys=True))
    check(RP.render_all(shuffled) == a, "dict key order in the plan does not change the output")
    check(set(a) == set(RP.RENDERERS), "every block id renders")
    check(a["status-line"] == EXPECTED_STATUS, f"the status line has the agreed form: "
                                               f"{a['status-line']!r}")
    p = plan()
    p["phases"][0]["status"] = "done"
    for g in p["gates"]:
        g["status"] = "decided"
    check(RP.render_status_line(p) == ("**Now:** no phase is active " + MIDDOT
                                       + " **Next gate:** none upcoming"),
          "with nothing active or upcoming the status line says so")
    p = plan()
    p["gates"][0]["status"] = "decided"
    check("**Next gate:** B Comparisons, 2026-12-31" in RP.render_status_line(p),
          "a decided gate hands 'next' to the first gate still upcoming")
    p = plan()
    p["gates"][0]["date"] = "2026-11-22"
    p["changelog"] = [dict(CHANGE)]
    check("2026-11-22 (baseline 2026-11-15)" in RP.render_gates_table(p),
          "a moved gate shows its baseline beside the new date")
    table = RP.render_gates_table(decided_plan("continues"))
    check("| decided on 2026-11-14; the line continues to the next phase |" in table
          and "| upcoming |" in table,
          "the gates table gives a decided gate its date and next step, and an undecided one its status")
    check("the line extends |" in RP.render_gates_table(decided_plan("extends"))
          and "the line stops |" in RP.render_gates_table(decided_plan("stops")),
          "the other two next steps read in the project's own words")
    line = RP.render_status_line(decided_plan("continues"))
    check("**Next gate:** B Comparisons, 2026-12-31" in line and "Novelty" not in line,
          "once gate A is decided the status line leads with gate B")
    check(RP.render_status_line(decided_plan("stops")).endswith(
          "**Next gate:** none, the line stops at gate A"),
          "after a decision that the line stops, the status line says so and names no later gate")
    check(RP.render_status_line(decided_plan("extends")).startswith(
          "**Now:** P0 Novelty review and setup"),
          "a decision that extends the phase leaves it the current one")
    for step in core.NEXT_STEPS:
        out = "\n".join(RP.render_all(decided_plan(step)).values())
        check(RP.render_all(decided_plan(step)) == RP.render_all(decided_plan(step))
              and "decided on 2026-11-14" in out
              and not any(lab in out for lab in STATUS_LABELS),
              f"a plan with a gate decided ({step}) renders deterministically, with no status label")
    rp_src = (HERE / "render_plan.py").read_text(encoding="utf-8")
    check(not re.search(r'== "(?:active|done|upcoming|decided|planned)"', rp_src),
          "the renderer compares statuses only through core's shared constants")

    pt = a["phases-table"]
    check("| P3 | Paper | 2027-04-15 | the submission deadline | C | planned |" in pt,
          "an open end shows its rule in the phases table")
    check(f"| P4 | Write-up | after submission | the release calendar | {EMDASH} | planned |"
          in pt,
          "an undated start shows its rule and a gateless phase shows a dash")
    check(f"| none yet | {EMDASH} | {EMDASH} | {EMDASH} | {EMDASH} |" in a["commitments-table"],
          "no commitments renders a 'none yet' row")
    ct = RP.render_commitments_table(plan(commitments=[dict(COMMITMENT)]))
    check(f"`{GOOD_SHA256}`" in ct and "none yet" not in ct, "a commitment renders its hash")
    check("not set; estimate: spring 2027" in a["deadlines-table"],
          "an undated deadline shows its estimate")
    check("A \\| B" in RP.render_layers_table(plan(layers=[{"id": "L1", "title": "A | B",
                                                           "summary": "s"}])),
          "a '|' in plan text cannot break a table row")

    section("render: no capitalised status label, ever")
    outputs = list(a.values()) + list(RP.render_all(core.load_plan(REPO)).values())
    for lab in STATUS_LABELS:
        check(not any(lab in o for o in outputs), f"no rendered block contains {lab!r}")

    section("render: the rendered text passes C2, C3 and C4 itself (loop-closed)")
    root = new_root(tmp)
    shutil.copy(REPO / core.LEDGER_REL, write(root, "tools/ledger.json", "{}"))
    led = LC.load_ledger(root)
    body = "\n\n".join(f"<!-- generated:{k}:start -->\n{v}\n<!-- generated:{k}:end -->"
                       for blocks in (a, RP.render_all(core.load_plan(REPO)))
                       for k, v in blocks.items())
    write(root, "docs/rendered.md", body + "\n")
    check("0d" in body, "the fixture really contains the '0d' milestone token C3 would read")
    for name, fn in (("C2", LC.check_prose_vs_ledger), ("C3", LC.check_status_vocabulary),
                     ("C4", LC.check_forbidden_claims)):
        got = fn(root, led)
        check(got == [], f"{name} finds nothing in the rendered blocks: "
                         f"{[f.message for f in got][:3]}")

    section("render: the clock is read only by --status")
    tree = ast.parse((HERE / "render_plan.py").read_text(encoding="utf-8"))
    clock_users = set()
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef):
            for node in ast.walk(fn):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr in ("now", "today", "utcnow", "time")):
                    clock_users.add(fn.name)
    check(clock_users == {"today_in_zone"},
          f"only today_in_zone reads the clock (found: {sorted(clock_users)})")
    status_callers = {fn.name for fn in ast.walk(tree) if isinstance(fn, ast.FunctionDef)
                      for node in ast.walk(fn)
                      if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                      and node.func.id in ("today_in_zone", "status_report")}
    check(status_callers == {"main"}, f"only main reaches the clock (found {status_callers})")

    section("render: --status arithmetic with a fixed today")
    pub = {"program": {"substrate": {"state": "paused", "since": "2026-10-23",
                                     "decision": "D-031"},
                       "cognitive_map": {"state": "active", "since": "2026-10-23",
                                         "decision": "D-031"}},
           "aim": "a fixture aim"}
    rep = RP.status_report(plan(), pub, date(2026, 10, 23), "fixture zone")
    check("next gate  A Novelty: 2026-11-15, in 23 days" in rep, "23 days to gate A")
    check("  substrate     paused since 2026-10-23 (D-031)" in rep
          and "  cognitive_map active since 2026-10-23 (D-031)" in rep,
          "program state is reported, one line per line of work")
    check("  aim           a fixture aim" in rep, "the project's aim is reported as the "
                                                 "ledger states it")
    check("Research plan (tools/research_plan.json, as of 2026-10-23)" in rep,
          "the plan header names the research plan")
    rep = RP.status_report(plan(), pub, date(2026, 11, 20), "fixture zone")
    check("5 days ago, decision pending" in rep, "an overdue gate says its decision is pending")
    rep = RP.status_report(decided_plan("continues"), pub, date(2026, 11, 20), "fixture zone")
    check("decided    A Novelty: decided on 2026-11-14; the line continues to the next phase" in rep
          and "next gate  B Comparisons: 2026-12-31, in 41 days" in rep,
          "a decided gate is reported with its date and next step, and the next gate moves on")
    rep = RP.status_report(decided_plan("stops"), pub, date(2026, 11, 20), "fixture zone")
    check("next gate  none, the line stops at gate A" in rep,
          "no gate follows a decision that the line stops")
    rep = RP.status_report(plan(), pub, date(2026, 11, 15), "fixture zone")
    check("2026-11-15, today" in rep, "a gate due today says today")


def test_past_due() -> None:
    section("render: --past-due lists gates past their date with no recorded decision")
    ids = lambda p, d: [g["id"] for g in RP.past_due_gates(p, d)]   # noqa: E731
    check(ids(plan(), date(2026, 11, 14)) == [] and ids(plan(), date(2026, 11, 15)) == [],
          "a gate is not late before its date, nor on it")
    check(ids(plan(), date(2026, 11, 16)) == ["A"], "the day after its date, gate A is late")
    check(ids(plan(), date(2099, 1, 1)) == ["A", "B"],
          "a gate with no fixed date (gate C) is never past due, however late the day")
    check(ids(decided_plan("continues"), date(2026, 11, 20)) == [],
          "a decided gate is never past due")
    check(ids(decided_plan("continues"), date(2027, 1, 5)) == ["B"],
          "the next gate becomes past due on its own date")
    check(ids(decided_plan("stops"), date(2027, 1, 5)) == []
          and ids(decided_plan("stops"), date(2099, 1, 1)) == [],
          "after a decision that stops the line no later gate is waited on, so none is past due")
    check(ids(decided_plan("extends"), date(2027, 1, 5)) == ["B"],
          "a decision that extends the phase leaves the later gates waiting")
    check(RP.past_due_report(decided_plan("stops"), date(2027, 1, 5), annotations=True)
          == ["render_plan: no gate is past its date without a recorded decision"],
          "the report raises no warning for a gate the line stopped before")
    rep = RP.past_due_report(plan(), date(2026, 11, 20))
    check(len(rep) == 1 and rep[0].startswith("warning: Gate A (Novelty) was due on 2026-11-15, "
                                              "5 days ago") and "::" not in rep[0],
          f"the plain report names the gate, its date and how late: {rep}")
    ann = RP.past_due_report(plan(), date(2027, 1, 1), annotations=True)
    check(len(ann) == 2 and all(a.startswith("::warning title=Gate decision pending::") for a in ann)
          and "Gate A (Novelty)" in ann[0] and "Gate B (Comparisons)" in ann[1],
          f"each late gate is one GitHub warning annotation: {ann}")
    none = RP.past_due_report(plan(), date(2026, 10, 23), annotations=True)
    check(none == ["render_plan: no gate is past its date without a recorded decision"],
          "with none late the line says so and is not an annotation")
    p = plan()
    p["gates"][0]["title"] = "100% sure\r\n::error::forged"
    one = RP.past_due_report(p, date(2026, 11, 20), annotations=True)
    check(len(one) == 1 and "\n" not in one[0] and "\r" not in one[0]
          and "100%25 sure%0D%0A::error::forged" in one[0],
          "a plan string cannot start a second workflow command: %, CR and LF are escaped")
    rep = "\n".join(RP.past_due_report(plan(), date(2026, 11, 20)))
    check(not any(lab in rep for lab in STATUS_LABELS) and "verdict" not in rep.lower(),
          "the report names the gate, its title and its date, and carries no detail")


def test_gantt() -> None:
    section("gantt: structure and the plan-derived horizon")
    g = RP.render_plan_gantt(plan())
    lines = g.splitlines()
    check(lines[0] == "```mermaid" and lines[1] == "gantt" and lines[-1] == "```",
          "a fenced mermaid gantt")
    check("    dateFormat YYYY-MM-DD" in lines, "dateFormat YYYY-MM-DD")
    check(sum(1 for ln in lines if ln.startswith("    section ")) == len(plan()["phases"]),
          "one section per phase (no gate or deadline sections needed here)")
    # By hand: the latest dated point is 2027-04-15; 61 days on is 2027-06-15, and the
    # next open phase runs a further 61 days, to 2027-08-15.
    check(RP.OPEN_END_DAYS == 61, "the horizon margin is the documented 61 days")
    shown = _decoded_lines(g)
    check("    Paper * :ph3, 2027-04-15, 2027-06-15" in shown,
          "an open end is drawn to the plan-derived horizon")
    check("    Write-up * :ph4, 2027-06-15, 2027-08-15" in shown,
          "an undated phase follows the previous bar for the fixed span")
    check("    Gate C Paper * :milestone, gt2, 2027-06-15, 0d" in shown,
          "an undated gate sits at its phase's drawn end and says so")
    check("    Novelty review and setup :active, ph0, 2026-10-23, 2026-11-15" in shown,
          "the active phase carries mermaid's lowercase 'active' tag")
    check("    #78;ovelty review and setup :active, ph0, 2026-10-23, 2026-11-15" in lines,
          "written with its first character as an entity code")
    p = plan()
    p["deadlines"][0]["due"] = "2027-05-20"
    g2 = RP.render_plan_gantt(p)
    shown2 = _decoded_lines(g2)
    check("    section Deadlines" in shown2 and "    Paper submission :crit, milestone, dl0, "
          "2027-05-20, 0d" in shown2, "a dated deadline is a milestone in its own section")
    check("2027-07-20" in g2,
          "a later dated point moves the horizon (2027-05-20 + 61 days = 2027-07-20)")
    p = plan()
    p["phases"][3]["gate"] = None   # gate C (undated) is now reached by no phase
    g3 = RP.render_plan_gantt(p)
    check(problems_of(p) == [] and "    section Gates" in _decoded_lines(g3)
          and "    Gate C Paper * :milestone, gt2, 2027-06-15, 0d"
          in _decoded_lines(g3),
          "an undated gate no phase leads to is drawn at the horizon, not dropped")

    section("gantt: no task or section name can start like a lexer rule")
    # Mermaid 11.17.2's gantt lexer tries, before a task name, case-insensitive rules for
    # 'call', 'href "', 'click', 'gantt', 'title', 'section', ... and a leading date. Each
    # of these titles validated and broke the whole chart when its first letter was
    # written as is (checked against mermaid.parse 11.17.2).
    risky = ["Call for papers review", "Gantt review", 'href "x" review', "2027-01-01 kickoff",
             "Click here", "Title page", "section two", "dateFormat x", "weekday monday",
             "%% not a comment", "x%y", "Ends: soon; #1 % 50%% <!-- x -->"]
    for title in risky:
        p = plan()
        p["phases"][1]["title"] = title
        p["gates"][1]["title"] = title
        p["deadlines"][0].update(due="2027-05-20", title=title)
        check(problems_of(p) == [], f"{title!r} validates (so the renderer must cope)")
        gt = RP.render_plan_gantt(p)
        names = [ln.strip()[len("section "):] if ln.strip().startswith("section ")
                 else ln.strip().split(" :", 1)[0]
                 for ln in gt.splitlines()[4:-1]]
        check(all(re.match(r"#\d+;", nm) for nm in names),
              f"{title!r}: every task and section name starts with an entity code")
        shown = _decoded_lines(gt)
        check(any(ln.strip().startswith(f"{title} :ph1,") for ln in shown)
              and any(ln.strip().startswith(f"Gate B {title} :milestone") for ln in shown)
              and any(ln.strip().startswith(f"{title} :crit, milestone, dl0") for ln in shown),
              f"{title!r}: and decodes back to the title exactly")
        bare = [re.sub(r"#\w+;", "", ln.split(" :", 1)[0]) for ln in gt.splitlines()[4:-1]]
        check(not any(c in b for b in bare for c in "%;#<>"),
              f"{title!r}: no raw '%' ';' '#' '<' '>' in a name")

    section("gantt: escaping")
    title = "Setup: phase #1; 50% done <x>"
    p = plan()
    p["phases"][0]["title"] = title
    task = [t for t in _gantt_tasks(RP.render_plan_gantt(p)) if ":active, ph0," in t][0]
    name = task.split(" :", 1)[0]
    bare = re.sub(r"#\w+;", "", name)
    check(not any(c in bare for c in ":;%#<>"),
          f"outside its entity codes the task name has no ':' ';' '%' '#' '<' '>': {name!r}")
    check(task.count(":") == 1, "the only raw ':' on the line is the name/data separator")
    check(_decode(name) == title, "the entity codes decode back to the title exactly")
    p = plan()
    p["phases"][1]["title"] = "Title page and lifestyle notes"
    task = [t for t in _gantt_tasks(RP.render_plan_gantt(p)) if ":ph1, " in t][0]
    name = task.split(" :", 1)[0]
    check(not name.lower().startswith("title"), "a name starting with a gantt keyword is defanged")
    check("style" not in name, "the word 'style' is defanged against mermaid's pre-parse")
    check(_decode(name) == "Title page and lifestyle notes", "and still decodes to the original")
    p = plan()
    p["gates"][0]["title"] = 'Say "no" & <stop>; 100% #1'
    p["gates"][0]["if_missed"] = 'Say "no" & <stop>; 100% #1'
    flow = RP.render_gate_flow(p)
    node = [ln for ln in flow.splitlines() if ln.strip().startswith('g0["')][0]
    inner = node.split('g0["', 1)[1].rsplit('"]', 1)[0]
    bare = inner.replace("<br/>", "")
    check('"' not in bare and "<" not in bare and ">" not in bare and "&" not in bare,
          f"a flowchart label carries no raw quote, angle bracket or ampersand: {inner!r}")
    check("#quot;" in inner and "#amp;" in inner and "#lt;" in inner, "they are entity codes")
    check(" --> ".join(f"g{i}" for i in range(3)) in flow, "gates chain in plan order")
    check('- **Gate A** (Say "no" & \\<stop\\>; 100% #1): Say "no" & \\<stop\\>; 100% #1'
          in flow.splitlines(),
          "the 'if missed' note under the diagram is Markdown-escaped plan text, in full")
    test_gate_flow()


def _flow_nodes(flow: str) -> dict:
    """{node id: [label line as the chart shows it]} for every quoted node of a flowchart."""
    out = {}
    for ln in flow.splitlines():
        m = re.match(r'^    ([a-z]+\d*)\["(.*)"\]$', ln)
        if m:
            out[m.group(1)] = [_decode(x) for x in m.group(2).split("<br/>")]
    return out


def test_gate_flow() -> None:
    section("gate flow: Mermaid that GitHub renders without clipping")
    want_init = '%%{init: {"htmlLabels": false, "markdownAutoWrap": false, "flowchart": {"htmlLabels": false, "wrappingWidth": 400}}}%%'
    check(RP.FLOW_INIT == want_init, "the init line is exactly the agreed one")
    real = core.load_plan(REPO)
    hostile = plan()
    hostile["gates"][0]["title"] = " ".join(["Comparisons"] * 9)
    hostile["gates"][1]["title"] = "x" * 70
    hostile["gates"][2]["date_rule"] = " ".join(["one week before"] * 6)
    for label, p in (("fixture", plan()), ("real", real), ("hostile", hostile),
                     ("no gates", plan(gates=[]))):
        flow = RP.render_gate_flow(p)
        lines = flow.splitlines()
        check(lines[:3] == ["```mermaid", want_init, "flowchart LR"],
              f"[{label}] the fence opens with the init line, then the flowchart")
        nodes = _flow_nodes(flow)
        check(len(nodes) == max(1, len(p["gates"])), f"[{label}] one node per gate, "
                                                     f"or one that says there are none")
        long = {k: v for k, v in nodes.items()
                if len(v) > RP.FLOW_LABEL_LINES or any(len(x) > RP.FLOW_LABEL_WIDTH for x in v)}
        check(RP.FLOW_LABEL_WIDTH == 22 and RP.FLOW_LABEL_LINES == 3 and long == {},
              f"[{label}] every label line is at most 22 characters, every label at most 3 "
              f"lines: {long}")
        body = lines[lines.index("flowchart LR") + 1:lines.index("```", 1)]
        edges = [x for x in body if "-->" in x or "-." in x or "==>" in x or "---" in x]
        check(all(re.match(r"^    g\d+( --> g\d+)+$", x) for x in edges)
              and not any("|" in x for x in edges),
              f"[{label}] plain arrows only, no edge label: {edges}")
        check(all(re.match(r'^    (?:[a-z]+\d*\[".*"\]|g\d+( --> g\d+)+|classDef .*|class .*)$', x)
                  for x in body),
              f"[{label}] every statement is a quoted node, a plain arrow or a class line")
        check(len(nodes) <= 12, f"[{label}] at most 12 nodes")
        tail = "\n".join(lines[lines.index("```", 1) + 1:])
        for g in p["gates"]:
            check(f"- **Gate {RP.md(g['id'])}** ({RP.md(g['title'])}): {RP.md(g['if_missed'])}"
                  in tail, f"[{label}] gate {g['id']}'s 'if missed' note is under the diagram, "
                           f"in full")
        check(not p["gates"] or "Each arrow leads to the next gate in plan order." in tail,
              f"[{label}] a sentence under the diagram says what the arrows mean")
        check(RP.render_checked(p)["gate-flow"] == flow if p["gates"] else True,
              f"[{label}] the flow passes the rendered-label check")
    nodes = _flow_nodes(RP.render_gate_flow(plan()))
    check(nodes["g0"] == ["Gate A: Novelty", "2026-11-15 " + MIDDOT + " upcoming"],
          f"a dated gate: its name, then its date and status on one line {nodes['g0']}")
    check(nodes["g2"] == ["Gate C: Paper", "date not fixed", "upcoming"],
          f"an undated gate says so; its rule stays in the gates table {nodes['g2']}")
    nodes = _flow_nodes(RP.render_gate_flow(hostile))
    first = nodes["g0"]
    check(len(first) == 3 and first[1].endswith(chr(0x2026))
          and (first[0] + " " + first[1][:-1]).startswith("Gate A: Comparisons Comparisons")
          and first[2] == "2026-11-15 " + MIDDOT + " upcoming",
          f"a long title is wrapped, then cut with an ellipsis, never reworded {first}")
    check(nodes["g1"][0] == "Gate B: " + "x" * 14 and nodes["g1"][1].endswith(chr(0x2026)),
          f"a word longer than a line is broken inside it {nodes['g1']}")
    check(nodes["g2"] == ["Gate C: Paper", "date not fixed", "upcoming"],
          "a long date rule never reaches the label")
    check(RP.wrap_words("  a  b\tc ", 3) == ["a b", "c"] and RP.wrap_words("", 5) == []
          and RP.wrap_words("abcdefg", 3) == ["abc", "def", "g"],
          "wrap_words: whitespace collapses, words wrap, a long word breaks")
    check(RP.clip_lines(["a", "b"], 2) == ["a", "b"]
          and RP.clip_lines(["abc", "d"], 1, 3) == ["ab" + chr(0x2026)],
          "clip_lines: kept whole when it fits, else cut with an ellipsis within the width")


def _doc_fixture(root: Path, p: dict) -> None:
    """Every block id placed at least once, so --check has something to check."""
    write(root, "tools/research_plan.json", json.dumps(p, indent=2))
    shutil.copy(REPO / core.LEDGER_REL, write(root, "tools/ledger.json", "{}"))
    write(root, "README.md",
          "# Fixture\n\nIntro text stays.\n\n<!-- generated:status-line:start -->\n"
          "<!-- generated:status-line:end -->\n\nMiddle.\n\n"
          "<!-- generated:plan-gantt:start -->\nstale hand-written gantt\n"
          "<!-- generated:plan-gantt:end -->\nTail without newline")
    write(root, "MOC.md", "<!-- generated:status-line:start -->\n<!-- generated:status-line:end -->\n"
                          "\nShown as code, not a block: `<!-- generated:gate-flow:start -->`.\n")
    write(root, "docs/research/roadmap.md",
          "# Roadmap\n\nThe marker syntax, shown as an example:\n\n```text\n"
          "<!-- generated:phases-table:start -->\nthis example must not be rewritten\n"
          "<!-- generated:phases-table:end -->\n```\n\n"
          "<!-- generated:phases-table:start -->\n<!-- generated:phases-table:end -->\n\n"
          "- a list item\n\n  <!-- generated:layers-table:start -->\n"
          "  <!-- generated:layers-table:end -->\n")
    write(root, "docs/research/crlf.md",
          b"# CRLF\r\n\r\n<!-- generated:gates-table:start -->\r\n"
          b"<!-- generated:gates-table:end -->\r\nend\r\n", binary=True)
    write(root, "docs/research/flow.md",
          "<!-- generated:gate-flow:start -->\n<!-- generated:gate-flow:end -->\n\n"
          "<!-- generated:deadlines-table:start -->\n<!-- generated:deadlines-table:end -->\n\n"
          "<!-- generated:commitments-table:start -->\n"
          "<!-- generated:commitments-table:end -->\n")


def _outside_blocks(text: str) -> str:
    return re.sub(r"(<!-- generated:([a-z-]+):start -->).*?(<!-- generated:\2:end -->)",
                  r"\1\3", text, flags=re.S)


def _bytes(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()
            and ".git" not in p.relative_to(root).parts}


def test_render_documents(tmp: Path) -> None:
    section("documents: --check, --write, idempotence")
    root = new_root(tmp)
    _doc_fixture(root, plan())
    before = {p: p.read_bytes() for p in RP.target_files(root)}
    rc, out, _ = capture(RP.main, ["--root", str(root), "--check"])
    check(rc == 1 and "stale  README.md" in out, f"--check on empty blocks exits 1 ({rc})")
    check({p: p.read_bytes() for p in RP.target_files(root)} == before, "--check writes nothing")
    rc, out, _ = capture(RP.main, ["--root", str(root), "--write"])
    check(rc == 0, f"--write exits 0 ({rc})")
    rc, out, _ = capture(RP.main, ["--root", str(root), "--check"])
    check(rc == 0, f"--check after --write is clean ({rc}): {out}")
    after = {p: p.read_bytes() for p in RP.target_files(root)}
    rc, out, _ = capture(RP.main, ["--root", str(root), "--write"])
    check({p: p.read_bytes() for p in RP.target_files(root)} == after,
          "a second --write changes no byte (idempotent)")
    check("wrote" not in out, "and reports nothing written")

    readme = (root / "README.md").read_text(encoding="utf-8")
    check(EXPECTED_STATUS in readme, "README carries the rendered status line")
    check("stale hand-written gantt" not in readme, "hand-written block content is replaced")
    check(readme.endswith("Tail without newline"), "text after the last block is untouched")
    for path, old in before.items():
        old_t = old.decode("utf-8")
        new_t = path.read_bytes().decode("utf-8")
        check(_outside_blocks(new_t.replace("this example must not be rewritten", ""))
              == _outside_blocks(old_t.replace("this example must not be rewritten", "")),
              f"{path.name}: nothing outside the blocks changed")
    road = (root / "docs/research/roadmap.md").read_text(encoding="utf-8")
    check("this example must not be rewritten" in road, "a marker inside a code fence is ignored")
    check(road.count("| P0 |") == 1, "exactly one phases table was rendered")
    check("  <!-- generated:layers-table:start -->\n  | Layer | Title | Summary |\n  |---|" in road,
          "an indented marker opens a block, and the generated lines carry its indentation "
          "(the block stays inside its list item)")
    moc = (root / "MOC.md").read_text(encoding="utf-8")
    check("`<!-- generated:gate-flow:start -->`" in moc and moc.count("flowchart") == 0,
          "a marker inside a code span is text, not a block")
    crlf = (root / "docs/research/crlf.md").read_bytes()
    check(b"| Gate | Title |" in crlf and b"\n" not in crlf.replace(b"\r\n", b""),
          "a CRLF file stays CRLF, generated lines included")

    section("documents: byte-identical across processes and hash seeds")
    outs = []
    for seed in ("0", "1"):
        r2 = new_root(tmp)
        _doc_fixture(r2, plan())
        env = dict(os.environ, PYTHONHASHSEED=seed)
        proc = subprocess.run([sys.executable, "-B", str(HERE / "render_plan.py"),
                               "--root", str(r2), "--write"], capture_output=True, text=True,
                              env=env)
        check(proc.returncode == 0, f"subprocess --write exits 0 (seed {seed}): {proc.stderr}")
        outs.append({p.relative_to(r2).as_posix(): p.read_bytes() for p in RP.target_files(r2)})
    check(outs[0] == outs[1], "two processes with different hash seeds write identical bytes")
    check(outs[0] == {p.relative_to(root).as_posix(): b for p, b in after.items()},
          "and identical to the in-process render")

    section("documents: the plan's own text cannot plant a marker")
    p = plan()
    spelled = "x <!-- generated:status-line:start --> y"
    p["phases"][0]["title"] = "Setup " + spelled
    p["gates"][0]["title"] = "Novelty " + spelled
    p["gates"][0]["if_missed"] = spelled
    p["layers"][0]["summary"] = spelled
    p["deadlines"][0]["title"] = "Submission " + spelled
    check(problems_of(p) == [], f"such a plan validates {problems_of(p)}")
    r5 = new_root(tmp)
    _doc_fixture(r5, p)
    rc1, _, err1 = capture(RP.main, ["--root", str(r5), "--write"])
    rc2, _, err2 = capture(RP.main, ["--root", str(r5), "--check"])
    check(rc1 == 0 and rc2 == 0, f"--write then --check stay clean ({rc1}, {rc2}) {err1}{err2}")

    section("documents: malformed and near-miss markers exit 2, nothing written")
    filler = "OLD HAND-TYPED 2026-12-01\n"
    cases = {
        "unknown id": "<!-- generated:no-such-block:start -->\n<!-- generated:no-such-block:end -->\n",
        "never closed": "<!-- generated:status-line:start -->\ntext\n",
        "end without start": "text\n<!-- generated:status-line:end -->\n",
        "mismatched end": "<!-- generated:status-line:start -->\n<!-- generated:gate-flow:end -->\n",
        "nested start": ("<!-- generated:status-line:start -->\n<!-- generated:gate-flow:start -->\n"
                         "<!-- generated:gate-flow:end -->\n<!-- generated:status-line:end -->\n"),
        "no space before -->": ("# x\n\n<!-- generated:status-line:start-->\n" + filler
                                + "<!-- generated:status-line:end-->\n"),
        "no space after <!--": ("<!--generated:status-line:start -->\n" + filler
                                + "<!--generated:status-line:end -->\n"),
        "capitalised id": ("<!-- generated:Status-Line:start -->\n" + filler
                           + "<!-- generated:Status-Line:end -->\n"),
        "underscore id": ("<!-- generated:status_line:start -->\n" + filler
                          + "<!-- generated:status_line:end -->\n"),
        "spaces inside": ("<!-- generated: status-line :start -->\n" + filler
                          + "<!-- generated: status-line :end -->\n"),
        "upper-case GENERATED": ("<!-- GENERATED:status-line:start -->\n" + filler
                                 + "<!-- GENERATED:status-line:end -->\n"),
        "text before the marker": ("Note <!-- generated:status-line:start -->\n" + filler
                                   + "<!-- generated:status-line:end -->\n"),
        "a near miss inside a block": ("<!-- generated:status-line:start -->\n"
                                       "<!-- generated:status-line:end-->\n"
                                       "<!-- generated:status-line:end -->\n"),
        "four-space indent": ("    <!-- generated:status-line:start -->\n" + filler
                              + "    <!-- generated:status-line:end -->\n"),
        "tab indent": ("\t<!-- generated:status-line:start -->\n" + filler
                       + "\t<!-- generated:status-line:end -->\n"),
        "a fence that never closes": ("```\n<!-- generated:status-line:start -->\n" + filler
                                      + "<!-- generated:status-line:end -->\n"),
        "a fence that ends with its list item": (
            "- ```\n  <!-- generated:status-line:start -->\n  " + filler
            + "x\n<!-- generated:status-line:end -->\n"),
        # GitHub's parser reads '-' as an empty list item after indented code and so
        # ends the fence at 'c', making the markers code inside a second fence; the
        # site's parser (micromark) reads '-' as text, closes the fence at '  ~~~' and
        # renders the markers as comments. A marker on a line the parsers disagree is
        # code is refused, never guessed.
        "a marker the parsers disagree is code": (
            "    x\n-\n  ~~~\nc\n  ~~~\n<!-- generated:status-line:start -->\n" + filler
            + "<!-- generated:status-line:end -->\n~~~\n"),
        # An end marker shown in a closed fence is an example, never the end of the open
        # block above it: taking it would delete the prose between and leave the fence's
        # closing line opening a new fence (the reviewer's repro, and its smaller form).
        "an end marker shown in a fenced example": (
            "<!-- generated:status-line:start -->\n## Generated blocks\n\nprose\n\n```text\n"
            "<!-- generated:status-line:end -->\n```\n\n## Determinism tiers\n"),
        "an end marker in the fence right below the start": (
            "<!-- generated:status-line:start -->\n```\n<!-- generated:status-line:end -->\n"
            "```\n"),
        "an end marker in an unclosed fence inside the block": (
            "<!-- generated:status-line:start -->\n```\n<!-- generated:status-line:end -->\n"),
        # Markdown reads '<!--' to '-->' as one comment across lines, so a split marker
        # hides exactly as a marker does and the text between two of them would be safe.
        "a marker comment split over lines": (
            "<!--\ngenerated:status-line:start -->\n" + filler
            + "<!--\ngenerated:status-line:end -->\n"),
        "a split marker opened inside a paragraph": (
            "Note <!--\n  generated:status-line:start -->\n" + filler
            + "Note <!--\n  GENERATED:status-line:end -->\n"),
        # Inside a block quote the next line's '>' is the quote's, not the comment's, so
        # each pair below is one comment per marker to micromark 4 (checked) and to
        # GitHub; a scan that skipped only whitespace after the line break saw nothing
        # and passed the hand-typed line between them (the reviewer's repro first).
        "a split marker in a block quote": (
            "# Status\n\n> <!--\n> generated:status-line:start -->\n"
            "> **Now:** P0 hand typed (2026-01-01 to 2026-02-02)\n"
            "> <!--\n> generated:status-line:end -->\n"),
        "a split marker in a block quote, a blank '>' line between": (
            "> <!--\n>\n> generated:status-line:start -->\n> " + filler
            + "> <!--\n>\n> generated:status-line:end -->\n"),
        "a split marker in a block quote, '>\\t' prefixes": (
            ">\t<!--\n>\tgenerated:status-line:start -->\n>\t" + filler
            + ">\t<!--\n>\tgenerated:status-line:end -->\n"),
        "a split marker in a list item inside a block quote": (
            "> - <!--\n>   generated:status-line:start -->\n>   " + filler
            + "> - <!--\n>   generated:status-line:end -->\n"),
        "a split marker in a nested block quote": (
            "> > <!--\n> >\n> > generated:status-line:start -->\n> > " + filler
            + "> > <!--\n> >\n> > generated:status-line:end -->\n"),
    }
    for name, body in cases.items():
        r3 = new_root(tmp)
        write(r3, "tools/research_plan.json", json.dumps(plan()))
        # README.md is scanned FIRST and is valid but stale; MOC.md is malformed.
        write(r3, "README.md", "<!-- generated:status-line:start -->\n"
                               "<!-- generated:status-line:end -->\n")
        write(r3, "MOC.md", body)
        before3 = {n: (r3 / n).read_bytes() for n in ("README.md", "MOC.md")}
        for flag in ("--write", "--check"):
            rc, _, err = capture(RP.main, ["--root", str(r3), flag])
            check(rc == 2 and "MOC.md" in err, f"{name}: {flag} exits 2 naming the file ({rc})")
        check({n: (r3 / n).read_bytes() for n in before3} == before3,
              f"{name}: nothing is written, not even the valid file scanned before it")
    r4 = new_root(tmp)
    write(r4, "tools/research_plan.json", json.dumps(plan(as_of="someday")))
    write(r4, "MOC.md", "<!-- generated:status-line:start -->\n<!-- generated:status-line:end -->\n")
    rc, _, err = capture(RP.main, ["--root", str(r4), "--check"])
    check(rc == 2 and "as_of" in err, f"an invalid plan exits 2 and names the problem ({rc})")
    bad = plan()
    bad["gates"][0]["id"] = ["A"]
    bad["gates"][0]["date"] = "2026-11-20"
    write(r4, "tools/research_plan.json", json.dumps(bad))
    rc, _, err = capture(RP.main, ["--root", str(r4), "--check"])
    check(rc == 2 and "invalid" in err,
          f"an unhashable gate id exits 2 ('could not run'), never 1 ('stale') ({rc})")

    section("documents: the reviewer's repro, an end marker in a fenced example")
    r17 = new_root(tmp)
    _doc_fixture(r17, plan())
    capture(RP.main, ["--root", str(r17), "--write"])
    eng = r17 / "docs/research/engineering.md"
    write(r17, "docs/research/engineering.md",
          "# Engineering\n\n<!-- generated:status-line:start -->\n\n## Generated blocks\n\n"
          "A document holds markers, and this tool fills them:\n\n```text\n"
          "<!-- generated:status-line:end -->\n```\n\n## Determinism tiers\n\nTier A.\n")
    before17 = _bytes(r17)
    for flag in ("--write", "--check"):
        rc, _, err = capture(RP.main, ["--root", str(r17), flag])
        check(rc == 2 and "never closed" in err and _bytes(r17) == before17,
              f"{flag}: exit 2 ('never closed'), nothing written ({rc}) {err.strip()[:90]}")
    check("## Generated blocks" in eng.read_text(encoding="utf-8"),
          "the hand-written section survives")
    write(r17, "docs/research/engineering.md",
          "# Engineering\n\n```text\n<!-- generated:status-line:start -->\n"
          "<!-- generated:status-line:end -->\n```\n\n<!-- generated:status-line:start -->\n"
          "<!-- generated:status-line:end -->\n")
    rc, _, err = capture(RP.main, ["--root", str(r17), "--write"])
    text = eng.read_text(encoding="utf-8")
    check(rc == 0 and text.count(EXPECTED_STATUS) == 1
          and ("```text\n<!-- generated:status-line:start -->\n"
               "<!-- generated:status-line:end -->\n```") in text,
          f"(a fenced example before a real block still works, and is left as it was) ({rc})")

    section("documents: a marker comment split over lines in a file that is not rendered")
    write(r17, "docs/other.md", "# Other\n\n<!--\ngenerated:status-line:start -->\n" + filler
          + "<!--\ngenerated:status-line:end -->\n")
    rc, _, err = capture(RP.main, ["--root", str(r17), "--check"])
    check(rc == 2 and "docs/other.md:3" in err, f"is a stray marker: exit 2, named ({rc}) {err}")
    write(r17, "docs/other.md", "# Other\n\n<!--\nTODO: generated later\n-->\n\n```\n<!--\n"
                                "generated:status-line:start -->\n```\n")
    rc, _, err = capture(RP.main, ["--root", str(r17), "--check"])
    check(rc == 0, f"a comment that does not begin with 'generated', and a split marker in a "
                   f"closed fence, are fine ({rc}) {err}")

    section("documents: a split marker comment inside a block quote, rendered or not")
    quoted = ("# Status\n\n> <!--\n>\n> generated:status-line:start -->\n"
              "> **Now:** P0 hand typed (2026-01-01 to 2026-02-02)\n"
              "> <!--\n>\n> generated:status-line:end -->\n")
    check(RP.marker_lines(quoted) == [3, 7],
          f"marker_lines names both quoted openings: {RP.marker_lines(quoted)}")
    try:
        RP.apply_blocks(quoted, RP.render_all(plan()), "docs/research/bq.md")
        check(False, "apply_blocks refuses the quoted split pair (it returned)")
    except RP.MarkerError as e:
        check("docs/research/bq.md:3" in str(e), f"apply_blocks refuses it at line 3: {e}")
    write(r17, "docs/other.md", quoted)
    before_q = _bytes(r17)
    for flag in ("--check", "--write"):
        rc, _, err = capture(RP.main, ["--root", str(r17), flag])
        check(rc == 2 and "docs/other.md:3" in err and _bytes(r17) == before_q,
              f"{flag}: a quoted split pair in a file that is not rendered is a stray marker: "
              f"exit 2, named, nothing written ({rc}) {err.strip()[:90]}")
    write(r17, "docs/other.md", "# Other\n\n> <!--\n>\n> TODO: generated later\n> -->\n\n"
                                "> ```\n> <!--\n> generated:status-line:start -->\n> ```\n")
    rc, _, err = capture(RP.main, ["--root", str(r17), "--check"])
    check(rc == 0, f"a quoted comment that does not begin with 'generated', and a quoted split "
                   f"marker in a closed fence, are fine ({rc}) {err}")

    section("documents: a plan that can never be written is invalid (exit 2), not stale")
    r18 = new_root(tmp)
    _doc_fixture(r18, plan())
    capture(RP.main, ["--root", str(r18), "--write"])
    bad18 = plan()
    bad18["gates"][0]["if_missed"] = "Reposition " + chr(0xD800) + " the contribution."
    write(r18, "tools/research_plan.json", json.dumps(bad18))
    before18 = _bytes(r18)
    for flag in ("--check", "--write"):
        rc, _, err = capture(RP.main, ["--root", str(r18), flag])
        check(rc == 2 and "lone surrogate" in err and _bytes(r18) == before18
              and not list(r18.rglob("*.render-tmp")),
              f"{flag}: exit 2, nothing written, no temporary file left ({rc})")
    a18 = write(r18, "w/a.md", "old a\n")
    b18 = write(r18, "w/b.md", "old b\n")
    try:
        RP._write_all(r18, [(a18, "old a\n", "new a\n"),
                            (b18, "old b\n", "new " + chr(0xD800) + "\n")])
        got = "returned"
    except core.PublishError:
        got = "PublishError"
    except Exception as e:  # noqa: BLE001
        got = type(e).__name__
    check(got == "PublishError" and not list(r18.rglob("*.render-tmp"))
          and a18.read_text(encoding="utf-8") == "old a\n",
          f"_write_all: a file that fails to stage (not an OSError) is PublishError, and the "
          f"files already staged are dropped ({got}, "
          f"{[p.name for p in r18.rglob('*.render-tmp')]})")

    section("documents: a label hidden by a reference or an invisible character exits 2")
    r19 = new_root(tmp)
    _doc_fixture(r19, plan())
    capture(RP.main, ["--root", str(r19), "--write"])
    bad19 = plan()
    bad19["gates"][0]["question"] = "Is it &#x50;ROVEN?"
    write(r19, "tools/research_plan.json", json.dumps(bad19))
    before19 = _bytes(r19)
    rc, _, err = capture(RP.main, ["--root", str(r19), "--write"])
    check(rc == 2 and "status label" in err and _bytes(r19) == before19,
          f"a character reference spelling a label: exit 2, nothing written ({rc})")
    for name, line in (
            ("a hex reference in a table", "| A | t | d | upcoming | Is it &#x50;ROVEN? |"),
            ("a zero-width space", "| A | t | d | upcoming | Is it P" + chr(0x200B) + "ROVEN? |"),
            ("a soft hyphen", "**Now:** P0 PRO" + chr(0xAD) + "VEN review"),
            ("a Mermaid code for an invisible", "    g0[\"Gate A: P#8203;ROVEN\"]")):
        check(raises(lambda ln=line: RP.check_rendered({"gates-table": ln}), core.PlanError),
              f"check_rendered refuses {name} with the plan check bypassed")
    RP.check_rendered({"gates-table": "| A | t | d | upcoming | P&amp;L &#x70;roven? |"})
    check(True, "a reference that spells no label passes check_rendered")

    section("documents: fences read with their containers (list items, block quotes)")
    # The reviewer's repro: a fence opened on a list-item line. Its closing line '  ```'
    # must not be taken for an opener that turns the rest of the file into "code".
    r13 = new_root(tmp)
    _doc_fixture(r13, plan())
    capture(RP.main, ["--root", str(r13), "--write"])
    glossary = r13 / "docs/research/glossary.md"
    hand = "**Now:** P9 typed by hand (1999-01-01 to 1999-02-01)"
    write(r13, "docs/research/glossary.md",
          "# Glossary\n\n- ```\n  example\n  ```\n\n<!-- generated:status-line:start -->\n"
          + hand + "\n<!-- generated:status-line:end -->\n\n```\nx\n```\n")
    rc, out, _ = capture(RP.main, ["--root", str(r13), "--check"])
    check(rc == 1 and "stale  docs/research/glossary.md" in out,
          f"a block after a fence opened on a list-item line is checked: stale ({rc})")
    rc, _, _ = capture(RP.main, ["--root", str(r13), "--write"])
    text = glossary.read_text(encoding="utf-8")
    check(rc == 0 and hand not in text and EXPECTED_STATUS in text
          and "- ```\n  example\n  ```\n" in text and text.endswith("```\nx\n```\n"),
          f"--write replaces the hand-typed line and leaves both fences as they were ({rc})")
    for name, body in (
            ("a fence in a block quote", "> ```\n> code\n> ```\n\n"),
            ("a fence in an ordered item", "1. ```\n   code\n   ```\n\n"),
            ("a fence nested in a list item", "- item\n\n    ```\n    code\n    ```\n\n"),
            ("a fence that ends with its block quote", "> ```\n> code\n\n")):
        write(r13, "docs/research/glossary.md", "# G\n\n" + body
              + "<!-- generated:status-line:start -->\n" + hand
              + "\n<!-- generated:status-line:end -->\n\n```\nx\n```\n")
        rc, out, _ = capture(RP.main, ["--root", str(r13), "--check"])
        check(rc == 1 and "glossary.md" in out, f"{name}: the block after it is checked ({rc})")
    write(r13, "docs/research/glossary.md",
          "# G\n\n- item\n\n    ```\n    <!-- generated:status-line:start -->\n"
          "    example only\n    <!-- generated:status-line:end -->\n    ```\n")
    before13 = glossary.read_bytes()
    rc, out, err = capture(RP.main, ["--root", str(r13), "--write"])
    check(rc == 0 and glossary.read_bytes() == before13,
          f"markers inside a closed fence nested in a list item are code, left alone ({rc}) {err}")

    section("documents: CommonMark fences — a one-line ```code span``` opens nothing")
    r6 = new_root(tmp)
    _doc_fixture(r6, plan())
    capture(RP.main, ["--root", str(r6), "--write"])
    write(r6, "MOC.md", "# x\n\n```inline``` code at the start of a line.\n\n"
                        "<!-- generated:status-line:start -->\n" + filler
                        + "<!-- generated:status-line:end -->\n")
    rc, out, _ = capture(RP.main, ["--root", str(r6), "--check"])
    check(rc == 1 and "stale  MOC.md" in out,
          f"a block after a line starting with ```code``` is still checked ({rc})")
    capture(RP.main, ["--root", str(r6), "--write"])
    check(filler.strip() not in (r6 / "MOC.md").read_text(encoding="utf-8"),
          "and --write replaces the hand-typed content")

    section("documents: --check fails when it has nothing to check")
    r7 = new_root(tmp)
    write(r7, "tools/research_plan.json", json.dumps(plan()))
    write(r7, "README.md", "# x\n\nNext gate: A, 2026-11-15 (typed by hand).\n")
    write(r7, "MOC.md", "# m\n")
    rc, out, _ = capture(RP.main, ["--root", str(r7), "--check"])
    check(rc == 1 and "no rendered file carries" in out,
          f"no markers anywhere: --check exits 1 ({rc})")
    rc, out, _ = capture(RP.main, ["--root", str(r7), "--check", "--allow-unplaced"])
    check(rc == 0 and "notice:" in out, f"--allow-unplaced turns it into a notice ({rc})")
    rc, out, _ = capture(RP.main, ["--root", str(r7), "--write"])
    check(rc == 0 and "notice:" in out, f"--write only notes it ({rc})")
    r8 = new_root(tmp)
    write(r8, "tools/research_plan.json", json.dumps(plan()))
    rc, out, _ = capture(RP.main, ["--root", str(r8), "--check"])
    check(rc == 1 and "README.md, MOC.md" in out,
          f"a root with no README.md, MOC.md or docs/research exits 1 ({rc})")
    r9 = new_root(tmp)
    _doc_fixture(r9, plan())
    (r9 / "docs/research/flow.md").unlink()
    capture(RP.main, ["--root", str(r9), "--write"])
    rc, out, _ = capture(RP.main, ["--root", str(r9), "--check"])
    check(rc == 1 and "commitments-table" in out and "gate-flow" in out,
          f"blocks fresh but three ids unplaced: --check exits 1 and names them ({rc})")

    section("documents: every Markdown file is either rendered or marker-free")
    r10 = new_root(tmp)
    _doc_fixture(r10, plan())
    capture(RP.main, ["--root", str(r10), "--write"])
    write(r10, "docs/other.md", "<!-- generated:status-line:start -->\n" + filler
          + "<!-- generated:status-line:end -->\n")
    rc, _, err = capture(RP.main, ["--root", str(r10), "--check"])
    check(rc == 2 and "docs/other.md:1" in err,
          f"a marker in a file render_plan does not render exits 2 and names it ({rc})")
    (r10 / "docs/other.md").write_text("```\n<!-- generated:status-line:start -->\n```\n"
                                       "Text with `<!-- generated:x:start -->` in code.\n",
                                       encoding="utf-8")
    rc, _, err = capture(RP.main, ["--root", str(r10), "--check"])
    check(rc == 0, f"marker syntax inside fenced code or a code span elsewhere is fine ({rc}) {err}")
    write(r10, "docs/research/sub/deep.md", "<!-- generated:status-line:start -->\n" + filler
          + "<!-- generated:status-line:end -->\n")
    rc, out, _ = capture(RP.main, ["--root", str(r10), "--check"])
    check(rc == 1 and "stale  docs/research/sub/deep.md" in out,
          f"docs/research/ is rendered recursively: a nested page is checked ({rc})")
    write(r10, "docs/publish.json", json.dumps({
        "site_base": "/psyche/", "repo": "o/r", "never_publish": ["docs/design/"],
        "sections": [{"title": "F", "pages": [{"src": "docs/PSYCHE.md", "slug": "substrate",
                                               "wiki": "Substrate"}]}]}))
    write(r10, "docs/PSYCHE.md", "<!-- generated:status-line:start -->\n" + filler
          + "<!-- generated:status-line:end -->\n")
    rc, out, _ = capture(RP.main, ["--root", str(r10), "--write"])
    check(rc == 0 and "wrote  docs/PSYCHE.md" in out and EXPECTED_STATUS in
          (r10 / "docs/PSYCHE.md").read_text(encoding="utf-8"),
          f"a manifest page is rendered ({rc})")
    write(r10, "docs/publish.json", json.dumps({"site_base": "nope"}))
    rc, _, err = capture(RP.main, ["--root", str(r10), "--check"])
    check(rc == 2 and "publish.json" in err,
          f"an invalid manifest stops the run: it decides part of the rendered set ({rc})")

    section("documents: --write never writes through a symlink")
    try:
        r11 = new_root(tmp)
        _doc_fixture(r11, plan())
        outside = tmp / f"outside{_N[0]}"
        write(outside, "private.md", "<!-- generated:status-line:start -->\nPRIVATE\n"
                                     "<!-- generated:status-line:end -->\n")
        os.symlink(os.path.relpath(outside / "private.md", r11 / "docs/research"),
                   r11 / "docs/research/link.md")
        priv_before = (outside / "private.md").read_bytes()
        rc, _, err = capture(RP.main, ["--root", str(r11), "--write"])
        check(rc == 2 and "link.md" in err, f"a symlinked page exits 2 ({rc})")
        check((outside / "private.md").read_bytes() == priv_before,
              "the file outside the repository is untouched")
        (r11 / "docs/research/link.md").unlink()
        inner = r11 / "docs/research/inner.md"
        os.symlink("roadmap.md", inner)
        rc, _, _ = capture(RP.main, ["--root", str(r11), "--write"])
        check(rc == 2, f"a symlink that stays inside the repository is refused too ({rc})")
        rc, _, err = capture(RP.main, ["--root", str(r11), "--check"])
        check(rc == 2 and "symbolic link" in err,
              f"and refused by --check, before any write is attempted ({rc})")
        inner.unlink()
        os.symlink(str(outside), r11 / "docs/research/dir")
        rc, _, _ = capture(RP.main, ["--root", str(r11), "--write"])
        check(rc == 2 and (outside / "private.md").read_bytes() == priv_before,
              f"a symlinked directory under docs/research is refused ({rc})")
        (r11 / "docs/research/dir").unlink()
        r12 = new_root(tmp)
        _doc_fixture(r12, plan())
        shutil.rmtree(r12 / "docs")
        outside2 = tmp / f"outside-docs{_N[0]}"
        write(outside2, "research/x.md", "<!-- generated:status-line:start -->\nPRIVATE\n"
                                       "<!-- generated:status-line:end -->\n")
        x_before = (outside2 / "research/x.md").read_bytes()
        os.symlink(str(outside2), r12 / "docs")
        rc, _, err = capture(RP.main, ["--root", str(r12), "--write"])
        check(rc == 2 and "outside" in err
              and (outside2 / "research/x.md").read_bytes() == x_before,
              f"a page that resolves outside the repository (docs/ is a link) is refused ({rc})")
    except (OSError, NotImplementedError):
        note("symlinks unavailable here; the symlink refusals were not exercised")

    section("documents: a status label in the rendered text exits 2 (defense in depth)")
    check(raises(lambda: RP.check_rendered(
        {"plan-gantt": "    Gate A BUILT UNVALIDATED review :milestone, gt0, 2026-11-15, 0d"}),
        core.PlanError), "a rendered milestone line with a label is refused")
    check(raises(lambda: RP.check_rendered({"plan-gantt": "    #66;UILT-UNVALIDATED x :ph0"}),
                 core.PlanError), "so is one that shows a label only once decoded")
    check(raises(lambda: RP.check_rendered({"status-line": "**Now:** NOT YET review"}),
                 core.PlanError), "so is a meaning verdict")
    RP.check_rendered(RP.render_all(plan()))
    check(True, "the fixture plan's rendering passes")
    labelled = plan()
    labelled["gates"][0].update(id="BUILT", title="UNVALIDATED review")
    labelled["phases"][0]["gate"] = "BUILT"
    r14 = new_root(tmp)
    _doc_fixture(r14, plan())
    capture(RP.main, ["--root", str(r14), "--write"])
    write(r14, "tools/research_plan.json", json.dumps(labelled))
    before14 = _bytes(r14)
    rc, _, err = capture(RP.main, ["--root", str(r14), "--write"])
    check(rc == 2 and "status label" in err and _bytes(r14) == before14,
          f"validate_plan refuses the id+title label: exit 2, nothing written ({rc})")
    real_problems = core.plan_problems
    try:
        core.plan_problems = lambda _p: []        # a validator that missed it
        rc_w, _, err_w = capture(RP.main, ["--root", str(r14), "--write"])
        rc_c, _, _ = capture(RP.main, ["--root", str(r14), "--check"])
    finally:
        core.plan_problems = real_problems
    check(rc_w == 2 and rc_c == 2 and "generated block" in err_w and _bytes(r14) == before14,
          f"with the plan check bypassed, the rendered-text check still refuses: exit 2, "
          f"nothing written ({rc_w}, {rc_c})")
    write(r14, "docs/probe.md", RP.render_plan_gantt(labelled) + "\n")
    c3 = [f for f in LC.check_status_vocabulary(r14, LC.load_ledger(r14))
          if f.path == "docs/probe.md"]
    check(any("0d" in f.message for f in c3),
          f"(not vacuous: the real C3 flags that rendered gantt: {[f.message for f in c3][:1]})")
    (r14 / "docs/probe.md").unlink()

    section("documents: every failure that is not a finding exits 2, never 1")
    r15 = new_root(tmp)
    _doc_fixture(r15, plan())
    capture(RP.main, ["--root", str(r15), "--write"])
    far = plan()
    far["deadlines"][0]["due"] = "9999-12-01"     # once: OverflowError, exit 1
    write(r15, "tools/research_plan.json", json.dumps(far))
    for flag in ("--check", "--write"):
        rc, _, err = capture(RP.main, ["--root", str(r15), flag])
        check(rc == 2 and "9000-12-31" in err, f"a due date of 9999-12-01: {flag} exits 2 ({rc})")
    write(r15, "tools/research_plan.json", json.dumps(plan()))
    real_render = RP.render_documents
    try:
        def broken(*a, **kw):
            raise ValueError("a bug in rendering")
        RP.render_documents = broken
        rc, _, err = capture(RP.main, ["--root", str(r15), "--check"])
    finally:
        RP.render_documents = real_render
    check(rc == 2 and "could not run" in err, f"an unexpected exception exits 2 ({rc}) {err}")

    section("documents: --write is all or nothing")
    r16 = new_root(tmp)
    _doc_fixture(r16, plan())
    roadmap = r16 / "docs/research/roadmap.md"
    before16 = _bytes(r16)
    os.chmod(roadmap, 0o444)
    try:
        rc, _, err = capture(RP.main, ["--root", str(r16), "--write"])
    finally:
        os.chmod(roadmap, 0o644)
    check(rc == 2 and "not writable" in err and _bytes(r16) == before16,
          f"a read-only target: exit 2 and no file written, not even README.md and MOC.md "
          f"which render first ({rc}) {err}")
    real_replace = os.replace
    calls = []

    def flaky(a, b):
        calls.append(b)
        if len(calls) == 3:
            raise OSError("disk full (simulated)")
        return real_replace(a, b)
    try:
        os.replace = flaky
        rc, _, err = capture(RP.main, ["--root", str(r16), "--write"])
    finally:
        os.replace = real_replace
    leftovers = [p.name for p in r16.rglob("*.render-tmp")]
    check(rc == 2 and _bytes(r16) == before16 and not leftovers,
          f"a rename that fails midway puts back the files already moved and leaves no "
          f"temporary file ({rc}, {leftovers})")
    os.chmod(r16 / "MOC.md", 0o640)
    rc, _, _ = capture(RP.main, ["--root", str(r16), "--write"])
    check(rc == 0 and (os.stat(r16 / "MOC.md").st_mode & 0o777) == 0o640
          and not list(r16.rglob("*.render-tmp")),
          f"a successful --write keeps each file's mode and leaves no temporary file ({rc})")

    section("documents: --status")
    rc, out, _ = capture(RP.main, ["--root", str(root), "--status"])
    check(rc == 0 and "next gate" in out and "Program state" in out,
          f"--status exits 0 with program state and the next gate ({rc})")

    section("documents: --past-due exits 0 whatever it finds, and 2 only when it cannot run")
    r17 = new_root(tmp)
    _doc_fixture(r17, plan(as_of="2020-01-01", gates=[
        dict(FIXTURE_PLAN["gates"][0], date="2020-02-01", baseline_date="2020-02-01"),
        *FIXTURE_PLAN["gates"][1:]],
        phases=[dict(FIXTURE_PLAN["phases"][0], start="2020-01-01", end="2020-02-01"),
                *FIXTURE_PLAN["phases"][1:]]))
    rc, out, _ = capture(RP.main, ["--root", str(r17), "--past-due", "--annotations"])
    check(rc == 0 and out.startswith("::warning title=Gate decision pending::Gate A (Novelty)"),
          f"a gate long past its date: exit 0 and a warning annotation ({rc}) {out[:80]}")
    rc, out, _ = capture(RP.main, ["--root", str(r17), "--past-due"])
    check(rc == 0 and out.startswith("warning: Gate A") and "::" not in out,
          f"without --annotations the same finding is plain text ({rc})")
    r18 = new_root(tmp)
    _doc_fixture(r18, plan(as_of="2999-01-01"))
    rc, out, _ = capture(RP.main, ["--root", str(r18), "--past-due", "--annotations"])
    check(rc == 0 and "::" not in out and "no gate is past its date" in out,
          f"nothing late: exit 0 and no annotation ({rc}) {out[:80]}")
    write(r18, "tools/research_plan.json", json.dumps(dict(plan(), schema_version=9)))
    rc, _, err = capture(RP.main, ["--root", str(r18), "--past-due"])
    check(rc == 2 and "schema_version" in err, f"an invalid plan exits 2, as every mode does ({rc})")
    try:
        capture(RP.main, ["--root", str(r18), "--check", "--annotations"])
        code = 0
    except SystemExit as e:
        code = e.code
    check(code == 2, f"--annotations without --past-due is a usage error ({code})")
    try:
        capture(RP.main, ["--root", str(r18), "--check", "--past-due"])
        code = 0
    except SystemExit as e:
        code = e.code
    check(code == 2, f"--past-due is its own mode, not combined with --check ({code})")


# ─────────────────────────────────────────────────────────────────────────────
# Markdown structure (shared by render_plan and rewrite_links)
# ─────────────────────────────────────────────────────────────────────────────

# (document, kinds in 'cmark' mode, kinds in 'micromark' mode); F fenced, I indented
# code, H HTML block, . anything else. Each micromark row was checked against micromark
# 4.0.2 with the GFM extensions (mdast-util-from-markdown), the parser the site uses.
SCAN_CASES = [
    ("- ```\n  a\n  ```\nb\n", "FFF.", "FFF."),
    ("> ```\n> a\n> ```\n", "FFF", "FFF"),
    ("> ```\n> a\n\nb\n", "FF..", "FF.."),
    ("1. ```\n   a\n   ```\n", "FFF", "FFF"),
    ("- item\n\n    ```\n    a\n    ```\n", "..FFF", "..FFF"),
    ("    x\n2. ~~~\n", "IF", "I."),          # micromark: no '2.' item after code
    ("    x\n\n2. ~~~\n", "IIF", "II."),   # (a blank line inside code is code)
    ("> a\n<x-y>\n> b\n", "...", ".HH"),       # micromark: a lazy lone tag is HTML
    ("> foo\n    - bar\n", "..", ".."),          # lazy, not indented code
    ("[x]: y\n===\n    z\n", "...", "..."),     # no setext over definitions only
    ("[^1]: note\n\n    see\n", "...", "..."),   # a footnote's paragraph
    ("```\na\n", "FF", "FF"),
    ("<div>\n```\n</div>\n\n<!-- c -->\n", "HHH.H", "HHH.H"),
]


def test_markdown() -> None:
    section("markdown: lines end at \\n, \\r and \\r\\n only")
    check(core.split_lines("a\u2028b\r\nc\rd\x0ce\n") == ["a\u2028b", "c", "d\x0ce"],
          "U+2028 and form feed do not end a line; CR, LF and CRLF do")
    check(core.split_lines("a\r\n", keepends=True) == ["a\r\n"], "keepends keeps CRLF whole")
    check(core.split_lines("") == [] and core.split_lines("\n") == [""],
          "no empty line after a final line ending")

    section("markdown: block structure in each parser's reading")
    for doc, want_cm, want_mm in SCAN_CASES:
        for mode, want in (("cmark", want_cm), ("micromark", want_mm)):
            info, _ = core.scan_blocks(core.split_lines(doc), mode)
            got = "".join({"fence": "F", "icode": "I", "html": "H"}.get(li.kind, ".")
                          for li in info)
            check(got == want, f"{mode}: {doc!r} reads {want}, got {got}")
    fences = core.code_fences(core.split_lines("- ```\n  a\n  ```\nb\n"))
    check(fences == [core.FENCE_CLOSED] * 3 + [None], f"a closed fence in a list item {fences}")
    fences = core.code_fences(core.split_lines("> ```\n> a\n\nb\n"))
    check(fences == [core.FENCE_UNCLOSED] * 2 + [None, None],
          f"a fence ended by its block quote is not closed {fences}")
    fences = core.code_fences(core.split_lines("    x\n2. ~~~\nq\n"))
    check(fences[1] == core.FENCE_DISPUTED,
          f"a line one parser reads as a fence and another as text is disputed {fences}")

    section("markdown: code spans, escapes and comments on one line")
    for line, masked in (
            ("a `b` c", "a ### c"),
            ("a \\`b` c", "a \\`b` c"),             # an escaped backtick opens nothing
            ("a \\``b` c", "a \\`### c"),           # ... the run after it does
            ("`a \\` b`", "##### b`"),               # inside a span nothing is escaped
            ("<span title=\"`\">x `y`", "<span title=\"`\">x ###"),   # a tag is atomic
            ("<!-- c --> `x`", "########## ###"),
            ("<!-- a -- b `x --> `y`", "<!-- a -- b `x --> `y`"),      # parsers disagree
            ("| `a | b` |", "| `a | b` |"),              # a table cell ends a span
    ):
        got = core.mask_inline(line).replace("\0", "#")
        check(got == masked, f"mask_inline({line!r}) == {masked!r}, got {got!r}")
    check(core.mask_inline("<!-- c --> `x`", comments=False).replace("\0", "#")
          == "<!-- c --> ###", "comments=False keeps comments (render_plan's markers)")


# ─────────────────────────────────────────────────────────────────────────────
# ci_c2
# ─────────────────────────────────────────────────────────────────────────────

def _fake_lc(fn):
    return types.SimpleNamespace(
        LEDGER_REL=LC.LEDGER_REL, load_ledger=LC.load_ledger, check_prose_vs_ledger=fn,
        CaptureMalformed=LC.CaptureMalformed, CensusUnreadable=LC.CensusUnreadable)


C2_LEDGER = {
    "tests": {"suites": 2, "assertions": 30, "failures": 0,
              "per_suite": {"test_a.py": 10, "test_b.py": 20}},
    "bricks": {}, "valid_statuses": ["PROVEN"], "forbidden_claim_terms": [],
    "claim_quarantine_paths": [], "count_quarantine_paths": [],
}


def test_ci_c2(tmp: Path) -> None:
    section("ci_c2: only C2 findings in docs/paper/**.tex are tolerated")
    F = LC.Finding
    held = [F("C2", "docs/paper/main.tex", 3, "says 20 suites"),
            F("C2", "docs/paper/ieee/sub.tex", 9, "says 618 assertions")]
    not_held = [F("C2", "docs/paper/notes.md", 1, "md in the paper dir"),
                F("C2", "docs/paperwork/a.tex", 1, "a different directory"),
                F("C2", "xdocs/paper/a.tex", 1, "not anchored"),
                F("C2", "docs/paper/a.tex.md", 1, "wrong suffix"),
                F("C2", "README.md", 4, "a public document"),
                F("C4", "docs/paper/main.tex", 2, "another check entirely")]
    h, o = ci_c2.partition(held + not_held)
    check(h == held, "both held-paper .tex findings are tolerated")
    check(o == not_held, "every other finding is reported, including C4 in the paper")

    root = new_root(tmp)
    write(root, "tools/ledger.json", json.dumps(C2_LEDGER))
    rc, out, _ = capture(ci_c2.run, root, _fake_lc(lambda r, l: list(held)))
    check(rc == 0, f"held only -> exit 0 ({rc})")
    lines = out.splitlines()
    check("C2: 2 finding(s) tolerated under D-012 (held paper)" in lines,
          "the tolerance line is printed exactly")
    check("  tolerated  docs/paper/main.tex:3" in lines
          and "  tolerated  docs/paper/ieee/sub.tex:9" in lines,
          "each tolerated finding is listed by path and line, so the excuse is visible")
    rc, out, _ = capture(ci_c2.run, root, _fake_lc(lambda r, l: held + not_held[4:5]))
    check(rc == 1 and "[C2] README.md:4" in out and "[C2] docs/paper/main.tex:3" not in out,
          f"held + other -> exit 1, the other is reported, the held one only listed ({rc})")
    rc, out, _ = capture(ci_c2.run, root, _fake_lc(lambda r, l: []))
    check(rc == 0 and "C2: 0 finding(s) tolerated" in out and "retired" in out,
          "no findings -> exit 0 with a notice that the exception can be retired")

    def raiser(exc):
        def fn(r, l):
            raise exc("fixture")
        return fn
    for exc in (LC.CaptureMalformed, LC.CensusUnreadable, KeyError, TypeError):
        rc, _, err = capture(ci_c2.run, root, _fake_lc(raiser(exc)))
        check(rc == 2, f"{exc.__name__} from C2 maps to exit 2, never 1 ({rc})")
    empty = new_root(tmp)
    rc, _, _ = capture(ci_c2.run, empty, _fake_lc(lambda r, l: []))
    check(rc == 2, f"a missing ledger is exit 2 ({rc})")

    section("ci_c2: every ledger shape C2 cannot read is exit 2 (the real C2)")
    shapes = {
        "not JSON": ("text", "{ not json"),
        "not UTF-8": ("bytes", b"\xff\xfe{}"),
        "a JSON array": ("text", "[]"),
        "a JSON string": ("text", '"ledger"'),
        "a directory": ("dir", None),
        "tests: null": ("text", json.dumps(dict(C2_LEDGER, tests=None))),
        "tests.per_suite: a list": ("text", json.dumps(dict(C2_LEDGER, tests=dict(
            C2_LEDGER["tests"], per_suite=[10, 20])))),
        "tests.per_suite: an unhashable value": ("text", json.dumps(dict(C2_LEDGER, tests=dict(
            C2_LEDGER["tests"], per_suite={"a": [1]})))),
        "count_quarantine_paths: null": ("text", json.dumps(dict(C2_LEDGER,
                                                                 count_quarantine_paths=None))),
        "count_quarantine_paths: [5]": ("text", json.dumps(dict(C2_LEDGER,
                                                                count_quarantine_paths=[5]))),
        # C2 skips a comparison whose total is missing: a run that checked nothing
        # must not read as clean (reviewer's repro: both totals removed, exit 0)
        "tests: {}": ("text", json.dumps(dict(C2_LEDGER, tests={}))),
        "tests without totals": ("text", json.dumps(dict(C2_LEDGER, tests={
            "per_suite": C2_LEDGER["tests"]["per_suite"]}))),
        "tests.assertions: null": ("text", json.dumps(dict(C2_LEDGER, tests=dict(
            C2_LEDGER["tests"], assertions=None)))),
        "tests.suites: null": ("text", json.dumps(dict(C2_LEDGER, tests=dict(
            C2_LEDGER["tests"], suites=None)))),
        "tests.suites: a string": ("text", json.dumps(dict(C2_LEDGER, tests=dict(
            C2_LEDGER["tests"], suites="2")))),
        "tests.assertions: true": ("text", json.dumps(dict(C2_LEDGER, tests=dict(
            C2_LEDGER["tests"], assertions=True)))),
        "tests.assertions: 30.0": ("text", json.dumps(dict(C2_LEDGER, tests=dict(
            C2_LEDGER["tests"], assertions=30.0)))),
        "no tests key": ("text", json.dumps({k: v for k, v in C2_LEDGER.items()
                                             if k != "tests"})),
    }
    for name, (kind, body) in shapes.items():
        r = new_root(tmp)
        write(r, "README.md", "The run has 30 assertions.\n")
        if kind == "dir":
            (r / "tools/ledger.json").mkdir(parents=True)
        else:
            write(r, "tools/ledger.json", body, binary=(kind == "bytes"))
        rc, _, err = capture(ci_c2.run, r, LC)
        check(rc == 2 and "ci_c2:" in err, f"ledger {name}: exit 2 ({rc})")
        if kind == "text" and name not in ("not JSON",):
            check("C2 cannot read it" in err,
                  f"ledger {name}: the shape is named before C2 runs, not caught as a crash")
    r = new_root(tmp)
    write(r, "tools/ledger.json", b"\xff\xfe{}", binary=True)
    proc = subprocess.run([sys.executable, "-B", str(HERE / "ci_c2.py"), "--root", str(r)],
                          capture_output=True, text=True)
    check(proc.returncode == 2 and "Traceback" not in proc.stderr,
          f"as a process too: exit 2 and no traceback ({proc.returncode})")
    r = new_root(tmp)
    write(r, "tools/ledger.json", json.dumps(dict(C2_LEDGER, tests={})))
    write(r, "README.md", "The run has 9999 assertions across 77 suites.\n")
    proc = subprocess.run([sys.executable, "-B", str(HERE / "ci_c2.py"), "--root", str(r)],
                          capture_output=True, text=True)
    check(proc.returncode == 2 and "clean" not in proc.stdout,
          f"the reviewer's repro (no totals, a wrong count in prose): exit 2, never "
          f"'clean' ({proc.returncode})")

    section("ci_c2: end to end through the real ledger_check C2")
    e2e = new_root(tmp)
    write(e2e, "tools/ledger.json", json.dumps(C2_LEDGER))
    write(e2e, "docs/paper/p.tex", "The run had 618 assertions.\n")
    write(e2e, "README.md", "The run has 30 assertions.\n")
    script = str(HERE / "ci_c2.py")

    def run_e2e():
        return subprocess.run([sys.executable, "-B", script, "--root", str(e2e)],
                              capture_output=True, text=True)
    r = run_e2e()
    check(r.returncode == 0 and "C2: 1 finding(s) tolerated" in r.stdout
          and "  tolerated  docs/paper/p.tex:1" in r.stdout,
          f"a stale count in the held paper alone -> exit 0, listed ({r.returncode}) {r.stderr}")
    write(e2e, "docs/paper/notes.md", "The run had 618 assertions.\n")
    r = run_e2e()
    check(r.returncode == 1 and "docs/paper/notes.md" in r.stdout,
          f"Markdown inside docs/paper/ is NOT tolerated ({r.returncode})")
    (e2e / "docs/paper/notes.md").unlink()
    write(e2e, "docs/note.md", "The run had 618 assertions.\n")
    r = run_e2e()
    check(r.returncode == 1 and "docs/note.md" in r.stdout,
          f"a stale count anywhere else -> exit 1 ({r.returncode})")


# ─────────────────────────────────────────────────────────────────────────────
# link rewriting
# ─────────────────────────────────────────────────────────────────────────────

def test_links(tmp: Path) -> None:
    section("links: rewriting")
    if not GIT:
        check(False, "git is required for the link tests and was not found")
        return
    root = new_root(tmp)
    tracked = {"docs/research/README.md": "# t\n", "docs/research/roadmap.md": "# r\n",
               "docs/ARCHITECTURE.md": "# a\n", "src/mod.py": "x = 1\n",
               "docs/assets/pic.svg": "<svg/>\n", "docs/My File.md": "# m\n"}
    for rel, body in tracked.items():
        write(root, rel, body)
    write(root, "docs/draft.md", "# untracked\n")
    sha = git_repo(root, list(tracked))
    # staged after the commit: in the index, not in the commit the links are pinned to
    write(root, "docs/staged.md", "# staged only\n")
    git_ok(root, "add", "--", "docs/staged.md")
    gh = f"https://github.com/o/r/blob/{sha}"
    raw = f"https://github.com/o/r/raw/{sha}"
    tree = f"https://github.com/o/r/tree/{sha}"
    mapping = {"docs/research/roadmap.md": "/psyche/research/roadmap/",
               "docs/ARCHITECTURE.md": "/psyche/substrate/architecture/",
               "docs/research/README.md": "/psyche/research/"}
    src = "docs/research/README.md"
    RM = "/psyche/research/roadmap/"

    def rw(md, m=mapping, **kw):
        return core.rewrite_links(md, src, m, sha, "o/r", root=root, **kw)

    cases = [
        ("[roadmap](roadmap.md)", f"[roadmap]({RM})"),
        ("[gate a](roadmap.md#gate-a)", f"[gate a]({RM}#gate-a)"),
        ('[arch](../ARCHITECTURE.md "Architecture")',
         '[arch](/psyche/substrate/architecture/ "Architecture")'),
        ("[self](README.md)", "[self](/psyche/research/)"),
        ("[code](../../src/mod.py)", f"[code]({gh}/src/mod.py)"),
        ("[code line](../../src/mod.py#L1)", f"[code line]({gh}/src/mod.py#L1)"),
        ("[src dir](../../src/)", f"[src dir]({tree}/src)"),
        ("[repo](../../)", f"[repo]({tree})"),
        ("![pic](../assets/pic.svg)", f"![pic]({raw}/docs/assets/pic.svg)"),
        ("[spaced](../My%20File.md)", f"[spaced]({gh}/docs/My%20File.md)"),
        ("[angle](<roadmap.md>)", f"[angle](<{RM}>)"),
        ("[the\nroadmap](roadmap.md)", f"[the\nroadmap]({RM})"),
        ("[![pic](../assets/pic.svg)](roadmap.md)",
         f"[![pic]({raw}/docs/assets/pic.svg)]({RM})"),
        ("[`code` text](roadmap.md)", f"[`code` text]({RM})"),
        ("[rm]: roadmap.md", f"[rm]: {RM}"),
        ('<a href="roadmap.md">r</a>', f'<a href="{RM}">r</a>'),
        ('<img src="../assets/pic.svg">', f'<img src="{raw}/docs/assets/pic.svg">'),
        # shapes the first round missed
        ("[a [b [c]] d](roadmap.md)", f"[a [b [c]] d]({RM})"),
        ("[x](roadmap.md#a(b(c)))", f"[x]({RM}#a(b(c)))"),
        ("[x](\nroadmap.md)", f"[x](\n{RM})"),
        ("[x](roadmap.md\n)", f"[x]({RM}\n)"),
        ("> [rm]: roadmap.md", f"> [rm]: {RM}"),
        ("- [rm]: roadmap.md", f"- [rm]: {RM}"),
        ("1. > [rm]: roadmap.md", f"1. > [rm]: {RM}"),
        ("[rm]:\n  roadmap.md", f"[rm]:\n  {RM}"),
        ('[rm]: roadmap.md "Title"', f'[rm]: {RM} "Title"'),
        ("<a href=roadmap.md>x</a>", f"<a href={RM}>x</a>"),
        ("<a href='roadmap.md'>x</a>", f"<a href='{RM}'>x</a>"),
        ('<a href = "roadmap.md">x</a>', f'<a href = "{RM}">x</a>'),
        ('<img srcset="../assets/pic.svg 1x, ../assets/pic.svg 2x">',
         f'<img srcset="{raw}/docs/assets/pic.svg 1x, {raw}/docs/assets/pic.svg 2x">'),
        ('<video poster="../assets/pic.svg">', f'<video poster="{raw}/docs/assets/pic.svg">'),
        ("![pic][p]\n\n[p]: ../assets/pic.svg", f"![pic][p]\n\n[p]: {raw}/docs/assets/pic.svg"),
        ("![p]\n\n[p]: ../assets/pic.svg", f"![p]\n\n[p]: {raw}/docs/assets/pic.svg"),
        ("![P][]\n\n[p]: ../assets/pic.svg", f"![P][]\n\n[p]: {raw}/docs/assets/pic.svg"),
        ("![x][code]\n\n[code]: ../../src/mod.py", f"![x][code]\n\n[code]: {raw}/src/mod.py"),
        ("[c]: ../../src/mod.py", f"[c]: {gh}/src/mod.py"),
        ("```inline``` code at the start of a line.\n\n[x](roadmap.md)\n",
         f"```inline``` code at the start of a line.\n\n[x]({RM})\n"),
        # fences read with their containers: the closing '  ```' of a fence opened on a
        # list-item line opens nothing (reviewer's repro B, with only a live link)
        ("- ```\n  pip install x\n  ```\n\nSee [the roadmap](roadmap.md).\n",
         f"- ```\n  pip install x\n  ```\n\nSee [the roadmap]({RM}).\n"),
        ("> ```\n> [x](nowhere.md)\n> ```\n\n[r](roadmap.md)\n",
         f"> ```\n> [x](nowhere.md)\n> ```\n\n[r]({RM})\n"),
        ("1. ```\n   [x](nowhere.md)\n   ```\n\n[r](roadmap.md)\n",
         f"1. ```\n   [x](nowhere.md)\n   ```\n\n[r]({RM})\n"),
        # a GFM footnote's indented paragraph is text, not indented code
        ("[^1]: note\n\n    see [the roadmap](roadmap.md)\n",
         f"[^1]: note\n\n    see [the roadmap]({RM})\n"),
        # attributes are attributes only inside a tag
        ('<a\n  href="roadmap.md">r</a>', f'<a\n  href="{RM}">r</a>'),
        ('<img alt="x" src=../assets/pic.svg />', f'<img alt="x" src={raw}/docs/assets/pic.svg />'),
        ("See https://example.com/embed?src=abc and [r](roadmap.md).",
         f"See https://example.com/embed?src=abc and [r]({RM})."),
        # labels read with CommonMark's grammar: an escaped ']', a label over two lines,
        # and a destination on the next line of a block quote
        ("[a\\]b]: roadmap.md\n\nsee [a\\]b]", f"[a\\]b]: {RM}\n\nsee [a\\]b]"),
        ("[a\nb]: roadmap.md\n\nsee [a b]", f"[a\nb]: {RM}\n\nsee [a b]"),
        ("> [a\n> b]: roadmap.md", f"> [a\n> b]: {RM}"),
        ("> [rm]:\n> roadmap.md", f"> [rm]:\n> {RM}"),
        # every line ending CommonMark knows ends a definition
        ("[rm]: roadmap.md\r\n[c]: ../../src/mod.py\r\n",
         f"[rm]: {RM}\r\n[c]: {gh}/src/mod.py\r\n"),
        ("[rm]: roadmap.md\r[c]: ../../src/mod.py\r", f"[rm]: {RM}\r[c]: {gh}/src/mod.py\r"),
        ("[x](HTTPS://example.org/a)", "[x](HTTPS://example.org/a)"),
    ]
    for given, want in cases:
        try:
            got = rw(given)
        except core.PublishError as e:
            got = f"!{e}"
        check(got == want, f"{given!r} -> {want!r}, got {got!r}")

    untouched = [
        "[ext](https://example.org/a_(b))", "[plain](http://example.org)",
        "[mail](mailto:someone@example.org)", "[anchor](#section)",
        "`[x](nowhere.md)` in a code span", "```\n[x](nowhere.md)\n```",
        "~~~~md\n[x](nowhere.md)\n~~~~", "[^1]: A footnote, not a link.",
        "a [bracket] alone", "<https://example.org/auto>",
        "[Gate A]: novelty review comes first (prose, not a definition)",
        "[deep](https://example.org/a(b(c(d(e(f))))))", "[self link]()",
        "````\n```inline``` inside a real fence\n[x](nowhere.md)\n````",
        "[x](\n\nnowhere.md) is not a link: a blank line ends it",
        # refused before although valid (reviewer's finding): none of these is a link
        "See https://example.com/embed?src=abc for details.",
        "<https://example.org/r?href=home>",
        "src = the input path, href = the link target",
        "<!-- TODO: [old](gone.md) -->",
        "Inline <!-- [old](gone.md) --> comment.",
        "<!--\n[old](gone.md)\n<a href=\"gone.md\">\n-->",
        "    [not a link](missing.md)",
        "Text.\n\n    [not a link](missing.md)\n",
        "- item\n\n      [not a link](missing.md)\n",
        "`[x](nowhere.md) \\` is one code span: a backslash escapes nothing inside one",
        # no label: a blank line inside, whitespace alone, or a GFM footnote
        "[a\n\nb]: nowhere.md", "> [a\n>\n> b]: nowhere.md", "[ ]: nowhere.md",
        "[^note]: nowhere.md is the footnote's text",
    ]
    for given in untouched:
        try:
            got = rw(given)
        except core.PublishError as e:
            got = f"!{e}"
        check(got == given, f"left alone: {given!r}, got {got!r}")

    wiki = {k: v for k, v in (("docs/research/roadmap.md", "Research-Roadmap"),)}
    check(rw("[g](roadmap.md#gate-a)", wiki) == "[g](Research-Roadmap#gate-a)",
          "wiki targets keep their fragment")
    doc = "# T\n\nSee [roadmap](roadmap.md) and [code](../../src/mod.py).\n"
    check(rw(doc) == rw(doc), "rewriting is deterministic")

    section("links: every dead or unparseable shape raises")
    dead = ["[x](nowhere.md)", "[x](../draft.md)", "[x](../../../outside.md)",
            "[x](/docs/research/roadmap.md)", "[x](javascript:alert(1))", "[x](//evil.example/x)",
            "[x](ftp://host/x)", "![x](../assets/missing.svg)", "[rm]: nowhere.md",
            '<a href="nowhere.md">x</a>', "[x](?query-only)", "[x](../../src/nope/)",
            # shapes the first round published unchecked
            "[a [b [c]] d](nowhere.md)", "[x](a(b(c)).md)", "[x](\nnowhere.md)",
            "> [rm]: nowhere.md", "- [rm]: nowhere.md", "[rm]:\nnowhere.md",
            "<a href=nowhere.md>x</a>", "<a href='nowhere.md'>x</a>",
            '<img srcset="nowhere.png 2x">', '<img srcset="../assets/pic.svg 1x, nowhere.png 2x">',
            "```inline``` text\n\n[x](nowhere.md)\n",
            # deeper than the patterns parse: refused by the leftover scan
            "[x](a(b(c(d(e(f)))))).md)", "[a [b [c [d [e [f]]]]]](nowhere.md)",
            '<a href=\n"nowhere.md">x</a>',
            # in the index but not in the pinned commit
            "[s](../staged.md)",
            # reviewer's repro B: before, the closing '  ```' opened a "fence" that hid
            # the rest of the file, and the dead link was published unchecked
            "- ```\n  pip install x\n  ```\n\nSee [the roadmap](roadmap.md) and "
            "[a dead one](nope.md).\n",
            "- ```\n  x\n  ```\n\n[a dead one](nope.md)\n\n```\ny\n```\n",
            "> ```\n> code\n\n[x](nope.md)\n",              # the fence ends with its quote
            "- ```\n  code\nnot indented\n[x](nope.md)\n",  # ... and with its list item
            # reviewer's finding: an escaped backtick opens no code span
            "Use \\`[real link](missing.md)\\` here.",
            "\\``[x](nope.md)` is code but this is not: [y](nope.md)",
            # a quoted attribute value never runs past its leaf block
            '- <a title="x\n> [t](nope.md)">',
            '<a title="x\n\n[r]: nope.md\n">',
            # parsers disagree, so the text is checked: a GFM table splits cells first
            "| `a | b` x `[dead](nope.md)` |\n| - | - |\n",
            # conservative: a line with pipes over '---' could be a table row, so its
            # code span is not trusted (no parser renders this link; it is still checked)
            "`x | [dead](nope.md) |`\n---\n",
            # a span closes at the first backtick run of its length, escaped or not: so
            # '`a \\`' is a span, and the link after the next one is live
            "`a \\` b` and `[x](nowhere.md)`",
            # ... a comment with '--' inside is one for the site, not for GitHub
            "Text <!-- a -- b `x --> [dead](nope.md) `y`",
            # ... the site's parser does not start a list after indented code
            "    x\n-\n  ~~~\nc\n  ~~~\n[dead](nope.md)\n",
            # a line Markdown reads as one line is one line: U+2028 does not end it
            "text" + chr(0x2028) + "```\n[dead](nope.md)\n",
            # reference definitions the earlier label pattern ([^\]\n]+) passed unread
            # (markdown-it and the CommonMark spec make each a link)
            "[a\\]b]: nowhere.md\n\nsee [a\\]b]", "[a\nb]: nowhere.md\n\nsee [a b]",
            "[\nfoo\n]: nowhere.md\n\n[foo]", "> [a]:\n> nowhere.md\n\n[a]",
            "- [a\n  b]: nowhere.md\n",
            # ... and what no pattern reads is refused by the leftover scan
            "[^a b]: nowhere.md", "[a]b]: nowhere.md",
            # a definition ending in CRLF inside a paragraph, and a CR-only file
            "[a]: nowhere.md\r\n[b]: roadmap.md\r\n\r\n[a] [b]",
            "[a]: nowhere.md\r[b]: roadmap.md\r\r[a] [b]",
            # http(s) without '//' is a path relative to the page (WHATWG URL)
            "[x](https:nowhere.md)", "[x](http:nowhere.md)", "[x](HTTPS:nowhere.md)",
            '<a href="https:nowhere.md">x</a>', "[x]: https:nowhere.md",
            "[x](https:/nowhere.md)"]
    for given in dead:
        check(raises(lambda g=given: rw(g)), f"dead or unparseable link {given!r} raises")
    try:
        rw("[x](nowhere.md)")
    except core.PublishError as e:
        check("dead relative link" in str(e) and src in str(e),
              "the error names the source and says 'dead relative link'")
    check(raises(lambda: rw("[code](../../src/mod.py)", tracked=set())),
          "a file the commit does not hold is dead even when it exists on disk")
    for bad_sha in ("HEAD", "xyz"):
        check(raises(lambda b=bad_sha: core.rewrite_links("[a](roadmap.md)", src, mapping, b,
                                                          "o/r", root=root)),
              f"sha {bad_sha!r} is refused")
    check(raises(lambda: core.rewrite_links("[c](../../src/mod.py)", src, mapping, "f" * 40,
                                            "o/r", root=root)),
          "a sha the repository does not have is refused (nothing can be proved about it)")
    check(raises(lambda: core.rewrite_links("x", src, mapping, sha, "not a repo", root=root)),
          "a malformed repo is refused")


# ─────────────────────────────────────────────────────────────────────────────
# the ledger projection
# ─────────────────────────────────────────────────────────────────────────────

def test_ledger_public(tmp: Path) -> None:
    section("ledger_public: shape and fidelity")
    pub = core.ledger_public(REPO)
    led = core.load_ledger(REPO)
    check(set(pub) == {"tests", "determinism", "bricks", "meaning_bar", "program", "aim"},
          "exactly the agreed top-level keys")
    check(set(pub["tests"]) == set(core.PUBLIC_TEST_FIELDS), "exactly the agreed test fields")
    check(all(pub["tests"][k] == led["tests"][k] for k in core.PUBLIC_TEST_FIELDS),
          "test figures are copied, never computed")
    check(pub["determinism"] == {"interpreters": led["determinism"]["interpreters_swept"],
                                 "hash_seeds": led["determinism"]["hash_seeds"]},
          "determinism reports what was swept")
    check([b["id"] for b in pub["bricks"]] == list(led["bricks"]),
          "bricks keep the ledger's order")
    check(all(set(b) == {"id", "name", "status"} for b in pub["bricks"]),
          "a brick projects id, name and status only (no notes)")
    check(all(set(v) == set(core.PUBLIC_PROGRAM_FIELDS) for v in pub["program"].values()),
          "program projects state, since and decision only")
    check(list(pub["program"]) == ["substrate", "cognitive_map"],
          "program projects the substrate, then the cognitive-map line, and nothing else")
    check(all(pub["program"][w][f] == led["program"][w][f] for w in pub["program"]
              for f in core.PUBLIC_PROGRAM_FIELDS),
          "program state is copied, never computed")
    check(pub["aim"] == led["program"]["aim"] and isinstance(pub["aim"], str)
          and pub["aim"].strip() != "",
          "the aim is the ledger's program.aim, copied as a non-empty string")
    check("aim_rule" not in json.dumps(pub), "the aim's rule (an instruction) is not projected")
    check(json.dumps(pub, sort_keys=True) == json.dumps(core.ledger_public(REPO), sort_keys=True),
          "the projection is deterministic")
    root = new_root(tmp)
    trimmed = copy.deepcopy(led)
    del trimmed["program"]
    write(root, "tools/ledger.json", json.dumps(trimmed))
    check(raises(lambda: core.ledger_public(root)), "a ledger without program is refused")
    for label, mutate in (
            ("without program.aim", lambda pg: pg.pop("aim")),
            ("with an empty program.aim", lambda pg: pg.__setitem__("aim", "  ")),
            ("with program.aim not a string", lambda pg: pg.__setitem__("aim", ["AGI"])),
            ("without program.substrate", lambda pg: pg.pop("substrate")),
            ("without program.cognitive_map", lambda pg: pg.pop("cognitive_map"))):
        bad = copy.deepcopy(led)
        mutate(bad["program"])
        write(root, "tools/ledger.json", json.dumps(bad))
        check(raises(lambda: core.ledger_public(root), core.PublishError),
              f"a ledger {label} is refused")
    old = copy.deepcopy(led)
    old["program"]["psyche"] = old["program"].pop("substrate")
    write(root, "tools/ledger.json", json.dumps(old))
    check(raises(lambda: core.ledger_public(root), core.PublishError),
          "a ledger that still names the old program key is refused, never half projected")


# ─────────────────────────────────────────────────────────────────────────────
# this file's own source
# ─────────────────────────────────────────────────────────────────────────────

def _prose_nodes(tree: ast.AST) -> set:
    """ids of the string nodes that are prose, not test data: docstrings, and the
    arguments of section(), note() and print() (titles and banners)."""
    prose: set = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                prose.add(id(first.value))
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in ("section", "note", "print")):
            for arg in node.args:
                prose.update(id(sub) for sub in ast.walk(arg))
    return prose


def test_source_hygiene() -> None:
    section("source: no Turkish letter, no raw invisible character, ASCII-only test data")
    src = (HERE / "test_core.py").read_text(encoding="utf-8")
    lines = src.split("\n")         # only '\n': a raw U+2028 must stay inside its line
    turkish = set(map(chr, (0xE7, 0x11F, 0x131, 0xF6, 0x15F, 0xFC,
                            0xC7, 0x11E, 0x130, 0xD6, 0x15E, 0xDC)))
    letters = [n for n, ln in enumerate(lines, 1) if turkish & set(ln)]
    check(letters == [], f"no Turkish letter sits raw in the source (English-only path): "
                         f"lines {letters[:5]}")
    hidden = [(n, f"U+{ord(ch):04X}") for n, ln in enumerate(lines, 1) for ch in ln
              if ch not in " \t" and unicodedata.category(ch)[0] in "ZC"]
    check(hidden == [], f"no invisible or control character sits raw in the source, so no "
                        f"editor can normalise a case away: {hidden[:5]}")
    tree = ast.parse(src)
    prose = _prose_nodes(tree)
    # the literal as WRITTEN (its source segment), so an escape such as \u2028 passes
    # and only a raw character is refused
    written = [(node.lineno, ast.get_source_segment(src, node) or "") for node in ast.walk(tree)
               if (isinstance(node, ast.JoinedStr)
                   or (isinstance(node, ast.Constant) and isinstance(node.value, str)))
               and id(node) not in prose]
    data = [(n, seg[:40]) for n, seg in written if not seg.isascii()]
    check(len(written) > 500 and data == [],
          f"every character outside ASCII in test data or an expectation is built with chr() "
          f"or an escape ({len(written)} literals read): {data[:3]}")
    check(RP.DOT == MIDDOT and RP.DASH == EMDASH,
          "(the renderer's separator and empty cell are the characters the expectations use)")


def main() -> int:
    print("=" * 70)
    print("  PUBLISHING TOOLS — TEST SUITE")
    print("=" * 70)
    tmp = Path(tempfile.mkdtemp(prefix="publish-test-")).resolve()
    os.environ["GIT_CEILING_DIRECTORIES"] = str(tmp)
    try:
        test_guard(tmp)
        test_plan()
        test_plan_fuzz()
        test_load_plan_errors(tmp)
        test_render_pure(tmp)
        test_past_due()
        test_gantt()
        test_render_documents(tmp)
        test_markdown()
        test_ci_c2(tmp)
        test_links(tmp)
        test_ledger_public(tmp)
        test_source_hygiene()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nRESULT: {PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
