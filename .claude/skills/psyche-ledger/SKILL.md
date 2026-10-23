---
name: psyche-ledger
description: Read or update the Psyche fact ledger — the single source of truth for test counts, brick statuses, constants and results. Use whenever you need a number, whenever a suite is re-captured, and whenever a brick changes status. Never quote a count from a document; quote it from here.
argument-hint: "[show|sync|status <brick> <STATUS>|check]"
allowed-tools: Read, Edit, Bash
---

# The ledger

`tools/ledger.json` is the single source of truth for every fact this project quotes.
Prose cites the ledger; the ledger never cites prose.

It exists because this repository has shipped **four different assertion counts across five
documents** — 618 in `README.md`, 130 in `docs/outreach/`, 1,372 in the claim inventory and
the capture. Nothing caught it, because nothing checked prose against fact.

Request: **$ARGUMENTS**

## Current contents

```!
cd "${CLAUDE_PROJECT_DIR}" && python3 - <<'PY' 2>/dev/null || echo "(no ledger)"
import json,pathlib
d=json.loads(pathlib.Path("tools/ledger.json").read_text())
t=d["tests"]
print(f"tests        {t['suites']} suites / {t['assertions']} assertions / {t['failures']} failures")
print(f"             captured {t['captured_at']}, Python {t['captured_python']}")
det=d["determinism"]
print(f"determinism  seeds {det['hash_seeds']}")
print(f"             swept {det['interpreters_swept']}  required {det['interpreters_required']}")
print("bricks")
for k,v in d["bricks"].items():
    print(f"             {k:<10} {v['status']}")
print("uncalibrated constants")
for k,v in d["uncalibrated_constants"].items():
    print(f"             {k} = {v}")
PY
```

## Operations

**`show`** — the block above. That is the whole answer; do not go looking in documents.

**`check`** — run all four staleness checks:
```
python3 tools/ledger_check.py
```
C1 ledger vs capture · C2 prose counts vs ledger · C3 status labels · C4 forbidden claims.
Exit 0 clean, 1 findings, 2 tool error.

**`sync`** — after capturing a new test run to `docs/TEST_OUTPUT.txt`:
```
python3 tools/ledger_sync.py          # rewrite the GENERATED fields
python3 tools/ledger_check.py         # then confirm the docs agree
```
`ledger_sync` refuses to sync from a capture containing failures. That is deliberate.

**`status <brick> <STATUS>`** — change a brick's status. This is **not** a routine edit:

1. The new status must be in `valid_statuses`.
2. Append an entry to `DECISIONS.md` first: date, what changed, the evidence, who decided.
   A status change with no decision record is a status change nobody can audit.
3. Then edit `tools/ledger.json`.
4. Then run `ledger_check` and fix every document the change now contradicts.

## The two axes — do not conflate them

**Build status** (is the code written and verified): `PROVEN`, `BUILT-UNVALIDATED`,
`DESIGNED`, `HORIZON`.

**Meaning verdict** (did an external yardstick grade it): `NO-GO`, `NOT-YET`, `EARNED`.

A brick is routinely both at once. **2c is `BUILT-UNVALIDATED` and its meaning verdict is
`NOT-YET`** — mechanism tester-PASS on 350 adversarial assertions, and a dead yardstick.
Those are not in tension; they are different questions.

## Hard rules

- **Never estimate a count.** If you need one and the ledger does not have it, capture a run
  and sync. Do not compute it from a document.
- **Never hand-edit the `tests` block.** It is generated. `ledger_sync.py` owns it.
- **Never silence a finding without a pragma and a reason.** `<!-- ledger:allow-count -->`
  and `<!-- ledger:allow-claim -->` exist for genuine cases — a labelled historical figure,
  a quotation of a vision document. Using them to make a check pass is the same failure as
  weakening a test to make it green.
- **A determinism claim is scoped to the interpreters it was swept on.** If
  `interpreters_swept` is shorter than `interpreters_required`, say so wherever the claim
  appears.
