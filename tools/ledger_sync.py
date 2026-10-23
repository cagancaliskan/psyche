#!/usr/bin/env python3
"""ledger_sync.py — regenerate the ledger's GENERATED fields from the captured run.

The generated fields are the ones nobody should ever type by hand: suite count,
assertion total, failure count, per-suite counts, and the capture's provenance.
They come from docs/TEST_OUTPUT.txt, which is itself produced by run_tests.py.

    python3 tools/ledger_sync.py              # write the ledger in place
    python3 tools/ledger_sync.py --check      # exit 1 if it would change (for CI)
    python3 tools/ledger_sync.py --diff       # show what would change, write nothing

Everything not marked GENERATED is left untouched, including key order, so the
diff after a sync is exactly the numbers and nothing else.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ledger_check import CaptureMalformed, LEDGER_REL, CAPTURE_REL, parse_capture  # noqa: E402


def sync(root: Path, mode: str) -> int:
    ledger_path = root / LEDGER_REL
    if not ledger_path.exists():
        print(f"ledger_sync: no ledger at {ledger_path}", file=sys.stderr)
        return 2

    try:
        cap = parse_capture(root)
    except CaptureMalformed as e:
        # BRICK 0e. ledger_sync WRITES the headline figure, so syncing from an
        # incomplete capture is how a wrong number becomes canonical. Refuse.
        print(f"ledger_sync: refusing to sync — {e}", file=sys.stderr)
        return 2
    if cap is None:
        print(f"ledger_sync: no capture at {root / CAPTURE_REL}", file=sys.stderr)
        return 2
    if cap["failures"]:
        print(f"ledger_sync: refusing to sync — the capture has "
              f"{cap['failures']} failure(s). Fix the suite, recapture, retry.",
              file=sys.stderr)
        return 2
    if not cap["per_suite"]:
        print("ledger_sync: the capture contains no RESULT lines; is it truncated?",
              file=sys.stderr)
        return 2

    raw = ledger_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    before = json.dumps(data.get("tests", {}), sort_keys=True)

    tests = data.setdefault("tests", {})
    tests["_GENERATED"] = ("by tools/ledger_sync.py from docs/TEST_OUTPUT.txt "
                           "— do not hand-edit")
    tests["suites"] = cap["suites"]
    tests["assertions"] = cap["assertions"]
    tests["failures"] = cap["failures"]
    tests["captured_at"] = cap["captured_at"]
    tests["captured_python"] = cap["captured_python"]
    tests["per_suite"] = dict(cap["per_suite"])

    after = json.dumps(tests, sort_keys=True)
    changed = before != after

    if mode == "check":
        if changed:
            print("ledger_sync: the ledger is STALE relative to the capture.")
            print(f"  capture: {cap['suites']} suites, {cap['assertions']} assertions, "
                  f"{cap['failures']} failures")
            print("  run: python3 tools/ledger_sync.py")
            return 1
        print("ledger_sync: the ledger is current.")
        return 0

    if mode == "diff":
        print(json.dumps({"would_write": tests}, indent=2, ensure_ascii=False))
        return 1 if changed else 0

    if not changed:
        print("ledger_sync: already current; nothing written.")
        return 0

    ledger_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"ledger_sync: wrote {LEDGER_REL} — "
          f"{cap['suites']} suites, {cap['assertions']} assertions, "
          f"{cap['failures']} failures (captured {cap['captured_at']}, "
          f"Python {cap['captured_python']})")
    return 0


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="exit 1 if a sync is needed")
    g.add_argument("--diff", action="store_true", help="print what would change")
    args = ap.parse_args(argv)
    mode = "check" if args.check else "diff" if args.diff else "write"
    return sync(Path(args.root).resolve(), mode)


if __name__ == "__main__":
    sys.exit(main())
