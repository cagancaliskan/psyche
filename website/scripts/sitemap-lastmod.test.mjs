import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { SITE_PAGES, historyAvailable, lastCommit, makeLastmod, makeSerialize, routeOfUrl, sourcesByRoute } from './sitemap-lastmod.mjs';

const MANIFEST = {
  sections: [{ title: 'S', pages: [{ src: 'docs/research/gates.md', slug: 'research/gates' }, { src: 'docs/PSYCHE.md', slug: 'substrate/overview' }] }],
};
const ENV = { ...process.env, GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_SYSTEM: '/dev/null' };
const git = (cwd, args, date) =>
  execFileSync('git', ['-C', cwd, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', ...args], {
    env: date ? { ...ENV, GIT_COMMITTER_DATE: date, GIT_AUTHOR_DATE: date } : ENV,
    stdio: ['ignore', 'pipe', 'ignore'],
    encoding: 'utf8',
  });

/** A repository where each file was last changed on a known day. */
function fixture() {
  const dir = mkdtempSync(join(tmpdir(), 'psyche-lastmod-'));
  const write = (rel, text) => {
    mkdirSync(dirname(join(dir, rel)), { recursive: true });
    writeFileSync(join(dir, rel), text);
  };
  git(dir, ['init', '-q']);
  write('docs/publish.json', JSON.stringify(MANIFEST));
  write('docs/research/gates.md', '# Gates\n');
  write('docs/PSYCHE.md', '# Substrate\n');
  write('website/src/pages/index.astro', 'a');
  write('website/src/pages/roadmap.astro', 'a');
  write('website/src/pages/battery.astro', 'a');
  write('website/src/pages/status.astro', 'a');
  write('website/src/components/BatteryExplorer.tsx', 'a');
  write('website/src/components/landing/Hero.astro', 'a');
  write('tools/research_plan.json', '{}');
  write('tools/ledger.json', '{}');
  git(dir, ['add', '-A']);
  git(dir, ['commit', '-q', '-m', 'one'], '2026-01-10T12:00:00Z');
  write('docs/research/gates.md', '# Gates\n\nmore\n');
  git(dir, ['commit', '-q', '-a', '-m', 'two'], '2026-03-05T08:30:00Z');
  write('tools/research_plan.json', '{"moved":1}');
  git(dir, ['commit', '-q', '-a', '-m', 'three'], '2026-05-20T17:45:00Z');
  write('website/src/components/BatteryExplorer.tsx', 'b');
  git(dir, ['commit', '-q', '-a', '-m', 'four'], '2026-07-01T09:00:00Z');
  return dir;
}

const BASE = '/psyche';
const url = (route) => `https://example.invalid${BASE}/${route}${route ? '/' : ''}`;

test('routeOfUrl reads the route below the base', () => {
  assert.equal(routeOfUrl(url(''), BASE), '');
  assert.equal(routeOfUrl(url('research/gates'), BASE), 'research/gates');
  assert.equal(routeOfUrl('https://example.invalid/other/', BASE), null);
});

test('sourcesByRoute lists the site pages and every docs page of the manifest', () => {
  const dir = fixture();
  try {
    const s = sourcesByRoute(dir);
    assert.deepEqual(s['research/gates'], ['docs/research/gates.md']);
    assert.deepEqual(s['substrate/overview'], ['docs/PSYCHE.md']);
    assert.ok(s[''].includes('website/src/pages/index.astro') && s[''].includes('tools/ledger.json'));
    assert.ok(s.battery.includes('website/src/pages/battery.astro') && s.battery.includes('website/src/components/BatteryExplorer.tsx'));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('each page gets the date of the last commit that touched its own files', () => {
  const dir = fixture();
  try {
    assert.equal(historyAvailable(dir), true);
    const serialize = makeSerialize({ repoRoot: dir, base: BASE });
    assert.equal(serialize({ url: url('research/gates') }).lastmod, '2026-03-05T08:30:00.000Z');
    assert.equal(serialize({ url: url('substrate/overview') }).lastmod, '2026-01-10T12:00:00.000Z');
    // the roadmap and the landing page move with the plan; the status page and the battery do not
    assert.equal(serialize({ url: url('roadmap') }).lastmod, '2026-05-20T17:45:00.000Z');
    assert.equal(serialize({ url: url('') }).lastmod, '2026-05-20T17:45:00.000Z');
    assert.equal(serialize({ url: url('status') }).lastmod, '2026-01-10T12:00:00.000Z');
    // a component a page is made from moves its date: the explorer is the battery's text, not its page file
    assert.equal(serialize({ url: url('battery') }).lastmod, '2026-07-01T09:00:00.000Z');
    // ... and a file in a listed directory counts, while the explorer is no part of the landing page
    assert.equal(serialize({ url: url('') }).lastmod, '2026-05-20T17:45:00.000Z');
    // other fields of the entry are kept
    assert.deepEqual(Object.keys(serialize({ url: url('battery'), changefreq: 'weekly' })).sort(), ['changefreq', 'lastmod', 'url']);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('makeLastmod gives a route the date its sitemap entry carries, and nothing for a route with no sources', () => {
  const dir = fixture();
  try {
    const lastmodOf = makeLastmod({ repoRoot: dir });
    const serialize = makeSerialize({ repoRoot: dir, base: BASE });
    for (const route of ['', 'roadmap', 'battery', 'status', 'research/gates', 'substrate/overview']) {
      assert.equal(lastmodOf(route), serialize({ url: url(route) }).lastmod, `route "${route}"`);
    }
    assert.equal(lastmodOf('research/gates'), '2026-03-05T08:30:00.000Z');
    // the 404 page, an unknown route and a name from Object.prototype are made from nothing: no date
    assert.equal(lastmodOf('404'), undefined);
    assert.equal(lastmodOf('nowhere'), undefined);
    assert.equal(lastmodOf('constructor'), undefined);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('a page with no source, or a file with no history, keeps its entry without a date', () => {
  const dir = fixture();
  try {
    const serialize = makeSerialize({ repoRoot: dir, base: BASE });
    assert.deepEqual(serialize({ url: url('nowhere') }), { url: url('nowhere') });
    assert.deepEqual(serialize({ url: 'https://example.invalid/other/' }), { url: 'https://example.invalid/other/' });
    assert.equal(lastCommit(dir, ['website/src/pages/never-committed.astro']), undefined);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('without git history no date is written: a shallow clone, and a folder that is no repository', () => {
  const dir = fixture();
  const parent = mkdtempSync(join(tmpdir(), 'psyche-lastmod-clone-'));
  try {
    const shallow = join(parent, 'shallow');
    execFileSync('git', ['clone', '-q', '--depth', '1', `file://${dir}`, shallow], { env: ENV, stdio: 'ignore' });
    assert.equal(historyAvailable(shallow), false);
    assert.deepEqual(makeSerialize({ repoRoot: shallow, base: BASE })({ url: url('research/gates') }), { url: url('research/gates') });
    // the footer asks the same helper: with no honest history it writes nothing, and never the build date
    assert.equal(makeLastmod({ repoRoot: shallow })('research/gates'), undefined);

    const bare = join(parent, 'plain');
    mkdirSync(join(bare, 'docs'), { recursive: true });
    writeFileSync(join(bare, 'docs/publish.json'), JSON.stringify(MANIFEST));
    assert.equal(historyAvailable(bare), false);
    assert.deepEqual(makeSerialize({ repoRoot: bare, base: BASE })({ url: url('') }), { url: url('') });
    assert.equal(makeLastmod({ repoRoot: bare })(''), undefined);
  } finally {
    rmSync(dir, { recursive: true, force: true });
    rmSync(parent, { recursive: true, force: true });
  }
});

// ---------------------------------------------------------------------------------------------
// Every module a page imports is covered by that page's list.
// ---------------------------------------------------------------------------------------------

const REPO = resolve(fileURLToPath(new URL('../../', import.meta.url)));
const SRC = join(REPO, 'website', 'src');
// Data the build writes into src/data from a file of tools/ (`npm run stage`; the copies are
// gitignored). Each stands for its source: it need not exist when the test runs, and in CI
// `npm test` runs before anything is staged.
const DERIVED = {
  'website/src/data/plan.json': 'tools/research_plan.json',
  'website/src/data/ledger.public.json': 'tools/ledger.json',
};

/** The modules a page file imports, followed to the end, as repository-relative paths. Imports of
 *  packages are skipped; one that cannot be found is returned in `unresolved`. */
function importClosure(entry) {
  const seen = new Set();
  const unresolved = [];
  const stack = [join(REPO, entry)];
  const specifier = /(?:\bfrom|\bimport)\s*\(?\s*["'`]([^"'`$]+)["'`]/g;
  while (stack.length) {
    const file = stack.pop();
    if (seen.has(file)) continue;
    seen.add(file);
    if (!/\.(astro|tsx?|mjs|js)$/.test(file)) continue;
    for (const m of readFileSync(file, 'utf8').matchAll(specifier)) {
      const spec = m[1].split('?')[0];
      const base = spec.startsWith('@/') ? join(SRC, spec.slice(2)) : spec.startsWith('.') ? resolve(dirname(file), spec) : null;
      if (!base) continue;
      if (DERIVED[relative(REPO, base)]) {
        seen.add(base);
        continue;
      }
      const found = ['', '.ts', '.tsx', '.astro', '.mjs', '.js', '/index.ts', '/index.tsx']
        .map((ext) => base + ext)
        .find((c) => existsSync(c) && statSync(c).isFile());
      if (found) stack.push(found);
      else unresolved.push(`${relative(REPO, file)}: ${spec}`);
    }
  }
  return { files: [...seen].map((f) => relative(REPO, f)).sort(), unresolved };
}

test('every module a site page imports is in that page\'s source list, so a change to it moves the date', () => {
  const entries = { '': 'index', roadmap: 'roadmap', battery: 'battery', status: 'status' };
  // Not text of the page: stylesheets. Data the build writes into src/data is covered by its source.
  for (const [route, name] of Object.entries(entries)) {
    const listed = SITE_PAGES[route];
    const covered = (rel) => listed.some((l) => rel === l || rel.startsWith(`${l}/`));
    const { files, unresolved } = importClosure(`website/src/pages/${name}.astro`);
    assert.deepEqual(unresolved, [], `page "${route}" imports something that cannot be found`);
    const missing = files.filter((rel) => {
      if (rel.endsWith('.css')) return false;
      return !covered(DERIVED[rel] ?? rel);
    });
    assert.deepEqual(missing, [], `page "${route}" imports files that are in no part of its lastmod list: add them to SITE_PAGES`);
  }
});

test('every file under the landing and battery component folders belongs to a page list', () => {
  const walk = (dir) =>
    readdirSync(dir).flatMap((name) => {
      const p = join(dir, name);
      return statSync(p).isDirectory() ? walk(p) : [relative(REPO, p)];
    });
  const all = Object.values(SITE_PAGES).flat();
  for (const folder of ['website/src/components/landing', 'website/src/components/battery']) {
    for (const rel of walk(join(REPO, folder))) {
      assert.ok(all.some((l) => rel === l || rel.startsWith(`${l}/`)), `${rel} is in no page's lastmod list`);
    }
  }
});
