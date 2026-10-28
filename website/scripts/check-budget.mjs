// Fails the build when a page ships more gzipped JavaScript, or links more gzipped CSS, than its
// budget. Node built-ins only (fs, path, zlib, url).
//
// What is counted for a page, read from the built HTML in dist/:
//   JS   every external script and module preload the page names, the component and renderer
//        module of every island, the imports of each of those files (followed to the end), and the
//        page's inline scripts. An import is static (`import x from './a.js'`) or dynamic with a
//        literal address (`import('./a.js')`): a dynamic one is a chunk the page loads later, often on
//        idle, and it is still the reader's download. Starlight's search loads its interface this
//        way (about 26 KB gzipped) on every page, which is why a docs page counts about 34 KB, not
//        the 7 KB its first script weighs. Diagrams are drawn ahead of the build and sit in the
//        page as inline SVG (tools/publish/diagrams.py), so they add no script; their bytes are
//        in the HTML, which this check does not count.
//   Also, whatever the sizes: a file in dist/_astro named for a diagram or maths library (mermaid,
//   katex, cytoscape, d3-) fails the build. Such a library once shipped to every docs page
//   through a lazily loaded chunk that only the dynamic imports above can see.
//   CSS  every stylesheet the page links (print included) and its inline <style> blocks.
// Each file is gzipped on its own (zlib level 9), because that is how a browser receives it, and
// a file used twice on a page counts once. Fonts and images are not counted.
//
// Budgets sit 3 percent above the sizes measured when they were set, rounded up to 100 bytes, so
// that a different zlib build does not trip them but real growth does. A page not listed in
// PAGE_BUDGETS falls under DEFAULT_BUDGET, which is the largest budget of any docs page, the research
// roadmap (it hosts the timeline island) excepted. To raise
// a budget on purpose, change the number here and say why in the commit that does it.
//
// Usage: node scripts/check-budget.mjs
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { join, dirname, resolve, relative, sep } from 'node:path';
import { gzipSync } from 'node:zlib';
import { fileURLToPath } from 'node:url';

const DIST = fileURLToPath(new URL('../dist/', import.meta.url));
// Must equal `base` in astro.config.mjs, without the trailing slash handling done below.
const BASE = '/psyche/';

// Bytes, gzipped. The comment on each line is what was measured when the budget was set (JavaScript,
// then CSS). Last set when the site chrome was redrawn: the title strip, the footer's title block, the
// shared registration-corner recipe, the search dialog and the forced-colours rules grew every page's CSS
// by about 1.2 KB (they are in global.css and docs.css), and the script that takes the tab stop off a
// table that does not scroll (components/chrome/TableRegions.astro) and, on stage 2 pages, the one that
// reads the next gate against the reader's day (components/chrome/NextGateClock.astro) grew the
// JavaScript of the docs pages by up to about 400 bytes. Every line was reset again when the roadmap
// and the status page were drawn as ruled sheets: the one roadmap skin (styles/plan.css, now holding the
// timeline, the gate list and the phase list that the landing page drew from a stylesheet of its own) and
// the readout (styles/readout.css) are in the CSS bundle every docs page loads, which grew it by about
// 450 bytes. /status/ grew by about 1.6 KB of CSS more, for the captured-run facts and the brick board
// with its key (styles/status.css, which no other page loads), while the count-up and the spotlight
// script that the old stats band and brick cards loaded took about 1.1 KB of JavaScript off it; the
// landing page's CSS fell by about 2 KB with its second roadmap stylesheet gone.
const DEFAULT_BUDGET = { js: 37700, css: 39400 };
const PAGE_BUDGETS = {
  '/':                          { js: 114200, css:  42800 }, // 110807,  41534
  '/roadmap/':                  { js: 111500, css:  35400 }, // 108173,  34325
  '/battery/':                  { js: 112700, css:  35500 }, // 109410,  34370
  '/status/':                   { js:  33100, css:  37000 }, //  32089,  35885
  '/research/':                 { js:  35500, css:  35300 }, //  34432,  34259
  '/research/origins/':         { js:  35500, css:  35300 }, //  34432,  34259
  '/research/roadmap/':         { js: 113600, css:  35400 }, // 110195,  34325
  '/research/gates/':           { js:  37700, css:  35300 }, //  36531,  34259
  '/research/test-battery/':    { js:  35800, css:  35300 }, //  34755,  34259
  '/research/claims-and-scope/':{ js:  34900, css:  35300 }, //  33852,  34259
  '/research/engineering/':     { js:  35500, css:  35300 }, //  34432,  34259
  '/research/glossary/':        { js:  34900, css:  35300 }, //  33852,  34259
  '/research/reading-list/':    { js:  34900, css:  35300 }, //  33852,  34259
  '/research/disclosure-policy/':{ js:  35500, css:  35300 }, //  34432,  34259
  '/substrate/overview/':       { js:  36300, css:  39400 }, //  35196,  38181
  '/substrate/architecture/':   { js:  36300, css:  39400 }, //  35196,  38181
  '/substrate/methodology/':    { js:  35100, css:  35300 }, //  34028,  34259
};

const gz = (buf) => gzipSync(buf, { level: 9 }).length;

const cache = new Map();
function read(file) {
  if (!cache.has(file)) cache.set(file, readFileSync(file));
  return cache.get(file);
}

// A page URL such as /psyche/_astro/x.js becomes the file in dist/.
function toFile(url, from) {
  if (/^[a-z][a-z0-9+.-]*:|^\/\//i.test(url)) return { external: url };
  const clean = url.split('#')[0].split('?')[0];
  let abs;
  if (clean.startsWith(BASE)) abs = join(DIST, clean.slice(BASE.length));
  else if (clean.startsWith('/')) return { external: url };
  else abs = resolve(dirname(from), clean);
  return { file: abs };
}

function attr(tag, name) {
  const m = tag.match(new RegExp(`\\s${name}\\s*=\\s*(?:"([^"]*)"|'([^']*)'|([^\\s>]+))`, 'i'));
  return m ? (m[1] ?? m[2] ?? m[3]) : null;
}

const STATIC_IMPORT = [
  /\b(?:import|export)\s*(?:\{[^}]*\}|\*(?:\s*as\s*[\w$]+)?|[\w$]+(?:\s*,\s*\{[^}]*\})?)\s*from\s*["']([^"']+)["']/g,
  /\bimport\s*["']([^"']+)["']/g,
  // import('./chunk.js'): a literal address only; one built at run time cannot be read here
  /\bimport\s*\(\s*[`"']([^`"'$]+)[`"']\s*\)/g,
];

// Libraries that must never reach a docs page again; matched against file names in dist/_astro.
const FORBIDDEN_CHUNKS = /mermaid|katex|cytoscape|(?:^|[^a-z])d3-/i;

function specifiers(source, patterns) {
  const out = [];
  for (const re of patterns) for (const m of source.matchAll(re)) out.push(m[1]);
  return out;
}
const relative_ = (s) => s.startsWith('./') || s.startsWith('../') || s.startsWith('/');

// A JS file and everything it imports statically.
function closure(roots, problems, page) {
  const seen = new Set();
  const stack = [...roots];
  while (stack.length) {
    const file = stack.pop();
    if (seen.has(file)) continue;
    if (!existsSync(file)) {
      problems.push(`${page}: ${relative(DIST, file)} is referenced but was not built`);
      continue;
    }
    seen.add(file);
    const src = read(file).toString('utf8');
    for (const spec of specifiers(src, STATIC_IMPORT)) {
      if (!relative_(spec)) continue;
      const r = toFile(spec, file);
      if (r.file) stack.push(r.file);
    }
  }
  return seen;
}

function htmlFiles(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) {
      if (name === 'pagefind' || name === '_astro') continue;
      out.push(...htmlFiles(p));
    } else if (name.endsWith('.html')) out.push(p);
  }
  return out.sort();
}

function measure(htmlPath, problems) {
  const route = '/' + relative(DIST, htmlPath).split(sep).join('/').replace(/index\.html$/, '');
  const html = readFileSync(htmlPath, 'utf8');
  const page = route === '/' ? '/' : route;

  const jsRoots = new Set();
  const cssFiles = new Set();
  let inlineJs = 0;
  let inlineCss = 0;
  const external = [];
  const add = (set, url) => {
    const r = toFile(url, htmlPath);
    if (r.external) external.push(r.external);
    else set.add(r.file);
  };

  for (const m of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\b[^>]*>/gi)) {
    const type = (attr(m[1], 'type') || '').toLowerCase();
    if (type && !['module', 'text/javascript', 'application/javascript'].includes(type)) continue;
    const src = attr(m[1], 'src');
    if (src) add(jsRoots, src);
    else if (m[2].trim()) {
      inlineJs += gz(Buffer.from(m[2]));
      for (const spec of specifiers(m[2], STATIC_IMPORT)) if (relative_(spec)) add(jsRoots, spec);
    }
  }
  for (const m of html.matchAll(/<link\b[^>]*>/gi)) {
    const rel = (attr(m[0], 'rel') || '').toLowerCase().split(/\s+/);
    const href = attr(m[0], 'href');
    if (!href) continue;
    if (rel.includes('stylesheet')) add(cssFiles, href);
    else if (rel.includes('modulepreload')) add(jsRoots, href);
  }
  for (const m of html.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)) {
    if (m[1].trim()) inlineCss += gz(Buffer.from(m[1]));
  }
  for (const m of html.matchAll(/<astro-island\b[^>]*>/gi)) {
    for (const name of ['component-url', 'renderer-url']) {
      const url = attr(m[0], name);
      if (url) add(jsRoots, url);
    }
  }
  for (const url of external) {
    problems.push(`${page}: ${url} is loaded from another origin and cannot be measured; host it with the site`);
  }

  const eager = closure(jsRoots, problems, page);

  const sum = (files) => [...files].reduce((n, f) => n + (existsSync(f) ? gz(read(f)) : 0), 0);
  const js = sum(eager) + inlineJs;
  const css = sum(cssFiles) + inlineCss;
  return { page, js, css };
}

if (!existsSync(DIST)) {
  console.error('check-budget: dist/ does not exist; build the site first');
  process.exit(1);
}

const problems = [];
const assets = join(DIST, '_astro');
if (existsSync(assets)) {
  for (const name of readdirSync(assets)) {
    if (FORBIDDEN_CHUNKS.test(name)) problems.push(`dist/_astro/${name}: a diagram or maths library is in the build`);
  }
}
const rows = htmlFiles(DIST)
  .filter((p) => !p.endsWith(`${sep}404.html`))
  .map((p) => measure(p, problems));

const over = [];
const pad = (v, n) => String(v).padStart(n);
console.log('check-budget: gzipped bytes per page (JS on load; CSS linked plus inline)');
console.log(`${'page'.padEnd(30)}${pad('js', 9)}${pad('budget', 9)}${pad('css', 9)}${pad('budget', 9)}`);
for (const r of rows) {
  const b = PAGE_BUDGETS[r.page] || DEFAULT_BUDGET;
  const flags = [];
  if (r.js > b.js) flags.push(`JS ${r.js} B is over its budget of ${b.js} B by ${r.js - b.js} B`);
  if (r.css > b.css) flags.push(`CSS ${r.css} B is over its budget of ${b.css} B by ${r.css - b.css} B`);
  for (const f of flags) over.push(`${r.page}: ${f}`);
  console.log(`${r.page.padEnd(30)}${pad(r.js, 9)}${pad(b.js, 9)}${pad(r.css, 9)}${pad(b.css, 9)}${flags.length ? '  OVER' : ''}`);
}
for (const p of problems) console.error(`check-budget: ${p}`);
for (const o of over) console.error(`check-budget: ${o}`);
if (problems.length || over.length) {
  console.error(`check-budget: ${problems.length + over.length} problem(s)`);
  process.exit(1);
}
console.log(`check-budget: within budget; ${rows.length} page(s) read`);
