// Accessibility check of the built site: axe-core over the key pages of dist/, at WCAG 2.2 AA
// (the axe tags wcag2a, wcag2aa, wcag21a, wcag21aa and wcag22aa). Exits 1 when any serious or
// critical violation is found; moderate and minor ones are listed but never fail the run.
//
// Run it after `npm run build`:  node scripts/check-a11y.mjs [--chrome PATH] [--json FILE]
//
// This is a development tool and nothing the site ships. Its two packages are not in package.json:
// the script installs them, at the exact versions below, into a temporary directory the first time
// it runs (A11Y_TOOLS_DIR changes where). It needs Google Chrome or Chromium; --chrome or
// CHROME_PATH names it, otherwise the usual locations are tried. GitHub's Ubuntu runners have it.
//
// The script serves dist/ itself on a free local port under the site's base path and closes the
// server and the browser before it exits, so nothing is left running.
//
// Each page is loaded four ways: desktop and phone width, light and dark colour scheme, all with
// reduced motion so that nothing is mid-fade when axe measures contrast. The page is scrolled
// through once first, so that islands which hydrate when they come into view have done so.
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync, appendFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { delimiter, extname, join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const TOOLS = { 'puppeteer-core': '25.12.0', 'axe-core': '4.14.0' };
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
const FAILING = new Set(['serious', 'critical']);

const DIST = resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
// Must equal `base` in astro.config.mjs.
const BASE = '/psyche/';
const PAGES = ['', 'battery/', 'roadmap/', 'status/', 'research/'];
const VIEWPORTS = [
  { name: 'desktop', width: 1280, height: 800, isMobile: false },
  { name: 'phone', width: 390, height: 844, isMobile: true },
];
const SCHEMES = ['light', 'dark'];

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

function ensureTools() {
  const dir = process.env.A11Y_TOOLS_DIR || join(tmpdir(), 'psyche-a11y-tools');
  const installed = (name, version) => {
    try {
      return JSON.parse(readFileSync(join(dir, 'node_modules', name, 'package.json'), 'utf8')).version === version;
    } catch {
      return false;
    }
  };
  if (!Object.entries(TOOLS).every(([n, v]) => installed(n, v))) {
    mkdirSync(dir, { recursive: true });
    console.log(`check-a11y: installing ${Object.entries(TOOLS).map(([n, v]) => `${n}@${v}`).join(', ')} into ${dir}`);
    execFileSync(
      'npm',
      ['install', '--prefix', dir, '--no-save', '--no-audit', '--no-fund', '--ignore-scripts', '--loglevel=error',
        ...Object.entries(TOOLS).map(([n, v]) => `${n}@${v}`)],
      { stdio: 'inherit' },
    );
  }
  const req = createRequire(join(dir, 'noop.js'));
  return { puppeteer: req('puppeteer-core'), axeSource: readFileSync(req.resolve('axe-core/axe.min.js'), 'utf8') };
}

function findChrome() {
  const given = arg('--chrome') || process.env.CHROME_PATH;
  if (given) {
    if (!existsSync(given)) throw new Error(`the Chrome given (${given}) does not exist`);
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
  throw new Error('no Chrome or Chromium found; pass --chrome PATH or set CHROME_PATH');
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
    server.listen(0, '127.0.0.1', () => ok(server));
  });
}

async function audit(browser, axeSource, url, viewport, scheme) {
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
    await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
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
    await page.evaluate(axeSource);
    return await page.evaluate(
      (tags) => axe.run(document, { runOnly: { type: 'tag', values: tags }, resultTypes: ['violations', 'incomplete'] })
        .then((r) => ({
          violations: r.violations.map((v) => ({
            id: v.id, impact: v.impact, help: v.help, helpUrl: v.helpUrl,
            nodes: v.nodes.map((n) => ({ target: n.target.join(' '), html: n.html.slice(0, 160) })),
          })),
          incomplete: r.incomplete.map((v) => ({ id: v.id, targets: v.nodes.map((n) => n.target.join(' ')) })),
        })),
      TAGS,
    );
  } finally {
    await page.close();
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
    browser = await puppeteer.launch({ executablePath, headless: true, args });
    version = await browser.version();
    console.log(`check-a11y: ${version}, axe-core ${TOOLS['axe-core']}, tags ${TAGS.join(' ')}`);
    for (const slug of PAGES) {
      const route = BASE + slug;
      for (const viewport of VIEWPORTS) {
        for (const scheme of SCHEMES) {
          const t0 = Date.now();
          const result = await audit(browser, axeSource, origin + route, viewport, scheme);
          runs++;
          for (const { id, targets } of result.incomplete) {
            undecided.set(id, (undecided.get(id) || 0) + 1);
            for (const t of targets) undecidedNodes.add(`${id} ${route} ${t}`);
          }
          const label = `${viewport.name}, ${scheme}`;
          console.log(`check-a11y: ${route} [${label}]: ${result.violations.length} violating rule(s) (${((Date.now() - t0) / 1000).toFixed(1)} s)`);
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
  const failing = all.filter((f) => FAILING.has(f.impact));
  const other = all.filter((f) => !FAILING.has(f.impact));
  const order = { critical: 0, serious: 1, moderate: 2, minor: 3 };
  const sorted = (list) => [...list].sort((a, b) => order[a.impact] - order[b.impact] || a.id.localeCompare(b.id) || a.route.localeCompare(b.route));

  const undecidedText = [...undecided].map(([id, n]) => `${id} x${n}`).join(', ') || 'none';
  console.log(`\ncheck-a11y: ${runs} page load(s); ${failing.length} serious or critical element(s), ${other.length} lesser`);
  console.log(`check-a11y: rules axe could not decide on (need a human look, never fail the run): ${undecidedText}`);
  for (const f of sorted(all)) {
    const row = `${f.impact.toUpperCase().padEnd(8)} ${f.id} on ${f.route} [${[...new Set(f.configs)].join('; ')}]\n         ${f.help}\n         ${f.target}\n         ${f.html.replace(/\s+/g, ' ')}\n         ${f.helpUrl}`;
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
    console.error(`check-a11y: ${e.stack || e}`);
    process.exitCode = 1;
  })
  .finally(() => {
    // Everything has been closed by now and the process ends by itself. If a stray handle holds
    // it open, end it after a short wait with the exit code already set. The timer is unref'd, so
    // it never keeps a finished process alive.
    setTimeout(() => process.exit(process.exitCode ?? 0), 10000).unref();
  });
