(function (P) {
  'use strict';
  var S = P.svg, n = S.n;
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function ease(u) { u = clamp(u, 0, 1); return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; }
  function smooth(a, b, x) { var u = clamp((x - a) / (b - a), 0, 1); return u * u * (3 - 2 * u); }
  function bez(c, u) {
    var v = 1 - u, a = v * v * v, b = 3 * v * v * u, d = 3 * v * u * u, e = u * u * u;
    return [a * c[0][0] + b * c[1][0] + d * c[2][0] + e * c[3][0], a * c[0][1] + b * c[1][1] + d * c[2][1] + e * c[3][1]];
  }
  function polyD(pts) { var s = ''; for (var i = 0; i < pts.length; i++) s += (i ? 'L' : 'M') + n(pts[i][0]) + ' ' + n(pts[i][1]); return s; }
  // a polyline cut at fraction f of its length
  function cut(pts, cum, f) {
    var L = cum[cum.length - 1] * clamp(f, 0, 1), out = [pts[0]];
    for (var i = 1; i < pts.length; i++) {
      if (cum[i] >= L) {
        var a = pts[i - 1], b = pts[i], u = (L - cum[i - 1]) / Math.max(1e-6, cum[i] - cum[i - 1]);
        out.push([a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u]);
        return out;
      }
      out.push(pts[i]);
    }
    return out;
  }
  function lengths(pts) { var c = [0]; for (var i = 1; i < pts.length; i++) c.push(c[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])); return c; }
  /* ------------------------------------------------------------------ */
  /* Keyed drawing: draw() writes the moving layer once as text; update() */
  /* then changes only the attributes that moved, adds what appeared and  */
  /* removes what went out, keeping the same paint order as draw().       */
  /* ------------------------------------------------------------------ */
  // Attribute sets for the palette roles (as S.stroke and S.fill, opacity always written)
  function strokeA(pal, r, w, op) {
    var c = pal[r], o = c[1] * (op == null ? 1 : op);
    var a = { fill: 'none', stroke: c[0], 'stroke-width': n((w || 1) * pal.weight), 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-opacity': n(o) };
    if (pal.dash[r]) a['stroke-dasharray'] = pal.dash[r];
    return a;
  }
  function fillA(pal, r, op) { var c = pal[r]; return { fill: c[0], 'fill-opacity': n(c[1] * (op == null ? 1 : op)) }; }
  function withA(a, more) { for (var k in more) a[k] = more[k]; return a; }
  function dotI(k, x, y, r, pal, role, op) { return { k: k, tag: 'circle', a: withA({ cx: n(x), cy: n(y), r: n(r) }, fillA(pal, role, op)) }; }
  function ringI(k, x, y, r, pal, role, w, op) { return { k: k, tag: 'circle', a: withA({ cx: n(x), cy: n(y), r: n(r) }, strokeA(pal, role, w, op)) }; }
  // a soft point of light: in dark a faint disc close around a solid core, in light and print a thin
  // ring keeps it crisp
  function lightI(k, x, y, r, pal, role, kk, out) {
    kk = kk == null ? 1 : kk;
    if (pal.glow) out.push(dotI(k + 'h', x, y, r * 3.4, pal, role, 0.13 * kk));
    else out.push(ringI(k + 'h', x, y, r * 2.4, pal, role, 0.9, 0.55 * kk));
    out.push(dotI(k + 'c', x, y, r, pal, role, kk));
  }
  function attrText(a) { var s = ''; for (var k in a) s += ' ' + k + '="' + a[k] + '"'; return s; }
  // groups: [{ k, items: [{ k, tag, a }] }], in paint order
  function keyedHTML(groups) {
    var s = '';
    groups.forEach(function (G) {
      s += '<g data-g="' + G.k + '">';
      G.items.forEach(function (it) { s += '<' + it.tag + ' data-k="' + it.k + '"' + attrText(it.a) + '/>'; });
      s += '</g>';
    });
    return s;
  }
  function keyedApply(root, cache, groups) {
    if (cache.root !== root) { // the kit drew the layer afresh: index what is there
      cache.root = root; cache.g = {}; cache.el = {}; cache.a = {};
      Array.prototype.forEach.call(root.children, function (g) {
        var gk = g.getAttribute('data-g'); if (!gk) return;
        cache.g[gk] = g; cache.el[gk] = {}; cache.a[gk] = {};
        Array.prototype.forEach.call(g.children, function (e) { cache.el[gk][e.getAttribute('data-k')] = e; });
      });
    }
    var seenG = {}, prevG = null;
    groups.forEach(function (G) {
      var ge = cache.g[G.k];
      if (!ge) {
        ge = document.createElementNS('http://www.w3.org/2000/svg', 'g'); ge.setAttribute('data-g', G.k);
        root.insertBefore(ge, prevG ? prevG.nextSibling : root.firstChild);
        cache.g[G.k] = ge; cache.el[G.k] = {}; cache.a[G.k] = {};
      }
      seenG[G.k] = 1; prevG = ge;
      var els = cache.el[G.k], last = cache.a[G.k], seen = {}, prev = null;
      G.items.forEach(function (it) {
        var e = els[it.k], la = last[it.k], a = it.a, key;
        seen[it.k] = 1;
        if (!e) {
          e = document.createElementNS('http://www.w3.org/2000/svg', it.tag); e.setAttribute('data-k', it.k);
          for (key in a) e.setAttribute(key, a[key]);
          ge.insertBefore(e, prev ? prev.nextSibling : ge.firstChild);
          els[it.k] = e;
        } else if (!la) {
          for (key in a) if (e.getAttribute(key) !== String(a[key])) e.setAttribute(key, a[key]);
        } else {
          for (key in a) if (la[key] !== a[key]) e.setAttribute(key, a[key]);
        }
        last[it.k] = a; prev = e;
      });
      for (var k in els) if (!seen[k]) { els[k].remove(); delete els[k]; delete last[k]; }
    });
    for (var gk in cache.g) if (!seenG[gk]) { cache.g[gk].remove(); delete cache.g[gk]; delete cache.el[gk]; delete cache.a[gk]; }
  }
  // the written description follows the drawing while it plays, too (the kit writes it when it stops)
  function syncDesc(ctx, cache, text) {
    if (cache.descSvg !== ctx.svg) { cache.descSvg = ctx.svg; cache.desc = ctx.svg.querySelector('desc'); }
    if (cache.desc && cache.desc.textContent !== text) cache.desc.textContent = text;
  }

  /* ================================================================== */
  /* 1. The opening: three lines of light run toward one point and join */
  /* ================================================================== */
  // Geometry in view units = the pixels of the opening. P is the title's full stop, J the place
  // under it where the three lines become one. The lines come up from below the title: on a wide
  // screen from the left edge (between the title and the sentences), the bottom edge (right of the
  // sentences) and the right edge low down; on a phone from the two side edges under the title.
  var NAMES = ['investors', 'engineers', 'research partners'];
  var STARTS = [0, 0.1, 0.2];      // the three pulses leave one after another and arrive together
  var ARRIVE = 1, JOINED = 1.14, END = 2.0;
  // where a label can stand: near the start of its line, clear of every line and of the words
  function placeLabel(lines, li, text, size, W, H, avoid, top) {
    var L = lines[li], tw = text.length * size * 0.54, pad = 12;
    var pts = [];
    lines.forEach(function (o) { o.centre.forEach(function (q) { pts.push(q); }); o.strands.forEach(function (st) { for (var i = 0; i < st.length; i += 2) pts.push(st[i]); }); });
    function box(x, y, anchor) { var x0 = anchor === 'end' ? x - tw : x; return [x0, y - size * 0.82, x0 + tw, y + size * 0.26]; }
    function clear(b) {
      if (b[0] < 10 || b[2] > W - 10 || b[1] < top || b[3] > H - 8) return false;
      for (var i = 0; i < pts.length; i++) {
        var q = pts[i];
        if (q[0] > b[0] - pad && q[0] < b[2] + pad && q[1] > b[1] - pad && q[1] < b[3] + pad) return false;
      }
      for (var k = 0; k < avoid.length; k++) { var r = avoid[k]; if (b[0] < r[2] && b[2] > r[0] && b[1] < r[3] && b[3] > r[1]) return false; }
      return true;
    }
    var us = [0.06, 0.1, 0.15, 0.04, 0.2, 0.26], offs = [18, 26, 36, 48, 62];
    for (var a = 0; a < us.length; a++) {
      var cq = cut(L.centre, L.cum, us[a]), p = cq[cq.length - 1];
      var anchor = p[0] > W * 0.5 ? 'end' : 'start';
      for (var o = 0; o < offs.length; o++) {
        var d = offs[o], cands = [[p[0], p[1] - d], [p[0], p[1] + d + size * 0.6], [p[0] + (anchor === 'end' ? -d : d), p[1] - d], [p[0] + (anchor === 'end' ? -d : d), p[1] + d + size * 0.6]];
        for (var c = 0; c < cands.length; c++) {
          var x = Math.min(W - 12, Math.max(12, cands[c][0])), y = cands[c][1];
          var an = x > W * 0.5 ? 'end' : 'start';
          if (clear(box(x, y, an))) return [x, y, an];
        }
      }
    }
    var q0 = L.centre[Math.round(L.centre.length * 0.08)];
    return [q0[0], q0[1] - 20, q0[0] > W * 0.5 ? 'end' : 'start'];
  }
  function makeJoin(g) {
    var W = g.w, H = g.h, P0 = g.P, narrow = W <= 700, fs = g.fs;
    var J = [P0[0], P0[1] + fs * (narrow ? 0.62 : 0.72)];
    var curves;
    if (!narrow) {
      // the band between the title and the sentences, and the open ground right of the sentences
      var yA = clamp(g.tBottom + (g.bottom - g.tBottom) * 0.52, J[1] + 40, H - 120);
      var xB = clamp(Math.max(g.leadRight + 120, W * 0.5), 300, J[0] - 220);
      var yC = clamp(H * 0.86, J[1] + 160, H - 30);
      curves = [
        [[-14, yA], [W * 0.38, yA + 12], [J[0] - 30, yA + 10], [J[0], J[1]]],
        [[xB, H + 14], [xB + 10, H - (H - J[1]) * 0.45], [J[0] - 8, J[1] + (H - J[1]) * 0.42], [J[0], J[1]]],
        [[W + 14, yC], [W * 0.78, yC + 6], [J[0] - 2, J[1] + (yC - J[1]) * 0.5], [J[0], J[1]]]
      ];
    } else {
      // phone: the title is set to the right, so the lines cross the band under it toward the right
      var span = Math.max(160, g.bottom - J[1]), ya = J[1] + span * 0.36, yb = J[1] + span * 0.88, yc = J[1] + span * 0.66;
      curves = [
        [[-10, ya], [W * 0.46, ya + 6], [J[0] - 10, J[1] + (ya - J[1]) * 0.55], [J[0], J[1]]],
        [[-10, yb], [W * 0.52, yb + 4], [J[0] - 4, J[1] + (yb - J[1]) * 0.5], [J[0], J[1]]],
        [[W + 10, yc], [W * 0.5, yc + 6], [J[0] + 2, J[1] + (yc - J[1]) * 0.4], [J[0], J[1]]]
      ];
    }
    var rng = P.mulberry(23), spread = narrow ? 7 : 11;
    var lines = curves.map(function (c, li) {
      var N = 140, centre = [], strands = [[], [], []], ph = [rng() * 6, rng() * 6, rng() * 6];
      for (var i = 0; i <= N; i++) {
        var u = i / N, p = bez(c, u), q = bez(c, Math.min(1, u + 0.004)), r = bez(c, Math.max(0, u - 0.004));
        var tx = q[0] - r[0], ty = q[1] - r[1], tl = Math.hypot(tx, ty) || 1, nx = -ty / tl, ny = tx / tl;
        centre.push(p);
        var k = 1 - smooth(0, 0.62, u);
        for (var s = 0; s < 3; s++) {
          var off = (s - 1) * spread * k + Math.sin(u * 19 + ph[s]) * 2.6 * k * (s === 1 ? 0.4 : 1);
          strands[s].push([p[0] + nx * off, p[1] + ny * off]);
        }
      }
      var cum = lengths(centre), beads = [], step = narrow ? 30 : 42;
      for (var b = step * (0.6 + li * 0.3); b < cum[N] - (narrow ? 40 : 70); b += step) beads.push(b / cum[N]);
      var beadP = beads.map(function (b) { var q = cut(centre, cum, b); return q[q.length - 1]; });
      return { c: c, centre: centre, strands: strands, cum: cum, scum: strands.map(lengths), beads: beads, beadP: beadP, sd: strands.map(polyD) };
    });
    var size = narrow ? 13 : 15, avoid = (g.avoid || []).slice();
    // the stem and the ring around the full stop are kept clear too
    avoid.push([P0[0] - fs * 0.9, P0[1] - fs * 0.9, P0[0] + fs * 0.9, J[1] + 10]);
    var lab = [];
    NAMES.forEach(function (nm, i) {
      var l = placeLabel(lines, i, nm, size, W, H, avoid, g.head + 16);
      lab.push(l);
      var tw = nm.length * size * 0.54, x0 = l[2] === 'end' ? l[0] - tw : l[0];
      avoid.push([x0 - 8, l[1] - size, x0 + tw + 8, l[1] + size * 0.4]);
    });
    return {
      key: [Math.round(W), Math.round(H), Math.round(P0[0]), Math.round(P0[1])].join(':'),
      view: { w: Math.round(W), h: Math.round(H) }, P: P0, J: J, fs: fs, lines: lines, labels: lab,
      narrow: narrow, ring: Math.max(8, fs * 0.13), dot: !!g.dot
    };
  }
  // a box where it rests: without the small lift the arrival gives the opening's words for a moment
  function restRect(el) {
    var r = el.getBoundingClientRect(), dx = 0, dy = 0;
    try { var t = getComputedStyle(el).transform; if (t && t !== 'none') { var mx = new DOMMatrix(t); dx = mx.e; dy = mx.f; } } catch (e) { /* none */ }
    return { left: r.left - dx, top: r.top - dy, right: r.right - dx, bottom: r.bottom - dy, width: r.width, height: r.height };
  }
  // where the title, its full stop and the sentences are, measured from the page (layout only)
  function measureOpen(box) {
    var sec = document.querySelector('.ab-open'), dot = sec && sec.querySelector('.ab-dot'), t = sec && sec.querySelector('.ab-title');
    if (!sec || !dot || !t || !box.width) return null;
    var sr = sec.getBoundingClientRect(), dr = dot.getBoundingClientRect(), row = sec.querySelector('.ab-row');
    var range = document.createRange(); range.selectNodeContents(t);
    var rects = Array.prototype.slice.call(range.getClientRects()).filter(function (r) { return r.width > 1; });
    var fs = parseFloat(getComputedStyle(t).fontSize) || 120;
    var head = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--head-h')) || 68;
    var gut = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--gutter')) || 32;
    var avoid = rects.map(function (r) { return [r.left - sr.left, r.top - sr.top, r.right - sr.left, r.bottom - sr.top]; });
    var rr = row ? row.getBoundingClientRect() : null, lead = row && row.querySelector('.ab-lead'), lr = lead ? restRect(lead) : rr;
    // on a phone the lines and their labels keep a wider berth above the sentences
    var clear = box.width <= 700 ? 52 : 14, lift = box.width <= 700 ? 46 : 14;
    if (row) Array.prototype.forEach.call(row.children, function (c) { var r = restRect(c); avoid.push([r.left - sr.left - clear, r.top - sr.top - clear, r.right - sr.left + clear, r.bottom - sr.top + clear]); });
    return {
      w: box.width, h: box.height, fs: fs, head: head, gut: gut, avoid: avoid,
      P: [dr.left - sr.left + dr.width * 0.5, dr.top - sr.top + dr.height * 0.735],
      bottom: rr ? rr.top - sr.top - lift : box.height * 0.8,
      leadRight: lr ? lr.right - sr.left : box.width * 0.4,
      tBottom: Math.max.apply(null, rects.map(function (r) { return r.bottom; })) - sr.top,
      tTop: Math.min.apply(null, rects.map(function (r) { return r.top; })) - sr.top + fs * 0.12
    };
  }
  var JOIN_DEFAULT = { w: 1600, h: 900, fs: 166, head: 68, gut: 32, P: [1556, 382], tTop: 110, tBottom: 420, bottom: 560, leadRight: 600, dot: true,
    avoid: [[350, 92, 1568, 250], [262, 242, 1568, 420], [32, 560, 600, 846]] };

  // The static part (the three tracks, their points, the stem) is drawn once in back, clearly
  // visible from the first frame: the light later runs along lines that are already there.
  // The moving part is a fixed set of keyed items: each lit strand is the whole strand, revealed
  // up to the pulse by its dash (pathLength 1), so a frame changes one number per strand.
  function joinBack(m, pal) {
    var back = '', lw = m.narrow ? 0.9 : 1;
    m.lines.forEach(function (L) {
      L.strands.forEach(function (st, k) { back += '<path d="' + L.sd[k] + '" ' + (k === 1 ? S.stroke(pal, 'quiet', 1.1 * lw, 0.95) : S.stroke(pal, 'faint', 0.8 * lw, 0.9)) + '/>'; });
      L.beadP.forEach(function (p) { back += S.dot(p[0], p[1], m.narrow ? 1.3 : 1.6, pal, 'quiet', 1); });
    });
    var end = [m.P[0], m.P[1] + m.fs * 0.12 * 0.9];
    back += S.line(m.J[0], m.J[1], end[0], end[1], pal, 'quiet', 1);
    return back;
  }
  function joinGroups(m, s, pal) {
    var t = s.t, lw = m.narrow ? 0.9 : 1, groups = [];
    m.lines.forEach(function (L, i) {
      var it = [], u = ease((t - STARTS[i]) / (ARRIVE - STARTS[i]));
      // points along the line, lit once the pulse has passed them (over the dim ones in back)
      L.beads.forEach(function (b, j) { if (u >= b) it.push(dotI('b' + j, L.beadP[j][0], L.beadP[j][1], m.narrow ? 1.5 : 1.9, pal, 'ink', 0.85)); });
      if (u > 0) {
        // what the pulse has lit so far
        L.strands.forEach(function (st, k) {
          it.push({ k: 's' + k, tag: 'path', a: withA({ d: L.sd[k], pathLength: 1, 'stroke-dasharray': '1 2', 'stroke-dashoffset': Math.round((1 - u) * 1e5) / 1e5 },
            strokeA(pal, k === 1 ? 'read' : 'soft', (k === 1 ? 1.25 : 0.8) * lw, k === 1 ? 0.95 : 0.55)) });
        });
        // its head, until it reaches the join
        if (t < ARRIVE) {
          var hp = cut(L.centre, L.cum, u), h = hp[hp.length - 1];
          var tail = cut(L.centre, L.cum, Math.max(0, u - 0.06)).length - 1, tp = hp.slice(Math.max(0, tail - 1));
          if (tp.length > 1) it.push({ k: 'tail', tag: 'path', a: withA({ d: polyD(tp) }, strokeA(pal, 'ink', 2 * lw, 0.9)) });
          lightI('head', h[0], h[1], m.narrow ? 2.6 : 3.4, pal, i === 1 ? 'peri' : 'mint', 1, it);
        }
      }
      groups.push({ k: 'l' + i, items: it });
    });
    // the one line from the join to the full stop
    var it2 = [], stem = clamp((t - ARRIVE) / (JOINED - ARRIVE), 0, 1);
    var end = [m.P[0], m.P[1] + m.fs * 0.12 * 0.9];
    if (stem > 0) {
      var y = m.J[1] + (end[1] - m.J[1]) * stem;
      it2.push({ k: 'stem', tag: 'line', a: withA({ x1: n(m.J[0]), y1: n(m.J[1]), x2: n(end[0]), y2: n(y) }, strokeA(pal, 'ink', 1.7 * lw, 0.95)) });
      if (stem < 1) lightI('sh', end[0], y, m.narrow ? 2.6 : 3.4, pal, 'mint', 1, it2);
    }
    // the point: two rings open from the full stop and fade; what stays is the lit line into it
    if (t >= JOINED) {
      var e = clamp((t - JOINED) / (END - JOINED - 0.2), 0, 1), r = m.ring;
      if (e < 1) it2.push(ringI('r1', m.P[0], m.P[1], r + m.fs * (m.narrow ? 0.9 : 0.8) * ease(e), pal, 'mint', 1.1, (1 - e) * 0.9));
      var e2 = clamp(e * 1.25 - 0.25, 0, 1);
      if (e2 > 0 && e2 < 1) it2.push(ringI('r2', m.P[0], m.P[1], r + m.fs * (m.narrow ? 0.5 : 0.42) * ease(e2), pal, 'peri', 0.9, (1 - e2) * 0.7));
      if (pal.glow) it2.push(dotI('ed', end[0], end[1], 2.6, pal, 'mint', 0.9));
    }
    if (m.dot) it2.push(dotI('dot', m.P[0], m.P[1], m.fs * 0.075, pal, 'ink'));
    groups.push({ k: 'p', items: it2 });
    return groups;
  }
  function joinLabelRole(s, i) { return ease((s.t - STARTS[i]) / 0.3) > 0.5 ? 'soft' : 'quiet'; }
  function joinDraw(m, s, pal) {
    var labels = '';
    m.labels.forEach(function (lb, i) {
      labels += S.text(lb[0], lb[1], NAMES[i], pal, joinLabelRole(s, i), { size: m.narrow ? 13 : 15, anchor: lb[2] });
    });
    return { back: joinBack(m, pal), front: keyedHTML(joinGroups(m, s, pal)), labels: labels };
  }
  var joinCache = {};
  function joinUpdate(m, s, ctx) {
    var pal = ctx.pal;
    keyedApply(ctx.front, joinCache, joinGroups(m, s, pal));
    if (joinCache.labRoot !== ctx.labels) { joinCache.labRoot = ctx.labels; joinCache.lab = ctx.labels.querySelectorAll('text'); joinCache.labRole = []; }
    for (var i = 0; i < joinCache.lab.length; i++) {
      var r = joinLabelRole(s, i);
      if (joinCache.labRole[i] === r) continue;
      var c = pal[r], o = c[1];
      joinCache.lab[i].setAttribute('fill', c[0]);
      if (o < 0.999) joinCache.lab[i].setAttribute('fill-opacity', n(o)); else joinCache.lab[i].removeAttribute('fill-opacity');
      joinCache.labRole[i] = r;
    }
    syncDesc(ctx, joinCache, joinDescribe(m, s));
  }
  function joinDescribe(m, s) {
    var d = 'Three lines of light, labelled investors, engineers and research partners, ' + (m.narrow ? 'come in from the left and right edges of the screen under the title and rise' : 'come in from the left edge, the bottom edge and the right edge of the screen and rise') + ' toward the full stop at the end of the title. ';
    if (s.t <= 0.01) return d + 'All three are drawn in quiet grey, with small points along them.';
    if (s.t < ARRIVE) return d + 'Light is running along the three lines toward the point.';
    if (s.t < JOINED) return d + 'The three lines have met and run on as one.';
    return d + 'The three lines have met and run on as one into the full stop, which is lit with a ring of light.';
  }
  var join = P.figure({
    id: 'join', name: 'three-lines-join', title: 'Three lines of light join at one point',
    caption: 'Three lines of light run toward one point and join there.',
    model: makeJoin(JOIN_DEFAULT),
    modelFor: function (box) {
      var g = measureOpen(box);
      if (!g) return makeJoin(JOIN_DEFAULT);
      return makeJoin(g);
    },
    initialState: function () { return { t: 0 }; },
    stillState: function () { return { t: END }; },
    // after the reader has pressed the figure, the light runs on from where it is to the end
    tick: function (m, s, dt) { return { t: Math.min(END, s.t + dt * (s.t < ARRIVE ? 0.36 : 0.62)) }; },
    settled: function (m, s) { return s.t >= END; },
    draw: joinDraw,
    update: joinUpdate,
    describe: joinDescribe,
    handle: function (m) { return m.P; },
    // the whole story, by itself, once the page has opened: the three faint lines, the light running
    // along them toward the point, the meeting, the one line rising into the full stop, its rings
    // (about 11.5 s in all, so the eye can follow each line)
    sequence: [
      { dur: 1200, tick: false },
      { dur: 5800, tick: false, to: { t: ARRIVE }, ease: 'linear' },
      { dur: 800, tick: false },
      { dur: 1300, tick: false, to: { t: JOINED }, ease: 'out' },
      { dur: 1900, tick: false, to: { t: END }, ease: 'out' },
      { dur: 500, tick: false }
    ],
    controls: [],
    keys: {
      ArrowRight: function (m, s) { return { t: Math.min(END, s.t + 0.08) }; },
      ArrowLeft: function (m, s) { return { t: Math.max(0, s.t - 0.08) }; },
      Home: function () { return { t: 0 }; },
      End: function () { return { t: END }; }
    },
    keysLabel: 'Left and right arrow keys move the light along the lines; Home and End go to the start and the end.'
  });

  /* ================================================================== */
  /* 2. Research partners: a pulse crosses between two networks          */
  /* ================================================================== */
  // Left (or top on a phone): an irregular network with curved, branching links, labelled brain.
  // Right (or bottom): a regular lattice with straight links, labelled machine. Two parallel
  // lines join them; one carries a pulse from the brain to the machine, the other carries one back.
  // A pulse spreads from its source along the links, lighting each point as it arrives.
  var SPEED = 300, FADE = 420;
  function makeNets(narrow) {
    var W = narrow ? 700 : 1400, H = narrow ? 1180 : 640, rng = P.mulberry(11);
    var nodes = [], edges = [];
    // the brain: points in a lobed outline, each linked to its near neighbours by curved links
    var bc = narrow ? [350, 290] : [330, 320], br = narrow ? [300, 238] : [262, 252], minD = narrow ? 60 : 54;
    for (var tries = 0; tries < 4000 && nodes.length < (narrow ? 40 : 46); tries++) {
      var a = rng() * Math.PI * 2, rr = Math.sqrt(rng());
      var lobe = 1 + 0.13 * Math.sin(3 * a + 0.7) + 0.07 * Math.sin(5 * a + 2.1);
      var x = bc[0] + Math.cos(a) * br[0] * rr * lobe * 0.96, y = bc[1] + Math.sin(a) * br[1] * rr * lobe * 0.92;
      if (nodes.some(function (q) { return Math.hypot(q.x - x, q.y - y) < minD; })) continue;
      nodes.push({ x: x, y: y, side: 0 });
    }
    var nb = nodes.length;
    function addEdge(a, b, kind, pts) {
      if (edges.some(function (e) { return (e.a === a && e.b === b) || (e.a === b && e.b === a); })) return;
      if (!pts) pts = [[nodes[a].x, nodes[a].y], [nodes[b].x, nodes[b].y]];
      edges.push({ a: a, b: b, kind: kind, pts: pts, cum: lengths(pts) });
    }
    function curved(a, b, bend) {
      var A = nodes[a], B = nodes[b], mx = (A.x + B.x) / 2, my = (A.y + B.y) / 2, dx = B.x - A.x, dy = B.y - A.y;
      var cx = mx - dy * bend, cy = my + dx * bend, pts = [];
      for (var i = 0; i <= 10; i++) { var u = i / 10, v = 1 - u; pts.push([v * v * A.x + 2 * v * u * cx + u * u * B.x, v * v * A.y + 2 * v * u * cy + u * u * B.y]); }
      return pts;
    }
    for (var i = 0; i < nb; i++) {
      var near = [];
      for (var j = 0; j < nb; j++) if (j !== i) near.push([Math.hypot(nodes[i].x - nodes[j].x, nodes[i].y - nodes[j].y), j]);
      near.sort(function (p, q) { return p[0] - q[0]; });
      var k = rng() < 0.45 ? 3 : 2;
      for (var m = 0; m < k; m++) if (near[m][0] < minD * 2.3) addEdge(i, near[m][1], 'brain', curved(i, near[m][1], (rng() - 0.5) * 0.42));
    }
    // keep the brain in one piece
    (function connect() {
      for (var guard = 0; guard < 40; guard++) {
        var seen = [0], st = [0], vis = {}; vis[0] = 1;
        while (st.length) { var c = st.pop(); edges.forEach(function (e) { var o = e.a === c ? e.b : e.b === c ? e.a : -1; if (o >= 0 && !vis[o]) { vis[o] = 1; seen.push(o); st.push(o); } }); }
        if (seen.length >= nb) return;
        var best = null;
        for (var p = 0; p < nb; p++) if (vis[p]) for (var q = 0; q < nb; q++) if (!vis[q]) { var d = Math.hypot(nodes[p].x - nodes[q].x, nodes[p].y - nodes[q].y); if (!best || d < best[0]) best = [d, p, q]; }
        addEdge(best[1], best[2], 'brain', curved(best[1], best[2], 0.12));
      }
    })();
    // the machine: a regular lattice, straight links
    var R = narrow ? 6 : 7, C = narrow ? 8 : 8;
    var x0 = narrow ? 70 : 860, x1 = narrow ? 630 : 1336, y0 = narrow ? 760 : 92, y1 = narrow ? 1110 : 548;
    var dx = (x1 - x0) / (C - 0.5), dy = (y1 - y0) / (R - 1), base = nodes.length;
    for (var r = 0; r < R; r++) for (var c2 = 0; c2 < C; c2++) nodes.push({ x: x0 + c2 * dx + (r % 2 ? dx / 2 : 0), y: y0 + r * dy, side: 1, r: r, c: c2 });
    function at(r, c) { return (r < 0 || r >= R || c < 0 || c >= C) ? -1 : base + r * C + c; }
    for (r = 0; r < R; r++) for (c2 = 0; c2 < C; c2++) {
      var me = at(r, c2);
      if (at(r, c2 + 1) >= 0) addEdge(me, at(r, c2 + 1), 'machine');
      var dl = r % 2 ? at(r + 1, c2) : at(r + 1, c2 - 1), dr = r % 2 ? at(r + 1, c2 + 1) : at(r + 1, c2);
      if (dl >= 0) addEdge(me, dl, 'machine');
      if (dr >= 0) addEdge(me, dr, 'machine');
    }
    // the two lines between them
    var bA = 0, mA;
    for (i = 1; i < nb; i++) if (narrow ? nodes[i].y > nodes[bA].y : nodes[i].x > nodes[bA].x) bA = i;
    mA = narrow ? at(0, Math.floor(C / 2) - 1) : at(Math.floor(R / 2), 0);
    var A = nodes[bA], B = nodes[mA], bridges = [];
    [-1, 1].forEach(function (sgn) {
      var pts = [], off = 7 * sgn;
      for (var i2 = 0; i2 <= 48; i2++) {
        var u = i2 / 48, s3 = u * u * (3 - 2 * u);
        var px = narrow ? A.x + (B.x - A.x) * s3 : A.x + (B.x - A.x) * u, py = narrow ? A.y + (B.y - A.y) * u : A.y + (B.y - A.y) * s3;
        var w = Math.sin(Math.PI * u); // apart in the middle, together at the ends
        pts.push(narrow ? [px + off * w, py] : [px, py + off * w]);
      }
      bridges.push(pts);
    });
    edges.push({ a: bA, b: mA, kind: 'to', pts: bridges[0], cum: lengths(bridges[0]) });
    edges.push({ a: mA, b: bA, kind: 'back', pts: bridges[1], cum: lengths(bridges[1]) });
    // each link's path text both ways, made once (a pulse may run a link either way)
    edges.forEach(function (e) { e.fd = polyD(e.pts); e.rpts = e.pts.slice().reverse(); e.rcum = lengths(e.rpts); e.rd = polyD(e.rpts); });
    // the sources the page uses on its own: the far side of the brain, the far side of the machine
    var bS = 0, mS = base;
    for (i = 1; i < nb; i++) if (narrow ? nodes[i].y < nodes[bS].y : nodes[i].x < nodes[bS].x) bS = i;
    mS = narrow ? at(R - 1, Math.floor(C / 2)) : at(Math.floor(R / 2), C - 1);
    var model = { key: narrow ? 'narrow' : 'wide', view: { w: W, h: H }, narrow: narrow, nodes: nodes, edges: edges, nb: nb, bA: bA, mA: mA, bS: bS, mS: mS,
      labels: narrow ? [[bc[0], bc[1] + br[1] + 54, 'brain'], [350, y1 + 54, 'machine']] : [[bc[0], 618, 'brain'], [(x0 + x1) / 2 + dx / 4, 618, 'machine']], dist: {} };
    // the moment the two pulses cross on the two lines: the return leaves so that they meet halfway
    var f = distFrom(model, bS, 'to'), b = distFrom(model, mS, 'back'), Lb = edges[edges.length - 2].cum[48];
    var tf = (f[bA] + Lb / 2) / SPEED, tb = (b[mA] + Lb / 2) / SPEED;
    model.auto = [{ src: bS, way: 'to', t0: Math.max(0, tb - tf) + 0.35, auto: true }, { src: mS, way: 'back', t0: Math.max(0, tf - tb) + 0.35, auto: true }];
    model.cross = Math.max(tf, tb) + 0.35;
    // the sequence's last picture: both pulses across and spreading through the other network
    model.tEnd = model.cross + 1.15;
    return model;
  }
  // shortest distance along the links from a source; a pulse uses only its own line between the two
  function distFrom(m, src, way) {
    var key = src + ':' + way; if (m.dist[key]) return m.dist[key];
    var N = m.nodes.length, d = new Array(N).fill(Infinity), done = new Array(N).fill(false); d[src] = 0;
    var adj = m.adj || (m.adj = (function () {
      var a = []; for (var i = 0; i < N; i++) a.push([]);
      m.edges.forEach(function (e, k) { a[e.a].push(k); a[e.b].push(k); }); return a;
    })());
    for (var it = 0; it < N; it++) {
      var u = -1; for (var i = 0; i < N; i++) if (!done[i] && (u < 0 || d[i] < d[u])) u = i;
      if (u < 0 || d[u] === Infinity) break; done[u] = true;
      adj[u].forEach(function (k) {
        var e = m.edges[k];
        if (e.kind === 'to' && (way !== 'to' || e.a !== u)) return;
        if (e.kind === 'back' && (way !== 'back' || e.a !== u)) return;
        var o = e.a === u ? e.b : e.a, L = e.cum[e.cum.length - 1];
        if (d[u] + L < d[o]) d[o] = d[u] + L;
      });
    }
    m.dist[key] = d; return d;
  }
  function waveSpan(m, w) { var d = distFrom(m, w.src, w.way), mx = 0; d.forEach(function (v) { if (v < Infinity && v > mx) mx = v; }); return mx; }
  // The two networks and the two lines never move: they are drawn once in back. Each pulse is a
  // set of keyed items (its links, its lit points, its heads); a frame changes only what moved.
  function netsBack(m, pal) {
    var back = '', lw = m.narrow ? 1.3 : 1;
    m.edges.forEach(function (e) {
      var st = e.kind === 'brain' ? S.stroke(pal, 'faint', 1 * lw, 0.95) : e.kind === 'machine' ? S.stroke(pal, 'faint', 0.9 * lw, 0.85) : S.stroke(pal, 'quiet', 1 * lw, 0.75);
      back += '<path d="' + e.fd + '" ' + st + '/>';
    });
    m.nodes.forEach(function (q) { back += S.dot(q.x, q.y, q.side ? 2 * lw : 2.4 * lw, pal, 'quiet', 0.9); });
    return back;
  }
  function waveKey(w) { return (w.way === 'to' ? 't' : 'b') + w.src + '_' + Math.round(w.t0 * 1000); }
  function netsGroups(m, s, pal) {
    var lw = m.narrow ? 1.3 : 1, groups = [];
    s.waves.forEach(function (w, wi) {
      var d = (s.t - w.t0) * SPEED; if (d <= 0) return;
      var role = w.way === 'to' ? 'mint' : 'peri', dist = distFrom(m, w.src, w.way), key = waveKey(w) + '_' + wi;
      var links = [], lit = [], heads = [];
      m.edges.forEach(function (e, ei) {
        if ((e.kind === 'to' || e.kind === 'back') && e.kind !== w.way) return;
        var da = dist[e.a], db = dist[e.b]; if (da === Infinity && db === Infinity) return;
        var L = e.cum[e.cum.length - 1], fwd = da <= db, lo = fwd ? da : db;
        if (e.kind === w.way && !fwd) return;
        var f = (d - lo) / L; if (f <= 0) return;
        var I = f < 1 ? 1 : Math.exp(-(d - lo - L) / FADE);
        var bridge = e.kind === w.way, a = strokeA(pal, role, (bridge ? 1.6 : 1.2) * lw, 0.07 + 0.88 * I);
        if (f < 1) {
          var seg = cut(fwd ? e.pts : e.rpts, fwd ? e.cum : e.rcum, f), h = seg[seg.length - 1];
          a.d = polyD(seg);
          heads.push(dotI('h' + ei, h[0], h[1], (bridge ? 3.4 : 2.3) * lw, pal, 'ink', 0.95));
          if (bridge) lightI('hl' + ei, h[0], h[1], 3.2 * lw, pal, role, 1, heads);
        } else a.d = fwd ? e.fd : e.rd;
        links.push({ k: 'e' + ei, tag: 'path', a: a });
      });
      m.nodes.forEach(function (q, i) {
        var dd = dist[i]; if (dd === Infinity || d < dd) return;
        var I = Math.exp(-(d - dd) / (FADE * 0.7));
        if (I > 0.04) lightI('n' + i, q.x, q.y, (q.side ? 2.4 : 2.8) * lw, pal, role, I, lit);
      });
      groups.push({ k: key + 'e', items: links }, { k: key + 'n', items: lit }, { k: key + 'h', items: heads });
    });
    return groups;
  }
  function netsDraw(m, s, pal) {
    var labels = '';
    m.labels.forEach(function (lb) { labels += S.text(lb[0], lb[1], lb[2], pal, 'soft', { size: m.narrow ? 26 : 16, anchor: 'middle' }); });
    return { back: netsBack(m, pal), front: keyedHTML(netsGroups(m, s, pal)), labels: labels };
  }
  var netsCache = {};
  function netsUpdate(m, s, ctx) {
    keyedApply(ctx.front, netsCache, netsGroups(m, s, ctx.pal));
    syncDesc(ctx, netsCache, netsDescribe(m, s));
  }
  // where a pulse is: 0 not left yet, 1 spreading through the network it started in, 2 on its line
  // between the two, 3 across and spreading through the other network, 4 across and spread
  function wavePhase(m, s, w) {
    var dd = (s.t - w.t0) * SPEED; if (dd <= 0) return 0;
    var dist = distFrom(m, w.src, w.way), from = w.way === 'to' ? m.bA : m.mA, to = w.way === 'to' ? m.mA : m.bA;
    if (dd < dist[from]) return 1;
    if (dd < dist[to]) return 2;
    return dd < waveSpan(m, w) ? 3 : 4;
  }
  var PHASE_TEXT = {
    to: ['', 'a pulse is spreading through the brain toward the line to the machine', 'a pulse is running along the line from the brain to the machine',
      'a pulse has crossed from the brain to the machine and is spreading through it', 'a pulse has crossed from the brain to the machine'],
    back: ['', 'a pulse is spreading through the machine toward the line to the brain', 'a pulse is running along the line from the machine to the brain',
      'a pulse has crossed from the machine to the brain and is spreading through it', 'a pulse has crossed from the machine to the brain']
  };
  function netsDescribe(m, s) {
    var d = 'On the ' + (m.narrow ? 'top' : 'left') + ', a network of points joined by curved, branching links, labelled brain. On the ' + (m.narrow ? 'bottom' : 'right') +
      ', a regular lattice of points joined by straight links, labelled machine. Two lines join them. ';
    var said = [];
    s.waves.forEach(function (w) {
      var tx = PHASE_TEXT[w.way][wavePhase(m, s, w)];
      if (tx && said.indexOf(tx) < 0) said.push(tx);
    });
    if (!said.length) return d + 'Every point and link is drawn in quiet grey.';
    var all = said.length === 1 ? said[0] : said.length === 2 ? said[0] + ', and ' + said[1] : said.join('; ');
    return d + all.charAt(0).toUpperCase() + all.slice(1) + '.';
  }
  function netsEnd(m, s) {
    var e = 0; s.waves.forEach(function (w) { e = Math.max(e, w.t0 + (waveSpan(m, w) + FADE * 2.2) / SPEED); }); return e;
  }
  // a new pulse from a point, and only that pulse: the automatic pair is cleared so the reader sees
  // exactly what their own action sent (their earlier pulses still spreading are kept);
  // under reduced motion it is shown already spread
  function clockS() { return (window.performance ? performance.now() : Date.now()) / 1000; }
  function send(m, s, src, way) {
    var waves = s.waves.filter(function (w) { return !w.auto && (s.t - w.t0) * SPEED < waveSpan(m, w) + FADE * 2.2; }).slice(-5);
    // it leaves at once: its first point is lit in the frame the reader asked for it
    var w = { src: src, way: way, t0: s.t - 1 / 60 };
    waves.push(w);
    // the reader's pulses run on the clock (live is when t was 0), so the page's driver below and
    // the figure's own tick, should both run, agree on every frame
    var ns = { t: s.t, waves: waves, live: clockS() - s.t };
    if (P.reducedMotion()) { ns.t = s.t + (waveSpan(m, w) + FADE * 0.5) / SPEED; ns.live = 0; } // a still: the pulse has spread
    else setTimeout(drive, 0);
    return ns;
  }
  // The reader has taken the figure (the kit stops its loop when they press a point or a key):
  // the page carries their pulses on, through the figure's usual drawing, until they have spread.
  var driving = false;
  function drive() {
    if (driving) return;
    driving = true;
    requestAnimationFrame(function frame() {
      var s = nets.state;
      if (nets.sequence !== 'yielded' || !s.live || document.hidden || document.documentElement.classList.contains('k-leaving')) { driving = false; return; }
      var ns = { t: clockS() - s.live, waves: s.waves, live: s.live };
      nets.set(ns, { quiet: true });
      if (netsModel && ns.t >= netsEnd(netsModel, ns)) { driving = false; return; }
      requestAnimationFrame(frame);
    });
  }
  var picked = null, netsModel = null;
  function seqModel() { return netsModel || (netsModel = makeNets(false)); }
  // The pulses run slower than their own speed while the sequence plays, so that the whole
  // sequence (holds included) lasts about 11 s and the eye can follow both pulses.
  var SEQ_MS = 11000, HOLDS_MS = 1000 + 1200 + 1000;
  function slow() { return clamp((SEQ_MS - HOLDS_MS) / (seqModel().tEnd * 1000), 1.25, 4); }
  // The quiet state (no pulse) is where the figure starts and where Reset returns it. Played from
  // quiet (its one unattended run when it first comes into view, or Play), it sends the automatic
  // pair: one pulse each way, meeting halfway. A button, a key or a click sends only its own pulse.
  var nets = P.figure({
    id: 'both', name: 'brain-and-machine', title: 'A pulse between a brain-like network and a machine-like network',
    caption: 'A pulse crosses from a brain-like network to a machine-like network, and another crosses back.',
    model: makeNets(false),
    modelFor: function (box) { netsModel = makeNets(box.width <= 640); return netsModel; },
    initialState: function () { return { t: 0, waves: [] }; },
    stillState: function (m) { return { t: m.tEnd, waves: m.auto.slice() }; },
    // after the reader has taken the figure: the pulses go on spreading (the pair, from quiet)
    tick: function (m, s, dt) {
      if (!s.waves.length) return { t: 0, waves: m.auto.slice() };
      if (s.live) return { t: clockS() - s.live, waves: s.waves, live: s.live };
      return { t: s.t + dt, waves: s.waves };
    },
    settled: function (m, s) { return s.waves.length > 0 && s.t >= netsEnd(m, s); },
    // the whole story, by itself, once the figure is well in view: both networks quiet; a pulse
    // leaves the far side of the brain and, a moment later, one leaves the far side of the machine;
    // they meet halfway on the two lines; each crosses and spreads into the other network
    sequence: [
      { dur: 1000, tick: false },
      { dur: 0, tick: false, 'do': function (m) { return { t: 0, waves: m.auto.slice() }; } },
      // the pulses run at a little under their own speed, so the eye can follow them
      { get dur() { return seqModel().cross * 1000 * slow(); }, tick: false, to: function (m) { return { t: m.cross }; }, ease: 'linear' },
      { dur: 1200, tick: false },
      { get dur() { return (seqModel().tEnd - seqModel().cross) * 1000 * slow(); }, tick: false, to: function (m) { return { t: m.tEnd }; }, ease: 'linear' },
      { dur: 1000, tick: false }
    ],
    draw: netsDraw,
    update: netsUpdate,
    describe: netsDescribe,
    handle: function (m) { var a = m.nodes[m.bA], b = m.nodes[m.mA]; return [(a.x + b.x) / 2, (a.y + b.y) / 2]; },
    controls: [],
    drag: {
      pick: function (m, s, p) {
        var best = -1, bd = m.narrow ? 46 : 30;
        m.nodes.forEach(function (q, i) { var d = Math.hypot(q.x - p[0], q.y - p[1]); if (d < bd) { bd = d; best = i; } });
        picked = best >= 0 ? best : null;
        return best >= 0;
      },
      move: function (m, s) { return s; },
      end: function (m, s) {
        if (picked == null) return s;
        var i = picked; picked = null;
        return send(m, s, i, m.nodes[i].side ? 'back' : 'to');
      }
    },
    keys: {
      ArrowRight: function (m, s) { return send(m, s, m.narrow ? m.bS : m.bS, 'to'); },
      ArrowDown: function (m, s) { return send(m, s, m.bS, 'to'); },
      ArrowLeft: function (m, s) { return send(m, s, m.mS, 'back'); },
      ArrowUp: function (m, s) { return send(m, s, m.mS, 'back'); }
    },
    keysLabel: 'Right or down arrow sends a pulse from the brain to the machine; left or up arrow sends one back.'
  });

  /* ================================================================== */
  /* Page: the words arrive; the research figure's one unattended run    */
  /* ================================================================== */
  // (the opening's lines find the title's full stop by measuring it; the kit measures again once
  // the fonts are in, and on a resize only when the opening's box changed size)
  P.ready(function () {
    var items = document.querySelectorAll('.ab-rv');
    if (P.reducedMotion() || !('IntersectionObserver' in window)) { items.forEach(function (e) { e.classList.add('is-in'); }); return; }
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); } });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
    items.forEach(function (e) { io.observe(e); });
  });
})(window.Psyche);
