# The consciousness question: an external, architectural yardstick

**Written:** 2026-07-25 · **Landed in repo:** 2026-07-26 · **Assessment date:** 2026-07-25

**Why this file exists.** The figure "0 of 14, 1 partial" was cited in project records and in
conversation for two days while the assessment backing it lived nowhere in this repository. That
is `C1`/`C2`'s failure class arriving through *absence* rather than drift: a number with no
checkable provenance is not better than a stale one, it is worse, because nothing can catch it.
Flagged by architect-pm on 2026-07-26; this document is the fix. **The figure must not be cited
anywhere — roadmap, ledger, paper, or conversation — except by reference to this file.**

**Provenance of the indicator list.** The fourteen indicators and their wording were re-verified
on 2026-07-26 against Table 1 of arXiv:2308.08708. The published version (*Identifying indicators
of consciousness in AI systems*, Trends in Cognitive Sciences, 2025) was **not** directly
accessible at verification time and its list was therefore **not** independently confirmed to be
identical. **Falsifier: a copy of the published version showing an added, removed, or reworded
indicator.** Until someone checks that, this assessment is against the preprint list, and should
be described that way.

**Purpose.** Give the project a way to make checkable progress toward the consciousness question
without ever making a consciousness claim — which `CONTRIBUTING.md` rule 1 forbids, and should keep
forbidding.

---

## 1. Split the question first, or nothing below makes sense

**The hard problem** (Chalmers): why is there something it is like to be a system at all. Nothing
anyone can build touches this. No experiment distinguishes a system that has experience from a
functional duplicate that does not. This is not pessimism about this project specifically; it is
the unmoved state of the question after thirty years. **Psyche should never claim anything here,
and should never be designed as though it could.**

**The functional / access questions**: global availability of information, metacognitive
monitoring, attention control, integration, self-modelling, reportability. These are buildable,
measurable, and are where every research programme that produces anything actually operates.

The move that keeps the project honest is to work entirely in the second category and let other
people argue about whether it bears on the first.

## 2. The empirical situation, as of 2025–2026

The Cogitate consortium's adversarial collaboration between Global Neuronal Workspace Theory and
Integrated Information Theory reported in *Nature* (2025): 256 participants, fMRI + MEG +
intracranial EEG, pre-registered predictions from both camps.

**Neither won.** Conscious content was decodable in *both* posterior and prefrontal cortex.
Against IIT: no sustained synchronization within posterior cortex, contradicting the claim that
network connectivity specifies consciousness. Against GNWT: across 655 prefrontal electrodes,
none showed the predicted onset-and-offset ignition pattern; ignition at stimulus offset was
largely absent.

*(These are external figures quoted from the cited paper, not project counts. They are outside
the ledger's scope by construction — see the count-quarantine note in §7.)*

**The operational consequence: do not bet the architecture on one theory.** Psyche sits in the
GWT/LIDA lineage by construction, and GWT's most specific neural prediction just failed its own
pre-registered test. A pluralist target is the correct posture, and one exists.

## 3. The yardstick: theory-derived indicator properties

Butlin, Long et al., *Consciousness in Artificial Intelligence: Insights from the Science of
Consciousness* (arXiv:2308.08708; published as *Identifying indicators of consciousness in AI
systems*, TiCS 2025). The method: take the major computational theories, derive from each the
**architectural** properties a system would need, and assess systems against the list rather than
against a behavioural test.

This is the right shape for this project for a reason that matters:

> **It is an architectural yardstick, not a behavioural one.** Every wall this project has hit —
> 1e circular, 1e′ mechanism-absent, 2c signal-flat — was a wall in *behavioural* measurement
> against external human data. An architectural indicator is assessed by reading the
> architecture. It cannot be circular, because the project did not author the list, and it cannot
> be signal-flat, because it is not a measurement.

The report's own conclusion is also the right register: no current AI system is conscious, **and
there are no obvious technical barriers to building systems that satisfy the indicators.**
Satisfying indicators is explicitly not a consciousness claim. That is exactly the sentence
structure `CONTRIBUTING.md` already demands.

**This is a distinct axis from the autonomy criteria in `SPEC-2e-autonomy-criteria.md` (AOL-1…5).**
Those are behavioural and measure open-ended learning; these are architectural and are assessed by
reading code. Neither supersedes the other, and neither is a consciousness test.

## 4. Psyche assessed against all 14 indicators — 2026-07-25

Indicator wording is quoted from arXiv:2308.08708 Table 1. Status is this project's own
assessment and is the falsifiable part.

| # | Indicator (quoted) | Status | Assessment |
|---|---|---|---|
| **RPT-1** | "Input modules using algorithmic recurrence" | ✗ | Perception is exact/substring token matching. The *cycle* is recurrent (broadcast → next cycle); the *input module* is not. |
| **RPT-2** | "Input modules generating organised, integrated perceptual representations" | ✗ | No binding, no integration. Perception emits sources, nothing more. |
| **GWT-1** | "Multiple specialised systems capable of operating in parallel (modules)" | ✗ | Layer 0 specifies eight brain systems; one pipeline is built. Single-threaded, no parallelism. |
| **GWT-2** | "Limited capacity workspace, entailing a bottleneck in information flow and a selective attention mechanism" | ✗ → **0b2** | The engine has no scarcity by default: `outgoing = node_act` down every road. The default-off normalization overlay (0b2) is the mechanism; its default flip is a separate brick with its own gate. **The single indicator most specific to the theory Psyche is built in, and it is the one the engine lacks.** |
| **GWT-3** | "Global broadcast: availability of information in the workspace to all modules" | ◐ | The broadcast mechanism exists (1d-ii), bounded and tester-verified. But it writes back onto the substrate; there are no modules for it to be *available to*. **Mechanism present, scope absent** — which is precisely why this is ◐ and not ✓. |
| **GWT-4** | "State-dependent attention, giving rise to the capacity to use the workspace to query modules in succession to perform complex tasks" | ✗ | No task capability. |
| **HOT-1** | "Generative, top-down or noisy perception modules" | ✗ | Perception is bottom-up and deterministic. |
| **HOT-2** | "Metacognitive monitoring distinguishing reliable perceptual representations from noise" | ✗ | `docs/design/psyche_self_model.md`. Designed in detail, entirely unbuilt. |
| **HOT-3** | "Agency guided by a general belief-formation and action selection system, and a strong disposition to update beliefs in accordance with the outputs of metacognitive monitoring" | ✗ | `docs/design/psyche_motivation_architecture_v2.md`. Presupposes credit assignment — **2f**. |
| **HOT-4** | "Sparse and smooth coding generating a 'quality space'" | ✗ | **Architectural tension worth knowing.** Psyche is *localist* — one node per concept — which is the opposite of a smooth quality space. There is no similarity metric between concepts except graph distance. Downstream of the "no embeddings" decision, and not a small gap. |
| **AST-1** | "A predictive model representing and enabling control over the current state of attention" | ✗ | `docs/design/psyche_attention_awareness.md` plus the self-model *is* an attention schema. Graziano's theory is the most straightforwardly engineerable of the set, and most of the design already exists on paper. |
| **PP-1** | "Input modules using predictive coding" | ✗ | Nothing in the system predicts anything. |
| **AE-1** | "Learning from feedback and selecting outputs so as to pursue goals, especially where this involves flexible responsiveness to competing goals" | ✗ → **2f** | Temporal credit assignment — the hole Layer 0 admits has no owner. |
| **AE-2** | "Modeling output-input contingencies, including some systematic effects, and using this model in perception or control" | ✗ | No action, so no contingencies to model. |

**Score: 0 of 14 met, 1 partial (GWT-3).** That is the honest baseline, and it is not a
humiliating one — the report finds the same of every deployed AI system, including the large ones.

**Falsifier for this assessment as a whole:** any indicator marked ✗ for which a reader can point
at the code that satisfies it, or any ✓/◐ that cannot be pointed at. Each row is intended to be
checkable by reading the named module or design document.

**The convergence worth noticing:** the current program was derived from the engine's three
failures, with no reference to this list. It lands on **GWT-2** (0b2) and **AE-1** (2f) — two of
the most fundamental unmet indicators. The diagnosis and the external yardstick agree
independently. That agreement is evidence, but it is weak evidence: both were produced by the
same project, and neither is an external test.

## 5. How this becomes a spine

Each unmet indicator is a brick with a citation, an external definition the project did not
author, and a done-means assessable by reading the architecture. That is a roadmap the project can
execute for years without ever needing a behavioural yardstick it cannot find.

Suggested order after 2f, by buildability × leverage:

1. **AST-1** — attention schema. Most engineerable; the design largely exists; the one indicator
   whose theory was *built* to be implemented rather than measured in brains.
2. **HOT-2** — metacognitive monitoring. Needs a confidence signal separable from the first-order
   activation, with calibration measurable against ground truth. Directly gradeable.
3. **RPT-1 / PP-1** — a perception module that predicts and recurs, replacing token matching.
   Also fixes the shallowest embarrassment in the current system.
4. **GWT-1** — actually build the eight-system parallel topology Layer 0 already specifies.
5. **HOT-4** — the quality-space problem. The hardest, because it argues with the localist
   representation choice at the substrate. Do not touch until there is a reason.

**This ordering is a suggestion, not a commitment,** and it is subordinate to the standing rule
that nothing above temporal credit assignment gets built until credit assignment exists.

## 6. The failure mode to guard against

Consciousness is the topic on which a solo researcher most reliably spends a decade producing
something nobody can disagree with. **Unfalsifiability, not difficulty, is what kills projects
here.**

Three recorded NO-GOs before any graded number is the strongest available evidence that this
project has the antibodies. But the discipline has not yet been tested against a topic that
actively rewards grandiosity. The rule that keeps it safe is already written:

> `CONTRIBUTING.md` rule 1: Psyche is never called "a mind," "conscious," "sentient," "AGI," or "a
> validated cognitive model."

**Keep it. Forever.** The indicator list is how the project makes real progress toward the
question while never once needing to break that rule. "The architecture satisfies GWT-2 and AE-1,
assessed against Butlin et al.'s indicator properties" is checkable, citable, modest, and true. It
is also a far stronger thing to put in front of a reviewer than any claim about minds.

## 7. Notes for the gates

- **C4 (forbidden claims).** This document uses "conscious" and "consciousness" throughout, in the
  only context where the project can legitimately do so: its subject *is* the claim, and its
  entire content is the argument for why the project must never make it. It therefore belongs in
  `claim_quarantine_paths` — **with that reason recorded, not merely listed.** A quarantine
  granted for convenience is how a forbidden-claim gate rots.
- **C2 (prose counts).** The external figures in §2 (256 participants, 655 electrodes) and the
  score in §4 are not project test counts. If C2 reaches for them, they belong in
  `count_quarantine_paths` with a reason, not silenced by rewording.

---

## Sources

- Butlin, Long, et al., *Consciousness in Artificial Intelligence: Insights from the Science of
  Consciousness*, arXiv:2308.08708. Published as *Identifying indicators of consciousness in AI
  systems*, Trends in Cognitive Sciences (2025). https://arxiv.org/abs/2308.08708
- Cogitate consortium, *Adversarial testing of global neuronal workspace and integrated
  information theories of consciousness*, Nature (2025).
  https://www.nature.com/articles/s41586-025-08888-1
