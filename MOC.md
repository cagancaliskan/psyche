<!-- ledger:ignore-file -->
# Nous / Psyche — map of content

The entry point. Start here in Obsidian; everything else hangs off this.

## Where we are

- [[tools/ledger.json|THE LEDGER]] — every quotable fact. Nothing else is authoritative.
- [[docs/nous_roadmap|Roadmap]] — the narrative position, phases, "you are here"
- [[DECISIONS|Decisions]] — append-only log of what changed and why
- [[CLAUDE|Constitution]] — the ten rules

## The build

- [[README|Repo README]]
- [[docs/ARCHITECTURE|Architecture (as-built)]]
- [[docs/METHODOLOGY|Methodology — the six bugs]]
- [[docs/REPORT|Technical report]]

Modules: `nous_store` · `nous_activation` · `nous_field` · `nous_coalitions` ·
`nous_source_clustering` · `nous_workspace` · `nous_perceive` · `nous_bodysensor`

## Specs and pre-registrations

| Brick | Spec | Pre-registration | Verdict |
|---|---|---|---|
| 0b | [[docs/BUG-0b1-coalition-strength-determinism\|BUG-0b1 §8]] | — | **PROVEN contested — DEFECT-A, status call open (D-011)** |
| 0b2 | [[docs/specs/SPEC-0b2-conserved-activation\|conserved activation]] | — | **mechanism FAIL — N-2, N-5; §6 is the record** |
| 1c | [[docs/specs/SPEC-1c-source-clustering\|source clustering]] | [[docs/experiments/EXP-1c-swow-recovery\|SWOW recovery]] | NOT YET (ARI 0.228 / 0.30) |
| 1d | [[docs/specs/SPEC-1d-workspace-broadcast\|workspace + broadcast]] | — | mechanism PASS |
| 1e | [[docs/specs/SPEC-1e-priming\|priming]] | [[docs/experiments/EXP-1e-priming\|priming]] | **NO-GO — circular** |
| 1e′ | [[docs/specs/SPEC-fan-effect\|fan effect]] | — | **NO-GO — mechanism absent** |
| 2c | [[docs/specs/SPEC-2c-interoception\|interoception]] | [[docs/experiments/EXP-2c-interoception\|interoception]] | **NOT-YET — signal flat** |

## The paper

- [[docs/specs/PAPER_CLAIM_INVENTORY|Claim inventory]] — the locked honesty contract
- `docs/paper/paper.tex` — *Mechanism Is Not Meaning*
- `docs/paper/ieee/` — the 6-page conference version

## The vision — **aspirational, not built**

[[docs/design/README|Read the disclaimer first]]. These thirteen documents were written
before the code and use deliberately grand language. Only `plan_layer0_topology` and
`plan_layer1_substrate_store` correspond to anything that exists.

Modules 01–06: memory hierarchy · abstraction engine · self model · motivation architecture ·
attention & awareness · emotional regulation.
Description docs: the body's voice · the sleeping brain · how this brain comes to speak.
Foundation: substrate biology (the most mathematically concrete doc in the set).

## The program

1. **Brick 0** — BUG-0b1, the determinism fix · *landed, `PROVEN` at its own site — but the
   same bug class is live one layer upstream (DEFECT-A, BUG-0b1 §8)*
2. **Brick 1** — SPEC-0b2, conserved activation · *overlay landed default-off; tester verdict
   **FAIL** on §6 (N-2, N-5); σ/floor decision still open; the default flip additionally needs
   plumbing through the field builder*
3. **Brick 1.5 (new, and it comes first)** — repair the foundation: DEFECT-A and DEFECT-B,
   both open, both awaiting Cagan's call in D-011
4. **Brick 2** — temporal credit assignment via tag-and-capture · *not started*
5. **Brick 3** — learn the graph, grade it against SWOW · *not started; the first
   non-circular meaning bar available*

## The three walls

Every meaning-bar attempt so far, and why each stopped:

- **1e — circular.** The prediction variable *was* the edge weight.
- **1e′ — mechanism absent.** No shared budget, so the fan curve is flat to the last digit.
- **2c — signal flat.** Friction ≈ 0 on realistic CPU-bound work.

The pattern is the finding. Scope it to this substrate and these yardsticks.
