// Fails the build when what the built pages tell a search engine or a link preview is wrong. Reads
// dist/ only (Node built-ins), after `astro build`. Usage: node scripts/check-seo.mjs
//
// Every built page (the 404 page included):
//   head      one title; a canonical address under the site; a description of 120 to 160 characters,
//             different on every page; og:title, og:description (the page's own),
//             og:url (the canonical address), og:locale, og:site_name; twitter:card, twitter:title and
//             twitter:description (the og values), twitter:image
//   image     og:image and twitter:image name a file that is in dist/, a PNG of the size og:image:width
//             and og:image:height say; og:image:alt and twitter:image:alt are not empty
//   type      og:type is "website" on the landing page and "article" everywhere else
//   colour    two theme-color tags, light and dark, with their media queries
//   icons     the 32 px icon, the 180 px touch icon and the manifest exist, at the sizes they claim
//   robots    noindex on the 404 page and on no other
//   404 page  its own title ("Page not found", a name and not a status code), the description in
//             lib/seo.ts NOT_FOUND, and its own canonical address; every other page keeps the rules above
//   JSON-LD   on the landing page only: parses, and holds a WebSite and a ResearchProject
//   own links every link in a page's body that is written with the site's whole address (a docs page
//             reaches the hand-written pages, which have no Markdown source to link, that way) leads to a
//             built page or file, and to an id that is on that page when it names one. The link validator
//             treats such an address as external and checks nothing
// The site:
//   robots.txt             allows everything and names the sitemap
//   site.webmanifest       parses; start_url inside scope; its icons exist at their sizes, one maskable
//   sitemap                every page but the 404 page is in it and nothing else is (the feed is not); each
//                          entry has a lastmod (the date of the last commit) when git history is available here
//   progress feed          every page's head names it (one <link rel="alternate" type="application/atom+xml">
//                          that reaches dist/progress.xml); the file parses as XML (Python's expat, since Node
//                          has no parser), is Atom 1.0, has an id, a title, an updated that is the newest
//                          event's day (never the build's), a self link at its own address, an alternate link
//                          to the progress page, the author CITATION.cff names, and one entry for each event of
//                          the plan (tools/publish/render_plan.py progress_events: the same ids, newest first),
//                          each with an id, a title, an updated, a summary and an alternate link to a built page
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { BASE, NOT_FOUND, ORIGIN, SITE_URL, THEME_COLOR } from '../src/lib/seo.ts';
import { historyAvailable } from './sitemap-lastmod.mjs';

const DIST = fileURLToPath(new URL('../dist/', import.meta.url));
const REPO = fileURLToPath(new URL('../../', import.meta.url));
const DESCRIPTION = { min: 120, max: 160 };
const FEED = { file: 'progress.xml', page: 'progress/', type: 'application/atom+xml' };
// Starlight writes `<title>` as the page's title, a bar and the site's title.
const TITLE_SUFFIX = ' | Psyche';

const problems = [];
const bad = (where, message) => problems.push(`${where}: ${message}`);

const decode = (s) =>
  s.replace(/&quot;/g, '"').replace(/&#39;|&#x27;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');

function attributes(tag) {
  const out = {};
  for (const m of tag.matchAll(/([A-Za-z_:][-A-Za-z0-9_:.]*)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?/g)) {
    if (m.index === 0) continue; // the tag name
    out[m[1].toLowerCase()] = decode(m[2] ?? m[3] ?? m[4] ?? '');
  }
  return out;
}

function head(html) {
  const end = html.search(/<\/head\b/i);
  const text = end === -1 ? html : html.slice(0, end);
  const tags = (name) => [...text.matchAll(new RegExp(`<${name}\\b[^>]*>`, 'gi'))].map((m) => attributes(m[0]));
  return {
    metas: tags('meta'),
    links: tags('link'),
    title: [...text.matchAll(/<title\b[^>]*>([^<]*)<\/title\b[^>]*>/gi)].map((m) => decode(m[1])),
    scripts: [...text.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\b[^>]*>/gi)].map((m) => ({ attrs: attributes(`<script ${m[1]}>`), body: m[2] })),
  };
}

// A built file from an address of the site, or null when the address is not below the site's base.
function fileOf(address) {
  let path;
  try {
    path = new URL(address, SITE_URL).pathname;
  } catch {
    return null;
  }
  if (!path.startsWith(BASE)) return null;
  return join(DIST, decodeURIComponent(path.slice(BASE.length)));
}

function pngSize(file) {
  const b = readFileSync(file);
  if (b.length < 24 || b.subarray(0, 8).toString('hex') !== '89504e470d0a1a0a') return null;
  return { width: b.readUInt32BE(16), height: b.readUInt32BE(20) };
}

function pages(dir = DIST, out = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (name === 'pagefind' || name === '_astro') continue;
    if (statSync(p).isDirectory()) pages(p, out);
    else if (name.endsWith('.html')) out.push(p);
  }
  return out;
}

const routeOfFile = (file) => relative(DIST, file).split(sep).join('/').replace(/(^|\/)index\.html$/, '').replace(/\.html$/, '').replace(/\/$/, '');

function checkImage(where, address, label, size) {
  const file = fileOf(address);
  if (!file || !existsSync(file)) return bad(where, `${label} ${address} is not a file of the site`);
  const png = pngSize(file);
  if (!png) return bad(where, `${label} ${address} is not a PNG`);
  if (size && (png.width !== size[0] || png.height !== size[1])) {
    bad(where, `${label} ${address} is ${png.width} x ${png.height}, not ${size[0]} x ${size[1]}`);
  }
}

const seen = new Map(); // description -> route
const routes = [];
const bodies = []; // [where, the page's body]: the own-address links are checked once every page is known
for (const file of pages().sort()) {
  const route = routeOfFile(file);
  const where = route === '' ? '/' : `/${route}`;
  const is404 = route === '404';
  const html = readFileSync(file, 'utf8');
  const h = head(html);
  routes.push(route);
  bodies.push([where, html.slice(html.search(/<\/head\b/i) + 1)]);

  const meta = (key, value) => h.metas.filter((m) => m[key] === value);
  const one = (key, value) => {
    const found = meta(key, value);
    if (found.length !== 1) {
      bad(where, `${found.length} <meta ${key}="${value}"> tags, expected one`);
      return undefined;
    }
    const content = found[0].content;
    if (content === undefined || content === '') bad(where, `<meta ${key}="${value}"> has no content`);
    return content;
  };

  if (h.title.length !== 1 || !h.title[0].trim()) bad(where, `${h.title.length} <title> elements, expected one with text`);
  const canonical = h.links.filter((l) => l.rel === 'canonical');
  if (canonical.length !== 1 || !canonical[0].href?.startsWith(SITE_URL)) bad(where, `needs one canonical address under ${SITE_URL}`);
  if (is404) {
    // The 404 page is a page of its own: a name for a title, the address it is built at, its own description.
    if (h.title.length === 1 && h.title[0] !== NOT_FOUND.title + TITLE_SUFFIX) bad(where, `the title is "${h.title[0]}", expected "${NOT_FOUND.title + TITLE_SUFFIX}"`);
    if (canonical.length === 1 && canonical[0].href !== `${SITE_URL}${NOT_FOUND.route}/`) bad(where, `the canonical address is ${canonical[0].href}, expected ${SITE_URL}${NOT_FOUND.route}/`);
  }

  const description = one('name', 'description');
  if (description !== undefined) {
    if (description.length < DESCRIPTION.min || description.length > DESCRIPTION.max) {
      bad(where, `description is ${description.length} characters, not ${DESCRIPTION.min} to ${DESCRIPTION.max}`);
    }
    if (is404 && description !== NOT_FOUND.description) bad(where, 'the description is not NOT_FOUND.description in src/lib/seo.ts');
    if (seen.has(description)) bad(where, `description is also the description of /${seen.get(description)}`);
    seen.set(description, route);
  }
  const ogTitle = one('property', 'og:title');
  const ogDescription = one('property', 'og:description');
  if (description !== undefined && ogDescription !== description) bad(where, 'og:description is not the page description');
  const url = one('property', 'og:url');
  if (url !== undefined && canonical[0] && url !== canonical[0].href) bad(where, 'og:url is not the canonical address');
  one('property', 'og:locale');
  one('property', 'og:site_name');
  const type = one('property', 'og:type');
  const wantType = route === '' ? 'website' : 'article';
  if (type !== undefined && type !== wantType) bad(where, `og:type is "${type}", expected "${wantType}"`);

  one('name', 'twitter:card');
  const twTitle = one('name', 'twitter:title');
  if (twTitle !== undefined && twTitle !== ogTitle) bad(where, 'twitter:title is not og:title');
  const twDescription = one('name', 'twitter:description');
  if (twDescription !== undefined && twDescription !== ogDescription) bad(where, 'twitter:description is not og:description');

  const ogImage = one('property', 'og:image');
  const twImage = one('name', 'twitter:image');
  if (ogImage !== undefined && twImage !== undefined && ogImage !== twImage) bad(where, 'twitter:image is not og:image');
  const width = Number(one('property', 'og:image:width'));
  const height = Number(one('property', 'og:image:height'));
  if (ogImage !== undefined) checkImage(where, ogImage, 'og:image', [width, height]);
  one('property', 'og:image:alt');
  one('name', 'twitter:image:alt');

  const themes = meta('name', 'theme-color');
  const light = themes.find((m) => m.media === '(prefers-color-scheme: light)');
  const dark = themes.find((m) => m.media === '(prefers-color-scheme: dark)');
  if (themes.length !== 2 || light?.content !== THEME_COLOR.light || dark?.content !== THEME_COLOR.dark) {
    bad(where, `needs two theme-color tags: ${THEME_COLOR.light} for light and ${THEME_COLOR.dark} for dark, each with its media query`);
  }

  const icon32 = h.links.find((l) => l.rel === 'icon' && l.sizes === '32x32');
  if (!icon32) bad(where, 'no <link rel="icon" sizes="32x32">');
  else checkImage(where, icon32.href, 'the 32 px icon', [32, 32]);
  const touch = h.links.find((l) => l.rel === 'apple-touch-icon');
  if (!touch) bad(where, 'no <link rel="apple-touch-icon">');
  else checkImage(where, touch.href, 'the touch icon', [180, 180]);
  const manifest = h.links.find((l) => l.rel === 'manifest');
  if (!manifest) bad(where, 'no <link rel="manifest">');
  else if (!existsSync(fileOf(manifest.href) ?? '')) bad(where, `manifest ${manifest.href} is not a file of the site`);
  if (!h.links.some((l) => /(^|\s)(shortcut )?icon(\s|$)/.test(l.rel ?? '') && l.type === 'image/svg+xml')) bad(where, 'the SVG icon link is missing');
  const feeds = h.links.filter((l) => l.rel === 'alternate' && l.type === FEED.type);
  if (feeds.length !== 1) bad(where, `${feeds.length} <link rel="alternate" type="${FEED.type}"> tags, expected one (the progress feed)`);
  else {
    if (fileOf(feeds[0].href ?? '') !== join(DIST, FEED.file)) bad(where, `the feed link ${feeds[0].href} does not lead to /${FEED.file}`);
    if (!feeds[0].title) bad(where, 'the feed link has no title for a feed reader to show');
  }

  const robots = meta('name', 'robots');
  if (is404 && !(robots.length === 1 && /\bnoindex\b/.test(robots[0].content))) bad(where, 'the 404 page must be noindex');
  if (!is404 && robots.length) bad(where, `has a robots meta (${robots.map((r) => r.content).join(', ')}), and only the 404 page may`);

  const ld = h.scripts.filter((s) => s.attrs.type === 'application/ld+json');
  if (route !== '' && ld.length) bad(where, 'structured data belongs on the landing page only');
  if (route === '') {
    if (ld.length !== 1) bad(where, `${ld.length} JSON-LD scripts, expected one`);
    for (const s of ld) {
      try {
        const graph = JSON.parse(s.body)['@graph'] ?? [];
        const types = graph.map((n) => n['@type']);
        for (const t of ['WebSite', 'ResearchProject']) if (!types.includes(t)) bad(where, `JSON-LD has no ${t}`);
        for (const n of graph) {
          if (n.name !== 'Psyche' || n.url !== SITE_URL || !n.description) bad(where, `JSON-LD ${n['@type']} needs name "Psyche", url ${SITE_URL} and a description`);
        }
      } catch (e) {
        bad(where, `the JSON-LD does not parse: ${e.message}`);
      }
    }
  }
}
if (!routes.includes('') || !routes.includes('404')) bad('dist', 'no landing page or no 404 page was built');

// ---- the links written with the site's whole address
// A page may link another page of the site by its absolute address, and the link validator then calls the
// link external. Every one must lead to a built page or file, and to an id that is there when it names one.
const targetHtml = new Map(); // file -> its text
function ownLinkProblem(address) {
  let url;
  try {
    url = new URL(address);
  } catch {
    return 'is not an address';
  }
  const base = fileOf(`${url.origin}${url.pathname}`);
  if (!base || !existsSync(base)) return 'leads to nothing in the build';
  const file = statSync(base).isDirectory() ? join(base, 'index.html') : base;
  if (!existsSync(file)) return 'leads to a folder with no page';
  if (url.hash.length > 1) {
    const id = decodeURIComponent(url.hash.slice(1));
    if (!file.endsWith('.html')) return `names the id ${id} in a file that is not a page`;
    if (!targetHtml.has(file)) targetHtml.set(file, readFileSync(file, 'utf8'));
    const escaped = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    if (!new RegExp(`\\sid=(?:"${escaped}"|'${escaped}'|${escaped}[\\s>])`).test(targetHtml.get(file))) return `names the id ${id}, which is not on that page`;
  }
  return null;
}
let ownLinks = 0;
for (const [where, body] of bodies) {
  for (const m of body.matchAll(/<a\b[^>]*>/gi)) {
    const href = attributes(m[0]).href;
    if (!href?.startsWith(SITE_URL)) continue;
    ownLinks += 1;
    const problem = ownLinkProblem(href);
    if (problem) bad(where, `the link ${href} ${problem}`);
  }
}

// ---- the site's own files
const robotsFile = join(DIST, 'robots.txt');
if (!existsSync(robotsFile)) bad('/robots.txt', 'missing');
else {
  const text = readFileSync(robotsFile, 'utf8');
  if (!/^User-agent: \*$/m.test(text) || !/^Allow: \/$/m.test(text) || /^Disallow:\s*\S/m.test(text)) bad('/robots.txt', 'must allow every crawler everywhere');
  if (!text.includes(`Sitemap: ${SITE_URL}sitemap-index.xml`)) bad('/robots.txt', `must name ${SITE_URL}sitemap-index.xml`);
}

const manifestFile = join(DIST, 'site.webmanifest');
if (!existsSync(manifestFile)) bad('/site.webmanifest', 'missing');
else {
  try {
    const m = JSON.parse(readFileSync(manifestFile, 'utf8'));
    for (const k of ['name', 'short_name', 'start_url', 'scope', 'display', 'background_color', 'theme_color']) {
      if (typeof m[k] !== 'string' || !m[k]) bad('/site.webmanifest', `${k} is missing`);
    }
    if (m.start_url !== BASE || m.scope !== BASE) bad('/site.webmanifest', `start_url and scope must be ${BASE}`);
    for (const k of ['background_color', 'theme_color']) if (!/^#[0-9a-f]{6}$/i.test(m[k] ?? '')) bad('/site.webmanifest', `${k} must be #rrggbb`);
    let maskable = 0;
    const sizes = new Set();
    for (const icon of m.icons ?? []) {
      if (!icon.src?.startsWith(BASE)) bad('/site.webmanifest', `icon ${icon.src} is outside ${BASE}`);
      const file = fileOf(icon.src ?? '');
      if (!file || !existsSync(file)) {
        bad('/site.webmanifest', `icon ${icon.src} is not a file of the site`);
        continue;
      }
      if (icon.type === 'image/png') {
        const png = pngSize(file);
        if (!png || `${png.width}x${png.height}` !== icon.sizes) bad('/site.webmanifest', `icon ${icon.src} is ${png ? `${png.width}x${png.height}` : 'not a PNG'}, not ${icon.sizes}`);
        sizes.add(icon.sizes);
        if (icon.purpose === 'maskable') maskable += 1;
      }
    }
    for (const s of ['192x192', '512x512']) if (!sizes.has(s)) bad('/site.webmanifest', `no ${s} PNG icon`);
    if (!maskable) bad('/site.webmanifest', 'no maskable icon');
  } catch (e) {
    bad('/site.webmanifest', `does not parse: ${e.message}`);
  }
}

// ---- the sitemap
const sitemapIndex = join(DIST, 'sitemap-index.xml');
if (!existsSync(sitemapIndex)) bad('/sitemap-index.xml', 'missing');
else {
  const files = [...readFileSync(sitemapIndex, 'utf8').matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => fileOf(m[1]));
  if (!files.length) bad('/sitemap-index.xml', 'names no sitemap');
  const entries = [];
  for (const f of files) {
    if (!f || !existsSync(f)) {
      bad('/sitemap-index.xml', 'names a sitemap that is not built');
      continue;
    }
    for (const m of readFileSync(f, 'utf8').matchAll(/<url>([\s\S]*?)<\/url>/g)) {
      entries.push({ loc: m[1].match(/<loc>([^<]*)<\/loc>/)?.[1], lastmod: m[1].match(/<lastmod>([^<]*)<\/lastmod>/)?.[1] });
    }
  }
  const locs = entries.map((e) => e.loc);
  const wanted = routes.filter((r) => r !== '404').map((r) => (r === '' ? SITE_URL : `${SITE_URL}${r}/`));
  for (const w of wanted) if (!locs.includes(w)) bad('/sitemap', `${w} is not in the sitemap`);
  for (const l of locs) if (!wanted.includes(l)) bad('/sitemap', `${l} is in the sitemap and is no page of the site`);
  for (const l of locs) if (l.endsWith('.xml')) bad('/sitemap', `${l} is a feed or a data file, and the sitemap lists pages only`);
  if (new Set(locs).size !== locs.length) bad('/sitemap', 'an address is listed twice');
  const dated = historyAvailable(REPO);
  for (const e of entries) {
    if (!e.lastmod) {
      if (dated) bad('/sitemap', `${e.loc} has no lastmod although git history is available`);
      continue;
    }
    const t = Date.parse(e.lastmod);
    if (!/^\d{4}-\d{2}-\d{2}T/.test(e.lastmod) || Number.isNaN(t)) bad('/sitemap', `${e.loc} has an unreadable lastmod ${e.lastmod}`);
    else if (t > Date.now() + 86400000) bad('/sitemap', `${e.loc} has a lastmod in the future (${e.lastmod})`);
  }
  console.log(`check-seo: ${entries.length} sitemap entries, ${dated ? 'each with a lastmod from git' : 'no git history here, so no dates'}`);
}

// ---- the progress feed
// Node has no XML parser, so the file is read by Python's (expat), which the build already needs to stage the
// site. The plan's events are derived by the same function that staged the feed's data, from the plan on disk.
const FEED_PROBE = `
import json, sys
import xml.etree.ElementTree as ET
repo = sys.argv[2]
sys.path.insert(0, repo + '/tools/publish')
import core, render_plan
A = '{http://www.w3.org/2005/Atom}'
def text(el, name):
    child = el.find(A + name)
    return None if child is None or child.text is None else child.text.strip()
def links(el):
    return [{'rel': l.get('rel'), 'type': l.get('type'), 'href': l.get('href')} for l in el.findall(A + 'link')]
root = ET.parse(sys.argv[1]).getroot()
plan = core.load_plan(repo)
events = render_plan.progress_events(plan)
author = root.find(A + 'author')
print(json.dumps({
    'root': root.tag,
    'lang': root.get('{http://www.w3.org/XML/1998/namespace}lang'),
    'id': text(root, 'id'), 'title': text(root, 'title'), 'updated': text(root, 'updated'),
    'author': None if author is None else text(author, 'name'),
    'links': links(root),
    'entries': [{'id': text(e, 'id'), 'title': text(e, 'title'), 'updated': text(e, 'updated'),
                 'summary': text(e, 'summary'), 'links': links(e)} for e in root.findall(A + 'entry')],
    'events': [e['id'] for e in events],
    'newest': events[0]['date'] if events else plan['as_of'],
    'citation': core.citation_author(open(repo + '/CITATION.cff', encoding='utf-8').read()),
}))
`;

const feedFile = join(DIST, FEED.file);
const problemsBeforeFeed = problems.length;
if (!existsSync(feedFile)) bad(`/${FEED.file}`, 'missing');
else {
  let f;
  try {
    f = JSON.parse(execFileSync('python3', ['-B', '-I', '-c', FEED_PROBE, feedFile, REPO.replace(/\/$/, '')], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }));
  } catch (e) {
    bad(`/${FEED.file}`, `cannot be read as XML, or the plan's events cannot be derived: ${String(e.stderr || e.message).trim().split('\n').pop()}`);
  }
  if (f) {
    const w = `/${FEED.file}`;
    const rfc3339 = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;
    const stampOk = (t) => typeof t === 'string' && rfc3339.test(t) && !Number.isNaN(Date.parse(t));
    const iri = /^[A-Za-z][A-Za-z0-9+.-]*:\S+$/;
    if (f.root !== '{http://www.w3.org/2005/Atom}feed') bad(w, `the root is ${f.root}, not an Atom 1.0 feed`);
    if (f.lang !== 'en') bad(w, 'the feed has no xml:lang="en"');
    if (!iri.test(f.id ?? '')) bad(w, `the feed id ${JSON.stringify(f.id)} is not an IRI`);
    if (!f.title) bad(w, 'the feed has no title');
    if (!stampOk(f.updated)) bad(w, `updated ${JSON.stringify(f.updated)} is not an RFC 3339 date and time`);
    else if (f.updated.slice(0, 10) !== f.newest) bad(w, `updated is ${f.updated}, not the day of the newest event (${f.newest}); a feed is dated by its events, never by the build`);
    if (!f.author) bad(w, 'the feed has no author');
    else if (f.author !== f.citation) bad(w, `the author is ${JSON.stringify(f.author)}, but CITATION.cff names ${JSON.stringify(f.citation)}`);
    const only = (list, rel, label) => {
      const found = list.filter((l) => l.rel === rel);
      if (found.length !== 1) bad(w, `${label}: ${found.length} <link rel="${rel}"> elements, expected one`);
      return found[0];
    };
    const self = only(f.links, 'self', 'the feed');
    if (self && (self.href !== `${SITE_URL}${FEED.file}` || self.type !== FEED.type)) bad(w, `the self link is ${self.href} (${self.type}), expected ${SITE_URL}${FEED.file} (${FEED.type})`);
    const alternate = only(f.links, 'alternate', 'the feed');
    if (alternate && alternate.href !== `${SITE_URL}${FEED.page}`) bad(w, `the alternate link is ${alternate.href}, expected ${SITE_URL}${FEED.page}`);
    if (alternate && !existsSync(join(fileOf(alternate.href) ?? DIST, 'index.html'))) bad(w, `the alternate link ${alternate.href} is not a built page`);

    if (f.entries.length !== f.events.length) bad(w, `${f.entries.length} entries for ${f.events.length} events in tools/research_plan.json`);
    const ids = new Set();
    f.entries.forEach((entry, n) => {
      const here = `${w} entry ${n + 1}`;
      if (!iri.test(entry.id ?? '')) bad(here, `the id ${JSON.stringify(entry.id)} is not an IRI`);
      else if (ids.has(entry.id)) bad(here, `the id ${entry.id} is also another entry's`);
      ids.add(entry.id);
      if (f.events[n] !== undefined && !(entry.id ?? '').endsWith(`/${f.events[n]}`)) bad(here, `its id ${entry.id} does not end in the plan's ${f.events[n]}: the entries must follow the plan's events, newest first`);
      if (!entry.title) bad(here, 'no title');
      if (!entry.summary) bad(here, 'no summary');
      if (!stampOk(entry.updated)) bad(here, `updated ${JSON.stringify(entry.updated)} is not an RFC 3339 date and time`);
      else if (n > 0 && stampOk(f.entries[n - 1].updated) && Date.parse(entry.updated) > Date.parse(f.entries[n - 1].updated)) bad(here, 'is newer than the entry before it; the feed is newest first');
      const link = only(entry.links, 'alternate', here);
      if (link && !link.href?.startsWith(SITE_URL)) bad(here, `its link ${link.href} is not an address under ${SITE_URL}`);
      else if (link && !existsSync(join(fileOf(link.href) ?? DIST, 'index.html'))) bad(here, `its link ${link.href} is not a built page`);
    });
    if (problems.length === problemsBeforeFeed) console.log(`check-seo: the progress feed is Atom with ${f.entries.length} entr${f.entries.length === 1 ? 'y' : 'ies'}, one for each event of the plan, dated ${f.updated}`);
  }
}

if (problems.length) {
  console.error(`check-seo: ${problems.length} problem(s)`);
  for (const p of problems) console.error(`  ${p}`);
  process.exit(1);
}
console.log(`check-seo: ${routes.length} pages, ${ownLinks} links by the site's own address, the manifest, robots.txt and the sitemap are in order (${ORIGIN})`);
