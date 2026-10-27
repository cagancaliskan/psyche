// Route data for every Starlight page, the landing and the 404 included.
//
// It adds to each page's head what differs by page, for search engines and link previews
// (lib/seo.ts): og:type, twitter:title and twitter:description from the page, noindex on the 404
// page, and the landing page's structured data. The entries that are the same on every page are in
// astro.config.mjs.
//
// The web fonts are deliberately not preloaded. A preload fetches the two Latin files (81 KB) beside
// the render-blocking stylesheet, and in headless Chrome with the cache off and the network
// throttled that delayed first paint by 80 to 430 ms on the landing page, the battery and the gates
// page, depending on the link, and bought no layout stability that styles/fonts.css does not already
// give: its stand-in faces, sized to the web fonts, take the shift to zero without any preload. If
// field data on the deployed site ever shows a gain, add the two entries to `route.head` here.
import { defineRouteMiddleware } from '@astrojs/starlight/route-data';
import { routeOf, seoHead, type HeadEntry } from './lib/seo.ts';

export const onRequest = defineRouteMiddleware((context) => {
  const route = context.locals.starlightRoute;
  route.head = seoHead(route.head as HeadEntry[], routeOf(context.url.pathname)) as typeof route.head;
});
