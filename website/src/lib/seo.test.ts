import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  BASE,
  NOT_FOUND,
  PROJECT_DESCRIPTION,
  SITE_URL,
  jsonLdScript,
  postJsonLd,
  projectJsonLd,
  routeOf,
  seoHead,
  type ArticleFacts,
  type HeadEntry,
} from './seo.ts';

// The head Starlight builds for a page, as far as this module reads it.
const starlightHead = (title: string, description: string): HeadEntry[] => [
  { tag: 'title', content: `${title} | Psyche` },
  { tag: 'meta', attrs: { property: 'og:title', content: title } },
  { tag: 'meta', attrs: { property: 'og:type', content: 'article' } },
  { tag: 'meta', attrs: { property: 'og:description', content: description } },
  { tag: 'meta', attrs: { name: 'description', content: description } },
];
const attrOf = (head: HeadEntry[], key: string, value: string) =>
  head.find((e) => e.tag === 'meta' && e.attrs?.[key] === value)?.attrs?.content;

test('routeOf names a page below the base', () => {
  assert.equal(routeOf('/psyche/'), '');
  assert.equal(routeOf('/psyche/404/'), '404');
  assert.equal(routeOf('/psyche/404'), '404');
  assert.equal(routeOf('/psyche/research/gates/'), 'research/gates');
  assert.equal(routeOf('/psyche/battery/index.html'), 'battery');
  assert.equal(routeOf('/research/gates/', '/'), 'research/gates');
});

test('the landing page is a website, every other page an article', () => {
  const head = starlightHead('Home', 'About.');
  assert.equal(attrOf(seoHead(head, ''), 'property', 'og:type'), 'website');
  assert.equal(attrOf(seoHead(head, 'research/gates'), 'property', 'og:type'), 'article');
  assert.equal(attrOf(seoHead(head, 'battery'), 'property', 'og:type'), 'article');
});

test('twitter:title and twitter:description come from the page, once', () => {
  const head = starlightHead('Decision gates', 'The gates of stage 2.');
  const out = seoHead(head, 'research/gates');
  assert.equal(attrOf(out, 'name', 'twitter:title'), 'Decision gates');
  assert.equal(attrOf(out, 'name', 'twitter:description'), 'The gates of stage 2.');
  assert.equal(out.filter((e) => e.attrs?.name === 'twitter:title').length, 1);
  // a head that already has them is left alone
  const again = seoHead(out, 'research/gates');
  assert.equal(again.filter((e) => e.attrs?.name === 'twitter:title').length, 1);
  assert.equal(again.filter((e) => e.attrs?.name === 'twitter:description').length, 1);
});

test('only the 404 page is noindex, and only the landing page carries structured data', () => {
  const head = starlightHead('404', 'Not found.');
  const robots = (route: string) => attrOf(seoHead(head, route), 'name', 'robots');
  assert.equal(robots('404'), 'noindex');
  for (const route of ['', 'battery', 'research/gates', 'substrate/overview']) assert.equal(robots(route), undefined);
  const scripts = (route: string) => seoHead(head, route).filter((e) => e.tag === 'script');
  assert.equal(scripts('').length, 1);
  assert.equal(scripts('404').length, 0);
  assert.equal(scripts('research/gates').length, 0);
});

test('seoHead returns a new array and leaves the one it was given unchanged', () => {
  const head = starlightHead('Home', 'About.');
  const before = JSON.stringify(head);
  seoHead(head, '');
  assert.equal(JSON.stringify(head), before);
});

test('the landing JSON-LD parses and describes the site and the project', () => {
  const entry = seoHead(starlightHead('Home', 'About.'), '').find((e) => e.tag === 'script');
  assert.ok(entry?.content);
  assert.equal(entry.attrs?.type, 'application/ld+json');
  const data = JSON.parse(entry.content);
  assert.equal(data['@context'], 'https://schema.org');
  const [site, project] = data['@graph'];
  assert.equal(site['@type'], 'WebSite');
  assert.equal(site.name, 'Psyche');
  assert.equal(site.url, SITE_URL);
  assert.equal(site.description, PROJECT_DESCRIPTION);
  assert.equal(project['@type'], 'ResearchProject');
  assert.equal(project.name, 'Psyche');
  assert.equal(project.url, SITE_URL);
  assert.equal(project.description, PROJECT_DESCRIPTION);
  assert.deepEqual(project.founder, {
    '@type': 'Person',
    name: 'Cagan Caliskan',
    sameAs: 'https://github.com/cagancaliskan',
  });
  assert.deepEqual(project.sameAs, ['https://github.com/cagancaliskan/psyche']);
  assert.ok(Array.isArray(project.keywords) && project.keywords.length > 0);
  // the two nodes refer to each other by the ids they declare
  assert.equal(site.about['@id'], project['@id']);
  assert.notEqual(site['@id'], project['@id']);
  assert.ok(SITE_URL.startsWith('https://') && SITE_URL.endsWith(BASE));
});

test('the JSON-LD names the aim as an aim and claims nothing about a component', () => {
  const text = JSON.stringify(projectJsonLd());
  assert.match(text, /as its long-term aim/);
  assert.doesNotMatch(text, /\b(is|achieves|reaches)\s+(an\s+)?(AGI|artificial general intelligence)/i);
  assert.doesNotMatch(text, /conscious|sentient|\bmind\b|proven|\boriginal\b|\bfirst\b/i);
  const keywords = (projectJsonLd()['@graph'] as { keywords?: string[] }[])[1].keywords ?? [];
  assert.ok(keywords.every((k) => !/general intelligence|agi/i.test(k)), 'the aim is not a keyword');
});

test('jsonLdScript cannot close its element, and reads back unchanged', () => {
  const data = { a: '</script><script>alert(1)</script>', b: '<!-- x -->', c: 'café' };
  const text = jsonLdScript(data);
  assert.ok(!text.includes('<'));
  assert.deepEqual(JSON.parse(text), data);
});

// The project sentence is typed in more than one place: here (the page descriptions, the structured
// data), in the web manifest, and in the social card (drawn into the image and recorded in its sidecar).
// copy_check scans this module, so it is the one the others are held to.
test('the manifest, the social card and its alt text say the project sentence of PROJECT_DESCRIPTION', () => {
  const read = (rel: string) => JSON.parse(readFileSync(new URL(rel, import.meta.url), 'utf8'));
  const manifest = read('../../public/site.webmanifest');
  const sidecar = read('../../../brand/psyche-social.json');
  const sentence = PROJECT_DESCRIPTION.replace(/^Psyche is an /, 'An ');
  assert.notEqual(sentence, PROJECT_DESCRIPTION, 'PROJECT_DESCRIPTION no longer starts "Psyche is an": update this test');
  assert.equal(manifest.description, sentence);
  assert.equal(sidecar.tagline, sentence);
  assert.ok(sidecar.alt.endsWith(` ${sentence}`), 'the card alt text ends with the sentence');
});

test('the 404 page has its own name and description, and is the one page that is noindex', () => {
  assert.equal(NOT_FOUND.route, '404');
  // a name, not a status code, and not the site name or the project sentence
  assert.equal(NOT_FOUND.title, 'Page not found');
  assert.doesNotMatch(NOT_FOUND.title, /\d/);
  assert.notEqual(NOT_FOUND.description, PROJECT_DESCRIPTION);
  // the same length rule as every other page (scripts/check-seo.mjs)
  assert.ok(NOT_FOUND.description.length >= 120 && NOT_FOUND.description.length <= 160, `${NOT_FOUND.description.length} characters`);
  assert.doesNotMatch(NOT_FOUND.description, /\b(proven|original|first|conscious|sentient)\b/i);
  const head = seoHead(starlightHead(NOT_FOUND.title, NOT_FOUND.description), NOT_FOUND.route);
  assert.equal(attrOf(head, 'name', 'robots'), 'noindex');
  assert.equal(attrOf(head, 'name', 'twitter:title'), NOT_FOUND.title);
  assert.equal(attrOf(head, 'name', 'twitter:description'), NOT_FOUND.description);
  assert.equal(attrOf(head, 'property', 'og:type'), 'article');
  // the route is what routeOf names the page's address
  assert.equal(routeOf(`${BASE}404/`), NOT_FOUND.route);
  assert.equal(routeOf(`${BASE}404`), NOT_FOUND.route);
});

const ARTICLE: ArticleFacts = { published: '2026-11-04', modified: '2026-11-06', author: 'Cagan Caliskan', tags: ['project', 'methods'] };
const withUrl = (head: HeadEntry[], url: string): HeadEntry[] => [...head, { tag: 'meta', attrs: { property: 'og:url', content: url } }];

test('a blog post carries its days, author and tags, and one BlogPosting with the same facts', () => {
  const url = `${SITE_URL}blog/opening-the-log/`;
  const head = withUrl(starlightHead('Opening the log', 'Why the project keeps a dated public log.'), url);
  const out = seoHead(head, 'blog/opening-the-log', ARTICLE);
  assert.equal(attrOf(out, 'property', 'og:type'), 'article');
  assert.equal(attrOf(out, 'property', 'article:published_time'), '2026-11-04');
  assert.equal(attrOf(out, 'property', 'article:modified_time'), '2026-11-06');
  assert.equal(attrOf(out, 'property', 'article:author'), 'Cagan Caliskan');
  assert.deepEqual(out.filter((e) => e.attrs?.property === 'article:tag').map((e) => e.attrs?.content), ['project', 'methods']);
  const scripts = out.filter((e) => e.tag === 'script');
  assert.equal(scripts.length, 1);
  const data = JSON.parse(scripts[0].content ?? '');
  assert.equal(data['@type'], 'BlogPosting');
  assert.equal(data.headline, 'Opening the log');
  assert.equal(data.url, url);
  assert.equal(data.datePublished, '2026-11-04');
  assert.equal(data.dateModified, '2026-11-06');
  assert.equal(data.author.name, 'Cagan Caliskan');
  assert.deepEqual(data.keywords, ['project', 'methods']);
});

test('a post never revised has no modified time, and its BlogPosting is modified on the day it was published', () => {
  const facts: ArticleFacts = { published: '2026-11-04', modified: null, author: 'A', tags: [] };
  const out = seoHead(withUrl(starlightHead('T', 'D.'), `${SITE_URL}blog/t/`), 'blog/t', facts);
  assert.equal(attrOf(out, 'property', 'article:modified_time'), undefined);
  assert.equal(out.filter((e) => e.attrs?.property === 'article:tag').length, 0);
  const data = postJsonLd({ url: `${SITE_URL}blog/t/`, title: 'T', description: 'D.', article: facts });
  assert.equal(data.dateModified, '2026-11-04');
  assert.equal('keywords' in data, false);
});

test('article facts are never written on the landing page or the 404 page', () => {
  for (const route of ['', '404']) {
    const out = seoHead(starlightHead('T', 'D.'), route, ARTICLE);
    assert.equal(attrOf(out, 'property', 'article:published_time'), undefined);
    assert.equal(out.filter((e) => e.tag === 'script').length, route === '' ? 1 : 0);
  }
});
