# SPEC-2f — Temporal credit assignment: giving the unowned problem an owner

**Status:** DESIGNED · **all three decisions closed by D-020** (§3.4 → C, §2.3 → assert dead,
§4.3 → caller-supplied scalar) · **blocked on 0d, which ships first**
**Revises:** nothing yet. §3 costs three ways of not revising much.
**Depends on:** 0a `PROVEN` (the store), 0d (the accumulation registry, §6)
**Date:** 2026-07-26
**Author lane:** architect-pm

---

## 0. Framing

### 0.1 What this is

**Temporal credit assignment is a mechanism, and this spec treats it as one.** The question
is narrow and answerable: *when an outcome occurs at cycle `t+k`, which of the roads
traversed at cycle `t` should be strengthened, and by how much?*

That is arithmetic over a bounded history. It is not learning-in-the-cognitive-sense, not
reward, not motivation, and not a self-model — **all of which the vision corpus builds on top
of it, which is exactly why it must exist first.**

### 0.2 What this is not, stated before anything else

No cognitive claim is made or approached. A system that reinforces a road because an outcome
followed it is doing **bookkeeping over a time window**, not valuing, wanting, or learning
from consequences in any sense a psychologist would recognise. The vocabulary in the corpus —
"credit", "capture", "consolidation", "salience" — names arithmetic here, exactly as
"competition" and "budget" do in SPEC-0b2 §0.1.

If this brick lands, the meaning bar is **exactly where it was**: open, after three
structurally distinct refusals.

### 0.25 Two labels a reader will over-read, corrected here rather than in a ledger note

**`0d` is `PROVEN`. That means the gate does what it says — not that it catches everything.**
Nine documented holes remain after 2f closes L3 as its step zero, each with a falsifier and
an asserted negative. **The order-dependent-accumulation class is not closed; it is
ENUMERATED**, which is a different and more honest thing, and the distinction is the entire
product of brick 0d. A reader who sees `0d PROVEN` and concludes the class is shut will be
wrong in exactly the direction this project's method exists to prevent. This is said here,
in the brick that builds *on* the gate, because here is where someone will act on the
misreading.

**And 2f satisfies ZERO of the five AOL autonomy criteria** (SPEC-2e). It is a prerequisite
for three of them, because without a mechanism connecting an outcome to an earlier action
there is no "learned" for those criteria to measure. **Being a prerequisite is not partial
credit**, and adopting a yardstick must not become adopting a roadmap.

### 0.3 Why this is the pivot off substrate work

Four bricks of substrate repair (0b1, 0b2, 0c, 0d) have earned a foundation that is now
`PROVEN` and structurally deterministic. That is the right moment to ask what the foundation
is *for* — and the answer the corpus keeps deferring is this.

---

## 0.5 STEP ZERO — mandatory, before any credit-assignment code is written

**Teach the gate to see tuple-target accumulation, then build the thing that would have
hidden in it.**

The 0d tester measured the line this brick is most likely to write:

```python
trace[rid], counts[rid] = trace[rid] + e, counts[rid] + 1
```

**Zero findings.** The float accumulation is lost to 0d's L3 (tuple targets are not
detected); the integer counter was never in scope and is correctly out of it. Split across
two lines, the float site is caught. So **the gate built to catch 2f's accumulations misses
the one accumulation 2f adds** — and it misses it on the most idiomatic way to write it.

**Why this is 2f's task and not 0d's.** 0d's deliverable was the gate, and its scope closed
by decision (D-022). Ownership sits with the brick that needs the coverage. That placement
is the point rather than a convenience: **2f's first act becomes a demonstration that
extending the gate is a normal cost of building on it.** A gate that no brick is ever
required to extend is a gate that silently narrows every time the code grows past it, and
this project has already watched that happen three times with the same defect class.

**A passive sentence in a spec would not be enough**, and saying so is not rhetoric: this
same cycle rejected exactly that pattern for the absence bounds — a recorded intention that
nothing enforces — and replaced it with a machine check. Accepting a passive note here,
one section after that decision, would be incoherent.

**Step zero, concretely:**
1. Extend the detector to report tuple-target accumulation (`a, b = a + x, b + y`), with the
   integer element still exempt on the existing structural rule.
2. Prove it by injection, per SPEC-0d F-3: a planted tuple-target fold turns the build red.
3. Retire L3 from `ledger_check.py`'s scope block and convert its asserted-negative in
   `tests/test_tester_0d_adversarial.py` to a positive assertion — **converted, not deleted**,
   per the standing rule.
4. **Only then** write credit-assignment code.

**L7 is deliberately NOT part of this.** An integer counter is not a float accumulation;
that is out of scope, not a hole, and widening the rule to cover it would produce exactly
the false-positive noise SPEC-0d §6 names as the way a registry stops being read.

---

## 1. The hole, and its exact shape

`docs/design/nous_plan_layer0_topology.md` lines 64–68, in the Layer 0 topology's own words:

> *"(Kept on the radar for Layer 2/3, not solved here: **action→consequence pairing** — who
> tells the self-update policy that *this* input is the world's response to *that* earlier
> action. **Temporal credit assignment has no owner yet; it must not vanish.**)"*

It vanished. Layers 2 and 3 were never written — **there is no `teknik_planlar/` directory in
this repository at all**, verified, so the deferral target does not exist as a document.
Meanwhile every downstream vision document presupposes the mechanism:
`nous_motivation_architecture_v2.md`, `nous_self_model.md`, `nous_emotional_regulation.md`
each assume that an outcome can reach back and change a connection that preceded it.

**The pyramid is upside down**: the layers that depend on credit assignment are specified in
detail, and credit assignment is a parenthesis.

---

## 2. The plasticity-model conflict — and it is already resolved, differently than assumed

### 2.1 The premise, corrected

The brief describes two incompatible models: (a) the biology document's continuous tag and
capture, and (b) *"Module 01 / `src/nous_store.py` — an integer `traverse_count` ladder
(5 / 20 / 100)"*, with (b) having shipped.

**Checked against the code, and (b) did not ship.** There are three models, not two:

| | Model | Status |
|---|---|---|
| (a) | `nous_substrate_biology.md` §1.3, §2 — continuous ω with tag τ, global pool `P_PRP`, capture | **never implemented** |
| (b) | `nous_memory_hierarchy.md` §1.3 — integer ladder, `traversal_count` 1–4 / 5–19 / 20–99 / 100+ | **never implemented either** |
| (c) | `src/nous_store.py` — continuous `strength ∈ [0,1]` with lazy decay; quality is a **derived view** via float ceilings `DIRT_CEILING=0.20`, `GRAVEL_CEILING=0.50`, `ROAD_CEILING=0.80` | **this is what shipped** |

`quality_of()` reads `road.strength`, a float. It does not read `traversal_count`. And
`traversal_count` is written (`+= 1` in `strengthen`) and copied into decayed views, but
**read by nothing in `src/`** — verified by grep: three occurrences, one declaration, one
increment, one copy.

### 2.2 What that means for the question asked

The question *"is the integer ladder kept as a derived view over a continuous ω, or
removed?"* **was already answered in the code, in favour of the view, before this spec
existed.** `Road.strength` *is* ω: continuous, bounded [0,1], lazily decayed, and the
quality names are a presentation layer over it.

This is the single most consequential fact in this document, because it means **2f does not
have to replace a plasticity model. It has to add a time dimension to one that already
exists in the right shape.** ω is there. What is missing is τ, and the rule that connects an
outcome at `t+k` to a road touched at `t`.

That makes this brick far cheaper than the framing implied — and the cheapness is the reason
§3 can offer an option that touches Tier 1 not at all.

### 2.3 DECIDED (D-020) — leave it, document it, and **assert it dead**

It is dead weight: written, never read, and it invites exactly the confusion that produced
the premise above.

- **(A) Leave it, document it as vestigial.** Zero cost. Mild ongoing confusion, now
  mitigated by this section existing.
- **(B) Remove it.** A change to `Road` in a Tier 1 `PROVEN` module: re-verify 0a's purity,
  integrity and determinism, plus every `dataclasses.replace` / view-construction site.
- **(C) Give it a job** — make it the tag's traversal counter.

**DECIDED: none of the three as offered — (A) plus enforcement.** Leave it, document it at
the declaration, **and add an asserted-negative that it remains unread in `src/`.**

**The rationale is measured harm, not tidiness.** This vestigial field **already caused a
documentation error** — it is why this brick was commissioned on a false premise one turn
ago (§2.1). `traversal_count` exists and looks exactly like Module 01's ladder, so it misled
the person commissioning the work. That is not a hypothetical cost; it is a cost already
paid.

Removing it is still a Tier-1 change to freshly-restored code for a cosmetic gain, so it
stays. But **"document it" becomes "enforce it"**, which is this project's idiom — at the
price of one comment and one test, and no Tier-1 change. If anyone starts reading it, the
test goes red and forces a decision rather than a discovery.

**Routed to the builder** (`src/` comment + `tests/test_nous_*.py` assertion); not
architect-pm's to write.

---

## 3. Three designs

All three deliver the §7 done-means. They differ almost entirely in **what they cost against
a `PROVEN` store**, and that is the axis on which to choose.

All three ship as a **gated overlay**, per the project's established discipline
(`broadcast=False`, `body_sensor=None`, `normalization_sigma=None`): a default-off parameter
whose neutral value is **byte-identical** to current behaviour. That is not negotiable and
is not one of the tradeoffs.

### 3.1 Design A — full tag and capture, in the store

τ becomes a field on `Road`, decaying like `strength`. A global `P_PRP` gates a capture sweep
that applies `ω ← ω + μ·(τ·P_PRP)` to every road whose τ exceeds a threshold.

Faithful to `nous_substrate_biology.md` §2, and the only option that delivers **behavioural
tagging** — a weak trace preserved because a *strong, unrelated* event flooded the system
within the same window. That is the property the biology document is actually about, and no
other option has it.

**Cost — the highest, and it lands in the worst place.** A new mutable float on `Road` in
Tier 1: `_compute_decay`, `get_road`'s view construction, purity snapshots, integrity, and
the determinism properties 0c just restored. Plus a **global sweep over all roads**, which is
a new whole-graph iteration and a new accumulation site (§6). Re-verification: 0a in full,
and 0b/1a–1d to confirm the default-off path is byte-identical.

### 3.2 Design B — minimal eligibility trace, no global pool

τ on `Road` as in A, but no `P_PRP` and no sweep. An explicit
`assign_credit(outcome_charge, ...)` call walks only the roads with a live τ and strengthens
them in proportion.

**Cost — high, for the same reason as A**: it still adds a field to `Road`, which is the
expensive part. It avoids the global sweep and the dependency on an unbuilt NEUROMODULATION
system. It **cannot** do behavioural tagging: with no global pool there is nothing for a weak
trace to capture.

### 3.3 Design C — an episodic trace outside the store · **RECOMMENDED**

No change to `Road`, and **no change to `src/nous_store.py` at all.**

A new module holds a bounded, append-only trace of `(cycle_index, road_id)` — a deque with a
fixed window `L`. An explicit `assign_credit(trace, outcome, ...)` computes an eligibility
weight `e(k) = f(cycle_outcome − cycle_traversal)` per entry, and applies credit **through
the existing public `strengthen(road_id, charge, base_gain)`**.

The eligibility trace is then not a stored field but a **function of the trace's own
timestamps** — which is the same move `nous_store` already makes with lazy decay: don't store
what you can compute from a timestamp on access.

**Cost — near zero against Tier 1.** The store is untouched, so 0a needs no re-verification.
`strengthen` is already `PROVEN`, already the only write path, already exercised by the
mutation batteries. Re-validation reduces to: the new module's own verification, plus a
default-off byte-identity check that nothing downstream moved.

**What it gives up.** No behavioural tagging (same as B). The window `L` is a hard cutoff
rather than an exponential tail, unless `e(k)` is made exponential — which it can be, at no
extra cost, and should be. And the trace lives outside the substrate, so it is *not* a
biological analogue of a synaptic tag; it is a replay buffer with a decay kernel. **That
distinction must be stated in the module docstring**, because "eligibility trace" invites the
reader to think a synapse is holding it, and here nothing is.

### 3.4 DECIDED (D-020) — Design C, and the reason is not that it is cheaper

**Recommendation: C, as brick `2f-i`, with A held as `2f-ii` and built only if behavioural
tagging earns its own justification.**

Three reasons. **First, cost placement:** C is the only option that gets the mechanism
without opening Tier 1, and Phase 0 was restored four commits ago through four bricks of
repair. *Do not spend a `PROVEN` label on a feature that does not require it.* **Second,
falsifiability first:** the §7 done-means is fully testable under C. If the mechanism cannot
be demonstrated with a trace and a decay kernel, adding a field to `Road` will not save it —
so C is the cheapest route to the *evidence*, and evidence should be cheap to get and
expensive to fake, not the reverse. **Third, the corpus's own sequencing argument:** the
biology document's distinctive contribution is behavioural tagging, and that deserves its own
brick with its own falsifier rather than arriving as a side effect of scaffolding.

**The counter-argument was answered, not overruled.** The honest objection was: if
behavioural tagging is the point — if the goal is the *biological* claim — then C is
scaffolding that will be replaced. D-020 answers it directly:

> **The biological claim cannot be the point.** CONTRIBUTING.md rule 1 permits describing
> biological *inspiration* and forbids asserting biological *fidelity*. **Paying a Tier-1
> re-validation now to buy fidelity buys a claim this project is constitutionally barred
> from making.** 2f's deliverable is a mechanism, and C delivers the mechanism.

**And C is idiomatic, not expedient — this is the second ground and the more durable one.**
Computing eligibility from a timestamp instead of storing it is **the substrate's own
existing move**: `nous_store` already does exactly this with lazy decay, which is why
`get_road` returns a computed view rather than a persisted value. C follows the design
philosophy already in the code. It is not a shortcut away from it.

**`2f-ii` stays registered, and its trigger is named so it cannot drift:** full tag and
capture is built when a **behavioural need** arrives — behavioural tagging, a weak trace
preserved by an unrelated strong event — and **never because a stored timestamp would be
tidier**. Deferred, not foreclosed, and the difference is written down.

---

## 4. Where `P_PRP` lives

### 4.1 What Layer 0 specifies

`nous_plan_layer0_topology.md` lines 271–277:

> *"**NEUROMODULATION (T2 integrator)** — global, cross-cutting state owned by no actor:
> system-wide **arousal** and the **plasticity budget** (`P_PRP`) … **Loop order pinned:**
> arousal flows in from SIGNALS/EMOTION and the integrated budget flows out to MEMORY/EMOTION;
> to avoid same-cycle circularity, **actors read the budget published on the *previous*
> cycle.** A one-cycle lag, biologically honest since neuromodulation is slow."*

### 4.2 Is it right? Yes, and for a better reason than the one given

The document justifies the lag as *"biologically honest since neuromodulation is slow."* That
is a resemblance argument, and this project does not accept those as load-bearing.

**The real justification is structural, and it is stronger.** Without the lag, `P_PRP` at
cycle `t` is a function of arousal at `t`, which is a function of what the cycle did, which
capture then changes — a same-cycle feedback loop whose fixed point is undefined and whose
*evaluation order* would decide the answer. This project has spent four bricks establishing
that **an answer decided by evaluation order is not an answer.** The one-cycle lag makes the
budget an **input** to the cycle rather than a simultaneous equation with it, which is what
makes the whole thing deterministic and replayable at all.

So: **the placement is right, the lag is right, and the reason should be restated in
structural terms** when NEUROMODULATION is specified.

### 4.3 DECIDED (D-020) — caller-supplied scalar; 2f does not block on NEUROMODULATION

NEUROMODULATION **does not exist as code**. If 2f depends on it, 2f cannot start.

- **(A) `P_PRP` is a caller-supplied scalar**, defaulting to a neutral value; NEUROMODULATION
  becomes its publisher later, with no change to 2f's interface.
- **(B) 2f builds a minimal NEUROMODULATION publisher** as part of this brick.
- **(C) 2f defers until NEUROMODULATION is specified.**

**DECIDED: (A).** Three grounds, per D-020: it does not block 2f on an unbuilt system; a
caller-supplied scalar **can be held fixed**, which is required to separate 2f's effect from
arousal's and which no published-state design permits; and it defers the publisher without
foreclosing it. NEUROMODULATION gets a real interface to satisfy, which is what "its first
real job" should mean.

**And the justification correction is recorded now, before NEUROMODULATION exists** — see
§4.2. `docs/design/nous_plan_layer0_topology.md` has been amended in place. The reason for
recording it early is itself the point: **a design implemented for a resemblance reason is a
design someone later removes when the resemblance stops feeling compelling.** The structural
reason survives that; "neuromodulation is slow in brains" does not.

---

## 5. Two global modulators that have never met

**2c** (`body_sensor`) modulates `decay_per_hop` — a **retrieval** parameter: it changes how
far activation spreads, i.e. *what gets read*. **2f** modulates plasticity — a **storage**
parameter: *what gets written*. Different axes, and that is the first thing to establish
rather than assume.

**The risk is not that they interact. It is that they share an upstream driver.** Both are
downstream of arousal/friction in the corpus's design. If both end up reading the same
scalar, then "high arousal narrows retrieval **and** raises plasticity" becomes a single
coupled knob wearing two names — and any experiment that varies one silently varies the
other. **That is a confound, and it is exactly the shape of the circularity that produced the
1e NO-GO.**

**How it will be tested — a 2×2 factorial, and it is an invariant, not a suggestion (I-9):**

| | 2f off | 2f on |
|---|---|---|
| **2c off** | baseline — byte-identical to today | credit only |
| **2c on** | retrieval modulation only | both |

Four assertions. **(i)** Each cell with a modulator off is byte-identical to the
corresponding cell without that modulator's code path. **(ii)** The both-on cell is
**reproducible from its inputs**, not merely deterministic — i.e. the effect is not
attributable to one modulator alone, and both single-on cells differ from it. **(iii)**
Determinism holds in all four cells across seeds and interpreters. **(iv)** **An
asserted-negative:** if 2f's budget and 2c's friction are ever derived from the same source
value, that coupling is asserted **explicitly**, with the shared term named. A coupling that
exists and is untested is the failure mode; a coupling that exists and is asserted is a
design.

---

## 6. This brick adds float accumulations, and 0d covers them from the first commit

Credit assignment is accumulation by definition: eligibility summed over a window, credit
summed over roads, and — under A — a global pool summed across a sweep.

**Every accumulation 2f introduces is either `math.fsum` or registered in
`tools/ledger.json` with a bound**, per SPEC-0d §2.3, **from the first commit and not
retrofitted.** 0d's C6 check must be in place before 2f's first line of production code, and
the model form is SPEC-0d §3.1: a bound that explains *why the site cannot break* beats a
conversion that merely prevents it from breaking.

This is the first brick built **after** the detector exists, and it is the test of whether
0d was worth building. If a naive accumulation reaches `main` during 2f, 0d failed at the
only job it has.

**Ordering consequence:** 0d is a prerequisite of 2f, not a parallel track.

---

## 7. Done means — a MECHANISM bar, sharpened

The brief's formulation, tightened where it was loose. Every clause below is a place a
plausible-looking implementation could pass without doing the work.

> **The claim.** A road traversed at cycle `t` and followed by a designated outcome at
> `t+k` is reinforced **more** than a **matched** road traversed at `t` and *not* followed by
> that outcome, for `k` up to the eligibility window `L`; the difference is **monotone
> non-increasing in `k`** and is **statistically indistinguishable from the shuffled control
> for `k > L`**. Byte-identical under replay.

**"Matched" is defined by construction, never by selection.** The control road must be
generated with identical initial `strength`, identical `charge`, identical in- and
out-degree, and traversed at the same cycle `t` in the same batch. Hand-picking a comparison
road is how a test encodes its own answer.

**"Reinforced more" must clear the control, not zero.** The bar is not `Δω > 0` — that is
satisfied by any implementation that strengthens anything. It is
`Δω(paired) − Δω(unpaired) > Δω(shuffled) − Δω(unpaired)`, so the effect must exceed what
random pairing produces on the same trace.

**The shuffled-outcome control, specified so it cannot be weakened.** Hold the trace fixed
and the outcome sequence fixed; **permute only which outcome pairs with which trace window**,
preserving both marginal distributions exactly. If the effect survives this shuffle, the
mechanism is measuring something other than temporal pairing — and that is a **falsifier, not
a curiosity**.

**Three asserted-negatives that must accompany the claim:**
1. **Empty trace** ⇒ no reinforcement anywhere. An outcome with no preceding traversal
   changes nothing.
2. **Never-traversed roads are never credited**, regardless of outcome magnitude — including
   roads adjacent to credited ones.
3. **The outcome must not be derived from the road's own strength.** If it is, this is a
   readback of ω and not credit assignment at all. This is the 1e circularity in a new
   costume, and it is the single most likely way this brick produces a meaningless pass.

**Determinism:** same trace, same outcome sequence, same parameters ⇒ **byte-identical ω** on
every interpreter, across hash seeds and fresh processes.

**What this done-means does NOT establish**, stated so the delivery cannot drift: that the
system *learns*, that credit is *correct*, that the assignment is *useful*, or that any of
it corresponds to what a brain does. It establishes that an outcome at `t+k` moves a weight
at `t` in a bounded, decaying, reproducible way. **That is the whole claim.**

---

### 7.1 SECONDARY acceptance criterion — 2f is the test of whether 0d works

2f is **the first brick built after the detector exists**, which makes it the only real
evidence about whether 0d does its one job. So the delivery must answer, explicitly and in
writing:

> **Did the gate catch what a manual hunt would have missed — or did it stay green while a
> new naive accumulation shipped?**

Both answers are informative and both must be reported. A green gate that missed something a
human then found by looking is 0d's failure, and it must be recorded as such rather than
absorbed as a 2f detail. This criterion is secondary to §7's mechanism bar: 2f can pass its
own done-means and still return a negative verdict on 0d, and if so, that verdict is the more
important half of the delivery.

### 7.2 PRECONDITIONS the 2f builder re-checks BY HAND before delivering

Two registry entries rest on an **absence**, and **2f is the most likely brick in the
project to end either one**:

- `ActivationField.flow` has no reader in `src/` — 2f reads the field, and reading `.flow` is
  a natural thing for a credit-assignment consumer to do.
- `advance()` has no caller in `src/` — 2f deals in cycles and elapsed time.

C6's `bound_on_absence` enforces both mechanically and will fail the build if either symbol
appears. **The builder re-checks both by hand anyway, and says so in the delivery report.**
That is belt and braces on purpose: the machine check is **one cycle old**, it has never been
fired in anger by real work, and the 0d tester found that it **under-reports on dynamic
access** — `getattr(x, 'flow')`, `x.__dict__['flow']` and aliased calls all evade it
(FINDING 0d-5). If 2f reaches the field by any of those routes, the machine check will stay
silent and the hand check is the only thing standing.

If either absence ends, that is **not a failure** — it is the registry working. The entry is
re-adjudicated with a new argument, and the fact that 2f was the trigger is recorded.

## 8. Invariants for the tester

- **I-1 Neutral byte-identity.** With credit assignment at its neutral value, output is
  byte-identical to the pre-2f engine under adversarial graphs. **The gate**: if this fails,
  the overlay argument collapses and nothing else matters.
- **I-2 The graded effect** — §7's claim, with the matched control generated by construction.
- **I-3 The decay shape** — the effect is monotone non-increasing in `k` and indistinguishable
  from control beyond `L`. Assert the boundary **exhaustively, not by sampling**: SPEC-0b2 §9.2
  records three different answers to one boundary, each of them the last value someone
  happened to test.
- **I-4 The shuffled-outcome control** kills the effect.
- **I-5 The three asserted-negatives** of §7 — empty trace, never-traversed roads, and the
  anti-readback check.
- **I-6 Determinism** — byte-identical across 6 hash seeds × every CPython on the machine,
  in fresh processes. Bit patterns, never `round(x, 9)`.
- **I-7 Purity until the explicit write.** Building and reading the trace mutates nothing;
  only `assign_credit` writes, and it writes only through `strengthen`.
- **I-8 Bounded trace.** The window cannot grow without limit; memory is bounded by `L`
  regardless of run length, asserted with a long run.
- **I-9 The 2×2 modulator factorial** of §5, including the coupling asserted-negative.
- **I-10 Every new accumulation** is `fsum` or registered with a bound; 0d's C6 passes
  (§6).
- **I-11 Loop-closure** — the trace is driven by roads that `think()` actually traversed, not
  by a hand-written road list. This is where a friendly-input pass would die.
- **I-12 ASSERTED-NEGATIVE, scope.** 2f assigns credit over a **bounded window on a single
  trace**. It does not do multi-step return estimation, discounting over episodes, or credit
  propagation through a value function. State the boundary so "credit assignment" is never
  read as reinforcement learning.

---

## 9. Re-validation cost

**Under the recommended Design C:**

| Brick | Cost | Why |
|---|---|---|
| **0a** store | **none** | untouched; `strengthen` is the only write path and is unchanged |
| **0b / 0b2 / 0c** | **none at neutral**; I-1 verifies it | no read path changes |
| **1a–1d, 2c** | **none at neutral**; re-verify only if the default is ever flipped | overlay discipline |
| **0d** | **prerequisite**, not a cost | §6 |
| **new module** | full mechanism verification | I-1 … I-12 |

**Under Design A or B**, add: full 0a re-verification (purity, integrity, determinism, the
decay path, view construction), plus 0b/1a–1d default-off byte-identity, plus a new global
sweep to register with 0d. **That is a Tier 1 re-opening, four commits after Phase 0 was
restored by four bricks of repair.** It may still be the right call — but it should be paid
for behavioural tagging, deliberately, and not incurred as a side effect of wanting a
timestamp.

---

## 10. Roadmap, and the single next action

2f is the **first brick that is not substrate repair** since 0b2, and it is the one the
corpus has been deferring since Layer 0. It unblocks, in principle, the three vision
documents that assume it — motivation, self-model, emotional regulation — none of which
should be started before it exists.

**It does not touch the meaning bar.** Credit assignment is a mechanism, it will be verified
as a mechanism, and the three NO-GOs stand exactly where they are.

**Three decisions are open and all are Cagan's:**
1. **§3.4 — which design.** Recommendation: **C** (`2f-i`), with A as a later `2f-ii` if
   behavioural tagging earns its own brick. This is the expensive one to get wrong.
2. **§2.3 — the vestigial `traversal_count`.** Recommendation: **(A) leave and document**.
3. **§4.3 — `P_PRP`'s home.** Recommendation: **(A) caller-supplied scalar**, with
   NEUROMODULATION as its later publisher.

**Single next action: Cagan decides §3.4.** The other two are cheap and can follow. And
**0d must land first regardless of which design is chosen** — §6 makes it a prerequisite, and
2f is the first real test of whether the detector does its job.
