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
