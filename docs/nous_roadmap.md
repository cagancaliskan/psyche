# Nous — The Road to a Mind

*A living roadmap. This is a map, not a contract. As real parts get built and tested, what we learn rewrites what comes next. The far end is a horizon, not a checkpoint we can schedule.*

Last updated: 2026-06-20 · Version 0.1 (first draft) · 1c mechanism independently tester-VERIFIED (PASS); §6.1 over-swallow re-scoped to 1d; meaning (§6.2) not yet earned

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
              1c source-clustering ✓built + tester-verified (mechanism)
              1d workspace + broadcast   1e first falsifiable result
  PHASE 0  ██  Foundations: substrate + activation             PROVEN
```

We are at the **end of Phase 0 and inside Phase 1**, specifically stuck-and-working at **1c**. Everything below 1c is real and verified. Everything above is the work.

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
> **Re-scoped to 1d (human decision, 2026-06-20):** "no over-swallow of a bridged, unperceived domain" is **not** a 1c criterion. After merging, a single source whose representative bridges into the unperceived `work` domain still pulls it in — there is no competing source to draw a seam. That is workspace-competition / coalition-pruning, which is 1d's job. Shipped as a passing asserted-negative that flips when 1d lands.
> **Done means — §6.2 meaning (validator), unchanged:** the grouping recovers external SWOW community structure better than the no-clustering control, ARI pre-registered (mean ≥ 0.30; lift ≥ 0.15; sign-test p < 0.05), direction fixed in advance. A null result is reported honestly and leaves the *meaning* unearned.
> **Decisions (all locked):** proximity = A1 topology only (A2 rejected); §6.2 labels = published SWOW partition preferred, frozen independent Leiden fallback; sequencing = finish 1c now.

**1d. Global workspace + broadcast** — `DESIGNED`
The missing piece that "strongest coalition = thought" is currently standing in for. One coalition wins a competition and is *broadcast* back onto the substrate, biasing the next cycle. This is what turns a one-shot pipeline into a loop.
> **Done means:** the broadcast measurably and predictably changes the *next* cycle's activation — a winning thought leaves a trace that shapes what comes next, in a direction stated in advance.
> **Inherited from 1c (re-scoped 2026-06-20):** the winning coalition must **not over-swallow a bridged, unperceived domain** — when one merged source bridges into a domain no source named (e.g. `coffee`→`work`), workspace competition / coalition-pruning must keep `work`/`code` out of the winning thought. 1c ships this as a passing asserted-negative that 1d is expected to flip.

**1e. First falsifiable cognitive result** — `DESIGNED`
The moment the cognitive layer earns the word "cognitive." Reproduce **semantic priming** — related primes retrieved faster/stronger than unrelated ones — where relatedness comes from a *published external association norm*, never from us.
> **Done means:** the known human direction is reproduced on data we did not author, with the prediction fixed before the run. (Fan effect is the safer, lower-circularity backup result if priming proves too entangled — but it proves less.)

> **🎯 Phase 1 milestone:** one complete cognitive cycle that runs on real input, closes the loop, and reproduces at least one external cognitive effect. This is the first result worth a real write-up, and the first "door."

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

The honest next action isn't to start a flashy new layer — it's to clear **1c**, because the loop has earned the right to keep finding problems before we pour more on top. After 1c is validated through the closed loop, **1d (workspace + broadcast)** makes it a real cycle, and **1e (priming)** makes that cycle mean something.

*Open question to decide together: do we go strictly in order (1c → 1d → 1e), or pull interoception (2c) forward early because it's your strongest original idea and a clean, independent win? Both are defensible.*
