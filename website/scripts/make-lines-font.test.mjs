import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { brotliDecompressSync } from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { ADVANCE, ARMS, COVERED, DASHES, DESIGN, OUTPUT, UPM, buildFont, buildGlyphs, checksum, readWoff2, toWoff2, unionRects } from './make-lines-font.mjs';

const text = (relative) => readFileSync(new URL(relative, import.meta.url), 'utf8');
const FONTS_CSS = text('../src/styles/fonts.css');
const GLOBAL_CSS = text('../src/styles/global.css');
const MARTIAN = fileURLToPath(new URL('../node_modules/@fontsource-variable/martian-mono/files/martian-mono-latin-wght-normal.woff2', import.meta.url));

const font = buildFont();
const glyphs = buildGlyphs();
const glyphOf = (code) => glyphs[1 + COVERED.indexOf(code)];

// ---- small readers -----------------------------------------------------------------------------

// The characters a cmap table maps (format 4, Windows Unicode), as a Map from character to glyph.
function characters(cmap) {
  let offset = null;
  for (let i = 0; i < cmap.readUInt16BE(2); i++) {
    if (cmap.readUInt16BE(4 + 8 * i) === 3 && cmap.readUInt16BE(6 + 8 * i) === 1) offset = cmap.readUInt32BE(8 + 8 * i);
  }
  assert.notEqual(offset, null, 'a Windows Unicode subtable');
  assert.equal(cmap.readUInt16BE(offset), 4, 'format 4');
  const segments = cmap.readUInt16BE(offset + 6) / 2;
  const [ends, starts] = [offset + 14, offset + 16 + 2 * segments];
  const [deltas, ranges] = [starts + 2 * segments, starts + 4 * segments];
  const map = new Map();
  for (let i = 0; i < segments; i++) {
    const [end, start] = [cmap.readUInt16BE(ends + 2 * i), cmap.readUInt16BE(starts + 2 * i)];
    assert.equal(cmap.readUInt16BE(ranges + 2 * i), 0, 'the delta alone maps a character to its glyph');
    if (start === 0xffff) continue;
    for (let c = start; c <= end; c++) map.set(c, (c + cmap.readUInt16BE(deltas + 2 * i)) & 0xffff);
  }
  return map;
}

// The characters a stylesheet's @font-face for `family` declares in its unicode-range.
function declared(css, family) {
  const face = new RegExp(`@font-face\\s*{[^}]*font-family:\\s*'${family}'[^}]*}`).exec(css);
  assert.ok(face, `an @font-face for ${family}`);
  const range = /unicode-range:([^;]+);/.exec(face[0]);
  assert.ok(range, `a unicode-range for ${family}`);
  const set = new Set();
  for (const part of range[1].split(',')) {
    const m = /^U\+([0-9A-F]+)(?:-([0-9A-F]+))?$/i.exec(part.trim());
    assert.ok(m, `a unicode-range item: ${part}`);
    for (let c = parseInt(m[1], 16); c <= parseInt(m[2] ?? m[1], 16); c++) set.add(c);
  }
  return set;
}

// The tables of any WOFF2 file, as stored (a transformed table is returned in its transformed form).
const KNOWN = ['cmap', 'head', 'hhea', 'hmtx', 'maxp', 'name', 'OS/2', 'post', 'cvt ', 'fpgm', 'glyf', 'loca', 'prep', 'CFF ', 'VORG', 'EBDT', 'EBLC', 'gasp', 'hdmx', 'kern', 'LTSH', 'PCLT', 'VDMX', 'vhea', 'vmtx', 'BASE', 'GDEF', 'GPOS', 'GSUB', 'EBSC', 'JSTF', 'MATH', 'CBDT', 'CBLC', 'COLR', 'CPAL', 'SVG ', 'sbix', 'acnt', 'avar', 'bdat', 'bloc', 'bsln', 'cvar', 'fdsc', 'feat', 'fmtx', 'fvar', 'gvar', 'hsty', 'just', 'lcar', 'mort', 'morx', 'opbd', 'prop', 'trak', 'Zapf', 'Silf', 'Glat', 'Gloc', 'Feat', 'Sill'];
function anyWoff2(file) {
  let at = 48;
  const listed = [];
  const number = () => {
    let n = 0;
    for (;;) {
      const byte = file[at++];
      n = n * 128 + (byte & 0x7f);
      if (!(byte & 0x80)) return n;
    }
  };
  for (let i = 0; i < file.readUInt16BE(12); i++) {
    const flags = file[at++];
    const tag = (flags & 0x3f) === 63 ? file.toString('latin1', at, (at += 4)) : KNOWN[flags & 0x3f];
    const version = flags >> 6;
    const transformed = tag === 'glyf' || tag === 'loca' ? version === 0 : version !== 0;
    const length = number();
    listed.push({ tag, stored: transformed ? number() : length });
  }
  const data = brotliDecompressSync(file.subarray(at, at + file.readUInt32BE(20)));
  const tables = {};
  let offset = 0;
  for (const { tag, stored } of listed) {
    tables[tag] = data.subarray(offset, offset + stored);
    offset += stored;
  }
  return tables;
}

const boundsOf = (glyph) => {
  const pts = glyph.contours.flat();
  return { xMin: Math.min(...pts.map((p) => p.x)), yMin: Math.min(...pts.map((p) => p.y)), xMax: Math.max(...pts.map((p) => p.x)), yMax: Math.max(...pts.map((p) => p.y)) };
};
const area = (contour) => contour.reduce((sum, p, i) => sum + (p.x * contour[(i + 1) % contour.length].y - contour[(i + 1) % contour.length].x * p.y) / 2, 0);

// ---- the file ------------------------------------------------------------------------------------

test('the committed font is what the script draws', () => {
  const committed = readWoff2(readFileSync(OUTPUT));
  assert.deepEqual(Object.keys(committed).sort(), Object.keys(font.tables).sort());
  for (const tag of Object.keys(font.tables)) {
    assert.ok(committed[tag].equals(font.tables[tag]), `the ${tag} table of psyche-lines.woff2 differs: run \`npm run lines\` in website/ and commit the file`);
  }
});

test('the drawing does not vary: two runs give the same font, and it adds up as a font file', () => {
  const again = buildFont();
  assert.ok(again.sfnt.equals(font.sfnt));
  assert.equal(checksum(font.sfnt), 0xb1b0afba);
  const woff2 = toWoff2(font.tables);
  assert.equal(woff2.readUInt32BE(8), woff2.length, 'the length in the header is the length of the file');
  assert.equal(woff2.readUInt32BE(16), font.sfnt.length, 'the header gives the size of the font it holds');
  const back = readWoff2(woff2);
  for (const tag of Object.keys(font.tables)) assert.ok(back[tag].equals(font.tables[tag]), tag);
});

// ---- what it covers ------------------------------------------------------------------------------

test('it covers all of U+2500 to U+257F, the four triangles and the two arrows, and the stylesheet says so', () => {
  const mapped = characters(font.tables.cmap);
  const wanted = [...Array.from({ length: 0x80 }, (_, i) => 0x2500 + i), 0x25b2, 0x25ba, 0x25bc, 0x25c4, 0x2190, 0x2192];
  assert.deepEqual([...mapped.keys()].sort((a, b) => a - b), wanted.sort((a, b) => a - b));
  COVERED.forEach((code, i) => assert.equal(mapped.get(code), i + 1, `U+${code.toString(16)} is glyph ${i + 1}`));
  assert.deepEqual([...declared(FONTS_CSS, 'Psyche Lines')].sort((a, b) => a - b), [...mapped.keys()].sort((a, b) => a - b), 'unicode-range in styles/fonts.css lists exactly the characters of the font');
});

test('the mono stack puts the face right after the Martian Mono faces, ahead of every system face', () => {
  assert.match(GLOBAL_CSS, /--font-mono:\s*'Martian Mono Variable',\s*'Martian Mono Fallback',\s*'Psyche Lines',\s*ui-monospace/);
});

// ---- the grid ------------------------------------------------------------------------------------

test('every glyph is as wide as a Martian Mono glyph, and the vertical metrics are its own', () => {
  const { hhea, hmtx, head } = font.tables;
  assert.equal(ADVANCE, 700);
  assert.equal(head.readUInt16BE(18), UPM);
  assert.equal(hhea.readUInt16BE(10), ADVANCE);
  assert.equal(hhea.readUInt16BE(34), glyphs.length, 'a metric for every glyph');
  for (let i = 0; i < glyphs.length; i++) assert.equal(hmtx.readUInt16BE(4 * i), ADVANCE, `glyph ${i}`);
  // The Latin file of Martian Mono that the site serves: its advance and its line metrics.
  const martian = anyWoff2(readFileSync(MARTIAN));
  assert.equal(martian.head.readUInt16BE(18), UPM);
  assert.equal(martian.hhea.readUInt16BE(10), ADVANCE, 'Martian Mono is 0.7 em wide');
  assert.equal(martian.hhea.readInt16BE(4), hhea.readInt16BE(4), 'the same ascent');
  assert.equal(martian.hhea.readInt16BE(6), hhea.readInt16BE(6), 'the same descent');
  assert.equal(martian.hhea.readInt16BE(8), hhea.readInt16BE(8), 'the same line gap');
});

test('a light line is the thickness of Martian Mono\'s hyphen and runs along its middle', () => {
  // The hyphen of Martian Mono at regular weight spans y 300 to 400 (read from the font, 2026-11).
  const { xMin, yMin, xMax, yMax } = boundsOf(glyphOf(0x2500));
  assert.deepEqual([yMin, yMax], [300, 400]);
  assert.deepEqual([xMin, xMax], [-DESIGN.BLEED, ADVANCE + DESIGN.BLEED], 'it runs past the cell a little, so a row of them has no seam');
  assert.equal(glyphOf(0x2500).contours.length, 1);
  assert.equal(glyphOf(0x2500).contours[0].length, 4);
});

test('a vertical line fills a code block\'s line, so the rails of a tree are unbroken', () => {
  const { xMin, yMin, xMax, yMax } = boundsOf(glyphOf(0x2502));
  assert.deepEqual([xMin, xMax], [300, 400]);
  assert.ok(yMax >= DESIGN.LINE_TOP, 'it reaches the top of a 1.75 em line');
  assert.ok(yMin <= DESIGN.LINE_BOTTOM, 'and its bottom');
  assert.deepEqual([yMin, yMax], [DESIGN.BOTTOM, DESIGN.TOP]);
  // The line is 1.75 em, Starlight's --sl-line-height, which the code blocks use.
  assert.equal(DESIGN.LINE_TOP - DESIGN.LINE_BOTTOM, 1750);
});

test('each arm of a box-drawing character reaches the edge of its cell, and no other part does', () => {
  for (const [code, spec] of Object.entries(ARMS)) {
    const { xMin, yMin, xMax, yMax } = boundsOf(glyphOf(Number(code)));
    const name = `U+${Number(code).toString(16).toUpperCase()}`;
    assert.equal(xMin === -DESIGN.BLEED, spec[0] !== '.', `${name} left`);
    assert.equal(xMax === ADVANCE + DESIGN.BLEED, spec[1] !== '.', `${name} right`);
    assert.equal(yMax === DESIGN.TOP, spec[2] !== '.', `${name} up`);
    assert.equal(yMin === DESIGN.BOTTOM, spec[3] !== '.', `${name} down`);
  }
});

test('lines that meet are one outline, with no shape drawn over another', () => {
  const contours = (code) => glyphOf(code).contours.map((c) => c.length);
  assert.deepEqual(contours(0x253c), [12]); // a light cross
  assert.deepEqual(contours(0x251c), [8]); // a light T
  assert.deepEqual(contours(0x250c), [6]); // a light corner
  assert.deepEqual(contours(0x2550), [4, 4]); // a double line is two bars
  assert.deepEqual(contours(0x256c), [6, 6, 6, 6]); // four corners round an open middle
});

test('the dashes repeat across cells: the gap at a cell\'s edges is as wide as the gaps between dashes', () => {
  for (const [code, [count, , vertical]] of Object.entries(DASHES)) {
    const spans = glyphOf(Number(code)).contours
      .map((c) => (vertical ? [Math.min(...c.map((p) => p.y)), Math.max(...c.map((p) => p.y))] : [Math.min(...c.map((p) => p.x)), Math.max(...c.map((p) => p.x))]))
      .sort((a, b) => a[0] - b[0]);
    assert.equal(spans.length, count);
    const [from, to] = vertical ? [DESIGN.LINE_BOTTOM, DESIGN.LINE_TOP] : [0, ADVANCE];
    const between = spans.slice(1).map((s, i) => s[0] - spans[i][1]);
    const edges = spans[0][0] - from + (to - spans[count - 1][1]);
    for (const gap of between) assert.ok(Math.abs(gap - edges) <= 2, `U+${Number(code).toString(16)}: ${gap} between dashes, ${edges} at the edges`);
  }
});

test('every outline is clockwise, a hole the other way, and no coordinate leaves the 16-bit range', () => {
  for (const glyph of glyphs) {
    for (const contour of glyph.contours) {
      assert.ok(contour.length >= 3);
      assert.ok(contour[0].on, 'a contour starts on the curve');
      for (const p of contour) assert.ok(Number.isInteger(p.x) && Number.isInteger(p.y) && Math.abs(p.x) < 4000 && Math.abs(p.y) < 4000);
    }
    // the total ink: outlines run clockwise (negative area) and holes counter-clockwise
    const ink = -glyph.contours.reduce((sum, c) => sum + area(c), 0);
    assert.ok(glyph.contours.length === 0 || ink > 0, `code ${glyph.code}: ink ${ink}`);
  }
});

// ---- the union of rectangles ---------------------------------------------------------------------

test('unionRects merges overlapping rectangles into outlines of the same area', () => {
  // A small deterministic generator, so the test never varies.
  let seed = 12345;
  const next = (n) => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed % n;
  };
  for (let round = 0; round < 200; round++) {
    const rects = [];
    for (let i = 0, n = 1 + next(5); i < n; i++) {
      const [x0, y0] = [next(10), next(10)];
      rects.push([x0, y0, x0 + 1 + next(8), y0 + 1 + next(8)]);
    }
    let expected = 0;
    for (let x = 0; x < 20; x++) {
      for (let y = 0; y < 20; y++) if (rects.some(([a, b, c, d]) => x >= a && x < c && y >= b && y < d)) expected++;
    }
    const contours = unionRects(rects);
    assert.equal(-contours.reduce((sum, c) => sum + area(c), 0), expected, JSON.stringify(rects));
    for (const c of contours) {
      c.forEach((p, i) => {
        const [q, r] = [c[(i + 1) % c.length], c[(i + c.length - 1) % c.length]];
        assert.ok(p.x === q.x || p.y === q.y, 'every edge is horizontal or vertical');
        assert.ok(!((p.x === q.x && p.x === r.x) || (p.y === q.y && p.y === r.y)), 'no point lies on a straight run');
      });
    }
  }
});

test('unionRects keeps a hole, counter-clockwise inside its outline', () => {
  const ring = unionRects([[0, 0, 30, 10], [0, 20, 30, 30], [0, 0, 10, 30], [20, 0, 30, 30]]);
  assert.deepEqual(ring.map((c) => Math.sign(area(c))).sort(), [-1, 1]);
  assert.equal(-ring.reduce((sum, c) => sum + area(c), 0), 900 - 100);
});
