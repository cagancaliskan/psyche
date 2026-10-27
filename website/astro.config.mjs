// Docs site for Psyche, one open research project in stages (D-031, D-033).
//
// Content is never written here by hand. `npm run stage` (tools/publish/stage.py) copies the
// governed Markdown listed in docs/publish.json into src/content/docs/ and writes the data files
// in src/data/ (plan, public ledger projection, sidebar). Both locations are gitignored, and CI
// fails if a staged copy is ever tracked, so the governed sources stay the only source.
import { readFileSync } from 'node:fs';
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import react from '@astrojs/react';
import starlightLinksValidator from 'starlight-links-validator';
import tailwindcss from '@tailwindcss/vite';

const BASE = '/psyche';

// One small inline script for the chrome, run once the page is parsed: the previous / next cards
// carry a light that follows a mouse pointer. Its position is written to --sx-spot-x / --sx-spot-y
// on the card under it, once per frame (global.css draws the light).
const CHROME_SCRIPT = `(()=>{
let frame=0;
const spot=(e)=>{if(e.pointerType==='touch')return;const card=e.target instanceof Element?e.target.closest('.pagination-links a'):null;if(!card)return;cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{const r=card.getBoundingClientRect();card.style.setProperty('--sx-spot-x',e.clientX-r.left+'px');card.style.setProperty('--sx-spot-y',e.clientY-r.top+'px');});};
const start=()=>{document.querySelector('.pagination-links')?.addEventListener('pointermove',spot,{passive:true});};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();`;

function stagedSidebar() {
  const url = new URL('./src/data/sidebar.json', import.meta.url);
  try {
    return JSON.parse(readFileSync(url, 'utf8'));
  } catch {
    throw new Error('src/data/sidebar.json is missing: run `npm run stage` first.');
  }
}

export default defineConfig({
  site: 'https://cagancaliskan.github.io',
  base: BASE,
  trailingSlash: 'always',
  vite: {
    build: { sourcemap: false },
    plugins: [tailwindcss()],
  },
  integrations: [
    starlight({
      title: 'Psyche',
      description:
        'Psyche is an open research project that builds and tests brain-inspired components in stages: spiking cognitive maps (active) and the substrate that founded it (paused). Its long-term aim is AGI.',
      logo: { light: './src/assets/brand/psyche-wordmark-light.svg', dark: './src/assets/brand/psyche-wordmark-dark.svg', replacesTitle: true },
      favicon: '/favicon.svg',
      social: [{ icon: 'github', label: 'Psyche on GitHub', href: 'https://github.com/cagancaliskan/psyche' }],
      // global.css comes first: its @layer statement must be the first one the cascade sees.
      customCss: [
        './src/styles/global.css',
        '@fontsource-variable/unbounded',
        '@fontsource-variable/instrument-sans',
        '@fontsource-variable/instrument-sans/standard-italic.css',
        '@fontsource-variable/martian-mono',
        './src/styles/docs.css',
      ],
      components: { PageTitle: './src/components/docs/PageTitle.astro' },
      sidebar: stagedSidebar(),
      lastUpdated: false,
      pagination: true,
      plugins: [starlightLinksValidator({ errorOnRelativeLinks: false })],
      head: [
        { tag: 'meta', attrs: { name: 'color-scheme', content: 'light dark' } },
        { tag: 'meta', attrs: { property: 'og:image', content: 'https://cagancaliskan.github.io/psyche/og.png' } },
        { tag: 'meta', attrs: { property: 'og:image:width', content: '1200' } },
        { tag: 'meta', attrs: { property: 'og:image:height', content: '630' } },
        { tag: 'meta', attrs: { name: 'twitter:card', content: 'summary_large_image' } },
        { tag: 'meta', attrs: { name: 'twitter:image', content: 'https://cagancaliskan.github.io/psyche/og.png' } },
        { tag: 'script', content: CHROME_SCRIPT },
      ],
    }),
    react(),
  ],
});
