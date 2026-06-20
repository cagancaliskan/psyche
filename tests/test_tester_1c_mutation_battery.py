"""
INDEPENDENT ADVERSARIAL TEST — randomized mutation battery for 1c integrity & purity.

Author: tester (independent adversary).

Protocol step 5 ("apply a long battery of randomized mutations, then assert every index is
mutually consistent") and step 4 ("snapshot stored state, perform reads, snapshot again —
assert nothing changed"), focused on the 1c clustering stage:

  - Build a pseudo-random graph (seeded by a FIXED int so the battery is reproducible, but
    the structure is not hand-chosen to be friendly: random contents, random edges with
    random repeat-counts, random charges, occasional closures, self-loops, duplicate
    contents, isolated nodes).
  - Interleave hundreds of randomized clustering calls (on random perceived-source subsets
    AND on perceive()-derived sources from random utterances) with full-graph integrity
    scans.
  - Assert the store is byte-identical (deep snapshot) before vs. after the whole battery
    AND that integrity holds at every checkpoint.

Determinism note: the randomness is for STRUCTURE GENERATION only (fixed seed via
random.Random(SEED)); clustering itself must be deterministic regardless. We additionally
re-run the battery in a fresh subprocess under a different PYTHONHASHSEED and require the
serialized clustering trace to match byte-for-byte — closing the loop on cross-process
determinism over a large, randomly-generated input rather than a hand-built one.

Run directly:
    PYTHONPATH=<repo>/src python3 tests/test_tester_1c_mutation_battery.py
"""

import os
import sys
import random
import subprocess
import textwrap

from nous_store import SubstrateStore, Clock, NodeType
from nous_perceive import perceive
from nous_source_clustering import cluster_sources

_passed = 0
_failed = 0
_fail_msgs = []


def check(cond, msg):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        _fail_msgs.append(msg)
        print(f"  FAIL: {msg}")


def section(name):
    print(f"\n{name}")


_WORDS = [
    "coffee", "kitchen", "morning", "warmth", "cozy", "work", "desk", "deadline",
    "code", "river", "stone", "ember", "willow", "harbor", "lantern", "thistle",
    "cobalt", "meadow", "cinder", "quartz", "velvet", "marrow", "tundra", "saffron",
]


def _deep_snapshot(s):
    roads = {}
    for rid in s.all_road_ids():
        r = s.get_road(rid, apply_decay=False)
        roads[rid] = (round(r.strength, 12), tuple(sorted(r.charges.items())),
                      r.closed, r.traversal_count, r.last_touched,
                      r.source_id, r.target_id)
    nodes = {}
    for nid in s.all_node_ids():
        nd = s.get_node(nid)
        nodes[nid] = (nd.content, nd.access_count, nd.last_accessed, nd.creation_seq)
    return roads, nodes


def _build_random_graph(seed):
    """A reproducibly-random, deliberately-hostile graph (NOT hand-tuned to be friendly)."""
    rng = random.Random(seed)
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    ids = []
    n_nodes = rng.randint(18, 30)
    for i in range(n_nodes):
        # duplicate contents are intentional: pick from a small vocab so collisions happen
        content = rng.choice(_WORDS)
        # occasionally append an index to vary, occasionally not (force duplicates)
        if rng.random() < 0.4:
            content = f"{content} {rng.randint(0, 3)}"
        ids.append(s.add_node(content, rng.choice(list(NodeType))))
    # random directed edges with random repeat counts; some self-loops; some closures
    n_edges = rng.randint(n_nodes, n_nodes * 3)
    for _ in range(n_edges):
        a = rng.choice(ids)
        b = rng.choice(ids)             # may equal a -> self-loop
        reps = rng.randint(1, 25)
        charge = None
        if rng.random() < 0.18:
            # sometimes a strongly-negative charge to trip closure
            charge = {"fear": -rng.uniform(0.8, 1.0)}
        for _ in range(reps):
            s.traverse(a, b, charge=charge)
    # leave some nodes isolated by construction (the later ids may have no edges) — fine
    return s, ids, rng


def _serialize_clustering(s, clustering):
    out = []
    for g in clustering.groups:
        # serialize each member as a (content, creation_seq) PAIR so the sort key is
        # type-homogeneous tuples of (str, int) — never a bare str adjacent to a bare int,
        # which would raise TypeError when groups of different sizes are compared.
        members = tuple(sorted((s.get_node(m).content, g._seq.get(m, -1))
                               for m in g.members))
        rep_seq = s.get_node(g.representative).creation_seq
        seed = round(clustering.group_seeds[g.representative], 9)
        out.append((members, rep_seq, seed))
    # sort the serialized groups by a stable key so we compare partitions, not build order
    return sorted(out)


def test_mutation_battery_integrity_and_purity():
    section("MUTATION BATTERY: random hostile graph; interleave 300 clustering calls with "
            "integrity scans; store must be byte-identical and integral throughout")
    s, ids, rng = _build_random_graph(seed=20260620)

    # integrity must hold on the freshly-built random graph
    ok = True
    try:
        s.check_integrity()
    except Exception as e:
        ok = False
        print("   pre-battery integrity error:", e)
    check(ok, "precondition: random graph is integral before the battery")

    before = _deep_snapshot(s)

    calls = 0
    integrity_failures = 0
    for step in range(300):
        # half the calls use a random subset of node ids as sources with random energies;
        # half use perceive() on a random utterance (loop-closed-ish source derivation)
        if step % 2 == 0:
            k = rng.randint(0, min(8, len(ids)))
            subset = rng.sample(ids, k)
            energies = {nid: rng.uniform(0.01, 5.0) for nid in subset}
            cluster_sources(s, energies)
        else:
            words = rng.sample(_WORDS, rng.randint(1, 5))
            p = perceive(s, " ".join(words))
            cluster_sources(s, p.sources)
        calls += 1
        # periodic full-graph integrity scan
        if step % 25 == 0:
            try:
                s.check_integrity()
            except Exception as e:
                integrity_failures += 1
                print(f"   integrity error at step {step}:", e)

    # final scan
    try:
        s.check_integrity()
    except Exception as e:
        integrity_failures += 1
        print("   post-battery integrity error:", e)

    after = _deep_snapshot(s)

    check(integrity_failures == 0,
          f"integrity held at every checkpoint across {calls} clustering calls "
          f"(failures={integrity_failures})")
    check(before == after,
          "the store is byte-identical (deep snapshot) before vs. after the whole battery "
          "(clustering is pure read)")


def test_mutation_battery_cross_process_determinism():
    section("MUTATION BATTERY cross-process: the full clustering trace over the random "
            "graph is byte-identical across 6 PYTHONHASHSEED values")
    # Re-run the SAME battery (same structure seed) under different hash seeds in fresh
    # interpreters; the serialized clustering trace must match byte-for-byte. This is the
    # strongest determinism check: a large, randomly-generated, adversarial input rather
    # than a hand-built one.
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(os.path.dirname(here), "src")
    # Inject WORDS via a repr-prepended assignment so the driver body contains NO percent
    # formatting at all (avoids any %-escaping fragility in the embedded source).
    driver = "WORDS = " + repr(_WORDS) + "\n" + textwrap.dedent('''
        import random
        from nous_store import SubstrateStore, Clock, NodeType
        from nous_perceive import perceive
        from nous_source_clustering import cluster_sources

        def build(seed):
            rng = random.Random(seed)
            s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
            ids = []
            n_nodes = rng.randint(18, 30)
            for i in range(n_nodes):
                content = rng.choice(WORDS)
                if rng.random() < 0.4:
                    content = content + " " + str(rng.randint(0, 3))
                ids.append(s.add_node(content, rng.choice(list(NodeType))))
            n_edges = rng.randint(n_nodes, n_nodes * 3)
            for _ in range(n_edges):
                a = rng.choice(ids); b = rng.choice(ids)
                reps = rng.randint(1, 25)
                charge = None
                if rng.random() < 0.18:
                    charge = {"fear": -rng.uniform(0.8, 1.0)}
                for _ in range(reps):
                    s.traverse(a, b, charge=charge)
            return s, ids, rng

        def serialize(s, clustering):
            out = []
            for g in clustering.groups:
                members = tuple(sorted((s.get_node(m).content, g._seq.get(m, -1))
                                       for m in g.members))
                rep_seq = s.get_node(g.representative).creation_seq
                seed = round(clustering.group_seeds[g.representative], 9)
                out.append((members, rep_seq, seed))
            return sorted(out)

        s, ids, rng = build(20260620)
        trace = []
        for step in range(120):
            if step % 2 == 0:
                k = rng.randint(0, min(8, len(ids)))
                subset = rng.sample(ids, k)
                energies = {nid: rng.uniform(0.01, 5.0) for nid in subset}
                cl = cluster_sources(s, energies)
            else:
                words = rng.sample(WORDS, rng.randint(1, 5))
                p = perceive(s, " ".join(words))
                cl = cluster_sources(s, p.sources)
            trace.append(serialize(s, cl))
        print(repr(trace))
    ''')

    outs = []
    errors = []
    for seed in ("0", "1", "5", "13", "257", "65521"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"]
                                   if env.get("PYTHONPATH") else "")
        rr = subprocess.run([sys.executable, "-c", driver],
                            cwd=here, capture_output=True, text=True, env=env)
        if rr.returncode != 0:
            print(f"  (subprocess error, seed={seed})\n", rr.stderr)
            errors.append((seed, rr.stderr.strip()[-300:]))
        outs.append(rr.stdout.strip())
    # A crashed probe must FAIL, not silently pass: identical crashes across seeds would
    # otherwise collapse to a single "output" and pass the equality check vacuously.
    check(not errors,
          f"all 6 determinism subprocesses exited 0 (errored seeds: {[e[0] for e in errors]})")
    check(len(set(outs)) == 1 and outs and outs[0] != "",
          f"random-graph clustering trace identical AND non-empty across 6 hash seeds "
          f"(distinct outputs: {len(set(outs))})")


def run_all():
    print("=" * 70)
    print("  TESTER — 1c RANDOMIZED MUTATION BATTERY (integrity / purity / determinism)")
    print("=" * 70)
    for t in [
        test_mutation_battery_integrity_and_purity,
        test_mutation_battery_cross_process_determinism,
    ]:
        t()
    print("\n" + "=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    if _fail_msgs:
        print("  FAILURES:")
        for m in _fail_msgs:
            print("   -", m)
    print("=" * 70)
    return _failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run_all() else 1)
