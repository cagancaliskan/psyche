# Fan-Effect Characterization (Phase 2A)

A pre-registered, deterministic measurement of how a target node's activation depends on
the **fan** (out-degree) of its source in Psyche, compared to the human fan effect. This is
the warm-up study for the empirical-validation phase: its primary deliverable is a reusable,
honest measurement harness and a characterized result — including the possibility (here,
the reality) of a **null**.

All numbers below are copied verbatim from
[`results/fan_effect_output.txt`](results/fan_effect_output.txt) (and the mechanism numbers
from [`results/step0_probe_output.txt`](results/step0_probe_output.txt)).

---

## Pre-registered prediction

> **Retrieval strength DECREASES as source fan (out-degree) increases.**

This is the direction of the **human fan effect** (Anderson): the more facts associated
with a concept, the slower/weaker the retrieval of any one of them. The prediction was
fixed before any measurement and is printed by `fan_effect.py` *before* any result is
computed (`print_preregistration`, called first in `main`).

## Bridge assumption

The human fan effect is measured as retrieval **latency** (reaction time). Psyche has no
latency — it produces an **activation magnitude**. We bridge the two by mapping:

> **higher activation = faster / stronger retrieval.**

Under this mapping, the human "slower retrieval at higher fan" becomes the Psyche prediction
"**lower activation at higher fan**." This bridge is an assumption, stated explicitly so it
can be challenged; it is the only way a magnitude model can be compared to a latency effect.

---

## Method

**Graph construction.** For each fan level `F`, build a *star*: one source `S` with `F`
out-roads to leaf targets `T1..TF` (`harness.star_spec`). Every edge is crossed the same
number of times (`STRENGTH_COUNT = 3`) on a **simulated clock** (`Clock(simulated=True)`),
so all edges have exactly equal strength and nothing decays during construction. This makes
"all edges equal strength" an exact control and the whole build deterministic
(`harness.build_graph_from_spec`).

**Readout (the instrument).** `harness.retrieval_strength(store, cue, target)` runs the
library's deterministic `spread_activation` from the cue and returns the target's
accumulated activation (0.0 if unreached). It is a **pure read** — asserted in
`test_harness.py` (the store is byte-identical before and after). This single definition is
"retrieval strength" for the study.

**Aggregation.** `harness.run_trials` rebuilds each condition `N_TRIALS = 5` times (fresh
uuid4 IDs each time) and reports mean and spread. Because the engine is verified invariant to
the uuid4 / hash-seed randomness, every trial is identical and **spread = 0.0** — itself a
determinism confirmation.

**Held constant across all conditions (only `F` varies):**

| factor | value |
|---|---|
| edge strength (traverse count per edge) | `3` |
| seed energy | `1.0` |
| decay_per_hop | `0.65` |
| floor | `0.02` |
| hop_budget | `6` |
| trials per condition | `5` |
| designated readout target | `T1` |

**Controls.**
- **Target symmetry** — for `F=8`, reading any of `T1..T8` gives the same value, so the
  choice of `T1` is not load-bearing. Captured: `distinct values observed =
  [0.2433743975]`, `spread across targets = 0.0 -> SYMMETRIC`.
- **Only-varied-factor** — the table above is printed by the experiment so it is visible
  that nothing but `F` changes between conditions.

---

## Result (captured verbatim)

```
RESULT — fan F vs mean activation at target T1
    F   mean target activation      spread (max-min)
  ---   --------------------------  ------------------
    1   0.2433743975                0.0
    2   0.2433743975                0.0
    4   0.2433743975                0.0
    8   0.2433743975                0.0
   16   0.2433743975                0.0

VERDICT:
  DOES NOT MATCH: activation is flat across fan — the engine does not normalize by out-degree (see EXPERIMENT_NOTES.md).
```

The curve is perfectly flat: the target's activation is the **same value to the last digit**
across fan 1 → 16.

---

## Interpretation (honest)

**The prediction is falsified, and that is the correct, informative outcome — not a bug.**

The mechanism was determined *before* the experiment (see
[`EXPERIMENT_NOTES.md`](EXPERIMENT_NOTES.md), STEP 0). In `spread_activation`, each out-road
is fed the source's **full** activation (`outgoing = node_act`), and
`transmitted = outgoing * road.strength * decay_per_hop`. There is **no division of the
source's energy among its out-roads** — no out-degree normalization, no per-source energy
budget. So a target's activation is determined by *its own* incoming edge strength and
distance, and is completely independent of how many siblings its source has.

The `1-vs-8` probe confirmed this directly (both `0.2433743975`), and the full sweep
confirms it across `{1,2,4,8,16}`. The human fan effect arises precisely from a *capacity /
normalization* assumption (a fixed activation source shared among more associations, or
competition at retrieval). Psyche's spreading activation makes no such assumption, so under an
equal-strength, connectivity-only manipulation it **cannot** produce a fan effect. The
engine was not modified to manufacture one.

What this study *does* establish positively: a reusable, deterministic, pure-read harness;
a pre-registered protocol; an adversarial cross-process determinism guarantee on the whole
result; and a cleanly characterized null with a mechanistic cause.

---

## Implication for the priming study (2B)

Because activation is **not** normalized by out-degree (and is not divided across competing
associations), two consequences follow for designing the semantic-priming study:

1. **A connectivity-only contrast will register, but a competition/fan contrast will not.**
   "Connected vs unconnected" (does a cue raise a target's activation above zero?) is a
   contrast Psyche *can* show, because reachability and edge strength drive the readout. But
   anything that depends on associations *competing* for a shared activation budget (fan,
   interference) will read flat under the current engine.

2. **Use a graded-magnitude contrast, or add a normalized readout — do not rely on mere
   connectivity counts.** The priming study should manipulate something the engine is
   actually sensitive to: **edge strength** (e.g. a strongly-primed vs weakly-primed
   relation via traverse count) and/or **path distance** (hops, via `decay_per_hop`), and
   measure the graded change in target activation. If a *competition* effect is wanted, it
   would require a normalized readout (e.g. target activation as a *share* of the cue's total
   outgoing activation) layered in the harness — explicitly, on top of the frozen engine,
   never by altering the engine. The honest framing for 2B is therefore: predict and measure
   a **graded** priming magnitude, not a binary connected-vs-unconnected difference, and keep
   any normalization in the measurement layer where it can be stated and tested.

**Decision to pre-register before 2B (do not resolve now).** STEP 0 showed that
`retrieval_strength` currently measures **raw transmitted activation**
(`energy × strength × decay` at a hop-1 target), *not* "share of the cue's outgoing
activation." Both are legitimate instruments, but they license *different* effects, so the
priming study must commit to one **in advance, on the record, before any priming run:**
- **Raw activation (as-is):** the contrast is **presence/absence** — a related (reachable)
  target lights up; an unrelated (unreachable) target does not. This is the effect Psyche can
  show with the current engine and readout, and it is what 2B should pre-register if it keeps
  this instrument.
- **Normalized / graded readout (added in the measurement layer):** relatedness *strength*
  maps to activation *magnitude* (e.g. target activation as a share of the cue's total
  outgoing activation, or driven by graded edge strength / path distance). This is required
  for any *graded* or *competition*-style priming prediction.

This note exists so that the choice — and therefore 2B's prediction — is registered before
data is collected, never reverse-engineered from a result. The engine is not changed either
way; any normalization lives in the harness, where it can be stated and tested.
