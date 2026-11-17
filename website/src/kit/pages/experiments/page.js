(function (P) {
  'use strict';
  var S = P.svg, n = S.n;
  var TAU = Math.PI * 2, DEG = Math.PI / 180;

  /* ===== Small helpers ================================================================ */
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function mix(p, q, t) { return [lerp(p[0], q[0], t), lerp(p[1], q[1], t)]; }
  function ease(u) { u = clamp(u, 0, 1); return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; }
  function easeOut(u) { u = clamp(u, 0, 1); return 1 - Math.pow(1 - u, 3); }
  function dist(a, b) { return Math.hypot(a[0] - b[0], a[1] - b[1]); }
  function polyLen(p) { var L = 0; for (var i = 1; i < p.length; i++) L += dist(p[i - 1], p[i]); return L; }
  function polyAt(p, d) {
    if (d <= 0) return p[0].slice(0, 2);
    for (var i = 1; i < p.length; i++) {
      var l = dist(p[i - 1], p[i]);
      if (d <= l) return mix(p[i - 1], p[i], l ? d / l : 0);
      d -= l;
    }
    return p[p.length - 1].slice(0, 2);
  }
  function polyCut(p, d0, d1) {
    if (d1 <= d0) return [];
    var out = [polyAt(p, d0)], acc = 0;
    for (var i = 1; i < p.length; i++) { acc += dist(p[i - 1], p[i]); if (acc > d0 && acc < d1) out.push(p[i].slice(0, 2)); }
    out.push(polyAt(p, d1));
    return out;
  }
  function cubic(a, b, c, d, steps) {
    var out = [];
    for (var i = 0; i <= steps; i++) {
      var t = i / steps, u = 1 - t;
      out.push([u * u * u * a[0] + 3 * u * u * t * b[0] + 3 * u * t * t * c[0] + t * t * t * d[0],
                u * u * u * a[1] + 3 * u * u * t * b[1] + 3 * u * t * t * c[1] + t * t * t * d[1]]);
    }
    return out;
  }
  // a corridor with rounded corners: each corner becomes a short arc
  function roundPoly(pts, r) {
    var out = [pts[0]];
    for (var i = 1; i < pts.length - 1; i++) {
      var a = pts[i - 1], b = pts[i], c = pts[i + 1], la = dist(a, b), lc = dist(b, c), rr = Math.min(r, la / 2, lc / 2);
      var p = mix(b, a, rr / la), q = mix(b, c, rr / lc);
      for (var k = 0; k <= 8; k++) { var t = k / 8, u = 1 - t; out.push([u * u * p[0] + 2 * u * t * b[0] + t * t * q[0], u * u * p[1] + 2 * u * t * b[1] + t * t * q[1]]); }
    }
    out.push(pts[pts.length - 1]);
    return out;
  }
  function densify(pts, step) {
    var out = [pts[0]];
    for (var i = 1; i < pts.length; i++) {
      var a = pts[i - 1], b = pts[i], k = Math.max(1, Math.ceil(dist(a, b) / step));
      for (var j = 1; j <= k; j++) out.push(mix(a, b, j / k));
    }
    return out;
  }
  function srand(s) { s.seed = (Math.imul(s.seed, 1664525) + 1013904223) >>> 0; return s.seed / 4294967296; }
  function colour(pal, role) { return pal[role][0]; }
  function rawLine(a, b, c, w, op) { return '<line x1="' + n(a[0]) + '" y1="' + n(a[1]) + '" x2="' + n(b[0]) + '" y2="' + n(b[1]) + '" stroke="' + c + '" stroke-width="' + n(w) + '" stroke-linecap="round"' + (op != null && op < 0.999 ? ' stroke-opacity="' + n(op) + '"' : '') + '/>'; }
  function rawPath(pts, c, w, extra) { return '<path d="' + S.d(pts) + '" fill="none" stroke="' + c + '" stroke-width="' + n(w) + '" stroke-linecap="round" stroke-linejoin="round"' + (extra || '') + '/>'; }
  function grp(op, inner) { return inner ? '<g opacity="' + n(op) + '">' + inner + '</g>' : ''; }
  // a dashed path in any palette (print already dashes mint; two dash attributes would break the file)
  function dpath(pts, pal, role, w, dash, opacity) {
    return S.path(pts, pal, role, w, { opacity: opacity }).replace(/ stroke-dasharray="[^"]*"/, '').replace('/>', ' stroke-dasharray="' + dash + '"/>');
  }
  // "lit" marks: mint on screen, solid ink in print (where mint would be dashed)
  function lit(pal) { return pal.dash.mint ? 'ink' : 'mint'; }
  // the light around a point: in dark a small disc held close to the point (the tight glow softens
  // only its edge), a thin ring in light and print
  function halo(x, y, r, pal, role, op) {
    return pal.glow ? S.dot(x, y, r * 0.52, pal, role, Math.min(0.5, op * 1.7)) : S.circle(x, y, r * 0.72, pal, role, 0.8, Math.min(0.6, op * 3.2));
  }
  // labels keep a thin ring of the ground colour around each letter, so a line passing under them never cuts the text
  function clear(svg, pal, w) {
    return svg.replace(/<text ([^>]*)>/g, function (all, a) {
      return '<text ' + a + ' stroke="' + pal.ground + '" stroke-width="' + (w || 4) + '" stroke-linejoin="round" paint-order="stroke">';
    });
  }
  function ratDot(p, r, pal) { return halo(p[0], p[1], r * 3.4, pal, 'mint', 0.17) + S.dot(p[0], p[1], r, pal, lit(pal)); }
  function foodMark(p, r, pal, op) {
    op = op == null ? 1 : op;
    return halo(p[0], p[1], r * 3, pal, 'peri', 0.14 * op) + S.dot(p[0], p[1], r, pal, 'peri', op) + S.circle(p[0], p[1], r * 2.1, pal, 'peri', 1, 0.6 * op);
  }
  // a place on the floor (start, end): a small round mark that stays round in perspective
  function placeMark(p, r, pal) { return S.circle(p[0], p[1], r, pal, 'soft', 1.1, 0.75) + S.dot(p[0], p[1], Math.max(1.6, r * 0.22), pal, 'soft', 0.8); }
  function reduced() { return P.reducedMotion(); }
  // after a reader's action: run the figure's motion, or (motion off) show where it ends
  function finish(def, m, s) { for (var i = 0; i < 6000 && !def.settled(m, s); i++) s = def.tick(m, s, 0.05); return s; }
  // A reader's action (a key, a drop, a click on a spot) hands the figure to the reader: the kit has
  // already stopped its sequence. The figure's own motion then runs from the new state until it
  // settles, drawn through the kit (handle.set with quiet, so it is the page and not the reader).
  // It stops as soon as the sequence plays again ("Play again", or the figure coming back into view).
  var DRIVE = {};
  function drive(def, handle) {
    var id = def.id, tok = (DRIVE[id] || 0) + 1, last = 0;
    DRIVE[id] = tok;
    function frame(ts) {
      if (DRIVE[id] !== tok || handle.sequence === 'playing' || handle.sequence === 'idle') return;
      var m = LIVE[id], s = handle.state;
      if (!m || !s || def.settled(m, s)) return;
      var dt = last ? Math.min(0.1, (ts - last) / 1000) : 1 / 60; last = ts;
      handle.set(def.tick(m, s, dt), { quiet: true });
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  function act(def, handle, m, s) {
    if (reduced()) return finish(def, m, s);
    setTimeout(function () { drive(def, handle); }, 0);
    return s;
  }
  function seqPlaying(handle) { return handle.sequence === 'playing' || handle.sequence === 'paused'; }
  // the size the kit measured, rounded, for the figures drawn to fill their box
  function boxWH(box) { return [Math.round(Math.max(320, box.width)), Math.round(Math.max(300, box.height))]; }
  function narrowPx(viewW, box) { return Math.round(viewW / Math.max(300, box.width) * 4) / 4; }

  /* One-point perspective onto a floor: world X across, Z away from the reader. s is the depth scale. */
  function persp(o) {
    var f = function (X, Z) { var s = 1 / (1 + o.k * Z); return [o.ox + X * o.sc * s, o.hz + (o.oy - o.hz) * s, s]; };
    f.o = o;
    f.zAt = function (y) { var s = (y - o.hz) / (o.oy - o.hz); return (1 / Math.max(1e-4, s) - 1) / o.k; };
    return f;
  }
  function perspFit(ox, yNear, yFar, zFar, k, sc) {
    var sF = 1 / (1 + k * zFar), hz = (yFar - yNear * sF) / (1 - sF);
    return persp({ ox: ox, oy: yNear, hz: hz, k: k, sc: sc });
  }
  // corridors as light: a fine bright core inside two narrow bands of the same ink (wider near the
  // reader), so the corridor keeps its depth without turning into a wide grey bar or a fog.
  function lanes(lines, pr, pal, o) {
    o = o || {};
    var c = colour(pal, o.role || 'ink'), band = '', band2 = '', core = '', w = o.w || 20, cw = (o.cw || 1.1) * pal.weight;
    var dark = !!pal.glow, lb = o.band === 0 ? 0 : 1;
    lines.forEach(function (pts) {
      if (pts.length < 2) return;
      var sp = densify(pts, o.step || 0.03).map(function (p) { return pr(p[0], p[1]); });
      if (lb) for (var i = 1; i < sp.length; i++) {
        var ww = w * (sp[i - 1][2] + sp[i][2]) / 2;
        if (dark) { band += rawLine(sp[i - 1], sp[i], c, Math.max(3, ww * 0.42)); band2 += rawLine(sp[i - 1], sp[i], c, Math.max(2, ww * 0.16)); }
        else { band += rawLine(sp[i - 1], sp[i], c, Math.max(3, ww * 0.3)); band2 += rawLine(sp[i - 1], sp[i], c, Math.max(2, ww * 0.12)); }
      }
      core += rawPath(sp, c, cw, o.dash ? ' stroke-dasharray="' + o.dash + '"' : '');
    });
    var co = (o.core == null ? 0.5 : o.core) * pal[o.role || 'ink'][1];
    if (dark) { var bo = o.band == null ? 0.06 : o.band; return grp(bo * 0.8, band) + grp(bo * 1.1, band2) + grp(co, core); }
    return grp(0.1 * lb, band) + grp(0.18 * lb, band2) + grp(Math.min(0.85, co * 1.25), core);
  }
  // a lit route: a world polyline drawn as a bright line in perspective
  function route(pts, pr, pal, role, w, op) {
    if (pts.length < 2) return '';
    return S.path(densify(pts, 0.04).map(function (p) { var q = pr(p[0], p[1]); return [q[0], q[1]]; }), pal, role, w, { opacity: op });
  }
  // a wall standing on the floor across a corridor: a bright bar, with a fainter echo of its top edge
  function wall(pr, X0, X1, Z, h, pal, op) {
    var a = pr(X0, Z), b = pr(X1, Z), ha = h * a[2], hb = h * b[2];
    op = op == null ? 1 : op;
    return S.line(a[0], a[1] - ha, b[0], b[1] - hb, pal, 'soft', 1.2, 0.55 * op) + S.line(a[0], a[1], b[0], b[1], pal, 'ink', 3.2, op);
  }
  function label(x, y, str, pal, role, size, anchor, op) { return S.text(x, y, str, pal, role, { size: n(size), anchor: anchor || 'middle', opacity: op }); }
  function scrollToPart(id) {
    var el = document.getElementById(id); if (!el) return;
    el.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'start' });
    var h = el.querySelector('h2');
    if (h) { h.setAttribute('tabindex', '-1'); setTimeout(function () { h.focus({ preventScroll: true }); }, reduced() ? 0 : 750); }
  }

  // Pointer hover on a figure: onMove(model, state, [x, y] in view units, or null when the pointer
  // leaves) returns a new state, or null to change nothing. The model comes from the handle's figure.
  var LIVE = {}; // the model each figure is drawing on this screen (the export model is set apart)
  function live(id, fn) { return function (box) { return (LIVE[id] = fn(box)); }; }
  function hoverFigure(id, handle, onMove, cursor) {
    var art = document.querySelector('[data-figure="' + id + '"] > .k-art'); if (!art) return;
    function viewPt(e) {
      var svg = art.querySelector('svg.k-layer-front'); if (!svg || !svg.getScreenCTM) return null;
      var ctm = svg.getScreenCTM(); if (!ctm) return null;
      var pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
      var q = pt.matrixTransform(ctm.inverse()); return [q.x, q.y];
    }
    // pointing is not acting: it never stops the figure's sequence, and while the sequence plays it changes nothing
    art.addEventListener('pointermove', function (e) {
      if (e.pointerType === 'touch' || !handle.mounted) return;
      var p = viewPt(e), m = LIVE[id]; if (!p || !m) return;
      var s = handle.state;
      if (cursor) art.style.cursor = cursor(m, s, p) || '';
      if (seqPlaying(handle)) return;
      var n2 = onMove(m, s, p);
      if (n2) handle.set(n2, { quiet: true });
    });
    art.addEventListener('pointerleave', function () {
      art.style.cursor = '';
      if (!handle.mounted || document.activeElement === art || !LIVE[id] || seqPlaying(handle)) return;
      var n2 = onMove(LIVE[id], handle.state, null); if (n2) handle.set(n2, { quiet: true });
    });
  }

  /* ===== 1. Opening: five corridors leave the title, one for each experiment ============== */
  var PARTS = ['latent', 'detour', 'shortcut', 'sets', 'order'];
  var LINES = ['It learns without being told to.', 'Block the road, and it finds another.', 'It takes a shortcut it has never taken.',
    'Learn one world, and the next comes easy.', 'It knows what it was never taught.'];
  var WANDER = (function () { // a seeded scribble for the first scene
    var r = P.mulberry(5), p = [-0.62, 0.55], out = [p], a = -1.2;
    for (var i = 0; i < 40; i++) {
      a += (r() - 0.5) * 2.1; var q = [p[0] + Math.cos(a) * 0.15, p[1] + Math.sin(a) * 0.15];
      if (Math.hypot(q[0], q[1]) > 0.78) { a += Math.PI * 0.8; continue; }
      out.push(q); p = q;
    }
    return out;
  })();
  var SCATTER = [[-0.55, -0.4], [0.3, 0.55], [-0.12, -0.62], [0.6, -0.3]];

  // where the title and the reading text are, in the opening's own pixels
  function heroGeo() {
    var sec = document.querySelector('.x-open'), t = sec && sec.querySelector('.x-title');
    if (!t || !t.offsetHeight) return null;
    // measured under the orb the title still has its arrival letter-spacing; measure it as it will
    // rest, without starting a transition, so the corridors leave from beside the settled title
    var arriving = document.documentElement.classList.contains('k-arrive');
    if (arriving) { t.style.transition = 'none'; t.style.letterSpacing = '-.025em'; }
    var tr = 0;
    [].forEach.call(t.querySelectorAll('.x-l'), function (s) { tr = Math.max(tr, t.offsetLeft + s.offsetLeft + s.offsetWidth); });
    if (arriving) { t.style.letterSpacing = ''; void t.offsetWidth; t.style.transition = ''; }
    var z = sec.querySelector('.x-open__zone'), w = sec.querySelector('.x-open__words');
    return { tr: tr, tt: t.offsetTop, tb: t.offsetTop + t.offsetHeight, zt: z && z.offsetHeight ? z.offsetTop : 0, zh: z ? z.offsetHeight : 0, wt: w ? w.offsetTop : 0 };
  }
  var heroM = null;
  function heroModel(W, H, g) {
    var narrow = W < 820;
    if (!g) g = narrow ? { tr: W - 16, tt: 70, tb: 230, zt: 250, zh: 460, wt: 720 } : { tr: W * 0.34, tt: H * 0.26, tb: H * 0.62, zt: 0, zh: 0, wt: H * 0.66 };
    var rays = [], R, hub;
    if (!narrow) {
      // the corridors leave from one point just right of the title's widest line, so no line ever
      // passes behind a letter; the five scenes stand in the free space to the right
      // the scenes stand on an arc around that point, so no corridor crosses another scene
      var x1 = W - 26, y0 = 92, y1 = H - 30, uh = y1 - y0;
      hub = [g.tr + Math.max(30, W * 0.026), clamp((y0 + y1) / 2, g.tt + 40, g.tb - 40)];
      R = clamp(Math.min((x1 - hub[0]) * 0.17, uh / 9), 40, 100);
      var rho = x1 - R - hub[0];
      for (var i = 0; i < 5; i++) {
        var cy = y0 + R + (uh - 2 * R) * i / 4, dy = cy - hub[1];
        var c = [hub[0] + Math.max(R * 2.4, Math.sqrt(Math.max(0, rho * rho - dy * dy))), cy];
        var v = [c[0] - hub[0], c[1] - hub[1]], L = Math.hypot(v[0], v[1]); v = [v[0] / L, v[1] / L];
        rays.push({ c: c, start: hub, end: [c[0] - v[0] * R * 1.16, c[1] - v[1] * R * 1.16] });
      }
    } else {
      var zt = g.zt, zh = g.zh || 400;
      R = clamp(Math.min(W * 0.15, (zh - 44) / 7), 28, 76);
      hub = [-12, zt + zh / 2];
      for (var j = 0; j < 5; j++) {
        var cx = j % 2 ? Math.min(W * 0.72, W - R - 14) : Math.max(W * 0.3, R + 40), cy = zt + R * 1.05 + (zh - 44 - R * 2.1) * j / 4;
        rays.push({ c: [cx, cy], start: [-12, cy], end: [cx - R * 1.18, cy] });
      }
    }
    return { key: 'hero:' + Math.round(W) + 'x' + Math.round(H) + ':' + Math.round(g.tr) + ':' + Math.round(g.tb) + ':' + Math.round(g.zt),
      view: { w: Math.round(W), h: Math.round(H) }, hub: hub, rays: rays, R: R, narrow: narrow, fs: narrow ? 15 : 17, tr: g.tr, lab: (g.zt || 0) + (g.zh || 400) - 6 };
  }
  var H_T0 = 0.75, H_GAP = 0.2, H_GROW = 1.05, H_LIT = 1.1;
  var H_END = H_T0 + 4 * H_GAP + H_GROW + H_LIT + 0.1;
  // a place for a scene's line where it crosses no corridor and no other scene (none: no label)
  function heroLabelAt(m, i, tw, fs) {
    var c = m.rays[i].c, R = m.R, W = m.view.w, H = m.view.h;
    var cands = [[c[0] + R * 1.15, c[1] + fs * 0.35, 'start'], [c[0] - R * 1.15, c[1] - R * 0.62, 'end'], [c[0] - R * 1.15, c[1] + R * 0.62 + fs * 0.7, 'end'],
      [c[0], c[1] - R * 1.1, 'middle'], [c[0], c[1] + R * 1.1 + fs * 0.7, 'middle'], [c[0] - R * 1.15, c[1] + fs * 0.35, 'end'],
      [c[0] - R * 1.3, c[1] - fs * 0.7, 'end'], [c[0] - R * 1.3, c[1] + fs * 1.3, 'end']];
    // then, left of the scene, every height from just above to just below it
    for (var dy = 0.2; dy <= 1.3; dy += 0.1) { cands.push([c[0] - R * 1.2, c[1] - R * dy + fs * 0.35, 'end'], [c[0] - R * 1.2, c[1] + R * dy + fs * 0.35, 'end']); }
    // only a place clear of every corridor and every other scene
    for (var pass = 0; pass < 1; pass++) {
      for (var k = 0; k < cands.length; k++) {
        var q = cands[k], x0 = q[2] === 'start' ? q[0] : q[2] === 'middle' ? q[0] - tw / 2 : q[0] - tw, x1 = x0 + tw, y0 = q[1] - fs * 0.85, y1 = q[1] + fs * 0.3, ok = true;
        if (x0 < m.hub[0] + 8 || x1 > W - 12 || y0 < 64 || y1 > H - 8) continue;
        m.rays.forEach(function (r, j) {
          if (!ok) return;
          if (!pass) {
            var L = dist(r.start, r.end), st = Math.max(2, Math.ceil(L / 6));
            for (var u = 0; u <= st && ok; u++) { var p = mix(r.start, r.end, u / st); if (p[0] > x0 - 12 && p[0] < x1 + 12 && p[1] > y0 - 12 && p[1] < y1 + 12) ok = false; }
          }
          if (j !== i) { var cx = clamp(r.c[0], x0 - 10, x1 + 10), cy = clamp(r.c[1], y0 - 10, y1 + 10); if (dist([cx, cy], r.c) < R * 1.1) ok = false; }
        });
        if (ok) return q;
      }
    }
    return null;
  }
  function heroLane(m, a, b, pal, w, on) { // on: how lit the corridor is, 0..1
    var c = colour(pal, 'ink'), dark = !!pal.glow, out;
    if (dark) out = grp(0.07, rawLine(a, b, c, w * 0.42)) + grp(0.09, rawLine(a, b, c, w * 0.16)) + grp(0.55, rawLine(a, b, c, 1.1 * pal.weight));
    else out = grp(0.1, rawLine(a, b, c, w * 0.3)) + grp(0.18, rawLine(a, b, c, w * 0.12)) + grp(0.62, rawLine(a, b, c, 1.1 * pal.weight));
    if (on > 0.01) out += S.path([a, b], pal, lit(pal), 1.8, { opacity: 0.9 * on });
    return out;
  }
  function motif(i, c, R, u, pal) {
    var x = c[0], y = c[1], on = easeOut(u), out = '', k, pts, wk = clamp(R / 70, 1, 1.8);
    if (u <= 0) return '';
    switch (i) {
      case 0: // a wandering trace, then a straight run to food
        pts = WANDER.map(function (p) { return [x + p[0] * R, y + p[1] * R]; });
        out += S.path(pts, pal, 'soft', 1.1 * wk, { opacity: 0.3 + 0.35 * on });
        var f = [x + R * 0.8, y - R * 0.76], a = pts[0], g = clamp((u - 0.35) / 0.55, 0, 1);
        out += S.dot(a[0], a[1], 2.6 * wk, pal, 'soft', 0.8);
        if (g > 0) out += S.path([a, mix(a, f, ease(g))], pal, lit(pal), 2 * wk);
        out += halo(f[0], f[1], 9 * wk, pal, 'peri', 0.14 * on) + S.dot(f[0], f[1], 3.6 * wk, pal, 'peri', 0.3 + 0.7 * on);
        break;
      case 1: // a route with a wall across it, and the way around
        out += S.line(x, y + R * 0.95, x, y - R * 0.85, pal, 'soft', 1.1 * wk, 0.7);
        out += S.line(x - R * 0.28, y - R * 0.05, x + R * 0.28, y - R * 0.05, pal, 'ink', 2.6 * wk);
        pts = cubic([x, y + R * 0.5], [x + R * 1.1, y + R * 0.42], [x + R * 1.1, y - R * 0.6], [x, y - R * 0.66], 30);
        out += S.path(pts, pal, 'soft', 1 * wk, { opacity: 0.35 });
        out += S.path(pts.slice(0, Math.max(2, Math.round(30 * on) + 1)), pal, lit(pal), 2 * wk);
        out += halo(x, y - R * 0.88, 9 * wk, pal, 'peri', 0.14 * on) + S.dot(x, y - R * 0.88, 3.6 * wk, pal, 'peri', 0.3 + 0.7 * on);
        break;
      case 2: // a fan of paths; the one aiming at the food lights
        var o = [x - R * 0.1, y + R * 0.62], angs = [-80, -60, -40, -20, 0, 20, 40, 60, 80];
        out += S.circle(o[0], o[1], R * 0.13, pal, 'soft', 1 * wk, 0.7);
        angs.forEach(function (d, j) {
          var e = [o[0] + Math.sin(d * DEG) * R * 1.0, o[1] - Math.cos(d * DEG) * R * 1.0], s0 = [o[0] + Math.sin(d * DEG) * R * 0.16, o[1] - Math.cos(d * DEG) * R * 0.16];
          var hot = j === 6;
          out += S.line(s0[0], s0[1], e[0], e[1], pal, hot ? lit(pal) : 'soft', hot ? (1.3 + 0.8 * on) * wk : 1 * wk, hot ? 0.4 + 0.6 * on : 0.5);
        });
        var fd = [o[0] + Math.sin(40 * DEG) * R * 1.32, o[1] - Math.cos(40 * DEG) * R * 1.32];
        out += halo(fd[0], fd[1], 9 * wk, pal, 'peri', 0.14 * on) + S.dot(fd[0], fd[1], 3.6 * wk, pal, 'peri', 0.3 + 0.7 * on);
        break;
      case 3: // tries per puzzle, fewer and fewer
        var counts = [6, 5, 4, 4, 3, 2, 2, 1, 1];
        counts.forEach(function (cnt, j) {
          if (u < j / counts.length) return;
          var cx = x - R * 0.95 + j * (1.9 * R / (counts.length - 1));
          for (k = 0; k < cnt; k++) {
            var yy = y + R * 0.8 - k * R * 0.28;
            out += S.line(cx - R * 0.075, yy, cx + R * 0.075, yy, pal, k === cnt - 1 ? lit(pal) : 'soft', 1.5 * wk, k === cnt - 1 ? 1 : 0.6);
          }
        });
        break;
      case 4: // four pieces fall into one line; the second lights
        var line = [], e2 = ease(u);
        for (k = 0; k < 4; k++) line.push(mix([x + SCATTER[k][0] * R, y + SCATTER[k][1] * R], [x - R * 0.9 + k * R * 0.6, y], e2));
        if (u > 0.75) out += S.path(line, pal, 'soft', 1 * wk, { opacity: (u - 0.75) * 4 * 0.7 });
        line.forEach(function (p, k2) { out += S.dot(p[0], p[1], (k2 === 1 ? 4.2 : 3) * wk, pal, k2 === 1 ? lit(pal) : 'ink', k2 === 1 ? 1 : 0.8); });
        break;
    }
    return grp(clamp(u * 3, 0, 1), out);
  }
  var heroPick = -1;
  var heroDef = {
    id: 'five', name: 'five-corridors', title: 'Five corridors, one for each experiment',
    caption: 'Five corridors leave the title, one for each experiment on this page.',
    modelFor: function (box) { heroM = LIVE.five = heroModel(box.width, box.height, heroGeo()); return heroM; },
    remeasure: true, // the corridors leave from beside the title, whose size is not the figure's box
    // the opening is whole from its first frame: every corridor and every scene is drawn
    initialState: function () { return { t: H_END + 1, sel: -1, la: 0, nm: 0 }; },
    stillState: function () { return { t: H_END + 1, sel: -1, la: 0, nm: 0 }; },
    tick: function (m, s) { return s; },
    // the corridors light in turn, one for each experiment, then all five rest
    sequence: (function () {
      var st = [{ dur: 500, tick: false }];
      PARTS.forEach(function (x, i) {
        st.push({ dur: 0, tick: false, 'do': function (m, s) { return { t: s.t, sel: i, la: 0, nm: 0 }; } });
        st.push({ dur: 380, tick: false, to: { la: 1 }, ease: 'out' });
        st.push({ dur: 900, tick: false });
        st.push({ dur: 320, tick: false, to: { la: 0 }, ease: 'in' });
      });
      st.push({ dur: 0, tick: false, 'do': function (m, s) { return { t: s.t, sel: -1, la: 0, nm: 0 }; } });
      st.push({ dur: 400, tick: false });
      return st;
    })(),
    settled: function (m, s) { return s.t >= H_END; },
    draw: function (m, s, pal) {
      // one part per corridor: a corridor that has finished growing is not written again
      var front = {}, labels = '', t = s.t, w = m.narrow ? 16 : 24, la = s.la == null ? 1 : s.la;
      m.rays.forEach(function (r, i) {
        var t0 = H_T0 + i * H_GAP, g = easeOut((t - t0) / H_GROW), part = '';
        front['r' + i] = '';
        if (g <= 0) return;
        var p = mix(r.start, r.end, g);
        part += heroLane(m, r.start, p, pal, w, s.sel === i ? la : 0);
        if (g < 1) part += ratDot(p, m.narrow ? 2.8 : 3.6, pal);
        else part += S.dot(r.end[0], r.end[1], 2.6, pal, 'ink', 0.85);
        var u = clamp((t - t0 - H_GROW) / H_LIT, 0, 1);
        part += motif(i, r.c, m.R, u, pal);
        front['r' + i] = part;
        if (s.nm && s.sel === i && u > 0) {
          // the scene's name, only while it is pointed at or chosen with the keys: beside it, where it
          // crosses no corridor and no other scene (where there is no such place, it is not written)
          var fs = m.fs, tw = LINES[i].length * fs * 0.5, lp = heroLabelAt(m, i, tw, fs);
          if (lp) labels += label(lp[0], lp[1], LINES[i], pal, 'ink', fs, lp[2], 1);
        }
      });
      front.hub = !m.narrow && t > H_T0 - 0.4 ? grp(clamp((t - H_T0 + 0.4) / 0.4, 0, 1), placeMark(m.hub, 7, pal)) : '';
      return { back: '', front: front, labels: clear(labels, pal, 6) };
    },
    describe: function (m, s) {
      var d = 'Five corridors leave the title, one for each experiment on this page. At their ends: a wandering trail that becomes a straight run to food; ' +
        'a route with a wall across it and a path around the wall; a fan of paths with one pointing at food; marks that get fewer from puzzle to puzzle; ' +
        'four points that fall into one line.';
      if (s.sel >= 0 && s.nm) d += ' Chosen: ' + LINES[s.sel] + ' Press Enter to go to it.';
      return d;
    },
    controls: [],
    drag: {
      pick: function (m, s, p) {
        heroPick = -1;
        m.rays.forEach(function (r, i) { if (dist(p, r.c) < m.R * 1.3) heroPick = i; });
        return heroPick >= 0;
      },
      move: function (m, s) { return s; },
      end: function (m, s) {
        if (heroPick < 0) return s;
        var i = heroPick; heroPick = -1;
        setTimeout(function () { scrollToPart(PARTS[i]); }, 0);
        return { t: Math.max(s.t, H_END), sel: i, la: 1, nm: 1 };
      }
    },
    keys: {
      ArrowRight: function (m, s) { return { t: Math.max(s.t, H_END), sel: (s.sel + 1) % 5, la: 1, nm: 1 }; },
      ArrowDown: function (m, s) { return { t: Math.max(s.t, H_END), sel: (s.sel + 1) % 5, la: 1, nm: 1 }; },
      ArrowLeft: function (m, s) { return { t: Math.max(s.t, H_END), sel: s.sel <= 0 ? 4 : s.sel - 1, la: 1, nm: 1 }; },
      ArrowUp: function (m, s) { return { t: Math.max(s.t, H_END), sel: s.sel <= 0 ? 4 : s.sel - 1, la: 1, nm: 1 }; },
      Enter: function (m, s) { var i = s.sel < 0 ? 0 : s.sel; setTimeout(function () { scrollToPart(PARTS[i]); }, 0); return { t: Math.max(s.t, H_END), sel: i, la: 1, nm: 1 }; }
    },
    keysLabel: 'Arrow keys choose a corridor; Enter goes to its experiment.',
    handle: function (m, s) { return m.rays[s.sel >= 0 ? s.sel : 0].c; }
  };
  heroDef.model = heroModel(1600, 900, null);
  var heroH = P.figure(heroDef);
  // pointing at a scene names it; leaving clears the name
  (function () {
    var art = document.querySelector('.x-open > .k-art');
    if (!art) return;
    function at(e) {
      var svg = art.querySelector('svg.k-layer-front'); if (!svg || !heroM || !svg.getScreenCTM) return -1;
      var pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
      var ctm = svg.getScreenCTM(); if (!ctm) return -1;
      var p = pt.matrixTransform(ctm.inverse()), hit = -1;
      heroM.rays.forEach(function (r, i) { if (dist([p.x, p.y], r.c) < heroM.R * 1.3) hit = i; });
      return hit;
    }
    // pointing names a scene; it is not acting, so it never stops the sequence (and waits while it plays)
    art.addEventListener('pointermove', function (e) {
      if (e.pointerType === 'touch' || !heroH.mounted) return;
      var i = at(e), s = heroH.state; if (!s) return;
      art.style.cursor = i >= 0 ? 'pointer' : 'default';
      if (seqPlaying(heroH)) return;
      if (i !== s.sel || (i >= 0) !== !!s.nm) heroH.set({ t: s.t, sel: i, la: i >= 0 ? 1 : 0, nm: i >= 0 ? 1 : 0 }, { quiet: true });
    });
    art.addEventListener('pointerleave', function () {
      art.style.cursor = '';
      if (!heroH.mounted || seqPlaying(heroH)) return;
      var s = heroH.state;
      if (s && s.sel >= 0 && document.activeElement !== art) heroH.set({ t: s.t, sel: -1, la: 0, nm: 0 }, { quiet: true });
    });
  })();

  /* ===== 2. Latent learning: the maze with no food ================================== */
  var MAIN = [[0, 0], [1, 0], [2, 0], [2, 1], [2, 2], [1, 2], [1, 3], [1, 4], [2, 4], [3, 4], [3, 3], [4, 3], [5, 3], [5, 2], [5, 1], [6, 1], [7, 1], [7, 2], [7, 3], [7, 4], [6, 4], [6, 5], [7, 5], [8, 5]];
  var MAZE = (function () {
    var C = 9, R = 6, used = {}, adj = {}, edges = [], xy = {};
    function k(p) { return p[0] + ',' + p[1]; }
    function add(a, b) { var ka = k(a), kb = k(b); (adj[ka] = adj[ka] || []).push(kb); (adj[kb] = adj[kb] || []).push(ka); edges.push([ka, kb]); }
    MAIN.forEach(function (p, i) { used[k(p)] = 1; xy[k(p)] = p; if (i) add(MAIN[i - 1], p); });
    var D = [[1, 0], [-1, 0], [0, 1], [0, -1]], rng = P.mulberry(31), nodes = MAIN.slice(1, -1), tips = [];
    function free(q, from) {
      if (q[0] < 0 || q[0] >= C || q[1] < 0 || q[1] >= R || used[k(q)]) return false;
      for (var d = 0; d < 4; d++) { var nb = [q[0] + D[d][0], q[1] + D[d][1]]; if (nb[0] === from[0] && nb[1] === from[1]) continue; if (used[k(nb)]) return false; }
      return true;
    }
    for (var tries = 0; tries < 900 && tips.length < 12; tries++) {
      var base = nodes[Math.floor(rng() * nodes.length)], dd = D[Math.floor(rng() * 4)], q = [base[0] + dd[0], base[1] + dd[1]];
      if (!free(q, base)) continue;
      used[k(q)] = 1; xy[k(q)] = q; add(base, q); var cur = q, len = Math.floor(rng() * 3);
      for (var j = 0; j < len; j++) {
        var opts = D.map(function (e) { return [cur[0] + e[0], cur[1] + e[1]]; }).filter(function (z) { return free(z, cur); });
        if (!opts.length) break;
        var nx = opts[Math.floor(rng() * opts.length)]; used[k(nx)] = 1; xy[k(nx)] = nx; add(cur, nx); cur = nx;
      }
      tips.push(k(cur)); nodes.push(cur);
    }
    var goal = k(MAIN[MAIN.length - 1]);
    var targets = [goal].concat(tips.filter(function (t) { return adj[t].length === 1 && t !== goal; }));
    return { C: C, R: R, adj: adj, edges: edges, xy: xy, start: k(MAIN[0]), goal: goal, targets: targets };
  })();
  function ekey(a, b) { return a < b ? a + '|' + b : b + '|' + a; }
  function latModel(box) {
    if (box.width < 640) {
      var px = narrowPx(600, box);
      return { key: 'lat:n' + px, view: { w: 600, h: 560 }, pr: perspFit(300, 505, 95, 0.8, 0.95, 690), gx: 0.105, gz: 0.16, px: px, fs: 14 * px, sz: 0.62, narrow: true };
    }
    var wh = boxWH(box), W = wh[0], H = wh[1];
    var sc = Math.min(W * 0.94 / 0.84, (H - 70) * 2.6);
    return { key: 'lat:' + W + 'x' + H, view: { w: W, h: H }, pr: perspFit(W / 2, H - 40, Math.max(22, H * 0.05), 0.8, 0.95, sc),
      gx: 0.105, gz: 0.16, px: 1, fs: 15, sz: clamp(sc / 1250, 0.8, 1.2), narrow: false };
  }
  function lw(m, key) { var p = MAZE.xy[key]; return [(p[0] - (MAZE.C - 1) / 2) * m.gx, p[1] * m.gz]; }
  function lwPt(m, g) { return [(g[0] - (MAZE.C - 1) / 2) * m.gx, g[1] * m.gz]; }
  function lScreen(m, key) { var w = lw(m, key), q = m.pr(w[0], w[1]); return [q[0], q[1], q[2]]; }
  function latPos(s) { var a = MAZE.xy[s.a], b = MAZE.xy[s.b]; return mix(a, b, s.u); }
  function bfsFrom(target) {
    var d = {}, next = {}, q = [target]; d[target] = 0;
    while (q.length) { var x = q.shift(); MAZE.adj[x].forEach(function (y) { if (d[y] == null) { d[y] = d[x] + 1; next[y] = x; q.push(y); } }); }
    return { d: d, next: next };
  }
  function covered(s) { return Object.keys(s.vis).length >= MAZE.edges.length; }
  function latRunTo(m, s, f) {
    // as in the experiment, the rat is set down in the start box and runs from there
    var b = bfsFrom(f), rt = [], cur = MAZE.start;
    while (cur) { rt.push(MAZE.xy[cur].slice()); if (cur === f) break; cur = b.next[cur]; }
    return { ph: 'run', t: s.t, k: s.k, a: MAZE.start, b: MAZE.start, u: 0, seed: s.seed, vis: s.vis, trail: s.trail, food: f, cand: f, fa: 1, rt: rt, rlen: polyLen(rt), rd: 0, stop: false };
  }
  // the wander is a fixed number of corridors (not a time), so the sequence and the still end on the same walked corridors
  var LAT_N = 20, LAT_SPEED = 2.9, LAT_RUN = 6.5;
  function latWanderDone(s) { for (var i = 0; i < 4000 && s.ph === 'wander'; i++) s = latDef.tick(null, s, 0.05); return s; }
  var latPicked = null;
  var LAT_RUNLEN = (function () { var b = bfsFrom(MAZE.goal), L = 0, cur = MAZE.start; while (cur && cur !== MAZE.goal) { L += 1; cur = b.next[cur]; } return L; })();
  var latDef = {
    id: 'latent', name: 'latent-learning-maze', title: 'A rat wanders a maze with no food in it',
    caption: "A rat explores a maze with no food in it.",
    modelFor: live('latent', latModel),
    initialState: function () { return { ph: 'wander', t: 0, k: 0, a: MAZE.start, b: MAZE.adj[MAZE.start][0], u: 0, seed: 7, vis: {}, trail: [], food: null, cand: null, fa: 1, rt: null, rlen: 0, rd: 0, stop: false }; },
    // the last picture of the sequence: the walked corridors faintly lit, the food at the end, the run to it lit
    stillState: function (m) {
      var s = latWanderDone(latDef.initialState(m));
      s = latRunTo(m, s, MAZE.goal); s.rd = s.rlen; s.ph = 'fed'; s.trail = [];
      return s;
    },
    tick: function (m, s, dt) {
      s = Object.assign({}, s); s.t += dt;
      if (s.ph === 'wander') {
        s.u += dt * LAT_SPEED;
        while (s.u >= 1) {
          s.u -= 1;
          var ek = ekey(s.a, s.b); s.vis = Object.assign({}, s.vis); s.vis[ek] = (s.vis[ek] || 0) + 1;
          s.trail = s.trail.concat([s.a]).slice(-14); s.k = (s.k || 0) + 1;
          if (s.k >= LAT_N || covered(s)) { s.ph = 'wait'; s.a = s.b; s.u = 0; break; }
          var from = s.a, at = s.b;
          var nb = MAZE.adj[at].filter(function (x) { return x !== from; });
          if (!nb.length) nb = [from];
          var unv = nb.filter(function (x) { return !s.vis[ekey(at, x)]; });
          var pool = (unv.length && srand(s) < 0.72) ? unv : nb;
          s.a = at; s.b = pool[Math.floor(srand(s) * pool.length)];
        }
      } else if (s.ph === 'run') {
        s.rd = Math.min(s.rlen, s.rd + dt * LAT_RUN);
        if (s.rd >= s.rlen) s.ph = 'fed';
      }
      return s;
    },
    settled: function (m, s) { return s.ph === 'wait' || s.ph === 'fed'; },
    draw: function (m, s, pal) {
      var back = '', front = {}, labels = '', pr = m.pr, sz = m.sz;
      back += lanes(MAZE.edges.map(function (e) { return [lw(m, e[0]), lw(m, e[1])]; }), pr, pal, { w: 30 * sz, band: 0.075, core: 0.42 });
      var ps = lScreen(m, MAZE.start), pg = lScreen(m, MAZE.goal);
      back += placeMark(ps, 8 * sz * m.px, pal) + placeMark(pg, 6 * sz * m.px, pal);
      labels += label(ps[0], ps[1] + 30 * m.px, 'start', pal, 'soft', m.fs, 'middle');
      labels += label(pg[0], pg[1] - 16 * m.px, 'end', pal, 'soft', m.fs, 'middle');
      // the front in parts: the walked corridors change only when a corridor is finished, the food only
      // when it is put down; the trail, the run and the rat change every frame
      var lit1 = '';
      Object.keys(s.vis).forEach(function (ek) {
        var e = ek.split('|'), v = s.vis[ek], a = lw(m, e[0]), b = lw(m, e[1]);
        lit1 += grp(Math.min(0.75, 0.3 + 0.15 * v), route([a, b], pr, pal, 'peri', 1.4));
      });
      front.walked = lit1;
      var pos = s.ph === 'run' || s.ph === 'fed' ? polyAt(s.rt, s.rd) : latPos(s);
      front.trail = '';
      if (s.ph === 'wander' && s.trail.length) {
        var tr = s.trail.map(function (key) { return lwPt(m, MAZE.xy[key]); }).concat([lwPt(m, pos)]);
        front.trail = route(tr, pr, pal, 'mint', 1.5, 0.45);
      }
      front.run = s.rt ? route(polyCut(s.rt, 0, s.rd).map(function (g) { return lwPt(m, g); }), pr, pal, lit(pal), 2.6, 0.95) : '';
      front.food = '';
      if (s.food && s.fa > 0.01) { var fp = lScreen(m, s.food); front.food = foodMark(fp, 5 * fp[2] * sz + 1.5, pal, s.fa == null ? 1 : s.fa); }
      if (s.cand && s.cand !== s.food) {
        // the spot chosen by pointing or by the arrow keys, and what choosing it does
        var cp = lScreen(m, s.cand), cr = 11 * sz * m.px, right = cp[0] < m.view.w * 0.72;
        front.food += S.circle(cp[0], cp[1], cr, pal, 'peri', 1.2, 0.8);
        labels += label(cp[0] + (right ? 1 : -1) * (cr + 8 * m.px), cp[1] + m.fs * 0.35, 'Put food here', pal, 'ink', m.fs, right ? 'start' : 'end');
      }
      var rp = lwPt(m, pos), rq = pr(rp[0], rp[1]);
      front.rat = ratDot(rq, (5.2 * rq[2] + 1.2) * sz, pal);
      return { back: back, front: front, labels: clear(labels, pal, 5) };
    },
    describe: function (m, s) {
      if (s.ph === 'wander') return 'A rat wanders a maze of corridors with no food in it. The corridors it has walked are faintly lit.';
      if (s.ph === 'wait') return 'The rat has wandered the maze with no food in it, and nothing seems to happen.';
      if (s.ph === 'run') return 'Food is put at the end of the maze. The rat is set down at the start and runs straight to it.';
      return 'The rat ran straight to the food' + (s.food === MAZE.goal ? ' at the end of the maze' : '') + ', by the shortest way. The rat\'s run is lit.';
    },
    // the rat wanders with no food; nothing seems to happen; food is put at the end; the rat is set
    // down at the start and runs straight there
    sequence: [
      { dur: Math.ceil(LAT_N / LAT_SPEED * 1000) + 500 },
      { dur: 0, 'do': function (m, s) { return latWanderDone(s); } },
      { dur: 1200 },
      { dur: 0, tick: false, 'do': function (m, s) { var r = latRunTo(m, s, MAZE.goal); r.fa = 0; return r; } },
      { dur: 650, tick: false, to: { fa: 1 }, ease: 'out' },
      { dur: 750, tick: false },
      { dur: 0, 'do': function (m, s) { return s; } },
      { dur: Math.ceil(LAT_RUNLEN / LAT_RUN * 1000) + 200 },
      { dur: 1300 }
    ],
    controls: [],
    drag: {
      pick: function (m, s, p) {
        var best = null, bd = 1e9;
        Object.keys(MAZE.xy).forEach(function (key) { var q = lScreen(m, key), d = dist(p, q); if (d < bd) { bd = d; best = key; } });
        latPicked = bd < 70 * m.px ? best : null;
        return !!latPicked;
      },
      move: function (m, s, p) {
        var best = null, bd = 1e9;
        Object.keys(MAZE.xy).forEach(function (key) { var q = lScreen(m, key), d = dist(p, q); if (d < bd) { bd = d; best = key; } });
        latPicked = best; var c = Object.assign({}, s); c.cand = best; return c;
      },
      end: function (m, s) {
        if (!latPicked) return s;
        var f = latPicked; latPicked = null;
        return act(latDef, latH, m, latRunTo(m, s, f));
      }
    },
    keys: {
      ArrowRight: function (m, s) { var i = MAZE.targets.indexOf(s.cand), c = Object.assign({}, s); c.cand = MAZE.targets[(i + 1) % MAZE.targets.length]; if (c.ph === 'wander') c.ph = 'wait'; return c; },
      ArrowLeft: function (m, s) { var i = MAZE.targets.indexOf(s.cand), c = Object.assign({}, s); c.cand = MAZE.targets[i <= 0 ? MAZE.targets.length - 1 : i - 1]; if (c.ph === 'wander') c.ph = 'wait'; return c; },
      Enter: function (m, s) { return act(latDef, latH, m, latRunTo(m, s, s.cand || MAZE.goal)); }
    },
    keysLabel: 'Left and right arrow keys choose a spot in the maze; Enter puts the food there.',
    handle: function (m, s) { if (s.cand && !s.food) return lScreen(m, s.cand); var p = s.rt ? polyAt(s.rt, s.rd) : latPos(s), w = lwPt(m, p), q = m.pr(w[0], w[1]); return [q[0], q[1]]; }
  };
  latDef.model = latModel({ width: 1376, height: 640 });
  var latH = P.figure(latDef);
  // pointing at a spot in the maze (while the rat is not moving) rings it and says what a click does
  function nearestSpot(m, p) {
    var best = null, bd = 1e9;
    Object.keys(MAZE.xy).forEach(function (key) { var q = lScreen(m, key), d = dist(p, q); if (d < bd) { bd = d; best = key; } });
    return bd < 70 * m.px ? best : null;
  }
  hoverFigure('latent', latH, function (m, s, p) {
    if (s.ph === 'run') return null;
    var c = p ? nearestSpot(m, p) : null;
    if (c === s.cand) return null;
    var n2 = Object.assign({}, s); n2.cand = c; return n2;
  });

  /* ===== 3. Detour: three routes and a wall ==================================== */
  var DT = (function () {
    var S0 = [0, 0], C = [0, 0.12], J = [0, 0.55], F = [0, 0.98];
    var p2 = roundPoly([C, [-0.34, 0.12], [-0.34, 0.55], J], 0.07);
    var p3 = roundPoly([C, [0.6, 0.12], [0.6, 0.98], F], 0.09);
    return { S0: S0, C: C, J: J, F: F, p2: p2, p3: p3, jf: (J[1] - C[1]) / (F[1] - C[1]) };
  })();
  function dtModel(box) {
    if (box.width < 640) {
      var px = narrowPx(600, box);
      return { key: 'dt:n' + px, view: { w: 600, h: 600 }, pr: perspFit(300, 545, 80, 0.98, 0.7, 520), px: px, fs: 14 * px, sz: 0.7, narrow: true };
    }
    var wh = boxWH(box), W = wh[0], H = wh[1];
    var sc = Math.min(W * 0.92 / 0.94, (H - 90) * 1.7);
    return { key: 'dt:' + W + 'x' + H, view: { w: W, h: H }, pr: perspFit(W / 2 - 0.13 * sc * 0.8, H - 46, 48, 0.98, 0.7, sc), px: 1, fs: 15, sz: clamp(sc / 820, 0.85, 1.25), narrow: false };
  }
  function dtBlockPt(b) { return [0, DT.C[1] + b * (DT.F[1] - DT.C[1])]; }
  function dtPlan(b) {
    if (b == null) return [{ pts: [DT.S0, DT.C, DT.J, DT.F], tag: 'go' }];
    var stop = dtBlockPt(b - 0.035);
    var around = b < DT.jf ? DT.p2.concat([DT.F]) : DT.p3;
    return [{ pts: [DT.S0, DT.C, stop], tag: 'try' }, { pts: [stop, DT.C], tag: 'back' }, { pts: around, tag: 'go' }];
  }
  function dtRun(block, mode) {
    var plan = dtPlan(block), offs = [], L = 0;
    plan.forEach(function (p) { offs.push(L); p.len = polyLen(p.pts); L += p.len; });
    return { mode: mode || 'run', lap: 0, d: 0, hold: 0, held: false, block: block, wa: 1, plan: plan, offs: offs, L: L };
  }
  function dtPos(s) {
    for (var i = s.plan.length - 1; i >= 0; i--) if (s.d >= s.offs[i]) return polyAt(s.plan[i].pts, s.d - s.offs[i]);
    return DT.S0.slice();
  }
  // a point on the straight route, where the wall can be dragged
  function dtOnRoute(m, p) {
    var a = m.pr(0, DT.C[1]), b = m.pr(0, DT.F[1]);
    return Math.abs(p[0] - a[0]) < 34 * m.px && p[1] <= a[1] + 10 && p[1] >= b[1] - 10;
  }
  function dtSnapB(b) { b = clamp(b, 0.07, 0.93); if (Math.abs(b - DT.jf) < 0.05) b = b < DT.jf ? DT.jf - 0.05 : DT.jf + 0.05; return b; }
  // how long the two taught runs and the run around the wall take (world units, the same for every model)
  var DT_BLOCK = 0.78, DT_SPEED = 0.62, DT_TRAIN = 2 * dtRun(null, 'train').L / DT_SPEED + 0.45, DT_RUN = dtRun(DT_BLOCK, 'run').L / DT_SPEED + 0.55;
  var dtDef = {
    id: 'detour', name: 'detour-three-routes', title: 'Three routes to the same food, and a wall',
    caption: "Three routes of different lengths lead to the same food.",
    modelFor: live('detour', dtModel),
    initialState: function () { return dtRun(null, 'train'); },
    stillState: function () { var s = dtRun(DT_BLOCK, 'run'); s.d = s.L; s.mode = 'done'; s.held = true; return s; },
    tick: function (m, s, dt) {
      s = Object.assign({}, s);
      if (s.hold > 0) { s.hold -= dt; return s; }
      var before = s.d; s.d = Math.min(s.L, s.d + dt * DT_SPEED);
      if (s.plan.length > 1 && !s.held && before < s.offs[1] && s.d >= s.offs[1]) { s.d = s.offs[1]; s.hold = 0.55; s.held = true; }
      if (s.d >= s.L) {
        if (s.mode === 'train' && s.lap < 1) { s.lap += 1; s.d = 0; s.hold = 0.45; }
        else s.mode = 'done';
      }
      return s;
    },
    settled: function (m, s) { return s.mode === 'done' || s.mode === 'ready'; },
    draw: function (m, s, pal) {
      var back = '', front = {}, labels = '', pr = m.pr, sz = m.sz, path = '';
      back += lanes([[DT.S0, DT.C, DT.J, DT.F], DT.p2, DT.p3], pr, pal, { w: 34 * sz, band: 0.08, core: 0.45 });
      var p0 = pr(0, 0), pf = pr(DT.F[0], DT.F[1]);
      back += placeMark(p0, 9 * sz * m.px, pal);
      labels += label(p0[0], p0[1] + 32 * m.px, 'start', pal, 'soft', m.fs, 'middle');
      labels += label(pf[0], pf[1] - 22 * m.px, 'food', pal, 'soft', m.fs, 'middle');
      back += foodMark(pf, 4.4 * sz + 1, pal);
      // where it has gone so far
      s.plan.forEach(function (pc, i) {
        var done = clamp(s.d - s.offs[i], 0, pc.len);
        if (done <= 0) return;
        var pts = polyCut(pc.pts, 0, done);
        if (pc.tag === 'go') path += route(pts, pr, pal, lit(pal), 2.6, 0.95);
        else path += grp(0.75, dpath(densify(pts, 0.04).map(function (p) { var q = pr(p[0], p[1]); return [q[0], q[1]]; }), pal, 'soft', 1.6, '3 6', 1));
      });
      front.path = path;
      front.wall = '';
      if (s.block != null && s.wa > 0.01) { var bp = dtBlockPt(s.block); front.wall = wall(pr, -0.055, 0.055, bp[1], 40 * sz, pal, s.wa == null ? 1 : s.wa); }
      var rp = s.mode === 'ready' ? DT.S0 : dtPos(s), rq = pr(rp[0], rp[1]);
      front.rat = ratDot(rq, (5 * rq[2] + 1.4) * sz, pal);
      return { back: back, front: front, labels: clear(labels, pal, 5) };
    },
    describe: function (m, s) {
      var where = s.block == null ? '' : (s.block < DT.jf ? ' The wall stands on the straight route, before the middle route joins it.' : ' The wall stands on the last stretch of the straight route, which the middle route shares.');
      if (s.block == null) return 'Three routes lead from the start to the food: straight, a middle loop, and a long loop. The rat knows the way and takes the straight route.' + (s.mode === 'done' ? '' : ' It is running now.');
      if (s.mode === 'ready') return 'A wall now stands on the rat\'s usual route. The rat waits at the start.' + where;
      if (s.mode !== 'done') return 'The rat runs its usual straight route.' + where;
      return 'The rat met the wall on its usual route, went back to the fork, and took the ' + (s.block < DT.jf ? 'middle' : 'long') + ' route, the one that gets around the wall.' + where;
    },
    // the rat runs its usual straight route twice; a wall appears on it; the rat meets the wall, goes
    // back to the fork and takes the long route around it
    sequence: [
      { dur: Math.ceil(DT_TRAIN * 1000) + 250 },
      { dur: 0, tick: false, 'do': function (m, s) { var r = dtRun(DT_BLOCK, 'ready'); r.wa = 0; return r; } },
      { dur: 700, tick: false, to: { wa: 1 }, ease: 'out' },
      { dur: 900, tick: false },
      { dur: 0, tick: false, 'do': function (m, s) { var r = dtRun(DT_BLOCK, 'run'); return r; } },
      { dur: Math.ceil(DT_RUN * 1000) + 200 },
      { dur: 1300 }
    ],
    controls: [],
    drag: {
      pick: function (m, s, p) { return dtOnRoute(m, p); },
      move: function (m, s, p) {
        var z = m.pr.zAt(p[1]), b = dtSnapB((z - DT.C[1]) / (DT.F[1] - DT.C[1]));
        return dtRun(b, 'ready');
      },
      end: function (m, s) { if (s.block == null) return s; return act(dtDef, dtH, m, dtRun(s.block, 'run')); }
    },
    keys: {
      ArrowUp: function (m, s) { return dtRun(dtSnapB(s.block == null ? DT_BLOCK : s.block + 0.07), 'ready'); },
      ArrowDown: function (m, s) { return dtRun(dtSnapB(s.block == null ? DT_BLOCK : s.block - 0.07), 'ready'); },
      Enter: function (m, s) { return act(dtDef, dtH, m, dtRun(s.block, s.block == null ? 'train' : 'run')); }
    },
    keysLabel: 'Up and down arrow keys move the wall along the straight route; Enter lets the rat run.',
    handle: function (m, s) { if (s.block == null) { var q = m.pr(0, 0); return [q[0], q[1]]; } var bp = dtBlockPt(s.block), r = m.pr(0, bp[1]); return [r[0], r[1] - 14]; }
  };
  dtDef.model = dtModel({ width: 900, height: 700 });
  var dtH = P.figure(dtDef);
  // over the straight route the pointer shows that the wall can be moved up and down it
  hoverFigure('detour', dtH, function () { return null; }, function (m, s, p) { return dtOnRoute(m, p) ? 'ns-resize' : ''; });

  /* ===== 4. The sunburst: a fan of new paths ========================================== */
  // World units on the floor: X across, Z away from the reader; the round start is at the origin.
  var SB = (function () {
    var trainR = [[0, 0.075], [0, 0.5], [-0.2, 0.5], [-0.2, 0.7], [0.62, 0.7], [0.62, 0.5]], G = [0.62, 0.47];
    var arms = [], r0 = 0.085, La = 0.4, target = -1, best = 1e9, aim = Math.atan2(G[0], G[1]) / DEG;
    // the fan: paths every ten degrees around the start, leaving the straight-ahead gap to the closed route
    for (var a = -80; a <= 80; a += 10) {
      if (a === 0) continue;
      var v = [Math.sin(a * DEG), Math.cos(a * DEG)];
      arms.push({ a: a, v: v, p0: [v[0] * r0, v[1] * r0], p1: [v[0] * La, v[1] * La] });
      if (Math.abs(a - aim) < best) { best = Math.abs(a - aim); target = arms.length - 1; }
    }
    return { trainR: trainR, G: G, arms: arms, target: target, N: 64, La: La, r0: r0, sp: 0.0172, cap: 17 };
  })();
  // how many points take each path: the one aimed at the food gets more than any other single path,
  // never a majority; the rest spread over every other path
  function sbCounts(seed) {
    var rng = P.mulberry(seed * 7919 + 3), A = SB.arms.length;
    for (var tries = 0; tries < 400; tries++) {
      var c = SB.arms.map(function () { return 0; });
      for (var j = 0; j < SB.N; j++) {
        var u = rng(), w = [], tot = 0;
        SB.arms.forEach(function (a, i) { var d = Math.abs(i - SB.target), x = d === 0 ? 0.23 : d === 1 ? 0.08 : 0.045; w.push(x); tot += x; });
        var acc = 0; for (var i = 0; i < A; i++) { acc += w[i] / tot; if (u <= acc) { c[i]++; break; } }
      }
      var mx = 0, empty = 0; c.forEach(function (x, i) { if (i !== SB.target) mx = Math.max(mx, x); if (!x) empty++; });
      if (c[SB.target] > mx + 2 && c[SB.target] < SB.N / 2 && c[SB.target] <= SB.cap && empty <= 1) return c;
    }
    return SB.arms.map(function (a, i) { return i === SB.target ? 14 : 3; });
  }
  function sbRats(seed) { // which path each point takes, in the order they leave, and its place on that path
    var c = sbCounts(seed), list = [], rng = P.mulberry(seed * 31 + 9), slot = SB.arms.map(function () { return 0; });
    c.forEach(function (k, i) { for (var j = 0; j < k; j++) list.push(i); });
    for (var i = list.length - 1; i > 0; i--) { var j = Math.floor(rng() * (i + 1)), t = list[i]; list[i] = list[j]; list[j] = t; }
    return list.map(function (arm) { return { arm: arm, k: slot[arm]++, side: (rng() - 0.5) }; });
  }
  var SB_SPEED = 0.75, SB_LAP = polyLen(SB.trainR) / SB_SPEED, SB_TRAIN = SB_LAP * 2 + 0.5, SB_OPEN = 1.8, SB_GAP = 0.06, SB_RUN = 1.15;
  var SB_REL = SB.N * SB_GAP + SB_RUN + 0.6;
  // fit the floor to the box: the near edge low, the far edge high, as wide as the box allows
  function sbFit(W, H, mb, mt, mx) {
    var k = 0.55, zF = 0.74, pr0 = perspFit(0, H - mb, mt, zF, k, 1), lo = 1e9, hi = -1e9;
    var pts = SB.trainR.concat([SB.G]);
    SB.arms.forEach(function (a) { pts.push(a.p1); });
    for (var i = 0; i < 24; i++) pts.push([Math.cos(i / 24 * TAU) * 0.09, Math.sin(i / 24 * TAU) * 0.09]);
    pts.forEach(function (p) { var q = pr0(p[0], p[1]); lo = Math.min(lo, q[0]); hi = Math.max(hi, q[0]); });
    var sc = (W - 2 * mx) / (hi - lo), avail = H - mb - mt, span = Math.min(avail, sc * zF * 1.12);
    if (span < sc * zF * 1.12) sc = Math.min(sc, span / (zF * 0.9));
    var yF = mt + (avail - span) / 2;
    return perspFit(W / 2 - sc * (lo + hi) / 2, yF + span, yF, zF, k, sc);
  }
  function sbModel(box) {
    if (box.width < 640) {
      var px = narrowPx(600, box), prn = sbFit(600, 600, 58 * px, 30 * px, 14 * px);
      return { key: 'sb:n' + px, view: { w: 600, h: 600 }, pr: prn, px: px, fs: 14 * px, sz: clamp(prn.o.sc / 1000, 0.6, 1.4) * 1.25, narrow: true };
    }
    var wh = boxWH(box), W = wh[0], H = wh[1], pr = sbFit(W, H, 56, 30, 30);
    return { key: 'sb:' + W + 'x' + H, view: { w: W, h: H }, pr: pr, px: 1, fs: 15, sz: clamp(pr.o.sc / 1000, 0.8, 1.35), narrow: false };
  }
  function sbState(ph, t, seed) { return { ph: ph, t: t, seed: seed || 0, rats: sbRats(seed || 0) }; }
  function sbSlot(r) { return SB.La - 0.014 - r.k * SB.sp; }
  // mark the first element of a piece of SVG text, so update() can find it again
  function tagged(svg, name) { return svg.replace(/^<(\w+) /, '<$1 data-x="' + name + '" '); }
  // Everything that does not change while the figure plays, made once per model and palette: the
  // corridors, the fan, the wall, the food, the labels, and the trained route as screen points.
  function sbC(m, pal) {
    m._c = m._c || [];
    for (var i = 0; i < m._c.length; i++) if (m._c[i].pal === pal) return m._c[i];
    var pr = m.pr, sz = m.sz, px = m.px, C = { pal: pal };
    var p0 = pr(0, 0), rx = pr(SB.r0 * 0.9, 0)[0] - p0[0], ry = rx * 0.55, ring = [];
    // the round start, drawn flat on the screen (the floor's near half would swell it into an egg)
    for (var ri = 0; ri <= 48; ri++) { var ra = ri / 48 * TAU; ring.push([p0[0] + Math.cos(ra) * rx, p0[1] + Math.sin(ra) * ry]); }
    C.ring = S.path(ring, pal, 'soft', 1.3 * px, { opacity: 0.8 });
    var pg = pr(SB.G[0], SB.G[1]);
    C.food = foodMark(pg, (5 * pg[2] + 1.6) * sz, pal);
    var labels = label(p0[0], Math.min(m.view.h - 6 * px, p0[1] + ry + 24 * px), 'start', pal, 'soft', m.fs, 'middle');
    if (pg[0] + 18 * px + m.fs * 2.4 < m.view.w) labels += label(pg[0] + 18 * px, pg[1] + m.fs * 0.35, 'food', pal, 'soft', m.fs, 'start');
    else labels += label(pg[0], pg[1] - 20 * px, 'food', pal, 'soft', m.fs, 'middle');
    C.labels = clear(labels, pal, 5);
    var armSegs = SB.arms.map(function (a) { return [a.p0, a.p1]; });
    C.trainLit = lanes([SB.trainR], pr, pal, { w: 30 * sz, band: 0.08, core: 0.55 });
    C.trainDash = lanes([SB.trainR], pr, pal, { w: 30 * sz, band: 0, core: 0.32, dash: '2 7' });
    C.fanDots = lanes(armSegs, pr, pal, { w: 20 * sz, band: 0, core: 0.4, dash: '1.5 7' });
    C.wall = wall(pr, -0.04, 0.04, 0.105, 18 * sz, pal);
    C.arms = lanes(armSegs, pr, pal, { w: 22 * sz, band: 0.08, core: 0.6 });
    // the food's direction, straight from the start
    C.dir = dpath(densify([[0, 0], SB.G], 0.02).map(function (p) { var q = pr(p[0], p[1]); return [q[0], q[1]]; }), pal, 'peri', 1.3 * px, '2 7', 1);
    C.hot = route([SB.arms[SB.target].p0, SB.arms[SB.target].p1], pr, pal, lit(pal), 2.6 * px, 0.95);
    // the trained route, fine enough to follow its perspective: screen points and the world distance to each
    var dense = densify(SB.trainR, 0.04), cum = [0];
    for (var k = 1; k < dense.length; k++) cum.push(cum[k - 1] + dist(dense[k - 1], dense[k]));
    C.tScr = dense.map(function (p) { var q = pr(p[0], p[1]); return [q[0], q[1]]; });
    C.tCum = cum;
    C.lap = cum[cum.length - 1];
    return C;
  }
  // the trained route walked so far, d along it (world units), as screen points
  function sbWalked(m, C, d) {
    if (d <= 0) return [];
    var out = [], i = 1;
    for (; i < C.tCum.length && C.tCum[i] <= d; i++) out.push(C.tScr[i - 1]);
    if (i >= C.tCum.length) { out.push(C.tScr[C.tScr.length - 1]); return out; }
    out.push(C.tScr[i - 1]);
    var q = m.pr.apply(null, polyAt(SB.trainR, d)); out.push([q[0], q[1]]);
    return out;
  }
  // the world disc the fan has grown to, as a screen outline (the opening fan is revealed through it)
  function sbFanClip(m, g) {
    var rr = SB.r0 + (SB.La - SB.r0) * g + 0.012, pts = [];
    for (var i = 0; i < 72; i++) { var a = i / 72 * TAU, q = m.pr(Math.sin(a) * rr, Math.cos(a) * rr); pts.push([q[0], q[1]]); }
    return S.d(pts, true);
  }
  function sbOpen(s) { var openG = s.ph === 'train' ? 0 : s.ph === 'open' ? ease(s.t / SB_OPEN) : 1; return { openG: openG, g: ease(openG) }; }
  // the moving rat while the route is taught: [x, y, radius], or null when the route is not shown
  function sbTrainRat(m, C, s) {
    var d = s.t * SB_SPEED, rp = d < C.lap * 2 ? polyAt(SB.trainR, d % C.lap) : [SB.G[0], SB.G[1] + 0.03], q = m.pr(rp[0], rp[1]);
    return [q[0], q[1], (5 * q[2] + 1.2) * m.sz];
  }
  function sbTrainRoute(m, C, s) { var d = s.t * SB_SPEED; return d < C.lap * 2 ? sbWalked(m, C, d % C.lap) : []; }
  function sbRatHalo(x, y, rad, pal) { return pal.glow ? rad * 3.4 * 0.52 : rad * 3.4 * 0.72; }
  // every released point: [x, y, radius, colour, opacity]; one not yet released has no size and no light
  function sbRelease(m, s, pal) {
    var T = s.ph === 'done' ? 1e9 : s.t, done = s.ph === 'done' ? 1 : clamp((s.t - (SB_REL - 0.9)) / 0.8, 0, 1), p0 = m.pr(0, 0);
    return { done: done, pts: s.rats.map(function (r, j) {
      var arm = SB.arms[r.arm], u = (T - j * SB_GAP) / SB_RUN;
      if (u <= 0) return [p0[0], p0[1], 0, pal.ink[0], 0];
      var e = ease(Math.min(1, u)), dd2 = lerp(0, sbSlot(r), e), perp = [arm.v[1], -arm.v[0]], off = u < 1 ? r.side * 0.03 * Math.sin(Math.PI * e) : 0;
      var q = m.pr(arm.v[0] * dd2 + perp[0] * off, arm.v[1] * dd2 + perp[1] * off);
      var hot = u >= 1 && r.arm === SB.target && done > 0, role = u < 1 || hot ? lit(pal) : 'ink', c = pal[role];
      return [q[0], q[1], (3.2 * q[2] + 0.9) * m.sz, c[0], c[1] * (u < 1 ? 0.95 : 0.88)];
    }) };
  }
  function sbDot(a) { return '<circle cx="' + n(a[0]) + '" cy="' + n(a[1]) + '" r="' + n(a[2]) + '" fill="' + a[3] + '" fill-opacity="' + n(a[4]) + '"/>'; }
  function setA(el, k, v) { if (el.getAttribute(k) !== v) el.setAttribute(k, v); }
  var sbDef = {
    id: 'shortcut', name: 'sunburst-maze', title: 'The sunburst maze',
    caption: 'Points released at the start spread over a fan of new paths.',
    modelFor: live('shortcut', sbModel),
    initialState: function () { return sbState('train', 0, 0); },
    stillState: function () { return sbState('done', 0, 0); },
    tick: function (m, s, dt) {
      var t = s.t + dt, ph = s.ph;
      if (ph === 'train' && t >= SB_TRAIN) { ph = 'open'; t = 0; }
      else if (ph === 'open' && t >= SB_OPEN) { ph = 'release'; t = 0; }
      else if (ph === 'release' && t >= SB_REL) { ph = 'done'; t = 0; }
      return { ph: ph, t: t, seed: s.seed, rats: s.rats };
    },
    settled: function (m, s) { return s.ph === 'done'; },
    // Back: what stands still in this phase (written once per phase). Front: only what moves.
    draw: function (m, s, pal) {
      var C = sbC(m, pal), o = sbOpen(s), back = C.ring, front = { mark: '<g data-sbph="' + s.ph + '"></g>' };
      if (s.ph === 'train') back += C.trainLit + grp(0.5, C.fanDots);
      else if (s.ph !== 'open') back += C.trainDash + C.wall + C.arms + grp(0.75, C.dir);
      back += C.food;
      if (s.ph === 'open') {
        var clipId = 'x-sb-fan-' + pal.name;
        front.open = '<g data-x="o0" opacity="' + n(1 - o.openG) + '">' + C.trainLit + '</g>' +
          '<g data-x="o1" opacity="' + n(o.openG) + '">' + C.trainDash + '</g>' +
          '<g data-x="o2" opacity="' + n(0.5 * (1 - o.openG)) + '">' + C.fanDots + '</g>' +
          '<g data-x="o3" opacity="' + n(o.openG) + '">' + C.wall + '</g>' +
          '<clipPath id="' + clipId + '"><path data-x="clip" d="' + sbFanClip(m, o.g) + '"/></clipPath>' +
          '<g clip-path="url(#' + clipId + ')">' + C.arms + '</g>' +
          '<g data-x="o4" opacity="' + n(0.75 * o.openG) + '">' + C.dir + '</g>';
      }
      if (s.ph === 'train') {
        var rt = sbTrainRat(m, C, s);
        front.run = '<path data-x="route" d="' + S.d(sbTrainRoute(m, C, s)) + '" ' + S.stroke(pal, lit(pal), 2.4 * m.px, 0.9) + '/>' +
          tagged(halo(rt[0], rt[1], rt[2] * 3.4, pal, 'mint', 0.17), 'rh') + tagged(S.dot(rt[0], rt[1], rt[2], pal, lit(pal)), 'rd');
      }
      if (s.ph === 'release' || s.ph === 'done') {
        var rel = sbRelease(m, s, pal);
        front.hot = '<g data-x="hot" opacity="' + n(rel.done) + '">' + C.hot + '</g>';
        front.rats = rel.pts.map(sbDot).join('');
      }
      return { back: back, front: front, labels: C.labels };
    },
    // Later frames of the same phase: move the points and fade the groups that are already there.
    update: function (m, s, ctx) {
      var mk = ctx.front.querySelector('[data-sbph]');
      if (!mk || mk.getAttribute('data-sbph') !== s.ph) return false;
      var C = sbC(m, ctx.pal), e = mk._els;
      if (!e || e.pal !== ctx.pal) {
        e = mk._els = { pal: ctx.pal };
        ['o0', 'o1', 'o2', 'o3', 'o4', 'clip', 'route', 'rh', 'rd', 'hot'].forEach(function (k) { e[k] = ctx.front.querySelector('[data-x="' + k + '"]'); });
        e.rats = ctx.parts && ctx.parts.rats ? ctx.parts.rats.children : null;
      }
      if (s.ph === 'open') {
        if (!e.o0 || !e.clip) return false;
        var o = sbOpen(s);
        setA(e.o0, 'opacity', String(n(1 - o.openG))); setA(e.o1, 'opacity', String(n(o.openG)));
        setA(e.o2, 'opacity', String(n(0.5 * (1 - o.openG)))); setA(e.o3, 'opacity', String(n(o.openG)));
        setA(e.o4, 'opacity', String(n(0.75 * o.openG))); setA(e.clip, 'd', sbFanClip(m, o.g));
      } else if (s.ph === 'train') {
        if (!e.route || !e.rh || !e.rd) return false;
        var rt = sbTrainRat(m, C, s), hr = sbRatHalo(rt[0], rt[1], rt[2], ctx.pal);
        setA(e.route, 'd', S.d(sbTrainRoute(m, C, s)));
        setA(e.rh, 'cx', String(n(rt[0]))); setA(e.rh, 'cy', String(n(rt[1]))); setA(e.rh, 'r', String(n(hr)));
        setA(e.rd, 'cx', String(n(rt[0]))); setA(e.rd, 'cy', String(n(rt[1]))); setA(e.rd, 'r', String(n(rt[2])));
      } else {
        if (!e.hot || !e.rats || e.rats.length !== s.rats.length) return false;
        var rel = sbRelease(m, s, ctx.pal);
        setA(e.hot, 'opacity', String(n(rel.done)));
        for (var i = 0; i < rel.pts.length; i++) {
          var a = rel.pts[i], c = e.rats[i];
          setA(c, 'cx', String(n(a[0]))); setA(c, 'cy', String(n(a[1]))); setA(c, 'r', String(n(a[2])));
          setA(c, 'fill', a[3]); setA(c, 'fill-opacity', String(n(a[4])));
        }
      }
    },
    describe: function (m, s) {
      if (s.ph === 'train') return 'Seen from above and behind: a round start, and one long route from it, ahead, left, across to the right and back down to the food. A rat runs the long route. Around the start, a fan of paths is drawn as faint dotted lines.';
      if (s.ph === 'open') return 'A wall closes the long route at its entrance, and a fan of new paths opens around the start. A dotted line marks the direction of the food.';
      if (s.ph === 'release') return 'A wall closes the long route, and a fan of new paths leaves the start. Many points leave the start one by one, each along one of the new paths, and line up on the path it took.';
      return 'A wall closes the long route, and a fan of new paths leaves the start. Many points have spread over the paths, lined up along each one. The path pointing straight at the food is lit and holds more points than any other single path; the rest are spread over all the others.';
    },
    // the long route is taught (twice round), then a wall closes it and the fan of new paths opens,
    // then the points leave the start one by one and spread over the fan
    sequence: [
      { dur: Math.ceil((SB_TRAIN + SB_OPEN + SB_REL) * 1000) + 250 },
      { dur: 0, 'do': function (m, s) { return s.ph === 'done' ? s : sbState('done', 0, s.seed); } },
      { dur: 900 }
    ],
    controls: []
  };
  sbDef.model = sbModel({ width: 860, height: 760 });
  var sbH = P.figure(sbDef);

  /* ===== 5. Learning sets: puzzle after puzzle ========================================= */
  // three runs of puzzles, early, later and much later; the faint dots between runs stand for the
  // many puzzles in between. Each number is how many tries that puzzle took.
  var LS_RUNS = [[6, 6, 5], [4, 3, 3], [2, 1, 1]];
  var LS = (function () {
    var rng = P.mulberry(77), puzzles = [], t = 0, idx = 0;
    LS_RUNS.forEach(function (run, gi) {
      run.forEach(function (k, pi) {
        var i = idx++, k1 = (i * 3) % 8, k2 = (k1 + 1 + (i % 3)) % 8;
        var g1 = { kind: k1, n: 3 + Math.floor(rng() * 4), rot: rng() * TAU, a: 0.38 + rng() * 0.22 };
        var g2 = { kind: k2, n: 3 + Math.floor(rng() * 4), rot: rng() * TAU, a: 0.38 + rng() * 0.22 };
        var right = rng() < 0.5 ? 0 : 1, d = gi === 0 ? 0.5 : gi === 1 ? 0.46 : 0.42, intro = 0.35, outro = 0.35, starts = [];
        for (var j = 0; j < k; j++) starts.push(t + intro + j * d);
        puzzles.push({ g: [g1, g2], right: right, tries: k, run: gi, pos: pi, start: t, d: d, intro: intro, tryStart: starts, end: t + intro + k * d + outro });
        t = puzzles[i].end;
      });
    });
    return { puzzles: puzzles, total: t };
  })();
  function glyph(g, cx, cy, R, pal, role, w, op) {
    var out = '', i, pts = [], a;
    switch (g.kind) {
      case 0: for (i = 0; i < g.n; i++) { a = g.rot + i * TAU / g.n; pts.push([cx + R * Math.cos(a), cy + R * Math.sin(a)]); } return S.path(pts, pal, role, w, { close: true, opacity: op });
      case 1: var k = g.n + 2; for (i = 0; i < 2 * k; i++) { a = g.rot + i * Math.PI / k; var rr = i % 2 ? R * g.a : R; pts.push([cx + rr * Math.cos(a), cy + rr * Math.sin(a)]); } return S.path(pts, pal, role, w, { close: true, opacity: op });
      case 2: return S.circle(cx, cy, R * 0.92, pal, role, w, op) + S.circle(cx, cy, R * 0.45, pal, role, w, op) + S.dot(cx, cy, Math.max(1.2, R * 0.09), pal, role, op);
      case 3: for (i = 0; i < 2; i++) { a = g.rot + i * Math.PI / 2; out += S.line(cx - R * Math.cos(a), cy - R * Math.sin(a), cx + R * Math.cos(a), cy + R * Math.sin(a), pal, role, w, op); } return out + S.circle(cx, cy, R * 0.5, pal, role, w, op);
      case 4: for (var row = -1; row <= 1; row += 2) { pts = []; for (i = 0; i <= 28; i++) { var x = -R + 2 * R * i / 28; pts.push([cx + x, cy + row * R * 0.36 + Math.sin(i / 28 * Math.PI * (2 + g.n % 2) + g.rot) * R * 0.26]); } out += S.path(pts, pal, role, w, { opacity: op }); } return out;
      case 5: out += S.circle(cx, cy, R * 0.95, pal, role, w, op); for (i = 0; i < 3; i++) { a = g.rot + i * TAU / 3; pts.push([cx + R * 0.58 * Math.cos(a), cy + R * 0.58 * Math.sin(a)]); } return out + S.path(pts, pal, role, w, { close: true, opacity: op });
      case 6: for (i = 0; i < g.n; i++) { a = g.rot + i * TAU / g.n; pts.push([cx + R * Math.cos(a), cy + R * Math.sin(a)]); } out += S.path(pts, pal, role, w, { close: true, opacity: op }); pts = [];
        for (i = 0; i < g.n; i++) { a = g.rot + Math.PI / g.n + i * TAU / g.n; pts.push([cx + R * 0.5 * Math.cos(a), cy + R * 0.5 * Math.sin(a)]); } return out + S.path(pts, pal, role, w, { close: true, opacity: op });
      default: for (i = 0; i <= 70; i++) { a = g.rot + i / 70 * Math.PI * 4.4; var r2 = R * (0.1 + 0.9 * i / 70); pts.push([cx + r2 * Math.cos(a), cy + r2 * Math.sin(a)]); } return S.path(pts, pal, role, w, { opacity: op });
    }
  }
  // one cell per puzzle: on a wide screen the three runs stand in one row, on a phone one run per row
  function lsModel(box) {
    var cells = [], gaps = [], W, H, px, key, R, cw, gap, lw, narrow = box.width < 640;
    if (narrow) {
      px = narrowPx(600, box); W = 600; cw = 172; R = 36; gap = 26; lw = 2.2;
      var top = 6, xs = (600 - 3 * cw) / 2;
      LS_RUNS.forEach(function (run, gi) {
        run.forEach(function (k, pi) { cells.push({ cx: xs + (pi + 0.5) * cw, top: top }); });
        var h = 2 * R + 82 + (Math.max.apply(null, run) - 1) * gap + 14;
        top += h;
        if (gi < LS_RUNS.length - 1) { gaps.push({ x: 300, y: top + 14, vertical: false }); top += 40; }
      });
      H = Math.round(top + 4); key = 'ls:n' + px;
      return { key: key, view: { w: W, h: H }, px: px, narrow: true, cells: cells, gaps: gaps, R: R, cw: cw, gap: gap, lw: lw, hand: 6 };
    }
    var wh = boxWH(box); W = wh[0]; H = wh[1];
    var mx = 16, units = 9 + 2 * 0.7; cw = (W - 2 * mx) / units;
    R = clamp(Math.min(cw * 0.21, H * 0.08), 16, 40);
    var y0 = 2 * R + 82; gap = clamp((H - 16 - y0) / 6, 14, 46); lw = clamp(gap * 0.11, 2.2, 4.4);
    LS.puzzles.forEach(function (p) { cells.push({ cx: mx + (p.run * 3 + p.pos + p.run * 0.7 + 0.5) * cw, top: 4 }); });
    for (var gi = 1; gi < 3; gi++) gaps.push({ x: mx + (gi * 3 + (gi - 0.5) * 0.7) * cw, y: 4 + R + 12, vertical: false });
    return { key: 'ls:' + W + 'x' + H, view: { w: W, h: H }, px: 1, narrow: false, cells: cells, gaps: gaps, R: R, cw: cw, gap: gap, lw: lw, hand: 6 };
  }
  function lsDone(t) { var k = 0; LS.puzzles.forEach(function (p) { if (p.end <= t + 1e-6) k++; }); return k; }
  function lsAt(t) { for (var i = 0; i < LS.puzzles.length; i++) if (t <= LS.puzzles[i].end + 1e-6) return i; return LS.puzzles.length - 1; }
  function lsNext(m, s) {
    var i = lsAt(s.t), p = LS.puzzles[i], stop;
    if (s.t < p.end - 1e-6 && s.t > p.start + 1e-6) stop = p.end; else if (s.t >= LS.total - 1e-6) return act(lsDef, lsH, m, { t: 0, stop: LS.puzzles[0].end }); else stop = LS.puzzles[Math.min(LS.puzzles.length - 1, s.t >= p.end - 1e-6 ? i + 1 : i)].end;
    return act(lsDef, lsH, m, { t: s.t, stop: stop });
  }
  var lsDef = {
    id: 'sets', name: 'learning-sets', title: 'A row of small two-object puzzles',
    caption: 'Each puzzle has two new objects, and each mark under it is one try.',
    modelFor: live('sets', lsModel),
    initialState: function () { return { t: 0, stop: LS.puzzles[0].end }; },
    stillState: function () { return { t: LS.total, stop: LS.total }; },
    tick: function (m, s, dt) { return { t: Math.min(s.stop, s.t + dt), stop: s.stop }; },
    settled: function (m, s) { return s.t >= s.stop - 1e-6; },
    draw: function (m, s, pal) {
      // one front part per puzzle: only the puzzle being solved is written again while it plays
      var back = '', front = {}, t = s.t, cur = lsAt(t), R = m.R, cw = m.cw, px = m.px;
      var objDx = cw * 0.25, objY = R + 12, trayY = objY + R + 14, restY = trayY + 26, y0 = trayY + 58;
      // the many puzzles between the runs
      m.gaps.forEach(function (g) { for (var k = -1; k <= 1; k++) back += S.dot(g.x + k * 12 * px, g.y + (m.narrow ? 0 : 0), 2.2 * px, pal, 'soft', 0.7); });
      LS.puzzles.forEach(function (p, i) {
        var c = m.cells[i], cx = c.cx, top = c.top, ob = [[cx - objDx, top + objY], [cx + objDx, top + objY]];
        var future = i > cur || (i === cur && t <= p.start + 1e-6 && i > 0);
        var isCur = i === cur && !future, done = !future && (i < cur || t >= p.end - 1e-6);
        back += S.line(cx - cw * 0.4, top + trayY, cx + cw * 0.4, top + trayY, pal, future ? 'faint' : 'soft', 1, future ? 1 : 0.6);
        // every try has its place under the puzzle from the start, drawn faintly; a try's mark covers it
        for (var jj = 0; jj < p.tries; jj++) { var yy = top + y0 + jj * m.gap; back += dpath([[cx - cw * 0.2, yy], [cx + cw * 0.2, yy]], pal, 'quiet', 0.5 * m.lw * px, '0.5 ' + n(1.6 * m.lw * px), 0.8); }
        front['p' + i] = '';
        // a puzzle still to come shows its two objects faintly
        if (future) { back += glyph(p.g[0], ob[0][0], ob[0][1], R, pal, 'soft', 1.2 * px, 0.42) + glyph(p.g[1], ob[1][0], ob[1][1], R, pal, 'soft', 1.2 * px, 0.42); return; }
        var part = '';
        var vis = isCur ? Math.max(0.28, clamp((t - p.start) / Math.max(0.01, p.intro), 0, 1)) : 1, curTry = -1, f = 0;
        if (isCur) p.tryStart.forEach(function (ts, j) { if (t >= ts) { curTry = j; f = (t - ts) / p.d; } });
        var marks = done ? p.tries : (curTry < 0 ? 0 : (f >= 0.5 ? curTry + 1 : curTry));
        var solved = marks === p.tries;
        // the two objects; the one with food under it lights once it is found
        [0, 1].forEach(function (o) {
          var isRight = o === p.right, role = isCur ? 'ink' : 'soft', op = isCur ? 0.95 : 0.85, w = (isCur ? 1.7 : 1.4) * px;
          if (solved && isRight) { role = isCur ? lit(pal) : 'ink'; op = 1; w = (isCur ? 2.1 : 1.6) * px; }
          if (isCur && !isRight && curTry >= 0 && curTry < p.tries - 1 && f >= 0.5 && f < 1.02) op = 0.35;
          part += glyph(p.g[o], ob[o][0], ob[o][1], R, pal, role, w, op * vis);
          if (solved && isRight) part += foodMark([ob[o][0], top + trayY + 9], 3.4 * px, pal, vis);
        });
        // the reach: a point goes out to one object and back for every try
        if (isCur && curTry >= 0 && f < 1) {
          var pick = curTry < p.tries - 1 ? 1 - p.right : p.right, rest = [cx, top + restY], tgt = [ob[pick][0], top + trayY - 4];
          var gg = f < 0.45 ? ease(f / 0.45) : f < 0.65 ? 1 : 1 - ease((f - 0.65) / 0.35);
          part += ratDot(mix(rest, tgt, gg), m.hand * px, pal);
        } else if (isCur) part += S.dot(cx, top + restY, m.hand * 0.7 * px, pal, 'soft', 0.7 * vis);
        // one mark per try, the last (the try that found the food) lit
        for (var j = 0; j < marks; j++) {
          var y = top + y0 + j * m.gap, right = j === p.tries - 1;
          part += S.line(cx - cw * 0.2, y, cx + cw * 0.2, y, pal, right ? lit(pal) : (isCur ? 'ink' : 'soft'), (right ? 1.15 : 1) * m.lw * px, right ? 1 : (isCur ? 0.95 : 0.7));
        }
        front['p' + i] = part;
      });
      return { back: back, front: front, labels: '' };
    },
    describe: function (m, s) {
      var k = lsDone(s.t), base = 'Small puzzles in a row, in three runs with faint dots between them for the many puzzles in between. Each puzzle has two different objects, with food under one. Under each puzzle, a faint place for each try it takes, filled with a mark as the try is made; the last mark, lit, is the try that found the food. ';
      if (k < LS.puzzles.length) base += 'The puzzles further along the row are drawn faintly. ';
      if (k === 0) return base + 'On the first puzzle, a point reaches for one object at a time.';
      if (k < 3) return base + 'The first puzzles each have a tall stack of marks.';
      if (k < LS.puzzles.length) return base + 'From run to run the stacks get shorter.';
      return base + 'The stacks get shorter from run to run: the early puzzles have many marks, and the last puzzle has a single lit mark.';
    },
    // the puzzles are stepped through by themselves, run by run, with a short rest between runs: many
    // tries on the first puzzles, fewer later, a single try on the last
    sequence: [
      { dur: 0, tick: false, 'do': function (m, s) { return { t: 0, stop: LS.total }; } },
      { dur: 6800, tick: false, to: { t: LS.puzzles[2].end }, ease: 'linear' },
      { dur: 550, tick: false },
      { dur: 3900, tick: false, to: { t: LS.puzzles[5].end }, ease: 'linear' },
      { dur: 550, tick: false },
      { dur: 2900, tick: false, to: { t: LS.total }, ease: 'linear' },
      { dur: 1100, tick: false }
    ],
    controls: [],
    keys: {
      ArrowRight: function (m, s) { return lsNext(m, s); },
      End: function (m, s) { return act(lsDef, lsH, m, { t: s.t >= LS.total - 1e-6 ? 0 : s.t, stop: LS.total }); }
    },
    keysLabel: 'The right arrow key shows the next puzzle; End plays them all.',
    handle: function (m, s) { var c = m.cells[lsAt(s.t)]; return [c.cx, c.top + m.R + 12]; }
  };
  lsDef.model = lsModel({ width: 1376, height: 470 });
  var lsH = P.figure(lsDef);

  /* ===== 6. Transitive inference: pairs taught one at a time, then B and D ============== */
  // as the sentence has it: A beats B, B beats C, C beats D; then B and D together
  var LET = ['A', 'B', 'C', 'D'], PAIRS = [[0, 1], [1, 2], [2, 3]];
  var ASKN = PAIRS.length + 1;
  var TEACH_D = 1.4, ASK_D = 4.2, OR_ASM = 2.3;
  function orModel(box) {
    if (box.width < 640) {
      var px = narrowPx(600, box);
      return { key: 'or:n' + px, view: { w: 600, h: 600 }, px: px, narrow: true, r: 34, fsTop: 26 * px, top: 84, fl: 22 * px,
        scat: [[100, 270], [228, 500], [372, 240], [500, 470]], line: [0, 1, 2, 3].map(function (i) { return [90 + i * 140, 400]; }) };
    }
    var wh = boxWH(box), W = wh[0], H = wh[1], r = clamp(H * 0.08, 32, 50);
    return { key: 'or:' + W + 'x' + H, view: { w: W, h: H }, px: 1, narrow: false, r: r, fsTop: clamp(H * 0.09, 30, 52), top: clamp(H * 0.12, 44, 84), fl: r,
      scat: [[0.15, 0.47], [0.38, 0.84], [0.62, 0.44], [0.85, 0.8]].map(function (f) { return [f[0] * W, f[1] * H]; }),
      line: [0, 1, 2, 3].map(function (i) { return [W * (0.18 + i * 0.64 / 3), H * 0.64]; }) };
  }
  function orAsm(s) { return s.n === ASKN ? ease((s.t - OR_ASM) / 1.5) : 0; }
  function orPos(m, s) { var a = orAsm(s); return m.scat.map(function (p, i) { return mix(p, m.line[i], a); }); }
  // the mark between two points of a pair: a small arrowhead at the middle of the link, pointing from
  // the one that wins to the other
  function orMark(seg, size, pal, role, w, op) {
    var a = seg[0], b = seg[1], d = dist(a, b) || 1, u = [(b[0] - a[0]) / d, (b[1] - a[1]) / d], c = mix(a, b, 0.5);
    var tip = [c[0] + u[0] * size * 0.6, c[1] + u[1] * size * 0.6], bk = [c[0] - u[0] * size * 0.6, c[1] - u[1] * size * 0.6];
    return S.path([[bk[0] - u[1] * size, bk[1] + u[0] * size], tip, [bk[0] + u[1] * size, bk[1] - u[0] * size]], pal, role, w, { opacity: op });
  }
  function trim(a, b, r) { var d = dist(a, b), u = [(b[0] - a[0]) / d, (b[1] - a[1]) / d]; return [[a[0] + u[0] * r, a[1] + u[1] * r], [b[0] - u[0] * r, b[1] - u[1] * r]]; }
  function orNext(m, s) {
    if (s.n >= ASKN) return orDef.initialState(m);
    return act(orDef, orH, m, { n: s.n + 1, t: 0 });
  }
  // the three pairs are taught one at a time, then B and D are shown together; B lights and the four line up
  var OR_SEQ = [{ dur: 1100, tick: false }];
  PAIRS.forEach(function (pp, i) {
    OR_SEQ.push({ dur: 0, 'do': function () { return { n: i + 1, t: 0 }; } });
    OR_SEQ.push({ dur: 2200 });
  });
  OR_SEQ.push({ dur: 0, 'do': function () { return { n: ASKN, t: 0 }; } });
  OR_SEQ.push({ dur: Math.round(ASK_D * 1000) });
  OR_SEQ.push({ dur: 0, tick: false, 'do': function () { return { n: ASKN, t: ASK_D }; } });
  OR_SEQ.push({ dur: 1000, tick: false });
  var orDef = {
    id: 'order', name: 'transitive-order', title: 'Four items taught one pair at a time',
    caption: 'Four items taught one pair at a time, then two that were never shown together.',
    modelFor: live('order', orModel),
    initialState: function () { return { n: 0, t: 0 }; },
    stillState: function () { return { n: ASKN, t: ASK_D }; },
    tick: function (m, s, dt) { return { n: s.n, t: s.t + dt }; },
    settled: function (m, s) { return s.n === 0 || s.t >= (s.n === ASKN ? ASK_D : TEACH_D); },
    draw: function (m, s, pal) {
      var links = '', items = '', labels = '', pos = orPos(m, s), r = m.r, px = m.px, taught = Math.min(s.n, PAIRS.length), asm = orAsm(s);
      var mz = (m.narrow ? 11 : clamp(r * 0.26, 9, 13)) * px;
      var ask = s.n === ASKN, pick = ask && s.t > 1.0, curPair = s.n >= 1 && s.n <= PAIRS.length ? PAIRS[s.n - 1] : null;
      // every pair taught so far, as a link between its two points
      for (var i = 0; i < taught; i++) {
        var pp = PAIRS[i], cur = curPair && i === s.n - 1, g = cur ? easeOut(s.t / 0.6) : 1;
        var seg = trim(pos[pp[0]], pos[pp[1]], r * 0.62 + 8), end = mix(seg[0], seg[1], g);
        if (asm > 0) links += S.path([seg[0], end], pal, 'soft', 1.3 * px, { opacity: 0.55 + 0.35 * asm });
        else links += S.path([seg[0], end], pal, cur ? lit(pal) : 'soft', (cur ? 2 : 1.3) * px, { opacity: cur ? 0.9 : 0.6 });
        // once the link is drawn, the mark between the two: the first of the pair wins
        var mk = cur ? clamp((s.t - 0.45) / 0.3, 0, 1) : 1;
        if (mk > 0.01) links += orMark(seg, mz, pal, cur && asm === 0 ? lit(pal) : 'soft', (cur ? 2 : 1.4) * px, (cur ? 1 : 0.75) * mk);
      }
      // the pairs still to teach are there from the start, as faint dotted links
      var rest = '';
      for (var k = taught; k < PAIRS.length; k++) rest += dpath(trim(pos[PAIRS[k][0]], pos[PAIRS[k][1]], r * 0.62 + 8), pal, 'quiet', 1.2 * px, '2 7', 1);
      // B and D together: a dotted link with an open ring between them, until B is picked; then the
      // same mark as a taught pair, from B to D
      if (ask && asm < 1) {
        var bd = trim(pos[1], pos[3], r * 0.62 + 8), bm = mix(bd[0], bd[1], 0.5), bin = '';
        bin += dpath(bd, pal, 'peri', 1.6 * px, '4 7', 0.95);
        if (!pick) bin += S.circle(bm[0], bm[1], mz * 0.7, pal, 'peri', 1.6 * px, 0.95);
        else bin += orMark(bd, mz, pal, lit(pal), 2 * px, clamp((s.t - 1.0) / 0.3, 0, 1));
        links += grp((1 - asm) * clamp(s.t / 0.4, 0, 1), bin);
      }
      if (asm > 0.98) links += lanes([[[m.line[0][0] - r * 1.6, m.line[0][1]], [m.line[3][0] + r * 1.6, m.line[3][1]]]], function (x, y) { return [x, y, 1]; }, pal, { w: 22 * px, band: 0.07, core: 0, step: 40 });
      pos.forEach(function (p, i) {
        var role = 'ink', op = 0.8, ring = null, rw = 1.5;
        if (curPair) {
          if (i === curPair[0] && s.t > 0.45) { role = lit(pal); op = 1; ring = lit(pal); rw = 2; }
          else if (i === curPair[0] || i === curPair[1]) { op = 1; ring = 'read'; }
          else op = 0.55;
        }
        if (ask && (i === 1 || i === 3)) { ring = 'peri'; op = 1; }
        if (ask && i !== 1 && i !== 3 && asm < 0.5) op = 0.5;
        if (pick && i === 1) { role = lit(pal); op = 1; ring = lit(pal); rw = 2; }
        if (pick && i === 3) { op = 0.6; ring = asm > 0.5 ? null : 'soft'; }
        var dr = (m.narrow ? 8 : 8.5) * px;
        items += halo(p[0], p[1], r * 0.8, pal, role === 'ink' ? 'peri' : 'mint', 0.13 * op) + S.dot(p[0], p[1], dr, pal, role, op);
        if (ring) items += S.circle(p[0], p[1], r * 0.62, pal, ring, rw * px, 0.95);
        var lop = curPair && (i === curPair[0] || i === curPair[1]) || (ask && (i === 1 || i === 3)) ? 1 : Math.max(0.62, op);
        labels += S.text(p[0], p[1] - r * 0.98, LET[i], pal, lop > 0.95 ? 'ink' : 'read', { size: n(m.fl), anchor: 'middle', weight: 500, opacity: lop });
      });
      // the links still to teach change only when a pair is taught: they sit in the back
      return { back: rest, front: { links: links, items: items }, labels: clear(labels, pal, 6) };
    },
    describe: function (m, s) {
      if (s.n === 0) return 'Four points labelled A, B, C and D, scattered, with faint dotted links for the pairs A and B, B and C, C and D.';
      if (s.n <= PAIRS.length) {
        var p = PAIRS[s.n - 1];
        return 'Four points labelled A to D. Links join the pairs taught so far: ' + PAIRS.slice(0, s.n).map(function (q) { return LET[q[0]] + ' beats ' + LET[q[1]]; }).join(', ') +
          '. A small arrowhead on each link points from the one that wins to the other. In the newest pair, ' + LET[p[0]] + ' and ' + LET[p[1]] + ', ' + LET[p[0]] + ' is lit.';
      }
      if (s.t < 1.0) return 'The taught pairs are linked. B and D are shown together for the first time, ringed and joined by a dotted line with an open ring at its middle.';
      return 'B and D are shown together for the first time, and B lights. The four points then line up in one order: A, B, C, D.';
    },
    sequence: OR_SEQ,
    controls: [],
    keys: { ArrowRight: function (m, s) { return orNext(m, s); }, Enter: function (m, s) { return orNext(m, s); } },
    keysLabel: 'The right arrow key or Enter teaches the next pair, then shows B and D.',
    handle: function (m, s) { var p = orPos(m, s); return p[s.n >= 1 && s.n <= PAIRS.length ? PAIRS[s.n - 1][0] : 1]; }
  };
  orDef.model = orModel({ width: 1376, height: 560 });
  var orH = P.figure(orDef);

})(window.Psyche);
