# SPEC-0c-ii — Boundary hygiene: the parameters that are accepted in silence

**Status:** DESIGNED · re-scoped 2026-07-26 (D-020) from "the floor thing" to the class
**Revises:** nothing. Adds boundary checks to `spread_activation`.
**Depends on:** 0c `PROVEN` (which closed the same class for σ and `energy`)
**Date:** 2026-07-26
**Author lane:** architect-pm

---

## 0. The class, which is what this brick is actually about

0c-ii was registered as a floor question. **That framing is too narrow and it hid a second
item.** The brick is about one class, and both members of it are the same failure:

> **A boundary silently accepts a value it should refuse, and the caller gets a well-formed
> result that is wrong instead of an error that is right.**

That is DEFECT-C's shape (σ = `inf` → NaN, passing the floor guard because every NaN
comparison is False) and O-12's shape (non-finite `energy` written straight into the returned
map). Both were closed in 0c. **Two more members of the class remain**, and they are §1 and
§2 below.

**The discriminator is silence, not wrongness.** `decay_per_hop` is deliberately *not* on this
list: a non-finite `decay_per_hop` reaches the backstop guard and **refuses loudly**, naming
the value and the road (verified, SPEC-0c §4). Loud refusal of a bad input is acceptable
behaviour. Silent acceptance is not. That distinction is the whole scoping rule for this
brick, and it should survive into whatever comes after it.

---

## 1. Item one — `floor` accepts non-finite values and silently disables the locality guard

`floor=float('nan')` **silently disables the locality guard.** Measured: 3 nodes reached
instead of 6, no error, behaviourally identical to `floor=-inf`. The mechanism is the same one
DEFECT-C exploited — `transmitted < floor` is False for every NaN comparison, so the guard
that exists to keep the spread local never fires.

The consequence is not confined to activation. A silently wider horizon changes which nodes
are reached, which changes coalition membership, which changes the competition. **A caller
who passes a bad `floor` does not get an error; they get a different mind.**

**Fix:** validate `floor` for finiteness at the boundary, with the same error shape as σ and
`energy`. **Do not** validate its sign or magnitude — a negative floor is a legitimate way to
disable the guard *deliberately*, and 0c's tests rely on `floor=0.0`.

---

## 2. Item two — `spread_activation` accepts a `RoadID` as a seed

Found during the 0b2 re-verification, and verified independently.

`spread_activation`'s seed guard is `store.exists(seed_node)`, and **`exists()` is True for
RoadIDs** — it checks both the node table and the road table. So a road id passes the guard.

**The silent window is `hop_budget=0` specifically**, and the precision matters:

| call | behaviour |
|---|---|
| `spread_activation(s, road_id, hop_budget=0)` | **returns a well-formed `ActivationResult` seeded on a road**, no error |
| `spread_activation(s, road_id)` (default budget) | raises `NotFound` — from *inside* the expansion, not at the boundary |

So at the default budget the failure is loud but mislocated; at `hop_budget=0` it is silent
and the caller receives a result whose seed is not a node. **Verified identical on the
pre-overlay engine — this is pre-existing, and belongs to 0a/0b rather than to any overlay.**

**Reachability, honestly:** no internal caller can hit it. `build_activation_field` receives
node ids from `perceive()` and `cluster_sources()`. It is caller-supplied-input, the same
class σ was before 0c closed it — and the same argument applies: the guard exists, it is one
line, and "unreachable today" is a statement about today's callers.

**Fix:** the seed guard must check that the id resolves to a **node**, not merely that it
exists. That makes the refusal boundary-located and identical at every `hop_budget`.

---

## 3. The two floor questions are independent — kept here, deliberately

This table lives in SPEC-0b2 §5 and SPEC-0d §7.1 as well. It is repeated rather than
cross-referenced because one constant appearing in two open questions is exactly how two
questions become one muddle.

| | **0c-ii — FINITENESS** *(this brick, §1)* | **D-008 — SCALE-INVARIANCE** |
|---|---|---|
| The question | May `floor` be non-finite? | Should `floor` be absolute or relative? |
| The defect | `floor=NaN` **silently** disables the locality guard — 3 nodes reached vs 6, no error, identical to `floor=-inf` | An absolute floor is not scale-invariant under conservation, so it becomes degree-dependent censoring |
| Class | Boundary hygiene. O-12's and DEFECT-C's class. | Constant **semantics**. |
| What it blocks | **Nothing.** | **The 0b2 default flip.** |
| Effect of fixing it on the other | **None.** | **None.** |

Validating `floor` for finiteness leaves it exactly as absolute as it was. Making it relative
leaves it exactly as non-finite-able as it was. **Neither fix advances the other**, and a
delivery claiming otherwise is claiming a brick it did not build.

---

## 4. Invariants for the tester

- **B-1** Non-finite `floor` (NaN, ±inf) is refused at the boundary with `ValueError` naming
  the value, on every graph shape, **before** any road is read.
- **B-2** Negative and zero `floor` remain **accepted** — `floor=0.0` in particular, which
  0c's own suites depend on. A fix that rejects them implemented the wrong ruling.
- **B-3** A `RoadID` passed as `seed_node` is refused at the boundary, **identically at every
  `hop_budget` including 0** — the failure must stop being budget-dependent.
- **B-4** A valid `NodeID` still works unchanged; `NotFound` is still raised for an id that
  resolves to nothing, and still at the boundary.
- **B-5** Neutral byte-identity: for every input that was previously *valid*, output is
  byte-identical to the pre-0c-ii engine. **The gate.**
- **B-6** Determinism unchanged: bit patterns across 6 hash seeds × every CPython on the
  machine.
- **B-7** ASSERTED-NEGATIVE: `decay_per_hop` is still **not** boundary-validated, and still
  refuses loudly through the backstop guard. This is deliberate (§0) and must not be
  "tidied up" into consistency — assert the intended asymmetry so a future reader argues with
  a test rather than assuming an oversight.
- **B-8** ASSERTED-NEGATIVE, scope: this brick does **not** address D-008. `floor` remains
  absolute, and the horizon remains degree-dependent under normalization.

---

## 5. Done means

1. B-1 … B-8 hold, tester-verified, on all five interpreters.
2. `ledger_check` C6 (0d) passes — any new accumulation registered or `fsum`.
3. The delivery report states that this closes **boundary hygiene**, not the floor's
   semantics, and names D-008 as still open.

**External and unfakeable:** B-3 at `hop_budget=0`. That is the exact call that returns a
well-formed wrong answer today, and it either raises or it does not.

## 6. Re-validation cost

**Small, and it lands where 0c already established the pattern.** Both fixes are boundary
checks in `spread_activation`, which already validates σ and `energy` at that same point. No
data model changes, no store changes, no new accumulation. Re-validation is B-5's neutral
byte-identity plus the existing suites — the same shape as D-015's `energy` close-out, which
moved nothing.

**Ordering:** independent of 0d and 2f. It can land at any point. It is *not* a prerequisite
for 2f, and it does **not** unblock the 0b2 default flip — D-008 does that, and D-008 is a
different question (§3).
