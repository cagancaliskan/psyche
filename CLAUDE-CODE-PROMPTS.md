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

## CC-9 · Fix the yardstick before the code ▶ LIVE

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
