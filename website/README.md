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

Hand-written copy lives only in `src/pages/*.astro`, `src/components/*`, `src/lib/battery.ts` and `src/lib/seo.ts`.
`tools/publish/check_copy.py` scans it with the same claim and count rules as the docs.

The landing page presents Psyche as one research project in stages: stage 1, the substrate
(the foundation, paused); stage 2, spiking cognitive maps (active); later stages toward the
long-term aim. Stage states and dates are read from the ledger projection, never typed.

## Commands

| Command | What it does |
|---|---|
| `npm ci` | Install the pinned dependencies |
| `npm run stage` | Stage content and data from the repository |
| `npm run build` | Check the social image against the ledger, stage, type-check, build into `dist/`, then check the built pages for words run together, against the size budget and for their search and link-preview head |
| `npm run preview` | Serve `dist/` locally |
| `npm run check:spacing` | Only the spacing step: look for words run together in `dist/` |
| `npm run check:budget` | Only the budget step: gzipped JavaScript and CSS per page against `scripts/check-budget.mjs` |
| `npm run diagrams` | Draw the Mermaid diagrams of the published pages into `src/diagrams/` (see Diagrams below) |
| `npm run check:diagrams` | Fail if a diagram has no current drawing, or a drawing no diagram uses |
| `npm run check:a11y` | After a build: axe-core at WCAG 2.2 AA over the key pages of `dist/` (see below) |
| `npm run check:seo` | After a build: the head of every built page, the manifest, `robots.txt` and the sitemap (see Search engines and link previews) |
| `npm run check:og` | Fail if the social image was not drawn for the stage the ledger says is active |
| `npm run og` | Draw the social image again from the ledger's program state |
| `npm run icons` | Draw the PNG icons in `public/` from `brand/psyche-icon.svg` |
| `npm test` | Unit tests for the plan, maze, battery, head and sitemap-date logic |

### Diagrams

The governed Markdown keeps its ```` ```mermaid ```` fences, which GitHub draws on the repository.
The site draws none of them in the browser: no Mermaid ships, there is no flash of source, and a
reader with JavaScript off sees the drawing. Each fence is drawn once, ahead of the build, by
`scripts/render-diagrams.mjs` into `src/diagrams/<key>.svg`, and `tools/publish/stage.py` puts
that file inline in the page in place of the fence, inside a `figure` with a text alternative
(`title` and `desc`, written from the diagram itself: the title is the image's name and the
description its description, and an item the plan leaves undated is described as undated, never
with the date the chart draws it at). The drawing holds geometry, classes and text and no colour;
`src/styles/docs.css` paints it from the site's tokens, with what a reader needs to see at least
3:1 against the card in both themes. A diagram wider than the column scales to three quarters of
its drawn size (nine tenths for a timeline on a narrow screen) and scrolls sideways beyond that;
the scroll box fades at its edges, is named after the drawing and takes keyboard focus (it is a
tab stop even where nothing scrolls, because static markup cannot know the reader's screen). A flowchart written left to right is drawn top to bottom, because
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
into a private cache under `node_modules/.cache` (owner-only: the script loads code from it, so it
refuses a directory owned by someone else or writable by others; `DIAGRAM_TOOLS_DIR` changes
where); they are not dependencies of the site. The Mono face is the one the site already ships.

### Size budget

`scripts/check-budget.mjs` reads the built HTML in `dist/` and fails the build when a page ships
more gzipped JavaScript, or links more gzipped CSS, than its budget. JavaScript is what the page
loads (scripts, module preloads, island modules and what they import, statically or with a
literal `import('./chunk.js')`, plus inline scripts); CSS is every linked stylesheet and every
inline `<style>`. Fonts, images and the inline SVG of a diagram are not counted. A docs page counts
about 33 KB of JavaScript, most of it the interface that Starlight's search loads on idle (about
26 KB), which an eager-only count would miss, as it once missed the diagram library that a lazily
loaded chunk carried. The check also fails when a file in `dist/_astro` is named for such a library
(mermaid, katex, cytoscape, d3-). The budgets sit 3 percent above the sizes
measured when they were set and are listed page by page at the top of the script. Raise one on
purpose by editing the number there, and say why in the commit.

### Search engines and link previews

What a page says about itself outside its own text:

- **Description.** Every staged docs page takes its description from its entry in
  `docs/publish.json` (`description`: one plain sentence of 120 to 160 characters that no other page
  repeats; `tools/publish/core.py` validates it and `stage.py` refuses a page without one). The
  four hand-written pages carry theirs in their `.astro` front matter, and the landing page's is
  the project in one sentence (`PROJECT_DESCRIPTION` in `src/lib/seo.ts`). Nothing in a
  description states a count or which stage is active; those are read from the ledger where the
  page shows them.
- **Head.** `astro.config.mjs` writes what is the same on every page (the two theme colours with
  their media queries, the icon, touch-icon and manifest links, the card's image and its alt text).
  `src/routeData.ts` writes what differs by page, through `src/lib/seo.ts`: `og:type` (`website` on
  the landing page, `article` elsewhere), `twitter:title` and `twitter:description` from the page,
  `noindex` on the 404 page, and the landing page's structured data (schema.org `WebSite` and
  `ResearchProject`, in the public wording, with the aim named as an aim).
- **Sitemap.** `@astrojs/sitemap` is registered here, not left to Starlight, so each entry carries
  a `lastmod`: the date of the last commit that touched the files the page is made from
  (`scripts/sitemap-lastmod.mjs`: the governed source for a docs page; for the others the page file,
  the components and modules it imports, and the plan or ledger it draws on. `npm test` reads each
  page's imports and fails when one is in no page's list). With no git history (a shallow clone, no git) it writes no
  date rather than a wrong one, so the Pages workflow checks out the full history.
- **`robots.txt` and `site.webmanifest`** are static files in `public/`. A crawler reads
  `robots.txt` only at the root of a host, which a project site under `/psyche/` does not control;
  the file is kept for tools that look beside the sitemap, and the sitemap is named in the head too.
- **Icons.** `favicon.svg` stays the primary icon. `npm run icons` draws `favicon-32.png`,
  `icon-192.png`, `icon-512.png`, `apple-touch-icon.png` (full-bleed and opaque, because iOS rounds
  it itself) and `icon-512-maskable.png` (full-bleed, the P scaled into the safe zone) from
  `brand/psyche-icon.svg` with the Chrome already on the machine, at their exact sizes. Commit the
  result.
- **Social card.** `public/og.png` is a byte copy of `brand/psyche-social.png`, and the card names
  the active stage, so it is drawn, never edited: `npm run og` renders `scripts/og-card.html` with
  Chrome using the card text from `tools/publish/og.py`, which reads `program` in
  `tools/ledger.json`. It writes the PNG (with its stage line also inside the file), the copy, and
  `brand/psyche-social.json`, which records the stage line, the alt text and the image's sha256.
  `python3 tools/publish/og.py --check` (governance and `npm run build` run it) fails when the
  ledger's active stage is no longer the one the card was drawn for, or an image was replaced by
  hand. Run `npm run og` after any change to `program`, then commit the three files.
- **`npm run check:seo`** reads `dist/` after a build and fails on a missing or duplicated
  description, an `og:` or `twitter:` value that is not the page's own, an image that is absent
  or the wrong size, a missing theme colour, icon or manifest, a `noindex` anywhere but the 404 page,
  structured data that does not parse or sits on another page, a manifest whose icons are missing, and
  a sitemap that lists the wrong pages or lacks a date where git history is available.

### Accessibility check

`scripts/check-a11y.mjs` serves `dist/` on a free local port, opens the home, battery, roadmap,
status and research pages, and the three docs pages that show the timeline and the other kinds of
diagram (research/roadmap, claims-and-scope, disclosure-policy), in Chrome at desktop and phone width and in the light and dark themes
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
`:root[data-theme='light']`. Components use the variables, never a raw colour.

| Role | Variable |
|---|---|
| Canvas | `--sl-color-black` |
| Card | `--sx-surface` |
| Raised, hover | `--sx-surface-2` |
| Hairline | `--sx-hairline` |
| Text | `--sl-color-white` |
| Secondary text | `--sx-muted` |
| Signal: the agent, its route, now, the primary action, the current page | `--sx-agent` |
| Structure: walls, axes, grids, connectors | `--sx-structure` |
| Spike: rare emphasis, such as the next gate | `--sx-spike` |

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

All three are self-hosted through `@fontsource-variable`, with `font-display: swap`. Reading
measures are set in `rem`, not `ch`: Instrument Sans has a wide zero, so `66ch` would run to about
95 characters. Documentation paragraphs are 33rem wide, about 66 characters at 17px.

How the faces load:

- Each family is split by script, and a browser fetches only the files whose characters a page
  uses. An English page fetches the Latin file of each family.
- The files are not preloaded. A preload fetches the two Latin files (81 KB) beside the
  render-blocking stylesheet; in headless Chrome with the cache off and the network throttled it
  delayed first paint by 80 to 430 ms depending on the link, and the stand-in faces below already
  take the layout shift to zero without it. Lab throttling cannot model the host's request
  priorities, so field data could still justify one: `src/routeData.ts` is where it would go.
- The italic of Instrument Sans (`wght-italic.css`, the weight axis only; the width axis is not
  used) is fetched only by a page that sets italic text: the landing's `<cite>` and the pages
  that use `<em>`.
- While a face is on its way, text is set in a stand-in: a local Arial or Courier New scaled and
  given the web font's vertical metrics (`src/styles/fonts.css`, which also records how the
  numbers were measured), so the swap changes the letter shapes and moves nothing. Measure again
  if a font or its weights change.

### Cascade layers beside Starlight

`global.css` opens with the layer order `base, starlight, theme, components, utilities`, and every
other stylesheet repeats it: Starlight's own styles sit in `starlight`, the site's CSS in
`components`, the one visually-hidden rule in `utilities` above both, and the token blocks stay
outside any layer. Because Starlight's rules sit in a lower layer, the site restyles them by layer
order alone, at low specificity. The `base` layer holds three rules: every element starts with a
`0 solid` border, and the reading and code faces are set on `html` and on `code`, `kbd`, `samp` and
`pre`. Light and dark switch through the variables, so no rule needs a theme variant. Custom
sections sit inside `class="not-content"`, which keeps Starlight's Markdown styles off them.

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
