# SPEC-fan-effect — Anderson's fan effect as the re-routed primary meaning bar

Status: **FEASIBILITY PRE-CHECK COMPLETE → NO-GO (structurally infeasible on this substrate).** This document
leads with a **gating** feasibility pre-check (§1), as instructed. The pre-check is answered **NO**: the fan
effect is **not testable on this substrate as built**, for a reason **different from** the 1e priming NO-GO. 1e
failed on **anti-circularity** (the prediction variable, SWOW strength, *is* the edge weight). The fan effect
fails on a more basic ground — **the generating mechanism of the fan effect does not exist in this engine** —
and this is **not** a provisional, population-uncertain finding but an **already-proven** property of the frozen
substrate. Per the instruction's second ending, the verdict is stated explicitly and the design **stops here**;
the full graded experiment is **not** written. A pivot to **interoception (2c)** is recommended (§4).

Author: architect-pm
For: the human (a direction decision) and, if the recommendation is accepted, the validator (who would own a
2c meaning experiment). This document writes **no code**, runs **no code**, and asserts **no** built or proven
artifact. It is `DESIGNED`-tier analysis only.
Depends on (read): Phase 2A fan-effect characterization (`experiments/fan_effect.py`, `experiments/FAN_EFFECT.md`,
`experiments/EXPERIMENT_NOTES.md` STEP 0 — all tier-3 disciplined-exploratory, captured verbatim in
`experiments/results/`); the closed loop `select_winner` / `broadcast` (`src/nous_workspace.py`); the frozen
spreading-activation engine (`src/nous_activation.py`); the 1e NO-GO (`docs/specs/SPEC-1e-priming.md` §14,
`docs/experiments/EXP-1e-priming.md` §15).

> **Scope discipline (CONTRIBUTING.md rules 1–5).** This is **description and analysis, not a result.** `PROVEN` and
> `DESIGNED` stay in separate boxes. Nothing here is built. The one empirical claim this document *leans on* —
> "the engine does not normalize by out-degree, so the fan curve is flat" — is **not authored here**; it is the
> Phase 2A result, captured verbatim in `experiments/results/fan_effect_output.txt` and
> `experiments/results/step0_probe_output.txt`, at the disciplined-exploratory tier. No mechanism status is
> changed by this document: 1c and 1d stay `BUILT · UNVALIDATED`; Phase 0 stays `PROVEN`; no brick is reopened.

---

## 1. FEASIBILITY PRE-CHECK (GATING — answered before any experiment is designed)

**The one question (verbatim from the directive):** *Does measuring the fan effect on THIS substrate — through
the closed loop — avoid the structural coupling that killed 1e?*

**Short answer: it avoids 1e's *specific* coupling, but it hits a different, harder wall that forecloses the
test before circularity is even reached. NO-GO.**

The pre-check has three parts, exactly as the directive frames them. I answer each, then state the gate verdict.

### 1.0 What killed 1e, restated precisely (so I test against the right failure)

1e's killer was **identity of the prediction variable with the mechanism**: SWOW R123.Strength is encoded
*as* the integer edge weight via `W = min(10, 1 + floor(strength·100))` (`swow.traverse_count_for_strength`).
So "related" and "strong-weight" were the **same number**. The anti-circularity gate demanded a **weight-blind
stratum S0** — pairs where HIGH and LOW bands tie on weight — so a HIGH>LOW result could not be the weight map
read straight back out. But the saturating ladder sends HIGH to a strictly higher integer than LOW almost
everywhere, so **N_S0 = 7 < 30** and the all-primes fallback's value-added headroom was arithmetically ~0.027
< 0.20 (`r_W ≈ 0.97`). The gate fired **at selection time, before any graded number** (EXP-1e §15.3–15.4).

The lesson I carry forward (and the directive insists on): **structural optimism over-predicted feasibility for
1e.** Reasoning said S0 would populate; the blind run said N_S0 = 7. So any feasibility claim I make from
reasoning alone is **provisional** and would need an empirical confirmation run — *unless* the blocker is a
property that is **already empirically established**, in which case no new run is needed to know the answer. The
fan-effect blocker is exactly that already-established kind (see §1.1).

### 1.1 Part 1 — State the fan effect precisely, with prior art

**The phenomenon (Anderson's fan effect).** In Anderson (1974) and the ACT / ACT-R memory literature, the time
to verify or retrieve a fact about a concept **increases with the number of facts associated with that concept**
— the concept's **fan** (its number of associations). A person who has learned three facts about "the lawyer"
is **slower** to verify any one of them than a person who learned only one. The established direction is
**unambiguous: higher fan → slower / weaker retrieval of any single associated fact.**

**The ACT-R mechanistic account (why it matters here).** ACT-R explains the fan effect by **spreading
activation under a *fixed, shared* source activation budget**: a concept emits a *bounded* amount of source
activation that is **divided among its associations** (in the standard ACT-R equation, the strength of
association `S_ji` from source `j` to chunk `i` falls as `j` fans out — `S_ji ≈ S − ln(fan_j)`). More fan →
each association receives a **smaller share** → lower activation at any one target → slower retrieval. **The
fan effect is, mechanistically, a *capacity-division / normalization* effect: it exists only because the source
activation is a shared, conserved quantity split across out-edges.**

**Prior art (cited; this is the phenomenon and the mechanism, NOT evidence Nous reproduces it):**
- **Anderson, J. R. (1974).** "Retrieval of propositional information from long-term memory." *Cognitive
  Psychology* 6(4), 451–474. — the original fan effect. *Establishes:* the human **direction** (higher fan →
  slower retrieval).
- **Anderson, J. R. (1983).** *The Architecture of Cognition.* Harvard Univ. Press; and **Anderson & Reder
  (1999),** "The fan effect: New results and new theories," *J. Exp. Psychol. General* 128(2), 186–197. —
  *Establishes:* the **spreading-activation-under-shared-budget** explanation (fan divides a conserved source
  activation).
- **Anderson, J. R., & Lebiere, C. (1998).** *The Atomic Components of Thought* (ACT-R). — *Establishes:* the
  formal `S_ji ≈ S − ln(fan)` association-strength equation that makes the fan effect a **normalization**
  effect by construction.
- **(Bridge / boundary)** the human effect is a **latency** (reaction-time) effect; Nous has no latency, only
  activation magnitude. The Phase 2A study fixed the bridge in advance (`FAN_EFFECT.md`): **higher activation =
  faster/stronger retrieval**, so the human "slower with higher fan" maps to the Nous prediction **"lower
  activation with higher fan."** This bridge is an assumption, stated so it can be challenged.

**What the literature establishes vs. what Nous would be testing.** The literature establishes that *humans*
show a fan effect and that its mechanism is **division of a shared activation source across associations.** Nous
would be testing only whether *its* activation magnitude **decreases** as a source's out-degree (fan) rises,
under matched edge strength and distance — the magnitude analogue of the human latency direction. A match would
be "the direction is reproduced," never "Nous retrieves the way a person does."

### 1.2 Part 2 — Is there a clean, well-populated stratum separating the fan prediction from a mechanical readback? (assessed BOTH ways, honestly)

The directive asks me to assess two opposite possibilities. I do both, then report which is true.

**(2a) The optimistic read — is fan structurally *cleaner* than priming?** On the surface, **yes, and this is
real**: the fan prediction rides on the **NUMBER of edges (out-degree / fan)**, which is a **different axis**
from the **weight of any one edge**. In 1e, prediction and mechanism were the *same* number; for the fan effect,
out-degree and edge weight are **distinct, separable graph properties** — one can hold edge strength and
distance fixed while varying only fan (exactly what `star_spec` does). So the fan effect **does avoid 1e's
specific strength=weight coupling.** If the only worry were "is the fan axis entangled with the weight axis the
way strength was," the answer would be: **less entangled — fan is the cleaner axis.** The directive's first
sub-question is answered **in the fan effect's favor.**

**(2b) The fatal read — does the generating mechanism even exist on this substrate?** Here the pre-check turns,
and this is the load-bearing finding. **The fan effect's generating mechanism — division of a shared source
activation across out-edges — is PROVABLY ABSENT from this engine.** This is not a conjecture; it is the
**Phase 2A result, already run, captured verbatim, and explained mechanistically:**

- `src/nous_activation.py`, inside `spread_activation`, feeds **each** out-road the source's **FULL** activation:
  `outgoing = node_act`, then `transmitted = outgoing × road.strength × decay_per_hop`. There is **no
  `/ len(out_roads)`**, no per-source energy budget, no division of the source's activation among its out-edges
  (`EXPERIMENT_NOTES.md` STEP 0, reading the frozen engine).
- The empirical confirmation is exact and verbatim (`results/step0_probe_output.txt`,
  `results/fan_effect_output.txt`): a source's out-degree 1 vs 8 gives a target the **byte-identical** activation
  `0.2433743975`, and the full sweep over fan ∈ {1, 2, 4, 8, 16} is **flat to the last digit**:

  ```
  RESULT — fan F vs mean activation at target T1
      F   mean target activation      spread (max-min)
      1   0.2433743975                0.0
      2   0.2433743975                0.0
      4   0.2433743975                0.0
      8   0.2433743975                0.0
     16   0.2433743975                0.0
  VERDICT:
    DOES NOT MATCH: activation is flat across fan — the engine does not normalize by out-degree.
  ```

So the question "**is there a stratum where the fan prediction separates from a mechanical readback?**" gets an
answer that is *worse* than 1e's: in 1e a mechanical readback **predicted the right direction** (the gate was to
prove the loop *added value over* that readback). For the fan effect there is **no readback predicting anything
in either direction** — the substrate's response to fan is **identically flat.** There is no stratum where the
loop produces a fan effect, because **the loop produces no fan-dependence at all.**

**Does a *similar* coupling resurface (the directive's named risk)?** I checked for the inverse worry — that
high-fan nodes might correlate with in-degree / weight / frequency artifacts so that a *spurious* "high fan →
lower activation" could appear as a mechanical topology readback. **It does not arise**, because the substrate
produces **no fan-dependence to be spurious about**: the readout at a target is a pure function of *its own*
incoming edge strength and *its own* path distance, and is **independent of the source's out-degree** by
construction. There is neither a genuine fan effect nor a confounded one — there is a **flat line**. (On real
SWOW one *could* manufacture an apparent fan slope by failing to hold edge strength constant — high-fan cues
tend to have weaker individual edges — but that would be reading the **weight** axis, i.e. 1e's confound wearing
a fan costume, and the honest controlled design holds edge strength fixed, which returns the flat line.)

### 1.3 Part 3 — Define the anti-circularity gate analogous to S0, and pre-estimate population

The S0-analogue for a fan experiment would be a **fan-blind / mechanism stratum**: a set of conditions where a
**mechanical readback predicts no fan effect**, so that any fan effect the closed loop produces there must come
from real closed-loop dynamics (competition / normalization / broadcast), not from topology. The honest
pre-estimate of whether that stratum populates:

> **The fan-blind stratum is not merely under-populated — it is the ENTIRE space.** Because the engine produces
> a **flat** fan response everywhere (the mechanical prediction is "no fan effect" for **every** fan level, on
> **every** topology, proven to the last digit), the locus where "a mechanical readback predicts nothing" is
> **100% of conditions.** And a fan effect produced *there* would have to come from a closed-loop dynamic — but
> the closed loop, as built, **has no such dynamic** (see §1.4). So the gate's stratum is maximally populated
> and **the loop produces nothing in it.** This is the mirror image of 1e: 1e's leverage stratum was **empty**
> (N_S0 = 7), so the gate could not be applied; here the leverage stratum is **everything**, and the gate is
> applied trivially and **fails** — the loop adds no fan-dependence over the flat mechanical baseline.

**Discipline check (the 1e lesson applied).** For 1e, structural optimism over-predicted feasibility and only
the **empirical** blind run revealed N_S0 = 7 — so a feasibility claim there required an empirical confirmation
run. **Does the fan NO-GO need an analogous empirical confirmation run before it can be trusted?** **No** — and
this is the crucial asymmetry. The fan blocker is **already the subject of a completed empirical run** (Phase
2A): the flat curve is not a prediction I am making from structure, it is a **measured, captured, verbatim
result** with a mechanistic cause read directly from the frozen engine. The thing an empirical selection-run
would establish for the fan effect (*does the substrate respond to fan?*) is **already established, and the
answer is no.** So unlike 1e — where I would temper a "looks testable" conclusion with a recommended blind
selection-run — here the empirical evidence already exists and points the other way. There is **nothing left to
confirm**: a confirmation run would re-measure the flat line.

### 1.4 The closed-loop check (does 1d's competition/broadcast rescue it?)

The directive asks specifically about the fan effect **through the closed loop**, not the bare engine the 2A
study used. I checked whether 1d-i competition or 1d-ii broadcast introduces any out-degree sensitivity the bare
engine lacks. **They do not:**

- **1d-i competition** (`src/nous_workspace.py`, `_density_score`) scores coalitions by
  **`total activation / max(coalition_size, guard)`** — normalization by **coalition SIZE**, not by source
  **out-degree/fan**. Fan does not enter the competition key. A target's activation, which feeds coalition
  strength, is still the fan-independent value from the bare engine.
- **1d-ii broadcast** (`broadcast`) strengthens the **winner's internal roads** by a fixed fractional gain
  (`strengthen`'s `g·(1−strength)`), once each. There is **no out-degree term**; the magnitude depends on
  current strength, not on how many associations the source has.

So the closed loop inherits the bare engine's **flat fan response** and adds no fan-dependence of its own. The
fan effect is **not** rescued by closing the loop. (This is consistent with `FAN_EFFECT.md`'s "Implication for
the priming study": a competition/fan contrast reads flat under this engine; only edge-strength and distance
contrasts register — and edge-strength is exactly the 1e axis that was too coupled to grade.)

### 1.5 GATE VERDICT

> **NO-GO. The fan effect is structurally infeasible on this substrate as built — not for 1e's anti-circularity
> reason, but because the mechanism that *generates* the fan effect (division of a shared source activation
> across out-edges) does not exist in the frozen engine, which is PROVEN to produce a fan response that is flat
> to the last digit at every layer (bare engine and closed loop alike). The anti-circularity stratum is not the
> blocker here; the blocker is upstream of it — there is no fan-dependent signal to grade, circular or
> otherwise.**

**This is the directive's second honest ending** ("entangled on this substrate" → say so and stop). I note one
precise nuance, because honesty requires it: the fan effect is not *entangled* the way priming was — it is
**absent**. The directive's three landings map as follows, and I pick the correct one without splitting the
difference:

- *Testable (clean stratum that plausibly populates)* → **NO.** There is no fan signal to grade.
- *Structurally entangled the way priming was* → **NOT exactly**; the fan axis is actually *cleaner* than the
  strength axis. But the experiment is still foreclosed, for the stronger reason that the effect is **not
  produced at all.**
- *Plausible but population-uncertain, gated on an empirical run* → **NO.** This landing is explicitly for when
  reasoning *looks* feasible and only a run can confirm. Here the run **already exists** (Phase 2A) and confirms
  **infeasibility**. Recommending a fresh confirmation run would be theater — it would re-measure a flat line
  already captured verbatim.

Because the gate is NO-GO, **the full graded fan experiment is NOT designed below.** §2 records what a faithful
fan experiment *would* have required (so the reasoning is preserved and auditable), §3 states what would have to
change about the **engine** for a fan effect to become testable (and why that is out of scope / forbidden by the
discipline now), and §4 recommends the pivot.

---

## 2. What a faithful fan experiment would have required (recorded, NOT built — for the audit trail)

Preserved so the NO-GO is a reasoned refusal, not a gap. A faithful fan-effect meaning experiment would need:

1. **An external yardstick the project did not author.** The clean choice is the **ACT-R fan-effect human data
   / published fan-set norms** (Anderson 1974; Anderson & Reder 1999 give the canonical person/location fan
   materials and the latency direction). The direction (higher fan → slower → *lower activation* under the
   bridge) is fixed in advance from that literature, never from us.
2. **A fan manipulation holding everything else constant** — exactly `star_spec`: one source, F equal-strength
   out-roads, read a designated symmetric target, vary only F. The 2A harness already does this correctly and
   is the instrument that would be reused (CONTRIBUTING.md rule 6).
3. **The anti-circularity / loop-work gate (the S0 analogue):** a stratum where a mechanical readback predicts
   no fan effect, in which a closed-loop fan effect must reflect competition/normalization/broadcast. **This is
   precisely the gate that the pre-check shows fails trivially**: the mechanical prediction is "flat" everywhere,
   and the loop produces "flat" there too.
4. **The pre-registered direction + effect size + falsifier**, frozen before any number, with the verdict
   computed from data. The 2A study already pre-registered the direction and **computed the falsifying verdict
   from data** (`fan_effect.py::verdict` → "DOES NOT MATCH: activation is flat"). A 1e-grade re-run **through
   the closed loop**, graded against external fan norms, would return the **same** flat result for the same
   mechanistic reason, now with the loop confirmed (§1.4) to add nothing.

The honest summary of this section: **the experiment is already, in substance, answered.** The Phase 2A
characterization *is* the fan-effect result at the bare-engine level (a pre-registered, falsified-as-flat null
with a mechanistic cause); the closed-loop analysis (§1.4) shows the loop does not change it. Re-dressing it as
the headline meaning bar would convert a **null** into the project's primary cognitive claim — which is exactly
backwards: a flat fan curve is the *absence* of the targeted effect.

---

## 3. Why this is an ENGINE property, not an experiment-design problem (and why that closes the door now)

The reason the fan effect cannot be made to appear by a cleverer experiment is that it is a property of the
**frozen engine**, not of the stimulus selection:

- The human fan effect **requires** a conserved, shared source activation divided across out-edges (the ACT-R
  `S − ln(fan)` normalization). The engine deliberately has **no such conservation** — each out-road gets the
  source's full activation. This was a **design choice** of Phase 0, verified and documented, not an oversight.
- To make a fan effect testable, one would have to **change the engine** — e.g. divide a source's activation
  among its out-roads (`outgoing = node_act / len(out_roads)`), or impose a per-source activation budget. That
  is a **Phase 0 substrate change**, which:
  - is **out of this step's lane** (the PM does not modify the engine; that is the builder's, and only on an
    approved spec);
  - would be a **substantial cognitive-architecture decision** (normalization changes the meaning of *every*
    activation result the project has, including 1c/1d), so it is a **human call**, not an agent's;
  - and crucially, **would not be "reproducing" the fan effect** in any earned sense if the normalization were
    added *in order to* produce it — that is engineering the answer into the mechanism (the cousin of the
    circularity bug). A fan effect would only be meaningful if normalization were adopted for an *independent*
    architectural reason and the fan effect then **fell out** as an untuned consequence.

So the door is closed on **two** independent grounds: (a) as the engine stands, the effect is provably flat; and
(b) the only way to open it is an engine change that is a human-level architecture decision and that, if made
*to get the effect*, would not earn it anyway.

---

## 4. RECOMMENDATION — pivot the primary meaning bar to interoception (2c)

**Recommendation: do not take the fan effect as the re-routed primary meaning bar. Pivot to interoception (2c).**

**Why (one paragraph, as the directive asks).** The project now has **two** re-routes that both dead-end inside
the *association/activation-magnitude* family: semantic priming (1e) is infeasible on SWOW because the
prediction variable **is** the edge weight (anti-circularity); the fan effect is infeasible because its
generating mechanism (shared-budget normalization) **is not in the engine** (a proven flat curve). These are
two different walls, but they share a root: **every "meaning" claim drawn from spreading activation over a
SWOW-weighted graph is either a readback of the weights the graph was built from, or an effect the engine
structurally cannot produce.** Interoception (2c) escapes this family entirely. Its signal source is **real
machine telemetry** (compute load, I/O pacing, memory pressure, elapsed time, interruption) — **external to the
substrate and not derived from SWOW or from any edge weight**, so it is **immune to both the 1e coupling and the
fan-mechanism absence.** Its "done means" is also cleaner and already well-formed in the roadmap: *the signals
are genuinely derived from live telemetry (not faked) and demonstrably **modulate** the cycle* — a claim about
the system **doing something**, gradeable against the telemetry itself as the external yardstick, with no
human-norm circularity to navigate. The roadmap already flags 2c as **the strongest original idea and unusually
testable**, and pulling it forward is an explicitly sanctioned move (Phase 2 preamble: "2c is a strong candidate
to pull early"). It is the lower-risk, higher-originality, genuinely-external next meaning bar.

**What the pivot does NOT do (held honest).** It does not reopen 1c/1d/Phase 0; it does not claim 1e or the fan
effect were "failures" (both are honest, citable structural findings about what this substrate can and cannot
show); and it does not assert that semantic priming or the fan effect are *absent in principle* — only that they
are **not measurable as an earned cognitive claim on this substrate as built.** Phase 1's cognitive cycle stays
**mechanism-verified**; what remains open is which **external behavioral effect** carries the milestone, and the
recommendation is that it be **interoceptive modulation (2c)**, not an association-family effect.

**The alternative, stated fairly (the human's call).** If the human wants to keep the milestone inside Phase 1
and is willing to make a **Phase 0 engine decision**, the *only* path to a fan effect is to add source-activation
normalization to the engine (§3) — adopted for an independent architectural reason, with the fan effect then
checked as an **untuned** consequence against external fan norms. That is a legitimate research direction, but it
is (a) a substrate change requiring a separate approved spec, (b) a human-level architecture decision because it
changes the meaning of every prior activation result, and (c) only meaningful if the normalization is **not**
adopted *in order to* manufacture the effect. My recommendation is to **pivot to 2c now** and hold any
engine-normalization question as a separate, later, explicitly-framed Phase 0 decision — not as a way to rescue
the meaning bar under time pressure.

---

## 5. Where this leaves the roadmap

The behavioral primary meaning bar was re-routed from 1e (priming, NO-GO: anti-circularity) to the fan effect;
this pre-check finds the **fan effect also NO-GO** — structurally infeasible on the substrate as built, because
the engine provably does not normalize by out-degree (Phase 2A flat curve), so there is no fan-dependent signal
to grade, and the closed loop adds none. **No full fan experiment is designed.** The roadmap's "you are here"
moves from "fan effect, to be specified" to **"two association-family meaning bars exhausted (priming entangled;
fan-mechanism absent) → primary meaning bar open; recommend pivot to interoception (2c)."** `PROVEN` / `DESIGNED`
stays separate; mechanism ≠ meaning intact; 1c, 1d stay `BUILT · UNVALIDATED`; Phase 0 stays `PROVEN`; nothing
reopened.

**Single next action (human decision):** approve the pivot of the primary behavioral meaning bar to
**interoception (2c)** — at which point the architect-pm writes SPEC-2c (telemetry-derived body-state signals
that measurably modulate the cycle, graded against the live telemetry as the external yardstick) and routes the
meaning experiment to the validator. (Holding, separately and unrescued, any future Phase 0 question of whether
to add source-activation normalization to the engine — a human-level architecture decision, not a meaning-bar
workaround.)
