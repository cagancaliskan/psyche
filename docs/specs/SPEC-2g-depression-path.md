# SPEC-2g — The depression path: asymmetric depression with its own rate

**Status:** DESIGNED · **decided by Cagan 2026-07-27 (D-029)** · ready for the builder
**Revises:** SPEC-2g's own first revision, which framed three *mutually exclusive* options.
That framing was wrong and is corrected in §1.
**Depends on:** 2f-i `BUILT-UNVALIDATED` (the trace), 0a `PROVEN` (the write path),
**0g (§0, mandatory step zero)**
**Date:** 2026-07-27
**Author lane:** architect-pm

---

## 0. STEP ZERO — brick 0g, mandatory, before any 2g code

**Fix `bound_on_absence`'s line-anchored dismissals first.**

Dismissals are keyed `path:line`. Inserting **one comment line** at the top of
`psyche_field.py` shifts every line below it and fires a **false `[C6]`** against the
`ActivationField.flow` bound. 2g edits `src/` — a new parameter on an existing signature and
a new branch in the write path — and will trip this constantly.

**Why it is step zero rather than a nuisance to work around.** It has already caused one real
mis-measurement: the tester's first blind-spot probe prepended to an existing module and
reported **all five** blind spots as CAUGHT. That was the *shifted* bound firing, not the
binding bound working.

> **A false positive that masquerades as the check working is worse than a silent gap.** A
> silent gap is a known unknown. A lying gate teaches people to re-key mechanically instead
> of re-reading — *verbatim* the failure the `Accumulation` dataclass docstring says it avoids
> by not keying on line number, reintroduced one field away. A gate that cries wolf gets
> ignored, and being ignored would waste the foundation arc that produced it.

**Fix shape (not decided):** a content-anchored key — the source line's text, or an AST path.
**Acceptance:** inserting a comment anywhere in `src/` changes no finding, and every existing
dismissal still resolves.

Same placement L3 had as 2f's step zero, for the same reason: **ownership sits with the brick
that needs the coverage.**

---

## 1. The framing error in this spec's first revision, corrected

The first revision presented three **mutually exclusive** options: symmetric (A), competitive
/ shared-budget (B), asymmetric-with-own-rate (C). **That was wrong about B and C, and the
error was mine.**

**B and C are not alternatives. They are different mechanisms at different scopes and
timescales, and the literature this spec already cites treats them as composed rather than
opposed:**

- **C is a LOCAL rule** — per-road, per-outcome, fast (the update happens on the event).
- **B is a GLOBAL constraint** — across a road's siblings, slow, and about keeping a *set* in
  range rather than about any one event.

**Turrigiano & Nelson (2004)** is the clearest case: homeostatic synaptic scaling is framed
throughout as a **complement to** Hebbian plasticity, not a replacement — the argument being
that Hebbian rules are inherently destabilising (strong synapses get stronger) and therefore
*require* a slower homeostatic mechanism alongside them. Scaling multiplicatively adjusts a
neuron's synapses **while preserving their relative weights**, which is precisely a design for
coexisting with a local rule rather than overriding it. **Oja (1982)** is a case where the two
are *fused in one equation* — Hebbian learning plus a normalisation term, derived as an
approximation to normalised Hebbian learning. **Miller & MacKay (1994)** is *about the
interaction*: its whole subject is what a normalisation constraint does to the outcome of a
Hebbian rule. **Carandini & Heeger (2012)** concerns response normalisation rather than
plasticity, so it supports "normalisation is a distinct layered operation" and does not speak
to this question directly.

**So Cagan's reading is right, and sequencing them is coherent.**

### 1.1 One refinement, and it changes 2h's price rather than the decision

They are complementary in the sense of **composed**, not **independent**. Miller & MacKay's
central result is that the *choice* of constraint changes what the local rule **converges
to** — subtractive normalisation drives winner-take-all outcomes, multiplicative gives graded
ones. So **B is not a pure addition on top of C: adding B later will perturb C's behaviour,
not merely sit beside it.**

**Consequence, recorded in 2h and not here:** when 2h lands, **2g's graded-effect invariants
must be re-run under the new constraint**, and 2h's own delivery must show that C's asserted
properties still hold. That is a real cost and it belongs to 2h.

### 1.2 Epistemic status of the paragraph above — stated, not assumed

This assessment is made **from knowledge of these sources, not from re-reading them at
verification time.** The project has a precedent for exactly this situation (the Butlin
figure, which is marked verified against the arXiv version only, and explicitly *not*
upgradeable until someone reads the published one). The same discipline applies here:

> **What would confirm it:** reading Turrigiano & Nelson (2004) §"Synaptic scaling and Hebbian
> plasticity" and Miller & MacKay (1994) §2 directly. **What would falsify it:** either source
> framing normalisation as a *substitute* for a local sign-carrying rule rather than a
> constraint on it. Until someone reads them, §1 is an *assessment*, and the sequencing rests
> on it.

**It is not load-bearing for 2g itself.** 2g is buildable and verifiable whether or not 2h
ever exists; the assessment governs only the claim that 2h is a *later addition* rather than
a *replacement*.

---

## 2. Option A — recorded as REJECTED, not deleted

**Symmetric depression: one rate for both directions, no new constant.**

**Rejected, and the reason is not cost.** Symmetry is **empirically rejected**: extinction is
not the reverse of acquisition. Spontaneous recovery, reinstatement and renewal all show the
original association survives extinction (Bouton 2004, *Learning & Memory* 11:485). Its
attraction was that it introduces no constant at all.

> **A known-wrong mechanism is not made acceptable by being free.** That is the whole content
> of this rejection, and it is kept visible rather than deleted so that the next person
> tempted by the cheapest option finds the reason it was refused.

---

## 3. The mechanism (Option C)

**Accept a signed `outcome_magnitude`. A negative outcome applies the same
eligibility-weighted rule with an INDEPENDENT rate**, so weakening need not mirror
strengthening:

- potentiation: `Δω = base_gain · P_PRP · e(k) · outcome · (1 − ω)` — today's rule, unchanged
- depression: `Δω = depression_gain · P_PRP · e(k) · outcome · ω` — the mirror, saturating at
  the floor as potentiation saturates at the ceiling

Eligibility `e(k)` is untouched: still a function of the integer cycle distance only, still
exactly zero past the window. **Nothing about the sign may enter `e(k)`** — the moment it
does, eligibility stops being a function of time alone and the anti-readback argument dies.

### 3.1 The constant

**One new constant: `depression_gain`.** It is already registered on
`uncalibrated_constants` **with what would calibrate it**, before any code exists.

**What would calibrate it:** the acquisition/extinction asymmetry is well documented (Bouton
2004; Frank et al. 2007, *PNAS* 104:16311; Niv et al. 2012, *J. Neurosci.* 32:551, on
differing positive and negative learning rates and a documented optimism bias) — but the
**ratio is task- and species-specific and no published value transfers.** So it ships
uncalibrated and is *named* as such.

**Its falsifier is the sharpest in this spec:** a constant with **no measurable effect on any
reachable input** — a knob that looks like a decision and does nothing. The tester must show
the asymmetry is *measurable*, not nominal.

### 3.2 The gated overlay — not negotiable

Default-off; the neutral value **byte-identical** to current behaviour; proven under attack
**on a frozen clock**. A live clock manufactures a difference through lazy decay — measured
at six roads differing with no credit code involved — and this project has filed a false
defect that way.

**The neutral value is `depression_gain = 0.0`**, at which a negative outcome produces zero
change and the module reduces exactly to 2f-i. Note the trap this inherits from 2f-i: the
neutral path must **not call `strengthen()` with a zero gain**, because `strengthen` also
advances `traversal_count`, sets `last_touched` and re-evaluates closure. Skipping the call is
what makes neutrality byte-identical, and it is already asserted for the potentiation side.

---

## 4. Re-validation cost

| Brick | Cost | Why |
|---|---|---|
| **0a** store | **the write path only** | a signed write is a change to `PROVEN` code: purity, integrity and determinism legs re-run. No data-model change, no coupling. |
| **0b / 0b2 / 0c** | **none at neutral** | no read path changes |
| **1a–1d, 2c** | **none at neutral** | overlay discipline |
| **0d** | **prerequisite** | any new accumulation is `fsum` or registered, from the first commit |
| **0g** | **step zero** | §0 |
| **2f-i** | **its refusal test CONVERTS** | see §5 clause 7 |

**No coupling between roads.** Every property this project has proven about a single road's
update stays a property about a single road. That is Option C's structural advantage and the
reason it is buildable now.

---

## 5. Done means

1. **§0 (0g) is closed first.**
2. Neutral byte-identity holds under adversarial graphs on a frozen clock — **the gate**.
3. An outcome can make an earlier traversal **less likely**, against a control **matched by
   construction**, with the effect monotone in `k` and exactly zero past `L`.
4. ω stays in **[0, 1]** under any sequence of signed outcomes; the bounds are asserted, not
   assumed.
5. The asymmetry is **measurable**: `depression_gain ≠ base_gain` produces a different
   magnitude than the symmetric case on the same input, and the difference is demonstrated.
6. Determinism: bit-exact across 6 hash seeds × every CPython available.
7. **2f-i's refusal test is CONVERTED, not deleted.** It goes red the day 2g lands, and that
   handshake is the point — the assertion moves from *"a negative is refused because no
   depression path exists"* to *"a negative is honoured, and here is the rate."*
8. The delivery states what 2g does **not** establish: §7 in full.

**External and unfakeable:** clause 3. **A weight went down because an outcome followed it,
and a matched weight did not.** That either happens or it does not.

---

## 6. Invariants for the tester

- **D-1** Neutral byte-identity (`depression_gain = 0.0`), adversarial graphs, frozen clock.
  **The gate.** Measure the noise floor first.
- **D-2** A negative outcome lowers the paired road and **not** a matched control built by
  construction.
- **D-3** Monotone non-increasing in `k`; **exactly zero** past `L`, established structurally
  rather than by sampling.
- **D-4** ω ∈ [0, 1] under any signed sequence — including a long alternating run.
- **D-5** `+x` then `−x` does **not** return ω to its start, and **whichever way that lands is
  asserted rather than assumed.** With an independent rate it cannot be symmetric; the test
  must pin the actual behaviour.
- **D-6** The asymmetry is measurable (§5.5), and an **asserted-negative** that
  `depression_gain = base_gain` reproduces the symmetric case exactly.
- **D-7** Eligibility is **unchanged and still sign-blind**: `e(k)` byte-identical for a
  positive and a negative outcome of the same magnitude. *This is the anti-readback guarantee
  and it must not weaken.*
- **D-8** Purity until the explicit write; the store byte-identical after a refused call.
- **D-9** Parameter validation on the new constant: non-finite and out-of-range refused at the
  boundary, per DEFECT-C's class.
- **D-10** Determinism across seeds and interpreters, bit patterns never `round(x, 9)`.
- **D-11** **ASSERTED-NEGATIVE, scope:** 2g adds a sign; it adds no goal, no output selection
  and no skill. §7 is asserted, not merely written.

**Falsifier for the brick:** `depression_gain` having no measurable effect on any reachable
input; or a signed sequence driving ω outside [0, 1]; or the final ω depending on the *order*
of a set of outcomes delivered in one window.

---

## 7. What 2g does NOT make true — stated so it cannot be assumed

**It does not reach Butlin AE-1.** *"Learning from feedback and selecting outputs so as to
pursue goals, especially where this involves flexible responsiveness to competing goals."*

With 2g, feedback acquires a sign, so the **first** conjunct becomes arguable in the narrow
arithmetic sense. **The second still fails outright**: the system selects no outputs and
pursues no goals, because it has none. There is no action, no goal representation, and no
policy over either.

> **2g moves AE-1 from failing at two conjuncts to failing at one.** That is progress on an
> architectural axis and it is **not** satisfaction of the indicator. A reader must not be
> able to take the missing half being filled as the picture being complete.

**AOL criteria moved by 2g: none.** All five need goal generation or skill representation;
2g is neither. **AOL-5 (does choosing cost anything) is reachable only through the
competitive mechanism — brick 2h** — because scarcity is a property of the mechanism, not of
the goal layer.

**The meaning bar stays exactly where it is: open, after three structurally distinct
refusals.** A signed update rule is not evidence of learning in any sense a psychologist would
recognise. What 2g removes is one specific, named, honest limitation — that the graph could
only move one way. What it leaves is everything else.
