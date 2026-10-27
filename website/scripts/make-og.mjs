// Draws the social card: the 1200 x 630 image that every page's link preview shows (og:image).
//
//   npm run og                       draw it again from the ledger's program state
//   node scripts/make-og.mjs --chrome PATH   (or CHROME_PATH) pick the browser
//
// The card names the active stage of the project, so it is never edited by hand. The text comes from
// tools/publish/og.py (`--card`), which reads `program` in tools/ledger.json; scripts/og-card.html is
// the template; Chrome, which is already on the machine, draws it at exactly 1200 x 630. Three files
// are written, and all three are committed:
//
//   brand/psyche-social.png    the card (the brand's own copy), with its stage line also written into
//                              the file as a tEXt chunk
//   website/public/og.png      a byte copy of it, what the site serves
//   brand/psyche-social.json   the stage line it was drawn for and the sha256 of the PNG
//
// `python3 tools/publish/og.py --check` (governance and `npm run build` both run it) fails when the
// ledger's active stage is no longer the one the card was drawn for, or when either PNG is not the
// image the sidecar describes. Run this script after any change to `program` in the ledger, to the
// template, to the brand wordmark or to the card text in og.py.
//
// Fonts are the site's own (Instrument Sans and Martian Mono from node_modules, Latin subsets),
// embedded in the page as data: addresses, so the template loads nothing from anywhere.
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { crc32 } from 'node:zlib';
import { copyFileSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { findChrome, shoot } from './chrome-shot.mjs';

const SITE = fileURLToPath(new URL('../', import.meta.url));
const REPO = fileURLToPath(new URL('../../', import.meta.url));
const WIDTH = 1200;
const HEIGHT = 630;

const arg = (name) => {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : undefined;
};

const escapeHtml = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
// A hyphenated word stays on one line ("brain-inspired" is never broken after "brain-").
const keepHyphenated = (s) => escapeHtml(s).replace(/\S+-\S+/g, (w) => `<span class="nb">${w}</span>`);
const font = (rel) => `data:font/woff2;base64,${readFileSync(SITE + rel).toString('base64')}`;

function cardText() {
  const out = execFileSync('python3', ['-B', 'tools/publish/og.py', '--card'], { cwd: REPO, encoding: 'utf8' });
  const card = JSON.parse(out);
  for (const key of ['stage', 'tagline', 'url', 'alt']) {
    if (typeof card[key] !== 'string' || !card[key]) throw new Error(`og.py --card gave no ${key}`);
  }
  return card;
}

const card = cardText();
let html = readFileSync(SITE + 'scripts/og-card.html', 'utf8');
const fill = {
  __FONT_SANS__: font('node_modules/@fontsource-variable/instrument-sans/files/instrument-sans-latin-wght-normal.woff2'),
  __FONT_MONO__: font('node_modules/@fontsource-variable/martian-mono/files/martian-mono-latin-wght-normal.woff2'),
  __WORDMARK__: readFileSync(REPO + 'brand/psyche-wordmark-dark.svg', 'utf8'),
  __STAGE__: escapeHtml(card.stage),
  __TAGLINE__: keepHyphenated(card.tagline),
  __URL__: escapeHtml(card.url),
};
for (const [placeholder, value] of Object.entries(fill)) {
  if (!html.includes(placeholder)) throw new Error(`scripts/og-card.html has no ${placeholder}`);
  html = html.split(placeholder).join(value);
}
const left = html.match(/__[A-Z_]+__/);
if (left) throw new Error(`scripts/og-card.html still holds ${left[0]} after filling`);

// The stage line goes into the PNG as a tEXt chunk (keyword "psyche-stage", Latin-1), right after the
// header, so the image file itself says which stage it was drawn for; og.py reads it back.
function withStageText(png, text) {
  if ([...text].some((c) => c.codePointAt(0) > 0xff)) throw new Error(`"${text}" cannot be written as Latin-1 text`);
  const data = Buffer.concat([Buffer.from('psyche-stage', 'latin1'), Buffer.from([0]), Buffer.from(text, 'latin1')]);
  const type = Buffer.from('tEXt', 'latin1');
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([type, data])) >>> 0);
  const afterHeader = 8 + 4 + 4 + 13 + 4; // signature, then the IHDR chunk: length, type, data, crc
  return Buffer.concat([png.subarray(0, afterHeader), length, type, data, crc, png.subarray(afterHeader)]);
}

const png = withStageText(shoot({ html, width: WIDTH, height: HEIGHT, chrome: findChrome(arg('--chrome')) }), card.stage);
writeFileSync(REPO + 'brand/psyche-social.png', png);
copyFileSync(REPO + 'brand/psyche-social.png', REPO + 'website/public/og.png');

const sidecar = {
  stage: card.stage,
  tagline: card.tagline,
  alt: card.alt,
  sha256: createHash('sha256').update(png).digest('hex'),
  width: WIDTH,
  height: HEIGHT,
  generator: 'website/scripts/make-og.mjs',
};
writeFileSync(REPO + 'brand/psyche-social.json', JSON.stringify(sidecar, null, 2) + '\n');
console.log(`make-og: drew "${card.stage}" (${png.length} bytes, sha256 ${sidecar.sha256.slice(0, 12)})`);

// The check that governance runs must pass on what was just written.
execFileSync('python3', ['-B', 'tools/publish/og.py', '--check'], { cwd: REPO, stdio: 'inherit' });
