# Docs site (maintainers)

The public docs site for this repository, built with Astro and Starlight and deployed to GitHub
Pages under `/psyche/` by `.github/workflows/pages.yml`. Owned by the builder lane (D-031).

## Where the content comes from

Nothing in `src/content/docs/` or `src/data/` is written by hand. `npm run stage` runs
`tools/publish/stage.py`, which:

- copies every page listed in `docs/publish.json` from its governed source (checked by
  `tools/ledger_check.py`) into `src/content/docs/`, rewriting links for the site and replacing each
  Mermaid fence with its committed drawing from `src/diagrams/` (see Diagrams below);
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
| `npm run build` | Stage, type-check, build into `dist/`, then check the built pages for words run together and against the size budget |
| `npm run preview` | Serve `dist/` locally |
| `npm run check:spacing` | Only the spacing step: look for words run together in `dist/` |
| `npm run check:budget` | Only the budget step: gzipped JavaScript and CSS per page against `scripts/check-budget.mjs` |
| `npm run diagrams` | Draw the Mermaid diagrams of the published pages into `src/diagrams/` (see Diagrams below) |
| `npm run check:diagrams` | Fail if a diagram has no current drawing, or a drawing no diagram uses |
| `npm run check:a11y` | After a build: axe-core at WCAG 2.2 AA over the key pages of `dist/` (see below) |
| `npm test` | Unit tests for the plan, maze and battery logic |

### Diagrams

The governed Markdown keeps its ```` ```mermaid ```` fences, which GitHub draws on the repository.
The site draws none of them in the browser: no Mermaid ships, there is no flash of source, and a
reader with JavaScript off sees the drawing. Each fence is drawn once, ahead of the build, by
`scripts/render-diagrams.mjs` into `src/diagrams/<key>.svg`, and `tools/publish/stage.py` puts
that file inline in the page in place of the fence, inside a `figure` with a text alternative
(`title` and `desc`, written from the diagram itself). The drawing holds geometry, classes and
text and no colour; `src/styles/docs.css` paints it from the site's tokens. A diagram wider than
the column scales to three quarters of its drawn size and scrolls sideways beyond that, and the
scroll box takes keyboard focus. A flowchart written left to right is drawn top to bottom, because
a row of labelled boxes in a mono face is 900 to 1300px wide and the column is about 600; the
timeline's "today" marker is left out, because a drawing made once cannot know the date.

`npm run diagrams` draws what is missing and deletes what no page uses. Run it after changing a
diagram, after `python3 tools/publish/render_plan.py --write` moves a date in the gantt or the gate
flow, or after editing the script, then commit `src/diagrams/`. The file name is a key over the
script's own bytes and the fence's text (`tools/publish/diagrams.py`), so a changed fence or a
changed renderer names new keys: staging stops, and governance runs
`python3 tools/publish/diagrams.py --check`, until the drawings are redrawn. The check needs
nothing installed. Drawing needs Google Chrome or Chromium (`--chrome PATH` or `CHROME_PATH`) and
installs `mermaid` and `puppeteer-core`, at the exact versions pinned at the top of the script,
into a temporary directory (`DIAGRAM_TOOLS_DIR` changes where); they are not dependencies of the
site. The Mono face is the one the site already ships.

### Size budget

`scripts/check-budget.mjs` reads the built HTML in `dist/` and fails the build when a page ships
more gzipped JavaScript, or links more gzipped CSS, than its budget. JavaScript is what the page
loads (scripts, module preloads, island modules and what they import, inline scripts); CSS is
every linked stylesheet and every inline `<style>`. Fonts, images and the inline SVG of a diagram
are not counted. The budgets sit 3 percent above the sizes
measured when they were set and are listed page by page at the top of the script. Raise one on
purpose by editing the number there, and say why in the commit.

### Accessibility check

`scripts/check-a11y.mjs` serves `dist/` on a free local port, opens the home, battery, roadmap,
status and research pages in Chrome at desktop and phone width and in the light and dark themes
(reduced motion on), and runs axe-core with the WCAG 2.0, 2.1 and 2.2 level A and AA rules. It
exits 1 on any serious or critical violation and lists the lesser ones. It needs Google Chrome or
Chromium (`--chrome PATH` or `CHROME_PATH` names it) and installs its two dev packages,
`puppeteer-core` and `axe-core`, at the exact versions pinned at the top of the script, into a
temporary directory; they are not dependencies of the site. The Pages workflow runs it on every
pull request and every push to main, as its last step, after the site has been uploaded. There it
is report-only for now (see the `TODO(a11y)` in `.github/workflows/pages.yml`): the known
violations are listed in the run and do not fail it. Run locally, it fails on any serious or
critical violation.

## Design notes

### Identity: neural cartography

The site is drawn as an instrument for watching an agent learn a map. A near-black canvas carries
a faint coordinate grid; structure (walls, axes, grids, connectors) is drawn in a cold map blue;
the agent, its route and "now" take one luminous signal colour; labels and figures are set like
instrument readouts in a monospace. The light theme is the same map on a pale canvas. The signal
colour stays rare, a few percent of any screen at most. There are no pink or violet gradients, no
glass panels apart from the header's blur, no emoji, no stock 3D shapes and no mesh gradients.

### Tokens

Every colour is a token, defined once in `src/styles/global.css`: dark on `:root`, light on
`:root[data-theme='light']`. Components use the variables or the Tailwind utilities mapped to
them, never a raw colour.

| Role | Variable | Utility |
|---|---|---|
| Canvas | `--sl-color-black` | `bg-paper` |
| Card | `--sx-surface` | `bg-card` |
| Raised, hover | `--sx-surface-2` | `bg-sx-surface-2` |
| Hairline | `--sx-hairline` | `border-border` |
| Text | `--sl-color-white` | `text-ink` |
| Secondary text | `--sx-muted` | `text-sx-muted` |
| Signal: the agent, its route, now, the primary action, the current page | `--sx-agent` | `text-sx-agent` |
| Structure: walls, axes, grids, connectors | `--sx-structure` | `text-sx-structure` |
| Spike: rare emphasis, such as the next gate | `--sx-spike` | `text-sx-spike` |

`--sx-glow` is the signal glow (a shadow value), `--sx-grid` the grid line colour and `--sx-ease`
the one easing curve. Radii are 14px for cards, 10px for inner elements and fully round for pills
and chips. A card is the card surface with a hairline border and a faint inner top edge; on hover
its edge warms toward the signal colour and a soft light follows a mouse pointer.

### Type

- **Unbounded Variable** for display: page titles, section headings and large figures, at
  weights 300 to 500.
- **Instrument Sans Variable** for reading, h3 and the interface.
- **Martian Mono Variable** for kickers, section indices, chips, axis ticks, table headers, code
  and figures in data.

All three are self-hosted through `@fontsource-variable`. Reading measures are set in `rem`, not
`ch`: Instrument Sans has a wide zero, so `66ch` would run to about 95 characters. Documentation
paragraphs are 33rem wide, about 66 characters at 17px.

### Tailwind beside Starlight

Tailwind v4 runs beside Starlight (`@tailwindcss/vite` with `@astrojs/starlight-tailwind`), held
apart by cascade layers. `global.css` opens with the order `base, starlight, theme, components,
utilities`: Starlight's own styles sit in `starlight`, the site's CSS in `components` and
Tailwind's utilities above both, while the token blocks stay outside any layer. Because
Starlight's rules sit in a lower layer, the site restyles them by layer order alone, at low
specificity. Stock Tailwind colours are reset, so the only colour utilities are the site's tokens;
they follow the light and dark themes by themselves, so no `dark:` variants are written.
Tailwind-styled sections sit inside `class="not-content"`, which keeps Starlight's Markdown styles
off them.

### Chrome and documentation pages

- `src/styles/global.css` restyles Starlight's chrome through its own markup: a translucent
  header over a blur with a hairline under it, the Unbounded wordmark and a pill-shaped search
  with a mono shortcut chip; sidebar groups as indexed mono labels (01, 02, 03) with their pages
  on a hairline rail, the current page marked by a 2px signal bar on a raised surface; the
  contents list on the right in mono, with the same bar on the current heading; previous and next
  as cards; asides as hairline cards tinted by their role.
- `src/styles/docs.css` styles the staged documentation pages: Starlight's Markdown output on
  pages without `.sx-landing` or `.sx-wide`, at zero specificity and skipping elements with a
  class or inside `.not-content`, so the custom pages and the components keep their own styles.
  Page titles and section headings are in Unbounded, each section opening with a mono index and a
  hairline; h3 is in the sans. Links are ink with a quiet underline that turns signal on hover
  and focus; inline code is mono on the raised surface; tables are hairline cards with a mono
  header row and tabular figures; quotes carry a structure bar; images and diagrams sit in
  hairline cards.
- Mermaid diagrams are written for GitHub and carry their own colours. The site draws none of them
  in the browser: each is drawn ahead of time into a colourless SVG (see Diagrams) and `docs.css`
  paints it from the live tokens, so one file reads in both themes. The labels were measured in
  Martian Mono when the diagram was drawn, so the stylesheet changes colour only, never type.

### Motion

- Hover and state changes take 180ms; reveals take 600 to 900ms; everything uses `--sx-ease`.
  Landing blocks below the fold fade and rise once as they enter, through one shared observer.
  Layout is never animated. Signal elements may glow; nothing loops on its own.
- Maze and battery figures draw only the agent's trail and its finished route.
- The landing's maze hero plays its sequence (the agent's trail, the goal, the direct route)
  three times and stops on the finished picture. A Pause button stops it at any point, and it
  also pauses while it is mostly off-screen or the tab is hidden. Elsewhere, figures move on
  hover, focus or a button, or play when they come into view, and anything that runs longer than
  five seconds has a Pause button.
- The server renders the finished picture, so without JavaScript, or with
  `prefers-reduced-motion: reduce`, every figure shows its final frame and nothing moves.

### Other notes

- The illustrations are drawings of classic paradigms computed deterministically in
  `src/lib/maze.ts` and `src/lib/battery.ts`. They are not results and not a model.
- Astro removes a line break next to an `{expression}` or an inline element, which runs words
  together. Keep `text {expr} text` and `text <a>…</a> text` on one line, or end the line with
  `{' '}`. The spacing check at the end of `npm run build` fails on any it finds.

### Catalog credits

Many layouts are adapted from components in the 21st.dev catalog: ported to the site's tokens,
their copy replaced and their animation libraries replaced by CSS or a few lines of script. Each
names its source in a one-line comment next to the code, and all of them are listed in
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) with the files that credit them, which is the
one list to keep current. Everything else is written for this site.
