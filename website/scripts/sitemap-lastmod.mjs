// The <lastmod> of each sitemap entry, from git: the date of the last commit that touched the files a
// page is made from. Used by astro.config.mjs as the `serialize` option of @astrojs/sitemap, and by the
// footer of every page (src/lib/lastUpdated.ts) for its "Last updated", so the two always agree.
//
//   a docs page            its governed source, as docs/publish.json lists it (docs/research/gates.md)
//   a blog post            its folder under docs/blog/, the post and its images (docs/blog/<slug>)
//   the blog's index       its page file and modules, and the folder of every published post, since a
//                          new or revised post changes the list it shows (the landing page's latest posts
//                          too); the authoring guide (docs/blog/README.md) and a draft are not read, so a
//                          change to either moves no date
//   a page of the site     its page file, every component and module it imports whose change can
//                          change what the page says (not stylesheets), and the data the page is drawn
//                          from (tools/research_plan.json for the roadmap, tools/ledger.json for the
//                          status page, both for the landing page), because a moved date or a new test
//                          run changes what the page says without touching the page file
//
// A directory in a list stands for every file under it. scripts/sitemap-lastmod.test.mjs reads the
// imports of each page and fails when one is in no list, so a component added to a page cannot be left
// out of its date.
//
// A date is only written when it is true. With no git, outside a repository, in a shallow clone (every
// file would then carry the date of the one commit that was fetched) or for a file with no history,
// the entry is left as it is, without a <lastmod>: a sitemap with no date is correct, one with a
// wrong date is not. The deploy workflow fetches the full history for this (fetch-depth: 0).
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const SRC = 'website/src';
const PLAN = 'tools/research_plan.json';
const LEDGER = 'tools/ledger.json';
/** The posts' sources: one folder per post (tools/publish/blog.py). */
export const BLOG = 'docs/blog';

/** Pages of the site that are not docs pages, by route below the base ('' is the landing page). */
export const SITE_PAGES = {
  '': [
    `${SRC}/pages/index.astro`,
    `${SRC}/components/LayersHero.astro`,
    `${SRC}/components/NowLine.tsx`,
    `${SRC}/components/Timeline.tsx`,
    `${SRC}/components/TimelineList.astro`,
    `${SRC}/components/battery`,
    `${SRC}/components/brand`,
    `${SRC}/components/landing`,
    `${SRC}/lib/battery.ts`,
    `${SRC}/lib/gateClock.ts`,
    `${SRC}/lib/ledger.ts`,
    `${SRC}/lib/maze.ts`,
    `${SRC}/lib/plan.ts`,
    `${SRC}/lib/today.ts`,
    `${SRC}/lib/seo.ts`,
    `${SRC}/lib/sheet.ts`,
    `${SRC}/lib/url.ts`,
    `${SRC}/lib/blog.ts`,
    `${SRC}/lib/feed.ts`,
    PLAN,
    LEDGER,
    BLOG,
  ],
  roadmap: [
    `${SRC}/pages/roadmap.astro`,
    `${SRC}/components/GateStepper.astro`,
    `${SRC}/components/NowLine.tsx`,
    `${SRC}/components/Timeline.tsx`,
    `${SRC}/components/TimelineList.astro`,
    `${SRC}/components/docs`,
    `${SRC}/lib/gateClock.ts`,
    `${SRC}/lib/plan.ts`,
    `${SRC}/lib/today.ts`,
    `${SRC}/lib/url.ts`,
    PLAN,
  ],
  battery: [
    `${SRC}/pages/battery.astro`,
    `${SRC}/components/BatteryExplorer.tsx`,
    `${SRC}/components/battery`,
    `${SRC}/lib/battery.ts`,
    `${SRC}/lib/maze.ts`,
    `${SRC}/lib/sheet.ts`,
    `${SRC}/lib/url.ts`,
  ],
  status: [
    `${SRC}/pages/status.astro`,
    `${SRC}/components/BrickBoard.astro`,
    `${SRC}/components/BrickTable.astro`,
    `${SRC}/components/landing/SubstrateReadout.astro`,
    `${SRC}/lib/ledger.ts`,
    `${SRC}/lib/plan.ts`,
    `${SRC}/lib/status.ts`,
    `${SRC}/lib/today.ts`,
    `${SRC}/lib/url.ts`,
    LEDGER,
  ],
  blog: [
    `${SRC}/pages/blog/index.astro`,
    `${SRC}/lib/blog.ts`,
    `${SRC}/lib/feed.ts`,
    `${SRC}/lib/plan.ts`,
    `${SRC}/lib/today.ts`,
    `${SRC}/lib/url.ts`,
    BLOG,
  ],
};

/**
 * The folders of the published posts: the posts tools/publish/stage.py staged (src/data/blog.json), or,
 * where nothing is staged yet, every post folder of docs/blog/.
 */
export function publishedPostFolders(repoRoot) {
  const staged = join(repoRoot, 'website/src/data/blog.json');
  if (existsSync(staged)) {
    try {
      const posts = JSON.parse(readFileSync(staged, 'utf8')).posts;
      if (Array.isArray(posts)) return posts.map((p) => `${BLOG}/${p.slug}`);
    } catch {
      // fall through to the folders on disk
    }
  }
  const dir = join(repoRoot, BLOG);
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => `${BLOG}/${e.name}`)
    .sort();
}

/** route -> the repository files the page is made from. */
export function sourcesByRoute(repoRoot) {
  const out = { ...SITE_PAGES };
  // BLOG in a page's list stands for the published posts' folders, not for the whole of docs/blog/.
  const published = publishedPostFolders(repoRoot);
  for (const route of Object.keys(out)) {
    if (out[route].includes(BLOG)) out[route] = out[route].flatMap((f) => (f === BLOG ? published : [f]));
  }
  const manifest = JSON.parse(readFileSync(join(repoRoot, 'docs/publish.json'), 'utf8'));
  for (const section of manifest.sections) {
    for (const page of section.pages) out[page.slug] = [page.src];
  }
  // A post's route is its folder's name. Every folder is listed, drafts too: a draft has no page, so its
  // route is never asked for.
  const posts = join(repoRoot, BLOG);
  if (existsSync(posts)) {
    for (const entry of readdirSync(posts, { withFileTypes: true })) {
      if (entry.isDirectory()) out[`blog/${entry.name}`] = [`${BLOG}/${entry.name}`];
    }
  }
  return out;
}

/** The route of a URL of the sitemap below the site base, or null when it is not below it. */
export function routeOfUrl(url, base) {
  const root = base.endsWith('/') ? base : `${base}/`;
  const { pathname } = new URL(url);
  if (!pathname.startsWith(root)) return null;
  return pathname.slice(root.length).replace(/\/+$/, '');
}

const git = (repoRoot, args) =>
  execFileSync('git', ['-C', repoRoot, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();

/** Whether git can give honest dates here: a work tree with its full history. */
export function historyAvailable(repoRoot) {
  try {
    return git(repoRoot, ['rev-parse', '--is-inside-work-tree']) === 'true' && git(repoRoot, ['rev-parse', '--is-shallow-repository']) === 'false';
  } catch {
    return false;
  }
}

/** The time of the last commit touching any of `files`, as an ISO 8601 string, or undefined. */
export function lastCommit(repoRoot, files) {
  try {
    const seconds = Number(git(repoRoot, ['log', '-1', '--format=%ct', '--', ...files]));
    return Number.isInteger(seconds) && seconds > 0 ? new Date(seconds * 1000).toISOString() : undefined;
  } catch {
    return undefined;
  }
}

/**
 * The date of the last commit that touched the files a route is made from, as an ISO 8601 string, or
 * undefined: the same sources and the same rule as the sitemap's <lastmod>, so the footer of a page and
 * its sitemap entry always give one date. `route` is the route below the base ('' for the landing page).
 * With no usable git history it answers undefined for every route, never the build date.
 */
export function makeLastmod({ repoRoot }) {
  let sources;
  let usable;
  return (route) => {
    usable ??= historyAvailable(repoRoot);
    if (!usable) return undefined;
    sources ??= sourcesByRoute(repoRoot);
    const files = Object.hasOwn(sources, route) ? sources[route] : undefined;
    return files ? lastCommit(repoRoot, files) : undefined;
  };
}

/** The `serialize` function for @astrojs/sitemap. */
export function makeSerialize({ repoRoot, base }) {
  const lastmodOf = makeLastmod({ repoRoot });
  return (item) => {
    const route = routeOfUrl(item.url, base);
    const lastmod = route === null ? undefined : lastmodOf(route);
    return lastmod ? { ...item, lastmod } : item;
  };
}
