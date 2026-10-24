import { defineCollection } from 'astro:content';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

// The docs collection is filled only by `npm run stage`; see astro.config.mjs.
export const collections = {
  docs: defineCollection({ loader: docsLoader(), schema: docsSchema() }),
};
