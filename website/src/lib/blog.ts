/**
 * The blog: the pure logic behind its index (pages/blog/index.astro), the strip above a post's title
 * (components/chrome/PageTitle.astro), the landing page's latest posts (components/landing/LatestPosts.astro)
 * and its Atom feed (pages/blog.xml.ts). No framework import, so `npm test` runs it as it is.
 *
 * Nothing here is a list of posts and nothing is typed per post. A post is a folder of docs/blog/ in the
 * repository; tools/publish/stage.py reads each one from the commit being built, checks its front matter
 * and stages it, with its images, as a docs page under blog/<slug>/, and writes the published posts,
 * newest first, to src/data/blog.json. This file reads that list. A draft is never staged, so it is not
 * in the list either.
 *
 * The feed is a serialiser and nothing else, like the progress feed (lib/feed.ts), whose escaping, day
 * stamps and tag URIs it reuses: the same posts give the same bytes on any day and any machine, and every
 * date in it is a post's own day, never the build's.
 */
import { escapeXml, FEED_MEDIA_TYPE, stamp, tagId } from './feed.ts';
import { formatDay } from './plan.ts';

/** One published post, as tools/publish/stage.py writes it to src/data/blog.json. */
export interface BlogPost {
  /** The post's folder under docs/blog/, and the last segment of its address. */
  slug: string;
  /** Its route below the site base: "blog/<slug>/". */
  route: string;
  title: string;
  /** The day it was published, YYYY-MM-DD. */
  date: string;
  /** The day it was last revised, YYYY-MM-DD, or null when it never was. */
  updated: string | null;
  /** One sentence of 120 to 160 characters: its meta description, its link preview and its feed summary. */
  description: string;
  tags: string[];
  author: string;
}

/** src/data/blog.json. */
export interface BlogData {
  /** The first author of CITATION.cff, the feed's author. */
  author: string;
  /** Newest first: by date, then by revision day, then by slug. */
  posts: BlogPost[];
}

/** The blog's index page, below the site base. */
export const BLOG_PAGE = 'blog/';
/** The feed file, below the site base. */
export const BLOG_FEED_FILE = 'blog.xml';
export const BLOG_FEED_TITLE = 'Psyche blog';
export const BLOG_FEED_SUBTITLE = "Posts from Psyche's public blog, newest first.";
/**
 * The day the blog began. It is the feed's `updated` while the blog holds no post (Atom requires one,
 * and the build's clock must not be used), and it is never changed.
 */
export const BLOG_SINCE = '2026-11-04';

/**
 * The tags a post may carry, with the words a reader sees. The same list is tools/publish/blog.py TAGS,
 * which refuses any other tag, and the options of the editor's tag field (public/admin/config.yml);
 * blog.test.ts holds the three equal.
 */
export const TAG_LABELS: Readonly<Record<string, string>> = {
  project: 'Project',
  substrate: 'Substrate',
  'cognitive-maps': 'Cognitive maps',
  methods: 'Methods',
  engineering: 'Engineering',
  reading: 'Reading',
  site: 'Site',
};

/** A tag as a reader sees it: its label, or the tag itself for one the list does not know. */
export function tagLabel(tag: string): string {
  return Object.hasOwn(TAG_LABELS, tag) ? TAG_LABELS[tag] : tag;
}

export interface Day {
  iso: string;
  label: string;
}

const day = (iso: string): Day => ({ iso, label: formatDay(iso) });

/** The posts grouped by the year they were published, newest year first, each year's posts in the order given. */
export function postsByYear(posts: readonly BlogPost[]): { year: string; posts: BlogPost[] }[] {
  const out: { year: string; posts: BlogPost[] }[] = [];
  for (const post of posts) {
    const year = post.date.slice(0, 4);
    const last = out[out.length - 1];
    if (last && last.year === year) last.posts.push(post);
    else out.push({ year, posts: [post] });
  }
  return out;
}

/** The first `count` posts of the list, which is newest first. */
export function latestPosts(posts: readonly BlogPost[], count: number): BlogPost[] {
  return posts.slice(0, Math.max(0, count));
}

/**
 * Whether a route below the base ('blog/opening-the-log') is a post: one segment below blog/. The segment
 * `index` is the index itself, which tools/publish/blog.py never lets a post take.
 */
export function isPostRoute(route: string): boolean {
  const r = route.replace(/\/+$/, '');
  return /^blog\/[a-z0-9]+(?:-[a-z0-9]+)*$/.test(r) && r !== 'blog/index';
}

/** What the strip above a post's title and the line under it say, from the post's own front matter. */
export interface PostMeta {
  published: Day;
  /** The revision day, when there is one and it differs from the day of publication. */
  updated: Day | null;
  author: string;
  tags: { tag: string; label: string }[];
}

export function postMeta(data: { date: string; updated?: string | null; author?: string; tags?: readonly string[] }, fallbackAuthor: string): PostMeta {
  const updated = data.updated && data.updated !== data.date ? day(data.updated) : null;
  return {
    published: day(data.date),
    updated,
    author: data.author || fallbackAuthor,
    tags: (data.tags ?? []).map((tag) => ({ tag, label: tagLabel(tag) })),
  };
}

/** The day a post was last changed: its revision day, or the day it was published. */
export function lastChanged(post: Pick<BlogPost, 'date' | 'updated'>): string {
  return post.updated && post.updated > post.date ? post.updated : post.date;
}

/**
 * The feed's `updated`: the latest day any post was published or revised, or BLOG_SINCE while there is
 * none. Only the posts' own days count, so a post dated before the blog began dates the feed by itself.
 */
export function blogFeedDay(posts: readonly Pick<BlogPost, 'date' | 'updated'>[]): string {
  if (posts.length === 0) return BLOG_SINCE;
  return posts.map(lastChanged).reduce((newest, d) => (d > newest ? d : newest));
}

function leaf(name: string, text: string, indent: string, attrs = ''): string {
  return `${indent}<${name}${attrs}>${escapeXml(text)}</${name}>`;
}

const TEXT = ' type="text"';

/**
 * Atom 1.0 (RFC 4287) for the published posts, in the order given (newest first). Each entry names its
 * post by a tag URI made from its address, so a rebuild never makes an entry look new; `published` is
 * the post's day and `updated` its revision day, both stamped noon UTC as the progress feed's are.
 * `siteUrl` is the site's origin and base with a closing slash, so every address is absolute.
 */
export function blogFeed(data: BlogData, siteUrl: string): string {
  if (!siteUrl.endsWith('/')) throw new Error(`the site address must end in a slash: ${siteUrl}`);
  const at = (path: string) => new URL(path, siteUrl).href;
  const lines: string[] = [
    '<?xml version="1.0" encoding="utf-8"?>',
    '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">',
    leaf('id', tagId(siteUrl, BLOG_FEED_FILE), '  '),
    leaf('title', BLOG_FEED_TITLE, '  ', TEXT),
    leaf('subtitle', BLOG_FEED_SUBTITLE, '  ', TEXT),
    leaf('updated', stamp(blogFeedDay(data.posts)), '  '),
    `  <link rel="self" type="${FEED_MEDIA_TYPE}" href="${escapeXml(at(BLOG_FEED_FILE))}"/>`,
    `  <link rel="alternate" type="text/html" href="${escapeXml(at(BLOG_PAGE))}"/>`,
    `  <author>\n${leaf('name', data.author, '    ')}\n  </author>`,
  ];
  for (const post of data.posts) {
    lines.push(
      '  <entry>',
      leaf('id', tagId(siteUrl, post.route), '    '),
      leaf('title', post.title, '    ', TEXT),
      leaf('published', stamp(post.date), '    '),
      leaf('updated', stamp(lastChanged(post)), '    '),
      `    <link rel="alternate" type="text/html" href="${escapeXml(at(post.route))}"/>`,
    );
    if (post.author !== data.author) lines.push(`    <author>\n${leaf('name', post.author, '      ')}\n    </author>`);
    for (const tag of post.tags) lines.push(`    <category term="${escapeXml(tag)}" label="${escapeXml(tagLabel(tag))}"/>`);
    lines.push(leaf('summary', post.description, '    ', TEXT), '  </entry>');
  }
  lines.push('</feed>', '');
  return lines.join('\n');
}
