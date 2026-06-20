# Phase 2B — Working Notes (internal build log; survives context compaction)

> ALL numbers below are MEASURED (scripts in /tmp during exploration). Earlier drafts of
> this file contained figures from CANCELLED runs (csv.DictReader crash) — those were
> fabricated and have been purged. If a number isn't reproduced by a committed script or a
> captured result file, it does not belong here.

## TASK (verbatim intent)
Pre-registered GRADED SEMANTIC PRIMING on SWOW English. Work in nous/experiments/. DO NOT
modify src/ or tests/. Reuse 2A harness.py (build_graph_from_spec, retrieval_strength,
run_trials) UNCHANGED; may ADD additive helpers. Disciplines: deterministic by construction
(Clock simulated), pure reads, adversarial cross-process determinism (PYTHONHASHSEED in
{0,1,2,3,7,42,123,999}) on FINAL numbers, capture every number verbatim to results/,
predictions PRINTED BEFORE results, verdicts computed from data, engine NEVER modified,
null = honest finding. Commit on NEW branch phase-2b-priming:
"Phase 2B: pre-registered graded semantic priming on SWOW (honest)."
Start branch: phase-2a-fan-effect (2A=780f96f, clean working tree).

## DATA — measured
- experiments/data/strength.SWOW-EN.R123.20180827.csv (53 MB, UTF-8). NOT committed (license
  + size). .gitignore excludes experiments/data/. data/README.md documents source+how-to-get.
- TAB-separated. Header: cue<TAB>response<TAB>R123<TAB>N<TAB>R123.Strength
- 1,389,711 data rows; all exactly 5 fields; max field 62 chars; 0 CR.
- *** csv module CRASHES: 2 rows contain a stray '"' -> "field larger than field limit".
  MUST parse plain TSV (line.split("\t") or csv QUOTE_NONE). Documented in EXPERIMENT_NOTES.
- MEASURED (two independent scripts agree): distinct cues 12,217; distinct responses
  133,762; union (graph nodes) 133,763; roads 1,388,741; responses-not-cues (out-deg-0
  leaves) 121,546; nodes with in-degree>0 = 133,762.
- R123.Strength in [0,1], heavy right skew (mean 0.0123, median 0.01). 28 rows strength==0 -> drop.

## LOCKED PRE-REGISTRATION (decided BEFORE the main run)
- SUBSTRATE: FULL graph (all 133,763 words; all cue->response edges, strength>0, drop self-loops).
  Cue-core subgraph REJECTED: measured reach within 3 hops = 98.2% -> no topological UNRELATED
  possible. Full graph reach (measured): <=2h 4.4%, <=3h 47.3%, <=4h 98.5%.
- EDGE MAPPING (same rule every edge, no per-pair tuning):
    traverse_count = min(10, 1 + floor(R123.Strength * 100))   # monotonic, capped 1..10
- CLOCK: Clock(simulated=True), t=0 (exact strengths, deterministic build).
- ACTIVATION KNOBS: library defaults (energy 1.0, decay_per_hop 0.65, floor 0.02, hop_budget 6).
- READOUT PRIMARY: raw target activation (harness.retrieval_strength == read_targets, 2A instrument).
  SECONDARY (labeled): normalized = target_act / prime_outgoing_total (sum of flow on prime's out-roads).
- CONDITIONS (within-prime; selected BLIND from topology+strength only, fixed seeded RNG):
    DIRECT   : 1-hop response of prime (record SWOW strength for P1).
    MEDIATED : exists prime->M->target (2-hop) AND no direct prime->target edge.
    UNRELATED: in-degree>0 AND not reachable from prime within K=4 hops.
  Measured UNRELATED candidates/prime at K=4 (in-deg>0 & unreachable): min 1139, median 1934,
  max 4105; candidate median in-degree = 1 = overall (no periphery/frequency bias). MEDIATED
  always plentiful (2-hop shell from out-deg ~113 primes).
- N_PRIMES target: 400 (within-prime: 1 direct + 1 mediated + 1 unrelated per prime). Report
  actual N (= primes yielding all 3 conditions). Selection seed: FIXED (see code constant).

## DETERMINISM DISCIPLINE
- Any set/dict must be SORTED before rng.choice / iteration that affects results (hash-seed
  invariance). Node ids assigned by sorted(words). CSR neighbor order sorted.
- Adversarial cross-process test: run the SAME pipeline in fresh subprocess per hash seed,
  print canonical summary, assert byte-identical across the 8 seeds. To keep it tractable it
  uses a REDUCED but real config (env NOUS_PRIMING_MAXROWS + small N_PRIMES) exercising the
  IDENTICAL load->build->select->spread->summarize code path. Documented as reduced-but-faithful.

## FEASIBILITY — measured (library defaults, manual TSV)
- Full build (debug=True): 133,763 nodes, 1,388,741 roads, ~16.5s, ~0.9 GB.
- Spread (full): median ~1.1s, reached median ~9,878. Main run 400 primes x1 spread ~ <10 min.

## ARCHITECTURE
- experiments/swow.py : load TSV (manual), CSR int-graph for fast BLIND BFS selection,
  spec() for build_graph_from_spec, select(n_primes,K,seed) -> word-space pairs + strengths.
  Selection touches ONLY topology+strength (never activation) => provably blind.
- harness.py : ADD read_targets(store, cue, targets, **knobs) -> {"activation":{t:a},
  "outgoing_total":float,"reached":int} via ONE spread_activation (same engine call as
  retrieval_strength; test asserts equivalence). No edits to existing 2A functions.
- experiments/priming.py : banner FIRST; load; build; select; SAVE pair lists; spread per
  prime; aggregate; print table (cond|N|mean|median raw + normalized) + MEDIATED-vs-UNRELATED
  highlight + within-prime sign proportions; verdicts P1, P2, M-vs-U computed from data.
- experiments/test_priming.py : build determinism (values), read_targets purity + equivalence
  to retrieval_strength, adversarial cross-process determinism of summary. check() style.

## DELIVERABLES CHECKLIST
- [ ] nous/.gitignore : add experiments/data/  (exclude the 53MB csv)
- [ ] experiments/data/README.md (SWOW version, URL, citation, license, schema, how-to-obtain)
- [ ] experiments/swow.py
- [ ] harness.py : + read_targets (additive)
- [ ] experiments/priming.py
- [ ] experiments/test_priming.py
- [ ] experiments/PRIMING.md
- [ ] EXPERIMENT_NOTES.md : append 2B (csv quote-row crash; substrate decision + measured reach; mapping; K)
- [ ] results/: priming_output.txt, priming_pairs_{direct,mediated,unrelated}.txt, determinism + audit captures
- [ ] printed self-audit; re-run run_tests.py -> 130/0
- [ ] commit on branch phase-2b-priming

## STATUS LOG
- Verified schema/size/edge-cases; csv crash -> manual TSV. Measured cue-core (too dense) +
  full graph + unrelated availability. Locked pre-registration (full graph, K=4, mapping,
  within-prime, defaults). NEXT: write swow.py + smoke test, then harness helper + priming.py.
