// Accessibility check of the built site: axe-core over every page of dist/, at WCAG 2.2 AA (the axe
// tags wcag2a, wcag2aa, wcag21a, wcag21aa and wcag22aa), and over the interface states a reader opens
// (on a document: the documentation's page list filtered to nothing; on a page of the documentation: its
// "Pages" list open on a phone, the timeline with a gate chosen, the walk-through stepped, the status
// page's designed bricks shown; on a front page, on a document and on the film: the site's phone menu; on
// a front page and on a document: the theme switch pressed; on a post with designed figures: a figure
// after its control is used; on the documentation's home: its filter with words typed). Exits 1 when any serious
// or critical violation is found, or when a page cannot be audited at all; moderate and minor ones are
// listed but never fail the run, and neither does what axe cannot decide (its "incomplete" results:
// today only text contrast over gradients, pseudo-elements and images, which need a human look).
// The Pages workflow runs it as a blocking step.
//
// Run it after `npm run build`:  node scripts/check-a11y.mjs [--chrome PATH] [--json FILE] [--only SLUGS] [--port N]
// --only takes a comma-separated list of pages (/,research/gates/,404.html) for a quick look while
// working on some; an interface state runs only when its page is among them. CI runs it whole.
//
// This is a development tool and nothing the site ships. Its two packages are not in package.json:
// the script installs them, at the exact versions scripts/a11y-tools/package.json names and with their
// own dependencies as its package-lock.json locks them (`npm ci`), into website/node_modules/.cache/
// psyche-a11y-tools the first time it runs (A11Y_TOOLS_DIR changes where). Code is loaded from there, so
// the directory is created private and refused when someone else owns it or others can write to it, as
// render-diagrams.mjs does with its own. The install is tried three times. It needs Google Chrome or
// Chromium; --chrome or CHROME_PATH names it, otherwise the usual locations are tried. GitHub's Ubuntu
// runners have it.
//
// Exit codes: 0 when the check ran and found nothing serious; 1 when it found a serious or critical
// violation or could not audit a page; 2 when it could not set itself up (the packages would not
// install, no Chrome, or a Chrome that will not start): that says nothing about the site, so a run that exits 2 is worth running again.
//
// The script serves dist/ itself on a free local port (--port N names one) under the site's base path
// and closes the server and the browser before it exits, so nothing is left running.
//
// Each page is loaded four ways: desktop and phone width, light and dark colour scheme, all with
// reduced motion so that nothing is mid-fade when axe measures contrast. The page is scrolled
// through once first, so that anything a page draws when it comes into view has been drawn. A state
// is the same page after the click that opens it; a state that has a way to close is closed again
// after the audit, and the run fails if it does not close as a reader expects.
//
// The theme is set, not left to chance. Every page is on the page kit, which ignores the system's
// colour scheme: a page opens dark and keeps the reader's choice in localStorage ('psyche-theme', the
// key the kit's switch writes), so each load writes the scheme there before any script of the page
// runs (the run emulates the system scheme too, for any rule that reads it). After the load the page must show the
// theme the run asked for (<html data-theme>), or the run fails: a "light" run that shows the dark
// theme would audit the dark page twice and the light one never. A page whose head script carries
// data-k-theme fixes its theme (the home page's film is dark by design): it is audited once per width,
// in that theme, and listed as "fixed dark".
//
// What no rule of axe can decide is checked by hand and by pixels, not here: see "Accessibility
// check" in website/README.md.
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { appendFileSync, copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { delimiter, extname, join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

// The two packages and their versions are read from the manifest `npm ci` installs from, so a version
// bump there (Dependabot's included) needs no edit here. scripts/a11y-tools.test.mjs checks that it pins
// exact versions and that its lockfile holds the same ones.
const LOCKED = fileURLToPath(new URL('./a11y-tools/', import.meta.url));
const TOOLS = JSON.parse(readFileSync(join(LOCKED, 'package.json'), 'utf8')).dependencies ?? {};
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
// Anything that is not named lesser fails, so a violation that carries no impact cannot slip through.
const LESSER = new Set(['moderate', 'minor']);
const isFailing = (impact) => !LESSER.has(impact);
// A run in which axe tested fewer rules than this did not run axe: fail rather than pass. A page with
// little in it applies few rules: the shortest document on a phone (/faq/: headings and paragraphs, its
// page list folded behind "Pages" and "On this page" not shown) applies 19, and a run that fails to start
// axe applies none.
const MIN_RULES_RUN = 15;

const DIST = resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
// Must equal `base` in astro.config.mjs.
const BASE = '/';
// Every page of the site: each folder of dist/ with an index.html (the home page included), then the
// 404 page, which the host serves for a missing address (the file itself is opened here, so its script
// has run as it does for a reader). Found, not listed, so a page added later is audited without anyone
// remembering to add it. The bundles are not pages.
const NOT_PAGES = new Set(['_astro']);
function findPages() {
  const found = [];
  const walk = (dir, rel) => {
    if (existsSync(join(dir, 'index.html'))) found.push(rel);
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      if (entry.isDirectory() && !NOT_PAGES.has(entry.name)) walk(join(dir, entry.name), `${rel}${entry.name}/`);
    }
  };
  walk(DIST, '');
  found.sort((a, b) => (a === '' ? -1 : b === '' ? 1 : a.localeCompare(b)));
  if (existsSync(join(DIST, '404.html'))) found.push('404.html');
  return found;
}
// The theme a page fixes for itself, or null: the value of data-k-theme on a script of its built HTML
// (the page kit's head script then ignores the reader's choice; the home page's film is dark only).
// Only the pages named here may fix it: on any other page a fixed theme would quietly take its light
// (or dark) audit away, so it fails the run instead.
const MAY_FIX_THEME = new Set(['']);
function fixedTheme(slug) {
  const file = slug.endsWith('.html') ? join(DIST, slug) : join(DIST, slug, 'index.html');
  const m = readFileSync(file, 'utf8').match(/<script\b[^>]*\bdata-k-theme=["']?(light|dark)["'\s>]/i);
  const fixed = m ? m[1].toLowerCase() : null;
  if (fixed && !MAY_FIX_THEME.has(slug)) throw new Error(`${BASE}${slug} fixes its theme to ${fixed}; only ${[...MAY_FIX_THEME].map((p) => BASE + p).join(', ')} may`);
  return fixed;
}

const VIEWPORTS = [
  { name: 'desktop', width: 1280, height: 800, isMobile: false },
  { name: 'phone', width: 390, height: 844, isMobile: true },
];
const SCHEMES = ['light', 'dark'];

// What a reader opens on a page. Each has to be opened by a click, so axe cannot reach it by loading
// a page. A state is audited on one document that has the documentation's page list, "On this page"
// and headings; a state that names a `page` is audited there instead. A state may also say how it is
// closed (`close`), which is checked after its audit.
const STATE_PAGE = 'research/gates/';
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const stateUrl = (state) => state.page ?? STATE_PAGE;
// How many elements of a page were inert before its menu opened, so that the close can be held to it.
const inertBefore = new WeakMap();
const countInert = (page) => page.evaluate(() => document.querySelectorAll('[inert]').length);
// The theme switch's spoken name in each theme: it says what pressing it will do.
const THEME_NAMES = { dark: 'Switch to the light theme', light: 'Switch to the dark theme' };
const themeState = (page, selector) => page.$eval(selector, (b) => {
  let kept = null;
  try { kept = localStorage.getItem('psyche-theme'); } catch { /* storage refused */ }
  return { theme: document.documentElement.dataset.theme, name: b.getAttribute('aria-label'), kept, text: b.textContent.trim() };
});
function expectSwitched(before, after) {
  if (before.name !== THEME_NAMES[before.theme]) throw new Error(`the theme switch is named "${before.name}" in the ${before.theme} theme`);
  if (before.text) throw new Error(`the theme switch shows the text "${before.text}"; it is a drawn icon`);
  if (after.theme === before.theme) throw new Error(`the theme switch was pressed but the page stayed ${before.theme}`);
  if (after.name !== THEME_NAMES[after.theme]) throw new Error(`after a press the theme switch is named "${after.name}" in the ${after.theme} theme`);
  if (after.kept !== after.theme) throw new Error(`after a press the page is ${after.theme} but the kept choice is ${after.kept}`);
}
// The phone menu of a front page, as a state: audited open; then Escape must close it, hide it, mark
// its button collapsed, give the rest of the page back (no more inert elements than before it
// opened) and return focus to the button. `themeSwitch` says whether the menu holds the theme switch,
// `marked` which of its five links is marked as the current item (none on the film).
function siteMenu(name, page, themeSwitch, marked) {
  return {
    name,
    page,
    viewports: ['phone'],
    async open(p) {
      await p.waitForSelector('button[data-k-menu]', { visible: true, timeout: 20000 });
      inertBefore.set(p, await countInert(p));
      await p.click('button[data-k-menu]');
      await p.waitForSelector('#k-menu:not([hidden])', { timeout: 10000 });
      const seen = await p.evaluate(() => ({
        expanded: document.querySelector('button[data-k-menu]')?.getAttribute('aria-expanded'),
        links: document.querySelectorAll('#k-menu .k-menu__link').length,
        focused: !!document.activeElement?.matches('#k-menu .k-menu__link'),
        marked: [...document.querySelectorAll('#k-menu .k-menu__link[aria-current]')].map((a) => a.textContent),
        theme: document.documentElement.dataset.theme,
        switches: [...document.querySelectorAll('#k-menu [data-k-theme]')].map((b) => b.getAttribute('aria-label')),
      }));
      if (seen.expanded !== 'true') throw new Error(`the menu opened but its button says aria-expanded="${seen.expanded}"`);
      if (seen.links !== 5) throw new Error(`the menu holds ${seen.links} link(s), not the site's five`);
      if (seen.marked.join() !== (marked ? [marked] : []).join()) throw new Error(`the menu marks ${JSON.stringify(seen.marked)} as the current item, expected ${JSON.stringify(marked ?? null)}`);
      if (!seen.focused) throw new Error('the menu opened but focus is not on its first link');
      const want = themeSwitch ? [THEME_NAMES[seen.theme]] : [];
      if (seen.switches.join() !== want.join()) throw new Error(`the menu's theme switch: ${JSON.stringify(seen.switches)}, expected ${JSON.stringify(want)}`);
      await wait(400);
    },
    async close(p) {
      await p.keyboard.press('Escape');
      await p.waitForSelector('#k-menu[hidden]', { timeout: 10000 });
      const after = await p.evaluate(() => {
        const button = document.querySelector('button[data-k-menu]');
        return {
          expanded: button?.getAttribute('aria-expanded'),
          focused: document.activeElement === button,
          inert: document.querySelectorAll('[inert]').length,
        };
      });
      if (after.expanded !== 'false') throw new Error(`the menu closed but its button says aria-expanded="${after.expanded}"`);
      const before = inertBefore.get(p) ?? 0;
      if (after.inert !== before) throw new Error(`the menu closed but ${after.inert} element(s) are inert (${before} before it opened)`);
      if (!after.focused) throw new Error('the menu closed but focus did not return to its button');
    },
  };
}
// The theme switch of the page kit's header, as a state: a drawn icon whose spoken name says what it
// will do. Pressed, it must switch the theme, keep the choice ('psyche-theme') and change its name; the
// page is audited in the theme it switched to, then pressed again, and must switch back.
function themeSwitched(name, page) {
  const button = '.k-head button[data-k-theme]';
  return {
    name,
    page,
    viewports: ['desktop'],
    async open(p) {
      await p.waitForSelector(button, { visible: true, timeout: 20000 });
      const before = await themeState(p, button);
      await p.click(button);
      await wait(400);
      expectSwitched(before, await themeState(p, button));
    },
    async close(p) {
      const now = await themeState(p, button);
      await p.click(button);
      await wait(400);
      expectSwitched(now, await themeState(p, button));
    },
  };
}
const STATES = [
  {
    // The documentation's page list on a document, with words typed into its field that match no page:
    // the field is written hidden by the server and shown by the documentation script; every page and
    // group must be hidden and the line "No page matches these words." shown. Then Escape in the field
    // must clear the words, show every page again and hide that line.
    name: 'page filter with no match',
    viewports: ['desktop'],
    async open(page) {
      const field = '#k-docnav-q';
      await page.waitForSelector(field, { visible: true, timeout: 20000 });
      await page.click(field);
      await page.type(field, 'qqqzzz');
      await page.waitForSelector('.k-docnav__none:not([hidden])', { timeout: 10000 });
      const shown = await page.$$eval('#k-docnav li[data-k-text]:not([hidden])', (l) => l.length);
      if (shown !== 0) throw new Error(`words that match no page left ${shown} page(s) in the list`);
      await wait(200);
    },
    async close(page) {
      await page.keyboard.press('Escape');
      const after = await page.evaluate(() => ({
        value: document.querySelector('#k-docnav-q')?.value,
        hidden: document.querySelectorAll('#k-docnav li[data-k-text][hidden], #k-docnav .k-docnav__group[hidden]').length,
        none: document.querySelector('.k-docnav__none')?.hidden,
      }));
      if (after.value !== '') throw new Error(`Escape did not clear the field (it holds "${after.value}")`);
      if (after.hidden !== 0 || after.none !== true) throw new Error(`Escape cleared the words but ${after.hidden} page(s) or group(s) stay hidden`);
    },
  },
  // The front pages' phone menu: on an inner page the page kit's full-screen list, with the theme
  // switch in its top row beside "Close"; on the home page the film's own copy of it, without the
  // switch (the film is dark only).
  siteMenu('site menu open', 'what-were-building/', true, "What we're building"),
  siteMenu('site menu open on the film', '', false, null),
  // A document's phone menu is the same list as a front page's, beside the documentation's own "Pages".
  // A document marks For developers, the item the documentation is under.
  siteMenu('site menu open on a document', STATE_PAGE, true, 'For developers'),
  // The header's theme switch, on a front page and on a document (the documentation's frame is on the
  // same page kit, so its header is the same).
  themeSwitched('theme switched', 'about/'),
  themeSwitched('theme switched on a document', STATE_PAGE),
  {
    // The documentation's home (/developers/): its filter, which the server writes hidden and the
    // documentation script shows, with a word typed. Audited filtered: the count's words must change from
    // the total to "N pages of <total>" and some page must be left; then Escape in the field must clear
    // the words, show every page again and put the count back to the total.
    name: 'documentation filter',
    page: 'developers/',
    viewports: ['desktop'],
    async open(page) {
      const field = '#k-docfilter';
      await page.waitForSelector(field, { visible: true, timeout: 20000 });
      const count = () => page.$eval('#k-docfilter-count', (p) => p.textContent.trim());
      const total = await count();
      if (!/^\d+ pages$/.test(total)) throw new Error(`the filter's count reads "${total}" before anything is typed`);
      await page.click(field);
      await page.type(field, 'gate');
      await page.waitForFunction((t) => document.querySelector('#k-docfilter-count')?.textContent.trim() !== t, { timeout: 10000 }, total);
      const after = await page.evaluate(() => ({
        count: document.querySelector('#k-docfilter-count')?.textContent.trim(),
        shown: document.querySelectorAll('.k-docindex__item:not([hidden])').length,
      }));
      if (!/^\d+ pages? of \d+$/.test(after.count || '') || after.shown < 1) throw new Error(`the filter left ${after.shown} page(s) and reads "${after.count}"`);
      await wait(200);
    },
    async close(page) {
      await page.keyboard.press('Escape');
      const after = await page.evaluate(() => ({
        value: document.querySelector('#k-docfilter')?.value,
        count: document.querySelector('#k-docfilter-count')?.textContent.trim(),
        hidden: document.querySelectorAll('.k-docindex__item[hidden]').length,
      }));
      if (after.value !== '') throw new Error(`Escape did not clear the filter (it holds "${after.value}")`);
      if (after.hidden !== 0 || !/^\d+ pages$/.test(after.count || '')) throw new Error(`Escape cleared the words but ${after.hidden} page(s) stay hidden and the count reads "${after.count}"`);
    },
  },
  {
    // The documentation's "Pages" list on a phone, on a page of the list (the timeline): the server writes
    // the list whole; the documentation script folds it behind "Pages". Opened with the page read some way
    // down, it must lie over the text and take no room: the page keeps its scroll position and its text
    // does not move. Audited open; then Escape must close it, mark the button collapsed and return focus to
    // the button.
    name: 'documentation pages open',
    page: 'roadmap/',
    viewports: ['phone'],
    async open(page) {
      await page.waitForSelector('button[data-k-docmenu]', { visible: true, timeout: 20000 });
      const where = () => page.evaluate(() => ({ y: Math.round(window.scrollY), top: Math.round(document.querySelector('main').getBoundingClientRect().top) }));
      await page.evaluate(() => window.scrollTo(0, 900));
      await wait(200);
      const before = await where();
      await page.click('button[data-k-docmenu]');
      await page.waitForSelector('#k-docnav.is-open', { timeout: 10000 });
      const expanded = await page.$eval('button[data-k-docmenu]', (b) => b.getAttribute('aria-expanded'));
      if (expanded !== 'true') throw new Error(`the list opened but its button says aria-expanded="${expanded}"`);
      await wait(200);
      const after = await where();
      if (after.y !== before.y || after.top !== before.top) throw new Error(`opening the list moved the page: scrolled ${before.y} then ${after.y}, its text at ${before.top} then ${after.top}`);
    },
    async close(page) {
      await page.keyboard.press('Escape');
      const after = await page.evaluate(() => {
        const button = document.querySelector('button[data-k-docmenu]');
        return {
          open: document.querySelector('#k-docnav')?.classList.contains('is-open'),
          expanded: button?.getAttribute('aria-expanded'),
          focused: document.activeElement === button,
        };
      });
      if (after.open || after.expanded !== 'false') throw new Error(`Escape left the list open (aria-expanded="${after.expanded}")`);
      if (!after.focused) throw new Error('the list closed but focus did not return to its button');
    },
  },
  {
    // The timeline's drawing (/roadmap/), written hidden and shown by its script, with a gate chosen: its
    // row must be pressed, the phase chosen before must not be, and the gate's reading must be the one shown.
    name: 'timeline gate chosen',
    page: 'roadmap/',
    viewports: ['desktop', 'phone'],
    async open(page) {
      const lane = '.tl-lane[data-tl="B"]';
      await page.waitForSelector(lane, { visible: true, timeout: 20000 });
      await page.$eval(lane, (b) => b.scrollIntoView({ block: 'center' }));
      await page.click(lane);
      const after = await page.evaluate(() => ({
        pressed: [...document.querySelectorAll('.tl-lane[aria-pressed="true"]')].map((b) => b.getAttribute('data-tl')),
        shown: [...document.querySelectorAll('[data-tl-reading]:not([hidden])')].map((r) => r.getAttribute('data-tl-reading')),
      }));
      if (after.pressed.join() !== 'B' || after.shown.join() !== 'B') throw new Error(`choosing Gate B left ${after.pressed.join() || 'nothing'} pressed and ${after.shown.join() || 'nothing'} shown`);
      await wait(200);
    },
  },
  {
    // The walk-through (/battery/): the first test stepped to its last step with "Next step". The picture,
    // the step marked current and the words "Step 3 of 3" must follow; nothing steps by itself.
    name: 'walk-through stepped',
    page: 'battery/',
    viewports: ['desktop', 'phone'],
    async open(page) {
      const next = '[data-bw-test="T1"] [data-bw-next]';
      await page.waitForSelector(next, { visible: true, timeout: 20000 });
      await page.$eval(next, (b) => b.scrollIntoView({ block: 'center' }));
      await page.click(next);
      await page.click(next);
      await wait(200);
      const after = await page.$eval('[data-bw-test="T1"]', (t) => ({
        at: t.querySelector('[data-bw-at]')?.textContent.trim(),
        current: [...t.querySelectorAll('[data-bw-step]')].findIndex((b) => b.getAttribute('aria-current') === 'step'),
        shown: [...t.querySelectorAll('[data-bw-pic]')].findIndex((p) => !p.hidden),
        last: t.querySelector('[data-bw-next]')?.getAttribute('aria-disabled'),
      }));
      if (after.at !== 'Step 3 of 3' || after.current !== 2 || after.shown !== 2 || after.last !== 'true') {
        throw new Error(`after two steps the walk-through reads "${after.at}", step ${after.current + 1} current, picture ${after.shown + 1} shown`);
      }
    },
  },
  {
    // The status page's designed bricks, opened: the control's first word must now say what it will do.
    name: 'designed bricks shown',
    page: 'status/',
    viewports: ['desktop', 'phone'],
    async open(page) {
      const summary = 'details[data-st-more] > summary';
      await page.waitForSelector(summary, { visible: true, timeout: 20000 });
      await page.$eval(summary, (s) => s.scrollIntoView({ block: 'center' }));
      await page.click(summary);
      await wait(200);
      const words = await page.$eval(summary, (s) => s.textContent.trim());
      if (!/^Hide the \d+ designed bricks?$/.test(words)) throw new Error(`the open control reads "${words}"`);
    },
    async close(page) {
      await page.click('details[data-st-more] > summary');
      await wait(200);
      const words = await page.$eval('details[data-st-more] > summary', (s) => s.textContent.trim());
      if (!/^Show the \d+ designed bricks?$/.test(words)) throw new Error(`the closed control reads "${words}"`);
    },
  },
  {
    // A post's own figure (src/kit/posts/<slug>/), after the reader has used its first control ("Play
    // again", or "Play"): the figure is mounted live, with its controls and its description, and the
    // control keeps focus. Audited on the post with the most figures.
    name: 'post figure played',
    page: 'blog/three-questions-before-a-number-counts/',
    viewports: ['desktop', 'phone'],
    async open(page) {
      const button = '[data-figure="ladder"] .k-fig-ctl button';
      await page.waitForSelector(button, { timeout: 20000 });
      await page.$eval('[data-figure="ladder"]', (f) => f.scrollIntoView({ block: 'center' }));
      await wait(400);
      await page.click(button);
      await wait(800);
      const live = await page.$eval('[data-figure="ladder"]', (f) => !!f.querySelector('.k-layer-front'));
      if (!live) throw new Error('the figure did not mount live after its control was used');
    },
  },
];

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.xml': 'application/xml; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.wasm': 'application/wasm',
};

function arg(name) {
  const i = process.argv.indexOf(name);
  return i > -1 ? process.argv[i + 1] : undefined;
}

// The setup could not be done: not a finding about the site (exit code 2).
class SetupError extends Error {}

const sleepSync = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);

function ensureTools() {
  // The two packages, each at an exact version: a range would install whatever the lockfile says and
  // never match the version checked below.
  if (Object.keys(TOOLS).sort().join() !== 'axe-core,puppeteer-core' || !Object.values(TOOLS).every((v) => /^\d+\.\d+\.\d+$/.test(v))) {
    const named = Object.entries(TOOLS).map(([n, v]) => `${n}@${v}`).join(', ') || 'nothing';
    throw new SetupError(`scripts/a11y-tools/package.json must name axe-core and puppeteer-core, each at an exact version (it names ${named})`);
  }
  const dir = process.env.A11Y_TOOLS_DIR || fileURLToPath(new URL('../node_modules/.cache/psyche-a11y-tools/', import.meta.url));
  // Code is loaded from this directory, so it must be ours alone: created private, and refused if it
  // already exists owned by someone else or writable by group or others.
  mkdirSync(dir, { recursive: true, mode: 0o700 });
  if (typeof process.getuid === 'function') {
    const st = statSync(dir);
    if (st.uid !== process.getuid() || (st.mode & 0o022) !== 0) {
      throw new SetupError(`${dir} must be owned by you and not group- or world-writable`);
    }
  }
  const installed = (name, version) => {
    try {
      return JSON.parse(readFileSync(join(dir, 'node_modules', name, 'package.json'), 'utf8')).version === version;
    } catch {
      return false;
    }
  };
  if (!Object.entries(TOOLS).every(([n, v]) => installed(n, v))) {
    // The two packages and everything they depend on, as the repository locks them.
    for (const file of ['package.json', 'package-lock.json']) copyFileSync(join(LOCKED, file), join(dir, file));
    console.log(`check-a11y: installing ${Object.entries(TOOLS).map(([n, v]) => `${n}@${v}`).join(', ')} into ${dir}`);
    for (let attempt = 1; ; attempt++) {
      try {
        execFileSync('npm', ['ci', '--prefix', dir, '--no-audit', '--no-fund', '--ignore-scripts', '--loglevel=error'], { stdio: 'inherit' });
        break;
      } catch (e) {
        if (attempt === 3) throw new SetupError(`the packages would not install after ${attempt} tries: ${e.message || e}`);
        console.error(`check-a11y: install failed (try ${attempt} of 3); trying again`);
        sleepSync(attempt * 4000);
      }
    }
    if (!Object.entries(TOOLS).every(([n, v]) => installed(n, v))) {
      throw new SetupError('the installed packages are not the versions scripts/a11y-tools/package.json names: its package-lock.json must say the same');
    }
  }
  const req = createRequire(join(dir, 'noop.js'));
  return { puppeteer: req('puppeteer-core'), axeSource: readFileSync(req.resolve('axe-core/axe.min.js'), 'utf8') };
}

function findChrome() {
  const given = arg('--chrome') || process.env.CHROME_PATH;
  if (given) {
    if (!existsSync(given)) throw new SetupError(`the Chrome given (${given}) does not exist`);
    return given;
  }
  const fixed = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
  ];
  for (const p of fixed) if (existsSync(p)) return p;
  for (const name of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
    for (const dir of (process.env.PATH || '').split(delimiter)) {
      const p = join(dir, name);
      if (dir && existsSync(p)) return p;
    }
  }
  throw new SetupError('no Chrome or Chromium found; pass --chrome PATH or set CHROME_PATH');
}

// dist/ under the site's base path, on a free port of the loopback interface.
function serve() {
  const server = createServer((req, res) => {
    const send = (code, body, type = 'text/plain; charset=utf-8') => {
      res.writeHead(code, { 'content-type': type });
      res.end(body);
    };
    let path;
    try {
      path = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    } catch {
      return send(400, 'bad request');
    }
    if (!path.startsWith(BASE)) return send(404, 'not found');
    let file = resolve(DIST, path.slice(BASE.length));
    if (file !== DIST && !file.startsWith(DIST + sep)) return send(403, 'forbidden');
    if (existsSync(file) && statSync(file).isDirectory()) file = join(file, 'index.html');
    if (!existsSync(file)) {
      const missing = join(DIST, '404.html');
      return send(404, existsSync(missing) ? readFileSync(missing) : 'not found', MIME['.html']);
    }
    send(200, readFileSync(file), MIME[extname(file)] || 'application/octet-stream');
  });
  return new Promise((ok, fail) => {
    server.once('error', fail);
    server.listen(Number(arg('--port')) || 0, '127.0.0.1', () => ok(server));
  });
}

async function audit(browser, axeSource, url, viewport, scheme, state, fixed) {
  const page = await browser.newPage();
  try {
    await page.setViewport({
      width: viewport.width,
      height: viewport.height,
      isMobile: viewport.isMobile,
      hasTouch: viewport.isMobile,
      deviceScaleFactor: 1,
    });
    // The reader's choice as the page kit's theme switch stores it, written before any script of the
    // page runs.
    await page.evaluateOnNewDocument((s) => {
      try {
        localStorage.setItem('psyche-theme', s);
      } catch {
        // storage refused: the theme check below then fails the light run, which is what should happen
      }
    }, scheme);
    await page.emulateMediaFeatures([
      { name: 'prefers-color-scheme', value: scheme },
      { name: 'prefers-reduced-motion', value: 'reduce' },
    ]);
    const response = await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
    // A missing page is served as the 404 page, which would be audited in its place and pass.
    if (!response || !response.ok()) throw new Error(`${url} answered ${response ? response.status() : 'nothing'}`);
    // The page shows the theme this run audits, or the run is not what its label says.
    const shown = await page.evaluate(() => ({
      theme: document.documentElement.dataset.theme,
      pin: document.querySelector('script[data-k-theme]')?.getAttribute('data-k-theme') ?? null,
    }));
    if ((shown.pin || null) !== fixed) throw new Error(`${url}: the page fixes its theme to ${shown.pin || 'nothing'}, the built file to ${fixed || 'nothing'}`);
    if (shown.theme !== scheme) throw new Error(`${url} shows the ${shown.theme || 'no'} theme in a ${scheme} run`);
    await page.evaluate(async () => {
      await document.fonts.ready;
      const step = Math.max(200, Math.floor(innerHeight / 2));
      for (let y = 0; y < document.documentElement.scrollHeight; y += step) {
        scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 40));
      }
      scrollTo(0, 0);
    });
    await new Promise((r) => setTimeout(r, 400));
    if (state) await state.open(page);
    await page.evaluate(axeSource);
    const result = await page.evaluate(
      (tags) => axe.run(document, { runOnly: { type: 'tag', values: tags }, resultTypes: ['violations', 'incomplete', 'passes'] })
        .then((r) => ({
          rulesRun: r.violations.length + r.passes.length + r.incomplete.length,
          violations: r.violations.map((v) => ({
            id: v.id, impact: v.impact, help: v.help, helpUrl: v.helpUrl,
            nodes: v.nodes.map((n) => ({ target: n.target.join(' '), html: n.html.slice(0, 160) })),
          })),
          incomplete: r.incomplete.map((v) => ({ id: v.id, targets: v.nodes.map((n) => n.target.join(' ')) })),
        })),
      TAGS,
    );
    if (result.rulesRun < MIN_RULES_RUN) throw new Error(`${url}: axe tested only ${result.rulesRun} rule(s)`);
    if (state?.close) await state.close(page);
    return result;
  } finally {
    await page.close();
  }
}

// One load, tried twice: a page that will not load or a state that will not open is an error and fails
// the run, but a slow runner gets a second go before it does. Violations are never retried.
async function auditWithRetry(...args) {
  try {
    return await audit(...args);
  } catch (first) {
    console.error(`check-a11y: ${first.message || first}; trying once more`);
    return await audit(...args);
  }
}

async function main() {
  if (!existsSync(join(DIST, 'index.html'))) throw new Error('dist/ is not built; run `npm run build` first');
  const { puppeteer, axeSource } = ensureTools();
  const executablePath = findChrome();
  const server = await serve();
  const origin = `http://127.0.0.1:${server.address().port}`;

  // One entry per rule and element, with every page and configuration that hit it.
  const found = new Map();
  let runs = 0;
  const undecided = new Map();
  const undecidedNodes = new Set();
  let version = '';
  let browser;
  try {
    const args = process.env.CI ? ['--no-sandbox', '--disable-dev-shm-usage'] : [];
    // A Chrome that is there but will not start says nothing about the site either.
    try {
      browser = await puppeteer.launch({ executablePath, headless: true, args });
    } catch (e) {
      throw new SetupError(`Chrome would not start: ${e.message || e}`);
    }
    version = await browser.version();
    console.log(`check-a11y: ${version}, axe-core ${TOOLS['axe-core']}, tags ${TAGS.join(' ')}`);
    const everyPage = findPages();
    for (const st of STATES) {
      if (!everyPage.includes(stateUrl(st))) throw new Error(`dist/${stateUrl(st)} is missing, so the state "${st.name}" cannot be audited`);
    }
    // '/' names the home page.
    const only = arg('--only')?.split(',').map((p) => p.trim()).filter(Boolean).map((p) => (p === '/' ? '' : p));
    const unknown = (only || []).filter((p) => !everyPage.includes(p));
    if (unknown.length) throw new Error(`--only names no page of dist/: ${unknown.join(', ')}`);
    const pages = only ? everyPage.filter((p) => only.includes(p)) : everyPage;
    const states = STATES.filter((st) => pages.includes(stateUrl(st)));
    // Every page, then each state on its page; each in both widths and both colour schemes, except that
    // a page that fixes its theme is audited in that theme only.
    const jobs = [];
    for (const slug of pages) jobs.push({ slug, label: BASE + slug });
    for (const state of states) jobs.push({ slug: stateUrl(state), label: `${BASE}${stateUrl(state)} (${state.name})`, state });
    const fixedOf = new Map(jobs.map(({ slug }) => [slug, fixedTheme(slug)]));
    const fixedPages = pages.filter((slug) => fixedOf.get(slug));
    console.log(`check-a11y: ${pages.length} page(s) and ${states.length} interface state(s)${only ? ' (--only: not the whole site)' : ''}`);
    for (const slug of fixedPages) console.log(`check-a11y: ${BASE}${slug} fixes its theme (fixed ${fixedOf.get(slug)}): audited once per width, in that theme`);
    for (const { slug, label: route, state } of jobs) {
      const fixed = fixedOf.get(slug);
      for (const viewport of VIEWPORTS) {
        if (state && !state.viewports.includes(viewport.name)) continue;
        for (const scheme of fixed ? [fixed] : SCHEMES) {
          const t0 = Date.now();
          const result = await auditWithRetry(browser, axeSource, origin + BASE + slug, viewport, scheme, state, fixed);
          runs++;
          for (const { id, targets } of result.incomplete) {
            undecided.set(id, (undecided.get(id) || 0) + 1);
            for (const t of targets) undecidedNodes.add(`${id} ${route} ${t}`);
          }
          const label = `${viewport.name}, ${fixed ? `fixed ${fixed}` : scheme}`;
          console.log(`check-a11y: ${route} [${label}]: ${result.violations.length} violating rule(s), ${result.rulesRun} rules run (${((Date.now() - t0) / 1000).toFixed(1)} s)`);
          for (const v of result.violations) {
            for (const n of v.nodes) {
              const key = `${v.id}\u0000${route}\u0000${n.target}`;
              if (!found.has(key)) {
                found.set(key, { id: v.id, impact: v.impact, help: v.help, helpUrl: v.helpUrl, route, target: n.target, html: n.html, configs: [] });
              }
              found.get(key).configs.push(label);
            }
          }
        }
      }
    }
  } finally {
    // The server is closed whatever the browser does: a close that throws or never answers must
    // not leave the loopback server holding the process open. The browser close is raced against
    // a timer, and the process is killed outright if it will not go.
    if (browser) {
      try {
        await Promise.race([browser.close(), new Promise((r) => setTimeout(r, 15000))]);
      } catch (e) {
        console.error(`check-a11y: the browser did not close cleanly: ${e.message || e}`);
      }
      try {
        browser.process()?.kill('SIGKILL');
      } catch {
        // already gone
      }
    }
    server.closeAllConnections?.();
    await Promise.race([new Promise((r) => server.close(r)), new Promise((r) => setTimeout(r, 5000))]);
  }

  const all = [...found.values()];
  const failing = all.filter((f) => isFailing(f.impact));
  const other = all.filter((f) => !isFailing(f.impact));
  const order = { critical: 0, serious: 1, moderate: 2, minor: 3 };
  const rank = (impact) => order[impact] ?? -1;
  const sorted = (list) => [...list].sort((a, b) => rank(a.impact) - rank(b.impact) || a.id.localeCompare(b.id) || a.route.localeCompare(b.route));

  const undecidedText = [...undecided].map(([id, n]) => `${id} x${n}`).join(', ') || 'none';
  console.log(`\ncheck-a11y: ${runs} page load(s); ${failing.length} serious or critical element(s), ${other.length} lesser`);
  console.log(`check-a11y: rules axe could not decide on (need a human look, never fail the run): ${undecidedText}`);
  for (const f of sorted(all)) {
    const row = `${String(f.impact || 'unknown').toUpperCase().padEnd(8)} ${f.id} on ${f.route} [${[...new Set(f.configs)].join('; ')}]\n         ${f.help}\n         ${f.target}\n         ${f.html.replace(/\s+/g, ' ')}\n         ${f.helpUrl}`;
    console.log(row);
  }
  for (const f of sorted(failing).slice(0, 20)) {
    if (process.env.GITHUB_ACTIONS) console.log(`::error title=axe ${f.id} (${f.impact})::${f.route}: ${f.help}. ${f.target}`.replace(/\n/g, ' '));
  }

  const json = arg('--json');
  if (json) writeFileSync(json, JSON.stringify({ browser: version, axe: TOOLS['axe-core'], tags: TAGS, runs, undecided: Object.fromEntries(undecided), undecidedElements: [...undecidedNodes].sort(), violations: sorted(all) }, null, 2));
  if (process.env.GITHUB_STEP_SUMMARY) {
    const md = [`### Accessibility (axe-core ${TOOLS['axe-core']}, WCAG 2.2 AA)`, '',
      `${runs} page loads; ${failing.length} serious or critical element(s); ${other.length} lesser. Undecided by axe, for a human look: ${undecidedText}.`, ''];
    if (all.length) {
      md.push('| Impact | Rule | Page | Element |', '|---|---|---|---|');
      for (const f of sorted(all).slice(0, 60)) md.push(`| ${f.impact} | [${f.id}](${f.helpUrl}) | \`${f.route}\` | \`${f.target.replace(/\\/g, '\\\\').replace(/\|/g, '\\|')}\` |`);
    }
    appendFileSync(process.env.GITHUB_STEP_SUMMARY, md.join('\n') + '\n');
  }

  if (failing.length) {
    console.error(`check-a11y: ${failing.length} serious or critical violation(s)`);
    process.exitCode = 1;
  } else {
    console.log('check-a11y: no serious or critical violation');
  }
}

main()
  .catch((e) => {
    if (e instanceof SetupError) {
      console.error(`check-a11y: could not set up (this is not a finding about the site; run it again): ${e.message}`);
      if (process.env.GITHUB_ACTIONS) console.log(`::error title=check-a11y could not set up::${e.message}`);
      process.exitCode = 2;
    } else {
      console.error(`check-a11y: ${e.stack || e}`);
      process.exitCode = 1;
    }
  })
  .finally(() => {
    // Everything has been closed by now and the process ends by itself. If a stray handle holds
    // it open, end it after a short wait with the exit code already set. The timer is unref'd, so
    // it never keeps a finished process alive.
    setTimeout(() => process.exit(process.exitCode ?? 0), 10000).unref();
  });
