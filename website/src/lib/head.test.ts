import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  DESCRIPTION_LENGTH,
  PAGES,
  TITLE_SUFFIX,
  articleFacts,
  canonicalOf,
  headHtml,
  pageHead,
  type PageHeadInput,
} from './head.ts';
import { NOT_FOUND, PROJECT_DESCRIPTION, SITE_URL, THEME_COLOR, type ArticleFacts, type HeadEntry } from './seo.ts';

const social = JSON.parse(readFileSync(new URL('../../../brand/psyche-social.json', import.meta.url), 'utf8'));

// What scripts/check-seo.mjs reads of a head, from the entries instead of the built HTML.
const metas = (head: HeadEntry[], key: 'name' | 'property', value: string) =>
  head.filter((e) => e.tag === 'meta' && e.attrs?.[key] === value).map((e) => e.attrs?.content);
const one = (head: HeadEntry[], key: 'name' | 'property', value: string) => {
  const found = metas(head, key, value);
  assert.equal(found.length, 1, `${found.length} <meta ${key}="${value}">, expected one`);
  assert.equal(typeof found[0], 'string');
  assert.notEqual(found[0], '');
  return found[0] as string;
};
const links = (head: HeadEntry[]) => head.filter((e) => e.tag === 'link').map((e) => e.attrs ?? {});
const ld = (head: HeadEntry[]) => head.filter((e) => e.tag === 'script' && e.attrs?.type === 'application/ld+json');

// Every entry as one key: the element and the attribute that names it. The multiset of these is what a
// page type must have, exactly.
const keyOf = (e: HeadEntry) => {
  const a = e.attrs ?? {};
  if (e.tag === 'meta') return a.charset ? 'meta charset' : a.name ? `meta name=${a.name}` : `meta property=${a.property}`;
  if (e.tag === 'link') return `link rel=${a.rel}${a.sizes ? ` ${a.sizes}` : ''}`;
  if (e.tag === 'script') return `script ${a.type}`;
  return e.tag;
};
const keys = (head: HeadEntry[]) => head.map(keyOf).sort();

// The entries every page has (check-seo "Every built page"), in check-seo's terms.
const EVERY_PAGE = [
  'meta charset',
  'meta name=viewport',
  'title',
  'link rel=canonical',
  'link rel=sitemap',
  'link rel=icon 32x32',
  'link rel=apple-touch-icon 180x180',
  'link rel=manifest',
  'link rel=alternate',
  'link rel=alternate',
  'link rel=shortcut icon',
  'meta property=og:title',
  'meta property=og:type',
  'meta property=og:url',
  'meta property=og:locale',
  'meta property=og:description',
  'meta property=og:site_name',
  'meta name=description',
  'meta name=color-scheme',
  'meta name=theme-color',
  'meta name=theme-color',
  'meta property=og:image',
  'meta property=og:image:type',
  'meta property=og:image:width',
  'meta property=og:image:height',
  'meta property=og:image:alt',
  'meta name=twitter:card',
  'meta name=twitter:image',
  'meta name=twitter:image:alt',
  'meta name=twitter:title',
  'meta name=twitter:description',
];

const POST_ARTICLE: ArticleFacts = { published: '2026-11-13', modified: null, author: 'A. Author', tags: ['methods', 'project'] };
const POST: PageHeadInput = {
  route: 'blog/a-post-slug',
  title: 'A post & its "title"',
  description: 'A description of a post that is long enough for the rule: it has between one hundred and twenty and one hundred and sixty letters.',
  article: POST_ARTICLE,
};

// The checks of check-seo that every page passes, whatever its type.
function everyPage(head: HeadEntry[], input: PageHeadInput) {
  const titles = head.filter((e) => e.tag === 'title');
  assert.equal(titles.length, 1);
  const canonical = links(head).filter((l) => l.rel === 'canonical');
  assert.equal(canonical.length, 1);
  assert.equal(canonical[0].href, canonicalOf(input.route));
  assert.ok(String(canonical[0].href).startsWith(SITE_URL));
  const description = one(head, 'name', 'description');
  assert.equal(description, input.description);
  assert.ok(description.length >= DESCRIPTION_LENGTH.min && description.length <= DESCRIPTION_LENGTH.max);
  assert.equal(one(head, 'property', 'og:title'), input.title);
  assert.equal(one(head, 'property', 'og:description'), description);
  assert.equal(one(head, 'property', 'og:url'), canonical[0].href);
  assert.equal(one(head, 'property', 'og:locale'), 'en');
  assert.equal(one(head, 'property', 'og:site_name'), 'Psyche');
  assert.equal(one(head, 'property', 'og:type'), input.route === '' ? 'website' : 'article');
  assert.equal(one(head, 'name', 'twitter:card'), 'summary_large_image');
  assert.equal(one(head, 'name', 'twitter:title'), one(head, 'property', 'og:title'));
  assert.equal(one(head, 'name', 'twitter:description'), one(head, 'property', 'og:description'));
  assert.equal(one(head, 'property', 'og:image'), `${SITE_URL}og.png`);
  assert.equal(one(head, 'name', 'twitter:image'), one(head, 'property', 'og:image'));
  assert.equal(one(head, 'property', 'og:image:width'), String(social.width));
  assert.equal(one(head, 'property', 'og:image:height'), String(social.height));
  assert.equal(one(head, 'property', 'og:image:alt'), social.alt);
  assert.equal(one(head, 'name', 'twitter:image:alt'), social.alt);
  // two theme colours, light and dark, each with its media query
  const themes = head.filter((e) => e.tag === 'meta' && e.attrs?.name === 'theme-color').map((e) => e.attrs ?? {});
  assert.deepEqual(
    themes.map((t) => [t.content, t.media]),
    [
      [THEME_COLOR.light, '(prefers-color-scheme: light)'],
      [THEME_COLOR.dark, '(prefers-color-scheme: dark)'],
    ],
  );
  // icons and the manifest at the addresses public/ serves them from
  const ls = links(head);
  assert.equal(ls.find((l) => l.rel === 'icon' && l.sizes === '32x32')?.href, '/favicon-32.png');
  assert.equal(ls.find((l) => l.rel === 'apple-touch-icon')?.href, '/apple-touch-icon.png');
  assert.equal(ls.find((l) => l.rel === 'manifest')?.href, '/site.webmanifest');
  assert.ok(ls.some((l) => /(^|\s)(shortcut )?icon(\s|$)/.test(String(l.rel)) && l.type === 'image/svg+xml'));
  // both feeds, one link each, each with a title
  const feeds = ls.filter((l) => l.rel === 'alternate' && l.type === 'application/atom+xml');
  assert.deepEqual(feeds.map((l) => l.href).sort(), ['/blog.xml', '/progress.xml']);
  for (const f of feeds) assert.ok(f.title);
  // robots on the 404 page only
  assert.deepEqual(metas(head, 'name', 'robots'), input.route === NOT_FOUND.route ? ['noindex'] : []);
}

test('the page table: the chosen titles, a description of 120 to 160 characters each, all different', () => {
  const pages = Object.values(PAGES);
  assert.deepEqual(
    pages.map((p) => p.route),
    ['', 'what-were-building', 'experiments', 'about', 'blog', '404'],
  );
  assert.equal(PAGES.home.title, 'Psyche: New era of intelligence');
  assert.equal(PAGES.whatWereBuilding.title, "What we're building");
  assert.equal(PAGES.experiments.title, 'The five experiments');
  assert.equal(PAGES.about.title, 'About and contact');
  assert.equal(PAGES.blog.title, 'Blog');
  // the 404 page's are the ones check-seo compares the built page with
  assert.deepEqual(PAGES.notFound, { route: NOT_FOUND.route, title: NOT_FOUND.title, description: NOT_FOUND.description });
  for (const p of pages) {
    assert.ok(p.description.length >= 120 && p.description.length <= 160, `/${p.route}: ${p.description.length} characters`);
    assert.notEqual(p.description, PROJECT_DESCRIPTION);
    assert.doesNotMatch(p.description, /\b(proven|original|first|conscious|sentient)\b/i);
    assert.equal(p.description, p.description.trim());
    assert.doesNotMatch(p.description, /\s{2}|[‘’“”]/);
  }
  assert.equal(new Set(pages.map((p) => p.description)).size, pages.length);
  assert.equal(new Set(pages.map((p) => p.title)).size, pages.length);
});

test('the home page: its whole title, a website, the WebSite and ResearchProject data and nothing else', () => {
  const head = pageHead(PAGES.home);
  everyPage(head, PAGES.home);
  assert.deepEqual(keys(head), [...EVERY_PAGE, 'script application/ld+json'].sort());
  assert.deepEqual(
    head.filter((e) => e.tag === 'title').map((e) => e.content),
    ['Psyche: New era of intelligence'],
  );
  assert.equal(one(head, 'property', 'og:url'), SITE_URL);
  const scripts = ld(head);
  assert.equal(scripts.length, 1);
  const graph = JSON.parse(String(scripts[0].content))['@graph'] as Record<string, unknown>[];
  assert.deepEqual(graph.map((n) => n['@type']), ['WebSite', 'ResearchProject']);
  for (const n of graph) {
    assert.equal(n.name, 'Psyche');
    assert.equal(n.url, SITE_URL);
    assert.ok(n.description);
  }
  assert.deepEqual(metas(head, 'property', 'article:published_time'), []);
  assert.deepEqual(metas(head, 'property', 'article:author'), []);
});

test('an ordinary page: "<name> | Psyche", an article, no structured data, no robots, no article tags', () => {
  for (const page of [PAGES.whatWereBuilding, PAGES.experiments, PAGES.about]) {
    const head = pageHead(page);
    everyPage(head, page);
    assert.deepEqual(keys(head), [...EVERY_PAGE].sort());
    assert.deepEqual(
      head.filter((e) => e.tag === 'title').map((e) => e.content),
      [`${page.title}${TITLE_SUFFIX}`],
    );
    assert.equal(one(head, 'property', 'og:url'), `${SITE_URL}${page.route}/`);
  }
  assert.equal(pageHead(PAGES.whatWereBuilding).find((e) => e.tag === 'title')?.content, "What we're building | Psyche");
});

test("the blog's index: an ordinary page at /blog/", () => {
  const head = pageHead(PAGES.blog);
  everyPage(head, PAGES.blog);
  assert.deepEqual(keys(head), [...EVERY_PAGE].sort());
  assert.equal(head.find((e) => e.tag === 'title')?.content, 'Blog | Psyche');
  assert.equal(one(head, 'property', 'og:url'), `${SITE_URL}blog/`);
});

test('a blog post: its article tags and exactly one BlogPosting that says what the head says', () => {
  const head = pageHead(POST);
  everyPage(head, POST);
  assert.deepEqual(
    keys(head),
    [
      ...EVERY_PAGE,
      'meta property=article:published_time',
      'meta property=article:author',
      'meta property=article:tag',
      'meta property=article:tag',
      'script application/ld+json',
    ].sort(),
  );
  assert.equal(head.find((e) => e.tag === 'title')?.content, `${POST.title} | Psyche`);
  const day = one(head, 'property', 'article:published_time');
  const author = one(head, 'property', 'article:author');
  assert.match(day, /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(day, POST_ARTICLE.published);
  assert.equal(author, POST_ARTICLE.author);
  assert.deepEqual(metas(head, 'property', 'article:tag'), ['methods', 'project']);
  assert.deepEqual(metas(head, 'property', 'article:modified_time'), []);
  const scripts = ld(head);
  assert.equal(scripts.length, 1);
  const post = JSON.parse(String(scripts[0].content));
  assert.equal(post['@type'], 'BlogPosting');
  assert.equal(post.headline, one(head, 'property', 'og:title'));
  assert.equal(post.url, one(head, 'property', 'og:url'));
  assert.equal(post.url, `${SITE_URL}${POST.route}/`);
  assert.equal(post.datePublished, day);
  assert.equal(post.author?.name, author);
  assert.equal(post.description, one(head, 'name', 'description'));

  // a later revision adds article:modified_time; a revision on the day itself does not
  const revised = pageHead({ ...POST, article: { ...POST_ARTICLE, modified: '2026-11-15' } });
  assert.deepEqual(metas(revised, 'property', 'article:modified_time'), ['2026-11-15']);
  assert.equal(JSON.parse(String(ld(revised)[0].content)).dateModified, '2026-11-15');
  const sameDay = pageHead({ ...POST, article: { ...POST_ARTICLE, modified: POST_ARTICLE.published } });
  assert.deepEqual(metas(sameDay, 'property', 'article:modified_time'), []);
});

test("a post's article facts come from its front matter, the author falling back to the blog's", () => {
  assert.deepEqual(articleFacts({ date: '2026-11-13', tags: ['methods'] }, 'Blog Author'), {
    published: '2026-11-13',
    modified: null,
    author: 'Blog Author',
    tags: ['methods'],
  });
  assert.deepEqual(articleFacts({ date: '2026-11-13', updated: '2026-11-14', author: 'Post Author' }, 'Blog Author'), {
    published: '2026-11-13',
    modified: '2026-11-14',
    author: 'Post Author',
    tags: [],
  });
});

test('the 404 page: its own name, its own address, noindex, no structured data', () => {
  const head = pageHead(PAGES.notFound);
  everyPage(head, PAGES.notFound);
  assert.deepEqual(keys(head), [...EVERY_PAGE, 'meta name=robots'].sort());
  assert.equal(head.find((e) => e.tag === 'title')?.content, NOT_FOUND.title + ' | Psyche');
  assert.equal(head.find((e) => e.tag === 'title')?.content, 'Page not found | Psyche');
  assert.equal(links(head).find((l) => l.rel === 'canonical')?.href, `${SITE_URL}${NOT_FOUND.route}/`);
  assert.equal(one(head, 'name', 'description'), NOT_FOUND.description);
  assert.equal(one(head, 'name', 'robots'), 'noindex');
});

test('pageHead refuses what check-seo would fail or never see', () => {
  const ok = PAGES.about;
  assert.throws(() => pageHead({ ...ok, description: 'Too short.' }), /description is 10 characters/);
  assert.throws(() => pageHead({ ...ok, description: 'x'.repeat(161) }), /161 characters/);
  assert.throws(() => pageHead({ ...ok, route: '/about' }), /slash/);
  assert.throws(() => pageHead({ ...ok, route: 'about/' }), /slash/);
  assert.throws(() => pageHead({ ...ok, title: ' ' }), /no title/);
  // article facts on a post and only there
  assert.throws(() => pageHead({ ...POST, article: undefined }), /needs its article facts/);
  assert.throws(() => pageHead({ ...ok, article: POST_ARTICLE }), /blog post only/);
  assert.throws(() => pageHead({ ...PAGES.blog, article: POST_ARTICLE }), /blog post only/);
  assert.throws(() => pageHead({ ...PAGES.home, article: POST_ARTICLE }), /blog post only/);
  assert.throws(() => pageHead({ ...PAGES.notFound, article: POST_ARTICLE }), /blog post only/);
  // the generator is written where Starlight writes it, when it is given
  assert.deepEqual(metas(pageHead({ ...ok, generator: 'Astro v0' }), 'name', 'generator'), ['Astro v0']);
  assert.deepEqual(metas(pageHead(ok), 'name', 'generator'), []);
});

// check-seo's own reading of a built head (attributes(), decode()), to show that the HTML headHtml()
// writes reads back as the entries.
const decode = (s: string) =>
  s.replace(/&quot;/g, '"').replace(/&#39;|&#x27;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
function attributes(tag: string) {
  const out: Record<string, string> = {};
  for (const m of tag.matchAll(/([A-Za-z_:][-A-Za-z0-9_:.]*)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?/g)) {
    if (m.index === 0) continue;
    out[m[1].toLowerCase()] = decode(m[2] ?? m[3] ?? m[4] ?? '');
  }
  return out;
}

test('headHtml writes the entries so that check-seo reads back the same values', () => {
  const head = pageHead(POST);
  const html = headHtml(head);
  const titles = [...html.matchAll(/<title\b[^>]*>([^<]*)<\/title\b[^>]*>/gi)].map((m) => decode(m[1]));
  assert.deepEqual(titles, ['A post & its "title" | Psyche']);
  const read = [...html.matchAll(/<meta\b[^>]*>/gi)].map((m) => attributes(m[0]));
  for (const e of head.filter((x) => x.tag === 'meta')) {
    const a = e.attrs ?? {};
    const k = a.name ? 'name' : a.property ? 'property' : 'charset';
    assert.ok(read.some((r) => r[k] === a[k] && r.content === a.content), `${k}=${String(a[k])} reads back`);
  }
  assert.ok(read.some((r) => r.name === 'description' && r.content === POST.description));
  const scripts = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\b[^>]*>/gi)];
  assert.equal(scripts.length, 1);
  assert.equal(attributes(`<script ${scripts[0][1]}>`).type, 'application/ld+json');
  assert.equal(JSON.parse(scripts[0][2]).headline, POST.title);
  // an apostrophe in a description, as in the page table's, reads back unchanged
  const home = headHtml(pageHead(PAGES.home));
  assert.ok([...home.matchAll(/<meta\b[^>]*>/gi)].map((m) => attributes(m[0])).some((r) => r.name === 'description' && r.content === PAGES.home.description));
  assert.match(home, /^<meta charset="utf-8">\n/);
});
