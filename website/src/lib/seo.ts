/**
 * What every page tells a search engine or a link preview about itself, beyond what Starlight writes.
 * Pure functions with no framework import, so astro.config.mjs, the route middleware (routeData.ts)
 * and `npm test` all use the same code.
 *
 * Starlight already writes the title, the canonical address, og:title, og:description,
 * og:url, og:site_name, og:type (article), twitter:card and the description. What it does not write,
 * and this module adds: og:type "website" on the landing page, twitter:title and twitter:description
 * from the page, noindex on the 404 page, and the landing page's structured data (schema.org JSON-LD).
 * The head entries that are the same on every page (theme colour, icons, manifest, the card's alt
 * text) are in astro.config.mjs.
 */

export const ORIGIN = 'https://cagancaliskan.github.io';
/** The base path of the site, with the trailing slash (astro.config.mjs `base` without it). */
export const BASE = '/psyche/';
export const SITE_URL = ORIGIN + BASE;

/** The project in one sentence, in the words CONTRIBUTING.md gives it: what it is, then its aim, named as an aim. */
export const PROJECT_DESCRIPTION =
  'Psyche is an open research project that builds brain-inspired components in stages, with artificial general intelligence as its long-term aim.';

/** The brand canvas colours (brand/README.md), for the browser's address bar. */
export const THEME_COLOR = { light: '#f5f7fb', dark: '#05070d' } as const;

const PROJECT_ID = `${SITE_URL}#project`;
const WEBSITE_ID = `${SITE_URL}#website`;

export interface HeadEntry {
  tag: string;
  attrs?: Record<string, string | boolean | undefined>;
  content?: string;
}

/**
 * The structured data of the landing page: the site, and the research project it describes. The
 * project is described in the public wording and nothing more: what it is, who started it, where its
 * code is, what it is about. The aim is in the description as an aim; it is not a keyword, because a
 * keyword reads as a property of the work.
 */
export function projectJsonLd(): Record<string, unknown> {
  return {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'WebSite',
        '@id': WEBSITE_ID,
        name: 'Psyche',
        url: SITE_URL,
        description: PROJECT_DESCRIPTION,
        inLanguage: 'en',
        about: { '@id': PROJECT_ID },
      },
      {
        '@type': 'ResearchProject',
        '@id': PROJECT_ID,
        name: 'Psyche',
        url: SITE_URL,
        description: PROJECT_DESCRIPTION,
        founder: {
          '@type': 'Person',
          name: 'Cagan Caliskan',
          sameAs: 'https://github.com/cagancaliskan',
        },
        // The code lives in a public repository; ResearchProject has no codeRepository property.
        sameAs: ['https://github.com/cagancaliskan/psyche'],
        keywords: [
          'brain-inspired components',
          'spiking neural networks',
          'cognitive maps',
          'local synaptic plasticity',
          'memory-and-activation substrate',
          'open research',
        ],
      },
    ],
  };
}

/**
 * JSON for a <script type="application/ld+json"> element. `<` is written as `\u003c`, so no text of the
 * data can close the element or open a comment inside it; the browser's JSON parser reads it back
 * unchanged.
 */
export function jsonLdScript(data: unknown): string {
  return JSON.stringify(data).replace(/</g, '\\u003c');
}

/** The route of a page below the site base: '' for the landing page, '404', 'research/gates'. */
export function routeOf(pathname: string, base: string = BASE): string {
  const root = base.endsWith('/') ? base : `${base}/`;
  const path = pathname.startsWith(root) ? pathname.slice(root.length) : pathname.replace(/^\/+/, '');
  return path.replace(/\/+$/, '').replace(/\/index\.html$/, '');
}

const find = (head: HeadEntry[], key: 'name' | 'property', value: string) =>
  head.find((e) => e.tag === 'meta' && e.attrs?.[key] === value);

const meta = (key: 'name' | 'property', value: string, content: string): HeadEntry => ({
  tag: 'meta',
  attrs: { [key]: value, content },
});

/**
 * The head of one page as Starlight built it, with this module's per-page entries applied. Returns a
 * new array; the entries of the one it was given are not changed.
 */
export function seoHead(head: HeadEntry[], route: string): HeadEntry[] {
  const out: HeadEntry[] = head.map((e) => (e.attrs ? { ...e, attrs: { ...e.attrs } } : { ...e }));

  const type = find(out, 'property', 'og:type');
  if (type?.attrs) type.attrs.content = route === '' ? 'website' : 'article';

  // Twitter reads og:title and og:description when its own are missing; they are written anyway, from
  // the same page values, so a preview never depends on that fallback.
  const title = find(out, 'property', 'og:title')?.attrs?.content;
  const description = find(out, 'property', 'og:description')?.attrs?.content;
  if (typeof title === 'string' && !find(out, 'name', 'twitter:title')) out.push(meta('name', 'twitter:title', title));
  if (typeof description === 'string' && !find(out, 'name', 'twitter:description')) {
    out.push(meta('name', 'twitter:description', description));
  }

  // The 404 page is what the host serves for an address that does not exist; it is not a page to list.
  if (route === '404') out.push(meta('name', 'robots', 'noindex'));

  if (route === '') {
    out.push({ tag: 'script', attrs: { type: 'application/ld+json' }, content: jsonLdScript(projectJsonLd()) });
  }
  return out;
}
