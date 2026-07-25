# Obsidian, and why the memory system is not a database

You asked whether to use Obsidian or build something more powerful. The honest answer is
that neither alone solves the problem this project actually has, and the right design is a
layer cake where each layer does what it is good at.

## What the memory problem here actually is

It is not "store notes." The repository already has ~100 documents and they are excellent.
The failure mode, observed and measured, is different:

- Five documents disagree about the assertion count (618, 130, 1372).
- `ARCHITECTURE.md` describes seven modules; there have been eight for a month.
- `REPORT.md` §9 and `SPEC-2c` §7 both describe futures that already happened.
- The roadmap's verification-tiers section says 1e has not been run. It was run and frozen.

Every one of those is the same bug: **a fact was copied into prose, the fact changed, and
the copy did not.** A database does not fix that — it just moves the copies. A note-taking
app does not fix it either.

## The design

```
  human layer      Obsidian  ──────────  reading, linking, graph view, mobile
                      │                   (points at the existing files; no migration)
                      ▼
  substrate        Markdown in git  ────  diffable, reviewable, native to Claude Code
                      │                   docs/, DECISIONS.md, specs, experiments
                      ▼
  fact layer       tools/ledger.json  ──  the ONE place a quotable number lives
                      │
                      ▼
  enforcement      tools/ledger_check.py  every fact in prose is checked against the
                                          ledger, in CI, on every edit, at session start
```

Markdown stays the substrate deliberately. Moving to a database would break git history,
break Claude Code's ability to read the corpus natively, and break every existing link — in
exchange for query features this project does not need. The structured part is small and
specific: **only the facts that get quoted**.

The enforcement layer is what makes this more powerful than either option you named. It is
the piece neither Obsidian nor a database gives you.

## Setting Obsidian up

Zero migration. Obsidian vaults are just folders of Markdown.

1. Obsidian → **Open folder as vault** → select the repo root
   (`~/Desktop/İşler/Nous/NOUS/nous`).
2. When prompted about `.obsidian/`, let it create the folder, then add it to `.gitignore` —
   your view settings should not be a repository artifact.
3. Settings → **Files & Links** → set *Excluded files* to `.git`, `__pycache__`,
   `.claude/worktrees`, `experiments/results`. Otherwise the graph view drowns in
   git objects.
4. Copy `MOC.md` to the repo root. It is the map of content — the entry point that makes the
   graph view meaningful instead of a hairball.
5. Optional: Settings → Appearance → enable **Show inline title**, and turn on
   **Strict line breaks** so the hard-wrapped docs render the way they read in an editor.

## Plugins worth having, and one to avoid

- **Dataview** — genuinely useful here. It can render live tables from the frontmatter of
  `docs/specs/` and `docs/experiments/`, so "which specs have no falsifier" becomes a query
  instead of a memory exercise.
- **Git** — commit from inside Obsidian. Convenient, but keep the real work in Claude Code
  where the hooks run.
- **Templater** — if you want the spec and pre-registration skeletons at hand outside a
  Claude Code session.
- **Avoid** any plugin that rewrites files on save (auto-formatters, link maintainers). They
  produce enormous diffs and will fight the ledger checks.

## What Obsidian must not become

It is a **reading and thinking surface**. It is not where facts live and it is not where
status changes happen. If a number needs changing, it changes in `tools/ledger.json` via a
`DECISIONS.md` entry, and the checker propagates the obligation to every document that
disagrees. If you edit a count in Obsidian, the next `ledger_check` run will tell you off —
which is the entire point.
