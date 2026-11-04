import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  BLOG_FEED_FILE,
  BLOG_SINCE,
  TAG_LABELS,
  blogFeed,
  blogFeedDay,
  isPostRoute,
  lastChanged,
  latestPosts,
  postMeta,
  postsByYear,
  tagLabel,
  type BlogData,
  type BlogPost,
} from './blog.ts';

const SITE = 'https://example.invalid/psyche/';

const post = (slug: string, date: string, extra: Partial<BlogPost> = {}): BlogPost => ({
  slug,
  route: `blog/${slug}/`,
  title: `Post ${slug}`,
  date,
  updated: null,
  description: `The description of ${slug}.`,
  tags: [],
  author: 'Cagan Caliskan',
  ...extra,
});

const DATA: BlogData = {
  author: 'Cagan Caliskan',
  posts: [
    post('third', '2027-01-04', { tags: ['methods', 'site'] }),
    post('second', '2026-12-20', { updated: '2027-01-10' }),
    post('first', '2026-11-04', { author: 'A Guest', title: 'Fish & <chips>' }),
  ],
};

test('the tags are one list: the labels here, tools/publish/blog.py TAGS and the editor options', () => {
  const python = readFileSync(new URL('../../../tools/publish/blog.py', import.meta.url), 'utf8');
  const m = python.match(/^TAGS\b[^=\n]*=\s*[([]([\s\S]*?)[)\]]/m);
  assert.ok(m, 'tools/publish/blog.py has no TAGS list');
  const fromPython = [...m[1].matchAll(/["']([^"']+)["']/g)].map((x) => x[1]);
  assert.deepEqual([...fromPython].sort(), Object.keys(TAG_LABELS).sort());

  const config = readFileSync(new URL('../../public/admin/config.yml', import.meta.url), 'utf8');
  const field = config.match(/- name: tags\n(?:[ \t]+.*\n)*?[ \t]+options:\s*\[([^\]]*)\]/);
  assert.ok(field, 'public/admin/config.yml has no options list for the tags field');
  const fromEditor = field[1].split(',').map((t) => t.trim().replace(/^["']|["']$/g, ''));
  assert.deepEqual([...fromEditor].sort(), Object.keys(TAG_LABELS).sort());
  // and the editor's tag filters name the same tags
  const filters = [...config.matchAll(/field: tags, pattern: ([a-z-]+)/g)].map((x) => x[1]);
  assert.deepEqual([...filters].sort(), Object.keys(TAG_LABELS).sort());
});

test('a tag reads as its label, and an unknown tag as itself', () => {
  assert.equal(tagLabel('cognitive-maps'), 'Cognitive maps');
  assert.equal(tagLabel('elsewhere'), 'elsewhere');
  assert.equal(tagLabel('constructor'), 'constructor');
});

test('posts are grouped by year, newest year first, in the order given', () => {
  const years = postsByYear(DATA.posts);
  assert.deepEqual(
    years.map((y) => [y.year, y.posts.map((p) => p.slug)]),
    [
      ['2027', ['third']],
      ['2026', ['second', 'first']],
    ],
  );
  assert.deepEqual(postsByYear([]), []);
});

test('the latest posts are the first ones of the list', () => {
  assert.deepEqual(latestPosts(DATA.posts, 2).map((p) => p.slug), ['third', 'second']);
  assert.deepEqual(latestPosts(DATA.posts, 0), []);
  assert.deepEqual(latestPosts(DATA.posts, -1), []);
  assert.equal(latestPosts(DATA.posts, 9).length, 3);
});

test('a post route is one segment below blog/, and the index is not a post', () => {
  assert.equal(isPostRoute('blog/opening-the-log'), true);
  assert.equal(isPostRoute('blog/opening-the-log/'), true);
  assert.equal(isPostRoute('blog'), false);
  assert.equal(isPostRoute('blog/'), false);
  assert.equal(isPostRoute('blog/a/b'), false);
  assert.equal(isPostRoute('research/gates'), false);
  assert.equal(isPostRoute('blog/Upper'), false);
  assert.equal(isPostRoute('blog/index'), false);
});

test("a post's meta: its days in words, its author or the fallback, its tags as labels", () => {
  const m = postMeta({ date: '2026-11-04', updated: '2026-11-05', tags: ['methods'] }, 'Fallback');
  assert.deepEqual(m.published, { iso: '2026-11-04', label: '4 November 2026' });
  assert.deepEqual(m.updated, { iso: '2026-11-05', label: '5 November 2026' });
  assert.equal(m.author, 'Fallback');
  assert.deepEqual(m.tags, [{ tag: 'methods', label: 'Methods' }]);
  // a revision on the day of publication is no revision
  assert.equal(postMeta({ date: '2026-11-04', updated: '2026-11-04' }, 'x').updated, null);
  assert.equal(postMeta({ date: '2026-11-04', author: 'A Guest' }, 'x').author, 'A Guest');
});

test("the feed is dated by its posts' days, and by BLOG_SINCE while there is none", () => {
  assert.equal(lastChanged(DATA.posts[1]), '2027-01-10');
  assert.equal(lastChanged(DATA.posts[0]), '2027-01-04');
  assert.equal(blogFeedDay(DATA.posts), '2027-01-10');
  assert.equal(blogFeedDay([]), BLOG_SINCE);
  // a post dated before the blog began dates the feed by its own day, not by BLOG_SINCE
  assert.equal(blogFeedDay([post('old', '2026-01-02')]), '2026-01-02');
});

test('the blog feed is Atom with one entry per post, newest first, and escapes what it is given', () => {
  const xml = blogFeed(DATA, SITE);
  assert.ok(xml.startsWith('<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">'));
  assert.ok(xml.includes(`<link rel="self" type="application/atom+xml" href="${SITE}${BLOG_FEED_FILE}"/>`));
  assert.ok(xml.includes(`<link rel="alternate" type="text/html" href="${SITE}blog/"/>`));
  assert.ok(xml.includes('<updated>2027-01-10T12:00:00Z</updated>'));
  const entries = [...xml.matchAll(/<entry>([\s\S]*?)<\/entry>/g)].map((m) => m[1]);
  assert.equal(entries.length, 3);
  assert.ok(entries[0].includes('<id>tag:example.invalid,2026:psyche/blog/third/</id>'));
  assert.ok(entries[0].includes('<category term="methods" label="Methods"/>'));
  assert.ok(entries[1].includes('<published>2026-12-20T12:00:00Z</published>'));
  assert.ok(entries[1].includes('<updated>2027-01-10T12:00:00Z</updated>'));
  assert.ok(entries[2].includes('<title type="text">Fish &amp; &lt;chips&gt;</title>'));
  // an author of its own only where it differs from the feed's
  assert.ok(entries[2].includes('<name>A Guest</name>'));
  assert.ok(!entries[0].includes('<author>'));
  assert.ok(entries[0].includes(`<link rel="alternate" type="text/html" href="${SITE}blog/third/"/>`));
  // the same posts give the same bytes
  assert.equal(blogFeed(DATA, SITE), xml);
});

test('an empty blog still gives a valid feed, dated the day the blog began', () => {
  const xml = blogFeed({ author: 'Cagan Caliskan', posts: [] }, SITE);
  assert.ok(xml.includes(`<updated>${BLOG_SINCE}T12:00:00Z</updated>`));
  assert.ok(!xml.includes('<entry>'));
  assert.throws(() => blogFeed(DATA, 'https://example.invalid/psyche'), /slash/);
});
