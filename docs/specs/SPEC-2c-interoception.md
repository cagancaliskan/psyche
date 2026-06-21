# SPEC-2c — Interoception ("the body's voice"): telemetry-derived body-state modulation of the cognitive cycle

Status: **FEASIBILITY PRE-CHECK COMPLETE → CLEAN (feasible, with binding design constraints); §6 DESIGN DECISIONS
RESOLVED (human, 2026-06-21); the determinism two-mode design (§3.2) is now a BINDING first-class commitment.**
This document **leads with a gating feasibility pre-check (§1)**, exactly as the 1e/fan-effect discipline now
requires. The full experiment design (§2 onward) is written **only because the pre-check clears**; had it hit a
structural wall, §1 would have stated the wall and stopped. The pre-check verdict (CLEAN) is **not re-litigated**
here; this revision folds in the human's six resolved decisions (§6) and makes the determinism two-mode design
binding (§3.2). **2c stays `DESIGNED`** — nothing here is built, run, or committed by this document; no mechanism
status changes.

Author: architect-pm
For: the **builder** (who implements the `BodySensor` + default-off modulation hook test-first, replay-
deterministic, and runs the §3.1 populability pilot) and the **validator** (who owns the graded meaning
experiment against a frozen, hashed pre-registration **if the pilot clears**). The §6 design decisions, formerly
open to the human, are now **RESOLVED** (2026-06-21) and folded into the binding design. This document writes
**no code**, runs **no code**, asserts **no** built or proven artifact, and computes **no** graded number. It is
`DESIGNED`-tier analysis and design only.

Depends on (read): the source design doc `docs/design/nous_the_bodys_voice.md` (the interoception "spark");
the two frozen NO-GOs that establish the gating pattern — `docs/experiments/EXP-1e-priming.md` §15 and
`docs/specs/SPEC-fan-effect.md` (what killed each, and why an engine-change rescue would not earn it); the
roadmap (`docs/nous_roadmap.md`, 2c is "you are here", the re-routed primary meaning bar); the frozen engine
(`src/nous_activation.py`, `spread_activation`); the closed loop (`src/nous_perceive.py` `think()`,
`src/nous_workspace.py` `select_winner` / `broadcast`); the substrate `Clock` (`src/nous_store.py`).

> **Scope discipline (CLAUDE.md rules 1–5).** This is **description, design, and feasibility analysis — not a
> result.** `PROVEN` and `DESIGNED` stay in separate boxes; nothing here is built. No mechanism status changes:
> 1c and 1d stay `BUILT · UNVALIDATED`; Phase 0 stays `PROVEN`; no brick is reopened. The honest-framing rules
> (rules 1–2) bind every line: a telemetry-modulated activation difference is **not** a feeling, an emotion,
> awareness, or "the body" in any literal sense — the design doc's evocative language ("the brain feels its
> body") is **vision, not claim**, and is quarantined to §0.1 below. The earned claim, if any, is narrow:
> *a variable computed from live machine telemetry causally and measurably changes the closed cycle's emergent
> behavior, in a pre-registered direction, gradable against the telemetry itself.*

---

## 0.1 The honest-framing firewall (read before anything — the design doc is vision, this spec is mechanism)

`nous_the_bodys_voice.md` is a **vision document**. It says the brain "feels" its heartbeat, that memory
pressure "is" muscular tension, that the system "panics." **None of that is a claim 2c may make.** Per CLAUDE.md
rules 1–2, this spec separates mechanism from meaning at every step:

- **What 2c can earn (mechanism + a narrow behavioral claim):** a scalar computed from live OS/process telemetry,
  injected at a defined point in the cycle, **causally changes** what the cycle does (what wins the workspace /
  how activation spreads / what consolidates) in a **measurable, pre-registered** way, and that change **tracks
  the live telemetry signal** (the external yardstick).
- **What 2c may never assert:** that the system *feels* anything, that the telemetry signal *is* an emotion or a
  body, that FRICTION/FLOW/GAP/OVERLOAD are experienced, or that any of this is consciousness/awareness. The
  design doc's six "signals ↔ biological equivalents" table is an **inspiration map**, not a fidelity claim.
- **Naming.** This spec uses **"body-state variable"** (a number) and **"telemetry-derived modulation"** (a
  mechanism), never "feeling" or "the body" outside this quarantined paragraph and direct quotes of the vision.

This firewall is itself an acceptance condition: any report from 2c that drops it is overclaiming and is void.

---

## 1. FEASIBILITY PRE-CHECK (GATING — answered before any experiment is designed)

**The one question (from the directive):** *Can live machine telemetry (CPU load, I/O timing, memory pressure,
elapsed wall-time, scheduling latency, interruption) become a body-state signal that MEASURABLY modulates the
closed cognitive cycle, such that the result is (a) genuinely telemetry-derived, (b) gradable against the
telemetry itself with no human-norm circularity, and (c) free of the association-family walls — while separating
real causal modulation from a trivially-wired pass-through, resolving the determinism tension, and staying
dependency-free?*

**Short answer: YES — CLEAN, with one binding design constraint.** Unlike both prior re-routes, the blocker that
killed each of them is **absent** here, and the trap unique to this paradigm (the pass-through) is **separable by
construction** because the cycle has a real emergent-competition stage (1d-i) downstream of the modulation site.
The "CLEAN" verdict is **conditional on the binding constraint of §1.4** (the modulation must enter *upstream* of
the workspace competition, and the graded readout must be a *competition/selection-level* emergent change, not a
readback of the injected scalar). With that constraint the pre-check clears on all sub-questions; without it the
design degenerates into the forbidden pass-through. The full design (§2+) is therefore written, built around
that constraint.

The pre-check has six parts: §1.0 restates the two prior walls so I test against the right failures; §1.1–§1.3
answer (a)/(b)/(c); §1.4 is the load-bearing part — the pass-through trap and its separability; §1.5 the
determinism tension; §1.6 dependency-free; §1.7 the gate verdict.

### 1.0 The two prior walls, restated precisely (so I test against the right failures)

The directive insists I confront both prior NO-GOs head-on. Stated exactly:

- **Wall 1 — the readback wall (1e priming, EXP-1e §15).** The prediction variable (SWOW R123.Strength) **was**
  the substrate edge weight (`W = min(10, 1 + floor(strength·100))`). So "related" and "strong-weight" were the
  **same number**, and the anti-circularity gate (a weight-blind stratum S0 where HIGH/LOW tie on weight)
  collapsed — `N_S0 = 7 < 30`, fallback unreachable (`r_W ≈ 0.97`). A HIGH>LOW result would have been the weight
  map read straight back out. **Root: the signal was internal to and derived from the very graph the substrate
  was built from.**
- **Wall 2 — the absent-mechanism wall (fan effect, SPEC-fan-effect §1.2/§1.4).** Anderson's fan effect requires
  a **shared-budget normalization** (a conserved source activation divided across out-edges, `S_ji ≈ S−ln(fan)`).
  The engine has no such conservation — `spread_activation` feeds every out-road the source's **full** activation
  (`outgoing = node_act`, no `/len(out_roads)`), so the fan curve is **flat to the last digit** and the closed
  loop inherits it. **Root: the generating mechanism the claim needs is structurally absent and cannot be reached
  by stimulus selection.**
- **The lesson both teach (and the §1.7 gate enforces).** Structural optimism over-predicted feasibility for 1e
  (reasoning said S0 would populate; the blind run said 7). So any feasibility claim from reasoning alone is
  **provisional** unless the blocker is *already* empirically settled (as the fan flat-curve was). I apply this
  to 2c honestly in §1.7: the pre-check clears on **structural** grounds, but it names exactly the **one
  empirical unknown** (effect-size populability) that a small instrumented pilot — not a reasoning claim — must
  confirm before the graded run, and it pre-registers the honest NOT-YET if that pilot comes back null.

### 1.1 Part (a) — Is the body-state variable GENUINELY telemetry-derived (live, not faked/hand-set/simulated)?

**YES, by construction, and this is the paradigm's foundational advantage.** The candidate signals are all
computed from **live OS/process telemetry** read at runtime:

| body-state variable | live telemetry source (stdlib) | what it measures |
|---|---|---|
| COMPUTE LOAD | `os.getloadavg()` (1-min load avg) and/or per-cycle `time.perf_counter()` Δ | how loaded the machine / how long the cycle took |
| ELAPSED-TIME / RHYTHM | `time.perf_counter()` deltas between cycle phases | per-cycle wall-time, rhythm regularity (variance of Δ) |
| CPU TIME vs WALL TIME | `time.process_time()` vs `time.perf_counter()` | scheduling pressure / contention (wall ≫ cpu ⇒ contended) |
| MEMORY PRESSURE | `resource.getrusage(RUSAGE_SELF).ru_maxrss` deltas | process resident-set growth (held-state proxy) |
| INTERRUPTION / LATENCY | scheduling-latency probe: measured Δ of a fixed-cost spin vs its baseline | preemption / jitter the process actually suffered |

**Why this is genuinely live, not faked:** the value is read from the OS at the moment the cycle runs; the
project does not author it, cannot author it, and (the §1.5 determinism point) must take deliberate steps to
*replay* it for testing precisely because it is otherwise uncontrollable. The "not faked, not hand-set, not
simulated" bar is met at the **boundary read** (the single `os.getloadavg()` / `perf_counter()` call); everything
downstream is deterministic transformation of that real read. **Contrast with 1e/fan:** in 1e the "external"
signal (SWOW) was real but **coupled to the substrate**; here the signal is real **and** external to both the
substrate and SWOW — it comes from the machine, a source the graph was not built from. **Part (a): CLEAN.**

**One honesty caveat, named now:** a body-state variable is only "genuinely telemetry-derived" if it is computed
from the read and **not** silently re-derived from graph state. E.g. MEMORY PRESSURE must come from
`ru_maxrss`/RSS, **not** from "number of active nodes in the field" (which would be a graph-internal quantity
wearing a telemetry costume — a soft re-entry of Wall 1). The §2 design fixes each variable to a **named OS
call**, and the §1.4 separability test forbids the graph-internal substitution. (This is the same vigilance the
interoceptive-machine framework's interoceptive-variable-vs-passive-telemetry distinction demands — see §1.1.1.)

#### 1.1.1 Prior art on the (a) boundary — interoceptive *variable* vs *passive telemetry* (the field's own distinction)

The genuinely novel part of 2c is *telemetry-as-interoception for a non-LLM cognitive substrate*; but the
**distinction that makes it rigorous is established prior art**, and I borrow it rather than reinvent it.

> **The load-bearing conceptual point stands on its own footing, independent of any single citation.** The
> distinction between an **interoceptive variable that influences control dynamics** and **passive telemetry that
> does not** is the conceptual basis for the §1.4 pass-through guard. It is sound *as a principle* — a number that
> changes the cycle's emergent behavior is categorically different from a number that is merely read and stored —
> and 2c's design would hold even if no external source had named it. The citation below is corroboration that the
> field names the same line; it is **not** a load-bearing dependency.

- **Candia-Rivera, D. (2026), "Interoceptive machine framework: Toward interoception-inspired regulatory
  architectures in artificial intelligence," *Cognitive Systems Research* (also arXiv:2604.24527).**
  *Verified (WebSearch, 2026-06-21): the paper, single author Diego Candia-Rivera, and the verbatim distinction
  below all confirmed.* *Establishes:* the exact line 2c must walk — the framework **"distinguishes interoceptive
  variables, which directly influence control dynamics, from passive telemetry, which does not."** This is, in the
  field's own words, the pass-through trap of §1.4. The framework's three principles (homeostatic, allostatic,
  enactive) are useful design vocabulary; 2c borrows only the *control-coupling* criterion and tests it.
  **(Provenance correction: an earlier draft mis-attributed this to "Sun et al." and an unverifiable arXiv ID —
  both were wrong and are corrected here; the author is Candia-Rivera and the verified ID is 2604.24527.)**
- **Springdrift (arXiv:2604.04660), an auditable persistent runtime for LLM agents with append-only stores
  including an affect store and a cycle-telemetry store, and continuous "ambient self-perception."** *Verified
  (WebSearch, 2026-06-21): the paper and arXiv ID exist; it is an **LLM-agent** runtime.* **UNVERIFIED in detail
  (WebFetch blocked in this sandbox):** the specific earlier-draft characterization that its affect subsystem
  "computes quantitative readings from observable cycle telemetry" and "exposes a valence/arousal readout from a
  homeostatic budget model" could **not** be confirmed at the source and is **not** relied upon. *Used only as a
  weak existence pointer* that an auditable runtime can carry an affect channel alongside cycle telemetry — and
  flagged as an **LLM** system, a different family from Nous's non-LLM substrate. **2c's pass-through guard does
  not depend on this reference** (see the boxed point above); it is retained, marked unverified, rather than
  asserted as settled prior art.
- **Craig, A. D. (2002), "How do you feel? Interoception: the sense of the physiological condition of the body,"
  *Nature Reviews Neuroscience* 3, 655–666.** *Establishes (in biology, not Nous):* interoception as a genuine
  sensory channel for the body's internal state, integrated in the anterior insula. **What Nous tests is only
  the computational analogue:** an internal-state scalar that modulates processing — **never** that Nous has an
  insula, a body, or a feeling.
- **Damasio, A. (1994), *Descartes' Error*; the somatic-marker hypothesis.** *Establishes (in biology):* bodily
  states bias decision/selection among options. **The 2c analogue, stated narrowly:** a telemetry-derived
  body-state variable biases **which coalition wins the workspace** (a selection bias) — the mechanistic shadow
  of a somatic marker, with **no** claim that the system has somatic feelings or makes decisions as a person does.

**What the literature establishes vs. what Nous would test.** The literature establishes that *biological*
interoception is real and shapes affect/decision, and that *artificial* systems can compute interoceptive-style
scalars from telemetry and must distinguish them from passive telemetry. **Nous would test only** whether *its*
telemetry-derived scalar **causally and measurably** changes *its* cycle's emergent selection/activation, tracked
against the live telemetry. A positive result is "a real machine-state signal demonstrably modulates the loop,"
never "Nous feels its body."

### 1.2 Part (b) — Is it GRADABLE AGAINST THE TELEMETRY ITSELF, with no human-norm circularity? (the key advantage)

**YES — and this is the decisive structural advantage of 2c over the entire exhausted association family.** State
it plainly:

> **The yardstick is the machine's own real, independently-measured state — not a human norm we could fool
> ourselves with.** In 1e the yardstick was human SWOW norms *and* the danger was that the substrate's own
> weights encoded them (Wall 1). In the fan effect the yardstick was human ACT-R norms *and* the danger was the
> engine couldn't produce the effect (Wall 2). In 2c the yardstick is **the telemetry trace itself** — a signal
> the substrate did **not** generate and cannot author. The "done means" compares **cycle behavior** (e.g.
> selection outcome, activation spread) **to the actual telemetry signal that was live during that cycle.** There
> is **no external human norm in the loop at all**, so there is **no human-norm circularity to navigate** — the
> 1c §6.2 "two algorithms over a shared graph agree" framing problem and the 1e "did we just read our own data
> back" framing problem **both vanish.**

Concretely, the gradable claim has the form: *across cycles, when the live body-state variable B is HIGH, the
cycle's emergent behavior shifts in pre-registered direction D relative to when B is LOW — and B is read from
live telemetry, the direction D is fixed in advance, and a within-design control isolates B from confounds.*
The grader correlates **a real measured machine signal** with **a real measured cycle outcome.** Neither side is
project-authored: the telemetry is the OS's, the cycle outcome is the substrate's emergent product. **Part (b):
CLEAN — this is the cleanest external yardstick on the entire roadmap**, because it is the only one where the
yardstick is a live physical measurement rather than a human-curated dataset. (The one thing §1.4 must still
guarantee: that "cycle outcome" is a *genuine emergent change*, not the injected B value read back out — else the
correlation is trivially 1.0 and proves nothing. That is the pass-through trap, handled next-but-one.)

### 1.3 Part (c) — Is it FREE of BOTH association-family walls?

**YES on both, and this is precisely why 2c was named the escape route.**

- **No weight-readback path (escapes Wall 1).** The body-state variable B is computed from **live OS telemetry**
  (`getloadavg`, `perf_counter`, `getrusage`, scheduling-latency probe — §1.1), which is **external to the SWOW
  graph and not derived from any edge weight.** There is no `W(P,T)` anywhere in B's definition. B cannot be a
  readback of the weights the graph was built from, **because it is not computed from the graph at all** — it is
  computed from the machine the graph runs on. The only way to re-introduce Wall 1 would be to define a "telemetry"
  variable that is secretly a graph quantity (e.g. MEMORY PRESSURE := active-node-count) — which §1.1's caveat and
  §1.4's separability test **explicitly forbid.** With B held to genuine OS sources, the readback wall is structurally
  absent.
- **No engine-can't-produce-it problem (escapes Wall 2).** The fan effect needed a mechanism the engine
  structurally lacked (shared-budget normalization) and could not be added without re-validating everything.
  **2c's modulation is the opposite case: it is a NEW, ADDABLE mechanism that the engine is already shaped to
  accept.** `spread_activation` already takes `energy`, `decay_per_hop`, `floor`, `hop_budget` as **first-class
  parameters** (`src/nous_activation.py` lines 162–166) — a body-state variable that scales `energy` or
  `decay_per_hop` is a **natural, in-grain modulation entry point**, not a missing conservation law. The cycle
  already has a real competition stage (1d-i `select_winner`) and a real feedback write (1d-ii `broadcast`) that
  a body-state variable can color. **The mechanism 2c needs is not absent the way fan normalization was absent —
  it is a parameter the engine already exposes.**

  **The crucial distinction from "the fan engine-change that wouldn't earn it" (confronted head-on, per the
  directive).** Adding source-activation normalization *to produce the fan effect* would not earn the fan effect,
  because (i) it changes the meaning of every prior activation result (forcing re-validation of 1c/1d) and (ii)
  it engineers the answer into the mechanism. **2c's modulation does neither, and the reason is structural, not
  rhetorical:**
  - It **does not change the unmodulated engine.** Modulation is a *gated overlay*: with body-state held at a
    neutral baseline (B = baseline ⇒ gain = 1.0, the identity), the cycle is **byte-identical** to the current
    1c/1d behavior. This is enforced exactly like 1d-ii's `broadcast=False` default-off path (`think()` is pure
    and unchanged when the feature is off). So 2c **does not force re-validation of 1c/1d** — they remain valid
    as the B = baseline case, and 2c is strictly additive. This is the opposite of the fan engine-change, which
    would alter the spreading law for *all* inputs.
  - The earned claim is **not** "we added a knob and the knob moved the output" (that would be the pass-through —
    §1.4). The earned claim is "a variable **computed from real, independent machine telemetry** is **causally
    coupled** to the loop's **emergent** behavior, in a pre-registered direction, gradable against that telemetry."
    The coupling is real because the **left side is a live physical measurement the substrate cannot fake** and
    the **right side is an emergent competition outcome distinguishable from the injected value** (§1.4). That is
    a genuine result about *the loop being coupled to real machine state* — the intended 2c architecture (body
    state colors processing) — verified by the coupling being real, **not** by wiring the conclusion in.

  **Part (c): CLEAN on both walls.**

### 1.4 THE PASS-THROUGH TRAP (this paradigm's S0-analogue) — pre-identified, and shown SEPARABLE by construction

This is the load-bearing section. **The danger unique to 2c** (the interoception analogue of 1e's S0 problem) is
the **trivially-wired pass-through**: inject a telemetry number B into the cycle and then "measure" B back out.
A correlation between B and "the cycle's B-readout" would be ~1.0 and would prove **nothing** — it is storing a
number and retrieving it, not modulation of cognition. The field names this exactly (Candia-Rivera 2026: an
*interoceptive variable that influences control dynamics* vs *passive telemetry that does not*). A genuine result
requires B to exert a **real causal effect on the cycle's EMERGENT behavior** — distinguishable from reading B
back. The pre-check must show this separation is **structurally achievable here**, not just desirable.

**It is structurally achievable, because the cycle has a genuine emergent bottleneck downstream of any injection
point: the 1d-i workspace competition (`select_winner` / `_density_score`), whose output is a SELECTED COALITION,
not a scalar.** This is the separability lever:

- **Where B is injected (upstream):** B modulates a **global spreading parameter** — the strongest candidate is
  `decay_per_hop` (or seed `energy`) in `spread_activation`. This is a *diffuse* effect: it changes how far/how
  strongly activation spreads from *every* seed, by a single global factor. B does **not** name any node, any
  coalition, any winner. (This is the design's analogue of a neuromodulator: a global gain/decay change, not a
  targeted command.)
- **What is graded (downstream, emergent):** **which coalition wins the workspace**, and/or **the size/composition
  of the winning coalition**, and/or **whether the over-swallow pruning boundary moves** — all *emergent products
  of the competition*, computed by `_density_score` over the whole field, not present anywhere in B. A global
  decay change can flip the winner (a higher decay shrinks far coalitions relative to near ones, changing the
  density ranking), prune differently, or change the broadcast trace — **none of which is "B read back out."**
- **Why this is NOT a pass-through (the concrete separation test, pre-registered):** the pass-through null would
  be "B correlates with a direct echo of B." The genuine claim is "B correlates with an **emergent selection
  outcome** that is a non-trivial function of the *whole field's competition*, not of B alone." The two are
  **distinguishable by a control the design fixes in advance** (§4): hold the **percept fixed** and vary **only B**
  (via replayed telemetry, §1.5); a pass-through would show B changing only a B-shaped readout, while genuine
  modulation shows **the winning coalition / pruning boundary / broadcast set changing** — a *categorical*
  emergent change (different winner, different members) that **cannot** be the injected scalar echoed, because the
  winner is a node-set produced by `_density_score` over all coalitions, and B is a single float that names no
  node. **The unfakeable signature of genuine modulation is a change in the discrete identity of what wins**,
  driven by a continuous global parameter — categorically distinct from retrieving a stored number.

**The binding design constraint that makes "CLEAN" hold (this is the §1 condition):**

> **(C-INJECT-UPSTREAM)** B must enter **upstream of the workspace competition**, as a **diffuse global
> spreading/decay/gain parameter that names no node and no coalition**; and **(C-GRADE-EMERGENT)** the graded
> readout must be a **competition/selection-level emergent change** (winner identity, winning-coalition
> composition, pruning-boundary movement, or broadcast-trace set) — **never** a direct readback of B or a
> monotone scalar echo of B. A design that injects B and reads B (or a rescaled B) back out is the forbidden
> pass-through and is **VOID**, not a result.

With (C-INJECT-UPSTREAM) ∧ (C-GRADE-EMERGENT), the pass-through trap is **separable by construction** — the
emergent competition stands between the injection and the measurement, and a categorical change in its discrete
output is the unfakeable evidence of genuine causal coupling. **This is the analogue of, and the answer to, the
S0 problem: where 1e could not find a stratum that separated genuine priming from a weight readback, 2c CAN
separate genuine modulation from a value readback — the separating structure (the emergent competition) exists
and is already built and tester-verified (1d-i).** That is the difference between a wall and a clearable gate.

**The one empirical unknown this leaves (named honestly, per the §1.0 lesson).** Structural separability is
proven above. What reasoning **cannot** guarantee is **effect-size populability**: whether realistic telemetry
swings (idle vs loaded machine) produce a global decay/gain change large enough to **actually flip enough
winners / move enough pruning boundaries** to clear a pre-registered effect size — or whether the cycle is too
*robust* (the competition ordering too stable) for plausible B ranges to change the discrete outcome. This is the
2c analogue of "will S0 populate," and the §1.0 lesson is explicit: **do not over-predict feasibility from
structure.** Therefore the design (§3) gates the graded run behind a **small instrumented populability pilot**
(does varying B across its real observed range change the winner/pruning for ≥ a pre-registered fraction of
probes?). If the pilot shows the cycle is too robust for real B ranges to produce emergent change, that is an
honest **NOT YET / structural finding** (*"the loop is causally couplable in principle but real telemetry ranges
do not move its emergent selection"*), reported as such — **not** papered over by widening B artificially (which
would be the forbidden move). This is the same gate 1e/fan applied; 2c applies it to its own one unknown.

### 1.5 The determinism tension (honest) — live telemetry is non-deterministic; the project bar (rule 7) is cross-process determinism. RESOLVABLE → now BINDING in §3.2.

> **This subsection established feasibility; the resolution is now a binding design commitment in §3.2** (the
> two-mode replay/live design, the frozen-and-hashed graded trace, and the simultaneous anti-circularity +
> determinism guards). §1.5 is retained as the feasibility analysis that motivated §3.2; §3.2 is the operative,
> binding text.

**The tension is real and must be stated, not finessed:** live telemetry (`getloadavg`, `perf_counter`,
`getrusage`) returns **different values on every read and on every machine** — it is intrinsically
non-deterministic, which collides head-on with the substrate bar (CLAUDE.md rule 7: identical output across
separate processes under randomized hash seeds). A naively telemetry-driven cycle would be **non-reproducible**
and could never be tester-verified as a mechanism.

**It is resolvable, and the substrate is already built for the resolution.** The pattern is **recorded/replayed
telemetry traces, with the single live read isolated at the boundary** — and the codebase **already has the exact
abstraction for this**: the `Clock` class (`src/nous_store.py` lines 72–91) has a **`simulated` mode** that
returns an injectable `self._t` instead of `time.time()`, precisely so "decay is observable instantly" and
deterministically in tests, with the live `time.time()` used only in real mode. 2c generalizes this proven
pattern to all telemetry:

- **A `BodySensor` boundary object** with two modes, mirroring `Clock(simulated=...)`:
  - **`live` mode:** reads real telemetry (`os.getloadavg()`, `time.perf_counter()`, `resource.getrusage(...)`)
    — used only at the real-run boundary; the **single point of non-determinism**, isolated behind one interface,
    exactly as `Clock.now()` isolates `time.time()`.
  - **`replay` mode:** reads from a **recorded telemetry trace** (a frozen sequence of body-state readings,
    hash-fixed) — fully deterministic, identical across processes and machines. **All mechanism tests and the
    graded determinism check run in replay mode**, so the substrate bar (rule 7) is met: byte-identical output
    across `PYTHONHASHSEED` in fresh processes, because the only non-deterministic input has been replaced by a
    frozen trace.
- **What this buys the graded experiment.** The meaning experiment is run in **replay mode against a recorded
  real telemetry trace** (recorded once from a real machine under varied load, then frozen and hashed like
  EXP-1c's partition or EXP-1e's pair lists). This gives **both** properties at once: the signal is **genuinely
  telemetry-derived** (it was recorded from real live telemetry — part (a) holds), **and** the graded run is
  **deterministic and reproducible** (replay of a frozen trace — rule 7 holds). The live read happens once, at
  recording time, at the boundary; the science is graded on the frozen replay. This is the **identical discipline**
  the project already uses (freeze the external artifact, hash it, grade against the frozen copy) — here the
  frozen artifact is a telemetry trace instead of a SWOW partition.
- **The honest boundary statement (pre-registered).** The claim "modulation tracks live telemetry" is
  established on a **recorded** live trace, not a re-read-every-time live feed; the report must state this. A
  *separate, non-graded* live-mode smoke test (run the cycle on truly live telemetry and confirm it runs and the
  modulation fires) demonstrates the live path works, but is **not** the graded result (because it is
  non-reproducible). This split — graded science on frozen replay, liveness demonstrated on a non-graded live
  smoke test — is exactly how rule 7 and "genuinely live" coexist. **Determinism tension: RESOLVED**, using a
  pattern already proven in the substrate.

### 1.6 Dependency-free (rule 8) — RESOLVED with the Python standard library alone

Every telemetry source in §1.1 is reachable with the **Python standard library** on ordinary compute:

- `os.getloadavg()` — stdlib `os`; available on Unix/macOS (the dev platform is darwin). **Honest flag:**
  `getloadavg` is **not available on Windows**; on Windows a stdlib fallback (per-cycle `perf_counter` deltas, or
  `os.cpu_count()` with timing) is used. The design **must** state a platform-portable default; I recommend the
  **`perf_counter`/`process_time` timing pair** as the *primary* body-state source (fully cross-platform, stdlib)
  and `getloadavg` as a *Unix-only secondary*. This keeps 2c dependency-free **and** portable.
- `time.perf_counter()`, `time.process_time()` — stdlib `time`; cross-platform, high-resolution. The
  **recommended primary** source (cycle wall-time, cpu-vs-wall contention).
- `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` — stdlib `resource`; Unix/macOS. **Honest flag:**
  `resource` is **Unix-only**; the cross-platform memory-pressure fallback within stdlib is limited
  (`sys.getsizeof` aggregates are graph-internal and thus **forbidden** by §1.1's caveat). **Recommendation:**
  treat MEMORY PRESSURE as a **Unix-only secondary** variable, and make the **timing pair the portable primary**,
  so the headline result needs no Unix-only call.
- Scheduling-latency / interruption probe — a fixed-cost spin measured by `perf_counter`; pure stdlib.

**No third-party dependency (`psutil` etc.) is required** for the recommended primary (timing-based) body-state
variable. `psutil` would give richer, more portable telemetry, but it is a dependency and is therefore **out of
scope** unless the human explicitly approves it (rule 8). **Recommendation: stay stdlib-only**, primary signal =
the `perf_counter`/`process_time` timing pair, with `getloadavg`/`getrusage` as Unix-only secondaries reported
alongside but not load-bearing for the headline. **Dependency-free: RESOLVED** (stdlib-only path exists and is
recommended).

### 1.7 GATE VERDICT

> **CLEAN — the interoception (2c) meaning experiment is FEASIBLE, conditional on the binding design constraint
> (C-INJECT-UPSTREAM) ∧ (C-GRADE-EMERGENT) of §1.4 and gated behind the §1.4 populability pilot.** All three
> directive sub-questions clear: (a) the body-state variable is genuinely live-telemetry-derived (§1.1); (b) it
> is gradable against the telemetry itself with **no human-norm circularity** — the paradigm's decisive advantage
> over the exhausted association family (§1.2); (c) it is free of **both** association-family walls — no
> weight-readback path (the signal is external to SWOW and the graph) and no absent-mechanism problem (modulation
> is a new, addable, gated-overlay mechanism the engine already exposes as parameters), and it escapes the
> fan-style "engine-change that wouldn't earn it" because it does not change the unmodulated engine and the earned
> claim is real causal coupling to live machine state, not a wired conclusion (§1.3). The pass-through trap — this
> paradigm's S0-analogue — is **separable by construction** because the emergent 1d-i competition stands between
> the diffuse injection and the categorical readout (§1.4). The determinism tension is **resolved** by the
> recorded/replayed-trace pattern the substrate's `Clock(simulated=...)` already proves (§1.5). The design is
> **dependency-free** on a stdlib-only timing-based primary (§1.6).

**This is the directive's first ending (CLEAN), with the §1.0 discipline honored:** the verdict is CLEAN on
**structural** grounds, and it does **not** over-predict the **one** empirical unknown (effect-size populability),
which is explicitly gated behind a small instrumented pilot (§1.4 / §3) whose null result is a pre-registered,
honest NOT YET. Because the gate is CLEAN, the full design follows (§2–§5) and the numbered design decisions are
surfaced to the human (§6).

**The honest asymmetry vs the two NO-GOs, stated for the record:** 1e hit a wall (the separating stratum was
empty); the fan effect hit a wall (the generating mechanism was absent). **2c hits neither** — the separating
structure (emergent competition) **exists and is built**, and the generating mechanism (parameter modulation)
**exists and is exposed.** What remains is not a wall but a **measurable empirical question** (do real telemetry
ranges move the emergent outcome enough), which is exactly the kind of question a graded experiment, gated by a
pilot, is *for*. That is the difference between "infeasible" and "feasible, go measure it."

---

## 2. The claim under test (narrow, exact — the design the pre-check unblocks)

> **Through the closed cognitive loop, a body-state variable B computed from live machine telemetry — injected
> as a diffuse global spreading parameter that names no node — causally and measurably changes the cycle's
> EMERGENT selection behavior (which coalition wins the workspace / the winning coalition's composition / the
> over-swallow pruning boundary), in a pre-registered direction, such that the change TRACKS the live telemetry
> signal (the external yardstick is the telemetry trace itself), and is DISTINGUISHABLE from a readback of B
> (the §1.4 pass-through control), with determinism intact across processes (replay mode).**

### 2.1 What 2c is NOT (the honest framing — travels with every report; per §0.1)

- 2c is **NOT** a claim that the system **feels**, has a **body**, has **emotions**, **interoception in the human
  sense**, **awareness**, or **consciousness**. The design doc's language ("the brain feels its body," "panic,"
  "muscular tension") is **vision/inspiration, quarantined to §0.1**, and may never appear as a claim.
- The system has **no felt states.** "The winner changes when load is high" is a statement about **a global
  spreading parameter, set from a telemetry number, changing an emergent competition outcome** — it is *not* a
  statement that the system experiences load, effort, stress, or anything at all.
- The mechanism corresponds, at most, to the **neuromodulatory-gain / somatic-marker-bias** *shadow*: a global
  state variable biasing selection. It is **not** a model of emotion, of the insula, or of feeling.
- A **positive** result establishes only: *a variable computed from real, independent live machine telemetry
  demonstrably and causally modulates the loop's emergent behavior, gradable against that telemetry, not a
  pass-through.* A **negative/NOT-YET** result (pilot shows the loop too robust, or modulation indistinguishable
  from pass-through, or direction fails) is equally honest, reported as-is; it leaves the claim unearned and does
  **not** reopen lower bricks.

---

## 3. Method (DESIGNED — for the builder, only on approval; built test-first, gated by the pilot)

**Three artifacts, in order; the graded run is last and gated. The determinism two-mode design (§3.2) is binding
on artifacts 1 and 3.**

1. **`BodySensor` boundary object (mechanism; tester-owned per §6.6; enters `run_tests.py`).** Two modes mirroring
   `Clock(simulated=...)`, per the §3.2 binding commitment: **`replay`** (reads a **frozen, hashed** telemetry
   trace — the entire deterministic test surface, (D-1)) and **`live`** (the single isolated non-deterministic
   boundary, (D-2), production only). The **headline body-state signal is the `perf_counter`/`process_time`
   friction signal** (§6.1); `os.getloadavg()` / `resource.getrusage(...).ru_maxrss` are **Unix-only secondary
   robustness signals**, each from its **named OS call only** and **never re-derived from graph state** (the §1.1
   asserted-negative is binding for the secondaries too, §6.1). Emits a normalized body-state scalar B ∈ [0,1]
   (or a small fixed vector) per cycle. **Determinism:** replay mode is byte-identical across processes/6 seeds
   (the rule-7 bar, (D-1)); live mode is isolated and non-graded ((D-2)). **Purity:** the sensor reads telemetry
   and graph-independent state only; it does not mutate the substrate.
2. **The modulation hook (mechanism; tester-owned per §6.6; default-OFF, gated-overlay).** B scales **`decay_per_hop`**
   (RESOLVED §6.2) — the diffuse global spreading parameter in `spread_activation`, threaded through
   `build_activation_field` / `think()` as an optional, default-neutral factor. **(C-INJECT-UPSTREAM):** the hook
   is upstream of `select_winner` and names no node/coalition. **Byte-identical-when-neutral:** with B at baseline
   ⇒ factor 1.0, the cycle is identical to current 1c/1d (enforced like 1d-ii's `broadcast=False`), so **1c/1d are
   not re-validated** and 2c is strictly additive. **No clamp/tunable magnitude tuned to an outcome** beyond the
   single principled mapping from B to the factor (fixed in advance).
3. **The graded meaning experiment (validator-owned per §6.6; NOT in `run_tests.py`; gated by the §3.1 pilot).**
   Run the closed loop in **REPLAY mode** against the **frozen, hashed recorded telemetry trace** (§3.2 (D-3)/(D-4),
   spanning a real low→high-friction range), on **fixed percepts**, varying **only B**, and grade the **emergent
   winner-flip** (§6.3) against the telemetry (§4). Pre-registration — including the §3.2 (D-4) trace-construction
   protocol — frozen before any graded number, EXP-1e-style.

### 3.1 THE POPULABILITY PILOT (gating — the §1.4 empirical unknown; run BEFORE the graded run, reported either way)

A small, instrumented, **pre-registered** pilot, analogous to EXP-1e's blind selection run: on a fixed battery of
percepts, sweep B across its **real observed range** (read from a **frozen replayed** telemetry trace, §3.2 —
**not** a live reading) and measure **what fraction of percepts show an emergent change** (different winner, or a
moved pruning boundary, or a changed broadcast set) between low-B and high-B. **Pre-registered go/no-go (RESOLVED,
§6.5): if < 30% of percepts** show *any* emergent change across the real B range, the loop is declared **too
robust for real telemetry to modulate**, and the result is an honest **NOT YET / structural finding** — *"the loop
is causally couplable in principle but real telemetry ranges do not move its emergent selection"* — **not**
rescued by inflating B beyond its real range. The 30% floor is **fixed before the pilot runs** and not loosened
after. If the pilot clears, the graded run proceeds. This is 2c's analogue of the `N_S0 ≥ 30` feasibility
checkpoint: **confirm the bar can be populated before grading.** Because the pilot sweeps a **frozen replayed
trace**, its pass/fail is itself **reproducible** (§3.2), not an unrepeatable live observation. (The pilot is
empirical and so cannot be run in this read-only step; it is the builder's, on approval.)

---

## 3.2 THE DETERMINISM TWO-MODE DESIGN (BINDING — a first-class design commitment, not a feasibility note)

This is a **binding design commitment** of 2c (the human's required addition, 2026-06-21), elevated from the
§1.5 feasibility analysis into a first-class constraint that the builder, tester, and validator are all bound by.
It exists so that adding a *non-deterministic* input (live telemetry) to the cycle does **not** breach the
substrate bar (CLAUDE.md rule 7: identical output across separate processes under randomized hash seeds). The
commitment has five parts, all binding:

**(D-1) DETERMINISTIC TEST MODE (replay) — the entire tester-grade mechanism surface.** The cycle is driven by
**recorded / replayed telemetry traces**: a fixed sequence of telemetry values captured once and **frozen**.
Identical replayed input MUST yield **byte-identical output across separate processes and across 6 `PYTHONHASHSEED`
values**, preserving the substrate determinism/integrity/purity bar (rule 7) **exactly as the tester verifies
every other layer** (1c, 1d-i, 1d-ii). **All tester-grade mechanism verification of the `BodySensor` and the
modulation hook runs in this mode** — replay only. A mechanism test that reads live telemetry is **not** a valid
mechanism test and is rejected.

**(D-2) LIVE MODE — boundary only, explicitly NOT part of the deterministic test surface.** Real
`perf_counter`/`process_time` telemetry is read **only at the boundary**, in production use. Live mode is the
**single isolated point of non-determinism** (mirroring `Clock`'s live `time.time()` read). Live mode is
**explicitly NOT part of the deterministic test surface**: it may be exercised by a **separate, non-graded live
smoke test** (run the cycle on truly live telemetry; confirm it runs and the modulation fires), which demonstrates
the live path works but is **never** a graded result and is **never** counted toward the rule-7 bar (it is
non-reproducible by construction).

**(D-3) THE GRADED RUN (the 30%-floor make-or-break) MUST be REPLAY over frozen traces spanning a real measured
range.** The pre-registered graded run — and the §3.1 populability pilot that gates it — MUST run in **REPLAY
mode over recorded traces** that span a **real measured friction range (low-friction → high-friction)**, with the
trace set **FROZEN before the pilot.** Stated plainly, and binding:

> **The make-or-break (does telemetry flip winners across the telemetry range) MUST be a reproducible result over
> frozen telemetry traces, NOT an unrepeatable live observation.** A winner-flip seen once on a live reading is
> **not** evidence; the same flip must be reproducible byte-for-byte from the frozen trace across processes and
> seeds, or it is **VOID** (instrument failure), not a result.

**(D-4) TRACE CONSTRUCTION IS PART OF THE FROZEN PRE-REGISTRATION (mirroring 1e's frozen-stimuli discipline).**
The frozen pre-registration MUST specify, **before** any graded number, the full trace-construction protocol —
the analogue of EXP-1e's blind, hashed pair lists:
  - **How real telemetry is captured:** the headline `perf_counter`/`process_time` friction signal (§6.1) is
    recorded from real live runs at the boundary, once.
  - **The range it must span:** the recorded trace set MUST cover a **real low-friction → high-friction range**
    (e.g. an idle/unloaded segment through a contended/loaded segment), so the sweep exercises the actual telemetry
    span, not a hand-widened one. (Inflating B beyond the real recorded range is the forbidden move, §3.1 / §4.1.)
  - **How the trace set is frozen and HASHED:** the recorded trace(s) are written to a fixed artifact, **SHA-256
    hashed**, and the hash recorded in the pre-registration — exactly as EXP-1e froze and hashed its pair lists and
    EXP-1c froze its partition. The graded run reads the **frozen, hash-checked** trace; a hash mismatch VOIDs the
    run.

**(D-5) BOTH GUARDS HOLD SIMULTANEOUSLY — neither is sacrificed for the other.** The design carries **two** guards
at once, and a result is valid only if **both** hold:
  - **The anti-circularity guard (§1.4):** the graded readout is a **winner-flip / emergent categorical change**,
    **never an echo of B**. (Pass-through ⇒ VOID.)
  - **The determinism guard (this §3.2):** the run is over **replayed frozen traces**, byte-identical across
    processes and 6 seeds. (Non-reproducible ⇒ VOID.)

  These are **independent and conjunctive.** A run that is reproducible but reads B back out is VOID (circularity).
  A run that flips winners but only on an unrepeatable live reading is VOID (non-reproducible). **2c earns its
  claim only when a winner-flip is BOTH emergent (not an echo) AND reproducible (frozen replay) — simultaneously.**
  Neither guard is relaxed to satisfy the other.

This commitment generalizes the substrate's already-proven `Clock(simulated=...)` pattern (`src/nous_store.py`):
the live read is isolated behind one boundary object (`BodySensor`, live mode), and the science is graded on the
frozen replay (`BodySensor`, replay mode) — the same freeze-hash-replay discipline the project already uses for
external artifacts, here applied to a telemetry trace instead of a SWOW partition.

---

## 4. Pre-registered "done means", with the control (telemetry-graded; pass-through-distinguishing)

All thresholds fixed **before any graded number**, by the validator. The headline rides on an **emergent**
readout, never a readback of B.

- **External yardstick:** the **frozen, hashed recorded telemetry trace** (§3.2: REPLAY mode, spanning a real
  low-friction → high-friction range) — a real machine signal the project did not author. **Direction fixed in
  advance** from the resolved headline signal (§6.1, the `perf_counter`/`process_time` friction signal): *higher
  friction (wall ≫ cpu / longer cycle) ⇒ higher `decay_per_hop` (§6.2) ⇒ activation stays more local ⇒ near,
  tightly-bound coalitions favored over far, diffuse ones*; the exact monotone direction is pre-registered, not
  discovered.
- **Headline readout (emergent; (C-GRADE-EMERGENT); RESOLVED §6.3):** the **categorical winner-identity flip** —
  across the trace, the **rate of winner-change** as B moves, tested for a **monotone association with B** in the
  pre-registered direction (a within-percept sign test on categorical winner-flips), with **winning-coalition
  compositional shift as graded corroboration** (e.g. Spearman of B against a scalar summary of the compositional
  shift). The grader correlates **replayed telemetry (B)** with an **emergent competition outcome** — and, per
  §3.2, the winner-flips must be **reproducible from the frozen trace across processes and 6 seeds**, not a one-off.
- **THE PASS-THROUGH CONTROL (the make-or-break gate; the §1.4 S0-analogue):** a **fixed-percept, vary-only-B**
  contrast in which a **pass-through null readout** (a direct echo of B, e.g. "the injected decay value") is
  computed alongside the emergent readout. The claim is EARNED **only if** the **emergent** readout (winner
  identity / coalition composition) shifts with B **categorically** — a *different node-set wins* — which the
  injected scalar provably cannot be, since the winner is produced by `_density_score` over the whole field and B
  names no node. **If the only thing that tracks B is a B-shaped scalar and the discrete winner/composition never
  changes, the result is the forbidden pass-through and is reported NOT YET** (*"telemetry was stored and
  retrieved, not causally modulating selection"*). This control is conjunctive with the headline: clearing a
  scalar correlation is **necessary but not sufficient** — the emergent categorical change is required.
- **Determinism (the §3.2 binding guard):** the graded numbers and the selected outcomes are **byte-identical
  across 6 `PYTHONHASHSEED` values in fresh processes in REPLAY mode over the frozen, hash-checked trace** (rule 7),
  or the run is **VOID** (instrument failure), not a result. A hash mismatch on the frozen trace also VOIDs it.
- **Both guards together (the §3.2 (D-5) conjunction):** the result is valid **only if both** the anti-circularity
  guard (winner-flip, not echo) **and** the determinism guard (replayed frozen traces, byte-identical across
  seeds) hold **simultaneously** — neither sacrificed for the other. Reproducible-but-echo ⇒ VOID; flips-but-
  unrepeatable ⇒ VOID.
- **Honest-framing assertion:** the report carries the §0.1 / §2.1 negations as an explicit asserted block; a
  report that drops them is void.

**The verdict rule (conjunctive, no post-hoc loosening):** the claim is **EARNED** iff (i) the §3.1 pilot cleared
its pre-registered populability floor, **AND** (ii) the emergent readout shifts with B in the pre-registered
direction at the pre-registered effect size, **AND** (iii) the pass-through control confirms a **categorical
emergent change** (not a scalar echo), **AND** (iv) determinism holds in replay. Failing any ⇒ honest **NOT YET**,
reported with which condition failed; **1c/1d stay `BUILT · UNVALIDATED`.** A null is a real, citable result
(*"a telemetry-derived body-state variable does not, on this loop, causally modulate emergent selection beyond a
pass-through"*).

### 4.1 What would FALSIFY the claim (stated in advance)

- **Pilot null:** real B range moves < the frozen fraction of percepts ⇒ NOT YET (*loop too robust*).
- **No emergent change, only a scalar echo:** the pass-through control shows the discrete winner/composition never
  changes with B ⇒ NOT YET (*pass-through, not modulation*) — **the make-or-break falsifier.**
- **Direction reverses:** emergent shift runs opposite the pre-registered direction ⇒ falsified.
- **B not genuinely telemetry-derived:** if B is found to be re-derived from graph state (§1.1 caveat) ⇒ VOID
  (circularity — a soft Wall 1) — caught by an asserted test that B's value depends only on the (replayed)
  telemetry trace, not on the graph.
- **Determinism breaks in replay** across hash seeds ⇒ VOID (instrument failure).

---

## 5. Why the closed loop is required (not the bare engine)

The bare engine could show "decay parameter changes activation" — trivially true and **a pass-through** (it is
just the parameter doing what parameters do). The **claim only becomes meaningful through the closed loop**,
because only the loop has the **emergent competition (1d-i)** that turns a diffuse global parameter change into a
**categorical selection change** distinguishable from a readback, and the **broadcast (1d-ii)** that lets a body
state leave a trace across cycles. **2c is therefore genuinely a Phase-1-loop result wearing a Phase-2 label** —
it needs exactly the cycle 1c/1d built, which is why it is the right re-routed bar: it tests the *built, verified*
loop against a *real, external, non-circular* yardstick.

---

## 6. DESIGN DECISIONS — RESOLVED (the human's calls, 2026-06-21; folded into the design above)

Exactly as 1e surfaced its five decisions. These were direction calls; the agent proposed, the human disposed.
**All six are now RESOLVED as below**, and each resolution is folded into the binding design (§1.5, §2–§4, and
the new §3.2 determinism commitment). The options are retained for the record; the resolved choice is marked
**RESOLVED →**.

1. **Primary body-state variable. RESOLVED → the timing pair (`perf_counter` vs `process_time`).** Options were
   (1a) timing pair `perf_counter`/`process_time` — cross-platform, stdlib, portable; (1b) `os.getloadavg` —
   **Unix-only**; (1c) a small vector. **The headline body-state signal is the wall-vs-CPU "friction" signal**
   (`perf_counter` measuring wall-time, `process_time` measuring CPU-time; their divergence is the friction the
   process actually suffered) — the portable stdlib headline. **Load-average and memory-pressure are SECONDARY
   robustness signals only**, reported alongside but **not** load-bearing for the headline. **Binding constraint
   on the secondaries:** every secondary must come from its **named OS call** (`os.getloadavg()`,
   `resource.getrusage(...).ru_maxrss`) and **NEVER** be re-derived from graph/internal state — the §1.1 caveat's
   asserted-negative against a soft Wall-1 re-entry (e.g. MEMORY PRESSURE := active-node-count) **stays and is
   binding for the secondaries too.** Rationale: keeps the headline stdlib-only and reproducible on any machine,
   avoids a platform gate on the headline, and quarantines the soft-circularity risk to a named OS boundary.
2. **Injection site / modulated parameter (the (C-INJECT-UPSTREAM) choice). RESOLVED → `decay_per_hop`.** Options
   were (2a) `decay_per_hop`; (2b) seed `energy`; (2c) `floor`. **The body-state variable modulates
   `decay_per_hop`** — the **upstream, node-naming-free global gain** that most directly changes the near-vs-far
   competition (so it is most likely to produce the emergent winner-flips the pass-through control needs), and a
   first-class `spread_activation` parameter already. It is the cleanest "neuromodulatory gain" analogue. Direction
   pre-registered: higher B ⇒ higher decay ⇒ near/tight coalitions favored over far/diffuse ones.
3. **Emergent readout for the headline (the (C-GRADE-EMERGENT) choice). RESOLVED → winner-identity flips (headline),
   coalition-composition shift (graded corroboration).** Options were (3a) winner-identity flips; (3b) winning-
   coalition compositional shift; (3c) pruning-boundary movement. **The make-or-break headline is the categorical
   winner-identity flip** — a *different winning coalition* is the pass-through-proof signal that a different
   winning coalition **cannot** be the injected scalar echoed (the winner is a node-set from `_density_score` over
   the whole field; B names no node). **Coalition-composition shift is graded corroboration.**
4. **Telemetry trace provenance + freezing. RESOLVED → one frozen, hashed real telemetry trace, graded in replay.**
   Options were (4a) one frozen real trace; (4b) a multi-trace battery. **The headline rides on one real telemetry
   trace, frozen and hashed (EXP-1e style), graded in REPLAY** (governed by the determinism design, §3.2). A
   **multi-trace battery is a later robustness re-run only**, used only if the headline is earned (the discipline
   of 1e's R1 re-run). The trace is recorded from **real live telemetry** (so part (a) holds) and **frozen** (so
   rule 7 holds) — see §3.2 for the binding trace-construction and freezing protocol.
5. **Pilot populability floor (the §3.1 go/no-go fraction). RESOLVED → 30% of percepts, fixed before the pilot.**
   Options were (5a) 30%; (5b) 50%; (5c) another value. **The floor is 30% of percepts showing emergent change
   across the real telemetry range, FIXED before the pilot runs and not loosened after.** Below it is an honest
   **NOT-YET** (*"the loop is causally couplable in principle but real telemetry ranges do not move its emergent
   selection"*). Rationale: low enough to be reachable if the coupling is real, high enough that clearing it means
   the modulation is not a rounding effect.
6. **Routing of the meaning claim. RESOLVED → BOTH lanes.** Options were (6a) validator owns the graded run;
   (6b) tester owns the sensor + hook. **Both, in lane:** the **tester owns the `BodySensor` + modulation hook**
   (mechanism — in `run_tests.py`, **replay-deterministic**); the **validator owns the graded meaning run** against
   the frozen trace. This is the standard mechanism ≠ meaning split (CLAUDE.md rule 2).

---

## 7. Where this leaves the roadmap

The primary behavioral meaning bar, re-routed to interoception (2c) after the 1e (readback wall) and fan
(absent-mechanism wall) NO-GOs, **passes its feasibility pre-check: CLEAN**, conditional on the binding
constraint (C-INJECT-UPSTREAM) ∧ (C-GRADE-EMERGENT) and gated behind a populability pilot. Unlike the two prior
re-routes, **2c hits neither wall** — the separating structure (the emergent 1d-i competition) exists and is
built, and the generating mechanism (parameter modulation) exists and is exposed — so what remains is a
**measurable empirical question**, not a structural wall. **The six §6 design decisions are now RESOLVED** (human,
2026-06-21): headline body-state signal = the `perf_counter`/`process_time` friction pair (load-avg/memory are
named-OS-call secondaries only, never graph-re-derived); injection site = `decay_per_hop`; headline readout =
categorical winner-identity flip (composition shift as graded corroboration); trace provenance = one frozen,
hashed real trace graded in replay; populability floor = 30%, fixed before the pilot; routing = both lanes
(tester owns sensor + hook, validator owns the graded run). **The determinism tension is now resolved by a
BINDING two-mode design (§3.2)** — all tester-grade mechanism verification runs in deterministic REPLAY over a
frozen, hashed trace; live telemetry is read only at the boundary and is explicitly outside the deterministic
test surface; the make-or-break graded run is a **reproducible** result over frozen traces spanning a real
low→high-friction range, not an unrepeatable live observation; trace construction is part of the frozen
pre-registration (hashed, mirroring 1e); and **both guards hold simultaneously** — the anti-circularity guard
(winner-flip, not echo) and the determinism guard (replayed frozen traces), neither sacrificed for the other.
The design is stdlib-only. **`PROVEN` / `DESIGNED` stays separate; mechanism ≠ meaning intact; 2c stays
`DESIGNED` (nothing built, run, or committed by this document); 1c and 1d stay `BUILT · UNVALIDATED`; Phase 0
stays `PROVEN`; no brick reopened; the engine-normalization question remains separately held and untouched.**

**Single next action:** the **builder** implements the `BodySensor` + **default-off** modulation hook
**test-first** (tester-owned, **replay-deterministic**, in `run_tests.py`) and runs the §3.1 **populability
pilot**; **the validator's graded run runs only if the pilot clears its 30% floor.** **If the pilot's
populability floor is not met, that is an honest NOT YET reported as-is** — feasibility was structural;
populability is the empirical gate, and it is allowed to fail. (The six §6 decisions are resolved, so no further
human decision gates the start of the build.)
