# SPEC-1e — Semantic priming through the closed cognitive loop, graded against human SWOW association norms

Status: **ATTEMPTED · NO-GO (design infeasible on SWOW for anti-circularity reasons) — 2026-06-21.** The blind three-arm stimulus selection was run (no graded number computed) and the design **cannot be graded without circularity on this corpus**: the §6.2 loop-work leverage stratum collapses to **N_S0 = 7 < 30** and the fallback is structurally unreachable (`r_W ≈ 0.97`). See **§14** for the spec-level disposition and **`docs/experiments/EXP-1e-priming.md` §15** for the full frozen record. **This is a structural finding learned before a graded run, not a failure** — the anti-circularity discipline working as designed. The **primary meaning bar is re-routed to the fan effect** (the pre-named, lower-circularity backup), a **separate human-directed step not started here.** Below is the original design as fully specified (all five open decisions RESOLVED; §13); **`PROVEN` / `DESIGNED` stays separate, mechanism ≠ meaning intact, and 1c/1d stay `BUILT · UNVALIDATED`, untouched.** When first written this spec was the project's **PRIMARY MEANING BAR**: the first claim that the system reproduces a real cognitive phenomenon (the *direction* of a semantic-priming effect) against external human data. It has **not** been run through the closed loop. When it is run, it is run by the **validator**, against a pre-registration frozen **before** any graded number is computed. The registered control design is a **three-arm structure with a conjunctive (a) ∧ (b) decision rule** (§5): arm (a) holds reachability constant, arm (b) holds path-distance constant, and the headline is earned only if both survive (arm (c) graded corroboration).
Author: architect-pm
For: **validator** (designs/runs the falsifiable experiment against external data, prediction fixed in advance). A small, separable **builder** task is carved out in §9 (a measurement-layer instrument + bringing the experiment suites into the canonical runner) and is the *only* part that touches code; the meaning experiment itself is the validator's.
Depends on: the **closed loop** `think()` (`src/nous_perceive.py`), 1d-i selection + 1d-ii bounded broadcast (`src/nous_workspace.py`), Phase 0 substrate + activation (`src/nous_store.py`, `src/nous_activation.py`), and the **Phase 2A/2B scaffolding** to be *reused* (`experiments/harness.py`, `experiments/swow.py`, `experiments/priming.py`).
Builds directly on: the **Phase 2B graded-priming result** (`experiments/PRIMING.md`, `experiments/priming.py`) and **must learn from its honest partial result** (see §3, the crux).

> Scope discipline (CONTRIBUTING.md rules 1–5). This document is **description and protocol design, not an implemented result**. `PROVEN` and `DESIGNED` stay in separate boxes: 1e is `DESIGNED`. When the validator runs it, a **positive** result moves 1c/1d *toward* meaning-validated for this one effect (it does **not** prove "a mind"); a **negative** result is an honest, publishable result that leaves the cognitive claim **UNVALIDATED**. Either way, the pre-registration is frozen first and no threshold is loosened after seeing data.

---

## 1. The claim of 1e — stated as narrowly as it must be

**The claim under test (narrow, exact):**

> Through the closed cognitive loop, a prime activates **strongly-associated** targets **more** than it activates **matched weakly-/un-associated** targets — where "associated" is defined by **external human SWOW association norms**, never by us — and this difference **survives, conjunctively, a control that holds graph reachability constant (arm a) AND a control that holds path distance constant while varying only association strength (arm b).** The claim is about the **DIRECTION** of the effect (related > unrelated), graded against human data.

That is the whole claim. It is a claim about a **mechanistic activation-magnitude difference in a pre-stated direction.** It earns the word "cognitive" only in the specific, limited sense that the *direction* matches a robust human behavioral phenomenon (semantic priming) measured on data the project did not author.

### 1.1 What 1e is NOT — the honest framing (hard, non-negotiable; CONTRIBUTING.md rules 1–2)

This disclaimer is part of the spec and must travel with every report of the result, in plain language:

- 1e is **NOT** a claim of **understanding**, **meaning in the human sense**, **comprehension**, **concepts**, **consciousness**, **awareness**, or that the system **"knows what words mean."** A directional activation difference is **not** comprehension and may never be described as such.
- The system has no semantics. "DOCTOR is more active after NURSE" is a statement about **activation spreading over a graph whose edges were built from human association counts** — it is *not* a statement that the system grasps doctors, nurses, or any relation between them.
- The mechanism Nous exercises corresponds, at most, to the **automatic / prospective / spreading-activation component** of human priming (Neely 1991): fast, association-driven activation. It does **not** model the strategic/expectancy or retrospective relatedness-checking components, and it is **not** a model of the lexical-decision *task*.
- A **positive** result establishes only: *on external human norms, with the prediction fixed in advance and reachability/distance controlled, the system reproduces the direction of automatic semantic priming.* A **negative** result is equally honest and is reported as-is; it leaves the cognitive claim unearned and does not reopen lower bricks.

Prior art is cited (§8) as the **definition of the phenomenon and the control logic**, never as evidence that Nous reproduces the underlying cognition.

---

## 2. The instrument we are working with (operational reality, read from the code)

This must be understood before the metric is chosen, because it constrains everything.

- **The engine does not normalize by out-degree.** `spread_activation` feeds each out-road the source's *full* activation: `transmitted = outgoing × road.strength × decay_per_hop`, with **no** `/len(out_roads)` and **no** per-source energy budget. This is the proven STEP-0 / fan-effect finding (`experiments/EXPERIMENT_NOTES.md`, `experiments/FAN_EFFECT.md`): the fan curve is **flat to the last digit**. Consequence, stated as a hard fact the metric must respect: **a "competition for a shared budget" contrast cannot register on the raw readout** — it must be added in the *measurement layer* (never the engine) if wanted, and even then it is just the raw value rescaled per prime (`experiments/PRIMING.md`, "Does not", item 3).
- **The raw readout** (`harness.retrieval_strength`, amortized by `harness.read_targets`) is **raw accumulated activation** at a target after one spread from the cue. A hop-1 target on an equal-strength edge receives exactly `energy × strength × decay_per_hop`. It is sensitive to **incoming edge strength** and **path distance (hops × decay)** — and to nothing else about the target.
- **Effective spreading horizon.** With library defaults (`energy 1.0`, `decay_per_hop 0.65`, `floor 0.02`, `hop_budget 6`) activation dies out by ~4 hops. On the full SWOW graph (measured, `PHASE2B_WORKING_NOTES.md`): reachability ≤2 hops 4.4%, ≤3 hops 47.3%, ≤4 hops 98.5%. **This single fact is the source of the 2B confound** (see §3).
- **The loop now closes.** `think()` runs perceive → 1c cluster → field → coalitions → 1d-i `select_winner` (pure read) → optional 1d-ii `broadcast` (single bounded write behind `broadcast=True`). The broadcast strengthens the **winner's internal roads** (a conductance bias), structurally bounded by `strengthen()`'s `(1−strength)` saturation. This is the precondition 1e needed: **a prime can now leave a trace that biases a later target.**

The 2B study measured priming on the **bare engine** (`spread_activation` directly, no `think()`, no broadcast). **1e's distinguishing requirement is that the effect must be measured *through the closed loop*** — the prime is presented to `think()`, broadcast is applied, and the target's activation is read on a *subsequent* cycle. That is what makes 1e the cognitive-cycle result and not a re-run of 2B (see §4, and the roadmap's "prior scaffolding to reuse, *not* a substitute").

---

## 3. THE CRUX — distinguishing genuine priming from a graph-reachability / decay artifact

This is the heart of the spec and gets the most rigor. **If a positive priming result could be fully explained by "a path exists in the graph" or "a shorter path decays less," it is trivial topology, not priming, and the claim is not earned.**

### 3.1 What 2B actually found, and the two holes it flagged honestly

2B (`experiments/PRIMING.md`, verbatim in `experiments/results/priming_output.txt`) found, on 300 blindly-selected primes:

```
DIRECT     median=0.330680   nonzero=300/300
MEDIATED   median=0.027447   nonzero=185/300
UNRELATED  median=0.000000   nonzero=0/300        (mean 0.0, max 0.0)
```

The ordering DIRECT > MEDIATED > UNRELATED held. But 2B itself flagged, in writing, two reasons this is **not** yet a competition/cognition result:

- **(a) UNRELATED was exactly 0 for ALL 300 pairs.** UNRELATED was defined as "no path within K=4 hops," and the engine's horizon dies by ~4 hops, so **"unrelated" coincided operationally with "beyond the activation horizon."** The DIRECT/MEDIATED-vs-UNRELATED contrast is therefore **partly graded *reach*** (a reachable target lights up; an out-of-horizon target delivers literally nothing) **rather than graded *competition* among reachable items.** A contrast where one arm is structurally pinned at exactly zero is a reachability contrast wearing a priming costume.
- **(b) DIRECT > MEDIATED is partly mechanical decay** — 1 hop attenuates less than 2 hops regardless of meaning (the same effect as the 2A fan sanity check). It is not, by itself, a cognitive result.

**The diagnosis:** in 2B, "related" (DIRECT/MEDIATED) and "unrelated" differed in **TWO** ways at once — *association strength* **and** *graph reachability/distance*. The activation difference could be entirely the second. **1e must break that confound.**

### 3.2 The design principle that breaks the confound

The confound is broken by **never letting the related and control arms differ in reachability or distance** — only in **human association strength.** **RESOLVED (Open Decision 2):** the registered design adopts a **three-arm pre-registered control structure**, because 2B flagged **two** distinct holes — reachability *(hole a)* **and** mechanical distance/decay *(hole b)* — and each needs its own arm. The two holes map onto two categorical control arms plus one graded corroboration:

- **Arm (a) — reachability control:** STRONG-RELATED vs UNRELATED-BUT-REACHABLE at **matched distance** (both in horizon, both non-zero). Rules out hole (a): *"it lit up only because a path exists / the control got nothing because it was beyond the horizon."* — *Control family B below.*
- **Arm (b) — distance/decay control (the NEW arm, addressing 2B's SECOND hole):** pairs held at **EQUAL graph path-distance** but **differing in SWOW association strength** (high-strength vs low-strength, both at the *same* distance). Rules out hole (b): *"DIRECT beat MEDIATED only because 1 hop decays less than 2."* — *Control family D below.*
- **Arm (c) — graded corroboration:** the continuous SWOW-strength → activation slope among equidistant direct targets (Spearman). Supporting evidence, not a categorical pass/fail. — *Control family A below.*

> **The engine is, by construction, sensitive to edge strength and path distance and to nothing else about a target (§2). Therefore the *only* way a positive result can be non-trivial is if it survives holding distance/reachability fixed while varying SWOW association strength.** This sentence is the spec's load-bearing logic, and the validator must be able to point to the specific control that enforces it. **Arm (b) is the sharpest instrument for this:** because R123.Strength is encoded *as the edge weight* (`swow.traverse_count_for_strength`), holding path-distance fixed and varying only SWOW strength is **precisely a test of whether SWOW strength → edge weight → activation.** That is what makes arm (b) a clean priming test rather than a topology test — distance is neutralized by construction, so any surviving effect can only be the association-strength signal flowing through the weight.

> **The conjunctive decision rule (pre-registered, binding — see §5 and §7):** the headline genuine-priming claim requires the effect to survive **BOTH arm (a) AND arm (b).** Passing only the graded arm (c) while **failing arm (b)** is an honest **NOT YET**, reported as *"explained by topology/decay, not association."* If arm (b) shows no high-vs-low separation once distance is held constant, the effect was distance/decay, not association strength — and that is reported as such, not buried.

The three control families below operationalize these arms. Families A and B are unchanged from the prior draft; **family D (arm b) is added here as a first-class, pre-registered control.**

#### Control family A — **Matched-distance graded strength** (the graded corroboration, arm (c))

Hold **path distance constant** (all targets are **1-hop direct responses** of the prime — equally reachable, equally close), and vary **SWOW association strength** across targets. Predict: higher SWOW strength → higher activation, *among equidistant reachable targets.*

- **Rules out:** the reachability artifact (every target is reachable, at the same distance) **and** the distance/decay artifact (every target is 1 hop). What remains can only be **edge strength**, and edge strength is built **monotonically from human SWOW association strength** (`swow.traverse_count_for_strength`). So a positive result says: *human association strength predicts activation, holding graph distance fixed.* That is the cleanest possible version of "automatic priming, direction reproduced."
- **Costs / residual confound:** this is a *graded-within-direct* test, conceptually close to 2B's **P1 instrument check** (which already passed: Spearman ρ = 0.2894 between SWOW strength and direct activation). The honest risk, stated up front: a strong positive here is **partly mechanical by construction** — the edge weight *is* a monotonic function of SWOW strength, so "stronger SWOW edge → more activation" is partly guaranteed by the strength→traverse_count map. **This is why family A alone is not sufficient and must be paired with the categorical arms (a) and (b)**, and why family A is registered as the **graded corroboration (arm c)**, never the headline. The residual confound is named so it cannot be hidden.
- **How arm (c) (this family) differs operationally from arm (b) (family D below) — they are not the same test:** arm (c) is a **continuous** statistic — the Spearman slope of activation against SWOW strength across *all* equidistant direct targets, asking "does more strength go with more activation, monotonically?" Arm (b) is a **categorical, pre-registered high-vs-low contrast at fixed distance** with a clean pass/fail — two strength bands (high, low) held at the *same* distance, with a within-prime sign test and a fixed direction. A slope can be significant yet driven by a few high-leverage points; a band contrast cannot hide that way — it forces a *thresholded, falsifiable* yes/no at a *fixed* distance, which is exactly the form the human direct-priming literature uses (strong associate beats weak associate). They earn separate places because a graded slope (c) is the *power* (it uses the whole strength range) while the categorical band contrast (b) is the *guard* (it is the pre-registrable pass/fail the verdict rule depends on). The conjunctive rule binds on (a) and (b), the categorical arms; (c) corroborates.

#### Control family B — **Matched-reachability categorical contrast** (arm (a): the reachability control)

Compare **STRONG-RELATED** targets (a prime's high-SWOW-strength direct responses) against **MATCHED-UNRELATED-BUT-REACHABLE** targets: nodes the prime reaches **at the same hop distance and with a path that exists**, but for which the SWOW association strength is **absent or near-zero** (no direct cue→response association, or one in the lowest SWOW-strength band). The matched-unrelated target must be **reachable and non-zero in raw activation** — that is the whole point: it is *in the horizon*, so a difference cannot be "it got nothing because it was too far."

- **Rules out:** the **reachability artifact specifically** (the 2B hole (a)). Both arms light up; the question is whether the *human-strong* one lights up **more** than a *human-weak-but-equally-reachable* one. If yes, the effect is association strength, not mere reach.
- **The hard construction problem (and its honest residual):** at 1 hop, "reachable but unrelated" is contradictory — a 1-hop neighbor *is* a direct SWOW response, so it has *some* association strength. So family B's matched-unrelated target sits at **2 hops** (reachable via a real 2-step path, in horizon, but with **no direct prime→target SWOW edge**), matched against a related target also evaluated through a 2-step framing, OR the contrast is run as **strong-direct vs weak-direct** (which collapses into family A). The cleanest non-circular form, recommended: **strong-direct vs a same-distance weak-or-absent comparison drawn so both are reachable and non-zero**, with distance matched by construction. The residual confound, named: matching distance *exactly* while varying strength *only* is hard on a real graph; the validator must report the achieved distance distributions per arm and show they are equalized (a falsifier if they are not — §7).

#### Control family D — **Distance-matched, strength-varied: the NEW arm (b)** (the decay control; co-headline)

**This is the arm that closes 2B's second hole** — the worry that DIRECT > MEDIATED was "partly mechanical decay" (1 hop attenuates less than 2 hops regardless of meaning). It does so by **holding graph path-distance EXACTLY constant and varying ONLY SWOW association strength**, in a **categorical** high-vs-low contrast with a pre-registered direction and a within-prime sign test.

**Construction (categorical, at a fixed distance — drawn from SWOW, never hand-authored):**

- **At distance 1 (the primary, cleanest realization — this absorbs the old family C):** per prime P, draw two direct responses of P — one in the **HIGH** R123.Strength band and one in the **LOW** R123.Strength band — **both direct (1 hop), both reachable, both non-zero**, differing **only** in strength band. Within-prime sign test: is the HIGH-strength target more active than the LOW-strength target, prime by prime? Here "strength" is unambiguous: it is the R123.Strength of the single direct cue→response edge, which *is* the edge weight.
- **At distance 2 (included only if it can be constructed cleanly; reported separately):** per prime P, draw two targets each reachable at **exactly 2 hops** via a real P→M→T path, where the **2-hop pairs are binned high-vs-low by the strength of the bottleneck path** — defined, fixed in advance, as the **minimum R123.Strength along the P→M→T path** (the weakest link; this is the standard bottleneck definition and avoids rewarding a target merely for having many weak paths). Both at 2 hops, both non-zero, differing only in the binned path-strength. *If a clean distance-2 strength definition cannot be applied (e.g. too few primes yield both a high- and a low-bottleneck 2-hop target), the distance-2 sub-arm is dropped and that is reported; the distance-1 contrast alone carries arm (b).*

- **Rules out:** the **distance/decay artifact specifically** (the 2B hole (b)). Distance is held fixed across the two bands, so attenuation is identical; the *only* surviving difference is SWOW association strength. If HIGH beats LOW at equal distance, the effect is association, not decay. **If priming vanishes once distance is held constant — HIGH ≈ LOW — the effect was topology/decay, not association, and that must be reported honestly as such (an honest NOT YET on the headline).**
- **Why this is a clean, non-circular priming test (stated plainly, per §2):** the bare engine is sensitive only to incoming edge strength and path distance. Arm (b) neutralizes distance by construction, leaving incoming edge strength as the sole live variable — and incoming edge strength **is** R123.Strength under the fixed `traverse_count_for_strength` map. So arm (b) at fixed distance is **exactly** the test of whether *SWOW strength → edge weight → activation*. It is therefore a direct probe of the priming pathway, not a topology probe. The residual is named honestly and is the *same* one family A carries — the edge weight is a monotonic function of SWOW strength, so a HIGH-vs-LOW separation is *partly* guaranteed by the strength→weight map. What makes arm (b) nonetheless load-bearing rather than circular is that it is the **categorical, pre-registered, distance-held pass/fail** that the human direct-priming literature itself uses (strong associate beats weak associate at fixed lag); a *null* here is fully possible (the bands could fail to separate if activation is dominated by something other than edge strength) and would falsify the headline. The claim is not "strength maps to weight" (true by construction) but "*that weight difference survives into a measurable activation difference at the target, through the loop, in the human direction*" — which the engine does not guarantee and the experiment can refute.
- **Feasibility / honesty (binding, like the arm-(a) fallback):** if SWOW cannot yield enough equal-distance / varied-strength pairs at acceptable counts (the HIGH and LOW bands at a fixed distance must both be populated per prime, for enough primes to power the sign test), the arm is reported as **underpowered or infeasible**, with the achieved N stated — **never silently dropped.** An infeasible arm (b) means the crux's second hole is *not* closed and the headline cannot be earned on decay-control grounds; that is reported as an honest limitation, not a pass.

> **Operational distinction, restated so it cannot be conflated:** family D / arm (b) is **categorical** (HIGH band vs LOW band, fixed distance, within-prime sign test, pre-registered direction, clean pass/fail). Family A / arm (c) is **continuous** (Spearman slope of activation on strength across equidistant targets). Both use SWOW strength at fixed distance; they differ in that (b) is the thresholded guard the verdict depends on and (c) is the graded power that corroborates. The conjunctive verdict rule binds on (a) ∧ (b); (c) supports.

### 3.3 The mediated condition — DEMOTED, with a literature reason

2B's most *interesting* number was MEDIATED > UNRELATED (185/300 primes). **1e does not make the mediated contrast its headline,** for a literature-grounded reason the validator must record:

- **Mediated priming is task-dependent and unreliable in humans.** Balota & Lorch (1986) found mediated priming (lion → [tiger] → stripes) in **naming** but **not** in **lexical decision** — because LDT adds a retrospective relatedness-checking stage that mediated pairs fail. De Groot (1983) and others report it as weak/inconsistent. So "mediated > unrelated" does **not** correspond to a single robust human direction; predicting it would be predicting a contested effect.
- Worse, in 2B the mediated effect is **still entangled with reachability** (UNRELATED = 0), so it inherits hole (a).
- **Disposition:** the mediated contrast is **retained as a recorded secondary/exploratory observation only** (reported, clearly labeled "exploratory; the human direction is task-dependent — Balota & Lorch 1986"), never as the meaning bar. The meaning bar is the **reachability- and distance-controlled strong-vs-weak contrast** — the three-arm structure: arm (a) reachability control (family B), arm (b) distance/decay control (family D), and arm (c) graded corroboration (family A), with the headline binding conjunctively on (a) ∧ (b).

---

## 4. PROPOSAL 1 — the priming metric through the closed loop (Open Decision 1 — **RESOLVED: M-A headline, M-B corroboration, M-C rejected**)

**Problem:** "faster/stronger activation of the target" must be made operational *now that broadcast exists.* What is fed in, how many cycles, what scalar is read, how it is normalized?

**RESOLVED.** The headline metric is **M-A (broadcast-trace Δ)** — it uses the 1d-ii broadcast and is therefore the genuinely closed-loop measurement that distinguishes 1e from 2B. **M-B (bare-spread)** is retained as corroboration and the bridge to 2B. **M-C (selection/winner)** stays rejected. The three candidates are recorded below for the audit trail.

### Metric M-A — **Broadcast-trace metric (the genuine closed-loop metric; ACCEPTED as headline)**

1. Start from the frozen SWOW substrate (built once, `Clock(simulated=True)`).
2. **Prime cycle:** call `think(store, prime_utterance, broadcast=True)`. The prime is presented as an utterance whose token matches the prime node (perception → 1c → field → coalitions → winner → **broadcast** strengthens the winner's internal roads). This leaves the bounded conductance trace.
3. **Probe cycle:** read the **target's activation under a spread from the prime** (`harness.read_targets`) **on the now-broadcast-modified store**, and compare to the **same read on a pristine copy of the store** (no broadcast). The scalar is **Δ activation at the target = activation_after_broadcast − activation_before_broadcast**, i.e. *how much the prime's own broadcast raised the target's reachability.*
4. **Read-out scalar:** Δ activation (raw), per (prime, target). Aggregated by condition (strong-related / weak-or-unrelated) and tested by a **within-prime sign test** on Δ.

- **Why recommended:** this is the **only** metric that actually exercises **1d-ii's broadcast** — the thing that distinguishes 1e from 2B. The claim becomes "*the prime's broadcast trace preferentially eases its strongly-associated targets*," which is a genuine closed-loop priming statement. It is falsifiable (Δ could be flat, or negative, or equal across conditions).
- **Cost / risk, named honestly:** the broadcast only strengthens roads **internal to the winning coalition.** If a target is not in the winner's coalition, its incoming roads are not strengthened and Δ = 0 for it regardless of association strength. So this metric measures priming **within the broadcast's reach**, and the validator must report what fraction of strong-related vs weak targets fall inside the winner (a structural property to characterize, and a possible reason for a null — reported, not hidden). This is the honest cost of using the real broadcast rather than a bare spread.

### Metric M-B — **Bare-spread metric (the 2B metric, reused; corroborating, NOT the closed-loop result)**

Single spread from the prime, read target activation (no `think()`, no broadcast) — exactly 2B's `read_targets`. Use it to **replicate 2B under the new controls** (all three arms), so the controlled result is comparable to the prior partial one.

- **Why keep it:** it is the proven instrument; it makes the §3 controls directly comparable to 2B; it is cheap and deterministic.
- **Why it is not the headline:** it does **not** use the broadcast, so it is **not** "through the closed loop" — it is the substrate's spreading-activation answer. Reported as the **mechanism-level corroboration**; the headline closed-loop claim rides on M-A.

### Metric M-C — **Selection/winner metric (rejected for 1e)**

Read whether the strong-related target *wins the workspace* more often than a weak/unrelated one. Rejected: selection is dominated by which sources the **current percept** lights up (1d-i seeds the field from perceived sources), so this mostly measures perception/clustering, not priming; and it is a coarse binary that throws away the graded signal. Recorded as rejected so the choice is on the record.

**Resolution (recorded):** **headline = M-A (broadcast-trace Δ) through the closed loop**, with **M-B (bare spread) reported alongside as corroboration and as the bridge to 2B.** Normalization: **raw Δ is primary**; a measurement-layer **normalized** readout (Δ as a share of the prime's outgoing total, via `read_targets`' `outgoing_total`) is reported as secondary, **clearly labeled as the same value rescaled per prime** (per the fan-effect finding it is not an independent competition measure). All knobs at library defaults, held identical across conditions and asserted as a control. **Each of the three control arms (a)/(b)/(c) is measured under both M-A (headline) and M-B (corroboration)**, so the conjunctive verdict is read on the closed-loop metric with the bare-spread bridge alongside.

---

## 5. PROPOSAL 2 — the control / baseline design (Open Decision 2 — THE most important decision — **RESOLVED: D-1, strengthened to a three-arm conjunctive design**)

**Problem:** which control(s) from §3.2 to adopt as the registered design. This is the single most important choice in the spec; §3 makes the tradeoffs sharp.

**RESOLVED — D-1 accepted, and strengthened.** The human accepted **D-1** (matched-reachability categorical contrast as headline + graded-SWOW corroboration), **keeping the auto-fallback to graded-only** if the data cannot support the matched construction. **But D-1 as originally drafted closed only 2B's FIRST hole (reachability).** A **THIRD arm is added** to close 2B's SECOND hole (the "DIRECT > MEDIATED was partly mechanical decay" worry): the **distance-matched, strength-varied** arm (family D / arm (b), §3.2). The registered design is therefore a **three-arm structure with a conjunctive decision rule**:

- **Arm (a) — reachability control (family B):** STRONG-RELATED vs UNRELATED-BUT-REACHABLE at matched distance — both in horizon, both non-zero — within-prime sign test, direction fixed (strong-related > matched-control). *Rules out: "a path merely exists" / "the control got nothing because it was out of horizon."*
- **Arm (b) — distance/decay control (family D, the NEW arm):** HIGH-strength vs LOW-strength SWOW pairs held at **EQUAL path-distance** (primary realization: both direct, 1 hop; optional distance-2 sub-arm by bottleneck path-strength), within-prime sign test, direction fixed (HIGH > LOW). *Rules out: "DIRECT beat MEDIATED only because nearer decays less."*
- **Arm (c) — graded corroboration (family A):** continuous SWOW-strength → activation slope among equidistant direct targets (Spearman ρ > 0). *Supporting evidence; not a categorical pass/fail.*

> **The conjunctive decision rule (pre-registered, binding):** the **headline genuine-priming claim requires the effect to survive BOTH arm (a) AND arm (b).** Each categorical arm must show its pre-stated direction at its pre-stated effect size. **Passing only the graded arm (c) while FAILING arm (b) is an honest NOT YET**, reported explicitly as *"the effect is explained by topology/decay, not association."* Likewise, passing (b) but failing (a) is a NOT YET (the reachability hole is not closed). The graded arm (c) can never *rescue* a failed categorical arm; it only corroborates a passing one. This rule is stated identically in §7 and is the verdict the validator freezes.

**Why three arms and not two:** arms (a) and (b) close *different* holes. Arm (a) lets both compared targets be reachable but makes one of them *unrelated* (no direct SWOW edge) — it cannot, on its own, rule out that the related target simply sat at a shorter effective distance. Arm (b) holds distance *exactly* equal and varies *only* strength — it cannot, on its own, rule out that the whole effect lives beyond the horizon (both its targets are in-horizon by construction). Only the conjunction rules out both the reachability artifact *and* the decay artifact, which is exactly the pair of holes 2B flagged. Neither single arm is sufficient; the headline is earned only when both hold.

### The rejected / fallback packagings (recorded for the audit trail)

- **D-2 — graded-within-direct only (the registered FALLBACK).** Arm (c) alone. Easiest to construct; but **partly mechanical by construction** and vulnerable to "that's just the strength→weight map," so it is the *weakest* form of the claim and **cannot** earn the headline. **It is the sanctioned auto-fallback** *only if* the matched constructions for arms (a) and/or (b) prove infeasible on the data — and that infeasibility (which arm failed to populate, at what N) **must be reported honestly when the fallback is triggered.** Falling back to (c)-only is reported as **NOT YET on the headline**, with the graded result stated for what it is.
- **D-3 — replicate 2B + UNRELATED-BUT-REACHABLE arm.** Its UNRELATED-BUT-REACHABLE construction is **folded into arm (a)** as that arm's operationalization (this is how arm (a) gets its in-horizon non-zero control). The full DIRECT/MEDIATED/UNRELATED replication is run for comparability, with MEDIATED exploratory throughout (§3.3).

**Resolution (recorded):** the registered design is **D-1 + arm (b)** — three arms, headline conjunctive on (a) ∧ (b), arm (c) graded corroboration, D-3's reachable-unrelated arm folded into arm (a). **If a matched construction yields too few primes for a categorical arm** (a data fact to be measured and reported, not assumed): if **arm (a)** is infeasible, the reachability hole is open → headline NOT YET; if **arm (b)** is infeasible, the decay hole is open → headline NOT YET; if **both** categorical arms are infeasible, the run **falls back to D-2** (arm (c) only) and says so explicitly. The mediated arm is exploratory throughout.

> **Anti-circularity guard (binding, CONTRIBUTING.md rule 5):** every condition in all three arms is selected **BLIND** — from SWOW **topology + strength only**, by a fixed seeded procedure, **before any activation/`think()` is run** — exactly the discipline `swow.select_pairs` already enforces. No pair may be chosen, dropped, reordered, or weighted by any Nous output. Selecting a target *because* it activated well is the circularity bug and voids the run. Arm (b)'s HIGH/LOW bands and distance bins are drawn from SWOW strength/topology alone; arm (a)'s reachable-unrelated control is drawn from SWOW topology alone.

---

## 6. PROPOSAL 3 — the external SWOW relatedness definition and matched-pair construction (Open Decision 3 — **RESOLVED: R123.Strength now, R1 as a robustness re-run if the headline passes**)

**Problem:** define "relatedness" from SWOW (never hand-authored) and construct matched pairs **algorithmically** so no pair is cherry-picked.

**RESOLVED (3a).** Use **R123.Strength** for the substrate and the selection bands now — no rebuild, consistent with the whole repo's edge basis. Add **R1 (first-response forward strength) as a pre-registered robustness re-run** *if and only if* the headline passes on R123 (a stronger result if it replicates on first-response strength). Raw counts (R-SET) stay rejected. **RESOLVED (3b).** Construction is algorithmic, seeded, blind to activation, with pair lists persisted and hashed — and §6.2 below now specifies the construction for **all three arms**, including the new arm (b).

### 6.1 Relatedness signal — which SWOW quantity (Open Decision 3a — **RESOLVED: R123.Strength**)

- **Option R-123 (currently loaded):** `R123.Strength` ∈ [0,1] = conditional probability of a response given the cue across **all three** responses. This is what `swow.py` loads today and what the whole repo's edge weights are built from. **Pro:** already wired, already the substrate's edge basis, no rebuild. **Con:** R123 pools first/second/third responses, a slightly noisier "association strength."
- **Option R-1 (first-response forward strength):** networks built from **first responses only** (De Deyne et al. 2019, GR1) — the cleaner *forward associative strength* signal, closest to the classical free-association norms (Nelson, McEvoy & Schreiber) the priming literature uses. **Pro:** the most defensible "human association strength." **Con:** requires re-deriving strengths/edges; a second substrate.
- **Option R-SET (cue-response token count / N):** raw response counts. **Con:** not normalized; rejected (a high-frequency cue inflates counts).

**Resolution (recorded):** **use R123.Strength** (R-123) for the **substrate and the edge weights** (no rebuild, consistent with the rest of the repo), **and define the relatedness *bands* for selection from the same R123.Strength** so the grading signal and the substrate are the same external quantity. Run R-1 as a **pre-registered robustness re-run** if **the headline passes** (both categorical arms) on R123 (a stronger result if it replicates on first-response strength). Note honestly: because the substrate edge weight and the relatedness band both derive from R123.Strength, this is "the same external signal drives both" — legitimate (the signal is external and human), but the report must state it is **not** two independent measurements (the same framing 1c §6.2 had to make).

### 6.2 Matched-pair construction — algorithmic, no cherry-picking (Open Decision 3b — **RESOLVED**)

All construction is in `swow.py`-style **topology+strength-only** code, seeded, deterministic, **blind to activation**. The construction now produces the pairs for **all three pre-registered arms**. All distances come from `Topology.reachable_within` (BFS hop counts); all strengths come from the retained per-direct-edge R123.Strength; **nothing is hand-authored.**

1. **Strength bands** from the empirical R123.Strength distribution (heavy right-skew: mean 0.0123, median 0.01 — `PHASE2B_WORKING_NOTES.md`). Define **STRONG/HIGH = top quantile** (e.g. ≥ 90th percentile of cue→response strengths) and **WEAK/LOW = a low non-zero band** (e.g. 10th–25th percentile), both **> 0**, with the exact percentile cuts **fixed in the pre-registration before any run.** The same HIGH and LOW bands serve arm (b) (categorical, fixed distance) and the high/low ends of arm (c)'s graded range.
2. **Per prime P** (out-degree ≥ a fixed `MIN_OUTDEG`, sorted candidate list, seeded shuffle — the `select_pairs` discipline), draw the targets for each arm:

   **Arm (a) — reachability control (family B), distance-matched:**
   - **STRONG-RELATED target:** a direct response of P in the STRONG band (1 hop, non-zero).
   - **MATCHED-UNRELATED-BUT-REACHABLE target:** a node reachable from P **within the horizon** (≤3 hops, so raw activation is non-zero) with **no direct P→target SWOW edge**, drawn from the sorted in-horizon pool — its hop distance recorded so the achieved per-arm distance distributions can be shown equalized (a §7 falsifier if they are not). Because a 1-hop neighbor is necessarily a direct response (and so cannot be "unrelated"), this control sits at 2 hops; the achieved distance match is reported, not assumed.

   **Arm (b) — distance/decay control (family D), the NEW arm, strength-varied at EQUAL distance:**
   - **Distance-1 (primary):** **HIGH-direct target** = a direct response of P in the HIGH band; **LOW-direct target** = a direct response of P in the LOW band. **Both are 1 hop, both reachable, both non-zero**, differing **only** in R123.Strength band. "Strength" here is the R123.Strength of the single direct P→target edge (== the edge weight). This is the cleanest, primary realization of arm (b) and **absorbs the old family-C within-direct matched pair.**
   - **Distance-2 (optional sub-arm, reported separately):** **HIGH-2hop** and **LOW-2hop** targets, **each reachable at exactly 2 hops** via a real P→M→T path and *not* a direct response of P, binned high-vs-low by the **bottleneck path-strength = min(R123.Strength(P→M), R123.Strength(M→T))** (weakest link; fixed in advance). Both at 2 hops, both non-zero, differing only in binned path-strength. **Included only if both bands populate for enough primes; otherwise the distance-2 sub-arm is dropped and that is reported — the distance-1 contrast alone then carries arm (b).**

   **Arm (c) — graded corroboration (family A), continuous, equidistant:**
   - The **full set of P's direct (1-hop) responses with their R123.Strength values**, for the Spearman slope of activation against strength among equidistant targets. (No banding; the whole strength range is used.)

   - (**exploratory MEDIATED**, retained labeled: 2-hop, not direct — as in 2B.)
3. **Keep a prime only if it yields the required arms** (report the actual N **per arm** and the per-arm hop-distance distributions). A prime may contribute to arm (c) and the distance-1 part of arm (b) even if it cannot populate arm (a) or the distance-2 sub-arm; **per-arm N is tracked separately** so an underpowered arm is visible, never hidden inside a single pooled count. Selection consults **SWOW only** — never activation.
4. **Persist the selected pair lists verbatim** to `experiments/results/`, **one file per arm** (as 2B does — `priming_pairs_*.txt`), for audit and for the §7 freeze-hash.

**External yardstick, not self-authored:** all bands, all pairs, all distances, all directions come from SWOW. The project authors **none** of the relatedness values. The only project-authored numbers are the **percentile cuts, `MIN_OUTDEG`, the horizon hop-cap, and the bottleneck definition**, which are **structural selection parameters fixed in advance** (not relatedness judgments), and they are pre-registered before any run.

---

## 7. PROPOSAL 4 — the pre-registration (Open Decision 4 — **RESOLVED: `docs/experiments/EXP-1e-priming.md`, three arms + conjunctive rule frozen**) — frozen BEFORE any graded number

**Problem:** the falsifiable prediction must be frozen, with anti-tamper discipline, before the validator computes anything.

### 7.1 Location, filename, freeze discipline (binding)

- **File:** **`docs/experiments/EXP-1e-priming.md`** (sibling of the existing `docs/experiments/EXP-1c-swow-recovery.md`, which is the template for this discipline).
- **Freeze discipline (modeled exactly on EXP-1c):**
  1. The pre-registration — claim, the **three arms** and their predicted directions, the **conjunctive (a) ∧ (b) decision rule**, metric (M-A primary, M-B corroboration), per-arm effect-size thresholds, the control design (D-1 + arm (b)), the selection procedure, the SWOW band/distance/bottleneck definitions, the falsifiers — is written **in full and committed** before any `think()`/activation is run on selected pairs.
  2. It carries an **ANTI-TAMPER NOTICE** (as EXP-1c does): nothing in it changes after any result is observed.
  3. The selected pair lists and the substrate build are **frozen and hashed** (SHA-256 of the pair-list files + the loaded-edge count), with the hash pasted into the pre-registration **once**, before measurement — so the run cannot be re-pointed at a friendlier pair set after the fact (mirrors EXP-1c's frozen-partition hash).
  4. The experiment runner **prints the pre-registration banner first** (before loading data), exactly as `priming.py`'s `print_preregistration()` does, and the captured stdout is committed verbatim to `experiments/results/`.
  5. **Order is enforced and reported:** freeze → select blind → build → measure → verdict-from-data. The validator commits the frozen pre-registration in a **separate commit before** the commit that adds any measured number.

### 7.2 Required contents of the pre-registration (the validator fills these with fixed values)

The pre-registration must enumerate **all three arms** and freeze the **conjunctive (a) ∧ (b) decision rule**.

- **Hypothesis** (the §1 narrow claim) and its **honest-framing disclaimer** (§1.1) reproduced verbatim.
- **The three pre-registered arms and their predicted directions:**
  - **Arm (a) — reachability control:** STRONG-RELATED activation (and Δ) **>** MATCHED-UNRELATED-BUT-REACHABLE, at matched distance, both non-zero.
  - **Arm (b) — distance/decay control (NEW):** at **equal path-distance**, HIGH-strength activation (and Δ) **>** LOW-strength (distance-1 primary; distance-2 sub-arm if populated).
  - **Arm (c) — graded corroboration:** SWOW strength **positively** predicts activation among equidistant direct targets (Spearman ρ > 0).
- **Metric:** M-A (broadcast Δ) primary; M-B (bare spread) corroboration; raw primary, normalized secondary (labeled rescaled). Each arm measured under both metrics.
- **Effect-size thresholds (fixed in advance), per arm:** for **each categorical arm (a) and (b)**, a within-prime sign test in the pre-stated direction in a pre-stated majority (a concrete fraction, e.g. ≥ X% with two-sided sign-test p < 0.05) **and** a pre-stated minimum median separation (raw activation, and Δ under M-A). For **arm (c)**, Spearman ρ > 0 with p < 0.05. **Exact numbers are the validator's to fix in EXP-1e before running** — this spec fixes the *form*, the *direction*, and the *conjunction*, not the post-hoc number.
- **The control comparisons:** arm (a)'s matched-reachable control (both arms non-zero, **distance-equalized**, with a report of achieved equalization) **and** arm (b)'s equal-distance HIGH-vs-LOW contrast (with a report that distance is genuinely held constant across the two bands and that both bands populate).
- **What would FALSIFY the claim (stated in advance):**
  - **Arm (a) fails:** STRONG-RELATED ≈ MATCHED-CONTROL (no separation once reachability/distance are held constant) → **NOT YET** (the 2B effect was reachability, not priming).
  - **Arm (b) fails:** HIGH ≈ LOW once distance is held constant → **the effect was topology/decay, not association** → **NOT YET**, reported explicitly as such. *(This is the new arm's specific falsifier and is co-decisive with arm (a).)*
  - **Arm (a)'s control arm is all-zero again** (matched-reachable construction failed to produce in-horizon non-zero controls) → the reachability confound is **not** broken → inconclusive on the crux, reported as such (not a pass).
  - **A categorical arm is underpowered/infeasible** (HIGH and LOW bands, or the reachable-unrelated control, do not populate for enough primes to power the sign test) → that arm's hole is **not** closed → headline **NOT YET**; if both categorical arms are infeasible, fall back to arm (c)-only and report the graded result as NOT YET on the headline.
  - Direction reverses in any categorical arm (weak/unrelated/LOW more active) → that arm falsified.
  - Achieved per-arm hop-distance distributions are **not** equalized (arm a) or distance is **not** genuinely constant across bands (arm b) → the distance confound stands → **NOT YET**.
  - Determinism breaks across hash seeds → run **void** (instrument failure), not a result.
- **Verdict rule (no post-hoc loosening) — CONJUNCTIVE:** the headline genuine-priming claim is **CLAIM EARNED (for this one effect) iff the pre-stated direction holds at the pre-stated effect size on BOTH arm (a) AND arm (b)**, with arm (c) in the same direction as corroboration, and determinism intact. **Passing arm (c) alone, or only one categorical arm, is NOT YET** — and if it is arm (b) that fails, the NOT YET is reported as *"explained by topology/decay, not association."* Otherwise **NOT YET**, reported honestly; 1c/1d stay `BUILT · UNVALIDATED`. (R1 robustness re-run is run only if the headline is earned on R123.)

---

## 8. Prior art (the phenomenon and the control logic — NOT evidence Nous reproduces cognition)

Cited to define the effect and justify the controls. The line between *what the literature establishes* and *what Nous tests* is drawn explicitly.

- **Meyer & Schvaneveldt (1971), *J. Exp. Psychol.* 90(2), 227–234** — the foundational semantic-priming result: a string (DOCTOR) is classified faster when preceded by an associate (NURSE) than by an unrelated word (BUTTER). *Establishes:* the human **direction** (related faster than unrelated). *Nous tests:* whether the analogous **activation magnitude** direction holds on SWOW, controlled for reachability/distance — **not** reaction time, **not** the lexical-decision task.
- **Neely (1991), "Semantic priming effects in visual word recognition: A selective review," in *Basic Processes in Reading*** (and Neely 1977) — distinguishes **automatic** (fast, association-driven, prospective) from **strategic** (expectancy, retrospective relatedness-checking) priming. *Establishes:* priming has multiple components. *Nous tests:* only the analogue of the **automatic/prospective spreading-activation** component; Nous models **none** of the strategic/retrospective machinery, and the spec says so.
- **Collins & Loftus (1975), "A spreading-activation theory of semantic processing," *Psychol. Rev.* 82, 407–428** — the spreading-activation account of priming and relatedness; activation radiates along associative links, easing related concepts. *Establishes:* the theoretical mechanism Nous's engine is *inspired by*. *Nous tests:* whether *its* spreading activation, over a **human-association-weighted** graph, reproduces the priming direction — citing this as **engineering/theoretical lineage**, not as proof Nous instantiates the theory.
- **Balota & Lorch (1986), "Depth of automatic spreading activation: Mediated priming effects in pronunciation but not in lexical decision," *J. Exp. Psychol. LMC* 12(3), 336–345** — mediated priming (lion→[tiger]→stripes) appears in **naming** but **not lexical decision**. *Establishes:* the mediated effect is **task-dependent and not a single robust direction.** *Why it matters here:* this is the literature reason 1e **demotes** the mediated contrast to exploratory (§3.3) and headlines the reachability-controlled direct contrast instead.
- **De Deyne, Navarro, Perfors, Brysbaert & Storms (2019), "The 'Small World of Words' English word association norms for over 12,000 cue words," *Behavior Research Methods* 51(3), 987–1006.** https://doi.org/10.3758/s13428-018-1115-7 — the external human data. R1 = first-response networks; R123 = all-responses networks; associative strength = conditional probability of response given cue. *Establishes:* the **external yardstick.** *Nous tests:* its activation against these human norms; the norms are **not** authored by the project.

**The honest separation, stated once:** the literature establishes that *humans* show automatic semantic priming and what its direction is. 1e tests only whether *Nous's activation, over a SWOW-weighted graph, moves in that direction when reachability and distance are controlled.* A match is "the direction is reproduced on external data," never "Nous primes the way a person does," and never "Nous understands."

---

## 9. Routing — validator runs it; a small separable builder task (binding)

**This is a meaning experiment → it is routed to the VALIDATOR** (CONTRIBUTING.md: the validator designs/runs falsifiable experiments against external data with a prediction fixed in advance; the builder does **not** assert its meaning). The validator: writes `docs/experiments/EXP-1e-priming.md`, freezes it, selects pairs blind, runs M-A through the closed loop + M-B corroboration, captures verbatim, computes the verdict from data, reports earned-or-NOT-YET.

**Separable builder task (the ONLY code 1e needs — keep the line clean):**

- **(B-i) A measurement-layer broadcast-Δ instrument** in the experiments layer (e.g. `read_target_delta(store, prime_utterance, targets)` that runs `think(prime, broadcast=True)` then reads the targets before/after on a pristine vs broadcast store) — **additive, in `experiments/`, importing the frozen `src/` library unchanged**, a pure read except for the one sanctioned broadcast write on a copy. It must be **deterministic across hash seeds** and have its own adversarial test. This is *instrumentation*, not a meaning claim; the builder builds it and the tester verifies its **mechanism** (determinism/purity), exactly as for any substrate-adjacent code.
- **(B-ii) Bring the experiment suites into the canonical runner** (see §11) so they stop being tier-3-only.

**The line:** the builder/tester own (B-i)+(B-ii) — *mechanism* of the instrument. The validator owns the *experiment and its meaning*. No agent crosses: the builder does not interpret the priming result; the validator does not modify the frozen engine; the tester does not adjudicate meaning.

---

## 10. PROPOSAL 5 — harness reuse vs revision, and the canonical-runner question (Open Decision 5 — **RESOLVED: reuse unchanged + extend additively; bring instrument MECHANISM tests into `run_tests.py`, keep data-dependent experiment scripts out**)

**Reuse, don't rebuild (CONTRIBUTING.md rule 6).** **RESOLVED.** The 2A/2B scaffolding is reused unchanged and extended additively; the instrument's mechanism tests are brought into the canonical runner; the data-dependent experiment-result scripts stay out.

- **Reuse unchanged:** `experiments/swow.py` (loader, `Topology`, `select_pairs` blind-selection discipline), `experiments/harness.py` (`build_graph_from_spec`, `retrieval_strength`, `read_targets`).
- **Extend additively (not revise):** add the §6.2 **band-based, three-arm matched-pair selection** (arms (a)/(b)/(c), including arm (b)'s HIGH/LOW distance-1 and optional distance-2 construction) to a 1e selection module (a sibling of `priming.py`, e.g. `experiments/priming_1e.py`) and the **broadcast-Δ instrument** (B-i). Do **not** edit the frozen 2A/2B functions; add alongside, as 2B added `read_targets` without touching 2A.
- **2B's `priming.py` stays** as the bare-engine corroboration (M-B); the new module adds the closed-loop M-A and the §3 three-arm controls.

**The canonical-runner decision (RESOLVED — the human has accepted the suite-count/tier-boundary shift):** the 2A/2B/exp1c suites (`test_harness.py`, `test_priming.py`, `test_exp1c.py`) were **NOT** in `run_tests.py` (tier-3 disciplined-exploratory). **Resolution: bring the *mechanism* tests of the reused/added instruments into the canonical runner** — specifically `test_harness.py` and the new (B-i) instrument's test (tester-grade) — so the instrument 1e depends on is tester-verified, not self-tested. **Keep the *experiment-result* scripts out** of the canonical runner (they require the uncommitted ~53 MB SWOW file and make meaning claims; they are validator-run artifacts, and the canonical run must stay green without the data file). This raises the instrument from tier 3 to tier 2 **without** blurring mechanism and meaning. **Note (accepted by the human):** this **shifts the canonical suite count and the tier-2/tier-3 boundary** — <!-- ledger:allow-count --> the canonical run *at the time of writing* (12 suites, 618 assertions) will grow when `test_harness.py` + the (B-i) test are added; the new counts are read from `docs/TEST_OUTPUT.txt` after the builder wires them in, never estimated here. **(Resolved: they were wired in; the canonical run's current totals are in `tools/ledger.json`, which is the only place they are quoted.)**

---

## 11. Acceptance test — the external, unfakeable "done means"

**1e is DONE (the claim earned, for this one effect) when, and only when:**

> Through the **closed loop** (M-A broadcast Δ, corroborated by M-B), on **SWOW human association norms the project did not author**, with conditions selected **blind** and the prediction + direction + per-arm effect-size thresholds + the **conjunctive (a) ∧ (b) decision rule** **frozen in `docs/experiments/EXP-1e-priming.md` before any number is computed**, **BOTH** of the following hold: **(a)** STRONG-RELATED targets are more active than MATCHED-UNRELATED-BUT-REACHABLE targets (both reachable, both non-zero, distance-equalized), **AND (b)** HIGH-strength targets are more active than LOW-strength targets **held at equal path-distance** — each at its pre-stated effect size and direction, with the graded arm (c) corroboration in the same direction — and the result is **deterministic across hash seeds** and captured **verbatim**.

This is **unfakeable** because: (1) the norms are external; (2) the conditions are blind and frozen-hashed; (3) the crux controls force the related/control arms to differ **only** in human association strength — arm (a) holds **reachability** constant and arm (b) holds **path-distance** constant — so a pass **cannot** be explained by "a path exists" *or* by "a shorter path decays less"; the conjunction closes **both** of 2B's holes at once; (4) the direction, thresholds, and the conjunction are pre-registered; (5) determinism is asserted across processes.

**A null is a real result — including a single-arm null.** If the separation vanishes once reachability is controlled (arm a fails) **or** once path-distance is held constant (arm b fails — *the effect was topology/decay, not association*), that is reported honestly: the cognitive claim is **NOT YET / UNVALIDATED**, 1c/1d stay `BUILT · UNVALIDATED`, and it is **publishable** as "a pure spreading-activation substrate over human association norms does not, by itself, reproduce semantic priming beyond graph reachability/decay." Passing only the graded arm (c) is likewise an honest NOT YET. Either outcome is a genuine, citable Phase-1 result.

---

## 12. Where this leaves the roadmap

1e remains **DESIGNED** and **unblocked** (the loop closed at 1d-ii), and **all five open decisions are now RESOLVED** (§13). This spec turns it into a runnable, frozen-pre-registration experiment for the **validator**, with the reachability/decay confound that limited 2B confronted head-on by a **three-arm, conjunctive** control design: arm (a) holds reachability constant, arm (b) holds path-distance constant, and the headline is earned only if **both** survive (arm (c) graded corroboration). Nothing here is built or proven. When the validator runs it: a **positive** result (both categorical arms pass) moves 1c/1d *toward* meaning-validated **for the semantic-priming effect specifically** (the primary meaning bar, the first "door" of Phase 1) — it does **not** prove a mind; a **negative/NOT-YET** result — including failing arm (b) alone, reported as *"topology/decay, not association"* — is an honest, publishable outcome that leaves the cognitive claim UNVALIDATED and does not reopen lower bricks. The §6.2 (1c) structural check stays a recorded secondary item; **this is the headline.**

**Single next action:** the **validator** writes and freezes `docs/experiments/EXP-1e-priming.md` — the pre-registration enumerating the **three arms** and the **conjunctive (a) ∧ (b) decision rule**, frozen *before* any graded number — and the **builder** implements the separable §9 instrument B-i (broadcast-Δ reader) + §10 canonical-runner wiring B-ii (mechanism only, tester-verified), in that order. The decisions are settled; this is now an execution step, not a decision step.

---

## 13. Decisions — all RESOLVED (numbered; chosen option each)

All five decisions are resolved (human, this revision). They are recorded here as decided; the recommendations that produced them are preserved in §§4–10.

1. **Priming metric through the closed loop (§4) — RESOLVED.** **M-A (broadcast-trace Δ) is the headline** — the only metric that uses 1d-ii's broadcast and is genuinely "through the closed loop." **M-B (bare-spread) is retained as corroboration and the bridge to 2B.** **M-C (selection) stays rejected.** Accepted cost: M-A only primes targets inside the winner's coalition (the coverage is reported, not hidden).

2. **Control / baseline design — the crux (§5, §3) — RESOLVED, and STRENGTHENED to three arms.** **D-1 accepted** (matched-reachability categorical headline + graded-SWOW corroboration), **with the graded-only auto-fallback** retained (and reported honestly when triggered). **Strengthened:** D-1 closed only 2B's first hole (reachability), so a **THIRD arm (b)** is added to close 2B's second hole (decay): **distance-matched, strength-varied** (HIGH vs LOW SWOW strength at EQUAL path-distance). The registered structure is **three arms — (a) reachability control, (b) distance/decay control, (c) graded corroboration — with a binding conjunctive verdict rule: the headline requires BOTH (a) AND (b).** Passing only (c), or failing (b), is an honest NOT YET (*"topology/decay, not association"*). D-3's reachable-unrelated arm is folded into arm (a); the mediated contrast stays exploratory.

3. **SWOW relatedness signal + matched-pair construction (§6) — RESOLVED.**
   - **3a (signal):** **R123.Strength** for substrate + selection bands now (no rebuild, repo-consistent); **R1 (first-response) as a pre-registered robustness re-run** *if the headline passes* on R123. Raw counts rejected.
   - **3b (construction):** **algorithmic, seeded, blind** band-based selection for **all three arms** — arm (a) STRONG-direct vs matched in-horizon non-direct; arm (b) HIGH-direct vs LOW-direct at distance 1 (+ optional distance-2 by bottleneck path-strength); arm (c) the full equidistant strength range. Pair lists persisted **per arm** and hashed; percentile cuts, `MIN_OUTDEG`, horizon cap, and bottleneck definition fixed in the pre-registration. No cherry-picking; selection never sees activation.

4. **Pre-registration location + freeze discipline (§7) — RESOLVED.** **`docs/experiments/EXP-1e-priming.md`**, modeled on EXP-1c: anti-tamper notice, frozen-hashed per-arm pair lists, banner-printed-first, committed in a **separate commit before** any measured number. The pre-registration **must enumerate the three arms and the conjunctive (a) ∧ (b) decision rule.** Effect-size *numbers* fixed by the validator in that file before running; this spec fixes the *form*, the *direction*, and the *conjunction*.

5. **Harness reuse + canonical runner (§10) — RESOLVED.** **Reuse `swow.py`/`harness.py` unchanged; extend additively** (new 1e three-arm selection module + broadcast-Δ instrument). **Bring the instrument's *mechanism* tests (`test_harness.py` + the new B-i test) into `run_tests.py`** so 1e's instrument is tester-grade; **keep the data-dependent experiment-result scripts out** of the canonical runner. The human has **accepted the resulting shift** in canonical suite count and the tier-2/tier-3 boundary; the new counts are read from `docs/TEST_OUTPUT.txt` after wiring, never estimated.

**Routing reminder:** 1e is a **meaning** experiment → **validator** runs it; the only **builder** work is the separable §9 instrument (B-i) + canonical-runner wiring (B-ii). The builder does not interpret the result; the validator does not touch the frozen engine.

---

## 14. OUTCOME — 2026-06-21: ATTEMPTED · NO-GO (design infeasible on SWOW for anti-circularity reasons)

**This design was attempted and is INFEASIBLE on SWOW.** The blind, seeded three-arm stimulus selection was run (committed selector `dc07477`, `SELECTION_SEED = 20260621`, topology + R123.Strength only, **no activation**, on the full graph: **1,388,741 directed edges, 133,763 nodes**), and it shows the registered control design **cannot be graded without circularity on this corpus**. **No graded number was computed** — no `think()`, no activation, no Δ, no effect size. The full frozen record (counts, decile cuts, per-arm SHA-256 hashes, the structural reasoning) lives in the pre-registration's frozen-outcome section, **`docs/experiments/EXP-1e-priming.md` §15**; this section records the spec-level disposition. This is **not a failure** — it is a **structural finding learned before a graded run**, the anti-circularity discipline (CONTRIBUTING.md rule 5) doing exactly its job.

**The counts that force NO-GO (verbatim from the blind run; full table in EXP-1e §15.2):** all four arms populated (arm (a) = 300, arm (b)-d1 = 300, arm (b)-d2 = 300 [sub-arm populated], arm (c) = 300), but the §6.2 / §6.2.0 **loop-is-doing-real-work** leverage stratum collapses: **N_S0 = 7** (weight-blind `W_gap = 0` ∧ in-degree-matched) against the frozen `N_S0 ≥ 30` floor, with **N_S+ = 296** and **0** primes dropped for in-degree mismatch (global in-degree decile cuts `1, 1, 1, 1, 1, 2, 2, 5, 15`).

**The structural reason (the crux §3.2 line-87 residual, realized).** The substrate encodes SWOW strength as a **coarse, saturating integer edge weight** (`W = min(10, 1 + floor(strength · 100))`, `swow.traverse_count_for_strength`). A prime's HIGH band (its strongest associations) therefore almost always maps to a **strictly higher** integer weight than its LOW band (its weak associations), so weight-blind pairs (`W_gap = 0`) are **rare** — only 7 of 300. With S0 unpowered, the verdict routes to the pre-registered `N_S0 < 30` fallback (`V = r_MA − r_W ≥ 0.20`), but that fallback is **structurally unreachable here**: S+ dominance gives `r_W = 2·(296/300) − 1 ≈ 0.97`, so `V ≥ 0.20` would require `r_MA ≥ ~1.17`, and the matched-pairs rank-biserial **caps at 1.0**. Both forms of the §6.2 gate are foreclosed by the corpus's own weight structure **before any activation is computed** — there is no informative graded run to perform.

**The honest finding (plain language; the §1.1 framing stands in full).** *A spreading-activation substrate whose edge weights encode SWOW R123.Strength cannot, on this corpus, with **both** the edge-weight mechanical path and the target-popularity mechanical path controlled, separate genuine priming-through-the-loop from its own weight map.* SWOW strength and the substrate edge weight are too tightly coupled here: the saturating ladder makes HIGH outweigh LOW almost everywhere (S+ dominates), so the weight-blind leverage the design needed is too rare to power the gate and the fallback's value-added margin is arithmetically unreachable. **This does NOT claim priming is absent** — it is a statement about **measurability under anti-circularity controls on SWOW**, not about the phenomenon: weight and strength are too entangled on this corpus to tell genuine priming apart from a mechanical weight-map readback. A HIGH > LOW result here would have been **uninterpretable**, so the design correctly **declines to grade it**. Nothing here asserts understanding, comprehension, concepts, awareness, or that the system knows what words mean (§1.1).

**Disposition of this spec.** The SPEC-1e design (all five decisions §13) is recorded as **ATTEMPTED and INFEASIBLE-ON-SWOW for anti-circularity reasons.** No threshold was loosened to rescue it: the S0 floor, the shared-decile in-degree tolerance, the §7 effect-size bars, and the fallback margin are exactly as frozen; the in-degree tolerance was **not** widened to manufacture a powered S0. **`PROVEN` / `DESIGNED` stays separate and mechanism ≠ meaning is intact:** this is a meaning-layer experiment-feasibility finding and touches **no** mechanism status — **1c and 1d stay `BUILT · UNVALIDATED`, untouched; Phase 0 stays `PROVEN`; no lower brick is reopened.** The acceptance test in §11 is therefore **not met and cannot be met on SWOW under these controls** (the conjunctive (a) ∧ (b) verdict requires arm (b)'s §6.2 loop-work gate, which cannot be populated here).

**Re-route of the primary meaning bar.** Per the roadmap's pre-named, lower-circularity backup (roadmap 1e block: *"Fan effect is the safer, lower-circularity backup if priming proves too entangled — but it proves less"*), the **primary meaning bar is re-routed to the fan effect.** The fan effect is a **separate step** — to be specified (its own spec) and directed by the human after reviewing this freeze. **It is NOT started here.** This freeze is bookkeeping of the 1e NO-GO only.
