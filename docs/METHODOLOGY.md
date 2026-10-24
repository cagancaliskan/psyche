# Psyche: Methodology: adversarial testing caught structural bugs

This is the most transferable part of the project, and the one whose claims are easiest to
check, so it is written to be checkable. **Every factual claim below is traceable to the code
in `src/` and the tests in `tests/`**: module docstrings, specific test functions, and the
assertions they make. It does **not** draw its bug history from the aspirational design notes in
`docs/design/`; those describe intent and may narrate things the code does not do. (For the
record, those notes state an intent to refuse laundering unfinished work into finished work; the
history below is told only from the code and tests, and you can re-run them.)

Where an original development log reported a *magnitude* of error that the shipped artifact does
not let you reproduce (e.g. "the over-count was about X%"), that magnitude is **omitted** here
rather than asserted: what remains is the mechanism and the specific test that now locks the fix.

## Central claim

Each component was built **test-first**, and each suite includes **adversarial tests:** tests
written to *break* the claim, not to confirm it. Two properties were treated as first-class and
verified directly: **determinism** (identical output across process runs, including under
randomized `PYTHONHASHSEED` in fresh subprocesses) and **read-purity** (reads never mutate stored
state). This discipline caught a sequence of **structural** bugs: bugs in the shape of the
algorithm, not typos, that ordinary happy-path tests would have passed straight over. The same
discipline, applied honestly, also drew the boundary this project refuses to cross: it shows the
substrate and activation layers are correct and deterministic, it shows the higher layers
(field, coalitions, source-clustering, workspace) are tester-verified **as mechanism** — enough
to close the cognitive cycle end-to-end — and it shows that **no cognitive meaning has been
earned** above the substrate. The closing sections below carry the same two practices into the
cycle that closed the loop (findings (g) and (h)); they add a *mechanism* result, not a cognitive
one.

## How the tests are built to break things

- **No pytest; a tiny harness with explicit checks:** Each suite counts `check(...)` /
  `expect_raises(...)` calls and exits non-zero on any failure. (Notably, this means the suites
  must be run as scripts: under pytest a logical `check(False, …)` would not raise and could be
  reported green. The honest runner is `run_tests.py`.)
- **Determinism is tested across processes, not within one:** The determinism tests spawn fresh
  interpreters with different `PYTHONHASHSEED` values and compare byte-for-byte. This is the only
  way to catch nondeterminism that comes from hashing uuid4 keys, because within a single process
  the hash seed is fixed. See `test_determinism_with_same_hop_edge_adversarial` (activation, seeds
  `0,1,3,7,42`), `test_determinism_adversarial_across_hash_seeds` (coalitions, 8 seeds),
  `test_field_determinism_adversarial_across_hash_seeds` (field, 8 seeds),
  `test_slice_determinism_across_hash_seeds` (slice, 6 seeds).
  > **Amended 2026-07-25 — two limits of this practice, both found by adversarial testing of it.**
  > (i) **Sweeping hash seeds is not sufficient here.** uuid4 ids differ per *process*, so pinning
  > `PYTHONHASHSEED` does not pin set-iteration order; a real defect (DEFECT-A, BUG-0b1 §8) varies
  > at a *fixed* seed. Fresh processes are what catches it, and the seed sweep is a weaker
  > guarantee than it reads as. (ii) **Comparing `round(x, 9)` cannot see the bug this project
  > actually has.** Every pre-existing determinism probe rounds; both real determinism defects found
  > so far were 1 ULP, at the 16th significant figure. A probe's *resolution* is part of its
  > coverage. The tester's 0b2 suite compares bit patterns throughout, and that is the change that
  > surfaced DEFECT-A.
- **Adversarial inputs, not friendly ones:** The clustering and field acceptance tests use a
  two-dense-communities-joined-by-a-thin-bridge graph built specifically to defeat distance-based
  segmentation (`test_acceptance_multisource_recovers_communities`,
  `test_single_seed_spread_yields_multiple_coalitions`).
- **Purity is hammered:** Read-only operations are run in tight loops and the full canonical
  (un-decayed) store state is asserted byte-equal before and after
  (`test_reads_are_pure`, `test_spread_is_pure_read`, `test_coalition_formation_is_pure_read`,
  `test_field_coalitions_are_pure_read`, `test_slice_is_pure_read`).

---

## The six structural findings

### (a) Read-as-write: a read that mutated state could silently re-open a closed wound
**The claim under test:** reads are pure; stored state changes only on writes.
**The bug:** roads decay with elapsed time, and the natural implementation applies that decay
*on access* and writes it back, so every read mutated the store. Worse, if decay also
re-evaluated closure, repeated reads over time could let a *closed* (traumatic) edge drift back
open, with no crossing ever having reopened it.
**Root cause:** conflating "compute the current value" with "persist the current value," and
letting a passive read touch a state (`closed`) that should only change on an active event.
**The fix (in `psyche_store.py`):** decay is split into a pure view and a persisting write.
`_compute_decay(road, now)` returns decayed `(strength, charges)` **without mutating**;
`get_road(apply_decay=True)` returns a **copy** carrying those values (docstring: *"a decayed
VIEW: a copy, so the read does not persist anything"*). Only `_persist_decay` mutates, and it is
called *only* by `strengthen`/`traverse`/offline passes. Decay deliberately **does not** touch
`closed`: closure is **sticky**, re-evaluated only by `_open_close_on_crossing` on an active
crossing.
**Locked by:** `test_reads_are_pure` (20 reads across `get_road`/`quality_of`/`neighbors`/
`roads_from` change *nothing* stored), `test_lazy_decay` (the read view shows decay while the
canonical stored value is unchanged), `test_closure_is_sticky` (time + repeated reads do **not**
reopen a closed road; only an active positive return does).

### (b) Convergence double-counting: importing "first-pop-final" where activation *sums*
**The claim under test:** a node downstream of a convergence point is not over-counted.
**The bug:** when activation converges on a node from several paths it must **sum**, but if the
node is then re-expanded as later paths raise its value, everything downstream of the convergence
point is counted multiple times.
**Root cause (named in the code):** importing **Dijkstra's "first-pop-final" intuition** into an
algorithm where activation *accumulates* rather than being a shortest-path minimum. The
`psyche_activation.py` docstring calls the earlier draft's structure out directly.
**The fix:** **bounded single-expansion**, hop-layered: each node expands exactly once, at the
first hop it is reached, carrying the full sum of all paths of length ≤ that hop. Equal-length
convergence is therefore **exact** (not a coincidence of edge strengths).
**Locked by:** `test_no_double_count_downstream_of_convergence`, which builds a diamond-with-tail
with **deliberately lopsided** edge strengths (`a→b` strong, `a→c` weak) *to prove the result does
not depend on them*, asserts the convergence node sums both equal-length in-paths exactly, asserts
the downstream child receives the full value exactly once, and includes an explicit guard that the
result is **strictly below** what additive re-expansion would have produced (the old bug's
signature). `test_convergent_activation_sums` separately confirms convergence does sum.

### (c) Order-dependence, then nondeterminism: a priority frontier + hash-randomized sets
**The claim under test:** post-convergence activation depends only on the graph, never on
expansion order or process hash seed.
**The bug:** an activation-priority (best-first) frontier made *which* late ripple got dropped
depend on incidental edge-strength ordering; and with same-hop edges, whether one sibling expanded
before another was decided by iterating a `set` of uuid4 strings: whose order is randomized per
process by `PYTHONHASHSEED`. So results swung across process runs for no cognitive reason.
**Root cause:** letting expansion order be load-bearing for the result, over a container whose
iteration order is intentionally randomized.
**The fix:** **hop-layered expansion with per-layer frozen values:** All hop-k contributions
accumulate before any hop-k node expands; the layer's expansion values are **frozen** into a
snapshot first, so an intra-layer edge's contribution lands in the target's accumulation but
propagates onward only in the *next* layer. Expansion then reads only the frozen snapshot: there
is no place left where live-mutation order can leak in. (This is also the *truer* model: a
radiating wave is hop-ordered by nature.)
**Locked by:** `test_expansion_is_deterministic_under_edge_strength` (same topology under
lopsided / moderate / balanced strengths must give the same relationship of the downstream node to
the convergence node's full value), and the decisive `test_determinism_with_same_hop_edge_adversarial`,
which builds an **intra-layer** edge (`a→b`, `a→c`, `b→c`, `c→f`) and then re-runs the spread in
fresh interpreters under `PYTHONHASHSEED ∈ {0,1,3,7,42}`, asserting the result is **byte-identical**
across seeds: the check that actually catches per-process uuid-set nondeterminism.

### (d) Identity/order leak: tie-breaking on a uuid that is regenerated every run
**The claim under test:** coalition output (partition, ordering, representatives) is identical
across processes.
**The bug:** coalition ordering and representative-selection tie-broke on the node's id, but ids
are `uuid4`, **regenerated every process run**, so any tiebreak that fell back to the id was
nondeterministic across processes even when the coalition *structure* was identical.
**Root cause:** using identity (which is intentionally non-stable across runs) to carry ordering.
**The fix:** tie-break on the stable **`creation_seq`** integer (formation order, persisted store
data, deliberately kept separate from identity in Layer 1 precisely so identity never has to carry
ordering). `Coalition._seq` maps each member to its `creation_seq`; `representative()` orders by
`(−activation, creation_seq)`; the coalition sort key is `(−strength, −size, min creation_seq)`.
**Locked by:** `test_determinism_adversarial_across_hash_seeds`, which builds a **ring** of equal-
activation nodes (many equally-valid traversal orders) plus tie-strength singletons (so any sort
leaking set order would diverge), serializes the full structure by **stable** keys (content +
`creation_seq`, never uuid), and asserts identity across 8 hash seeds; and
`test_representative_is_most_active_deterministically`.

### (e) Binding degeneracy: connected-components on a graph that is connected by construction
**The claim under test:** coalition binding subdivides a co-activated region into the *right*
groups.
**The bug, in two stages:** (1) **Connectivity binding is structurally degenerate:** Every
co-activated node got its activation by being reached from the seed along carried edges, so the
co-activated subgraph is **connected by construction:** and connected-components on a connected
graph is always **one** component. A single-seed spread would therefore essentially always yield a
single coalition, leaving the downstream competition with one contestant. (2) **Flow-magnitude
cutting subdivides, but keys off the wrong thing.** Cutting weak-flow edges does break the region
into more than one coalition, but for a *single* seed the only strong signal is **distance from
the seed**, and flow-magnitude is even **anti-correlated** with community membership near the seed
(a bridge edge adjacent to the seed carries *more* flow than distant intra-cluster edges, so it is
preserved while genuine internal edges are cut).
**Root cause:** a single seed produces one activation peak and monotonically-decaying flow, so any
segmentation rule applied to it keys off distance, not community structure.
**The fix:** keep flow-cut as the single-seed segmenter (it does satisfy the "more than one
coalition" property), but recognize the real problem is **upstream** of the algorithm and reframe
to a **multi-source field** (`psyche_field.py`): multiple sources → multiple genuine peaks → basins
around peaks, where a node bridging two concerns goes to whichever pulls it harder, so seams fall
*between* centers.
**Locked by:** `test_single_seed_spread_yields_multiple_coalitions` (flow-cut yields > 1 coalition
on a *real* single-seed spread: the degeneracy of stage 1 is gone) and
`test_acceptance_multisource_recovers_communities` (the multi-source field recovers exactly the two
communities on the adversarial bridge graph that single-seed segmentation could not).

### (f) Circular validation: the answer was hand-encoded in the input
**The claim under test:** the cognitive layer works on input the *system* produced, not on input
chosen to make it work.
**The bug:** every layer above the substrate had been validated against a *fiction* of what would
feed it. Sources were **hand-placed**, "it works" kept meaning "it works on my guess of the
input," and this culminated in the field acceptance test recovering two communities **only because
one source was hand-placed at the center of each**: the answer was encoded in the input. (This is
visible in the artifact itself: `test_acceptance_multisource_recovers_communities` does place one
source per community by hand. It is honest as a *mechanism* test and dishonest if read as evidence
the system finds communities on its own.)
**Root cause:** validating a stage against inputs invented to produce the desired output.
**The fix:** **close the loop** with the thinnest real vertical slice (`psyche_perceive.py`):
`text → perceive() → sources → field → coalitions → thought`, where *which* nodes become sources is
decided by the input matched against the substrate, **not** chosen by the test. Run on real
clustered input, the field then produces an **incoherent** "thought": basins collapse, one source
over-swallows across domains, and same-domain sibling sources strand as singletons.
**Locked by: as a *limitation*, not a result (at the time of finding (f)):**
`test_KNOWN_LIMITATION_clustered_sources_give_poor_basins` *asserted the failure on purpose*: it
confirmed real input named three sources in the same domain, then asserted the "thought"
over-swallows (pulls in the work domain) **and** that a perceived same-domain source strands as a
singleton. The test was written so it would **flip to green only when source-grouping was actually
fixed**: the limitation was encoded as a standing, checkable claim rather than a comment.
**It has since flipped** — see finding (g) below: source-clustering and workspace pruning resolved
both halves at the mechanism level, and the assertion was re-expressed as the now-passing behavior
(one residual cohesion-valley corner case remains, shipped as an asserted-negative). This finding
records the bug as discovered; finding (g) records its resolution.

---

## The recurring failure mode, and the meta-lesson

Read findings (b)–(f) together and the same shape repeats: **a component passes on a friendly,
hand-chosen input and fails on an adversarial or system-generated one.** Each fix had two parts:

1. **Adversarial testing:** write the test that tries to break the claim (lopsided strengths,
   intra-layer edges, equal-activation rings, two-community bridges, cross-process hash seeds), not
   the test that confirms it on an easy case.
2. **Closing the loop:** make the inputs *system-generated* rather than hand-chosen, so a stage can
   no longer be validated against a fiction of what feeds it. Finding (f) is this lesson applied to
   the whole pipeline at once.

The honest boundary that falls out of this:

> **Proven:** the substrate store and the spreading-activation engine are **deterministic**,
> **integrity-preserving**, and **pure** (verified, including across process hash seeds).
> **Amended 2026-07-25:** the determinism half of that sentence is **contested for the activation
> engine**. Convergent accumulation is an order-dependent float sum, so on graphs where three or
> more contributions reach one node, fresh processes disagree in the last place at library
> defaults (DEFECT-A, `docs/BUG-0b1-coalition-strength-determinism.md` §8). The store is not
> affected. Whether the engine keeps the `PROVEN` label is an open decision (D-011) and is
> deliberately not settled inside a methodology document.
>
> **Tester-verified mechanism:** the field, coalitions, source-clustering, and workspace layers
> make the cognitive cycle **close end-to-end** and are independently, adversarially verified for
> the same hard properties — but **as mechanism only**. Closing an information loop with bounded
> feedback is **not** a cognitive result.
>
> **Not established:** that anything the cognitive layer produces is **cognitively meaningful**.
> No behavioral cognitive effect has been reproduced against external human data.

"The mechanism is correct and deterministic" and "the mechanism reproduces a cognitive phenomenon"
are different claims. This project earns the first and explicitly does not claim the second. The
natural next step is to test the cognitive layer against a **measurable** effect whose direction is
known independently of Psyche (for example **semantic priming**, graded against human association
norms), so that, as with the substrate, the input is no longer chosen to make the answer come out
right. That result has not yet been produced; it is the open frontier.

---

## The same discipline, carried into the cognitive cycle (1c / 1d)

The six findings above were paid for *before* the cognitive cycle closed. After them, three more
bricks were built — source-clustering (1c), workspace competition + pruning (1d-i), and bounded
broadcast (1d-ii) — and the *same* two practices (adversarial testing; loop-closure with
system-generated inputs) governed them. These are **further instances of the discipline**, not a
recharacterization of the original six. Two changes of process are worth recording, because they
are themselves methodological:

1. **Verification split across two independent roles.** Each brick was built by a builder and then
   **independently re-verified in a separate adversarial tester role**, with its *own* hostile and
   loop-closed suites (`test_tester_1c_*`, `test_tester_1d_i_*`, `test_tester_1d_ii_*` — not the
   builder's). "Mechanism" is what the tester verifies; a "cognitive claim" would be routed to a
   separate validator against external data. None of the bricks below makes a cognitive claim, so
   none reached the validator.
2. **An asserted known-limitation was *flipped through the live loop*, not edited away.** The
   earlier slice shipped an incoherent "thought" on clustered real input as a standing
   asserted-negative (finding (f)). Rather than relax that test, the new bricks made the real
   behavior change, and the negative was re-expressed as the now-passing behavior — the honest way
   for a documented limitation to retire.

### (g) The over-swallow flip — fixed at the mechanism level, *through* the cycle

- **Claim under test:** on real clustered input, the closed cycle no longer collapses basins — it
  neither strands a same-domain perceived source as a singleton, nor over-swallows a bridged
  unperceived domain into the winning thought.
- **The two halves, and what fixed each.** Source-clustering (1c) groups nearby perceived sources
  before the field is built, which fixes the **stranded-singleton** half. Workspace pruning (1d-i)
  removes the **bridged unperceived** domain from the winner, which fixes the **over-swallow**
  half. The fix is upstream-then-downstream, in the spirit of finding (e): the real problem was in
  the *shape* of what fed the field and what left the workspace, not a tuning constant.
- **Anti-circularity (the loop-closure discipline, applied again).** The flip is driven by
  coalitions the cycle *generated*, not hand-placed; it is verified to **generalize on a second,
  independently-built isomorphic-but-relabelled graph**, so it cannot be an artifact tuned to the
  `coffee`/`work` fixture. A counterfactual control checks the dual: when the input *names* the
  formerly-pruned domain, it is **not** pruned (the flip is membership-driven, not a fixed cut).
- **Honest residual, shipped as an asserted-negative.** The realized pruning rule is a
  **parameter-free cohesion-valley / relative-attachment watershed**, not literal
  domain-membership. The tester's adjudication (the "C1 adjudication" checks) established
  decisively that the two rules **diverge**: an unnamed multi-node domain bridged into the named
  region *at least as strongly as its own internal cohesion* has no valley and is **kept**, so
  over-swallow can recur in that topology. This was **accepted as the intended design** (Cagan's
  decision), because the divergence is always **safe-direction** — it can over-include an unnamed
  domain but can never over-prune a perceived member — and it is documented as a standing
  asserted-negative rather than hidden. This is the methodology's own rule applied to itself: a
  limitation is written as a checkable claim, not smoothed over.

### (h) Bounded feedback verified in *both* directions — the harder half of "it doesn't break"

- **Claim under test:** the single broadcast write that closes the loop is bounded **both ways** —
  it does not diverge (runaway potentiation) and it does not lock in (the cycle can still escape a
  deeply-reinforced winner).
- **Why both directions matter.** A feedback write is the first place a "pure read everywhere"
  substrate gains a way to corrupt itself over time. Testing only that it *settles* would miss the
  dual failure (it freezes); testing only that it *can change* would miss runaway growth. The
  tester verifies **no-divergence** (road strength stays ≤ 1.0, the aggregate plateaus, per-cycle
  deltas → ~0, even from a near-saturated start and inside tight self-reinforcing loops) **and**
  **no-lock-in** (after biasing winner A over many cycles, a strong fresh percept for B switches
  the winner — *non-vacuously*: A is verified dominant immediately before the switch — on a hostile
  bridged graph, mirrored for bridge direction, with a freeze probe and a close-competition
  differential control).
- **Boundedness is structural, and that is asserted as such.** A code-body audit asserts that
  **neither** `broadcast()` **nor** its helpers contain a clamp, cap, ceiling, or tunable
  magnitude: the boundedness comes entirely from `strengthen()`'s `(1 − strength)` saturation
  (verified against the closed-form geometric contraction, fixed point 1.0, approached from below
  and provably never exceeded). This is the same instinct as findings (b)/(c): pin the *property*
  by its mechanism, not by spot-checking an output.
- **Re-owned across the role boundary (P9 / T7c).** Two claims that crossed brick boundaries were
  **re-derived independently by the tester** rather than inherited: that the over-swallow residual
  is absent after 1d-i by the membership watershed (P9, re-owned as T11), and that
  `broadcast=True` performs **exactly one** write while `broadcast=False` stays pure (T7c,
  re-owned for 1d-ii). Independent re-derivation agreeing with the builder's claim is what earns a
  PASS across a boundary — not the builder asserting it once.

### What (g) and (h) do and do not establish

They establish that the cognitive cycle now **closes end-to-end** and that every property the
substrate bar demands (determinism across processes, integrity, purity on the read path, and —
new for the write path — bounded, non-locking feedback) holds under adversarial and loop-closed
inputs. They establish **no cognitive claim**: the winner is a selected information structure and
the broadcast is a bounded conduction bias. The line the original six findings drew is unchanged —
mechanism is verified, meaning is not — and the next step is exactly what the method recommends:
an externally-graded behavioral effect, run through the now-closed loop.

---

## Four rules the substrate-repair sequence paid for

Each was bought with a defect that shipped, sat undetected, and was then found by accident.
They are stated here as rules because in each case the project already *had* a probe for the
property and the probe could not see it.

### 1. A coverage axis is only evidence for the property it can perturb

This project swept `PYTHONHASHSEED` for a month against a nondeterminism that **uuid4**
caused. Iteration order derived from uuid values, which are freshly random in every process,
so the defect varied at a *fixed* seed and no seed could have found it. The axis being swept
did not control the mechanism, and sweeping it produced confidence without evidence — which
is worse than no probe, because a swept axis is read as a guarantee.

The interpreter axis survives this test and the seed axis does not, for a concrete reason:
CPython 3.12 changed the builtin `sum()` to Neumaier compensated summation, so identical code
computes different floats on 3.11 and 3.12. That is a property of the environment, and the
interpreter sweep can perturb it. Determinism, by contrast, is now established by **removing**
the order dependence rather than by sampling an axis that never controlled it.

**Corollary: prefer removing a dependence to sampling it.** An axis you have eliminated needs
no coverage argument.

### 2. A boundary located by sampling is the last sample, not the boundary

The activation-silencing cliff under normalization was recorded three times, by three
different measurements, as three different numbers: **16**, then **24**, then — by exhaustive
search — **31**. None of the three was a wrong *observation*. Each was the largest value that
measurement happened to test, mistaken for the edge.

A sampled boundary reports the resolution of the sample. If a spec states an edge, the edge
must be found by search or by proof, and a probe that samples must say so in the number it
reports.

*(Both rules are enforced in practice rather than remembered: bit-exact comparison replaces
`round(x, 9)` in every determinism probe, and `ledger_check` C5/C6 fail the build on the
classes that were previously caught by looking.)*

### 3. A site can have the shape, have the symptom, and still clear a probe a competent person designed to find it

> **Therefore reproduction cannot be the gate. Only enumeration can.**

This is the generalisation of the most expensive defect in the sequence, and it was bought at
the highest price of the three: **it occurred inside the brick built to stop that very class,
and it was written into that brick's spec as its headline argument.**

The registry entry for `psyche_field.py`'s merged-flow accumulator read *"shape present, symptom
unreproduced"* — a site that looked dangerous, probed, and cleared. The probe put four sources
onto **one node**. At the first hop each road is traversed by exactly one source's spread, so
every value there is **single-term**, and a single-term sum cannot vary by reordering. The
probe was **structurally incapable** of exhibiting the symptom it was run to find. Move the
shared road one hop downstream and the site moves — two distinct bit patterns over the source
orders, on 40 of 40 randomly generated graphs.

Nobody was careless. The probe was designed by someone who understood the defect, aimed at the
right site, and reported truthfully what it saw. **That is what makes the lesson general**: the
failure was not in the observation but in treating a negative observation as evidence of
absence.

The operational form, and the reason this project's float gate is a *census* rather than a
hunt: **a clearing probe must be shown capable of failing before its silence counts as
evidence.** Ask of any probe that found nothing — *could this have produced the symptom at
all?* If the answer is no, the result is not a clean bill; it is no measurement.

*Marked for the paper's methodology section, alongside the other two.*

### 4. An assertion must be shown capable of failing against the code it was written against

Rule 3 says a *probe* must be able to fail. This is its enforced form, and it is stronger
for one reason: **it runs.**

Rule 3 was carried as a habit for three bricks, and a habit does not survive a green suite.
The failure it was supposed to prevent then occurred in the file whose whole purpose is to
prevent it. Verifying SPEC-2f step zero, the tester's audit ran every assertion written
for the brick against the tool **as it stood before the fix** — and <!-- ledger:allow-count
reason: "2 of 12" is the audit ratio for ONE brick's assertions (twelve claims examined
two-sidedly, two found dead), not a suite count and not the captured total. C2 correctly
cannot tell these apart; the number must not be updated to the ledger total. -->**2 of 12
passed on both sides**. One of the two asserted that `scan_source` returns `[]` for a
declined fold and `[]`
for an empty file: perfectly true, and true before the fix as well, because the fix
deliberately left that signature alone and added a separate entry point. It named a defect it
could no longer perturb. The second was found by the same audit and had never had the power
it claimed: it was written to prove two code paths were mutually exclusive, and its input
produced one finding either way.

Neither assertion was wrong. Both were **evidence for nothing**, which is harder to notice,
because a passing assertion reads as verification and a green suite reads as a result.

**The rule, and it is mechanical:** a suite that verifies a fix loads the pre-fix revision —
`git show <rev>:<path>` — and requires each of its claims to **fail** there and pass on
current. A claim that survives the old code is reported as dead rather than counted. This now
runs as a test (`test_the_repointed_assertions_can_actually_fail`), so the next dead assertion
turns the suite red instead of padding the count.

Two corollaries worth stating, because both were paid for here:

- **Convert, never delete.** An asserted-negative that goes red because the defect was fixed
  becomes a positive assertion of the capability gained. A deleted negative leaves no trace
  that the limit ever existed; a converted one goes red again on regression.
- **A dead assertion is kept and labelled, not removed.** The `scan_source` one is retained
  in the suite as the standing example, with its status recorded. Deleting it would destroy
  the only evidence that the failure mode is real.

*Marked for the paper's methodology section. It is the operational form of rule 3 and the
first of the four that is enforced by execution rather than by review.*

#### 4a. Only a NEGATIVE containment assertion can pass vacuously

Rule 4's sharp form, and it narrows the search enormously.

A **positive** containment assertion — `check("X" in Y)` — that passes is **live by
construction**: it passed *because* the matcher found X. It cannot be vacuous.

A **negative** one — `check("X" not in Y)` — passes whenever X is absent, and X is absent
both when the code is correct **and when X could never have matched at all**. Those two are
indistinguishable from the result. That is the whole failure mode.

It was found in this repository the expensive way: an assertion that a superseded claim was
gone searched for a phrase spanning a hard-wrapped docstring line, so it could never match,
and it passed. A whitespace-normalised comparison fixed it, and a two-sided check — the same
matcher, run against the revision where the phrase *was* present — proved the fix live.

**The rule:** for every negative containment assertion, produce a **witness** — text where
the phrase IS findable by the same matcher. No witness, no assertion. A sweep of all four
suites on this basis found the one instance and zero others, and it also found two ways to
run the sweep wrongly: searching a source blob flags a *live* assertion matching a
runtime-assembled string, and requiring a string literal on the left misses the very shape
that caused the defect, a phrase held in a variable.

*Marked for the paper, beside rule 4.*
