# Psyche site

The site of Psyche, live at <https://psyche.cagancaliskan.com/>: its front pages and its
documentation. This file is for a contributor who needs to change it.

Read [CONTRIBUTING.md](../CONTRIBUTING.md) first. Site work is builder work under it, and every sentence
on the site is read against rule 1 (claims discipline) and the
[disclosure policy](../docs/research/disclosure-policy.md). Public prose says "verified", never "proven".

- [What the site is](#what-the-site-is)
- [How a build works](#how-a-build-works)
- [Commands](#commands)
- [Design language](#design-language)
- [The documentation](#the-documentation)
- [Component inventory](#component-inventory)
- [Checks](#checks)
- [CI](#ci)
- [Rules for a change](#rules-for-a-change)
- [Credits](#credits)

"Stage 1" and "stage 2" are the project's stages (the substrate, spiking cognitive maps). "Staging" is
the step that copies governed sources into the site's input. The two are unrelated.

## What the site is

The site has two parts, both plain Astro pages drawn with the page kit (`src/kit/`): its stylesheet, a
classic script that writes the header's theme switch (a drawn icon, named for what it does: "Switch to
the light theme" or "Switch to the dark theme") and phone menu and the footer and runs the figures, a
head script that shows an orb while a page opens and between pages, and each page's markup, styles,
figure script and figure stills.

- The front pages (the home, What we're building, Experiments, About, the blog's index, its posts and
  the 404 page) are on three layouts of their own, `src/layouts/Bare.astro`, `Kit.astro` and
  `Post.astro`. The home is a scroll film drawn with three.js (`src/kit/film/`), with the site's header
  and phone menu over it in its own markup and script; the film is dark only, so it has no theme switch.
- The documentation (the home at `/developers/`, every governed document, and the `/roadmap/`,
  `/battery/` and `/status/` pages) is on `src/layouts/Docs.astro`, which puts the documentation's
  frame (its page list, "On this page", previous and next, the edit line) around a page on `Kit.astro`,
  so it has the same header, theme switch and phone menu as the front pages.
  See [The documentation](#the-documentation).

No page runs a framework in the browser: the pages are static HTML and CSS, with small scripts that
add behaviour to markup the server has already written. "For developers", the fourth item of the
header's menu (What we're building, Experiments, Blog, For developers, Contact; at 860 px and under they
sit behind "Menu") and a link in the footer, leads to `/developers/`, and is marked as the current item
there and on every page of the documentation; the blog's posts link to some documents. The build writes plain HTML to `dist/`,
which GitHub Pages serves at the root of `psyche.cagancaliskan.com`. Every dependency is pinned to an
exact version in `package.json`, which is where the versions of Astro and three.js are; ask the project
lead before adding one.

The files under `src/kit/` are brought in from the project lead's design files, which are kept outside
this repository, by a tool that is not in it either: a hand edit there is overwritten by the next
import. A change to a front page's markup, styles, figures or words is a change to the design; ask the
project lead. The front pages' files in `src/pages/` and their layouts only put the kit's parts
together. The documentation's frame (`src/layouts/Docs.astro`, `src/components/devdocs/`) and its
hand-written pages are written here, to the markup the design's documentation pages use, because their
content comes from the repository's Markdown and data at build time; the documentation's stylesheet and
script come from the design like the rest of `src/kit/`.

The site holds no count, date or status of the project's work of its own. Its documentation pages are
governed documents, staged from the repository. Its hand-written pages carry prose of their own, which
lives only in `src/pages/*.astro`, `src/layouts/`, `src/components/`, `src/kit/` (the pages' words, in
`.astro`, `.js` and `.svg` files) and the files of `src/lib/` that hold wording (`battery.ts`, `seo.ts`,
`head.ts`, `devdocs.ts` and `walkthrough.ts` among them). `tools/publish/check_copy.py` reads all
of it for counts, claims and language, under the same rules as the docs (it does not read `.css`). The
documentation's hand-written pages read every number, date and status from staged copies of
`tools/ledger.json` and `tools/research_plan.json`. A page reads a count, a date or a status. It never
types one, with one exception today: the figure on the blog's index draws the three posts and a fixed
day written into its script (`src/kit/pages/blog/page.js`); it does not read `src/data/blog.json`. The
list of posts under it is read from `blog.json`.

| Route | Source | What it is |
|---|---|---|
| `/` | `src/pages/index.astro` | The home page: the scroll film, on `layouts/Bare.astro` |
| `/what-were-building/` | `src/pages/what-were-building.astro` | What we're building, on `layouts/Kit.astro` |
| `/experiments/` | `src/pages/experiments.astro` | The five experiments, on `layouts/Kit.astro` |
| `/about/` | `src/pages/about.astro` | About and contact, on `layouts/Kit.astro` |
| `/developers/` | `src/pages/developers.astro` | The documentation's home: where to start, then every page of the documentation list by group, on `layouts/Docs.astro` |
| `/roadmap/` | `src/pages/roadmap.astro` | The phases and gates of stage 2 on one timeline, on `layouts/Docs.astro` |
| `/battery/` | `src/pages/battery.astro` | The test battery's paradigms, stepped through one picture at a time, on `layouts/Docs.astro` |
| `/status/` | `src/pages/status.astro` | The substrate's captured test run and its bricks, on `layouts/Docs.astro` |
| `404.html` | `src/pages/404.astro` | The page for an address that does not exist, on `layouts/Kit.astro` |
| `/progress.xml` | `src/pages/progress.xml.ts` | Atom feed of the progress page |
| `/blog/` | `src/pages/blog/index.astro` | The blog's index: every published post, newest first, on `layouts/Kit.astro` |
| `/blog/<slug>/` | `docs/blog/<slug>/index.md` | A post, staged into `src/content/docs/blog/` with its images, read as the `posts` collection (`src/content.config.ts`) and rendered by `src/pages/blog/[slug].astro` on `layouts/Post.astro` |
| `/blog.xml` | `src/pages/blog.xml.ts` | Atom feed of the blog |
| every other route | `docs/publish.json` | A governed Markdown document, staged into `src/content/docs/`, read as the `docs` collection and rendered by `src/pages/[...slug].astro` on `layouts/Docs.astro` |

- Folders: `public/` (icons, `og.png`, manifest, `robots.txt`, and in `public/brand/` the two wordmarks
  the kit's header and the film's header load), `scripts/` (checks and drawing tools), `src/diagrams/`
  (committed drawings), `src/assets/fonts/` (the box-drawing face), `src/layouts/` and `src/kit/` (the
  pages' design), `src/components/devdocs/` (the documentation's frame).
- `astro.config.mjs` takes `site` and `base` from `src/lib/seo.ts`, sets `trailingSlash: 'always'`,
  Markdown code without syntax colour (`markdown.syntaxHighlight: false`), prefetching of every link to
  the site's own pages, the repository root for the "Last updated" dates, and three integrations: the
  table regions and the post figures (two steps of the Markdown processor, `scripts/table-region.mjs`
  and `scripts/post-figures.mjs`) and the sitemap. Every page gets its whole head from `src/lib/head.ts`
  (`pageHead`, which ends with `seoHead()` from `seo.ts`): the titles and descriptions of the
  hand-written pages are its `PAGES` table, a document's and a post's are their front matter.
- **Where the site is served.** GitHub Pages serves it at `psyche.cagancaliskan.com` because of two
  things outside this repository: a DNS record (`psyche` as a CNAME to `cagancaliskan.github.io`) and
  the custom domain in the repository's Pages settings, with HTTPS enforced. The deploy is the
  workflow's artifact, so a `CNAME` file here would do nothing. While the custom domain is set,
  GitHub redirects the project address the site used before, `cagancaliskan.github.io/psyche/`.
- The address and the base are defined in `src/lib/seo.ts` (`ORIGIN`, `BASE`). The base is also written
  in `scripts/check-budget.mjs`, `scripts/check-a11y.mjs`, `public/site.webmanifest`,
  `public/robots.txt` and `docs/publish.json` (`site_base`). The address is also written in
  `.github/workflows/links.yml`, the issue templates, `CITATION.cff`, `SECURITY.md`, the root
  `README.md` and the governed pages that link to the site, and it
  is printed on the social card (`URL_TEXT` in `tools/publish/og.py`; run `npm run og` and commit the
  three files it writes). Change them together: nothing checks that the address drawn on the card matches,
  so a stale card passes the build. The site has no full-text search: the documentation's page list
  and its home each have a filter that matches the pages' titles, descriptions and group names, not
  their text.
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
(`plan.json`, `ledger.public.json`, `docs.json`, `progress.json`, `blog.json`, `stage.json`).
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
- builds the documentation list, `docs.json` (`build_docs_index`): "Start here" first (the documents of
  the manifest section of that title, in manifest order, then the hand-written pages in `CUSTOM_PAGES`),
  then the other manifest sections in order. A document item carries its slug, the title the page shows
  and the manifest's description; a hand-written page item carries its route and title, and its
  description is the one `src/lib/head.ts` `PAGES` gives that page. A hand-written page's title may not
  be, or contain, a staged document's title (`tools/publish/test_core.py`). Neither the home page nor
  the blog is in the list.

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
size the script sets, and every shape is laid out round them. The documentation's stylesheet
(`src/kit/docs/docs.css`) draws the labels in Instrument Sans, which is narrower, at one and a quarter
times the laid-out size together with the whole drawing, so a label stays inside its shape; a wider face,
or a label drawn larger than the drawing, would not. A change of the measuring face or size is a change
to the script, followed by `npm run diagrams`. No check sees a stylesheet that breaks this: the
drawings stay valid and the labels no longer fit. The script's comments still name the stylesheet that
painted the drawings before the documentation moved into the page kit (`src/styles/docs.css`): its bytes
are part of every drawing's key, so even a comment edit would rename every drawing. It installs Mermaid and
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
  (D-034). Feed ids are tag URIs built from a host, the year and a path, so they are the same on every
  build. They are made from the address the feeds began at (`TAG_SITE` in `src/lib/feed.ts`), not from
  the site's current one, so they did not change when the site moved to its own domain.
- **Blog.** A post is a folder of `docs/blog/` (the format and how to publish are in
  [`docs/blog/README.md`](../docs/blog/README.md)). `tools/publish/blog.py` reads each one from the
  commit being staged, holds its front matter to a strict allowlist (title, day, a description of 120
  to 160 characters, tags from one list, author, revision day, draft) and its folder to images only,
  refuses an SVG that could run code, and passes the post through the same guard as a docs page.
  A post is text and pictures only, which is why the guard allows a short list of HTML elements and
  refuses an SVG that could run code: anything that runs on the site is site code, and site code is
  reviewed in a pull request.
  `stage.py` writes it to `src/content/docs/blog/<slug>/` with its images and with `prev` and `next`
  set to the neighbouring posts, and writes the published posts, newest first, to
  `src/data/blog.json`, which the index and `src/pages/blog.xml.ts` (through `src/lib/blog.ts`) read.
  A draft is never staged. The feed is dated by the posts' own days. Each post's head carries its days,
  author and tags and a BlogPosting (`src/lib/head.ts`, through `src/lib/seo.ts`).
- **Dates.** The sitemap's `<lastmod>` and the "Last updated" beside a documentation page's edit link
  are the date of the last commit that touched the files a page is made from
  (`scripts/sitemap-lastmod.mjs`, read for the page by `src/lib/lastUpdated.ts`): a document's source, or
  a hand-written page's file, imports and data (for a front page: its layouts, its head, the modules the
  head reads and the whole of `src/kit/`; for a page of the documentation also its frame and
  `docs/publish.json`; a post is dated by its own folder). With no history, or a shallow clone, no date
  is written; the build date is never used.

## Commands

Run in `website/` after `npm ci`. From the repository root, `make site` runs `npm ci` then
`npm run dev`, so it stages from the last commit. The other `make` targets are in CONTRIBUTING.md.

| Command | What it does |
|---|---|
| `npm run stage` | Stage pages and data from `HEAD` (`stage.py --target site`) |
| `npm run dev` | Stage, then `astro dev`. Staging happens once, at start: after committing a governed change, restart. `-- --port N` picks the port |
| `npm run build` | `check:og`, `stage`, `astro check`, `astro build`, `check:spacing`, `check:refs`, `check:budget`, `check:seo`; stops at the first failure |
| `npm run preview` | `astro preview` over `dist/`; build first |
| `npm test` | Node's test runner over the unit tests in `src/lib/` and `scripts/` |
| `npm run diagrams`, `icons`, `og` | Draw the diagrams, the PNG icons, the social card (Chrome) |
| `npm run lines` | Draw the box-drawing face, `src/assets/fonts/psyche-lines.woff2`; `-- --check` fails if the committed file differs (no browser, no download) |
| `npm run check:og`, `check:spacing`, `check:refs`, `check:budget`, `check:seo` | One check each, as `build` runs them; all but the first read `dist/` (see Checks) |
| `npm run check:diagrams` | `diagrams.py --check` |
| `npm run check:a11y` | axe-core at WCAG 2.2 AA over `dist/` (Chrome; not part of `build`) |

## Design language

Every page follows the page kit: `src/kit/kit.css` and each page's `page.css`, and on the documentation's
pages `src/kit/docs/docs.css` as well. The tokens are at the head of `kit.css` (`--field`, `--ink`,
`--read`, `--soft`, `--quiet`, `--rule`, `--peri`, `--mint`, `--focus`, the two faces and the type
scale); dark is `:root`, light is `:root[data-theme="light"]`. A page opens dark and keeps the reader's
choice in `localStorage` (`psyche-theme`); the home fixes its own theme, dark, for the film. The kit draws
flat: no box around content, no fill behind it, no shadow, gradient or pill. Live figures start from a
baked still and pause on request, and an orb that a page opens out of gathers it in when the reader
leaves (none under reduced motion). None of this is edited here: it is the project lead's design,
imported (see the start of this file).

A colour change in the design must also reach the copies of values outside the kit: `THEME_COLOR` in
`src/lib/seo.ts` and `public/site.webmanifest`. The brand's own files (`brand/`, the PNG icons and
`scripts/og-card.html`) keep the brand canvas, `#05070d`, and the mark's bowls are never recoloured.

### Type (`src/styles/fonts.css`)

Two self-hosted variable faces from Fontsource: **Instrument Sans** for reading, the interface and
labels, **Martian Mono** for data and code. The documentation's pages also load Instrument Sans's italic
file, so a document's `<em>` is a real italic. `fonts.css` gives each face a stand-in (a local Arial or
Courier New scaled to the web font's metrics) so the swap moves nothing; measure again, and update the
table at its head, if a face changes. Faces are not preloaded.

A third face, **Psyche Lines**, follows Martian Mono in the kit's `--mono`. Martian Mono's Latin file has
no box-drawing character (U+2500 to U+257F), no triangle pointer and no leftwards or rightwards arrow, and
a code block took those from a system face at another width (Menlo's are 0.602 em against Martian Mono's
0.7), so a text diagram drifted out of column. Psyche Lines is drawn by `scripts/make-lines-font.mjs`
(`npm run lines`; `-- --check` fails if the committed `src/assets/fonts/psyche-lines.woff2` is not what the
script draws) with every glyph 0.7 em wide, and it is fetched only by a page that shows one of its
characters. A character that neither face has still falls to a system face and shifts the columns of its
line: draw that diagram in ASCII, or add the character to the script and to the `unicode-range` in
`fonts.css`, which `scripts/make-lines-font.test.mjs` keeps in step with the font. Its vertical lines run
the whole of a code block's line (1.75 em, the line height of the documentation's code blocks in
`docs.css`), so a tree's rails join from one line to the next; the script says what changes if that line
height does.

## The documentation

### The frame

`src/layouts/Docs.astro` is the documentation's frame on `Kit.astro`: the navigation of every page of the
documentation list on the left, the page's own `<main>` in the middle and, from 1100 px wide, its "On this
page" on the right. The home, `/developers/`, has no "On this page". The list is `src/data/docs.json`,
staged from `docs/publish.json` (see Staging); `src/lib/devdocs.ts` turns it into what the parts show. The
parts are in `src/components/devdocs/`: `DocsNav.astro` (the page list, the current page marked),
`DocsIndex.astro` (the home's "Where to start" and every page by group, with its description),
`OnThisPage.astro` (a page's h2 and h3), `DocPager.astro` (previous and next, over the whole list, the
three site pages included) and `DocEdit.astro` (the link to the page's source on GitHub and, beside it,
"Last updated" with the day).

The server writes all of it into the HTML, so every page reads and navigates without script; on a phone
without script the page list stands once above the text. The documentation's script,
`src/kit/docs/docs.js`, only adds behaviour to that markup: it shows the "Search pages" field and the
home's filter (both written hidden, since they work only with script) and filters the items by their
`data-k-text`; "/" puts focus in the field and Escape clears it; on a phone it folds the list behind
"Pages", which opens over the text without moving it and which Escape closes; it marks the section being read in "On this page"; it gives a code block a
tab stop only while it scrolls; and it takes role, name and tab stop off a table's or a diagram's scroll
box while its content fits. It writes no link, item or text of the list. `scripts/devdocs-hooks.test.mjs`
fails when `docs.css` or `docs.js` uses a documentation class or `data-k-*` hook that the frame, its parts
and its pages do not write.

`src/pages/[...slug].astro` renders every staged document at its slug (the `docs` collection of
`src/content.config.ts`, whose id is the manifest's slug): its title, its description, its Markdown,
previous and next, the edit line and "On this page". `/roadmap/`, `/battery/` and `/status/` are
hand-written pages in the same frame; their pictures and text are written on the server
(`src/lib/timeline.ts`, `src/lib/walkthrough.ts`, `src/lib/status.ts`), and small scripts change them only
when the reader asks (a gate chosen, a step taken, the designed bricks shown); `src/lib/timelineView.ts`
also brings the timeline to the reader's day. Nothing on these pages moves by itself.

### Adding a page

A new document, for example a page to get started and install, needs three things and no markup:

1. Its Markdown source in the repository, governed like any document (see "What is never published").
2. An entry in `docs/publish.json`: `src`, a `slug` (lower case words joined by `-`, not under a route the
   site writes by hand: `RESERVED_SLUG_ROOTS` in `tools/publish/core.py`), a `wiki` name, and a
   `description`, one plain sentence of 120 to 160 characters that no other page repeats. A `title`
   replaces the page's first heading if given. To lead the documentation, list it first in the
   `pages` of the "Start here" section: the list's order is the manifest's.
3. A commit, then `npm run build` (staging reads the commit).

The page then appears in the navigation of every documentation page, on the home under its group, in
previous and next, in the sitemap (dated by its source), and under `DOC_BUDGET` in `check-budget`; the
accessibility check finds it in `dist/`. Its code blocks are plain ink with no Copy control. To make it
one of the home's "Where to start" pages, add its slug to `START_SLUGS` in `src/lib/devdocs.ts`
(`npm test` fails on a slug the manifest lacks); that list is part of the design, so ask the project lead
first.

A hand-written page in the list (like `/status/`) needs more: its file in `src/pages/` on `Docs.astro`
with `here` set to its route, its title and description in `PAGES` in `src/lib/head.ts`, its route and
title in `CUSTOM_PAGES` in `tools/publish/stage.py` and its route in `RESERVED_SLUG_ROOTS`, its source
list in `scripts/sitemap-lastmod.mjs` (and its route in the test beside it), and, if it weighs more than
a document, a line of its own in `scripts/check-budget.mjs`.

### Tables, code, diagrams, notes

- **Tables**: `scripts/table-region.mjs` wraps every Markdown table in
  `<div class="sx-table" role="region" tabindex="0" aria-label="Table: ...">`, named by its caption or
  nearest heading, so a table that scrolls can be scrolled by keyboard (WCAG 2.1.1), and labels each
  cell with its column's heading for phones (`data-label`); a cell holding a calendar date is kept on one
  line. **Write tables in Markdown:** a raw HTML table is not wrapped, so it is unstyled and
  unreachable by keyboard.
- **Code** is one ink, in Martian Mono, with no syntax colour and no Copy control.
- **Diagrams** are staged SVG with geometry and classes but no colour, inside `.sx-diagram` (a figure and a
  scroll box); `docs.css` paints them from the kit's tokens, so one file serves both themes, flat: thin
  outlines, the inside of a shape the page's own field, no box around the drawing. The figure still
  carries `data-pagefind-ignore`, from the site search the documentation once had; nothing reads it now,
  and it stays so that the staged markup (`tools/publish/diagrams.py`, pinned by its tests) is unchanged.
- **Notes** are a document's block quotes, drawn with a thin mark at their left.

## Component inventory

Under `src/components/devdocs/`: the documentation's frame, described in
[The documentation](#the-documentation): `DocsNav.astro`, `DocsIndex.astro`, `OnThisPage.astro`,
`DocPager.astro` and `DocEdit.astro`. No other component is shared; each hand-written page writes its own
markup.

Under `src/layouts/`: `Bare.astro` (the document: the head from `lib/head.ts` with the kit's head
snippet first, the fonts; the home uses it alone), `Kit.astro` (Bare with `kit.css`, the skip link, the
kit's header, the page's `<main>`, the footer the kit writes, `kit.js` and the page's own script),
`Post.astro` (Kit with a post's title, lead, days and body, and links to the previous and next post)
and `Docs.astro` (Kit with the documentation's frame, its stylesheet and its script).

Under `src/kit/` (imported, never edited by hand): `kit.js`, `kit.css`, `orb-head.js` and
`orb-head.css` (inlined into every page's head), `Header.astro`, `docs/` (`docs.css` and `docs.js`, the
documentation's stylesheet and script, loaded by its pages only), `film/` (the home's film:
`Body.astro`, `Noscript.astro`, `film.css`, `film.js`, and `gen.js`, the shape generator the film
bundles as text), `pages/<page>/` (`Main.astro`, `page.css`, `page.js`, `page.ts` for
what-were-building, experiments, about, blog and not-found), `posts/<slug>/` (a post's own figures, for
a post whose page design has them: `Open.astro`, the opening; `page.css`; `page.js`, the figure script;
`figures.json`, where the figures go in the post's text) and `stills/<page>/` and `stills/posts/<slug>/`
(each figure's baked still, inlined into the page's HTML).

A post's words stay its Markdown's. `scripts/post-figures.mjs` (a step of the Markdown processor, like
`scripts/table-region.mjs`) lays a designed post's Markdown out in the design's reading columns with its
figures between them; it checks every block of the post against `figures.json` and stops the build when
the post has changed since its figures were imported, so a revised post needs a re-import. The image in
the post's Markdown that a figure stands in for stays in `index.md` (GitHub shows it) and is left out of
the page. A post without a folder under `src/kit/posts/` is shown as its Markdown, in one reading column.

**`src/lib/`**: `plan.ts` (date logic over the plan; "today" is passed in), `today.ts` (`todayIn`, apart
so a page script can load only it), `timeline.ts` (the roadmap's timeline as of the plan's own date) and
`timelineView.ts` (its script in the browser: a chosen gate, the reader's day), `ledger.ts` (types of the
public projection), `status.ts` (readout and brick rows, build and meaning axes kept apart),
`devdocs.ts` (the documentation list, its navigation, previous and next, "Where to start", "On this
page", the edit links), `lastUpdated.ts` (a page's "Last updated" at build time) and `commitDay.ts` (a
commit time as a day), `seo.ts` (origin, base, `NOT_FOUND`, theme colours, JSON-LD, per-page head),
`head.ts` (the whole head of a page, and the `PAGES` table of the hand-written pages' titles and
descriptions), `blog.ts` (the blog's posts and feed), `feed.ts` (Atom serialiser), `maze.ts`
(deterministic grid geometry and seeded walks), `battery.ts` (the paradigms' data), `walkthrough.ts` (the
walk-through's pictures, drawn from the paradigms), `sheet.ts` (wall outlines, grids, rulers), `url.ts`
(`withBase`). `battery`, `blog`, `commitDay`, `devdocs`, `feed`, `head`, `maze`, `plan`, `seo`, `sheet`,
`status`, `timeline` and `walkthrough` have a unit test beside them.

## Checks

`npm run build` stops at the first failure.

| Check | Fails when |
|---|---|
| `check:og` | The card names a stage other than the ledger's active one, the sidecar does not describe `brand/psyche-social.png` byte for byte, or `public/og.png` is not its copy |
| Staging | A governed source differs from `HEAD`; the guard refuses a page; a heading or description is missing; a relative link is dead; a fence has no current drawing or a drawing no fence |
| `astro check` | Type or Astro errors. Warnings and hints do not fail it |
| Link validation | Staging fails on a dead relative link in a document or post. After the build, the built output of every page is read: `check:refs` fails on a link to an id the same page lacks, `check:seo` on a link from the root or by the site's whole address that leads to no built page or file, or to an id that page lacks. Build hand-written links with `withBase()`. For the kit and the hand-written pages, `scripts/kit-links.test.mjs` (in `npm test`) fails earlier, on a link that leads to no page |
| `check:spacing` | The built home, What we're building, Experiments, About, blog index, documentation home, roadmap, battery or status page has text glued to an inline element or an expression's output, or a number to a word; or any figure caption has two words run together |
| `check:refs` | A page has a `<use href>`, `url(#...)`, `aria-labelledby`, `aria-describedby`, `aria-controls`, `<label for>` or `<a href="#...">` pointing at an id it lacks (a bare `#` is no reference) |
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
zlib build does not trip it and real growth does. Every document (each slug of `docs/publish.json`,
read there) falls under `DOC_BUDGET`, as does a page with no line of its own (`DEFAULT_BUDGET` is the
same line). To raise one, change the number and say why in the commit; a new page that needs more gets
its own measured line. The home (the film and three.js), What we're building, Experiments and About (the
kit and their figure scripts) have lines above the default; the blog's index and each post have lines of
their own (a post with designed figures carries its figure script), as do the documentation's home and
its three hand-written pages. The comment above `PAGE_BUDGETS` says why each weighs what it does.

**SEO and the feed.** `scripts/check-seo.mjs` reads `dist/`. Per page, the 404 page included, it fails
on: other than one title, canonical address and description (120 to 160 characters, unique); `og:` or
`twitter:` tags that differ from the page's; an image that is not a PNG of its stated size; a missing
theme colour, icon or manifest; a `robots` meta anywhere but the 404 page (which must be `noindex`, with
its own title, description and address); structured data off the landing page and the blog posts; and a link to another page of the site,
written from the root or with the site's whole address (which the link validator treats as external),
that leads to nothing or to a missing id (markup inside a script is not read). For the site: a `robots.txt` that does not allow everything and name the sitemap; a bad
manifest; a sitemap that omits a page, lists a non-page or repeats an address, or a `<lastmod>` that is
missing (with history), unreadable or in the future. For the feeds: either one not named once in every
head; for the progress feed, not Atom 1.0, an `updated` other than the newest event's day, an author
other than `CITATION.cff`'s, or entries that are not one per plan event, newest first; for the blog's,
not Atom 1.0, an `updated` other than the latest day a post was published or revised, or entries that
are not one per built post, newest first. A blog post must carry its `article:` tags and one
BlogPosting that matches its head; no other page but the landing page carries structured data.

### Accessibility check

`scripts/check-a11y.mjs` serves `dist/` on a free local port and runs axe-core (WCAG 2.0, 2.1 and 2.2,
levels A and AA) over every page it finds, the 404 page included, at desktop and phone width, light and
dark, reduced motion on. Every page ignores the system's colour scheme, so each load first writes the
scheme to `localStorage` (`psyche-theme`), and the run fails if the page then shows another theme. The
home fixes its own theme (the film is dark), so it is audited once per width, dark, and listed as "fixed
dark"; any other page that fixes its theme fails the run. It also opens what a reader opens by clicking,
audits it and closes it again where it closes, failing if it does not close as a reader expects: on a
document, the page list's field with words that match no page (Escape clears them); on the
documentation's home, its filter with words typed; on `/roadmap/` at phone width, the "Pages" list
(opened with the page scrolled down, it must not move the page or its text; Escape closes it and
returns focus to "Pages"); on `/roadmap/`, a gate chosen; on `/battery/`, the
walk-through stepped; on `/status/`, the designed bricks shown; on a post with designed figures, a figure
played; on `what-were-building/`, on `research/gates/` and on the home (the film), at phone width, the
site's menu (it must hold the five links, mark the page's item, For developers on the document and
none on the film, take focus to the first and hold the theme switch, on the film
no switch; Escape closes it, focus returns to its button and the page is left as it was); on `about/`
and on `research/gates/`, at desktop width, the header's theme switch pressed (the page is audited in
the other theme, then the switch is pressed again; the run fails if the theme does not change and stay chosen or the switch's spoken name does not
say what it will do). It exits 1 on a serious or critical
violation and on anything it cannot audit (a page that does not answer 200, a state that will not open,
a run where axe tested fewer than 15 rules, a state whose page is missing). Lesser findings, and rules axe cannot decide, are listed
and never fail it. It exits 2 when it could not set itself up (no Chrome, a failed install), which says
nothing about the site; CI runs it once more on a 2. Flags: `--chrome PATH`, `--json FILE`, `--port N`
and `--only /,research/gates/,404.html` for a quick look.

It installs `axe-core` and `puppeteer-core` with `npm ci` into `node_modules/.cache/psyche-a11y-tools`
(`A11Y_TOOLS_DIR` moves it), at the exact versions `scripts/a11y-tools/package.json` names, with their
own dependencies as `package-lock.json` locks them, so a release of one of those cannot change the
check. They are not site dependencies. `scripts/a11y-tools.test.mjs` (in `npm test`) fails if a version
is not exact, the lockfile disagrees or lacks a hash, or the script types a version.

To keep it passing, a control's accessible name must contain the text drawn on it (WCAG 2.5.3), and a
picture that only repeats the words beside it is `aria-hidden`.

axe cannot decide text contrast over gradients, pseudo-elements and images: after changing a colour
token or surface, measure it from pixels. After changing the frame, walk the keyboard through the
header, the documentation's page list and its filter, "Pages" on a phone, "On this page", a scrolling
table, a diagram that scrolls, previous and next, the footer and the 404 links at desktop and phone
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
- The "Start here" section is first in `docs/publish.json`, once (`tools/publish/test_core.py`); a new
  section becomes a group of the documentation list after it, in manifest order. A section title is
  shown as typed and names no program state; the ledger holds it (`src/lib/devdocs.test.ts`).
- Three bars no script checks. Nothing scrolls sideways at 320px wide with text at 200 percent; the
  accessibility check runs at one desktop and one phone width only. Anything that moves for more than five
  seconds has a Pause control (WCAG 2.2.2). A state is never told by colour alone (WCAG 1.4.1): its marker
  differs in shape or carries a label, and is drawn with borders so that it survives forced colours.

## Credits

[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) is the one list to keep current: the two
typefaces and their licence, the one face the project draws itself, the components adapted from the
21st.dev catalog, and the npm packages.

To credit a catalog component you adapted:

1. Port it to the site's tokens in plain CSS, Astro or a few lines of script, leaving its libraries out
   and writing the words yourself.
2. Credit it in a comment next to the code: the component's name and its author's catalog username on
   one line, so a search finds them, and what you took (its anatomy, or an idea only).
3. Add a row, in alphabetical order, to the table in section 2 of `THIRD_PARTY_NOTICES.md`: component,
   author, what it was adapted for, and every file that credits it (paths under `website/src/`).

The notices state no licence for the catalog components and assume none; they name them so the original
and its terms can be found.
