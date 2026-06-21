"""
SPEC-1e §10 — the BLIND three-arm stimulus selector for the 1e priming pre-registration
(EXP-1e-priming.md). This is the SINGLE authoritative selector the pre-registration defers
its per-arm pair-list hashes to (EXP-1e §10.2 / SPEC-1e §10: no parallel selector).

It is STIMULUS CONSTRUCTION ONLY. It selects, per prime, the targets for the three
pre-registered arms using **SWOW topology + R123.Strength ONLY** — never any Nous activation
(the anti-circularity core, CLAUDE.md rule 5 / EXP-1e §11). It computes **no activation, no
Δ, no verdict.** Selecting a target *because it activated well* would void the run; nothing
here calls the engine.

Everything project-authored here is a STRUCTURAL selection knob fixed in advance by the
frozen pre-registration; no relatedness value or stimulus pair is hand-authored — the bands,
distances, and directions all come from SWOW.

────────────────────────────────────────────────────────────────────────────────────
FROZEN KNOBS (EXP-1e §9.1 / §6.2 / §6.2.0 — do not change; they are pre-registered)
────────────────────────────────────────────────────────────────────────────────────
  SELECTION_SEED = 20260621        deterministic given this seed (sorted lists, seeded shuffle)
  MIN_OUTDEG     = 4               a prime must have SWOW out-degree >= 4 to be a candidate
  HORIZON_HOPS   = 3               "reachable / in-horizon, non-zero" = reachable within 3 hops
  HIGH band      = R123.Strength in the top decile (>= 90th pct) of THAT prime's own direct-
                   edge strengths, and > 0  (per-prime, EXP-1e §9.1)
  LOW band       = R123.Strength in the 10th-25th percentile of that prime's own direct-edge
                   strengths, and > 0       (per-prime, a low NON-zero band)
  W(P,T)         = swow.traverse_count_for_strength(R123.Strength(P->T))   (integer weight map)
  W_gap(P)       = W(P,T_H) - W(P,T_L)      (>= 0 by band construction)
  S0 (weight-blind stratum)  = primes with a candidate (T_H,T_L) where W_gap = 0
  in-degree      = UNWEIGHTED structural in-degree on the INITIAL graph (count of distinct
                   incoming cues), blind to activation, broadcast-invariant (EXP-1e §6.2.0)
  S0 in-degree match = T_H and T_L fall in the SAME global in-degree decile (9 cuts at the
                   10th..90th pct of node in-degree, computed ONCE over all nodes; a value
                   exactly on a decile boundary goes to the LOWER decile)
  S0 tie-break   = among weight-blind AND in-degree-matched candidate pairs, pick the one
                   MINIMISING |indeg(T_H) - indeg(T_L)|; remaining ties broken by the
                   SELECTION_SEED seeded shuffle of the sorted candidate-pair list
  Bottleneck (arm-b distance-2 only) = min(R123.Strength(P->M), R123.Strength(M->T))

Percentile method (a project-authored structural knob, fixed here so selection is
deterministic; the frozen pre-registration fixes the band *cuts* — 90th / 10th-25th pct — but
not the interpolation rule, so it is pinned here): the standard inclusive linear-interpolation
percentile over the SORTED per-prime direct-edge strengths (the "linear"/numpy-default method).
For a prime with a single direct strength the percentile is that value. This is a structural
selection rule, not a relatedness judgement.
"""

from __future__ import annotations

import hashlib
import os
import random
import sys
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import swow
from swow import Topology, traverse_count_for_strength


# ─────────────────────────────────────────────────────────────────────────────
# FROZEN structural knobs (EXP-1e §9.1 / §6.2 / §6.2.0)
# ─────────────────────────────────────────────────────────────────────────────

SELECTION_SEED = 20260621
MIN_OUTDEG = 4
HORIZON_HOPS = 3

HIGH_PCT = 90.0            # HIGH band: strength >= this per-prime percentile (top decile)
LOW_PCT_LO = 10.0         # LOW band: this per-prime percentile ...
LOW_PCT_HI = 25.0         # ... up to this one (inclusive), low non-zero

S0_POWER_FLOOR = 30        # EXP-1e §6.2: N_S0 >= 30 → PRIMARY S0 gate, else FALLBACK


def _rng(seed: int, p: int, tag: str) -> random.Random:
    """A deterministic, per-(prime, tag) RNG. The seed is a STRING built from the integer
    SELECTION_SEED, the prime index, and a stage tag — strings/bytes are stable seed inputs
    to random.Random across processes (no dependence on PYTHONHASHSEED), so every seeded
    shuffle here is byte-identical across interpreters."""
    return random.Random("%d:%d:%s" % (seed, p, tag))


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic percentile (pure stdlib; the "linear" / numpy-default method)
# ─────────────────────────────────────────────────────────────────────────────

def percentile(sorted_vals: Sequence[float], pct: float) -> float:
    """Linear-interpolation percentile over an ALREADY-SORTED ascending sequence.

    Matches numpy.percentile's default ("linear") method, in pure stdlib, so band cuts are
    deterministic. `pct` in [0,100]. Empty → 0.0; single element → that element."""
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    if n == 1:
        return float(sorted_vals[0])
    rank = (pct / 100.0) * (n - 1)         # 0-based fractional rank
    lo = int(rank)
    frac = rank - lo
    if lo >= n - 1:
        return float(sorted_vals[-1])
    return float(sorted_vals[lo] + (sorted_vals[lo + 1] - sorted_vals[lo]) * frac)


# ─────────────────────────────────────────────────────────────────────────────
# Global in-degree deciles (EXP-1e §6.2.0): 9 cuts over ALL nodes' structural in-degree
# ─────────────────────────────────────────────────────────────────────────────

def indegree_decile_cuts(topo: Topology) -> List[float]:
    """The 9 decile cut points (10th..90th percentile) of the GLOBAL node in-degree
    distribution over ALL nodes of the initial graph (EXP-1e §6.2.0). Computed ONCE.

    Uses the same deterministic linear percentile as the bands. Structural, unweighted
    in-degree (topo.indeg = count of distinct incoming cues), blind to activation."""
    indegs = sorted(topo.indeg)            # over ALL nodes (including in-degree 0)
    return [percentile(indegs, p) for p in (10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0)]


def decile_of(indeg: int, cuts: Sequence[float]) -> int:
    """Which global in-degree decile (0..9) a node with the given in-degree falls in.

    `cuts` are the 9 boundary values from indegree_decile_cuts. A value exactly on a
    boundary is assigned to the LOWER decile (EXP-1e §6.2.0: 'boundary ties → lower decile').
    Concretely: decile = number of cut points STRICTLY LESS THAN indeg. So a value equal to a
    cut does NOT cross it (stays in the lower bin)."""
    d = 0
    for c in cuts:
        if indeg > c:
            d += 1
        else:
            break
    return d


# ─────────────────────────────────────────────────────────────────────────────
# Per-prime HIGH / LOW bands (EXP-1e §9.1) — pure topology+strength
# ─────────────────────────────────────────────────────────────────────────────

def _direct_strengths(topo: Topology, p: int) -> List[Tuple[int, float]]:
    """Sorted list of (response_index, R123.Strength) for prime p's direct edges, ascending
    by (strength, response_index) so banding is deterministic. Strengths are > 0 (the loader
    drops <= 0)."""
    out = []
    for r in topo.out[p]:                  # topo.out[p] is a sorted tuple of response indices
        out.append((r, topo.strength[(p, r)]))
    out.sort(key=lambda x: (x[1], x[0]))
    return out


def high_low_bands(topo: Topology, p: int) -> Tuple[List[int], List[int]]:
    """Return (high_targets, low_targets) for prime p by the frozen per-prime band rule.

    HIGH = direct responses with strength >= the 90th percentile of p's own direct-edge
    strengths, and > 0. LOW = direct responses with strength in [10th pct, 25th pct] of p's
    own direct-edge strengths, and > 0. Both lists are returned sorted by response index
    (determinism). Pure: reads only SWOW topology + strength."""
    ds = _direct_strengths(topo, p)
    if not ds:
        return [], []
    strengths = [s for _, s in ds]         # already ascending
    hi_cut = percentile(strengths, HIGH_PCT)
    lo_lo = percentile(strengths, LOW_PCT_LO)
    lo_hi = percentile(strengths, LOW_PCT_HI)

    high = sorted(r for r, s in ds if s >= hi_cut and s > 0.0)
    low = sorted(r for r, s in ds if (lo_lo <= s <= lo_hi) and s > 0.0)
    return high, low


# ─────────────────────────────────────────────────────────────────────────────
# Candidate primes (EXP-1e §9.1): out-degree >= MIN_OUTDEG, sorted then seeded-shuffled
# ─────────────────────────────────────────────────────────────────────────────

def candidate_primes(topo: Topology, *, seed: int = SELECTION_SEED,
                     min_outdeg: int = MIN_OUTDEG) -> List[int]:
    """Prime indices with out-degree >= min_outdeg, in the deterministic select_pairs order:
    sorted ascending, then a SINGLE seeded shuffle (so the order is fixed given the seed)."""
    primes = [i for i in range(topo.n) if len(topo.out[i]) >= min_outdeg]
    primes.sort()
    random.Random(seed).shuffle(primes)
    return primes


# ─────────────────────────────────────────────────────────────────────────────
# Arm (b) distance-1 selection: HIGH-direct vs LOW-direct (EXP-1e §9.2)
# ─────────────────────────────────────────────────────────────────────────────

def select_arm_b_d1(topo: Topology, p: int, *, seed: int = SELECTION_SEED
                    ) -> Optional[Tuple[int, int]]:
    """For prime p, pick ONE (T_H, T_L) distance-1 pair: a HIGH-band direct response and a
    LOW-band direct response (both 1 hop, both > 0). Deterministic: among the sorted
    candidate (T_H, T_L) pairs, a seeded shuffle picks one. Returns None if either band is
    empty (the prime does not populate arm (b)-d1). Pure topology+strength."""
    high, low = high_low_bands(topo, p)
    if not high or not low:
        return None
    pairs = sorted((h, l) for h in high for l in low if h != l)
    if not pairs:
        return None
    rng = _rng(seed, p, "b_d1")   # per-prime seeded, deterministic
    rng.shuffle(pairs)
    return pairs[0]


# ─────────────────────────────────────────────────────────────────────────────
# Arm (a) selection: STRONG-RELATED (HIGH direct) vs MATCHED-UNRELATED-BUT-REACHABLE
# (in-horizon, no direct edge), distance recorded (EXP-1e §9.2)
# ─────────────────────────────────────────────────────────────────────────────

def select_arm_a(topo: Topology, p: int, *, seed: int = SELECTION_SEED,
                 horizon_hops: int = HORIZON_HOPS
                 ) -> Optional[Tuple[int, int, int]]:
    """For prime p, pick (T_strong, T_unrelated_reachable, hop_distance_of_control).

    T_strong = a HIGH-band direct response (1 hop). T_unrelated_reachable = a node reachable
    from p within horizon_hops with NO direct p->target edge (so its association strength is
    absent), drawn from the sorted in-horizon pool; its hop distance is recorded. Returns None
    if no HIGH target or no in-horizon non-direct node exists. Pure topology only."""
    high, _ = high_low_bands(topo, p)
    if not high:
        return None

    # in-horizon non-direct pool, with hop distance recorded (BFS layers)
    direct = topo.out_set[p]
    seen = {p}
    frontier = {p}
    dist: Dict[int, int] = {}
    for hop in range(1, horizon_hops + 1):
        nxt = set()
        for u in frontier:
            for v in topo.out[u]:
                if v not in seen:
                    seen.add(v)
                    dist[v] = hop
                    nxt.add(v)
        frontier = nxt
        if not frontier:
            break
    control_pool = sorted(t for t in dist
                          if t != p and t not in direct and topo.indeg[t] > 0)
    if not control_pool:
        return None

    rng = _rng(seed, p, "a")
    strong = sorted(high)
    rng_h = _rng(seed, p, "a_strong")
    rng_h.shuffle(strong)
    t_strong = strong[0]

    pool = list(control_pool)
    rng.shuffle(pool)
    t_ctrl = pool[0]
    return t_strong, t_ctrl, dist[t_ctrl]


# ─────────────────────────────────────────────────────────────────────────────
# Arm (b) distance-2 (OPTIONAL sub-arm): HIGH-2hop vs LOW-2hop by bottleneck (EXP-1e §9.2)
# ─────────────────────────────────────────────────────────────────────────────

def _two_hop_bottlenecks(topo: Topology, p: int) -> Dict[int, float]:
    """For each node T reachable from p at EXACTLY 2 hops (P->M->T) and NOT a direct response
    of p (and != p), the bottleneck path-strength = max over intermediates M of
    min(strength(P->M), strength(M->T)) — the strongest weakest-link path. (Max over M so a
    target with several 2-hop paths is scored by its best one; the per-path strength is the
    standard weakest-link bottleneck.) Pure topology+strength."""
    direct = topo.out_set[p]
    one_hop = set(topo.out[p])
    best: Dict[int, float] = {}
    for m in topo.out[p]:
        s_pm = topo.strength[(p, m)]
        for t in topo.out[m]:
            if t == p or t in direct or t in one_hop:
                continue
            bott = min(s_pm, topo.strength[(m, t)])
            if bott > best.get(t, -1.0):
                best[t] = bott
    return best


def select_arm_b_d2(topo: Topology, p: int, *, seed: int = SELECTION_SEED
                    ) -> Optional[Tuple[int, int]]:
    """OPTIONAL arm-(b) distance-2 sub-arm: pick (T_high2, T_low2), both reachable at exactly
    2 hops and not direct, binned HIGH vs LOW by 2-hop bottleneck path-strength using the SAME
    per-distribution band rule (top decile vs 10th-25th pct of THIS prime's 2-hop bottleneck
    strengths). Returns None if either band is empty. Deterministic. Pure topology+strength."""
    bott = _two_hop_bottlenecks(topo, p)
    if len(bott) < 2:
        return None
    items = sorted(bott.items(), key=lambda kv: (kv[1], kv[0]))
    strengths = [s for _, s in items]
    hi_cut = percentile(strengths, HIGH_PCT)
    lo_lo = percentile(strengths, LOW_PCT_LO)
    lo_hi = percentile(strengths, LOW_PCT_HI)
    high = sorted(t for t, s in items if s >= hi_cut and s > 0.0)
    low = sorted(t for t, s in items if (lo_lo <= s <= lo_hi) and s > 0.0)
    if not high or not low:
        return None
    pairs = sorted((h, l) for h in high for l in low if h != l)
    if not pairs:
        return None
    rng = _rng(seed, p, "b_d2")
    rng.shuffle(pairs)
    return pairs[0]


# ─────────────────────────────────────────────────────────────────────────────
# S0 weight-blind + in-degree-matched selection (EXP-1e §6.2 / §6.2.0)
# ─────────────────────────────────────────────────────────────────────────────

def w_of(topo: Topology, p: int, t: int) -> int:
    """The integer bare-weight W(P,T) = traverse_count_for_strength(R123.Strength(P->T))."""
    return traverse_count_for_strength(topo.strength[(p, t)])


def select_s0_pair(topo: Topology, p: int, cuts: Sequence[float], *,
                   seed: int = SELECTION_SEED
                   ) -> Optional[Tuple[int, int]]:
    """For prime p, select the S0 (T_H, T_L) pair that is BOTH weight-blind (W_gap = 0) AND
    in-degree-matched (T_H, T_L in the same global in-degree decile), per EXP-1e §6.2 + §6.2.0.

    Candidate pairs are all (T_H in HIGH band, T_L in LOW band, T_H != T_L) with
    W(P,T_H) == W(P,T_L) (W_gap = 0) AND decile_of(indeg(T_H)) == decile_of(indeg(T_L)).
    Among them pick the pair MINIMISING |indeg(T_H) - indeg(T_L)| (tightest popularity match);
    remaining ties broken by the seeded shuffle of the sorted candidate-pair list. Returns
    None if the prime has no such pair (it is then DROPPED from S0). Pure topology+strength
    (+ structural in-degree); blind to activation."""
    high, low = high_low_bands(topo, p)
    if not high or not low:
        return None
    cands: List[Tuple[int, int]] = []
    for h in high:
        wh = w_of(topo, p, h)
        dh = decile_of(topo.indeg[h], cuts)
        for l in low:
            if h == l:
                continue
            if w_of(topo, p, l) != wh:           # weight-blind: W_gap = 0
                continue
            if decile_of(topo.indeg[l], cuts) != dh:   # in-degree-matched: same decile
                continue
            cands.append((h, l))
    if not cands:
        return None
    cands.sort()                                  # deterministic base order
    rng = _rng(seed, p, "s0")
    rng.shuffle(cands)
    # tightest |Δindeg| first; Python's sort is STABLE, so among equal |Δindeg| the order is
    # the seeded-shuffled order above — i.e. ties are broken by the SELECTION_SEED shuffle.
    cands.sort(key=lambda pr: abs(topo.indeg[pr[0]] - topo.indeg[pr[1]]))
    return cands[0]


# ─────────────────────────────────────────────────────────────────────────────
# The full blind selection over a Topology (no activation, no engine)
# ─────────────────────────────────────────────────────────────────────────────

class Selection:
    """The result of the blind three-arm selection (word-space). Instrumentation/stimulus
    only; carries NO activation and NO verdict.

    arm_a   : list of dicts {prime, strong, control, control_hops}
    arm_b_d1: list of dicts {prime, high, low, w_high, w_low, indeg_high, indeg_low}
    arm_b_d2: list of dicts {prime, high2, low2}
    arm_c   : list of dicts {prime, targets: [(response, strength), ...]}
    s0      : list of dicts {prime, high, low, indeg_high, indeg_low, decile} (W_gap=0 AND matched)
    s_plus_count : N_S+ (arm-b-d1 primes with W_gap > 0)
    s0_indeg_drop_count : primes with a weight-blind pair but NO in-degree-matched pair
    decile_cuts : the 9 global in-degree decile cut points
    n_primes_requested / n_arm_b_d1_primes : reporting counts
    """

    def __init__(self):
        self.arm_a: List[dict] = []
        self.arm_b_d1: List[dict] = []
        self.arm_b_d2: List[dict] = []
        self.arm_c: List[dict] = []
        self.s0: List[dict] = []
        self.s_plus_count = 0
        self.s0_indeg_drop_count = 0
        self.decile_cuts: List[float] = []
        self.n_primes_requested = 0
        self.n_arm_b_d1_primes = 0


def select(topo: Topology, n_primes: int, *, seed: int = SELECTION_SEED,
           min_outdeg: int = MIN_OUTDEG, horizon_hops: int = HORIZON_HOPS) -> Selection:
    """Run the full BLIND three-arm selection over `topo` for up to `n_primes` primes.

    Walks the seeded candidate-prime order; for each prime constructs whatever arms it can
    populate (per-arm N is independent, EXP-1e §9.3). Stops once `n_primes` primes have
    contributed to arm (b)-d1 (the headline categorical arm), since that is the gating
    population; arms (a)/(c) and the S0 stratum are computed for those same primes.

    Pure: topology + R123.Strength + structural in-degree ONLY. No activation, no engine,
    no verdict — stimulus construction for the validator's later graded run.
    """
    sel = Selection()
    sel.n_primes_requested = n_primes
    cuts = indegree_decile_cuts(topo)
    sel.decile_cuts = cuts

    for p in candidate_primes(topo, seed=seed, min_outdeg=min_outdeg):
        if sel.n_arm_b_d1_primes >= n_primes:
            break
        bd1 = select_arm_b_d1(topo, p, seed=seed)
        if bd1 is None:
            continue   # the prime cannot populate the headline arm; skip it
        t_h, t_l = bd1
        w_h, w_l = w_of(topo, p, t_h), w_of(topo, p, t_l)
        sel.arm_b_d1.append({
            "prime": topo.words[p], "high": topo.words[t_h], "low": topo.words[t_l],
            "w_high": w_h, "w_low": w_l,
            "indeg_high": topo.indeg[t_h], "indeg_low": topo.indeg[t_l],
        })
        sel.n_arm_b_d1_primes += 1

        # S+ / S0 accounting on the SAME arm-(b)-d1 contrast
        if w_h - w_l > 0:
            sel.s_plus_count += 1

        # S0: a weight-blind pair must exist AND be in-degree-matched. The drop count is for
        # primes that HAVE a weight-blind candidate pair but NO in-degree-matched one.
        s0pair = select_s0_pair(topo, p, cuts, seed=seed)
        if s0pair is not None:
            sh, sl = s0pair
            sel.s0.append({
                "prime": topo.words[p], "high": topo.words[sh], "low": topo.words[sl],
                "indeg_high": topo.indeg[sh], "indeg_low": topo.indeg[sl],
                "decile": decile_of(topo.indeg[sh], cuts),
            })
        else:
            if _has_weight_blind_pair(topo, p):
                sel.s0_indeg_drop_count += 1

        # arm (a)
        a = select_arm_a(topo, p, seed=seed, horizon_hops=horizon_hops)
        if a is not None:
            ts, tc, ch = a
            sel.arm_a.append({
                "prime": topo.words[p], "strong": topo.words[ts],
                "control": topo.words[tc], "control_hops": ch,
            })

        # arm (b) d2 (optional)
        d2 = select_arm_b_d2(topo, p, seed=seed)
        if d2 is not None:
            h2, l2 = d2
            sel.arm_b_d2.append({
                "prime": topo.words[p], "high2": topo.words[h2], "low2": topo.words[l2],
            })

        # arm (c): full direct strength range
        ds = _direct_strengths(topo, p)
        sel.arm_c.append({
            "prime": topo.words[p],
            "targets": [(topo.words[r], s) for r, s in ds],
        })

    return sel


def _has_weight_blind_pair(topo: Topology, p: int) -> bool:
    """True iff prime p has ANY (T_H in HIGH, T_L in LOW, H != L) pair with W_gap = 0 — used
    to count primes dropped from S0 specifically for FAILING in-degree matching (they had a
    weight-blind pair but no in-degree-matched one). Pure topology+strength."""
    high, low = high_low_bands(topo, p)
    if not high or not low:
        return False
    for h in high:
        wh = w_of(topo, p, h)
        for l in low:
            if h != l and w_of(topo, p, l) == wh:
                return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Pair-list persistence (one file per arm) + SHA-256 (EXP-1e §9.3 / §10.1)
# ─────────────────────────────────────────────────────────────────────────────

def _write_lines(path: str, header: str, lines: Sequence[str]) -> str:
    """Write a UTF-8 file (header + lines) and return its SHA-256 hex digest. Deterministic:
    the caller passes lines already in selection order."""
    content = header + "".join(lines)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def save_pair_lists(sel: Selection, outdir: str) -> Dict[str, str]:
    """Persist the per-arm pair lists verbatim (one file per arm, EXP-1e §9.3) and return a
    dict of {artifact_name: sha256}. The validator pastes these into EXP-1e §10.1 in the
    follow-up freeze commit — this module does NOT edit the pre-registration."""
    os.makedirs(outdir, exist_ok=True)
    hashes: Dict[str, str] = {}

    hashes["arm_a"] = _write_lines(
        os.path.join(outdir, "priming_1e_pairs_arm_a.txt"),
        "# prime\tstrong_related\tunrelated_reachable\tcontrol_hops\n",
        ["%s\t%s\t%s\t%d\n" % (d["prime"], d["strong"], d["control"], d["control_hops"])
         for d in sel.arm_a],
    )
    hashes["arm_b_d1"] = _write_lines(
        os.path.join(outdir, "priming_1e_pairs_arm_b_d1.txt"),
        "# prime\thigh_direct\tlow_direct\tw_high\tw_low\tindeg_high\tindeg_low\n",
        ["%s\t%s\t%s\t%d\t%d\t%d\t%d\n" % (d["prime"], d["high"], d["low"], d["w_high"],
                                           d["w_low"], d["indeg_high"], d["indeg_low"])
         for d in sel.arm_b_d1],
    )
    if sel.arm_b_d2:
        hashes["arm_b_d2"] = _write_lines(
            os.path.join(outdir, "priming_1e_pairs_arm_b_d2.txt"),
            "# prime\thigh_2hop\tlow_2hop\n",
            ["%s\t%s\t%s\n" % (d["prime"], d["high2"], d["low2"]) for d in sel.arm_b_d2],
        )
    else:
        hashes["arm_b_d2"] = "DROPPED (sub-arm not populated)"

    hashes["arm_c"] = _write_lines(
        os.path.join(outdir, "priming_1e_pairs_arm_c.txt"),
        "# prime\tresponse\tr123_strength\n",
        ["%s\t%s\t%s\n" % (d["prime"], r, repr(s))
         for d in sel.arm_c for (r, s) in d["targets"]],
    )
    hashes["s0"] = _write_lines(
        os.path.join(outdir, "priming_1e_pairs_s0.txt"),
        "# prime\thigh\tlow\tindeg_high\tindeg_low\tdecile\n",
        ["%s\t%s\t%s\t%d\t%d\t%d\n" % (d["prime"], d["high"], d["low"], d["indeg_high"],
                                       d["indeg_low"], d["decile"]) for d in sel.s0],
    )
    return hashes


# ─────────────────────────────────────────────────────────────────────────────
# Banner + N_S0 / N_S+ feasibility checkpoint (stimulus construction, NOT a graded number)
# ─────────────────────────────────────────────────────────────────────────────

def print_preregistration_banner() -> None:
    """Print the frozen selection PROCEDURE banner first (EXP-1e §10), before loading data,
    so the captured stdout records that selection was blind and seeded. No activation here."""
    print("=" * 78)
    print("EXP-1e — BLIND three-arm stimulus selection (SPEC-1e §10) — pre-registered")
    print("=" * 78)
    print("This is STIMULUS CONSTRUCTION ONLY — topology + R123.Strength, blind to activation.")
    print("It computes NO activation, NO Δ, NO verdict (the validator's graded run does that).")
    print("FROZEN KNOBS: SELECTION_SEED=%d  MIN_OUTDEG=%d  HORIZON_HOPS=%d"
          % (SELECTION_SEED, MIN_OUTDEG, HORIZON_HOPS))
    print("  HIGH band = >= %gth pct of prime's own direct strengths (>0);"
          " LOW band = %g-%gth pct (>0)." % (HIGH_PCT, LOW_PCT_LO, LOW_PCT_HI))
    print("  W(P,T) = min(%d, 1+floor(strength*%d)); W_gap = W(high)-W(low);"
          % (swow.STRENGTH_CAP, swow.STRENGTH_SCALE))
    print("  S0 = W_gap=0 AND high/low share a global in-degree decile (boundary→lower).")
    print("  S0 tie-break: min |Δindeg| then SELECTION_SEED shuffle. In-degree = structural,")
    print("                unweighted, initial-graph, activation-blind, broadcast-invariant.")
    print("N_S0 >= %d → PRIMARY S0 loop-work gate; else FALLBACK (V = r_MA - r_W >= 0.20)."
          % S0_POWER_FLOOR)
    print("=" * 78)
    print()
    sys.stdout.flush()


def run_selection_on_swow(n_primes: int = 300, *, data_path: Optional[str] = None) -> int:
    """Blind-select on the real SWOW data (if present), persist per-arm pair lists + hashes,
    and report N_S0 / N_S+ as an explicit GO/NO-GO. Computes NO activation / NO graded number.

    Returns an exit code: 0 if selection ran (regardless of GO/NO-GO — the go/no-go is a
    reported structural fact, not a runner failure), 2 if the SWOW data file is absent."""
    print_preregistration_banner()

    try:
        edges = swow.load_edges() if data_path is None else swow.load_edges(data_path)
    except swow.SwowMissing as e:
        print("DATA NOT AVAILABLE — selection cannot run; N_S0/N_S+ are PENDING DATA.\n")
        print(str(e))
        return 2

    print("loaded %d directed edges (strength>0, no self-loops)." % len(edges))
    topo = Topology(edges)
    print("topology: %d nodes." % topo.n)

    sel = select(topo, n_primes)
    outdir = os.path.join(_HERE, "results")
    hashes = save_pair_lists(sel, outdir)

    n_s0 = len(sel.s0)
    n_splus = sel.s_plus_count
    print()
    print("SELECTION COMPLETE (blind, seed=%d). Per-arm N (reported separately):" % SELECTION_SEED)
    print("  arm (a)      N = %d" % len(sel.arm_a))
    print("  arm (b) d1   N = %d   (the headline categorical population)" % len(sel.arm_b_d1))
    print("  arm (b) d2   N = %d   %s"
          % (len(sel.arm_b_d2), "(sub-arm populated)" if sel.arm_b_d2 else "(DROPPED — not populated)"))
    print("  arm (c)      N = %d" % len(sel.arm_c))
    print()
    print("LOOP-WORK LEVERAGE STRATUM S0 (EXP-1e §6.2 / §6.2.0):")
    print("  N_S0  (W_gap=0 AND in-degree-matched) = %d" % n_s0)
    print("  N_S+  (W_gap>0, arm-b-d1 primes)       = %d" % n_splus)
    print("  primes DROPPED from S0 for failing in-degree match = %d" % sel.s0_indeg_drop_count)
    print("  global in-degree decile cuts (10th..90th pct) = %s"
          % ", ".join("%g" % c for c in sel.decile_cuts))
    print()
    print("PER-ARM PAIR-LIST SHA-256 (for the validator's §10.1 follow-up freeze):")
    for name in ("arm_a", "arm_b_d1", "arm_b_d2", "arm_c", "s0"):
        print("  %-10s %s" % (name, hashes[name]))
    print()

    # GO / NO-GO (a reported structural fact, NOT a graded number)
    print("=" * 78)
    if n_s0 >= S0_POWER_FLOOR:
        print("GO/NO-GO: GO — N_S0 = %d >= %d. The PRIMARY S0 loop-work gate is powered."
              % (n_s0, S0_POWER_FLOOR))
    else:
        print("GO/NO-GO: NO-GO (S0 underpowered) — N_S0 = %d < %d." % (n_s0, S0_POWER_FLOOR))
        print("  With BOTH the edge-weight path (W_gap=0) AND the target-popularity path")
        print("  (in-degree matching) controlled, SWOW does not supply >= %d clean leverage"
              % S0_POWER_FLOOR)
        print("  pairs. This is an HONEST, INFORMATIVE STRUCTURAL result (EXP-1e §6.2), learned")
        print("  BEFORE any graded run; the verdict routes to the frozen N_S0<30 FALLBACK")
        print("  (V = r_MA - r_W >= 0.20). The in-degree tolerance is NOT widened to manufacture")
        print("  a powered S0. (No activation/graded number is computed here.)")
    print("=" * 78)
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_selection_on_swow())
