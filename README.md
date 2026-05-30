# Nous

A **biologically-motivated, dependency-free Python prototype** of a memory-and-activation
substrate for a cognitive architecture. Nous implements, with no third-party
dependencies, four layers: (1) a graph **substrate store** of concept *nodes* and weighted
*roads* with synaptic-tagging/consolidation-*inspired* dynamics, lazy activity-dependent
decay, and "sticky" closure of traumatic edges; (2) a deterministic **spreading-activation**
engine that records per-edge flow and treats closed roads as *leaky-not-inert* (an
intrusive-recall-like breakthrough); (3) a multi-source activation **field** that assigns
each node to the source that activates it most; and (4) a first end-to-end **slice** —
*perceive → activate → form coalitions → select a thought*. The lower two layers are
rigorously tested for determinism, integrity, and purity. The upper two are exploratory:
they run, they are deterministic, but their *cognitive meaningfulness is not claimed*.

---

## What this is (and how to read it)

Nous is **an engineering prototype and a software-testing-methodology case study**. It is
suitable as a technical-report artifact: a small, self-contained system built
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

## Scope: what is proven vs. what is exploratory

**Proven (by the test suites):** the substrate store and the spreading-activation engine are
verified for three properties:

- **Determinism** — identical results across process runs, including under randomized hash
  seeds (`PYTHONHASHSEED`) checked in fresh subprocesses. This matters because the natural
  implementations leak set-iteration order (over uuid4 keys) into results.
- **Integrity** — the graph's indices, adjacency, dedup, and designations stay mutually
  consistent across every mutation; a full-graph scan finds no drift.
- **Purity** — reads never mutate stored state. Lazy time-decay is computed as a read-only
  *view*; only writes persist it. (This is load-bearing: a read that silently re-opened a
  "closed" traumatic edge would corrupt state over time. A test asserts it cannot.)

These are claims about **mechanism**: the code does exactly and only what it says,
reproducibly.

**Exploratory (runs, but cognitive meaning not claimed):** coalition formation (grouping
co-activated nodes), the multi-source field, and the end-to-end "thought" slice. They are
deterministic and tested for *mechanics* (they run end-to-end, they are pure, they are
reproducible), but **whether the resulting "thought" is cognitively meaningful is not
established.** In fact, on clustered real input the slice currently produces an *incoherent*
"thought" — and that failure is asserted as a **known-limitation test** (see below), so it is
documented rather than hidden, and will flip to green only if/when the underlying problem is
solved. Picking the single strongest coalition as "the thought" is an explicit **placeholder**
for a workspace-competition (broadcast) phase that does not yet exist.

The distinction to keep throughout: **"the mechanism is correct and deterministic" is proven;
"the mechanism reproduces a cognitive phenomenon" is future work.**

---

## Running the tests

Pure standard library — nothing to install (Python 3.8+; developed and captured on CPython
3.13).

```bash
# all five suites, with the correct PYTHONPATH handled for you:
python3 run_tests.py

# or a single suite directly (absolute PYTHONPATH so the determinism subprocess
# probes resolve their imports regardless of working directory):
PYTHONPATH="$PWD/src" python3 tests/test_nous_store.py
```

The suites use a tiny built-in harness, **not** pytest: each prints `RESULT: N passed,
M failed` and exits non-zero on any failure. Do not run them under pytest — pytest would
collect the `test_*` functions but would not register a logical `check(...)` failure as a
failed assertion, so it could report green on a real failure. Run them as scripts (or via
`run_tests.py`).

### Real results

Captured verbatim in [docs/TEST_OUTPUT.txt](docs/TEST_OUTPUT.txt) (CPython 3.13). Every
suite passes with zero failures:

| Suite | Layer | Checks passed |
|---|---|---:|
| `test_nous_store.py` | substrate store | **45** |
| `test_nous_activation.py` | spreading activation | **35** |
| `test_nous_coalitions.py` | coalition formation | **19** |
| `test_nous_field.py` | multi-source field | **13** |
| `test_nous_perceive.py` | perception + end-to-end slice | **18** |
| **Total** | | **130 passed, 0 failed** |

That total is **130 assertions executed across 56 test functions** — including adversarial
cross-process determinism checks (run in fresh interpreters under
`PYTHONHASHSEED ∈ {0,1,2,3,7,42,123,999}`) and one explicitly-asserted *known limitation*
(`test_KNOWN_LIMITATION_clustered_sources_give_poor_basins`).

---

## Project size (measured)

| | Files | Lines (`wc -l`) | Non-blank, non-comment |
|---|---:|---:|---:|
| Source modules (`src/`) | 5 | 1,476 | 1,058 |
| Test suites (`tests/`) | 5 | 1,555 | 1,223 |
| **Python total** | **10** | **3,031** | **2,281** |

Per module (`wc -l`): `nous_store.py` 548 · `nous_activation.py` 281 ·
`nous_coalitions.py` 324 · `nous_field.py` 161 · `nous_perceive.py` 162.

---

## Project structure

```
nous/
├── README.md               ← you are here
├── LICENSE                 ← MIT
├── requirements.txt        ← standard library only (no dependencies)
├── run_tests.py            ← runs all 5 suites with the correct absolute PYTHONPATH
├── src/                    ← the 5 modules
│   ├── nous_store.py           substrate store (Layer 1): graph, IDs, decay, closure
│   ├── nous_activation.py      deterministic spreading activation + flow
│   ├── nous_field.py           multi-source activation field (basins)
│   ├── nous_coalitions.py      coalition formation (flow-cut & by-basin)
│   └── nous_perceive.py        perception + the end-to-end "thought" slice
├── tests/                  ← the 5 test suites (built-in harness; run as scripts)
└── docs/
    ├── ARCHITECTURE.md         as-built technical reference
    ├── METHODOLOGY.md          the adversarial-testing development history (six bugs)
    ├── TEST_OUTPUT.txt         verbatim captured test run (the source of the numbers above)
    ├── design/                 the original *aspirational* vision docs (see its README)
    └── diagrams/               Mermaid (.mmd) diagrams
```

---

## Background (conceptual inspiration — not implementation)

Nous **borrows vocabulary and structure** from the following bodies of work. These are
*inspirations that shaped the design's framing*; Nous does **not** implement, validate, or
reproduce any of these theories or their biological results, and makes **no claim of
biological fidelity**.

- **Complementary Learning Systems** (McClelland, O'Reilly) — the fast/slow,
  experience-then-consolidate split that motivates separating *activation* (what lights up
  now) from *consolidation* (what later gets reinforced).
- **Synaptic Tagging and Capture** (Frey, Morris) — the framing behind treating
  reinforcement as a *gated, budgeted* event, which is why spreading activation here is a
  pure read and never strengthens what it touches.
- **Global Workspace Theory** (Baars, Dehaene) — the source of the *coalitions compete, one
  is broadcast* vocabulary. Only coalition *formation* exists here; the broadcast/competition
  step is an acknowledged placeholder.
- **LIDA cognitive cycle** — the *perceive → attend → broadcast* staging the end-to-end slice
  is loosely shaped after.
- **Yerkes–Dodson** (arousal / inverted-U) — appears in the design notes as motivation for
  emotionally-modulated plasticity; in the code this shows up only as charge-modulated
  strengthening, and is best read as design-level aspiration rather than a realized model.

The honest verb throughout is *"inspired by"* / *"borrows the framing of"* — never
*"implements"* or *"models"* in any validated sense.

---

## Limitations & future work

- **Cognitive meaningfulness above the substrate is unestablished.** The coalition/field/
  thought layers are deterministic and pure, but there is no evidence the "thought" they
  produce is meaningful. The single asserted known-limitation test documents one concrete
  failure: when real perception lights up several nodes in the *same* domain, basins collapse
  — one source over-swallows across domains while same-domain siblings strand as singletons.
- **"Strongest coalition = the thought" is a placeholder** for a workspace-competition
  (broadcast) phase that has not been built.
- **Several constants are uncalibrated guesses on probation** — notably the closed-road
  breakthrough threshold/leak fraction and the coalition flow-cut fraction. The tests pin the
  *qualitative* regime (closed roads block weak cues and leak strong ones; weak flow edges are
  cut), never the magnitudes. Nothing downstream may depend on these numbers.
- **Perception is exact/substring token matching** — no embeddings, no fuzzy semantics. It is
  the minimal step that makes activation sources *input-derived* rather than hand-placed.
- **Backward spread is not implemented** — activation follows directed out-roads only (v1).

**The natural next step** is to stop validating the cognitive layer against hand-built inputs
and instead validate it against a *measurable cognitive effect* — for example **semantic
priming** (does pre-activating a related concept measurably speed/raise the activation of a
target?), where the expected direction of the effect is known independently of Nous.

---

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Cagan Caliskan.
