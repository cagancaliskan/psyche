# How Psyche is run

Psyche is run by its project lead. This page says who decides, how the work is kept honest, how
decisions are recorded, what stays usable if the work stops, where funding stands, and what the
project does about the questions that its long-term aim raises.

## Who runs it

Cagan Caliskan is the project lead. The project lead sets direction and makes the calls;
contributors propose. When a decision shapes the project's direction, such as a constant, a
default or anything that carries a re-validation cost, the proposal sets out the options, their
tradeoffs and a recommendation, and the project lead decides. The project has one maintainer, who
is the project lead ([security policy](../SECURITY.md)).

Some decisions are reserved. Only the project lead changes the program state in the ledger, which
says which line of work is active and which is paused, and only with a new entry in the decision
record. The `cogmap/` folder is changed only by a release export that the project lead runs, under
the [disclosure policy](research/disclosure-policy.md).

If a claim or a goal is unclear, the place to ask is
[GitHub Discussions](https://github.com/cagancaliskan/psyche/discussions), before it is written
into the repository.

## The four roles

Work moves through four roles, each with a lane of its own.

- **architect-pm.** Turns direction into a sequenced spec with an external definition of done,
  keeps the roadmap and ledger current, and proposes approaches grounded in prior art. Never
  changes production code or tests; spec and roadmap work changes documents only.
- **builder.** Implements the spec test-first, audits the change against a checklist of past
  bugs, and submits it only when the whole suite passes on every interpreter and nothing is
  overclaimed. Never changes files outside its own paths: the substrate's code and builder
  suites, the publishing tools, the site and the workflows.
- **tester.** Verifies independently and adversarially, with hostile suites written separately
  from the code they attack. Never modifies production code or judges meaning; the tester
  verifies mechanism.
- **validator.** Pre-registers and runs a falsifiable experiment against external data for any
  cognitive-sounding claim. Never patches the module under test or judges mechanism; the
  validator verifies meaning.

A unit of work, called a brick in the substrate's record, moves through the roles in order: the
architect-pm writes the spec, the builder implements it, the tester attacks it, the validator runs
the pre-registered experiment when a cognitive claim is involved, and the architect-pm folds the
result into the roadmap and the ledger.

The lanes stay apart because a check written by the author of the code shares the author's blind
spots. In the substrate, the independent adversarial passes found defects that the builder's own
suites had passed over ([Origins](research/origins.md)). The roles name kinds of work, not separate
people: the project has one maintainer. What the separation fixes is where each kind of change may
be made, and that a test suite is written apart from the code it attacks. The documents and the
plan are architect-pm work, and the publishing tools, the site and the workflows are builder work;
the [project rules](../CONTRIBUTING.md) give the full list.

## How decisions are recorded

Three records each have one job.

- **The decision record.** Every decision that shapes the project's direction is a dated entry in
  [DECISIONS.md](../DECISIONS.md): who decided, what it supersedes, the context, the options, the
  decision, the evidence and the cost. Entries are appended and never rewritten. A later decision
  supersedes an earlier one by a new entry.
- **The ledger.** [`tools/ledger.json`](../tools/ledger.json) is the only source of the
  substrate's counts, statuses and program state. A checker fails when a document disagrees with
  it, and the repository's checks run on every pull request and every push to the main branch.
- **The plan.** [`tools/research_plan.json`](../tools/research_plan.json) is the only source of
  the phases, gates and dates of stage 2. Pages render from it, so no date is typed by hand. A
  gate keeps its originally planned date, and a date that moves needs a change-log entry that
  gives the reason. Criteria are fixed before the work they judge and are committed as hashes, so
  the day they were fixed can be checked.

The [Progress](progress.md) page shows the public record of the plan as it changes.

## If the work stops

Every phase ends in something shippable. If the road stops at any point, what is behind it must
stand on its own as a real, citable artifact. Today that means:

- **The archived report of stage 1**, with its DOI and open access under CC BY 4.0. How to cite
  it is in the [Reader's guide](guide.md#how-to-cite).
- **The code under the MIT licence**, in this repository. The substrate's suites run on the Python
  standard library alone, so anyone can run them without installing anything, and the licence lets
  anyone keep using and building on the code.
- **The public plan and record**: the research plan with its change log, the decision record, the
  ledger and the documents of this site, all in the repository's history. The site is built from
  files in the repository, so the record does not depend on the site.
- **Stage 2's safe base**, which is planned to stand without the spiking model. If the model falls
  short, a documented account of where and why is kept as a result, and a decided gate that stops
  the line says so as a date and a next step ([Decision gates](research/gates.md)).

A line of work can be paused without being abandoned. Which line is active is the program state in
the ledger, shown on the
[substrate status page](https://cagancaliskan.github.io/psyche/status/). While the substrate is
paused, no new brick starts and no default changes, and its suites, ledger, checker and
determinism sweep stay maintained. Resuming it takes a new entry in the decision record from the
project lead.

This list covers what is public today. Material held back under the disclosure policy is not part
of it until it is released.

## Funding

Psyche has no external funding yet. Its project lead is searching for funding, and a person willing
to donate to the work can get in touch through
[GitHub Discussions](https://github.com/cagancaliskan/psyche/discussions).

## Ethics and safety

Psyche's long-term aim is AGI. An aim like that raises questions about safety and about what a
project owes its readers. This note does not claim to answer them. It lists what the project does
now, so that each point can be checked against the pages and the repository, and it leaves out
what cannot be checked.

### What the project does now

- **Simulated agents on published paradigms.** Stage 2 is designed to run agents only in seeded,
  deterministic simulated environments, with tests adapted from classic animal-learning
  experiments ([Test battery](research/test-battery.md)). Its scope leaves out measurement on
  neuromorphic hardware, three-dimensional or visual environments and language tasks
  ([Claims and scope](research/claims-and-scope.md#out-of-scope)).
- **The substrate's core modules are small.** They are written on the Python standard library
  alone, open no files or network connections and start no processes. Their only calls into the
  operating system are read-only readings of the clock, the load average and memory use, and the
  random identifiers the standard library's `uuid` module draws
  ([security policy](../SECURITY.md)).
- **Data.** The environments and the exploration that every stage 2 agent learns from are
  specified to be generated by code from recorded seeds. The substrate's exploratory experiments,
  which are separate from its core modules, read an external word-association norm set that the
  project did not author ([The substrate](PSYCHE.md)). The public
  [research plan](../tools/research_plan.json) lists no step that gathers data from people.

### The practices behind it

- **The claims discipline is a safety practice.** A reader should not come away believing more
  than the evidence supports. So the aim is named as an aim and never as a claim, no component is
  called a mind, conscious or sentient, mechanism is kept apart from meaning, a number without a
  captured source is not written, and a planned result is never written as obtained. Checks that
  enforce the claim terms run on every pull request and every push to the main branch
  ([Claims and scope](research/claims-and-scope.md)).
- **Negative results are reported.** A result that does not support the line's expectations is
  recorded and reported. The plan has a layer for the failure analysis, and the substrate's three
  stops are kept as results ([The three walls](three-walls.md)). The line reports what
  it finds at release, whichever way it falls.
- **The disclosure policy decides what leaves and when.** Material is released only as a complete,
  working, older version that has passed the scans and whose full diff the author has read.
  Pre-registered criteria are published unchanged at submission, so a reviewer can check them
  against their hashes ([Disclosure policy](research/disclosure-policy.md)).
- **Energy is an analytic estimate.** It is never a hardware reading and never a general claim that
  spiking networks are more efficient. Every estimate comes with its sensitivity analysis
  ([Claims and scope](research/claims-and-scope.md#energy-claims)).

### What this note does not cover

Later stages are not specified publicly, so this note says nothing about them. It makes no promise
about how any future component would be used, because the project cannot verify that today.

To raise a concern, ask in [GitHub Discussions](https://github.com/cagancaliskan/psyche/discussions).
A security problem goes through the private report described in the
[security policy](../SECURITY.md), and the [Code of Conduct](../CODE_OF_CONDUCT.md) names the same
private channel for conduct reports.
