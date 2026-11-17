// The site of Psyche, a pre-seed company whose research is open in stages (D-031, D-033, D-037): its front pages and its
// documentation.
//
// Content is never written here by hand. `npm run stage` (tools/publish/stage.py) copies the
// governed Markdown listed in docs/publish.json into src/content/docs/ and writes the data files
// in src/data/ (plan, public ledger projection, documentation list). Both locations are gitignored, and CI
// fails if a staged copy is ever tracked, so the governed sources stay the only source.
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';
import { BASE, ORIGIN } from './src/lib/seo.ts';
import { makeSerialize } from './scripts/sitemap-lastmod.mjs';
import { postFiguresIntegration } from './scripts/post-figures.mjs';
import { tableRegionIntegration } from './scripts/table-region.mjs';

const REPO_ROOT = fileURLToPath(new URL('../', import.meta.url));

export default defineConfig({
  site: ORIGIN,
  base: BASE,
  trailingSlash: 'always',
  // Code in documents and posts is drawn in one ink, by the kit's rules for <pre>: no syntax colour.
  // The documents' and posts' links to the site's own pages and ids are checked in the built pages by
  // scripts/check-seo.mjs and scripts/check-refs.mjs.
  markdown: { syntaxHighlight: false },
  // Every link to a page of the site is fetched ahead when the reader points at it or focuses it,
  // as the site has always done (Astro's prefetch script, on every page).
  prefetch: { prefetchAll: true },
  vite: {
    build: { sourcemap: false },
    // The repository root, for the documentation's "Last updated" (src/lib/lastUpdated.ts): the path the
    // sitemap's dates are read from.
    define: { __REPO_ROOT__: JSON.stringify(REPO_ROOT) },
  },
  integrations: [
    // Puts every table of a Markdown page in a named, keyboard-reachable scroll region (WCAG 2.1.1);
    // the Satteri counterpart of a rehype plugin (scripts/table-region.mjs).
    tableRegionIntegration(),
    // Lays a post that has a page design of its own out in the design's reading columns, with its
    // figures between them (src/kit/posts/<slug>/figures.json); its words stay the Markdown's
    // (scripts/post-figures.mjs). Placed after the table step, before the processor's heading ids.
    postFiguresIntegration(),
    // Each entry carries a <lastmod> from git (scripts/sitemap-lastmod.mjs).
    sitemap({ serialize: makeSerialize({ repoRoot: REPO_ROOT, base: BASE }) }),
    react(),
  ],
});
