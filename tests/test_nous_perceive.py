"""
Test suite for perception and the end-to-end slice.

The discipline this round, learned the hard way five times: do NOT validate on inputs
invented to make the behavior correct. Here that means feeding TEXT and letting
perception decide the sources — never hand-placing sources — and including inputs that
were NOT designed to produce a clean result, so the tests record what the system
actually does rather than what I hoped.

These tests assert two kinds of thing:
  1. The pipeline mechanics: perception matches content; the slice runs end-to-end;
     it is pure and deterministic. (Durable, like the substrate tests.)
  2. The HONEST behavioral finding: on real (clustered/overlapping) perceptual input,
     the multi-source field does NOT yet produce clean coalitions. This is asserted as
     a known limitation, not hidden — so a future fix has a test that currently
     documents the problem and would flip when it is solved.

Run directly:
    python3 test_nous_perceive.py
"""

from nous_store import SubstrateStore, Clock, NodeType
from nous_perceive import perceive, think, _tokenize

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
    """A small store with two loose domains and some cross-linking."""
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


# ── pipeline mechanics (durable) ─────────────────────────────────────────────

def test_tokenize_filters_short_words():
    section("tokenize: lowercases, keeps content words, drops short ones")
    toks = _tokenize("I made Coffee in the kitchen")
    check("coffee" in toks and "kitchen" in toks, "content words kept")
    check("in" not in toks and "i" not in toks, "short words dropped")


def test_perceive_matches_content_from_input():
    section("perceive: input tokens select matching nodes as sources (input-driven)")
    s, n = _small_mind()
    p = perceive(s, "I want some coffee")
    check(n["coffee"] in p.sources, "the named node 'coffee' became a source")
    check(n["work"] not in p.sources, "an unrelated node did not")
    # the input decided this — not a hand-placed choice
    check("coffee" in p.matched_terms.get(n["coffee"], []),
          "the matching token is recorded")


def test_perceive_nothing_on_no_match():
    section("perceive: input matching nothing yields no sources")
    s, n = _small_mind()
    p = perceive(s, "elephants and submarines")
    check(p.sources == {}, "no matching content → no sources")
    r = think(s, "elephants and submarines")
    check(r.thought is None and r.coalitions == [],
          "the slice yields no thought when nothing is perceived")


def test_energy_scales_with_match_count():
    section("perceive: a node named by more tokens is a stronger source")
    s = SubstrateStore(clock=Clock(simulated=True))
    one = s.add_node("coffee", NodeType.ENTITY)
    two = s.add_node("morning coffee ritual", NodeType.CONCEPT)
    p = perceive(s, "morning coffee")
    check(p.sources[two] > p.sources[one],
          "node matching two tokens gets more energy than node matching one")


def test_slice_runs_end_to_end_on_real_input():
    section("the slice runs end-to-end: text → sources → field → coalitions → thought")
    s, n = _small_mind()
    r = think(s, "back to work, the deadline is close")
    check(r.perception.sources != {}, "perceived sources from the text")
    check(r.field_ is not None, "built an activation field from those sources")
    check(len(r.coalitions) >= 1, "formed at least one coalition")
    check(r.thought is not None, "selected a strongest coalition as the thought")
    # the work-related sources should at least place work in the thought's vicinity
    all_members = set()
    for c in r.coalitions:
        all_members |= set(c.members)
    check(n["work"] in all_members, "work (named in the input) is somewhere in the result")


def test_slice_is_pure_read():
    section("the end-to-end slice mutates NOTHING (pure read)")
    s, n = _small_mind()
    before = {rid: (s.get_road(rid, apply_decay=False).strength,
                    s.get_road(rid, apply_decay=False).traversal_count)
              for rid in s.all_road_ids()}
    for _ in range(3):
        think(s, "coffee in the kitchen this morning")
        think(s, "work and the deadline")
    after = {rid: (s.get_road(rid, apply_decay=False).strength,
                   s.get_road(rid, apply_decay=False).traversal_count)
             for rid in s.all_road_ids()}
    check(before == after, "three end-to-end passes changed no road")


# ── the HONEST behavioral finding (documents a real limitation) ──────────────

def test_KNOWN_LIMITATION_clustered_sources_give_poor_basins():
    section("KNOWN LIMITATION: clustered real-input sources do NOT yield clean basins")
    # When real perception lights up several nodes in the SAME domain (which it does —
    # "coffee in the kitchen this morning" names three warm-domain nodes), the
    # multi-source field does not produce one-coalition-per-concern. Basins collapse:
    # one source swallows most nodes, its same-domain siblings strand as singletons.
    # This is the same structural issue the review exposed (multiple sources in one
    # community), now arising naturally from real input. We ASSERT the problem exists,
    # so this test documents it honestly and will FLIP when source-grouping is fixed.
    s, n = _small_mind()
    r = think(s, "coffee in the kitchen this morning")
    # all three warm-domain terms were perceived as separate sources
    perceived = set(r.perception.sources)
    check({n["coffee"], n["kitchen"], n["morning"]} <= perceived,
          "real input named three sources in the same (warm) domain")
    # the failure signature: the strongest coalition over-swallows (pulls in the
    # work domain), AND some perceived sources strand as singletons.
    thought_members = set(r.thought.members) if r.thought else set()
    over_swallows = n["work"] in thought_members or n["code"] in thought_members
    singletons = [c for c in r.coalitions if c.size() == 1]
    has_stranded_source = any(
        (set(c.members) & perceived) for c in singletons
    )
    check(over_swallows,
          "DOCUMENTED: the 'thought' over-swallows across domains (work pulled in)")
    check(has_stranded_source,
          "DOCUMENTED: a perceived same-domain source strands as a singleton basin")
    print("      → recorded as a known limitation: clustered sources need grouping/")
    print("        merging before basins are meaningful (a real next-step problem).")


# ── determinism (established discipline) ─────────────────────────────────────

def test_slice_determinism_across_hash_seeds():
    section("ADVERSARIAL determinism: end-to-end result identical across hash seeds")
    import subprocess, sys, os, textwrap
    probe = textwrap.dedent('''
        from nous_store import SubstrateStore, Clock, NodeType
        from nous_perceive import think
        s = SubstrateStore(clock=Clock(simulated=True, start=0.0))
        def add(l, t=NodeType.CONCEPT): return s.add_node(l, t)
        coffee=add("coffee",NodeType.ENTITY); warmth=add("warmth",NodeType.SENSATION)
        morning=add("morning routine"); cozy=add("cozy feeling"); kitchen=add("kitchen",NodeType.ENTITY)
        work=add("work"); desk=add("desk",NodeType.ENTITY); deadline=add("deadline pressure"); code=add("writing code")
        def w(a,b,n):
            for _ in range(n): s.traverse(a,b)
        w(coffee,warmth,30); w(coffee,morning,28); w(morning,cozy,26); w(coffee,kitchen,24); w(kitchen,morning,20)
        w(work,desk,30); w(work,deadline,28); w(work,code,26); w(desk,code,22); w(coffee,work,8)
        r = think(s, "coffee in the kitchen this morning")
        out = []
        for c in r.coalitions:
            out.append((tuple(sorted(s.get_node(m).content for m in c.members)),
                        round(c.strength, 9),
                        s.get_node(c.representative()).content))
        print(repr((out, s.get_node(r.thought.representative()).content if r.thought else None)))
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
          f"end-to-end result identical across 6 hash seeds (distinct: {len(set(outs))})")


def run_all():
    print("=" * 70)
    print("  NOUS PERCEPTION + END-TO-END SLICE — TEST SUITE")
    print("=" * 70)
    for t in [
        test_tokenize_filters_short_words,
        test_perceive_matches_content_from_input,
        test_perceive_nothing_on_no_match,
        test_energy_scales_with_match_count,
        test_slice_runs_end_to_end_on_real_input,
        test_slice_is_pure_read,
        test_KNOWN_LIMITATION_clustered_sources_give_poor_basins,
        test_slice_determinism_across_hash_seeds,
    ]:
        t()
    print("\n" + "=" * 70)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    print("=" * 70)
    return _failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if run_all() else 1)
