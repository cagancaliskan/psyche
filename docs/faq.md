# Questions and answers

Short answers to what newcomers ask first. Each question is a heading, so it can be linked.
Where a longer answer exists, it is linked. For a first tour of the project, read the
[Reader's guide](guide.md).

## Why is AGI named as an aim?

Psyche's long-term aim is artificial general intelligence (AGI), and leaving the aim unsaid would
misstate the project. The rule is that it is named as an aim and never as a claim. No page says
that Psyche or any of its components is or achieves AGI, and nothing built so far is general
intelligence ([Claims and scope](research/claims-and-scope.md#the-projects-aim)).

The stages are how the project works toward the aim without claiming it. Each stage is built
test-first and kept as a citable artifact. Stage 1 gave the project its method. Stage 2 asks one
narrow question about one measurable class of behaviour, and no result of it is presented as a
measured step toward the aim. Later stages are not specified publicly yet
([Origins](research/origins.md#where-it-points)).

## Is Psyche a mind, or conscious?

No page claims it. Psyche and its components are never called a mind, conscious or sentient, and
the spiking model of stage 2 is never described in terms of consciousness, understanding or
thinking. In stage 2, "cognition" names a class of behaviour that a test can measure. Passing a
test is evidence of that behaviour and nothing more
([Claims and scope](research/claims-and-scope.md#the-core-rule)).

The substrate's closed cycle is a mechanism result: it runs, deterministically, and does what it
says. No cognitive meaning is claimed for it ([The substrate](PSYCHE.md)).

## Are there results yet?

Not for stage 2. No stage 2 results are reported yet, and its pages describe a plan. The plan does
not depend on a positive answer: if the spiking model falls short, a documented account of where
and why is kept as a result ([Roadmap](research/roadmap.md)). When the plan changes, the
[Progress](progress.md) page records it.

The substrate does have a public record. Its lower layers are verified correct and deterministic,
and its three attempts at a first cognitive claim each stopped before a graded number existed
([The three walls](three-walls.md)). That record is about the substrate only and says
nothing for or against stage 2.

## What does "verified" mean here?

It means verified by the full adversarial suite on every interpreter. It is not a formal proof.

It is also a statement about mechanism: the code does exactly what it says, reproducibly. Whether
code reproduces a cognitive effect is a separate claim with a separate evidence bar, judged
against external data. A part of the substrate can be verified as mechanism while its meaning is
still open, and the two are tracked as separate axes ([The substrate](PSYCHE.md)).

## Why are some parts private?

Two rules sit behind it. Criteria are written before the work they judge, so that a result cannot
reshape the test it is judged by. And a public version must never hold the code, comments or
documents that would let a reader catch up with the current state of the work. The
[disclosure policy](research/disclosure-policy.md) applies both: hypotheses beyond the research
questions, pass criteria and thresholds, the reasoning behind a decided gate, the experiment plan,
the model and its code, and results stay private until a release.

A release is a complete, working, older version, never the current state. Pre-registered criteria
are published unchanged at submission. Until then the date they were fixed is public as a hash
commitment, so that anyone can check later that they did not change.

What is public now is the overview, the roadmap, the gates, the test battery, the claims
discipline, the engineering standards, and the substrate's code, tests and published record.

## Does Psyche use a large language model?

The substrate has no language model in it. It is a prototype written on the Python standard library
alone: a graph store of concept nodes and weighted roads, a deterministic spreading-activation
engine, and a workspace that runs one competition and prunes what no perceived input supports. Its
recorded aim describes it as a non-LLM memory-and-activation substrate ([The substrate](PSYCHE.md)).

Stage 2 studies a spiking network that learns only through local plasticity: a learning rule that
changes a synapse from information available at that synapse, not from an error propagated
backwards through the network ([Glossary](research/glossary.md)). Language tasks are outside its
scope ([Claims and scope](research/claims-and-scope.md#out-of-scope)).

Stage 2 is designed to compare its model with other agents on the same environments, from the
same experience. The public pages name the families: model-free reinforcement learning, recurrent
model-free agents, a small transformer agent, the successor representation and published
cognitive-map models. They are points of comparison, not parts of Psyche
([Test battery](research/test-battery.md#comparator-families)).

## Why spiking networks, and are they more energy efficient?

The open question is narrow: whether behaviour that an internal map would explain, and memorised
responses would not, can arise in a network of spiking neurons that learns only through local
synaptic plasticity ([Overview](research/README.md)). Place cells and grid cells motivate
brain-inspired models of map learning, but they do not say how a map is learned.

Whether such a network is more efficient is not claimed. One research question asks what the
behaviour costs, as an analytic estimate of synaptic operations. Energy is only ever an analytic
estimate or lower bound, reported with a sensitivity analysis. No hardware reading is evidence,
and a ranking is stated only if it holds in every setting of that analysis. Any comparison holds
for one task, one measure and stated assumptions
([Claims and scope](research/claims-and-scope.md#energy-claims)).

## Who runs Psyche?

The project lead, Cagan Caliskan, sets direction and makes the calls. Contributors propose. Work
moves through four roles, architect-pm, builder, tester and validator. They name kinds of work,
not separate people: the project has one maintainer. Each kind of change has its own place in the
repository, and a test suite is written apart from the code it attacks.
[How Psyche is run](governance.md) sets out the roles, how decisions are recorded and how funding
stands.

## Can I fund or support the work?

Psyche has no external funding yet. Its project lead is searching for funding, and a person willing
to donate to the work can get in touch through
[GitHub Discussions](https://github.com/cagancaliskan/psyche/discussions).
[How Psyche is run](governance.md#funding) says where funding stands.

## How can I take part?

Ask a question, propose a battery test or comment on a page in
[GitHub Discussions](https://github.com/cagancaliskan/psyche/discussions). A new baseline or a new
paradigm for the battery should say which published paradigm or source it comes from. The other
routes, for a wrong claim, a stale number or a security problem, are in the
[Reader's guide](guide.md#get-in-touch).

If a claim or a goal is unclear, ask in a Discussion before writing it into the repository. To send
a change, [Taking part from outside the project](../CONTRIBUTING.md#taking-part-from-outside-the-project)
says where each thing goes, how to set up and what a pull request must pass. The
[project rules](../CONTRIBUTING.md) are the shared ground truth, and the
[Code of Conduct](../CODE_OF_CONDUCT.md) covers the issues, pull requests and Discussions.

## Can I use or cite the work?

The code is MIT-licensed and the archived report is open access under CC BY 4.0. How to cite is in
the [Reader's guide](guide.md#how-to-cite). No code of stage 2 is public yet: it will appear under
`cogmap/` only as a release, under the [disclosure policy](research/disclosure-policy.md).
