#!/usr/bin/env python3
"""SessionStart hook — inject the true project state into every new session.

Claude Code sessions start with no memory. Documents in this repository are known to be
stale (four different assertion counts across five files). So rather than let a session
absorb whatever a document happens to say, this injects the ledger's facts directly at
session start, before anything is read.

Reads the hook payload on stdin, writes JSON on stdout. Never blocks: any failure here is
reported as a note, not an error, because a broken hook must not make the repo unusable.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def project_dir() -> Path:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    cwd = payload.get("cwd") or "."
    return Path(cwd).resolve()


def build_context(root: Path) -> str:
    ledger_path = root / "tools" / "ledger.json"
    if not ledger_path.exists():
        return ""

    try:
        d = json.loads(ledger_path.read_text(encoding="utf-8"))
    except Exception as e:  # malformed ledger is itself worth saying out loud
        return f"PSYCHE LEDGER: tools/ledger.json could not be parsed ({e})."

    t = d.get("tests", {})
    det = d.get("determinism", {})
    mb = d.get("meaning_bar", {})

    lines = [
        "PSYCHE / NOUS — canonical state, read from tools/ledger.json at session start.",
        "These numbers override anything a document in this repository says.",
        "",
        f"  tests        {t.get('suites')} suites, {t.get('assertions')} assertions, "
        f"{t.get('failures')} failures "
        f"(captured {t.get('captured_at')}, Python {t.get('captured_python')})",
        f"  determinism  hash seeds {det.get('hash_seeds')}; "
        f"interpreters swept {det.get('interpreters_swept')} "
        f"of required {det.get('interpreters_required')}",
        f"  meaning bar  {mb.get('status')} — "
        + ", ".join(f"{a['id']} ({a['wall']})" for a in mb.get("attempts", [])),
        "",
        "  bricks:",
    ]
    for k, v in (d.get("bricks") or {}).items():
        note = f"  — {v['note']}" if v.get("note") else ""
        lines.append(f"    {k:<10} {v.get('status'):<28} {v.get('name')}{note}")

    # staleness, cheap enough to run every session
    try:
        r = subprocess.run(
            [sys.executable, "tools/ledger_check.py", "--quiet"],
            cwd=root, capture_output=True, text=True, timeout=20)
        first = (r.stdout.strip().splitlines() or ["clean"])[0]
        lines += ["", f"  ledger_check: {first if r.returncode else 'clean'}"]
        if r.returncode == 1:
            lines.append("  (run `python3 tools/ledger_check.py` for the list)")
    except Exception:
        pass

    lines += [
        "",
        "  Rules that govern every action here: mechanism is not meaning; PROVEN and",
        "  DESIGNED stay in separate boxes; external yardsticks never self-authored",
        "  inputs; docs/design/ is aspirational vision, not built code. Run /psyche-orient",
        "  for the full briefing and /psyche-lane before touching a file.",
    ]
    return "\n".join(lines)


def main() -> int:
    root = project_dir()
    ctx = build_context(root)
    if ctx:
        json.dump({"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": ctx,
        }}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
