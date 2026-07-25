# SPEC-0b2 — Conserved activation: divisive normalization at the transmission site

**Status:** brick 1 (the overlay) **BUILT, default-off** · **TESTER VERDICT ON §6: FAIL** — seven
of nine invariants hold, **N-2 and N-5 do not**, N-7 holds only for finite sigma · brick 2 (the
activation floor) **NOT STARTED** · the §5 default-flip decision remains **open**
**Revises:** 0b, the spreading-activation engine — was `PROVEN`, now `BUILT-UNVALIDATED`.
Demoted on 2026-07-25 by D-012: §6.0's DEFECT-A falsifies the determinism leg of Phase 0's
done-means at library defaults.
**Depends on:** BUG-0b1 landed first (the summation-order fix). Non-negotiable — see §0.2.
**Date:** 2026-07-25 · verification record added 2026-07-25 after the tester's adjudication
**Author lane:** architect-pm (§6 records the tester's verdict; the tester wrote the suite, this
lane wrote the record)

---

## 0. Framing

### 0.1 The honest-framing firewall

This spec adds a **capacity constraint to a spreading-activation engine**. It does not add
attention, awareness, competition-for-consciousness, or a bottleneck in any phenomenal
sense. "Conserved," "budget," "competition" and "normalization" here name **arithmetic**:
a road's transmitted activation is divided by the conductance of the roads leaving the same
source. Carandini & Heeger (2012) are cited as the source of the functional form, not as
evidence that Psyche reproduces a cortical computation. No claim of biological fidelity is
made or implied.

Nothing in this spec earns a cognitive claim. If it lands, 1c / 1d / 2c remain
`BUILT · UNVALIDATED`.

### 0.2 Why BUG-0b1 must land first

This change alters every float that reaches `Coalition.strength`. On the pre-fix code the
competition's winner could flip on a 1-ULP asymmetry produced by float-summation order
(`BUG-0b1`). Landing a representation change on top of that makes the change's effect and
the bug's effect indistinguishable, and any re-validation of 1c / 1d would be measuring
both at once. **BUG-0b1 is a separate, prior brick.** It has been fixed and verified.
<!-- ledger:allow-count -->
*(Snapshot at the moment the fix landed: 20 suites / 1,372 assertions / 0 failures on CPython
3.11, 3.12 and 3.13. The canonical run has since grown —
`tools/ledger.json` is the only current figure. The determinism sweep has also since widened to five
CPython minor versions, per D-010.)*

**Amended 2026-07-25.** The premise of this section — that the summation-order hazard was removed
before the representation change landed — is **only half true**, and the tester's adjudication is
what established it. `math.fsum` removed the hazard at the *coalition-strength* site. It did not
remove it at the **activation-accumulation** site one layer upstream, where the same bug class was
live all along (DEFECT-A, §6.2). So this change did land on top of a summation-order defect, in the
precise sense this section was written to prevent. That does not invalidate the neutral-identity
result — N-1 compares the new engine against the *actual* pre-change engine, so a defect present in
both cancels — but it does mean §0.2's guarantee should be read as scoped to `nous_coalitions`,
not to the whole float path.

---

## 1. The independent justification — and why it must be independent

`SPEC-fan-effect` §4 is explicit that the engine change is *"held as a separate, later,
explicitly-framed architecture decision — NOT a meaning-bar rescue"*, on the grounds that
*"adopting it in order to produce the fan effect would not earn it (engineering the answer
into the mechanism — the cousin of the circularity bug)"*. That reasoning stands and this
spec does not attempt to dodge it. The change therefore needs a justification that would
hold **if the fan effect did not exist as a target**.

It has one, and it comes from the project's own cited lineage.

> **A workspace with no capacity limit is not a workspace.** Global Workspace Theory is a
> theory about a **bottleneck**: coalitions compete because access is scarce, and the whole
> explanatory content of "one wins and is broadcast" is that not everything can. LIDA
> inherits this. `SPEC-1d` §1 cites Baars (1988) and LIDA as the engineering lineage of the
> competition, and `nous_plan_layer0_topology.md` locates Psyche as *"a blackboard
> architecture combined with a Global Workspace running on a timed cognitive cycle."*
>
> In the engine as built, **nothing is scarce.** `spread_activation` gives every out-road
> the source's full activation (`outgoing = node_act`); a node with one association and a
> node with two hundred transmit the same amount down each. The workspace then ranks the
> resulting coalitions. Ranking under abundance is a **sorting function**, not a
> bottleneck. The competition is currently a competition in name only, and that gap is
> between the code and the theory the code says it borrows from — not between the code and
> a desired experimental result.

Two secondary consequences of the same argument, both independent of any effect to be graded:

- **The min-size guard in `_density_score` is a symptom.** `denom = max(size, guard)` exists
  because *"the guard keeps a tiny coalition from winning purely by being small."* Under an
  unconserved spread there is no principled reason a small coalition should not win: nothing
  cost it anything to be small. Under conservation, a small coalition's members each
  received a larger share of a fixed source budget, so density carries information and the
  guard is doing less arbitrary work. The guard is one of the roadmap's named uncalibrated
  constants; conservation reduces what it has to paper over.
- **The activation floor becomes load-bearing in a new way.** See §5 — this is the open risk.

The falsifier that keeps this honest is in §4: **the fan effect must appear at a σ fixed in
advance on a principle unrelated to fan.** If σ has to be tuned to produce the effect, the
answer was engineered and this spec fails on its own terms.

---

## 2. The change

One site, `src/nous_activation.py`, inside the per-node expansion:

```
S_out    = Σ_{r ∈ out(node)} strength(r)          # fsum: exactly rounded, order-independent
competing = S_out − strength(this road)
transmitted = node_act · strength · decay_per_hop · σ / (σ + competing)      if competing > 0
transmitted = node_act · strength · decay_per_hop                            otherwise
```

with `normalization_sigma: Optional[float] = None`, **neutral by default**.

Properties of this form, all mechanical. **The right-hand column is the claim as specified; the
third column is what the tester's adversarial suite actually found on 2026-07-25.** Two of these
claims are false as written, and the corrections are load-bearing — see §6.

| Property | Claimed consequence | As verified |
|---|---|---|
| `σ = None` | Byte-identical to the current engine. | **HOLDS**, under attack, against two independent oracles — but only on a **frozen clock**; see §6.1. |
| `σ → ∞` | Analytically recovers the current engine (factor → 1). The unnormalized engine is a limiting case, not a discarded alternative. | **HOLDS for large finite σ** (σ = 1e300 recovers `σ=None` bit-for-bit). **FALSE at the literal limit**: `σ = float('inf')` computes `inf/inf = NaN`. DEFECT-C, §6.7. |
| single out-road | `competing = 0` ⇒ factor exactly 1.0 at **every** σ. A lone association is never attenuated, so absolute edge strength keeps its meaning in the F=1 case. | **FALSE on a clock that advances**, which is the library default: the road is read twice at different clock instants, so `competing ≈ 1.7e-9` and the factor is `0.99999999827341`. Exactly 1.0 only on a frozen clock. DEFECT-B, §6.5. |
| σ finite, competing > 0 | Strictly attenuating, strictly decreasing in `competing`. | **HOLDS**, property-based (§6.6). |
| σ has units of strength | It is *"the competing conductance at which a road's transmission is halved."* One constant, one reading. | Unchanged as a reading of the constant. σ stays uncalibrated and nothing downstream may depend on its value (§8 item 2). |

One numerical point the original table did not state, and should have: `competing` is computed as
`S_out − strength(this road)`, which is **not** bit-identical to the exact sum of the *other* roads.
It carries a residue of up to 1 ULP of `S_out`. For a lone out-road that residue is exactly zero,
which is why the single-out-road row is sound *in principle* and fails only through DEFECT-B.

This follows the project's established gated-overlay discipline exactly: `broadcast=False`
(1d-ii) and `body_sensor=None` (2c) both ship as default-off parameters whose neutral value
is byte-identical. `normalization_sigma=None` is the third instance of the same pattern, so
**1c / 1d / 2c do not require re-validation to land the parameter.** They require
re-validation only if and when the default is flipped, which is a separate decision and a
separate brick.

Rejected alternative — hard out-degree division (`outgoing = node_act / len(out_roads)`,
the ACT-R `S − ln(fan)` shape). It discards edge-strength information (all out-roads share
equally regardless of strength), it has no neutral value so it cannot ship as an overlay,
and it forces immediate re-validation of everything. The divisive form is a strict
generalization; hard division is a replacement.

---

## 3. Pre-check result 1 — the fan effect

Reproduces `experiments/fan_effect.py`'s star stimulus exactly: source S, F equal-strength
out-roads at `STRENGTH_COUNT = 3`, readout at T1, activation knobs at library defaults.

**σ fixed at 1.0, on principle, before any fan number was computed.** The principle: 1.0 is
the maximum strength a single saturated road can carry, so σ = 1.0 reads as *"transmission
halves when the competing conductance equals one fully saturated road."* It is not derived
from fan data and was not adjusted after seeing the sweep.

```
normalization OFF (σ = None)                normalization ON (σ = 1.0)
  F   activation @T1      spread              F   activation @T1        spread   ratio
  1   0.2433743975        0.0                 1   0.2433743975          0.0      1.000000
  2   0.2433743975        0.0                 2   0.1770739779623022    0.0      0.727578
  4   0.2433743975        0.0                 4   0.11462263603326847   0.0      0.470972
  8   0.2433743975        0.0                 8   0.06721276407449465   0.0      0.276170
 16   0.2433743975        0.0                16   0.03678388392602261   0.0      0.151141
  FLAT: True                                   FLAT: False
  DECREASING IN FAN: False                     STRICTLY DECREASING IN FAN: True
```

The OFF column reproduces the recorded `0.2433743975` flat baseline to the last digit,
which validates the probe against `experiments/results/fan_effect_output.txt`. The ON column
is strictly monotone decreasing in fan. Target spread is 0.0 at every level, so the
symmetry control from the 2A characterization still holds.

`SPEC-fan-effect`'s pre-registered prediction was directional — *"Retrieval strength
DECREASES as source fan (out-degree) increases"* — and it is met, at a σ chosen before the
measurement.

**Honest limitation on the functional form.** The falloff here is hyperbolic,
`1/(1 + (F−1)·s/σ)`, not Anderson's logarithmic `S − ln(fan)`. Direction matches; shape does
not. These are distinguishable against human latency data, and any future graded fan run
must pre-register which it is testing. Reporting "the fan effect appears" without that
qualifier would be an overclaim.

---

## 4. Pre-check result 2 — what this does to the 1e wall

`EXP-1e` recorded the priming NO-GO as a **thin leverage stratum**: `N_S0 = 7 < 30`, where
S0 is the set of primes whose HIGH/LOW targets tie on the strength→weight ladder, so that
*"the bare-weight baseline predicts exactly zero HIGH−LOW separation for these primes."*

A mechanism-existence probe on a synthetic graph — **no SWOW data, no graded number, no
cognitive claim** — asks a prior question the record does not address: *can a weight-tied
pair separate at all?* The P→T edge is held byte-identical at `traverse_count = 3` while the
prime's **other** associations vary:

```
 other assocs   activation @T, OFF      activation @T, ON (σ=1.0)
            0   0.2433743975            0.2433743975
            1   0.2433743975            0.1770739779623022
            3   0.2433743975            0.11462263603326847
            7   0.2433743975            0.06721276407449465
           15   0.2433743975            0.03678388392602261
           31   0.2433743975            0.0
  OFF: 1 distinct value  (spread 0.0)
  ON : 6 distinct values (spread 0.243374)
```

**The finding, stated carefully.** On the direct-edge path, with normalization off,
weight-tied is activation-tied **by construction** — the substrate builds strength from
`traverse_count`, and `W` is a function of `traverse_count`, so two edges that tie on the
ladder are the same edge strength and transmit identically. The direct-edge component of a
weight-blind pair therefore contributes **exactly zero** separation, at any `N_S0`.

This means 1e was foreclosed twice over, and only one of the two reasons is on the record.
`N_S0 = 7` is the recorded reason. The unrecorded one is that the stratum the design was
built to exploit had no *direct-path* signal in it to begin with; whatever separation 1e
could have found had to come entirely from indirect paths and the broadcast Δ — a much
weaker channel than the design's leverage argument assumed.

**Two caveats, both load-bearing.** (i) The probe graph is a star with no multi-hop
structure. On the real SWOW graph, targets do receive activation via indirect paths, so real
S0 pairs would not be *exactly* tied — the honest claim is about the direct-edge component,
not about total activation. (ii) This says nothing about whether priming is present. It says
the instrument, as configured, could not have resolved it.

With normalization on, target activation becomes a function of the prime's whole
out-neighbourhood, which the bare-weight map does not encode. That is precisely the
"value added over the bare-weight baseline" that §6.2's gate was written to detect.

**This must not be used as the motivation.** §1 is the justification; this is a downstream
consequence, recorded because a future 1e re-spec needs to know it. A re-spec would also
need a fresh pre-registration, a fresh stratum definition (weight-tied *and*
out-conductance-differing), and a fresh anti-circularity argument, because
out-conductance is itself derived from SWOW — the coupling is reduced, **not** removed.

---

## 5. The open decision — σ does not survive contact with SWOW scale

This is the reason this spec is a GO on mechanism and not a GO overall.

`floor = DEFAULT_FLOOR = 0.02`. Under normalization, activation magnitudes shrink with
source out-degree, so an **absolute** floor becomes degree-dependent censoring:

```
σ FIXED at 1.0                        σ SCALED to the source (σ = S_out)
 out-deg  activation @T   silenced      out-deg  activation @T
       0  0.2433743975                        0  0.2433743975
       2  0.13916298752267428                 2  0.1460246385
       5  0.08473712147068145                 5  0.13274967136363636
      10  0.05129912199504176                10  0.12748182726190477
      20  0.028671264859762857                20  0.12465517920731709
      50  0.0             YES                 50  0.1228920225
     114  0.0             YES                114  0.1222185838973799
     200  0.0             YES                200  0.12199065809850373
```

SWOW has ~114 mean out-degree per cue (1,388,741 edges / 12,217 cues). **At σ = 1.0 the
majority of SWOW cues would transmit nothing at all** — the graph goes dark. The fan sweep
alone would not have caught this; it only runs to F = 16.

Scaling σ with the source's own conductance is scale-free and never silences, but the
falloff **saturates**: past out-degree ~10 the curve is essentially flat
(0.1275 → 0.1220 from 10 to 200). Algebraically, for equal roads
`factor = c / (c + 1 − 1/F)`, which is bounded below by `c/(c+1)` — the fan gradient is
capped, and most of it is spent between F = 1 and F = 2. Sharpening it with a smaller `c`
makes the F = 1 → 2 drop steeper without extending the graded range.

**Three candidate resolutions. This is Cagan's call, and the discipline says the principle
comes before the data.**

1. **σ fixed, floor revisited.** Keep σ = 1.0 on its stated principle and treat `floor` —
   already a named uncalibrated constant — as the thing that was implicitly assuming an
   unconserved engine. Cost: `floor` governs the spreading horizon, which touches 1c
   (reachability), 1d (which members exist to prune), and 2c (the modulation acts on
   `decay_per_hop`). Largest re-validation surface, cleanest principle.
2. **σ ∝ S_out.** Scale-free, no silencing, no floor change. Cost: the fan gradient is
   capped and mostly spent by F = 2, so the fan effect exists but weakly, and a graded fan
   run against human data would likely fail on shape.
3. **σ ∝ S_out^β, 0 < β < 1.** Graded falloff without silencing. Cost: a **new free
   parameter with no principled value**, which is the failure mode the project's constant
   discipline exists to prevent. Should not be adopted unless β has a justification that
   is not "it makes the curve look right."

**Two empirical corrections from the tester's suite (2026-07-25), both sharper than this section
was.**

1. **The horizon does not taper, it cliffs.** The table above suggests a gradient. On
   equal-strength fans at σ = 1.0 and the default floor, the measured behaviour is a **step**:
   every target survives up to out-degree 16 and **none** survives from out-degree 32 onward
   (`(out_degree, reached)` = `(1,1) (2,2) (4,4) (8,8) (16,16) (32,0) (64,0) (128,0) (200,0)`).
   Equal-strength roads cross the floor together, so the censoring arrives all at once rather than
   thinning gradually. The silencing is at least **observable** — the result is an empty flow with
   the seed still present and no exception (N-9) — but any floor design in brick 2 must reckon with
   a cliff, not a slope.
2. **The default flip is not a one-line change.** The overlay is **not plumbed past
   `spread_activation`**: `build_activation_field()` and `think()` have no `normalization_sigma`
   parameter, so no downstream consumer (field, coalitions, workspace) can enable it today. That is
   consistent with default-off, and it usefully bounds the blast radius of DEFECT-B and DEFECT-C to
   direct `spread_activation` callers. But it also means flipping the default requires **plumbing
   the parameter through the field builder first**, and that plumbing is itself a re-validation
   surface for **1a, 1b, 1c and 1d** — a larger surface than §7's "1c and 1d" wording assumed.

**Recommendation: (1), and treat the floor as the second brick of this spec rather than a
side effect.** The floor's current value predates conservation; under conservation an
absolute activation floor is not scale-invariant, and scale-invariance is a property the
project already treats as load-bearing everywhere else (1c's relative proximity threshold,
1d-i's parameter-free watershed). A relative floor is the same argument applied one layer
down. But this changes the spreading horizon, and the horizon is what 1c and 1d were
verified against — so it is a real cost and it is the human's to accept.

---

## 6. Invariants — the verification record

This section was written as a list of things to check. It is now the **record of what was
actually checked, by whom, in what environment, and what the answer was.** The invariants are
restated in place so the claim and its adjudication sit together.

### 6.0 Provenance and verdict

| | |
|---|---|
| Suite | `tests/test_tester_0b2_adversarial.py` — written independently in the tester lane, from the invariants below, **not** adapted from the builder's suite. `src/` untouched. |
| Result line | 83 assertions, 0 failures. |
| Environment | Identical on **CPython 3.10.17, 3.11.15, 3.12.4, 3.13.14 and 3.14.4**, hash seeds swept **{0, 1, 2, 3, 7, 42}**, Darwin 24.5.0 arm64. |
| **Verdict** | **FAIL.** Seven of nine invariants hold. **N-2 fails** (DEFECT-A) and **N-5 fails** (DEFECT-B); **N-7 holds only for finite σ** (DEFECT-C). |

**The passing count is not the verdict.** All three defects ship as **asserted negatives**, per
CONTRIBUTING.md's definition of done: each test passes *while the defect is present* and turns red
deliberately the moment the defect is fixed, so a fix must come back through this suite and
re-verify the property it restores. The suite prints the verdict as a banner at the end of its
output, and the banner — not the `83 passed` line — is the finding.

**Attribution matters more than the count.** Of the three defects, **one is inherited** from 0b and
neither caused nor fixed by this change (DEFECT-A), and **two are this change's own** (DEFECT-B,
DEFECT-C). The overlay's own core arithmetic — the conductance sum, the attenuation factor, its
monotonicity, its treatment of closed roads — is sound.

### 6.1 N-1 neutral byte-identity — **PASS**

*Claim: with `normalization_sigma=None`, output is byte-identical to the pre-change engine, under
attack.*

Verified against **two independent oracles**, which is stronger than the invariant asked for:

- the **actual pre-change engine recovered from git** (resolved by content — the newest revision of
  `src/nous_activation.py` with no `normalization_sigma`): **17,017 adversarial comparisons, 0
  mismatches**;
- an **independent reimplementation of the documented algorithm**: **15,554 comparisons, 0
  mismatches**.

Adversarial surface: self-loops, cycles, duplicate pairs, high-degree fans, closed and traumatic
roads, decayed and saturated strengths, crossed with a parameter sweep. Comparison is on **full bit
patterns** of `activation`, `hops`, `broke_through` and `flow`, **including dict order**. Also
verified: the *default* argument equals an explicit `None` (so the neutrality is in the signature,
not only in a call site), and identity holds **loop-closed** on a substrate built by `traverse()`
with seeds chosen by `perceive()`.

> **Scope note that belongs in the record.** Byte-identity is asserted under a **frozen simulated
> clock**. On a moving clock any two runs differ through 0a's lazy decay alone, so the property
> cannot be stated unconditionally. That is a property of lazy decay, not of this overlay — but a
> reader who takes "byte-identical to the current engine" as unconditional would be misreading it.

### 6.2 N-2 determinism — **FAIL · DEFECT-A · inherited from 0b**

*Claim: byte-identical output across separate processes under `PYTHONHASHSEED ∈ {0,1,2,3,7,42}` in
fresh interpreters, and across every CPython minor version available.*

Determinism holds bit-exactly across six hash seeds × five interpreters **on graphs whose nodes
have in-degree ≤ 2**. It **breaks when three or more contributions converge on one node**:

```
activation[target] = activation.get(target, 0.0) + transmitted     # src/nous_activation.py:287
```

is a naive sequential float add, and the term order comes from
`roads_from() -> iter(tuple(self._out[node_id]))` — iteration over a **set of uuid4 hex strings**
(`src/nous_store.py:444`). Float addition is not associative, so the accumulated sum is
run-dependent. This is the **same bug class as BUG-0b1, one layer upstream** of the
coalition-strength site that `math.fsum` fixed.

Reproduction, **at library defaults**, on a 5-node graph built with `traverse()` alone
(S → M0, M1, M2 → T; traverse counts (1,2), (1,3), (1,9)): **48 fresh processes produced two
distinct results**, `0.10145973529004966` and `0.10145973529004967`. It reproduces identically with
the overlay **off**, which is the scoping evidence: **0b2 did not cause it and does not fix it.**

Two methodological findings the record must carry, because they change how determinism is checked
in this project:

1. **It varies at a fixed `PYTHONHASHSEED`.** uuid4 ids differ per process, so pinning the hash seed
   does not pin set-iteration order. **Seed-pinning alone cannot establish determinism for this
   substrate.**
2. **Every pre-existing determinism probe in `tests/` compares `round(x, 9)`**, which structurally
   cannot see a 1-ULP difference — and 1 ULP is exactly what BUG-0b1 was. The new suite compares bit
   patterns throughout.

### 6.3 N-3 purity — **PASS**

*Claim: `spread_activation` still mutates nothing; `S_out` is computed from decayed road views and
no `_persist_decay` path is entered.*

Substrate byte-identical (strength, charges, closure, `traversal_count`, `last_touched`) after
normalized spreads across **40 adversarial graphs**. A mutation-guard proxy proves no mutating store
method is ever called. Unchanged `last_touched` is the witness that `_persist_decay` is never
entered, so `S_out` is computed from decayed **views** only, exactly as the spec requires.

### 6.4 N-4 order-independence of `S_out` — **PASS, and the probe is proven non-vacuous**

*Claim: `math.fsum`, not `sum`; shuffle the out-road iteration order and require the identical
`S_out` bit pattern.*

Out-road iteration order was shuffled through a delegating store proxy and identical bit patterns
required: **all 120 orders of a 5-road star**, plus **25 random fans of out-degree 8..40 with 6
shuffles each** — one flow signature every time. `S_out`'s *value* is also pinned directly: every
road's transmitted activation equals `act·s·decay·σ / (σ + fsum(others))` to the bit.

**Sensitivity is itself a checked property.** A naive left-fold over the same strengths yields 2
distinct totals and 2 distinct transmitted values, so the test would catch a regression rather than
passing vacuously.

> **Caveat worth preserving.** Python's builtin `sum()` could **not** be used as the naive control,
> because CPython 3.12 changed `sum()` to Neumaier compensated summation for floats. Using it would
> have made the probe's sensitivity depend on the interpreter — which is the BUG-0b1 mistake itself.
> The control is an explicit sequential left-fold.

### 6.5 N-5 limiting case — **FAIL · DEFECT-B · introduced by 0b2**

*Claim (§2 property table row 3, and this invariant): a single out-road gives `competing = 0` and
therefore a factor of **exactly 1.0** at every σ.*

**This is false on any clock that advances — which is the library default**, `SubstrateStore()` with
`Clock(simulated=False)`. The overlay reads each road **twice** per expansion (once for `out_total`,
once inside the transmission loop), and `get_road` applies lazy decay as of `clock.now()` at each
call, so the two reads return different strengths and `competing = out_total − road.strength` is a
positive **elapsed-time residue** rather than zero.

Measured with a deterministic ticking clock at 1 µs per read, one road worn 3 times:

```
read #1 (out_total) strength = 0.37442215
read #2 (transmit)  strength = 0.37442214827340997
competing                    = 1.7265900376095544e-09     (spec requires exactly 0.0)
applied factor               = 0.99999999827341           (spec requires exactly 1.0)
```

The lone road is attenuated. More generally, **`competing` is contaminated by elapsed time for every
road**, so it is not the pure conductance sum §2 defines.

Why nothing caught it: every existing test uses `Clock(simulated=True)`, where `dt ≤ 0` makes lazy
decay a no-op. Confirmed 0b2-specific: the pre-change engine had exactly **one** `get_road` site
inside the expansion; the current one has two.

**Severity, stated plainly rather than dismissed as small.** ~2e-9 relative is roughly 1e9 ULP, and
BUG-0b1 established that **1 ULP** was enough to flip a workspace winner 8 times in 30.

### 6.6 N-6 monotonicity — **PASS**

*Claim: transmitted activation is strictly decreasing in `competing` and strictly increasing in σ.*

Both directions hold, and transmitted activation never exceeds the unnormalized value.
Property-based over 30 random adversarial graphs plus targeted fixtures.

### 6.7 N-7 σ → ∞ convergence — **PASS for finite σ · DEFECT-C at the limit · introduced by 0b2**

*Claim: as σ grows, output converges to the unnormalized result; the difference is monotone
decreasing in σ.*

The gap to the unnormalized engine is monotone non-increasing along a σ ladder, and **σ = 1e300
recovers `σ = None` byte-for-byte**. That much holds.

But `normalization_sigma` is **unvalidated**, and the spec's own wording is the trap:
`σ = float('inf')` — the exact value §2 describes as the one that "analytically recovers the current
engine" — computes `inf/inf = NaN`. **NaN passes the `transmitted < floor` guard**, because every
comparison with NaN is False, so NaN propagates into `activation` **silently, with no exception**.
`σ = nan` behaves likewise. `σ = 0` and `σ < 0` silence everything (the negative transmitted value
fails the floor guard) — but only while `floor ≥ 0`; with a negative floor, `σ = −1.0` produces
genuinely **negative activation**.

**A caller who follows this spec's own wording gets NaN.** That is a defect in the spec as much as
in the code, and §2 has been corrected accordingly.

### 6.8 N-8 closed roads compete — **PASS**

*Claim: closed roads contribute to `S_out` but transmit only their leaked fraction — a decision, not
an accident, asserted so a future change must argue with a test.*

Asserted with exact arithmetic **and against the excluded alternative**. Sharpest case confirmed: a
closed road **below the breakthrough threshold**, which transmits nothing and is absent from `flow`,
still consumes budget and attenuates the open road beside it. A leaking closed road is normalized
like any other.

> **Observability wart, recorded rather than hidden.** `broke_through` is appended **before** the
> floor guard, so it can list a road that is absent from `flow`. Normalization makes this markedly
> easier to reach, so any consumer reading `broke_through` as "intrusive recall happened" will
> **over-report**. This is not new in 0b2, but 0b2 widens it.

### 6.9 N-9 no silent silencing — **PASS**

*Claim: for a source whose out-degree pushes every target below `floor`, the result is observably
empty rather than quietly truncated.*

A source at out-degree 200 goes **observably** empty: `activation` is `{seed: energy}`, `flow` is
`{}`, `hops` is `{seed: 0}`, `ranked()` is `[]`, no exception, integrity intact, substrate
byte-identical. The same graph is **not** silent unnormalized, so the horizon change is visible as a
*difference* rather than hidden inside a truncated result.

Empirically sharper than §5's table: on equal-strength fans at σ = 1.0 and the default floor, the
horizon **cliffs rather than tapers** — every target survives up to out-degree 16 and none survives
from 32 onward, because equal-strength roads cross the floor together.

### 6.10 Structural findings outside the nine invariants

- **The overlay is not plumbed past `spread_activation`.** `build_activation_field()` and `think()`
  have no `normalization_sigma` parameter, so no downstream consumer can enable it. This bounds the
  blast radius of DEFECT-B and DEFECT-C to direct `spread_activation` callers — and it means the §5
  default flip needs plumbing through the field builder, a re-validation surface for **1a/1b/1c/1d**.
- **The parameter is keyword-only and defaults to `None`**, as the gated-overlay discipline requires.

---

## 7. Done means

**The mechanism brick is done** when: the overlay is present, N-1 through N-9 hold, the
canonical suite is unchanged at neutral on every available interpreter, and the delivery
report states plainly that no cognitive claim has been earned and that the default is off.

> **Status 2026-07-25: NOT met.** The overlay is present and the canonical suite is unchanged at
> neutral on all five interpreters, but **N-2 and N-5 do not hold and N-7 holds only for finite σ**
> (§6). The bar is not lowered to fit the result: 0b2 is `BUILT · UNVALIDATED` with its **mechanism
> bar open**, not tester-verified. Closing it requires, at minimum:
> **(a)** DEFECT-B fixed at its cause — the double read of each road inside one expansion — so that
> `competing` is a pure conductance sum and a lone out-road is attenuated by exactly nothing;
> **(b)** DEFECT-C resolved by a stated policy on σ's domain (validate and reject, or define
> `inf` explicitly as the neutral value), because the current behaviour contradicts §2's own text;
> **(c)** DEFECT-A adjudicated — it is 0b's, not 0b2's, so it is a *separate brick* and its status
> call belongs to Cagan (D-011), but 0b2's N-2 cannot pass while it stands;
> **(d)** the tester's suite re-run, with the three asserted-negatives flipping red and being
> rewritten as positive assertions of the restored properties.

**The default flip is a separate brick** and is done only when: the §5 decision is taken on
a stated principle recorded *before* any downstream number; the parameter is first plumbed through
`build_activation_field()` and `think()` (§6.10 — this was not anticipated when the sentence below
was written); 1a, 1b, 1c and 1d are re-verified under
the new default (not merely re-run — re-verified, tester lane, including 1c's merge and
no-stranding properties and 1d-i's watershed and anti-overcorrection controls); and the
re-validation report says which previously-passing properties changed and why.

**No cognitive claim is done by either brick.** The fan sweep in §3 is a mechanism
characterization on a synthetic star, not a graded behavioral result against human data.

## 8. Known limitations, to ship as asserted-negatives

1. **Hyperbolic, not logarithmic falloff.** Direction matches the fan effect; shape differs
   from ACT-R's. Assert the shape so it cannot be quietly claimed as an ACT-R replication.
2. **σ is uncalibrated.** Like `DEFAULT_PROXIMITY_FRACTION` and the broadcast gain, it is on
   probation. Tests pin the qualitative regime (monotone, bounded, neutral at None), never a
   magnitude. Nothing downstream may depend on σ's value.
3. **Degree-dependent horizon.** §5. Real, unresolved, visible by N-9 — and measured to be a
   **cliff, not a taper** (§6.9): every target survives to out-degree 16 and none from 32 on, at
   σ = 1.0 with the default floor on equal-strength fans.
4. **`S_out` is a per-expansion cost.** One extra pass over each expanding node's out-roads.
   Negligible on the current toy graphs; on SWOW-scale it doubles the road reads in the
   inner loop. It is cacheable per (node, decay epoch) if profiling ever demands it — not
   designed in now on speculation, per the Layer 1 rule.
   **Amended:** that second pass is not only a cost, it is the *cause* of DEFECT-B (§6.5) — the two
   reads happen at different clock instants. Any fix that reads each road once, or caches the
   decayed view for the expansion, removes both the cost and the defect. That is a design
   observation, not a decision; the decision is Cagan's (D-011).
5. **Conservation is per-source, not global.** A source shares its own budget across its own
   out-roads. There is still no *system-wide* activation budget, so this does not give the
   architecture a global capacity limit and must not be described as one.
6. **Neutral byte-identity is a frozen-clock property** (§6.1). On a moving clock, two runs differ
   through 0a's lazy decay regardless of this overlay. State it that way; "byte-identical to the
   current engine" without the qualifier over-reads the evidence.
7. **`competing` is `S_out − strength`, not the exact sum of the other roads** (§2), and carries a
   residue of up to 1 ULP of `S_out`. Exactly zero for a lone out-road.
8. **`broke_through` can list a road absent from `flow`** (§6.8), because it is appended before the
   floor guard. Normalization makes this easier to reach, so any consumer treating `broke_through`
   as "intrusive recall happened" over-reports. Pre-existing, widened here.
9. **σ's domain is unvalidated** (§6.7). Until DEFECT-C is resolved, `inf`, `nan`, `0` and negative
   values are all accepted and all misbehave, one of them silently.
