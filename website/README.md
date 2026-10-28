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

Hand-written copy lives only in `src/pages/*.astro`, `src/components/*`, `src/lib/battery.ts`, `src/lib/seo.ts` and
`src/lib/pageChrome.ts` (the footer's labels and links).
`tools/publish/check_copy.py` scans it with the same claim and count rules as the docs.

The landing page presents Psyche as one research project in stages: stage 1, the substrate
(the foundation); stage 2, spiking cognitive maps; later stages toward the
long-term aim. Stage states and dates are read from the ledger projection, never typed.

## Commands

| Command | What it does |
|---|---|
| `npm ci` | Install the pinned dependencies |
| `npm run stage` | Stage content and data from the repository |
| `npm run build` | Check the social image against the ledger, stage, type-check, build into `dist/`, then check the built pages and figure captions for words run together, every in-page reference for its id, against the size budget and for their search and link-preview head |
| `npm run preview` | Serve `dist/` locally |
| `npm run check:spacing` | Only the spacing step: look for words run together in `dist/` (the hand-written pages' text, and the caption of every figure on every page) |
| `npm run check:refs` | Only the reference step: every `<use href="#…">`, `url(#…)`, `aria-labelledby`, `aria-describedby`, `aria-controls` and `<label for>` in `dist/` must name an id on its own page |
| `npm run check:budget` | Only the budget step: gzipped JavaScript and CSS per page against `scripts/check-budget.mjs` |
| `npm run diagrams` | Draw the Mermaid diagrams of the published pages into `src/diagrams/` (see Diagrams below) |
| `npm run check:diagrams` | Fail if a diagram has no current drawing, or a drawing no diagram uses |
| `npm run check:a11y` | After a build: axe-core at WCAG 2.2 AA over every page of `dist/` and the interface states a reader opens; fails on any serious or critical violation, and exits 2 when it could not set itself up (see below) |
| `npm run check:seo` | After a build: the head of every built page, the manifest, `robots.txt` and the sitemap (see Search engines and link previews) |
| `npm run check:og` | Fail if the social image was not drawn for the stage the ledger says is active |
| `npm run og` | Draw the social image again from the ledger's program state |
| `npm run icons` | Draw the PNG icons in `public/` from `brand/psyche-icon.svg` |
| `npm test` | Unit tests for the plan, maze, battery, head, sitemap-date and page-chrome (title strip, sheet number, stage line, next gate, footer date and links) logic, for the table regions, for the search override (it must stay Starlight's component with its three edits) and for the lock of the accessibility check's two packages |

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
about 34 KB of JavaScript, most of it the interface that Starlight's search loads on idle (about
26 KB), which an eager-only count would miss, as it once missed the diagram library that a lazily
loaded chunk carried. The check also fails when a file in `dist/_astro` is named for such a library
(mermaid, katex, cytoscape, d3-). The budgets sit 3 percent above the sizes measured when they were
set, so that another zlib build does not trip them but real growth does, and are listed page by page at
the top of the script with those sizes and what last moved them. Raise one on purpose by editing the
number there, and say why in the commit.

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
  `ResearchProject`, in the public wording, with the aim named as an aim). The 404 page has a title
  and a description of its own (`NOT_FOUND` in `src/lib/seo.ts`: "Page not found", a name and never the
  status code), is in no sitemap and is kept out of search.
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
  description (the 404 page's included, which must also carry the `NOT_FOUND` title, description and its
  own canonical address), an `og:` or `twitter:` value that is not the page's own, an image that is absent
  or the wrong size, a missing theme colour, icon or manifest, a `noindex` anywhere but the 404 page,
  structured data that does not parse or sits on another page, a manifest whose icons are missing, and
  a sitemap that lists the wrong pages or lacks a date where git history is available.

### Accessibility check

`scripts/check-a11y.mjs` serves `dist/` on a free local port and runs axe-core, with the WCAG 2.0, 2.1
and 2.2 level A and AA rules, over every page of the site, in Chrome at desktop and phone width and in
the light and dark themes (reduced motion on). The pages are found, not listed: each folder of `dist/`
with an `index.html`, and the 404 page, so a page added later is audited without anyone adding it. It
then opens, on the Decision gates page, what a reader opens with a click, and audits that in the same
configurations where they apply: the search dialog with results, the phone menu and the phone contents
list.

It exits 1 on any serious or critical violation (a violation that carries no impact counts as one) and
on anything it cannot audit: a page that does not answer 200, a state that will not open (each load is
tried twice) or a run in which axe tested fewer than 20 rules. It lists moderate and minor violations
and never fails on them, and never fails on what axe marks "incomplete" (it lists those too: today only
`color-contrast`). It needs Google Chrome or Chromium (`--chrome PATH` or `CHROME_PATH` names it) and
installs its two dev packages, `puppeteer-core` and `axe-core`, at the exact versions that
`scripts/a11y-tools/package.json` names and with their own dependencies as its `package-lock.json`
locks them (`npm ci`, tried three times; `scripts/a11y-tools.test.mjs` fails when a version there is
not exact or the lock disagrees),
into `node_modules/.cache/psyche-a11y-tools` (`A11Y_TOOLS_DIR` names another), a directory it creates
private and refuses when someone else owns it or others can write to it; they are not dependencies of
the site. It closes the server
and the browser before it exits. It exits 0 when it ran and found nothing serious, 1 on a violation or a
page it could not audit, and 2 when it could not set itself up (the install, no Chrome, a Chrome that will not start): that says nothing
about the site, so the workflow runs it once more on a 2 and never on a 1. `--only /,research/gates/,404.html`
(`/` is the home page) audits just those pages while you work on them (the states run only with
research/gates/), and `--port N` names the port to serve on; the workflow always runs it whole. The Pages
workflow runs it on every pull request and every push to
main, as the last step of the `build` job, after the site has been uploaded, and the step is blocking:
a violation fails the job, so a pull request cannot merge on it and the site is not deployed.

What the site does so that the check passes, and what has to stay true:

- **A control's name contains the text drawn on it** (WCAG 2.5.3). The search button's shortcut cap
  ("Ctrl K", or the command key and K) is not text: `src/components/chrome/Search.astro` is Starlight's
  Search component with the two keys drawn from a `data-key` attribute by a pseudo-element in
  `global.css`, and the cap hidden from assistive technology, so the button's visible text is "Search",
  its name, and the shortcut is told by `aria-keyshortcuts`. `src/lib/searchOverride.test.ts` applies
  those edits to the installed Starlight file and fails when the result is not the override, so an
  upgrade of Starlight cannot leave an old search behind. A battery row on the landing page is a link
  that holds a picture: its name is its visible label, and the picture is `aria-hidden` and draws the
  letters on its nodes through `<use>` from glyphs defined once per page, outside every link
  (`components/battery/BatteryTeaser.astro`), so no text but the label is inside the link.
- **A table that can scroll is a named, focusable region** (WCAG 2.1.1). Every table of a Markdown page
  is wrapped in `<div class="sx-table" role="region" tabindex="0" aria-label="Table: ...">`, named
  after the table's caption or the nearest heading before it (two under one heading are numbered). It
  is a tab stop, and a landmark, in the static markup, because static markup cannot know the width of
  the reader's screen; `components/chrome/TableRegions.astro` (a script on every page) then takes the
  role, the name and the tab stop off a region whose table fits and puts them back the moment it
  scrolls, so a page of five tables does not cost five dead stops. Without script the static attributes
  stay. The diagrams' scroll box is a tab stop even where nothing scrolls. The wrapper is the card and the
  one that scrolls (`docs.css`). Astro 7 renders Markdown with Satteri, so the step is a Satteri plugin that a small
  integration appends to the processor, as Starlight appends its own (`scripts/table-region.mjs`,
  tested in `scripts/table-region.test.mjs`); a `markdown.rehypePlugins` entry would need
  `@astrojs/markdown-remark`, which the site does not install. A table written as raw HTML in a Markdown
  file is not an element at that stage and would not be wrapped: write tables in Markdown.
- **Focus is a 2px ring in the signal colour.** A diagram's scroll box is masked at its edges, which
  would fade a ring drawn on it, so the figure carries the ring; a table region has no mask and
  carries its own.

What axe cannot decide is text contrast over gradients, pseudo-element content and images, which it
marks "incomplete" on every page. That is settled by pixels, not by axe, and again after any change to
a colour token or a surface: render the page, render it again with the glyphs made transparent, treat
every pixel that differs as text, and measure each run's foreground against its own background (the
10th percentile of the strongest pixels, which is conservative) at 4.5:1, or 3:1 for large text; over
every page at both widths in both themes, and over the open search dialog, menu and contents list. The
tool for that is not in the repository, and the result is not recorded here: it is a measurement to
repeat after a colour or surface changes, not a fact to carry. After a change to the chrome, also walk
the keyboard by hand (header, sidebar, contents list, a table region that scrolls, the footer and the
404 page's links at 1440 and 390 pixels) and confirm the focus ring is in view on every stop, and look
at the page with forced colours on, where a transparent border is drawn and a background-only mark is
not.

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
| Strong rule: the edge of a control, the mark of a state (3:1 or more against the canvas and both surfaces) | `--sx-rule-strong` |
| Text | `--sl-color-white` |
| Secondary text | `--sx-muted` |
| Signal: the agent, its route, now, the primary action, the current page | `--sx-agent` |
| Structure: walls, axes, grids, connectors | `--sx-structure` |
| Spike: rare emphasis, such as the next gate | `--sx-spike` |

`--sx-glow` is the signal glow (a shadow value), `--sx-grid` the grid line colour and `--sx-ease`
the one easing curve. `--sx-lab-size` and `--sx-lab-track` are the one mono label of the site (10.5px,
0.13em, uppercase: a field label or a section head, weight 400 or 500); chips in `plan.css` are the only
smaller mono type. `--sx-dur`, `--sx-dur-bar` and `--sx-dur-line` are how long the chrome's state changes
take (a colour, a bar running along a rule, an underline drawing) and are `0s` under
`prefers-reduced-motion: reduce`, so no rule needs its own override. `--sx-gutter` is the landing
page's gutter, which the footer's title block takes on that page. Radii are 14px for cards, 10px for inner elements and fully round for pills
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

- `src/styles/global.css` restyles Starlight's chrome through its own markup, as a drafting sheet: a
  nearly solid header over a light blur with a hairline under it and the Unbounded wordmark; the search as a
  square field in the strong rule with a mono label and a key cap, and its dialog as a sheet with
  registration corners, a mono readout of the count and each result a mono page label over a ruled list
  of its sections; sidebar groups as indexed mono labels (01, 02, 03) with their pages on a hairline
  rail; the contents list on the right in mono, on the same kind of rail. The current page, and the
  heading being read, take a 2px signal bar on the rail and ink text, with no fill, and hover only
  changes the ink. Previous and next are ruled rows (a hairline above each and one under the pair, a
  mono label over the title, a short bar on the rule that runs the row's width on hover or focus), and
  asides are a rule down the start edge in the aside's colour with a mono label and no card. The
  chrome draws no shadow, no fill and no pointer-following light. A border that is the only thing
  identifying a control (the search field, the menu button, the contents toggle, the search input)
  uses `--sx-rule-strong`; every other rule is the hairline, which is decorative.
- `src/styles/docs.css` styles the staged documentation pages: Starlight's Markdown output on
  pages without `.sx-landing` or `.sx-wide`, at zero specificity and skipping elements with a
  class or inside `.not-content`, so the custom pages and the components keep their own styles.
  Page titles and section headings are in Unbounded, each section opening with a mono index and a
  hairline; h3 is in the sans. Links are ink with a quiet underline that turns signal on hover
  and focus; inline code is mono on the raised surface; tables are hairline cards with a mono
  header row and tabular figures, each in a named scroll region that takes the focus ring (see
  Accessibility check); quotes carry a structure bar; images and diagrams sit in hairline cards.
- `src/components/chrome/PageTitle.astro` adds a ruled strip above every page title, as the head of a
  drawing sheet. A page of stage 1 (`substrate/*`) or stage 2 (`research/*`) opens it with the stage and
  its section ("Stage 1 Substrate") and ends it with that stage's state, read from the public ledger
  projection ("Active", "Paused since" and the day, the day never split; the square marker is the signal
  colour when active, an outline otherwise). A page outside the stages opens with the sidebar's number for
  its group ("01 Start here"); the 404 page says "Error 404 ... Not filed". The stage number and the
  sidebar's group number are never printed on one strip: they are different numbers. Below 30rem the two
  ends stack. Nothing is typed per page: the logic is `src/lib/pageChrome.ts` (tested in
  `pageChrome.test.ts`, which also fails when the publication manifest gains a section that has no stage,
  or when a section title names a program state that the ledger does not hold). The stage numbers are
  fixed there, as in `tools/publish/og.py`. The file lives with the other chrome, outside the folders that
  date `/roadmap/` and `/status/` (`scripts/sitemap-lastmod.mjs`), so a change to the strip moves no
  page's date.
- `src/components/chrome/Footer.astro` overrides Starlight's footer on every page. The edit link and
  previous and next stay; below them is the sheet's title block: a hairline frame with registration
  corners (`.sx-reg`) whose cells share their rules. A first row holds the sheet (the page's title and its
  number among the sidebar's links, written "NN / NN" here because it is counted, never typed), its stage
  with that stage's state and, on a page of stage 2, the next gate ("Gate A", and its date or "decision
  pending"). The gate is read from the public plan as of the day the plan was written, as the roadmap's
  built page reads it, and `src/components/chrome/NextGateClock.astro` reads it against the reader's day
  in the browser, as the roadmap does, so the two never disagree; a day in a cell never breaks across
  lines. A cell is left out when its data is absent, so the home
  page and the 404 page, which are not sheets, have no first row (on the home page the block takes the
  landing's own gutter). A second, quieter row holds the repository's links, each saying what it does
  (the licence, the source, the discussions, "Cite this repository", which GitHub offers from
  `CITATION.cff`, and "Report a vulnerability") and "Last updated". That date is the last commit that
  touched the files the page is made from, from the helper that dates the sitemap
  (`scripts/sitemap-lastmod.mjs`, through `src/lib/lastUpdated.ts`), so the two agree; with no git history
  (a shallow clone) it is left out, and the build date is never used. The block and the strip are left out
  of search (`data-pagefind-ignore`). The component is a copy of Starlight's footer with the block added
  (see `THIRD_PARTY_NOTICES.md`).
- `src/components/chrome/Search.astro` is Starlight's Search component, copied with the shortcut cap
  drawn rather than written, so the button's name holds its visible text (see Accessibility check); the
  look of the button and the dialog is `global.css`. It is credited in `THIRD_PARTY_NOTICES.md`.
- `src/pages/404.astro` is the 404 page (Starlight's own route is off: `disable404Route`). Under the
  strip every page opens with, a hairline frame with registration corners holds the address that was
  asked for (script: only the browser knows it) and one sentence, and a ruled list leads to the home
  page, the research overview, the test battery, the substrate status and the search (script: it opens
  Starlight's own dialog). With script, a row names the nearest filed page when the address is within two
  edits of one (`components/chrome/NearestPage.astro` bakes the pages in from the sidebar; the edit
  distance is a few lines in the page's script), and shows nothing otherwise. The sheet and the list run
  the same column as the footer's title block.
- Mermaid diagrams are written for GitHub and carry their own colours. The site draws none of them
  in the browser: each is drawn ahead of time into a colourless SVG (see Diagrams) and `docs.css`
  paints it from the live tokens, so one file reads in both themes. The labels were measured in
  Martian Mono when the diagram was drawn, so the stylesheet changes colour only, never type.

### Motion

- Hover and state changes take 180ms in the chrome (`--sx-dur`, which is `0s` under reduced motion); reveals take 600 to 900ms; everything uses `--sx-ease`.
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
