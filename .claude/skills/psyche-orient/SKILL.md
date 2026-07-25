---
name: psyche-orient
description: Orient at the start of any Psyche/Nous session. Loads the LIVE project state — git status, ledger facts, brick statuses, open decisions, and the current meaning-bar position — so you reason about what is true now rather than what a document remembers. Run this before planning, building, testing, or validating anything in this repository.
disable-model-invocation: false
allowed-tools: Read, Glob, Grep, Bash
---

# Orient — where this project actually is, right now

You are working on **Psyche** (paper name) / **Nous** (codebase). Before doing anything
else, absorb the live state below. It is generated at load time, so it cannot be stale the
way a document can.

## Live state

Git, last 8 commits and working tree:

```!
git -C "${CLAUDE_PROJECT_DIR}" log --date=short --pretty='%ad %h %s' -8 2>/dev/null || echo "(no git)"
echo "--- working tree ---"
git -C "${CLAUDE_PROJECT_DIR}" status --short 2>/dev/null | head -20 || true
echo "--- branch ---"
git -C "${CLAUDE_PROJECT_DIR}" branch --show-current 2>/dev/null || true
```

Ledger consistency (the four staleness checks):

```!
cd "${CLAUDE_PROJECT_DIR}" && python3 tools/ledger_check.py --quiet 2>&1 | head -12 || echo "(ledger_check not installed)"
```

Canonical facts, read from the ledger — **never estimate these, never recompute them**:

```!
cd "${CLAUDE_PROJECT_DIR}" && python3 - <<'PY' 2>/dev/null || echo "(no ledger)"
import json,pathlib
d=json.loads(pathlib.Path("tools/ledger.json").read_text())
t=d["tests"]
print(f"TESTS       {t['suites']} suites, {t['assertions']} assertions, {t['failures']} failures")
print(f"            captured {t['captured_at']} on Python {t['captured_python']}")
det=d["determinism"]
print(f"DETERMINISM hash seeds {det['hash_seeds']}")
print(f"            interpreters swept {det['interpreters_swept']} / required {det['interpreters_required']}")
mb=d["meaning_bar"]
print(f"MEANING BAR {mb['status']} — {len(mb['attempts'])} attempts: " +
      ", ".join(f"{a['id']}({a['wall']})" for a in mb["attempts"]))
print("BRICKS")
for k,v in d["bricks"].items():
    note = f"  [{v['note']}]" if v.get("note") else ""
    print(f"            {k:<10} {v['status']:<28} {v['name']}{note}")
PY
```

## The three things that govern everything you do here

1. **Mechanism ≠ meaning.** "The code is correct and deterministic" and "the code
   reproduces a cognitive effect" are separate claims with separate evidence bars. Never
   let one stand for the other.
2. **`PROVEN` and `DESIGNED` live in separate boxes.** `docs/design/` is a folder of
   *aspirational vision documents written before the code*. It describes intent. Nothing in
   it is built unless `tools/ledger.json` says so.
3. **External yardsticks, never self-authored inputs.** Any test that encodes its own
   answer is invalid. This project has three recorded NO-GOs precisely because that rule
   was enforced; they are the discipline working, not failures.

## What to read next, by task

| Task | Read |
|---|---|
| Planning / sequencing | `CLAUDE.md`, `docs/nous_roadmap.md`, `DECISIONS.md` |
| Writing code | `CLAUDE.md`, the relevant `docs/specs/SPEC-*.md`, the module and its suite |
| Testing | the module under test, the builder's suite, `docs/specs/SPEC-*.md` §invariants |
| An experiment / any cognitive claim | `docs/specs/PAPER_CLAIM_INVENTORY.md`, then `/psyche-prereg` |
| Anything touching a number | `tools/ledger.json` — and only that |

## Lanes

Four roles, and they do not cross: **architect-pm** plans and writes specs · **builder**
writes production code test-first · **tester** writes hostile tests and never touches
production code · **validator** grades meaning against external data and never patches the
module under test. Run `/psyche-lane` to confirm which one you are in before acting.

## Now say, in three lines

- Where the project is (brick, status, what is blocking).
- What the single next action is.
- Anything the live state above contradicts in what you were told or assumed.
