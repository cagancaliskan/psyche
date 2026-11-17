
function mulberry(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hash3(i, j, k) {
  let h = (Math.imul(i, 374761393) + Math.imul(j, 668265263) + Math.imul(k, 1440662683)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967295;
}
function vnoise(x, y, z) {
  const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
  const xf = x - xi, yf = y - yi, zf = z - zi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf), w = zf * zf * (3 - 2 * zf);
  const l = (a, b, t) => a + (b - a) * t;
  const c000 = hash3(xi, yi, zi), c100 = hash3(xi + 1, yi, zi), c010 = hash3(xi, yi + 1, zi), c110 = hash3(xi + 1, yi + 1, zi);
  const c001 = hash3(xi, yi, zi + 1), c101 = hash3(xi + 1, yi, zi + 1), c011 = hash3(xi, yi + 1, zi + 1), c111 = hash3(xi + 1, yi + 1, zi + 1);
  return l(l(l(c000, c100, u), l(c010, c110, u), v), l(l(c001, c101, u), l(c011, c111, u), v), w) * 2 - 1;
}
function fbm(x, y, z) {
  return vnoise(x, y, z) * 0.62 + vnoise(x * 2.03 + 11.1, y * 2.03 - 3.7, z * 2.03 + 5.3) * 0.28 + vnoise(x * 4.1 - 7.2, y * 4.1 + 1.9, z * 4.1 + 9.4) * 0.1;
}
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const gauss = (rng) => { let s = 0; for (let i = 0; i < 4; i++) s += rng(); return (s - 2) / 0.577; };

const WHITE = [0.9, 0.93, 1.0];
const MINT = [0.37, 0.94, 0.78];
const PERI = [0.54, 0.64, 1.0];
// pack a horizontal normal (x, z) into one float; 0 means "no normal"
const packN = (nx, nz) => 1 + Math.round((nx * 0.5 + 0.5) * 254) * 256 + Math.round((nz * 0.5 + 0.5) * 254);
const mixc = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

class Cloud {
  constructor(n) {
    this.n = n; this.i = 0;
    this.pos = new Float32Array(n * 3);
    this.col = new Float32Array(n * 3);
    this.aux = new Float32Array(n * 4);
    this.tag = new Float32Array(n); // part of the shape each point belongs to; 0 = ambient dust
    this.g = 1;
  }
  get left() { return this.n - this.i; }
  add(x, y, z, c, size, alpha, param = -10, nrm = 0) {
    if (this.i >= this.n) return false;
    const i = this.i++;
    this.tag[i] = this.g;
    this.pos[i * 3] = x; this.pos[i * 3 + 1] = y; this.pos[i * 3 + 2] = z;
    this.col[i * 3] = c[0]; this.col[i * 3 + 1] = c[1]; this.col[i * 3 + 2] = c[2];
    this.aux[i * 4] = size; this.aux[i * 4 + 1] = alpha; this.aux[i * 4 + 2] = param; this.aux[i * 4 + 3] = nrm;
    return true;
  }
  dust(rng, radius = 11, alpha = 0.16, tint = WHITE) {
    this.g = 0;
    while (this.i < this.n) {
      const u = rng() * 2 - 1, th = rng() * Math.PI * 2, r = radius * Math.cbrt(0.08 + 0.92 * rng());
      const s = Math.sqrt(1 - u * u);
      const c = rng() < 0.25 ? mixc(tint, MINT, 0.5) : rng() < 0.3 ? mixc(tint, PERI, 0.5) : tint;
      // param -99 marks ambient dust: it fades by its own rule and never paints over
      this.add(r * s * Math.cos(th), r * u * 0.7, r * s * Math.sin(th) - 2, c, 0.022 + rng() * 0.03, alpha * (0.4 + rng()), -99);
    }
    return this;
  }
}
// a fixed shuffle, so that drawing any leading fraction of a set is a fair sample of all of it
function shuffleCloud(c, seed) {
  const rng = mulberry(seed), n = c.n, perm = new Uint32Array(n);
  for (let i = 0; i < n; i++) perm[i] = i;
  for (let i = n - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const t = perm[i]; perm[i] = perm[j]; perm[j] = t; }
  const P = (arr, w) => { const o = new Float32Array(arr.length); for (let i = 0; i < n; i++) for (let q = 0; q < w; q++) o[i * w + q] = arr[perm[i] * w + q]; return o; };
  c.pos = P(c.pos, 3); c.col = P(c.col, 3); c.aux = P(c.aux, 4); c.tag = P(c.tag, 1);
  return c;
}

/* sample points along a list of segments, density by length (and weight) */
function sampleSegments(cloud, rng, segs, count, style) {
  let total = 0;
  for (const s of segs) { s.len = Math.hypot(s.b[0] - s.a[0], s.b[1] - s.a[1], s.b[2] - s.a[2]); total += s.len * (s.w ?? 1); }
  const acc = []; let run = 0;
  for (const s of segs) { run += s.len * (s.w ?? 1); acc.push(run); }
  for (let k = 0; k < count && cloud.left > 0; k++) {
    const r = rng() * total;
    let lo = 0, hi = acc.length - 1;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (acc[mid] < r) lo = mid + 1; else hi = mid; }
    const s = segs[lo]; const t = rng();
    const rad = s.r0 + (s.r1 - s.r0) * t;
    const ox = gauss(rng) * rad * 0.5, oy = gauss(rng) * rad * 0.5, oz = gauss(rng) * rad * 0.5;
    const x = s.a[0] + (s.b[0] - s.a[0]) * t + ox;
    const y = s.a[1] + (s.b[1] - s.a[1]) * t + oy;
    const z = s.a[2] + (s.b[2] - s.a[2]) * t + oz;
    style(cloud, x, y, z, s, t, rng);
  }
}

/* ------------------------------------------------------------------ */
/* Shape generators                                                     */
/* ------------------------------------------------------------------ */
// The loader orb is a true sphere centred on the brain's centre, in the brain's own frame: its
// points are the brain's points (matched once, in the worker) and travel the short way into it.
const BRAIN_C = [0, 0.12, 0];
const ORB_R = 1.62;
function makeOrb(N) {
  const rng = mulberry(7), c = new Cloud(N);
  const shell = Math.floor(N * 0.62), inner = Math.floor(N * 0.2);
  const ga = Math.PI * (3 - Math.sqrt(5));
  const R0 = ORB_R;
  c.g = 1;
  for (let k = 0; k < shell; k++) {
    const y = 1 - (k / (shell - 1)) * 2, r = Math.sqrt(1 - y * y), th = ga * k + gauss(rng) * 0.04;
    const n = fbm(Math.cos(th) * r * 1.6, y * 1.6, Math.sin(th) * r * 1.6);
    // a round shell: the noise only shades it (bands), it barely moves the radius
    const R = R0 * (1 + n * 0.018) + gauss(rng) * 0.022;
    const band = 0.5 + 0.5 * Math.sin(n * 9 + y * 3);
    const col = rng() < 0.3 ? mixc(MINT, WHITE, 0.3) : rng() < 0.2 ? PERI : WHITE;
    c.add(Math.cos(th) * r * R + BRAIN_C[0], y * R + BRAIN_C[1], Math.sin(th) * r * R + BRAIN_C[2], col, 0.018 + rng() * 0.012, (0.08 + 0.2 * band ** 2) * (0.7 + 0.6 * rng()));
  }
  c.g = 2;
  for (let k = 0; k < inner; k++) {
    const u = rng() * 2 - 1, th = rng() * 6.283, r = R0 * 0.86 * Math.pow(rng(), 0.7), s = Math.sqrt(1 - u * u);
    c.add(r * s * Math.cos(th) + BRAIN_C[0], r * u + BRAIN_C[1], r * s * Math.sin(th) + BRAIN_C[2], mixc(MINT, WHITE, rng() * 0.5), 0.034, 0.03);
  }
  c.dust(rng, 12, 0.1);
  return c;
}

function makeBrain(N) {
  const rng = mulberry(11), c = new Cloud(N);
  const S = 1.3; // overall scale
  const surf = Math.floor(N * 0.74);
  let made = 0, guard = 0;
  // hemispheres: long axis along x (front = +x), height y, width z
  while (made < surf && guard++ < surf * 8) {
    const u = rng() * 2 - 1, th = rng() * Math.PI * 2, s = Math.sqrt(1 - u * u);
    let dx = s * Math.cos(th), dy = u, dz = s * Math.sin(th);
    const side = rng() < 0.5 ? -1 : 1;
    // medial wall flattening: points facing the midline are rare
    if (dz * side < -0.35 && rng() < 0.85) continue;
    let rx = 1.5, ry = 1.22, rz = 0.74;
    let x = dx * rx, y = dy * ry, z = dz * rz;
    // domed crown, rounder frontal lobe, flatter base
    y += 0.1 * Math.max(0, -x) * Math.max(0, dy);
    if (y < 0) y *= 0.8;
    if (x > 0.6 && y < 0) y *= 0.85; // orbital surface of the frontal lobe
    // temporal lobe: bulge low-front-lateral
    const tl = Math.exp(-((x - 0.25) ** 2) / 0.35 - ((y + 0.55) ** 2) / 0.08);
    z += side * 0.12 * tl * Math.abs(dz);
    y -= 0.12 * tl;
    // occipital pole tapering
    if (x < -1.1) { y *= 0.92; }
    // sylvian fissure: a groove running up and back from the temporal pole
    const sylv = Math.abs(y - (-0.12 + 0.32 * (0.6 - x) * 0.5)) ;
    const inSylv = x > -0.6 && x < 1.0 && Math.abs(dz) > 0.35 && sylv < 0.06;
    // folds
    const px = x * 1.5, py = y * 1.5, pz = z * 1.5 + side * 7.0;
    const wx = vnoise(px * 0.8 + 3.1, py * 0.8, pz * 0.8) * 0.6;
    const wy = vnoise(px * 0.8, py * 0.8 + 8.3, pz * 0.8) * 0.6;
    const n = fbm(px + wx, py + wy, pz);
    // labyrinth of gyri: contour lines of a warped field. Only a thin band near each
    // zero crossing is emptied, so sulci read as fine dark grooves between full gyri.
    const w = Math.abs(Math.sin(n * 11.0));
    let accept = 0.03 + 0.97 * smooth(0.06, 0.34, w);
    if (inSylv) accept *= 0.04;
    if (rng() > accept) continue;
    const rad = 1 + 0.05 * (w - 0.6);
    x *= rad; y *= rad; z *= rad;
    // light from the upper front, toward the viewer: gives the folds a body
    const nl = Math.max(0, dx * 0.35 + dy * 0.55 + dz * side * 0.2 + 0.45);
    z += side * 0.6;
    // a region of activity on the parietal surface: mint, rippling
    const ax = x - 0.15, ay = y - 0.62, az = z - side * 0.6;
    const act = side > 0 ? Math.exp(-(ax * ax + ay * ay * 1.4) / 0.2) * (dz > 0.1 ? 1 : 0) : 0;
    if (act > 0.25 && rng() < act * 0.85) {
      c.add(x * S, y * S + 0.1, z * S, mixc(MINT, WHITE, 0.15 * rng()), 0.026, 0.3 + 0.3 * w, 1 + Math.hypot(ax, ay), packN(dx, dz));
      made++; continue;
    }
    const col = mixc(mixc(WHITE, [0.72, 0.82, 1.0], rng() * 0.4), MINT, w * 0.22 * rng());
    c.add(x * S, y * S + 0.1, z * S, col, 0.02 + rng() * 0.01, (0.12 + w * 0.42) * (0.45 + 0.75 * nl), -10, packN(dx, dz));
    made++;
  }
  // cerebellum: back-bottom, finely striated
  c.g = 2;
  const cb = Math.floor(N * 0.07);
  for (let k = 0, g = 0; k < cb && g < cb * 6; g++) {
    const u = rng() * 2 - 1, th = rng() * Math.PI * 2, s = Math.sqrt(1 - u * u);
    const x = -1.02 + s * Math.cos(th) * 0.52, y = -0.6 + u * 0.34, z = s * Math.sin(th) * 0.84;
    const band = Math.abs(Math.sin((y + 0.06 * Math.sin(z * 3) + 0.04 * x) * 52));
    if (rng() > 0.05 + 0.95 * band ** 3) continue;
    if (x > -0.6 && y > -0.5) continue;
    c.add(x * S, y * S + 0.1, z * S, mixc(WHITE, MINT, 0.25), 0.02, 0.2 + 0.1 * (1 - u), -10, packN(s * Math.cos(th), s * Math.sin(th)));
    k++;
  }
  // brainstem: short, tapered, soft (a gaussian body, not a hollow tube)
  c.g = 3;
  const bs = Math.floor(N * 0.02);
  for (let k = 0; k < bs; k++) {
    const t = Math.pow(rng(), 0.8);
    const x = -0.36 - t * 0.2, y = -0.58 - t * 0.62;
    const r = (0.17 - t * 0.07) * Math.abs(gauss(rng)) * 0.7;
    const th = rng() * 6.283;
    c.add((x + Math.cos(th) * r) * S, y * S + 0.1, Math.sin(th) * r * 1.2 * S, mixc(WHITE, MINT, 0.2), 0.022, 0.2 * (1 - t * 0.85));
  }
  // inner light: a faint glow inside, so the brain has a luminous core
  c.g = 4;
  const inner = Math.floor(N * 0.035);
  for (let k = 0; k < inner; k++) {
    const x = gauss(rng) * 0.55, y = gauss(rng) * 0.36, z = gauss(rng) * 0.42;
    c.add(x * S, y * S + 0.2, z * S, mixc(MINT, PERI, rng() * 0.25), 0.07, 0.035);
  }
  // the cell about to fire, inside the active region
  c.g = 5;
  for (let k = 0; k < 420; k++) {
    const r = Math.abs(gauss(rng)) * 0.05;
    const th = rng() * 6.283, u = rng() * 2 - 1, s = Math.sqrt(1 - u * u);
    c.add((0.2 + r * s * Math.cos(th)) * S, (0.68 + r * u) * S + 0.1, (1.24 + r * s * Math.sin(th)) * S, MINT, 0.032, 0.6, 1);
  }
  c.dust(rng, 12, 0.1);
  // in: its centre (the orb becomes it in place); out: the cell about to fire (the camera dives into it)
  return { cloud: c, meta: { center: BRAIN_C, out: [0.2 * S, 0.68 * S + 0.1, 1.24 * S] } };
}

function neuronSegs(rng, origin, scale, primaries, depthMax, axonDir) {
  const segs = [];
  const norm = (v) => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };
  const rv = () => [gauss(rng), gauss(rng), gauss(rng)];
  function branch(p, dir, len, rad, depth, w) {
    const steps = 7; let cur = p, d = dir;
    for (let s = 0; s < steps; s++) {
      const r = rv(); d = norm([d[0] + r[0] * 0.22, d[1] + r[1] * 0.22, d[2] + r[2] * 0.22]);
      const nx = [cur[0] + d[0] * len / steps, cur[1] + d[1] * len / steps, cur[2] + d[2] * len / steps];
      segs.push({ a: cur, b: nx, r0: rad, r1: rad * 0.94, w, depth });
      cur = nx; rad *= 0.94;
    }
    if (depth < depthMax) {
      const kids = rng() < 0.25 ? 3 : 2;
      for (let k = 0; k < kids; k++) {
        const r = rv();
        branch(cur, norm([d[0] + r[0] * 0.75, d[1] + r[1] * 0.75, d[2] + r[2] * 0.75]), len * (0.62 + rng() * 0.2), rad * 0.72, depth + 1, w * 0.85);
      }
    }
  }
  for (let k = 0; k < primaries; k++) {
    const r = rv();
    let d = norm(r); if (axonDir) d = norm([d[0], d[1] + 0.6, d[2]]);
    branch(origin, d, 0.75 * scale * (0.7 + rng() * 0.6), 0.05 * scale, 0, 1);
  }
  if (axonDir) branch(origin, axonDir, 2.6 * scale, 0.035 * scale, depthMax, 0.7);
  return segs;
}

function makeNeurons(N, mobile) {
  const rng = mulberry(23), c = new Cloud(N);
  const somaStyle = (cl, x, y, z) => cl.add(x, y, z, MINT, 0.03, 0.5);
  const neurons = [{ o: [0.2, 0.15, 1.2], s: 1.25, share: 0.34, hero: true }];
  for (let k = 0; k < 13; k++) {
    neurons.push({ o: [(rng() * 2 - 1) * 7, (rng() * 2 - 1) * 3.6, -1.5 - rng() * 9], s: 0.75 + rng() * 0.6, share: 0.034 });
  }
  neurons.push({ o: [-3.9, 1.2, 1.3], s: 0.85, share: 0.05, fg: true });
  neurons.push({ o: [3.6, 1.9, 1.6], s: 0.8, share: 0.045, fg: true });
  let contact = null;
  for (const n of neurons) {
    const count = Math.floor(N * n.share);
    const segs = neuronSegs(rng, n.o, n.s, n.hero ? 7 : 5, n.hero ? 4 : 3, [0.1 * gauss(rng), -1, 0.2 * gauss(rng)]);
    c.g = n.hero ? 1 : 2;
    if (n.hero) {
      // the place where two cells meet: an upper dendrite tip of the hero cell, right of the soma,
      // reached by another cell's axon coming down from above and ending in a small terminal
      let best = -1e9;
      for (const s of segs) {
        if (s.depth < 3) continue;
        const q = s.b;
        const sc = q[1] - 0.8 * Math.abs(q[0] - (n.o[0] + 0.9)) - 0.6 * Math.abs(q[2] - (n.o[2] + 0.2)) - (q[1] > n.o[1] + 2.2 ? 3 : 0);
        if (sc > best) { best = sc; contact = q; }
      }
    }
    const dim = n.fg ? 0.55 : 1; // foreground cells bloom; keep them from clipping
    // soma
    const somaN = Math.floor(count * 0.12);
    for (let k = 0; k < somaN; k++) {
      const u = rng() * 2 - 1, th = rng() * 6.283, s = Math.sqrt(1 - u * u), r = 0.16 * n.s * Math.pow(rng(), 0.35);
      c.add(n.o[0] + r * s * Math.cos(th), n.o[1] + r * u * 1.15, n.o[2] + r * s * Math.sin(th), mixc(MINT, WHITE, rng() * 0.4), 0.03, 0.3 * dim);
    }
    sampleSegments(c, rng, segs, count - somaN, (cl, x, y, z, s) => {
      const near = Math.max(0, 1 - s.depth / 5);
      const tip = s.depth / 4;
      // trunks near-white, branches turning mint toward the tips: the cell reads as alive
      const col = mixc(WHITE, MINT, Math.min(1, 0.15 + tip * 0.7) * (0.5 + 0.5 * rng()));
      cl.add(x, y, z, col, 0.022 + 0.01 * near, (0.18 + 0.18 * near) * dim);
    });
    if (n.hero) {
      // the incoming axon: thin, from above and behind, ending in a bouton on the dendrite tip
      c.g = 3;
      const tip = [contact[0], contact[1] + 0.05, contact[2]];
      const a0 = [tip[0] + 1.1, tip[1] + 2.9, tip[2] - 0.9], a1 = [tip[0] + 0.7, tip[1] + 1.3, tip[2] - 0.2], a2 = [tip[0] + 0.05, tip[1] + 0.55, tip[2]];
      for (let k = 0; k < N * 0.012; k++) {
        const t = rng(), mt = 1 - t;
        const b0 = mt * mt * mt, b1 = 3 * mt * mt * t, b2 = 3 * mt * t * t, b3 = t * t * t;
        const w = 0.016;
        c.add(b0 * a0[0] + b1 * a1[0] + b2 * a2[0] + b3 * tip[0] + gauss(rng) * w,
          b0 * a0[1] + b1 * a1[1] + b2 * a2[1] + b3 * tip[1] + gauss(rng) * w,
          b0 * a0[2] + b1 * a1[2] + b2 * a2[2] + b3 * tip[2] + gauss(rng) * w,
          mixc(WHITE, MINT, 0.2 + 0.6 * t), 0.022, 0.16 + 0.14 * t);
      }
      // the terminal: a small bright bead that pulses softly, the way the brain's active cell did
      for (let k = 0; k < N * 0.004; k++) {
        const r = Math.abs(gauss(rng)) * 0.035;
        const th = rng() * 6.283, u = rng() * 2 - 1, s = Math.sqrt(1 - u * u);
        c.add(tip[0] + r * s * Math.cos(th), tip[1] + 0.02 + r * u, tip[2] + r * s * Math.sin(th), mixc(MINT, WHITE, 0.3), 0.026, 0.45, 1 + r * 4);
      }
    }
  }
  c.dust(rng, 13, 0.1, mixc(WHITE, MINT, 0.25));
  // in: the hero soma (the brain's firing cell opens into it); out: the contact (the dive into the synapse)
  return { cloud: c, meta: { in: neurons[0].o, out: [contact[0], contact[1] + 0.05, contact[2]] } };
}

function makeSynapse(N) {
  // Seen a little from above: the presynaptic bouton on top, the postsynaptic spine head below,
  // a narrow cleft between their flattened faces. Membranes are three layers thick with a packed
  // normal, so the shader lights their rims and lets their faces go glassy; their surface is
  // patchy, like a real membrane studded with proteins. Vesicles are filled, rim-lit spheres at
  // many depths, a few docked, three fused and releasing. The transmitter puffs out of each
  // release site, crosses and lands on a field of receptors that lights mint, and a wave of
  // calcium blooms through the spine head below. The spine head holds its own apparatus.
  const rng = mulberry(31), c = new Cloud(N), kN = N / 78000;
  const tiltX = 0.15, tiltZ = -0.08;
  const cy = Math.cos(tiltX), sy = Math.sin(tiltX), cz = Math.cos(tiltZ), sz = Math.sin(tiltZ);
  const T = (x, y, z) => { const y2 = y * cy - z * sy, z2 = y * sy + z * cy; return [x * cz - y2 * sz, x * sz + y2 * cz, z2]; };
  const OFF = 0.15;
  const put = (x, y, z, col, size, alpha, param = -10, n = null) => {
    const q = T(x, y, z);
    let nrm = 0;
    if (n) { const m = T(n[0], n[1], n[2]); nrm = packN(m[0], m[2]); }
    c.add(q[0], q[1] + OFF, q[2], col, size, alpha, param, nrm);
  };
  const yPre = (x, z) => 0.21 + 0.04 * (x * x + z * z);
  const yPost = (x, z) => -0.21 + 0.04 * (x * x + z * z);
  const nrmz = (v) => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };
  const MEM_O = mixc(WHITE, [0.78, 0.86, 1.0], 0.3), MEM_M = mixc(WHITE, MINT, 0.3), MEM_I = mixc(MINT, WHITE, 0.4);
  // proteins and rafts: the membrane is patchy, not an even stipple
  const patch = (x, y, z) => 0.62 + 0.75 * smooth(-0.25, 0.45, fbm(x * 2.3 + 3.3, y * 2.3, z * 2.3 - 1.7));

  // a membrane: an ellipsoid shell, flattened on one face, in three layers (bright outer, then two inner)
  function membrane(count, C, A, face, alpha) {
    for (let k = 0; k < count; k++) {
      const u = rng() * 2 - 1, th = rng() * 6.283, s = Math.sqrt(1 - u * u);
      const ex = s * Math.cos(th), ey = u, ez = s * Math.sin(th);
      let x = C[0] + ex * A[0], y = C[1] + ey * A[1], z = C[2] + ez * A[2];
      let n = nrmz([ex / A[0], ey / A[1], ez / A[2]]);
      const r = Math.hypot(x, z);
      if (face.neck(y, r)) continue;
      const f = face.y(x, z);
      if (face.up ? y < f : y > f) {
        if (rng() < 0.45) continue; // points pressed onto the face would crowd it
        y = f; n = nrmz([0.09 * x, face.up ? -1 : 1, 0.09 * z]);
      }
      const L = rng(), layer = L < 0.5 ? 0 : L < 0.78 ? 1 : 2;
      const off = -0.035 * layer + gauss(rng) * 0.005;
      const pt = patch(x, y, z);
      put(x + n[0] * off, y + n[1] * off, z + n[2] * off, layer === 0 ? MEM_O : layer === 1 ? MEM_M : MEM_I,
        layer === 0 ? 0.024 : 0.021, alpha * pt * (layer === 0 ? 1 : layer === 1 ? 0.6 : 0.42), -10, n);
    }
  }
  // a neck: a tube leaving the bulb, with radial normals
  function neck(count, y0, y1, r0, r1, lean, alpha) {
    for (let k = 0; k < count; k++) {
      const t = rng(), th = rng() * 6.283;
      const r = (r0 + (r1 - r0) * t) * (1 + gauss(rng) * 0.01);
      const layer = rng() < 0.55 ? 0 : 1;
      const rr = r - 0.04 * layer;
      const cx = lean * t * t;
      put(cx + Math.cos(th) * rr, y0 + (y1 - y0) * t, Math.sin(th) * rr, layer ? MEM_I : MEM_O, 0.022, alpha * (1 - t * 0.75) * (layer ? 0.5 : 1), -10, [Math.cos(th), 0, Math.sin(th)]);
    }
  }
  const PRE_C = [0, 1.15, 0], PRE_A = [1.55, 1.2, 1.3];
  const STEM_LEAN = 1.2; // the bouton's stem leans up and to the right, the way the axon arrived
  const POST_C = [0, -1.0, 0], POST_A = [1.45, 1.0, 1.22];
  c.g = 1;
  membrane(Math.floor(N * 0.22), PRE_C, PRE_A, { y: yPre, up: true, neck: (y, r) => y > PRE_C[1] + PRE_A[1] * 0.86 && r < 0.46 }, 0.5);
  c.g = 6;
  neck(Math.floor(N * 0.03), PRE_C[1] + PRE_A[1] * 0.86, 4.6, 0.47, 0.38, STEM_LEAN, 0.32);
  c.g = 2;
  membrane(Math.floor(N * 0.18), POST_C, POST_A, { y: yPost, up: false, neck: (y, r) => y < POST_C[1] - POST_A[1] * 0.86 && r < 0.35 }, 0.5);
  c.g = 6;
  neck(Math.floor(N * 0.025), POST_C[1] - POST_A[1] * 0.86, -4.4, 0.34, 0.29, -0.4, 0.3);

  // the two faces across the cleft: two lit sheets with the dark gap between
  for (const [fy, sgn] of [[yPre, -1], [yPost, 1]]) {
    for (let k = 0; k < N * 0.02; k++) {
      const a = rng() * 6.283, r = Math.sqrt(rng()) * 0.95;
      const x = Math.cos(a) * r * 1.15, z = Math.sin(a) * r;
      const inner = rng() < 0.4;
      c.g = sgn < 0 ? 1 : 2;
      const edge = 0.55 + 0.45 * smooth(0.6, 0.95, r);
      put(x, fy(x, z) - sgn * (inner ? 0.04 : 0) + gauss(rng) * 0.004, z, inner ? MEM_I : MEM_O, 0.021, (inner ? 0.14 : 0.24) * edge * patch(x, 0, z), -10, [0, sgn, 0]);
    }
  }
  // vesicles: docked on the active zone, three fused and releasing, the rest at many depths
  c.g = 3;
  const ves = [], sites = [];
  const inPre = (x, y, z, r) => ((x / (PRE_A[0] - 0.14)) ** 2 + ((y - PRE_C[1]) / (PRE_A[1] - 0.14)) ** 2 + (z / (PRE_A[2] - 0.14)) ** 2) < 1 - r * 1.4;
  const free = (v) => !ves.some((q) => Math.hypot(q.x - v.x, q.y - v.y, q.z - v.z) < q.r + v.r + 0.035);
  for (let g = 0; g < 4000 && ves.length < 10; g++) {
    const a = rng() * 6.283, rr = 0.15 + Math.sqrt(rng()) * 0.62;
    const r = 0.12 + rng() * 0.03;
    const fused = sites.length < 3;
    const x = Math.cos(a) * rr * 1.1, z = Math.sin(a) * rr * 0.95;
    const v = { x, z, r, y: fused ? yPre(x, z) + r * 0.25 : yPre(x, z) + r + 0.012, fused, docked: !fused };
    if (fused && sites.some((q) => Math.hypot(q[0] - x, q[2] - z) < 0.55)) continue;
    if (!free(v)) continue;
    ves.push(v);
    if (fused) sites.push([x, yPre(x, z), z]);
  }
  for (let g = 0; g < 20000 && ves.length < 50; g++) {
    const r = 0.09 + rng() * 0.07;
    const x = (rng() * 2 - 1) * 1.35, z = (rng() * 2 - 1) * 1.15;
    const y = yPre(x, z) + r + 0.06 + Math.pow(rng(), 1.4) * 1.8;
    const v = { x, y, z, r, fused: false };
    if (!inPre(x, y, z, r) || !free(v)) continue;
    ves.push(v);
  }
  for (const v of ves) {
    // depth: vesicles toward the viewer are brighter and whiter, those behind dimmer and cooler
    const dz = smooth(-1.2, 1.1, v.z);
    const n = Math.round(13000 * kN * v.r * v.r);
    const shellCol = mixc(mixc(MINT, PERI, 0.35 * (1 - dz)), WHITE, 0.3 + 0.35 * dz);
    for (let j = 0; j < n; j++) {
      const u = rng() * 2 - 1, th = rng() * 6.283, s = Math.sqrt(1 - u * u);
      const nn = [s * Math.cos(th), u, s * Math.sin(th)];
      const rr = v.r * (1 + gauss(rng) * 0.025);
      const x = v.x + nn[0] * rr, y = v.y + nn[1] * rr, z = v.z + nn[2] * rr;
      if (v.fused && y < yPre(x, z) + 0.01) continue; // opened into the cleft
      put(x, y, z, shellCol, 0.021, (0.4 + 0.45 * dz) * (v.docked || v.fused ? 1.25 : 1), -10, nn);
    }
    // the filling: transmitter packed inside, a soft glow so each vesicle reads as a full sphere
    const fill = Math.round(2600 * kN * v.r * v.r);
    for (let j = 0; j < fill; j++) {
      const u = rng() * 2 - 1, th = rng() * 6.283, s = Math.sqrt(1 - u * u), rr = v.r * 0.82 * Math.cbrt(rng());
      put(v.x + s * Math.cos(th) * rr, v.y + u * rr, v.z + s * Math.sin(th) * rr, mixc(MINT, WHITE, 0.2), 0.03, 0.09 + 0.07 * dz, v.fused ? -5 : -10);
    }
  }
  // a mitochondrion high in the bouton: a capsule with faint cristae, for scale and depth
  const mito = (C0, ax, L, R, count) => {
    const up = nrmz([-ax[1], ax[0], 0]), w = [ax[1] * up[2] - ax[2] * up[1], ax[2] * up[0] - ax[0] * up[2], ax[0] * up[1] - ax[1] * up[0]];
    for (let k = 0; k < count; k++) {
      const t = rng() * 2 - 1, th = rng() * 6.283;
      const cap = Math.abs(t) > 0.75 ? Math.sqrt(Math.max(0, 1 - ((Math.abs(t) - 0.75) / 0.25) ** 2)) : 1;
      const cristae = rng() < 0.3;
      const rr = cristae ? R * Math.sqrt(rng()) * 0.9 : R * cap;
      const tt = cristae ? Math.round(t * 4) / 4 : t;
      const n = [up[0] * Math.cos(th) + w[0] * Math.sin(th), up[1] * Math.cos(th) + w[1] * Math.sin(th), up[2] * Math.cos(th) + w[2] * Math.sin(th)];
      put(C0[0] + ax[0] * tt * L + n[0] * rr, C0[1] + ax[1] * tt * L + n[1] * rr, C0[2] + ax[2] * tt * L + n[2] * rr,
        mixc(WHITE, PERI, 0.35), 0.021, cristae ? 0.12 : 0.24, -10, cristae ? null : n);
    }
  };
  mito([-0.6, 1.72, -0.5], nrmz([0.85, 0.3, 0.42]), 0.55, 0.19, N * 0.02);
  // postsynaptic density and the receptor field on the lower membrane
  c.g = 5;
  for (let k = 0; k < N * 0.016; k++) {
    const a = rng() * 6.283, r = Math.sqrt(rng()) * 0.85;
    const x = Math.cos(a) * r * 1.1, z = Math.sin(a) * r;
    put(x, yPost(x, z) - 0.04 - rng() * 0.07, z, mixc(MINT, WHITE, 0.3), 0.022, 0.09);
  }
  const nearSite = (x, z) => {
    let bi = 0, bd = 9;
    sites.forEach((q, i) => { const d = Math.hypot(q[0] - x, q[2] - z); if (d < bd) { bd = d; bi = i; } });
    return [bi, Math.min(0.99, bd / 1.1)];
  };
  // receptors: small clusters standing on the face, each lighting as its site's cloud arrives
  for (let k = 0, g = 0; k < 480 * kN && g < 12000; g++) {
    const a = rng() * 6.283, r = Math.sqrt(rng()) * 0.97;
    const bx = Math.cos(a) * r * 1.12, bz = Math.sin(a) * r;
    const [si, d] = nearSite(bx, bz);
    const by = yPost(bx, bz);
    for (let j = 0; j < 11; j++) {
      put(bx + gauss(rng) * 0.013, by + 0.005 + rng() * 0.04, bz + gauss(rng) * 0.013, mixc(WHITE, MINT, 0.55), 0.022, 0.32, -(20 + si + d));
    }
    k++;
  }
  // the spine head is full: actin meshwork, endosomes, a spine apparatus of stacked cisternae,
  // and the calcium that blooms through it when the receptors open
  for (let f = 0; f < 230 * kN; f++) {
    const a = [(rng() * 2 - 1) * 1.0, POST_C[1] + (rng() * 2 - 1) * 0.62, (rng() * 2 - 1) * 0.85];
    const d = nrmz([gauss(rng), gauss(rng), gauss(rng)]), L = 0.18 + rng() * 0.3;
    for (let k = 0; k < 10; k++) {
      const t = rng();
      put(a[0] + d[0] * L * t, a[1] + d[1] * L * t, a[2] + d[2] * L * t, mixc(WHITE, PERI, 0.4), 0.02, 0.12);
    }
  }
  c.g = 8;
  for (let s = 0; s < 3; s++) { // spine apparatus: three flat discs, rim-lit
    const yc = POST_C[1] - 0.18 - s * 0.16, rx = 0.5 - s * 0.06, rz = 0.36 - s * 0.04;
    for (let k = 0; k < N * 0.007; k++) {
      const th = rng() * 6.283, rr = Math.pow(rng(), 0.25);
      const x = 0.15 + Math.cos(th) * rx * rr, z = 0.05 + Math.sin(th) * rz * rr;
      put(x, yc + gauss(rng) * 0.012 + 0.03 * Math.sin(th * 2 + s), z, mixc(WHITE, PERI, 0.45), 0.021, 0.12 + 0.3 * rr ** 6, -10, rr > 0.93 ? [Math.cos(th), 0, Math.sin(th)] : null);
    }
  }
  for (let e = 0; e < 6; e++) { // endosomes
    const r = 0.06 + rng() * 0.05;
    const C = [(rng() * 2 - 1) * 0.8, POST_C[1] + (rng() * 2 - 1) * 0.4 - 0.1, (rng() * 2 - 1) * 0.7];
    for (let k = 0; k < 9000 * kN * r * r; k++) {
      const u = rng() * 2 - 1, th = rng() * 6.283, s = Math.sqrt(1 - u * u), nn = [s * Math.cos(th), u, s * Math.sin(th)];
      put(C[0] + nn[0] * r, C[1] + nn[1] * r, C[2] + nn[2] * r, mixc(PERI, WHITE, 0.4), 0.021, 0.3, -10, nn);
    }
  }
  for (let k = 0; k < N * 0.035; k++) { // calcium: a soft mint volume that lights after the receptors
    const x = gauss(rng) * 0.5, y = -Math.abs(gauss(rng)) * 0.42 - 0.02, z = gauss(rng) * 0.45;
    const [si, d] = nearSite(x, z);
    const dd = Math.min(0.99, d * 0.5 + Math.min(1, -y / 0.9) * 0.5);
    put(x * 1.1, yPost(x, z) - 0.06 + y, z, mixc(MINT, WHITE, 0.15), 0.045, 0.006, -(40 + si + dd));
  }
  // transmitter: stored where each molecule lands; the shader puffs it out of its site
  c.g = 4;
  const per = Math.floor(N * 0.016);
  sites.forEach((q, si) => {
    for (let k = 0; k < per; k++) {
      let lx = q[0] + gauss(rng) * 0.36, lz = q[2] + gauss(rng) * 0.36;
      const l = Math.hypot(lx, lz); if (l > 1.0) { lx *= 1.0 / l; lz *= 1.0 / l; }
      put(lx, yPost(lx, lz) + 0.02 + rng() * 0.05, lz, mixc(MINT, WHITE, 0.2 * rng()), 0.024, 0.55, 1 + si + rng() * 0.999);
    }
  });
  // at rest the cleft is never empty: a faint transmitter haze hangs in it, drifting
  c.g = 9;
  for (let k = 0; k < N * 0.06; k++) {
    const a = rng() * 6.283, r = Math.sqrt(rng()) * 0.95;
    const x = Math.cos(a) * r * 1.12, z = Math.sin(a) * r;
    const y0 = yPost(x, z) + 0.03, y1 = yPre(x, z) - 0.03;
    const near = sites.reduce((m, q) => Math.min(m, Math.hypot(q[0] - x, q[2] - z)), 9);
    // most of it hangs in the cleft; some has drifted down through the lit field into the spine head
    const down = rng() < 0.3;
    const y = down ? y0 - 0.06 - Math.pow(rng(), 1.6) * 0.75 : y0 + rng() * (y1 - y0);
    put(x * (down ? 0.85 : 1), y, z * (down ? 0.85 : 1), mixc(MINT, WHITE, 0.25 * rng()), 0.028, (0.07 + 0.09 * Math.exp(-near * near * 3)) * (down ? 0.55 : 1), -7);
  }
  const siteT = sites.map((q) => { const t = T(q[0], q[1] - 0.02, q[2]); return [t[0], t[1] + OFF, t[2]]; });
  // depth: one neurite passing close to the lens (soft), one far behind
  c.g = 7;
  const rot0 = 0.35, SH = [1.55, -0.05];
  const fromView = (x, y, z) => { // a point given in screen-aligned space, back into the shape's own frame
    const px = x - SH[0], py = y - SH[1], cc = Math.cos(-rot0), ss = Math.sin(-rot0);
    return [cc * px + ss * z, py, -ss * px + cc * z];
  };
  const fibre = (p0, p1, R, count, alpha, size) => {
    for (let k = 0; k < count; k++) {
      const t = rng(), th = rng() * 6.283;
      const q = fromView(p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t + Math.sin(t * 3) * 0.15 + Math.sin(th) * R, p0[2] + (p1[2] - p0[2]) * t + Math.cos(th) * R);
      c.add(q[0], q[1], q[2], mixc(WHITE, MINT, 0.3), size, alpha);
    }
  };
  fibre([-3.6, 2.2, 5.0], [1.0, 1.25, 5.5], 0.22, N * 0.02, 0.06, 0.03);
  fibre([-7, -3.2, -6], [7, 0.4, -7.5], 0.35, N * 0.025, 0.07, 0.024);
  fibre([2.5, -3.6, 4.2], [6.5, 1.5, 3.6], 0.18, N * 0.012, 0.05, 0.03); // a second soft one near the lens
  fibre([-8, 3.0, -9.5], [5, 4.2, -10], 0.3, N * 0.012, 0.05, 0.024);     // and one far behind
  // out-of-focus light: soft mint blobs close to the lens and far behind
  for (const [bx, by, bz, cnt] of [[-2.6, 1.5, 6.4, 500], [2.2, -1.9, 6.0, 420], [-3.4, -2.4, -8.5, 600], [3.6, 2.6, -9.5, 600]]) {
    const q0 = fromView(bx, by, bz);
    for (let k = 0; k < cnt * kN; k++) c.add(q0[0] + gauss(rng) * 0.07, q0[1] + gauss(rng) * 0.07, q0[2] + gauss(rng) * 0.07, mixc(MINT, WHITE, 0.2), 0.03, 0.03);
  }
  c.dust(rng, 12, 0.09, mixc(WHITE, MINT, 0.3));
  // the stem anchor: on the centreline of the leaning neck, with the neck's direction there
  const y0 = PRE_C[1] + PRE_A[1] * 0.86, yA = 3.3, tA = (yA - y0) / (4.6 - y0);
  const cleft = T(0, 0, 0), stem = T(STEM_LEAN * tA * tA, yA, 0), sd = T(2 * STEM_LEAN * tA, 4.6 - y0, 0);
  const sl = Math.hypot(...sd);
  return { cloud: c, meta: { sites: siteT, in: [cleft[0], cleft[1] + OFF, cleft[2]], out: [stem[0], stem[1] + OFF, stem[2]], outDir: sd.map((v) => v / sl) } };
}

function makeLattice(N) {
  // Microtubules: hollow tubes whose wall is wound with fine helical threads (the protofilament
  // lattice read from a distance), the far wall dimmer so they read as hollow. Three of them,
  // gently curved, open near ends toward the viewer, receding to the upper right.
  const rng = mulberry(41), c = new Cloud(N);
  const norm = (v) => { const l = Math.hypot(...v); return v.map((q) => q / l); };
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const D = norm([1, 0.28, -0.85]);
  const U = norm(cross(D, [0, 1, 0]));
  const V = cross(U, D);
  const O = [-2.5, -0.5, 2.3];
  const tubes = [
    { a: 0, b: 0, R: 0.62, len: 10, w: 1, ph: 0.3 },
    { a: 1.55, b: 1.35, R: 0.55, len: 9, w: 0.75, ph: 2.1 },
    { a: -1.75, b: 0.85, R: 0.5, len: 8.5, w: 0.6, ph: 4.0 },
  ];
  const starts = 5, pitch = 2.3;
  const center = (tb, s) => {
    const ua = tb.a + 0.012 * s * s * (tb.ph > 2 ? -1 : 1), vb = tb.b + 0.18 * Math.sin(s * 0.42 + tb.ph);
    return [O[0] + D[0] * s + U[0] * ua + V[0] * vb, O[1] + D[1] * s + U[1] * ua + V[1] * vb, O[2] + D[2] * s + U[2] * ua + V[2] * vb];
  };
  const totalW = tubes.reduce((q, t) => q + t.len * t.R * t.w, 0);
  const budget = Math.floor(N * 0.84);
  for (const tb of tubes) {
    const cnt = Math.floor(budget * tb.len * tb.R * tb.w / totalW);
    for (let k = 0; k < cnt; k++) {
      const s = rng() * tb.len;
      const roll = rng();
      const thread = roll < 0.6, fil = roll >= 0.6 && roll < 0.85; // helical threads, then the 13 straight protofilaments
      const st = Math.floor(rng() * starts);
      const th = thread ? 2 * Math.PI * (s / pitch + st / starts) + gauss(rng) * 0.05
        : fil ? (Math.floor(rng() * 13) / 13) * 2 * Math.PI + gauss(rng) * 0.03 : rng() * 6.283;
      const P = center(tb, s);
      const ca = Math.cos(th), sa = Math.sin(th);
      const rr = tb.R * (1 + gauss(rng) * 0.025);
      const nz = U[2] * ca + V[2] * sa;
      const wall = nz >= 0 ? 1 : 0.35;
      const fade = Math.min(1, (tb.len - s) / 3.2) * Math.min(1, 0.35 + s * 2.5) * tb.w * wall;
      // dimers along each thread: a soft beading, alpha and beta alternating in tint
      const bead = 0.6 + 0.4 * Math.cos(s * Math.PI * 2 / 0.16);
      const beta = Math.floor(s / 0.16) % 2 === 1;
      c.add(P[0] + (U[0] * ca + V[0] * sa) * rr, P[1] + (U[1] * ca + V[1] * sa) * rr, P[2] + (U[2] * ca + V[2] * sa) * rr,
        thread ? (beta ? mixc(WHITE, MINT, 0.2) : mixc(MINT, WHITE, 0.3)) : mixc(WHITE, MINT, 0.35),
        0.022, (thread ? 0.3 * bead : fil ? 0.13 * bead : 0.07) * fade, s + st * pitch / starts + 0.001);
    }
  }
  c.dust(rng, 12, 0.09, mixc(WHITE, MINT, 0.3));
  // the tube runs along D (it bends only slightly): both anchors carry that direction
  return { cloud: c, meta: { in: center(tubes[0], 2.4), out: center(tubes[0], 3.8), dir: D } };
}

function makeSpike(N) {
  // One cell in close-up: a soma at the left, the hillock and bare initial segment where the
  // pulse is born, then a myelinated axon (beaded internodes, nodes of Ranvier) that rises and
  // arcs over to the right. Its last stretch loses its myelin and thins into a bare mint fibre:
  // that fibre runs on, at the same scale, into one input of the machine neuron. The pulse is a
  // long comet, a bright head with a fading tail; a halo exists only where it is. Neighbouring
  // fibres at many depths give the space volume.
  const rng = mulberry(53), c = new Cloud(N);
  const SO = [-3.55, -0.3, -0.9];
  const P0 = [-3.02, 0.3, -0.7], P1 = [-1.9, 1.75, -0.2], P2 = [0.6, 1.3, 0.4], P3 = [5.9, 0.55, 0.4];
  const curve = (t) => {
    const m = 1 - t, b0 = m * m * m, b1 = 3 * m * m * t, b2 = 3 * m * t * t, b3 = t * t * t;
    return [0, 1, 2].map((i) => b0 * P0[i] + b1 * P1[i] + b2 * P2[i] + b3 * P3[i]);
  };
  const tangent = (t) => { const a = curve(Math.max(0, t - 0.002)), b = curve(Math.min(1, t + 0.002)); const d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]; const l = Math.hypot(...d); return d.map((v) => v / l); };
  const frame = (t) => {
    const p = curve(t), d = tangent(t);
    let u = [-d[2], 0, d[0]]; const ul = Math.hypot(...u); u = u.map((q) => q / ul);
    const v = [u[1] * d[2] - u[2] * d[1], u[2] * d[0] - u[0] * d[2], u[0] * d[1] - u[1] * d[0]];
    return { p, u, v };
  };
  const ring = (F, th) => [F.u[0] * Math.cos(th) + F.v[0] * Math.sin(th), F.u[1] * Math.cos(th) + F.v[1] * Math.sin(th), F.u[2] * Math.cos(th) + F.v[2] * Math.sin(th)];
  const IS = 0.1, END = 0.88, NI = 7; // initial segment, myelinated stretch, internodes
  const radius = (t) => {
    if (t < IS) return 0.075 + 0.26 * Math.pow(1 - t / IS, 2.2); // hillock tapering into the initial segment
    if (t > END) return 0.075 - 0.03 * smooth(END, 1, t);        // the bare terminal stretch
    const seg = (((t - IS) / (END - IS)) * NI) % 1;
    const bead = Math.pow(Math.sin(Math.PI * seg), 0.32);
    const close = smooth(END - 0.05, END, t);                     // the last internode closes onto the fibre
    return ((0.205 - 0.03 * t) * (0.3 + 0.7 * bead)) * (1 - close) + 0.075 * close;
  };
  // sheath (and the bare membrane of the initial segment and the terminal), two lamellae with radial normals
  c.g = 1;
  for (let k = 0; k < N * 0.4; k++) {
    const t = rng();
    const bare = t < IS || t > END;
    if (t > END && rng() < 0.4) continue; // the bare fibre is thin: fewer points
    const F = frame(t), th = rng() * 6.283, n = ring(F, th);
    const inner = !bare && rng() < 0.35;
    const rr = radius(t) * (inner ? 0.78 : 1) * (1 + gauss(rng) * 0.02);
    // the last stretch turns from mint toward periwinkle: it is about to become the machine's input
    const col = bare ? mixc(mixc(MINT, WHITE, 0.35), PERI, 0.5 * smooth(0.9, 1.0, t)) : inner ? mixc(MINT, WHITE, 0.5) : mixc(WHITE, [0.78, 0.86, 1.0], 0.3);
    c.add(F.p[0] + n[0] * rr, F.p[1] + n[1] * rr, F.p[2] + n[2] * rr, col, 0.022, (bare ? 0.42 : 0.24) * (inner ? 0.5 : 1), t, packN(n[0], n[2]));
  }
  // the axon core inside, glimpsed through the sheath
  c.g = 2;
  for (let k = 0; k < N * 0.07; k++) {
    const t = rng(), F = frame(t), th = rng() * 6.283, n = ring(F, th);
    const rr = Math.abs(gauss(rng)) * 0.028;
    c.add(F.p[0] + n[0] * rr, F.p[1] + n[1] * rr, F.p[2] + n[2] * rr, mixc(MINT, PERI, 0.5 * smooth(0.9, 1.0, t)), 0.022, t > END ? 0.45 : 0.3, t);
  }
  // nodes of Ranvier: small rings of light in the gaps, where the pulse jumps
  c.g = 3;
  for (let j = 0; j <= NI; j++) {
    const t0 = IS + (j / NI) * (END - IS), F = frame(Math.min(1, t0));
    for (let k = 0; k < N * 0.0016; k++) {
      const th = rng() * 6.283, n = ring(F, th), rr = 0.07 + gauss(rng) * 0.012;
      c.add(F.p[0] + n[0] * rr, F.p[1] + n[1] * rr, F.p[2] + n[2] * rr, MINT, 0.03, 0.3, t0);
    }
  }
  // the pulse: a comet that exists only where the spike is. A tight halo hugging the sheath,
  // and a streak of light on the fibre's axis: a bright head and a long tail fading behind it
  c.g = 4;
  for (let k = 0; k < N * 0.05; k++) {
    const t = rng(), F = frame(t), th = rng() * 6.283, n = ring(F, th);
    const rr = radius(t) * 0.92 + Math.abs(gauss(rng)) * 0.035;
    c.add(F.p[0] + n[0] * rr, F.p[1] + n[1] * rr, F.p[2] + n[2] * rr, mixc(MINT, WHITE, 0.4), 0.03, 0.0, 2 + t);
  }
  for (let k = 0; k < N * 0.07; k++) {
    const t = rng(), F = frame(t), th = rng() * 6.283, n = ring(F, th);
    const rr = Math.abs(gauss(rng)) * 0.022;
    c.add(F.p[0] + n[0] * rr, F.p[1] + n[1] * rr, F.p[2] + n[2] * rr, mixc(MINT, WHITE, 0.55), 0.03, 0.0, 4 + Math.min(t, 0.999));
  }
  // the soma: a full, rounded pyramid with a nucleus, its membrane rim-lit; it charges and flashes
  c.g = 5;
  const toAx = [P0[0] - SO[0], P0[1] - SO[1], P0[2] - SO[2]]; { const l = Math.hypot(...toAx); toAx[0] /= l; toAx[1] /= l; toAx[2] /= l; }
  for (let k = 0; k < N * 0.075; k++) {
    const u = rng() * 2 - 1, th = rng() * 6.283, s = Math.sqrt(1 - u * u);
    const n = [s * Math.cos(th), u, s * Math.sin(th)];
    const along = n[0] * toAx[0] + n[1] * toAx[1] + n[2] * toAx[2];
    const R = 0.74 * (1 + 0.3 * Math.max(0, along) ** 3 + fbm(n[0] * 2 + 5, n[1] * 2, n[2] * 2) * 0.12) * (1 + 0.2 * Math.max(0, n[1]) ** 4);
    const inner = rng() < 0.3;
    const rr = R * (inner ? 0.88 : 1);
    c.add(SO[0] + n[0] * rr, SO[1] + n[1] * rr * 1.05, SO[2] + n[2] * rr, inner ? mixc(MINT, WHITE, 0.5) : mixc(WHITE, MINT, 0.25), 0.026, inner ? 0.22 : 0.54, -3, packN(n[0], n[2]));
  }
  for (let k = 0; k < N * 0.02; k++) { // the nucleus and the soma's inner light
    const x = gauss(rng) * 0.19, y = gauss(rng) * 0.19, z = gauss(rng) * 0.19;
    c.add(SO[0] + x - 0.06, SO[1] + y + 0.05, SO[2] + z, mixc(MINT, WHITE, 0.3), 0.045, 0.2, -3);
  }
  const dsegs = neuronSegs(rng, SO, 1.1, 6, 2, null).filter((s) => {
    const d = [s.b[0] - SO[0], s.b[1] - SO[1], s.b[2] - SO[2]];
    return d[0] * toAx[0] + d[1] * toAx[1] + d[2] * toAx[2] < 0.15 && s.b[1] > -1.5;
  });
  sampleSegments(c, rng, dsegs, N * 0.05, (cl, x, y, z, s) => cl.add(x, y, z, mixc(WHITE, MINT, 0.25 + s.depth * 0.25), 0.022, 0.2 * (1 - s.depth * 0.22)));
  // neighbouring fibres at many depths: two close to the lens (soft), the rest further and further behind
  c.g = 6;
  const fib = [
    { a: [-7, 2.9, 4.6], b: [6, 3.6, 5.2], R: 0.2, al: 0.9 },
    { a: [-6, -3.3, 5.4], b: [7, -2.2, 4.8], R: 0.22, al: 0.8 },
    { a: [-8, -0.6, -3.2], b: [8, 1.2, -4.6], R: 0.17, al: 0.3 },
    { a: [-7, -2.6, -5.5], b: [8, -1.4, -6.5], R: 0.17, al: 0.3 },
    { a: [-6, 3.6, -7], b: [8, 2.6, -8], R: 0.15, al: 0.32 },
    { a: [-9, 1.6, -11], b: [9, -0.4, -12], R: 0.2, al: 0.4 },
    { a: [-9, -4.2, -13], b: [9, -3.0, -12], R: 0.2, al: 0.4 },
  ];
  for (const f of fib) {
    for (let k = 0; k < N * 0.018; k++) {
      const t = rng(), th = rng() * 6.283;
      const bead = 0.35 + 0.65 * Math.pow(Math.abs(Math.sin(t * Math.PI * 9)), 0.32);
      const rr = f.R * bead;
      c.add(f.a[0] + (f.b[0] - f.a[0]) * t, f.a[1] + (f.b[1] - f.a[1]) * t + Math.sin(t * 2.5) * 0.3 + Math.sin(th) * rr, f.a[2] + (f.b[2] - f.a[2]) * t + Math.cos(th) * rr,
        mixc(WHITE, MINT, 0.3), 0.022, f.al);
    }
  }
  c.dust(rng, 13, 0.11, mixc(WHITE, MINT, 0.35));
  // anchor: the first internode, where the lattice runs in the core; end: where the fibre hands on
  return { cloud: c, meta: { anchor: curve(0.14), anchorDir: tangent(0.14), end: curve(1.0), endDir: tangent(1.0), soma: SO } };
}

function makeMachine(N) {
  const rng = mulberry(61), c = new Cloud(N);
  const R = 1.0;
  // core: a soft periwinkle glow with a gaussian falloff (param = normalised radius)
  c.g = 1;
  for (let k = 0; k < N * 0.13; k++) {
    const x = gauss(rng) * 0.42, y = gauss(rng) * 0.42, z = gauss(rng) * 0.42;
    const r = Math.hypot(x, y, z);
    c.add(x, y, z, [0.36, 0.46, 1.0], 0.05, 0.035, Math.min(1, r / R));
  }
  // a faint membrane, just enough to give the cell an edge
  c.g = 2;
  for (let k = 0; k < N * 0.04; k++) {
    const u = rng() * 2 - 1, th = rng() * 6.283, s = Math.sqrt(1 - u * u), rr = R * (1 + gauss(rng) * 0.06);
    c.add(s * Math.cos(th) * rr, u * rr, s * Math.sin(th) * rr, PERI, 0.026, 0.13, 1);
  }
  // charge: two arcs of light rise from the bottom on both sides and meet at the top (the threshold)
  const RR = 1.6;
  c.g = 3;
  for (let k = 0; k < N * 0.06; k++) {
    const a = rng(), side = rng() < 0.5 ? -1 : 1;
    const ang = -Math.PI / 2 + side * a * Math.PI;
    const rr = RR + gauss(rng) * 0.03;
    c.add(Math.cos(ang) * rr, Math.sin(ang) * rr, gauss(rng) * 0.03, PERI, 0.026, 0.09, 30 + a * 0.999);
  }
  // the threshold: a small bright point at the top
  c.g = 4;
  for (let k = 0; k < 500; k++) {
    c.add(gauss(rng) * 0.06, RR + gauss(rng) * 0.06, gauss(rng) * 0.06, mixc(PERI, WHITE, 0.5), 0.03, 0.12, 31.5);
  }
  // the shock ring released on firing (expands in the shader)
  c.g = 5;
  for (let k = 0; k < N * 0.035; k++) {
    const ang = rng() * 6.283, rr = 1.1 + gauss(rng) * 0.05;
    c.add(Math.cos(ang) * rr, Math.sin(ang) * rr, gauss(rng) * 0.05, PERI, 0.03, 0.0, 40 + rng());
  }
  // inputs: organic curved strands from the left; mint far away (the biological pulse) turning periwinkle at the cell
  const strands = 7;
  let a0In = null, a0Dir = null;
  for (let s = 0; s < strands; s++) {
    c.g = 10 + s;
    const y0 = (s - 3) * 1.05 + gauss(rng) * 0.35;
    let a0 = [-8.5, y0, -2.5 + rng() * 3.5];
    const ang = Math.PI - ((s - 3) / 3) * 0.95 + gauss(rng) * 0.08;
    let a3 = [Math.cos(ang) * R * 0.9, Math.sin(ang) * R * 0.9, (rng() - 0.5) * 0.4];
    let a1 = [-5.6, y0 * 1.1 + gauss(rng) * 0.5, a0[2] * 0.7 + gauss(rng) * 0.5];
    let a2 = [-2.4, a3[1] * 2.2 + y0 * 0.3 + gauss(rng) * 0.3, gauss(rng) * 0.4];
    if (s === 3) { // the input the biological axon runs on into: it starts where that axon ends
      a0 = [-8.5, 0.0, 0.0]; a1 = [-5.6, -0.12, 0.0]; a2 = [-2.6, 0.05, 0.0]; a3 = [-R * 0.9, 0, 0];
      a0In = a0; const d = [a1[0] - a0[0], a1[1] - a0[1], a1[2] - a0[2]], l = Math.hypot(...d); a0Dir = d.map((v) => v / l);
    }
    for (let k = 0; k < N * (s === 3 ? 0.05 : 0.024); k++) { // the input the axon becomes is the fullest
      const t = rng(), mt = 1 - t;
      const b0 = mt * mt * mt, b1 = 3 * mt * mt * t, b2 = 3 * mt * t * t, b3 = t * t * t;
      const x = b0 * a0[0] + b1 * a1[0] + b2 * a2[0] + b3 * a3[0];
      const y = b0 * a0[1] + b1 * a1[1] + b2 * a2[1] + b3 * a3[1];
      const z = b0 * a0[2] + b1 * a1[2] + b2 * a2[2] + b3 * a3[2];
      const w = 0.03 * (1.2 - t * 0.6) * (s === 3 ? 1.35 : 1);
      // the other inputs come out of the dark; the axon's own input is lit all along
      const al = s === 3 ? 0.2 : 0.2 * smooth(0.0, 0.22, t);
      c.add(x + gauss(rng) * w, y + gauss(rng) * w, z + gauss(rng) * w,
        s === 3 ? mixc(mixc(MINT, PERI, 0.5), PERI, smooth(0.0, 0.6, t)) : mixc(MINT, PERI, smooth(0.45, 0.95, t)), 0.022, al, 2 + s + Math.min(t, 0.999));
    }
  }
  // output axon to the right
  c.g = 7;
  for (let k = 0; k < N * 0.07; k++) {
    const t = rng();
    const x = R * 0.9 + t * 7.5, y = Math.sin(t * 2.2) * 0.45 * t, z = -t * 1.6;
    const w = 0.035 * (1 - t * 0.4);
    c.add(x + gauss(rng) * w, y + gauss(rng) * w, z + gauss(rng) * w, PERI, 0.024, 0.24, 20 + t);
  }
  c.dust(rng, 12, 0.09, mixc(WHITE, PERI, 0.5));
  return { cloud: c, meta: { core: [0, 0, 0], a0: a0In, a0Dir } };
}

function makeMap(N) {
  // A map forming: cells scattered irregularly through a volume above a faint terrain,
  // a few curved links, place fields (soft rings) on the ground, one route lighting up.
  const rng = mulberry(71), c = new Cloud(N);
  const X0 = -6.4, X1 = 6.4, Z0 = -7.0, Z1 = 2.6;
  const TA = 0.5, ca = Math.cos(TA), sa = Math.sin(TA);
  const TT = (x, y, z) => [x, y * ca - z * sa - 0.1, y * sa + z * ca - 0.4];
  const addT = (x, y, z, ...rest) => c.add(x, y * ca - z * sa - 0.1, y * sa + z * ca - 0.4, ...rest);
  const ground = (x, z) => vnoise(x * 0.22, 0.7, z * 0.22) * 0.9 + vnoise(x * 0.5, 2.1, z * 0.5) * 0.25 - 0.9;
  const nodes = [];
  let guard = 0;
  while (nodes.length < 150 && guard++ < 60000) {
    const x = X0 + rng() * (X1 - X0), z = Z0 + rng() * (Z1 - Z0);
    // clustered, uneven density
    if (rng() > 0.25 + 0.75 * smooth(-0.3, 0.4, vnoise(x * 0.35 + 4, 1.3, z * 0.35))) continue;
    const y = ground(x, z) + 0.45 + rng() * 1.0;
    if (nodes.some((n) => (n.x - x) ** 2 + (n.y - y) ** 2 + (n.z - z) ** 2 < 0.5)) continue;
    nodes.push({ x, y, z, nb: [] });
  }
  const edges = new Map();
  nodes.forEach((n, i) => {
    const d = nodes.map((m, j) => [j, (m.x - n.x) ** 2 + (m.y - n.y) ** 2 + (m.z - n.z) ** 2]).filter((q) => q[0] !== i).sort((a, b) => a[1] - b[1]);
    const kk = 2 + (rng() < 0.35 ? 1 : 0);
    for (let k = 0; k < kk; k++) {
      const j = d[k][0]; const key = i < j ? i + '-' + j : j + '-' + i;
      if (!edges.has(key)) { edges.set(key, [Math.min(i, j), Math.max(i, j)]); n.nb.push(j); nodes[j].nb.push(i); }
    }
  });
  const near = (x, z) => nodes.reduce((b, n, i) => ((n.x - x) ** 2 + (n.z - z) ** 2 < (nodes[b].x - x) ** 2 + (nodes[b].z - z) ** 2 ? i : b), 0);
  const s0 = near(-5.2, 1.8), s1 = near(4.8, -6.0);
  const dist = new Array(nodes.length).fill(Infinity), prev = new Array(nodes.length).fill(-1), done = new Array(nodes.length).fill(false);
  dist[s0] = 0;
  for (let it = 0; it < nodes.length; it++) {
    let u = -1; for (let i = 0; i < nodes.length; i++) if (!done[i] && (u < 0 || dist[i] < dist[u])) u = i;
    if (u < 0 || dist[u] === Infinity) break; done[u] = true;
    for (const v of nodes[u].nb) {
      const w = Math.hypot(nodes[u].x - nodes[v].x, nodes[u].z - nodes[v].z) * (0.8 + hash3(u, v, 3) * 0.6);
      if (dist[u] + w < dist[v]) { dist[v] = dist[u] + w; prev[v] = u; }
    }
  }
  const path = []; for (let v = s1; v >= 0; v = prev[v]) path.unshift(v);
  const pathLen = []; let acc = 0; path.forEach((v, i) => { if (i) acc += Math.hypot(nodes[v].x - nodes[path[i - 1]].x, nodes[v].z - nodes[path[i - 1]].z); pathLen.push(acc); });
  const onPath = new Map(); path.forEach((v, i) => onPath.set(v, pathLen[i] / Math.max(acc, 1e-6)));
  const pathEdge = new Set(); for (let i = 1; i < path.length; i++) { const a = path[i - 1], b = path[i]; pathEdge.add(a < b ? a + '-' + b : b + '-' + a); }
  // cells: small glowing spheres
  for (const [i, n] of nodes.entries()) {
    c.g = 1;
    const pp = onPath.has(i) ? onPath.get(i) : -10;
    const r0 = pp >= 0 ? 0.075 : 0.05 + rng() * 0.03;
    const cnt = pp >= 0 ? 110 : 55;
    for (let k = 0; k < cnt; k++) {
      const core = k < cnt * 0.3;
      const rr = core ? r0 * 0.35 : r0;
      addT(n.x + gauss(rng) * rr, n.y + gauss(rng) * rr, n.z + gauss(rng) * rr, core ? mixc(PERI, WHITE, 0.55) : mixc(PERI, WHITE, 0.12), 0.027, core ? 0.6 : 0.34, pp);
    }
    // place fields: a soft ring on the ground under each cell on the route
    if (pp >= 0) {
      c.g = 2;
      const gy = ground(n.x, n.z);
      for (let k = 0; k < 420; k++) {
        const a = rng() * 6.283, rr = 0.55 + gauss(rng) * 0.05;
        addT(n.x + Math.cos(a) * rr, gy, n.z + Math.sin(a) * rr, mixc(PERI, WHITE, 0.2), 0.024, 0.035, 2 + pp);
      }
      for (let k = 0; k < 60; k++) {
        const t = rng();
        addT(n.x + gauss(rng) * 0.01, gy + (n.y - gy) * t, n.z + gauss(rng) * 0.01, PERI, 0.02, 0.0, 2 + pp);
      }
    }
  }
  // links: faint curved strands; the route brighter
  const elist = [...edges.entries()].map(([key, [a, b]]) => ({ key, a, b, l: Math.hypot(nodes[a].x - nodes[b].x, nodes[a].y - nodes[b].y, nodes[a].z - nodes[b].z) }));
  const terrainN = Math.floor(N * 0.16);
  const edgeBudget = Math.max(0, c.left - terrainN - Math.floor(N * 0.08));
  let totalLen = 0; for (const e of elist) totalLen += e.l * (pathEdge.has(e.key) ? 2.2 : 1);
  c.g = 3;
  for (const e of elist) {
    const isP = pathEdge.has(e.key);
    const cnt = Math.floor(edgeBudget * e.l * (isP ? 2.2 : 1) / totalLen);
    const A = nodes[e.a], B = nodes[e.b];
    const bk = isP ? 0.25 : 1;
    const bend = [gauss(rng) * 0.22 * e.l * bk, (0.12 * e.l + gauss(rng) * 0.08 * e.l) * bk, gauss(rng) * 0.22 * e.l * bk];
    const pa = isP ? onPath.get(e.a) : -10, pb = isP ? onPath.get(e.b) : -10;
    for (let k = 0; k < cnt; k++) {
      const t = rng(), arc = Math.sin(t * Math.PI);
      addT(A.x + (B.x - A.x) * t + bend[0] * arc + gauss(rng) * 0.014,
        A.y + (B.y - A.y) * t + bend[1] * arc + gauss(rng) * 0.014,
        A.z + (B.z - A.z) * t + bend[2] * arc + gauss(rng) * 0.014,
        mixc(PERI, WHITE, 0.1), 0.021, isP ? 0.17 : 0.125, isP ? pa + (pb - pa) * t : -10);
    }
  }
  // terrain: a faint, irregular ground the map sits on
  c.g = 4;
  for (let k = 0; k < terrainN; k++) {
    const x = X0 - 1 + rng() * (X1 - X0 + 2), z = Z0 - 1 + rng() * (Z1 - Z0 + 2);
    const y = ground(x, z);
    const shade = 0.5 + 0.5 * smooth(-0.9, -0.3, y);
    addT(x, y, z, mixc(PERI, WHITE, 0.3), 0.02, 0.05 * shade);
  }
  c.dust(rng, 12, 0.08, mixc(WHITE, PERI, 0.5));
  // in: the start of the route (the machine neuron becomes this cell); out: the middle of the network
  const mid = nodes.reduce((m, n) => [m[0] + n.x / nodes.length, m[1] + n.y / nodes.length, m[2] + n.z / nodes.length], [0, 0, 0]);
  return { cloud: c, meta: { in: TT(nodes[s0].x, nodes[s0].y, nodes[s0].z), out: TT(mid[0], mid[1], mid[2]) } };
}

// The mark exactly as the logo paints it: the three bowls share the top edge and are painted
// outer (near-white), middle (periwinkle), inner (mint), then the stem (near-white). The logo is
// rasterised offscreen and every point is placed on a covered pixel and takes the colour visible
// there, so overlaps are never populated twice and no colour can spill into its neighbour.
const MARK_PATHS = [
  ['M3.6 1.59H17.1A5.45 5.45 0 0 1 17.1 12.49H6.84', '#f4f6fb', 1],
  ['M3.6 1.59H15.35A3.7 3.7 0 0 1 15.35 8.99H3.6', '#8aa2ff', 2],
  ['M3.6 1.59H13.6A1.95 1.95 0 0 1 13.6 5.49H3.6', '#5ef0c4', 3],
  ['M3.6 0.75V24.0', '#f4f6fb', 1],
];
const MARK_GEO = { S: 0.1, CX: 13, CY: 12.375, OY: 0 };
function makeMark(N) {
  const rng = mulberry(83), c = new Cloud(N);
  const SC = 48, cw = 26 * SC, ch = 24 * SC;
  const cv = typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas(cw, ch) : document.createElement('canvas');
  cv.width = cw; cv.height = ch;
  const g = cv.getContext('2d', { willReadFrequently: true });
  g.scale(SC, SC); g.lineWidth = 1.68; g.lineJoin = 'round'; g.lineCap = 'butt';
  for (const [d, col] of MARK_PATHS) { g.strokeStyle = col; g.stroke(new Path2D(d)); }
  const px = g.getImageData(0, 0, cw, ch).data;
  const pal = [
    { rgb: [0xf4, 0xf6, 0xfb], tag: 1 }, { rgb: [0x8a, 0xa2, 0xff], tag: 2 }, { rgb: [0x5e, 0xf0, 0xc4], tag: 3 },
  ];
  const hits = new Int32Array(cw * ch), cls = new Uint8Array(cw * ch);
  let nh = 0;
  for (let i = 0; i < cw * ch; i++) {
    if (px[i * 4 + 3] < 128) continue; // covered at least half: the edge sits where the vector edge is
    let best = 0, bd = 1e9;
    for (let k = 0; k < 3; k++) {
      const q = pal[k].rgb, d = (px[i * 4] - q[0]) ** 2 + (px[i * 4 + 1] - q[1]) ** 2 + (px[i * 4 + 2] - q[2]) ** 2;
      if (d < bd) { bd = d; best = k; }
    }
    hits[nh++] = i; cls[i] = best;
  }
  const { S, CX, CY, OY } = MARK_GEO;
  const M = Math.floor(N * 0.78);
  for (let k = 0; k < M && nh; k++) {
    const i = hits[Math.floor(rng() * nh)], p = pal[cls[i]];
    const x = ((i % cw) + rng()) / SC, y = (Math.floor(i / cw) + rng()) / SC;
    c.g = p.tag;
    c.add((x - CX) * S, -(y - CY) * S + OY, 0, p.rgb.map((v) => v / 255), 0.026 + rng() * 0.004, 0.85, (x + y) * 0.12);
  }
  c.dust(rng, 13, 0.07);
  const at = (x, y) => [(x - CX) * S, -(y - CY) * S + OY, 0];
  // in: the middle of the outer bowl's lower edge (near-white): the network lies inside that stroke
  return { cloud: c, meta: { in: at(11.97, 12.49) } };
}

/* ------------------------------------------------------------------ */
/* The one hand-over that is a morph: the orb's own points become the brain */
/* ------------------------------------------------------------------ */
function selectK(idx, lo, hi, k, P, ax) { // quickselect on idx[lo, hi) by P[idx*3 + ax]
  let l = lo, r = hi - 1;
  while (r > l) {
    const m = (l + r) >> 1;
    const a = P[idx[l] * 3 + ax], b = P[idx[m] * 3 + ax], c = P[idx[r] * 3 + ax];
    const pivot = a < b ? (b < c ? b : a < c ? c : a) : (a < c ? a : b < c ? c : b);
    let i = l, j = r;
    while (i <= j) {
      while (P[idx[i] * 3 + ax] < pivot) i++;
      while (P[idx[j] * 3 + ax] > pivot) j--;
      if (i <= j) { const t = idx[i]; idx[i] = idx[j]; idx[j] = t; i++; j--; }
    }
    if (k <= j) r = j; else if (k >= i) l = i; else break;
  }
}
function kdMatch(PA, PB, ia, ib, out) { // a balanced k-d split of both lists together: neighbours stay neighbours
  const stack = [0, ia.length];
  while (stack.length) {
    const hi = stack.pop(), lo = stack.pop(), n = hi - lo;
    if (n <= 0) continue;
    if (n === 1) { out[ia[lo]] = ib[lo]; continue; }
    let best = 0, bext = -1;
    for (let ax = 0; ax < 3; ax++) {
      let a0 = Infinity, a1 = -Infinity, b0 = Infinity, b1 = -Infinity;
      for (let k = lo; k < hi; k++) {
        const va = PA[ia[k] * 3 + ax], vb = PB[ib[k] * 3 + ax];
        if (va < a0) a0 = va; if (va > a1) a1 = va; if (vb < b0) b0 = vb; if (vb > b1) b1 = vb;
      }
      const e = (a1 - a0) + (b1 - b0);
      if (e > bext) { bext = e; best = ax; }
    }
    const mid = lo + (n >> 1);
    selectK(ia, lo, hi, mid, PA, best); selectK(ib, lo, hi, mid, PB, best);
    stack.push(lo, mid, mid, hi);
  }
}
// Reorders the brain so that its point i is the partner of the orb's point i, both seen as they
// are on screen when the hand-over starts (the orb unrotated, the brain at its resting turn).
function matchToOrb(orb, brain, brainRot) {
  const n = orb.n, PA = orb.pos, PB = new Float32Array(n * 3);
  const cr = Math.cos(brainRot), sr = Math.sin(brainRot);
  for (let i = 0; i < n; i++) {
    const x = brain.pos[i * 3], y = brain.pos[i * 3 + 1], z = brain.pos[i * 3 + 2];
    PB[i * 3] = cr * x + sr * z; PB[i * 3 + 1] = y; PB[i * 3 + 2] = -sr * x + cr * z;
  }
  const map = new Int32Array(n);
  const ia = [], ib = [], ra = [], rb = [];
  for (let i = 0; i < n; i++) (orb.tag[i] >= 0.5 ? ia : ra).push(i);
  for (let j = 0; j < n; j++) (brain.tag[j] >= 0.5 ? ib : rb).push(j);
  const m = Math.min(ia.length, ib.length);
  const A1 = ia.slice(0, m).concat(ra), B1 = ib.slice(0, m).concat(rb);
  kdMatch(PA, PB, Int32Array.from(A1.slice(0, m)), Int32Array.from(B1.slice(0, m)), map);
  kdMatch(PA, PB, Int32Array.from(A1.slice(m)), Int32Array.from(B1.slice(m)), map);
  const P = (arr, w) => { const o = new Float32Array(arr.length); for (let i = 0; i < n; i++) for (let q = 0; q < w; q++) o[i * w + q] = arr[map[i] * w + q]; return o; };
  brain.pos = P(brain.pos, 3); brain.col = P(brain.col, 3); brain.aux = P(brain.aux, 4); brain.tag = P(brain.tag, 1);
}
const MAKERS = [makeBrain, makeNeurons, makeSynapse, makeLattice, makeSpike, makeMachine, makeMap, makeMark];
const BRAIN_ROT = -0.55;
function orbCloud(N) { return shuffleCloud(makeOrb(N), 899); }
function buildSet(k, N, mobile, orb) {
  const S = MAKERS[k](N, mobile), c = S.cloud;
  shuffleCloud(c, 900 + k);
  if (k === 0) matchToOrb(orb, c, BRAIN_ROT);
  return { k, pos: c.pos, col: c.col, aux: c.aux, meta: S.meta };
}

