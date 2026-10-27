# Contributing to Psyche

The project's rules, and the shared ground truth for everyone who works on this repository.
Read it first. Where a proposed change conflicts with a rule below, raise the conflict in the
pull request or in a GitHub Discussion rather than resolving it silently.

Current counts, statuses and program state live in `tools/ledger.json`; this file does not
repeat them.

---

## What this repository is (D-031, D-033)

Psyche is one open research project that builds brain-inspired components in stages, with
artificial general intelligence (AGI) as its long-term aim. Each stage is built test-first and
kept as a citable artifact.

- **Stage 1, the substrate** (`src/`, `tests/`, `experiments/`, `docs/PSYCHE.md`): a
  memory-and-activation substrate, the project's foundation. **Paused** since 2026-10-23.
- **Stage 2, spiking cognitive maps** (`docs/research/`, `tools/research_plan.json`, `cogmap/`):
  *Cognitive Map Formation and Energy Efficiency in Spiking Neural Networks with Local
  Plasticity* (short name SCM). It is framed as a test. It asks whether a spiking network that
  learns only through local synaptic plasticity shows, on classic cognitive-map tests, the
  behaviours that an internal map would explain and memorised responses would not; whether other
  families of agents, given the same experience, show them too; and what the behaviour costs, as
  an analytic estimate of synaptic operations. The plan does not depend on a positive answer.
  **Active.**
- **Later stages** build toward the long-term aim on the same discipline; they are not specified
  publicly yet.

**AGI is the project's long-term aim (D-033).** Name it freely, as an aim. Never write that
Psyche or any current component is or achieves AGI.

**Program state** is a third axis, orthogonal to the build axis (`bricks[*].status`) and the
meaning axis (`meaning_bar`). Read it from `program` in `tools/ledger.json`: it says which line
is being worked on, never what is true of a brick. No brick status, meaning verdict or test
figure changes because of the pause. Only the project lead changes `program`, and only with a
new entry in `DECISIONS.md`. While the substrate is paused, no new substrate brick starts and no substrate
default changes; the suites, the ledger, `ledger_check` and the determinism sweep stay
maintained, and the paper stays held (D-012).

The substrate's own aim is paused, not abandoned and not achieved. It is stated only as an aim,
never as a property of the system: *a biologically grounded, non-LLM memory-and-activation
substrate that moves information without loss and sets how much activation it spends without
producing output its inputs do not support*.

**Public summary, private detail.** This repository holds the cognitive-map line's overview,
roadmap, gates, battery overview, claims discipline, engineering standards and visuals.
Hypotheses beyond the research questions, pre-registered criteria and thresholds, the experiment
plan, the spiking model and its code, the analysis of related work, results and working records,
and the paper draft live in a private companion repository that is never named here. Material
moves here only under [`docs/research/disclosure-policy.md`](docs/research/disclosure-policy.md).
When unsure whether something is private, it is.

**Everything in this repository is English.**

---

## What Psyche is

Public text describes the project this way.

Psyche is an open research project that builds brain-inspired components in stages, with AGI as
its long-term aim. Its first stage, the substrate, is a biologically-motivated, dependency-free
Python prototype of a **memory-and-activation substrate for a cognitive architecture**; its aim is
stated above and is paused. Its second stage, spiking cognitive maps, is active. The current built
artifact is a verified substrate plus an honest, well-tested exploration of higher layers.

**What is verified** is that the substrate's lower layers are *correct and deterministic*:
verified by the full adversarial suite on every interpreter; not a formal proof. **What is not
claimed** is that any layer *reproduces a cognitive phenomenon*, constitutes a mind, or is AGI.
These are different claims and the line between them is sacred.

The project is **Psyche** everywhere: the paper, the codebase, and the repository.

---

## Where the facts live

| Fact | Source of truth |
|---|---|
| Test counts, statuses, constants, results | `tools/ledger.json` — **only** |
| Program state (which line is paused, which is active) | `tools/ledger.json` → `program` |
| Captured run | `docs/TEST_OUTPUT.txt` (the ledger is generated from it) |
| The substrate's narrative position, phases | `docs/psyche_roadmap.md` |
| Research plan: phases, gates, dates, deadlines | `tools/research_plan.json` — **only** |
| Research public docs | `docs/research/` |
| Spiking model package (exported releases only) | `cogmap/` |
| Why something changed | `DECISIONS.md` |
| Specs / ADRs | `docs/specs/` |
| Pre-registrations and results | `docs/experiments/` |
| Aspirational vision, **not built** | `docs/design/` |

**Never recompute a count from a document.** Five documents once disagreed about the
assertion total; that is why `tools/ledger_check.py` exists and why it runs in CI.

---

## The ten non-negotiable rules

These are the disciplines the project has already paid for in bugs.

1. **Never overclaim.** Psyche, or any of its components, is never called "a mind,"
   "conscious," "sentient," or "a validated cognitive model," and no text says that it is or
   achieves AGI — not in code, comments, docstrings, docs, or commit messages. AGI may be named
   as the project's long-term aim (D-033). Biological *inspiration* may be described; biological
   *fidelity* or cognitive achievement may not be asserted.

   **The cognitive-map line adds its own terms.** The spiking model is never described in
   terms of consciousness, understanding or thinking; results describe behaviour and internal
   structure. It is "brain-inspired" or, where it can be argued, "biologically plausible",
   never "the brain does it this way". Energy appears only as an analytic estimate or lower
   bound, reported with its sensitivity analysis: never GPU wall-clock time or watts as
   evidence, and never a general claim that spiking networks are more efficient. No priority claim
   ("first", "the first to") before release: a decided gate lifts none of the claim terms
   (D-034). Every number traces to a captured results file.

2. **Mechanism ≠ meaning.** "The code is correct and deterministic" and "the code reproduces
   a cognitive effect" are separate claims with separate evidence bars. Mechanism is
   verified by the tester; meaning by the validator, against external data.

3. **`PROVEN` and `DESIGNED` stay in separate boxes.** `PROVEN` is the ledger's internal status
   name; its plain meaning is "verified by the full adversarial suite on every interpreter; not a
   formal proof", and public prose says "verified" (D-035). Vision documents are *description,
   not specification*. Nothing is built until it is tested. Track build status and meaning
   verdict as **two orthogonal axes** — a brick is routinely `BUILT-UNVALIDATED` with a
   `NOT-YET` verdict at the same time.

4. **Loop-closure: every brick proves itself before the next snaps on.** A component that
   passes on a friendly, hand-chosen input has not passed — it is waiting to fail under
   load. Drive each stage with input *generated by the previous stage*.

5. **External yardsticks, never self-authored inputs.** Any test that quietly encodes its own
   answer is invalid. Relatedness norms, baselines, ground-truth directions: all from outside
   the project.

   For the cognitive-map line, the behavioural paradigms are published and the published
   behaviour of the baselines is the reference. The agent-side operationalisation of each
   paradigm and its pass criteria are the project's own and are pre-registered privately. Each
   baseline is reproduced against its published behaviour before any comparison is made, and
   development and test environments stay strictly split.

6. **Reinvent the idea, borrow the scaffolding.** The novelty is the architecture. Spend
   invention only where the genuinely new thing lives.

7. **The substrate bar is determinism + integrity + purity** — and determinism is checked on
   **two axes**: randomized `PYTHONHASHSEED` *and* every CPython minor version available. A
   property that holds on one interpreter and fails on another was never a property of the
   program. (BUG-0b1: a 1-ULP float-summation leak was invisible on 3.12 and flipped the
   workspace winner 8 times in 30 on 3.11, at a fixed hash seed.)

   The cognitive-map line states determinism in three tiers, and each result states its tier;
   a result built from parts at different tiers states the weakest of them.
   - **Tier A:** bit-exact across CPython versions and hash seeds (environments, battery,
     metrics, counters).
   - **Tier B:** bit-exact on CPU for one pinned version, with deterministic algorithms
     enabled.
   - **Tier C:** statistical reproducibility for GPU runs: fixed seeds, results reported with
     confidence intervals over seeds.

8. **The substrate core stays dependency-free.** `src/psyche_*.py` and `tools/` use the
   standard library only, unless a dependency is explicitly justified and approved by the
   project lead. The spiking model's package under `cogmap/` declares its own pinned
   dependencies and is never imported by the core; nothing under `cogmap/` is registered in
   `run_tests.py`.

9. **Every phase ends in something shippable.** If the road stops at any point, what is
   behind us must stand on its own as a real, citable artifact.

10. **Prefer the gated overlay.** A change to existing behaviour ships as a **default-off
    parameter whose neutral value is byte-identical** to current behaviour — as
    `broadcast=False`, `body_sensor=None` and `normalization_sigma=None` all do. Flipping a
    default is a separate brick with its own gate and its own re-validation cost.

---

## The float rule

Never compare two independently-accumulated floats for strict inequality where an integer
key could decide. Sum with `math.fsum` (exactly rounded, therefore order-independent), and
make every comparison resolve on an intrinsic integer **before** it resolves on a float. A
tie-break that a 1-ULP asymmetry pre-empts is not a tie-break.

---

## The project lead decides

The project lead, Cagan Caliskan, sets direction and makes the calls; contributors propose. When
a decision shapes the project's direction — a constant, a default, anything carrying a
re-validation cost — the proposal sets out the options, their tradeoffs and a recommendation, and
the project lead decides. If a claim or a goal is unclear, ask in a GitHub Discussion before
writing it into the repository.

---

## Roles

Work moves through four roles: architect-pm, builder, tester and validator. Lanes do not
cross; the separation **is** the evidence. A brick moves through them in order: the
architect-pm writes the spec; the builder implements it test-first; the tester attacks it;
the validator, when a cognitive claim is involved, runs the pre-registered experiment; the
architect-pm then folds the result into the roadmap and the ledger.

- **architect-pm** turns direction into a sequenced spec with an external "done means",
  keeps the roadmap and ledger current, and proposes approaches grounded in prior art. Spec
  and roadmap work changes documents only, never production code or tests.
- **builder** implements the spec test-first, self-audits against the six-bug checklist
  (below), and submits a change only when the whole suite passes on every interpreter and
  nothing is overclaimed. Builder changes stay in `src/` and the builder suites
  (`tests/test_psyche_*.py`).
- **tester** verifies independently and adversarially; tester suites are hostile and
  loop-closed and are written separately from the code they attack. The tester verifies
  mechanism, not meaning, and never modifies production code.
- **validator** pre-registers and runs a falsifiable experiment against external data for any
  cognitive-sounding claim. The validator verifies meaning, not mechanism, and never patches
  the module under test.

**While the substrate is paused (D-031)**, no new substrate brick starts and no substrate
default changes. Check `program` in `tools/ledger.json` before any brick work. Each new path has
a responsible role (D-031, item 10):

- changes to `README.md`, `MOC.md`, `docs/PSYCHE.md`, `docs/research/**`, `docs/publish.json`
  and `tools/research_plan.json` are architect-pm work;
- changes to `tools/publish/**`, `website/**` and `.github/**` are builder work.
- **`cogmap/` is export-only.** Nobody edits it by hand. It changes only through a release export
  that the project lead runs, under `docs/research/disclosure-policy.md`.

### The six-bug checklist

The builder's self-audit, run on every change. Each item is a real bug the project has been
bitten by; the seventh was added by D-020 and the record keeps the original name.

- **Purity:** does any read mutate stored state? Snapshot before and after.
- **Convergence double-counting:** where paths or activations converge, is anything counted
  twice?
- **Cross-process determinism:** fresh interpreters, randomized `PYTHONHASHSEED`, and every
  CPython minor version available. One interpreter is not determinism.
- **Structurally-impossible branches:** can a grouping step only ever produce one group? Can a
  branch never fire? Show that the structure can do what it claims.
- **Circular tests:** does any test encode the answer into its own input?
- **Integrity:** after a battery of mutations, are all graph indices mutually consistent?
- **Builder-side evidence (D-020):** does a builder-side assertion exist for the new arithmetic,
  or does all evidence for it live in tester files?

---

## The three walls (why the meaning bar is still open)

Three attempts, three structurally distinct obstacles, all caught **before** any graded
number existed:

- **1e semantic priming — CIRCULAR.** SWOW strength *was* the edge weight, so a weight-tied
  pair was activation-tied by construction.
- **1e′ fan effect — MECHANISM ABSENT.** The engine gave every out-road the source's full
  activation, so the fan curve was flat to the last digit.
- **2c interoception — SIGNAL FLAT.** Friction ≈ 0 on realistic CPU-bound work; any gradable
  band would have to be manufactured.

**The pattern is the finding**, and it is the anti-circularity discipline working — not
project failure. Scope it: this is a finding about *this substrate and these three
yardsticks*, never a general law about spreading activation or cognition.

---

## Repo conventions

- Modules `src/psyche_<name>.py`; builder suites `tests/test_psyche_<name>.py`; tester suites
  `tests/test_tester_<brick>_*.py`.
- One runner: `run_tests.py`. Its captured output in `docs/TEST_OUTPUT.txt` is the ground
  truth for all counts. Never estimate; read them from the ledger.
- Commits: `feat(<brick>):` · `fix(<brick>):` · `test(<brick>):` · `docs(<area>):` ·
  `chore:`. Branch per brick: `brick/<id>`. Research-line and program work uses
  `docs(research):` · `chore(program):` · `chore(release):` · `chore(publish):`.
- Public commits never carry private ids. No identifier or wording from the private companion
  appears in a commit message, a branch name or a file name here.
- Research-plan dates are never typed by hand. Render the plan with
  `python3 tools/publish/render_plan.py --write`, which fills the generated blocks from
  `tools/research_plan.json`.
- Stage files by explicit path only; never `git add -A` or `commit -a`, so that a commit holds
  exactly the files the change meant to touch.
- Before any commit, the commit gate: `python3 tools/ledger_check.py --only C1,C3,C4,C5,C6`
  exits 0, `python3 tools/publish/ci_c2.py` exits 0 and `python3 tools/publish/check_copy.py`
  exits 0, and the change has been read against rule 1 and the disclosure policy. The paper
  draft is held (D-012) and kept outside this repository.
- **Never `git stash`. Inspect an old revision with `git show <rev>:<path>` or a temporary
  worktree.** A stash is **repo-wide**: it sets aside every uncommitted change in the working
  tree, not only the one being worked on, and one that is never popped loses that work. A stash
  once set aside 315 lines of unrelated uncommitted work at `a444ae6`; it was recovered by
  diffing every stashed path against `HEAD` and disk.

---

## Definition of done

**A code module is done** when: it passes its full suite on every available interpreter; it
is deterministic across processes and versions, integrity-preserving, and pure; it has been
hit with adversarial and loop-closed inputs; no test encodes its own answer; and its verification
notes honestly state what is verified, what is not claimed, and any known limitation —
written as an explicit asserted-negative test, not hidden.

**A cognitive claim is done** when: it is reproduced on external data the project did not
author, with the prediction and its direction fixed in advance, against a baseline — or the
negative result is reported honestly. A pre-registered NO-GO caught before a graded run is a
first-class result.

---

## Tone

Honest, precise, willing to report what broke. A result that says "this passes, and here is
exactly where it would not" is worth more than a confident one. No marketing language and no
exclamation marks in documents, commit messages or notes.
