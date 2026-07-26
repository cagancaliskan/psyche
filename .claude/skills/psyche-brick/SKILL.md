---
name: psyche-brick
description: Run a complete Psyche/Nous brick end to end — spec, build, adversarial verify, ledger update, commit. Use when starting or finishing a numbered step (0b2, 1c, 2a...). Orchestrates the four lanes in order with a hand-off between each, so no role certifies its own work.
argument-hint: "[brick-id] e.g. 0b2"
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, Agent
---

# Brick workflow — $ARGUMENTS

One brick proves itself before the next snaps on. This skill runs the four lanes in order
and enforces the hand-off between them. **Do not run two lanes in one pass.** The value of
the separation is that the role writing the mechanism is never the role certifying it;
collapsing that inside one context destroys the evidence even if the code is fine.

## Phase 0 — orient

Run `/psyche-orient`. Confirm from the live output that this brick's dependencies are
actually at the status you expect, and that the working tree is clean. If a dependency is
`DESIGNED` rather than built, stop: the foundation is not there.

Create the branch: `git checkout -b brick/$ARGUMENTS`

## Phase 1 — architect-pm: the spec

Delegate to the **architect-pm** agent. It writes `docs/specs/SPEC-<brick>-<name>.md`
containing:

- the problem, precisely stated
- 2–3 candidate approaches with honest tradeoffs, grounded in cited prior art
- a recommendation and why
- **the external, unfakeable done-means**
- the falsifier
- the invariants the tester will check, enumerated and labelled
- **the re-validation cost** — which already-verified bricks this change invalidates
- known limitations to ship as asserted-negatives

**Gate:** a spec with no falsifier, or no re-validation cost, is incomplete. Send it back.

**Overlay rule.** If the change alters existing behaviour, prefer shipping it as a
**default-off parameter whose neutral value is byte-identical** to current behaviour. This
is the established pattern here — `broadcast=False`, `body_sensor=None`,
`normalization_sigma=None` — and it is what lets a change land without re-validating
everything downstream. Flipping the default is then a separate brick with its own gate.

**Hand off.** Stop. Report the spec. Let Cagan approve any decision that shapes direction —
constants, defaults, anything with a re-validation cost.

## Phase 2 — builder: implement test-first

Delegate to the **builder** agent with the approved spec.

Test first, adversarial input and loop-closed input from the start, minimum implementation,
whole suite, then the six-bug self-audit. The determinism check runs across **every CPython
minor version on the machine**, not just one — see BUG-0b1.

```
for PY in python3.11 python3.12 python3.13; do
  command -v $PY >/dev/null && { echo "== $PY =="; $PY run_tests.py 2>&1 | tail -3; }
done
```

**Gate:** whole suite green on every available interpreter, six-bug checklist explicitly
clean, nothing overclaimed in code, comments, docstrings or the delivery report.

**Hand off.** Stop. The builder does not certify its own work.

## Phase 3 — tester: adversarial verification

Delegate to the **tester** agent. It writes `tests/test_tester_<brick>_adversarial.py` from
scratch — not adapted from the builder's tests — and it may not touch production code.

Every invariant the spec enumerated, plus: hostile topologies, cross-process determinism
across seeds *and* interpreters, purity by snapshot, integrity after randomized mutation
batteries, and loop-closure on input the previous stage actually produced.

If the change was an overlay, the tester's first job is **neutral byte-identity under
attack**: with the parameter at its neutral value, is the output bit-for-bit what it was
before? If not, the migration argument collapses and nothing else matters.

**Gate:** verdict PASS with every property holding. A FAIL goes back to the builder with the
exact failing input — the tester never fixes it.

## Phase 4 — validator: only if a meaning claim is in play

If — and only if — the brick asserts that something *means* something, delegate to the
**validator**. Run `/psyche-prereg` first; the pre-registration is committed before any
number exists.

Most bricks stop at phase 3 with **no cognitive claim**, and that is the normal, correct
outcome.

## Phase 5 — close out

0. **REGISTER any new suite in `run_tests.py` — before capturing, not after.** A suite that
   exists on disk but is not in `SUITES` is invisible to the canonical count, so the capture
   records a green run that omits it and the ledger then certifies an incomplete
   verification. This has happened: 0c's tester suite was written, passed in full, and sat
   outside the capture entirely.

   **This step is architect-pm's, not the tester's.** `run_tests.py` decides what the
   canonical count includes, which makes registration a fact-of-record change rather than a
   test change — and the lane hook blocks the tester from it, correctly. If a suite is
   deliberately excluded (data-dependent, parked, validator-run), it goes in
   `ledger.unregistered_suites` **with its reason**. `ledger_check` C5 enforces exactly this
   and will fail the build if a suite is neither registered nor excused.

1. Capture the run: `python3 run_tests.py > docs/TEST_OUTPUT.txt` (with the header block
   naming the interpreters swept and the seed set).
2. `python3 tools/ledger_sync.py` — and **never sync from a partial run.** If the capture
   omitted a suite, or the run was not green on every interpreter, the ledger must not record
   it: a ledger describing an incomplete capture is precisely the staleness the ledger exists
   to prevent. Fix the run, then sync.
3. Update the brick's status in `tools/ledger.json`, and append the decision to
   `DECISIONS.md` — date, what changed, evidence, who decided.
4. `python3 tools/ledger_check.py` — fix every document the change now contradicts.
5. Update `docs/nous_roadmap.md`: status, the "you are here" marker, the next action.
6. Run `/psyche-claim-check` on the delivery report and the commit message.
7. Commit in the repository's existing style:
   `feat(<brick>): <what>` · `fix(<brick>): <what>` · `test(<brick>): <what>` ·
   `docs(<area>): <what>` · `chore: <what>`

## The report

Close with: what changed · test totals **read from the runner, never estimated** · the
six-bug audit results · what is proven versus what is explicitly not claimed · known
limitations as asserted-negative tests · where this leaves the roadmap · the single next
action.
