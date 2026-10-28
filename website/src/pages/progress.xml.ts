// The Atom feed of the progress page, built to /psyche/progress.xml.
//
// The events are the plan's public events, derived once in Python (tools/publish/render_plan.py
// progress_events) and staged by `npm run stage` as src/data/progress.json; lib/feed.ts only writes
// them as Atom. Every address is absolute, from the `site` of astro.config.mjs and the base path, and
// every date is a day from the plan, so the same plan gives the same file on any day. The feed is an
// endpoint, not a page: it is not in the sitemap, and every page's head points to it
// (astro.config.mjs).
import type { APIRoute } from 'astro';
import progress from '../data/progress.json';
import { atomFeed, FEED_MEDIA_TYPE, type ProgressData } from '../lib/feed.ts';
import { withBase } from '../lib/url.ts';

export const GET: APIRoute = ({ site }) => {
  if (!site) throw new Error('astro.config.mjs sets no `site`, so the feed has no absolute addresses.');
  const siteUrl = new URL(withBase(''), site).href;
  return new Response(atomFeed(progress as ProgressData, siteUrl), {
    headers: { 'Content-Type': `${FEED_MEDIA_TYPE}; charset=utf-8` },
  });
};
