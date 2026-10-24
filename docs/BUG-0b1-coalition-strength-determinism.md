# BUG-0b1 — the competition tie-break is unreachable: `Coalition.strength` leaks
# float-summation order into the winner

**Status:** FOUND · REPRODUCED · FIXED at its site · fix verified against the full canonical suite ·
**§5 and §7 amended 2026-07-25 after the tester found the same bug class upstream — see §8**
**Found:** 2026-07-25, while establishing a baseline before the SPEC-0b2 engine work
**Severity:** the cross-process determinism property of the workspace competition (Tier 2)
does not hold. ~~Tier 1 (`psyche_store`, `psyche_activation`) is **not** affected.~~ **That
sentence is retracted:** `psyche_store` is not affected, but `psyche_activation` carries the same
hazard at its accumulation site (DEFECT-A, §8), and the fix here does not reach it.
**Caught by:** the project's own existing adversarial test —
`test_tester_1d_i_adversarial.py::test_T6b` ("multi-basin tie graph identical across 6 seeds").
The test was correct and it fires. It had never been run on an interpreter that exposes the bug.

---

## 0. Why this document exists before SPEC-0b2

SPEC-0b2 changes how transmitted activation is computed, which changes every float that
enters `Coalition.strength`. Landing a representation change on top of a latent
summation-order bug would make the change's effects and the bug's effects
indistinguishable. This must land first, on its own, as its own brick.

---

## 1. The observation

On CPython **3.11**, at a **fixed** `PYTHONHASHSEED=0`, running the T6b probe 30 times in
fresh processes returns **two different winners**:

```
  22 / 30   winner = ('alfa', 'bravo', 'charlie')
   8 / 30   winner = ('delta', 'echo', 'foxtrot')
```

On CPython **3.12** and **3.13**, 30/30 runs return the same winner. The project's captured
output was produced on 3.12, so the suite has always been green.

This is not hash-seed leakage. It varies **run to run at one fixed seed**, which rules out
the failure mode the project already hardened against.

## 2. Root cause

> **CORRECTION, 2026-07-26 (D-014) — this section said "two sites" and it was wrong.**
> There are **three** `Coalition(` construction sites in `src/`, not two:
> `psyche_coalitions.py:228`, `psyche_coalitions.py:311`, and **`psyche_workspace.py:426`**, which
> builds the *pruned* winner with `strength=sum(pruned_members.values())`. That third site
> was never converted, so this bug was reported as closed while a live instance of it
> remained **on the same competition path**. It is reproduced in SPEC-0c §2.5.1: on the
> post-0c working tree, at a **fixed** `PYTHONHASHSEED=0`, 30 fresh processes give two
> distinct strengths on python3.10 (6 / 24) and one on python3.14 — the same
> invisible-on-the-newer-interpreter signature this report describes below, for the same
> reason, now explained (see §9). Winner *identity* is stable on that graph, which is
> exactly how the original instance hid too. The site is converted in brick 0c.
> Nothing else in this report is affected: the diagnosis, the mechanism and the fix applied
> at the two `psyche_coalitions.py` sites were correct as far as they went. What was wrong was
> the claim of completeness.

`src/psyche_coalitions.py`, two sites (lines 225 and 308) — **and see the correction above; a
third site in `psyche_workspace.py` was missed**:

```python
strength = sum(members.values())
```

`members` is `Dict[NodeID, float]`. `NodeID` is uuid4. `.values()` therefore yields
activations in an insertion order that traces back to iteration over uuid4-keyed
containers upstream. **Float addition is not associative**, so two mathematically
identical coalitions produce sums that differ in the **last unit in the last place**
depending on the order the terms were added.

Instrumenting the pre-sort keys on 3.11 shows exactly this:

```
run 1   delta   key=(-0.5861157631335455, -3, 3)     <- delta's density is 1 ULP larger
        alfa    key=(-0.5861157631335454, -3, 0)        -> delta wins
run 3   alfa    key=(-0.5861157631335455, -3, 0)     <- exact tie
        delta   key=(-0.5861157631335455, -3, 3)        -> creation_seq breaks it, alfa wins
```

The consequence is the load-bearing part:

> **`_competition_key`'s `min creation_seq` tie-break is unreachable in practice.** It
> only runs when two densities land on the *same bits*. A 1-ULP difference resolves the
> comparison first, and which coalition receives the larger float is not a property of
> the graph.

The docstring on `_competition_key` states the intent correctly — *"Every key is
intrinsic and reproducible; none falls back to a uuid — identical across process runs."*
The key is fine. The **inputs** to the key are not.

Two things hid this:

1. **The suite's probes round.** T6b prints `round(c.strength, 9)`; the ULP difference is
   at the 16th significant figure. The reported strengths are identical in every run. Only
   the *winner identity* changes, which is why the assertion that catches it is a
   whole-output equality check and not a numeric comparison.
2. **Single-interpreter coverage.** Determinism was checked across 6 hash seeds and fresh
   processes, but always on one CPython minor version. The randomisation axis the project
   hardened against was hash seeding; the axis that actually mattered here was the
   interpreter's container layout, which hash seeding does not sweep.

## 3. The fix

```python
strength = math.fsum(members.values())
```

`math.fsum` is exactly rounded, therefore **order-independent by construction**, therefore
the density comparison becomes a pure function of the multiset of activations and the
`creation_seq` tie-break becomes reachable. Standard library, so the dependency-free
constraint holds.

Rejected alternative: sorting `members` before summing. Sorting by `NodeID` is wrong
(uuid4, not stable across processes); sorting by `creation_seq` would work but adds a
lookup and still leaves plain `sum` associativity-sensitive to future refactors. `fsum`
removes the failure mode rather than avoiding it.

## 4. Verification

| Check | Result |
|---|---|
| T6b probe, 40 runs, fixed `PYTHONHASHSEED=0`, CPython 3.11 | 40/40 identical |
| T6b probe, 6 seeds × 3 runs, CPython 3.11 / 3.12 / 3.13 | 1 distinct output on each |
| Full canonical suite, CPython 3.11 / 3.12 / 3.13 | green on each; no assertion added, weakened or removed |

<!-- ledger:allow-count -->
*Canonical run at the moment the fix landed, retained as a labelled snapshot: 20 suites / 1,372 assertions / 0 failures, on each of CPython 3.11, 3.12 and 3.13. The current figure is in `tools/ledger.json`, and the sweep has since widened to five CPython minor versions (D-010).*

## 5. What this does and does not mean

**Does not affect the Tier 1 `PROVEN` claim.** `psyche_store` and `psyche_activation` are
untouched; the paper's engine-determinism sentence is about the store and the spread, and
`spread_activation` accumulates convergent activation as a commutative sum into a dict per
target — the value at a node does not depend on arrival order. Only the *aggregation across
members* in `psyche_coalitions` was order-sensitive.

> **RETRACTED 2026-07-25 — this paragraph was wrong, and §8 records how it was caught.** The
> accumulation in `spread_activation` is commutative in exact arithmetic and **is not commutative in
> floating point**. Where three or more contributions converge on one node, the value at that node
> *does* depend on arrival order, and arrival order comes from iterating a set of uuid4 ids. The
> tester reproduced two distinct results across 48 fresh processes at library defaults. The
> conclusion "does not affect the Tier 1 claim" therefore does not follow from the reason given
> here; whether the Tier 1 claim survives is an open decision (D-011), not something this document
> may assert. What remains true is narrower: **the fix in §3 is correct at its own site**, and `0a`
> (`psyche_store`) is not implicated.

**Does affect the Tier 2 mechanism claim** for the workspace competition, for the interval
during which the suite was reported green on 3.12 while the property did not hold on 3.11.
The honest statement is: the property holds now, on three interpreters; it did not hold
before, and the project's own test would have said so under wider coverage.

## 6. The methodology consequence — this is the interesting part

The paper's third practice is adversarial and property-based testing: *"asserts invariants
designed to break a claim rather than to confirm it."* That practice **worked**. T6b was
written to catch exactly this class of bug, it targets exactly the right graph (a genuine
density + size + strength tie resolvable only by `creation_seq`), and it fails the moment
it is given an environment that exposes the leak.

What failed is narrower and worth naming precisely: **an invariant asserted over a
randomisation axis you sweep is only verified over the axes you sweep.** The project swept
hash seeds because that was the known leak. Container layout across interpreter versions is
a second axis, it is not reachable by `PYTHONHASHSEED`, and it was not swept.

Proposed addition to the methodology, stated in the paper's own register:

> A determinism claim is scoped to the execution environments it was checked in. Where the
> claim's stated purpose is that results do not depend on incidental runtime state, the
> environment axis — at minimum the interpreter minor version — belongs in the sweep
> alongside the hash seed. A property that holds on one interpreter and fails on another
> was never a property of the program.

Concretely, in `run_tests.py`: run the determinism probes under every CPython minor version
available on the machine, not only the one the runner is invoked with, and record the set
of versions in `TEST_OUTPUT.txt` next to the seed set.

This is a genuine strengthening of the paper rather than a retraction from it: the
methodology section already qualifies itself with *"the discipline is reported as what it
did, not as a guarantee"*, and this is one more thing it did — it caught a real bug the
moment the coverage widened.

## 7. Known limitation this leaves standing (as an asserted-negative candidate)

`fsum` makes the *sum* order-independent. It does not make every downstream float
comparison exact. Any future scoring path that compares two independently-accumulated
floats for strict inequality inherits the same hazard class. The durable form of the fix is
the one already in the code's intent: **make every comparison resolve on an intrinsic
integer before it resolves on a float**, or compare floats only through an explicit
tolerance with the integer key beneath it. `_competition_key` is now correct because its
float component is exact; it is not correct because floats are safe to compare.

Suggested new asserted-negative, in the tester's lane: a probe that constructs two
coalitions whose densities differ by exactly 1 ULP and asserts that the *documented*
tie-break policy is what decides the winner — so that if a future change reintroduces
ULP-scale asymmetry, the test names it rather than the winner silently flipping.

## 8. The limitation was not future — it was already upstream (recorded 2026-07-25)

§7 named the hazard class as something a *future* scoring path could inherit. The tester's
independent SPEC-0b2 suite (`tests/test_tester_0b2_adversarial.py`, five interpreters, six hash
seeds) found it **already present, one layer up**, and reported it as **DEFECT-A**.

**The site.** `src/psyche_activation.py:287`:

```python
activation[target] = activation.get(target, 0.0) + transmitted
```

a naive sequential float add, whose term order comes from
`roads_from() -> iter(tuple(self._out[node_id]))` — iteration over a **set of uuid4 hex strings**
(`src/psyche_store.py:444`). Same bug class as this one: an order-dependent float sum feeding a
comparison. Determinism holds bit-exactly at in-degree ≤ 2 and breaks when **three or more**
contributions converge on one node.

**The evidence.** At library defaults, on a 5-node graph built by `traverse()` alone
(S → M0, M1, M2 → T; traverse counts (1,2), (1,3), (1,9)), **48 fresh processes produced two
distinct results**: `0.10145973529004966` and `0.10145973529004967`. It reproduces with the 0b2
overlay off, so 0b2 neither caused nor fixed it.

**What this does to the fix in §3.** The fix is still correct at its site: `math.fsum` makes
`Coalition.strength` order-independent *given its inputs*. But those inputs are node activations
produced upstream, and on in-degree ≥ 3 graphs they are themselves 1-ULP-unstable across processes.
**An order-independent sum of order-dependent terms is order-dependent.** So the competition's
cross-process determinism is restored only for graphs where no node has three or more incoming
contributions — which is not a restriction the project ever stated.

**Two methodological consequences, both sharper than §6's.**

1. **Pinning `PYTHONHASHSEED` cannot establish determinism for this substrate.** uuid4 ids differ
   per process, so a fixed seed does not fix set-iteration order; DEFECT-A varies at a *fixed* seed.
   §6 proposed widening the environment axis to interpreter versions, and that was right but not
   sufficient — the randomisation that matters here is inside the *ids*, not inside the interpreter.
2. **The project's determinism probes cannot see a bug of this size.** Every pre-existing
   determinism probe in `tests/` compares `round(x, 9)`. The difference here, like the one this
   document is about, is at the last unit in the last place. A probe that rounds cannot fail on
   1 ULP. The tester's new suite compares **bit patterns** throughout, and that change of resolution
   is what surfaced it.

**Status.** DEFECT-A belongs to brick `0b`, not to `0b1` and not to `0b2`. It contests Phase 0's
`PROVEN` label, and that call — with its re-validation cost — is the project lead's, recorded as **D-011** in
`DECISIONS.md`. Nothing is re-labelled here on a lane's own initiative.

---

## 9. Postscript, 2026-07-26 — why this bug was invisible on 3.12, and where an instance survived

Two things were unexplained when this report was written. Both are now settled, and each is
recorded here because a bug report that leaves its own key fact unexplained invites the next
reader to guess.

**(a) The interpreter split has a cause, and it is not mysterious.** This report records the
failure as reproducing on CPython 3.11 and being invisible on 3.12 without saying why.
The reason: **CPython 3.12 changed the builtin `sum()` to Neumaier compensated summation for
floats.** Reproduced across all five interpreters on the project machine, over
`[1.0, 1e-16, 1e-16, 1e-16]`: `sum() == math.fsum()` is **False** on 3.10.17 and 3.11.15 and
**True** on 3.12.4, 3.13.14 and 3.14.4. Since the fix here was exactly `sum(...)` →
`math.fsum(...)`, the pre-fix code was **accidentally correct on 3.12+ and naive on 3.11**.
That is the whole of the version-dependence. It also means any surviving naive float `sum()`
in this project is a value that depends on which interpreter runs it — which is the general
form of the defect, and why SPEC-0c §2.5 converts every one of them.

**(b) An instance survived on the same path, for four weeks.** See the correction in §2:
`psyche_workspace.py` builds the pruned winner's strength with a naive `sum()`, and this
report's completeness claim missed it. The instructive part is *how* it survived: the
`Coalition.members` order it inherits comes from `by_basin[src]` — a `Set[str]` of uuid4
NodeIDs built in `psyche_coalitions.py`, not from the store's adjacency index. So brick 0c's
store-ordering fix does not reach it. **Fixing a class at one owner does not fix it at
another owner**, and a report that says "two sites" without a mechanical check that there
were only two is an assertion, not a finding. SPEC-0c §2.5.2 records the corresponding
lesson for the spec: 0c's own falsifier exercised only the activation accumulator, so the
brick whose purpose is closing this class would have shipped with a live instance of it.

**Status, updated.** DEFECT-A belongs to brick `0b`. The label question was resolved in
**D-012**: Phase 0's `PROVEN` label is withdrawn, and both `0a` and `0b` now carry
`BUILT · UNVALIDATED` — restored only after the repair brick is built and re-verified.
The third-site correction and the conversion of the remaining naive sums are **D-014**,
folded into that same repair brick, which is specified in
`docs/specs/SPEC-0c-deterministic-road-ordering.md`.
