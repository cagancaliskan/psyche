// Docs site for the thesis-first Psyche repository (D-031).
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

const BASE = '/psyche';

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
  },
  integrations: [
    mermaid({ theme: 'default', autoTheme: true }),
    starlight({
      title: 'Psyche',
      description:
        'Public summary of an undergraduate thesis on cognitive maps in spiking networks with local plasticity, and the paused Psyche substrate.',
      logo: { src: './src/assets/mark.svg', replacesTitle: false },
      social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/cagancaliskan/psyche' }],
      customCss: [
        '@fontsource-variable/newsreader',
        '@fontsource/atkinson-hyperlegible-next/400.css',
        '@fontsource/atkinson-hyperlegible-next/400-italic.css',
        '@fontsource/atkinson-hyperlegible-next/700.css',
        './src/styles/global.css',
      ],
      sidebar: stagedSidebar(),
      lastUpdated: false,
      pagination: true,
      plugins: [starlightLinksValidator({ errorOnRelativeLinks: false })],
      head: [{ tag: 'meta', attrs: { name: 'color-scheme', content: 'light dark' } }],
    }),
    react(),
  ],
});
