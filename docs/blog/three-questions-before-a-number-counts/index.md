---
title: "Three questions a test answers before its number counts"
date: "2026-11-10"
description: "Three checks Psyche runs on an experiment before any number is graded, shown in code on the substrate's priming, fan-effect and interoception tests."
tags:
  - "substrate"
  - "project"
  - "methods"
---

A check written before the substrate's priming experiment ran settled the experiment by
arithmetic. The substrate is Psyche's memory-and-activation prototype, and the test had selected
300 primes from a human word-association corpus. Before a single activation was computed, the
bare edge weights already ranked the strong associate above the weak one for 296 of them, a
separation of about 0.973 on a scale that ends at 1.0. The check asked the full cycle to beat
that by 0.20, so a pass would have needed about 1.17 out of a possible 1.0.

Two more checks did the same kind of work on two later experiments. For the fan effect, a
pre-check found that an earlier sweep had already returned the same activation, `0.2433743975`,
at fan 1, 2, 4, 8 and 16. For interoception, a body-state signal read from the machine's own
timers sat near zero on real work, and the band the capture recorded was set by a sleep the
capture itself injected. Each check asked a different question of its test: whether the answer
was already in the input, whether the mechanism was there, and whether the signal moved. Each
was answered before a graded number existed, so none was graded.

## Why one check is not enough

The reflex repair for a test that cannot be graded is more of something. For the first case it is
more primes: the weight-blind pairs the protocol needed turned up for 7 primes in 300, and at
that rate roughly 1,300 primes would clear its floor of 30. The fallback ceiling of about 0.027
would not move with the sample at all. For the second case the reflex is a better stimulus set,
and for the third a heavier workload. With three ungraded tests on one system, the next reflex is
to merge them into one statement, here something like "spreading activation does not produce
these effects".

Each of those readings breaks on the code. The three checks sit at three different points of the
pipeline, so they answer different questions, and no single one of them would have caught all
three cases.

![Three rows, one per experiment, across three stages: input, mechanism and signal. For semantic priming the check fires at the input, because the external norm is the edge weight. The fan effect passes the input and its check fires at the mechanism, because every out-road receives the full source activation. Interoception passes the input and the mechanism and its check fires at the signal, because friction stays near zero on CPU-bound work. No graded number exists for any row.](what-each-check-caught.svg)

## Question one: is the answer already in the input?

The priming experiment (brick 1e) was designed to grade the direction of semantic priming against the Small World of
Words association norms. The substrate graph was built from the same corpus, and each road's
weight comes from the same association strength the norms use to call a pair related. From
[`experiments/swow.py`](../../../experiments/swow.py):

```python
def traverse_count_for_strength(strength: float) -> int:
    """The single fixed monotonic mapping from SWOW association strength to traverse count."""
    return min(STRENGTH_CAP, 1 + int(strength * STRENGTH_SCALE))
```

`STRENGTH_SCALE` is 100 and `STRENGTH_CAP` is 10. Every corpus row with a positive strength becomes
a road traversed that many times, and traversal count sets a road's strength in the store. So
"strongly associated" and "heavy edge" are one number seen twice. A result in the predicted
direction, strong associates more active than weak ones at equal distance, could be this map read
straight back out at the target.

The [pre-registration](../../experiments/EXP-1e-priming.md) saw this and fixed a guard before any
data: the cycle had to separate strong from weak targets where the bare weights could not. That
needs pairs whose strong and weak member land on the same integer weight, a weight-blind stratum.
The selector admits a pair to it only when the integer weights tie, and then only when both
targets also share a decile of in-degree, a coarse control on popularity. From
[`experiments/priming_1e.py`](../../../experiments/priming_1e.py):

```python
    high, low = high_low_bands(topo, p)
    if not high or not low:
        return None
    cands: List[Tuple[int, int]] = []
    for h in high:
        wh = w_of(topo, p, h)
        dh = decile_of(topo.indeg[h], cuts)
        for l in low:
            if h == l:
                continue
            if w_of(topo, p, l) != wh:           # weight-blind: W_gap = 0
                continue
            if decile_of(topo.indeg[l], cuts) != dh:   # in-degree-matched: same decile
                continue
            cands.append((h, l))
    if not cands:
        return None
```

The blind, seeded selection run consulted only topology and association strength. It found 7 such
primes against a pre-registered floor of 30
([selection output](../../../experiments/results/priming_1e_selection_output.txt)). The in-degree
match dropped none of them, so the count comes from the weight tie alone. Below the floor,
the protocol falls back to a margin over all primes: the cycle's strong-over-weak separation, as a
rank-biserial `r_MA`, must exceed the bare weights' own separation `r_W` by at least 0.20. The
protocol defines both as twice the fraction of primes with the strong target strictly ahead, minus
one, so a tie counts as no separation. The weights put the strong target strictly ahead for 296 of
300 primes, so `r_W = 2 × 296/300 − 1 ≈ 0.973`. Neither quantity can exceed 1.0, so the largest
margin any activation pattern could produce is about 0.027. The gate was closed by arithmetic,
before the cycle ran on a single selected pair ([D-003](../../../DECISIONS.md)).

The obvious repair is more data. More primes could fill the weight-blind stratum, slowly, since
the integer ladder rarely gives a prime's top-decile associate and its 10th-to-25th-percentile
associate the same rung. They would not move the fallback: its ceiling is fixed by the fraction of
primes the weights already separate, whatever the size of the sample.

## Question two: is the mechanism there?

The fan effect (brick 1e′) was the pre-named backup. In people, the more facts are learned about a
concept, the slower any one of them is verified (Anderson, 1974). With a stated bridge from latency
to activation, the prediction was that a target's activation falls as its source's out-degree
grows. The account in the ACT-R literature is a fixed source budget divided among its associations.
The transmission loop of [`src/psyche_activation.py`](../../../src/psyche_activation.py) does not
divide by default:

```python
            for road_id, road in roads:
                outgoing = node_act
                if road.closed:
                    frac = closed_transmission(outgoing, road)
                    if frac <= 0.0:
                        continue  # barrier holds; weak cue blocked
                    outgoing = outgoing * frac
                    broke_through.append(road_id)  # observable intrusive-recall event

                # two distinct attenuators:
                #   edge conductance (road.strength) — property of the connection
                #   global distance penalty (decay_per_hop) — property of the spread
                transmitted = outgoing * road.strength * decay_per_hop
```

`outgoing = node_act` sits inside the loop over out-roads, so every road starts from the source's
full activation, whatever the number of roads. In a star, a leaf's activation depends only on its
own road and its own distance, and on nothing about its siblings. The fan sweep in
[`experiments/fan_effect.py`](../../../experiments/fan_effect.py) builds a star of equal-strength
roads and reads one leaf as the fan grows; the line is flat to the last digit
([captured output](../../../experiments/results/fan_effect_output.txt)).

The first case's circularity does not recur here. The star holds edge weight fixed while only fan
varies, so the input carries no hidden answer, and what is missing is the mechanism. As the
[fan-effect specification](../../specs/SPEC-fan-effect.md) puts it, priming's weight-blind stratum
was too thin to use, while here the stratum where a bare readback predicts no fan effect is every
condition, and the closed loop adds nothing there: the workspace scores a coalition by activation
per member, and the broadcast has no out-degree term.

The obvious repair is to add the division. The engine has a default-off overlay that does a version
of it: divisive normalisation, where a road's drive is scaled by `sigma / (sigma + competing)` and
`competing` is the rest of the source's outgoing conductance. With `sigma = 1.0` the same sweep
falls strictly, and the recorded values are in [D-008](../../../DECISIONS.md), which also records
the cost: at that `sigma`, every target on the word-association graph falls below the engine's
activation floor. That curve is not a result. [D-004](../../../DECISIONS.md) holds that a mechanism adopted in order to produce an effect
would not earn it, so the overlay ships with a neutral default identical to the old engine, its own
justification is independent of the fan effect, and no fan-effect claim is made.

## Question three: does the signal move?

The interoception experiment (brick 2c) did not have the first case's problem, by design. Its yardstick
is the machine's own timers, which the project cannot author. A body-state number is computed from
them and injected as one global spreading parameter that names no node. The number is defined in
[`src/psyche_bodysensor.py`](../../../src/psyche_bodysensor.py):

```python
    if wall_dt is None or cpu_dt is None:
        return NEUTRAL_FRICTION
    if wall_dt < MIN_MEANINGFUL_WALL_DT:
        return NEUTRAL_FRICTION
    ratio = cpu_dt / wall_dt
    friction = 1.0 - ratio
    if friction < 0.0:
        return 0.0
    if friction > 1.0:
        return 1.0
    return friction
```

`friction = 1 − cpu_dt / wall_dt` is a stall fraction. It rises only when the process is off the
CPU. A cycle of the substrate is single-threaded, held in memory, and does no input, output or
blocking. CPython's cyclic collector runs in-thread and is counted as CPU time, so a collection
makes a cycle slower without raising friction. On real work the number sits near zero.

The capture written for the graded run,
[`experiments/exp2c_capture.py`](../../../experiments/exp2c_capture.py), did produce a band, for a
reason visible in its loop:

```python
    for i in range(CAPTURE_SAMPLES_REALISTIC):
        # ONE realistic work interval = real cognitive work (the cycle). The returned
        # ThoughtResult is intentionally discarded: we measure TIMING, never read its winner.
        think(workload_store, WORK_UTTERANCES[i % len(WORK_UTTERANCES)])
        time.sleep(REALISTIC_YIELD_S)  # small cooperative yield (NOT a deliberate stall)
        samples.append(TelemetrySample(perf=time.perf_counter(), proc=time.process_time()))
```

The yield is 0.5 ms; [D-005](../../../DECISIONS.md) records a realistic cycle as about 47 µs of
CPU-bound work. The sleep is the only off-CPU interval, so it sets the level:
`1 − 47/(47 + 500) ≈ 0.914`. The recorded band was [0.79, 0.93] with a mean of about 0.86, high
and narrow, and its level followed the ratio of sleep to work, with no contention behind it. A description saying otherwise was found false
and corrected in the [pre-registration](../../experiments/EXP-2c-interoception.md) before any graded
number existed.

The obvious repair is a heavier workload. A ratio does not notice: pure CPU work of any size gives
`cpu ≈ wall`, so ten times the work is ten times the duration at the same friction. The remaining
ways to widen the band are larger sleeps, forced swapping or saturating the cores with rival
processes. Each manufactures the contention it claims to measure, and the protocol forbids all of
them. The sensor, the default-off hook and replay determinism were verified. The check fired on
the signal.

## The proof

Each check is pinned by something that runs, and each pin was also run against a deliberately
altered scratch copy outside the repository, to see that it can report otherwise.

### The circular input

The selector's [adversarial suite](../../../tests/test_tester_1e_selector_adversarial.py) builds
graphs whose correct answer can be derived by hand. One gives a prime whose strong and weak bands
always land on different integer weights and requires that the selector admits no pair; another
requires that the stratum can be a true zero. With the `W_gap = 0` check deleted from the
selector, exactly those two checks fail. The 0.973 is not taken on trust either: counting the rows
of the frozen [arm (b) pair list](../../../experiments/results/priming_1e_pairs_arm_b_d1.txt)
whose `w_high` exceeds `w_low` gives 296 of 300, the file's SHA-256 matches the hash frozen in the
pre-registration, and the ceiling `1 − r_W` comes out at about 0.027.

### The missing division

`python3 experiments/fan_effect.py` reproduces the flat sweep, `0.2433743975` at every fan level,
and its verdict line reports that activation is flat across fan.
The [sweep's determinism test](../../../experiments/test_harness.py) runs that whole script in
fresh interpreters under eight hash seeds and requires byte-identical output. To show the
instrument can see a fan effect when one exists, `outgoing = node_act` was changed to
`outgoing = node_act / len(roads)` on a scratch copy of the engine. The same script then reported
activation halving with each doubling of the fan up to 8, then nothing at 16, where the value
falls below the activation floor, and its verdict changed to a match with the human direction. On the real engine, a direct call with `normalization_sigma=1.0` reproduced the
D-008 sweep value for value.

### The flat signal

`test_compute_friction_is_the_stall_fraction` in
[`tests/test_psyche_bodysensor.py`](../../../tests/test_psyche_bodysensor.py) pins the arithmetic:
`cpu == wall` gives 0.0, half the CPU gives 0.5, none gives 1.0. One part of the rule against
manufacturing a band is pinned in
[`experiments/test_exp2c_capture.py`](../../../experiments/test_exp2c_capture.py): the swept
friction levels are quantiles of the observed range and are never stretched toward the pilot's
near-saturated extreme. With the sweep widened to run from 0.0 to 0.999, the no-inflation checks
fail. No test forbids an injected wait; that part of the rule is held by the pre-registration, and
the same suite pins the 0.5 ms yield as a constant, so the sleep that made the band is on the
record.

## What this does not show

- **No phenomenon is shown absent.** Each statement is that the effect could not be measured
  under these controls, on this substrate, with this yardstick. Priming was not shown missing; it
  could not be told apart from a readback of the weights.
- **Nothing general follows.** This is a finding about one substrate and three yardsticks. It
  says nothing about spreading activation as a family, about word-association norms elsewhere, or
  about cognition.
- **The mechanisms were not found broken.** The missing division was a design choice of the engine,
  verified and documented. The interoception sensor and its hook passed their verification. Build
  status and meaning verdict are separate axes, read from the ledger and shown on the
  [substrate status page](https://cagancaliskan.github.io/psyche/status/).
- **The timing numbers are machine-specific.** The recorded band comes from one machine and one
  capture. The stall-fraction arithmetic does not depend on it. The statement that garbage
  collection counts as CPU time rests on the record's reasoning, and no test measures it.
- **The flat fan response is measured on a star.** That it holds for other graph shapes rests on
  reading the transmission code, where convergent activation sums at a target.
- **It says nothing about stage 2.** Stage 2 shares no model code with the substrate
  ([Origins](../../research/origins.md)).

## The general lesson

Each of the three answers rules out a different repair. A larger sample leaves a ceiling set by the
input where it is. A better stimulus set cannot supply a mechanism the engine lacks, and a larger
workload does not move a ratio. Reading the three as one result would have pointed at the wrong
lever every time. Asking at which point of the pipeline a test can be trusted (input, mechanism or signal) can be
answered before any graded data exists.

The second lesson is about timing. All three answers came from checks written before the run: a
weight-blind stratum with a floor, a feasibility pre-check, a rule against widening the signal. Any
of the three experiments could have been run anyway, and each would have printed a number that
looked like a result: a priming separation that might be the weight map read back, a fan curve
made by an engine change chosen to make it, a selection shift whose driver was a sleep. The
project counts a pre-registered stop caught before a graded run as a first-class result
([contributing guide](../../../CONTRIBUTING.md)), and these three are why.

## Further reading

- [The three walls](../../three-walls.md): the reference page for all three experiments, with the
  works they cite.
- [EXP-1e](../../experiments/EXP-1e-priming.md), the frozen priming pre-registration, and its
  section 15 outcome.
- [The fan-effect specification](../../specs/SPEC-fan-effect.md) and its feasibility pre-check.
- [EXP-2c](../../experiments/EXP-2c-interoception.md), the interoception pre-registration, with
  its corrected provenance and band-design finding.
- [`DECISIONS.md`](../../../DECISIONS.md): D-003, D-004 and D-005 for the three decisions, D-008 and
  D-009 for the normalisation overlay.
- [Architecture](../../ARCHITECTURE.md), section 9, on the body-state sensor, and
  [Methodology](../../METHODOLOGY.md).
- [The fan-effect characterisation](../../../experiments/FAN_EFFECT.md), the earlier exploratory
  sweep.
