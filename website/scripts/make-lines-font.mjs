// Draws Psyche Lines, the small web font that keeps a text diagram in a code block on Martian Mono's
// grid: src/assets/fonts/psyche-lines.woff2, built into the site and committed.
//
//   npm run lines                          draw the font again
//   node scripts/make-lines-font.mjs --check   fail if the committed font is not what this script draws
//   node scripts/make-lines-font.mjs --ttf PATH   also write the same font as an uncompressed TrueType file
//
// Why it exists. The site serves the Latin file of Martian Mono, and that file has no box-drawing
// character (U+2500 to U+257F), no triangle pointer and no leftwards or rightwards arrow. A code block
// that holds one gets it from a system face (Menlo on macOS, 0.602 em wide), while every Martian Mono
// glyph is 0.7 em wide, so a line that mixes the two drifts out of column by 1.37 px for each such
// character at 14 px, and the descriptions of a file tree slide left with its nesting depth. This face
// draws those characters at Martian Mono's own advance, so a diagram keeps the columns it was typed in.
//
// What it covers, and what the stylesheet must say (src/styles/fonts.css keeps the same list, and
// make-lines-font.test.mjs fails when the two differ):
//   U+2500 to U+257F   all 128 box-drawing characters: light, heavy and double lines, every junction,
//                      the dashed lines, the four arcs, the three diagonals and the half lines
//   U+25B2 U+25BA U+25BC U+25C4   the four triangles of a flow diagram
//   U+2190 U+2192      the leftwards and rightwards arrows (Martian Mono draws its up and down arrows
//                      in the Latin file, and these two only in the full font)
//
// How it is drawn. Every glyph is built from rectangles, arcs and triangles; no outline comes from
// another font, so there is nothing to credit and no licence beyond the project's own (MIT, LICENSE).
// All numbers are in font units of a 1000-unit em:
//   - Every glyph is 700 wide, the advance of every Martian Mono glyph.
//   - A light line is 100 thick and runs along y = 350: the thickness and the middle of Martian Mono's
//     hyphen (y 300 to 400, regular weight), so `├──` sits on the same line as a `-` beside it.
//     A heavy line is 200. A double line is two bars of 80, their centres 90 either side of the axis.
//   - A horizontal line bleeds 10 units past the cell on each side, so a row of `─` has no hairline
//     seam where the browser rounds a glyph's position.
//   - A vertical line runs the whole height of a code block's line (1.75 em, Starlight's
//     --sl-line-height, plus 40 units of overlap), so `│` on one line meets `├` on the next and a tree's
//     rails are unbroken. If the code blocks' line height changes, only that changes: a gap returns
//     between the lines of a rail. The font's own metrics are Martian Mono's (ascent 1000, descent 200),
//     so a line that uses it keeps the height it had.
//   - Where lines meet, each bar stops at the bar it joins, as the Unicode charts draw them (light and
//     heavy lines meet at the centre, a double line turns into the double line it meets, a single line
//     crosses a double one only when it passes through). Overlapping shapes are merged, so no glyph
//     has overlapping contours.
//
// How it is written. The TrueType tables are written here, byte by byte, with no library; the
// container is WOFF2 with Brotli from node:zlib (the glyf and loca tables are stored untransformed,
// which the format allows). Nothing in the output depends on the date or the machine, so the file is
// the same on every run; the checker compares the font's tables, not the compressed bytes, which
// another zlib build might arrange differently.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { brotliCompressSync, brotliDecompressSync, constants } from 'node:zlib';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

export const OUTPUT = fileURLToPath(new URL('../src/assets/fonts/psyche-lines.woff2', import.meta.url));

// ---------------------------------------------------------------------------------------------------
// Design numbers (font units; the em is 1000)

export const UPM = 1000;
export const ADVANCE = 700;
const CX = 350; // the middle of the cell
const CY = 350; // the axis of every horizontal line: the middle of Martian Mono's hyphen
const ASCENT = 1000; // Martian Mono's ascent and descent: this font's own, so line boxes are unchanged
const DESCENT = -200;
const WIN_ASCENT = 1090; // and its Windows metrics
const WIN_DESCENT = 250;
const LINE_HEIGHT = 1750; // a code block's line: 1.75 em
const HALF_LEADING = (LINE_HEIGHT - (ASCENT - DESCENT)) / 2; // 275 above the ascent and below the descent
const LINE_TOP = ASCENT + HALF_LEADING;
const LINE_BOTTOM = DESCENT - HALF_LEADING;
const OVERLAP = 40; // a vertical line reaches this far into the line above and the line below
const TOP = LINE_TOP + OVERLAP;
const BOTTOM = LINE_BOTTOM - OVERLAP;
const BLEED = 10; // a horizontal line reaches this far past the cell on each side
const LIGHT = 100;
const HEAVY = 200;
const BAR = 80; // one bar of a double line
const BAR_OFFSET = 90; // from the axis to the middle of that bar
const DASH_FILL = 0.6; // the share of each dash period that is ink
const ARC_RADIUS = 350; // the centre line of an arc: half the cell, so the arc ends at the cell's edge

// The numbers the tests hold the drawing to.
export const DESIGN = { ASCENT, DESCENT, WIN_ASCENT, WIN_DESCENT, TOP, BOTTOM, BLEED, LIGHT, HEAVY, CX, CY, LINE_TOP, LINE_BOTTOM };

// ---------------------------------------------------------------------------------------------------
// What each box-drawing character is made of. Read from the Unicode names: four letters, the style of
// the left, right, up and down arms in that order. `.` no arm, `l` light, `h` heavy, `d` double
// ("DOWN LIGHT AND RIGHT HEAVY" is `.h.l`).

export const ARMS = {
  0x2500: 'll..', 0x2501: 'hh..', 0x2502: '..ll', 0x2503: '..hh', 0x250C: '.l.l', 0x250D: '.h.l',
  0x250E: '.l.h', 0x250F: '.h.h', 0x2510: 'l..l', 0x2511: 'h..l', 0x2512: 'l..h', 0x2513: 'h..h',
  0x2514: '.ll.', 0x2515: '.hl.', 0x2516: '.lh.', 0x2517: '.hh.', 0x2518: 'l.l.', 0x2519: 'h.l.',
  0x251A: 'l.h.', 0x251B: 'h.h.', 0x251C: '.lll', 0x251D: '.hll', 0x251E: '.lhl', 0x251F: '.llh',
  0x2520: '.lhh', 0x2521: '.hhl', 0x2522: '.hlh', 0x2523: '.hhh', 0x2524: 'l.ll', 0x2525: 'h.ll',
  0x2526: 'l.hl', 0x2527: 'l.lh', 0x2528: 'l.hh', 0x2529: 'h.hl', 0x252A: 'h.lh', 0x252B: 'h.hh',
  0x252C: 'll.l', 0x252D: 'hl.l', 0x252E: 'lh.l', 0x252F: 'hh.l', 0x2530: 'll.h', 0x2531: 'hl.h',
  0x2532: 'lh.h', 0x2533: 'hh.h', 0x2534: 'lll.', 0x2535: 'hll.', 0x2536: 'lhl.', 0x2537: 'hhl.',
  0x2538: 'llh.', 0x2539: 'hlh.', 0x253A: 'lhh.', 0x253B: 'hhh.', 0x253C: 'llll', 0x253D: 'hlll',
  0x253E: 'lhll', 0x253F: 'hhll', 0x2540: 'llhl', 0x2541: 'lllh', 0x2542: 'llhh', 0x2543: 'hlhl',
  0x2544: 'lhhl', 0x2545: 'hllh', 0x2546: 'lhlh', 0x2547: 'hhhl', 0x2548: 'hhlh', 0x2549: 'hlhh',
  0x254A: 'lhhh', 0x254B: 'hhhh', 0x2550: 'dd..', 0x2551: '..dd', 0x2552: '.d.l', 0x2553: '.l.d',
  0x2554: '.d.d', 0x2555: 'd..l', 0x2556: 'l..d', 0x2557: 'd..d', 0x2558: '.dl.', 0x2559: '.ld.',
  0x255A: '.dd.', 0x255B: 'd.l.', 0x255C: 'l.d.', 0x255D: 'd.d.', 0x255E: '.dll', 0x255F: '.ldd',
  0x2560: '.ddd', 0x2561: 'd.ll', 0x2562: 'l.dd', 0x2563: 'd.dd', 0x2564: 'dd.l', 0x2565: 'll.d',
  0x2566: 'dd.d', 0x2567: 'ddl.', 0x2568: 'lld.', 0x2569: 'ddd.', 0x256A: 'ddll', 0x256B: 'lldd',
  0x256C: 'dddd', 0x2574: 'l...', 0x2575: '..l.', 0x2576: '.l..', 0x2577: '...l', 0x2578: 'h...',
  0x2579: '..h.', 0x257A: '.h..', 0x257B: '...h', 0x257C: 'lh..', 0x257D: '..lh', 0x257E: 'hl..',
  0x257F: '..hl',
};

// The dashed lines: [dashes in the cell, thickness, vertical].
export const DASHES = {
  0x2504: [3, LIGHT, false], 0x2505: [3, HEAVY, false], 0x2506: [3, LIGHT, true], 0x2507: [3, HEAVY, true],
  0x2508: [4, LIGHT, false], 0x2509: [4, HEAVY, false], 0x250A: [4, LIGHT, true], 0x250B: [4, HEAVY, true],
  0x254C: [2, LIGHT, false], 0x254D: [2, HEAVY, false], 0x254E: [2, LIGHT, true], 0x254F: [2, HEAVY, true],
};

// The arcs: the direction of the horizontal and of the vertical arm, +1 right or up, -1 left or down.
export const ARCS = {
  0x256D: [+1, -1], // down and right
  0x256E: [-1, -1], // down and left
  0x256F: [-1, +1], // up and left
  0x2570: [+1, +1], // up and right
};

// The characters this font covers, in the order of their glyphs (glyph 0 is .notdef).
export const COVERED = [
  0x2190, 0x2192,
  ...Array.from({ length: 0x80 }, (_, i) => 0x2500 + i),
  0x25B2, 0x25BA, 0x25BC, 0x25C4,
];

// ---------------------------------------------------------------------------------------------------
// Shapes. A contour is a list of points {x, y, on}; an outer contour runs clockwise and a hole
// counter-clockwise (y up), which is what a TrueType rasteriser fills by the non-zero rule.

const polygon = (pairs) => pairs.map(([x, y]) => ({ x, y, on: true }));

// The shoelace sum: positive when the points run counter-clockwise.
function signedArea(points) {
  let sum = 0;
  for (let i = 0; i < points.length; i++) {
    const a = points[i];
    const b = points[(i + 1) % points.length];
    sum += a.x * b.y - b.x * a.y;
  }
  return sum / 2;
}

// An outer contour made clockwise, and started at a point on the curve.
function clockwise(points) {
  let out = points;
  if (signedArea(points) > 0) {
    out = [...points].reverse();
    const first = out.findIndex((p) => p.on);
    out = [...out.slice(first), ...out.slice(0, first)];
  }
  return out;
}

// The union of axis-aligned rectangles [x0, y0, x1, y1] as contours with no overlap. The rectangles'
// edges cut the plane into cells; the edges of the filled cells that touch an empty cell are chained
// into loops (a filled cell on the right of every edge, so an outer loop runs clockwise and a hole
// counter-clockwise), and points in a straight line are dropped.
export function unionRects(rects) {
  const xs = [...new Set(rects.flatMap((r) => [r[0], r[2]]))].sort((a, b) => a - b);
  const ys = [...new Set(rects.flatMap((r) => [r[1], r[3]]))].sort((a, b) => a - b);
  const filled = Array.from({ length: ys.length - 1 }, () => new Array(xs.length - 1).fill(false));
  for (const [x0, y0, x1, y1] of rects) {
    for (let iy = ys.indexOf(y0); iy < ys.indexOf(y1); iy++) {
      for (let ix = xs.indexOf(x0); ix < xs.indexOf(x1); ix++) filled[iy][ix] = true;
    }
  }
  const at = (ix, iy) => iy >= 0 && iy < filled.length && ix >= 0 && ix < filled[0].length && filled[iy][ix];

  const out = new Map(); // "x,y" of an edge's start -> its edges
  const edge = (ax, ay, bx, by) => {
    const key = `${ax},${ay}`;
    if (!out.has(key)) out.set(key, []);
    out.get(key).push({ ax, ay, bx, by, used: false });
  };
  for (let iy = 0; iy < filled.length; iy++) {
    for (let ix = 0; ix < filled[0].length; ix++) {
      if (!filled[iy][ix]) continue;
      const [x0, x1, y0, y1] = [xs[ix], xs[ix + 1], ys[iy], ys[iy + 1]];
      if (!at(ix - 1, iy)) edge(x0, y0, x0, y1); // left side, upwards
      if (!at(ix, iy + 1)) edge(x0, y1, x1, y1); // top, rightwards
      if (!at(ix + 1, iy)) edge(x1, y1, x1, y0); // right side, downwards
      if (!at(ix, iy - 1)) edge(x1, y0, x0, y0); // bottom, leftwards
    }
  }

  const contours = [];
  for (const edges of out.values()) {
    for (const first of edges) {
      if (first.used) continue;
      const loop = [];
      let cur = first;
      for (;;) {
        cur.used = true;
        loop.push([cur.ax, cur.ay]);
        if (cur.bx === first.ax && cur.by === first.ay) break;
        const next = out.get(`${cur.bx},${cur.by}`).filter((e) => !e.used);
        // Two cells that touch at a corner leave two ways out of it: take the sharper right turn, so
        // each piece keeps its own loop.
        const din = [cur.bx - cur.ax, cur.by - cur.ay];
        next.sort((p, q) => turn(din, p) - turn(din, q));
        cur = next[0];
      }
      contours.push(polygon(straighten(loop)));
    }
  }
  return contours;
}

const turn = (din, e) => Math.sign(din[0] * (e.by - e.ay) - din[1] * (e.bx - e.ax)); // negative: right
function straighten(loop) {
  return loop.filter((p, i) => {
    const a = loop[(i + loop.length - 1) % loop.length];
    const b = loop[(i + 1) % loop.length];
    return (p[0] - a[0]) * (b[1] - p[1]) - (p[1] - a[1]) * (b[0] - p[0]) !== 0;
  });
}

// Points of a circular arc as quadratic segments (an off-curve point, then the on-curve point that
// ends the segment), at most 45 degrees to a segment, from angle a0 to a1 about (cx, cy).
function arcPoints(cx, cy, r, a0, a1) {
  const n = Math.max(1, Math.ceil(Math.abs(a1 - a0) / (Math.PI / 4) - 1e-9));
  const step = (a1 - a0) / n;
  const points = [];
  for (let i = 0; i < n; i++) {
    const mid = a0 + (i + 0.5) * step;
    const reach = r / Math.cos(step / 2);
    points.push({ x: cx + reach * Math.cos(mid), y: cy + reach * Math.sin(mid), on: false });
    points.push({ x: cx + r * Math.cos(a0 + (i + 1) * step), y: cy + r * Math.sin(a0 + (i + 1) * step), on: true });
  }
  return points;
}

// The shorter way round from one angle to another.
const sweep = (a, b) => {
  let d = b - a;
  while (d > Math.PI) d -= 2 * Math.PI;
  while (d <= -Math.PI) d += 2 * Math.PI;
  return d;
};

// ---------------------------------------------------------------------------------------------------
// The lines and junctions

const bars = (style) =>
  style === 'l' ? [{ o: 0, t: LIGHT }] : style === 'h' ? [{ o: 0, t: HEAVY }] : style === 'd' ? [{ o: -BAR_OFFSET, t: BAR }, { o: BAR_OFFSET, t: BAR }] : [];
// How far an arm's outermost bar reaches from the axis.
const reach = (style) => (style === 'l' ? LIGHT / 2 : style === 'h' ? HEAVY / 2 : style === 'd' ? BAR_OFFSET + BAR / 2 : 0);

// An arm runs along `axis` ('h' is x, 'v' is y) from the centre out to `outer`; `dir` is its direction;
// `pos` and `neg` are the arms across it on its positive and negative side (an arm's bars have offsets
// across it, so a bar of offset > 0 lies on the side of `pos`).
const ARM = {
  L: { axis: 'h', dir: -1, outer: -BLEED, opp: 'R', pos: 'U', neg: 'D' },
  R: { axis: 'h', dir: +1, outer: ADVANCE + BLEED, opp: 'L', pos: 'U', neg: 'D' },
  U: { axis: 'v', dir: +1, outer: TOP, opp: 'D', pos: 'R', neg: 'L' },
  D: { axis: 'v', dir: -1, outer: BOTTOM, opp: 'U', pos: 'R', neg: 'L' },
};
const CENTRE = { h: CX, v: CY }; // the middle of the cell along an axis

// Where one bar of an arm stops on the side of the centre. `styles` is {L, R, U, D}.
function innerEnd(name, bar, styles) {
  const arm = ARM[name];
  const style = styles[name];
  const c = CENTRE[arm.axis];
  const across = [arm.pos, arm.neg].filter((n) => styles[n] !== '.');
  const partner = bar.o > 0 ? arm.pos : bar.o < 0 ? arm.neg : null; // the arm across it, on its own side
  const hasPartner = partner !== null && styles[partner] !== '.';
  // The far edge, seen from this arm, of the bar of arm p that lies nearest to this arm's side.
  const meet = (p) => {
    const nearest = bars(styles[p]).reduce((a, b) => (b.o * arm.dir > a.o * arm.dir ? b : a));
    return c + nearest.o - (arm.dir * nearest.t) / 2;
  };

  if (styles[arm.opp] !== '.') {
    // The line goes on past the centre. A double bar still stops at an arm across it on its own side;
    // anything else runs through.
    return style === 'd' && hasPartner ? meet(partner) : c;
  }
  if (style !== 'd') {
    if (across.length === 0) return c; // a half line ends at the centre
    if (across.length === 2) {
      // The stem of a T: it stops at the near bar of a double line across it, else at the centre.
      const double = across.find((n) => styles[n] === 'd');
      return double ? meet(double) : c;
    }
    // A corner: it runs to the outer edge of the line across it, so the corner is closed.
    return c - arm.dir * reach(styles[across[0]]);
  }
  if (hasPartner) return meet(partner); // a double bar turns into the bar it meets
  const other = bar.o > 0 ? arm.neg : arm.pos;
  return styles[other] !== '.' ? c - arm.dir * reach(styles[other]) : c;
}

function armsGlyph(spec) {
  const styles = { L: spec[0], R: spec[1], U: spec[2], D: spec[3] };
  const rects = [];
  for (const name of ['L', 'R', 'U', 'D']) {
    if (styles[name] === '.') continue;
    const arm = ARM[name];
    for (const bar of bars(styles[name])) {
      const a = arm.outer;
      const b = innerEnd(name, bar, styles);
      const [from, to] = [Math.min(a, b), Math.max(a, b)];
      const lo = (arm.axis === 'h' ? CY : CX) + bar.o - bar.t / 2;
      const hi = lo + bar.t;
      rects.push(arm.axis === 'h' ? [from, lo, to, hi] : [lo, from, hi, to]);
    }
  }
  return unionRects(rects);
}

function dashGlyph([count, thickness, vertical]) {
  const span = vertical ? LINE_HEIGHT : ADVANCE;
  const start = vertical ? LINE_BOTTOM : 0;
  const period = span / count;
  const dash = period * DASH_FILL;
  const rects = [];
  for (let i = 0; i < count; i++) {
    const a = Math.round(start + i * period + (period - dash) / 2);
    const b = Math.round(start + i * period + (period + dash) / 2);
    rects.push(vertical ? [CX - thickness / 2, a, CX + thickness / 2, b] : [a, CY - thickness / 2, b, CY + thickness / 2]);
  }
  return unionRects(rects);
}

// A quarter circle between a vertical and a horizontal arm. sx and sy are the directions of the arms.
function arcGlyph([sx, sy]) {
  const half = LIGHT / 2;
  const [mx, my] = [CX + sx * ARC_RADIUS, CY + sy * ARC_RADIUS]; // the centre of the circle
  const endV = sy > 0 ? TOP : BOTTOM;
  const endH = sx > 0 ? ADVANCE + BLEED : -BLEED;
  const angle = (x, y) => Math.atan2(y - my, x - mx);
  // Outer edge: down the outside of the vertical arm, round the outside of the arc, out along the
  // outside of the horizontal arm; then back along the inside.
  const outerFrom = [CX - sx * half, CY + sy * ARC_RADIUS];
  const outerTo = [CX + sx * ARC_RADIUS, CY - sy * half];
  const innerFrom = [CX + sx * ARC_RADIUS, CY + sy * half];
  const innerTo = [CX + sx * half, CY + sy * ARC_RADIUS];
  const a0 = angle(...outerFrom);
  const b0 = angle(...innerFrom);
  const points = [
    ...polygon([[CX - sx * half, endV], outerFrom]),
    ...arcPoints(mx, my, ARC_RADIUS + half, a0, a0 + sweep(a0, angle(...outerTo))),
    ...polygon([[endH, CY - sy * half], [endH, CY + sy * half], innerFrom]),
    ...arcPoints(mx, my, ARC_RADIUS - half, b0, b0 + sweep(b0, angle(...innerTo))),
    ...polygon([[CX + sx * half, endV]]),
  ];
  return [clockwise(points)];
}

// The diagonals run corner to corner of the line, so they meet the next line's.
function diagonalGlyph(kind) {
  const [W, H, y0, y1] = [ADVANCE, LINE_HEIGHT, LINE_BOTTOM, LINE_TOP];
  const hw = LIGHT / Math.sin(Math.atan2(H, W)) / 2; // half the stroke measured along x
  const yA = y0 + (hw * H) / W; // where the left edge of the rising stroke meets x = 0
  const yB = y1 - (hw * H) / W; // where its right edge leaves x = W
  const yc = (y0 + y1) / 2;
  const rise = [[0, y0], [0, yA], [W - hw, y1], [W, y1], [W, yB], [hw, y0]];
  const mirror = (pairs) => pairs.map(([x, y]) => [W - x, y]);
  if (kind === 'rise') return [clockwise(polygon(rise))];
  if (kind === 'fall') return [clockwise(polygon(mirror(rise)))];
  // Both strokes as one outline: the four notches between them end where their edges cross.
  const kl = [CX - hw, yc];
  const kt = [CX, yc + (hw * H) / W];
  const kr = [CX + hw, yc];
  const kb = [CX, yc - (hw * H) / W];
  return [clockwise(polygon([
    [0, y0], [0, yA], kl, [0, yB], [0, y1], [hw, y1], kt, [W - hw, y1],
    [W, y1], [W, yB], kr, [W, yA], [W, y0], [W - hw, y0], kb, [hw, y0],
  ]))];
}

// ---------------------------------------------------------------------------------------------------
// Triangles and arrows

const TRIANGLES = {
  0x25B2: [[110, 140], [350, 560], [590, 140]], // up
  0x25BC: [[110, 560], [590, 560], [350, 140]], // down
  0x25BA: [[80, 130], [80, 570], [620, CY]], // right
  0x25C4: [[620, 130], [80, CY], [620, 570]], // left
};

// A line arrow pointing right, drawn as one outline: a shaft of the light thickness and a head of two
// strokes of the same thickness at 45 degrees, cut square to their own direction, 600 wide as Martian
// Mono's up and down arrows are.
function arrowRight() {
  const w = LIGHT / 2;
  const a = w * Math.SQRT2; // half the stroke measured along x at the axis
  const tip = 650;
  const wing = 300; // how far each stroke reaches from the axis
  const stemX = tip - 2 * a - w; // where the shaft's edge meets a stroke's inner edge
  const out = [tip - wing, CY + wing]; // end of a stroke's outer edge, upper
  const inn = [out[0] - a, out[1] - a]; // and of its inner edge
  const lower = ([x, y]) => [x, 2 * CY - y];
  return [clockwise(polygon([
    [50, CY - w], [50, CY + w], [stemX, CY + w], inn, out, [tip, CY], lower(out), lower(inn), [stemX, CY - w],
  ]))];
}

function drawGlyph(code) {
  if (ARMS[code]) return armsGlyph(ARMS[code]);
  if (DASHES[code]) return dashGlyph(DASHES[code]);
  if (ARCS[code]) return arcGlyph(ARCS[code]);
  if (code === 0x2571) return diagonalGlyph('rise');
  if (code === 0x2572) return diagonalGlyph('fall');
  if (code === 0x2573) return diagonalGlyph('cross');
  if (TRIANGLES[code]) return [clockwise(polygon(TRIANGLES[code]))];
  if (code === 0x2192) return arrowRight();
  if (code === 0x2190) {
    return arrowRight().map((c) => clockwise(c.map((p) => ({ ...p, x: ADVANCE - p.x }))));
  }
  throw new Error(`no drawing for U+${code.toString(16).toUpperCase()}`);
}

// Every glyph, .notdef first: { code, contours } with integer coordinates.
export function buildGlyphs() {
  const round = (c) => c.map((p) => ({ x: Math.round(p.x), y: Math.round(p.y), on: p.on }));
  return [
    { code: null, contours: [] },
    ...COVERED.map((code) => ({ code, contours: drawGlyph(code).map(round) })),
  ];
}

// ---------------------------------------------------------------------------------------------------
// TrueType tables

const buf = (size, write) => {
  const b = Buffer.alloc(size);
  write(b);
  return b;
};
const pad4 = (b) => (b.length % 4 === 0 ? b : Buffer.concat([b, Buffer.alloc(4 - (b.length % 4))]));

export function checksum(b) {
  const p = pad4(b);
  let sum = 0;
  for (let i = 0; i < p.length; i += 4) sum = (sum + p.readUInt32BE(i)) >>> 0;
  return sum;
}

function bounds(glyphs) {
  const pts = glyphs.flatMap((g) => g.contours.flat());
  return {
    xMin: Math.min(...pts.map((p) => p.x)),
    yMin: Math.min(...pts.map((p) => p.y)),
    xMax: Math.max(...pts.map((p) => p.x)),
    yMax: Math.max(...pts.map((p) => p.y)),
  };
}

// The glyf and loca tables. Coordinates are written as 16-bit differences; the table is padded so every
// glyph starts on a 4-byte boundary and loca is the long format.
function glyfAndLoca(glyphs) {
  const parts = [];
  const offsets = [0];
  let length = 0;
  for (const g of glyphs) {
    let data = Buffer.alloc(0);
    if (g.contours.length) {
      const pts = g.contours.flat();
      const b = bounds([g]);
      const ends = [];
      let n = 0;
      for (const c of g.contours) {
        n += c.length;
        ends.push(n - 1);
      }
      data = buf(10 + 2 * ends.length + 2 + pts.length * 5, (o) => {
        let at = 0;
        o.writeInt16BE(g.contours.length, at); at += 2;
        for (const v of [b.xMin, b.yMin, b.xMax, b.yMax]) { o.writeInt16BE(v, at); at += 2; }
        for (const e of ends) { o.writeUInt16BE(e, at); at += 2; }
        o.writeUInt16BE(0, at); at += 2; // no instructions
        for (const p of pts) o.writeUInt8(p.on ? 1 : 0, at++); // on or off the curve; 16-bit differences follow
        let px = 0;
        for (const p of pts) { o.writeInt16BE(p.x - px, at); at += 2; px = p.x; }
        let py = 0;
        for (const p of pts) { o.writeInt16BE(p.y - py, at); at += 2; py = p.y; }
      });
      data = pad4(data);
    }
    parts.push(data);
    length += data.length;
    offsets.push(length);
  }
  const loca = buf(offsets.length * 4, (o) => offsets.forEach((v, i) => o.writeUInt32BE(v, i * 4)));
  return { glyf: Buffer.concat(parts), loca };
}

// Format 4, the one every browser reads: one segment for each run of consecutive characters.
function cmapTable(glyphs) {
  const runs = [];
  glyphs.forEach((g, gid) => {
    if (g.code === null) return;
    const last = runs[runs.length - 1];
    if (last && last.end + 1 === g.code && last.firstGid + (g.code - last.start) === gid) last.end = g.code;
    else runs.push({ start: g.code, end: g.code, firstGid: gid });
  });
  runs.push({ start: 0xffff, end: 0xffff, firstGid: 0 });
  const n = runs.length;
  const subtable = buf(16 + 8 * n, (o) => {
    const entry = Math.floor(Math.log2(n));
    const search = 2 * 2 ** entry;
    let at = 0;
    for (const v of [4, 16 + 8 * n, 0, 2 * n, search, entry, 2 * n - search]) { o.writeUInt16BE(v, at); at += 2; }
    for (const r of runs) { o.writeUInt16BE(r.end, at); at += 2; }
    at += 2; // reserved
    for (const r of runs) { o.writeUInt16BE(r.start, at); at += 2; }
    for (const r of runs) { o.writeUInt16BE((r.firstGid - r.start) & 0xffff, at); at += 2; }
    // idRangeOffset: all zero, so the delta alone maps a character to its glyph
  });
  const head = buf(4 + 2 * 8, (o) => {
    o.writeUInt16BE(0, 0);
    o.writeUInt16BE(2, 2);
    o.writeUInt16BE(0, 4); o.writeUInt16BE(3, 6); o.writeUInt32BE(20, 8); // Unicode, BMP
    o.writeUInt16BE(3, 12); o.writeUInt16BE(1, 14); o.writeUInt32BE(20, 16); // Windows, Unicode BMP
  });
  return Buffer.concat([head, subtable]);
}

const LONG_DATE = (Date.UTC(2026, 10, 6) - Date.UTC(1904, 0, 1)) / 1000; // 2026-11-06, fixed so the font never varies

function headTable(box) {
  return buf(54, (o) => {
    o.writeUInt32BE(0x00010000, 0); // version
    o.writeUInt32BE(0x00010000, 4); // font revision 1.0
    o.writeUInt32BE(0, 8); // checkSumAdjustment, filled in when the font is assembled
    o.writeUInt32BE(0x5f0f3cf5, 12);
    o.writeUInt16BE(0x0801, 16); // bit 0: baseline at y = 0; bit 11: the font may be converted without loss (WOFF2)
    o.writeUInt16BE(UPM, 18);
    o.writeBigInt64BE(BigInt(LONG_DATE), 20);
    o.writeBigInt64BE(BigInt(LONG_DATE), 28);
    o.writeInt16BE(box.xMin, 36); o.writeInt16BE(box.yMin, 38); o.writeInt16BE(box.xMax, 40); o.writeInt16BE(box.yMax, 42);
    o.writeUInt16BE(0, 44); // macStyle
    o.writeUInt16BE(8, 46); // lowestRecPPEM
    o.writeInt16BE(2, 48); // fontDirectionHint
    o.writeInt16BE(1, 50); // long loca
    o.writeInt16BE(0, 52);
  });
}

function hheaTable(box, count) {
  return buf(36, (o) => {
    o.writeUInt32BE(0x00010000, 0);
    o.writeInt16BE(ASCENT, 4); o.writeInt16BE(DESCENT, 6); o.writeInt16BE(0, 8);
    o.writeUInt16BE(ADVANCE, 10);
    o.writeInt16BE(box.xMin, 12); // minLeftSideBearing
    o.writeInt16BE(ADVANCE - box.xMax, 14); // minRightSideBearing
    o.writeInt16BE(box.xMax, 16); // xMaxExtent
    o.writeInt16BE(1, 18); o.writeInt16BE(0, 20); o.writeInt16BE(0, 22); // caret
    o.writeUInt16BE(count, 34); // every glyph has its own metrics
  });
}

function hmtxTable(glyphs) {
  return buf(glyphs.length * 4, (o) => {
    glyphs.forEach((g, i) => {
      o.writeUInt16BE(ADVANCE, i * 4);
      o.writeInt16BE(g.contours.length ? bounds([g]).xMin : 0, i * 4 + 2);
    });
  });
}

function maxpTable(glyphs) {
  const sizes = glyphs.map((g) => g.contours.flat().length);
  return buf(32, (o) => {
    o.writeUInt32BE(0x00010000, 0);
    o.writeUInt16BE(glyphs.length, 4);
    o.writeUInt16BE(Math.max(...sizes), 6); // maxPoints
    o.writeUInt16BE(Math.max(...glyphs.map((g) => g.contours.length)), 8); // maxContours
    o.writeUInt16BE(1, 14); // maxZones
  });
}

function nameTable() {
  const strings = {
    0: 'Copyright (c) 2026 Cagan Caliskan. MIT License.',
    1: 'Psyche Lines',
    2: 'Regular',
    3: 'Psyche Lines Regular 1.000',
    4: 'Psyche Lines Regular',
    5: 'Version 1.000',
    6: 'PsycheLines-Regular',
    13: 'Released under the MIT licence of the Psyche repository (LICENSE). Drawn by website/scripts/make-lines-font.mjs; no outline in it comes from another font.',
    14: 'https://github.com/cagancaliskan/psyche/blob/main/LICENSE',
  };
  const ids = Object.keys(strings).map(Number);
  const encoded = ids.map((id) => Buffer.from(strings[id], 'utf16le').swap16());
  const head = buf(6 + 12 * ids.length, (o) => {
    o.writeUInt16BE(0, 0); o.writeUInt16BE(ids.length, 2); o.writeUInt16BE(6 + 12 * ids.length, 4);
    let at = 6;
    let offset = 0;
    ids.forEach((id, i) => {
      for (const v of [3, 1, 0x409, id, encoded[i].length, offset]) { o.writeUInt16BE(v, at); at += 2; }
      offset += encoded[i].length;
    });
  });
  return Buffer.concat([head, ...encoded]);
}

function os2Table() {
  return buf(96, (o) => {
    o.writeUInt16BE(4, 0); // version
    o.writeInt16BE(ADVANCE, 2); // xAvgCharWidth
    o.writeUInt16BE(400, 4); o.writeUInt16BE(5, 6); o.writeUInt16BE(0, 8); // weight, width, embedding
    [650, 600, 0, 75, 650, 600, 0, 350, LIGHT, CY, 0].forEach((v, i) => o.writeInt16BE(v, 10 + 2 * i)); // sub/superscript, strikeout, family class
    o.writeUInt8(9, 32 + 3); // panose: bProportion 9, monospaced (the others stay 0, any)
    o.writeUInt32BE(0, 42); // ulUnicodeRange1
    o.writeUInt32BE(0x2820, 46); // ulUnicodeRange2: Arrows (37), Box Drawing (43), Geometric Shapes (45)
    o.write('NONE', 58, 'ascii');
    o.writeUInt16BE(0x00c0, 62); // fsSelection: regular, use the typographic metrics
    o.writeUInt16BE(COVERED[0], 64); o.writeUInt16BE(COVERED[COVERED.length - 1], 66);
    o.writeInt16BE(ASCENT, 68); o.writeInt16BE(DESCENT, 70); o.writeInt16BE(0, 72);
    o.writeUInt16BE(WIN_ASCENT, 74); o.writeUInt16BE(WIN_DESCENT, 76);
    o.writeUInt32BE(1, 78); // ulCodePageRange1: Latin 1
    o.writeInt16BE(600, 86); o.writeInt16BE(800, 88); // x-height and cap height of Martian Mono
    o.writeUInt16BE(1, 94); // usMaxContext
  });
}

function postTable() {
  return buf(32, (o) => {
    o.writeUInt32BE(0x00030000, 0); // no glyph names
    o.writeInt16BE(-100, 8); o.writeInt16BE(50, 10); // underline
    o.writeUInt32BE(1, 12); // fixed pitch
  });
}

// The font: its tables by tag, and the assembled sfnt.
export function buildFont() {
  const glyphs = buildGlyphs();
  const box = bounds(glyphs);
  const { glyf, loca } = glyfAndLoca(glyphs);
  const tables = {
    'OS/2': os2Table(),
    cmap: cmapTable(glyphs),
    glyf,
    head: headTable(box),
    hhea: hheaTable(box, glyphs.length),
    hmtx: hmtxTable(glyphs),
    loca,
    maxp: maxpTable(glyphs),
    name: nameTable(),
    post: postTable(),
  };
  const tags = Object.keys(tables).sort();
  const dirSize = 12 + 16 * tags.length;
  const entries = [];
  let offset = dirSize;
  for (const tag of tags) {
    entries.push({ tag, offset, length: tables[tag].length, sum: checksum(tables[tag]) });
    offset += pad4(tables[tag]).length;
  }
  const header = buf(dirSize, (o) => {
    o.writeUInt32BE(0x00010000, 0);
    o.writeUInt16BE(tags.length, 4);
    const entry = Math.floor(Math.log2(tags.length));
    o.writeUInt16BE(16 * 2 ** entry, 6); o.writeUInt16BE(entry, 8); o.writeUInt16BE(16 * tags.length - 16 * 2 ** entry, 10);
    entries.forEach((e, i) => {
      o.write(e.tag, 12 + 16 * i, 'latin1');
      o.writeUInt32BE(e.sum, 16 + 16 * i); o.writeUInt32BE(e.offset, 20 + 16 * i); o.writeUInt32BE(e.length, 24 + 16 * i);
    });
  });
  const sfnt = Buffer.concat([header, ...tags.map((t) => pad4(tables[t]))]);
  // checkSumAdjustment: what makes the whole file add up to 0xB1B0AFBA.
  const headAt = entries.find((e) => e.tag === 'head').offset;
  sfnt.writeUInt32BE((0xb1b0afba - checksum(sfnt)) >>> 0, headAt + 8);
  tables.head = Buffer.from(sfnt.subarray(headAt, headAt + 54));
  return { sfnt, tables, glyphs };
}

// ---------------------------------------------------------------------------------------------------
// WOFF2

const KNOWN_TAGS = { cmap: 0, head: 1, hhea: 2, hmtx: 3, maxp: 4, name: 5, 'OS/2': 6, post: 7, glyf: 10, loca: 11 };
const WOFF2_ORDER = ['OS/2', 'cmap', 'glyf', 'loca', 'head', 'hhea', 'hmtx', 'maxp', 'name', 'post']; // loca follows glyf

function base128(n) {
  const out = [n & 0x7f];
  for (n = Math.floor(n / 128); n > 0; n = Math.floor(n / 128)) out.unshift((n & 0x7f) | 0x80);
  return Buffer.from(out);
}

export function toWoff2(tables) {
  const tags = WOFF2_ORDER.filter((t) => tables[t]);
  const directory = Buffer.concat(
    tags.map((tag) => {
      const stored = tag === 'glyf' || tag === 'loca';
      // flags: the table's number, and for glyf and loca transform version 3, which means "stored as it is"
      return Buffer.concat([Buffer.from([KNOWN_TAGS[tag] | (stored ? 0xc0 : 0)]), base128(tables[tag].length)]);
    }),
  );
  const data = Buffer.concat(tags.map((t) => tables[t]));
  const packed = brotliCompressSync(data, {
    params: {
      [constants.BROTLI_PARAM_MODE]: constants.BROTLI_MODE_FONT,
      [constants.BROTLI_PARAM_QUALITY]: 11,
      [constants.BROTLI_PARAM_SIZE_HINT]: data.length,
    },
  });
  const sfntSize = 12 + 16 * tags.length + tags.reduce((sum, t) => sum + pad4(tables[t]).length, 0);
  const total = pad4(Buffer.alloc(48 + directory.length + packed.length)).length;
  const header = buf(48, (o) => {
    o.writeUInt32BE(0x774f4632, 0); // 'wOF2'
    o.writeUInt32BE(0x00010000, 4); // TrueType outlines
    o.writeUInt32BE(total, 8);
    o.writeUInt16BE(tags.length, 12);
    o.writeUInt32BE(sfntSize, 16);
    o.writeUInt32BE(packed.length, 20);
    o.writeUInt16BE(1, 24); o.writeUInt16BE(0, 26); // version 1.0
  });
  return Buffer.concat([header, directory, packed, Buffer.alloc(total - 48 - directory.length - packed.length)]);
}

// The tables of a WOFF2 file this script wrote (every table stored as it is), by tag.
export function readWoff2(file) {
  if (file.readUInt32BE(0) !== 0x774f4632) throw new Error('not a WOFF2 file');
  if (file.readUInt32BE(8) !== file.length) throw new Error('the length in the header is not the length of the file');
  const count = file.readUInt16BE(12);
  const packedLength = file.readUInt32BE(20);
  const names = Object.fromEntries(Object.entries(KNOWN_TAGS).map(([k, v]) => [v, k]));
  let at = 48;
  const listed = [];
  for (let i = 0; i < count; i++) {
    const flags = file[at++];
    if ((flags & 0x3f) === 63) throw new Error('a table with a tag of its own: this reader does not handle it');
    let length = 0;
    for (;;) {
      const byte = file[at++];
      length = length * 128 + (byte & 0x7f);
      if (!(byte & 0x80)) break;
    }
    const tag = names[flags & 0x3f];
    const version = flags >> 6;
    if (version !== (tag === 'glyf' || tag === 'loca' ? 3 : 0)) throw new Error(`${tag} is transformed: this reader does not handle it`);
    listed.push({ tag, length });
  }
  const data = brotliDecompressSync(file.subarray(at, at + packedLength));
  const tables = {};
  let offset = 0;
  for (const { tag, length } of listed) {
    tables[tag] = Buffer.from(data.subarray(offset, offset + length));
    offset += length;
  }
  if (offset !== data.length) throw new Error('the compressed data is longer than the tables');
  return tables;
}

// ---------------------------------------------------------------------------------------------------

function main() {
  const arg = (name) => {
    const i = process.argv.indexOf(name);
    return i >= 0 ? process.argv[i + 1] : undefined;
  };
  const { sfnt, tables } = buildFont();
  if (process.argv.includes('--check')) {
    let committed;
    try {
      committed = readWoff2(readFileSync(OUTPUT));
    } catch (err) {
      console.error(`make-lines-font: ${OUTPUT} cannot be read (${err.message}). Run \`npm run lines\` in website/ and commit the file.`);
      process.exit(1);
    }
    const differ = Object.keys(tables).filter((t) => !committed[t] || !committed[t].equals(tables[t]));
    if (differ.length || Object.keys(committed).length !== Object.keys(tables).length) {
      console.error(`make-lines-font: the committed font differs from what this script draws (${differ.join(', ') || 'its table list'}). Run \`npm run lines\` in website/ and commit the file.`);
      process.exit(1);
    }
    console.log(`make-lines-font: ${OUTPUT.split('/').slice(-3).join('/')} is what the script draws`);
    return;
  }
  mkdirSync(dirname(OUTPUT), { recursive: true });
  const woff2 = toWoff2(tables);
  writeFileSync(OUTPUT, woff2);
  console.log(`make-lines-font: ${woff2.length} bytes written to ${OUTPUT}`);
  if (arg('--ttf')) {
    writeFileSync(arg('--ttf'), sfnt);
    console.log(`make-lines-font: ${sfnt.length} bytes written to ${arg('--ttf')}`);
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) main();
