# SPEC-0c — Deterministic road ordering: removing the order-dependence class at its source

**Status:** BUILT · tester verdict FAIL on O-12, **now closed by D-015** (§4.1) ·
awaiting the energy-validation fix, O-12 re-verification, suite registration and capture ·
**scope narrowed (§0.4)** · §2.7's site deferred to brick 0d
**Revises:** 0a (substrate store), 0b (spreading activation), 0b2 (normalization overlay)
**Depends on:** D-011 (the verdict), D-012 (the resolutions and the fix shapes),
D-013 (§2.3 — `fsum` joins the ordering fix), D-014 (§2.5, §2.6 and the routing split)
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

### 0.4 What 0c may and may not claim — the scope is narrowed, deliberately (D-015)

0c began as "removing the order-dependence class at its source." **It does not do that, and
the title now overstates it.** Three separate encounters with the same shape — BUG-0b1's two
sites, §2.5's third site, §2.7's fourth — plus the fact that each was found by *looking* and
none by a *sweep*, is sufficient evidence that the class is larger than any one brick's
enumeration. So the claim is bounded to what was actually verified:

**0c MAY claim:**
- Determinism is **restored at the enumerated sites**, verified structurally rather than
  sampled — §1 case 1 and case 2, O-1…O-6, O-16.
- **Order-independence** is achieved at those sites: a different iteration order yields the
  same bits, not merely a fixed order yielding a fixed result.
- One further site is **identified and deferred** (§2.7, `nous_field.py`). It is
  **order-pinned**, so it is **not a determinism defect** and it falsifies nothing 0c
  asserts.

**0c MAY NOT claim:**
- That the order-dependent-aggregate **class is closed**. It is not. No sweep has
  established that the four known sites are all of them, and §2.7 exists precisely because
  the second sweep was not exhaustive either.

This distinction is not pedantry: "the class is closed" is the claim that would let the next
brick stop looking. Brick **0d** replaces looking with a detector, and until 0d lands the
honest statement is *"every site we have found is fixed,"* which is a different sentence.

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
different construction programs*.

### 1.1 The two reproduction cases the claim is tested against

The claim covers **every** float path, not the one that happened to be found first. The
spec originally carried only case 1, and §2.5.2(b) records why that was a defect in the
spec rather than merely in the code.

**Case 1 — the activation accumulator (DEFECT-A as originally found).** Five nodes, built
with `traverse()` alone, at library defaults: `S → M0,M1,M2 → T` at traverse counts
`(1,2)`, `(1,3)`, `(1,9)`. Before 0c this gave `0.10145973529004966` and
`0.10145973529004967` across fresh processes. It must now give one bit pattern.

**Case 2 — the competition path (§2.5.1).** This one is not reachable from case 1: it runs
through `think()`, and its order comes from a set of uuid4 NodeIDs in the coalition layer,
which the store-ordering fix does not touch.

```python
from nous_store import SubstrateStore, Clock, NodeType
from nous_perceive import think
import itertools
s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
add = lambda c: s.add_node(c, NodeType.CONCEPT)
warm = [add(x) for x in ("coffee","kitchen","morning","mug","toast")]
cold = [add(x) for x in ("work","code","deadline")]
def w(a,b,n):
    for _ in range(n): s.traverse(a,b)
for a,b in itertools.permutations(warm,2): w(a,b,7)
for a,b in itertools.permutations(cold,2): w(a,b,9)
w(warm[0], cold[0], 8)
r = think(s, "coffee kitchen morning mug toast")
print(repr(r.thought.strength))   # must be ONE bit pattern across processes
```

On the post-0c tree this still gives **two** values on python3.10 at a fixed hash seed and
**one** on python3.14 — the Neumaier split. It must give one bit pattern on **every**
interpreter, which is what makes it a test of the fix rather than of the interpreter.

**Amended 2026-07-26, on the builder's witness.** The draft said two isomorphic graphs built
in different insertion sequences "may still produce different floats." That was written
against ordering-alone and is **wrong for the brick as decided**: because `fsum` is exactly
rounded, the same multiset of contributions reduces to the same value whatever order it
arrived in, so isomorphic graphs now agree on every activation **value**, bit for bit. The
residual is not in the values, it is in the **key order** — `activation`'s insertion order,
and therefore `ranked()`'s order among *tied* entries, still follows construction order.
That is the honest bound, it is narrower and more useful than the one first written, and
O-7 asserts it in that form. The guarantee must still never be read as full
isomorphism-invariance.

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
the first place. **CORRECTED 2026-07-26, on the tester's measurement — the boundary was
stated wrongly and off by one.** The draft said "in-degree ≤ 2". But the engine seeds
`contributions = {seed_node: [energy]}`, so **the seed's own energy is itself a
contribution**: a seed with in-degree 2 on a cycle accumulates *three* terms and moves.
Measured: max in-degree 2, seed energy 1e6 — pre-0c `1086319.0400302166`, post-0c
`…63`. The boundary must be stated on **contributions, not in-degree**: *no node may
accumulate three or more contributions, counting the seed's own energy*. A structural
enforcement is in-degree ≤ 2 globally **and ≤ 1 at the seed**. Outside it, the oracle never
had a stable value, with or
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

**`experiments/harness.py:290` — split the comment from the code, and they route differently
(D-014).** The **comment** is documentation of the very hazard 0c fixes, and it still names
the wrong cause: it attributes the nondeterminism to `PYTHONHASHSEED`, when the finding is
that it varies at a *fixed* seed because uuid4 values differ per process. A wrong causal
explanation of a fixed defect is worse than none — the next reader inherits the error the
project just paid to discover. It is corrected **in the architect-pm lane, as part of 0c**.
The **code** — the local sort-before-summing workaround — is untouched and stays
**validator territory**; it becomes unnecessary after 0c but it is harmless, and removing
experiment code is not this brick's business.

### 2.5 DECIDED — all three surviving naive float sums convert to `math.fsum`

**Decided by Cagan, 2026-07-26. See D-014.** And the framing matters: **this is not
hardening.** Site 3 is a **live instance of the defect BUG-0b1 was supposed to close**, it
reproduces on the post-0c working tree, and BUG-0b1's own report is wrong about how many
sites there were.

Found while verifying §2.3 ground 4. Confirming that BUG-0b1's fix was `sum` → `math.fsum`
raised the obvious next question — *where else does this project sum floats with the
builtin?* — and the answer is three places:

| Site | What it computes | Assessment |
|---|---|---|
| **`src/nous_workspace.py:428`** | `strength=sum(pruned_members.values())` — the **pruned winner's** strength | **A LIVE DEFECT, reproduced — see §2.5.1.** Its own comment says it applies *"the same 'sum of member activations' rule coalition formation uses."* BUG-0b1 changed that rule to `math.fsum` at `nous_coalitions.py:228` and `:311` and **did not change this site**. There are **three** `Coalition(` construction sites in `src/`, not two. So the pruned winner's strength is computed by a *different* rule than the raw winner's, by the version-dependent one, on the 1d-i winner path — the exact path BUG-0b1's flip occurred on. |
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

#### 2.5.1 Site 3 is a live defect, and here is the reproduction

Run against the **post-0c working tree** — that is, with the store ordered and the
activation accumulator already using `math.fsum`. The §2 fix does not reach it.

```
30 fresh processes, PYTHONHASHSEED=0 (a FIXED seed), the think() graph in §1 case 2:

  python3.10   2 distinct strengths   6x 4.14276559350793   24x 4.142765593507931
  python3.14   1 distinct strength   30x 4.14276559350793
  winner membership: 1 distinct on both — identity is stable
```

**Three things this shows, and each is load-bearing.**

1. **The store-ordering fix cannot reach it.** `Coalition.members` inherits its order from
   `by_basin[src]`, which is `Dict[str, Set[str]]` in `nous_coalitions.py:297` — a **set of
   uuid4 NodeIDs** built in the coalition layer, not an adjacency index the store owns.
   Ordering `_out`/`_in` fixes the store's iteration; it does nothing for a set some other
   module constructs. **Fixing a class at one owner does not fix it at another owner.**
2. **The 3.10-versus-3.14 split is the Neumaier fingerprint.** It is invisible on 3.14 for
   exactly the reason §2.3 ground 4 documents: 3.12+'s builtin `sum()` is compensated, so
   the naive site behaves like `fsum` there. This is BUG-0b1's signature — *invisible on
   the newer interpreter, reproducible on the older one* — recurring at the site BUG-0b1
   missed. §2.3 ground 4 predicted this class; here it is, found.
3. **Winner identity is stable today, which is exactly how BUG-0b1 hid.** `Coalition.strength`
   is what `_competition_key` compares, so this is squarely the competition path. It is not
   flipping a winner *on this graph, today*. BUG-0b1 did not flip one either until a graph
   arrived where it did — 8 times in 30.

**Decision: all three sites convert.** Sites 1 and 2 convert on §2.3 ground 4's reasoning
rather than on a reproduction — site 2 is `total_strength_after()`, which **by its own
docstring** is "the bounded aggregate the no-divergence test watches converge across
cycles," i.e. a version-dependent number feeding an assertion; site 1 is `Road.valence`,
feeding a categorical closure decision. A determinism brick that knowingly left
version-dependent float sums on the winner path would be answering "is Phase 0
deterministic?" with "yes, except where it depends on your interpreter."

#### 2.5.2 Two consequences that outlive the fix

**(a) BUG-0b1's report is wrong, and is corrected in place.**
`docs/BUG-0b1-coalition-strength-determinism.md` states the fix was *"`src/nous_coalitions.py`,
two sites (lines 225 and 308)"*. There was a **third** `Coalition` construction site, in
`nous_workspace.py`, and it was missed. The bug was reported as closed while an instance of
it remained on the same path. This is corrected in the document, **dated**, as a
claim-accuracy fix — the same treatment its §5 "Tier 1 is not affected" sentence already
received. The ledger's `0b1` note is corrected with it.

**(b) §1's falsifier did not cover this, and that is a spec defect, not just a code defect.**
The original §1 reproduction exercises **only the activation accumulator**. It cannot see
the competition path, so a brick whose entire purpose is closing the order-dependence class
would have shipped with a live instance of that class still in it. **Had §1 covered the
competition path, 0c would have caught this itself.** §1 now carries a second reproduction
case and O-4b asserts it. The general lesson is the same one §5.3 states: a probe is only
evidence for the path it exercises.

### 2.6 The one neutral-path bit change that is not a convergence effect · **OPEN CALL**

Found by the builder, flagged rather than silently special-cased, and verified here:
**`math.fsum([-0.0])` returns `+0.0`.** The pre-0c engine seeded `activation = {seed: energy}`
directly and stored the caller's negative zero verbatim; the `fsum` reducer normalises it.

```
math.fsum([-0.0])            ->  0.0    bits 0000000000000000
-0.0                                    bits 0000000000000080
spread_activation(s, A, energy=-0.0).activation[A]  ->  bits 0000000000000000
```

`fsum([x]) == x` bit-for-bit for every other double tested, including `+0.0`, subnormals and
infinities — so this is a single degenerate input, not a class. Numerically `-0.0 == +0.0`
is True, and nothing in the engine or downstream distinguishes them; **only a bit-pattern
comparison does — which is exactly what N-1 performs.** So this is the one input at which
"byte-identical at the neutral value" acquires a documented exception.

**DECIDED by Cagan, 2026-07-26 (D-014): accept the exception and assert it.** No
special-casing of the reducer, and **no boundary validation for `energy`** — no caller
passes a negative and adding one would be scope creep into §4, which exists for σ.

**But the assertion must be phrased as OUR semantics, not as agreement with the stdlib.**
The test states:

> *Activation energy has no signed zero: `-0.0` normalises to `+0.0`, by design.*

and **not** *"we match `math.fsum`'s treatment of `-0.0`."* The second phrasing makes a
CPython implementation detail into our specification: if the stdlib ever changed, the test
would break for a reason that has nothing to do with what this project intends. A test
should fail when the intent is violated, not when an unrelated dependency moves. The
builder wrote the assertion; this is a change to its wording and its rationale, not to its
subject.

### 2.7 FINDING — a fourth order-dependent aggregate, in a module 0c never touched · **OPEN**

The tester was asked whether the §2.5 sweep was exhaustive. **It was not.**
`src/nous_field.py:131` and `:124`:

```python
total[node] = total.get(node, 0.0) + act            # DEFECT-A's exact shape
merged_flow[rid] = merged_flow.get(rid, 0.0) + fv
```

Reproduced here: three sources, three mids, one hub — `field.total[m1]` takes **two distinct
bit patterns** over the 3! source orders (`1.0206966281696925` / `…28`). It reaches
`Coalition.strength`, and over 60 random trials the ranked winner never flipped — **which is
exactly how BUG-0b1 hid, and how §2.5's site hid after it.** That is now three times this
project has met the same shape.

**Scoping, carefully, because this is not a 0c failure.** The source order is
`ordered_sources`, which is program order, so this site is **order-PINNED, not
order-INDEPENDENT** — cross-process determinism is unaffected and every O-4 / O-4b / O-5 /
O-16 result stands. It is also outside 0c's decided scope: §2.5 enumerated builtin `sum()`
sites, and these are `+=` accumulations, which no decision to date has covered.

But "pinned, not independent" is precisely the state D-013 ground 1 refused to accept for
the activation accumulator, for reasons that apply here word for word. **Recommendation: a
follow-on brick** — not a widening of 0c, which is already carrying two scope extensions and
a failing invariant. 0c's claim should meanwhile be stated as what it is: the *activation
engine* is order-independent; the *field merge* is order-pinned.

### 2.8 A second neutral-path behaviour change, documented rather than discovered

`math.fsum` raises `OverflowError: intermediate overflow in fsum` where the pre-0c engine
returned `inf`. At `energy=1e308`, 12-way convergence, `decay_per_hop=1.0`, `floor=0.0`:
pre-0c `T = inf`, post-0c `OverflowError`. It fires at the layer-boundary freeze, so the
engine's own non-finite guard never runs and the stdlib exception escapes instead of a
diagnostic `ValueError`.

It sits outside N-1's `PARAM_SWEEP`, which is why nothing saw it. Probably an improvement —
refusing an overflow beats returning `inf` — but §7's done-means item 4 requires that a
changed property be **stated**, not found later by someone else. Whether it should surface
as the engine's own `ValueError` rather than a stdlib `OverflowError` rides on the §4.1
decision, since it is the same question about the same guard.

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

3. **Validate `energy` for finiteness at the boundary (D-015, closing O-12).** Reject NaN
   and ±inf with the same error shape as σ. **Negative energy is untouched** — D-014's
   ruling stands and the two questions stay separate, so the record stays legible.

   **The reason is not "consistency with σ", and stating it that way would understate it.**
   The engine seeds `contributions = {seed_node: [energy]}`, so **the seed's own activation
   is unguarded on every graph, connected or not** — part 2's guard is on `transmitted`,
   which only ever sees downstream values. A NaN at the seed therefore lands in the
   **returned** activation map, is consumed by `nous_field`, accumulated into basins, and
   reaches `Coalition.strength` and thence `_competition_key`, where **every NaN comparison
   is False and the ordering silently degrades**. That is DEFECT-C's own failure mode, one
   input earlier. The isolated node in §4.1 is the *visible instance*, not the risk.

**A consequence that must be stated here, or someone will delete the guard.** Once both
`energy` and σ are finiteness-validated, part 2's `transmitted` non-finite guard becomes
unreachable **within the documented parameter domain**.

> **CORRECTED 2026-07-26, on the builder's challenge — my earlier wording said "unreachable
> from the public API" and that was wrong.** `decay_per_hop` is *documented* as 0..1 but is
> **not validated**: D-015 scoped the boundary to `energy`. So `decay_per_hop=inf` or `nan`
> is a live public route that still reaches the guard, and it fires correctly —
> `ValueError: non-finite transmitted activation (inf) on road …`, verified. The guard is
> therefore not merely a theoretical backstop; it has a demonstrable public route today.
> **Whether `decay_per_hop` should itself be validated is a third question** — separate from
> σ (D-012) and from `energy` (D-015), and deliberately not answered here. It is low
> urgency precisely because the guard catches it loudly rather than silently, which is the
> failure mode that mattered. Flagged for Cagan; not decided by an agent.

> **`floor` is the third boundary, and it is brick 0c-ii — but note there are TWO floor
> questions and they are independent.** 0c-ii is the **finiteness** one: `floor=NaN`
> **silently** disables the locality guard (3 nodes reached instead of 6, no error,
> behaviourally identical to `floor=-inf`), which is exactly O-12's and DEFECT-C's class —
> a bad value accepted in silence. D-008, in SPEC-0b2 §5, is the **scale-invariance** one:
> whether an absolute floor is coherent under conservation. That one blocks the 0b2 default
> flip; this one blocks nothing. **Fixing either does nothing for the other.** Full table in
> SPEC-0d §7.1.
>
> `decay_per_hop` is deliberately *not* on this list: it refuses **loudly** via the guard
> above, and loud-versus-silent is the discriminator that decides what needs a boundary
> check (D-016).

It stays as a **backstop** — it protects against a future term that can manufacture a
non-finite value from finite inputs, which is exactly the class part 2 was written for. Two
things follow, and both are requirements:

- Its test **must inject below the boundary** (construct the non-finite `transmitted`
  directly rather than by passing a bad `energy`), because a test that drives it through the
  public API will now fail at validation and never reach the guard.
- The guard **must not be removed as dead code**. A future reader who finds no public route
  to it is reading correctly and concluding wrongly: this is belt *and* braces, and removing
  the belt because the braces hold is how the braces come to be load-bearing unnoticed.

**Prose correction, already made by D-012 and restated here so the spec is self-contained:
the neutral value is `None`, never infinity.** "σ → ∞ recovers the current engine" is true
analytically in the limit and catastrophic at the literal value. Large finite σ does behave
— σ = 1e300 was verified byte-identical to `None` — but that is a fact about large finite
σ, and the spec must not invite a caller to write `inf`.

### 4.1 O-12 — the tester's FAIL, and how it closes · **DECIDED (D-015)**

**Tester verdict on brick 0c: FAIL.** Seventeen of the eighteen enumerated properties hold
under adversarial and loop-closed conditions. **O-12 does not.**

O-12 says: *"No non-finite value can reach `activation` or `flow`, **by any route**,
independent of σ."* It does not hold, and the failing input is trivial:

```python
s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
A = s.add_node('A', NodeType.CONCEPT)
spread_activation(s, A, energy=float('nan')).activation[A]   # -> nan     (expected: refused)
spread_activation(s, A, energy=float('inf')).activation[A]   # -> inf
spread_activation(s, A, energy=float('-inf')).activation[A]  # -> -inf
```

**Root cause.** The engine seeds `contributions = {seed_node: [energy]}` before any work,
and §4's guard is on `transmitted`. A seed that never transmits offers the guard nothing to
inspect, so the value is returned verbatim. A second route reaches it on a graph that *does*
have out-roads: `hop_budget=0`.

**Why this one matters more than its blast radius suggests.** The builder's own guard test
used a two-node fixture `A→B`, where `transmitted` always exists and the guard always fires.
Delete the edge — an isolated node, which the same suite already exercises elsewhere — and
the invariant fails. **The test passed on a hand-chosen input and fell apart on the
adversarial one**, which is the exact failure CLAUDE.md rule 4 exists to catch.

**Honest bounds, verified here, so it is not overstated.** It is **pre-existing**: the
pre-0c engine returns `nan` on the same input, confirmed against the committed engine. And
**no internal caller can reach it** — `build_activation_field`'s energies come from
`perceive()` / `cluster_sources()` and are always finite. It is caller-supplied input, the
same class σ=inf was before §4 closed that one.

**DECIDED by Cagan, D-015: option (A).** D-014 declined `energy` validation — but that
decision was argued about *negative* energy, and this is *non-finite* energy. The two are
not the same question and the earlier answer was not stretched to cover it. The fix is
specified in §4 part 3, with the reason stated as the general one rather than as
consistency with σ. **Option (B) was rejected on its own description: it weakens an
invariant to fit an implementation, which is the one move this project cannot make.**
O-12's wording stands unchanged, and becomes true.

- **(A) Close it in code.** Validate `energy` for finiteness at the same boundary σ is
  validated. Consistent with §4's own reasoning — the NaN hazard was already judged "more
  general than σ" — and makes O-12 true as written. Cost: one more boundary check, and it
  reopens the question D-014 closed, though on different grounds.
- **(B) Narrow O-12's wording** to "no non-finite value can pass the floor guard", and
  record the seed-energy route as an accepted, asserted limitation. Cost: the invariant no
  longer says "by any route", and a caller passing `nan` still gets `nan` back silently.
- **(C) Validate both `energy` and the seed contribution** — a superset of (A) that also
  covers any future pre-seeded value. Cost: scope creep beyond the defect.

The options are retained above because the reasoning that rejected (B) is the reusable
part: an invariant that asserts something false is fixed by making it true, not by
narrowing it until it is.

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

*Tester-owned (5 files, **9** sites — corrected from 8 on the tester's audit):*
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

### 5.4 A count that depends on the environment is not a fact about the code

Found by the builder during the §2.5 pass, and verified here. `tests/test_tester_0b2_adversarial.py`
reports **83** assertions in the repository and **81** in a checkout without `.git` — a
`git archive` extract, a release tarball, a Docker `COPY`, the Zenodo artifact:

```
git archive HEAD | tar -x -C /tmp/nogit   # no .git present
  NOTE: git unavailable — oracle 1 skipped; oracle 2 (independent reference) still runs
  NOTE: git unavailable — pre-change read-count comparison skipped
```

Reason for the pragma below: this section exists *because* the figure disagrees with the
ledger. "Correcting" it to the ledger's number would delete the finding it documents.

<!-- ledger:allow-count -->
That run ends `RESULT: 81 passed, 0 failed`, against the **83** the ledger records for the same suite on the same code.

The cause is benign and the consequence is not. Two tests degrade gracefully when the
git-recovered oracle is unavailable — which is correct behaviour — but they degrade by
emitting **fewer checks**, so the total moves. `tools/ledger_check.py` C1 treats per-suite
counts as fixed facts and runs in CI, so it would report a stale ledger for a reason that
has nothing to do with the code.

**The principle, which is the same one this whole brick is about, one level up: a number
the project publishes must be a property of the code, not of the environment that ran it.**
The project already refuses to let a determinism claim depend on an interpreter; it should
equally refuse to let its headline assertion count depend on whether version-control
metadata happens to be present. O-17 requires the count be made invariant — the graceful
degradation stays, but the *number of checks* must not move: record git-availability as an
observation, and keep the check count constant.

This is tester-owned work in a tester-owned file, and it lands naturally in the same pass
that re-bases the oracle (O-8), since both concern the same two tests.

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
- **O-4b** **Competition-path determinism** (§1 case 2, §2.5.1). `think()` on the eight-node
  two-domain graph yields **one** bit pattern for `r.thought.strength` across fresh
  processes, on **every** interpreter — 3.10 and 3.11 especially, since 3.12+'s compensated
  `sum()` masks the defect. Numbered out of sequence because it was added after the rest:
  it is the second reproduction case of O-4's own claim, not a new claim. Assert winner
  *membership* alongside strength, so a future flip is attributable.
- **O-5** Generalised: over a battery of randomly generated adversarial graphs including
  high in-degree, cycles, self-loops and closed roads, every graph yields one bit pattern
  across fresh processes.
- **O-6** Order-perturbation invariance: permuting `roads_from` leaves activation **values**,
  `hops` and the breakthrough **set** bit-identical. **Corrected on the tester's
  measurement:** the draft said "leaves output bit-identical", which claims more than holds.
  `activation`'s **key order** necessarily moves — key order is first-arrival order, and
  perturbing arrival order is the whole point of the probe (0 value differences in 6,090
  comparisons; 1,159 key-order differences). Assert invariance of what is invariant, and
  assert the key-order movement rather than pretending it away.
  **Required unconditionally** under the §2.3 decision, and it is the invariant that
  distinguishes a fix at the cause from a fix at the symptom. The tester already built the
  permuting store proxy during the 0b2 pass; it changes role here from demonstrating the
  defect to certifying its absence.
- **O-7** ASSERTED-NEGATIVE, to bound the claim, **in its amended form (§1)**: two
  isomorphic graphs built in different insertion orders agree on every activation **value**
  bit-for-bit, but differ in `activation`'s **key order** and therefore in `ranked()`'s
  order among tied entries. Assert both halves — the agreement *and* the divergence — so
  the §1 guarantee is read as exactly what it is.

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
  a written justification. Machine-checkable. **Unconditional — §2.5 is decided.**
- **O-16** **Cross-interpreter bit-identity**, which nothing checks today: the same graph
  produces identical bit patterns on all five interpreters, not merely identical per-suite
  counts. Scoped honestly to **one machine** — IEEE-754 arithmetic is exactly rounded and
  version-independent, but transcendental functions (`math.exp` in the decay path) come
  from the platform's libm, so this is a claim about interpreters, not about platforms.
  Achievable once §2.5 lands, and **unachievable before it** — which is why §2.5 is in
  this brick and not a later one.
- **O-17** **The assertion count is a property of the code, not the environment** (§5.4).
  `tests/test_tester_0b2_adversarial.py` must report the same total in the repository and
  in a `git archive` extract with no `.git`. Graceful degradation stays; the *check count*
  must not move. Machine-checkable, and it protects `ledger_check` C1 from failing on a
  release tarball for a reason unrelated to the code.

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

**Amended 2026-07-26 — the red list is larger than six, and the spec under-enumerated it.**
The builder's run turned **four further tests** red, none of which indicates a problem with
the fix. The tester must expect them and rewrite them, not investigate them:

| Also red | Why | Action |
|---|---|---|
| `test_N5_DEFECT_B_scoping_absent_from_the_pre_change_engine` | Asserts the source contains `store.get_road(` **twice**. After §3 it appears **once** — which is the fix working. | Rewrite the expected count to 1. |
| `test_N1_byte_identity_vs_git_pre_change_engine` | The git oracle models the naive accumulator. | Restrict to in-degree ≤ 2 per §2.3's boundary, or retire. |
| `test_N1_byte_identity_vs_independent_reference` | **The trap in O-8, firing exactly as predicted.** The reference still models the old accumulator, so it now agrees with a broken engine. Tellingly, it produces byte-identical partition numbers to the git oracle — the signature of a second copy of the same accumulator. | **Re-base onto ordered + `fsum` semantics.** This is part of the fix, not an afterthought. |
| `test_N1_byte_identity_loop_closed_on_a_system_built_substrate` | Same stale oracle. | Same re-base. |

Two notes for whoever runs this. The two DEFECT-C asserted-negatives now **raise** rather
than fail, which **aborts the suite** and hides the 13 tests after them (N-8 ×4, N-9 ×4, R1,
R2, S1, S2). The builder ran those directly against the unmodified file: all pass, so O-13
holds — but the tester must confirm that independently rather than take it on report. And
the ordering of the rewrite matters: until the two raising tests are converted, the suite
cannot report on anything downstream of them.

Minor, tester-owned: `load_pre_change_engine()` writes its temporary oracle into `tests/`
and removes it in a `finally`, so an *interrupted* run can leave `tests/__pre0b2_oracle.py`
behind (it did once, during the 0b2 pass). It should write to a temp directory instead.

---

## 7. Done means

**0c is done when:**

1. O-1 … O-16 **plus O-4b** hold, verified by the tester in its own lane, on all five
   interpreters. O-15 and O-16 are now unconditional: §2.5 is decided.
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
- O-8 fails → **and here the spec must be read carefully, because it was wrong once.** An
  N-1 failure has **two** possible causes and they mean opposite things:
  - **(i) the oracle is stale** — it still models the naive accumulator, so it agrees with a
    broken engine and disagrees with a correct one. This is O-8's TRAP firing, it is
    *expected* on the first run after the fix, and it is **not** a falsifier.

    **The signature, CORRECTED 2026-07-26 — the builder's version of it was wrong in three
    details and the tester falsified it by measurement.** The builder reported that
    `flow`/`hops`/`broke_through` stay byte-identical, that mismatches occur only at 3+
    contributions, and that 14,397 of 17,017 comparisons matched. Measured independently:
    **`flow` does differ** (16 spreads against the git oracle, 35 against the reference),
    **11 mismatches occur below the 3-contribution line** — which is the off-by-one this
    spec had in its own boundary, see §2.3 — and the byte-identical count is **15,606**, not
    14,397. Only "max gap 2 ULP" survived intact.

    The *conclusion* nonetheless stands, and the tester established it on a stronger and
    non-tunable criterion than the one it replaced: **every deviation is downstream
    propagation, not a change in the transmission rule.** All out-roads of a moved source
    shift by **one common ratio** — 25/25 and 35/35 groups, maximum relative move 4.44e-16.
    A changed rule could not produce a single shared ratio across a source's whole
    out-neighbourhood; a changed *input* to an unchanged rule is exactly what does.

    Use the common-ratio criterion, not the byte-identity counts. Under it the correct
    action is to **re-base the oracle**, not to revert the fix. Recording this because a
    plausible-sounding signature that is wrong in its details is worse than none: it invites
    the next reader to match on the wrong features.
  - **(ii) the fix genuinely changed neutral behaviour** — the real falsifier. The signature
    is anything the above does not cover: a mismatch at a node with fewer than three
    contributions that is not explained by a differing *upstream* flow, or any difference in
    `flow`, `hops` or `broke_through`.

  The draft carried only (ii), which would have told the tester the fix broke neutrality
  when it had not. Distinguishing them is mandatory before N-1 is called a failure.
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
