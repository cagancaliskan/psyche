# Nous — The Road to a Mind

*A living roadmap. This is a map, not a contract. As real parts get built and tested, what we learn rewrites what comes next. The far end is a horizon, not a checkpoint we can schedule.*

Last updated: 2026-06-20 · Version 0.1 (first draft) · 1c mechanism tester-VERIFIED (PASS); §6.1 over-swallow re-scoped to 1d; §6.2 meaning experiment ran → NOT YET (ARI 0.228 < 0.30; beats control decisively, p≈6e-25); 1c stays BUILT · UNVALIDATED. **1d-i (competition + over-swallow pruning) BUILT · mechanism tester-VERIFIED (PASS) (2026-06-20)** — the inherited over-swallow asserted-negative is FLIPPED through the live loop; 1d-ii (broadcast + feedback) not built, so **1d overall stays `DESIGNED`**. **Design decisions logged 2026-06-20:** (i) the project's *primary* meaning bar is relocated from 1c §6.2 (one layer's partition vs an automatic partition) to the behavioral semantic-priming result at step 1e, graded against human association norms (§6.2 retained as a recorded secondary/structural check, not the headline); (ii) 1d-i's realized C1 pruning is the **parameter-free cohesion-valley / relative-attachment watershed** (not literal domain-membership), **accepted as the intended design** — the divergence is always safe-direction (over-includes an unnamed domain, never over-prunes a perceived member), with the bridged-≥-cohesion corner case logged as an accepted known-limitation (SPEC-1d §3.2 / §7 item 8).

---

## How to read this map

Every step has three things:

- **What it is** — the brick.
- **Depends on** — what has to be solid underneath before this brick can bear weight.
- **Done means** — the *external* test that lets us call it finished. Not "it runs," not "it looks right to me." A claim with a direction we cannot fake.

Each step carries a status tag:

- `PROVEN` — built and verified against hard properties or an external yardstick.
- `BUILT · UNVALIDATED` — the mechanism runs and is deterministic, but its *meaning* hasn't been earned yet.
- `DESIGNED` — exists as a vision document, not as tested code.
- `HORIZON` — genuinely open research. No agreed definition of "done" exists yet, even in the field.

---

## The path at a glance

```
  PHASE 4  ░░  Integration · development · the AGI horizon      HORIZON
  PHASE 3  ░░  Higher cognition (abstraction · self · language) DESIGNED
  PHASE 2  ░░  From a cycle to a persisting mind                DESIGNED
              (memory · sleep · interoception · emotion · drive)
  PHASE 1  ▓▓  One honest cognitive cycle            ◄── YOU ARE HERE
              1a field ✓built  1b coalitions ✓built
              1c source-clustering ✓mechanism verified · §6.2 NOT YET (secondary check)
              1d workspace + broadcast  (DESIGNED)
                 1d-i competition + over-swallow pruning ✓mechanism verified
                 1d-ii broadcast + bounded feedback  ◄ NEXT BUILD (closes the loop)
              1e first falsifiable result (priming) ◄ PRIMARY meaning bar
  PHASE 0  ██  Foundations: substrate + activation             PROVEN
```

We are at the **end of Phase 0 and inside Phase 1**. 1c's **mechanism** is tester-VERIFIED (PASS) and its **meaning** experiment (§6.2) has run → **NOT YET** (it beats the control decisively but misses the absolute ARI bar; see the 1c block). 1c stays `BUILT · UNVALIDATED`, and — by a decision logged 2026-06-20 — its §6.2 partition check is **not** the project's headline meaning bar; that role moves to the behavioral priming result at **1e**. **1d-i (competition + over-swallow pruning) is now BUILT and its mechanism is tester-VERIFIED (PASS)**: the over-swallow asserted-negative inherited from 1c is flipped through the live `think()` loop. But **1d-ii (broadcast + bounded feedback) is not built**, so **1d overall stays `DESIGNED`** and the loop is not yet closed; the next build is **1d-ii**. Everything below 1c (Phase 0) is real and verified. Everything above 1d-i is the work.

---

## PHASE 0 — Foundations `PROVEN`

The durable core. This is the part that's already a real, shippable, defensible artifact regardless of how far the rest goes.

**0a. Substrate store** — a graph of concept *nodes* and weighted *roads*. Roads carry emotional charge, access quality, and use-history; nodes stay neutral. Synaptic-tagging-and-consolidation dynamics: roads progress dirt → gravel → road → highway, strengthen with traversal, decay lazily, and "closed" (traumatic) roads stay *leaky, not inert* — a strong cue can still break through.

**0b. Spreading-activation engine** — deterministic, hop-layered single expansion, leaky-closure breakthrough, per-edge flow recording.

> **Done means — and this is met:** determinism (identical output across separate process runs under randomized hash seeds), integrity (graph indices stay mutually consistent through every mutation), purity (reads never mutate state). 130 assertions, 56 test functions, five suites, all passing.

---

## PHASE 1 — One honest cognitive cycle `IN PROGRESS`

The goal of this phase: **text in → a coherent, externally-validated thought out**, through one complete loop. This is the first "door" in the lego metaphor — the smallest thing that is recognizably a *cognitive act* rather than a graph operation. The loop follows the GWT/LIDA shape the design already commits to: perceive → activate memory → form coalitions → one wins the workspace → it broadcasts back and biases the next cycle.

**1a. Multi-source activation field** — `BUILT · UNVALIDATED`
Assigns each node to whichever source activates it most (basins, dominant source). Mechanism proven deterministic; cognitive meaning not yet claimed.

**1b. Coalition formation** — `BUILT · UNVALIDATED`
Single-source and field-based (basin) coalitions. Same status.

**1c. Source-clustering fix** — `BUILT · UNVALIDATED` *(mechanism implemented & independently tester-VERIFIED; meaning not yet earned — spec `docs/specs/SPEC-1c-source-clustering.md`)*
The real problem the closed loop surfaced: perception emits *clustered, overlapping* source sets, so basins are meaningless until nearby sources are merged or grouped first. Built: a deterministic, pure-read pre-processing stage between perception and field construction that groups nearby sources (single-link on a source proximity graph — A1 topology/road-strength only) and seeds the field from one representative per group. Integrated into the live `think()` loop without changing the perception surface or the field-builder signature.
> **Done means — §6.1 mechanism (tester), as re-scoped 2026-06-20:** on *real perceived input* through the closed loop, (a) `coffee/kitchen/morning` **merge into one group**, and (b) **no perceived source strands** as a singleton — both now pass; hand-placed groupings = automatic fail. *Tester verdict: PASS — full canonical run is 8 suites / 254 assertions, 0 failures, incl. the tester's adversarial suite and 6-seed cross-process determinism on randomly-generated hostile graphs.*
> **Re-scoped to 1d (human decision, 2026-06-20) — now fixed by 1d-i.** "No over-swallow of a bridged, unperceived domain" is **not** a 1c criterion. After merging, a single source whose representative bridges into the unperceived `work` domain still pulls it in — there is no competing source to draw a seam. That is workspace-competition / coalition-pruning, which is 1d's job. 1c shipped it as a passing asserted-negative; **1d-i has now flipped it** (mechanism tester-VERIFIED) — the bridged, unperceived `work`/`code` domain is pruned from the winning thought, via 1d-i's parameter-free cohesion-valley / relative-attachment watershed (SPEC-1d §3.2). One accepted corner case remains: an unnamed domain bridged **≥ its own internal cohesion** has no valley and is KEPT, so over-swallow can recur in that specific topology (accepted as a safe-direction known-limitation; SPEC-1d §7 item 8).
> **Done means — §6.2 meaning (validator):** the grouping recovers external SWOW community structure better than the no-clustering control, ARI pre-registered (mean ≥ 0.30; lift ≥ 0.15; sign-test p < 0.05), direction fixed in advance. A null result is reported honestly and leaves the *meaning* unearned.
> **§6.2 result (2026-06-20 — honest NOT YET).** Ran the pre-registered experiment (`docs/experiments/EXP-1c-swow-recovery.md`; external labels = a frozen, hash-verified, independent Louvain partition — a *different* algorithm family from the method under test; captured verbatim in `experiments/results/exp1c_output.txt`). Verdict by the frozen AND-rule: **NOT YET**; 1c stays `BUILT · UNVALIDATED`. No threshold was loosened after seeing results.
> - **The grouping is significantly, directionally right but fails the absolute bar.** 1c beats the no-clustering control **decisively**: lift +0.223 (≥0.15 ✓ P-b), sign test 170/200 probes beat the control vs 30 against, p≈6.2e-25 (✓ P-c), random-control sanity 0.010 ≈ 0 (✓). It fails the absolute threshold: **mean ARI(1c) = 0.228 < 0.30 (✗ P-a)**. So 170/200 probes are better-aligned with the external structure than no-clustering, yet the absolute agreement is capped.
> - **Diagnosed cause — granularity, not direction.** 1c **under-merges** relative to the coarse standard partition: it emits a mean of **~5.5 groups per 9-word probe** (min 5, max 8; 0/200 all-singleton) where the external Louvain partition is much coarser. ARI is **granularity-sensitive** (it penalizes a finer partition against a coarser truth even when the finer one nests correctly), so absolute ARI is structurally capped even though the grouping is directionally aligned. The honest read: *two clustering principles agree on the external structure's direction; they disagree on grain.*
> - **Framing (fixed, per the frozen pre-registration §3 / §8c).** Reported as **agreement with an independent standard partition, not ground-truth recovery** — 1c proximity (max directed road strength) and the Louvain grader both read the SWOW edge weights, so this is "two unrelated clustering algorithms over a shared external graph agree," not "1c recovers a gold-standard human-labelled taxonomy."
> - **Open design items — CONDITIONAL and DORMANT (not a backlog to start).** These are *only* to be revisited **if** 1d/1e show that grouping **granularity is load-bearing** for a downstream result, and **only** re-validated on **FRESH probe data never tuned to the EXP-1c set** (tuning against this set would be the circularity bug — forbidden, per the frozen pre-registration §8c and CONTRIBUTING.md rule 5): **(a)** the single-link **relative threshold** (`DEFAULT_PROXIMITY_FRACTION`, the shipped uncalibrated constant) — a coarser threshold would merge more and could lift absolute ARI; **(b)** the **proximity signal**, A1 (topology/road-strength, shipped) vs A2 (activation-overlap, rejected at build for circularity). Recording these so the diagnosis is not lost; **neither is dispatched and neither is a reason to reopen 1c now.**
> - **Why this is no longer the headline meaning bar (decision logged below).** §6.2 compares *one layer's partition* against *an automatic partition of the same graph* — even a clean pass would only show two clustering principles agree, which is low-value as evidence of cognition. The project's **primary** meaning bar is therefore relocated to the **behavioral semantic-priming result (step 1e)**, measured against **human association norms**: meaning is established by what the system *does*, not by one layer's partition shape. §6.2 is **retained as a recorded secondary/structural check**, in the `BUILT · UNVALIDATED` box where it belongs — it does **not** become "validated," and 1c is **not** reopened on its account.
> **Decisions (all locked):** proximity = A1 topology only (A2 rejected); §6.2 labels = published SWOW partition preferred, frozen independent Louvain fallback (used here); sequencing = next build was **1d** (since built as **1d-i**, tester-VERIFIED; the next build is now **1d-ii**).

**1d. Global workspace + broadcast** — `DESIGNED` *(split into 1d-i + 1d-ii; spec `docs/specs/SPEC-1d-workspace-broadcast.md`)*
The missing piece that "strongest coalition = thought" is currently standing in for. One coalition wins a competition and is *broadcast* back onto the substrate, biasing the next cycle. This is what turns a one-shot pipeline into a loop. **Built as two bricks (Decision E):** 1d-i (competition + over-swallow pruning; pure selection; no feedback) and 1d-ii (broadcast + bounded feedback; the single write that closes the loop). **1d-i is built and tester-VERIFIED; 1d-ii is not built, so 1d overall stays `DESIGNED`.** No cognitive claim is made by 1d — it is a selection-and-feedback *mechanism*, verified by the tester, not the validator.
>
> **1d-i (competition + over-swallow pruning)** — *BUILT · mechanism tester-VERIFIED (PASS) (2026-06-20)*. Replaces `coalitions[0]` with density-normalized competition (A2, min-size guard) and prunes the over-swallowed unperceived domain through the live `think()` loop (pure read; no write).
>   - **Mechanism done means — met:** through the live loop on system-generated coalitions, exactly one winner is selected deterministically and the over-swallow asserted-negative inherited from 1c is **flipped to a real pass** (the bridged, unperceived `work`/`code` domain is excluded from the winner), with an anti-overcorrection control (a *named* domain is never pruned) and generalization on an independently-built isomorphic-but-relabelled graph — all deterministic across 6 hash seeds, integrity-preserving, selection proven a pure read. *Tester verdict: PASS.*
>   - **Realized + accepted pruning rule (decision logged 2026-06-20):** the implemented C1 is the **parameter-free cohesion-valley / relative-attachment watershed** — keep a reached member iff it is pulled toward the named region at least as strongly as toward the unnamed region; else prune. It is threshold-free and generalizes. It is **NOT** literal domain-membership; an unnamed domain bridged **≥ its own internal cohesion** has no valley and is **KEPT**. Cagan **accepted the valley rule as the intended design** (no mechanism rework); the divergence is always **safe-direction** (over-includes an unnamed domain, never over-prunes a perceived member — verified across 60 random adversarial graphs). The corner case is logged as an accepted known-limitation (SPEC-1d §3.2 / §7 item 8), shipped as an asserted-negative.
>   - **No meaning claim:** 1d-i proves a selection *mechanism* only — not priming, not awareness.
>
> **1d-ii (broadcast + bounded feedback)** — `DESIGNED` (not built). The single, explicit, bounded write back onto the substrate (B1: bounded strengthening of the winner's internal roads) that biases the next cycle. This is what actually closes the loop and **unblocks 1e**.
>   - **Done means:** the broadcast measurably and predictably changes the *next* cycle's activation — a winning thought leaves a trace that shapes what comes next, in a direction stated in advance — and the feedback is proven **bounded both ways**: it does **not diverge** (converges toward a ceiling over many cycles) and does **not lock in** (a sufficiently strong fresh percept still changes the winner), at one untuned broadcast constant.

**1e. First falsifiable cognitive result** — `DESIGNED` *(the project's PRIMARY meaning bar — relocated here 2026-06-20)*
The moment the cognitive layer earns the word "cognitive." Reproduce **semantic priming** — related primes retrieved faster/stronger than unrelated ones — where relatedness comes from a *published external association norm* (SWOW human association data), never from us.
> **Why the primary bar lives here, not at 1c §6.2 (decision logged 2026-06-20).** Meaning is established at what the system *does*, not at one internal layer's partition shape. 1c §6.2 (a layer's partition vs an automatic partition of the same graph) is low-value as evidence of cognition — even a clean pass shows only that two clustering principles agree. A *behavioral* priming effect, graded against **human** association norms, is the externally-meaningful claim. 1c §6.2 stays a recorded secondary/structural check in the `BUILT · UNVALIDATED` box; this — 1e — is the headline.
> **Done means:** the known human direction is reproduced on data we did not author, with the prediction fixed before the run, against a baseline/control. (Fan effect is the safer, lower-circularity backup result if priming proves too entangled — but it proves less. NB: Phase 2A/2B already ran pre-registered fan-effect and graded-priming harnesses on SWOW — `experiments/results/` — which is prior scaffolding to reuse here, *not* a substitute for 1e's result through the closed cognitive loop.)
> **Routing:** this is a cognitive claim — the validator designs and runs the falsifiable experiment with a pre-registered, direction-fixed prediction; the builder does not assert its meaning.

> **🎯 Phase 1 milestone:** one complete cognitive cycle that runs on real input, closes the loop, and reproduces at least one external cognitive effect **graded against human data (the primary meaning bar — semantic priming at 1e)**. This is the first result worth a real write-up, and the first "door." The milestone is the *behavioral* effect, not any single layer's internal partition shape (1c §6.2 is a structural check beneath it, not the milestone).

---

## PHASE 2 — From a cycle to a persisting mind `DESIGNED`

A cycle that fires once is not a mind. This phase gives it continuity: memory across time, rest, internal body-state, and states that color processing. These are largely independent bricks, so the order below is a suggestion, not a hard chain — and **2c (interoception) is a strong candidate to pull early**, because it's your most original idea and unusually testable.

**2a. Memory hierarchy / consolidation (CLS)** — working → episodic → consolidated, with principled rules for what's kept versus what decays.
> **Done means:** a memory laid down in one session measurably shapes retrieval in a *later* session, and consolidation is shown to preferentially keep the traces it should.

**2b. Sleep / dreams** — an offline phase doing replay-style consolidation and pruning (sharp-wave-ripple lineage).
> **Done means:** an offline "sleep" pass measurably improves later retrieval and prunes weak roads, beaten against a no-sleep control.

**2c. Interoception — "the body's voice"** — primitive body-state signals derived from *real machine telemetry*: compute load, I/O pacing, memory pressure, elapsed time, interruption.
> **Done means:** the signals are genuinely derived from live telemetry (not faked) and demonstrably *modulate* the cycle — e.g., load measurably changes activation or selection behavior.

**2d. Emotional regulation as modulation** — road charge plus an arousal variable shaping how activation spreads (Yerkes–Dodson: too little or too much arousal both degrade retrieval).
> **Done means:** an arousal/emotion variable changes retrieval and consolidation in a measured, predicted direction.

**2e. Motivation architecture** — drives/goals that bias what wins the workspace and where attention goes.
> **Done means:** a motivational state predictably shifts *which* coalition wins the broadcast.

> **🎯 Phase 2 milestone:** a system that runs continuously, remembers across sessions, rests, and has internal states that color its processing. The "engine." Several of these (especially memory + sleep + interoception together) are independently publishable.

---

## PHASE 3 — Higher cognition `DESIGNED` *(the hard part)*

This is where engineering starts blending into open research. The bricks are real design goals, but the "done" bars get harder to set honestly, because we're approaching capabilities the whole field argues about.

**3a. Abstraction engine** — forming higher-order concepts from regularities across the graph (categories, schemas) rather than having them hand-coded.
> **Done means:** the system forms an abstraction *nobody hand-coded*, and that abstraction is shown to generalize to instances it hasn't seen.

**3b. Self-model** — a represented, queryable model of the system's own state and history.
> **Done means:** the self-model's predictions about the system's *own* behavior are measurably accurate — and, critically, falsifiable.

**3c. Language, grounded** — "how this brain comes to speak," across the three developmental stages, with language grounded in the substrate instead of an LLM bolted on the side.
> **Done means:** the hardest bar in the whole map. This needs the most careful, externally-graded criteria we'll have designed yet — and it's the step most likely to get split into many smaller bricks once we reach it.

> **🎯 Phase 3 milestone:** a system that abstracts, models itself, and grounds its own language. Reaching even one of these credibly would be a genuine research contribution in its own right.

---

## PHASE 4 — Integration, development, and the horizon `HORIZON`

Here the map gets deliberately blurry, and that's correct. Anyone who draws this part in sharp detail is guessing.

**4a. Full integration** — all systems running together in the closed topology (the "eight systems" and their tempos), stable over long runs without one subsystem corrupting another.

**4b. Development / bonding** — the "first caregiver" idea: the system matures through sustained interaction rather than being fully specified up front. Growth as architecture.

**4c. The AGI question** — flagged honestly: *there is no agreed definition of AGI and no agreed test for it.* This is exactly where this roadmap stops handing out "done" criteria. By the time we're here, the right move is no longer the builder's conviction — it's external evaluation, peer scrutiny, and letting *measured capability* define what's actually been reached. The horizon recedes as you walk toward it; the honest plan is to keep building verified parts and let them, not the dream, say where we are.

---

## Rules of the road (the discipline that makes lego bricks become a car)

These are the habits already paid for in Phase 0. They're what keep the stack compounding instead of collapsing three layers up.

1. **Reinvent the idea, borrow the scaffolding.** The novelty is the architecture, not the syntax or the substrate language. Spend the reinvention budget only where the genuinely new thing lives.
2. **Every brick proves itself before the next snaps on.** Loop-closure. A brick that "passes on a friendly input" hasn't passed — it's just waiting to fail under load.
3. **External yardsticks, never self-authored inputs.** The fastest way to fool ourselves is to grade the system on data we wrote. Relatedness, norms, baselines: all from outside.
4. **Keep `PROVEN` and `DESIGNED` in separate boxes, always.** The vision docs are description, not specification. Calling something built when it's only designed is the one move that poisons trust in everything else.
5. **Every phase ends in something shippable.** Even if the road stops at any phase, what's behind us should stand on its own as a real, citable artifact. Phase 0 already does.

---

## Where we go from here

1c has done its job for now: its mechanism is verified, and its meaning experiment ran and returned an honest **NOT YET** (decisively better than control, short of the absolute ARI bar — under-merging vs a coarse standard partition). Crucially, a decision logged 2026-06-20 establishes that 1c §6.2 was never the right *headline* for "meaning" anyway — comparing one layer's partition to an automatic partition of the same graph is low-value evidence of cognition. The project's **primary meaning bar moves to the behavioral semantic-priming result at 1e**, graded against human association norms: meaning is what the system *does*. 1c's §6.2 remains a recorded secondary/structural check, and 1c is **not** reopened to chase the absolute ARI number (the granularity tradeoffs are recorded as **dormant, conditional** items — revisit only if 1d/1e show grouping grain is load-bearing, and only on fresh data, never tuned to the EXP-1c set).

Since then, **1d-i (competition + over-swallow pruning) has been built and its mechanism is tester-VERIFIED (PASS)**: the over-swallow asserted-negative inherited from 1c is flipped through the live loop, via a parameter-free cohesion-valley / relative-attachment watershed accepted (2026-06-20) as the intended design (the divergence from literal membership is safe-direction only, with one corner case logged as an accepted known-limitation). 1d-i is pure selection — it makes **no** cognitive claim and writes nothing.

So the honest next action is **1d-ii (broadcast + bounded feedback)** — the single bounded write that actually closes the loop and that 1d-i's verified selection now stands ready to feed. Until 1d-ii is built and tester-verified, **1d overall stays `DESIGNED`** and the loop is not yet closed. **1e (priming)** then makes that closed cycle *mean* something against external human data — and 1e is blocked until 1d-ii lands.

*Open question to decide together: do we go strictly in order (1d-ii → 1e), or pull interoception (2c) forward early because it's your strongest original idea and a clean, independent win? Both are defensible.*
