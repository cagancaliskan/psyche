# SPEC-0d — A detector and a registry for float accumulation

**Status:** **PROVEN, within a stated scope** · tester PASS on re-verification 2026-07-26
(D-022) · L3 is scheduled as brick 2f's STEP ZERO, not as a 0d task
**Revises:** nothing. Adds a gate. **Fixes nothing — deliberately.**
**Depends on:** D-015 (this site is 0d, not a third widening of 0c), D-016, SPEC-0c
**Date:** 2026-07-26
**Author lane:** architect-pm

---

## 0. Framing

### 0.1 The deliverable is a detector and a registry. It is not a patch.

0d ships **two things and no third**: a structural check that enumerates every float
accumulation in `src/`, and a registry in `tools/ledger.json` that each one must appear in
with a reason. **The known sites are registered, not converted.**

That is a deliberate reversal of the obvious move, and the reason is the only thing in this
spec worth remembering:

| # | Site | How it was found |
|---|---|---|
| 1 | `psyche_coalitions.py` ×2 | BUG-0b1 — an existing adversarial test happened to fire on an interpreter that exposed it |
| 2 | `psyche_workspace.py:426` | SPEC-0c §2.5 — someone asked "where else?" *after* the first fix |
| 3 | `psyche_field.py:131` | SPEC-0c §2.7 — the tester's review question: "was that sweep exhaustive?" |

**Three encounters, three times found by a person looking. Never once by a sweep.** Each
time the project fixed the instance and moved on; each time an instance survived. Twice the
survivor sat in a file the previous fix's author had open.

A fourth manual hunt has no better prior than the first three. **So 0d builds the sweep, and
fixes nothing** — because a brick that both builds the gate and clears the backlog behind it
tempts everyone to read the empty backlog as the deliverable. The deliverable is the gate.

### 0.2 Why not fix the two known sites here

Because the value of this brick is that **the gate goes red on anything new** — including
what Phase 2 will introduce — so the remaining hardening **forces itself** instead of
relying on someone remembering to do it.

This repository has twice proved that a recorded intention does not hold here:
`experiments/harness.py:290` documented the naive-sum hazard in writing while the substrate
carried `PROVEN` for a month; BUG-0b1's report claimed "two sites" and a third survived four
weeks on the same competition path. **A note is not a control. A failing build is.**

If 0d also fixed `psyche_field`, the next naive accumulation would still arrive unannounced
and the brick after it would be a fifth manual hunt. Registering the known sites and leaving
them is what converts "we should look again sometime" into "the build stops."

### 0.3 What this brick is not

No cognitive claim. It is also **not a determinism repair**: both known sites are
*order-pinned* — their iteration order is program order, so they are reproducible across
processes and falsify nothing 0c asserts. 0d must never be described as restoring a
determinism property. It closes the gap between *pinned* and *independent*, and it closes it
by making the gap **visible**, not by eliminating it.

---

## 1. The claim 0d must make true

> Every float accumulation in `src/` is either exactly rounded (`math.fsum`) or **registered
> in `tools/ledger.json` with a stated reason**, and an unregistered naive accumulation
> **fails the canonical suite**.

The second clause is the whole brick. A fix is a fact about today; a gate is a fact about
every commit after it.

---

## 2. The detector

### 2.1 What it must find

Any construct reducing two or more floats into one where the reduction order is not fixed by
the values. In this codebase, three shapes:

```python
total[k] = total.get(k, 0.0) + v      # the +=-into-a-dict shape (both psyche_field sites)
acc += v                              # a running local
sum(iterable_of_floats)               # the builtin (BUG-0b1, SPEC-0c §2.5)
```

The builtin-`sum` shape is at **zero** in `src/` after 0c. Keeping it at zero is the
regression half of the detector's job.

### 2.2 What it must not do

**It must not flag integer accumulation, and must not demand `fsum` where `fsum` is wrong.**
`math.fsum` over integers returns a float and would silently change types: `creation_seq`,
`access_count`, `traversal_count` and any `len`-like tally are out of scope. The detector
reports **candidates for adjudication**, and each is adjudicated **once**.

### 2.3 The registry, and why it lives in the ledger

A new top-level key in `tools/ledger.json`:

```
"float_accumulations": {
  "<path>:<symbol>": { "verdict": "fsum" | "registered", "reason": "<one line>" }
}
```

It lives in the ledger and not in a code comment for one reason: **the ledger is already the
file this project treats as the single source of truth, and it is already checked in CI.** A
`# noqa`-style comment at the site is invisible at exactly the moment it matters — when
someone is deciding whether a new accumulation is like the old ones.

### 2.4 Where the check lives

`tools/ledger_check.py`, as check **C6**, beside C5. Stdlib-only, structural over source
text (the same category as C4's forbidden-claim scan, and it should reuse that machinery),
and it **fails the build**.

---

## 3. The registry's opening entries

### 3.1 The model entry — and registry entries should aspire to this form

**`src/psyche_activation.py` — the `flow` accumulator.**

```python
flow[rid] = flow.get(rid, 0.0) + transmitted
```

Naive, and **deliberately not converted.** It is registered with a **bound**: under
hop-layered single expansion a road's source expands exactly once, so a road transmits
exactly once and **the add's second operand cannot exist**. The tester measured it — 574
spreads across 60 hostile graphs (cycles, self-loops, fans), no road read twice in any
spread — and the `+` is structurally single-term.

**A bound is stronger than a conversion, and this is the point of the registry.** A
conversion says *"this site can no longer break."* A bound says *"here is why this site
cannot break"* — which survives refactoring as an argument a future reader can check and
falsify, rather than as a call they must not accidentally undo. Converting this site to
`fsum` would have hidden the reasoning behind an idiom.

Registry entries should aspire to this form: a reason that explains, not a reason that
asserts. "Registered because it is single-term, proven over N adversarial graphs" is an
entry that does work. "Registered because it is fine" is an entry that trains people to skim.

### 3.2 `src/psyche_field.py:131` — confirmed order-dependent, registered not fixed

```python
total[node] = total.get(node, 0.0) + act
```

Confirmed: `field.total` takes **two distinct bit patterns over the source-order
permutations**, and the difference reaches `Coalition.strength`. **Order-PINNED** — source
order is program order — so it is **not** a determinism defect and no 0c result depends on
it. Registered with exactly that reason and left in place.

### 3.3 `src/psyche_field.py:124` — CORRECTED: the symptom was present; the probe could not see it

```python
merged_flow[rid] = merged_flow.get(rid, 0.0) + fv
```

> **THIS SECTION WAS WRONG, and the correction is worth more than the original claim.**
> It read: *"same shape as §3.2, four lines away. A four-way-convergence probe produced no
> variation. Shape present, symptom absent — this pair is the entire case for a detector."*
> The tester ran the entry's own falsifier on 2026-07-26 and **it fires**: 2 distinct bit
> patterns over 4! source orders, on 40 of 40 randomly generated convergent stores.

**Why the clearing probe could not have worked, which is the actual lesson.** The probe used
four sources converging on **one node**. At hop 1 every road is traversed by exactly **one**
source's spread, so each `merged_flow` value is **single-term** — and a single-term sum cannot
vary by reordering. The probe was **structurally incapable of exhibiting the symptom it was
run to look for.** A shared road must sit **downstream** of the convergence to accumulate
terms from several spreads; put it there and the site moves.

That is the six-bug checklist's **structurally-impossible branch** — *"can a branch never
fire? prove the structure can do what it claims"* — occurring **inside the brick built to stop
exactly this class**, and written into this spec as its headline argument. Recorded rather
than quietly amended, because the failure mode is the point: a clearing probe that cannot
fail is indistinguishable from a passing one, which is the same sentence as F-3's, one level
up.

**So the case for a detector is stronger than the false version, not weaker.** The original
argument was *"a site can have the shape and lack the symptom, so shapes must be enumerated."*
The true argument is: **a site can have the shape, have the symptom, and still clear a probe
that a competent person designed to look for it.** Reproduction cannot be the gate. Only
enumeration can.

**The corrected registry entry** carries the verdict `CONFIRMED ORDER-DEPENDENT, order-pinned`
— identical to §3.2 — and rests on a bound that has been verified rather than assumed:
`ActivationField.flow` **has no reader in `src/`**. `form_coalitions_from_field` reads only
`field_.total`, `field_.broke_through` and `field_.dominant`; the `.flow` read inside
`form_coalitions` is `ActivationResult.flow` from a single spread, and `form_coalitions` has
no caller in `src/`. Falsifier: any consumer that starts reading `ActivationField.flow`.

---

## 4. Invariants (the tester's lane)

**The detector — and F-3 is the one that matters**

- **F-1** The detector reports all four known accumulation sites (§3.1–3.3 plus any
  `fsum` sites) when run against `src/`. A detector that does not find the known instances
  is not a detector; demonstrate this, do not assert it.
- **F-2** With the registry populated, the detector reports **zero unregistered** candidates.
- **F-3** **ACCEPTANCE TEST — injection.** Introducing a *new*, unregistered naive
  accumulation into a **scratch copy** of `src/` makes the canonical suite go **red**.

  > **A detector that passes because it found nothing is indistinguishable from a detector
  > that is broken.** "It passes" is not evidence that it works, and must not be accepted as
  > such. The only evidence is a deliberately planted defect that it catches. Inject into a
  > scratch copy — never edit `src/` to prove the point.

  Inject at least three shapes: `+=` into a dict, a running local, and a builtin `sum` over
  floats. A detector that catches one shape and misses two is worse than none, because it
  will be trusted.
- **F-4** No false positives on integer accumulation (`creation_seq`, `access_count`,
  `traversal_count`).
- **F-5** A **stale registry entry** — one naming a site that no longer exists, or whose
  verdict no longer matches the source — is itself a finding. A registry that can rot
  silently is a note again.

**The registry's honesty**

- **F-6** Every entry names a real site and carries a reason that is checkable rather than
  decorative. The `flow` bound (§3.1) is the reference standard.
- **F-7** ASSERTED-NEGATIVE: `psyche_field.py:131` **is still order-dependent** after 0d, and
  a test asserts it. 0d fixes nothing, and the record must not drift into implying it did.
  This test goes red when a later brick converts the site — which is the correct signal, and
  that brick re-verifies here.

**Scope honesty**

- **F-8** ASSERTED-NEGATIVE: the detector scans `src/` only. It makes no claim about
  `experiments/`, `tests/` or `tools/`. State the boundary so the gate is never read as a
  whole-repository guarantee.

---

## 5. Done means

1. F-1 … F-8 hold, tester-verified, on all five interpreters.
2. C6 runs in `ledger_check.py` and fails the build on an unregistered naive accumulation,
   **demonstrated by injection of three distinct shapes** (F-3).
3. `src/` contains zero *unregistered* float accumulations — and **the two `psyche_field`
   sites are still naive**, registered rather than converted.
4. The verification notes state plainly that 0d fixed nothing and explains why that is the
   deliverable.

**External and unfakeable:** F-3. Everything else in this brick can be satisfied by a check
that always returns "clean."

## 6. What would falsify success

- F-3 fails on any injected shape → the detector does not detect, and 0d has shipped a
  ritual.
- The detector reports a large number of candidates that are all legitimately exempt → the
  shape is too coarse, and it should be narrowed **before** it trains people to approve
  entries without reading them. **A registry nobody reads is worse than no check**, because
  it converts a signal into a formality.
- Anyone "closes" 0d by converting the `psyche_field` sites and finding the detector then has
  nothing to report → that is §0.2's failure mode, and it means the gate was never tested
  against the thing it exists to catch.

## 7. Re-validation cost, and the two floor questions it does *not* touch

**Re-validation cost: none.** 0d changes no production behaviour — it adds a check and a
ledger key. No brick is invalidated, and no capture value moves except the assertion count.
This is the cheapest brick in the log, which is precisely why it should not be bundled with
fixes that are not cheap.

**It also does not touch either floor question, and those two are independent of each other**
(see §7.1). 0d is about float *accumulation*; the floor is a *threshold*. No part of 0d
changes `DEFAULT_FLOOR`, its finiteness, or its semantics.

### 7.1 The two floor questions are independent — do not conflate them

They touch the same constant and are otherwise unrelated. Stated here, in SPEC-0b2 §5 and
in SPEC-0c, because the same constant appearing in two open questions is exactly how two
questions become one muddle:

| | **0c-ii — FINITENESS** | **D-008 — SCALE-INVARIANCE** |
|---|---|---|
| The question | May `floor` be non-finite? | Should `floor` be absolute or relative? |
| The defect | `floor=NaN` **silently** disables the locality guard — 3 nodes reached vs 6, no error, identical to `floor=-inf` | An absolute floor is not scale-invariant under conservation, so it becomes degree-dependent censoring |
| Class | Boundary hygiene. O-12's and DEFECT-C's class. | Constant semantics. |
| What it blocks | Nothing. | **The 0b2 default flip.** |
| Fixing it does what to the other | **Nothing.** | **Nothing.** |

Validating `floor` for finiteness leaves it just as absolute as it was. Making it relative
leaves it just as non-finite-able as it was. **Neither fix advances the other**, and a
delivery that claims otherwise is claiming a brick it did not build.

## 8. Roadmap impact

0d blocks nothing and is blocked by nothing. It should land **before** Phase 2 rather than
after, for one reason: Phase 2 will introduce new accumulation sites, and the entire value
of the gate is that it is standing **before** the code that would otherwise slip past it. A
gate installed after the traffic has passed is a fifth manual hunt wearing a detector's name.

**Single next action:** hand to the builder. Detector and registry only. If the builder
finds itself editing `psyche_field.py`, it has left the spec.

---

## 8. Dispositions from the re-verification (D-022)

**FINDING 0d-5 — narrow the wording, never widen the machinery.** `bound_on_absence`'s
docstring promises it flags *every* matching read; it under-reports on `getattr(x, 'flow')`,
`x.__dict__['flow']`, an aliased call, and `getattr(c, 'advance')()`. The bounds themselves
are true today and the realistic path is covered, so this blocks nothing — **but a promise
wider than its machinery is the same true-looking sentence that has now bitten this brick
three times, and the third occurrence of a pattern is where it stops being bad luck.**

Routed to the builder as a docstring change. It must **not** merely delete the
over-reporting claim; it must state **actionably** what *is* covered — direct attribute
access and direct calls — say plainly that dynamic access is not seen, and carry an exit
instruction. The machinery is not widened: over-reporting on the *type-ambiguity* axis
remains the right bias, and this is about describing it correctly.

**`field.total` now names a falsifier.** Five of six entries named one and this did not, and
five-of-six is a convention a reader generalises. Its "order-pinned" half rests on `sources`
arriving in program order — which comes from `cluster_sources` ordering `group_seeds` by
`creation_seq`, **not** from `build_activation_field`, which only dedups preserving what it
is given. Recorded in the entry with that provenance, because a falsifier that names the
wrong mechanism is worse than none.

**L3 is brick 2f's STEP ZERO, not a 0d task.** See SPEC-2f §0.5. 0d's scope closed by
decision; ownership sits with the brick that needs the coverage, and 2f's first act becomes a
demonstration that extending the gate is a normal cost of building on it.

**What "PROVEN" means for this brick**, since the two axes do not fit a tool cleanly: the
meaning axis is **vacuous** — a gate makes no claim an external yardstick will ever grade —
so `BUILT-UNVALIDATED` would imply a validation that can never arrive. The substrate bar is
met (determinism, purity; integrity has no analogue for a scanner) and the functional claim
is verified the only way a refusal can be: the retro-catch on three pre-fix trees, and
injection turning the build red. **PROVEN within a stated scope**, and the scope is L1–L10.
