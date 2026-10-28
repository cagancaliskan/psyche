# Glossary

> Public summary. Detail is withheld until submission under the [disclosure policy](disclosure-policy.md).

This page defines the terms used on the pages of the cognitive-map line and in the record of the
substrate, the two stages of Psyche so far. Terms are grouped by topic. Each definition says what
a word means on these pages. None of them describes how the spiking model works; its design is
withheld under the [disclosure policy](disclosure-policy.md). Works cited by author and year are
listed in full in the [reading list](reading-list.md).

## The project

**Psyche.** One open research project that builds brain-inspired components in stages, with
artificial general intelligence as its long-term aim. Each stage is built test-first and kept as
a citable artifact. The overview is the [repository README](../../README.md).

**Stage.** One step of the project, with its own code, record and claims. Stage 1 is the
[substrate](#the-substrate), the project's foundation, whose development is paused. Stage 2 is the
cognitive-map line described on these pages, which is active. Later stages are not specified
publicly yet. How the first stage led to the second is told in [Origins](origins.md).

**Artificial general intelligence (AGI).** The project's long-term aim (D-033 in
[DECISIONS.md](../../DECISIONS.md)). On these pages it is named only as an aim. No component is
described as having reached it, and no result is presented as a measured step toward it.

**Line.** A research line: one body of work within Psyche, with its own question, record and state.
There are two so far, the substrate (stage 1) and the cognitive-map line (stage 2). On these pages
"the line" means the cognitive-map line unless the text says otherwise. Which line is active and
which is paused is the [program state](#process-and-record), read from the ledger; it says what is
being worked on and never what is true of a result.

**SCM.** The short name of stage 2, which [CONTRIBUTING.md](../../CONTRIBUTING.md) gives for the
plan titled *Cognitive Map Formation and Energy Efficiency in Spiking Neural Networks with Local
Plasticity*. These pages mostly say "the cognitive-map line" or "stage 2" instead.

## Spiking cognitive maps

### Behaviour and the battery

**Cognitive map.** An internal model of how places, or items, relate to one another. Tolman
(1948) proposed it to explain maze behaviour in rats that chains of learned stimulus-response
associations did not explain. In this line the term names a measurable class of behaviour:
behaviour that memorised stimulus-response associations would not explain and an internal model
of the environment would. Showing that behaviour on a test is evidence of the behaviour and of
nothing more ([claims and scope](claims-and-scope.md)).

The five behaviours below are the tests of the [battery](test-battery.md). Each is adapted from a
classic animal-learning experiment, cited on the battery page.

**Latent learning.** Learning that takes place without reward and shows in behaviour only once a
reward is introduced. Rats that explored a maze without reward, and were then given food in it,
soon matched rats rewarded from the start. Battery test T1.

**Detour.** Choosing a suitable alternative route when a familiar route is blocked, using what is
already known about the environment. Battery test T2.

**Shortcut.** Taking a direct route between two known places when that route has never been
travelled. Battery test T3.

**Structural transfer.** Using structure learned in one environment to learn faster in another
that shares its layout but not its observations. Battery test T4.

**Transitive inference.** Inferring the relation between two items that were never presented
together from relations learned one pair at a time: having learned A over B and B over C,
choosing A over C. Battery test T5.

### Neuroscience background

**Place cell.** A neuron in the hippocampus that fires mainly when an animal is in one particular
region of its environment, the cell's place field (O'Keefe and Dostrovsky, 1971). Research
question RQ3 asks whether place-like representations emerge in the spiking model without being
built in. It is a question, not a result.

**Grid cell.** A neuron in the medial entorhinal cortex that fires at many locations which
together form a regular triangular lattice across the environment (Hafting et al., 2005).

Place cells and grid cells motivate brain-inspired models of map learning. Their existence does
not by itself say how a map is learned.

### Models and learning

**Spiking neural network.** A network of model neurons that communicate through spikes: brief,
discrete events in time. A model neuron integrates its input over time and emits a spike when
that input is strong enough; between spikes it sends nothing. The model of this line is a
spiking network. Its cost is expressed as a [synaptic-operation estimate](#measures-and-reference-agents).

**Neuromorphic hardware.** Hardware built around spikes and event-driven operation, as opposed to
a conventional processor or a GPU simulating them. The line does not measure on it: measurement on
neuromorphic hardware is out of scope, the cost of the spiking model is an analytic estimate of
synaptic operations, and that estimate is never set against energy figures reported for
neuromorphic chips, nor used for a general claim of efficiency ([claims and
scope](claims-and-scope.md#energy-claims)).

**Local plasticity.** A learning rule that computes the change to a synapse from information
available at that synapse, not from an error propagated backwards through the network as in
backpropagation, the standard way of training artificial neural networks. The spiking model
learns only through local plasticity.

**Brain-inspired, biologically plausible.** The words the line uses for its model in place of
any statement about biology. "Brain-inspired" says where a design idea came from. "Biologically
plausible" is used only where it can be argued, and says that a component relies on nothing a
neuron or a synapse could not plausibly have. Neither says that animals solve a task the same
way.

**Model-free reinforcement learning.** Reinforcement learning in which an agent learns action
values or a policy directly from the rewards it receives, without learning a model of how its
actions move it between states of the environment. One comparator family in the battery.

**Successor representation.** A representation of each state by the expected discounted future
occupancy of every state, itself included, under the agent's current behaviour (Dayan, 1993). It sits between
model-free and model-based learning. One comparator family in the battery.

### Measures and reference agents

**Synaptic-operation estimate.** An analytic estimate of how many synaptic operations an agent
performs on a task, used as a stand-in for energy. It is computed, not read from hardware:
nothing is measured on a chip or a power meter. It is always named an analytic estimate or an
analytic lower bound, under stated assumptions. A comparison it supports holds for that task,
that measure and those assumptions, and is not a general statement about spiking and
conventional networks. The measurement framework reports it for every agent, beside behaviour
and internal structure. The rules are in [claims and scope](claims-and-scope.md#energy-claims); the counting
method is withheld until release.

**Sensitivity analysis.** Repeating a calculation across a range of its assumptions to see which
results depend on them. Every energy figure of the line rests on assumptions about the cost of each
operation and about what is counted, so it is reported across a sensitivity analysis of those
assumptions, and a ranking is stated only if it holds in every setting. Otherwise the text says the
comparison depends on assumptions ([claims and scope](claims-and-scope.md#energy-claims)).

**Random agent.** A reference agent that chooses at random among the actions available to it. It
gives the lower bound beside which every result is reported.

**Shortest-path oracle.** A reference agent that knows the true layout of each environment and
always takes a shortest route. It gives the upper bound beside which every result is reported.
It learns nothing; it is given the true layout and marks the best a test permits. A test on which the
random agent and the oracle do not separate cannot grade any agent.

**Seed.** The integer that starts a pseudo-random number generator. The same seed gives the same
sequence, so a run can be repeated exactly; different seeds show how much a result depends on
chance. In this line, every source of randomness gets its own seed, the run's config records
them, and results are reported over several seeds ([engineering](engineering.md)). A hash seed
is different: it fixes Python's string hashing and is varied in determinism checks.

**Bootstrap confidence interval.** An interval for a statistic, such as a mean score over seeds,
obtained by resampling the observed values with replacement many times, recomputing the
statistic each time and taking the central range of the results. It makes no assumption about
the shape of the underlying distribution. The line reports uncertainty over seeds this way
([engineering](engineering.md)).

### Reproducibility and statistics

**Bit-exact.** Identical bit for bit, not merely equal after rounding. The line compares outputs
exactly, because a comparison after rounding cannot see a difference in the last bit of a
floating-point number, and that is where an order-dependent sum shows up. The substrate's record
has the case: a one-ULP difference in a float sum, the smallest step between two neighbouring
floats, was invisible on one interpreter and changed a result on another ([Origins](origins.md#the-determinism-discipline)).

**Tier.** One of three levels at which a result's reproducibility is stated. Tier A is bit-exact
across CPython versions and hash seeds, and covers the environments, the battery, the metrics and
the counters. Tier B is bit-exact on CPU for one pinned version, with deterministic algorithms
enabled. Tier C is statistical reproducibility for GPU runs: fixed seeds, with results reported
with confidence intervals over seeds. Each reported result states its tier, and a result built from
parts at different tiers states the weakest of them ([engineering](engineering.md#determinism-tiers)).

**Permutation test.** A significance test that builds its reference distribution by reshuffling
labels. The observed difference between two groups, for example the scores of two models, is
compared with the differences found when the group labels are shuffled at random many times; the
share of shuffled differences at least as large as the observed one is the p-value. It assumes
nothing about the shape of the data's distribution. The line tests differences between models this
way ([engineering](engineering.md#statistics)).

**Holm correction.** A way to keep the overall chance of a false positive in check when several
comparisons are made together. The p-values are ordered from smallest to largest. The smallest is
compared with the single-test threshold divided by the number of comparisons, the next with that
threshold divided by one fewer, and so on, so the strictest threshold applies to the smallest
p-value and the last is compared with the single-test threshold. Testing stops at the first
p-value that fails. The line applies it across multiple comparisons between models
([engineering](engineering.md#statistics)).

### Plan and governance

**Gate.** A fixed point in the plan where a decision is taken against criteria written in
advance. Each gate falls at or near the end of a phase, and its decision sets the route the next
phase takes. A gate has a public question, criteria written before the work they judge and kept
private until submission, and a fallback fixed in advance. Its public status is `upcoming` or
`decided`. A decided gate shows only the date it was decided and the next step (the line
continues to the next phase, extends, or stops), never its verdict. The gates are labelled A to D
([gates](gates.md)).

**Layer.** One of three levels the plan is built in, so that the line does not rest on its
riskiest part. The authoritative wording is generated from the plan file on the
[roadmap](roadmap.md).

- **Safe base.** The environments, the battery, the baseline comparisons, the analysis and the
  report. The line stands on it even if the spiking model does not work.
- **Main goal.** The spiking model with local plasticity, evaluated on the battery, with an
  analytic estimate of its synaptic operations.
- **Failure analysis.** If the main goal falls short, a documented account of where and why, kept
  as a result in its own right.

These layers are unrelated to the layers of the substrate's architecture.

**Ablation.** An experiment that removes, disables or holds fixed one part of a system and
measures what changes, to find out what that part contributes. In the plan, ablations belong to
the scaling phase and are part of what the last gate asks for ([roadmap](roadmap.md),
[gates](gates.md)). Which ablations are run is part of the experiment plan, which is withheld
([disclosure policy](disclosure-policy.md)).

**Pre-registration.** Writing down what will be measured and the criterion that will judge the
result before the work that tests it, then freezing that record, so that a result cannot reshape
the test it is judged by. Changing a frozen record needs a recorded decision with its reason. In
this line, pre-registrations stay private until submission, and their dates are made public by
hash commitment.

**Hash commitment.** A way to fix a file's content publicly without revealing it. A line holding a
random nonce is added to the frozen file, the SHA-256 hash of the whole file is published with a
date, and the file itself is published later, unchanged, so that anyone can hash it and compare.
The nonce stops anyone recovering a short file by hashing guesses until one matches, and a file
changed after its commitment no longer matches its hash. The commitments are listed in the
[disclosure policy](disclosure-policy.md#pre-registration-without-disclosure) and recorded in
[`tools/research_plan.json`](../../tools/research_plan.json).

## The substrate

The substrate is stage 1 of Psyche and its foundation: a dependency-free prototype of a
memory-and-activation substrate. Its development has been paused since 2026-10-23 under D-031 in
[DECISIONS.md](../../DECISIONS.md); its record is in [PSYCHE.md](../PSYCHE.md) and its as-built
reference in [ARCHITECTURE.md](../ARCHITECTURE.md). The terms below come from that record, where
the substrate is often called Psyche, the name it carried when it was the whole project. None of
them names a part of the spiking model ([Origins](origins.md)).

> **Borrowed vocabulary is engineering lineage, not a claim.** Several substrate terms come from
> cognitive psychology and from research on cognitive architectures: spreading activation,
> coalition, workspace and broadcast among them, and the emotion words used as labels on roads.
> In the substrate they are names for engineering components. They record where a design idea came
> from. They do not claim that a component reproduces the effect or the theory the word comes
> from. Whether any component has cognitive meaning is decided only on the meaning axis, below,
> and the substrate makes no cognitive claim.

### Components

**Store.** The substrate store: the component that holds the substrate's graph of nodes and
roads, and the only component that changes it. Every node and road is addressed by a stable opaque id,
never by position. Reads are pure: reading a road computes its decayed strength without writing
it back. In development, each change is checked for integrity incrementally, and a full
integrity scan is available for an offline pass. Module `src/psyche_store.py`.

**Node.** The unit of information in the store: a piece of content with a type (event, concept,
entity, sensation or abstract), a stable id, and a formation order kept separately from the id,
so that ties break the same way in every process. A node carries no emotional label; labels live
on roads.

**Road.** A directed connection from one node to another. There is at most one road per ordered
pair, and the reverse direction is a separate road. A road has a strength, which acts as its
conductance, grows when the road is crossed or strengthened, can be lowered by an explicit
weakening call on the store, and decays with elapsed time. It may carry named charges, each a
label with a signed intensity. It may also be closed: a sticky state that only an active crossing
changes, never a read and never the passage of time.

**Spreading activation.** The substrate's read-only operation that sends activation outward from
a start node (the substrate's code calls it the seed) along its out-roads. Each hop passes on a share set
by the road's strength and by a global per-hop decay; activation that reaches a node by several
paths sums; a hop budget and a floor keep the spread local. The spread is expanded one hop layer
at a time and its sums do not depend on iteration order, so its result is a deterministic
function of the store. The captured run checks this on CPython 3.10 to 3.14 under six hash seeds
(the `determinism` block of [`tools/ledger.json`](../../tools/ledger.json)). A closed road blocks weak activation and lets a small
fraction of strong activation through. The operation changes nothing in the store. The term
comes from models of semantic memory in cognitive psychology.

**Coalition.** A group of co-activated nodes treated as one candidate for selection. The
substrate forms coalitions mainly from a multi-source activation field. The nodes the input text matched are
first grouped by graph proximity, and the field spreads from one representative per group. Each
representative's basin, the nodes it activated more strongly than any other representative did,
becomes one coalition. A coalition's strength is the sum of its members' activations.

**Workspace.** The stage that selects one coalition from the candidates, by activation density
with a minimum-size guard, and prunes from it the members pulled more strongly toward a region
the input did not name than toward the region it did name. Selection is a pure read.

**Broadcast.** The one bounded write in the substrate's cycle. It strengthens each road inside the
selected coalition exactly once, creates no road and touches no node, and so biases the next
cycle. Its bound comes from the saturation of the store's strengthening rule, not from a clamp.
It is off by default; with it off, the whole cycle is a pure read.

### Process and record

**Brick.** A unit of the substrate's build plan: a component, a fix, a tool or an attempt at a cognitive
claim. Under the project's process, a brick is specified, tested and verified by an independent
tester before anything builds on it. Each brick has a short id, such as 0a for the substrate
store, and the ledger records its status. Build and meaning are tracked as two separate axes and
are never collapsed into one. The substrate's three attempts to earn a first cognitive claim
were bricks of this kind ([the three walls](../three-walls.md)).

**Build axis.** Whether a brick is built and verified, as a mechanism. Its status names:

| Status name | Meaning |
|---|---|
| `PROVEN` | Verified by the full adversarial suite on every interpreter; not a formal proof. For the substrate: determinism, integrity and purity |
| `BUILT-UNVALIDATED` | Built and tester-verified as mechanism, with no positive meaning verdict |
| `DESIGNED` | Designed on paper, in a vision document or a specification, and not built |
| `HORIZON` | Open research, with no agreed definition of done |

A brick that is only an attempt at a cognitive claim carries its meaning verdict as its ledger
status.

**Meaning axis.** Whether a brick reproduces a cognitive effect, judged against external data the
project did not author, with the prediction and its direction fixed in advance and a baseline.
Its verdicts are `EARNED`, `NOT-YET` and `NO-GO`; a stop caught by pre-registration before a
graded run is a result in its own right ([the three walls](../three-walls.md)). A brick is
routinely built and tester-verified on the build axis while its meaning verdict is `NOT-YET`.
No substrate brick holds an `EARNED` verdict; the meaning bar is open.

**Yardstick.** A reference from outside the project against which a result is graded, so that a
test cannot quietly encode its own answer (rule 5 of the project's rules). For the substrate it was
external data the project did not author, such as human association norms or the machine's own
clock readings. For the cognitive-map line the behavioural paradigms are published, and the
published behaviour of each baseline is the reference. The agent-side operationalisation of each
paradigm and its pass criteria are the project's own and are pre-registered privately, so they are
not an external protocol for artificial agents. A yardstick the mechanism can both produce and be
graded against is what the substrate's attempts lacked ([the three walls](../three-walls.md)).

**Wall.** The project's name for each of the substrate's three negative results: three attempts to
earn a first cognitive claim, each stopped before any graded result existed, each for a
structurally different reason (circular, mechanism absent, signal flat). The walls are a finding
about the substrate and these three yardsticks, not a general law, and a wall never means that the
phenomenon is absent, only that it could not be measured under those controls. They are set out in
[the three walls](../three-walls.md) and carried forward as a checklist in [Origins](origins.md).

**Program state.** A third axis, separate from the build and meaning axes, that records what is
being worked on: the substrate paused, the cognitive-map line active. It never says what is true of a brick, so the
pause changed no brick status, meaning verdict or test figure. It lives in the `program` block of
the ledger, and only the project lead changes it, by a new entry in [DECISIONS.md](../../DECISIONS.md).

**Ledger.** [`tools/ledger.json`](../../tools/ledger.json), the single source of truth for every
fact the substrate's documents quote: test counts, brick statuses, meaning verdicts, constants
and results, plus the program state and the claim terms for the whole project and for the
cognitive-map line. Prose cites the ledger; the ledger never cites prose.
[`tools/ledger_check.py`](../../tools/ledger_check.py) fails when a document disagrees with it,
uses a status word it does not hold, or asserts one of the project's forbidden claims; the
line's own terms are checked by [`tools/publish/check_copy.py`](../../tools/publish/check_copy.py).
The cognitive-map line keeps its public dates the same way, in one plan file.

**Capture.** A recorded run of the substrate's canonical test runner, `run_tests.py`, saved in
[`docs/TEST_OUTPUT.txt`](../TEST_OUTPUT.txt) with its date, the interpreters it was run on and
the hash seeds swept. The ledger's test counts are
generated from the capture by a tool, never typed by hand. The cognitive-map line applies the
same idea to its results: a number it reports must come from a captured results file.

**Loop-closed.** Describes a test or a check that feeds each stage with what the stage before it
produced, not with friendly, hand-chosen input. A component that passes only on input chosen to
suit it has not passed. Loop-closure is rule 4 of the project's rules, and the substrate's tester
suites are adversarial and loop-closed ([Origins](origins.md#an-independent-adversarial-tester-lane)).
It is a property of a test and is not the substrate's closed cycle, in which a broadcast biases the
next cycle.

**Lane.** The part of the work that one role owns. Psyche has four roles: the architect-pm writes
the specification and keeps the roadmap and ledger, the builder implements it test-first, the
tester attacks it separately and never edits the code, and the validator runs the pre-registered
experiment when a cognitive claim is involved. The lanes do not cross, and the separation is the
evidence: a check written by the author of the code shares the author's blind spots
([how Psyche is run](../governance.md)).

Back to the [overview](README.md).
