"""
Unit checks for the EXP-1c grader components (ARI + Louvain + probe machinery).

These guard the GRADER, not the method under test — so a positive or negative §6.2 verdict
rests on a metric and an external partitioner that are themselves checked. Tiny check() style
(NOT pytest), matching the project convention. No SWOW data needed for the pure-logic checks;
the Louvain check uses a small hand-built planted-partition graph (this is grader test data,
NOT the experiment's input — the experiment's labels come from the frozen SWOW partition).

Run:
    python3 experiments/test_exp1c.py
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import exp1c_recovery as R
import exp1c_build_partition as B

_passed = 0
_failed = 0


def check(cond, msg):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print("  FAIL: %s" % msg)


def section(name):
    print("\n=== %s ===" % name)


# ─────────────────────────────────────────────────────────────────────────────
# ARI correctness (Hubert & Arabie 1985), against known values.
# ─────────────────────────────────────────────────────────────────────────────

def test_ari():
    section("ARI (Hubert & Arabie 1985) known values")
    ari = R.adjusted_rand_index
    # identical partitions -> 1.0
    check(abs(ari([0, 0, 1, 1], [0, 0, 1, 1]) - 1.0) < 1e-12, "identical -> 1.0")
    # identical up to relabeling -> 1.0
    check(abs(ari([0, 0, 1, 1], [5, 5, 9, 9]) - 1.0) < 1e-12, "relabeled identical -> 1.0")
    # all-singletons vs blocked truth -> 0.0 (the no-clustering control case)
    check(abs(ari([0, 1, 2, 3], [0, 0, 1, 1]) - 0.0) < 1e-12, "singletons vs blocks -> 0.0")
    # everything-one-cluster vs blocked truth -> 0.0
    check(abs(ari([0, 0, 0, 0], [0, 0, 1, 1]) - 0.0) < 1e-12, "one-cluster vs blocks -> 0.0")
    # both all-singletons (degenerate 0/0) and equal -> 1.0
    check(abs(ari([0, 1, 2], [0, 1, 2]) - 1.0) < 1e-12, "both singletons equal -> 1.0")
    # both all-in-one and equal -> 1.0
    check(abs(ari([0, 0, 0], [7, 7, 7]) - 1.0) < 1e-12, "both one-cluster equal -> 1.0")
    # classic worked example (scikit-learn doc): ari([0,0,1,1],[0,0,1,2]) == 0.5714...
    val = ari([0, 0, 1, 1], [0, 0, 1, 2])
    check(abs(val - 0.5714285714285714) < 1e-9, "worked example ~0.5714 (got %.6f)" % val)
    # a partial-overlap symmetric case
    check(abs(ari([0, 0, 1, 1], [0, 1, 0, 1]) - (-0.5)) < 1e-9, "anti-correlated 2x2 -> -0.5")


# ─────────────────────────────────────────────────────────────────────────────
# Sign test (exact two-sided) sanity.
# ─────────────────────────────────────────────────────────────────────────────

def test_sign():
    section("exact two-sided sign test")
    st = R.sign_test_two_sided
    check(abs(st(0, 0) - 1.0) < 1e-12, "no trials -> p=1")
    check(abs(st(5, 5) - 1.0) < 1e-12, "5 vs 5 -> p=1")
    # 10 vs 0 -> 2 * (1/1024) = 0.001953125
    check(abs(st(10, 0) - 2.0 / 1024.0) < 1e-12, "10 vs 0 -> ~0.00195")
    # monotone: more lopsided -> smaller p
    check(st(9, 1) < st(7, 3), "more lopsided -> smaller p")
    # symmetry
    check(abs(st(8, 2) - st(2, 8)) < 1e-12, "sign test symmetric in wins/losses")


# ─────────────────────────────────────────────────────────────────────────────
# clustering_to_labels / random_partition_labels machinery.
# ─────────────────────────────────────────────────────────────────────────────

class _FakeGroup:
    def __init__(self, members):
        self.members = frozenset(members)


class _FakeClustering:
    def __init__(self, groups):
        self.groups = [_FakeGroup(g) for g in groups]


def test_label_mapping():
    section("clustering_to_labels + random_partition_labels")
    # words a,b in group0 ; c in group1 ; map ids = identity for the test
    words = ["a", "b", "c"]
    w2id = {"a": "a", "b": "b", "c": "c"}
    clus = _FakeClustering([{"a", "b"}, {"c"}])
    labs = R.clustering_to_labels(clus, w2id, words)
    check(labs[0] == labs[1] and labs[0] != labs[2], "a,b same group; c different")
    # a word missing from the clustering becomes a unique singleton
    clus2 = _FakeClustering([{"a"}])
    labs2 = R.clustering_to_labels(clus2, w2id, words)
    check(len(set(labs2)) == 3, "missing words -> unique singletons")
    # random_partition_labels uses exactly n_blocks blocks, deterministic given seed
    rp1 = R.random_partition_labels(9, 3, 123)
    rp2 = R.random_partition_labels(9, 3, 123)
    check(rp1 == rp2, "random partition deterministic given seed")
    check(len(set(rp1)) == 3, "random partition uses exactly n_blocks blocks")
    check(len(rp1) == 9, "random partition covers all items")


# ─────────────────────────────────────────────────────────────────────────────
# Louvain on a PLANTED partition: it should recover well-separated blocks.
# (Grader self-check: this is hand-built GRADER test data, not the experiment input.)
# ─────────────────────────────────────────────────────────────────────────────

def test_louvain_planted():
    section("Louvain recovers a planted 3-block partition (grader self-check)")
    # 3 dense blocks of 5 nodes, sparse bridges between blocks
    n = 15
    adj = [dict() for _ in range(n)]
    total = 0.0

    def add(a, b, w):
        nonlocal total
        if a == b:
            return
        adj[a][b] = adj[a].get(b, 0.0) + w
        adj[b][a] = adj[b].get(a, 0.0) + w
        total += w

    blocks = [range(0, 5), range(5, 10), range(10, 15)]
    for blk in blocks:
        bl = list(blk)
        for i in range(len(bl)):
            for j in range(i + 1, len(bl)):
                add(bl[i], bl[j], 10.0)   # strong within-block
    # weak bridges
    add(0, 5, 1.0)
    add(5, 10, 1.0)
    add(10, 0, 1.0)

    members = set(range(n))
    labels = B.louvain(adj, total, members, gamma=1.0)
    # group nodes by label
    from collections import defaultdict
    groups = defaultdict(list)
    for node, c in labels.items():
        groups[c].append(node)
    # should be exactly 3 communities, each one planted block
    got_blocks = sorted(sorted(v) for v in groups.values())
    expected = [list(range(0, 5)), list(range(5, 10)), list(range(10, 15))]
    check(got_blocks == expected, "Louvain recovers the 3 planted blocks (got %s)" % got_blocks)

    # determinism: same input -> same labels
    labels2 = B.louvain(adj, total, members, gamma=1.0)
    check(labels == labels2, "Louvain deterministic on identical input")


def test_louvain_singletons_when_no_edges():
    section("Louvain on an edgeless member set -> singletons (no crash)")
    n = 4
    adj = [dict() for _ in range(n)]
    labels = B.louvain(adj, 0.0, set(range(n)), gamma=1.0)
    check(len(set(labels.values())) == n, "edgeless -> all singletons")


def main() -> int:
    test_ari()
    test_sign()
    test_label_mapping()
    test_louvain_planted()
    test_louvain_singletons_when_no_edges()
    print()
    print("RESULT: %d passed, %d failed" % (_passed, _failed))
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
