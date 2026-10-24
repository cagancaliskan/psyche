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
| `npm run build` | Stage, type-check and build into `dist/` |
| `npm run preview` | Serve `dist/` locally |
| `npm test` | Unit tests for the plan, maze and battery logic |

## Design notes

- Palette and type are defined once in `src/styles/global.css` as Starlight custom properties:
  ink violet for text, eosin pink only for the agent (trails, paths, "today"), slate teal for
  structure. Newsreader for display, Atkinson Hyperlegible Next for reading.
- The only automatic motion is the landing figure's single sequence; everything else moves only
  in response to a button. `prefers-reduced-motion` shows final frames.
- The illustrations are drawings of classic paradigms computed deterministically in
  `src/lib/maze.ts` and `src/lib/battery.ts`. They are not results and not a model.
- The custom components are hand-written. The landing page's stage arc (`.sx-stages`) follows
  the structure of the "Milestone Timeline" component by olewandowski1 on 21st.dev (timeline-1),
  ported from Tailwind to plain CSS on the site's tokens.
