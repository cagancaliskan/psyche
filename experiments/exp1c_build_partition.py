"""
EXP-1c — FROZEN EXTERNAL PARTITION GENERATOR  (§6.2 grader, fallback path).

Produces the EXTERNAL community partition the 1c source-clustering is graded against, by a
DIFFERENT algorithm family from the method under test:

  - Method under test (1c, src/nous_source_clustering.py): single-link agglomerative =
    connected-components of a thinned proximity graph (transitive closure).
  - This grader: LOUVAIN modularity optimization (Blondel, Guillaume, Lambiotte & Lefebvre,
    2008, J. Stat. Mech. P10008). A modularity-objective method — a genuinely different
    principle from single-link, which is the independence the anti-circularity argument needs.

ANTI-CIRCULARITY (load-bearing):
  - This script imports NOTHING from ../src. It never calls cluster_sources. It is run ONCE to
    freeze the external labels BEFORE the method under test is ever scored.
  - It reads the SAME external SWOW data via the existing experiments/swow.py loader and the
    SAME fixed edge-weight map used everywhere in this repo. It authors no edges and no labels.
  - Output is written to experiments/results/exp1c_external_partition.tsv and its SHA-256 is
    printed; that hash is pasted into docs/experiments/EXP-1c-swow-recovery.md §3.1 and frozen.

DEPENDENCY POSTURE (CLAUDE.md rule 8, SPEC-1c "Dependency posture"):
  - Pure Python standard library. Lives under experiments/, never enters the core import graph.

DETERMINISM:
  - Undirected weighted graph: w(a,b) = traverse_count(a->b) + traverse_count(b->a) over the
    SWOW directed edges (symmetrized FOR THE GRADER ONLY; the store the method reads is
    untouched and directed).
  - Resolution gamma = 1.0 (standard; the value published SWOW Louvain work uses).
  - All node/neighbor iteration in a fixed sorted order; modularity-gain ties broken toward the
    lowest community id. RNG seed 20250620 (fixed) — but with sorted visit order no randomness
    affects the result; the seed is recorded for completeness.
  - Partition computed on the LARGEST weakly-connected component; nodes outside it -> label -1.

USAGE:
    python3 experiments/exp1c_build_partition.py
  (optional, for a fast smoke test only — NOT the frozen artifact:
    NOUS_EXP1C_MAXROWS=200000 python3 experiments/exp1c_build_partition.py
   the frozen run uses the FULL file; if MAXROWS is set the script refuses to overwrite the
   canonical output path and writes a *_SMOKE.tsv instead.)
"""

from __future__ import annotations

import hashlib
import os
import sys
from typing import Dict, List, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# external SWOW loader (the project's existing, blind, anti-circular loader)
import swow  # noqa: E402

# ── pre-registered constants (frozen; see docs/experiments/EXP-1c-swow-recovery.md) ──────
GAMMA = 1.0
SEED = 20250620
RESULTS_DIR = os.path.join(_HERE, "results")
OUT_PATH = os.path.join(RESULTS_DIR, "exp1c_external_partition.tsv")
SMOKE_PATH = os.path.join(RESULTS_DIR, "exp1c_external_partition_SMOKE.tsv")


# ─────────────────────────────────────────────────────────────────────────────
# Build an undirected weighted graph (integer-indexed) from SWOW edges.
# ─────────────────────────────────────────────────────────────────────────────

def build_undirected(edges: List[Tuple[str, str, float]]):
    """Return (words, adj, total_w) where words is the sorted word list, adj[i] is a dict
    {j: weight} (undirected, j != i; self-loops dropped), total_w = sum of all undirected
    edge weights (each unordered pair counted once). Weight uses the repo's fixed map and
    symmetrizes directed traverse-counts by summation."""
    # collect undirected weight per unordered index pair
    words = sorted({w for c, r, _ in edges for w in (c, r)})
    index = {w: i for i, w in enumerate(words)}
    n = len(words)
    pair_w: Dict[Tuple[int, int], float] = {}
    for c, r, s in edges:
        ci, ri = index[c], index[r]
        if ci == ri:
            continue
        a, b = (ci, ri) if ci < ri else (ri, ci)
        tc = float(swow.traverse_count_for_strength(s))
        pair_w[(a, b)] = pair_w.get((a, b), 0.0) + tc
    adj: List[Dict[int, float]] = [dict() for _ in range(n)]
    total_w = 0.0
    for (a, b), w in pair_w.items():
        adj[a][b] = w
        adj[b][a] = w
        total_w += w
    return words, adj, total_w


# ─────────────────────────────────────────────────────────────────────────────
# Largest weakly-connected component (undirected components here).
# ─────────────────────────────────────────────────────────────────────────────

def giant_component(adj: List[Dict[int, float]]) -> set:
    n = len(adj)
    seen = [False] * n
    best: List[int] = []
    for start in range(n):              # sorted order (index == sorted word)
        if seen[start]:
            continue
        comp: List[int] = []
        stack = [start]
        seen[start] = True
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in sorted(adj[u]):    # sorted neighbor iteration
                if not seen[v]:
                    seen[v] = True
                    stack.append(v)
        if len(comp) > len(best):
            best = comp
    return set(best)


# ─────────────────────────────────────────────────────────────────────────────
# Louvain (Blondel et al. 2008), deterministic, weighted, undirected.
# ─────────────────────────────────────────────────────────────────────────────

def louvain(adj: List[Dict[int, float]], total_w: float, members: set,
            gamma: float = GAMMA) -> Dict[int, int]:
    """Full Louvain over the subgraph induced by `members`. Returns original-node -> community
    label (an int). Deterministic given sorted iteration."""
    if total_w <= 0.0:
        return {u: u for u in sorted(members)}
    two_m = 2.0 * total_w

    # current graph state: node list, adjacency, degree (incident weight)
    cur_nodes = sorted(members)
    # degree restricted to members
    k = [0.0] * len(adj)
    # restricted adjacency (only edges within members) so community math is correct
    radj: Dict[int, Dict[int, float]] = {}
    for u in cur_nodes:
        d = {}
        s = 0.0
        for v, w in adj[u].items():
            if v in members:
                d[v] = w
                s += w
        radj[u] = d
        k[u] = s

    # map original node -> its label, refined across levels
    # level 0 works on original nodes
    # represent the working graph as integer "super-nodes"
    # super_of[orig] = current super-node id
    super_of = {u: u for u in cur_nodes}
    work_nodes = list(cur_nodes)
    work_adj = {u: dict(radj[u]) for u in cur_nodes}
    work_k = {u: k[u] for u in cur_nodes}

    while True:
        # build dense-ish structures for _one_level over work graph
        nodes_sorted = sorted(work_nodes)
        # adapt _one_level to dict-based adjacency
        comm = _one_level_dict(nodes_sorted, work_adj, work_k, two_m, gamma)
        # did anything merge? count distinct communities
        distinct = set(comm.values())
        if len(distinct) == len(nodes_sorted):
            # no merges this level -> done; fold labels back to original nodes
            break
        # fold super_of: every original node currently mapped to `node` now maps to comm
        node_to_comm = {node: comm[node] for node in nodes_sorted}
        for orig in super_of:
            super_of[orig] = node_to_comm[super_of[orig]]
        # aggregate graph: super-nodes = communities
        new_nodes = sorted(set(node_to_comm.values()))
        new_adj: Dict[int, Dict[int, float]] = {c: {} for c in new_nodes}
        new_k: Dict[int, float] = {c: 0.0 for c in new_nodes}
        for u in nodes_sorted:
            cu = node_to_comm[u]
            for v, w in work_adj[u].items():
                cv = node_to_comm[v]
                new_adj[cu][cv] = new_adj[cu].get(cv, 0.0) + w
                new_k[cu] += w
        work_nodes = new_nodes
        work_adj = new_adj
        work_k = new_k

    # final labels: original node -> super community id
    return {orig: super_of[orig] for orig in cur_nodes}


def _one_level_dict(nodes: List[int], adj: Dict[int, Dict[int, float]],
                    k: Dict[int, float], two_m: float, gamma: float) -> Dict[int, int]:
    """Dict-based variant of one Louvain level (handles aggregated super-graphs whose node ids
    are sparse). Deterministic; sorted visiting; ties -> lowest community id. Self-loops on a
    super-node contribute to its internal weight and are kept in degree."""
    comm = {u: u for u in nodes}
    sigma_tot: Dict[int, float] = {u: k[u] for u in nodes}
    improved = True
    while improved:
        improved = False
        for u in nodes:
            cu = comm[u]
            ku = k[u]
            sigma_tot[cu] -= ku
            w_to: Dict[int, float] = {}
            for v, w in adj[u].items():
                if v == u:
                    continue
                cv = comm[v]
                w_to[cv] = w_to.get(cv, 0.0) + w
            best_comm = cu
            best_gain = w_to.get(cu, 0.0) - gamma * sigma_tot.get(cu, 0.0) * ku / two_m
            for c in sorted(w_to.keys()):
                if c == cu:
                    continue
                gain = w_to[c] - gamma * sigma_tot.get(c, 0.0) * ku / two_m
                if gain > best_gain + 1e-12:
                    best_gain = gain
                    best_comm = c
            sigma_tot[best_comm] = sigma_tot.get(best_comm, 0.0) + ku
            comm[u] = best_comm
            if best_comm != cu:
                improved = True
    return comm


# ─────────────────────────────────────────────────────────────────────────────
# Main: build, partition, freeze, hash.
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    import random
    random.Random(SEED)  # recorded for completeness; sorted order makes output seed-free

    maxrows_env = os.environ.get("NOUS_EXP1C_MAXROWS")
    smoke = maxrows_env is not None

    print("=" * 70)
    print("EXP-1c — FROZEN EXTERNAL PARTITION (Louvain, gamma=%.3f, seed=%d)" % (GAMMA, SEED))
    print("Algorithm family: modularity optimization (DIFFERENT from 1c single-link).")
    print("Imports from ../src: NONE. Calls cluster_sources: NEVER.")
    print("=" * 70)

    edges = swow.load_edges()
    if smoke:
        n = int(maxrows_env)
        edges = edges[:n]
        print("SMOKE MODE: using first %d edges (NOT the frozen artifact)." % n)
    print("edges loaded: %d" % len(edges))

    words, adj, total_w = build_undirected(edges)
    print("undirected graph: %d nodes, total undirected weight %.1f" % (len(words), total_w))

    members = giant_component(adj)
    # total weight within the giant component
    gw = 0.0
    for u in members:
        for v, w in adj[u].items():
            if v in members and u < v:
                gw += w
    print("giant component: %d nodes, internal weight %.1f" % (len(members), gw))

    labels_idx = louvain(adj, gw, members, gamma=GAMMA)

    # canonicalize community ids to small contiguous ints in a deterministic way:
    # order communities by (size desc, min-member-index asc) and renumber 0..K-1
    from collections import defaultdict
    comm_members = defaultdict(list)
    for node, c in labels_idx.items():
        comm_members[c].append(node)
    order = sorted(comm_members.keys(),
                   key=lambda c: (-len(comm_members[c]), min(comm_members[c])))
    remap = {c: i for i, c in enumerate(order)}

    # write word -> community_id; nodes outside the giant component get -1
    out_path = SMOKE_PATH if smoke else OUT_PATH
    os.makedirs(RESULTS_DIR, exist_ok=True)
    lines = []
    member_set = members
    for i, w in enumerate(words):           # i == sorted index
        if i in member_set:
            cid = remap[labels_idx[i]]
        else:
            cid = -1
        lines.append("%s\t%d" % (w, cid))
    body = "\n".join(lines) + "\n"
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(body)

    n_comm = len(order)
    sizes = sorted((len(v) for v in comm_members.values()), reverse=True)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()

    print("-" * 70)
    print("WROTE: %s" % out_path)
    print("nodes total: %d   in-giant (labelled): %d   communities: %d"
          % (len(words), len(member_set), n_comm))
    print("top-10 community sizes: %s" % sizes[:10])
    print("SHA-256 (content): %s" % digest)
    print("-" * 70)
    if smoke:
        print("SMOKE run — do NOT paste this hash into the pre-registration.")
    else:
        print("PASTE this SHA-256 and counts into docs/experiments/EXP-1c-swow-recovery.md §3.1,")
        print("then (and only then) run experiments/exp1c_recovery.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
