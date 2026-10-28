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
            key given twice (a second never_publish) and a lone surrogate stop the guard; a
            page's description (one plain sentence of 120 to 160 characters, no two alike;
            every page of the real manifest has one) and the stager writing it into the front
            matter and refusing a page that has none.
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
  og        the social image names the stage the ledger says is active: the stage line for
            every program state (stage 1, stage 2, both, none), a program line with no stage
            number refused, the check on a repository (a ledger that moved on, a sidecar edited
            to match without a new image, an image replaced by hand, a copy that differs, a
            missing or malformed sidecar, a wrong size, bytes that are no PNG), and the real
            card against the real ledger.
  diagrams  Mermaid fences found the way Markdown reads them (info string, tildes, CRLF;
            a fence in a list item, indented, unclosed or inside a longer fence is refused
            or ignored), the key (source, renderer, nothing else), the SVG the site may
            inline (tags, event attributes, references, key), the replacement (text around
            it kept, one line of HTML, a repeated fence keeps unique ids, no drawing is
            refused with the command to run), the check on a working tree and on a commit
            (missing, left over, renamed, wrong key, renderer changed), and stage_site on a
            fixture repository (drawings read from the commit, never the disk).
  front door  the Makefile has the six fixed targets, each .PHONY, each recipe the fixed
            commands, and a bare make lists them; tools/setup_python.sh parses (bash -n), keeps
            its interpreter list equal to the CI matrix (its install and PATH steps too),
            tools/capture_run.py and the ledger, and, run with a stub uv first on PATH, calls
            'uv python install' with that list and exits 0, reports a version that does not
            resolve with the directory to add to PATH, fails when uv fails, and without uv names
            the installation documentation and exits 1; the README has the status line above the
            Quick start, four badges, each make target with its plain command, the interpreter
            range and links that resolve. Every check is shown to fail on a mutated copy.
  source    this file holds no Turkish letter and no raw invisible character, and every
            character outside ASCII in its test data is built with chr() or an escape.
"""

from __future__ import annotations

import ast
import contextlib
import copy
import hashlib
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
import diagrams as DG          # noqa: E402
import og as OG                # noqa: E402
import stage                   # noqa: E402

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
FIXTURE_DESCRIPTION = ("A page of a fixture repository, written to give the stager the one sentence of "
                       "description it requires, in plain words and within the bounds.")
SECOND_DESCRIPTION = ("The first page of a fixture repository, written to give a second section its one "
                      "sentence of description, in plain words and within the bounds.")
FIXTURE_CITATION = ("cff-version: 1.2.0\nmessage: \"Cite the fixture.\"\ntitle: \"Fixture\"\nauthors:\n"
                    "  - family-names: Example\n    given-names: Ada\n"
                    "  - family-names: Second\n    given-names: Bea\nlicense: MIT\n")
GUARD_MANIFEST = {
    "site_base": "/psyche/",
    "repo": "owner/name",
    "sections": [{"title": "Fixture", "pages": [
        {"src": "docs/ok.md", "slug": "ok", "wiki": "Ok", "description": FIXTURE_DESCRIPTION}]}],
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


def starts(problems: list, prefix: str) -> bool:
    return any(x.startswith(prefix) for x in problems)


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

    section("manifest: a page's description")
    check(len(FIXTURE_DESCRIPTION) >= core.DESCRIPTION_MIN and len(FIXTURE_DESCRIPTION) <= core.DESCRIPTION_MAX,
          "(the fixture description is inside the bounds)")
    ok_text = FIXTURE_DESCRIPTION
    check(core.description_problem(ok_text) is None, "a plain sentence inside the bounds is accepted")
    check(core.DESCRIPTION_MIN == 120 and core.DESCRIPTION_MAX == 160, "the bounds are 120 and 160 characters")
    for label, text, needle in (
            ("a non-string", 7, "string"),
            ("one character short", ok_text[:core.DESCRIPTION_MIN - 2] + ".", "characters"),
            ("one character over", "w" * core.DESCRIPTION_MAX + ".", "characters"),
            ("one character under", "w" * (core.DESCRIPTION_MIN - 2) + ".", "characters"),
            ("no full stop", ok_text[:-1], "full stop"),
            ("a trailing space", ok_text + " ", "one line"),
            ("a line break", ok_text.replace(", in plain", ",\nin plain"), "one line"),
            ("a tab", ok_text.replace(", in plain", ",\tin plain"), "one line"),
            ("two sentences", ok_text.replace(", in plain words", ". In plain words"), "one sentence"),
            ("an angle bracket", ok_text.replace("a fixture", "a <b>fixture"), "plain text"),
            ("an ampersand", ok_text.replace("a fixture", "a fixture &"), "plain text"),
            ("emphasis", ok_text.replace("a fixture", "a *fixture*"), "plain text"),
            ("a link", ok_text.replace("a fixture", "a [fixture](x)"), "plain text"),
            ("a code span", ok_text.replace("a fixture", "a `fixture`"), "plain text")):
        got = core.description_problem(text)
        check(got is not None and needle in got, f"a description with {label} is refused ({got})")
    check(core.description_problem("w" * (core.DESCRIPTION_MIN - 1) + ".") is None
          and core.description_problem("w" * (core.DESCRIPTION_MAX - 1) + ".") is None,
          "a description of exactly 120 and of exactly 160 characters is accepted")
    for label, desc in (("an empty", ""), ("a short", "Too short."), ("a non-string", ["x"])):
        m_bad = copy.deepcopy(GUARD_MANIFEST)
        m_bad["sections"][0]["pages"][0]["description"] = desc
        check(has(core.manifest_problems(m_bad), ".description"),
              f"manifest_problems refuses {label} description")
    m_two = copy.deepcopy(GUARD_MANIFEST)
    m_two["sections"][0]["pages"].append({"src": "docs/two.md", "slug": "two", "wiki": "Two",
                                          "description": FIXTURE_DESCRIPTION.upper()})
    check(has(core.manifest_problems(m_two), "description of another page"),
          "two pages with the same description (in any case) are refused")
    m_two["sections"][0]["pages"][1]["description"] = FIXTURE_DESCRIPTION.replace("fixture", "second fixture")
    check(core.manifest_problems(m_two) == [], "two pages with different descriptions are accepted")
    m_none = copy.deepcopy(GUARD_MANIFEST)
    del m_none["sections"][0]["pages"][0]["description"]
    check(core.manifest_problems(m_none) == [],
          "a manifest without descriptions is valid (stage_site, not the manifest, requires one)")
    real = core.manifest_pages(core.load_manifest(REPO))
    check(all(core.description_problem(p.get("description")) is None for p in real),
          "every page of the real manifest has a valid description")
    check(len({p["description"].casefold() for p in real}) == len(real),
          "no two pages of the real manifest share a description")

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
            ("a status outside the vocabulary", {"item": "P0", "field": "status",
                                                 "from": "planned", "to": "passed"},
             "is not in vocabulary.phase"),
            ("a gate's status (a decision is recorded by decided_on and next_step, D-034)",
             {"item": "A", "field": "status", "from": "upcoming", "to": "decided"},
             "not a field a gate has"),
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
          "<!-- generated:commitments-table:end -->\n\n"
          "<!-- generated:progress-log:start -->\n<!-- generated:progress-log:end -->\n")


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
    check(rc == 1 and "commitments-table" in out and "gate-flow" in out and "progress-log" in out,
          f"blocks fresh but four ids unplaced: --check exits 1 and names them ({rc})")

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
# og: the social image names the stage the ledger says is active
# ─────────────────────────────────────────────────────────────────────────────

def png_bytes(label=None, *, width: int = 1200, height: int = 630, extra: bytes = b"") -> bytes:
    """The smallest byte string the check reads as a PNG of that size, with the stage line the
    generator writes into it as a tEXt chunk (when `label` is given)."""
    def chunk(kind: bytes, body: bytes) -> bytes:
        return len(body).to_bytes(4, "big") + kind + body + b"\x00\x00\x00\x00"
    ihdr = width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
    out = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
    if label is not None:
        out += chunk(b"tEXt", OG.TEXT_KEYWORD.encode("latin-1") + b"\x00" + label.encode("latin-1"))
    return out + chunk(b"IDAT", extra) + chunk(b"IEND", b"")


def og_fixture(tmp: Path, *, states: dict = None):
    """A repository with the real ledger (its program states overridden by `states`), and a card
    and sidecar made for exactly those states. Returns (root, sidecar dict, png bytes)."""
    root = new_root(tmp)
    led = json.loads((REPO / "tools" / "ledger.json").read_text(encoding="utf-8"))
    for line, state in (states or {}).items():
        led["program"][line]["state"] = state
    write(root, "tools/ledger.json", json.dumps(led))
    card = OG.card(root)
    png = png_bytes(card["stage"], extra=b"fixture")
    write(root, OG.CARD_REL, png, binary=True)
    write(root, OG.PUBLIC_REL, png, binary=True)
    side = {"stage": card["stage"], "tagline": card["tagline"], "alt": card["alt"],
            "sha256": hashlib.sha256(png).hexdigest(), "width": 1200, "height": 630,
            "generator": OG.GENERATOR_REL}
    write(root, OG.SIDECAR_REL, json.dumps(side))
    return root, side, png


def test_og(tmp: Path) -> None:
    section("og: the stage line for a program state")
    label = OG.stage_label
    check(label({"substrate": "paused", "cognitive_map": "active"}) == "Stage 2 " + MIDDOT + " Spiking cognitive maps",
          "stage 2 active, stage 1 paused: the card names stage 2")
    check(label({"substrate": "active", "cognitive_map": "paused"}) == "Stage 1 " + MIDDOT + " The substrate",
          "stage 1 active, stage 2 paused: the card names stage 1")
    check(label({"substrate": "active", "cognitive_map": "active"})
          == "Stages 1 and 2 " + MIDDOT + " The substrate and spiking cognitive maps",
          "both active: both stages are named, in stage order")
    check(label({"cognitive_map": "active", "substrate": "active"}) == label({"substrate": "active", "cognitive_map": "active"}),
          "the order of the ledger's keys does not change the line")
    check(label({"substrate": "paused", "cognitive_map": "closed"}) == "No stage active"
          and label({"substrate": "closed", "cognitive_map": "paused"}) == "No stage active",
          "paused and closed are not active: no stage is named")
    check(all(isinstance(OG.STAGES[k][0], int) for k in OG.STAGES)
          and sorted(OG.STAGES) == sorted(core.PUBLIC_PROGRAM_LINES),
          "every program line the public projection knows has a stage number")

    section("og: the card text, from the ledger")
    if not GIT:
        note("(no git needed for these; running on plain directories)")
    root, side, png = og_fixture(tmp)
    states = OG.program_states(root)
    check(states == {"substrate": "paused", "cognitive_map": "active"},
          f"program_states reads the real ledger's two lines ({states})")
    card = OG.card(root)
    check(card["stage"] == "Stage 2 " + MIDDOT + " Spiking cognitive maps" and card["tagline"] == OG.TAGLINE
          and card["url"] == OG.URL_TEXT and card["stage"] in card["alt"] and card["tagline"] in card["alt"]
          and "long-term aim" in card["tagline"] and "is AGI" not in card["tagline"],
          "the card text is the stage line, the tagline (the aim named as an aim) and the address; the alt text holds both")
    rc, out, err = capture(OG.main, ["--card", "--root", str(root)])
    check(rc == 0 and json.loads(out) == card, "--card prints the same text as JSON")
    led = json.loads((root / "tools/ledger.json").read_text(encoding="utf-8"))
    led["program"]["future"] = {"state": "active", "since": "2027-01-01", "decision": "D-0"}
    write(root, "tools/ledger.json", json.dumps(led))
    check(raises(lambda: OG.card(root)) and has(OG.check(root), "STAGES"),
          "a program line with no stage number is refused, naming the table to extend")
    led["program"].pop("future")
    led["program"].pop("cognitive_map")
    write(root, "tools/ledger.json", json.dumps(led))
    check(raises(lambda: OG.card(root)), "a program block missing a line is refused")
    write(root, "tools/ledger.json", "{not json")
    check(raises(lambda: OG.card(root)) and OG.check(root) != [], "an unreadable ledger fails the check")

    section("og: the check")
    root, side, png = og_fixture(tmp)
    check(OG.check(root) == [], "a card drawn for the ledger's program state passes")
    rc, out, err = capture(OG.main, ["--check", "--root", str(root)])
    check(rc == 0 and "Stage 2" in out and err == "", "the command line exits 0 and names the stage")
    check(OG.png_text(png) == {OG.TEXT_KEYWORD: card["stage"]} and OG.png_size(png) == (1200, 630),
          "(the fixture PNG carries its stage line and its size)")
    real = OG.check(REPO)
    check(real == [], f"the real card passes against the real ledger ({real[:2]})")
    real_side = json.loads((REPO / OG.SIDECAR_REL).read_text(encoding="utf-8"))
    check(real_side["stage"] == OG.card(REPO)["stage"] and real_side["generator"] == OG.GENERATOR_REL
          and set(real_side) == set(OG.SIDECAR_KEYS),
          "the real sidecar names the real active stage and is written by the generator")
    check((REPO / OG.CARD_REL).read_bytes() == (REPO / OG.PUBLIC_REL).read_bytes(),
          "the site's image is a byte copy of the brand's")

    # the ledger moves on: the stage the card names is no longer the active one
    for label_, states_ in (("stage 1 becomes the active line", {"substrate": "active", "cognitive_map": "paused"}),
                            ("both lines are paused", {"substrate": "paused", "cognitive_map": "paused"}),
                            ("the cognitive-map line is closed", {"substrate": "paused", "cognitive_map": "closed"})):
        led = json.loads((root / "tools/ledger.json").read_text(encoding="utf-8"))
        for line, state in states_.items():
            led["program"][line]["state"] = state
        write(root, "tools/ledger.json", json.dumps(led))
        probs = OG.check(root)
        want = OG.stage_label(states_)
        check(has(probs, "Stage 2 " + MIDDOT + " Spiking cognitive maps") and has(probs, want) and has(probs, "npm run og"),
              f"when {label_}, the check fails, names both stage lines and the command to run")
        rc, out, err = capture(OG.main, ["--check", "--root", str(root)])
        check(rc == 1 and "problem(s)" in err, f"(and exits 1 when {label_})")
    led = json.loads((root / "tools/ledger.json").read_text(encoding="utf-8"))
    led["program"]["substrate"]["since"] = "2030-01-01"
    led["program"]["substrate"]["state"] = "paused"
    led["program"]["cognitive_map"]["state"] = "active"
    write(root, "tools/ledger.json", json.dumps(led))
    check(OG.check(root) == [], "a change that leaves the active stage as it was (a date) needs no new card")

    # a sidecar edited to match the ledger, with no new image: the image still says the old stage
    root, side, png = og_fixture(tmp)
    led = json.loads((root / "tools/ledger.json").read_text(encoding="utf-8"))
    led["program"]["substrate"]["state"], led["program"]["cognitive_map"]["state"] = "active", "paused"
    write(root, "tools/ledger.json", json.dumps(led))
    new = OG.card(root)
    write(root, OG.SIDECAR_REL, json.dumps(dict(side, stage=new["stage"], alt=new["alt"])))
    probs = OG.check(root)
    check(starts(probs, OG.CARD_REL + " carries the stage line") and starts(probs, OG.PUBLIC_REL + " carries the stage line")
          and not has(probs, "sha256 differs"),
          "a sidecar edited to the new stage, with the old image, fails: each image carries the old stage line (and its hash still matches)")

    # an image replaced by hand
    root, side, png = og_fixture(tmp)
    other = png_bytes(side["stage"], extra=b"another picture")
    write(root, OG.CARD_REL, other, binary=True)
    probs = OG.check(root)
    check(starts(probs, OG.CARD_REL + ": is not the image") and has(probs, "sha256 differs")
          and has(probs, "never edited or replaced by hand") and not starts(probs, OG.PUBLIC_REL + ":"),
          "the brand image changed on its own fails against the sidecar's hash; the untouched site copy does not")
    write(root, OG.SIDECAR_REL, json.dumps(dict(side, sha256=hashlib.sha256(other).hexdigest())))
    probs = OG.check(root)
    check(starts(probs, OG.PUBLIC_REL + ": is not the image") and not starts(probs, OG.CARD_REL + ":"),
          "with the sidecar's hash updated to the new image, the site's copy, which is no longer a copy, fails alone")
    write(root, OG.PUBLIC_REL, other, binary=True)
    check(OG.check(root) == [], "(and with the copy refreshed the card passes again)")

    # missing and malformed pieces
    root, side, png = og_fixture(tmp)
    os.remove(root / OG.PUBLIC_REL)
    check(starts(OG.check(root), OG.PUBLIC_REL + ": missing"), "a missing site image fails")
    os.remove(root / OG.CARD_REL)
    check(starts(OG.check(root), OG.CARD_REL + ": missing"), "a missing brand image fails")
    root, side, png = og_fixture(tmp)
    os.remove(root / OG.SIDECAR_REL)
    check(starts(OG.check(root), OG.SIDECAR_REL + ": missing"), "a missing sidecar fails")
    write(root, OG.SIDECAR_REL, "[1]")
    check(has(OG.check(root), "not a JSON object"), "a sidecar that is not an object fails")
    write(root, OG.SIDECAR_REL, "{")
    check(has(OG.check(root), "not readable JSON"), "a sidecar that is not JSON fails")
    write(root, OG.SIDECAR_REL, json.dumps(dict(side, extra=1)))
    check(has(OG.check(root), "unknown"), "a sidecar with a key of its own fails")
    write(root, OG.SIDECAR_REL, json.dumps({k: v for k, v in side.items() if k != "alt"}))
    check(has(OG.check(root), "missing"), "a sidecar without its alt text fails")
    write(root, OG.SIDECAR_REL, json.dumps(dict(side, tagline="Something else.")))
    check(has(OG.check(root), "tagline"), "a tagline that is not the one og.py gives fails")
    write(root, OG.SIDECAR_REL, json.dumps(dict(side, alt="Something else.")))
    check(has(OG.check(root), "alt text"), "an alt text that is not the one og.py gives fails")
    write(root, OG.SIDECAR_REL, json.dumps(side))
    small = png_bytes(side["stage"], width=600, height=315, extra=b"fixture")
    write(root, OG.CARD_REL, small, binary=True)
    write(root, OG.PUBLIC_REL, small, binary=True)
    write(root, OG.SIDECAR_REL, json.dumps(dict(side, sha256=hashlib.sha256(small).hexdigest())))
    check(has(OG.check(root), "1200 x 630"), "an image of another size fails even when its hash matches")
    write(root, OG.CARD_REL, b"not a png", binary=True)
    write(root, OG.PUBLIC_REL, b"not a png", binary=True)
    write(root, OG.SIDECAR_REL, json.dumps(dict(side, sha256=hashlib.sha256(b"not a png").hexdigest())))
    probs = OG.check(root)
    check(has(probs, "1200 x 630") and has(probs, "carries the stage line None"),
          "bytes that are no PNG fail: no size, no stage line")
    check(OG.png_text(b"") == {} and OG.png_size(b"") is None and OG.png_text(png[:30]) == {},
          "png_text and png_size never raise on short or foreign bytes")
    check(OG.png_text(png_bytes("A" + MIDDOT + "B")) == {OG.TEXT_KEYWORD: "A" + MIDDOT + "B"},
          "a stage line with the middle dot reads back as written (Latin-1)")


# ─────────────────────────────────────────────────────────────────────────────
# diagrams: Mermaid fences drawn ahead of time, inlined by the stager
# ─────────────────────────────────────────────────────────────────────────────

FLOW = "flowchart TD\n  a[\"One\"] --> b[\"Two\"]"
FLOW2 = "flowchart TD\n  a[\"One\"] --> c[\"Three\"]"


def svg_for(key: str, extra: str = "") -> str:
    """The smallest drawing the site may inline, as the render script writes it."""
    return ('<svg xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-labelledby="dg-{key}-t" aria-describedby="dg-{key}-d" data-key="{key}" font-size="12" '
            'viewBox="-8 4 120.5 60" width="121" height="60">\n'
            f' <title id="dg-{key}-t">Flowchart of 2 steps</title>\n'
            f' <desc id="dg-{key}-d">Steps: One; Two.</desc>\n'
            ' <g>\n'
            f'  <marker id="dg-{key}_end" viewBox="0 0 10 10"><path d="M 0 0 L 10 5 z"/></marker>\n'
            f'  <path d="M0,0L10,10" marker-end="url(#dg-{key}_end)" fill="none"/>\n'
            '  <rect x="0" y="0" width="10" height="10"/>\n'
            '  <text text-anchor="middle"><tspan x="0" dy="1.1em">One two</tspan></text>\n'
            f' {extra}</g>\n'
            '</svg>\n')


def test_diagrams(tmp: Path) -> None:
    section("diagrams: fences, keys, drawings")
    page = "# Title\n\nBefore.\n\n```mermaid\n" + FLOW + "\n```\n\nAfter.\n"
    found = DG.fences(page)
    check(len(found) == 1 and found[0].source == FLOW and found[0].line == 5
          and (found[0].first, found[0].last) == (4, 7),
          "a top-level fence is found with its source and its line")
    check(DG.fences("```python\nx = 1\n```\n") == [], "a fence of another language is not a diagram")
    check(DG.fences("````text\n```mermaid\n" + FLOW + "\n```\n````\n") == [],
          "a Mermaid fence shown inside a longer fence is code, not a diagram")
    check([f.source for f in DG.fences("~~~mermaid\n" + FLOW + "\n~~~\n")] == [FLOW],
          "a tilde fence counts")
    check([f.source for f in DG.fences("```Mermaid title=\"x\"\n" + FLOW + "\n```\n")] == [FLOW],
          "the info string is read by its first word, in any case")
    check([f.source for f in DG.fences("```mermaid\r\n" + FLOW.replace("\n", "\r\n") + "\r\n```\r\n")] == [FLOW],
          "CRLF line endings give the same source")
    check(len(DG.fences(page + "\n```mermaid\n" + FLOW2 + "\n```\n")) == 2, "two fences on a page are both found")
    check(DG.fences("") == [] and DG.fences("no fence here\n") == [], "a page with no fence has none")
    for label, bad in (
            ("a list item", "- item\n\n  ```mermaid\n  " + FLOW.replace("\n", "\n  ") + "\n  ```\n"),
            ("a block quote", "> ```mermaid\n> " + FLOW.replace("\n", "\n> ") + "\n> ```\n"),
            ("an indent", " ```mermaid\n" + FLOW + "\n ```\n"),
            ("an unclosed fence", "```mermaid\n" + FLOW + "\n")):
        check(raises(lambda b=bad: DG.fences(b)), f"a Mermaid fence in {label} is refused, never guessed at")

    section("diagrams: the key")
    k = DG.diagram_key("r" * 64, FLOW)
    check(len(k) == DG.KEY_LEN and set(k) <= set("0123456789abcdef"), "a key is 16 hex digits")
    check(k == DG.diagram_key("r" * 64, FLOW), "the key is deterministic")
    check(k != DG.diagram_key("r" * 64, FLOW2), "a changed source changes the key")
    check(k != DG.diagram_key("s" * 64, FLOW), "a changed renderer changes the key")
    check(k != DG.diagram_key("r" * 64, FLOW + " "), "a space in the source changes the key")
    check(DG.renderer_id(b"a") != DG.renderer_id(b"a "), "the renderer id is the hash of the script's bytes")

    section("diagrams: the SVG the site may inline")
    check(DG.svg_problems(svg_for(k), k) == [], "the drawing the render script writes passes")
    check(DG.svg_problems(svg_for(k), "0" * 16) != [], "a drawing made for another key is refused")
    check(DG.svg_problems(svg_for(k).replace('data-key="%s"' % k, ""), k) != [], "a drawing with no key is refused")
    for label, evil in (
            ("a script", "<script>alert(1)</script>"),
            ("a foreignObject", "<foreignObject><div/></foreignObject>"),
            ("an image", "<image x=\"0\" y=\"0\"/>"),
            ("an event attribute", "<rect width=\"1\" height=\"1\" onload=\"x()\"/>"),
            ("an event attribute after a quote", "<rect width=\"1\" height=\"1\"/><rect width='1'onclick='x()'/>"),
            ("a link", "<a>x</a>"),
            ("an href", "<use href=\"#x\"/>"),
            ("a style attribute", "<rect width=\"1\" height=\"1\" style=\"fill:red\"/>"),
            ("a style element", "<style>*{fill:red}</style>"),
            ("a remote url", "<rect width=\"1\" height=\"1\" fill=\"url(http://example.invalid/x)\"/>"),
            ("a javascript url", "<rect width=\"1\" height=\"1\" fill=\"javascript:x()\"/>"),
            ("a comment", "<!-- x -->")):
        check(DG.svg_problems(svg_for(k, evil), k) != [], f"a drawing with {label} is refused")
    check(DG.svg_problems("<div>" + svg_for(k), k) != [], "text before <svg> is refused")
    check(DG.svg_problems(svg_for(k, "<text>Metadata: data: 1 &amp; 2</text>"), k) == [],
          "the words data: and an escaped ampersand in a label are text, not a URL")

    section("diagrams: replacing the fences")
    renderer = "r" * 64
    key1, key2 = DG.diagram_key(renderer, FLOW), DG.diagram_key(renderer, FLOW2)
    have = {key1: svg_for(key1), key2: svg_for(key2)}
    out, used = DG.inline_fences(page, "docs/x.md", renderer, have.get, {})
    check(used == [key1] and "```" not in out and "mermaid" not in out.lower(),
          "the fence is gone and its key is reported")
    check(out.startswith("# Title\n\nBefore.\n\n<figure") and out.endswith("</figure>\n\nAfter.\n"),
          "the text around the fence is kept, with a blank line on each side of the figure")
    html_line = [ln for ln in out.split("\n") if ln.startswith("<figure")]
    check(len(html_line) == 1 and "\n" not in html_line[0] and "<svg" in html_line[0],
          "the figure is one line, so Markdown reads it as one HTML block")
    check('class="sx-diagram not-content"' in html_line[0] and 'tabindex="0"' in html_line[0]
          and "data-pagefind-ignore" in html_line[0] and 'style="--dg-w:120.5"' in html_line[0],
          "the figure carries its class, a focusable scroll box, no search indexing and its drawn width")
    check('<tspan x="0" dy="1.1em">One two</tspan>' in html_line[0],
          "the text of the drawing is not altered by joining its lines")
    check(f'<div class="sx-diagram__scroll" role="group" aria-labelledby="dg-{key1}-t" tabindex="0"' in html_line[0],
          "the focusable scroll box is a group named by the drawing's title, so it is not an unnamed stop")
    out2, used2 = DG.inline_fences(page + "\n```mermaid\n" + FLOW + "\n```\n", "docs/x.md", renderer, have.get, {})
    ids = re.findall(r'\bid="([^"]+)"', out2)
    check(used2 == [key1, key1] and len(ids) == len(set(ids)) and len(ids) >= 6,
          "a fence repeated on one page keeps every id on the page unique")
    again = [ln for ln in out2.split("\n") if ln.startswith("<figure")][1]
    check(f'role="group" aria-labelledby="dg-{key1}-2-t"' in again and f'id="dg-{key1}-2-t"' in again
          and f'aria-describedby="dg-{key1}-2-d"' in again,
          "the second copy of a drawing names its group and describes its image by its own ids")
    check(DG.inline_fences("no fence\n", "docs/x.md", renderer, have.get, {}) == ("no fence\n", []),
          "a page with no fence is returned as it was")
    try:
        DG.inline_fences(page, "docs/x.md", renderer, {}.get, {})
        msg = ""
    except core.PublishError as e:
        msg = str(e)
    check("npm run diagrams" in msg and "docs/x.md" in msg and key1 in msg,
          "a fence with no drawing is refused, naming the page, the key and the command to run")
    bad = {key1: svg_for(key1, "<script/>")}
    check(raises(lambda: DG.inline_fences(page, "docs/x.md", renderer, bad.get, {})),
          "a drawing that is not a plain SVG is never inlined")
    crlf = page.replace("\n", "\r\n")
    out3, _ = DG.inline_fences(crlf, "docs/x.md", renderer, have.get, {})
    check("\r\n<figure" in out3 and out3.endswith("</figure>\r\n\r\nAfter.\r\n"),
          "CRLF line endings are kept around the figure")


def diagram_fixture(tmp: Path, *, script: bytes = b"// renderer one\n", body: str = None, draw: bool = True,
                    manifest: dict = None, extra: dict = None, research_plan: dict = None):
    """A committed repository with one published page holding a Mermaid fence, the render
    script, a citation file and (when `draw`) the drawing of the fence. `manifest` replaces the
    default one, `extra` adds tracked files (path -> text) and `research_plan` replaces the plan.
    Returns (root, key, renderer)."""
    root = new_root(tmp)
    page = body if body is not None else "# Title\n\nBefore.\n\n```mermaid\n" + FLOW + "\n```\n\nAfter.\n"
    write(root, "docs/ok.md", page)
    write(root, "docs/publish.json", json.dumps(manifest if manifest is not None else GUARD_MANIFEST))
    write(root, "tools/ledger.json", (REPO / "tools" / "ledger.json").read_text(encoding="utf-8"))
    write(root, "tools/research_plan.json",
          json.dumps(research_plan if research_plan is not None else plan(), indent=1))
    write(root, core.CITATION_REL.as_posix(), FIXTURE_CITATION)
    write(root, DG.SCRIPT_REL, script, binary=True)
    renderer = DG.renderer_id(script)
    key = DG.diagram_key(renderer, FLOW)
    tracked = ["docs/ok.md", "docs/publish.json", "tools/ledger.json", "tools/research_plan.json",
               core.CITATION_REL.as_posix(), DG.SCRIPT_REL]
    for rel, text in (extra or {}).items():
        write(root, rel, text)
        tracked.append(rel)
    if draw:
        write(root, DG.svg_rel(key), svg_for(key))
        tracked.append(DG.svg_rel(key))
    git_repo(root, tracked)
    return root, key, renderer


def test_diagrams_repo(tmp: Path) -> None:
    section("diagrams: the check on a repository")
    if not GIT:
        check(False, "git is required for the diagram tests and was not found")
        return
    root, key, renderer = diagram_fixture(tmp)
    check(DG.check(root) == [] and DG.check(root, "HEAD") == [],
          "a drawing made for its fence passes, on the disk and in the commit")
    rc, out, err = capture(DG.main, ["--check", "--root", str(root)])
    check(rc == 0 and "1 drawing" in out, "the command line exits 0 and says how many drawings")
    listing = DG.listing(root)
    check([d["key"] for d in listing["diagrams"]] == [key] and listing["diagrams"][0]["source"] == FLOW
          and listing["diagrams"][0]["where"] == ["docs/ok.md:5"] and listing["directory"] == DG.DIR_REL
          and listing["renderer"] == renderer,
          "--list gives the fence, its key, where it stands and the directory the drawings go to")

    # a changed diagram, not yet redrawn
    write(root, "docs/ok.md", "# Title\n\n```mermaid\n" + FLOW2 + "\n```\n")
    problems = DG.check(root)
    check(any("no drawing" in x and "npm run diagrams" in x for x in problems)
          and any(key in x and "matches no Mermaid diagram" in x for x in problems),
          "a changed fence is reported twice: no drawing for the new one, a drawing left for the old")
    rc, out, err = capture(DG.main, ["--check", "--root", str(root)])
    check(rc == 1 and "problem(s)" in err, "the command line exits 1 with a count")
    check(DG.check(root, "HEAD") == [], "the commit is still current: the edit is not committed")
    git_ok(root, "checkout", "-q", "--", "docs/ok.md")

    # a renderer changed (the script's bytes), drawings not redrawn
    write(root, DG.SCRIPT_REL, b"// renderer two\n", binary=True)
    problems = DG.check(root)
    check(any("no drawing" in x for x in problems) and any("matches no Mermaid" in x for x in problems),
          "a changed render script makes every drawing stale")
    git_ok(root, "checkout", "-q", "--", DG.SCRIPT_REL)

    # a drawing nothing uses, a file that is not a drawing, a drawing copied under another name
    other = "0123456789abcdef"
    write(root, DG.svg_rel(other), svg_for(other))
    write(root, DG.DIR_REL + "/notes.txt", "x\n")
    problems = DG.check(root)
    check(sum("matches no Mermaid diagram" in x for x in problems) == 2,
          "a drawing no fence uses, and any other file in the directory, are reported")
    os.remove(root / DG.svg_rel(other))
    os.remove(root / (DG.DIR_REL + "/notes.txt"))
    write(root, DG.svg_rel(key), svg_for(other))
    check(any("data-key" in x for x in DG.check(root)),
          "a drawing under the wrong name (its key is another's) is caught")
    write(root, DG.svg_rel(key), svg_for(key, "<script/>"))
    check(any("tags the site does not inline" in x for x in DG.check(root)),
          "a drawing with a script in it is caught")
    git_ok(root, "checkout", "-q", "--", DG.svg_rel(key))
    check(DG.check(root) == [], "(restored)")

    # a fence that cannot be replaced, a page missing, no script
    write(root, "docs/ok.md", "- item\n\n  ```mermaid\n  " + FLOW.replace("\n", "\n  ") + "\n  ```\n")
    check(any("left margin" in x for x in DG.check(root)), "a Mermaid fence in a list item fails the check")
    git_ok(root, "checkout", "-q", "--", "docs/ok.md")
    os.remove(root / DG.SCRIPT_REL)
    check(any(DG.SCRIPT_REL in x for x in DG.check(root)), "a missing render script fails the check")
    rc, out, err = capture(DG.main, ["--list", "--root", str(root)])
    check(rc == 2, "--list without the script exits 2")
    git_ok(root, "checkout", "-q", "--", DG.SCRIPT_REL)

    # no drawing at all
    root2, key2, _ = diagram_fixture(tmp, draw=False)
    check(any("no drawing" in x for x in DG.check(root2)) and not (root2 / DG.DIR_REL).exists(),
          "a repository with fences and no drawings fails, and the check creates nothing")
    root3, _, _ = diagram_fixture(tmp, body="# Title\n\nNo diagram here.\n", draw=False)
    check(DG.check(root3) == [], "a repository with no fence and no drawing is clean")


def test_stage_diagrams(tmp: Path) -> None:
    section("stage: Mermaid fences become the committed drawings")
    if not GIT:
        check(False, "git is required for the stage tests and was not found")
        return
    root, key, _ = diagram_fixture(tmp)
    res = stage.stage_site(root, "HEAD")
    staged = (root / "website/src/content/docs/ok.md").read_text(encoding="utf-8")
    check(res["diagrams"] == 1 and "```" not in staged and "mermaid" not in staged.lower(),
          "stage_site reports one diagram and no Mermaid fence is left in the staged page")
    check('<figure class="sx-diagram not-content"' in staged and f'data-key="{key}"' in staged
          and "Before." in staged and "After." in staged and staged.count("<figure") == 1,
          "the page holds the drawing in a figure between its own text")
    check(staged.startswith("---\n") and "ledger:ignore-file" in staged and "GENERATED by" in staged,
          "the staged page keeps its front matter, its pragma and its GENERATED line")
    front = staged.split("---\n")[1]
    check(f"description: {json.dumps(FIXTURE_DESCRIPTION)}\n" in front and front.startswith("title: "),
          "the staged front matter carries the page's description from the manifest")
    rc, out, err = capture(stage.main, ["--target", "site", "--root", str(root)])
    check(rc == 0 and "1 diagram(s)" in out, "the command line says how many diagrams were staged")

    # a page with no description is refused: the site never falls back to its general one
    no_desc = copy.deepcopy(GUARD_MANIFEST)
    del no_desc["sections"][0]["pages"][0]["description"]
    write(root, "docs/publish.json", json.dumps(no_desc))
    git_ok(root, "add", "--", "docs/publish.json")
    git_ok(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q",
           "--no-verify", "-m", "fixture manifest without a description")
    rc, out, err = capture(stage.main, ["--target", "site", "--root", str(root)])
    check(rc == 1 and "docs/ok.md" in err and "no description" in err,
          "a published page with no description stops staging, naming the page")
    write(root, "docs/publish.json", json.dumps(GUARD_MANIFEST))
    git_ok(root, "add", "--", "docs/publish.json")
    git_ok(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q",
           "--no-verify", "-m", "fixture manifest with its description")

    # the commit is what is staged, never the disk
    write(root, DG.svg_rel(key), svg_for(key, "<rect x=\"3\" y=\"3\" width=\"3\" height=\"3\"/>"))
    stage.stage_site(root, "HEAD")
    staged = (root / "website/src/content/docs/ok.md").read_text(encoding="utf-8")
    check('x="3" y="3"' not in staged, "a drawing edited after the commit is not staged: the commit's is")
    git_ok(root, "checkout", "-q", "--", DG.svg_rel(key))

    # a drawing committed later is what the next commit stages
    write(root, "docs/ok.md", "# Title\n\n```mermaid\n" + FLOW2 + "\n```\n")
    git_ok(root, "add", "--", "docs/ok.md")
    git_ok(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q",
           "--no-verify", "-m", "fixture edit")
    rc, out, err = capture(stage.main, ["--target", "site", "--root", str(root)])
    check(rc == 1 and "npm run diagrams" in err and DG.DIR_REL in err,
          "a changed fence with no new drawing stops staging, with the command to run")
    key2 = DG.diagram_key(DG.read_renderer(root, None), FLOW2)
    write(root, DG.svg_rel(key2), svg_for(key2))
    git_ok(root, "add", "--", DG.svg_rel(key2))
    git_ok(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q",
           "--no-verify", "-m", "fixture drawing")
    rc, out, err = capture(stage.main, ["--target", "site", "--root", str(root)])
    check(rc == 1 and "no published page uses" in err and key in err,
          "the old drawing, now unused, stops staging until it is dropped")
    git_ok(root, "rm", "-q", "--", DG.svg_rel(key))
    git_ok(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q",
           "--no-verify", "-m", "fixture drop")
    rc, out, err = capture(stage.main, ["--target", "site", "--root", str(root)])
    check(rc == 0 and "1 diagram(s)" in out, "with the drawing replaced and the old one dropped, staging passes")

    # an unsafe drawing is never staged
    root2, key3, _ = diagram_fixture(tmp)
    write(root2, DG.svg_rel(key3), svg_for(key3, "<rect width=\"1\" height=\"1\" onclick=\"x()\"/>"))
    git_ok(root2, "add", "--", DG.svg_rel(key3))
    git_ok(root2, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q",
           "--no-verify", "-m", "fixture unsafe")
    rc, out, err = capture(stage.main, ["--target", "site", "--root", str(root2)])
    check(rc == 1 and "event-handler" in err, "a committed drawing with an event handler is refused at staging")


def test_stage_sidebar_labels() -> None:
    section("stage: the hand-written pages' sidebar labels say what each page is, and are not a document's title")
    custom = [(label, path) for label, path in stage.CUSTOM_PAGES if path]
    labels = [label for label, _ in stage.CUSTOM_PAGES]
    check(len({x.casefold() for x in labels}) == len(labels), "no two hand-written pages share a label")

    # the titles of the staged documents, as the stager takes them: the manifest's override or the first heading
    manifest = core.load_manifest(REPO)
    titles = []
    for page in core.manifest_pages(manifest):
        text = (REPO / page["src"]).read_text(encoding="utf-8")
        titles.append(page.get("title") or stage.split_title(text, page["src"])[0])
    check(len(titles) >= 10 and all(titles), "the titles of the published documents are read")
    for label, path in custom:
        low = label.casefold()
        clash = [t for t in titles if t.casefold() in low or low in t.casefold()]
        check(clash == [], f"the label {label!r} is not, and does not contain, a document title (found {clash})")
    check(all(label.casefold() != "home" or not path for label, path in stage.CUSTOM_PAGES),
          "only the home page is labelled Home")

    # a page's own title is its sidebar label: the front matter of website/src/pages/<name>.astro says the same
    for label, path in custom:
        page_file = REPO / "website" / "src" / "pages" / (path.strip("/") + ".astro")
        text = page_file.read_text(encoding="utf-8")
        found = re.search(r"^\s*title: '([^'\n]*)',?$", text, re.M)
        check(found is not None and found.group(1) == label,
              f"{page_file.name} has the title {label!r} that its sidebar label shows")


# ─────────────────────────────────────────────────────────────────────────────
# the plan's public events, the progress page's block and the feed's data
# ─────────────────────────────────────────────────────────────────────────────

def events_plan() -> dict:
    """The fixture plan as of the commitment's day with one event of every kind: gate A decided on
    2026-11-14 (so P0, which it closes, is done that day, and P1 started on 2026-11-16),
    two changes recorded in the changelog and one hash commitment."""
    p = decided_plan("continues", 0, "2026-11-14")
    p["as_of"] = COMMITMENT["date"]
    p["phases"][1]["status"] = "active"
    p["gates"][1]["date"] = "2027-01-07"
    p["changelog"] = [
        {"date": "2026-11-03", "item": "B", "field": "date", "from": "2026-12-31",
         "to": "2027-01-07", "reason": "a fixture move", "ref": "fixture"},
        {"date": "2026-11-02", "item": "L1", "field": "title", "from": "Safe base",
         "to": "Safe base layer", "reason": "a clearer name", "ref": "fixture"},
    ]
    p["commitments"] = [dict(COMMITMENT)]
    return p


def event_triples(events: list) -> list:
    return [(e["kind"], e["id"], e["date"]) for e in events]


def test_progress_events() -> None:
    section("events: the plan's public events, derived from the plan and nothing else")
    p = events_plan()
    check(problems_of(p) == [], f"the fixture plan with every kind of event is valid: {problems_of(p)[:2]}")
    events = RP.progress_events(p)
    check(event_triples(events) == [
        ("commitment", "commitment/PC-001", "2026-12-01"),
        ("phase-started", "phase-started/P1", "2026-11-16"),
        ("phase-done", "phase-done/P0", "2026-11-14"),
        ("gate-decided", "gate-decided/A", "2026-11-14"),
        ("change", "change/2026-11-03/B/date/1", "2026-11-03"),
        ("change", "change/2026-11-02/L1/title/1", "2026-11-02"),
        ("phase-started", "phase-started/P0", "2026-10-23")],
        f"one event of every kind, newest first: {event_triples(events)}")
    by_kind = {e["kind"]: e for e in events}
    check(all(tuple(e) == RP.EVENT_KEYS for e in events) and len({e["id"] for e in events}) == len(events),
          "every event has exactly the same keys, and its own id")
    check(by_kind["phase-done"]["subject"] == "Phase P0, Novelty review and setup"
          and by_kind["phase-done"]["headline"] == "Phase P0 done" and by_kind["phase-done"]["change"] == "done",
          "a phase done says so with its code and title")
    check(by_kind["gate-decided"] == {
        "id": "gate-decided/A", "kind": "gate-decided", "date": "2026-11-14", "item": "A",
        "subject": "Gate A, Novelty", "headline": "Gate A decided",
        "change": "decided; the line continues to the next phase"},
        "a decided gate's event is its date and its next step in the project's words")
    changes = [e for e in events if e["kind"] == "change"]
    check(changes[0]["change"] == "date changed from 2026-12-31 to 2027-01-07 (reason: a fixture move)"
          and changes[0]["subject"] == "Gate B, Comparisons" and changes[0]["headline"] == "Gate B date changed"
          and changes[1]["subject"] == "Layer L1, Safe base" and changes[1]["headline"] == "Layer L1 title changed",
          "a changelog entry gives the field, the old and new value and the reason, in words")
    check(by_kind["commitment"]["subject"] == "Commitment PC-001, frozen criteria"
          and by_kind["commitment"]["change"] == "hash committed; reveal: at submission"
          and GOOD_SHA256 not in json.dumps(events),
          "a commitment gives its date, id, subject and reveal, and not its hash")
    check("fixture" not in json.dumps([e for e in events if e["kind"] == "change"]).replace("a fixture move", ""),
          "a changelog entry's ref is not carried")
    for step in core.NEXT_STEPS:
        ev = [e for e in RP.progress_events(decided_plan(step)) if e["kind"] == "gate-decided"]
        check(len(ev) == 1 and ev[0]["change"] == "decided; " + RP.NEXT_STEP_TEXT[step],
              f"a gate decided with the next step {step!r} reads in the project's words")

    section("events: a decided gate's event carries nothing but the gate, the date and the next step (D-034)")
    g = decided_plan("stops")
    g["gates"][0].update(verdict="VERDICT-SENTINEL", evidence="EVIDENCE-SENTINEL", criterion="CRITERION-SENTINEL")
    dumped = json.dumps(RP.progress_events(g))
    gate = g["gates"][0]
    for needle in ("VERDICT-SENTINEL", "EVIDENCE-SENTINEL", "CRITERION-SENTINEL", gate["question"],
                   gate["if_missed"]):
        check(needle not in dumped, f"{needle!r} is not in any event")
    check("the line stops" in dumped, "(the next step is)")
    fn = next(n for n in ast.walk(ast.parse((HERE / "render_plan.py").read_text(encoding="utf-8")))
              if isinstance(n, ast.FunctionDef) and n.name == "progress_events")
    read = set()
    for node in ast.walk(fn):
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "g"
                and isinstance(node.slice, ast.Constant)):
            read.add(node.slice.value)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "g" and node.args
                and isinstance(node.args[0], ast.Constant)):
            read.add(node.args[0].value)
    check(read == {"id", "status", "next_step", "decided_on"},
          f"the event reader opens only these fields of a gate: {sorted(read)}")
    undated = decided_plan("continues")
    del undated["gates"][0]["decided_on"]
    check("gate-decided" not in {e["kind"] for e in RP.progress_events(undated)},
          "a decided gate with no decision date has no event: an event needs a day")

    section("events: what makes a phase an event")
    q = plan(as_of="2026-11-20")
    q["phases"][0].update(status="done")                      # started 2026-10-23, ended 2026-11-15
    q["phases"][1].update(status="active", start="2026-11-21")  # active, but starts after as_of
    check(event_triples(RP.progress_events(q)) == [
        ("phase-done", "phase-done/P0", "2026-11-15"), ("phase-started", "phase-started/P0", "2026-10-23")],
        "a phase done has a start and an end; an active one that starts after the plan's day has none yet")
    q["phases"][1]["start"] = "2026-11-20"
    check(("phase-started", "phase-started/P1", "2026-11-20") in event_triples(RP.progress_events(q)),
          "a phase that starts on the plan's own day has started")
    q["phases"][1].update(status="planned")
    check(all(e["id"] != "phase-started/P1" for e in RP.progress_events(q)), "a planned phase has no event")
    r = plan(as_of="2027-05-01")
    r["phases"][3].update(status="done")                      # a fixed start, an end that is a rule
    r["phases"][4].update(status="done")                      # no fixed start or end at all
    ids = {e["id"] for e in RP.progress_events(r)}
    check("phase-started/P3" in ids and "phase-done/P3" not in ids,
          "a done phase with a fixed start but an end that is a rule has a start and no end")
    check("phase-started/P4" not in ids and "phase-done/P4" not in ids,
          "a phase with no fixed day for either step has no event")

    section("events: order, ties, stability, an empty plan")
    t = events_plan()
    t["gates"][0]["decided_on"] = "2026-11-16"
    t["phases"][0]["end"] = "2026-11-16"
    t["commitments"][0]["date"] = "2026-11-16"
    t["changelog"][0]["date"] = "2026-11-16"
    t["changelog"][1]["date"] = "2026-11-16"
    check(problems_of(t) == [], f"the plan with five kinds on one day is valid: {problems_of(t)[:2]}")
    same_day = [e["id"] for e in RP.progress_events(t) if e["date"] == "2026-11-16"]
    check(same_day == ["commitment/PC-001", "change/2026-11-16/B/date/1", "change/2026-11-16/L1/title/1",
                       "phase-started/P1", "phase-done/P0", "gate-decided/A"],
          f"a tie breaks by kind (the later step of a story first), then by item: {same_day}")
    reversed_plan = json.loads(json.dumps(t))
    for key in ("phases", "gates", "changelog", "layers"):
        reversed_plan[key].reverse()
    check(RP.progress_events(reversed_plan) == RP.progress_events(t),
          "the order does not depend on the order of the plan's lists")
    twice = t["changelog"] + [dict(t["changelog"][1], **{"from": "Safe base layer", "to": "Safe base",
                                                         "reason": "undone"})]
    t["changelog"] = twice
    again = [e for e in RP.progress_events(t) if e["id"].startswith("change/2026-11-16/L1")]
    check([e["id"] for e in again] == ["change/2026-11-16/L1/title/2", "change/2026-11-16/L1/title/1"]
          and "undone" in again[0]["change"],
          "two entries for one item and field on one day keep separate ids, the later entry first")
    before = {e["id"]: e for e in RP.progress_events(events_plan())}
    later = events_plan()
    later["phases"][2].update(status="active", start="2026-11-18")
    later["phases"][1].update(status="done")
    after = {e["id"]: e for e in RP.progress_events(later)}
    check(all(after[i] == e for i, e in before.items() if i in after)
          and {"phase-started/P2"} <= set(after) - set(before),
          "a new event leaves the others as they were, ids included")
    empty = plan()
    empty["phases"][0]["status"] = "planned"
    check(problems_of(empty) == [] and RP.progress_events(empty) == [], "a plan with nothing yet has no event")
    check(RP.render_progress_log(empty) == "\n".join([
        "| Date | What changed |", "|---|---|", f"| none yet | {EMDASH} |"]),
        "and its log is one 'none yet' row")
    odd = plan(as_of="2026-11-10")
    odd["changelog"] = [{"date": "2026-11-05", "item": "P4", "field": "end_rule", "from": None,
                         "to": "the release calendar", "reason": "a rule was added", "ref": "fixture"}]
    check(problems_of(odd) == []
          and RP.progress_events(odd)[0]["change"]
          == "end rule changed from not set to the release calendar (reason: a rule was added)",
          "a value that was not set reads 'not set'")
    check(set(RP.FIELD_WORDS) == set(core.ALL_CHANGE_FIELDS) and set(RP.EVENT_KINDS) == {
        "commitment", "change", "phase-started", "phase-done", "gate-decided"},
        "every field the changelog may record has a word, and the kinds are the five")

    section("events: the changelog cannot carry the reasoning behind a decision (D-034)")
    sentinel = "REASON-SENTINEL verdict and reasoning"
    d = events_plan()
    d["changelog"].append({"date": "2026-11-13", "item": "A", "field": "status", "from": "upcoming",
                           "to": "decided", "reason": sentinel, "ref": "fixture"})
    check(has(problems_of(d), "not a field a gate has"),
          "the plan refuses a changelog entry for a gate's status: a decision has decided_on and next_step")
    forced = RP.progress_events(d)                   # a plan that got past the validator all the same
    check(sentinel not in json.dumps(forced) and sentinel not in RP.render_progress_log(d)
          and not any(e["id"].startswith("change/2026-11-13/A/") for e in forced),
          "and such an entry makes no event, so its reason reaches neither the log nor the feed's data")
    d = events_plan()
    d["changelog"].append({"date": "2026-11-17", "item": "P1", "field": "status", "from": "planned",
                           "to": "active", "reason": sentinel, "ref": "fixture"})
    status_events = [e for e in RP.progress_events(d) if e["id"].startswith("change/2026-11-17/P1/status/")]
    check(problems_of(d) == [] and len(status_events) == 1
          and status_events[0]["change"] == "status changed from planned to active"
          and sentinel not in json.dumps(RP.progress_events(d)) and sentinel not in RP.render_progress_log(d),
          "a change of status says what changed and gives no reason, whatever the item")

    section("events: nothing is dated after the plan's day")
    f = decided_plan("continues", 0, "2026-11-12")     # decided early: P0 is done, but its planned end is 2026-11-15
    f["as_of"] = "2026-11-12"
    check(problems_of(f) == [], f"the early decision is a valid plan: {problems_of(f)[:2]}")
    early = {e["id"]: e["date"] for e in RP.progress_events(f)}
    check(early.get("phase-done/P0") == "2026-11-12" and early.get("gate-decided/A") == "2026-11-12"
          and max(early.values()) == "2026-11-12",
          f"a phase done before its planned end is done on the plan's day, not on a day that has not come: {early}")
    f["phases"][0]["end"] = "2026-11-10"
    f["phases"][0]["start"] = "2026-10-23"
    check({e["id"]: e["date"] for e in RP.progress_events(f)}.get("phase-done/P0") == "2026-11-12",
          "a phase its gate closes is done on the day of the decision, whatever its planned end")
    moved = {}
    for day in ("2026-11-12", "2026-11-14", "2026-11-20", "2027-03-01"):
        f["as_of"] = day
        moved[day] = {e["id"]: e["date"] for e in RP.progress_events(f)}.get("phase-done/P0")
    check(set(moved.values()) == {"2026-11-12"},
          f"and that date does not move when only the plan's as_of moves: {moved}")
    ext = decided_plan("extends", 0, "2026-11-12")
    ext["phases"][0]["status"] = "done"              # not what the recording edit does, but readable
    ext["as_of"] = "2026-11-13"
    check({e["id"]: e["date"] for e in RP.progress_events(ext)}.get("phase-done/P0") == "2026-11-13",
          "a gate that extends its phase does not close it, so the phase is dated by its end or the plan's day")
    loose = plan(as_of="2027-04-20")
    loose["phases"][3].update(status="done", end="2027-04-15")   # P3 has no gate
    check({e["id"]: e["date"] for e in RP.progress_events(loose)}.get("phase-done/P3") == "2027-04-15",
          "a done phase with no gate that closes it is done on its end")
    loose["as_of"] = "2027-04-10"
    check({e["id"]: e["date"] for e in RP.progress_events(loose)}.get("phase-done/P3") == "2027-04-10",
          "or on the plan's day when its end has not come")
    g2 = events_plan()
    g2["as_of"] = "2026-11-20"
    g2["commitments"][0]["date"] = "2026-11-21"
    g2["changelog"].append(dict(g2["changelog"][0], date="2026-11-25"))
    ids = {e["id"] for e in RP.progress_events(g2)}
    check("commitment/PC-001" not in ids and not any(i.startswith("change/2026-11-25") for i in ids),
          "a commitment or a change dated after the plan's day is not an event yet")
    check(max(e["date"] for e in RP.progress_events(g2)) <= "2026-11-20",
          "so the feed's newest day is never later than the plan's own")

    section("events: the real plan")
    real = core.load_plan(REPO)
    real_events = RP.progress_events(real)
    check(len(real_events) >= 1 and all(tuple(e) == RP.EVENT_KEYS for e in real_events)
          and len({e["id"] for e in real_events}) == len(real_events)
          and [e["date"] for e in real_events] == sorted((e["date"] for e in real_events), reverse=True),
          "the real plan's events are keyed alike, have their own ids and run newest first")
    outs = []
    for seed in ("0", "1"):
        proc = subprocess.run(
            [sys.executable, "-B", "-c",
             "import json,sys; sys.path.insert(0, sys.argv[1]); import core, render_plan; "
             "print(json.dumps(render_plan.progress_events(core.load_plan(core.REPO))))", str(HERE)],
            capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED=seed))
        outs.append(proc.stdout)
        check(proc.returncode == 0, f"the events derive in a fresh process (seed {seed}): {proc.stderr[:200]}")
    check(outs[0] == outs[1] and json.loads(outs[0]) == real_events,
          "two processes with different hash seeds derive the same events")


def test_progress_log() -> None:
    section("progress-log: the block, as a table of the events")
    check("progress-log" in RP.RENDERERS and "progress-log" in ALL_IDS, "the block is registered")
    p = events_plan()
    table = RP.render_progress_log(p).split("\n")
    check(table[0] == "| Date | What changed |" and table[1] == "|---|---|" and len(table) == 2 + 7,
          "a header and one row for each event, in two columns so that the table fits a phone")
    check(table[2] == "| 2026-12-01 | Commitment PC-001, frozen criteria: hash committed; reveal: at submission |"
          and table[5] == "| 2026-11-14 | Gate A, Novelty: decided; the line continues to the next phase |",
          "a row is the day, then the item and what changed in one cell")
    p["changelog"][0]["reason"] = "a | b *c* [d]"
    check("(reason: a \\| b \\*c\\* \\[d\\])" in RP.render_progress_log(p),
          "plan text cannot break a table row or add emphasis")
    rendered = RP.render_checked(events_plan())
    check(rendered["progress-log"] == RP.render_progress_log(events_plan())
          and not any(lab in "\n".join(rendered.values()) for lab in STATUS_LABELS),
          "it is rendered with the other blocks and passes the status-label check")
    sneaky = events_plan()
    sneaky["changelog"][1]["reason"] = "PROV" + "EN by hand"
    check(has(problems_of(sneaky), "status label"), "a status label in a reason is refused by the plan check")
    page = (REPO / "docs/progress.md").read_text(encoding="utf-8")
    check(all(f"<!-- generated:{b}:start -->" in page for b in ("progress-log", "commitments-table")),
          "docs/progress.md carries the log and the commitments")
    rc, out, err = capture(RP.main, ["--check"])
    check(rc == 0, f"render_plan --check is clean on the repository ({rc}): {out[-200:]}{err[-200:]}")
    # a block placed on two pages is rendered on both, and the same bytes
    root = new_root(Path(tempfile.mkdtemp(prefix="publish-test-twice-")))
    try:
        _doc_fixture(root, plan())
        write(root, "docs/research/again.md", "<!-- generated:progress-log:start -->\n"
              "<!-- generated:progress-log:end -->\n")
        rc, _, err = capture(RP.main, ["--root", str(root), "--write"])
        a = (root / "docs/research/again.md").read_text(encoding="utf-8")
        b = (root / "docs/research/flow.md").read_text(encoding="utf-8")
        check(rc == 0 and RP.render_progress_log(plan()) in a and RP.render_progress_log(plan()) in b,
              f"the same block on two pages is written on both ({rc}) {err}")
    finally:
        shutil.rmtree(root.parent, ignore_errors=True)


def test_citation_author() -> None:
    section("citation: the feed's author is the first author of CITATION.cff, as the file gives the name")
    real = (REPO / core.CITATION_REL).read_text(encoding="utf-8")
    check(core.citation_author(real) == "Cagan Caliskan", "the repository's file names its project lead")
    check(core.citation_author(FIXTURE_CITATION) == "Ada Example", "only the first author is read")
    cases = {
        "given names after the family names": "authors:\n  - given-names: Ada\n    family-names: Example\n",
        "quoted values": "authors:\n  - family-names: \"Example\"\n    given-names: 'Ada'  # a comment\n",
        "a name particle and a suffix": ("authors:\n  - family-names: Lovelace\n    given-names: Ada\n"
                                         "    name-particle: King\n    name-suffix: Jr.\n"),
        "a blank line and a comment": "authors:\n\n  # the lead\n  - family-names: Example\n    given-names: Ada\n",
    }
    want = {"given names after the family names": "Ada Example", "quoted values": "Ada Example",
            "a name particle and a suffix": "Ada King Lovelace Jr.", "a blank line and a comment": "Ada Example"}
    for label, text in cases.items():
        check(core.citation_author("cff-version: 1.2.0\n" + text + "title: x\n") == want[label], label)
    check(core.citation_author("authors:\n  - name: \"The Fixture Group\"\n") == "The Fixture Group",
          "an entity is named by its name")
    for label, text in {
            "no authors list": "cff-version: 1.2.0\ntitle: x\n",
            "an empty list": "authors:\ntitle: x\n",
            "an author with no name": "authors:\n  - orcid: https://orcid.org/0000-0000-0000-0000\n",
            "a scalar list": "authors:\n  - Ada Example\n",
            "a control character": "authors:\n  - family-names: \"Ex\\u0007ample\"\n    given-names: Ada\n".replace(
                "\\u0007", chr(7)),
            "a flow mapping": "authors: [{family-names: Example, given-names: Ada}]\n"}.items():
        try:
            core.citation_author(text)
            check(False, f"{label} is refused")
        except core.PublishError:
            check(True, f"{label} is refused")


def cited_doi() -> str:
    """The doi of preferred-citation in CITATION.cff: the one place the project's citation is kept."""
    text = (REPO / core.CITATION_REL).read_text(encoding="utf-8")
    block = re.search(r"^preferred-citation:[ \t]*\n((?:[ \t]+\S.*\n|[ \t]*\n)+)", text, re.M)
    found = re.search(r"^[ \t]+doi:[ \t]*[\"']?(10\.\d{4,9}/[^\s\"']+)[\"']?[ \t]*$", block.group(1), re.M) if block else None
    return found.group(1) if found else ""


def test_cited_doi() -> None:
    section("citation: the DOI the site prints is the DOI of CITATION.cff's preferred citation")
    doi = cited_doi()
    check(re.fullmatch(r"10\.\d{4,9}/\S+", doi) is not None, f"preferred-citation in CITATION.cff has a DOI: {doi!r}")
    landing = (REPO / "website/src/components/landing/CiteContact.astro").read_text(encoding="utf-8")
    typed = re.findall(r"\b10\.\d{4,9}/[^\s\"'`<>)]+", landing)
    check(typed == [doi] and f"doi: '{doi}'" in landing,
          f"the landing's cite section holds that DOI, and only that one, as its constant: {typed}")
    check("https://doi.org/${cite.doi}" in landing and "href={doiUrl}" in landing,
          "and the DOI is the link in the reference, through that constant")
    guide = (REPO / "docs/guide.md").read_text(encoding="utf-8")
    links = re.findall(r"https://doi\.org/(\S+?)(?=[>)\s])", guide)
    check(links and all(x == doi for x in links),
          f"every doi.org link in docs/guide.md is that DOI: {links}")
    manifest = core.load_manifest(REPO)
    seo = (REPO / "website/src/lib/seo.ts").read_text(encoding="utf-8")
    check(f"export const REPO_URL = 'https://github.com/{manifest['repo']}';" in seo,
          "the site's repository address is the manifest's repository")
    check("href={`${REPO_URL}/discussions`}" in landing,
          "the landing's cite section links the repository's GitHub Discussions page")
    check("href={withBase('guide/')}" in landing, "and the Reader's guide")
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    badge = re.findall(r"https://zenodo\.org/badge/DOI/(10\.\d{4,9}/[^\s)]+?)\.svg", readme)
    links = re.findall(r"https://doi\.org/([^\s>)\]*]+)", readme)
    typed_in_readme = {re.sub(r"(\.svg)?\.?$", "", x) for x in re.findall(r"\b10\.\d{4,9}/[^\s\"'`<>)\]*]+", readme)}
    check(badge == [doi], f"the README's DOI badge is that DOI: {badge}")
    check(links and all(x == doi for x in links), f"every doi.org link in the README is that DOI: {links}")
    check(typed_in_readme == {doi}, f"and the README types no other DOI: {sorted(typed_in_readme)}")
    other = readme.replace(doi, doi[:-1] + ("0" if doi[-1] != "0" else "1"), 1)
    check(re.findall(r"https://zenodo\.org/badge/DOI/(10\.\d{4,9}/[^\s)]+?)\.svg", other) != [doi]
          or {re.sub(r"(\.svg)?\.?$", "", x) for x in re.findall(r"\b10\.\d{4,9}/[^\s\"'`<>)\]*]+", other)} != {doi},
          "(the comparison is able to fail: a README with one digit of the DOI changed is seen)")


# ─────────────────────────────────────────────────────────────────────────────
# the front door: the Makefile, tools/setup_python.sh and README.md
# ─────────────────────────────────────────────────────────────────────────────

MAKE_TARGETS = ("help", "setup", "test", "check", "capture", "site")
MAKE_RECIPES = {
    "setup": ["bash tools/setup_python.sh"],
    "test": ["python3 run_tests.py"],
    "check": [
        "python3 tools/ledger_check.py --only C1,C3,C4,C5,C6",
        "python3 tools/publish/ci_c2.py",
        "python3 tools/publish/check_copy.py",
        "python3 tools/publish/render_plan.py --check",
        "python3 tools/publish/diagrams.py --check",
        "python3 tools/test_ledger.py",
        "python3 -B tools/publish/test_core.py",
        "python3 -B tools/publish/test_checks.py",
    ],
    "capture": ["python3 tools/capture_run.py"],
    "site": ["cd website && npm ci", "cd website && npm run dev"],
}
UV_DOCS_URL = "https://docs.astral.sh/uv/getting-started/installation/"
SETUP_SCRIPT = REPO / "tools" / "setup_python.sh"
UV_STUB = "\n".join([
    "#!/bin/sh",
    "printf '%s\\n' \"$*\" >> \"$UV_STUB_LOG\"",
    "if [ \"$1\" = python ] && [ \"$2\" = install ]; then exit \"${UV_STUB_INSTALL_RC:-0}\"; fi",
    "if [ \"$1\" = python ] && [ \"$2\" = dir ]; then",
    "  if [ \"${UV_STUB_NO_BIN_FLAG:-0}\" = 1 ]; then echo \"error: unexpected argument\" >&2; exit 2; fi",
    "  echo \"$UV_STUB_BIN\"; exit 0",
    "fi",
    "exit 0",
    ""])


def join_continuations(text: str) -> list:
    """The lines of a Makefile with each backslash continuation joined to the line before it."""
    lines, i = text.replace("\r\n", "\n").split("\n"), 0
    joined = []
    while i < len(lines):
        ln = lines[i]
        while ln.endswith("\\") and i + 1 < len(lines):
            i += 1
            ln = ln[:-1] + " " + lines[i].lstrip()
        joined.append(ln)
        i += 1
    return joined


def parse_makefile(text: str) -> tuple:
    """(rules, prerequisites, phony, default goal) of a Makefile's text. A rule is a name at the
    start of a line followed by a colon; its recipe is the tab-indented lines after it, each
    stripped of the prefixes that change nothing about whether a failure stops make (@ and +) and
    of extra whitespace. A `-` prefix is kept, because it makes make carry on after a failure.
    Backslash continuations are joined. Enough make for this file, not a make."""
    rules, prereqs, phony, default, current = {}, {}, set(), None, None
    for ln in join_continuations(text):
        if ln.startswith("\t"):
            if current is not None:
                rules[current].append(" ".join(ln.strip().lstrip("@+ ").split()))
            continue
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        m = re.match(r"^\.PHONY\s*:\s*(.*)$", ln)
        if m:
            phony.update(m.group(1).split())
            current = None
            continue
        m = re.match(r"^\.DEFAULT_GOAL\s*:?=\s*(\S+)\s*$", ln)
        if m:
            default, current = m.group(1), None
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*:(?!=)\s*(.*)$", ln)
        if m:
            current = m.group(1)
            rules.setdefault(current, [])
            prereqs[current] = m.group(2).split()
        else:
            current = None
    return rules, prereqs, phony, default


MAKE_TOP_LEVEL = (
    re.compile(r"^\.PHONY\s*:"),
    re.compile(r"^\.DEFAULT_GOAL\s*:?=\s*\S+\s*$"),
    re.compile(r"^[A-Za-z0-9_.-]+\s*:(?!=)"),
)


def makefile_stray_lines(text: str) -> list:
    """The top-level lines of a Makefile that are none of: blank, a comment, a recipe line, .PHONY,
    .DEFAULT_GOAL or a rule. A variable (MAKEFLAGS, SHELL, .SHELLFLAGS, an exported PATH), an
    include or any other text changes how make runs the recipes, and the recipe check cannot see it."""
    out = []
    for ln in join_continuations(text):
        if not ln.strip() or ln.startswith("\t") or ln.lstrip().startswith("#"):
            continue
        if not any(p.match(ln) for p in MAKE_TOP_LEVEL):
            out.append(ln.strip())
    return out


def makefile_problems(text: str) -> list:
    """Everything wrong with a Makefile against the fixed target list: the set of targets, each
    one .PHONY, a bare `make` that lists them, exactly the commands each recipe is meant to run
    (and nothing hidden behind a prerequisite or in a line outside the rules), and a help text
    with one line per target."""
    rules, prereqs, phony, default = parse_makefile(text)
    out = []
    for ln in makefile_stray_lines(text):
        out.append(f"a top-level line that is not a rule, .PHONY or .DEFAULT_GOAL: {ln!r}")
    if sorted(rules) != sorted(MAKE_TARGETS):
        out.append(f"targets are {sorted(rules)}, not {sorted(MAKE_TARGETS)}")
    if phony != set(MAKE_TARGETS):
        out.append(f".PHONY is {sorted(phony)}, not {sorted(MAKE_TARGETS)}")
    first = next(iter(rules), None)
    if not (default == "help" or (default is None and first == "help")):
        out.append(f"a bare make runs {default or first!r}, not help")
    for name, want in MAKE_RECIPES.items():
        if rules.get(name) != want:
            out.append(f"{name}: the recipe is {rules.get(name)}, not {want}")
    for name, pre in prereqs.items():
        if pre:
            out.append(f"{name} has prerequisites {pre}")
    help_lines = rules.get("help", [])
    if not help_lines or any(re.match(r"(echo|printf)\b", ln) is None for ln in help_lines):
        out.append("help does more than print")
    listed = "\n".join(help_lines)
    for name in MAKE_TARGETS:
        n = len(re.findall(rf"\bmake {name}\b", listed))
        if n != 1:
            out.append(f"help names 'make {name}' {n} times, not once")
    return out


def version_key(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def interpreter_lists(script: str, workflow: str, capture: str, ledger: str) -> dict:
    """Every list of CPython minors the project keeps, each read from its own file as a list of
    '3.X' strings (None when the list cannot be found, which is itself a finding)."""
    out = {}
    m = re.search(r"^VERSIONS=\(([^)\n]*)\)[ \t]*$", script, re.M)
    out["setup_python.sh VERSIONS"] = m.group(1).split() if m else None
    m = re.search(r"^[ \t]*matrix:[ \t]*\n[ \t]*python-version:[ \t]*\[([^\]\n]*)\]", workflow, re.M)
    out["tests.yml matrix"] = [x.strip().strip("\"'") for x in m.group(1).split(",")] if m else None
    m = re.search(r"python-version:[ \t]*\|[ \t]*\n((?:[ \t]+\d+\.\d+[ \t]*\n)+)", workflow)
    out["tests.yml install step"] = m.group(1).split() if m else None
    m = re.search(r"for v in ((?:\d+\.\d+ )+\d+\.\d+); do", workflow)
    out["tests.yml PATH check"] = m.group(1).split() if m else None
    names = None
    for node in ast.walk(ast.parse(capture)):
        if (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CANDIDATES"
                                                 for t in node.targets)):
            names = [n[len("python"):] for n in ast.literal_eval(node.value)]
    out["capture_run.py CANDIDATES"] = names
    try:
        out["ledger determinism.interpreters_required"] = json.loads(ledger)["determinism"]["interpreters_required"]
    except (ValueError, KeyError, TypeError):
        out["ledger determinism.interpreters_required"] = None
    return out


def version_problems(lists: dict) -> list:
    """The first list is the script's; every other list must hold the same minors, and the
    script's must be in ascending numeric order (so 3.9 and 3.10 cannot swap by sorting text)."""
    script = lists.get("setup_python.sh VERSIONS")
    if not script:
        return ["setup_python.sh has no VERSIONS list"]
    out = []
    if script != sorted(script, key=version_key):
        out.append(f"setup_python.sh VERSIONS is not in ascending order: {script}")
    for name, got in lists.items():
        if got is None:
            out.append(f"{name}: not found")
        elif sorted(got, key=version_key) != script:
            out.append(f"{name} is {got}, setup_python.sh has {script}")
    return out


def github_slugs(md: str) -> set:
    """The anchors GitHub gives the headings of a Markdown text (outside code fences)."""
    slugs, seen, fenced = set(), {}, False
    for ln in md.split("\n"):
        if ln.startswith("```"):
            fenced = not fenced
            continue
        m = None if fenced else re.match(r"^#{1,6}[ \t]+(.*?)[ \t#]*$", ln)
        if not m:
            continue
        head = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", m.group(1).replace("`", ""))
        slug = re.sub(r"[^\w\- ]", "", head.lower()).replace(" ", "-")
        n = seen.get(slug, 0)
        seen[slug] = n + 1
        slugs.add(slug if n == 0 else f"{slug}-{n}")
    return slugs


def strip_fences(md: str) -> str:
    out, fenced = [], False
    for ln in md.split("\n"):
        if ln.startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append(ln)
    return "\n".join(out)


def readme_link_problems(text: str, root: Path) -> list:
    """Every relative link of the README (Markdown, src, srcset, href) names a file or directory
    of the repository, and an anchor names a heading of the file it points into. Absolute links
    to GitHub must name this repository."""
    body = strip_fences(text)
    targets = re.findall(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", body)
    targets += re.findall(r"""(?:src|srcset|href)=["']([^"']+)["']""", body)
    out = []
    for target in targets:
        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
            continue
        path, _, frag = target.partition("#")
        dest = (root / path) if path else (root / "README.md")
        if not dest.exists():
            out.append(f"{target}: {path} does not exist")
        elif frag and dest.is_file() and dest.suffix == ".md":
            md = text if not path else dest.read_text(encoding="utf-8")
            if frag not in github_slugs(md):
                out.append(f"{target}: no heading with that anchor in {path or 'README.md'}")
    return out


def readme_problems(text: str, versions: list, repo: str, doi: str, root: Path) -> list:
    """What the README's front door must hold: the on-ramp order, the badge row, the make
    targets with their plain commands, the interpreter range, the plain statement that no
    stage 2 results exist yet, the three generated blocks, and links that resolve."""
    out = []
    ramp, _, rest = text.partition("## Quick start")
    if not rest:
        return ["there is no Quick start section"]
    for block in ("status-line", "plan-gantt", "gates-table"):
        if text.count(f"<!-- generated:{block}:start -->") != 1 or text.count(f"<!-- generated:{block}:end -->") != 1:
            out.append(f"the generated block {block} is not placed exactly once")
    if "<!-- generated:status-line:start -->" not in ramp:
        out.append("the status line is not above the Quick start")
    if "No stage 2 results are reported yet" not in ramp:
        out.append("the on-ramp does not say that no stage 2 results are reported yet")
    if "](#quick-start)" not in ramp:
        out.append("the on-ramp does not point to the Quick start")
    if "](#citation)" not in ramp or "](CITATION.cff)" not in ramp:
        out.append("the on-ramp does not point to the Citation section and CITATION.cff")
    if "/discussions)" not in ramp or "](SECURITY.md)" not in ramp:
        out.append("the on-ramp does not say how to get in touch (Discussions, SECURITY.md)")
    intro = ramp.split("Psyche is an open research project", 1)[0]
    badges = re.findall(r"\[!\[([^\]]*)\]\(([^)]+)\)\]\(([^)]+)\)", intro)
    images = len(re.findall(r"!\[", intro))
    if images != 4 or len(badges) != 4:
        out.append(f"the badge row holds {len(badges)} linked badges and {images} images, not 4")
    want = {
        "Tests": (f"https://github.com/{repo}/actions/workflows/tests.yml/badge.svg",
                  f"https://github.com/{repo}/actions/workflows/tests.yml"),
        "Pages": (f"https://github.com/{repo}/actions/workflows/pages.yml/badge.svg",
                  f"https://github.com/{repo}/actions/workflows/pages.yml"),
        "DOI": (f"https://zenodo.org/badge/DOI/{doi}.svg", f"https://doi.org/{doi}"),
        "License: MIT": ("https://img.shields.io/badge/license-MIT-blue.svg", "LICENSE"),
    }
    got = {alt: (img, link) for alt, img, link in badges}
    if got != want:
        out.append(f"the badge row is {got}, not {want}")
    for alt in got:
        if not re.fullmatch(r"[A-Za-z0-9: ]+", alt):
            out.append(f"badge alt text {alt!r} is not plain")
    for wf in ("tests.yml", "pages.yml"):
        if not (root / ".github" / "workflows" / wf).is_file():
            out.append(f"the badge for {wf} has no such workflow")
    for name in ("setup", "test", "check", "capture", "site"):
        if f"`make {name}`" not in text:
            out.append(f"the README does not document make {name}")
    lines = set(text.split("\n"))
    for name in ("test", "check", "capture"):
        for cmd in MAKE_RECIPES[name]:
            if cmd not in lines and f"`{cmd}`" not in text:
                out.append(f"the plain command for make {name} is missing: {cmd}")
    if f"`uv python install {' '.join(versions)}`" not in text:
        out.append("the plain command for make setup (uv python install ...) is missing or differs")
    if "npm ci" not in text or "npm run dev" not in text:
        out.append("the plain commands for make site (npm ci, npm run dev) are missing")
    if f"{versions[0]} to {versions[-1]}" not in text:
        out.append(f"the README does not state the interpreter range {versions[0]} to {versions[-1]}")
    out += readme_link_problems(text, root)
    for slug in re.findall(r"https://github\.com/([^/\s)>]+/[^/\s)>]+)", text):
        if re.sub(r"\.git$", "", slug) != repo:
            out.append(f"a GitHub link names {slug}, not {repo}")
    typed = {re.sub(r"(\.svg)?\.?$", "", d) for d in re.findall(r"\b10\.\d{4,9}/[^\s\"'`<>)\]*]+", text)}
    if typed != {doi}:
        out.append(f"the README types the DOIs {sorted(typed)}, CITATION.cff has {doi}")
    return out


PREREQUISITE_TERMS = ("full clone", "3.9", "SyntaxError", "make setup", "failures on a correct tree")
COUNT_WORD = re.compile(r"\b(?:two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
                        r"(?:commands|items|interpreters|minors|checks|targets|suites|python3)\b", re.I)


def node_minimum(root: Path) -> str:
    """The lowest Node.js that website/package.json allows ('' when it names none)."""
    engines = json.loads((root / "website/package.json").read_text(encoding="utf-8")).get("engines", {}).get("node", "")
    found = re.fullmatch(r">=\s*(\d+(?:\.\d+)*)", engines.strip())
    return found.group(1) if found else ""


def contributor_problems(contributing: str, template: str, readme: str, rules: dict, versions: list, node_min: str) -> list:
    """What the contributor pages must keep in step with the Makefile and each other: every plain
    command of the make targets, the interpreter range, the Node minimum, the prerequisites the
    README states (a full clone, CPython 3.10 or newer, every interpreter for `make test`), and no
    typed count of commands, items or interpreters (which go stale when one is added)."""
    out = []
    c, t, r = " ".join(contributing.split()), " ".join(template.split()), " ".join(readme.split())
    install = f"uv python install {' '.join(versions)}"
    for cmd in rules.get("check", []) + rules.get("test", []) + rules.get("capture", []) + [install]:
        if f"`{cmd}`" not in c:
            out.append(f"CONTRIBUTING.md does not give the plain command {cmd}")
    for cmd in rules.get("check", []) + rules.get("test", []):
        if f"`{cmd}`" not in t:
            out.append(f"the pull request template does not list {cmd}")
    for name in ("setup", "test", "check", "capture", "site"):
        if f"`make {name}`" not in c:
            out.append(f"CONTRIBUTING.md does not document make {name}")
    for name in ("test", "check", "setup"):
        if f"`make {name}`" not in t:
            out.append(f"the pull request template does not name make {name}")
    span = f"{versions[0]} to {versions[-1]}"
    for label, doc in (("CONTRIBUTING.md", c), ("README.md", r), ("the pull request template", t)):
        if span not in doc:
            out.append(f"{label} does not state the interpreter range {span}")
        for found in COUNT_WORD.findall(doc):
            out.append(f"{label} types a count that nothing checks: {found!r}")
    for label, doc in (("CONTRIBUTING.md", c), ("README.md", r)):
        for term in PREREQUISITE_TERMS:
            if term not in doc:
                out.append(f"{label} does not state a prerequisite: {term!r}")
        if "website/.nvmrc" not in doc:
            out.append(f"{label} does not point to website/.nvmrc for the CI Node version")
        if not node_min or node_min not in doc:
            out.append(f"{label} does not state the Node minimum {node_min!r} of website/package.json")
    return out


def bash_candidates() -> list:
    """Every distinct bash on this machine that the script should run under: the one on PATH
    and /bin/bash (on macOS the 3.2 that Apple ships, where an empty array under set -u fails)."""
    found, seen = [], set()
    for cand in (shutil.which("bash"), "/bin/bash"):
        if cand and os.access(cand, os.X_OK) and os.path.realpath(cand) not in seen:
            seen.add(os.path.realpath(cand))
            found.append(cand)
    return found


def setup_world(base: Path, versions: list, *, uv: bool = True, shims: list = None, py3: str = "default",
                reports: dict = None, broken: tuple = ()) -> dict:
    """A directory of stubs: a `uv` that records its arguments in a log, a shim for each python3.X
    named that prints the version it is (or the one `reports` says it is), a shim in `broken` that
    fails the way a version manager's does, and a `python3` that prints `py3` (the newest version by
    default; None for no python3 at all). Returns the pieces a run needs."""
    stubs, home = base / "stubs", base / "home"
    for d in (stubs, home):
        d.mkdir(parents=True, exist_ok=True)
    if uv:
        (stubs / "uv").write_text(UV_STUB, encoding="utf-8")
        (stubs / "uv").chmod(0o755)
    for v in (versions if shims is None else shims):
        if v in broken:
            body = f"#!/bin/sh\necho 'pyenv: python{v}: command not found' >&2\nexit 127\n"
        else:
            body = f"#!/bin/sh\necho {(reports or {}).get(v, v)}\n"
        (stubs / f"python{v}").write_text(body, encoding="utf-8")
        (stubs / f"python{v}").chmod(0o755)
    if py3 == "default":
        py3 = versions[-1]
    if py3 is not None:
        (stubs / "python3").write_text(f"#!/bin/sh\necho {py3}\n", encoding="utf-8")
        (stubs / "python3").chmod(0o755)
    return {"stubs": stubs, "home": home, "log": base / "uv.log", "bin": base / "uvbin"}


def run_setup(bash: str, world: dict, *, path: str = None, extra: dict = None, args: tuple = (),
              script: Path = None) -> tuple:
    env = {"PATH": path if path is not None else str(world["stubs"]), "HOME": str(world["home"]),
           "UV_STUB_LOG": str(world["log"]), "UV_STUB_BIN": str(world["bin"])}
    env.update(extra or {})
    r = subprocess.run([bash, str(script or SETUP_SCRIPT), *args], env=env, capture_output=True, text=True,
                       cwd=str(world["home"]), timeout=120)
    calls = world["log"].read_text(encoding="utf-8").splitlines() if world["log"].exists() else []
    return r.returncode, r.stdout, r.stderr, calls


def moved_status(readme: str) -> str:
    """The README with its generated status-line block moved from the on-ramp to just under the
    Quick start heading."""
    m = re.search(r"<!-- generated:status-line:start -->.*?<!-- generated:status-line:end -->\n", readme, re.S)
    if m is None:
        return readme
    return readme.replace(m.group(0), "", 1).replace("## Quick start\n", "## Quick start\n" + m.group(0), 1)


def test_front_door(tmp: Path) -> None:
    section("front door: the Makefile, tools/setup_python.sh and the README's quick start")
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    problems = makefile_problems(makefile)
    check(problems == [], f"the Makefile has the six fixed targets, each .PHONY, each recipe the fixed commands: {problems}")
    rules, _, _, _ = parse_makefile(makefile)
    check(list(rules) == list(MAKE_TARGETS), f"and `make` alone runs help, the first target: {list(rules)}")
    attributes = (REPO / ".gitattributes").read_text(encoding="utf-8").split("\n") if (REPO / ".gitattributes").exists() else []
    check("*.sh text eol=lf" in attributes and "Makefile text eol=lf" in attributes,
          ".gitattributes pins *.sh and the Makefile to LF line endings")
    mutants = {
        "a command left out of make check": makefile.replace("\tpython3 tools/publish/check_copy.py\n", ""),
        "a command reordered in make check": makefile.replace(
            "\tpython3 tools/publish/ci_c2.py\n\tpython3 tools/publish/check_copy.py\n",
            "\tpython3 tools/publish/check_copy.py\n\tpython3 tools/publish/ci_c2.py\n"),
        "a target missing from .PHONY": makefile.replace(".PHONY: help setup test check capture site",
                                                         ".PHONY: help setup test check capture"),
        "a seventh target": makefile + "\nlint:\n\tpython3 tools/lint.py\n",
        "python instead of python3": makefile.replace("\tpython3 run_tests.py", "\tpython run_tests.py"),
        "a recipe behind a prerequisite": makefile.replace("test:\n", "test: check\n"),
        "help in second place": makefile.replace(".DEFAULT_GOAL := help\n\n", "").replace(
            "setup:\n\tbash tools/setup_python.sh\n\n", "").replace(
            "help:\n", "setup:\n\tbash tools/setup_python.sh\n\nhelp:\n", 1),
        "another default goal": makefile.replace(".DEFAULT_GOAL := help", ".DEFAULT_GOAL := test"),
        "help that runs a command": makefile.replace("\t@echo \"\"\n", "\tpython3 run_tests.py\n"),
        "a target left out of help": makefile.replace("\t@echo \"  make setup", "\t@echo \"  (setup", 1),
        "a site that skips npm ci": makefile.replace("\tcd website && npm ci\n", ""),
        "a minus before a command (make carries on after a failure)": makefile.replace(
            "\tpython3 tools/publish/ci_c2.py\n", "\t-python3 tools/publish/ci_c2.py\n"),
        "MAKEFLAGS set to keep going": makefile.replace(".DEFAULT_GOAL := help\n", ".DEFAULT_GOAL := help\nMAKEFLAGS += -k\n"),
        "another SHELL": makefile.replace(".DEFAULT_GOAL := help\n", ".DEFAULT_GOAL := help\nSHELL := /bin/false\n"),
        "another .SHELLFLAGS": makefile.replace(".DEFAULT_GOAL := help\n", ".DEFAULT_GOAL := help\n.SHELLFLAGS := -c\n"),
        "an exported PATH": makefile.replace(".DEFAULT_GOAL := help\n", ".DEFAULT_GOAL := help\nexport PATH := /nowhere:$(PATH)\n"),
        "an include of a missing file": makefile.replace(".DEFAULT_GOAL := help\n", ".DEFAULT_GOAL := help\n-include missing.mk\n"),
        "a line that is no make at all": makefile.replace("\ncheck:\n", "\noops this is not make\ncheck:\n"),
    }
    for label, text in mutants.items():
        check(text != makefile, f"(the mutation '{label}' changes the file)")
        check(makefile_problems(text) != [], f"the check refuses a Makefile with {label}")
    check(parse_makefile("a:\n\t@echo x \\\n\t  y\n")[0] == {"a": ["echo x y"]},
          "the recipe reader joins a continuation and drops the @ prefix")
    check(parse_makefile("a:\n\t-echo x\n")[0] == {"a": ["-echo x"]},
          "and keeps a - prefix in the recipe text, so the guard sees it")
    check(makefile_stray_lines(makefile) == [] and makefile_stray_lines("a:\n\t@echo x\nCC = cc\n") == ["CC = cc"],
          "the real Makefile holds nothing but comments, .PHONY, .DEFAULT_GOAL, rules and recipe lines, and a variable is seen")

    script = SETUP_SCRIPT.read_text(encoding="utf-8")
    code = "\n".join(ln for ln in script.split("\n") if not ln.lstrip().startswith("#"))
    check(script.startswith("#!/usr/bin/env bash\n") and "\nset -euo pipefail\n" in script,
          "the script is bash and stops on the first error (set -euo pipefail)")
    check(os.access(SETUP_SCRIPT, os.X_OK), "the script is executable")
    check(re.search(r"\b(sudo|curl|wget|eval)\b|\|\s*(ba)?sh\b", code) is None,
          "the script uses no sudo, downloads nothing and pipes nothing into a shell")
    check(f'UV_DOCS_URL="{UV_DOCS_URL}"' in script, "the script names the uv installation documentation")

    lists = interpreter_lists(script, (REPO / ".github/workflows/tests.yml").read_text(encoding="utf-8"),
                              (REPO / "tools/capture_run.py").read_text(encoding="utf-8"),
                              (REPO / "tools/ledger.json").read_text(encoding="utf-8"))
    problems = version_problems(lists)
    check(problems == [], f"setup_python.sh, the CI matrix (and its install and PATH steps), capture_run.py and the "
                          f"ledger keep one list of interpreters: {problems}")
    versions = lists["setup_python.sh VERSIONS"] or []
    check(len(versions) >= 2 and all(re.fullmatch(r"3\.\d+", v) for v in versions), f"and it is a list of 3.X minors: {versions}")
    workflow_text = (REPO / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    capture_text = (REPO / "tools/capture_run.py").read_text(encoding="utf-8")
    ledger_text = (REPO / "tools/ledger.json").read_text(encoding="utf-8")
    drift = [
        ("a version only in the script", "script", "3.14)", "3.14 3.15)"),
        ("a version missing from the script", "script", "3.11 ", ""),
        ("a script list out of order", "script", "(3.10 3.11", "(3.11 3.10"),
        ("a version only in the CI matrix", "workflow", '"3.14"]', '"3.14", "3.15"]'),
        ("a version missing from the CI install step", "workflow", "            3.12\n", ""),
        ("a version missing from the CI PATH check", "workflow",
         "for v in 3.10 3.11 3.12 3.13 3.14; do", "for v in 3.10 3.11 3.13 3.14; do"),
        ("a version missing from capture_run.py", "capture", '"python3.12", ', ""),
    ]
    for label, which, old, new in drift:
        texts = {"script": script, "workflow": workflow_text, "capture": capture_text}
        mutated = texts[which].replace(old, new)
        check(mutated != texts[which], f"(the mutation '{label}' changes {which})")
        texts[which] = mutated
        check(version_problems(interpreter_lists(texts["script"], texts["workflow"], texts["capture"], ledger_text)) != [],
              f"the check refuses {label}")
    plan_ledger = json.loads(ledger_text)
    plan_ledger["determinism"]["interpreters_required"].append("3.15")
    check(version_problems(interpreter_lists(script, workflow_text, capture_text, json.dumps(plan_ledger))) != [],
          "the check refuses a ledger that requires another interpreter")
    check(version_problems(interpreter_lists(script, workflow_text, capture_text, '{"determinism": {}}')) != [],
          "and a ledger without interpreters_required")

    bashes = [] if os.name == "nt" else bash_candidates()
    if not bashes:
        note("no bash on this machine (or Windows): the script itself is not run")
    for n, b in enumerate(bashes):
        tag = str(n)
        r = subprocess.run([b, "-n", str(SETUP_SCRIPT)], capture_output=True, text=True)
        check(r.returncode == 0, f"bash -n tools/setup_python.sh passes under {b}: {r.stderr.strip()}")
        install = "python install " + " ".join(versions)
        base = tmp / f"setup-ok-{tag}"
        world = setup_world(base, versions)
        rc, out, err, calls = run_setup(b, world)
        check(rc == 0 and err == "", f"{b}: with uv and every python3.X present the script exits 0 quietly ({rc}) {err}")
        check(calls == [install], f"{b}: it calls exactly 'uv {install}': {calls}")
        shown = out.strip().split("\n")
        check(all(f"python{v}  {world['stubs']}/python{v}" in shown for v in versions)
              and f"python3  {world['stubs']}/python3  reports {versions[-1]}" in shown and len(shown) == len(versions) + 2,
              f"{b}: it prints one line per version with where it resolves, the line for python3, and a closing line: {shown}")
        rc2, out2, err2, calls2 = run_setup(b, world)
        check((rc2, out2, err2) == (rc, out, err) and calls2 == [install, install],
              f"{b}: a second run does the same (it is safe to repeat): {calls2}")

        base = tmp / f"setup-missing-{tag}"
        world = setup_world(base, versions, shims=[v for v in versions if v != "3.12"])
        rc, out, err, calls = run_setup(b, world)
        check(rc != 0 and "python3.12  not found on PATH" in out and "python3.11  " + str(world["stubs"]) in out,
              f"{b}: a version that does not resolve is reported as missing and the others as found: {rc} {out!r}")
        check("not found on PATH: python3.12" in err and str(world["bin"]) in err and "export PATH=" in err,
              f"{b}: it prints the directory to add to PATH, from 'uv python dir --bin': {err!r}")
        check(calls == [install, "python dir --bin"], f"{b}: it asks uv for the executable directory: {calls}")
        rc, out, err, calls = run_setup(b, world, path=f"{world['stubs']}:{world['bin']}")
        check(rc != 0 and "export PATH=" not in err and str(world["bin"]) in err,
              f"{b}: with that directory already on PATH it does not tell the reader to add it again: {err!r}")
        rc, out, err, calls = run_setup(b, world, extra={"UV_STUB_NO_BIN_FLAG": "1"})
        check(rc != 0 and f"{world['home']}/.local/bin" in err,
              f"{b}: a uv without 'python dir --bin' falls back to ~/.local/bin: {err!r}")

        floor, top = versions[0], versions[-1]
        for k, (label, kwargs, needs) in enumerate((
            ("a python3.X on PATH that does not run (a version manager's shim)", {"broken": ("3.12",)},
             ("python3.12  ", "does not run as 3.12", "found on PATH but not running as the right version: python3.12")),
            ("a python3.X on PATH that is another version", {"reports": {"3.12": "3.11"}},
             ("does not run as 3.12 (it reports: 3.11)",)),
        )):
            world = setup_world(tmp / f"setup-shim-{k}-{tag}", versions, **kwargs)
            rc, out, err, calls = run_setup(b, world)
            check(rc == 1 and all(x in out + err for x in needs) and "setup_python: every interpreter" not in out,
                  f"{b}: {label} is reported, not counted as found, and the script exits 1: {rc} {out!r} {err!r}")
        for k, (label, py3, ok) in enumerate((("at the lowest version", floor, True), ("at the newest version", top, True),
                                              ("below the lowest version (3.9 against 3.10 is numeric, not text)", "3.9", False),
                                              ("far below it", "2.7", False), ("that prints nothing", "", False),
                                              ("that is absent", None, False))):
            world = setup_world(tmp / f"setup-py3-{k}-{tag}", versions, py3=py3)
            rc, out, err, calls = run_setup(b, world)
            if ok:
                check(rc == 0 and err == "" and f"reports {py3}." in out and calls == [install],
                      f"{b}: a python3 {label} passes: {rc} {out!r} {err!r}")
            else:
                check(rc == 1 and "make runs python3" in err and f"{floor} or newer" in err and "ln -s" in err
                      and "setup_python: every interpreter" not in out and "export PATH=" not in err,
                      f"{b}: a python3 {label} fails, says make runs python3, and says what to do: {rc} {out!r} {err!r}")
        world = setup_world(tmp / f"setup-py3-and-missing-{tag}", versions, shims=[v for v in versions if v != "3.12"], py3="3.9")
        rc, out, err, calls = run_setup(b, world)
        check(rc == 1 and "not found on PATH: python3.12" in err and "make runs python3" in err,
              f"{b}: a missing version and an old python3 are both reported in one run: {rc} {err!r}")

        for k, (label, old, new, kwargs, wrong) in enumerate((
            ("python3 is never checked", 'if [ "${new_enough}" -eq 1 ]; then', "if true; then", {"py3": "3.9"},
             lambda rc, out, err: rc == 0),
            ("a shim is trusted by its name", 'if [ "${got}" = "${v}" ]; then', "if true; then", {"broken": ("3.12",)},
             lambda rc, out, err: rc == 0),
            ("the versions are compared as text", '[ "${got#*.}" -ge "${floor#*.}" ]', '[[ "${got#*.}" > "${floor#*.}" || "${got#*.}" == "${floor#*.}" ]]',
             {"py3": "3.9"}, lambda rc, out, err: rc == 0),
        )):
            check(old in script, f"(the mutation '{label}' finds its text in the script)")
            mutant = tmp / f"setup-mutant-{k}-{tag}.sh"
            mutant.write_text(script.replace(old, new), encoding="utf-8")
            world = setup_world(tmp / f"setup-mutant-world-{k}-{tag}", versions, **kwargs)
            rc, out, err, calls = run_setup(b, world, script=mutant)
            check(wrong(rc, out, err), f"{b}: (the run is able to fail: a script where {label} is seen: {rc} {err!r})")

        base = tmp / f"setup-fail-{tag}"
        world = setup_world(base, versions)
        rc, out, err, calls = run_setup(b, world, extra={"UV_STUB_INSTALL_RC": "3"})
        check(rc != 0 and out == "" and calls == [install] and "failed" in err,
              f"{b}: when uv python install fails the script fails, reports no interpreter and says why: {rc} {out!r} {err!r}")

        base = tmp / f"setup-nouv-{tag}"
        world = setup_world(base, versions, uv=False)
        empty = base / "empty"
        empty.mkdir()
        rc, out, err, calls = run_setup(b, world, path=str(empty))
        check(rc == 1 and UV_DOCS_URL in err and calls == [] and out == "",
              f"{b}: without uv on PATH it exits 1, names the documentation link and runs nothing: {rc} {err!r}")
        rc, out, err, calls = run_setup(b, world, path=str(world["stubs"]))
        check(rc == 1 and UV_DOCS_URL in err and calls == [],
              f"{b}: with python3.X shims but no uv it still stops at the missing uv: {rc}")
        base = tmp / f"setup-args-{tag}"
        world = setup_world(base, versions)
        rc, out, err, calls = run_setup(b, world, args=("--dry-run",))
        check(rc == 2 and calls == [], f"{b}: an argument is refused before anything runs, not ignored: {rc} {calls}")
        mutated = tmp / f"setup-mutated-{tag}.sh"
        mutated.write_text(script.replace("uv python install \"${VERSIONS[@]}\"", "uv python install"), encoding="utf-8")
        world = setup_world(tmp / f"setup-mut-{tag}", versions)
        env = {"PATH": str(world["stubs"]), "HOME": str(world["home"]), "UV_STUB_LOG": str(world["log"]),
               "UV_STUB_BIN": str(world["bin"])}
        subprocess.run([b, str(mutated)], env=env, capture_output=True, text=True, cwd=str(world["home"]))
        got = world["log"].read_text(encoding="utf-8").splitlines() if world["log"].exists() else []
        check(got != ["python install " + " ".join(versions)],
              f"{b}: (the run is able to fail: a script that installs no versions is seen as one: {got})")

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    manifest = core.load_manifest(REPO)
    doi = cited_doi()
    problems = readme_problems(readme, versions, manifest["repo"], doi, REPO)
    check(problems == [], f"the README has the on-ramp, the badge row, the make targets with their plain commands, "
                          f"the interpreter range and links that resolve: {problems}")
    rmut = {
        "a missing badge": readme.replace("[![Pages]", "[!["),
        "a badge pointing at another workflow": readme.replace("workflows/pages.yml", "workflows/other.yml"),
        "the status line below the Quick start": moved_status(readme),
        "no statement that stage 2 has no results yet": readme.replace("No stage 2 results are reported yet", "Results follow"),
        "no make check": readme.replace("`make check`", "`make verify`"),
        "a missing plain command": readme.replace("python3 tools/publish/check_copy.py\n", ""),
        "a different uv command": readme.replace("uv python install 3.10 ", "uv python install 3.11 "),
        "a different interpreter range": readme.replace("3.10 to 3.14", "3.9 to 3.14"),
        "a dead relative link": readme.replace("docs/guide.md", "docs/no-such-page.md", 1),
        "a dead anchor": readme.replace("](#citation)", "](#nowhere)", 1),
        "a missing image": readme.replace("brand/psyche-wordmark-dark.svg", "brand/missing.svg"),
        "another repository": readme.replace("cagancaliskan/psyche/discussions", "someone/else/discussions"),
        "another DOI": readme.replace("zenodo.20474613>", "zenodo.20474614>", 1),
        "a deleted generated block": readme.replace("<!-- generated:gates-table:end -->", ""),
        "no pointer to the Quick start in the on-ramp": readme.replace("[Quick start](#quick-start)", "Quick start", 1),
    }
    for label, text in rmut.items():
        check(text != readme, f"(the mutation '{label}' changes the README)")
        check(readme_problems(text, versions, manifest["repo"], doi, REPO) != [], f"the README check refuses {label}")
    contributing = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    template = (REPO / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    node_min = node_minimum(REPO)
    check(re.fullmatch(r"\d+(\.\d+)+", node_min) is not None, f"website/package.json names a Node minimum: {node_min!r}")
    problems = contributor_problems(contributing, template, readme, rules, versions, node_min)
    check(problems == [], f"CONTRIBUTING.md, the pull request template and the README agree with the Makefile "
                          f"(commands, range, Node minimum, prerequisites, no typed counts): {problems}")
    cmut = {
        "a make check command missing from CONTRIBUTING.md": (
            contributing.replace("`python3 tools/publish/diagrams.py --check`", "`python3 tools/publish/diagrams.py`"), template, readme),
        "a make check command missing from the template": (
            contributing, template.replace("`python3 tools/publish/diagrams.py --check`", "`python3 tools/publish/diagrams.py`"), readme),
        "no run_tests in the template": (contributing, template.replace("python3 run_tests.py", "pytest"), readme),
        "fewer interpreters described as a smaller run": (
            contributing.replace("failures on a correct tree", "fewer interpreters than CI"), template, readme),
        "no mention of a full clone": (re.sub(r"full\s+clone", "clone", contributing), template, readme),
        "no mention of Python 3.9": (contributing.replace("Python 3.9", "Python 3.8"), template, readme),
        "another Node minimum": (contributing.replace(node_min, "20.0.0"), template, readme),
        "another Node minimum in the README": (contributing, template, readme.replace(node_min, "20.0.0")),
        "a typed count of interpreters": (contributing + "\nAll five interpreters.\n", template, readme),
        "a typed count of commands": (contributing, template, readme.replace("the commands below", "the eight commands below")),
        "a typed count of items": (contributing, template.replace("down to the tool suites", "the first six items"), readme),
        "another range in the template": (contributing, template.replace("3.10 to 3.14", "3.9 to 3.14"), readme),
        "make capture undocumented": (contributing.replace("`make capture`", "`make snapshot`"), template, readme),
    }
    for label, (c_text, t_text, r_text) in cmut.items():
        check((c_text, t_text, r_text) != (contributing, template, readme), f"(the mutation '{label}' changes a page)")
        check(contributor_problems(c_text, t_text, r_text, rules, versions, node_min) != [],
              f"the contributor pages check refuses {label}")
    check(github_slugs("# A b\n## C: d `e`\n## C: d `e`\n```\n# not a heading\n```\n") == {"a-b", "c-d-e", "c-d-e-1"},
          "the anchor reader follows GitHub: lower case, punctuation dropped, a repeat numbered, code skipped")


def sidebar_titles(manifest: dict) -> dict:
    """slug -> title as the stager takes it: the manifest's override or the first heading."""
    titles = {}
    for page in core.manifest_pages(manifest):
        text = (REPO / page["src"]).read_text(encoding="utf-8")
        titles[page["slug"]] = page.get("title") or stage.split_title(text, page["src"])[0]
    return titles


def test_stage_sidebar() -> None:
    section("sidebar: one first group, Start here, with the manifest's section of that title after Home")
    manifest = core.load_manifest(REPO)
    titles = sidebar_titles(manifest)
    sidebar = stage.build_sidebar(manifest, titles)
    labels = [g["label"] for g in sidebar]
    start = next(s for s in manifest["sections"] if s["title"] == stage.START_GROUP)
    others = [s["title"] for s in manifest["sections"] if s is not start]
    check(labels == [stage.START_GROUP] + others and sum(x.casefold() == "start here" for x in labels) == 1,
          f"the first group is Start here, the others follow in manifest order, and none repeats it: {labels}")
    items = sidebar[0]["items"]
    custom = [{"label": label, "link": "/" + path} for label, path in stage.CUSTOM_PAGES]
    docs = [{"label": titles[pg["slug"]], "slug": pg["slug"]} for pg in start["pages"]]
    check(items == custom[:1] + docs + custom[1:] and items[0] == {"label": "Home", "link": "/"},
          "Home first, then the manifest's Start here pages in manifest order, then the other hand-written pages")
    check(len(docs) >= 4 and len({i["label"].casefold() for i in items}) == len(items),
          "no two entries of the first group share a label")
    in_groups = [i["slug"] for g in sidebar for i in g["items"] if "slug" in i]
    check(in_groups == [pg["slug"] for pg in core.manifest_pages(manifest)],
          "every published page is in the sidebar once, in manifest order")
    check([i["link"] for g in sidebar for i in g["items"] if "link" in i] == ["/" + path for _, path in stage.CUSTOM_PAGES],
          "the hand-written pages are in the sidebar once")
    check(manifest["sections"][0]["title"] == stage.START_GROUP and stage.START_GROUP == "Start here",
          "the manifest's first section is the Start here section")

    pg = lambda n: {"src": f"docs/{n}.md", "slug": n, "wiki": n.capitalize()}  # noqa: E731
    fx = {"sections": [{"title": "Alpha", "pages": [pg("a1"), pg("a2")]},
                       {"title": "Start here", "pages": [pg("s1"), pg("s2")]},
                       {"title": "Beta", "pages": [pg("b1")]}]}
    fx_titles = {n: n.upper() for n in ("a1", "a2", "s1", "s2", "b1")}
    got = stage.build_sidebar(fx, fx_titles)
    check([g["label"] for g in got] == ["Start here", "Alpha", "Beta"]
          and [i["label"] for i in got[0]["items"]][:3] == ["Home", "S1", "S2"]
          and [i["label"] for i in got[1]["items"]] == ["A1", "A2"],
          "the section is moved to the front wherever the manifest lists it, its pages in their order")
    none = stage.build_sidebar({"sections": [{"title": "Alpha", "pages": [pg("a1")]}]}, {"a1": "A1"})
    check([g["label"] for g in none] == ["Start here", "Alpha"] and none[0]["items"] == custom,
          "without such a section the first group is the hand-written pages alone")
    for odd in ("start here", "START HERE", "Start Here"):
        try:
            stage.build_sidebar({"sections": [{"title": odd, "pages": [pg("s1")]}]}, {"s1": "S1"})
            check(False, f"a section titled {odd!r} is refused")
        except core.PublishError as e:
            check("differs from" in str(e), f"a section titled {odd!r} is refused: it would be a second group of that name")
    m = copy.deepcopy(GUARD_MANIFEST)
    m["sections"].append({"title": "FIXTURE", "pages": [dict(m["sections"][0]["pages"][0], src="docs/o2.md",
                                                           slug="o2", wiki="O2", description=SECOND_DESCRIPTION)]})
    check(has(core.manifest_problems(m), "is the title of another section too"),
          "two sections with one title (in any case) are a manifest problem")


def test_stage_progress(tmp: Path) -> None:
    section("stage: the progress data, the author and the sidebar are staged from the commit")
    if not GIT:
        check(False, "git is required for the stage tests and was not found")
        return
    manifest = copy.deepcopy(GUARD_MANIFEST)
    manifest["sections"].insert(0, {"title": stage.START_GROUP, "pages": [
        {"src": "docs/start.md", "slug": "start", "wiki": "Start", "description": SECOND_DESCRIPTION}]})
    p = events_plan()
    root, _, _ = diagram_fixture(tmp, manifest=manifest, research_plan=p,
                                 extra={"docs/start.md": "# The start\n\nA page.\n"})
    res = stage.stage_site(root, "HEAD")
    data = root / "website/src/data"
    progress = json.loads((data / "progress.json").read_text(encoding="utf-8"))
    check(progress == {"as_of": p["as_of"], "timezone": p["timezone"], "author": "Ada Example",
                       "events": RP.progress_events(p)} and res["events"] == 7,
          "progress.json holds the events of the committed plan, its day and zone, and the citation file's author")
    side = json.loads((data / "sidebar.json").read_text(encoding="utf-8"))
    check([g["label"] for g in side] == ["Start here", "Fixture"]
          and [i["label"] for i in side[0]["items"]][:2] == ["Home", "The start"]
          and side[0]["items"][1] == {"label": "The start", "slug": "start"},
          "the staged sidebar has one Start here group, with the manifest's page after Home")
    first = (data / "progress.json").read_bytes()
    stage.stage_site(root, "HEAD")
    check((data / "progress.json").read_bytes() == first, "staging twice writes the same bytes")
    rc, out, err = capture(stage.main, ["--target", "site", "--root", str(root)])
    check(rc == 0 and "7 progress event(s)" in out, f"the command line says how many events: {out.strip()}")
    kinds = {e["kind"] for e in progress["events"]}
    check(kinds == set(RP.EVENT_KINDS), "(every kind of event reached the file)")
    check(not any(k in json.dumps(progress) for k in ("Is it new?", "Reposition.", GOOD_SHA256)),
          "no gate question, fallback or hash reached the file")
    reasoned = events_plan()
    reasoned["changelog"].append({"date": "2026-11-17", "item": "P1", "field": "status", "from": "planned",
                                  "to": "active", "reason": "REASON-SENTINEL", "ref": "fixture"})
    root3, _, _ = diagram_fixture(tmp, manifest=manifest, research_plan=reasoned,
                                  extra={"docs/start.md": "# The start\n\nA page.\n"})
    stage.stage_site(root3, "HEAD")
    check("REASON-SENTINEL" not in (root3 / "website/src/data/progress.json").read_text(encoding="utf-8"),
          "the reason of a change of status does not reach the staged file either")

    # the commit is what is staged: the citation file, like the plan, must not differ from it
    write(root, "CITATION.cff", FIXTURE_CITATION.replace("Ada", "Eve"))
    try:
        stage.stage_site(root, "HEAD")
        check(False, "a citation file that differs from the commit stops staging")
    except core.PublishError as e:
        check("citation file" in str(e), "a citation file that differs from the commit stops staging")
    git_ok(root, "checkout", "-q", "--", "CITATION.cff")
    write(root, "CITATION.cff", "cff-version: 1.2.0\ntitle: x\n")
    git_ok(root, "add", "--", "CITATION.cff")
    git_ok(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q",
           "--no-verify", "-m", "fixture citation without authors")
    rc, out, err = capture(stage.main, ["--target", "site", "--root", str(root)])
    check(rc == 1 and "authors" in err, "a citation file with no authors stops staging, saying so")
    # a plan with no event stages an empty list, dated by the plan
    root2, _, _ = diagram_fixture(tmp, research_plan=dict(plan(), phases=[dict(ph, status="planned")
                                                                       for ph in plan()["phases"]]))
    stage.stage_site(root2, "HEAD")
    quiet = json.loads((root2 / "website/src/data/progress.json").read_text(encoding="utf-8"))
    check(quiet["events"] == [] and quiet["as_of"] == "2026-10-23", "a plan with nothing yet stages no event")


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
        test_og(tmp)
        test_diagrams(tmp)
        test_diagrams_repo(tmp)
        test_stage_diagrams(tmp)
        test_stage_sidebar_labels()
        test_progress_events()
        test_progress_log()
        test_citation_author()
        test_cited_doi()
        test_front_door(tmp)
        test_stage_sidebar()
        test_stage_progress(tmp)
        test_source_hygiene()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nRESULT: {PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
