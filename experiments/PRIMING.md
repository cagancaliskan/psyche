# Graded Semantic Priming on SWOW-EN (Phase 2B)

A pre-registered test of whether Psyche's spreading-activation engine reproduces **graded
semantic priming** on real human association norms (Small World of Words, English). The
contrast direction is known independently of Psyche, so this is a genuine prediction, not a
demonstration tuned after the fact.

All numbers below are copied verbatim from
[`results/priming_output.txt`](results/priming_output.txt). The selected pairs are in
[`results/priming_pairs_direct.txt`](results/priming_pairs_direct.txt),
[`_mediated.txt`](results/priming_pairs_mediated.txt),
[`_unrelated.txt`](results/priming_pairs_unrelated.txt).

---

## Pre-registered predictions (fixed before any activation was computed)

Printed by `priming.py` as the first thing it does (`print_preregistration`), before the
data is even loaded.

- **P1 — SANITY / INSTRUMENT CHECK (not the cognitive result).** Within DIRECT pairs, higher
  SWOW association strength → higher target activation. Should pass almost by construction;
  failure would mean the graph-building pipeline is broken.
- **P2 — THE REAL TEST.** Target-activation ordering **DIRECT > MEDIATED > UNRELATED**.
  Pre-stated outcome menu:
  - full ordering → graded priming reproduced;
  - DIRECT > UNRELATED but MEDIATED ≈ UNRELATED → direct priming only (the human pattern:
    mediated priming is weak/unreliable);
  - flat → no priming (an informative null about a pure spreading-activation account).
- **CRITICAL honest control.** DIRECT > MEDIATED is **partly mechanical** — `decay_per_hop`
  attenuates a 2-hop path more than a 1-hop path regardless of meaning (the same effect as
  the 2A fan sanity check). So the **PRIMARY COGNITIVE CONTRAST is MEDIATED vs UNRELATED**:
  does activation through a *real* 2-step associative path exceed activation to an unrelated
  node, beyond what hop-distance alone forces? The analysis is centered there.

## Readout (locked before running)

- **PRIMARY** = raw target activation, via `harness.read_targets` (one spread, many reads) —
  which returns the identical value the 2A-validated `harness.retrieval_strength` instrument
  would for each target (asserted in `test_priming.py`).
- **SECONDARY** = normalized: target activation / the prime's total outgoing activation
  (sum of activation transmitted on the prime's own out-roads). Reported, clearly labeled;
  not the primary metric.

## Method

- **Source data:** SWOW-EN `strength.SWOW-EN.R123.20180827.csv` (TAB-separated; parsed as
  plain TSV because the `csv` module crashes on two stray-quote rows — see
  [`data/README.md`](data/README.md) and [`EXPERIMENT_NOTES.md`](EXPERIMENT_NOTES.md)). Not
  redistributed; obtain locally. Citation: De Deyne, Navarro, Perfors, Brysbaert & Storms
  (2019), *Behavior Research Methods* 51(3), 987–1006.
- **Graph (built once, frozen):** one node per word; a directed road `cue → response` for
  every row with `R123.Strength > 0` (self-loops dropped). Built on `Clock(simulated=True)`
  so edge strengths are exact and the build is deterministic. **133,763 nodes, 1,388,741
  roads.**
- **Fixed edge-strength mapping (identical for every edge, no per-pair tuning):**
  `traverse_count = min(10, 1 + floor(R123.Strength * 100))` — one monotonic map from
  association strength to traverse count (and thus, via the store's strengthen dynamics, to
  edge strength).
- **Activation knobs:** library defaults (energy 1.0, decay_per_hop 0.65, floor 0.02,
  hop_budget 6) — unchanged from the verified engine.
- **Substrate choice:** the **full** graph, not the cue-core subgraph. The cue-core is too
  dense to host a topological UNRELATED condition (98% of nodes reachable within 3 hops);
  the full graph leaves a large unreachable pool. Documented in `EXPERIMENT_NOTES.md`.
- **Pair selection (BLIND — topology + SWOW strength only, fixed seed, before any spread):**
  within-prime design — for each prime one target per condition, spread once, read all three.
  - **DIRECT:** a 1-hop response of the prime (its SWOW strength recorded for P1).
  - **MEDIATED:** a node at exactly 2 hops (`prime → M → target`) that is *not* a direct
    response of the prime.
  - **UNRELATED:** a node with in-degree > 0 that is *not* reachable from the prime within
    **K = 4** hops.
  - **N = 300 primes** (300 pairs per condition).

## Result (captured verbatim)

```
RESULT — RAW target activation by condition (PRIMARY readout):
  DIRECT     N=300   mean=0.750332  median=0.330680  min=0.112775  max=13.229589  nonzero=300/300
  MEDIATED   N=300   mean=0.136601  median=0.027447  min=0.000000  max=5.158383  nonzero=185/300
  UNRELATED  N=300   mean=0.000000  median=0.000000  min=0.000000  max=0.000000  nonzero=0/300

RESULT — NORMALIZED activation (SECONDARY: share of prime's outgoing total):
  DIRECT     N=300   mean=0.049879  median=0.021410  min=0.005270  max=0.903757  nonzero=300/300
  MEDIATED   N=300   mean=0.009029  median=0.001797  min=0.000000  max=0.332900  nonzero=185/300
  UNRELATED  N=300   mean=0.000000  median=0.000000  min=0.000000  max=0.000000  nonzero=0/300

PRIMARY CONTRAST — MEDIATED vs UNRELATED (the cognitive test):
  mean:   MEDIATED=0.136601   UNRELATED=0.000000   diff=0.136601
  median: MEDIATED=0.027447   UNRELATED=0.000000
  within-prime sign test (N=300): MEDIATED>UNRELATED in 185, equal in 115, < in 0
  nonzero: MEDIATED=185/300  UNRELATED=0/300

VERDICTS (computed from the data above):
  P1 VERDICT: PASS (instrument sane) — Spearman(strength, direct activation) rho=0.2894
  P2 VERDICT: MATCHES: full ordering DIRECT > MEDIATED > UNRELATED — graded priming reproduced.
  PRIMARY VERDICT: MEDIATED > UNRELATED — median 0.027447 vs 0.000000; MEDIATED>UNRELATED in 185/300 primes (61.7%).
```

## Interpretation (honest, keyed to the pre-registered menu)

- **P1 (instrument) PASSED.** Spearman ρ = 0.2894 between SWOW association strength and the
  direct target's activation — a positive correlation, so the strength→edge→activation
  pipeline carries the gradient it should. This is a sanity check, not a cognitive claim.
- **P2 falls in the "full ordering" branch:** DIRECT (median 0.330680) > MEDIATED (0.027447) >
  UNRELATED (0.000000). On the pre-stated menu this reads as *graded priming reproduced*.
- **Primary cognitive contrast (MEDIATED vs UNRELATED): positive.** A real 2-step associative
  path delivered more activation than an unrelated node in **185/300 primes (61.7%)**, none in
  the opposite direction; the other 115 were ties at zero. So Psyche shows **mediated priming**,
  not only direct priming.

### What this does and does not establish

**Does:** On real human association norms, with conditions chosen blind from topology before
any activation was computed, and on a frozen unmodified engine, Psyche produces the expected
priming *ordering* — including a non-trivial mediated effect — deterministically and
reproducibly (byte-identical across 8 `PYTHONHASHSEED`s, `test_priming.py`).

**Does not:** This is **not** evidence of graded *competition* or of a quantitatively
human-like effect size, for three honest reasons.
1. **DIRECT > MEDIATED is partly mechanical** (decay over 1 vs 2 hops), as pre-registered;
   it is not by itself a cognitive result.
2. **UNRELATED activation was exactly 0 for all 300 pairs.** K=4-unreachable was not
   zero-*by construction* (5–6-hop paths ≤ hop_budget could exist), but the engine's
   effective spreading horizon (decay 0.65 against floor 0.02) dies out by ~4 hops, so
   "beyond 4 hops" coincided empirically with "zero measurable activation." The
   MEDIATED-vs-UNRELATED contrast is therefore partly **graded reach** (a real 2-hop path
   delivers measurable activation; a node past the horizon delivers none) rather than graded
   competition among reachable items. In 38.3% of primes (115/300) the 2-hop path itself fell
   below floor and tied unrelated at 0 — consistent with the 2A finding that weak multi-hop
   paths are floored out.
3. As established in **2A**, the engine does **not** normalize by out-degree, so the SECONDARY
   normalized readout is just the raw readout rescaled per prime (it shows the same ordering);
   it is not an independent competition measure. A true competition contrast would require a
   normalized readout layered in the measurement code (never in the engine) — left to future
   work.

**Bottom line:** Psyche reproduces the *direction* of graded semantic priming on real norms
(direct and, more interestingly, mediated > unrelated), as an honest, pre-registered,
reproducible result — while the magnitude and the competition question remain open and are
explicitly not claimed.
