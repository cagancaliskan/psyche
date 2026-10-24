# EXP-1c — SWOW community-structure recovery (§6.2 meaning bar for step 1c)

Status: **FROZEN PRE-REGISTRATION** — written before any clustering result was seen.
Validator: meaning, not mechanism. Mechanism (§6.1) is already independently tester-VERIFIED
<!-- ledger:allow-count -->
(PASS; see `docs/TEST_OUTPUT.txt` — *historical snapshot at the time of freezing: 8 suites /
254 assertions, 0 failures. The current canonical run is 20 suites / 1,372 assertions; this
document is a frozen pre-registration and is deliberately not rewritten.*). This document
grades only whether 1c's grouping *corresponds to externally-defined structure*.

> ANTI-TAMPER NOTICE. Nothing in this file may change after any result is observed. The
> claim, the thresholds, the control definition, the metric, the probe-selection procedure,
> the external-label source + parameters, and the probe-set count are all fixed here. If the
> result is null or negative it is reported as-is and 1c stays `BUILT · UNVALIDATED`.

---

## 1. Claim under test (verbatim from SPEC-1c §6.2)

> 1c's source grouping recovers *externally-defined* community structure **better than no
> clustering**.

Operationally: the partition produced by `cluster_sources` (`src/nous_source_clustering.py`,
the A1 topology/road-strength method) agrees with an external community partition of the SWOW
graph **more** than the spec's no-clustering control does, measured by Adjusted Rand Index
over blindly-selected probe source-sets.

## 2. Human direction this must reproduce

Words that sit in the **same** external association community should be **grouped together**
by 1c; words in **different** communities should be kept **apart**. The direction is fixed:
1c must move ARI *up* relative to the no-clustering baseline (positive lift), not down.

## 3. External yardstick (the project did not author it)

- **Source graph:** SWOW-EN association norms already in the repo,
  `experiments/data/strength.SWOW-EN.R123.20180827.csv`, via the existing loader
  `experiments/swow.py` (`load_edges`, `build_spec`, `Topology`). De Deyne, Navarro, Perfors,
  Brysbaert & Storms (2019), *Behavior Research Methods* 51(3), 987–1006.
  https://doi.org/10.3758/s13428-018-1115-7
- **External community labels — decision (bounded search performed 2026-06-20):**
  A bounded search was made for a *citable, downloadable* SWOW community
  partition file (word → community-id). The official SWOWEN-2018 repository
  (github.com/SimonDeDeyne/SWOWEN-2018) ships adjacency matrices, `cueStats`, and R analysis
  scripts (`createSWOWENGraph.R`) but **no precomputed community-label file**; published
  community-structure analyses (e.g. Louvain on SWOW-EN at γ=1) describe partitions but do not
  ship a standard offline-loadable word→community file. In this environment downloads
  and network probes were not available, so **no published partition is loadable
  here.** Per SPEC-1c §6.2 / Decision 2, the sanctioned **FALLBACK** is used:

  - An independent community partition is generated on the SWOW graph by a **different
    algorithm family** from the method under test — **Louvain modularity optimization**
    (Blondel, Guillaume, Lambiotte & Lefebvre 2008, *J. Stat. Mech.* P10008), explicitly
    sanctioned by §6.2's "Leiden/Louvain". (Leiden was preferred; `leidenalg`/`igraph` cannot
    be assumed present and were not installed for this run, so a self-contained, stdlib-only
    Louvain implementation living under `experiments/` is used instead. It never enters the
    core import graph — CONTRIBUTING.md rule 8 and SPEC-1c "Dependency posture".)
  - Because the partition is generated rather than published, the result is reported as
    **"agreement with an independent standard partition," NOT "ground-truth recovery."**

### 3.1 Frozen-partition parameters (pre-registered, fixed before the method runs)

- Algorithm: Louvain (Blondel et al. 2008), modularity optimization, **undirected weighted**.
- Edge weights for the grader graph: the SWOW edge weight used everywhere else in this repo —
  `traverse_count = min(10, 1 + floor(R123.Strength * 100))` (the same fixed monotonic map as
  `experiments/swow.py`). Direction is symmetrized for the *undirected* community grader by
  summing the two directed traverse-counts on each unordered pair (w(a,b) = tc(a→b)+tc(b→a)).
  *(This symmetrization is for the EXTERNAL grader only; the method under test reads directed
  road strength from the store and is untouched.)*
- Resolution: γ = 1.0 (the standard/default; the value the published SWOW Louvain work uses).
- Determinism: fixed node-visit order (nodes sorted by word), all neighbor iteration sorted,
  ties in modularity gain broken toward the lowest community id; pass loop runs to convergence
  (no gain ≥ 1e-12) then aggregates; repeated until no further modularity improvement. RNG
  seed for any shuffle: **20250620** (fixed). No randomness affects the output given this seed
  and the sorted orders.
- Scope: the partition is computed on the **largest weakly-connected component** of the SWOW
  graph (community ids are only meaningful within a connected component; isolated fringe nodes
  carry no community signal). Words outside it are labelled `-1` (no-community) and are excluded
  from probe selection (§5).
- **Freezing:** the partition is written to
  `experiments/results/exp1c_external_partition.tsv` (TSV: `word <TAB> community_id`) and its
  SHA-256 content hash is recorded in this document **before** `cluster_sources` is ever called
  or scored. The generator script is `experiments/exp1c_build_partition.py`.

  FROZEN PARTITION FILE HASH (SHA-256): `bebea867e82eaf3c6a44093bcac4901164e38d44a726ebaad6c02f3e298f54a9`
  FROZEN PARTITION NODE COUNT / COMMUNITY COUNT: `133763 nodes (entire graph is one connected component) / 15 communities; top-10 sizes [21736, 18852, 14405, 14084, 10754, 8133, 7449, 6936, 6007, 5745]` (generated 2026-06-20 by experiments/exp1c_build_partition.py; grader self-checks 21/0)

  *(The hash line is filled in once, by pasting the generator's printed hash, and then never
  changed. The clustering method is run only after this line is populated. The generator does
  not import anything from `src/` and never calls `cluster_sources`.)*

## 4. Metric

**Adjusted Rand Index** (Hubert & Arabie 1985), computed between two partitions of the *same
probe word-set*: (a) the partition 1c induces on the probe set, and (b) the restriction of the
external Louvain partition to that probe set. ARI is implemented from scratch under
`experiments/` (stdlib only), unit-checked on textbook cases (identical → 1.0; independent →
≈0.0; the standard Hubert–Arabie worked example). ARI is computed per probe set; the headline
statistic is the **mean ARI across probe sets**.

## 5. Probe-set construction (BLIND — topology only, before any Nous output is seen)

Each probe set is a small set of SWOW words handed to 1c as the "perceived source set." Probe
sets are selected by **SWOW topology** (reusing the Phase 2B `Topology` / `select_pairs`
discipline — `direct` vs `unrelated`), and graded against the **frozen external community
labels** as ground truth. Selection **never calls the engine or `cluster_sources`**.

**Why topology-selected, not random-within-community (decided in advance, not after results).**
1c is a pre-processor for the *perceived* source set, and in the real loop those sources are
topologically related cues (the canonical input is `coffee/kitchen/morning` — words with SWOW
roads between them), not arbitrary word pairs. 1c's mechanism, moreover, is single-link on a
**direct** road-strength graph: it can only merge sources that have a SWOW road clearing the
relative threshold. The faithful test of the claim ("does 1c's grouping recover external
community structure") therefore presents 1c with the kind of related-source sets it exists to
process, and asks whether its groupings align with the *external* partition. Topology decides
*which words to probe*; the external Louvain partition (unseen by 1c) decides *what the correct
grouping is*; this separation is the anti-circularity guarantee (§8). Drawing words at random
from a community regardless of connectivity would instead test single-link against a target it
structurally cannot reach (most same-community words share no direct road), guaranteeing a null
by construction rather than measuring the claim — so it is rejected here, in advance.

Procedure (deterministic given the seed):

- **Seed RNG:** `random.Random(20250620)` (fixed, pre-registered).
- **Number of probe sets:** **N = 200**.
- **Per probe set:** pick a **seed word** P with SWOW out-degree ≥ `MIN_OUTDEG = 4` (sorted
  candidate list, seeded shuffle — the `select_pairs` discipline). Build a 9-word probe:
  - **NEAR block:** P together with **4** of its direct SWOW responses (1-hop), chosen at
    random from P's sorted response list. These are the topologically-near sources single-link
    *can* act on.
  - **FAR block:** **4** words that are **not reachable from P within `K_UNRELATED = 4` hops**
    and (for symmetry with `select_pairs`) have in-degree > 0, drawn at random from the sorted
    unreachable pool. These are topologically-far sources single-link should keep apart from P.
  - The probe is the 9 words {P + 4 near + 4 far}.
- **Ground truth = the frozen external community label of each of the 9 words.** A probe is
  **kept** only if, under the *external* partition, its 9 words span **≥ 2 communities** (so
  there is real structure for ARI to score) and all 9 carry a community label (≠ −1). This
  keep-filter consults the **external labels only — never any Nous output** — so it does not
  pre-encode 1c's answer; it only ensures the probe is gradable.
- No probe is ever filtered, reordered, or weighted by how 1c groups it.

The external label of each probe word (its frozen community id) is the **ground truth** for
that probe; 1c never sees these labels. NB: because ground truth is the *external* partition
(not "near vs far"), a NEAR word and the seed can legitimately fall in *different* external
communities, and a FAR word can share a community with the seed — i.e. the topological
selection does **not** dictate the grading; only the external partition does. That is exactly
what keeps the test honest: 1c is rewarded only for matching the external structure, not for
reproducing the topological recipe used to pick the words.

## 6. Conditions graded by the identical ARI pipeline

For every probe set, three partitions of the same 9 words are scored against the external
labels with the identical ARI function:

1. **1c (method under test):** `cluster_sources(store, source_energies)` where
   `source_energies` gives every probe word equal energy 1.0 (energy must not encode the
   answer; equal energy means representative election is the only energy-dependent step and it
   does not affect membership). The induced partition = the group memberships.
2. **No-clustering control (the spec's baseline):** every probe word is its own group (all 9
   singletons). Graded by the same ARI function against the same labels.
3. **Random-partition sanity control:** a random partition of the 9 words into the *same number
   of blocks 1c produced for that probe* (so it is matched on block count, not handed the
   truth), drawn with `random.Random(20250620 + probe_index)`. Pre-registered expectation:
   mean ARI ≈ 0 (near zero), confirming the metric is not inflated by construction.

## 7. Pre-registered prediction (FIXED — the falsifiable part)

Let ARI(1c), ARI(none), ARI(rand) be mean ARI across the 200 probe sets.

- **(P-a) Absolute:** **mean ARI(1c) ≥ 0.30.**
- **(P-b) Lift over control:** **mean ARI(1c) − mean ARI(none) ≥ 0.15**, in the predicted
  direction (1c higher).
- **(P-c) Sign test:** across the 200 probe sets, the count of probes with
  ARI(1c) > ARI(none) vs ARI(1c) < ARI(none) gives a two-sided sign test **p < 0.05** in the
  predicted direction (more probes where 1c beats no-clustering).
- **(Sanity) Random control:** mean ARI(rand) ≈ 0 (must sit near zero; if the random control
  is materially positive the metric/design is suspect and the run is void, not "passed").

**Verdict rule (no post-hoc loosening):**
- **CLAIM EARNED** iff **P-a AND P-b AND P-c all hold** *and* the random-control sanity holds.
- Otherwise **NOT YET**, reported as an honest negative result; 1c stays `BUILT · UNVALIDATED`.

### 7.1 Falsifiers (stated in advance)

- ARI(1c) < 0.30 → fails P-a → NOT YET.
- Lift < 0.15 → fails P-b → NOT YET (even if P-a passes).
- Sign test p ≥ 0.05, or the majority of differing probes favor no-clustering → fails P-c.
- Random control mean ARI not near 0 → run VOID (design artifact), not a pass.
- **A known structural risk, pre-registered, NOT a reason to relax thresholds:** the
  no-clustering control is all-singletons. The Hubert–Arabie ARI of an all-singletons partition
  against a blocked ground truth is **0 by construction** when no two items truly share a class
  in a degenerate way — i.e. ARI(none) is expected to be ≈0 here. That makes P-b ≈ P-a in
  practice. This is acknowledged in advance and does **not** change the thresholds; it simply
  means the real work is done by P-a (does 1c reach ARI ≥ 0.30 at all) and P-c (does it beat
  the singleton baseline probe-by-probe). The random control guards against the metric being
  trivially inflated.

## 8. Anti-circularity commitments (audited and reported before the verdict)

- (a) **Labels external and frozen pre-method.** The external partition is generated by a
  different algorithm family (Louvain) from the SWOW data, written to disk with a SHA-256 hash
  recorded in §3.1, **before** `cluster_sources` is run or scored. The generator imports
  nothing from `src/`.
- (b) **Probe selection blind to Nous.** Probe sets are chosen from SWOW topology + frozen
  external labels only (§5); selection never calls the engine or `cluster_sources`. Within-
  community words are drawn at random, not picked for sharing a SWOW road, so the probe does not
  pre-encode 1c's answer.
- (c) **No metric encodes the method's answer.** ARI is the standard Hubert–Arabie statistic,
  unit-checked independently; the no-clustering and random controls are graded by the identical
  function against the identical labels, so any shared-input effect (both 1c proximity and
  Louvain read SWOW edge weights) applies equally to all arms and is differenced out by the
  lift. The shared input is the *external graph itself*, which is legitimate; what is forbidden
  — hand-authored edges/labels/probe answers, or tuning 1c's threshold to this set — is not
  done (the threshold `DEFAULT_PROXIMITY_FRACTION = 0.35` is the shipped uncalibrated constant,
  untouched).
- **Honest limitation to report regardless of outcome:** 1c proximity (max directed road
  strength) and the Louvain grader both derive from SWOW edge weights, so they are not
  *fully* independent measurements — they are two different *algorithms* over a shared external
  graph. A positive result is therefore "two unrelated clustering principles agree on external
  structure," not "1c recovers a gold-standard human-labelled taxonomy." This framing is fixed
  here and stated in the final report.

## 9. Artifacts (paths)

- Frozen external-partition generator: `experiments/exp1c_build_partition.py`
- Frozen partition file: `experiments/results/exp1c_external_partition.tsv` (+ SHA-256 in §3.1)
- Experiment runner (probes, 1c, controls, ARI, sign test):
  `experiments/exp1c_recovery.py`
- Self-contained ARI + Louvain unit checks: `experiments/test_exp1c.py`
- Captured output (verbatim): `experiments/results/exp1c_output.txt`

## 10. Run order (must be executed in this sequence — anti-circularity)

All commands run from the repo root `nous/`. The SWOW data file must be present at
`experiments/data/strength.SWOW-EN.R123.20180827.csv`.

```
# 0) grader self-checks (ARI + Louvain) — must print "0 failed" before trusting any verdict
python3 experiments/test_exp1c.py

# 1) FREEZE the external partition (Louvain, full SWOW graph). Prints a SHA-256.
python3 experiments/exp1c_build_partition.py | tee experiments/results/exp1c_partition_build.txt

# 2) PASTE the printed SHA-256 (and node/community counts) into §3.1 of THIS file, once.
#    (This is the only edit permitted after creation, and only this line.)

# 3) RUN the graded experiment, passing the frozen hash so the runner verifies it and
#    refuses to run on any other partition. Capture verbatim.
EXP1C_EXPECTED_SHA256=<paste the SHA-256 from step 1> \
  python3 experiments/exp1c_recovery.py | tee experiments/results/exp1c_output.txt
```

Optional fast smoke (NON-canonical; do not use its numbers for the verdict) — both steps must
use the SAME `NOUS_EXP1C_MAXROWS` so the smoke partition and the smoke run share a word set:

```
NOUS_EXP1C_MAXROWS=200000 python3 experiments/exp1c_build_partition.py   # writes *_SMOKE.tsv
NOUS_EXP1C_MAXROWS=200000 EXP1C_PARTITION=results/exp1c_external_partition_SMOKE.tsv \
  EXP1C_EXPECTED_SHA256=<smoke hash> python3 experiments/exp1c_recovery.py
```
