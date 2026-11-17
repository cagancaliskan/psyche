/**
 * The <head> of the pages that are not Starlight pages: the home page, What we're building, Experiments,
 * About, the blog's index, the blog's posts, the documentation's home (/developers/), the timeline, the
 * walk-through and the status page, and the 404 page. Starlight writes the head of every docs page
 * itself (with astro.config.mjs `head` and src/routeData.ts); these pages have no Starlight, so this
 * module writes the same entries: the ones Starlight wrote (title, canonical, sitemap link, SVG icon,
 * og:* and description), the ones astro.config.mjs gives every docs page (theme colour, icons, manifest,
 * the two feeds, the social card), then lib/seo.ts seoHead() for what differs by page (og:type,
 * twitter:title and twitter:description, noindex on the 404 page, the structured data, a post's article
 * tags). scripts/check-seo.mjs reads the built pages and holds them to exactly these rules.
 *
 * The values come from the modules that already define them (seo.ts, feed.ts, blog.ts, the social card's
 * own description in brand/psyche-social.json); nothing here restates one. Pure functions with no
 * framework import, so `npm test` runs it as it is.
 */
import social from '../../../brand/psyche-social.json' with { type: 'json' };
import { BLOG_FEED_FILE, BLOG_FEED_TITLE, isPostRoute } from './blog.ts';
import { FEED_FILE, FEED_MEDIA_TYPE, FEED_TITLE } from './feed.ts';
import { BASE, NOT_FOUND, ORIGIN, SITE_URL, THEME_COLOR, seoHead, type ArticleFacts, type HeadEntry } from './seo.ts';

/** The site's name: og:site_name, and the end of every title but the home page's. */
export const SITE_NAME = 'Psyche';
/** What follows a page's own name in its <title> (scripts/check-seo.mjs TITLE_SUFFIX). */
export const TITLE_SUFFIX = ` | ${SITE_NAME}`;
/** The length a description must have (scripts/check-seo.mjs DESCRIPTION). */
export const DESCRIPTION_LENGTH = { min: 120, max: 160 } as const;

/** One page's name and description, as its head and its link preview give them. */
export interface PageFacts {
  /** The route below the base: '' for the home page, '404', 'about'. */
  route: string;
  title: string;
  /** 120 to 160 characters, different on every page. */
  description: string;
}

/**
 * The name and description of each page that is not a document and not a post (a document's come from
 * docs/publish.json and its first heading, a post's from its front matter). The descriptions are made
 * only of sentences the project lead chose for these pages; a page takes its entry from here, so no page
 * types its own. The 404 page's are lib/seo.ts NOT_FOUND, which check-seo compares the built page with.
 */
export const PAGES = {
  home: {
    route: '',
    // The home page's title is written whole, without the site name after it.
    title: 'Psyche: New era of intelligence',
    description:
      "Psyche is building machines on the brain's own principles: neurons that spike, connections that teach themselves. Toward machines with a mind of their own.",
  },
  whatWereBuilding: {
    route: 'what-were-building',
    title: "What we're building",
    description:
      "We're building machines the way nature built minds: neurons that spike, connections that teach themselves, networks that draw their own map of the world.",
  },
  experiments: {
    route: 'experiments',
    title: 'The five experiments',
    description:
      'Memorising answers gets you far. These five experiments show where it stops and something else takes over. Animals do all five.',
  },
  about: {
    route: 'about',
    title: 'About and contact',
    description:
      'The other way to build intelligence. Three kinds of people will build it with us: investors, engineers and research partners.',
  },
  blog: {
    route: 'blog',
    title: 'Blog',
    description:
      "Notes from the road to machine cognition. Psyche is building machines on the brain's own principles: neurons that spike, connections that teach themselves.",
  },
  developers: {
    route: 'developers',
    title: 'For developers',
    description:
      "The documentation, records and source code behind Psyche: the reader's guide, the roadmap and its gates, the test battery and the rules for claims.",
  },
  // The three pages of the documentation list that are pages of the site, not documents: the list
  // (lib/devdocs.ts) shows their title and description from here.
  roadmap: {
    route: 'roadmap',
    title: 'Explore the timeline',
    description:
      'The phases and decision gates of stage 2 of Psyche on one timeline, read from the research plan: where today falls and the date of each gate that has one.',
  },
  battery: {
    route: 'battery',
    title: 'Step through the paradigms',
    description:
      'Step through the classic cognitive-map paradigms behind the stage 2 test battery: what the agent does, what changes after learning and what each test measures.',
  },
  status: {
    route: 'status',
    title: 'Substrate status',
    description:
      'The substrate, stage 1 of Psyche: its captured test run, the build status of each brick, what its tests show, and where its development stands.',
  },
  notFound: { route: NOT_FOUND.route, title: NOT_FOUND.title, description: NOT_FOUND.description },
} as const satisfies Record<string, PageFacts>;

export interface PageHeadInput extends PageFacts {
  /** A blog post's days, author and tags (articleFacts); given on a post and on no other page. */
  article?: ArticleFacts;
  /** Astro.generator, written where Starlight writes it. */
  generator?: string;
}

/** The address of a route below the base, with its trailing slash: what canonical and og:url say. */
export function canonicalOf(route: string): string {
  return new URL(route ? `${BASE}${route}/` : BASE, ORIGIN).href;
}

/** The <title> text: the home page's title as it is, every other page's followed by the site name. */
export function titleOf(route: string, title: string): string {
  return route === '' ? title : `${title}${TITLE_SUFFIX}`;
}

/**
 * A post's article facts from its front matter, the author falling back to the blog's (src/data/blog.json
 * `author`), as src/routeData.ts does for the Starlight posts.
 */
export function articleFacts(
  data: { date: string; updated?: string | null; author?: string; tags?: readonly string[] },
  fallbackAuthor: string,
): ArticleFacts {
  return { published: data.date, modified: data.updated ?? null, author: data.author || fallbackAuthor, tags: data.tags ?? [] };
}

/**
 * Every head entry of one page, in the order Starlight writes them. Throws, so the build stops, on what
 * check-seo would fail later or not see at all: a description out of length, a route with a slash at
 * either end, a post without its article facts, or article facts on a page that is not a post.
 */
export function pageHead({ route, title, description, article, generator }: PageHeadInput): HeadEntry[] {
  const where = route === '' ? '/' : `/${route}/`;
  if (/^\/|\/$/.test(route)) throw new Error(`pageHead: the route "${route}" has a slash at its start or end`);
  if (!title.trim()) throw new Error(`pageHead ${where}: no title`);
  if (description.length < DESCRIPTION_LENGTH.min || description.length > DESCRIPTION_LENGTH.max) {
    throw new Error(`pageHead ${where}: the description is ${description.length} characters, not ${DESCRIPTION_LENGTH.min} to ${DESCRIPTION_LENGTH.max}`);
  }
  if (isPostRoute(route) && !article) throw new Error(`pageHead ${where}: a blog post needs its article facts`);
  if (!isPostRoute(route) && article) throw new Error(`pageHead ${where}: article facts belong on a blog post only`);

  const canonical = canonicalOf(route);
  const image = `${SITE_URL}og.png`;
  const meta = (key: 'name' | 'property', value: string, content: string): HeadEntry => ({ tag: 'meta', attrs: { [key]: value, content } });
  const head: HeadEntry[] = [
    { tag: 'meta', attrs: { charset: 'utf-8' } },
    meta('name', 'viewport', 'width=device-width, initial-scale=1'),
    { tag: 'title', content: titleOf(route, title) },
    { tag: 'link', attrs: { rel: 'canonical', href: canonical } },
    { tag: 'link', attrs: { rel: 'sitemap', href: `${BASE}sitemap-index.xml` } },
    { tag: 'link', attrs: { rel: 'icon', type: 'image/png', sizes: '32x32', href: `${BASE}favicon-32.png` } },
    { tag: 'link', attrs: { rel: 'apple-touch-icon', sizes: '180x180', href: `${BASE}apple-touch-icon.png` } },
    { tag: 'link', attrs: { rel: 'manifest', href: `${BASE}site.webmanifest` } },
    { tag: 'link', attrs: { rel: 'alternate', type: FEED_MEDIA_TYPE, title: FEED_TITLE, href: `${BASE}${FEED_FILE}` } },
    { tag: 'link', attrs: { rel: 'alternate', type: FEED_MEDIA_TYPE, title: BLOG_FEED_TITLE, href: `${BASE}${BLOG_FEED_FILE}` } },
    { tag: 'link', attrs: { rel: 'shortcut icon', href: `${BASE}favicon.svg`, type: 'image/svg+xml' } },
    ...(generator ? [meta('name', 'generator', generator)] : []),
    meta('property', 'og:title', title),
    // seoHead() sets it: "website" on the home page, "article" on every other.
    meta('property', 'og:type', 'article'),
    meta('property', 'og:url', canonical),
    meta('property', 'og:locale', 'en'),
    meta('property', 'og:description', description),
    meta('property', 'og:site_name', SITE_NAME),
    meta('name', 'description', description),
    meta('name', 'color-scheme', 'light dark'),
    { tag: 'meta', attrs: { name: 'theme-color', content: THEME_COLOR.light, media: '(prefers-color-scheme: light)' } },
    { tag: 'meta', attrs: { name: 'theme-color', content: THEME_COLOR.dark, media: '(prefers-color-scheme: dark)' } },
    meta('property', 'og:image', image),
    meta('property', 'og:image:type', 'image/png'),
    meta('property', 'og:image:width', String(social.width)),
    meta('property', 'og:image:height', String(social.height)),
    meta('property', 'og:image:alt', social.alt),
    meta('name', 'twitter:card', 'summary_large_image'),
    meta('name', 'twitter:image', image),
    meta('name', 'twitter:image:alt', social.alt),
  ];
  return seoHead(head, route, article);
}

const escapeText = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const escapeAttr = (s: string) => escapeText(s).replace(/"/g, '&quot;');

/**
 * The entries as HTML, one element a line, for a layout to write with `<Fragment set:html={...} />`.
 * Text and attribute values are escaped (`&`, `<`, `>`, and `"` in an attribute), so a title with an
 * ampersand stays text; a script's content is written as it is, which is safe for the JSON-LD because
 * lib/seo.ts jsonLdScript() never writes a `<`.
 */
export function headHtml(entries: readonly HeadEntry[]): string {
  return entries
    .map(({ tag, attrs = {}, content }) => {
      const a = Object.entries(attrs)
        .filter(([, v]) => v !== undefined && v !== false)
        .map(([k, v]) => (v === true ? ` ${k}` : ` ${k}="${escapeAttr(String(v))}"`))
        .join('');
      if (tag === 'meta' || tag === 'link') return `<${tag}${a}>`;
      const body = content === undefined ? '' : tag === 'script' ? content : escapeText(content);
      return `<${tag}${a}>${body}</${tag}>`;
    })
    .join('\n');
}
