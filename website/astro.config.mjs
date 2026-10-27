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

const BASE = '/psyche';
const SITE = ORIGIN + BASE + '/';

// One small inline script for the chrome, run once the page is parsed: the previous / next cards
// carry a light that follows a mouse pointer. Its position is written to --sx-spot-x / --sx-spot-y
// on the card under it, once per frame (global.css draws the light).
const CHROME_SCRIPT = `(()=>{
let frame=0;
const spot=(e)=>{if(e.pointerType==='touch')return;const card=e.target instanceof Element?e.target.closest('.pagination-links a'):null;if(!card)return;cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{const r=card.getBoundingClientRect();card.style.setProperty('--sx-spot-x',e.clientX-r.left+'px');card.style.setProperty('--sx-spot-y',e.clientY-r.top+'px');});};
const start=()=>{document.querySelector('.pagination-links')?.addEventListener('pointermove',spot,{passive:true});};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();`;

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
  },
  integrations: [
    // Registered here so each entry can carry a <lastmod> from git (scripts/sitemap-lastmod.mjs).
    // Starlight adds its own, with no dates, only when none is registered.
    sitemap({ serialize: makeSerialize({ repoRoot: fileURLToPath(new URL('../', import.meta.url)), base: BASE }) }),
    starlight({
      title: 'Psyche',
      // The description of any page that has none of its own (the 404 page): the project in a sentence.
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
      components: { PageTitle: './src/components/docs/PageTitle.astro' },
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
        { tag: 'script', content: CHROME_SCRIPT },
      ],
    }),
    react(),
  ],
});
