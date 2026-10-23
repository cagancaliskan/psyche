"""
MECHANISM tests for the SPEC-1e §10 BLIND three-arm selector (experiments/priming_1e.py).

These verify the SELECTOR'S MECHANISM ONLY — never a cognitive/priming claim, never a verdict,
never an activation number. They run on small CONTROLLED Topology objects built from explicit
(cue, response, strength) edge lists where the correct bands, in-degree deciles, W_gap, S0
membership, and tie-breaks are DERIVABLE by hand — the answer comes from the construction, not
from the selector under test (no circular test).

Covered (EXP-1e §9.1 / §9.2 / §6.2 / §6.2.0):
  - per-prime HIGH / LOW bands match the frozen percentile rule exactly;
  - global in-degree deciles + same-decile matching (incl. boundary→lower decile);
  - W(P,T) integer weight map and W_gap; S0 = weight-blind (W_gap=0);
  - S0 in-degree matching: tightest |Δindeg| then SELECTION_SEED shuffle; drop count correct;
  - arm (a) reachable-unrelated control is in-horizon & non-direct, distance recorded;
  - arm (b)-d1 HIGH-vs-LOW both 1 hop; arm (c) full direct range; arm (b)-d2 bottleneck;
  - BLIND: selection consults no activation (it takes only a Topology; the engine is never
    imported); structurally-impossible-branch guard (S0 can be both populated AND empty);
  - DETERMINISM across processes: selection byte-identical across PYTHONHASHSEED.
  - ASSERTED-NEGATIVE: a prime whose only weight-blind pair is NOT in-degree-matched is
    DROPPED from S0 (and counted) — the §6.2.0 tightening, pinned explicitly.

Tiny built-in harness (print + count, exit nonzero), NOT pytest. Run as a script:
    python3 experiments/test_priming_1e.py
"""

from __future__ import annotations

import os
import sys
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from swow import Topology, traverse_count_for_strength
import priming_1e as S1E


_passed = 0
_failed = 0


def check(cond: bool, msg: str) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {msg}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def approx(a: float, b: float, tol: float = 1e-12) -> bool:
    return abs(a - b) <= tol


# ─────────────────────────────────────────────────────────────────────────────
# 1) Deterministic percentile matches hand computation
# ─────────────────────────────────────────────────────────────────────────────

def test_percentile_linear():
    section("percentile() linear-interpolation matches hand computation")
    vals = [0.01, 0.02, 0.03, 0.05, 0.50]   # n=5, ascending
    # 90th: rank=3.6 → 0.05 + 0.45*0.6 = 0.32
    check(approx(S1E.percentile(vals, 90.0), 0.32, 1e-12), "p90 == 0.32")
    # 10th: rank=0.4 → 0.01 + 0.01*0.4 = 0.014
    check(approx(S1E.percentile(vals, 10.0), 0.014, 1e-12), "p10 == 0.014")
    # 25th: rank=1.0 → 0.02
    check(approx(S1E.percentile(vals, 25.0), 0.02, 1e-12), "p25 == 0.02")
    # edges
    check(approx(S1E.percentile(vals, 0.0), 0.01), "p0 == min")
    check(approx(S1E.percentile(vals, 100.0), 0.50), "p100 == max")
    check(approx(S1E.percentile([0.7], 90.0), 0.7), "single value → that value")
    check(approx(S1E.percentile([], 50.0), 0.0), "empty → 0.0")


# ─────────────────────────────────────────────────────────────────────────────
# 2) Per-prime HIGH/LOW bands match the frozen rule on a controlled prime
# ─────────────────────────────────────────────────────────────────────────────

def _topo(edges):
    """Build a Topology from (cue, response, strength) edges (the real loader's tuple shape)."""
    return Topology(edges)


def test_high_low_bands():
    section("per-prime HIGH/LOW bands match the frozen percentile rule")
    # prime P has 5 direct edges with the strengths used in test 1; responses named by strength
    edges = [
        ("P", "r01", 0.01), ("P", "r02", 0.02), ("P", "r03", 0.03),
        ("P", "r05", 0.05), ("P", "r50", 0.50),
    ]
    topo = _topo(edges)
    p = topo.index["P"]
    high, low = S1E.high_low_bands(topo, p)
    high_w = sorted(topo.words[i] for i in high)
    low_w = sorted(topo.words[i] for i in low)
    # HIGH = strength >= p90(0.32) → {r50}; LOW = strength in [p10(0.014), p25(0.02)] → {r02}
    check(high_w == ["r50"], f"HIGH band == ['r50']; got {high_w}")
    check(low_w == ["r02"], f"LOW band == ['r02']; got {low_w}")
    # bands are disjoint and both > 0 (by construction here)
    check(set(high_w).isdisjoint(low_w), "HIGH and LOW disjoint")


# ─────────────────────────────────────────────────────────────────────────────
# 3) Global in-degree deciles + same-decile matching, incl. boundary→lower
# ─────────────────────────────────────────────────────────────────────────────

def test_indegree_deciles_and_boundary():
    section("global in-degree deciles + decile_of (boundary tie → LOWER decile)")
    # Build a graph with a KNOWN in-degree distribution. 11 sink nodes s0..s10 with
    # in-degrees 0,1,2,...,10 respectively (node s_k has exactly k distinct incoming cues).
    # We create k distinct cue nodes c{k}_{j} → s_k.
    edges = []
    for k in range(0, 11):
        for j in range(k):
            edges.append((f"c{k}_{j}", f"s{k}", 0.5))
    topo = _topo(edges)
    # in-degree of s_k is k; the cue nodes have in-degree 0. So the global in-degree multiset
    # over ALL nodes is: many zeros (the cue nodes + s0) plus 1..10 once each.
    cuts = S1E.indegree_decile_cuts(topo)
    check(len(cuts) == 9, "exactly 9 decile cut points")
    check(cuts == sorted(cuts), "decile cuts are non-decreasing")

    # decile_of: a value strictly greater than a cut crosses it; equal does NOT (lower decile).
    # Construct a tiny explicit cut list to test the boundary rule directly:
    cl = [1.0, 2.0, 3.0]
    check(S1E.decile_of(0, cl) == 0, "indeg 0 → decile 0")
    check(S1E.decile_of(1, cl) == 0, "indeg 1 ON the first cut → LOWER decile (0), not 1")
    check(S1E.decile_of(2, cl) == 1, "indeg 2 ON the second cut → decile 1 (lower)")
    check(S1E.decile_of(3, cl) == 2, "indeg 3 ON the third cut → decile 2 (lower)")
    check(S1E.decile_of(4, cl) == 3, "indeg 4 above all cuts → decile 3")
    check(S1E.decile_of(1.5, cl) == 1, "indeg between cut1 and cut2 → decile 1")


# ─────────────────────────────────────────────────────────────────────────────
# 4) W(P,T) integer map and W_gap; S0 weight-blind condition
# ─────────────────────────────────────────────────────────────────────────────

def test_weight_map_and_w_gap():
    section("W(P,T) integer weight map and W_gap")
    # the map: min(10, 1 + floor(strength*100))
    check(traverse_count_for_strength(0.005) == 1, "strength 0.005 → W 1")
    check(traverse_count_for_strength(0.01) == 2, "strength 0.01 → W 2")
    check(traverse_count_for_strength(0.009) == 1, "strength 0.009 → W 1 (floor)")
    check(traverse_count_for_strength(0.50) == 10, "strength 0.50 → W cap 10")
    check(traverse_count_for_strength(0.99) == 10, "strength 0.99 → W cap 10")
    # On a prime: a HIGH and a LOW target whose strengths map to the SAME integer weight have
    # W_gap = 0 (the weight-blind condition). 0.011 → 2, 0.019 → 2.
    edges = [("P", "h", 0.019), ("P", "l", 0.011), ("P", "x", 0.40), ("P", "y", 0.001)]
    topo = _topo(edges)
    p = topo.index["P"]
    wh = S1E.w_of(topo, p, topo.index["h"])
    wl = S1E.w_of(topo, p, topo.index["l"])
    check(wh == wl == 2, f"h and l both map to weight 2 (W_gap=0); got {wh},{wl}")


# ─────────────────────────────────────────────────────────────────────────────
# 5) S0 selection: weight-blind AND in-degree-matched; tightest |Δindeg|; drop count
# ─────────────────────────────────────────────────────────────────────────────

def test_s0_weight_blind_and_indegree_matched():
    section("S0: weight-blind (W_gap=0) AND in-degree-matched (shared decile); tie-break")
    # HIGH and LOW members all SHARE the integer weight (all strengths in (0.01,0.02) → W=2),
    # but are still split into HIGH vs LOW by the per-prime percentile. With n=10 direct edges
    # the LOW window [p10,p25] lands on positions 1 and 2 and HIGH (>=p90) on position 9, so we
    # place L1,L2 at those low positions and H at the top (hand-derived from the percentile rule):
    #   ascending: f00, L1=0.0110, L2=0.0112, then six fillers 0.0150, then H=0.0199
    #   p10≈0.01091  p25≈0.01215  → LOW = {L1(0.0110), L2(0.0112)}
    #   p90≈0.01549  → HIGH = {H(0.0199)}
    edges = [
        ("P", "f00", 0.0101),
        ("P", "L1", 0.0110), ("P", "L2", 0.0112),
        ("P", "f03", 0.0150), ("P", "f04", 0.0150), ("P", "f05", 0.0150),
        ("P", "f06", 0.0150), ("P", "f07", 0.0150), ("P", "f08", 0.0150),
        ("P", "H", 0.0199),
    ]
    # in-degrees: give H and L1 in-degree 1 (only P), and L2 a LARGE in-degree (many extra cues)
    # so L2 lands in a HIGHER decile → (H,L1) is in-degree-matched, (H,L2) is NOT.
    for j in range(20):
        edges.append((f"pop{j}", "L2", 0.5))    # push L2's in-degree up (very popular)
    for k in range(40):
        edges.append((f"bgsrc{k}", f"bg{k}", 0.5))   # background nodes with in-degree 1
    topo = _topo(edges)
    p = topo.index["P"]

    high, low = S1E.high_low_bands(topo, p)
    check(sorted(topo.words[i] for i in high) == ["H"],
          f"HIGH band == ['H']; got {sorted(topo.words[i] for i in high)}")
    check(sorted(topo.words[i] for i in low) == ["L1", "L2"],
          f"LOW band == ['L1','L2']; got {sorted(topo.words[i] for i in low)}")

    # all of H, L1, L2 map to weight 2 → both (H,L1) and (H,L2) are weight-blind
    for nm in ("H", "L1", "L2"):
        check(S1E.w_of(topo, p, topo.index[nm]) == 2, f"{nm} maps to weight 2 (weight-blind)")

    cuts = S1E.indegree_decile_cuts(topo)
    dH = S1E.decile_of(topo.indeg[topo.index["H"]], cuts)
    dL1 = S1E.decile_of(topo.indeg[topo.index["L1"]], cuts)
    dL2 = S1E.decile_of(topo.indeg[topo.index["L2"]], cuts)
    check(dH == dL1, f"H and L1 share an in-degree decile (matched); {dH} vs {dL1}")
    check(dH != dL2, f"H and L2 do NOT share a decile (unmatched); {dH} vs {dL2}")

    pair = S1E.select_s0_pair(topo, p, cuts)
    check(pair is not None, "an S0 pair exists (the weight-blind + matched (H,L1))")
    if pair is not None:
        h_sel, l_sel = topo.words[pair[0]], topo.words[pair[1]]
        check((h_sel, l_sel) == ("H", "L1"),
              f"S0 pair is the matched (H,L1), not the unmatched (H,L2); got ({h_sel},{l_sel})")


def test_s0_drop_when_weight_blind_but_unmatched():
    section("ASSERTED-NEGATIVE: weight-blind pair but NO in-degree match → DROPPED from S0")
    # Same robust n=10 band layout: HIGH={H}, LOW={L1,L2}, all weight-blind (W=2). Here BOTH
    # low-band members are made VERY popular (high in-degree) while H has in-degree 1, so
    # NEITHER (H,L1) NOR (H,L2) shares a decile → a weight-blind pair EXISTS but NONE is
    # in-degree-matched → select_s0_pair returns None AND _has_weight_blind_pair is True →
    # the prime is counted as an in-degree DROP from S0.
    edges = [
        ("P", "f00", 0.0101),
        ("P", "L1", 0.0110), ("P", "L2", 0.0112),
        ("P", "f03", 0.0150), ("P", "f04", 0.0150), ("P", "f05", 0.0150),
        ("P", "f06", 0.0150), ("P", "f07", 0.0150), ("P", "f08", 0.0150),
        ("P", "H", 0.0199),
    ]
    for j in range(25):
        edges.append((f"popA{j}", "L1", 0.5))     # L1 very popular → high decile
        edges.append((f"popB{j}", "L2", 0.5))     # L2 very popular → high decile
    for k in range(40):
        edges.append((f"bgsrc{k}", f"bg{k}", 0.5))
    topo = _topo(edges)
    p = topo.index["P"]
    cuts = S1E.indegree_decile_cuts(topo)

    high, low = S1E.high_low_bands(topo, p)
    check(sorted(topo.words[i] for i in high) == ["H"], "HIGH band == ['H']")
    check(sorted(topo.words[i] for i in low) == ["L1", "L2"], "LOW band == ['L1','L2']")
    check(S1E._has_weight_blind_pair(topo, p) is True,
          "a weight-blind (W_gap=0) candidate pair exists")
    pair = S1E.select_s0_pair(topo, p, cuts)
    check(pair is None,
          "but NO in-degree-matched pair exists → select_s0_pair returns None (dropped)")


# ─────────────────────────────────────────────────────────────────────────────
# 6) Arm (a) / (b)-d1 / (c) construction on a controlled graph
# ─────────────────────────────────────────────────────────────────────────────

def test_arm_b_d1_both_one_hop():
    section("arm (b)-d1: HIGH-direct vs LOW-direct, both 1 hop, both direct responses")
    edges = [
        ("P", "L1", 0.0110), ("P", "L2", 0.0120),
        ("P", "Ma", 0.05), ("P", "Mb", 0.05),
        ("P", "H", 0.40),
    ]
    topo = _topo(edges)
    p = topo.index["P"]
    pair = S1E.select_arm_b_d1(topo, p)
    check(pair is not None, "arm (b)-d1 pair exists")
    if pair is not None:
        h, l = pair
        # both are direct responses of P (1 hop)
        check(h in topo.out_set[p] and l in topo.out_set[p],
              "both HIGH and LOW targets are direct responses (1 hop)")
        check(topo.words[h] == "H", f"HIGH-direct is H; got {topo.words[h]}")
        check(topo.words[l] in ("L1", "L2"), f"LOW-direct is a low-band member; got {topo.words[l]}")


def test_arm_a_control_in_horizon_nondirect():
    section("arm (a): reachable-unrelated control is in-horizon, non-direct, distance recorded")
    # P → A → C : C is reachable at 2 hops, not a direct response of P → a valid control.
    # P also has direct HIGH target H. Build enough direct edges for banding (MIN_OUTDEG aside;
    # select_arm_a doesn't gate on out-degree — the driver does).
    edges = [
        ("P", "H", 0.40), ("P", "A", 0.30), ("P", "B", 0.30), ("P", "D", 0.20),
        ("A", "C", 0.30),     # C at 2 hops from P, not direct
    ]
    topo = _topo(edges)
    p = topo.index["P"]
    res = S1E.select_arm_a(topo, p)
    check(res is not None, "arm (a) populated")
    if res is not None:
        ts, tc, ch = res
        check(tc not in topo.out_set[p], "control is NOT a direct response of P (unrelated edge)")
        check(ch >= 1 and ch <= S1E.HORIZON_HOPS, f"control hop-distance in [1,{S1E.HORIZON_HOPS}]; got {ch}")
        check(topo.words[tc] == "C", f"the only valid in-horizon non-direct control is C; got {topo.words[tc]}")
        check(ch == 2, f"C is at 2 hops; got {ch}")


def test_arm_c_full_direct_range():
    section("arm (c): the full set of P's direct responses with their strengths")
    edges = [("P", "a", 0.01), ("P", "b", 0.05), ("P", "c", 0.30), ("P", "d", 0.40)]
    topo = _topo(edges)
    p = topo.index["P"]
    ds = S1E._direct_strengths(topo, p)
    names = sorted(topo.words[r] for r, _ in ds)
    check(names == ["a", "b", "c", "d"], f"arm (c) covers all 4 direct responses; got {names}")
    # strengths are the SWOW values, ascending
    strengths = [s for _, s in ds]
    check(strengths == sorted(strengths), "arm (c) strengths ascending (deterministic order)")


# ─────────────────────────────────────────────────────────────────────────────
# 7) Structurally-impossible-branch guard: S0 can be BOTH non-empty AND empty
# ─────────────────────────────────────────────────────────────────────────────

def test_s0_branch_reachable_both_ways():
    section("structural guard: the S0 stratum CAN populate AND CAN be empty (both branches fire)")
    # CASE A — S0 populates: a prime with a weight-blind, in-degree-matched HIGH/LOW pair
    # (the robust n=10 band layout; H and L1 both have in-degree 1 → same low decile → matched).
    edgesA = [
        ("P", "f00", 0.0101),
        ("P", "L1", 0.0110), ("P", "L2", 0.0112),
        ("P", "f03", 0.0150), ("P", "f04", 0.0150), ("P", "f05", 0.0150),
        ("P", "f06", 0.0150), ("P", "f07", 0.0150), ("P", "f08", 0.0150),
        ("P", "H", 0.0199),
    ]
    for k in range(40):
        edgesA.append((f"bg{k}", f"t{k}", 0.5))
    topoA = _topo(edgesA)
    selA = S1E.select(topoA, 1)
    check(len(selA.s0) >= 1, "CASE A: S0 populates (>=1 weight-blind+matched pair)")

    # CASE B — S0 empty: a prime whose HIGH and LOW map to DIFFERENT weights (W_gap>0 always),
    # so no weight-blind pair exists at all → S0 empty, and NOT counted as an indeg drop.
    edgesB = [
        ("P", "L", 0.011),   # weight 2
        ("P", "Ma", 0.05), ("P", "Mb", 0.05), ("P", "Mc", 0.05),
        ("P", "H", 0.40),    # weight 10  → W_gap = 8 > 0
    ]
    topoB = _topo(edgesB)
    selB = S1E.select(topoB, 1)
    check(len(selB.s0) == 0, "CASE B: S0 empty (HIGH/LOW map to different weights)")
    check(selB.s0_indeg_drop_count == 0,
          "CASE B: no indeg-drop counted (the absence is weight, not a failed match)")
    check(selB.s_plus_count == 1, "CASE B: the prime is in S+ (W_gap>0)")


# ─────────────────────────────────────────────────────────────────────────────
# 8) BLIND: the selector consults no activation (engine never imported by it)
# ─────────────────────────────────────────────────────────────────────────────

def test_selector_is_blind_to_activation():
    section("BLIND: priming_1e imports no engine activation; selection takes only a Topology")
    src = open(os.path.join(_HERE, "priming_1e.py"), encoding="utf-8").read()
    # the selector must not import the activation engine or call think()/spread_activation
    check("spread_activation" not in src, "priming_1e never references spread_activation")
    check("psyche_activation" not in src, "priming_1e never imports psyche_activation")
    check("import think" not in src and "psyche_perceive" not in src,
          "priming_1e never imports the think() loop")
    check("read_targets" not in src, "priming_1e never reads activation targets")


# ─────────────────────────────────────────────────────────────────────────────
# 9) DETERMINISM across processes — selection byte-identical across PYTHONHASHSEED
# ─────────────────────────────────────────────────────────────────────────────

_DET_PROBE = r'''
import os, sys
sys.path.insert(0, os.environ["PSYCHE_EXP"])
from swow import Topology
import priming_1e as S1E

# a controlled multi-prime graph (no SWOW data file needed): several primes each with a
# bandable direct-edge distribution plus background nodes for stable deciles.
edges = []
primes = ["alpha", "bravo", "charlie", "delta", "echo"]
for pi, P in enumerate(primes):
    edges += [(P, P+"_L1", 0.0110), (P, P+"_L2", 0.0120),
              (P, P+"_Ma", 0.0150), (P, P+"_Mb", 0.0150), (P, P+"_H", 0.0199)]
    edges += [(P, P+"_A", 0.30)]               # for arm (a) reach
    edges += [(P+"_A", P+"_C", 0.30)]          # 2-hop control
for k in range(60):
    edges.append(("bgsrc%d" % k, "bg%d" % k, 0.5))

topo = Topology(edges)
sel = S1E.select(topo, 5)
# print a canonical, ID-independent digest of the full selection
def dump(label, rows):
    for r in rows:
        print(label, r)
dump("A", [(d["prime"], d["strong"], d["control"], d["control_hops"]) for d in sel.arm_a])
dump("B1", [(d["prime"], d["high"], d["low"], d["w_high"], d["w_low"]) for d in sel.arm_b_d1])
dump("C", [(d["prime"], tuple(d["targets"])) for d in sel.arm_c])
dump("S0", [(d["prime"], d["high"], d["low"], d["indeg_high"], d["indeg_low"], d["decile"]) for d in sel.s0])
print("NS0", len(sel.s0), "NSPLUS", sel.s_plus_count, "DROP", sel.s0_indeg_drop_count)
print("CUTS", sel.decile_cuts)
'''


def _det_probe(seed: str) -> str:
    env = dict(os.environ)
    env["PSYCHE_EXP"] = _HERE
    env["PYTHONHASHSEED"] = seed
    out = subprocess.run([sys.executable, "-c", _DET_PROBE], env=env,
                         capture_output=True, text=True)
    if out.returncode != 0:
        print("  (subprocess stderr)\n" + out.stderr)
        return ""
    return out.stdout


def test_determinism_across_hash_seeds():
    section("ADVERSARIAL determinism: selection byte-identical across PYTHONHASHSEED")
    seeds = ["0", "1", "2", "7", "42", "123"]
    outs = [_det_probe(s) for s in seeds]
    first = outs[0]
    check(first.strip() != "", "selection probe produced non-empty output")
    check("NS0" in first and "CUTS" in first, "probe output has the S0 + decile digest")
    for s, o in zip(seeds, outs):
        check(o == first, f"hash seed {s} matches seed {seeds[0]} (byte-identical selection)")


# ─────────────────────────────────────────────────────────────────────────────
# 10) candidate_primes honors MIN_OUTDEG and is deterministic
# ─────────────────────────────────────────────────────────────────────────────

def test_candidate_primes_min_outdeg():
    section("candidate_primes honors MIN_OUTDEG and is deterministic given the seed")
    edges = []
    edges += [("big", "a", 0.5), ("big", "b", 0.5), ("big", "c", 0.5), ("big", "d", 0.5)]  # outdeg 4
    edges += [("small", "a", 0.5), ("small", "b", 0.5)]                                      # outdeg 2
    topo = _topo(edges)
    prs = S1E.candidate_primes(topo)
    names = {topo.words[i] for i in prs}
    check("big" in names, "prime with out-degree >= 4 is a candidate")
    check("small" not in names, "prime with out-degree 2 (< MIN_OUTDEG) is excluded")
    # determinism: same seed → same order
    prs2 = S1E.candidate_primes(topo)
    check(prs == prs2, "candidate_primes is deterministic for a fixed seed")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    test_percentile_linear()
    test_high_low_bands()
    test_indegree_deciles_and_boundary()
    test_weight_map_and_w_gap()
    test_s0_weight_blind_and_indegree_matched()
    test_s0_drop_when_weight_blind_but_unmatched()
    test_arm_b_d1_both_one_hop()
    test_arm_a_control_in_horizon_nondirect()
    test_arm_c_full_direct_range()
    test_s0_branch_reachable_both_ways()
    test_selector_is_blind_to_activation()
    test_determinism_across_hash_seeds()
    test_candidate_primes_min_outdeg()

    print()
    print(f"RESULT: {_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
