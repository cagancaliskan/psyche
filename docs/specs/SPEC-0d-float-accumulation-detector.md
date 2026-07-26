# SPEC-0d — A detector for naive float accumulation, then the sites it finds

**Status:** DESIGNED · ready for the builder
**Revises:** nothing. Adds a structural check, then fixes what it reports.
**Depends on:** D-015 (call 2 — this site is 0d, not a third widening of 0c), SPEC-0c
**Date:** 2026-07-26
**Author lane:** architect-pm

---

## 0. Framing

### 0.1 The one thing that makes this brick different

**The deliverable is a detector, not a patch.** The two known `nous_field.py` sites are
fixed *by* this brick, but they are not the point of it — they are its first output, and
its acceptance test.

The reason is a record this project can now read off its own history:

| # | Site | How it was found |
|---|---|---|
| 1 | `nous_coalitions.py` ×2 | BUG-0b1 — an existing adversarial test happened to fire on an interpreter that exposed it |
| 2 | `nous_workspace.py:426` | SPEC-0c §2.5 — someone asked "where else?" *after* the first fix |
| 3 | `nous_field.py:131` | SPEC-0c §2.7 — the tester was asked "was that sweep exhaustive?" |

**Three encounters, three times found by looking. Never once by a sweep.** Each time the
project fixed the instance and moved on; each time an instance survived. Twice the surviving
instance was in a file the previous fix's author had open. A fourth manual hunt has no
better prior than the first three, and the cost of being wrong is now known: BUG-0b1 was
reported closed for four weeks while a live instance sat on the same path.

So 0d inverts the order. **Build the thing that enumerates, then fix what it enumerates.**

### 0.2 What this brick is not

No cognitive claim. `0d` is a brick about floats and about a lint. It does not touch the
meaning bar.

It is also **not a determinism repair**. The known sites are *order-pinned*: their iteration
order is program order, so they are reproducible across processes. Nothing in 0d restores a
falsified determinism claim, and 0d must not be described as though it did. What it closes
is the gap between "pinned" and "independent" — the same gap D-013 ground 1 refused to leave
open at the activation accumulator.

---

## 1. The claim 0d must make true

> Every float accumulation in `src/` is either exactly rounded (`math.fsum`) or **registered
> in the ledger with a stated reason**, and a newly-introduced naive accumulation fails the
> canonical suite.

The second clause is the one that matters. A fix is a fact about today; a detector is a fact
about every commit after it.

---

## 2. The detector

### 2.1 What it must find

An accumulation is any construct that reduces two or more floats into one, where the
reduction order is not fixed by the *values*. In this codebase that is three shapes:

```python
total[k] = total.get(k, 0.0) + v      # the += -into-a-dict shape (DEFECT-A, §2.7)
acc += v                              # a running local
sum(iterable_of_floats)               # the builtin (BUG-0b1, SPEC-0c §2.5)
```

The builtin-`sum` shape is already at zero in `src/` after 0c, and the detector must keep
it there — that is the regression half of its job.

### 2.2 What it must not do

**It must not flag integer accumulation, and it must not require `fsum` where `fsum` is
wrong.** `math.fsum` on integers returns a float and would silently change types;
`creation_seq` counters, `access_count`, and any `len`-like tally must be left alone. The
detector therefore reports *candidates* and requires each to be **adjudicated once**, not
mechanically rewritten.

### 2.3 The registry, and why the exemption list lives in the ledger

Every candidate is either converted or entered in `tools/ledger.json` under a new
`float_accumulation_exemptions` key, with the site and a one-line reason. Putting the
exemption list in the ledger rather than in a code comment is deliberate: the ledger is
already the file this project treats as the single source of truth, it is already checked in
CI by `ledger_check.py`, and an exemption that must be written down where the counts live is
an exemption someone will read. A `# noqa`-style comment at the site would be invisible at
exactly the moment it matters.

### 2.4 Where the check lives

`tools/ledger_check.py`, as a new check **C6**, alongside C5's runner-completeness. It runs
in CI, it is stdlib-only, and it fails the build. It is a *structural* check over source
text, not a runtime test — the same category as C4's forbidden-claim scan, and it should
reuse that machinery.

---

## 3. The sites the detector must find on its first run

Both are in `src/nous_field.py`, and the pair is instructive because **only one of them
reproduced**.

**Site A — `nous_field.py:131`, confirmed.**
```python
total[node] = total.get(node, 0.0) + act
```
Reproduced: `field.total[m1]` takes **two distinct bit patterns over the source-order
permutations**, and the difference reaches `Coalition.strength`.

**Site B — `nous_field.py:124`, `merged_flow`, not reproduced.**
```python
merged_flow[rid] = merged_flow.get(rid, 0.0) + fv
```
**Identical shape. A four-way-convergence probe produced no variation.**

**Site B is the whole argument for this brick.** It has the same defect shape as site A,
in the same file, four lines away — and a targeted probe said it was fine. That is the
friendly-input trap in its purest form: an input chosen by someone who already believed the
site was safe, returning the answer they expected. Had 0d been a reproduction hunt, site B
would have been marked clean and left in place, exactly as `nous_workspace.py:426` was left
in place by BUG-0b1.

**Therefore: site B is converted on the strength of its shape, not on a reproduction.** This
is the one place in this project where "we could not make it fail" is explicitly *not*
accepted as evidence of correctness — because the same sentence has now been wrong three
times about this same shape.

---

## 4. Invariants (the tester's lane)

**The detector**

- **F-1** The detector reports both `nous_field.py` sites on the pre-fix tree. A detector
  that does not find the known instances is not a detector. This must be demonstrated
  against the pre-fix source, not asserted.
- **F-2** After the fix, the detector reports zero unregistered candidates in `src/`.
- **F-3** **Sensitivity, and this is the acceptance test:** introducing a *new* naive
  accumulation into `src/` makes the canonical suite fail. Demonstrated by injecting one
  into a scratch copy — never by editing `src/` to prove the point.
- **F-4** The detector does not flag integer accumulation (`creation_seq`, `access_count`,
  `traversal_count`) and does not flag the exempted entries.
- **F-5** Every exemption in `float_accumulation_exemptions` names a real site and carries a
  reason; a stale exemption naming a site that no longer exists is itself a finding.

**The two conversions**

- **F-6** `field.total` is order-independent: permuting the source list yields bit-identical
  totals. This is the property, and it is stronger than the reproduction that motivated it.
- **F-7** `merged_flow` likewise — asserted **structurally**, since §3 records that no probe
  made it vary. The test asserts `fsum` semantics, not the absence of a witness.
- **F-8** Cross-process and cross-interpreter bit-identity of `build_activation_field` over
  adversarial multi-source graphs, on all five interpreters × six hash seeds.
- **F-9** No categorical outcome changes anywhere: same winners, groupings, prunes. A float
  moving is expected; an outcome flipping is a finding and stops the brick.

**Scope honesty**

- **F-10** ASSERTED-NEGATIVE: 0d closes the sites the detector finds **in `src/`**. It does
  not scan `experiments/`, and it makes no claim about paths outside the canonical modules.
  State the boundary so nobody reads the detector as a whole-repository guarantee.

---

## 5. Done means

1. F-1 … F-10 hold, tester-verified, on all five interpreters.
2. The detector runs in `ledger_check.py` as C6 and fails the build on a new naive
   accumulation — demonstrated by injection, per F-3.
3. `src/` contains zero unregistered float accumulations.
4. The delivery report states which values moved and confirms no categorical outcome did.

**External and unfakeable:** F-3. A detector that cannot be shown to catch a defect
deliberately introduced is a decoration, and this project has just spent two bricks learning
what decorative checks cost.

## 6. What would falsify success

- F-3 fails → the detector does not detect, and 0d has delivered two point fixes wearing a
  detector's name.
- F-9 fails → the conversions changed behaviour rather than stabilising it; that is a
  finding, not something to absorb.
- The detector reports a large number of candidates that are all legitimately exempt → the
  shape is too coarse to be useful, and it should be narrowed before it trains people to
  approve exemptions without reading them. **An exemption list nobody reads is worse than no
  check**, because it converts a real signal into a ritual.

## 7. Roadmap impact

0d does not block Phase 0's re-labelling: 0a and 0b turn on 0c's determinism claim, and
§2.7's site is order-pinned and therefore not part of that claim. 0d can land after Phase 0
returns to `PROVEN`, and it should — it is a hardening brick, not a repair.

It does bear on the default-flip and the floor brick, both of which run more activation
through `nous_field`.

**Single next action:** hand to the builder, detector first. The two conversions must not
land before the detector that justifies them, or the brick becomes a third point fix and the
record above gains a fourth row.
