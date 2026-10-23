# Psyche: Architecture (as built)

This is the **as-built** technical reference for the code in `src/`. It describes what the
eight modules actually do, the data model, the public surfaces and their invariants, and the
key design decisions and *why* they were made. Claims here are traceable to the code and its
docstrings; design rationale draws on the two implementation-plan documents,
[`design/psyche_plan_layer0_topology.md`](design/psyche_plan_layer0_topology.md) and
[`design/psyche_plan_layer1_substrate_store.md`](design/psyche_plan_layer1_substrate_store.md),
and on the specs in [`specs/`](specs/).

Where a component is exploratory, or where a property is mechanism-verified but its *cognitive
meaning* is not claimed, it is labeled as such. The development history that produced these
decisions (the bugs found and fixed) is a separate document: [METHODOLOGY.md](METHODOLOGY.md).

**Assurance, in one line:** the substrate store and spreading-activation engine are `PROVEN`
(determinism, integrity, purity); the field, coalitions, source-clustering, and workspace are
**tester-verified mechanism** that make the cognitive cycle *close end-to-end* — a mechanism
result, with **no cognitive claim**. The body-state sensor (2c) is likewise tester-verified
mechanism, shipped default-off. The first behavioral cognitive claim has been attempted three
times and refused three times before any graded number existed; the meaning bar is open.

## Layering

```
text ─► perceive() ─► cluster_sources() ─► build_activation_field() ─► form_coalitions_from_field()
                            │                       │                          │
   psyche_perceive.py         │  psyche_source_         │   psyche_field.py          │  psyche_coalitions.py
                            │  clustering.py         ▼                          ▼
                            │              spread_activation()  ◄── reads ──  SubstrateStore
                            │              psyche_activation.py                 psyche_store.py
                            ▼                                                       ▲
                     select_winner() ─► prune ─► broadcast()  ── single bounded write ──┘
                     psyche_workspace.py                          (biases the next cycle; closes the loop)
```

- **`psyche_store.py`: SubstrateStore (Layer 1):** Holds the graph; the only component that
  mutates. Contains no "cognitive" logic. **`PROVEN`: determinism, integrity, purity.**
- **`psyche_activation.py`: spreading activation:** The first operation that *reads across* the
  graph. Pure read. **`PROVEN`: determinism, purity; principled approximation.**
- **`psyche_field.py`: multi-source field:** Composes per-source spreads into basins.
  Deterministic, pure. *Tester-verified mechanism; no cognitive claim.*
- **`psyche_coalitions.py`: coalition formation:** Groups co-activated nodes. Deterministic,
  pure. *Tester-verified mechanism; no cognitive claim.*
- **`psyche_source_clustering.py`: source-clustering (1c):** A pure-read pre-stage between
  perception and the field that groups nearby perceived sources and seeds the field from one
  representative per group. Deterministic, pure, integrity-preserving. *Tester-verified
  mechanism; no cognitive claim.*
- **`psyche_workspace.py`: workspace (1d):** One competition among coalitions (1d-i), pruning of
  the bridged unperceived material from the winner (1d-i), and a single bounded broadcast back
  onto the substrate that biases the next cycle (1d-ii). Selection is a pure read; the broadcast
  is the one explicit write. *Tester-verified mechanism — including no-divergence and
  no-lock-in stability of the write; no cognitive claim.*
- **`psyche_perceive.py`: perception + the closed cycle:** Turns text into sources and runs the
  whole loop. `think(..., broadcast=False)` (the default) is a pure read; `broadcast=True`
  performs the single feedback write. *Tester-verified mechanism; the loop closes.*
- **`psyche_bodysensor.py`: body-state sensor + modulation hook (2c):** Derives a scalar from
  live process telemetry and, when enabled, scales the global `decay_per_hop`. Two modes:
  deterministic **replay** over a frozen hashed trace (the entire test surface) and **live**
  (the single isolated boundary, production only). **Default-off**: with no sensor supplied,
  `think()` is byte-identical to 1c/1d. *Tester-verified mechanism; the meaning claim is a
  recorded NOT-YET.*

Everything is pure-Python standard library. Each layer reads the one below it through its
public surface only.

---

## 1. Data model

### Node: `psyche_store.Node`
The atomic unit of information; **always emotionally neutral** (emotion lives on roads, never
on nodes).

| field | type | meaning |
|---|---|---|
| `id` | `str` (uuid4 hex) | stable opaque identity; callers must not interpret it |
| `content` | `str` | the information the node carries |
| `node_type` | `NodeType` | `EVENT · CONCEPT · ENTITY · SENSATION · ABSTRACT` |
| `creation_seq` | `int` | **formation order as data, separate from identity** |
| `formation_time` | `float` | clock time at creation |
| `last_accessed` | `float` | updated by `traverse()` (touch) |
| `access_count` | `int` | how often the node was touched |

### Road: `psyche_store.Road`
A **directed** connection `source → target`. Carries access quality (via `strength`) and a
**multi-valued emotional life** (via `charges`). Decay is lazy.

| field | type | meaning |
|---|---|---|
| `id` | `str` (uuid4 hex) | stable identity |
| `source_id`, `target_id` | `NodeID` | endpoints |
| `creation_seq` | `int` | formation order |
| `formation_time`, `last_touched` | `float` | creation time; clock of last *write*/decay-persist |
| `strength` | `float` | edge weight; a new road starts at `0.05` (faint dirt track) |
| `charges` | `Dict[str, float]` | named feelings → intensity in `[-1, 1]` (e.g. `{"fear": -0.9}`) |
| `closed` | `bool` | sticky barrier state (see §3) |
| `traversal_count` | `int` | number of strengthening crossings |
| `valence` *(property)* | `float` | derived aggregate: clamped mean of `charges` (0.0 if none) |

A single road can hold **several feelings at once** (anger *and* grief on the same path); the
aggregate signed `valence` is derived from them. One road per `(source, target)` pair (see §2).

### Road quality (a read-time classification of `strength`)
`RoadQuality ∈ {CLOSED, DIRT, GRAVEL, ROAD, HIGHWAY}`. `CLOSED` is a *state*, not a strength
band. For open roads the bands are `strength < 0.20 → DIRT`, `< 0.50 → GRAVEL`,
`< 0.80 → ROAD`, else `HIGHWAY`. `quality_of()` decays first, so the quality reflects the
present.

---

## 2. Substrate store: API and invariants

### Public surface (narrow, ID-addressed)
- **Writes (nodes):** `add_node(content, node_type) → NodeID`; `remove_node(node_id)`.
- **Writes (roads):** `add_road(src, tgt) → RoadID` (creation only); `remove_road(road_id)`;
  `strengthen(road_id, charge=None, base_gain=0.13)` (strengthen only).
- **Write (convenience):** `traverse(src, tgt, charge=None) → RoadID`: get-or-add then
  strengthen, plus touch both endpoints. This is one synchronous method, atomic as a unit.
- **Designations/guards:** `designate_self` / `undesignate_self`; `pin` / `unpin`.
- **Reads:** `get_node`, `get_road(road_id, apply_decay=True)`, `exists`, `roads_from`,
  `roads_into`, `neighbors`, `find_road`, `quality_of`, `self_region`, `is_self`, `is_pinned`,
  counts and id iterators.
- **Integrity:** `check_integrity()` (full scan); incremental `_assert_*` on each mutation.

### Invariants and the decisions behind them

**Stable identity vs. ordering (uuid4 IDs, `creation_seq` for order):** Every node and road has
a stable `uuid4` id and is *never* addressed by position. uuid4 (not a counter) so that a bad
reload can never reissue an old id and resolve a stale handle to the *wrong* object: a stale
id resolves to `NotFound`, never to corruption. Formation order, when it matters (e.g.
tiebreaks), is a **separate `creation_seq` integer**. *Why it matters:* the upper layers must
break ties deterministically, and tying on a uuid (regenerated every process) would be
nondeterministic across runs. See METHODOLOGY finding (d).

**One road per pair:** A `(source, target) → RoadID` dedup index (`_pair`) keeps
get-or-add O(1) and guarantees a "simple" graph: the same path carrying two feelings is *one*
road, not two. The reverse direction is a distinct road (directed graph).

**Pure reads / lazy decay (load-bearing):** Roads decay with elapsed time, but decay is
**computed on access as a read-only view**, never written by a read. `_compute_decay(road,
now)` returns `(strength, charges)` *without mutating*; `get_road(apply_decay=True)` returns a
**copy** carrying those decayed values, leaving the stored road untouched. Only writes
(`strengthen`, `traverse`) and the offline pass call `_persist_decay`, which mutates in place
and advances `last_touched`. *Why it matters:* the atomicity model treats reads as safe to
interleave; a read that persisted state could, over time, silently re-open a closed traumatic
edge. METHODOLOGY finding (a) is exactly this bug, caught and fixed. Asserted by
`test_reads_are_pure` and `test_lazy_decay`.

**Sticky closure:** A road closes when an active crossing makes it strongly negative
(`valence ≤ −0.75`) or on one-shot trauma (a crossing with peak intensity `≥ 0.85` and
negative valence). Closure is re-evaluated **only on an active crossing**
(`_open_close_on_crossing`, called from `strengthen`): *never* by a read and *never* by the
passage of time. Time decays charge toward neutral but does **not** reopen a closed road;
only an active positive crossing that lifts valence past `−0.30` reopens it. *Why:* avoidance
preserves trauma rather than dissolving it; "post-traumatic growth" is then an architectural
event (an active positive return), not mere forgetting. Asserted by `test_closure_is_sticky`.

**Pin guard:** `remove_node` refuses (raises `IntegrityError`) to delete a pinned node: you do
not prune what is currently in use (e.g. the node under the attention spotlight). The *policy*
of what to pin lives in a higher layer; the *mechanism* (the guard) lives here. Asserted by
`test_pin_guard`.

**Atomicity by construction:** Every mutation is a synchronous method with no `await` inside.
Under single-threaded asyncio that makes each mutation atomic; there are no locks because there
is no preemption to lock against.

**Integrity:** Adjacency/dedup/designation consistency is asserted incrementally on every
mutation (cheap, gated by a `debug` flag, on in development). `check_integrity()` is a full
orphan/drift scan for an offline pass: every road's endpoints exist, every index entry points
to a live road, the pair-index agrees, and designations/pins reference live nodes. Asserted by
`test_deletion_leaves_no_dangling_index` and `test_integrity_catches_nothing_when_clean`.

**Clock:** A `Clock` abstraction allows simulated time so tests can advance the clock by hand
and observe decay instantly; `advance()` is simulated-only and raises in real mode (sleeping
there would block the event loop). Asserted by `test_clock_advance_is_simulated_only`.

### Decay dynamics (pure functions)
Strength decays exponentially with a time constant that **scales steeply with strength**, so a
highway is dramatically more stable than a dirt track: `tau = 45 · exp(strength · 4.2)`,
`new_strength = strength · exp(−dt / tau)`. Charge mellows toward neutral on a slower clock
(`exp(−dt / 90)`); a feeling that fully fades (|value| < 1e-4) drops off the road. Closure is
deliberately **not** part of decay (it is sticky).

---

## 3. Spreading activation

`spread_activation(store, seed_node, *, energy=1.0, decay_per_hop=0.65, floor=0.02,
hop_budget=6) → ActivationResult`. Radiate activation outward from a seed along directed
out-roads and report what lit up. **Pure read: mutates nothing:**

`ActivationResult` carries `activation: NodeID → float` (final accumulated), `hops: NodeID →
int` (settle distance), `broke_through: List[RoadID]` (closed roads that leaked), and `flow:
RoadID → float` (activation each edge actually transmitted). `.ranked()` returns reached nodes
by activation, seed excluded.

**Convergent activation SUMS:** A node lit from several paths is more active; that convergence
is half of what makes the operation cognitive. Asserted by `test_convergent_activation_sums`.

**Hop-layered single-expansion (deterministic):** The wave is expanded in **hop layers**: all
hop-k contributions accumulate before any hop-k node expands, and each node expands **exactly
once**, at the first hop it is reached, carrying the full sum of all paths of length ≤ that hop.
Before any node in a layer expands, the layer's expansion values are **frozen** into a
snapshot, so a same-hop sibling that increments a node via an intra-layer edge cannot change
what that node expands with this layer (its contribution propagates only in the *next* layer).
*Why this and not a best-first/priority frontier:* (1) **determinism:** with a priority heap,
*which* late ripple gets dropped depends on tie-ordering and tiny strength differences, i.e. on
hash-randomized set iteration over uuid keys, so results wobbled across process runs;
(2) **principled approximation:** "strictly-longer-path ripples don't propagate further" is a
meaningful rule, whereas "whichever parent popped later doesn't ripple" is arbitrary.
Equal-length convergence is **exact**. See METHODOLOGY findings (b) and (c); asserted by
`test_no_double_count_downstream_of_convergence`,
`test_expansion_is_deterministic_under_edge_strength`, and the cross-process
`test_determinism_with_same_hop_edge_adversarial`.

**Two attenuators, distinct on purpose:** `transmitted = outgoing · road.strength ·
decay_per_hop`. `road.strength` is **edge conductance** (a property of the connection: a weak
road carries less of whatever reaches it); `decay_per_hop` is the **global distance penalty** (a
property of the spread: activation weakens with cognitive distance regardless of any single
road). Keeping them separate keeps tuning legible. Asserted by `test_stronger_road_carries_more`.

**Closed roads are leaky, not inert:** All "what crosses a closed road" logic lives behind one
swappable policy, `closed_transmission(incoming, road)`: below a breakthrough threshold (`0.50`)
nothing passes (the barrier holds); above it, a small attenuated fraction (`0.15`) leaks
through, and the road is logged in `broke_through`. This is *intended to evoke* intrusive
recall: avoided material that a strong enough cue reaches anyway, but it is an uncalibrated
sketch, not a validated model of that phenomenon. **These constants are uncalibrated guesses on
probation:** the tests pin the qualitative regime (weak blocked / strong leaks, and leaked flow
is far weaker than an equivalent open road), never the magnitudes, and nothing downstream may
depend on the numbers. Asserted by `test_closed_transmission_regime` and
`test_closed_road_blocks_weak_passes_strong`.

**Flow records what the spread actually did:** `flow[road_id]` is the activation a road
transmitted *after* all attenuation. It is distinct from static topology: a road that exists but
carried nothing is not in `flow`; a blocked closed road is not in `flow`; a leaked closed road
**is** (with its attenuated value). Downstream consumers that need "which connections the thought
actually used" must read `flow`, not the store's edges. Asserted by
`test_flow_records_what_transmitted`.

**Locality & termination:** The `hop_budget` and `floor` keep the spread in the seed's
neighborhood (never a whole-graph wave), which is what makes it affordable every cycle in pure
Python. Cycles terminate because each node settles/expands once. Asserted by
`test_cycle_terminates`, `test_locality_hop_budget`, `test_floor_keeps_it_local`. Purity asserted
by `test_spread_is_pure_read`.

---

## 4. Multi-source activation field

`build_activation_field(store, sources, …) → ActivationField`. **Why it exists:** coalition
formation first tried to segment a *single*-seed spread, but a single seed produces one
activation peak and monotonically-decaying flow, so *distance from the seed* is the only strong
signal: every segmentation rule keyed off it, and flow-magnitude was even anti-correlated with
community membership near the seed. The fix is upstream of the segmentation algorithm: use
**multiple sources** (the real cognitive architecture's ATTEND phase consumes several
simultaneous sources: percept, goals, emotion), which yields multiple genuine peaks so that
*basins around peaks* become natural. See METHODOLOGY finding (e).

It reuses the proven single-source `spread_activation` unchanged, once per source, and assembles:
- `per_source: SourceID → (NodeID → activation)`,
- `total: NodeID → Σ activation across sources` (genuine convergence across concerns),
- `dominant: NodeID → the source that activated it most` (its **basin**),
- plus merged `flow` and `broke_through`, and the underlying `results`.
`.basin(source_id)` returns the nodes that source dominates.

**Determinism:** Each per-source spread is already deterministic; **dominant-source ties break
on the source's `creation_seq`** (stable), never the uuid, and sources are iterated in
`creation_seq` order, so the whole field is deterministic given store state. Sources are
de-duplicated while preserving order. **Pure read:** Asserted by `test_field_sums_across_sources`,
`test_dominant_source_assignment`, the adversarial two-community
`test_acceptance_multisource_recovers_communities`, and the cross-process
`test_field_determinism_adversarial_across_hash_seeds`.

---

## 5. Coalition formation

Two entry points, both pure reads, both deterministic by construction.

**`form_coalitions(store, result, …)`: flow-cut segmentation of a single spread:** A coalition
is a group of co-activated nodes connected by **strong carried flow**. The co-activated set is
the nodes at/above `coherence_floor` (0.05). The binding graph is built from `result.flow` (not
static topology), keeping only edges whose **both** endpoints are co-activated and whose flow is
at or above a **relative** cut, `flow_cut_fraction × max_observed_flow` (0.35 × max). Coalitions
are the connected components of that thinned graph: cutting weak-flow edges subdivides the
otherwise seed-connected region into more than one coalition (the property the downstream
competition needs). Using flow respects closure for free: a blocked road has no flow entry, so it
never binds. Asserted by `test_single_seed_spread_yields_multiple_coalitions` and
`test_binding_respects_closure`.

**`form_coalitions_from_field(field, store, …)`: group-by-basin (the non-degenerate path):**
Each source's basin becomes a candidate coalition: the territory of one active concern; a node
bridging two concerns belongs to whichever pulled it harder, so seams fall *between* centers
rather than being an artificial cut in one blob. Members carry their `total` (summed) activation.

**`Coalition`** holds `members: NodeID → activation`, `strength` (sum of member activations),
`intrusive` (true if any member was reached via a closed-road breakthrough),
`breakthrough_members`, and `_seq` (each member's `creation_seq`). `representative()` is the
most-active member with a **stable** `creation_seq` tiebreak (never the uuid);
`canonical_member_order()` is `creation_seq`-sorted. Coalitions are returned strongest-first by
an explicit, fully stable total order: `(−strength, −size, min creation_seq)`. *Why so much care
about order:* clustering is the classic home of hidden order-dependence; every output-affecting
order here is an explicit total order over intrinsic, reproducible keys. Asserted by
`test_representative_is_most_active_deterministically`, `test_coalition_formation_is_pure_read`,
and the cross-process `test_determinism_adversarial_across_hash_seeds`.

**Intrusive nodes are flagged, not forced:** A node reached only via a breakthrough is marked
(the structural sign of avoided material surfacing) but its coalition membership is decided by
the same flow/basin structure as everything else, not by fiat. Asserted by
`test_intrusive_node_is_marked` and `test_intrusive_node_in_field_coalition`.

---

## 6. Source-clustering (the pre-field stage, 1c)

`cluster_sources(store, sources, …) → SourceClustering`. The closed loop surfaced a real
problem: perception emits *clustered, overlapping* source sets (e.g. `coffee`, `kitchen`,
`morning` all in one domain), so basins are meaningless until nearby sources are merged or
grouped first. This stage sits **between perception and the field** and is a **pure read**.

- **Mechanism.** It groups nearby perceived sources by **single-link clustering on a source
  proximity graph**, where proximity is **topology / road-strength only** (the "A1" signal:
  the strongest directed road between two sources). It then seeds the field from **one
  representative per group** (highest source energy; ties broken on `creation_seq`, never the
  uuid). Single-link **chaining** (A–B–C grouped though A–C are not directly near) is
  intentional. The relative proximity threshold is an **uncalibrated design constant**
  (`DEFAULT_PROXIMITY_FRACTION`), pinned only qualitatively by the tests.
- **Integration.** It is wired into the live `think()` loop **without changing the perception
  surface or the field-builder signature**: the field is seeded from group representatives
  rather than the raw source set.
- **Why A1 and not activation-overlap (A2).** An activation-overlap proximity signal was
  rejected at build time for circularity (it would let the field leak back into the grouping).
  A structural test asserts `cluster_sources` has no field/per-source parameter, so the field
  *cannot* influence the partition.
- **Verification (mechanism only).** Deterministic across 6 hash seeds in fresh interpreters,
  pure (clustering mutates nothing — road strengths and traversal counts unchanged), integrity-
  preserving (the store's integrity scan is unchanged before/after), and scale-invariant
  (scaling energies/proximities by a constant keeps the partition). It carries an explicit
  asserted-negative that the grouping is **topological only — no cognitive claim**.

**No cognitive claim.** Source-clustering is a topological grouping mechanism. A separate,
non-canonical structural check compared this grouping against an independent standard partition
of the SWOW graph and returned an honest **NOT YET** (it beats the no-clustering control
decisively but under-merges relative to a coarse standard partition); that result lives in the
disciplined-exploratory tier, not here, and does not move this layer out of `BUILT · UNVALIDATED`.

---

## 7. The workspace: competition, pruning, and bounded broadcast (1d)

`psyche_workspace.py` is what the old "strongest coalition = the thought" placeholder stood in
for. It is built as two bricks.

### 7.1 Competition + pruning (1d-i) — a pure read

`select_winner(store, coalitions, …) → Workspace`. Among the system-generated coalitions, **one
winner** is selected by **activation density** (A2), normalized so a tight, intensely-active
coalition beats a larger sprawling one of equal *total* activation, with a **min-size guard** so
a degenerate tiny coalition cannot win on density alone. `Workspace` exposes the `ranked` list of
all candidates in competition order (`raw_winner` is `ranked[0]`), the chosen `winner`, and the
`pruned_members`.

- **Pruning rule (the realized, accepted design).** The winner is pruned by a **parameter-free
  cohesion-valley / relative-attachment watershed**: a reached member is kept iff it is pulled
  toward the named (perceived) region *at least as strongly* as toward the unnamed region; else
  it is pruned. This removes the **bridged, unperceived** domain (e.g. a `work`/`code` region
  reached only through a bridge) from the winner, which is the half of the old over-swallow
  limitation that 1c could not fix on its own. The rule is **threshold-free** (no calibrated
  constant lives in pruning) and generalizes.
- **A known, accepted divergence (shipped as an asserted-negative).** The watershed is **not**
  literal domain-membership. An unnamed domain bridged into the named region **at least as
  strongly as its own internal cohesion** has no valley and is therefore **kept** — so
  over-swallow can recur in that one topology. This divergence is always **safe-direction**: it
  can over-*include* an unnamed domain, but it can never over-*prune* a perceived member
  (verified across random adversarial graphs, and with an anti-overcorrection control: a *named*
  domain is never pruned). It is documented as a standing asserted-negative, not hidden.
- **Verification (mechanism only).** Exactly one winner is selected deterministically across 6
  hash seeds; winner + `pruned_members` + ranked order are byte-identical across processes;
  selection is a pure read (repeated calls mutate nothing); integrity is unchanged; the flip of
  the over-swallow case generalizes on an independently-built isomorphic-but-relabelled graph
  (so it is not tuned to the `coffee`/`work` fixture).

### 7.2 Bounded broadcast + feedback (1d-ii) — the single write that closes the loop

`broadcast(store, winner) → Broadcast`. This is the one explicit, bounded write back onto the
substrate: a **bounded strengthening of the winner's internal roads** (reusing the store's
`strengthen()`), which biases the next cycle. This is what turns a one-shot pipeline into a
**loop**.

- **Exactly scoped.** The broadcast strengthens **only** roads internal to the winner, **once
  each**, **creates no new road**, and **touches no node** (nodes stay neutral, consistent with
  the substrate design). The bridge and the unperceived domain's roads are not touched. A
  convergence guard asserts each broadcast road's `traversal_count` increments by exactly 1.
- **Bounded both ways — and the boundedness is structural, not a clamp.** Over many cycles, road
  strength stays ≤ 1.0 and the broadcast aggregate **plateaus** (per-cycle deltas → ~0): the
  system **does not diverge**. This boundedness comes entirely from `strengthen()`'s
  `(1 − strength)` saturation (fixed point 1.0, approached from below, never exceeded) — there is
  **no clamp, cap, or tunable magnitude** added in `broadcast()`. It also **does not lock in**:
  after deeply biasing winner A over many cycles, a strong fresh percept favoring domain B
  **switches** the winner to B (escape proven **non-vacuously** — A is verified dominant
  immediately before the switch — on a hostile bridged graph, with a freeze-mode probe and a
  close-competition differential control).
- **The broadcast magnitude is uncalibrated.** It inherits `strengthen()`'s default gain and is
  **not** tuned to any external or cognitive outcome.

### 7.3 `think(broadcast=...)` — pure-read default vs. the single broadcast write

`think(store, utterance, *, hop_budget=6, broadcast=False) → ThoughtResult` is the closed
end-to-end cycle: `perceive → cluster_sources → build_activation_field (seeded from
representatives) → form_coalitions_from_field → select_winner → prune → (optionally) broadcast`.

- With the default **`broadcast=False`**, the whole cycle is a **pure read**: the store is
  byte-identical across repeated calls (asserted, including interleaved with a separate
  `broadcast=True` store).
- With **`broadcast=True`**, the cycle additionally performs the **single bounded write** that
  closes the loop and biases the next cycle; `ThoughtResult` then carries the non-empty
  `Broadcast` (it is `None` on the pure-read path).

**Hostile inputs are recorded no-ops, not crashes.** An utterance that names nothing, or a lone
isolated perceived node with no internal road, yields an empty broadcast and mutates nothing.

**No cognitive claim anywhere in §7.** The winner is a *selected information structure* and the
broadcast is a *bounded conduction bias* — neither is priming, awareness, or understanding.
Closing an information loop with bounded feedback is a **mechanism** property, verified by the
tester, not a cognitive result.

---

## 8. Perception (the entry stage)

`perceive(store, utterance, source_energy=1.0) → Perception`. `_tokenize` lowercases, keeps
`[a-z0-9]+` tokens of length ≥ 3. A node becomes a **source** if any token appears (substring) in
its lowercased content; energy grows with the number of distinct matching tokens and saturates
(`scale = 1 − 0.6^hits`, `energy = source_energy · (0.6 + 0.4·scale)`). **The input — matched
against the substrate — decides which nodes light up; sources are not hand-placed.** That is the
whole point of this layer (METHODOLOGY finding (f)). It is deliberately minimal: exact/substring
matching, **no embeddings, no fuzzy semantics** — a placeholder for a real perception system, and
the only stage that is still a placeholder in the cycle.

**The closed loop is where the honesty bites.** Asserted *mechanics* (durable): perception is
input-driven, the cycle runs end-to-end and closes, it is pure on the `broadcast=False` path, and
it is deterministic across hash seeds. The earlier draft of this document described the cycle
ending in an **incoherent "thought"** on clustered input, asserted as a known-limitation; that
limitation is now **resolved at the mechanism level** by §6 (source-clustering) and §7 (workspace
pruning) — the perception suite's old known-limitation test has been re-expressed as the now-passing
behavior (the stranded-source half fixed by 1c; the over-swallow half fixed by 1d-i), with the one
residual corner case (§7.1) shipped as an asserted-negative.

---

## 9. Body-state sensor and the modulation hook (2c)

`psyche_bodysensor.py`. Interoception in the only sense this codebase permits the word: **a scalar
computed from live OS/process telemetry, injected at a defined point in the cycle, which
causally changes what the cycle does.** It is not a claim that the system feels anything, has a
body, or is aware of its own state; the vision document this descends from
([`design/psyche_the_bodys_voice.md`](design/psyche_the_bodys_voice.md)) is quarantined as vision,
and SPEC-2c §0.1 states that firewall as an acceptance condition.

### 9.1 The signal

```
friction = clamp(1 - cpu_dt/wall_dt, 0, 1)          # compute_friction()
```

`cpu_dt` from `time.process_time()`, `wall_dt` from `time.perf_counter()`. The quantity is a
**stall fraction**: ≈ 0 when the process runs flat-out (`wall ≈ cpu`), rising only as the process
waits **off-CPU**. Load average and RSS growth are specified as secondary robustness signals and
must each come from their own named OS call — a signal re-derived from graph state (for example
"memory pressure := active-node-count") is a graph-internal quantity in a telemetry costume and
is forbidden.

### 9.2 The coupling

```
decay_factor = 1 - MODULATION_SPAN * friction       # MODULATION_SPAN = 0.6
effective_decay = decay_per_hop * decay_factor      # modulated_decay_per_hop()
```

As friction goes 0 → 1 the factor falls 1.0 → 0.4. Because the engine's transmission line is
`transmitted = outgoing * road.strength * decay_per_hop`, a **lower** `decay_per_hop` means less
activation survives each hop, so the spread becomes **more local**. The pre-registered direction
is therefore *higher friction → more local spread*, fixed against Easterbrook's cue-utilization
narrowing. This is a diffuse global gain change that names no node and no coalition — the
design's analogue of a neuromodulator, and at most the *shadow* of a neuromodulatory-gain or
somatic-marker bias.

### 9.3 The two-mode determinism design (binding)

- **Replay** — a frozen, SHA-256-hashed telemetry trace. Identical replayed input must yield
  byte-identical output across separate processes and across every swept hash seed. **All**
  tester-grade verification runs here; a mechanism test that reads live telemetry is not a valid
  mechanism test and is rejected.
- **Live** — read **only at the boundary**, production only, and explicitly *not* part of the
  deterministic test surface. This mirrors `Clock(simulated=...)`.

Both guards hold simultaneously and neither is relaxed for the other: a result must be **emergent**
(a categorical winner-flip, never a scalar echo of the injected number) **and** reproducible from
the frozen trace. Reproducible-but-echo is VOID for circularity; flips-but-unrepeatable is VOID
for non-determinism.

### 9.4 Status

Mechanism is tester-verified: default-off byte-identity under attack, replay determinism in fresh
processes, live telemetry proven off the deterministic surface (timers monkeypatched to detonate),
and the anti-circularity guard that two distinct frictions mapping to the same effective decay
produce the *same* winner. A couplability pilot cleared its pre-fixed floor, establishing that the
loop genuinely can be moved by this channel.

**The meaning claim is a recorded NOT-YET, and the reason is the yardstick, not the loop.** On a
realistic `think()` workload the friction signal does not vary meaningfully from real machine
contention: `think()` is CPU-bound, so `wall ≈ cpu`; the signal is a ratio and therefore
scale-invariant in work magnitude; and CPython's collector runs in-thread and counts as CPU time,
so garbage collection makes `think()` slower without raising friction. Any band wide enough to
grade would have to be **manufactured** by an injected sleep, a forced swap, or core saturation —
which the anti-manufacture guard forbids. This is recorded as the finding rather than rescued.

---

## Cross-cutting design principles

- **Activation and consolidation are different events:** Spreading activation is a *pure read*
  and never strengthens what it touches: reinforcement is a separate, gated act (the
  STC-*inspired* "plasticity budget"). If thinking reinforced for free, it would steal the job a
  future neuromodulation layer owns.
- **Determinism is a first-class requirement, not a nicety:** The natural implementations leak
  uuid set-iteration order into results; every layer is built to be a deterministic function of
  store state, and that is verified across process hash-seeds in fresh interpreters.
- **Uncalibrated constants are quarantined:** The breakthrough threshold/leak fraction, the
  flow-cut fraction, the source-clustering proximity threshold, and the broadcast gain are
  first-pass / inherited defaults; tests pin only the qualitative regime, and nothing downstream
  may depend on the magnitudes until an externally-graded result can calibrate them.
- **Honest boundary (three tiers, kept distinct):**
  - **`PROVEN`** — substrate + activation: mechanism proven (determinism, integrity, purity).
  - **tester-verified mechanism (`BUILT · UNVALIDATED`)** — field, coalitions, source-clustering,
    and the workspace (competition + pruning + bounded broadcast). The cognitive cycle **closes
    end-to-end** and is independently, adversarially tester-verified — but **as mechanism only**.
    Closing the loop is *not* a cognitive result.
  - **open frontier** — the first behavioral cognitive claim (semantic priming through the closed
    loop, graded against human SWOW norms) has **not** been run. No cognitive meaning is claimed
    by any layer above.

  See [METHODOLOGY.md](METHODOLOGY.md), [`psyche_roadmap.md`](psyche_roadmap.md), and the README's
  scope statement.
