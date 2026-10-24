// Fails the build when words run together on the custom pages.
//
// Astro compresses whitespace the way JSX does: a line break next to an {expression} or an
// inline element disappears, so "on⏎{name}" renders as "onCPython" and "the⏎<a>" as "the<a>".
// This reads the built HTML of the hand-written pages and reports text glued to an inline element
// or to an expression's output.
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIST = fileURLToPath(new URL('../dist/', import.meta.url));
const PAGES = ['index.html', 'roadmap/index.html', 'battery/index.html', 'status/index.html'];

const RAW_RULES = [
  [/[A-Za-z0-9,.;:]<(a|code|strong|em|span|time)[\s>]/g, 'text glued to the start of an inline element'],
  [/<\/(a|code|strong|em|time)>[A-Za-z0-9(]/g, 'text glued to the end of an inline element'],
];
const TEXT_RULES = [
  [/\b\d+[a-z]{3,}\b/g, 'a number glued to a word'],
  [/\b(?:on|of|in|the|read|with|across|and|at|from|to|by)(?=[A-Z0-9])[A-Z0-9]\w*/g, 'a word glued to a name or number'],
];

function main(html) {
  const m = html.match(/<main[\s\S]*?<\/main>/);
  return (m ? m[0] : html).replace(/<(script|style|svg)\b[\s\S]*?<\/\1>/g, '');
}

let problems = 0;
for (const page of PAGES) {
  const file = join(DIST, page);
  if (!existsSync(file)) {
    console.error(`check-spacing: ${page} was not built`);
    problems++;
    continue;
  }
  const html = main(readFileSync(file, 'utf8'));
  const text = html.replace(/<[^>]+>/g, '');
  for (const [rule, what] of RAW_RULES) {
    for (const m of html.matchAll(rule)) {
      console.error(`check-spacing: ${page}: ${what}: …${html.slice(Math.max(0, m.index - 30), m.index + 30).replace(/\s+/g, ' ')}…`);
      problems++;
    }
  }
  for (const [rule, what] of TEXT_RULES) {
    for (const m of text.matchAll(rule)) {
      console.error(`check-spacing: ${page}: ${what}: "${m[0]}"`);
      problems++;
    }
  }
}
if (problems) {
  console.error(`check-spacing: ${problems} problem(s)`);
  process.exit(1);
}
console.log(`check-spacing: clean; ${PAGES.length} page(s) read`);
