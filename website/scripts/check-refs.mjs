// Fails the build when a page points at an id it does not hold.
//
// A reference inside one page is only a string, and nothing else in the build reads it: a drawing that
// takes its letters from glyphs defined elsewhere on the page (<use href="#...">), a mask or a marker
// (url(#...)), and the names and descriptions that assistive technology reads from another element
// (aria-labelledby, aria-describedby, aria-controls, <label for>). When the id is missing, the browser
// draws nothing or reads nothing, without an error, and the accessibility check cannot tell an empty
// circle from a full one. Links to headings (<a href="#...">) are left to the link validation step.
//
// Every page of dist/ is read, the 404 page included. Node built-ins only.
//
// Usage: node scripts/check-refs.mjs
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIST = fileURLToPath(new URL('../dist/', import.meta.url));

// Every built page: each .html file outside the bundles and the search index.
function pages(dir = DIST, rel = '') {
  const found = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (!['_astro', 'pagefind'].includes(entry.name)) found.push(...pages(join(dir, entry.name), `${rel}${entry.name}/`));
    } else if (entry.name.endsWith('.html')) found.push(`${rel}${entry.name}`);
  }
  return found.sort();
}

// [what points, the attribute pattern, how many ids one value holds]
const REFS = [
  ['<use> href', /<use\b[^>]*?\s(?:xlink:)?href\s*=\s*["']#([^"']+)["']/gi, 'one'],
  ['url(#...)', /\s(?:mask|clip-path|fill|stroke|filter|marker-start|marker-mid|marker-end)\s*=\s*["']url\(#([^)"']+)\)["']/gi, 'one'],
  ['aria-labelledby', /\saria-labelledby\s*=\s*["']([^"']+)["']/gi, 'list'],
  ['aria-describedby', /\saria-describedby\s*=\s*["']([^"']+)["']/gi, 'list'],
  ['aria-controls', /\saria-controls\s*=\s*["']([^"']+)["']/gi, 'list'],
  ['<label for>', /<label\b[^>]*?\sfor\s*=\s*["']([^"']+)["']/gi, 'one'],
];

if (!existsSync(DIST)) {
  console.error('check-refs: dist/ does not exist; build the site first');
  process.exit(1);
}

let problems = 0;
let refs = 0;
const all = pages();
for (const page of all) {
  // Scripts hold strings that look like markup; what they build at run time is not in the file. The
  // removal is repeated until nothing changes, so that no script is left behind by one it joined up.
  let html = readFileSync(join(DIST, page), 'utf8');
  for (let before = ''; before !== html; ) {
    before = html;
    html = html.replace(/<script\b[\s\S]*?<\/script\b[^>]*>/gi, '');
  }
  const ids = new Set([...html.matchAll(/\sid\s*=\s*["']([^"']+)["']/gi)].map((m) => m[1]));
  for (const [what, pattern, arity] of REFS) {
    for (const m of html.matchAll(pattern)) {
      for (const id of arity === 'list' ? m[1].trim().split(/\s+/) : [m[1]]) {
        refs++;
        if (!ids.has(id)) {
          console.error(`check-refs: ${page}: ${what} points at #${id}, which is not on the page`);
          problems++;
        }
      }
    }
  }
}
if (problems) {
  console.error(`check-refs: ${problems} reference(s) to a missing id`);
  process.exit(1);
}
console.log(`check-refs: ${refs} reference(s) on ${all.length} page(s), each to an id on its page`);
