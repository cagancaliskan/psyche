# Third-party notices

Psyche's own code is released under the MIT licence (see [LICENSE](LICENSE)). This file lists the
third-party material that the documentation site (`website/`) uses or was adapted from, with the
credit and the licence terms that go with it.

## 1. Typefaces

The site self-hosts three variable typefaces. They are installed from the Fontsource packages
named below, built into the site and served from its own origin. The project uses them as
packaged and does not modify or sell them.

| Typeface | Used for | npm package | Copyright, as stated in the package | Licence |
|---|---|---|---|---|
| Unbounded | Display headings | `@fontsource-variable/unbounded` | Copyright 2022 The Unbounded Project Authors (<https://github.com/googlefonts/unbounded>) | SIL Open Font License 1.1 |
| Instrument Sans | Body text | `@fontsource-variable/instrument-sans` | Copyright 2022 The Instrument Sans Project Authors (<https://github.com/Instrument/instrument-sans>) | SIL Open Font License 1.1 |
| Martian Mono | Labels and code | `@fontsource-variable/martian-mono` | Copyright 2020 The Martian Mono Project Authors (<https://github.com/evilmartians/mono>) | SIL Open Font License 1.1 |

The copyright lines and the licence identifier are those in each package's `LICENSE` and
`package.json`. The three packages carry the same licence text. It is reproduced here, as the
licence asks of every copy.

```text
-----------------------------------------------------------
SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
-----------------------------------------------------------

PREAMBLE
The goals of the Open Font License (OFL) are to stimulate worldwide
development of collaborative font projects, to support the font creation
efforts of academic and linguistic communities, and to provide a free and
open framework in which fonts may be shared and improved in partnership
with others.

The OFL allows the licensed fonts to be used, studied, modified and
redistributed freely as long as they are not sold by themselves. The
fonts, including any derivative works, can be bundled, embedded,
redistributed and/or sold with any software provided that any reserved
names are not used by derivative works. The fonts and derivatives,
however, cannot be released under any other type of license. The
requirement for fonts to remain under this license does not apply
to any document created using the fonts or their derivatives.

DEFINITIONS
"Font Software" refers to the set of files released by the Copyright
Holder(s) under this license and clearly marked as such. This may
include source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the
copyright statement(s).

"Original Version" refers to the collection of Font Software components as
distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting,
or substituting -- in part or in whole -- any of the components of the
Original Version, by changing formats or by porting the Font Software to a
new environment.

"Author" refers to any designer, engineer, programmer, technical
writer or other person who contributed to the Font Software.

PERMISSION & CONDITIONS
Permission is hereby granted, free of charge, to any person obtaining
a copy of the Font Software, to use, study, copy, merge, embed, modify,
redistribute, and sell modified and unmodified copies of the Font
Software, subject to the following conditions:

1) Neither the Font Software nor any of its individual components,
in Original or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy
contains the above copyright notice and this license. These can be
included either as stand-alone text files, human-readable headers or
in the appropriate machine-readable metadata fields within text or
binary files as long as those fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font
Name(s) unless explicit written permission is granted by the corresponding
Copyright Holder. This restriction only applies to the primary font name as
presented to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
Software shall not be used to promote, endorse or advertise any
Modified Version, except to acknowledge the contribution(s) of the
Copyright Holder(s) and the Author(s) or with their explicit written
permission.

5) The Font Software, modified or unmodified, in part or in whole,
must be distributed entirely under this license, and must not be
distributed under any other license. The requirement for fonts to
remain under this license does not apply to any document created
using the Font Software.

TERMINATION
This license becomes null and void if any of the above conditions are
not met.

DISCLAIMER
THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM
OTHER DEALINGS IN THE FONT SOFTWARE.
```

## 2. Components adapted from the 21st.dev catalog

Several layouts and effects on the site were adapted from components in the 21st.dev catalog. None
is bundled or copied as published. Each was rewritten against the site's own design tokens, in
plain CSS, Astro or a few lines of script, with the catalog component's own libraries left out
(for example a motion library). The words on the page are the project's own.

Each adaptation is credited by component name and author in a comment next to the code. This
table is collected from those comments; the comments are the record, and an adaptation added
later is credited there and here. The author column holds the catalog usernames as the comments
give them. Paths are under `website/src/`.

This file states no licence for these components, and none is assumed. The catalog components
themselves are not included here; only the project's own adaptations are. They are credited by
name and author so that anyone can find the original and read the terms its author set.

| Component | Author | Adapted for | Credited in |
|---|---|---|---|
| 404 Did You Mean | ziegfiroyt | The address that was asked for, and the nearest page to it, on the 404 page | `pages/404.astro`, `components/chrome/NearestPage.astro`, `styles/notfound.css` |
| 404 Search And Popular Links | olewandowski1 | A list whose rows share their rules: the 404 page's places to go and the cells of the footer's title block | `styles/notfound.css`, `pages/404.astro`, `styles/global.css`, `components/chrome/Footer.astro` |
| Admonition | deltacomponents | Asides (notes, tips, cautions) | `styles/global.css` |
| Animated Beam | dillionverma | Light pulse on the evaluation pipeline figure | `components/docs/EvaluationPipeline.astro` |
| Animated Sidebar | unlumen | Active marker in the sidebar | `styles/global.css` |
| Animated Signature | dqnamo | Stroke draw of the hero mark and the maze figure | `styles/hero.css`, `styles/landing/maze-figure.css` |
| Audit Log Table | arihantcodes | Mono identifier column and the state cell that is a marker and a word, in the brick board | `styles/status.css`, `components/BrickBoard.astro` |
| Command Menu | victor-teles | Search dialog: grouped results, the match in ink | `styles/global.css` |
| Corner Frame | kevingirelli | Registration corner marks on figures, battery sheets, the search dialog, the footer's title block and the 404 page (one shared recipe, `.sx-reg`) | `styles/global.css`, `styles/battery.css`, `styles/notfound.css`, `styles/landing/maze-figure.css`, `components/landing/MazeFigure.astro`, `components/chrome/Footer.astro`, `components/BatteryExplorer.tsx` |
| Footer with Navigation Grid | shadcnui-blocks | A row of links under a divider, in the footer's title block | `styles/global.css`, `components/chrome/Footer.astro` |
| Frame Button | radiumcoders | Primary action in the hero: a ruled, square-cornered control whose four corner marks step outward on hover | `styles/hero.css` |
| Gantt Chart | klyv-ui | Month gridlines, today marker and gate marks on the axis of the roadmap timeline | `styles/plan.css`, `components/Timeline.tsx` |
| Health Checks | astralyxdev | Rows that lead with a state mark and end with its word, and two signals of one item kept apart, in the brick board | `styles/status.css`, `components/BrickBoard.astro` |
| How It Works Steps | ln-dev7 | Sequence figures in the documentation | `styles/docs-visuals.css` |
| Input Group with Keyboard Shortcut | sean0205 | Search button | `styles/global.css` |
| Interactive List Preview | hyperiux | Battery rows | `styles/landing/battery-rows.css`, `components/battery/BatteryTeaser.astro` |
| Kbd | shadcn | Shortcut key cap on the search button | `styles/global.css` |
| Kbd Input Group | uiable | Search button | `styles/global.css` |
| Key Value List | corr | The label column and value column of the captured-run facts, stacked when narrow | `styles/status.css`, `pages/status.astro` |
| Klyv Animated Beam | klyv-ui | Light pulse along the connectors of documentation figures | `styles/docs-visuals.css` |
| Kokonut UI Scroll Index | kokonutd | Passed, current and ahead states of the battery index | `styles/battery.css`, `components/BatteryExplorer.tsx` |
| Legends | airbnb-visx | The key to the hero's four sheets: a swatch in each sheet's own colour, then its name in neutral type | `styles/hero.css` |
| Line Draw SVG | pulkitxm | Route draw in the battery pictures | `styles/battery.css` |
| Link Button | hyperiux | Section-end links | `styles/landing/links.css` |
| Milestone Timeline | olewandowski1 | Dated rows with a status label in the roadmap's phase list | `components/TimelineList.astro`, `styles/plan.css` |
| Note | shugar | Asides | `styles/global.css` |
| Not Found 404 Page | mohammadshehadeh | The 404 page: a mono label, one sentence and a ruled list of places to go | `pages/404.astro`, `styles/notfound.css` |
| Numberless Pagination | shadcnui-blocks | Previous and next links | `styles/global.css` |
| Page Header with Breadcrumbs | olewandowski1 | The ruled strip of stage, section and state above a page title | `styles/docs.css`, `components/chrome/PageTitle.astro` |
| Reshaped Table | reshaped | The shared outer and column rules of the footer's title block (the idea only; the package is not used) | `styles/global.css`, `components/chrome/Footer.astro` |
| Reveal | asanshay | Scroll reveals on the landing page | `styles/landing.css`, `pages/index.astro` |
| Scroll animated timeline | ibrandify | Scroll-drawn bars of the roadmap timeline and rows of its list | `styles/plan.css` |
| Scroll Caliper | nikolas-sapa | Measuring rail in the page gutter | `styles/landing/caliper.css`, `components/landing/CaliperRail.astro` |
| Search Input with Keyboard Shortcut | shadcnspace | Search button | `styles/global.css` |
| Sidebar Light | inference-sh | Sidebar rail and rows | `styles/global.css` |
| Spec Sheet | isaiahbjork | Ruled tables and rows on the landing and battery pages, the label column and ruled rows of the gate list and of the brick board, the bar on a previous or next rule, on a footer or title rule and on the 404 rows | `styles/global.css`, `styles/docs.css`, `styles/notfound.css`, `styles/battery.css`, `styles/landing/ledger.css`, `styles/landing/rows.css`, `components/landing/StageLedger.astro`, `components/landing/HowBuilt.astro`, `components/landing/PublicWithheld.astro`, `components/landing/SubstrateReadout.astro`, `styles/readout.css`, `components/BrickBoard.astro`, `styles/status.css`, `components/GateStepper.astro`, `styles/plan.css`, `pages/battery.astro` |
| Spotlight | kevingirelli | Pointer-following light on cards | `styles/docs-visuals.css` |
| Stack | abhishek-mallick | Layer stack figure | `styles/docs-visuals.css` |
| Stats Band | kuratlielia | Label-over-figure cells of the substrate readout | `styles/readout.css`, `components/landing/SubstrateReadout.astro` |
| Status | diceui | State label with its marker, in the roadmap's timeline, list and gate rows | `styles/plan.css` |
| Status Badge | serafimcloud | Two-part label and value of the "now" readout | `styles/plan.css`, `components/NowLine.tsx` |
| Stepper | kevingirelli | Step rows of the battery, and the connecting rule and square marks of the gate list | `styles/battery.css`, `styles/plan.css`, `components/BatteryExplorer.tsx`, `components/GateStepper.astro` |
| Table | originui | Tables in the documentation | `styles/docs.css` |
| Table of Contents | appica-dev | Current-heading bar of the contents list | `styles/global.css` |
| Table of Contents | mohammadshehadeh | Sidebar rail and the battery index | `styles/global.css`, `styles/battery.css`, `components/BatteryExplorer.tsx` |
| Tagline | shadcncraft | Index and kicker of the landing section openings | `components/landing/SectionHeader.astro` |
| Text Reveal (Mask) | soralabs | Headings that rise out of a clip | `styles/hero.css`, `styles/landing/section-header.css`, `components/landing/SectionHeader.astro` |
| Underline Link | balick | Underline links, the title of a previous or next link | `styles/global.css`, `styles/hero.css`, `styles/landing/links.css`, `styles/landing/battery-rows.css`, `styles/landing/ledger.css` |
| Vertical Titled Stepper | sean0205 | Numbered titles of the battery steps | `styles/battery.css`, `components/BatteryExplorer.tsx` |

If you are an author listed here and want a credit corrected or an adaptation removed, tell the
project lead in an issue or in a
[GitHub Discussion](https://github.com/cagancaliskan/psyche/discussions).

## 3. Packages installed from npm

Everything else the site uses comes from npm packages pinned in `website/package.json` and
`website/package-lock.json`. They are installed when the site is built and are not copied into
this repository. The built site bundles parts of these packages, and each package remains under
the licence it ships with; those terms apply to it. This file does not reproduce them.

Two files are copies rather than installs, both of `@astrojs/starlight` 0.42.6.
`website/src/components/chrome/Search.astro` is Starlight's Search component with three small edits
(the key cap beside the search button is drawn rather than written, so the button's accessible name
holds its visible text; the script for Apple devices sets the key's attribute; the icon is imported
from the package). `website/src/components/chrome/Footer.astro` reproduces the markup and the first
style rules of Starlight's Footer component (the footer element, the edit-link row, previous and next,
and the layout rules for the footer and that row), with the project's title block added below them.
Both are used under the package's MIT licence, whose notice follows and covers both.

```text
MIT License

Copyright (c) 2023 Astro contributors (https://github.com/withastro/starlight/graphs/contributors)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
