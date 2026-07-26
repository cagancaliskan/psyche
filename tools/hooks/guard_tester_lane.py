#!/usr/bin/env python3
"""PreToolUse hook — keep the tester out of the code it certifies, and out of the ledger.

Two separate protections, both learned the hard way.

1. FILES. The separation of duties is this project's primary evidence mechanism: "the role
   which writes a mechanism is never the role that certifies it." A tester that patches src/
   to make its own test pass voids the verification of everything it touched, and nothing in
   the transcript would show it.

2. CLAIM-BEARING TOOLS. capture_run.py and ledger_sync.py move the canonical assertion count.
   That count is a claim, and moving it is not the tester's to do — the same reason
   run_tests.py is off-limits. On 2026-07-25 a tester ran capture_run and produced a capture
   that omitted an unregistered suite; the ledger then recorded an under-reported total that
   was internally consistent and wrong. That was not a mistake inside a correct workflow, it
   was a tool in the wrong hands (D-016). Capture and sync belong to architect-pm, after the
   tester hands off.

Wired into the tester agent's frontmatter, so it applies to that lane only.
Exit 2 blocks the tool call and shows stderr to Claude.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FORBIDDEN_PREFIXES = ("src/",)
FORBIDDEN_EXACT = (
    "run_tests.py",          # controls what the canonical count includes
    "CLAUDE.md",
    "tools/ledger.json",     # the claim-bearing fact base
    "docs/TEST_OUTPUT.txt",  # the capture the ledger is generated from
)
FORBIDDEN_TOOLS = ("capture_run.py", "ledger_sync.py")

HANDBACK = (
    "If you have found a defect: report it precisely — the exact failing input, expected vs\n"
    "actual, and your best read on the root cause — and hand back. Fixing or re-labelling the\n"
    "thing you are testing reintroduces exactly the circularity this project exists to avoid.\n"
)


def block(msg: str) -> int:
    sys.stderr.write(f"LANE VIOLATION — blocked.\n\nYou are in the tester lane. {msg}\n")
    return 2


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = payload.get("tool_input") or {}
    root = Path(payload.get("cwd") or ".").resolve()

    # ── claim-bearing tools, invoked through the shell ───────────────────────
    command = tool_input.get("command") or ""
    if command:
        for tool in FORBIDDEN_TOOLS:
            if re.search(rf"\b{re.escape(tool)}\b", command):
                return block(
                    f"You may not run {tool}. It moves the canonical assertion count, which is\n"
                    f"a claim, and claims are not the tester's to move — the same reason\n"
                    f"run_tests.py is off-limits to you.\n\n"
                    f"Finish your verdict and hand off. architect-pm runs capture and sync as\n"
                    f"its own step, after your suite is registered. See DECISIONS D-016.\n")
        return 0

    # ── files ────────────────────────────────────────────────────────────────
    target = tool_input.get("file_path") or tool_input.get("path") or ""
    if not target:
        return 0
    try:
        rel = Path(target).resolve().relative_to(root).as_posix()
    except Exception:
        return 0

    if rel in FORBIDDEN_EXACT or any(rel.startswith(p) for p in FORBIDDEN_PREFIXES):
        return block(
            f"You may create and edit test files and harnesses only\n"
            f"(tests/test_tester_*.py). You may not modify {rel}.\n\n{HANDBACK}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
