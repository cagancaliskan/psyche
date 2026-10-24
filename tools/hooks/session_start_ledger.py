#!/usr/bin/env python3
"""SessionStart hook — inject the true project state into every new session.

Claude Code sessions start with no memory. Documents in this repository are known to be
stale (four different assertion counts across five files). So rather than let a session
absorb whatever a document happens to say, this injects the ledger's facts directly at
session start, before anything is read.

Since D-031 it opens with the program state (what is being worked on: Psyche paused, the
thesis active) and the thesis plan's current phase, next gate and next deadline, read from
tools/thesis_plan.json, the only source of thesis dates. Days left are counted from today in
the plan's own timezone. That count lives only here and in /psyche-orient, never in a
rendered document, so the documents stay deterministic.

Reads the hook payload on stdin (as bytes, decoded as UTF-8 whatever the locale says: this
checkout's path is not ASCII), writes JSON on stdout. Never blocks: any failure here is
reported as a note, not an error, because a broken hook must not make the repo unusable. A
malformed program entry or plan costs one note line; it never costs the rest of the briefing.
A program block that is not an object is such a note, and so is a gate or deadline date that
cannot be read ("date unreadable"), which is never shown as a date that was not set.
"""

from __future__ import annotations

import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def project_dir() -> Path:
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    cwd = payload.get("cwd")
    return Path(cwd if isinstance(cwd, str) and cwd else ".").resolve()


def program_lines(d: dict) -> List[str]:
    """`psyche: paused since 2026-10-23 (D-031) · thesis: active`, from ledger.program.

    No line when the ledger has no program block (a ledger from before D-031). A block that is
    present but not an object, or that names no program, costs one note line: dropping it
    would let the briefing read as if no program state were recorded."""
    if "program" not in d:
        return []
    prog = d.get("program")
    if not isinstance(prog, dict):
        return ["  program      unreadable (expected an object in tools/ledger.json program, "
                f"found {type(prog).__name__})"]
    parts = []
    for name, v in prog.items():
        if str(name).startswith("_"):
            continue
        if not isinstance(v, dict):
            parts.append(f"{name}: unreadable entry (expected an object)")
            continue
        state = v.get("state") or "unknown"
        part = f"{name}: {state}"
        if state != "active":
            if v.get("since"):
                part += f" since {v['since']}"
            if v.get("decision"):
                part += f" ({v['decision']})"
        parts.append(part)
    if not parts:
        return ["  program      no entries (tools/ledger.json program names no program)"]
    out = [f"  program      {' · '.join(parts)}"]
    ps = prog.get("psyche")
    if isinstance(ps, dict) and ps.get("state") == "paused":
        out.append("               no new Psyche brick starts and no default changes while "
                   "paused; only Cagan resumes it")
    return out


def _today(tz_name: Optional[str]) -> Tuple[_dt.date, str]:
    """Today in the plan's zone, and the note to print beside it. Falls back to local time,
    and says so, in the words render_plan.today_in_zone uses."""
    if not tz_name:
        return _dt.date.today(), "local time; the plan names no zone"
    try:
        from zoneinfo import ZoneInfo
        return _dt.datetime.now(ZoneInfo(tz_name)).date(), str(tz_name)
    except Exception:
        return _dt.date.today(), f"local time; no zone data for {tz_name}"


def _date(s) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(s) if isinstance(s, str) else None
    except ValueError:
        return None


def _when(value, unset: str, today: _dt.date) -> str:
    """A gate's or deadline's date with its countdown. A missing date and a malformed one are
    told apart: "date not set" would hide that a date was recorded and cannot be read."""
    if value is None or value == "":
        return f"date not set{unset}"
    due = _date(value)
    if due is None:
        return f"date unreadable ({value!r}; expected YYYY-MM-DD)"
    return f"{due.isoformat()}, {_countdown(due, today)}"


def _countdown(due: _dt.date, today: _dt.date) -> str:
    n = (due - today).days
    if n > 1:
        return f"{n} days left"
    if n == 1:
        return "1 day left"
    if n == 0:
        return "due today"
    return f"{-n} day(s) past its date"


def plan_lines(root: Path) -> List[str]:
    """Current phase, next gate and next deadline from tools/thesis_plan.json."""
    path = root / "tools" / "thesis_plan.json"
    if not path.exists():
        return []
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"  thesis plan  tools/thesis_plan.json could not be parsed ({e})"]

    try:
        today, zone_note = _today(plan.get("timezone"))
        out = [f"  thesis plan  tools/thesis_plan.json, today {today.isoformat()} ({zone_note})"]

        phases = [p for p in plan.get("phases") or [] if isinstance(p, dict)]
        cur = next((p for p in phases if p.get("status") == "active"), None)
        if cur is None:
            cur = next((p for p in phases
                        if _date(p.get("start")) and _date(p.get("end"))
                        and _date(p["start"]) <= today <= _date(p["end"])), None)
        if cur is not None:
            start = cur.get("start") or cur.get("start_rule") or "?"
            end = cur.get("end") or cur.get("end_rule") or "?"
            gate = f", ends at gate {cur['gate']}" if cur.get("gate") else ""
            out.append(f"    phase      {cur.get('id')} {cur.get('title')}: "
                       f"{start} to {end} ({cur.get('status')}{gate})")
        else:
            out.append("    phase      none active")

        gates = [g for g in plan.get("gates") or [] if isinstance(g, dict)]
        nxt = next((g for g in gates if g.get("status") == "upcoming"), None)
        if nxt is not None:
            when = _when(nxt.get("date"),
                         f": {nxt.get('date_rule') or 'no rule recorded'}", today)
            out.append(f"    next gate  {nxt.get('id')} {nxt.get('title')}: {when}")
        else:
            out.append("    next gate  none upcoming")

        dls = [x for x in plan.get("deadlines") or [] if isinstance(x, dict)]
        dl = next((x for x in dls if x.get("status") == "upcoming"), None)
        if dl is not None:
            when = _when(dl.get("due"), f" (estimate: {dl.get('estimate') or 'none'})", today)
            out.append(f"    deadline   {dl.get('id')}: {when}")
        return out
    except Exception as e:
        return [f"  thesis plan  tools/thesis_plan.json could not be read ({e})"]


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
        "PSYCHE — canonical state, read from tools/ledger.json at session start.",
        "These numbers override anything a document in this repository says.",
        "",
    ]
    try:
        head = program_lines(d)
    except Exception as e:
        head = [f"  program      could not be read ({type(e).__name__}: {e})"]
    try:
        head += plan_lines(root)
    except Exception as e:
        head += [f"  thesis plan  tools/thesis_plan.json could not be read ({e})"]
    if head:
        lines += head + [""]
    lines += [
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
        if r.returncode == 2:
            first = "tool error (exit 2); run it by hand"
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
    try:
        ctx = build_context(root)
    except Exception as e:  # the last net: say so, never fail the session start
        ctx = (f"PSYCHE LEDGER: the session-start briefing could not be built "
               f"({type(e).__name__}: {e}). Run /psyche-orient, and "
               f"`python3 tools/ledger_check.py` for the ledger's own verdict.")
    if ctx:
        json.dump({"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": ctx,
        }}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
