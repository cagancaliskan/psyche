# PAPER CLAIM INVENTORY — Nous (experience-report paper)

**Status:** **LOCKED honesty contract as of 2026-06-21.** PM-authored reference artifact. This is **not** the
paper. It is the paper's **honesty contract**: *if a claim is not in Section 1 with evidence and an assurance
tier, it may not appear in the paper.* Human decisions folded in: **D1 (Phase 0 count) — done**; **D2 (seed
phrasing) — done**; **D4 (.claude tracking) — done**; **D3 (citations) — done** (citation-verification pass
completed 2026-06-21; freeze lifted; all 9 priority references independently confirmed at source — see Section 5).

**Authored by:** architect-pm · **Date:** 2026-06-21 · **Against:** `CLAUDE.md`, `docs/nous_roadmap.md`,
`docs/METHODOLOGY.md`, all `docs/specs/**`, all `docs/experiments/**`, `docs/TEST_OUTPUT.txt`, and `git log`.

**Paper frame (decided, not re-litigated here):** a software-engineering / methodology **experience report**.
The central contribution is the **verification methodology** (four-agent build/break-mechanism/break-meaning/plan
separation; loop-closure; adversarial + property-based testing; pre-registration; anti-circularity gates). Nous
is the **case study**. The three structurally-distinct meaning-bar NOT-YETs are the **empirical evidence the
methodology works** — it caught false-meaning claims before any wasted graded run.

**Ground-truth rule:** all test counts in this document are read verbatim from `docs/TEST_OUTPUT.txt`. Where a
count is not in that file, it is flagged, not invented.

**Assurance tiers (held in separate boxes at all times):**
- **PROVEN** — verified against hard properties (determinism across process hash seeds, integrity, purity) or an
  external yardstick.
- **MECHANISM-VERIFIED** (`BUILT · UNVALIDATED`) — the mechanism runs, is deterministic/integrity-preserving/pure,
  and was independently and adversarially re-verified by the tester; **no meaning/cognitive claim**.
- **METHODOLOGY** — a claim about the *process* (roles, gates, discipline), evidenced by artifacts and history.
- **NOT-YET (UNVALIDATED)** — a meaning-bar attempt that was attempted and honestly recorded as not earned, with
  a precise structural reason; no graded number was manufactured.

---

# SECTION 1 — WHAT WE CAN CLAIM

## 1.A PROVEN claims (Phase 0: substrate + activation) — tier **PROVEN**

> Canonical run (whole suite, all tiers): **20 suites, 1,372 assertions, 0 failures** (`docs/TEST_OUTPUT.txt`,
> `OVERALL: all 20 suites passed`). The 1,372 figure is the sum of the per-suite `RESULT:` lines; it is verified
> by summation here and matches the roadmap's headline. (TEST_OUTPUT.txt prints per-suite passed counts and the
> suite total, but does **not** print a single "1,372" line — the total is the arithmetic sum, confirmed.)

**P0-1. The substrate store is deterministic, integrity-preserving, and pure.** — **PROVEN**
The graph store (`src/nous_store.py`) splits decay into a pure view and a persisting write; reads never mutate
stored state; closure is sticky (time + repeated reads do not reopen a closed road); deletion leaves no dangling
index entries; the integrity scan passes on healthy and adversarial graphs.
- Evidence: `tests/test_nous_store.py` — **45 passed, 0 failed** (TEST_OUTPUT.txt). Named properties include
  "reads do not mutate stored state," "lazy decay … stored state untouched," "closure is sticky," "deletion is
  complete: no dangling index entries; integrity holds," "integrity scan passes on a healthy graph."

**P0-2. The spreading-activation engine is deterministic across process hash seeds, and pure.** — **PROVEN**
Bounded single-expansion, hop-layered, per-layer frozen values; convergence sums without double-counting; a
cycle terminates; reads are pure.
- Evidence: `tests/test_nous_activation.py` — **35 passed, 0 failed** (TEST_OUTPUT.txt). Cross-process
  determinism is verified in fresh interpreters under **5 PYTHONHASHSEED values: `{0,1,3,7,42}`**
  (`test_determinism_with_same_hop_edge_adversarial`, confirmed in the test source). Named properties include
  "post-convergence activation is DETERMINISTIC, not order-dependent," "spreading activation mutates NOTHING in
  the store (pure read)."

**P0-3. The determinism property is established across process hash seeds for every layer that makes a
cross-process claim — but the *number of seeds is not uniform.*** — **PROVEN** (with the precision below)
- **LOCKED standing phrasing (human decision, 2026-06-21).** Every determinism claim in the paper uses exactly:
  **"randomized process hash seeds (5–8 per suite, in fresh interpreters)."** Never "6 seeds" uniformly, and never
  any single fixed number applied across the whole repo.
- The real per-suite seed counts are kept where precision matters: activation: **5 seeds** `{0,1,3,7,42}`;
  coalitions: **8 seeds** `{0,1,2,3,7,42,123,999}`; field: **8 seeds** `{0,1,2,3,7,42,123,999}`; end-to-end
  perceive slice: **6 seeds** `{0,1,2,7,42,999}`; the 1c/1d/2c tester suites: **6 seeds** (TEST_OUTPUT.txt phrasing
  "across 6 hash seeds … fresh interpreters/processes").
- **Precision the paper must keep:** the phrase "determinism across 6 hash seeds" is accurate for the
  1c/1d/2c/slice suites; it is **not** uniform across the whole repo (Phase 0 activation uses 5; coalitions/field
  use 8). The paper says **"across randomized process hash seeds (5–8 per suite, in fresh interpreters)"** (the
  locked wording above) rather than assert one fixed number everywhere.
- Evidence: the four determinism tests named in `docs/METHODOLOGY.md` and confirmed in the test sources
  (`tests/test_nous_activation.py`, `tests/test_nous_coalitions.py`, `tests/test_nous_field.py`,
  `tests/test_nous_perceive.py`).

<!-- ledger:allow-count -->
> **RESOLVED (human decision, 2026-06-21) — Phase 0 scope vs. roadmap "Done means" line.** The roadmap's Phase 0
> "Done means" line (`docs/nous_roadmap.md` line 65) reads: *"130 assertions, 56 test functions, five suites, all
> passing."* The **current** TEST_OUTPUT.txt has no "five suites / 130 assertions" Phase-0 grouping; the two
> indisputably Phase-0 suites (`test_nous_store.py` = 45, `test_nous_activation.py` = 35) sum to 80.
> **Decision:** the **present-day canonical Phase 0 figure is store (45) + activation (35) = 80 assertions in the
> canonical run.** The "130 assertions / 56 test functions / 5 suites" figure may be cited **only** as an
> explicitly-labelled **historical snapshot from Phase 0's completion moment** — consistent with how the roadmap
> labels superseded figures — **never** as the current count. The paper therefore cites Phase 0 as **45 + 35 = 80
> assertions** in the current canonical run; any use of 130/56/5 must carry the "Phase-0-completion historical
> snapshot" label.

**Honest scope of the PROVEN tier:** "PROVEN" means *correct, deterministic, integrity-preserving, pure* — a
**mechanism** guarantee. It is **not** a cognitive claim. Phase 0 is the project's shippable, citable artifact.

---

## 1.B TESTER-VERIFIED MECHANISM claims — tier **MECHANISM-VERIFIED** (`BUILT · UNVALIDATED`)

> Each of these was built by the builder and **independently, adversarially re-verified by a separate tester**
> who wrote their own hostile and loop-closed suites (`test_tester_*`). Every claim below is a claim about a
> **deterministic, integrity-preserving, pure mechanism** — explicitly **not** a claim that it reproduces a
> cognitive phenomenon.

**M-1. Source-clustering (1c) is a deterministic, pure, integrity-preserving pre-stage that merges nearby
perceived sources through the live loop.** — **MECHANISM-VERIFIED**
- What was verified: on real perceived input through the closed loop, (a) `coffee/kitchen/morning` merge into one
  group and (b) no perceived source strands as a singleton; **hand-placed groupings fail the property** (so it is
  not trivially true); scale-invariance; cross-process determinism on randomly-generated hostile graphs; purity;
  integrity unchanged before/after.
- Evidence: builder suite `tests/test_nous_source_clustering.py` — **49 passed, 0 failed**; tester suite
  `tests/test_tester_1c_adversarial.py` — **73 passed, 0 failed**; tester mutation battery
  `tests/test_tester_1c_mutation_battery.py` — **5 passed, 0 failed** (TEST_OUTPUT.txt). Spec:
  `docs/specs/SPEC-1c-source-clustering.md`. Commit `e4169f9`.
- Explicit non-claim (shipped as asserted-negatives in the suite): "grouping is topological only — no cognitive
  claim"; "1c does NOT broadcast/feed back"; "the relative threshold is an uncalibrated design constant."

**M-2. Workspace competition + over-swallow pruning (1d-i) deterministically selects exactly one winner and prunes
the bridged, unperceived domain — through the live loop, as a pure read.** — **MECHANISM-VERIFIED**
- What was verified: exactly one winner selected deterministically; the over-swallow asserted-negative inherited
  from 1c is **flipped to a real pass** (the bridged unperceived `work`/`code` domain is excluded); the raw
  pre-prune winner genuinely *contained* that domain (so the flip is pruning's doing, not absence);
  anti-overcorrection (a *named* domain is never pruned); the flip **generalizes on a second, independently-built
  isomorphic-but-relabelled graph** (not tuned to coffee/work); deterministic across 6 hash seeds; selection is a
  pure read.
- Evidence: builder suite `tests/test_nous_workspace.py` — **83 passed, 0 failed**; tester suite
  `tests/test_tester_1d_i_adversarial.py` — **107 passed, 0 failed** (TEST_OUTPUT.txt). Spec:
  `docs/specs/SPEC-1d-workspace-broadcast.md`. Commit `2fd878b`.
- Honest known-limitation (shipped as an asserted-negative, not hidden): the realized rule is a **parameter-free
  cohesion-valley / relative-attachment watershed**, not literal domain-membership; an unnamed domain bridged
  **≥ its own internal cohesion** has no valley and is **kept**, so over-swallow can recur in that specific
  topology. The divergence is always **safe-direction** (over-includes an unnamed domain, never over-prunes a
  perceived member). Accepted as intended design (human decision, 2026-06-20); SPEC-1d §3.2 / §7 item 8; tester
  adjudication checks T12c/T12d/T12e in `tests/test_tester_1d_i_adversarial.py`.

**M-3. Bounded broadcast + feedback (1d-ii) is the single explicit write that closes the loop, proven bounded both
ways (no divergence; no lock-in).** — **MECHANISM-VERIFIED**
- What was verified: the broadcast is a **single explicit write** changing exactly the winner's internal roads
  (once each, no new road, nodes stay neutral); the `broadcast=False` path is byte-identical (pure read);
  **no divergence** (road strength ≤ 1.0, the aggregate plateaus, per-cycle deltas → ~0; boundedness is
  **structural** from `strengthen()`'s `(1−strength)` saturation, with **no clamp/cap/tunable magnitude** added —
  asserted by a code-body audit); **no lock-in** (escape proven **non-vacuously** after **80** reinforcing cycles
  on a hostile bridged graph, A verified dominant immediately before the switch; mirror test; freeze probe;
  close-competition differential control); deterministic + integrity-preserving under the write across 6 hash
  seeds.
- Evidence: builder suite `tests/test_nous_workspace_broadcast.py` — **63 passed, 0 failed**; tester suite
  `tests/test_tester_1d_ii_adversarial.py` — **110 passed, 0 failed** (TEST_OUTPUT.txt). Spec:
  `docs/specs/SPEC-1d-workspace-broadcast.md`. Commit `e4df7df`.
- Explicit non-claim: closing an information loop with bounded feedback is **not** priming, awareness, or a
  consciousness result; the broadcast magnitude is the **uncalibrated** default gain from `strengthen()`.

**M-4. The cognitive cycle closes end-to-end as a mechanism.** — **MECHANISM-VERIFIED**
- Claim: perceive → activate → cluster → compete → prune → broadcast → next cycle runs end-to-end on real input,
  deterministically, and the end-to-end slice is a pure read across hash seeds.
- Evidence: `tests/test_nous_perceive.py` — **19 passed, 0 failed** (end-to-end slice, determinism across 6 hash
  seeds, pure read); plus M-1/M-2/M-3 above. `docs/METHODOLOGY.md` findings (g)/(h).
- Explicit non-claim: "closes end-to-end" is a **mechanism** statement only. No external-data cognitive claim is
  made by 1c or 1d, so **1c and 1d are `BUILT · UNVALIDATED`**.

**M-5. Interoception (2c): a `BodySensor` derives a `friction` scalar from real machine telemetry and modulates
`decay_per_hop`, default-OFF, as a deterministic (in replay), pure, integrity-preserving mechanism with an
anti-circular causal readout.** — **MECHANISM-VERIFIED**
- What was verified (tester verdict PASS, **350 adversarial assertions**): with interoception **off**, `think()`
  is **byte-identical** to the pre-2c path (default-off byte-identity under attack); **replay determinism across
  6 PYTHONHASHSEED in fresh processes** over a frozen, hashed trace; **live telemetry proven off the deterministic
  test surface** (timers monkeypatched to detonate; static check that `perf_counter`/`process_time` appear only in
  the live branch); the **anti-circularity winner-flip-not-echo guard** — two distinct friction values mapping to
  the same effective decay produce the **same** winner, every winner element is a real `NodeID` (never the injected
  float), friction names no node; integrity + purity on the ON path.
- Evidence: builder suite `tests/test_nous_bodysensor.py` — **49 passed, 0 failed**; tester suite
  `tests/test_tester_2c_adversarial.py` — **350 passed, 0 failed** (TEST_OUTPUT.txt). Module
  `src/nous_bodysensor.py`. Spec `docs/specs/SPEC-2c-interoception.md`. Commit `462c82a`.
- **Feasibility (NOT meaning):** the populability pilot returned **GO, 85% (34/40 winner-flips)**, independently
  re-derived by the tester; **not 100% — 6 genuine non-flips rule out a rigged battery**. This is a **feasibility**
  number — the flip rate on flip-capable, contested-by-design inputs over a deliberately-extreme telemetry range —
  **not a meaning result.** Evidence: tester suite checks E1–E5/F1–F3/G1–G3/H1–H3.
- Explicit non-claim (shipped as asserted-negatives): no public name encodes a feeling/emotion/awareness/
  consciousness claim (headline word is "friction"); the suite proves a **real causal effect (winner-flip) and
  determinism only** — it does **not** establish the flip tracks telemetry in a pre-registered direction or that
  it means anything (that is the validator's graded run).

> **Note on the 2c capture-script and its battery (parked).** `experiments/exp2c_capture.py` and its
> tester-verified realistic battery are **parked, uncommitted** (stimulus construction for a graded run that is
> not happening). They are **not** in the canonical count (the count stays 20 suites / 1,372). The paper must not
> count them. (They appear as untracked files in `git status`.)

---

## 1.C METHODOLOGY claims — tier **METHODOLOGY**

**MM-1. A four-agent separation of duties governs the work: build / break-mechanism / break-meaning / plan.** —
**METHODOLOGY**
- Claim: an architect-pm specs and plans; a builder implements test-first; a separate tester independently and
  adversarially re-verifies *mechanism*, writing its own hostile + loop-closed suites and never modifying
  production code; a validator (when a cognitive claim is in play) verifies *meaning* against external data with a
  pre-registered prediction. Agents do not cross lanes.
- Evidence: `CLAUDE.md` ("How the agents work together"); the existence of independent tester suites
  (`tests/test_tester_*`) distinct from builder suites; `docs/METHODOLOGY.md` §"The same discipline, carried into
  the cognitive cycle" (records the role split as a process fact). Honest scope: this is a **demonstrated process**,
  not a controlled experiment in software engineering (see Section 4).

**MM-2. Loop-closure (driving each stage with system-generated, not hand-placed, input) caught structural bugs
that happy-path tests would have passed.** — **METHODOLOGY**
- Evidence: `docs/METHODOLOGY.md` findings (a)–(f), each traced to a named test in `src/`/`tests/`; finding (f)
  is loop-closure applied to the whole pipeline; the over-swallow asserted-negative was **flipped through the live
  loop** by 1c+1d-i (findings (g)/(h)), not edited away.

**MM-3. The six structural bugs the discipline caught (enumerated).** — **METHODOLOGY**
(From `docs/METHODOLOGY.md` §"The six structural findings"; each is a *structural* bug — a bug in the shape of the
algorithm — with a named locking test. Magnitudes of error are deliberately omitted by the methodology doc where
the shipped artifact cannot reproduce them; the paper should keep that restraint.)
- **(a) Read-as-write:** decay applied on access wrote back, so reads mutated state and could let a closed road
  drift open. Fixed by splitting decay into a pure view + a persisting write; closure made sticky. Locked by
  `test_reads_are_pure`, `test_lazy_decay`, `test_closure_is_sticky`.
- **(b) Convergence double-counting:** importing Dijkstra "first-pop-final" intuition where activation *sums*.
  Fixed by bounded single-expansion, hop-layered. Locked by `test_no_double_count_downstream_of_convergence`,
  `test_convergent_activation_sums`.
- **(c) Order-dependence → nondeterminism:** a best-first frontier + iterating a `set` of uuid4 keys made results
  swing across process hash seeds. Fixed by hop-layered expansion with per-layer frozen values. Locked by
  `test_expansion_is_deterministic_under_edge_strength`, `test_determinism_with_same_hop_edge_adversarial`.
- **(d) Identity/order leak:** tie-breaking on uuid4 (regenerated every run) → nondeterministic ordering. Fixed by
  tie-breaking on the stable `creation_seq`. Locked by `test_determinism_adversarial_across_hash_seeds`,
  `test_representative_is_most_active_deterministically`.
- **(e) Binding degeneracy:** connected-components on a graph connected by construction always yields one
  component; flow-magnitude cutting keys off distance, not community. Fixed by reframing to a multi-source field.
  Locked by `test_single_seed_spread_yields_multiple_coalitions`,
  `test_acceptance_multisource_recovers_communities`.
- **(f) Circular validation:** the answer was hand-encoded in the input (sources hand-placed; the field
  acceptance test recovered two communities only because one source was hand-placed per community). Fixed by
  closing the loop (`nous_perceive.py`) so input is system-derived. Locked, *as a limitation*, by
  `test_KNOWN_LIMITATION_clustered_sources_give_poor_basins` (an asserted-negative written to flip green only when
  source-grouping was actually fixed — since flipped; see M-1/M-2).
- Evidence: `docs/METHODOLOGY.md` §(a)–(f).

**MM-4. Pre-registration + anti-circularity gates are applied before any graded number is computed.** —
**METHODOLOGY**
- Evidence: frozen pre-registrations `docs/experiments/EXP-1c-swow-recovery.md`, `EXP-1e-priming.md`,
  `EXP-2c-interoception.md`, each with an explicit anti-tamper notice and SHA-256-frozen artifacts; the 1e blind
  selection run (commit `dc07477`, `SELECTION_SEED=20260621`, topology-only, no activation) emitted stimulus
  lists + counts only; the deferred-hash discipline (artifacts hashed before any graded outcome exists).

**MM-5. The discipline caught three meaning-bar attempts as honest obstacles BEFORE any graded run.** —
**METHODOLOGY** (this is the paper's load-bearing empirical evidence; the three are detailed in 1.D.)
- Evidence: 1e NO-GO (commit `9b96b97`), fan-effect NO-GO (commit `79260fa`), 2c timing-pair NOT-YET (commit
  `1faf517`). In each case **no graded number was manufactured.**

> **Honest scope of the METHODOLOGY tier (state in the paper).** These claims are evidenced by the project's own
> artifacts and history on **one** project. They are not validated across many projects, and "caught the bug" is a
> demonstrated instance, not a guaranteed property (Section 4).

---

## 1.D The three NOT-YET findings — tier **NOT-YET (UNVALIDATED)**

> Each is a meaning-bar attempt with a **precise structural reason**, recorded honestly with no graded number
> manufactured. The phrasings below are corrected against the source docs where the user's brief differed; the
> corrections are flagged at the end of this section.

**NY-1. Semantic priming (1e): NO-GO — circular (the prediction variable *is* the edge weight).** —
**NOT-YET (UNVALIDATED)**
- Precise structural reason (from EXP-1e §15 / SPEC-1e §14 / roadmap 1e block): SWOW R123.Strength **is** encoded
  as the edge weight, so the anti-circularity gate — a **weight-blind leverage stratum S0** (pairs where the
  HIGH and LOW bands carry **equal** integer weight, `W_gap = 0`, *and* are in-degree-matched) — cannot be
  populated. On the coarse saturating weight ladder `W = min(10, 1 + floor(strength·100))`, a prime's HIGH band
  almost always outweighs its LOW band, so weight-blind pairs are rare: **N_S0 = 7 < 30** (with N_S+ = 296). The
  pre-registered fallback `V = r_MA − r_W ≥ 0.20` is **arithmetically unreachable**: S+ dominance gives
  `r_W ≈ 0.97`, so `V ≥ 0.20` would require `r_MA ≥ ~1.17 > 1.0` (rank-biserial caps at 1.0).
- Why inevitable: a HIGH > LOW result would be the weight map read straight back out — uninterpretable. The gate
  exists precisely to prevent that, and the corpus's own weight structure forecloses it **before any activation**.
- What was actually run: the committed, tester-verified §10 selector was run **blind** (topology + R123.Strength
  only, no activation) on the full SWOW graph (**1,388,741 directed edges, 133,763 nodes**); it emits stimulus
  lists + structural counts only — **no `think()`, no activation, no Δ, no effect size computed.**
- Honest finding (does NOT claim priming is absent): *a spreading-activation substrate whose edge weights encode
  SWOW strength cannot, on this corpus, with both the edge-weight and target-popularity mechanical paths
  controlled, separate genuine priming-through-the-loop from its own weight map.*
- Evidence: `docs/specs/SPEC-1e-priming.md` §14; `docs/experiments/EXP-1e-priming.md` §15; verbatim selector
  stdout `experiments/results/priming_1e_selection_output.txt`; selector + instrument suites in TEST_OUTPUT.txt
  (`test_tester_1e_selector_adversarial.py` = 92, `test_tester_1e_instrument_adversarial.py` = 76,
  `test_tester_1e_loopclosed.py` = 58, `test_priming_1e.py` = 67, `test_priming_instrument.py` = 42,
  `test_harness.py` = 17). Commit `9b96b97`.

**NY-2. Fan effect (Anderson): NO-GO — the generating mechanism is absent (no out-degree / shared-budget
normalization).** — **NOT-YET (UNVALIDATED)**
- Precise structural reason (from `docs/specs/SPEC-fan-effect.md`): the fan effect is, mechanistically, a
  **shared-budget / normalization** effect — ACT-R divides a *conserved* source activation across its
  associations (`S_ji ≈ S − ln(fan)`). **This engine has no such conservation.** In `spread_activation`
  (`src/nous_activation.py`), each out-road receives the source's **full** activation (`outgoing = node_act`, then
  `transmitted = outgoing × road.strength × decay_per_hop`) with **no `/ len(out_roads)`**. Consequently the
  Phase 2A fan sweep is **flat to the last digit**: target activation `0.2433743975`, identical (spread 0.0)
  across fan ∈ {1,2,4,8,16}. The closed loop inherits the flat response (1d-i competition normalizes by
  **coalition size**, not source out-degree; 1d-ii broadcast has **no out-degree term**).
- Why inevitable / how it differs from 1e: the fan effect **escapes** 1e's strength=weight coupling (fan rides on
  out-degree, a distinct axis) — but unlike 1e (where a mechanical readback *predicted the right direction*),
  here there is **no fan-dependent signal at all** to grade, in either direction. Re-running would re-measure
  flat.
- The engine-change path (adding source-activation / out-degree normalization) is held as a **separate, later,
  explicitly-framed architecture decision, NOT a meaning-bar rescue** — it would change the meaning of every
  prior activation result (forcing re-validation of 1c/1d), and adopting it *to produce* the effect would not
  earn it.
- Evidence: `docs/specs/SPEC-fan-effect.md`; verbatim flat-curve output `experiments/results/fan_effect_output.txt`;
  characterization harness `experiments/fan_effect.py` (tier: disciplined-exploratory). Commit `79260fa`.

**NY-3. Interoception timing-pair (2c): NOT-YET — the signal is flat on a realistic CPU-bound workload (the
contention-tracking meaning claim is structurally unsupported on this substrate with this signal).** —
**NOT-YET (UNVALIDATED)**
- Precise structural reason (from EXP-2c §6.1/§6.1.1, verified against `src/nous_activation.py` /
  `src/nous_bodysensor.py`): `friction = clamp(1 − cpu_dt/wall_dt, 0, 1)` is a **stall fraction** that rises only
  when the process is **off-CPU**. A realistic `think()` is single-threaded, in-memory, pure compute with no I/O
  and no blocking, so `wall ≈ cpu → friction ≈ 0`; it is **scale-invariant** (a ratio: heavier work moves
  duration, not the cpu/wall ratio); CPython GC runs **in-thread** (counted as CPU — a GC pass makes `think()`
  slower but keeps `wall ≈ cpu`, so friction does not rise); a KB-scale substrate never swaps; preemption is
  rare/brief on an unloaded machine. So real friction carries **no real-contention variation** on a realistic
  workload.
- Why inevitable: the only gradable band would be a **manufactured** one (injected `sleep`, GB-scale allocations
  to force swap, or saturating every core) — forbidden by the anti-manufacture guard. The as-written realistic
  capture's band (`[0.79 .. 0.93]`, mean ≈ 0.86) was **yield-dominated, not contention-tracking** (set by an
  injected 0.5 ms sleep-to-work ratio); EXP-2c §6.1's earlier "real contention during real work" wording was
  **corrected as false** before any graded number, and the §6.4 contention-trace freeze is **HELD**.
- **CRITICAL framing (state in the paper): this is NOT a mechanism defect.** The `BodySensor` + default-off hook
  and the 85% couplability stay **tester-PASS** — the loop genuinely *can* be moved by friction. What is dead is
  the chosen signal's real-contention content (a flat external yardstick, not a wall in the loop). **2c stays
  `BUILT · UNVALIDATED`.**
- Open future path (NOT attempted, NOT a quick swap): **option 2** — re-spec the body-state signal to one that
  genuinely varies on a realistic, dependency-free workload — held open, must earn its own feasibility pre-check.
  Recorded caveats: RSS-growth is real but **monotonic** and **correlates with the graph size that drives
  competition** (a fresh circularity risk); `getloadavg` is flat when idle / non-reproducible under external load
  (breaks the determinism guard).
- Evidence: `docs/experiments/EXP-2c-interoception.md` §6.1/§6.1.1; `docs/specs/SPEC-2c-interoception.md` (header
  `BUILT · UNVALIDATED`); roadmap 2c block + meta-finding. Commits `a9e2f6e` (prose direction fix),
  `1faf517` (NOT-YET recorded), `b474b8f` (meta-finding), `656d6c2` (parked-work revert).

> **CORRECTIONS / CONFIRMATIONS against the user's brief (follow-the-docs rule).**
> - The user's NY-1 phrasing ("circular, strength = edge weight") is **confirmed exact** by the docs.
> - The user's NY-2 phrasing ("mechanism absent, no out-degree normalization") is **confirmed exact**; the docs
>   add the precise mechanism (ACT-R `S_ji ≈ S − ln(fan)` conservation) and the verbatim flat value
>   `0.2433743975`.
> - The user's NY-3 phrasing ("signal flat, friction invariant on CPU-bound work") is **confirmed exact**; the
>   docs add the precise reason it is invariant (stall fraction + scale-invariance + in-thread GC + no I/O + no
>   swap) and that the prior provenance wording was corrected as false. The paper should use "NOT-YET" for 2c
>   (the docs' word), reserving "NO-GO" for 1e and the fan effect.

---

## 1.E The META-FINDING — tier **NOT-YET (UNVALIDATED)** synthesis / **METHODOLOGY** evidence

**MF-1. The recurring wall is the external meaning yardstick, not the mechanism.** — **METHODOLOGY** (synthesis
over three NOT-YETs)
- Statement (from roadmap top status + Phase-1 META-FINDING block + `docs/specs/SPEC-fan-effect.md`): three
  consecutive meaning-bar attempts were each caught as an honest obstacle **before any wasted graded run, each for
  a different structural reason** — 1e: **circular** (prediction variable IS the edge weight); fan: **mechanism
  absent** (no out-degree normalization); 2c timing-pair: **signal flat** (friction invariant on realistic
  CPU-bound work). The substrate and the cognitive cycle are real and tester-verified; the recurring hard problem
  is finding an external signal the built mechanism can both **produce** and be **graded against without
  circularity.** This pattern is the anti-circularity / honest-framing discipline working (CLAUDE.md rules 2 & 5),
  not project failure.
- Evidence: `docs/nous_roadmap.md` (top status line; Phase-1 META-FINDING block, lines ~135–140); commits
  `1faf517`, `b474b8f`, `79260fa`, `9b96b97`.
- Honest scope: this is a finding *about this substrate and these three yardsticks*, not a general law about
  spreading-activation models or cognition.

---

# SECTION 2 — WHAT WE CANNOT CLAIM (hard boundaries)

Each is a forbidden claim. None may appear in the paper, in any softened form.

**CC-1.** Nous is **NOT** a mind, consciousness, sentience, understanding, awareness, or AGI — not in prose,
figures, captions, or commit-style asides. (CLAUDE.md rule 1.) Biological *inspiration* may be described;
biological *fidelity* or cognitive achievement may not.

**CC-2.** Nous is **NOT** a validated cognitive model. Its **meaning** is **UNVALIDATED across all three attempts**
(1e, fan, 2c). The paper may claim mechanism, never meaning.

**CC-3.** The substrate does **NOT** reproduce **any** cognitive phenomenon. Three attempts were made and none was
earned, each for a structural reason (Section 1.D). The honest statement is "we tried three times and could not,
for structural reasons" — **not** "the phenomenon is absent" (the data do not license that either).

**CC-4.** The methodology does **NOT** guarantee correctness. It is **not** a proof of bug-freedom or of
cognitive validity. The only claim is that it **caught what it caught** (the six structural bugs; three false-
meaning attempts before any graded run).

**CC-5.** No claim may be made that requires the **graded runs that were never run.** Specifically: no priming
effect size, no fan slope, no interoceptive-modulation direction-of-effect, no ARI "pass." The 1c §6.2 ARI is a
**NOT-YET** secondary check (decisively beats control, fails the absolute bar) — it is not a meaning result.

**CC-6.** The **85% pilot is feasibility, not meaning** — it may never be cited as evidence that interoception
modulates cognition. The "winner-flip" is a **mechanism** causal effect, not a cognitive one.

**CC-7.** "Determinism across 6 hash seeds" may **not** be asserted uniformly — the seed count varies by suite
(5–8). Do not round all suites to one number. **LOCKED positive phrasing (human decision, 2026-06-21):** every
determinism claim uses exactly **"randomized process hash seeds (5–8 per suite, in fresh interpreters)"** (see
P0-3).

<!-- ledger:allow-count -->
**CC-8.** Phase 0's **"130 assertions / 56 functions / 5 suites"** figure is a historical snapshot and may **not**
be presented as the current canonical count. **RESOLVED (human decision, 2026-06-21):** present-day canonical
Phase 0 = store (45) + activation (35) = **80 assertions**; the 130/56/5 figure may appear **only** as an
explicitly-labelled **historical snapshot from Phase 0's completion moment** (see the resolution under P0-1/1.A).

**CC-9.** No claim may rest on the **parked, uncommitted** 2c capture-script/battery, and the canonical count is
**20 suites / 1,372**, not 22.

**CC-10.** The disciplined-exploratory experiment scaffolding (Phase 2A/2B harness, SWOW loader, priming/fan
harnesses) is a **lower assurance tier** than PROVEN or MECHANISM-VERIFIED: it is self-tested, **not** tester- or
validator-verified, and makes **no** cognitive claim of its own. It may not be cited as if it were tier-1/tier-2.

---

# SECTION 3 — CLAIM-TO-EVIDENCE MAP

> Test counts are verbatim from `docs/TEST_OUTPUT.txt`. "Commit" = the hash from `git log` where the artifact
> landed. File paths are absolute-from-repo-root under `/Users/cagancaliskan/Desktop/İşler/Nous/NOUS/nous/`.

| Claim | Tier | Primary artifact(s) | Test (file · what it verifies) | Count | Commit |
|---|---|---|---|---|---|
| P0-1 substrate det/integrity/purity | PROVEN | `src/nous_store.py` | `tests/test_nous_store.py` · reads-pure, sticky closure, integrity, deletion | 45 | (pre-`5d29071` base; see note) |
| P0-2 activation det/purity/no-double-count | PROVEN | `src/nous_activation.py` | `tests/test_nous_activation.py` · cross-proc determinism seeds {0,1,3,7,42}, pure read, convergence sums | 35 | (base) |
| P0-3 cross-proc determinism (seed counts) | PROVEN | activation/coalitions/field/perceive | det tests: act 5 seeds, coalitions 8, field 8, slice 6 | (within above) | (base) |
| M-1 source-clustering mechanism | MECHANISM-VERIFIED | `src/nous_source_clustering.py` · `SPEC-1c-source-clustering.md` | `test_nous_source_clustering.py` (49) + `test_tester_1c_adversarial.py` (73) + `test_tester_1c_mutation_battery.py` (5) | 49 / 73 / 5 | `e4169f9` |
| M-2 workspace competition + pruning | MECHANISM-VERIFIED | `src/nous_workspace.py` · `SPEC-1d-workspace-broadcast.md` | `test_nous_workspace.py` (83) + `test_tester_1d_i_adversarial.py` (107) · over-swallow flip, generalizes on relabelled graph | 83 / 107 | `2fd878b` |
| M-3 bounded broadcast/feedback | MECHANISM-VERIFIED | `src/nous_workspace.py` (broadcast) | `test_nous_workspace_broadcast.py` (63) + `test_tester_1d_ii_adversarial.py` (110) · no-divergence + no-lock-in (80-cycle escape) | 63 / 110 | `e4df7df` |
| M-4 cycle closes end-to-end | MECHANISM-VERIFIED | `src/nous_perceive.py` | `test_nous_perceive.py` · end-to-end slice, det 6 seeds, pure read | 19 | `52abdb6` (merge) |
| M-5 interoception mechanism | MECHANISM-VERIFIED | `src/nous_bodysensor.py` · `SPEC-2c-interoception.md` | `test_nous_bodysensor.py` (49) + `test_tester_2c_adversarial.py` (350) · default-off byte-identity, replay det 6 seeds, live-off, winner-flip-not-echo | 49 / 350 | `462c82a` |
| M-5 feasibility pilot (85%) | MECHANISM-VERIFIED (feasibility, not meaning) | `experiments/pilot_2c_populability.py` | `test_tester_2c_adversarial.py` E3 · re-derived 34/40 = 85.0% | (within 350) | `462c82a` |
| MM-1 four-agent separation | METHODOLOGY | `CLAUDE.md` · `.claude/agents/` | existence of `test_tester_*` distinct from builder suites | n/a | n/a |
| MM-2 loop-closure caught bugs | METHODOLOGY | `docs/METHODOLOGY.md` | findings (a)–(f) + (g)/(h), each → named test | n/a | n/a |
| MM-3 six structural bugs | METHODOLOGY | `docs/METHODOLOGY.md` §6 findings | `test_reads_are_pure`, `test_no_double_count_downstream_of_convergence`, `test_determinism_with_same_hop_edge_adversarial`, `test_determinism_adversarial_across_hash_seeds`, `test_single_seed_spread_yields_multiple_coalitions`, `test_acceptance_multisource_recovers_communities`, `test_KNOWN_LIMITATION_clustered_sources_give_poor_basins` | n/a | base + `e4169f9`/`2fd878b` |
| MM-4 pre-registration + anti-circularity gates | METHODOLOGY | `EXP-1c/1e/2c` (frozen, anti-tamper, SHA-256) | blind 1e selector run, topology-only | (selector suites) | `dc07477`, `321ad80` |
| MM-5 three caught before graded run | METHODOLOGY | roadmap + EXP docs | NO-GO/NOT-YET records | n/a | `9b96b97`, `79260fa`, `1faf517` |
| NY-1 priming NO-GO (circular) | NOT-YET | `SPEC-1e §14` · `EXP-1e §15` · `experiments/results/priming_1e_selection_output.txt` | selector suites (92/76/58) + `test_priming_1e.py` (67) + `test_priming_instrument.py` (42) + `test_harness.py` (17) | 92/76/58/67/42/17 | `9b96b97` |
| NY-2 fan NO-GO (mechanism absent) | NOT-YET | `SPEC-fan-effect.md` · `experiments/results/fan_effect_output.txt` · `experiments/fan_effect.py` | flat curve `0.2433743975`, spread 0.0 | n/a (exploratory) | `79260fa` |
| NY-3 2c timing-pair NOT-YET (flat) | NOT-YET | `EXP-2c §6.1/§6.1.1` · `SPEC-2c` | reason read from engine; freeze held | n/a (no graded run) | `1faf517`, `b474b8f` |
| MF-1 meta-finding (yardstick is the wall) | METHODOLOGY synthesis | roadmap META-FINDING block | three NO-GO/NOT-YET records | n/a | `1faf517`, `b474b8f`, `79260fa`, `9b96b97` |

> **DISCREPANCY FLAGGED (commit attribution for Phase 0).** `git log --oneline -100` shows the **earliest** commit
> as `5d29071 Initial honest package …`, which already contains the verified substrate + activation. The 100-commit
> window does **not** expose the individual commits where `nous_store.py` / `nous_activation.py` were first written
> and verified (they predate or are bundled into `5d29071`). The paper should attribute Phase 0 to "the initial
> honest package (`5d29071`) and earlier development," not to a fabricated per-module commit hash. Marked "base"
> above.

---

# SECTION 4 — HONEST LIMITATIONS (state up front in the paper)

**L-1. Single developer + AI agents.** The work was produced by one human (Cagan) directing a small set of AI
subagents. The "four-agent separation" is a separation of **roles/contexts**, not of independent human teams;
the tester and validator are AI agents operating under enforced lane rules, not external auditors. State this
plainly.

**L-2. The meaning bar was never cleared.** Across all three attempts (1e, fan, 2c) no cognitive phenomenon was
reproduced. The paper's positive result is a **methodology** result and a **mechanism** result, not a cognitive
one.

**L-3. The substrate is small and dependency-free — a prototype, not a system.** Core runs on the Python standard
library alone; all tests are on small graphs; **no scaling claims are made** (`docs/REPORT.md` line 724:
"Scale is unverified … the prototype makes no scaling claims"). The largest graph touched is the SWOW corpus
(1,388,741 edges / 133,763 nodes) and only by the **disciplined-exploratory** selector (blind, no activation) —
not by the verified core under load.

**L-4. The methodology is demonstrated on ONE project.** There is no cross-project validation, no control group,
no comparison against a team that did not use the discipline. "It caught these bugs here" is an existence proof,
not a generalization. The paper is an **experience report**, and should claim only that.

**L-5. Three assurance tiers coexist in the repo and must not be conflated.** PROVEN (Phase 0), MECHANISM-VERIFIED
(1c/1d/2c), and disciplined-exploratory (Phase 2A/2B scaffolding, the 1c §6.2 reproduction). The last is
self-tested, not tester/validator-verified, predates the four-agent discipline, and its data-dependent suites are
**not** in `run_tests.py`. (`docs/nous_roadmap.md` "Verification tiers" note.)

**L-6. "Tester-verified" means verified by an independent adversarial AI agent, against *mechanism* properties
only.** It is not a formal proof and not a meaning verification. The known-limitations are shipped as
asserted-negatives (e.g. the 1d-i cohesion-valley corner case), which is honest but is a *documented gap*, not its
absence.

**L-7. The prior-art citations have been verified at source; the residual is narrow.** The citation-verification
pass is **done** (2026-06-21): **14 references are source-confirmed `[VERIFIED]`** and **8 foundational classics
are `[VERIFIED-PENDING-FINAL-CHECK]`**, needing only a one-line volume/page confirmation at the final
pre-publication pass (Section 5); **no reference remains `[UNVERIFIED]`**. The discipline is visible in the
history: one earlier fabricated mis-attribution ("Sun et al.") was caught and corrected to Candia-Rivera — which
is now itself independently source-confirmed (arXiv:2604.24527; also in Cognitive Systems Research). The only
residual citation caution is the one-line volume/page check on the 8 classics before publication.

**L-8. The roadmap carries historical snapshots alongside current status.** Several figures in
`docs/nous_roadmap.md` (e.g. the 8-suite/254-assertion 1c snapshot; the 130/56/5 Phase-0 line) are explicitly
superseded. The paper must read counts from `docs/TEST_OUTPUT.txt` only (canonical: 20 suites / 1,372).

---

# SECTION 5 — PRIOR-ART / POSITIONING

> **CITATION VERIFICATION DONE** — all references verified at source or marked VERIFIED-PENDING-FINAL-CHECK
> (foundational classics needing only a volume/page confirmation at final pre-publication pass). No fabricated
> citations found; the project's own [VERIFIED-DOCS] markings were all confirmed accurate when checked. (The one
> historically fabricated cite, "Sun et al.", was already caught and corrected to Candia-Rivera — now
> independently confirmed real.)

> **Verification ledger (2026-06-21 citation pass, architect-pm).** The freeze is **LIFTED**. Tag meanings:
> **[VERIFIED]** = independently confirmed at source this session (author/title/venue/year, and the specific
> bibliographic detail — volume/pages/DOI/arXiv ID — checked to match); **[VERIFIED-PENDING-FINAL-CHECK]** =
> foundational classic whose existence is certain and detail is carried as given, needing only a one-line
> volume/page confirmation at the final pre-publication pass (not web-verified in this pass by design).
> **9 priority references were independently confirmed at source this session** (the two post-cutoff 2026 arXiv
> items, the two Shanahan refs, De Deyne/SWOW, Blondel/Louvain, Anderson 1974, Anderson & Reder 1999, Sibson/SLINK,
> Hubert & Arabie/ARI), **plus Franklin et al. (2014) LIDA** — originally the lone [VERIFIED-DOCS] item, now also
> independently confirmed at source (IEEE T-AMD 6(1):19–41; DOI 10.1109/TAMD.2013.2277589) and promoted to
> **[VERIFIED]** — for **10 references source-confirmed this session**. **4 references were already agent-verified**
> (Claessen & Hughes; MacIver & Hatfield-Dodds; Nosek et al.; Anderson & Lebiere) and are kept **[VERIFIED]**.
> **8 foundational classics** are **[VERIFIED-PENDING-FINAL-CHECK]**. **No reference remains [UNVERIFIED] or
> [VERIFIED-DOCS].** WebFetch was unavailable this session; all source confirmation was done via WebSearch against
> publisher / arXiv / DOI-registrar results.

### 5.1 Property-based / random testing (the methodology's nearest engineering lineage)
- **Claessen, K. & Hughes, J. (2000). "QuickCheck: A Lightweight Tool for Random Testing of Haskell Programs."
  ICFP '00 (ACM). DOI 10.1145/351240.351266.** **[VERIFIED]** (agent-verified prior pass; kept) — positions Nous's
  property tests (determinism, purity, integrity, scale-invariance, no-double-count) in the property-based-testing
  tradition. *Nous does not use QuickCheck; it hand-rolls properties in a stdlib harness — note this as a deliberate
  dependency-free choice.*
- **MacIver, D. R. & Hatfield-Dodds, Z. (2019). "Hypothesis: A new approach to property-based testing." Journal of
  Open Source Software 4(43):1891. DOI 10.21105/joss.01891.** **[VERIFIED]** (agent-verified prior pass; kept) — the
  canonical Python PBT library; the natural "why not just use this" comparison. *Nous deliberately stays stdlib-only
  (CLAUDE.md rule 8), so it re-implements a minimal property runner; positioning, not endorsement.*

### 5.2 Pre-registration / reproducibility (the methodology's science lineage)
- **Nosek, B. A., Ebersole, C. R., DeHaven, A. C. & Mellor, D. T. (2018). "The preregistration revolution." PNAS
  115(11):2600–2606. DOI 10.1073/pnas.1708274114.** **[VERIFIED]** (agent-verified prior pass; kept) — the
  anti-circularity / pre-registration discipline (fix prediction + direction before seeing data) is borrowed
  directly; Nous applies it to a software artifact (frozen EXP docs, anti-tamper notices, deferred hashing).
- Cross-process determinism under randomized `PYTHONHASHSEED` is a **reproducibility** practice; if the paper wants
  a citation for the general reproducibility-in-computational-science argument, that needs a real check.
  **[NO CITATION YET — do not invent one]** (this is a placeholder for an optional future reference, *not* a
  reference asserted by this document; it is therefore outside the 9-item verification scope and out of the
  freeze).

### 5.3 Cognitive architectures (DESIGN LINEAGE ONLY — explicitly NOT a validated comparison)
> **Framing rule for the paper:** these are cited as the *design vocabulary and structural lineage* Nous borrows
> (GWT competition-then-broadcast; ACT-R spreading activation), **never** as systems Nous is benchmarked against
> or shown to match. Nous reproduces **none** of their cognitive results (see Section 2). The fan-effect NO-GO is
> precisely a place where Nous's engine **diverges** from ACT-R's mechanism.
- **Baars, B. J. (1988). *A Cognitive Theory of Consciousness.* Cambridge Univ. Press.**
  **[VERIFIED-PENDING-FINAL-CHECK]** (foundational classic; existence certain; carry detail as given; one-line
  volume/page confirmation at final pre-publication pass) (SPEC-1d §9) — Global Workspace Theory; the competition →
  single winner → broadcast **structure** for 1d. *Cited for structure; not a consciousness claim for Nous.*
- **Franklin, S., Madl, T., D'Mello, S. & Snaider, J. (2014). "LIDA: A Systems-level Architecture for Cognition,
  Emotion, and Learning." IEEE Transactions on Autonomous Mental Development 6(1):19–41. DOI
  10.1109/TAMD.2013.2277589.** **[VERIFIED]** (independently confirmed at source 2026-06-21 via WebSearch: IEEE
  Transactions on Autonomous Mental Development vol. 6, no. 1, pp. 19–41, March 2014; DOI 10.1109/TAMD.2013.2277589;
  corroborated across the ACM Digital Library record (dl.acm.org/doi/abs/10.1109/tamd.2013.2277589, "Vol 6, No 1"),
  IEEE Xplore (ieeexplore.ieee.org/document/6587077/), and Semantic Scholar) (SPEC-1d §9) — computational GWT / the
  cognitive cycle; design lineage for the whole Phase-1 loop. *(The project's own prior [VERIFIED-DOCS] marking is
  now upgraded to source-confirmed; the previously-missing venue/volume/pages/DOI are added from source.)*
- **Anderson, J. R. & Lebiere, C. (1998). *The Atomic Components of Thought.* Erlbaum. ISBN 9780805828177.**
  **[VERIFIED]** (agent-verified prior pass; kept) — ACT-R; source of the `S_ji ≈ S − ln(fan)` shared-budget
  account that the fan-effect NO-GO shows Nous's engine lacks.
- **Anderson, J. R. (1974). "Retrieval of propositional information from long-term memory." Cognitive Psychology
  6(4):451–474. DOI 10.1016/0010-0285(74)90021-8.** **[VERIFIED]** (independently confirmed at source 2026-06-21:
  Cognitive Psychology 6(4):451–474; via Semantic Scholar / Springer-indexed citation and the U. Michigan Deep Blue
  record) — the original fan effect; the external direction the fan bar would have graded against.
- **Anderson, J. R. & Reder, L. M. (1999). "The fan effect: New results and new theories." J. Exp. Psychol.
  General 128(2):186–197.** **[VERIFIED]** (independently confirmed at source 2026-06-21: J. Exp. Psychol. General
  vol. 128, pp. 186–197, via the ACT-R/CMU publications listing and ResearchGate record).
- **Shanahan, M. (2006). "A cognitive architecture that combines internal simulation with a global workspace."
  Consciousness and Cognition 15(2):433–449.** **[VERIFIED]** (independently confirmed at source 2026-06-21:
  Consciousness and Cognition vol. 15, pp. 433–449; via the author's Imperial College PDF, PhilPapers, and Semantic
  Scholar). — internal-simulation + global-workspace design lineage.
- **Shanahan, M. (2010). *Embodiment and the Inner Life: Cognition and Consciousness in the Space of Possible
  Minds.* Oxford University Press. ISBN 9780199226559.** **[VERIFIED]** (independently confirmed at source
  2026-06-21: Oxford University Press, 2010, ISBN 9780199226559; via the OUP/Biblio listing, Internet Archive, and
  Semantic Scholar). — the "space of possible minds" framing; design lineage, not a consciousness claim for Nous.
- **Dehaene, S. & Changeux, J.-P. (2011). "Experimental and theoretical approaches to conscious processing."
  Neuron 70(2):200–227.** **[VERIFIED-PENDING-FINAL-CHECK]** (foundational classic; existence certain; carry detail
  as given; one-line volume/page confirmation at final pre-publication pass) (SPEC-1d §9) — cited for selective
  amplification/suppression **structure** only.

### 5.4 Neuroscience / cognitive-science lineage for specific bricks (analogy of *direction*, never fidelity)
- **Hebb, D. O. (1949). *The Organization of Behavior.* Wiley.** **[VERIFIED-PENDING-FINAL-CHECK]** (foundational
  classic; existence certain; one-line confirmation at final pre-publication pass) (SPEC-1d §9) — strengthening
  co-active associations (broadcast-as-plasticity lineage).
- **Turrigiano, G. G. (2008). "The self-tuning neuron: synaptic scaling of excitatory synapses." Cell 135(3):
  422–435.** **[VERIFIED-PENDING-FINAL-CHECK]** (foundational classic; existence certain; carry detail as given;
  one-line volume/page confirmation at final pre-publication pass) (SPEC-1d §9) — homeostatic plasticity; lineage
  for the bounding/normalization that keeps the broadcast from diverging.
- **Easterbrook, J. A. (1959). "The effect of emotion on cue utilization and the organization of behavior."
  Psychological Review 66(3):183–201.** **[VERIFIED-PENDING-FINAL-CHECK]** (foundational classic; existence
  certain; carry detail as given; one-line volume/page confirmation at final pre-publication pass; EXP-2c §2.2
  additionally marks it WebSearch-verified 2026-06-21) — the cue-utilization (attentional-narrowing) hypothesis;
  the external *direction* for the 2c interoception claim.
- **Damasio, A. (1994). *Descartes' Error.* Putnam — somatic-marker hypothesis.** **[VERIFIED-PENDING-FINAL-CHECK]**
  (foundational classic; existence certain; one-line confirmation at final pre-publication pass) (SPEC-2c §2.1) —
  bodily states bias selection; the 2c analogue, stated narrowly.
- **Craig, A. D. (2002). "How do you feel? Interoception: the sense of the physiological condition of the body."
  Nature Reviews Neuroscience 3:655–666.** **[VERIFIED-PENDING-FINAL-CHECK]** (foundational classic; existence
  certain; carry detail as given; one-line volume/page confirmation at final pre-publication pass) (SPEC-2c §2.1) —
  interoception as a sensory channel; Nous tests only the computational analogue.
- **Candia-Rivera, D. (2026). "Interoceptive machine framework: Toward interoception-inspired regulatory
  architectures in artificial intelligence." Cognitive Systems Research (arXiv:2604.24527; submitted 27 Apr 2026).**
  **[VERIFIED]** (independently confirmed at source 2026-06-21: sole author Diego Candia-Rivera, arXiv:2604.24527
  submitted 27 Apr 2026, also published in Cognitive Systems Research per ScienceDirect article
  S1571064526000461) — the interoceptive-variable-vs-passive-telemetry distinction (the pass-through trap).
  **NB: post-cutoff (2026), confirmed via WebSearch against arXiv + ScienceDirect; a one-line re-confirm at final
  pre-publication pass is still prudent given the post-cutoff date.** *This entry **replaced the one historically
  fabricated cite on this project ("Sun et al."), which was already caught and corrected (SPEC-2c §2.1) — the
  replacement Candia-Rivera reference is now independently confirmed real at source.***
- **Brady, S. (2026). "Springdrift: An Auditable Persistent Runtime for LLM Agents with Case-Based Memory,
  Normative Safety, and Ambient Self-Perception." arXiv:2604.04660 (cs.AI; submitted 6 Apr 2026).** **[VERIFIED]**
  (independently confirmed at source 2026-06-21: sole author Seamus Brady, arXiv:2604.04660 submitted 6 Apr 2026,
  cs.AI; confirmed via the arXiv 2026-04 listing and the project's own GitHub/site) — cited **only** as a
  different-family reference point (an **LLM-based** persistent-runtime system), **not** as a comparison or
  benchmark for Nous. **NB: post-cutoff (2026); a one-line re-confirm at final pre-publication pass is prudent.**
  *(The doc previously carried the fuller title; confirmed it matches. Earlier SPEC-2c marking "UNVERIFIED in detail
  / WebFetch blocked" is now superseded — WebSearch reached the arXiv listing and the title/author/date all match.)*

### 5.5 External data / methods the experiments used
- **De Deyne, S., Navarro, D. J., Perfors, A., Brysbaert, M. & Storms, G. (2019). "The 'Small World of Words'
  English word association norms for over 12,000 cue words." Behavior Research Methods 51(3):987–1006. DOI
  10.3758/s13428-018-1115-7.** **[VERIFIED]** (independently confirmed at source 2026-06-21: Behavior Research
  Methods vol. 51, pp. 987–1006, 2019; DOI 10.3758/s13428-018-1115-7; via the authors' PDFs and Semantic Scholar) —
  the external relatedness yardstick for 1e/1c (SWOW).
- **Blondel, V. D., Guillaume, J.-L., Lambiotte, R. & Lefebvre, E. (2008). "Fast unfolding of communities in large
  networks." J. Stat. Mech.: Theory and Experiment 2008(10):P10008. DOI 10.1088/1742-5468/2008/10/P10008.**
  **[VERIFIED]** (independently confirmed at source 2026-06-21: J. Stat. Mech. 2008, P10008; DOI
  10.1088/1742-5468/2008/10/P10008; via the official IOPscience record and arXiv:0803.0476) — Louvain; the
  *independent* community grader for 1c §6.2 (a different algorithm family from the method under test).
- **Hubert, L. & Arabie, P. (1985). "Comparing partitions." Journal of Classification 2(1):193–218. DOI
  10.1007/BF01908075.** **[VERIFIED]** (independently confirmed at source 2026-06-21: Journal of Classification
  vol. 2, pp. 193–218, 1985; DOI 10.1007/BF01908075; via the Springer record and Semantic Scholar) — the Adjusted
  Rand Index used in §6.2.
- **Sibson, R. (1973). "SLINK: an optimally efficient algorithm for the single-link cluster method." The Computer
  Journal 16(1):30–34. DOI 10.1093/comjnl/16.1.30.** **[VERIFIED]** (independently confirmed at source 2026-06-21:
  The Computer Journal vol. 16, no. 1, pp. 30–34, 1973; DOI 10.1093/comjnl/16.1.30; via the official Oxford Academic
  record) — single-link clustering lineage for 1c. *(DOI 10.1093/comjnl/16.1.30 confirmed at source; the brief did
  not assert a DOI — adding the confirmed one.)*
- **Traag, V. A., Waltman, L. & van Eck, N. J. (2019). "From Louvain to Leiden: guaranteeing well-connected
  communities." Scientific Reports 9:5233.** **[VERIFIED-PENDING-FINAL-CHECK]** (foundational/standard reference;
  existence certain; carry detail as given; one-line confirmation at final pre-publication pass) (SPEC-1c) — cited
  as the preferred community grader (Leiden), used only as last-resort external grader.

> **Action before writing the paper (residual, post-freeze-lift):** the 9 priority references, the 4 prior-pass
> references, and **Franklin et al. (2014) LIDA** (now source-confirmed at IEEE T-AMD 6(1):19–41; DOI
> 10.1109/TAMD.2013.2277589) are **[VERIFIED]** and need no further check — **no [VERIFIED-DOCS] reference remains.**
> One residual item remains: the **8 [VERIFIED-PENDING-FINAL-CHECK]** classics each need a one-line volume/page
> confirmation at the final pre-publication pass. The two post-cutoff 2026 arXiv items (Candia-Rivera, Springdrift)
> are now confirmed via WebSearch; a one-line human re-confirm at final pass is still prudent given the post-cutoff
> date. When in doubt, downgrade rather than risk a second fabrication.

---

# SECTION 6 — VISUALIZATION PLAN (a PLAN only — NO figures generated here)

> For each candidate: (1) what it shows; (2) which Section-1 claim it backs; (3) what real artifact it is built
> from; (4) how it avoids overclaiming. Figures that cannot be mapped to a real artifact are flagged.

**F-1. The closed cognitive-cycle architecture diagram** (perceive → activate → cluster → compete → prune →
broadcast → next).
1. Shows the seven-stage loop and where the single bounded write closes it.
2. Backs **M-4** (cycle closes end-to-end) and contextualizes M-1/M-2/M-3.
3. Built from: the module call graph (`nous_perceive.py` → `nous_activation.py` → `nous_source_clustering.py` →
   `nous_field.py`/`nous_coalitions.py` → `nous_workspace.py` → broadcast); existing diagram source
   `docs/diagrams/pipeline.mmd` can be the starting point (note it predates 1d — must be updated to show
   prune + broadcast + feedback edge).
4. Avoids overclaiming: label it **"mechanism / information flow"**; caption must say "no cognitive claim — these
   are graph operations and a bounded write." Use neutral verbs (select, prune, write), not "decide," "attend,"
   "experience." Mark the broadcast edge "bounded, default-off feedback."

**F-2. The four-agent verification topology** (build / break-mechanism / break-meaning / plan, with the lane
rules and the artifacts each produces).
1. Shows the role separation and what crosses between roles (spec → code → independent adversarial suite →
   validator pre-registration), and the hard lane rules (PM no prod code; tester no prod edits; builder no
   designed-as-built).
2. Backs **MM-1** (four-agent separation).
3. Built from: `CLAUDE.md` "How the agents work together"; the file split (`test_tester_*` vs builder suites);
   `.claude/agents/` (note: `.claude/` is untracked per `git status` — confirm contents before depicting).
4. Avoids overclaiming: caption "separation of roles/contexts operated by AI agents under enforced rules" (per
   L-1) — not "independent human teams." Show the validator lane as **partly unexercised** (no cognitive claim
   reached it for 1c/1d; for the meaning bars it returned NO-GO/NOT-YET before grading).

**F-3a. Anatomy of NY-1 (priming): the S0-stratum collapse.**
1. Shows why the weight-blind leverage stratum cannot populate: the saturating ladder `W = min(10, 1+floor(s·100))`
   maps almost all HIGH > LOW, so weight-blind pairs are rare (N_S0 = 7 < 30), and the fallback is unreachable
   (`r_W ≈ 0.97` ⇒ needed `r_MA > 1.0`).
2. Backs **NY-1**.
3. Built from: the verbatim selector stdout `experiments/results/priming_1e_selection_output.txt` and the
   pair-count files; EXP-1e §15. (Real artifact — exists.)
4. Avoids overclaiming: caption "design infeasible on SWOW under anti-circularity controls — does NOT claim
   priming is absent"; show that **no activation/Δ was computed** (the gate fired pre-grade).

**F-3b. Anatomy of NY-2 (fan effect): the flat curve.**
1. Shows the fan sweep flat to the last digit (`0.2433743975`, spread 0.0 across fan {1,2,4,8,16}) and annotates
   the cause: `spread_activation` feeds full activation per out-edge, no `/fan` (vs ACT-R `S_ji ≈ S − ln(fan)`).
2. Backs **NY-2**.
3. Built from: verbatim `experiments/results/fan_effect_output.txt`; `experiments/fan_effect.py`. (Real artifact —
   exists.)
4. Avoids overclaiming: caption "the engine has no out-degree normalization — the effect is not produced *on this
   engine as built*; this is not a claim about the fan effect in general." Mark tier **disciplined-exploratory.**

**F-3c. Anatomy of NY-3 (interoception): the yield-dominated / flat friction band.**
1. Shows `friction = clamp(1 − cpu/wall, 0, 1)` as a stall fraction that is ≈ 0 on CPU-bound work and
   scale-invariant; contrasts the manufactured/yield-dominated band `[0.79..0.93]` (set by an injected sleep)
   against the realistic-workload friction ≈ 0.
2. Backs **NY-3**.
3. Built from: the **arithmetic/structural argument** in EXP-2c §6.1.1 (the relationship is analytic, read from
   the engine). **FLAG:** the realistic-workload "friction ≈ 0" line is an analytic/derived statement, not a
   committed measurement file — the as-written capture is **parked/uncommitted** (`experiments/exp2c_capture.py`).
   The figure must be drawn from the **analytic argument**, labelled as such, OR explicitly note the band is from
   the parked capture and not in the canonical record. Do **not** present a fabricated measured curve.
4. Avoids overclaiming: caption "NOT a mechanism defect — the modulation channel is tester-PASS (85% couplability);
   the *signal* carries no real-contention variation." Show the §6.4 freeze as HELD.

**F-4. The three-tier assurance map** (PROVEN / MECHANISM-VERIFIED / disciplined-exploratory — and the meaning bar
as UNVALIDATED).
1. Shows the repo stratified by tier: Phase 0 (PROVEN) at the base; 1c/1d/2c (MECHANISM-VERIFIED) above; Phase
   2A/2B scaffolding + 1c §6.2 (disciplined-exploratory) to the side; the meaning bar as an open/empty top box.
2. Backs the whole of Section 1's tier structure and **L-5**.
3. Built from: `docs/nous_roadmap.md` "Verification tiers" note + `docs/TEST_OUTPUT.txt` per-suite counts.
4. Avoids overclaiming: keep the three boxes visually distinct and **never** merge them; the meaning box is empty
   with the label "UNVALIDATED (3 attempts, 3 structural walls)." Put exact assertion counts only where they come
   from TEST_OUTPUT.txt.

**F-5. The meta-finding schematic** (three distinct structural walls → one common root: the external yardstick).
1. Shows three lanes (1e: circular / strength=weight; fan: mechanism-absent / no out-degree norm; 2c: signal-flat /
   friction invariant) converging on one node: "the wall is the external meaning yardstick, not the mechanism."
2. Backs **MF-1** and **MM-5**.
3. Built from: roadmap META-FINDING block; the three NO-GO/NOT-YET commits (`9b96b97`, `79260fa`, `1faf517`).
4. Avoids overclaiming: caption "the substrate + cycle are tester-verified; this is the anti-circularity discipline
   working, not project failure" and "a finding about these three yardsticks on this substrate, not a general law."

**F-6 (additional, recommended). The six-bug timeline / table** (bug → root cause → fix → locking test).
1. Shows each of the six structural bugs with the test that now locks it (a compact version of METHODOLOGY §6).
2. Backs **MM-3** (and is the paper's most concrete evidence the discipline catches structural bugs).
3. Built from: `docs/METHODOLOGY.md` §(a)–(f); the named tests; existing diagram `docs/diagrams/six_findings.mmd`
   (real artifact — exists; verify it matches the current six before reuse).
4. Avoids overclaiming: present as "bugs *caught by this discipline on this project*"; do not imply the list is
   exhaustive or that the discipline guarantees bug-freedom (CC-4). Omit error magnitudes (the methodology doc
   already omits them where unreproducible).

**F-7 (additional, optional). Determinism-across-seeds evidence strip.**
1. Shows, per suite, the seed set used (act 5, coalitions 8, field 8, slice 6, tester suites 6) and "byte-identical
   across all."
2. Backs **P0-3** and **CC-7** (makes the non-uniform seed count honest and visible).
3. Built from: the determinism tests' seed lists (confirmed in `tests/test_nous_*.py`).
4. Avoids overclaiming: this figure exists precisely to **prevent** the "6 seeds everywhere" overclaim — show the
   real per-suite numbers. (An existing `docs/diagrams/figures/determinism_seeds.py` exists but its docstring
   mentions "invented activation values" for illustration — **flag:** if reused, redraw from the real seed lists,
   not illustrative values.)

> **Figures NOT to propose (no real artifact / would overclaim):** any "cognitive performance" curve; any
> priming effect size, fan slope, or interoception direction-of-effect plot (those graded runs were never run —
> CC-5); any figure built from the parked 2c capture as if it were canonical; any side-by-side "Nous vs ACT-R/LIDA
> performance" comparison (design lineage only — Section 5.3).

---

## Appendix — flags raised while building this inventory

These are listed again, consolidated, at the end of the returned message.
