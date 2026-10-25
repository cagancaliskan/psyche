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
import mermaid from 'astro-mermaid';
import starlightLinksValidator from 'starlight-links-validator';
import tailwindcss from '@tailwindcss/vite';

const BASE = '/psyche';

const MERMAID_FONT = "'Instrument Sans Variable', system-ui, sans-serif";

// One small inline script for the chrome, run once the page is parsed.
// - Mermaid copies each classDef's fill, stroke and text colour onto the shapes as inline
//   !important styles, which no stylesheet can override. Removing those three properties after
//   each render lets the token theme in docs.css apply; dash patterns and widths stay.
// - The previous / next cards carry a light that follows a mouse pointer: its position is written
//   to --sx-spot-x / --sx-spot-y on the card under it, once per frame (global.css draws the light).
const CHROME_SCRIPT = `(()=>{
const strip=(root)=>root.querySelectorAll('svg :is(.node,.cluster)[style],svg :is(.node,.cluster) [style]').forEach((el)=>{for(const p of ['fill','stroke','color'])el.style.removeProperty(p);});
let frame=0;
const spot=(e)=>{if(e.pointerType==='touch')return;const card=e.target instanceof Element?e.target.closest('.pagination-links a'):null;if(!card)return;cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{const r=card.getBoundingClientRect();card.style.setProperty('--sx-spot-x',e.clientX-r.left+'px');card.style.setProperty('--sx-spot-y',e.clientY-r.top+'px');});};
const start=()=>{document.querySelectorAll('pre.mermaid').forEach((pre)=>{strip(pre);new MutationObserver(()=>strip(pre)).observe(pre,{childList:true});});document.querySelector('.pagination-links')?.addEventListener('pointermove',spot,{passive:true});};
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
    // Mermaid on the site's tokens. `base` is the only Mermaid theme that takes themeVariables; the
    // values below are the dark tokens, and src/styles/docs.css recolours every rendered diagram
    // from the live tokens in both themes. autoTheme stays off: it swaps to Mermaid's built-in
    // 'default' and 'dark' themes, which ignore themeVariables.
    mermaid({
      theme: 'base',
      autoTheme: false,
      enableLog: false,
      mermaidConfig: {
        fontFamily: MERMAID_FONT,
        themeVariables: {
          darkMode: true,
          fontFamily: MERMAID_FONT,
          fontSize: '14px',
          background: '#0b0f18',
          mainBkg: '#0b0f18',
          primaryColor: '#0b0f18',
          primaryBorderColor: '#4a5888',
          primaryTextColor: '#f4f6fb',
          secondaryColor: '#111726',
          secondaryBorderColor: '#1c2333',
          secondaryTextColor: '#f4f6fb',
          tertiaryColor: '#111726',
          tertiaryBorderColor: '#1c2333',
          tertiaryTextColor: '#f4f6fb',
          nodeBorder: '#4a5888',
          textColor: '#f4f6fb',
          titleColor: '#f4f6fb',
          lineColor: '#8aa2ff',
          clusterBkg: '#0b0f18',
          clusterBorder: '#1c2333',
          edgeLabelBackground: '#0b0f18',
          sectionBkgColor: '#111623',
          sectionBkgColor2: '#111623',
          altSectionBkgColor: '#0b0f18',
          gridColor: '#1c2333',
          taskBkgColor: '#1e263b',
          taskBorderColor: '#526299',
          taskTextColor: '#f4f6fb',
          taskTextLightColor: '#f4f6fb',
          taskTextDarkColor: '#f4f6fb',
          taskTextOutsideColor: '#f4f6fb',
          activeTaskBkgColor: '#1e3939',
          activeTaskBorderColor: '#5ef0c4',
          doneTaskBkgColor: '#111726',
          doneTaskBorderColor: '#1c2333',
          critBkgColor: '#2f2927',
          critBorderColor: '#ffb45e',
          todayLineColor: '#5ef0c4',
          vertLineColor: '#8aa2ff',
        },
      },
    }),
    starlight({
      title: 'Psyche',
      description:
        'Psyche, an open research project building toward AGI from original, brain-inspired components: spiking cognitive maps (active) and the substrate that founded it (paused).',
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
