#!/usr/bin/env python3
"""PreToolUse hook — stop the tester from editing the code it is testing.

The separation of duties is this project's primary evidence mechanism. Its paper's central
claim is that "the role which writes a mechanism is never the role that certifies it." If
the tester patches src/ to make its own test pass, the verification of everything it touched
becomes worthless — and nothing in the transcript would show it happened.

Wired into the tester agent's frontmatter, so it applies to that lane only.

Exit 2 blocks the tool call and shows stderr to Claude.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# the tester owns tests and harnesses; everything else in these trees is off-limits
FORBIDDEN_PREFIXES = ("src/",)
FORBIDDEN_EXACT = ("run_tests.py", "CLAUDE.md")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = payload.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("path") or ""
    if not target:
        return 0

    root = Path(payload.get("cwd") or ".").resolve()
    try:
        rel = Path(target).resolve().relative_to(root).as_posix()
    except Exception:
        return 0

    blocked = rel in FORBIDDEN_EXACT or any(
        rel.startswith(pref) for pref in FORBIDDEN_PREFIXES)
    if not blocked:
        return 0

    sys.stderr.write(
        f"LANE VIOLATION — blocked.\n\n"
        f"You are in the tester lane. You may create and edit test files and harnesses "
        f"only ({', '.join(['tests/test_tester_*.py'])}). You may not modify {rel}.\n\n"
        f"If you have found a defect: report it precisely — the exact failing input, "
        f"expected vs actual, and your best read on the root cause — and hand back to the "
        f"builder. Fixing the thing you are testing reintroduces exactly the circularity "
        f"this project exists to avoid, and it silently voids the verification of "
        f"everything it touches.\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
