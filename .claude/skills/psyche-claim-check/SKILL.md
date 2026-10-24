---
name: psyche-claim-check
description: Audit any text against the Psyche honesty contract before it ships — a commit message, README section, paper paragraph, delivery report, outreach email, or docstring. Runs the automated staleness and forbidden-claim checks, then applies the judgement checks a linter cannot. Use before every commit and before anything leaves the repository.
argument-hint: "[path or paste the text]"
allowed-tools: Read, Glob, Grep, Bash, Edit
---

# Claim check — before this leaves the building

Target: **$ARGUMENTS**

## Step 1 — the automated pass

The D-031 commit gate while the paper is held (D-012): every check except C2 must be clean,
and C2 may report only the held paper.

```!
cd "${CLAUDE_PROJECT_DIR}" && { out=$(python3 tools/ledger_check.py --only C1,C3,C4,C5,C6 2>&1); rc=$?; printf '%s\n' "$out" | head -40; echo "ledger_check --only C1,C3,C4,C5,C6: exit $rc"; }
```

```!
cd "${CLAUDE_PROJECT_DIR}" && { out=$(python3 tools/publish/ci_c2.py 2>&1); rc=$?; printf '%s\n' "$out" | head -40; echo "tools/publish/ci_c2.py: exit $rc"; }
```

Both must exit 0. `ci_c2.py` tolerates C2 findings only under `docs/paper/`; a stale count
anywhere else fails it. Exit 1 is a finding; exit 2 is a tool error, and a tool error is a
**HOLD**, never a pass. Fix every finding or add an explicit pragma with a reason — never
silence one without it.

## Step 2 — the judgement pass

A linter catches stale numbers and asserted forbidden terms. It cannot catch the four ways
this project could still mislead. Read the target text and answer each **in writing**.

### A. Tier leakage — the most likely failure

Three assurance tiers, and each must stand on its own credibility:

| Tier | What it covers | What it earns |
|---|---|---|
| **1 · PROVEN** | substrate store, spreading activation | determinism, integrity, purity — mechanism only |
| **2 · mechanism-verified** | clustering, workspace, broadcast, body sensor | the mechanism does what it says, deterministically. **No cognitive claim.** |
| **3 · disciplined-exploratory** | `experiments/` scaffolding | an *instrument*. Self-tested, not tester-verified. Establishes nothing. |

- Does any sentence let a tier-3 number wear tier-1 clothes?
<!-- ledger:allow-count -->
- Does "618 assertions, all passing" appear next to a cognitive-sounding noun in a way that
  implies the assertions verified the cognition? They verified mechanism.
- Is a **feasibility** figure being read as a **meaning** figure? The 2c pilot's 85%
  winner-flip rate is feasibility. It is not evidence that interoception modulates
  cognition, and it may never be cited as though it were.

### B. Mechanism-as-meaning

- Does any verb do work the evidence does not support? Allowed: *inspired by*, *borrows the
  framing of*, *is loosely shaped after*. Not allowed: *implements*, *models*, *reproduces*,
  *demonstrates*, *shows that the system* — unless an external graded result backs it.
- "The loop closes" is a statement about a pipeline running to completion with one bounded
  write. It is not perceiving, attending, deciding, or meaning.
- Borrowed vocabulary — *workspace*, *coalition*, *broadcast*, *winner*, *body*, *friction*
  — is engineering lineage. Using GWT's words is not evidence of GWT's phenomena.

### C. The negative results

- Are all three walls represented honestly where relevant: 1e **circular**, fan
  **mechanism-absent**, 2c **signal-flat**? Collapsing them into "we hit some obstacles"
  loses the finding, which is that they are *structurally distinct*.
- Is any NO-GO framed as "the phenomenon is absent"? It is not. The honest form is *"we
  could not measure it under these controls on this corpus"* — the data do not license more.
- Is the meta-finding scoped? It is a finding about **this substrate and these three
  yardsticks**, not a general law about spreading-activation models.

### D. What is missing

- If a number appears, does a captured artifact produce it? If it cannot be reproduced by a
  committed script or a captured result file, it does not belong in the text.
- If a limitation exists, is it stated *here*, or only in a document the reader will not
  open? Known limitations travel with the claim.
- If the text reports a determinism property, does it state the environments it was checked
  in? A property that holds on one interpreter and fails on another was never a property.
  Say which interpreters, and which hash seeds.

## Step 3 — the outreach-specific pass

If this is leaving the repository (email, abstract, submission, post):

- Numbers must match `tools/ledger.json`. The templates in `docs/outreach/` have historically
  quoted figures an order of magnitude stale.
- Lead with the methodology, not the ambition. The defensible claim is a verification
  methodology demonstrated on one system, with three refused claims as evidence it works.
- Never write the words *mind*, *conscious*, *sentient*, *AGI*, or *validated cognitive
  model* about this system, in any softened form.
- If describing progress toward the consciousness question, use the indicator-property
  framing: *"the architecture satisfies indicator X, assessed against Butlin et al."* is
  checkable and modest. Anything about minds is neither.

## Step 4 — disclosure pass (D-031)

**Scope.** Questions 1–6 apply to text about the thesis (the SCM work), wherever it appears,
and to anything under the D-031 public paths (`README.md`, `MOC.md`, `docs/PSYCHE.md`,
`docs/thesis/**`, `thesis/**`, `website/**`, `tools/thesis_plan.json`). Psyche's own public
record is not thesis detail: its pre-registrations and results under `docs/experiments/`, its
experiment ids (1e, 1e′, 2c and the like) and the held paper under `docs/paper/` are judged by
Steps 1–3, even where a D-031 page mentions them. Questions 7 and 8 apply to every target. If
the target holds no thesis text and touches no D-031 path, say so in one line and answer 7
and 8 only.

This repository holds the public summary of the thesis; the detail stays private until
submission and moves here only under `docs/thesis/disclosure-policy.md`. Read the target and
answer each question **in writing**. **Any yes is a HOLD.** When unsure whether something is
private, it is.

1. **Hypotheses.** Does it state a hypothesis beyond the level of the research questions? A
   research question may be asked; a prediction, an expected direction or an expected outcome
   may not be stated.
2. **Thresholds and criteria.** Does it give a threshold, a pass criterion or any numeric
   criterion for a thesis test, gate or comparison?
3. **Experiments.** Does it name a thesis experiment id or any other private identifier, or
   give the order in which the thesis experiments run?
4. **The model.** Does it describe the thesis model's mechanism, or name its files, modules,
   classes or functions?
5. **Positioning.** Does it position the thesis against a named model or a named competing
   system?
6. **Venues and funding.** Does it name a venue for the thesis work (a conference, workshop
   or journal) while venue names are withheld, or a funding programme? They are withheld
   now: the public pages say only "a major peer-reviewed ML venue". Naming one is Cagan's
   call.
7. **The private repository.** Does it name the private companion repository, or point to it
   by path, URL or remote?
8. **Language.** Does it contain Turkish text, even a single Turkish letter? Everything in
   this repository is English; proper names are written in ASCII.

The PreToolUse guard (`tools/hooks/guard_public_boundary.py`) already refuses Turkish letters,
private identifiers and the private marker in the English-only public paths as they are
written through Write, Edit, MultiEdit, NotebookEdit and the MCP file tools its matcher
names, in sessions launched in the repository root. It cannot judge questions 1–7, it never
sees commit messages, shell writes (`render_plan.py --write` among them), writes through any
other tool, or text leaving the repository, and a session rooted in a parent folder does not
run it at all. This pass does not depend on it.

A disclosure finding is fixed by deleting or generalising the text, never by a pragma.

## Output

A verdict — **SHIP** or **HOLD** — followed by a numbered list of every change required, each
with the exact replacement text. If SHIP, say in one line what the strongest claim in the
text is and what evidence backs it, and confirm that Step 4 found nothing.
