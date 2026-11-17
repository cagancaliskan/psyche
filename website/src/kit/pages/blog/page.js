(function (P) {
  'use strict';
  var S = P.svg;
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function ease(u) { u = clamp(u, 0, 1); return 1 - Math.pow(1 - u, 3); }
  function wrap(str, max) {
    var words = String(str).split(' '), lines = [], cur = '';
    words.forEach(function (w) { if (cur && (cur + ' ' + w).length > max) { lines.push(cur); cur = w; } else cur = cur ? cur + ' ' + w : w; });
    if (cur) lines.push(cur);
    return lines;
  }
  // the narrowest wrap that keeps the same number of lines, so no word stands alone on the last one
  function balanced(str, max) {
    var n = wrap(str, max).length, best = max;
    for (var m = max - 1; m >= 8; m--) { if (wrap(str, m).length > n) break; best = m; }
    return wrap(str, best);
  }
  function widthOf(lines, size) { var n = 0; lines.forEach(function (l) { n = Math.max(n, l.length); }); return n * size * 0.5; }
  function textLines(x, y, lines, lh, pal, role, opts) {
    return lines.map(function (l, i) { return S.text(x, y + i * lh, l, pal, role, opts); }).join('');
  }
  // the soft light around a point: a blurred disc in dark, a thin ring (no fill) in light and print
  function halo(x, y, r, pal, role, op) {
    return pal.glow ? S.dot(x, y, r, pal, role, op) : S.circle(x, y, r * 0.72, pal, role, 0.8, Math.min(0.6, op * 3.2));
  }
  // labels keep a thin ring of the ground colour around each letter, so a stroke passing under them never cuts the text
  function clear(svg, pal, w) {
    return svg.replace(/<text ([^>]*)>/g, function (all, a) {
      var mo = /fill-opacity="([^"]*)"/.exec(a);
      return '<text ' + a + ' stroke="' + pal.ground + '" stroke-width="' + (w || 4) + '" stroke-linejoin="round" paint-order="stroke"' + (mo && mo[1] * 1.4 < 1 ? ' stroke-opacity="' + S.n(mo[1] * 1.4) + '"' : '') + '>';
    });
  }
  function textOp(x, y, lines, lh, pal, role, opts, op) {
    var o = {}; for (var k in opts) o[k] = opts[k]; o.opacity = op;
    return textLines(x, y, lines, lh, pal, role, o);
  }

  /* ===== Opening figure: every post on the day it was published ===================== */
  var DAY0 = Date.UTC(2026, 10, 1);
  function dayOf(iso) { var m = iso.split('-'); return Math.round((Date.UTC(+m[0], +m[1] - 1, +m[2]) - DAY0) / 864e5) + 1; }
  var POSTS = [
    { iso: '2026-11-04', title: 'Why Psyche keeps a blog' },
    { iso: '2026-11-10', title: 'Three questions a test answers before its number counts' },
    { iso: '2026-11-13', title: 'Testing the test before the model: a random player at 22%' }
  ];
  var TODAY = '2026-11-16';

  function makeDays(o) {
    var W = o.w, H = o.h, wide = o.kind === 'wide', base = o.base;
    var d0 = dayOf(POSTS[0].iso), dT = dayOf(TODAY);
    var x0 = wide ? Math.max(o.right + 90, W * 0.3) : 30, xT = W - (wide ? 130 : 40);
    var sp = (xT - x0) / (dT - d0);
    var fs = wide ? 24 : 15, lh = Math.round(fs * 1.28), maxc = wide ? 22 : 26;
    var below = H - base - (wide ? 44 : 28), above = base - (wide ? 96 : 70);
    // where the days are close together (a narrower desktop), the newest post hangs below the line too
    var compact = wide && sp < 46;
    // on a phone the posts hang at three depths, oldest shallowest, so a title only passes stems that end above it
    var lens = wide ? [Math.min(above, Math.max(o.cap * 1.14, above * 0.8)), below * 0.66, compact ? below * 0.3 : Math.min(above, Math.max(o.cap * 0.72, above * 0.42))] : [Math.max(56, below * 0.16), Math.max(100, below * 0.4), below * 0.8];
    var dirs = wide ? [-1, 1, compact ? 1 : -1] : [1, 1, 1];
    var posts = POSTS.map(function (p, i) {
      var d = dayOf(p.iso), x = x0 + (d - d0) * sp, anchor, room;
      // a title takes the side with room, as many characters a line as that room holds, in balanced lines
      if (wide) {
        room = Math.floor((W - (compact ? 8 : 24) - x - 16) / (fs * 0.5));
        anchor = room >= 16 ? 'start' : 'end';
        if (anchor === 'end') room = Math.floor((x - 16 - 8) / (fs * 0.5));
      } else {
        anchor = i === 0 ? 'start' : 'end';
        room = Math.floor((anchor === 'start' ? W - x - 16 - 12 : x - 16 - 12) / (fs * 0.5));
      }
      // on a phone the first title stops short of the next post's stem
      if (!wide && i === 0) room = Math.min(room, Math.floor((x0 + (dayOf(POSTS[1].iso) - d0) * sp - x - 16 - 14) / (fs * 0.5)));
      var lines = balanced(p.title, Math.max(9, Math.min(compact ? 18 : maxc, room)));
      var hy = base + dirs[i] * lens[i];
      // a title hanging below the line keeps its last line inside the figure
      if (dirs[i] > 0) hy = Math.min(hy, H - 14 - (lines.length - 1) * lh - 5);
      return { d: d, x: x, hy: hy, dir: dirs[i], lines: lines, anchor: anchor, lx: anchor === 'start' ? x + 16 : x - 16, ly: hy + 5 };
    });
    if (!wide) {
      // on a phone the titles stack downward, shallowest first, each clear of the one above it
      var bottom = function (q) { return q.hy + 5 + (q.lines.length - 1) * lh; };
      [[0, 1], [1, 2]].forEach(function (pr) {
        var up = posts[pr[0]], dn = posts[pr[1]], min = bottom(up) + lh + 14;
        if (dn.hy < min) { dn.hy = Math.min(min, H - 14 - (dn.lines.length - 1) * lh - 5); dn.ly = dn.hy + 5; }
      });
    }
    return {
      key: (o.key || o.kind) + ':' + Math.round(W) + 'x' + Math.round(H) + ':' + Math.round(base) + ':' + Math.round(o.right) + ':' + (o.gap ? Math.round(o.gap[0]) : ''),
      gap: o.gap || null,
      view: { w: Math.round(W), h: Math.round(H) }, wide: wide, base: base, x0: x0, xT: xT, sp: sp, d0: d0, dT: dT,
      dMin: Math.floor(d0 - x0 / sp) - 1, dMax: Math.ceil(dT + (W - xT) / sp) + 1,
      posts: posts, fs: fs, lh: lh, cStart: d0 - 2.4, rate: 2.7
    };
  }
  function dx(m, d) { return m.x0 + (d - m.d0) * m.sp; }

  // The front is drawn in parts, each rewritten only when its own text changes: the day ticks
  // (only when the light passes a day), the posts (only while one rises), and the light itself.
  // The figure fills the screen, so its moving layer carries no blur filter (frontGlow: false):
  // the lit line, the stems and the light draw their own close halo with S.glowPath.
  function drawDays(m, s, pal) {
    var back = '', ticks = '', posts = '', trail = '', cursor = '', labels = '', W = m.view.w, b = m.base, c = s.c;
    var xc = dx(m, clamp(c, m.dMin, m.dT));
    // the line of days: faint everywhere, brighter where the days have passed
    var G = m.gap, inG = function (x) { return G && x > G[0] - 2 && x < G[1] + 2; };
    // a line from x1 to x2, opened where the g passes
    function seg(x1, x2, role, w, op, shine) {
      if (x2 <= x1) return '';
      var ln = shine ? function (a, z) { return S.glowPath([[a, b], [z, b]], pal, role, w, { opacity: op }); } : function (a, z) { return S.line(a, b, z, b, pal, role, w, op); };
      if (!G || x2 <= G[0] || x1 >= G[1]) return ln(x1, x2);
      return (G[0] > x1 ? ln(x1, G[0]) : '') + (x2 > G[1] ? ln(G[1], x2) : '');
    }
    back += seg(0, W, 'faint', 1);
    trail += seg(0, clamp(xc, 0, W), 'soft', 1.2, 0.9, true);
    for (var d = m.dMin; d <= m.dMax; d++) {
      var x = dx(m, d); if (x < -2 || x > W + 2 || inG(x)) continue;
      var mon = ((d - 2) % 7 + 7) % 7 === 0, len = mon ? 13 : 6, future = d > m.dT;
      var fade = clamp(x / (W * 0.4), 0.3, 1) * (future ? 0.5 : 1);
      ticks += S.line(x, b + 4, x, b + 4 + len, pal, d <= c ? 'soft' : 'faint', 1, fade);
    }
    // the posts
    m.posts.forEach(function (p) {
      var g = ease((c - p.d) / 0.75); if (g <= 0) return;
      var y = b + (p.hy - b) * g;
      var y0 = inG(p.x) ? b + G[2] : b; // a stem behind the g starts below its tail
      if (y > y0 || y < b) posts += S.glowPath([[p.x, y0], [p.x, y]], pal, 'ink', 1.25, { opacity: 0.8 });
      if (!inG(p.x)) posts += S.dot(p.x, b, 3, pal, 'ink');
      posts += halo(p.x, y, 15, pal, 'peri', 0.13 * g) + S.dot(p.x, y, 4.4, pal, 'peri');
      if (g > 0.55) labels += textOp(p.lx, p.ly, p.lines, m.lh, pal, 'ink', { size: m.fs, anchor: p.anchor }, clamp((g - 0.55) / 0.45, 0, 1));
    });
    // today: the cursor rests there
    if (c >= m.dT - 0.02) labels += S.text(m.xT, b + (m.wide ? 44 : 40), 'today', pal, 'soft', { size: m.fs - 1, anchor: 'middle' });
    if (c > m.dMin) {
      cursor += S.glowPath([[xc, b - 22], [xc, b + 22]], pal, 'mint', 1.3);
      cursor += halo(xc, b, 13, pal, 'mint', 0.16) + S.dot(xc, b, 3.6, pal, 'mint');
    }
    return { back: back, front: { trail: trail, ticks: ticks, posts: posts, cursor: cursor }, labels: clear(labels, pal, 5) };
  }
  function describeDays(m, s) {
    var shown = m.posts.filter(function (p) { return s.c >= p.d; }).map(function (p) { return p.lines.join(' '); });
    var t = 'A line of days, with a light that moves along it. ';
    if (!shown.length) return t + 'No post has appeared yet at this point of the line.';
    t += 'Posts standing on the days they were published, oldest first: ' + shown.join('; ') + '.';
    if (s.c >= m.dT - 0.02) t += ' The light rests on today.';
    return t;
  }
  // The opening's layout comes from the page: where the word "Blog" stands and where it ends.
  function heroBox(box) {
    var sec = document.querySelector('.b-open'), real = sec && sec.querySelector('.b-title'), art = sec && sec.querySelector('.k-art');
    var wide = box.width > 700;
    if (!real || !art) return { base: box.height * 0.56, right: box.width * 0.4, cap: box.height * 0.2, wide: wide, gap: null };
    // measure a hidden copy without the arrival styles, so the layout is the settled one even while the title eases in
    var h1 = real.cloneNode(true); h1.removeAttribute('id'); h1.classList.remove('k-open-title'); h1.setAttribute('aria-hidden', 'true');
    h1.style.visibility = 'hidden'; h1.style.transition = 'none';
    real.parentNode.appendChild(h1);
    var mk = h1.querySelector('.b-base');
    var fs = parseFloat(getComputedStyle(h1).fontSize) || 200;
    var base = h1.offsetTop + mk.offsetTop - art.offsetTop;
    var right = h1.offsetLeft + mk.offsetLeft - art.offsetLeft;
    // where the tail of the g passes below the line: the line opens there, so the letter never cuts through a stroke
    var g = h1.querySelector('.b-g'), gap = null;
    if (g) { var gl = h1.offsetLeft + g.offsetLeft - art.offsetLeft; gap = [gl - fs * 0.05, gl + g.offsetWidth - fs * 0.08, fs * 0.15 + 8]; }
    h1.parentNode.removeChild(h1);
    return { base: base, right: right, cap: fs * 0.7, wide: wide, gap: gap };
  }
  var DAYS_EXPORT = makeDays({ w: 1600, h: 760, base: 430, right: 60, cap: 220, kind: 'wide', key: 'export' });
  P.figure({
    id: 'days', name: 'posts-on-their-days', title: 'Every post on the day it was published',
    caption: 'Each post stands on the day it was published.',
    model: DAYS_EXPORT,
    modelFor: function (box) {
      var h = heroBox(box);
      return makeDays({ w: box.width, h: box.height, base: h.base, right: h.right, cap: h.cap, gap: h.gap, kind: h.wide ? 'wide' : 'narrow' });
    },
    initialState: function (m) { return { c: m.cStart }; },
    stillState: function (m) { return { c: m.dT }; },
    tick: function (m, s, dt) { return { c: Math.min(m.dT, s.c + dt * m.rate) }; },
    settled: function (m, s) { return s.c >= m.dT; },
    draw: drawDays, describe: describeDays, frontGlow: false,
    handle: function (m, s) { return [dx(m, clamp(s.c, m.dMin, m.dT)), m.base]; },
    // The story by itself: the light walks the days and stops on each post as it rises, then rests on today.
    sequence: (function () {
      var d = POSTS.map(function (p) { return dayOf(p.iso) + 0.85; });
      return [
        { dur: 1900, tick: false, to: { c: d[0] } },
        { dur: 900, tick: false },
        { dur: 2600, tick: false, to: { c: d[1] } },
        { dur: 900, tick: false },
        { dur: 1700, tick: false, to: { c: d[2] } },
        { dur: 900, tick: false },
        { dur: 1500, tick: false, to: function (m) { return { c: m.dT }; } },
        { dur: 400, tick: false }
      ];
    })(),
    keysLabel: 'Left and right arrow keys move one day.',
    keys: {
      ArrowRight: function (m, s) { return { c: Math.min(m.dT, Math.floor(s.c + 1e-6) + 1) }; },
      ArrowLeft: function (m, s) { return { c: Math.max(m.cStart, Math.ceil(s.c - 1e-6) - 1) }; },
      Home: function (m) { return { c: m.cStart }; },
      End: function (m) { return { c: m.dT }; }
    },
    drag: {
      pick: function (m, s, p) { return Math.abs(p[1] - m.base) < Math.max(90, m.view.h * 0.22); },
      move: function (m, s, p) { return { c: clamp(m.d0 + (p[0] - m.x0) / m.sp, m.cStart, m.dT) }; }
    }
  });

})(window.Psyche);
