/**
 * The day a page last changed, from the time of the commit that last touched its sources (ISO 8601, as
 * scripts/sitemap-lastmod.mjs reads it from git): the date in UTC and the same date in words. Pure, so
 * `npm test` runs it as it is; src/lib/lastUpdated.ts gives it the commit time while pages are built.
 */
import { formatDay } from './plan.ts';

export interface Day {
  /** YYYY-MM-DD. */
  iso: string;
  /** The same day in words, "5 March 2026". */
  label: string;
}

/** The commit time as a day, or null when there is none or it cannot be read. */
export function commitDay(lastmod: string | undefined): Day | null {
  if (!lastmod) return null;
  const t = Date.parse(lastmod);
  if (Number.isNaN(t)) return null;
  const iso = new Date(t).toISOString().slice(0, 10);
  return { iso, label: formatDay(iso) };
}
