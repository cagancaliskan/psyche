# The three walls

The substrate, stage 1 of Psyche, tried three times to earn a first cognitive claim, each time
naming an external yardstick that the project did not author. All three attempts were stopped
before any graded result existed, and each for a structurally different reason. The project calls
each of these stops a wall. This page sets the three out from their own records: what was
attempted, what stopped it, what was and was not claimed, and what it left behind.

The [substrate](PSYCHE.md) is a dependency-free memory-and-activation prototype whose lower layers
are verified correct and deterministic. Its cycle runs end to end: activation spreads over a graph
of weighted roads, a workspace selects one candidate, and a bounded broadcast feeds back. It makes
no cognitive claim. Psyche itself is an open research project that builds brain-inspired
components in stages, with artificial general intelligence (AGI) as its long-term aim, named here
only as an aim ([Reader's guide](guide.md)).

## The three at a glance

| Attempt | What stopped it |
|---|---|
| Semantic priming (brick 1e) | Circular: the norm and the edge weight were the same quantity, so agreement could hold by construction |
| The fan effect (brick 1e′) | Mechanism absent: the engine gives every out-road the source's full activation, so there was nothing to grade |
| Interoception (brick 2c) | Signal flat: on realistic work the signal sits near zero, so a test would have to manufacture the range of values it needs |

Each section below also gives the external yardstick and what the attempt left behind. The build
status and the meaning verdict of each brick are not repeated here. They are read from the ledger
and shown, on two separate axes, on the
[substrate status page](https://cagancaliskan.github.io/psyche/status/).

## Semantic priming (brick 1e): circular

**What was attempted.** In people, judging that two strings of letters are both words is faster
for commonly associated words than for unassociated ones (Meyer and Schvaneveldt, 1971), the
effect known as semantic priming. The attempt asked whether the substrate's cycle, given a prime,
activates strongly associated targets more than matched weakly associated ones. It was to grade
only the direction of the effect, against human association norms, with graph reachability and
path distance held constant.

**The yardstick.** The norms are the Small World of Words English word-association data (De Deyne
et al., 2019). The project authored none of the relatedness values. The pairs were chosen by a
blind, seeded procedure that was frozen before the run, and the predicted direction was fixed in
advance.

**What stopped it.** The substrate builds each road's weight from the same association strength
that the norms use to call a pair related. A result in the predicted direction could therefore
have been the weight map read straight back out. The protocol guarded against this with a check
that the cycle adds something over the bare weights, which needs pairs that the norms separate and
the weights do not. The blind selection step showed that on this corpus such pairs are far too few
to grade anything, and that the fallback comparison could not succeed even in principle, because
the bare weights already separate the pairs almost completely. The check fired at selection time.
No cycle was run on any selected pair.

**What was and was not claimed.** No priming result is claimed, because none was graded. It is
not claimed that priming is absent from the substrate. The honest form is that it could not be
measured under these controls on this corpus, because weight and association are too entangled to
tell priming through the cycle from a readback of the weights. Nothing here says anything about
understanding or meaning in a human sense, and no threshold was loosened to obtain a graded run.

**What it left behind.** The record keeps the check and its refusal as the worked example of
declining a run that could not be interpreted. Stage 2 carries the failure mode forward as an item
on a checklist: a test whose answer is already encoded in the environment, the input or the
comparison ([Origins](research/origins.md)).

## The fan effect (brick 1e′): mechanism absent

**What was attempted.** After the priming stop, the fan effect was the pre-named backup. In
people, the more facts are learned about a concept, the slower any one of them is verified
(Anderson, 1974). The substrate has activation, not latency, so the record states a bridge as an
assumption that can be challenged: higher activation stands for faster retrieval, which gives the
prediction that activation of any one target falls as the number of out-roads of its source grows.
The attempt began as a feasibility pre-check, answered before any experiment was designed.

**The yardstick.** The published human effect. Its direction, more facts and slower retrieval, was
taken from that literature and not from the project.

**What stopped it.** The account given in the literature on the ACT-R cognitive architecture is
spreading activation from a source with a fixed budget that is divided among its associations. The
substrate's engine does the reverse, by design: every out-road receives the source's full
activation. An earlier exploratory characterisation of the engine, captured in full and not a graded
run, had already found the response flat to the last digit as the fan grew. The record then checks
that closing the loop changes nothing, since the workspace's competition scores a candidate group by
its activation per member, which depends on the size of the group and not on the fan of its source,
and its broadcast has no fan term. There was no fan-dependent signal to grade, circular or
otherwise. This wall differs from the first: the signal was not entangled with the weights, it was
absent.

**What was and was not claimed.** No fan-effect result is claimed. No graded fan experiment was
designed or run, because re-running a flat line as the headline would have turned a null into the
project's main cognitive claim. It is not claimed that the fan effect is absent in principle. The
missing division of activation is not a defect either: it was a design choice of the engine,
verified and documented.

**What it left behind.** The only route to a testable fan effect is to change the engine, and the
record holds that a change made in order to produce the effect would not earn it. The effect would
count only if the mechanism were adopted for an independent reason and the effect then fell out
untuned. The change was therefore held as a separate architecture decision
([D-004](../DECISIONS.md)). A divisive-normalisation overlay was later built as its own brick,
default off with a neutral value identical to the earlier behaviour, as rule 10 of the project's
rules asks. Its justification was independent of the fan effect: a workspace with no capacity limit
is a workspace in name only ([the overlay's specification](specs/SPEC-0b2-conserved-activation.md)).
A check on a synthetic example shows activation falling as the fan grows, which is a property of
the mechanism and not a graded result. Changing its default would be a separate brick with its
own gate, and no fan-effect claim is made.

## Interoception (brick 2c): signal flat

**What was attempted.** The attempt asked whether a body-state signal, computed from the machine's
own clock readings and injected as one global parameter that names no node, changes which
candidate wins the workspace. The direction was fixed in advance: the higher the signal, the
narrower and more local the selection, taken from published work on arousal and the range of cues
used (Easterbrook, 1959). The test also needed a control showing that the effect was not the signal
passed straight through.

**The yardstick.** The machine's own timers: wall-clock time against CPU time over each measured
interval. The project neither authors nor can author these readings, and no human-norm dataset is
in the loop, so the circularity of the priming attempt could not arise.

**What stopped it.** The signal is a stall fraction: the share of elapsed time that a process spends
waiting instead of computing. A realistic cycle of the substrate is single-threaded, held in memory,
and does no input or output and no blocking, so it spends essentially no time waiting and the signal
sits near zero. The signal is also a ratio, so a heavier workload does not move it. The first
capture design had injected a short sleep into the measured work. That produced a high, narrow range
of values, but its level was set by the sleep and not by contention, and a description that said
otherwise was found false and corrected before any graded number existed. The only ways to widen the
range are injected waits, forced memory swapping and saturating the cores with rival processes. Each
manufactures contention, and the protocol forbids it. The limitation was recorded as the finding,
and the graded run did not proceed.

**What was and was not claimed.** No interoceptive effect is claimed, and no graded number was
computed. Nothing here says that the substrate has a body, emotions or any experience of load: the
language of bodily feeling in the early vision documents is inspiration, and it stays out of every
claim. This wall concerns the signal, not the mechanism. The sensor, the modulation hook and replay
determinism were verified by an independent tester, and the ledger keeps that mechanism result and
the unearned meaning verdict on separate axes.

**What it left behind.** A rule against widening the range of the signal to make a test gradable:
any variation must come from the work itself. Stage 2 turns the lesson into a design requirement.
Every result is reported beside a random agent and a shortest-path oracle, and a test on which those
two do not separate cannot grade anything ([Origins](research/origins.md)).

## The pattern

The three obstacles differ in kind. In the first, the external norm was the same quantity as an
edge weight. In the second, the mechanism that produces the effect was not in the engine. In the
third, the signal under test did not move. The substrate's layers were verified as mechanism each
time, and what was missing was an external yardstick that the mechanism could both produce and be
graded against. Each stop was caught before a graded result existed, by a check or a protocol
written beforehand.

That is the anti-circularity discipline working. The project reports it as a result and not as a
failure: a pre-registered stop caught before a graded run is a first-class result
([CONTRIBUTING.md](../CONTRIBUTING.md)). Stage 2 uses the three as a checklist of failure modes to
rule out beforehand ([Origins](research/origins.md)).

## What the pattern does not show

- **It is not a general law.** It is a finding about this substrate and these three yardsticks. It
  says nothing general about spreading activation, about word-association norms or about
  cognition.
- **A stop is never "the phenomenon is absent".** The honest form is that the effect could not be
  measured under these controls on this substrate.
- **It is evidence about the substrate only.** It says nothing for or against the spiking model of
  stage 2, which is a separate codebase and shares no model code with the substrate
  ([Origins](research/origins.md#what-does-not-carry-over)).
- **It is not a measure of progress toward the long-term aim.** The walls are results about what
  could be measured. No result on this page is presented as a step toward AGI.

## The records

Each wall is a frozen record in the repository.

- Semantic priming: [the pre-registration and its outcome](experiments/EXP-1e-priming.md),
  [the specification](specs/SPEC-1e-priming.md) and decision [D-003](../DECISIONS.md).
- The fan effect: [the specification and its feasibility pre-check](specs/SPEC-fan-effect.md)
  and decision [D-004](../DECISIONS.md).
- Interoception: [the pre-registration](experiments/EXP-2c-interoception.md),
  [the specification](specs/SPEC-2c-interoception.md) and decision [D-005](../DECISIONS.md).
  The [architecture reference](ARCHITECTURE.md) describes the sensor and its modulation hook.
- Facts: [`tools/ledger.json`](../tools/ledger.json) holds every count and status, and the
  [substrate status page](https://cagancaliskan.github.io/psyche/status/) shows them.

## Works named on this page

- De Deyne, S., Navarro, D. J., Perfors, A., Brysbaert, M., and Storms, G. (2019). The "Small
  World of Words" English word association norms for over 12,000 cue words. *Behavior Research
  Methods*, 51(3), 987-1006.
  [doi:10.3758/s13428-018-1115-7](https://doi.org/10.3758/s13428-018-1115-7)
- Anderson, J. R. (1974). Retrieval of propositional information from long-term memory.
  *Cognitive Psychology*, 6(4), 451-474.
  [doi:10.1016/0010-0285(74)90021-8](https://doi.org/10.1016/0010-0285%2874%2990021-8)
- Easterbrook, J. A. (1959). The effect of emotion on cue utilization and the organization of
  behavior. *Psychological Review*, 66(3), 183-201.
  [doi:10.1037/h0047707](https://doi.org/10.1037/h0047707)
- Meyer, D. E., and Schvaneveldt, R. W. (1971). Facilitation in recognizing pairs of words:
  Evidence of a dependence between retrieval operations. *Journal of Experimental Psychology*,
  90(2), 227-234. [doi:10.1037/h0031564](https://doi.org/10.1037/h0031564)

## Related pages

- [Origins](research/origins.md): how the substrate led to stage 2, and which practices carry over.
- [The substrate](PSYCHE.md): what it built and what it showed.
- [Methodology](METHODOLOGY.md): how adversarial testing found defects in the substrate.
- [Claims and scope](research/claims-and-scope.md): the wording rules for stage 2.
- [Glossary](research/glossary.md): yardstick, wall, brick and the other terms used here.
