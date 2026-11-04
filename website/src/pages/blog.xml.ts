// The Atom feed of the blog, built to /psyche/blog.xml.
//
// The posts are the published posts of docs/blog/, checked and staged by `npm run stage`
// (tools/publish/stage.py) as src/data/blog.json, newest first; lib/blog.ts only writes them as Atom.
// Every address is absolute, from the `site` of astro.config.mjs and the base path, and every date is a
// post's own day, so the same posts give the same file on any day. The feed is an endpoint, not a page:
// it is not in the sitemap, and every page's head points to it (astro.config.mjs).
import type { APIRoute } from 'astro';
import blog from '../data/blog.json';
import { blogFeed, type BlogData } from '../lib/blog.ts';
import { FEED_MEDIA_TYPE } from '../lib/feed.ts';
import { withBase } from '../lib/url.ts';

export const GET: APIRoute = ({ site }) => {
  if (!site) throw new Error('astro.config.mjs sets no `site`, so the feed has no absolute addresses.');
  const siteUrl = new URL(withBase(''), site).href;
  return new Response(blogFeed(blog as BlogData, siteUrl), {
    headers: { 'Content-Type': `${FEED_MEDIA_TYPE}; charset=utf-8` },
  });
};
