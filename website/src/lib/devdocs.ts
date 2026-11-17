/**
 * The documentation section of the site (/developers/ and the pages in its list): what its navigation,
 * its home's lists, "On this page" and previous / next show, worked out from the documentation list
 * tools/publish/stage.py writes (src/data/docs.json, staged, never tracked). The components under
 * src/components/devdocs write it all into the HTML; the documentation script (src/kit/docs/docs.js)
 * only adds behaviour to that markup.
 *
 * The list's shape (stage.py build_docs_index): { groups: [{ title, items }] }. A document item is
 * { kind: 'doc', slug, title, description }; a page of the site is { kind: 'page', route, title },
 * and its description is the one lib/head.ts PAGES gives that page, so it is written once. Slugs and
 * routes carry no slash at either end and no site base.
 *
 * Pure functions with no framework import and no file read, so `npm test` runs them on fixtures.
 */
import { PAGES, type PageFacts } from './head.ts';
import { REPO_URL } from './seo.ts';

/** The documentation's home, below the base. */
export const DEVELOPERS_ROUTE = 'developers';
/** The opening sentence of the home. */
export const DEVELOPERS_LEAD = 'The documentation, records and source code behind Psyche.';
/** Four more places in the repository, under the home's repository line, in order. "Licence" names no
 *  licence, so the word stays right when the licence changes. */
export const DEVELOPERS_LINKS: readonly { text: string; href: string }[] = [
  { text: 'Discussions', href: `${REPO_URL}/discussions` },
  { text: 'Cite this repository', href: `${REPO_URL}/blob/main/CITATION.cff` },
  { text: 'Licence', href: `${REPO_URL}/blob/main/LICENSE` },
  { text: 'Report a vulnerability', href: `${REPO_URL}/blob/main/SECURITY.md` },
];
/** The home's "Where to start" list, in order: slugs of published documents (docs/publish.json). */
export const START_SLUGS = ['guide', 'research/roadmap', 'research/test-battery'] as const;
/** What the navigation and the home's filter say when no page matches the words typed. */
export const NO_MATCH = 'No page matches these words.';

export interface DocItem {
  kind: 'doc';
  slug: string;
  title: string;
  description: string;
}
export interface SitePageItem {
  kind: 'page';
  route: string;
  title: string;
}
export interface DocsGroup {
  title: string;
  items: (DocItem | SitePageItem)[];
}
/** src/data/docs.json as stage.py writes it. */
export interface DocsData {
  groups: DocsGroup[];
}

/** One page of the list, as the components write it. */
export interface DocsEntry {
  /** The slug of a document, or the route of a page of the site: below the base, no slashes at the ends. */
  route: string;
  /** The site path of its link, for withBase(): the route with its trailing slash. */
  path: string;
  title: string;
  description: string;
  /** The title of the group it is listed in. */
  group: string;
  kind: 'doc' | 'page';
  /** What the filters match: title, description and group, in lower case (data-k-text). */
  text: string;
}

export interface NavGroup {
  title: string;
  items: (DocsEntry & { current: boolean })[];
}

/** The title and description of a page of the site, from lib/head.ts PAGES. Throws on a route it lacks. */
export function pageFacts(route: string): PageFacts {
  const found = Object.values(PAGES).find((p) => p.route === route);
  if (!found) throw new Error(`devdocs: the documentation list names the page /${route}/, which lib/head.ts PAGES does not describe`);
  return found;
}

function routeOf(item: DocItem | SitePageItem): string {
  const route = item.kind === 'doc' ? item.slug : item.route;
  if (!route || /^\/|\/$/.test(route)) throw new Error(`devdocs: "${route}" is not a route without slashes at its ends`);
  return route;
}

/** Every page of the list, in its order (groups in order, items in order), with what the components need. */
export function entriesOf(data: DocsData, describe: (route: string) => PageFacts = pageFacts): DocsEntry[] {
  const out: DocsEntry[] = [];
  const seen = new Set<string>();
  for (const group of data.groups) {
    for (const item of group.items) {
      const route = routeOf(item);
      if (seen.has(route)) throw new Error(`devdocs: /${route}/ is listed twice`);
      seen.add(route);
      const description = item.kind === 'doc' ? item.description : describe(route).description;
      if (!item.title.trim() || !description.trim()) throw new Error(`devdocs: /${route}/ has no title or no description`);
      out.push({
        route,
        path: `${route}/`,
        title: item.title,
        description,
        group: group.title,
        kind: item.kind,
        text: `${item.title} ${description} ${group.title}`.toLowerCase(),
      });
    }
  }
  return out;
}

/** The navigation's groups, the page at `here` (a route, or undefined on the home) marked current. */
export function navGroups(data: DocsData, here?: string, describe?: (route: string) => PageFacts): NavGroup[] {
  const all = entriesOf(data, describe);
  if (here !== undefined && !all.some((e) => e.route === here)) throw new Error(`devdocs: /${here}/ is not in the documentation list`);
  return data.groups
    .map((g) => ({ title: g.title, items: all.filter((e) => e.group === g.title).map((e) => ({ ...e, current: e.route === here })) }))
    .filter((g) => g.items.length > 0);
}

/** Previous and next of the page at `here`: its neighbours in the whole list, site pages included. */
export function neighbours(entries: DocsEntry[], here: string): { prev: DocsEntry | null; next: DocsEntry | null } {
  const i = entries.findIndex((e) => e.route === here);
  if (i < 0) throw new Error(`devdocs: /${here}/ is not in the documentation list`);
  return { prev: entries[i - 1] ?? null, next: entries[i + 1] ?? null };
}

/** The home's "Where to start" list: the START_SLUGS entries, in that order. Throws when one is not listed. */
export function startEntries(entries: DocsEntry[], slugs: readonly string[] = START_SLUGS): DocsEntry[] {
  return slugs.map((slug) => {
    const found = entries.find((e) => e.route === slug && e.kind === 'doc');
    if (!found) throw new Error(`devdocs: the starting page "${slug}" is not a document of the list`);
    return found;
  });
}

/** What the home's count says with nothing typed. */
export function countLabel(n: number): string {
  return n === 1 ? '1 page' : `${n} pages`;
}

/** A heading as Astro's Markdown gives it (render(entry).headings) or as a page lists its own. */
export interface Heading {
  depth: number;
  slug: string;
  text: string;
}

/** "On this page": the h2 and h3 that carry an id, in order; an h3 is a sub-entry. Empty: no list. */
export function tocOf(headings: readonly Heading[]): { href: string; text: string; sub: boolean }[] {
  return headings
    .filter((h) => (h.depth === 2 || h.depth === 3) && h.slug && h.text.trim())
    .map((h) => ({ href: `#${h.slug}`, text: h.text.trim(), sub: h.depth === 3 }));
}

/** The edit link of a document: its Markdown source in the repository (front matter editUrl says the same). */
export function sourceEditUrl(source: string): string {
  if (!source || /^\/|\.\.|^[a-z]+:/i.test(source)) throw new Error(`devdocs: "${source}" is not a path in the repository`);
  return `${REPO_URL}/blob/main/${source}`;
}

/** The edit link of a page of the site: its page file. */
export function pageEditUrl(route: string): string {
  return sourceEditUrl(`website/src/pages/${route}.astro`);
}
