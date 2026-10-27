// Draws the site's raster icons from the brand icon, brand/psyche-icon.svg (the simplified P on its
// dark tile, the same drawing as website/public/favicon.svg), with the Chrome already on the machine.
//
//   npm run icons                            draw every icon again
//   node scripts/make-icons.mjs --chrome PATH   (or CHROME_PATH) pick the browser
//
// Written to website/public/, each one rendered at its exact size (never scaled from another PNG),
// and committed. favicon.svg stays the primary icon; these are for the places that cannot use it.
//
//   favicon-32.png            32 x 32     the tab icon where SVG is not used; rounded tile, clear corners
//   icon-192.png              192 x 192   the web app manifest's icon; rounded tile, clear corners
//   icon-512.png              512 x 512   the same, large
//   apple-touch-icon.png      180 x 180   iOS puts the icon on its own rounded mask and fills any clear
//                                         corner with black, so the tile runs to the edges, opaque
//   icon-512-maskable.png     512 x 512   for Android's adaptive masks, which cut a circle or a squircle
//                                         from the middle: the tile runs to the edges, opaque, and the
//                                         P is scaled and centred to stand inside the safe zone
//
// The safe zone of a maskable icon is the circle of 40 percent of the side around the centre (radius
// 9.6 of 24 units). The brand drawing puts the P at scale 0.7 from (3.6, 3.6); the P occupies
// x 5.63 to 19.42 and y 4.44 to 20.40 of the tile (strokes included, worked out from the path
// coordinates in the SVG: stem 2.9 to 5.5 wide, outer bowl out to 22.6, both in the P's own units),
// so its centre is (12.525, 12.42) and its far corner, where the stem meets the tile's lower left, is
// 10.55 units from it. Scaled by 0.88 about its own centre and moved to the tile's centre, that
// corner is 9.28 units out, inside the 9.6 of the safe zone. The ink is the P alone; the tile colour
// fills the rest.
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { findChrome, shoot } from './chrome-shot.mjs';

const SITE = fileURLToPath(new URL('../', import.meta.url));
const REPO = fileURLToPath(new URL('../../', import.meta.url));
const SOURCE = 'brand/psyche-icon.svg';

const GLYPH = 'translate(3.6 3.6) scale(0.7)';
const GLYPH_CENTRE = [12.525, 12.42];
const SAFE_SCALE = 0.88;

const arg = (name) => {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : undefined;
};

const source = readFileSync(REPO + SOURCE, 'utf8').trim();
if (!source.includes(GLYPH) || !/ rx="5\.5"/.test(source)) {
  throw new Error(`${SOURCE} no longer has the drawing this script expects (the P at ${GLYPH} on a tile with rx="5.5"); update make-icons.mjs`);
}
const square = source.replace(' rx="5.5"', '');
const maskable = square.replace(
  GLYPH,
  `translate(12 12) scale(${SAFE_SCALE}) translate(${-GLYPH_CENTRE[0]} ${-GLYPH_CENTRE[1]}) ${GLYPH}`,
);

const ICONS = [
  { file: 'favicon-32.png', size: 32, svg: source, transparent: true },
  { file: 'icon-192.png', size: 192, svg: source, transparent: true },
  { file: 'icon-512.png', size: 512, svg: source, transparent: true },
  { file: 'apple-touch-icon.png', size: 180, svg: square, transparent: false },
  { file: 'icon-512-maskable.png', size: 512, svg: maskable, transparent: false },
];

const chrome = findChrome(arg('--chrome'));
for (const { file, size, svg, transparent } of ICONS) {
  const html =
    '<!doctype html><meta charset="utf-8"><title>icon</title>' +
    `<style>html,body{margin:0;padding:0;background:transparent;overflow:hidden}svg{display:block;width:${size}px;height:${size}px}</style>` +
    svg;
  const png = shoot({ html, width: size, height: size, transparent, chrome });
  writeFileSync(SITE + 'public/' + file, png);
  console.log(`make-icons: public/${file}  ${size} x ${size}  ${png.length} bytes`);
}
