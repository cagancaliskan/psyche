<!--
  MASTER SOURCE OF TRUTH for the Nous technical report.
  The LaTeX (docs/report/nous_report.tex) and Word (docs/report/nous_report.docx)
  deliverables are rendered from THIS file and must be kept in sync in content.

  HARD RULES (do not relax):
   - Every number is taken verbatim from docs/TEST_OUTPUT.txt and the measured stats
     in README.md. Do not recompute or estimate.
   - Nous is an engineering prototype AND a testing-methodology case study: never a
     mind, consciousness, AGI, or a validated cognitive model. The cognitive cycle now
     CLOSES end-to-end, but that is a tester-verified MECHANISM result, not a cognitive
     one; no cognitive meaning is claimed above the substrate.
   - Three assurance tiers are kept strictly distinct: PROVEN (substrate + activation);
     tester-verified mechanism (field, coalitions, source-clustering, workspace — the
     closed cycle); disciplined-exploratory (the experiment scaffolding, incl. the §6.2
     SWOW structural check, which returned an honest NOT YET).
   - Neuroscience/cognitive theories are conceptual inspiration only: never
     "implemented" or "reproduced"; no claims of biological fidelity.

  The §11 reference list is verified: every entry carries page numbers, volume/issue,
  and a DOI (or ISBN) confirmed against the primary source.
-->

# Nous: Adversarial Testing of a Dependency-Free Memory-and-Activation Substrate for Cognitive Architectures

### An Engineering and Methodology Case Study

**Author:** Cagan Caliskan
**Year:** 2026
**DOI:** https://doi.org/10.5281/zenodo.20474613
**Archived on Zenodo** (open access, CC BY 4.0).
**Artifact:** `nous/`: pure-Python standard-library prototype; 7 modules, 12 test suites; MIT-licensed.

---

## Abstract

This report describes **Nous**, a dependency-free Python prototype of a memory-and-activation
substrate for a cognitive architecture, and (more centrally) the **software-engineering
methodology** used to build it. Nous comprises a graph *substrate store* of concept nodes and
weighted "roads"; a deterministic *spreading-activation* engine; a multi-source *activation
field*; a *source-clustering* pre-stage that groups nearby perceived sources; and a *workspace*
that runs one competition among coalitions, prunes the bridged unperceived material from the
winner, and performs a single **bounded broadcast** back onto the substrate — so the cognitive
cycle *perceive → activate → cluster → compete → prune → broadcast → next cycle* now **closes
end-to-end**. The work is reported in **three assurance tiers, kept strictly distinct**.
**(1) `PROVEN`:** the substrate store and the spreading-activation engine are verified, by an
adversarial property-style test suite, for **determinism** (identical output across process runs,
confirmed in fresh interpreters under randomized hash seeds), **integrity** (graph indices stay
mutually consistent across every mutation), and **purity** (reads never mutate stored state).
**(2) Tester-verified mechanism:** the field, coalitions, source-clustering, and workspace layers
are independently and adversarially verified for the same hard properties — plus, for the feedback
write, that it is bounded **both ways** (no divergence, no lock-in) — which is what lets the cycle
close. This is a **mechanism** result; their cognitive *meaningfulness is explicitly not claimed*,
because closing an information loop with bounded feedback is not a cognitive result. **(3)
Disciplined-exploratory:** a separate body of pre-registered experiment scaffolding (a SWOW
association-norm loader, a fan-effect characterization, a graded-priming harness), on which one
structural check was run — comparing the source-clustering grouping against an **independent
standard partition** of the SWOW graph — and returned an honest **NOT YET** (it beat the
no-clustering control decisively, but missed the pre-registered absolute ARI bar). The central
methodological finding is a recurring failure mode: a component that *passes on a friendly,
hand-chosen input and fails on an adversarial or system-generated one*, and the two practices that
caught it: **adversarial/property-based testing** and **loop-closure** (driving each stage with
system-generated rather than hand-placed inputs). Together they exposed **six distinct structural
bugs** in the substrate/activation layers, and the same discipline — now split across an
independent builder and an independent adversarial tester — governed the three later bricks that
closed the cycle. The artifact's verified totals: **618 assertions across 12 test suites, all
passing.** The first *behavioral* cognitive claim — semantic priming through the closed loop,
graded against human association norms — has **not** yet been run and is the open frontier.

---

## 1. Introduction

Most write-ups of ambitious systems describe what the system is meant to become. This one separates
that aspiration from what was actually built and proven, and reports the engineering discipline in
between. The subject is a cognitive-architecture prototype; the contribution is the **testing
methodology** applied to it.

**Motivation:** Cognitive-architecture components (graph memories, spreading activation, clustering
into "coalitions") are easy to implement in a way that *looks* correct on a hand-built example and
is quietly wrong in structure: it double-counts, it depends on iteration order, it bakes the answer
into the input. These are not typos; they are bugs in the *shape* of the algorithm, and they
survive happy-path tests. The question this project answers in the affirmative is whether a
disciplined, adversarial, property-oriented test process can surface such bugs early and force the
honest scoping of what has and has not been achieved.

**Aspiration vs. built reality:** Nous began as a large design vision. Those original vision
documents are retained verbatim in the repository under `docs/design/`, but they are **quarantined
as aspiration**: a disclaimer there states plainly that their grand language ("AGI," "a real
brain," "mind," "felt experience") describes intent, not the built code, and that of the thirteen
documents only the two layer-plan files correspond to anything implemented. This report concerns
**only the built artifact** and is bound by the scope below.

**Scope and non-claims (binding):**

- Nous is an **engineering prototype** and a **testing-methodology case study**.
- It is **not** a mind, consciousness, AGI, or a validated cognitive model, and makes **no claim of
  machine cognition**.
- The substrate store and spreading-activation engine are **`PROVEN`** deterministic,
  integrity-preserving, and pure. These are claims about *mechanism*.
- The field, coalition, source-clustering, and workspace layers are **tester-verified mechanism**:
  they are independently and adversarially verified for determinism, integrity, and purity (and the
  feedback write for bounded, non-locking stability), and together they make the cognitive cycle
  **close end-to-end**. **Closing the loop is a mechanism result, not a cognitive one**; their
  cognitive meaningfulness is **not established** and is **not** claimed.
- The experiment scaffolding is **disciplined-exploratory** — a distinct, lower tier (not in the
  canonical runner; no independent tester/validator pass). The one structural check run on it
  (source-clustering vs. an independent SWOW partition) returned an honest **NOT YET**.
- The first **behavioral** cognitive claim — semantic priming through the closed loop, graded
  against human association norms — has **not** been run. It is named as future work, not a result.
- Named neuroscience and cognitive theories are **conceptual inspiration** only. Nothing here
  *implements* or *reproduces* them, and no biological fidelity is claimed.

**Contributions (methodology first):**

1. **A software-engineering experience report** showing that adversarial/property-based testing
   (determinism verified across process hash seeds, and read-purity verified by hammering reads) and
   **loop-closure** caught a sequence of **six structural bugs** in a memory/activation substrate,
   and that the same discipline — now split across an independent builder and an independent
   adversarial tester — governed three further bricks that closed the cognitive cycle.
2. A **`PROVEN` substrate**: a graph store and a spreading-activation engine that are deterministic,
   integrity-preserving, and pure, with the verification shipped as runnable tests.
3. A **tester-verified, end-to-end-closing cognitive cycle** (source-clustering + workspace
   competition + pruning + bounded broadcast), with the bounded-feedback write verified to neither
   diverge nor lock in — delivered explicitly as **mechanism, not meaning**, including one residual
   over-swallow corner case shipped as a standing, checkable asserted-negative.
4. A **reusable discipline**: phrased as transferable lessons (§6.8) about how "passes on a friendly
   input" recurs and how to design tests and inputs that defeat it.

---

## 2. Background and related work

The following bodies of work **inspired** the design's vocabulary and structure. Nous does not
implement, validate, or reproduce any of them, and claims no biological fidelity; each is named to
position the prototype, not to assert a result.

**Complementary Learning Systems (CLS):** The fast/slow split between a rapidly-learning episodic
system and a slowly-consolidating semantic one [1], updated for intelligent-agent design in [2],
*inspires* Nous's separation of **activation** (what lights up now) from **consolidation** (what is
later reinforced). In the prototype this appears only as a strict rule: spreading activation is a
pure read and never strengthens what it touches, not as a consolidation system.

**Synaptic Tagging and Capture (STC):** The hypothesis that a weak event sets a local "tag" that can
capture plasticity-related products from a nearby strong event [3, 4] *inspires* the framing of
reinforcement as a *gated, budgeted* event. Nous borrows the framing to justify keeping activation
read-only; it does not model tagging dynamics.

**Global Workspace Theory (GWT):** The idea that specialized processes form coalitions that compete,
and a winner is broadcast globally [5, 6], is the source of Nous's *coalition* vocabulary. Coalition
**formation**, a one-winner **competition**, and a single **bounded broadcast** back onto the
substrate now all exist as mechanism. This borrows the theory's *framing* only: no claim of
conscious access, ignition, or global availability in its sense is made — the broadcast is an
internal, bounded conduction bias.

**LIDA cognitive cycle:** LIDA's systems-level *perceive → attend → broadcast* cycle [7] loosely
shapes the staging of the end-to-end cycle, which now **closes** (the broadcast biases the next
pass). The resemblance is structural framing, not an implementation or validation of the model.

**Cognitive architectures:** ACT-R's integrated theory of cognition [8] and SPAUN's large-scale
functional brain model [9] are referenced for **positioning**: Nous is far smaller and makes no
behavioral or biological claims; it is a substrate-and-method study, not an architecture in their
sense.

**Spreading-activation theory:** Nous's activation engine is a deterministic, engineered variant of
spreading activation in the sense of Collins & Loftus [10]; the convergence-sums property is taken
from that lineage, while the hop-layered single-expansion is an engineering choice made for
determinism (§6).

**Arousal and plasticity:** The Yerkes–Dodson inverted-U relating arousal to performance [12]
appears in the design notes as motivation for emotion-modulated plasticity; in the code this is only
charge-modulated strengthening and is best read as design-level aspiration.

**Semantic priming** [10, 11] is named here because it is the worked example for future validation
(§9): an effect whose direction is known independently of Nous.

---

## 3. System architecture (as built)

Nous is pure-Python standard library, organized bottom-up across **seven modules**. Each layer
reads the one below through its public surface only. The full pipeline is the closed cognitive
cycle *perceive → cluster → activate (field) → form coalitions → compete → prune → broadcast →
next cycle*. The honest boundary runs **through** the tiers, not between two halves: the substrate
store and spreading-activation engine are `PROVEN`; the field, coalitions, source-clustering, and
workspace are **tester-verified mechanism** (no cognitive claim).

![Figure 1: architecture layer stack](diagrams/rendered/architecture_stack.png)

**Figure 1: The layer stack and the honest boundary.** The substrate store and spreading
activation are **`PROVEN`** (determinism, integrity, purity); the higher layers (multi-source
field, coalitions, source-clustering, workspace) are **tester-verified mechanism** that make the
cycle close end-to-end. The figure establishes *where verification stops* — it does **not** claim
any layer is cognitively meaningful. (This rendered figure predates the source-clustering and
workspace bricks; the as-built module set and the closed cycle are described in §3.5–§3.6 below.)

### 3.1 Substrate store (`nous_store.py`, 548 lines)

The only component that mutates the graph; it holds no cognitive logic.

- **Nodes and roads:** A `Node` is an always-neutral unit of information with a stable identity and a
  content string. A `Road` is a *directed* edge `source → target` carrying a scalar `strength`
  (edge weight; a new road starts at `0.05`) and a *multi-valued* emotional life `charges` (named
  feelings → intensity in `[-1, 1]`), from which an aggregate `valence` is derived. There is **one
  road per `(source, target)` pair** (a dedup index); the reverse direction is a distinct road.
- **Stable identity vs. ordering:** Every node and road has a stable `uuid4` identity and is never
  addressed by position; a stale handle therefore resolves to `NotFound`, never to a wrong object.
  Formation order, when needed, is a **separate integer `creation_seq`**, kept distinct from identity
  precisely so that ordering never has to fall back to a uuid (§6.4).
- **Lazy, pure-read decay:** Roads decay with elapsed time, but decay is **computed on access as a
  read-only view**: a read returns a *copy* carrying decayed values and never writes. Only writes
  persist decay. The strength time-constant scales steeply with strength
  (`tau = 45 · exp(strength · 4.2)`), so a "highway" is far more stable than a "dirt track"; charge
  mellows on a slower clock. This purity is load-bearing and is the subject of finding (a).
- **Sticky closure:** A strongly-negative crossing (or one-shot trauma) **closes** a road; closure is
  re-evaluated *only on an active crossing*, never by a read or by the passage of time, and only an
  active positive crossing reopens it. Avoidance preserves the closed state rather than dissolving it.
- **Pin guard and integrity:** `remove_node` refuses to delete a *pinned* node (the mechanism behind
  a higher layer's "do not prune what is in use" policy). Adjacency, dedup, and designation
  consistency are asserted incrementally on every mutation, with a full-graph scan available offline.
- **Atomicity:** Every mutation is a synchronous method with no `await` inside, making each mutation
  atomic by construction under single-threaded asyncio.

![Figure 2: substrate data model](diagrams/rendered/data_model.png)

**Figure 2: Substrate data model.** The `Node` and `Road` fields; identity (`uuid4`) is deliberately
separate from ordering (`creation_seq`). Describes the data structures only.

![Figure 3: read vs. write paths](diagrams/rendered/substrate_read_write.png)

**Figure 3: Read vs. write paths (the purity invariant).** Reads compute decay into a *copy* and never
mutate; only writes persist decay; closure changes only on an active crossing. Visualizes finding (a);
it proves a *mechanism* property, not anything about cognition.

### 3.2 Spreading activation (`nous_activation.py`, 281 lines)

The first operation that reads *across* the graph: radiate activation from a seed along directed
out-roads and report what lit up. **Pure read:**

- **Convergence sums:** Activation arriving at a node from several paths is summed: a node lit from
  several directions is more active.
- **Hop-layered single-expansion:** The wave expands in hop layers; all hop-*k* contributions
  accumulate before any hop-*k* node expands, each node expands **exactly once**, and a per-layer
  **frozen snapshot** is used for expansion so that same-hop ("intra-layer") edges cannot leak
  iteration order into the result. Equal-length convergence is therefore **exact**, and the
  algorithm is a deterministic function of store state. This replaced an earlier priority-frontier
  design (findings (b), (c)).
- **Two attenuators:** Transmitted activation is `outgoing · road.strength · decay_per_hop`:
  `road.strength` is **edge conductance** (a property of the connection); `decay_per_hop` is a
  **global distance penalty** (a property of the spread). They are kept separate deliberately.
- **Leaky closure:** A single swappable policy governs closed roads: below a breakthrough threshold
  nothing crosses; above it, a small attenuated fraction leaks through and the event is logged. The
  constants are **uncalibrated guesses on probation**; the tests pin only the qualitative regime.
- **Flow recording:** The engine records, per edge, the activation actually transmitted (`flow`),
  distinct from static topology: a blocked road carries no flow, a leaked road carries attenuated
  flow. Downstream consumers read `flow`, not raw edges.
- **Locality:** A hop budget and an activation floor keep the spread in the seed's neighborhood,
  which is what makes it affordable in pure Python.

### 3.3 Multi-source activation field (`nous_field.py`, 161 lines)

Runs the proven single-source spread once **per source** and assembles a field: each node's
activation from each source, the **summed total** across sources, and the **dominant source** (the
one that activates it most: the node's *basin*). Dominant-source ties break on the stable
`creation_seq`, so the field is deterministic given store state. Pure read. This exists because a
*single* seed yields one activation peak, so any segmentation of it keys off distance from the seed
rather than community structure (finding (e)); multiple sources yield multiple genuine peaks.

### 3.4 Coalitions and perception (`nous_coalitions.py` 324 lines; `nous_perceive.py` 248 lines)

- **Coalition formation** groups co-activated nodes. Two entry points exist: a *flow-cut*
  segmentation of a single spread (cut the region at weak-flow edges), and a *group-by-basin* path
  for the multi-source field. Every output-affecting order is an explicit total order over intrinsic,
  reproducible keys (activation, then `creation_seq`), never set-iteration order.
- **Perception** turns text into sources: tokens (length ≥ 3) are matched by substring against node
  content, and matched nodes become activation sources with energy scaled by match count. This is
  deliberately minimal: exact/substring matching, no embeddings, but it makes the sources
  **input-derived rather than hand-placed**. It is the only stage still a placeholder in the cycle.
- **The closed cycle** (`think`) runs `perceive → cluster_sources → build field (seeded from
  representatives) → form coalitions by basin → select_winner → prune → (optionally) broadcast`.
  The earlier draft's final step, *"strongest coalition = thought,"* is **gone**: it has been
  replaced by a real workspace competition (§3.6). With the default `broadcast=False` the cycle is a
  **pure read**; with `broadcast=True` it performs the single feedback write that closes the loop.
  The cycle is deterministic; what it produces is **not** claimed to be cognitively meaningful
  (finding (f); §7.3).

### 3.5 Source-clustering (`nous_source_clustering.py`, 275 lines)

A **pure-read** pre-stage between perception and the field. The closed loop surfaced that
perception emits *clustered, overlapping* source sets, so basins are meaningless until nearby
sources are grouped first. `cluster_sources` groups nearby perceived sources by **single-link
clustering on a source proximity graph**, where proximity is **topology / road-strength only** (the
"A1" signal — an activation-overlap signal was rejected at build for circularity), then seeds the
field from **one representative per group** (highest source energy; `creation_seq` tiebreak).
Single-link **chaining** is intentional; the relative proximity threshold is an **uncalibrated
design constant**. It is wired into `think()` without changing the perception surface or the
field-builder signature. Verified (mechanism only): deterministic across 6 hash seeds in fresh
interpreters, pure (mutates nothing), integrity-preserving, scale-invariant — and it carries an
explicit asserted-negative that the grouping is **topological only, no cognitive claim**.

### 3.6 The workspace: competition, pruning, bounded broadcast (`nous_workspace.py`, 533 lines)

What the old placeholder stood in for, built as two bricks.

- **Competition + pruning (1d-i), a pure read.** `select_winner` picks **one winner** by
  **activation density** (normalized, so a tight intense coalition beats a larger sprawling one of
  equal total activation) with a **min-size guard**. The winner is then pruned by a **parameter-free
  cohesion-valley / relative-attachment watershed**: a reached member is kept iff it is pulled toward
  the named (perceived) region at least as strongly as toward the unnamed region; else it is pruned.
  This removes the **bridged, unperceived** domain from the winner — the over-swallow half of the old
  known limitation (§7.3). The watershed is **not** literal domain-membership; an unnamed domain
  bridged into the named region *at least as strongly as its own internal cohesion* has no valley and
  is **kept**, so over-swallow can recur in that one topology. The divergence is always
  **safe-direction** (it can over-include an unnamed domain but never over-prune a perceived member)
  and is shipped as a standing asserted-negative.
- **Bounded broadcast + feedback (1d-ii), the single write that closes the loop.** `broadcast`
  performs the one explicit, bounded write: a bounded strengthening of the winner's internal roads
  (reusing `strengthen()`), **once each**, **creating no new road** and **touching no node**, that
  biases the next cycle. It is **bounded both ways**: it does **not diverge** (road strength stays
  ≤ 1.0, the aggregate plateaus; boundedness is **structural** from `strengthen()`'s `(1 − strength)`
  saturation, with **no clamp or tunable magnitude** added) and does **not lock in** (a strong fresh
  percept switches the winner away from a deeply-reinforced one — verified non-vacuously). The
  broadcast magnitude is **uncalibrated** (the inherited default gain, not tuned to any outcome).

**No cognitive claim in §3.5–§3.6.** The winner is a *selected information structure* and the
broadcast is a *bounded conduction bias*. Closing an information loop with bounded feedback is a
**mechanism** property, not priming, awareness, or understanding.

![Figure 4: end-to-end thought slice](diagrams/rendered/pipeline.png)

**Figure 4: The end-to-end cognitive cycle.** Data flow `text → perceive → cluster → field →
coalitions → compete → prune → broadcast → next cycle`. (This rendered figure predates the
clustering and workspace bricks and shows the earlier `perceive → field → coalitions → thought`
slice; the as-built closed cycle is described in §3.5–§3.6.) The figure shows *data flow*; it does
**not** assert the result is cognitively meaningful.

---

## 4. Methodology

The thesis of this report is that the test process (not the prototype) is the contribution. Two
properties were treated as first-class and verified directly.

**Property-based / adversarial testing:** Each component ships with tests written to *break* its
central claim, not to confirm it on an easy case: lopsided edge strengths, intra-layer edges,
equal-activation rings, and a two-dense-communities-joined-by-a-thin-bridge graph built specifically
to defeat distance-based segmentation.

**Determinism across processes, not within one:** The natural implementations leak `set`-iteration
order over `uuid4` keys into their results. Within a single process the hash seed is fixed, so this
cannot be seen; the determinism tests therefore spawn **fresh interpreters** with different
`PYTHONHASHSEED` values and compare output byte-for-byte. The activation suite uses seeds
{0, 1, 3, 7, 42}; the coalition and field suites use {0, 1, 2, 3, 7, 42, 123, 999} (eight seeds); the
slice uses {0, 1, 2, 7, 42, 999}.

**Read-purity as an asserted invariant:** Read-only operations are run in tight loops and the full
canonical (un-decayed) store state is asserted byte-equal before and after, in every layer.

**The harness, and a deliberate non-use of pytest:** The suites use a tiny built-in harness: each
`check(...)` / `expect_raises(...)` increments a counter, and the suite prints `RESULT: N passed,
M failed` and exits non-zero on any failure. They are intentionally **not** pytest tests: pytest
would collect the `test_*` functions but would not register a logical `check(False, …)` as a failed
assertion, so it could report green on a real failure. The honest runner is `run_tests.py`, which
sets an absolute `PYTHONPATH` (required so the determinism subprocesses resolve their imports
regardless of working directory) and propagates non-zero exit codes.

---

## 5. Findings overview

Read findings (b)–(f) together and one shape repeats: **a component passes on a friendly,
hand-chosen input and fails on an adversarial or system-generated one.** Each fix had two parts:
write the test that *tries to break* the claim, and make the inputs *system-generated* rather than
hand-chosen so a stage can no longer be validated against a fiction of what feeds it. The six
findings below are each presented as: *claim under test → bug → root cause → fix → the specific test
that now locks it.* Every claim is traceable to the code and the named test; reported magnitudes that
the shipped artifact does not let one reproduce are omitted rather than asserted.

![Figure 5: the friendly-input failure mode](diagrams/rendered/friendly_input_loop.png)

**Figure 5: The recurring "friendly-input" failure mode, and the two remedies.** Conceptual: the loop
shared by findings (b)–(f), broken by adversarial testing and by closing the loop. It illustrates the
*method*; it asserts no measurement.

---

## 6. The six structural findings

![Figure 6: the six structural findings](diagrams/rendered/six_findings.png)

**Figure 6: The six structural findings at a glance.** Each row: *claim → bug → root cause → fix →
locking test*. Every cell traces to a module docstring and a named test; no error magnitudes are
asserted (the report omits the ones the artifact cannot reproduce).

### 6.1 (a) Read-as-write: a read that could silently re-open a closed wound

- **Claim under test:** reads are pure; stored state changes only on writes.
- **Bug:** the natural implementation applies time-decay on access and writes it back, so every read
  mutates the store; worse, if decay also re-evaluated closure, repeated reads over time could let a
  *closed* (traumatic) edge drift back open with no crossing ever reopening it.
- **Root cause:** conflating "compute the current value" with "persist the current value," and
  letting a passive read touch state (`closed`) that should change only on an active event.
- **Fix:** split decay into a pure view (`_compute_decay`, returns decayed values without mutating;
  `get_road` returns a *copy*) and a persisting write (`_persist_decay`, called only by
  writes/offline). Decay never touches `closed`; closure is sticky.
- **Locked by:** `test_reads_are_pure` (many reads change nothing stored), `test_lazy_decay` (the
  read view shows decay while the canonical value is unchanged), `test_closure_is_sticky` (time +
  repeated reads do not reopen a closed road; only an active positive return does).

![Figure 7: closure lifecycle](diagrams/rendered/sticky_closure_state.png)

**Figure 7: A road's closure lifecycle (finding (a) invariant).** `Open ⇄ Closed` transitions happen
*only* on active crossings; time passing and reads never reopen a closed road. A mechanism property,
asserted by `test_closure_is_sticky`.

### 6.2 (b) Convergence double-counting: "first-pop-final" where activation sums

- **Claim under test:** a node downstream of a convergence point is not over-counted.
- **Bug:** when activation converges from several paths it must sum, but re-expanding the convergence
  node as later paths raise its value counts everything downstream multiple times.
- **Root cause:** importing Dijkstra's "first-pop-final" intuition into an algorithm where activation
  *accumulates* rather than being a shortest-path minimum.
- **Fix:** bounded single-expansion, hop-layered: each node expands exactly once carrying the full
  sum of paths of length ≤ its settle hop; equal-length convergence is exact.
- **Locked by:** `test_no_double_count_downstream_of_convergence`, which uses **deliberately
  lopsided** edge strengths to prove the result does not depend on them, asserts the downstream child
  receives the convergence node's full value exactly once, and includes an explicit guard that the
  result is *strictly below* what additive re-expansion would produce (the old bug's signature);
  `test_convergent_activation_sums` confirms convergence does sum.

![Figure 8: convergence before/after](diagrams/rendered/convergence_before_after.png)

**Figure 8: Convergence double-counting, before/after (finding (b)).** Structural schematic of the
diamond-with-tail: naive re-expansion over-counts everything downstream of the convergence node;
single-expansion counts it once. No magnitudes are shown (the report omits them as not reproducible).

### 6.3 (c) Order-dependence, then nondeterminism: a priority frontier over hashed sets

- **Claim under test:** post-convergence activation depends only on the graph, never on expansion
  order or process hash seed.
- **Bug:** an activation-priority frontier made *which* late ripple was dropped depend on incidental
  edge-strength ordering; and with same-hop edges, which sibling expanded first was decided by
  iterating a `set` of uuids: order randomized per process by `PYTHONHASHSEED`, so results swung
  across runs.
- **Root cause:** letting expansion order be load-bearing for the result, over a container whose
  iteration order is intentionally randomized.
- **Fix:** hop-layered expansion with **per-layer frozen values**: a layer's expansion snapshot is
  fixed before any node in it expands, so an intra-layer edge's contribution propagates only in the
  next layer; expansion reads only the frozen snapshot.
- **Locked by:** `test_expansion_is_deterministic_under_edge_strength` (same topology under lopsided /
  moderate / balanced strengths gives the same relationship), and the decisive
  `test_determinism_with_same_hop_edge_adversarial`, which builds an intra-layer edge and re-runs the
  spread in fresh interpreters under `PYTHONHASHSEED ∈ {0,1,3,7,42}`, asserting the result is
  byte-identical across seeds.

### 6.4 (d) Identity/order leak: tie-breaking on a uuid regenerated every run

- **Claim under test:** coalition output (partition, ordering, representatives) is identical across
  processes.
- **Bug:** coalition ordering and representative selection tie-broke on the node id, but ids are
  `uuid4`, regenerated every run, so any tiebreak falling back to the id was nondeterministic across
  processes even when the structure was identical.
- **Root cause:** using identity (intentionally non-stable across runs) to carry ordering.
- **Fix:** tie-break on the stable `creation_seq` integer; `representative()` orders by
  `(−activation, creation_seq)` and the coalition sort key is `(−strength, −size, min creation_seq)`.
- **Locked by:** `test_determinism_adversarial_across_hash_seeds`, which builds a ring of
  equal-activation nodes plus tie-strength singletons, serializes by stable keys (content +
  `creation_seq`, never uuid), and asserts identity across 8 hash seeds;
  `test_representative_is_most_active_deterministically`.

### 6.5 (e) Binding degeneracy: components on a graph connected by construction

- **Claim under test:** coalition binding subdivides a co-activated region into the right groups.
- **Bug, two stages:** (1) Connectivity binding is structurally degenerate: a seed-rooted spread's
  co-activated subgraph is **connected by construction**, so connected-components always yields *one*
  coalition. (2) Flow-magnitude cutting does subdivide, but for a single seed the only strong signal
  is **distance from the seed**, and flow magnitude is even *anti-correlated* with community
  membership near the seed (a seed-adjacent bridge edge carries more flow than distant intra-cluster
  edges, so it is preserved while genuine internal edges are cut).
- **Root cause:** a single seed produces one activation peak and monotonically-decaying flow; any
  segmentation of it keys off distance, not community.
- **Fix:** keep flow-cut as the single-seed segmenter (it does yield more than one coalition) but
  recognize the real problem is *upstream* and reframe to a **multi-source field**: multiple sources →
  multiple genuine peaks → basins around peaks.
- **Locked by:** `test_single_seed_spread_yields_multiple_coalitions` (flow-cut yields > 1 coalition
  on a real spread) and `test_acceptance_multisource_recovers_communities` (the field recovers exactly
  the two communities on the adversarial bridge graph that single-seed segmentation could not).

![Figure 9: single-seed vs multi-source](diagrams/rendered/single_seed_vs_multisource.png)

**Figure 9: Single-seed degeneracy vs. multi-source basins (finding (e)).** The same
two-communities-with-a-thin-bridge graph: one seed yields a single distance-keyed blob; two sources
yield two basins with the bridge as the seam. The multi-source recovery is the asserted acceptance test
:  in which the two sources are *placed one per community* (see finding (f) for why that matters).

### 6.6 (f) Circular validation: the answer hand-encoded in the input

- **Claim under test:** the cognitive layer works on input the *system* produced, not input chosen to
  make it work.
- **Bug:** every layer above the substrate had been validated against a fiction of what would feed it.
  Sources were **hand-placed**, and this culminated in the field acceptance test recovering two
  communities *only because one source was hand-placed at the center of each*: the answer was encoded
  in the input. (This is visible in the artifact: `test_acceptance_multisource_recovers_communities`
  does place one source per community by hand. It is honest as a *mechanism* test and would be
  dishonest if read as evidence that the system finds communities on its own.)
- **Root cause:** validating a stage against inputs invented to produce the desired output.
- **Fix:** **close the loop** with the thinnest real slice (`nous_perceive.py`): `text → perceive →
  sources → field → coalitions → thought`, where which nodes become sources is decided by the input
  matched against the substrate, not by the test. On real clustered input the field then produces an
  **incoherent** "thought": basins collapse, one source over-swallows across domains, and same-domain
  sibling sources strand as singletons.
- **Locked by, as a *limitation*, not a result (at the time of finding (f)):** the original slice
  asserted the failure on purpose — it confirmed three same-domain sources were perceived, then
  asserted the "thought" over-swallows and that a perceived same-domain source strands as a singleton.
  The limitation was encoded as a standing, checkable claim, written to flip only when source-grouping
  was fixed. **It has since flipped:** source-clustering (§3.5) and workspace pruning (§3.6) resolved
  both halves at the mechanism level, and the assertion has been re-expressed as the now-passing
  behavior (with one residual cohesion-valley corner case shipped as an asserted-negative; see §3.6 and
  §7.3). This bullet records the finding as it stood when discovered; §7.3 records its resolution.

### 6.7 What the six have in common

(b)–(f) are all instances of "passes on a friendly input." (a) is the dual lesson for *invariants*:
a property (purity) that an easy test trivially satisfies can be violated by an interaction
(decay × closure × time) that only a purpose-built test exercises. In every case the bug was
structural, and in every case the catching test was adversarial or loop-closing.

![Figure 10: cognitive-layer evolution and dead-ends](diagrams/rendered/cognitive_evolution.png)

**Figure 10: The cognitive-layer arc and its dead-ends.** connectivity binding → flow-cut →
multi-source field → closed-loop, and what each step revealed (findings (e), (f)), ending at the
known limitation. It documents the *development path*, not a working capability.

### 6.8 Transferable lessons

1. **Test the property, not the example:** purity, determinism, and "no double-count" are
   properties; assert them directly and across processes, not by spot-checking outputs.
2. **Randomize what you assume is fixed:** running under multiple `PYTHONHASHSEED` values is what
   makes uuid-set nondeterminism observable.
3. **Close the loop:** let a stage's inputs be produced by the stage below it; hand-chosen inputs
   hide both degeneracy and circularity.
4. **Encode known limitations as asserted tests:** a negative result written as a failing-on-purpose
   assertion is a standing, checkable claim, not a comment that rots.

---

## 7. Results

### 7.1 Verified properties (the positive results)

For the substrate store and the spreading-activation engine (Tier 1, `PROVEN`), the test suite
establishes, as runnable checks:

- **Determinism:** identical output across process runs, confirmed in fresh interpreters under the
  hash seeds listed in §4.
- **Integrity:** graph indices, adjacency, dedup, and designations remain mutually consistent across
  every mutation; a full-graph scan finds no drift.
- **Purity:** reads never mutate stored state; lazy decay is a read-only view.

For the field, coalitions, source-clustering, and workspace layers (Tier 2, **tester-verified
mechanism**), an **independent adversarial tester** establishes the same hard properties on its own
hostile and loop-closed suites, plus the properties the feedback write requires:

- **The cycle closes end-to-end** — `perceive → cluster → field → coalitions → compete → prune →
  broadcast → next cycle` — with selection a pure read and exactly one bounded write.
- **The over-swallow case is resolved through the live cycle** (formerly an asserted-negative; now a
  real pass) and the flip **generalizes** to an independently-built isomorphic-but-relabelled graph.
- **The broadcast is bounded both ways:** no divergence (≤ 1.0, plateaus; boundedness structural, no
  clamp) and no lock-in (a strong fresh percept still switches the winner, verified non-vacuously).

These are claims about **mechanism**: the code does exactly and only what it says, reproducibly.
They are *not* claims that the mechanism reproduces any cognitive phenomenon — closing the loop is a
mechanism result, not a cognitive one.

![Figure 11: determinism across hash seeds](diagrams/rendered/determinism_seeds.png)

**Figure 11: Adversarial determinism across process hash seeds (before/after).** *AFTER* is the
asserted, byte-identical result of the four determinism tests (each across its own seed set); *BEFORE*
is the documented prior bug (findings (c), (d)), shown qualitatively and **not** re-measured. It
establishes reproducibility of *mechanism* only, not cognition.

### 7.2 Test suite

All figures below are taken verbatim from `docs/TEST_OUTPUT.txt` (CPython 3.12.4, Darwin 24.5.0
x86_64) and re-confirmed by `python3 run_tests.py` for this report. Every suite passes with zero
failures. The suites now include the **independent tester-authored adversarial suites**
(`test_tester_*`), distinct from the builder suites.

| Suite | Layer / role | Checks passed |
|---|---|---:|
| `test_nous_store.py` | substrate store | 45 |
| `test_nous_activation.py` | spreading activation | 35 |
| `test_nous_coalitions.py` | coalition formation | 19 |
| `test_nous_field.py` | multi-source field | 13 |
| `test_nous_source_clustering.py` | source-clustering (1c) | 49 |
| `test_nous_workspace.py` | workspace competition + pruning (1d-i) | 80 |
| `test_nous_workspace_broadcast.py` | bounded broadcast + feedback (1d-ii) | 63 |
| `test_nous_perceive.py` | perception + closed end-to-end cycle | 19 |
| `test_tester_1c_adversarial.py` | tester: adversarial 1c | 73 |
| `test_tester_1c_mutation_battery.py` | tester: 1c randomized mutation battery | 5 |
| `test_tester_1d_i_adversarial.py` | tester: adversarial 1d-i | 107 |
| `test_tester_1d_ii_adversarial.py` | tester: adversarial 1d-ii | 110 |
| **Total** | **12 suites** | **618 passed, 0 failed** |

The total is **618 assertions across 12 suites, 0 failures**, including the cross-process
determinism checks, randomized mutation batteries, the no-divergence / no-lock-in stability checks
on the broadcast write, and the resolved over-swallow case now driven through the live cycle. The
verbatim run is reproduced in Appendix A.

![Figure 12: passing assertions per suite](diagrams/rendered/test_suite_bars.png)

**Figure 12: Passing assertions per suite.** Counts taken verbatim from `docs/TEST_OUTPUT.txt`.
(This rendered figure predates the source-clustering and workspace suites and shows the earlier
five-suite/130-total run; the current canonical total is **618 across 12 suites**, tabulated above.)
Proves *mechanism* (and the *mechanics* of the higher layers); it does **not** measure cognitive
quality.

**Code size (measured):**

| | Files | Lines (`wc -l`) | Non-blank, non-comment (approx.) |
|---|---:|---:|---:|
| Source modules (`src/`) | 7 | 2,370 | ~1,720 |
| Test suites (`tests/`) | 12 | 7,303 | ~5,591 |
| **Python total** | **19** | **9,673** | **~7,311** |

Per module (`wc -l`): `nous_store.py` 548, `nous_workspace.py` 533, `nous_coalitions.py` 324,
`nous_activation.py` 281, `nous_source_clustering.py` 275, `nous_perceive.py` 248,
`nous_field.py` 161. (`wc -l` is exact; the non-blank/non-comment column is an approximate
`grep`-based count, not a precise tokenizer pass.)

### 7.3 The over-swallow limitation — resolved at the mechanism level (with a residual asserted-negative)

The earlier draft of this report recorded an **incoherent "thought"** on clustered real input as an
asserted negative result: when perception lit up several nodes in the same domain, basins collapsed —
one source over-swallowed across domains while same-domain siblings stranded as singletons. **This is
now resolved at the mechanism level**, in two halves: source-clustering (§3.5) groups nearby
perceived sources before basins are built, fixing the **stranded-singleton** half; workspace pruning
(§3.6) removes the **bridged unperceived** domain from the winner, fixing the **over-swallow** half.
The fix was driven through the **live cycle** on system-generated coalitions, and the flip
**generalizes** to an independently-built isomorphic-but-relabelled graph (so it is not tuned to the
fixture). The former known-limitation assertion has accordingly been re-expressed as the now-passing
behavior.

One **residual corner case** remains and is shipped as a standing asserted-negative: because the
realized pruning rule is a **parameter-free cohesion-valley / relative-attachment watershed** rather
than literal domain-membership, an unnamed domain bridged into the named region *at least as strongly
as its own internal cohesion* has no valley and is **kept**, so over-swallow can recur in that one
topology. The divergence is always **safe-direction** — it can over-include an unnamed domain, but it
can never over-prune a perceived member. This is documented as a checkable assertion, not hidden.

![Figure 13: closed-loop slice and its honest failure](diagrams/rendered/closed_loop_known_limitation.png)

**Figure 13: The closed-loop cycle (finding (f) lineage).** On the real input *"coffee in the kitchen
this morning,"* the earlier slice over-swallowed across domains (pulled in *work*/*code*) and stranded
same-domain sources as singletons. (This rendered figure depicts that earlier *failing* state; in the
current as-built cycle the failure is **resolved** — see §3.5–§3.6 — with the single residual
cohesion-valley corner case above shipped as an asserted-negative.)

### 7.4 The SWOW structural check (an honest NOT YET) — disciplined-exploratory tier

One structural meaning-style check has been run, on the **disciplined-exploratory** scaffolding
(Tier 3), and is reported as the honest negative it is. The source-clustering grouping was compared,
on SWOW association data, against an **independent standard partition** of the same graph (a Louvain
partition — a *different* clustering-algorithm family), with the prediction pre-registered and its
direction fixed in advance. By the frozen acceptance rule the verdict is **NOT YET**:

- It **beat the no-clustering control decisively** — lift +0.223 over control; sign test 170/200
  probes better-aligned with the external partition, p ≈ 6e-25; random-control sanity ≈ 0.
- It **missed the pre-registered absolute bar** — mean ARI 0.228 < 0.30. The diagnosed cause is
  **granularity, not direction**: the grouping **under-merges** relative to the coarse standard
  partition (~5.5 groups per 9-word probe), and ARI penalizes a finer partition against a coarser
  truth even when the finer one nests correctly.

Framed correctly (as pre-registered): this is **agreement with an independent standard partition, not
ground-truth recovery** — two unrelated clustering algorithms over a shared external graph agree on
direction but disagree on grain. It does **not** move source-clustering out of `BUILT · UNVALIDATED`,
and it is **not** the project's primary meaning bar.

### 7.5 What these results do and do not establish

They establish that the substrate and activation engine are correct, deterministic, integrity-
preserving, and pure (Tier 1), and that the field, coalitions, source-clustering, and workspace layers
are deterministic, pure, integrity-preserving, and — for the feedback write — bounded both ways, which
is what lets the cognitive cycle **close end-to-end** (Tier 2). They do **not** establish that
anything the cognitive layers produce is cognitively meaningful: closing the loop is a mechanism
result, and the one structural meaning-style check (§7.4) returned an honest NOT YET. "The mechanism
is correct and deterministic" and "the mechanism reproduces a cognitive phenomenon" are different
claims; this work earns the first and explicitly does not claim the second. The first **behavioral**
cognitive claim — semantic priming through the closed loop, graded against human association norms —
**has not been run**; it is the open frontier (§9).

---

## 8. Limitations and threats to validity

- **Cognitive meaningfulness is unestablished:** The field, coalitions, source-clustering, and
  workspace layers are tester-verified as **mechanism** and make the cycle close end-to-end, but no
  *behavioral* cognitive effect has been reproduced against external human data. The one structural
  meaning-style check (§7.4) returned an honest NOT YET. Closing the loop is a mechanism result.
- **Residual over-swallow corner case:** The workspace pruning watershed (§3.6) keeps an unnamed
  domain bridged into the named region *at least as strongly as its own internal cohesion*; in that
  topology over-swallow can recur. The divergence is always safe-direction (never over-prunes a
  perceived member) and is shipped as an asserted-negative.
- **Uncalibrated constants on probation:** The closed-road breakthrough threshold/leak fraction, the
  coalition flow-cut fraction, the source-clustering proximity threshold, and the broadcast gain (the
  inherited `strengthen()` default, not tuned to any cognitive outcome) are first-pass / inherited
  defaults. The tests pin only the qualitative regime, never the magnitudes, and nothing downstream
  may depend on the numbers.
- **Perception is exact/substring matching only:** No embeddings or fuzzy semantics; it is the minimal
  step that makes sources input-derived, and the only stage still a placeholder in the cycle.
- **Out-roads-only spread (v1):** Activation follows directed out-roads; backward spread along
  in-roads is a deliberate later addition.
- **The experiment scaffolding (Tier 3) is not in the canonical runner:** It is self-tested and
  pre-registered, but it has had no independent tester or validator pass; the 12-suite/618-assertion
  canonical run does not exercise it. Its existence does not establish a cognitive result.
- **Determinism is "given store state," not over the abstract graph:** The proven property is that the
  output is a deterministic function of the *store's state*, where state includes the integer
  `creation_seq` assigned in build order. Two stores that are isomorphic as abstract graphs but built
  in a different order can therefore differ in `creation_seq` and, where ties are broken on it, can
  produce different (but each individually deterministic and reproducible) tie-break orderings.
  Determinism here means *reproducibility across process runs of the same construction*, not
  invariance under graph isomorphism.
- **Scale is unverified:** All tests are small graphs; the prototype makes no scaling claims.

---

## 9. Future work

Two of the items the earlier draft listed as future work are now **done at the mechanism level**: the
source-grouping problem (resolved by source-clustering, §3.5) and the missing broadcast/competition
phase (built as the workspace, §3.6, closing the cycle). The remaining — and now central — item is the
**first behavioral cognitive claim**, and it is **still open**.

The next step is to validate the *closed cycle* against a **measurable cognitive effect whose
direction is known independently of Nous**. **Semantic priming** is the worked example: in human
studies, recognizing a target word is faster when preceded by a related prime than an unrelated one
[11], a result the spreading-activation account explains via pre-activation spreading to related
concepts [10]. With the bounded broadcast (§3.6) in place, a prime can now leave a trace that biases a
later target *through the closed loop* — the precondition such a test needs. The protocol would fix a
directional prediction **before** running the system, grade it against **human association norms**
(SWOW), and compare against an unrelated control — so the input is no longer chosen to make the answer
come out right (closing the loop at the level of evaluation). **This has not yet been run**, and until
it is, no behavioral cognitive effect is claimed.

- **Routing:** because this is a cognitive claim, it is for an independent validator to design and run
  with a pre-registered, direction-fixed prediction — not for the builder to assert.
- **Reusable scaffolding (Tier 3), not a substitute:** a pre-registered fan-effect and graded-priming
  harness on SWOW already exists under `experiments/` and is an *instrument* to reuse; it is not a
  substitute for the result through the closed loop, and it carries no independent tester/validator
  pass.
- **Calibration follows, not precedes, a result:** only once an externally-graded effect exists can
  the uncalibrated constants begin to be calibrated against it rather than guessed.

---

## 10. Conclusion

What was earned is concrete and modest, and kept in three strictly-distinct tiers. A correct,
deterministic, integrity-preserving, and pure memory-and-activation substrate, built in
dependency-free Python and shipped with the tests that prove those properties across process hash
seeds (`PROVEN`). Above it, a **tester-verified cognitive cycle that now closes end-to-end** —
source-clustering, workspace competition, pruning, and a bounded broadcast whose feedback write is
verified to neither diverge nor lock in — delivered explicitly as **mechanism, not meaning**, with the
one residual over-swallow corner case shipped as a standing asserted-negative. And, separately, a
disciplined-exploratory experiment scaffolding on which one structural check returned an honest NOT
YET. The larger contribution is the **method**: adversarial/property-based testing and loop-closure
caught six structural bugs that happy-path testing passes over, and the same discipline — now split
across an independent builder and an independent adversarial tester — drew the boundary the project
refuses to cross: proving mechanism while explicitly declining to claim cognition. What remains open
is exactly what the method recommends next, and it is the headline of the next phase: evaluate the
*closed cycle* against a behavioral effect whose direction is known independently of Nous (semantic
priming, graded against human association norms) — a result that has not yet been produced. The honest
version of "it works" used throughout this project is the useful one: *this part is proven; that part
is tester-verified as mechanism; that part is not yet earned, and here is exactly where the line is.*

---

## 11. References

[1] McClelland, J. L., McNaughton, B. L., & O'Reilly, R. C. (1995). Why there are complementary
learning systems in the hippocampus and neocortex: Insights from the successes and failures of
connectionist models of learning and memory. *Psychological Review, 102*(3), 419–457.
https://doi.org/10.1037/0033-295X.102.3.419

[2] Kumaran, D., Hassabis, D., & McClelland, J. L. (2016). What learning systems do intelligent agents
need? Complementary Learning Systems theory updated. *Trends in Cognitive Sciences, 20*(7), 512–534.
https://doi.org/10.1016/j.tics.2016.05.004

[3] Frey, U., & Morris, R. G. M. (1997). Synaptic tagging and long-term potentiation.
*Nature, 385*(6616), 533–536. https://doi.org/10.1038/385533a0

[4] Redondo, R. L., & Morris, R. G. M. (2011). Making memories last: The synaptic tagging and capture
hypothesis. *Nature Reviews Neuroscience, 12*(1), 17–30. https://doi.org/10.1038/nrn2963

[5] Baars, B. J. (1988). *A cognitive theory of consciousness.* Cambridge University Press.
ISBN 0-521-30133-5.

[6] Dehaene, S., & Changeux, J.-P. (2011). Experimental and theoretical approaches to conscious
processing. *Neuron, 70*(2), 200–227. https://doi.org/10.1016/j.neuron.2011.03.018

[7] Franklin, S., Madl, T., D'Mello, S., & Snaider, J. (2014). LIDA: A systems-level architecture for
cognition, emotion, and learning. *IEEE Transactions on Autonomous Mental Development, 6*(1), 19–41.
https://doi.org/10.1109/TAMD.2013.2277589

[8] Anderson, J. R., Bothell, D., Byrne, M. D., Douglass, S., Lebiere, C., & Qin, Y. (2004). An
integrated theory of the mind. *Psychological Review, 111*(4), 1036–1060.
https://doi.org/10.1037/0033-295X.111.4.1036

[9] Eliasmith, C., Stewart, T. C., Choo, X., Bekolay, T., DeWolf, T., Tang, Y., & Rasmussen, D. (2012).
A large-scale model of the functioning brain. *Science, 338*(6111), 1202–1205.
https://doi.org/10.1126/science.1225266

[10] Collins, A. M., & Loftus, E. F. (1975). A spreading-activation theory of semantic processing.
*Psychological Review, 82*(6), 407–428. https://doi.org/10.1037/0033-295X.82.6.407

[11] Meyer, D. E., & Schvaneveldt, R. W. (1971). Facilitation in recognizing pairs of words: Evidence
of a dependence between retrieval operations. *Journal of Experimental Psychology, 90*(2), 227–234.
https://doi.org/10.1037/h0031564

[12] Yerkes, R. M., & Dodson, J. D. (1908). The relation of strength of stimulus to rapidity of
habit-formation. *Journal of Comparative Neurology and Psychology, 18*(5), 459–482.
https://doi.org/10.1002/cne.920180503

---

## Appendix A: Verbatim test output

The following is the captured run from `docs/TEST_OUTPUT.txt` (per-suite result lines are the source
of the totals in §7.2).

```
test_nous_store.py                  → RESULT: 45 passed, 0 failed
test_nous_activation.py             → RESULT: 35 passed, 0 failed
test_nous_coalitions.py             → RESULT: 19 passed, 0 failed
test_nous_field.py                  → RESULT: 13 passed, 0 failed
test_nous_source_clustering.py      → RESULT: 49 passed, 0 failed
test_nous_workspace.py              → RESULT: 80 passed, 0 failed
test_nous_workspace_broadcast.py    → RESULT: 63 passed, 0 failed
test_nous_perceive.py               → RESULT: 19 passed, 0 failed
test_tester_1c_adversarial.py       → RESULT: 73 passed, 0 failed
test_tester_1c_mutation_battery.py  → RESULT:  5 passed, 0 failed
test_tester_1d_i_adversarial.py     → RESULT: 107 passed, 0 failed
test_tester_1d_ii_adversarial.py    → RESULT: 110 passed, 0 failed
                                       OVERALL: all 12 suites passed (0 failures); 618 assertions
```

The complete, unabridged capture (including every individual check label and the asserted-negative
notes) is the file `docs/TEST_OUTPUT.txt` in the repository.

## Appendix B: Reproduction

```bash
# all 12 suites (handles the absolute PYTHONPATH for the determinism subprocesses):
python3 run_tests.py

# a single suite directly:
PYTHONPATH="$PWD/src" python3 tests/test_nous_store.py
```

Pure standard library; no dependencies (developed and captured on CPython 3.12.4). The suites use a
built-in harness and must be run as scripts, not under pytest (§4).

## Appendix C: Figure index and sources

All figures are embedded inline in the sections above. Their **editable sources** and
**presentation-resolution renders** live in the repository:

- **Mermaid diagrams:** source `docs/diagrams/*.mmd`, rendered `docs/diagrams/rendered/*.png` (the
  `.mmd` files also render crisply at mermaid.live or via `mmdc`).
- **Data charts:** matplotlib scripts `docs/diagrams/figures/*.py` (run them to regenerate the PNGs at
  `dpi=200`), rendered `docs/diagrams/rendered/*.png`.

| Fig | Section | Asset name (in `docs/diagrams/`) | Kind |
|---:|---|---|---|
| 1 | §3 | `architecture_stack` | Mermaid |
| 2 | §3.1 | `data_model` | Mermaid |
| 3 | §3.1 | `substrate_read_write` | Mermaid |
| 4 | §3.4 | `pipeline` | Mermaid |
| 5 | §5 | `friendly_input_loop` | Mermaid |
| 6 | §6 | `six_findings` | Mermaid |
| 7 | §6.1 | `sticky_closure_state` | Mermaid |
| 8 | §6.2 | `convergence_before_after` | Mermaid |
| 9 | §6.5 | `single_seed_vs_multisource` | Mermaid |
| 10 | §6.7 | `cognitive_evolution` | Mermaid |
| 11 | §7.1 | `figures/determinism_seeds.py` | matplotlib |
| 12 | §7.2 | `figures/test_suite_bars.py` | matplotlib |
| 13 | §7.3 | `closed_loop_known_limitation` | Mermaid |
| 14 | this appendix | `repo_map` | Mermaid |

![Figure 14: repository / asset map](diagrams/rendered/repo_map.png)

**Figure 14: Repository / asset map.** Orientation only; it shows the package layout, not behavior.
