// The documentation's stylesheet and script (src/kit/docs/docs.css and docs.js, written by the page
// import, never by hand) style and enhance markup that this repository writes by hand: the frame
// (src/layouts/Docs.astro), its parts (src/components/devdocs/*.astro) and the pages built on it. This
// test holds the two sides together: every documentation class (k-doc*, k-toc*, k-filter*, k-devhome*,
// k-devstart*, k-diagram*) and every data-k-* hook the imported files use must be written by one of the
// hand-written files, so a renamed class in a new import cannot leave a part unstyled or a control dead
// without a failing test.
//
// Read: sources only (the imported files are tracked; nothing staged or built is read).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const WEB = fileURLToPath(new URL('../', import.meta.url));
const SRC = join(WEB, 'src');
const DOCS_CSS = join(SRC, 'kit', 'docs', 'docs.css');
const DOCS_JS = join(SRC, 'kit', 'docs', 'docs.js');

// Created by docs.js itself at run time, never by the server: the diagram's "Scrolls sideways" line and
// its reading as text.
const MADE_BY_SCRIPT = new Set(['k-diagram__note', 'k-diagram__reading']);
// Written by the document route (the page that renders each document in the frame), which does not
// exist yet: until it does, nothing may write these. The test below fails as soon as a file writes one,
// so this list is emptied by the change that writes them.
const DOCUMENT_ROUTE_ONLY = new Set(['k-doc', 'k-doc__body', 'k-doc__desc']);

const FAMILY = /(?<![\w-])k-(?:doc|toc|filter|devhome|devstart|diagram)[a-z0-9_-]*/g;
const HOOK = /(?<![\w-])data-k-[a-z0-9-]*[a-z0-9]/g;

function walk(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(join(dir, e.name)) : [join(dir, e.name)]));
}
const rel = (p) => relative(WEB, p).split('\\').join('/');

/** The hand-written files of the documentation: the frame, its parts and every page built on the frame. */
export function writers() {
  const files = [join(SRC, 'layouts', 'Docs.astro'), ...walk(join(SRC, 'components', 'devdocs')).filter((p) => p.endsWith('.astro'))];
  for (const p of walk(join(SRC, 'pages')).filter((f) => f.endsWith('.astro'))) {
    const text = readFileSync(p, 'utf8');
    if (text.includes("from '@/layouts/Docs.astro'") || text.includes('from "@/layouts/Docs.astro"')) files.push(p);
  }
  return files;
}

/** Whether `word` occurs in `text` with no letter, digit, "_" or "-" right before or after it. */
export function writes(text, word) {
  const part = /[\w-]/;
  for (let i = text.indexOf(word); i >= 0; i = text.indexOf(word, i + 1)) {
    const before = text[i - 1] ?? '';
    const after = text[i + word.length] ?? '';
    if (!part.test(before) && !part.test(after)) return true;
  }
  return false;
}

/** The classes and hooks a stylesheet or script of the documentation uses. */
export function used(text) {
  const hooks = new Set(text.match(HOOK) ?? []);
  // a hook's name is not a class: take the hooks out before the classes are read
  const rest = text.replace(HOOK, ' ');
  const classes = new Set(rest.match(FAMILY) ?? []);
  return { classes, hooks };
}

test('the reader itself: classes and hooks, and a word only where it stands whole', () => {
  const { classes, hooks } = used(".k-docnav__input { } [data-k-docfilter-count] .k-toc a; q('[data-k-toc]'); x.className = 'k-vh k-diagram__note';");
  assert.deepEqual([...classes].sort(), ['k-diagram__note', 'k-docnav__input', 'k-toc']);
  assert.deepEqual([...hooks].sort(), ['data-k-docfilter-count', 'data-k-toc']);
  assert.ok(writes('<p class="k-doc__title">', 'k-doc__title'));
  assert.ok(!writes('<p class="k-doc__title">', 'k-doc'));
  assert.ok(!writes('<p data-k-docfilter-count>', 'data-k-docfilter'));
  assert.ok(writes("{ class: 'k-docs' }", 'k-docs'));
});

test('the documentation stylesheet and script have been imported', () => {
  for (const f of [DOCS_CSS, DOCS_JS]) assert.ok(existsSync(f), `${rel(f)} is missing: run the page import`);
});

test('every documentation class and hook that docs.css and docs.js use is written by the frame, its parts or its pages', () => {
  const css = used(readFileSync(DOCS_CSS, 'utf8'));
  const js = used(readFileSync(DOCS_JS, 'utf8'));
  const classes = new Set([...css.classes, ...js.classes]);
  const hooks = new Set([...css.hooks, ...js.hooks]);
  assert.ok(classes.size >= 30, `only ${classes.size} documentation classes read from the imported files`);
  assert.ok(hooks.size >= 5, `only ${hooks.size} hooks read from the imported files`);
  const files = writers();
  assert.ok(files.length >= 6, `only ${files.length} hand-written documentation files found`);
  const text = files.map((f) => readFileSync(f, 'utf8')).join('\n');
  const missing = [];
  for (const c of classes) {
    if (MADE_BY_SCRIPT.has(c) || DOCUMENT_ROUTE_ONLY.has(c)) continue;
    if (!writes(text, c)) missing.push(`class ${c}`);
  }
  for (const h of hooks) if (!writes(text, h)) missing.push(`hook ${h}`);
  assert.deepEqual(missing, [], `used by src/kit/docs/ but written by none of ${files.map(rel).join(', ')}`);
  // the script's own lines and the classes it reads, not left to the stylesheet alone
  for (const c of ['k-docs', 'k-docnav__search', 'k-docnav__none', 'k-docindex__item', 'k-docindex__none', 'k-filter']) assert.ok(js.classes.has(c), `docs.js no longer reads .${c}`);
});

test('what only the script makes is never in the server markup, and what only the document route writes is not written yet', () => {
  const text = writers().map((f) => readFileSync(f, 'utf8')).join('\n');
  for (const c of MADE_BY_SCRIPT) assert.ok(!writes(text, c), `${c} is made by docs.js; the server must not write it`);
  for (const c of DOCUMENT_ROUTE_ONLY) assert.ok(!writes(text, c), `${c} is now written: take it off DOCUMENT_ROUTE_ONLY in this test`);
  // the body carries no data-title (kit.js would put the site-wide sentence in the page's title)
  assert.ok(!writes(text, 'data-title'), 'a documentation page writes data-title on its body');
});
