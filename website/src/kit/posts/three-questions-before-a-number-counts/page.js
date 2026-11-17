/* ===== This post's figures: one family of gates, threads and points ======================
   Every figure is one model (data and geometry, no drawing) and one draw(model, state, palette)
   that returns SVG text: what stays still in 'back' (drawn and glowed once), what moves in
   'front', split into named parts so a part is rewritten only when its own text changes. The kit turns that into the live figure, the still in the HTML, and
   the print, dark and light exports. Colour carries no meaning alone: the strong associate and
   the threads are mint (dashed in print), the checks and the weak associate are periwinkle
   (solid in print). */
(function (P) {
  var S = P.svg;
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function ease(t) { t = clamp(t, 0, 1); return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  function wrap(str, max) {
    var lines = [], cur = '';
    str.split(' ').forEach(function (w) {
      if (cur && (cur + ' ' + w).length > max) { lines.push(cur); cur = w; } else cur = cur ? cur + ' ' + w : w;
    });
    if (cur) lines.push(cur);
    return lines;
  }
  function lines(x, y, list, lh, pal, role, opts) {
    return list.map(function (l, i) { return S.text(x, y + i * lh, l, pal, role, opts); }).join('');
  }
  function assign(a, b) { var o = {}, k; for (k in a) o[k] = a[k]; for (k in b) o[k] = b[k]; return o; }

  /* ---------------------------------------------------------------------------------------
     The pipeline: three tests run toward a graded number through three checks.
     Drawn by the opening (gates).
     'along' is the direction of the run, 'across' separates the tests. */
  var STAGES = ['input', 'mechanism', 'signal'];
  var TESTS = [
    { name: 'Semantic priming', short: 'Priming', reason: 'The external norm is the edge weight.' },
    { name: 'Fan effect', short: 'Fan effect', reason: 'Every out-road receives the full source activation.' },
    { name: 'Interoception', short: 'Interoception', reason: 'Friction stays near zero on CPU-bound work.' }
  ];
  function pt(m, a, c) { return m.orient === 'h' ? [a, c] : [c, a]; }
  function seg(m, a1, c1, a2, c2, pal, role, w, op, dash) {
    return S.path([pt(m, a1, c1), pt(m, a2, c2)], pal, role, w, { opacity: op, dash: dash });
  }
  // a check: a column of short ticks standing across the run, like the teeth of a comb
  function comb(m, g, pal, role, w, op, from, to) {
    var s = '';
    for (var c = from; c <= to + 0.01; c += m.tickGap) {
      var f = m.fade ? clamp((c - from) / m.fade, 0.12, 1) : 1;
      s += seg(m, g - m.tick / 2, c, g + m.tick / 2, c, pal, role, w, op * f);
    }
    return s;
  }
  function combs(m, pal) {
    var s = '';
    m.gates.forEach(function (g) { m.spans.forEach(function (sp) { s += comb(m, g, pal, 'faint', 1, 1, sp[0], sp[1]); }); });
    return s;
  }

  // the bottom of the title in the opening, so the gates never run behind its letters
  function titleClear() {
    var t = document.querySelector('.tq-title'), o = document.querySelector('.tq-open');
    if (!t || !o) return 92;
    return Math.round((t.getBoundingClientRect().bottom - o.getBoundingClientRect().top) / 8) * 8 + 28;
  }
  function heroModel(box, paper) {
    if (box.width < 640) { // a phone: the run goes down the screen
      var W = 390, H = 480, G = [128, 222, 316], C = [72, 195, 318];
      return { key: 'v', view: { w: W, h: H }, orient: 'v', a0: 46, ag: 412, gates: G, rows: C,
        spans: [[14, W - 14]], tick: 12, tickGap: 9,
        lab: {
          tests: TESTS.map(function (t, i) { return [C[i], 26, 'middle', t.short]; }),
          gates: STAGES.map(function (st, i) { return [133, G[i] - 14, 'middle', st]; }),
          graded: [W - 14, 438, 'end', 'graded number'],
          fake: [W / 2, 466, 'middle', 'a number that looked like a result']
        } };
    }
    var w = Math.round(box.width), h = Math.round(box.height);
    var clear = paper ? 92 : titleClear();
    var gap = clamp(Math.min(h * 0.085, (h - 290 - clear) / 2), 44, 80), r0 = h - 220 - 2 * gap - 40, rows = [r0, r0 + gap, r0 + 2 * gap];
    var gates = [w * 0.37, w * 0.575, w * 0.78], ag = w * 0.945, bottom = rows[2] + 52;
    return { key: 'h' + Math.round(w / 32) + 'x' + Math.round(h / 32) + 'c' + clear, view: { w: w, h: h }, orient: 'h', a0: Math.max(16, w * 0.022), ag: ag,
      gates: gates, rows: rows, spans: [[Math.min(clear, rows[0] - 60), bottom]], fade: paper ? 0 : 90, tick: 16, tickGap: 9, bold: true,
      lab: {
        tests: TESTS.map(function (t, i) { return [Math.max(16, w * 0.022), rows[i] - 16, 'start', t.name]; }),
        gates: STAGES.map(function (st, i) { return [gates[i], bottom + 32, 'middle', st]; }),
        graded: [ag, bottom + 32, 'middle', 'graded number'],
        fake: [ag - 16, rows[0] - 40, 'end', 'a number that looked like a result']
      } };
  }

  // where each test's moving point is at time t (0..1 of the run). t is the clock the three runs
  // share (they start one after another); each run goes from rest at its start to rest at its stop
  // on the kit's 'travel' curve, in the same time a constant speed v would take.
  var TRAVEL = P.ease.travel;
  function heads(m, s) {
    var v = (m.ag - m.a0) / 0.5;
    return m.rows.map(function (c, i) {
      var start = 0.06 + i * 0.15, stop = s.unchecked ? m.ag : m.gates[i], T = (stop - m.a0) / v;
      var p = clamp((s.t - start) / T, 0, 1);
      return { a: m.a0 + (stop - m.a0) * TRAVEL(p), started: s.t > start, done: p >= 1, age: s.t - (start + T), stop: stop };
    });
  }
  // the clock at which the second test's point stands at a (the inverse of heads for that row)
  function clockAt(m, s, a) {
    var v = (m.ag - m.a0) / 0.5, stop = s.unchecked ? m.ag : m.gates[1], T = (stop - m.a0) / v;
    if (a <= m.a0 || a >= stop) return 0.21 + (a - m.a0) / v;
    var f = (a - m.a0) / (stop - m.a0), lo = 0, hi = 1;
    for (var k = 0; k < 30; k++) { var mid = (lo + hi) / 2; if (TRAVEL(mid) < f) lo = mid; else hi = mid; }
    return 0.21 + (lo + hi) / 2 * T;
  }
  // one part per test, so a row that has stopped is not rewritten while the others still run
  function drawRun(m, s, pal, hs, dim) {
    var parts = {};
    hs.forEach(function (h, i) {
      var c = m.rows[i], k = dim ? dim(i) : 1, front = '';
      parts['run' + i] = '';
      if (!h.started) return;
      var B = m.bold ? 1.45 : 1;
      front += seg(m, m.a0, c, h.a, c, pal, 'mint', 1.7 * B, 0.95 * k);
      if (!h.done) {
        var p = pt(m, h.a, c);
        front += S.dot(p[0], p[1], 11 * B, pal, 'mint', 0.18 * k) + S.dot(p[0], p[1], 3.4 * B, pal, 'ink', k);
        parts['run' + i] = front;
        return;
      }
      if (s.unchecked) {
        var e = pt(m, m.ag, c);
        front += S.dot(e[0], e[1], 10 * B, pal, 'mint', 0.16 * k) + S.dot(e[0], e[1], 4.2 * B, pal, 'mint', k);
        parts['run' + i] = front;
        return;
      }
      // caught: the check lights around the row, the run ends on a bar across it
      var g = m.gates[i], lit = clamp(h.age / 0.12, 0, 1);
      for (var j = -4; j <= 4; j++) {
        var cc = c + j * m.tickGap, f = (1 - Math.abs(j) / 5) * lit * k;
        if (f > 0.02) front += seg(m, g - m.tick / 2 - 3, cc, g + m.tick / 2 + 3, cc, pal, 'peri', 1.4, f);
      }
      front += seg(m, g, c - 15 * B, g, c + 15 * B, pal, 'peri', 2.2 * B, k);
      var q = pt(m, g, c);
      if (h.age < 0.18) { // a ring opens where the check fires, then is gone before the run ends
        var u = clamp(h.age / 0.18, 0, 1);
        front += S.circle(q[0], q[1], 6 + 34 * B * ease(u), pal, 'peri', 1.2, (1 - u) * 0.9 * k);
      }
      front += S.dot(q[0], q[1], 3.6 * B, pal, 'ink', k);
      parts['run' + i] = front;
    });
    return parts;
  }
  function drawLabels(m, s, pal, hs) {
    var L = m.lab, out = '';
    var big = m.bold ? 17 : 15;
    L.tests.forEach(function (t) { out += S.text(t[0], t[1], t[3], pal, m.bold ? 'ink' : 'soft', { anchor: t[2], size: big }); });
    L.gates.forEach(function (t) { out += S.text(t[0], t[1], t[3], pal, 'soft', { anchor: t[2], size: 15 }); });
    out += S.text(L.graded[0], L.graded[1], L.graded[3], pal, 'quiet', { anchor: L.graded[2], size: 15 });
    var allIn = hs.every(function (h) { return h.done; });
    if (s.unchecked && allIn) out += S.text(L.fake[0], L.fake[1], L.fake[3], pal, 'ink', { anchor: L.fake[2], size: 15 });
    return out;
  }
  function drawPipeStatic(m, pal) {
    var back = combs(m, pal);
    m.rows.forEach(function (c) { back += seg(m, m.a0, c, m.ag, c, pal, 'faint', 1, 0.7); });
    var top = m.spans[0][0], bot = m.spans[m.spans.length - 1][1];
    back += seg(m, m.ag, m.orient === 'h' ? m.rows[0] - 26 : top, m.ag, m.orient === 'h' ? bot : bot, pal, 'quiet', 1, 0.9, '2 6');
    return back;
  }

  var HERO = heroModel({ width: 1440, height: 640 }, true); // the paper copy: the run without the room the title needs
  P.figure({
    id: 'gates', name: 'three-checks-pipeline', title: 'Three tests, three checks',
    caption: 'Three tests run toward a graded number; each is stopped at a different check, and without the checks all three would print one.',
    model: HERO,
    modelFor: function (box) { return heroModel(box, false); },
    initialState: function () { return { t: 0, unchecked: false }; },
    stillState: function () { return { t: 1, unchecked: false }; },
    tick: function (m, s, dt) { return { t: Math.min(1, s.t + dt / 4.2), unchecked: s.unchecked }; },
    settled: function (m, s) { return s.t >= 1; },
    draw: function (m, s, pal) {
      var hs = heads(m, s);
      return { back: drawPipeStatic(m, pal), front: drawRun(m, s, pal, hs), labels: drawLabels(m, s, pal, hs) };
    },
    describe: function (m, s) {
      var hs = heads(m, s), n = hs.filter(function (h) { return h.done; }).length;
      var base = 'Three tests, semantic priming, the fan effect and interoception, run as lines of light toward a graded number through three checks standing across their path: input, mechanism and signal. ';
      if (s.unchecked) return base + 'The checks are taken out: ' + (n === 3 ? 'every test runs through to the end and prints a number that looked like a result.' : 'the tests are running through all three checks toward the end.');
      if (n === 3) return base + 'Priming is stopped at the input, the fan effect at the mechanism, and interoception at the signal. None reaches a graded number.';
      return base + 'The tests are on their way; ' + (n === 0 ? 'none has reached its check yet.' : n === 1 ? 'priming has been stopped at the input.' : 'priming and the fan effect have been stopped.');
    },
    // The story by itself: the three runs are stopped at their checks; with the checks taken out
    // all three run through to a number; with the checks back, each is stopped again.
    sequence: [
      // t is the shared clock and stays 'linear': each point eases itself in heads()
      // each reset (checks out, checks back) is held on its own before the clock runs again
      { dur: 300, tick: false },
      { dur: 2200, tick: false, to: { t: 1 }, ease: 'linear' },
      { dur: 700, tick: false },
      { dur: 650, tick: false, 'do': function () { return { t: 0, unchecked: true }; } },
      { dur: 2200, tick: false, to: { t: 1 }, ease: 'linear' },
      { dur: 700, tick: false },
      { dur: 650, tick: false, 'do': function () { return { t: 0, unchecked: false }; } },
      { dur: 2200, tick: false, to: { t: 1 }, ease: 'linear' },
      { dur: 600, tick: false }
    ],
    keysLabel: 'Left and right arrow keys move through the run; the C key takes the checks out or puts them back.',
    keys: {
      ArrowRight: function (m, s) { return { t: Math.min(1, s.t + 0.04), unchecked: s.unchecked }; },
      ArrowLeft: function (m, s) { return { t: Math.max(0, s.t - 0.04), unchecked: s.unchecked }; },
      c: function (m, s) { return { t: s.t, unchecked: !s.unchecked }; }
    },
    drag: {
      pick: function (m, s, p) { return true; },
      move: function (m, s, p) {
        var a = m.orient === 'h' ? p[0] : p[1];
        return { t: clamp(clockAt(m, s, a), 0, 1), unchecked: s.unchecked };
      }
    }
  });

  /* ---------------------------------------------------------------------------------------
     Question one: association strength becomes edge weight by one fixed map
     (experiments/swow.py): traverse count = min(STRENGTH_CAP, 1 + int(strength * STRENGTH_SCALE)),
     with STRENGTH_SCALE 100 and STRENGTH_CAP 10. Below it, the fallback margin. */
  var SCALE = 100, CAP = 10;
  var R_W = 2 * 296 / 300 - 1, NEEDED = R_W + 0.2; // from the post; drawn as positions, never typed
  function rung(s) { return Math.min(CAP, 1 + Math.floor(s * SCALE + 1e-9)); }
  function ladderModel(box) {
    if (box.width < 640) {
      return { key: 'n', view: { w: 390, h: 720 }, narrow: true, px0: 24, px1: 286, py0: 436, rungH: 31, smax: 0.12, ladX: 346, ladW: 30,
        verdict: [16, 30], wrapAt: 40, strip: { y: 590, x0: 24, x1: 286 } };
    }
    return { key: 'w', view: { w: 1180, h: 720 }, narrow: false, px0: 90, px1: 780, py0: 470, rungH: 37, smax: 0.12, ladX: 990, ladW: 46,
      verdict: [90, 34], wrapAt: 80, strip: { y: 628, x0: 90, x1: 780 } };
  }
  function LX(m, s) { return m.px0 + (s / m.smax) * (m.px1 - m.px0); }
  function LY(m, r) { return m.py0 - r * m.rungH; }
  var LADDER = ladderModel({ width: 1180, height: 720 });
  var STRONG0 = 0.074, WEAK0 = 0.023;
  var ladderPick = "s"; // which associate a drag holds
  function ladderPos(s) { var e = ease(s.t); return { s: lerp(0.004, s.s, e), w: lerp(0.004, s.w, e) }; }
  P.figure({
    id: 'ladder', name: 'one-number-seen-twice', title: 'One number seen twice',
    caption: 'Association strength becomes edge weight by one fixed map, so a pair is weight-blind only when both associates land on the same rung.',
    model: LADDER,
    modelFor: ladderModel,
    initialState: function () { return { s: STRONG0, w: WEAK0, t: 1 }; },
    stillState: function () { return { s: STRONG0, w: WEAK0, t: 1 }; },
    tick: function (m, s, dt) { return assign(s, { t: Math.min(1, s.t + dt / 1.8) }); },
    settled: function (m, s) { return s.t >= 1; },
    draw: function (m, st, pal) {
      var back = '', front = '', labels = '', i;
      // the staircase: strength in, rung out
      var pts = [[LX(m, 0), LY(m, 1)]];
      for (i = 1; i < CAP; i++) { pts.push([LX(m, i / SCALE), LY(m, i)]); pts.push([LX(m, i / SCALE), LY(m, i + 1)]); }
      pts.push([LX(m, m.smax), LY(m, CAP)]);
      back += S.line(m.px0, m.py0, m.px1, m.py0, pal, 'quiet', 1);
      back += S.path(pts, pal, 'ink', 1.5, { opacity: 0.85 });
      // the ladder of edge weights in the graph
      var lx0 = m.ladX - m.ladW / 2, lx1 = m.ladX + m.ladW / 2;
      back += S.line(lx0, LY(m, 0.4), lx0, LY(m, CAP + 0.6), pal, 'quiet', 1);
      back += S.line(lx1, LY(m, 0.4), lx1, LY(m, CAP + 0.6), pal, 'quiet', 1);
      for (i = 1; i <= CAP; i++) back += S.line(lx0, LY(m, i), lx1, LY(m, i), pal, 'faint', 1);
      // the fallback margin, on a scale that ends at complete separation
      var sp = m.strip, sx = function (r) { return sp.x0 + r * (sp.x1 - sp.x0); };
      back += S.line(sp.x0, sp.y, sp.x1, sp.y, pal, 'quiet', 1.2);
      back += S.line(sp.x0, sp.y - 6, sp.x0, sp.y + 6, pal, 'quiet', 1);
      back += S.line(sp.x1, sp.y - 13, sp.x1, sp.y + 13, pal, 'ink', 1.6);
      back += S.path([[sx(R_W), sp.y], [sx(NEEDED) - 8, sp.y]], pal, 'quiet', 1, { dash: '2 5' });
      back += S.dot(sx(R_W), sp.y, 11, pal, 'mint', 0.16) + S.dot(sx(R_W), sp.y, 4.6, pal, 'mint');
      back += S.circle(sx(NEEDED), sp.y, 7, pal, 'peri', 1.5);

      var p = ladderPos(st), rs = rung(p.s), rw = rung(p.w), same = rs === rw;
      var xs = LX(m, p.s), ys = LY(m, rs), xw = LX(m, p.w), yw = LY(m, rw);
      // guides: down to the strength axis, across to the ladder
      front += S.path([[xs, ys], [xs, m.py0]], pal, 'quiet', 1, { dash: '2 5', opacity: 0.9 });
      front += S.path([[xw, yw], [xw, m.py0]], pal, 'quiet', 1, { dash: '2 5', opacity: 0.9 });
      front += S.path([[xs, ys], [lx0 - 6, ys]], pal, 'quiet', 1, { dash: '2 5', opacity: 0.9 });
      if (!same) front += S.path([[xw, yw], [lx0 - 6, yw]], pal, 'quiet', 1, { dash: '2 5', opacity: 0.9 });
      // the rungs the two associates land on
      front += S.line(lx0 - 4, ys - (same ? 3 : 0), lx1 + 4, ys - (same ? 3 : 0), pal, 'mint', 3);
      front += S.line(lx0 - 4, yw + (same ? 3 : 0), lx1 + 4, yw + (same ? 3 : 0), pal, 'peri', 3);
      // the two associates
      front += S.dot(xw, yw, 15, pal, 'peri', 0.16) + S.dot(xw, yw, 6.5, pal, 'peri');
      front += S.dot(xs, ys, 15, pal, 'mint', 0.16) + S.dot(xs, ys, 6.5, pal, 'mint');
      front += S.circle(xs, ys, 10, pal, 'mint', 1.2, 0.8);
      front = { pair: front };

      var fs = m.narrow ? 14 : 15;
      // the strong label sits above its point, the weak one below, so they never collide
      // labels sit where the rising staircase never goes: the strong one above-left, the weak one below-right
      var sl = xs - 18 < m.px0 + 120 ? [xs + 18, 'start'] : [xs - 18, 'end'];
      var wl = xw + 18 > m.px1 - 110 ? [xw - 18, 'end'] : [xw + 18, 'start'];
      labels += S.text(sl[0], ys - 18, 'strong associate', pal, 'ink', { size: fs, anchor: sl[1] });
      labels += S.text(wl[0], yw + 34, 'weak associate', pal, 'ink', { size: fs, anchor: wl[1] });
      labels += S.text(m.px1, m.py0 + 30, 'association strength in the norms', pal, 'soft', { size: fs, anchor: 'end' });
      labels += S.text(m.narrow ? 390 - 10 : m.ladX, LY(m, CAP + 0.6) - 16, 'edge weight', pal, 'soft', { size: fs, anchor: m.narrow ? 'end' : 'middle' });
      if (!m.narrow) labels += S.text(m.ladX, m.py0 + 30, 'one rung per count', pal, 'quiet', { size: 14, anchor: 'middle' });
      var v1 = same ? 'One rung for both: the pair is weight-blind.' : 'Different rungs: the bare weights already order the pair.';
      var v2 = same ? 'The cycle would have to separate them where the weights cannot.' : 'A result in the predicted direction could be this map read back.';
      labels += lines(m.verdict[0], m.verdict[1], wrap(v1, m.wrapAt), 22, pal, 'ink', { size: m.narrow ? 16 : 18, weight: 500 });
      labels += lines(m.verdict[0], m.verdict[1] + (wrap(v1, m.wrapAt).length) * 22 + 2, wrap(v2, m.wrapAt + 6), 20, pal, 'soft', { size: fs });
      // the strip's words
      if (m.narrow) {
        labels += S.text(sp.x0, sp.y - 20, 'what the bare weights already reach', pal, 'soft', { size: 14 });
        labels += S.text(374, sp.y - 44, 'what a pass needed', pal, 'soft', { size: 14, anchor: 'end' });
        labels += S.text(sp.x1, sp.y + 30, 'the scale ends', pal, 'soft', { size: 14, anchor: 'middle' });
        labels += S.text(sp.x0, sp.y + 64, 'separation of strong over weak, from none', pal, 'quiet', { size: 14 });
        labels += S.text(sp.x0, sp.y + 84, 'to complete', pal, 'quiet', { size: 14 });
      } else {
        labels += S.text(sx(R_W) - 16, sp.y - 20, 'what the bare weights already reach', pal, 'soft', { size: 15, anchor: 'end' });
        labels += S.text(sp.x1 + 12, sp.y - 20, 'the scale ends', pal, 'soft', { size: 15 });
        labels += S.text(sx(NEEDED), sp.y + 34, 'what a pass needed', pal, 'soft', { size: 15, anchor: 'middle' });
        labels += S.text(sp.x0, sp.y + 34, 'separation of strong over weak, from none to complete', pal, 'quiet', { size: 14 });
      }
      return { back: back, front: front, labels: labels };
    },
    describe: function (m, st) {
      var p = ladderPos(st), rs = rung(p.s), rw = rung(p.w);
      return 'A staircase maps association strength in the word-association norms to an integer edge weight in the graph. The strong associate sits on rung ' + rs + ' and the weak associate on rung ' + rw + '. ' +
        (rs === rw ? 'They share a rung, so the pair is weight-blind: the cycle would have to separate them where the weights cannot.' : 'They are on different rungs, so the bare weights already order the pair.') +
        ' Below, on a scale of separation that ends at complete, the bare weights already reach almost the end, and the margin a pass needed lies beyond the end of the scale.';
    },
    // The story by itself: the pair lands on two rungs; the weak associate climbs until both share a
    // rung (weight-blind), then goes back to where most pairs are, ordered by the weights alone.
    sequence: [
      { dur: 500, tick: false },
      { dur: 2500, tick: false, to: { w: 0.0715 }, ease: 'travel' },
      { dur: 1700, tick: false },
      { dur: 2100, tick: false, to: { w: WEAK0 }, ease: 'travel' },
      { dur: 600, tick: false }
    ],
    keysLabel: 'Left and right arrow keys move the strong associate, down and up the weak one.',
    keys: (function () {
      function mv(k, d) { return function (m, s) { var p = ladderPos(s), o = { s: p.s, w: p.w, t: 1 }; o[k] = clamp(o[k] + d, 0.0005, m.smax - 0.0005); return o; }; }
      return { ArrowRight: mv('s', 0.0025), ArrowLeft: mv('s', -0.0025), ArrowUp: mv('w', 0.0025), ArrowDown: mv('w', -0.0025) };
    })(),
    drag: {
      pick: function (m, s, p) {
        var q = ladderPos(s), ds = Math.hypot(p[0] - LX(m, q.s), p[1] - LY(m, rung(q.s))), dw = Math.hypot(p[0] - LX(m, q.w), p[1] - LY(m, rung(q.w)));
        if (Math.min(ds, dw) > 56) return false;
        ladderPick = ds <= dw ? 's' : 'w';
        return true;
      },
      move: function (m, s, p) {
        var q = ladderPos(s), o = { s: q.s, w: q.w, t: 1 };
        o[ladderPick] = clamp((p[0] - m.px0) / (m.px1 - m.px0) * m.smax, 0.0005, m.smax - 0.0005);
        return o;
      }
    }
  });

  /* ---------------------------------------------------------------------------------------
     Question two: the fan sweep. A star of equal-strength roads; one leaf is read as the fan
     doubles. The engine starts every road from the source's full activation (flat). On the
     scratch copy, outgoing = node_act / len(roads): it halves with each doubling up to 8, then
     falls below the activation floor at 16. */
  var A0 = 0.2433743975, FLOOR = 0.022; // the floor is drawn between the last two divided values
  function starModel(box) {
    if (box.width < 640) {
      return { key: 'n', view: { w: 390, h: 730 }, narrow: true, cx: 195, cy: 200, R: 150,
        plot: { x0: 22, x1: 372, y0: 666, top: 540 }, verdict: [16, 404], wrapAt: 42 };
    }
    return { key: 'w', view: { w: 1180, h: 580 }, narrow: false, cx: 270, cy: 300, R: 210,
      plot: { x0: 640, x1: 1150, y0: 420, top: 270 }, verdict: [640, 132], wrapAt: 60 };
  }
  var STAR = starModel({ width: 1180, height: 580 });
  function leafValue(level, divide) { return divide ? A0 / Math.pow(2, level) : A0; }
  function px(m, i) { return m.plot.x0 + 40 + i * (m.plot.x1 - m.plot.x0 - 80) / 4; }
  function py(m, v) { return m.plot.y0 - (v / A0) * (m.plot.y0 - m.plot.top); }
  P.figure({
    id: 'star', name: 'fan-sweep', title: 'The fan sweep',
    caption: 'One leaf of a star read as the fan doubles: flat on the engine, halving on the scratch copy that divides the source among its roads.',
    model: STAR,
    modelFor: starModel,
    initialState: function () { return { k: 0, divide: false }; },
    stillState: function () { return { k: 4, divide: false }; },
    tick: function (m, s, dt) { return { k: Math.min(4, s.k + dt * 0.62), divide: s.divide }; },
    settled: function (m, s) { return s.k >= 4; },
    draw: function (m, s, pal) {
      // the star's roads change only when the fan doubles; the pulses along them move every frame
      var back = '', star = '', pulses = '', series = '', labels = '', lvl = Math.floor(s.k + 1e-6), n = Math.pow(2, lvl), ph = s.k - lvl;
      var v = leafValue(lvl, s.divide), on = v >= FLOOR, f = on ? v / A0 : 0;
      // the star
      for (var j = 0; j < n; j++) {
        var an = j * 2 * Math.PI / n, lx = m.cx + m.R * Math.cos(an), ly = m.cy + m.R * Math.sin(an);
        star += S.line(m.cx, m.cy, lx, ly, pal, j === 0 ? 'ink' : 'soft', j === 0 ? 1.5 : 1.1, on ? 0.25 + 0.75 * f : 0.18);
        if (on) star += S.dot(lx, ly, 3 + 6 * f, pal, 'mint', 0.35 + 0.65 * f);
        else star += S.circle(lx, ly, 3.5, pal, 'quiet', 1);
        if (on && ph > 0.03 && ph < 0.97 && s.k < 4) {
          var e = ease(ph * 1.15);
          pulses += S.dot(lerp(m.cx, lx, e), lerp(m.cy, ly, e), 3, pal, 'ink', 0.4 + 0.6 * f);
        }
      }
      var rx = m.cx + m.R;
      var source = S.circle(rx, m.cy, 15, pal, 'ink', 1.2, 0.9) +
        S.dot(m.cx, m.cy, 18, pal, 'ink', 0.08) + S.dot(m.cx, m.cy, 6, pal, 'ink') +
        S.circle(m.cx, m.cy, 13, pal, 'ink', 1.2, 0.8);
      // the plot: one leaf's activation at each fan
      var pl = m.plot;
      back += S.line(pl.x0, pl.y0, pl.x1, pl.y0, pal, 'quiet', 1);
      for (var i = 0; i < 5; i++) back += S.line(px(m, i), pl.y0, px(m, i), pl.y0 + 7, pal, 'quiet', 1);
      back += S.path([[pl.x0, py(m, FLOOR)], [pl.x1, py(m, FLOOR)]], pal, 'quiet', 1, { dash: '3 6' });
      var pts = [];
      for (i = 0; i <= lvl; i++) { var vi = leafValue(i, s.divide); if (vi >= FLOOR) pts.push([px(m, i), py(m, vi)]); }
      if (pts.length > 1) series += S.path(pts, pal, 'mint', 1.8);
      pts.forEach(function (q, k2) { series += S.dot(q[0], q[1], k2 === pts.length - 1 ? 6 : 4.4, pal, 'mint'); });
      // at the last fan the divided value is below the floor: nothing is drawn there, as nothing was reported
      var fs = m.narrow ? 14 : 15;
      labels += S.text(pl.x0, pl.top - 34, 'activation of the read leaf', pal, 'soft', { size: fs });
      labels += S.text(pl.x1, pl.y0 + 34, 'fan, doubling at each step', pal, 'soft', { size: fs, anchor: 'end' });
      labels += S.text(pl.x1, py(m, FLOOR) - 9, 'activation floor', pal, 'quiet', { size: 14, anchor: 'end' });
      labels += S.text(rx, m.cy - 26, 'the read leaf', pal, 'soft', { size: fs, anchor: 'middle' });
      var v1 = s.divide ? 'Divided among its roads, as on the scratch copy:' : "Every road starts from the source's full activation.";
      var v2 = s.divide ? 'activation halves with each doubling, then falls below the floor.' : 'The line is flat to the last digit.';
      labels += lines(m.verdict[0], m.verdict[1], wrap(v1, m.wrapAt), 22, pal, 'ink', { size: m.narrow ? 16 : 18, weight: 500 });
      labels += lines(m.verdict[0], m.verdict[1] + wrap(v1, m.wrapAt).length * 22 + 2, wrap(v2, m.wrapAt + 6), 20, pal, 'soft', { size: fs });
      return { back: back, front: { star: star, pulses: pulses, source: source, series: series }, labels: labels };
    },
    describe: function (m, s) {
      var lvl = Math.floor(s.k + 1e-6), n = Math.pow(2, lvl), v = leafValue(lvl, s.divide);
      return 'A star: one source and ' + n + (n === 1 ? ' road' : ' equal-strength roads') + ' to its leaves; one leaf is read. Beside it, the read leaf\'s activation at each fan so far. ' +
        (s.divide ? 'With the source divided among its roads, the activation halves with each doubling' + (v < FLOOR ? ' and at this fan falls below the activation floor, so the leaf is dark.' : '.') :
          'Every road starts from the source\'s full activation, so the line is flat.');
    },
    // The story by itself: the fan doubles on the engine (flat), then on the scratch copy that
    // divides the source (halving, then below the floor), then the engine again.
    // Each sweep runs the fan on 'travel' to half a doubling past the last one, held at 4, so the last
    // pulse reaches its leaf and the fan doubles to 16 while still moving, as every earlier doubling does,
    // instead of creeping into the last whole value at the very end of the step.
    sequence: [
      { dur: 400, tick: false },
      { dur: 2900, tick: false, frame: function (m, s, e) { return { k: Math.min(4, 4.25 * e), divide: s.divide }; }, ease: 'travel' },
      { dur: 600, tick: false },
      { dur: 650, tick: false, 'do': function () { return { k: 0, divide: true }; } },
      { dur: 2900, tick: false, frame: function (m, s, e) { return { k: Math.min(4, 4.25 * e), divide: s.divide }; }, ease: 'travel' },
      { dur: 1300, tick: false },
      { dur: 700, tick: false, 'do': function () { return { k: 4, divide: false }; } }
    ],
    keysLabel: 'Left and right arrow keys halve or double the fan; the D key divides the source or undoes it.',
    keys: {
      ArrowRight: function (m, s) { return { k: Math.min(4, Math.floor(s.k + 1e-6) + 1), divide: s.divide }; },
      ArrowLeft: function (m, s) { return { k: Math.max(0, Math.ceil(s.k - 1e-6) - 1), divide: s.divide }; },
      d: function (m, s) { return { k: Math.floor(s.k + 1e-6), divide: !s.divide }; }
    },
    drag: {
      pick: function (m, s, p) { return m.narrow ? p[1] >= m.plot.top - 60 : p[0] >= m.plot.x0 - 20; }, // drag across the plot to set the fan
      move: function (m, s, p) { var i = Math.round(clamp((p[0] - px(m, 0)) / (px(m, 1) - px(m, 0)), 0, 4)); return { k: i, divide: s.divide }; }
    }
  });

  /* ---------------------------------------------------------------------------------------
     Question three: friction = 1 - cpu_dt / wall_dt over the capture loop. Each cycle is about
     47 microseconds of CPU-bound work, then the 0.5 ms yield. The sleep is the only off-CPU
     interval, so it sets the level; pure CPU work of any size keeps friction near zero. */
  var WORK = 47, SLEEP = 500;
  function stallModel(box) {
    if (box.width < 640) {
      return { key: 'n', view: { w: 390, h: 560 }, narrow: true, tx0: 16, tx1: 374, ty: 150, win: 1700, gy: 352, gx0: 16, gx1: 374, stmt: [16, 452], wrapAt: 42 };
    }
    return { key: 'w', view: { w: 1180, h: 450 }, narrow: false, tx0: 40, tx1: 1140, ty: 100, win: 3300, gy: 280, gx0: 40, gx1: 1140, stmt: [40, 386], wrapAt: 90 };
  }
  var STALL = stallModel({ width: 1180, height: 450 });
  function cycles(m, s) {
    var out = [], t = 0, w = WORK * s.L;
    while (t < m.win) {
      out.push({ kind: 'work', a: t, b: Math.min(m.win, t + w) }); t += w;
      if (s.sleep && t < m.win) { out.push({ kind: 'sleep', a: t, b: Math.min(m.win, t + SLEEP) }); t += SLEEP; }
    }
    return out;
  }
  function frictionAt(m, cs, T) {
    if (T < 8) return null;
    var cpu = 0;
    cs.forEach(function (c) { if (c.kind === 'work' && c.a < T) cpu += Math.min(c.b, T) - c.a; });
    return clamp(1 - cpu / T, 0, 1);
  }
  P.figure({
    id: 'stall', name: 'stall-fraction', title: 'The stall fraction',
    caption: 'The stall fraction over the capture cycles: the injected sleep sets its level, and without it the reading stays near zero however heavy the work.',
    model: STALL,
    modelFor: stallModel,
    initialState: function () { return { L: 1, sleep: true, t: 0 }; },
    stillState: function () { return { L: 10, sleep: false, t: 1 }; },
    tick: function (m, s, dt) { return assign(s, { t: Math.min(1, s.t + dt / 4) }); },
    settled: function (m, s) { return s.t >= 1; },
    draw: function (m, s, pal) {
      // Parts: the track (changes only with the sleep or the workload), the work run so far (one
      // path), the sleeps (rewritten only when one more is reached), the cycle ticks, the cursor,
      // the trail of readings and the reading itself.
      var back = '', track = '', litWork = '', sleeps = '', ticks = '', cursor = '', trail = '', gauge = '', labels = '';
      var k = (m.tx1 - m.tx0) / m.win, T = s.t * m.win, cs = cycles(m, s);
      var X = function (u) { return m.tx0 + u * k; }, N = S.n;
      var wr = pal.name === 'print' ? 'ink' : 'mint'; // in print the work is solid black, the sleep dotted grey
      // the track: work on the CPU as solid light, the sleep as a dotted pause
      cs.forEach(function (c) {
        var lit = c.a < T, a = X(c.a), b = X(c.b), mid = X(Math.min(c.b, Math.max(c.a, T)));
        if (c.kind === 'work') {
          track += S.line(a, m.ty, b, m.ty, pal, wr, 3.4, 0.22);
          ticks += S.line(a, m.ty - 9, a, m.ty + 9, pal, 'quiet', 1, 0.8);
          if (lit) litWork += 'M' + N(a) + ' ' + N(m.ty) + 'L' + N(mid) + ' ' + N(m.ty);
        } else {
          sleeps += S.path([[a + 3, m.ty], [b - 3, m.ty]], pal, 'soft', 1.2, { dash: '1 6', opacity: lit ? 0.9 : 0.35 });
        }
      });
      if (litWork) litWork = '<path d="' + litWork + '" ' + S.stroke(pal, wr, 3.4, 1) + '/>';
      if (s.t < 1) cursor += S.line(X(T), m.ty - 24, X(T), m.ty + 24, pal, 'ink', 1.2, 0.9);
      // the gauge: from no stall to all stall
      back += S.line(m.gx0, m.gy, m.gx1, m.gy, pal, 'quiet', 1.2);
      back += S.line(m.gx0, m.gy - 7, m.gx0, m.gy + 7, pal, 'quiet', 1);
      back += S.line(m.gx1, m.gy - 7, m.gx1, m.gy + 7, pal, 'quiet', 1);
      var G = function (f) { return m.gx0 + f * (m.gx1 - m.gx0); };
      for (var i = 1; i <= 28; i++) { // where the reading has been
        var Ti = (i / 28) * T, fi = frictionAt(m, cs, Ti);
        if (fi != null) trail += S.dot(G(fi), m.gy, 2.2, pal, 'mint', 0.12 + 0.3 * i / 28);
      }
      var f = frictionAt(m, cs, T);
      if (f != null) {
        gauge += S.line(G(f), m.gy - 18, G(f), m.gy + 18, pal, 'mint', 2.2);
        gauge += S.dot(G(f), m.gy, 13, pal, 'mint', 0.16) + S.dot(G(f), m.gy, 5, pal, 'ink');
      }
      var fs = m.narrow ? 14 : 15;
      labels += S.text(m.tx0, m.ty - 34, 'work on the CPU', pal, 'soft', { size: fs });
      if (s.sleep) {
        var sl = cs[1] && cs[1].kind === 'sleep' ? cs[1] : null;
        if (sl) labels += S.text(X((sl.a + sl.b) / 2), m.ty + 38, 'the injected sleep', pal, 'soft', { size: fs, anchor: 'middle' });
      }
      labels += S.text(m.tx1, m.ty - 34, 'wall time', pal, 'quiet', { size: fs, anchor: 'end' });
      labels += S.text(m.gx0, m.gy - 40, 'friction, the stall fraction', pal, 'ink', { size: m.narrow ? 15 : 16, weight: 500 });
      labels += S.text(m.gx0, m.gy + 36, 'no stall', pal, 'soft', { size: fs });
      labels += S.text(m.gx1, m.gy + 36, 'all stall', pal, 'soft', { size: fs, anchor: 'end' });
      var v1 = s.sleep ? 'The sleep is the only off-CPU interval, so it sets the level.' : 'Pure CPU work of any size gives cpu ≈ wall.';
      var v2 = s.sleep ? 'The level follows the ratio of sleep to work, with no contention behind it.' : 'More work is more duration at the same friction: the number sits near zero.';
      labels += lines(m.stmt[0], m.stmt[1], wrap(v1, m.wrapAt), 22, pal, 'ink', { size: m.narrow ? 16 : 18, weight: 500 });
      labels += lines(m.stmt[0], m.stmt[1] + wrap(v1, m.wrapAt).length * 22 + 2, wrap(v2, m.wrapAt + 4), 20, pal, 'soft', { size: fs });
      return { back: back, front: { track: track, litWork: litWork, sleeps: sleeps, ticks: ticks, cursor: cursor, trail: trail, gauge: gauge }, labels: labels };
    },
    // While it plays, only positions change: move the existing marks instead of drawing them again.
    // Anything that adds or removes a mark (a sleep reached, the first readings, the end of the run,
    // a control) asks for a full draw, which leaves the drawing exactly as draw() would.
    update: function (m, s, ctx) {
      var parts = ctx.parts; if (!parts || !parts.litWork) return false;
      var k = (m.tx1 - m.tx0) / m.win, T = s.t * m.win, cs = m._cs && m._cs.L === s.L && m._cs.sleep === s.sleep ? m._cs.list : cycles(m, s);
      m._cs = { L: s.L, sleep: s.sleep, list: cs };
      var X = function (u) { return m.tx0 + u * k; }, G = function (f) { return m.gx0 + f * (m.gx1 - m.gx0); }, N = S.n;
      var d = '', nLit = 0, xs = [];
      cs.forEach(function (c) {
        if (c.a >= T) return;
        if (c.kind === 'work') d += 'M' + N(X(c.a)) + ' ' + N(m.ty) + 'L' + N(X(Math.min(c.b, Math.max(c.a, T)))) + ' ' + N(m.ty);
        else nLit++;
      });
      for (var i = 1; i <= 28; i++) { var fi = frictionAt(m, cs, (i / 28) * T); if (fi != null) xs.push(G(fi)); }
      var f = frictionAt(m, cs, T);
      var key = [s.L, s.sleep, nLit, xs.length, f != null, s.t < 1, !!d].join();
      if (!m._live || m._live.front !== ctx.front || m._live.key !== key) { m._live = { front: ctx.front, key: key }; return false; }
      var el = parts.litWork.firstElementChild; if (d && el) el.setAttribute('d', d);
      el = parts.cursor.firstElementChild;
      if (el) { el.setAttribute('x1', N(X(T))); el.setAttribute('x2', N(X(T))); }
      var dots = parts.trail.children;
      if (dots.length !== xs.length) return false;
      for (i = 0; i < xs.length; i++) dots[i].setAttribute('cx', N(xs[i]));
      var g = parts.gauge.children;
      if (f != null && g.length === 3) {
        var gx = N(G(f));
        g[0].setAttribute('x1', gx); g[0].setAttribute('x2', gx); g[1].setAttribute('cx', gx); g[2].setAttribute('cx', gx);
      }
    },
    describe: function (m, s) {
      var cs = cycles(m, s), f = frictionAt(m, cs, Math.max(8, s.t * m.win));
      var where = f == null ? 'at the start of the scale, before the first reading' : f > 0.75 ? 'high, close to all stall' : f > 0.35 ? 'in the middle of the scale' : f > 0.05 ? 'low' : 'near zero';
      return 'A track of capture cycles in wall time: short bursts of CPU-bound work' + (s.sleep ? ', each followed by the injected sleep' : ' back to back, with no sleep') +
        (s.L > 1.5 ? ', the work made ' + Math.round(s.L) + ' times heavier' : '') + '. Below, the friction reading on a scale from no stall to all stall: it is ' + where + '. ' +
        (s.sleep ? 'The sleep is the only off-CPU interval, so it sets the level.' : 'Pure CPU work of any size keeps friction near zero.');
    },
    // The story by itself: with the sleep in, the reading climbs high; with it taken out, the reading
    // stays near zero; made heavier step by step, the work leaves it near zero.
    sequence: [
      // t is wall time, so both cursor sweeps stay 'linear' and take the same 2100 ms: one clock, one speed.
      { dur: 400, tick: false },
      { dur: 2100, tick: false, to: { t: 1 }, ease: 'linear' },
      { dur: 800, tick: false },
      { dur: 650, tick: false, 'do': function (m, s) { return assign(s, { sleep: false, t: 0 }); } },
      { dur: 2100, tick: false, to: { t: 1 }, ease: 'linear' },
      { dur: 700, tick: false },
      { dur: 1700, tick: false, frame: function (m, s, u) { return assign(s, { L: 1 + Math.round(9 * u) }); }, ease: 'settle' },
      { dur: 700, tick: false }
    ],
    keysLabel: 'Left and right arrow keys make the work lighter or heavier; the S key takes out the sleep or puts it back.',
    keys: {
      ArrowRight: function (m, s) { return assign(s, { L: Math.min(10, Math.round(s.L) + 1), t: Math.max(s.t, 0.6) }); },
      ArrowLeft: function (m, s) { return assign(s, { L: Math.max(1, Math.round(s.L) - 1), t: Math.max(s.t, 0.6) }); },
      s: function (m, s) { return assign(s, { sleep: !s.sleep, t: Math.max(s.t, 0.6) }); }
    },
    drag: {
      pick: function (m, s, p) { return Math.abs(p[1] - m.ty) < 60 || Math.abs(p[1] - m.gy) < 50; },
      move: function (m, s, p) { return assign(s, { t: clamp((p[0] - m.tx0) / (m.tx1 - m.tx0), 0.01, 1) }); }
    }
  });
})(window.Psyche);

