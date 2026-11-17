/* ===== This post's figure: the way a post reaches the site =================================
   One model (geometry, no drawing) and one draw(model, state, palette) returning SVG text. What
   stays still is in 'back' (the repository line, the post's way drawn faint, the checks unlit,
   their leaders, the site line); 'front' carries only what moves, in parts: the lit trace, the
   lit checks, the review ring, the merge commit, the post itself. While the post travels,
   update() moves the trace and the point without rebuilding anything.
   Every word comes from the post or its old chart. Colour carries no meaning alone: the post's
   way is mint (dashed in print), the checks and the review are periwinkle (solid in print). */
(function (P) {
  var S = P.svg;
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function wrap(str, max) {
    var out = [], cur = '';
    str.split(' ').forEach(function (w) {
      if (cur && (cur + ' ' + w).length > max) { out.push(cur); cur = w; } else cur = cur ? cur + ' ' + w : w;
    });
    if (cur) out.push(cur);
    return out;
  }

  // the checks, in the order the post names them: four read by the checks, three by the build
  var CHECKS = [
    'counts that disagree with the ledger',
    'claim terms the project rules out',
    'material the disclosure policy withholds',
    'language',
    'links',
    'head',
    'accessibility'
  ];

  // the way of the post: line and cubic pieces, sampled once into a polyline with lengths
  function sampleRoute(pieces) {
    var pts = [], i, k;
    pieces.forEach(function (pc, j) {
      if (pc.length === 2) { if (!j) pts.push(pc[0]); pts.push(pc[1]); return; }
      for (k = j ? 1 : 0; k <= 28; k++) {
        var t = k / 28, a = (1 - t) * (1 - t) * (1 - t), b = 3 * (1 - t) * (1 - t) * t, c = 3 * (1 - t) * t * t, d = t * t * t;
        pts.push([a * pc[0][0] + b * pc[1][0] + c * pc[2][0] + d * pc[3][0], a * pc[0][1] + b * pc[1][1] + c * pc[2][1] + d * pc[3][1]]);
      }
    });
    var len = [0];
    for (i = 1; i < pts.length; i++) len.push(len[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    return { pts: pts, len: len, L: len[len.length - 1] };
  }
  function uAt(r, p) { // route progress (0..1) of the sample nearest to p, and its distance
    var best = 0, bd = 1e9;
    for (var i = 0; i < r.pts.length; i++) { var d = Math.hypot(r.pts[i][0] - p[0], r.pts[i][1] - p[1]); if (d < bd) { bd = d; best = i; } }
    return { u: r.len[best] / r.L, d: bd };
  }
  function uOfPoint(r, p) { return uAt(r, p).u; }
  function at(r, u) { // the point at progress u, and the polyline up to it
    var s = clamp(u, 0, 1) * r.L, lo = 0, hi = r.len.length - 1;
    while (hi - lo > 1) { var mid = (lo + hi) >> 1; if (r.len[mid] <= s) lo = mid; else hi = mid; }
    var seg = r.len[hi] - r.len[lo], f = seg > 0 ? (s - r.len[lo]) / seg : 0;
    var p = [r.pts[lo][0] + (r.pts[hi][0] - r.pts[lo][0]) * f, r.pts[lo][1] + (r.pts[hi][1] - r.pts[lo][1]) * f];
    return { p: p, upto: r.pts.slice(0, lo + 1).concat([p]) };
  }

  function wideModel() {
    var W = 1180, H = 504, TY = 384, BY = 244, SY = 90;
    var route = sampleRoute([
      [[230, TY], [262, TY], [258, BY], [290, BY]],
      [[290, BY], [740, BY]],
      [[740, BY], [792, BY], [788, TY], [840, TY]],
      [[840, TY], [884, TY], [876, SY], [920, SY]],
      [[920, SY], [1140, SY]]
    ]);
    var teeth = CHECKS.map(function (c, k) {
      var x = 400 + 40 * k, y = BY - 48 - (6 - k) * 24;
      return { c: [x, BY], a: [x, BY - 13], b: [x, BY + 13], u: uOfPoint(route, [x, BY]),
        leader: [[x, BY - 18], [x, y - 13]], lab: [[x + 9, y, c]] };
    });
    return { key: 'w', view: { w: W, h: H }, size: { name: 18, sub: 15, check: 16 }, route: route, teeth: teeth,
      trunk: [[40, TY], [1140, TY]], site: [[920, SY], [1140, SY]],
      start: [230, TY], review: [740, BY], commit: [840, TY],
      uIn: uOfPoint(route, [372, BY]), uOut: uOfPoint(route, [668, BY]), uEnd: uOfPoint(route, [740, BY]), uMerge: uOfPoint(route, [840, TY]),
      labels: [
        { x: 40, y: TY - 14, t: 'the repository', r: 'soft', s: 'sub' },
        { x: 230, y: TY + 44, t: 'Write', r: 'ink', s: 'name' },
        { x: 230, y: TY + 66, t: 'a Markdown file under docs/blog/', r: 'soft', s: 'sub' },
        { x: 400, y: BY + 44, t: 'Check', r: 'ink', s: 'name' },
        { x: 400, y: BY + 66, t: 'a pull request that runs the checks', r: 'soft', s: 'sub' },
        { x: 740, y: TY + 44, t: 'Review', r: 'ink', s: 'name' },
        { x: 740, y: TY + 66, t: 'merged by the project lead', r: 'soft', s: 'sub' },
        { x: 740, y: TY + 88, t: 'what no check can read, such as its tone', r: 'soft', s: 'sub' },
        { x: 920, y: SY - 46, t: 'Publish', r: 'ink', s: 'name' },
        { x: 920, y: SY - 22, t: 'staged from that commit and published', r: 'soft', s: 'sub' },
        { x: 1140, y: SY + 30, t: 'the site', r: 'soft', s: 'sub', a: 'end' }
      ] };
  }
  function narrowModel(box) {
    var W = Math.max(320, Math.round(box.width)), H = 750, TX = 34, BX = 100, X = 128, R = W - 18;
    var route = sampleRoute([
      [[TX, 58], [TX, 88], [BX, 84], [BX, 114]],
      [[BX, 114], [BX, 506]],
      [[BX, 506], [BX, 542], [TX, 542], [TX, 578]],
      [[TX, 578], [TX, 650], [110, 702], [150, 702]],
      [[150, 702], [R, 702]]
    ]);
    var teeth = CHECKS.map(function (c, k) {
      var y = 230 + 44 * Math.min(k, 3) + 36 * Math.max(0, k - 3), ls = wrap(c, 24); // two-line checks get more room
      return { c: [BX, y], a: [BX - 13, y], b: [BX + 13, y], u: uOfPoint(route, [BX, y]), leader: null,
        lab: ls.map(function (l, i) { return [X, y + 5 + i * 17 - (ls.length - 1) * 5, l]; }) };
    });
    function block(x, y, name, subs, lh) {
      var out = [{ x: x, y: y, t: name, r: 'ink', s: 'name' }];
      subs.forEach(function (l, i) { out.push({ x: x, y: y + 22 + i * lh, t: l, r: 'soft', s: 'sub' }); });
      return out;
    }
    return { key: 'n' + W, view: { w: W, h: H }, size: { name: 18, sub: 15, check: 15 }, route: route, teeth: teeth,
      trunk: [[TX, 16], [TX, 742]], site: [[150, 702], [R, 702]],
      start: [TX, 58], review: [BX, 506], commit: [TX, 578],
      uIn: uOfPoint(route, [BX, 206]), uOut: uOfPoint(route, [BX, 486]), uEnd: uOfPoint(route, [BX, 506]), uMerge: uOfPoint(route, [TX, 578]),
      labels: [{ x: TX + 12, y: 24, t: 'the repository', r: 'soft', s: 'sub' }]
        .concat(block(X, 72, 'Write', ['a Markdown file under', 'docs/blog/'], 19))
        .concat(block(X, 150, 'Check', ['a pull request that runs', 'the checks'], 19))
        .concat(block(X, 534, 'Review', ['merged by the project lead', 'what no check can read,', 'such as its tone'], 19))
        .concat(block(168, 636, 'Publish', ['staged from that commit', 'and published'], 19))
        .concat([{ x: R, y: 730, t: 'the site', r: 'soft', s: 'sub', a: 'end' }]) };
  }
  function lit(m, s) { var n = 0; m.teeth.forEach(function (t) { if (s.u >= t.u - 1e-4) n++; }); return n; }
  function ringPts(c, r, f) {
    var pts = [], n = Math.max(2, Math.round(56 * f));
    for (var i = 0; i <= n; i++) { var a = -Math.PI / 2 + (i / n) * f * 2 * Math.PI; pts.push([c[0] + r * Math.cos(a), c[1] + r * Math.sin(a)]); }
    return pts;
  }
  function liveKey(m, s) {
    return [lit(m, s), s.rv >= 1 ? 1 : s.rv <= 0 ? 0 : 'm' + Math.round(s.rv * 60), s.u >= m.uMerge - 1e-4 ? 1 : 0].join();
  }

  function drawFig(m, s, pal) {
    var back = '', labels = '', r = m.route, here = at(r, s.u), n = lit(m, s);
    // static: the repository, the post's way drawn faint, the checks unlit with their leaders, the site
    back += S.path(m.trunk, pal, 'quiet', 1.2);
    back += S.path(r.pts, pal, 'faint', 1.2);
    back += S.path(m.site, pal, 'quiet', 1.2);
    m.teeth.forEach(function (t) {
      back += S.line(t.a[0], t.a[1], t.b[0], t.b[1], pal, 'faint', 1.6);
      if (t.leader) back += S.path(t.leader, pal, 'faint', 1);
    });
    back += S.dot(m.start[0], m.start[1], 3.2, pal, 'ink', 0.9);

    // moving: the trace, the lit checks, the review ring, the merge commit, the post
    var trace = S.glowPath(here.upto, pal, 'mint', 1.9, { glow: 0.2 });
    var checks = '';
    m.teeth.forEach(function (t, k) { if (k < n) checks += S.glowPath([t.a, t.b], pal, 'peri', 2.2, { glow: 0.22 }); });
    var ring = s.rv > 0 ? S.path(ringPts(m.review, 17, Math.min(1, s.rv)), pal, 'peri', 1.6) : '';
    var merged = s.u >= m.uMerge - 1e-4;
    var commit = merged ? S.circle(m.commit[0], m.commit[1], 8, pal, 'ink', 1.4) : '';
    var dot = S.glowDot(here.p[0], here.p[1], 5.5, pal, 'mint', 1, 0.22) + S.dot(here.p[0], here.p[1], 2.2, pal, 'ink');

    // words: the checks the post has passed are in full ink
    m.teeth.forEach(function (t, k) {
      t.lab.forEach(function (l) { labels += S.text(l[0], l[1], l[2], pal, k < n ? 'ink' : 'soft', { size: m.size.check }); });
    });
    m.labels.forEach(function (l) {
      labels += S.text(l.x, l.y, l.t, pal, l.r, { size: m.size[l.s], anchor: l.a || 'start', weight: l.s === 'name' ? 500 : null });
    });
    return { back: back, front: { trace: trace, checks: checks, ring: ring, commit: commit, dot: dot }, labels: labels };
  }

  function rvFor(m, u, rv) { return u > m.uEnd + 1e-4 ? 1 : u < m.uEnd - 1e-4 ? 0 : rv; }
  var WIDE = wideModel();
  P.figure({
    id: 'route', name: 'how-a-post-is-published', title: 'How a post reaches the site',
    caption: 'A post is written as a Markdown file, passes the checks in a pull request, is merged by the project lead and is published from that commit.',
    model: WIDE,
    modelFor: function (box) { return box.width < 640 ? narrowModel(box) : WIDE; },
    frontGlow: false,
    initialState: function () { return { u: 0, rv: 0 }; },
    stillState: function () { return { u: 1, rv: 1 }; },
    draw: drawFig,
    update: function (m, s, ctx) {
      var key = liveKey(m, s);
      if (!m._live || m._live.front !== ctx.front || m._live.key !== key) { m._live = { front: ctx.front, key: key }; return false; }
      var here = at(m.route, s.u), d = S.d(here.upto), i;
      var tr = ctx.parts.trace ? ctx.parts.trace.children : [];
      for (i = 0; i < tr.length; i++) tr[i].setAttribute('d', d);
      var dots = ctx.parts.dot ? ctx.parts.dot.children : [];
      if (!dots.length) return false;
      var x = S.n(here.p[0]), y = S.n(here.p[1]);
      for (i = 0; i < dots.length; i++) { dots[i].setAttribute('cx', x); dots[i].setAttribute('cy', y); }
    },
    handle: function (m, s) { return at(m.route, s.u).p; },
    describe: function (m, s) {
      var n = lit(m, s), base = 'The way a post reaches the site, drawn as lines: a post is written as a Markdown file in the repository under docs/blog/, goes out on a pull request that runs the checks (counts that disagree with the ledger, claim terms the project rules out, material the disclosure policy withholds, language, and the build\'s links, head and accessibility), is read in review for what no check can read, such as its tone, is merged by the project lead, and is staged from that commit and published. ';
      if (s.u >= 0.999) return base + 'The post has passed all seven checks, been merged and been published on the site.';
      if (s.u >= m.uMerge - 1e-4) return base + 'The post has been merged and is being staged from that commit.';
      if (s.u >= m.uEnd - 1e-4) return base + 'The post has passed all seven checks and is in review.';
      if (n > 0) return base + 'The post is in its pull request and has passed ' + n + ' of the seven checks.';
      return base + 'The post has been written and has not reached the checks yet.';
    },
    // The story by itself: written, through the seven checks one by one, read in review, merged,
    // then staged from that commit and published.
    sequence: [
      { dur: 900 },
      { dur: 1400, to: function (m) { return { u: m.uIn }; } },
      { dur: 3800, to: function (m) { return { u: m.uOut }; }, ease: 'linear' },
      { dur: 700, to: function (m) { return { u: m.uEnd }; }, ease: 'out' },
      { dur: 1000, to: { rv: 1 } },
      { dur: 600 },
      { dur: 1300, to: function (m) { return { u: m.uMerge }; } },
      { dur: 600 },
      { dur: 2200, to: { u: 1 } },
      { dur: 500 }
    ],
    keysLabel: 'Left and right arrow keys move the post along its way; Home and End go to its start and its end.',
    keys: {
      ArrowRight: function (m, s) { var u = Math.min(1, s.u + 0.02); return { u: u, rv: rvFor(m, u, 1) }; },
      ArrowLeft: function (m, s) { var u = Math.max(0, s.u - 0.02); return { u: u, rv: rvFor(m, u, 1) }; },
      Home: function () { return { u: 0, rv: 0 }; },
      End: function () { return { u: 1, rv: 1 }; }
    },
    drag: {
      pick: function (m, s, p) { return uAt(m.route, p).d < 48; },
      move: function (m, s, p) { var u = uAt(m.route, p).u; return { u: u, rv: rvFor(m, u, 1) }; }
    }
  });
})(window.Psyche);
