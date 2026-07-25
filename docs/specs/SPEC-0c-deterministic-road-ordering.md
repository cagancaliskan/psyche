# SPEC-0c — Deterministic road ordering: removing the order-dependence class at its source

**Status:** SPECIFIED · ready for the builder · **one scope call open** (§2.5, new)
**Revises:** 0a (substrate store), 0b (spreading activation), 0b2 (normalization overlay)
**Depends on:** D-011 (the verdict), D-012 (the resolutions and the fix shapes),
D-013 (§2.3 — `fsum` joins the ordering fix)
**Date:** 2026-07-25, amended 2026-07-26 with the §2.3 decision
**Author lane:** architect-pm

---

## 0. Framing

### 0.1 What this brick is

0c is a **repair brick**. It adds no capability, and it earns nothing new. It fixes the
three defects the 0b2 tester pass returned (D-011) and restores the determinism leg of
Phase 0's done-means, which D-012 removed the `PROVEN` label over.

Its real product is not the three fixes. It is that **the determinism guarantee stops
being a sampled axis and becomes a structural property**. That change outlives the
defects and is specified in §5.

### 0.2 What this brick is not

No cognitive claim is made or approached. `0c` does not touch the meaning bar, which stays
open after three structurally distinct refusals. A brick that makes floats reproducible is
a brick about floats.

### 0.3 The one thing this spec must not do

D-012 fixed the *shape* of each fix. This spec fixes the *contract, the invariants and the
re-validation plan*. It must not quietly widen the change: every item below is either a
named defect's cause, or the methodology change D-012 mandated. Anything else is a later
brick.

---

## 1. The claim 0c must make true

> For a fixed store state and fixed parameters, `spread_activation` returns
> **byte-identical** output in every process, on every supported interpreter, regardless
> of `PYTHONHASHSEED` and regardless of which uuid4 values were drawn.

Two things about the wording, both load-bearing.

**"Regardless of which uuid4 values were drawn" is the new part.** The old claim was
implicitly *"across the hash seeds we swept."* D-012 finding 2 established that the seed
axis does not control the source of the nondeterminism, so sweeping it never established
the claim. The new claim is unconditional and therefore has to be earned structurally.

**"For a fixed store state" is narrower than it looks, deliberately.** Determinism here is
over *process runs of the same construction program*, not over *isomorphic graphs built by
different construction programs*. Two stores holding the same logical graph, built by
different insertion sequences, may still produce different floats after 0c. That is
inherent to floating-point accumulation over a graph, it is not a defect, and §6 requires
it be written down as an asserted-negative so nobody reads the guarantee as more than it
is.

---

## 2. DEFECT-A — ordering at the store

### 2.1 Cause, restated exactly

`SubstrateStore._out` and `._in` are `Dict[NodeID, Set[RoadID]]`. `roads_from()` returns
`iter(tuple(self._out.get(node_id, set())))` (`src/nous_store.py:444`) — iteration over a
**set of uuid4 hex strings**, whose order depends on the hash of values that are freshly
random in every process. `nous_activation.py:287` then accumulates convergent
contributions with a naive sequential float add in that order, and float addition is not
associative. At in-degree ≥ 3 the accumulated sum is run-dependent.

**This was known.** `experiments/harness.py:290` carries a comment describing this exact
hazard — *"store.roads_from yields road IDs in set-iteration order over uuids ... float
addition is NOT associative, so summing in that order could differ in the last ULP across
processes"* — and works around it locally by sorting flow values before summing. The
knowledge sat in the repository, in writing, while the substrate carried `PROVEN`. A
per-consumer workaround in one experiment file did not, and could not, protect the engine.
That is the argument for fixing at the store: **the store owns the ordering contract, so
the store is where it is stated once.**

### 2.2 The change

Replace the unordered set with an insertion-ordered mapping used as an ordered set:

```
_out: Dict[NodeID, Dict[RoadID, None]]
_in:  Dict[NodeID, Dict[RoadID, None]]
```

`roads_from()` and `roads_into()` then yield in **road-creation order**, which is program
order, which is identical in every process. This is the project's existing float rule —
*"make every comparison resolve on an intrinsic integer before it resolves on a float"* —
applied one level out, to iteration rather than to comparison: the intrinsic integer is
`creation_seq`, and insertion order already encodes it.

The full change surface is **fourteen lines** in `src/nous_store.py`, all mechanical: the
two type annotations (249–250), per-node init `set()` → `{}` (276–277), `add(rid)` →
`d[rid] = None` (319–320), `discard(rid)` → `d.pop(rid, None)` (330–331), and the six
`.get(node_id, set())` fallbacks (291, 444, 449, 453, 504, 506). Four further sites need
**no** change and are listed so the builder does not touch them: the `pop` calls in
`remove_node` (294–295), the membership test in `_assert_node_indices` (499), and the two
`check_integrity` walks (522, 526), which iterate keys either way. Membership tests, `len`
and `list()` are unchanged in meaning. Complexity is unchanged;
memory per road grows by one dict slot.

**No consumer needs to change.** Every consumer of `roads_from`/`roads_into`/`neighbors`
keeps working; they simply now see a defined order.

### 2.3 DECIDED — `math.fsum` joins the ordering fix; both land together in 0c

**Decided by Cagan, 2026-07-26. See D-013.** The accumulator uses `math.fsum` *and* the
store is ordered. This section records the reasoning, because the grounds matter more than
the verdict.

**The distinction that made it a real question.** Ordering and `fsum` do not buy the same
property:

| | ordering alone | ordering + `fsum` |
|---|---|---|
| **Determinism** (same program, different process) | holds | holds |
| **Order-independence** (a *different* iteration order gives the same bits) | does **not** hold | holds |
| Guarantee rests on | an implementation detail of the store | a property of the arithmetic |
| Tester's permutation probe as acceptance test | unusable — it would correctly still fail | usable, and strictly stronger |
| Float semantics across CPython versions | still `sum()`-shaped at sibling sites, so version-dependent | uniform by construction |
| Tester's N-1 git oracle | **breaks either way** — see the correction below | **breaks** (values change vs the pre-0b2 engine) |

**The four grounds, in the order Cagan weighted them.**

1. **DECISIVE — ordering alone leaves our own adversarial suite able to assert the
   pathology, truthfully.** Of the six asserted-negatives, only the cross-process ones flip
   under ordering alone; the two permutation-based ones keep passing, because the engine
   *is* still order-dependent — the order is merely pinned. **A fix after which our own
   adversarial suite can still honestly assert the pathology is a fix at the symptom, not
   at the cause.** That is the whole test, and ordering alone fails it.

2. **The repository has already lost this exact bet once.** Ordering-alone's safety rests on
   a recorded condition being honoured later — "do not reorder iteration without adding
   `fsum` first." `experiments/harness.py:290` recorded this very hazard, in writing, in
   this repository, and worked around it locally; the substrate carried `PROVEN` for a month
   anyway and the engine was never fixed. A control that depends on a future reader
   honouring a note has been tried here, on this hazard, and it failed. Do not buy it twice.

3. **A reordering change is already planned, in writing.** `nous_activation.py`'s own design
   note contemplates *"a future locality prune [that wants] 'expand only the top-K most
   active nodes' ... within a hop layer."* Top-K within a layer **reorders iteration**. So
   order-independence is not speculative hardening against a hypothetical refactor; it is a
   prerequisite for a feature the module has already written down — the very condition
   ground 2 says will not be honoured.

4. **Float correctness here is currently a function of which interpreter runs it, and
   `fsum` makes it uniform.** This is the mechanism behind BUG-0b1's version-dependence, and
   it is now confirmed rather than conjectured. BUG-0b1's fix was exactly
   `sum(members.values())` → `math.fsum(members.values())`. CPython 3.12 changed the builtin
   `sum()` to use **Neumaier compensated summation** for floats. Reproduced on this machine
   over `[1.0, 1e-16, 1e-16, 1e-16]`:

   | interpreter | naive left-fold | builtin `sum()` | `math.fsum()` | `sum() == fsum()` |
   |---|---|---|---|---|
   | 3.10.17 | `…f03f` | `…f03f` | `01…f03f` | **False** |
   | 3.11.15 | `…f03f` | `…f03f` | `01…f03f` | **False** |
   | 3.12.4 | `…f03f` | `01…f03f` | `01…f03f` | True |
   | 3.13.14 | `…f03f` | `01…f03f` | `01…f03f` | True |
   | 3.14.4 | `…f03f` | `01…f03f` | `01…f03f` | True |

   So the pre-0b1 code was **accidentally correct on 3.12+** and naive on 3.10/3.11. That is
   precisely why BUG-0b1 was *"invisible on 3.12 and flipped the winner 8 times in 30 on
   3.11"* — a fact the bug report recorded as an unexplained interpreter difference. It is
   explained now. `math.fsum` is exactly-rounded on every version, so it makes the semantics
   uniform by construction rather than accidentally-correct on new interpreters.

**The one real cost, accepted.** The restructure lands in the hot loop. The accumulator is a
running total *read at layer boundaries* (`frozen = {node: activation[node] ...}`), and
contributions to a node arrive across several layers. `fsum` therefore requires keeping
per-target contribution lists and reducing at each layer boundary, plus once at the end.
That is contained, it arguably makes the freeze step more explicit, but it is a real change
to the loop's data structure and it allocates per target.

**CORRECTION — the N-1 git oracle is not a differentiator, and the earlier draft was wrong
to list it as one.** The draft claimed the git-recovered pre-0b2 engine survives under
ordering alone, "because both engines walk the same ordered store." That is false wherever
it matters. Ordering changes the **accumulation sequence** at in-degree ≥ 3, so the
pre-change engine run on an *ordered* store does not reproduce the values it produced on an
*unordered* one — and on the unordered store it had no single answer to reproduce. The git
oracle is well-defined only on the region where the pre-change engine was deterministic in
the first place: **in-degree ≤ 2**. Outside it, the oracle never had a stable value, with or
without `fsum`. It therefore breaks under both options, it is not evidence for either, and
the spec carries the boundary explicitly instead of the objection.

### 2.4 Re-validation forced by DEFECT-A's fix

**What actually changes:** the *set* of roads is untouched; only the order changes. So any
quantity that is order-independent — a maximum, a two-term sum, a sorted output, a count,
a set membership — is bit-identical before and after. Only **order-dependent float
accumulations move**, and they move by ULPs. BUG-0b1 established that 1 ULP is enough to
flip a categorical winner 8 times in 30, so "moves by ULPs" is not "moves harmlessly."

| Brick | Consumes | What must be re-verified | Cost |
|---|---|---|---|
| **0a** | owns `_out`/`_in` | ordering contract (O-1, O-2), integrity after mutation batteries, purity unchanged | small; the change is here |
| **0b** | `roads_from` in the expansion loop | full mechanism re-verification: determinism (O-3), purity, convergence, the hop-layer freeze | **largest**; this is the brick whose claim failed |
| **1a** field | merges per-source activations | merged field values may shift; per-source spreads re-verified via 0b | medium |
| **1b** coalitions | `math.fsum` of member activations | the fsum is correct at its own site but its **inputs** move (BUG-0b1's amended note); strength values and therefore ranking may change | medium |
| **1c** clustering | proximity over graph structure and strengths | grouping is decided by strengths, not activations, so most of it is structurally stable — but `_pair_proximity` and the merge must be re-verified for order sensitivity | medium |
| **1d-i** workspace | density scores over coalition strengths | **the known flip site.** BUG-0b1 lived exactly here; re-verify the winner, the tie-break, the min-size guard, the over-swallow prune | **high attention**, small surface |
| **1d-ii** broadcast | the winner's identity | writes follow the winner, so a flipped winner changes what is written | medium |
| **2c** interoception | modulates `decay_per_hop` | every activation value is scaled by it, so all of 0b's re-verification applies under modulation too | medium |
| **1e / 1e-prime** | — | **no re-run needed.** Both are closed NO-GOs whose reasons are *structural* (circular by construction; mechanism absent), not numerical. A ULP shift cannot revive a stratum that was tied by construction. Recorded so the cost is not overstated. | none |

**A scoping point worth stating plainly:** all of the above is **mechanism re-verification
(tester lane), not meaning re-validation.** No cognitive claim is at stake, because none is
outstanding. The cost is six suites re-verified with bit-exact probes; it is not a
re-opening of the meaning bar.

**`experiments/harness.py`'s local workaround** becomes unnecessary after 0c. Recommend
keeping it (sorting is harmless and the comment is now history worth reading) but
**correcting its comment**, which attributes the hazard to `PYTHONHASHSEED` alone — the
finding that it also varies at a fixed seed is exactly what the seed framing missed.

### 2.5 NEW FINDING — three further naive float sums survive in `src/` · **OPEN CALL**

Found while verifying §2.3 ground 4. Confirming that BUG-0b1's fix was `sum` → `math.fsum`
raised the obvious next question — *where else does this project sum floats with the
builtin?* — and the answer is three places:

| Site | What it computes | Assessment |
|---|---|---|
| **`src/nous_workspace.py:428`** | `strength=sum(pruned_members.values())` — the **pruned winner's** strength | **The serious one.** Its own comment says it applies *"the same 'sum of member activations' rule coalition formation uses."* BUG-0b1 changed that rule to `math.fsum` at `nous_coalitions.py:226` and `:309` and **did not change this site**. So the pruned winner's strength is computed by a *different* rule than the raw winner's, by the version-dependent one, on the 1d-i winner path — the exact path BUG-0b1's flip occurred on. BUG-0b1's own ledger note says "`math.fsum` at both sites"; there were three. |
| **`src/nous_workspace.py:235`** | `total_strength_after()` — the bounded aggregate the no-divergence test watches converge | Lower stakes: it informs a test's judgement rather than a selection. But a convergence test whose statistic is version-dependent is a weak test. |
| **`src/nous_store.py:161`** | `Road.valence` = `sum(charges.values()) / max(1, len(...))` | Feeds `_open_close_on_crossing`'s comparisons against `_CLOSURE_THRESHOLD` (−0.75) and `_REOPEN_THRESHOLD` (−0.30) — a **categorical** closure decision resolved on a float sum, which is the exact shape the project's float rule prohibits. Reachability is low (a sum must land within a ULP of a threshold) but the shape is wrong. |

**Why this is not already covered by the rest of 0c.** Ordering closes *order*-dependence;
after 0c these dicts iterate deterministically anyway. It does **not** close
*version*-dependence: `sum()` and `math.fsum()` return different bits on 3.10/3.11 and the
same bits on 3.12+, regardless of order. So these three sites make the project's floats a
function of which interpreter runs them.

**And nothing currently checks that.** `capture_run` compares per-suite *counts* across
interpreters, not values; the determinism probes all run under a single `sys.executable`.
A genuine cross-interpreter value discrepancy at these sites would be reported by nothing
in the repository today. That gap is what O-16 closes.

**The call.** These are three one-line changes, and 0c is *already* paying the
re-validation for 1b, 1d-i and 2c (§2.4), so folding them in costs little beyond the edit
itself. The alternative is coherent but has a consequence that must be stated: **O-16
(cross-interpreter bit-identity) is unachievable while any naive float sum remains.** So
the choice is genuinely between the two:

- **(A) Fold all three into 0c.** One brick closes the class everywhere it appears; O-16
  becomes achievable; BUG-0b1's "both sites" note is corrected to three.
- **(B) Fold in `nous_workspace.py:428` only**, as a BUG-0b1 completion, and defer the
  other two. Smallest correct scope, but leaves O-16 unachievable and leaves two known
  instances of a class we are mid-way through eliminating.
- **(C) Defer all three to a separate brick.** Keeps 0c's scope exactly as specified, at
  the cost of shipping a determinism brick that knowingly leaves version-dependent float
  sums in the winner path.

**Recommendation: (A).** The marginal cost is three lines inside a re-validation this brick
is already performing, and the same ground-2 argument applies — a deferred condition in
this repository, on this hazard, has already failed once. **(C) is not recommended**: it
would mean answering "is Phase 0 deterministic?" with "yes, except where it depends on your
interpreter."

**This is a scope widening and therefore Cagan's call, not mine.** If (A) or (B) is taken,
`docs/BUG-0b1-coalition-strength-determinism.md` also needs its "both sites" claim
corrected in place, the way its §5 sentence already was.

---

## 3. DEFECT-B — read each road once per expansion

**Cause.** The overlay calls `store.get_road()` twice for each road in one expansion — once
building `out_total`, once in the transmission loop — and `get_road` applies lazy decay as
of `clock.now()` at each call. On any clock that advances (the library default,
`Clock(simulated=False)`), the two reads return different strengths, so
`competing = out_total − road.strength` is an elapsed-time residue rather than exactly 0.
Measured on a lone out-road: `competing = 1.7265900376095544e-09`, factor
`0.99999999827341` where SPEC-0b2 §2 row 3 and N-5 both require exactly `1.0`.

**The change (D-012, adopted).** Materialise the expanding node's roads **once**:

```
roads = [(rid, store.get_road(rid)) for rid in store.roads_from(node)]
out_total = fsum(road.strength for _, road in roads)     # when sigma is not None
for rid, road in roads:  ...
```

`out_total` and every `road.strength` then come from a single instant, so `competing` is a
pure conductance quantity by construction, and a lone out-road gives exactly `0.0`.

**Two consequences to record.**

- SPEC-0b2 §8 item 4 listed the duplicated road read as a **cost**. After this change it is
  removed: the fix is strictly better on both correctness and cost.
- **N-1 must be re-verified, not assumed.** The read *pattern* changes. At `sigma=None` the
  materialisation still performs exactly one read per road, so neutral byte-identity is
  expected to survive — but "expected" is what the 0b2 pass was sent to test, and it found
  two things that were expected and false.
- Byte-identity tests must continue to use a **frozen clock**. On a moving clock any two
  runs differ through 0a's lazy decay alone; that is a store property, not an overlay
  property, and conflating them is how DEFECT-B stayed invisible.

---

## 4. DEFECT-C — validate σ, and stop NaN at the floor guard

**Cause.** `normalization_sigma` is unvalidated. `float('inf')` — the exact value SPEC-0b2
§2 called the one that "analytically recovers the current engine" — computes `inf/inf` =
NaN. NaN then **passes** `if transmitted < floor: continue`, because every comparison with
NaN is False, so NaN propagates into `activation` silently and with no exception. σ ≤ 0
misbehaves too: it silences everything while `floor ≥ 0`, and produces genuinely negative
activation once `floor` is negative.

**The change (D-012, adopted), in two independent parts.**

1. **Validate σ at the boundary.** At the top of `spread_activation`, before any work:
   reject a `normalization_sigma` that is not `None` and not finite-and-strictly-positive,
   with `ValueError` naming the offending value. Fail fast, at the caller's frame.
2. **Guard non-finite transmission generally.** The NaN-passes-the-floor hazard is *more
   general than σ* — it is a property of the floor comparison, and any future term that can
   produce NaN or ±inf inherits it. The guard must reject non-finite `transmitted` on its
   own terms, not as a side effect of σ validation.

**Prose correction, already made by D-012 and restated here so the spec is self-contained:
the neutral value is `None`, never infinity.** "σ → ∞ recovers the current engine" is true
analytically in the limit and catastrophic at the literal value. Large finite σ does behave
— σ = 1e300 was verified byte-identical to `None` — but that is a fact about large finite
σ, and the spec must not invite a caller to write `inf`.

---

## 5. The methodology change — the part that outlives the defects

### 5.1 Every determinism probe must compare bit patterns

**The rule.** No determinism probe may compare rounded values. A probe payload serialises
floats with `repr()` (which round-trips, so it is exact) or `struct.pack('<d', x).hex()`
(explicit). `round(x, 9)` is blind to everything below 1e-9 — and BUG-0b1 was 1 ULP.

The probes that "caught" BUG-0b1 did not catch it by seeing the number; they caught it
because the ULP happened to flip a categorical winner. **Any ULP difference that did not
flip an outcome has been invisible for the life of the project.**

**Enumeration — 18 `round()` call sites inside hash-seed driver payloads, across 13 files,
split by lane.** Each owner rewrites its own; the lanes do not cross for this either.

*Builder-owned (8 files, 10 sites):*
`test_nous_activation.py` (1) · `test_nous_bodysensor.py` (2) · `test_nous_coalitions.py`
(1) · `test_nous_field.py` (1) · `test_nous_perceive.py` (1) ·
`test_nous_source_clustering.py` (1) · `test_nous_workspace.py` (1) ·
`test_nous_workspace_broadcast.py` (2)

*Tester-owned (5 files, 8 sites):*
`test_tester_1c_adversarial.py` (3) · `test_tester_1c_mutation_battery.py` (1) ·
`test_tester_1d_i_adversarial.py` (2) · `test_tester_1d_ii_adversarial.py` (1) ·
`test_tester_2c_adversarial.py` (1)

*Already exact, no change needed:* `test_tester_0b2_adversarial.py` compares
`struct.pack('<d', …).hex()` throughout. The remaining hash-seed probes
(`test_tester_1e_*`, `experiments/test_*`) carry no driver-internal rounding and serialise
through `repr()`, which is exact — **but that must be audited, not assumed**, and the audit
is an acceptance item (O-9).

### 5.2 What replaces seed-sweeping as the guarantee

Seed-pinning never controlled the source of the nondeterminism: iteration order derives
from uuid4 values, which are freshly random per process whatever `PYTHONHASHSEED` says.
DEFECT-A varies at a *fixed* seed. So the axis the project has been sweeping is not the
axis the defect lives on.

**The guarantee becomes structural, not statistical.** After 0c there is no order for a
seed to perturb: the order is fixed by construction (and, under the §2.3 recommendation,
the arithmetic is order-independent as well). Three probes replace one, and each is
demoted or promoted to what it actually establishes:

| Probe | Status after 0c | What it actually establishes |
|---|---|---|
| **Hash-seed sweep** {0,1,2,3,7,42} | **Demoted** from "the guarantee" to a cheap regression probe | Catches a *newly introduced* hash-order dependence. It never established determinism and must stop being described as though it did. |
| **Interpreter sweep** 3.10–3.14 (D-010) | **Kept, and re-justified on confirmed evidence** | Catches *version-dependent library semantics*, a different failure class entirely. CPython 3.12 changed builtin `sum()` to Neumaier compensated summation, so identical code computes different floats on 3.11 and 3.12 — reproduced in §2.3 ground 4. **This is the mechanism behind BUG-0b1's version-dependence**, which the bug report recorded as an unexplained interpreter difference: the pre-fix `sum()` was accidentally exact on 3.12+ and naive on 3.11. That is exactly what this axis is for, and it is not what the seed axis is for. |
| **Order-perturbation probe** (NEW) | **Promoted to the actual guarantee** | Drives the engine through a store proxy that permutes `roads_from`, and requires identical bits. This tests the property *directly* instead of sampling an axis that may or may not perturb it. The tester already built the proxy for the 0b2 pass; 0c makes it the standard. Valid as an acceptance test only under the §2.3 `fsum` recommendation — under ordering alone it is replaced by O-1. |
| **uuid4-invariance probe** (NEW) | Added | Builds the same logical graph in N fresh processes and requires identical bits. This is the direct test of the claim in §1, and it is what DEFECT-A failed. |

### 5.3 The generalisation, for the paper's methodology section

> **A coverage axis is only evidence for the property it can perturb.**

Sweeping an axis that does not control the mechanism produces confidence without evidence,
which is worse than no probe at all, because it is read as a guarantee. This project swept
`PYTHONHASHSEED` for a month against a nondeterminism that uuid4 caused, and the sweep
could not have found it at any seed.

The corollary the two findings share: **prefer removing a dependence to sampling it.** An
axis you have eliminated needs no coverage argument. Ordering plus `fsum` removes the
order dependence; validation removes the non-finite dependence. What remains sampled — the
interpreter axis — is sampled because it is genuinely a property of the environment rather
than of the program, and §2.3 ground 4 shows it earning its keep.

---

## 6. Invariants — the tester's acceptance list

The tester writes its own hostile tests; these are the properties, not the tests.

**Ordering contract (0a)**

- **O-1** `roads_from()` and `roads_into()` yield in road-creation order, for every node,
  after arbitrary add/remove/re-add batteries. Asserted against `creation_seq`, which is
  the intrinsic integer, not against insertion coincidence.
- **O-2** Order survives mutation: after removing roads and adding new ones, surviving
  roads keep their relative order and a re-added pair is a **new** road that sorts last.
  (`add_road` on an existing pair returns the existing road and must **not** reorder it.)
- **O-3** Integrity and purity are unchanged by the representation change — the two legs of
  Phase 0 that did *not* fail must be shown still to hold, not assumed.

**Determinism (0b) — the claim in §1**

- **O-4** The DEFECT-A reproduction — 5-node, `traverse()`-only, library defaults,
  in-degree 3 — yields **one** bit pattern across ≥ 48 fresh processes × 6 hash seeds × all
  5 interpreters. This is the direct replacement for the retired asserted-negative.
- **O-5** Generalised: over a battery of randomly generated adversarial graphs including
  high in-degree, cycles, self-loops and closed roads, every graph yields one bit pattern
  across fresh processes.
- **O-6** Order-perturbation invariance: permuting `roads_from` leaves output bit-identical.
  **Required unconditionally** under the §2.3 decision, and it is the invariant that
  distinguishes a fix at the cause from a fix at the symptom. The tester already built the
  permuting store proxy during the 0b2 pass; it changes role here from demonstrating the
  defect to certifying its absence.
- **O-7** ASSERTED-NEGATIVE, to bound the claim: two **isomorphic graphs built in different
  insertion orders** may still differ. Must be asserted as a known limitation so the §1
  guarantee is never read as isomorphism-invariance.

**Overlay (0b2)**

- **O-8** N-1 re-established, on a **re-based oracle**. The property remains *"with
  `normalization_sigma=None` the engine is byte-identical to the same engine with the
  normalization branch removed"* — but the git-recovered pre-0b2 engine can no longer
  supply it, so the tester's independent reference implementation becomes the oracle.

  > **THE TRAP, and it is the one most likely to be walked into.** The reference
  > implementation must mirror the **intended** semantics — ordered iteration *and* `fsum`
  > accumulation — not the semantics it was written against. A reference that still models
  > the old naive accumulator will agree with a *broken* engine and disagree with a correct
  > one. At that point it has silently stopped being an oracle and has become **a second
  > copy of the bug**, and N-1 will read as a failure of the fix rather than a failure of
  > the reference. Re-basing the oracle is part of the fix, not an afterthought to it.

  The git oracle retains exactly one legitimate use, bounded by §2.3's correction: as a
  cross-check on **in-degree ≤ 2** graphs, the region where the pre-change engine had a
  single well-defined answer. It must not be pointed at anything above that boundary.
- **O-9** Each road is read exactly once per expansion of a node (DEFECT-B's cause,
  asserted structurally, e.g. via a recording store proxy).
- **O-10** A source with exactly one out-road transmits with factor exactly `1.0`, **on a
  moving clock**, at every valid σ. This is N-5 restored, and the moving clock is the point.
- **O-11** σ validation: non-finite and non-positive σ raise `ValueError` at the boundary,
  naming the value. `None` remains neutral.
- **O-12** No non-finite value can reach `activation` or `flow`, by any route, independent
  of σ.
- **O-13** The rest of SPEC-0b2 §6 — N-3, N-4, N-6, N-8, N-9 — still holds after the change.
  They passed once; the read-pattern change means they must pass again.

**Methodology**

- **O-14** No determinism probe anywhere in `tests/` or `experiments/` compares rounded
  values. Machine-checkable, and worth making a check rather than a habit.
- **O-15** No builtin `sum()` over float values remains in `src/`, or each survivor carries
  a written justification. Machine-checkable. *Conditional on §2.5 being taken.*
- **O-16** **Cross-interpreter bit-identity**, which nothing checks today: the same graph
  produces identical bit patterns on all five interpreters, not merely identical per-suite
  counts. Scoped honestly to **one machine** — IEEE-754 arithmetic is exactly rounded and
  version-independent, but transcendental functions (`math.exp` in the decay path) come
  from the platform's libm, so this is a claim about interpreters, not about platforms.
  *Unachievable while any naive float sum remains (§2.5).*

### 6.1 The six asserted-negatives, and what replaces each

D-012's acceptance signal is that these go **red on a correct fix**. Under the §2.3
decision, **all six flip**, and that is the point: the two that would have survived
ordering alone are exactly the ones that certify the cause rather than the symptom.

| Current asserted-negative (`test_tester_0b2_adversarial.py`) | After 0c | Replaced by |
|---|---|---|
| `test_N2_DEFECT_A_reaches_real_processes_at_library_defaults` | **RED** | O-4 |
| `test_N2_DEFECT_A_convergent_accumulation_is_order_dependent` | **RED** — *would have survived ordering alone* | O-6 |
| `test_N2_DEFECT_A_is_inherited_from_0b_not_introduced_by_the_overlay` | **RED** — *would have survived ordering alone* | O-6, then retire: "inherited" is moot once fixed |
| `test_N5_DEFECT_B_lone_out_road_IS_attenuated_on_a_moving_clock` | **RED** | O-10 |
| `test_N7_DEFECT_C_sigma_infinity_and_nan_poison_the_result` | **RED** (now raises) | O-11, O-12 |
| `test_N7_non_positive_sigma_silences_rather_than_going_negative` | **RED** (now raises) | O-11 |

**Six red asserted-negatives is the acceptance signal for 0c.** A run in which any of them
still passes is a run in which that defect is still present — including the two
permutation-based ones, whose survival is precisely what §2.3 ground 1 refused to accept.

Minor, tester-owned: `load_pre_change_engine()` writes its temporary oracle into `tests/`
and removes it in a `finally`, so an *interrupted* run can leave `tests/__pre0b2_oracle.py`
behind (it did once, during the 0b2 pass). It should write to a temp directory instead.

---

## 7. Done means

**0c is done when:**

1. O-1 … O-14 hold, verified by the tester in its own lane, on all five interpreters.
2. The canonical suite is green and captured, with every determinism probe comparing bit
   patterns (§5.1).
3. The six asserted-negatives above have been retired and replaced per §6.1, with the
   replacement asserting the positive property.
4. The delivery report states which previously-passing properties changed value and why —
   D-012's route back requires Phase 0 to return **stronger**, and "stronger" means the
   probes can now see the failure class that hid here.
5. `0a` and `0b` return to `PROVEN` **only after** the tester re-verifies them; the builder
   does not restore its own label.

**External and unfakeable:** O-4 is the acceptance test, and it cannot be satisfied by
adjusting a tolerance. Bit patterns across 48 fresh processes are either identical or they
are not, and the input is the graph the defect was found on.

## 8. What would falsify success

- O-4 produces more than one bit pattern → the fix is incomplete; there is a second
  ordering source.
- O-8 fails → the fix changed neutral behaviour, and 0b2's default-off guarantee is broken.
- Any brick in §2.4 changes a **categorical** outcome (a winner, a grouping, a prune
  decision) rather than only a float → that is not a re-verification, it is a behaviour
  change, and it needs its own entry and its own gate before Phase 0 is re-labelled.
- The suite goes green while `test_N2_DEFECT_A_convergent_accumulation_is_order_dependent`
  still passes, *and* `fsum` was adopted → the `fsum` change did not actually take effect.

---

## 9. Roadmap impact, and the single next action

**What 0c unblocks.** Phase 0's label, and with it everything queued behind it: 0b2's
second brick (the activation floor, D-008), the default flip (D-009, whose re-validation
surface D-011 already widened to 1a/1b/1c/1d), and the paper brick — the paper is held
(D-012) because its Tier-1 determinism claim is presently false, and 0c is what makes it
true again.

**What 0c does not touch.** The meaning bar stays open. `1e` and `1e-prime` stay NO-GO on
structural grounds and are not re-run (§2.4). Nothing here approaches a cognitive claim.

**What this spec leaves open.** One thing, and it is new rather than carried over:
**§2.5, whether the three surviving naive float sums in `src/` are folded into 0c.**
Recommendation (A), fold all three; the marginal cost is three lines inside a
re-validation this brick already performs, and deferring leaves O-16 unachievable.
§2.3 is **closed** — `fsum` joins the ordering fix (D-013).

**The single next action: hand SPEC-0c to the builder**, with §2.5 answered. The builder
implements ordering + `fsum` at the store and the accumulator (§2), the single-read
materialisation (§3), and σ validation plus the non-finite guard (§4), test-first, then
hands to the tester for O-1 … O-16. The tester's acceptance signal is unambiguous and
inverted from the usual one: **all six asserted-negatives in
`tests/test_tester_0b2_adversarial.py` must go red**, and the two that would have survived
ordering alone are the ones that matter most.
