---
name: psyche-prereg
description: Write a frozen pre-registration for any Psyche/Nous experiment that will produce a graded number, and run the anti-circularity gate before a single number is computed. Use for every meaning-bar attempt, every cognitive claim, and every validator experiment. Encodes the reasoning that produced three correct NO-GOs before wasted graded runs.
argument-hint: "[brick-id] [short experiment name]"
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, WebSearch, WebFetch
---

# Pre-registration — freeze the prediction before the number exists

This project's most valuable output so far is three experiments it **refused to run**. Each
was caught by a gate that fired before any graded number existed. That is not caution; it is
the only thing separating this work from a system graded on inputs chosen to make it
succeed.

Target: **$ARGUMENTS**

Write to `docs/experiments/EXP-<brick>-<name>.md`. Commit it **before** running anything.

---

## The gate — run this first, and be willing to fail it

Three walls have been hit. Before designing anything, check the new experiment against all
three. If it hits one, say NO-GO and stop; that is a result, and it belongs in the roadmap.

### Wall 1 — CIRCULAR (killed 1e priming)

*Is the prediction variable the same thing as, or a deterministic function of, something
the substrate was built from?*

1e loaded SWOW association strength **as the edge weight** (`W = min(10, 1+floor(s·100))`).
So "related targets activate more" was the weight map read straight back out. Worse: because
strength is a function of `traverse_count` and `W` is a function of `traverse_count`, a
weight-tied pair was **activation-tied by construction** — the leverage stratum had no
direct-path signal at any sample size.

**Ask:** if I froze the mechanism and predicted the outcome from the input data alone, would
I get the same answer? If yes, the experiment measures the data, not the system.

**Ask also:** is there a stratum where the trivial baseline predicts *exactly zero*
separation, and can that stratum actually populate? Compute its expected size **before**
committing — do not reason your way to "it will populate." 1e's structural optimism predicted
a healthy stratum; the blind run returned `N_S0 = 7`.

### Wall 2 — MECHANISM ABSENT (killed the fan effect)

*Does the engine contain the mechanism that generates the effect?*

The fan effect is a shared-budget/normalization phenomenon. The engine gave every out-road
the source's full activation, so the fan curve was flat to the last digit at every layer.
There was no signal to grade, circular or otherwise.

**Ask:** name the specific line of code that would produce a difference. If you cannot point
at it, the effect is absent, not merely small.

**And:** adopting a mechanism *in order to* produce the effect does not earn it. The
mechanism must be justified independently and the effect must then fall out untuned.

### Wall 3 — SIGNAL FLAT (killed the 2c timing pair)

*Does the external signal actually vary, on realistic work, without being manufactured?*

`friction = 1 − cpu/wall` is a stall fraction. A realistic `think()` is ~47 µs of pure CPU,
so friction ≈ 0, and it is scale-invariant. The only gradable band came from an injected
sleep — manufactured, and forbidden.

**Ask:** measure the yardstick's range on realistic work *before* designing around it. If a
gradable range requires injecting something, the range is manufactured and the run is void.

**Ask also:** would a null be interpretable? If a NOT-YET could not distinguish "no effect"
from "the yardstick barely moved," the experiment cannot be run either way.

---

## The document

Write these sections, in this order. Sections 1–8 are frozen before any number.

**§1 The claim.** One paragraph, precise. What is asserted, in what direction, graded
against what external source. State plainly what it is **not** a claim of — understanding,
concepts, awareness, semantics.

**§2 The direction, fixed in advance.** The known human/external direction with citations.
State the reversal that would falsify it.

**§3 The external source.** Published, cited, fetched, and not authored by this project. If
you cannot find one, stop and say so — hand-authored data voids the result.

**§4 Design.** Arms, conditions, what is held constant in each, and which confound each arm
closes. If one arm alone cannot close both confounds, say so and require the conjunction.

**§5 Metric.** The exact readout, and its named cost. (1e's headline metric could only see
targets inside the winning coalition; that limitation was stated in advance and was a
candidate reason for a null.)

**§6 The anti-circularity gate.** The stratum or control that separates a genuine result
from the trivial baseline. Its expected population size, computed not assumed. What makes it
VOID rather than NOT-YET.

**§7 Thresholds.** Every number that decides the verdict, fixed now: effect sizes, sample
floors, significance levels, and the conjunctive verdict rule. **No post-hoc loosening,
ever.** Record the fallback and check its arithmetic ceiling — 1e's fallback needed a
rank-biserial of 1.17 against a maximum of 1.0, which was unreachable before any data.

**§8 Falsifiers.** What outcome would make you say NOT-YET. What would make the run VOID
(instrument failure) rather than a result. These are different and both must be named.

**§9 Freeze.** Selection seeds, commit hash, SHA-256 of every stimulus artifact. The runner
must verify the hashes and refuse to run on any other set.

**§10 Result.** Written after. If a gate fired, record the NO-GO with the structural reason
and the numbers that produced it. **A NO-GO caught before a graded run is a first-class
result and goes in the roadmap.**

---

## Rules that have teeth

- **No threshold moves after a number is seen.** Record explicitly that none did.
- **A null is a result.** Report it, cite it, put it in the roadmap.
- **Report what you could not measure**, not just what you did. If a stratum was thin, say
  how thin and why, in numbers.
- **Scope every finding.** It is a finding about *this substrate and this yardstick*, never
  a general law about spreading activation or cognition.
- **Direction comes from the engine's code, not the spec's prose.** SPEC-2c's prose had the
  sign backwards relative to the implementation; the pre-registration caught it by reading
  `transmitted = outgoing * road.strength * decay_per_hop` directly. Read the line.

## Close with

The verdict rule in one sentence, the single next action, and where this leaves the roadmap.
