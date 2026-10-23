#!/usr/bin/env python3
"""PostToolUse hook — tell Claude immediately when an edit made a document inconsistent.

Staleness in this repository has always been discovered months later, by a human, by
accident. This closes the loop to seconds: edit a Markdown or Python file, and if that file
now disagrees with tools/ledger.json, the finding comes straight back into the conversation.

Only findings for the file that was just touched are reported, so the signal stays sharp.
Never blocks — PostToolUse fires after the write anyway, and a noisy guardrail gets disabled.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WATCHED_SUFFIXES = {".md", ".py", ".json"}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    root = Path(payload.get("cwd") or ".").resolve()
    if not (root / "tools" / "ledger_check.py").exists():
        return 0

    tool_input = payload.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("path") or ""
    if not target:
        return 0

    p = Path(target)
    if p.suffix.lower() not in WATCHED_SUFFIXES:
        return 0

    try:
        rel = p.resolve().relative_to(root).as_posix()
    except Exception:
        return 0

    try:
        r = subprocess.run(
            [sys.executable, "tools/ledger_check.py", "--quiet"],
            cwd=root, capture_output=True, text=True, timeout=25)
    except Exception:
        return 0

    if r.returncode != 1:
        return 0

    # keep only the findings that name the file just edited
    blocks, current = [], []
    for line in r.stdout.splitlines():
        if line.startswith("  [") and current:
            blocks.append("\n".join(current))
            current = [line]
        elif line.startswith("  ["):
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append("\n".join(current))

    mine = [b for b in blocks if rel in b]
    if not mine:
        return 0

    msg = (f"ledger_check: the edit to {rel} leaves "
           f"{len(mine)} inconsistency(ies) with tools/ledger.json.\n\n"
           + "\n".join(b.rstrip() for b in mine)
           + "\n\nFix these before moving on, or add an explicit pragma with a reason. "
             "Do not silence a finding to make the check pass — that is the same failure "
             "as weakening a test to make it green.")

    json.dump({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": msg,
    }}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
