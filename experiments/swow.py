"""
Phase 2B — Small World of Words (SWOW-EN) loader + BLIND pair selection.

This module turns the raw SWOW association norms into (a) a declarative spec the FROZEN
library builds into a SubstrateStore, and (b) priming pairs chosen from TOPOLOGY/STRENGTH
ONLY — never from any activation result. Keeping selection here, upstream of and ignorant
of `spread_activation`, is the anti-circularity core of the study: the conditions are fixed
before the engine is ever run.

It imports nothing from the engine. It reads the data file by an EXPLICIT path and fails
with a clear message if the file is absent (no filename guessing).

DATA SCHEMA (verified):
  Tab-separated (despite the .csv name). Header: cue \t response \t R123 \t N \t R123.Strength
  `cue` -> `response` is a directed association; `R123.Strength` in [0,1] is its strength.
  NOTE: the file contains a couple of rows with a stray double-quote character, which makes
  Python's csv module raise "field larger than field limit". We therefore parse as PLAIN
  TSV (split on tab), which is correct for this file (every data row has exactly 5 fields).

EDGE MAPPING (pre-registered; identical for every edge, no per-pair tuning):
  traverse_count = min(STRENGTH_CAP, 1 + floor(R123.Strength * STRENGTH_SCALE))
  with STRENGTH_SCALE = 100, STRENGTH_CAP = 10 — a single monotonic map from association
  strength to how many times the edge is traversed (and thus, via the store's strengthen
  dynamics, to edge strength). Rows with strength <= 0 are dropped; self-loops are dropped.

GRAPH = FULL graph (all words that appear as cue or response). The cue-core induced subgraph
was rejected because it is too dense to host a topological UNRELATED condition (measured:
98% of nodes reachable within 3 hops). See EXPERIMENT_NOTES.md.
"""

from __future__ import annotations

import os
from typing import Dict, List, Tuple, Optional

# ── pre-registered constants (locked before the main run) ────────────────────────────
STRENGTH_SCALE = 100
STRENGTH_CAP = 10
DEFAULT_DATA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "strength.SWOW-EN.R123.20180827.csv"
)


def traverse_count_for_strength(strength: float) -> int:
    """The single fixed monotonic mapping from SWOW association strength to traverse count."""
    return min(STRENGTH_CAP, 1 + int(strength * STRENGTH_SCALE))


class SwowMissing(FileNotFoundError):
    """Raised when the SWOW data file is not present at the expected path."""


# ─────────────────────────────────────────────────────────────────────────────
# Load: raw TSV -> deduped directed edges with strength
# ─────────────────────────────────────────────────────────────────────────────

def load_edges(path: str = DEFAULT_DATA_PATH) -> List[Tuple[str, str, float]]:
    """Read the SWOW TSV and return a list of (cue, response, strength) with strength>0 and
    no self-loops. Deterministic order: as encountered in the file (the file is itself a
    fixed artifact). Fails clearly if the file is missing.

    Plain-TSV parse (NOT csv module) — see module docstring for why.
    """
    if not os.path.exists(path):
        raise SwowMissing(
            "SWOW data file not found at:\n  %s\n\n"
            "Phase 2B needs the Small World of Words English strength file\n"
            "  strength.SWOW-EN.R123.20180827.csv\n"
            "Obtain it from https://smallworldofwords.org/ (Research > Data) and place it at\n"
            "the path above (see experiments/data/README.md). It is intentionally NOT committed\n"
            "(size + license)." % path
        )
    edges: List[Tuple[str, str, float]] = []
    with open(path, encoding="utf-8", newline="") as fh:
        header = next(fh).rstrip("\n").split("\t")
        try:
            i_cue = header.index("cue")
            i_resp = header.index("response")
            i_str = header.index("R123.Strength")
        except ValueError as e:
            raise ValueError(
                "Unexpected SWOW header %r; expected columns cue/response/R123.Strength" % header
            ) from e
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) <= i_str:
                continue  # malformed; skip (none expected in this file)
            cue = parts[i_cue]
            resp = parts[i_resp]
            try:
                strength = float(parts[i_str])
            except ValueError:
                continue
            if strength <= 0.0 or cue == resp:
                continue
            edges.append((cue, resp, strength))
    return edges


# ─────────────────────────────────────────────────────────────────────────────
# Spec for the frozen library's build_graph_from_spec
# ─────────────────────────────────────────────────────────────────────────────

def build_spec(edges: List[Tuple[str, str, float]]) -> Dict[str, object]:
    """Turn loaded edges into the declarative spec consumed by harness.build_graph_from_spec.

    Nodes are the sorted union of all words (sorted so node creation order is fixed and
    independent of dict/hash ordering — a determinism guard). Each edge becomes
    (cue, response, traverse_count) under the fixed mapping. One spec, built once.
    """
    words = set()
    for c, r, _ in edges:
        words.add(c)
        words.add(r)
    nodes = sorted(words)
    spec_edges = [(c, r, traverse_count_for_strength(s)) for (c, r, s) in edges]
    return {"nodes": nodes, "edges": spec_edges}


# ─────────────────────────────────────────────────────────────────────────────
# A lightweight integer adjacency (for fast, BLIND topological selection only).
# This is NOT the substrate the engine runs on — it is a read-only index over the SAME
# edges, used to choose pairs by graph structure before any spread. Building it from the
# same `edges` guarantees selection sees exactly the substrate's topology.
# ─────────────────────────────────────────────────────────────────────────────

class Topology:
    """Directed adjacency over word indices, with sorted neighbor lists (determinism).
    Strength of each direct edge retained for the P1 graded-direct test."""

    def __init__(self, edges: List[Tuple[str, str, float]]):
        words = sorted({w for c, r, _ in edges for w in (c, r)})
        self.words = words
        self.index = {w: i for i, w in enumerate(words)}
        self.n = len(words)
        out: List[set] = [set() for _ in range(self.n)]
        indeg = [0] * self.n
        strength: Dict[Tuple[int, int], float] = {}
        for c, r, s in edges:
            ci = self.index[c]
            ri = self.index[r]
            if ri not in out[ci]:
                out[ci].add(ri)
                indeg[ri] += 1
            # keep the max strength if duplicated (deduped data has none, but be safe)
            key = (ci, ri)
            if s > strength.get(key, -1.0):
                strength[key] = s
        # frozen sorted adjacency for deterministic iteration
        self.out: List[Tuple[int, ...]] = [tuple(sorted(o)) for o in out]
        self.out_set: List[frozenset] = [frozenset(o) for o in out]
        self.indeg = indeg
        self.strength = strength

    def reachable_within(self, src: int, k: int) -> set:
        """Set of node indices reachable from `src` within `k` hops (BFS). Includes src."""
        seen = {src}
        frontier = {src}
        for _ in range(k):
            nxt = set()
            for u in frontier:
                for v in self.out[u]:
                    if v not in seen:
                        seen.add(v)
                        nxt.add(v)
            frontier = nxt
            if not frontier:
                break
        return seen


# ─────────────────────────────────────────────────────────────────────────────
# BLIND pair selection
# ─────────────────────────────────────────────────────────────────────────────

PRIMING_K_UNRELATED = 4  # pre-registered: UNRELATED = no path within this many hops


def select_pairs(
    topo: Topology,
    n_primes: int,
    *,
    seed: int,
    k_unrelated: int = PRIMING_K_UNRELATED,
    min_outdeg: int = 2,
):
    """Choose, for each of `n_primes` primes, ONE target in each condition — using ONLY
    topology and SWOW strength. Returns a list of dicts (word-space), and is fully
    deterministic given `seed` (a fixed RNG, sorted candidate lists).

    Per prime P (P must have out-degree >= min_outdeg and at least one 2-hop target):
      DIRECT   : a direct response of P (recorded with its SWOW strength).
      MEDIATED : a node at exactly 2 hops (P->M->T) that is NOT a direct response of P.
      UNRELATED: a node with in-degree>0 that is NOT reachable from P within k_unrelated hops.

    The DIRECT target is chosen to span strength (we pick a random direct edge; the P1 test
    uses the recorded strength, so range matters more than which one). MEDIATED and UNRELATED
    are uniform random from their (sorted) candidate pools. Nothing here calls the engine.
    """
    import random
    rng = random.Random(seed)

    # candidate primes: out-degree >= min_outdeg, sorted for determinism
    primes = [i for i in range(topo.n) if len(topo.out[i]) >= min_outdeg]
    primes.sort()
    rng.shuffle(primes)  # deterministic shuffle (seeded)

    indeg_pos = [i for i in range(topo.n) if topo.indeg[i] > 0]
    indeg_pos_set = frozenset(indeg_pos)

    pairs = []
    for p in primes:
        if len(pairs) >= n_primes:
            break
        direct_set = topo.out_set[p]
        if not direct_set:
            continue

        # MEDIATED candidates: 2-hop minus direct minus {p}
        two_hop = set()
        for m in topo.out[p]:
            for t in topo.out[m]:
                two_hop.add(t)
        mediated_cands = sorted(two_hop - direct_set - {p})
        if not mediated_cands:
            continue

        # UNRELATED candidates: in-deg>0, not reachable within k, not p
        reach = topo.reachable_within(p, k_unrelated)
        # iterate the (sorted) in-degree-positive list for determinism
        unrelated_cands = [t for t in indeg_pos if t not in reach and t != p]
        if not unrelated_cands:
            continue

        direct = rng.choice(sorted(direct_set))
        mediated = rng.choice(mediated_cands)
        unrelated = rng.choice(unrelated_cands)

        pairs.append({
            "prime": topo.words[p],
            "prime_idx": p,
            "direct": topo.words[direct],
            "direct_strength": topo.strength[(p, direct)],
            "mediated": topo.words[mediated],
            "unrelated": topo.words[unrelated],
        })

    return pairs
