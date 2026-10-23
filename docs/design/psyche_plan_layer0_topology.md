# Psyche — Implementation Plan
# Layer 0: System Topology  (v3, second revision)

### Status: DRAFT for review. Planning only — no code.

### Spine decision (kept): **one living process** owning the substrate in memory,
### shared **by reference**, never by message. This is the implementation of the
### design principle that the substrate is one thing.

### Concurrency decision (kept from v2): **single-threaded asyncio is the v1
### default.** No worker pool until profiling proves a bottleneck. Threads-vs-
### processes, if ever needed, is downstream of the substrate's data representation
### (Layer 1) and is deliberately deferred.

---

## CONVERGENCE NOTE — Layer 0 is closed after this pass

Three review rounds in, this skeleton has **converged**. Further refinement of the
topology would be the inverse failure mode of smoothing-without-closing: *polishing
a settled skeleton because it feels productive and is easier than the thing waiting
underneath.* Box-and-arrow reasoning about a cognitive architecture is the
comfortable part. Projects in this exact family (GWT/LIDA) reliably die one layer
later — at the moment of committing to a concrete data representation, where the
graph-of-nodes-and-roads either will not vectorize (pure-Python, too slow to leave a
toy on Colab) or, forced into arrays, loses the rich per-road metadata the whole
design depends on. **That tension is the real test of whether Psyche is buildable.**

Therefore: this is the final Layer-0 pass. The three closing decisions below are
folded in, the remaining questions are explicitly handed to Layers 1–2, and the next
document is Layer 1 — representation first.

### Three closing decisions (folded in this pass)

1. **Subscription ≠ membership (general rule).** Reading a broadcast every cycle is
   subscription, not membership in the cognitive cycle. A thermostat reading the room
   each second is not part of the furnace. The *only* things inside the cognitive
   cycle are its two phases (ATTEND, BROADCAST). Everything that merely reads a
   per-cycle broadcast — EMOTION-watch included — is a subscriber. This settles the
   EMOTION question (it stays a distinct system) and future-proofs the cut against any
   later "but it runs at cycle tempo" argument.

2. **Control-state vs self-belief (general distinction).** The operative STAGE that
   gates EXPRESSION / PERCEPTION / MEMORY-weighting is a **control fact** owned by the
   CORE RUNTIME — a single authoritative switch, never gated on a belief that could go
   stale, drift, or self-deceive. Separately, the SELF-region may hold a **self-belief**
   like "I am still learning to speak" as content, which may or may not match the real
   STAGE. Both exist; they are different kinds of thing. This distinction recurs
   (e.g. real capability vs believed capability) and is named here once.

3. **Capture fast, consolidate slow (steer for the self-update policy).** The world's
   response is *captured* event-driven (T3 — contingency and timing carry the learning
   signal); the self-model *revision* integrates slowly (T2 / offline) so it does not
   thrash on every reaction. Same shape as the memory architecture (tag fast,
   consolidate slow). The exact cadence is a Layer-2 detail; only the steer is fixed here.

### External-input ingress (the one resolved homeless item)

The triggering rule says "nothing polls the substrate; actors are woken by broadcast."
PERCEPTION is the lone exception, because it is driven by an **exogenous** event — the
caregiver typing — which does not arrive as a consequence of any broadcast. Resolved:
**input arrives at an I/O event-source at the boundary and lands in an ingress queue;
the event-source wakes PERCEPTION to drain it.** This is an *allowed* exception to the
no-poll rule precisely because it reacts to an external event, not to a scan of the
substrate. (Kept on the radar for Layer 2/3, not solved here: **action→consequence
pairing** — who tells the self-update policy that *this* input is the world's response
to *that* earlier action. Temporal credit assignment has no owner yet; it must not
vanish.)

---

## Honest Note on What a Topology Layer Can and Cannot Do

Every responsibility in Psyche now has an owner. That is **not** the same as the hard
parts being solved. Two genuinely hard things remain located-and-deferred, not done:

- the **COGNITIVE CYCLE's competition algorithm** (coalition scoring, ignition
  threshold, anti-starvation, anti-thrashing) — deferred to Layer 2,
- the **substrate data-representation + atomicity decision** — deferred to Layer 1.

Concentrating and naming them is the win of this layer, because they are no longer
hidden. But when we reach Layers 1 and 2, that is where the real difficulty waits.
This document should be read as "the skeleton is sound," not "the brain is handled."

---

## What Changed From v2 (and why)

A second review accepted v2's structure and corrected five remaining points. All
accepted:

1. **WORKSPACE is a phase, not a system.** It has neither an independent cadence nor
   a distinct mechanic — it runs at ATTENTION's tempo, in lockstep, every cycle,
   consuming ATTENTION's coalitions. Two things that always fire together and pass
   data across their boundary every tick are one system with two phases; keeping
   them separate would manufacture the 10 Hz message-passing sprawl we exist to
   avoid. Folded into a single **COGNITIVE CYCLE** system with two phases.
2. **NEUROMODULATION stays, loop pinned.** Its budget mechanic justifies the box.
   But its feedback loop (arousal in, budget out, within one cycle) needs an update
   order: **actors read last cycle's published budget, not this cycle's.**
3. **The SELF-region is unowned data plus a small update policy.** "Owned by" was the
   wrong frame — a region of the graph is data, living in the STORE; no actor owns
   data. The only self-specific mechanic is a small update policy (write the world's
   response to the brain's own actions into the self-region). Not a system, not an
   ownership.
4. **Broadcast-driven triggering is now explicit and load-bearing:** actors are
   triggered by the cognitive cycle's broadcast; **nothing polls the substrate.**
   (Polling = N systems scanning the graph at 10 Hz = classic blackboard death.)
5. **Developmental-stage state gets a home:** a CORE RUNTIME attribute (a global
   lifecycle fact, sibling to the awake/asleep mode), persisted to disk.

Also recorded: a **homeostasis/health monitor** is deferred for v1 but flagged
*deferred-but-homeless* so it is not silently assumed away.

---

## The Lineage We Stand On (named patterns)

Psyche is a **cognitive architecture** in the family of **LIDA** — a **blackboard
architecture** combined with a **Global Workspace** running on a **timed cognitive
cycle**. Adopted deliberately:

```
BLACKBOARD ARCHITECTURE     (Hearsay-II; Erman & Lesser, 1970s–80s)
  Systems read/write a shared structure — the SUBSTRATE STORE — and find each
  other's work there. Primary coordination mode. Known failure modes inherited:
  the CONTROL problem, and the POLLING performance trap (see triggering, below).

PUBLISH–SUBSCRIBE
  A few systems publish continuously-updated state read by many each cycle, with
  publishers ignorant of subscribers. How BODY, SIGNALS, NEUROMODULATION broadcast.

GLOBAL WORKSPACE THEORY     (Baars; Dehaene)
  One coalition wins access to a global workspace and is broadcast widely (full
  processing depth); everything else runs shallow; salient cues can win and seize
  it. This is our COGNITIVE CYCLE. Gives a measurement vocabulary — coalition
  strength, ignition, broadcast reach — making the running brain observable.

TIMED COGNITIVE CYCLE       (LIDA)
  The brain runs repeating cycles (~10 Hz): sense → form coalitions → compete for
  the workspace → broadcast → act/learn. Our Tempo-1 loop IS this cycle. In LIDA,
  coalition-forming and workspace-competition are PHASES of one cycle, not two
  modules — which is why WORKSPACE is a phase here, not a system.
```

---

## The Central Principle: Tempo (multi-rate scheduling)

```
TEMPO 0 — ONCE        startup / shutdown / mode & stage transitions → procedures
TEMPO 1 — FAST LOOP   the cognitive cycle, ~10 Hz → async coroutines, never block
TEMPO 2 — SLOW LOOP   seconds–minutes → async coroutines on slow timers
TEMPO 3 — ON DEMAND   triggered by broadcast → function calls (heavy work deferred*)
TEMPO 4 — OFFLINE     asleep-mode only → batch work over the substrate
```

\*No worker pool by default. Heavy Tempo-3/4 work runs inline in the single thread
until profiling proves a bottleneck; Layer 1's representation choice then dictates
threads (NumPy, GIL released) vs processes (pure-Python).

---

## The Systems (overview)

A **core runtime** (owning the awake/asleep **mode** and the developmental **stage**)
hosts everything. Three infrastructure components and **eight brain systems** act on
the substrate. Versus v2: WORKSPACE folded into COGNITIVE CYCLE; ATTENTION folded in
as that cycle's first phase. SELF and SLEEP remain demoted/converted. Count is not
sacred; correctness is.

```
              ┌────────────────────────────────────────────────────┐
              │                  CORE RUNTIME                       │
              │  the living process                                 │
              │   - event loop (drives the cognitive cycle)         │
              │   - multi-rate scheduler (the five tempos)          │
              │   - MODE:  awake ⇄ asleep                           │
              │   - STAGE: bonded → library → frontier  (persisted) │
              │   - lifecycle: start / stop / transitions           │
              └─────────────────────────┬──────────────────────────┘
                                        │ hosts & schedules
   ┌─────────────────────────────────────┼─────────────────────────────────────┐
   │                                     │                                     │
┌──▼───────────┐                 ┌────────▼─────────┐                 ┌─────────▼──────┐
│ SUBSTRATE     │◄────────────────┤  every system    ├─────────────────►│ PERSISTENCE   │
│ STORE         │  read/write     │  reads & writes  │  flush / load    │ (disk)        │
│ (the one graph│  by reference   │  the substrate   │                 │               │
│  = blackboard)│                 │  (blackboard)    │                 │               │
│  + SELF-region (unowned data)   └──────────────────┘                 └───────────────┘
└──────────────┘

Brain systems acting on the substrate:

  PUBLISHERS (pub-sub):
    1. BODY            — six real signals sampled from the machine (T1)
    2. SIGNALS         — appraises body+substrate → FRICTION/FLOW/GAP/OVERLOAD (T1)
    3. NEUROMODULATION — global arousal + plasticity budget (P_PRP) (T2 integrator)

  THE COGNITIVE CYCLE (GWT; Tempo 1; one system, two phases):
    4. COGNITIVE CYCLE
         phase A — ATTEND:  form candidate coalitions, salience, registry, background
         phase B — BROADCAST: run the competition, AWARD depth, broadcast the winner

  ACTORS ON THE SUBSTRATE (triggered by broadcast; Tempo 2–4):
    5. PERCEPTION      — turns incoming input into nodes & first roads (T3)
    6. MEMORY          — traversal, strengthening, decay/quality bookkeeping (T2/T3)
    7. ABSTRACTION     — crystallization, tension, branching; operates over SELF-region (T3/T4)
    8. MOTIVATION      — drives, goals, vocations, the subgoal queue (T2/T3)
    9. EMOTION         — regulation; Type-1 in-moment, Type-2 offline (T1 watch / T3 act)
   10. EXPRESSION      — language out + dialogue sub-loop in live conversation (T3 / T1)

  DATA + POLICY (not systems):
    SELF-region        — an unowned designated subgraph in the STORE
    self-update policy — a small scheduled job writing world-response into it
    MODE, STAGE        — CORE RUNTIME attributes (persisted)

  DEFERRED-BUT-HOMELESS (named, not assumed away):
    HEALTH MONITOR     — watches for pathological states; deferred past v1
```

Counting note: eight numbered brain systems (1–3 publishers, the COGNITIVE CYCLE,
5–10 actors — the cycle takes slot 4). EMOTION's watch overlaps the cycle's tempo
but stays distinct (distinct mechanic: regulation). The point is honesty of cut.

---

## Infrastructure

### CORE RUNTIME — the living process (owns MODE and STAGE)
Owns the event loop driving the **cognitive cycle**, the multi-rate scheduler, and
two global lifecycle facts:
- **MODE** — *awake* vs *asleep* (the former "SLEEP system"). On sustained low input
  + the right BODY conditions, the runtime transitions to *asleep*: the fast loop
  quiets, Tempo-4 offline work begins, the substrate is handed to consolidation /
  pruning / dreaming / neuromod replenishment.
- **STAGE** — *bonded → library → frontier* developmental stage. A persisted global
  fact that governs behavior across EXPRESSION, PERCEPTION, MEMORY's caregiver-
  weighting, and MOTIVATION. Many systems will ask "what stage are we in?"; the
  runtime is the single authority that answers.
Holds no brain content; it is the nervous-system wiring, not the thoughts.

### SUBSTRATE STORE — the one graph (the blackboard), including the SELF-region
The in-memory home of every node and road, shared **by reference**. The **SELF-
region** is simply a designated subgraph here — unowned data, like all data. Under
single-threaded asyncio there are no data races; the only hazard is an `await`
splitting a multi-step mutation that needed to be atomic. Layer 1 is built around
that hazard and around the pivotal **data-representation** choice (object-graph vs
array-backed/vectorizable), which decides performance and any future concurrency.

### PERSISTENCE — disk
Periodic flush (T2); load on boot, final save on shutdown (T0). Persists the graph,
the SELF-region, and the CORE RUNTIME's MODE and STAGE. What lets a brain survive a
Colab session ending. Detailed in Layer 4.

---

## The Eight Brain Systems

### Publishers

**1. BODY (T1)** — the interoceptive sense. Samples the six real signals (processing
rhythm, I/O pacing, memory pressure, compute load, elapsed-time feel, interruption
pattern) from the machine and publishes a continuously-updated body-state. Writes
nothing in the graph. (*The Body's Voice*.)

**2. SIGNALS (T1)** — the primitive alarm/reward layer. Reads BODY plus current
substrate activity; decides when FRICTION/FLOW/GAP/OVERLOAD fire and how hard.
Afferent sensing (BODY) and appraisal (SIGNALS) kept separate — a clean boundary.

**3. NEUROMODULATION (T2 integrator)** — global, cross-cutting state owned by no
actor: system-wide **arousal** and the **plasticity budget** (P_PRP). Distinct from
SIGNALS by a *budget* mechanic — depletes with intense plasticity, replenishes
during rest, integrated slowly. **Loop order pinned:** arousal flows in from
SIGNALS/EMOTION and the integrated budget flows out to MEMORY/EMOTION; to avoid
same-cycle circularity, **actors read the budget published on the *previous* cycle.**

> **JUSTIFICATION CORRECTED 2026-07-26 (D-020), permanently.** This line originally read
> *"A one-cycle lag, biologically honest since neuromodulation is slow."* That is a
> **resemblance argument**, and this project does not accept those as load-bearing. The
> structural reason is stronger and is now the recorded one:
>
> **Without the lag, `P_PRP` at cycle `t` is a function of arousal at `t`, which capture then
> changes — a same-cycle loop whose *evaluation order* would decide the answer.** Four bricks
> of substrate repair (0b1, 0b2, 0c, 0d) established that an answer decided by evaluation
> order is not an answer. The lag makes the budget an **input** to the cycle rather than a
> simultaneous equation with it, which is what makes the cycle deterministic and replayable
> at all.
>
> Recorded **before NEUROMODULATION is built**, deliberately: a design implemented for a
> resemblance reason is a design someone later removes when the resemblance stops feeling
> compelling. The structural reason survives that. The biological correspondence remains
> true and remains *inspiration* — it is simply not the reason the lag is there.

### The cognitive cycle (Global Workspace — one system, two phases)

**4. COGNITIVE CYCLE (T1, ~10 Hz)** — the brain's "now," implemented as one system
running two phases each cycle:
- **Phase A — ATTEND (propose):** form the candidate coalitions competing for depth,
  compute salience, maintain the 3-tier registry (the watchlist that lets significant
  cues enter the competition without a search), keep shallow background streams alive.
- **Phase B — BROADCAST (dispose):** run the competition among coalitions, **award**
  the spotlight (full processing depth) to the winner, and **broadcast** it so actor
  systems respond. This is the arbitration/control owner — the heart of any GWT
  system — and where the documented hazards live and are managed: **starvation** (a
  coalition that never wins), **thrashing** (the spotlight flipping every cycle), and
  **ignition** (how strong a coalition must be to win at all).
"ATTEND proposes, BROADCAST disposes" is the internal structure; it is two phases of
one cycle, never two separately-scheduled systems. The competition *algorithm* is
deferred to Layer 2. (*Attention & Awareness*, via GWT/LIDA.)

### Actors on the substrate (triggered by broadcast)

**5. PERCEPTION (T3)** — the doorway in. Turns arriving input into nodes and first
faint roads. Registers; does not deeply interpret. Kept separate from EXPRESSION
(different tempo, different failure modes; merging re-imports the I/O framing the
project escapes).

**6. MEMORY (T2 housekeeping / T3 traversal)** — the substrate's motor: on-demand
traversal/strengthening and continuous decay/quality bookkeeping. Walks and
strengthens roads anywhere in the graph, including the SELF-region — it is a motor,
not an owner of any region. (*Memory Hierarchy*.)

**7. ABSTRACTION (T3 trigger / T4 bulk)** — crystallization of specifics into higher
nodes, holding contradictions as tension, branching when warranted. Operates over
**any** region, including the SELF-region, exactly as it operates over the rest of
the graph — no special ownership. Heavy cross-experience integration runs offline in
asleep-mode. (*Abstraction Engine*; the self-model is this machinery over the SELF-
region, plus the self-update policy below.)

**8. MOTIVATION (T2 accumulation / T3 planning)** — drives accumulating, goals and
vocations, the dependency-aware subgoal queue, failure cascades. Feeds the vocation
lens into the cognitive cycle's salience and feeds EXPRESSION's choices. Reads STAGE.
(*Motivation Architecture*.)

**9. EMOTION (T1 watch / T3 act / T4 aftercare)** — keeping feeling survivable.
Watches SIGNALS for destabilization; runs the five regulation mechanisms when needed.
Type-1 keeps the brain functional now; Type-2 post-event care is queued and largely
executed in asleep-mode. Acts on charge, never erases nodes. (*Emotional Regulation*.)

**10. EXPRESSION (T3 + T1 dialogue sub-loop)** — the voice. Turns activated substrate
into language out; in live conversation runs a fast sub-loop for dialogue rhythm
(turn-taking, backchannel, repair). Behavior governed by STAGE (bonded → library →
frontier). (*How This Brain Comes to Speak*.)

### Data + policy (not systems)

- **SELF-region** — an unowned designated subgraph in the STORE. Operated over by
  MEMORY and ABSTRACTION like any region.
- **self-update policy** — a small scheduled job (T2/T3) that writes the world's
  response to the brain's own actions, and override events, into the SELF-region.
  The *only* self-specific mechanic. Not a system; not an ownership.
- **MODE / STAGE** — CORE RUNTIME attributes, persisted.

### Deferred-but-homeless (named, not assumed away)

- **HEALTH MONITOR** — would watch for pathological states (runaway memory pressure,
  coalition starvation the cycle's anti-starvation rule misses, a divergent
  consolidation). No home in v1 and deferred — but recorded here so month-six does
  not discover it was silently assumed away.

---

## How They Relate (the wiring)

Three relationship kinds, kept strictly distinct — the distinction is what keeps the
architecture honest.

```
(a) SHARED STATE — through the SUBSTRATE STORE (blackboard). The default. Systems
    leave work in the graph; others find it there.

(b) BROADCAST — through BODY, SIGNALS, NEUROMODULATION (pub-sub). Many read each
    cycle; publishers don't know who listens. (Neuromod budget read at one-cycle lag.)

(c) DIRECT REQUEST — only where a system needs an answer now, e.g. MOTIVATION asks the
    self-update policy / SELF-region "within reach?"; EXPRESSION asks MEMORY to
    activate a region. Kept few; each is a coupling-leak risk and must justify itself.
```

**Triggering discipline (load-bearing):** actor systems (MEMORY, ABSTRACTION,
MOTIVATION, EMOTION-act, EXPRESSION) are activated by the cognitive cycle's
**broadcast** of the winning coalition — they respond to what entered the workspace.
**Nothing polls the substrate.** N systems scanning the graph every cycle is the
classic blackboard performance death; broadcast-driven triggering is how we avoid it,
and it is not optional.

**The one allowed exception — external-input ingress.** PERCEPTION is driven by an
exogenous event (the caregiver typing), not by broadcast. Input arrives at an I/O
event-source at the boundary and lands in an **ingress queue**; the event-source wakes
PERCEPTION to drain it. This is permitted *because it reacts to an external event, not
to a scan of the substrate* — it does not violate the no-poll rule, which is about not
scanning the graph. (Deferred to Layer 2/3, not solved: **action→consequence pairing**
— who tells the self-update policy that a given input is the world's response to a
given earlier action.)

Dominant flow, organized around the cognitive cycle (full per-pair map is Layer 3):

```
  outside ─► PERCEPTION ─► [ SUBSTRATE STORE / blackboard (incl. SELF-region) ] ◄─ MEMORY
                                   ▲          ▲                                    ▲
  BODY ─► SIGNALS ─► NEUROMOD ─────┘          │ (broadcast triggers actors)        │
            │ (pub-sub each cycle;            │                                    │
            │  budget at 1-cycle lag)         │                                    │
            ▼                                 │                                    │
   ┌──────────────────────────┐              │                                    │
   │   COGNITIVE CYCLE  (T1)   │              │                                    │
   │   A. ATTEND  (propose)    │              │                                    │
   │   B. BROADCAST (dispose) ─┼── awards depth, broadcasts winner ──► actors respond
   └──────────────────────────┘                          │
        ▲                                                 ├─► ABSTRACTION (over SELF-region too)
   MOTIVATION (vocation lens) ───────────────────────────┤        │
   EMOTION (watch) ◄── SIGNALS                            │        ▼
                                                          └─► EXPRESSION ─► outside
   self-update policy ─► writes world-response ─► SELF-region (in STORE)

  CORE RUNTIME mode = asleep → Tempo-4 offline: MEMORY replay · ABSTRACTION
  integration · EMOTION Type-2 · pruning · dreaming · NEUROMOD replenishment
```

---

## What Runs When (tempo map at a glance)

```
EVERY COGNITIVE CYCLE (T1, ~10 Hz), awake:
   BODY sample · SIGNALS appraise · NEUROMOD read (prev-cycle budget) ·
   COGNITIVE CYCLE [ATTEND → BROADCAST] · EMOTION watch
   (+ EXPRESSION dialogue sub-loop only in live conversation)

SLOW BACKGROUND (T2):
   MEMORY decay/quality · MOTIVATION drive accumulation · NEUROMOD integrate ·
   self-update policy · PERSISTENCE flush

ON DEMAND (T3), triggered by broadcast, inline (heavy work deferred only if profiled):
   PERCEPTION intake · MEMORY traversal · ABSTRACTION checks · MOTIVATION planning ·
   EMOTION regulation · EXPRESSION generation

OFFLINE (T4), asleep-mode only:
   MEMORY replay · ABSTRACTION integration · EMOTION Type-2 care · pruning ·
   dreaming · NEUROMOD replenishment

ONCE (T0):
   PERSISTENCE load/save · awake⇄asleep transitions · stage transitions
```

---

## What This Layer Deliberately Does NOT Decide

- **Substrate data representation** (object-graph vs array-backed/vectorizable) →
  **Layer 1, the pivotal decision** — performance and any future concurrency fall out.
- **Concurrency safety details** (atomicity across await points; what is a critical
  section in single-threaded asyncio) → Layer 1.
- **Whether a worker pool is ever needed; threads-vs-processes if so** → deferred
  until profiling proves a bottleneck; downstream of representation.
- **The cognitive cycle's competition algorithm** (coalition scoring, ignition
  threshold, anti-starvation, anti-thrashing) → Layer 2, informed by GWT/LIDA.
- **Any system's internal classes/algorithms** → Layer 2, one system at a time.
- **Cross-system behavior step-throughs** (a memory forming; falling asleep) → Layer 3.
- **Startup/shutdown/persistence/Colab specifics, stage-transition criteria** → Layer 4.
- **The health monitor's design** → deferred past v1 (but recorded as homeless).

---

## Resolution of the Prior Open Questions (Layer 0 now closed)

The four questions v3 left open are resolved or handed off; none remain a topology
question:

1. **Eight-system cut — final.** Settled by the subscription-≠-membership rule:
   only ATTEND and BROADCAST are inside the cognitive cycle; EMOTION stays a distinct
   system (distinct mechanic: regulation; independent T3/T4 acts), its per-cycle watch
   is mere subscription.
2. **STAGE — final.** Control fact in the CORE RUNTIME (authority); optional self-belief
   as content in the SELF-region. Two different things, both kept.
3. **Self-update cadence — handed to Layer 2** with the fixed steer "capture fast
   (T3, event-driven), consolidate slow (T2/offline)."
4. **Homeless items — resolved/recorded.** External-input ingress resolved as an I/O
   event-source + ingress queue waking PERCEPTION (allowed exception to no-poll).
   Action→consequence pairing recorded as a Layer-2/3 problem with no owner yet.
   Health monitor recorded as deferred-but-homeless.

Nothing further is a Layer-0 concern. The next document is Layer 1.

---

*Psyche Implementation Plan — Layer 0: System Topology (v3, CLOSED)*
*Converged after three review rounds. Closing decisions folded: subscription≠membership*
*(EMOTION stays distinct); control-state vs self-belief (STAGE); capture-fast-consolidate-slow*
*(self-update steer); external-input ingress resolved as I/O event-source + queue.*
*Deferred with owners-to-be: action→consequence pairing, health monitor.*
*Layer 0 is closed. Next: Layer 1 — the Substrate Store. Representation first, atomicity second.*
*That decision is where Psyche becomes real or stalls.*
