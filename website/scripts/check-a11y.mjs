// Accessibility check of the built site: axe-core over every page of dist/, at WCAG 2.2 AA (the axe
// tags wcag2a, wcag2aa, wcag21a, wcag21aa and wcag22aa), and over the interface states a reader opens
// (the search dialog with results, the phone menu, the phone contents list). Exits 1 when any serious
// or critical violation is found, or when a page cannot be audited at all; moderate and minor ones are
// listed but never fail the run, and neither does what axe cannot decide (its "incomplete" results:
// today only text contrast over gradients, pseudo-elements and images, which need a human look).
// The Pages workflow runs it as a blocking step.
//
// Run it after `npm run build`:  node scripts/check-a11y.mjs [--chrome PATH] [--json FILE] [--only SLUGS] [--port N]
// --only takes a comma-separated list of pages (/,research/gates/,404.html) for a quick look while
// working on some; the interface states run only when research/gates/ is among them. CI runs it whole.
//
// This is a development tool and nothing the site ships. Its two packages are not in package.json:
// the script installs them, at the exact versions below and with their own dependencies as
// scripts/a11y-tools/package-lock.json locks them (`npm ci`), into website/node_modules/.cache/
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
// through once first, so that islands which hydrate when they come into view have done so. A state
// is the same page after the click that opens it.
//
// What no rule of axe can decide is checked by hand and by pixels, not here: see "Accessibility
// check" in website/README.md.
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { appendFileSync, copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { delimiter, extname, join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const TOOLS = { 'puppeteer-core': '25.12.0', 'axe-core': '4.14.0' };
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
// Anything that is not named lesser fails, so a violation that carries no impact cannot slip through.
const LESSER = new Set(['moderate', 'minor']);
const isFailing = (impact) => !LESSER.has(impact);
// A run in which axe tested fewer rules than this did not run axe: fail rather than pass.
const MIN_RULES_RUN = 20;

const DIST = resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
// Must equal `base` in astro.config.mjs.
const BASE = '/psyche/';
// Every page of the site: each folder of dist/ with an index.html (the home page included), then the
// 404 page, which the host serves for a missing address (the file itself is opened here, so its script
// has run as it does for a reader). Found, not listed, so a page added later is audited without anyone
// remembering to add it. The search index and the bundles are not pages.
const NOT_PAGES = new Set(['_astro', 'pagefind']);
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
const VIEWPORTS = [
  { name: 'desktop', width: 1280, height: 800, isMobile: false },
  { name: 'phone', width: 390, height: 844, isMobile: true },
];
const SCHEMES = ['light', 'dark'];

// What a reader opens on a page, audited on one docs page that has a sidebar, a contents list and
// headings. Each has to be opened by a click, so axe cannot reach it by loading a page.
const STATE_PAGE = 'research/gates/';
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const STATES = [
  {
    name: 'search dialog with results',
    viewports: ['desktop', 'phone'],
    async open(page) {
      // The button is disabled until Starlight's script has run, and the search box exists once the
      // search interface has loaded on idle.
      await page.waitForSelector('button[data-open-modal]:not([disabled])', { timeout: 20000 });
      await page.waitForSelector('#starlight__search input', { timeout: 20000 });
      await page.click('button[data-open-modal]');
      await page.type('#starlight__search input', 'gate');
      await page.waitForSelector('#starlight__search .pagefind-ui__result', { timeout: 20000 });
      await wait(600);
    },
  },
  {
    name: 'phone menu open',
    viewports: ['phone'],
    async open(page) {
      await page.click('button.sl-menu-button');
      await page.waitForSelector('#starlight__sidebar:popover-open', { timeout: 10000 });
      await wait(400);
    },
  },
  {
    name: 'phone contents open',
    viewports: ['phone'],
    async open(page) {
      await page.click('mobile-starlight-toc summary');
      await page.waitForSelector('mobile-starlight-toc details[open]', { timeout: 10000 });
      await wait(400);
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
    const locked = fileURLToPath(new URL('./a11y-tools/', import.meta.url));
    for (const file of ['package.json', 'package-lock.json']) copyFileSync(join(locked, file), join(dir, file));
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
      throw new SetupError('the installed packages are not the versions pinned in TOOLS: scripts/a11y-tools/package.json must say the same');
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

async function audit(browser, axeSource, url, viewport, scheme, state) {
  const page = await browser.newPage();
  try {
    await page.setViewport({
      width: viewport.width,
      height: viewport.height,
      isMobile: viewport.isMobile,
      hasTouch: viewport.isMobile,
      deviceScaleFactor: 1,
    });
    await page.emulateMediaFeatures([
      { name: 'prefers-color-scheme', value: scheme },
      { name: 'prefers-reduced-motion', value: 'reduce' },
    ]);
    const response = await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
    // A missing page is served as the 404 page, which would be audited in its place and pass.
    if (!response || !response.ok()) throw new Error(`${url} answered ${response ? response.status() : 'nothing'}`);
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
    if (!everyPage.includes(STATE_PAGE)) throw new Error(`dist/${STATE_PAGE} is missing, so the interface states cannot be audited`);
    // '/' names the home page.
    const only = arg('--only')?.split(',').map((p) => p.trim()).filter(Boolean).map((p) => (p === '/' ? '' : p));
    const unknown = (only || []).filter((p) => !everyPage.includes(p));
    if (unknown.length) throw new Error(`--only names no page of dist/: ${unknown.join(', ')}`);
    const pages = only ? everyPage.filter((p) => only.includes(p)) : everyPage;
    const states = pages.includes(STATE_PAGE) ? STATES : [];
    // Every page, then each state on its page; each in both widths and both colour schemes.
    const jobs = [];
    for (const slug of pages) jobs.push({ slug, label: BASE + slug });
    for (const state of states) jobs.push({ slug: STATE_PAGE, label: `${BASE}${STATE_PAGE} (${state.name})`, state });
    console.log(`check-a11y: ${pages.length} page(s) and ${states.length} interface state(s)${only ? ' (--only: not the whole site)' : ''}`);
    for (const { slug, label: route, state } of jobs) {
      for (const viewport of VIEWPORTS) {
        if (state && !state.viewports.includes(viewport.name)) continue;
        for (const scheme of SCHEMES) {
          const t0 = Date.now();
          const result = await auditWithRetry(browser, axeSource, origin + BASE + slug, viewport, scheme, state);
          runs++;
          for (const { id, targets } of result.incomplete) {
            undecided.set(id, (undecided.get(id) || 0) + 1);
            for (const t of targets) undecidedNodes.add(`${id} ${route} ${t}`);
          }
          const label = `${viewport.name}, ${scheme}`;
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
