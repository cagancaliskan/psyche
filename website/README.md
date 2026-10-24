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
- Mermaid diagrams are written for GitHub and carry their own colours. On the site Mermaid runs
  with its `base` theme on the dark tokens (`astro.config.mjs`), `docs.css` recolours every
  rendered diagram from the live tokens in both themes, and a small inline script removes the
  colours Mermaid copies onto shapes as inline styles. Mermaid measures its labels in Instrument
  Sans, so the stylesheet changes colour only, never type.

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
names its source in a one-line comment next to the code.

- **Hero:** "Hero Section with Animated Grid" by shadcnui-blocks, "Soft Blur In" by educalvolpz,
  "Border Beam Panel" by rmahammad, "Chip" by preetsuthar17 and "Mute Toggle Button" by sean0205.
- **Landing:** "Tagline" by shadcncraft, "Animated Grid" by rmahammad, "Reveal" by asanshay,
  "Scroll Reveal Content A" by abui, "Bento Feature Grid" by ln-dev7, "Us vs Them Comparison" by
  olewandowski1, "Animated Beam" by dillionverma, "Spotlight" by kevingirelli, "Glow Card Grid"
  by ncdai, and "Stats Band" by kuratlielia with "Number Ticker" by dillionverma.
- **Test battery:** "Line Draw SVG" by pulkitxm, "Feature Grid Spotlight Cards" by
  mohammadshehadeh, "Underlined Navigation Menu" by shadcnui-blocks and "Stepper" by kevingirelli.
- **Roadmap and status:** "Status" by diceui, "Status Badge" by serafimcloud, "Gantt Chart" by
  klyv-ui, "Stepper" by kevingirelli, "Quarterly Roadmap Columns" by olewandowski1 and "Stats
  Band" by kuratlielia.
- **Documentation visuals:** "Spotlight" by kevingirelli, "Klyv Animated Beam" by klyv-ui,
  "Animated Beam" by dillionverma, "How It Works Steps" by ln-dev7 and "Stack" by
  abhishek-mallick.
- **Chrome and documentation pages:** "Search Input with Keyboard Shortcut" by shadcnspace and
  "Kbd" by shadcn (search), "Table of Contents" by mohammadshehadeh and "Animated Sidebar" by
  unlumen (sidebar and contents rail), "Spotlight" by kevingirelli (previous and next),
  "Admonition" by deltacomponents (asides) and "Table" by originui (tables).

Everything else is written for this site.
