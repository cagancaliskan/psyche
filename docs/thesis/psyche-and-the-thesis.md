# Psyche and the thesis

> Public summary. Detail is withheld until submission under the [disclosure policy](disclosure-policy.md).

This page states how the thesis relates to Psyche, the project this repository was built for.
The short version: the thesis reuses how Psyche was built and checked, and some of its tooling;
the thesis model is a separate codebase and shares no code with Psyche's core.

## What Psyche is

Psyche is a dependency-free Python memory-and-activation substrate for a cognitive
architecture, built test-driven on the standard library alone and verified by an independent
adversarial tester. What it proves is mechanism: its lower layers are correct and
deterministic, reproducibly. It makes no cognitive claim, and its three attempts at a behavioural claim were
each stopped before any graded number existed. Psyche is paused under D-031 in
[DECISIONS.md](../../DECISIONS.md): no new brick starts and no default changes, while the
suites, the ledger, its checker and the determinism sweep stay maintained. The pause changes no
brick status, meaning verdict or test figure; at the pause the record stands at 26 suites and
2,645 assertions with no failures. The full account is in [PSYCHE.md](../PSYCHE.md).

## The paused aim

Psyche's long-term aim is recorded in [`tools/ledger.json`](../../tools/ledger.json) as an aim,
never as a property of the system:

> a biologically grounded, non-LLM memory-and-activation substrate that moves information without loss and sets how much activation it spends without producing output its inputs do not support

The aim is paused, not abandoned and not achieved. Nothing in this repository claims that Psyche
meets it. The thesis does not inherit it; it has its own research questions, set out in the
[overview](README.md).

## What the thesis reuses

Methodology and tooling only. Five practices carry over.

| Practice | In Psyche | In the thesis |
|---|---|---|
| One ledger with a checker | Every quoted count and status lives in one file, beside the recorded determinism scope, and a checker fails when a document's count or status disagrees with it | The public plan lives in one file, and pages render from it |
| Pre-registration | Prediction, direction and yardstick fixed before any graded run | Criteria frozen before the work they judge, committed publicly as hashes |
| Determinism discipline | Bit-exact across interpreters and hash seeds | Three tiers, and each result states its tier |
| Adversarial tester lane | Independent hostile tests; no edits to production code | Adopted as a rule: checks written separately from the code they attack |
| Decision records | Dated entries with options, evidence and cost | A comparable form: dated, with context, options considered, the decision and its cost |

### One ledger, one checker

In Psyche, a number that a document quotes is never typed from memory. Test counts are captured
by a tool from the canonical runner and written into [`tools/ledger.json`](../../tools/ledger.json).
[`tools/ledger_check.py`](../../tools/ledger_check.py) then fails when a document disagrees with
the ledger, uses a status word the ledger does not hold, or uses a term the claim rules forbid.

The thesis keeps that shape. Its public phases, gates, dates and deadlines live only in
[`tools/thesis_plan.json`](../../tools/thesis_plan.json), which is validated against a key
allowlist so that no criterion or threshold field can exist in it. The [roadmap](roadmap.md) and
[gates](gates.md) pages render their tables and diagrams from that file rather than typing dates.
The thesis claim rules are held in the ledger as a term list beside Psyche's, and the publishing
checks apply them to every public thesis surface. A number the thesis reports must trace to a
released result file.

### Pre-registration before any graded run

In Psyche, a cognitive-sounding claim is tested only against external data the project did not
author, with the prediction, its direction and the baseline fixed before the run. Three attempts
were stopped this way, each for a structurally distinct reason. The thesis uses these three
walls as a checklist of generic failure modes to rule out before a graded run, not as findings
about its own model.

| Wall in Psyche | What happened | Generic failure mode the thesis rules out |
|---|---|---|
| Circular | The external norm was the same quantity as an edge weight, so agreement held by construction | A test whose answer is already encoded in the environment, the input or the comparison |
| Mechanism absent | The system lacked the mechanism the effect depends on (no division of activation across out-roads), so the fan response was flat by construction and there was nothing to grade | A test whose outcome is decided by a property the system lacks by design, rather than by what it learned |
| Signal flat | The signal under test barely moved on realistic work, so any graded band would have had to be manufactured | A measure that does not separate the reference bounds, such as a random agent and an oracle, so nothing can be graded on it |

The walls are a finding about Psyche's substrate and those three yardsticks, never a general law.
What carries over is the habit of checking for them before any graded run.

In the thesis, criteria are written before the work they judge and are not changed afterwards. A
justified exception needs a recorded decision with its reason, and the result is then reported
under both the original and the changed criterion. When a pre-registration is frozen, a salted SHA-256 hash of
it is added to the commitments list in the plan: the date is public at once, and the content is
published at submission so that anyone can check it against the hash. A stop caught by
pre-registration before a graded run is kept as a result, as it was in Psyche.

### The determinism discipline

Psyche checks determinism on two axes at once: randomised hash seeds, and every CPython minor
version available. The ledger records the sweep (five minor versions under six hash seeds), and
the claim is scoped to what was swept. The rule was paid for: a one-ULP difference in a float sum
was invisible on one interpreter and changed a result on another
([BUG-0b1](../BUG-0b1-coalition-strength-determinism.md)). Four habits follow. The thesis keeps
all of them wherever a result claims Tier A, and states a weaker tier where it cannot:

- **Bit-exact comparison.** Checks compare results bit for bit, not after rounding. A rounded
  comparison once hid a one-ULP disagreement in Psyche.
- **Remove order dependence rather than sweep for it.** Where iteration order can differ between
  processes for reasons a seed does not control, a seed sweep cannot establish determinism. The
  order dependence is removed instead.
- **Integer tie-breaks.** Every comparison resolves on an intrinsic integer key before it
  resolves on a float. A tie-break that a one-ULP asymmetry can pre-empt is not a tie-break.
- **Exactly-rounded sums.** Floats are summed with `math.fsum`, which is exactly rounded and
  therefore independent of order.

Not every thesis run can be bit-exact across interpreters, so the thesis states the guarantee
each result carries:

| Tier | Guarantee |
|---|---|
| A | Bit-exact across interpreters and hash seeds. Covers the environments, the battery, the metrics and the operation counters. This is the Psyche standard, unchanged. |
| B | Bit-exact on CPU for one pinned library version, with deterministic algorithms. |
| C | Statistical reproducibility: fixed seeds, with results reported as confidence intervals. Covers GPU runs. |

Each reported result states its tier. The [engineering standards](engineering.md) give the detail.

### An independent adversarial tester lane

In Psyche, the tester writes its own hostile and loop-closed tests against code it did not write.
Loop-closed means each stage is driven with input produced by the stage before it, not with
friendly hand-chosen input. The tester verifies mechanism, not meaning, and does not modify
production code; a hook enforces that boundary. The separation is the evidence: a check written
by the author of the code shares the author's blind spots, and in Psyche the independent passes
found defects that the builder's own suites had passed over. A suite's passing count is a count;
the tester's verdict is the verdict.

The thesis adopts the same rule: checks on its code are written separately from the code they
attack, and a green run is read as a count, not as a verdict.

### Decision records

Psyche records every decision that shapes its direction in [DECISIONS.md](../../DECISIONS.md):
a dated entry recording who decided, what it supersedes, the context, the options, the decision,
the evidence and the cost. Entries are appended, not rewritten; a later decision supersedes an
earlier one by a new entry. D-031, which pauses Psyche and restructures this repository around
the thesis, is one such entry.

The thesis keeps decision records in a comparable form. Those that change this repository appear
here: a change of program state or a lifted thesis claim term needs an entry in DECISIONS.md,
and a moved public date needs an entry in the plan's change log. The thesis's other decision
records stay in the private companion and are not released (see the
[disclosure policy](disclosure-policy.md)).

## What the thesis does not reuse

- **No model code.** The thesis model is a separate codebase. It shares no model code with
  Psyche's core.
- **No ancestry.** Psyche's components are not parts of the thesis model, and they are not
  presented as its ancestors or as earlier versions of it.
- **No evidence.** Psyche's results, including its test record and its three walls, are evidence
  about Psyche only. They say nothing for or against the thesis model.
- **Separate packages.** `src/` stays standard library only and never imports `thesis/`. When
  the earliest group is released, the thesis package will bring its own project file with
  pinned dependencies. Nothing under it is registered in `run_tests.py`, and it is filled only
  by export of released versions.
- **No aim.** The thesis does not take over Psyche's paused aim.

## How the pieces fit

Psyche, paused, contributes methods and tools. The thesis keeps its public summary in this
repository and its detail in a private companion. Material moves from the companion to this
repository only as older, complete, working releases, under the
[disclosure policy](disclosure-policy.md).

```mermaid
flowchart LR
  psyche["Psyche, paused"]
  reuse["Reused methodology<br/>and tooling"]
  thesis["Thesis"]
  summary["Public summary<br/>in this repository"]
  companion["Private companion"]
  releases["Older, complete releases<br/>exported to thesis/"]

  psyche --> reuse --> thesis
  thesis --> summary
  summary <--> companion
  companion --> releases

  classDef paused fill:#5f6b7a,stroke:#414a55,color:#ffffff
  classDef method fill:#3f6f94,stroke:#2b4f6b,color:#ffffff
  classDef work fill:#4f7a3f,stroke:#365429,color:#ffffff
  classDef private fill:#6b4f86,stroke:#4a365d,color:#ffffff
  classDef release fill:#8a5a2b,stroke:#5f3d1c,color:#ffffff
  class psyche paused
  class reuse method
  class thesis,summary work
  class companion private
  class releases release
```

## Further reading

- [PSYCHE.md](../PSYCHE.md): what Psyche built and what it showed.
- [METHODOLOGY.md](../METHODOLOGY.md): the development history, and the defects adversarial
  testing found.
- [Claims and scope](claims-and-scope.md): the wording rules for the thesis.
- [Engineering standards](engineering.md): determinism tiers, statistics and figures.
- [Disclosure policy](disclosure-policy.md): what is public now, and how releases are made.
