"""
TESTER-authored ADVERSARIAL suite for the SPEC-1e §10 BLIND three-arm selector
(experiments/priming_1e.py). Independent of the builder's tests; the verdict rests here.

This file is MECHANISM-only and DATA-FREE: every Topology is a synthetic adversarial fixture
built from an explicit (cue, response, strength) edge list whose correct bands / W_gap / S0
membership / in-degree decile / tie-break are derivable BY HAND from the construction — so no
test encodes its own answer via the selector under test. It computes NO activation and never
imports the engine; the selector's blindness is itself one of the properties under attack.

The make-or-break properties (EXP-1e §6.2 / §6.2.0) attacked hardest:
  - S0 identification: NO W_gap != 0 pair leaks in; NO true W_gap = 0 pair is wrongly excluded
    (boundary cases of the saturating/capped integer weight map probed directly).
  - in-degree matching: same-global-decile rule, boundary tie -> LOWER decile; close-but-outside
    pairs DROPPED; asserted-negative an unmatched weight-blind pair is excluded and counted;
    in-degree is the UNWEIGHTED STRUCTURAL initial-graph degree (broadcast-invariant by being
    activation-free here).
  - blindness / anti-circularity: selection consumes only topology/strength; no activation path.
  - determinism: identical pair-lists across fresh processes / 6 randomized PYTHONHASHSEED.
  - feasibility guards: S0 can populate AND can be a TRUE ZERO (no crash, no silent fallback).

Tiny built-in harness (print + count, exit nonzero), NOT pytest. Run as a script:
    python3 tests/test_tester_1e_selector_adversarial.py
"""

from __future__ import annotations

import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_EXP = os.path.join(_ROOT, "experiments")
_SRC = os.path.join(_ROOT, "src")
for _p in (_EXP, _SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import swow
from swow import Topology, traverse_count_for_strength as tcs
import priming_1e as S


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


def topo(edges):
    return Topology(edges)


def idx(t: Topology, w: str) -> int:
    return t.index[w]


# ─────────────────────────────────────────────────────────────────────────────
# 0) Re-derive the integer weight map's saturation/cap from first principles.
#    The whole S0 leverage stratum depends on WHERE the ladder collapses HIGH==LOW.
# ─────────────────────────────────────────────────────────────────────────────

def test_weight_map_saturation_and_cap():
    section("weight map W = min(10, 1+floor(strength*100)): floor at <=0.01, cap at >=0.09")
    # floor of the ladder: any strength in (0, 0.01] -> 1+floor(<=1.0) but float truncation:
    # 0.01*100 == 1.0 -> 1+1 = 2. strengths strictly below 0.01 map to 1.
    check(tcs(0.001) == 1, "tcs(0.001)=1 (floor)")
    check(tcs(0.009) == 1, "tcs(0.009)=1 (floor)")
    check(tcs(0.01) == 2, "tcs(0.01)=2 (0.01*100==1.0 -> 1+1)")
    check(tcs(0.019) == 2, "tcs(0.019)=2")
    check(tcs(0.02) == 3, "tcs(0.02)=3")
    # cap at 10: anything mapping to >=10 saturates.
    check(tcs(0.09) == 10, "tcs(0.09)=10 (1+9)")
    check(tcs(0.10) == 10, "tcs(0.10)=10 (1+10 capped)")
    check(tcs(0.5) == 10, "tcs(0.5)=10 (cap)")
    check(tcs(1.0) == 10, "tcs(1.0)=10 (cap)")
    # w_of is exactly this map applied to the stored edge strength
    t = topo([("p", "a", 0.5), ("p", "b", 0.99), ("p", "c", 0.001), ("p", "d", 0.009)])
    check(S.w_of(t, idx(t, "p"), idx(t, "a")) == 10, "w_of cap path")
    check(S.w_of(t, idx(t, "p"), idx(t, "c")) == 1, "w_of floor path")


# ─────────────────────────────────────────────────────────────────────────────
# 1) S0 IDENTIFICATION — no W_gap != 0 leaks in (the saturating-ladder leverage).
#    Build a prime whose HIGH and LOW bands map to DIFFERENT integer weights, so a
#    true S0 pair is impossible; assert select_s0_pair returns None and no leak.
# ─────────────────────────────────────────────────────────────────────────────

def test_s0_rejects_weight_informative_pair():
    section("S0: a HIGH/LOW pair with W_gap != 0 is NEVER admitted (no leak)")
    # prime p with 5 direct edges spanning strength so HIGH (top decile) and LOW (10-25 pct)
    # land on different integer weights. Strengths chosen so floor/cap do NOT collapse them.
    # values: 0.01(w2) 0.012(w2) 0.014(w2) 0.05(w6) 0.5(w10)
    # ascending strengths -> percentile p90 high, p10..p25 low.
    edges = [
        ("p", "lo1", 0.01), ("p", "lo2", 0.012), ("p", "mid", 0.014),
        ("p", "hi1", 0.05), ("p", "hi2", 0.5),
    ]
    t = topo(edges)
    p = idx(t, "p")
    high, low = S.high_low_bands(t, p)
    # confirm the bands are non-empty and that EVERY (h,l) cross-pair has W_gap != 0
    check(bool(high) and bool(low), "bands populated")
    any_gap_zero = False
    for h in high:
        for l in low:
            if h != l and S.w_of(t, p, h) == S.w_of(t, p, l):
                any_gap_zero = True
    check(not any_gap_zero, "no weight-blind cross-pair exists by construction")
    cuts = S.indegree_decile_cuts(t)
    check(S.select_s0_pair(t, p, cuts) is None, "select_s0_pair returns None when W_gap!=0 everywhere")
    # and _has_weight_blind_pair must agree there is NO weight-blind pair (so NOT a drop)
    check(S._has_weight_blind_pair(t, p) is False, "_has_weight_blind_pair False here")


def test_s0_accepts_true_weight_blind_pair():
    section("S0: a TRUE W_gap=0 pair (saturating ladder collapses HIGH==LOW) IS admitted")
    # All five strengths are >= 0.09 so they ALL map to w=10 (the cap). Then HIGH and LOW
    # bands are by strength percentile (distinct), but their WEIGHTS are identical (all 10),
    # so W_gap=0 for every cross pair. With in-degree matched, S0 must populate.
    # Give the two extreme targets the SAME in-degree (1) so they share a decile.
    edges = [
        ("p", "s1", 0.09), ("p", "s2", 0.20), ("p", "s3", 0.40),
        ("p", "s4", 0.70), ("p", "s5", 0.99),
        # give every target in-degree 1 exactly (only p points to them) -> same decile
    ]
    t = topo(edges)
    p = idx(t, "p")
    high, low = S.high_low_bands(t, p)
    check(bool(high) and bool(low), "bands populated (cap stratum)")
    for h in high:
        for l in low:
            if h != l:
                check(S.w_of(t, p, h) == 10 and S.w_of(t, p, l) == 10,
                      "all weights saturate to 10 (W_gap=0)")
    # all targets have in-degree 1 -> same global decile -> match holds
    cuts = S.indegree_decile_cuts(t)
    pair = S.select_s0_pair(t, p, cuts)
    check(pair is not None, "select_s0_pair admits the true W_gap=0 in-degree-matched pair")
    if pair is not None:
        h, l = pair
        check(h in high and l in low, "admitted pair is HIGH x LOW")
        check(S.w_of(t, p, h) == S.w_of(t, p, l), "admitted pair is genuinely weight-blind")


def test_s0_boundary_floor_ladder_collapse():
    section("S0: floor of the ladder also collapses weights (strengths <0.01 -> w=1)")
    # strengths strictly below 0.01 all map to w=1. So HIGH and LOW bands (distinct by
    # strength) again tie in weight -> W_gap=0. This probes the OTHER collapse region.
    edges = [
        ("p", "a", 0.001), ("p", "b", 0.002), ("p", "c", 0.004),
        ("p", "d", 0.006), ("p", "e", 0.009),
    ]
    t = topo(edges)
    p = idx(t, "p")
    high, low = S.high_low_bands(t, p)
    check(bool(high) and bool(low), "bands populated (floor stratum)")
    allw = set()
    for r in t.out[p]:
        allw.add(S.w_of(t, p, r))
    check(allw == {1}, "every direct edge maps to w=1 (floor collapse)")
    cuts = S.indegree_decile_cuts(t)
    check(S.select_s0_pair(t, p, cuts) is not None, "floor-collapse pair admitted to S0")


# ─────────────────────────────────────────────────────────────────────────────
# 2) IN-DEGREE MATCHING — same global decile, boundary tie -> lower; close-but-outside
#    is DROPPED; asserted-negative the unmatched weight-blind prime is excluded+counted.
# ─────────────────────────────────────────────────────────────────────────────

def _drop_case_edges():
    """A prime whose actual HIGH-band member is a very-popular (high in-degree) node and whose
    actual LOW-band member is unpopular (in-degree 1), with BOTH saturating to w=10 (W_gap=0).
    Band membership is DERIVED from the selector (not assumed by node name), so the fixture is
    robust to the per-prime percentile placing a particular node in a band."""
    edges = []
    # 5 direct edges, all >= 0.09 so they saturate to w=10; spread so HIGH/LOW bands form.
    edges += [("p", "HI", 0.99), ("p", "LO", 0.10), ("p", "m1", 0.5),
              ("p", "m2", 0.6), ("p", "m3", 0.7)]
    # make the eventual HIGH-band response (HI) very popular; everything else in-degree 1.
    for i in range(40):
        edges.append((f"cueHI{i}", "HI", 0.5))
    # spread global in-degrees so deciles separate the popular HIGH member from the rest.
    for j in range(60):
        edges.append((f"src{j}", f"z{j}", 0.5))
        if j % 2 == 0:
            edges.append((f"src2_{j}", f"z{j}", 0.5))
    return edges


def test_indegree_match_drops_close_but_outside_decile():
    section("in-degree match: a weight-blind pair split across deciles is DROPPED + counted")
    # Construct a global in-degree distribution with a clear decile boundary, then a prime
    # whose actual HIGH-band member and actual LOW-band member are weight-blind but straddle
    # a decile boundary. Band membership is DERIVED from the selector, not assumed by name.
    t = topo(_drop_case_edges())
    p = idx(t, "p")
    cuts = S.indegree_decile_cuts(t)
    high, low = S.high_low_bands(t, p)
    check(bool(high) and bool(low), "HIGH and LOW bands both populate")
    # find a weight-blind cross-pair and verify EVERY weight-blind cross-pair is cross-decile
    weight_blind_pairs = [(h, l) for h in high for l in low
                          if h != l and S.w_of(t, p, h) == S.w_of(t, p, l)]
    check(len(weight_blind_pairs) >= 1, "at least one weight-blind HIGH/LOW pair exists")
    all_cross_decile = all(
        S.decile_of(t.indeg[h], cuts) != S.decile_of(t.indeg[l], cuts)
        for h, l in weight_blind_pairs)
    check(all_cross_decile,
          "every weight-blind HIGH/LOW pair straddles a decile boundary (none matched)")
    # so S0 selection must DROP this prime (no in-degree-matched pair) ...
    check(S.select_s0_pair(t, p, cuts) is None, "select_s0_pair drops the cross-decile prime")
    # ... and it IS recognized as having had a weight-blind pair (i.e. it is a real drop)
    check(S._has_weight_blind_pair(t, p) is True, "the dropped prime DID have a weight-blind pair")


def test_indegree_match_drop_count_in_full_select():
    section("ASSERTED-NEGATIVE: full select() counts the unmatched weight-blind prime as S0 drop")
    # The same prime as above, run through the full select() path, must contribute to
    # arm_b_d1 (it has HIGH & LOW) but be EXCLUDED from s0 and increment s0_indeg_drop_count.
    t = topo(_drop_case_edges())
    sel = S.select(t, n_primes=1000)
    primes_in_b = {d["prime"] for d in sel.arm_b_d1}
    primes_in_s0 = {d["prime"] for d in sel.s0}
    check("p" in primes_in_b, "prime p populates arm_b_d1 (has HIGH and LOW)")
    check("p" not in primes_in_s0, "prime p is EXCLUDED from S0 (in-degree-unmatched)")
    check(sel.s0_indeg_drop_count >= 1, "s0_indeg_drop_count counts the unmatched weight-blind prime")


def test_decile_boundary_tie_goes_to_lower():
    section("decile boundary tie -> LOWER decile (value EQUAL to a cut does not cross it)")
    cuts = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    # value exactly on a cut: decile = #cuts strictly less than value
    check(S.decile_of(1, cuts) == 0, "indeg=1 (==cut[0]) -> decile 0 (lower)")
    check(S.decile_of(2, cuts) == 1, "indeg=2 (==cut[1]) -> decile 1 (lower, not 2)")
    check(S.decile_of(9, cuts) == 8, "indeg=9 (==cut[8]) -> decile 8 (lower, not 9)")
    check(S.decile_of(0, cuts) == 0, "indeg=0 -> decile 0")
    check(S.decile_of(10, cuts) == 9, "indeg=10 (> all cuts) -> decile 9")
    # an off-boundary value
    check(S.decile_of(3, cuts) == 2, "indeg=3 (==cut[2]) -> decile 2 (lower)")


def test_indegree_is_unweighted_structural_initial_graph():
    section("in-degree is UNWEIGHTED structural count of distinct incoming cues (not strength sum)")
    # node T fed by 3 distinct cues with WILDLY different strengths. Structural in-degree=3,
    # NOT a sum of strengths and NOT the integer weight. Also a duplicate edge must not
    # double-count (dedup by (ci,ri)).
    edges = [
        ("c1", "T", 0.99), ("c2", "T", 0.001), ("c3", "T", 0.5),
        ("c1", "T", 0.4),  # duplicate (c1->T) — must NOT bump in-degree
    ]
    t = topo(edges)
    T = idx(t, "T")
    check(t.indeg[T] == 3, "in-degree counts 3 DISTINCT cues, dedups the repeat, ignores strength")
    # a node with no incoming edges has in-degree 0
    c1 = idx(t, "c1")
    check(t.indeg[c1] == 0, "a pure-source node has in-degree 0")


# ─────────────────────────────────────────────────────────────────────────────
# 3) S0 TIE-BREAK — tightest |Δindeg| wins; ties resolved by the seeded shuffle and are
#    deterministic. Build several weight-blind+matched candidate pairs with different
#    |Δindeg| and confirm the minimum is chosen.
# ─────────────────────────────────────────────────────────────────────────────

def test_s0_tiebreak_min_abs_indeg_delta():
    section("S0 tie-break: among matched weight-blind pairs, the tightest |Δindeg| is chosen")
    # Two HIGH targets (H1,H2) and two LOW targets (L1,L2), all saturating to w=10.
    # Arrange in-degrees so all four sit in the SAME decile but |Δindeg| differs across pairs.
    # We want one pair (say H2,L2) to have the strictly smallest |Δindeg|.
    edges = []
    edges.append(("p", "H1", 0.5))
    edges.append(("p", "H2", 0.6))
    edges.append(("p", "L1", 0.09))
    edges.append(("p", "L2", 0.10))
    # filler so bands form: need >=5 direct edges for clean percentiles
    edges.append(("p", "m1", 0.3))
    # Give in-degrees: H1=5, H2=4, L1=2, L2=4  -> |H2-L2|=0 is tightest.
    # Build distinct cues to set each in-degree exactly.
    def feed(target, k):
        for i in range(k - 1):  # -1 because p->target already gives 1
            edges.append((f"cue_{target}_{i}", target, 0.5))
    feed("H1", 5)
    feed("H2", 4)
    feed("L1", 2)
    feed("L2", 4)
    # pad the global distribution so the four targets all share a decile (in-degrees 2..5
    # cluster together). Add many nodes with in-degree in {2,3,4,5}.
    for j in range(40):
        edges.append((f"a{j}", f"q{j}", 0.5))
        edges.append((f"b{j}", f"q{j}", 0.5))
        if j % 2 == 0:
            edges.append((f"c{j}", f"q{j}", 0.5))
        if j % 3 == 0:
            edges.append((f"d{j}", f"q{j}", 0.5))
    t = topo(edges)
    p = idx(t, "p")
    cuts = S.indegree_decile_cuts(t)
    H1, H2, L1, L2 = (idx(t, x) for x in ("H1", "H2", "L1", "L2"))
    # only test the tie-break if the construction actually placed all four in one decile
    ds = {S.decile_of(t.indeg[x], cuts) for x in (H1, H2, L1, L2)}
    if len(ds) == 1:
        pair = S.select_s0_pair(t, p, cuts)
        check(pair is not None, "a matched weight-blind pair exists")
        if pair is not None:
            h, l = pair
            delta = abs(t.indeg[h] - t.indeg[l])
            # the minimum achievable |Δindeg| among matched weight-blind HIGH x LOW pairs
            high, low = S.high_low_bands(t, p)
            best = min(abs(t.indeg[hh] - t.indeg[ll])
                       for hh in high for ll in low if hh != ll
                       and S.w_of(t, p, hh) == S.w_of(t, p, ll)
                       and S.decile_of(t.indeg[hh], cuts) == S.decile_of(t.indeg[ll], cuts))
            check(delta == best, f"chosen pair has the minimum |Δindeg| ({delta} == {best})")
    else:
        # construction didn't isolate a single decile; still assert no crash and a valid result
        pair = S.select_s0_pair(t, p, cuts)
        check(pair is None or (pair[0] in S.high_low_bands(t, p)[0]),
              "select_s0_pair returns a valid HIGH-band high or None")


# ─────────────────────────────────────────────────────────────────────────────
# 4) FEASIBILITY GUARDS — S0 can populate AND can be a TRUE ZERO (no crash, no fallback).
# ─────────────────────────────────────────────────────────────────────────────

def test_s0_can_be_true_zero():
    section("feasibility: S0 can be a TRUE ZERO (every arm-b prime is weight-informative)")
    # Two primes, each with HIGH/LOW bands that are weight-INFORMATIVE (different integer
    # weights), so NO prime has a weight-blind pair -> N_S0 == 0, with no crash.
    edges = []
    for pn in ("p1", "p2"):
        edges += [
            (pn, f"{pn}_lo1", 0.01), (pn, f"{pn}_lo2", 0.012), (pn, f"{pn}_mid", 0.014),
            (pn, f"{pn}_hi1", 0.05), (pn, f"{pn}_hi2", 0.5),
        ]
    t = topo(edges)
    sel = S.select(t, n_primes=100)
    check(len(sel.arm_b_d1) >= 1, "arm_b_d1 populated (primes have HIGH and LOW)")
    check(len(sel.s0) == 0, "N_S0 is a TRUE ZERO (no weight-blind pair anywhere)")
    check(sel.s0_indeg_drop_count == 0, "no weight-blind-unmatched drops (there are no blind pairs)")
    # and s_plus accounting must see these as S+ (W_gap>0)
    check(sel.s_plus_count == len(sel.arm_b_d1), "every arm-b prime is S+ (W_gap>0)")


def test_s0_can_populate():
    section("feasibility: S0 CAN populate (saturated weight-blind + matched in-degree)")
    edges = []
    for pn in ("p1", "p2", "p3"):
        edges += [
            (pn, f"{pn}_a", 0.2), (pn, f"{pn}_b", 0.3), (pn, f"{pn}_c", 0.4),
            (pn, f"{pn}_d", 0.7), (pn, f"{pn}_e", 0.99),
        ]
    t = topo(edges)
    sel = S.select(t, n_primes=100)
    check(len(sel.s0) >= 1, "N_S0 populates when bands saturate and in-degrees match")
    # every S0 record's HIGH and LOW share a decile (the matching invariant)
    cuts = sel.decile_cuts
    ok = True
    for d in sel.s0:
        # recover indices
        hi = t.index[d["high"]]
        lo = t.index[d["low"]]
        if S.decile_of(t.indeg[hi], cuts) != S.decile_of(t.indeg[lo], cuts):
            ok = False
    check(ok, "every S0 pair is genuinely in-degree-matched (shared decile)")


def test_empty_and_singleton_topologies_do_not_crash():
    section("HOSTILE: empty / singleton / no-qualifying-prime topologies return empty, no crash")
    # empty graph
    t0 = topo([])
    check(t0.n == 0, "empty topology has 0 nodes")
    sel0 = S.select(t0, n_primes=10)
    check(sel0.arm_b_d1 == [] and sel0.s0 == [], "empty graph -> empty selection")
    check(sel0.s_plus_count == 0 and sel0.s0_indeg_drop_count == 0, "empty graph -> zero counts")
    # single edge: only one prime with out-degree 1 (< MIN_OUTDEG=4) -> no candidate
    t1 = topo([("a", "b", 0.5)])
    sel1 = S.select(t1, n_primes=10)
    check(sel1.arm_b_d1 == [], "single-edge graph yields no arm-b prime (out-degree < 4)")
    # a prime with exactly MIN_OUTDEG edges but all DISTINCT weights and a degenerate LOW band
    t2 = topo([("p", "x1", 0.5), ("p", "x2", 0.5), ("p", "x3", 0.5), ("p", "x4", 0.5)])
    sel2 = S.select(t2, n_primes=10)
    # all equal strengths: HIGH band = all (>= p90 == max), LOW band = all (10-25 pct == same
    # value). This is a real edge case — assert it does not crash and yields a consistent result.
    check(isinstance(sel2.arm_b_d1, list), "equal-strength prime handled without crash")


def test_arm_b_d1_targets_are_both_direct_one_hop():
    section("arm (b)-d1 invariant: HIGH and LOW are BOTH direct (1-hop) responses of the prime")
    edges = [
        ("p", "a", 0.01), ("p", "b", 0.02), ("p", "c", 0.03),
        ("p", "d", 0.05), ("p", "e", 0.5),
        ("e", "deep", 0.5),  # a 2-hop node that must NEVER appear as an arm-b target
    ]
    t = topo(edges)
    p = idx(t, "p")
    direct = t.out_set[p]
    sel = S.select(t, n_primes=10)
    for d in sel.arm_b_d1:
        hi, lo = t.index[d["high"]], t.index[d["low"]]
        check(hi in direct and lo in direct, "both arm-b-d1 targets are direct responses of p")
        check(hi != lo, "HIGH and LOW are distinct targets")


# ─────────────────────────────────────────────────────────────────────────────
# 5) ARM (a) — control is in-horizon, NON-direct, distance recorded; strong is HIGH-direct.
# ─────────────────────────────────────────────────────────────────────────────

def test_arm_a_control_is_in_horizon_nondirect():
    section("arm (a): control reachable within HORIZON_HOPS, NOT a direct edge, hops recorded")
    # p -> a,b,c,d (direct). c -> far (2 hops). far has in-degree>0. far must be a valid control;
    # a direct response must NEVER be the control.
    edges = [
        ("p", "a", 0.5), ("p", "b", 0.4), ("p", "c", 0.3), ("p", "d", 0.2),
        ("c", "far", 0.5),         # 2-hop, non-direct
        ("d", "far2", 0.5), ("far2", "far3", 0.5),  # far3 at 3 hops
        ("x", "far", 0.5),         # give 'far' in-degree 2
    ]
    t = topo(edges)
    p = idx(t, "p")
    direct = t.out_set[p]
    r = S.select_arm_a(t, p)
    check(r is not None, "arm (a) populates")
    if r is not None:
        ts, tc, hops = r
        check(ts in direct, "strong target is a direct response")
        check(tc not in direct and tc != p, "control is NOT a direct response and not p")
        check(1 <= hops <= S.HORIZON_HOPS, f"control hop-distance {hops} within horizon")
        # the recorded hops must equal the true BFS distance
        true_d = None
        seen = {p}; frontier = {p}
        for hop in range(1, S.HORIZON_HOPS + 1):
            nxt = set()
            for u in frontier:
                for v in t.out[u]:
                    if v not in seen:
                        seen.add(v); nxt.add(v)
                        if v == tc:
                            true_d = hop
            frontier = nxt
        check(true_d == hops, f"recorded control hops match true BFS distance ({hops})")


def test_arm_a_none_when_no_nondirect_in_horizon():
    section("arm (a): None when NO in-horizon non-direct node exists (no false control)")
    # a pure star: p -> a,b,c,d and NOTHING reachable beyond direct responses.
    edges = [("p", "a", 0.5), ("p", "b", 0.4), ("p", "c", 0.3), ("p", "d", 0.2)]
    t = topo(edges)
    p = idx(t, "p")
    r = S.select_arm_a(t, p)
    check(r is None, "no non-direct in-horizon node -> arm (a) returns None")


# ─────────────────────────────────────────────────────────────────────────────
# 6) BLINDNESS / ANTI-CIRCULARITY — the selector never imports the engine; selection
#    takes only a Topology; no activation/result key influences pair choice.
# ─────────────────────────────────────────────────────────────────────────────

def test_blindness_no_engine_import():
    section("BLINDNESS: priming_1e never imports the activation engine / think")
    import priming_1e
    src = open(priming_1e.__file__, encoding="utf-8").read()
    # forbidden engine surfaces (the selector must not be able to see activation)
    for forbidden in ("spread_activation", "nous_activation", "nous_perceive",
                      "import think", "from nous_perceive", "nous_workspace",
                      "build_activation_field", "ThoughtResult", "MAResult",
                      "priming_instrument"):
        check(forbidden not in src, f"selector source does not reference '{forbidden}'")
    # the module's loaded namespace must not contain an activation function
    check(not hasattr(priming_1e, "spread_activation"), "no spread_activation in namespace")
    check(not hasattr(priming_1e, "think"), "no think in namespace")


def test_blindness_select_signature_takes_only_topology():
    section("BLINDNESS: select() consumes only a Topology + structural knobs (no store/engine)")
    import inspect
    sig = inspect.signature(S.select)
    params = list(sig.parameters)
    # first positional is the topology; nothing here is a store / activation / result object
    check(params[0] == "topo", "select's first parameter is the topology")
    for p in params:
        check("store" not in p and "activation" not in p and "result" not in p
              and "delta" not in p and "winner" not in p,
              f"select parameter '{p}' is not an activation/result handle")


def test_selection_independent_of_word_label_ordering():
    section("ANTI-CIRCULARITY: selection depends on STRUCTURE, invariant to label spelling")
    # Two isomorphic graphs with relabeled (but order-preserving) node names must produce
    # structurally identical selections (same indices chosen), proving the choice is driven by
    # topology+strength, not by any spelling that could correlate with an activation outcome.
    base = [
        ("p", "a", 0.2), ("p", "b", 0.3), ("p", "c", 0.4), ("p", "d", 0.7), ("p", "e", 0.99),
        ("c", "z", 0.5), ("x", "z", 0.5),
    ]
    # relabel by prefixing 'n_' to every node (sorted order is preserved within the prefix)
    relabel = [(f"n_{c}", f"n_{r}", s) for (c, r, s) in base]
    t1, t2 = topo(base), topo(relabel)
    s1 = S.select(t1, n_primes=10)
    s2 = S.select(t2, n_primes=10)
    # compare the structural shape (indices), not labels: map each selection's words back
    def shape(sel, t):
        out = []
        for d in sel.arm_b_d1:
            out.append((t.index[d["prime"]], t.index[d["high"]], t.index[d["low"]],
                        d["w_high"], d["w_low"]))
        return sorted(out)
    check(shape(s1, t1) == shape(s2, t2),
          "isomorphic relabeled graph yields structurally identical arm-b selection")


# ─────────────────────────────────────────────────────────────────────────────
# 7) DETERMINISM across processes (6 randomized PYTHONHASHSEED). The frozen selection
#    must be byte-identical. We hash the per-arm pair lists produced in fresh interpreters.
# ─────────────────────────────────────────────────────────────────────────────

_DETERMINISM_CHILD = r'''
import os, sys, hashlib
_EXP = os.environ["E1E_EXP"]; _SRC = os.environ["E1E_SRC"]
for p in (_EXP, _SRC):
    if p not in sys.path:
        sys.path.insert(0, p)
from swow import Topology
import priming_1e as S

# a fixed adversarial topology, built identically in every child process
edges = []
for pn in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot"):
    edges += [
        (pn, pn+"_a", 0.2), (pn, pn+"_b", 0.3), (pn, pn+"_c", 0.4),
        (pn, pn+"_d", 0.7), (pn, pn+"_e", 0.99), (pn, pn+"_f", 0.01),
    ]
# cross-links to create in-horizon non-direct controls and 2-hop nodes
edges += [("charlie_e", "shared", 0.5), ("delta_e", "shared", 0.5), ("q", "shared", 0.5)]
edges += [("alpha_e", "alpha_e2", 0.5), ("alpha_e2", "alpha_e3", 0.5)]
t = Topology(edges)
sel = S.select(t, n_primes=50)

def ser(records, keys):
    rows = []
    for d in records:
        rows.append("|".join(str(d[k]) for k in keys))
    return "\n".join(rows)

blob = "\n##A\n" + ser(sel.arm_a, ["prime","strong","control","control_hops"])
blob += "\n##B1\n" + ser(sel.arm_b_d1, ["prime","high","low","w_high","w_low","indeg_high","indeg_low"])
blob += "\n##B2\n" + ser(sel.arm_b_d2, ["prime","high2","low2"])
blob += "\n##S0\n" + ser(sel.s0, ["prime","high","low","indeg_high","indeg_low","decile"])
blob += "\n##C\n"
for d in sel.arm_c:
    blob += d["prime"] + ":" + ",".join("%s=%r" % (r, s) for (r, s) in d["targets"]) + "\n"
blob += "\n##COUNTS\n%d|%d|%d|%s" % (
    sel.s_plus_count, sel.s0_indeg_drop_count, sel.n_arm_b_d1_primes,
    ",".join("%g" % c for c in sel.decile_cuts))
sys.stdout.write(hashlib.sha256(blob.encode("utf-8")).hexdigest())
'''


def test_determinism_across_processes():
    section("DETERMINISM: byte-identical selection across 6 randomized PYTHONHASHSEED (fresh procs)")
    env = dict(os.environ)
    env["E1E_EXP"] = _EXP
    env["E1E_SRC"] = _SRC
    digests = []
    for seed in ("0", "1", "7", "13", "524287", "2147483647"):
        e = dict(env)
        e["PYTHONHASHSEED"] = seed
        out = subprocess.run([sys.executable, "-c", _DETERMINISM_CHILD],
                             env=e, capture_output=True, text=True)
        if out.returncode != 0:
            print("    child stderr:", out.stderr[-500:])
        check(out.returncode == 0, f"determinism child (seed {seed}) ran cleanly")
        digests.append(out.stdout.strip())
    check(len(set(digests)) == 1,
          f"selection digest identical across all seeds (got {len(set(digests))} distinct)")
    check(all(d for d in digests), "every child produced a non-empty digest")


# ─────────────────────────────────────────────────────────────────────────────
# 8) Persistence / hashing determinism: save_pair_lists hashes are a pure function of the
#    Selection content (same selection -> same hashes), and DROPPED sub-arm reported.
# ─────────────────────────────────────────────────────────────────────────────

def test_save_pair_lists_hash_is_deterministic():
    section("save_pair_lists: SHA-256 is a deterministic function of selection content")
    import tempfile
    edges = []
    for pn in ("p1", "p2", "p3"):
        edges += [
            (pn, f"{pn}_a", 0.2), (pn, f"{pn}_b", 0.3), (pn, f"{pn}_c", 0.4),
            (pn, f"{pn}_d", 0.7), (pn, f"{pn}_e", 0.99),
        ]
    t = topo(edges)
    sel = S.select(t, n_primes=100)
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        h1 = S.save_pair_lists(sel, d1)
        h2 = S.save_pair_lists(sel, d2)
        for k in h1:
            check(h1[k] == h2[k], f"hash for '{k}' identical across two writes")
    # arm_b_d2 must report the DROPPED sentinel when the sub-arm is not populated
    # (a pure star has no 2-hop nodes)
    star = topo([("p", "a", 0.2), ("p", "b", 0.3), ("p", "c", 0.4), ("p", "d", 0.7), ("p", "e", 0.99)])
    sstar = S.select(star, n_primes=10)
    with tempfile.TemporaryDirectory() as d3:
        hstar = S.save_pair_lists(sstar, d3)
        check(hstar["arm_b_d2"].startswith("DROPPED"),
              "unpopulated distance-2 sub-arm reported as DROPPED, not crashed")


# ─────────────────────────────────────────────────────────────────────────────
# runner
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    test_weight_map_saturation_and_cap()
    test_s0_rejects_weight_informative_pair()
    test_s0_accepts_true_weight_blind_pair()
    test_s0_boundary_floor_ladder_collapse()
    test_indegree_match_drops_close_but_outside_decile()
    test_indegree_match_drop_count_in_full_select()
    test_decile_boundary_tie_goes_to_lower()
    test_indegree_is_unweighted_structural_initial_graph()
    test_s0_tiebreak_min_abs_indeg_delta()
    test_s0_can_be_true_zero()
    test_s0_can_populate()
    test_empty_and_singleton_topologies_do_not_crash()
    test_arm_b_d1_targets_are_both_direct_one_hop()
    test_arm_a_control_is_in_horizon_nondirect()
    test_arm_a_none_when_no_nondirect_in_horizon()
    test_blindness_no_engine_import()
    test_blindness_select_signature_takes_only_topology()
    test_selection_independent_of_word_label_ordering()
    test_determinism_across_processes()
    test_save_pair_lists_hash_is_deterministic()

    print("\n" + "=" * 60)
    print(f"RESULT: {_passed} passed, {_failed} failed")
    print("=" * 60)
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
