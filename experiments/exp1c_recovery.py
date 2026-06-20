"""
EXP-1c — SWOW community-structure recovery  (§6.2 MEANING bar for step 1c).

Grades whether the 1c source-clustering (src/nous_source_clustering.py, cluster_sources) agrees
with an EXTERNAL community partition of the SWOW graph BETTER than the spec's no-clustering
control, on blindly-selected probe source-sets, by Adjusted Rand Index (Hubert & Arabie 1985).

ORDER OF OPERATIONS (anti-circularity — do not reorder):
  1. The external partition is frozen FIRST by experiments/exp1c_build_partition.py (a DIFFERENT
     algorithm family — Louvain), written to results/exp1c_external_partition.tsv with a SHA-256
     recorded in docs/experiments/EXP-1c-swow-recovery.md §3.1.
  2. This script LOADS that frozen file, verifies its SHA-256 against the value passed in
     (EXP1C_EXPECTED_SHA256 env or --sha argument), and REFUSES to run if it does not match —
     so the labels cannot have been silently regenerated after seeing a result.
  3. Probe sets are selected BLIND from topology + the frozen labels only (never from any Nous
     output). Only THEN is cluster_sources called and ARI computed.

This script DOES import the method under test (src/nous_source_clustering.cluster_sources) and
the harness (build_graph_from_spec) — that is correct: it is the grader, run after the labels
are frozen. It never modifies src/. Pure reads on the store.

USAGE (after pasting the frozen hash into the pre-registration):
    EXP1C_EXPECTED_SHA256=<hash from generator> python3 experiments/exp1c_recovery.py
  (optional fast smoke, NON-canonical:
    NOUS_EXP1C_MAXROWS=200000 EXP1C_PARTITION=results/exp1c_external_partition_SMOKE.tsv \
    EXP1C_EXPECTED_SHA256=<smoke hash> python3 experiments/exp1c_recovery.py)
"""

from __future__ import annotations

import hashlib
import os
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import swow  # noqa: E402
from harness import build_graph_from_spec, SRC_DIR  # noqa: E402

# the method under test (the grader is ALLOWED to import it; labels are already frozen)
sys.path.insert(0, SRC_DIR)
from nous_source_clustering import cluster_sources  # noqa: E402

# ── pre-registered constants (frozen; see docs/experiments/EXP-1c-swow-recovery.md) ──────
SEED = 20250620
N_PROBES = 200
N_NEAR = 4               # direct (1-hop) responses of the seed word in each probe
N_FAR = 4               # words unreachable within K_UNRELATED hops of the seed
MIN_OUTDEG = 4           # seed word must have SWOW out-degree >= this
K_UNRELATED = 4          # FAR = not reachable from seed within this many hops
# probe size = 1 (seed) + N_NEAR + N_FAR = 9 words.

ARI_ABS_THRESH = 0.30    # P-a
LIFT_THRESH = 0.15       # P-b
SIGN_P_THRESH = 0.05     # P-c

RESULTS_DIR = os.path.join(_HERE, "results")
DEFAULT_PARTITION = os.path.join(RESULTS_DIR, "exp1c_external_partition.tsv")


# ─────────────────────────────────────────────────────────────────────────────
# Adjusted Rand Index (Hubert & Arabie 1985), from scratch, stdlib only.
# ─────────────────────────────────────────────────────────────────────────────

def _comb2(n: int) -> int:
    return n * (n - 1) // 2


def adjusted_rand_index(labels_a: List[int], labels_b: List[int]) -> float:
    """ARI between two labelings of the same N items. Returns 1.0 for identical partitions,
    ~0.0 for independent ones; can be negative. Defined via the contingency table.

    Convention for the degenerate case where ARI is 0/0 (both partitions put everything in a
    single cluster, OR both are all-singletons): return 1.0 iff the two partitions are equal,
    else 0.0 — the standard scikit-learn convention. This matters because our no-clustering
    control IS all-singletons.
    """
    assert len(labels_a) == len(labels_b)
    n = len(labels_a)
    if n == 0:
        return 1.0
    # contingency
    contingency: Dict[Tuple[int, int], int] = defaultdict(int)
    a_counts: Dict[int, int] = defaultdict(int)
    b_counts: Dict[int, int] = defaultdict(int)
    for x, y in zip(labels_a, labels_b):
        contingency[(x, y)] += 1
        a_counts[x] += 1
        b_counts[y] += 1

    sum_comb_c = sum(_comb2(v) for v in contingency.values())
    sum_comb_a = sum(_comb2(v) for v in a_counts.values())
    sum_comb_b = sum(_comb2(v) for v in b_counts.values())
    total_comb = _comb2(n)

    expected = (sum_comb_a * sum_comb_b) / total_comb if total_comb else 0.0
    max_index = 0.5 * (sum_comb_a + sum_comb_b)
    denom = max_index - expected
    if denom == 0.0:
        # denom == 0 happens ONLY when both partitions are all-singletons (sum_comb == 0) or
        # both are a single cluster (sum_comb == total): max_index == expected forces
        # sum_comb_a == sum_comb_b in {0, total}. In either case the two partitions are the
        # SAME partition up to relabeling, so ARI == 1.0 (the scikit-learn convention). Raw
        # list equality is wrong here: [0,0,0] and [7,7,7] are the same one-cluster partition
        # with different label values, and [0,1,2] vs [3,4,5] the same all-singletons one.
        return 1.0
    return (sum_comb_c - expected) / denom


# ─────────────────────────────────────────────────────────────────────────────
# Frozen-partition load + hash verification.
# ─────────────────────────────────────────────────────────────────────────────

def load_partition(path: str, expected_sha256: str) -> Dict[str, int]:
    if not os.path.exists(path):
        raise SystemExit("FATAL: frozen partition not found at %s — run "
                         "experiments/exp1c_build_partition.py first." % path)
    with open(path, "r", encoding="utf-8") as fh:
        body = fh.read()
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if not expected_sha256:
        raise SystemExit(
            "FATAL: no expected SHA-256 supplied (set EXP1C_EXPECTED_SHA256). The actual hash "
            "of %s is:\n  %s\nPaste it into docs/experiments/EXP-1c-swow-recovery.md §3.1 and "
            "pass it back via EXP1C_EXPECTED_SHA256 so the labels are provably frozen." %
            (path, digest))
    if digest != expected_sha256:
        raise SystemExit(
            "FATAL: frozen-partition hash MISMATCH.\n  expected: %s\n  actual:   %s\n"
            "The external labels differ from the pre-registered, frozen partition. Refusing to "
            "run (anti-circularity)." % (expected_sha256, digest))
    labels: Dict[str, int] = {}
    for line in body.splitlines():
        if not line:
            continue
        word, cid = line.rsplit("\t", 1)
        labels[word] = int(cid)
    return labels


# ─────────────────────────────────────────────────────────────────────────────
# BLIND probe selection (topology + frozen labels only; never touches the engine).
# ─────────────────────────────────────────────────────────────────────────────

def select_probes(topo, labels: Dict[str, int], seed: int):
    """Return a list of probe sets, selected BLIND by SWOW topology and graded against the
    FROZEN external labels. Each probe is a dict:
        {"words": [9 words], "truth": [9 ints], "seed_word": str}
    where `truth[i]` is the FROZEN external community id of words[i] (the ground truth), NOT a
    function of the near/far topological recipe used to pick the words.

    Selection (the Phase 2B `select_pairs` discipline — direct vs unrelated):
      seed P with out-degree >= MIN_OUTDEG; NEAR = P + N_NEAR direct responses of P;
      FAR = N_FAR words with in-degree>0 not reachable from P within K_UNRELATED hops.
    Kept only if the 9 words all carry an external label (>=0) and span >= 2 external
    communities (so ARI is informative). This keep-filter reads the EXTERNAL labels only.

    Does NOT call cluster_sources / spread_activation / anything in the engine. Deterministic.
    """
    import random
    rng = random.Random(seed)

    # candidate seeds: out-degree >= MIN_OUTDEG, sorted then seeded-shuffled (select_pairs style)
    seeds = [i for i in range(topo.n) if len(topo.out[i]) >= MIN_OUTDEG]
    seeds.sort()
    rng.shuffle(seeds)

    indeg_pos = [i for i in range(topo.n) if topo.indeg[i] > 0]  # sorted (range order)

    probes = []
    seen_keys = set()
    for p in seeds:
        if len(probes) >= N_PROBES:
            break
        direct = sorted(topo.out_set[p])
        if len(direct) < N_NEAR:
            continue
        reach = topo.reachable_within(p, K_UNRELATED)
        far_pool = [t for t in indeg_pos if t not in reach and t != p]
        if len(far_pool) < N_FAR:
            continue

        near_idx = rng.sample(direct, N_NEAR)
        far_idx = rng.sample(far_pool, N_FAR)
        idxs = [p] + near_idx + far_idx
        words = [topo.words[i] for i in idxs]

        # external labels (ground truth); require all labelled and >= 2 communities
        if any(w not in labels or labels[w] < 0 for w in words):
            continue
        truth = [labels[w] for w in words]
        if len(set(truth)) < 2:
            continue

        key = tuple(sorted(words))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        probes.append({"words": words, "truth": truth, "seed_word": topo.words[p]})

    if len(probes) < N_PROBES:
        # honest: report how many we could build; the run proceeds with what exists but the
        # verdict notes the shortfall (a too-small N would itself be a finding).
        print("  NOTE: built %d/%d probes (seed pool exhausted under the fixed topology rule)."
              % (len(probes), N_PROBES))
    return probes


# ─────────────────────────────────────────────────────────────────────────────
# Partition helpers: turn a clustering into a per-word integer label list.
# ─────────────────────────────────────────────────────────────────────────────

def clustering_to_labels(clustering, word_to_id: Dict[str, str], words: List[str]) -> List[int]:
    """Map each probe word to the integer index of the SourceGroup it landed in. Words must be
    in the same order as `words`. A word missing from the clustering (should not happen — all
    probe words exist in the store) is given a unique singleton label."""
    # build id -> group index
    gid_of: Dict[str, int] = {}
    for i, g in enumerate(clustering.groups):
        for m in g.members:
            gid_of[m] = i
    labels = []
    next_singleton = len(clustering.groups) + 1
    for w in words:
        nid = word_to_id[w]
        if nid in gid_of:
            labels.append(gid_of[nid])
        else:
            labels.append(next_singleton)
            next_singleton += 1
    return labels


def random_partition_labels(n: int, n_blocks: int, seed: int) -> List[int]:
    """A random partition of n items into exactly the given number of blocks (matched on block
    count, NOT handed the truth). If n_blocks < 1 or > n it is clamped to [1, n]."""
    import random
    rng = random.Random(seed)
    n_blocks = max(1, min(n_blocks, n))
    # ensure each block used at least once, then fill the rest randomly
    assign = list(range(n_blocks)) + [rng.randrange(n_blocks) for _ in range(n - n_blocks)]
    rng.shuffle(assign)
    return assign


# ─────────────────────────────────────────────────────────────────────────────
# Sign test (exact two-sided binomial) — stdlib only.
# ─────────────────────────────────────────────────────────────────────────────

def sign_test_two_sided(wins: int, losses: int) -> float:
    """Exact two-sided sign test p-value over (wins+losses) non-tie trials under p=0.5."""
    n = wins + losses
    if n == 0:
        return 1.0
    from math import comb
    k = min(wins, losses)
    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2.0 ** n)
    p = 2.0 * tail
    return min(1.0, p)


# ─────────────────────────────────────────────────────────────────────────────
# Main.
# ─────────────────────────────────────────────────────────────────────────────

def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _median(xs: List[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else 0.5 * (s[mid - 1] + s[mid])


def main() -> int:
    expected_sha = os.environ.get("EXP1C_EXPECTED_SHA256", "").strip()
    partition_path = os.environ.get("EXP1C_PARTITION", DEFAULT_PARTITION)
    if not os.path.isabs(partition_path):
        partition_path = os.path.join(_HERE, partition_path)
    maxrows_env = os.environ.get("NOUS_EXP1C_MAXROWS")

    print("=" * 72)
    print("EXP-1c — SWOW community recovery (MEANING bar, §6.2)")
    print("Method under test: cluster_sources (1c, single-link / A1 road-strength).")
    print("External labels: FROZEN Louvain partition (different algorithm family).")
    print("=" * 72)

    # ---- pre-registration ECHO (printed BEFORE any result) ----
    print("\nPRE-REGISTERED (frozen in docs/experiments/EXP-1c-swow-recovery.md):")
    print("  N_PROBES=%d  probe=1 seed + %d near(1-hop) + %d far(>%d-hop) = %d words  seed=%d"
          % (N_PROBES, N_NEAR, N_FAR, K_UNRELATED, 1 + N_NEAR + N_FAR, SEED))
    print("  P-a  mean ARI(1c)        >= %.2f" % ARI_ABS_THRESH)
    print("  P-b  mean ARI(1c) - ARI(none) >= %.2f  (1c higher)" % LIFT_THRESH)
    print("  P-c  sign test ARI(1c)>ARI(none) across probes: p < %.2f" % SIGN_P_THRESH)
    print("  sanity: mean ARI(random) ~ 0")
    print("  VERDICT = EARNED iff P-a AND P-b AND P-c all hold AND random sanity holds.")

    # ---- load + verify frozen labels (refuses on hash mismatch) ----
    labels = load_partition(partition_path, expected_sha)
    print("\nfrozen partition loaded + hash VERIFIED: %s" % partition_path)
    print("  labelled words: %d" % sum(1 for v in labels.values() if v >= 0))

    # ---- build the SWOW store via the existing harness (the substrate 1c reads) ----
    edges = swow.load_edges()
    if maxrows_env is not None:
        edges = edges[: int(maxrows_env)]
        print("  SMOKE MODE: %d edges" % len(edges))
    # topology index for BLIND selection (built from the SAME edges; reads no engine output)
    topo = swow.Topology(edges)
    spec = swow.build_spec(edges)
    print("\nbuilding SWOW store (this is the ~1.39M-road build; please wait) ...")
    inst = build_graph_from_spec(spec)
    store = inst.store
    word_to_id = inst.ids
    print("  store built: %d nodes, %d roads" % (store.node_count(), store.road_count()))

    # restrict labels to words actually in the store (they all are, but be safe)
    labels = {w: c for w, c in labels.items() if w in word_to_id}

    # ---- BLIND probe selection (topology + frozen labels only; no engine) ----
    probes = select_probes(topo, labels, SEED)
    print("\nselected %d blind probe sets (topology select; frozen labels = ground truth)."
          % len(probes))
    if not probes:
        raise SystemExit("FATAL: no probes selected; cannot grade.")

    # ---- grade every probe by all three conditions with the identical ARI fn ----
    ari_1c: List[float] = []
    ari_none: List[float] = []
    ari_rand: List[float] = []
    group_counts: List[int] = []
    singleton_probes = 0
    wins = losses = ties = 0

    for pi, probe in enumerate(probes):
        words = probe["words"]
        truth = probe["truth"]
        # 1c: equal energy so membership is energy-independent
        energies = {word_to_id[w]: 1.0 for w in words}
        clustering = cluster_sources(store, energies)
        pred_1c = clustering_to_labels(clustering, word_to_id, words)
        a1 = adjusted_rand_index(pred_1c, truth)

        # no-clustering control: every word its own group
        pred_none = list(range(len(words)))
        an = adjusted_rand_index(pred_none, truth)

        # random control: matched on the block count 1c produced for this probe
        n_blocks_1c = len(set(pred_1c))
        pred_rand = random_partition_labels(len(words), n_blocks_1c, SEED + pi)
        ar = adjusted_rand_index(pred_rand, truth)

        ari_1c.append(a1)
        ari_none.append(an)
        ari_rand.append(ar)
        ng = len(clustering.groups)
        group_counts.append(ng)
        if ng == len(words):
            singleton_probes += 1
        if a1 > an + 1e-12:
            wins += 1
        elif a1 < an - 1e-12:
            losses += 1
        else:
            ties += 1

    m1 = _mean(ari_1c)
    mn = _mean(ari_none)
    mr = _mean(ari_rand)
    lift = m1 - mn
    p_sign = sign_test_two_sided(wins, losses)

    print("\n" + "-" * 72)
    print("RESULT — mean ARI across %d probes:" % len(probes))
    print("  ARI(1c)      mean=%.6f  median=%.6f  min=%.6f  max=%.6f"
          % (m1, _median(ari_1c), min(ari_1c), max(ari_1c)))
    print("  ARI(none)    mean=%.6f  median=%.6f  min=%.6f  max=%.6f"
          % (mn, _median(ari_none), min(ari_none), max(ari_none)))
    print("  ARI(random)  mean=%.6f  median=%.6f  min=%.6f  max=%.6f"
          % (mr, _median(ari_rand), min(ari_rand), max(ari_rand)))
    print("  LIFT (1c - none) = %.6f" % lift)
    print("  sign test 1c vs none:  wins=%d  losses=%d  ties=%d  p(two-sided)=%.6g"
          % (wins, losses, ties, p_sign))

    # distribution of how many groups 1c made (observability)
    print("  1c groups-per-probe: mean=%.3f  min=%d  max=%d  (all-singleton probes: %d/%d)"
          % (_mean([float(x) for x in group_counts]), min(group_counts), max(group_counts),
             singleton_probes, len(probes)))

    # ---- verdict (computed from data; thresholds frozen) ----
    pa = m1 >= ARI_ABS_THRESH
    pb = lift >= LIFT_THRESH
    pc = (p_sign < SIGN_P_THRESH) and (wins > losses)
    sanity = abs(mr) < 0.05  # random control near zero

    print("\n" + "=" * 72)
    print("VERDICT (thresholds frozen pre-run):")
    print("  P-a  mean ARI(1c) >= %.2f        : %s   (%.6f)"
          % (ARI_ABS_THRESH, "PASS" if pa else "FAIL", m1))
    print("  P-b  lift >= %.2f                 : %s   (%.6f)"
          % (LIFT_THRESH, "PASS" if pb else "FAIL", lift))
    print("  P-c  sign test p<%.2f & 1c>none   : %s   (p=%.6g, wins=%d losses=%d)"
          % (SIGN_P_THRESH, "PASS" if pc else "FAIL", p_sign, wins, losses))
    print("  sanity random ~0 (|mean|<0.05)   : %s   (%.6f)"
          % ("PASS" if sanity else "FAIL(VOID)", mr))
    earned = pa and pb and pc and sanity
    print("-" * 72)
    print("  OVERALL: %s" % ("CLAIM EARNED" if earned else "NOT YET"))
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
