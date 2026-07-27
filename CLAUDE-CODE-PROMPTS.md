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

## CC-18 · Fix 0e now — I am overriding my own schedule ▶ LIVE

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
