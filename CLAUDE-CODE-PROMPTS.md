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
