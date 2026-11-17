// Every link and asset address that the page kit (src/kit/) and the front pages built on it write
// leads somewhere this site has: no design file name (*.html), no path that climbs out of the site
// (../), no other origin (the repository and mail links are the only exceptions), and every site path
// names a page under src/pages (a post: a slug in src/data/blog.json, rendered by blog/[slug].astro)
// or a file under public/.
//
// Read: every file under src/kit/, every layout under src/layouts/, and every page under src/pages/
// that is built on the kit (imports from @/kit/ or from the layouts). Addresses are read where the
// files write them: withBase('…') and href/src attributes in .astro, url(…) in .css, href in .svg,
// string literals in .js and .ts, and kit.js's menu, footer, home and asset paths.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const WEB = fileURLToPath(new URL('../', import.meta.url));
const SRC = join(WEB, 'src');
const KIT = join(SRC, 'kit');
const PAGES = join(SRC, 'pages');
const PUBLIC = join(WEB, 'public');

const seo = readFileSync(join(SRC, 'lib', 'seo.ts'), 'utf8');
const BASE = /^export const BASE = '([^']*)';$/m.exec(seo)?.[1];
const REPO_URL = /^export const REPO_URL = '([^']*)';$/m.exec(seo)?.[1];
// The posts, read from the committed sources: docs/blog/<slug>/index.md, a draft left out. The staged
// list (src/data/blog.json) is not read, because it exists only after staging and this test runs before.
const POSTS_DIR = join(WEB, '..', 'docs', 'blog');
const BLOG = {
  posts: readdirSync(POSTS_DIR, { withFileTypes: true })
    .filter((e) => e.isDirectory() && existsSync(join(POSTS_DIR, e.name, 'index.md')))
    .filter((e) => !/^draft:\s*true\s*$/m.test(readFileSync(join(POSTS_DIR, e.name, 'index.md'), 'utf8').split(/^---\s*$/m)[1] ?? ''))
    .map((e) => ({ slug: e.name, route: `blog/${e.name}/` })),
};

function walk(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(join(dir, e.name)) : [join(dir, e.name)]));
}
const rel = (p) => relative(WEB, p).split('\\').join('/');

/** The files this test reads. */
export function scannedFiles() {
  const kit = walk(KIT).filter((p) => /\.(astro|ts|js|mjs|css|svg|json)$/.test(p));
  const layouts = walk(join(SRC, 'layouts')).filter((p) => p.endsWith('.astro'));
  const pages = walk(PAGES).filter((p) => p.endsWith('.astro'))
    .filter((p) => /from\s+['"](?:@\/kit\/|@\/layouts\/|(?:\.\.\/)+(?:kit|layouts)\/)/.test(readFileSync(p, 'utf8')));
  return [...kit, ...layouts, ...pages];
}

// ---------------------------------------------------------------------------------------------
// Reading addresses out of a file. Each address comes back as { at, value, kind }:
//   kind 'site'  a path on this site, without the base (withBase('x/'), or '/x/' with BASE '/')
//   kind 'raw'   an address as written (an attribute, a url(), a string literal that looks like one)
// ---------------------------------------------------------------------------------------------
const LOOKS_LIKE_ADDRESS = /^(?:[a-z][a-z0-9+.-]*:\/\/|(?:mailto|tel|javascript|data|blob|file|ftp):|\/\/|\.{1,2}\/|\/(?!\/)|#|[\w.-]+\.(?:html?|svg|png|jpe?g|webp|gif|css|js|mjs|xml|json|woff2?)(?:[?#].*)?$)/i;

export function addresses(path, text) {
  const out = [];
  const line = (i) => text.slice(0, i).split('\n').length;
  const push = (i, value, kind) => out.push({ at: `${path}:${line(i)}`, value, kind });
  if (path.endsWith('.astro')) {
    for (const m of text.matchAll(/withBase\(\s*(['"`])([^'"`$]*)\1\s*\)/g)) push(m.index, m[2], 'site');
    for (const m of text.matchAll(/\s(?:href|src|action|poster|srcset|xlink:href)="([^"]*)"/g)) push(m.index, m[1], 'raw');
    for (const m of text.matchAll(/url\(\s*['"]?([^'")]+)['"]?\s*\)/g)) push(m.index, m[1], 'raw');
  } else if (path.endsWith('.css')) {
    for (const m of text.matchAll(/url\(\s*['"]?([^'")]+)['"]?\s*\)/g)) push(m.index, m[1], 'raw');
    for (const m of text.matchAll(/@import\s+['"]([^'"]+)['"]/g)) push(m.index, m[1], 'raw');
  } else if (path.endsWith('.svg')) {
    for (const m of text.matchAll(/\s(?:href|xlink:href|src)="([^"]*)"/g)) push(m.index, m[1], 'raw');
    for (const m of text.matchAll(/url\(\s*['"]?([^'")]+)['"]?\s*\)/g)) push(m.index, m[1], 'raw');
  } else {
    // .js / .ts: every string literal that looks like an address (module specifiers included)
    for (const m of text.matchAll(/(['"`])((?:\\.|(?!\1)[^\\\n])*)\1/g)) {
      const v = m[2];
      if (LOOKS_LIKE_ADDRESS.test(v) && !/\s/.test(v)) push(m.index, v, 'raw');
    }
  }
  return out;
}

const NAMESPACES = /^http:\/\/www\.w3\.org\/(?:2000\/svg|1999\/xlink|1999\/xhtml|XML\/1998\/namespace)$/;

/** Why an address is wrong, or null. `module` is true for module specifiers in .js/.ts/.astro. */
export function problem(addr) {
  const v = addr.value;
  if (/(?:^|[\/\w-])[\w-]+\.html?(?:[?#]|$)/i.test(v)) return 'names an .html file (a design file name, not a route)';
  if (/(?:^|\/)\.\.\//.test(v)) return 'climbs with ../';
  if (/^(?:[a-z][a-z0-9+.-]*:)?\/\//i.test(v)) {
    if (NAMESPACES.test(v)) return null; // an XML namespace, not a link
    if (REPO_URL && (v === REPO_URL || v.startsWith(REPO_URL + '/'))) return null; // the repository
    return 'points to another origin';
  }
  if (/^[a-z][a-z0-9+.-]*:/i.test(v)) return /^mailto:[^\s@]+@[^\s@]+$/i.test(v) ? null : `uses the scheme ${v.split(':')[0]}:`;
  return null;
}

// ---------------------------------------------------------------------------------------------
// Routes the site has.
// ---------------------------------------------------------------------------------------------
/** The page or file a site path (no base, e.g. 'about/' or 'brand/x.svg') leads to, or null. */
export function resolveSite(path) {
  const p = path.split('#')[0].split('?')[0].replace(/^\/+/, '');
  if (/\.[a-z0-9]+$/i.test(p)) return existsSync(join(PUBLIC, p)) ? `public/${p}` : null;
  if (p !== '' && !p.endsWith('/')) return null; // every page of this site is a folder
  const route = p.replace(/\/$/, '');
  if (route === '') return existsSync(join(PAGES, 'index.astro')) ? 'src/pages/index.astro' : null;
  for (const f of [`${route}.astro`, `${route}/index.astro`]) if (existsSync(join(PAGES, f))) return `src/pages/${f}`;
  const post = /^blog\/([a-z0-9-]+)$/.exec(route);
  if (post && BLOG.posts.some((x) => x.slug === post[1]) && existsSync(join(PAGES, 'blog', '[slug].astro'))) return 'src/pages/blog/[slug].astro';
  return null;
}

/** Turns a raw address into a site path when it is one ('/x/' under BASE '/'), else null. */
function sitePathOf(addr) {
  if (addr.kind === 'site') return addr.value;
  // in scripts a string starting with '/' is as often markup ('/>') or a pattern as a path; the
  // script that writes links, kit.js, has its paths checked one by one in the test above
  if (/\.(?:js|mjs|ts)$/.test(addr.at.split(':')[0])) return null;
  const v = addr.value;
  if (v.startsWith('/') && !v.startsWith('//')) return BASE && v.startsWith(BASE) ? v.slice(BASE.length) : v.slice(1);
  return null;
}

// Module specifiers and build-time imports are not links: '@/…', './x.js?raw', 'three', node: …
function isModuleSpecifier(addr, text) {
  if (addr.kind !== 'raw') return false;
  const v = addr.value;
  if (/^(?:@\/|\.\/|node:)/.test(v) || /\?(?:raw|url)$/.test(v)) return true;
  return false;
}

// ---------------------------------------------------------------------------------------------
// The tests
// ---------------------------------------------------------------------------------------------
test('the checker itself: it finds each kind of bad address in a sample', () => {
  const sample = [
    ['x.astro', '<a href="about.html">a</a>'],
    ['x.astro', '<a href={withBase("../film/index.html")}>a</a>'],
    ['x.astro', '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=X">'],
    ['x.css', '.a { background: url("https://cdn.example.com/x.png"); }'],
    ['x.js', "import('https://cdnjs.cloudflare.com/ajax/libs/three.js/0.160.0/three.module.min.js')"],
    ['x.js', "var HOME = KIT_DIR + '../film/index.html';"],
    ['x.svg', '<svg><a href="//evil.example/">x</a></svg>'],
    ['x.ts', "export const a = 'blog-three-questions-before-a-number-counts.html';"],
  ];
  for (const [path, text] of sample) {
    const found = addresses(path, text).map(problem).filter(Boolean);
    assert.ok(found.length > 0, `the checker missed the bad address in ${path}: ${text}`);
  }
  const fine = [
    ['x.astro', '<a href="#top">a</a><a href={withBase(\'about/\')}>b</a><a href="mailto:someone@example.org">c</a>'],
    ['x.svg', '<svg xmlns="http://www.w3.org/2000/svg"><use href="#g"/></svg>'],
    ['x.js', `var DEV = '${REPO_URL}'; var NS = 'http://www.w3.org/2000/svg';`],
  ];
  for (const [path, text] of fine) assert.deepEqual(addresses(path, text).map(problem).filter(Boolean), [], `${path}: ${text}`);
  assert.equal(resolveSite('no-such-page/'), null);
  assert.equal(resolveSite('blog/no-such-post/'), null);
  assert.equal(resolveSite('brand/no-such-file.svg'), null);
});

test('the kit has been imported (this test does not pass on an empty folder)', () => {
  for (const f of ['kit.js', 'kit.css', 'orb-head.js', 'orb-head.css', 'Header.astro', 'film/Body.astro', 'film/film.js', 'film/gen.js']) {
    assert.ok(existsSync(join(KIT, f)), `src/kit/${f} is missing: run the page import`);
  }
  for (const page of ['what-were-building', 'experiments', 'about', 'blog', 'not-found']) {
    for (const f of ['Main.astro', 'page.css', 'page.js', 'page.ts']) {
      assert.ok(existsSync(join(KIT, 'pages', page, f)), `src/kit/pages/${page}/${f} is missing: run the page import`);
    }
  }
  // a post's own figures (src/kit/posts/<slug>/) belong to a post the site has; their fit to the post's
  // text is tested in scripts/post-figures.test.mjs
  const postDirs = existsSync(join(KIT, 'posts')) ? readdirSync(join(KIT, 'posts'), { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name) : [];
  for (const slug of postDirs) {
    assert.ok(BLOG.posts.some((p) => p.slug === slug), `src/kit/posts/${slug}/ is not a post of docs/blog/`);
    assert.ok(existsSync(join(KIT, 'stills', 'posts', slug)), `src/kit/stills/posts/${slug}/ is missing: run the page import`);
  }
});

test('no address in the kit or the front pages names a design file, climbs out of the site, or leaves it', () => {
  const bad = [];
  let read = 0;
  for (const file of scannedFiles()) {
    const text = readFileSync(file, 'utf8');
    for (const a of addresses(rel(file), text)) {
      read++;
      const why = problem(a);
      if (why) bad.push(`${a.at}: ${a.value}: ${why}`);
    }
  }
  assert.ok(read >= 30, `only ${read} address(es) read: the reader is not finding the kit's links`);
  assert.deepEqual(bad, []);
});

// The names of the design folders and design tools the kit is imported from, which live outside this
// repository and are not named in it: kept as SHA-256 digests of the lower-case name, so this public
// test can find them without spelling them.
const PRIVATE_NAME_DIGESTS = new Set([
  '6272697125d75541277d993f8f5633089482907f8415c902b475d10604f9847b',
  '041b69a18166b0a71906bf7cdbecec73efa686ceb4a7d2f572c7a0f537286c3c',
  'fd4724e97003de393e3446a2b4345f1a4ea0a1e8d806b8368b07af096dc955eb',
  '6dfb7bc1acd89941f1167a44a35851e22eab6a1382e4d868bf02c098dca72bc4',
  '4abdd4076edb21d4c4489b817320878cf723750c687b1644e90cfd4b7f3b1b4c',
  '96828587e5d542b59d27b5b2cbb28098d68b2e44b626815175e5eef91aca96be',
  'cde4011b99302aaecc47ab8ef5570a3116321719bbcc5d2e38cf206723e3265f',
]);
const sha256 = (s) => createHash('sha256').update(s).digest('hex');

/** Whether a line names one of `digests`: every word and every hyphen-joined run of a word's parts,
 *  in lower case, as written and with a final "s" dropped, is compared by its digest. */
export function namesOneOf(line, digests) {
  for (const word of line.toLowerCase().split(/[^a-z0-9-]+/)) {
    const parts = word.split('-').filter(Boolean);
    for (let i = 0; i < parts.length; i++) {
      for (let j = i + 1; j <= parts.length; j++) {
        const run = parts.slice(i, j).join('-');
        if (digests.has(sha256(run)) || (run.endsWith('s') && digests.has(sha256(run.slice(0, -1))))) return true;
      }
    }
  }
  return false;
}

test('the name check itself finds a name inside a longer word, in the plural and in a file name', () => {
  const decoy = new Set([sha256('decoy-word')]);
  assert.ok(namesOneOf('see Decoy-Words.mjs', decoy));
  assert.ok(namesOneOf("var x = 'a-decoy-word-b/index.html';", decoy));
  assert.ok(!namesOneOf('a decoy, a word, decoyword', decoy));
  assert.equal(PRIVATE_NAME_DIGESTS.size, 7);
  for (const d of PRIVATE_NAME_DIGESTS) assert.match(d, /^[0-9a-f]{64}$/);
});

test('the kit files never name the design folders or a design tool, and never climb (../), anywhere', () => {
  const bad = [];
  for (const file of walk(KIT)) {
    readFileSync(file, 'utf8').split('\n').forEach((l, i) => {
      if (/\.\.\//.test(l) || namesOneOf(l, PRIVATE_NAME_DIGESTS)) bad.push(`${rel(file)}:${i + 1}: ${l.trim().slice(0, 120)}`);
    });
  }
  assert.deepEqual(bad, []);
});

test("kit.js writes its links from the site's base path, to the four menu pages, the footer pages and the brand files", () => {
  assert.equal(BASE, '/', "kit.js writes links from '/': if the site's base path changes, kit.js's KIT_DIR must change with it");
  const k = readFileSync(join(KIT, 'kit.js'), 'utf8');
  assert.match(k, /^  var KIT_DIR = '\/';$/m);
  assert.match(k, /^  var HOME = KIT_DIR;$/m);
  const assets = /^  var ASSETS = KIT_DIR \+ '([^']*)';$/m.exec(k);
  assert.ok(assets, 'kit.js sets ASSETS from KIT_DIR');
  const nav = [...k.matchAll(/\{ label: [^,]+, file: '([^']*)'/g)].map((m) => m[1]);
  assert.deepEqual(nav, ['what-were-building/', 'experiments/', 'blog/', 'about/'], 'the menu');
  const foot = [...k.matchAll(/\{ label: '[^']*', href: KIT_DIR \+ '([^']*)' \}/g)].map((m) => m[1]);
  assert.deepEqual(foot, ['blog/', 'about/'], 'the footer');
  assert.match(k, /\{ label: 'For developers', href: SITE\.developers \}/);
  assert.equal(/developers: '([^']*)'/.exec(k)?.[1], REPO_URL, 'the footer\'s developers link is the repository (lib/seo.ts REPO_URL)');
  const files = [...k.matchAll(/ASSETS \+ '([^'"]*)/g)].map((m) => assets[1] + m[1]);
  assert.ok(files.length >= 2, 'kit.js loads the wordmarks from ASSETS');
  const missing = [...nav, ...foot, '', ...files].filter((p) => !resolveSite(p)).map((p) => `/${p}`);
  assert.deepEqual(missing, [], 'kit.js links to a route or file the site does not have');
  // the current-page mark compares the path with the menu's paths; the post pattern matches a post route
  const match = /match: \/([^\n]*)\/([a-z]*)\s*\}/.exec(k);
  assert.ok(match, 'the Blog item marks posts');
  const re = new RegExp(match[1], match[2]);
  for (const p of BLOG.posts) assert.ok(re.test(p.route), `the Blog item does not mark the post route ${p.route}`);
});

test("the film's header and phone menu carry the site's menu: the wordmark home and kit.js's four pages, in order", () => {
  const k = readFileSync(join(KIT, 'kit.js'), 'utf8');
  const nav = [...k.matchAll(/\{ label: (?:"([^"]*)"|'([^']*)'), file: '([^']*)'/g)].map((m) => `${m[3]} ${m[1] ?? m[2]}`);
  assert.equal(nav.length, 4, "kit.js's menu");
  const body = readFileSync(join(KIT, 'film', 'Body.astro'), 'utf8');
  const part = (start, end) => {
    const a = body.indexOf(start);
    assert.ok(a >= 0, `src/kit/film/Body.astro has no ${start}`);
    assert.equal(body.indexOf(start, a + 1), -1, `src/kit/film/Body.astro has ${start} twice`);
    return body.slice(a, body.indexOf(end, a));
  };
  const head = part('<header class="k-head">', '</header>');
  const menu = part('<div class="k-menu" id="k-menu"', '</nav>');
  const links = (text, re) => [...text.matchAll(re)].map((m) => `${m[1]} ${m[2]}`);
  assert.deepEqual(links(head, /<a class="k-head__link" href=\{withBase\('([^']*)'\)\}[^>]*>([^<]*)<\/a>/g), nav, "the film's header links");
  assert.deepEqual(links(menu, /<a class="k-menu__link" href=\{withBase\('([^']*)'\)\}>([^<]*)<\/a>/g), nav, "the film's phone menu links");
  for (const [where, text] of [['header', head], ['phone menu', menu]]) {
    assert.match(text, /<a class="k-head__home" href=\{withBase\(''\)\} aria-label="Psyche, home"><img src=\{withBase\('brand\/psyche-wordmark-dark\.svg'\)\}/, `the film's ${where} wordmark leads home`);
  }
  assert.ok(resolveSite('brand/psyche-wordmark-dark.svg'), "the film's wordmark file is in public/brand/");
  // the film is dark only: its header keeps the theme switch's place empty and has no switch
  assert.match(head, /<span class="k-head__theme" aria-hidden="true"><\/span>/);
  assert.doesNotMatch(head + menu, /data-k-theme/);
  assert.match(head, /<button type="button" class="k-ctl k-head__menu" data-k-menu aria-haspopup="dialog" aria-expanded="false" aria-controls="k-menu">Menu<\/button>/);
});

test('every site path the kit and the front pages write leads to a page or file the site has', () => {
  const bad = [];
  let paths = 0;
  for (const file of scannedFiles()) {
    const text = readFileSync(file, 'utf8');
    for (const a of addresses(rel(file), text)) {
      if (isModuleSpecifier(a, text)) continue;
      const p = sitePathOf(a);
      if (p === null) continue;
      paths++;
      if (!resolveSite(p)) bad.push(`${a.at}: /${p} is not a page of the site (no file under src/pages or public/)`);
    }
  }
  assert.ok(paths >= 10, `only ${paths} site path(s) read`);
  for (const post of BLOG.posts) if (!resolveSite(post.route)) bad.push(`docs/blog/${post.slug}: /${post.route} is not a page of the site`);
  assert.deepEqual(bad, []);
});
