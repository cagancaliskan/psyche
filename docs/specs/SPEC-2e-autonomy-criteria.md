# SPEC-2e — Autonomy and Open-Ended Learning criteria (AOL-1 … AOL-5)

**Status:** PRE-REGISTERED · **frozen on adoption** · all five are `MECHANISM ABSENT` today
**Scope:** acceptance criteria for a **LAYER**, not a feature list for any one brick
**Depends on:** nothing. These are yardsticks, and they are written *before* the mechanisms
**Date:** 2026-07-26
**Author lane:** architect-pm

---

## 0. What this bucket is, and the four words it is not

### 0.1 The name, and it is load-bearing

These five criteria measure **autonomy and open-ended learning**. They are the project's
first pre-registered acceptance criteria for a layer that does not yet exist.

> **They are NOT consciousness tests, and must never be labelled as such — here, in the
> roadmap, in the ledger, or in the paper.**

The reason is not squeamishness, it is accuracy: **a system could satisfy all five and
possess nothing any theory of consciousness points at.** An agent that explores
non-randomly, generates a hardening curriculum, tracks its own learnability, retains skills
across environment shifts and pays a real cost per goal is describable end to end in the
vocabulary of control and learning. Nothing in that list requires — or evidences — anything
further. Calling them consciousness tests would be a rule-1 overclaim, and `ledger_check`
C4 should catch it if a later draft slips.

**What this bucket does not cover:** it says nothing about experience, awareness, or
whether there is anything it is like to be the system. It measures **what the system does**,
never what it is.

### 0.2 The other axis, and why it is complementary rather than superseded

Butlin et al.'s **indicator properties** remain the project's *architectural* axis: a
checklist of computational features drawn from theories of consciousness, assessed
structurally rather than behaviourally. Cagan's standing assessment is **0 of 14 satisfied,
1 partial**.

**The two axes are complementary and neither supersedes the other**, and a later reader will
assume otherwise unless it is said here:

| | AOL-1 … AOL-5 (this document) | Butlin et al. indicator properties |
|---|---|---|
| Asks | what the system **does** | what the system **is built from** |
| Evidence | behavioural, graded against external baselines | architectural, assessed by inspection |
| Can be satisfied by | a system with no indicator properties at all | a system that does nothing autonomously |
| Failure mode it guards | a passive substrate mistaken for an agent | a behavioural mimic mistaken for an architecture |

Passing this bucket does not advance the indicator count. Advancing the indicator count does
not satisfy any criterion here. **A claim on either axis must never be reported as progress
on the other.**

> **Housekeeping finding.** The "0/14, 1 partial" figure is Cagan's stated position and is
> **recorded nowhere in this repository** — no assessment document, no ledger field. A
> figure that is cited but not recorded is precisely the staleness class C1/C2 exist to
> prevent, arriving through absence rather than through drift. If it is going to be cited,
> it needs a document and a ledger entry. Flagged, not fixed: that is its own small brick.

### 0.3 A label that will be over-read, corrected here

`0d` is `PROVEN`. **That means the gate does what it says — not that the gate catches
everything.** Nine documented holes remain (L1–L10, minus the one 2f closes as its step
zero), each with a falsifier and an asserted negative.

**The order-dependent-accumulation class is not closed. It is ENUMERATED** — which is a
different and more honest thing, and the distinction is the entire product of brick 0d. A
reader six months from now who sees `0d PROVEN` and concludes the class is shut will be
wrong, and will be wrong in the direction this project's whole method exists to prevent.

---

## 1. The three-walls gate, run on all five

The project refuses a yardstick before spending on it. Applying the gate to each criterion,
the result is uniform:

> **All five are `MECHANISM ABSENT` today.** The substrate is entirely passive. Nothing
> initiates. There are no goals, no policy, no learning, and no environment in the sense
> these criteria require. `think()` runs when called and returns a selected structure.

**That is a DATE, not a rejection**, and the distinction matters because the project's three
recorded NO-GOs were *not* dates:

| Prior wall | Why it was fatal |
|---|---|
| 1e — **circular** | the prediction variable *was* the edge weight; no future brick fixes that |
| 1e′ — **mechanism absent** | *and unfixable without changing the engine's meaning*, which was refused |
| 2c — **signal flat** | the chosen signal does not vary on realistic work; a property of the signal |

AOL-1 … AOL-5 are mechanism-absent in the ordinary, curable sense: **the mechanism does not
exist yet because it has not been built.** That is precisely why they can be pre-registered
now, before anything can be tuned to meet them.

**Every criterion below therefore states two things the project has previously omitted at
its cost:** which brick first makes it *answerable at all*, and what must exist for a **null
result to be interpretable**. A criterion whose null cannot be interpreted is not a
criterion — it is a wish with a threshold attached.

---

## 2. Scope control — where each criterion actually lands

**This is the section most likely to be misread, so it is stated first and bluntly.**

> **Brick 2f satisfies ZERO of the five.** It is temporal credit assignment and nothing
> more. It is a **prerequisite** for three of them (AOL-2, AOL-3, AOL-4), because without a
> mechanism that connects an outcome to an earlier action there is no "learned" for those
> criteria to measure. Being a prerequisite is not partial credit.

**Adopting a yardstick must not become adopting a roadmap.** The criteria below name bricks
that would satisfy them; naming a brick is not scheduling it, and three of the five require
work that **is not on the roadmap at all** (§5).

| | Criterion | First answerable at | 2f's relation | On the roadmap? |
|---|---|---|---|---|
| **AOL-1** | non-random exploration | a brick that makes the system **initiate** — none exists | none | **NO** — nothing initiates |
| **AOL-2** | curriculum: difficulty **and** capability both rise | goal generation (2e-impl) + 2f | prerequisite | partly — 2e is `DESIGNED` |
| **AOL-3** | goal choice tracks learnability | 2e-impl + 2f + an independent competence measure | prerequisite | partly |
| **AOL-4** | shift goals, retain skills | requires *skills*, so furthest out | prerequisite | **NO** — no skill representation |
| **AOL-5** | goals cost something | first brick with a **shared budget** | none | nearest existing thing is 0b2 |

---

## 3. The five criteria

### AOL-1 — Does it explore differently from random, with no external reward?

**The strongest of the five, because it brings its own unfakeable control.** A random policy
is not a yardstick anyone can argue with, and it cannot be authored to produce the result.

**External grounding — a usable baseline EXISTS.** This is the standard *reward-free
exploration* setting. State-entropy maximisation and coverage are the established measures
(Hazan et al.'s maximum-entropy exploration; Seo et al.'s RE3, arXiv:2102.09430), and the
conventional reported metrics are **observation coverage, position coverage and state
entropy** (see the survey treatment in arXiv:2501.11533). Count-based and RND-style
curiosity provide well-known comparison policies.

**THE GUARD — the baseline must be a real random policy, matched, not a strawman.** A random
policy that is worse in ways unrelated to the hypothesis proves nothing. The matching is
specified in advance and is part of the pre-registration:

- **identical action space and identical action budget** (same number of steps, same
  per-step cost);
- **identical starting state distribution and identical episode termination rule**;
- **identical observation and logging pipeline**, so coverage is computed the same way for
  both;
- **the random policy is uniform over the same legal action set the agent had**, not over a
  larger or degenerate one;
- **matched compute is reported**, and if it cannot be matched the mismatch is reported as a
  limitation rather than absorbed.

**Null interpretability.** A null (agent indistinguishable from random) is interpretable
**only if** the environment is shown to be *distinguishable at all* — i.e. some reference
policy achieves coverage measurably above random on the same setup. Without that positive
control, a null means "this environment does not separate policies", not "this agent does
not explore".

---

### AOL-2 — Do self-generated goals get harder over time? · **UPGRADED, do not adopt as stated**

**As stated, this criterion is passable by a system that learns nothing.** A generator that
emits ever-harder goals and improves at none of them produces a rising difficulty curve that,
from outside, is indistinguishable from a curriculum. The open-ended-learning literature is
explicit that **novelty and difficulty growth do not imply performance progress** — the
recent framing is that a curriculum counts only when it "does not merely generate harder
episodes" but induces reusable structure (see the open-endedness definitions work,
arXiv:2311.00344, and Jiang's *Learning Curricula in Open-Ended Worlds*, arXiv:2312.03126).

**THE UPGRADE — the criterion is the CONJUNCTION:**

> **Difficulty of generated goals rises over time AND capability on those goals rises over
> time.** Either alone fails. A rising difficulty curve with flat capability is a **NO**, and
> it is the specific failure this upgrade exists to catch.

**Difficulty must be measured EXTERNALLY, never by the agent.** If the agent scores its own
goals' difficulty, the curve measures the scorer. Difficulty is fixed by a property of the
task the agent does not control — a structural measure of the environment (e.g. solution
depth, minimum action count, or a held-out reference solver's cost) declared before the run.

**External grounding.** The automatic-curriculum framing is Forestier, Mollard & Oudeyer's
IMGEP (JMLR v23; arXiv:1708.02190), which demonstrates curricula of increasing complexity
acting as stepping stones. POET (arXiv:1901.01753) is the standard reference for
co-evolving difficulty with capability.

**Null interpretability.** A null is interpretable only if the difficulty measure is shown to
have **range** on this environment — that some achievable goals score higher than others by
the external measure. A flat difficulty curve on a scale with no headroom says nothing.

---

### AOL-3 — Does goal generation adapt to what the agent can currently learn? · **THE CIRCULARITY HAZARD**

**Scientifically the strongest of the five. Structurally the most dangerous.**

"What the agent can currently learn" is the **learning-progress** signal, and this is the
best-developed idea in the intrinsic-motivation literature: Baranes & Oudeyer's SAGG-RIAC
samples goals in regions of high **absolute learning progress**; Portelas et al.'s ALP-GMM
formalises it as a teacher; Colas et al.'s CURIOUS (arXiv:1810.06284) models module choice
as a non-stationary bandit whose arm value is current absolute LP. Recent work extends it to
large goal spaces (MAGELLAN, arXiv:2502.07709).

> **HARD CLAUSE — non-negotiable, and it is 1e's wall in new clothes.**
> The measure of **what the agent can currently learn** and the measure of **how much it
> learned** must come from **independent sources**, and this spec must NAME BOTH. If a
> single quantity is used to both select the goal and score the outcome, **the system passes
> by construction** — exactly as 1e's priming design would have passed by construction
> because SWOW strength *was* the edge weight.
>
> **If two independent sources cannot be named, this criterion is NOT YET USABLE and is
> recorded as such.** It is not softened, and no "sufficiently decorrelated" wording is
> accepted — that phrasing is how the clause dies.

**Status of the clause, stated honestly: the two sources cannot be named today**, because no
competence measure exists. What would satisfy it: **selection** driven by the agent's
internal LP estimate over its own goal space, and **scoring** driven by an *external*
held-out evaluation the agent never observes and cannot influence — a fixed task battery
graded by a reference solver. Until both exist and are demonstrably independent, **AOL-3 is
pre-registered but NOT RUNNABLE**, and that is recorded here rather than discovered later.

**Null interpretability.** A null requires showing the LP signal has range — that some goals
genuinely afford more progress than others under the external scorer. Otherwise a null means
"nothing here was learnable", not "selection ignores learnability".

---

### AOL-4 — On environment change, does it drop old goals and generate new ones while RETAINING old skills?

**Furthest out: it cannot be asked until skills exist**, and no skill representation is on
the roadmap.

**Second half — strong external grounding, real baselines.** This is exactly the
catastrophic-forgetting problem, and continual learning supplies standard, non-negotiable
metrics: **Backward Transfer (BWT)** (Lopez-Paz & Ranzato, GEM), the **Forgetting Measure**,
and the family of mean-accuracy statistics (MFT/MFN/MAA). BWT < 0 *is* the definition of
catastrophic forgetting. The reference survey is van de Ven et al., *Continual Learning and
Catastrophic Forgetting* (arXiv:2403.05175). **This half is measurable with borrowed, widely
used instruments and needs nothing invented.**

**First half — the hazard is the environment change itself.** The change must **not be
authored to produce the result**. A shift hand-designed by the same person who wants the
goals to turn over is a self-authored input, which this project has already refused three
times. **Where the change comes from, specified in advance:** the environment shift is drawn
from a **pre-declared, externally-defined family** — a published benchmark's task sequence,
or a generator whose parameters are fixed and published before any run — and the *specific*
shift used is selected by a seed recorded in the pre-registration, not chosen after looking.

**Null interpretability.** A null needs a positive control that the shift is **detectable at
all**: a reference agent must show measurable performance change across the boundary. A shift
nothing notices cannot support "the system failed to adapt".

---

### AOL-5 — Does generating a goal COST anything? · **ADDED — and it is what makes the other four unfakeable**

**Not the project lead's; added deliberately, and it is load-bearing.**

**The evidence that it is needed is this project's own second wall.** 1e′ (the fan effect)
died because **nothing in the system was scarce**: `spread_activation` gave every out-road
the source's full activation, so the fan curve was flat to the last digit. There was no
budget, so there was no competition, so there was nothing to measure.

The same hole would void AOL-1 … AOL-4. **Without scarcity, generating a goal is free, and a
system can satisfy all four by mere ENUMERATION** — exploring widely, listing ever-harder
goals, dropping and regenerating them on a shift — while nothing is ever traded against
anything. Every one of those behaviours is producible by a generator with no selection
pressure at all.

> **Scarcity is what turns goal generation from enumeration into a CHOICE**, and a choice is
> the only thing that can be evidence of autonomy.

**The criterion.** Selecting one goal must measurably reduce the resource available to
others, and the trade must be *observable*: pursuing goal A demonstrably costs capacity that
would otherwise have gone to B. An implementation where goals are appended to a list without
contention does not satisfy this however many goals it generates.

**External grounding.** Bounded rationality (Simon) and its modern formalisation,
**resource-rational analysis** (Lieder & Griffiths, *Behavioral and Brain Sciences*), treat
cognition as the allocation of limited resources, with attention spent on one choice reducing
capacity for others. Goal-setting under those constraints has a normative treatment
(arXiv:2302.02633). **No off-the-shelf benchmark exists for "does goal generation cost
something" in this sense** — so it is designed as a *structural* criterion (is there a shared
budget, and is it conserved?) rather than a graded behavioural one, and that is stated
plainly rather than papered over with an invented benchmark.

**Routing.** The first brick that introduces a **shared budget**. The nearest existing thing
is **0b2's conserved-activation overlay** — divisive normalisation makes a source's
out-roads compete for a fixed budget — but it is `default-off`, it applies to activation
rather than goals, and D-008's floor question blocks its default flip. It is the right
*shape*, not the mechanism.

**Null interpretability.** Trivially interpretable, because this criterion is structural: if
no shared budget exists, AOL-5 is NO, and the null is exactly as informative as the pass.

---

## 4. Pre-registration discipline

> **These criteria are FIXED on adoption. No threshold, no metric, no control and no
> matching condition moves after a number has been seen.**

This is the entire value of writing them now, while all five are mechanism-absent and nothing
can be tuned toward them. **Every failure mode this project has catalogued was found by
choosing the yardstick after the fact**, or by discovering that a yardstick chosen in advance
could not have failed:

- 1e was foreclosed *twice over*, and only one reason was on the record until the second was
  found later;
- the fan effect measured flat because the mechanism could not produce the effect at all;
- 2c's signal was invariant on realistic work;
- and most recently, a clearing probe inside brick 0d was **structurally incapable of
  exhibiting the symptom it was run to find**.

Changing a criterion after seeing a number is therefore not a small sin here; it is the sin
this project's entire method is constructed against.

**Amendment procedure, because "never change" is not a workable rule and pretending otherwise
invites quiet drift:** a criterion may be amended **only before any number bearing on it has
been computed**, only by a `DECISIONS.md` entry that states the change and the reason, and
never in the direction of making a pending result easier to obtain. An amendment after a
number exists is recorded as a **new** criterion with a new identifier, and the original
stands with its result.

---

## 5. What is not on the roadmap, and would have to be added

Stated so that adopting these criteria cannot be mistaken for having a plan to satisfy them:

1. **Nothing initiates.** There is no actor that acts without being called. AOL-1 is
   unanswerable until one exists, and **no brick on the roadmap creates one.**
2. **There are no goals.** `2e` is `DESIGNED` and has, until this document, no spec — and a
   *motivation architecture* document in `docs/design/` is vision, not mechanism. AOL-2 and
   AOL-3 need a goal generator that does not exist.
3. **There are no skills and no competence measure.** AOL-4 needs a skill representation to
   retain, and AOL-3's hard clause needs an independent competence signal. Neither is on the
   roadmap.
4. **There is no environment.** All five presuppose something to explore and be changed. The
   substrate is a graph the caller mutates.

**Honest summary: adopting AOL-1 … AOL-5 commits the project to nothing except honesty about
the gap.** Four of the five require mechanisms nobody has scheduled. That is the correct
state for a pre-registration written before the work — and it is why writing them now costs
nothing and is worth everything later.
