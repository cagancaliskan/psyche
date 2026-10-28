# Reader's guide

Start here if Psyche is new to you. This page says what the project is and why it works in
stages, where those stages stand, what is not known yet, how to cite the work and how to get in
touch. It ends with [routes for four kinds of reader](#where-to-go-next).

## What Psyche is, and why

Psyche is an open research project that builds brain-inspired components in stages, with
artificial general intelligence (AGI) as its long-term aim. Each stage is built test-first and
kept as a citable artifact, so that if the work stopped at any point, what was behind it would
stand on its own.

AGI is named as an aim and only as an aim. Nothing built so far is general intelligence, and no
page of this site says that it is. [Why the aim is named at all](faq.md#why-is-agi-named-as-an-aim)
is answered in the questions.

The work is staged because of what the first stage taught. The substrate tried three times to
earn a first cognitive claim, and each attempt stopped before any graded number existed, each for
a structurally different reason: one was circular, one had the mechanism absent, and in one the
signal stayed flat. The substrate's layers were verified as mechanism each time; what was missing
was an external yardstick that the mechanism could both produce and be graded against. This is a
finding about this substrate and these three yardsticks, not a general law. Stage 2 is built
around that lesson: classic behavioural tests whose paradigms are published, baselines checked
against the behaviour their own papers report, and criteria written before the runs they judge.
The story is told in [Origins](research/origins.md), and the three stops are set out in
[The three walls](three-walls.md).

## The stages

| Stage | What it is |
|---|---|
| 1. The substrate | A dependency-free Python memory-and-activation substrate, the project's foundation. Its lower layers are verified correct and deterministic. No cognitive claim is made for it. Its state is on the [substrate status page](https://cagancaliskan.github.io/psyche/status/) and its record is in [The substrate](PSYCHE.md). |
| 2. Spiking cognitive maps | A test of whether a spiking network that learns only through local synaptic plasticity shows, on classic cognitive-map tests, the behaviours that an internal map would explain and memorised responses would not. Its plan is in the [overview](research/README.md) and on the [timeline](https://cagancaliskan.github.io/psyche/roadmap/). |
| Later stages | They build toward the long-term aim on the same discipline. They are not specified publicly yet. |

The state of each stage is read from the project's ledger and plan and is not typed on this page.
For stage 2, the plan says:

<!-- generated:status-line:start -->
**Now:** P0 Novelty review and setup (2026-10-23 to 2026-11-15) · **Next gate:** A Novelty, 2026-11-15
<!-- generated:status-line:end -->

When a phase starts or ends, a gate is decided, a date moves or a commitment is made, the
[Progress](progress.md) page records it.

## What is not known yet

No stage 2 results are reported yet. The pages about stage 2 describe a plan and put questions,
not answers, and any number reported later will come from a captured results file.

The plan does not depend on a positive answer. Its safe base, which is the environments, the test
battery, the baseline comparisons, the analysis and the report, stands on its own. If the spiking
model falls short, a documented account of where and why is kept as a result. A decided gate shows
only the date it was decided and what comes next, never why
([Decision gates](research/gates.md)).

So nothing here presents a stage 2 finding. The substrate does have a public record, and it is
scoped to the substrate: [The substrate](PSYCHE.md).

## How to cite

The preferred citation is the archived report of stage 1:

> Caliskan, C. (2026). *Nous: Adversarial Testing of a Dependency-Free Memory-and-Activation
> Substrate for Cognitive Architectures.* Zenodo. <https://doi.org/10.5281/zenodo.20474613>

The archived title uses the project's earlier name; the project is Psyche
([D-030](../DECISIONS.md) retired the earlier name). The report is open access under CC BY 4.0
and the code is MIT-licensed ([LICENSE](../LICENSE)).

The same citation is in [`CITATION.cff`](../CITATION.cff) at the root of the repository. GitHub
reads that file and offers it through the "Cite this repository" link on the repository's page.

## Get in touch

- **Questions, ideas and comments on a page:**
  [GitHub Discussions](https://github.com/cagancaliskan/psyche/discussions).
- **A wrong claim, a stale number, a broken link:** a bug report through the
  [issue form](https://github.com/cagancaliskan/psyche/issues/new/choose).
- **A security problem:** report it privately, as the [security policy](../SECURITY.md) describes,
  and not in a public issue or discussion.
- **A change to the repository:** read
  [Taking part from outside the project](../CONTRIBUTING.md#taking-part-from-outside-the-project)
  first. It says where each thing goes, how to set up and what a pull request must pass.

## Where to go next

### If you are a researcher

- [Overview of stage 2](research/README.md): the question, the aim, the research questions and
  what the line does not claim.
- [Test battery](research/test-battery.md): the classic paradigms, the environment families and
  the rules that keep every agent on the same footing.
- [Roadmap](research/roadmap.md): the phases, the layers and the paper deadline.
- [Engineering standards](research/engineering.md): how code is written, how determinism is
  stated and how the statistics are done.
- [Glossary](research/glossary.md) and [Reading list](research/reading-list.md): the terms, and
  the classic works behind the question.

### If you are a reviewer

- [Claims and scope](research/claims-and-scope.md): what the line may and may not say about its
  model.
- [Disclosure policy](research/disclosure-policy.md): what is public, what is withheld and when
  material is released.
- [Decision gates](research/gates.md): the question each gate asks, its fallback and its public
  status.
- [The three walls](three-walls.md): the substrate's three negative results.
- [Methodology](METHODOLOGY.md): how adversarial testing caught structural bugs in the
  substrate.
- [The ledger](../tools/ledger.json): the one file that every count and status in the
  documents comes from.
- [Project rules](../CONTRIBUTING.md): the ten rules the work follows, including the claims
  discipline.

### If you want to support the work

- [How Psyche is run](governance.md): who decides, how decisions are recorded and what stays
  usable if the work stops.
- [Funding](governance.md#funding): where the project stands and how to get in touch.
- [GitHub Discussions](https://github.com/cagancaliskan/psyche/discussions): the place to ask or
  to offer.

### If you are visiting

- [Home](https://cagancaliskan.github.io/psyche/): the project on one page.
- [Explore the timeline](https://cagancaliskan.github.io/psyche/roadmap/): the phases and gates of
  stage 2 on one timeline.
- [Step through the paradigms](https://cagancaliskan.github.io/psyche/battery/): the classic tests
  behind the battery, one step at a time.
- [Questions and answers](faq.md): short answers to what newcomers ask first.
