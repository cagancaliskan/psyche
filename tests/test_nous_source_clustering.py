"""
Test suite for Nous source-clustering (step 1c).

DISCIPLINE THIS ROUND (the one paid for in bugs five times over):
  - Loop-closure: the grouping is driven by sources that perceive() produced from TEXT,
    never by hand-placed sources and never by hand-assigned groups. The acceptance path
    runs through the real think() on a real utterance. Hand-assigning a grouping to make a
    test pass is an automatic FAIL — it re-encodes its own answer.
  - Mechanism, not meaning: these tests verify the grouping is correct, deterministic,
    pure, integrity-preserving, and scale-invariant. Whether the grouping CORRESPONDS to
    any externally-defined structure (word-association communities, etc.) is NOT tested
    here — that is the validator's §6.2 job against external data.
  - The substrate bar (determinism across processes, integrity, purity, scale-invariance)
    ships WITH this first commit, each as an explicit test, on inputs built to stress it.
  - Known limitations are shipped as explicit asserted-negative tests, not hidden.

Run directly:
    python3 test_nous_source_clustering.py
"""

from nous_store import SubstrateStore, Clock, NodeType
from nous_perceive import perceive, think
from nous_source_clustering import (
    cluster_sources, SourceClustering, SourceGroup,
    DEFAULT_PROXIMITY_FRACTION, _pair_proximity,
)

_passed = 0
_failed = 0

def check(cond, msg):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {msg}")

def section(name):
    print(f"\n{name}")

def _worn(s, a, b, n=30):
    for _ in range(n):
        s.traverse(a, b)


def _small_mind():
    """The SAME small store the perceive/known-limitation test uses: two loose domains
    with cross-linking. Built once, identically, so 1c is exercised on the exact graph the
    closed loop already surfaced the bug on."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Loop-closed grouping behavior (sources come from perceive(), never hand-placed)
# ─────────────────────────────────────────────────────────────────────────────

def test_same_domain_sources_merge_into_one_group_loop_closed():
    section("LOOP-CLOSED: three same-domain perceived sources merge into ONE group")
    s, n = _small_mind()
    # sources are produced by perception from TEXT — not hand-placed
    p = perceive(s, "coffee in the kitchen this morning")
    perceived = set(p.sources)
    # precondition: perception did light up the three warm-domain sources
    check({n["coffee"], n["kitchen"], n["morning"]} <= perceived,
          "precondition: real input named coffee, kitchen, morning as sources")

    clustering = cluster_sources(s, p.sources)
    # the three warm sources land in exactly one group together
    groups_with_warm = [
        g for g in clustering.groups
        if {n["coffee"], n["kitchen"], n["morning"]} & set(g.members)
    ]
    check(len(groups_with_warm) == 1,
          f"coffee/kitchen/morning occupy a single group "
          f"(touched {len(groups_with_warm)} groups)")
    if groups_with_warm:
        g = groups_with_warm[0]
        check({n["coffee"], n["kitchen"], n["morning"]} <= set(g.members),
              "all three same-domain sources are members of that one group")


def test_separate_domains_form_separate_groups_loop_closed():
    section("LOOP-CLOSED: perceived sources in unconnected domains form SEPARATE groups")
    # This proves the partition can structurally yield MORE THAN ONE group — i.e. the
    # grouping is not a degenerate 'everything always merges' branch. The input is chosen
    # by what perception lights up, not by hand-grouping: 'coffee in the kitchen, writing
    # code' names coffee+kitchen (directly linked, n=30) and the 'writing code' node, which
    # has NO direct road to coffee or kitchen.
    s, n = _small_mind()
    p = perceive(s, "coffee in the kitchen, writing code")
    perceived = set(p.sources)
    check({n["coffee"], n["kitchen"], n["code"]} <= perceived,
          "precondition: perception named coffee, kitchen, and the code node")

    clustering = cluster_sources(s, p.sources)
    # coffee and kitchen (directly linked) share a group; code (no direct road) is apart
    def group_of(node):
        for g in clustering.groups:
            if node in g.members:
                return frozenset(g.members)
        return None
    g_coffee = group_of(n["coffee"])
    g_kitchen = group_of(n["kitchen"])
    g_code = group_of(n["code"])
    check(g_coffee is not None and g_coffee == g_kitchen,
          "coffee and kitchen (directly linked) are in the same group")
    check(g_code is not None and n["coffee"] not in g_code and n["kitchen"] not in g_code,
          "the code node (no direct road to either) is in a separate group")
    check(len(clustering.groups) >= 2,
          f"the partition yields more than one group (got {len(clustering.groups)}) — "
          f"proves grouping is not a structurally-impossible single-group branch")


def test_representative_is_highest_energy_then_creation_seq():
    section("representative election: highest source energy, ties on creation_seq asc")
    # Build a tiny store where two linked sources tie on energy; the earlier-created one
    # (lower creation_seq) must represent. Energies come from perceive(), not hand-set:
    # both nodes are named by exactly one token, so they tie, exercising the tiebreak.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    alpha = s.add_node("alpha", NodeType.CONCEPT)   # earlier creation_seq
    beta = s.add_node("beta", NodeType.CONCEPT)     # later creation_seq
    _worn(s, alpha, beta, n=30)                      # directly linked → one group
    p = perceive(s, "alpha and beta")
    check(abs(p.sources[alpha] - p.sources[beta]) < 1e-12,
          "precondition: the two sources tie on perceived energy")
    clustering = cluster_sources(s, p.sources)
    check(len(clustering.groups) == 1, "the two linked sources form one group")
    check(clustering.groups[0].representative == alpha,
          "the earlier-created source (lower creation_seq) wins the energy tie")


def test_group_seeds_feed_representatives_only():
    section("group_seeds maps representatives only (the field is seeded from reps)")
    s, n = _small_mind()
    p = perceive(s, "coffee in the kitchen this morning")
    clustering = cluster_sources(s, p.sources)
    reps = set(clustering.representatives())
    check(set(clustering.group_seeds.keys()) == reps,
          "group_seeds keys are exactly the group representatives")
    # every seed energy is the MAX of its group's perceived source energies (documented)
    for g in clustering.groups:
        expected = max(p.sources[m] for m in g.members)
        check(abs(clustering.group_seeds[g.representative] - expected) < 1e-12,
              "seed energy is the max of the group's source energies")


def test_think_seeds_field_from_group_representatives():
    section("integration: think() seeds the field from group representatives, not raw set")
    s, n = _small_mind()
    r = think(s, "coffee in the kitchen this morning")
    check(r.clustering is not None, "think() ran the 1c clustering stage")
    # the field's sources are the group representatives, NOT every perceived source
    field_sources = set(r.field_.sources)
    reps = set(r.clustering.representatives())
    check(field_sources == reps,
          f"the field was built from group representatives "
          f"(field sources == representatives)")
    # and there are fewer field sources than raw perceived sources (merging happened)
    check(len(field_sources) < len(r.perception.sources),
          "merging reduced the number of sources reaching the field")


# ─────────────────────────────────────────────────────────────────────────────
# Substrate bar — each an explicit test
# ─────────────────────────────────────────────────────────────────────────────

def test_clustering_is_pure_read():
    section("read-purity: clustering mutates NOTHING (road strengths + traversal counts)")
    s, n = _small_mind()
    before = {rid: (s.get_road(rid, apply_decay=False).strength,
                    s.get_road(rid, apply_decay=False).traversal_count)
              for rid in s.all_road_ids()}
    # repeated clustering passes, on real perceived sources
    p1 = perceive(s, "coffee in the kitchen this morning")
    p2 = perceive(s, "coffee in the kitchen, writing code")
    for _ in range(5):
        cluster_sources(s, p1.sources)
        cluster_sources(s, p2.sources)
    after = {rid: (s.get_road(rid, apply_decay=False).strength,
                   s.get_road(rid, apply_decay=False).traversal_count)
             for rid in s.all_road_ids()}
    check(before == after, "five repeated clustering passes changed no road")


def test_clustering_preserves_integrity():
    section("integrity: the store's integrity scan is unchanged before vs. after clustering")
    s, n = _small_mind()
    # a clean scan must hold before
    ok_before = True
    try:
        s.check_integrity()
    except Exception:
        ok_before = False
    check(ok_before, "precondition: integrity holds before clustering")

    p = perceive(s, "coffee in the kitchen this morning")
    for _ in range(3):
        cluster_sources(s, p.sources)

    ok_after = True
    try:
        s.check_integrity()
    except Exception as e:
        ok_after = False
        print("   integrity error:", e)
    check(ok_after, "integrity still holds after repeated clustering (no graph mutation)")


def test_scale_invariance_of_partition():
    section("scale-invariance: scaling energies/proximities by a constant keeps the partition")
    # The relative threshold means the partition depends on PROXIMITY RATIOS, not absolute
    # magnitudes. We prove it two ways, both without mutating the store.
    s, n = _small_mind()
    p = perceive(s, "coffee in the kitchen this morning")

    base = cluster_sources(s, p.sources)
    base_partition = sorted(tuple(sorted(g.members)) for g in base.groups)

    # (1) scale every SOURCE ENERGY by a constant: representatives and partition unchanged
    for k in (2.5, 0.1, 1000.0):
        scaled_energy = {nid: e * k for nid, e in p.sources.items()}
        c = cluster_sources(s, scaled_energy)
        part = sorted(tuple(sorted(g.members)) for g in c.groups)
        check(part == base_partition,
              f"partition identical when source energies scaled by {k}")
        # representative election is also scale-invariant (ratios unchanged)
        check(set(c.representatives()) == set(base.representatives()),
              f"representatives identical when source energies scaled by {k}")

    # (2) scale the PROXIMITY DISTRIBUTION itself: a relative threshold must be invariant.
    #     We exercise the threshold logic on a scaled proximity by scaling the energies
    #     fed to a controlled store whose proximities we can reason about — but the cleanest
    #     proof is structural: build two stores whose proximities differ by a constant
    #     factor and confirm identical partitions. We do this with two linked pairs.
    def _two_pair_store(strength_traversals):
        st = SubstrateStore(clock=Clock(simulated=True, start=0.0))
        a = st.add_node("a", NodeType.CONCEPT); b = st.add_node("b", NodeType.CONCEPT)
        c2 = st.add_node("c", NodeType.CONCEPT); d = st.add_node("d", NodeType.CONCEPT)
        # a-b strongly linked, c-d strongly linked, no a/b <-> c/d roads
        for _ in range(strength_traversals):
            st.traverse(a, b); st.traverse(c2, d)
        return st, {a: 1.0, b: 1.0, c2: 1.0, d: 1.0}, (a, b, c2, d)

    st1, e1, ids1 = _two_pair_store(30)
    st2, e2, ids2 = _two_pair_store(10)   # weaker absolute strengths, same STRUCTURE
    c1 = cluster_sources(st1, e1)
    c2c = cluster_sources(st2, e2)
    # both must yield two groups: {a,b} and {c,d}, regardless of absolute strength
    part1 = sorted(len(g.members) for g in c1.groups)
    part2 = sorted(len(g.members) for g in c2c.groups)
    check(part1 == [2, 2] and part2 == [2, 2],
          f"same structure at different absolute strengths → same partition shape "
          f"(got {part1} and {part2})")


def test_determinism_across_hash_seeds():
    section("ADVERSARIAL determinism: clustering identical across 6 hash seeds (fresh procs)")
    # Build an input that stresses every nondeterminism seam: equal-strength proximities
    # (ties everywhere in the proximity graph), equal source energies (ties in
    # representative election), driven through perceive() so nothing is hand-placed. Run in
    # fresh interpreters under distinct PYTHONHASHSEED values and assert the FULL clustering
    # — group membership (by stable content), representatives, group order, and group_seeds
    # — is byte-identical. Serialized by STABLE keys (content + creation_seq), never uuids.
    import subprocess, sys, os, textwrap
    probe = textwrap.dedent('''
        from nous_store import SubstrateStore, Clock, NodeType
        from nous_perceive import perceive
        from nous_source_clustering import cluster_sources
        s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
        def add(l, t=NodeType.CONCEPT): return s.add_node(l, t)
        coffee=add("coffee",NodeType.ENTITY); warmth=add("warmth",NodeType.SENSATION)
        morning=add("morning routine"); cozy=add("cozy feeling"); kitchen=add("kitchen",NodeType.ENTITY)
        work=add("work"); desk=add("desk",NodeType.ENTITY); deadline=add("deadline pressure"); code=add("writing code")
        def w(a,b,n):
            for _ in range(n): s.traverse(a,b)
        w(coffee,warmth,30); w(coffee,morning,30); w(morning,cozy,30); w(coffee,kitchen,30); w(kitchen,morning,30)
        w(work,desk,30); w(work,deadline,30); w(work,code,30); w(desk,code,30); w(coffee,work,8)
        p = perceive(s, "coffee in the kitchen this morning")
        clustering = cluster_sources(s, p.sources)
        out = []
        for g in clustering.groups:
            members_by_content = tuple(sorted(s.get_node(m).content for m in g.members))
            rep_content = s.get_node(g.representative).content
            seed = round(clustering.group_seeds[g.representative], 9)
            out.append((members_by_content, rep_content, seed))
        print(repr(out))
    ''')
    outs = []
    cwd = os.path.dirname(__file__) or "."
    for seed in ("0", "1", "2", "7", "42", "999"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        rr = subprocess.run([sys.executable, "-c", probe], cwd=cwd,
                            capture_output=True, text=True, env=env)
        if rr.returncode != 0:
            print("  (subprocess error)\n", rr.stderr)
        outs.append(rr.stdout.strip())
    check(len(set(outs)) == 1,
          f"clustering identical across 6 hash seeds (distinct outputs: {len(set(outs))})")


# ─────────────────────────────────────────────────────────────────────────────
# §6.1 mechanism / acceptance — the known-limitation test, re-examined through 1c
# ─────────────────────────────────────────────────────────────────────────────

def test_clustering_no_longer_strands_same_domain_sources():
    section("§6.1 (partial): 1c removes the stranded-singleton-source failure")
    # PROVEN by this test: the pre-1c failure stranded same-domain sibling SOURCES as
    # singleton basins (kitchen/morning alone). After 1c merges them into one group with a
    # single representative, there is only one warm basin, so NO perceived source strands
    # as a singleton. Driven through the real loop; sources from perceive(), not hand-placed.
    s, n = _small_mind()
    r = think(s, "coffee in the kitchen this morning")
    perceived = set(r.perception.sources)
    check({n["coffee"], n["kitchen"], n["morning"]} <= perceived,
          "precondition: real input named three same-domain sources")
    # 1c grouped them into ONE group (the merge that the field then sees as one source)
    warm_groups = [g for g in r.clustering.groups
                   if {n["coffee"], n["kitchen"], n["morning"]} & set(g.members)]
    check(len(warm_groups) == 1 and
          {n["coffee"], n["kitchen"], n["morning"]} <= set(warm_groups[0].members),
          "1c merged the three same-domain sources into one group")
    # FIXED behavior: no perceived source strands as a singleton coalition
    singletons = [c for c in r.coalitions if c.size() == 1]
    stranded = [c for c in singletons if (set(c.members) & perceived)]
    check(len(stranded) == 0,
          f"no perceived source strands as a singleton basin after 1c "
          f"(stranded: {len(stranded)})")


def test_KNOWN_LIMITATION_single_representative_still_swallows_bridged_domain():
    section("KNOWN LIMITATION: a single-group representative still over-swallows a "
            "bridged domain")
    # HONEST RESIDUAL after 1c, shipped as an asserted-negative that PASSES:
    #
    # On 'coffee in the kitchen this morning' perception names ONLY warm-domain sources, so
    # 1c yields exactly ONE group, whose representative is elected by the locked rule
    # (highest energy, ties on creation_seq asc) = coffee. coffee has a direct road to the
    # work domain (the n=8 coffee->work bridge in _small_mind). With a single source there
    # is exactly one basin, so EVERY node the representative reaches — including the bridged
    # work/code domain — lands in that one coalition. Source-clustering alone cannot keep a
    # bridged, non-perceived domain out of a single-source basin: there is no competing
    # source to draw a seam, and the bridge is too strong (n=8) for the relative flow/cut to
    # sever without tuning a threshold to the test (which is forbidden).
    #
    # This is the §6.1 over-swallow criterion NOT being met on _small_mind. It is recorded
    # honestly here rather than smoothed over. See the delivery report: the full §6.1
    # acceptance (over-swallow excluded) is a SPEC-vs-SUBSTRATE conflict for the PM to
    # resolve (e.g. thin the bridge, re-scope the criterion, or extend 1c's mechanism).
    s, n = _small_mind()
    r = think(s, "coffee in the kitchen this morning")
    # exactly one group (only warm sources perceived) and coffee represents it
    check(len(r.clustering.groups) == 1, "only one source group on this utterance")
    check(r.clustering.groups[0].representative == n["coffee"],
          "the elected representative is coffee (lowest creation_seq among tied energies)")
    thought_members = set(r.thought.members) if r.thought else set()
    over_swallows = n["work"] in thought_members or n["code"] in thought_members
    check(over_swallows,
          "DOCUMENTED: the single-source thought still pulls in the bridged work/code "
          "domain — source-clustering alone does not fix over-swallow here")
    print("      → recorded as a residual limitation: over-swallow persists when the "
          "elected")
    print("        representative bridges to a non-perceived domain (PM decision needed; "
          "see report).")


# ─────────────────────────────────────────────────────────────────────────────
# Six asserted-negative tests (spec §7) — limitations shipped as explicit tests
# ─────────────────────────────────────────────────────────────────────────────

def test_NEGATIVE_clusters_only_perceived_sources_not_whole_graph():
    section("ASSERTED-NEGATIVE #1: 1c clusters ONLY the perceived sources, not the graph")
    s, n = _small_mind()
    p = perceive(s, "coffee in the kitchen this morning")
    clustering = cluster_sources(s, p.sources)
    all_members = set()
    for g in clustering.groups:
        all_members |= set(g.members)
    # every clustered node is a perceived source; non-perceived nodes (work, code, desk...)
    # are NOT in any group, even though they exist in the graph
    check(all_members <= set(p.sources),
          "no node outside the perceived source set appears in any group")
    check(n["work"] not in all_members and n["code"] not in all_members and
          n["desk"] not in all_members,
          "non-perceived graph nodes are not clustered (not whole-graph clustering)")
    check(len(all_members) <= s.node_count(),
          "the clustered set is a subset of the graph, never the whole graph")


def test_NEGATIVE_no_cognitive_claim_membership_is_topological_only():
    section("ASSERTED-NEGATIVE #2: grouping is topological only — no cognitive claim")
    # Two nodes with a strong DIRECT road group together purely because of that road, with
    # no semantic content in common. This documents that 1c asserts a graph-proximity
    # mechanism, NOT that grouped nodes are 'semantically related' (a meaning claim the
    # validator grades against external data, never asserted here).
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    xx = s.add_node("xyzzy", NodeType.CONCEPT)
    qq = s.add_node("quux", NodeType.CONCEPT)
    _worn(s, xx, qq, n=30)                 # a strong road, no shared meaning
    p = perceive(s, "xyzzy quux")
    clustering = cluster_sources(s, p.sources)
    check(len(clustering.groups) == 1,
          "two nodes with a strong direct road group together — by topology, not meaning")
    # the converse: identical-looking but UNLINKED nodes do NOT group
    s2 = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    a2 = s2.add_node("xyzzy", NodeType.CONCEPT)
    b2 = s2.add_node("quux", NodeType.CONCEPT)   # no road between them
    p2 = perceive(s2, "xyzzy quux")
    c2 = cluster_sources(s2, p2.sources)
    check(len(c2.groups) == 2,
          "the same two contents with NO road do not group — membership is topological")


def test_NEGATIVE_chaining_is_intentional_and_documented():
    section("ASSERTED-NEGATIVE #3: single-link CHAINING (A-B-C) is intentional")
    # Single-link transitive merging chains A-B-C even when A and C are not DIRECTLY near.
    # Build A-B strong, B-C strong, A-C with NO direct road. All three must end in one
    # group (the chain), documented rather than pretended impossible.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    A = s.add_node("aaa", NodeType.CONCEPT)
    B = s.add_node("bbb", NodeType.CONCEPT)
    C = s.add_node("ccc", NodeType.CONCEPT)
    _worn(s, A, B, n=30); _worn(s, B, C, n=30)   # A-B and B-C linked; A-C NOT
    # precondition: A and C have no direct road (proximity 0)
    check(_pair_proximity(s, A, C) == 0.0, "precondition: A and C are not directly near")
    p = perceive(s, "aaa bbb ccc")
    clustering = cluster_sources(s, p.sources)
    check(len(clustering.groups) == 1 and
          {A, B, C} <= set(clustering.groups[0].members),
          "A, B, C chain into one group though A-C are not directly near (single-link)")


def test_NEGATIVE_perception_surface_and_field_signature_untouched():
    section("ASSERTED-NEGATIVE #4: perceive()/Perception and field-builder signature "
            "are unchanged")
    import inspect
    from nous_perceive import perceive as _perceive, Perception
    from nous_field import build_activation_field as _baf
    # perceive's signature is unchanged (store, utterance, *, source_energy)
    psig = inspect.signature(_perceive)
    check(list(psig.parameters.keys()) == ["store", "utterance", "source_energy"],
          "perceive() signature is unchanged")
    # Perception's fields are unchanged
    check(set(Perception.__dataclass_fields__.keys()) ==
          {"sources", "matched_terms", "utterance"},
          "Perception's fields are unchanged")
    # build_activation_field's signature is unchanged
    fsig = inspect.signature(_baf)
    check(list(fsig.parameters.keys()) ==
          ["store", "sources", "energy", "decay_per_hop", "floor", "hop_budget",
           "source_energies"],
          "build_activation_field() signature is unchanged")
    # and perceive still returns a Perception with exactly those fields (behavioral)
    s, n = _small_mind()
    p = _perceive(s, "coffee")
    check(isinstance(p, Perception) and hasattr(p, "sources") and
          hasattr(p, "matched_terms") and hasattr(p, "utterance"),
          "perceive() still returns the unchanged Perception shape")


def test_NEGATIVE_no_broadcast_no_feedback_into_next_cycle():
    section("ASSERTED-NEGATIVE #5: 1c does NOT broadcast/feed back into a next cycle")
    # 1c is pure pre-processing. Running think() must not leave any trace that biases a
    # later think() — there is no broadcast (that is 1d). We assert two cycles on the same
    # input produce identical clusterings AND that the store is byte-identical across them
    # (no feedback written anywhere).
    s, n = _small_mind()
    before = {rid: (s.get_road(rid, apply_decay=False).strength,
                    s.get_road(rid, apply_decay=False).traversal_count)
              for rid in s.all_road_ids()}
    r1 = think(s, "coffee in the kitchen this morning")
    r2 = think(s, "coffee in the kitchen this morning")
    after = {rid: (s.get_road(rid, apply_decay=False).strength,
                   s.get_road(rid, apply_decay=False).traversal_count)
             for rid in s.all_road_ids()}
    check(before == after, "no state written between/after cycles (no broadcast/feedback)")
    part1 = sorted(tuple(sorted(g.members)) for g in r1.clustering.groups)
    part2 = sorted(tuple(sorted(g.members)) for g in r2.clustering.groups)
    check(part1 == part2,
          "the second cycle's clustering is identical — the first did not bias it")


def test_NEGATIVE_threshold_is_uncalibrated_design_constant():
    section("ASSERTED-NEGATIVE #6: the relative threshold is an uncalibrated design "
            "constant")
    # The threshold is a documented relative design constant, not tuned against external
    # data. We assert it is exposed as a module-level constant with a relative (fractional)
    # value in (0, 1], and that it is RELATIVE (passing a different fraction changes the
    # cut), so nothing downstream may depend on a calibrated magnitude.
    check(0.0 < DEFAULT_PROXIMITY_FRACTION <= 1.0,
          "DEFAULT_PROXIMITY_FRACTION is a fraction in (0, 1] (relative, not absolute)")
    # demonstrate relativity: a chain that merges at the default fraction can be split by a
    # stricter fraction — proving the constant governs a relative cut, and is not magic.
    s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
    A = s.add_node("aaa", NodeType.CONCEPT)
    B = s.add_node("bbb", NodeType.CONCEPT)
    C = s.add_node("ccc", NodeType.CONCEPT)
    _worn(s, A, B, n=30)        # strong A-B
    _worn(s, B, C, n=3)         # weak B-C (lower strength → lower proximity)
    p = perceive(s, "aaa bbb ccc")
    loose = cluster_sources(s, p.sources, proximity_fraction=0.05)  # keep weak edge too
    strict = cluster_sources(s, p.sources, proximity_fraction=0.95)  # cut the weak edge
    check(len(loose.groups) < len(strict.groups),
          "a stricter relative fraction cuts more edges → more groups (threshold is "
          "relative, uncalibrated)")


def run_all():
    print("=" * 70)
    print("  NOUS SOURCE-CLUSTERING (1c) — TEST SUITE")
    print("=" * 70)
    for t in [
        # loop-closed grouping behavior
        test_same_domain_sources_merge_into_one_group_loop_closed,
        test_separate_domains_form_separate_groups_loop_closed,
        test_representative_is_highest_energy_then_creation_seq,
        test_group_seeds_feed_representatives_only,
        test_think_seeds_field_from_group_representatives,
        # substrate bar
        test_clustering_is_pure_read,
        test_clustering_preserves_integrity,
        test_scale_invariance_of_partition,
        test_determinism_across_hash_seeds,
        # §6.1 mechanism (the part 1c fixes) + the honest residual
        test_clustering_no_longer_strands_same_domain_sources,
        test_KNOWN_LIMITATION_single_representative_still_swallows_bridged_domain,
        # six asserted-negatives (spec §7)
        test_NEGATIVE_clusters_only_perceived_sources_not_whole_graph,
        test_NEGATIVE_no_cognitive_claim_membership_is_topological_only,
        test_NEGATIVE_chaining_is_intentional_and_documented,
        test_NEGATIVE_perception_surface_and_field_signature_untouched,
        test_NEGATIVE_no_broadcast_no_feedback_into_next_cycle,
        test_NEGATIVE_threshold_is_uncalibrated_design_constant,
    ]:
        t()
    print("\n" + "=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    print("=" * 70)
    return _failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run_all() else 1)
