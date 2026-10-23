# SPEC-1c — Source-clustering

Status: **BUILT (mechanism) · UNVALIDATED (meaning)** — implemented and passing as-scoped; independent tester verification pending; §6.2 meaning not yet earned.
Author: architect-pm
For: builder (§6.1 test-first) → tester (independent verify) → validator (§6.2)
Amended 2026-06-20: §6.1's "no over-swallow" criterion re-scoped to 1d by human decision (see §6.1 and §8).
Depends on: 1a (`psyche_field`), 1b (`psyche_coalitions`, `psyche_perceive`), Phase 0 substrate.

> Scope discipline (CLAUDE.md): this document is **description, not built code**. Nothing here is
> `PROVEN` or `BUILT` until the tester returns PASS on §6.1 and the validator returns a verdict on §6.2.
> Mechanism and meaning are graded separately and one never stands in for the other.

---

## 1. What 1c is

1c is a **deterministic, pure-read pre-processing stage** inserted *between perception and field
construction*. It takes the set of sources perception emits and partitions it into groups — "merge
near sources, keep far sources apart" — then hands the field builder **one representative seed per
group** instead of every raw source.

The motivation is biological in the loose sense only: nearby cues in a real utterance tend to name
one concern, and a cognitive cycle should treat them as one pull, not several competing ones.
Biological *inspiration* is named; no biological *fidelity* and no cognitive *achievement* is claimed
by 1c on its own (see §7).

**The concrete problem 1c exists to fix.** The closed loop already surfaced the bug, and it is
recorded honestly as a deliberately-failing test:
`test_KNOWN_LIMITATION_clustered_sources_give_poor_basins` in `tests/test_psyche_perceive.py`. On real
input — `think(s, "coffee in the kitchen this morning")` — perception lights up three same-domain
sources (`coffee`, `kitchen`, `morning`). The multi-source field then collapses: one source
over-swallows (it pulls in the unrelated `work`/`code` domain), and same-domain siblings strand as
singleton basins. Basins are only meaningful once nearby sources are grouped first. 1c is that
grouping step.

This is a **well-posed structural problem, not a guess.** The fix must be validated *through the
closed loop* so the problem is not merely relocated one layer up, and the grouping must be **decided
by the substrate, never by hand** — hand-chosen groupings would be the circularity bug in a new
costume (CLAUDE.md rules 4 and 5).

---

## 2. Inputs (loop-closed)

1c is driven entirely by artifacts the previous stages generate. No hand-placed sources, no
hand-placed groupings.

| Input | Type | Origin |
|---|---|---|
| `perception.sources` | `Dict[str, float]` (NodeID → source energy) | `perceive()` / `Perception` in `src/psyche_perceive.py` |
| `store` | `SubstrateStore` | Phase 0 |
| per-source spreads | `ActivationField.per_source` (`SourceID → NodeID → activation`) | `build_activation_field()` in `src/psyche_field.py` — only if the activation-overlap signal (A2) is chosen; see §3 / Decision 1 |

**Canonical driver.** The acceptance path is the existing `think()` flow, unmodified at its public
surface. 1c slots in so that the sources reaching `build_activation_field` are the **group
representatives**, not the raw perceived set. Tests must call `think()` (or `perceive()` →
clustering) on real utterances; constructing a `Perception` by hand for the loop-closed acceptance
test is forbidden.

---

## 3. Algorithm / approach

The novelty budget is spent on *which sources are near each other*, not on the clustering scaffolding
(CLAUDE.md rule 6). The clustering itself reuses the proven determinism pattern already shipped in
`psyche_coalitions.py`: build a graph, take connected components of a thinned graph, iterate seeds and
neighbors in **sorted order**, and break every tie on `creation_seq` (never a uuid, never set
iteration order).

**Recommended: (A) single-link agglomerative clustering on a source–source proximity graph.**

1. Compute a symmetric **proximity** value for every pair of perceived sources (the signal is
   Decision 1 below).
2. Keep an edge between two sources iff their proximity clears a **relative** threshold (a fraction
   of the per-run proximity distribution — e.g. relative to the max or median observed proximity),
   **never an absolute constant**. Relative thresholding is what gives scale-invariance (§5).
3. The **connected components** of the thinned graph are the source groups (this is single-link /
   transitive merging — chaining is intentional and documented as a limitation, §7).
4. Each group elects one **representative** by the existing rule: highest source energy, ties broken
   on `creation_seq` ascending.

This is single-link agglomerative clustering (Sibson 1973, SLINK) realized as
connected-components-of-a-thinned-graph — the same shape as basin/coalition formation, so the
determinism story is already paid for.

### Considered and ranked

- **(A) single-link on a proximity graph — RECOMMENDED.** Matches the symptom (merge same-domain
  siblings, separate far domains), reuses proven deterministic scaffolding, stays stdlib-only.
- **(B) direct-pairwise threshold, no transitive merging.** Simpler, but under-merges: A–B and B–C
  near while A–C just misses leaves the group split. Rejected as the primary; its no-chaining
  behavior is a useful contrast in tests.
- **(C) full-graph community detection (Louvain/Leiden) over the whole substrate.** Out of scope for
  1c and a determinism hazard (these are non-deterministic / resolution-sensitive). 1c clusters
  **only the small perceived source set**, not the whole graph. Community detection appears in 1c
  only as an *external grader* (§6.2), living under `experiments/`, never in the core.

### Prior art (cited, not reinvented)

- Sibson, R. (1973). *SLINK: an optimally efficient algorithm for the single-link cluster method.*
- Hubert, L. & Arabie, P. (1985). *Comparing partitions.* (Adjusted Rand Index — §6.2 metric.)
- De Deyne, S. et al. (2019). *The "Small World of Words" English word association norms.* (External
  yardstick — §6.2.)
- Traag, V. A. et al. (2019). *From Louvain to Leiden: guaranteeing well-connected communities.*
  (Only as the external community grader of last resort — §6.2 / Decision 2.)

### Dependency posture

Core stays **stdlib-only** (CLAUDE.md rule 8). No new dependency is requested for `psyche_source_clustering`.
Any community-detection library needed purely to *grade* §6.2 lives under `experiments/`, is run
once to produce a frozen external label file, and never enters the core import graph.

---

## 4. Outputs

New module `src/psyche_source_clustering.py` (suite `tests/test_psyche_source_clustering.py`), exposing
small immutable dataclasses:

- `SourceGroup` — `members: frozenset[str]`, `representative: str`, `_seq: Dict[str,int]` (the
  `creation_seq` map, same convention as `Coalition`, for stable ordering).
- `SourceClustering` — the ordered list of `SourceGroup`s plus a `group_seeds: Dict[str, float]` map
  (representative NodeID → seed energy, e.g. the max or sum of the group's source energies — fixed in
  the spec build, documented).

`group_seeds` feeds the **unchanged** `build_activation_field(store, list(group_seeds), source_energies=group_seeds)`.
1c changes *what sources reach the field*, not the field builder's signature or the perception
surface. Downstream (1b basins, 1d workspace) consume the field exactly as today.

---

## 5. Substrate bar (mechanism — tester verifies)

All four properties from CLAUDE.md rule 7, each an explicit test:

1. **Cross-process determinism.** Identical `SourceClustering` (group membership, representatives,
   order, `group_seeds`) across ≥6 distinct `PYTHONHASHSEED` values, checked the same way the
   existing slice does (`subprocess` probe, compare serialized output). No reliance on set/dict
   iteration order; all iteration sorted; all ties on `creation_seq`.
2. **Integrity.** The store's integrity scan is unchanged before vs. after clustering (1c is
   pre-processing; it must not mutate the graph or its indices).
3. **Read-purity.** Road strengths and traversal counts identical before/after repeated clustering
   passes (mirror `test_slice_is_pure_read`).
4. **Scale-invariance from relative thresholding.** Scaling all source energies / proximities by a
   constant yields the *same* partition — proves the threshold is relative, not absolute.

---

## 6. External "done means"

Two **separate** bars. §6.1 is mechanism (the loop bug is fixed); §6.2 is meaning (the grouping
corresponds to external structure). Passing §6.1 does **not** earn §6.2, and vice versa.

### 6.1 Mechanism bar (tester) — the known-limitation test inverts and passes

> **AMENDED 2026-06-20 (human decision — see §8).** The original §6.1 bundled three criteria, one of
> which (no over-swallow) was found at build time to be structurally outside 1c's reach and has been
> **re-scoped to 1d**. The two criteria below are 1c's acceptance; the moved criterion is recorded as
> a known limitation (§7.7) and shipped as a *passing asserted-negative* until 1d earns it.

The deliberately-failing `test_KNOWN_LIMITATION_clustered_sources_give_poor_basins` is rewritten (or
a paired positive test added) to assert the **fixed** behavior, driven through the closed loop on the
same real input `think(s, "coffee in the kitchen this morning")`:

- **Merge:** `coffee`, `kitchen`, `morning` land in **one** source group (merged, not three competing
  sources). — *1c acceptance.*
- **No stranding:** **no perceived source strands** as a singleton basin — *for sources that are
  near at least one other perceived source.* (A genuinely **isolated** source — one with no road to
  any other perceived source — correctly forms its own singleton: there is nothing to merge it with.
  The tester confirmed this boundary on a system-generated isolated source; it is correct behavior,
  not a defect, and the acceptance input `coffee/kitchen/morning` is fully connected so the property
  holds there.) — *1c acceptance.*

Loop-closure is mandatory: the sources are produced by `perceive()` from text, never hand-placed. A
version that passes by hand-assigning the groups is an automatic FAIL (it re-encodes its own answer).

This is a mechanism claim: it proves the structural part 1c owns is fixed through the real loop. It is
**not** a cognitive claim and must not be described as one.

**Moved to 1d (NOT a 1c criterion):** *no over-swallow of a bridged, unperceived domain* — the winning
thought should not pull `work`/`code` in. After 1c merges the warm sources into one group there is a
**single** source whose representative bridges into the unperceived `work` domain; with no competing
source there is no seam, so the single-source basin still reaches `work`/`code` over the bridge.
Changing which member is representative does not help (the warm cluster is internally dense, so any
representative's spread reaches the bridging node). This is a workspace-competition / coalition-pruning
concern — 1d's job, not source-grouping's. Severing the bridge by tuning the activation floor, the
proximity threshold, or the loop's own graph is **forbidden** (it would tune a parameter to the test).
1c ships this as a passing asserted-negative
(`test_KNOWN_LIMITATION_single_representative_still_swallows_bridged_domain`) asserting the residual
**persists**; that test flips when 1d lands.

### 6.2 Meaning bar (validator) — external community recovery vs. control

**Claim under test:** 1c's source grouping recovers *externally-defined* community structure better
than no clustering.

- **External yardstick (project did not author it):** the SWOW-EN association norms already in the
  repo (`experiments/data/strength.SWOW-EN.R123.20180827.csv`, loader `experiments/swow.py`). Ground-
  truth community labels come from a **third-party community partition of the SWOW graph** — a
  published partition if a citable one is available (Decision 2), otherwise a single documented
  off-the-shelf Leiden/Louvain run frozen under `experiments/` and treated as fixed external truth.
  The labels are **not** authored by Psyche.
- **Probe construction (anti-circularity):** probe source-sets are selected **blind**, by SWOW graph
  topology only (reuse the `Topology` / `select_pairs` discipline from Phase 2B), before any Psyche
  output is seen. Selection never looks at how Psyche will cluster them.
- **Metric:** Adjusted Rand Index (Hubert & Arabie 1985) between Psyche's 1c partition and the external
  community labels, over the probe sets.
- **Control:** the no-clustering baseline (every source its own group) graded by the identical
  pipeline. Plus a random-partition sanity control (ARI must sit near 0).
- **Pre-registered prediction (fixed before the run):**
  - mean **ARI(1c) ≥ 0.30**, and
  - **ARI(1c) − ARI(no-clustering) ≥ 0.15**, in the predicted direction,
  - sign test across probe sets **p < 0.05** in the predicted direction.
- **Honesty clause:** a null or negative result is reported as-is. If the prediction is not met, 1c
  stays `BUILT · UNVALIDATED` — the mechanism (§6.1) can still be PROVEN while the meaning is not
  earned.

---

## 7. Known limitations / asserted negatives (builder ships each as an explicit test)

1. **Not whole-graph clustering.** 1c clusters only the perceived source set, not the substrate. —
   asserted-negative test.
2. **No cognitive claim on its own.** Passing §6.1 proves a mechanism, not a cognitive phenomenon. —
   stated in the delivery report and as a code comment, not hidden.
3. **Chaining is intentional and documented.** Single-link transitive merging can chain A–B–C even
   when A–C are not directly near; a test documents this behavior rather than pretending it can't
   happen.
4. **Perception is unchanged.** 1c does not alter `perceive()` / `Perception`; an asserted-negative
   test confirms the perception surface and the field-builder signature are untouched.
5. **No broadcast / no feedback.** 1c does not feed anything back into the next cycle — that is 1d.
6. **Threshold is uncalibrated.** The relative threshold is a documented design constant, not tuned
   against external data; tuning it on the §6.2 set would be circular and is forbidden.
7. **Over-swallow of a bridged, unperceived domain persists (re-scoped to 1d, 2026-06-20).** After
   merging, a single-source basin whose representative bridges to a domain that no source named still
   pulls that domain into the winning thought. This is a 1d workspace-competition concern, not
   source-grouping; shipped as a passing asserted-negative
   (`test_KNOWN_LIMITATION_single_representative_still_swallows_bridged_domain`) that flips when 1d
   earns it. See the §6.1 amendment.

---

## 8. Decisions (all resolved — 2026-06-20)

1. **Proximity signal.**
   - **A1 — topology/road-strength (RECOMMENDED).** Proximity from the substrate graph (shared
     neighbors / road strength) — independent of the activation field it feeds, so the cleanest
     anti-circularity story.
   - **A2 — activation-overlap.** Proximity from `ActivationField.per_source` overlap — more faithful
     to the literal symptom (basins collapsing), but softer on circularity since it grades the
     grouping by the same field the grouping then reshapes.
2. **External community labels for §6.2.** Prefer a **citable published SWOW partition**; fallback is
   a single documented off-the-shelf Leiden/Louvain run frozen under `experiments/` (RECOMMENDED
   fallback).
3. **Sequencing.** Finish 1c fully (§6.1 mechanism → §6.2 meaning) before pulling 2c (interoception)
   forward — RECOMMENDED — vs. reorder now per the roadmap's open question.

**RESOLVED (2026-06-20, human decision):**

1. Proximity signal → **A1 (graph topology / road-strength only)**. A2 (activation-field overlap)
   explicitly rejected, so the grouping stays a pure function of stable graph state. *(Locked at build.)*
2. §6.2 external labels → **published SWOW partition preferred via a bounded search; a pre-registered,
   frozen, independent Leiden run as the fallback** if no citable published partition is found.
   *(Built by the validator, not 1c.)*
3. Sequencing → **finish 1c now**; pull nothing else forward.
4. *(Surfaced at build)* §6.1 over-swallow conflict → **re-scoped to 1d** (see §6.1 amendment and
   §7.7). 1c's acceptance is **merge + no-stranding**.
