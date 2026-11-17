/* ===== This post's figures: a floor and a ceiling on one scale ===========================
   Every figure is one model (data and geometry, no drawing) and one draw(model, state, palette)
   that returns SVG text: what stays still in 'back' (drawn and glowed once), what moves in
   'front', and the words in 'labels'. While a figure plays, update() moves the few marks that
   move instead of drawing everything again. Every number in a figure is the post's own: 100%,
   22% on average, 2 of the 50 test environments, 5 seeds; and, for the arithmetic of luck, the
   post's illustrative p = 0.05 with m = 20 (about 0.64) and m = 100 (about 0.994).
   Colour carries no meaning alone: the all-knowing reference is periwinkle (solid in print), the
   random player mint (dashed in print), and every mark is also named in words. */
(function (P) {
  var S = P.svg, N = S.n;
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function assign(a, b) { var o = {}, k; for (k in a) o[k] = a[k]; for (k in b) o[k] = b[k]; return o; }
  function wrap(str, max) {
    var out = [], cur = '';
    str.split(' ').forEach(function (w) {
      if (cur && (cur + ' ' + w).length > max) { out.push(cur); cur = w; } else cur = cur ? cur + ' ' + w : w;
    });
    if (cur) out.push(cur);
    return out;
  }
  function lines(x, y, list, lh, pal, role, opts) {
    return list.map(function (l, i) { return S.text(x, y + i * lh, l, pal, role, opts); }).join('');
  }
  // a text the update() path can find and change: S.text with a data-k key on it
  function keyed(key, svg) { return svg.replace(/^<(\w+)/, '<$1 data-k="' + key + '"'); }
  // look elements up once per drawing; a new drawing (rebuild, theme) starts a new cache
  function finder(m, ctx) {
    if (!m._find || m._find.front !== ctx.front) m._find = { front: ctx.front, els: {} };
    var c = m._find.els;
    return function (k) {
      if (!c[k] || !c[k].isConnected) c[k] = ctx.front.querySelector('[data-k="' + k + '"]') || (ctx.labels && ctx.labels.querySelector('[data-k="' + k + '"]'));
      return c[k];
    };
  }

  /* ---------------------------------------------------------------------------------------
     How luck adds up: P = 1 - (1 - p)^m with the post's illustrative p = 0.05.
     The curve is drawn as m grows; the three values the post names are marked as m passes them. */
  var PL = 0.05;
  function Pm(m) { return 1 - Math.pow(1 - PL, m); }
  function luckModel(box) {
    if (box.width < 640) {
      return { key: 'n', view: { w: 390, h: 470 }, narrow: true, x0: 30, x1: 380, y0: 380, yt: 150,
        head: [0, 30], wrapAt: 40, fs: 15, mfs: 16 };
    }
    return { key: 'w', view: { w: 1180, h: 500 }, narrow: false, x0: 56, x1: 1110, y0: 410, yt: 120,
      head: [0, 40], wrapAt: 200, fs: 15, mfs: 17 };
  }
  function lx(m, k) { return m.x0 + (k / 100) * (m.x1 - m.x0); }
  function ly(m, v) { return m.y0 - v * (m.y0 - m.yt); }
  function curvePts(m, upto) {
    var pts = [], k;
    for (k = 1; k <= Math.floor(upto); k++) pts.push([lx(m, k), ly(m, Pm(k))]);
    if (upto > Math.floor(upto) + 1e-6) pts.push([lx(m, upto), ly(m, Pm(upto))]);
    return pts;
  }
  var MARKS = [
    { k: 1, text: 'one place: p = 0.05', dx: 14, dy: 5, anchor: 'start' },
    { k: 20, text: 'm = 20: P is about 0.64', dx: 16, dy: 30, anchor: 'start' },
    { k: 100, text: 'm = 100: P is about 0.994', dx: 0, dy: 36, anchor: 'end' }
  ];
  // a mark shows as soon as the tip stands on it (the sequence holds at 20 and ends at 100)
  function reached(s, mk) { return s.m >= mk.k - 0.05; }
  P.figure({
    id: 'luck', name: 'luck-adds-up', title: 'How luck adds up',
    caption: 'With the illustrative p = 0.05 in each place, the chance that luck breaks the check somewhere is about 0.64 at m = 20 and about 0.994 at m = 100.',
    model: luckModel({ width: 1180, height: 500 }),
    modelFor: luckModel,
    initialState: function () { return { m: 1 }; },
    stillState: function () { return { m: 100 }; },
    draw: function (m, s, pal) {
      var back = '', labels = '', fs = m.fs;
      // the scale: m from 1 to 100 places, P from 0 to 1; near certainty is the dotted line at 1
      back += S.line(m.x0, m.y0, m.x1, m.y0, pal, 'quiet', 1);
      back += S.line(m.x0, m.y0, m.x0, m.yt, pal, 'quiet', 1);
      back += S.path([[m.x0, m.yt], [m.x1, m.yt]], pal, 'quiet', 1, { dash: '2 6' });
      [1, 20, 100].forEach(function (k) { back += S.line(lx(m, k), m.y0, lx(m, k), m.y0 + 7, pal, 'quiet', 1); });
      back += S.line(m.x0 - 7, m.y0, m.x0, m.y0, pal, 'quiet', 1) + S.line(m.x0 - 7, m.yt, m.x0, m.yt, pal, 'quiet', 1);
      [1, 20, 100].forEach(function (k) { labels += S.text(lx(m, k), m.y0 + 28, String(k), pal, 'soft', { size: fs, anchor: k === 100 ? 'end' : 'middle' }); });
      labels += S.text(m.x0 - 14, m.y0 + 5, '0', pal, 'soft', { size: fs, anchor: 'end' });
      labels += S.text(m.x0 - 14, m.yt + 5, '1', pal, 'soft', { size: fs, anchor: 'end' });
      labels += S.text(m.x1, m.y0 + 54, 'm, the number of independent places', pal, 'soft', { size: fs, anchor: 'end' });
      var h1 = wrap('P, the probability that luck breaks the check somewhere', m.wrapAt);
      labels += lines(m.head[0], m.head[1], h1, 22, pal, 'ink', { size: m.mfs, weight: 500 });
      var h2 = m.narrow ? ['Illustrative numbers, not this project\'s:', 'p = 0.05 in each place'] : ['Illustrative numbers, not this project\'s: p = 0.05 in each place'];
      labels += lines(m.head[0], m.head[1] + h1.length * 22 + 2, h2, 20, pal, 'soft', { size: fs });
      // what moves: the curve so far and its tip
      var pts = curvePts(m, s.m), tip = pts[pts.length - 1];
      var front = '';
      front += pts.length > 1 ? keyed('curve', S.path(pts, pal, 'mint', 2.2)) : keyed('curve', S.path([tip, tip], pal, 'mint', 2.2));
      // the values the post names, as the curve reaches them
      MARKS.forEach(function (mk) {
        if (!reached(s, mk)) return;
        var x = lx(m, mk.k), y = ly(m, Pm(mk.k));
        front += S.circle(x, y, 7, pal, 'peri', 1.4);
        // on a phone the curve is nearly flat under the 100 mark: its words sit above the dotted line at 1
        var ty = m.narrow && mk.k === 100 ? m.yt - 18 : y + mk.dy;
        labels += S.text(x + mk.dx, ty, mk.text, pal, 'ink', { size: m.mfs, weight: 500, anchor: mk.anchor });
      });
      front += keyed('tip', S.dot(tip[0], tip[1], 4.5, pal, 'ink'));
      return { back: back, front: front, labels: labels };
    },
    // while the curve grows only its path and its tip change; a newly reached mark asks for a full draw
    update: function (m, s, ctx) {
      var passed = MARKS.filter(function (mk) { return reached(s, mk); }).length;
      if (!m._lk || m._lk.front !== ctx.front || m._lk.passed !== passed) { m._lk = { front: ctx.front, passed: passed }; return false; }
      var f = finder(m, ctx), c = f('curve'), t = f('tip'); if (!c || !t) return false;
      var pts = curvePts(m, s.m); if (pts.length < 2) return false;
      var tip = pts[pts.length - 1];
      c.setAttribute('d', S.d(pts)); t.setAttribute('cx', N(tip[0])); t.setAttribute('cy', N(tip[1]));
    },
    handle: function (m, s) { return [lx(m, s.m), ly(m, Pm(s.m))]; },
    describe: function (m, s) {
      var k = Math.round(s.m);
      return 'A curve of P, the probability that luck breaks the check somewhere, against m, the number of independent places, from 1 to 100, with the illustrative p = 0.05 in each place. ' +
        'The curve is drawn up to m = ' + k + '. It starts at 0.05 for one place' +
        (k >= 20 ? ', is about 0.64 at m = 20' : '') + (k >= 100 ? ' and about 0.994 at m = 100, near certainty' : '') + '.';
    },
    // the story by itself: from one place to twenty, a pause on 0.64, then on to a hundred
    sequence: [
      { dur: 700 },
      { dur: 3000, to: { m: 20 }, ease: 'inOut' },
      { dur: 1500 },
      { dur: 3800, to: { m: 100 }, ease: 'inOut' },
      { dur: 1500 }
    ],
    keysLabel: 'Left and right arrow keys take m down or up by one place; Page Up and Page Down by ten; Home and End go to 1 and 100.',
    keys: {
      ArrowRight: function (m, s) { return { m: Math.min(100, Math.round(s.m) + 1) }; },
      ArrowLeft: function (m, s) { return { m: Math.max(1, Math.round(s.m) - 1) }; },
      PageUp: function (m, s) { return { m: Math.min(100, Math.round(s.m) + 10) }; },
      PageDown: function (m, s) { return { m: Math.max(1, Math.round(s.m) - 10) }; },
      Home: function () { return { m: 1 }; },
      End: function () { return { m: 100 }; }
    },
    drag: {
      pick: function (m, s, p) { return p[1] > m.yt - 30 && p[1] < m.y0 + 30; },
      move: function (m, s, p) { return { m: Math.round(clamp(100 * (p[0] - m.x0) / (m.x1 - m.x0), 1, 100)) }; }
    }
  });

  /* ---------------------------------------------------------------------------------------
     The opening: what the check returned, drawn as levels across the whole screen. Height is the
     share of cases solved, from zero (the foot of the opening) to 100% (above the title). The
     ceiling rises first, then what had been assumed for the floor is laid at zero, then the floor
     rises to where it was measured, and the distance between the two is marked. The figure reads
     the title's and the foot's places, so the ceiling stands above the title and zero above the
     foot on every screen; exports (no page around them) use fixed fractions. */
  function sharesModel(box) {
    var W = Math.round(box.width), H = Math.round(box.height), narrow = W <= 700;
    var sec = document.querySelector('.tt-open'), t = sec && sec.querySelector('.tt-title'), ft = sec && sec.querySelector('.tt-foot');
    var live = sec && t && ft && Math.abs(sec.offsetWidth - W) < 2 && Math.abs(sec.offsetHeight - H) < 2;
    var x0, x1, ceil, zero;
    if (live) {
      x0 = ft.offsetLeft; x1 = ft.offsetLeft + ft.offsetWidth;
      ceil = t.offsetTop - (narrow ? 34 : 44); zero = ft.offsetTop - (narrow ? 40 : 50);
    } else { x0 = W * 0.08; x1 = W * 0.92; ceil = H * 0.2; zero = H * 0.8; }
    return { key: [W, H, x0, x1, ceil, zero].map(Math.round).join(','), view: { w: W, h: H }, narrow: narrow,
      x0: x0, x1: x1, ceil: ceil, zero: zero, fs: 15, nfs: narrow ? 16 : 17, vfs: narrow ? 18 : 20 };
  }
  function oy(m, v) { return m.zero - v * (m.zero - m.ceil); }
  var ROWS = [
    { id: 'a', name: 'All-knowing reference', sub: 'should always succeed', role: 'peri', tail: '' },
    { id: 'b', name: 'Random player', sub: 'should almost never succeed', role: 'mint', tail: ' on average' }
  ];
  function valText(r, v) { return Math.round(v * 100) + '%' + r.tail; }
  // the ceiling's words wait until it stands at 100%, so nothing written crosses the title
  function named(r, v) { return r.id === 'a' ? v >= 1 : v > 0; }
  function rowLabels(m, r, y, v, pal) {
    var o = '';
    if (m.narrow) o += keyed(r.id + 'n', S.text(m.x0, y - 12, r.name, pal, 'ink', { size: m.nfs, weight: 500 }));
    else {
      o += keyed(r.id + 'n', S.text(m.x0, y - 36, r.name, pal, 'ink', { size: m.nfs, weight: 500 }));
      o += keyed(r.id + 's', S.text(m.x0, y - 13, r.sub, pal, 'soft', { size: m.fs }));
    }
    o += keyed(r.id + 'v', S.text(m.x1, y - 12, valText(r, v), pal, 'ink', { size: m.vfs, weight: 500, anchor: 'end' }));
    return o;
  }
  P.figure({
    id: 'shares', name: 'share-of-cases', title: 'Share of cases each reference player succeeded in',
    caption: 'Share of cases each reference player succeeded in, over 5 seeds and 50 test environments: the all-knowing reference at 100%, the random player at 22% on average.',
    model: sharesModel({ width: 1600, height: 900 }),
    modelFor: sharesModel,
    remeasure: true,
    initialState: function () { return { a: 0, b: 0, z: 0, g: 0 }; },
    stillState: function () { return { a: 1, b: 0.22, z: 1, g: 1 }; },
    draw: function (m, s, pal) {
      var back = '', front = '', labels = '', W = m.view.w;
      // what had been assumed for the random player: close to zero (static once laid)
      if (s.z) {
        back += S.path([[0, m.zero], [W, m.zero]], pal, 'soft', 1.2, { dash: '3 5' });
        labels += S.text(m.x0, m.zero + 26, 'assumed before the run: close to zero', pal, 'soft', { size: m.fs });
      }
      // the distance between the assumption and the measurement, at the right end
      if (s.g) {
        var yb = oy(m, 0.22), xg = m.x1 - 1;
        back += S.line(xg, m.zero, xg, yb, pal, 'ink', 1.2, 0.8) + S.line(xg - 6, m.zero, xg, m.zero, pal, 'ink', 1.2, 0.8) + S.line(xg - 6, yb, xg, yb, pal, 'ink', 1.2, 0.8);
      }
      // the two levels: each rises from zero to the share it reached
      ROWS.forEach(function (r) {
        var v = s[r.id]; if (!(v > 0)) return;
        var y = oy(m, v);
        front += keyed(r.id + 'l', S.line(0, y, W, y, pal, r.role, 2));
        if (named(r, v)) labels += rowLabels(m, r, y, v, pal);
      });
      return { back: back, front: front, labels: labels };
    },
    // while a level rises only its line and its words move, and its number changes
    update: function (m, s, ctx) {
      var key = [s.a > 0, named(ROWS[0], s.a), s.b > 0, s.z, s.g].join();
      if (!m._sk || m._sk.front !== ctx.front || m._sk.key !== key) { m._sk = { front: ctx.front, key: key }; return false; }
      var f = finder(m, ctx);
      for (var i = 0; i < ROWS.length; i++) {
        var r = ROWS[i], v = s[r.id]; if (!(v > 0)) continue;
        var y = oy(m, v), l = f(r.id + 'l'); if (!l) return false;
        var ys = N(y); if (l.getAttribute('y1') === String(ys)) continue;
        l.setAttribute('y1', ys); l.setAttribute('y2', ys);
        if (!named(r, v)) continue;
        var nm = f(r.id + 'n'), sb = f(r.id + 's'), vt = f(r.id + 'v'); if (!nm || !vt) return false;
        nm.setAttribute('y', N(y - (m.narrow ? 12 : 36)));
        if (sb) sb.setAttribute('y', N(y - 13));
        vt.setAttribute('y', N(y - 12));
        var txt = valText(r, v); if (vt.textContent !== txt) vt.textContent = txt;
      }
    },
    describe: function (m, s) {
      var t = 'Share of cases solved, over 5 seeds and 50 test environments, drawn as height from 0% to 100%. ';
      t += s.a > 0 ? 'The all-knowing reference, which should always succeed, at ' + Math.round(s.a * 100) + '%. ' : '';
      t += s.z ? 'For the random player, close to zero had been assumed before the run. ' : '';
      t += s.b > 0 ? 'The random player at ' + Math.round(s.b * 100) + '% on average.' : '';
      return t;
    },
    // the story by itself: the ceiling, then the assumption for the floor, then the floor as measured
    sequence: [
      { dur: 600 },
      { dur: 2200, to: { a: 1 }, ease: 'out' },
      { dur: 1000 },
      { dur: 0, 'do': function (m, s) { return assign(s, { z: 1 }); } },
      { dur: 1500 },
      { dur: 2600, to: { b: 0.22 }, ease: 'out' },
      { dur: 700 },
      { dur: 0, 'do': function (m, s) { return assign(s, { g: 1 }); } },
      { dur: 1500 }
    ]
  });

  /* ---------------------------------------------------------------------------------------
     Against the limit written down before the run: the random player in each of the 50 test
     environments. Each environment is one ring; the two in which it crossed the limit rise
     straight up through the line from their own column, and their words stand beside them. The
     post gives the count, not which environments, so the two are drawn last; the order is not
     the order of the run (the caption says so). */
  var ENVS = 50, OVER = 2;
  function limitModel(box) {
    var xs = [], ys = [], i;
    if (box.width < 640) {
      // three rows of 17, 17 and 16 rings, about 23 apart across and 22 down
      for (i = 0; i < ENVS; i++) { xs.push(8 + (i % 17) * 23.375); ys.push(206 + Math.floor(i / 17) * 22); }
      return { key: 'n', view: { w: 390, h: 300 }, narrow: true, lx0: 0, lx1: 390, ly: 166, xs: xs, ys: ys, up: 112, r: 5.5,
        head: [0, 26], wrapAt: 40, fs: 15, nfs: 16 };
    }
    for (i = 0; i < ENVS; i++) { xs.push(9 + i * (1162 / 49)); ys.push(196); }
    return { key: 'w', view: { w: 1180, h: 250 }, narrow: false, lx0: 0, lx1: 1180, ly: 146, xs: xs, ys: ys, up: 92, r: 7,
      head: [0, 30], wrapAt: 200, fs: 15, nfs: 17 };
  }
  P.figure({
    id: 'limit', name: 'fifty-environments', title: 'The random player against the limit set in advance',
    caption: 'The random player in each of the 50 test environments, drawn in no particular order: it crossed the limit written down before the run in 2 of them.',
    model: limitModel({ width: 1180, height: 250 }),
    modelFor: limitModel,
    initialState: function () { return { lim: 0, n: 0, lift: 0 }; },
    stillState: function () { return { lim: 1, n: ENVS, lift: 1 }; },
    draw: function (m, s, pal) {
      var labels = '', fs = m.fs, rings = '', over = '', line = '';
      var h1 = wrap('The random player in each of the 50 test environments', m.wrapAt);
      labels += lines(m.head[0], m.head[1], h1, 22, pal, 'ink', { size: m.nfs, weight: 500 });
      // the limit, written down before the run
      if (s.lim > 0) {
        line += S.line(m.lx0, m.ly, lerp(m.lx0, m.lx1, s.lim), m.ly, pal, 'peri', 1.6);
        if (s.lim >= 1) labels += S.text(m.lx0, m.ly - 14, 'the limit written down before the run', pal, 'soft', { size: fs });
      }
      // the environments, one ring each, as they are checked
      var shown = Math.floor(s.n + 1e-6);
      for (var i = 0; i < shown; i++) {
        if (i >= ENVS - OVER) continue;
        rings += S.circle(m.xs[i], m.ys[i], m.r, pal, 'soft', 1.3);
      }
      for (i = ENVS - OVER; i < shown; i++) {
        var y = lerp(m.ys[i], m.up, s.lift);
        over += S.circle(m.xs[i], y, m.r, pal, s.lift > 0 ? 'mint' : 'soft', 1.3);
        if (s.lift > 0) over += S.dot(m.xs[i], y, m.r - 1.6, pal, 'mint', s.lift);
      }
      if (shown >= ENVS) labels += S.text(m.lx0, m.ys[ENVS - 1] + (m.narrow ? 34 : 40), 'below the limit', pal, 'soft', { size: fs });
      if (s.lift >= 1) {
        // the words stand at the left of the two raised rings, on their row
        var xe = m.xs[ENVS - OVER] - m.r - 14;
        if (m.narrow) labels += lines(xe, m.up - 5, ['crossed it in 2 of the 50', 'test environments'], 20, pal, 'ink', { size: m.nfs, weight: 500, anchor: 'end' });
        else labels += S.text(xe, m.up + 6, 'crossed it in 2 of the 50 test environments', pal, 'ink', { size: m.nfs, weight: 500, anchor: 'end' });
      }
      return { back: '', front: { line: line, rings: rings, over: over }, labels: labels };
    },
    describe: function (m, s) {
      var shown = Math.floor(s.n + 1e-6);
      return 'A line marks the limit written down before the run. Below it, one ring for each test environment checked so far: ' + shown + ' of 50. ' +
        (s.lift >= 1 ? 'In 2 of the 50 the random player crossed the limit; those two rings stand above the line. The two are drawn last; the order is not the order of the run.' : '');
    },
    // the story by itself: the limit is set, the 50 environments are checked one by one, two cross it
    sequence: [
      { dur: 500 },
      { dur: 1000, to: { lim: 1 }, ease: 'out' },
      { dur: 600 },
      { dur: 5200, to: { n: ENVS }, ease: 'linear' },
      { dur: 800 },
      { dur: 1200, to: { lift: 1 }, ease: 'inOut' },
      { dur: 1600 }
    ]
  });
})(window.Psyche);
