# The substrate: stage 1 of Psyche

> **Stage 1 of Psyche: the substrate.** This is the foundation of Psyche, an open research
> project that builds brain-inspired components in stages with AGI as its long-term aim, and the
> origin of the project's method. Its development has been paused since 2026-10-23 (D-031) while
> stage 2, spiking cognitive maps, is the active line; its code, suites, ledger and this record
> stay maintained. Project overview: [README](../README.md); how the substrate led to stage 2:
> [Origins](research/origins.md). The text below was the repository README until 2026-10-23, when
> the substrate was the whole project, so in it the name "Psyche" refers to the substrate;
> [About this page](#about-this-page) lists every edit made since.

A **biologically-motivated, dependency-free Python prototype** of a memory-and-activation
substrate for a cognitive architecture. Psyche implements, with no third-party
dependencies, a **perceive-to-broadcast cycle that now closes end-to-end**: (1) a graph **substrate
store** of concept *nodes* and weighted *roads* with consolidation-*inspired*
dynamics, lazy activity-dependent decay, and "sticky" closure of traumatic edges;
(2) a deterministic **spreading-activation** engine that records per-edge flow and treats
closed roads as *leaky-not-inert* (an intrusive-recall-like breakthrough); (3) a multi-source
activation **field** that assigns each node to the source that activates it most; (4) a
**source-clustering** pre-stage that groups nearby perceived sources before the field is built;
and (5) a **workspace** stage that runs one competition among coalitions, prunes the bridged
unperceived material from the winner, and performs a single **bounded broadcast** back onto
the substrate that biases the next cycle — closing the loop
*perceive → activate → cluster → compete → prune → broadcast → next cycle*.

The substrate and activation layers are **verified** correct and deterministic. The
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

The substrate is **an engineering prototype and a software-testing-methodology case study**: a
small, self-contained system built test-first, where adversarial testing caught a sequence of
real structural bugs that the write-up ([docs/METHODOLOGY.md](METHODOLOGY.md)) documents in
detail.

The long-term aim of the whole project, Psyche, is artificial general intelligence (AGI), stated
only as an aim. This substrate is not AGI and makes no such claim. It is **not** a validated cognitive model, **not** a
claim of machine cognition, and **not** a "mind" or "consciousness." The neuroscience it borrows
vocabulary from
(below) is **conceptual inspiration**, not an implemented or reproduced result. Where the
system does something unverified, this documentation says so plainly.

> Note on the `docs/design/` folder: it contains the project's **original aspirational
> vision documents**, written *before* this code and using far grander language than the
> code earns. They describe intent, not what is built. See
> [docs/design/README.md](design/README.md) for the disclaimer. The accurate account of
> the real system is here, in [docs/ARCHITECTURE.md](ARCHITECTURE.md), and in
> [docs/METHODOLOGY.md](METHODOLOGY.md).

---

## Citation

This work is archived on **Zenodo** with a permanent DOI:
**<https://doi.org/10.5281/zenodo.20474613>**

If you use or reference Psyche, please cite:

> Caliskan, C. (2026). *Nous: Adversarial Testing of a Dependency-Free Memory-and-Activation
> Substrate for Cognitive Architectures.* Zenodo. https://doi.org/10.5281/zenodo.20474613

The **report is open access under CC BY 4.0**; the **code is MIT-licensed** (see
[LICENSE](../LICENSE)). A machine-readable [`CITATION.cff`](../CITATION.cff) is provided at the
repository root.

---

## Scope: three assurance tiers (kept strictly distinct)

Not everything in the repository carries the same assurance, and the project's first discipline
is to never let one tier borrow the credibility of another. Three tiers are in play, from
strongest to weakest.

### Tier 1 — verified (substrate + activation)

The ledger's status name for this tier is `PROVEN`. It means: verified by the full adversarial
suite on every interpreter; it is not a formal proof.

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
> [docs/BUG-0b1-coalition-strength-determinism.md](BUG-0b1-coalition-strength-determinism.md)
> §8. Whether Tier 1 keeps the `PROVEN` label while it stands is an open decision in
> [DECISIONS.md](../DECISIONS.md) (D-011), not something quietly resolved in a README.

Later record: this defect was fixed and Phase 0 returned to its earlier status (D-013, D-016
in [DECISIONS.md](../DECISIONS.md)).

### Tier 2 — tester-verified mechanism (the closed perceive-to-broadcast cycle)

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
and is genuinely depended upon by the structural check below. It is disciplined and
pre-registered, but it is a **distinct, lower** tier: it does **not** hold `PROVEN` and it has **not**
had a validator pass. It is an *instrument*; its existence does not establish a cognitive
result. (The instruments' **mechanism** suites — `test_harness.py`, `test_priming_instrument.py`,
`test_priming_1e.py` — were since brought into the canonical runner and are tester-verified, per
SPEC-1e §10. The data-dependent **experiment-result** scripts stay out: they need the ~53 MB
SWOW file and make meaning claims.)

One structural check has already been run on this scaffolding and is reported as the
negative it is: the source-clustering grouping was compared against an **independent standard
partition** of the SWOW graph (a different clustering-algorithm family). It beat the
no-clustering control decisively (sign test 170/200 probes, p ≈ 6e-25) but **missed the
pre-registered absolute bar** (mean ARI 0.228 < 0.30 — it under-merges relative to a coarse
standard partition). Verdict: **NOT YET**. This is reported as *agreement with an independent
standard partition*, not ground-truth recovery, and it does not move the source-clustering layer
out of `BUILT · UNVALIDATED`.

### The line that matters

**"The mechanism is correct and deterministic" is verified (Tier 1) or tester-verified
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
PYTHONPATH="$PWD/src" python3 tests/test_psyche_store.py
```

The suites use a tiny built-in harness, **not** pytest: each prints `RESULT: N passed,
M failed` and exits non-zero on any failure. Do not run them under pytest: pytest would
collect the `test_*` functions but would not register a logical `check(...)` failure as a
failed assertion, so it could report green on a real failure. Run them as scripts (or via
`run_tests.py`).

### Real results

Captured verbatim in [docs/TEST_OUTPUT.txt](TEST_OUTPUT.txt). Every suite passes with
zero failures. These counts are mirrored in [`tools/ledger.json`](../tools/ledger.json), which is
the single source of truth; `tools/ledger_check.py` fails the build if any document disagrees
with it.

| Suite | Layer / role | Checks passed |
|---|---|---:|
| `test_psyche_store.py` | substrate store | **67** |
| `test_psyche_activation.py` | spreading activation | **102** |
| `test_psyche_coalitions.py` | coalition formation | **19** |
| `test_psyche_field.py` | multi-source field | **13** |
| `test_psyche_source_clustering.py` | source-clustering (1c) | **49** |
| `test_psyche_workspace.py` | workspace competition + pruning (1d-i) | **96** |
| `test_psyche_workspace_broadcast.py` | bounded broadcast + feedback (1d-ii) | **63** |
| `test_psyche_perceive.py` | perception + closed end-to-end cycle | **19** |
| `test_psyche_bodysensor.py` | body-state sensor + modulation hook (2c) | **49** |
| `test_psyche_credit.py` | temporal credit assignment + depression path (2f-i, 2g) | **133** |
| `test_tester_1c_adversarial.py` | tester: adversarial 1c | **73** |
| `test_tester_1c_mutation_battery.py` | tester: 1c randomized mutation battery | **5** |
| `test_tester_1d_i_adversarial.py` | tester: adversarial 1d-i | **107** |
| `test_tester_1d_ii_adversarial.py` | tester: adversarial 1d-ii | **110** |
| `test_tester_1e_selector_adversarial.py` | tester: 1e blind selector | **92** |
| `test_tester_1e_instrument_adversarial.py` | tester: 1e broadcast-Δ instrument | **76** |
| `test_tester_1e_loopclosed.py` | tester: 1e loop-closure | **58** |
| `test_tester_0b2_adversarial.py` | tester: adversarial 0b2 normalization overlay | **104** |
| `test_tester_0d_adversarial.py` | tester: adversarial 0d float-accumulation detector | **342** |
| `test_tester_0b2_reverify.py` | tester: independent 0b2 re-verification | **246** |
| `test_tester_0c_adversarial.py` | tester: adversarial 0c road ordering + fsum | **150** |
| `test_tester_2f_adversarial.py` | tester: adversarial 2f-i, 0e, 0g and 2g | **196** |
| `test_tester_2c_adversarial.py` | tester: adversarial 2c interoception | **350** |
| `test_harness.py` | experiment harness mechanism | **17** |
| `test_priming_instrument.py` | priming instrument mechanism | **42** |
| `test_priming_1e.py` | blind three-arm selector mechanism | **67** |
| **Total** | **26 suites** | **2,645 passed, 0 failed** |

That total is **2,645 assertions across 26 suites, 0 failures**, including the builder suites
above and the **independent tester-authored adversarial suites** (`test_tester_*`), which add
hostile and loop-closed checks: cross-process determinism in fresh interpreters under
`PYTHONHASHSEED ∈ {0,1,2,3,7,42}`, randomized mutation batteries interleaved with integrity
scans, no-divergence / no-lock-in stability of the broadcast write, and the resolved
over-swallow case now driven through the live cycle (formerly an asserted-negative limitation,
now a real pass).

**A passing count is not a verdict.** When `test_tester_0b2_adversarial.py` first ran (2026-07-25),
it had 83 passing checks and the tester's verdict on the brick it examines was **FAIL**: seven of
nine specified invariants held and two did not. Its three defects were recorded as *asserted
negatives* — checks that passed because the defect was present and were designed to turn red the
moment it was fixed, so that a fix had to come back through the same suite. The defects, their
scope, and which of them the change introduced versus inherited are recorded in
[docs/specs/SPEC-0b2-conserved-activation.md](specs/SPEC-0b2-conserved-activation.md) §6. All
three were later closed (DEFECT-A by brick 0c, the other two by follow-up fixes); those checks now
assert the fix, the suite now has 104, and a second, independent pass, `test_tester_0b2_reverify.py`,
returned **PASS** on all nine invariants on 2026-07-26 (§9 of the same spec). Read the verdict, not
the count.

**Determinism is scoped to the interpreters it was swept on.** A cross-process determinism
failure lived undetected in `Coalition.strength` for a month because the suite was only ever
run on one CPython minor version: float summation over a uuid4-keyed dict is
order-dependent, so two identical coalitions differed by one ULP and that resolved the
competition before the `creation_seq` tie-break could run. It was invisible on 3.12 and
flipped the winner 8 times in 30 on 3.11, at a *fixed* hash seed. Fixed with `math.fsum`;
see [docs/BUG-0b1-coalition-strength-determinism.md](BUG-0b1-coalition-strength-determinism.md).
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
| Source modules (`src/`) | 9 | — | — |
| Test suites in the canonical runner (`tests/` + `experiments/`) | 26 | — | — |
| **Python total** | **35** | — | — |

Line counts are deliberately not tabulated here any more: they were hand-maintained, they
went stale, and nothing depends on them. Run `wc -l src/*.py tests/*.py` for current figures.
Assertion counts, which *are* load-bearing, live in [`tools/ledger.json`](../tools/ledger.json)
and are checked against every document by `tools/ledger_check.py`.

---

## Project structure

```
psyche/
├── README.md               ← you are here
├── LICENSE                 ← MIT
├── requirements.txt        ← standard library only (no dependencies)
├── run_tests.py            ← runs all 26 suites with the correct absolute PYTHONPATH
├── src/                    ← the 9 modules
│   ├── psyche_store.py               substrate store (Layer 1): graph, IDs, decay, closure
│   ├── psyche_activation.py          deterministic spreading activation + flow
│   ├── psyche_field.py               multi-source activation field (basins)
│   ├── psyche_coalitions.py          coalition formation (flow-cut & by-basin)
│   ├── psyche_source_clustering.py   source-clustering pre-stage (group nearby sources)
│   ├── psyche_workspace.py           workspace: competition + pruning + bounded broadcast
│   ├── psyche_perceive.py            perception + the closed end-to-end cycle
│   ├── psyche_bodysensor.py          body-state sensor + default-off decay modulation (2c)
│   └── psyche_credit.py              temporal credit assignment + depression path (2f-i, 2g)
├── tests/                  ← the test suites (built-in harness; run as scripts)
│   ├── test_psyche_*.py              builder suites (one per module)
│   └── test_tester_*.py            independent tester-authored adversarial suites
├── experiments/            ← Tier 3 disciplined-exploratory scaffolding (its data-free mechanism suites are in run_tests.py; the data-dependent result scripts are not)
└── docs/
    ├── ARCHITECTURE.md         as-built technical reference
    ├── METHODOLOGY.md          the adversarial-testing development history
    ├── TEST_OUTPUT.txt         verbatim captured test run (the source of the numbers above)
    ├── psyche_roadmap.md         the living roadmap (current state, tiers, next step)
    ├── specs/                  ADRs / specs the architect writes for the builder
    ├── design/                 the original *aspirational* vision docs (see its README)
    └── diagrams/               Mermaid (.mmd) diagrams
```

The tree shows the repository before D-031, when this text was `README.md`.

---

## Background (conceptual inspiration, not implementation)

Psyche **borrows vocabulary and structure** from the following bodies of work. These are
*inspirations that shaped the design's framing*; Psyche does **not** implement, validate, or
reproduce any of these theories or their biological results, and makes **no claim of
biological fidelity**.

- **Complementary Learning Systems** (McClelland, O'Reilly): the fast/slow,
  experience-then-consolidate split that motivates separating *activation* (what lights up
  now) from *consolidation* (what later gets reinforced).
- **Synaptic consolidation research**: the framing behind treating
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

The correct verb throughout is *"inspired by"* / *"borrows the framing of"*: never
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

## About this page

This page was the repository README until 2026-10-23. It is kept intact apart from these edits:
the title names the stage; the opening banner is new, and this note moved here from it; the
section "What this is" is reworded for the project's stage structure, with its claims unchanged;
links are repointed for the new location; wording is edited under the public writing rules;
figures that had gone stale or were wrong are corrected (the source-module count, now matching
`src/`; the suite count, now matching [tools/ledger.json](../tools/ledger.json); the file total
that follows from those two; and the BUG-0b1 flip count and interpreter, now matching [the
BUG-0b1 record](BUG-0b1-coalition-strength-determinism.md) section 1); one module is added to
the project tree and one wrong tree label is corrected; and a later-record note follows the open
defect, with another note under the project tree; and the word "proven" is replaced by "verified"
in prose, with the ledger's status name `PROVEN` explained where the tiers are set out.

---

## License

MIT: see [LICENSE](../LICENSE). Copyright (c) 2026 Cagan Caliskan.
