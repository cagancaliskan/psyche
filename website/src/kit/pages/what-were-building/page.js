/* ===== Shared helpers ===================================================================== */
(function (P) {
  'use strict';
  var S = P.svg;
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function ease(u) { u = clamp(u, 0, 1); return u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2; }
  function lerp(a, b, u) { return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u]; }
  function dist(a, b) { return Math.hypot(a[0] - b[0], a[1] - b[1]); }
  function h01(a, b) { var x = Math.sin(a * 127.1 + b * 311.7 + 0.5) * 43758.5453; return x - Math.floor(x); }
  // the soft light around a point: a blurred disc in dark, a thin ring in light and print
  function halo(x, y, r, pal, role, op) {
    return pal.glow ? S.dot(x, y, r, pal, role, op) : S.circle(x, y, r * 0.72, pal, role, 0.8, Math.min(0.6, op * 3.2));
  }
  // After the reader acts on a figure (its sequence has yielded to them), the figure's own motion plays
  // out what they started. The kit stops a figure's loop while the reader drags or presses keys, so the
  // page moves it on itself, one frame at a time through handle.set(s, { quiet: true }), and only while
  // the kit is not moving it (H.kitT: the last time the kit called the figure's tick). It stops when the
  // figure settles, when its sequence plays again or it goes out of view, and while the page leaves.
  // Never under reduced motion: the state the reader made already shows the end.
  function driver(H) {
    var raf = 0, last = 0, root = document.documentElement;
    H.kitT = 0;
    function frame(t) {
      raf = 0;
      var h = H.fig;
      if (!h || !H.m || h.sequence !== 'yielded' || document.hidden || root.classList.contains('k-leaving')) { last = 0; return; }
      var dt = last ? Math.min(0.1, (t - last) / 1000) : 0; last = t;
      var s = h.state;
      if (H.settled(H.m, s)) { last = 0; return; }
      if (dt > 0 && performance.now() - H.kitT > 80) {
        H.own = true;
        try { s = H.tick(H.m, s, dt); } finally { H.own = false; }
        h.set(s, { quiet: true });
      }
      raf = requestAnimationFrame(frame);
    }
    return function () { if (!raf && !P.reducedMotion()) { last = 0; raf = requestAnimationFrame(frame); } };
  }
  // the figure's tick, seen by the driver: the live model, and when the kit itself last moved it
  function watch(H, tick) { H.tick = tick; return function (m, s, dt) { H.m = m; if (!H.own) H.kitT = performance.now(); return tick(m, s, dt); }; }
  // points spread evenly but not on a grid
  function scatter(rng, n, dmin, inside, b) {
    var pts = [], tries = 0, max = n * 80;
    while (pts.length < n && tries++ < max) {
      var x = b[0] + rng() * (b[2] - b[0]), y = b[1] + rng() * (b[3] - b[1]);
      if (!inside(x, y)) continue;
      var ok = true;
      for (var i = 0; i < pts.length; i++) { var dx = pts[i][0] - x, dy = pts[i][1] - y; if (dx * dx + dy * dy < dmin * dmin) { ok = false; break; } }
      if (ok) pts.push([x, y]);
    }
    return pts;
  }
  // each point joined to its nearest neighbours
  function knn(pts, k, maxD, ok) {
    var edges = [], seen = {};
    pts.forEach(function (p, i) {
      var c = [];
      pts.forEach(function (q, j) { if (j !== i) { var d = dist(p, q); if (d < maxD) c.push([d, j]); } });
      c.sort(function (a, b) { return a[0] - b[0]; });
      var n = 0;
      for (var z = 0; z < c.length && n < k; z++) {
        var j = c[z][1], key = i < j ? i + '-' + j : j + '-' + i;
        if (seen[key]) { n++; continue; }
        if (ok && !ok(i, j)) continue;
        seen[key] = 1; edges.push([Math.min(i, j), Math.max(i, j)]); n++;
      }
    });
    return edges;
  }
  function adjOf(n, edges) {
    var adj = [], i;
    for (i = 0; i < n; i++) adj.push([]);
    edges.forEach(function (e, k) { adj[e[0]].push([e[1], k]); adj[e[1]].push([e[0], k]); });
    return adj;
  }
  function dijkstra(n, adj, lens, src) {
    var d = [], prev = [], done = [], i;
    for (i = 0; i < n; i++) { d.push(Infinity); prev.push(-1); done.push(false); }
    d[src] = 0;
    for (var it = 0; it < n; it++) {
      var b = -1, bd = Infinity;
      for (i = 0; i < n; i++) if (!done[i] && d[i] < bd) { bd = d[i]; b = i; }
      if (b < 0) break;
      done[b] = true;
      adj[b].forEach(function (a) { var nd = bd + lens[a[1]]; if (nd < d[a[0]]) { d[a[0]] = nd; prev[a[0]] = b; } });
    }
    return { dist: d, prev: prev };
  }
  function inRect(x, y, r) { return x >= r[0] && x <= r[2] && y >= r[1] && y <= r[3]; }
  function crosses(a, b, rects, skip) {
    for (var k = 1; k < 20; k++) {
      var u = k / 20, x = a[0] + (b[0] - a[0]) * u, y = a[1] + (b[1] - a[1]) * u;
      if (skip && Math.hypot(x - skip[0], y - skip[1]) < skip[2]) continue;
      for (var r = 0; r < rects.length; r++) if (inRect(x, y, rects[r])) return true;
    }
    return false;
  }
  // the nearest point lying roughly in a direction, for arrow keys
  function towards(pts, from, dir, maxD, skip) {
    var best = from, bs = Infinity, p = pts[from];
    pts.forEach(function (q, i) {
      if (i === from || (skip && skip(i))) return;
      var vx = q[0] - p[0], vy = q[1] - p[1], d = Math.hypot(vx, vy);
      if (d > maxD || d < 1) return;
      var c = (vx * dir[0] + vy * dir[1]) / d;
      if (c < 0.45) return;
      var sc = d * (2.2 - c * 1.2);
      if (sc < bs) { bs = sc; best = i; }
    });
    return best;
  }
  function nearest(pts, p, maxD, skip) {
    var best = -1, bd = maxD == null ? Infinity : maxD;
    pts.forEach(function (q, i) { if (skip && skip(i)) return; var d = dist(p, q); if (d < bd) { bd = d; best = i; } });
    return best;
  }
  // connections as gentle curves: a control point beside the middle, to one side or the other
  function bend(a, b, seed, amt) {
    var mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2, dx = b[0] - a[0], dy = b[1] - a[1];
    var k = (h01(seed, 3.7) - 0.5) * 2 * amt;
    return [mx - dy * k, my + dx * k];
  }
  function qpt(a, c, b, u) { var v = 1 - u; return [v * v * a[0] + 2 * v * u * c[0] + u * u * b[0], v * v * a[1] + 2 * v * u * c[1] + u * u * b[1]]; }
  function qpts(a, c, b, u0, u1, n) { var out = []; n = n || 10; for (var i = 0; i <= n; i++) out.push(qpt(a, c, b, u0 + (u1 - u0) * i / n)); return out; }
  function qline(a, c, b, pal, role, w, op) { return '<path d="M' + S.n(a[0]) + ' ' + S.n(a[1]) + 'Q' + S.n(c[0]) + ' ' + S.n(c[1]) + ' ' + S.n(b[0]) + ' ' + S.n(b[1]) + '" ' + S.stroke(pal, role, w, op) + '/>'; }
  // a curve's path data, and many points or segments in one path (a point is a round cap on a zero-length stroke)
  function qd(a, c, b) { return 'M' + S.n(a[0]) + ' ' + S.n(a[1]) + 'Q' + S.n(c[0]) + ' ' + S.n(c[1]) + ' ' + S.n(b[0]) + ' ' + S.n(b[1]); }
  function dotsD(pts) { var d = ''; for (var i = 0; i < pts.length; i++) d += 'M' + S.n(pts[i][0]) + ' ' + S.n(pts[i][1]) + 'h0'; return d; }
  function dots(pts, rad, pal, role, op) {
    if (!pts.length) return '';
    if (pal.dash[role]) { var s = ''; pts.forEach(function (p) { s += S.dot(p[0], p[1], rad, pal, role, op); }); return s; }
    return '<path d="' + dotsD(pts) + '" ' + S.stroke(pal, role, 2 * rad / pal.weight, op) + '/>';
  }
  function halos(pts, r, pal, role, op) {
    if (pal.glow) return dots(pts, r, pal, role, op);
    var s = ''; pts.forEach(function (p) { s += halo(p[0], p[1], r, pal, role, op); }); return s;
  }
  function segsD(list) { var d = ''; for (var i = 0; i < list.length; i++) d += 'M' + S.n(list[i][0][0]) + ' ' + S.n(list[i][0][1]) + 'L' + S.n(list[i][1][0]) + ' ' + S.n(list[i][1][1]); return d; }

  // Elements as data, for figures that change a few attributes a frame: draw writes them as text (stills,
  // exports, the first frame), update brings the same elements up to date in place (nothing is parsed or
  // rebuilt; a new element is added, a gone one removed, a changed attribute set).
  function ns(x) { return String(S.n(x)); }
  function sa(pal, r, w, op) {
    var c = pal[r], a = { fill: 'none', stroke: c[0], 'stroke-width': ns(w * pal.weight), 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-opacity': ns(c[1] * (op == null ? 1 : op)) };
    if (pal.dash[r]) a['stroke-dasharray'] = pal.dash[r];
    return a;
  }
  function fa(pal, r, op) { var c = pal[r]; return { fill: c[0], 'fill-opacity': ns(c[1] * (op == null ? 1 : op)) }; }
  function item(k, t, a) { return { k: k, t: t, a: a }; }
  function itemText(it) { var s = '<' + it.t + ' data-q="' + it.k + '"'; for (var n in it.a) s += ' ' + n + '="' + it.a[n] + '"'; return s + '/>'; }
  function itemsText(list) { var s = ''; for (var i = 0; i < list.length; i++) s += itemText(list[i]); return s; }
  function bindPart(g) {
    var map = new Map(), kids = g.children;
    for (var i = 0; i < kids.length; i++) {
      var e = kids[i], k = e.getAttribute('data-q'); if (k == null) continue;
      var a = {}; for (var j = 0; j < e.attributes.length; j++) { var at = e.attributes[j]; if (at.name !== 'data-q') a[at.name] = at.value; }
      map.set(k, { el: e, a: a, s: 0 });
    }
    return { g: g, map: map, stamp: 0 };
  }
  // fixed: an element's attributes never change once it is there (only whether it is there)
  function syncPart(st, list, fixed) {
    var stamp = ++st.stamp, html = '', fresh = [], map = st.map, i;
    for (i = 0; i < list.length; i++) {
      var it = list[i], r = map.get(it.k);
      if (r) { r.s = stamp; if (!fixed) { var a = it.a, ra = r.a; for (var n in a) if (ra[n] !== a[n]) { r.el.setAttribute(n, a[n]); ra[n] = a[n]; } } }
      else { html += itemText(it); fresh.push(it); }
    }
    map.forEach(function (r, k) { if (r.s !== stamp) { r.el.remove(); map.delete(k); } });
    if (html) {
      st.g.insertAdjacentHTML('beforeend', html);
      var kids = st.g.children, n0 = kids.length - fresh.length;
      for (i = 0; i < fresh.length; i++) map.set(fresh[i].k, { el: kids[n0 + i], a: fresh[i].a, s: stamp });
    }
  }
  // the bound parts of a live figure, read again from the page after every full draw (draw bumps m.__gen)
  function keyed(m, holder, groups) {
    var kd = m.__kd;
    if (!kd || kd.gen !== m.__gen || kd.holder !== holder) {
      var b = {}; for (var k in groups) if (groups[k]) b[k] = bindPart(groups[k]);
      kd = m.__kd = { gen: m.__gen, holder: holder, parts: b };
    }
    return kd.parts;
  }
  P.wwb = { clamp: clamp, ease: ease, lerp: lerp, dist: dist, h01: h01, halo: halo, driver: driver, watch: watch, scatter: scatter, knn: knn,
    adjOf: adjOf, dijkstra: dijkstra, inRect: inRect, crosses: crosses, towards: towards, nearest: nearest,
    bend: bend, qpt: qpt, qpts: qpts, qline: qline, qd: qd, dots: dots, halos: halos, segsD: segsD,
    ns: ns, sa: sa, fa: fa, item: item, itemsText: itemsText, bindPart: bindPart, syncPart: syncPart, keyed: keyed };
})(window.Psyche);

/* ===== Opening: a pulse leaves the full stop and runs into a deep field of model neurons ===== */
(function (P) {
  'use strict';
  var S = P.svg, U = P.wwb, H = { fig: null };
  // the layout used for the exported stills: a 1600 by 900 screen, the title in the lower left
  // (measured from the page at that size)
  var EXPORT = { w: 1600, h: 900, fs: 88, top: 74, lines: [[32, 606, 440, 713], [32, 697, 501, 804]], blocks: [[581, 450, 967, 797]], dotRight: true,
    dot: [489.5, 776.25], foot: [32, 801, 722, 878], print: [[32, 691, 'New era of'], [32, 781, 'intelligence.']], fade: 64,
    printLead: { size: 21, lines: [[581, 473, 'Today\'s AI has read the whole internet'], [581, 504, 'and still has no map of the room it\'s in. A'], [581, 536, 'brain builds that map just by walking'], [581, 567, 'around, on twenty watts. We\'re building'], [581, 599, 'machines the way nature built minds:'], [581, 630, 'neurons that spike, connections that'], [581, 662, 'teach themselves, networks that draw'], [581, 693, 'their own map of the world. They won\'t'], [581, 725, 'just answer. They\'ll know where they are,'], [581, 756, 'learn as they go, and run on a fraction of'], [581, 788, 'the power.']] } };

  // where the title, its full stop and the controls stand, measured from the page (layout, not the arrival's motion)
  function measure(box) {
    var sec = document.querySelector('.w-open');
    if (!sec) return null;
    function off(el) { var x = 0, y = 0; while (el && el !== sec) { x += el.offsetLeft; y += el.offsetTop; el = el.offsetParent; } return [x, y]; }
    var h1 = sec.querySelector('.w-title'), fs = parseFloat(getComputedStyle(h1).fontSize) || 160;
    var lines = Array.prototype.map.call(sec.querySelectorAll('.w-ink'), function (e) { var o = off(e); return [o[0], o[1], o[0] + e.offsetWidth, o[1] + e.offsetHeight]; });
    var d = sec.querySelector('.w-dot'), od = off(d), foot = sec.querySelector('.w-open__foot'), of = off(foot);
    var lead = sec.querySelector('.w-lead'), ol = off(lead);
    return { w: box.width, h: box.height, fs: fs, top: box.width <= 700 ? 58 : 74, lines: lines,
      blocks: [[ol[0], ol[1], ol[0] + lead.offsetWidth, ol[1] + lead.offsetHeight]], dotRight: true,
      dot: [od[0] + d.offsetWidth * 0.5, od[1] + d.offsetHeight * 0.79 - fs * 0.06],
      foot: [of[0], of[1], of[0] + foot.offsetWidth, of[1] + foot.offsetHeight], fade: box.width <= 700 ? 44 : 64 };
  }

  // A camera looks into a deep volume of cells. The volume fills the whole screen at every depth;
  // its vanishing point sits up and to the right, away from the title.
  function makeDeep(o) {
    var W = Math.round(o.w), Hh = Math.round(o.h), narrow = W <= 700, rng = P.mulberry(o.seed || (narrow ? 19 : 7));
    var cx = W * (o.vx != null ? o.vx : narrow ? 0.56 : 0.66), cy = Hh * (o.vy != null ? o.vy : narrow ? 0.3 : 0.34), f = narrow ? W * 1.15 : Math.min(W, Hh * 1.6) * 0.9;
    var Z0 = 1.15, Z1 = 10, n = Math.round((narrow ? 230 : U.clamp(W * Hh / 3000, 300, 470)) * (o.density || 1));
    var px = o.pad != null ? o.pad : Math.max(10, o.fs * 0.07), py = o.pad != null ? o.pad : Math.max(4, o.fs * 0.02);
    var holes = o.lines.map(function (r) { return [r[0] - px, r[1] - py, r[2] + px, r[3] + py]; });
    if (o.foot) holes.push([o.foot[0] - 14, o.foot[1] - 14, o.foot[2] + 14, o.foot[3] + 10]);
    // other words (the sentences beside the title) keep a clear field around them too
    (o.blocks || []).forEach(function (b) { holes.push([b[0] - 18, b[1] - 16, b[2] + 18, b[3] + 12]); });
    // the field thins out before the bottom of the screen instead of being cut by it
    if (o.fade) holes.push([-200, Hh - o.fade, W + 200, Hh + 400]);
    function free(x, y, pad) {
      if (y < o.top) return false;
      for (var i = 0; i < holes.length; i++) { var h = holes[i]; if (x >= h[0] - pad && x <= h[2] + pad && y >= h[1] - pad && y <= h[3] + pad) return false; }
      return true;
    }
    function scr(p) { return [cx + f * p[0] / p[2], cy + f * p[1] / p[2]]; }
    var world = [], pts = [], dep = [], size = [], guard = 0;
    // a box of cells seen from its near face: near cells spread over the whole screen, far cells
    // gather toward the vanishing point, so the field thickens into a lit mass in the distance
    var BX = (Math.max(cx, W - cx) + 80) * Z0 / f, BY = (Math.max(cy - o.top, Hh - cy) + 80) * Z0 / f;
    while (world.length < n && guard++ < n * 60) {
      var z = rng() < 0.45 ? Z0 * Math.pow(Z1 / Z0, rng()) : Z0 + (Z1 - Z0) * Math.pow(rng(), 0.7), gz = 1 + 0.2 * (z / Z0 - 1);
      var X = (rng() * 2 - 1) * BX * gz, Y = (rng() * 2 - 1) * BY * gz;
      var sx = cx + f * X / z, sy = cy + f * Y / z;
      if (sx < -80 || sx > W + 80 || sy > Hh + 80) continue;
      var s = Z0 / z, rad = (0.5 + 8.5 * Math.pow(s, 1.7)) * (0.75 + rng() * 0.5);
      // a soft edge around the words: the field thins out toward them instead of stopping at a straight line
      if (!free(sx, sy, rad + 10 + rng() * (26 + 50 * s))) continue;
      world.push([X, Y, z]); pts.push([sx, sy]); dep.push(s); size.push(rad);
    }
    var D = world.length;
    // the full stop is a near cell too
    var dz = Z0 * 1.05;
    world.push([(o.dot[0] - cx) * dz / f, (o.dot[1] - cy) * dz / f, dz]); pts.push([o.dot[0], o.dot[1]]); dep.push(Z0 / dz); size.push(2);
    function wd(i, j) { var a = world[i], b = world[j]; return Math.hypot(a[0] - b[0], a[1] - b[1], (a[2] - b[2]) * 0.8); }
    var edges = [], seen = {};
    function add(i, j) { var k = Math.min(i, j) + '-' + Math.max(i, j); if (seen[k]) return false; seen[k] = 1; edges.push([Math.min(i, j), Math.max(i, j)]); return true; }
    for (var i = 0; i < D; i++) {
      // the 14 nearest, in order (a short insertion list instead of sorting every cell)
      var c = [];
      for (var j = 0; j < D; j++) {
        if (j === i) continue;
        var dd = wd(i, j);
        if (c.length === 14 && dd >= c[13][0]) continue;
        var at = c.length; while (at > 0 && c[at - 1][0] > dd) at--;
        c.splice(at, 0, [dd, j]); if (c.length > 14) c.pop();
      }
      var got = 0;
      for (var q = 0; q < c.length && got < 3 && q < 14; q++) {
        if (U.crosses(pts[i], pts[c[q][1]], holes)) continue;
        add(i, c[q][1]); got++;
      }
    }
    // The full stop is the last letter of the title, so with o.dotRight a connection from it may pass
    // anywhere to its right (no letter is there); elsewhere it keeps clear of every hole.
    var nT = o.lines.length;
    function blockedD(x, y) {
      if (Math.hypot(x - o.dot[0], y - o.dot[1]) < o.fs * 0.2) return false;
      for (var h = 0; h < holes.length; h++) {
        if (o.dotRight && h < nT && x > o.dot[0] + 3) continue;
        var r = holes[h]; if (x >= r[0] && x <= r[2] && y >= r[1] && y <= r[3]) return true;
      }
      return false;
    }
    var cand = [];
    for (i = 0; i < D; i++) cand.push([wd(i, D), i]);
    cand.sort(function (a, b) { return a[0] - b[0]; });
    for (var nd = 0, k = 0; k < cand.length && nd < 6; k++) {
      var pa = pts[D], pb = pts[cand[k][1]], hit = false;
      for (var q0 = 1; q0 < 20 && !hit; q0++) hit = blockedD(pa[0] + (pb[0] - pa[0]) * q0 / 20, pa[1] + (pb[1] - pa[1]) * q0 / 20);
      if (hit) continue;
      add(cand[k][1], D); nd++;
    }
    var ctl = edges.map(function (e, k) { return U.bend(pts[e[0]], pts[e[1]], k + 1, 0.12); });
    // a connection whose curve bends into the clear space around the words is left out: no light behind text
    var keep = edges.map(function (e, k) {
      for (var q = 1; q < 24; q++) {
        var p = U.qpt(pts[e[0]], ctl[k], pts[e[1]], q / 24);
        if (e[0] === D || e[1] === D) { if (blockedD(p[0], p[1])) return false; continue; }
        for (var h = 0; h < holes.length; h++) if (U.inRect(p[0], p[1], holes[h])) return false;
      }
      return true;
    });
    edges = edges.filter(function (e, k) { return keep[k]; }); ctl = ctl.filter(function (c, k) { return keep[k]; });
    // the pulse runs at an even pace across the screen, so it is seen crossing the whole field
    var lens = edges.map(function (e) { return U.dist(pts[e[0]], pts[e[1]]) + 14; });
    var edep = edges.map(function (e) { return Math.min(dep[e[0]], dep[e[1]]); });
    // near cells are small neurons: a body and a few branches, at the scale of their depth
    var branches = pts.map(function (p, i) {
      var s = dep[i], out = [];
      if (i === D || s < 0.24) return out;
      var cnt = 5 + Math.floor(rng() * 3), a0 = rng() * 6.28;
      for (var b = 0; b < cnt; b++) {
        var a = a0 + b * 6.2832 / cnt + (rng() - 0.5) * 0.8, len = (22 + rng() * 44) * s * 1.8, bnd = (rng() - 0.5) * 0.9;
        var p1 = [p[0] + Math.cos(a) * size[i], p[1] + Math.sin(a) * size[i]];
        var p2 = [p[0] + Math.cos(a + bnd * 0.5) * len * 0.55, p[1] + Math.sin(a + bnd * 0.5) * len * 0.55];
        var p3 = [p[0] + Math.cos(a + bnd) * len, p[1] + Math.sin(a + bnd) * len];
        if (free(p3[0], p3[1], 4)) out.push([p1, p2, p3]);
      }
      return out;
    });
    // dust: the faint grain of the volume, never over the title
    var dust = [], dg = 0, dn = narrow ? 260 : 620;
    while (dust.length < dn && dg++ < dn * 20) {
      var x = rng() * W, y = o.top + rng() * (Hh - o.top), zz = rng();
      if (!free(x, y, 6)) continue;
      // denser toward the vanishing point
      if (Math.hypot((x - cx) / W, (y - cy) / Hh) > 0.25 + rng() * 0.75) continue;
      dust.push([x, y, 0.35 + zz * 0.9, 0.06 + 0.22 * zz]);
    }
    var m = { key: (o.tag || 'deep') + ':' + W + 'x' + Hh + ':' + Math.round(o.dot[0]) + ',' + Math.round(o.dot[1]) + ':' + Math.round(o.fs),
      view: { w: W, h: Hh }, pts: pts, dep: dep, size: size, edges: edges, lens: lens, ctl: ctl, edep: edep, branches: branches, dust: dust,
      adj: U.adjOf(pts.length, edges), D: D, fs: o.fs, narrow: narrow, speed: 1, waves: {}, holes: holes, noRing: !!o.noRing, qd: [], bd: [],
      edq: edep.map(q50), dq: dep.map(q50) };
    // the pulse crosses the whole field in a little over three seconds
    var raw = waveOf(m, D).max || 1;
    m.speed = raw / (narrow ? 3 : 3.6); m.waves = {};
    return m;
  }
  // one pulse from a cell: when every cell fires, and which connections carry it (most do, a few do not)
  function waveOf(m, src) {
    if (m.waves[src]) return m.waves[src];
    var n = m.pts.length, fire = [], done = [], tr = [], i;
    for (i = 0; i < n; i++) { fire.push(Infinity); done.push(false); }
    fire[src] = 0;
    for (var it = 0; it < n; it++) {
      var b = -1, bt = Infinity;
      for (i = 0; i < n; i++) if (!done[i] && fire[i] < bt) { bt = fire[i]; b = i; }
      if (b < 0) break;
      done[b] = true;
      m.adj[b].forEach(function (a) {
        var j = a[0], e = a[1];
        if (done[j]) return;
        if (b !== src && U.h01(e * 3 + 1, src + 7) > 0.86) return;
        var arr = bt + m.lens[e] / m.speed;
        tr.push({ e: e, a: b, b: j, t0: bt, t1: arr });
        if (arr + 0.03 < fire[j]) fire[j] = arr + 0.03;
      });
    }
    var mx = 0, reached = 0;
    fire.forEach(function (f) { if (f < Infinity) { reached++; if (f > mx) mx = f; } });
    return (m.waves[src] = { fire: fire, tr: tr, max: mx, reached: reached });
  }
  var backCache = {};
  function deepBack(m, pal) {
    var k = m.key + ':' + pal.name;
    if (backCache[k]) return backCache[k];
    var dark = pal.glow, B = bucket(pal);
    // the still field, batched: strokes of the same look share one path (widths to a tenth, opacities to
    // a fiftieth), so the page and its still carry a few hundred elements instead of thousands. The
    // groups are made from what is drawn (depth, size), never from the theme's paint, so the dark and
    // light drawings group alike and their stills fold into one.
    m.dust.forEach(function (d) { var r = Math.round(d[2] * 10) / 10, o = Math.round(d[3] * 50) / 50; B.dot(d[0], d[1], r, 'soft', dark ? o : o * 0.8, 'u' + r + '/' + o); });
    // far first, near last
    var order = m.edges.map(function (e, k) { return k; }).sort(function (a, b) { return m.edep[a] - m.edep[b]; });
    order.forEach(function (k) {
      var e = m.edges[k], s = q50(m.edep[k]);
      B.stroke(U.qd(m.pts[e[0]], m.ctl[k], m.pts[e[1]]), dark ? 'peri' : 'soft', 0.3 + 2 * Math.pow(s, 1.5), (dark ? 0.07 : 0.1) + 0.5 * s * s, 'e' + s);
    });
    var cells = m.pts.map(function (p, i) { return i; }).sort(function (a, b) { return m.dep[a] - m.dep[b]; });
    var C = bucket(pal);
    cells.forEach(function (i) {
      if (i === m.D) return;
      var p = m.pts[i], s = m.dep[i];
      var sb = q50(s);
      m.branches[i].forEach(function (b) { B.stroke(S.d(b), dark ? 'peri' : 'soft', 0.5 + 1.8 * sb, 0.2 + 0.55 * sb, 'b' + sb); });
      if (s > 0.5 && dark) C.dot(p[0], p[1], m.size[i] * 2.6, 'peri', 0.1);
      C.dot(p[0], p[1], m.size[i], s > 0.45 ? 'ink' : s > 0.2 ? 'read' : 'soft', 0.3 + 0.65 * Math.pow(s, 0.6));
    });
    return (backCache[k] = B.text() + C.text());
  }
  // Strokes and points of the same look gathered into one path each (a point is a round cap on a
  // zero-length stroke). Widths and radii to a tenth, opacities to a fiftieth: no visible change.
  function bucket(pal) {
    var g = {}, keys = [], plain = '';
    function put(key, role, w, op, d) { var b = g[key]; if (!b) { b = g[key] = { role: role, w: w, op: op, d: '' }; keys.push(key); } b.d += d; }
    // key (optional): the group, named from what is drawn; every member of a key has the same look
    return {
      stroke: function (d, role, w, op, key) {
        if (pal.dash[role]) { plain += '<path d="' + d + '" ' + S.stroke(pal, role, w, op) + '/>'; return; }
        w = Math.round(w * 10) / 10; op = Math.round(op * 50) / 50; if (op <= 0) return;
        put(key || 's' + role + w + '/' + op, role, w, op, d);
      },
      dot: function (x, y, r, role, op, key) {
        if (pal.dash[role]) { plain += S.dot(x, y, r, pal, role, op); return; }
        r = Math.round(r * 10) / 10; op = Math.round(op * 50) / 50; if (op <= 0 || r <= 0) return;
        put(key || 'd' + role + r + '/' + op, role, 2 * r / pal.weight, op, 'M' + S.n(x) + ' ' + S.n(y) + 'h0');
      },
      text: function () { var out = plain; keys.forEach(function (k) { var b = g[k]; out += '<path d="' + b.d + '" ' + S.stroke(pal, b.role, b.w, b.op) + '/>'; }); return out; }
    };
  }
  // a settled picture's lit threads and cells (the 'rest' part), batched the same way: used for stills
  // and for any full draw once nothing is moving (updateDeep then asks for one full draw before it goes on)
  function restCompact(list, pal) {
    var g = {}, keys = [], at = {};
    list.forEach(function (it) {
      var a = it.a, d, key, attrs;
      if (it.t === 'circle') {
        d = 'M' + a.cx + ' ' + a.cy + 'h0';
        attrs = 'fill="none" stroke="' + a.fill + '" stroke-width="' + U.ns(2 * Number(a.r)) + '" stroke-linecap="round" stroke-opacity="' + a['fill-opacity'] + '"';
      } else {
        d = a.d; attrs = '';
        for (var n in a) if (n !== 'd') attrs += n + '="' + a[n] + '" ';
      }
      key = it.g || attrs; if (g[key] == null) { g[key] = ''; keys.push(key); at[key] = attrs; } g[key] += d;
    });
    return keys.map(function (k) { return '<path data-c="1" d="' + g[k] + '" ' + at[k] + '/>'; }).join('');
  }
  // a state made for another layout of the network (the screen changed size) keeps only what still fits
  function fit(m, s) {
    var n = m.pts.length, ok = s.waves.every(function (w) { return w.src < n; }) && s.sel < n;
    return ok ? s : { t: s.t, waves: s.waves.filter(function (w) { return w.src < n; }), sel: s.sel < n ? s.sel : m.D };
  }
  function inHole(m, x, y, pad) {
    for (var i = 0; i < m.holes.length; i++) { var h = m.holes[i]; if (x >= h[0] - pad && x <= h[2] + pad && y >= h[1] - pad && y <= h[3] + pad) return true; }
    return false;
  }
  // the ring that opens where a pulse leaves, drawn only where it does not pass behind the words
  function ringD(m, o, R) {
    var N = 120, vis = [], i, st = -1, d = '';
    for (i = 0; i < N; i++) { var a = i / N * 6.2832, x = o[0] + Math.cos(a) * R, y = o[1] + Math.sin(a) * R; vis.push([x, y, !inHole(m, x, y, 8)]); if (st < 0 && !vis[i][2]) st = i; }
    if (st < 0) return 'M' + S.n(o[0] + R) + ' ' + S.n(o[1]) + 'A' + S.n(R) + ' ' + S.n(R) + ' 0 1 1 ' + S.n(o[0] - R) + ' ' + S.n(o[1]) + 'A' + S.n(R) + ' ' + S.n(R) + ' 0 1 1 ' + S.n(o[0] + R) + ' ' + S.n(o[1]);
    for (var k = 1, pen = false; k <= N; k++) { var v = vis[(st + k) % N]; if (v[2]) { d += (pen ? 'L' : 'M') + S.n(v[0]) + ' ' + S.n(v[1]); pen = true; } else pen = false; }
    return d;
  }
  function edgeD(m, k) { var e = m.edges[k]; return m.qd[k] || (m.qd[k] = U.qd(m.pts[e[0]], m.ctl[k], m.pts[e[1]])); }
  function branchD(m, i) { if (m.bd[i] == null) { var d = ''; m.branches[i].forEach(function (b) { d += S.d(b); }); m.bd[i] = d; } return m.bd[i]; }
  function q50(x) { return Math.round(x * 50) / 50; }
  // Everything the moving layer shows for a state, as elements with keys:
  //   rest: the threads a pulse has crossed and the cells it has reached (they stay; written once each)
  //   glow: the light a pulse leaves on a thread for a moment;  run: the pulses in flight
  //   lit: cells that just fired;  ring: where a pulse leaves a cell
  // Anything fainter than 4% is left out.
  function deepScene(m, s, pal) {
    s = fit(m, s);
    var I = U.item, sa = U.sa, fa = U.fa, dark = pal.glow;
    var out = { rest: [], glow: [], run: [], lit: [], ring: [] }, lit = {}, fired = {}, used = {}, usedList = [], firedList = [];
    s.waves.forEach(function (w, wi) {
      var e = s.t - w.t0;
      if (e < 0) return;
      var W = waveOf(m, w.src), tr = W.tr;
      for (var ti = 0; ti < tr.length; ti++) {
        var t = tr[ti];
        if (e < t.t0) continue;
        var sd = m.edep[t.e];
        if (e < t.t1) {
          var a = m.pts[t.a], b = m.pts[t.b], c = m.ctl[t.e], u = (e - t.t0) / (t.t1 - t.t0), id = wi + '_' + ti;
          var hd = S.d(U.qpts(a, c, b, Math.max(0, u - 0.4), u, 5)), hw = 1.1 + 4.5 * sd * sd;
          out.run.push(I('a' + id, 'path', Object.assign({ d: S.d(U.qpts(a, c, b, 0, u, 6)) }, sa(pal, 'mint', 0.5 + 1.6 * sd, 0.35 + 0.3 * sd))));
          if (dark) out.run.push(I('g' + id, 'path', Object.assign({ d: hd }, sa(pal, 'mint', hw * 2.6 + 1.6, 0.16))));
          out.run.push(I('h' + id, 'path', Object.assign({ d: hd }, sa(pal, 'mint', hw, 1))));
        } else {
          if (!used[t.e]) { used[t.e] = 1; usedList.push(t.e); }
          var g = q50(Math.exp(-(e - t.t1) / 0.7) * 0.7);
          if (g > 0.04) out.glow.push(I(wi + '_' + t.e, 'path', Object.assign({ d: edgeD(m, t.e) }, sa(pal, 'mint', 0.6 + 1.6 * sd, g))));
        }
      }
      W.fire.forEach(function (f, i) {
        if (f === Infinity || e < f) return;
        if (!fired[i]) { fired[i] = 1; firedList.push(i); }
        var v = Math.exp(-(e - f) / 0.38); if (v > (lit[i] || 0)) lit[i] = v;
      });
      if (e < 1.8 && !m.noRing) {
        var o = m.pts[w.src], sd0 = m.dep[w.src], r0 = w.src === m.D ? m.fs * 0.05 : m.size[w.src] + 3, ue = U.ease(e / 1.8);
        out.ring.push(I('a' + wi, 'path', Object.assign({ d: ringD(m, o, r0 + (m.narrow ? 120 : 260) * sd0 * ue) }, sa(pal, 'mint', 1 + 1.2 * sd0, q50(0.85 * (1 - e / 1.8))))));
        out.ring.push(I('b' + wi, 'path', Object.assign({ d: ringD(m, o, r0 + (m.narrow ? 60 : 120) * sd0 * ue) }, sa(pal, 'mint', 0.8, q50(0.5 * (1 - e / 1.8))))));
      }
    });
    // where a pulse has passed, the threads and the cells stay faintly lit
    // (depths to a fiftieth; .g names the group a still draws them in, the same in every theme)
    usedList.forEach(function (k) { var sd = m.edq[k], it = I('e' + k, 'path', Object.assign({ d: edgeD(m, k) }, sa(pal, 'peri', 0.5 + 1.1 * sd, (dark ? 0.2 : 0.3) + 0.25 * sd))); it.g = 'e' + sd; out.rest.push(it); });
    firedList.forEach(function (i) {
      if (i === m.D) return;
      var p = m.pts[i], r = U.ns(m.size[i] * 1.05), dq = m.dq[i];
      var it = I('c' + i, 'circle', Object.assign({ cx: U.ns(p[0]), cy: U.ns(p[1]), r: r }, fa(pal, 'peri', 0.5 + 0.4 * dq))); it.g = 'c' + r + '/' + dq; out.rest.push(it);
    });
    firedList.forEach(function (i) {
      var f = q50(lit[i] || 0);
      if (i === m.D || f <= 0.03) return;
      var p = m.pts[i], sd = m.dep[i], r = m.size[i], hr = r * 2.2 + 14 * sd + 4;
      if (dark) { if (0.26 * f > 0.04) out.lit.push(I('h' + i, 'circle', Object.assign({ cx: U.ns(p[0]), cy: U.ns(p[1]), r: U.ns(hr) }, fa(pal, 'mint', 0.26 * f)))); }
      else if (0.64 * f > 0.04) out.lit.push(I('h' + i, 'circle', Object.assign({ cx: U.ns(p[0]), cy: U.ns(p[1]), r: U.ns(hr * 0.72) }, sa(pal, 'mint', 0.8, Math.min(0.6, 0.64 * f)))));
      if (m.branches[i].length && 0.9 * f > 0.04) out.lit.push(I('b' + i, 'path', Object.assign({ d: branchD(m, i) }, sa(pal, 'mint', 0.7 + 1.4 * sd, 0.9 * f))));
      out.lit.push(I('d' + i, 'circle', Object.assign({ cx: U.ns(p[0]), cy: U.ns(p[1]), r: U.ns(r * (1.15 + 0.5 * f)) }, fa(pal, f > 0.3 ? 'ink' : 'mint', 0.75 + 0.25 * f))));
    });
    return out;
  }
  var PARTS = ['rest', 'glow', 'run', 'lit', 'ring'];
  function drawDeep(m, s, pal) {
    var sc = deepScene(m, s, pal), front = {};
    var still = m.compact && sc.rest.length && !sc.glow.length && !sc.run.length && !sc.lit.length && !sc.ring.length && !pal.dash.peri;
    PARTS.forEach(function (k) { front[k] = still && k === 'rest' ? restCompact(sc.rest, pal) : U.itemsText(sc[k]); });
    m.__compact = !!still;
    m.__gen = (m.__gen || 0) + 1;
    // the print copy stands alone, so it carries the title the page sets in type
    var labels = '';
    if (pal.name === 'print' && m.printTitle) m.printTitle.forEach(function (l) { labels += S.text(l[0], l[1], l[2], pal, 'ink', { size: Math.round(m.fs), weight: 500, anchor: 'start' }).replace('<text ', '<text letter-spacing="' + S.n(-0.025 * m.fs) + '" '); });
    if (pal.name === 'print' && m.printLead) m.printLead.lines.forEach(function (l) { labels += S.text(l[0], l[1], l[2], pal, 'read', { size: m.printLead.size, weight: 400, anchor: 'start' }); });
    return { back: deepBack(m, pal), front: front, labels: labels };
  }
  // every later frame: the same elements, brought up to date in place
  function syncDeep(m, s, pal, groups, holder) {
    var kd = U.keyed(m, holder, groups), sc = deepScene(m, s, pal);
    PARTS.forEach(function (k) { if (kd[k]) U.syncPart(kd[k], sc[k], k === 'rest'); });
  }
  function updateDeep(m, s, ctx) {
    var g = ctx.parts;
    if (!g || !g.rest || !g.ring || m.__compact) return false;
    syncDeep(m, s, ctx.pal, g, ctx.front);
  }
  function describeDeep(m, s) {
    s = fit(m, s);
    var t = 'A deep field of model neurons fills the screen above and beside the title, near cells large with short branches, far cells small points, all joined by thin connections. ';
    var w = s.waves[s.waves.length - 1];
    if (!w) return t + 'The field is at rest.';
    var W = waveOf(m, w.src), e = s.t - w.t0, n = 0;
    W.fire.forEach(function (f) { if (f < Infinity && e >= f) n++; });
    var from = w.src === m.D ? 'the full stop at the end of the title' : 'one of the cells';
    if (e < 0) return t + 'A pulse leaves ' + from + '.';
    if (e > W.max + 0.6) return t + (s.waves.length > 1 ? 'Pulses left the full stop at the end of the title and two other cells and spread from cell to cell through the field; the connections they crossed stay faintly lit.'
      : 'A pulse left ' + from + ' and spread from cell to cell into the depth of the field; the connections it crossed stay faintly lit.');
    var share = e / (W.max || 1);
    return t + 'A pulse that left ' + from + ' is spreading from cell to cell into the depth of the field and has reached ' + (share < 0.3 ? 'the cells nearby' : share < 0.7 ? 'about half way across the field' : 'most of the field') + '.';
  }
  function fire(m, s, i) {
    s = fit(m, s);
    var t0 = P.reducedMotion() ? s.t - waveOf(m, i).max * 0.55 : s.t + 0.02;
    return { t: s.t, waves: s.waves.concat([{ src: i, t0: t0 }]).slice(-3), sel: i };
  }
  function fireSel(m, s) { var ns = fire(m, s, s.sel); H.go(); return ns; }
  // the opening's own story: a pulse from the full stop, then from a cell far to the right, then from one
  // high in the middle; each spreads through the field and leaves the connections it crossed faintly lit
  function sendFrom(m, s, i) { s = fit(m, s); return { t: s.t, waves: s.waves.concat([{ src: i, t0: s.t }]).slice(-3), sel: s.sel }; }
  function picks(m) {
    if (m.__picks) return m.__picks;
    var W = m.view.w, Hh = m.view.h, n = m.pts.length;
    function best(tx, ty, not) {
      var c = [];
      m.pts.forEach(function (p, i) { if (i !== m.D && i !== not && m.dep[i] > 0.28) c.push([Math.hypot(p[0] - tx, p[1] - ty), i]); });
      c.sort(function (a, b) { return a[0] - b[0]; });
      // the nearest cell from which a pulse reaches most of the field
      for (var k = 0; k < c.length && k < 14; k++) if (waveOf(m, c[k][1]).reached > n * 0.6) return c[k][1];
      return c.length ? c[0][1] : m.D;
    }
    var a = m.narrow ? best(W * 0.82, Hh * 0.14) : best(W * 0.88, Hh * 0.24);
    return (m.__picks = [a, m.narrow ? best(W * 0.22, Hh * 0.3, a) : best(W * 0.4, Hh * 0.17, a)]);
  }
  var FIELD_SEQ = [
    { dur: 500 },
    { dur: 4400, do: function (m, s) { return sendFrom(m, s, m.D); } },
    { dur: 3700, do: function (m, s) { return sendFrom(m, s, picks(m)[0]); } },
    { dur: 5400, do: function (m, s) { return sendFrom(m, s, picks(m)[1]); } }
  ];
  // the picture the story ends on: the three pulses have spread and settled
  function fieldEnd(m) {
    var t = 0, waves = [];
    FIELD_SEQ.forEach(function (st, k) { if (k === 1) waves.push({ src: m.D, t0: t }); if (k === 2) waves.push({ src: picks(m)[0], t0: t }); if (k === 3) waves.push({ src: picks(m)[1], t0: t }); t += st.dur / 1000; });
    return { t: t, waves: waves, sel: m.D };
  }
  function move(dir) { return function (m, s) { s = fit(m, s); return { t: s.t, waves: s.waves, sel: U.towards(m.pts, s.sel, dir, Math.max(m.view.w, m.view.h) * 0.12) }; }; }
  // the close draws the same field again, around its own words
  U.bucket = bucket;
  U.deep = { make: makeDeep, draw: drawDeep, back: deepBack, sync: syncDeep, parts: PARTS, wave: waveOf, measure: measure };
  function fieldSettled(m, s) { return fit(m, s).waves.every(function (w) { return s.t - w.t0 > waveOf(m, w.src).max + 1.6; }); }
  H.settled = fieldSettled; H.go = U.driver(H);
  var picked = -1;
  H.fig = P.figure({
    id: 'field', name: 'a-pulse-through-a-deep-field', title: 'A pulse through a deep field of model neurons',
    caption: 'Pulses leave the full stop, then two other cells, and run from cell to cell through a deep field of model neurons.',
    // no model is built while the page loads: the kit asks for one when the figure mounts, and for the
    // stills it asks for a 1600 by 900 box, which is the layout measured for them (EXPORT)
    modelFor: function (box) {
      if (box.width === 1600 && box.height === 900) { var m = makeDeep(EXPORT); m.printTitle = EXPORT.print; m.printLead = EXPORT.printLead; m.compact = true; return m; }
      var lm = makeDeep(measure(box) || EXPORT); lm.compact = true; return lm;
    },
    initialState: function (m) { return { t: 0, waves: [], sel: m.D }; },
    stillState: fieldEnd,
    tick: U.watch(H, function (m, s, dt) { return { t: s.t + dt, waves: s.waves, sel: s.sel }; }),
    settled: fieldSettled,
    sequence: FIELD_SEQ,
    draw: function (m, s, pal) { H.m = m; return drawDeep(m, s, pal); }, update: updateDeep, frontGlow: false, describe: describeDeep,
    controls: ['play'],
    handle: function (m, s) { return m.pts[fit(m, s).sel]; },
    keysLabel: 'Arrow keys choose a cell; Enter fires it.',
    keys: { ArrowUp: move([0, -1]), ArrowDown: move([0, 1]), ArrowLeft: move([-1, 0]), ArrowRight: move([1, 0]), Enter: fireSel, ' ': fireSel },
    drag: {
      // a press anywhere on the field fires the cell nearest to it
      pick: function (m, s, p) { picked = U.nearest(m.pts, p, null); return picked >= 0; },
      move: function (m, s) { return s; },
      end: function (m, s) { var i = picked; picked = -1; if (i < 0) return s; var ns = fire(m, s, i); H.go(); return ns; }
    }
  });
  // The opening is the reader's as soon as they press anywhere in it (the words lie over the field, so a
  // press there counts too), not only on the figure: its sequence stops where it is. A touch that turns
  // into a scroll fires nothing (capture: this runs before the figure's own pointer handlers).
  var openSec = document.querySelector('.w-open');
  if (openSec) {
    openSec.addEventListener('pointerdown', function (e) {
      if (e.button !== 0 || (e.target.closest && e.target.closest('a, button, .k-fig-ctl'))) return;
      var h = H.fig; if (h && (h.sequence === 'playing' || h.sequence === 'paused')) h.set(h.state);
    }, true);
    openSec.addEventListener('pointercancel', function () { picked = -1; }, true);
  }
})(window.Psyche);

/* ===== Row 2: every layer, every time; or one pulse where it is needed ====================== */
(function (P) {
  'use strict';
  var S = P.svg, U = P.wwb, H = { fig: null };
  var memo = {};
  function makePulse(narrow) {
    var key = narrow ? 'pulse-n' : 'pulse-w';
    if (memo[key]) return memo[key];
    var o = narrow
      ? { view: { w: 700, h: 1300 }, A: { x: 50, y: 30, w: 630, h: 500 }, B: { x: 50, y: 700, w: 630, h: 500 }, my: 60 }
      : { view: { w: 1600, h: 690 }, A: { x: 60, y: 44, w: 640, h: 520 }, B: { x: 900, y: 44, w: 640, h: 520 }, my: 84 };
    var L = 6, n = 8, A = o.A, B = o.B, nodes = [], bands = [], k, j, j2;
    for (k = 0; k < L; k++) { nodes.push([]); for (j = 0; j < n; j++) nodes[k].push([A.x + k * A.w / (L - 1), A.y + (j + 0.5) * A.h / n]); }
    for (k = 0; k < L - 1; k++) { bands.push([]); for (j = 0; j < n; j++) for (j2 = 0; j2 < n; j2++) bands[k].push([nodes[k][j], nodes[k + 1][j2]]); }
    var rng = P.mulberry(narrow ? 41 : 31), target = 60, dmin = Math.sqrt(B.w * B.h / (target * 1.75));
    var pts = U.scatter(rng, target, dmin, function () { return true; }, [B.x + 10, B.y + 6, B.x + B.w - 6, B.y + B.h - 6]);
    var edges = U.knn(pts, 3, dmin * 2.5), lens = edges.map(function (e) { return U.dist(pts[e[0]], pts[e[1]]); }), adj = U.adjOf(pts.length, edges);
    var ctl = edges.map(function (e, k) { return U.bend(pts[e[0]], pts[e[1]], k + 11, 0.16); }), eid = {};
    edges.forEach(function (e, k) { eid[e[0] + '-' + e[1]] = eid[e[1] + '-' + e[0]] = k; });
    var paths = [];
    for (j = 0; j < n; j++) {
      var y = B.y + (j + 0.5) * B.h / n, inp = U.nearest(pts, [B.x, y]), dj = U.dijkstra(pts.length, adj, lens, inp), best = -1, bd = Infinity;
      pts.forEach(function (p, i) { if (dj.dist[i] === Infinity) return; var d = Math.hypot(p[0] - (B.x + B.w), (p[1] - y) * 1.6); if (d < bd) { bd = d; best = i; } });
      var cells = [best]; while (cells[0] !== inp) cells.unshift(dj.prev[cells[0]]);
      var hops = [], total = 0, q;
      for (q = 1; q < cells.length; q++) { var len = U.dist(pts[cells[q - 1]], pts[cells[q]]); hops.push({ a: cells[q - 1], b: cells[q], len: len, e: eid[cells[q - 1] + '-' + cells[q]] }); total += len; }
      var t = 0.2;
      hops.forEach(function (h) { h.t0 = t; t += h.len / total * 2.1; h.t1 = t; });
      paths.push({ cells: cells, hops: hops, inp: inp });
    }
    return (memo[key] = { key: key, view: o.view, A: A, B: B, L: L, n: n, nodes: nodes, bands: bands, total: (L - 1) * n * n,
      pts: pts, edges: edges, ctl: ctl, paths: paths, my: o.my, narrow: narrow, t0: 0.2, band: 0.42, END: 2.9 });
  }
  var backCache = {};
  function back(m, pal) {
    var k = m.key + pal.name;
    if (backCache[k]) return backCache[k];
    var out = '';
    // the layered network: every connection drawn lit, always
    m.bands.forEach(function (b) { b.forEach(function (q) { out += S.line(q[0][0], q[0][1], q[1][0], q[1][1], pal, 'soft', 0.7, pal.glow ? 0.2 : 0.24); }); });
    m.nodes.forEach(function (col) { col.forEach(function (p) { out += S.dot(p[0], p[1], 3, pal, 'soft', 0.9); }); });
    // the spiking network: dark and silent
    m.edges.forEach(function (e, k) { out += U.qline(m.pts[e[0]], m.ctl[k], m.pts[e[1]], pal, 'faint', 0.8, 0.6); });
    m.pts.forEach(function (p) { out += S.dot(p[0], p[1], 2.3, pal, 'quiet', 0.75); });
    return (backCache[k] = out);
  }
  // the moving layer in parts, each written only when its own text changed: the finished layers of
  // connections are one path each and change once; only the layer being crossed is redrawn each frame
  function bandD(m, k) { m.__bd = m.__bd || []; return m.__bd[k] || (m.__bd[k] = U.segsD(m.bands[k])); }
  function drawPulse(m, s, pal) {
    var e = s.e, A = m.A, B = m.B, row = s.row, k;
    var F = { inp: '', done: '', wave: '', nodes: '', right: '', meter: '' };
    var li = m.nodes[0][row], path = m.paths[row], ri = m.pts[path.inp], on = e >= 0;
    // where the signal comes in, on both sides
    if (on) F.inp = S.glowPath([[A.x - 46, li[1]], [li[0] - 9, li[1]]], pal, 'mint', 1.4, { opacity: 0.95 }) + S.glowPath([[B.x - 46, ri[1]], [ri[0] - 8, ri[1]]], pal, 'mint', 1.4, { opacity: 0.95 });
    else F.inp = S.line(A.x - 46, li[1], li[0] - 9, li[1], pal, 'soft', 1.4, 0.6) + S.line(B.x - 46, ri[1], ri[0] - 8, ri[1], pal, 'soft', 1.4, 0.6);
    // left: values pass through every connection of every layer
    var litA = 0;
    if (on) for (k = 0; k < m.L - 1; k++) {
      var tk = m.t0 + k * m.band;
      if (e < tk) break;
      var u = (e - tk) / m.band;
      if (u < 1) {
        litA += m.n * m.n * u;
        var eu = U.ease(u), segs = [], heads = [];
        m.bands[k].forEach(function (q) { var hd = U.lerp(q[0], q[1], eu); segs.push([q[0], hd]); heads.push(hd); });
        F.wave = '<path d="' + U.segsD(segs) + '" ' + S.stroke(pal, 'read', 0.8, 0.55) + '/>' + U.dots(heads, 1.8, pal, 'ink', 0.9);
      } else {
        litA += m.n * m.n;
        F.done += '<path d="' + bandD(m, k) + '" ' + S.stroke(pal, 'read', 0.75, 0.36) + '/>';
      }
    }
    if (on) for (k = 0; k < m.L; k++) {
      var f = e - (m.t0 + k * m.band);
      if (f < 0) continue;
      var g = Math.round(Math.exp(-f / 0.4) * 50) / 50;
      F.nodes += (g > 0.05 ? U.halos(m.nodes[k], 11, pal, 'mint', 0.2 * g) : '') + U.dots(m.nodes[k], 3 + 1.6 * g, pal, 'ink', 0.85);
    }
    // right: one pulse, only where it is needed
    var litB = 0;
    if (on) {
      var a0 = ri, fi = e - path.hops[0].t0;
      if (fi >= 0) F.right += U.halo(a0[0], a0[1], 12, pal, 'mint', 0.22 * Math.exp(-fi / 0.4)) + S.dot(a0[0], a0[1], 3.4, pal, 'mint');
      path.hops.forEach(function (h) {
        if (e < h.t0) return;
        var a = m.pts[h.a], b = m.pts[h.b], c = m.ctl[h.e], uu = U.clamp((e - h.t0) / (h.t1 - h.t0), 0, 1), hd = U.qpt(a, c, b, uu);
        if (uu > 0) F.right += S.glowPath(U.qpts(a, c, b, 0, uu, 10), pal, 'mint', 1.9, { opacity: 0.95 });
        litB += uu;
        if (uu < 1) F.right += U.halo(hd[0], hd[1], 13, pal, 'mint', 0.22) + S.dot(hd[0], hd[1], 3.4, pal, 'ink');
        else { var fb = Math.exp(-(e - h.t1) / 0.4); F.right += (fb > 0.05 ? U.halo(b[0], b[1], 12, pal, 'mint', 0.22 * fb) : '') + S.dot(b[0], b[1], 3 + 1.4 * fb, pal, 'mint'); }
      });
    }
    // how much of each lit up: a line under each side
    function meter(x, y, w, share) { return S.line(x, y, x + w, y, pal, 'faint', 1.2, 0.9) + (share > 0.001 ? S.line(x, y, x + w * share, y, pal, 'ink', 2.6) : ''); }
    F.meter = meter(A.x, A.y + A.h + m.my, A.w, litA / m.total) + meter(B.x, B.y + B.h + m.my, B.w, litB / m.edges.length);
    return { back: back(m, pal), front: F };
  }
  function describePulse(m, s) {
    var t = (m.narrow ? 'Two networks, one above the other. The upper one' : 'Two networks side by side. The left one') +
      ' is built in layers, with every cell joined to every cell of the next layer, and all of its connections are drawn lit. ' +
      (m.narrow ? 'The lower one' : 'The right one') + ' is a loose web of cells that stays dark. ';
    if (s.e < 0) return t + 'Both are at rest, and the line under each is empty.';
    var done = s.e >= m.END - 0.4;
    return t + (done ? 'A signal entered both. In the layered network it passed through every connection, and the line under it is full. In the web, one pulse travelled a short path of cells to the far side, and the line under it barely grew.'
      : 'A signal is passing through both: in the layered network through every connection at once, in the web as one pulse moving from cell to cell.');
  }
  function send(m, row) { var s = { row: row, e: P.reducedMotion() ? m.END : 0 }; H.go(); return s; }
  function pulseTick(m, s, dt) { return { row: s.row, e: Math.min(m.END, s.e + dt) }; }
  H.settled = function (m, s) { return s.e >= m.END; }; H.go = U.driver(H);
  function toEnd(m) { return { e: m.END }; }
  var pickedRow = -1;
  function rowAt(m, p) {
    var A = m.A, B = m.B, inB = m.narrow ? p[1] > (A.y + A.h + B.y) / 2 : p[0] > (A.x + A.w + B.x) / 2, R = inB ? B : A;
    return U.clamp(Math.floor((p[1] - R.y) / R.h * m.n), 0, m.n - 1);
  }
  H.fig = P.figure({
    id: 'pulse', name: 'layers-and-pulses', title: 'Every layer, every time; or one pulse where it is needed',
    caption: 'A signal enters both networks twice: each time it lights every connection of the layered one, and one short path through the other.',
    modelFor: function (box) { return makePulse(box.width < 620); },
    initialState: function () { return { row: 3, e: -0.5 }; },
    // the second signal, along another row, is the picture the story ends on
    stillState: function (m) { return { row: 6, e: m.END }; },
    tick: U.watch(H, pulseTick),
    settled: H.settled,
    // the signal enters both, slowed so the reader can follow it; then again along another row:
    // every layer, every time, against one short path
    sequence: [
      { dur: 900, tick: false },
      { dur: 5600, tick: false, to: toEnd, ease: 'linear' },
      { dur: 1700, tick: false },
      { dur: 0, do: function () { return { row: 6, e: -0.3 }; } },
      { dur: 4800, tick: false, to: toEnd, ease: 'linear' },
      { dur: 700, tick: false }
    ],
    draw: function (m, s, pal) { H.m = m; return drawPulse(m, s, pal); }, frontGlow: false, describe: describePulse,
    controls: [],
    handle: function (m, s) { return m.nodes[0][s.row]; },
    keysLabel: 'Arrow keys send a signal along another row; Enter sends it again.',
    keys: {
      ArrowUp: function (m, s) { return send(m, Math.max(0, s.row - 1)); },
      ArrowDown: function (m, s) { return send(m, Math.min(m.n - 1, s.row + 1)); },
      ArrowLeft: function (m, s) { return send(m, Math.max(0, s.row - 1)); },
      ArrowRight: function (m, s) { return send(m, Math.min(m.n - 1, s.row + 1)); },
      Enter: function (m, s) { return send(m, s.row); },
      ' ': function (m, s) { return send(m, s.row); }
    },
    drag: {
      pick: function (m, s, p) { pickedRow = rowAt(m, p); return true; },
      move: function (m, s) { return s; },
      end: function (m, s) { var r = pickedRow; pickedRow = -1; return r < 0 ? s : send(m, r); }
    }
  });
})(window.Psyche);

/* ===== Row 3: a connection grows where activity meets ======================================= */
(function (P) {
  'use strict';
  var S = P.svg, U = P.wwb, H = { fig: null };
  var WIN = 0.6, REF = 0.35, memo = {};
  function makeHebb(narrow) {
    var key = narrow ? 'hebb-n' : 'hebb-w';
    if (memo[key]) return memo[key];
    var view = narrow ? { w: 600, h: 760 } : { w: 1600, h: 600 }, cx = view.w / 2, cy = view.h / 2;
    var rx = narrow ? 262 : 750, ry = narrow ? 336 : 250, n = narrow ? 10 : 22, dmin = narrow ? 158 : 142;
    var rng = P.mulberry(narrow ? 8 : 3);
    var pts = U.scatter(rng, n, dmin, function (x, y) { var u = (x - cx) / rx, v = (y - cy) / ry; return u * u + v * v <= 1; }, [cx - rx, cy - ry, cx + rx, cy + ry]);
    var edges = [], i, j;
    for (i = 0; i < pts.length; i++) for (j = i + 1; j < pts.length; j++) if (U.dist(pts[i], pts[j]) < dmin * 1.75) edges.push([i, j]);
    var adj = U.adjOf(pts.length, edges);
    // two groups of neighbours for the opening run: one toward each side
    function group(at, size, avoid) {
      var first = U.nearest(pts, at, null, function (k) { return avoid.indexOf(k) >= 0; }), g = [first];
      while (g.length < size) {
        var best = -1, bd = Infinity;
        g.forEach(function (c) { adj[c].forEach(function (a) { var k = a[0]; if (g.indexOf(k) >= 0 || avoid.indexOf(k) >= 0) return; var d = U.dist(pts[k], pts[first]); if (d < bd) { bd = d; best = k; } }); });
        if (best < 0) break;
        g.push(best);
      }
      return g;
    }
    var GA = group(narrow ? [cx, cy - ry * 0.45] : [cx - rx * 0.42, cy], 4, []), GB = group(narrow ? [cx, cy + ry * 0.5] : [cx + rx * 0.45, cy], 3, GA);
    // the figure's story: two neighbours fire together four times, and their connection grows step by step;
    // then two others on the far side do the same; then the first cell fires alone, and its strong
    // connection carries the firing on to its partner
    var script = [], t = 1.0;
    function together(cells) { cells.forEach(function (c, k) { script.push({ at: t + k * 0.1, i: c }); }); t += 1.1; }
    together([GA[0], GA[1]]); together([GA[0], GA[1]]); together([GA[1], GA[0]]); together([GA[0], GA[1]]);
    t += 0.9;
    together([GB[0], GB[1]]); together([GB[1], GB[0]]); together([GB[0], GB[1]]); together([GB[0], GB[1]]);
    t += 0.6;
    script.push({ at: t, i: GA[0] });
    // each cell drawn as a small neuron: a body and a few short branches, pointing away from its connections
    var ctl = edges.map(function (e, k) { return U.bend(pts[e[0]], pts[e[1]], k + 5, 0.14); });
    var branches = pts.map(function (p, i) {
      var out = [], nb = rng() * 6.28, cnt = 5 + Math.floor(rng() * 3);
      for (var b = 0; b < cnt; b++) {
        var a = nb + b * 6.2832 / cnt + (rng() - 0.5) * 0.7, len = (narrow ? 30 : 30) + rng() * 26, bendA = (rng() - 0.5) * 0.9;
        var p1 = [p[0] + Math.cos(a) * 10, p[1] + Math.sin(a) * 10], p2 = [p[0] + Math.cos(a + bendA * 0.5) * len * 0.6, p[1] + Math.sin(a + bendA * 0.5) * len * 0.6], p3 = [p[0] + Math.cos(a + bendA) * len, p[1] + Math.sin(a + bendA) * len];
        out.push([p1, p2, p3]);
        if (rng() < 0.5) { var a2 = a + bendA + (rng() < 0.5 ? 0.6 : -0.6); out.push([p2, [p2[0] + Math.cos(a2) * len * 0.45, p2[1] + Math.sin(a2) * len * 0.45]]); }
      }
      return out;
    });
    return (memo[key] = { key: key, view: view, pts: pts, edges: edges, ctl: ctl, branches: branches, adj: adj, script: script, narrow: narrow, dmin: dmin, GA: GA, GB: GB });
  }
  function copy(s) { return { t: s.t, w: s.w.slice(), last: s.last.slice(), q: s.q.slice(), gl: s.gl.slice(), si: s.si, act: s.act, sel: s.sel }; }
  function fireCell(m, st, i, t, gen) {
    gen = gen || 0;
    if (t - st.last[i] < REF) return;
    st.last[i] = t; st.act = t;
    m.adj[i].forEach(function (a) {
      var j = a[0], e = a[1], dt = t - st.last[j];
      // fired together: the connection between them grows
      if (dt >= 0 && dt <= WIN) { st.w[e] = Math.min(1, st.w[e] + 0.26 * (1 - st.w[e])); st.gl.push({ e: e, at: t }); }
      // a strong connection carries the firing on
      // (only a step or two: a firing never keeps itself going)
      if (gen < 2 && st.w[e] > 0.5 && t - st.last[j] > REF && !st.q.some(function (x) { return x.i === j; })) st.q.push({ i: j, at: t + 0.16, g: gen + 1 });
    });
  }
  function advance(m, s, dt) {
    var st = copy(s), t1 = s.t + dt;
    for (var guard = 0; guard < 400; guard++) {
      var nx = Infinity, kind = null, qi = -1;
      if (st.si < m.script.length) { nx = m.script[st.si].at; kind = 's'; }
      st.q.forEach(function (x, k) { if (x.at < nx) { nx = x.at; kind = 'q'; qi = k; } });
      if (nx > t1) break;
      if (kind === 's') { fireCell(m, st, m.script[st.si].i, nx); st.si++; }
      else { var x = st.q.splice(qi, 1)[0]; fireCell(m, st, x.i, nx, x.g); }
    }
    st.t = t1;
    st.gl = st.gl.filter(function (g) { return t1 - g.at < 0.7; });
    return st;
  }
  function initial(m) {
    var w = m.edges.map(function () { return 0.05; }), last = m.pts.map(function () { return -99; });
    return { t: 0, w: w, last: last, q: [], gl: [], si: 0, act: 0, sel: m.GA[0] };
  }
  function settled(m, s) { return s.si >= m.script.length && !s.q.length && s.t - s.act > 1.3; }
  var stillMemo = {};
  function still(m) {
    if (stillMemo[m.key]) return stillMemo[m.key];
    var s = initial(m), g = 0;
    while (!settled(m, s) && g++ < 2000) s = advance(m, s, 1 / 30);
    s.last = s.last.map(function () { return -99; }); s.gl = [];
    return (stillMemo[m.key] = s);
  }
  // the moving layer in three parts: the connections change only when a pair fires together, so on most
  // frames only the flashes and the cells are written
  var hebbBack = {};
  function drawHebb(m, s, pal) {
    var back = '', front = '', flash = '', cells = '', t = s.t, bk = m.key + pal.name;
    if (hebbBack[bk]) back = hebbBack[bk];
    else { m.branches.forEach(function (bs) { bs.forEach(function (b) { back += S.path(b, pal, 'soft', 1.2, { opacity: 0.5 }); }); }); hebbBack[bk] = back; }
    m.edges.forEach(function (e, k) {
      var a = m.pts[e[0]], b = m.pts[e[1]], w = s.w[k], c = m.ctl[k];
      // a connection runs from just outside one cell to just outside the other: a hairline at first,
      // then each time it grows a little brighter and wider, a glowing line around a thin bright core
      var seg = U.qpts(a, c, b, 0.09, 0.91, 16);
      if (w > 0.08) front += S.path(seg, pal, 'peri', 2 + 9 * w, { opacity: (pal.glow ? 0.1 : 0.08) + 0.14 * w });
      front += S.path(seg, pal, w > 0.08 ? 'peri' : 'soft', 0.7 + 2.1 * w, { opacity: w > 0.08 ? 0.45 + 0.55 * w : 0.42 });
      if (w > 0.4) front += S.path(seg, pal, 'ink', 0.6 + 0.8 * w, { opacity: 0.35 + 0.5 * w });
    });
    s.gl.forEach(function (g) {
      var e = m.edges[g.e], age = (t - g.at) / 0.7;
      if (age < 0 || age > 1) return;
      flash += S.path(U.qpts(m.pts[e[0]], m.ctl[g.e], m.pts[e[1]], 0.07, 0.93, 14), pal, 'ink', 1 + 2.4 * s.w[g.e], { opacity: 0.8 * (1 - age) });
    });
    m.pts.forEach(function (p, i) {
      var since = t - s.last[i], f = since >= 0 && s.last[i] > -50 ? Math.exp(-since / 0.28) : 0;
      if (f > 0.02) {
        cells += U.halo(p[0], p[1], 44, pal, 'mint', 0.3 * f) + S.circle(p[0], p[1], 18 + 46 * (1 - f), pal, 'mint', 1.6, 0.85 * f);
        m.branches[i].forEach(function (b) { cells += S.path(b, pal, 'mint', 1.8, { opacity: 0.95 * f }); });
      }
      cells += S.dot(p[0], p[1], 9 + 4 * f, pal, f > 0.25 ? 'ink' : 'read', 0.9 + 0.1 * f);
    });
    return { back: back, front: { net: front, flash: flash, cells: cells } };
  }
  function describeHebb(m, s) {
    // a connection above 0.08 is drawn brighter than a hairline (see drawHebb)
    var strong = s.w.filter(function (w) { return w > 0.5; }).length, mid = s.w.filter(function (w) { return w > 0.08 && w <= 0.5; }).length;
    var t = 'A small network of cells, each pair of neighbours joined by a connection. ';
    if (!strong && !mid) return t + (s.gl.length ? 'Two joined cells fire together, and the hairline between them brightens.' : 'Every connection is a faint hairline.');
    return t + (strong === 1 ? 'One connection, between two cells that fired together, has grown bright and thick' : strong ? (strong < 4 ? 'A few connections' : 'Several connections') + ', between cells that fired together, have grown bright and thick and link those cells into groups' : 'A few connections, between cells that fired together, have grown brighter and thicker') +
      '; the others are faint hairlines.' + (strong ? ' A strong connection carries a firing on to the next cell.' : '');
  }
  function userFire(m, s, list) {
    var st = copy(s);
    st.si = m.script.length;
    list.forEach(function (i) { fireCell(m, st, i, st.t); });
    if (P.reducedMotion()) {
      for (var g = 0; g < 60 && st.q.length; g++) { var x = st.q.shift(); fireCell(m, st, x.i, st.t + 0.4 * (g + 1), x.g); }
      st.t = st.act;
    }
    st.sel = list[list.length - 1];
    H.go();
    return st;
  }
  var drag = { down: -1, moved: false };
  function selMove(dir) { return function (m, s) { var ns = copy(s); ns.sel = U.towards(m.pts, s.sel, dir, m.dmin * 2.6); return ns; }; }
  function fireSel(m, s) { return userFire(m, s, [s.sel]); }
  H.settled = settled; H.go = U.driver(H);
  H.fig = P.figure({
    id: 'hebb', name: 'connections-that-grow', title: 'Connections that grow where activity meets',
    caption: 'Two pairs of cells fire together, and each time the connection between them brightens and thickens.',
    modelFor: function (box) { return makeHebb(box.width < 620); },
    initialState: initial, stillState: still,
    tick: U.watch(H, advance), settled: settled,
    // the figure's own script plays out (see makeHebb), then the picture rests on the two strong connections
    sequence: [{ dur: 13800 }],
    draw: function (m, s, pal) { H.m = m; return drawHebb(m, s, pal); }, describe: describeHebb,
    controls: [],
    handle: function (m, s) { return m.pts[s.sel]; },
    keysLabel: 'Arrow keys choose a cell; Enter fires it. Fire two neighbours one after the other to join them.',
    keys: { ArrowUp: selMove([0, -1]), ArrowDown: selMove([0, 1]), ArrowLeft: selMove([-1, 0]), ArrowRight: selMove([1, 0]), Enter: fireSel, ' ': fireSel },
    drag: {
      pick: function (m, s, p) { drag.down = U.nearest(m.pts, p, 80); drag.moved = false; return true; },
      move: function (m, s, p) {
        drag.moved = true;
        var hit = [];
        m.pts.forEach(function (q, i) { if (U.dist(p, q) < (m.narrow ? 44 : 40) && s.t - s.last[i] >= REF) hit.push(i); });
        return hit.length ? userFire(m, s, hit) : s;
      },
      end: function (m, s) { var i = drag.down; drag.down = -1; return !drag.moved && i >= 0 ? userFire(m, s, [i]) : s; }
    }
  });
})(window.Psyche);

/* ===== Row 4: a maze of corridors, seen in perspective ====================================== */
(function (P) {
  'use strict';
  var S = P.svg, U = P.wwb, H = { fig: null };
  var DIRS = [[1, -1, 0], [2, 0, 1], [4, 1, 0], [8, 0, -1]];
  var OPP = { 1: 4, 2: 8, 4: 1, 8: 2 };
  var clamp = U.clamp, ease = U.ease;
  function A(a, b) { var o = {}, k; for (k in a) o[k] = a[k]; for (k in b) o[k] = b[k]; return o; }
  function lcg(seed) { var s = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return [s, s / 4294967296]; }
  function carve(cols, rows, seed, loops, from) {
    var N = cols * rows, rng = P.mulberry(seed), open = [], seen = [], i;
    for (i = 0; i < N; i++) { open.push(0); seen.push(false); }
    var stack = [from]; seen[from] = true;
    while (stack.length) {
      var c = stack[stack.length - 1], r = Math.floor(c / cols), q = c % cols, nb = [];
      DIRS.forEach(function (d) { var rr = r + d[1], qq = q + d[2]; if (rr >= 0 && rr < rows && qq >= 0 && qq < cols && !seen[rr * cols + qq]) nb.push([rr * cols + qq, d[0]]); });
      if (!nb.length) { stack.pop(); continue; }
      var k = nb[Math.floor(rng() * nb.length)];
      open[c] |= k[1]; open[k[0]] |= OPP[k[1]]; seen[k[0]] = true; stack.push(k[0]);
    }
    var added = 0, guard = 0;
    while (added < loops && guard++ < loops * 60) {
      var cc = Math.floor(rng() * N), d = DIRS[Math.floor(rng() * 4)], r2 = Math.floor(cc / cols) + d[1], q2 = cc % cols + d[2];
      if (r2 < 0 || r2 >= rows || q2 < 0 || q2 >= cols || (open[cc] & d[0])) continue;
      open[cc] |= d[0]; open[r2 * cols + q2] |= OPP[d[0]]; added++;
    }
    return open;
  }
  function corridorRuns(cols, rows, open, hw) {
    var Hm = {}, V = {};
    function h(y, x0, x1) { var k = y.toFixed(4); (Hm[k] = Hm[k] || []).push([Math.min(x0, x1), Math.max(x0, x1)]); }
    function v(x, y0, y1) { var k = x.toFixed(4); (V[k] = V[k] || []).push([Math.min(y0, y1), Math.max(y0, y1)]); }
    for (var i = 0; i < cols * rows; i++) {
      var r = Math.floor(i / cols), q = i % cols, cx = q + 0.5, cy = r + 0.5, o = open[i];
      if (o & 1) { v(cx - hw, r, cy - hw); v(cx + hw, r, cy - hw); } else h(cy - hw, cx - hw, cx + hw);
      if (o & 4) { v(cx - hw, cy + hw, r + 1); v(cx + hw, cy + hw, r + 1); } else h(cy + hw, cx - hw, cx + hw);
      if (o & 2) { h(cy - hw, cx + hw, q + 1); h(cy + hw, cx + hw, q + 1); } else v(cx + hw, cy - hw, cy + hw);
      if (o & 8) { h(cy - hw, q, cx - hw); h(cy + hw, q, cx - hw); } else v(cx - hw, cy - hw, cy + hw);
    }
    var runs = [];
    function merge(map, horiz) {
      Object.keys(map).forEach(function (k) {
        var list = map[k].sort(function (a, b) { return a[0] - b[0]; }), cur = null, c = Number(k);
        list.forEach(function (s) {
          if (cur && s[0] <= cur[1] + 1e-6) cur[1] = Math.max(cur[1], s[1]);
          else { if (cur) runs.push(horiz ? [cur[0], c, cur[1], c] : [c, cur[0], c, cur[1]]); cur = [s[0], s[1]]; }
        });
        if (cur) runs.push(horiz ? [cur[0], c, cur[1], c] : [c, cur[0], c, cur[1]]);
      });
    }
    merge(Hm, true); merge(V, false);
    return runs;
  }
  var memo = {};
  function makeMaze(narrow) {
    var key = narrow ? 'maze-n' : 'maze-w';
    if (memo[key]) return memo[key];
    var o = narrow
      ? { cols: 6, rows: 8, seed: 29, loops: 9, view: { w: 760, h: 900 }, margin: [34, 18, 30, 18], elev: 1.06, dist: 20 }
      : { cols: 12, rows: 8, seed: 72, loops: 19, view: { w: 1400, h: 800 }, margin: [30, 18, 30, 18], elev: 0.96, dist: 19 };
    var cols = o.cols, rows = o.rows, N = cols * rows, hw = 0.21, wall = 0.34, lift = 0.04;
    var open = carve(cols, rows, o.seed, o.loops, 0), adj = [], edges = [], edgeOf = {}, i;
    for (i = 0; i < N; i++) {
      var ri = Math.floor(i / cols), qi = i % cols, list = [];
      DIRS.forEach(function (d) { if (open[i] & d[0]) list.push((ri + d[1]) * cols + qi + d[2]); });
      adj.push(list);
      if (open[i] & 2) { edgeOf[i + '-' + (i + 1)] = edgeOf[(i + 1) + '-' + i] = edges.length; edges.push([i, i + 1]); }
      if (open[i] & 4) { edgeOf[i + '-' + (i + cols)] = edgeOf[(i + cols) + '-' + i] = edges.length; edges.push([i, i + cols]); }
    }
    var ca = Math.cos(o.elev), sa = Math.sin(o.elev);
    function raw(x, h, z) { var X = x - cols / 2, Z = z - rows / 2, yc = h * ca - Z * sa, zc = o.dist - h * sa - Z * ca; return [X / zc, -yc / zc, zc]; }
    var bx0 = 1e9, bx1 = -1e9, by0 = 1e9, by1 = -1e9;
    [[0, 0], [cols, 0], [0, rows], [cols, rows]].forEach(function (p) {
      [0, wall].forEach(function (hh) { var w = raw(p[0], hh, p[1]); bx0 = Math.min(bx0, w[0]); bx1 = Math.max(bx1, w[0]); by0 = Math.min(by0, w[1]); by1 = Math.max(by1, w[1]); });
    });
    var mg = o.margin, fx = o.view.w - mg[1] - mg[3];
    var view = { w: o.view.w, h: Math.round(fx * (by1 - by0) / (bx1 - bx0)) + mg[0] + mg[2] };
    var fy = view.h - mg[0] - mg[2], sc = Math.min(fx / (bx1 - bx0), fy / (by1 - by0));
    var ox = mg[3] + fx / 2 - sc * (bx0 + bx1) / 2, oy = mg[0] + fy / 2 - sc * (by0 + by1) / 2;
    function proj(x, h, z) { var w = raw(x, h, z); return [ox + sc * w[0], oy + sc * w[1], w[2]]; }
    var runs = corridorRuns(cols, rows, open, hw), walls = [], postMap = {}, posts = [];
    runs.forEach(function (r) {
      var len = Math.hypot(r[2] - r[0], r[3] - r[1]), n = r[1] === r[3] ? 1 : Math.max(1, Math.ceil(len / 0.5));
      for (var k = 0; k < n; k++) {
        var x0 = r[0] + (r[2] - r[0]) * k / n, z0 = r[1] + (r[3] - r[1]) * k / n, x1 = r[0] + (r[2] - r[0]) * (k + 1) / n, z1 = r[1] + (r[3] - r[1]) * (k + 1) / n;
        var a = proj(x0, 0, z0), b = proj(x1, 0, z1);
        walls.push({ a: a, b: b, at: proj(x0, wall, z0), bt: proj(x1, wall, z1), z: (a[2] + b[2]) / 2 });
      }
      [[r[0], r[1]], [r[2], r[3]]].forEach(function (p) {
        var k2 = p[0].toFixed(3) + ',' + p[1].toFixed(3);
        if (postMap[k2]) return; postMap[k2] = 1;
        posts.push({ b: proj(p[0], 0, p[1]), t: proj(p[0], wall, p[1]) });
      });
    });
    var floor = [], liftP = [], plan = [];
    for (i = 0; i < N; i++) { var cr = Math.floor(i / cols) + 0.5, cq = i % cols + 0.5; plan.push([cq, cr]); floor.push(proj(cq, 0, cr)); liftP.push(proj(cq, lift, cr)); }
    var zs = floor.map(function (f) { return f[2]; });
    var mid = proj(cols / 2, 0, rows / 2), nx = proj(cols / 2 + 1, 0, rows / 2);
    var edgeMid = edges.map(function (e) { var a = plan[e[0]], b = plan[e[1]]; return proj((a[0] + b[0]) / 2, 0, (a[1] + b[1]) / 2); });
    var m = { key: key, view: view, cols: cols, rows: rows, N: N, open: open, adj: adj, edges: edges, edgeOf: edgeOf, walls: walls, posts: posts,
      floor: floor, lift: liftP, plan: plan, edgeMid: edgeMid, proj: proj, hw: hw, wall: wall, narrow: narrow,
      zNear: Math.min.apply(null, zs), zFar: Math.max.apply(null, zs), cellPx: Math.hypot(nx[0] - mid[0], nx[1] - mid[1]), fog: 0.8 };
    m.start = (rows - 1) * cols; m.goal = cols - 1;
    m.maxSteps = Math.round(N * 1.25); m.rate = 9; m.runRate = 5.5;
    return (memo[key] = m);
  }
  function route(m, from, to, blocks) {
    var prev = {}, q = [from], seen = {};
    seen[from] = 1;
    while (q.length) {
      var c = q.shift(); if (c === to) break;
      m.adj[c].forEach(function (n) { if (!seen[n] && !(blocks && blocks[m.edgeOf[c + '-' + n]])) { seen[n] = 1; prev[n] = c; q.push(n); } });
    }
    if (!seen[to]) return [];
    var path = [to]; while (path[0] !== from) path.unshift(prev[path[0]]);
    return path;
  }
  function nearness(m, z) { return Math.pow(clamp((m.zFar - z) / ((m.zFar - m.zNear) || 1), 0, 1), m.fog); }
  function depthScale(m, z) { return ((m.zNear + m.zFar) / 2) / z; }
  var backCache = {};
  function mazeBack(m, pal) {
    var key = m.key + ':' + pal.name;
    if (backCache[key]) return backCache[key];
    var hv = m.narrow && pal.name !== 'dark', kw = hv ? 1.7 : 1, B = U.bucket(pal);
    function op(v) { return hv ? Math.min(1, 0.22 + v * 1.2) : v; }
    function ln(a, b) { return 'M' + S.n(a[0]) + ' ' + S.n(a[1]) + 'L' + S.n(b[0]) + ' ' + S.n(b[1]); }
    // batched: walls of the same look share one path (see bucket)
    m.walls.forEach(function (w) {
      var f = nearness(m, w.z);
      B.stroke(ln(w.a, w.b), 'quiet', 0.7 * kw, op(0.12 + 0.5 * f));
      B.stroke(ln(w.at, w.bt), 'ink', (0.7 + 0.8 * f) * kw, op(0.1 + 0.84 * f));
    });
    m.posts.forEach(function (p) { var f = nearness(m, p.b[2]); B.stroke(ln(p.b, p.t), 'faint', 0.7 * kw, op(0.2 + 0.8 * f)); });
    m.floor.forEach(function (c) { var f = nearness(m, c[2]); B.dot(c[0], c[1], (0.7 + 1.1 * f) * Math.min(1.6, m.cellPx / 70), 'quiet', 0.16 + 0.36 * f); });
    return (backCache[key] = B.text() + placeMark(m, pal, m.start, 'soft'));
  }
  function ring(m, cell, rad) {
    var c = m.plan[cell], pts = [];
    for (var k = 0; k < 32; k++) { var a = k / 32 * 6.2832, p = m.proj(c[0] + Math.cos(a) * rad, 0.02, c[1] + Math.sin(a) * rad); pts.push([p[0], p[1]]); }
    return pts;
  }
  function pointAt(m, from, to, u) {
    var a = m.lift[from], b = m.lift[to], e = ease(clamp(u, 0, 1));
    return [a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e, a[2] + (b[2] - a[2]) * e];
  }
  function lightPoint(m, p, pal) {
    var k = depthScale(m, p[2]) * Math.min(1.7, m.cellPx / 64), dark = pal.name === 'dark';
    return S.dot(p[0], p[1], 15 * k, pal, 'mint', dark ? 0.15 : 0.1) + S.dot(p[0], p[1], 5.6 * k, pal, dark ? 'ink' : 'mint');
  }
  function corridorLine(m, a, b, pal, role, w, op) {
    var p = m.lift[a], q = m.lift[b], f = nearness(m, (p[2] + q[2]) / 2);
    return S.line(p[0], p[1], q[0], q[1], pal, role, w * (0.75 + 0.5 * f), op * (0.35 + 0.65 * f));
  }
  function routeLine(m, cells, upto, pal, role, w, op, dash) {
    if (cells.length < 2) return '';
    var pts = [], n = Math.min(cells.length - 1, upto), whole = Math.floor(n), i;
    for (i = 0; i <= whole; i++) pts.push([m.lift[cells[i]][0], m.lift[cells[i]][1]]);
    if (n > whole && whole + 1 < cells.length) { var p = pointAt(m, cells[whole], cells[whole + 1], n - whole); pts.push([p[0], p[1]]); }
    if (pts.length < 2) return '';
    return S.path(pts, pal, role, w, { opacity: op, dash: dash });
  }
  // a blocked corridor: one short bright bar standing across it, wall to wall
  function barrier(m, pal, e, role, w, op) {
    var a = m.plan[m.edges[e][0]], b = m.plan[m.edges[e][1]], mx = (a[0] + b[0]) / 2, mz = (a[1] + b[1]) / 2;
    var horiz = a[1] === b[1], h = m.hw * 1.05, y = m.wall * 0.55;
    var p0 = horiz ? [mx, mz - h] : [mx - h, mz], p1 = horiz ? [mx, mz + h] : [mx + h, mz];
    var t0 = m.proj(p0[0], y, p0[1]), t1 = m.proj(p1[0], y, p1[1]), k = Math.min(1.6, m.cellPx / 70);
    return (pal.glow ? S.line(t0[0], t0[1], t1[0], t1[1], pal, 'mint', w * 3.2 * k, 0.22) : '') + S.line(t0[0], t0[1], t1[0], t1[1], pal, role, w * 1.5 * k, op);
  }
  function placeMark(m, pal, cell, role) {
    return S.path(ring(m, cell, 0.34), pal, role, 1.6, { close: true }) + S.path(ring(m, cell, 0.17), pal, role, 1.1, { close: true, opacity: 0.7 });
  }
  // one move of an explorer: it prefers places it has not been, and rarely turns straight back
  function explore(m, s) {
    var opts = m.adj[s.cell], r1 = lcg(s.seed), r2 = lcg(r1[0]);
    var fresh = opts.filter(function (c) { return !s.visited[c]; });
    var pool = fresh.length && r1[1] < 0.88 ? fresh : (opts.length > 1 ? opts.filter(function (c) { return c !== s.prev; }) : opts);
    return { next: pool[Math.floor(r2[1] * pool.length)], seed: r2[0] };
  }
  function share(arr) { var n = 0; for (var i = 0; i < arr.length; i++) n += arr[i] ? 1 : 0; return n / arr.length; }
  function shareWords(v) { return v >= 0.98 ? 'every place in it' : v > 0.75 ? 'most of it' : v > 0.4 ? 'about half of it' : v > 0.08 ? 'a part of it' : 'only where it started'; }

  function initialState(m) {
    var v = [], c = [], i;
    for (i = 0; i < m.N; i++) v.push(0);
    for (i = 0; i < m.edges.length; i++) c.push(0);
    v[m.start] = 1;
    return { phase: 'explore', cell: m.start, prev: m.start, u: 1, steps: 0, visited: v, counts: c, seed: 4111, trail: [m.start], run: [], ri: 0, to: m.goal, blocks: {}, old: [] };
  }
  function moveTo(m, s, next, seed) {
    var v = s.visited.slice(), c = s.counts.slice(), e = m.edgeOf[s.cell + '-' + next];
    v[next] = 1; if (e != null) c[e]++;
    return A(s, { cell: next, prev: s.cell, u: 0, steps: s.steps + 1, visited: v, counts: c, seed: seed, trail: s.trail.concat([next]).slice(-12) });
  }
  // where the point is now, as a place in the maze
  function here(m, s) { return s.phase === 'explore' ? s.cell : s.run.length ? s.run[Math.min(s.run.length - 1, Math.round(s.ri))] : s.cell; }
  function trip(m, s, to, extra) {
    var from = here(m, s), run = route(m, from, to, s.blocks);
    return A(s, A({ phase: run.length > 1 ? 'go' : 'done', cell: from, prev: from, u: 1, run: run.length ? run : [from], ri: 0, to: to }, extra || {}));
  }
  function tick(m, s, dt) {
    if (s.phase === 'explore') {
      var u = s.u + dt * m.rate;
      if (u < 1) return A(s, { u: u });
      if (s.steps >= m.maxSteps) return trip(m, A(s, { u: 1 }), m.goal);
      var e = explore(m, s), ns = moveTo(m, s, e.next, e.seed); ns.u = Math.min(1, u - 1); return ns;
    }
    if (s.phase === 'go') {
      var ri = s.ri + dt * m.runRate;
      if (ri >= s.run.length - 1) return A(s, { phase: 'done', ri: s.run.length - 1, cell: s.run[s.run.length - 1] });
      return A(s, { ri: ri });
    }
    return s;
  }
  function step(m, s) {
    if (s.phase === 'explore') { if (s.steps >= m.maxSteps) return trip(m, s, m.goal); var e = explore(m, s), ns = moveTo(m, s, e.next, e.seed); ns.u = 1; return ns; }
    if (s.phase === 'go') { var ri = Math.min(s.run.length - 1, Math.floor(s.ri + 1e-6) + 1); return A(s, { ri: ri, phase: ri >= s.run.length - 1 ? 'done' : 'go' }); }
    return s;
  }
  // block a corridor on the route ahead: it takes another
  function blockRoute(m, s) {
    var s0 = s.phase === 'explore' ? A(s, { u: 1 }) : s;
    var from = here(m, s0), to = s0.phase === 'done' ? (s0.to === m.goal ? m.start : m.goal) : s0.to;
    var base = route(m, from, to, s0.blocks);
    if (base.length < 3) { to = to === m.goal ? m.start : m.goal; base = route(m, from, to, s0.blocks); }
    // the corridor just ahead of the point (the second one if the first cannot be blocked), so the turn is seen where it happens
    for (var k = Math.min(2, base.length - 1), tries = 0; tries < base.length; tries++, k = (k % (base.length - 1)) + 1) {
      var e = m.edgeOf[base[k - 1] + '-' + base[k]], nb = A(s0.blocks, {}); nb[e] = 1;
      if (route(m, from, to, nb).length) return finish(trip(m, A(s0, { blocks: nb, phase: 'go', run: [from], ri: 0 }), to, { old: base }));
    }
    return s;
  }
  function toggleBlock(m, s, e) {
    var s0 = s.phase === 'explore' ? A(s, { u: 1 }) : s;
    var from = here(m, s0), to = s0.phase === 'done' ? (s0.to === m.goal ? m.start : m.goal) : s0.to;
    var nb = A(s0.blocks, {});
    if (nb[e]) delete nb[e]; else nb[e] = 1;
    if (!route(m, from, to, nb).length) return s; // never cut the far place off
    var old = route(m, from, to, s0.blocks);
    return finish(trip(m, A(s0, { blocks: nb, phase: 'go', run: [from], ri: 0 }), to, { old: old }));
  }
  function finish(s) { if (P.reducedMotion()) return A(s, { phase: 'done', ri: s.run.length - 1, cell: s.run[s.run.length - 1] }); H.go(); return s; }
  // the same block as blockRoute, for the figure's own story (no motion started for the reader)
  function blockAhead(m, s) {
    var from = here(m, s), to = s.to, base = route(m, from, to, s.blocks);
    if (base.length < 3) { to = to === m.goal ? m.start : m.goal; base = route(m, from, to, s.blocks); }
    for (var k = Math.min(2, base.length - 1), tries = 0; tries < base.length; tries++, k = (k % (base.length - 1)) + 1) {
      var e = m.edgeOf[base[k - 1] + '-' + base[k]], nb = A(s.blocks, {}); nb[e] = 1;
      if (route(m, from, to, nb).length) return trip(m, A(s, { blocks: nb, phase: 'go', run: [from], ri: 0 }), to, { old: base });
    }
    return s;
  }
  // the wander as a number of moves done so far (a real number: the point is part way along the last)
  function wanderTo(m, s, target) {
    var want = Math.max(0, Math.ceil(target - 1e-9));
    while (s.steps < want) { var e = explore(m, s); s = moveTo(m, s, e.next, e.seed); }
    return A(s, { u: want === 0 ? 1 : clamp(target - (want - 1), 0, 1) });
  }
  function wanderK(m) { return Math.round(m.N * 0.6); }
  function aheadAt(m, s) { return Math.max(0, Math.min(4, s.run.length - 3)); }
  function arrive(m, s) { return A(s, { phase: 'done', ri: s.run.length - 1, cell: s.run[s.run.length - 1] }); }
  // The figure's story: the point wanders part of the maze, then sets off for the far corner; a few
  // places on, a corridor on its route is blocked, the old route stays dotted, and it takes another way.
  var MAZE_SEQ = [
    { dur: 400, tick: false },
    { dur: 6000, tick: false, ease: 'linear', frame: function (m, s, u) { return wanderTo(m, s, u * wanderK(m)); } },
    { dur: 600, tick: false },
    { dur: 0, do: function (m, s) { return trip(m, A(s, { u: 1 }), m.goal); } },
    { dur: 1500, tick: false, ease: 'linear', to: function (m, s) { return { ri: aheadAt(m, s) }; } },
    { dur: 0, do: blockAhead },
    { dur: 1100, tick: false },
    { dur: 4400, tick: false, to: function (m, s) { return { ri: s.run.length - 1 }; } },
    { dur: 0, do: arrive },
    { dur: 600, tick: false }
  ];
  var endMemo = {};
  function mazeEnd(m) {
    if (endMemo[m.key]) return endMemo[m.key];
    var s = wanderTo(m, initialState(m), wanderK(m));
    s = trip(m, A(s, { u: 1 }), m.goal);
    s = blockAhead(m, A(s, { ri: aheadAt(m, s) }));
    return (endMemo[m.key] = arrive(m, A(s, { ri: s.run.length - 1 })));
  }
  function where(m, s) {
    if (s.phase === 'explore') return pointAt(m, s.prev, s.cell, s.u);
    var i = Math.floor(s.ri), f = s.ri - i;
    if (i >= s.run.length - 1) return m.lift[s.run[s.run.length - 1]];
    return pointAt(m, s.run[i], s.run[i + 1], f);
  }
  // The walls, the floor and the start are still: they are the back, drawn once. The moving layer is in
  // parts: the corridors walked so far change only when the point reaches a new place; each frame writes
  // only the trail (or route) and the point.
  function draw(m, s, pal) {
    var map = '', trail = '', route = '', i, travelling = s.phase !== 'explore';
    for (i = 0; i < m.edges.length; i++) if (s.counts[i]) {
      var e = m.edges[i], cw = 1.2 + 0.35 * Math.min(4, s.counts[i]), co = Math.min(0.9, 0.24 + 0.17 * s.counts[i]) * (travelling ? 0.7 : 1);
      if (pal.glow) map += corridorLine(m, e[0], e[1], pal, 'peri', cw * 3.2 + 1.6, co * 0.16);
      map += corridorLine(m, e[0], e[1], pal, 'peri', 1.2 + 0.35 * Math.min(4, s.counts[i]), Math.min(0.9, 0.24 + 0.17 * s.counts[i]) * (travelling ? 0.7 : 1));
    }
    for (i = 0; i < m.N; i++) if (s.visited[i]) { var p = m.floor[i]; map += S.dot(p[0], p[1], 2.4 * Math.min(1.6, m.cellPx / 70), pal, 'peri', travelling ? 0.55 : 0.8); }
    if (s.phase === 'explore') {
      var tr = s.trail, n = tr.length;
      for (var j = 1; j < n; j++) {
        var a = m.lift[tr[j - 1]], b = j === n - 1 ? pointAt(m, s.prev, s.cell, s.u) : m.lift[tr[j]], ag = (n - 1 - j) / Math.max(1, n - 1), op = Math.pow(1 - ag, 1.6) * 0.9;
        if (op > 0.04) trail += S.glowPath([[a[0], a[1]], [b[0], b[1]]], pal, 'mint', 2.2, { opacity: op });
      }
    } else {
      if (s.old.length > 1) route += routeLine(m, s.old, s.old.length, pal, 'peri', 1.8, 0.5, '2 7');
      var rl = routeLine(m, s.run, s.ri, pal, 'mint', 3, 1);
      if (rl && pal.glow) rl = routeLine(m, s.run, s.ri, pal, 'mint', 3 * 3.2 + 1.6, 0.16) + rl;
      route += rl;
    }
    var blocks = '';
    Object.keys(s.blocks).forEach(function (k) { blocks += barrier(m, pal, +k, 'ink', 2.6, 1); });
    return { back: mazeBack(m, pal), front: { map: map, route: route, trail: trail, blocks: blocks, point: lightPoint(m, where(m, s), pal) } };
  }
  function describe(m, s) {
    var base = 'A maze of corridors drawn in light and seen at an angle, with a start in the near corner. ';
    if (s.phase === 'explore') return base + 'A point of light wanders it with no reward and has visited ' + shareWords(share(s.visited)) + '; each corridor it uses brightens and stays lit.';
    var nb = Object.keys(s.blocks).length;
    if (!nb) return base + 'After wandering, the point goes along the corridors it has explored ' + (s.phase === 'done' ? 'and stands in the far corner.' : 'toward the far corner.');
    return base + (nb === 1 ? 'A corridor just ahead of it is blocked' : (['Two', 'Three', 'Four', 'Five'][nb - 2] || 'Several') + ' corridors are blocked') + '. The route it would have taken stays as a dotted line, and the point takes another way' + (s.phase === 'done' ? ' around the block.' : '.');
  }
  var picked = -1;
  H.settled = function (m, s) { return s.phase === 'done'; }; H.go = U.driver(H);
  H.fig = P.figure({
    id: 'maze', name: 'a-maze-with-no-reward', title: 'A maze with no reward, and a blocked route',
    caption: 'A point of light wanders a maze with no reward; when a corridor on its route is blocked, it takes another way.',
    modelFor: function (box) { return makeMaze(box.width < 620); },
    initialState: initialState, stillState: mazeEnd, tick: U.watch(H, tick), step: step,
    settled: H.settled,
    finishStep: function (m, s) { return s.phase === 'explore' ? A(s, { u: 1 }) : s; },
    sequence: MAZE_SEQ,
    draw: function (m, s, pal) { H.m = m; return draw(m, s, pal); }, frontGlow: false, describe: describe,
    controls: [],
    handle: function (m, s) { var p = where(m, s); return [p[0], p[1]]; },
    keysLabel: 'Enter blocks the route ahead of the point.',
    keys: { Enter: blockRoute, ' ': blockRoute },
    drag: {
      pick: function (m, s, p) {
        var best = -1, bd = Infinity;
        m.edgeMid.forEach(function (q, i) { var d = Math.hypot(p[0] - q[0], p[1] - q[1]); if (d < bd) { bd = d; best = i; } });
        picked = bd < m.cellPx * 0.45 ? best : -1;
        return picked >= 0;
      },
      move: function (m, s) { return s; },
      end: function (m, s) { var e = picked; picked = -1; return e < 0 ? s : toggleBlock(m, s, e); }
    }
  });
})(window.Psyche);

/* ===== Row 5: one steady point beside a field of lights ===================================== */
(function (P) {
  'use strict';
  var S = P.svg, U = P.wwb, memo = {};
  // still: the model the stills and exports use (it draws only what is in the picture)
  function makeWatts(narrow, still) {
    var key = (narrow ? 'watts-n' : 'watts-w') + (still ? '-x' : '');
    if (memo[key]) return memo[key];
    var view = narrow ? { w: 800, h: 900 } : { w: 1600, h: 760 }, W = view.w, Hh = view.h;
    // a camera above a flat ground: rows of lights recede toward a horizon and run past both edges
    var hy = Hh * (narrow ? 0.12 : 0.16), vx = W * 0.5, f = (Hh - hy - 22) * 1.12;
    var dx = 0.06, rows = [], z = 1.12, k = 0;
    // rows too far for single lights are left out (the field thins into the distance instead)
    while (z < 60) { if (f * dx / z > 3.4) { rows.push({ z: z, k: k }); k++; } z += 0.07 * z * 0.9 + 0.012; }
    // the one steady point stands on the same ground, in a small clearing near the left
    var zp = narrow ? 3.2 : 1.5, bx = W * (narrow ? 0.24 : 0.14);
    // the view travels until the point has left the picture well behind, and the field still runs on
    var PM = 1.3 * W * zp / f;
    return (memo[key] = { key: key, view: view, W: W, H: Hh, hy: hy, vx: vx, f: f, dx: dx, rows: rows, K: rows.length, PM: PM,
      brain: [bx, hy + f / zp], Xp: (bx - vx) * zp / f, zp: zp, clear: narrow ? [34, 120] : [44, 170], narrow: narrow,
      // the lights are drawn a little past the right edge, so the view can move that far by moving the rows
      // alone; only then is the field drawn again. The stills draw no more than the picture.
      SL: still ? 0 : 0.8 });
  }
  function smooth(u) { u = U.clamp(u, 0, 1); return u * u * (3 - 2 * u); }
  // the place the rows are drawn for: the view's place, rounded down to a whole slack
  function baseOf(m, pan) { return m.SL ? Math.floor(pan / m.SL + 1e-9) * m.SL : pan; }
  // Per row, its lights in a few strengths, each strength one path, drawn for one base place. Kept for
  // the last base, so while the view moves only each row's shift changes, and while the rows come on
  // only their opacity.
  function rowsAt(m, base) {
    if (m.__geo && m.__geo.base === base) return m.__geo.rows;
    var W = m.W, h01 = U.h01, b = m.brain, STEPS = 5, out = [];
    m.rows.forEach(function (r) {
      var z = r.z, sy = m.hy + m.f / z, sp = m.f * m.dx / z;
      var far = smooth((sp - 3.4) / 5);
      var rr = Math.max(0.6, 2.9 / Math.pow(z, 0.62)), depth = Math.log(z) / Math.log(60);
      var Xa = base + (-8 - m.vx) * z / m.f, Xb = base + m.SL + (W + 8 - m.vx) * z / m.f, xr = W + 8 + m.f * m.SL / z;
      var buckets = [], q;
      for (q = 0; q < STEPS * 2; q++) buckets.push('');
      var j0 = Math.floor(Xa / m.dx) - 1, j1 = Math.ceil(Xb / m.dx) + 1;
      for (var j = j0; j <= j1; j++) {
        var X = (j + (h01(j, r.k) - 0.5) * 0.7) * m.dx;
        var sx = m.vx + m.f * (X - base) / z, yy = sy + (h01(r.k, j + 0.3) - 0.5) * Math.min(2.5, sp * 0.5);
        if (sx < -8 || sx > xr) continue;
        // the clearing around the point lies on the ground with it, so it travels with the field
        var d = Math.hypot((X - m.Xp) * m.f / m.zp, (yy - b[1]) * 1.7);
        var al = smooth((d - m.clear[0]) / m.clear[1]) * (0.5 + 0.5 * h01(j * 0.37, r.k * 1.3));
        if (al < 0.06) continue;
        var bi = Math.min(STEPS - 1, Math.floor(al * STEPS)) + (h01(j * 1.7, r.k * 2.3) < 0.2 ? STEPS : 0);
        buckets[bi] += 'M' + S.n(sx) + ' ' + S.n(yy) + 'h0';
      }
      out.push({ k: r.k, z: z, rr: rr, op: (1 - 0.5 * depth) * far, buckets: buckets });
    });
    m.__geo = { base: base, rows: out };
    return out;
  }
  // how far each row has come on: near rows first, the far ones last
  function rowOn(m, on, k) { return U.clamp((on * (m.K + 10) - k) / 10, 0, 1); }
  function shiftOf(m, z, pan, base) { return S.n(-m.f * (pan - base) / z); }
  function rowAttrs(m, r, s, pan, base) {
    var o = rowOn(m, s.on, r.k), sh = shiftOf(m, r.z, pan, base);
    return (sh ? ' transform="translate(' + sh + ' 0)"' : '') + (o < 1 ? ' opacity="' + S.n(o) + '"' : '');
  }
  function fieldText(m, s, pan, base, pal) {
    var out = '', STEPS = 5;
    rowsAt(m, base).forEach(function (r) {
      var inner = '';
      for (var q = 0; q < STEPS; q++) {
        var aq = 0.3 + 0.7 * (q + 0.5) / STEPS;
        if (r.buckets[q]) inner += '<path d="' + r.buckets[q] + '" ' + S.stroke(pal, 'read', 2 * r.rr / pal.weight, r.op * aq) + '/>';
        if (r.buckets[q + STEPS]) inner += '<path d="' + r.buckets[q + STEPS] + '" ' + S.stroke(pal, 'ink', 2.5 * r.rr / pal.weight, Math.min(1, r.op * aq * 1.2)) + '/>';
      }
      if (inner) out += '<g data-r="' + r.k + '"' + rowAttrs(m, r, s, pan, base) + '>' + inner + '</g>';
    });
    return out;
  }
  // the point: small, clearly lit, steady; a soft light around it in dark, a ring in light and print
  function pointText(m, pal) {
    var b = m.brain, pr = m.narrow ? 7 : 6;
    return U.halo(b[0], b[1], pr * 2.8, pal, 'mint', 0.24) + S.dot(b[0], b[1], pr, pal, 'mint');
  }
  function drawWatts(m, s, pal) {
    var pan = s.v * m.PM, base = baseOf(m, pan), sh = shiftOf(m, m.zp, pan, 0);
    m.__gen = (m.__gen || 0) + 1;
    return { back: '', front: { field: fieldText(m, s, pan, base, pal),
      point: '<g data-pt="1"' + (sh ? ' transform="translate(' + sh + ' 0)"' : '') + '>' + pointText(m, pal) + '</g>' } };
  }
  // every later frame: each row's shift and opacity, and the point's shift, set in place
  function updateWatts(m, s, ctx) {
    var g = ctx.parts;
    if (!g || !g.field || !g.point) return false;
    var pan = s.v * m.PM, base = baseOf(m, pan);
    if (!m.__geo || m.__geo.base !== base) return false; // past the drawn lights: draw again
    var c = m.__wc;
    if (!c || c.gen !== m.__gen || c.field !== g.field) {
      var els = {};
      Array.prototype.forEach.call(g.field.children, function (e) { els[e.getAttribute('data-r')] = { el: e, t: e.getAttribute('transform'), o: e.getAttribute('opacity') }; });
      c = m.__wc = { gen: m.__gen, field: g.field, els: els, pt: g.point.querySelector('[data-pt]') };
      c.ptT = c.pt ? c.pt.getAttribute('transform') : null;
    }
    m.__geo.rows.forEach(function (r) {
      var e = c.els[r.k]; if (!e) return;
      var sh = shiftOf(m, r.z, pan, base), t = sh ? 'translate(' + sh + ' 0)' : null, o = rowOn(m, s.on, r.k), os = o < 1 ? String(S.n(o)) : null;
      if (t !== e.t) { if (t) e.el.setAttribute('transform', t); else e.el.removeAttribute('transform'); e.t = t; }
      if (os !== e.o) { if (os) e.el.setAttribute('opacity', os); else e.el.removeAttribute('opacity'); e.o = os; }
    });
    if (c.pt) {
      var ps = shiftOf(m, m.zp, pan, 0), pt = ps ? 'translate(' + ps + ' 0)' : null;
      if (pt !== c.ptT) { if (pt) c.pt.setAttribute('transform', pt); else c.pt.removeAttribute('transform'); c.ptT = pt; }
    }
  }
  function describeWatts(m, s) {
    var t = 'Near the left, on dark ground, stands one small steady point of light. ';
    if (s.on <= 0) return t + 'Beside it the ground is still dark.';
    t += 'Beside it a field of lights spreads over the ground to the horizon and runs past the edges of the picture. ';
    if (s.on < 1) return t + 'The lights of the field are coming up, row by row.';
    if (s.v < 0.02) return t + 'The view rests on the point, at the start of the field.';
    return t + (s.v > 0.6 ? 'The view has travelled far along the field: the point is out of sight and the lights still run on past the edge.'
      : 'The view is travelling along the field, which runs on past the edge.');
  }
  var drag = null;
  function nudge(m, s, k) { return { on: 1, v: U.clamp(s.v + 0.08 * k, 0, 1) }; }
  P.figure({
    id: 'watts', name: 'one-point-and-a-field', title: 'One steady point and a field of lights',
    caption: 'One steady point of light; beside it a field of lights comes up, and the view travels far along the field and comes back to the point.',
    modelFor: function (box) { return makeWatts(box.width < 620, box.width === 1600 && box.height === 900); },
    initialState: function () { return { on: 0, v: 0 }; },
    stillState: function () { return { on: 1, v: 0 }; },
    // the point alone, held; the field comes up row by row, near to far; the view travels far along
    // it, past the point, while the field runs on past the edge; then it comes back to the point
    sequence: [
      { dur: 1400 },
      { dur: 3200, to: { on: 1 }, ease: 'linear' },
      { dur: 900 },
      { dur: 6500, to: { v: 1 }, ease: smooth },
      { dur: 1200 },
      { dur: 6000, to: { v: 0 }, ease: smooth },
      { dur: 1000 }
    ],
    draw: drawWatts, update: updateWatts, frontGlow: false,
    describe: describeWatts,
    controls: [],
    keysLabel: 'Left and right arrow keys move along the field.',
    keys: {
      ArrowRight: function (m, s) { return nudge(m, s, 1); },
      ArrowLeft: function (m, s) { return nudge(m, s, -1); },
      Home: function () { return { on: 1, v: 0 }; },
      End: function () { return { on: 1, v: 1 }; }
    },
    drag: {
      pick: function (m, s, p) { drag = { x: p[0], v: s.v }; return true; },
      move: function (m, s, p) { if (!drag) return s; return { on: 1, v: U.clamp(drag.v + (drag.x - p[0]) * m.zp / m.f / m.PM, 0, 1) }; },
      end: function (m, s) { drag = null; return { on: 1, v: s.v }; }
    }
  });
})(window.Psyche);

/* ===== The close: the field of the opening returns around the last words, one pulse, then stillness == */
(function (P) {
  'use strict';
  var U = P.wwb, D = U.deep;
  var sec = document.querySelector('.w-close'), host = sec && sec.querySelector('.w-close__field');
  if (!sec || !host || !D) return;
  var m = null, t = 0, started = false, raf = 0, last = 0, seen = false, visible = false, layoutKey = '', groups = null;
  var root = document.documentElement;
  function measure() {
    var r = sec.getBoundingClientRect(), W = Math.round(r.width), Hh = Math.round(r.height), narrow = W <= 700;
    function box(el, padX, padY) { var b = el.getBoundingClientRect(); return [b.left - r.left - padX, b.top - r.top - padY, b.right - r.left + padX, b.bottom - r.top + padY]; }
    var h2 = sec.querySelector('.w-big'), under = sec.querySelector('.k-under'), pt = sec.querySelector('.w-close__point');
    var fs = parseFloat(getComputedStyle(h2).fontSize) || 100, pb = pt.getBoundingClientRect();
    // the words keep a clear field around them; the field thins toward that edge (makeDeep's soft edge)
    var lines = [box(h2, fs * 0.5, fs * 0.3), box(under, fs * 0.45, fs * 0.3),
      // and it thins out toward the top and bottom of the screen instead of being cut there
      [-200, -400, W + 200, narrow ? 24 : 40], [-200, Hh - (narrow ? 36 : 56), W + 200, Hh + 400]];
    // no ring opens here: nothing of the pulse comes near the words
    return { tag: 'close', w: W, h: Hh, fs: fs, top: 0, lines: lines, pad: 0, seed: narrow ? 23 : 11, density: narrow ? 0.9 : 0.85,
      vx: 0.5, vy: narrow ? 0.13 : 0.46, noRing: true,
      dot: [pb.left - r.left + pb.width / 2, pb.top - r.top + pb.height / 2] };
  }
  function keyOf(o) { return [o.w, o.h].concat(o.lines.slice(0, 2).map(function (b) { return b.map(Math.round).join(','); })).join('|'); }
  function state() { return { t: t, waves: started ? [{ src: m.D, t0: 0 }] : [], sel: m.D }; }
  function end() { return D.wave(m, m.D).max + 1.7; }
  // the same tight glow as the kit's figures: a close halo and a slightly wider faint one, under the sharp strokes
  function glowDef(v) {
    function am(a) { return '1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 ' + a + ' 0'; }
    return '<defs><filter id="wc-glow" filterUnits="userSpaceOnUse" x="-12" y="-12" width="' + (v.w + 24) + '" height="' + (v.h + 24) + '" color-interpolation-filters="sRGB">' +
      '<feGaussianBlur in="SourceGraphic" stdDeviation="3" result="f"/><feColorMatrix in="f" type="matrix" values="' + am(0.26) + '" result="fa"/>' +
      '<feGaussianBlur in="SourceGraphic" stdDeviation="1.1" result="n"/><feColorMatrix in="n" type="matrix" values="' + am(0.7) + '" result="na"/>' +
      '<feMerge><feMergeNode in="fa"/><feMergeNode in="na"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>';
  }
  // two layers: the still field once, with its glow; the pulse above it, changed in place every frame
  function paintAll() {
    if (!m) return;
    var pal = P.palettes[P.theme.get()], L = D.draw(m, state(), pal), v = m.view;
    var open = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + v.w + ' ' + v.h + '" preserveAspectRatio="none" focusable="false" opacity="' + (pal.glow ? 0.62 : 0.6) + '"';
    host.innerHTML = open + '>' + (pal.glow ? glowDef(v) + '<g filter="url(#wc-glow)">' : '<g>') + L.back + '</g></svg>' +
      open + ' class="w-close__front">' + D.parts.map(function (k) { return '<g data-p="' + k + '">' + L.front[k] + '</g>'; }).join('') + '</svg>';
    groups = {};
    D.parts.forEach(function (k) { groups[k] = host.querySelector('[data-p="' + k + '"]'); });
  }
  function paint() {
    if (!m) return;
    if (!groups) return paintAll();
    D.sync(m, state(), P.palettes[P.theme.get()], groups, host);
  }
  function build() {
    var o = measure();
    if (!o.w || !o.h) return;
    var k = keyOf(o);
    if (m && k === layoutKey) return; // nothing moved: keep what is drawn
    layoutKey = k;
    var wasDone = started && !raf;
    m = D.make(o);
    if ((P.reducedMotion() && seen) || wasDone) { started = true; t = end(); }
    groups = null;
    paintAll();
  }
  function frame(now) {
    raf = 0;
    if (root.classList.contains('k-leaving') || !visible) { last = 0; return; } // resumes when seen again
    var dt = last ? Math.min(0.05, (now - last) / 1000) : 0; last = now;
    t = Math.min(end(), t + dt); paint();
    if (t < end()) raf = requestAnimationFrame(frame);
  }
  function run() { if (!raf && started && m && t < end() && !P.reducedMotion()) { last = 0; raf = requestAnimationFrame(frame); } }
  function begin() {
    if (!m) build();
    if (!m) return;
    if (started) return run();
    seen = true; started = true;
    if (P.reducedMotion()) { t = end(); paint(); return; }
    t = -0.6; run();
  }
  // set up only once the page is styled (kit.css may arrive after this script): nothing is measured before
  P.ready(function () {
  if ('IntersectionObserver' in window) {
    // built while it is still a screen away, in idle time; the pulse starts when it is well in view
    var idle = window.requestIdleCallback ? function (fn) { requestIdleCallback(fn, { timeout: 400 }); } : function (fn) { setTimeout(fn, 30); };
    var near = new IntersectionObserver(function (es) { if (es.some(function (e) { return e.isIntersecting; })) { near.disconnect(); idle(function () { if (!m) build(); }); } }, { rootMargin: '100% 0px' });
    near.observe(sec);
    new IntersectionObserver(function (es) { es.forEach(function (e) { visible = e.isIntersecting; if (visible && e.intersectionRatio >= 0.45) begin(); else if (visible) run(); }); }, { threshold: [0, 0.45] }).observe(sec);
  } else { build(); visible = true; begin(); }
  });
  // measured again only when the section or its words moved
  var rt = 0;
  function later() { clearTimeout(rt); rt = setTimeout(function () { if (m) build(); }, 200); }
  window.addEventListener('resize', later);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(later);
  window.addEventListener('pageshow', function () { if (visible) run(); });
  P.theme.onChange(function () { groups = null; paintAll(); });
})(window.Psyche);
