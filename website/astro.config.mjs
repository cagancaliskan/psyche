// Docs site for Psyche, one open research project in stages (D-031, D-033).
//
// Content is never written here by hand. `npm run stage` (tools/publish/stage.py) copies the
// governed Markdown listed in docs/publish.json into src/content/docs/ and writes the data files
// in src/data/ (plan, public ledger projection, sidebar). Both locations are gitignored, and CI
// fails if a staged copy is ever tracked, so the governed sources stay the only source.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';
import starlightLinksValidator from 'starlight-links-validator';
import { ORIGIN, PROJECT_DESCRIPTION, THEME_COLOR } from './src/lib/seo.ts';
import { makeSerialize } from './scripts/sitemap-lastmod.mjs';
import { tableRegionIntegration } from './scripts/table-region.mjs';

const BASE = '/psyche';
const SITE = ORIGIN + BASE + '/';
const REPO_ROOT = fileURLToPath(new URL('../', import.meta.url));

// What the social card says, for people who cannot see it. The card is drawn by scripts/make-og.mjs,
// which writes this description of itself beside the image (brand/psyche-social.json), so the alt
// text names the stage the card actually shows.
function socialCardAlt() {
  const url = new URL('../brand/psyche-social.json', import.meta.url);
  try {
    const { alt } = JSON.parse(readFileSync(url, 'utf8'));
    if (typeof alt === 'string' && alt) return alt;
  } catch {
    // fall through to the error below
  }
  throw new Error('brand/psyche-social.json is missing or has no alt text: run `npm run og` in website/.');
}

function stagedSidebar() {
  const url = new URL('./src/data/sidebar.json', import.meta.url);
  try {
    return JSON.parse(readFileSync(url, 'utf8'));
  } catch {
    throw new Error('src/data/sidebar.json is missing: run `npm run stage` first.');
  }
}

export default defineConfig({
  site: ORIGIN,
  base: BASE,
  trailingSlash: 'always',
  vite: {
    build: { sourcemap: false },
    // The repository root, for the footer's "Last updated" (src/lib/lastUpdated.ts): the path the
    // sitemap's dates are read from.
    define: { __REPO_ROOT__: JSON.stringify(REPO_ROOT) },
  },
  integrations: [
    // Puts every table of a Markdown page in a named, keyboard-reachable scroll region (WCAG 2.1.1);
    // the Satteri counterpart of a rehype plugin (scripts/table-region.mjs).
    tableRegionIntegration(),
    // Registered here so each entry can carry a <lastmod> from git (scripts/sitemap-lastmod.mjs).
    // Starlight adds its own, with no dates, only when none is registered.
    sitemap({ serialize: makeSerialize({ repoRoot: REPO_ROOT, base: BASE }) }),
    starlight({
      title: 'Psyche',
      // The description of any page that sets none of its own: the project in a sentence.
      description: PROJECT_DESCRIPTION,
      logo: { light: './src/assets/brand/psyche-wordmark-light.svg', dark: './src/assets/brand/psyche-wordmark-dark.svg', replacesTitle: true },
      favicon: '/favicon.svg',
      social: [{ icon: 'github', label: 'Psyche on GitHub', href: 'https://github.com/cagancaliskan/psyche' }],
      // global.css comes first: its @layer statement must be the first one the cascade sees.
      customCss: [
        './src/styles/global.css',
        './src/styles/fonts.css',
        '@fontsource-variable/unbounded',
        '@fontsource-variable/instrument-sans',
        '@fontsource-variable/instrument-sans/wght-italic.css',
        '@fontsource-variable/martian-mono',
        './src/styles/docs.css',
      ],
      // PageTitle: a ruled strip above the title: the stage and its section (or the sidebar's group) and, on
      // stage 1 and stage 2 pages, the stage's state.
      // Footer: Starlight's (edit link, previous and next) with a title block below: the sheet, its stage,
      // the next gate, the project's links and the page's date.
      // Search: Starlight's, with the key cap drawn rather than written, so the button's name holds the
      // text drawn on it (WCAG 2.5.3); src/lib/searchOverride.test.ts keeps it in step with Starlight's.
      components: {
        PageTitle: './src/components/chrome/PageTitle.astro',
        Footer: './src/components/chrome/Footer.astro',
        Search: './src/components/chrome/Search.astro',
      },
      // The 404 page is src/pages/404.astro, a StarlightPage set as a drafting sheet.
      disable404Route: true,
      routeMiddleware: './src/routeData.ts',
      sidebar: stagedSidebar(),
      lastUpdated: false,
      pagination: true,
      plugins: [starlightLinksValidator({ errorOnRelativeLinks: false })],
      // The same on every page. What differs by page (og:type, twitter:title and twitter:description,
      // noindex on the 404 page, the landing page's structured data) is added by src/routeData.ts.
      // Starlight writes the favicon link, <link rel="shortcut icon"> to favicon.svg, after these, so
      // the SVG stays the primary icon and the PNGs are fallbacks.
      head: [
        { tag: 'meta', attrs: { name: 'color-scheme', content: 'light dark' } },
        { tag: 'meta', attrs: { name: 'theme-color', content: THEME_COLOR.light, media: '(prefers-color-scheme: light)' } },
        { tag: 'meta', attrs: { name: 'theme-color', content: THEME_COLOR.dark, media: '(prefers-color-scheme: dark)' } },
        { tag: 'link', attrs: { rel: 'icon', type: 'image/png', sizes: '32x32', href: `${BASE}/favicon-32.png` } },
        { tag: 'link', attrs: { rel: 'apple-touch-icon', sizes: '180x180', href: `${BASE}/apple-touch-icon.png` } },
        { tag: 'link', attrs: { rel: 'manifest', href: `${BASE}/site.webmanifest` } },
        { tag: 'meta', attrs: { property: 'og:image', content: `${SITE}og.png` } },
        { tag: 'meta', attrs: { property: 'og:image:type', content: 'image/png' } },
        { tag: 'meta', attrs: { property: 'og:image:width', content: '1200' } },
        { tag: 'meta', attrs: { property: 'og:image:height', content: '630' } },
        { tag: 'meta', attrs: { property: 'og:image:alt', content: socialCardAlt() } },
        { tag: 'meta', attrs: { name: 'twitter:card', content: 'summary_large_image' } },
        { tag: 'meta', attrs: { name: 'twitter:image', content: `${SITE}og.png` } },
        { tag: 'meta', attrs: { name: 'twitter:image:alt', content: socialCardAlt() } },
      ],
    }),
    react(),
  ],
});
