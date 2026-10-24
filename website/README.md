# Docs site (maintainers)

The public docs site for this repository, built with Astro and Starlight and deployed to GitHub
Pages under `/psyche/` by `.github/workflows/pages.yml`. Owned by the builder lane (D-031).

## Where the content comes from

Nothing in `src/content/docs/` or `src/data/` is written by hand. `npm run stage` runs
`tools/publish/stage.py`, which:

- copies every page listed in `docs/publish.json` from its governed source (checked by
  `tools/ledger_check.py`) into `src/content/docs/`, rewriting links for the site;
- writes `src/data/plan.json` (from `tools/research_plan.json`), `src/data/ledger.public.json` (a
  public projection of `tools/ledger.json`, including the project's aim and the program state of
  each stage) and `src/data/sidebar.json`.

Both directories are gitignored, and CI fails if a staged copy is ever tracked. To change what the
site says, edit the governed source and re-stage.

Hand-written copy lives only in `src/pages/*.astro`, `src/components/*` and `src/lib/battery.ts`.
`tools/publish/check_copy.py` scans it with the same claim and count rules as the docs.

The landing page presents Psyche as one research project in stages: stage 1, the substrate
(the foundation, paused); stage 2, spiking cognitive maps (active); later stages toward the
long-term aim. Stage states and dates are read from the ledger projection, never typed.

## Commands

| Command | What it does |
|---|---|
| `npm ci` | Install the pinned dependencies |
| `npm run stage` | Stage content and data from the repository |
| `npm run build` | Stage, type-check, build into `dist/`, then check the built pages for words run together |
| `npm run preview` | Serve `dist/` locally |
| `npm run check:spacing` | Only the last step: look for words run together in `dist/` |
| `npm test` | Unit tests for the plan, maze and battery logic |

## Design notes

- Palette and type are defined once in `src/styles/global.css` as Starlight custom properties:
  ink violet for text, eosin pink only for the agent (trails, paths, "today"), slate teal for
  structure. Newsreader for display, Atkinson Hyperlegible Next for reading.
- Tailwind v4 runs beside Starlight (`@tailwindcss/vite` with `@astrojs/starlight-tailwind`), held
  apart by cascade layers. `global.css` opens with the order `base, starlight, theme, components,
  utilities`: Starlight's own styles sit in `starlight`, the site's component CSS in `components`
  and Tailwind's utilities above both, while the token blocks stay outside any layer. Stock
  Tailwind colours are reset, so the only colour utilities are the site's tokens (`text-ink`,
  `bg-paper`, `text-sx-agent`, `text-sx-structure`, `border-sx-hairline` and the rest); they follow
  the light and dark themes by themselves, so no `dark:` variants are written. Tailwind-styled
  sections sit inside `class="not-content"`, which keeps Starlight's Markdown styles off them.
- `src/styles/docs.css` styles only the staged documentation pages: Starlight's Markdown output on
  pages without `.sx-landing` or `.sx-wide`, at zero specificity, so the custom pages and the
  components keep their own styles. It sets the measure and leading, Newsreader section headings
  with a hairline above each one, underlined links that take the agent colour on hover and focus,
  tinted inline code, hairline tables with tabular figures, structure-colour blockquotes and
  asides tinted from the tokens. Its one site-wide rule marks the current page in the sidebar.
- Motion is kept small. The landing's maze hero plays its sequence (the agent's
  trail, the goal, the direct route) at most three times and stops on the finished picture; a
  Pause button stops it at any point, and it also pauses while it is mostly off-screen or the
  tab is hidden. Elsewhere, figures move on hover, focus or a button, or play when they come into
  view, and anything that runs longer than five seconds has a Pause button. The server renders
  the finished picture, so without JavaScript, or with `prefers-reduced-motion: reduce`, every
  figure shows its final frame and nothing moves.
- The illustrations are drawings of classic paradigms computed deterministically in
  `src/lib/maze.ts` and `src/lib/battery.ts`. They are not results and not a model.
- Astro removes a line break next to an `{expression}` or an inline element, which runs words
  together. Keep `text {expr} text` and `text <a>…</a> text` on one line, or end the line with
  `{' '}`. The spacing check at the end of `npm run build` fails on any it finds.
- Several layouts are adapted from components in the 21st.dev catalog: ported to the site's
  tokens, with their copy replaced and their animation libraries replaced by CSS or a few lines
  of script. Each names its source in a one-line comment next to the code. The hero follows
  "Hero Section with Animated Grid" by shadcnui-blocks, with a caption chip after "Chip" by
  preetsuthar17 and a pause control after "Mute Toggle Button" by sean0205. The landing uses
  "Scroll Reveal Content A" by abui (the stages), "Bento Feature Grid" by ln-dev7 (how the work
  is built), "Us vs Them Comparison" by olewandowski1 (public now and withheld) and "Stats Band"
  by kuratlielia (the figures band, also on the status page). The test battery uses "Line Draw
  SVG" by pulkitxm, "Feature Grid Spotlight Cards" by mohammadshehadeh, "Underlined Navigation
  Menu" by shadcnui-blocks and "Stepper" by kevingirelli. The roadmap and status pages use
  "Status" by diceui, "Status Badge" by serafimcloud, "Gantt Chart" by klyv-ui, "Stepper" by
  kevingirelli and "Quarterly Roadmap Columns" by olewandowski1. Everything else, the
  documentation styles included, is written for this site.
