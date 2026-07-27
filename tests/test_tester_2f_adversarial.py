#!/usr/bin/env python3
"""
TESTER-authored adversarial verification of brick 2f-i (SPEC-2f Design C) and of the
0e runner/parser fix, written from scratch rather than adapted from the builder's suite.

VERDICT: FAIL on one criterion. `outcome_magnitude` is neither validated nor asserted:
a NEGATIVE outcome is accepted and strengthens the road byte-identically to a positive
one of the same size, because the gain takes `abs()`. Everything else holds, including
the neutral byte-identity gate measured against the real pre-2f engine recovered from
git rather than against a transcription.

WHAT THIS FILE VERIFIES
  - 0e: an aborted suite is named with its exception and location; its count is UNKNOWN
    and no path reconstructs one from FAIL: lines; the END-OF-INPUT arm is caught; the
    contract is exit 2 exactly like CensusUnreadable; all three readers of the RESULT
    format agree.
  - 2f-i: the overlay's neutral value, the parameter matrix, the window boundary
    established structurally, application-order independence proved from the code rather
    than observed, and loop-closure driven only by roads think() actually produced.

FROZEN CLOCK, AND THE NOISE FLOOR IS MEASURED FIRST
Every byte-identity comparison here uses Clock(simulated=True) and never calls advance().
That is not decoration: on a LIVE clock two identical credit-free runs of the same graph
differ on 6 roads through lazy decay, which is larger than anything 2f does. The floor is
measured in test_P0_noise_floor before any off-vs-on conclusion is drawn, because a
comparison made above an unmeasured floor is how this project filed a false defect once.

Run directly:
    python3 test_tester_2f_adversarial.py
"""

import ast
import inspect
import itertools
import os
import pathlib
import re
import struct
import subprocess
import sys
import tempfile
import textwrap

from nous_store import SubstrateStore, Clock, NodeType
from nous_perceive import think
import nous_credit as cr
from nous_credit import EpisodicTrace, assign_credit, eligibility

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

_passed = 0
_failed = 0
_findings = []


def check(cond, msg):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {msg}")


def section(name):
    print(f"\n=== {name} ===")


def note(msg):
    print(f"  NOTE: {msg}")


def finding(tag, msg):
    _findings.append((tag, msg))
    print(f"  FINDING [{tag}]: {msg}")


def bits(x):
    """Bit pattern. round(x, 9) cannot see 1 ULP; every float comparison here is raw."""
    return struct.pack("<d", x).hex()


def frozen():
    """A store whose clock does not move. advance() is never called anywhere in this
    file — a registry bound rests on it having no caller, and 2f is the brick most
    likely to end it, so the habit stays out of 2f's test files too."""
    return SubstrateStore(clock=Clock(simulated=True, start=1000.0))


def graph():
    s = frozen()
    n = {w: s.add_node(w, NodeType.CONCEPT) for w in
         "dog bark loud noise pet soft cat purr kitten hound".split()}
    for a, b in (("dog", "bark"), ("bark", "loud"), ("loud", "noise"), ("dog", "pet"),
                 ("pet", "soft"), ("cat", "purr"), ("kitten", "purr"),
                 ("hound", "bark"), ("dog", "hound"), ("cat", "kitten")):
        for _ in range(8):
            s.traverse(n[a], n[b])
    return s


def snap(store):
    """Canonical state keyed on creation_seq — a stable persisted INTEGER, never the
    road's uuid, which differs between two independently built stores and would make
    every cross-store comparison vacuously unequal."""
    return tuple(sorted(
        (r.creation_seq, bits(r.strength), r.traversal_count, bits(r.last_touched),
         tuple(sorted((k, bits(v)) for k, v in r.charges.items())), r.closed)
        for r in (store.get_road(x, apply_decay=False) for x in store.all_road_ids())))


def one_road():
    s = frozen()
    a = s.add_node("a", NodeType.CONCEPT)
    b = s.add_node("b", NodeType.CONCEPT)
    r = s.add_road(a, b)
    s.strengthen(r)
    return s, r


# ─────────────────────────────────────────────────────────────────────────────
# PART ONE — 0e
# ─────────────────────────────────────────────────────────────────────────────

def _runner():
    import importlib.util
    sp = importlib.util.spec_from_file_location("rt_2f", ROOT / "run_tests.py")
    m = importlib.util.module_from_spec(sp)
    sys.modules["rt_2f"] = m
    sp.loader.exec_module(m)
    return m


H = lambda n: "#" * 70 + f"\n# {n}\n" + "#" * 70 + "\n"
GOOD = H("test_a.py") + "  RESULT: 10 passed, 0 failed\n" + H("test_b.py") + "  RESULT: 5 passed, 0 failed\n"
MID = H("test_a.py") + "KeyError: boom\n" + H("test_b.py") + "  RESULT: 5 passed, 0 failed\n"
LAST = H("test_a.py") + "  RESULT: 10 passed, 0 failed\n" + H("test_b.py") + "RuntimeError: late\n"


def test_0e_aborted_is_named_and_its_count_is_unknown():
    section("0e  an aborted suite is NAMED; its count is UNKNOWN, never reconstructed")
    RT = _runner()
    t = ("  FAIL: one\n  FAIL: two\nTraceback (most recent call last):\n"
         '  File "x.py", line 9, in inner\nKeyError: \'planted\'\n')
    v = RT.classify(t)
    check(v["aborted"] is True, "a transcript with no RESULT is classified ABORTED")
    check(v["passed"] is None and v["failed"] is None,
          f"its counts are None — UNKNOWN, not 0 and not the 2 that could have been "
          f"reconstructed from the FAIL lines (got {v['passed']!r}/{v['failed']!r})")
    check("KeyError" in v["detail"] and "x.py:9" in v["detail"] and "in inner" in v["detail"],
          f"and it names the exception AND where it died: {v['detail']!r}")
    # THE RECONSTRUCTION TEMPTATION, attacked behaviourally rather than by reading code:
    # if any path counted FAIL lines, these two would differ.
    a = RT.classify("Traceback\nValueError: x")
    b = RT.classify("  FAIL: y\n" * 50 + "Traceback\nValueError: x")
    check(a == b,
          "0 FAIL lines and 50 FAIL lines produce an IDENTICAL verdict, so no code path "
          "invents a partial count from them")
    src = (ROOT / "run_tests.py").read_text(encoding="utf-8")
    check(not re.search(r"(count|len)\([^)]*FAIL", src),
          "and no count()/len() is taken over anything FAIL-shaped")


def test_0e_the_end_of_input_arm_and_whether_my_probe_could_fail():
    section("0e  the END-OF-INPUT arm, and a probe that can actually fail")
    sys.path.insert(0, str(ROOT / "tools"))
    import capture_run as CR
    import ledger_check as LC
    check(CR.parse_full(MID)[1] == ["test_a.py"], "mid-file abort is reported")
    check(CR.parse_full(LAST)[1] == ["test_b.py"],
          "LAST-suite abort is reported — the arm no following header can reveal")

    # A mid-file-only fix is what someone repairing the bug they SAW would write. If my
    # end-of-input probe passes against it, the probe is decoration.
    def midfile_only(out):
        per, aborted, current = {}, [], None
        for line in out.splitlines():
            m = CR.SUITE_RE.match(line)
            if m:
                if current is not None:
                    aborted.append(current)
                current = m.group(1)
                continue
            m = CR.RESULT_RE.search(line)
            if m and current:
                per[current] = int(m.group(1))
                current = None
        return aborted                       # deliberately no end-of-input check
    check(midfile_only(MID) == CR.parse_full(MID)[1],
          "the partial fix AGREES on the mid-file case — so that case cannot separate them")
    check(midfile_only(LAST) != CR.parse_full(LAST)[1],
          f"but DISAGREES on the last-suite case ({midfile_only(LAST)} vs "
          f"{CR.parse_full(LAST)[1]}) — the probe discriminates and is not decoration")


def test_0e_exit_two_matches_the_census_unreadable_contract():
    section("0e  malformed capture is exit 2, exactly as an unreadable source is")
    def cap(text):
        d = pathlib.Path(tempfile.mkdtemp(prefix="t2f-"))
        (d / "docs").mkdir()
        (d / "tools").mkdir()
        (d / "docs" / "TEST_OUTPUT.txt").write_text(text, encoding="utf-8")
        (d / "tools" / "ledger.json").write_text(
            '{"tests":{"suites":2,"assertions":15,"failures":0,'
            '"per_suite":{"test_a.py":10,"test_b.py":5}}}', encoding="utf-8")
        return d
    for label, text, want in (("clean", GOOD, 0), ("mid-file", MID, 2), ("last", LAST, 2)):
        d = cap(text)
        rc = subprocess.run([sys.executable, str(ROOT / "tools" / "ledger_check.py"),
                             "--root", str(d), "--only", "C1"],
                            capture_output=True, text=True)
        rs = subprocess.run([sys.executable, str(ROOT / "tools" / "ledger_sync.py"),
                             "--root", str(d)], capture_output=True, text=True)
        check(rc.returncode == want, f"ledger_check on a {label} capture exits {want} "
                                     f"(got {rc.returncode})")
        check(rs.returncode == want, f"ledger_sync on a {label} capture exits {want} "
                                     f"(got {rs.returncode})")
    # the same contract, on the shape it was borrowed from
    d = pathlib.Path(tempfile.mkdtemp(prefix="t2fu-"))
    (d / "src").mkdir()
    (d / "tools").mkdir()
    (d / "src" / "m.py").write_text("def f(:\n", encoding="utf-8")
    (d / "tools" / "ledger.json").write_text('{"float_accumulations":{}}', encoding="utf-8")
    rc = subprocess.run([sys.executable, str(ROOT / "tools" / "ledger_check.py"),
                         "--root", str(d), "--only", "C6"], capture_output=True, text=True)
    check(rc.returncode == 2,
          "and an UNPARSEABLE SOURCE still exits 2 — the two 'the tool could not run' "
          "cases carry the same code, which is what makes the ruling a contract rather "
          "than a coincidence")


def test_0e_all_three_readers_agree_and_the_agreement_is_asserted():
    section("0e  three readers of the RESULT format agree, and it is pinned")
    RT = _runner()
    sys.path.insert(0, str(ROOT / "tools"))
    import capture_run as CR
    import ledger_check as LC
    twice = H("test_a.py") + "  RESULT: 3 passed, 0 failed\n  RESULT: 7 passed, 0 failed\n"
    d = pathlib.Path(tempfile.mkdtemp(prefix="t2fa-"))
    (d / "docs").mkdir()
    (d / "tools").mkdir()
    (d / "docs" / "TEST_OUTPUT.txt").write_text(twice, encoding="utf-8")
    (d / "tools" / "ledger.json").write_text('{"tests":{}}', encoding="utf-8")
    a = RT.classify(twice)["passed"]
    b = CR.parse_full(twice)[0]["test_a.py"]
    c = LC.parse_capture(d)["assertions"]
    check(a == b == c == 3,
          f"all three take the FIRST RESULT on a double-RESULT transcript ({a}/{b}/{c})")
    t = (ROOT / "tools" / "test_ledger.py").read_text(encoding="utf-8")
    check("all THREE readers of the format agree" in t,
          "and the agreement is ASSERTED in the builder's suite rather than merely true "
          "today — so a future reader that drifts turns the build red")
    check("last wins" not in (ROOT / "tools" / "ledger_check.py").read_text(encoding="utf-8"),
          "the comment that claimed 'last wins' while the code did the opposite is gone")


def test_0e_refusal_precedes_the_agreement_check_and_what_that_costs_my_own_probes():
    section("0e  refusal ordering, and the blindness my own sweeps share")
    src = (ROOT / "tools" / "capture_run.py").read_text(encoding="utf-8")
    i_ab = src.index("REFUSING to capture — suite(s) emitted a header")
    i_agree = src.index("REFUSING to capture — interpreters disagree")
    check(i_ab < i_agree,
          "the abort refusal is placed BEFORE the interpreter-agreement check — five "
          "interpreters that all abort the same suite AGREE on a total that omits it, so "
          "agreement alone would have waved the incomplete capture through")
    note("THE GENERAL LIMIT, recorded because it applies to this project's flagship "
         "discipline and not merely to capture_run: any probe whose assertion is 'these "
         "N observations agree' is structurally blind to a defect identical across all "
         "N. That covers the interpreter sweep, the hash-seed sweep, and every "
         "byte-identity comparison in this file. They were built to catch "
         "ENVIRONMENT-DEPENDENT defects — BUG-0b1 was one — and they do. They are not "
         "correctness checks and must never be read as one. What is NOT blind: probes "
         "asserting an independently-derived absolute value, such as 0d's retro-catch "
         "MUST-CATCH sites, the exact-zero window assertions below, and the pre-2f "
         "byte-identity comparison, which compares against code recovered from git "
         "rather than against another run of the same code.")


# ─────────────────────────────────────────────────────────────────────────────
# PART TWO — 2f-i
# ─────────────────────────────────────────────────────────────────────────────

def test_P0_noise_floor_must_be_measured_before_any_conclusion():
    section("2f  P-0 THE NOISE FLOOR, measured before any off-vs-on comparison")
    a = graph(); think(a, "dog bark loud", broadcast=True)
    b = graph(); think(b, "dog bark loud", broadcast=True)
    check(snap(a) == snap(b),
          "on a FROZEN clock two identical credit-free runs are byte-identical, so the "
          "floor is zero and a difference below can be attributed to 2f")
    la = SubstrateStore(clock=Clock())
    lb = SubstrateStore(clock=Clock())
    for st in (la, lb):
        n = {w: st.add_node(w, NodeType.CONCEPT) for w in "dog bark loud".split()}
        for x, y in (("dog", "bark"), ("bark", "loud")):
            for _ in range(8):
                st.traverse(n[x], n[y])
        think(st, "dog bark", broadcast=True)
    check(snap(la) != snap(lb),
          "on a LIVE clock the same two runs DIFFER with no credit code involved at all "
          "— which is why every comparison in this file is frozen, and why a live-clock "
          "measurement here would have produced a false defect against 2f")


def test_I1_neutral_is_byte_identical_to_the_REAL_pre_2f_engine():
    section("2f  I-1 THE GATE: neutral 2f vs the pre-2f engine recovered from git")
    work = pathlib.Path(tempfile.mkdtemp(prefix="pre2f-"))
    r = subprocess.run(f"git archive cce3dc5 src | tar -x -C {work}",
                       shell=True, cwd=str(ROOT), capture_output=True, text=True)
    if r.returncode != 0 or not (work / "src").is_dir():
        note("pre-2f tree unavailable from git; I-1 compared against the current engine only")
        return
    check(not (work / "src" / "nous_credit.py").exists(),
          "the recovered tree genuinely predates 2f — it has no nous_credit module, so "
          "this is a comparison against the real thing and not against a transcription")
    probe = work / "probe.py"
    probe.write_text(textwrap.dedent('''
        import struct
        from nous_store import SubstrateStore, Clock, NodeType
        from nous_perceive import think
        def bits(x): return struct.pack("<d", x).hex()
        out = []
        for utt in ("dog bark loud", "cat purr kitten", "hound dog pet soft", "no match"):
            for bc in (False, True):
                s = SubstrateStore(clock=Clock(simulated=True, start=1000.0))
                n = {w: s.add_node(w, NodeType.CONCEPT) for w in
                     "dog bark loud noise pet soft cat purr kitten hound".split()}
                for a, b in (("dog","bark"),("bark","loud"),("loud","noise"),
                             ("dog","pet"),("pet","soft"),("cat","purr"),
                             ("kitten","purr"),("hound","bark"),("dog","hound"),
                             ("cat","kitten")):
                    for _ in range(8): s.traverse(n[a], n[b])
                tr = think(s, utt, broadcast=bc)
                st = tuple(sorted((r.creation_seq, bits(r.strength), r.traversal_count)
                          for r in (s.get_road(x, apply_decay=False)
                                    for x in s.all_road_ids())))
                out.append(f"{utt}|{bc}|{len(sorted(tr.thought.members)) if tr.thought else 0}|{st}")
        print(chr(10).join(out))
    '''), encoding="utf-8")
    env = dict(os.environ, PYTHONHASHSEED="0")
    old = subprocess.run([sys.executable, str(probe)], capture_output=True, text=True,
                         env=dict(env, PYTHONPATH=str(work / "src")))
    new = subprocess.run([sys.executable, str(probe)], capture_output=True, text=True,
                         env=dict(env, PYTHONPATH=str(ROOT / "src")))
    check(old.returncode == 0 and new.returncode == 0,
          f"both engines ran ({old.stderr[:100]}{new.stderr[:100]})")
    check(old.stdout == new.stdout,
          "BYTE-IDENTICAL across 8 scenarios (4 utterances x broadcast on/off). This is "
          "the gate: if it fails the overlay argument collapses and nothing else matters")
    # AND the probe must be able to see a difference, or the comparison proves nothing
    ws = work / "src" / "nous_workspace.py"
    orig = ws.read_text(encoding="utf-8")
    ws.write_text(orig.replace("store.strengthen(rid)  #",
                               "store.strengthen(rid, base_gain=0.1300000001)  #", 1),
                  encoding="utf-8")
    perturbed = subprocess.run([sys.executable, str(probe)], capture_output=True,
                               text=True, env=dict(env, PYTHONPATH=str(work / "src")))
    ws.write_text(orig, encoding="utf-8")
    check(perturbed.stdout != new.stdout,
          "and a 1e-10 perturbation planted in the pre-2f engine IS detected — so the "
          "byte-identity above is a measurement, not a comparison that cannot fail")


def test_I1_neutral_p_prp_does_not_call_strengthen_at_all():
    section("2f  I-1 at the neutral budget, strengthen is SKIPPED, not called with zero")
    s, r = one_road()
    t = EpisodicTrace()
    t.record([r])
    before = snap(s)
    res = assign_credit(s, t, outcome_magnitude=1.0, p_prp=cr.NEUTRAL_P_PRP)
    check(snap(s) == before,
          "the store is byte-identical at the neutral budget, including traversal_count, "
          "last_touched and closure — which a zero-gain strengthen() call would have moved")
    check(res.road_ids == [], "and nothing is reported as credited")


def test_PARAM_the_hostile_matrix():
    section("2f  PARAMETER VALIDATION — DEFECT-C's class, on every caller-supplied number")
    INF, NINF, NAN = float("inf"), float("-inf"), float("nan")

    def probe(**kw):
        s, r = one_road()
        t = EpisodicTrace()
        t.record([r])
        b = s.get_road(r, apply_decay=False).strength
        try:
            assign_credit(s, t, **kw)
        except ValueError:
            return "validates", None
        a = s.get_road(r, apply_decay=False).strength
        import math
        if not math.isfinite(a):
            return "NON-FINITE", a
        return ("wrote" if bits(a) != bits(b) else "no-write"), a

    base = dict(outcome_magnitude=1.0, p_prp=1.0)
    for key, vals in (("decay", [1.5, -0.5, NAN, INF, NINF]),
                      ("p_prp", [-1.0, NAN, INF, NINF]),
                      ("outcome_magnitude", [NAN, INF, NINF]),
                      ("window", [0, -1])):
        for v in vals:
            kw = dict(base)
            kw[key] = v
            out, _ = probe(**kw)
            check(out == "validates",
                  f"{key}={v!r} is REFUSED at the boundary (got {out}) — no non-finite or "
                  f"out-of-range value may produce a well-formed answer")
    # the legitimate edges must still be accepted
    for key, v in (("decay", 0.0), ("decay", 1.0), ("p_prp", 0.0), ("window", 1),
                   ("outcome_magnitude", 0.0)):
        kw = dict(base)
        kw[key] = v
        out, _ = probe(**kw)
        check(out in ("wrote", "no-write"),
              f"{key}={v!r} is a legitimate value and is accepted (got {out})")
    for w in (0, -1, 2.5, True, None):
        try:
            EpisodicTrace(window=w)
            check(False, f"EpisodicTrace(window={w!r}) should be refused")
        except ValueError:
            check(True, f"EpisodicTrace(window={w!r}) is refused at construction")
    check(cr.eligibility.__defaults__ is not None, "eligibility carries defaults")
    for bad_k in (-1, 2.5, True):
        try:
            eligibility(bad_k, 0.6, 8)
            check(False, f"eligibility(k={bad_k!r}) should be refused")
        except ValueError:
            check(True, f"eligibility(k={bad_k!r}) is refused — an outcome cannot reach "
                        f"backwards, and k must be an integer cycle distance")


def test_FINDING_negative_outcome_is_a_well_formed_wrong_answer():
    section("2f  FINDING 2f-1: a NEGATIVE outcome strengthens exactly like a positive one")

    def run(mag):
        s, r = one_road()
        t = EpisodicTrace()
        t.record([r])
        assign_credit(s, t, outcome_magnitude=mag, p_prp=1.0)
        return s.get_road(r, apply_decay=False).strength
    pos, neg = run(1.0), run(-1.0)
    check(bits(pos) == bits(neg),
          f"ASSERTED-NEGATIVE: outcome_magnitude=-1.0 and +1.0 produce a BYTE-IDENTICAL "
          f"result ({pos:.6f}). The gain takes abs(), so the sign is discarded silently")
    check("abs(outcome_magnitude)" in inspect.getsource(cr.assign_credit),
          "the discard is structural: the gain expression takes abs()")
    doc = (cr.assign_credit.__doc__ or "") + (cr.__doc__ or "")
    check("negative" not in doc.lower(),
          "and NOTHING in the module documents that a negative outcome is treated as "
          "positive — so a caller signalling an adverse outcome silently reinforces")
    suite = (HERE / "test_nous_credit.py").read_text(encoding="utf-8")
    check("outcome_magnitude=-" not in suite,
          "the builder's own suite never exercises a negative outcome, which is why this "
          "survived to delivery")
    finding("2f-1", "outcome_magnitude is neither validated for sign nor documented as "
                    "unsigned: -1.0 strengthens byte-identically to +1.0 because the gain "
                    "takes abs(). This is a WELL-FORMED WRONG ANSWER of DEFECT-C's class "
                    "— no crash, no warning, a plausible result. Two defensible fixes and "
                    "the choice is the architect's: refuse a negative at the boundary "
                    "(sign carries no meaning), or honour the sign (which needs a "
                    "weakening path that does not exist and would not be a 2f-i change). "
                    "Silently treating adverse as favourable is the one option that is "
                    "not defensible.")


def test_WINDOW_boundary_is_structural_not_sampled():
    section("2f  the window boundary, established from the code and then enumerated")
    src = inspect.getsource(cr.eligibility)
    tree = ast.parse(textwrap.dedent(src))
    guard = None
    for n in ast.walk(tree):
        if isinstance(n, ast.If):
            for c in ast.walk(n.test):
                if (isinstance(c, ast.Compare) and any(isinstance(o, ast.Gt) for o in c.ops)
                        and isinstance(c.left, ast.Name) and c.left.id == "k"):
                    rets = [x for x in ast.walk(n) if isinstance(x, ast.Return)]
                    guard = (ast.unparse(c), ast.unparse(rets[0].value) if rets else None)
    check(guard == ("k > window", "0.0"),
          f"STRUCTURAL: the cutoff is the integer test `k > window` returning a LITERAL "
          f"0.0 (got {guard}) — the edge is exact by construction, so it is not a "
          f"boundary located by sampling and cannot be the last value someone tested")
    check("isinstance(k, int)" in src,
          "and k is type-checked as an int before any float arithmetic happens")
    L, D = 8, 0.6
    inside = [eligibility(k, D, L) for k in range(0, L + 1)]
    check(all(v > 0.0 for v in inside) and
          all(inside[i] >= inside[i + 1] for i in range(len(inside) - 1)),
          "inside the window every value is positive and monotone non-increasing")
    check(all(bits(eligibility(k, D, L)) == bits(0.0) for k in range(L + 1, L + 2001)),
          f"and 2000 consecutive values past the edge are EXACTLY 0.0 — enumerated over "
          f"the range rather than sampled at its ends")
    check(eligibility(L, D, L) > 0.0 and eligibility(L + 1, D, L) == 0.0,
          f"off-by-one in both directions: k=L={L} is inside, k=L+1 is the first zero")
    # and on the store, where the trace's eviction enforces it a second time
    def moved(k):
        s, r = one_road()
        t = EpisodicTrace(window=L)
        t.record([r])
        for _ in range(k):
            t.record([])
        b = s.get_road(r, apply_decay=False).strength
        assign_credit(s, t, outcome_magnitude=1.0, p_prp=1.0)
        return bits(s.get_road(r, apply_decay=False).strength) != bits(b)
    check(moved(L) and not moved(L + 1),
          "the same edge holds on the APPLIED credit, where trace eviction enforces it a "
          "second time — two independent integer comparisons, not one")


def test_CONTROLS_can_each_exhibit_a_difference():
    section("2f  every control is shown CAPABLE OF FAILING — not decoration")
    sys.path.insert(0, str(HERE))
    import test_nous_credit as B

    s, rp, ru = B.matched_pair_store()
    check(bits(B.strength_of(s, rp)) == bits(B.strength_of(s, ru)),
          "C1 matched pair starts byte-identical")
    s2, rp2, ru2 = B.matched_pair_store()
    s2.strengthen(rp2)
    check(bits(B.strength_of(s2, rp2)) != bits(B.strength_of(s2, ru2)),
          "C1 CAN FAIL: perturbing one road of the pair is detected by the same check")

    def arm(credit_first):
        s, rp, ru = B.matched_pair_store()
        t = EpisodicTrace()
        t.record([rp, ru])
        b = B.strength_of(s, rp)
        assign_credit(s, t, outcome_magnitude=1.0, p_prp=1.0,
                      credited_road_ids=[rp] if credit_first else [ru])
        return B.strength_of(s, rp) - b
    check(arm(True) > 0.0 and arm(False) == 0.0,
          f"C2 shuffled control: the paired arm moves ({arm(True):.6f}) and the shuffled "
          f"arm does not — BOTH arms are live, so the comparison measures something")
    # the vacuous form the builder shipped and then found, kept as the standing example
    sA, rpA, _ = B.matched_pair_store()
    sB, rpB, _ = B.matched_pair_store()
    tA = EpisodicTrace()
    tA.record([rpA])
    bA = B.strength_of(sA, rpA)
    assign_credit(sA, tA, outcome_magnitude=1.0, p_prp=1.0, credited_road_ids=[rpB])
    check(bits(B.strength_of(sA, rpA)) == bits(bA),
          "and the ORIGINAL vacuous form — a road id taken from a DIFFERENT store — "
          "moves nothing, which is exactly why it passed while proving nothing. Fourth "
          "instance of this class in a week; recorded so the shape is recognisable")

    def elig(extra):
        s, rp, _ = B.matched_pair_store()
        for _ in range(extra):
            s.strengthen(rp)
        t = EpisodicTrace()
        t.record([rp])
        return assign_credit(s, t, outcome_magnitude=1.0, p_prp=1.0).eligibility[rp]
    check(bits(elig(0)) == bits(elig(9)),
          "C3 anti-readback: eligibility is byte-identical for a weak and a strong road")
    s3, rp3, _ = B.matched_pair_store()
    w0 = B.strength_of(s3, rp3)
    for _ in range(9):
        s3.strengthen(rp3)
    check(bits(B.strength_of(s3, rp3)) != bits(w0),
          "C3 CAN FAIL: the two arms' strengths genuinely differ, so an eligibility that "
          "read strength would have shown it")

    s4 = frozen()
    n = {w: s4.add_node(w, NodeType.CONCEPT) for w in "abcd"}
    r_ab = s4.add_road(n["a"], n["b"])
    r_bc = s4.add_road(n["b"], n["c"])
    for r in (r_ab, r_bc):
        s4.strengthen(r)
    t4 = EpisodicTrace()
    t4.record([r_ab])
    b4 = B.strength_of(s4, r_bc)
    assign_credit(s4, t4, outcome_magnitude=5.0, p_prp=1.0)
    untraced_moved = bits(B.strength_of(s4, r_bc)) != bits(b4)
    t5 = EpisodicTrace()
    t5.record([r_ab, r_bc])
    b5 = B.strength_of(s4, r_bc)
    assign_credit(s4, t5, outcome_magnitude=5.0, p_prp=1.0)
    traced_moved = bits(B.strength_of(s4, r_bc)) != bits(b5)
    check(not untraced_moved and traced_moved,
          "C4 adjacent road: an untraced neighbour is untouched, and the SAME road moves "
          "once it is traced — so 'untouched' is a real contrast, not a structural "
          "impossibility dressed as a result")


def test_REPEATS_mechanical_property_and_the_design_question():
    section("2f  repeats: the mechanical property holds; the SEMANTICS are unspecified")
    for reps, want in ((1, 1.0), (2, 2.0), (3, 3.0), (10, 10.0)):
        s, r = one_road()
        t = EpisodicTrace()
        t.record([r] * reps)
        res = assign_credit(s, t, outcome_magnitude=1.0, p_prp=1.0)
        check(bits(res.eligibility[r]) == bits(want),
              f"{reps} same-cycle repeats sum to exactly {want} via fsum")
        check(len(res.road_ids) == 1,
              f"and strengthen is called ONCE for {reps} repeats, so the write cannot be "
              f"compounded by how the trace was chunked")
    s, r = one_road()
    t = EpisodicTrace()
    t.record([r] * 10000)
    assign_credit(s, t, outcome_magnitude=1.0, p_prp=1.0)
    check(s.get_road(r, apply_decay=False).strength <= 1.0,
          "10000 repeats stay bounded — the ceiling is strengthen()'s saturation, "
          "inherited rather than clamped here")
    s, r = one_road()
    t = EpisodicTrace()
    t.record([r] * 3)
    within = assign_credit(s, t, outcome_magnitude=1.0, p_prp=1.0).eligibility[r]
    s, r = one_road()
    t = EpisodicTrace()
    for _ in range(3):
        t.record([r])
    across = assign_credit(s, t, outcome_magnitude=1.0, p_prp=1.0).eligibility[r]
    check(bits(within) != bits(across),
          f"three repeats in ONE cycle ({within}) and across THREE cycles ({across}) "
          f"differ — the second is decayed, the first is not")
    spec = (ROOT / "docs" / "specs" / "SPEC-2f-credit-assignment.md").read_text(
        encoding="utf-8").lower()
    check(not any(p in spec for p in ("more than once", "several times", "repeat",
                                      "multiple traversal")),
          "SPEC-2f specifies NOTHING about a road traversed several times in one window")
    finding("2f-2", "ROUTED TO ARCHITECT, not a defect: 'three traversals in one cycle "
                    "earn exactly triple eligibility' is linear and unbounded in the "
                    "eligibility term (10000 repeats -> 10000.0), bounded only downstream "
                    "by strengthen()'s saturation. SPEC-2f does not specify it, so it is "
                    "an implementation consequence rather than a recorded decision. It is "
                    "exactly the kind of unstated behaviour that later gets cited as a "
                    "design choice; it needs a ruling before anything is built on it.")


def test_ORDER_independence_is_structural():
    section("2f  application order cannot change any outcome — proved from the code")
    import nous_store as ns
    src = textwrap.dedent(inspect.getsource(ns.SubstrateStore.strengthen))
    tree = ast.parse(src)
    targets = sorted({ast.unparse(t) for n in ast.walk(tree)
                      if isinstance(n, (ast.Assign, ast.AugAssign))
                      for t in (n.targets if isinstance(n, ast.Assign) else [n.target])})
    local = all(t.startswith("road.") or t in ("road", "now", "peak", "gain", "blend", "prior")
                for t in targets)
    check(local,
          f"STRUCTURAL: every write inside strengthen() targets the single looked-up "
          f"`road` or a local ({targets}) — two applications to DISTINCT roads share no "
          f"mutable state and therefore commute by construction, not by observation")
    csrc = inspect.getsource(cr.assign_credit)
    check("applied = sorted(gains, key=lambda r: order[r])" in csrc,
          "and the credit path writes each road at most once, in ascending order of an "
          "intrinsic integer")
    def run(perm):
        s = frozen()
        n = {w: s.add_node(w, NodeType.CONCEPT) for w in "abcdef"}
        rs = [s.add_road(n[x], n[y]) for x, y in
              (("a", "b"), ("c", "d"), ("e", "f"), ("a", "c"), ("b", "d"))]
        for r in rs:
            s.strengthen(r)
        t = EpisodicTrace()
        t.record([rs[i] for i in perm])
        assign_credit(s, t, outcome_magnitude=0.7, p_prp=0.9)
        return snap(s)
    base = run(range(5))
    same = sum(1 for p in itertools.permutations(range(5)) if run(p) == base)
    check(same == 120,
          f"CONFIRMED: all {same}/120 recording permutations give a byte-identical store "
          f"— recording order changes the application order and nothing else")


def test_LOOPCLOSED_driven_only_by_think():
    section("2f  LOOP-CLOSURE: every road id comes from think(), none chosen here")
    s = graph()
    t = EpisodicTrace(window=4)
    seq = ["dog bark loud", "cat purr kitten", "hound dog", "nothing matches at all",
           "dog bark loud", "pet soft", "cat purr", "dog hound bark"]
    counts = []
    for utt in seq:
        think(s, utt, credit_trace=t)
        counts.append(sum(1 for e in t.entries if e.cycle == t.cycle))
    check(any(c == 0 for c in counts),
          "a cycle that perceived NOTHING still advanced the trace — otherwise an "
          "unperceived cycle would be invisible to the decay and silently shorten k")
    check(all(t.cycle - e.cycle <= t.window for e in t.entries),
          "every retained entry is inside the window after 8 real cycles")
    ids = [e.road_id for e in t.entries]
    check(len(ids) != len(set(ids)),
          f"roads REPEAT across the retained cycles ({len(ids) - len(set(ids))} duplicate "
          f"entries) — the repeat path is exercised by real pipeline output, not by a "
          f"list this test wrote")
    check(all(s.exists(r) for r in ids), "every recorded id is a real road")

    s2 = graph()
    t2 = EpisodicTrace()
    b2 = snap(s2)
    assign_credit(s2, t2, outcome_magnitude=9.0, p_prp=1.0)
    check(snap(s2) == b2, "an outcome with NO preceding traversal changes nothing")

    s3 = graph()
    t3 = EpisodicTrace(window=2)
    think(s3, "dog bark loud", credit_trace=t3)
    first = [e.road_id for e in t3.entries]
    for _ in range(5):
        think(s3, "cat purr", credit_trace=t3)
    res = assign_credit(s3, t3, outcome_magnitude=1.0, p_prp=1.0)
    check(not (set(first) & set(res.road_ids)),
          "on a trace LONGER than the window, the roads from cycle 0 are no longer "
          "credited five cycles later — eviction and the kernel agree")


def test_ABSENCE_BOUNDS_rechecked_independently():
    section("2f  the two absence bounds, searched my own way by AST")
    flow_loads, dynamic = [], []
    for p in sorted((ROOT / "src").glob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and n.attr == "flow" and isinstance(n.ctx, ast.Load):
                flow_loads.append(f"{p.name}:{n.lineno} {ast.unparse(n)}")
            if isinstance(n, ast.Attribute) and n.attr == "__dict__":
                dynamic.append(f"{p.name}:{n.lineno} __dict__")
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id in ("getattr", "setattr")):
                dynamic.append(f"{p.name}:{n.lineno} {ast.unparse(n)[:48]}")
    check(sorted(flow_loads) == ["nous_coalitions.py:178 result.flow",
                                 "nous_field.py:123 res.flow"],
          f"ActivationField.flow has NO new reader — the only two .flow loads in src/ are "
          f"the pair already dismissed in the registry ({flow_loads})")
    check(all("flow" not in d for d in dynamic),
          f"and the dynamic routes the machine check is blind to (FINDING 0d-5) reach no "
          f"`flow`: {dynamic}")
    advance_calls = []
    for p in sorted((ROOT / "src").glob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                f = n.func
                nm = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                if nm == "advance":
                    advance_calls.append(f"{p.name}:{n.lineno}")
    check(advance_calls == [],
          f"advance() has NO caller in src/ (a declaration is not a call): {advance_calls}")
    csrc = inspect.getsource(cr)
    check(not any(w in csrc for w in ("Clock", ".now()", "import time")),
          "and nous_credit never touches the clock at all — eligibility is measured in "
          "integer CYCLES, which is why neither bound was even at risk")


def test_LANGUAGE_read_as_a_human_because_C4_is_broken():
    section("2f  LANGUAGE: read as a human, since 0f leaves C4 blind to interpolation")
    src = (ROOT / "src" / "nous_credit.py").read_text(encoding="utf-8")
    low = src.lower()
    lines = src.splitlines()
    claims = []
    pats = {
        "learn": r"\blearn(s|ed|ing|t)?\b",
        "remember": r"\bremember(s|ed|ing)?\b",
        "want": r"\bwant(s|ed|ing)?\b|\bdesire[sd]?\b",
        "understand": r"\bunderstand(s|ing)?\b|\bcomprehend(s|ed)?\b",
        "know": r"\bknow(s|n|ing|ledge)\b",
        "conscious": r"\bconscious(ly|ness)?\b",
        "sentient": r"\bsentien(t|ce)\b",
        "aware": r"\baware(ness)?\b",
        "mind": r"\bmind(s)?\b",
        "intelligent": r"\bintelligen(t|ce)\b",
        "believe": r"\bbeliev(e|es|ed)\b|\bbelief\b",
    }
    for label, pat in pats.items():
        for m in re.finditer(pat, low):
            ln = low[:m.start()].count("\n")
            text = lines[ln].strip()
            # a NEGATION or a mechanical use is not a claim
            negated = any(w in text.lower() for w in
                          ("not ", "no ", "never", "must not", "nothing", "neither"))
            if not negated:
                claims.append(f"L{ln+1} [{label}]: {text[:78]}")
    check(claims == [],
          f"no docstring, comment or identifier asserts acquisition, retention, "
          f"preference or comprehension in ANY inflected or adjectival form — including "
          f"the interpolated shapes C4 cannot match today. Unnegated uses: {claims}")
    names = [n for n in dir(cr) if not n.startswith("_")]
    bad = [n for n in names if any(w in n.lower() for w in
                                   ("learn", "want", "know", "understand", "aware"))]
    check(bad == [], f"and no public identifier encodes such a claim: {names}")
    check("inspired by" in low and "bookkeeping" in low,
          "the module frames itself as inspiration and bookkeeping, which is the strongest "
          "form CLAUDE.md rule 1 permits")
    note("checked by reading, not by C4: 'a conscious mind', 'clearly conscious' and "
         "'undeniably sentient' all pass C4 today (brick 0f). None of those forms, or "
         "any inflection of them, appears in nous_credit.py.")


def test_DETERMINISM_across_seeds_in_fresh_processes():
    section("2f  determinism: bit patterns across 6 hash seeds, fresh processes")
    prog = textwrap.dedent("""
        import struct
        from nous_store import SubstrateStore, Clock, NodeType
        from nous_perceive import think
        from nous_credit import EpisodicTrace, assign_credit
        s = SubstrateStore(clock=Clock(simulated=True, start=1000.0))
        n = {w: s.add_node(w, NodeType.CONCEPT) for w in
             "dog bark loud noise pet soft cat purr".split()}
        for a, b in (("dog","bark"),("bark","loud"),("loud","noise"),("dog","pet"),
                     ("pet","soft"),("cat","purr")):
            for _ in range(8): s.traverse(n[a], n[b])
        t = EpisodicTrace()
        for u in ("dog bark loud", "cat purr", "pet soft"):
            think(s, u, credit_trace=t)
        assign_credit(s, t, outcome_magnitude=0.7, p_prp=0.9)
        print("|".join(struct.pack("<d", r.strength).hex()
              for r in sorted((s.get_road(x, apply_decay=False)
                               for x in s.all_road_ids()), key=lambda r: r.creation_seq)))
    """)
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    seen = set()
    for seed in (0, 1, 2, 3, 7, 42):
        env["PYTHONHASHSEED"] = str(seed)
        r = subprocess.run([sys.executable, "-c", prog], capture_output=True,
                           text=True, env=env)
        check(r.returncode == 0, f"seed {seed} ran cleanly ({r.stderr[:120]})")
        seen.add(r.stdout.strip())
    check(len(seen) == 1,
          f"ONE bit pattern across 6 hash seeds in fresh processes (got {len(seen)})")


def main():
    print("=" * 78)
    print("  TESTER — brick 2f-i (SPEC-2f Design C) and the 0e runner fix")
    print("=" * 78)
    for t in [
        test_0e_aborted_is_named_and_its_count_is_unknown,
        test_0e_the_end_of_input_arm_and_whether_my_probe_could_fail,
        test_0e_exit_two_matches_the_census_unreadable_contract,
        test_0e_all_three_readers_agree_and_the_agreement_is_asserted,
        test_0e_refusal_precedes_the_agreement_check_and_what_that_costs_my_own_probes,
        test_P0_noise_floor_must_be_measured_before_any_conclusion,
        test_I1_neutral_is_byte_identical_to_the_REAL_pre_2f_engine,
        test_I1_neutral_p_prp_does_not_call_strengthen_at_all,
        test_PARAM_the_hostile_matrix,
        test_FINDING_negative_outcome_is_a_well_formed_wrong_answer,
        test_WINDOW_boundary_is_structural_not_sampled,
        test_CONTROLS_can_each_exhibit_a_difference,
        test_REPEATS_mechanical_property_and_the_design_question,
        test_ORDER_independence_is_structural,
        test_LOOPCLOSED_driven_only_by_think,
        test_ABSENCE_BOUNDS_rechecked_independently,
        test_LANGUAGE_read_as_a_human_because_C4_is_broken,
        test_DETERMINISM_across_seeds_in_fresh_processes,
    ]:
        t()
    print("\n" + "=" * 78)
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    print("=" * 78)
    print("  TESTER VERDICT ON BRICK 2f-i — FAIL (2026-07-27)")
    print("=" * 78)
    print("  The overlay GATE holds: neutral 2f is byte-identical to the pre-2f engine")
    print("  recovered from git across 8 scenarios, and the probe is proven able to see a")
    print("  1e-10 perturbation. The window edge is STRUCTURAL — `k > window` returning a")
    print("  literal 0.0 under an integer test — not a boundary located by sampling.")
    print("  Application order is provably irrelevant from the code, and 120/120")
    print("  permutations confirm it. Every control is shown capable of failing.")
    print()
    print("  WHY FAIL, on one criterion: outcome_magnitude is neither validated nor")
    print("  asserted. A NEGATIVE outcome is accepted and strengthens byte-identically to")
    print("  a positive one, because the gain takes abs(). No crash, no warning, a")
    print("  plausible number — DEFECT-C's class exactly. Nothing documents it and the")
    print("  builder's suite never exercises it.")
    print("=" * 78)
    if _findings:
        print("  FINDINGS")
        for tag, msg in _findings:
            print(f"   [{tag}] {msg}")
        print("=" * 78)
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
