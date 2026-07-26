"""
INDEPENDENT ADVERSARIAL TEST SUITE for step 1d-i (nous_workspace.select_winner).

Author: tester (independent adversary). These tests are written FROM SCRATCH against
the spec's acceptance PROPERTIES (SPEC-1d §3.1 A2 competition, §3.2 + Decision C1
pruning, §5 substrate bar, §6.1/§6.2/§6.4 acceptance). They are NOT adapted from the
builder's suite. The goal is to break the mechanism, expose happy-path bias, and to
ADJUDICATE the C1 perceived-source watershed objectively (threshold-free? generalizes?
circular?).

Scope (mechanism only — never meaning): the winner is a SELECTED INFORMATION STRUCTURE.
We verify it is selected correctly, deterministically, purely, integrity-preserving, and
scale-invariant; and that pruning is the unperceived-domain watershed C1 claims to be.
We make NO cognitive claim.

Properties:
  T1  §6.1 over-swallow flip LOOP-CLOSED through the real think() (system-generated
      coalitions). work/code/desk/deadline genuinely pruned from the winner.
  T1b The over-swallow is REAL pre-prune: the raw winner DOES contain the work domain,
      so pruning is doing the work (the flip is not vacuous because work was never there).
  T2  Anti-overcorrection: a PERCEIVED domain is NEVER pruned — including hostile cases
      built to TRY to make the watershed over-prune a legitimately-perceived member
      (loosely-attached perceived node; perceived node bridged to a denser unperceived
      region).
  T3  C1 generalization on NEW, structurally-different graphs (NOT isomorphic relabels):
      different domain sizes, multiple bridges, asymmetric cohesion, >=3 domains with
      mixed perceived/unperceived — WITHOUT per-graph tuning.
  T4  C1 boundary probes: does it mis-prune a weakly-cohesive unperceived region, or
      fail-to-prune when the bridge is unusually strong? (the decisive C1-vs-C2 test).
  T5  Threshold-free audit: no calibrated constant in the pruning path; pruning result is
      invariant to the only constant in the module (DEFAULT_MIN_SIZE_GUARD belongs to
      competition, not pruning).
  T6  Cross-process determinism (winner + pruned + ranked order) across ALL 6 hash seeds
      in fresh interpreters — our OWN probe, ties everywhere.
  T7  Purity: deep snapshot byte-identical before/after select_winner AND
      think(broadcast=False), with ties + adversarial graph. ZERO mutation.
  T8  Integrity: randomized mutation battery, check_integrity() clean throughout, store
      byte-identical across interleaved selection calls.
  T9  Hostile topologies for the COMPETITION: empty, singleton, duplicate edges, cycles,
      self-loops, high-degree fans, multiple competing basins, ties in density/size/seq.
  T10 Scale-invariance of BOTH criteria (competition ratio + pruning road-strength).
  T11 P9 re-derivation (re-owned in our voice): independent proof the residual is gone.

Run via run_tests.py (added to its SUITES). For a direct run:
    PYTHONPATH=<repo>/src python3 tests/test_tester_1d_i_adversarial.py
"""

import os
import sys
import subprocess
import textwrap
import inspect

from nous_store import SubstrateStore, Clock, NodeType
from nous_perceive import perceive, think
from nous_field import build_activation_field
from nous_coalitions import form_coalitions_from_field, Coalition
from nous_source_clustering import cluster_sources
from nous_workspace import (
    select_winner, rank_coalitions, WorkspaceResult,
    _density_score, _perceived_domain_members, _strongest_road_strength,
    _internal_road_ids,
    DEFAULT_MIN_SIZE_GUARD,
)

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


def _worn(s, a, b, n=30):
    for _ in range(n):
        s.traverse(a, b)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures — rebuilt independently (NOT imported from the builder's suite)
# ─────────────────────────────────────────────────────────────────────────────

def _small_mind():
    """Independently rebuilt _small_mind: two loose domains, strong n=8 coffee->work
    bridge. Identical topology to the acceptance fixture so 1d-i is exercised on the exact
    graph the over-swallow bug surfaced on (loop-closed)."""
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    coffee = s.add_node("coffee", NodeType.ENTITY)
    warmth = s.add_node("warmth", NodeType.SENSATION)
    morning = s.add_node("morning routine", NodeType.CONCEPT)
    cozy = s.add_node("cozy feeling", NodeType.CONCEPT)
    kitchen = s.add_node("kitchen", NodeType.ENTITY)
    work = s.add_node("work", NodeType.CONCEPT)
    desk = s.add_node("desk", NodeType.ENTITY)
    deadline = s.add_node("deadline pressure", NodeType.CONCEPT)
    code = s.add_node("writing code", NodeType.CONCEPT)
    _worn(s, coffee, warmth); _worn(s, coffee, morning); _worn(s, morning, cozy)
    _worn(s, coffee, kitchen); _worn(s, kitchen, morning)
    _worn(s, work, desk); _worn(s, work, deadline); _worn(s, work, code); _worn(s, desk, code)
    _worn(s, coffee, work, n=8)
    return s, dict(coffee=coffee, warmth=warmth, morning=morning, cozy=cozy,
                   kitchen=kitchen, work=work, desk=desk, deadline=deadline, code=code)


def _deep_snapshot(s):
    """Deep snapshot of ALL stored state a pure read must leave untouched: per-road
    strength/charges/closed/traversal_count/last_touched (canonical, decay-free) and
    per-node access_count/last_accessed. Used to prove ZERO mutation."""
    roads = {}
    for rid in s.all_road_ids():
        r = s.get_road(rid, apply_decay=False)
        roads[rid] = (round(r.strength, 12), tuple(sorted(r.charges.items())),
                      r.closed, r.traversal_count, r.last_touched)
    nodes = {}
    for nid in s.all_node_ids():
        nd = s.get_node(nid)
        nodes[nid] = (nd.access_count, nd.last_accessed)
    return roads, nodes


def _contents(s, ids):
    return sorted(s.get_node(m).content for m in ids)


# ─────────────────────────────────────────────────────────────────────────────
# T1 — over-swallow flip LOOP-CLOSED (system-generated coalitions)
# ─────────────────────────────────────────────────────────────────────────────

def test_T1_over_swallow_flips_loop_closed():
    section("T1 §6.1 LOOP-CLOSED: the winner excludes the bridged, unperceived work/code "
            "domain (coalitions system-generated through think())")
    s, n = _small_mind()
    r = think(s, "coffee in the kitchen this morning")
    check(r.workspace is not None and r.thought is not None,
          "think() produced a workspace result and a winner")
    winner = set(r.thought.members)
    # the ENTIRE unperceived work domain is gone
    for name in ("work", "code", "desk", "deadline"):
        check(n[name] not in winner,
              f"the unperceived work-domain node {name!r} is excluded from the winner")
    check({n["work"], n["code"], n["desk"], n["deadline"]} <= set(r.workspace.pruned_members),
          "the whole unperceived work domain is recorded in pruned_members")
    # the perceived warm domain survives
    check({n["coffee"], n["kitchen"], n["morning"]} <= winner,
          "the perceived warm domain is preserved in the winner")


def test_T1b_over_swallow_is_real_preprune_not_vacuous():
    section("T1b the over-swallow is REAL: the RAW winner (pre-prune) actually CONTAINS "
            "the work domain — so the flip is pruning's doing, not 'work was never there'")
    s, n = _small_mind()
    r = think(s, "coffee in the kitchen this morning")
    # the field must REACH work/code (the bridge is strong); precondition the bug exists
    reached = set(r.field_.total.keys())
    check(n["work"] in reached and n["code"] in reached,
          "precondition: the single-source spread REACHES work/code over the n=8 bridge")
    raw = set(r.workspace.raw_winner.members) if r.workspace.raw_winner else set()
    check(n["work"] in raw and n["code"] in raw,
          "the RAW top coalition over-swallows work/code (the over-swallow is genuinely "
          "present before pruning; the flip is not vacuous)")


# ─────────────────────────────────────────────────────────────────────────────
# T2 — anti-overcorrection: a PERCEIVED domain is NEVER pruned (hostile attempts)
# ─────────────────────────────────────────────────────────────────────────────

def test_T2_anti_overcorrection_perceived_domain_survives_loop_closed():
    section("T2 anti-overcorrection (loop-closed): naming the work domain keeps "
            "work/desk and their basin (a perceived domain is never pruned)")
    s, n = _small_mind()
    r = think(s, "work at the desk")
    perceived = set(r.perception.sources)
    check({n["work"], n["desk"]} <= perceived, "precondition: perception named work + desk")
    winner = set(r.thought.members) if r.thought else set()
    check(n["work"] in winner and n["desk"] in winner,
          "perceived work/desk survive (never pruned)")
    check(n["work"] not in r.workspace.pruned_members and
          n["desk"] not in r.workspace.pruned_members,
          "no perceived member is in pruned_members")


def test_T2b_loosely_attached_perceived_node_survives():
    section("T2b HOSTILE anti-overcorrection: a loosely-attached PERCEIVED node (weak "
            "n=3 link to its domain) is NOT pruned, because it is a perceived seed itself")
    # Build a domain with a dense core (n=30) and a perceived node attached only weakly
    # (n=3). If the watershed pruned by attachment-strength it would drop the weak node;
    # but the node is a perceived SEED, so it must survive unconditionally.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    core1 = s.add_node("alpha", NodeType.CONCEPT)
    core2 = s.add_node("beta", NodeType.CONCEPT)
    core3 = s.add_node("gamma", NodeType.CONCEPT)
    weak = s.add_node("delta", NodeType.CONCEPT)   # perceived, but only weakly attached
    _worn(s, core1, core2, n=30); _worn(s, core2, core3, n=30); _worn(s, core3, core1, n=30)
    _worn(s, core1, weak, n=3)                      # WEAK link
    # name all four: alpha beta gamma delta
    r = think(s, "alpha beta gamma delta")
    perceived = set(r.perception.sources)
    check({core1, core2, core3, weak} <= perceived, "precondition: all four perceived")
    winner = set(r.thought.members) if r.thought else set()
    check(weak in winner,
          "the loosely-attached PERCEIVED node survives (perceived seeds are never pruned)")
    check(weak not in r.workspace.pruned_members,
          "the weakly-attached perceived node is not in pruned_members")


def test_T2c_perceived_node_bridged_to_denser_unperceived_region_survives():
    section("T2c HOSTILE anti-overcorrection: a perceived node bridged into a DENSER "
            "unperceived region keeps its perceived label (its own seed status wins)")
    # A perceived node 'hinge' sits between a small perceived domain and a big dense
    # unperceived domain. The watershed must NOT strip 'hinge' (it is a seed); the big
    # unperceived domain should still be pruned, but the perceived hinge must remain.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    # small perceived domain: ping - pong
    ping = s.add_node("ping", NodeType.CONCEPT)
    pong = s.add_node("pong", NodeType.CONCEPT)
    _worn(s, ping, pong, n=30)
    # hinge perceived, attached to perceived ping (n=30) and bridged to a dense unnamed
    # region (n=8 bridge)
    hinge = s.add_node("hinge", NodeType.CONCEPT)
    _worn(s, ping, hinge, n=30)
    # dense unperceived region: rho sigma tau (triangle n=30), bridged from hinge
    rho = s.add_node("rho", NodeType.CONCEPT)
    sigma = s.add_node("sigma", NodeType.CONCEPT)
    tau = s.add_node("tau", NodeType.CONCEPT)
    _worn(s, rho, sigma, n=30); _worn(s, sigma, tau, n=30); _worn(s, tau, rho, n=30)
    _worn(s, hinge, rho, n=8)
    r = think(s, "ping pong hinge")   # names ping/pong/hinge only
    perceived = set(r.perception.sources)
    check({ping, pong, hinge} <= perceived, "precondition: ping/pong/hinge perceived")
    winner = set(r.thought.members) if r.thought else set()
    check(hinge in winner, "the perceived hinge survives even though it bridges a denser "
                           "unperceived region")
    # if the unperceived region was reached & in the raw winner, it should be pruned
    raw = set(r.workspace.raw_winner.members) if r.workspace.raw_winner else set()
    if {rho, sigma, tau} & raw:
        check(not ({rho, sigma, tau} & winner),
              "the dense unperceived region is still pruned (membership, not weakness)")
    else:
        check(True, "(unperceived region not in raw winner on this field; nothing to prune)")


# ─────────────────────────────────────────────────────────────────────────────
# T3 — C1 GENERALIZES on NEW, structurally-different graphs (NOT relabels)
# ─────────────────────────────────────────────────────────────────────────────

def test_T3_generalize_multiple_bridges_into_unnamed_domain():
    section("T3 C1 generalizes: TWO strong bridges (n=8 each) into ONE unnamed domain — "
            "the unnamed domain is still pruned (not a single-bridge artifact)")
    # Structurally DIFFERENT from _small_mind: two distinct bridge edges into the unnamed
    # domain. If pruning depended on there being a single weak/strong bridge it could break.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    # named domain: sun moon star (triangle)
    sun = s.add_node("sun", NodeType.CONCEPT)
    moon = s.add_node("moon", NodeType.CONCEPT)
    star = s.add_node("star", NodeType.CONCEPT)
    _worn(s, sun, moon, n=30); _worn(s, moon, star, n=30); _worn(s, star, sun, n=30)
    # unnamed domain: iron lead zinc (triangle, dense)
    iron = s.add_node("iron", NodeType.CONCEPT)
    lead = s.add_node("lead", NodeType.CONCEPT)
    zinc = s.add_node("zinc", NodeType.CONCEPT)
    _worn(s, iron, lead, n=30); _worn(s, lead, zinc, n=30); _worn(s, zinc, iron, n=30)
    # TWO bridges from the named domain into the unnamed one
    _worn(s, sun, iron, n=8)
    _worn(s, moon, lead, n=8)
    r = think(s, "sun moon star")
    perceived = set(r.perception.sources)
    check({sun, moon, star} <= perceived, "precondition: sun/moon/star perceived")
    winner = set(r.thought.members) if r.thought else set()
    raw = set(r.workspace.raw_winner.members) if r.workspace.raw_winner else set()
    # require the bug-precondition: the unnamed domain is actually reached into the raw winner
    if {iron, lead, zinc} & raw:
        check(not ({iron, lead, zinc} & winner),
              "the unnamed metal domain is pruned despite TWO bridges into it")
        check({iron, lead, zinc} <= set(r.workspace.pruned_members) or
              not ({iron, lead, zinc} & winner),
              "the unnamed metal domain members are recorded as pruned / excluded")
    else:
        check(True, "(unnamed domain not pulled into raw winner; report-only)")
    check({sun, moon, star} <= winner, "the named domain survives intact")


def test_T3b_generalize_three_domains_mixed_perceived():
    section("T3 C1 generalizes: THREE domains, two perceived + one unperceived; only the "
            "unperceived one is pruned (>=3 domain mixed case)")
    # Different domain SIZES + 3 communities. Name domain A and domain B; leave domain C
    # unnamed but bridged. Only C should be pruned (if pulled into the winner).
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    # domain A (size 2): apple ant
    apple = s.add_node("apple", NodeType.CONCEPT)
    ant = s.add_node("ant", NodeType.CONCEPT)
    _worn(s, apple, ant, n=30)
    # domain B (size 3): boat bell bone
    boat = s.add_node("boat", NodeType.CONCEPT)
    bell = s.add_node("bell", NodeType.CONCEPT)
    bone = s.add_node("bone", NodeType.CONCEPT)
    _worn(s, boat, bell, n=30); _worn(s, bell, bone, n=30); _worn(s, bone, boat, n=30)
    # domain C (size 4, unnamed): cat cap car cow
    cat = s.add_node("cat", NodeType.CONCEPT)
    cap = s.add_node("cap", NodeType.CONCEPT)
    car = s.add_node("car", NodeType.CONCEPT)
    cow = s.add_node("cow", NodeType.CONCEPT)
    _worn(s, cat, cap, n=30); _worn(s, cap, car, n=30); _worn(s, car, cow, n=30); _worn(s, cow, cat, n=30)
    # bridge from A and B into C (the unnamed one)
    _worn(s, apple, cat, n=8)
    _worn(s, boat, cat, n=8)
    # bridge A-B so they may share a coalition or be separate; either way C is the target
    _worn(s, ant, boat, n=8)
    r = think(s, "apple ant boat bell bone")  # names A and B, NOT C
    perceived = set(r.perception.sources)
    check({apple, ant, boat, bell, bone} <= perceived, "precondition: A and B perceived")
    winner = set(r.thought.members) if r.thought else set()
    raw = set(r.workspace.raw_winner.members) if r.workspace.raw_winner else set()
    # whichever coalition wins, no member of C should survive if C was pulled into it
    c_domain = {cat, cap, car, cow}
    if c_domain & raw:
        check(not (c_domain & winner),
              "the unnamed C domain is pruned from the winner (mixed 3-domain case)")
    else:
        check(True, "(C not pulled into the raw winner; report-only)")
    # a perceived member that IS in the raw winner must survive
    perceived_in_raw = perceived & raw
    check(perceived_in_raw <= winner,
          "every perceived member present in the raw winner survives pruning")


def test_T3c_generalize_asymmetric_cohesion():
    section("T3 C1 generalizes: ASYMMETRIC cohesion — named domain LOOSE (n=10), unnamed "
            "domain TIGHT (n=30); the unnamed tight domain is still pruned by MEMBERSHIP")
    # The decisive C1-vs-C2 shape: here the NAMED domain is the loose one and the UNNAMED
    # domain is the tight one. A weakness-only rule (C2) would tend to keep the tight
    # unnamed domain and prune the loose named one — the OPPOSITE of correct. C1 (membership)
    # must keep the named (loose) domain and prune the unnamed (tight) one.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    # named LOOSE domain: lake lily (n=10)
    lake = s.add_node("lake", NodeType.CONCEPT)
    lily = s.add_node("lily", NodeType.CONCEPT)
    reed = s.add_node("reed", NodeType.CONCEPT)
    _worn(s, lake, lily, n=10); _worn(s, lily, reed, n=10); _worn(s, reed, lake, n=10)
    # unnamed TIGHT domain: gold gem glint (n=30)
    gold = s.add_node("gold", NodeType.CONCEPT)
    gem = s.add_node("gem", NodeType.CONCEPT)
    glint = s.add_node("glint", NodeType.CONCEPT)
    _worn(s, gold, gem, n=30); _worn(s, gem, glint, n=30); _worn(s, glint, gold, n=30)
    # moderate bridge from named loose domain into unnamed tight domain
    _worn(s, lake, gold, n=12)
    r = think(s, "lake lily reed")
    perceived = set(r.perception.sources)
    check({lake, lily, reed} <= perceived, "precondition: lake/lily/reed perceived")
    winner = set(r.thought.members) if r.thought else set()
    raw = set(r.workspace.raw_winner.members) if r.workspace.raw_winner else set()
    tight_unnamed = {gold, gem, glint}
    check({lake, lily, reed} & winner == {lake, lily, reed} or
          ({lake, lily, reed} & raw) <= winner,
          "the NAMED (loose) domain members present in the raw winner all survive")
    if tight_unnamed & raw:
        check(not (tight_unnamed & winner),
              "the UNNAMED (tight) domain is pruned by membership even though it is the "
              "more cohesive region (C1, not C2)")
    else:
        check(True, "(unnamed tight domain not pulled into raw winner; report-only)")


# ─────────────────────────────────────────────────────────────────────────────
# T4 — C1 boundary probes (the decisive discriminator vs the rejected C2)
# ─────────────────────────────────────────────────────────────────────────────

def test_T4_weak_cohesion_unperceived_region_still_pruned():
    section("T4 boundary: a WEAKLY-cohesive unperceived region (n=6 internal) is STILL "
            "pruned by membership — C1 does not need cohesion to exceed a threshold")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    # named domain (tight): one two three
    one = s.add_node("one", NodeType.CONCEPT)
    two = s.add_node("two", NodeType.CONCEPT)
    three = s.add_node("three", NodeType.CONCEPT)
    _worn(s, one, two, n=30); _worn(s, two, three, n=30); _worn(s, three, one, n=30)
    # unnamed region weakly cohesive internally (n=6) but reachable
    fourx = s.add_node("fourx", NodeType.CONCEPT)
    fivex = s.add_node("fivex", NodeType.CONCEPT)
    _worn(s, fourx, fivex, n=6)
    _worn(s, one, fourx, n=8)   # bridge stronger than the unnamed region's internal link
    r = think(s, "one two three")
    perceived = set(r.perception.sources)
    check({one, two, three} <= perceived, "precondition: one/two/three perceived")
    winner = set(r.thought.members) if r.thought else set()
    raw = set(r.workspace.raw_winner.members) if r.workspace.raw_winner else set()
    unnamed = {fourx, fivex}
    # NOTE: here the bridge (n=8 -> strength) EXCEEDS the unnamed region's internal link
    # (n=6). Under the watershed, fourx's strongest road to perceived (the n=8 bridge) is
    # >= its strongest road to unperceived (the n=6 internal), so fourx ADOPTS perceived.
    # We REPORT the outcome and assert internal consistency rather than presuppose pruning.
    f4_to_perceived = _strongest_road_strength(s, fourx, one)
    f4_to_unperc = _strongest_road_strength(s, fourx, fivex)
    print(f"      probe: fourx->perceived(one)={round(f4_to_perceived,4)} "
          f"fourx->unperceived(fivex)={round(f4_to_unperc,4)}")
    in_raw = unnamed & raw
    if in_raw:
        # whichever way it goes, the watershed result must equal the documented rule:
        kept = _perceived_domain_members(
            s, list(r.workspace.raw_winner.members), perceived)
        for node, label in (("fourx", fourx), ("fivex", fivex)):
            if label in raw:
                in_winner = label in winner
                in_kept = label in kept
                check(in_winner == in_kept,
                      f"{node}: winner-membership matches the watershed rule "
                      f"(consistent, deterministic)")
    else:
        check(True, "(unnamed region not in raw winner; report-only)")


def test_T4b_decisive_C1_not_C2_strong_bridge_into_unnamed():
    section("T4b DECISIVE C1-vs-C2: a strong bridge into an UNNAMED domain whose internal "
            "cohesion is EVEN STRONGER — pruned by membership; a pure weakness rule could "
            "not flip _small_mind, this watershed flips by domain not by a weakness cut")
    # This is the exact discriminator the brief names. The bridge is strong (n=8) but the
    # unnamed domain's internal ties (n=30) are stronger, so the watershed pulls the unnamed
    # domain into its OWN community and prunes it. Replicates the _small_mind logic on a
    # fresh non-isomorphic graph (5-node unnamed domain).
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    # named: river rock (size 2)
    river = s.add_node("river", NodeType.CONCEPT)
    rock = s.add_node("rock", NodeType.CONCEPT)
    _worn(s, river, rock, n=30)
    # unnamed dense 5-clique-ish: node a b c d e
    ua = s.add_node("uxa", NodeType.CONCEPT)
    ub = s.add_node("uxb", NodeType.CONCEPT)
    uc = s.add_node("uxc", NodeType.CONCEPT)
    ud = s.add_node("uxd", NodeType.CONCEPT)
    ue = s.add_node("uxe", NodeType.CONCEPT)
    dense = [ua, ub, uc, ud, ue]
    for i in range(len(dense)):
        for j in range(i + 1, len(dense)):
            _worn(s, dense[i], dense[j], n=30)
    _worn(s, river, ua, n=8)   # strong bridge into the dense unnamed domain
    r = think(s, "river rock")
    perceived = set(r.perception.sources)
    check({river, rock} <= perceived, "precondition: river/rock perceived")
    winner = set(r.thought.members) if r.thought else set()
    raw = set(r.workspace.raw_winner.members) if r.workspace.raw_winner else set()
    dense_set = set(dense)
    if dense_set & raw:
        check(not (dense_set & winner),
              "the dense UNNAMED domain is pruned despite a strong bridge (membership "
              "watershed, not a weakness threshold)")
    else:
        check(True, "(dense domain not pulled into raw winner; report-only)")
    check({river, rock} <= winner, "the named domain survives")


# ─────────────────────────────────────────────────────────────────────────────
# T5 — threshold-free audit (no calibrated constant in the pruning path)
# ─────────────────────────────────────────────────────────────────────────────

def test_T5_pruning_is_invariant_to_min_size_guard():
    section("T5 threshold-free: the PRUNING result (pruned_members) is invariant to "
            "DEFAULT_MIN_SIZE_GUARD over a wide sweep — proving that constant lives in "
            "COMPETITION, not in pruning (the pruning path has no calibrated constant)")
    # If the winner identity is stable across guards, pruned_members must be too — because
    # pruning is a pure function of (winner members, perceived sources, road strengths),
    # none of which involves the guard. We sweep the guard from 1..12 and assert the
    # pruned set is identical wherever the SAME raw winner is chosen.
    s, n = _small_mind()
    p = perceive(s, "coffee in the kitchen this morning")
    clustering = cluster_sources(s, p.sources)
    field_ = build_activation_field(
        s, list(clustering.group_seeds.keys()),
        hop_budget=6, source_energies=clustering.group_seeds,
    )
    coalitions = form_coalitions_from_field(field_, s)
    results = {}
    for guard in range(1, 13):
        ws = select_winner(s, coalitions, field_, clustering, p.sources,
                           min_size_guard=guard)
        raw = frozenset(ws.raw_winner.members) if ws.raw_winner else frozenset()
        results[guard] = (raw, ws.pruned_members)
    # group by raw winner; within each group pruned_members MUST be identical
    by_raw = {}
    for guard, (raw, pruned) in results.items():
        by_raw.setdefault(raw, set()).add(pruned)
    all_consistent = all(len(prunes) == 1 for prunes in by_raw.values())
    check(all_consistent,
          "for every raw-winner choice, pruned_members is identical across all guards "
          "(pruning does not read the guard — it is threshold-free)")
    # and on this graph the raw winner is stable AND the work domain is always pruned
    pruned_contents = {tuple(sorted(s.get_node(m).content for m in pr))
                       for (_, pr) in results.values()}
    work_always_pruned = all(
        (n["work"] in pr and n["code"] in pr) for (_, pr) in results.values()
    )
    check(work_always_pruned,
          "work and code are pruned for EVERY guard value (the flip is not guard-tuned)")


def test_T5b_no_numeric_threshold_constant_in_pruning_source():
    section("T5 threshold-free (structural): the watershed helpers contain no magic numeric "
            "comparison constant; pruning compares stored road strengths only")
    # Inspect the source of the pruning helpers for hidden tunable constants. The ONLY
    # comparisons should be against 0.0 (existence of a road) and between two read road
    # strengths — never against a calibrated fraction/threshold literal.
    src_watershed = inspect.getsource(_perceived_domain_members)
    src_road = inspect.getsource(_strongest_road_strength)
    blob = src_watershed + src_road
    # crude but effective: collect float/fraction-looking literals that are NOT 0.0/1.0
    import re
    literals = re.findall(r"(?<![\w.])\d+\.\d+", blob)
    suspicious = [x for x in literals if x not in ("0.0", "1.0")]
    check(not suspicious,
          f"no calibrated numeric threshold in the pruning path (suspicious literals: "
          f"{suspicious})")
    # and the watershed does not reference the only module constant (the guard)
    check("DEFAULT_MIN_SIZE_GUARD" not in blob and "min_size_guard" not in blob,
          "the watershed does not read the min-size guard (guard is competition-only)")


# ─────────────────────────────────────────────────────────────────────────────
# T6 — cross-process determinism, ALL 6 seeds, our OWN probe
# ─────────────────────────────────────────────────────────────────────────────

def _det_probe(driver_body):
    """Run driver under 6 distinct PYTHONHASHSEED values in fresh interpreters. Return
    list of stdout strings (mirrors the established subprocess-probe pattern)."""
    outs = []
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(os.path.dirname(here), "src")
    for seed in ("0", "1", "2", "7", "42", "999"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"]
                                   if env.get("PYTHONPATH") else "")
        rr = subprocess.run([sys.executable, "-c", driver_body],
                            cwd=here, capture_output=True, text=True, env=env)
        if rr.returncode != 0:
            print("  (subprocess error)\n", rr.stderr)
            outs.append("ERROR:" + rr.stderr.strip()[-300:])
        else:
            outs.append(rr.stdout.strip())
    return outs


def test_T6_determinism_winner_pruned_ranked_6_seeds():
    section("T6 cross-process determinism: winner + pruned_members + FULL ranked order "
            "byte-identical across 6 hash seeds (our own probe; ties everywhere)")
    # Equal traversal counts everywhere -> equal strengths -> equal densities -> the sort
    # MUST fall back to size then creation_seq. If any uuid/iteration order leaked, ranked
    # order would differ across seeds.
    # SPEC-0c §5.1: BIT PATTERNS, never round(x, 9).
    driver = textwrap.dedent('''
        import struct
        from nous_store import SubstrateStore, Clock, NodeType
        from nous_perceive import think
        s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
        def add(c, t=NodeType.CONCEPT): return s.add_node(c, t)
        coffee=add("coffee",NodeType.ENTITY); warmth=add("warmth",NodeType.SENSATION)
        morning=add("morning routine"); cozy=add("cozy feeling"); kitchen=add("kitchen",NodeType.ENTITY)
        work=add("work"); desk=add("desk",NodeType.ENTITY); deadline=add("deadline pressure"); code=add("writing code")
        def w(a,b,n):
            for _ in range(n): s.traverse(a,b)
        w(coffee,warmth,30); w(coffee,morning,30); w(morning,cozy,30); w(coffee,kitchen,30); w(kitchen,morning,30)
        w(work,desk,30); w(work,deadline,30); w(work,code,30); w(desk,code,30); w(coffee,work,8)
        r = think(s, "coffee in the kitchen this morning")
        winner = tuple(sorted(s.get_node(m).content for m in r.thought.members)) if r.thought else None
        pruned = tuple(sorted(s.get_node(m).content for m in r.workspace.pruned_members))
        ranked = tuple(
            (tuple(sorted(s.get_node(m).content for m in c.members)),
             struct.pack("<d", c.strength).hex(), c.size())
            for c in r.workspace.ranked
        )
        raw = tuple(sorted(s.get_node(m).content for m in r.workspace.raw_winner.members)) if r.workspace.raw_winner else None
        rep = s.get_node(r.thought.representative()).content if r.thought else None
        print(repr((winner, pruned, ranked, raw, rep)))
    ''')
    outs = _det_probe(driver)
    check(len(set(outs)) == 1,
          f"winner+pruned+ranked+raw+rep identical across 6 seeds "
          f"(distinct outputs: {len(set(outs))})")
    if len(set(outs)) != 1:
        for i, o in enumerate(outs):
            print(f"      seed#{i}: {o[:160]}")


def test_T6b_determinism_multi_basin_ties_6_seeds():
    section("T6b cross-process determinism on a MULTI-BASIN tie graph: two equal-sized, "
            "equal-strength unlinked domains -> a genuine density+size+strength tie broken "
            "only by creation_seq; identical winner/ranked across 6 seeds")
    # SPEC-0c §5.1: BIT PATTERNS, never round(x, 9). THIS probe is the one that caught
    # BUG-0b1, and it caught it only because the 1-ULP leak happened to flip a categorical
    # winner — round(x, 9) could never have seen the ULP itself. Serialising the strength
    # exactly is what makes the next such leak visible before it flips anything.
    driver = textwrap.dedent('''
        import struct
        from nous_store import SubstrateStore, Clock, NodeType
        from nous_perceive import think
        s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
        def add(c, t=NodeType.CONCEPT): return s.add_node(c, t)
        # two identical, unlinked triangles named by one token each -> equal everything
        a1=add("alfa"); a2=add("bravo"); a3=add("charlie")
        b1=add("delta"); b2=add("echo"); b3=add("foxtrot")
        def w(a,b,n=30):
            for _ in range(n): s.traverse(a,b)
        w(a1,a2); w(a2,a3); w(a3,a1)
        w(b1,b2); w(b2,b3); w(b3,b1)
        r = think(s, "alfa bravo charlie delta echo foxtrot")
        winner = tuple(sorted(s.get_node(m).content for m in r.thought.members)) if r.thought else None
        ranked = tuple(
            (tuple(sorted(s.get_node(m).content for m in c.members)),
             struct.pack("<d", c.strength).hex(), c.size())
            for c in r.workspace.ranked
        )
        print(repr((winner, ranked)))
    ''')
    outs = _det_probe(driver)
    check(len(set(outs)) == 1,
          f"multi-basin tie graph identical across 6 seeds (distinct: {len(set(outs))})")
    if len(set(outs)) != 1:
        for i, o in enumerate(outs):
            print(f"      seed#{i}: {o[:160]}")


# ─────────────────────────────────────────────────────────────────────────────
# T7 — purity: ZERO mutation in the selection path (deep snapshot)
# ─────────────────────────────────────────────────────────────────────────────

def test_T7_select_winner_is_pure_read_deep_snapshot():
    section("T7 purity: 12 repeated select_winner calls mutate NOTHING (deep snapshot incl. "
            "last_touched + node access stats)")
    s, n = _small_mind()
    p = perceive(s, "coffee in the kitchen this morning")
    clustering = cluster_sources(s, p.sources)
    field_ = build_activation_field(
        s, list(clustering.group_seeds.keys()),
        hop_budget=6, source_energies=clustering.group_seeds,
    )
    coalitions = form_coalitions_from_field(field_, s)
    before = _deep_snapshot(s)
    for _ in range(12):
        select_winner(s, coalitions, field_, clustering, p.sources)
    after = _deep_snapshot(s)
    check(before == after,
          "12 repeated select_winner calls changed no road and no node access stat")


def test_T7b_think_broadcast_false_pure_on_adversarial_graph():
    section("T7 purity: think(broadcast=False) byte-identical across repeated calls on an "
            "ADVERSARIAL graph (cycle + self-loop + closed road + duplicate content + fan)")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    a = s.add_node("alpha", NodeType.CONCEPT)
    b = s.add_node("alpha", NodeType.CONCEPT)   # duplicate content
    c = s.add_node("gamma", NodeType.CONCEPT)
    _worn(s, a, b); _worn(s, b, c); _worn(s, c, a)   # cycle
    _worn(s, a, a)                                    # self-loop
    hub = s.add_node("hub", NodeType.CONCEPT)
    leaves = [s.add_node(f"leaf gamma {i}", NodeType.CONCEPT) for i in range(12)]
    for lf in leaves:
        _worn(s, hub, lf)
    x = s.add_node("xeno", NodeType.CONCEPT)
    y = s.add_node("yotta", NodeType.CONCEPT)
    for _ in range(5):
        s.traverse(x, y, charge={"fear": -0.95})     # close the road
    before = _deep_snapshot(s)
    for _ in range(5):
        think(s, "alpha gamma hub xeno yotta")
        think(s, "alpha gamma", broadcast=False)
    after = _deep_snapshot(s)
    check(before == after,
          "10 think(broadcast=False) passes on an adversarial graph changed no stored state")


def test_T7c_broadcast_true_now_performs_exactly_one_write_reowned():
    section("T7c (RE-OWNED for 1d-ii): broadcast=True now performs EXACTLY ONE bounded write "
            "(the winner's internal roads, once each, no new road, nodes neutral); "
            "broadcast=False still mutates NOTHING")
    # ── WHY THIS TEST CHANGED (tester-owned re-derivation, NOT accepted on authority) ──
    # In the 1d-i era this assertion read "broadcast=True raises NotImplementedError / the
    # failed attempt mutated nothing" — a tester-owned asserted-NEGATIVE documenting that the
    # feedback write did not exist yet. 1d-ii (broadcast + bounded feedback) is now built, so
    # that negative is FALSE BY DESIGN. The builder correctly did NOT edit this tester file to
    # mask it (that would be a lane violation — the analog of P9->T11 in the 1c cycle); the
    # builder flipped only its OWN copy. Re-owning it is the tester's job.
    #
    # I do not accept the flip on authority. I RE-DERIVE the now-built contract independently
    # and only re-author the assertion if my derivation agrees. My derivation, from the
    # mechanism (nous_workspace.broadcast + nous_store.strengthen, both read directly):
    #   (1) broadcast=True must strengthen EXACTLY the winner's internal roads (both endpoints
    #       in the winner), each EXACTLY ONCE (deduped by RoadID), creating NO new road, and
    #       touching NO node (strengthen with no charge moves no node access stat).
    #   (2) broadcast=False (the default) must remain a pure read — byte-identical store.
    # Both are checked below on the exact _small_mind graph the old negative used, loop-closed.
    s, n = _small_mind()

    # (2) first: broadcast=False is still a pure read (the guarantee 1d-i shipped survives).
    before_pure = _deep_snapshot(s)
    rf = think(s, "coffee in the kitchen this morning")          # default broadcast=False
    after_pure = _deep_snapshot(s)
    check(rf.broadcast_ is None, "broadcast=False records no Broadcast (broadcast_ is None)")
    check(before_pure == after_pure,
          "RE-DERIVED: broadcast=False mutates NOTHING (the 1d-i pure-read guarantee holds "
          "unchanged under 1d-ii)")

    # (1): broadcast=True performs exactly one write — the winner's internal roads, once each.
    winner = rf.thought
    expected_roads = set(_internal_road_ids(s, winner))   # independent recomputation
    rc_before = s.road_count()
    roads_before, nodes_before = _deep_snapshot(s)
    tc_before = {rid: s.get_road(rid, apply_decay=False).traversal_count
                 for rid in expected_roads}
    rt = think(s, "coffee in the kitchen this morning", broadcast=True)
    roads_after, nodes_after = _deep_snapshot(s)
    tc_after = {rid: s.get_road(rid, apply_decay=False).traversal_count
                for rid in expected_roads}

    check(rt.broadcast_ is not None,
          "RE-DERIVED: broadcast=True now performs the write (Broadcast record present, no "
          "NotImplementedError) — the old asserted-negative is correctly false by design")
    check(set(rt.broadcast_.road_ids) == expected_roads,
          "the write targets EXACTLY the winner's internal roads (independently recomputed)")
    changed = {rid for rid in roads_after if roads_before.get(rid) != roads_after[rid]}
    check(changed == expected_roads,
          f"EXACTLY the winner's internal roads changed and nothing else "
          f"(changed={len(changed)} expected={len(expected_roads)})")
    check(all(tc_after[rid] - tc_before[rid] == 1 for rid in expected_roads),
          "each internal road was strengthened EXACTLY ONCE (traversal_count +1; no "
          "double-count at a convergence point)")
    check(rc_before == s.road_count(),
          "broadcast created NO new road (road_count unchanged)")
    check(nodes_before == nodes_after,
          "broadcast touched NO node (nodes stay neutral — the substrate requires it)")
    # CONCLUSION (re-owned): my independent derivation AGREES with the flip. broadcast=True
    # now performs exactly one bounded write and broadcast=False is still a pure read, so I
    # re-author the assertion in my own voice to reflect the now-built 1d-ii behavior.
    print("      → RE-OWNED: independent derivation agrees; broadcast=True performs exactly "
          "one write, broadcast=False stays pure. See verdict.")


# ─────────────────────────────────────────────────────────────────────────────
# T8 — integrity: randomized mutation battery, indices consistent throughout
# ─────────────────────────────────────────────────────────────────────────────

def test_T8_mutation_battery_integrity_and_purity():
    section("T8 integrity: a randomized mutation battery on a hostile graph, interleaved "
            "with 200 selection calls; check_integrity() clean throughout + byte-identical")
    import random
    rng = random.Random(20260620)   # fixed seed -> the battery itself is reproducible
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    ids = []
    contents = ["coffee", "kitchen", "morning routine", "work", "desk", "writing code",
                "warmth", "deadline pressure", "cozy feeling", "alpha", "beta", "gamma"]
    for cnt in contents:
        ids.append(s.add_node(cnt, NodeType.CONCEPT))
    # random mutation battery: traversals (incl. self-loops, duplicates, charges, trauma)
    for _ in range(400):
        a = rng.choice(ids)
        b = rng.choice(ids)   # may equal a -> self-loop
        kind = rng.random()
        if kind < 0.15:
            s.traverse(a, b, charge={"fear": -0.95})   # may close
        elif kind < 0.30:
            s.traverse(a, b, charge={"joy": 0.8})
        else:
            s.traverse(a, b)
    # advance simulated clock a bit so decay views differ from canonical (still pure)
    s.clock.advance(3.0)
    try:
        s.check_integrity()
        ok0 = True
    except Exception as e:
        ok0 = False
        print("   integrity error (pre):", e)
    check(ok0, "precondition: hostile mutated graph is integral")

    snap = _deep_snapshot(s)
    utters = ["coffee in the kitchen this morning", "work at the desk",
              "alpha beta gamma", "coffee writing code", "warmth and the deadline"]
    integ_ok = True
    for i in range(200):
        u = utters[i % len(utters)]
        think(s, u)                       # full selection path
        if i % 25 == 0:
            try:
                s.check_integrity()
            except Exception as e:
                integ_ok = False
                print("   integrity error (loop):", e)
                break
    check(integ_ok, "integrity holds across 200 interleaved selection calls")
    check(_deep_snapshot(s) == snap,
          "store byte-identical after the whole selection battery (selection is pure)")


# ─────────────────────────────────────────────────────────────────────────────
# T9 — hostile topologies for the COMPETITION + watershed helper
# ─────────────────────────────────────────────────────────────────────────────

def test_T9_empty_coalitions():
    section("T9 hostile: empty coalition list -> winner None, empty pruned/ranked, no crash")
    s, n = _small_mind()
    p = perceive(s, "coffee in the kitchen this morning")
    clustering = cluster_sources(s, p.sources)
    field_ = build_activation_field(
        s, list(clustering.group_seeds.keys()),
        hop_budget=6, source_energies=clustering.group_seeds,
    )
    ws = select_winner(s, [], field_, clustering, p.sources)
    check(ws.winner is None and ws.raw_winner is None, "no coalitions -> winner None")
    check(ws.pruned_members == frozenset() and ws.ranked == [],
          "no coalitions -> empty pruned set and empty ranked list")


def test_T9b_empty_utterance_loop_closed():
    section("T9 hostile: an utterance that names NOTHING -> empty workspace, no crash")
    s, n = _small_mind()
    r = think(s, "zzz qqq xyzzy")   # no token matches a node
    check(r.thought is None and (r.workspace is None or r.workspace.winner is None),
          "an utterance matching nothing yields no winner and does not crash")


def test_T9c_singleton_coalition_winner():
    section("T9 hostile: a single isolated perceived node -> singleton coalition wins, "
            "is NOT pruned (a lone perceived seed cannot be 'a domain no source named')")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    lone = s.add_node("solitude", NodeType.CONCEPT)
    r = think(s, "solitude")
    check(r.thought is not None and set(r.thought.members) == {lone},
          "the lone perceived node is the winner")
    check(lone not in (r.workspace.pruned_members if r.workspace else set()),
          "the lone perceived seed is not pruned")


def test_T9d_density_competition_discriminates_unit():
    section("T9 competition: density (not summed strength) picks the tighter of two "
            "equal-total coalitions; min-size guard blocks a degenerate singleton")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    ids = [s.add_node(f"z{i}", NodeType.CONCEPT) for i in range(10)]
    seqm = {nid: s.get_node(nid).creation_seq for nid in ids}
    # tight 3-member total 6.0 vs sprawl 6-member total 6.0
    tightm = {ids[0]: 2.0, ids[1]: 2.0, ids[2]: 2.0}
    tight = Coalition(members=tightm, strength=6.0, _seq={k: seqm[k] for k in tightm})
    sprawlm = {ids[i]: 1.0 for i in range(3, 9)}
    sprawl = Coalition(members=sprawlm, strength=6.0, _seq={k: seqm[k] for k in sprawlm})
    ranked = rank_coalitions([sprawl, tight])
    check(ranked[0] is tight, "density picks the tighter equal-total coalition")
    # degenerate singleton with huge per-node activation must NOT beat a substantial one
    singleton = Coalition(members={ids[9]: 100.0}, strength=100.0, _seq={ids[9]: seqm[ids[9]]})
    big = Coalition(members={ids[0]: 5.0, ids[1]: 5.0, ids[2]: 5.0, ids[3]: 5.0},
                    strength=20.0, _seq={k: seqm[k] for k in (ids[0], ids[1], ids[2], ids[3])})
    # singleton density with guard>=3: 100/3 ~ 33.3 ; big: 20/4=5.0 -> singleton STILL wins
    # the guard does NOT claim to stop a genuinely intense singleton; it only stops a small
    # coalition winning *purely by being small* at equal totals. We assert the guard's real
    # contract: it divides by max(size,guard). Verify the documented behavior numerically.
    ds_single = _density_score(singleton, min_size_guard=DEFAULT_MIN_SIZE_GUARD)
    check(abs(ds_single - 100.0 / max(1, DEFAULT_MIN_SIZE_GUARD)) < 1e-12,
          "singleton density divides by the guard, not by 1 (guard active)")
    # equal-per-node singleton vs substantial: guard makes substantial win
    eq_single = Coalition(members={ids[9]: 3.0}, strength=3.0, _seq={ids[9]: seqm[ids[9]]})
    substantial = Coalition(members={ids[0]: 3.0, ids[1]: 3.0, ids[2]: 3.0, ids[3]: 3.0},
                            strength=12.0,
                            _seq={k: seqm[k] for k in (ids[0], ids[1], ids[2], ids[3])})
    r2 = rank_coalitions([eq_single, substantial])
    check(r2[0] is substantial,
          "at equal per-node activation, the guard stops the singleton winning on density")


def test_T9e_duplicate_edges_and_cycles_do_not_break_competition():
    section("T9 hostile: duplicate-content nodes, cycles, self-loops in the live loop -> "
            "competition still selects exactly one winner deterministically")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    a = s.add_node("rune", NodeType.CONCEPT)
    b = s.add_node("rune", NodeType.CONCEPT)   # duplicate content (perceived together)
    c = s.add_node("rune", NodeType.CONCEPT)   # triple duplicate
    _worn(s, a, b); _worn(s, b, c); _worn(s, c, a)   # cycle among the duplicates
    _worn(s, a, a)                                    # self-loop
    r = think(s, "rune")
    check(r.thought is not None, "a winner is selected on the duplicate-content cycle graph")
    check(isinstance(r.thought, Coalition) and not isinstance(r.thought, (list, set, tuple)),
          "exactly one winner (single Coalition), no parallel winners")


def test_T9f_high_degree_fan_winner():
    section("T9 hostile: a high-degree fan hub (1 hub -> 25 leaves) all in one basin; the "
            "winner is well-formed and selection is deterministic on the fan")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    hub = s.add_node("nexus", NodeType.CONCEPT)
    leaves = [s.add_node(f"spoke {i:02d}", NodeType.CONCEPT) for i in range(25)]
    for lf in leaves:
        _worn(s, hub, lf)
    r = think(s, "nexus")
    check(r.thought is not None, "a winner exists on the 25-leaf fan")
    # the hub's basin is one coalition; winner membership is a subset of the raw winner
    raw = set(r.workspace.raw_winner.members) if r.workspace.raw_winner else set()
    check(set(r.thought.members) <= raw, "winner is the (possibly pruned) top coalition")


def test_T9g_watershed_helper_separates_communities_unit():
    section("T9 watershed helper (unit): on _small_mind, the watershed keeps the warm "
            "community (incl. non-source warmth/cozy) and excludes the work community")
    s, n = _small_mind()
    perceived = {n["coffee"], n["kitchen"], n["morning"]}
    members = [n["coffee"], n["warmth"], n["morning"], n["cozy"], n["kitchen"],
               n["work"], n["desk"], n["deadline"], n["code"]]
    kept = _perceived_domain_members(s, members, perceived)
    check({n["coffee"], n["warmth"], n["morning"], n["cozy"], n["kitchen"]} <= kept,
          "the named warm community is kept (transitive, incl. non-source members)")
    check(not ({n["work"], n["desk"], n["deadline"], n["code"]} & kept),
          "the bridged unnamed work community is excluded")


def test_T9h_watershed_order_independence_permuted_member_lists():
    section("T9 watershed determinism: the kept set is identical under ANY permutation of "
            "the member-id input list (frozen-per-pass fixpoint is order-independent)")
    import random
    s, n = _small_mind()
    perceived = {n["coffee"], n["kitchen"], n["morning"]}
    base_members = [n["coffee"], n["warmth"], n["morning"], n["cozy"], n["kitchen"],
                    n["work"], n["desk"], n["deadline"], n["code"]]
    base_kept = _perceived_domain_members(s, base_members, perceived)
    rng = random.Random(7)
    all_same = True
    for _ in range(30):
        perm = base_members[:]
        rng.shuffle(perm)
        k = _perceived_domain_members(s, perm, perceived)
        if k != base_kept:
            all_same = False
            break
    check(all_same,
          "watershed result invariant under 30 random permutations of the member list")


# ─────────────────────────────────────────────────────────────────────────────
# T10 — scale-invariance of BOTH criteria
# ─────────────────────────────────────────────────────────────────────────────

def _scale_coalition(c, k):
    members = {m: a * k for m, a in c.members.items()}
    return Coalition(members=members, strength=c.strength * k, intrusive=c.intrusive,
                     breakthrough_members=set(c.breakthrough_members), _seq=dict(c._seq))


def test_T10_selection_scale_invariant_isolated():
    section("T10 scale-invariance: scaling all coalition activations by any positive "
            "constant (1e-15 .. 1e15) keeps winner identity AND pruned_members")
    s, n = _small_mind()
    p = perceive(s, "coffee in the kitchen this morning")
    clustering = cluster_sources(s, p.sources)
    field_ = build_activation_field(
        s, list(clustering.group_seeds.keys()),
        hop_budget=6, source_energies=clustering.group_seeds,
    )
    coalitions = form_coalitions_from_field(field_, s)
    base = select_winner(s, coalitions, field_, clustering, p.sources)
    base_winner = frozenset(base.winner.members) if base.winner else frozenset()
    base_pruned = base.pruned_members
    for k in (1e-15, 1e-9, 0.001, 3.3, 1e6, 1e15):
        scaled = [_scale_coalition(c, k) for c in coalitions]
        ws = select_winner(s, scaled, field_, clustering, p.sources)
        wn = frozenset(ws.winner.members) if ws.winner else frozenset()
        check(wn == base_winner, f"winner identical at activation scale {k}")
        check(ws.pruned_members == base_pruned, f"pruned identical at activation scale {k}")


def test_T10b_pruning_scale_invariant_in_road_strength_structure():
    section("T10 scale-invariance (road strength): identical TOPOLOGY at different absolute "
            "strengths (n=8/12/30 vs n=4/6/15) yields the same prune decision (membership)")
    def build(scale):
        s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
        # named pair
        x = s.add_node("xx", NodeType.CONCEPT); y = s.add_node("yy", NodeType.CONCEPT)
        # unnamed triangle
        u1 = s.add_node("u1", NodeType.CONCEPT); u2 = s.add_node("u2", NodeType.CONCEPT)
        u3 = s.add_node("u3", NodeType.CONCEPT)
        _worn(s, x, y, n=15 * scale)
        _worn(s, u1, u2, n=15 * scale); _worn(s, u2, u3, n=15 * scale); _worn(s, u3, u1, n=15 * scale)
        _worn(s, x, u1, n=4 * scale)   # bridge proportionally weaker than internal ties
        return s, x, y, {u1, u2, u3}
    decisions = []
    for scale in (1, 2):
        s, x, y, unnamed = build(scale)
        members = [x, y] + list(unnamed)
        kept = _perceived_domain_members(s, members, {x, y})
        decisions.append(frozenset(s.get_node(m).content for m in (set(members) - kept)))
    check(len(set(decisions)) == 1,
          f"prune decision identical at proportionally-scaled strengths (got {decisions})")


# ─────────────────────────────────────────────────────────────────────────────
# T11 — P9 RE-DERIVATION (re-owned in the tester's voice)
# ─────────────────────────────────────────────────────────────────────────────

def test_T11_P9_reowned_over_swallow_residual_is_gone():
    section("T11 (P9 RE-OWNED): INDEPENDENT re-derivation that, after 1d-i, the "
            "over-swallow residual is ABSENT — by the membership watershed, not by tuning")
    # TESTER'S INDEPENDENT REASONING (re-authored, not the builder's note):
    #
    # The 1c-era P9 asserted over-swallow PERSISTS (over == True). The builder flipped it.
    # I do not accept the flip on authority; I re-derive it from the mechanism.
    #
    # Claim to verify: on think("coffee in the kitchen this morning"), the winner excludes
    # work/code/desk/deadline, AND this exclusion is a NECESSARY consequence of the C1
    # watershed (perceived = {coffee,kitchen,morning}), NOT of any tuned threshold.
    #
    # Independent argument: the field still REACHES the work domain (the n=8 bridge is
    # unchanged — pruning is downstream of the field). 'work' has internal ties of n=30 to
    # desk/deadline/code but only an n=8 bridge to the perceived region. So work's strongest
    # road to a PERCEIVED member (<= the n=8 bridge's strength) is strictly LESS than its
    # strongest road to a NON-perceived member (the n=30 internal tie). The watershed rule
    # (adopt PERCEIVED iff pull-to-perceived >= pull-to-unperceived) therefore CANNOT label
    # work perceived; the same holds for desk/deadline/code. They are pruned. This is a
    # consequence of road strengths the substrate already stores — no calibrated constant.
    #
    # I verify EACH link of that chain below, on a freshly built graph.
    s, n = _small_mind()
    r = think(s, "coffee in the kitchen this morning")
    perceived = set(r.perception.sources)
    check(perceived == {n["coffee"], n["kitchen"], n["morning"]},
          "perceived set is exactly the warm domain (the watershed seeds)")
    # link 1: the field reaches work/code (the residual's precondition still holds)
    reached = set(r.field_.total.keys())
    check(n["work"] in reached and n["code"] in reached,
          "link1: the spread still reaches work/code (pruning is downstream of the field)")
    # link 2: work's pull toward perceived < its pull toward unperceived
    work_to_coffee = _strongest_road_strength(s, n["work"], n["coffee"])     # the n=8 bridge
    work_to_desk = _strongest_road_strength(s, n["work"], n["desk"])         # n=30 internal
    work_to_code = _strongest_road_strength(s, n["work"], n["code"])         # n=30 internal
    check(work_to_coffee > 0.0, "link2a: work has a (bridge) road toward the perceived side")
    check(work_to_coffee < max(work_to_desk, work_to_code),
          f"link2b: work's pull to perceived ({round(work_to_coffee,4)}) < its pull to "
          f"unperceived ({round(max(work_to_desk, work_to_code),4)}) — so the watershed "
          f"cannot adopt work")
    # link 3: therefore the winner excludes the whole work domain, and they are recorded
    thought_members = set(r.thought.members) if r.thought else set()
    check(not ({n["work"], n["code"], n["desk"], n["deadline"]} & thought_members),
          "link3: the winner excludes the entire work domain (residual gone)")
    check({n["work"], n["code"]} <= set(r.workspace.pruned_members),
          "link3b: work and code are recorded in pruned_members")
    # CONCLUSION (re-owned): my independent derivation AGREES with the flip. The
    # over-swallow residual is genuinely absent after 1d-i, by domain membership, not by a
    # tuned threshold. I re-author the assertion as my own (this test).
    print("      → RE-OWNED: independent derivation agrees; residual is absent by the C1 "
          "membership watershed (no tuning). See verdict.")


def test_T11b_P9_flip_depends_on_what_was_named_counterfactual():
    section("T11b (P9 re-owned, counterfactual): the SAME graph with the work domain NAMED "
            "does NOT prune it — proving the flip is membership-driven, not a fixed cut")
    # The decisive anti-tuning control: identical topology, only the utterance changes.
    # If the flip were a tuned weakness cut, naming the work domain could not save it. It does.
    s1, n1 = _small_mind()
    r_warm = think(s1, "coffee in the kitchen this morning")
    pruned_warm = set(r_warm.workspace.pruned_members)
    s2, n2 = _small_mind()
    r_work = think(s2, "work at the desk")
    work_winner = set(r_work.thought.members) if r_work.thought else set()
    check(n1["work"] in pruned_warm,
          "when warm is named, the (unnamed) work domain is pruned")
    check(n2["work"] in work_winner,
          "when work is named, it is KEPT (the flip follows what was named, not a cut)")


# ─────────────────────────────────────────────────────────────────────────────
# T12 — audit of a possible over-inclusion seam in the watershed tie rule
# ─────────────────────────────────────────────────────────────────────────────

def test_T12_watershed_chaining_floods_perceived_through_equal_strength_ties():
    section("T12 watershed CHAINING (corrected derivation): on an EQUAL-STRENGTH chain "
            "per=mid=unp=other, the PERCEIVED label floods the WHOLE connected component "
            "(single-link chaining through ties). We pin this ACTUAL behavior — it is the "
            "watershed's load-bearing property and the crux of the C1 adjudication.")
    # CORRECTED: an earlier prediction assumed 'unp'/'other' would stay unperceived. That
    # was wrong, and the wrongness is informative. Trace, all edges strength S (n=20):
    #   pass1 snapshot={per}: mid sees per(S, perceived) and unp(S, unperceived) -> S>=S adopt.
    #   pass2 snapshot={per,mid}: unp sees mid(S, NOW perceived) and other(S) -> S>=S adopt.
    #   pass3 snapshot={per,mid,unp}: other sees unp(S, perceived) -> S>=0 adopt.
    # So the entire component is PERCEIVED. The watershed prunes ONLY where a STRICT strength
    # decrease separates a region from the perceived seeds — i.e. it stops at a genuine
    # cohesion valley, NOT at "membership in an unnamed community" per se. This is the single
    # decisive fact behind the C1 verdict (see report): with equal weights, NOTHING is pruned.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    per = s.add_node("perr", NodeType.CONCEPT)        # perceived seed
    mid = s.add_node("midd", NodeType.CONCEPT)
    unp = s.add_node("unpp", NodeType.CONCEPT)
    other = s.add_node("oth", NodeType.CONCEPT)
    _worn(s, per, mid, n=20)
    _worn(s, mid, unp, n=20)        # EQUAL strength
    _worn(s, unp, other, n=20)      # EQUAL strength
    members = [per, mid, unp, other]
    kept = _perceived_domain_members(s, members, {per})
    check(kept == {per, mid, unp, other},
          "documented: equal-strength chain floods PERCEIVED through the whole component "
          "(single-link chaining; nothing is pruned without a strict cohesion valley)")


def test_T12c_ADJUDICATION_unnamed_domain_survives_when_bridge_ge_cohesion():
    section("T12c C1 ADJUDICATION (decisive): a GENUINELY unnamed, multi-node community is "
            "NOT pruned when its bridge to the perceived region is >= its internal cohesion. "
            "This proves the watershed prunes by COHESION VALLEY (weakness), not by pure "
            "domain MEMBERSHIP. Reported as a generalization characterization, not a §6.1 "
            "FAIL (the locked §6.1 case has bridge < cohesion).")
    # Build the over-swallow shape but with the bridge EQUAL to the unnamed domain's internal
    # ties. A pure-membership C1 ("prune any domain no source named") would prune the unnamed
    # community regardless. A cohesion-valley rule keeps it because there is no valley.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    # named domain: tea cup (tight n=30 so it wins the competition / is the basin core)
    tea = s.add_node("tea", NodeType.ENTITY)
    cup = s.add_node("cup", NodeType.ENTITY)
    _worn(s, tea, cup, n=30)
    # unnamed community: gizmo widget (internal n=12) bridged from tea with n=12 (EQUAL)
    gizmo = s.add_node("gizmo", NodeType.CONCEPT)
    widget = s.add_node("widget", NodeType.CONCEPT)
    _worn(s, gizmo, widget, n=12)     # internal cohesion
    _worn(s, tea, gizmo, n=12)        # bridge EQUAL to internal cohesion
    # direct watershed probe on the full member set (the field would reach all four)
    members = [tea, cup, gizmo, widget]
    kept = _perceived_domain_members(s, members, {tea, cup})
    b = _strongest_road_strength(s, gizmo, tea)        # bridge
    ic = _strongest_road_strength(s, gizmo, widget)    # internal cohesion
    print(f"      probe: gizmo bridge->perceived={round(b,4)}  internal->unperceived={round(ic,4)}")
    # gizmo's pull to perceived (tea) >= its pull to unperceived (widget) -> adopts PERCEIVED;
    # then widget chains in. The unnamed community SURVIVES.
    check(gizmo in kept and widget in kept,
          "DOCUMENTED GENERALIZATION GAP: a genuinely UNNAMED community survives when its "
          "bridge >= its internal cohesion (the watershed is a cohesion-valley/relative-"
          "weakness rule in disguise, NOT pure C1 membership). This is the objective "
          "evidence for the C1 verdict; it is not a §6.1 failure because the locked case "
          "has bridge(n=8) < cohesion(n=30).")


def test_T12d_ADJUDICATION_membership_C1_would_prune_but_watershed_does_not():
    section("T12d C1 ADJUDICATION (contrast): on the SAME graph a true membership-C1 "
            "(prune iff the node's 1c-group/basin contains no perceived source) WOULD prune "
            "the unnamed gizmo/widget community — the watershed does NOT. The two rules "
            "diverge, so the watershed is not a faithful realization of C1-as-written.")
    # We compute what a literal membership-C1 would do (basin membership = which perceived
    # source dominates each node) and compare to the watershed. They must DIVERGE here.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    tea = s.add_node("tea", NodeType.ENTITY)
    cup = s.add_node("cup", NodeType.ENTITY)
    _worn(s, tea, cup, n=30)
    gizmo = s.add_node("gizmo", NodeType.CONCEPT)
    widget = s.add_node("widget", NodeType.CONCEPT)
    _worn(s, gizmo, widget, n=12)
    _worn(s, tea, gizmo, n=12)
    # Loop-closed: name only the tea domain.
    r = think(s, "tea cup")
    perceived = set(r.perception.sources)
    check({tea, cup} <= perceived, "precondition: tea/cup perceived, gizmo/widget not")
    raw = set(r.workspace.raw_winner.members) if r.workspace.raw_winner else set()
    winner = set(r.thought.members) if r.thought else set()
    print(f"      raw winner: {_contents(s, raw)}  winner: {_contents(s, winner)}  "
          f"pruned: {_contents(s, r.workspace.pruned_members)}")
    # Whatever the field does, document the watershed outcome objectively. If gizmo/widget are
    # in the raw winner, a literal membership-C1 would prune them (no perceived source in their
    # community); the watershed's behavior (keep, due to bridge>=cohesion) is the divergence.
    if {gizmo, widget} & raw:
        watershed_kept_unnamed = bool({gizmo, widget} & winner)
        check(watershed_kept_unnamed,
              "the watershed KEEPS the unnamed community here, where a literal membership-C1 "
              "would PRUNE it — concrete evidence the watershed != C1-as-written")
    else:
        # If the competition/field kept them out of the raw winner anyway, the divergence is
        # not observable through this path; still record the direct-helper finding from T12c.
        check(True, "(unnamed community not in raw winner via this field; see T12c direct "
                    "helper probe for the divergence evidence)")


def test_T12e_gap_is_always_safe_direction_never_overprunes_perceived():
    section("T12e the C1 gap is in the SAFE direction: the watershed errs toward KEEPING "
            "(over-inclusion), so it can never over-PRUNE a perceived member. We hammer the "
            "anti-overcorrection guarantee in the adversarial bridge>=cohesion regime.")
    # The gap found in T12c/T12d is over-INCLUSION (keep an unnamed domain). The dangerous
    # direction would be over-EXCLUSION (prune a PERCEIVED member). We construct many random
    # graphs where perceived nodes sit at every awkward position and assert NO perceived
    # member is EVER pruned by the helper — across tie/asymmetric/valley topologies.
    import random
    rng = random.Random(424242)
    ever_overpruned = False
    worst = None
    for trial in range(60):
        s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
        ids = [s.add_node(f"t{trial}_n{i}", NodeType.CONCEPT) for i in range(8)]
        # random edges with random strengths (1..30 traversals)
        for _ in range(rng.randint(6, 14)):
            a = rng.choice(ids); b = rng.choice(ids)
            if a != b:
                _worn(s, a, b, n=rng.randint(1, 30))
        # random perceived subset (at least one)
        k = rng.randint(1, 4)
        perceived = set(rng.sample(ids, k))
        kept = _perceived_domain_members(s, ids, perceived)
        # CORE ANTI-OVERCORRECTION INVARIANT: every perceived member is kept (never pruned).
        if not (perceived <= kept):
            ever_overpruned = True
            worst = (trial, sorted(perceived - kept))
            break
    check(not ever_overpruned,
          f"NO perceived member is ever pruned across 60 random adversarial graphs "
          f"(over-correction would be a real FAIL; worst={worst})")


def test_T12f_locked_acceptance_graphs_have_bridge_below_cohesion():
    section("T12f scope confirmation: BOTH locked §6.1 acceptance graphs (coffee/work and "
            "the tea/project relabel) have bridge(n=8) STRICTLY below internal cohesion "
            "(n=30) — so the cohesion-valley watershed correctly prunes them. The §6.1 "
            "criterion is met; the T12c gap lies OUTSIDE the locked acceptance scope.")
    # _small_mind: work's bridge to perceived (n=8) vs internal (n=30).
    s, n = _small_mind()
    bridge = _strongest_road_strength(s, n["work"], n["coffee"])
    internal = max(_strongest_road_strength(s, n["work"], n["desk"]),
                   _strongest_road_strength(s, n["work"], n["code"]))
    check(bridge < internal,
          f"_small_mind: work bridge {round(bridge,4)} < internal cohesion {round(internal,4)} "
          f"(a genuine valley -> correctly pruned)")
    # the relabel graph used by the builder's generalization test (tea/project) — same shape.
    s2 = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    job = s2.add_node("project", NodeType.CONCEPT)
    table = s2.add_node("table surface", NodeType.ENTITY)
    due = s2.add_node("due date", NodeType.CONCEPT)
    prog = s2.add_node("programming task", NodeType.CONCEPT)
    tea = s2.add_node("tea", NodeType.ENTITY)
    galley = s2.add_node("galley", NodeType.ENTITY)
    dawn = s2.add_node("dawn ritual", NodeType.CONCEPT)
    _worn(s2, job, table); _worn(s2, job, due); _worn(s2, job, prog); _worn(s2, table, prog)
    _worn(s2, tea, galley); _worn(s2, tea, dawn)
    _worn(s2, tea, job, n=8)
    bridge2 = _strongest_road_strength(s2, job, tea)
    internal2 = max(_strongest_road_strength(s2, job, table),
                    _strongest_road_strength(s2, job, prog),
                    _strongest_road_strength(s2, job, due))
    check(bridge2 < internal2,
          f"relabel graph: project bridge {round(bridge2,4)} < internal cohesion "
          f"{round(internal2,4)} (a genuine valley -> correctly pruned)")


def test_T12b_node_with_no_road_to_perceived_never_adopts():
    section("T12 watershed floor: a member with NO road to ANY perceived member is never "
            "adopted (best_to_perceived must be > 0 to adopt) -> always pruned")
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    per = s.add_node("perr", NodeType.CONCEPT)
    island1 = s.add_node("isle one", NodeType.CONCEPT)
    island2 = s.add_node("isle two", NodeType.CONCEPT)
    _worn(s, island1, island2, n=30)   # an unnamed island with NO link to perceived
    # per is alone (no road to the island)
    members = [per, island1, island2]
    kept = _perceived_domain_members(s, members, {per})
    check(kept == {per},
          "only the perceived seed is kept; an island with no road to perceived is pruned")


# ─────────────────────────────────────────────────────────────────────────────
# T13 — the PRUNED winner is a well-formed Coalition (structural consistency)
# ─────────────────────────────────────────────────────────────────────────────

def test_T13_pruned_winner_is_internally_consistent():
    section("T13 structural: after pruning, the winner's members/_seq/strength/breakthrough "
            "marks are mutually consistent and representative() is deterministic")
    s, n = _small_mind()
    r = think(s, "coffee in the kitchen this morning")
    w = r.thought
    check(w is not None, "a pruned winner exists")
    check(set(w.members.keys()) == set(w._seq.keys()),
          "winner members and _seq keys match exactly after pruning (no uuid fallback)")
    check(abs(w.strength - sum(w.members.values())) < 1e-9,
          "winner strength == sum of surviving member activations (recomputed on prune)")
    check(set(w.breakthrough_members) <= set(w.members.keys()),
          "breakthrough marks reference only surviving members")
    rep1 = w.representative()
    rep2 = w.representative()
    check(rep1 == rep2 and rep1 in w.members,
          "representative() is deterministic and is a surviving member")
    raw = set(r.workspace.raw_winner.members)
    check(set(w.members.keys()).isdisjoint(set(r.workspace.pruned_members)),
          "surviving members and pruned_members are disjoint")
    check(set(w.members.keys()) | set(r.workspace.pruned_members) == raw,
          "surviving + pruned exactly partition the raw winner (nothing lost or invented)")


def test_T13b_ranked_is_pure_read_product_and_complete():
    section("T13b structural: workspace.ranked lists ALL candidate coalitions in competition "
            "order and is a pure-read product (raw_winner is ranked[0])")
    s, n = _small_mind()
    r = think(s, "coffee in the kitchen, writing code")  # multi-candidate
    ws = r.workspace
    check(len(ws.ranked) == len(r.coalitions),
          "ranked contains exactly as many coalitions as were formed")
    check(ws.raw_winner is ws.ranked[0],
          "the raw winner is the top of the ranked competition order")
    rr = rank_coalitions(r.coalitions)
    check([frozenset(c.members) for c in rr] == [frozenset(c.members) for c in ws.ranked],
          "ranked order matches an independent re-rank (competition is a pure function)")


def run_all():
    print("=" * 70)
    print("  TESTER — INDEPENDENT ADVERSARIAL SUITE for 1d-i (workspace selection)")
    print("=" * 70)
    for t in [
        # T1 over-swallow flip loop-closed + reality of the over-swallow
        test_T1_over_swallow_flips_loop_closed,
        test_T1b_over_swallow_is_real_preprune_not_vacuous,
        # T2 anti-overcorrection (incl. hostile attempts to over-prune)
        test_T2_anti_overcorrection_perceived_domain_survives_loop_closed,
        test_T2b_loosely_attached_perceived_node_survives,
        test_T2c_perceived_node_bridged_to_denser_unperceived_region_survives,
        # T3 generalization on NEW non-isomorphic graphs
        test_T3_generalize_multiple_bridges_into_unnamed_domain,
        test_T3b_generalize_three_domains_mixed_perceived,
        test_T3c_generalize_asymmetric_cohesion,
        # T4 boundary probes (decisive C1-vs-C2)
        test_T4_weak_cohesion_unperceived_region_still_pruned,
        test_T4b_decisive_C1_not_C2_strong_bridge_into_unnamed,
        # T5 threshold-free audit
        test_T5_pruning_is_invariant_to_min_size_guard,
        test_T5b_no_numeric_threshold_constant_in_pruning_source,
        # T6 cross-process determinism (6 seeds, our probe)
        test_T6_determinism_winner_pruned_ranked_6_seeds,
        test_T6b_determinism_multi_basin_ties_6_seeds,
        # T7 purity (zero mutation)
        test_T7_select_winner_is_pure_read_deep_snapshot,
        test_T7b_think_broadcast_false_pure_on_adversarial_graph,
        test_T7c_broadcast_true_now_performs_exactly_one_write_reowned,
        # T8 integrity mutation battery
        test_T8_mutation_battery_integrity_and_purity,
        # T9 hostile topologies + competition
        test_T9_empty_coalitions,
        test_T9b_empty_utterance_loop_closed,
        test_T9c_singleton_coalition_winner,
        test_T9d_density_competition_discriminates_unit,
        test_T9e_duplicate_edges_and_cycles_do_not_break_competition,
        test_T9f_high_degree_fan_winner,
        test_T9g_watershed_helper_separates_communities_unit,
        test_T9h_watershed_order_independence_permuted_member_lists,
        # T10 scale-invariance
        test_T10_selection_scale_invariant_isolated,
        test_T10b_pruning_scale_invariant_in_road_strength_structure,
        # T11 P9 re-derivation (re-owned)
        test_T11_P9_reowned_over_swallow_residual_is_gone,
        test_T11b_P9_flip_depends_on_what_was_named_counterfactual,
        # T12 watershed chaining + C1 adjudication (decisive evidence)
        test_T12_watershed_chaining_floods_perceived_through_equal_strength_ties,
        test_T12b_node_with_no_road_to_perceived_never_adopts,
        test_T12c_ADJUDICATION_unnamed_domain_survives_when_bridge_ge_cohesion,
        test_T12d_ADJUDICATION_membership_C1_would_prune_but_watershed_does_not,
        test_T12e_gap_is_always_safe_direction_never_overprunes_perceived,
        test_T12f_locked_acceptance_graphs_have_bridge_below_cohesion,
        # T13 pruned-winner structural consistency
        test_T13_pruned_winner_is_internally_consistent,
        test_T13b_ranked_is_pure_read_product_and_complete,
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
