# SPEC-2g — The depression path: the missing half of credit assignment

**Status:** DESIGNED · **one decision open and it is Cagan's** (§4)
**Revises:** nothing. Extends 2f-i, which refuses the input this brick would accept.
**Depends on:** 2f-i `BUILT-UNVALIDATED` (the trace), 0a `PROVEN` (the write path),
0g (§0, mandatory step zero)
**Date:** 2026-07-27
**Author lane:** architect-pm

---

## 0. STEP ZERO — brick 0g, mandatory, before any 2g code

**Fix `bound_on_absence`'s line-anchored dismissals first.**

Dismissals are keyed `path:line`. Inserting **one comment line** at the top of
`nous_field.py` shifts every line below it and fires a **false `[C6]`** against the
`ActivationField.flow` bound. 2g edits `src/` — a new module, a new parameter on an existing
signature, quite possibly a new field — and will trip this constantly.

**Why it is step zero rather than a nuisance to work around.** It has already caused one
real mis-measurement: the tester's first blind-spot probe prepended to an existing module and
reported **all five** blind spots as CAUGHT. That was the *shifted* bound firing, not the
binding bound working. The correct measurement, planting in a new module, showed all five
slip through as documented.

> **A false positive that masquerades as the check working is worse than a silent gap.** A
> silent gap is a known unknown. A lying gate teaches people to re-key mechanically instead
> of re-reading — which is *verbatim* the failure the `Accumulation` dataclass docstring says
> it avoids by not keying on line number, reintroduced one field away. A gate that cries wolf
> gets ignored, and being ignored would waste the entire foundation arc that produced it.

**Fix shape (not decided):** a content-anchored key — the text of the source line, or an AST
path. **Acceptance:** inserting a comment anywhere in `src/` changes no finding, and every
existing dismissal still resolves.

This is the same placement L3 had as 2f's step zero, for the same reason: **ownership sits
with the brick that needs the coverage.**

---

## 1. What this brick is, in one paragraph

2f-i can strengthen a road that preceded an outcome. It cannot weaken one. A negative
`outcome_magnitude` is refused at the boundary with a message that says so. **2g is the
mechanism that would let an outcome make an earlier traversal less likely** — and until it
exists, nothing built on the trace may be called learning by this project, in any document.

That sentence is the whole of "attention, not credit," and it is why this brick is the
roadmap's headline item rather than a refinement.

---

## 2. What 2g would and would NOT make true — answered here, not left to inference

### 2.1 It does NOT reach Butlin AE-1, and the reason is structural

AE-1: *"learning from feedback and selecting outputs so as to pursue goals, especially where
this involves flexible responsiveness to competing goals."*

**A signed rule satisfies the first conjunct's precondition and nothing else.** With 2g,
feedback acquires a sign, so "learning from feedback" becomes arguable in the narrow
arithmetic sense. **The second conjunct still fails outright**: the system selects no outputs
and pursues no goals, because it *has* no goals. There is no action, no goal representation,
and no policy over either.

**Stated plainly so nobody reads the missing half as completing the picture: 2g moves AE-1
from "fails at two conjuncts" to "fails at one." That is progress on an architectural axis
and it is not satisfaction of the indicator.** The project's standing assessment against that
whole list lives in one document and is cited from there alone.

### 2.2 Which AOL criteria 2g could move, and which cannot move regardless

| | Could 2g move it? | Why |
|---|---|---|
| **AOL-1** exploration | **No** | needs a goal generator; nothing initiates |
| **AOL-2** difficulty **and** capability growth | **No** | needs goals *and* a capability measure; 2g supplies neither |
| **AOL-3** adapting to learning progress | **No** | needs a learning-progress signal from an independent source; not runnable today by its own HARD CLAUSE |
| **AOL-4** drop goals, retain skills | **No** | needs a skill representation; none is on the roadmap |
| **AOL-5** does choosing COST anything | **Only under Option B** | scarcity is a property of the *mechanism*, not of the goal layer — see §3.2 |

**Four of five stay MECHANISM ABSENT no matter which option is chosen**, because they need
goal generation and skill representation, and 2g is neither. **AOL-5 is the exception**, and
that is the entire strategic content of the choice below.

---

## 3. Three options

All three ship as a **gated overlay**: a default-off parameter whose neutral value is
**byte-identical** to current behaviour, proven under attack **on a frozen clock**. That is
not a tradeoff and is not negotiable. A live clock manufactures a difference through lazy
decay — measured at 6 roads differing with no credit code involved — and this project has
filed a false defect that way.

### 3.1 Option A — symmetric depression

**Mechanism.** Accept a signed `outcome_magnitude`. A negative outcome applies the same
eligibility-weighted rule with the sign carried through: `gain = base_gain · P_PRP · e(k) ·
outcome`, and a negative gain lowers `strength` by the mirror of the saturating rule —
`Δω = gain · ω` on the way down, so the effect saturates at the floor as it saturates at the
ceiling going up.

**Constants introduced: zero new ones.** It reuses `base_gain` and `P_PRP`. That is Option
A's whole case.

**Prior art.** The symmetric case is the textbook delta rule (Widrow & Hoff 1960) and the
classical two-sided Rescorla–Wagner form (Rescorla & Wagner 1972), where the same rate governs
acquisition and extinction. Note honestly that **the empirical literature mostly rejects
symmetry**: extinction is not the reverse of acquisition — spontaneous recovery,
reinstatement and renewal all show the original association survives extinction (Bouton 2004,
*Learning & Memory* 11:485). Symmetry is the simple choice, not the faithful one, and this
spec does not claim fidelity for it.

**Re-validation cost — lowest.** No change to `Road`, no change to the store, no coupling
between roads. `strengthen()` gains a signed sibling or a signed parameter; that is a change
to a `PROVEN` module's write path, so 0a's purity, integrity and determinism legs re-run, but
nothing structural moves. 0b/0b2/0c/1a–1d are unaffected at neutral.

**Invariants for the tester.** Neutral byte-identity · a negative outcome lowers the paired
road and not a matched control · the effect is monotone non-increasing in `k` and exactly
zero past `L` · bounded below (no road passes the floor, no ω leaves [0,1]) ·
`+x` then `−x` is **not** required to return to the starting ω, and whichever way that lands
is asserted rather than assumed · determinism across seeds and interpreters · purity until
the explicit write.

**Falsifier.** Any sequence of signed outcomes that drives ω outside [0,1], or that makes the
final ω depend on the *order* of a set of outcomes delivered in one window.

### 3.2 Option B — competitive / shared budget · **RECOMMENDED, with its cost stated**

**Mechanism.** Strengthening is drawn from a **shared budget across a road's siblings**:
crediting one out-road of a node implicitly weakens the others, normalising the set. No road
is weakened by an explicit negative signal; depression is what happens to whatever was *not*
credited.

**Three things fall out of one mechanism**, which is the case for it:

1. **The depression path**, without a second signed rule.
2. **AOL-5's scarcity requirement** — *does choosing cost anything?* Under B it does, by
   construction. AOL-5 exists because **1e′ died of exactly this absence**: `spread_activation`
   gave every out-road the source's full activation, so the fan curve was flat to the last
   digit — no budget, no competition, nothing to measure. AOL-5 is what makes AOL-1…4
   unfakeable, because without scarcity all four are satisfiable by **enumeration**.
3. **It reuses 0b2's conserved-activation overlay**, which is already built and
   mechanism-verified across five interpreters — the same divisive-normalisation shape,
   applied to plasticity instead of transmission. *Reinvent the idea, borrow the scaffolding.*

**Constants introduced: one.** A competition sharpness (how hard the normalisation
concentrates on the credited road). 0b2's `normalization_sigma` is the existing analogue and
its neutral value is `None`.

**Prior art — the strongest of the three.** Synaptic normalisation and competitive
plasticity: Miller & MacKay (1994, *Neural Computation* 6:100) on subtractive versus divisive
normalisation and their different competitive consequences; Oja (1982, *J. Math. Biol.*
15:267) for the multiplicative-normalisation form; Turrigiano & Nelson (2004, *Nat. Rev.
Neurosci.* 5:97) for homeostatic scaling as the biological instance. Divisive normalisation is
additionally described as a canonical cortical computation (Carandini & Heeger 2012, *Nat.
Rev. Neurosci.* 13:51) — which is the same citation 0b2 already rests on.

**Re-validation cost — HIGHEST, and this is the honest counterweight.** **It couples roads
that were independent.** Every property this project has proven about a single road's update
becomes a property about a *set*:

- **The float rule bites immediately.** A normalising denominator is a fold over a
  collection — precisely the shape 0d's L1 cannot see and the shape the registry exists for.
  It must be `math.fsum` and registered from the first commit.
- **Determinism becomes order-sensitive where it was not.** Sibling iteration order now
  affects a shared denominator. 0c's structural fix (insertion-ordered `_out`) makes this
  tractable, but it must be re-proved, not assumed.
- **0a's integrity legs re-run**, because a single `strengthen` now touches several roads.
- **1b/1d re-verification at the flipped default**, since coalition strength and workspace
  competition read the strengths this would move.

**Invariants for the tester.** All of Option A's, plus: the sibling set is closed and
identified deterministically · the shared quantity is conserved to `fsum` precision · sibling
iteration order cannot change any final ω (bit-exact, across seeds and interpreters) · a node
with one out-road is a no-op (**the degenerate case that would hide a coupling bug**) · the
2×2 factorial against 0b2's transmission normalisation, since both would now normalise and
**a shared upstream driver is the 1e-circularity shape**.

**Falsifier.** Sibling order changing any final ω by even 1 ULP; or the conserved quantity
drifting over a long run.

### 3.3 Option C — asymmetric depression with its own rate

**Mechanism.** Option A's shape, but depression carries an independent rate constant
`depression_gain ≠ base_gain`, so weakening can be slower (or faster) than strengthening.

**Constants introduced: one**, and it is the one this project is most likely to invent to
make a shape work — which is why `uncalibrated_constants` exists.

**Prior art — the most empirically supported.** Asymmetry between acquisition and extinction
is the standard finding (Bouton 2004). In reinforcement learning the same asymmetry is
explicit as differing positive and negative learning rates, with a documented optimism bias
(Frank et al. 2007, *PNAS* 104:16311; Niv et al. 2012, *J. Neurosci.* 32:551). Empirically the
best-supported of the three.

**Re-validation cost — same as Option A**, plus one more constant to justify. No coupling.

**Invariants.** Option A's, plus: the two rates are independently settable and the asymmetry
is *measurable* rather than nominal; and an asserted-negative that the neutral value of the
new constant reproduces Option A exactly.

**Falsifier.** The asymmetry constant having no measurable effect on any reachable input —
i.e. an uncalibrated constant that is also inert, which is the worst outcome: a knob that
looks like a decision and does nothing.

---

## 4. THE DECISION, and it is Cagan's

**Recommendation: Option B**, and the recommendation is *not* that it is cheapest — it is the
most expensive of the three. It is that **B is the only option that buys a second thing the
project already knows it needs.**

AOL-5 is not decoration. It was added because this project's second wall (1e′) was caused by
the absence of scarcity, and AOL-5 is what stops AOL-1…4 being satisfiable by enumeration. A
mechanism that delivers scarcity *structurally* converts a pre-registered criterion from
MECHANISM ABSENT to measurable — and it does so by extending an overlay that is already built
and verified, rather than by inventing one.

**The honest counter-argument, which is real:** B couples roads that this project has spent
four bricks proving correct *independently*. A shared denominator turns single-road properties
into set properties, adds a fold the float registry must cover, and makes sibling order
load-bearing where it was not. **A and C keep every proven property local.** If the aim is a
signed rule and nothing more, A is the cheapest honest answer and C is the empirically
best-supported one.

> **The tradeoff, in one line:** **A/C buy the missing half cheaply and leave scarcity for
> later; B buys the missing half *and* AOL-5's scarcity out of one mechanism, at the price of
> coupling roads that are currently independent and re-opening determinism and integrity
> questions against `PROVEN` bricks.**

**Nothing is built until Cagan chooses.** Whichever is chosen, every new constant lands on
`uncalibrated_constants` **with what would calibrate it**, before the constant is used.

---

## 5. Done means

1. §0 (0g) is closed **first**.
2. Neutral byte-identity holds under adversarial graphs on a frozen clock — **the gate**.
3. An outcome can make an earlier traversal **less likely**, against a control matched by
   construction, with the effect monotone in `k` and exactly zero past `L`.
4. ω stays in [0,1] under any sequence of signed outcomes; bounds are asserted, not assumed.
5. Determinism: bit-exact across 6 hash seeds × every CPython available.
6. Every new accumulation is `fsum` or registered with a bound, from the first commit.
7. 2f-i's refusal test is **CONVERTED, not deleted** — it goes red the day 2g lands, and that
   handshake is the point.
8. The delivery states what 2g does **not** establish: §2.1 and §2.2 in full.

**External and unfakeable:** clause 3 against the matched control. **A weight went down
because an outcome followed it, and a matched weight did not.** That either happens or it
does not.

---

## 6. What this brick still does not make true

The meaning bar stays exactly where it is: **open**, after three structurally distinct
refusals. 2g is a mechanism, it will be verified as a mechanism, and a signed update rule is
not evidence of learning in any sense a psychologist would recognise. What it removes is a
specific, named, honest limitation — that the graph could only move one way — and what it
leaves is everything else.
