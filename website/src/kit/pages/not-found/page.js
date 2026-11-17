(function (P) {
  'use strict';
  var S = P.svg;
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function ease(u) { u = clamp(u, 0, 1); return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; }

  // The corridor: one route from the way back to the dead end, and side corridors that also end.
  // Everything is in view units, which are the pixels of the box the figure fills.
  function makeCorridor(o) {
    var W = o.w, H = o.h, wide = o.kind === 'wide';
    var route, sides;
    if (wide) {
      var sx = o.start, y0 = o.startY || H * 0.56, xa = Math.max(sx + 140, (o.clear || 0) + 72, W * 0.36), ya = H * 0.2, xb = Math.max(W * 0.6, xa + 200), yb = H * 0.38, xe = W * 0.84;
      route = [[sx, y0], [xa, y0], [xa, ya], [xb, ya], [xb, yb], [xe, yb]];
      sides = [
        [[xa, y0], [xa + (xb - xa) * 0.7, y0]],
        [[xb, ya], [W * 0.76, ya]],
        [[xa, ya], [xa, H * 0.11]],
        [[(xb + xe) / 2, yb], [(xb + xe) / 2, H * 0.27]]
      ];
    } else {
      var px = 22, qy = H * 0.84, ax = W * 0.34, ay = H * 0.4, bx = W * 0.74, by = H * 0.22, ex = W - 26;
      route = [[px, qy], [ax, qy], [ax, ay], [bx, ay], [bx, by], [ex, by]];
      sides = [
        [[ax, qy], [W * 0.78, qy]],
        [[ax, ay], [ax, H * 0.12]],
        [[bx, ay], [bx, H * 0.62]]
      ];
    }
    var len = [0];
    for (var i = 1; i < route.length; i++) len.push(len[i - 1] + Math.hypot(route[i][0] - route[i - 1][0], route[i][1] - route[i - 1][1]));
    return { key: o.kind + ':' + Math.round(W) + 'x' + Math.round(H) + ':' + Math.round(o.start || 0) + ':' + Math.round(o.startY || 0) + ':' + Math.round(o.clear || 0), view: { w: Math.round(W), h: Math.round(H) },
      wide: wide, route: route, sides: sides, len: len, total: len[len.length - 1], wall: wide ? 15 : 12 };
  }
  // a point at distance d along the route, and the route up to it
  function at(m, d) {
    d = clamp(d, 0, m.total);
    for (var i = 1; i < m.route.length; i++) {
      if (d <= m.len[i] || i === m.route.length - 1) {
        var a = m.route[i - 1], b = m.route[i], u = (d - m.len[i - 1]) / Math.max(1e-6, m.len[i] - m.len[i - 1]);
        return { p: [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u], i: i };
      }
    }
  }
  function upTo(m, d) { var q = at(m, d), pts = m.route.slice(0, q.i); pts.push(q.p); return pts; }

  // time: 0..1 out to the wall, 1..1.35 at the wall, 1.35..2.35 back to the start
  var OUT = 1, HOLD = 1.35, END = 2.35;
  function where(m, t) {
    if (t <= OUT) return { d: ease(t) * m.total, back: false };
    if (t <= HOLD) { var k = (t - OUT) / (HOLD - OUT); return { d: m.total - Math.sin(k * Math.PI) * 3, back: k > 0.5 }; }
    return { d: (1 - ease((t - HOLD) / (END - HOLD))) * m.total, back: true };
  }

  // The corridors are static (back). The front is in parts, each rewritten only when its own text
  // changes: the stretch walked, the wall, the way back and the point.
  function draw(m, s, pal) {
    var back = '', trail = '', wall = '', again = '', point = '', w = where(m, s.t), q = at(m, w.d), e = m.route[m.route.length - 1], pre = m.route[m.route.length - 2];
    // the corridors, faint; their ends closed by a short wall
    function wallAt(a, b, len, role, wd, op) {
      var dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L;
      return S.line(b[0] + nx * len, b[1] + ny * len, b[0] - nx * len, b[1] - ny * len, pal, role, wd, op);
    }
    back += S.path(m.route, pal, 'faint', 1);
    m.sides.forEach(function (sd) { back += S.path(sd, pal, 'faint', 1) + wallAt(sd[0], sd[1], m.wall * 0.6, 'faint', 1); });
    // the start: an open end, a small ring
    back += S.circle(m.route[0][0], m.route[0][1], 5, pal, 'quiet', 1);
    // how far the light has been
    var reach = s.t >= OUT ? m.total : w.d;
    if (reach > 1) trail += S.path(upTo(m, reach), pal, 'soft', 1.2, { opacity: 0.85 });
    // the dead end: the wall lights when the point meets it
    var hit = s.t < OUT ? 0 : s.t <= HOLD + 0.3 ? 1 - Math.max(0, s.t - HOLD) / 0.3 * 0.6 : 0.4;
    wall += wallAt(pre, e, m.wall, hit > 0 ? 'mint' : 'quiet', 1.4, hit > 0 ? 0.35 + 0.65 * hit : 1);
    // on the way back, the stretch already walked again
    if (w.back && w.d < m.total) {
      var seg = [q.p].concat(m.route.slice(at(m, w.d).i)); seg[seg.length - 1] = e;
      again += S.path(seg, pal, 'peri', 1.1, { opacity: 0.55, dash: '3 6' });
    }
    // the point
    var x = q.p[0], y = q.p[1];
    if (pal.glow) point += S.dot(x, y, 16, pal, 'mint', 0.14);
    else point += S.circle(x, y, 11, pal, 'mint', 0.9, 0.5);
    point += S.dot(x, y, 4.6, pal, 'mint');
    return { back: back, front: { trail: trail, wall: wall, again: again, point: point } };
  }
  function describe(m, s) {
    var t = 'A corridor of thin lines with side corridors that end in walls, and a point of light. ';
    if (s.t <= 0.02) return t + 'The light waits at the open end of the corridor.';
    if (s.t < OUT) return t + 'The light moves along the corridor toward its far end.';
    if (s.t <= HOLD) return t + 'The light has reached the wall at the dead end.';
    if (s.t < END - 0.02) return t + 'The light has met the wall at the dead end and is on its way back to the start.';
    return t + 'The light has met the wall at the dead end and is back at the start.';
  }
  // the corridor opens beside the way back: it starts just right of the link, level with its middle,
  // and climbs only right of the title
  function startOf(box) {
    // offsets, not screen rectangles, so the layout read is the settled one even while the arrival eases in
    var sec = document.querySelector('.nf'), a = document.querySelector('.nf__back'), t = document.querySelector('.nf__title');
    if (!sec || !a || !t || box.width <= 700) return [0, 0, 0];
    function off(el) { var x = 0, y = 0; while (el && el !== sec) { x += el.offsetLeft; y += el.offsetTop; el = el.offsetParent; } return [x, y]; }
    var pa = off(a), pt = off(t), right = 0;
    Array.prototype.forEach.call(t.children, function (sp) { var r = document.createRange(); r.selectNodeContents(sp); right = Math.max(right, r.getBoundingClientRect().width); });
    return [pa[0] + a.offsetWidth + 34, pa[1] + a.offsetHeight * 0.55, pt[0] + right];
  }
  P.figure({
    id: 'deadend', name: 'dead-end', title: 'A point of light at a dead end',
    caption: 'A point of light reaches a dead end and turns back.',
    model: makeCorridor({ w: 1600, h: 900, start: 300, startY: 500, clear: 610, kind: 'wide' }),
    modelFor: function (box) {
      var st = startOf(box);
      return makeCorridor({ w: box.width, h: box.height, start: st[0], startY: st[1], clear: st[2], kind: box.width > 700 ? 'wide' : 'narrow' });
    },
    initialState: function () { return { t: 0 }; },
    stillState: function () { return { t: END }; },
    tick: function (m, s, dt) {
      var sp = s.t < OUT ? 0.3 : s.t < HOLD ? 0.7 : 0.34;
      return { t: Math.min(END, s.t + dt * sp) };
    },
    settled: function (m, s) { return s.t >= END; },
    draw: draw, describe: describe,
    handle: function (m, s) { return at(m, where(m, s.t).d).p; },
    // The story by itself: out along the corridor, the wall, a short hold, and back to the start.
    sequence: [
      { dur: 3600, tick: false, to: { t: OUT }, ease: 'linear' },
      { dur: 700, tick: false, to: { t: HOLD }, ease: 'linear' },
      { dur: 700, tick: false },
      { dur: 3200, tick: false, to: { t: END }, ease: 'linear' },
      { dur: 600, tick: false }
    ],
    keysLabel: 'Right and left arrow keys move the light forward and back in time.',
    keys: {
      ArrowRight: function (m, s) { return { t: Math.min(END, s.t + 0.1) }; },
      ArrowLeft: function (m, s) { return { t: Math.max(0, s.t - 0.1) }; },
      Home: function () { return { t: 0 }; },
      End: function () { return { t: END }; }
    }
  });
})(window.Psyche);
