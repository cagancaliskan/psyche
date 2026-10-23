<!-- ledger:ignore-file -->
# Install

Extract into the repository root (`~/Desktop/İşler/Psyche/PSYCHE/psyche`). Everything is additive
except `CLAUDE.md`, which is a rewrite — diff it before overwriting.

```
tar xzf psyche-toolkit.tar.gz -C /path/to/psyche
```

## What lands where

```
CLAUDE.md                              REPLACES the existing one (diff first)
DECISIONS.md                           new — append-only decision log
CLAUDE-CODE-PROMPTS.md                 new — the copy-paste prompts
MOC.md                                 new — Obsidian map of content (from obsidian/)

.claude/settings.json                  new — permissions + three hooks
.claude/skills/psyche-orient/          new — /psyche-orient
.claude/skills/psyche-lane/            new — /psyche-lane
.claude/skills/psyche-prereg/          new — /psyche-prereg
.claude/skills/psyche-claim-check/     new — /psyche-claim-check
.claude/skills/psyche-ledger/          new — /psyche-ledger
.claude/skills/psyche-brick/           new — /psyche-brick
.claude/agents/{architect-pm,builder,tester,validator}.md   REPLACES — upgraded

tools/ledger.json                      new — the fact ledger
tools/ledger_check.py                  new — the staleness linter
tools/ledger_sync.py                   new — regenerate counts from the capture
tools/capture_run.py                   new — multi-interpreter sweep + capture
tools/test_ledger.py                   new — 34 assertions for the tools
tools/hooks/*.py                       new — session-start, post-edit, lane guard

docs/BUG-0b1-*.md                      new — the bug report
docs/specs/SPEC-0b2-*.md               new — the conserved-activation spec
```

## Steps

```bash
cd ~/Desktop/İşler/Psyche/PSYCHE/psyche
git checkout -b toolkit/install

# 1. diff the constitution before replacing it
diff CLAUDE.md /path/to/kit/CLAUDE.md

# 2. extract
tar xzf psyche-toolkit.tar.gz -C .
mv obsidian/MOC.md . 2>/dev/null || true

# 3. make the hooks executable
chmod +x tools/hooks/*.py tools/*.py

# 4. verify the tools on every interpreter you have
for PY in python3.11 python3.12 python3.13; do
  command -v $PY >/dev/null && { echo "== $PY =="; $PY tools/test_ledger.py | tail -1; }
done
# expect: RESULT: 34 passed, 0 failed

# 5. see the state of the repository
python3 tools/ledger_check.py
# expect ~36 C2 findings on first run — those are real, and CC-2 fixes them

# 6. keep local settings out of git
grep -q 'settings.local.json' .gitignore || \
  echo '.claude/settings.local.json' >> .gitignore
grep -q '^\.obsidian' .gitignore || echo '.obsidian/' >> .gitignore

git add -A && git commit -m "chore: install the psyche toolkit — ledger, skills, agents, hooks"
```

## Verify it took

Start Claude Code in the repo. You should see the ledger block injected at session start —
the suite and assertion totals, the brick table, and the ledger_check status — all read from
`tools/ledger.json`, never typed here. Then:

```
/psyche-orient
```

If the slash commands do not appear, restart Claude Code once — creating an `agents/`
directory for the first time needs a restart, though skills hot-reload.

## The three hooks, and how to turn one off

| Hook | Fires | Does |
|---|---|---|
| `SessionStart` | every new session | injects the ledger's facts, so no session starts from a stale document |
| `PostToolUse` on `Write\|Edit` | after each edit to `.md`/`.py`/`.json` | if that file now disagrees with the ledger, says so immediately |
| `Stop` | end of each turn | one-line ledger status |

Plus a `PreToolUse` guard in the **tester** agent's frontmatter that blocks writes to `src/`,
`run_tests.py` and `CLAUDE.md`. That is the lane rule with teeth: the tester cannot patch the
code it is certifying, which is the single failure that would void the project's verification
without leaving a trace.

To disable any hook, delete its block from `.claude/settings.json`. To disable one just for
yourself, override in `.claude/settings.local.json` (gitignored).

## Optional: a git pre-commit hook

```bash
cat > .git/hooks/pre-commit <<'EOF'
#!/bin/sh
python3 tools/ledger_check.py --quiet || {
  echo
  echo "Commit blocked: the repository is inconsistent with tools/ledger.json."
  echo "Run: python3 tools/ledger_check.py"
  exit 1
}
EOF
chmod +x .git/hooks/pre-commit
```

Wait until CC-2 has cleared the existing 36 findings before enabling this, or every commit
will be blocked.

## Then

Open `CLAUDE-CODE-PROMPTS.md` and run **CC-1**.
