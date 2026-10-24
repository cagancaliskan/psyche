# ledger:ignore-file — the fixtures below plant counts and claim terms on purpose.
"""test_checks.py — suite for check_copy.py, check_disclosure.py, leak_check.py and
decode_denylist.py.

Uses the project's own harness convention (as tools/test_ledger.py does): no pytest, prints
`RESULT: N passed, M failed`, exits non-zero on any failure. Run as a script:

    python3 -B tools/publish/test_checks.py

Every test builds a throwaway repository in a temp directory, so the real one is never
touched. The leak_check tests build a real git repository there, with git's global and
system configuration switched off so the user's settings cannot change the result.

Fixture text that would itself trip a check (a claim term, a private id, a home-directory
path, a Turkish letter, a tag-shaped token) is assembled by concatenation or written with
escapes, so this file contains none of it literally. The denylist fixtures and the tag-shaped
token are invented words, never entries of the real private list.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Dict, List, Optional

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent


def _load(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


CC = _load("check_copy")
CD = _load("check_disclosure")
LK = _load("leak_check")

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


# ─────────────────────────────────────────────────────────────────────────────
# fixture text, assembled so this file never contains it literally
# ─────────────────────────────────────────────────────────────────────────────

CLAIM = "is con" + "scious"                 # a ledger forbidden_claim_terms entry
CLAIM2 = "is a mi" + "nd"
RESEARCH_TERM = "the model th" + "inks"            # a research_forbidden_claim_terms entry
FIRST = "is the fir" + "st"
TR_G = "\u011f"                             # g with breve
TR_C = "\u00e7"                             # c with cedilla
TR_DOTTED_I = "\u0130"
HOME = "/" + "Users" + "/someone/project"
EXP_ID = "E-" + "07"
ADR_ID = "ADR-" + "001"
Q_ID = "Q-M-" + "3"
TAG = "[" + "QAZ" + "\u015e" + "UX]"          # invented: only the tag SHAPE is checked
THINKS = RESEARCH_TERM[len("the model "):]

BASE_LEDGER = {
    "schema_version": 1,
    "tests": {"suites": 2, "assertions": 30, "failures": 0,
              "per_suite": {"test_a.py": 10, "test_b.py": 20}},
    "bricks": {},
    "valid_statuses": ["PROVEN"],
    "forbidden_claim_terms": [CLAIM, CLAIM2],
    "research_forbidden_claim_terms": {"_README": "fixture", "terms": [RESEARCH_TERM, FIRST]},
    "claim_quarantine_paths": [],
    "count_quarantine_paths": [],
}


def make_repo(tmp: Path, files: Optional[Dict[str, str]] = None,
              ledger: Optional[dict] = None) -> Path:
    root = tmp / f"repo{len(list(tmp.iterdir()))}"
    (root / "tools").mkdir(parents=True)
    (root / "tools" / "ledger.json").write_text(
        json.dumps(BASE_LEDGER if ledger is None else ledger, indent=2), encoding="utf-8")
    for rel, body in (files or {}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return root


def run_py(script: str, *args: str, env: Optional[dict] = None,
           cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(HERE / script), *args],
                          capture_output=True, text=True, env=env, cwd=cwd)


def copy_findings(root: Path) -> List:
    findings, _, _ = CC.run(root)
    return findings


def rules_at(findings, path: str, line: Optional[int] = None) -> List[str]:
    return [f.rule for f in findings
            if f.path == path and (line is None or f.line == line)]


# ─────────────────────────────────────────────────────────────────────────────
# check_copy
# ─────────────────────────────────────────────────────────────────────────────

def test_check_copy(tmp: Path) -> None:
    section("check_copy: missing surfaces are fine")
    r = make_repo(tmp)
    check(copy_findings(r) == [], "a repository with no surfaces at all is clean")
    p = run_py("check_copy.py", "--root", str(r))
    check(p.returncode == 0, f"and exits 0 (got {p.returncode}: {p.stderr.strip()})")

    section("check_copy: CLAIM — forbidden term caught, negated term passes")
    r = make_repo(tmp, files={
        "website/src/components/Hero.tsx":
            "export const Hero = () => <p>The substrate " + CLAIM + ".</p>;\n",
        "website/src/pages/about.astro":
            "<p>We make no claim that the substrate " + CLAIM + ".</p>\n",
        "website/src/pages/wrapped.astro":
            "<p>This page does not say\nthat it " + CLAIM + ".</p>\n",
        "website/src/pages/pragma.astro":
            "<!-- ledger:allow-claim -->\n<blockquote>it " + CLAIM2 + "</blockquote>\n",
    })
    f = copy_findings(r)
    check(rules_at(f, "website/src/components/Hero.tsx", 1) == ["CLAIM"],
          "an asserted forbidden term in a .tsx component is a CLAIM finding at line 1")
    check(rules_at(f, "website/src/pages/about.astro") == [],
          "the same term after a negation cue passes")
    check(rules_at(f, "website/src/pages/wrapped.astro") == [],
          "a negation on the previous line governs a hard-wrapped term (C4's window)")
    check(rules_at(f, "website/src/pages/pragma.astro") == [],
          "ledger:allow-claim on the line above permits one quotation")

    section("check_copy: RESEARCH terms on copy surfaces and research prose")
    r = make_repo(tmp, files={
        "website/src/pages/index.astro": "<h1>Here " + RESEARCH_TERM + " in maps.</h1>\n",
        "docs/research/overview.md": "# Overview\n\nWe never say " + RESEARCH_TERM + ".\n",
        "docs/research/claims.md": "Line one.\nThis work " + FIRST + " of its kind.\n",
        "README.md": "Intro.\n\nThe model " + FIRST + " here.\n",
        "cogmap/sub/notes.md": "In short " + RESEARCH_TERM + ".\n",
        "docs/other.md": "Not a research surface: " + RESEARCH_TERM + ".\n",
        "MOC.md": "Plain English only.\n",
    })
    f = copy_findings(r)
    check("RESEARCH" in rules_at(f, "website/src/pages/index.astro", 1),
          "a research term on a page is a RESEARCH finding")
    check(rules_at(f, "docs/research/overview.md") == [], "a negated research term passes")
    check(rules_at(f, "docs/research/claims.md", 2) == ["RESEARCH"],
          "an asserted research term in docs/research/*.md is caught at its line")
    check(rules_at(f, "README.md", 3) == ["RESEARCH"], "README.md is a research surface")
    check(rules_at(f, "cogmap/sub/notes.md", 1) == ["RESEARCH"],
          "cogmap/**/*.md is walked recursively")
    check(rules_at(f, "docs/other.md") == [],
          "docs/other.md is not a check_copy surface (ledger_check's job)")
    check(rules_at(f, "MOC.md") == [], "clean MOC.md has no finding")

    section("check_copy: COUNT — count mismatch caught, ledger figures pass")
    r = make_repo(tmp, files={
        "website/src/pages/status.astro": "\n".join([
            "<p>618 assertions</p>",           # 1 wrong total
            "<p>30 assertions in 2 suites</p>",  # 2 correct
            "<p>10 passed</p>",                # 3 a per-suite figure
            "<p>5 suites</p>",                 # 4 wrong suite count
            "<!-- ledger:allow-count -->",     # 5
            "<p>1,372 assertions (historical)</p>",  # 6 permitted by pragma
            "<p>{t.suites} suites</p>",        # 7 rendered from data, no digit
        ]) + "\n",
        "docs/research/x.md": "618 assertions\n",
    })
    f = copy_findings(r)
    check(rules_at(f, "website/src/pages/status.astro", 1) == ["COUNT"],
          "a stale assertion total on a page is a COUNT finding")
    check(rules_at(f, "website/src/pages/status.astro", 2) == [],
          "the ledger's total and suite count pass")
    check(rules_at(f, "website/src/pages/status.astro", 3) == [],
          "a per-suite figure passes, exactly as in C2")
    check(rules_at(f, "website/src/pages/status.astro", 4) == ["COUNT"],
          "a wrong suite count is caught")
    check(rules_at(f, "website/src/pages/status.astro", 6) == [],
          "ledger:allow-count permits a labelled historical figure")
    check(rules_at(f, "website/src/pages/status.astro", 7) == [],
          "a count rendered from data carries no digit and passes")
    check(rules_at(f, "docs/research/x.md") == [],
          "COUNT is not re-applied to Markdown, which ledger_check C2 already checks")

    section("check_copy: ENERGY — figures and multiples caught")
    r = make_repo(tmp, files={
        "website/src/diagrams/energy.mmd": "\n".join([
            "flowchart LR",
            "  a[about 3.2 pJ per operation]",  # 2
            "  b[10x fewer operations]",        # 3
            "  c[10 \u00d7 less]",              # 4
            "  d[40% fewer synaptic events]",   # 5
            "  e[pJ per synaptic operation]",   # 6 unit with no number
            "  f[2x faster build]",             # 7 not an efficiency claim
            "  g[5 times less]",                # 8
        ]) + "\n",
    })
    f = copy_findings(r)
    for line, label in ((2, "an energy figure in pJ"), (3, "an 'Nx fewer' multiple"),
                        (4, "an 'N x less' multiple with the multiplication sign"),
                        (5, "a percentage reduction"), (8, "an 'N times less' multiple")):
        check(rules_at(f, "website/src/diagrams/energy.mmd", line) == ["ENERGY"],
              f"{label} is an ENERGY finding (line {line})")
    check(rules_at(f, "website/src/diagrams/energy.mmd", 6) == [], "a unit with no number passes")
    check(rules_at(f, "website/src/diagrams/energy.mmd", 7) == [],
          "a multiple that is not 'fewer/less' passes")
    r = make_repo(tmp, files={"docs/research/claims-and-scope.md": "It costs 4 nJ.\n"})
    check(rules_at(copy_findings(r), "docs/research/claims-and-scope.md", 1) == ["ENERGY"],
          "ENERGY applies to research prose too")

    section("check_copy: LANGUAGE — Turkish letters caught")
    r = make_repo(tmp, files={
        "website/src/diagrams/flow.mmd": "flowchart LR\n  a[ba" + TR_G + "lam]\n  b[context]\n",
        "website/src/lib/x.ts": "export const label = 'sa" + TR_C + "ma';\n",
        "docs/research/README.md": "# Research\n\n" + TR_DOTTED_I + "stanbul\n",
    })
    f = copy_findings(r)
    check(rules_at(f, "website/src/diagrams/flow.mmd", 2) == ["LANGUAGE"],
          "a Turkish letter in a Mermaid source is a LANGUAGE finding")
    check(rules_at(f, "website/src/diagrams/flow.mmd", 3) == [], "an ASCII line passes")
    check(rules_at(f, "website/src/lib/x.ts", 1) == ["LANGUAGE"],
          "and in a .ts string")
    check(rules_at(f, "docs/research/README.md", 3) == ["LANGUAGE"],
          "and in research prose (capital dotted I)")
    msgs = [x.message for x in f if x.path == "website/src/diagrams/flow.mmd"]
    check(bool(msgs) and "U+011F" in msgs[0] and TR_G not in msgs[0],
          "the message names the code point and stays ASCII")

    section("check_copy: SVG text nodes")
    svg = "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" id="618-suites">',  # 1 attribute only
        "  <title>Battery</title>",                                  # 2
        "  <text x='1'>618 assertions</text>",                       # 3
        "  <text><tspan>The network</tspan> <tspan>" + RESEARCH_TERM[len("the model "):]
        + "</tspan></text>",                                         # 4 split, no term
        "  <g aria-label='ma" + TR_G + "ara'/>",                     # 5 accessible name
        "  <desc>an estimate of 7 pJ</desc>",                        # 6
        "</svg>",
    ]) + "\n"
    r = make_repo(tmp, files={"docs/assets/battery.svg": svg})
    f = copy_findings(r)
    check(rules_at(f, "docs/assets/battery.svg", 1) == [],
          "an id attribute is not text and is not scanned")
    check(rules_at(f, "docs/assets/battery.svg", 3) == ["COUNT"],
          "a count in a <text> node is caught at its source line")
    check(rules_at(f, "docs/assets/battery.svg", 5) == ["LANGUAGE"],
          "an aria-label counts as copy")
    check(rules_at(f, "docs/assets/battery.svg", 6) == ["ENERGY"],
          "a <desc> node counts as copy")
    pairs = CC.svg_text(svg.encode("utf-8"), "x")
    check(any("The network" in t and t.endswith(RESEARCH_TERM[len("the model "):])
              for _, t in pairs),
          "adjacent tspans on one line read as rendered text")
    r = make_repo(tmp, files={"docs/assets/broken.svg": "<svg><text>oops</svg>\n"})
    p = run_py("check_copy.py", "--root", str(r))
    check(p.returncode == 2, f"a malformed SVG exits 2, never clean (got {p.returncode})")

    section("check_copy: every string value of the research plan")
    plan = {
        "_README": ["plain"],
        "phases": [{"id": "P0", "title": "Setup", "start": "2026-10-23", "weeks": 3,
                    "outputs": ["a map " + RESEARCH_TERM[len("the model "):],
                                "The model " + RESEARCH_TERM[len("the model "):] + " here",
                                "ana" + TR_G + "ac"]}],
        "gates": [{"id": "A", "question": "Does it pass 618 assertions?"}],
    }
    text = json.dumps(plan, indent=2, ensure_ascii=False)
    r = make_repo(tmp, files={"tools/research_plan.json": text})
    lines = text.splitlines()
    want_research = next(i for i, ln in enumerate(lines, 1) if "The model" in ln)
    want_tr = next(i for i, ln in enumerate(lines, 1) if TR_G in ln)
    want_count = next(i for i, ln in enumerate(lines, 1) if "618" in ln)
    f = [x for x in copy_findings(r) if x.path == "tools/research_plan.json"]
    check(sorted((x.line, x.rule) for x in f)
          == sorted([(want_research, "RESEARCH"), (want_tr, "LANGUAGE"),
                     (want_count, "COUNT")]),
          f"exactly the research term, the Turkish letter and the count are found, each "
          f"at its JSON line (got {[(x.line, x.rule) for x in f]})")
    check(any("(at /phases/0/outputs/1)" in x.message for x in f),
          "a plan finding names its JSON pointer")
    r = make_repo(tmp, files={"tools/research_plan.json": "{ not json"})
    p = run_py("check_copy.py", "--root", str(r))
    check(p.returncode == 2, "an unparseable plan exits 2")

    section("check_copy: staged copies and node_modules are not surfaces")
    r = make_repo(tmp, files={
        "website/src/content/docs/staged.mdx": "618 assertions; " + RESEARCH_TERM + "\n",
        "website/src/content/docs/deep/page.astro": "618 assertions\n",
        "website/src/node_modules/pkg/index.ts": "618 assertions\n",
        "website/node_modules/pkg/index.tsx": "618 assertions\n",
        "website/src/content/other.mdx": "618 assertions\n",
    })
    f = copy_findings(r)
    check(not any(x.path.startswith("website/src/content/docs/") for x in f),
          "website/src/content/docs/ (staged copies) is excluded")
    check(not any("node_modules" in x.path for x in f), "node_modules is excluded")
    check(rules_at(f, "website/src/content/other.mdx", 1) == ["COUNT"],
          "but the rest of website/src/content/ is scanned")

    section("check_copy: ledger plumbing and the CLI contract")
    led = dict(BASE_LEDGER)
    led.pop("research_forbidden_claim_terms")
    r = make_repo(tmp, ledger=led, files={"website/src/a.ts": "const x = 1;\n"})
    p = run_py("check_copy.py", "--root", str(r))
    check(p.returncode == 2 and "research_forbidden_claim_terms" in p.stderr,
          "a ledger without research terms is invalid since D-031: exit 2, never a notice")
    led = dict(BASE_LEDGER)
    led["research_forbidden_claim_terms"] = [RESEARCH_TERM]
    r = make_repo(tmp, ledger=led, files={"website/src/a.ts": "// " + RESEARCH_TERM + "\n"})
    check(rules_at(copy_findings(r), "website/src/a.ts") == ["RESEARCH"],
          "the research terms may also be a plain list")
    r = make_repo(tmp, files={
        "website/src/a.tsx": "<p>618 assertions</p>\n<p>It " + CLAIM + "</p>\n"})
    p = run_py("check_copy.py", "--root", str(r), "--quiet")
    out = p.stdout.splitlines()
    check(p.returncode == 1, f"findings exit 1 (got {p.returncode})")
    check(out == ["website/src/a.tsx:1: [COUNT] says 618 assertions; that is neither the "
                  "total (30) nor any per-suite count",
                  "website/src/a.tsx:2: [CLAIM] forbidden claim term " + repr(CLAIM)
                  + " asserted without negation (CONTRIBUTING.md rule 1)"],
          f"output is exactly `path:line: [RULE] message`, sorted (got {out})")
    empty = tmp / "no-ledger"
    empty.mkdir()
    p = run_py("check_copy.py", "--root", str(empty))
    check(p.returncode == 2, "no ledger exits 2")
    check(CC.LC.__name__ == "ledger_check" and CC.LC.COUNT_RE.pattern
          and CC.LC.COUNT_RE.search("618 assertions") is not None,
          "check_copy imports tools/ledger_check.py and matches counts with its COUNT_RE")
    # the negation cues are ledger_check's: a cue added there negates here, once Rules is
    # rebuilt, without any change to check_copy
    saved = CC.LC.NEGATION_CUES
    try:
        CC.LC.NEGATION_CUES = tuple(saved) + ("zorbly",)
        patched = CC.Rules(BASE_LEDGER)
        low = ["we zorbly say " + RESEARCH_TERM]
        negated_new = patched.negated(low, 0, low[0].index(RESEARCH_TERM))
    finally:
        CC.LC.NEGATION_CUES = saved
    plain = CC.Rules(BASE_LEDGER)
    check(negated_new and not plain.negated(low, 0, low[0].index(RESEARCH_TERM)),
          "check_copy's negation follows ledger_check.NEGATION_CUES (a cue patched in "
          "there negates a term here; without it, the term is asserted)")


# ─────────────────────────────────────────────────────────────────────────────
# check_disclosure
# ─────────────────────────────────────────────────────────────────────────────

# Invented words. Entry numbers: #1 phrase, #2 regex, #3 single word, #4 a word with a
# Turkish letter, written in the list DECOMPOSED (g + combining breve, as macOS may save it).
BLORP_NFC = "blo" + "\u011f" + "rp"
BLORP_NFD = "blo" + "g\u0306" + "rp"
DENY_WORDS = ("zephyr", "moss", "glint", "qx-", "blo")
DENYLIST = "\n".join([
    "# private terms (fixture)",
    "",
    "Zephyr Moss",
    "re:qx-\\d{3}",
    "   # an indented comment",
    "glint",
    BLORP_NFD,
]) + "\n"


def no_term_in(text: str) -> bool:
    low = text.lower()
    return not any(w in low for w in DENY_WORDS)


def test_check_disclosure(tmp: Path) -> None:
    section("check_disclosure: the denylist format")
    entries = CD.parse_denylist(DENYLIST)
    check([e.index for e in entries] == [1, 2, 3, 4],
          "entries are numbered 1..K, comments and blank lines take no number")
    hits = CD.find_hits(entries, "a zephyr\n   MOSS here\nqx-123 and qx-12\nglinting\n")
    check(hits == [(1, 1), (3, 2)],
          f"a plain phrase matches case-insensitively across a line break, a re: entry "
          f"matches as a regex, and whole words only (got {hits})")
    check(CD.find_hits(entries, "zephyrmoss, glinted, xglint") == [],
          "a plain entry inside a longer word does not match")
    check(CD.find_hits(entries, "QX-123") == [],
          "a re: entry is compiled as written (case-sensitive unless it says (?i))")
    check(CD.mask(entries, "docs/glint-notes.md") == "docs/[#3]-notes.md",
          "mask() replaces a term in a path with its entry number")

    root = tmp / "disc"
    files = {
        "pub/a.md": "Intro.\nThe Zephyr\n  Moss method.\n",          # #1, line 2
        "pub/b.html": "<p>zephyr <em>moss</em></p>\n",               # #1 via tags
        "pub/c.txt": "zephyrmoss and glinting\n",                    # nothing
        "pub/d.json": '{"k": "qx-123"}\n',                           # #2
        "pub/e.ts": "\n\nconst a = 'glint';\n",                      # #3, line 3
        "pub/f.png": b"\x89PNG\r\n\x1a\n\x00\x00glint\x00\n",       # binary: skipped
        "pub/g.astro": "<p>GLINT</p>\n",                             # #3
        "pub/h.js": 'var s = "\\u0067lint";\n',                      # #3 via escape
        "pub/glint-notes.md": "clean\n",                             # #3 in the file name
        "pub/node_modules/x.md": "glint\n",                          # skipped dir
        "clean/ok.md": "Nothing private here.\n",
    }
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            p.write_bytes(body)
        else:
            p.write_text(body, encoding="utf-8")
    deny = tmp / "deny.txt"
    deny.write_text(DENYLIST, encoding="utf-8")
    check([(h.line, h.index) for h in CD.scan_file(entries, root / "pub" / "b.html")]
          == [(1, 1)], "a phrase split by an inline tag is caught (tags stripped)")
    check([(h.line, h.index) for h in CD.scan_file(entries, root / "pub" / "h.js")]
          == [(1, 3)], "a word hidden behind a \\u escape in JS is caught")

    section("check_disclosure: hits are reported by index only")
    p = run_py("check_disclosure.py", "--denylist", str(deny), str(root / "pub"))
    out = p.stdout.splitlines()
    check(p.returncode == 1, f"hits exit 1 (got {p.returncode})")
    got = {(Path(ln.split(":")[0]).name, ln.split(":")[1], ln.split(": ", 1)[1])
           for ln in out}
    want = {
        ("a.md", "2", "private term #1"),
        ("b.html", "1", "private term #1"),
        ("d.json", "1", "private term #2"),
        ("e.ts", "3", "private term #3"),
        ("g.astro", "1", "private term #3"),
        ("h.js", "1", "private term #3"),
        ("[#3]-notes.md", "0", "private term #3"),
    }
    check(got == want, f"plain vs regex vs tag-split vs escaped vs file-name hits "
                       f"(got {sorted(got)})")
    check(all(re.fullmatch(r".+:\d+: private term #\d+", ln) for ln in out),
          "every line is `path:line: private term #K`")
    check(no_term_in(p.stdout + p.stderr),
          "neither stdout nor stderr contains any denylisted word, even in a path")
    check(not any("f.png" in ln or "node_modules" in ln for ln in out),
          "a binary file's lone five-letter run is below the six-character floor, and "
          "node_modules is not scanned in a directory walk")
    p = run_py("check_disclosure.py", "--denylist", str(deny), str(root / "pub" / "f.png"))
    check(p.returncode == 1, "a file named explicitly is scanned whatever its suffix")

    section("check_disclosure: clean, and the exit-2 contract")
    p = run_py("check_disclosure.py", "--denylist", str(deny), str(root / "clean"))
    check(p.returncode == 0 and p.stdout == "", f"a clean tree exits 0 (got {p.returncode})")
    p = run_py("check_disclosure.py", "--denylist", str(tmp / "missing.txt"),
               str(root / "clean"))
    check(p.returncode == 2, f"a missing denylist exits 2 (got {p.returncode})")
    only_comments = tmp / "empty.txt"
    only_comments.write_text("# nothing yet\n\n   \n", encoding="utf-8")
    p = run_py("check_disclosure.py", "--denylist", str(only_comments), str(root / "pub"))
    check(p.returncode == 2, "a denylist with no entries exits 2, never clean")
    bad = tmp / "bad.txt"
    bad.write_text("fine\nre:([unclosed\n", encoding="utf-8")
    p = run_py("check_disclosure.py", "--denylist", str(bad), str(root / "clean"))
    check(p.returncode == 2 and "#2" in p.stderr and "unclosed" not in p.stderr,
          "an invalid regex exits 2 and names the entry by number only")
    greedy = tmp / "greedy.txt"
    greedy.write_text("re:x*\n", encoding="utf-8")
    p = run_py("check_disclosure.py", "--denylist", str(greedy), str(root / "clean"))
    check(p.returncode == 2, "a regex that matches the empty string is refused")
    p = run_py("check_disclosure.py", "--denylist", str(deny), str(root / "nope"))
    check(p.returncode == 2, "a PATH that does not exist exits 2")

    section("check_disclosure: --denylist-env (the CI secret)")
    env = dict(os.environ, TEST_DISCLOSURE_LIST=DENYLIST)
    p = run_py("check_disclosure.py", "--denylist-env", "TEST_DISCLOSURE_LIST",
               str(root / "pub" / "e.ts"), env=env)
    check(p.returncode == 1 and p.stdout.strip().endswith("e.ts:3: private term #3"),
          f"the list can come from an environment variable (got {p.stdout!r})")
    env = {k: v for k, v in os.environ.items() if k != "TEST_DISCLOSURE_LIST"}
    p = run_py("check_disclosure.py", "--denylist-env", "TEST_DISCLOSURE_LIST",
               str(root / "pub"), env=env)
    check(p.returncode == 2, "an unset variable exits 2")
    env["TEST_DISCLOSURE_LIST"] = "  \n"
    p = run_py("check_disclosure.py", "--denylist-env", "TEST_DISCLOSURE_LIST",
               str(root / "pub"), env=env)
    check(p.returncode == 2, "an empty variable exits 2")


# ─────────────────────────────────────────────────────────────────────────────
# leak_check
# ─────────────────────────────────────────────────────────────────────────────

def git_env(**extra: str) -> dict:
    env = dict(os.environ)
    env.update({
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test Author", "GIT_AUTHOR_EMAIL": "author@example.com",
        "GIT_COMMITTER_NAME": "Test Author", "GIT_COMMITTER_EMAIL": "author@example.com",
        "GIT_TERMINAL_PROMPT": "0",
    })
    env.update(extra)
    return env


class Repo:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True)
        self.git("init", "-q", "-b", "main")

    def git(self, *args: str, env: Optional[dict] = None) -> str:
        r = subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull, *args],
                           cwd=self.root, capture_output=True, text=True,
                           env=env or git_env())
        if r.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
        return r.stdout.strip()

    def write(self, rel: str, body) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            p.write_bytes(body)
        else:
            p.write_text(body, encoding="utf-8")

    def commit(self, message: str, files: Optional[Dict[str, object]] = None,
               env: Optional[dict] = None) -> str:
        for rel, body in (files or {}).items():
            if body is None:
                self.git("rm", "-q", rel)
            else:
                self.write(rel, body)
                self.git("add", "--", rel)
        self.git("commit", "-q", "--allow-empty", "-m", message, env=env)
        return self.git("rev-parse", "HEAD")


def leak(repo: Repo, rng: str, *extra: str) -> subprocess.CompletedProcess:
    return run_py("leak_check.py", "--root", str(repo.root), "--range", rng, *extra,
                  env=git_env())


def test_leak_check(tmp: Path) -> None:
    section("leak_check: a temporary repository with planted leaks")
    repo = Repo(tmp / "leakrepo")
    base = repo.commit("base", {
        "README.md": "Hello\nEski sat\u0131r here\n",   # Turkish, but before the range
        "SETUP.md": "Setup notes\n",
    })
    repo.git("branch", "pub")                          # stands in for origin/main

    c1 = repo.commit("docs: plain change", {
        "README.md": "Hello\nPlain English line.\n",    # removes the Turkish line
        "docs/research/a.md": "Title\nBu bir a" + TR_C + "iklama\n",
        "SETUP.md": "Setup notes\nKurulum ad\u0131mlar\u0131\n",
    })
    c2 = repo.commit("chore: refs " + ADR_ID, {
        "notes.txt": "first\npath " + HOME + "/file\n",
        "website/x.ts": "const id = '" + EXP_ID + "';\n",
        "docs/q.md": "see " + Q_ID + " and " + TAG + "\n",
    })
    c3 = repo.commit("docs: add notes", {
        "docs/glint-notes.md": "intro\nthe zephyr moss trick\n",
    })
    c4 = repo.commit("docs: drop notes", {"docs/glint-notes.md": None})
    c5 = repo.commit("docs: tidy", {"docs/tidy.md": "tidy\n"},
                     env=git_env(GIT_AUTHOR_NAME="Glint Person"))
    deny = tmp / "leak-deny.txt"
    deny.write_text(DENYLIST, encoding="utf-8")

    p = leak(repo, "pub..main", "--denylist", str(deny))
    out = p.stdout.splitlines()
    s = {k: v[:10] for k, v in dict(c1=c1, c2=c2, c3=c3, c4=c4, c5=c5).items()}
    check(p.returncode == 1, f"planted leaks exit 1 (got {p.returncode}: {p.stderr})")

    def has(where: str, rule: str) -> bool:
        return any(ln.startswith(where + ": [" + rule + "]") for ln in out)

    check(has(f"{s['c1']}:docs/research/a.md:2", "LANGUAGE"),
          "a Turkish line added to an English-only path is caught at its line")
    check(not any(f"{s['c1']}:SETUP.md" in ln for ln in out),
          "a Turkish line in a path outside the English-only list is not")
    check(not any(":README.md:" in ln for ln in out),
          "a removed Turkish line is ignored")
    check(has(f"{s['c2']}:notes.txt:2", "HOME-PATH"),
          "a home-directory path is caught in any file")
    check(has(f"{s['c2']}:website/x.ts:1", "PRIVATE-ID"),
          "an experiment id is caught")
    check(has(f"{s['c2']}:docs/q.md:1", "PRIVATE-ID")
          and has(f"{s['c2']}:docs/q.md:1", "UNVERIFIED-TAG"),
          "an open-question id and a verification tag are caught")
    check(has(f"{s['c2']}: message line 1", "PRIVATE-ID"),
          "a decision-record id in a commit message is caught")
    check(has(f"{s['c3']}:docs/[#3]-notes.md:2", "DENYLIST"),
          "a denylisted phrase in an added line is caught, path masked")
    check(has("docs/[#3]-notes.md: file name", "DENYLIST"),
          "a file added and deleted inside the range is still seen by name "
          "(rev-list --objects)")
    check(has(f"{s['c5']}: author name", "DENYLIST"),
          "an author field is checked against the denylist")
    check(not any(ln.startswith(s["c4"]) for ln in out),
          "the deleting commit adds nothing and reports nothing")
    check(no_term_in(p.stdout + p.stderr),
          "no denylisted word appears anywhere in the output")
    leaked = [EXP_ID, ADR_ID, Q_ID, HOME, TAG, TR_C, "\u0131"]
    check(not any(x in p.stdout + p.stderr for x in leaked),
          "no matched id, path, tag or letter is echoed")
    check(all(re.match(r"^\S.*: \[[A-Z-]+\] ", ln) for ln in out),
          "every finding line has the `where: [RULE] message` shape")

    section("leak_check: merges count only what is new in the merge")
    repo.git("checkout", "-q", "pub")
    pub_tip = repo.commit("pub: already public", {"PUBLIC.md": "id " + "E-" + "11" + "\n",
                                                  "pub-" + "E-" + "11" + ".md": "x\n"})
    repo.git("checkout", "-q", "main")
    repo.git("merge", "-q", "--no-ff", "--no-commit", "pub")
    repo.write("website/x.ts", "const id = '" + EXP_ID + "';\nconst b = '"
               + "ADR-" + "002" + "';\n")
    repo.git("add", "--", "website/x.ts")
    merge = repo.commit("Merge pub")
    p = leak(repo, pub_tip + "..main", "--no-denylist")
    out = p.stdout.splitlines()
    mine = [ln for ln in out if ln.startswith(merge[:10])]
    check(len(mine) == 1 and mine[0].startswith(f"{merge[:10]}:website/x.ts:2: [PRIVATE-ID]"),
          f"an edit made inside a merge is caught; the merged-in public content and "
          f"the first parent's own lines are not (got {mine})")
    check(not any("PUBLIC.md" in ln for ln in out),
          "content brought in from the already-public parent is not re-reported")
    check(not any(ln.startswith("pub-") for ln in out),
          "nor is a file name it brings in (a merge's paths are those new to every parent)")
    check("--no-denylist" in p.stderr and "did not run" in p.stderr,
          "running with --no-denylist says the DENYLIST rule did not run")
    p = leak(repo, pub_tip + "..main")
    check(p.returncode == 2 and p.stdout == "" and "no denylist given" in p.stderr,
          f"with no denylist and no --no-denylist it refuses to run, exit 2 "
          f"(got {p.returncode})")

    section("leak_check: clean ranges and the exit-2 contract")
    p = leak(repo, "main..main", "--no-denylist")
    check(p.returncode == 0 and p.stdout == "" and "0 commit(s)" in p.stderr,
          f"an empty range is clean (got {p.returncode})")
    clean = Repo(tmp / "cleanrepo")
    clean.commit("base", {"README.md": "Hello\n"})
    clean.git("branch", "pub")
    clean.commit("docs: plain English", {"docs/research/a.md": "A plain page.\n"})
    p = leak(clean, "pub..main", "--denylist", str(deny))
    check(p.returncode == 0 and p.stdout == "",
          f"a clean range exits 0 (got {p.returncode}: {p.stdout})")
    p = leak(clean, "nosuchref..main", "--no-denylist")
    check(p.returncode == 2 and "git rev-list failed" in p.stderr,
          f"an invalid range exits 2, as a git failure (got {p.returncode}: {p.stderr})")
    p = leak(clean, "pub..main", "--denylist", str(tmp / "missing.txt"))
    check(p.returncode == 2, "a named but missing denylist exits 2")
    p = leak(clean, "--all", "--no-denylist")
    check(p.returncode == 2, "a range that looks like an option is refused")

    section("leak_check: the diff reader")
    diff = "\n".join([
        "diff --git a/README.md b/README.md",
        "--- a/README.md",
        "+++ b/README.md",
        "@@ -1,3 +1,3 @@",
        " keep",
        "-gone",
        "+++ looks like a header but is content",
        " tail",
        "diff --cc website/m.ts",
        "+++ b/website/m.ts",
        "@@@ -1,1 -1,1 +1,3 @@@",
        "  shared",
        " +from parent two",
        "++evil",
        "\\ No newline at end of file",
    ])
    got = LK.added_lines(diff)
    check(got == [("README.md", 2, "++ looks like a header but is content"),
                  ("website/m.ts", 3, "evil")],
          f"added lines, hunk-relative numbering, combined-diff columns (got {got})")
    check(LK.unquote_path('"b/docs/\\303\\247.md"') == "b/docs/" + TR_C + ".md",
          "git's octal-quoted paths are decoded")
    check(LK.english_only("website/src/a.ts") and LK.english_only("CONTRIBUTING.md")
          and not LK.english_only("SETUP.md") and not LK.english_only("docs/researchx.md"),
          "the English-only path list")


# ─────────────────────────────────────────────────────────────────────────────
# review round 1: each gap found in review, pinned
# ─────────────────────────────────────────────────────────────────────────────

def test_check_copy_review(tmp: Path) -> None:
    section("check_copy: the ledger's quarantine paths, read as C2 and C4 read them")
    led = json.loads(json.dumps(BASE_LEDGER))
    led["count_quarantine_paths"] = ["website/src/diagrams/old.mmd"]
    led["claim_quarantine_paths"] = ["website/src/legacy/"]
    r = make_repo(tmp, ledger=led, files={
        "website/src/diagrams/old.mmd": "flowchart LR\n  a[5 suites]\n  b[ba" + TR_G + "lam]\n",
        "website/src/diagrams/new.mmd": "flowchart LR\n  a[5 suites]\n",
        "website/src/legacy/a.astro":
            "<p>It " + CLAIM + "; " + RESEARCH_TERM + "; 3 pJ</p>\n<p>618 assertions</p>\n",
    })
    f = copy_findings(r)
    check(rules_at(f, "website/src/diagrams/old.mmd", 2) == [],
          "count_quarantine_paths (an exact path) exempts a file from COUNT")
    check(rules_at(f, "website/src/diagrams/old.mmd", 3) == ["LANGUAGE"],
          "but never from LANGUAGE")
    check(rules_at(f, "website/src/diagrams/new.mmd", 2) == ["COUNT"],
          "a path that is not listed is still checked")
    check(rules_at(f, "website/src/legacy/a.astro", 1) == [],
          "claim_quarantine_paths (a prefix) exempts CLAIM, RESEARCH and ENERGY")
    check(rules_at(f, "website/src/legacy/a.astro", 2) == ["COUNT"], "but not COUNT")

    section("check_copy: decomposed letters, entities and inline tags")
    r = make_repo(tmp, files={
        "website/src/pages/nfd.astro":
            "<p>ba" + "g\u0306" + "lam</p>\n<p>i\u0307</p>\n<p>plain</p>\n",
        "website/src/pages/m.astro": "\n".join([
            "<p>3&nbsp;pJ</p>",                            # 1
            "<p>10&times; fewer</p>",                      # 2
            "<p>the model <em>" + THINKS + "</em></p>",    # 3
            "<p>&ccedil;</p>",                             # 4
        ]) + "\n",
    })
    f = copy_findings(r)
    check(rules_at(f, "website/src/pages/nfd.astro", 1) == ["LANGUAGE"],
          "a Turkish letter written decomposed (NFD) is a LANGUAGE finding")
    check(rules_at(f, "website/src/pages/nfd.astro", 2) == ["LANGUAGE"],
          "so is a dotted small i (i + combining dot, which has no precomposed form)")
    check(rules_at(f, "website/src/pages/nfd.astro", 3) == [], "plain ASCII passes")
    m_astro = "website/src/pages/m.astro"
    check(rules_at(f, m_astro, 1) == ["ENERGY"], "an energy figure joined by &nbsp; is caught")
    check(rules_at(f, m_astro, 2) == ["ENERGY"], "a multiple written with &times; is caught")
    check(rules_at(f, m_astro, 3) == ["RESEARCH"], "a research term split by an inline tag is caught")
    check(rules_at(f, m_astro, 4) == ["LANGUAGE"], "a Turkish letter written as an entity is caught")

    section("check_copy: a negation cue counts only as a word")
    r = make_repo(tmp, files={"website/src/diagrams/neg.mmd": "\n".join([
        "flowchart LR",                                          # 1
        "  a[Another milestone: " + RESEARCH_TERM + "]",               # 2
        "  b[Notably, " + RESEARCH_TERM + "]",                         # 3
        "  c[note: " + RESEARCH_TERM + "]",                            # 4
        "  d[Minor revision: " + RESEARCH_TERM + "]",                  # 5
        "  e[plain]",                                            # 6
        "  f[We do not say " + RESEARCH_TERM + "]",                    # 7
        "  g[This page isn't saying " + RESEARCH_TERM + "]",           # 8
        "  h[It cannot be said that " + RESEARCH_TERM + "]",           # 9
        "  i[We avoided saying " + RESEARCH_TERM + "]",                # 10
    ]) + "\n"})
    f = copy_findings(r)
    for line, word in ((2, "Another"), (3, "Notably"), (4, "note"), (5, "Minor")):
        check(rules_at(f, "website/src/diagrams/neg.mmd", line) == ["RESEARCH"],
              f"'{word}' is not a negation (line {line})")
    for line, cue in ((7, "do not"), (8, "n't"), (9, "cannot"), (10, "avoided")):
        check(rules_at(f, "website/src/diagrams/neg.mmd", line) == [],
              f"'{cue}' still negates (line {line})")
    check("not" in CC.LC.NEGATION_CUES and CC.LC.NEGATION_WINDOW > 0,
          "the cues and the window themselves are still ledger_check's")

    section("check_copy: a term wrapped across a line, or split by Markdown emphasis")
    r = make_repo(tmp, files={
        "docs/research/wrap.md": "Intro line.\nHere the model\n" + THINKS + " in maps.\n",
        "docs/research/wrapneg.md": "We never claim that the model\n" + THINKS + ".\n",
        "docs/research/em.md": "Here the model *" + THINKS + "* in maps.\n",
    })
    f = copy_findings(r)
    check(rules_at(f, "docs/research/wrap.md") == ["RESEARCH"]
          and rules_at(f, "docs/research/wrap.md", 2) == ["RESEARCH"],
          "a hard-wrapped research term is caught, at the line where it starts")
    check(rules_at(f, "docs/research/wrapneg.md") == [], "and a negated one still passes")
    check(rules_at(f, "docs/research/em.md", 1) == ["RESEARCH"],
          "a research term split by Markdown emphasis is caught")

    section("check_copy: the research plan, read token by token")
    plan_text = "\n".join([
        "{",
        '  "title": "ba\\u011Flam",',            # 2: an escape in upper-case hex
        '  "path": "a\\/b 618 assertions",',      # 3: an escaped slash
        '  "a": {"618 suites": 3},',              # 4: a KEY equal to the next value
        '  "c": "618 suites"',                    # 5
        "}",
    ]) + "\n"
    r = make_repo(tmp, files={"tools/research_plan.json": plan_text})
    f = [(x.line, x.rule) for x in copy_findings(r) if x.path == "tools/research_plan.json"]
    check(sorted(f) == [(2, "LANGUAGE"), (3, "COUNT"), (5, "COUNT")],
          f"each value is found on its own line, whatever its escapes, and a value equal "
          f"to a key is not placed on the key's line (got {sorted(f)})")
    r = make_repo(tmp, files={"tools/research_plan.json":
                              '{\n  "title": "' + RESEARCH_TERM + '",\n  "title": "ok"\n}\n'})
    p = run_py("check_copy.py", "--root", str(r))
    check(p.returncode == 2 and "repeats" in p.stderr and RESEARCH_TERM not in p.stderr,
          f"a key repeated inside one object exits 2 (got {p.returncode})")
    r = make_repo(tmp, files={"tools/research_plan.json":
                              json.dumps({"t": "ledger:allow-claim " + RESEARCH_TERM})})
    check(rules_at(copy_findings(r), "tools/research_plan.json") == ["RESEARCH"],
          "a plan string cannot carry a pragma")

    section("check_copy: the surfaces added in review")
    r = make_repo(tmp, files={
        "website/astro.config.mjs": "export default { description: 'Where " + RESEARCH_TERM + "' };\n",
        "website/src/data/site.json": '{"tagline": "10x fewer operations"}\n',
        "website/src/lib/x.mjs": "export const t = '618 assertions';\n",
        "website/src/package.json": '{"description": "618 assertions"}\n',
        "website/README.md": "It costs 4 nJ.\n",
        "website/node_modules/pkg/README.md": "It costs 4 nJ.\n",
        "website/dist/index.md": "It costs 4 nJ.\n",
        "docs/research/sub/deep.md": "It costs 4 nJ.\n",
    })
    f = copy_findings(r)
    check(rules_at(f, "website/astro.config.mjs", 1) == ["RESEARCH"],
          "website/astro.config.mjs (the site description) is a copy surface")
    check(rules_at(f, "website/src/data/site.json", 1) == ["ENERGY"],
          ".json under website/src is a copy surface")
    check(rules_at(f, "website/src/lib/x.mjs", 1) == ["COUNT"], "and .mjs")
    check(rules_at(f, "website/src/package.json") == [], "but not package*.json")
    check(rules_at(f, "website/README.md", 1) == ["ENERGY"],
          "Markdown under website/ is prose (RESEARCH, ENERGY, LANGUAGE)")
    check(not any("node_modules" in x.path or "/dist/" in x.path for x in f),
          "node_modules and dist under website/ are not")
    check(rules_at(f, "docs/research/sub/deep.md", 1) == ["ENERGY"],
          "docs/research/ is walked recursively")

    section("check_copy: exit 2 for whatever it cannot read")
    lone = tmp / "lone"
    (lone / "tools" / "publish").mkdir(parents=True)
    for name in ("check_copy.py", "check_disclosure.py"):
        shutil.copy(HERE / name, lone / "tools" / "publish" / name)
    (lone / "tools" / "ledger.json").write_text(json.dumps(BASE_LEDGER), encoding="utf-8")
    p = subprocess.run([sys.executable, "-B", str(lone / "tools" / "publish" / "check_copy.py"),
                        "--root", str(lone)], capture_output=True, text=True)
    check(p.returncode == 2 and "cannot run" in p.stderr and "Traceback" not in p.stderr,
          f"a missing tools/ledger_check.py exits 2, without a traceback (got {p.returncode})")
    r = make_repo(tmp, files={"website/src/ok.ts": "const a = 1;\n"})
    os.symlink(str(r / "website" / "src" / "nowhere.ts"), str(r / "website" / "src" / "broken.ts"))
    p = run_py("check_copy.py", "--root", str(r))
    check(p.returncode == 2 and "broken.ts" in p.stderr and "Traceback" not in p.stderr,
          f"a surface that cannot be read (a dangling link) exits 2 (got {p.returncode})")
    for bad, label in (
            ([], "a ledger that is a JSON list"),
            (dict(BASE_LEDGER, forbidden_claim_terms=[1]), "a claim term that is not a string"),
            (dict(BASE_LEDGER, count_quarantine_paths="docs/"), "a quarantine list that is a string"),
            (dict(BASE_LEDGER, tests={"suites": "26"}), "a suite count that is a string")):
        r = make_repo(tmp, ledger=bad, files={"website/src/a.ts": "const a = 1;\n"})
        p = run_py("check_copy.py", "--root", str(r))
        check(p.returncode == 2 and "Traceback" not in p.stderr,
              f"{label} exits 2 (got {p.returncode})")
    src = (HERE / "check_copy.py").read_text(encoding="utf-8")
    check(("ledger:" + "ignore-file") not in src,
          "check_copy.py does not carry the whole-file ignore token, so C4 still reads it")


def test_check_disclosure_review(tmp: Path) -> None:
    deny = tmp / "deny-review.txt"
    deny.write_text(DENYLIST, encoding="utf-8")
    root = tmp / "disc-review"
    files = {
        "d1/pub/glint/readme.md": "clean text\n",
        "d1/pub/zephyr-moss/index.html": "<p>clean</p>\n",
        "d1/pub/ok/fine.md": "clean\n",
        "d2/em1.md": "**Zephyr** Moss\n",
        "d2/em2.md": "*Zephyr* Moss\n",
        "d2/em3.md": "Zephyr [Moss](x)\n",
        "d2/em4.md": "`zephyr` moss\n",
        "d2/em5.md": "> The Zephyr\n> Moss rule\n",
        "d2/plain.md": "Zephyr and moss, apart\n",
        "d3/a.ts": 'const s = "\\u0067lint";\n',
        "d3/b.tsx": 'const s = "\\u0067lint";\n',
        "d3/c.py": "s = '\\u0067lint'\n",
        "d3/d.js": "s = '\\x67lint';\n",
        "d3/e.js": "s = '\\u{67}lint';\n",
        "d3/f.css": ".x::after { content: '\\67 lint'; }\n",
        "d3/g.astro": "<p>{'\\u0067lint'}</p>\n",
        "d4/refs.bib": "@misc{x, title={glint}}\n",
        "d4/nb.ipynb": '{"cells": [{"source": ["glint"]}]}\n',
        "d4/NOTES": "glint\n",
        "d4/run.sh": "echo glint\n",
        "d4/a.rst": "glint\n",
        "d4/b.cfg": "x = glint\n",
        "d4/bin.dat": b"\x00\x01glint\x00\xff",
        "d5/e.html": "a &#10; b\n\nglint\n",
        "d5/f.html": "a &NewLine; b &#xA; c\nglint\n",
        "d6/nfc.md": "x " + BLORP_NFC + " y\n",
        "d6/nfd.md": "x " + BLORP_NFD + " y\n",
        "d8/x.png": b"\x89PNG\r\n\x1a\n\x00\x00glint",
    }
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            p.write_bytes(body)
        else:
            p.write_text(body, encoding="utf-8")
    (root / "d7").mkdir()

    def hits(sub: str):
        base = root / sub
        p = run_py("check_disclosure.py", "--denylist", str(deny), str(base))
        got = set()
        for ln in p.stdout.splitlines():
            left, index = ln.rsplit(": private term #", 1)
            path, line = left.rsplit(":", 1)
            got.add((path[len(str(base)) + 1:], int(line), int(index)))
        return p, got

    section("check_disclosure: every directory below the PATH is part of the name")
    p, got = hits("d1/pub")
    check(got == {("[#3]/readme.md", 0, 3), ("[#1]/index.html", 0, 1)},
          f"a term as a directory, and a phrase as a slug directory, are hits at line 0, "
          f"masked (got {sorted(got)})")
    check(p.returncode == 1 and no_term_in(p.stdout + p.stderr),
          "exit 1, and the directory names are never printed")

    section("check_disclosure: Markdown inline syntax does not split a phrase")
    p, got = hits("d2")
    check(got == {(f"em{k}.md", 1, 1) for k in range(1, 6)},
          f"bold, italic, a link, code and a wrapped blockquote all match; words apart "
          f"do not (got {sorted(got)})")

    section("check_disclosure: string escapes in every scripting format")
    p, got = hits("d3")
    check(got == {(n, 1, 3) for n in ("a.ts", "b.tsx", "c.py", "d.js", "e.js", "f.css",
                                       "g.astro")},
          f"\\u in .ts/.tsx/.py/.astro, \\x and \\u{{}} in .js, a CSS escape (got {sorted(got)})")

    section("check_disclosure: text files of any name are scanned in a walk")
    p, got = hits("d4")
    check(got == {(n, 1, 3) for n in ("refs.bib", "nb.ipynb", "NOTES", "run.sh", "a.rst",
                                       "b.cfg")},
          f".bib, .ipynb, .sh, .rst, .cfg and an extensionless file are scanned; a binary "
          f"file's lone five-letter run is not read (got {sorted(got)})")

    section("check_disclosure: a newline entity does not shift line numbers")
    p, got = hits("d5")
    check(got == {("e.html", 3, 3), ("f.html", 2, 3)},
          f"&#10;, &#xA; and &NewLine; read as spaces (got {sorted(got)})")

    section("check_disclosure: NFC and NFD are the same text")
    p, got = hits("d6")
    check(got == {("nfc.md", 1, 4), ("nfd.md", 1, 4)},
          f"an entry written decomposed matches text in either form (got {sorted(got)})")
    check(no_term_in(p.stdout + p.stderr), "and is never printed")

    section("check_disclosure: nothing to scan is never clean")
    p = run_py("check_disclosure.py", "--denylist", str(deny), str(root / "d7"))
    check(p.returncode == 2 and "nothing to scan" in p.stderr,
          f"an empty directory exits 2 (got {p.returncode})")
    p = run_py("check_disclosure.py", "--denylist", str(deny), str(root / "d8"))
    check(p.returncode == 2, f"a directory holding only binary files exits 2 (got {p.returncode})")
    p = run_py("check_disclosure.py", "--denylist", str(deny), "--quiet",
               str(root / "d1" / "pub" / "ok" / "fine.md"), str(root / "d7"))
    check(p.returncode == 2, "an empty directory next to a clean file still exits 2")

    section("check_disclosure: masking never leaves part of a match showing")
    two = CD.parse_denylist("zephyr\nZephyr Moss\n")
    check(CD.mask(two, "a/zephyr moss/b") == "a/[#1]/b",
          f"overlapping matches merge into one mask (got {CD.mask(two, 'a/zephyr moss/b')})")
    check(CD.mask(two, "site/zephyr-moss/index.html") == "site/[#1]/index.html",
          "a slug's match is masked too")
    check(CD.path_indices(entries_of(DENYLIST), "docs/zephyr_moss.md") == [1],
          "an underscore slug matches a phrase")


def entries_of(text: str):
    return CD.parse_denylist(text)


def test_leak_check_review(tmp: Path) -> None:
    deny = tmp / "leak-review-deny.txt"
    deny.write_text(DENYLIST, encoding="utf-8")
    repo = Repo(tmp / "leak-review")
    repo.commit("base", {"a.md": "hello\n", "keep": "", "empty/.gitkeep": "",
                         "ctx.md": "line one\nMoss approach\n"})
    repo.git("branch", "pub")

    (repo.root / "docs" / "research").mkdir(parents=True)
    repo.git("mv", "a.md", "docs/research/ba" + TR_G + "lam.md")       # same content
    c1 = repo.commit("docs: names", {
        "docs/research/" + TR_C + ".txt": "",                        # empty: no new blob
        "docs/research/" + EXP_ID + "-notes.md": "",                  # empty, id in the name
        "docs/glint/.gitkeep": "",                                 # same tree as empty/
        "docs/same.md": "same body\n",
        "docs/notes-" + EXP_ID + ".md": "same body\n",              # same blob as a sibling
    })
    c2 = repo.commit("chore: attributes", {
        ".gitattributes": "*.md -diff\n",
        "docs/attr.md": "path " + HOME + "/x\nid " + EXP_ID + "\n",
    })
    c3 = repo.commit("chore: nul", {"docs/nul.txt": b"text\x00 with " + EXP_ID.encode() + b"\n"})
    blob = (b"\x89PNG\r\n\x1a\n\x00\x00" + TR_C.encode("utf-8") * 40 + b"\x00\xff"
            + (HOME + "/img").encode() + b"\x00")
    c4 = repo.commit("chore: image", {"website/img.bin": blob})
    c5 = repo.commit("chore: utf16", {"docs/u16.txt": ("note " + EXP_ID + "\n").encode("utf-16")})
    c6 = repo.commit("docs: the Zephyr\nMoss note",
                     {"docs/phrase.md": "We describe the Zephyr\nMoss approach\n"})
    c7 = repo.commit("docs: cite", {"ctx.md": "We cite Zephyr\nMoss approach\n"})
    c8 = repo.commit("docs: more", {
        "docs/research/nfd.md": "ba" + "g\u0306" + "lam\n",
        "docs/tag.md": "see " + TAG + "\n",
        "docs/" + EXP_ID + "/notes.md": "plain\n",
        "notes/" + "Users" + "/someone/x.md": "plain\n",
    })
    p = leak(repo, "pub..main", "--denylist", str(deny))
    out = p.stdout.splitlines()
    s = {k: v[:10] for k, v in dict(c1=c1, c2=c2, c3=c3, c4=c4, c5=c5, c6=c6, c7=c7,
                                    c8=c8).items()}

    def has(where: str, rule: str) -> bool:
        return any(ln.startswith(where + ": [" + rule + "]") for ln in out)

    section("leak_check: names are taken from each commit, not from new objects")
    check(has("docs/research/ba[U+011F]lam.md: file name", "LANGUAGE"),
          "a public file renamed to a Turkish name (same content, so no new blob) is caught")
    check(has("docs/research/[U+00E7].txt: file name", "LANGUAGE"),
          "a new empty file is caught by name")
    check(has("docs/research/[ID]-notes.md: file name", "PRIVATE-ID"),
          "an empty file with a private id in its name is caught")
    check(has("docs/[#3]: file name", "DENYLIST"),
          "a new directory whose tree already exists in public history is caught")
    check(not any(ln.startswith("docs/[#3]/") for ln in out),
          "a finding on a directory is reported once, not again for each file in it")
    check(has("docs/notes-[ID].md: file name", "PRIVATE-ID"),
          "of two new files with identical content, both names are checked")

    section("leak_check: content git would show as binary is still read")
    check(has(f"{s['c2']}:docs/attr.md:1", "HOME-PATH")
          and has(f"{s['c2']}:docs/attr.md:2", "PRIVATE-ID"),
          "a -diff attribute committed inside the range hides nothing")
    check(has(f"{s['c3']}:docs/nul.txt:1", "PRIVATE-ID"), "a NUL byte hides nothing")
    check(has(f"{s['c4']}:website/img.bin: binary content", "HOME-PATH"),
          "a binary file's printable runs are checked")
    check(not any("img.bin" in ln and "[LANGUAGE]" in ln for ln in out),
          "and LANGUAGE is not applied to binary bytes")
    check(has(f"{s['c5']}:docs/u16.txt:1", "PRIVATE-ID"), "UTF-16 text is decoded")

    section("leak_check: a denylisted phrase wrapped across lines")
    check(has(f"{s['c6']}: message line 1", "DENYLIST"),
          "across two lines of a commit message")
    check(has(f"{s['c6']}:docs/phrase.md:1", "DENYLIST"), "across two added lines")
    check(has(f"{s['c7']}:ctx.md:1", "DENYLIST"),
          "completed by an added line next to an unchanged public line")

    section("leak_check: NFD text, the tag shape, and masked paths")
    check(has(f"{s['c8']}:docs/research/nfd.md:1", "LANGUAGE"),
          "a decomposed Turkish letter is caught")
    check(has(f"{s['c8']}:docs/tag.md:1", "UNVERIFIED-TAG"), "the tag shape is caught")
    check(has("docs/[ID]: file name", "PRIVATE-ID")
          and not any(ln.startswith("docs/[ID]/") for ln in out),
          "an id in a directory name is reported once, masked")
    check(has("notes[HOME]: file name", "HOME-PATH"),
          "a home directory in a path is reported, masked with the user name")
    shown_text = p.stdout + p.stderr
    leaked = [EXP_ID, HOME, "someone", TAG, TR_C, TR_G, "\u0306", "glint", "zephyr"]
    check(not any(x in shown_text or x in shown_text.lower() for x in leaked),
          "no id, home path, user name, tag, Turkish letter or term is printed, even in a path")
    check(all(ord(ch) < 128 for ch in p.stdout), "the findings are plain ASCII")

    section("leak_check: repository configuration cannot hide content")
    cfg = Repo(tmp / "cfgrepo")
    cfg.git("config", "log.showRoot", "false")
    cfg.git("config", "diff.suppressBlankEmpty", "true")
    first = cfg.commit("root", {"f.md": "id " + EXP_ID + "\n", "g.md": "a\n\nb\n"})
    second = cfg.commit("more", {"g.md": "a\n\nb\nid " + EXP_ID + "\n"})
    p = leak(cfg, "main", "--no-denylist")
    out = p.stdout.splitlines()
    check(has(f"{first[:10]}:f.md:1", "PRIVATE-ID"),
          "a root commit's content is read even with log.showRoot=false")
    check(has(f"{second[:10]}:g.md:4", "PRIVATE-ID"),
          "line numbers hold with diff.suppressBlankEmpty=true")
    diff = "\n".join(["diff --git a/g.md b/g.md", "--- a/g.md", "+++ b/g.md",
                      "@@ -1,3 +1,4 @@", " a", "", " b", "+new"])
    check(LK.added_lines(diff) == [("g.md", 4, "new")],
          "the diff reader counts a bare blank context line")
    check("|" not in LK.TAG_RE.pattern,
          "the tag rule is a shape with no word alternatives (the words are the denylist's)")


# ─────────────────────────────────────────────────────────────────────────────
# review round 2
# ─────────────────────────────────────────────────────────────────────────────

CAN_LOCK = hasattr(os, "geteuid") and os.geteuid() != 0   # root reads a mode-000 directory
CONSCIOUS = CLAIM[len("is "):]


def write_tree(root: Path, files: Dict[str, object]) -> None:
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            p.write_bytes(body)
        else:
            p.write_text(body, encoding="utf-8")


def disclosure_lines(deny_text: str, tmp: Path, *paths: Path,
                     cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    deny = tmp / f"deny-{abs(hash(deny_text)) % 10**8}.txt"
    deny.write_text(deny_text, encoding="utf-8")
    return run_py("check_disclosure.py", "--denylist", str(deny),
                  *[str(p) for p in paths], cwd=cwd)


def test_check_copy_round2(tmp: Path) -> None:
    section("check_copy: ENERGY catches what the spec regex catches")
    r = make_repo(tmp, files={"website/src/diagrams/sci.mmd": "\n".join([
        "flowchart LR",                    # 1
        "  a[about 1e3 pJ]",               # 2 scientific notation
        "  b[2.3e2 pJ]",                   # 3
        "  c[about 4e2nJ]",                # 4
        "  d[.5 pJ]",                      # 5 leading-dot decimal
        "  e[x10pJ]",                      # 6 glued to a letter
        "  f[a10x fewer]",                 # 7
        "  g[plain]",                      # 8
    ]) + "\n"})
    f = copy_findings(r)
    for line, label in ((2, "1e3 pJ"), (3, "2.3e2 pJ"), (4, "4e2nJ"), (5, ".5 pJ"),
                        (6, "x10pJ"), (7, "a10x fewer")):
        check(rules_at(f, "website/src/diagrams/sci.mmd", line) == ["ENERGY"],
              f"'{label}' is an ENERGY finding (line {line})")
    check(rules_at(f, "website/src/diagrams/sci.mmd", 8) == [], "a line with no figure passes")

    section("check_copy: COUNT and CLAIM on rendered prose, nothing reported twice")
    r = make_repo(tmp, files={
        "docs/research/fig.md": "\n".join([
            "# Figure",                                        # 1
            "",                                                # 2
            "```mermaid",                                      # 3
            "flowchart LR",                                    # 4
            '  a["618<br/>assertions"]',                       # 5 split by a tag
            '  c["618 **assertions**"]',                       # 6 split by emphasis
            "```",                                             # 7
            "618 assertions, stale",                           # 8 raw: C2 reports it
        ]) + "\n",
        "README.md": "\n".join([
            "Totals: 618 <b>assertions</b>",                   # 1 split by a tag
            "The substrate is <b>" + CONSCIOUS + "</b>.",      # 2 claim split by a tag
            "The substrate " + CLAIM + ".",                    # 3 raw: C4 reports it
            "We say the substrate is",                         # 4 wrapped: C4 cannot see it
            CONSCIOUS + " here.",                              # 5
            "Another note: the substrate " + CLAIM + ".",      # 6 C4 reads 'not' in 'Another'
        ]) + "\n",
        "docs/research/ignored.md": "<!-- ledger:" + "ignore-file -->\n618 assertions\n",
        "docs/research/pragma.md": "<!-- ledger:allow-count -->\n618 <b>assertions</b>\n",
    })
    f = copy_findings(r)
    check(rules_at(f, "docs/research/fig.md", 5) == ["COUNT"],
          "a count split by <br/> in a Markdown Mermaid fence is a COUNT finding")
    check(rules_at(f, "docs/research/fig.md", 6) == ["COUNT"],
          "a count split by Markdown emphasis is a COUNT finding")
    check(rules_at(f, "docs/research/fig.md", 8) == [],
          "a raw count is left to ledger_check C2 (not reported twice)")
    check(rules_at(f, "README.md", 1) == ["COUNT"], "README.md: a count split by <b>")
    check(rules_at(f, "README.md", 2) == ["CLAIM"], "README.md: a claim term split by <b>")
    check(rules_at(f, "README.md", 3) == [],
          "a raw asserted claim term is left to ledger_check C4 (not reported twice)")
    check(rules_at(f, "README.md", 4) == ["CLAIM"],
          "a claim term wrapped across two lines, which C4 cannot see, is reported here")
    check(rules_at(f, "README.md", 6) == ["CLAIM"],
          "a claim C4 reads as negated by a cue inside a word is reported here")
    check(rules_at(f, "docs/research/ignored.md", 2) == ["COUNT"],
          "a prose file ledger_check skips (whole-file ignore token) gets its raw COUNT here")
    check(rules_at(f, "docs/research/pragma.md") == [], "ledger:allow-count still applies")

    section("check_copy: Mermaid sources are read as markup")
    r = make_repo(tmp, files={"website/src/diagrams/a.mmd": "\n".join([
        "flowchart LR",                                       # 1
        '  a["The model<br/>' + THINKS + ' in maps"]',        # 2
        '  b["618<br/>assertions"]',                          # 3
        '  c["about 3<br/>pJ"]',                              # 4
        '  d["618#32;assertions"]',                           # 5 Mermaid entity
        "  classDef x fill:#fff;",                            # 6 a colour, not an entity
    ]) + "\n"})
    f = copy_findings(r)
    check(rules_at(f, "website/src/diagrams/a.mmd", 2) == ["RESEARCH"],
          "a research term split by <br/> in an .mmd label is caught")
    check(rules_at(f, "website/src/diagrams/a.mmd", 3) == ["COUNT"], "and a count")
    check(rules_at(f, "website/src/diagrams/a.mmd", 4) == ["ENERGY"], "and an energy figure")
    check(rules_at(f, "website/src/diagrams/a.mmd", 5) == ["COUNT"],
          "Mermaid's #NN; entity syntax is decoded")
    check(rules_at(f, "website/src/diagrams/a.mmd", 6) == [], "a CSS colour is left alone")

    section("check_copy: JSX string expressions do not split a term")
    r = make_repo(tmp, files={
        "website/src/components/X.tsx":
            "<p>\n  Here the model{\" \"}\n  <em>" + THINKS + "</em> in maps.\n</p>\n",
        "website/src/components/Y.astro":
            "<p>{\"the model\"} " + THINKS + "</p>\n<p>Zeph{\"yr\"}</p>\n",
    })
    f = copy_findings(r)
    check(rules_at(f, "website/src/components/X.tsx", 2) == ["RESEARCH"],
          "{\" \"} between a term's words, across a line break, reads as a space")
    check(rules_at(f, "website/src/components/Y.astro", 1) == ["RESEARCH"],
          "a string-literal expression is read as its text")

    section("check_copy: the RESEARCH term list cannot switch off unseen")
    for value, label in (({"_README": "x", "term": [RESEARCH_TERM]}, "a misspelt 'terms' key"),
                         ({"_README": "x"}, "an object with no terms"),
                         (None, "a null"), ("x", "a string")):
        led = dict(BASE_LEDGER, research_forbidden_claim_terms=value)
        r = make_repo(tmp, ledger=led, files={"README.md": "Here " + RESEARCH_TERM + ".\n"})
        p = run_py("check_copy.py", "--root", str(r))
        check(p.returncode == 2 and "research_forbidden_claim_terms" in p.stderr
              and "inactive" not in p.stderr and "Traceback" not in p.stderr,
              f"{label} is an invalid ledger, exit 2 (got {p.returncode}: {p.stderr.strip()})")

    section("check_copy: local virtual environments and build output are not surfaces")
    r = make_repo(tmp, files={
        "cogmap/.venv/lib/README.md": "Costs 3 pJ\n",
        "cogmap/venv/lib/README.md": "Costs 3 pJ\n",
        "cogmap/build/lib/README.md": "Costs 3 pJ\n",
        "cogmap/notes.md": "Costs 3 pJ\n",
    })
    f = copy_findings(r)
    check([x.path for x in f] == ["cogmap/notes.md"],
          f".venv, venv and build are skipped, as ledger_check skips them "
          f"(got {[x.path for x in f]})")

    section("check_copy: SVG pragmas are read from the source lines")
    svg = "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">',
        "  <!-- ledger:allow-count -->",                              # 2
        "  <text>618 assertions</text>",                              # 3 permitted
        "  <text>618 suites</text>",                                  # 4 not permitted
        "  <a xlink:title='Here " + RESEARCH_TERM + "'><text>x</text></a>",  # 5 tooltip
        "</svg>",
    ]) + "\n"
    r = make_repo(tmp, files={"docs/assets/s.svg": svg})
    f = copy_findings(r)
    check(rules_at(f, "docs/assets/s.svg", 3) == [],
          "an XML comment pragma on the line above a <text> node permits it")
    check(rules_at(f, "docs/assets/s.svg", 4) == ["COUNT"], "and only that node")
    check(rules_at(f, "docs/assets/s.svg", 5) == ["RESEARCH"], "xlink:title is read as copy")

    section("check_copy: linked directories are followed; unreadable ones exit 2")
    r = make_repo(tmp, files={
        "website/src/ok.ts": "const a = 1;\n",
        "elsewhere/x.ts": "// Here " + RESEARCH_TERM + "\n",
    })
    os.symlink(os.path.join("..", "..", "elsewhere"), str(r / "website" / "src" / "linked"))
    os.symlink(".", str(r / "website" / "src" / "loop"))
    f = copy_findings(r)
    check(rules_at(f, "website/src/linked/x.ts", 1) == ["RESEARCH"],
          "a .ts file in a symlinked directory under website/src is scanned")
    p = run_py("check_copy.py", "--root", str(r), "--list")
    check("scanned  website/src/linked/x.ts" in p.stderr,
          "and --list names it under the path the site serves it at")
    check(not any("loop" in x.path for x in f) and p.returncode == 1,
          "a link back to its own directory is not walked twice (no endless loop)")
    if CAN_LOCK:
        r = make_repo(tmp, files={"website/src/ok.ts": "const a = 1;\n",
                                  "website/src/locked/x.ts": "const b = 2;\n"})
        locked = r / "website" / "src" / "locked"
        os.chmod(locked, 0)
        try:
            p = run_py("check_copy.py", "--root", str(r))
        finally:
            os.chmod(locked, 0o755)
        check(p.returncode == 2 and "locked" in p.stderr and "Traceback" not in p.stderr,
              f"a directory the walk cannot list exits 2, never clean (got {p.returncode})")


def test_check_disclosure_round2(tmp: Path) -> None:
    root = tmp / "disc-r2"

    section("check_disclosure: a printed path is masked where the hit was computed")
    write_tree(root, {"pub/zork/a.md": "clean\n", "pub2/quux-notes.md": "clean\n",
                      "pub3/sub/zork/b.md": "clean\n"})
    p = disclosure_lines("re:^zork\nre:(?i)\\Aquux\n", tmp, root / "pub",
                         root / "pub2" / "quux-notes.md", root / "pub3")
    out = p.stdout.splitlines()
    check(p.returncode == 1 and len(out) == 3, f"three path hits (got {out})")
    check(any(ln.endswith("pub/[#1]/a.md:0: private term #1") for ln in out),
          "an anchored entry on a walked directory name is masked")
    check(any(ln.endswith("pub2/[#2]-notes.md:0: private term #2") for ln in out),
          "an anchored entry on an explicit file name is masked")
    check(any(ln.endswith("pub3/sub/[#1]/b.md:0: private term #1") for ln in out),
          "a directory name is matched as its own component, so ^ anchors there too")
    check("zork" not in p.stdout + p.stderr and "quux" not in p.stdout.lower(),
          "no anchored term is printed")
    # a look-behind that holds on the name below the PATH ("zork/a.md") but not on the full
    # path ("pub/zork/a.md", where "b/" precedes it), and spans two components
    p = disclosure_lines("re:(?<!b/)zork/a\n", tmp, Path("pub"), cwd=root)
    check(p.stdout.splitlines() == ["pub/[#1].md:0: private term #1"],
          f"a look-behind entry is masked on the string its hit was computed on "
          f"(got {p.stdout.splitlines()})")
    # #1 matches the head of the word; #2 matches its tail only when no letter precedes it,
    # which masking #1 brings about, so "[#1]rk.md" would still show a match of #2
    two = CD.parse_denylist("re:zo(?=rk)\nre:(?<!\\w)rk\n")
    check(CD.path_indices(two, "zork.md") == [1]
          and CD.display_path(two, "pub/zork.md", "zork.md") == "pub/[#1]",
          "masking fails closed: a masked name that still matches prints as [#K] "
          f"(got {CD.display_path(two, 'pub/zork.md', 'zork.md')})")
    check(CD.display_path(CD.parse_denylist("zork\nre:\\[#1\n"), "pub/zork.md",
                          "zork.md") == "pub/[#1].md",
          "an entry that matches only inside a [#K] token is not residue")

    section("check_disclosure: the walk never skips content silently")
    write_tree(root, {
        "w/ok.md": "clean\n",
        "elsewhere/inner.md": "glint\n",
        "w/.venv/pyvenv.cfg": "home = x\n",
        "w/.venv/lib/site.md": "glint\n",
        "w/venv/notes.md": "glint\n",
        "w/build/page.html": "<p>glint</p>\n",
    })
    os.symlink(os.path.join("..", "elsewhere"), str(root / "w" / "linkdir"))
    os.symlink(".", str(root / "w" / "glint-loop"))
    p = disclosure_lines(DENYLIST, tmp, Path("w"), cwd=root)
    got = sorted(ln for ln in p.stdout.splitlines())
    want = sorted(["w/[#3]-loop:0: private term #3",
                   "w/build/page.html:1: private term #3",
                   "w/linkdir/inner.md:1: private term #3",
                   "w/venv/notes.md:1: private term #3"])
    check(got == want,
          f"a linked directory is followed, a loop is not re-entered but its name is "
          f"checked, a virtualenv is skipped, a plain venv/ and build/ are not "
          f"(got {got})")
    if CAN_LOCK:
        write_tree(root, {"lk/ok.md": "clean\n", "lk/locked/x.md": "glint\n"})
        os.chmod(root / "lk" / "locked", 0)
        try:
            p = disclosure_lines(DENYLIST, tmp, root / "lk")
        finally:
            os.chmod(root / "lk" / "locked", 0o755)
        check(p.returncode == 2 and "cannot read" in p.stderr and p.stdout == "",
              f"an unreadable directory exits 2, never '0 hits' (got {p.returncode})")
        write_tree(root, {"lk2/glint-dir/x.md": "clean\n"})
        os.chmod(root / "lk2" / "glint-dir", 0)
        try:
            p = disclosure_lines(DENYLIST, tmp, root / "lk2")
        finally:
            os.chmod(root / "lk2" / "glint-dir", 0o755)
        check(p.returncode == 2 and no_term_in(p.stderr),
              "and its name is masked in the error")

    section("check_disclosure: content renderings added in round 2")
    write_tree(root, {
        "r/a.md": "See [the repo](https://github.com/someone/zephyr-moss)\n",
        "r/b.astro": "\n".join([
            '<a href="/research/zephyr-moss/">x</a>',           # 1
            '<div id="zephyr_moss"></div>',                   # 2
            '<p>{"Zephyr"} Moss</p>',                         # 3
            '<p>Zephyr{" "}',                                 # 4
            "Moss</p>",                                       # 5
        ]) + "\n",
        "r/c.mmd": 'flowchart LR\n  a["Zephyr<br/>Moss"]\n  b["Zephyr#32;Moss"]\n',
        "r/d.md": "Zephyr and moss, apart; zephyr-mossy\n",
    })
    p = disclosure_lines(DENYLIST, tmp, Path("r"), cwd=root)
    got = sorted(p.stdout.splitlines())
    want = sorted(["r/a.md:1: private term #1",
                   "r/b.astro:1: private term #1", "r/b.astro:2: private term #1",
                   "r/b.astro:3: private term #1", "r/b.astro:4: private term #1",
                   "r/c.mmd:2: private term #1", "r/c.mmd:3: private term #1"])
    check(got == want,
          f"a slug in a URL, href or id, a string-literal expression, {{\" \"}} across a "
          f"line, a Mermaid <br/> and a Mermaid entity are all caught; words apart and a "
          f"longer word are not (got {got})")
    check(no_term_in(p.stdout + p.stderr), "and nothing matched is printed")


def test_leak_check_round2(tmp: Path) -> None:
    section("leak_check: history is read in check_disclosure's renderings")
    repo = Repo(tmp / "leak-r2")
    repo.commit("base", {"README.md": "Hello\n"})
    repo.git("branch", "pub")
    add = repo.commit("docs: add", {
        "docs/bold.md": "The **Zephyr** Moss idea\n",
        "docs/em.html": "<p>zephyr <em>moss</em></p>\n",
        "website/src/esc.ts": 'const s = "\\u0067lint";\n',
        "docs/link.md": "See [x](https://example.com/zephyr-moss)\n",
        "docs/jsx.astro": '<p>{"Zephyr"} Moss</p>\n',
    })
    repo.commit("docs: drop", {k: None for k in ("docs/bold.md", "docs/em.html",
                                                  "website/src/esc.ts", "docs/link.md",
                                                  "docs/jsx.astro")})
    deny = tmp / "leak-r2-deny.txt"
    deny.write_text(DENYLIST, encoding="utf-8")
    p = leak(repo, "pub..main", "--denylist", str(deny))
    out = p.stdout.splitlines()

    def has(where: str, rule: str) -> bool:
        return any(ln.startswith(where + ": [" + rule + "]") for ln in out)

    for path, label in (("docs/bold.md", "a phrase split by Markdown bold"),
                        ("docs/em.html", "a phrase split by an inline tag"),
                        ("website/src/esc.ts", "a word behind a \\u escape"),
                        ("docs/link.md", "a phrase written as a slug in a URL"),
                        ("docs/jsx.astro", "a phrase split by a string expression")):
        check(has(f"{add[:10]}:{path}:1", "DENYLIST"),
              f"{label}, added and removed inside the range, is caught")
    check(no_term_in(p.stdout + p.stderr), "and never printed")
    msg = repo.commit("docs: see zephyr-moss")
    p = leak(repo, "pub..main", "--denylist", str(deny))
    check(any(ln.startswith(f"{msg[:10]}: message line 1: [DENYLIST]")
              for ln in p.stdout.splitlines()),
          "a slug in a commit message is caught")

    section("leak_check: a missing sibling is exit 2, not a traceback")
    lone = tmp / "lone-leak"
    lone.mkdir()
    shutil.copy(HERE / "leak_check.py", lone / "leak_check.py")
    p = subprocess.run([sys.executable, "-B", str(lone / "leak_check.py"), "--range",
                        "a..b", "--no-denylist"], capture_output=True, text=True)
    check(p.returncode == 2 and "cannot run" in p.stderr and "Traceback" not in p.stderr,
          f"leak_check without check_disclosure.py exits 2 (got {p.returncode})")
    check(str(lone) not in p.stderr and str(lone.resolve()) not in p.stderr,
          "and does not print the absolute path of the checkout")
    lone_cc = tmp / "lone-cc" / "tools" / "publish"
    lone_cc.mkdir(parents=True)
    shutil.copy(HERE / "check_copy.py", lone_cc / "check_copy.py")
    shutil.copy(HERE.parent / "ledger_check.py", lone_cc.parent / "ledger_check.py")
    p = subprocess.run([sys.executable, "-B", str(lone_cc / "check_copy.py"), "--root",
                        str(lone_cc.parent.parent)], capture_output=True, text=True)
    check(p.returncode == 2 and "Traceback" not in p.stderr
          and str(lone_cc) not in p.stderr and str(lone_cc.resolve()) not in p.stderr,
          f"check_copy without check_disclosure.py exits 2, no absolute path "
          f"(got {p.returncode}: {p.stderr.strip()})")


# ─────────────────────────────────────────────────────────────────────────────
# review round 3
# ─────────────────────────────────────────────────────────────────────────────

TR_S = "\u015f"                              # s with cedilla
WORD_TR = "Bili" + TR_S + "sel"              # a Turkish word, assembled
ESC_TR = "Bili\\u015fsel"                    # the same word with its letter as a \u escape


def test_check_copy_round3(tmp: Path) -> None:
    section("check_copy: docs/diagrams/*.mmd are archived report figures, not surfaces")
    r = make_repo(tmp, files={
        "docs/diagrams/repo_map.mmd":
            "flowchart LR\n  t[tests: 5 suites]\n  b[ba" + TR_G + "lam]\n  c[3 pJ]\n",
        "website/src/diagrams/live.mmd": "flowchart LR\n  t[tests: 5 suites]\n",
    })
    f = copy_findings(r)
    check(not any(x.path.startswith("docs/diagrams/") for x in f),
          "a stale figure in docs/diagrams/*.mmd is not a finding: they are the archived "
          "report figures (D-030 keeps their render), published nowhere, historical by design")
    p = run_py("check_copy.py", "--root", str(r), "--list")
    check("docs/diagrams" not in p.stderr, "and they are not listed as scanned")
    check(rules_at(f, "website/src/diagrams/live.mmd", 2) == ["COUNT"],
          "a Mermaid source the site itself carries (under website/src) is still a surface")

    section("check_copy: string escapes are read as they render")
    r = make_repo(tmp, files={
        "website/src/data/strings.json": '{"title": "' + ESC_TR + ' Harita"}\n',
        "website/src/data/gen.json": json.dumps({"title": WORD_TR}) + "\n",   # ensure_ascii
        "website/src/data/strings.ts": 'export const t = "' + ESC_TR + '";\n',
        "website/src/components/A.tsx": '<p>{"' + ESC_TR + '"}</p>\n',
        "website/src/data/count.json": '{"x": "618\\u0020assertions"}\n',
        "website/src/components/B.astro":
            '<p>{"' + RESEARCH_TERM[:-4] + '\\u0069' + RESEARCH_TERM[-3:] + '"}</p>\n',
        "website/src/data/lines.ts":
            'const a = 1;\nconst b = 2;\nconst s = "a\\x0a1 p\\u004a";\n',
    })
    check("\\u015f" in (r / "website/src/data/gen.json").read_text(encoding="utf-8"),
          "fixture: json.dumps writes the letter as an escape, as generated data would")
    f = copy_findings(r)
    for path in ("website/src/data/strings.json", "website/src/data/gen.json",
                 "website/src/data/strings.ts", "website/src/components/A.tsx"):
        check(rules_at(f, path, 1) == ["LANGUAGE"],
              f"a Turkish letter written as a \\u escape is a LANGUAGE finding ({path})")
    check(rules_at(f, "website/src/data/count.json", 1) == ["COUNT"],
          "a count joined by an escaped space is a COUNT finding")
    check(rules_at(f, "website/src/components/B.astro", 1) == ["RESEARCH"],
          "a research term with an escaped letter inside a string expression is caught")
    check(rules_at(f, "website/src/data/lines.ts") == ["ENERGY"]
          and rules_at(f, "website/src/data/lines.ts", 3) == ["ENERGY"],
          "an escaped unit is caught, and an escape that decodes to a line break is left as "
          "written, so the finding stays on its line")

    section("check_copy: COUNT and ENERGY across a line break")
    r = make_repo(tmp, files={
        "website/src/pages/a.astro":
            "<p>\n  The harness runs 30 assertions across 25\n  suites, and an event costs "
            "about 3.2\n  pJ in the estimate.\n</p>\n",
        "website/src/pages/ok.astro": "<!-- ledger:allow-count -->\n<p>Once 25\n  suites.</p>\n",
        "docs/assets/b.svg": '<svg xmlns="http://www.w3.org/2000/svg"><text><tspan>618</tspan>'
                             '\n<tspan>assertions</tspan></text></svg>\n',
        "README.md": "Intro.\nWe ran 618\nassertions here.\n",
    })
    f = copy_findings(r)
    check(rules_at(f, "website/src/pages/a.astro", 2) == ["COUNT"],
          "a suite count wrapped away from its unit is caught, at the line where it starts")
    check(rules_at(f, "website/src/pages/a.astro", 3) == ["ENERGY"],
          "and an energy figure wrapped away from its unit")
    check(rules_at(f, "website/src/pages/a.astro") == ["COUNT", "ENERGY"],
          "and nothing else on that page (30 is the ledger's total)")
    check(rules_at(f, "website/src/pages/ok.astro") == [],
          "ledger:allow-count above the line where a wrapped count starts permits it")
    check(rules_at(f, "docs/assets/b.svg", 1) == ["COUNT"],
          "a count split across two tspans on two source lines is caught")
    check(rules_at(f, "README.md", 2) == ["COUNT"],
          "a count hard-wrapped in prose, which C2 cannot see, is reported here")

    section("check_copy: a finding is dropped only where ledger_check itself reports it")
    r = make_repo(tmp, files={
        "README.md": "618\u2028assertions\n",
        "MOC.md": "Intro.\n618\x0cassertions\n",
        "docs/research/bom.md": "\ufeff618 assertions\n",
        "elsewhere/linked.md": "618 assertions\nThe substrate " + CLAIM2 + ".\n",
    })
    os.symlink(os.path.join("..", "..", "elsewhere"), str(r / "docs" / "research" / "ext"))
    f = copy_findings(r)
    check(rules_at(f, "README.md", 1) == ["COUNT"],
          "618<U+2028>assertions: ledger_check's splitlines() sees two lines and C2 reports "
          "nothing, so the count is reported here")
    check(rules_at(f, "MOC.md", 2) == ["COUNT"], "and so is a form feed between the two")
    check(rules_at(f, "docs/research/bom.md") == [],
          "a raw count C2 does report is still dropped (a leading byte-order mark, which "
          "ledger_check keeps, does not stop the two splits agreeing)")
    lc_sees = "docs/research/ext/linked.md" in CC.ledger_reads(r)
    got = sorted(set(rules_at(f, "docs/research/ext/linked.md")))
    check(got == ([] if lc_sees else ["CLAIM", "COUNT"]),
          f"a prose file reached through a symlinked directory keeps its COUNT and CLAIM "
          f"findings unless ledger_check's own walk reads it (it "
          f"{'does' if lc_sees else 'does not'} on this interpreter; got {got})")

    section("check_copy: a UTF-16 surface is read as text")
    r = make_repo(tmp, files={"docs/research/u16.md": "x\n", "website/src/u16.ts": "x\n"})
    body = WORD_TR + " harita. It costs 3 pJ. Here " + RESEARCH_TERM + ".\n"
    (r / "docs" / "research" / "u16.md").write_bytes(body.encode("utf-16"))
    (r / "website" / "src" / "u16.ts").write_bytes(("// " + body).encode("utf-16"))
    f = copy_findings(r)
    for path in ("docs/research/u16.md", "website/src/u16.ts"):
        check(sorted(rules_at(f, path, 1)) == ["ENERGY", "LANGUAGE", "RESEARCH"],
              f"a UTF-16 file is decoded, so its letter, figure and term are found ({path}; "
              f"got {rules_at(f, path)})")

    section("check_copy: negation cues are never looser than C4's")
    neg_lines = [
        "<p>Phase no. 2: this map " + FIRST + " of its kind.</p>",      # 1 "no." is no cue
        "<p>Plain line.</p>",                                          # 2
        "<p>a no-op step; " + RESEARCH_TERM + "</p>",                         # 3 nor is "no-op"
        "<p>Plain line.</p>",                                          # 4
        "<p>(no) " + RESEARCH_TERM + "</p>",                                  # 5 nor "(no)"
        "<p>Plain line.</p>",                                          # 6
        "<p>There is no sense in which " + RESEARCH_TERM + ".</p>",           # 7 "no " still negates
    ]
    r = make_repo(tmp, files={"website/src/pages/neg.astro": "\n".join(neg_lines) + "\n"})
    f = copy_findings(r)
    for line, label in ((1, "Phase no. 2"), (3, "a no-op step"), (5, "(no)")):
        low = [neg_lines[line - 1].lower()]
        term = FIRST if line == 1 else RESEARCH_TERM
        check(rules_at(f, "website/src/pages/neg.astro", line) == ["RESEARCH"]
              and not CC.LC._is_negated(low, 0, low[0].index(term)),
              f"'{label}' negates nothing, here as in C4 (line {line})")
    check(rules_at(f, "website/src/pages/neg.astro", 7) == [],
          "'no ' followed by a space still negates")

    section("check_copy: neither term list can be switched off by a ledger edit")
    cases = (
        ("research_forbidden_claim_terms", [], "an empty research list"),
        ("research_forbidden_claim_terms", {"_README": "x", "terms": []},
         "an object whose 'terms' is empty"),
        ("research_forbidden_claim_terms", [""], "a research list holding only a blank term"),
        ("research_forbidden_claim_terms", {"terms": [RESEARCH_TERM, "  "]},
         "a blank research term next to a real one"),
        ("forbidden_claim_terms", [], "an empty claim list"),
        ("forbidden_claim_terms", [""], "a claim list holding only a blank term"),
    )
    for key, value, label in cases:
        led = dict(BASE_LEDGER)
        led[key] = value
        r = make_repo(tmp, ledger=led, files={"README.md": "Here " + RESEARCH_TERM + ".\n"})
        p = run_py("check_copy.py", "--root", str(r))
        check(p.returncode == 2 and key in p.stderr and "Traceback" not in p.stderr,
              f"{label} is an invalid ledger, exit 2 (got {p.returncode}: {p.stderr.strip()})")
    for key in ("research_forbidden_claim_terms", "forbidden_claim_terms"):
        led = dict(BASE_LEDGER)
        led.pop(key)
        r = make_repo(tmp, ledger=led, files={"README.md": "Here " + RESEARCH_TERM + ".\n"})
        p = run_py("check_copy.py", "--root", str(r))
        check(p.returncode == 2 and key in p.stderr and "Traceback" not in p.stderr,
              f"a ledger without {key} exits 2, never a notice and exit 0 "
              f"(got {p.returncode})")

    section("check_copy: ENERGY carries no word boundary after fewer/less")
    r = make_repo(tmp, files={"website/src/pages/e.astro":
                              "<p>a 10x lesser cost</p>\n<p>plain</p>\n<p>10\u00d7 lessened</p>\n"})
    f = copy_findings(r)
    check(rules_at(f, "website/src/pages/e.astro", 1) == ["ENERGY"]
          and rules_at(f, "website/src/pages/e.astro", 3) == ["ENERGY"],
          "'10x lesser' and '10\u00d7 lessened' are ENERGY findings, as the spec regex "
          "\\d+\\s*[x\u00d7]\\s*(fewer|less) finds them")
    check(rules_at(f, "website/src/pages/e.astro", 2) == [], "a plain line passes")


def test_check_disclosure_round3(tmp: Path) -> None:
    root = tmp / "disc-r3"

    section("check_disclosure: a plain entry's separators are two-sided")
    hy = CD.parse_denylist("zephyr-moss\n")
    for text, label in (("a zephyr moss b", "a space"), ("a zephyr_moss b", "an underscore"),
                        ("a zephyr\n  moss b", "a line break"),
                        ("a zephyr\u2011moss b", "a non-breaking hyphen"),
                        ("a Zephyr-Moss b", "its own spelling")):
        check([i for _, i in CD.find_hits(hy, text)] == [1],
              f"a hyphenated plain entry matches the phrase written with {label}")
    check(CD.path_indices(hy, "site/zephyr_moss/index.html") == [1],
          "and a directory named with an underscore")
    check(CD.find_hits(hy, "zephyrmoss, zephyr-mossy") == [],
          "but not run together, nor inside a longer word")
    check(CD.find_hits(CD.parse_denylist("zephyr_moss\n"), "the zephyr moss rule") == [(1, 1)],
          "an entry written with an underscore matches the spaced phrase")
    write_tree(root, {"hy/zephyr_moss/a.md": "clean\n", "hy/b.md": "the zephyr\nmoss rule\n"})
    p = disclosure_lines("zephyr-moss\n", tmp, Path("hy"), cwd=root)
    got = sorted(p.stdout.splitlines())
    check(got == ["hy/[#1]/a.md:0: private term #1", "hy/b.md:1: private term #1"]
          and no_term_in(p.stdout + p.stderr),
          f"end to end: a directory and a wrapped phrase, masked and never printed (got {got})")
    p = disclosure_lines("glint\n-- \n", tmp, root / "hy")
    check(p.returncode == 2 and "#2" in p.stderr,
          f"a plain entry made only of separators is refused, by number (got {p.returncode})")

    section("check_disclosure: a Turkish letter in a plain entry also matches its ASCII letter")
    entries = CD.parse_denylist(DENYLIST)            # #4 is the invented BLORP, decomposed
    for text, label in (("x blogrp y", "the transliterated spelling"),
                        ("x BLOGRP y", "in capitals"), ("x " + BLORP_NFC + " y", "and the "
                                                        "Turkish spelling, as before")):
        check([i for _, i in CD.find_hits(entries, text)] == [4], f"#4 matches {label}")
    tr = CD.parse_denylist("\u00e7orbel \u015fiv\n\u0130mzor\n")    # invented words
    check(CD.find_hits(tr, "a corbel siv b") == [(1, 1)]
          and CD.find_hits(tr, "a CORBEL SIV b") == [(1, 1)],
          "c-cedilla reads c and s-cedilla reads s, in any case")
    check(CD.find_hits(tr, "imzor") == [(1, 2)] and CD.find_hits(tr, "Imzor") == [(1, 2)],
          "a dotted capital I reads i or I")
    check(CD.find_hits(tr, "corbelsiv, imzory") == [], "whole words still")
    write_tree(root, {"tr/corbel_siv/a.md": "clean\n", "tr/b.md": "the corbel siv rule\n"})
    p = disclosure_lines("\u00e7orbel \u015fiv\n", tmp, Path("tr"), cwd=root)
    got = sorted(p.stdout.splitlines())
    check(got == ["tr/[#1]/a.md:0: private term #1", "tr/b.md:1: private term #1"]
          and "corbel" not in (p.stdout + p.stderr).lower(),
          f"end to end, index-only and masked (got {got})")

    section("check_disclosure: a walked binary file's printable runs are read")
    packed = zlib.compress(b"glint glint glint glint")
    check(b"glint" not in packed, "fixture: the compressed bytes do not hold the word")
    write_tree(root, {
        "bin/ok.md": "clean\n",
        "bin/img.png": b"\x89PNG\r\n\x1a\n\x00\x00tEXt\x00zephyr moss\x00",
        "bin/u16.dat": b"\x00\x01" + "the glint here".encode("utf-16-le") + b"\x00\x00\xff",
        "bin/short.dat": b"\x00\x01glint\x00\xff",
        "bin/packed.png": b"\x89PNG\r\n\x1a\n\x00\x00IDAT" + packed,
    })
    p = disclosure_lines(DENYLIST, tmp, Path("bin"), cwd=root)
    got = sorted(p.stdout.splitlines())
    check(got == ["bin/img.png:0: private term #1", "bin/u16.dat:0: private term #3"],
          f"an ASCII run (a PNG tEXt chunk) and a UTF-16 run are read and reported at line "
          f"0, the name unmasked because only the content hit (got {got})")
    check(no_term_in(p.stdout + p.stderr), "and nothing matched is printed")
    check("4 binary file(s)" in p.stderr and "1 text file(s)" in p.stderr,
          f"the summary counts the binary files read (got {p.stderr.strip()})")
    check(not any("short.dat" in ln for ln in got),
          "known limit, asserted: a run under six characters standing alone between "
          "non-printable bytes is not read")
    check(not any("packed.png" in ln for ln in got),
          "known limit, asserted: compressed content (PNG image data) cannot be read")
    p = disclosure_lines(DENYLIST, tmp, root / "bin" / "u16.dat")
    check(p.returncode == 1 and p.stdout.strip().endswith("u16.dat:0: private term #3"),
          "a binary file named explicitly is read as printable runs as well as text")


def test_leak_check_round3(tmp: Path) -> None:
    deny = tmp / "leak-r3-deny.txt"
    deny.write_text(DENYLIST, encoding="utf-8")

    def lines_of(p: subprocess.CompletedProcess) -> List[str]:
        return p.stdout.splitlines()

    def has(out: List[str], where: str, rule: str) -> bool:
        return any(ln.startswith(where + ": [" + rule + "]") for ln in out)

    section("leak_check: the tag shape, with content after the token")
    repo = Repo(tmp / "leak-r3")
    repo.commit("base", {"README.md": "Hello\n"})
    repo.git("branch", "pub")
    tok_s = "QAZ" + "\u015e" + "UX"                  # invented tokens: only the SHAPE counts
    tok_g = "QAZ" + "\u011e" + "UX"
    tok_i = "QAZ" + "\u0130" + "UX"
    c1 = repo.commit("docs: tags", {
        "docs/notes.md": "\n".join([
            "Claim A [" + tok_s + "; ab cd] here.",              # 1
            "Claim B [" + tok_s + ": ab] here.",                 # 2
            "Claim C [" + tok_i + " — lower case] here.",   # 3
            "Claim D [" + tok_s + "] here.",                     # 4
            "Claim E [QAZ: ab] here.",                           # 5 no Turkish letter
            "Claim F [QAZ B] here.",                             # 6 no Turkish letter
            "See [Data](x) and [A-1] here.",                     # 7 ordinary brackets
        ]) + "\n",
        "src/mod.py": "# [" + tok_g + ": ab cd]\n",
    })
    out = lines_of(leak(repo, "pub..main", "--no-denylist"))
    for line in (1, 2, 3, 4):
        check(has(out, f"{c1[:10]}:docs/notes.md:{line}", "UNVERIFIED-TAG"),
              f"a tag with content after its token is the tag shape (line {line})")
    check(has(out, f"{c1[:10]}:src/mod.py:1", "UNVERIFIED-TAG"),
          "outside the English-only paths too, where no LANGUAGE rule backs it up")
    check(not any(f"docs/notes.md:{n}:" in ln for n in (5, 6, 7) for ln in out),
          "known limit, asserted: a tag whose token holds no Turkish letter is not the "
          "shape (nor is an ordinary bracket), so without the denylist it passes")
    tag_deny = tmp / "leak-r3-tag-deny.txt"
    tag_deny.write_text("re:\\[QAZ\\b\n", encoding="utf-8")
    p = leak(repo, "pub..main", "--denylist", str(tag_deny))
    out = lines_of(p)
    check(has(out, f"{c1[:10]}:docs/notes.md:5", "DENYLIST")
          and has(out, f"{c1[:10]}:docs/notes.md:6", "DENYLIST"),
          "a denylist entry written as a prefix regex catches those, whatever follows")
    check("QAZ" not in p.stdout + p.stderr and "\u015e" not in p.stdout,
          "and no tag is echoed")
    check("|" not in LK.TAG_RE.pattern, "the tag rule is still a shape with no words in it")

    section("leak_check: diff.context=0 in the repository's configuration hides nothing")
    ctx = Repo(tmp / "leak-r3-ctx")
    ctx.git("config", "diff.context", "0")
    ctx.commit("base", {"README.md": "Hello\n"})
    ctx.git("branch", "pub")
    ctx.commit("docs: notes", {"notes.md": "one\ntwo zephyr\nthree\n"})
    c = ctx.commit("docs: more", {"notes.md": "one\ntwo zephyr\nmoss is here\nthree\n"})
    p = leak(ctx, "pub..main", "--denylist", str(deny))
    check(p.returncode == 1 and has(lines_of(p), f"{c[:10]}:notes.md:3", "DENYLIST"),
          f"a phrase an added line completes next to an unchanged line is caught with "
          f"diff.context=0 set (got {p.returncode}: {lines_of(p)})")

    section("leak_check: --denylist-env (the CI secret)")
    env = git_env(TEST_LEAK_LIST=DENYLIST)
    p = run_py("leak_check.py", "--root", str(ctx.root), "--range", "pub..main",
               "--denylist-env", "TEST_LEAK_LIST", env=env)
    check(p.returncode == 1 and has(lines_of(p), f"{c[:10]}:notes.md:3", "DENYLIST")
          and no_term_in(p.stdout + p.stderr),
          f"the denylist can come from an environment variable (got {p.returncode})")
    env = {k: v for k, v in git_env().items() if k != "TEST_LEAK_LIST"}
    p = run_py("leak_check.py", "--root", str(ctx.root), "--range", "pub..main",
               "--denylist-env", "TEST_LEAK_LIST", env=env)
    check(p.returncode == 2 and "not set" in p.stderr, "an unset variable exits 2")
    env["TEST_LEAK_LIST"] = "  \n"
    p = run_py("leak_check.py", "--root", str(ctx.root), "--range", "pub..main",
               "--denylist-env", "TEST_LEAK_LIST", env=env)
    check(p.returncode == 2 and "empty" in p.stderr, "an empty variable exits 2")

    section("leak_check: one invalid byte does not turn a page into binary content")
    inv = Repo(tmp / "leak-r3-inv")
    inv.commit("base", {"README.md": "Hello\n"})
    inv.git("branch", "pub")
    c = inv.commit("docs: page", {"docs/research/a.md":
                                  b"Caf\xe9 note\nBu bir a\xc3\xa7\xc4\xb1klama sat\xc4\xb1r"
                                  b"\xc4\xb1\nid " + ("E-" + "07").encode() + b"\n"})
    p = leak(inv, "pub..main", "--no-denylist")
    out = lines_of(p)
    check(has(out, f"{c[:10]}:docs/research/a.md:2", "LANGUAGE"),
          f"UTF-8 Turkish next to one stray Latin-1 byte is read as text, LANGUAGE included "
          f"(got {out})")
    check(has(out, f"{c[:10]}:docs/research/a.md:3", "PRIVATE-ID")
          and not any("binary content" in ln for ln in out),
          "every rule applies at its line, and nothing is reported as binary content")

    section("leak_check: private ids in any letter case")
    ids = Repo(tmp / "leak-r3-ids")
    ids.commit("base", {"README.md": "Hello\n"})
    ids.git("branch", "pub")
    low_e, low_adr, low_q = "e-" + "07", "adr-" + "001", "q-m-" + "3"
    c = ids.commit("docs: ids", {"docs/notes-" + low_e + ".md":
                                 "see " + low_adr + " and " + low_q + "\nplain 1e-12 and "
                                 "type-12\n"})
    p = leak(ids, "pub..main", "--no-denylist")
    out = lines_of(p)
    check(has(out, "docs/notes-[ID].md: file name", "PRIVATE-ID"),
          "a lower-case experiment id in a file name is caught, masked")
    check(sum(ln.startswith(f"{c[:10]}:docs/notes-[ID].md:1: [PRIVATE-ID]") for ln in out) == 2,
          "lower-case decision-record and open-question ids in a line are caught")
    check(not any(":2: [PRIVATE-ID]" in ln for ln in out), "1e-12 and type-12 are still not ids")
    check(not any(x in p.stdout + p.stderr for x in (low_e, low_adr, low_q)),
          "and no id is echoed")
    check(all(rx.flags & re.IGNORECASE for _, rx in LK.PRIVATE_ID_RES),
          "every id pattern is case-insensitive")

    section("leak_check: English-only paths are compared case-folded")
    for path in ("readme.md", "Readme.md", "contributing.md", "docs/Research/x.md",
                 "Website/src/a.ts", "TOOLS/PUBLISH/x.py"):
        check(LK.english_only(path), f"{path} is English-only")
    check(not LK.english_only("docs/researchx.md") and not LK.english_only("SETUP.md"),
          "and the list is no wider than before")
    cf = Repo(tmp / "leak-r3-cf")
    cf.commit("base", {"SETUP.md": "x\n"})
    cf.git("branch", "pub")
    c = cf.commit("docs: readme", {"readme.md": "Hello\nEski sat\u0131r\n",
                                   "docs/Research/x.md": "Bir " + WORD_TR + "\n"})
    out = lines_of(leak(cf, "pub..main", "--no-denylist"))
    check(has(out, f"{c[:10]}:readme.md:2", "LANGUAGE"),
          "a Turkish line in a root readme.md (the README GitHub renders) is caught")
    check(has(out, f"{c[:10]}:docs/Research/x.md:1", "LANGUAGE"),
          "and in docs/Research/, which a case-insensitive file system serves as docs/research/")


# ─────────────────────────────────────────────────────────────────────────────
# review round 4
# ─────────────────────────────────────────────────────────────────────────────

def manifest_text(sections: List[dict], **extra) -> str:
    """A publication manifest in the shape core.load_manifest accepts, one key per line."""
    m = {"_README": ["fixture"], "site_base": "/psyche/", "repo": "o/r", "sections": sections,
         "never_publish": ["docs/design/"]}
    m.update(extra)
    return json.dumps(m, indent=2, ensure_ascii=False) + "\n"


def manifest_page(title: Optional[str] = None, wiki: str = "Page-A",
                  slug: str = "a", src: str = "docs/research/a.md") -> dict:
    page = {"src": src, "slug": slug, "wiki": wiki}
    if title is not None:
        page["title"] = title
    return page


def manifest_at(f, pointer: str) -> List[str]:
    return sorted(x.rule for x in f
                  if x.path == "docs/publish.json" and x.message.endswith(f"(at {pointer})"))


def test_check_copy_round4(tmp: Path) -> None:
    section("check_copy: docs/publish.json is a copy surface (the sidebar and the wiki)")
    text = manifest_text([{"title": "Ba" + TR_G + "lam, 5 suites, 3 pJ",
                           "pages": [manifest_page(title="618 assertions")]}])
    r = make_repo(tmp, files={"docs/publish.json": text})
    f = copy_findings(r)
    check(manifest_at(f, "/sections/0/title") == ["COUNT", "ENERGY", "LANGUAGE"],
          f"a section title (every page's sidebar label) is read with every rule "
          f"(got {manifest_at(f, '/sections/0/title')})")
    check(manifest_at(f, "/sections/0/pages/0/title") == ["COUNT"],
          "a page title (it replaces the page's level-one heading on the site and the wiki) is read")
    lines = text.split("\n")
    sec_line = next(i for i, ln in enumerate(lines, 1) if "5 suites" in ln)
    check(all(x.line == sec_line for x in f if x.message.endswith("(at /sections/0/title)")),
          "a finding is placed on the line the value sits on")
    p = run_py("check_copy.py", "--root", str(r), "--list")
    check(p.returncode == 1 and "scanned  docs/publish.json" in p.stderr
          and "1 surface(s) scanned" in p.stderr,
          f"the CLI exits 1 and lists the manifest as scanned (got {p.returncode}: "
          f"{p.stderr.strip()})")
    check(TR_G not in p.stdout + p.stderr, "and no Turkish letter is echoed")

    section("check_copy: manifest wiki names, slugs and sources are read too")
    hyph = FIRST.replace(" ", "-")
    r = make_repo(tmp, files={"docs/publish.json": manifest_text([
        {"title": "Cognitive maps (active)", "pages": [
            manifest_page(wiki="Gate-A-" + hyph),
            manifest_page(wiki="Notes", slug="research/5_suites", src="docs/research/b.md"),
            manifest_page(wiki="Tr", slug="research/ba" + TR_G + "lam", src="docs/research/c.md"),
        ]}])})
    f = copy_findings(r)
    check(manifest_at(f, "/sections/0/pages/0/wiki") == ["RESEARCH"],
          "a wiki name is read as GitHub shows it, hyphens as spaces")
    check(manifest_at(f, "/sections/0/pages/1/slug") == ["COUNT"],
          "an underscore is read as a space too")
    check(manifest_at(f, "/sections/0/pages/2/slug") == ["LANGUAGE"],
          "a slug is English-only too")
    check(manifest_at(f, "/sections/0/title") == [], "a plain title passes")

    section("check_copy: manifest titles are read as the wiki's Markdown renders them")
    r = make_repo(tmp, files={"docs/publish.json": manifest_text([
        {"title": "618 **assertions**", "pages": [
            manifest_page(title="5<br/>suites"),
            manifest_page(title="Where *" + RESEARCH_TERM + "*", wiki="B", slug="b",
                          src="docs/research/b.md"),
            manifest_page(title="3&nbsp;pJ", wiki="C", slug="c", src="docs/research/c.md"),
        ]}])})
    f = copy_findings(r)
    check(manifest_at(f, "/sections/0/title") == ["COUNT"],
          "a count split by emphasis is caught (the wiki writes titles into Markdown)")
    check(manifest_at(f, "/sections/0/pages/0/title") == ["COUNT"],
          "a count split by an inline tag is caught")
    check(manifest_at(f, "/sections/0/pages/1/title") == ["RESEARCH"],
          "a term inside emphasis is caught")
    check(manifest_at(f, "/sections/0/pages/2/title") == ["ENERGY"],
          "an energy figure behind an entity is caught")

    section("check_copy: each manifest string is its own unit, with no pragma")
    r = make_repo(tmp, files={"docs/publish.json": manifest_text([
        {"title": "We make no claim that", "pages": [
            manifest_page(title=RESEARCH_TERM),
            manifest_page(title="No claim that " + RESEARCH_TERM, wiki="B", slug="b",
                          src="docs/research/b.md"),
            manifest_page(title="ledger:allow-claim " + RESEARCH_TERM, wiki="C", slug="c",
                          src="docs/research/c.md"),
        ]}])})
    f = copy_findings(r)
    check(manifest_at(f, "/sections/0/pages/0/title") == ["RESEARCH"],
          "no negation carries over from a sibling string")
    check(manifest_at(f, "/sections/0/pages/1/title") == [],
          "a term negated inside its own string passes")
    check(manifest_at(f, "/sections/0/pages/2/title") == ["RESEARCH"],
          "a manifest string cannot carry a pragma (it would render as copy)")

    section("check_copy: a manifest escape is read decoded; a bad manifest exits 2")
    r = make_repo(tmp, files={"docs/publish.json":
                              '{"sections": [{"title": "ba\\u011flam", "pages": []}]}\n'})
    check(manifest_at(copy_findings(r), "/sections/0/title") == ["LANGUAGE"],
          "a Turkish letter written as a JSON escape is caught")
    r = make_repo(tmp, files={"docs/publish.json": "{ not json"})
    p = run_py("check_copy.py", "--root", str(r))
    check(p.returncode == 2 and "docs/publish.json" in p.stderr,
          f"a manifest that is not JSON exits 2, never clean (got {p.returncode})")
    r = make_repo(tmp, files={"docs/publish.json":
                              '{\n  "sections": [{"title": "' + RESEARCH_TERM + '", "title": "ok",'
                              ' "pages": []}]\n}\n'})
    p = run_py("check_copy.py", "--root", str(r))
    check(p.returncode == 2 and "repeats" in p.stderr and RESEARCH_TERM not in p.stderr,
          f"a key repeated inside one manifest object exits 2 (got {p.returncode})")
    r = make_repo(tmp)
    check(not (r / "docs" / "publish.json").exists() and copy_findings(r) == [],
          "a repository with no manifest is still fine")

    section("check_copy: the manifest honours the quarantine lists, LANGUAGE excepted")
    led = json.loads(json.dumps(BASE_LEDGER))
    led["claim_quarantine_paths"] = ["docs/publish.json"]
    led["count_quarantine_paths"] = ["docs/publish.json"]
    r = make_repo(tmp, ledger=led, files={"docs/publish.json": manifest_text([
        {"title": RESEARCH_TERM + ", 5 suites, 3 pJ, ba" + TR_G + "lam", "pages": []}])})
    check(manifest_at(copy_findings(r), "/sections/0/title") == ["LANGUAGE"],
          "a quarantined manifest still gets LANGUAGE, and only LANGUAGE")

    section("check_copy: the docstring names where the sidebar labels are read")
    doc = CC.__doc__ or ""
    check("sidebar labels shown on every page" not in doc,
          "astro.config is no longer said to hold the sidebar labels")
    check("every string value in docs/publish.json" in doc and "sidebar.json" in doc,
          "the manifest is listed as a surface, and the staged sidebar is explained")


# ─────────────────────────────────────────────────────────────────────────────
# review round 5
# ─────────────────────────────────────────────────────────────────────────────

def _is_utf8(data: bytes) -> bool:
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def test_leak_check_round5(tmp: Path) -> None:
    def has(out: List[str], where: str, rule: str) -> bool:
        return any(ln.startswith(where + ": [" + rule + "]") for ln in out)

    section("leak_check: UTF-16 whose added lines are valid UTF-8 byte by byte")
    body = "\n".join(["plain line",                               # 1
                      "id " + EXP_ID + " here",                   # 2
                      "path " + HOME + "/x",                      # 3
                      "Bir " + WORD_TR + " not"]) + "\n"          # 4 s-cedilla: 5F 01
    plain16 = body.encode("utf-16-le")                            # no byte-order mark
    check(b"\x00" in plain16 and _is_utf8(plain16)
          and CD.text_encoding(plain16) == "utf-16-le",
          "fixture: BOM-less UTF-16LE that is valid UTF-8 byte by byte, known by its NULs")
    repo = Repo(tmp / "leak-r5")
    repo.commit("base", {"README.md": "Hello\n"})
    repo.git("branch", "pub")
    c1 = repo.commit("docs: wide", {"docs/plain16.txt": plain16,
                                    "docs/research/plain16.txt": plain16})
    head = "Title\nPlain\n"
    c2 = repo.commit("docs: bom", {"docs/research/n.txt": head.encode("utf-16")})
    grown = head + "Bir " + WORD_TR + " daha\nsee " + EXP_ID + "\npath " + HOME + "/y\n"
    grown16 = grown.encode("utf-16")
    added = grown16[len(head.encode("utf-16")):]
    check(_is_utf8(added) and b"\x00" in added
          and grown16[:2] in (b"\xff\xfe", b"\xfe\xff"),
          "fixture: the appended bytes of the BOM'd file are valid UTF-8 and hold NULs")
    c3 = repo.commit("docs: append", {"docs/research/n.txt": grown16})
    p = leak(repo, "pub..main", "--no-denylist")
    out = p.stdout.splitlines()
    s1, s2, s3 = c1[:10], c2[:10], c3[:10]
    check(p.returncode == 1, f"the range is not clean (got {p.returncode}: {p.stderr.strip()})")
    check(has(out, f"{s1}:docs/plain16.txt:2", "PRIVATE-ID")
          and has(out, f"{s1}:docs/plain16.txt:3", "HOME-PATH"),
          f"a new BOM-less UTF-16LE file: the id and the home path at their lines (got {out})")
    check(not any(f"{s1}:docs/plain16.txt" in ln and "[LANGUAGE]" in ln for ln in out),
          "and no LANGUAGE outside the English-only paths")
    check(has(out, f"{s1}:docs/research/plain16.txt:4", "LANGUAGE")
          and has(out, f"{s1}:docs/research/plain16.txt:2", "PRIVATE-ID")
          and has(out, f"{s1}:docs/research/plain16.txt:3", "HOME-PATH"),
          "the same file under docs/research/: LANGUAGE too, at the Turkish word's line")
    check(not any(ln.startswith(s2) for ln in out), "the clean BOM'd file adds nothing")
    check(has(out, f"{s3}:docs/research/n.txt:3", "LANGUAGE")
          and has(out, f"{s3}:docs/research/n.txt:4", "PRIVATE-ID")
          and has(out, f"{s3}:docs/research/n.txt:5", "HOME-PATH"),
          f"lines appended to a BOM'd UTF-16 file: LANGUAGE, PRIVATE-ID and HOME-PATH at "
          f"their lines (got {[ln for ln in out if ln.startswith(s3)]})")
    check(not any("binary content" in ln for ln in out),
          "UTF-16 text is never reported as binary content")
    check(not any(x in p.stdout + p.stderr for x in (EXP_ID, HOME, "someone", TR_S)),
          "no id, home path or letter is echoed")

    section("leak_check: a NUL in UTF-8 text that is not UTF-16 is still read at its line")
    nul = Repo(tmp / "leak-r5-nul")
    nul.commit("base", {"README.md": "Hello\n"})
    nul.git("branch", "pub")
    c = nul.commit("docs: nul", {"docs/research/m.txt":
                                 b"a\x00b\nBir " + WORD_TR.encode() + b"\nid "
                                 + EXP_ID.encode() + b"\n"})
    out = leak(nul, "pub..main", "--no-denylist").stdout.splitlines()
    check(has(out, f"{c[:10]}:docs/research/m.txt:2", "LANGUAGE")
          and has(out, f"{c[:10]}:docs/research/m.txt:3", "PRIVATE-ID"),
          f"the added lines are read as they are, every rule at its line (got {out})")
    doc = LK.__doc__ or ""
    check("or hold a NUL byte" in doc and "Known limit: BOM-less UTF-16" in doc,
          "the docstring says why a NUL sends a file to the blob, and states the limit")


def test_check_copy_round5(tmp: Path) -> None:
    section("check_copy: negation cues are matched literally, as C4 matches them")
    neg_lines = [
        "<p>We don’t stop here: " + RESEARCH_TERM + "</p>",       # 1 curly apostrophe
        "<p>Plain line.</p>",                                  # 2
        "<p>rather  than " + RESEARCH_TERM + "</p>",                  # 3 two spaces
        "<p>Plain line.</p>",                                  # 4
        "<p>instead of " + RESEARCH_TERM + "</p>",               # 5 a non-breaking space
        "<p>Plain line.</p>",                                  # 6
        "<p>instead&nbsp;of " + RESEARCH_TERM + "</p>",               # 7 the same, as an entity
        "<p>Plain line.</p>",                                  # 8
        "<p>none\tof " + RESEARCH_TERM + "</p>",                      # 9 a tab
        "<p>Plain line.</p>",                                  # 10
        "<p>There is no sense in which " + RESEARCH_TERM + "</p>",  # 11 'no' before NBSP
        "<p>Plain line.</p>",                                  # 12
        "<p>We don't stop here: " + RESEARCH_TERM + "</p>",           # 13 ASCII apostrophe
        "<p>Plain line.</p>",                                  # 14
        "<p>rather than " + RESEARCH_TERM + "</p>",                   # 15 one ASCII space
        "<p>Plain line.</p>",                                  # 16
        "<p>We would rather\nthan " + RESEARCH_TERM + "</p>",         # 17-18 wrapped cue
    ]
    text = "\n".join(neg_lines) + "\n"
    r = make_repo(tmp, files={"website/src/pages/neg5.astro": text})
    f = copy_findings(r)
    src = text.split("\n")
    for line, label in ((1, "a typographic don’t (U+2019)"),
                        (3, "'rather' and 'than' two spaces apart"),
                        (5, "'instead' and 'of' joined by U+00A0"),
                        (7, "'instead' and 'of' joined by &nbsp;"),
                        (9, "'none' and 'of' joined by a tab"),
                        (11, "'no' before U+00A0")):
        low = [src[line - 1].lower()]
        check(rules_at(f, "website/src/pages/neg5.astro", line) == ["RESEARCH"]
              and not CC.LC._is_negated(low, 0, low[0].index(RESEARCH_TERM)),
              f"{label} negates nothing, here as in C4 (line {line}; got "
              f"{rules_at(f, 'website/src/pages/neg5.astro', line)})")
    for line, label in ((13, "the ASCII don't"), (15, "'rather than' with one space")):
        low = [src[line - 1].lower()]
        check(rules_at(f, "website/src/pages/neg5.astro", line) == []
              and CC.LC._is_negated(low, 0, low[0].index(RESEARCH_TERM)),
              f"{label} still negates, here as in C4 (line {line})")
    low = [x.lower() for x in src[16:18]]
    check(rules_at(f, "website/src/pages/neg5.astro", 18) == []
          and CC.LC._is_negated(low, 1, low[1].index(RESEARCH_TERM)),
          "a cue wrapped across a line break still reads whole (both windows join the "
          "two lines with one space)")
    rx = CC._negation_re()
    check("\\u2019" not in rx.pattern and "’" not in rx.pattern
          and "\\s+" not in rx.pattern and "(?=\\s)" not in rx.pattern,
          "the cue pattern holds no typographic apostrophe and no whitespace class")
    doc = CC.__doc__ or ""
    check("never looser" in doc and "U+2019" in doc and "ASCII space" in doc,
          "the docstring states the literal matching it now does")

    section("check_copy: every page the manifest publishes is read at its source")
    pages_research = [manifest_page(src="docs/research/a.md", slug="research",
                                    wiki="Research-A"),
                      manifest_page(src="docs/other.md", slug="research/other", wiki="Other")]
    pages_substrate = [manifest_page(src="docs/psy.md", slug="substrate/overview", wiki="Psy"),
                       manifest_page(src="docs/research/b.md", slug="substrate/b",
                                     wiki="Psy-B"),
                       manifest_page(src="docs/missing.md", slug="substrate/gone",
                                     wiki="Gone")]
    manifest = manifest_text([{"title": "Cognitive maps (active)", "pages": pages_research},
                              {"title": "Substrate (foundation)", "pages": pages_substrate}])
    r = make_repo(tmp, files={
        "docs/publish.json": manifest,
        "docs/research/a.md": "A page.\n",
        "docs/other.md": "Intro.\nHere " + RESEARCH_TERM + ".\n",
        "docs/psy.md": "\n".join([
            "Intro.",                                          # 1
            "Here " + RESEARCH_TERM + ".",                            # 2 RESEARCH not applied
            "We ran 618",                                      # 3 COUNT wrapped
            "assertions here.",                                # 4
            "It costs 3 pJ.",                                  # 5 ENERGY
            "Ba" + TR_G + "lam.",                              # 6 LANGUAGE
            "The substrate " + CLAIM2 + ".",                   # 7 C4 reports it: dropped
            "We ran 618 assertions.",                          # 8 C2 reports it: dropped
            "The substrate " + CLAIM2 + " and " + CLAIM + ".",  # 9 C4 reports one
        ]) + "\n",
        "docs/research/b.md": "Here " + RESEARCH_TERM + ".\n",
    })
    check(CC.CORE.load_manifest(r)["sections"][1]["pages"][0]["src"] == "docs/psy.md",
          "fixture: core.load_manifest accepts the manifest")
    f = copy_findings(r)
    check(rules_at(f, "docs/other.md", 2) == ["RESEARCH"],
          "a page outside the hard-coded list, in the cognitive-map section, gets RESEARCH")
    got = sorted(set(rules_at(f, "docs/psy.md")))
    check(got == ["CLAIM", "COUNT", "ENERGY", "LANGUAGE"],
          f"a page in another section gets COUNT, CLAIM, ENERGY and LANGUAGE (got {got})")
    check(rules_at(f, "docs/psy.md", 2) == [],
          "and not RESEARCH: the research term list is about the cognitive-map line's "
          "claims, and the substrate's own pages are the substrate's record (asserted "
          "negative)")
    check(rules_at(f, "docs/psy.md", 3) == ["COUNT"] and rules_at(f, "docs/psy.md", 5)
          == ["ENERGY"] and rules_at(f, "docs/psy.md", 6) == ["LANGUAGE"],
          "a wrapped count, an energy figure and a Turkish letter, each at its line")
    check(rules_at(f, "docs/psy.md", 7) == [] and rules_at(f, "docs/psy.md", 8) == [],
          "a claim and a count C4 and C2 report themselves are not reported twice")
    check(rules_at(f, "docs/psy.md", 9) == ["CLAIM"],
          "a second claim on a line, which C4 does not report, is reported here")
    check(rules_at(f, "docs/research/b.md", 1) == ["RESEARCH"],
          "a docs/research page keeps RESEARCH in any section (the hard-coded list is the "
          "research term list's own scope)")
    check(not any(x.path == "docs/missing.md" for x in f),
          "a manifest source that does not exist is left out, not an error")
    p = run_py("check_copy.py", "--root", str(r), "--list")
    check(p.returncode == 1 and "scanned  docs/other.md" in p.stderr
          and "scanned  docs/psy.md" in p.stderr and "missing.md" not in p.stderr,
          f"the CLI lists the manifest pages as scanned (got {p.returncode})")
    os.symlink("nowhere.md", str(r / "docs" / "missing.md"))
    p = run_py("check_copy.py", "--root", str(r))
    check(p.returncode == 2 and "docs/missing.md" in p.stderr,
          f"a manifest source that is a dangling link is exit 2 (got {p.returncode})")

    section("check_copy: a manifest core refuses still has its pages read")
    outside = tmp / "outside-r5.md"
    outside.write_text("Ba" + TR_G + "lam.\n", encoding="utf-8")
    r = make_repo(tmp, files={
        "docs/publish.json": manifest_text([{"title": "Psyche", "pages": [
            manifest_page(src="docs/inv.md", slug="Bad_Slug", wiki="Inv"),
            manifest_page(src="../" + outside.name, slug="out", wiki="Out")]}]),
        "docs/inv.md": "Ba" + TR_G + "lam.\n",
    })
    refused = False
    try:
        CC.CORE.load_manifest(r)
    except CC.CORE.PublishError:
        refused = True
    check(refused, "fixture: core.load_manifest refuses this manifest")
    f = copy_findings(r)
    check(rules_at(f, "docs/inv.md", 1) == ["LANGUAGE"],
          "its page source is still read")
    check(not any("outside" in x.path for x in f),
          "a source that is not a canonical repository path is never read")
    doc = CC.__doc__ or ""
    check("every page src in docs/publish.json" in doc and 'begins "Cognitive map"' in doc,
          "the docstring lists the manifest pages and the RESEARCH scope")
    check(CC._research_section("Cognitive maps (active)")
          and CC._research_section("  cognitive MAPS (paused) ")
          and not CC._research_section("Substrate (foundation)")
          and not CC._research_section(None) and not CC._research_section("Maps"),
          "the cognitive-map section is found by its title's start, whatever state it names")


def test_check_copy_comment_pragma(tmp: Path) -> None:
    section("check_copy: a pragma in a comment that closes right before the figure")
    count = "ledger:allow-" + "count"
    claim = "ledger:allow-" + "claim"
    conscious = CLAIM[len("is "):]
    # the shape docs/METHODOLOGY.md uses: the comment opens mid-sentence, runs over several
    # lines, and closes immediately before a count that wraps onto the next line
    shaped = "\n".join([
        "The audit examined every assertion as it stood before the fix.",   # 1
        "It found that <!-- " + count,                                      # 2 opens
        'reason: "2 of 12" is an audit ratio for one brick, not a suite',   # 3
        "count, and must not be updated to the ledger total. -->**2 of 12",  # 4 closes
        "passed on both sides**. One of the two was dead.",                  # 5
    ]) + "\n"
    r = make_repo(tmp, files={
        "README.md": shaped,
        "MOC.md": shaped.replace(count, "a note"),                          # no pragma
        "docs/research/near.md": "\n".join([
            "Intro.",                                                       # 1
            "<!-- " + count,                                                # 2 opens
            "reason: a note. -->",                                          # 3 closes
            "Then **2 of 12",                                               # 4 line after
            "passed** here.",                                               # 5
        ]) + "\n",
        "docs/research/far.md": "\n".join([
            "Intro.",                                                       # 1
            "<!-- " + count,                                                # 2 opens
            "reason: a note. -->",                                          # 3 closes
            "A spacer line.",                                               # 4
            "Then **2 of 12",                                               # 5 two after
            "passed** here.",                                               # 6
        ]) + "\n",
        "docs/research/outside.md": "\n".join([
            count + " sits before a comment. <!-- a note",                  # 1 not inside
            "that runs on",                                                 # 2
            "-->**2 of 12",                                                 # 3 closes
            "passed** here.",                                               # 4
        ]) + "\n",
        "docs/research/claim.md": "\n".join([
            "Quoted from a critic, <!-- " + claim,                          # 1 opens
            "reason: a quotation, not a claim made here. -->",              # 2 closes
            "The substrate is <b>" + conscious + "</b>, they wrote.",       # 3 line after
            "<!-- " + claim,                                                # 4 opens
            "reason: a quotation. -->",                                     # 5 closes
            "A spacer line.",                                               # 6
            "The substrate is <b>" + conscious + "</b>, they wrote.",       # 7 two after
        ]) + "\n",
    })
    f = copy_findings(r)
    check(rules_at(f, "MOC.md", 4) == ["COUNT"],
          "fixture: the wrapped count is a finding without the pragma (C2 cannot see it)")
    check(rules_at(f, "README.md") == [],
          "a pragma in a comment that opens lines earlier and closes immediately before a "
          "count wrapped onto the next line permits it (the METHODOLOGY shape)")
    check(rules_at(f, "docs/research/near.md") == [],
          "a multi-line comment that closed on the line above still covers a figure")
    check(rules_at(f, "docs/research/far.md") == ["COUNT"]
          and rules_at(f, "docs/research/far.md", 5) == ["COUNT"],
          "the same count with the comment closed two lines earlier is reported")
    check(rules_at(f, "docs/research/outside.md", 3) == ["COUNT"],
          "the token must sit inside the comment that closes there")
    check(rules_at(f, "docs/research/claim.md", 3) == [],
          "ledger:allow-claim in a multi-line comment closing on the line above permits it")
    check(rules_at(f, "docs/research/claim.md", 7) == ["CLAIM"],
          "and a claim two lines after the comment closed is reported")

    section("check_copy: an SVG pragma in a multi-line XML comment")
    svg = "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg">',                    # 1
        "  <!-- " + count,                                               # 2 opens
        "       reason: a historical figure, labelled. -->",             # 3 closes
        "  <text>618 assertions</text>",                                 # 4 permitted
        "  <!-- " + count,                                               # 5 opens
        "       reason: a note. -->",                                    # 6 closes
        "  <text>spacer</text>",                                         # 7
        "  <text>618 suites</text>",                                     # 8 two after
        "</svg>",
    ]) + "\n"
    r = make_repo(tmp, files={"docs/assets/s.svg": svg})
    f = copy_findings(r)
    check(rules_at(f, "docs/assets/s.svg", 4) == [],
          "a multi-line XML comment closing on the line above a <text> node permits it")
    check(rules_at(f, "docs/assets/s.svg", 8) == ["COUNT"],
          "and a node two lines after the comment closed is reported")
    doc = CC.__doc__ or ""
    check("wherever the comment opens" in doc and "two or more lines earlier" in doc,
          "the docstring states the multi-line comment pragma and its limit")


DECODE_ENV = "DISCLOSURE_DENYLIST_B64"


def test_check_disclosure_round5(tmp: Path) -> None:
    section("check_disclosure: a walked binary file is matched by its path too")
    root = tmp / "disc-r5"
    term_a = "zeph" + "yr" + " " + "mo" + "ss"
    term_b = "gli" + "nt"
    deny_text = "# fixture\n" + term_a + "\n" + term_b + "\n"
    slug_a = term_a.replace(" ", "-")
    write_tree(root, {
        "bn/ok.md": "clean\n",
        "bn/" + slug_a + "/x.png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR\x00\x01",
        "bn/" + term_b + "-dir/a.woff2": b"wOF2\x00\x01\x00\x00"
                                         + zlib.compress(((term_b + " ") * 8).encode()),
        "bn/img/" + term_b + ".png": b"\x89PNG\r\n\x1a\n\x00\x00IDAT"
                                    + zlib.compress(((term_a + " ") * 8).encode()),
    })
    entries = CD.parse_denylist(deny_text)
    blobs = [q.read_bytes() for q in sorted((root / "bn").rglob("*")) if q.suffix in
             (".png", ".woff2")]
    check(len(blobs) == 3 and not any(CD.matching_indices(entries, run)
                                      for b in blobs for run in CD.binary_strings(b)),
          "fixture: no term is readable in any binary's content (two are compressed)")
    p = disclosure_lines(deny_text, tmp, Path("bn"), cwd=root)
    got = sorted(p.stdout.splitlines())
    want = sorted(["bn/[#1]/x.png:0: private term #1",
                   "bn/[#2]-dir/a.woff2:0: private term #2",
                   "bn/img/[#2].png:0: private term #2"])
    check(got == want, f"a binary under a directory whose name holds a term, and a binary "
                       f"whose own name holds one, are hits at line 0, masked (got {got})")
    check(p.returncode == 1, f"and exit 1 (got {p.returncode})")
    shown = (p.stdout + p.stderr).lower()
    check(not any(w in shown for w in ("zeph", "moss", term_b)),
          "no term is printed, in a path or anywhere else")
    check("3 binary file(s)" in p.stderr and "1 text file(s)" in p.stderr
          and "3 hit(s) in 3 file(s)" in p.stderr,
          f"the summary counts the binary files read (got {p.stderr.strip()})")


def test_decode_denylist(tmp: Path) -> None:
    import base64
    section("decode_denylist: the secret becomes a private file, or nothing")
    work = tmp / "decode-r5"
    work.mkdir()
    entry_a = "zeph" + "yr" + " " + "mo" + "ss"
    entry_b = "re:" + "qx-" + "\\d{3}"
    text = "# fixture\n" + entry_a + "\n\n" + entry_b + "\n"
    value = base64.b64encode(text.encode("utf-8")).decode("ascii")

    def run(env_value: Optional[str], out: Path, *args: str) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items() if k != DECODE_ENV}
        if env_value is not None:
            env[DECODE_ENV] = env_value
        argv = args if args else (str(out),)
        return run_py("decode_denylist.py", *argv, env=env, cwd=work)

    def quiet(p: subprocess.CompletedProcess, *secrets: str) -> bool:
        shown = (p.stdout + p.stderr).lower()
        return not any(s.lower() in shown for s in secrets if s)

    out = work / "list.txt"
    out.write_text("stale\n", encoding="utf-8")
    os.chmod(out, 0o644)
    p = run(value + "\n", out)
    mode = out.stat().st_mode & 0o777
    check(p.returncode == 0 and out.read_text(encoding="utf-8") == text,
          f"a valid value round-trips to the file, replacing what was there (got "
          f"{p.returncode})")
    check(mode == 0o600, f"the file is readable by its owner only (mode {oct(mode)})")
    check(quiet(p, value, entry_a, "qx-", text.strip()),
          "neither the value nor an entry is printed")
    check(CD.parse_denylist(out.read_text(encoding="utf-8"))[0].index == 1,
          "the file is a denylist check_disclosure reads")
    fresh = work / "fresh.txt"
    p = run(value, fresh)
    check(p.returncode == 0 and fresh.stat().st_mode & 0o777 == 0o600,
          "a new file is created 0600")

    for env_value, label in ((None, "an unset secret"), ("", "an empty secret"),
                             ("  \n", "a secret of whitespace only")):
        target = work / "absent.txt"
        p = run(env_value, target)
        check(p.returncode == 3 and not target.exists() and quiet(p, value),
              f"{label} exits 3 and writes nothing (got {p.returncode})")

    bad_cases = (
        (value[:8] + "\n" + value[8:], "a line break inside the value"),
        (value[:8] + " " + value[8:], "a space inside the value"),
        (value[:8] + "\t" + value[8:], "a tab inside the value"),
        ("not*base64!", "a value that is not base64"),
        (value[:-1], "base64 cut short (its length is not a multiple of four)"),
        (base64.b64encode(b"\xff\xfe" + entry_a.encode()).decode("ascii"),
         "base64 of bytes that are not UTF-8"),
        (base64.b64encode((entry_a + "\x01\n").encode()).decode("ascii"),
         "a control character in the list"),
        (base64.b64encode((entry_a + "\x7f\n").encode()).decode("ascii"),
         "a DEL character in the list"),
        (base64.b64encode(b"# only a comment\n\n   \n").decode("ascii"),
         "a list with no entries"),
    )
    for k, (bad, label) in enumerate(bad_cases):
        target = work / f"bad{k}.txt"
        p = run(bad, target)
        check(p.returncode == 1 and not target.exists(),
              f"{label} exits 1 and writes nothing (got {p.returncode})")
        check(quiet(p, bad.strip(), value, entry_a, "qx-") and DECODE_ENV in p.stderr,
              f"{label}: the message names the secret, never its value or an entry")
    p = run(value, work / "x.txt", "one", "two")
    check(p.returncode == 2 and not (work / "one").exists(),
          "a wrong number of arguments is exit 2, with nothing written")


def main() -> int:
    print("=" * 70)
    print("  PUBLISH CHECKS — TEST SUITE")
    print("=" * 70)
    tmp = Path(tempfile.mkdtemp(prefix="publish-checks-"))
    try:
        test_check_copy(tmp)
        test_check_disclosure(tmp)
        test_leak_check(tmp)
        test_check_copy_review(tmp)
        test_check_disclosure_review(tmp)
        test_leak_check_review(tmp)
        test_check_copy_round2(tmp)
        test_check_disclosure_round2(tmp)
        test_leak_check_round2(tmp)
        test_check_copy_round3(tmp)
        test_check_disclosure_round3(tmp)
        test_leak_check_round3(tmp)
        test_check_copy_round4(tmp)
        test_leak_check_round5(tmp)
        test_check_copy_round5(tmp)
        test_check_copy_comment_pragma(tmp)
        test_check_disclosure_round5(tmp)
        test_decode_denylist(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nRESULT: {PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
