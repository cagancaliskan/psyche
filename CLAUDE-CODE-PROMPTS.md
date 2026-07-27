<!-- ledger:ignore-file -->
# Claude Code prompts — copy, paste, run

Each block below is a complete, self-contained prompt. Claude Code starts with no memory of
our conversation, so every prompt restates what it needs. Run them **in order**; each assumes
the previous one landed.

Before the first one, install the toolkit — see `INSTALL.md`. After that, every session
auto-loads the ledger at startup via the `SessionStart` hook, so you never have to paste
project state again.

**How to run:** open a terminal in the repo, type `claude`, paste the block, press enter.
Prompts marked ⏸ end with a hand-off — read the report and decide before continuing.

---

## CC-1 · Land the determinism fix and the interpreter sweep ⏸

> **Lane: builder, then tester.** Small, mechanical, and it must land before anything else
> because every later change alters the floats this bug lives in.

```
/psyche-orient

Then work in the builder lane on BUG-0b1, following /psyche-lane.

CONTEXT
A cross-process determinism failure was found in src/nous_coalitions.py and has already been
diagnosed and verified externally. Two sites, lines ~225 and ~308:

    strength = sum(members.values())

members is Dict[NodeID, float] keyed by uuid4. Float addition is not associative, so two
mathematically identical coalitions produce sums differing in the last ULP depending on
iteration order. That 1-ULP difference resolves the density comparison in
_competition_key BEFORE the `min creation_seq` tie-break can run, which makes the tie-break
unreachable in practice.

Evidence: on CPython 3.11, at a FIXED PYTHONHASHSEED=0, the T6b probe in
tests/test_tester_1d_i_adversarial.py returns two different winners across 30 runs (22 vs 8).
On 3.12 and 3.13 it is stable, which is why the suite has always been green — the captured
run was produced on 3.12.

TASK
1. Read docs/BUG-0b1-coalition-strength-determinism.md in full before touching anything.
2. Apply the fix: `import math` and `math.fsum(members.values())` at both sites. Do not
   change anything else in that file.
3. Verify, and show me the actual output:
   a. Run the T6b probe 40 times at a fixed PYTHONHASHSEED=0 under python3.11 — all 40 must
      be identical.
   b. Run the full suite under every python3.X on this machine. Each must report
      20 suites / 1372 assertions / 0 failures.
4. Install the sweep as the new capture path: verify tools/capture_run.py runs, sweeps every
   interpreter, refuses capture when they disagree, and writes docs/TEST_OUTPUT.txt with the
   provenance header naming the swept set and the hash seeds.
5. Run `python3 tools/capture_run.py`, then `python3 tools/ledger_check.py`.
6. Commit as TWO separate commits, in the repo's existing style:
     fix(0b1): sum coalition strength with math.fsum so the tie-break is reachable
     chore(tests): capture across every available CPython, not one
   Branch first: `git checkout -b brick/0b1-determinism`. Do NOT push.

CONSTRAINTS
- Do not weaken, delete or skip any assertion. The canonical count must stay 20 / 1372 / 0.
- Do not touch any file outside src/nous_coalitions.py, tools/, docs/TEST_OUTPUT.txt.
- Read every count from the runner output. Never estimate one.

REPORT
What changed; the 40-run and per-interpreter evidence verbatim; the six-bug self-audit
results; and one line on what this obliges the paper to say about determinism scope.
```

---

## CC-2 · Fix every stale fact in the repository ⏸

> **Lane: architect-pm.** 36 real inconsistencies, all found automatically. Purely
> documentation; no code moves.

```
/psyche-orient
/psyche-ledger check

Then work in the architect-pm lane, following /psyche-lane.

TASK
`python3 tools/ledger_check.py` currently reports ~36 findings. Fix every one. The ledger is
correct; the documents are stale. Work file by file, and after each file re-run the checker
so you can see the count fall.

The known classes, so you know what you are looking at:
- README.md says 12 suites / 618 assertions. The truth is in tools/ledger.json.
- docs/REPORT.md quotes 618 and describes a 7-module system. There are 8 —
  src/nous_bodysensor.py has existed since 2c and is missing from ARCHITECTURE.md,
  METHODOLOGY.md and REPORT.md entirely.
- docs/outreach/EMAILS.md and SUMMARY.md quote 130 assertions across 56 test functions.
  That is an order of magnitude stale and it is the text most likely to leave the building.
- docs/specs/PAPER_CLAIM_INVENTORY.md and SPEC-1e-priming.md quote superseded figures.

RULES
- Where a figure is genuinely historical — "the count at the time of 1c's verification was
  8 suites / 254" — keep it, label it as a snapshot, and add <!-- ledger:allow-count --> on
  the line above with a short reason. Do not use the pragma to silence a real staleness.
- docs/nous_roadmap.md narrates history and already marks superseded passages. Fix only
  figures presented as current.
- While you are in REPORT.md and the roadmap: §9 "Future work" still describes semantic
  priming as un-run. It was run and frozen NO-GO on 2026-06-21. The roadmap's
  "Verification tiers" section (dated 2026-06-20) says the same. Correct both, and mark them
  as superseded rather than deleting the history.
- Add nous_bodysensor to ARCHITECTURE.md with the same depth as its siblings: what it does,
  data structures, the friction formula, the two-mode replay/live design, and its
  default-off coupling to decay_per_hop. Read src/nous_bodysensor.py and
  docs/specs/SPEC-2c-interoception.md first.

FINISH
- `python3 tools/ledger_check.py` must exit 0.
- Run /psyche-claim-check on docs/outreach/EMAILS.md and SUMMARY.md specifically — those are
  outreach text and must clear the stricter bar.
- Commit: `docs: reconcile every quoted figure with the ledger; add bodysensor to the
  as-built docs`

REPORT
A table of file → findings fixed → anything you deliberately left with a pragma and why.
```

---

## CC-3 · Land SPEC-0b2 as a default-off overlay ⏸

> **Lane: architect-pm → builder.** Requires D-008 to be decided first — see CC-3a below.
> The overlay itself is already written and verified; this is about landing it properly.

```
/psyche-orient
/psyche-brick 0b2

Work the brick workflow for 0b2, conserved activation.

CONTEXT
docs/specs/SPEC-0b2-conserved-activation.md is written and its feasibility pre-check is
complete. The change is divisive normalization at the single transmission site in
src/nous_activation.py:

    competing = S_out - road.strength                 # S_out via math.fsum
    transmitted *= sigma / (sigma + competing)        # only when competing > 0

shipped as `normalization_sigma: Optional[float] = None`, byte-identical at neutral.

Already measured and reproducible:
- Fan sweep at sigma=1.0 fixed on principle: 0.2434 / 0.1771 / 0.1146 / 0.0672 / 0.0368
  across F in {1,2,4,8,16}. Strictly monotone, target spread 0.0, and F=1 is unchanged.
- With sigma=None the sweep reproduces the recorded flat 0.2433743975 to the last digit.
- Full suite unchanged at neutral: 20 suites / 1372 assertions / 0 failures.

PHASE 1 — architect-pm
Read SPEC-0b2 §5. The sigma/floor decision (DECISIONS.md D-008) must already be recorded. If
D-008 still says PENDING, STOP and tell me — do not pick a value yourself. That is the one
call that is mine.

PHASE 2 — builder
Apply the overlay (docs/02-spec0b2-normalization-overlay.patch has the exact diff). Then
write tests/test_nous_activation additions for the neutral case, and confirm the suite is
unchanged on every interpreter.

PHASE 3 — tester
Hand off. The tester writes tests/test_tester_0b2_adversarial.py from scratch, covering
N-1 through N-9 in SPEC-0b2 §6. Its FIRST job is to attack N-1: is the neutral value truly
byte-identical under adversarial graphs? If not, the migration argument collapses and
nothing else matters. Note the tester lane is hook-enforced — it cannot edit src/.

CONSTRAINTS
- The default stays None. Flipping it is a SEPARATE brick with its own gate.
- No cognitive claim. The fan sweep is a mechanism characterization on a synthetic star, not
  a graded behavioral result.
- Ship the §8 known limitations as asserted-negative tests, including the hyperbolic-vs-
  logarithmic falloff — the direction matches Anderson, the shape does not, and that must
  not be quietly claimed as an ACT-R replication.

FINISH
capture_run, ledger_sync, ledger_check, roadmap update, /psyche-claim-check, commit.
```

### CC-3a · The decision I need from you first

Not a Claude Code prompt — this is yours. `DECISIONS.md` D-008 is open:

**σ = 1.0 silences SWOW.** At ~114 mean out-degree per cue, every target falls below the
0.02 activation floor. Three options, measured:

| Option | Fan effect | SWOW-scale | Cost |
|---|---|---|---|
| **(1) σ fixed, revisit the floor** | strong, graded | works once the floor is relative | largest — the floor governs the spreading horizon that 1c and 1d were verified against |
| **(2) σ ∝ S_out** | weak; flat past out-degree 10 | works as-is | a graded fan run would likely fail on shape |
| **(3) σ ∝ S_out^β** | tunable | works | a new free parameter with no principled value — refuse |

My recommendation is (1), treating the floor as the second brick of 0b2. The principle has
to be recorded in D-008 **before** any downstream number is computed.

---

## CC-4 · Brick 2 — temporal credit assignment ⏸

> **Lane: architect-pm.** The largest hole in the design, and the mechanism is already in
> your own corpus.

```
/psyche-orient

Work in the architect-pm lane. Write the Layer 2 plan that was never written, and the spec
for temporal credit assignment.

THE HOLE
docs/design/nous_plan_layer0_topology.md states: "Temporal credit assignment has no owner
yet; it must not vanish." It was deferred to Layers 2 and 3. Neither was ever written —
teknik_planlar/layer03/ is an empty directory. Every motivation, self-model and regulation
mechanism in the vision corpus presupposes it.

THE MECHANISM IS ALREADY WRITTEN, AND WAS DROPPED
The corpus contains two incompatible plasticity models and never reconciled them:

  (a) docs/design/nous_substrate_biology.md — local tag  tau_ij <- min(1, tau_ij + eta*dA),
      background decay tau*e^(-lambda), global plasticity pool P_PRP = kappa*A*e^(-gamma*A),
      capture  omega_ij <- omega_ij + mu*(tau_ij * P_PRP).
  (b) Module 01 / src/nous_store.py — an integer traverse_count ladder (5 / 20 / 100).

(b) shipped. But the tag tau IS an eligibility trace and P_PRP IS a global capture signal;
together they are a three-factor learning rule. Synaptic Tagging and Capture — the theory
this project cites most — is precisely the answer to "how does an outcome at time t reinforce
a road traversed at t-k." It was cited as inspiration and never implemented.

TASK
1. Read nous_substrate_biology.md and nous_memory_hierarchy.md in full, plus
   src/nous_store.py, and write docs/specs/SPEC-2f-credit-assignment.md.
2. Resolve the two-model conflict explicitly. Is the integer ladder kept as a derived VIEW
   over a continuous omega, or removed? Argue it; do not assume.
3. Propose 2-3 designs with honest tradeoffs. At minimum: full tag/capture per
   substrate_biology, versus a minimal eligibility trace with no global pool. Say what each
   costs in re-validation of the store, which is Tier 1 PROVEN — this is the most expensive
   place in the codebase to change.
4. Decide where P_PRP lives. Layer 0 specifies a NEUROMODULATION publisher at tempo T2 with
   a pinned one-cycle lag ("actors read the budget published on the previous cycle"). That
   would give the system its first real job. Say whether that is right.
5. State the interaction with 2c: the interoception hook also modulates globally, on
   decay_per_hop. Two global modulators that have never met. Name the interaction and how it
   will be tested.
6. The done-means is a MECHANISM bar, not a cognitive one. My proposal, sharpen it: a road
   traversed at cycle t and followed by a designated outcome at t+k is reinforced more than a
   matched road traversed at t and not followed by that outcome, for k up to the tag
   lifetime, with the effect vanishing as k exceeds it — deterministic in replay, with a
   shuffled-outcome control.
7. Enumerate the invariants for the tester and the re-validation cost for the store.

CONSTRAINTS
- Documents only. No code, no tests.
- Dependency-free.
- Do not decide anything that shapes direction — options and a recommendation, and I decide.
- No cognitive claim. Credit assignment is a mechanism.

REPORT
The spec, plus one line on where this leaves the roadmap and what the single next action is.
```

---

## CC-5 · Brick 3 — the first non-circular meaning bar ⏸

> **Lane: architect-pm → validator.** Do not start until brick 2 exists. Writing the
> pre-registration early is fine and useful; running anything is not.

```
/psyche-orient
/psyche-prereg 3 learned-graph-vs-swow

Work in the architect-pm lane to design the experiment, then hand to the validator to
pre-register it. RUN NOTHING.

THE IDEA
Every meaning bar so far failed because SWOW was both the substrate and the ground truth.
Invert it:

    external corpus -> learned edges (via brick 2) -> grade the LEARNED association
    structure against SWOW as external ground truth

Now the norms are ground truth for something the system derived, rather than the thing it
was handed. This is the first non-circular cognitive claim available to this project, and it
is also Stage A of docs/design/nous_how_this_brain_comes_to_speak.md — the vision and the
experiment coincide.

THE GATE THAT DECIDES WHETHER THIS IS REAL
The anti-circularity control is a CO-OCCURRENCE BASELINE. If raw co-occurrence or PMI over
the same corpus predicts SWOW as well as the learned graph does, the architecture added
nothing and the result is a null. That is the honest hard bar and it must be pre-registered
with a margin fixed in advance.

Before designing, run the three-wall gate from /psyche-prereg against this design and write
the answers down:
- CIRCULAR? The corpus must not be SWOW-derived. Say how you guarantee that.
- MECHANISM ABSENT? Name the line of code that produces learning. If brick 2 is not built,
  this is a design on paper and must say so.
- SIGNAL FLAT? What is the expected range of the correlation, and would a null be
  interpretable — could it distinguish "the architecture adds nothing" from "the corpus was
  too small to learn from"?

DESIGN QUESTIONS TO ANSWER
- Which corpus? It must be public, citable, not SWOW-derived, and small enough to run on a
  laptop. Search for candidates and cite them.
- What exactly is graded — edge rank correlation against SWOW strength on held-out cues?
  Recall of SWOW's top-k responses? Say why, and name the metric's failure mode.
- Held-out design: which cues are never seen during learning?
- What effect size, at what N, decides EARNED vs NOT YET? Fix it now.
- What makes the run VOID rather than NOT YET?

CONSTRAINTS
- Write the pre-registration to docs/experiments/EXP-3-learned-graph.md and mark it clearly
  as DESIGN-STAGE, pending brick 2.
- Compute NO numbers. Do not download the corpus. Do not run the engine.
- If the gate fires, say NO-GO and explain why. That is a first-class result here.

REPORT
The pre-registration, the gate answers, and an honest read on whether this is the right bar
or whether something better exists.
```

---

## CC-6 · Ship the paper ⏸

> **Lane: architect-pm.** Independent of the bricks; run it whenever.

```
/psyche-orient
/psyche-claim-check docs/paper/paper.tex

Work in the architect-pm lane.

TASK
The paper "Mechanism Is Not Meaning: A Verification Methodology for Cognitive-Architecture
Prototypes" is written and there is an IEEE 6-page version for IDAP/UBMK. Get it shippable.

1. Verify every number in paper.tex against tools/ledger.json. The claim inventory says the
   canonical count is 20 suites / 1372 assertions; confirm the paper's Appendix A table sums
   to exactly that, and that no superseded figure survives.
2. Add the BUG-0b1 finding to the methodology section. This STRENGTHENS the paper. The
   argument: practice 3 (adversarial and property-based testing) worked — the test written to
   catch this class was correct and fired the moment it met an interpreter that exposes the
   leak. What failed was coverage: an invariant is only verified over the axes you sweep, and
   interpreter container layout is a second axis PYTHONHASHSEED cannot reach. Propose the
   refinement as one paragraph plus one sentence in the limitations section, and scope the
   determinism claim to the swept interpreter set.
   Read docs/BUG-0b1-coalition-strength-determinism.md §6 — the framing is there.
3. Check both versions compile: paper.tex and docs/paper/ieee/paper_ieee.tex. Report any
   missing figure or bib entry.
4. Check the claim inventory's constraints still hold: system is "Psyche" in the paper and
   "Nous" in the code; zero source references, no commit hashes, no file paths, no URL; no
   em-dashes.
5. Tell me what is still missing before submission — venue formatting, page limit, anonymity
   requirements, anything.

CONSTRAINTS
- Do not add a claim the evidence does not support. Run /psyche-claim-check on any paragraph
  you write.
- Do not remove a limitation to make the paper stronger.

REPORT
A submission checklist: done / not done / blocked-on-me.
```

---

## CC-7 · Verify the detector — brick 0d ✔ RUN (verdict: FAIL on F-6)

Brick 0d is **built, clean, uncommitted, and unverified**. `C6` in `tools/ledger_check.py`
enumerates 14 float accumulations in `src/` — 8 `fsum`, 6 registered with a reason and a
falsifier — and `tools/test_ledger.py` is 139/139 green. Nobody independent has looked at it.
Run part A. Only run part B if A returns PASS.

### CC-7a · The tester

```
/psyche-orient

Work in the TESTER lane. Brick 0d — the float-accumulation detector (C6 in
tools/ledger_check.py) — is built, clean, and uncommitted. It has never been independently
verified. Verify it adversarially, then hand back.

WHY THIS TARGET IS UNLIKE EVERY PREVIOUS ONE
Every previous target was a mechanism that produces a value. This one is a GATE: its only
product is a refusal. A gate that never refuses looks exactly like a gate that works, and
every test the builder could write for it is a test the builder also designed it to pass.
The ordinary protocol is not sufficient. Your single most important job is:

  PROVE THE GATE WOULD HAVE CAUGHT THE THREE BUGS IT WAS BUILT FOR — from real git history,
  not from a fixture you authored.

RETRO-CATCH (first; if this fails nothing else matters)
Reconstruct each pre-fix file from git and run C6 against it in a temporary tree. Never write
to src/ — ledger_check.py takes --root PATH, use it.

  1. BUG-0b1, src/nous_coalitions.py. The fix is d9ab474. Extract its parent:
       git show d9ab474^:src/nous_coalitions.py
     C6 must report that site as an UNREGISTERED naive accumulation. If it reports fsum, or
     reports nothing, the detector is decorative and 0d has not been built.
  2. src/nous_workspace.py — the naive sum found in SPEC-0c §2.5. Locate the converting
     revision yourself rather than trusting a SHA from me:
       git log -S 'sum(pruned_members.values())' -- src/nous_workspace.py
     Extract that commit's parent and repeat.
  3. src/nous_field.py:131 — never converted, deliberately registered. Extract the ORIGINAL
     from 5d29071 and confirm C6 finds it there too — i.e. that detection does not depend on
     anything the 0c work happened to add to that file later.

For all three, also run with the registry EMPTIED. A detection that only works because the
site is already named in ledger.json is not a detection.

THE FALSE-NEGATIVE SURFACE
C6's own header names four blind spots: multiplicative chains, two-hop temporaries,
sumprod/Counter-style reductions, and non-src/ directories. It claims each is asserted as a
negative in tools/test_ledger.py. Verify that claim by reading those assertions, and for each
answer one question: does it assert the DOCUMENTED LIMIT, or merely that some input produces
no finding? Only the first is honest. Add what is missing, in your own file —
tests/test_tester_0d_*.py.

Then attack from the other side. Each of these must FAIL, with a message naming which:
- Plant a naive accumulation in a fixture tree. Then plant one whose variable name and shape
  mimic an already-registered site — registration must key on LOCATION, not resemblance.
- Delete a reason. Shorten a reason below the floor. Flip a verdict to "fsum" while the code
  stays naive.
- Register a site that does not exist. Rename a function so a registered key goes stale. A
  registry entry with no matching site must not pass silently; a stale registry is how a
  detector rots into decoration.
- Put a file with a syntax error in the fixture src/. C6 must exit 2 (the tool could not
  run), never exit 0 (clean). A parser that reads unparseable as clean is worse than none.
- Add a BRAND-NEW file to the fixture src/ with an unregistered naive accumulation, and
  confirm C6 finds it with no registry edit. This is the loop-closed case, and the only
  scenario this gate exists for: 2f will add new files.

THE SIX REGISTERED REASONS
Read all six. You are NOT adjudicating whether the reasoning is right — that is the
architect's call. Check one mechanical thing: every reason names a FALSIFIER, and that
falsifier is something a person could actually run. Flag any reason that asserts safety
without naming what would disprove it.

RUN
tools/test_ledger.py on every interpreter available, plus the full run_tests.py suite.
Confirm totals against tools/ledger.json. Report the interpreters swept — never estimate.

EXPECT
tools/ledger_check.py currently exits 1 with exactly 16 [C2] findings, all under docs/paper/.
That is correct, deliberately held signal. A 17th finding, or any finding outside docs/paper/,
is a real regression. Do not "fix" the 16.

VERDICT
PASS only if the retro-catch succeeds on all three AND every negative above actually fails.
Otherwise FAIL, with reproductions, and hand back to the builder. Fix nothing yourself. Do
not touch src/, run_tests.py, tools/ledger.json or docs/TEST_OUTPUT.txt.

Open your report with the plain-language summary for Cagan. That block in your agent
definition is not optional.
```

### CC-7b · Fold it in — only after a PASS

```
/psyche-orient

Work in the ARCHITECT-PM lane. The tester has returned a verdict on brick 0d, the
float-accumulation detector. Fold it in.


IF PASS
- tools/ledger.json: 0d moves off DESIGNED. Choose between BUILT-UNVALIDATED and PROVEN and
  JUSTIFY the choice in a paragraph. 0d is a TOOL, not a substrate brick — state explicitly
  what PROVEN would even mean for a gate, and whether the evidence reaches it. If the two
  axes do not fit a tool cleanly, say so rather than forcing it.
- DECISIONS.md: what 0d does; what it deliberately does NOT do (it fixes nothing —
  nous_field:131 stays order-dependent on purpose, and the empty backlog must never be read
  as the deliverable); and its four named blind spots.
- docs/nous_roadmap.md: move the "you are here" marker. State in one line that the foundation
  arc is CLOSED and that 2f is next.
- python3 tools/ledger_check.py — expect exit 1 with exactly the 16 held [C2] paper findings
  and nothing else.
- Commit: feat(0d): float-accumulation census — the gate that ends the manual hunts
  Include the four .claude/agents/*.md changes in the same commit. They are Cagan's reporting
  requirement, not code.

IF FAIL
Change no status. Commit nothing. Tell me in plain language what the builder must fix.

THEN STOP. Do not begin 0c-ii. Do not begin 2f. The foundation arc ends here by decision, and
starting the next brick in the same session is exactly how an arc fails to end.
```

---

## CC-8 · Close 0d — the bounded remediation cycle ✔ DONE (PASS, closed at e64e9e6)

Tester verdict on 0d: **FAIL on F-6.** F-1 (retro-catch) succeeded on all three historical bugs
from real git history, F-3 and F-4 clean. The failure is that two registry reasons were **false**,
and C6 structurally cannot detect a false reason — it verifies a reason *exists* and that the
verdict matches the AST. The architect corrected both in place and cannot certify its own
correction.

**This is the last cycle on the foundation.** Its boundary is stated in CC-8a and is binding:
anything discovered from here becomes a written limitation with a falsifier, **not** a fix —
unless it makes the detector fail to catch one of the three historical bugs. That single clause
is the only thing permitted to reopen scope.

**Ratified, and my instruction was wrong:** CC-7b said "on FAIL, commit nothing." The
architect committed the evidence — the detector, the tester's 1,335-line adversarial suite, the
corrected spec and DECISIONS — while leaving 0d at `DESIGNED`. That was the better call and it
stands. The rule is now: **on FAIL, commit the evidence and the corrections; never the status.**

### CC-8a · The builder

```
/psyche-orient

Work in the BUILDER lane. Brick 0d (C6 in tools/ledger_check.py) came back FAIL on F-6. The
detector itself is sound — the retro-catch proved it would have caught all three historical bugs
on the day each was written. What failed is the REGISTRY: two reasons were false. Four defects
were routed to you. Fix exactly those four and the one addition below. Nothing else.

THE BOUNDARY, AND IT IS BINDING
This is the last remediation cycle on the foundation. If you find something new: register it as
a LIMITATION with a falsifier, do NOT fix it. The single exception — the only thing permitted to
reopen scope — is a finding that makes C6 fail to catch one of the three historical bugs. If you
hit that, stop and hand back. Do not widen the brick to be thorough; a gate that never ships
because it is still being perfected is a gate that never guarded anything.

FIX 1 — the `-=` gap is a DEFECT, not a limitation
C6's header says "ADDITIVE reduction only." Subtraction IS additive — `x -= v` is `x += (-v)` and
is exactly as order-sensitive. The comment therefore claims coverage the scanner does not have.
That is the same defect class that just failed this brick: a true-looking sentence a later reader
relies on. Detect ast.Sub alongside ast.Add in AugAssign and in the self-referential BinOp form.
Every newly-surfaced site gets adjudicated, not silently absorbed.

FIX 2 — the match-statement traversal gap
Statements inside a `match` case are never walked, so an accumulation there is invisible. src/
has no `match` today; 2f is written next and may introduce one. A traversal that silently skips a
syntax construct is the same failure as a parser that reads unparseable source as clean, wearing
different clothes — and that one is already an explicit contract in this tool. Walk match cases.
While you are there, audit the traversal for any OTHER statement-bearing construct it misses
(with, try/except/else/finally, async variants, nested function and class bodies) and either walk
it or add it to the limitations list. State which you did for each.

FIX 3 — the two exit-code contract breaks on malformed source
Named in the tester's report. The contract is absolute: unparseable or malformed source exits 2,
"the tool could not run." It must never exit 0. Exit 0 on source C6 could not read is the single
worst outcome this tool has, because it is indistinguishable from clean.

FIX 4 — the eight remaining undetected shapes get LIMITATION ENTRIES, not fixes
Eight shapes remain after `-=` and `match` are handled. Do NOT implement them. Write each into
the limitations list with a falsifier, and assert each as a negative in tools/test_ledger.py the
way the existing four are — so "the detector is clean" can never quietly mean "the detector did
not look." If any of the eight is a one-line detection you are tempted to just add: resist it and
say so in your report. Whether it is worth adding is not your call in this cycle.

ADDITION — make the two absence-bounds machine-verified
This is a scope addition and I am naming it as one rather than smuggling it in. Both corrected
reasons now rest on an ABSENCE: `ActivationField.flow` has no reader in src/, and `advance()` has
no caller in src/. Those are the strongest available arguments and they are honest. They are also
the most fragile kind of claim a registry can hold, because nothing enforces them — and 2f is the
very next brick and the most likely thing to fire both falsifiers. A false registry reason is
precisely what failed this brick; leaving two of six resting on an unenforced absence would be
losing the same way twice, with the trigger date already on the calendar.

The fix is NOT a new check and NOT a hand audit — the lesson of this FAIL is that reproduction
cannot be the gate, only enumeration can. Add a machine-checkable field to the registry entry and
let the AST walk C6 already performs verify it:

    "bound_on_absence": [
      {"kind": "attribute_read", "symbol": "ActivationField.flow"},
      {"kind": "call",           "symbol": "form_coalitions"}
    ]

C6 fails if any named symbol turns up in src/, with a message that says: this entry rests on the
absence of Y, Y now exists at <file>:<line>, the reason is now FALSE, re-adjudicate it. Populate
it for the two corrected entries and for any other reason whose argument rests on absence — read
all six and say which qualify.

BIAS IT TOWARD OVER-REPORTING, and put that in its docstring. An attribute read cannot be
resolved to a type without inference, so flag any `.flow` read in src/ and let a human dismiss
it. A false positive costs one sentence; a false negative is a silently false claim in the
registry, which is the failure this whole brick exists to prevent. Choosing the other bias is
choosing the way we just lost.

RUN
The full suite on every interpreter available, plus tools/test_ledger.py. Read totals from the
runner output; never estimate. Report the interpreters swept. tools/ledger_check.py exits 1 with
exactly 16 [C2] findings, all under docs/paper/ — that is correct held signal. Any 17th finding,
or any finding outside docs/paper/, is a regression you caused.

SELF-AUDIT
All seven items, including the seventh added by D-020: does a builder-side assertion exist for
the arithmetic you just wrote, or does all evidence for it live in tester files?

Open your report with the plain-language summary for Cagan. That block in your agent definition
is not optional.
```

### CC-8b · The tester — F-6 re-verification

```
/psyche-orient

Work in the TESTER lane. You returned FAIL on brick 0d at F-6: two registry reasons were false.
The architect corrected both and cannot certify its own correction. The builder has since fixed
four routed defects and added one machine-checked field. Re-verify.

F-6 IS THE WHOLE JOB, AND IT IS THE ONE C6 CANNOT DO FOR YOU
C6 verifies a reason EXISTS and that the verdict matches the AST. It can never verify a reason is
TRUE. That gap is what failed this brick, and it does not close — a registry's reasons need a
human adversary every time, not once. So: take each of the six reasons and try to make it false.

For every reason:
- RUN ITS OWN FALSIFIER. That is how you caught 0d-1 — the entry named what would disprove it and
  nobody had run it. Run all six. A falsifier that has never been executed is decoration.
- ATTACK THE PROBE, NOT JUST THE CLAIM. 0d-1's root cause was a probe STRUCTURALLY INCAPABLE of
  exhibiting the symptom it was run to find — four sources converging on one node, where every
  value at hop 1 is single-term by construction. For each reason that rests on a measurement, ask
  the question that would have caught it: could this probe have produced the symptom AT ALL? If
  the answer is no, the reason is unsupported regardless of what the measurement showed.
- SEPARATE THE HALVES. Clock.advance._t failed because a reason had a true clause and a false one,
  and the false one was the half a reader relies on. Split every reason into its claims and test
  each independently. A reason is only as strong as its weakest load-bearing clause.

THE NINE FLIPPED NEGATIVES — READ THIS BEFORE YOU TOUCH YOUR OWN FILE
Nine asserted-negatives in your 0d file now FAIL, by design: subtraction is detected, match is
walked, the scope comment is corrected, and three registry claims were corrected. Those
assertions were documenting limits that no longer exist, so failing is the correct behaviour and
there is no regression.

The danger is the obvious repair. The cheapest way to turn nine failing assertions green is to
delete them, and that is the one move this project forbids — making a failing test pass by
weakening it. For EACH of the nine, do this instead and show your work:
- State what the assertion previously documented, and what the builder now claims changed.
- Verify the capability INDEPENDENTLY — not by re-running the builder's test. Construct your own
  input that the old scanner provably could not see and the new one must.
- Only then convert the assertion: from "the scanner cannot see X" to "the scanner sees X", with
  the positive case asserted. A deleted negative leaves no trace that the limit ever existed; a
  converted one is a record of a capability gained.
If any of the nine cannot be converted because the capability is NOT actually there, that is a
FAIL and it outranks everything else in this pass.

THE TWO ABSENCE-BOUNDS ARE THE SHARPEST TARGET
Both corrected reasons now rest on something NOT existing in src/. Verify independently that each
absence actually holds — do not inherit the architect's search. Then verify the new
bound_on_absence field does what it claims: add a reader of ActivationField.flow to a fixture
tree and confirm C6 FAILS naming that entry; add a caller of advance() and confirm the same.
Then check its bias: confirm it OVER-reports rather than under-reports, because the docstring
now promises that, and a gate that promises over-reporting and under-reports is worse than one
that promises nothing.

THE FOUR BUILDER FIXES
- `-=` now detected: confirm newly-surfaced sites are adjudicated, not silently absorbed. Confirm
  the header no longer claims coverage the scanner lacks.
- match traversal: plant an accumulation inside a match case and confirm detection. Then check
  every other statement-bearing construct the builder claims to walk, and confirm each claim.
- exit codes: malformed source exits 2, never 0. Re-run the malformed-source battery in full.

THE EIGHT LIMITATION ENTRIES — one is load-bearing for the next brick
For each of the eight, the usual question: does it assert the DOCUMENTED LIMIT, or merely that
some input produces no finding? Only the first is honest.

Then single out L3, tuple-target accumulation (`a, b = a + x, b + y`). That shape is a plausible
thing for 2f to write — updating a trace and a counter together is idiomatic — and the gate
cannot see it. It stays a limitation this cycle by decision, NOT because it is safe. Confirm its
asserted-negative is precise enough that a reader of 2f's spec could act on it, because that is
where the burden has been placed.

Note for the record: the builder was tempted by L6 (`reduce(operator.__add__)`), judged it a
scoping call rather than a builder call, and left it. That was correct. Do not add it either.

REGRESSION
Re-run F-1 (the retro-catch) in full. The builder touched the traversal, and F-1 is the only
evidence the detector works at all. If the retro-catch no longer catches all three historical
bugs, that is the one finding permitted to reopen this brick's scope — say so loudly.

VERDICT
PASS only if every reason survives its own falsifier, the absence-bounds are independently
confirmed and mechanically enforced, and the retro-catch still succeeds on all three. Fix
nothing. Do not touch src/, run_tests.py, tools/ledger.json or docs/TEST_OUTPUT.txt.

Open your report with the plain-language summary for Cagan.
```

### CC-8c · Fold it in and close the arc — only after a PASS

```
/psyche-orient

Work in the ARCHITECT-PM lane. The tester has re-verified brick 0d at F-6. Fold it in and close
the foundation arc.

DECISION FROM CAGAN — the tools/test_ledger.py question, settled
Option B, with one addition that is the part that matters. Extend C5 to scan tools/ so the gate's
own suite can no longer sit unregistered, and register it in a SEPARATE bucket from the substrate
and cognitive-layer suites. Do NOT fold its assertions into the headline total.

The addition: RENAME the headline figure so it says what it counts. Once C5 sees tools/, the repo
contains more assertions than the ledger's headline number reports, and an unlabelled "1,973
assertions" then becomes a false claim in a paper that cites it — the exact failure C2 exists to
prevent, arriving through a field name instead of through prose. Carry two named figures, and
make the paper cite the substrate one BY NAME. Closing a silence must not open a claim.

FOUR THINGS FROM THE TESTER'S PASS, EACH WITH ITS DISPOSITION DECIDED

1. FINDING 0d-5 — narrow the WORDING, never widen the machinery. The docstring promises
   over-reporting; it under-reports on getattr(x,'flow'), x.__dict__['flow'], aliasing, and
   getattr(c,'advance')(). Route the wording fix to the builder as a one-line docstring change.
   It must not merely delete the over-reporting claim — it must state ACTIONABLY what IS covered:
   direct attribute access and direct calls; dynamic access is not seen, here is the exit
   instruction. A promise wider than its machinery is the same "true-looking sentence" that has
   now bitten this brick three times, and the third occurrence of a pattern is where it stops
   being bad luck.

2. field.total names NO falsifier where the other five do. The tester asserted the asymmetry
   rather than leaving it, which was right — five-of-six is a convention a reader generalises.
   Give it one, or state in the entry itself why the site admits none. "This entry has no
   falsifier, and here is why" is an acceptable answer; silence is not.

3. L3 IS NOT 0d's LAST TASK — IT IS 2f's FIRST. This is the sharpest finding of the pass and I am
   deliberately NOT reopening 0d for it. The tester showed that the idiomatic line 2f will write —
       trace[rid], counts[rid] = trace[rid] + e, counts[rid] + 1
   produces ZERO findings: the float site is lost to L3, the int counter was never in scope. So
   the gate built to catch 2f's accumulations misses the one accumulation 2f adds.

   A passive sentence in a spec is not enough — I rejected exactly that pattern for the absence
   bounds this cycle, and accepting it here would be incoherent. So write it into SPEC-2f as
   STEP ZERO, mandatory, before any credit-assignment code is written: **teach the gate to see
   tuple-target accumulation, then build the thing that would have hidden in it.** Ownership sits
   with the brick that needs the coverage, the foundation arc still ends here, and 2f's first act
   becomes a demonstration that extending the gate is a normal cost of building — which is the
   only way this gate survives contact with future work.

   Leave L7 out. An integer counter is not a float accumulation; that is out of scope, not a hole.

4. ABORT-HIDES-TESTS, second occurrence — register it as its own brick and SCHEDULE IT BEFORE THE
   PAPER CAPTURE. A test that aborts does not appear in the failure list, so "0 failures" can be
   true of the report and false of the repository. Both times it was caught by someone running the
   thing directly; twice is a pattern, and the project's headline claim rides on that number. It
   is NOT 0d's problem — it affects every brick — so give it an ID, a one-line statement of the
   defect, and a slot before the capture that the paper cites. Do not fix it in this commit.

IF PASS
- tools/ledger.json: 0d moves off DESIGNED. Choose between BUILT-UNVALIDATED and PROVEN and
  justify it in a paragraph. 0d is a TOOL, not a substrate brick — state what PROVEN would even
  mean for a gate whose only product is a refusal, and whether the evidence reaches it. If the
  two axes do not fit a tool cleanly, say so rather than forcing the fit.
- DECISIONS.md: record the third aphorism, and state it as the generalisation of 0d-1 —
  **"A site can have the shape, have the symptom, and still clear a probe a competent person
  designed to find it."** Therefore reproduction cannot be the gate; only enumeration can. It
  belongs beside the other two, and it was bought at the highest price of the three: the
  impossible-branch defect occurred INSIDE the brick built to stop that class, and was written
  into that brick's spec as its headline argument. Add it to docs/METHODOLOGY.md and mark it for
  the paper.
- DECISIONS.md: record the standing rule this cycle established — **on a FAIL, commit the
  evidence and the corrections; never the status.** My original instruction said commit nothing
  and was wrong; you were right to commit the tester's suite rather than leave 1,335 lines of
  adversarial tests in an uncommitted working tree.
- DECISIONS.md: record that C6 verifies a reason EXISTS, never that it is TRUE, and that this gap
  does not close — a registry's reasons need a human adversary on every pass, not once. Write it
  as a standing obligation, not an observation.
- docs/nous_roadmap.md: move the "you are here" marker. State in one line that the foundation arc
  is CLOSED and 2f is next.
- python3 tools/ledger_check.py — expect exit 1 with exactly the 16 held [C2] paper findings.
- Commit, including the four .claude/agents/*.md changes and CLAUDE-CODE-PROMPTS.md. Those are
  Cagan's reporting requirement, not code, and they have been uncommitted for two cycles.

THEN CARRY TWO THINGS FORWARD INTO SPEC-2f, and do it now while the reasoning is fresh
1. 2f is the FIRST BRICK BUILT AFTER THE DETECTOR EXISTS, which makes it the test of whether 0d
   does its only job. Write that into the spec as an explicit secondary acceptance criterion:
   did the gate catch what a manual hunt would have missed, or did it stay green while a new
   naive accumulation shipped?
2. 2f is the most likely brick to fire both absence-bound falsifiers. The spec must name them as
   preconditions the 2f builder re-checks BEFORE delivering — belt and braces alongside the
   machine check, because the machine check is one cycle old.

THEN STOP. Do not begin 0c-ii. Do not begin 2f implementation. The foundation arc ends here by
decision — not because nothing is left to improve down there, but because something always will
be, and that is the whole reason a stop has to be a decision rather than a discovery.

IF FAIL
Change no status. Commit the evidence and the corrections, never the status. Tell me in plain
language what remains.
```

---

## CC-9 · Fix the yardstick before the code ✔ DONE (AOL-1…AOL-5 frozen)

The foundation arc is closed. Before any credit-assignment code is written, Cagan's five autonomy
criteria go into the specs as **pre-registered acceptance criteria**. This is the first time in
this project's history that the yardstick is fixed *before* the mechanism exists — all three
cancelled experiments were retrofitted yardsticks, and that ordering is why they were cancelled.

Architect lane. Documents only. **No experiment runs and no code is written from this prompt.**

```
/psyche-orient

Work in the ARCHITECT-PM lane. Documents only. Do NOT write code, do NOT run an experiment, and
do NOT begin 2f's implementation. This prompt produces spec text and nothing else.

CONTEXT YOU NEED BEFORE YOU START
0d is PROVEN, and that label means "the gate does what it says" — NOT "the gate catches
everything." Nine documented holes remain. In six months someone will read "0d PROVEN" and
conclude the order-dependent-accumulation class is closed. It is not closed; it is ENUMERATED,
which is a different and more honest thing. Write that sentence into 2f's opening context, where
someone might over-read the label, not buried in a ledger note.

THE TASK
Cagan has proposed five criteria for judging whether this system is doing something mind-like.
Fold them into the specs as pre-registered acceptance criteria, with every correction and hazard
below preserved. They are his direction; the corrections are mine and they are not optional.

  Q1. Does it explore its environment differently from random, with no external reward?
  Q2. Do its self-generated goals get harder over time — an automatic curriculum?
  Q3. Does goal generation adapt to what the agent can currently learn?
  Q4. On environment change, does it drop old goals and generate new ones while RETAINING old
      skills?
  Q5. Does generating a goal COST anything — does choosing one require giving up another?
      (Q5 is added, not Cagan's. Reason below; it is load-bearing.)

RULE ONE — THE NAME. These are NOT consciousness tests and must never be labelled as such, in the
specs, the roadmap, the ledger, or the paper. They measure AUTONOMY and OPEN-ENDED LEARNING. A
system could pass all five and possess nothing any consciousness theory points at. Calling them
consciousness tests would be a rule-1 overclaim and C4 should catch it if you slip. Name the
bucket honestly and say in one line what it does not cover. Butlin et al.'s indicator properties
remain the ORTHOGONAL architectural axis (0/14, 1 partial) — say explicitly that the two axes are
complementary, not competing, because a later reader will assume one supersedes the other.

RULE TWO — RUN THE THREE-WALLS GATE ON EACH, AND WRITE THE RESULT INTO THE SPEC. All five are
MECHANISM ABSENT today: the substrate is entirely passive, nothing initiates, there are no goals
and no learning. That is a DATE, not a rejection — it is precisely why they can be fixed now. For
each question state which brick would first make it answerable at all, and what would have to
exist for a null result to be interpretable. A criterion whose null is uninterpretable is not a
criterion.

RULE THREE — SCOPE CONTROL, AND THIS IS THE ONE MOST LIKELY TO GO WRONG. These five are acceptance
criteria for a LAYER, not a feature list for 2f. 2f is temporal credit assignment and nothing
more. Route each question to the brick that could actually satisfy it, and if the honest answer is
that 2f alone satisfies ZERO of the five and is merely a prerequisite for three of them, say that
plainly. Do not let adopting a yardstick turn into adopting a roadmap. If a question is not
supportable by anything currently on the roadmap, say so and name what would have to be added.

PER-QUESTION CORRECTIONS — each is required, not advisory

Q1 — the strongest of the five, because it brings its own unfakeable control: the random baseline.
Guard: the baseline must be a REAL random policy matched on everything except the thing being
tested, not a strawman. Specify the matching explicitly.

Q2 — REQUIRES AN UPGRADE, do not adopt as stated. Difficulty growth alone is passable by a system
that generates ever-harder goals and improves at none of them, which from outside looks like a
curriculum. Current work on open-ended learning is explicit that novelty and difficulty growth do
not imply performance progress. Couple the two: measure CAPABILITY growth alongside difficulty
growth and make the conjunction the criterion. Also: difficulty must be measured externally, not
by the agent. Cite what you use.

Q3 — SCIENTIFICALLY THE STRONGEST, STRUCTURALLY THE MOST DANGEROUS. "What the agent can currently
learn" is the learning-progress signal. If the measure of what-it-can-learn and the measure of
how-much-it-learned share a source, the system passes BY CONSTRUCTION — this is 1e's circularity
in new clothes, and 1e is the wall that cost the most. Write a HARD CLAUSE: the two measures come
from independent sources, and the spec names both sources. If you cannot name two independent
sources, the criterion is not yet usable and you say so rather than softening the clause.

Q4 — needs skills to exist before it can be asked, so it sits furthest out. Its second half is
directly the catastrophic-forgetting problem and has a real external literature with baselines.
Its first half needs a defined environment change that is not authored to produce the result — say
where that change comes from.

Q5 — ADDED, AND IT IS WHAT MAKES THE OTHER FOUR UNFAKEABLE. 1e' (the fan effect) died because
nothing in the system was scarce: the engine gave every out-road the source's full activation, so
the curve was flat to the last digit. Without scarcity, generating a goal is free, and a system
can pass Q1 through Q4 by mere ENUMERATION — exploring widely, listing ever-harder goals, dropping
and regenerating them — while nothing is ever traded against anything. Scarcity is what turns goal
generation into a choice. Route it to whichever brick first introduces a shared budget, and note
that 0b2's conserved-activation overlay is the nearest existing thing.

EXTERNAL YARDSTICKS — SEARCH, DO NOT ASSERT
Every criterion in this project needs an external source. For each of the five, search for and
cite the actual literature, and state whether a usable external benchmark or baseline EXISTS. If
none exists for a question, say so plainly and design the control differently rather than quietly
inventing one — a hand-authored ground truth voids the result and that rule has already cost this
project three experiments. Ground Q2 and Q3 in the intrinsic-motivation / autotelic-agent
literature specifically; ground Q4's second half in the continual-learning literature.

PRE-REGISTRATION DISCIPLINE
Once written, these are FIXED. Record explicitly, in the spec, that no threshold moves after a
number is seen. That is the whole value of writing them now: everything this project has learned
about its own failure modes was learned from yardsticks chosen after the fact.

OUTPUT
Spec text folded into SPEC-2f and SPEC-2e (create the latter if it does not exist), plus a short
section in docs/nous_roadmap.md naming the bucket and stating what it does not measure. Update
tools/ledger.json if any status or note changes, run python3 tools/ledger_check.py, expect exit 1
with exactly the 16 held paper findings, append to DECISIONS.md, and commit.

Close with one line: where this leaves us, and what the single next action is.

Open your report with the plain-language summary for Cagan.
```

---

## CC-10 · Land the yardstick, and register a confirmed hole in C4 ✔ DONE (6425553)

`docs/CONSCIOUSNESS-YARDSTICK.md` is written and untracked in the working tree. It is the
assessment behind the "0 of 14, 1 partial" figure that had been cited for two days with no
provenance anywhere in the repo — architect-pm's catch, and correct.

**And probing it turned up a confirmed defect in C4.** Measured, not suspected:

| injected sentence | C4 findings |
|---|---|
| `Nous is conscious.` | 1 |
| `Nous is a mind.` | 1 |
| **`Nous is a conscious mind.`** | **0** |
| **`Nous is clearly conscious.`** | **0** |
| **`Nous is, in every sense, a mind.`** | **0** |

The terms match as literal substrings, so **any interpolated word evades the gate** — and the
evading forms are exactly the sentences a person writes when overclaiming. C4 guards rule 1, the
project's most important rule, and it has been weaker evidence than assumed for its whole life.

```
/psyche-orient

Work in the ARCHITECT-PM lane. Two items, both small, both about provenance. Do not begin 2f.

ITEM 1 — land docs/CONSCIOUSNESS-YARDSTICK.md
It is untracked in the working tree. It is the assessment behind "0 of 14, 1 partial", which was
cited in project records for two days with nothing in this repository backing it — C1/C2's
failure class arriving through ABSENCE rather than drift, and worse than drift because nothing
can catch it. Read it before integrating; it carries its own notes for the gates.

- Add it to claim_quarantine_paths WITH THE REASON RECORDED, not merely listed. The reason: this
  is the one document whose subject IS the claim, and whose entire content is the argument for
  why the project must never make it. A quarantine granted for convenience is how a
  forbidden-claim gate rots — so if you would not write the reason down, do not grant it.
  Check first whether it is even needed: C4 currently passes on the file unquarantined.
- Do the same for count_quarantine_paths if C2 reaches for the external figures in §2 (256
  participants, 655 electrodes) or the 0/14 score. Reason recorded, not reworded away.
- The document states that the published TiCS version could not be reached at verification time,
  so the list is verified against the arXiv preprint ONLY, with a falsifier. Preserve that
  scoping exactly. Do not upgrade it to "verified" without someone actually reading the
  published version.
- Record the standing rule: the 0/14 figure is cited BY REFERENCE to this file, nowhere else,
  ever — roadmap, ledger, paper, or conversation.

ITEM 2 — register brick 0f, a CONFIRMED defect in C4
Measured by perturbation, not suspected. C4's forbidden terms match as literal substrings, so any
interpolated word evades them:

    "Nous is conscious."               -> 1 finding
    "Nous is a mind."                  -> 1 finding
    "Nous is a conscious mind."        -> 0 findings   <-- evades
    "Nous is clearly conscious."       -> 0 findings   <-- evades
    "Nous is, in every sense, a mind." -> 0 findings   <-- evades

The evading forms are precisely the sentences someone writes when overclaiming. C4 guards
CLAUDE.md rule 1 — the rule this project's whole credibility rests on — and every "C4 passes" in
the record has therefore covered less than it appeared to.

Register it as brick 0f with that table, DESIGNED, and SCHEDULE IT BEFORE THE PAPER CAPTURE
alongside 0e. Do NOT fix it now; it is not 2f's problem and it must not delay 2f.

Record the connection explicitly in DECISIONS.md, because it is the project's own rule turning on
the project's own gate: **"a coverage axis is only evidence for the property it can perturb."**
C4 was never perturbed until now. It was found because a clean pass on a document saturated with
the forbidden vocabulary looked too easy — which is the third aphorism working as intended: the
silence of a probe counts as evidence only once the probe is shown capable of failing.

Then commit. ledger_check should exit 1 with exactly the 16 held paper findings.
```

---

## CC-11 · 2f step zero — teach the gate the shape ✔ BUILT (tester next)

SPEC-2f §0.5. The gate must see tuple-target accumulation **before** the code that would hide in
it is written. This is the whole reason 0d closed without fixing L3: ownership sits with the brick
that needs the coverage.

```
/psyche-orient

Work in the BUILDER lane. This is SPEC-2f STEP ZERO. You are NOT writing credit assignment yet —
you are extending the gate so that it can see the shape you are about to write. Do not start the
credit-assignment mechanism in this pass; if you find yourself designing an eligibility trace,
stop, you have gone past the boundary.

WHY THIS IS FIRST
The tester demonstrated that the idiomatic line 2f will write —

    trace[rid], counts[rid] = trace[rid] + e, counts[rid] + 1

produces ZERO findings from C6. The float accumulation is invisible because it sits in a
tuple-target assignment (limitation L3); split across two lines it is caught. So the gate built to
catch this project's signature defect is blind at exactly the point of use. 0d closed without
fixing it BY DECISION — ownership belongs to the brick that needs the coverage, and extending the
gate is a normal cost of building, not an interruption to it.

WHAT TO IMPLEMENT
Detect additive float accumulation in tuple-target assignments: for `t1, t2, ... = v1, v2, ...`,
pair each target with its corresponding value and apply the SAME self-referential test C6 already
uses for the single-target form — the target appearing in its own value expression under Add (or
Sub, on the left operand only, per the existing asymmetry). Cover both the plain-name form and the
subscript form, since the subscript form is the one 2f will actually write.

Enumerate what you do NOT cover and add each as a limitation with a falsifier and an asserted
negative, exactly as the existing nine are done. At minimum decide and state: starred targets
(`a, *b = ...`), nested tuple targets (`(a, (b, c)) = ...`), mismatched arity, a single value that
is not a tuple literal (`a, b = f()` — the pairing is not statically knowable, so say so), and
list-target syntax (`[a, b] = ...`).

Leave L7 out. An integer counter is not a float accumulation; that is out of scope, not a hole.

THE L3 ENTRY IS CONVERTED, NEVER DELETED
Same rule that governed the tester's nine: an entry deleted leaves no trace that the limit ever
existed; an entry converted is a record of a capability gained. L3 moves from "the scanner cannot
see tuple-target accumulation" to "the scanner sees it", with the positive case asserted and the
newly-carved limitations taking its place beside it.

ADJUDICATE WHAT SURFACES
Any new site this exposes in src/ gets adjudicated — fsum, or registered with a reason that names
a falsifier. Do not silently absorb one. If nothing surfaces, say so; that is a fine result and it
is the expected one.

REGRESSION — THIS IS THE PART THAT MATTERS MOST
You are touching the traversal of the only gate this project has. Re-run the retro-catch: extract
src/ at the three pre-fix commits and confirm C6 still catches all three historical bugs. If it
does not, stop immediately and hand back — that is the one finding permitted to reopen scope.

CONTEXT YOU SHOULD HAVE
0d is PROVEN, and that means "the gate does what it says", NOT "the gate catches everything".
Nine documented holes remain and you are closing one of them. The class is ENUMERATED, not closed.
See SPEC-2f §0.25.

RUN
Full suite on every interpreter available, plus tools/test_ledger.py. Read totals from the runner
output; never estimate. Report the interpreters swept. ledger_check exits 1 with exactly 16 [C2]
findings, all under docs/paper/ — any 17th, or any finding outside docs/paper/, is yours.

SELF-AUDIT
All seven items, including the seventh: does a builder-side assertion exist for what you wrote, or
does all evidence for it live in tester files?

Open your report with the plain-language summary for Cagan.
```

---

## CC-12 · The gate-hardening block ⏸ QUEUED — before the paper capture, NOT before 2f

**Do not run this before 2f.** It is scheduled ahead of the capture the paper cites, and nowhere
earlier. Recorded now so the reasoning is not reconstructed from memory in a month.

**Why it is one block.** Three gates have now been perturbed. **Two failed on first contact** —
the determinism probes could not see 1 ULP (they compared `round(x, 9)`), and C4 cannot see an
adverb. The one that survived, C6, survived because it shipped with an injection test *as its
acceptance criterion*. That is not luck, and the base rate is the argument: **four gates have
never been perturbed at all**, and one of them, C2, is what holds every number the paper prints.

**Standing rule, adopted now and applying forward from this moment:** *every gate ships with an
injection test proving it can fail.* Not a special measure for suspicious gates — the default.
A gate without one is an unmeasured claim wearing a green tick.

Contents of the block, in priority order:

1. **The eight unreasoned claim exemptions.** `claim_quarantine_paths` had eight entries and no
   reasons field at all, while the *counts* gate has had one all along — so the more important
   gate is the one whose exemptions were unexplained. They were flagged rather than retro-filled,
   correctly: writing reasons after the fact for someone else's exemptions manufactures provenance
   instead of recording it. Each gets adjudicated — a reason, or removal. **Ask specifically about
   `docs/design/`:** a wholesale directory exemption means the entire vision corpus is unchecked
   for overclaims, and the vision corpus is exactly where grandiose language would live. That
   exemption may well be right — vision documents are description, not specification — but nobody
   has written down why, and "may well be right" is not a record.
2. **0f — C4's interpolation hole.** Confirmed by perturbation; five evading phrasings recorded in
   the ledger, plus "undeniably sentient" and "by any measure, an AGI". The matcher must widen
   *without* breaking the negation-cue logic that keeps this project's disclaimer-dense documents
   from being flagged. Those two requirements pull against each other; that tension is the work.
3. **0e — abort-hides-tests.** A test that raises is invisible to the failure list, so "0 failures"
   can be true of the report and false of the repository. Second occurrence when registered.
4. **Perturb C1, C2, C3, C5 — the four never tested.** For each: inject the exact defect the check
   exists to catch and confirm it fires. C2 first, because the paper's numbers rest on it. Any that
   fails joins this block; any that survives gets its injection test committed as a permanent
   acceptance criterion, per the standing rule above.

5. **`post_edit_ledger.py` does not run the tests the ledger feeds.** It runs `ledger_check`
   (consistency) and reports findings naming the edited file — so a ledger edit that leaves the
   ledger self-consistent while breaking a test that reads it is invisible to it. That is exactly
   how two failures shipped silently. The hook is already wired in `.claude/settings.json`, so the
   extension point exists: on an edit to `tools/ledger.json` specifically, also run the suites that
   read it. Belt to the braces of de-brittling the assertions themselves.
6. **`tools/test_ledger.py` is outside both the canonical runner and C5's scope.** C5 scans
   `tests/`, not `tools/`, so the gate's own 191 assertions are in neither place — which is the
   silence Option B was routed to close. Land Option B in this block if it has not landed by then.

7. **C1 verifies ledger == capture, never capture == reality.** A stale capture makes both agree
   and both wrong, and C1 stays green throughout. It is live right now: at `656c38a` the ledger
   says 1,973 assertions and the repository holds 1,992. Staleness is normally bounded by the
   cycle, since the capture is retaken at close-out — but nothing detects a capture that was never
   retaken, which is precisely the "documents disagree with reality" failure C2 exists to prevent,
   arriving through the capture instead of through prose. Register it; do not fix it before 2f.

8. **Nothing compares the runner to the capture, and a whole suite went missing.** Confirmed at
   `044008c`: `test_tester_0d_adversarial` is in `run_tests.py` and **entirely absent** from
   `docs/TEST_OUTPUT.txt` — 23 suites captured, 24 in the runner — while **C1 and C5 both pass**.
   C1 compares ledger to capture; C5 compares suites on disk to the registry; neither compares
   what the runner RUNS to what the capture CONTAINS. The missing suite is the 1,335-line
   adversarial file that is the primary evidence 0d works, so the headline figure omits the
   evidence for the brick it is quoted alongside. This is the **third** occurrence of "the count
   silently under-reports" — after the unregistered-suite hole that created C5, and 0e. Cheapest
   fix is in `capture_run.py`, which already refuses on interpreter disagreement: refuse on
   runner/capture suite mismatch too.

**Bounded on purpose.** This block does not grow. Anything found beyond these four items is
registered as a limitation with a falsifier and scheduled after the paper, unless it demonstrably
lets a false claim into a document — which is the only condition permitted to widen it.

---

## CC-14 · Close 2f step zero — the tester, and four red assertions ✔ RUN (FAIL on 2f-0-2)

Four failures in the tester's own file: two are its L3 negatives flipping by design, **two are
pre-existing and were shipped silently two passes ago** by a ledger-only edit that changed a note
those tests asserted the exact prose of. Nobody re-ran the suite after a ledger edit.

**Root cause, and the fix is not a detector.** Asserting the *exact wording* of a ledger note was
always a proxy. The property those tests were for is that the note carries certain substance — a
falsifier, a correction date, a named bound. Assert the substance and the brittleness is gone at
the source, which is better than adding a hook to notice the breakage. The hook extension is
recorded in CC-12 anyway, as belt to this braces.

```
/psyche-orient

Work in the TESTER lane. The builder has landed SPEC-2f step zero — C6 now sees tuple-target
accumulation (L3). Verify it, and fix the four red assertions in your own file. Then hand back.

FOUR FAILURES, TWO CAUSES — DO NOT TREAT THEM THE SAME

Two are yours and flip BY DESIGN: your L3 asserted-negatives, because L3 is now closed. Convert
them, never delete them — the rule that governed the nine last cycle. Verify the capability with
inputs of your OWN first, not by re-running the builder's fixtures.

Two are PRE-EXISTING and were shipped silently two passes ago. A ledger-only edit changed a note;
your tests asserted its exact prose; nobody re-ran the suite because the edit "only touched a
document". The ledger is an INPUT to your tests, and editing an input can break them.

For those two, do NOT simply update the string to the new wording. That leaves the same trap armed
for the next note edit. Instead ask, for each: WHAT PROPERTY WAS THIS TEST ALWAYS FOR? Almost
certainly it was that the entry carries certain substance — that it names a falsifier, that it
records a correction, that it states the bound it rests on. Assert THAT, and the test stops
breaking every time someone improves a sentence.

THE TRAP IN THAT INSTRUCTION, AND YOU MUST NOT FALL INTO IT
"De-brittle the assertion" is one short step from "assert nothing". A check that a note is longer
than twenty characters is not a substance check, it is surrender wearing a test's clothes. For
each of the two, state in your report: the property you now assert, why that property is what the
test was always for, and — this is the part that proves it — a note that would PASS the old
assertion and FAIL the new one, or vice versa. If you cannot produce a discriminating example, you
have not written a substance check.

VERIFY THE L3 IMPLEMENTATION
- Elementwise pairing on both plain-name and subscript targets, and on the `[a, b] = ...` list
  form. The subscript form is the one 2f will actually write; hit it hardest.
- The four refusal paths — starred elements, nested targets, non-literal right-hand side, arity
  mismatch. For each: does it REFUSE, or does it silently produce nothing? Those look identical
  from outside and are completely different. A refusal that is indistinguishable from a clean pass
  is the exit-code defect in a new costume.
- Arity mismatch is recorded as a runtime error, not a limitation. Confirm that distinction holds
  and that nobody can mistake one for the other.
- The builder flagged double-counting as the risk its own change introduced, and asserted against
  it: `a, b = c, d = x + a, y + b` must report exactly `a` and `b`, with no duplicate keys, and a
  statement must take the single-target path or the sequence path, never both. Attack that
  directly — chained targets, repeated names across chained targets, and the same name as both a
  single target and a sequence element.

REGRESSION — THE ONE THAT MATTERS
Re-run the retro-catch in full. The builder changed how the gate WALKS code, which is the one
edit that can silently break everything the gate is for. All three historical bugs must still be
caught, and the per-commit counts (10/12/12) must be identical. Independently confirm the census
digest 25ff712c9002fa91 across every interpreter — that digest is the cheapest evidence that the
traversal change moved nothing it should not have.

EXPECT
ledger_check exit 1 with exactly 16 [C2] findings, all under docs/paper/. Anything else is real.

VERDICT
PASS only if L3 detection holds under your own inputs, all four refusal paths refuse visibly, the
retro-catch is unchanged, and both de-brittled assertions come with a discriminating example. Fix
nothing outside your own test file. Do not touch src/, run_tests.py, tools/ledger.json or
docs/TEST_OUTPUT.txt.

Open your report with the plain-language summary for Cagan.
```

---

## CC-15 · Two findings from the step-zero verification ✔ DONE (044008c)

Tester verdict: **FAIL on 2f-0-2**, plus 2f-0-1. The L3 capability itself holds — elementwise
pairing works on plain names, subscripts and the list form, mixed operators classify per element,
the retro-catch is unchanged at 10/12/12 and the census digest is identical on five interpreters.
Both findings are cheap, neither is reachable in `src/` today, and both become reachable **the day
2f writes the shape step zero existed for.**

```
/psyche-orient

Work in the BUILDER lane. Two findings from the tester's verification of SPEC-2f step zero. Fix
exactly these two. Do NOT begin the credit-assignment mechanism — step zero is still step zero.

FINDING 2f-0-1 — the double-count guard holds only for DISTINCT names
Your guard was verified against a fixture with distinct names, which is the shape you had in mind
when you wrote it. Repeated names break it:

    a, b = a, b = x + a, y + b        ->  4 findings at 2 distinct keys
    d[k], d[k] = d[k] + x, d[k] + y   ->  2 findings at 1 key

The count is not the damage. The census dedup turns the surplus into a PHANTOM ENTRY — a site
someone must adjudicate that does not independently exist. A registry that invents work is worse
than one that misses it, because the invented entry gets a reason written for it, and now a false
reason sits in the record. That is the failure this brick already failed once.

FINDING 2f-0-2 — THE ONE THAT FAILS THE PASS. Refusals are invisible from outside.
The refusals are real code paths — you record ('REFUSED','Tuple','Tuple') for starred, nested and
arity cases, and ('REFUSED','Tuple','Call') for a non-literal right-hand side. But `scan_source`
returns `[]` for a declined fold and `[]` for an empty file. From outside, "I could not look" and
"there is nothing here" are byte-identical. That is the exit-code contract's defect wearing a
different costume, and this project has now met that shape three times.

THE LINE TO DRAW, AND THE TESTER DREW IT — hold it exactly here
L1's multiplicative shape NEVER MATCHES, so the scanner has nothing to report and it stays a
documented limitation. L11–L13 are DECISIONS TAKEN WITH FULL KNOWLEDGE: the scanner uniquely
possesses the information that it declined, and says nothing. **Anything the scanner knowingly
declines is recorded. Anything it simply never matched stays a limitation.** Implement that line
and no wider one.

WHAT A REFUSAL IS AND IS NOT
- It is NOT a finding. A finding means the repository is inconsistent (exit 1). A refusal means a
  site exists that the scanner chose not to fold. Do not make refusals fail the build — that would
  turn three documented limitations into blockers and the gate would be disabled within a week.
- It IS countable and surfaced. `--list-accumulations` must show them, with file, line, and which
  refusal applied, alongside the census. The summary line must say so: N sites, M refusals.
- Keep the exit code unchanged. Exit 2 stays reserved for "the tool could not run at all".

DO NOT WIDEN THIS
The temptation is a general "report everything the scanner noticed" mechanism. Resist it. Two
findings, the line above, nothing else. Anything further is a limitation with a falsifier.

REGRESSION — the part that matters
You are editing the fold path again. Re-run the retro-catch in full: all three historical bugs,
per-commit counts 10/12/12, all four MUST-CATCH sites. Confirm the census digest across every
interpreter and report whether it changed — if adding refusal records changes the digest, say so
explicitly and say why that is or is not correct, rather than letting a digest change pass
unremarked.

NOT YOURS
tools/ledger.json and docs/TEST_OUTPUT.txt are stale by exactly 19 assertions (1973 -> 1992) after
the tester's commit 656c38a. Leave them. The architect recaptures at close-out.

RUN
Full suite on every interpreter available, plus tools/test_ledger.py. Totals read from the runner
output, never estimated; report the interpreters swept. ledger_check exit 1 with exactly 16 [C2]
findings, all under docs/paper/.

SELF-AUDIT
All seven items. Item seven especially: is every capability AND every refusal asserted in your own
file, or does the evidence live only in the tester's?

Open your report with the plain-language summary for Cagan.
```

---

## CC-16 · Re-point a dead assertion, and close step zero ✔ RUN (PASS; 2 of 12 assertions were dead)

Builder fixed both findings (044008c). **But its own report names the thing you must fix first:
your 2f-0-2 asserted-negative has stopped discriminating.** It asserts on `scan_source` alone, and
the builder deliberately left that contract unchanged — so it passes before the fix and after it.
An assertion that passes on both sides of the thing it names is not evidence. This is the first
aphorism landing on your own suite.

```
/psyche-orient

Work in the TESTER lane. The builder fixed 2f-0-1 and 2f-0-2 (044008c). Verify, fix the
assertions in your own file, and hand back.

START HERE — YOUR OWN ASSERTION HAS GONE DEAD
Your 2f-0-2 asserted-negative asserts on scan_source. The builder deliberately kept that
signature unchanged — widening it would have silently changed what every existing `== []` means
in both suites — and routed refusals through additive entry points instead. So your assertion
passes before the fix AND after it. It names a defect it can no longer perturb.

That is "a coverage axis is only evidence for the property it can perturb", arriving in your own
file, and it is the third time this project has met it. Re-point it at whatever now carries the
refusal — scan_source_refusals, or the listing — and prove the re-pointing worked the only way
that counts: show it FAILING against the pre-fix tool from git, and passing against the current
one. An assertion you cannot make fail on the old code is not verifying the fix.

Then ask the same question of every other assertion you wrote for this brick. How many others
would pass on both sides? Report the number honestly even if it is uncomfortable.

CONVERT, NEVER DELETE
Your double-count asserted-negatives now go red by design. Same rule as the nine and the two
before them: converted, with the positive case asserted.

THE DEDUP KEY — verify the property, not the count
The builder deduped on (kind, ast.dump(target)) rather than (kind, symbol), and its argument is
the load-bearing part: symbol-level dedup would make the tuple form report FEWER sites than the
same code split across two statements, undoing the one property closing L3 established. Test that
property directly and generatively: for a set of accumulation pairs, assert that the tuple form
and the split form report the SAME number of sites, and that d[i], d[j] stays two while d[k],
d[k] collapses to one. The count is not the claim; the equivalence is.

THE LISTING IS A CONSUMED INTERFACE — attack it as one
The builder's first version printed refusal lines beginning with the file path, and your own
loop-closed test — which feeds the listing back as a registry and takes the last token of every
src/-prefixed line — would have been handed two phantom keys. Its fix for invisible refusals was
one step from creating the exact defect it was fixing, and nothing in its own file caught it.

So: enumerate every consumer of that listing. Is your loop-closed test the only one? Does the
REFUSED prefix collide with anything a consumer might match? What happens to a consumer if a
future refusal rule is added? A gate's stdout is an API the moment anything parses it, and this
one has at least one parser nobody had listed.

THE DIGEST — redo the decomposition, do not inherit it
The builder reports the digest moved 25ff712c9002fa91 -> a2f7ed1d67f53fbe, and that the census
lines are byte-identical at b11fd55a71d900ee with only the REFUSED lines and the summary
differing. That reasoning is correct if the numbers are. Redo it yourself from git rather than
accepting the diff.

Then answer a design question and route it if you agree: should the census digest and the
LISTING digest be separate values? A census digest that moves when the report format changes is a
weaker invariant than one that does not — and this pass had to spend real effort establishing
that a digest change was benign. That is not your fix to make; say whether you agree and hand it
to the architect.

VERIFY THE REFUSAL MACHINERY
Two L13 refusals exist in src/ today. Confirm both independently. Confirm all four rules are
reachable and that each reports which rule applied. Confirm a refusal never fails the build, and
that exit 2 still means only "the tool could not run". Confirm refusals are found inside classes,
methods and match cases — the builder claims the shared walk reaches them.

REGRESSION
Retro-catch in full: three historical bugs, per-commit counts 10/12/12, four MUST-CATCH sites.

NOT YOURS, AND THE NUMBER IN THE LAST BRIEF WAS WRONG
docs/TEST_OUTPUT.txt does not contain your 0d suite AT ALL — 23 suites captured, 24 in the
runner. Confirmed independently. The capture is stale by a whole suite, not by 19 assertions.
Leave tools/ledger.json and docs/TEST_OUTPUT.txt alone; the architect recaptures.

VERDICT
PASS only if the re-pointed assertion fails against the pre-fix tool, the dedup equivalence holds
generatively, and the retro-catch is unchanged.

Open your report with the plain-language summary for Cagan.
```

---

## CC-17 · Close step zero, recapture honestly, then 2f proper begins ✔ DONE (cce3dc5)

Tester PASS. Step zero has taken **five passes** for a gate extension, and it produced real value —
L3 detection, refusal visibility, a dedup correctness fix, two dead assertions found, and a
machine-check that a future dead assertion goes red. It has also not written one line of the
learning mechanism. **After this close-out, gate work stops until CC-12.** That is a decision.

```
/psyche-orient

Work in the ARCHITECT-PM lane. Tester PASS on SPEC-2f step zero. Close it out, recapture, and
leave the project ready for 2f proper. Do NOT begin 2f's implementation.

FIRST — CLEAR A STALE LOCK, OR NOTHING BELOW CAN COMMIT
`.git/index.lock` exists, is zero bytes, and no git process is running. It blocks every index
write — `git add` fails with "Unable to create '.git/index.lock': File exists." It was left by
tooling that could not unlink it. You run natively and can:

    rm -f .git/index.lock

Also remove the empty `_to_delete/` directory in the repo root if it is still there; it was created
by the same tooling and is empty. Verify with `git add -A -n` before doing anything else in this
prompt.

RECAPTURE, AND VERIFY THE CAPTURE IS COMPLETE — this is the part that is currently broken
docs/TEST_OUTPUT.txt does not contain tests/test_tester_0d_adversarial.py AT ALL. 23 suites
captured, 24 in the runner, and C1 and C5 BOTH PASS — C1 compares ledger to capture, C5 compares
disk to registry, neither compares what the runner RUNS to what the capture CONTAINS. The missing
suite is the 1,335-line file that is the primary evidence 0d works, so the headline figure omits
the evidence for the brick it is quoted beside.

So: recapture, and then verify completeness EXPLICITLY rather than assuming it. Diff the suite
names in run_tests.py against the suite names in the new capture and report the result as a list,
not as a reassurance. The tester's file is now 334 assertions, so do not carry forward 1992 or
2281 — read the new totals from the runner output. I gave the builder 1992 and it was wrong; I had
not verified it. Do not inherit a number from a brief, including from this one.

I am choosing an instruction over a mechanism here, deliberately, and the reasoning is on the
record: three times this cycle I refused a written note in favour of a machine check, because the
trigger was future code someone else would write. Here the trigger is the next action and this
prompt is its instruction. The mechanical check — capture_run.py refusing on runner/capture suite
mismatch, since it already refuses on interpreter disagreement — is registered in CC-12.

THE DIGEST — record two values, do not change the tool
Both the builder and the tester independently propose splitting the census digest from the
listing digest, and I agree: a census digest that moves when the report format changes is a weaker
invariant than one that does not, and two consecutive passes have now spent real effort proving a
digest change was benign. That cost recurs on every pass that touches the gate.

But the tool change goes in CC-12, not here. What you do NOW is cheaper and captures most of the
value: record BOTH values in the ledger, named and distinguished —
  census digest  b11fd55a71d900ee  (the 14 census rows; unchanged across step zero)
  listing digest a2f7ed1d67f53fbe  (full --list-accumulations stdout; moved because the report grew)
Once the census digest is a named citable value, nobody has to re-derive whether a change was
benign. State plainly that they are one value in the tool today and that separating them is
registered.

STRIKE THE OBSOLETE CONSTRAINT — open for two passes now
SPEC-2f's recorded warning "write the trace update on its own line" is obsolete: L3 is closed, the
gate sees the shape. Strike it before it gets quoted as a live constraint. A stale constraint
cited as current is the same failure class as a stale count, and this project has met that class
enough times to recognise it on sight.

RECORD THE NEW STANDING RULE — the tester built it, make it doctrine
The tester now has a test that loads the pre-fix tool from git and requires each of its claims to
FAIL there. That turns "an assertion must be able to perturb the property it names" from a habit
into a gate. Two of its twelve assertions for this brick could not fail on the old code — one I
flagged, one it found itself. Write the rule into docs/METHODOLOGY.md and mark it for the paper:
**an assertion must be shown capable of failing against the code it was written against.** It is
the operational form of the third aphorism and it is stronger than the aphorism, because it runs.

NEW RULE — RECORD IT, IT COST SOMETHING TODAY
Inspecting an old revision must use `git show <rev>:<path>` or a temporary worktree — **never
`git stash`.** A stash is repo-wide, so a stash taken inside one lane silently reverts uncommitted
work in every other lane's files, and a stash that is never popped discards it. That happened
during this brick: `stash@{0}`, taken at 044008c, swallowed 315 lines of CLAUDE-CODE-PROMPTS.md and
nothing noticed. Damage was bounded to that one file — no code was lost, verified by diffing every
path in the stash against HEAD and disk — and it has been recovered from the stash and the stash
dropped. The builder did this correctly on the same task (`git show` + diff); the tester used
stash. Write the rule into CLAUDE.md's repo conventions, because lane discipline that a routine git
command can cross is not lane discipline.


ADJUDICATE AND REGISTER, briefly
- The two visible L13 refusals sit on `new_strength, new_charges = _compute_decay(...)` — the one
  place in the substrate a tuple-returning float computation actually occurs. Those refusals are
  not noise; L13 declines at exactly the interesting spot. Record that, and name what would make
  them dangerous rather than merely present.
- The listing's summary line contains `src/`, so a consumer matching on containment rather than
  prefix would capture it. The tester recorded rather than fixed it. Register it as a limitation
  with a falsifier.
- 0d stays PROVEN; its note records that L3 closed under 2f, and why ownership sat there. 2f stays
  DESIGNED with §0.5 marked complete — step zero is done, credit assignment has not started.

THEN
python3 tools/ledger_check.py — expect exit 1 with exactly the 16 held [C2] paper findings and
nothing else. Append to DECISIONS.md. Commit everything outstanding, including the builder's
uncommitted tools/ changes and CLAUDE-CODE-PROMPTS.md.

Close with one line: where this leaves us, and confirm in that line that the next action is 2f
proper — the eligibility trace — and not another gate pass.

Open your report with the plain-language summary for Cagan.
```

---

---

## CC-18 · Fix 0e now — I am overriding my own schedule ✔ DONE (d8debc2)

**0d passed its exam decisively.** C6 fired on the builder's *first save* of `nous_credit.py`,
before a single test ran — `unregistered fsum accumulation: EpisodicTrace.eligible.<return>`. The
gate did not agree with a hunt already done; it **front-ran the hunt.** That is the return on the
entire foundation arc, and it is the answer to SPEC-2f §7.1.

**And 0e happened a third time, worse.** `test_tester_0d_adversarial.py` raised, aborted at test 8
of 27, printed no `RESULT:` line, and its **334 assertions silently left the total** — 2,078
reported where ~2,412 exist. Found, again, only because someone ran the file directly.

**I verified the mechanism, and it unifies two findings into one.** Both `tools/capture_run.py`
and `tools/ledger_check.py` parse suites by pairing a `# test_x.py` header with a later
`RESULT: N passed, M failed`. A suite that aborts emits the header and never the RESULT, so
`current` stays set and the suite is **never added to `per_suite` at all.** It vanishes from the
capture, from the ledger, from C1 and from C5 simultaneously — every one of them staying green.

So the suite missing from the earlier capture was **not a capture bug. It was 0e.** CC-12 item 8
and 0e are the same defect seen from two ends.

**I am changing my own scheduling call and saying so.** I put 0e "before the paper capture" and
declared gate work closed until CC-12. That was wrong on this item: three occurrences, escalating
each time, and it is now actively obscuring the very next pass — the tester must distinguish five
red-by-design assertions from one genuine crash, which is exactly what 0e hides. My standing bar
for reopening is *the instrument is blind at the point of use and the point of use is now*, and
this clears it. This is also not CC-12's kind of work: CC-12 is about check **coverage**; this is
the runner **lying about its own totals**, which every number in the project rests on.

Bounded to this one defect. Nothing else reopens.

```
/psyche-orient

Work in the BUILDER lane. Fix brick 0e and nothing else. Do NOT touch the tester's file, do NOT
continue 2f, do NOT widen into CC-12's block.

THE DEFECT, VERIFIED MECHANICALLY
Both tools/capture_run.py and tools/ledger_check.py pair a `# test_x.py` header with a later
`RESULT: N passed, M failed`. A suite that raises mid-run emits the header and never the RESULT,
so `current` stays set and that suite is NEVER ADDED to per_suite. It disappears from the capture,
the ledger, C1 and C5 at once, and all of them stay green. Live right now:
test_tester_0d_adversarial.py aborts at test 8 of 27 and its 334 assertions are simply absent —
2,078 reported against roughly 2,412 real.

This is the third occurrence. It has now hidden an unregistered suite, then a stale delta, then an
entire 334-assertion file that is the primary evidence for 0d.

WHAT DONE MEANS
1. A suite that raises must appear BY NAME in the failure list, with the exception type and where
   it died. Never silently absent.
2. The totals must never be quietly lower because a suite died. "24 suites ran, 2 failed" and
   "23 suites ran, 1 aborted" must be visibly different outcomes in the runner's own output.
3. Decide and STATE the contract for an aborted suite's assertion count: reported as partial, or
   marked unknown. Either is defensible; silently contributing zero is not. Write the choice down
   with its reason.
4. The parsers must not be able to lose a suite. A header with no RESULT is a MALFORMED CAPTURE,
   and this project already has the right precedent for that shape: unparseable source exits 2,
   "the tool could not run", never 0. Apply the same reasoning here and say whether it warrants
   the same exit code or a finding.
5. Assert the negative: a deliberately-raising fixture suite must produce a visible entry, and
   its assertions must not vanish. That assertion must be shown capable of FAILING against the
   current code — rule four, which is now doctrine.

DO NOT FIX THE CRASH ITSELF
tests/test_tester_0d_adversarial.py raises KeyError on the new census site because the census
moved from 14/8 to 15/9. That file is the tester's and the tester converts it. Your job is that
the runner TELLS THE TRUTH about the crash, not that the crash goes away. Use a synthetic raising
suite as your fixture — if you fix the real crash to make your own work look green, you have
removed the only live specimen of the defect you are fixing.

SCOPE
The runner and the two parsers. A runner/capture cross-check is defence in depth and stays in
CC-12 — fixing the root here is what matters. Nothing else.

RUN
Full suite on every interpreter available, plus tools/test_ledger.py. Totals read from the runner
output, never estimated. Report the interpreters swept, and report the run_tests.py totals BOTH
before and after your fix, because the difference between them is the measurement of the defect
and belongs in the record.

SELF-AUDIT
All seven items.

Open your report with the plain-language summary for Cagan.
```

---

## CC-19 · Verify 2f-i adversarially ✔ RUN (0e verified; FAIL on 2f-1, the sign)

0e is fixed at the root (d8debc2) and the runner now tells the truth, which is the precondition
for this pass: the tester can finally distinguish five red-by-design assertions from one genuine
crash.

**A fifth instance of the first aphorism, and this one scopes a paper claim.** The builder found
that `capture_run` had to refuse *before* the interpreter-agreement test, because five interpreters
that all abort the same suite **agree** on a total that omits it. The five-interpreter sweep — this
project's flagship discipline — is structurally blind to any defect that behaves identically on all
five. That is not a weakness to bury; it is a scoping sentence the paper needs, exactly like
"a coverage axis is only evidence for the property it can perturb."

```
/psyche-orient

Work in the TESTER lane. Two targets, in this order. 0e first because it is the instrument your own
verdict is read from; then 2f-i, which is the real work.

PART ONE — 0e, short
The builder fixed the runner and both parsers (d8debc2). Verify independently:
- A suite that raises is named, with exception and location, and its assertion count is UNKNOWN —
  never zero, never reconstructed. Attack the reconstruction temptation: confirm no code path
  invents a partial count from FAIL: lines.
- The end-of-input arm: an aborted LAST suite has no following header to reveal the gap. Confirm
  it is caught, and that your probe for it could actually have failed.
- Exit 2, not 1, and `ledger_sync` refuses. Confirm the contract matches CensusUnreadable's.
- The builder found three readers disagreeing — `classify` took the last RESULT, both parsers took
  the first, and a comment claimed "last wins" when the code never did. Confirm all three now agree
  and that the agreement is asserted, not merely true today.
- Confirm the ordering the builder chose: refusal happens BEFORE the interpreter-agreement check.
  Then state, for the record, which of YOUR OWN probes share that same blindness — a defect
  identical on all five interpreters is invisible to a five-interpreter sweep, and that is now a
  known limit of this project's flagship discipline.

PART TWO — 2f-i, the eligibility trace. This is the pass that matters.

FIRST, THE OVERLAY. If `off` is not byte-identical to previous behaviour, nothing else matters and
the migration argument collapses. Attack that claim before anything else, ON A FROZEN CLOCK — a
live clock manufactures a difference and this project has filed a false defect that way before.
Measure the noise floor first: run two identical off-calls and confirm they agree, before
concluding anything from an off-vs-on comparison.

PARAMETER VALIDATION — this project's most expensive repeat offender. `decay` and `P_PRP` are
numbers a caller supplies. DEFECT-C was `float('inf')` producing NaN that sailed through a floor
guard because every NaN comparison is False. So: decay = 0, 1, >1, negative, NaN, inf, -inf;
P_PRP the same; window = 0, 1, negative, larger than all history. For each, does it validate, or
does it produce a well-formed wrong answer? A well-formed wrong answer is the worst outcome and it
is the one this substrate keeps producing.

THE WINDOW BOUNDARY. The claim is credit decays with distance and is EXACTLY zero past the window.
Test the boundary itself, both sides, off-by-one in both directions — and remember the second
aphorism: a boundary located by sampling is the last sample, not the boundary. Establish it
structurally if you can, not by probing until it stops moving.

EVERY CONTROL — CHECK IT CAN EXHIBIT A DIFFERENCE. The builder found its own shuffled-control test
was VACUOUS: it compared road ids across two independently-built stores, so both arms measured zero
and the control proved nothing while passing. That is the fourth instance of this failure class in
a week. Audit every control in both suites, yours and the builder's, and for each state what result
would have made it fail. A control that cannot fail is decoration.

DOUBLE-COUNTING SEMANTICS. The builder asserts a road traversed three times in one cycle
accumulates eligibility to exactly 3.0 but is written once. Verify the mechanical property. Then
flag — do not decide — whether "three traversals earn triple credit" is a design choice that was
made deliberately or fell out of the implementation. That distinction is the architect's to
resolve, and it is exactly the kind of thing that silently becomes a claim.

DETERMINISM, ON THE APPLICATION SIDE. The fold is fsum and registered. But the trace is keyed by
road id, and road ids are uuids. Ask whether the ORDER in which credit is applied across roads can
change any outcome — and if the answer is "no, each application is two-operand", prove that
structurally rather than by observing it.

LOOP-CLOSURE, HARDER THAN THE BUILDER DROVE IT. Multiple cycles, roads that repeat, roads that
appear and vanish between cycles, an outcome with no preceding traversal, a trace longer than the
window, an empty trace. All driven by real think() output, never values you chose.

THE TWO ABSENCE BOUNDS — check independently, do not inherit. The builder says
`ActivationField.flow` has no new reader and `advance()` has no new caller, and checked the
`getattr`/`__dict__` routes the machine check is blind to. 2f is the brick most likely to fire
both. Redo the search your own way.

LANGUAGE — YOU ARE THE GATE HERE, BECAUSE THE REAL ONE IS BROKEN. 0f is registered and unfixed:
C4 matches literal phrases, so any interpolated word evades it. Read every docstring, comment and
identifier in the new module as a human. "Learns", "remembers", "wants", "understands" — and the
adjectival forms that C4 cannot see. Report what you find, including nothing.

VERDICT
PASS only if the neutral value is byte-identical under attack, every parameter either validates or
its failure mode is asserted, the window boundary is established rather than sampled, and every
control can be shown capable of failing. Fix nothing outside your own test file.

Open your report with the plain-language summary for Cagan.
```

---

## CC-20 · The sign problem — 2f-i is half of credit assignment ✔ DONE (7886167)

Tester FAIL on 2f-1, and it is the most consequential finding of the brick. `outcome_magnitude`
takes `abs()`, so telling the system an outcome was **bad** strengthens the preceding roads exactly
as much as telling it the outcome was **good**. `-1.0` and `+1.0` are byte-identical in effect.
Nothing says so, and the builder's suite never tried a negative.

**Ruling: refuse the negative at the boundary. Do not build the weakening path.** Reasoning below,
in the prompt, because it is the part that must survive into the record.

```
/psyche-orient

Work in the BUILDER lane. Two findings from the tester's verification of 2f-i. One is a fix, one is
a recording. Neither expands the brick.

FINDING 2f-1 — MY RULING, AND WHY IT IS NOT THE OBVIOUS ONE
`outcome_magnitude` is abs()'d, so an adverse outcome reinforces exactly like a favourable one. The
tester named two defensible options — refuse the negative, or honour it — and one indefensible one,
which is what ships today.

RULING: refuse a negative at the boundary. Do NOT build a weakening path in this pass.

Why not honour it: honouring a negative requires a depression path that does not exist. Building
one now means inventing its arithmetic and at least one uncalibrated constant, mid-verification, in
a brick already under a FAIL. That is the exact pattern this project has spent a week learning to
stop.

Why refusing is not merely the cheap option: the refusal message states a TRUE thing about what is
built. Write it so it says so — that this mechanism has no way to represent an adverse outcome, so
passing its magnitude would silently reinforce what it was meant to discourage. An error that
teaches is worth more than a branch that copes.

Then assert it as an explicit negative in your own suite: the trace is POTENTIATION-ONLY; there is
no depression path; a negative outcome is refused rather than absorbed.

AND STATE THE CONSEQUENCE PLAINLY IN YOUR DELIVERY REPORT — this is the part that matters most
A one-signed rule is not credit assignment in the sense the roadmap means. Everything that follows
from it, you must write down rather than let a reader infer:

- Every outcome, favourable or adverse, strengthens whatever preceded it. The graph moves in one
  direction only, toward saturation. Nothing can be un-learned.
- So the mechanism as built assigns ATTENTION, not CREDIT. Feedback without a sign is not feedback.
- Therefore 2f-i does NOT satisfy Butlin AE-1 ("learning from feedback and selecting outputs so as
  to pursue goals, especially where this involves flexible responsiveness to competing goals"), and
  it does not move any of the five pre-registered AOL autonomy criteria. Say both, by name.

This is not a hedge. It is the difference between a brick that is honestly half of a mechanism and
a brick that quietly claims to be the whole one. The half we have is real and it is verified; the
half we lack is the half that makes it learning.

FINDING 2f-2 — RECORD IT AS DELIBERATE, DO NOT CAP IT
Three traversals in one cycle earn exactly triple eligibility, linear and unbounded — 10,000
repeats give 10000.0 — bounded only downstream by `strengthen`'s saturation. SPEC-2f specifies
nothing, so today it is an implementation consequence, which is precisely the kind of thing that
later gets cited as a design choice nobody made.

RULING: leave it linear, and record it as a decision with its reason and its falsifier. Do not add
a cap. A cap means inventing a constant with no calibration, and this project maintains an
`uncalibrated_constants` list because that trap has been sprung before. The reason it is safe
today: the downstream saturation in `strengthen` bounds the reachable effect, so unbounded
eligibility is not reachable as unbounded strength.

FALSIFIER, write it next to the decision: any path where an eligibility value reaches something
that is NOT saturated downstream.

SCOPE — AND THE THING YOU MUST NOT DO
Do not build the depression path. Do not add a cap. Do not touch the tester's file. The weakening
mechanism is a separate brick with its own spec, its own calibration decision and its own gate; the
architect registers it. If while fixing this you find yourself designing how a road should weaken,
stop — you have left the brick.

RUN
Full suite on every interpreter available, plus tools/test_ledger.py. Totals read from the runner
output, never estimated. The runner now names an aborted suite and marks its count UNKNOWN, so read
the outcome line as well as the totals. ledger_check exits 1 with exactly 16 [C2] findings under
docs/paper/, plus a C5 finding for the tester's new unregistered file — that one is the architect's
to register and is not yours to silence.

SELF-AUDIT
All seven items.

Open your report with the plain-language summary for Cagan.
```

---

## CC-21 · Close 2f-i — narrow verification ✔ RUN (PASS; findings 2f-3, 2f-4)

Builder closed both findings (7886167). It removed `abs()` rather than guarding around it — leaving
it would have kept saying "the sign does not matter here", which is the claim the guard denies. It
kept `0.0` accepted and writing nothing, because an outcome of no size is not an adverse outcome.
And it put the consequence in the module rather than the report.

**A pattern worth naming, because it is now the third instance:** a text scan cannot tell a
mechanism from its negation. It bit the `traversal_count` deadness check, it bit the builder's own
potentiation check today (red on the module's docstring *saying no such path exists*), and it is
exactly why C4 evades on an interpolated word (0f). Where the thing being checked is CODE, decide
by AST. Where it is PROSE — C4 — no AST exists, so 0f's fix has to lean on negation cues and must
not pretend to be structural. That belongs in CC-12's notes.

```
/psyche-orient

Work in the TESTER lane. Narrow re-verification of 2f-i after the builder's fix (7886167). Convert
your own suite, verify the two closures, hand back.

FIRST — YOUR SUITE ABORTS, AND THAT IS 0e WORKING
Your 2f-1 asserted-negative calls with -1.0, which now raises, so your suite aborts. Note for the
record that 0e's fix NAMED it rather than letting its assertions vanish — that is the first time
this defect has been caught in the wild by the mechanism built for it, and it is worth one line.

Convert, never delete: the assertion moves from "a negative is silently absorbed" to "a negative is
refused, and here is what the caller is told". Prove the conversion the only way that counts — show
it FAILING against 1065c43, where the abs() still lived.

VERIFY THE REFUSAL, NOT THE MESSAGE
- `abs()` is removed, not merely guarded. Confirm structurally: no path can reach the arithmetic
  with a sign-stripped value.
- `0.0` is accepted and writes nothing. `-0.0` — decide what it does and confirm the code agrees
  with whatever it claims. Python says `-0.0 >= 0` is True; is that the intended answer, or an
  accident of the comparison? Flag it either way.
- Purity under refusal: the store must be byte-identical after a refused call, meaning the guard
  raises before any write. Verify independently, do not inherit.
- The refusal message states a claim about the system ("no depression path exists"). Verify the
  CLAIM, not the wording.

THE STRUCTURAL ARGUMENT IS THE LOAD-BEARING ONE
The builder now decides potentiation-only by AST call graph, asserting the store surface is exactly
`get_road` + `strengthen`. That claim is what makes "nothing here can weaken a road" true rather
than merely observed. Re-derive it yourself, your own way, and attack it: does any path reach the
store other than through those two? `getattr`, aliasing, a held reference, a mutable returned
object. This is the same blind spot FINDING 0d-5 named in the absence-bound checker.

2f-2's FALSIFIER — is it live or hypothetical?
The recorded falsifier is "any path where an eligibility value reaches something not saturated
downstream — a consumer reading CreditAssignment.eligibility or .gain and acting on the raw
magnitude." Check whether such a consumer exists TODAY. If one does, the recording is already
false and that is a finding. If none does, say so and say what would create one.

FLAG, DO NOT ADJUDICATE
The module now asserts that AOL-2, AOL-3 and AOL-4 each require an outcome to be able to make an
earlier action LESS likely. That is a claim about SPEC-2e, and claims about specs become citable.
Check it against the actual text of those three criteria and report agreement or disagreement. Do
not decide it — that is the architect's.

RULE FOUR
Every assertion you add or change in this pass must be shown capable of failing against 1065c43.
That is doctrine now, not a request.

SEQUENCING — read this before you finish
`ledger_check` reports one [C5] for your unregistered file. Do NOT register it; that is a
fact-of-record change and the architect's lane. But note in your hand-off that registration should
happen AFTER your conversion lands, or the runner gains a second aborting suite.

VERDICT
PASS only if the conversion fails on 1065c43, the store surface is independently confirmed, and the
2f-2 falsifier is shown live or hypothetical rather than assumed.

Open your report with the plain-language summary for Cagan.
```

---

## CC-22 · Right conclusion, wrong reason ✔ DONE (6411ef7; a third instance found by the builder)

Tester PASS with two findings, and **both are the same class: the conclusion is correct and the
stated reason is not.** 2f-i really is potentiation-only — but the argument given for it guarantees
nothing. AOL-2/3/4 really are unmoved — but not for the reason written in the module.

That class is more dangerous than being wrong outright, because it **survives review**: a reader
checks the conclusion, finds it true, and inherits a false argument. It is the same thing F-6
taught on the registry — *a gate can verify a reason EXISTS, never that it is TRUE* — arriving in
prose instead. Standing form: **verify the reason, not just the conclusion.**

```
/psyche-orient

Work in the BUILDER lane. Two findings from the tester (c23c591). Both are "right conclusion,
wrong reason", both live in shipped code, and neither expands the brick. This is the last
correctness pass on 2f-i.

FINDING 2f-4 — a false justification in a shipped module. Fix the reason, keep the conclusion.
Your module states that AOL-2, AOL-3 and AOL-4 "each need an outcome to be able to make an earlier
action less likely." Checked against SPEC-2e's actual text: none of the three says that. AOL-2 is
difficulty growth conjoined with capability growth; AOL-3 is goal generation adapting to a
learning-progress signal; AOL-4 is skill retention grounded in catastrophic forgetting and BWT.

Your conclusion is right and your reason is invented. Replace it with the true one, which the
ledger already carries and which is STRONGER: D-023 — all five AOL criteria are MECHANISM ABSENT.
2f-i does not move them because nothing in the system initiates, has goals, or has skills; not
because of a property of the three criteria you inferred. Cite D-023 rather than restating it.

Keep the AE-1 claim, which is correct on its own terms, and check its stated reason with the same
suspicion.

FINDING 2f-3 — the potentiation-only claim is TRUE; its stated basis does not establish it
`store.get_road(rid, apply_decay=False)` returns the LIVE stored Road — two calls give the same
object, and assigning `.strength` or mutating `.charges` through it reaches the store.
`apply_decay=True` copies, and that asymmetry is what makes this easy to miss. So "the store
surface is get_road + strengthen, and strengthen only increases" bounds nothing: a future edit that
binds the returned road and halves its strength weakens a road AND leaves your AST assertion green.

Today your module reads the attribute immediately and never binds it, so the brick is correct. Fix
the ARGUMENT, in two steps:

1. Restate the basis truthfully: the claim rests on **no code in `src/` binding a returned road and
   writing through it** — an absence, not a structural impossibility. Say so in those terms.
2. Make that absence machine-checked, using the pattern already built for 0d's
   `bound_on_absence` — an absence a future brick can silently invalidate is precisely what that
   machinery exists for. The cheap sound-ish form: flag any Assign whose value is a call to
   `get_road`, and let a human dismiss each with a written reason. **Bias it toward
   over-reporting** and document that, exactly as FINDING 0d-5's fix does — a false positive costs
   one sentence, a false negative is a silently false guarantee.

If a general "write-through-a-returned-object" check turns out to need real dataflow rather than a
pattern match, DO NOT build it. Say so plainly, ship the narrow binding check, and hand the general
case to the architect as its own brick. Do not let a guarantee-hardening turn into a static
analyser.

WHAT YOU MUST NOT DO
Do not change `get_road` to copy, and do not freeze `Road`. Both are real options, both carry a
re-validation cost against a PROVEN brick (0a), and neither is a 2f-i change. The architect
registers the encapsulation question — 0a hands out a write-capable reference from a method
documented as a pure read; purity is not violated, but there is no encapsulation.

INHERIT THE WEAKNESS HONESTLY
The absence-bound checker is blind to `getattr`, aliasing and `__dict__` (FINDING 0d-5). Your new
bound inherits that. State it where the bound is recorded rather than letting a reader assume the
check is complete.

RULE FOUR
Every assertion you add must be shown capable of failing against 7886167.

RUN
Full suite on every interpreter available, plus tools/test_ledger.py. Totals read from the runner
output. The 0d tester suite still aborts and is the tester's to convert — the runner names it, so
do not mistake it for a regression. ledger_check: 16 [C2] under docs/paper/, plus the [C5] for the
tester's file which the architect registers next.

SELF-AUDIT
All seven items — and one extra this pass, given the finding: for every claim you leave in a
docstring, is the REASON checked, or only the conclusion?

Open your report with the plain-language summary for Cagan.
```

---

## CC-23 · The wrapped-string sweep ✔ DONE (19d3286; PASS, 0 vacuous, runner exits 0)

Builder corrected both false reasons (6411ef7), then **applied the same suspicion to AE-1 and found
a third itself**: the stated reason addressed only the "especially" clause — the criterion's most
conditional part — when AE-1 fails at its **first conjunct** (this module selects no outputs and
pursues no goals). *The reason had picked the clause furthest from the actual failure.*

**And it caught one of its own assertions being vacuous:** a string search spanning a docstring line
wrap could never match. A passing assertion proving nothing.

**That is a whole class, not one bug.** This repository hard-wraps prose everywhere, so *every*
multi-word string assertion against a docstring, a spec or a ledger note is a candidate. It is also
the same root as C4's interpolation blindness and the text-scan-vs-negation problem: **matching text
that was never normalised.** Sharpened form of rule six: *normalise before matching text, and prove
the matcher can find what it is looking for.*

```
/psyche-orient

Work in the TESTER lane. Last verification pass on 2f-i (builder at 6411ef7). Three jobs, then
hand to the architect.

JOB ONE — THE WRAPPED-STRING SWEEP. This is the headline, not the cleanup.
The builder found one of its own assertions vacuous: it searched for a string that spans a
docstring line wrap, so it could never match, and it passed. This repository hard-wraps prose
everywhere, which makes every multi-word string assertion against a docstring, spec, ledger note or
comment a candidate for the same defect.

Sweep BOTH suites — yours and the builder's — for every assertion that matches a multi-word string
against wrapped prose. For each, do not eyeball it: run the search against text where the phrase is
KNOWN to be present and confirm it is found. Any that cannot find its own target is vacuous; report
the count honestly, including zero, and fix the ones in your file. The builder's are its own.

This is the same root as two defects already registered — C4's interpolation blindness (0f) and the
text-scan-that-cannot-tell-a-mechanism-from-its-negation. All three are matching text that was never
normalised. If your sweep supports that generalisation, say so; if it does not, say that instead.

JOB TWO — CONVERT THE 0d SUITE. It has aborted for four passes now.
Five assertions pin the census at 14 sites / 8 fsum; it is now 15 / 9, plus the new `binding`
absence kind. Convert, never delete. Each conversion proved by failing against the revision where
the old value was correct.

JOB THREE — ATTACK THE NEW BOUND, ESPECIALLY ITS DISMISSALS
The potentiation-only claim now rests on a machine-checked absence: no code in `src/` binds a
returned road and writes through it. The builder registered a `binding` kind, found four existing
bindings, and dismissed each with a reason.

- Verify each of the four dismissals YOURSELF. Three reportedly read only `source_id`/`target_id`;
  one uses `apply_decay=True` and receives a copy. A dismissal is a written reason, and this project
  has already failed a brick because two written reasons were false.
- Confirm the bound bites: plant `road = get_road(...); road.strength *= 0.5` and confirm C6 goes
  red. Then plant the forms the check CANNOT see — `getattr`, aliasing, a write through a container,
  a road returned from a helper — and confirm each one slips through. That is not a failure; it is
  the documented blind spot, and it must be asserted rather than assumed, so nobody later reads a
  clean run as "no write path exists".
- The general dataflow case was declined deliberately and handed to the architect. Confirm the
  decline is recorded where a reader would look, not only in a report.

VERIFY THE THREE CORRECTED REASONS, NOT THE CONCLUSIONS
D-023 cited rather than restated; the invented AOL text absent under a NORMALISED match, not a raw
one; AE-1's reason now naming the first conjunct. And check the remaining docstring claims the
builder enumerated — not-RL, no behavioural tagging, not-a-synaptic-analogue, linear repeats — with
the same question: is the reason checked, or only the conclusion?

RULE FOUR, and it is exactly what failed here
Every assertion you add or change must be shown capable of failing against 6411ef7 — and for string
matches, that proof must use a normalised comparison, or you will reproduce the defect you are
sweeping for.

HAND-OFF
Registration of your file is the architect's and is now unblocked. State clearly in your hand-off
whether 2f-i is done from your side.

Open your report with the plain-language summary for Cagan.
```

---

## CC-24 · Close 2f-i ✔ DONE (b09e7be)

Tester PASS (19d3286). **The runner exits 0 for the first time in this arc: 2,441 passed, 0 failed,
25 suites, 0 aborted.** The wrapped-string sweep came back clean — the builder's was the only
vacuous assertion and it was already fixed.

**My generalisation was refused, and the refusal is right.** I proposed recording C4's interpolation
blindness, the mechanism-vs-negation scan and the wrapped string as one class. The tester's
objection: all three are substring matching on structured text, but they need **three different
fixes** — tokenisation, parsing, whitespace normalisation. *"A single 'normalise everything' pass
closes one third of the class while looking like it closed all of it."* That is this project's
signature failure mode aimed at my own proposal. Not merged.

**And the sweep produced a sharper rule than the one I gave it:** a positive `X in Y` that passes is
live **by construction**; only a negative `X not in Y` can pass while the phrase could never match.
That is the precise shape of the vacuous class, and it is checkable.

```
/psyche-orient

Work in the ARCHITECT-PM lane. Both builder and tester have signed off on 2f-i. Close it out,
recapture, register what is outstanding. Do NOT begin the next brick.

RECAPTURE, AND VERIFY COMPLETENESS BY NAME
The runner exits 0 at 2,441 passed / 25 suites / 0 aborted. Recapture across all five interpreters,
then diff runner suite names against capture suite names and report the result AS A LIST, not as a
reassurance. Read every total from the runner output; inherit no number from this brief.

REGISTER THE TESTER'S FILE
`tests/test_tester_2f_adversarial.py` is unregistered ([C5]) and now runs clean, so registering adds
no aborting suite.

2f-i's STATUS — decide and justify on BOTH axes, separately
Build status: the mechanism is tester-verified. Meaning verdict: D-023 already holds that all five
AOL criteria are MECHANISM ABSENT, and 2f-i does not satisfy Butlin AE-1. Do not collapse the two.
Say what 2f-i IS — a verified eligibility trace — and in the same breath what it is NOT.

**The sentence that must survive into the roadmap:** the mechanism assigns ATTENTION, not CREDIT.
Every outcome it can express strengthens what preceded it; the graph moves one direction only.
The half that exists is real and verified; the half that is missing is the half that would make it
learning.

REGISTER THREE THINGS AS THEIR OWN BRICKS
1. **The depression path.** The missing half. Own spec, own calibration decision, own gate. Nothing
   above it can be called learning until it exists. This is the headline item on the roadmap now.
2. **Encapsulation / the general write-through case.** `get_road(apply_decay=False)` hands back the
   live stored Road, so 0a gives out a write-capable reference from a method documented as a pure
   read. Purity is not violated; encapsulation is absent. The general "does a write follow a
   binding" question is dataflow and was deliberately declined. Record both halves and the two
   options considered and rejected for now (copy on read; freeze `Road`), each with its
   re-validation cost against a PROVEN brick.
3. **2f-5 — the registry rots on line numbers.** `bound_on_absence` dismissals are keyed
   `path:line` and shift on any edit above them: one inserted comment in `nous_field.py` fires a
   false [C6]. It already cost a real mis-measurement — the tester's first blind-spot probe reported
   all five blind spots as CAUGHT, which was the shifted bound firing, not the binding bound
   working. **A false positive that masquerades as the check working is worse than a silent gap**,
   and a gate that cries wolf gets ignored, which would waste the whole foundation arc.
   **Schedule it as STEP ZERO of the next brick**, exactly as L3 was step zero of 2f — the next
   brick edits `src/` and will trip it constantly. A content-anchored key closes it.

RECORD FOUR THINGS IN DECISIONS.md
- **My proposed generalisation was refused, and correctly.** Three substring-matching defects, three
  different fixes; merging them would have produced a named class that looks closed while one third
  is. Record the refusal, not just the outcome — a boss proposal overturned by evidence is the lane
  discipline working, and it should be visible that it happened.
- **The vacuous-assertion rule, in its sharp form:** a positive containment assertion that passes is
  live by construction; only a negative containment assertion can pass vacuously. Add to
  METHODOLOGY beside rule four and mark for the paper.
- **A hand census that copies the scanner is not a second opinion.** The tester derived 0d's census
  by hand rather than reading the tool. Small, load-bearing, easy to lose.
- **"Six naive, unchanged" is the substantive half of the census claim** — 2f-i added no naive
  accumulation. The count that did not move carried more information than the one that did.

THEN
`python3 tools/ledger_check.py` — expect exit 1 with exactly the 16 held [C2] under `docs/paper/`
and nothing else once the [C5] is registered. Append to DECISIONS.md. Commit everything.

Close with one line: where this leaves us, and name the next action.

Open your report with the plain-language summary for Cagan.
```

---

## CC-26 · 0g — the registry that rots ✔ DONE (5a1c385, b2f71f6)

SPEC-2g is re-scoped to option C and **brick 2h** carries 0b2's unpaid default-flip debt (9c15249).
The architect verified my premise instead of adopting it, and **found a refinement I had missed**:
B and C are not merely complementary, they are **composed** — Miller & MacKay's central result is
that the choice of normalisation constraint changes what the local rule converges to. So 2h will
*perturb* 2g, not sit beside it, and 2h's delivery must re-run 2g's graded-effect invariants. It
also excluded Carandini & Heeger as not bearing on plasticity rather than counting it as support,
and marked its own epistemic status as assessed-from-knowledge rather than re-read.

**Now 0g — and I verified the shape myself. It is worse than "a gate that cries wolf".**

`tools/ledger_check.py:636`, the `Accumulation` docstring, in the same file:

> *"`key` is `<path>:<scope>.<symbol>` — deliberately NOT a line number, because a registry keyed by
> line rots on every insertion above it and **trains people to re-key mechanically instead of
> re-reading**."*

And the `dismissed` entries inside `bound_on_absence`, one field away, are keyed
`src/nous_field.py:123 — …`. **The exact thing the docstring warns against, reintroduced beside it.**
The docstring also names the real harm, which is sharper than false positives: a rotting registry
teaches people to update keys without re-reading the reason — and in this project the reason **is**
the entire guarantee.

```
/psyche-orient

Work in the BUILDER lane. Brick 0g, and it is SPEC-2g's mandatory §0. Fix this and nothing else.
Do NOT begin 2g's mechanism.

THE DEFECT, AND IT IS WRITTEN AGAINST ITS OWN DOCSTRING
`bound_on_absence` dismissals are keyed `path:line`. `tools/ledger_check.py:636` — the
`Accumulation` docstring, in the same file, one field away — already says the key is deliberately
NOT a line number, "because a registry keyed by line rots on every insertion above it and trains
people to re-key mechanically instead of re-reading." The rule was written down, and then broken
next to where it was written.

It has already cost a real mis-measurement: the tester's first blind-spot probe prepended to a
module and reported all five blind spots as CAUGHT. That was the shifted bound firing, not the
binding bound working — **a false positive that masqueraded as the check working.** Worse than a
silent gap, because it makes an uncovered blind spot look covered.

THE FIX IS NOT NEW DESIGN — IT IS THE FORMAT THIS FILE ALREADY DOCUMENTS AND USES
Key dismissals the way `Accumulation.key` is keyed: `<path>:<scope>.<symbol>`. You are applying an
existing, already-correct convention to a field that skipped it, not inventing one.

THE WHOLE DESIGN PROBLEM, IN ONE SENTENCE — hold both halves
**The key must be STABLE under irrelevant edits and UNSTABLE under relevant ones.** Stable-only is
what you get by keying on nothing; unstable-only is what we have. A key that survives the site
actually changing is worse than a line number, because a stale dismissal then silently excuses a
site that is no longer the site it was written about.

So decide and state, with reasons:
- What identifies a dismissal when a scope contains SEVERAL matching expressions — an ordinal? the
  expression text? Say what happens when one of them is deleted.
- What happens when the enclosing scope is renamed. That is a relevant change; the dismissal should
  not survive it silently.
- What happens when the dismissed expression itself changes while the scope does not.

ASSERT BOTH DIRECTIONS. This is the part that proves the fix rather than claiming it.
- Insert a comment line at the top of `nous_field.py`: every dismissal still holds, **no false
  [C6]**. Prove this assertion fails against the pre-fix revision.
- Change the dismissed expression at its site: the dismissal must **stop** applying and the finding
  must reappear. A key that cannot go stale cannot be trusted to be fresh.
- Rename the enclosing scope: the dismissal must not silently carry over.

MIGRATE THE EXISTING DISMISSALS, AND RE-READ THEM WHILE YOU DO
There are dismissals under `nous_field.py:build_activation_field.merged_flow` and under
`nous_credit.py:EpisodicTrace.eligible.<return>`. Do NOT mechanically re-key them — that is exactly
the behaviour the docstring says a rotting registry trains. **Re-read each reason and confirm it is
still true of the site it now points at**, then re-key. Report any that had already drifted.

SCOPE
The dismissal key format, its migration, and its assertions. Nothing else. Do not extend the
absence-bound checker's coverage; FINDING 0d-5's blind spots (`getattr`, `__dict__`, aliasing) stay
exactly as documented, and the general write-through-a-binding question stays declined in 0a-ii.

REGRESSION
Re-run the retro-catch in full — three historical bugs, per-commit counts 10/12/12, four MUST-CATCH
sites. Report both digests and say whether each moved and why. You are editing the gate the next
brick depends on.

RUN
Full suite on every interpreter available, plus tools/test_ledger.py. Totals read from the runner
output, never estimated. ledger_check exits 1 with exactly 16 [C2] under docs/paper/.

SELF-AUDIT
All seven items, plus the one this arc added: for every claim you leave in a docstring, is the
REASON checked, or only the conclusion?

Open your report with the plain-language summary for Cagan.
```

---

## CC-27 · Verify 0g ✔ DONE (401f7ee; PASS; census 11 of 22)

0g is fixed (`5a1c385`, `b2f71f6`). Key is now `<path>:<scope>.<expression>` — the format
`Accumulation.key` already documented, applied to the field that skipped it. **Both directions
asserted**, the no-false-alarm half proved by showing one comment line still fires a false [C6] on
the pre-fix tool. An ordinal was rejected with the right reason: deleting an earlier occurrence
renumbers the later one — line-number rot again, smaller blast radius, same shape. **A stale reason
was found by re-reading**, exactly as the docstring predicted mechanical re-keying would preserve.

**And the finding that matters most has nothing to do with 0g.** Both recorded digests had been
**stale since `1065c43`** — four passes — because 2f-i added the fifteenth site and nothing checked
them. The builder proved its own change moved neither, by running both tools against both trees.

**That is the fourth instance of one shape, and it deserves a name.** C1 verifies ledger == capture,
never capture == reality — which is how a whole suite vanished. C3 verifies a status is a legal
token, never that it matches what the code does — which is how `0e` read `DESIGNED` for two passes
after being fixed. And now the digests: recorded so nobody would re-derive them, and therefore
never re-derived.

> **Rule 12 — a fact recorded to avoid re-derivation must have exactly one thing that re-derives
> it.** Otherwise the record is a claim with no falsifier, and the ledger's entire design — record
> it once so nobody recomputes it — becomes a machine for manufacturing confident stale numbers.

The three are **one family and get one check**, in CC-12, built together rather than patched
separately. Until then the digests are recorded-but-unchecked and must say so where they are
recorded.

```
/psyche-orient

Work in the TESTER lane. Verify 0g (5a1c385, b2f71f6), convert your six red assertions, hand back.
This is the last pass before 2g's mechanism.

JOB ONE — CONVERT YOUR SIX
Six assertions in tests/test_tester_2f_adversarial.py are red by design: they assert the old
line-keyed dismissals, plus FINDING 2f-5's asserted-negative, which correctly flips now the defect
is fixed. Convert, never delete, each proved by failing against b09e7be.

JOB TWO — THE INSTABILITY DIRECTION IS THE ONE THAT MATTERS
Stability is easy to get by keying on nothing. **A key that cannot go stale is worse than a line
number**, because a dismissal that survives its site changing silently excuses a site that is no
longer the one it was written about. So attack instability hardest:
- Change the dismissed expression: the dismissal must stop applying and the finding must return.
- Rename the enclosing scope: the build must go red. **And verify the MECHANISM, not the colour** —
  the builder says the finding is "unregistered accumulation", not a revived bound, because the
  registry's own key is scope-anchored too, so the entry unmatches and the bound is never
  evaluated. Red by a different path than a reader would assume. That is a reason, and this arc has
  taught that reasons are where the errors live. Confirm it or refute it.
- Move a dismissed site to a different scope entirely. Delete it. Duplicate it.

JOB THREE — THE DOCUMENTED LIMITATION, AND WHETHER ITS MERGED REASON IS TRUE
Two textually identical occurrences in one scope share a key, so one reason covers both. The
builder found this the hard way: the old 167 entry read "used solely for road.target_id" — true of
that line, false of the merged site, and mechanical re-keying would have carried it forward.
Verify the merged reason is now true of BOTH occurrences, not just the one someone was looking at.
Then test the limitation's edges: what happens when the two diverge, and when one is deleted?

JOB FOUR — THE REFUSALS AND CONTRACTS
- A legacy `path:NNN` dismissal gets its own finding, so a half-migrated ledger cannot pass while
  its old entries excuse nothing. Confirm, and confirm a MIXED ledger fails rather than partially
  passing.
- Keys are whitespace-free by construction, asserted as a contract — the builder's first format
  produced `road = store.get_road`, which `split(" ", 1)[0]` truncated to nothing. Attack the
  parser directly: tabs, unicode spaces, an empty key, a key containing the delimiter.

JOB FIVE — RE-DERIVE THE DIGESTS YOURSELF, AND CONFIRM THE STALENESS ACCOUNT
The builder reports both digests were stale since 1065c43 and that its own change moved neither,
proved by running both tools against both trees. Do not inherit that. Re-derive independently, and
confirm the corrected values are right rather than merely new.

Then answer one question for the record: **how many other recorded values in tools/ledger.json have
nothing that re-derives them?** Enumerate them. Do not fix any — this is a census, and it is the
evidence for Rule 12: *a fact recorded to avoid re-derivation must have exactly one thing that
re-derives it.* C1 (ledger vs capture, never capture vs reality), C3 (status token valid, never
status vs code) and the digests are three instances; your census tells us whether there are more.

REGRESSION
Retro-catch in full — 10/12/12, all three historical bugs, four MUST-CATCH sites.

RULE FOUR
Every assertion added or changed shown capable of failing against b09e7be. For string matches use a
normalised comparison — rule 4a: only a negative containment assertion can pass vacuously.

VERDICT
PASS only if the instability direction holds on every attack, the merged reason is true of both
occurrences, and your digest re-derivation is independent of the builder's.

Open your report with the plain-language summary for Cagan.
```

---

## CC-28 · 2g — the missing half ▶ LIVE

0g closed (`401f7ee`), step zero satisfied, runner green at 26 suites / 2,608 / 0 failed / 0 aborted.
The tester attacked instability six ways and it held; it confirmed the builder's *mechanism* claim
rather than its colour; and it re-derived the digests independently, **correcting the account** —
the recorded value was two revisions behind, not one.

**The Rule-12 census came back 11 of 22, not 3 of 3.** So the rule as I stated it is wrong for a
whole class and must be split:

- **Machine-derivable** (digests, `captured_at`/`captured_python`, status-vs-code, capture-vs-reality):
  Rule 12 applies as written — one re-deriver each, built as ONE check in CC-12, not patched
  separately.
- **Consumed but never validated** (`claim_quarantine_paths`, `count_quarantine_paths`): validate
  that each path still exists and is still needed. Cheap; CC-12.
- **Unfalsifiable by construction** — every `float_accumulations[*].reason`, brick names and notes,
  `uncalibrated_constants` descriptions, `meaning_bar`. **No checker can ever cover these**, and they
  are what the whole registry rests on. Rule 12 cannot apply; **Rule 9 already does** — a registry's
  reasons need a human adversary on every pass. What the census adds is that this is not a special
  case, it is *half the ledger*.

> **Rule 12, corrected:** a recorded fact must have either a re-deriver, or a named human obligation
> that re-reads it on a stated cadence. **A fact with neither should not be recorded as a fact.**

```
/psyche-orient

Work in the BUILDER lane. Brick 2g — asymmetric depression with its own rate, SPEC-2g Option C.
Step zero (0g) is closed. Follow the spec; do not re-design it. If the spec is ambiguous, or
finishing would force you to GUESS at a goal or a claim, stop and hand back.

THE INVARIANT TO WATCH HARDEST — D-7, ANTI-READBACK
Eligibility must stay SIGN-BLIND: byte-identical for a positive and a negative outcome of the same
magnitude. The trace records WHICH roads preceded an outcome; it must not encode WHAT the outcome
was. If eligibility becomes sign-dependent, the trace carries the answer and anything downstream
reading it is reading back what it was supposed to derive — this project's oldest failure mode
(1e), arriving inside the learner. Assert it directly and early, not as a corollary.

THE TRAP THIS BRICK SETS — a guarantee that outlives its purpose
2f-i's docstring claims POTENTIATION-ONLY, and that claim rests on a machine-checked absence bound
(`binding` on `get_road`), which exists to support "nothing in src/ can lower a road's strength".
**2g deliberately makes that false.** But the bound may well keep PASSING, because your weakening
will go through a sanctioned path rather than through a bound road reference.

So: a check that still goes green while the thing it was protecting is gone. That is
"right conclusion, wrong reason" inverted, and it is worse, because nothing turns red to tell you.
Handle it explicitly — re-scope the bound to what it now guards, or retire it with its reason
recorded. **Silently leaving a passing bound whose purpose has been deleted is the one outcome that
is not acceptable.** Say in your report which you did and why.

CONVERT, NEVER DELETE — the refusal becomes an acceptance
A negative `outcome_magnitude` is currently REFUSED, with an asserted-negative and a message
stating that no depression path exists. Both become false. Convert both: the assertion becomes the
positive case, and the message's claim is replaced rather than removed. The superseded text is
recorded as superseded, not deleted — a deleted claim leaves no trace that the limit ever existed.

THE OVERLAY, AND MEASURE THE NOISE FLOOR FIRST
Default-off, neutral value byte-identical, proven under attack **on a frozen clock**. Run two
identical off-calls and confirm they agree BEFORE concluding anything from an off-vs-on comparison —
a live clock manufactures differences and this project has filed a false defect that way.

THE CONSTANT
`depression_gain` is already on `uncalibrated_constants` with what would calibrate it, registered
before any code existed. Do not add a second constant. If the mechanism seems to need one, stop and
hand back — inventing a constant to make a shape work is a trap this project has already sprung.

STATE WHAT 2g DOES NOT MAKE TRUE, IN THE MODULE, NOT THE REPORT
- Butlin AE-1 moves from failing at TWO conjuncts to failing at ONE. The second — selecting outputs
  so as to pursue goals — still fails outright: the system selects no outputs and has no goals.
- Four of the five AOL criteria stay MECHANISM ABSENT regardless, for D-023's reason. AOL-5 is the
  sole exception and only under 2h.
- Cite D-023 rather than restating it, and check the REASON of every claim you leave, not just its
  conclusion. Four instances of right-conclusion-wrong-reason were found in 2f-i.

LANGUAGE — THIS IS THE MOST DANGEROUS BRICK YET FOR IT
0f is unfixed: C4 matches literal phrases and any interpolated word evades it. And with a signed
rule, "the system learns from consequences" stops being obviously false and becomes *almost* true —
which is exactly when an overclaim slips through review. A docstring may say the mechanism is
*inspired by* three-factor plasticity. It may not say the code learns, wants, remembers or
understands. You are the gate here.

LOOP-CLOSURE AND THE FLOAT RULE
Drive it with activations produced by the real pipeline, never values you chose: adverse outcomes
after multi-cycle traces, alternating signs, a negative with no preceding traversal, magnitudes at
the window edge. `math.fsum` for every float fold; every comparison resolves on an intrinsic integer
before it resolves on a float.

0d's EXAM AGAIN — report it either way
Did C6 catch an accumulation you would otherwise have shipped, or did it stay green while you wrote
new float arithmetic? Both answers are publishable; the second is more interesting. Do not omit it.

RUN
Full suite on every interpreter available, plus tools/test_ledger.py. Totals read from the runner
output, never estimated. Report both digests and whether each moved, and why. ledger_check exits 1
with exactly 16 [C2] under docs/paper/.

SELF-AUDIT
All seven items, plus: for every claim you leave in a docstring, is the REASON checked or only the
conclusion?

Open your report with the plain-language summary for Cagan.
```

---

## Ad-hoc prompts worth keeping

**Before any commit:**
```
/psyche-claim-check
Review the staged diff and the commit message I am about to use. Verdict SHIP or HOLD, with
exact replacement text for anything that needs changing.
```

**When something breaks:**
```
/psyche-orient
Work in the tester lane. This is failing:

<paste the output>

Reproduce it first — I want the exact failing input before any hypothesis. Then diagnose.
Do NOT fix it: report it precisely and hand back. Check the interpreter axis specifically;
BUG-0b1 was invisible on 3.12 and reproducible on 3.11.
```

**Weekly, to catch drift:**
```
/psyche-orient
/psyche-ledger check

Then: read the last two weeks of git log and tell me, honestly, (a) what actually moved,
(b) what I said I would do and did not, (c) anything in the repository that is now
inconsistent with anything else. Be blunt. Do not be encouraging.
```
