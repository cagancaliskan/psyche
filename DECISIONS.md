<!-- ledger:ignore-file -->
# DECISIONS

Append-only. Every entry: date · what was decided · the evidence · who decided · what it
supersedes. **Never edit a past entry** — supersede it with a new one and link back.

A status change in `tools/ledger.json` with no entry here is a status change nobody can
audit. Write the entry first.

Format:

```
## D-NNN · YYYY-MM-DD · <one-line title>
**Decided by:** Cagan | architect-pm | tester | validator
**Supersedes:** D-NNN or —
**Context:** why this came up
**Options:** what was on the table, with the tradeoff that mattered
**Decision:** what was chosen
**Evidence:** the numbers or the artifact that justify it
**Cost:** what this invalidates or obliges us to redo
```

---

## D-001 · 2026-06-20 · The primary meaning bar is a behavioural effect, not a partition score
**Decided by:** Cagan
**Supersedes:** —
**Context:** 1c §6.2 compared the clustering layer's partition against an automatic Louvain
partition of the same graph. Should that be the project's headline meaning bar?
**Options:** (A) 1c §6.2 as the bar. (B) a behavioural effect graded against human norms.
**Decision:** B.
**Evidence:** "even a clean pass would only show two clustering principles agree, which is
low-value as evidence of cognition… meaning is established by what the system *does*, not by
one layer's partition shape."
**Cost:** 1c §6.2 demoted to a secondary structural check; it stays a recorded NOT YET
(mean ARI 0.228 against a 0.30 bar).

## D-002 · 2026-06-20 · The 1d-i pruning rule is a cohesion valley, not domain membership
**Decided by:** Cagan
**Context:** the realized watershed diverges from the specified intent. An unnamed domain
bridged at least as strongly as its own internal cohesion has no valley and is kept.
**Decision:** accept the valley rule as the intended design; no mechanism rework.
**Evidence:** the divergence is always safe-direction — it over-includes an unnamed domain
and never over-prunes a perceived member, verified across 60 random adversarial graphs.
**Cost:** over-swallow can recur in that specific topology; shipped as a standing
asserted-negative test rather than hidden.

## D-003 · 2026-06-21 · 1e priming is frozen NO-GO; do not manufacture a graded pass
**Decided by:** validator, accepted by Cagan
**Context:** the anti-circularity gate could not be populated on SWOW.
**Decision:** NO-GO. No `think()` was run on any selected pair; no graded number exists.
**Evidence:** N_S0 = 7 against a floor of 30; the fallback needed a rank-biserial of ~1.17
against a maximum of 1.0, unreachable by construction with r_W ≈ 0.97.
**Cost:** the primary meaning bar re-routes. No threshold was loosened.

## D-004 · 2026-06-21 · The fan effect is NO-GO; the engine change is held separate
**Decided by:** validator, accepted by Cagan
**Decision:** NO-GO — the generating mechanism is absent, not merely weak.
**Evidence:** the fan sweep is flat at 0.2433743975 across F ∈ {1,2,4,8,16}, spread 0.0.
`spread_activation` gives every out-road the source's full activation; there is no
`/ len(out_roads)` and no per-source budget.
**Cost:** adding normalization is held as a **separate, later, explicitly-framed
architecture decision** — adopting it *in order to* produce the effect would not earn it,
and it would force re-validation of 1c and 1d.

## D-005 · 2026-06-21 · 2c records an honest NOT-YET rather than a manufactured band
**Decided by:** Cagan
**Options:** (1) record the NOT-YET now. (2) re-spec the body-state signal.
**Decision:** option 1. The graded run does not proceed.
**Evidence:** `friction = 1 − cpu/wall` is a stall fraction; a realistic `think()` is ~47 µs
of CPU-bound work so friction ≈ 0, and it is scale-invariant. The measured band [0.79, 0.93]
was yield-dominated by an injected 0.5 ms sleep, not contention.
**Cost:** option 2 remains open but must earn its own fresh feasibility pre-check. The
mechanism is not defective — tester PASS on 350 adversarial assertions, pilot GO at 85%.

---

<!-- New entries below. Newest last. -->

## D-006 · 2026-07-25 · Coalition strength sums with math.fsum
**Decided by:** Cagan (pending) — proposed after an independent baseline run
**Supersedes:** —
**Context:** establishing a clean baseline before the 0b2 engine work surfaced a
cross-process determinism failure that the project's own adversarial test catches but that
had never been run on an interpreter which exposes it.
**Options:** (A) `math.fsum` — exactly rounded, order-independent by construction.
(B) sort members by `creation_seq` before summing — works, but leaves plain `sum`
associativity-sensitive to future refactors.
**Decision:** (A). Two lines, both in `src/nous_coalitions.py`.
**Evidence:** on CPython 3.11 at a **fixed** `PYTHONHASHSEED=0`, `test_T6b` returned two
different winners across 30 runs (22 / 8). The 1-ULP difference in `_density_score` resolved
the comparison before the `min creation_seq` tie-break could run, making the tie-break
unreachable in practice. After the fix: 40/40 identical on 3.11, and 20 suites / 1,372
assertions / 0 failures on 3.11, 3.12 and 3.13. Canonical count unchanged; no assertion
weakened.
**Cost:** none to the counts. Obliges the methodology change in D-007.

## D-007 · 2026-07-25 · Determinism is checked across interpreter versions, not only hash seeds
**Decided by:** Cagan (pending)
**Context:** BUG-0b1 was caught by a test that was correct all along. What failed was
coverage — an invariant asserted over a randomisation axis is only verified over the axes
you sweep, and interpreter container layout is a second axis `PYTHONHASHSEED` cannot reach.
**Decision:** `run_tests.py` sweeps every CPython minor version on the machine; the swept set
is recorded in `docs/TEST_OUTPUT.txt` and in `tools/ledger.json` under
`determinism.interpreters_swept`. Until that set equals `interpreters_required`, the
determinism claim is stated as scoped to the swept set.
**Evidence:** see D-006.
**Cost:** a longer test run. Adds one paragraph to the paper's methodology section — a
strengthening, since the discipline caught a real bug the moment coverage widened.

## D-008 · 2026-07-25 · Sigma is fixed at 1.0 on principle; the activation floor becomes the second brick of 0b2
**Decided by:** Cagan
**Supersedes:** —
**Context:** SPEC-0b2 adds divisive normalization at the transmission site as a default-off
overlay. The fan effect falls out untuned at sigma = 1.0, but sigma = 1.0 silences SWOW: at
~114 mean out-degree per cue, every target falls below the 0.02 activation floor.
**Options:**
- **(1) sigma fixed at 1.0, and revisit the floor.** Cleanest principle. Largest
  re-validation surface, because the floor governs the spreading horizon that 1c and 1d were
  verified against.
- **(2) sigma proportional to S_out.** Scale-free and never silences, but the fan gradient is
  algebraically capped below by c/(c+1) and is essentially flat past out-degree 10, so a
  graded fan run would likely fail on shape.
- **(3) sigma proportional to S_out^beta.** Graded falloff without silencing, at the price of
  a new free parameter with no principled value.
**Decision:** **(1).** sigma = 1.0, fixed on the stated principle and not fitted: 1.0 is the
maximum strength a single saturated road can carry, so sigma = 1.0 reads as "transmission
halves when the competing conductance out of a source equals one fully saturated road."

The activation floor is hereby reclassified. It is not a side effect of this change; it is
**the second brick of 0b2**, with its own spec, its own tester pass, and its own
re-validation of 1c and 1d. The reasoning: an *absolute* activation floor is not
scale-invariant under conservation, and scale-invariance is treated as load-bearing
everywhere else in this codebase — 1c's relative proximity threshold, 1d-i's parameter-free
watershed. A relative floor is the same argument applied one layer down. `DEFAULT_FLOOR`
was chosen for an unconserved engine and that assumption no longer holds.

**(3) is refused** on the standing constant discipline: a free parameter adopted because it
makes a curve look right is exactly the failure mode that discipline exists to prevent.

**Evidence:** SPEC-0b2 §3 and §5. Reproduced on this machine 2026-07-25, Python 3.10.12:
fan sweep at sigma = 1.0 gives 0.2433743975 / 0.1770739779623022 / 0.11462263603326847 /
0.06721276407449465 / 0.03678388392602261 across F in {1,2,4,8,16} — strictly monotone,
target spread 0.0 at every level, F=1 unchanged. With sigma=None the sweep reproduces the
recorded flat 0.2433743975 to the last digit. Full suite unchanged at the neutral value:
20 suites, 1372 assertions, 0 failures.
**Cost:** brick 1 (the overlay, default-off) lands now and costs nothing downstream, because
the neutral value is byte-identical. Brick 2 (the floor) forces re-validation of 1c and 1d
and has not been started. **This principle is recorded before any downstream number is
computed**, which is the condition the decision was gated on.

## D-009 · 2026-07-25 · The 0b2 overlay lands default-off; flipping the default is a separate brick
**Decided by:** Cagan
**Context:** the overlay changes every float that reaches the competition. Landing it and
flipping it in one step would make the change's effect and the re-validation indistinguishable.
**Decision:** `normalization_sigma` ships with a neutral default of `None`, byte-identical to
the previous engine — the same gated-overlay pattern as `broadcast=False` and
`body_sensor=None`. Flipping the default is a separate brick with its own gate.
**Evidence:** full suite unchanged at neutral on this machine: 20 suites, 1372 assertions,
0 failures.
**Cost:** none now. The tester still owes N-1 through N-9 from SPEC-0b2 §6, and the default
flip owes a full re-validation of 1c and 1d.

## D-010 · 2026-07-25 · The determinism bar is raised to five CPython minor versions
**Decided by:** Cagan
**Supersedes:** raises the bar set in D-007
**Context:** D-007 established that a determinism claim is scoped to the environments it was
checked in, and set `interpreters_required` to 3.11/3.12/3.13 as the target. Python 3.11 and
3.13 were then installed and `tools/capture_run.py` swept five.
**Decision:** `interpreters_required` is raised to **3.10, 3.11, 3.12, 3.13, 3.14**. A capture
that does not cover all five leaves the determinism claim scoped down to whatever it did cover,
and `capture_run.py` refuses to write a capture when any two interpreters disagree.
**Evidence:** capture of 2026-07-25 22:30:23 +0300 on Darwin 24.5.0 arm64 swept python3.10
(3.10.17), python3.11 (3.11.10), python3.12 (3.12.4), python3.13 (3.13.2) and python3.14
(3.14.4). All five produced identical per-suite counts and identical overall verdicts:
20 suites, 1,372 assertions, 0 failures.
**Cost:** a longer capture, and a real obligation — dropping an interpreter now requires a
decision entry rather than silence. The upside is that the determinism claim in the paper
strengthens from "across randomized hash seeds" to "across randomized hash seeds and five
CPython minor versions", which is the axis BUG-0b1 proved was load-bearing.

## D-011 · 2026-07-25 · The 0b2 tester verdict is FAIL; three defects recorded, and two follow-on calls are OPEN for Cagan
**Decided by:** tester (the verdict) · architect-pm (the record) · **the two follow-on calls below
are NOT decided and belong to Cagan**
**Supersedes:** — (amends the "Tier 1 is not affected" sentence in BUG-0b1 §5, retracted in place)
**Context:** the tester wrote an independent adversarial suite against SPEC-0b2 §6 and adjudicated
the nine invariants. This entry records the verdict as fact, and separates cleanly what was decided
from what is still open.

**The verdict (recorded, not decided).** `tests/test_tester_0b2_adversarial.py`, 83 assertions, 0
failures, identical on CPython 3.10.17 / 3.11.15 / 3.12.4 / 3.13.14 / 3.14.4, hash seeds
{0, 1, 2, 3, 7, 42}. **Overall: FAIL — seven of nine invariants hold; N-2 and N-5 do not; N-7 holds
only for finite sigma.** The overlay's own core arithmetic is sound. Three defects:

- **DEFECT-A (N-2) — INHERITED FROM 0b, not caused and not fixed by 0b2.** Convergent accumulation
  (`activation[target] = activation.get(target, 0.0) + transmitted`, `src/nous_activation.py:287`)
  is a naive sequential float add whose term order comes from iterating a set of uuid4 ids
  (`src/nous_store.py:444`). At library defaults, on a 5-node graph built by `traverse()` alone,
  **48 fresh processes produced two distinct results** (0.10145973529004966 / 0.10145973529004967).
  Holds bit-exactly at in-degree <= 2; breaks at in-degree >= 3. Reproduces with the overlay off.
- **DEFECT-B (N-5) — INTRODUCED BY 0b2.** The overlay reads each road twice per expansion, and lazy
  decay is applied at `clock.now()` on each read, so on a moving clock — the library default — a
  lone out-road has `competing = 1.7265900376095544e-09` instead of exactly 0 and is attenuated by
  0.99999999827341 instead of exactly 1.0. This contradicts SPEC-0b2 section 2 row 3 and N-5 as
  written. Invisible to every existing test, which all use `Clock(simulated=True)`.
- **DEFECT-C (N-7) — INTRODUCED BY 0b2.** `normalization_sigma` is unvalidated: `float('inf')` — the
  exact value section 2 calls the one that "analytically recovers the current engine" — computes
  `inf/inf = NaN`, and NaN passes the floor guard silently because every comparison with NaN is
  False. `sigma <= 0` misbehaves too.

**Two methodological findings, worth more than the defects.** (i) Pinning `PYTHONHASHSEED` cannot
establish determinism for this substrate: uuid4 ids differ per process, so a fixed seed does not fix
set-iteration order, and DEFECT-A varies at a fixed seed. (ii) Every pre-existing determinism probe
in `tests/` compares `round(x, 9)`, which structurally cannot see a 1-ULP difference — and 1 ULP is
exactly what BUG-0b1 was. The new suite compares bit patterns throughout.

**Decision taken here (architect-pm, documentation only):** the verdict, the three defects and the
two methodological findings are recorded in `docs/specs/SPEC-0b2-conserved-activation.md` section 6
(rewritten as a verification record), in `docs/BUG-0b1-coalition-strength-determinism.md` section 8,
and in the roadmap's Phase 0 blocks. SPEC-0b2 section 2's property table is corrected in place: two
of its five claimed properties are false as written. `0b2` stays `BUILT-UNVALIDATED` with its
**mechanism bar open** — it is explicitly **not** listed as tester-verified. No status label is
changed on any brick by this entry.

**OPEN CALL 1 — does `0b` keep its `PROVEN` label while DEFECT-A stands?** Phase 0's own "done
means" is determinism across process runs; DEFECT-A falsifies it at library defaults on in-degree
>= 3 graphs.
- **(A) Demote `0b` to `BUILT-UNVALIDATED` until DEFECT-A is fixed and re-verified.** Most honest
  reading of the evidence and of rule 3. Cost: the paper's Phase 0 claim narrows while the fix is in
  flight, and "Phase 0 is PROVEN" appears in the README, the report, the outreach material and the
  paper.
- **(B) Keep `PROVEN` but scope it explicitly** — "deterministic on graphs where no node has three
  or more convergent contributions" — and carry the scope everywhere the claim is made. Cost: a
  scoped claim nobody can state in one sentence tends to get quoted unscoped; the project has
  already been bitten by exactly that with the interpreter axis.
- **(C) Fix DEFECT-A first (`math.fsum` over per-target contributions, or an accumulation keyed by
  an intrinsic integer), then re-verify and keep `PROVEN` unbroken.** Cost: it is a change to the
  `PROVEN` engine, so it re-opens 0b's own verification and touches every downstream float; the
  tester's asserted-negative goes red by design and must be rewritten as a positive assertion.
- **architect-pm recommendation: (C), with (B) as the interim wording until the fix lands.** The fix
  is small and its shape is already established by BUG-0b1 (`math.fsum`, exactly rounded, therefore
  order-independent), and a foundation defect fixed is worth more than a foundation defect
  documented. But it is a Phase 0 change with a real re-validation cost, so it is not an agent's
  call.

**OPEN CALL 2 — how is DEFECT-B fixed, given it is 0b2's own?**
- **(A) Read each road once per expansion** (compute `out_total` from the same road views the
  transmission loop uses). Removes the defect at its cause, and removes the duplicated road read
  that section 8 item 4 already flagged as a cost. Cost: a real change to the expansion loop's
  shape; N-1 must be re-verified because the read pattern changes.
- **(B) Freeze the clock for the duration of one expansion.** Fixes DEFECT-B and any sibling
  double-read defect at once. Cost: a semantic change to lazy decay that reaches far beyond 0b2 and
  would need its own spec.
- **(C) Weaken the spec to say the factor is 1.0 "up to elapsed-time residue".** Cheapest, and
  wrong: it is the failure mode of changing the claim to fit the result, and BUG-0b1 established
  that ULP-scale residue is not harmless here.
- **architect-pm recommendation: (A).** It is local, it is the cause, and it makes section 8 item 4
  a benefit rather than a caveat. **(C) is refused** on the standing discipline.

**Evidence:** the tester's suite and its end-of-run verdict banner, reproduced verbatim in
`docs/TEST_OUTPUT.txt`; the reproductions quoted above; SPEC-0b2 section 6.
**Cost:** none to the canonical counts — the suite is registered and the canonical run is 21 suites
/ 1,455 assertions / 0 failures. The real cost is that **the mechanism bar for 0b2 is open, not
cleared**, and that the second brick of 0b2 (the activation floor, D-008) and the default flip
(D-009) are both blocked behind these two calls. The default flip additionally now needs the
parameter plumbed through `build_activation_field()` and `think()`, which widens its re-validation
surface from 1c/1d to **1a, 1b, 1c and 1d**.

## D-012 · 2026-07-25 · Phase 0 loses PROVEN; the 0b2 defects are routed; the paper is held
**Decided by:** Cagan
**Supersedes:** resolves the two calls left open in D-011
**Context:** the 0b2 tester pass returned FAIL with three defects, one of which (DEFECT-A)
falsifies Phase 0's own done-means at library defaults.

### Call 1 — does 0b keep PROVEN? **No. Phase 0 loses PROVEN. Both 0a and 0b drop to
`BUILT-UNVALIDATED`.**

Phase 0's done-means is a single joint claim: *"determinism (identical output across separate
process runs under randomized hash seeds), integrity (graph indices stay mutually consistent
through every mutation), purity (reads never mutate state)."* DEFECT-A shows identical output
does **not** hold across separate process runs, at library defaults, on a five-node graph built
with nothing but `traverse()`. That is not an edge case; it is the most ordinary possible input.
The claim as written is false, so the label comes off. Rule 1 does not have an exception for
labels we are attached to.

**0a is demoted too, and that is deliberate.** The defect site is in `nous_activation`, but the
enabling condition is `nous_store`'s `_out` being an unordered set of uuid4 ids, exposed through
`roads_from()`. Keeping 0a at PROVEN would rest on the fact that its own suite happened not to
check the thing that broke — which is precisely the "passes on a friendly input" failure this
project exists to prevent. Integrity and purity are unaffected and remain verified; only the
determinism leg failed, and the ledger note says so.

**This is recoverable and the route back is specified.** Fix, re-verify, and Phase 0 returns to
PROVEN *stronger* than it was, because the probes will by then be able to see the failure class
that hid here.

### Call 2 — how is DEFECT-B fixed? **The tester's read is adopted.**

Read each road **once per expansion**: materialise the `(road_id, road)` pairs for the expanding
node a single time, compute `out_total` from that list, and iterate that same list. The bug is
that two `get_road` calls apply lazy decay at two different `clock.now()` instants, so `out_total`
and `road.strength` come from different moments and `competing` becomes an elapsed-time residue
rather than exactly 0. Reading once makes the arithmetic internally consistent by construction,
and it also removes the duplicated-read cost SPEC-0b2 §8 item 4 already flagged — the fix is
strictly better on both axes.

**DEFECT-C is fixed at the same time.** `normalization_sigma` is validated at the boundary:
reject non-finite and non-positive values with a clear error. SPEC-0b2 §2's prose is corrected —
"σ → ∞ recovers the current engine" is true analytically in the limit and catastrophic at the
literal value `float('inf')`, which yields NaN and passes the floor guard silently because every
NaN comparison is False. **The neutral value is `None`, not infinity, and the spec must say so.**
The NaN-passes-the-floor hazard is more general than σ and gets its own guard.

### DEFECT-A's fix — architect-pm to spec, this is the recommended shape

**Fix at the store, not at each consumer.** Make `_out` and `_in` insertion-ordered (an
insertion-ordered mapping used as an ordered set) so `roads_from()` yields in road-creation order
deterministically and at no cost. Insertion order is creation order is program order, which is
identical across processes.

This kills the whole class at its source rather than patching one accumulation site, and it uses
the stable ordering integer the project already relies on everywhere else. Ordering alone is
*sufficient*: a fixed traversal order gives a fixed sum. `math.fsum` at the accumulator is
optional hardening against a future refactor changing iteration order, and it costs a restructure
(contributions collected per target, summed at each layer boundary) because the running total is
read at layer boundaries. Architect-pm decides whether that hardening is worth it.

This is a **Tier 1 change** and it forces re-validation of everything above. That cost is real,
unavoidable, and correct.

### The methodological findings, which matter more than the defects

1. **Every existing determinism probe compares `round(x, 9)`, which structurally cannot see a
   1-ULP difference — and 1 ULP is exactly what BUG-0b1 was.** Every determinism probe in the
   repository must compare full bit patterns. The probes that "caught" BUG-0b1 did not catch it by
   seeing the number; they caught it because the ULP happened to flip a categorical winner. Any
   ULP difference that does not flip an outcome has been invisible this whole time.

2. **Seed-pinning cannot establish determinism for this substrate.** Iteration order derives from
   uuid4 values, which differ per process regardless of `PYTHONHASHSEED`. DEFECT-A varies at a
   *fixed* seed. So the axis the project has been sweeping does not control the source of the
   nondeterminism. **Determinism must be established by REMOVING order dependence, not by sweeping
   an axis that does not control it.** The five-interpreter sweep (D-010) stays valuable, but it
   is not the guarantee it was being read as.

Finding 2 is a correction to the paper's methodology section, and it is a **strengthening**: the
paper is about a discipline that catches overclaiming, and the discipline has now falsified the
paper's own headline Tier-1 claim, by its own gates, at a coverage axis the paper itself named.
Reported honestly, that is a far better paper than one in which everything passed.

### Call 3 — routing outside both lanes

- **`docs/paper/paper.tex` and `docs/paper/ieee/paper_ieee.tex`: HELD. The paper must not be
  submitted.** Its Tier-1 determinism claim is presently false. Fixing the counts is clerical and
  can happen at any time; the substantive revisions — the determinism claim, its scope, and the
  two methodological findings above — are a paper brick with its own gate. `ledger_check` C2 stays
  red on the paper until that lands, and that red is correct signal, not noise: it says the paper
  is stale and must not ship. **Do not enable the pre-commit hook until the paper brick lands.**
- **`docs/report/nous_report.tex`: QUARANTINED, permanently.** It is the source of the artifact
  published under DOI 10.5281/zenodo.20474613 on 2026-05-31. Its 130/56/5 figures are correct for
  what was published, and a published record is immutable by definition. It is never "corrected";
  it is cited as the version it is. Added to `count_quarantine_paths` with that reason recorded.
- **`SUMMARY.docx`** is regenerated from the corrected `SUMMARY.md` via
  `docs/outreach/build_summary_docx.py`, after the paper brick, not before.
- **`ledger_check` now scans `.tex`.** It did not until today, which is why the paper drifted
  through two total changes unnoticed — the one document where a stale count actually gets
  published was the one document the checker never read. That gap was mine.

**Cost:** Phase 0 is unlabelled until the fix re-verifies. The paper is frozen. Every determinism
probe in `tests/` needs rewriting to compare bit patterns. This is the most expensive entry in
this log, and every item in it was bought by one tester pass that was allowed to say FAIL.

## D-013 · 2026-07-26 · `math.fsum` joins the ordering fix in 0c; both land together
**Decided by:** Cagan
**Supersedes:** resolves SPEC-0c §2.3, the one call D-012 delegated to architect-pm
**Context:** D-012 fixed the shape of DEFECT-A's fix — make `_out`/`_in` insertion-ordered so
`roads_from()` yields creation order — and left one question open: whether `math.fsum` at the
convergence accumulator is worth its restructure on top, or whether ordering alone is enough.

**Decision: both. Ordering *and* `math.fsum`, in 0c.** Ordering alone gives *determinism* (the
same program in a different process gives the same bits). Only `fsum` gives *order-independence*
(a **different** iteration order gives the same bits). The second is the property that closes the
class; the first only pins it.

**Ground 1, decisive.** Under ordering alone, two of the six asserted-negatives in
`tests/test_tester_0b2_adversarial.py` keep passing — **truthfully**, because the engine would
still be order-dependent, merely pinned. **A fix after which our own adversarial suite can still
honestly assert the pathology is a fix at the symptom, not at the cause.**

**Ground 2 — this repository has already lost this exact bet, on this exact hazard.**
Ordering-alone's safety rests on a recorded condition being honoured later ("do not reorder
iteration without adding `fsum` first"). `experiments/harness.py:290` recorded this very hazard in
writing, worked around it locally, and the substrate carried `PROVEN` for a month regardless while
the engine went unfixed. A control that depends on a future reader honouring a note has been tried
here and failed. Do not buy it twice.

**Ground 3 — the reordering change is already planned, in writing.** `nous_activation.py`'s design
note contemplates a future locality prune that expands "only the top-K most active nodes" within a
hop layer. Top-K within a layer reorders iteration, which is precisely the condition ground 2 says
will not be honoured.

**Ground 4 — float correctness here is currently a function of which interpreter runs it, and this
is now the confirmed mechanism behind BUG-0b1's version-dependence.** BUG-0b1's fix was exactly
`sum(members.values())` → `math.fsum(members.values())`. CPython 3.12 changed the builtin `sum()`
to Neumaier compensated summation for floats. Reproduced on this machine over
`[1.0, 1e-16, 1e-16, 1e-16]`: `sum() == fsum()` is **False** on 3.10.17 and 3.11.15, **True** on
3.12.4, 3.13.14 and 3.14.4. So the pre-0b1 code was **accidentally correct on 3.12+ and naive on
3.11** — which is exactly why BUG-0b1 was "invisible on 3.12 and flipped the winner 8 times in 30
on 3.11", a difference that bug report recorded as unexplained. It is explained now. `math.fsum`
is exactly rounded on every version, making the semantics uniform by construction rather than
accidentally-correct on new interpreters.

**One objection was withdrawn rather than carried.** The draft spec claimed ordering-alone
preserves the tester's git-recovered N-1 oracle. That is false where it matters: ordering changes
the accumulation *sequence* at in-degree >= 3, and on the unordered store the pre-change engine had
no single answer to reproduce. The git oracle is well-defined only on **in-degree <= 2**. It breaks
under both options and was never a differentiator; SPEC-0c §2.3 now states the boundary instead.

**A trap the spec now names.** When the tester re-bases N-1 onto its independent reference
implementation, that reference must mirror the **intended** semantics — ordered *and* `fsum` — not
the semantics it was originally written against. A reference still modelling the old naive
accumulator agrees with a broken engine and disagrees with a correct one: it stops being an oracle
and becomes a second copy of the bug. Re-basing is part of the fix.

**For the paper's methodology section, as the generalisation:** *"A coverage axis is only evidence
for the property it can perturb."* This project swept `PYTHONHASHSEED` for a month against a
nondeterminism that uuid4 caused, and no seed could have found it. Corollary: prefer removing a
dependence to sampling it.

**Cost:** the accumulator restructures — it is a running total read at layer boundaries, so `fsum`
requires per-target contribution lists reduced at each boundary. Contained, but a real change to
the hot loop's data structure. The re-validation surface is unchanged from D-012, because the
ordering fix already moved every convergent float; `fsum` in the same brick adds no second
re-validation round.

**Registered:** `0c` is now in the ledger and the roadmap as `DESIGNED`. **SPEC-0c §2.5 is a NEW
open call** raised while verifying ground 4: three naive `sum()` calls over floats survive in
`src/` — `nous_workspace.py:428` (the pruned winner's strength, on the 1d-i winner path, which
BUG-0b1's "both sites" missed — there were three), `nous_workspace.py:235`, and
`nous_store.py:161` (`Road.valence`, feeding a categorical closure decision). Recommendation is to
fold all three into 0c; O-16 (cross-interpreter bit-identity) is unachievable while any remain.

## D-014 · 2026-07-26 · All three naive float sums convert; BUG-0b1's report is corrected; the -0.0 exception is accepted
**Decided by:** Cagan
**Supersedes:** resolves SPEC-0c §2.5, §2.6 and the `experiments/harness.py` routing question
**Context:** verifying D-013's ground 4 raised the question of where else this project sums floats
with the builtin. Three sites survived in `src/`. One of them turned out not to be a hardening
opportunity but a **live instance of the defect BUG-0b1 was reported to have closed**.

### §2.5 — all three sites convert to `math.fsum`. This is not hardening.

`src/nous_workspace.py:426` builds the **pruned winner** with `strength=sum(pruned_members.values())`.
Reproduced on the **post-0c working tree** — store already ordered, activation accumulator already
using `fsum` — at a **fixed** `PYTHONHASHSEED=0`, 30 fresh processes:

```
python3.10   2 distinct strengths   6x 4.14276559350793   24x 4.142765593507931
python3.14   1 distinct strength   30x 4.14276559350793
winner membership: 1 distinct on both — identity is stable
```

Three things this establishes. **(i) The store-ordering fix cannot reach it:** `Coalition.members`
inherits order from `by_basin[src]`, a `Dict[str, Set[str]]` of uuid4 NodeIDs built in
`nous_coalitions.py:297` — a set some *other* module constructs. Fixing a class at one owner does
not fix it at another owner. **(ii) The 3.10-vs-3.14 split is the Neumaier fingerprint** from D-013
ground 4: invisible on the newer interpreter, reproducible on the older one — BUG-0b1's exact
signature, recurring at the site BUG-0b1 missed. **(iii) Winner identity is stable today, which is
exactly how BUG-0b1 hid** until a graph arrived where it flipped one, 8 times in 30.
`Coalition.strength` is what `_competition_key` compares, so this is the competition path.

Sites 1 and 2 convert on D-013 ground 4's reasoning rather than on a reproduction:
`nous_workspace.py:235` is `total_strength_after()`, which **by its own docstring** is "the bounded
aggregate the no-divergence test watches converge across cycles" — a version-dependent number
feeding an assertion; `nous_store.py:168` is `Road.valence`, feeding a categorical closure decision
against −0.75 / −0.30.

### Two consequences recorded, both larger than the fix

**(a) BUG-0b1's report is wrong and is corrected in place, dated.** It states the fix was
"`src/nous_coalitions.py`, two sites." There are **three** `Coalition(` construction sites in
`src/`; the third, in `nous_workspace.py`, was never converted. The bug was reported as closed while
an instance of it remained on the same path. Corrected in `docs/BUG-0b1-*.md` §2 (an inline
correction block) and §9 (a new postscript that also explains, for the first time, why the bug was
invisible on 3.12 — the Neumaier change). The diagnosis, mechanism and applied fix were all correct;
what was false was the **claim of completeness**. **Whether `0b1` keeps `PROVEN` given that is an
OPEN CALL for Cagan** — the ledger note records the contest and nothing is re-labelled here.

**(b) SPEC-0c §1's falsifier did not cover this, and that is a spec defect, not just a code defect.**
The original reproduction exercises only the activation accumulator, so the brick whose entire
purpose is closing the order-dependence class would have shipped with a live instance of that class
still in it. **Had §1 covered the competition path, 0c would have caught this itself.** §1 now
carries a second reproduction case, through `think()`, and **O-4b** asserts it — one bit pattern for
`r.thought.strength` across fresh processes on **every** interpreter, with winner membership
asserted alongside so a future flip is attributable. The lesson is §5.3's, one level up: a probe is
only evidence for the path it exercises.

### §2.6 — the `-0.0` exception is accepted and asserted, with its phrasing fixed

`math.fsum([-0.0])` returns `+0.0`, so `energy=-0.0` is the one input at which neutral byte-identity
acquires a documented exception. Accepted: no special-casing of the reducer, and **no boundary
validation for `energy`** — no caller passes a negative and that would be scope creep into §4, which
exists for σ. **But the assertion must state OUR semantics** — *"activation energy has no signed
zero: −0.0 normalises to +0.0, by design"* — and **not** *"we match `math.fsum`"*. The second
phrasing turns a CPython implementation detail into our specification, and would break the test if
the stdlib moved, for a reason unrelated to intent. A test should fail when the intent is violated.

### Routing — `experiments/harness.py:290` splits into comment and code

The **comment** documents the very hazard 0c fixes and named the **wrong cause**: it attributed the
nondeterminism to `PYTHONHASHSEED`, when it varies at a *fixed* seed because uuid4 values differ per
process. That misattribution is why a hash-seed axis was swept for a month against a defect no seed
could perturb, and why the local workaround was never promoted into the engine — the hazard looked
like it belonged to an environment variable rather than to the substrate. Corrected **in the
architect-pm lane as part of 0c**, in place, showing the wrong text and the right one. The **code** —
the local sort-before-summing workaround — is **untouched and stays validator territory**; it
becomes unnecessary after 0c but removing experiment code is not this brick's business.

**Cost:** three one-line conversions inside a re-validation 0c already performs, plus one new
invariant (O-4b) and one new reproduction case. O-15 and O-16 become unconditional. The
`nous_workspace.py:426` conversion changes `Coalition.strength` values by ULPs on the competition
path, so 1b, 1d-i and 1d-ii re-verification — already required by §2.4 — now has a specific place to
look.

## D-015 · 2026-07-26 · The 0c tester verdict is FAIL on O-12; three findings recorded, two calls open
**Decided by:** tester (the verdict) · architect-pm (the record) · **the two calls below are NOT
decided and belong to Cagan**
**Context:** the tester adversarially verified brick 0c against SPEC-0c §6 (O-1 … O-17, incl. O-4b),
re-based the N-1 oracle, and re-adjudicated the 0b2 suite. This entry records the verdict as fact
and separates cleanly what was decided from what is open.

**The verdict (recorded, not decided). FAIL.** Seventeen of the eighteen enumerated properties hold
under adversarial and loop-closed conditions. **O-12 does not hold as written.** Coverage swept:
five interpreters (3.10.17 / 3.11.15 / 3.12.4 / 3.13.14 / 3.14.4) × hash seeds {0,1,2,3,7,42}.
`test_tester_0b2_adversarial.py` rewritten: 104 passed. `test_tester_0c_adversarial.py` new: 123
passed. O-4 one bit pattern over 60 processes; O-4b one strength, one membership, one full ranking;
O-16 one SHA-256 across all five interpreters; O-17 **104 with `.git` and 104 without** — the
environment-dependence is closed.

**What 0c did achieve, and it is most of the brick.** The determinism leg of Phase 0's done-means is
restored and verified **structurally rather than sampled** (O-1…O-6, O-16), with integrity and
purity re-verified (O-3). §1 case 1 and case 2 each yield one bit pattern across processes and
interpreters. On that evidence `0a` and `0b` are **eligible** to return to `PROVEN` — the tester
said so explicitly and correctly declined to re-label anything it had just certified. No label is
changed by this entry.

**OPEN CALL 1 — how is O-12 closed?** See SPEC-0c §4.1 for the failing input and the options.
`spread_activation(s, isolated_node, energy=float('nan')).activation[A]` returns `nan`: the engine
seeds `contributions = {seed: [energy]}` and §4's guard is on `transmitted`, so a seed that never
transmits bypasses it. **Verified pre-existing** (the committed pre-0c engine returns `nan` on the
same input) and **unreachable from any internal caller** (`build_activation_field`'s energies come
from `perceive()`/`cluster_sources()` and are always finite). Options: (A) validate `energy` for
finiteness at the boundary σ is validated; (B) narrow O-12's wording to "cannot pass the floor
guard" and assert the seed route as an accepted limitation; (C) validate both energy and the seed
contribution. **architect-pm recommendation: (A)** — §4 already judged the non-finite hazard "more
general than σ", and D-014's refusal of `energy` validation was argued about *negative* energy, not
*non-finite* energy. Whichever is chosen, **O-12 cannot stand as written**, because it currently
asserts something false.

**OPEN CALL 2 — the fourth order-dependent aggregate.** SPEC-0c §2.7. `src/nous_field.py:131` and
`:124` accumulate with `+=` in source order — DEFECT-A's exact shape at a site 0c never touched
(§2.5 enumerated builtin `sum()` sites; these are `+=`). Reproduced: `field.total[m1]` takes two
distinct bit patterns over 3! source orders, and it reaches `Coalition.strength`. **Cross-process
determinism is unaffected** — source order is program order, so the site is order-PINNED — and every
O-4/O-4b/O-5/O-16 result stands. But "pinned, not independent" is exactly what D-013 ground 1
refused for the activation accumulator. **Recommendation: a follow-on brick**, not a third widening
of 0c. **This is the third time this project has met this shape** (BUG-0b1, §2.5's site, now this).

**Three corrections the tester made to this project's own documents, all folded into SPEC-0c.**
(i) §2.3/O-8's "in-degree ≤ 2" oracle boundary was **off by one**: the seed's own energy is a
contribution, so a seed with in-degree 2 on a cycle accumulates three terms. The boundary is stated
on *contributions*, not in-degree. (ii) §8's stale-oracle signature — which this log endorsed —
was **wrong in three details**: `flow` does differ, 11 mismatches occur below the 3-contribution
line, and the byte-identical count is 15,606 not 14,397. The conclusion survives on a stronger
criterion the tester supplied: every deviation is downstream propagation, proved because all
out-roads of a moved source shift by **one common ratio** (25/25 and 35/35 groups, max relative move
4.44e-16). (iii) O-6 claimed more invariance than holds — values, `hops` and the breakthrough set
are invariant; `activation`'s key order necessarily moves. Also: §5.1 under-counted tester-owned
`round()` sites, 9 not 8.

**One further behaviour change, documented not discovered** (SPEC-0c §2.8): `math.fsum` raises
`OverflowError` where the pre-0c engine returned `inf`, at `energy=1e308` with 12-way convergence.
Outside N-1's parameter sweep, which is why nothing saw it.

**State of the tree.** Nothing is committed — correctly, since the commit sequence was conditioned
on PASS. `tests/test_tester_0c_adversarial.py` is **not registered in `run_tests.py`**, so its 123
assertions are outside the canonical capture; registering it is harness work and the tester was
blocked from it by hook. The tester's `capture_run`/`ledger_sync` run has been **reverted by
architect-pm**: it rewrote the ledger to 21 suites / 1,545 assertions from a run that *omitted the
new suite*, and a ledger recording an incomplete capture is precisely the staleness the ledger
exists to prevent. `tools/ledger.json` and `docs/TEST_OUTPUT.txt` are back at their committed
values, `ledger_check` is clean apart from the 14 held-paper C2 findings, and **the capture is
deferred until O-12 is resolved and the suite registered.**

## D-015 · 2026-07-25 · O-12 closes by validating energy; the fourth aggregate becomes brick 0d
**Decided by:** Cagan
**Supersedes:** narrows D-014's scope statement (which refused *negative*-energy validation —
a different question from finiteness)

### Call 1 — O-12 closes by option (A): validate `energy` for finiteness at the boundary.

Adopted, and for a stronger reason than consistency with σ. The isolated-node case is not the
risk; it is the *visible instance* of a general fact: `contributions = {seed: [energy]}` means
**the seed's own activation is unguarded on every graph, connected or not.** §4's guard is on
`transmitted`, which only ever sees downstream values.

A NaN at the seed therefore lands in the **returned** activation map. That map is consumed by
`nous_field`, accumulated into basins, and reaches `Coalition.strength` and thence
`_competition_key` — where every NaN comparison is False and the ordering silently degrades.
That is DEFECT-C's failure mode one input earlier, and §4 already judged this hazard "more
general than σ". Validating σ for finiteness while leaving `energy` unvalidated is the same
guard applied to one of two adjacent doors.

Option (B) is rejected on its own description: it weakens an invariant to fit an
implementation. That is the one move this project cannot make.

**Scope, kept narrow:** reject non-finite `energy` (NaN, ±inf) with the same error shape as σ.
**Negative energy is untouched** — D-014's ruling on −0.0 stands, and the two questions stay
separate so the record stays legible.

**A consequence that must be written into the spec, or someone deletes the guard later.** Once
both `energy` and σ are finiteness-validated, and given every multiplier is ≤ 1, the internal
`transmitted` NaN guard becomes **unreachable from the public API**. It stays as a backstop.
Its test must inject below the boundary, and §4 must say so explicitly — otherwise a future
reader correctly identifies it as dead code and removes the belt while keeping the braces.

### Call 2 — the fourth aggregate is brick 0d, not a third widening of 0c. Agreed.

The distinction is in kind, not degree, and it is the one that matters:

- §2.5's site 3 (`nous_workspace.py:428`) **reproduced nondeterminism across processes**. It
  falsified 0c's core claim, so it was mandatory scope.
- `nous_field.py:131` is **order-pinned** — source order is program order — so it falsifies
  nothing 0c claims. What is missing there is the weaker property, order-*independence*.

D-013 ground 1 does apply to it, but as a *new instance*, not as a defect in 0c's delivery. A
brick that keeps growing never closes, and 0c is 17/18 done with an uncommitted implementation.

**Two conditions.**

1. **0d is registered now** — ledger and roadmap, status `DESIGNED`, dated — not left as a
   note. The precedent is this project's own: `experiments/harness.py:290` documented this
   exact hazard in writing and `PROVEN` shipped anyway. A recorded intention has already
   failed to protect anything once here.
2. **0c's claim is narrowed to what it delivers.** 0c may state: determinism restored at the
   enumerated sites, order-independence achieved at those sites, one further site identified
   and deferred, order-pinned and therefore not a determinism defect. **0c may not state that
   the order-dependent-aggregate class is closed.**

### 0d's deliverable is a DETECTOR, not a fifth patch.

"This is the third time this project has met this shape" is the most important sentence in the
0c verdict. Three encounters — `nous_coalitions` (BUG-0b1), `nous_activation` +
`nous_workspace:428` + two others (§2.5), now `nous_field:131` — and every one was found by a
person looking, never by a sweep.

The evidence that symptom-hunting cannot close this: **`nous_field.py:124` (`merged_flow`) has
the identical shape and did NOT reproduce variation** on a four-source, four-way-convergence
probe. Shape present, symptom absent on that input. That is the friendly-input trap in its
purest form, and no amount of further reproduction hunting answers it.

So 0d builds a structural test that enumerates every float accumulation in `src/` and requires
each to be either `math.fsum` or explicitly registered in the ledger with a reason — failing
when a new naive accumulation appears. **Then** it fixes whatever the detector finds, which
will include `:131`, probably `:124`, and possibly sites nobody has looked at. That converts
the third encounter into the last one.

### Bookkeeping — the revert was right, and it exposed a hole that was mine.

Reverting the ledger to its committed values was correct: a ledger recording a capture that
omitted a suite present on disk is precisely the staleness the ledger exists to prevent.

But `capture_run` accepted that capture. It had no notion of whether the runner ran everything,
so the count could silently under-report by forgetting to register a suite — and the capture
would be internally consistent and wrong. **`ledger_check` now has C5, runner-completeness:**
every `test_*.py` on disk must be registered in `run_tests.py` or listed in the ledger's new
`unregistered_suites` with a reason. It also catches phantom registrations and stale excuses.
Verified against this repo: it flags `test_tester_0c_adversarial.py`. The four deliberately
excluded data-dependent suites are now recorded with their reasons rather than assumed.

**The hook-block was correct and the workflow was incomplete.** Keeping `run_tests.py` out of
the tester's hands stops a tester inflating the canonical count with its own suite — that
safeguard stays. What was missing is an explicit registration step, in another lane, after a
tester pass. That belongs in `psyche-brick` phase 5.

### The labels

0a and 0b are **eligible** to return to `PROVEN`, and neither the tester nor architect-pm was
right to re-label. That call is mine and it is **pending**: the labels return when O-12 closes,
the 0c suite is registered, and a complete capture across all five interpreters is taken. Not
before, and not on the strength of 17 of 18.

## D-016 · 2026-07-26 · The 0c tester verdict is PASS; Phase 0 is eligible for re-labelling
**Decided by:** tester (the verdict) · architect-pm (the record and the prose reconciliation)
**The label restoration below is NOT decided and belongs to Cagan.**

**The verdict (recorded, not decided). PASS.** All eighteen enumerated properties — O-1 … O-17
including O-4b — hold under adversarial and loop-closed conditions. O-12, the single failure of the
previous pass, is closed by D-015's `energy` finiteness validation and re-verified against the
invariant rather than against the patch: **10 seed shapes × 7 non-finite energies × 8 parameter
sets = 560 calls, none returned a result.** The energies include a *payload* NaN
(`0x7ff8000000000001`), so the check cannot be passing by comparing against one canonical NaN.
D-014 is intact and directly asserted: negative finite energy is accepted, `-0.0` still normalises
to `+0.0`, and `-1e300` is accepted where `-inf` is refused — so the discriminator is finiteness,
not sign.

**Canonical run: 22 suites, 1,727 assertions, 0 failures**, identical per-suite counts on CPython
3.10.17 / 3.11.15 / 3.12.4 / 3.13.14 / 3.14.4. Verified independently by architect-pm on 3.10.
§1 case 1 (`0d7ceee443f9b93f`) and case 2 (`3e71cc2431921040`) are unmoved.

**Three things the tester added that were not asked for, and each is worth keeping.**
(i) The backstop guard's presence is now **machine-checked by AST** — a raising `If` on
`math.isfinite(transmitted)` inside `spread_activation` — so SPEC-0c §4's "must not be removed as
dead code" is *enforced* rather than requested. (ii) A **loop-closed third route** into the guard
through `think(body_sensor=…)`: a primed replay sensor yields NaN friction, `modulated_decay_per_hop`
returns NaN because neither clamp fires on NaN, and the guard catches it three modules downstream.
(iii) A **bound** on FINDING 1's scope: `nous_activation`'s `flow[rid] = flow.get(rid, 0.0) + …` has
the same shape but is *structurally single-term* — over 574 spreads on 60 hostile graphs no road was
read twice per spread — so the field-merge finding must not be read as wider than it is.

**Prose reconciliation (architect-pm).** The totals moved 21/1,455 → 22/1,727, which staled 39
figures outside `docs/paper/`. All are reconciled: `README.md`, `docs/REPORT.md` (its per-suite
table rebuilt from the ledger rather than patched), `docs/nous_roadmap.md`, `docs/outreach/*`.
**`ledger_check` C1/C3/C4/C5 are green and C2 now reports 16 findings, every one of them in
`docs/paper/*.tex`** — the HELD paper (D-012), where red is correct signal.

**SPEC-0b2 §6 was deliberately NOT rewritten.** Its "83 assertions" is the figure at the FAIL pass;
the suite now reports 104 after its 0c re-adjudication. The number is preserved under an explicit
`ledger:allow-count` pragma with its reason, and a supersession note records what changed. **A
verification record edited after the fact to reflect a later state is not a record.**

**A process conflict the tester surfaced rather than resolved, and it was right to.** CONTRIBUTING.md
requires `ledger_check` to exit 0 before any commit; the close-out sequence handed to it required
reporting the C2 staleness without fixing it, since prose is architect-pm's lane. So commit
`1b5780a` was made at exit 1. That is now resolved by this reconciliation, and the sequencing gap
is real: **a tester close-out that moves the totals cannot satisfy the pre-commit gate on its own.**
Either the gate tolerates C2-only findings during a lane hand-off, or the reconciliation must
precede the commit. Recorded for Cagan; not resolved here.

**OPEN CALL — restore Phase 0's labels?** All three conditions Cagan set are now met: O-12 closed in
code, the 0c suite registered in `run_tests.py` (C5 green), and a complete five-interpreter capture
taken. On the tester's evidence `0a` and `0b` are **ELIGIBLE** to return to `PROVEN`: ordering
asserted against `creation_seq` through mutation batteries, purity and integrity intact, one bit
pattern across fresh processes on both reproduction cases, order-perturbation invariance, and
cross-interpreter bit-identity. **`0c`'s own status is also stale at `DESIGNED`** — it is built and
tester-verified. Neither is changed here. Restoring a label on an agent's initiative is the
circularity this project exists to avoid, and the three prior status changes in this log were all
Cagan's.

**Also open, all minor, all recorded rather than actioned:** whether `0b1` keeps `PROVEN` given its
completeness claim was false (D-014); whether `decay_per_hop` should be finiteness-validated as a
third boundary (SPEC-0c §4, low urgency — the guard catches it loudly, and silence was the failure
mode that mattered); and a stray untracked `_c5.tar.gz` at the repository root, which is not an
agent's to delete.

## D-016 · 2026-07-25 · Phase 0 returns to PROVEN; floor joins the validated boundaries; the tester stops running capture_run
**Decided by:** Cagan
**Supersedes:** restores what D-012 removed; corrects D-015's triage of the third boundary

### Phase 0 returns to PROVEN. 0a, 0b and 0c are all PROVEN.

All three conditions I set are met: O-12 closed in code, the 0c suite registered (C5 green),
and a complete five-interpreter capture taken. Independently confirmed: Phase 0's own modules
carry no naive float aggregation. What remains in `nous_store` is integer counters and the
clock's sequential `_t += dt`; `valence` is converted; `nous_activation`'s accumulator is
list-plus-fsum.

**This PROVEN is better than the one it replaces.** The old label rested on sweeping
`PYTHONHASHSEED`, an axis that could not perturb the property it was cited for. The new one
rests on there being no order dependence left to perturb, confirmed across five CPython minor
versions. The difference is the whole of what 0b1, 0c and D-012 bought.

**`nous_activation`'s flow accumulator stays naive and is PROVED structurally single-term**
rather than converted. That is the correct treatment and the better one: a bound is stronger
than a conversion, because it says why the site cannot break rather than making it not matter.
It goes into 0d's registry as the model entry.

### 0b1 keeps PROVEN, and the reason matters.

Its completeness claim was false — a third `Coalition` construction site was missed. Its
*property* claim was true and remains true: the tie-break is reachable at the sites it fixed.
**Labels track properties, not report quality.** The enumeration error is corrected in place
and dated, and 0d's detector is the systemic answer to the class of mistake. Demoting a brick
whose verified property is intact, in order to punish a documentation omission, would inflate
the appearance of rigour rather than serve it — and this project's labels have to mean one
thing only.

### The third boundary is `floor`, not `decay_per_hop`. New brick 0c-ii.

The triage principle in the 0c report is right — **silence is the discriminator, not
parameter-hood** — but it selected the wrong parameter. Measured:

```
floor=0.02 (default)   reached 3: A=1, B=0.243, C=0.0592
floor=nan              reached 6: A=1, B=0.243, C=0.0592, D=0.0144, E=0.00351, F=0.000854
floor=-inf             reached 6: (identical to floor=nan)
```

`floor=NaN` **silently disables the locality guard**, with no error and behaviour identical to
`-inf`. It changes which nodes are reached, therefore coalition membership, therefore
`Coalition.strength`, therefore the competition. That is DEFECT-C's failure mode exactly: a NaN
passing a comparison unremarked.

`decay_per_hop` is confirmed **not** to need validation — it refuses loudly with
`ValueError: non-finite transmitted activation`. Recorded as a decision, not an omission, so
the asymmetry between validated and unvalidated parameters is legible rather than inferred.

**0c-ii, not a third widening of 0c.** One parameter, one invariant, its own small pass. It is
a boundary-validation item and belongs with O-12's class, not with 0d's accumulation class;
folding it into 0d would blur two different diseases.

### The process gap: the tester must not run capture_run or ledger_sync.

Neither option offered is the right one. Tolerating C2 findings during a hand-off puts a hole
in the gate; making reconciliation precede the commit leaves verified work uncommitted and
blurs who committed what.

**The actual fix is that the tester should never have been running those tools.**
`capture_run` writes the ledger, and the ledger is a claim-bearing artifact — moving the
canonical count is not the tester's to do, for exactly the reason `run_tests.py` is
hook-blocked from it. Remove capture and sync from the tester's close-out; they belong to
architect-pm. Then the totals do not move at the tester's commit, C2 stays green, and the gate
passes without being weakened.

This also retro-explains the earlier incident in which the tester produced a capture that
omitted an unregistered suite. It was not a mistake inside a correct workflow; it was a tool in
the wrong hands.

### Endorsed without change

**SPEC-0b2 §6's "83 assertions" stays as written.** *A verification record edited after the
fact to reflect a later state is not a record.* That principle is now binding and belongs in
the pre-registration discipline alongside "no threshold moves after a number is seen."

### Flagged, decision deferred, before the paper ships

**Nine assertions across the new suites hard-fail on any machine without five interpreters.**
An independent run in a one-interpreter environment gives 22 suites, 1,718 passed, 9 failed —
and 1,718 + 9 = 1,727, so the canonical total is right and the nine are entirely
environment-gated. The consequence is that the canonical suite is unrunnable on CI, by a
collaborator, or from a fresh clone of an MIT-licensed repository that invites scrutiny.

It also conflates two things this project separates everywhere else: **"the property failed"
and "this machine cannot test the property."** A reviewer on one interpreter should read
*18 of 18 invariants verified; 3 environment-gated checks skipped; sweep incomplete* — which is
honest and useful — not a red suite, which is neither. Recommend converting these to
skip-with-recorded-reason. Not decided; must be before submission.

The check asserting that *the interpreters which can expose the defect were actually swept* is
the best single assertion in this repository and must survive the conversion. It encodes "a
coverage axis is only evidence for the property it can perturb" as executable.

## D-017 · 2026-07-26 · 0b2's mechanism bar closes — tester PASS on all nine invariants
**Decided by:** tester (the verdict) · architect-pm (the record and the close-out)
**Supersedes:** the FAIL verdict of D-011, which is preserved in SPEC-0b2 §8 as the record it was

**The verdict (recorded, not decided). PASS — all nine of SPEC-0b2 §6's invariants hold** under
adversarial and loop-closed conditions. Suite `tests/test_tester_0b2_reverify.py`, written from
scratch rather than as an extension of the original adversarial suite; swept five CPython minors ×
six hash seeds × two reps, one digest throughout. Canonical run: **23 suites, 1,973 assertions, 0
failures**, all five interpreters agreeing.

The three defects the FAIL recorded are closed: **DEFECT-A** by brick 0c, **DEFECT-B** by the
single-read materialisation, **DEFECT-C** by σ validation and then `energy` validation (D-015).

**`0b2` stays `BUILT-UNVALIDATED`.** This closes the **mechanism** bar only. No cognitive claim is
made or approached, and the meaning bar is untouched — still open after three structurally distinct
refusals.

**The most useful output of this pass is a measurement technique, not a verdict.** N-5 must be
tested on a **frozen** clock, and the numbers say why: on the library-default live clock, two
*identical* `sigma=None` calls differ (`0.2433743747480014` vs `0.24337436243963237`), and over 60
identical calls the spread is ≈ 2e-9 relative — about 1e9 ULP — from lazy decay between calls.
**DEFECT-B's entire effect is inside that spread.** Cagan hit this and nearly filed a defect against
a working engine. The suite now **asserts** the noise floor, so the reason every bit-exact test
freezes the clock lives in the tests rather than in a deletable comment. *Establish the noise floor
before believing the signal* generalises well past this brick.

**A correction that is itself the lesson.** SPEC-0b2 recorded the silencing cliff as "survives to
16, none from 32". The re-verification measured **24**. An exhaustive binary search found the truth:
**every out-degree 1…31 survives; 32 is fully silenced.** Three measurements, three answers, none
wrong as observations — each reported *the largest value it happened to sample*. **A boundary
located by sampling is the last sample, not the boundary.** Corrected in §6.9 and §8, and "cliff,
not taper" is now scoped to **equal-strength** fans, since unequal fans taper genuinely.

**What stays open for 0b2, and the two floor questions are NOT one question.** The §5 default-flip
decision (Cagan's). **D-008** — the floor's **SCALE-INVARIANCE** — open, and it is what **blocks the
flip**. Brick **0c-ii** — the floor's **FINITENESS** — registered, blocks nothing. They touch the
same constant and are otherwise unrelated: validating `floor` for finiteness leaves it as absolute
as it was, and making it relative leaves it as non-finite-able as it was. Stated in SPEC-0b2 §5,
SPEC-0c §4 and SPEC-0d §7.1 so the two cannot quietly merge.

**Two observations routed, neither blocking.** (i) `spread_activation`'s seed guard is
`store.exists(seed_node)`, which is **true for RoadIDs**: at `hop_budget=0` a road id yields a
well-formed result seeded on a road with no error; at a larger budget `NotFound` is raised from
inside the expansion rather than at the boundary. Verified identical on the pre-overlay engine —
**pre-existing, not 0b2's** — and unreachable from any internal caller. Same class as O-12 and
DEFECT-C; **recommend folding into 0c-ii**, whose scope is exactly that class. (ii) The overlay's
own arithmetic has **no builder-side assertion** — `tests/test_nous_activation.py` has one test
named for it, and everything else lives in tester-owned files. Not a defect and not a reason to
doubt the verdict, but the overlay would have no coverage if those suites were removed. Worth a
builder pass eventually.

**Also swept, worth recording:** the machine now carries CPython **3.14.5** alongside 3.14.4; both
were exercised. The ledger records whatever `python3.14` resolves to at capture time.

## D-020 · 2026-07-25 · 2f takes design C; traversal_count stays and is asserted dead; P_PRP is caller-supplied
**Decided by:** Cagan
**Supersedes:** corrects the premise I gave when commissioning 2f

### The premise I gave was wrong, and I verified the correction before accepting it.

I framed 2f as reconciling two plasticity models with "the integer ladder having shipped." It
did not ship. Verified in code: `quality_of` reads `road.strength`, a float, against
DIRT/GRAVEL/ROAD ceilings; `traversal_count` has exactly three occurrences in `src/` —
declaration, increment, copy — and is read by nothing.

So ω already exists: continuous, bounded, lazily decayed. **2f does not have to replace a
plasticity model. It has to add a time dimension to one that is already the right shape.** The
question I posed — ladder as derived view, or removed — was answered in code, in favour of the
view, before the spec existed.

### §3.4 — design C. The counter-argument asks us to pay for a claim we are forbidden to make.

C: episodic trace outside the store, eligibility computed from timestamps, credit applied
through the existing `strengthen()`. Zero Tier-1 re-validation. Full tag/capture held as 2f-ii.

The honest counter in the spec is that if the biological claim is the point, C is scaffolding
that will be replaced. **The biological claim cannot be the point.** CONTRIBUTING.md rule 1: biological
*inspiration* may be described; biological *fidelity* may not be asserted. Paying Tier-1
re-validation now to buy fidelity buys a claim this project is constitutionally barred from
making. 2f's deliverable is a mechanism — temporal credit assignment — and C delivers it.

Second ground, which makes C idiomatic rather than expedient: **computing from timestamps
instead of storing is the substrate's own existing move.** `nous_store` already does exactly
this with lazy decay. C is consistent with the design philosophy, not a shortcut away from it.

And the instinct behind it is correct and worth recording: *Phase 0 was restored four commits
ago by four bricks of repair; I am not spending it on a timestamp.*

**2f-ii stays registered, and its trigger is named:** it is paid for when a *behavioural* need
arrives (behavioural tagging), never because a timestamp would be tidier. Deferred, not
foreclosed.

### §2.3 — `traversal_count` stays, is documented, AND is asserted dead. Neither option as offered.

Leave-and-document is nearly right — removing it is a Tier-1 change to freshly-restored code
for a cosmetic gain. But there is measured harm, not hypothetical: **that vestigial field
already caused a documentation error today.** I framed this entire brick around a shipped
integer ladder because `traversal_count` exists and looks exactly like Module 01's ladder. It
misled the person commissioning the work, one turn ago.

So: leave it, document at the declaration that it is written-never-read and is **not** the
plasticity signal, and add an **asserted-negative that it remains unread in `src/`**. If anyone
starts reading it, the test goes red and forces a decision. That converts "document it" into
"enforce it", which is this project's idiom, at the cost of one comment and one test with no
Tier-1 change.

### §4.3 — P_PRP is a caller-supplied scalar. And the justification correction is the best thing in the report.

Adopted, on three grounds: it does not block 2f on NEUROMODULATION, which is unbuilt; a
caller-supplied scalar can be **held fixed**, which is required to separate 2f's effect from
arousal's and which no published-state design permits; and it defers the publisher without
foreclosing it.

Layer 0 justified the one-cycle lag as *"biologically honest since neuromodulation is slow."*
That is a resemblance argument and this project does not accept those. The structural reason is
stronger and is now the recorded one: **without the lag, P_PRP at cycle t is a function of
arousal at t, which capture then changes — a same-cycle loop whose evaluation order would decide
the answer.** Four bricks of repair have established that an answer decided by evaluation order
is not an answer.

**Record the corrected justification now, before NEUROMODULATION is built.** A design
implemented for a resemblance reason is a design someone later removes when the resemblance
stops feeling compelling. The structural reason survives that.

### The two routed observations

**RoadID-as-seed → folded into 0c-ii.** Confirmed: `store.exists(road_id)` is True, and
`spread_activation(store, road_id, hop_budget=0)` returns a well-formed result seeded on a road;
at the default budget it raises `NotFound`, so the silent window is `hop_budget=0` specifically.

0c-ii now carries two items and both are *a boundary silently accepting something it should
not*. That is not scope creep — it is the brick finding its actual subject. **Re-scope 0c-ii as
boundary hygiene**, not as "the floor thing", and state the two-floor-questions distinction
inside it as before.

**The missing builder-side assertion is mine.** I wrote that overlay in the builder lane and
asserted only the neutral case plus a fan probe, so all evidence for its arithmetic lives in
tester-owned files. The practical risk is low — the tester's suite is in the canonical runner —
but it is a **claim-accuracy** problem: the paper says the builder implements test-first, and for
this mechanism that is not true. The builder adds arithmetic assertions to
`tests/test_nous_activation.py`, and the builder's self-audit gains a seventh item: *does a
builder-side assertion exist for the arithmetic you just wrote, or does all evidence for it live
in tester files?*

### Two aphorisms, both bought with real defects, both for the paper

- **"A coverage axis is only evidence for the property it can perturb."** (0c)
- **"A boundary located by sampling is the last sample, not the boundary."** (the silencing
  cliff: 16, then 24, then binary-searched to 32 — three measurements, three answers, none wrong
  as observations, each reporting the largest value it happened to sample.)

### Order

**0d lands before 2f.** As the report puts it: a gate installed after the traffic has passed is
a fifth manual hunt wearing a detector's name. 2f is the first brick built after the detector
exists, which makes it the test of whether 0d does its only job.

## D-021 · 2026-07-26 · 0d tester verdict is FAIL on F-6 — and the false claim was mine
**Decided by:** tester (the verdict) · architect-pm (the record and the corrections)
**Amends:** SPEC-0d §3.3, which asserted something false as the brick's headline argument

**The verdict (recorded, not decided). FAIL on F-6.** Seven of eight invariants hold. The
detector itself is sound: F-3 verified with the tester's own injections plus mine (three spec
shapes, nine more of the tester's, a brand-new module, a stale registry entry, exit 1 with
injections and 0 clean), F-4 clean with a structural rather than name-based integer exemption,
and F-1 demonstrated **loop-closed on the project's own git history** — `src/` extracted at three
pre-fix commits shows **all three manual hunts would have been caught on the day the code was
written**. That is the strongest single piece of evidence 0d could have produced, and nobody
writing the scanner chose what is in those commits.

**DEFECT 0d-1, and it is mine.** The registry entry for `nous_field.py:124` read *"shape present,
symptom unreproduced"*, and **SPEC-0d §3.3 presented that pair as "the entire case for a
detector."** The tester ran the entry's own falsifier and it fires: 2 distinct bit patterns over
4! source orders, on 40 of 40 randomly generated convergent stores. Verified independently
(0.4325968097408329 vs 0.43259680974083287).

**The root cause is the lesson.** The clearing probe used four sources converging on **one node**.
At hop 1 each road is traversed by exactly one source's spread, so every `merged_flow` value is
**single-term** — and a single-term sum cannot vary by reordering. **The probe was structurally
incapable of exhibiting the symptom it was run to look for.** A shared road must sit *downstream*
of the convergence to accumulate terms from several spreads. That is the six-bug checklist's
"structurally-impossible branch" occurring **inside the brick built to stop that class**, written
into the spec as its headline argument.

**The corrected argument is stronger than the false one.** The original was *"a site can have the
shape and lack the symptom, so shapes must be enumerated."* The truth is: **a site can have the
shape, have the symptom, and still clear a probe a competent person designed to find it.**
Reproduction cannot be the gate. Only enumeration can. §3.3 is corrected in place, showing the
wrong text and the right one, because a spec quietly amended teaches nothing.

**FINDING 0d-3, also mine to fix.** `Clock.advance._t`'s reason claimed *"no term SET that could
be permuted."* False, and it was the half a reader relies on — permuting a dt multiset moves `_t`
(2.402012593713817 vs 2.4020125937138173, first multiset tried). The mechanical half is true
(one `AugAssign` per call; **no caller of `advance()` in `src/` at all**). Corrected to the real
and weaker argument: time order is *semantically* fixed. Both entries now carry falsifiers.

**Both corrected reasons rest on bounds I verified rather than inherited.** `ActivationField.flow`
has **no reader in `src/`**: `form_coalitions_from_field` reads only `field_.total`,
`field_.broke_through` and `field_.dominant`; the `.flow` read inside `form_coalitions` is
`ActivationResult.flow` from a single spread, and `form_coalitions` has **no caller in `src/`**.
A false bound is worse than no registry, because it is an argument someone will trust — which is
exactly what just happened.

**Routed to the builder, not fixed here.** **0d-2:** ten undetected shapes with no limitation
entry, including `-=` (the scanner's own comment says "additive only", so a reader concludes `-=`
is covered — it is not), walrus, tuple targets, `itertools.accumulate`, `operator.add` in a loop,
and a **traversal blind spot**: statements inside a `match` case are never walked, because the
walker recurses into `body/orelse/finalbody/handlers` and `ast.Match` uses `cases`. `src/` has no
`match` today; **Phase 2 is when that stops being true.** **0d-4:** a NUL-byte module raises an
uncaught `ValueError` on 3.10 only, and a non-UTF-8 module raises `UnicodeDecodeError` and exits
**1** where the documented contract for "the tool could not run" is **2**. Both fail loud, which
is the safe direction.

**F-6 is the invariant a machine cannot check, and that is now demonstrated rather than argued.**
C6 verifies a reason **exists**, is ≥24 characters, and that the verdict matches the AST. It
cannot verify a reason is **true**. The builder's F-6 tests were the mechanical floor plus one
substring match, and **structurally could not have caught 0d-1**. "C6 green + suite green" said
nothing about whether the registry was true — which is precisely what failed. The division of
labour is correct; the lesson is that a registry's *reasons* need a human adversary every time,
not once.

**Not closed out.** No capture taken — the verdict is FAIL. `tests/test_tester_0d_adversarial.py`
(270 assertions) is registered in `run_tests.py`; C5 and C6 are green; C2 holds at 16, all in the
held paper. **The tester must re-verify F-6 against the corrected reasons — architect-pm cannot
certify its own correction.**

**Still open and unanswered:** whether `tools/test_ledger.py` (the gate's own 139 assertions)
joins the canonical count, extends C5 to scan `tools/`, or stays out. It changes what the
headline figure means, so it is Cagan's.

## D-022 · 2026-07-26 · 0d PASSES and the FOUNDATION ARC CLOSES; three standing rules recorded
**Decided by:** tester (the verdict) · Cagan (the dispositions and the stop) · architect-pm (the record)
**Supersedes:** D-021's FAIL verdict on 0d, which is preserved as the record it was

**The verdict (recorded, not decided). PASS.** All eight invariants hold. 289 assertions, 0 failures,
on five CPython minors × six hash seeds. Canonical suite green at 24 suites.

**F-6 was re-verified the only way it can be: by hand, adversarially, every reason.** All six
falsifiers were **run** rather than admired — several had never been executed. All six survive. The
tester also attacked each probe's *capability* rather than only its claim, which is what caught 0d-1
the first time, and confirmed independently that the discredited probe yields one bit pattern where
the correct shape yields two.

### The dispositions

**FINDING 0d-5 — routed to the builder, wording only.** `bound_on_absence` promises to flag every
matching read and under-reports on dynamic access. Narrow the promise; do **not** widen the
machinery. It must state actionably what *is* covered and carry an exit instruction.

**`field.total` now names a falsifier**, with its provenance corrected: the pinning rests on
`cluster_sources` ordering `group_seeds` by `creation_seq`, not on `build_activation_field`.
"This entry has no falsifier, and here is why" would have been acceptable; silence was not.

**L3 is brick 2f's STEP ZERO, not a 0d task**, and it is written into SPEC-2f §0.5 as mandatory:
*teach the gate to see tuple-target accumulation, then build the thing that would have hidden in
it.* The tester showed the idiomatic 2f line produces **zero** findings. A passive sentence in a
spec would have been incoherent one section after this same cycle replaced a recorded intention
with a machine check. Ownership sits with the brick that needs the coverage, and **2f's first act
becomes a demonstration that extending the gate is a normal cost of building on it.** L7 stays out:
an integer counter is not a float accumulation — out of scope, not a hole.

**Brick `0e` registered — abort-hides-tests, scheduled BEFORE the paper capture.** A test that
*raises* rather than fails is absent from the failure list and aborts everything after it, so
"0 failures" can be true of the report and false of the repository. Seen **twice**, both times found
only because someone ran the file directly. It is not 0d's problem — it affects every suite — and
the project's headline number rides on it.

**`0d` moves to `PROVEN`, within a stated scope**, and the two axes do **not** fit a tool cleanly.
`BUILT-UNVALIDATED` would imply a meaning validation that can never arrive, because a gate makes no
claim an external yardstick will grade. The substrate bar is met — determinism, purity; integrity
has no analogue for a scanner — and the functional claim is verified the only way a refusal can be:
retro-catch on three pre-fix trees, and injection turning the build red. The scope is L1–L10, one of
which is knowingly scheduled as 2f's step zero. The vacuity of the meaning axis is recorded rather
than papered over.

### Three standing rules, recorded as obligations rather than observations

**1. THE THIRD APHORISM — "A site can have the shape, have the symptom, and still clear a probe a
competent person designed to find it." Therefore reproduction cannot be the gate; only enumeration
can.** Bought at the highest price of the three: the impossible-branch defect occurred **inside the
brick built to stop that class** and was written into that brick's spec as its headline argument.
Nobody was careless — the probe was aimed at the right site and reported truthfully. The failure was
treating a negative observation as evidence of absence. Operational form: **a clearing probe must be
shown capable of failing before its silence counts as evidence.** In `docs/METHODOLOGY.md` beside
the other two, and marked for the paper.

**2. ON A FAIL, COMMIT THE EVIDENCE AND THE CORRECTIONS; NEVER THE STATUS.** Cagan's original
instruction said commit nothing on a FAIL, and records here that it was wrong: leaving 1,335 lines
of adversarial tests uncommitted would have discarded the pass's entire product to protect a label
that was not going to change anyway. The status is what a FAIL withholds. The evidence is what a
FAIL produces.

**3. C6 VERIFIES THAT A REASON EXISTS, NEVER THAT IT IS TRUE — AND THIS GAP DOES NOT CLOSE.** It
checks presence, a length floor, and that the verdict matches the AST. Truth is out of machine
reach. **A registry's reasons therefore require a human adversary on EVERY pass, not once**, and
each pass must *run* the falsifiers rather than read them. This is a standing obligation on every
future tester pass that touches the registry, not a note about one brick. The evidence that it binds:
the builder's own F-6 tests were the mechanical floor plus one substring match, and could not
structurally have caught either false reason.

### Routed to the builder, as one bundle, NOT in this commit

Cagan's Option B on the `tools/test_ledger.py` question, plus 0d-5: **(a)** extend C5 to scan
`tools/` so the gate's own suite cannot sit unregistered; **(b)** register it in a **separate
bucket** — its assertions do **not** join the headline total; **(c)** **rename the headline figure
so it says what it counts.** Once C5 sees `tools/`, the repository contains more assertions than the
headline reports, and an unlabelled figure in a paper that cites it becomes a false claim — the
exact failure C2 exists to prevent, arriving through a **field name** instead of through prose.
Carry two **named** figures and make the paper cite the substrate one **by name**. *Closing a
silence must not open a claim.* Verified before routing: renaming `tests.*` breaks `ledger_sync.py`
and C1/C2, so the schema change and the code change must land together — which is why this is the
builder's bundle and not a ledger edit here. **(d)** the 0d-5 docstring narrowing.

### The stop

**The foundation arc ends here, by decision.** Not because nothing is left to improve — `0c-ii` is
specified and unbuilt, `0e` is registered, L3 is scheduled, the paper is held — but because
something always will be, and that is precisely why a stop has to be a **decision rather than a
discovery**. Next is `2f`, beginning with its step zero.

## D-023 · 2026-07-26 · The AOL autonomy criteria are pre-registered — five, not four, and one is upgraded
**Direction:** Cagan (the four questions) · **corrections and the fifth:** architect-pm · **frozen on adoption**

**What was adopted.** `docs/specs/SPEC-2e-autonomy-criteria.md`: **AOL-1 … AOL-5**, the project's
first pre-registered acceptance criteria, written while all five are mechanism-absent and nothing
can be tuned toward them. Also folded into SPEC-2f, the roadmap and the ledger.

**THE NAME IS LOAD-BEARING. These are AUTONOMY AND OPEN-ENDED LEARNING criteria and are NOT
consciousness tests**, in any document, ever. The reason is accuracy, not squeamishness: **a system
could satisfy all five and possess nothing any theory of consciousness points at.** Everything the
five describe is expressible in the vocabulary of control and learning. They measure what the
system **does**, never what it is; they say nothing about experience or awareness. Butlin et al.'s
indicator properties remain the **orthogonal architectural** axis — **complementary, neither
superseding the other**, and progress on one is never progress on the other.

**The three-walls gate, run on all five: MECHANISM ABSENT — and that is a DATE, not a rejection.**
Unlike 1e (circular by construction), 1e′ (mechanism absent *and* unfixable without changing the
engine's meaning) and 2c (the signal does not vary), these are absent in the ordinary curable
sense. Which is exactly why they are worth pre-registering now.

**Corrections that were not optional:**

- **AOL-2 was UPGRADED before adoption.** As posed, "do goals get harder" is passable by a system
  that generates ever-harder goals and **improves at none of them** — from outside, indistinguishable
  from a curriculum. The criterion is now the **conjunction**: difficulty rises AND capability on
  those goals rises. Difficulty is measured **externally**, never by the agent, or the curve measures
  the scorer.
- **AOL-3 carries a HARD CLAUSE and is recorded as NOT RUNNABLE.** Learning progress is the
  best-developed idea in the literature and the most dangerous to implement here: if the measure of
  *what can be learned* and the measure of *how much was learned* share a source, the system passes
  **by construction** — 1e's circularity in new clothes, and 1e is the wall that cost most. The two
  sources must be independent and **named**. They cannot be named today, so the criterion is
  pre-registered and **not runnable**, stated rather than softened.
- **AOL-1's baseline must be matched, and the matching is specified in advance** — action space,
  budget, start distribution, termination, observation pipeline, and a uniform random policy over the
  **same legal actions**. A strawman baseline proves nothing.
- **AOL-4's environment change must not be authored to produce the result** — drawn from a
  pre-declared external family, with the specific shift fixed by a recorded seed.
- **Every criterion states what makes its NULL interpretable.** A criterion whose null cannot be
  interpreted is a wish with a threshold attached. Three of the five need a positive control showing
  the environment/measure has range at all.

**AOL-5 was ADDED, and it is what makes the other four unfakeable.** 1e′ died because **nothing in
the system was scarce** — every out-road received the source's full activation and the fan curve was
flat to the last digit. The same hole voids AOL-1…4: **without scarcity, generating a goal is free,
and a system passes all four by mere ENUMERATION** — exploring widely, listing harder goals, dropping
and regenerating them — while nothing is ever traded against anything. Scarcity is what turns goal
generation into a **choice**, and a choice is the only thing that can evidence autonomy. Routed to
the first brick with a shared budget; **0b2's conserved-activation overlay is the nearest existing
thing** — right shape, wrong object, and default-off.

**SCOPE CONTROL, recorded because it is the thing most likely to go wrong: 2f satisfies ZERO of the
five.** It is a prerequisite for three. **Being a prerequisite is not partial credit, and adopting a
yardstick is not adopting a roadmap.** Four of the five require mechanisms **not on the roadmap at
all**: nothing initiates, there are no goals, no skills, no competence measure, no environment. That
gap is stated in the spec rather than left to be discovered.

**External grounding — searched, not asserted.** AOL-1: reward-free exploration, state-entropy and
coverage metrics (Hazan et al.; Seo et al. RE3, arXiv:2102.09430) — **a usable baseline exists**.
AOL-2: IMGEP with automatic curriculum learning (Forestier, Mollard & Oudeyer, JMLR v23 /
arXiv:1708.02190), POET (arXiv:1901.01753), and the open-endedness definitions work
(arXiv:2311.00344, arXiv:2312.03126) for the novelty≠progress critique. AOL-3: SAGG-RIAC (Baranes &
Oudeyer), ALP-GMM (Portelas et al.), CURIOUS (Colas et al., arXiv:1810.06284), MAGELLAN
(arXiv:2502.07709). AOL-4: continual learning — **BWT, Forgetting Measure, MFT/MFN/MAA** are
standard and borrowable (van de Ven et al., arXiv:2403.05175); BWT < 0 *is* catastrophic forgetting.
AOL-5: bounded rationality (Simon) and resource-rational analysis (Lieder & Griffiths, BBS) —
**no off-the-shelf benchmark exists**, so it is designed as a **structural** criterion rather than a
graded one, and that is said plainly instead of inventing a benchmark.

**Two corrections to the record, made in passing:**
1. **"0d PROVEN" will be over-read**, so the correction is written into SPEC-2f §0.25 where someone
   might act on the misreading, not buried in a ledger note: the label means *the gate does what it
   says*, not *the gate catches everything*. **The class is not closed; it is ENUMERATED** — which is
   the entire product of brick 0d.
2. **The "0/14, 1 partial" Butlin figure is recorded NOWHERE in this repository.** It is Cagan's
   standing position, cited but undocumented — the staleness class C1/C2 exist to prevent, arriving
   through absence rather than drift. Flagged, not fixed; it needs its own document and ledger entry
   before it is cited again.

**PRE-REGISTRATION DISCIPLINE.** Fixed on adoption: no threshold, metric, control or matching
condition moves after a bearing number is seen. Amendment is permitted **only before** any such
number exists, only via a DECISIONS entry, and **never toward an easier result**; an amendment after
a number exists becomes a **new** criterion with a new id while the original stands with its result.

## D-024 · 2026-07-26 · The yardstick document lands; C4 is a confirmed defect and becomes brick 0f
**Decided by:** Cagan (both items) · architect-pm (the two quarantine calls and their reasons)

### Item 1 — `docs/CONSCIOUSNESS-YARDSTICK.md` is tracked, and the two quarantines resolve DIFFERENTLY

The assessment behind "0 of 14, 1 partial" was cited in project records for two days with **nothing
in this repository backing it** — C1/C2's failure class arriving through **absence** rather than
drift, and worse than drift because no check can catch a figure that is simply not written down.
It is now tracked.

**C4 quarantine: GRANTED, on SUBJECT MATTER, with the reason recorded in the ledger.** This is the
one document whose subject *is* the claim and whose entire content is the argument for why the
project must never make it — the same class as `PAPER_CLAIM_INVENTORY.md`.

**It was explicitly NOT granted on the strength of C4 currently passing on the file.** That silence
is uninformative, for a reason discovered in Item 2: C4 matches by literal substring and is weaker
than a clean pass makes it look. The file does contain `is conscious` and `validated cognitive
model`; both are negated, and C4's negation logic correctly skips them *today*. When 0f widens the
matcher C4 will see more of this file, and without the quarantine someone would "fix" the one
document whose job is to make the argument. **Re-checking this file is an explicit 0f acceptance
item.**

**C2 quarantine: REFUSED, and the refusal is the more interesting half.** C2's regex requires a
number followed by `assertions|suites|checks passed|passed`. Verified by running `COUNT_RE` against
each figure: `256 participants`, `655 electrodes`, `0 of 14`, `1 partial` are **structurally out of
reach**. Granting a quarantine against a gate that cannot fire is exactly the convenience-grant
this project treats as how a gate rots. **The distinction is the point: C4's quarantine is a
property of the SUBJECT; C2's would have been a property of a RUN.**

**Scoping preserved exactly, not upgraded.** The assessment is verified against **arXiv:2308.08708
Table 1 ONLY**. The published TiCS version could not be reached at verification time, and the
document carries its own falsifier — *a copy of the published version showing an added, removed or
reworded indicator*. It must **not** be described as "verified" until someone reads the published
version.

**STANDING RULE: the 0/14 figure is cited BY REFERENCE to that file and nowhere else — ever.** Not
in the ledger, the roadmap, the paper, or conversation. The ledger's `2e` note, which asserted two
days ago that the figure was "recorded nowhere", is corrected in place rather than left as a stale
claim of my own making.

**A finding raised in passing, and not silently fixed:** `claim_quarantine_paths` had **eight
entries and no reasons field**, while `count_quarantine_paths` has had one all along — so the
*more* important gate is the one whose exemptions were unexplained. A `_claim_quarantine_reasons`
field now exists and carries the new entry. The other eight are **flagged, not retro-filled**:
writing reasons after the fact for exemptions granted by someone else manufactures provenance
rather than recording it. Each should gain its reason the next time it is touched.

### Item 2 — brick `0f`: C4 evades on any interpolated word. CONFIRMED, not suspected.

Reproduced independently rather than taken on report:

```
"Nous is conscious."                -> 1 finding
"Nous is a mind."                   -> 1 finding
"Nous is a conscious mind."         -> 0 findings   EVADES
"Nous is clearly conscious."        -> 0 findings   EVADES
"Nous is, in every sense, a mind."  -> 0 findings   EVADES
"Nous is undeniably sentient."      -> 0 findings   EVADES   (not in the reported table)
"This is an AGI."                   -> 1 finding
"This is, by any measure, an AGI."  -> 0 findings   EVADES   (not in the reported table)
```

Two evading forms beyond the ones reported. Mechanism: `forbidden_claim_terms` are matched with
`str.find()` as **literal substrings**, so any word interpolated between the copula and the noun
breaks the match.

**The evading forms are precisely the sentences someone writes when overclaiming** — an unhedged
assertion attracts an intensifier, and "clearly", "undeniably", "in every sense" are what
enthusiasm sounds like. C4 guards CONTRIBUTING.md **rule 1**, the rule this project's entire credibility
rests on, so **every "C4 passes" in the record has covered less than it appeared to.** That is not
a reason to distrust the existing record — no forbidden claim has been found by any other means
either — but it is a reason the record's *strength* was overstated.

Registered as **`0f`, DESIGNED, scheduled BEFORE the paper capture alongside `0e`.** Not fixed now:
it is not 2f's problem and must not delay 2f. The fix is a brick rather than an edit because the
matcher must be widened **without breaking the negation-cue logic** that keeps this project's
disclaimer-dense documents from being flagged — and those two requirements pull against each other.

### Why this was found, and it is the project's own rule turning on the project's own gate

> **"A coverage axis is only evidence for the property it can perturb."**

**C4 had never been perturbed.** It was found because a clean pass on a document *saturated* with
the forbidden vocabulary looked too easy — which is the third aphorism working exactly as intended:
**the silence of a probe counts as evidence only once the probe is shown capable of failing.**

Three gates have now been perturbed and two were found wanting on first contact: the determinism
probes could not see 1 ULP, and C4 cannot see an adverb. The one that survived, C6, survived
*because* it was built with an injection test as its acceptance criterion. That is the argument for
making adversarial self-test the default for every gate this project ships, not a special measure
for the ones that look suspicious.

---

## D-025 — SPEC-2f step zero: the gate is extended by the brick that needs it

**Date:** 2026-07-26 · **Lane:** architect-pm · **Status:** recorded retroactively

**A recording gap, closed here and labelled rather than hidden.** `D-025` was cited in four
places in `tools/` — `ledger_check.py` twice, `test_ledger.py` twice — as the decision
authorising SPEC-2f's step zero, before any such entry existed in this file. The work was
correctly commissioned (SPEC-2f §0.5, under D-020 and D-022) and correctly executed; only the
decision record was missing. It is written now, with its number preserved so the four
references resolve instead of being renumbered around.

**The decision.** Brick 0d's gate could not see `trace[rid], counts[rid] = trace[rid] + e,
counts[rid] + 1` — the line 2f is most likely to write. Ownership of the fix sat with **2f,
not 0d**, and that placement was the point rather than a convenience: *extending a gate is a
normal cost of building on it.* A gate no brick is ever required to extend is a gate that
narrows silently every time the code grows past it.

**Held to, and worth recording because it was the tempting corner:** step zero closed L3 and
**stopped**. No eligibility trace, no credit assignment, no "while we are here".

---

## D-026 — Step zero closes: two rules, two digests, and a capture that omitted its own evidence

**Date:** 2026-07-26 · **Lane:** architect-pm · **Status:** decided

Tester PASS on SPEC-2f step zero (`9c26356`), builder fix at `044008c`. Close-out.

### 1. The capture omitted the primary evidence for the brick it was quoted beside

`docs/TEST_OUTPUT.txt` did not contain `tests/test_tester_0d_adversarial.py` **at all** — 23
suites captured, 24 in the runner. The missing file is the 334-assertion suite that is the
primary evidence brick 0d works, so the headline figure omitted the evidence for the brick it
sat next to. **`C1` and `C5` both passed throughout**, and that is the finding: C1 compares
the ledger to the capture, C5 compares disk to the registry, and **nothing compared what the
runner runs to what the capture contains.**

Recaptured across all five interpreters, all agreeing: **24 suites, 2,307 assertions, 0
failures.** Completeness was then verified by an explicit name-by-name diff of
`run_tests.py`'s suite lists against the capture — reported as a list, not as a reassurance:
zero missing, zero extra, order identical.

**Three stale totals were in circulation and none survived.** 1,973 (the old capture), 1,992
(my own figure, given to the builder in a brief, wrong because I had not verified it), and
2,281 (a correct measurement of a since-changed tree). The canonical number is read from the
runner output and is **2,307**. *Do not inherit a number from a brief, including from mine.*

**I am choosing an instruction over a mechanism here, and the reasoning is on the record.**
Three times this cycle I refused a written note in favour of a machine check, because in each
case the trigger was future code someone else would write. Here the trigger is the next
action and the brief is its instruction. The mechanical form — `capture_run.py` refusing on a
runner/capture suite mismatch, as it already refuses on interpreter disagreement — is
registered as **CC-12** and is **not built**.

### 2. Two digests, named — but still one value in the tool

`census_digest = b11fd55a71d900ee` (the 14 census rows) and `listing_digest =
a2f7ed1d67f53fbe` (full `--list-accumulations` stdout) are now recorded separately in the
ledger. Across step zero the **listing** digest moved and the **census** digest did not: the
report grew by two `REFUSED` rows and a summary suffix while the census was untouched. Both
the builder and the tester independently proposed splitting them and both were right — a
census digest that moves when the report format changes is a weaker invariant than one that
does not, and two consecutive passes spent real effort re-deriving from git that a movement
was benign.

**Recording the value is not the fix.** In the tool the determinism probe still hashes whole
stdout. Naming `census_digest` makes it citable so nobody re-derives that question; splitting
them in `ledger_check.py` is **CC-12** and is not done.

### 3. The obsolete constraint is struck

SPEC-2f carried *"write the trace update on its own line, or the gate will not see the one
accumulation 2f adds."* True only while L3 was open, and open in the spec for two passes after
it stopped being true. **Struck visibly**, with the retraction left in place of the text, so
that anyone who remembers the constraint finds its withdrawal rather than its absence. A stale
constraint cited as current is the same failure class as a stale count.

### 4. Rule four, and it is the first that runs

**An assertion must be shown capable of failing against the code it was written against.**

The tester audited every assertion it had written for this brick against the pre-fix tool and
found **2 of 12 passed on both sides** — one I flagged, one it found itself, and neither was
*wrong*, which is what makes them dangerous. A passing assertion reads as verification.

This is the operational form of the third aphorism and it is stronger, because the tester made
it a test: `test_the_repointed_assertions_can_actually_fail` loads the pre-fix revision from
git and requires each claim to fail there. Written into `docs/METHODOLOGY.md` as rule 4 and
marked for the paper. Both corollaries recorded: **convert, never delete**, and **a dead
assertion is kept and labelled**, because deleting it destroys the only evidence the failure
mode is real.

### 5. Never `git stash`

Into `CONTRIBUTING.md`'s repo conventions: inspect an old revision with `git show <rev>:<path>` or a
temporary worktree. A stash is **repo-wide**, so one taken inside a lane reverts every other
lane's uncommitted work. During this brick a stash at `044008c` swallowed 315 lines of
`WORKING-NOTES.md` and nothing noticed; damage was bounded to that file and recovered,
verified by diffing every path in the stash against `HEAD` and disk. On the same task the
builder used `git show` and the tester used stash — **lane discipline that a routine git
command can cross is not lane discipline.** The rule is about the command's blast radius, not
about anyone's care.

### 6. Adjudications

- **The two visible L13 refusals are not noise.** Both sit on `new_strength, new_charges =
  _compute_decay(road, ...)`, the one place in the substrate where a tuple-returning float
  computation occurs. **What would make them dangerous rather than merely present**, named so
  it can be watched for: today each returned value is single-term, so there is no fold to miss.
  It becomes dangerous the moment either aggregates over a collection — then the gate would be
  declining to look at precisely the site it exists for. *Falsifier: any change making
  `_compute_decay` aggregate more than one term per returned value.*
- **Limitation registered** — the listing's summary line contains `src/`, so a consumer
  matching on containment rather than prefix would capture it as a key. Every current consumer
  matches on prefix and is correct. Recorded, not fixed: rewording is cheap but would move the
  listing digest again for no measured benefit.
- **Limitations went 10 → 13**, reported as three rather than as one net win. Closing L3 cost
  L11/L12/L13.
- **0d stays PROVEN**; **2f stays DESIGNED** with §0.5 marked complete.

### 7. What this does not do

Step zero being complete unblocks SPEC-2f §1 onward. It is **not** partial delivery of it. No
eligibility trace exists, and 2f still satisfies zero of SPEC-2e's five autonomy criteria
(D-023). The next action is the mechanism, not another gate pass.

---

## D-027 — 2f-i closes: attention, not credit; and a proposal of mine was refused

**Date:** 2026-07-27 · **Lane:** architect-pm · **Status:** decided

Builder `1065c43` / `7886167` / `6411ef7`, tester PASS `19d3286`. Both lanes signed off.

### 1. The status, on two axes, deliberately not collapsed

**Build:** `BUILT-UNVALIDATED`, mechanism **tester-verified**. What 2f-i *is*: a verified
eligibility trace. Neutral byte-identity against the pre-2f engine recovered from git, the
window edge established structurally rather than sampled, application order proved
irrelevant from the code, every caller-supplied number refused at the boundary, every
control shown capable of failing, loop-closed on real `think()` output.

**Meaning:** `NOT-YET` — and it does not become `YET` by any further mechanism work of this
shape, which is why the two axes must not be collapsed into one label.

> **The sentence that governs every citation of this brick: the mechanism assigns ATTENTION,
> not CREDIT.** Every outcome it can express *strengthens* what preceded it. The graph moves
> one direction only, toward saturation, and nothing it does can be undone by anything it
> does. It marks which roads preceded a designated outcome and how recently — never whether
> that outcome was worth repeating. **Feedback with no sign is not feedback.** The half that
> exists is real and verified; the half that is missing is the half that would make it
> learning.

Not satisfied, by name: **zero of five AOL criteria** (D-023's reason — all five are
MECHANISM ABSENT), and **Butlin AE-1**, failed at its *first* conjunct.

### 2. Three bricks registered

**2g — the depression path.** The missing half, and now the **headline item on the
roadmap**. Nothing above it may be called learning until it exists. It is its own brick
because honouring a negative outcome needs new arithmetic and at least one **uncalibrated
constant**, and inventing that mid-verification inside a brick under a FAIL is the pattern
this project spent a week learning to stop.

**0a-ii — encapsulation.** `get_road(apply_decay=False)` returns the live stored `Road`;
`apply_decay=True` copies. 0a's **purity claim is not violated** — the read mutates nothing
— but there is no **encapsulation**. Two options recorded and rejected for now: *copy on
read* (Tier-1 change to 0a `PROVEN`, re-verifying purity, integrity, determinism and every
internal caller that relies on the live object) and *freeze `Road`* (strictly larger — every
internal mutation site rewrites to construct rather than assign). The general
"does a write follow a binding" question is **dataflow**, was deliberately declined, and
lives here.

**0g — the registry rots on line numbers.** `bound_on_absence` dismissals are keyed
`path:line`; one inserted comment fires a false `[C6]`. **Scheduled as STEP ZERO of the next
brick**, exactly as L3 was step zero of 2f, because the next brick edits `src/` and will trip
it constantly. The reason it outranks a silent gap: **a false positive that masquerades as
the check working is worse than a silent gap.** It already cost a real mis-measurement — the
tester's first blind-spot probe reported all five blind spots as CAUGHT, which was the
*shifted* bound firing, not the binding bound working. A gate that cries wolf gets ignored,
and that would waste the entire foundation arc that produced it.

### 3. A generalisation I proposed was refused, and the refusal was right

I put it to the tester that three defects shared one root — C4's interpolation blindness
(0f), the text scan that cannot tell a mechanism from its negation, and the wrapped-string
vacuity — all being "text matching that was never normalised."

**The tester checked and reported back that this is only partly true, and the difference
matters.** All three *are* substring matching on structured text, but they need **three
different fixes**: tokenisation, parsing, and whitespace normalisation. Merging them would
have produced a named class that looks closed when one third of it is — and a class that
reads as closed is worse than three open defects, because nobody re-opens it.

**The refusal is recorded, not just the outcome.** A direction from the person setting
direction, overturned by evidence from the lane whose job is to check it, is the separation
of duties doing exactly what it exists for. It should be visible in the record that this
happened, and how often. This is the second time.

### 4. Three small rules the pass paid for

**The vacuous-assertion rule, in its sharp form.** A **positive** containment assertion that
passes is live by construction — it passed because the matcher found the text. Only a
**negative** one can pass vacuously, because absence and impossibility are indistinguishable
from the result. Into `docs/METHODOLOGY.md` as rule **4a**, beside rule 4, and marked for
the paper. The sweep also found two ways to run itself wrongly: searching a source blob
flags a *live* assertion matching a runtime-assembled string, and requiring a string literal
on the left misses the very shape that caused the defect.

**A hand census that copies the scanner is not a second opinion.** The tester derived 0d's
census entry for 2f-i by hand from `src/` rather than reading it out of the tool. Small,
load-bearing, and the first thing that would be lost to convenience.

**"Six naive, unchanged" is the substantive half of the census claim.** The count that
*moved* (8 → 9 fsum) records that a site was added. The count that **did not move** records
that 2f-i introduced no naive accumulation — which is the property anyone actually cares
about, and it is asserted *because* it is unchanged.

### 5. Recapture

26 suites, **2,594 assertions**, 0 failures, all five interpreters agreeing. Completeness
verified by a name-by-name diff of `run_tests.py` against the capture: zero missing, zero
extra, order identical. `tests/test_tester_2f_adversarial.py` registered — after its
conversion landed, so that registering added no aborting suite.
