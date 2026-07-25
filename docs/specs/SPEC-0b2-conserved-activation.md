# SPEC-0b2 — Conserved activation: divisive normalization at the transmission site

**Status:** FEASIBILITY PRE-CHECK COMPLETE · **GO on the mechanism, ONE HUMAN DECISION OPEN**
**Revises:** 0b (spreading-activation engine, Tier 1 `PROVEN`)
**Depends on:** BUG-0b1 landed first (the summation-order fix). Non-negotiable — see §0.2.
**Date:** 2026-07-25
**Author lane:** architect-pm

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
both at once. **BUG-0b1 is a separate, prior brick.** It has been fixed and verified
(20 suites / 1,372 assertions / 0 failures on CPython 3.11, 3.12 and 3.13).

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

Properties of this form, all mechanical:

| Property | Consequence |
|---|---|
| `σ = None` | Byte-identical to the current engine. Verified: full suite unchanged. |
| `σ → ∞` | Analytically recovers the current engine (factor → 1). The unnormalized engine is a limiting case, not a discarded alternative. |
| single out-road | `competing = 0` ⇒ factor exactly 1.0 at **every** σ. A lone association is never attenuated, so absolute edge strength keeps its meaning in the F=1 case. |
| σ finite, competing > 0 | Strictly attenuating, strictly decreasing in `competing`. |
| σ has units of strength | It is *"the competing conductance at which a road's transmission is halved."* One constant, one reading. |

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

**Recommendation: (1), and treat the floor as the second brick of this spec rather than a
side effect.** The floor's current value predates conservation; under conservation an
absolute activation floor is not scale-invariant, and scale-invariance is a property the
project already treats as load-bearing everywhere else (1c's relative proximity threshold,
1d-i's parameter-free watershed). A relative floor is the same argument applied one layer
down. But this changes the spreading horizon, and the horizon is what 1c and 1d were
verified against — so it is a real cost and it is the human's to accept.

---

## 6. Invariants (the tester's lane)

The substrate bar applies in full, plus the overlay-specific properties:

- **N-1 neutral byte-identity.** With `normalization_sigma=None`, output is byte-identical
  to the pre-change engine, under attack. *(Verified: 20 suites / 1,372 assertions / 0
  failures, on CPython 3.11, 3.12 and 3.13.)*
- **N-2 determinism with normalization on.** Byte-identical output across separate
  processes under `PYTHONHASHSEED ∈ {0,1,2,3,7,42}` in fresh interpreters, **and across
  every CPython minor version available** — the coverage axis BUG-0b1 §6 adds.
- **N-3 purity.** `spread_activation` still mutates nothing. `S_out` is computed from decayed
  road *views*; no `_persist_decay` path is entered.
- **N-4 order-independence of `S_out`.** `math.fsum`, not `sum` — the same class of bug as
  BUST-0b1. Assert this directly: shuffle the out-road iteration order and require the
  identical `S_out` bit pattern.
- **N-5 limiting case.** For a graph where every source has exactly one out-road, output is
  identical with normalization on and off, at every σ.
- **N-6 monotonicity.** Transmitted activation is strictly decreasing in `competing` and
  strictly increasing in σ. Property-based, on randomly generated graphs.
- **N-7 σ → ∞ convergence.** As σ grows, output converges to the unnormalized result;
  assert the difference is monotone decreasing in σ.
- **N-8 closed roads.** Closed roads contribute to `S_out` (they are still connections) but
  transmit only their leaked fraction. This is a decision, not an accident — assert it, so a
  future change has to argue with a test rather than with a comment.
- **N-9 no silent silencing.** For a source whose out-degree pushes every target below
  `floor`, the result must be observably empty rather than quietly truncated. A degree-
  dependent horizon is acceptable only if it is visible; see §5.

## 7. Done means

**The mechanism brick is done** when: the overlay is present, N-1 through N-9 hold, the
canonical suite is unchanged at neutral on every available interpreter, and the delivery
report states plainly that no cognitive claim has been earned and that the default is off.

**The default flip is a separate brick** and is done only when: the §5 decision is taken on
a stated principle recorded *before* any downstream number; 1c and 1d are re-verified under
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
3. **Degree-dependent horizon.** §5. Real, unresolved, and visible by N-9.
4. **`S_out` is a per-expansion cost.** One extra pass over each expanding node's out-roads.
   Negligible on the current toy graphs; on SWOW-scale it doubles the road reads in the
   inner loop. It is cacheable per (node, decay epoch) if profiling ever demands it — not
   designed in now on speculation, per the Layer 1 rule.
5. **Conservation is per-source, not global.** A source shares its own budget across its own
   out-roads. There is still no *system-wide* activation budget, so this does not give the
   architecture a global capacity limit and must not be described as one.
