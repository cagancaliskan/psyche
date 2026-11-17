import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const DAY = /^\d{4}-\d{2}-\d{2}$/;

// Both collections are filled only by `npm run stage`; see astro.config.mjs.
//
// docs: every staged document, the blog's posts left out (src/content/docs/<slug>.md, or
// <slug>/index.md when other pages nest under it). src/pages/[...slug].astro renders them in the
// documentation frame (layouts/Docs.astro) at /<slug>/. The id is the document's slug in
// docs/publish.json: the file's path without `.md` and without a closing `/index`, so research/index.md
// is `research`. The schema is exactly what stage.py writes for a document: its title, its description
// and its source on GitHub.
//
// posts: the blog's posts, which tools/publish/stage.py writes to src/content/docs/blog/<slug>/index.md
// (beside each post's own figures). src/pages/blog/[slug].astro renders them on the page kit
// (layouts/Post.astro) at /blog/<slug>/; the id is the slug. The schema is exactly what stage.py writes
// for a post, after tools/publish/blog.py has checked the post's own front matter: its title and
// description, its source on GitHub, the day it was published, the day it was revised if it was, its
// author, its tags, and its neighbours in the list (false at either end).
const neighbour = z.union([z.literal(false), z.object({ link: z.string().min(1), label: z.string().min(1) }).strict()]);

export const collections = {
  docs: defineCollection({
    loader: glob({
      base: './src/content/docs',
      pattern: ['**/*.md', '!blog/**'],
      generateId: ({ entry }) => entry.replace(/\.md$/, '').replace(/(^|\/)index$/, ''),
    }),
    schema: z
      .object({
        title: z.string().min(1),
        description: z.string().min(1),
        editUrl: z.string().url(),
      })
      .strict(),
  }),
  posts: defineCollection({
    loader: glob({
      base: './src/content/docs/blog',
      pattern: '*/index.md',
      generateId: ({ entry }) => entry.replace(/\/index\.md$/, ''),
    }),
    schema: z
      .object({
        title: z.string().min(1),
        description: z.string().min(1),
        editUrl: z.string().url(),
        date: z.string().regex(DAY),
        updated: z.string().regex(DAY).optional(),
        author: z.string().min(1),
        tags: z.array(z.string().min(1)).optional(),
        prev: neighbour.optional(),
        next: neighbour.optional(),
      })
      .strict(),
  }),
};
