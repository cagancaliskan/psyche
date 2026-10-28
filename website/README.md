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
  each stage), `src/data/progress.json` (the plan's public events and the first author of
  `CITATION.cff`, for the feed) and `src/data/sidebar.json`.

Both directories are gitignored, and CI fails if a staged copy is ever tracked. To change what the
site says, edit the governed source and re-stage.

The sidebar's first group is "Start here": Home, then the pages of the manifest section of that
title (`docs/publish.json`: the reader's guide, the questions and answers, the progress record, how
the project is run), then the other hand-written pages (`build_sidebar` in
`tools/publish/stage.py`). A section of the manifest with that title is moved into this group,
never shown as a second one of the same name; a section whose title differs from it only in case,
or any two sections with one title, is refused.

Hand-written copy lives only in `src/pages/*.astro`, `src/components/*`, `src/lib/battery.ts`, `src/lib/seo.ts` and
`src/lib/pageChrome.ts` (the footer's labels and links).
`tools/publish/check_copy.py` scans it with the same claim and count rules as the docs.

The landing page presents Psyche as one research project in stages: stage 1, the substrate
(the foundation); stage 2, spiking cognitive maps; later stages toward the
long-term aim. Stage states and dates are read from the ledger projection, never typed.
The landing page's closing section, Cite and contact (`components/landing/CiteContact.astro`),
carries the project's preferred citation, the archived report of stage 1 with its DOI, and the
contact route, GitHub Discussions; the hero's third action links the Reader's guide
(`components/LayersHero.astro`). The citation is copied from `preferred-citation` in
`CITATION.cff` and typed in the component, because that file is not part of the site's build;
`test_cited_doi` in `tools/publish/test_core.py` keeps the DOI equal to the one in `CITATION.cff`
and checks that the section links the repository's Discussions. The section has the anchor
`#cite`.

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
| `npm run check:seo` | After a build: the head of every built page, the manifest, `robots.txt`, the sitemap, the progress feed, and every link written with the site's own address (see Search engines and link previews) |
| `npm run check:og` | Fail if the social image was not drawn for the stage the ledger says is active |
| `npm run og` | Draw the social image again from the ledger's program state |
| `npm run icons` | Draw the PNG icons in `public/` from `brand/psyche-icon.svg` |
| `npm test` | Unit tests for the plan, maze, battery, head, sitemap-date, page-chrome (title strip, sheet number, stage line, next gate, footer date and links) and status-page (the readout's figures and each brick's two axes, `lib/status.ts`) logic, for the progress feed (`lib/feed.ts`), for the table regions (and the dates they keep on one line), for the search override (it must stay Starlight's component with its three edits) and for the lock of the accessibility check's two packages |

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
3:1 against the canvas in both themes. A diagram wider than the column scales to three quarters of
its drawn size (nine tenths for a timeline on a narrow screen) and scrolls sideways beyond that;
the scroll box fades at its edges, is named after the drawing and takes keyboard focus (it is a
tab stop even where nothing scrolls, because static markup cannot know the reader's screen). A flowchart written left to right is drawn top to bottom, because
a row of labelled boxes in a mono face is 900 to 1300px wide and the column is about 600; the
timeline's "today" marker is left out, because a drawing made once cannot know the date.

The geometry that CSS cannot reach is changed by the script's post-processing, so that the figure can be
drawn as a drafting figure: node corners (rx) are taken off, a stadium becomes a square with a second
square inside it (`terminal-inner`), an arrowhead is an open chevron, a gantt phase is a thin bar centred
on its row (6px, 8px when in progress) with its label beside it, a gate is a small square with a crosshair
of four ticks (`gate-ticks`), the bands behind the phases become one rule per phase and one for the axis,
and an item the plan leaves undated (marked * in its name) carries the class `open` so that it can be
drawn dashed or muted. A connection of a flowchart is a right-angled trace, as in the figure under the
title of the research overview: down, across at half the height between two points, down again. The
points Mermaid laid out between two nodes stay on the trace, so it never crosses a node and a label is
still on its line; it leaves a box level, a decision at its vertices, and stops 4px short of the node,
which is where Mermaid ends every connection, because the arrowhead's tip stands that far past the end
of the path. A connection that does not run downward is left as Mermaid drew it. None of it adds,
removes or changes a word of a title, a description or a label.

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
  structured data that does not parse or sits on another page, a manifest whose icons are missing, a
  sitemap that lists the wrong pages or lacks a date where git history is available, the progress feed (see
  below), and any link in a page's body that is written with the site's whole address and leads to no built
  page, file or id. A docs page reaches the hand-written pages (Home, the timeline, the paradigms, the status
  page), which have no Markdown source to link, that way, and the link validator treats such an address as
  external, so this check is the only one that sees a dead one.

### The progress page and its feed

`docs/progress.md` is the public record of the research plan: a table of the plan's events, the
commitments, and the feed. Its tables are generated blocks (`python3 tools/publish/render_plan.py
--write`), so nothing on it is typed. The events are derived in one place, `progress_events` in
`tools/publish/render_plan.py`, from `tools/research_plan.json` and nothing else: a phase started (status
active or done, start date fixed), a phase done (dated by the decision day of the gate that closes it,
since the edit that records a decision marks the phase done, so the date does not move with `as_of`; a
done phase that no gate closes needs a fixed end and is dated by the earlier of that end and the plan's
`as_of`), a gate decided (its decision date and next step only, never a verdict or a
criterion: D-034), a change recorded in the changelog (date, item, field, old and new value and reason; a
change of status carries no reason, and the plan refuses a changelog entry for a gate's status) and a hash
commitment (date, id, subject, reveal). Nothing dated after `as_of` is an event. Newest first; the same day
is ordered by kind, then item. The log is two columns, the day and then the item with what changed, so that
it fits a phone. `tools/publish/stage.py` stages the list as `src/data/progress.json` with the author named
in `CITATION.cff` (staging refuses a `CITATION.cff` that differs from the commit, and the Pages workflow
runs when that file changes); `src/pages/progress.xml.ts` serves it at `/psyche/progress.xml` as Atom 1.0
through `src/lib/feed.ts`, a serialiser that adds no event, no wording and no clock. Feed ids are tag URIs
(host, year, path below the base): the same on every build, and new if the host or the base path ever
changes. Every entry links to the progress page; every date is a day of the plan stamped noon UTC, and the
feed's `updated` is the newest event's day, never the build time, so the same plan always gives the same
bytes. Every page's head carries `<link rel="alternate" type="application/atom+xml">` for it
(`astro.config.mjs`); it is an endpoint, so it is not in the sitemap. `npm run check:seo` parses the built
file (with Python's XML parser, since Node has none) and checks that it is Atom with the right self and
alternate links, the author `CITATION.cff` names, an `updated` equal to the newest event's day and one
entry for each event of the plan, in the plan's order, each linking to a built page; and that every page's
head names the feed.

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
  stay. The diagrams' scroll box is a tab stop even where nothing scrolls. The wrapper is the box that scrolls (`docs.css`); with
  no card round a table, a 2px structure bar on the side where there is more is the cue that it scrolls, and a
  table that fits shows none. Astro 7 renders Markdown with Satteri, so the step is a Satteri plugin that a small
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
`:root[data-theme='light']`. Components use the variables, never a raw colour. The one place that holds
their values instead is the syntax theme of the code blocks (`astro.config.mjs`): Expressive Code writes a
theme's colours into the markup and checks their contrast, so it needs values. It uses three tokens, ink
(`--sl-color-white`), muted (`--sx-muted`) and structure (`--sx-structure`), in both themes, and changes
with them.

| Role | Variable |
|---|---|
| Canvas | `--sl-color-black` |
| Surface: a fill, not a card | `--sx-surface` |
| Raised, hover | `--sx-surface-2` |
| Hairline | `--sx-hairline` |
| Strong rule: the edge of a control, the mark of a state (3:1 or more against the canvas and both surfaces) | `--sx-rule-strong` |
| Text | `--sl-color-white` |
| Secondary text | `--sx-muted` |
| Signal: the agent, its route, now, the primary action, the current page | `--sx-agent` |
| Structure: walls, axes, grids, connectors | `--sx-structure` |
| Spike: rare emphasis, such as the next gate | `--sx-spike` |

`--sx-grid` is the grid line colour and `--sx-ease` the one easing curve. `--sx-lab-size` and `--sx-lab-track` are the one mono label of the site (10.5px,
0.13em, uppercase: a field label, a section head or a state label, weight 400 or 500). `--sx-dur`, `--sx-dur-bar` and `--sx-dur-line` are how long the chrome's state changes
take (a colour, a bar running along a rule, an underline drawing) and are `0s` under
`prefers-reduced-motion: reduce`, so no rule needs its own override. `--sx-gutter` is the landing
page's gutter, which the footer's title block takes on that page. Everything is drawn as a drafting sheet (the chrome, the landing, the roadmap and status pages, and the
documentation's tables, code blocks and figures): corners are square (0 to 2px; a circle only where a shape
is a dot or a ring by meaning), rules and ruled rows take the place of cards, and there are no pills. The
surface tokens remain for a few fills (the search dialog, and the pictures of the maze and the battery), and
no component is a card.

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
  rail; the contents list on the right in mono, on the same kind of rail. On a phone the contents toggle may
  shrink and wrap its label at large text sizes (320px wide at 200 percent), and the heading named beside
  it truncates first, so the page never scrolls sideways. The current page, and the
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
  and focus; inline code is plain mono in a hairline box at 2px; lists have square markers and mono
  numbers; the section-link icon is a mono `#`. Tables are ruled, with no card: a hairline above the
  header, the header as a mono label over a stronger rule, a hairline under each row and tabular figures;
  each is in a named scroll region that takes the focus ring and, where it scrolls, a 2px structure bar on
  the side where there is more (see Accessibility check). A date stays on one line: a browser would
  break `2026-10-23` after a hyphen in a narrow column or on a phone, so `scripts/table-region.mjs` sets
  `data-nowrap` on a cell that holds a date (an attribute, because the table rules skip a cell with a
  class), puts any other date in running text, such as the generated status line, in a
  `<span data-nowrap>` (code is left as it is) and `docs.css` keeps both from wrapping. Below 50rem, where Starlight drops its sidebar,
  a table of three or more columns also has a floor on its width, so that a phone scrolls it instead of
  squeezing a column to a word a line; beside the sidebars the column is narrower than that floor but wide
  enough to wrap the table as it is, so no floor is set there. Code blocks are square, in a hairline frame
  on the canvas, through Expressive Code's variables. Each has a caption line on a rule with a short
  structure bar under its start: the title, or `Terminal` for a terminal frame, and none for a block with
  neither (a caption that read `Text` or `Code` over every untitled block would name nothing). The line
  holds a square copy button in the strong rule, always visible, so that it never covers the code. A block
  that scrolls shows the table's bar on the side where there is more. The syntax colours are three inks
  of the site (`astro.config.mjs`): comments muted, commands, keywords and functions in the structure
  colour, everything else in ink, so no hue the site keeps for a meaning is used. Quotes carry a
  structure bar, images a hairline frame, and diagrams are drafting figures (see below).
- `src/components/chrome/PageTitle.astro` adds a ruled strip above every page title, as the head of a
  drawing sheet. A page of stage 1 (`substrate/*`) or stage 2 (`research/*`) opens it with the stage and
  its section ("Stage 1 Substrate") and ends it with that stage's state, read from the public ledger
  projection ("Active", "Paused since" and the day, the day never split; the square marker is the signal
  colour when active, an outline otherwise). A page outside the stages, which includes every page of the Start here group, opens with the
  sidebar's number for its group ("01 Start here") and ends with no state: a page of that group belongs to no
  stage (`START_SECTION` in `src/lib/pageChrome.ts`; `pageChrome.test.ts` fails when a page of the manifest's
  Start here section has a route that is a stage's); the 404 page says "Error 404 ... Not filed". The stage number and the
  sidebar's group number are never printed on one strip: they are different numbers. Below 30rem the two
  ends stack, and a state too long for the line (large text on a narrow screen) wraps between its words
  and the day, never inside the day. Nothing is typed per page: the logic is `src/lib/pageChrome.ts` (tested in
  `pageChrome.test.ts`, which also fails when the publication manifest gains a section, other than Start here,
  that has no stage, or when a section title carries a program state in brackets: a state is read from the ledger, never written
  in a title). The stage numbers are
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
  Martian Mono when the diagram was drawn, so the stylesheet changes colour only, never type. A drawing
  sits in a hairline frame with registration corners (the `.sx-reg` recipe, repeated in `docs.css` because
  the figure's markup is written by `stage.py`), on the canvas, with no radius, grid, fill or shadow.
  Flowchart nodes are square hairline boxes (a terminal node has a second square inside), connections are
  right-angled hairline traces ending in an open chevron, and a group is a solid hairline frame: a dash
  means "not yet" or "private" (a node the source dashes), never a group. The timeline reads in the roadmap's
  notation (`styles/plan.css`): a rule per phase, a thin bar for each phase (an outline when planned, filled
  in the structure colour when done, the signal colour in progress, dashed and muted where its end is not
  fixed) and each gate a square mark with a crosshair, never a filled diamond. In forced colours the
  bar in progress takes the system's highlight colour, the rules and gridlines the grey text colour, and a
  label keeps its halo, so that a gridline does not strike through it.

### The roadmap and the status page

Both are drawn as sheets, in the same language as the chrome: hairline rules, mono labels (the label
tokens), registration corners (`.sx-reg`), ruled rows in place of cards, square marks, and the signal
colour kept for what is current. A state is a mono label with a small marker whose shape says it as the
word does, so colour is never the only cue (WCAG 1.4.1), and the markers are drawn with borders, so
they survive forced colours. Everything is read from the plan or the ledger projection; no count, date
or state is typed in a component.

- **The roadmap** (`styles/plan.css`; `Timeline.tsx`, `NowLine.tsx`, `TimelineList.astro`,
  `GateStepper.astro`) is one skin on the landing, `/roadmap/`, `/research/roadmap/` and
  `/research/gates/`. The timeline is a hairline month axis with ruled rows and one thin bar per phase
  (an outline when planned, filled when done, the signal colour when active, dashed at an open end).
  Gates are square marks with a crosshair, lettered on the axis and at the end of the bar they close;
  the next gate has a second square round its mark and an underlined letter, and a gate past its date
  with no decision is filled in the spike colour. Today is a thin signal rule, and each phase label is
  knocked out of it. Below 36rem of the chart's own width the phase list takes over. The gate list is
  a ruled sheet, a row per gate with its letter on a vertical rule, in two columns from 40rem. The
  bars and the gate marks have forced-colours rules, because forced colours would otherwise draw every
  state like a planned one. `lib/gateClock.ts` keeps working through the data attributes
  (`data-gate-id`, `data-gate-state`, `data-next` and the rest); keep them.
- **The substrate readout** (`components/landing/SubstrateReadout.astro`, `styles/readout.css`) is the
  one readout of the landing, `/status/` and the substrate overview. It lays out by the width of its
  own container (one row each below 30rem, three to a row from 30rem, all in one row from 52rem, the
  label over the figure below 20rem), because the same figures sit in columns of three different
  widths. `framed` draws it as a sheet, with a slot under the figures.
- **The brick board** (`components/BrickBoard.astro`, `components/BrickTable.astro`,
  `styles/status.css`, `lib/status.ts`) is a key to the two axes over one ruled row per brick, build
  status and meaning verdict in columns of their own (CONTRIBUTING rule 3). It is a real `table`: the
  rows are CSS grids, which would drop the table's meaning for assistive technology, so every part
  carries its role in the markup. The ledger projection holds one status per brick, and a status is a
  name on one axis or the other, so a brick with a build status reads "Not earned" on the meaning axis
  (true while the meaning bar is open) and a brick with a meaning verdict reads "None recorded" on the
  build axis. `lib/status.test.ts` fails if the meaning bar is no longer open or a brick is earned, so
  that wording cannot go stale unseen. If a per-brick verdict is wanted, the ledger needs a structured
  field and `ledger_public` in `tools/publish/core.py` has to pass it on.
- **Cite and contact** (`components/landing/CiteContact.astro`, `styles/landing/cite.css`) is the
  landing's last section, section 07 of the caliper rail. It is a definition list of two ruled rows
  that reuse the landing's `.sx-ruled` rules (`styles/landing/rows.css`): a mono label in the label
  tokens, then its value, one over the other on a phone and side by side from 48rem on the method
  rows' columns, so a value starts where a method row's title does. The reference is set as the
  README and `docs/PSYCHE.md` set it, and its DOI is an inline link in the landing's link style,
  wrapped anywhere so that a narrow screen at 200 percent text does not scroll sideways; the contact
  link is the landing's section-end link. It draws no card, pill, glow, colour of its own or
  registration corner: the footer's title block directly below is the page's one frame. The row
  structure follows "Key Value List" by corr (21st.dev) and is credited in `THIRD_PARTY_NOTICES.md`.

### Figures on the documentation pages

The visual under the title of a docs page (`components/docs/*`, mapped in `visuals.ts` and drawn by
`chrome/PageTitle.astro`) is a drawing on the same sheet as the chrome: hairline rules, mono labels (the
label tokens), the shared registration corners (`.sx-reg`), square marks, and ruled columns and rows in
place of cards. The figures that `Figure.astro` draws (the stage arc, the release flow, the role lanes, the
evaluation pipeline, the determinism tiers and the layer stack) have no fill, glow, shadow, coordinate
grid, radius or motion, and ship no JavaScript of their own. The roadmap, gates and battery figures are
`bare`: they keep the sheets and the scripts of their own pages. All of the figures' styling is
`styles/docs-visuals.css`. A figure's words are the page's public summary, read from the ledger projection
or written in its component; a change to a figure changes its drawing, never its claims.

- **The frame** (`Figure.astro`) is a hairline box with registration corners and no fill. Its caption is
  the figure's label (`Fig.` and its name, the `.sx-kicker`) over one line of lead, ruled off from the
  drawing by a hairline across the full width of the frame, so a figure reads as a caption band over a
  drawing. `--dv-pad` is the frame's padding, which the caption band and a closing band cancel with a
  negative margin of the same size. The frame is a container named `sx-dv`, and the figures lay out by its
  width, not the window's. `bare` is for a figure whose content is a sheet with its own frame and rules
  (the roadmap's phase list, the decision gates, the battery explorer): it draws no frame, no corners and
  no padding, and only the caption stays above the sheet. The Mermaid drawings in `docs.css` use the same
  hairline and corners.
- **Sequences** (the stage arc, the release flow and the role lanes, each an `ol.sx-seq`) draw every step
  as a square on a hairline rail with its words beside or under it, numbered in the release flow and the
  role lanes. The stage arc's markers are empty: the label under one already says "Stage 1", and the
  marker's own line says whether the stage is current. Under 40rem of the figure's width the steps stack
  and the rail runs down from marker to marker; what one stage hands to the next stands beside the rail on
  a short leader. From 40rem the stage arc and the release flow are ruled columns, one per step: the rail
  runs across, each column's rule drops from its marker, and the three rows (the hand-off, the marker with
  its rail, the words) are shared by all columns through a subgrid, so the rails line up whatever the
  length of a label. The role lanes stay one step under another and become ruled rows, with the role as a
  mono label in a column of its own. A marker is a bordered square, so it survives forced colours, and it
  says its state by shape as well as colour: dashed for a step that is not here (a private step, a stage
  not specified yet, a step that only some changes take), a heavier line in the signal colour for the
  current stage, a square in a square for where the flow ends. A stage's state is also a mono label with a
  small square (filled when active, an outline when paused, dashed when not specified yet), as the title
  strip draws it, and the day in it never splits. The rail is a border, dashed where it leads into a stage
  that is not specified yet. Words wrap anywhere, and below 24rem of window width the frame's padding and
  the markers give up some room, so that 320px at 200 percent text does not scroll sideways. The figures
  hold no control, so they add no tab stop.
- **The evaluation pipeline** (`EvaluationPipeline.astro`) is a drafting diagram: a node is a square
  hairline box in the strong rule on the sheet's own fill, a private node is drawn with a dashed outline
  and says so in words, and a zone (the agents, the metrics) is a solid box in the strong rule with its
  mono label set into its top edge (a zone is not dashed: a dash means private). The connectors are fixed
  traces in the structure colour that leave a box level, turn in the middle of the gap and enter the next
  one level, with a small open arrowhead at every box they enter and a dot where they split or join. From
  40rem of the figure's width the five columns sit on a 720 by 420 sheet under a ruler whose ticks number
  them 01 to 05 (CSS counters with empty alt text, so the list keeps its own order and the numbers are not
  read as words); the traces are one SVG on the same grid as the columns and line up through percentages.
  Narrow, the boxes stack, a short connector with an arrowhead drops from each to the next, and a zone's
  boxes wrap in a grid whose columns shrink to the figure (`min(7.5rem, 100%)`), so that 320px at 200
  percent text does not scroll sideways. Boxes wrap words anywhere. Nothing moves.
- **The determinism tiers** (`DeterminismTiers.astro`) are a ruled sheet with one row per tier, the
  strongest first, the rows running from edge to edge of the frame under the caption band. A row is the
  tier's letter over its gauge, then the guarantee and, under a hairline, what the tier applies to and how
  it is checked in two columns split by a hairline (stacked below 40rem). The gauge is a scale of three
  cells, the weakest tier on the left; the cells filled count the row's place on the scale. The scale is
  labelled once, under the first row, with the tiers' own letters, as a ruler is marked once, and the
  rows under it share it, so the order of strength reads by count and position, not colour. The letters
  are drawn by the stylesheet from the data, so they add no text to the page or to search. A filled cell
  is a border as thick as the cell, so it survives forced colours (the cells take Highlight there). The
  gauge shows only the order the page states: a result built from parts at different tiers states the
  weakest.
- **The layer stack** (`LayerStack.astro`) is an elevation, not an isometric view: the five layers are
  ruled bands one on top of the other, the store at the bottom, sharing their edges, each labelled with its
  module in mono; a leader with a small square at the band runs to the layer's name, line and state; a
  bracket on the left leaves the top band and enters the bottom one, the loop the last line describes,
  with the "Loop" label at its foot. A state is a mono label with the square the status page draws (filled
  for verified, a square in a square for a mechanism the tester verified), drawn with borders so it
  survives forced colours. Below 34rem of the figure's width the bands and the bracket are left out and
  it is a ruled list, the module a hairline tag under the name. A module name carries a break
  opportunity after each underscore, so a long one wraps at its own seams. The list keeps reading order
  from the bottom up. No skew, fill, light or motion.
- **The kicker** (`.sx-kicker`) is the mono label of a section or a figure, reads the label tokens and
  wraps onto a second line, label above name, when the figure is too narrow for both on one (320px at 200
  percent text). The roadmap, the status page and the timeline import `docs-visuals.css` for it and for
  nothing else.

### Motion

- Hover and state changes take 180ms in the chrome (`--sx-dur`, which is `0s` under reduced motion); reveals take 600 to 900ms; everything uses `--sx-ease`.
  Landing blocks below the fold fade and rise once as they enter, through one shared observer.
  Layout is never animated. Nothing glows, and nothing loops on its own.
- Maze and battery figures draw only the agent's trail and its finished route.
- The landing's maze hero plays its sequence (the agent's trail, the goal, the direct route)
  three times and stops on the finished picture. A Pause button stops it at any point, and it
  also pauses while it is mostly off-screen or the tab is hidden. Elsewhere, figures move on
  hover, focus or a button, or play when they come into view, and anything that runs longer than
  five seconds has a Pause button. The figures that `components/docs/Figure.astro` draws (the stage arc,
  the release flow, the role lanes, the evaluation pipeline, the determinism tiers and the layer stack)
  are the exception: they draw their finished picture and nothing in them moves.
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
