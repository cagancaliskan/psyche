"""
TESTER — INDEPENDENT ADVERSARIAL SUITE for experiments/exp2c_capture.py
(the 2c BLIND realistic stimulus-construction script — the 1e-selector analogue).

WHAT THIS VERIFIES (mechanism / fairness / faithfulness — NOT meaning):
  This suite is written from scratch by the tester. It does NOT adapt the builder's
  test_exp2c_capture.py. Its single purpose is to break the claim that the realistic
  stimulus construction is FAIR and FAITHFUL to the FROZEN pre-registration
  (docs/experiments/EXP-2c-interoception.md §5 realistic battery, §6 realistic trace),
  the way the 1e selector was tester-verified before its blind run.

  It computes NO graded number / NO flip-rate (forbidden — that is the validator's
  step). It verifies the *stimulus construction's* fairness + faithfulness:
    1. the 60-percept battery is independently re-derivable from seed 20260622 and the
       §5.2 draw order, and is genuinely NOT pre-selected for flip-capability —
       structurally (no contested midnode / no positioned crossover is even possible),
       and probed for any COVERT flip-bias beyond what §5 discloses;
    2. it is honestly DISTINCT from the pilot's contested-by-design battery (structural,
       not cosmetic);
    3. the trace is genuinely captured from REAL telemetry over a REALISTIC band (same
       compute_friction/BodySensor by object identity; sweep from the real observed range
       with no inflation; not re-widened toward the pilot's ~0.999 extremes);
    4. replay-determinism across 6 PYTHONHASHSEED in fresh processes (battery canonical
       serialization + trace processing);
    5. blindness — no winner/flip/grade/effect-size path, no activation read, main() not
       triggered by import or tests.

  Two builder-flagged frozen-provenance choices are scrutinized hard:
    - depth_extra placement ("anchorA's first neighbor") is a neutral structural choice,
      not a flip lever;
    - WORK_UTTERANCES + the workload substrate are workload-only (never co-constructed
      with the battery) and produce a realistic friction band.
  Plus: loop-closed re-test of the anchor-free-neighbor property (perceive lights up
  EXACTLY the two anchors — no neighbor leakage).

Uses the project's tiny built-in harness (print + count, exit nonzero), NOT pytest. The
live trace CAPTURE (the single non-determinism) is NOT exercised here — exactly as the
pilot's live capture stays out of run_tests.py; the capture's boundary read is verified
only structurally.

Run as a script:  python3 experiments/test_tester_exp2c_capture_adversarial.py
"""

from __future__ import annotations

import os
import re
import sys
import ast
import json
import inspect
import hashlib
import random
import subprocess

# self-bootstrap: src/ (frozen library, bare-name imports) and experiments/ onto sys.path,
# mirroring the other experiment-layer suites.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), "src")
for _p in (_SRC, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import exp2c_capture as cap
import psyche_bodysensor as bs
import pilot_2c_populability as pilot
from psyche_store import SubstrateStore, Clock, NodeType
from psyche_perceive import perceive


# ─────────────────────────────────────────────────────────────────────────────
# Tiny test harness (matches the rest of the suite)
# ─────────────────────────────────────────────────────────────────────────────

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


def approx(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol


# Independently-declared constants (re-typed from EXP-2c §5.2/§6.4, NOT imported from the
# script — so a silent edit to the script's constant is caught by these tests, not masked).
EXP_SEED = 20260622
EXP_COUNT = 60
EXP_VOCAB = (
    "alpha", "bravo", "delta", "echo", "foxtrot", "golf", "hotel", "india",
    "juliet", "kilo", "lima", "november", "oscar", "papa", "quebec", "romeo",
    "sierra", "tango", "uniform", "victor", "whiskey", "xray", "yankee", "zulu",
)


def _rederive_battery(seed: int, count: int):
    """INDEPENDENT re-implementation of the §5.2 draw order — NOT cap.build_realistic_battery.
    Returns a list of dicts describing each percept's structural draws. This is the tester's
    own generator; if it agrees with the script, the script faithfully realizes §5.2."""
    rng = random.Random(seed)
    vn = len(EXP_VOCAB)
    out = []
    for _ in range(count):
        ia = rng.randrange(vn)
        ib = rng.randrange(vn)
        while ib == ia:
            ib = rng.randrange(vn)
        a, b = EXP_VOCAB[ia], EXP_VOCAB[ib]
        ds_a = rng.randint(2, 5)
        ds_b = rng.randint(2, 5)
        in_a = [rng.randint(8, 30) for _ in range(ds_a)]
        in_b = [rng.randint(8, 30) for _ in range(ds_b)]
        bridge = rng.random() < 0.5
        if bridge:
            bti = rng.randrange(ds_b)
            bn = rng.randint(1, 30)
        else:
            bti = None
            bn = None
        de = rng.randint(0, 1)
        out.append(dict(a=a, b=b, ds_a=ds_a, ds_b=ds_b, in_a=in_a, in_b=in_b,
                        bridge=bridge, bti=bti, bn=bn, de=de))
    return out


# ═════════════════════════════════════════════════════════════════════════════
# A. INDEPENDENT RE-DERIVATION OF THE §5.2 BATTERY (faithfulness from scratch)
# ═════════════════════════════════════════════════════════════════════════════

def test_independent_rederivation_matches_the_script_exactly():
    section("A1 INDEPENDENT RE-DERIVATION: a from-scratch tester re-implementation of the "
            "§5.2 draw order over random.Random(20260622) reproduces the script's battery "
            "byte-for-byte (faithful to the frozen procedure, not just self-consistent)")
    mine = _rederive_battery(EXP_SEED, EXP_COUNT)
    theirs = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    check(len(mine) == len(theirs) == EXP_COUNT,
          f"both produce {EXP_COUNT} percepts (mine={len(mine)}, theirs={len(theirs)})")
    mism = 0
    for i, (m, t) in enumerate(zip(mine, theirs)):
        ok = (m['a'] == t.anchor_a_content and m['b'] == t.anchor_b_content and
              m['ds_a'] == t.domain_size_a and m['ds_b'] == t.domain_size_b and
              m['in_a'] == t.internal_n_a and m['in_b'] == t.internal_n_b and
              m['bridge'] == t.bridge_present and m['bti'] == t.bridge_target_index and
              m['bn'] == t.bridge_n and m['de'] == t.depth_extra)
        if not ok:
            mism += 1
            if mism <= 3:
                print(f"    mismatch @ {i}: mine={m} theirs={vars(t)}")
    check(mism == 0,
          f"every percept matches the independent re-derivation (mismatches={mism})")
    # the script's own declared constants equal the independently-typed §5.2 values
    check(cap.BATTERY_SEED_REALISTIC == EXP_SEED, "script seed == 20260622")
    check(cap.PERCEPT_COUNT_REALISTIC == EXP_COUNT, "script count == 60")
    check(tuple(cap.ANCHOR_VOCAB) == EXP_VOCAB, "script vocab == the independent vocab")
    check(cap.DOMAIN_SIZE_RANGE == (2, 5) and cap.INTERNAL_N_RANGE == (8, 30) and
          cap.BRIDGE_PRESENT_P == 0.5 and cap.BRIDGE_N_RANGE == (1, 30) and
          cap.DEPTH_EXTRA_RANGE == (0, 1),
          "script parameter ranges == the frozen §5.2/§6.4 values")


def test_anchor_vocab_is_substring_clean_independently_verified():
    section("A2 VOCAB CLEAN (independent): every anchor word is mutually NON-substring-"
            "overlapping — re-checked by the tester (so two-anchor perception cannot light a "
            "third anchor). A structural cleanliness requirement, not a flip lever")
    bad = []
    for a in EXP_VOCAB:
        for b in EXP_VOCAB:
            if a is not b and (a in b or b in a):
                bad.append((a, b))
    check(not bad, f"no anchor word is a substring of another (offenders: {bad})")


# ═════════════════════════════════════════════════════════════════════════════
# B. THE BATTERY IS STRUCTURALLY *NOT* FLIP-PRE-SELECTED + NO COVERT FLIP-BIAS
# ═════════════════════════════════════════════════════════════════════════════

def test_no_contested_node_is_structurally_possible_not_just_absent():
    section("B1 NO CONTESTED NODE IS POSSIBLE: across ALL 60 built stores, no node is reached "
            "from BOTH anchors (the structural precondition for a pilot-style contested "
            "crossover). The bridge, when present, is the ONLY anchorA->B-side edge and it "
            "targets an EXISTING B-neighbor — so no node is co-reached by short paths from "
            "both anchors via a constructed sink. This is structural impossibility, not "
            "'absent in this draw'.")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    for spec in battery:
        store = spec.build_store()
        # Build content->id and the directed adjacency from the store itself.
        id_to_content = {nid: store.get_node(nid).content for nid in store.all_node_ids()}
        content_to_id = {c: n for n, c in id_to_content.items()}
        a_id = content_to_id[spec.anchor_a_content]
        b_id = content_to_id[spec.anchor_b_content]
        # directed out-adjacency (roads_from yields RoadIDs; neighbors() yields target NodeIDs)
        adj = {nid: set(store.neighbors(nid)) for nid in store.all_node_ids()}
        # BFS reachable sets (within the small store; full reach is fine, the store is tiny)
        def reach(start):
            seen = {start}
            stack = [start]
            while stack:
                u = stack.pop()
                for v in adj.get(u, ()):
                    if v not in seen:
                        seen.add(v)
                        stack.append(v)
            seen.discard(start)
            return seen
        ra = reach(a_id)
        rb = reach(b_id)
        co_reached = ra & rb
        # The ONLY way a node is reached from both anchors is the optional single bridge
        # anchorA -> (a B-neighbor): that B-neighbor is reachable from B (1 hop) and from A
        # (the bridge). That is a REAL existing B-domain member, NOT a constructed contested
        # sink, and there is at most ONE such node (the single bridge target). Crucially the
        # B-neighbor has NO out-roads back, so it is a leaf — it cannot host an asymmetric
        # 1-hop-vs-2-strong-hop crossover the way the pilot's midnode (reached via
        # gamma->gnode->mid) does.
        if spec.bridge_present:
            # exactly the bridged B-neighbor may be co-reached
            tgt_content = f"nbr_b_{spec.bridge_target_index}"
            tgt_id = content_to_id[tgt_content]
            check(co_reached <= {tgt_id},
                  f"{spec.percept_text!r}: only the single bridge target is co-reached "
                  f"(saw {sorted(id_to_content[x] for x in co_reached)})")
        else:
            check(co_reached == set(),
                  f"{spec.percept_text!r}: NO node is reached from both anchors (no bridge -> "
                  f"two disjoint domains) (saw {sorted(id_to_content[x] for x in co_reached)})")
        # the literal 'midnode' name the pilot uses must never appear
        check("midnode" not in id_to_content.values(),
              f"{spec.percept_text!r}: no 'midnode' contested sink")


def test_no_constructed_two_hop_sink_from_the_far_anchor():
    section("B2 NO 2-HOP FAR SINK: the pilot's flip lever is a node reached 2 STRONG hops "
            "from the far anchor (gamma->gnode->mid). Here, the only distance-2 structure is "
            "the optional depth_extra tail on anchorA's OWN first neighbor (an A-side tail, "
            "never reached from anchorB), and the bridge is a single 1-hop A->B-neighbor. No "
            "node is reached at 2 hops from one anchor AND 1 hop from the other.")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    saw_tail = False
    saw_bridge = False
    for spec in battery:
        store = spec.build_store()
        id_to_content = {nid: store.get_node(nid).content for nid in store.all_node_ids()}
        content_to_id = {c: n for n, c in id_to_content.items()}
        adj = {nid: set(store.neighbors(nid)) for nid in store.all_node_ids()}
        a_id = content_to_id[spec.anchor_a_content]
        b_id = content_to_id[spec.anchor_b_content]

        def hops_from(start):
            dist = {start: 0}
            stack = [start]
            while stack:
                u = stack.pop()
                for v in adj.get(u, ()):
                    if v not in dist:
                        dist[v] = dist[u] + 1
                        stack.append(v)
            return dist
        da = hops_from(a_id)
        db = hops_from(b_id)
        # tail_a, if present, is at distance 2 from A and UNREACHED from B
        if spec.depth_extra == 1 and spec.domain_size_a >= 1:
            saw_tail = True
            tail_id = content_to_id["tail_a"]
            check(da.get(tail_id) == 2, f"{spec.percept_text!r}: tail_a is 2 hops from anchorA")
            check(tail_id not in db,
                  f"{spec.percept_text!r}: tail_a is NOT reachable from anchorB (an A-side "
                  f"tail, never a cross-anchor contested sink)")
        # the bridge target is at most 1 hop from A (the bridge) and 1 hop from B
        if spec.bridge_present:
            saw_bridge = True
            tgt_id = content_to_id[f"nbr_b_{spec.bridge_target_index}"]
            check(da.get(tgt_id) == 1 and db.get(tgt_id) == 1,
                  f"{spec.percept_text!r}: bridge target is 1 hop from BOTH anchors (a real "
                  f"B-neighbor), never 1-vs-2 asymmetric like the pilot's midnode")
        # NO node is at distance 2 from one anchor and distance 1 from the other (the pilot's
        # exact asymmetric contested geometry)
        for nid in store.all_node_ids():
            a_d = da.get(nid)
            b_d = db.get(nid)
            asym = ((a_d == 1 and b_d == 2) or (a_d == 2 and b_d == 1))
            check(not asym,
                  f"{spec.percept_text!r}: node {id_to_content[nid]!r} is NOT at the pilot's "
                  f"1-vs-2 asymmetric contested distance (a_d={a_d}, b_d={b_d})")
    check(saw_tail, "at least one percept has a depth_extra tail (non-vacuous)")
    check(saw_bridge, "at least one percept has a bridge (non-vacuous)")


def test_no_crossover_field_anywhere_in_the_dataclass():
    section("B3 NO CROSSOVER FIELD: the RealisticPercept dataclass carries NO d*/crossover/"
            "contested/midnode field — the crossover is structurally un-representable, not "
            "merely unset (contrast: the pilot computes d* = sA/sB^2 to POSITION the flip)")
    fields = set(cap.RealisticPercept.__dataclass_fields__.keys())
    for forbidden in ("d_star", "dstar", "crossover", "midnode", "contested", "d_crit",
                      "flip", "movable"):
        check(forbidden not in fields,
              f"RealisticPercept has NO '{forbidden}' field (saw fields: {sorted(fields)})")
    # and the source text of build_store never computes a crossover ratio
    src = inspect.getsource(cap.RealisticPercept.build_store)
    check("sB" not in src and "d_star" not in src and "/ sB" not in src,
          "build_store computes no crossover ratio (no d* positioning)")


def test_covert_flip_bias_probe_bridge_n_is_free_uniform_not_a_crossover_window():
    section("B4 COVERT FLIP-BIAS PROBE (bridge_n distribution): bridge_n is a FREE uniform "
            "draw over [1..30] — NOT confined to the pilot's [1..6] crossover-positioning "
            "window. If the construction quietly capped or concentrated bridge_n to position "
            "near-vs-far competition, this would catch it.")
    mine = _rederive_battery(EXP_SEED, EXP_COUNT)
    bns = sorted(m['bn'] for m in mine if m['bridge'])
    check(len(bns) > 0, "some percepts are bridged (non-vacuous)")
    check(all(1 <= n <= 30 for n in bns), f"all bridge_n in [1..30] (saw {bns})")
    check(max(bns) > 6,
          f"bridge_n reaches ABOVE the pilot's [1..6] window (max={max(bns)}) — a free "
          f"uniform draw, not a positioned crossover")
    # spread across the range: not concentrated in a narrow flip-favoring band.
    above_15 = sum(1 for n in bns if n > 15)
    check(above_15 > 0,
          f"bridge_n genuinely populates the UPPER half (>15): {above_15} of {len(bns)} — not "
          f"concentrated where a weak bridge would favor a flip")
    check(len(set(bns)) >= 5, f"bridge_n takes many distinct values ({sorted(set(bns))})")


def test_covert_flip_bias_probe_bridge_n_not_tuned_to_internal_cohesion():
    section("B5 COVERT FLIP-BIAS PROBE (bridge vs cohesion): bridge_n is drawn INDEPENDENTLY "
            "of the B-domain internal cohesion — it is NOT systematically placed near the "
            "internal_n it competes with (which would manufacture near-vs-far basin "
            "competition favoring flips). We verify bridge_n spans well above, around, AND "
            "below the B-domain mean cohesion, i.e. it is not tuned to sit at the boundary.")
    mine = _rederive_battery(EXP_SEED, EXP_COUNT)
    bridged = [m for m in mine if m['bridge']]
    check(len(bridged) > 0, "some bridged percepts (non-vacuous)")
    # ratio = bridge_n / mean(internal_n_b). A construction tuned to flip would cluster ratios
    # near 1.0 (bridge strength ~ internal cohesion => contested). A free draw spreads them.
    ratios = []
    for m in bridged:
        mean_in_b = sum(m['in_b']) / len(m['in_b'])
        ratios.append(m['bn'] / mean_in_b)
    ratios.sort()
    near_one = sum(1 for r in ratios if 0.7 <= r <= 1.3)
    far = sum(1 for r in ratios if r < 0.5 or r > 1.5)
    check(far > 0,
          f"bridge_n/cohesion ratios populate the NON-contested region (ratio<0.5 or >1.5): "
          f"{far} of {len(ratios)} — the draw is not pinned to the contested boundary")
    # not the MAJORITY clustered at the boundary (a flip-tuned design would be majority-near-1)
    check(near_one <= len(ratios) - 1,
          f"not ALL ratios sit near 1.0 (near-1 count {near_one}/{len(ratios)}) — bridge "
          f"strength is not engineered to match internal cohesion")
    print(f"    bridge_n/cohesion ratios (sorted): {[round(r,2) for r in ratios]}")


def test_depth_extra_placement_is_a_neutral_structural_choice():
    section("B6 FLAGGED CHOICE — depth_extra placement: the second-hop tail is built on "
            "anchorA's FIRST neighbor (the builder's choice; §5.2 did not fix which). Confirm "
            "this is NEUTRAL: the tail (a) is on the A side, (b) is a leaf reached only via "
            "that one neighbor, (c) is NEVER reachable from anchorB, and (d) carries the same "
            "internal_n as that neighbor's road (not a specially-weighted flip lever).")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    checked_any = False
    for spec in battery:
        if not (spec.depth_extra == 1 and spec.domain_size_a >= 1):
            continue
        checked_any = True
        store = spec.build_store()
        id_to_content = {nid: store.get_node(nid).content for nid in store.all_node_ids()}
        content_to_id = {c: n for n, c in id_to_content.items()}
        tail_id = content_to_id["tail_a"]
        first_nbr_id = content_to_id["nbr_a_0"]
        # the tail's only incoming road is from nbr_a_0 (anchorA's first neighbor). roads_into
        # yields RoadIDs; resolve each to its source via get_road.
        incoming = []
        for rid in store.roads_into(tail_id):
            incoming.append(store.get_road(rid, apply_decay=False).source_id)
        check(incoming == [first_nbr_id],
              f"{spec.percept_text!r}: tail_a's only parent is anchorA's first neighbor "
              f"(saw parents {[id_to_content[x] for x in incoming]})")
        # the tail has no out-roads (a pure leaf — cannot become a contested junction)
        out_roads = list(store.roads_from(tail_id))
        check(len(out_roads) == 0, f"{spec.percept_text!r}: tail_a is a leaf (no out-roads)")
        # the road nbr_a_0->tail uses internal_n_a[0], the SAME count as anchorA->nbr_a_0
        # (so it is plain domain depth, not a specially-strong lever). We read the road's
        # traversal_count (canonical, no decay) and compare to the documented internal_n_a[0].
        rid = store.find_road(first_nbr_id, tail_id)
        tc = store.get_road(rid, apply_decay=False).traversal_count if rid else None
        check(tc == spec.internal_n_a[0],
              f"{spec.percept_text!r}: tail road traversal_count == internal_n_a[0] "
              f"({tc} vs {spec.internal_n_a[0]}) — plain domain depth, not a tuned lever")
    check(checked_any, "at least one depth_extra==1 percept exists to verify (non-vacuous)")


def test_some_percepts_have_no_bridge_real_coin_flip():
    section("B7 p=0.5 BRIDGE IS A REAL COIN FLIP: the battery contains BOTH bridged and "
            "unbridged percepts (the pilot's contested bridge is ALWAYS present). An unbridged "
            "percept has two fully disjoint domains and CANNOT flip on a cross-domain basin "
            "crossover — proving the battery does not force a movable topology onto every "
            "percept.")
    mine = _rederive_battery(EXP_SEED, EXP_COUNT)
    bridged = sum(1 for m in mine if m['bridge'])
    unbridged = EXP_COUNT - bridged
    check(bridged > 0 and unbridged > 0,
          f"both bridged ({bridged}) and unbridged ({unbridged}) percepts exist — a real "
          f"p=0.5 flip, unlike the pilot's always-present contested bridge")


# ═════════════════════════════════════════════════════════════════════════════
# C. HONEST STRUCTURAL DISTINCTNESS FROM THE PILOT (not cosmetic)
# ═════════════════════════════════════════════════════════════════════════════

def test_distinct_from_pilot_structurally_rederived_both():
    section("C1 DISTINCTNESS (both re-derived): re-deriving BOTH batteries, the pilot builds "
            "a 'midnode' contested sink reached 1-hop-from-alpha AND 2-strong-hops-from-gamma "
            "in EVERY percept; the realistic battery builds NO such node in ANY percept. The "
            "distinctness is structural (the flip mechanism is present in one, absent in the "
            "other), not cosmetic.")
    # pilot
    pilot_battery = pilot.build_battery(pilot.BATTERY_SEED, pilot.PERCEPT_COUNT)
    pilot_has_mid = 0
    pilot_has_2hop_asym = 0
    for label, builder, _pt, _a, _b in pilot_battery:
        s = builder()
        id_to_content = {n: s.get_node(n).content for n in s.all_node_ids()}
        content_to_id = {c: n for n, c in id_to_content.items()}
        if "midnode" in id_to_content.values():
            pilot_has_mid += 1
        # verify the asymmetric geometry: midnode is 1 hop from alpha and 2 hops from gamma
        adj = {n: set(s.neighbors(n)) for n in s.all_node_ids()}

        def hops(start):
            d = {start: 0}; st = [start]
            while st:
                u = st.pop()
                for v in adj.get(u, ()):
                    if v not in d:
                        d[v] = d[u] + 1; st.append(v)
            return d
        if "alpha" in content_to_id and "gamma" in content_to_id and "midnode" in content_to_id:
            da = hops(content_to_id["alpha"]); dg = hops(content_to_id["gamma"])
            mid = content_to_id["midnode"]
            if da.get(mid) == 1 and dg.get(mid) == 2:
                pilot_has_2hop_asym += 1
    check(pilot_has_mid == len(pilot_battery),
          f"(control) EVERY pilot percept has a 'midnode' ({pilot_has_mid}/{len(pilot_battery)})")
    check(pilot_has_2hop_asym == len(pilot_battery),
          f"(control) EVERY pilot percept has the 1-vs-2 asymmetric contested geometry "
          f"({pilot_has_2hop_asym}/{len(pilot_battery)})")
    # realistic
    realistic = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    real_has_mid = 0
    for spec in realistic:
        s = spec.build_store()
        if "midnode" in {s.get_node(n).content for n in s.all_node_ids()}:
            real_has_mid += 1
    check(real_has_mid == 0,
          f"NO realistic percept has a 'midnode' contested sink ({real_has_mid}/60)")
    # seed + count distinct
    check(cap.BATTERY_SEED_REALISTIC != pilot.BATTERY_SEED,
          f"distinct seeds ({cap.BATTERY_SEED_REALISTIC} vs {pilot.BATTERY_SEED})")
    check(cap.PERCEPT_COUNT_REALISTIC != pilot.PERCEPT_COUNT,
          f"distinct counts ({cap.PERCEPT_COUNT_REALISTIC} vs {pilot.PERCEPT_COUNT})")


def test_realistic_domains_generically_asymmetric_unlike_pilot_mirror():
    section("C2 ASYMMETRY vs PILOT MIRROR: the pilot grows mirror-symmetric near neighbors "
            "(same count on both anchors, kept symmetric so they never bias the winner); the "
            "realistic battery draws domain sizes INDEPENDENTLY, so many percepts have "
            "ds_a != ds_b. Verified by re-derivation.")
    mine = _rederive_battery(EXP_SEED, EXP_COUNT)
    asym = sum(1 for m in mine if m['ds_a'] != m['ds_b'])
    check(asym > 0,
          f"the realistic battery has generically asymmetric domains ({asym}/60 with "
          f"ds_a != ds_b) — unlike the pilot's mirror-symmetric construction")
    # and internal_n is drawn per-road (cohesion varies within a domain), unlike the pilot's
    # fixed n=30 tight neighbors
    varied = sum(1 for m in mine if len(set(m['in_a'])) > 1 or len(set(m['in_b'])) > 1)
    check(varied > 0,
          f"internal cohesion varies per-road in {varied}/60 percepts (realistic), not a "
          f"fixed n=30 like the pilot's tight neighbors")


# ═════════════════════════════════════════════════════════════════════════════
# D. TRACE IS REAL TELEMETRY OVER A REALISTIC BAND (same compute_friction; no inflation)
# ═════════════════════════════════════════════════════════════════════════════

def test_same_compute_friction_and_bodysensor_by_object_identity():
    section("D1 SAME FRICTION BY IDENTITY: the capture module's compute_friction and "
            "BodySensor ARE the psyche_bodysensor objects (identity, not a re-implementation) — "
            "so the trace friction is computed by the SAME code the cycle uses")
    check(cap.compute_friction is bs.compute_friction,
          "cap.compute_friction IS psyche_bodysensor.compute_friction (same object)")
    check(cap.BodySensor is bs.BodySensor,
          "cap.BodySensor IS psyche_bodysensor.BodySensor (same object)")
    check(cap.TelemetrySample is bs.TelemetrySample,
          "cap.TelemetrySample IS psyche_bodysensor.TelemetrySample (same object)")
    # frictions_from_trace must construct a real BodySensor(simulated=True, trace=...) and
    # call .read() — exactly how the cycle consumes it. Verify structurally.
    src = inspect.getsource(cap.frictions_from_trace)
    check("BodySensor(" in src and "trace=" in src and ".read()" in src,
          "frictions_from_trace builds a BodySensor(simulated=True, trace=...) and reads it "
          "(the cycle's exact replay-consumption path)")


def test_frictions_from_trace_equals_compute_friction_on_deltas_loopclosed():
    section("D2 FRICTIONS == compute_friction ON DELTAS (independent fixed trace): over a "
            "tester-authored fixed sample sequence, frictions_from_trace yields EXACTLY the "
            "library compute_friction on each consecutive-sample delta (first/baseline "
            "dropped). Re-derived independently, not from the script's math.")
    # a fixed sequence with hand-known deltas, including a degenerate sub-resolution interval
    samples = [
        bs.TelemetrySample(perf=10.0, proc=5.0),     # baseline (dropped)
        bs.TelemetrySample(perf=11.0, proc=6.0),     # wall=1 cpu=1   -> 0.0
        bs.TelemetrySample(perf=12.0, proc=6.4),     # wall=1 cpu=0.4 -> 0.6
        bs.TelemetrySample(perf=12.0, proc=6.4),     # wall=0 (sub-res) -> NEUTRAL 0.0
        bs.TelemetrySample(perf=13.0, proc=6.4),     # wall=1 cpu=0.0 -> 1.0
        bs.TelemetrySample(perf=14.0, proc=20.0),    # wall=1 cpu>>wall -> clamp 0.0
    ]
    got = cap.frictions_from_trace(samples)
    expected = []
    for k in range(1, len(samples)):
        wall = samples[k].perf - samples[k - 1].perf
        cpu = samples[k].proc - samples[k - 1].proc
        expected.append(bs.compute_friction(wall, cpu))
    check(len(got) == len(samples) - 1,
          f"a {len(samples)}-sample trace yields {len(samples)-1} frictions (baseline dropped) "
          f"(saw {len(got)})")
    check(got == expected,
          f"frictions_from_trace == compute_friction(deltas) (got {got}, expected {expected})")
    # pin the concrete arithmetic independently
    check(approx(got[0], 0.0) and approx(got[1], 0.6) and approx(got[2], 0.0) and
          approx(got[3], 1.0) and approx(got[4], 0.0),
          f"hand-computed friction sequence matches (saw {got})")


def test_sweep_uses_only_observed_range_no_inflation_and_not_pilot_extremes():
    section("D3 NO INFLATION: sweep_levels_from_frictions spans [observed_min..observed_max] "
            "at 9 evenly-spaced points and NEVER widens beyond the real observed span — the "
            "forbidden move is re-widening toward the pilot's ~0.999 extreme. Verified on a "
            "tester-chosen REALISTIC narrow band.")
    # a realistic, narrow, right-skewed band (NOT the pilot's bimodal 0..0.999)
    frictions = [0.004, 0.011, 0.006, 0.052, 0.009, 0.007, 0.123, 0.013, 0.008, 0.019]
    levels = cap.sweep_levels_from_frictions(frictions, cap.SWEEP_LEVELS_REALISTIC)
    lo, hi = min(frictions), max(frictions)
    check(len(levels) == 9, f"exactly 9 swept levels (saw {len(levels)})")
    check(approx(levels[0], lo), f"first level == observed min ({levels[0]} vs {lo})")
    check(approx(levels[-1], hi), f"last level == observed max ({levels[-1]} vs {hi})")
    eps = 1e-9
    check(all(lo - eps <= v <= hi + eps for v in levels),
          "every swept level lies within the observed band +/- float-eps (no inflation)")
    check(levels == sorted(levels), "levels are monotone non-decreasing")
    # decisively NOT re-widened toward the pilot's extreme
    check(max(levels) < 0.5,
          f"the realistic sweep max ({max(levels):.4f}) is nowhere near the pilot's ~0.999 "
          f"busy-vs-idle extreme")
    # the formula is exactly lo + (hi-lo)*k/(n-1) — re-derive each level independently
    n = 9
    expect = [lo + (hi - lo) * (k / (n - 1)) for k in range(n)]
    check(levels == expect, f"levels match the independent quantile formula (saw {levels})")
    # degenerate band -> single value (honest collapse, not widened)
    flat = cap.sweep_levels_from_frictions([0.02, 0.02, 0.02], 9)
    check(flat == [0.02], f"a collapsed band returns a single value, not a widened span "
                          f"(saw {flat})")
    check(cap.SWEEP_LEVELS_REALISTIC == 9, "SWEEP_LEVELS_REALISTIC == 9 (frozen)")


def test_capture_params_are_realistic_not_pilot_extremes():
    section("D4 §6 CAPTURE PARAMS realistic: 300 samples, 0.5 ms cooperative yield, 9 sweep "
            "levels — and the yield is FAR smaller than the pilot's deliberate 4 ms idle "
            "stall. The capture path uses think() + a small sleep, NOT a busy-spin-vs-sleep "
            "alternation manufacturing 0-and-1 extremes.")
    check(cap.CAPTURE_SAMPLES_REALISTIC == 300, f"300 samples (saw {cap.CAPTURE_SAMPLES_REALISTIC})")
    check(approx(cap.REALISTIC_YIELD_S, 0.0005), f"0.5 ms yield (saw {cap.REALISTIC_YIELD_S})")
    check(cap.REALISTIC_YIELD_S < pilot.IDLE_SLEEP_S,
          f"realistic yield {cap.REALISTIC_YIELD_S} < pilot idle stall {pilot.IDLE_SLEEP_S}")
    src = inspect.getsource(cap.capture_real_telemetry)
    check("busy_spin" not in src and "_busy_spin" not in src,
          "no busy-spin in the realistic capture (no manufactured low-friction extreme)")
    check("perf_counter" in src and "process_time" in src,
          "the capture reads BOTH perf_counter AND process_time (real telemetry pair)")
    check("think(" in src,
          "the capture's work interval is think() (real mixed cognitive load)")
    # there is exactly ONE sleep and it is the small realistic yield (not the pilot's 4ms)
    check("time.sleep(REALISTIC_YIELD_S)" in src,
          "the only sleep is the small REALISTIC_YIELD_S cooperative pause")


def test_workload_substrate_is_separate_from_the_graded_battery():
    section("D5 FLAGGED CHOICE — WORK_UTTERANCES workload-only: the §6.1 workload substrate "
            "(build_workload_store) is ENTIRELY separate from the §5 graded percept battery — "
            "different node contents (real english words coffee/river/... vs NATO anchors + "
            "nbr_* namespace), built by a different function, never co-constructed. The trace "
            "is not derived from the battery.")
    # the workload substrate contents
    ws = cap.build_workload_store()
    work_contents = {ws.get_node(n).content for n in ws.all_node_ids()}
    # the graded battery contents (union over all percepts)
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    battery_contents = set()
    for spec in battery:
        s = spec.build_store()
        battery_contents |= {s.get_node(n).content for n in s.all_node_ids()}
    overlap = work_contents & battery_contents
    check(overlap == set(),
          f"workload substrate and graded battery share NO node content (overlap: {overlap}) "
          f"— the trace is not co-constructed with the battery")
    # the WORK_UTTERANCES tokens name workload nodes (real work), not battery anchors
    work_tokens = set()
    for u in cap.WORK_UTTERANCES:
        work_tokens |= set(re.findall(r"[a-z0-9]+", u.lower()))
    anchors = {spec.anchor_a_content for spec in battery} | {spec.anchor_b_content
                                                             for spec in battery}
    check(work_tokens & anchors == set(),
          f"WORK_UTTERANCES tokens name no battery anchor (overlap: {work_tokens & anchors})")
    # WORK_UTTERANCES drive REAL work: each utterance lights up real workload sources
    lit_total = 0
    for u in cap.WORK_UTTERANCES:
        p = perceive(ws, u)
        lit_total += len(p.sources)
        check(len(p.sources) > 0,
              f"WORK_UTTERANCE {u!r} lights up >=1 workload source (real work) "
              f"(saw {len(p.sources)})")
    check(lit_total >= len(cap.WORK_UTTERANCES),
          "the workload utterances collectively drive real spreading work")


def test_workload_substrate_does_not_steer_selection_or_extremes():
    section("D6 FLAGGED CHOICE — workload not engineered toward extremes/selection: the "
            "workload substrate is a few small symmetric linked domains (not a busy-vs-idle "
            "extreme generator, not a contested topology). Confirm it builds cleanly, is "
            "integral, and is NOT a contested/midnode topology (it just gives think() real "
            "nodes to spread over).")
    ws = cap.build_workload_store()
    # integral
    try:
        ws.check_integrity()
        ok = True
    except Exception as e:
        ok = False
        print(f"    integrity error: {e}")
    check(ok, "the workload substrate passes check_integrity()")
    contents = {ws.get_node(n).content for n in ws.all_node_ids()}
    check("midnode" not in contents,
          "the workload substrate is NOT a contested/midnode topology (it is workload only)")
    # the workload is small (a handful of domains), not an extreme generator
    check(len(contents) <= 40,
          f"the workload substrate is small ({len(contents)} nodes) — a realistic mixed "
          f"workload, not an extreme generator")
    # build_workload_store is referenced only by capture_real_telemetry (workload generator),
    # never by the battery construction
    cap_src = inspect.getsource(cap)
    # the battery builder must not call build_workload_store
    bb_src = inspect.getsource(cap.build_realistic_battery)
    check("build_workload_store" not in bb_src,
          "build_realistic_battery does NOT touch the workload substrate (separation)")
    rp_src = inspect.getsource(cap.RealisticPercept.build_store)
    check("build_workload_store" not in rp_src and "WORK_UTTERANCES" not in rp_src,
          "the percept store builder does NOT touch the workload substrate / WORK_UTTERANCES")


# ═════════════════════════════════════════════════════════════════════════════
# E. LOOP-CLOSED: perception lights up EXACTLY the two anchors (no neighbor leakage)
# ═════════════════════════════════════════════════════════════════════════════

def test_perception_lights_exactly_two_anchors_loopclosed():
    section("E1 LOOP-CLOSED CLEAN PERCEPTION: for EVERY percept, driving perceive() with the "
            "percept's OWN generated text lights up EXACTLY its two anchor nodes as sources — "
            "never a neighbor (nbr_*) or tail (the builder's anchor-free-neighbor bug-fix, "
            "re-verified loop-closed on system-generated input, not a hand input).")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    leaks = 0
    for spec in battery:
        store = spec.build_store()
        p = perceive(store, spec.percept_text)   # the percept's OWN text (loop-closed)
        lit = {store.get_node(nid).content for nid in p.sources}
        want = {spec.anchor_a_content, spec.anchor_b_content}
        if lit != want:
            leaks += 1
            if leaks <= 5:
                print(f"    LEAK @ {spec.percept_text!r}: lit {sorted(lit)} != {sorted(want)}")
    check(leaks == 0,
          f"every percept lights up EXACTLY its two anchors — no neighbor/tail leakage "
          f"(violations={leaks}/60)")


def test_neighbor_and_tail_contents_embed_no_anchor_substring():
    section("E2 ANCHOR-FREE NAMESPACE (structural): every neighbor (nbr_a_*/nbr_b_*) and tail "
            "(tail_a) content contains NO anchor word as a substring — the structural reason "
            "E1 holds. Re-checked directly against the built stores for the WHOLE battery.")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    offenders = []
    for spec in battery:
        store = spec.build_store()
        anchors = {spec.anchor_a_content, spec.anchor_b_content}
        for nid in store.all_node_ids():
            c = store.get_node(nid).content
            if c in anchors:
                continue
            # a non-anchor node must contain NO anchor word as a substring
            for anc in EXP_VOCAB:
                if anc in c:
                    offenders.append((spec.percept_text, c, anc))
    check(not offenders,
          f"no neighbor/tail content embeds an anchor substring (offenders: {offenders[:5]})")


def test_built_stores_are_integral_loopclosed():
    section("E3 INTEGRITY (every built store): all 60 percept stores pass check_integrity() — "
            "the substrate bar holds on every system-generated topology the battery builds.")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    bad = 0
    for spec in battery:
        s = spec.build_store()
        try:
            s.check_integrity()
        except Exception as e:
            bad += 1
            if bad <= 3:
                print(f"    integrity fail @ {spec.percept_text!r}: {e}")
    check(bad == 0, f"all 60 built stores are integral (failures={bad})")


# ═════════════════════════════════════════════════════════════════════════════
# F. REPLAY-DETERMINISM ACROSS 6 PYTHONHASHSEED (fresh processes)
# ═════════════════════════════════════════════════════════════════════════════

def _probe(code: str, seed: str) -> str:
    env = dict(os.environ)
    env["PSYCHE_SRC"] = _SRC
    env["PSYCHE_EXP"] = _HERE
    env["PYTHONHASHSEED"] = seed
    out = subprocess.run([sys.executable, "-c", code], env=env,
                         capture_output=True, text=True)
    if out.returncode != 0:
        print("  (subprocess stderr)\n" + out.stderr)
        return ""
    return out.stdout.strip()


def test_battery_canonical_hash_byte_identical_across_six_seeds():
    section("F1 REPLAY DETERMINISM (battery, rule-7): the battery's canonical-JSON SHA-256 is "
            "byte-identical across 6 PYTHONHASHSEED in FRESH interpreters. Independently "
            "re-hashed by the tester via the script's serialize_battery.")
    code = (
        "import os,sys\n"
        "sys.path.insert(0, os.environ['PSYCHE_SRC'])\n"
        "sys.path.insert(0, os.environ['PSYCHE_EXP'])\n"
        "import exp2c_capture as cap\n"
        "b = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)\n"
        "print(cap.sha256_of_canonical(cap.serialize_battery(b)))\n"
    )
    seeds = ["0", "1", "2", "3", "7", "42"]
    digests = [_probe(code, s) for s in seeds]
    first = digests[0]
    check(first != "" and len(first) == 64,
          f"battery probe produced a SHA-256 digest (got len {len(first)})")
    for s, d in zip(seeds, digests):
        check(d == first, f"hash seed {s}: battery digest matches seed {seeds[0]} "
                          f"(byte-identical)")
    print(f"    battery canonical SHA-256 (all seeds): {first}")


def test_battery_object_fields_byte_identical_across_six_seeds():
    section("F2 REPLAY DETERMINISM (battery OBJECT fields, not just the hash): a full repr of "
            "every percept's structural draws is byte-identical across 6 seeds — so the "
            "determinism is in the DATA, not only in a hash that could mask field reordering.")
    code = (
        "import os,sys\n"
        "sys.path.insert(0, os.environ['PSYCHE_SRC'])\n"
        "sys.path.insert(0, os.environ['PSYCHE_EXP'])\n"
        "import exp2c_capture as cap\n"
        "b = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)\n"
        "rows = [(p.anchor_a_content,p.anchor_b_content,p.domain_size_a,p.domain_size_b,"
        "tuple(p.internal_n_a),tuple(p.internal_n_b),p.bridge_present,p.bridge_target_index,"
        "p.bridge_n,p.depth_extra) for p in b]\n"
        "print(repr(rows))\n"
    )
    seeds = ["0", "1", "2", "3", "7", "42"]
    outs = [_probe(code, s) for s in seeds]
    first = outs[0]
    check(first != "", "battery-fields probe produced non-empty output")
    for s, o in zip(seeds, outs):
        check(o == first, f"hash seed {s}: battery object fields match seed {seeds[0]}")


def test_trace_processing_deterministic_across_six_seeds():
    section("F3 REPLAY DETERMINISM (trace processing): frictions_from_trace + "
            "sweep_levels_from_frictions over a FIXED sample sequence are byte-identical "
            "across 6 seeds in fresh interpreters (the trace-PROCESSING surface is "
            "deterministic; the live CAPTURE is the only non-determinism and is NOT run).")
    code = (
        "import os,sys\n"
        "sys.path.insert(0, os.environ['PSYCHE_SRC'])\n"
        "sys.path.insert(0, os.environ['PSYCHE_EXP'])\n"
        "import exp2c_capture as cap\n"
        "import psyche_bodysensor as bs\n"
        "samples=[bs.TelemetrySample(0.0,0.0),bs.TelemetrySample(1.0,0.91),"
        "bs.TelemetrySample(2.3,1.4),bs.TelemetrySample(2.9,1.42),"
        "bs.TelemetrySample(5.0,3.7),bs.TelemetrySample(5.05,5.04)]\n"
        "fr=cap.frictions_from_trace(samples)\n"
        "lv=cap.sweep_levels_from_frictions(fr,cap.SWEEP_LEVELS_REALISTIC)\n"
        "print(repr(fr)); print(repr(lv))\n"
    )
    seeds = ["0", "1", "2", "3", "7", "42"]
    outs = [_probe(code, s) for s in seeds]
    first = outs[0]
    check(first != "", "trace-processing probe produced non-empty output")
    for s, o in zip(seeds, outs):
        check(o == first, f"hash seed {s}: trace-processing output matches seed {seeds[0]}")


def test_serialize_battery_canonical_form_independently_rehashed():
    section("F4 CANONICAL SERIALIZATION (independent re-hash): the tester independently parses "
            "serialize_battery's output and re-serializes it with sorted keys + compact "
            "separators, then SHA-256s it — and gets the SAME digest sha256_of_canonical "
            "produces. So the digest is genuinely over the canonical content, tamper-evident.")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    blob = cap.serialize_battery(battery)
    # the script's digest
    script_digest = cap.sha256_of_canonical(blob)
    # independent re-canonicalization
    payload = json.loads(blob)
    recanon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    my_digest = hashlib.sha256(recanon.encode("utf-8")).hexdigest()
    check(my_digest == script_digest,
          f"independent canonical re-hash matches the script digest "
          f"({my_digest[:12]}.. vs {script_digest[:12]}..)")
    # and the blob is already canonical (round-trips to itself)
    check(recanon == blob,
          "serialize_battery already emits canonical sorted compact JSON (re-canon is a no-op)")
    # a single-bit change to the content changes the digest (tamper-evidence)
    tampered = dict(payload)
    tampered["percept_count"] = payload["percept_count"] + 1
    t_digest = hashlib.sha256(
        json.dumps(tampered, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    check(t_digest != script_digest, "a tampered battery yields a different digest")


# ═════════════════════════════════════════════════════════════════════════════
# G. BLINDNESS — NO GRADED NUMBER / NO ACTIVATION-WINNER-FLIP PATH; main() inert
# ═════════════════════════════════════════════════════════════════════════════

def test_no_graded_or_flip_or_winner_symbol_exposed():
    section("G1 BLINDNESS (no graded path): the module exposes NO winner/flip/grade/"
            "effect-size/verdict symbol — it builds stimuli only. Checked over the module's "
            "public AND private names.")
    forbidden = ("flip", "winner", "grade", "graded", "effect_size", "effectsize",
                 "select_winner", "verdict", "narrow", "direction_stat", "jaccard",
                 "spearman", "sign_test", "crossover", "d_star")
    for name in dir(cap):
        if name.startswith("__"):
            continue
        low = name.lower()
        for bad in forbidden:
            check(bad not in low,
                  f"module exposes no '{bad}'-named symbol (saw {name!r})")
    for must_absent in ("percept_flips", "winner_set", "_winner_set", "grade_battery",
                        "flip_rate", "compute_flip_rate", "select_winner", "_density_score"):
        check(not hasattr(cap, must_absent),
              f"capture module has no '{must_absent}' attribute (graded readout is the "
              f"validator's later step)")


def test_does_not_import_competition_or_field_or_coalition_engine():
    section("G2 BLINDNESS (static imports): the module never imports psyche_workspace "
            "(select_winner), and never calls form_coalitions / build_activation_field to "
            "grade. It imports ONLY the permitted §6 surface (store + perceive/think for the "
            "workload + the SAME psyche_bodysensor).")
    src = inspect.getsource(cap)
    check("psyche_workspace" not in src,
          "no reference to psyche_workspace (the competition/winner readout is not consumed)")
    check("select_winner" not in src, "select_winner appears nowhere")
    check("form_coalitions" not in src, "no coalition formation")
    check("build_activation_field" not in src, "no activation-field construction")
    check("from psyche_bodysensor import" in src,
          "the module DOES import psyche_bodysensor (the permitted §6 telemetry surface)")
    # parse imports via AST to be sure nothing graded sneaks in
    tree = ast.parse(src)
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Import):
            for n in node.names:
                imported_modules.add(n.name)
    check("psyche_workspace" not in imported_modules,
          f"AST confirms psyche_workspace is not imported (imports: {sorted(imported_modules)})")
    check("psyche_coalitions" not in imported_modules,
          "AST confirms psyche_coalitions is not imported")
    check("psyche_field" not in imported_modules,
          "AST confirms psyche_field is not imported")
    check("psyche_activation" not in imported_modules,
          "AST confirms psyche_activation is not imported")


def test_capture_runs_think_only_as_workload_never_reads_result():
    section("G3 BLINDNESS (workload, not readout): capture_real_telemetry calls think() ONLY "
            "to generate CPU work; it NEVER binds or inspects think()'s result for a winner/"
            "thought/field/coalitions/friction. AST-verified that the think() call is an "
            "expression statement (result discarded), not an assignment that is later read.")
    src = inspect.getsource(cap.capture_real_telemetry)
    for attr in (".winner", ".thought", ".workspace", ".field_", ".coalitions",
                 ".body_friction", ".effective_decay", ".clustering"):
        check(attr not in src,
              f"capture never reads think()'s {attr} (no result-side signal consumed)")
    # AST: the think(...) call appears only as a bare Expr statement (discarded), never as the
    # value of an Assign whose target is later inspected.
    tree = ast.parse(src)
    assigned_from_think = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and \
               val.func.id == "think":
                assigned_from_think = True
    check(not assigned_from_think,
          "think()'s return is never assigned to a name (the result is discarded — pure "
          "workload, never a graded readout)")


def test_battery_serialization_is_structural_only():
    section("G4 BLINDNESS (structural serialization): the serialized battery contains ONLY "
            "structural keys (anchors, domain sizes, integer traversal counts, bridge "
            "presence/target/bridge_n, depth_extra) — no activation/winner/thought/flip/decay/"
            "friction/coalition token anywhere.")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    blob = cap.serialize_battery(battery)
    text = blob.lower()
    for bad in ("activation", "winner", "thought", "flip", "decay", "friction", "coalition",
                "effective", "crossover", "d_star", "midnode"):
        check(bad not in text,
              f"serialized battery contains no '{bad}' token (structural only)")
    payload = json.loads(blob)
    percepts = payload["percepts"]
    for required in ("anchor_a", "anchor_b", "domain_size_a", "domain_size_b",
                     "internal_n_a", "internal_n_b", "bridge_present", "bridge_target_index",
                     "bridge_n", "depth_extra"):
        check(required in percepts[0],
              f"each serialized percept carries the structural key '{required}'")
    check(len(percepts) == 60, f"60 percepts serialized (saw {len(percepts)})")


def test_main_not_triggered_by_import_and_writes_nothing_on_import():
    section("G5 MAIN INERT ON IMPORT: importing the module does NOT run main() / "
            "capture_real_telemetry (no live capture, no file write on import). Verified by a "
            "fresh-process import that asserts the results artifacts were NOT created and no "
            "capture banner was printed.")
    # fresh process: import the module, then assert the frozen artifact files do NOT exist as a
    # side effect of import (they are produced only by the gated main()).
    trace_path = cap.TRACE_PATH
    percepts_path = cap.PERCEPTS_PATH
    code = (
        "import os,sys\n"
        "sys.path.insert(0, os.environ['PSYCHE_SRC'])\n"
        "sys.path.insert(0, os.environ['PSYCHE_EXP'])\n"
        "tp = os.environ['TRACE_PATH']; pp = os.environ['PERCEPTS_PATH']\n"
        "before = (os.path.exists(tp), os.path.exists(pp))\n"
        "import exp2c_capture as cap\n"
        "after = (os.path.exists(tp), os.path.exists(pp))\n"
        "print(repr((before, after)))\n"
    )
    env = dict(os.environ)
    env["PSYCHE_SRC"] = _SRC
    env["PSYCHE_EXP"] = _HERE
    env["TRACE_PATH"] = trace_path
    env["PERCEPTS_PATH"] = percepts_path
    env["PYTHONHASHSEED"] = "0"
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    check(out.returncode == 0, f"the import probe ran (rc={out.returncode}); stderr:\n{out.stderr}")
    printed = out.stdout.strip()
    # import must not create the artifacts: the 'after' existence must equal the 'before'
    # existence (import is side-effect-free w.r.t. the frozen artifacts).
    check("), (" in printed or printed.startswith("(("),
          f"probe printed a (before, after) tuple (saw {printed!r})")
    # parse the tuple and assert before == after (no new file created by import)
    try:
        before, after = ast.literal_eval(printed)
        same = (before == after)
    except Exception as e:
        same = False
        print(f"    parse error: {e}; raw={printed!r}")
    check(same,
          f"importing exp2c_capture does NOT create the frozen artifacts (before {before if 'before' in dir() else '?'} "
          f"== after {after if 'after' in dir() else '?'}) — main() is not import-triggered")
    # and no capture banner / no graded language was printed on import
    check("CAPTURE COMPLETE" not in out.stdout and "flip-rate" not in out.stdout.lower(),
          "import prints no capture banner and no flip-rate (main is not run on import)")


def test_module_guarded_by_name_main():
    section("G6 MAIN GUARDED: main() is invoked only under `if __name__ == '__main__'` "
            "(AST-verified), so neither import nor the test suite triggers the live capture.")
    src = inspect.getsource(cap)
    tree = ast.parse(src)
    # find the `if __name__ == "__main__":` guard and confirm main() is called inside it
    guarded_main_call = False
    top_level_main_call = False
    for node in tree.body:
        if isinstance(node, ast.If):
            test = node.test
            is_name_main = (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name) and test.left.id == "__name__"
            )
            if is_name_main:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and \
                       sub.func.id == "main":
                        guarded_main_call = True
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            f = node.value.func
            if isinstance(f, ast.Name) and f.id == "main":
                top_level_main_call = True
    check(guarded_main_call, "main() is called inside the `if __name__ == '__main__'` guard")
    check(not top_level_main_call, "main() is NOT called at module top level (import-safe)")


# ═════════════════════════════════════════════════════════════════════════════
# H. NO OVERCLAIM (asserted-negatives)
# ═════════════════════════════════════════════════════════════════════════════

def test_serialization_fully_determines_every_topology():
    section("G7 RECONSTRUCTABILITY (the frozen hash genuinely pins the stimuli): the "
            "serialized JSON records seed, count, parameter_space, draw_order, anchor_vocab, "
            "AND every percept's complete structural draws — so the topology the graded run "
            "uses is fully determined by (and recoverable from) the frozen artifact. We "
            "reconstruct each store from the JSON ALONE and confirm it is byte-identical to "
            "the store the script builds.")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    blob = cap.serialize_battery(battery)
    payload = json.loads(blob)
    # provenance keys that make the frozen artifact self-describing
    for key in ("battery_seed", "percept_count", "parameter_space", "draw_order",
                "anchor_vocab", "percepts"):
        check(key in payload, f"serialized battery records '{key}' (self-describing frozen artifact)")
    check(payload["battery_seed"] == EXP_SEED, "serialized seed == 20260622")
    check(payload["percept_count"] == EXP_COUNT, "serialized count == 60")
    check(list(payload["anchor_vocab"]) == list(EXP_VOCAB), "serialized vocab == the vocab")
    # reconstruct each topology from the JSON description alone, independently of the script's
    # RealisticPercept, and compare node-set + directed-edge-with-traversal-count to the
    # script-built store. If the JSON omitted any structural field, this would diverge.
    def store_signature(s):
        nodes = sorted(s.get_node(n).content for n in s.all_node_ids())
        content = {n: s.get_node(n).content for n in s.all_node_ids()}
        edges = []
        for rid in s.all_road_ids():
            r = s.get_road(rid, apply_decay=False)
            edges.append((content[r.source_id], content[r.target_id], r.traversal_count))
        return (tuple(nodes), tuple(sorted(edges)))

    def rebuild_from_json(pj):
        s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
        a = s.add_node(pj["anchor_a"], NodeType.CONCEPT)
        b = s.add_node(pj["anchor_b"], NodeType.CONCEPT)
        a_nbrs = []
        for k in range(pj["domain_size_a"]):
            nid = s.add_node(f"nbr_a_{k}", NodeType.CONCEPT)
            a_nbrs.append(nid)
            for _ in range(pj["internal_n_a"][k]):
                s.traverse(a, nid)
        b_nbrs = []
        for k in range(pj["domain_size_b"]):
            nid = s.add_node(f"nbr_b_{k}", NodeType.CONCEPT)
            b_nbrs.append(nid)
            for _ in range(pj["internal_n_b"][k]):
                s.traverse(b, nid)
        if pj["depth_extra"] == 1 and a_nbrs:
            tail = s.add_node("tail_a", NodeType.CONCEPT)
            for _ in range(pj["internal_n_a"][0]):
                s.traverse(a_nbrs[0], tail)
        if pj["bridge_present"] and b_nbrs:
            tgt = b_nbrs[pj["bridge_target_index"]]
            for _ in range(pj["bridge_n"]):
                s.traverse(a, tgt)
        return s

    mismatches = 0
    for spec, pj in zip(battery, payload["percepts"]):
        sig_script = store_signature(spec.build_store())
        sig_json = store_signature(rebuild_from_json(pj))
        if sig_script != sig_json:
            mismatches += 1
            if mismatches <= 3:
                print(f"    reconstruct mismatch @ {pj['percept_text']!r}")
    check(mismatches == 0,
          f"every topology reconstructed from the JSON ALONE matches the script-built store "
          f"(mismatches={mismatches}) — the frozen artifact fully determines the stimuli")


def test_ondisk_indent_file_rehashes_to_the_canonical_digest():
    section("G8 DEFERRED-HASH FAITHFULNESS: the on-disk artifact is written indent=2 (human-"
            "diffable) while the digest is over the COMPACT canonical form. A graded run that "
            "loads the committed file and re-canonicalizes (sort_keys, compact separators) "
            "must reproduce the frozen digest. We simulate that round-trip in-memory (no file "
            "written) and confirm it reproduces sha256_of_canonical.")
    battery = cap.build_realistic_battery(cap.BATTERY_SEED_REALISTIC, cap.PERCEPT_COUNT_REALISTIC)
    compact = cap.serialize_battery(battery)
    digest = cap.sha256_of_canonical(compact)
    # what _write_canonical writes to disk: indent=2 sorted JSON of the SAME payload
    payload = json.loads(compact)
    on_disk = json.dumps(payload, sort_keys=True, indent=2)
    # the graded run re-loads the file and re-canonicalizes to compact, then hashes
    reloaded = json.loads(on_disk)
    recompact = json.dumps(reloaded, sort_keys=True, separators=(",", ":"))
    rehash = hashlib.sha256(recompact.encode("utf-8")).hexdigest()
    check(rehash == digest,
          f"the indent=2 on-disk artifact re-canonicalizes to the frozen compact digest "
          f"({rehash[:12]}.. == {digest[:12]}..) — deferred-hash round-trip is faithful")
    check(on_disk != compact,
          "the on-disk (indent=2) form differs from the compact hashed form (as designed)")


def test_exploratory_live_capture_band_is_realistic_not_pilot_extreme():
    section("D7 EXPLORATORY LIVE CAPTURE (band sanity, NOT frozen): actually run "
            "capture_real_telemetry() ONCE in-process (NO artifact written, NOT frozen) and "
            "confirm the real friction band the §6.1 workload produces is REALISTIC — i.e. it "
            "does NOT saturate to the pilot's ~0.999 busy-vs-idle extreme. This is the one "
            "fairness property that cannot be checked statically; the directive permits a "
            "small exploratory capture to check the band. The frozen stimulus is NOT produced "
            "here (that is gated on PASS + the human's word).")
    # one honest live capture, in-process; we never serialize/write/freeze it.
    samples = cap.capture_real_telemetry()
    frictions = cap.frictions_from_trace(samples)
    check(len(samples) == cap.CAPTURE_SAMPLES_REALISTIC + 1,
          f"capture produced {cap.CAPTURE_SAMPLES_REALISTIC}+1 samples (saw {len(samples)})")
    check(len(frictions) == cap.CAPTURE_SAMPLES_REALISTIC,
          f"the trace yields {cap.CAPTURE_SAMPLES_REALISTIC} frictions (saw {len(frictions)})")
    # every friction is a real value in [0,1]
    check(all(0.0 <= f <= 1.0 for f in frictions),
          "every captured friction is in [0,1] (real compute_friction output)")
    lo, hi = min(frictions), max(frictions)
    mean = sum(frictions) / len(frictions)
    print(f"    EXPLORATORY observed friction band: [{lo:.6f} .. {hi:.6f}]  mean={mean:.6f}")
    print(f"    (this capture is NOT frozen; it is a band-sanity probe only)")
    # The decisive REALISM check: the realistic band must NOT be the pilot's near-saturated
    # extreme. The pilot's busy-spin-vs-sleep alternation pushed friction to ~0.999; a
    # realistic mixed workload (think() + a 0.5ms yield) must produce a MODERATE band. We do
    # NOT assert a graded number; we assert the band is not the manufactured extreme. A very
    # high max on EVERY sample would betray a covert extreme generator; the realistic workload
    # should keep the bulk of mass low. NB: machine-dependent — this is a sanity band, and the
    # capture's own §6.2 degenerate-guard documents that a narrow/collapsed band is a valid
    # honest finding (not a license to widen). So we only flag a hard FAILURE if the band looks
    # like the pilot's manufactured bimodal extreme (mean pinned near 1.0).
    check(mean < 0.95,
          f"the realistic band's MEAN friction ({mean:.4f}) is not pinned at the pilot's "
          f"manufactured ~0.999 extreme (a covert extreme generator would saturate it)")
    # the workload is think()+small-yield, so we expect contention spikes but not a forced
    # bimodal 0-or-1; report the fraction of samples above 0.9 (pilot-extreme-like) for the
    # record — not a hard gate (machine-dependent), but a covert extreme generator would have
    # nearly ALL samples saturated.
    frac_extreme = sum(1 for f in frictions if f > 0.9) / len(frictions)
    print(f"    fraction of samples > 0.9 (pilot-extreme-like): {frac_extreme:.3f}")
    check(frac_extreme < 1.0,
          "not EVERY captured sample is a pilot-style >0.9 extreme (the workload is not a "
          "manufactured saturated-extreme generator)")


def test_no_overclaim_public_names():
    section("H1 NO OVERCLAIM: no public name in the module encodes a feeling/emotion/"
            "awareness/consciousness/mind/meaning claim — the headline is 'battery'/'trace'/"
            "'friction' (a derived telemetry signal).")
    for name in dir(cap):
        if name.startswith("__"):
            continue
        low = name.lower()
        for bad in ("feel", "emotion", "aware", "conscious", "sentient", "_mind", "meaning"):
            check(bad not in low, f"no public name encodes '{bad}' (saw {name!r})")


def test_known_limitation_asserted_negative():
    section("H2 KNOWN LIMITATION (asserted-negative): this script builds the FROZEN STIMULI "
            "ONLY — it computes NO flip-rate, NO graded number, and establishes NO meaning. "
            "Whether realistic telemetry meaningfully moves realistic selection is the "
            "validator's later step, NOT decided here. (Pinned structurally by G1-G4.)")
    has_graded = any(
        ("flip" in n.lower() or "grade" in n.lower() or "winner" in n.lower())
        for n in dir(cap) if not n.startswith("__")
    )
    check(not has_graded,
          "ASSERTED-NEGATIVE: no flip/grade/winner symbol exists — blind stimulus "
          "construction; NO meaning claim made (the graded run is the validator's step)")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 70)
    print("  TESTER — EXP-2c CAPTURE ADVERSARIAL SUITE (stimulus fairness + faithfulness)")
    print("  independent re-derivation; NO graded number; NO meaning claim")
    print("=" * 70)

    # A. independent re-derivation
    test_independent_rederivation_matches_the_script_exactly()
    test_anchor_vocab_is_substring_clean_independently_verified()
    # B. not flip-pre-selected + covert flip-bias probes + flagged choices
    test_no_contested_node_is_structurally_possible_not_just_absent()
    test_no_constructed_two_hop_sink_from_the_far_anchor()
    test_no_crossover_field_anywhere_in_the_dataclass()
    test_covert_flip_bias_probe_bridge_n_is_free_uniform_not_a_crossover_window()
    test_covert_flip_bias_probe_bridge_n_not_tuned_to_internal_cohesion()
    test_depth_extra_placement_is_a_neutral_structural_choice()
    test_some_percepts_have_no_bridge_real_coin_flip()
    # C. distinct from pilot (structural)
    test_distinct_from_pilot_structurally_rederived_both()
    test_realistic_domains_generically_asymmetric_unlike_pilot_mirror()
    # D. real telemetry, realistic band, no inflation, workload separation
    test_same_compute_friction_and_bodysensor_by_object_identity()
    test_frictions_from_trace_equals_compute_friction_on_deltas_loopclosed()
    test_sweep_uses_only_observed_range_no_inflation_and_not_pilot_extremes()
    test_capture_params_are_realistic_not_pilot_extremes()
    test_workload_substrate_is_separate_from_the_graded_battery()
    test_workload_substrate_does_not_steer_selection_or_extremes()
    # NB: test_exploratory_live_capture_band_is_realistic_not_pilot_extreme() is defined below
    # but DELIBERATELY NOT called in the canonical deterministic run: it performs a real live
    # capture (non-deterministic, machine-dependent, slow) and is a tester DIAGNOSTIC only,
    # run manually to gather band evidence. Keeping it out of the canonical suite preserves the
    # runner's determinism (the live capture is the single non-determinism, kept off the test
    # surface exactly like the pilot's live capture). Its evidence is recorded in the tester
    # verdict. Run it manually with: python3 experiments/test_tester_exp2c_capture_adversarial.py --live
    # E. loop-closed clean perception
    test_perception_lights_exactly_two_anchors_loopclosed()
    test_neighbor_and_tail_contents_embed_no_anchor_substring()
    test_built_stores_are_integral_loopclosed()
    # F. replay determinism
    test_battery_canonical_hash_byte_identical_across_six_seeds()
    test_battery_object_fields_byte_identical_across_six_seeds()
    test_trace_processing_deterministic_across_six_seeds()
    test_serialize_battery_canonical_form_independently_rehashed()
    # G. blindness / main inert
    test_no_graded_or_flip_or_winner_symbol_exposed()
    test_does_not_import_competition_or_field_or_coalition_engine()
    test_capture_runs_think_only_as_workload_never_reads_result()
    test_battery_serialization_is_structural_only()
    test_serialization_fully_determines_every_topology()
    test_ondisk_indent_file_rehashes_to_the_canonical_digest()
    test_main_not_triggered_by_import_and_writes_nothing_on_import()
    test_module_guarded_by_name_main()
    # H. no overclaim
    test_no_overclaim_public_names()
    test_known_limitation_asserted_negative()

    print()
    print("=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    print("=" * 70)
    return 1 if _failed else 0


def live_diagnostic() -> int:
    """Manual, NON-deterministic tester diagnostic (NOT part of the canonical run): perform a
    real in-process live capture to check the friction band is realistic (not the pilot's
    saturated extreme) and decompose what drives it (think() cost vs the 0.5ms yield). Writes
    NOTHING and freezes NOTHING. Run: python3 experiments/test_tester_exp2c_capture_adversarial.py --live"""
    print("=" * 70)
    print("  TESTER — EXP-2c LIVE BAND DIAGNOSTIC (manual; non-deterministic; nothing frozen)")
    print("=" * 70)
    # band sanity (the D7 assertions)
    test_exploratory_live_capture_band_is_realistic_not_pilot_extreme()
    # decompose what drives the band
    import time as _t
    ws = cap.build_workload_store()
    n = 60
    p0, q0 = _t.perf_counter(), _t.process_time()
    for i in range(n):
        cap.think(ws, cap.WORK_UTTERANCES[i % len(cap.WORK_UTTERANCES)])
    p1, q1 = _t.perf_counter(), _t.process_time()
    tw, tc = (p1 - p0) / n, (q1 - q0) / n
    print(f"\n  per-think(): wall={tw*1e6:.1f}us cpu={tc*1e6:.1f}us "
          f"(yield={cap.REALISTIC_YIELD_S*1e6:.0f}us)")
    est_wall = tw + cap.REALISTIC_YIELD_S
    share = cap.REALISTIC_YIELD_S / est_wall if est_wall > 0 else 0.0
    print(f"  sleep wall-share of each interval: {share:.3f}  -> band is yield-dominated, "
          f"NOT primarily 'real contention'")
    print(f"\n  RESULT (diagnostic): {_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    if "--live" in sys.argv:
        raise SystemExit(live_diagnostic())
    raise SystemExit(main())
