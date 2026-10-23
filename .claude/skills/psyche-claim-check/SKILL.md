---
name: psyche-claim-check
description: Audit any text against the Psyche honesty contract before it ships — a commit message, README section, paper paragraph, delivery report, outreach email, or docstring. Runs the automated staleness and forbidden-claim checks, then applies the judgement checks a linter cannot. Use before every commit and before anything leaves the repository.
argument-hint: "[path or paste the text]"
allowed-tools: Read, Glob, Grep, Bash, Edit
---

# Claim check — before this leaves the building

Target: **$ARGUMENTS**

## Step 1 — the automated pass

```!
cd "${CLAUDE_PROJECT_DIR}" && python3 tools/ledger_check.py 2>&1 | head -40 || echo "(ledger_check not installed)"
```

Anything above is a hard finding. Fix it or add an explicit pragma with a reason — never
silence it without one.

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

## Output

A verdict — **SHIP** or **HOLD** — followed by a numbered list of every change required, each
with the exact replacement text. If SHIP, say in one line what the strongest claim in the
text is and what evidence backs it.
