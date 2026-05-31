"""
Phase 2B — Pre-registered graded semantic-priming study on SWOW-EN.

╔══════════════════════════════════════════════════════════════════════════════╗
║ PRE-REGISTERED PREDICTIONS  (fixed BEFORE any activation is computed; printed   ║
║ to stdout by print_preregistration() as the FIRST thing main() does).          ║
║                                                                                ║
║ P1  SANITY / INSTRUMENT CHECK (NOT the cognitive result):                       ║
║     Within DIRECT pairs, higher SWOW association strength -> higher target      ║
║     activation. This should pass almost by construction; if it FAILS, the       ║
║     graph-building pipeline is broken (not an interesting finding).             ║
║                                                                                ║
║ P2  THE REAL TEST:                                                              ║
║     Target activation ordering  DIRECT > MEDIATED > UNRELATED.                  ║
║     Pre-stated interpretation of each possible outcome:                         ║
║       * full ordering holds            -> graded priming reproduced;            ║
║       * DIRECT>UNRELATED, MEDIATED≈UNRELATED -> direct priming only (this is    ║
║         the human pattern: mediated priming is weak/unreliable);               ║
║       * flat                           -> no priming; an informative null about  ║
║         a pure spreading-activation account.                                    ║
║                                                                                ║
║ CRITICAL HONEST CONTROL (stated up front):                                      ║
║     DIRECT > MEDIATED is PARTLY MECHANICAL — decay_per_hop attenuates a 2-hop   ║
║     path more than a 1-hop path regardless of meaning (same effect as the 2A    ║
║     fan sanity check). Therefore the PRIMARY COGNITIVE CONTRAST is              ║
║     MEDIATED vs UNRELATED: does activation through a REAL 2-step associative     ║
║     path exceed activation to an unrelated node, beyond what hop-distance alone  ║
║     forces? The analysis is centered on this contrast; DIRECT>MEDIATED is       ║
║     labeled partly distance-driven.                                             ║
║                                                                                ║
║ READOUT (locked):                                                               ║
║     PRIMARY   = raw target activation (harness.retrieval_strength instrument,   ║
║                 amortized via harness.read_targets — one spread, many reads).    ║
║     SECONDARY = normalized: target activation / prime's total outgoing          ║
║                 activation. Reported, clearly labeled; not the primary metric.   ║
╚══════════════════════════════════════════════════════════════════════════════╝

Substrate, mapping, and selection are all pre-registered in swow.py / EXPERIMENT_NOTES.md
and fixed before this runs. Conditions are chosen BLIND from SWOW topology + strength only,
never from any activation result (anti-circularity). The engine is the frozen library,
imported unchanged; nothing here modifies it. Verdicts are computed from the data.

Run:
    python3 experiments/priming.py
Optional env (used by the determinism test for a reduced-but-faithful run):
    NOUS_PRIMING_MAXROWS=<int>   cap edges loaded (default: all)
    NOUS_PRIMING_NPRIMES=<int>   number of primes (default: 300)
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import swow
from harness import build_graph_from_spec, read_targets

# ── pre-registered run parameters (locked) ───────────────────────────────────────────
N_PRIMES = int(os.environ.get("NOUS_PRIMING_NPRIMES", "300"))
SELECTION_SEED = 20250531          # fixed; selection is deterministic given this
K_UNRELATED = swow.PRIMING_K_UNRELATED   # = 4 (no path within 4 hops)
MAXROWS = os.environ.get("NOUS_PRIMING_MAXROWS")  # None unless reduced run
MAXROWS = int(MAXROWS) if MAXROWS else None

EPS = 1e-9

PRED_P1 = ("P1 SANITY (instrument check, NOT the cognitive result): within DIRECT pairs, "
           "higher SWOW association strength -> higher target activation.")
PRED_P2 = ("P2 REAL TEST: target activation ordering DIRECT > MEDIATED > UNRELATED.")
PRED_PRIMARY = ("PRIMARY COGNITIVE CONTRAST: MEDIATED vs UNRELATED — does a real 2-step "
                "associative path beat an unrelated node beyond what hop-distance forces? "
                "(DIRECT>MEDIATED is partly mechanical: decay attenuates 2 hops > 1 hop.)")


# ─────────────────────────────────────────────────────────────────────────────
# Pre-registration banner — PRINTED BEFORE ANY RESULT IS COMPUTED
# ─────────────────────────────────────────────────────────────────────────────

def print_preregistration() -> None:
    print("=" * 78)
    print("PHASE 2B — GRADED SEMANTIC PRIMING ON SWOW-EN — pre-registered")
    print("=" * 78)
    print("PRE-REGISTERED PREDICTIONS (fixed before any activation computed):")
    print("  " + PRED_P1)
    print("  " + PRED_P2)
    print("  " + PRED_PRIMARY)
    print()
    print("READOUT: PRIMARY = raw target activation (harness.read_targets / retrieval_strength).")
    print("         SECONDARY = normalized (target activation / prime outgoing total).")
    print()
    print("SUBSTRATE: full SWOW-EN graph; edge traverse_count = min(%d, 1+floor(strength*%d));"
          % (swow.STRENGTH_CAP, swow.STRENGTH_SCALE))
    print("           Clock(simulated=True); library default activation knobs.")
    print("CONDITIONS (BLIND, topology+strength only, seed=%d):" % SELECTION_SEED)
    print("           DIRECT=1-hop response; MEDIATED=2-hop & not direct;")
    print("           UNRELATED=in-degree>0 & no path within K=%d hops." % K_UNRELATED)
    print("A null/flat result is an honest finding; verdicts below are computed from data.")
    print("=" * 78)
    print()
    sys.stdout.flush()


# ─────────────────────────────────────────────────────────────────────────────
# Stats helpers (pure stdlib, deterministic)
# ─────────────────────────────────────────────────────────────────────────────

def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _median(xs):
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    m = n // 2
    return s[m] if n % 2 else (s[m - 1] + s[m]) / 2.0


def _ranks(xs):
    """Average ranks (1-based), ties averaged. Deterministic."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # average of 1-based ranks i+1..j+1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _spearman(xs, ys):
    """Spearman rank correlation (Pearson on ranks). Returns 0.0 if undefined."""
    if len(xs) < 2:
        return 0.0
    rx = _ranks(xs)
    ry = _ranks(ys)
    mx = _mean(rx)
    my = _mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx)
    dy = sum((b - my) ** 2 for b in ry)
    if dx <= 0 or dy <= 0:
        return 0.0
    return num / (dx * dy) ** 0.5


# ─────────────────────────────────────────────────────────────────────────────
# The experiment
# ─────────────────────────────────────────────────────────────────────────────

def measure(pairs, inst):
    """For each prime: one spread, read DIRECT/MEDIATED/UNRELATED targets. Pure read.
    Returns lists keyed by condition plus per-prime records for the within-prime sign test."""
    ids = inst.ids
    raw = {"direct": [], "mediated": [], "unrelated": []}
    norm = {"direct": [], "mediated": [], "unrelated": []}
    direct_strengths = []
    per_prime = []  # (mediated_raw, unrelated_raw) for the sign test
    for d in pairs:
        cue = ids[d["prime"]]
        td, tm, tu = ids[d["direct"]], ids[d["mediated"]], ids[d["unrelated"]]
        res = read_targets(inst.store, cue, [td, tm, tu])
        a = res["activation"]
        denom = res["outgoing_total"] if res["outgoing_total"] > 0 else 1.0
        dv, mv, uv = a[td], a[tm], a[tu]
        raw["direct"].append(dv); raw["mediated"].append(mv); raw["unrelated"].append(uv)
        norm["direct"].append(dv / denom); norm["mediated"].append(mv / denom); norm["unrelated"].append(uv / denom)
        direct_strengths.append(d["direct_strength"])
        per_prime.append((mv, uv))
    return raw, norm, direct_strengths, per_prime


def _fmt_row(name, xs):
    nz = sum(1 for x in xs if x > 0)
    return ("  %-9s  N=%-4d  mean=%.6f  median=%.6f  min=%.6f  max=%.6f  nonzero=%d/%d"
            % (name, len(xs), _mean(xs), _median(xs), min(xs), max(xs), nz, len(xs)))


def print_table(raw, norm):
    print("RESULT — RAW target activation by condition (PRIMARY readout):")
    for c in ("direct", "mediated", "unrelated"):
        print(_fmt_row(c.upper(), raw[c]))
    print()
    print("RESULT — NORMALIZED activation (SECONDARY: share of prime's outgoing total):")
    for c in ("direct", "mediated", "unrelated"):
        print(_fmt_row(c.upper(), norm[c]))
    print()


def print_primary_contrast(raw, per_prime):
    med = raw["mediated"]
    unr = raw["unrelated"]
    n = len(per_prime)
    gt = sum(1 for m, u in per_prime if m > u + EPS)
    eq = sum(1 for m, u in per_prime if abs(m - u) <= EPS)
    lt = n - gt - eq
    print("PRIMARY CONTRAST — MEDIATED vs UNRELATED (the cognitive test):")
    print("  mean:   MEDIATED=%.6f   UNRELATED=%.6f   diff=%.6f"
          % (_mean(med), _mean(unr), _mean(med) - _mean(unr)))
    print("  median: MEDIATED=%.6f   UNRELATED=%.6f" % (_median(med), _median(unr)))
    print("  within-prime sign test (N=%d): MEDIATED>UNRELATED in %d, equal in %d, < in %d"
          % (n, gt, eq, lt))
    print("  nonzero: MEDIATED=%d/%d  UNRELATED=%d/%d"
          % (sum(1 for x in med if x > 0), n, sum(1 for x in unr if x > 0), n))
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Verdicts — computed from the data
# ─────────────────────────────────────────────────────────────────────────────

def verdict_p1(direct_strengths, direct_raw):
    rho = _spearman(direct_strengths, direct_raw)
    ok = rho > 0.0
    line = ("P1 VERDICT: %s — Spearman(strength, direct activation) rho=%.4f"
            % ("PASS (instrument sane)" if ok else "FAIL (graph build broken)", rho))
    return ok, rho, line


def verdict_p2(raw):
    md = _median(raw["direct"]); mm = _median(raw["mediated"]); mu = _median(raw["unrelated"])
    # use medians (robust); also check means agree on ordering
    full = md > mm + EPS and mm > mu + EPS
    direct_only = md > mu + EPS and abs(mm - mu) <= EPS
    flat = abs(md - mu) <= EPS and abs(mm - mu) <= EPS
    if full:
        v = "MATCHES: full ordering DIRECT > MEDIATED > UNRELATED — graded priming reproduced."
    elif direct_only:
        v = ("PARTIAL: DIRECT > UNRELATED but MEDIATED ~= UNRELATED — direct priming only "
             "(consistent with weak human mediated priming).")
    elif flat:
        v = "NULL: flat across conditions — no priming (informative null)."
    else:
        v = ("OTHER: ordering does not match any pre-stated pattern cleanly; "
             "see table (medians D=%.6f M=%.6f U=%.6f)." % (md, mm, mu))
    return v, (md, mm, mu)


def verdict_primary(per_prime):
    n = len(per_prime)
    gt = sum(1 for m, u in per_prime if m > u + EPS)
    frac = gt / n if n else 0.0
    med = _median([m for m, _ in per_prime]); unr = _median([u for _, u in per_prime])
    beats = med > unr + EPS
    line = ("PRIMARY VERDICT: MEDIATED %s UNRELATED — median %.6f vs %.6f; "
            "MEDIATED>UNRELATED in %d/%d primes (%.1f%%)."
            % (">" if beats else "~=/<", med, unr, gt, n, 100 * frac))
    return beats, line


# ─────────────────────────────────────────────────────────────────────────────
# Pair-list persistence (auditable selection)
# ─────────────────────────────────────────────────────────────────────────────

def save_pair_lists(pairs, outdir):
    os.makedirs(outdir, exist_ok=True)
    # DIRECT with strength; MEDIATED and UNRELATED plain prime->target
    with open(os.path.join(outdir, "priming_pairs_direct.txt"), "w", encoding="utf-8") as fh:
        fh.write("# prime\tdirect_target\tswow_strength\n")
        for d in pairs:
            fh.write("%s\t%s\t%s\n" % (d["prime"], d["direct"], repr(d["direct_strength"])))
    with open(os.path.join(outdir, "priming_pairs_mediated.txt"), "w", encoding="utf-8") as fh:
        fh.write("# prime\tmediated_target\n")
        for d in pairs:
            fh.write("%s\t%s\n" % (d["prime"], d["mediated"]))
    with open(os.path.join(outdir, "priming_pairs_unrelated.txt"), "w", encoding="utf-8") as fh:
        fh.write("# prime\tunrelated_target\n")
        for d in pairs:
            fh.write("%s\t%s\n" % (d["prime"], d["unrelated"]))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    # 1) PRE-REGISTRATION FIRST.
    print_preregistration()

    # 2) Load data + select pairs BLIND (topology only), before any spread.
    try:
        edges = swow.load_edges()
    except swow.SwowMissing as e:
        print("DATA NOT AVAILABLE — cannot compute results.\n")
        print(str(e))
        print("\n(The pre-registered predictions above stand; rerun with the data present.)")
        return 2
    if MAXROWS is not None:
        edges = edges[:MAXROWS]
    print("loaded %d directed edges (strength>0, no self-loops)%s."
          % (len(edges), "" if MAXROWS is None else " [REDUCED: first %d]" % MAXROWS))

    topo = swow.Topology(edges)
    pairs = swow.select_pairs(topo, N_PRIMES, seed=SELECTION_SEED, k_unrelated=K_UNRELATED)
    print("selected %d primes (one DIRECT/MEDIATED/UNRELATED target each), BLIND to activation."
          % len(pairs))
    print("N per condition = %d." % len(pairs))
    print()

    outdir = os.path.join(_HERE, "results")
    save_pair_lists(pairs, outdir)

    # 3) Build the frozen-library substrate ONCE.
    spec = swow.build_spec(edges)
    inst = build_graph_from_spec(spec)
    print("substrate built: %d nodes, %d roads (Clock simulated)."
          % (inst.store.node_count(), inst.store.road_count()))
    print()

    # 4) Measure (one pure-read spread per prime).
    raw, norm, direct_strengths, per_prime = measure(pairs, inst)

    # 5) Tables + contrasts.
    print_table(raw, norm)
    print_primary_contrast(raw, per_prime)

    # 6) Verdicts from data.
    print("VERDICTS (computed from the data above):")
    ok1, rho, line1 = verdict_p1(direct_strengths, raw["direct"])
    print("  " + line1)
    v2, meds = verdict_p2(raw)
    print("  P2 VERDICT: " + v2)
    _, linep = verdict_primary(per_prime)
    print("  " + linep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
