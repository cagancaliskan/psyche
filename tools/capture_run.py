#!/usr/bin/env python3
"""capture_run.py — run the canonical suite across every interpreter, then capture.

BUG-0b1 established that a determinism claim is scoped to the environments it was checked
in. `run_tests.py` sweeps hash seeds; nothing swept interpreter versions, and a real
cross-process determinism failure lived in that gap for a month — invisible on CPython 3.12,
reproducible on 3.11.

This runs the whole suite under every CPython minor version it can find, requires them all
to agree, writes `docs/TEST_OUTPUT.txt` with a provenance header naming the swept set, and
syncs the ledger.

    python3 tools/capture_run.py                  # sweep, capture, sync
    python3 tools/capture_run.py --dry-run        # sweep only; write nothing
    python3 tools/capture_run.py --primary python3.12

The captured output comes from the primary interpreter (default: the newest found, or the
one named). The other interpreters must produce the same per-suite counts and the same
overall verdict, or the capture is refused.

Stdlib only.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CANDIDATES = ["python3.11", "python3.12", "python3.13", "python3.14", "python3.10"]
RESULT_RE = re.compile(r"RESULT:\s+(\d+)\s+passed,\s+(\d+)\s+failed")
SUITE_RE = re.compile(r"^#\s+(test_\S+\.py)\s*$", re.M)
HASH_SEEDS = [0, 1, 2, 3, 7, 42]


def discover() -> List[str]:
    found, seen = [], set()
    for name in CANDIDATES:
        path = shutil.which(name)
        if path and path not in seen:
            seen.add(path)
            found.append(name)
    return sorted(found, key=lambda n: tuple(int(x) for x in n[6:].split(".")))


def version_of(interp: str) -> str:
    try:
        r = subprocess.run([interp, "--version"], capture_output=True, text=True, timeout=20)
        return (r.stdout or r.stderr).strip()
    except Exception:
        return interp


def run_suite(interp: str, root: Path) -> Tuple[int, str]:
    env = dict(os.environ)
    env.pop("PYTHONHASHSEED", None)
    r = subprocess.run([interp, "run_tests.py"], cwd=root, env=env,
                       capture_output=True, text=True)
    return r.returncode, r.stdout


def parse(out: str) -> Dict[str, int]:
    """Map suite name -> passed count, in file order."""
    per: Dict[str, int] = {}
    current: Optional[str] = None
    for line in out.splitlines():
        m = SUITE_RE.match(line)
        if m:
            current = m.group(1)
            continue
        m = RESULT_RE.search(line)
        if m and current:
            per[current] = int(m.group(1))
            current = None
    return per


def totals(per: Dict[str, int]) -> Tuple[int, int]:
    return len(per), sum(per.values())


def header(interps: List[str], primary: str, per: Dict[str, int]) -> str:
    suites, assertions = totals(per)
    now = datetime.now(timezone.utc).astimezone()
    sweep = ", ".join(f"{i} ({version_of(i).split()[-1]})" for i in interps)
    return "\n".join([
        "=" * 70,
        "  NOUS — CAPTURED TEST OUTPUT (verbatim)",
        "=" * 70,
        f"Generated : {now.strftime('%Y-%m-%d %H:%M:%S %z')}",
        f"Machine   : {os.uname().sysname} {os.uname().release} {os.uname().machine}",
        f"Python    : {version_of(primary)}   (primary — this transcript)",
        f"Swept     : {sweep}",
        f"Hash seeds: {HASH_SEEDS}  (per-suite determinism probes, fresh interpreters)",
        f"Command   : python3 tools/capture_run.py   (wraps run_tests.py per interpreter)",
        "Note      : Built-in harness (not pytest); each suite prints RESULT: N passed,",
        "            M failed and exits non-zero on any failure. Every interpreter above",
        "            produced identical per-suite counts; a disagreement refuses capture.",
        f"            Totals: {suites} suites, {assertions} assertions, 0 failures.",
        "=" * 70,
        "",
    ])


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--primary", default="", help="interpreter whose transcript is captured")
    ap.add_argument("--dry-run", action="store_true", help="sweep only; write nothing")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not (root / "run_tests.py").exists():
        print(f"capture_run: no run_tests.py under {root}", file=sys.stderr)
        return 2

    interps = discover()
    if not interps:
        print("capture_run: found no python3.X interpreters", file=sys.stderr)
        return 2

    primary = args.primary or interps[-1]
    if primary not in interps:
        interps.append(primary)

    print(f"capture_run: sweeping {len(interps)} interpreter(s): {', '.join(interps)}")
    print(f"capture_run: primary (captured transcript): {primary}\n")

    outputs: Dict[str, Tuple[int, str, Dict[str, int]]] = {}
    for interp in interps:
        code, out = run_suite(interp, root)
        per = parse(out)
        s, a = totals(per)
        status = "PASS" if code == 0 else "FAIL"
        print(f"  {interp:<14} {status}   {s} suites, {a} assertions")
        outputs[interp] = (code, out, per)

    # every interpreter must agree, and all must pass
    failures = [i for i, (c, _, _) in outputs.items() if c != 0]
    if failures:
        print(f"\ncapture_run: REFUSING to capture — failing interpreter(s): "
              f"{', '.join(failures)}")
        for i in failures:
            tail = [ln for ln in outputs[i][1].splitlines() if "FAIL" in ln][:8]
            for ln in tail:
                print(f"    {i}: {ln.strip()}")
        return 1

    ref = outputs[primary][2]
    disagree = {i: p for i, (_, _, p) in outputs.items() if p != ref}
    if disagree:
        print("\ncapture_run: REFUSING to capture — interpreters disagree on counts.")
        print("  This is exactly the BUG-0b1 failure class: a property that holds on one")
        print("  interpreter and fails on another was never a property of the program.")
        for i, p in disagree.items():
            for name in sorted(set(p) | set(ref)):
                if p.get(name) != ref.get(name):
                    print(f"    {name}: {primary}={ref.get(name)} {i}={p.get(name)}")
        return 1

    suites, assertions = totals(ref)
    print(f"\ncapture_run: all interpreters agree — {suites} suites, "
          f"{assertions} assertions, 0 failures")

    if args.dry_run:
        print("capture_run: --dry-run, nothing written")
        return 0

    out_path = root / "docs" / "TEST_OUTPUT.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header(interps, primary, ref) + outputs[primary][1],
                        encoding="utf-8")
    print(f"capture_run: wrote {out_path.relative_to(root)}")

    # keep the ledger's determinism block truthful about what was actually swept
    ledger_path = root / "tools" / "ledger.json"
    if ledger_path.exists():
        import json
        d = json.loads(ledger_path.read_text(encoding="utf-8"))
        d.setdefault("determinism", {})["interpreters_swept"] = [i[6:] for i in interps]
        d["determinism"]["hash_seeds"] = HASH_SEEDS
        ledger_path.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        print("capture_run: updated determinism.interpreters_swept")

    r = subprocess.run([sys.executable, "tools/ledger_sync.py"], cwd=root)
    if r.returncode != 0:
        return r.returncode
    print("\ncapture_run: now run  python3 tools/ledger_check.py  "
          "and fix any document the new counts contradict.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
