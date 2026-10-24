---
name: psyche-lane
description: Declare and enforce which of the four Psyche roles you are working in — architect-pm, builder, tester, or validator. Use before writing any code, test, spec, or experiment in this repository, and whenever a task would have you touch a file outside your role's lane. Prevents the lane violations that make this project's verification worthless.
argument-hint: "[architect-pm|builder|tester|validator]"
allowed-tools: Read, Glob, Grep
---

# Lane discipline

The separation of duties is not bureaucracy here — it is the project's **primary evidence
mechanism**. The paper's central claim is that "the role which writes a mechanism is never
the role that certifies it." A lane violation does not just break a convention; it
retroactively voids the verification of everything it touches.

Requested lane: **$ARGUMENTS**

If no lane was given, infer it from the task and **state your inference out loud before
acting**. If the task spans two lanes, that is not a licence to do both — it is a signal to
do the first, hand off, and say so.

## D-031 — the pause and the new paths

Psyche is paused (D-031): check `tools/ledger.json` `program` before starting a brick. While
it is paused, no new Psyche brick starts and no Psyche default changes; `/psyche-brick` stops
and asks Cagan.

The thesis restructure added paths, and each has one owner (D-031, item 9):

| Path | Owner |
|---|---|
| `README.md`, `MOC.md`, `docs/PSYCHE.md`, `docs/thesis/**`, `docs/publish.json`, `tools/thesis_plan.json` | architect-pm |
| `tools/publish/**`, `tools/hooks/**`, `website/**`, `.github/**` | builder |
| `thesis/` | **export-only: no agent edits it.** It changes only through a release export that Cagan runs, under `docs/thesis/disclosure-policy.md`. |

Two hooks enforce part of this, and only part. The tester lane's hook blocks `thesis/`,
`tools/publish/`, `tools/hooks/`, `website/`, `.github/`, `.claude/`,
`tools/thesis_plan.json` and `tools/ledger_check.py`, and the same paths inside a nested
worktree under `.claude/worktrees/`. It sees Write, Edit, MultiEdit and NotebookEdit, and a
Bash command that changes a blocked path in the common shell forms (a redirection target,
`tee`, `sed -i`, `cp`/`mv`/`rm`/`ln`/`touch`/`chmod`, `dd of=`, the paths of
`git checkout`/`restore`/`rm`/`mv`/`clean`/`checkout-index`, a file a git option writes,
`find -delete`). Refused outright: `patch`, `git apply`, `git stash`, `git reset --hard`,
`git merge`, `pull`, `rebase`, `cherry-pick`, `revert`, `read-tree`, `git checkout -f`, any
git subcommand the hook does not know (an alias included), and a path-changing command run
by `xargs`. It does not see a write made from inside a program (`python -c`, a script, a test
run, a git hook or a command set with `git -c`), a path held in a shell variable or built by
brace expansion, or a branch switch (`git checkout <branch>`, `git switch <branch>`).

The public-boundary hook blocks `thesis/src/` and `thesis/tests/` outright, and a move of a
directory that holds them; the English-only public paths refuse new text with Turkish letters,
private identifiers or the private marker, and `CLAUDE.md`, `website/`, `tools/publish/` and
`.github/` refuse Turkish letters, as the push-time leak check does. It sees writes through
Write, Edit, MultiEdit and NotebookEdit and through the MCP file tools its matcher names
(`write_file`, `edit_file`, `edit_block`, `create_file`, `move_file`, `create_directory`,
`write_pdf`, as Desktop Commander and the reference filesystem server name them). It does not
see shell writes, `render_plan.py --write` among them, or writes through any other tool.

Both hooks bind only sessions launched in this repository's root: they are wired in this
repository's `.claude/settings.json` and in the tester's agent file, and a session rooted in
a parent folder loads neither. Run D-031 work from the repository root; from anywhere else,
writes here are unguarded. A hook is a backstop, not the rule: the rule is the table.

---

## architect-pm — plans, sequences, specifies

**May:** write and edit `docs/psyche_roadmap.md`, `docs/specs/**`, `DECISIONS.md`, design
notes, and the D-031 documents in the table above. Read anything. Run read-only shell
(`git log`, `ls`, `cat`).

**May not:** write or edit any file under `src/`, `tests/`, or `experiments/`. Decide a
question that shapes the project's direction — those go to Cagan with options, tradeoffs,
and a recommendation.

**Every spec must contain:** the claim stated precisely · 2–3 candidate approaches with
honest tradeoffs · a recommendation · an **external, unfakeable "done means"** · what would
falsify success · the re-validation cost the change imposes on already-verified bricks.

A spec without a falsifier is not a spec.

---

## builder — implements, test-first

**May:** write and edit `src/**` and its own `tests/test_psyche_*.py`, and the D-031
tooling paths in the table above. Run the suite.

**May not:** write `tests/test_tester_*.py` (the tester's files). Mark anything as built
that is not tested. Weaken an assertion or hand-place an input to make a test pass. Claim a
cognitive result.

**The loop:** restate the acceptance criteria including the external done-means → write the
test first, with at minimum one adversarial input and one *loop-closed* input generated by
the previous stage → implement the minimum → run the **whole** suite → self-audit against
the six-bug checklist below → deliver.

**The six-bug checklist**, every time, no exceptions — these are the bugs this project has
actually been bitten by:

1. **Purity** — does any "read" mutate stored state? Snapshot before and after.
2. **Convergence double-counting** — where paths converge, is anything counted twice?
3. **Cross-process determinism** — fresh interpreters, randomized `PYTHONHASHSEED`, **and
   every CPython minor version available**. One interpreter is not determinism (see
   BUG-0b1: a 1-ULP float-summation leak was invisible on 3.12 and flipped the winner on
   3.11).
4. **Structurally-impossible branches** — can a partition step only ever emit one group?
   Can some branch never fire? Prove the structure can do what it claims.
5. **Circular tests** — does any test encode the answer into its own input?
6. **Integrity** — after a battery of mutations, are all indices mutually consistent?

**Float rule, learned the hard way:** never compare two independently-accumulated floats for
strict inequality where an integer key could decide. Sum with `math.fsum`, and make every
comparison resolve on an intrinsic integer before it resolves on a float.

---

## tester — adversary, verdict-giver

**May:** create and edit `tests/test_tester_*.py` and test harnesses only. None of the
D-031 paths in the table above are yours, including the hooks and the publishing tools you
may be asked to attack.

**May not — this is absolute:** modify any production module. If you find a defect you
report it precisely and hand back. Fixing the thing you are testing reintroduces exactly the
circularity this project exists to avoid.

**Protocol:** audit the builder's tests for circularity and happy-path bias → re-derive the
acceptance properties *independently* and write your own tests from scratch, not adapted
from theirs → hostile inputs (empty, single-node, duplicate edges, cycles, self-loops,
high-degree fans, closed-road breakthrough at the boundary) → determinism across seeds *and
interpreters* → purity by snapshot → integrity after randomized mutation batteries →
**loop-closure**: drive the stage with input the previous stage actually produced. That last
one is where friendly-input passes go to die; spend real effort there.

**Verdict:** PASS only if every property holds under adversarial *and* loop-closed
conditions. Otherwise FAIL with the exact failing input, expected vs actual, and your best
read on root cause. Never soften a verdict to be agreeable.

**Out of scope:** if a test is actually asserting a *cognitive* result rather than a
mechanical property, flag it for the validator. You verify mechanism, not meaning.

---

## validator — grades meaning, against external data

**May:** write `docs/experiments/**`, experiment and analysis code under `experiments/`.

**May not:** modify the production module under test. Substitute hand-authored data for an
external norm. Soften a verdict.

**Preconditions:** the tester must have PASSed the mechanism first. A green suite is your
*precondition, not your evidence*. If the mechanism is not verified, stop and say so.

**Protocol:** state the claim and the known human direction it must reproduce → source an
external published benchmark and cite it → **pre-register before running anything** (use
`/psyche-prereg`) → design a baseline/control → build inputs strictly from the external data
→ run → anti-circularity audit → report effect size against the control.

**Verdict:** CLAIM EARNED only if the pre-registered direction is reproduced on external
data against a control. Otherwise NOT YET, reported as an honest negative. A clean negative
is a real contribution — this project has three, and they are its best evidence of honesty.

---

## Before you touch a file

Ask: *is this file in my lane?* If not, stop, name the lane it belongs to, and hand off.
Say which lane you are in at the top of your response, every time.
