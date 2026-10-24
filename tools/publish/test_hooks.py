#!/usr/bin/env python3
"""test_hooks.py - suite for the governance hooks in tools/hooks/ (D-031).

Uses the project's own harness convention: no pytest, prints
`RESULT: N passed, M failed`, exits non-zero on any failure. Run as a script.

    python3 tools/publish/test_hooks.py

Each hook is run as Claude Code runs it: a fresh interpreter, a synthetic JSON event on
stdin, and the verdict read from the exit code (2 blocks, 0 allows). The hooks never write
to the target path, so no event here touches a real file; the throwaway repositories live in
a temp directory.

Every string this suite feeds the guards as "forbidden" is assembled from escapes or parts,
so this file itself carries no Turkish letter, private identifier or private marker.
"""

from __future__ import annotations

import datetime as _dt
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
HOOKS = REPO / "tools" / "hooks"
BOUNDARY = HOOKS / "guard_public_boundary.py"
TESTER = HOOKS / "guard_tester_lane.py"
SESSION = HOOKS / "session_start_ledger.py"

# assembled, never literal (see the module docstring)
S_CEDILLA = "\u015f"
DOTLESS_I = "\u0131"
DOTTED_CAP_I = "\u0130"
G_BREVE = "\u011f"
TURKISH_WORD = "ba" + S_CEDILLA + "ar" + DOTLESS_I                 # an ordinary Turkish word
DIR_NFC = DOTTED_CAP_I + S_CEDILLA + "ler"                          # a directory like the real one
E_ID = "E" + "-07"
ADR_ID = "ADR" + "-012"
Q_IDS = ("Q-" + "ADM" + "-3", "Q-" + "M" + "-12", "Q-" + "E" + "-1")
MARKER = "scm" + ":" + "private"
A_CIRCUMFLEX = "\u00e2"

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


def run_hook(script: Path, stdin, *, env_extra=None, cwd=None):
    """Run a hook as Claude Code does. Returns (exit code, stdout, stderr).

    The event goes in as raw UTF-8 with non-ASCII characters unescaped, as Claude Code's
    JSON.stringify sends it, whatever locale the hook itself runs under."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDE_PROJECT_DIR", "PYTHONIOENCODING", "PYTHONUTF8")}
    env.update(env_extra or {})
    data = stdin if isinstance(stdin, str) else json.dumps(stdin, ensure_ascii=False)
    try:
        r = subprocess.run([sys.executable, "-B", str(script)], input=data.encode("utf-8"),
                           capture_output=True, timeout=60, env=env,
                           cwd=str(cwd) if cwd else None)
    except subprocess.TimeoutExpired:
        # Claude Code would kill the hook and let the call through: report it as a failure
        return 124, "", "hook timed out after 60 s"
    return (r.returncode, r.stdout.decode("utf-8", "replace"),
            r.stderr.decode("utf-8", "replace"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def event(tool: str, cwd: Path | str, **tool_input) -> dict:
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "cwd": str(cwd),
            "tool_input": tool_input}


def make_repo(tmp: Path, name: str, *, marker: bool = True) -> Path:
    root = tmp / name
    (root / "tools").mkdir(parents=True)
    if marker:
        (root / "tools" / "ledger.json").write_text("{}\n", encoding="utf-8")
    return root


# -----------------------------------------------------------------------------
# guard_public_boundary.py
# -----------------------------------------------------------------------------

def test_boundary(tmp: Path) -> None:
    section("guard_public_boundary: forbidden text in English-only paths is blocked")
    r = make_repo(tmp, "repo-boundary")

    rc, _, err = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "docs/thesis/x.md"),
                                          content=f"An overview.\nThe {TURKISH_WORD} line.\n"))
    check(rc == 2, f"a Turkish letter in docs/thesis/ is blocked (exit {rc})")
    check("Turkish letter" in err and "line 2" in err,
          f"the message names the finding and its line: {err!r}")

    rc, _, err = run_hook(BOUNDARY, event("Edit", r, file_path=str(r / "README.md"),
                                          old_string="x", new_string=f"see {E_ID} for detail"))
    check(rc == 2, f"an E-id in README.md (Edit new_string) is blocked (exit {rc})")
    check(E_ID in err, "the message names the identifier")

    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "MOC.md"),
                                        content=f"note <!-- {MARKER} -->\n"))
    check(rc == 2, f"the private marker in MOC.md is blocked (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "MOC.md"),
                                        content=f"note {MARKER.upper()}\n"))
    check(rc == 2, f"the marker is matched case-insensitively (exit {rc})")

    for qid in Q_IDS:
        rc, _, _ = run_hook(BOUNDARY, event(
            "Write", r, file_path=str(r / "tools/thesis_plan.json"),
            content=json.dumps({"note": f"tracks {qid}"})))
        check(rc == 2, f"question id {qid} in tools/thesis_plan.json is blocked (exit {rc})")

    rc, _, err = run_hook(BOUNDARY, event(
        "MultiEdit", r, file_path=str(r / "docs/PSYCHE.md"),
        edits=[{"old_string": "a", "new_string": "clean English"},
               {"old_string": "b", "new_string": f"as {ADR_ID} decided"}]))
    check(rc == 2, f"an ADR id in the SECOND MultiEdit edit is blocked (exit {rc})")
    check("edit 2" in err, f"the message says which edit: {err!r}")

    rc, _, _ = run_hook(BOUNDARY, event(
        "NotebookEdit", r, notebook_path=str(r / "website/src/demo.ipynb"),
        new_source=f"# {G_BREVE}\n"))
    check(rc == 2, f"NotebookEdit new_source under website/src/ is checked (exit {rc})")

    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "thesis/README.md"),
                                        content=f"{DOTTED_CAP_I}stanbul\n"))
    check(rc == 2, f"thesis/** is English-only too (exit {rc})")

    # only a letter that HAS a decomposition: s-cedilla is s + U+0327 under NFD
    decomposed = unicodedata.normalize("NFD", "ba" + S_CEDILLA + "ka")
    check(decomposed.isascii() is False and S_CEDILLA not in decomposed,
          "the decomposed probe really is decomposed")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "docs/thesis/y.md"),
                                        content=decomposed))
    check(rc == 2, f"a decomposed (NFD) Turkish letter is still caught (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "docs/thesis/y.md"),
                                        content=DOTTED_CAP_I.lower()))
    check(rc == 2, f"i + COMBINING DOT ABOVE is caught (exit {rc})")

    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path="docs/thesis/rel.md",
                                        content=TURKISH_WORD))
    check(rc == 2, f"a relative file_path is resolved against cwd (exit {rc})")

    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "Readme.md"),
                                        content=E_ID))
    check(rc == 2, f"path case is folded (Readme.md is README.md on this filesystem) "
                   f"(exit {rc})")

    section("guard_public_boundary: thesis/src/ and thesis/tests/ are export-only")
    for rel in ("thesis/src/scm/envs.py", "thesis/tests/test_battery.py"):
        rc, _, err = run_hook(BOUNDARY, event("Write", r, file_path=str(r / rel),
                                              content="x = 1\n"))
        check(rc == 2, f"clean content under {rel} is still blocked (exit {rc})")
        check("export-only" in err, "the message says export-only")
    rc, _, _ = run_hook(BOUNDARY, event("Edit", r, file_path=str(r / "thesis/src/a.py"),
                                        old_string="x", new_string=""))
    check(rc == 2, f"a deleting Edit under thesis/src/ is blocked (exit {rc})")

    section("guard_public_boundary: what it must allow")
    rc, _, err = run_hook(BOUNDARY, event(
        "Write", r, file_path=str(r / "README.md"),
        content="# Thesis\n\nA plain English summary. Tolerance 1E-12; TYPE-12; E-mail.\n"))
    check(rc == 0, f"clean English in README.md is allowed, with no false positive on "
                   f"1E-12 / TYPE-12 (exit {rc}, {err!r})")
    for rel in ("docs/specs/notes.md", "docs/diagrams/README.md", "tests/test_x.py"):
        rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / rel),
                                            content=f"{TURKISH_WORD} {E_ID} {MARKER}"))
        check(rc == 0, f"a path outside both sets ({rel}) is not judged (exit {rc})")

    section("guard_public_boundary: the rest of leak_check's English-only set (Turkish only)")
    for rel in ("CLAUDE.md", "website/astro.config.mjs", "website/package.json",
                "tools/publish/x.py", ".github/workflows/governance.yml"):
        rc, _, err = run_hook(BOUNDARY, event("Write", r, file_path=str(r / rel),
                                              content=f"# {TURKISH_WORD}\n"))
        check(rc == 2 and "English-only" in err,
              f"a Turkish letter in {rel} is blocked at write time, as at push (exit {rc})")
        rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / rel),
                                            content=f"{E_ID} {MARKER}\n"))
        check(rc == 0, f"ids and the marker in {rel} are left to the push-time check "
                       f"(exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "tools/publish/y.py"),
                                        content='LETTER = "\\u015f"\n'))
    check(rc == 0, f"a \\u escape in tools/publish/ source is not decoded (detection "
                   f"patterns are written that way) (exit {rc})")
    other = tmp / "elsewhere"
    other.mkdir()
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(other / "README.md"),
                                        content=TURKISH_WORD))
    check(rc == 0, f"a README.md outside the repository is not judged (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Edit", r, file_path=str(r / "README.md"),
                                        old_string=f"{TURKISH_WORD} {E_ID}",
                                        new_string="English"))
    check(rc == 0, f"the text being REPLACED is not judged, only the new text (exit {rc})")

    section("guard_public_boundary: never blocks on its own failure")
    for label, stdin in (("malformed JSON", "{not json"), ("empty stdin", ""),
                         ("a JSON list", "[1, 2]"), ("tool_input not a dict",
                                                     json.dumps({"tool_input": "x"})),
                         ("no file path", json.dumps({"tool_input": {"content": E_ID}})),
                         ("content not a string",
                          json.dumps(event("Write", r, file_path=str(r / "README.md"),
                                           content=12345))),
                         ("edits not a list",
                          json.dumps(event("MultiEdit", r, file_path=str(r / "README.md"),
                                           edits="x")))):
        rc, _, _ = run_hook(BOUNDARY, stdin)
        check(rc == 0, f"{label} -> exit 0 (got {rc})")

    section("guard_public_boundary: NFC/NFD spellings of the same directory")
    # The real checkout sits under a directory the filesystem stores decomposed, while a
    # path typed into a tool call is composed. Compared raw they never match.
    base = tmp / DIR_NFC
    rm = make_repo(base, "repo-marked")
    nfd_cwd = unicodedata.normalize("NFD", str(rm))
    rc, _, _ = run_hook(BOUNDARY, event("Write", nfd_cwd,
                                        file_path=unicodedata.normalize("NFC", str(rm / "MOC.md")),
                                        content=E_ID))
    check(rc == 2, f"NFD cwd + NFC file_path, repo found by its marker: blocked (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", unicodedata.normalize("NFC", str(rm)),
                                        file_path=unicodedata.normalize("NFD", str(rm / "MOC.md")),
                                        content=E_ID))
    check(rc == 2, f"NFC cwd + NFD file_path: blocked (exit {rc})")
    elsewhere = tmp / "cwd-elsewhere"
    elsewhere.mkdir()
    rc, _, _ = run_hook(BOUNDARY, event("Write", elsewhere, file_path=str(rm / "MOC.md"),
                                        content=E_ID),
                        env_extra={"CLAUDE_PROJECT_DIR": unicodedata.normalize("NFD", str(rm))})
    check(rc == 2, f"the marked root is found when cwd is elsewhere (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", rm / "website",
                                        file_path=str(rm / "website/src/x.tsx"),
                                        content=E_ID),
                        env_extra={"CLAUDE_PROJECT_DIR": str(rm)})
    check(rc == 2, f"a cwd inside the repo (website/) does not shorten website/src/ to src/ "
                   f"(exit {rc})")

    section("guard_public_boundary: an unmarked directory is never this repository")
    ru = make_repo(base, "repo-unmarked", marker=False)
    rc, _, _ = run_hook(BOUNDARY, event("Write", unicodedata.normalize("NFD", str(ru)),
                                        file_path=unicodedata.normalize("NFC", str(ru / "MOC.md")),
                                        content=E_ID))
    check(rc == 0, f"cwd alone does not make an unmarked directory a root (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", elsewhere, file_path=str(ru / "MOC.md"),
                                        content=E_ID),
                        env_extra={"CLAUDE_PROJECT_DIR": str(ru)})
    check(rc == 0, f"nor does an unmarked CLAUDE_PROJECT_DIR (exit {rc})")
    # the private companion beside the public repo: Turkish belongs there
    pub = make_repo(tmp, "sib-public")
    lab = tmp / "sib-lab"
    (lab / "thesis" / "src").mkdir(parents=True)
    for rel, content in (("README.md", TURKISH_WORD), ("thesis/src/m.py", "x = 1\n"),
                         ("docs/thesis/n.md", f"{E_ID} {MARKER}")):
        rc, _, err = run_hook(BOUNDARY, event("Write", lab, file_path=str(lab / rel),
                                              content=content),
                              env_extra={"CLAUDE_PROJECT_DIR": str(pub)})
        check(rc == 0, f"a session rooted in the public repo that writes {rel} in a sibling "
                       f"repository is not judged as the public repo (exit {rc}, {err!r})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", lab, file_path="README.md",
                                        content=TURKISH_WORD),
                        env_extra={"CLAUDE_PROJECT_DIR": str(pub)})
    check(rc == 0, f"same, with a relative path resolved against the sibling cwd (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", lab, file_path=str(pub / "README.md"),
                                        content=TURKISH_WORD),
                        env_extra={"CLAUDE_PROJECT_DIR": str(pub)})
    check(rc == 2, f"while a write into the public repo from that cwd is still judged "
                   f"(exit {rc})")

    section("guard_public_boundary: nested worktrees and planted markers")
    outer = make_repo(tmp, "wt-outer")
    for name, marked in (("marked", True), ("unmarked", False)):
        w = outer / ".claude" / "worktrees" / name
        (w / "tools").mkdir(parents=True)
        if marked:
            (w / "tools" / "ledger.json").write_text("{}\n", encoding="utf-8")
        for cwd in (w, outer):
            rc, _, _ = run_hook(BOUNDARY, event("Write", cwd, file_path=str(w / "README.md"),
                                                content=TURKISH_WORD),
                                env_extra={"CLAUDE_PROJECT_DIR": str(outer)})
            check(rc == 2, f"README.md of a {name} nested worktree is public "
                           f"(cwd {cwd.name}) (exit {rc})")
        rc, _, err = run_hook(BOUNDARY, event("Write", w, file_path=str(w / "thesis/src/a.py"),
                                              content="x = 1\n"),
                              env_extra={"CLAUDE_PROJECT_DIR": str(outer)})
        check(rc == 2 and "export-only" in err,
              f"thesis/src/ of a {name} nested worktree is export-only (exit {rc})")
        rc, _, _ = run_hook(BOUNDARY, event("Write", w, file_path=str(w / "docs/specs/a.md"),
                                            content=TURKISH_WORD),
                            env_extra={"CLAUDE_PROJECT_DIR": str(outer)})
        check(rc == 0, f"a non-public path of a {name} worktree is still not judged "
                       f"(exit {rc})")
    decoy = make_repo(tmp, "decoy")
    (decoy / "docs" / "thesis" / "tools").mkdir(parents=True)
    (decoy / "docs" / "thesis" / "tools" / "ledger.json").write_text("{}", encoding="utf-8")
    rc, _, _ = run_hook(BOUNDARY, event("Write", elsewhere,
                                        file_path=str(decoy / "docs/thesis/x.md"),
                                        content=TURKISH_WORD))
    check(rc == 2, f"a tools/ledger.json planted inside docs/thesis/ does not shorten the "
                   f"path out of the public set (exit {rc})")
    sib_wt = make_repo(tmp, "wt-sibling")
    rc, _, _ = run_hook(BOUNDARY, event("Write", outer, file_path=str(sib_wt / "README.md"),
                                        content=TURKISH_WORD),
                        env_extra={"CLAUDE_PROJECT_DIR": str(outer)})
    check(rc == 2, f"a marked checkout outside the session's repo (a worktree elsewhere) is "
                   f"judged against its own root (exit {rc})")

    section("guard_public_boundary: stdin is UTF-8 whatever the locale says")
    for label, env in (("PYTHONIOENCODING=latin-1", {"PYTHONIOENCODING": "latin-1"}),
                       ("PYTHONIOENCODING=ascii", {"PYTHONIOENCODING": "ascii"}),
                       ("LC_ALL=en_US.ISO8859-1", {"LC_ALL": "en_US.ISO8859-1",
                                                   "LANG": "en_US.ISO8859-1"})):
        rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "README.md"),
                                            content=TURKISH_WORD), env_extra=env)
        check(rc == 2, f"a Turkish letter is still blocked under {label} (exit {rc})")
        rc, _, _ = run_hook(BOUNDARY, event("Write", rm, file_path=str(rm / "MOC.md"),
                                            content=E_ID), env_extra=env)
        check(rc == 2, f"a repo under a non-ASCII directory is still found under {label} "
                       f"(exit {rc})")

    section("guard_public_boundary: an Edit is judged by the file it produces")
    doc = r / "docs" / "thesis" / "edit.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# Notes\n\nsee E|X for detail\n\nlegacy line " + E_ID + "\n",
                   encoding="utf-8")
    rc, _, err = run_hook(BOUNDARY, event("Edit", r, file_path=str(doc),
                                          old_string="|X", new_string="-07"))
    check(rc == 2 and E_ID in err and "after the edit, line 3" in err,
          f"an Edit that completes an id out of text already in the file is blocked "
          f"(exit {rc}, {err!r})")
    rc, _, err = run_hook(BOUNDARY, event("Edit", r, file_path=str(doc),
                                          old_string="# Notes", new_string="# Overview"))
    check(rc == 0, f"an Edit that leaves an older offending line untouched is allowed "
                   f"(exit {rc}, {err!r})")
    rc, _, _ = run_hook(BOUNDARY, event(
        "MultiEdit", r, file_path=str(doc),
        edits=[{"old_string": "# Notes", "new_string": "# Overview"},
               {"old_string": "|X", "new_string": "|-0"},
               {"old_string": "E|-0", "new_string": "E-0" + "7"}]))
    check(rc == 2, f"a MultiEdit is judged after all its edits apply in order (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event(
        "MultiEdit", r, file_path=str(doc),
        edits=[{"old_string": "see E", "new_string": "see Q-M"},
               {"old_string": "|X", "new_string": "-12"}]))
    check(rc == 2, f"two edits that each look clean but together write an id: blocked "
                   f"(exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Edit", r, file_path=str(doc), old_string="|X",
                                        new_string="-07", replace_all=True))
    check(rc == 2, f"replace_all is applied too (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Edit", r, file_path=str(doc),
                                        old_string="not in the file", new_string=E_ID))
    check(rc == 2, f"when the replacement does not apply, new_string alone is still judged "
                   f"(exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Edit", r, file_path=str(doc),
                                        old_string="not in the file", new_string="clean"))
    check(rc == 0, f"and a clean new_string then passes (exit {rc})")
    check("E|X" in doc.read_text(encoding="utf-8"), "the hook never wrote the file it judged")

    doc2 = r / "docs" / "thesis" / "multiset.md"
    doc2.write_text("one\nlegacy " + E_ID + "\ntwo\n", encoding="utf-8")
    rc, _, err = run_hook(BOUNDARY, event("Edit", r, file_path=str(doc2),
                                          old_string="one\nlegacy " + E_ID,
                                          new_string="legacy " + E_ID + "\none"))
    check(rc == 0, f"reordering existing lines writes nothing new (exit {rc}, {err!r})")
    rc, _, _ = run_hook(BOUNDARY, event(
        "MultiEdit", r, file_path=str(doc2),
        edits=[{"old_string": "one", "new_string": "ONE"},
               {"old_string": "two", "new_string": "TWO"},
               {"old_string": "legacy " + E_ID,
                "new_string": "legacy " + E_ID + "\nlegacy " + E_ID}]))
    check(rc == 2, f"repeating an offending line one time more, among other changed lines, "
                   f"writes it: lines are counted with multiplicity (exit {rc})")

    section("guard_public_boundary: the Edit simulation stays linear (no line diff)")
    big = r / "website" / "src" / "data" / "big.json"
    big.parent.mkdir(parents=True, exist_ok=True)
    rows = [("    {", '      "x": 1,', "    },")[i % 3] for i in range(60000)]
    rows[30000] = '    "anchor": 0,'
    big.write_text("[\n" + "\n".join(rows) + "\n]\n", encoding="utf-8")
    t0 = time.monotonic()
    rc, _, err = run_hook(BOUNDARY, event("Edit", r, file_path=str(big),
                                          old_string='"anchor": 0,',
                                          new_string=f'"anchor": "see {E_ID}",'))
    took = time.monotonic() - t0
    check(rc == 2 and E_ID in err, f"an id written into a 60k-line file of repeated lines is "
                                   f"blocked (exit {rc})")
    check(took < 5, f"and judged in {took:.1f} s, far inside the 15 s hook timeout (a line "
                    f"diff took over 100 s on this file)")
    t0 = time.monotonic()
    rc, _, _ = run_hook(BOUNDARY, event("Edit", r, file_path=str(big), old_string='"x": 1,',
                                        new_string='"x": 2,', replace_all=True))
    took = time.monotonic() - t0
    check(rc == 0 and took < 5, f"replace_all over every repeated line: exit {rc} in "
                                f"{took:.1f} s")
    big.write_text("HEAD\n" + "\n".join(["a", "b"] * 1000) + "\nTAIL\n", encoding="utf-8")
    t0 = time.monotonic()
    rc, _, _ = run_hook(BOUNDARY, event(
        "MultiEdit", r, file_path=str(big),
        edits=[{"old_string": "HEAD", "new_string": "H"},
               {"old_string": "TAIL", "new_string": "T"},
               {"old_string": "a\nb\na\nb\n", "new_string": "b\na\nc\n",
                "replace_all": True}]))
    took = time.monotonic() - t0
    check(rc == 0 and took < 5, f"edits at both ends of 2000 alternating lines: exit {rc} in "
                                f"{took:.1f} s (a 2000-line diff took 14 s)")

    section("guard_public_boundary: files over 1 MB and CRLF line endings are simulated")
    bigmd = r / "docs" / "thesis" / "big.md"
    bigmd.write_text(("filler line " + "x" * 67 + "\n") * 13500 + "see E|X\n",
                     encoding="utf-8")
    check(bigmd.stat().st_size > 1_000_000, "the probe file is over 1 MB")
    rc, _, err = run_hook(BOUNDARY, event("Edit", r, file_path=str(bigmd), old_string="|X",
                                          new_string="-07"))
    check(rc == 2 and "after the edit, line 13501" in err,
          f"an Edit completing an id at the end of a 1.08 MB file is blocked (exit {rc})")
    crlf = r / "docs" / "thesis" / "crlf.md"
    crlf.write_bytes(b"see E|X\r\nend\r\n")
    rc, _, _ = run_hook(BOUNDARY, event("Edit", r, file_path=str(crlf), old_string="|X\nend",
                                        new_string="-07\nend"))
    check(rc == 2, f"an Edit whose LF old_string matches CRLF text, as the Edit tool matches "
                   f"it, is simulated and blocked (exit {rc})")
    lf = r / "docs" / "thesis" / "lf.md"
    lf.write_bytes(b"see E|X\nend\n")
    rc, _, _ = run_hook(BOUNDARY, event("Edit", r, file_path=str(lf), old_string="|X\nend",
                                        new_string="-07\nend"))
    check(rc == 2, f"and the same edit on an LF copy (exit {rc})")

    section("guard_public_boundary: an edit is applied as the tool that makes it applies it")
    # Claude Code 2.1.246, checked by real Edit calls: an empty new_string also removes the
    # newline after old_string, and straight quotes in old_string match curly ones.
    ed = r / "docs" / "thesis" / "tool.md"
    ed.write_text("see E-0Z\n7 items\n", encoding="utf-8")
    rc, _, err = run_hook(BOUNDARY, event("Edit", r, file_path=str(ed), old_string="Z",
                                          new_string=""))
    check(rc == 2 and E_ID in err, f"Edit deleting 'Z' also deletes the newline after it, which "
                                   f"joins 'see E-0' and '7 items' (exit {rc}, {err!r})")
    ed.write_text("tag " + MARKER[:-3] + "Z\n" + MARKER[-3:] + "\n", encoding="utf-8")
    rc, _, _ = run_hook(BOUNDARY, event("Edit", r, file_path=str(ed), old_string="Z",
                                        new_string=""))
    check(rc == 2, f"the same join completes the private marker (exit {rc})")
    ed.write_text("see E-0Zq\nsee E-0Z\n7 items\n", encoding="utf-8")
    rc, _, _ = run_hook(BOUNDARY, event("Edit", r, file_path=str(ed), old_string="Z",
                                        new_string="", replace_all=True))
    check(rc == 2, f"with replace_all only the occurrences followed by a newline lose it, as "
                   f"the tool does (exit {rc})")
    ed.write_text("abcZ\nxyz\n", encoding="utf-8")
    rc, _, err = run_hook(BOUNDARY, event("Edit", r, file_path=str(ed), old_string="Z",
                                          new_string=""))
    check(rc == 0, f"and a harmless join passes (exit {rc}, {err!r})")
    for label, curly, straight in (("double", "“q”", '"q"'),
                                   ("single", "‘q’", "'q'")):
        ed.write_text(f"see E-0{curly} here\n", encoding="utf-8")
        rc, _, err = run_hook(BOUNDARY, event("Edit", r, file_path=str(ed), old_string=straight,
                                              new_string="7"))
        check(rc == 2 and E_ID in err, f"straight {label} quotes in old_string match curly ones in "
                                       f"the file, as the Edit tool matches them (exit {rc})")
    ed.write_text("see E-0“q” here\n", encoding="utf-8")
    rc, _, _ = run_hook(BOUNDARY, event("MultiEdit", r, file_path=str(ed),
                                        edits=[{"old_string": '"q"', "new_string": "7"}]))
    check(rc == 2, f"MultiEdit matches quotes the same way (exit {rc})")

    fs_edit = "mcp__filesystem__edit_file"
    ed.write_text("X7 items\n", encoding="utf-8")
    rc, _, err = run_hook(BOUNDARY, event(fs_edit, r, path=str(ed),
                                          edits=[{"oldText": "X", "newText": "see E-0$'"}]))
    check(rc == 2 and E_ID in err, f"edit_file: $' read as JavaScript's 'text after the match' "
                                   f"completes an id (exit {rc}, {err!r})")
    rc, _, _ = run_hook(BOUNDARY, {"cwd": str(r),
                                   "tool_input": {"path": str(ed),
                                                  "edits": [{"oldText": "X",
                                                             "newText": "see E-0$'"}]}})
    check(rc == 2, f"with no tool name every reading is judged, the pattern one included "
                   f"(exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("mcp__Desktop_Commander__edit_block", r,
                                        file_path=str(ed), old_string="X",
                                        new_string="see E-0$'"))
    check(rc == 0, f"edit_block splices its text literally (Desktop Commander 0.2.46), so $' "
                   f"is two characters there (exit {rc})")
    ed.write_text("7 items\n", encoding="utf-8")
    rc, _, _ = run_hook(BOUNDARY, event(fs_edit, r, path=str(ed),
                                        edits=[{"oldText": "", "newText": "see E-0"}]))
    check(rc == 2, f"edit_file with an empty oldText inserts at the start of the file and "
                   f"joins its first line (exit {rc})")
    ed.write_text("x" * 1_000_000 + "X\n", encoding="utf-8")
    rc, _, err = run_hook(BOUNDARY, event(fs_edit, r, path=str(ed),
                                          edits=[{"oldText": "X", "newText": "$`" * 40}]))
    check(rc == 2 and "JavaScript replacement pattern" in err,
          f"a pattern that would expand past the size cap is refused, not expanded (exit {rc})")
    ed.write_text("see E-<!--\n   placeholder  \n07 items\n", encoding="utf-8")
    rc, _, err = run_hook(BOUNDARY, event(fs_edit, r, path=str(ed),
                                          edits=[{"oldText": "placeholder   ",
                                                  "newText": "-->07"}]))
    check(rc == 2 and E_ID in err,
          f"edit_file with no exact match matches the line with its whitespace ignored, as the "
          f"filesystem server does; the new line closes the comment (exit {rc}, {err!r})")
    rc, _, _ = run_hook(BOUNDARY, event(fs_edit, r, path=str(ed),
                                        edits=[{"oldText": "nowhere", "newText": "-->07"}]))
    check(rc == 0, f"and an edit_file that matches nothing judges its new text alone (exit {rc})")

    section("guard_public_boundary: the path is resolved as the tool resolves it")
    rs = make_repo(tmp, "repo-symlink")
    (rs / "docs" / "thesis" / "sub").mkdir(parents=True)
    out_deep = tmp / "outside" / "deep"
    out_deep.mkdir(parents=True)
    os.symlink(out_deep, rs / "lnk")
    os.symlink(rs / "docs" / "thesis" / "sub", rs / "lnk2")
    rc, _, _ = run_hook(BOUNDARY, event("Write", rs, file_path=str(rs) + "/lnk/../README.md",
                                        content=TURKISH_WORD))
    check(rc == 2, f"'..' after a symlink that points outside: <repo>/lnk/../README.md is "
                   f"README.md, as the tool writes it (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", rs, file_path=str(rs) + "/lnk2/../a.md",
                                        content=TURKISH_WORD))
    check(rc == 2, f"the spelling that follows the symlink first is judged too, and the "
                   f"strictest judgment wins (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", rs, file_path=str(rs) + "/lnk/x.md",
                                        content=TURKISH_WORD))
    check(rc == 0, f"a path that really is outside the repository is not judged (exit {rc})")
    home = tmp / "home"
    rh = make_repo(home, "repo-home")
    rc, _, _ = run_hook(BOUNDARY, event("Write", tmp, file_path="~/repo-home/README.md",
                                        content=TURKISH_WORD),
                        env_extra={"HOME": str(home)})
    check(rc == 2, f"a leading '~' is read as the home directory (exit {rc})")
    check(not (rh / "README.md").exists(), "no event wrote a file")

    section("guard_public_boundary: invisible characters and Markdown escapes")
    invisible_cases = (
        ("U+2062 INVISIBLE TIMES", "E\u2062-" + "07"),
        ("U+2063 INVISIBLE SEPARATOR", "E\u2063-" + "07"),
        ("U+034F COMBINING GRAPHEME JOINER", "E\u034f-" + "07"),
        ("U+180E MONGOLIAN VOWEL SEPARATOR", "E\u180e-" + "07"),
        ("U+FE0F VARIATION SELECTOR-16", "E\ufe0f-" + "07"),
        ("a tag character", "E\U000e0041-" + "07"),
        ("a left-to-right mark", "E\u200e-" + "07"),
        ("a Hangul filler", "E\u3164-" + "07"),
    )
    for label, text in invisible_cases:
        rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "docs/thesis/i.md"),
                                            content=f"see {text}\n"))
        check(rc == 2, f"an id split by {label} is blocked (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "docs/thesis/m.md"),
                                        content="scm" + "\\:" + "private\n"))
    check(rc == 2, f"the marker with a Markdown-escaped colon is blocked (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "docs/thesis/m.md"),
                                        content="ba" + "s\u200d\u0327" + "ar\n"))
    check(rc == 2, f"a decomposed Turkish letter split by a joiner recombines (exit {rc})")
    control_cases = (
        ("U+0001 (a C0 control)", "E\x01-" + "07"),
        ("U+001C FILE SEPARATOR", "E\x1c-" + "07"),
        ("U+001E RECORD SEPARATOR", "E\x1e-" + "07"),
        ("U+000B VERTICAL TAB", "E\x0b-" + "07"),
        ("U+000C FORM FEED", "E\x0c-" + "07"),
        ("U+007F DELETE", "E\x7f-" + "07"),
        ("U+0085 NEXT LINE", "E\x85-" + "07"),
        ("U+0090 (a C1 control)", "E\x90-" + "07"),
        ("U+2028 LINE SEPARATOR", "E -" + "07"),
        ("U+2029 PARAGRAPH SEPARATOR", "E -" + "07"),
        ("U+001C inside the marker", MARKER[:3] + "\x1c" + MARKER[3:]),
    )
    for label, text in control_cases:
        rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "README.md"),
                                            content=f"see {text}\n"))
        check(rc == 2, f"an id split by {label} is blocked: it ends no line in Markdown or HTML "
                       f"(exit {rc})")
    rc, _, err = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "README.md"),
                                          content="a\x0bb\x1cc d\nsee " + E_ID + "\n"))
    check(rc == 2 and "line 2:" in err, f"lines are counted at LF only, as an editor counts them "
                                        f"({err!r})")
    rc, _, err = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "README.md"),
                                          content="see E\t-" + "07 and E\r-" + "07\n"))
    check(rc == 0, f"a tab or a lone CR is whitespace where it renders, not dropped (exit {rc}, "
                   f"{err!r})")

    section("guard_public_boundary: inline markup and look-alike letters (PUBLIC paths)")
    markup_cases = (
        ("bold around the letter", "**E**-" + "07"),
        ("emphasis around the dash", "E*-*" + "07"),
        ("an empty HTML element", "E<span></span>-" + "07"),
        ("an HTML comment", "E<!-- x -->-" + "07"),
        ("a code span", "`E`-" + "07"),
        ("strike-through", "E~~-" + "07~~"),
        ("a link", "[E](https://example.org)-" + "07"),
        ("a reference link", "[E][1]-" + "07"),
        ("bold inside the marker", "**scm**:" + "private"),
        ("a Cyrillic E", "\u0415-" + "07"),
        ("a Greek A", "\u0391DR-" + "012"),
        ("a Cherokee M", "Q-\u13b7-" + "12"),
        ("a Lisu E", "\ua4f0-" + "07"),
        ("a Cyrillic c in the marker", "s\u0441m" + ":" + "private"),
        ("a ratio sign for the colon", "scm\u2236" + "private"),
    )
    for label, text in markup_cases:
        for rel in ("README.md", "website/src/pages/a.astro"):
            rc, _, err = run_hook(BOUNDARY, event("Write", r, file_path=str(r / rel),
                                                  content=f"see {text} here\n"))
            check(rc == 2, f"{label} in {rel} is blocked (exit {rc})")
    check("split by inline markup" in run_hook(BOUNDARY, event(
        "Write", r, file_path=str(r / "README.md"), content="**E**-" + "07\n"))[2],
        "the message says the id was split by inline markup")
    # A quoted attribute value may hold ">" (HTML and CommonMark inline HTML); the tag still
    # renders as nothing. Each of these exited 0 before the fix (reviewer round 2).
    for rel, text in (("README.md", 'see E-<span title="a>b">' + "07</span>"),
                      ("website/src/p.astro", "<p>E-<b data-x='>'>" + "07</b></p>"),
                      ("docs/thesis/a.md", "E<i title=\"x>y\" class='z>w'>-</i>" + "07"),
                      ("README.md", 'see E-<span title="a<b>c">' + "07</span>"),
                      ("README.md", "see E-<a title='unclosed>" + "07"),
                      ("README.md", "see E-<span title='a\"b>c'>" + "07"),
                      # a JSX or Astro attribute expression holds ">" the same way
                      ("website/src/a.tsx", "<p>E-<b onClick={() => go()}>" + "07</b></p>"),
                      ("website/src/a.astro", "<p>E-<b style={{a: x > y}}>" + "07</b></p>")):
        rc, _, err = run_hook(BOUNDARY, event("Write", r, file_path=str(r / rel),
                                              content=text + "\n"))
        check(rc == 2 and "split by inline markup" in err,
              f"{text!r} in {rel}: a tag whose quoted value holds '>' is removed "
              f"(exit {rc}, {err!r})")
    for label, text in (("snake_case and emphasis", "use *snake_case* and __init__ names"),
                        ("an HTML tag in prose", "<kbd>E</kbd> then 07"),
                        ("a link labelled E-mail", "[E-mail](mailto:a@example.org)"),
                        ("Greek in a formula", "\u03c4 = 10 ms, \u03bd = 5 Hz, "
                                               "\u0394 = 0.07"),
                        ("Markdown escapes in prose", "a \\* b \\_ c \\- d"),
                        ("a scientific literal next to markup", "**1E-12** and `TYPE-12`")):
        rc, _, err = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "README.md"),
                                              content=text + "\n"))
        check(rc == 0, f"no false positive: {label} (exit {rc}, {err!r})")

    section("guard_public_boundary: a comment or tag that spans a line break (PUBLIC paths)")
    for rel, text in (("README.md", "see E-<!--\n-->" + "07 here"),
                      ("README.md", "see E-<!-- a\nlonger\ncomment -->" + "07 here"),
                      ("docs/thesis/a.md", "see E-<span\n>" + "07</span>"),
                      ("MOC.md", "tag " + MARKER[:4] + "<!--\n-->" + MARKER[4:]),
                      ("website/src/pages/b.astro", "<p>E<b\n  class='x'>-</b\n>" + "07</p>"),
                      ("docs/thesis/a.md", "see **E**-<!--\n-->" + "07"),
                      # a quoted value holding ">" (reviewer round 2; each exited 0)
                      ("README.md", 'see E-<span title="a>b"\n>' + "07</span>"),
                      ("website/src/pages/c.astro", "<p>E-<b\n data-x='>'>" + "07</b></p>"),
                      ("README.md", 'see E-<span title="a\n>b">' + "07</span>"),
                      ("README.md", 'see E-<a title="-->"\n>' + "07"),
                      ("website/src/b.astro", "<p>E-<b\n onClick={() =>\n go()}>" + "07</b></p>")):
        rc, _, err = run_hook(BOUNDARY, event("Write", r, file_path=str(r / rel), content=text))
        check(rc == 2 and "read across lines" in err,
              f"{text!r} in {rel} is read as it renders, joined (exit {rc}, {err!r})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "README.md"),
                                        content="see E-<!-- x -->" + "07 here"))
    check(rc == 2, f"the same split on one line was already blocked (exit {rc})")
    far = r / "docs" / "thesis" / "far.md"
    far.write_text("see E-<!--\na\nb\nc\nEND 07 here\n", encoding="utf-8")
    rc, _, err = run_hook(BOUNDARY, event("Edit", r, file_path=str(far), old_string="END ",
                                          new_string="-->"))
    check(rc == 2 and "line 1" in err,
          f"an Edit that closes a comment opened four lines up is judged at the line it joins "
          f"(exit {rc}, {err!r})")
    far.write_text("see E-<!--\n-->07\nother\n", encoding="utf-8")
    rc, _, err = run_hook(BOUNDARY, event("Edit", r, file_path=str(far), old_string="other",
                                          new_string="else"))
    check(rc == 0, f"an Edit elsewhere does not re-judge a joined line already in the file "
                   f"(exit {rc}, {err!r})")
    for label, rel, text in (
            ("a tag over several lines in prose", "README.md",
             '<div\n  class="note">\nPlain English.\n</div>\n'),
            ("comparisons in code", "website/src/x.ts", "if (a < b) {\n  return c > d;\n}\n"),
            ("an unclosed comment", "README.md", "see E-<!--\n07 is a count\n"),
            ("a comment that hides the id's tail", "README.md", "see E-<!--\n07\n-->\n")):
        rc, _, err = run_hook(BOUNDARY, event("Write", r, file_path=str(r / rel), content=text))
        check(rc == 0, f"no false positive: {label} (exit {rc}, {err!r})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "CLAUDE.md"),
                                        content="see E-<!--\n-->" + "07\n"))
    check(rc == 0, f"English-only paths outside the public set are judged for Turkish letters "
                   f"only, joined or not (exit {rc})")
    t0 = time.monotonic()
    storm = ("a <!-- b\n" * 100_000) + ("<div\n>x</div>\n" * 50_000) + "see E-<b\n>" + "07\n"
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "website/src/storm.astro"),
                                        content=storm))
    took = time.monotonic() - t0
    check(rc == 2 and took < 5, f"100k unclosed comment openers and 50k multi-line tags are read "
                                f"in linear time: exit {rc} in {took:.1f} s")
    for label, storm in (
            ("200k unclosed quotes in tags over lines", '<a "x\n' * 200_000),
            ("a 400 kB line of quoted '<'", '<"<"' * 100_000),
            ("a 400 kB line of alternating quotes", "<a \"'<'\" '\"<\"' " * 25_000),
            ("a 400 kB line of braces around '<'", "<{<}{<}" * 60_000),
            ("a 400 kB line of nested braces", "<a x={{<}{<}}" * 30_000),
            ("200k unclosed braces over lines", "<a x={\n" * 200_000),
            ("100k comment openers on one line before a far close", "<!--" * 100_000 + "-->"),
            ("100k single-line tags with quoted '>'", '<b t=">">x</b>\n' * 100_000)):
        t0 = time.monotonic()
        rc, _, _ = run_hook(BOUNDARY, event("Write", r,
                                            file_path=str(r / "website/src/storm2.astro"),
                                            content=storm + "\nsee E-<b\n>" + "07\n"))
        took = time.monotonic() - t0
        check(rc == 2 and took < 5, f"{label}: read in linear time, and the split id after it "
                                    f"is still found (exit {rc} in {took:.1f} s)")
    try:
        joined_cap = load_module("guard_public_boundary_joined", BOUNDARY).MAX_JOINED_LINES
        t0 = time.monotonic()
        rc, _, err = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "README.md"),
                                              content="x<b\n>y\n" * (joined_cap + 1)))
        took = time.monotonic() - t0
        check(rc == 2 and f"more than {joined_cap} lines are joined" in err and took < 5,
              f"a write that joins more than {joined_cap} lines is refused, not judged past the "
              f"hook's timeout (exit {rc} in {took:.1f} s)")
        rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "README.md"),
                                            content="x<b\n>y\n" * (joined_cap // 4)))
        check(rc == 0, f"and one that joins {joined_cap // 4} clean lines passes (exit {rc})")
    except Exception as e:
        check(False, f"could not run the joined-lines cap probe: {type(e).__name__}: {e}")

    section("guard_public_boundary: MCP file tools")
    m = make_repo(tmp, "repo-mcp")
    dc = "mcp__Desktop_Commander__"
    rc, _, _ = run_hook(BOUNDARY, event(dc + "write_file", m, path=str(m / "docs/thesis/a.md"),
                                        content=f"see {E_ID}"))
    check(rc == 2, f"write_file {{path, content}} with an id is blocked (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event(dc + "write_file", m, path=str(m / "docs/thesis/a.md"),
                                        content="Plain English."))
    check(rc == 0, f"write_file with clean text is allowed (exit {rc})")
    (m / "docs" / "thesis").mkdir(parents=True, exist_ok=True)
    (m / "docs" / "thesis" / "app.md").write_text("see E", encoding="utf-8")
    rc, _, _ = run_hook(BOUNDARY, event(dc + "write_file", m, path=str(m / "docs/thesis/app.md"),
                                        content="-07\n", mode="append"))
    check(rc == 2, f"write_file in append mode is judged with the line it extends (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event(dc + "write_file", m, path=str(m / "docs/thesis/app.md"),
                                        content="-mail\n", mode="append"))
    check(rc == 0, f"and a clean append passes (exit {rc})")
    (m / "README.md").write_text("# T\n\nsee E|X\ne|mail E|" + "07\n", encoding="utf-8")
    rc, _, _ = run_hook(BOUNDARY, event(dc + "edit_block", m, file_path=str(m / "README.md"),
                                        old_string="|X", new_string="-07"))
    check(rc == 2, f"edit_block {{file_path, old_string, new_string}} is simulated (exit {rc})")
    (m / "README.md").write_text("e|mail\nE|" + "07\n", encoding="utf-8")
    rc, _, _ = run_hook(BOUNDARY, event(dc + "edit_block", m, file_path=str(m / "README.md"),
                                        old_string="|", new_string="-"))
    check(rc == 0, f"edit_block replaces one occurrence by default (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event(dc + "edit_block", m, file_path=str(m / "README.md"),
                                        old_string="|", new_string="-",
                                        expected_replacements=2))
    check(rc == 2, f"and expected_replacements=2 replaces two (exit {rc})")
    (m / "docs" / "thesis" / "fs.md").write_text("see E|X\n", encoding="utf-8")
    rc, _, _ = run_hook(BOUNDARY, event("mcp__filesystem__edit_file", m,
                                        path=str(m / "docs/thesis/fs.md"),
                                        edits=[{"oldText": "|X", "newText": "-07"}]))
    check(rc == 2, f"the filesystem server's edit_file {{path, edits[oldText, newText]}} is "
                   f"simulated (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event(dc + "write_pdf", m, path=str(m / "docs/thesis/in.pdf"),
                                        outputPath=str(m / "docs/thesis/out.pdf"),
                                        content=f"# {TURKISH_WORD}"))
    check(rc == 2, f"write_pdf markdown content is judged (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event(dc + "write_pdf", m, path=str(m / "docs/thesis/in.pdf"),
                                        content=[{"type": "insert", "pageIndex": 0,
                                                  "markdown": f"see {E_ID}"}]))
    check(rc == 2, f"and so is the markdown of a write_pdf operation (exit {rc})")
    for rel, want in (("thesis/src/new", 2), ("thesis/src", 2),
                      ("docs/thesis/" + TURKISH_WORD, 2), ("docs/thesis/clean", 0)):
        rc, _, _ = run_hook(BOUNDARY, event(dc + "create_directory", m, path=str(m / rel)))
        check(rc == want, f"create_directory {rel}: exit {want} (got {rc})")

    src_dir = tmp / "mcp-src"
    src_dir.mkdir()
    (src_dir / "tr.md").write_text(TURKISH_WORD, encoding="utf-8")
    (src_dir / "clean.md").write_text("Plain English.\n", encoding="utf-8")
    (src_dir / "img.png").write_bytes(b"\x89PNG\x00\x00" + S_CEDILLA.encode("utf-8"))
    for label, src, dest, want in (
            ("a file with a Turkish letter into docs/thesis/", "tr.md", "docs/thesis/m1.md", 2),
            ("a clean file into docs/thesis/", "clean.md", "docs/thesis/m2.md", 0),
            ("a clean file into thesis/src/", "clean.md", "thesis/src/m3.md", 2),
            ("a clean file to a name with an id", "clean.md", f"docs/thesis/{E_ID}.md", 2),
            ("a binary file (NUL bytes) into website/src/", "img.png", "website/src/i.png", 0)):
        rc, _, _ = run_hook(BOUNDARY, event(dc + "move_file", m, source=str(src_dir / src),
                                            destination=str(m / dest)))
        check(rc == want, f"move_file {label}: exit {want} (got {rc})")
    (m / "thesis" / "src").mkdir(parents=True, exist_ok=True)
    (m / "thesis" / "src" / "x.py").write_text("x = 1\n", encoding="utf-8")
    rc, _, err = run_hook(BOUNDARY, event(dc + "move_file", m, source=str(m / "thesis/src/x.py"),
                                          destination=str(m / "docs/specs/x.py")))
    check(rc == 2 and "moves a file out of" in err,
          f"move_file out of thesis/src/ is refused (exit {rc})")
    pkg = tmp / "mcp-pkg"
    (pkg / "notes").mkdir(parents=True)
    (pkg / "notes" / "a.md").write_text("fine\n" + TURKISH_WORD + "\n", encoding="utf-8")
    rc, _, err = run_hook(BOUNDARY, event(dc + "move_file", m, source=str(pkg),
                                          destination=str(m / "docs/thesis/pkg")))
    check(rc == 2 and "notes/a.md, line 2" in err,
          f"move_file of a directory judges the files inside it (exit {rc}, {err!r})")
    pkg2 = tmp / "mcp-pkg2"
    (pkg2 / "src").mkdir(parents=True)
    (pkg2 / "src" / "m.py").write_text("x = 1\n", encoding="utf-8")
    rc, _, err = run_hook(BOUNDARY, event(dc + "move_file", m, source=str(pkg2),
                                          destination=str(m / "thesis")))
    check(rc == 2 and "export-only" in err,
          f"a directory moved to thesis/ that brings a src/ with it is refused (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event(
        "mcp__google_drive__create_file", m, title="README.md", textContent=TURKISH_WORD,
        contentMimeType="text/plain"))
    check(rc == 0, f"a create_file that carries no local path (a Drive upload) is not "
                   f"judged (exit {rc})")

    section("guard_public_boundary: moving the export-only package by an ancestor")
    for src_rel, dest_rel in (("thesis", "thesis_old"), ("thesis/", "archive/thesis"),
                              ("THESIS", "elsewhere")):
        rc, _, err = run_hook(BOUNDARY, event(dc + "move_file", m, source=str(m / src_rel),
                                              destination=str(m / dest_rel)))
        check(rc == 2 and "holds thesis/src/" in err,
              f"move_file {src_rel} -> {dest_rel} takes thesis/src/ with it: refused (exit {rc})")
    wt = m / ".claude" / "worktrees" / "w1"
    (wt / "thesis" / "src").mkdir(parents=True)
    (wt / "thesis" / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    for src in (wt, wt / "thesis", m / ".claude" / "worktrees"):
        rc, _, _ = run_hook(BOUNDARY, event(dc + "move_file", m, source=str(src),
                                            destination=str(m / "docs/specs/moved")))
        check(rc == 2, f"moving {src.relative_to(m)} takes a checkout's thesis/src/ with it: "
                       f"refused (exit {rc})")
    (m / "docs" / "specs").mkdir(parents=True, exist_ok=True)
    (m / "thesis_notes").mkdir(exist_ok=True)
    for src_rel in ("docs/specs", "thesis_notes"):
        rc, _, _ = run_hook(BOUNDARY, event(dc + "move_file", m, source=str(m / src_rel),
                                            destination=str(m / "docs/archive")))
        check(rc == 0, f"moving {src_rel}, which holds no export-only path, is allowed "
                       f"(exit {rc})")
    tree = tmp / "mcp-wt-tree"
    tree.mkdir()
    (tree / "README.md").write_text(TURKISH_WORD + "\n", encoding="utf-8")
    rc, _, _ = run_hook(BOUNDARY, event(dc + "move_file", m, source=str(tree),
                                        destination=str(m / ".claude/worktrees/w2")))
    check(rc == 2, f"a directory moved in as a nested worktree has its README.md judged as "
                   f"public, as a direct write there is (exit {rc})")

    section("guard_public_boundary: a move too large to judge is refused, not judged in part")
    try:
        guard = load_module("guard_public_boundary_caps", BOUNDARY)
        cap_bytes, cap_files, cap_names = (guard.MAX_SIMULATED_BYTES, guard.MAX_MOVED_FILES,
                                           guard.MAX_MOVED_NAMES)
        bulk = tmp / "mcp-bulk"
        bulk.mkdir()
        for i in range(cap_names + 1):
            os.close(os.open(str(bulk / f"e{i:05d}"), os.O_CREAT | os.O_WRONLY, 0o644))
        (bulk / ("zz_" + TURKISH_WORD + ".md")).write_text("x\n", encoding="utf-8")
        (bulk / "zz_note.md").write_text(f"see {E_ID}\n", encoding="utf-8")
        rc, _, err = run_hook(BOUNDARY, event(dc + "move_file", m, source=str(bulk),
                                              destination=str(m / "docs/thesis/bulk")))
        check(rc == 2 and f"more than {cap_names} entries" in err,
              f"a tree of more than {cap_names} entries moved into docs/thesis/ is refused "
              f"(exit {rc}, {err[-160:]!r})")
        rc, _, _ = run_hook(BOUNDARY, event(dc + "move_file", m, source=str(bulk),
                                            destination=str(m / "docs/specs/bulk")))
        check(rc == 0, f"the same tree moved where nothing is judged is not walked (exit {rc})")
        shutil.rmtree(bulk)
        many = tmp / "mcp-many"
        many.mkdir()
        for i in range(cap_files + 1):
            (many / f"f{i:05d}.md").write_text("Plain English.\n", encoding="utf-8")
        rc, _, err = run_hook(BOUNDARY, event(dc + "move_file", m, source=str(many),
                                              destination=str(m / "website/src/many")))
        check(rc == 2 and f"more than {cap_files} files" in err,
              f"more than {cap_files} files of text into website/src/ is refused (exit {rc})")
        shutil.rmtree(many)
        heavy = tmp / "mcp-heavy"
        heavy.mkdir()
        for name in ("a.md", "b.md"):
            with open(heavy / name, "wb") as fh:
                fh.write(b"plain line\n" * (cap_bytes // 22 + 100))
        rc, _, err = run_hook(BOUNDARY, event(dc + "move_file", m, source=str(heavy),
                                              destination=str(m / "docs/thesis/heavy")))
        check(rc == 2 and "left to judge" in err,
              f"more than {cap_bytes // 1_000_000} MB of text in all is refused (exit {rc})")
        shutil.rmtree(heavy)
        one = tmp / "mcp-one.md"
        with open(one, "wb") as fh:
            fh.write(b"filler line\n" * (cap_bytes // 12 + 1))
            fh.write(("see " + TURKISH_WORD + "\n").encode("utf-8"))
        t0 = time.monotonic()
        rc, _, err = run_hook(BOUNDARY, event(dc + "move_file", m, source=str(one),
                                              destination=str(m / "docs/thesis/one.md")))
        check(rc == 2 and "left to judge" in err and time.monotonic() - t0 < 5,
              f"one moved file over the {cap_bytes // 1_000_000} MB cap is refused, not passed "
              f"unread (exit {rc})")
        rc, _, _ = run_hook(BOUNDARY, event(dc + "move_file", m, source=str(one),
                                            destination=str(m / "docs/specs/one.md")))
        check(rc == 0, f"and moved where nothing is judged it is allowed (exit {rc})")
        one.unlink()
    except Exception as e:
        check(False, f"could not run the move-cap probes: {type(e).__name__}: {e}")

    section("guard_public_boundary: dashes, escapes, case, underscores, file names")
    hyphen_cases = (
        ("a non-breaking hyphen", "E\u2011" + "07"),
        ("an en dash", "E\u2013" + "07"),
        ("a minus sign", "ADR\u2212" + "012"),
        ("a fullwidth hyphen", "E\uff0d" + "07"),
        ("a zero-width space", "E\u200b-" + "07"),
        ("a Markdown-escaped hyphen", "E\\-" + "07"),
        ("lower case", E_ID.lower()),
        ("lower case ADR", ADR_ID.lower()),
        ("after an underscore", "run_" + E_ID),
        ("after a hyphen", "results-" + E_ID),
        ("in an anchor", "#" + E_ID.lower() + "-results"),
    )
    for label, text in hyphen_cases:
        rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "docs/thesis/h.md"),
                                            content=f"see {text}\n"))
        check(rc == 2, f"an id written with {label} is blocked (exit {rc})")
    for label, text in (("1E-12", "1E-12"), ("TYPE-12", "TYPE-12"), ("1e-07", "1e-07"),
                        ("an em dash in prose", "a pause \u2014 then more"),
                        ("E-mail", "E-mail")):
        rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "docs/thesis/h.md"),
                                            content=f"{text}\n"))
        check(rc == 0, f"{label} is not an id (exit {rc})")

    escape_cases = (
        ("an HTML numeric entity in Markdown", "docs/thesis/e.md", "ba&#351;ar"),
        ("an HTML hex entity in README.md", "README.md", "ba&#x15F;ar"),
        ("an HTML named entity", "docs/thesis/e.md", "ba&scedil;ar"),
        ("an entity spelling an id", "docs/thesis/e.md", "E&#45;" + "07"),
        ("a JS \\u escape under website/src/", "website/src/x.tsx",
         'const s = "ba\\u015far";'),
        ("a JS \\u{...} escape under website/src/", "website/src/x.tsx",
         'const s = "ba\\u{15f}ar";'),
        ("a JS \\x escape under website/src/", "website/src/x.tsx",
         'const s = "\\xfc";'),
        ("JSON written with ensure_ascii to the plan", "tools/thesis_plan.json",
         json.dumps({"title": TURKISH_WORD})),
        ("a JSON \\u escape spelling the marker", "tools/thesis_plan.json",
         '{"note": "' + MARKER.replace(":", "\\u003a") + '"}'),
    )
    for label, rel, content in escape_cases:
        rc, _, err = run_hook(BOUNDARY, event("Write", r, file_path=str(r / rel),
                                              content=content))
        check(rc == 2, f"{label} is decoded and blocked (exit {rc})")
    check("escape or entity" in err, f"the message says it was an escape: {err!r}")

    for label, rel in (("an id in the file name", "docs/thesis/" + E_ID + ".md"),
                       ("an id in a directory name", "website/src/" + E_ID.lower() + "/a.ts"),
                       ("a Turkish letter in the file name",
                        "docs/thesis/" + TURKISH_WORD + ".md"),
                       ("a Turkish letter in an English-only file name",
                        "tools/publish/" + TURKISH_WORD + ".py")):
        rc, _, err = run_hook(BOUNDARY, event("Write", r, file_path=str(r / rel),
                                              content="Plain English.\n"))
        check(rc == 2 and "file name" in err, f"{label} is blocked (exit {rc})")

    section("guard_public_boundary: known limitations, pinned (asserted negatives)")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "docs/thesis/k.md"),
                                        content="x" + E_ID + "\n"))
    check(rc == 0, f"KNOWN LIMITATION: an id glued to a preceding letter (x{E_ID}) passes; "
                   f"that is what keeps TYPE-12 out (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "docs/thesis/k.md"),
                                        content="h" + A_CIRCUMFLEX + "l" + A_CIRCUMFLEX + "\n"))
    check(rc == 0, f"KNOWN LIMITATION: the circumflex vowels are not in the letter set "
                   f"(exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "docs/thesis/k.md"),
                                        content="ba\\u015far\n"))
    check(rc == 0, f"KNOWN LIMITATION: a \\u escape in Markdown is not decoded (it does not "
                   f"render there) (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "docs/thesis/k.md"),
                                        content="\u15c5DR-" + "012\n"))
    check(rc == 0, f"KNOWN LIMITATION: a look-alike from a script outside the folded set (a "
                   f"Canadian syllabics A) is not folded (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "website/src/k.tsx"),
                                        content='const s = <p>E{"-"}07</p>;\n'))
    check(rc == 0, f"KNOWN LIMITATION: an id assembled by code (E{{\"-\"}}07 in JSX) is not "
                   f"judged as it renders (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "website/src/k.tsx"),
                                        content="<p>E-<b x={() => ({a: {b: c > d}})}>"
                                                + "07</b></p>\n"))
    check(rc == 0, f"KNOWN LIMITATION: an attribute expression nested three braces deep is not "
                   f"read as one, so a '>' inside it hides the tag (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", r, file_path=str(r / "website/src/k.tsx"),
                                        content='<p>E-<b x={"}" + (a > b)}>' + "07</b></p>\n"))
    check(rc == 0, f"KNOWN LIMITATION: a brace inside a string in an attribute expression ends "
                   f"the group, so a '>' after it hides the tag (exit {rc})")
    try:
        cap = load_module("guard_public_boundary_cap", BOUNDARY).MAX_SIMULATED_BYTES
        huge = r / "docs" / "thesis" / "huge.md"
        with open(huge, "wb") as fh:
            fh.write(b"filler line\n" * (cap // 12 + 1))
            fh.write(b"see E|X\n")
        rc, _, _ = run_hook(BOUNDARY, event("Edit", r, file_path=str(huge), old_string="|X",
                                            new_string="-07"))
        check(rc == 0, f"KNOWN LIMITATION: an Edit to a file over the {cap // 1_000_000} MB "
                       f"simulation cap is judged by its new_string alone (exit {rc})")
        rc, _, _ = run_hook(BOUNDARY, event("Edit", r, file_path=str(huge), old_string="|X",
                                            new_string=E_ID))
        check(rc == 2, f"while an id in that new_string is still blocked (exit {rc})")
        huge.unlink()
    except Exception as e:
        check(False, f"could not run the size-cap probe: {type(e).__name__}: {e}")
    utf16 = tmp / "k-utf16.md"
    utf16.write_bytes(("see " + E_ID + " and " + TURKISH_WORD + "\n").encode("utf-16"))
    rc, _, _ = run_hook(BOUNDARY, event("mcp__Desktop_Commander__move_file", r,
                                        source=str(utf16), destination=str(r / "docs/thesis/u.md")))
    check(rc == 0, f"KNOWN LIMITATION: a moved file holding a NUL byte is judged by its name "
                   f"only, so UTF-16 text moves in unread (exit {rc})")

    section("guard_public_boundary: mirrors leak_check's English-only set")
    try:
        guard = load_module("guard_public_boundary_under_test", BOUNDARY)
        leak = load_module("leak_check_under_test", REPO / "tools" / "publish" / "leak_check.py")
        check(set(guard.ENGLISH_ONLY_EXACT) == {f.casefold() for f in leak.ENGLISH_ONLY_FILES},
              "ENGLISH_ONLY_EXACT == leak_check.ENGLISH_ONLY_FILES (case-folded)")
        check(set(guard.ENGLISH_ONLY_PREFIXES)
              == {d.casefold() for d in leak.ENGLISH_ONLY_DIRS},
              "ENGLISH_ONLY_PREFIXES == leak_check.ENGLISH_ONLY_DIRS (case-folded)")
        check(set(guard.TURKISH_LETTERS) == set(leak.TURKISH_RE.pattern.strip("[]")),
              "the Turkish letter set equals leak_check's")
        check(all(guard.is_english_only(p) for p in guard.PUBLIC_EXACT)
              and all(guard.is_english_only(p + "x") for p in guard.PUBLIC_PREFIXES),
              "every public path is also English-only")
    except Exception as e:
        check(False, f"could not compare with leak_check: {type(e).__name__}: {e}")

    section("guard_public_boundary: against the real repository (read-only)")
    rc, _, _ = run_hook(BOUNDARY, event("Write", REPO, file_path=str(REPO / "docs/thesis/zz.md"),
                                        content=TURKISH_WORD))
    check(rc == 2, f"the real docs/thesis/ is guarded (exit {rc})")
    rc, _, _ = run_hook(BOUNDARY, event("Write", REPO, file_path=str(REPO / "docs/thesis/zz.md"),
                                        content="Plain English.\n"))
    check(rc == 0, f"and clean English there is allowed (exit {rc})")
    check(not (REPO / "docs/thesis/zz.md").exists(), "no event wrote a file")

    src = BOUNDARY.read_bytes()
    check(src.isascii(), "guard_public_boundary.py is pure ASCII, as its comment says")
    check(MARKER.encode() not in src, "and does not itself carry the private marker")


# -----------------------------------------------------------------------------
# guard_tester_lane.py
# -----------------------------------------------------------------------------

def test_tester_lane(tmp: Path) -> None:
    section("guard_tester_lane: the D-031 paths are blocked for the tester")
    r = make_repo(tmp, "repo-tester")
    blocked = ("tools/publish/x.py", "tools/publish/test_hooks.py", "thesis/README.md",
               "thesis/src/a.py", "website/src/pages/index.astro", "website/package.json",
               ".github/workflows/governance.yml", "tools/thesis_plan.json",
               "tools/hooks/guard_public_boundary.py",
               # the pre-D-031 rules still hold
               "src/psyche_store.py", "run_tests.py", "CLAUDE.md", "tools/ledger.json",
               "docs/TEST_OUTPUT.txt")
    for rel in blocked:
        rc, _, err = run_hook(TESTER, event("Write", r, file_path=str(r / rel), content="x"))
        check(rc == 2, f"tester Write to {rel} is blocked (exit {rc})")
    check("LANE VIOLATION" in err, "the message is the lane-violation message")

    rc, _, _ = run_hook(TESTER, event("Edit", r, file_path=str(r / "tools/publish/x.py"),
                                      old_string="a", new_string="b"))
    check(rc == 2, f"tester Edit to tools/publish/x.py is blocked (exit {rc})")
    rc, _, _ = run_hook(TESTER, event("NotebookEdit", r,
                                      notebook_path=str(r / "website/src/demo.ipynb"),
                                      new_source="x"))
    check(rc == 2, f"tester NotebookEdit (notebook_path) under website/ is blocked (exit {rc})")
    rc, _, _ = run_hook(TESTER, event("Write", r, file_path="tools/publish/rel.py", content="x"))
    check(rc == 2, f"a relative path is resolved against cwd (exit {rc})")
    rc, _, _ = run_hook(TESTER, event("Write", r, file_path=str(r / "Tools/Publish/x.py"),
                                      content="x"))
    check(rc == 2, f"path case is folded (exit {rc})")

    rt = make_repo(tmp, "t-symlink")
    (rt / "tests").mkdir()
    t_out = tmp / "t-outside" / "x"
    t_out.mkdir(parents=True)
    os.symlink(t_out, rt / "tests" / "l2")
    rc, _, _ = run_hook(TESTER, event("Edit", rt, file_path=str(rt) + "/tests/l2/../../src/a.py",
                                      old_string="a", new_string="b"))
    check(rc == 2, f"'..' after a symlink: tests/l2/../../src/a.py is src/a.py, as the tool "
                   f"writes it (exit {rc})")
    home = tmp / "t-home"
    make_repo(home, "repo")
    rc, _, _ = run_hook(TESTER, event("Write", tmp, file_path="~/repo/src/a.py", content="x"),
                        env_extra={"HOME": str(home)})
    check(rc == 2, f"a leading '~' is read as the home directory (exit {rc})")

    section("guard_tester_lane: what the tester keeps, and no over-matching")
    rc, _, _ = run_hook(TESTER, event("Write", r,
                                      file_path=str(r / "tests/test_tester_0x_adversarial.py"),
                                      content="x"))
    check(rc == 0, f"the tester's own suite file is allowed (exit {rc})")
    rc, _, _ = run_hook(TESTER, event("Write", r, file_path=str(r / "tools/publishing_notes.md"),
                                      content="x"))
    check(rc == 0, f"the tools/publish/ prefix does not match tools/publishing_notes.md "
                   f"(exit {rc})")
    rc, _, _ = run_hook(TESTER, event("Write", r / "tests", file_path=str(r / "src/a.py"),
                                      content="x"),
                        env_extra={"CLAUDE_PROJECT_DIR": str(r)})
    check(rc == 2, f"a tester whose cwd is tests/ is still blocked from src/ (exit {rc})")

    section("guard_tester_lane: claim-bearing tools and failure modes")
    rc, _, _ = run_hook(TESTER, event("Bash", r, command="python3 tools/capture_run.py"))
    check(rc == 2, f"capture_run via Bash is still blocked (exit {rc})")
    rc, _, _ = run_hook(TESTER, event("Bash", r, command="python3 run_tests.py"))
    check(rc == 0, f"an ordinary command is allowed (exit {rc})")
    for label, stdin in (("malformed JSON", "{not json"), ("a JSON list", "[1]")):
        rc, _, _ = run_hook(TESTER, stdin)
        check(rc == 0, f"{label} -> exit 0 (got {rc})")

    section("guard_tester_lane: NFC/NFD spellings of the same directory")
    base = tmp / ("t-" + DIR_NFC)
    ru = make_repo(base, "repo")
    rc, _, _ = run_hook(TESTER, event("Write", unicodedata.normalize("NFD", str(ru)),
                                      file_path=unicodedata.normalize(
                                          "NFC", str(ru / "tools/publish/x.py")),
                                      content="x"))
    check(rc == 2, f"NFD cwd + NFC file_path is still blocked (exit {rc}); before D-031 "
                   f"the raw comparison failed and the guard allowed it")
    for label, env in (("PYTHONIOENCODING=ascii", {"PYTHONIOENCODING": "ascii"}),
                       ("PYTHONIOENCODING=latin-1", {"PYTHONIOENCODING": "latin-1"})):
        rc, _, _ = run_hook(TESTER, event("Write", ru, file_path=str(ru / "src/a.py"),
                                          content="x"), env_extra=env)
        check(rc == 2, f"a repo under a non-ASCII directory is still guarded under {label} "
                       f"(exit {rc})")

    section("guard_tester_lane: the tester cannot edit what binds it")
    for rel in ("tools/hooks/guard_tester_lane.py", "tools/hooks/post_edit_ledger.py",
                "tools/hooks/session_start_ledger.py", "tools/hooks/new_hook.py",
                "tools/ledger_check.py", "tools/capture_run.py", "tools/ledger_sync.py",
                ".claude/agents/tester.md", ".claude/settings.json",
                ".claude/settings.local.json", ".claude/skills/psyche-lane/SKILL.md"):
        rc, _, _ = run_hook(TESTER, event("Edit", r, file_path=str(r / rel),
                                          old_string="a", new_string="b"),
                            env_extra={"CLAUDE_PROJECT_DIR": str(r)})
        check(rc == 2, f"tester Edit to {rel} is blocked (exit {rc})")
    rc, _, _ = run_hook(TESTER, event("Write", r, file_path=str(r / "tools/test_ledger.py"),
                                      content="x"))
    check(rc == 0, f"no over-matching: tools/test_ledger.py is not on the list (exit {rc})")

    section("guard_tester_lane: nested worktrees under .claude/worktrees/")
    outer = make_repo(tmp, "t-outer")
    for name, marked in (("marked", True), ("unmarked", False)):
        w = outer / ".claude" / "worktrees" / name
        (w / "tools").mkdir(parents=True)
        if marked:
            (w / "tools" / "ledger.json").write_text("{}\n", encoding="utf-8")
        for cwd in (w, outer):
            for rel in ("src/psyche_store.py", "tools/publish/x.py", "website/src/a.tsx",
                        "thesis/README.md", "tools/hooks/guard_tester_lane.py"):
                rc, _, _ = run_hook(TESTER, event("Edit", cwd, file_path=str(w / rel),
                                                  old_string="a", new_string="b"),
                                    env_extra={"CLAUDE_PROJECT_DIR": str(outer)})
                check(rc == 2, f"{name} worktree, cwd {cwd.name}: {rel} is blocked "
                               f"(exit {rc})")
            rc, _, _ = run_hook(TESTER, event("Write", cwd,
                                              file_path=str(w / "tests/test_tester_x.py"),
                                              content="x"),
                                env_extra={"CLAUDE_PROJECT_DIR": str(outer)})
            check(rc == 0, f"{name} worktree, cwd {cwd.name}: the tester's own suite file "
                           f"is allowed (exit {rc})")
        rc, _, _ = run_hook(TESTER, event("Write", w, file_path="src/rel.py", content="x"),
                            env_extra={"CLAUDE_PROJECT_DIR": str(outer)})
        check(rc == 2, f"{name} worktree: a relative path is resolved against the worktree "
                       f"cwd (exit {rc})")

    sib_wt = make_repo(tmp, "t-wt-sibling")
    rc, _, _ = run_hook(TESTER, event("Edit", outer, file_path=str(sib_wt / "src/a.py"),
                                      old_string="a", new_string="b"),
                        env_extra={"CLAUDE_PROJECT_DIR": str(outer)})
    check(rc == 2, f"a worktree outside the repo (marked) is judged against its own root, "
                   f"even with cwd and CLAUDE_PROJECT_DIR on the main checkout (exit {rc})")

    section("guard_tester_lane: planted markers and unmarked checkouts")
    decoy = make_repo(tmp, "t-decoy")
    for planted, rel in (("tools/tools", "tools/thesis_plan.json"),
                         ("tools/tools", "tools/hooks/guard_tester_lane.py"),
                         ("docs/tools", "docs/TEST_OUTPUT.txt")):
        (decoy / planted).mkdir(parents=True, exist_ok=True)
        (decoy / planted / "ledger.json").write_text("{}", encoding="utf-8")
        rc, _, _ = run_hook(TESTER, event("Write", decoy, file_path=str(decoy / rel),
                                          content="x"))
        check(rc == 2, f"a tools/ledger.json planted at {planted}/ does not shorten {rel} "
                       f"to an allowed name (exit {rc})")
    bare = make_repo(tmp, "t-bare", marker=False)
    (bare / "tests").mkdir()
    rc, _, _ = run_hook(TESTER, event("Write", bare / "tests", file_path=str(bare / "src/a.py"),
                                      content="x"),
                        env_extra={"CLAUDE_PROJECT_DIR": str(bare)})
    check(rc == 2, f"no ledger anywhere: falls back to CLAUDE_PROJECT_DIR (exit {rc})")
    rc, _, _ = run_hook(TESTER, event("Write", bare, file_path=str(bare / "src/a.py"),
                                      content="x"))
    check(rc == 2, f"no ledger, no CLAUDE_PROJECT_DIR: falls back to cwd (exit {rc})")
    rc, _, _ = run_hook(TESTER, event("Write", bare / "tests",
                                      file_path=str(bare / "tests/test_tester_a.py"),
                                      content="x"),
                        env_extra={"CLAUDE_PROJECT_DIR": str(bare)})
    check(rc == 0, f"and the longest base wins, so tests/ stays the tester's (exit {rc})")
    for label, stdin in (("tool_input not a dict", json.dumps({"tool_input": "x"})),
                         ("command not a string",
                          json.dumps({"tool_input": {"command": ["capture_run.py"]}})),
                         ("file_path not a string",
                          json.dumps({"tool_input": {"file_path": 3}}))):
        rc, _, _ = run_hook(TESTER, stdin)
        check(rc == 0, f"{label} -> exit 0 (got {rc})")

    section("guard_tester_lane: a forbidden path changed through the shell is blocked")
    sh = make_repo(tmp, "t-shell")
    (sh / "tools" / "hooks").mkdir()
    (sh / "tools" / "hooks" / "guard_tester_lane.py").write_text("x\n", encoding="utf-8")
    (sh / "src").mkdir()
    (sh / "src" / "a.py").write_text("x\n", encoding="utf-8")
    (sh / "tests").mkdir()
    shell_blocked = (
        "sed -i '' 's/return block/return 0/' tools/hooks/guard_tester_lane.py",
        "cp /tmp/a .claude/agents/tester.md",
        "printf x > src/psyche_store.py",
        "echo x >src/a.py", "echo x >> tools/ledger.json", "echo x >| src/a.py",
        "echo x &> src/a.py", "echo x >& src/a.py", "python3 t.py 2> src/err.log",
        "python3 x.py > CLAUDE.md", "cat foo | tee src/a.py",
        "cat <<'EOF' > src/a.py\nx = 1\nEOF",
        "rm -rf tools/hooks", "rm -rf tools", "rm -- src/a.py", "rm src/*.py",
        "rm tools/*/guard_tester_lane.py", "rm -rf .",
        "mv src/psyche_store.py /tmp/", "mv tests/x.py src/", "cp -r /tmp/hooks tools/",
        "ln -sf /tmp/x src/a.py", "truncate -s 0 run_tests.py", "touch .claude/x",
        "mkdir -p thesis/x", "chmod 000 tools/hooks/guard_tester_lane.py",
        "perl -pi -e 's/a/b/' src/a.py", "dd if=/dev/zero of=src/a.py",
        "git checkout -- src/psyche_store.py", "git restore src/", "git checkout -- .",
        "git -C src checkout -- a.py", "git stash", "git apply fix.diff", "patch -p1 < fix.diff",
        "find . -name '*.py' -delete", "find /tmp -exec cp {} src/ \\;",
        "cd src && sed -i '' s/a/b/ psyche_store.py",
        "(cd /tmp && touch a); rm a.py src/b.py",
        "echo ok; touch website/x", "echo hi\nrm src/a.py",
        "bash -c \"echo x > src/a.py\"", "eval 'rm src/a.py'",
        "x=$(sed -i '' s/a/b/ src/a.py)", "echo \"$(rm src/a.py)\"", "`rm src/a.py`",
        "sudo rm src/a.py", "env X=1 rm src/a.py", "xargs -0 rm src/a.py",
    )
    for command in shell_blocked:
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=command))
        check(rc == 2 and "LANE VIOLATION" in err,
              f"tester Bash {command!r} is blocked (exit {rc})")
    rc, _, err = run_hook(TESTER, event("Bash", sh,
                                        command='echo x > "$CLAUDE_PROJECT_DIR/src/a.py"'),
                          env_extra={"CLAUDE_PROJECT_DIR": str(sh)})
    check(rc == 2, f"$CLAUDE_PROJECT_DIR in a path is expanded (exit {rc})")
    rc, _, _ = run_hook(TESTER, event("Bash", sh, command="rm -rf ~"),
                        env_extra={"HOME": str(tmp)})
    check(rc == 2, f"removing a directory above the repository (~) is blocked (exit {rc})")

    section("guard_tester_lane: a wrapper is read past its options and their values")
    # four of the first five exited 0 before the fix (nice -n 5 was already blocked): the
    # option's value was read as the command (reviewer follow-up, hooks-skills finding)
    wrapper_blocked = (
        "sudo -u me rm src/a.py", "env -u FOO rm src/a.py", "timeout -s KILL 10 rm src/a.py",
        "exec -a x rm src/a.py", "nice -n 5 rm src/a.py",
        # values written every way the option parsers accept them
        "sudo -g staff -u me rm src/a.py", "sudo --user me rm src/a.py",
        "sudo --user=me rm src/a.py", "sudo --us me rm src/a.py", "sudo -uroot rm src/a.py",
        "sudo -Eu me rm src/a.py", "sudo -- rm src/a.py", "doas -u me rm src/a.py",
        "env -i -u FOO X=1 rm src/a.py", "env - rm src/a.py", "env --unset=FOO rm src/a.py",
        "timeout --signal KILL 10 rm src/a.py", "timeout -k 5 -s KILL 10s rm src/a.py",
        "timeout -sKILL 10 rm src/a.py", "stdbuf -o L rm src/a.py", "stdbuf -oL tee src/a.py",
        "nice -n -5 rm src/a.py", "nice -5 rm src/a.py", "command -p rm src/a.py",
        "caffeinate -t 60 rm src/a.py", "time -p rm src/a.py", "setsid rm src/a.py",
        "arch -arm64 rm src/a.py",
        "sudo -u me env -u FOO nice -n 5 timeout -s KILL 10 stdbuf -o L rm src/a.py",
        # an option missing from the table: the next word is read as its value and as the
        # command, so neither reading hides the rm
        "sudo --frobnicate x rm src/a.py", "env --zz -u FOO rm src/a.py",
        "timeout --zz rm src/a.py",
        # values that do more than set a mode
        "env -C src rm a.py", "env --chdir=src rm a.py", "env -Csrc rm a.py",
        "sudo -D src rm a.py", "sudo --chdir=src rm a.py",
        "env -S 'rm src/a.py'", "env -S'rm -f' src/a.py", "env --split-string='rm src/a.py'",
        "env -i -S 'nice -n 5 rm' src/a.py",
        "/usr/bin/time -o src/a.py true", "time --output=src/a.py true",
        "sudo -e src/a.py", "sudo --edit -u me src/a.py", "sudoedit src/a.py",
        # a wrapper behind xargs, and a command named by xargs's input
        "ls src | xargs sudo -u me rm", "ls | xargs env", "ls | xargs sudo",
        "ls | xargs sudo -u", "ls | xargs timeout 10", "ls | xargs -I{} {}",
        "ls | xargs -I{} env -C {} rm a.py", "ls | xargs -I{} time -o {} true",
        "ls | xargs time -o", "ls | xargs sudo -e", "ls | xargs -I{} env -S {}",
        # a long flag written out in full is that flag, though it starts a valued option
        # (--login, --login-class); both exited 0 in fix round 1, which read --login as
        # taking a value (reviewer fix round 2)
        "sudo --login rm src/a.py", "sudo --login -u me rm src/a.py",
        "sudo --log rm src/a.py", "sudo --login-class x rm src/a.py",
        # "--" ends the options, not the reading: timeout's DURATION still follows it; the
        # first three exited 0 in fix round 1 (reviewer fix round 2)
        "timeout -- 10 rm src/a.py", "timeout -k5 -- 1 rm src/a.py",
        "timeout -s KILL -- 10 rm src/a.py", "env -u FOO -- X=1 rm src/a.py",
        "sudo -u -- rm src/a.py",
        # and the words after "--" are read with options on too, for a wrapper that does
        # not honour it (no wrapper here would run these, so blocking them costs nothing)
        "env -- -i rm src/a.py", "nice -- -n 5 rm src/a.py", "timeout -- 10 -- rm src/a.py",
        # a DURATION in any spelling strtod reads; each exited 0 before (reviewer fix round 2)
        "timeout inf rm src/a.py", "timeout infinity rm src/a.py", "timeout 1e3 rm src/a.py",
        "timeout 0x10 rm src/a.py", "timeout +5 rm src/a.py",
    )
    for command in wrapper_blocked:
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=command))
        check(rc == 2 and "LANE VIOLATION" in err,
              f"tester Bash {command!r} is blocked (exit {rc})")
    wrapper_allowed = (
        "sudo -u me cat src/a.py", "env -u FOO python3 run_tests.py",
        "timeout -s KILL 60 python3 run_tests.py", "nice -n 5 python3 run_tests.py",
        "exec -a x python3 -B tests/test_tester_x.py", "env -i grep -r rm src/",
        "timeout 300 grep -rn 'rm -rf' src/", "time -p python3 run_tests.py",
        "stdbuf -oL python3 run_tests.py | tee /tmp/log.txt",
        "env -S 'python3 -B tests/test_tester_x.py'", "env -C tests rm -f test_tester_x.py",
        "caffeinate -i -t 600 python3 run_tests.py", "command -v rm", "sudo -l",
        "/usr/bin/time -o /tmp/time.txt python3 run_tests.py",
        "ls | xargs", "ls src | xargs -0",
        "sudo --login cat src/a.py", "timeout -- 600 python3 run_tests.py",
        "timeout inf python3 run_tests.py", "timeout 1e3 python3 run_tests.py",
    )
    for command in wrapper_allowed:
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=command))
        check(rc == 0, f"tester Bash {command!r} is allowed (exit {rc}, {err[-120:]!r})")

    section("guard_tester_lane: past the nesting limit the command is refused")
    # past five levels the hook stops reading; before the fix that let the command through
    # (six evals of rm exited 0), now it fails closed
    deep = 5    # _MAX_DEPTH in guard_tester_lane.py

    def nest(levels: int, inner: str, how: str) -> str:
        for _ in range(levels):
            if how == "eval":
                inner = "eval " + inner
            elif how == "bash -c":
                inner = "bash -c '" + inner.replace("'", "'\\''") + "'"
            else:
                inner = "find tests -exec " + inner + " \\;"
        return inner

    for how in ("eval", "bash -c", "find -exec"):
        inner = "echo {}" if how == "find -exec" else "echo hi"
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=nest(deep + 1, inner, how)))
        check(rc == 2 and f"nested more than {deep} deep" in err,
              f"{how} nested {deep + 1} deep is refused even around a harmless command "
              f"(exit {rc})")
        rc, _, err = run_hook(TESTER, event("Bash", sh,
                                            command=nest(deep + 1, "rm src/a.py", how)))
        check(rc == 2, f"{how} nested {deep + 1} deep around rm src/a.py is refused "
                       f"(exit {rc})")
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=nest(deep, inner, how)))
        check(rc == 0, f"{how} nested {deep} deep around a harmless command is allowed: "
                       f"the limit is exact (exit {rc}, {err[-120:]!r})")
        rc, _, _ = run_hook(TESTER, event("Bash", sh, command=nest(deep, "rm src/a.py", how)))
        check(rc == 2, f"{how} nested {deep} deep around rm src/a.py is read and blocked "
                       f"(exit {rc})")
    rc, _, err = run_hook(TESTER, event("Bash", sh, command="eval " * 40 + "echo hi"))
    check(rc == 2 and f"nested more than {deep} deep" in err,
          f"forty evals are refused, not read to the bottom (exit {rc})")

    # a "$( )" inside a double-quoted "$( )" is read flat, at every level (the module
    # docstring, item 4): never refused for depth, and a write at the bottom is still read
    def quoted(levels: int, inner: str, escape: bool = False) -> str:
        for _ in range(levels):
            if escape:      # each level escapes the quotes of the level inside it
                inner = inner.replace("\\", "\\\\").replace('"', '\\"')
            inner = 'echo "$(' + inner + ')"'
        return inner

    for levels in (deep + 1, 40):
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=quoted(levels, "echo hi")))
        check(rc == 0, f"a double-quoted \"$( )\" nested {levels} deep around a harmless "
                       f"command is read flat and allowed (exit {rc}, {err[-120:]!r})")
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=quoted(levels, "rm src/a.py")))
        check(rc == 2 and "src/a.py" in err,
              f"a double-quoted \"$( )\" nested {levels} deep around rm src/a.py is read "
              f"flat and blocked by its path (exit {rc})")
    # escaped quotes keep the substitution inside one quoted word, which the lexer nests
    rc, _, err = run_hook(TESTER, event("Bash", sh,
                                        command=quoted(deep + 1, "echo hi", escape=True)))
    check(rc == 2 and f"nested more than {deep} deep" in err,
          f"a \"$( )\" nested {deep + 1} deep through escaped quotes is refused (exit {rc})")
    rc, _, err = run_hook(TESTER, event("Bash", sh,
                                        command=quoted(deep, "echo hi", escape=True)))
    check(rc == 0, f"a \"$( )\" nested {deep} deep through escaped quotes is allowed "
                   f"(exit {rc}, {err[-120:]!r})")

    section("guard_tester_lane: a nested backtick substitution is refused, not read")
    # the first five exited 0 before the fix: the lexer read the escaped inner backticks as
    # text, so the inner command was never read (reviewer fix round 4)
    for command in ("echo `echo \\`rm src/a.py\\``", "echo \"`echo \\`rm src/a.py\\``\"",
                    "x=`eval \\`echo rm src/a.py\\``", "`echo \\`rm src/a.py\\``",
                    "echo `sudo -u me echo \\`rm src/a.py\\``",
                    # the same inside a string a nested shell or eval reads
                    "bash -c 'echo `echo \\`rm src/a.py\\``'",
                    "eval 'echo `echo \\`rm src/a.py\\``'"):
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=command))
        check(rc == 2 and "a nested backtick substitution this hook does not read" in err,
              f"tester Bash {command!r} is refused as a nested backtick substitution "
              f"(exit {rc})")
    for command in ("echo `date`", "echo \"built `date`\"", "grep -n '\\`' src/a.py",
                    "echo 'use \\`ls\\`'", "echo a # \\`",
                    "cat > tests/test_tester_x.py <<'EOF'\nprint('\\`')\nEOF"):
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=command))
        check(rc == 0, f"tester Bash {command!r} is allowed: no escaped backtick outside "
                       f"single quotes, a comment or a here-document (exit {rc}, "
                       f"{err[-120:]!r})")
    rc, _, err = run_hook(TESTER, event("Bash", sh, command='echo "use \\`ls\\` to list"'))
    check(rc == 2 and "nested backtick" in err,
          f"FAIL-CLOSED COST: an escaped backtick printed inside double quotes is refused "
          f"though harmless; single quotes keep it (exit {rc})")

    section("guard_tester_lane: a command too long to read is refused, never timed out")
    # Claude Code lets a call through when its hook times out (15 s in tester.md). Before the
    # fix the first two took 17.9 s and 16.8 s; past the character limit they are refused
    # at once, and below it the work budget refuses them (reviewer fix round 4)
    too_long = (
        ("over the character limit", "env -Z " * 2000 + "rm src/a.py", "characters"),
        ("over the character limit", "sudo --zz " * 2000 + "rm src/a.py", "characters"),
        ("over the character limit", "env -Z " * 900 + "rm src/a.py", "characters"),
        ("over the character limit", "sudo --zz " * 800 + "rm src/a.py", "characters"),
        ("over the work budget", "env -Z " * 580 + "rm src/a.py", "steps of reading"),
        ("over the work budget", "sudo --zz " * 400 + "rm src/a.py", "steps of reading"),
        ("over the work budget", "env -Z eval " * 300 + "rm src/a.py", "steps of reading"),
        ("over the work budget", "find . -exec " * 60 + "rm src/a.py", "steps of reading"),
        ("over the work budget", "; ".join(f"cd d{i}" for i in range(17)) + "; rm a.py",
         "steps of reading"),
    )
    for label, command, limit in too_long:
        start = time.monotonic()
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=command))
        took = time.monotonic() - start
        check(rc == 2 and "a command too long for this hook to read" in err and limit in err,
              f"{label}: {command[:24]!r}... ({len(command)} characters) is refused as too "
              f"long to read (exit {rc}, {err[:160]!r})")
        check(took < 3, f"{label}: {command[:24]!r}... is decided in under 3 s "
                        f"({took:.2f} s)")
    for command in ("env -Z " * 10 + "python3 run_tests.py",
                    "python3 -B tests/test_tester_x.py " + "-k a " * 700,
                    "echo " + "x" * 4091, "; ".join(f"cd d{i}" for i in range(4)) + "; rm a.py"):
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=command))
        check(rc == 0, f"a long harmless command within both limits is allowed: "
                       f"{command[:24]!r}... ({len(command)} characters, exit {rc}, "
                       f"{err[-120:]!r})")
    # A reading reached by many wrappers is queued once; without that, these run past the
    # work budget and are refused (reviewer fix round 2: the mutant refused all of them)
    for command in ("env -Z " * 40 + "python3 run_tests.py",
                    "sudo --zz " * 40 + "python3 run_tests.py"):
        start = time.monotonic()
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=command))
        took = time.monotonic() - start
        check(rc == 0 and took < 3,
              f"a run of 40 wrappers behind an unknown option is read once per reading and "
              f"allowed: {command[:24]!r}... (exit {rc}, {took:.2f} s, {err[:160]!r})")
    # A glob is paid for by the directory entries it reads, not only by its matches. Before
    # the fix a pattern that scanned many directories and matched nothing cost almost
    # nothing, and eighteen of them over / took 16.1 s, past the 15 s timeout, so the rm
    # behind them would have run (reviewer fix round 2)
    wide = tmp / "t-wide"
    for i in range(60):
        for j in range(60):
            (wide / f"d{i}" / f"e{j}").mkdir(parents=True)
    command = f"cd '{wide}' && rm"
    n = 0
    while len(command) + len(f" */*/q{n}") + len("; rm src/a.py") <= 4096:
        command += f" */*/q{n}"
        n += 1
    command += "; rm src/a.py"
    start = time.monotonic()
    rc, _, err = run_hook(TESTER, event("Bash", sh, command=command))
    took = time.monotonic() - start
    check(rc == 2 and "a command too long for this hook to read" in err
          and "steps of reading" in err,
          f"{n} distinct globs that each scan 3600 directories and match nothing are refused "
          f"as too long to read, not judged one by one (exit {rc}, {err[:200]!r})")
    check(took < 3, f"{n} globs over a 60 x 60 tree are decided in under 3 s ({took:.2f} s)")
    rc, _, err = run_hook(TESTER, event("Bash", sh, command=f"cd '{wide}' && rm */*/q0"))
    check(rc == 0, f"one glob over the same tree is read within the budget and allowed "
                   f"(exit {rc}, {err[:160]!r})")
    rc, _, err = run_hook(TESTER, event("Bash", sh, command="rm tools/*/guard_tester_lane.py "
                                                            "tests/*/q0"))
    check(rc == 2 and "tools/hooks/guard_tester_lane.py" in err,
          f"a glob still finds the forbidden file it matches (exit {rc}, {err[:200]!r})")
    # The work no step counts (a system call slow on some filesystem) is bounded by a timer
    # that refuses the command after _MAX_SECONDS; here a judge made slow stands in for it
    if hasattr(signal, "setitimer"):
        guard = load_module("guard_tester_lane_timer", TESTER)

        def slow_judge(target, cwd):
            time.sleep(10)
            return []

        def callers_own(signum, frame):
            pass

        guard._MAX_SECONDS = 0.3
        guard.repo_relatives = slow_judge
        before = signal.signal(signal.SIGALRM, callers_own)
        try:
            start = time.monotonic()
            hit = guard.shell_hit("rm src/a.py", str(sh))
            took = time.monotonic() - start
            kept = signal.getsignal(signal.SIGALRM)
            pending = signal.getitimer(signal.ITIMER_REAL)[0]
        finally:
            signal.signal(signal.SIGALRM, before)
        check(hit == (None, "a command too long for this hook to read "
                            "(over 0.3 seconds of reading)") and took < 3,
              f"a reading still going after _MAX_SECONDS is refused as too long to read, "
              f"not left to the hook's timeout ({hit!r}, {took:.2f} s)")
        check(kept is callers_own and pending == 0,
              f"the timer is stopped and the caller's SIGALRM handler put back "
              f"({kept!r}, {pending})")
    rc, _, err = run_hook(TESTER, event("Bash", sh, command="echo " + "x" * 4092))
    check(rc == 2 and "over 4096 characters" in err,
          f"the character limit is exact: 4097 characters are refused (exit {rc})")
    heredoc = "cat > tests/test_tester_x.py <<'EOF'\n" + "x = 1\n" * 700 + "EOF"
    rc, _, err = run_hook(TESTER, event("Bash", sh, command=heredoc))
    check(rc == 2 and "Write tool" in err,
          f"FAIL-CLOSED COST: a here-document over 4096 characters is refused though "
          f"harmless, and the message points to the Write tool (exit {rc})")

    section("guard_tester_lane: a GNU tool under a g prefix is read as that tool")
    # MacPorts installs these in /opt/local/bin; the first four exited 0 before the fix
    # (reviewer fix round 4)
    for command in ("grm src/a.py", "gcp /tmp/x src/a.py", "gtimeout -s KILL 10 rm src/a.py",
                    "genv -u FOO rm src/a.py", "gnice -n 5 rm src/a.py",
                    "gstdbuf -oL rm src/a.py", "gnohup rm src/a.py", "gmv src/a.py /tmp/",
                    "gln -sf /tmp/x src/a.py", "echo x | gtee src/a.py", "gtouch src/a.py",
                    "gtruncate -s 0 src/a.py", "gchmod 000 src/a.py", "gunlink src/a.py",
                    "ginstall /tmp/x src/a.py", "gdd if=/dev/zero of=src/a.py",
                    "gsed -i s/a/b/ src/a.py", "gfind src -delete", "ls src | gxargs rm",
                    "gtime -o src/a.py true", "gpatch -p1 < fix.diff",
                    "/opt/local/bin/grm src/a.py", "sudo -u me grm src/a.py",
                    "gtimeout 10 genv -u FOO grm src/a.py"):
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=command))
        check(rc == 2 and "LANE VIOLATION" in err,
              f"tester Bash {command!r} is blocked (exit {rc})")
    for command in ("git status", "git rm --cached tests/test_tester_x.py",
                    "gcp src/a.py /tmp/x", "grep -rn rm src/", "gzip -k /tmp/x",
                    "gtimeout 60 python3 run_tests.py", "genv -u FOO python3 run_tests.py"):
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=command))
        check(rc == 0, f"tester Bash {command!r} is allowed (exit {rc}, {err[-120:]!r})")

    section("guard_tester_lane: git commands that change the working tree are blocked")
    # each of these exited 0 before the fix (reviewer round 2, finding 6 follow-up)
    git_blocked = (
        # paths read as git rm's are; none given means the whole tree
        "git clean -fd tools/hooks", "git clean -f src/a.py", "git -C . clean -fdx",
        "git clean -fdx", "git clean -f -e '*.log'", "git clean -fde tests",
        "git clean -fd -- src", "git checkout-index -f -- src/a.py", "git checkout-index -a -f",
        "git ls-files | git checkout-index -f --stdin",
        "git checkout-index --prefix=src/ -a",
        # refused outright: they rewrite paths this hook cannot name
        "git reset --hard", "git -C . reset --hard", "git reset --hard HEAD~1",
        "git reset -q --merge HEAD~1", "git reset --keep HEAD~1", "git reset --har",
        "git merge other", "git pull", "git rebase main", "git cherry-pick abc",
        "git revert abc", "git read-tree -u --reset HEAD", "git read-tree -mu HEAD",
        "git read-tree --index-output=src/a.py HEAD", "git -c x.y=z pull",
        "git checkout -f", "git checkout --force HEAD", "git checkout -qf main",
        "git switch -f main", "git switch --discard-changes main", "git switch --orphan x",
        "yes | git checkout -p", "yes | git checkout -p HEAD~1", "yes | git restore --patch",
        "git checkout --pathspec-from-file=list.txt", "git rm --pathspec-from-file list.txt",
        "git apply --stat --apply fix.diff", "ls src | xargs -0I {} rm {}",
        "git bisect start", "git bisect reset", "git sparse-checkout set docs",
        "git submodule update", "git submodule foreach 'rm -rf x'",
        "git difftool --dir-diff", "git mergetool", "git co src/a.py",
        "git -c alias.x='!rm src/a.py' x", "/usr/bin/git reset --hard",
        # a file a git command writes by option, or a directory it creates or removes
        "git diff --output=src/a.py", "git log -p --output src/a.py", "git diff --o=src/a.py",
        "git format-patch -o src HEAD~1", "git format-patch -ko src HEAD~1",
        "git format-patch --output-directory=.claude HEAD~1", "cd src && git format-patch -1",
        "git archive -o src/a.tar HEAD", "git archive --output=src/a.tar HEAD",
        "git bundle create src/a.bundle HEAD", "git config --file src/a.py a.b c",
        "git config -f tools/ledger.json a.b c", "git init src/x",
        # a subcommand it does not read is refused, this one among them (its name is
        # assembled: see the module docstring)
        "git " + "cl" + "one /tmp/r /tmp/r2",
        "cd src && git init", "git worktree add src/wt", "git worktree add .claude/worktrees/x",
        "git worktree remove .claude/worktrees/x", "git worktree move .claude/worktrees/x /tmp/y",
        # xargs appends paths that come from its input
        "ls src | xargs rm", "ls src | xargs -0 rm -f", "ls src | xargs -I {} rm {}",
        "ls src | xargs -n 1 -P 4 chmod 000", "git ls-files src | xargs git checkout --",
        "ls src | xargs sed -i '' s/a/b/", "ls | xargs -I{} find {} -delete",
        "ls src | xargs mv -t /tmp", "ls src | xargs -I{} sh -c 'rm {}'",
        "ls | xargs -I {} cp /tmp/x {}", "ls | xargs -I {} cp {} tools",
        "ls | xargs --replace=@ rm @", "ls src | xargs -i rm {}",
    )
    for command in git_blocked:
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=command))
        check(rc == 2 and "LANE VIOLATION" in err,
              f"tester Bash {command!r} is blocked (exit {rc})")

    section("guard_tester_lane: the shell stays usable for running and reading")
    shell_allowed = (
        "cat src/psyche_store.py", "grep \">\" src/psyche_store.py", "grep -rn \"rm -rf\" src/",
        "echo \"sed -i x src/a.py\"", "echo a # > src/a.py", "sed -n '1,20p' src/a.py",
        "perl -ne 'print' src/a.py", "git diff src/", "git log -- src/", "git status",
        "git show HEAD:tools/hooks/guard_tester_lane.py > /tmp/old.py",
        "diff <(git show HEAD:src/a.py) src/a.py", "git checkout -b test/x", "git stash list",
        "git apply --check fix.diff", "python3 run_tests.py",
        "python3 run_tests.py > /tmp/out.txt 2>&1",
        "python3 -B tests/test_tester_x.py 2>&1 | tee /tmp/log.txt",
        "cp src/psyche_store.py /tmp/copy.py", "cp -r src /tmp/srccopy",
        "cat > tests/test_tester_x.py <<'EOF'\nrm src/a.py\nmv src/a.py src/b.py\nEOF\necho done",
        "rm -rf /tmp/scratch", "rm tests/test_tester_x.py", "find tests -name '*.pyc' -delete",
        "mkdir -p tests/fixtures && touch tests/fixtures/a.txt", "ls src > /dev/null",
        # git that leaves forbidden paths alone
        "git clean -n", "git clean -nd tools", "git clean --dry-run -x", "git clean -fd tests",
        "git clean -fdx tests/fixtures", "git checkout-index --prefix=/tmp/old/ -a",
        "git reset", "git reset --soft HEAD~1", "git reset -- src/a.py", "git reset --mixed",
        "git merge-base HEAD main", "git switch -c test/x", "git worktree add /tmp/wt HEAD~1",
        "git worktree list", "git worktree remove /tmp/wt", "git format-patch --stdout -1",
        "git format-patch -o /tmp/patches HEAD~2", "git diff --output=/tmp/d.txt",
        "git diff --no-index /tmp/a src/a.py", "git log --oneline -5", "git log -S foo -- src",
        "git blame src/a.py", "git grep -n foo -- src", "git ls-files src", "git rev-parse HEAD",
        "git branch -a", "git stash show -p", "git bisect log", "git bisect",
        "git submodule status", "git sparse-checkout list", "git fetch", "git tag -l",
        "git add tests/test_tester_x.py", "git commit -m 'test(0x): adversarial suite'",
        "git config --get user.name", "git archive HEAD src > /tmp/src.tar",
        "git init /tmp/scratch-repo", "git -C /tmp/wt status",
        "git --no-pager log -1", "git help clean",
        "ls src | xargs grep -n foo", "ls src | xargs -I {} cp {} /tmp/scratch",
        "git ls-files src | xargs wc -l",
    )
    for command in shell_allowed:
        rc, _, err = run_hook(TESTER, event("Bash", sh, command=command))
        check(rc == 0, f"tester Bash {command!r} is allowed (exit {rc}, {err[-120:]!r})")

    section("guard_tester_lane: shell writes it does not see, pinned (asserted negatives)")
    # one pin for each example the module docstring's "Not seen" list names
    for label, command in (
            ("a write from inside a program", "python3 -c \"open('src/a.py','w').write('x')\""),
            ("a write from a script a program runs", "python3 /tmp/w.py"),
            ("a command git itself runs (a hook)",
             "printf 'rm src/a.py\\n' > .git/hooks/pre-commit && "
             "chmod +x .git/hooks/pre-commit && git commit -m x"),
            ("a command git itself runs (the pager git grep -O names)",
             "git grep -O'rm src/a.py' foo"),
            ("a path held in a shell variable", "f=src/a.py; echo x > $f"),
            ("a path built by brace expansion", "cp x {src,tests}/a.py"),
            ("a branch switch, which rewrites the working tree", "git checkout main"),
            ("a branch switch through git switch", "git switch main"),
            ("a command git itself runs (set with git -c)",
             "git -c core.fsmonitor='rm src/a.py' status"),
            ("a name xargs passes into a nested shell as \"$@\"",
             "ls src | xargs sh -c 'rm \"$@\"' sh"),
            ("a name xargs passes into a nested shell as its replace string",
             "ls src | xargs -I{} sh -c '{}'"),
            ("a command behind a wrapper not on the list (flock)", "flock /tmp/l rm src/a.py"),
            ("a command behind a wrapper not on the list (watch)", "watch 'rm src/a.py'"),
            ("a command behind a wrapper not on the list (script)",
             "script /dev/null rm src/a.py"),
            ("a command behind a wrapper not on the list (su -c)", "su -c 'rm src/a.py'")):
        rc, _, _ = run_hook(TESTER, event("Bash", sh, command=command))
        check(rc == 0, f"KNOWN LIMITATION: {label} ({command!r}) is not seen (exit {rc})")
    check((sh / "src" / "a.py").read_text(encoding="utf-8") == "x\n",
          "no shell event ran: the hook only reads the command")


# -----------------------------------------------------------------------------
# session_start_ledger.py
# -----------------------------------------------------------------------------

def _context(stdout: str) -> str:
    return json.loads(stdout)["hookSpecificOutput"]["additionalContext"]


def test_session_start(tmp: Path) -> None:
    section("session_start_ledger: program and plan lines")
    r = make_repo(tmp, "repo-session")
    ledger = {
        "tests": {"suites": 1, "assertions": 1, "failures": 0},
        "determinism": {}, "meaning_bar": {"status": "OPEN", "attempts": []},
        "bricks": {},
        "program": {"_README": "x",
                    "psyche": {"state": "paused", "since": "2026-10-23", "decision": "D-031"},
                    "thesis": {"state": "active", "since": "2026-10-23", "decision": "D-031"}},
    }
    (r / "tools" / "ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
    today = _dt.datetime.now(_dt.timezone.utc).date()
    plan = {
        "timezone": "UTC",
        "phases": [
            {"id": "P0", "title": "Setup", "start": (today - _dt.timedelta(days=3)).isoformat(),
             "end": (today + _dt.timedelta(days=10)).isoformat(), "gate": "A",
             "status": "active"},
            {"id": "P1", "title": "Next", "start": None, "end": None, "status": "planned"}],
        "gates": [
            {"id": "A", "title": "Novelty", "date": (today + _dt.timedelta(days=10)).isoformat(),
             "status": "upcoming"},
            {"id": "B", "title": "Later", "date": None, "date_rule": "after A",
             "status": "upcoming"}],
        "deadlines": [{"id": "dl", "due": None, "estimate": "spring", "status": "upcoming"}],
    }
    (r / "tools" / "thesis_plan.json").write_text(json.dumps(plan), encoding="utf-8")

    rc, out, _ = run_hook(SESSION, {"cwd": str(r)})
    check(rc == 0, f"exit 0 (got {rc})")
    ctx = _context(out) if rc == 0 and out else ""
    lines = ctx.splitlines()
    check(any("program      psyche: paused since 2026-10-23 (D-031) \u00b7 thesis: active" in ln
              for ln in lines), "the program line reads `psyche: paused since \u2026 (D-031) \u00b7 "
                                "thesis: active`")
    prog_at = next((i for i, ln in enumerate(lines) if "program" in ln), 99)
    tests_at = next((i for i, ln in enumerate(lines) if ln.strip().startswith("tests")), -1)
    check(prog_at < tests_at, "the program line comes before the existing test totals")
    m = re.search(r"today (\d{4}-\d{2}-\d{2})", ctx)
    check(m is not None, "the plan header states the date it counted from")
    if m:
        hook_today = _dt.date.fromisoformat(m.group(1))
        left = (_dt.date.fromisoformat(plan["gates"][0]["date"]) - hook_today).days
        check(f"next gate  A Novelty: {plan['gates'][0]['date']}, {left} days left" in ctx,
              f"the next gate shows its date and days left ({left})")
    check("phase      P0 Setup" in ctx and "(active, ends at gate A)" in ctx,
          "the current phase shows its id, title, dates and status")
    check("deadline   dl: date not set (estimate: spring)" in ctx,
          "an undated deadline shows its estimate")
    check("tests        1 suites" in ctx and "bricks:" in ctx, "the existing output is kept")
    check("ledger_check: tool error" in ctx,
          "a ledger_check that cannot run is reported as a tool error, not as clean")

    section("session_start_ledger: never blocks")
    (r / "tools" / "thesis_plan.json").write_text("{broken", encoding="utf-8")
    rc, out, _ = run_hook(SESSION, {"cwd": str(r)})
    check(rc == 0 and "could not be parsed" in _context(out),
          "a malformed plan is reported as a note, exit 0")
    (r / "tools" / "thesis_plan.json").write_text(json.dumps({"phases": "x", "gates": [1]}),
                                                  encoding="utf-8")
    rc, out, _ = run_hook(SESSION, {"cwd": str(r)})
    check(rc == 0 and "none active" in _context(out), "a plan of the wrong shape: exit 0")
    plan["timezone"] = "Mars/Olympus"
    (r / "tools" / "thesis_plan.json").write_text(json.dumps(plan), encoding="utf-8")
    rc, out, _ = run_hook(SESSION, {"cwd": str(r)})
    ctx = _context(out) if rc == 0 and out else ""
    check("(local time; no zone data for Mars/Olympus)" in ctx,
          "an unknown zone says it fell back to local time, as render_plan --status does")
    check("(Mars/Olympus)" not in ctx, "and does not print the zone as if it were used")
    plan["timezone"] = "UTC"
    (r / "tools" / "thesis_plan.json").write_text(json.dumps(plan), encoding="utf-8")

    for label, bad in (("a string", "paused"), ("a list", ["paused"]), ("a number", 7)):
        broken = dict(ledger, program={"psyche": bad,
                                       "thesis": {"state": "active", "since": "2026-10-23"}})
        (r / "tools" / "ledger.json").write_text(json.dumps(broken), encoding="utf-8")
        rc, out, err = run_hook(SESSION, {"cwd": str(r)})
        ctx = _context(out) if rc == 0 and out else ""
        check(rc == 0 and "tests        1 suites" in ctx and "bricks:" in ctx
              and "thesis plan" in ctx,
              f"program.psyche as {label}: exit 0 and the rest of the briefing is kept "
              f"(exit {rc}, {err[-200:]!r})")
        check("psyche: unreadable entry" in ctx and "thesis: active" in ctx,
              f"program.psyche as {label}: the entry is reported, not dropped")
    for label, bad in (("a string", "paused"), ("null", None), ("a list", ["paused"])):
        (r / "tools" / "ledger.json").write_text(
            json.dumps(dict(ledger, program=bad)), encoding="utf-8")
        rc, out, _ = run_hook(SESSION, {"cwd": str(r)})
        ctx = _context(out) if rc == 0 and out else ""
        check("tests        1 suites" in ctx, f"program as {label}: exit 0, briefing kept")
        check("program      unreadable (expected an object" in ctx,
              f"program as {label}: one note line says so, the state is not silently dropped")
    (r / "tools" / "ledger.json").write_text(
        json.dumps(dict(ledger, program={"_README": "x"})), encoding="utf-8")
    rc, out, _ = run_hook(SESSION, {"cwd": str(r)})
    check(rc == 0 and "program      no entries" in _context(out),
          "a program block that names no program says so")
    no_program = {k: v for k, v in ledger.items() if k != "program"}
    (r / "tools" / "ledger.json").write_text(json.dumps(no_program), encoding="utf-8")
    rc, out, _ = run_hook(SESSION, {"cwd": str(r)})
    check(rc == 0 and "  program  " not in _context(out),
          "a ledger from before D-031, with no program block, prints no program line")
    (r / "tools" / "ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
    bad_dates = dict(plan, gates=[{"id": "A", "title": "Novelty", "date": "2026-13-40",
                                   "status": "upcoming"}],
                     deadlines=[{"id": "dl", "due": "2026-02-30", "status": "upcoming"}])
    (r / "tools" / "thesis_plan.json").write_text(json.dumps(bad_dates), encoding="utf-8")
    rc, out, _ = run_hook(SESSION, {"cwd": str(r)})
    ctx = _context(out) if rc == 0 and out else ""
    check("next gate  A Novelty: date unreadable ('2026-13-40'" in ctx,
          "a gate date that cannot be read is reported as unreadable, not as unset")
    check("deadline   dl: date unreadable ('2026-02-30'" in ctx,
          "so is a deadline's")
    check("date not set" not in ctx, "neither is shown as a date that was never recorded")
    (r / "tools" / "thesis_plan.json").write_text(json.dumps(plan), encoding="utf-8")
    (r / "tools" / "ledger.json").write_text(
        json.dumps(dict(ledger, bricks={"0a": "BUILT"})), encoding="utf-8")
    rc, out, _ = run_hook(SESSION, {"cwd": str(r)})
    check(rc == 0 and "could not be built" in (_context(out) if out else ""),
          "a malformed brick entry: exit 0 with a one-line note, not a traceback")
    (r / "tools" / "ledger.json").write_text(json.dumps(ledger), encoding="utf-8")

    rn = make_repo(tmp / ("s-" + DIR_NFC), "repo")
    (rn / "tools" / "ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
    for label, env in (("PYTHONIOENCODING=ascii", {"PYTHONIOENCODING": "ascii"}),
                       ("PYTHONIOENCODING=latin-1", {"PYTHONIOENCODING": "latin-1"})):
        rc, out, _ = run_hook(SESSION, {"cwd": str(rn)}, env_extra=env, cwd=tmp)
        check(rc == 0 and out and "psyche: paused" in _context(out),
              f"a repo under a non-ASCII directory is still read under {label}")

    rc, _, _ = run_hook(SESSION, "{not json", cwd=r)
    check(rc == 0, f"malformed stdin -> exit 0 (got {rc})")
    rc, _, _ = run_hook(SESSION, json.dumps({"cwd": 5}), cwd=r)
    check(rc == 0, f"cwd not a string -> exit 0 (got {rc})")
    rc, _, _ = run_hook(SESSION, "[1]", cwd=r)
    check(rc == 0, f"a JSON list on stdin -> exit 0 (got {rc})")

    section("session_start_ledger: against the real repository (read-only)")
    rc, out, _ = run_hook(SESSION, {"cwd": str(REPO)})
    ctx = _context(out) if rc == 0 and out else ""
    real = json.loads((REPO / "tools" / "ledger.json").read_text(encoding="utf-8"))
    state = ((real.get("program") or {}).get("psyche") or {}).get("state")
    check(rc == 0 and f"psyche: {state}" in ctx, f"exit 0 and the live program state ({state})")
    check("thesis plan  tools/thesis_plan.json" in ctx and "next gate" in ctx,
          "the live plan lines are present")


# -----------------------------------------------------------------------------
# psyche-orient: the canonical-facts block
# -----------------------------------------------------------------------------

def test_orient(tmp: Path) -> None:
    section("psyche-orient: the canonical-facts block survives a malformed program entry")
    skill = (REPO / ".claude" / "skills" / "psyche-orient" / "SKILL.md").read_text(
        encoding="utf-8")
    blocks = re.findall(r"```!\n(.*?)\n```", skill, re.S)
    block_src = next((b for b in blocks if "<<'PY'" in b and "BRICKS" in b), None)
    check(block_src is not None, "the facts block is found in the skill")
    if block_src is None:
        return
    r = make_repo(tmp, "repo-orient")
    base = {
        "tests": {"suites": 2, "assertions": 9, "failures": 0, "captured_at": "2026-10-23",
                  "captured_python": "3.12"},
        "determinism": {"hash_seeds": 5, "interpreters_swept": ["3.12"],
                        "interpreters_required": ["3.12"]},
        "meaning_bar": {"status": "OPEN", "attempts": [{"id": "1e", "wall": "CIRCULAR"}]},
        "bricks": {"0a": {"status": "PROVEN", "name": "store"}},
    }
    cases = (
        ("a valid program", {"psyche": {"state": "paused", "since": "2026-10-23",
                                        "decision": "D-031"}},
         "Psyche (paused) since 2026-10-23 (D-031)"),
        ("program.psyche a string", {"psyche": "paused"}, "program entry unreadable"),
        ("program.psyche a list", {"psyche": ["paused"]}, "program entry unreadable"),
        ("program a string", "paused", "program entry unreadable"),
        ("no program", None, "state unknown"),
    )
    for label, program, want in cases:
        ledger = dict(base)
        if program is not None:
            ledger["program"] = program
        (r / "tools" / "ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        env["CLAUDE_PROJECT_DIR"] = str(r)
        p = subprocess.run(["/bin/sh", "-c", block_src], capture_output=True, timeout=60,
                           env=env)
        out = p.stdout.decode("utf-8", "replace")
        check(want in out, f"{label}: the program line reads {want!r} ({out[:80]!r})")
        check("(no ledger)" not in out and "TESTS       2 suites" in out and "BRICKS" in out,
              f"{label}: the tests and bricks are still shown")


# -----------------------------------------------------------------------------
# wiring
# -----------------------------------------------------------------------------

def test_wiring() -> None:
    section("settings.json and the tester agent wire the guards")
    s = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    pre = s.get("hooks", {}).get("PreToolUse", [])
    entry = next((e for e in pre if any("guard_public_boundary.py" in h.get("command", "")
                                        for h in e.get("hooks", []))), None)
    check(entry is not None, "guard_public_boundary.py is registered as a PreToolUse hook")
    if entry:
        matcher = entry.get("matcher", "")
        try:
            rx = re.compile(matcher)
        except re.error as e:
            rx = None
            check(False, f"the matcher is a valid regular expression: {e}")

        def routed(name: str):
            # the same answer whether the host anchors the pattern or searches with it
            return (rx.search(name) is not None, re.fullmatch(f"(?:{matcher})", name) is not None)
        if rx is not None:
            for name in ("Write", "Edit", "MultiEdit", "NotebookEdit",
                         "mcp__Desktop_Commander__write_file", "mcp__Desktop_Commander__edit_block",
                         "mcp__Desktop_Commander__move_file",
                         "mcp__Desktop_Commander__create_directory",
                         "mcp__Desktop_Commander__write_pdf", "mcp__filesystem__write_file",
                         "mcp__filesystem__edit_file", "mcp__plugin_x_fs__create_file"):
                check(routed(name) == (True, True), f"the guard runs for {name}")
            for name in ("Read", "Bash", "Glob", "WebFetch", "Writer", "NotebookRead",
                         "mcp__Desktop_Commander__read_file",
                         "mcp__Desktop_Commander__write_file_v2", "mcp__x__rewrite_file",
                         "mcp__Desktop_Commander__start_process"):
                check(routed(name) == (False, False), f"and not for {name}")
    perms = s.get("permissions", {})
    check("Bash(git push:*)" in perms.get("deny", []), "the git push deny is kept")
    for a in ("Bash(python3 tools/publish/render_plan.py:*)",
              "Bash(python3 tools/publish/ci_c2.py:*)"):
        check(a in perms.get("allow", []), f"{a} is allowed")
    check("SessionStart" in s.get("hooks", {}) and "PostToolUse" in s.get("hooks", {}),
          "the existing SessionStart and PostToolUse hooks are kept")
    tester = (REPO / ".claude" / "agents" / "tester.md").read_text(encoding="utf-8")
    check("guard_tester_lane.py" in tester and "MultiEdit" in tester,
          "the tester's lane guard also matches MultiEdit")
    lane = (REPO / ".claude" / "skills" / "psyche-lane" / "SKILL.md").read_text(encoding="utf-8")
    guard_doc = TESTER.read_text(encoding="utf-8")
    for label, text in (("tester.md", tester), ("psyche-lane SKILL.md", lane),
                        ("guard_tester_lane.py", guard_doc)):
        flat = " ".join(text.split())
        check("python -c" in flat and "shell variable" in flat,
              f"{label} states what the lane hook does not see through the shell")
        check(all(t in flat for t in ("reset --hard", "clean", "checkout-index", "xargs",
                                      "git switch <branch>", "git -c")),
              f"{label} names the git forms the lane hook reads, refuses and does not see")

    section("settings.json: the guard command fails open when the hook cannot run")
    command = entry["hooks"][0]["command"] if entry else ""
    shells = [sh for sh in ("/bin/sh", "/bin/bash", "/bin/zsh") if Path(sh).exists()]
    empty = Path(tempfile.mkdtemp(prefix="hooks-wiring-"))
    blocking = json.dumps(event("Write", REPO, file_path=str(REPO / "docs/thesis/zz.md"),
                                content=TURKISH_WORD), ensure_ascii=False).encode("utf-8")
    clean = json.dumps(event("Write", REPO, file_path=str(REPO / "docs/thesis/zz.md"),
                             content="Plain English.\n")).encode("utf-8")
    try:
        for sh in shells:
            def run(env_dir, data):
                env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
                if env_dir is not None:
                    env["CLAUDE_PROJECT_DIR"] = str(env_dir)
                return subprocess.run([sh, "-c", command], input=data, capture_output=True,
                                      timeout=60, env=env).returncode
            rc = run(empty, blocking)
            check(rc == 0, f"{sh}: script missing under CLAUDE_PROJECT_DIR -> exit 0 (got {rc})")
            rc = run(None, blocking)
            check(rc == 0, f"{sh}: CLAUDE_PROJECT_DIR unset -> exit 0 (got {rc})")
            rc = run(REPO, blocking)
            check(rc == 2, f"{sh}: with the script present a real block still exits 2 "
                           f"(got {rc})")
            rc = run(REPO, clean)
            check(rc == 0, f"{sh}: and clean text exits 0 (got {rc})")
    finally:
        shutil.rmtree(empty, ignore_errors=True)
    check(not (REPO / "docs/thesis/zz.md").exists(), "no wiring run wrote a file")


def main() -> int:
    print("=" * 70)
    print("  GOVERNANCE HOOKS - TEST SUITE")
    print("=" * 70)
    tmp = Path(tempfile.mkdtemp(prefix="hooks-test-"))
    try:
        test_boundary(tmp)
        test_tester_lane(tmp)
        test_session_start(tmp)
        test_orient(tmp)
        test_wiring()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nRESULT: {PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
