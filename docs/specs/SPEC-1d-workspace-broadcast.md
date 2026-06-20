# SPEC-1d — Global workspace + broadcast

Status: **1d-i AND 1d-ii both BUILT · mechanism tester-VERIFIED (PASS); 1d overall `BUILT · UNVALIDATED`** — the cognitive cycle now closes end-to-end (perceive → activate → cluster → compete → prune → broadcast → next cycle). 1d makes a **mechanism** claim only; it makes **no external-data cognitive claim**, so it is **mechanism-verified, not meaning-validated** — meaning lives at 1e. Design decisions A–E **locked 2026-06-20** (A2 / B1 / C1 / D1 / take-the-split — see §8); built 1d-i first, then 1d-ii. **Decision C resolved 2026-06-20 → the realized + accepted C1 is a parameter-free cohesion-valley / relative-attachment watershed (see §3.2 / §8), distinct from both literal domain-membership and the rejected fraction-based C2.** Nothing here is `PROVEN` against external data; "mechanism tester-VERIFIED" means determinism + integrity + the declared selection/feedback properties hold — it is **not** a cognitive result.
Author: architect-pm
For: builder (test-first) → tester (independent, adversarial verify). **Mechanism-only: 1d is verified by the tester, not the validator.**
Depends on: 1a (`nous_field`), 1b (`nous_coalitions`), 1c (`nous_source_clustering`), `nous_perceive` (`think()`), Phase 0 substrate (`nous_store`, `nous_activation`).
Inherits from: SPEC-1c §6.1 (amendment) and §7.7 — the re-scoped "no over-swallow" criterion.

> Scope discipline (CONTRIBUTING.md rules 1–4): this document began as **description**; both components are
> now built and tester-VERIFIED. Each component is `BUILT` only after the tester returns PASS on the §6
> bars that apply to it. **1d-i (competition + over-swallow pruning) returned PASS** (mechanism
> tester-VERIFIED) and **1d-ii (broadcast + bounded feedback) has now also returned PASS** (mechanism
> tester-VERIFIED): the §6.2 explicit-write half and the §6.3 both-directions bounded-feedback bar are
> met on hostile topologies. Mechanism and meaning are graded separately and one never stands in for the
> other. 1d makes a **mechanism** claim only; it does **not** make an external-data cognitive claim
> (that is 1e). Because the loop now closes but no external-data claim is made, **1d overall sits at
> `BUILT · UNVALIDATED`** — mechanism-verified, not meaning-validated. The roadmap's "you are here"
> marker moves to **1e** (the loop is closed; the next frontier is the primary meaning bar). Nothing
> here became "validated": closing an information loop with bounded feedback is **not** a cognitive or
> consciousness result, and no code, comment, test name, or doc may describe it as one.

---

## 1. What 1d is

1d is the **workspace-selection-and-feedback mechanism** that replaces the `think()` placeholder
"strongest coalition is the thought" (`coalitions[0]`, `src/nous_perceive.py`) with three real
components:

1. **Competition** — a deterministic, **pure-read** rule that selects exactly **one** winning
   coalition from the candidates `form_coalitions_from_field` produced.
2. **Pruning** — before (or as part of) selecting the winner, drop members that are only **weakly
   bridged** into a domain **no source named**. This is the over-swallow criterion *re-scoped from 1c*
   (SPEC-1c §6.1 amendment, §7.7): on `"coffee in the kitchen this morning"` the single warm basin
   currently reaches `work`/`code` over the strong `coffee→work` bridge; pruning must keep that
   unperceived domain out of the winning structure.
3. **Broadcast** — a single, explicit, **bounded** write back onto the substrate that biases the
   *next* cycle. This is the one mutation 1d introduces, and it is what turns the current one-shot
   pipeline into a loop.

### Honest framing (hard, non-negotiable — CONTRIBUTING.md rule 1)

The vocabulary here — *workspace*, *coalition*, *broadcast*, *winner* — is borrowed from Global
Workspace Theory (Baars 1988) and its computational descendant LIDA (Franklin et al. 2014), which is
the **design lineage** for the whole cognitive cycle. Using that vocabulary is **NOT** a claim of
consciousness, awareness, subjective experience, or phenomenal "ignition." 1d is an
**information-selection-and-feedback mechanism inspired by GWT's routing structure** — nothing more.

Specifically and bindingly:

- The winning coalition is **a selected information structure**. It is **never** "what the system is
  conscious of," "what the system is aware of," or "the system's experience." No code, comment,
  docstring, test name, or commit message may describe it that way.
- "Broadcast biases the next cycle" is an **internal mechanism property** of the substrate — a
  measurable change in the next cycle's activation in a pre-stated direction. It is **not** a claim
  that the system attends, notices, or experiences anything.
- GWT/LIDA are cited as **engineering lineage** for the routing/selection structure, not as evidence
  that Nous reproduces the cognitive or neural phenomena those theories model.

No biological or cognitive *fidelity* is claimed by 1d. Biological/architectural *inspiration* is
named; that is the limit.

### The concrete problem 1d exists to fix

The closed loop already exposes two gaps that the `coalitions[0]` placeholder papers over:

- **No real competition.** "Strongest coalition" is a single sort key (summed activation). There is
  no notion of *selecting one structure to the exclusion of others* as a named, testable step, and no
  decision about whether summed activation is even the right rule (see Decision A).
- **Over-swallow persists (inherited from 1c).** SPEC-1c §7.7 ships
  `test_KNOWN_LIMITATION_single_representative_still_swallows_bridged_domain` (in
  `tests/test_nous_source_clustering.py`) and its twin residual assertion in
  `tests/test_nous_perceive.py::test_clustered_sources_no_longer_strand_after_1c`, both **passing**
  while asserting that the winning thought *still* pulls in the unperceived `work`/`code` domain. 1d
  owns the flip of both (§6.1, §7.1).
- **No feedback.** Nothing the winner does shapes the next cycle, so the pipeline is one-shot, not a
  loop. 1e (semantic priming) cannot be measured until the loop closes — a prime cannot bias a later
  target if nothing is written between them. **1d unblocks 1e.**

This is a **well-posed structural problem, not a guess**, and — like 1c — the fix must be validated
**through the closed loop** (`think()` driven by `perceive()` on real utterances), with **all
coalitions system-generated**. Hand-built coalitions in the acceptance path are forbidden (CONTRIBUTING.md
rules 4–5): a competition that "selects correctly" on a hand-built candidate set has not passed.

---

## 2. Inputs (loop-closed)

1d is driven entirely by artifacts the previous stages generate. No hand-placed coalitions, no
hand-placed winners, no hand-placed bias.

| Input | Type | Origin |
|---|---|---|
| `coalitions` | `List[Coalition]` (already strongest-first) | `form_coalitions_from_field()` in `src/nous_coalitions.py`, via `think()` |
| `field_` | `ActivationField` | `build_activation_field()` in `src/nous_field.py` |
| `clustering` | `SourceClustering` | `cluster_sources()` (1c) — tells us which domains a source *named* (perceived) vs. merely *reached* |
| `store` | `SubstrateStore` | Phase 0 — read for competition/pruning; the **single broadcast write** targets it |
| `perception.sources` | `Dict[str, float]` | `perceive()` — the set of NodeIDs the input actually named (the anchor for "perceived domain") |

**Canonical driver.** The acceptance path is the existing `think()` flow. 1d slots in where
`thought = coalitions[0]` is today; the public `think()` surface (signature, `perceive()`,
`build_activation_field()` signatures) is unchanged except for the new fields on `ThoughtResult`
(§4). For the multi-cycle (feedback) acceptance tests, the driver is **repeated `think()` calls on
the same `store`**, so each cycle reads the trace the previous cycle's broadcast left.

---

## 3. Approach (three components, prior art cited)

The novelty budget (CONTRIBUTING.md rule 6) is spent on **the selection rule, the pruning criterion, and
the bounded-feedback dynamics** — not on scaffolding. Determinism reuses the proven pattern shipped in
`nous_coalitions.py` / `nous_source_clustering.py`: sorted iteration everywhere, every tie broken on
`creation_seq` (never a uuid, never set/dict iteration order), connected-components / explicit total
orders only.

### 3.1 Competition — select exactly one winner (pure read)

A deterministic scoring rule ranks the candidate coalitions and selects the single top one as the
winner. The rule is **Decision A** below; the default carried forward from the placeholder is summed
activation, but the spec proposes density-normalized and coherence-weighted alternatives with
tradeoffs. Whatever rule is chosen, ties break on the existing stable key
(`(-score, -size, min creation_seq)`), exactly as `form_coalitions_from_field` already sorts. This
step **mutates nothing** — it is a pure read of `coalitions` + `field_` + `store`.

Prior art: Baars (1988), *A Cognitive Theory of Consciousness* — the global-workspace competition
("one coalition wins access"). Franklin et al. (2014), *LIDA* — coalitions competing for the
workspace via attention codelets. Shanahan (2006/2010) — global-workspace dynamics as
competition-then-broadcast in an artificial agent. These are cited as the **selection-structure
lineage**, not as cognitive validation (§1).

### 3.2 Pruning — the cohesion-valley / relative-attachment watershed (pure read) — REALIZED + ACCEPTED RULE

> **Decision C resolved (2026-06-20).** The earlier framing in this section — "prune any domain no
> source named" (literal domain-membership) — was the **intent**. The builder's implementation and the
> tester's proof established that the realized C1 is **not** that literal membership rule; it is a
> **parameter-free cohesion-valley (relative-attachment) watershed**. Cagan **accepted the valley rule
> as the intended design** (2026-06-20) — no mechanism rework — requiring this framing be corrected and
> the divergence logged as an accepted known-limitation (§7, item 8). The realized rule is distinct
> from both literal-membership and the rejected fraction-based C2. The paragraph below is the
> authoritative characterization (it matches the module docstring, corrected in parallel).

**The realized + accepted rule.** 1d-i pruning is a parameter-free **cohesion-valley /
relative-attachment watershed**: keep a reached member iff it is pulled toward the named region at
least as strongly as toward the unnamed region; else prune. It is threshold-free and generalizes. It
is **NOT** pure domain-membership ('prune any domain no source named'): an unnamed domain bridged **at
least as strongly as its own internal cohesion** has no valley and is therefore **KEPT**, so
over-swallow can recur in that topology. Accepted as the intended design (Cagan 2026-06-20); the
divergence is always in the safe direction (over-inclusion of an unnamed domain — never over-pruning a
perceived member; verified across 60 random adversarial graphs).

Concretely, in the realized rule:

- A reached node's **attachment to the named region** vs its **attachment to the unnamed region** is
  compared on the same relative-strength scale (no absolute constant, no tunable fraction — scale-
  invariant, in the spirit of 1c's `DEFAULT_PROXIMITY_FRACTION` and 1b's `DEFAULT_FLOW_CUT_FRACTION`,
  but with **no** parameter at all: the comparison is the watershed itself).
- A node is **pruned** when it sits across a **cohesion valley** from the named region — i.e. its pull
  toward the named region is strictly weaker than its pull toward the unnamed region.
- A node is **kept** when there is **no valley** — its pull toward the named region is at least as
  strong as toward the unnamed region. (This is what keeps a non-source node that is densely fused into
  a perceived domain — it is reached strongly from the named side, so it survives.)

Why this still flips the inherited case (SPEC-1c §7.7): on `_small_mind` the `coffee→work` bridge has
weight `n=8` and is **strong**, but `work`/`code`'s pull *back into their own unnamed cohesion* is
stronger still, so a valley exists between the named `coffee` region and the `work`/`code` region and
they are pruned. The flip therefore does **not** rely on "cut weak roads" (the bridge is strong) and
does **not** rely on a tuned threshold — it falls out of the parameter-free relative-attachment
comparison. The acceptance test (§6.1) verifies that this strong-bridge-into-an-unnamed-region case is
still pruned, while a region the input **named** is **not** pruned (the anti-overcorrection control),
and that the flip generalizes on an independently-built isomorphic-but-relabelled graph.

The corner case where the watershed **diverges from literal membership** is logged as an accepted
known-limitation: an unnamed domain bridged **≥ its own internal cohesion** has no valley and is
**KEPT** → over-swallow can recur in that topology (§7, item 8). It is accepted because the divergence
is always in the **safe direction** (over-inclusion of an unnamed domain; it never over-prunes a
perceived member).

This is still the heart of why over-swallow is a *workspace* concern, not a *source-grouping* concern:
only the workspace sees both the named region and the relative pull of everything spreading reached,
and can place the watershed between them.

Prior art: the GWT account of selective access — the workspace admits *one coherent content* and
excludes the rest (Baars 1988; Dehaene & Changeux 2011 model selective amplification/suppression).
Cited as structure, not as a claim Nous reproduces neural ignition.

### 3.3 Broadcast — one bounded write that biases the next cycle

The winner is broadcast back onto the substrate as a **single, explicit, named, bounded** mutation —
the only write 1d introduces. **Decision B** fixes exactly *what* is written and the
decay/normalization rule that **guarantees bounded feedback**. The recommended shape:

- Strengthen the **roads internal to the winning coalition** (the associations that just "won") by a
  **small bounded delta**, so that on the next cycle those associations conduct activation slightly
  more — a "what just won is slightly easier to think next" bias. This is in-grain with the substrate
  (roads carry plasticity; nodes are neutral — `nous_store.py`), reuses the existing road-write path,
  and is exactly the kind of trace 1e (priming) needs.
- **Boundedness is structural, two ways, both tested (§6.3):**
  1. **No divergence.** Road strength already saturates (`strengthen`: `gain ∝ (1 − strength)`), and
     the broadcast delta is capped per cycle, so repeated broadcasts on the same winner **converge**
     toward a ceiling rather than growing without bound. The spec requires a hard invariant: across
     N cycles, total activation / max road strength stays below a fixed bound and does not grow
     monotonically without limit.
  2. **No lock-in.** The bias must be **small and/or decaying** enough that a **sufficiently strong
     new percept can still change the winner**. The spec requires a paired invariant: after biasing
     toward winner A over several cycles, presenting an utterance whose perceived sources strongly
     favor a different coalition B yields B as the winner. (The substrate's lazy decay assists here;
     the broadcast delta must not overwhelm a strong fresh percept.)

These two requirements are in tension by design — too strong a broadcast diverges or locks in; too
weak and it leaves no measurable trace (which would fail 1e later). The bounded-feedback tests pin
**both** ends. The exact delta and decay are a documented, uncalibrated design constant (like every
other relative threshold in the project); 1e may later motivate calibration, but 1d must not tune the
broadcast magnitude to make any cognitive result come out (that would be the circularity bug).

Prior art for the feedback/stability framing: Baars (1988) broadcast-as-feedback; Hebbian
plasticity ("cells that fire together wire together," Hebb 1949) as the lineage for strengthening
co-active associations; **homeostatic plasticity / synaptic scaling** (Turrigiano 2008) as the
lineage for the *bounding/normalization* that prevents runaway potentiation. Citing the bounding
lineage is what keeps the "broadcast" honest: real synapses don't grow without limit, and neither may
this write.

### Dependency posture

Core stays **stdlib-only** (CONTRIBUTING.md rule 8). No new dependency is requested for 1d. The broadcast
write goes through the existing `SubstrateStore` write surface (or a thin, explicit wrapper named for
broadcast — see Decision D), never a new persistence layer.

---

## 4. Outputs / data structures (and how `think()` is rewired)

**Module boundary is Decision D.** The recommended shape: a new module `src/nous_workspace.py`
(suite `tests/test_nous_workspace.py`), keeping competition/pruning/broadcast together and out of the
proven, pure `nous_coalitions.py`. It exposes small immutable result types:

- `WorkspaceResult` — the outcome of competition + pruning:
  - `winner: Optional[Coalition]` — the selected coalition **after pruning** (members already
    pruned), or `None` if there were no candidates.
  - `pruned_members: frozenset[str]` — NodeIDs removed from the raw top coalition by §3.2, recorded
    for inspection and for the over-swallow test.
  - `ranked: List[Coalition]` — the candidates in competition order (for inspection / determinism
    checks). Pure-read product.
  - `_seq: Dict[str,int]` — creation_seq map for stable ordering, same convention as `Coalition`.
- `Broadcast` — the **description** of the write that *will be* applied (what roads, what bounded
  delta), produced as a pure value first, then applied by an explicit, separately-named function.
  This separation is what makes the purity nuance testable (§5): selection produces a `Broadcast`
  value without mutating; a distinct call applies it.

Two functions, with the purity boundary explicit in their names and contracts:

- `select_winner(store, coalitions, field_, clustering, perception) -> WorkspaceResult` — **pure
  read.** Competition + pruning. Mutates nothing.
- `broadcast(store, winner, *, ...) -> Broadcast` — **the single explicit write.** Applies the
  bounded bias to the store and returns what it did. This is the *only* mutation 1d introduces, and
  no read in 1d may call it.

`ThoughtResult` (in `src/nous_perceive.py`) gains fields without changing `think()`'s public
signature:

- `workspace: Optional[WorkspaceResult]` — the competition/pruning outcome.
- `thought: Optional[Coalition]` — **rewired** to `workspace.winner` (the pruned winner), replacing
  `coalitions[0]`. The docstring's "BROADCAST placeholder" language is removed and replaced with an
  honest description of the real mechanism (and the §1 honest-framing caveat).
- `broadcast_: Optional[Broadcast]` — what was written back (present only when `think()` is invoked in
  the writing mode; see below).

**`think()` writing mode (Decision D detail).** `think()` is today a pure read end-to-end, and
several shipped tests assert that (`test_nous_perceive.py::the end-to-end slice mutates NOTHING`).
Broadcast is a write, so it must be **opt-in and explicit** so the pure-read guarantee is not silently
broken. The recommended contract: `think(..., broadcast=False)` by default keeps `think()` a pure read
(selection + pruning only, no write — the existing purity tests stay green and meaningful);
`think(..., broadcast=True)` performs the single broadcast write and populates `broadcast_`. The
multi-cycle feedback acceptance tests (§6.3) call `think(..., broadcast=True)` repeatedly on one
store. This makes "pure selection" and "explicit broadcast write" two visibly different call modes,
which the acceptance tests in §6.2 exploit directly.

---

## 5. Substrate bar (mechanism — tester verifies)

All of CONTRIBUTING.md rule 7, each an explicit test. **Note the purity nuance**: 1d is *not* globally
pure — it deliberately introduces exactly one write. The bar is therefore split.

1. **Cross-process determinism.** Identical output — winner identity, `pruned_members`, `ranked`
   order, and (in writing mode) the `Broadcast`'s targeted roads and deltas — across **all 6**
   distinct `PYTHONHASHSEED` values, checked the same way the existing slices do (`subprocess` probe,
   compare serialized output). No reliance on set/dict iteration order; all iteration sorted; all ties
   on `creation_seq`. Both the pure-selection path and the full writing-mode `think()` are checked
   across seeds (mirror `test_tester_1c_*` P2 / P2b).
2. **Integrity.**
   - **Selection path:** the store's integrity scan is unchanged before vs. after `select_winner`
     (selection is a pure read; it must not mutate the graph or its indices).
   - **Broadcast path:** the store's integrity scan **still passes** after `broadcast` — the write
     strengthens existing roads through the legitimate write surface and leaves all graph indices
     mutually consistent. Integrity is preserved *through* the mutation, not by avoiding it.
3. **Purity nuance (hard — the distinguishing tests).**
   - **`select_winner` is a pure read.** Road strengths, charges, closure flags, traversal counts,
     and node access stats are **identical** before/after repeated `select_winner` calls (mirror
     `test_slice_is_pure_read`). A `Broadcast` *value* may be produced, but no state changes.
   - **`broadcast` is the single explicit write, and it is the ONLY one.** A test asserts that after
     `broadcast`, **exactly** the roads named in the returned `Broadcast` changed (their strength /
     traversal_count moved) and **nothing else** did — no node was mutated (nodes stay neutral), no
     other road moved, no index drifted. This is the test that proves no write is hidden inside a
     read and that the write is exactly the declared one.
   - **No read calls the write.** A test asserts `think(..., broadcast=False)` leaves the store
     byte-identical across repeated calls (the existing end-to-end purity test, kept and extended),
     while `think(..., broadcast=True)` is the only path that changes state.
4. **Scale-invariance of the relative criteria.** Scaling all source energies / activations by a
   constant yields the **same** winner and the **same** `pruned_members` (proves the pruning threshold
   and the competition rule are relative, not absolute — mirror 1c's scale-invariance test).

**Loop-closure (mandatory, CONTRIBUTING.md rule 4).** Every acceptance test in §6 is driven by `think()`
on real utterances; coalitions come from `form_coalitions_from_field`. A test that constructs a
`Coalition` by hand for the acceptance path is an automatic FAIL. (Hand-built coalitions may appear
*only* in narrow unit tests of pure helpers, never in the §6 acceptance path, and never as the basis
for an over-swallow, competition, or feedback claim.)

---

## 6. Acceptance / "done means" (mechanism tests — specify, do not implement)

These are **mechanism** claims, verified by the **tester**. 1d makes **no external-data cognitive
claim**; there is deliberately **no §6.2-style meaning experiment here** (contrast SPEC-1c §6.2). The
project's primary meaning bar remains at **1e** (semantic priming, graded against human SWOW norms),
which 1d unblocks by closing the loop.

### 6.1 Over-swallow flips — through the live loop (the inherited criterion)

The two shipped passing asserted-negatives that document over-swallow **flip to real passing tests**:

- `tests/test_nous_source_clustering.py::test_KNOWN_LIMITATION_single_representative_still_swallows_bridged_domain`
  — its `over_swallows == True` assertion is replaced by the positive: **on
  `think(s, "coffee in the kitchen this morning")`, the winning thought contains NEITHER `work` NOR
  `code`** (`n["work"] not in winner.members and n["code"] not in winner.members`), and those nodes
  appear in `workspace.pruned_members`. The known-limitation framing is removed.
- `tests/test_nous_perceive.py::test_clustered_sources_no_longer_strand_after_1c` — its
  `DOCUMENTED RESIDUAL` over-swallow assertion is likewise flipped to assert the winner excludes the
  unperceived domain. (The stranding half it already asserts stays.)

Driven **through the closed loop** on the exact `_small_mind` graph the bug surfaced on (sources from
`perceive()`, never hand-placed). This is the inherited 1c criterion; SPEC-1c §6.1 amendment and §7.7
explicitly hand it to 1d.

**Anti-overcorrection control (required, same test family).** Pruning must not become "drop anything
far from a source." A paired test asserts that on an utterance that **does** name the work domain
(e.g. `think(s, "work at the desk")`), `work`/`desk`/`code` are **NOT** pruned — they are perceived
(or in a perceived basin), so they belong in the winner. Without this control, a degenerate "prune
everything but the seed" rule would pass §6.1, which must be impossible.

**Anti-circularity (required).** Severing the `coffee→work` bridge by tuning the activation floor, the
proximity threshold, the flow-cut fraction, or any loop parameter **to make this specific case pass**
is forbidden (SPEC-1c §6.1; CONTRIBUTING.md rule 5). The flip must come from the *perceived-vs-unperceived*
pruning principle (§3.2), demonstrated to generalize by the anti-overcorrection control and by at
least one **system-generated** second graph (isomorphic-but-relabelled, à la tester P8c) where a
strong bridge into an unnamed domain is pruned.

### 6.2 Pure selection vs. explicit broadcast write (the purity-nuance distinction)

Two tests that **distinguish** the two modes (this is constraint 4 made concrete):

- **Pure selection:** repeated `select_winner(...)` / `think(..., broadcast=False)` leave the store
  byte-identical (deep snapshot: strengths, charges, closure, traversal counts, node access stats).
  Selection chose a winner and pruned members **without writing**.
- **Explicit broadcast write:** `think(..., broadcast=True)` (or `broadcast(store, winner)`) changes
  **exactly** the roads enumerated in the returned `Broadcast` and nothing else; the diff equals the
  declared write. Running it twice strengthens the same roads further (toward saturation), never other
  roads.

### 6.3 Bounded feedback — BOTH directions (each an explicit test) — MET (1d-ii, tester-VERIFIED 2026-06-20)

Both directions are now independently confirmed by the tester on hostile topologies; the §6.2
explicit-write half is also met (single explicit write; pure `broadcast=False` path preserved
byte-identical). What was specified and what was verified:

- **No divergence (stability) — MET.** `think(..., broadcast=True)` over many cycles (tester probes:
  120 cycles on a dense 6-node clique; 100 on a tight 3-cycle; 60 from a ~0.99 near-saturated start)
  keeps max road strength **≤ 1.0** and the broadcast aggregate **plateaus** (per-cycle deltas → ~0),
  never unbounded growth. **Boundedness is structural** — it comes from `strengthen()`'s `(1 −
  strength)` saturation (fixed point 1.0, approached from below, never exceeded), with **no clamp, cap,
  ceiling, or tunable magnitude** added in `broadcast()` (tester code-body audit + analytic
  fixed-point proof confirm this).
- **No lock-in (responsiveness) — MET, non-vacuously.** After **80** reinforcing cycles biasing winner
  A on a **hostile bridged graph** (B→A, so a B-percept spreads into the heavily-biased A), a strong
  fresh B percept still **switches the winner to B**; escape is verified **non-vacuous** (A is checked
  dominant immediately before the switch). Confirmed under a reversed-bridge mirror, an
  alternating-percept **freeze probe** (the winner follows the current percept on every alternation,
  never freezing), and a differential close-competition control (accumulated bias does not flip a
  both-domains utterance toward A).

These two tests both pass with the **same** broadcast magnitude — it is the **uncalibrated** default
gain inherited from `strengthen()`, **not** tuned to any cognitive outcome (asserted-negative). The
direction in each case was fixed in advance. T7c (the single-write probe) was **re-owned by the
tester** for 1d-ii: independent derivation agrees the write is exactly one bounded write of the
winner's internal roads (once each, no new road, nodes neutral) and `broadcast=False` mutates nothing.

### 6.4 Determinism + integrity (the substrate bar, as acceptance)

The §5 determinism (all 6 seeds, both modes) and integrity (selection pure; broadcast
integrity-preserving) tests are part of "done." A loop-closed cross-process determinism test over
multi-cycle `think(..., broadcast=True)` (the trace of winners + broadcasts across cycles is
byte-identical across 6 seeds) is required, mirroring tester P2b.

> **Done means (one line):** through the live `think()` loop on system-generated coalitions, 1d
> selects one winner by an explicit deterministic rule, prunes weakly-/unperceived-bridged members so
> the over-swallow asserted-negatives flip to real passes (with an anti-overcorrection control), and
> writes a single bounded broadcast that (a) provably does not diverge and (b) provably does not lock
> in — all deterministic across 6 seeds, integrity-preserving, with pure selection and explicit write
> distinguished by test. No cognitive meaning is claimed.

---

## 7. Known limitations / asserted negatives (builder ships each as an explicit test)

> **Status note (2026-06-20).** 1d-i (competition + over-swallow pruning; pure selection; no feedback)
> **and** 1d-ii (broadcast + bounded feedback) are **both BUILT and tester-VERIFIED (PASS)**. 1d-i
> passes every §6 acceptance bar that applies to selection (§6.1 over-swallow flip + anti-overcorrection
> + generalization control, §6.2 pure-selection half, §6.4 determinism/integrity); 1d-ii passes the
> §6.2 explicit-write half and the §6.3 both-directions bounded-feedback bar (no divergence; no
> non-vacuous lock-in), plus §6.4 determinism/integrity under the write across 6 seeds after N cycles.
> The cognitive cycle therefore now **closes end-to-end**. Because 1d makes **no external-data cognitive
> claim**, **1d overall sits at `BUILT · UNVALIDATED`** (mechanism-verified, not meaning-validated) —
> not `DESIGNED`, and not "validated." Limitation item 8 below was added when the tester proved the
> realized pruning rule is the cohesion-valley watershed (§3.2), accepted by Cagan as the intended
> design; it is a *mechanism* limitation and is unaffected by 1d-ii.

1. **No cognitive claim.** Passing §6 proves a selection-and-feedback **mechanism**, not a cognitive
   phenomenon. "The winner biases the next cycle" is an internal property; it is **not** priming and
   **not** evidence of awareness. — stated in the delivery report and as a code comment, asserted as a
   negative (no test or docstring asserts cognitive meaning for 1d).
2. **The winner is a selected information structure, not "what the system is conscious of."** — an
   explicit framing assertion / comment; no overclaiming language anywhere (constraint 1).
3. **Broadcast magnitude is uncalibrated.** The bounded delta/decay is a documented design constant,
   not tuned against external data; tuning it to produce a 1e result would be circular and is
   forbidden. — asserted-negative.
4. **Pruning is a relative-attachment watershed, not semantic.** 1d-i prunes by *relative pull* —
   whether a reached node is attached at least as strongly to the named region as to the unnamed region
   (§3.2) — anchored on what the input *named* vs. what spreading merely *reached*; it does not
   understand domains semantically. A node densely fused into a perceived domain is never pruned even if
   it has no direct source link (it is reached strongly from the named side; the §6.1 anti-overcorrection
   control pins this). — asserted-negative.
5. **Single winner only.** 1d selects exactly one coalition; it does not model parallel or blended
   winners, partial broadcast, or attention over multiple structures. — asserted-negative.
6. **No memory hierarchy / consolidation.** Broadcast is an immediate within-substrate road bias; it
   is **not** episodic memory, replay, or cross-session consolidation (that is Phase 2). — asserted-negative.
7. **Perception and field/coalition surfaces unchanged.** 1d does not alter `perceive()`,
   `build_activation_field()`, or `form_coalitions_from_field()` signatures; it consumes their output
   and adds fields to `ThoughtResult`. — asserted-negative.
8. **An unnamed domain bridged ≥ its own internal cohesion is KEPT → over-swallow can recur there
   (ACCEPTED, safe-direction).** The realized pruning rule is the parameter-free cohesion-valley /
   relative-attachment watershed (§3.2), **not** literal domain-membership. When an unnamed domain is
   bridged into the named region **at least as strongly as its own internal cohesion**, there is **no
   valley**, so the watershed **keeps** it — over-swallow can recur in that specific topology. This
   divergence from literal membership is **accepted as the intended design (Cagan 2026-06-20)** because
   it is always in the **safe direction**: it over-includes an *unnamed* domain and **never** over-prunes
   a *perceived* member (verified across 60 random adversarial graphs). Shipped as an explicit
   asserted-negative — the builder's `test_KNOWN_LIMITATION_unnamed_domain_bridged_ge_cohesion_is_kept`,
   independently confirmed by the tester's T12c / T12d (the corner-case probes that the bridged-≥-cohesion
   node is KEPT and that the divergence is safe-direction only). This is a *mechanism* limitation, not a
   cognitive one; it is **not** a reason to reopen 1d-i — the §6 acceptance bars all pass.

---

## 8. Decisions (RESOLVED 2026-06-20 — locked by Cagan)

> Per CONTRIBUTING.md ("the human is the brain"), these were surfaced as choices, not decided unilaterally.
> All are now **locked** (every choice took the PM's recommendation). The builder implements to these;
> they are not to be re-opened without the human.

**LOCKED:**
- **A → A2:** competition = activation **density-normalized by coalition size, with a minimum-size guard**; `creation_seq` tiebreaks reuse the `nous_coalitions.py` pattern.
- **B → B1:** broadcast = **bounded strengthening of the winner's internal roads** (reuse `strengthen()`, whose gain∝(1−strength) gives structural boundedness); this is the durable trace 1e needs.
- **C → C1, resolved → valley rule (accepted 2026-06-20):** pruning = the realized + accepted
  **parameter-free cohesion-valley / relative-attachment watershed** (§3.2). C1's *intent* was literal
  domain-membership ("prune any domain no source named"); the **realized + accepted** rule keeps a
  reached member iff it is pulled toward the named region at least as strongly as toward the unnamed
  region (else prune) — threshold-free, generalizing, and distinct from **both** literal-membership
  (it KEEPS an unnamed domain bridged ≥ its own cohesion — §7 item 8) **and** the rejected
  fraction-based C2. It flips the strong `coffee→work` bridge without tuning a threshold to the test.
- **D → D1:** new module **`src/nous_workspace.py`** + opt-in `broadcast` flag on `think()`; `broadcast=False` stays a pure read, `broadcast=True` is the only writing path.
- **E → take the split:** build **1d-i** (competition + over-swallow pruning; pure selection; no feedback) first, then **1d-ii** (broadcast + bounded feedback; closes the loop; unblocks 1e).

*(The per-decision options and tradeoffs below are retained as the rationale of record.)*

### Decision A — Competition scoring rule

How the single winner is chosen from the candidate coalitions.

- **A1 — summed activation (carry the placeholder forward).** Winner = highest sum of member
  activations (what `form_coalitions_from_field` already sorts by). *Tradeoff:* simplest, zero new
  code, but **size-biased** — a large diffuse basin beats a small intensely-active one, which is
  arguably wrong for "the most salient single concern" and is exactly the dynamic that lets the warm
  basin sprawl into `work`.
- **A2 — density-normalized (mean activation, or sum ÷ size).** Winner = highest *average* activation.
  *Tradeoff:* favors tight, intensely-active coalitions over sprawling ones — a better fit for
  "selective access to one coherent content," and synergizes with pruning. But it can over-favor a
  tiny 1–2 node coalition; needs a minimum-size guard.
- **A3 — coherence-weighted (sum weighted by internal flow cohesion).** Winner = activation weighted
  by how strongly the coalition's members are internally bound (mean internal flow). *Tradeoff:*
  closest to the GWT "coherent coalition wins" idea and most principled, but the most new code and the
  most parameters to keep honest.

All three break ties on the existing stable key (`(-score, -size, min creation_seq)`).

**Recommendation: A2 (density-normalized) with a minimum-size guard**, falling back to A3 only if the
over-swallow flip (§6.1) proves to need internal-cohesion weighting that pruning alone doesn't give.
A2 is a small, honest change from the placeholder, directly counters the size-bias that feeds
over-swallow, and keeps the parameter surface minimal. **Lock at build** after Cagan picks.

### Decision B — Broadcast mechanism + the boundedness rule

What gets written, and the rule that guarantees bounded feedback (constraint 5).

- **B1 — strengthen roads internal to the winning coalition, bounded delta (RECOMMENDED).** Apply a
  small capped increment to the strengths of roads among the winner's members. *Tradeoff:* in-grain
  with the substrate (roads carry plasticity; nodes are neutral), reuses the proven road-write path,
  inherits saturation (`gain ∝ 1−strength`) for free, and is precisely the trace 1e needs ("what won
  is easier to retrieve next"). Boundedness: per-cycle cap + saturation ceiling → converges.
- **B2 — raise node "activation baselines" for the next cycle.** Give the winner's nodes a residual
  head-start activation that seeds the next spread. *Tradeoff:* conceptually clean ("recently-active
  stays warm"), but **nodes are currently neutral** in the substrate (`nous_store.py`), so this needs
  a new per-node state field — a larger substrate change, and a new boundedness story (the baseline
  must decay or it accumulates). More invasive, more ways to diverge.
- **B3 — tag-for-next-cycle (a transient bias map outside the store).** Carry a decaying bias dict
  between cycles, applied at the next spread, never persisted to roads. *Tradeoff:* leaves the proven
  substrate completely untouched and is trivially bounded by an explicit decay factor, but the bias is
  **ephemeral** — it does not lay a durable trace, which is weaker for 1e (priming wants a real
  retrieval-strength change) and arguably not "broadcast onto the substrate" at all.

**Boundedness rule (applies to whichever is chosen):** a per-cycle bounded delta **plus** an explicit
decay/normalization so the feedback is contractive — the homeostatic-plasticity lineage (Turrigiano
2008). For B1, saturation + per-cycle cap; for B2/B3, an explicit decay factor < 1 per cycle. The
§6.3 tests pin both "no divergence" and "no lock-in" at the chosen constant.

**Recommendation: B1 (bounded road strengthening on the winner's internal roads).** It is the most
in-grain, reuses proven write code, needs no substrate change, and produces exactly the durable trace
1e will measure — while saturation makes boundedness mostly structural. B2 is the cleaner *idea* but
costs a substrate change and a new neutrality exception; defer it unless 1e shows road-bias is too
coarse. **Lock at build** after Cagan picks.

### Decision C — Definition of "weakly bridged into an unperceived domain" (the pruning criterion)

> **RESOLVED 2026-06-20 → valley rule (accepted).** The options below are the rationale of record.
> C1 was selected; the **realized implementation + accepted rule** is the **parameter-free
> cohesion-valley / relative-attachment watershed** (§3.2), which the tester proved is **not** literal
> domain-membership and Cagan accepted as the intended design (no mechanism rework). It is distinct
> from both C1-as-literal-membership and the rejected C2; the accepted corner-case divergence is §7
> item 8. Read C1 below as the *intent*; read §3.2 for the *realized + accepted* rule.

- **C1 — unperceived-domain pruning (RECOMMENDED).** Prune a member iff its domain (basin / 1c group)
  contains **no perceived source** — i.e. spreading reached it but the input never named anything in
  it. *Tradeoff:* this is the criterion that actually flips `_small_mind` (where the `coffee→work`
  bridge is *strong*, so weakness alone won't cut it), and it generalizes (any unnamed domain reached
  over any bridge is excluded). Risk: too aggressive if a perceived domain has a sub-region with no
  *direct* source — mitigated by anchoring on basin/group membership, not per-node adjacency, and
  pinned by the §6.1 anti-overcorrection control.
- **C2 — relative bridge-weakness only.** Prune a member iff the road/flow linking it to the perceived
  region is weak relative to within-coalition cohesion. *Tradeoff:* scale-invariant and simple, but
  **does not flip `_small_mind`** (the bridge is `n=8`, strong) without tuning the threshold to the
  test — forbidden. Useful only as a *secondary* filter on top of C1.
- **C3 — hybrid (C1 gated by C2).** Prune iff unperceived **and** the bridge is below a relative
  cohesion fraction. *Tradeoff:* most conservative (won't prune an unperceived domain that is *densely*
  fused into the percept), but adds a parameter and could fail §6.1 if the fusion is dense — needs
  care.

**Recommendation: C1 (unperceived-domain pruning), anchored on basin/1c-group membership**, with C2's
relative-weakness available as a documented secondary refinement only if a later case shows C1 prunes
something genuinely fused. C1 is the principle that matches *why* over-swallow is a workspace problem
(only the workspace knows perceived-vs-reached) and is the one that flips the case honestly without
threshold-tuning. The anti-overcorrection control (§6.1) is mandatory to keep C1 from over-pruning.
**Lock at build** after Cagan picks.

### Decision D — Module boundary and how `think()` is rewired

- **D1 — new `src/nous_workspace.py` + opt-in `broadcast` flag on `think()` (RECOMMENDED).**
  Competition/pruning/broadcast live in a new module; `think(..., broadcast=False)` stays a pure read
  (existing purity tests stay meaningful), `broadcast=True` performs the one write. *Tradeoff:* keeps
  the proven, pure `nous_coalitions.py` untouched; makes "pure selection" vs "explicit write" two
  visible call modes the acceptance tests exploit; small surface addition to `ThoughtResult`. Slightly
  more files.
- **D2 — extend `nous_coalitions.py`.** Add selection/pruning/broadcast to the existing coalition
  module. *Tradeoff:* fewer files, but it **mixes a pure-read module with a writing one**, muddying
  the purity story that module currently guarantees, and risks the over-swallow/feedback logic
  entangling with the proven coalition-formation code. Rejected as primary.
- **D3 — make broadcast always-on in `think()` (no flag).** *Tradeoff:* simplest call site, but
  **breaks the existing end-to-end pure-read guarantee silently** and removes the clean way to test
  pure-selection in isolation. Rejected (violates the purity-nuance requirement, constraint 4).

**Recommendation: D1.** It is the only option that keeps the purity nuance (constraint 4) cleanly
testable, leaves the proven substrate-pure modules pure, and gives the acceptance suite two distinct
modes to assert against. **Lock at build** after Cagan picks.

### Decision E — Decomposition: split 1d into 1d-i and 1d-ii?

The brief recommends evaluating a split. Confirmed and recommended:

- **1d-i — real competition + over-swallow pruning (pure selection; NO feedback).** Delivers
  Decisions A and C, the §6.1 over-swallow flip + anti-overcorrection control, §6.2's *pure-selection*
  half, and the §5 determinism/integrity/purity-of-selection bar. **No write yet.** This is a complete,
  shippable, tester-verifiable brick: it flips the inherited 1c limitation and proves selection is a
  pure, deterministic read — *without* taking on the harder feedback-stability surface.
- **1d-ii — broadcast + bounded feedback (the single write; closes the loop).** Delivers Decisions B
  (and the writing-mode half of D), §6.2's *explicit-write* half, and the §6.3 bounded-feedback
  (both-directions) bar. This is what unblocks 1e.

**Recommendation: take the split (1d-i then 1d-ii).** Rationale: (1) it honors loop-closure — 1d-i's
pure selection proves itself before the write that depends on it snaps on (CONTRIBUTING.md rule 4); (2) it
isolates the two genuinely different risk surfaces (a *pure* selection/pruning correctness problem vs.
a *dynamical* stability problem), so a bug in one cannot masquerade as the other; (3) each half is
independently shippable and tester-verifiable, matching "every brick proves itself before the next";
(4) the over-swallow flip (high-value, inherited, well-posed) lands first and fast, while the
subtler bounded-feedback work gets its own focused verification. The only cost is a second
build/verify cycle, which the project's discipline already pays gladly. **Confirm or override.**

---

## 9. Prior art (cited, not reinvented)

- Baars, B. J. (1988). *A Cognitive Theory of Consciousness.* — Global Workspace Theory: coalitions
  compete; one wins access; the winner is broadcast. (Selection-and-feedback **structure**; not a
  consciousness claim for Nous — see §1.)
- Franklin, S., Madl, T., D'Mello, S., & Snaider, J. (2014). *LIDA: A Systems-level Architecture for
  Cognition, Emotion, and Learning.* IEEE T-AMD. — Computational GWT: attention codelets, coalitions,
  the cognitive cycle. (Design lineage for the whole 1-phase loop.)
- Shanahan, M. (2006/2010). Global-workspace dynamics in an artificial agent. — Competition-then-
  broadcast realized computationally.
- Dehaene, S., & Changeux, J.-P. (2011). Experimental and theoretical approaches to conscious
  processing. *Neuron.* — Selective amplification/suppression (cited for the pruning/selection
  *structure* only).
- Hebb, D. O. (1949). *The Organization of Behavior.* — Strengthening co-active associations (the
  broadcast-as-plasticity lineage).
- Turrigiano, G. G. (2008). The self-tuning neuron: synaptic scaling of excitatory synapses. *Cell.*
  — Homeostatic plasticity / synaptic scaling: the lineage for the **bounding/normalization** that
  keeps the broadcast from diverging (constraint 5).

---

## 10. Where this leaves the roadmap

**1d-i AND 1d-ii are both BUILT and their mechanism is tester-VERIFIED (PASS).** 1d-i replaced the
`coalitions[0]` placeholder with real density-normalized competition (A2) and flipped the over-swallow
asserted-negative inherited from 1c (SPEC-1c §6.1 / §7.7) through the live loop — via the realized +
accepted cohesion-valley / relative-attachment watershed (§3.2), with the bridged-≥-cohesion corner
case logged and accepted as a safe-direction known-limitation (§7 item 8). 1d-ii added the single,
explicit, bounded broadcast write (B1: bounded strengthening of the winner's internal roads, reusing
`strengthen()`), proven bounded **both ways** on hostile topologies — no divergence (plateaus, ≤ 1.0,
boundedness structural from saturation, no clamp) and no non-vacuous lock-in (escape after 80 cycles on
a bridged graph, with a freeze probe). 1d makes **no cognitive claim** — its mechanism is verified by
the tester, not the validator.

**The cognitive cycle now closes end-to-end:** perceive → activate → cluster → compete → prune →
broadcast → next cycle — a winning coalition leaves a bounded trace that biases the next cycle. Because
1d makes **no external-data cognitive claim**, **1d overall sits at `BUILT · UNVALIDATED`** (mechanism
complete and tester-verified, meaning not earned). This is **not** a cognitive or consciousness result;
it is bounded feedback closing an information loop, with GWT/LIDA cited as engineering lineage only.
Closing the loop **unblocks 1e**, which remains the project's **primary meaning bar** (semantic priming
vs. human SWOW norms).

**Single next action:** begin **1e** (first falsifiable cognitive result — semantic priming graded
against human SWOW association norms) through the now-closed loop. This is a cognitive claim, so it is
routed to the **validator** to design and run a pre-registered, direction-fixed, control-baselined
experiment; the builder does not assert its meaning. (Phase 2A/2B's pre-registered fan-effect and
graded-priming harnesses in `experiments/results/` are prior scaffolding to reuse — not a substitute
for 1e's result through the closed cognitive loop.)
