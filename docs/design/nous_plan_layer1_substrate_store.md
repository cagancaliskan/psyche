# Nous — Implementation Plan
# Layer 1: The Substrate Store

### Status: DRAFT for review. Planning only — no code.
### Depends on: Layer 0 (closed). Decides: how the one graph is held, mutated,
### kept consistent under continuous growth and pruning, and touched safely by
### single-threaded asyncio.

---

## The Decision, Up Front

**v1 representation: a pure-Python object graph, addressed exclusively by stable
permanent IDs, with dict-based indices.** No vectorization. No worker pool. The
array-backed hybrid is documented below as a *mechanical migration* taken if and
only if a profiler shows the object graph is the wall AND the millions-of-nodes
ambition stops being a someday.

This is the same discipline that unlocked the worker pool in Layer 0: build the
simplest correct thing, and buy performance later, deliberately, once profiling
says what to optimize. Premature vectorization is premature concurrency wearing a
different hat — it costs weeks, may never pay off, and would cost the thing year one
needs most: the ability to **read and debug** a brain doing things we did not predict.

---

## Why Object-Graph-First Is Correct (the three questions, resolved)

The representation falls almost entirely out of **scale ambition**, with the other
two considerations reinforcing the same answer.

### Scale — nearly dispositive
The honest near-term runnable target governs, not the north star.

```
~10,000–50,000 concepts (a bonded brain over a long relationship):
    completely comfortable as a pure-Python object graph + dict indices.
    No vectorization needed. You will not feel pain.

millions of nodes (read-the-libraries ambition):
    this is the ONLY thing that forces vectorization.
```

The build-first answer is therefore the object graph, with the hybrid as a future
migration triggered by a real profiled bottleneck — not designed-in now on
speculation.

### Locality — answered by the architecture itself
A Global Workspace is **inherently local per cycle**: one coalition wins and is
broadcast; activation radiates from the spotlight through its neighborhood, not as a
whole-graph wave at 10 Hz. The only genuinely whole-graph workloads are **decay,
pruning, consolidation** — and those are the Tempo-2 slow-background and Tempo-4
offline passes, where a full sweep is affordable even in pure Python.

```
EVERY CYCLE (T1):   local — neighborhood around the spotlight only
SLOW / OFFLINE:     global — full sweeps, but rare and time-tolerant
```

Local-every-cycle does not force vectorization. It reinforces object-graph-first.

### Inspectability vs speed — year-one favors inspectability
The entire risk of the project is whether the brain does anything interesting and
whether emergent behavior can be debugged. **You cannot debug a brain you cannot
read.** Printing one road and seeing its whole life — strength, charge, emotional
history, quality, open/closed — is a development asset that outweighs throughput not
yet needed. Speed is bought later. Legibility is needed now.

---

## THE REAL HARD PROBLEM: continuous mutation + stable references

This, not field-hotness, is what Layer 1 lives or dies on — and it is the thing that
makes the *future* hybrid migration safe rather than a source of silent corruption.

Nous is not a static graph computed over. It **grows** every time it learns (new
nodes, new roads) and **shrinks** every time the pruning daemon runs (dead roads and
nodes removed). Two facts collide:

```
- Object graphs mutate easily (add/remove objects, references stay valid) but
  traverse slowly.
- Array-backed graphs traverse fast but mutate painfully: deletion forces either
  tombstoning (holes accumulate; compute wasted sweeping dead slots) or compaction
  (cheap to run, but RENUMBERS every array index — silently invalidating every
  index-based reference held anywhere else).
```

The references that would be silently invalidated by naive renumbering are not
incidental — they are load-bearing pieces of the Layer-0 topology:

```
  the SELF-region designation        (which subgraph is "self")
  the attention registry's watchlist (the 3-tier significant-cue list)
  the spotlight pointer              (what currently holds depth)
  the ingress queue contents         (pending perception targets)
  MOTIVATION's subgoal queue         (references to goal/target nodes)
  any held reference, anywhere
```

If any of these stored a raw array index, a single compaction pass would corrupt the
brain. So the representation must be designed, from day one, to make references
survive both mutation now (object graph) and compaction later (hybrid).

### The resolution: stable IDs as the only address

**Everything is addressed by a stable permanent ID, never by position.** This is the
single most important rule in Layer 1, and it is what makes the future migration
mechanical instead of a rewrite.

```
RULE: No system ever holds an array index or a raw object reference as its durable
      handle to a node or road. It holds the stable ID. It resolves the ID to the
      live object (v1) or to the current array index (future hybrid) through the
      STORE's lookup, every time it needs the actual data.
```

Concretely, for v1 (object graph) this means:

```
  NodeID, RoadID                — opaque stable identifiers (e.g. uuid4 or a
                                  monotonic counter; opaque so callers can't do
                                  arithmetic on them)
  nodes:  Dict[NodeID, Node]    — the authoritative node table
  roads:  Dict[RoadID, Road]    — the authoritative road table
  adjacency indices keyed by ID — out[NodeID] -> set[RoadID],
                                  in[NodeID]  -> set[RoadID]
  the SELF-region               — a set[NodeID], not a list of objects
  the registry / spotlight /
  queues / subgoal lists        — all hold IDs, never objects or indices
```

Holding IDs (not objects) even in v1 looks like a small extra indirection (a dict
lookup) for no immediate payoff. It is paid deliberately, because:
1. it makes deletion safe *now* (removing from the tables can't leave a dangling
   object reference held elsewhere — held IDs simply fail to resolve, which is a
   checkable condition, not a crash),
2. it makes the hybrid migration *mechanical later* (swap "resolve ID → object" for
   "resolve ID → current index"; nothing else changes), and
3. it gives a single chokepoint for validation, logging, and the compaction remap.

### The future hybrid migration (documented now so it stays mechanical)

If and when profiling shows the object graph is the wall and scale demands it:

```
  Hot numeric fields → structure-of-arrays:
      strength[], charge[], last_update[], quality-cache[], source_idx[], target_idx[]
      adjacency → sparse CSR-style, so spreading activation = sparse matrix-vector
      multiply (and NumPy releases the GIL → a thread pool parallelizes with no copy)
  Cold/rich metadata → side table keyed by stable ID:
      structured emotional context, variable-length tags, formation provenance,
      anything that doesn't fit a numeric array
  The bridge that makes it safe:
      id_to_index: Dict[RoadID, int]   (and the node equivalent)
      tombstone on delete (mark slot dead; do not renumber mid-life)
      COMPACT DURING SLEEP-MODE: the Tempo-4 offline phase already prunes; add one
      index-remap pass that compacts the arrays and rewrites id_to_index in a single
      sweep. Because every external handle is an ID (never an index), the remap fixes
      every held reference at once, atomically, while the brain is offline and nothing
      is mid-traversal.
```

That co-location — compaction riding alongside the pruning that already runs in
sleep-mode — is what makes the hybrid buildable rather than a perpetual source of
index-corruption bugs. It is the reason the v1 "address by ID only" discipline is
non-negotiable: it is the seam the migration slides into.

---

## The Substrate Store's Responsibilities (v1)

The STORE is the one component every system touches. Its job is narrow and total:
hold the graph, mutate it safely, resolve IDs, maintain indices, and expose read/
write operations that other systems call. It contains **no brain logic** — it does
not decide what to remember or strengthen; it is the tissue, not the thought.

```
STORE
  authoritative tables:   nodes: Dict[NodeID, Node],  roads: Dict[RoadID, Road]
  indices:                out[NodeID]->set[RoadID], in[NodeID]->set[RoadID]
  designations:           self_region: set[NodeID]   (a designated subgraph)
  id generation:          new_node_id(), new_road_id()  (opaque, monotonic)

  WRITE operations (mutations):
    add_node(content, type) -> NodeID
    add_road(src_id, tgt_id) -> RoadID          (faint dirt; or returns existing)
    strengthen(road_id, experienced_charge)     (the traversal mutation)
    apply_decay(scope)                           (T2 local / T4 global sweep)
    remove_road(road_id)                         (delete + index cleanup)
    remove_node(node_id)                         (delete node + its roads + cleanup)
    designate_self(node_id) / undesignate_self(node_id)

  READ operations (queries):
    get_node(node_id) -> Node | NotFound
    get_road(road_id) -> Road | NotFound
    roads_from(node_id) -> Iterable[RoadID]
    roads_into(node_id) -> Iterable[RoadID]
    neighbors(node_id) -> Iterable[NodeID]
    quality_of(road_id) -> RoadQuality
    exists(id) -> bool

  INTEGRITY:
    every read resolves an ID; a stale ID returns NotFound, never a crash
    every delete leaves no dangling index entry
    invariant checks runnable on demand (no orphan roads, no index/table drift)
```

Every other system in Layer 0 is expressed in terms of these operations and nothing
else. MEMORY is mostly `strengthen` + `apply_decay`. PERCEPTION is mostly `add_node`
+ `add_road`. The cognitive cycle reads `neighbors` / `roads_from` to radiate
activation locally. Pruning (sleep-mode) is `remove_road` / `remove_node` in bulk.
This narrowness is deliberate: it is the chokepoint that the hybrid migration, the
atomicity model, and integrity checking all hang on.

---

## THE ATOMICITY MODEL (single-threaded asyncio)

Framed correctly this time: under single-threaded asyncio there are **no data
races** — coroutines run on one thread and never preempt each other. The *only*
hazard is **logical interleaving**: an `await` landing in the middle of a multi-step
mutation that needed to complete as a unit, letting another coroutine observe or
mutate a half-updated substrate.

```
THE RULE:
  A substrate mutation that spans multiple steps must not contain an `await`
  between its first and last step. The whole mutation runs to completion within a
  single synchronous stretch of one coroutine before control can yield.
```

What this means in practice:

```
- STORE write operations are SYNCHRONOUS functions (no `await` inside a mutation).
  add_road, strengthen, remove_node etc. complete fully before returning. They never
  yield mid-mutation. This makes each one atomic by construction — there is no point
  at which another coroutine can interleave, because control never leaves.

- A "critical section" here is simply: a synchronous span that reads-then-writes
  related substrate state. Keep it synchronous; do not sprinkle `await` into it.
  If a sequence of mutations must be atomic together (e.g. remove a node AND all its
  roads AND its self-designation), implement it as ONE synchronous STORE method, not
  as several awaited calls a scheduler could split.

- `await` is for I/O and for yielding between cognitive-cycle steps — NOT for the
  interior of a substrate mutation. The boundary is bright: between operations, yes;
  inside an operation, never.

- Long offline sweeps (T4 pruning/compaction) that would block the loop too long are
  the one place to be careful: they either run while the brain is asleep (fast loop
  quiet, blocking acceptable) or are chunked into synchronous batches with explicit
  yields BETWEEN batches (never mid-batch), so each batch is individually atomic and
  the loop can breathe in the gaps.
```

This is far smaller and more tractable than locks-everywhere. There are no locks at
all in v1, because there is no preemption to lock against. The discipline is purely:
**mutations are synchronous; `await` only between operations, never inside one.**

(If the future hybrid ever introduces a real thread pool for NumPy work, *that* is
when genuine concurrency enters and a real synchronization scheme is needed — and it
is scoped to the array layer, behind the same ID chokepoint. Recorded; not now.)

---

## What Layer 1 Deliberately Does NOT Decide

- **The exact fields on Node and Road** beyond what the prototype established →
  Layer 2 (MEMORY), where road dynamics are detailed. Layer 1 fixes only that they
  are ID-addressed objects in dict tables.
- **The activation-spread algorithm** (how far, how it attenuates, ignition) →
  Layer 2 (cognitive cycle / MEMORY).
- **Pruning policy** (what gets removed, thresholds) → Layer 2 (sleep-mode + MEMORY).
  Layer 1 fixes only the *mechanism* (`remove_*` + safe index cleanup) and *when*
  compaction would ride alongside it (offline).
- **Persistence format** (how the tables serialize to disk) → Layer 4. Layer 1 fixes
  only that IDs are stable across save/load (so a reloaded brain's references still
  resolve).
- **When/whether to migrate to the hybrid** → deferred to a profiled bottleneck; the
  migration's shape is documented above so the decision is mechanical, not a rewrite.

---

## Resolutions (Layer 1 now settled)

The forks and gaps are closed:

**Forks**
1. **ID scheme → uuid4 for identity + `creation_seq` integer for order.** Overturned
   the monotonic-counter lean: a persisted counter risks reissuing an old ID on a
   bad reload, resolving a stale reference to a *new wrong object* — silent corruption,
   strictly worse than NotFound. uuid4 makes that impossible and is merge-safe. The
   monotonic→index "benefit" was illusory (IDs stay stable while compaction renumbers
   indices, so `id_to_index` is needed regardless). Formation order is data, not
   identity → explicit `creation_seq` field on Node and Road.
2. **`strengthen` is split from creation.** `add_road` is the only road-creating
   primitive; `strengthen(road_id, ...)` returns NotFound on a missing road. Biology
   ("first traversal lays the path") lives at the behavior level as a synchronous
   `traverse(src,tgt,charge)` = get-or-add-then-strengthen.
3. **Self-region is a separate `set[NodeID]`.** Cleaner (matches unowned-data) *and*
   faster (O(1) membership, O(region) enumeration vs O(N) scan for a boolean flag).
4. **Integrity checks: incremental invariant at mutation time + full scan offline.**
   Adjacency consistency asserted on every mutation (cheap); the expensive orphan/drift
   scan runs each offline pass. Behind a debug flag; always-on in year one.

**Gaps (all real, all closed)**
5. **Simple graph, not multigraph: one road per (src,tgt) pair with structured
   multi-charge.** "A road has an emotional life" — the same path carrying anger *and*
   grief is one road with multi-valued charge, not two roads. Requires a
   `(src,tgt) → RoadID` dedup index so get-or-add is O(1), not an O(out-degree) scan
   on a hot path. (The exact shape of multi-valued charge is a Layer-2 MEMORY detail;
   Layer 1 fixes only that a road is unique per pair and that charge is a structured
   field, not a scalar that forces a second road.)
6. **Lazy decay, not a global sweep.** Each road stores `last_touched`; decay is
   computed *on access* as f(now − last_touched), applied when the road is read or
   strengthened. Untouched roads need no active decay until the pruner examines them
   offline. This turns the one unavoidable O(N) workload into local work and fits the
   locality argument. It shapes the Road fields now.
7. **Pin guard.** Deletion is safe (stale ID → NotFound) but not complete: pruning the
   node the spotlight points at mid-cycle is a real bug. The STORE holds a
   `pinned: set[NodeID]` and `remove_node` refuses (or defers) a pinned node. The
   pruning *policy* is Layer 2; the *mechanism* to express "don't prune the pinned" is
   here.
8. **Quiescence is an invariant.** Compaction renumbering is correct *only* with no
   concurrent awake mutators. Stated as a hard invariant: **sleep-mode guarantees
   quiescence, and that is why compaction lives there.** Any future change that lets a
   loop run during sleep must preserve this or the remap silently breaks.

These change the v1 data model in three concrete ways the build must reflect:
`creation_seq` on Node/Road; `last_touched` on Road with decay-on-access; a
`(src,tgt)→RoadID` dedup index and a `pinned` set on the STORE.

---

## Post-Build Corrections (found by running the code)

Building the STORE surfaced problems invisible in the planning prose. Recorded here
because they corrected real decisions, and because the lesson — *run it, don't trust
the plan* — is part of the method now.

**C1 — Lazy decay must be pure on read (the load-bearing fix).** The first
implementation applied decay *in place* inside `get_road`, which turned every read
into a write. That silently broke the atomicity model: the model's safety rests on
reads being interleave-safe, which is only true if reads do not mutate. Fix: decay is
split into `_compute_decay` (pure; returns decayed values, used by reads, which now
return a decayed *copy* and never touch stored state) and `_persist_decay` (mutating;
used only by `strengthen`/`traverse` and the offline pass). The canonical stored value
is "as of last write or last offline sweep"; reads compute forward without writing.
Verified by `test_reads_are_pure` (20 reads across every read path change nothing
stored) and by reproducing the original probe directly.

**C2 — Closure is sticky, by deliberate decision.** The first implementation
re-evaluated closure inside the passive decay path, so a traumatized road reopened
from the passage of time alone, with no positive experience — and a mere read
triggered it. That is backwards: avoidance preserves trauma, it does not dissolve it.
Decision: closure is re-evaluated *only* on an active crossing (`_open_close_on_crossing`,
called only from `strengthen`/`traverse`), never on a read or time-decay. A closed road
reopens only through active positive return. Verified by `test_closure_is_sticky`
(500 time-units + repeated reads leave it closed; positive return reopens it).

**C3 — `Clock.advance` is simulated-only.** In real mode it called `time.sleep`, which
would block the event loop and freeze every coroutine. Now it raises in real mode;
real time advances on its own.

**Honest scope, restated:** the atomicity model is *argued, not tested* (asyncio
interleaving is hard to unit-test; we did not count it as proven). Closure is a flag
the STORE sets and reports but does **not** yet enforce — `neighbors`/`roads_from` do
not skip closed roads; making closure impassable is Layer 2's activation policy. The
STORE is still ephemeral; "survives a Colab session" is not true until Layer 4
persistence.

---

*Nous Implementation Plan — Layer 1: The Substrate Store*
*Representation decided: object graph, addressed by stable IDs only, v1. The real hard*
*problem named and solved: continuous mutation survives because nothing holds a*
*position — only IDs — so deletion is safe now and the array-backed hybrid (compaction*
*during sleep-mode + ID-remap) is mechanical later. Atomicity model: mutations are*
*synchronous; `await` only between operations, never inside one. No locks in v1.*
*Next: Layer 2 — the first system's internals, one at a time.*
