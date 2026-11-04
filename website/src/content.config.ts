import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

const DAY = /^\d{4}-\d{2}-\d{2}$/;

// The docs collection is filled only by `npm run stage`; see astro.config.mjs. A blog post is a page of
// it under blog/, and carries four more fields, which tools/publish/stage.py writes from the post's own
// front matter after checking them (tools/publish/blog.py): the day it was published, the day it was
// revised if it was, its author and its tags. A docs page has none of them.
export const collections = {
  docs: defineCollection({
    loader: docsLoader(),
    schema: docsSchema({
      extend: z.object({
        date: z.string().regex(DAY).optional(),
        updated: z.string().regex(DAY).optional(),
        author: z.string().min(1).optional(),
        tags: z.array(z.string().min(1)).optional(),
      }),
    }),
  }),
};
