# Psyche docs site

The documentation site of Psyche, live at <https://cagancaliskan.github.io/psyche/>. This file is for a
contributor who needs to change it.

Read [CONTRIBUTING.md](../CONTRIBUTING.md) first. Site work is builder work under it, and every sentence
on the site is read against rule 1 (claims discipline) and the
[disclosure policy](../docs/research/disclosure-policy.md). Public prose says "verified", never "proven".

- [What the site is](#what-the-site-is)
- [How a build works](#how-a-build-works)
- [Commands](#commands)
- [Design language: neural cartography, in colour](#design-language-neural-cartography-in-colour)
- [Component inventory](#component-inventory)
- [Checks](#checks)
- [CI](#ci)
- [Rules for a change](#rules-for-a-change)
- [Credits](#credits)

"Stage 1" and "stage 2" are the project's stages (the substrate, spiking cognitive maps). "Staging" is
the step that copies governed sources into the site's input. The two are unrelated.

## What the site is

Astro with Starlight is the documentation shell. React runs three interactive pieces (the "now"
readout, the timeline, the battery explorer); everything else is static Astro and CSS. The build writes
plain HTML to `dist/`, which GitHub Pages serves under `/psyche/`. Every dependency is pinned to an
exact version in `package.json`, which is where the versions of Astro, Starlight and React are; ask the
project lead before adding one.

The site holds no figures of its own. Its documentation pages are governed documents, staged from the
repository. Its hand-written pages carry prose of their own, which lives only in `src/pages/*.astro`,
`src/components/`, and the files of `src/lib/` that hold wording (`battery.ts`, `seo.ts` and
`pageChrome.ts`, the footer's labels and links, among them). `tools/publish/check_copy.py` reads all of
it for counts, claims and language, under the same rules as the docs. The hand-written pages read every
number, date and status from staged copies of `tools/ledger.json` and `tools/research_plan.json`. A page
reads a count, a date or a status. It never types one.

| Route | Source | What it is |
|---|---|---|
| `/` | `src/pages/index.astro` | Landing page |
| `/roadmap/` | `src/pages/roadmap.astro` | The phases and gates of stage 2 on one timeline |
| `/battery/` | `src/pages/battery.astro` | The test battery's paradigms, one sheet each |
| `/status/` | `src/pages/status.astro` | The substrate's captured test run and its bricks |
| `404.html` | `src/pages/404.astro` | The page for an address that does not exist |
| `/progress.xml` | `src/pages/progress.xml.ts` | Atom feed of the progress page |
| `/blog/` | `src/pages/blog/index.astro` | The blog's index: every published post, newest first |
| `/blog/<slug>/` | `docs/blog/<slug>/index.md` | A post, staged into `src/content/docs/blog/` with its images |
| `/blog.xml` | `src/pages/blog.xml.ts` | Atom feed of the blog |
| `/admin/` | `public/admin/` | The blog's editor (Sveltia CMS, loaded pinned from unpkg); not a page of the site |
| every other route | `docs/publish.json` | A governed Markdown document, staged into `src/content/docs/` |

- Folders: `public/` (icons, `og.png`, manifest, `robots.txt`), `scripts/` (checks and drawing tools),
  `src/diagrams/` (committed drawings), `src/assets/brand/` (copies of the two wordmarks in `brand/`).
- `astro.config.mjs` sets `base: '/psyche'`, `trailingSlash: 'always'`, the Starlight options and four
  component overrides (`PageTitle`, `Footer`, `Search`, and `SocialIcons`, which puts the blog link
  before the GitHub link in the header and the phone menu). `src/routeData.ts` adds per-page head entries
  from `src/lib/seo.ts`. Starlight's own 404 route is off; the sidebar is the staged `sidebar.json`.
- The base is also written in `src/lib/seo.ts`, `scripts/check-budget.mjs`, `scripts/check-a11y.mjs`,
  `public/site.webmanifest`, `public/robots.txt` and `docs/publish.json` (`site_base`), and the address
  is printed on the social card (`URL_TEXT` in `tools/publish/og.py`; run `npm run og` and commit the
  three files it writes). Change them together: nothing checks that the address drawn on the card matches,
  so a stale card passes the build. Search is Starlight's Pagefind index, built by `astro build`; there is
  none in `npm run dev`.
- Node: CI uses the version in `.nvmrc`; `engines` in `package.json` gives the minimum. Tests and
  checks import `.ts` files directly, which relies on Node's type stripping. Python 3 on the PATH
  runs staging and several checks, standard library only (rule 8). Chrome or Chromium is needed by
  `npm run diagrams`, `icons`, `og` and `check:a11y` only (`--chrome PATH` or `CHROME_PATH`, else
  the usual places).

## How a build works

### Staging

`tools/publish/stage.py` (`npm run stage`) is the only way content reaches the site. It reads every
page and data file from a commit (`HEAD`, or `--rev`), never from the working tree, so one commit names
everything a build shows. It refuses to run when the plan, the ledger, the manifest or `CITATION.cff`
on disk differs from that commit, and it refuses a page whose source does. **Commit changes to governed
sources before you build.**

It writes two gitignored folders, emptied first: `src/content/docs/` (each page, with `title`,
`description` and an `editUrl` to its source on `main`, and a `GENERATED` banner) and `src/data/`
(`plan.json`, `ledger.public.json`, `sidebar.json`, `progress.json`, `stage.json`).
`ledger.public.json` is the public projection of `tools/ledger.json`, copied and never computed.
**A staged copy is never tracked:** governance and the Pages build fail if `git ls-files` shows
anything under either folder, because a tracked copy is a second, ungoverned source.

For each page, staging:

- takes the first level-one heading as the title (a manifest `title` replaces it) and refuses a page
  with none. The manifest must give a `description`: one plain sentence of 120 to 160 characters that no
  other page repeats and that holds no typed figure.
- rewrites relative links. A link to a manifest source becomes its site route (fragment kept); a link
  to any other tracked file becomes a GitHub link pinned to the staged commit; full URLs, `mailto:` and
  bare `#anchors` are left alone. Anything that will not resolve once published stops staging:
  **a dead relative link fails the build.**
- replaces each `mermaid` fence with its committed drawing (see Diagrams).
- builds the sidebar: "Start here" first (Home, the manifest section of that title, then the
  hand-written pages in `CUSTOM_PAGES`), then the other manifest sections in order. A hand-written
  page's label may not be, or contain, a staged document's title (`tools/publish/test_core.py`).

**What is never published.** `docs/publish.json` is the only list of documents that may reach the site,
and its `never_publish` list names what may not. A page is staged only if the guard (`publishable_guard`
in `tools/publish/core.py`) accepts it: Markdown, in the commit and unchanged on disk, not under
`never_publish`, not skipped by the ledger's claim check, in neither quarantine list of
`tools/ledger.json`, with no ignore pragma. A document not in the manifest is not on the site.

### Generated blocks

`README.md`, `MOC.md`, `docs/research/**` and every manifest page can hold blocks that
`python3 tools/publish/render_plan.py --write` fills from `tools/research_plan.json`: the status line,
the phase, layer and gate tables, the gantt, the gate flow, deadlines, commitments and the progress log.
The ids and marker syntax are at the head of `render_plan.py`. Never edit inside a block and never type
a plan date: change the plan, run `--write`, commit. `--check` fails on a stale or missing block.

### Diagrams

The governed Markdown keeps its `mermaid` fences, which GitHub draws; the site draws none in the
browser. `npm run diagrams` (`scripts/render-diagrams.mjs`) draws each fence once in Chrome, strips it
to geometry and classes, and writes `src/diagrams/<key>.svg`; staging puts the SVG inline in a
`.sx-diagram` figure. The key hashes the render script and the fence. `python3 tools/publish/diagrams.py
--check` (governance runs it; `npm run check:diagrams` is its shortcut) fails on a fence with no
current drawing, a drawing with no fence, or an SVG that is not the plain drawing the site may inline.
Run `npm run diagrams` and commit `src/diagrams/` after changing a fence, after `--write` moves a date
in the gantt or gate flow, or after editing the script. The labels are measured in Martian Mono at the
size the script sets, so the stylesheet may repaint a drawing but never changes its face or size; a
change to either is a change to the script, followed by `npm run diagrams`. No check sees a stylesheet
that does otherwise: the drawings stay valid and the labels no longer fit. It installs Mermaid and
`puppeteer-core`, at pinned versions, into `node_modules/.cache/psyche-diagram-tools`
(`DIAGRAM_TOOLS_DIR` moves it).

### The social card, the progress feed, dates

- **Card.** `public/og.png` names the active stage, so it is drawn, never edited. `npm run og`
  (`scripts/make-og.mjs`) takes its text from `tools/publish/og.py --card` (from `program` in the
  ledger), fills `scripts/og-card.html` and has Chrome draw 1200 by 630. It writes
  `brand/psyche-social.png`, `brand/psyche-social.json` (the line, alt text and sha256) and `public/og.png`
  (a byte copy). Commit all three after any change to `program`, the template, the wordmark or the card
  text in `og.py`. `npm run icons` draws the PNG icons in `public/` from `brand/psyche-icon.svg`.
- **Feed.** `render_plan.progress_events` derives the plan's public events once; the progress page's
  table and `src/pages/progress.xml.ts` (Atom 1.0, through `src/lib/feed.ts`) both come from that list.
  The feed is dated by the events' days, never the build, is not in the sitemap, and is linked from
  every page's head. A decided gate shows its date and next step only, never a verdict or a criterion
  (D-034). Feed ids are tag URIs built from the host, the year and the path below the base, so they are
  the same on every build and change if the host or the base path ever does.
- **Blog.** A post is a folder of `docs/blog/` (the format and the two ways to publish are in
  [`docs/blog/README.md`](../docs/blog/README.md)). `tools/publish/blog.py` reads each one from the
  commit being staged, holds its front matter to a strict allowlist (title, day, a description of 120
  to 160 characters, tags from one list, author, revision day, draft) and its folder to images only,
  refuses an SVG that could run code, and passes the post through the same guard as a docs page.
  `stage.py` writes it to `src/content/docs/blog/<slug>/` with its images and with `prev` and `next`
  set to the neighbouring posts, and writes the published posts, newest first, to
  `src/data/blog.json`, which the index, the landing page's latest posts and `src/pages/blog.xml.ts`
  (through `src/lib/blog.ts`) read. A draft is never staged. The feed is dated by the posts' own days.
  Each post's head carries its days, author and tags and a BlogPosting (`src/lib/seo.ts`).
- **Editor.** `public/admin/` holds the editor's page and its configuration. It never writes to
  `main`: every save is a branch `cms/posts/<slug>` and a pull request, and it shows no publish
  control, so a post is published by merging that pull request on GitHub once the required checks
  pass. Its page is noindex, sends no referrer, carries a content security policy whose only script
  source is the pinned version of the editor, and loads that version's one script with an integrity
  hash; `scripts/check-seo.mjs` fails the build if any of that goes, and the accessibility,
  budget and sitemap checks leave the editor out, since it is not a page of the site.
- **Dates.** The sitemap's `<lastmod>` and the footer's "Last updated" are the date of the last commit
  that touched the files a page is made from (`scripts/sitemap-lastmod.mjs`): a docs page's source, or a
  hand-written page's file, imports and data. With no history, or a shallow clone, no date is written;
  the build date is never used.

## Commands

Run in `website/` after `npm ci`. From the repository root, `make site` runs `npm ci` then
`npm run dev`, so it stages from the last commit. The other `make` targets are in CONTRIBUTING.md.

| Command | What it does |
|---|---|
| `npm run stage` | Stage pages and data from `HEAD` (`stage.py --target site`) |
| `npm run dev` | Stage, then `astro dev`. Staging happens once, at start: after committing a governed change, restart. `-- --port N` picks the port |
| `npm run build` | `check:og`, `stage`, `astro check`, `astro build`, `check:spacing`, `check:refs`, `check:budget`, `check:seo`; stops at the first failure |
| `npm run preview` | `astro preview` over `dist/`; build first. Search works here |
| `npm test` | Node's test runner over the unit tests in `src/lib/` and `scripts/` |
| `npm run diagrams`, `icons`, `og` | Draw the diagrams, the PNG icons, the social card (Chrome) |
| `npm run check:og`, `check:spacing`, `check:refs`, `check:budget`, `check:seo` | One check each, as `build` runs them; all but the first read `dist/` (see Checks) |
| `npm run check:diagrams` | `diagrams.py --check` |
| `npm run check:a11y` | axe-core at WCAG 2.2 AA over `dist/` (Chrome; not part of `build`) |

## Design language: neural cartography, in colour

The site is set as a drafting sheet, in the language its drawings already speak: square corners,
hairline edges, flat colour, rulers and registration marks, and no gradient, glow, shadow, pill or
tinted card. Colour is drawn the way the illustrations draw it: a rule in a hue, a square swatch before
a label (as in a map's legend), a line, a solid mark. Hairlines separate rows and edge blocks.
Decorative numbering is gone; real sequences (phases P0 to P5, gates A to D, paradigms T1 to T5) keep
their numbers.

### Tokens and hues (`src/styles/global.css`)

Components use tokens, never a raw colour. Dark is `:root`; light is `:root[data-theme='light']`.
Starlight's `--sl-color-*` point at the same values (`--sl-color-white` is the text ink,
`--sl-color-black` the canvas, in both themes).

| Variable | Role |
|---|---|
| `--sx-agent` (signal mint) | Stage 1, the agent and its route, what is current: "now", the focus ring |
| `--sx-structure` (map blue) | Stage 2 and structure: walls, axes, links in prose, the primary action |
| `--sx-violet` | The project as a whole and the stages still to come |
| `--sx-spike` (amber) | Rare emphasis: today, the gate the line is waiting on, cautions |
| `--sx-stage` | The hue of the page's own stage: violet on the project's pages, mint on stage 1 pages, blue on stage 2 pages |
| `--sx-surface`, `--sx-surface-2` | A block on the canvas; a block raised or inset one step further, each told by its edge |
| `--sx-arena`, `.sx-arena` | The flat night plate the maze and the battery's drawings sit in, dark in both themes: the class sets the dark tokens on itself |
| `--sx-muted`, `--sx-hairline` | Secondary text; rules and edges |
| `--sx-rule-strong` | The edge of a control, the mark of a state: 3:1 against canvas and surfaces (WCAG 1.4.11) |
| `--sx-grid` | The faint drafting grid behind the hero's mark |
| `--sx-r-xs` to `--sx-r-l`, `--sx-r-pill` | Corners: 2px everywhere, so a control does not cut the hand and nothing is a pill |
| `--sx-space-section`, `--sx-pad-panel`, `--sx-pad-card` | Space between the landing page's sections, inside a block and inside a smaller block |
| `--sx-lab-font`, `--sx-lab-weight`, `--sx-lab-case`, `--sx-lab-size`, `--sx-lab-track` | The label: sentence case in the reading face at weight 600 |
| `--sx-dur`, `--sx-dur-bar`, `--sx-dur-line`, `--sx-ease` | Durations of chrome state changes; the curve |

`--sx-gutter` completes the set. A colour change must also reach the copies of values: `CODE_INKS` in
`astro.config.mjs`, `THEME_COLOR` in `src/lib/seo.ts` and `public/site.webmanifest`. The brand's own
files (`brand/`, the PNG icons and `scripts/og-card.html`) keep the brand canvas, `#05070d`, and the
mark's bowls are never recoloured.

### Type (`src/styles/fonts.css`, `docs.css`)

Three self-hosted variable faces from Fontsource: **Unbounded** for display (weights 200 to 400),
**Instrument Sans** for reading, the interface and labels, **Martian Mono** for data (an id, a day, a
count) and code. `fonts.css` gives each a stand-in (a local Arial or Courier New scaled to the web
font's metrics) so the swap moves nothing; measure again, and update the table at its head, if a face
changes. Faces are not preloaded (see `src/routeData.ts`). Docs body text is 1.0625rem at a line height
of 1.7 in a 35rem measure, in `rem` and not `ch` because Instrument Sans has a wide zero.

### Blocks, labels, links (`global.css`, `docs.css`)

- **Blocks**: a surface fill and a hairline edge with square corners; a block that stands for a stage or
  a state carries a rule in its hue along its top edge. Lists are rows on rules. The landing page sets
  some sections on full-bleed bands of the raised surface and its battery section in the arena.
- **Labels** are legend entries: a square swatch in the hue, then the words. A state's marker keeps
  its shape (a ring, a disc or a square), so colour is never the only cue. An id (P0, Gate A, T1) is
  mono data.
- **Buttons**: the primary action is a solid map-blue rectangle; the others are outlined.
- **Links** in prose: the map blue over a 1.5px underline that takes the stage hue on hover and focus.
  **Focus** is a 2px signal outline everywhere. **Asides** are a 4px bar in the aside's hue (note blue,
  tip mint, caution and danger amber) with a coloured title; a danger adds a full-strength edge, so
  colour is not the only difference. The sidebar's group headings carry a square in their stage's hue,
  and the current page a bar in the stage hue.

### Title block and footer title block

`chrome/PageTitle.astro` draws the strip above each title (`.sx-pt`, `docs.css`): the stage, section and
the stage's state from the ledger, or the sidebar's group name, or "Error 404", as legend entries. It
sets `data-stage` (1, 2 or 0) from the page's section, which gives the page its hue; three Start here
pages that show one stage's work (the timeline, the battery, the substrate's status) take that stage's.
A 3px rule in the stage's hue runs over the strip and the title, and a hairline closes the block.
`chrome/Footer.astro` draws the title block (`.sx-foot`, `global.css`): a block with the page's facts
as cells (its stage and state, on stage 2 pages the next gate), then the repository's links and the
page's date. Both read the sidebar, ledger and plan through
`src/lib/pageChrome.ts`, type nothing per page, leave out a cell with no data, and are excluded from
search.

### Tables, code, diagrams, figures

- **Tables** (`docs.css`): a block on the surface, the header row on `--sx-surface-2` in the label
  recipe, a hairline between rows. `scripts/table-region.mjs` wraps every Markdown table in
  `<div class="sx-table" role="region" tabindex="0" aria-label="Table: ...">`, named by its caption or
  nearest heading, so a table that scrolls can be scrolled by keyboard (WCAG 2.1.1);
  `chrome/TableRegions.astro` removes role, name and tab stop from a region whose table fits. A 2px
  structure bar at the edge with more content is the cue that it scrolls. **Write tables in Markdown:**
  a raw HTML table is not wrapped, so it is unstyled and unreachable by keyboard.
- **Code frames** (`docs.css`, `codeTheme` in `astro.config.mjs`): a block on the surface, a caption
  strip with the title or "Terminal", an always-visible copy button. Syntax uses three inks (comments
  muted; commands, keywords and functions structure; the rest ink).
- **Diagrams** are staged SVG with geometry and classes but no colour, inside `.sx-diagram` (a block
  and a scroll box); the page's tokens paint them, so one file serves both themes.
- **Figures** under docs titles are `components/docs/` components mapped to routes in `visuals.ts`,
  framed by `Figure.astro` as a block and styled by `docs-visuals.css`. A figure lays out by its
  own width (container `sx-dv`), not the window's, and does not move.

## Component inventory

Under `src/components/`.

**Top level**

- `LayersHero.astro`: the landing hero, the mark as four CSS 3D sheets beside the statement.
- `NowLine.tsx`, `Timeline.tsx` (islands), `TimelineList.astro`: the current phase and next gate, the
  phase timeline and its list form for narrow screens. Used by the landing, `/roadmap/` and the research
  roadmap's figure.
- `GateStepper.astro`: gates as ruled rows, with the "next" mark moved to the reader's day by a script
  (`lib/gateClock.ts`). Used by `/roadmap/` and the research gates figure. `gateClock.ts` reads and
  writes the `data-gate-*` and `data-next*` attributes that its header comment lists, on the markup of
  `GateStepper.astro`, `TimelineList.astro` and the footer's next-gate cell (`chrome/Footer.astro`): keep
  them when you change that markup. No test covers them.
- `BatteryExplorer.tsx` (island): the battery page, an index and one sheet per test.
- `BrickBoard.astro`, `BrickTable.astro`: the status page's brick board; the table sets ARIA roles in
  the markup because its rows are drawn as grids.

**`battery/`**: `BatteryTeaser.astro` (one ruled row per test with a small picture; landing and the
test-battery figure), `Pictures.tsx` (server-rendered SVG drawings of the paradigms: illustrations,
never a model or a result; used by the teaser and the explorer).

**`brand/`**: `PMark.astro` (the Psyche mark; hero), `StageGlyph.astro` (the mark with one stage lit;
`landing/StageLedger.astro`).

**`chrome/`** (every page unless noted): `PageTitle.astro`, `Footer.astro` and `Search.astro` are the
Starlight overrides. `Footer.astro` copies Starlight's footer markup and adds the title block;
`Search.astro` copies Starlight's search with the key cap drawn, not written (WCAG 2.5.3).
`NextGateClock.astro` and `TableRegions.astro` are scripts run from the footer (the first turns the
next-gate cell into "decision pending" once its day has passed). `NearestPage.astro` is the 404 page's
"nearest filed page" row.

**`docs/`**: `Figure.astro` (the frame), `visuals.ts` (route id to figure, read by `PageTitle.astro`)
and one figure per mapped page: `EvaluationPipeline` (research overview), `StageArc` (origins),
`RoadmapVisual`, `GatesVisual`, `BatteryVisual`, `DeterminismTiers` (engineering), `ReleaseFlow`
(disclosure policy), `SubstrateOverview`, `LayerStack` (architecture), `RoleLanes` (methodology). Four
of them reuse components above.

**`landing/`** (all used by the landing page): `SectionHeader.astro` (a section opening), `StageLedger.astro`
(stages as a ruled table), `MazeFigure.astro` (Fig. 1, from `lib/maze.ts` and `lib/battery.ts`),
`HowBuilt.astro`, `PublicWithheld.astro`, `CiteContact.astro` (its DOI is typed and must equal
`CITATION.cff`; `test_cited_doi` in `tools/publish/test_core.py` checks it), `CaliperRail.astro` (the
measuring rail in the gutter) and `SubstrateReadout.astro` (the captured-run figures, also used by
`/status/` and the substrate overview's figure).

**`src/lib/`**: `plan.ts` (date logic over the plan; "today" is passed in), `today.ts` (`todayIn`, apart
so a page script loads only it), `gateClock.ts` (brings server-rendered gates to the reader's day),
`ledger.ts` (types of the public projection), `status.ts` (readout and brick rows, build and meaning
axes kept apart), `pageChrome.ts` (strip and footer logic), `lastUpdated.ts` (the footer date),
`seo.ts` (origin, base, `NOT_FOUND`, theme colours, JSON-LD, per-page head), `feed.ts` (Atom
serialiser), `maze.ts` (deterministic grid geometry and seeded walks), `battery.ts` (the paradigms'
data), `sheet.ts` (wall outlines, grids, rulers), `url.ts` (`withBase`). `battery`, `feed`, `maze`,
`pageChrome`, `plan`, `seo`, `sheet` and `status` have a unit test beside them;
`searchOverride.test.ts` tests `Search.astro`.

## Checks

`npm run build` stops at the first failure.

| Check | Fails when |
|---|---|
| `check:og` | The card names a stage other than the ledger's active one, the sidecar does not describe `brand/psyche-social.png` byte for byte, or `public/og.png` is not its copy |
| Staging | A governed source differs from `HEAD`; the guard refuses a page; a heading or description is missing; a relative link is dead; a fence has no current drawing or a drawing no fence |
| `astro check` | Type or Astro errors. Warnings and hints do not fail it |
| Link validation | `starlight-links-validator`, during `astro build`, finds an invalid internal link or fragment in a Markdown page (`errorOnRelativeLinks` is off: staging has rewritten them). It does not read the hand-written pages: a dead root-relative link there passes, so build those with `withBase()` and check them yourself |
| `check:spacing` | The built landing, roadmap, battery or status page has text glued to an inline element or an expression's output, or a number to a word; or any figure caption has two words run together |
| `check:refs` | A page has a `<use href>`, `url(#...)`, `aria-labelledby`, `aria-describedby`, `aria-controls` or `<label for>` pointing at an id it lacks |
| `check:budget` | See below |
| `check:seo` | See below |
| `npm test` | A unit test fails. CI runs it before the build |
| `check:diagrams` | See Diagrams. Governance runs it |
| `check:a11y` | See below. CI runs it after the build |

**Budgets.** `scripts/check-budget.mjs` counts, per built page, the JavaScript loaded on arrival
(scripts, preloads, islands, and their imports followed to the end, dynamic ones with a literal address
included) and the CSS linked or inline, each file gzipped on its own at level 9; fonts, images and the
404 page are not counted. A page over its line in `PAGE_BUDGETS` fails, as does a chunk in `dist/_astro`
named for Mermaid, KaTeX, Cytoscape or d3, or a script or stylesheet from another origin. A budget
is 3 percent above the size measured when it was set, rounded up to the next 100 bytes, so another
zlib build does not trip it and real growth does. A page with no line falls under `DEFAULT_BUDGET`,
the largest of any docs page without an island. To raise one, change the number and say why in the
commit; a new page that needs more gets its own measured line.

**SEO and the feed.** `scripts/check-seo.mjs` reads `dist/`. Per page, the 404 page included, it fails
on: other than one title, canonical address and description (120 to 160 characters, unique); `og:` or
`twitter:` tags that differ from the page's; an image that is not a PNG of its stated size; a missing
theme colour, icon or manifest; a `robots` meta anywhere but the 404 page (which must be `noindex`, with
its own title, description and address); structured data off the landing page and the blog posts; and a link written with
the site's whole address (which the link validator treats as external) that leads to nothing or to a
missing id. For the site: a `robots.txt` that does not allow everything and name the sitemap; a bad
manifest; a sitemap that omits a page, lists a non-page or repeats an address, or a `<lastmod>` that is
missing (with history), unreadable or in the future. For the feeds: either one not named once in every
head; for the progress feed, not Atom 1.0, an `updated` other than the newest event's day, an author
other than `CITATION.cff`'s, or entries that are not one per plan event, newest first; for the blog's,
not Atom 1.0, an `updated` other than the latest day a post was published or revised, or entries that
are not one per built post, newest first. A blog post must carry its `article:` tags and one
BlogPosting that matches its head; no other page but the landing page carries structured data. The
editor (`dist/admin/`) is left out of the page rules and must be noindex, send no referrer, and carry
one content security policy (`default-src`, `object-src`, `base-uri` and `form-action` set to
`'none'`, and a `script-src` that is exactly the pinned editor path) and one script of that same
version with an integrity hash.

### Accessibility check

`scripts/check-a11y.mjs` serves `dist/` on a free local port and runs axe-core (WCAG 2.0, 2.1 and 2.2,
levels A and AA) over every page it finds, the 404 page included, at desktop and phone width, light and
dark, reduced motion on. On `research/gates/` it also opens what a reader opens by clicking: the search
dialog with results, the phone menu and the phone contents list. It exits 1 on a serious or critical
violation and on anything it cannot audit (a page that does not answer 200, a state that will not open,
a run where axe tested fewer than 20 rules). Lesser findings, and rules axe cannot decide, are listed
and never fail it. It exits 2 when it could not set itself up (no Chrome, a failed install), which says
nothing about the site; CI runs it once more on a 2. Flags: `--chrome PATH`, `--json FILE`, `--port N`
and `--only /,research/gates/,404.html` for a quick look.

It installs `axe-core` and `puppeteer-core` with `npm ci` into `node_modules/.cache/psyche-a11y-tools`
(`A11Y_TOOLS_DIR` moves it), at the exact versions `scripts/a11y-tools/package.json` names, with their
own dependencies as `package-lock.json` locks them, so a release of one of those cannot change the
check. They are not site dependencies. `scripts/a11y-tools.test.mjs` (in `npm test`) fails if a version
is not exact, the lockfile disagrees or lacks a hash, or the script types a version.

To keep it passing, a control's accessible name must contain the text drawn on it (WCAG 2.5.3): that is
why `Search.astro` is an override and why a battery row's picture is `aria-hidden`.
`src/lib/searchOverride.test.ts` applies the override's three edits to the installed Starlight file and
fails when the result is not `Search.astro`: after a Starlight upgrade, copy the new file and make the
edits again, and compare `Footer.astro` with Starlight's by eye.

axe cannot decide text contrast over gradients, pseudo-elements and images: after changing a colour
token or surface, measure it from pixels. After changing the chrome, walk the keyboard through the
header, sidebar, contents list, a scrolling table, the footer and the 404 links at desktop and phone
widths, and look at the page with forced colours on.

## CI

`.github/workflows/pages.yml` builds and deploys the site. It runs on a push to `main` that touches
`docs/`, `website/`, `tools/`, `README.md`, `MOC.md`, `CITATION.cff` or the two workflow files, on every
pull request (no path filter, because `build` is a required check) and by hand. Four jobs:

1. **`governance`** calls `governance.yml`: the commit gate, plan, diagram and social-card checks, the
   tool suites, the claims check for other surfaces, no tracked staged content, every action pinned by
   commit SHA. Nothing deploys past a red gate.
2. **`build`** checks out the full history (for the dates), sets up the Python that `pages.yml` pins
   and Node from `.nvmrc`, runs `npm ci`, `npm test`, `npm run build` and a no-tracked-staged-copy
   step, uploads the built pages for the disclosure scan and `dist/` as the Pages artifact, and runs
   `check-a11y.mjs` last (15 minutes at most, one retry on exit 2), so nothing it installs can
   change what is published.
3. **`disclosure`** scans those built pages against the private denylist, decoded from a base64 secret
   into a file only the runner reads. On a pull request without the secret it warns and skips;
   elsewhere a missing secret fails the run.
4. **`deploy`** publishes `dist/` to GitHub Pages: only on `main`, never for a pull request, after
   `build` and `disclosure`.

A newer push replaces a pull request's run in flight; a deploy is never cancelled. `tests.yml` runs the
Python suites, not the site. `links.yml` runs lychee weekly and by hand over the repository's documents
and the staged docs pages (not the hand-written pages). `codeql.yml` scans the code. Dependabot proposes
weekly updates for the actions and the npm packages here: minor and patch in one grouped pull request, a
major alone, TypeScript held on its current major because `astro check` does not support the next.

## Rules for a change

- Never edit or commit `src/content/docs/` or `src/data/`; change the governed source and stage again.
  Commit governed sources before `npm run build` or `make site`.
- Write tables in Markdown. Use relative links to files that exist.
- Never type a count, a test total, a date or a status; read it from the staged projection or plan.
  `tools/publish/check_copy.py` reads `src/`, `astro.config.mjs` and this folder's Markdown for counts,
  claims and language.
- Keep text and an `{expression}` or inline element on one line, or end the line with `{' '}`: Astro
  drops a line break next to them and runs the words together. `check:spacing` fails on it.
- A component that a hand-written page imports must be in that page's source list in
  `scripts/sitemap-lastmod.mjs`, or its date will not move; `npm test` fails if it is missing.
- Load nothing from another origin; ship no diagram or maths library to the browser.
- The status page's meaning-column wording holds only while the meaning bar is open and no brick has an
  earned verdict. `status.test.ts` fails when that stops being true: it is the cue to rewrite the wording.
- After `program` changes in the ledger, run `npm run og`. After a diagram or plan date changes, run
  `npm run diagrams`. Commit what they write.
- Drawings of the paradigms (`lib/maze.ts`, `lib/battery.ts`) are illustrations, not results or a model.
  Say so wherever one appears.
- A docs page belongs to the stage named by the first segment of its route: `substrate/` is stage 1 and
  `research/` is stage 2 (`STAGE_OF_SECTION` in `src/lib/pageChrome.ts`, with the stage numbers also
  fixed in `tools/publish/og.py`). A new route prefix or a new section of `docs/publish.json` needs an
  entry there. The "Start here" section is first in the manifest, once, and none of its pages uses a
  stage's route prefix. A section title names no program state; the ledger holds it. `npm test` fails on
  each of these.
- Three bars no script checks. Nothing scrolls sideways at 320px wide with text at 200 percent; the
  accessibility check runs at one desktop and one phone width only. Anything that moves for more than five
  seconds has a Pause control (WCAG 2.2.2). A state is never told by colour alone (WCAG 1.4.1): its marker
  differs in shape or carries a label, and is drawn with borders so that it survives forced colours.

## Credits

[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) is the one list to keep current: the three
typefaces and their licence, the components adapted from the 21st.dev catalog, and the npm packages,
with the two copied Starlight files under their MIT notice.

To credit a catalog component you adapted:

1. Port it to the site's tokens in plain CSS, Astro or a few lines of script, leaving its libraries out
   and writing the words yourself.
2. Credit it in a comment next to the code: the component's name and its author's catalog username on
   one line, so a search finds them, and what you took (its anatomy, or an idea only).
3. Add a row, in alphabetical order, to the table in section 2 of `THIRD_PARTY_NOTICES.md`: component,
   author, what it was adapted for, and every file that credits it (paths under `website/src/`).

The notices state no licence for the catalog components and assume none; they name them so the original
and its terms can be found.
