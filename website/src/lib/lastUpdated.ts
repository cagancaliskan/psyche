/**
 * The "Last updated" of a page, at build time: the date of the last commit that touched the files the
 * page is made from, by the helper that dates the sitemap's entries (scripts/sitemap-lastmod.mjs), so
 * the two never disagree. With no usable git history (a shallow clone, no git) there is no date and
 * the footer writes none; the build date is never used.
 *
 * Runs on the server only, while pages are built. The repository root comes from astro.config.mjs
 * (`vite.define`), the same path the sitemap is given.
 */
import { makeLastmod } from '../../scripts/sitemap-lastmod.mjs';
import { footerDate } from './pageChrome.ts';

declare const __REPO_ROOT__: string;

const lastmodOf = makeLastmod({ repoRoot: __REPO_ROOT__ });
const seen = new Map<string, ReturnType<typeof footerDate>>();

/** The footer date of a route ('' for the landing page, 'research/gates', '404'), or null. */
export function lastUpdatedOf(route: string): ReturnType<typeof footerDate> {
  if (!seen.has(route)) seen.set(route, footerDate(lastmodOf(route)));
  return seen.get(route) ?? null;
}
