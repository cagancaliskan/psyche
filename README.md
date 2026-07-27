# Nous

A **biologically-motivated, dependency-free Python prototype** of a memory-and-activation
substrate for a cognitive architecture. Nous implements, with no third-party
dependencies, a **cognitive cycle that now closes end-to-end**: (1) a graph **substrate
store** of concept *nodes* and weighted *roads* with synaptic-tagging/consolidation-*inspired*
dynamics, lazy activity-dependent decay, and "sticky" closure of traumatic edges;
(2) a deterministic **spreading-activation** engine that records per-edge flow and treats
closed roads as *leaky-not-inert* (an intrusive-recall-like breakthrough); (3) a multi-source
activation **field** that assigns each node to the source that activates it most; (4) a
**source-clustering** pre-stage that groups nearby perceived sources before the field is built;
and (5) a **workspace** stage that runs one competition among coalitions, prunes the bridged
unperceived material from the winner, and performs a single **bounded broadcast** back onto
the substrate that biases the next cycle — closing the loop
*perceive → activate → cluster → compete → prune → broadcast → next cycle*.

The substrate and activation layers are **proven** correct and deterministic. The
source-clustering and workspace layers are **mechanism-verified** (independently and
adversarially tester-verified for determinism, purity, integrity, and stability) but their
**cognitive meaning is not claimed** — closing the loop is a *mechanism* result, not a
cognitive one. The first behavioral cognitive claim has been **attempted three times and refused three
times**, each for a structurally distinct reason, and each before any graded number existed:
semantic priming was **circular** (the external norm *was* the edge weight), the fan effect
found the **generating mechanism absent**, and interoception found the **signal flat** on
realistic work. The meaning bar is still open, and the recurring obstacle is the external
yardstick rather than the mechanism.

---

## What this is (and how to read it)

Nous is **an engineering prototype and a software-testing-methodology case study**. It is
suitable as a capstone / technical-report artifact: a small, self-contained system built
test-first, where adversarial testing caught a sequence of real structural bugs that the
write-up ([docs/METHODOLOGY.md](docs/METHODOLOGY.md)) documents in detail.

It is **not** a validated cognitive model, **not** a claim of machine cognition, and **not**
a "mind," "consciousness," or "AGI." The neuroscience it borrows vocabulary from
(below) is **conceptual inspiration**, not an implemented or reproduced result. Where the
system does something unproven, this documentation says so plainly.

> Note on the `docs/design/` folder: it contains the project's **original aspirational
> vision documents**, written *before* this code and using far grander language than the
> code earns. They describe intent, not what is built. See
> [docs/design/README.md](docs/design/README.md) for the disclaimer. The honest account of
> the real system is here, in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and in
> [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

---

## Citation

This work is archived on **Zenodo** with a permanent DOI:
**<https://doi.org/10.5281/zenodo.20474613>**

If you use or reference Nous, please cite:

> Caliskan, C. (2026). *Nous: Adversarial Testing of a Dependency-Free Memory-and-Activation
> Substrate for Cognitive Architectures.* Zenodo. https://doi.org/10.5281/zenodo.20474613

The **report is open access under CC BY 4.0**; the **code is MIT-licensed** (see
[LICENSE](LICENSE)). A machine-readable [`CITATION.cff`](CITATION.cff) is provided at the
repository root.

---

## Scope: three assurance tiers (kept strictly distinct)

Not everything in the repository carries the same assurance, and the project's first discipline
is to never let one tier borrow the credibility of another. Three tiers are in play, from
strongest to weakest.

### Tier 1 — `PROVEN` (substrate + activation)

The substrate store and the spreading-activation engine are verified for three properties:

- **Determinism:** identical results across process runs, including under randomized hash
  seeds (`PYTHONHASHSEED`) checked in fresh subprocesses. This matters because the natural
  implementations leak set-iteration order (over uuid4 keys) into results.
- **Integrity:** the graph's indices, adjacency, dedup, and designations stay mutually
  consistent across every mutation; a full-graph scan finds no drift.
- **Purity:** reads never mutate stored state. Lazy time-decay is computed as a read-only
  *view*; only writes persist it. (This is load-bearing: a read that silently re-opened a
  "closed" traumatic edge would corrupt state over time. A test asserts it cannot.)

These are claims about **mechanism**: the code does exactly and only what it says, reproducibly.

> **Open defect, stated here rather than in a footnote (2026-07-25).** The determinism bullet above
> is **contested for the activation engine**. An independent adversarial pass found that convergent
> accumulation is a naive sequential float add whose term order comes from iterating a set of uuid4
> ids, so on graphs where **three or more** contributions reach the same node, fresh processes
> disagree in the last place: at library defaults, 48 processes produced two results differing by
> 1 ULP. It holds bit-exactly at in-degree ≤ 2, the substrate store is not affected, and the
> project's existing probes could not have seen it because they compare `round(x, 9)`. It is the
> same bug class as the one described under "Determinism is scoped to the interpreters it was swept
> on" below, one layer upstream, and it is **not yet fixed**. Full record:
> [docs/BUG-0b1-coalition-strength-determinism.md](docs/BUG-0b1-coalition-strength-determinism.md)
> §8. Whether Tier 1 keeps the `PROVEN` label while it stands is an open decision in
> [DECISIONS.md](DECISIONS.md) (D-011), not something quietly resolved in a README.

### Tier 2 — tester-verified mechanism (the closed cognitive cycle)

Coalition formation, the multi-source field, **source-clustering**, and the **workspace**
(competition + pruning + bounded broadcast) make the cycle close end-to-end. They are
independently and adversarially **tester-verified** for the same hard properties as Tier 1 —
determinism across processes, purity, integrity — plus the stability properties the feedback
write requires (the broadcast does not diverge and does not lock in; see below). This is a
**mechanism** result only: the loop runs, deterministically, and does exactly what it says.

What changed since the earlier draft of this README:

- **The cycle now closes.** The old "strongest coalition = the thought" placeholder is **gone**.
  A real workspace competition selects one winner, prunes the bridged unperceived material from
  it, and a single **bounded broadcast** writes the winner's reinforcement back onto the
  substrate to bias the next cycle.
- **The old over-swallow known limitation is resolved at the mechanism level.** Source-clustering
  groups nearby perceived sources before the field is built, and the workspace prunes the
  bridged unperceived domain from the winner. A **residual corner case** remains and is shipped
  as an explicit asserted-negative (see "Known limitation" below).

**Crucially, Tier 2 makes no cognitive claim.** Closing an information loop with bounded
feedback is an internal substrate property, **not** priming, awareness, or understanding. The
status of these layers is therefore `BUILT · UNVALIDATED`: mechanism-verified, meaning not yet
earned.

### Tier 3 — disciplined-exploratory (experiment scaffolding)

A separate body of pre-registered experiment scaffolding (a SWOW association-norm loader, a
fan-effect characterization, and a graded semantic-priming harness) lives under `experiments/`
and is genuinely depended upon by the structural check below. It is honest and
pre-registered, but it is a **distinct, lower** tier: it is **not** `PROVEN` and it has **not**
had a validator pass. It is an *instrument*; its existence does not establish a cognitive
result. (The instruments' **mechanism** suites — `test_harness.py`, `test_priming_instrument.py`,
`test_priming_1e.py` — were since brought into the canonical runner and are tester-verified, per
SPEC-1e §10. The data-dependent **experiment-result** scripts stay out: they need the ~53 MB
SWOW file and make meaning claims.)

One structural check has already been run on this scaffolding and is reported as the honest
negative it is: the source-clustering grouping was compared against an **independent standard
partition** of the SWOW graph (a different clustering-algorithm family). It beat the
no-clustering control decisively (sign test 170/200 probes, p ≈ 6e-25) but **missed the
pre-registered absolute bar** (mean ARI 0.228 < 0.30 — it under-merges relative to a coarse
standard partition). Verdict: **NOT YET**. This is reported as *agreement with an independent
standard partition*, not ground-truth recovery, and it does not move the source-clustering layer
out of `BUILT · UNVALIDATED`.

### The line that matters

**"The mechanism is correct and deterministic" is proven (Tier 1) or tester-verified
(Tier 2); "the mechanism reproduces a cognitive phenomenon" has not been shown.** The meaning
bar remains open after three structurally distinct refusals — see "Limitations & future work".

---

## Running the tests

Pure standard library: nothing to install (Python 3.8+; the current capture is swept across
CPython 3.10, 3.11, 3.12, 3.13 and 3.14, with 3.14 as the transcript interpreter).

```bash
# all 26 suites, with the correct PYTHONPATH handled for you:
python3 run_tests.py

# or a single suite directly (absolute PYTHONPATH so the determinism subprocess
# probes resolve their imports regardless of working directory):
PYTHONPATH="$PWD/src" python3 tests/test_nous_store.py
```

The suites use a tiny built-in harness, **not** pytest: each prints `RESULT: N passed,
M failed` and exits non-zero on any failure. Do not run them under pytest: pytest would
collect the `test_*` functions but would not register a logical `check(...)` failure as a
failed assertion, so it could report green on a real failure. Run them as scripts (or via
`run_tests.py`).

### Real results

Captured verbatim in [docs/TEST_OUTPUT.txt](docs/TEST_OUTPUT.txt). Every suite passes with
zero failures. These counts are mirrored in [`tools/ledger.json`](tools/ledger.json), which is
the single source of truth; `tools/ledger_check.py` fails the build if any document disagrees
with it.

| Suite | Layer / role | Checks passed |
|---|---|---:|
| `test_nous_store.py` | substrate store | **45** |
| `test_nous_activation.py` | spreading activation | **35** |
| `test_nous_coalitions.py` | coalition formation | **19** |
| `test_nous_field.py` | multi-source field | **13** |
| `test_nous_source_clustering.py` | source-clustering (1c) | **49** |
| `test_nous_workspace.py` | workspace competition + pruning (1d-i) | **83** |
| `test_nous_workspace_broadcast.py` | bounded broadcast + feedback (1d-ii) | **63** |
| `test_nous_perceive.py` | perception + closed end-to-end cycle | **19** |
| `test_nous_bodysensor.py` | body-state sensor + modulation hook (2c) | **49** |
| `test_tester_0b2_adversarial.py` | tester: adversarial 0b2 normalization overlay | **83** |
| `test_tester_1c_adversarial.py` | tester: adversarial 1c | **73** |
| `test_tester_1c_mutation_battery.py` | tester: 1c randomized mutation battery | **5** |
| `test_tester_1d_i_adversarial.py` | tester: adversarial 1d-i | **107** |
| `test_tester_1d_ii_adversarial.py` | tester: adversarial 1d-ii | **110** |
| `test_tester_2c_adversarial.py` | tester: adversarial 2c interoception | **350** |
| `test_tester_1e_selector_adversarial.py` | tester: 1e blind selector | **92** |
| `test_tester_1e_instrument_adversarial.py` | tester: 1e broadcast-Δ instrument | **76** |
| `test_tester_1e_loopclosed.py` | tester: 1e loop-closure | **58** |
| `test_harness.py` | experiment harness mechanism | **17** |
| `test_priming_instrument.py` | priming instrument mechanism | **42** |
| `test_priming_1e.py` | blind three-arm selector mechanism | **67** |
| **Total** | **26 suites** | **2,594 passed, 0 failed** |

That total is **2,594 assertions across 26 suites, 0 failures**, including the builder suites
above and the **independent tester-authored adversarial suites** (`test_tester_*`), which add
hostile and loop-closed checks: cross-process determinism in fresh interpreters under
`PYTHONHASHSEED ∈ {0,1,2,3,7,42}`, randomized mutation batteries interleaved with integrity
scans, no-divergence / no-lock-in stability of the broadcast write, and the resolved
over-swallow case now driven through the live cycle (formerly an asserted-negative limitation,
now a real pass).

**A passing count is not a verdict.** `test_tester_0b2_adversarial.py` above has 83 passing checks
and the tester's verdict on the brick it examines is **FAIL**: seven of nine specified invariants
hold and two do not. Three of its checks are *asserted negatives* — they pass because a defect is
present and are designed to turn red the moment it is fixed, so that a fix has to come back through
the same suite. The defects, their scope, and which of them the change introduced versus inherited
are recorded in [docs/specs/SPEC-0b2-conserved-activation.md](docs/specs/SPEC-0b2-conserved-activation.md)
§6. Read the verdict, not the count.

**Determinism is scoped to the interpreters it was swept on.** A cross-process determinism
failure lived undetected in `Coalition.strength` for a month because the suite was only ever
run on one CPython minor version: float summation over a uuid4-keyed dict is
order-dependent, so two identical coalitions differed by one ULP and that resolved the
competition before the `creation_seq` tie-break could run. It was invisible on 3.12 and
flipped the winner 10 times in 30 on 3.10, at a *fixed* hash seed. Fixed with `math.fsum`;
see [docs/BUG-0b1-coalition-strength-determinism.md](docs/BUG-0b1-coalition-strength-determinism.md).
Captures are now produced by `tools/capture_run.py`, which sweeps every CPython on the
machine and refuses to capture if they disagree. **The current capture was swept across five
CPython minor versions — 3.10, 3.11, 3.12, 3.13 and 3.14 — on macOS (Darwin arm64), all
producing identical per-suite counts and identical verdicts.** The determinism claim is
therefore scoped to those five versions and to `PYTHONHASHSEED ∈ {0,1,2,3,7,42}`, and
`tools/ledger.json` records that scope so it cannot silently narrow.

---

## Project size (measured)

| | Files | Lines (`wc -l`) | Non-blank, non-comment (approx.) |
|---|---:|---:|---:|
| Source modules (`src/`) | 8 | — | — |
| Test suites in the canonical runner (`tests/` + `experiments/`) | 21 | — | — |
| **Python total** | **29** | — | — |

Line counts are deliberately not tabulated here any more: they were hand-maintained, they
went stale, and nothing depends on them. Run `wc -l src/*.py tests/*.py` for current figures.
Assertion counts, which *are* load-bearing, live in [`tools/ledger.json`](tools/ledger.json)
and are checked against every document by `tools/ledger_check.py`.

---

## Project structure

```
nous/
├── README.md               ← you are here
├── LICENSE                 ← MIT
├── requirements.txt        ← standard library only (no dependencies)
├── run_tests.py            ← runs all 26 suites with the correct absolute PYTHONPATH
├── src/                    ← the 8 modules
│   ├── nous_store.py               substrate store (Layer 1): graph, IDs, decay, closure
│   ├── nous_activation.py          deterministic spreading activation + flow
│   ├── nous_field.py               multi-source activation field (basins)
│   ├── nous_coalitions.py          coalition formation (flow-cut & by-basin)
│   ├── nous_source_clustering.py   source-clustering pre-stage (group nearby sources)
│   ├── nous_workspace.py           workspace: competition + pruning + bounded broadcast
│   ├── nous_perceive.py            perception + the closed end-to-end cycle
│   └── nous_bodysensor.py          body-state sensor + default-off decay modulation (2c)
├── tests/                  ← the test suites (built-in harness; run as scripts)
│   ├── test_nous_*.py              builder suites (one per module)
│   └── test_tester_*.py            independent tester-authored adversarial suites
├── experiments/            ← Tier 3 disciplined-exploratory scaffolding (NOT in run_tests.py)
└── docs/
    ├── ARCHITECTURE.md         as-built technical reference
    ├── METHODOLOGY.md          the adversarial-testing development history
    ├── TEST_OUTPUT.txt         verbatim captured test run (the source of the numbers above)
    ├── nous_roadmap.md         the living roadmap (current state, tiers, next step)
    ├── specs/                  ADRs / specs the architect writes for the builder
    ├── design/                 the original *aspirational* vision docs (see its README)
    └── diagrams/               Mermaid (.mmd) diagrams
```

---

## Background (conceptual inspiration, not implementation)

Nous **borrows vocabulary and structure** from the following bodies of work. These are
*inspirations that shaped the design's framing*; Nous does **not** implement, validate, or
reproduce any of these theories or their biological results, and makes **no claim of
biological fidelity**.

- **Complementary Learning Systems** (McClelland, O'Reilly): the fast/slow,
  experience-then-consolidate split that motivates separating *activation* (what lights up
  now) from *consolidation* (what later gets reinforced).
- **Synaptic Tagging and Capture** (Frey, Morris): the framing behind treating
  reinforcement as a *gated, budgeted* event, which is why spreading activation here is a
  pure read and never strengthens what it touches.
- **Global Workspace Theory** (Baars, Dehaene): the source of the *coalitions compete, one
  is broadcast* vocabulary. Coalition *formation*, a one-winner *competition*, and a single
  *bounded broadcast* back onto the substrate now all exist as mechanism — but this borrows the
  *framing* only. No claim of conscious access, ignition, or global availability in the
  theory's sense is made; the broadcast is an internal, bounded conduction bias, nothing more.
- **LIDA cognitive cycle:** the *perceive → attend → broadcast* staging the end-to-end cycle
  is loosely shaped after. The cycle now closes (the broadcast biases the next pass), but the
  resemblance is structural framing, not an implementation or validation of the LIDA model.
- **Yerkes–Dodson** (arousal / inverted-U): appears in the design notes as motivation for
  emotionally-modulated plasticity; in the code this shows up only as charge-modulated
  strengthening, and is best read as design-level aspiration rather than a realized model.

The honest verb throughout is *"inspired by"* / *"borrows the framing of"*: never
*"implements"* or *"models"* in any validated sense.

---

## Limitations & future work

- **Cognitive meaningfulness above the substrate is unestablished:** The field, clustering, and
  workspace layers are deterministic, pure, and tester-verified as *mechanism*, but there is no
  evidence yet that the "thought" they produce is cognitively meaningful. Closing the loop is a
  mechanism result, not a cognitive one.
- **The over-swallow known limitation is resolved at the mechanism level — with a residual
  corner case shipped as an asserted-negative.** Source-clustering groups nearby perceived
  sources before basins are built, and the workspace prunes the bridged unperceived domain from
  the winner (the old "incoherent thought on clustered input" is gone, verified through the live
  cycle). The pruning rule is a **parameter-free cohesion-valley / relative-attachment
  watershed**, not literal domain-membership: an unnamed domain bridged into the named region *at
  least as strongly as its own internal cohesion* has no valley and is therefore **kept**, so
  over-swallow can recur in that specific topology. This divergence is always **safe-direction**
  (it over-includes an unnamed domain; it never over-prunes a perceived member) and is documented
  as a standing asserted-negative test rather than hidden.
- **The "strongest coalition = the thought" placeholder is gone.** It has been replaced by a real
  workspace competition (one winner, by activation density with a min-size guard), pruning, and a
  single bounded broadcast that biases the next cycle.
- **Several constants are uncalibrated guesses on probation:** notably the closed-road
  breakthrough threshold/leak fraction, the coalition flow-cut fraction, the source-clustering
  proximity threshold, and the broadcast gain (it inherits `strengthen()`'s default and is **not**
  tuned to any cognitive outcome). The tests pin the *qualitative* regime, never the magnitudes,
  and nothing downstream may depend on these numbers.
- **Perception is exact/substring token matching:** no embeddings, no fuzzy semantics. It is
  the minimal step that makes activation sources *input-derived* rather than hand-placed.
- **Backward spread is not implemented:** activation follows directed out-roads only (v1).

**The first behavioral cognitive claim is still open, and three attempts have been refused —
each before any graded number existed, each for a different structural reason.**

- **Semantic priming (1e) — CIRCULAR.** The substrate encodes SWOW association strength *as*
  the edge weight, so "related targets activate more" would have been the weight map read back
  out. The weight-blind leverage stratum the design needed populated at N = 7 against a floor of
  30, and the fallback margin was arithmetically unreachable. Frozen NO-GO.
- **Fan effect (1e′) — MECHANISM ABSENT.** The engine gives every out-road the source's full
  activation, with no division across out-edges and no per-source budget, so the fan response is
  flat to the last digit. There is no fan-dependent signal to grade. Frozen NO-GO.
- **Interoception (2c) — SIGNAL FLAT.** The body-state signal is a stall fraction, and a
  realistic `think()` is CPU-bound, so it sits at ≈ 0 and is scale-invariant. Any gradable band
  would have to be manufactured, which is forbidden. Recorded NOT-YET; the *mechanism* is
  tester-verified and is not the defect.

**The pattern is itself the finding**: the substrate and the cycle are real and verified, and the
recurring hard problem is finding an external yardstick the mechanism can both produce and be
graded against without circularity. That is the anti-circularity discipline working — three
unwinnable graded runs caught before any of them produced an uninterpretable "pass" — and it is
scoped to *this substrate and these three yardsticks*, not offered as a general claim about
spreading-activation models.

---

## License

MIT: see [LICENSE](LICENSE). Copyright (c) 2026 Cagan Caliskan.
