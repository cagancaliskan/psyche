# SPEC-0c — Deterministic road ordering: removing the order-dependence class at its source

**Status:** DRAFT · **one call is OPEN for Cagan** (§2.3), everything else is specified
**Revises:** 0a (substrate store), 0b (spreading activation), 0b2 (normalization overlay)
**Depends on:** D-011 (the verdict), D-012 (the resolutions and the fix shapes)
**Date:** 2026-07-25
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

### 2.3 OPEN CALL — is `math.fsum` at the convergence accumulator worth its restructure?

D-012 delegated this to architect-pm. I am recording a recommendation rather than a
decision, because it carries a re-validation cost and because §2.3's evidence changed my
first answer.

**The distinction that decides it.** Ordering and `fsum` do not buy the same property:

| | ordering alone | ordering + `fsum` |
|---|---|---|
| **Determinism** (same program, different process) | holds | holds |
| **Order-independence** (a *different* iteration order gives the same bits) | does **not** hold | holds |
| Guarantee rests on | an implementation detail of the store | a property of the arithmetic |
| Tester's permutation probe as acceptance test | unusable — it would correctly still fail | usable, and strictly stronger |
| Tester's N-1 git oracle | **preserved** (both engines iterate the same ordered store) | **broken** (values change vs the pre-0b2 engine) |

**Three arguments for adding `fsum`.**

1. **A reordering change is already planned, in writing.** `nous_activation.py`'s own
   design note contemplates *"a future locality prune [that wants] 'expand only the top-K
   most active nodes' ... within a hop layer."* Top-K within a layer **reorders
   iteration**. So order-independence is not speculative hardening against a hypothetical
   refactor; it is a prerequisite for a feature the module has already written down.
2. **The value-change cost is paid once, either way.** The ordering fix *by itself* already
   moves every convergent float, from "whatever uuid order gave" to "creation order". Every
   brick above must be re-verified regardless. Adding `fsum` in the same brick does not add
   a second re-validation round; deferring it to `0c-ii` would.
   This is *not* the situation SPEC-0b2 §0.2 guarded against. There, two changes had to be
   separated because a measurement had to be attributed to one of them. Here there is no
   measurement to attribute — both changes have the same observable consequence ("numbers
   move by ULPs, re-verify"), so separating them buys no diagnostic power.
3. **Ordering alone leaves the tester asserting the defect is still present, correctly.**
   Of the DEFECT-A asserted-negatives, only the cross-process one flips under ordering
   alone; the two permutation-based ones keep passing, because the engine *is* still
   order-dependent — the order is merely pinned. A fix after which the adversarial suite
   still truthfully asserts "reordering this source's out-roads changes the answer" has
   closed the symptom, not the class.

**Two arguments against.**

1. **It breaks the tester's strongest N-1 oracle.** Under ordering alone, the git-recovered
   pre-0b2 engine still validates neutral byte-identity, because both engines walk the same
   ordered store. With `fsum` it cannot, and N-1 must be re-based (see §6, O-8).
2. **The restructure lands in the hot loop.** The accumulator is a running total *read at
   layer boundaries* (`frozen = {node: activation[node] ...}`), and contributions to a node
   arrive across several layers. So `fsum` requires keeping per-target contribution lists
   and reducing at each layer boundary, plus once at the end. That is contained, and
   arguably makes the freeze step more explicit, but it is a real change to the loop's data
   structure and it allocates per target.

**Recommendation: do both, in 0c — ordering *and* `fsum` at the accumulator.** Argument 1
is decisive on its own: the module has already planned the change that would silently
re-break ordering-alone. Argument 2 removes the usual reason to defer.

**If Cagan prefers ordering alone**, that is a coherent position — it discharges the stated
done-means at lower cost — and the spec then requires, as the substitute for `fsum`'s
defense-in-depth, that O-1 (the ordering contract test) be treated as a Tier 1 invariant
and that any future within-layer prune be blocked behind a `0c-ii` that adds `fsum` first.
That condition must be written into the roadmap, not left as a comment.

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
| **Interpreter sweep** 3.10–3.14 (D-010) | **Kept, and re-justified** | Catches *version-dependent library semantics*, which is a different failure class entirely. Concrete evidence from the 0b2 pass: CPython 3.12 changed builtin `sum()` to Neumaier compensated summation, so identical code computes different floats on 3.11 and 3.12. That is exactly what this axis is for, and it is not what the seed axis is for. |
| **Order-perturbation probe** (NEW) | **Promoted to the actual guarantee** | Drives the engine through a store proxy that permutes `roads_from`, and requires identical bits. This tests the property *directly* instead of sampling an axis that may or may not perturb it. The tester already built the proxy for the 0b2 pass; 0c makes it the standard. Valid as an acceptance test only under the §2.3 `fsum` recommendation — under ordering alone it is replaced by O-1. |
| **uuid4-invariance probe** (NEW) | Added | Builds the same logical graph in N fresh processes and requires identical bits. This is the direct test of the claim in §1, and it is what DEFECT-A failed. |

**The general lesson, stated for the paper's methodology section:** *a coverage axis is only
evidence for the property it can perturb.* Sweeping an axis that does not control the
mechanism produces confidence without evidence, which is worse than no probe, because it
is read as a guarantee. Prefer removing a dependence to sampling it.

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
  *Required only under the §2.3 `fsum` recommendation; under ordering alone this property
  is false by design and O-1 carries the weight instead.*
- **O-7** ASSERTED-NEGATIVE, to bound the claim: two **isomorphic graphs built in different
  insertion orders** may still differ. Must be asserted as a known limitation so the §1
  guarantee is never read as isomorphism-invariance.

**Overlay (0b2)**

- **O-8** N-1 re-established. Neutral byte-identity still holds at `normalization_sigma=None`
  — but the oracle must be **re-based**: under ordering alone the git-recovered pre-0b2
  engine still serves; under `fsum` it cannot, and the property becomes *"σ=None is
  byte-identical to the same engine with the normalization branch removed,"* which the
  tester's independent reference implementation provides.
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

### 6.1 The three asserted-negatives, and what replaces each

D-012's acceptance signal is that these go **red on a correct fix**. Precisely which ones
flip depends on the §2.3 call, and that difference is itself diagnostic:

| Current asserted-negative (`test_tester_0b2_adversarial.py`) | Ordering alone | Ordering + `fsum` | Replaced by |
|---|---|---|---|
| `test_N2_DEFECT_A_reaches_real_processes_at_library_defaults` | **goes RED** | **goes RED** | O-4 |
| `test_N2_DEFECT_A_convergent_accumulation_is_order_dependent` | still passes | **goes RED** | O-6 |
| `test_N2_DEFECT_A_is_inherited_from_0b_not_introduced_by_the_overlay` | still passes | **goes RED** | O-6 (and retire — "inherited" is moot once fixed) |
| `test_N5_DEFECT_B_lone_out_road_IS_attenuated_on_a_moving_clock` | **goes RED** | **goes RED** | O-10 |
| `test_N7_DEFECT_C_sigma_infinity_and_nan_poison_the_result` | **RED** (now raises) | **RED** | O-11, O-12 |
| `test_N7_non_positive_sigma_silences_rather_than_going_negative` | **RED** (now raises) | **RED** | O-11 |

Under ordering alone, two of the six keep passing — truthfully. **That is the tell that
the class is closed only at its symptom**, and it is the sharpest form of §2.3's argument.

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

**What this spec leaves open.** Exactly one thing: **§2.3, whether `fsum` joins the ordering
fix in 0c.** My recommendation is that it should, because the module has already planned
the within-layer prune that would silently re-break ordering-alone, and because the
re-validation cost is paid once either way. The alternative is coherent and cheaper, and it
carries one condition: any future within-layer prune must be blocked behind a `0c-ii`.

**The single next action: Cagan decides §2.3.** The builder cannot start without it — the
answer changes the shape of the accumulator, which of the six asserted-negatives are
expected to flip, and whether the tester's N-1 oracle survives or must be re-based.
