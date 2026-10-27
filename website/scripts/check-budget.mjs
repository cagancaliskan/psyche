// Fails the build when a page ships more gzipped JavaScript, or links more gzipped CSS, than its
// budget. Node built-ins only (fs, path, zlib, url).
//
// What is counted for a page, read from the built HTML in dist/:
//   JS   every external script and module preload the page names, the component and renderer
//        module of every island, the static imports of each of those files (followed to the
//        end), and the page's inline scripts. When the page holds a Mermaid diagram, the
//        module the page script loads on demand to draw it, with its static imports, is
//        counted as well, because that page always downloads it. The chunks that module
//        loads in turn for one diagram type or another are not followed: which of them load
//        depends on the diagram.
//   CSS  every stylesheet the page links (print included) and its inline <style> blocks.
// Each file is gzipped on its own (zlib level 9), because that is how a browser receives it, and
// a file used twice on a page counts once. Fonts and images are not counted.
//
// Budgets sit 3 percent above the sizes measured when they were set, rounded up to 100 bytes, so
// that a different zlib build does not trip them but real growth does. A page not listed in
// PAGE_BUDGETS falls under DEFAULT_BUDGET, which is the largest budget of any docs page. To raise
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

// Bytes, gzipped. The comment on each line is what was measured when the budget was set.
const DEFAULT_BUDGET = { js: 186500, css: 38500 };
const PAGE_BUDGETS = {
  '/':                            { js:  88700, css: 44600 }, // 86037, 43259
  '/roadmap/':                    { js:  86800, css: 34500 }, // 84210, 33484
  '/battery/':                    { js:  90300, css: 34600 }, // 87591, 33529
  '/status/':                     { js:  10100, css: 34500 }, //  9739, 33418
  '/research/':                   { js: 185000, css: 34500 }, // 179602, 33418
  '/research/origins/':           { js: 185000, css: 34500 }, // 179602, 33418
  '/research/roadmap/':           { js: 261600, css: 34500 }, // 253927, 33484
  '/research/gates/':             { js: 186400, css: 34500 }, // 180958, 33418
  '/research/test-battery/':      { js: 185400, css: 34500 }, // 179925, 33418
  '/research/claims-and-scope/':  { js: 184400, css: 34500 }, // 178973, 33418
  '/research/engineering/':       { js: 185000, css: 34500 }, // 179602, 33418
  '/research/glossary/':          { js:  10300, css: 34500 }, //   9943, 33418
  '/research/reading-list/':      { js:  10300, css: 34500 }, //   9943, 33418
  '/research/disclosure-policy/': { js: 185000, css: 34500 }, // 179602, 33418
  '/substrate/overview/':         { js:  12700, css: 38500 }, //  12266, 37340
  '/substrate/architecture/':     { js:  12100, css: 38500 }, //  11740, 37340
  '/substrate/methodology/':      { js:  10900, css: 34500 }, //  10572, 33418
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
];
const DYNAMIC_IMPORT = /\bimport\(\s*["'`]([^"'`]+)["'`]\s*\)/g;

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
  let lazy = new Set();
  if (/class="[^"]*\bmermaid\b/.test(html)) {
    const targets = [];
    for (const file of eager) {
      for (const spec of specifiers(read(file).toString('utf8'), [DYNAMIC_IMPORT])) {
        if (!relative_(spec)) continue;
        const r = toFile(spec, file);
        if (r.file && /mermaid\.core/.test(r.file)) targets.push(r.file);
      }
    }
    // A page with a diagram that finds no renderer module would otherwise count none of its
    // weight and pass quietly; a bundler change that moves the dynamic import must fail loudly.
    if (!targets.length) {
      problems.push(`${page}: has a Mermaid diagram but the renderer module was not found; the budget cannot be measured`);
    }
    lazy = closure(targets, problems, page);
    for (const f of eager) lazy.delete(f);
  }

  const sum = (files) => [...files].reduce((n, f) => n + (existsSync(f) ? gz(read(f)) : 0), 0);
  const jsEager = sum(eager) + inlineJs;
  const jsLazy = sum(lazy);
  const css = sum(cssFiles) + inlineCss;
  return { page, js: jsEager + jsLazy, jsEager, jsLazy, css };
}

if (!existsSync(DIST)) {
  console.error('check-budget: dist/ does not exist; build the site first');
  process.exit(1);
}

const problems = [];
const rows = htmlFiles(DIST)
  .filter((p) => !p.endsWith(`${sep}404.html`))
  .map((p) => measure(p, problems));

const over = [];
const pad = (v, n) => String(v).padStart(n);
console.log('check-budget: gzipped bytes per page (JS on load plus the diagram renderer; CSS linked plus inline)');
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
