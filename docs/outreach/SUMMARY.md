# Nous: a one-page summary

**What it is:** Nous is a dependency-free Python prototype of a memory-and-activation substrate
for a cognitive architecture, presented as much as a software-testing-methodology case study as an
engineering artifact: a small system built test-first, in which adversarial testing caught a
sequence of real structural bugs. It is not a mind, a consciousness, an AGI, or a validated
cognitive model; the neuroscience it borrows vocabulary from is conceptual inspiration only.

**The four layers:**

- **Substrate store:** a graph of concept *nodes* and weighted *roads* with
  consolidation-inspired dynamics, lazy activity-dependent decay, and "sticky" closure of edges.
- **Spreading activation:** a deterministic engine that records per-edge flow and treats closed
  roads as leaky rather than inert.
- **Multi-source field:** runs activation from several sources at once and assigns each node to the
  source that activates it most.
- **Perceive then think slice:** a first end-to-end pass from input text to a single selected
  "thought."

**Proven vs. exploratory:** The lower two layers (store and activation) are rigorously tested for
three properties. *Determinism:* identical results across process runs, including under randomized
hash seeds checked in fresh subprocesses. *Integrity:* graph indices and adjacency stay mutually
consistent across every mutation. *Purity:* reads never mutate stored state. These are claims about
mechanism. The upper two layers (the field and the "thought") run and are deterministic, but their
*cognitive meaningfulness is explicitly not claimed.* The full suite is **1,372 assertions across
20 suites, all passing**, including the independent tester-authored adversarial suites.

**The central methodology finding:** One failure mode recurred at every layer. A component would
*pass on a friendly, hand-built input* and break only under adversarial testing, or once the loop
was closed so its inputs were system-generated instead of hand-chosen. Six structural bugs were
caught this way: a read that secretly wrote, double-counting where paths converge, hash-seed
nondeterminism, an identity and ordering leak, a binding step that always produced exactly one
group, and circular validation from hand-placed sources.

**The honest negative result:** When real perception lights up several nodes in the *same* domain,
the field's basins collapse: one source over-swallows across domains while same-domain siblings
strand alone, and the resulting "thought" is incoherent. This is not hidden. It is asserted as a
known-limitation test that flips to green only if the underlying problem is solved.

**The next step:** Stop validating the cognitive layer against hand-built inputs, and instead test
it against a *measurable* cognitive effect whose direction is known independently of Nous, for
example **semantic priming** [10, 11]: does pre-activating a related concept measurably raise a
target's activation?

**The ethos:** this part is proven; that part is not, and here is the failing test that says so.

Report (open access, CC BY 4.0): https://doi.org/10.5281/zenodo.20474613
