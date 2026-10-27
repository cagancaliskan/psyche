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
| Admonition | deltacomponents | Asides (notes, tips, cautions) | `styles/global.css` |
| Animated Beam | dillionverma | Light pulse on the evaluation pipeline figure | `components/docs/EvaluationPipeline.astro` |
| Animated Sidebar | unlumen | Active marker in the sidebar | `styles/global.css` |
| Animated Signature | dqnamo | Stroke draw of the hero mark and the maze figure | `styles/hero.css`, `styles/landing/maze-figure.css` |
| Corner Frame | kevingirelli | Registration corner marks on figures and battery sheets | `styles/battery.css`, `styles/landing/maze-figure.css`, `components/landing/MazeFigure.astro`, `components/BatteryExplorer.tsx` |
| Expanding Arrow Button | starc007 | Primary action in the hero | `styles/hero.css` |
| Gantt Chart | klyv-ui | Month gridlines and today marker of the roadmap timeline | `styles/plan.css` |
| How It Works Steps | ln-dev7 | Sequence figures in the documentation | `styles/docs-visuals.css` |
| Interactive List Preview | hyperiux | Battery rows | `styles/landing/battery-rows.css`, `components/battery/BatteryTeaser.astro` |
| Kbd | shadcn | Shortcut chip on the search button | `styles/global.css` |
| Klyv Animated Beam | klyv-ui | Light pulse along the connectors of documentation figures | `styles/docs-visuals.css` |
| Kokonut UI Scroll Index | kokonutd | Passed, current and ahead states of the battery index | `styles/battery.css`, `components/BatteryExplorer.tsx` |
| Line Draw SVG | pulkitxm | Route draw in the battery pictures | `styles/battery.css` |
| Link Button | hyperiux | Section-end links | `styles/landing/links.css` |
| Number Ticker | dillionverma | Count-up of headline numbers | `components/ui/StatsBand.astro` |
| Quarterly Roadmap Columns | olewandowski1 | Status columns on the status page | `styles/plan.css` |
| Reveal | asanshay | Scroll reveals on the landing page | `styles/landing.css`, `pages/index.astro` |
| Scroll animated timeline | ibrandify | Scroll-drawn bands and rail on the landing roadmap | `styles/landing/roadmap.css` |
| Scroll Caliper | nikolas-sapa | Measuring rail in the page gutter | `styles/landing/caliper.css`, `components/landing/CaliperRail.astro` |
| Search Input with Keyboard Shortcut | shadcnspace | Search button | `styles/global.css` |
| Spec Sheet | isaiahbjork | Ruled tables and rows on the landing and battery pages | `styles/battery.css`, `styles/landing/ledger.css`, `styles/landing/rows.css`, `components/landing/StageLedger.astro`, `components/landing/HowBuilt.astro`, `components/landing/PublicWithheld.astro`, `components/landing/SubstrateReadout.astro`, `pages/battery.astro` |
| Spotlight | kevingirelli | Pointer-following light on cards and on previous and next links | `styles/global.css`, `styles/docs-visuals.css` |
| Stack | abhishek-mallick | Layer stack figure | `styles/docs-visuals.css` |
| Stats Band | kuratlielia | Band of headline numbers | `styles/plan.css`, `components/ui/StatsBand.astro` |
| Status | diceui | Status chip | `styles/plan.css` |
| Status Badge | serafimcloud | Two-part chips of the "now" strip | `styles/plan.css` |
| Stepper | kevingirelli | Step rows of the battery and the gate stepper | `styles/battery.css`, `styles/plan.css`, `components/BatteryExplorer.tsx` |
| Table | originui | Tables in the documentation | `styles/docs.css` |
| Table of Contents | mohammadshehadeh | Sidebar rail and the battery index | `styles/global.css`, `styles/battery.css`, `components/BatteryExplorer.tsx` |
| Tagline | shadcncraft | Index and kicker of the landing section openings | `components/landing/SectionHeader.astro` |
| Text Reveal (Mask) | soralabs | Headings that rise out of a clip | `styles/hero.css`, `styles/landing/section-header.css`, `components/landing/SectionHeader.astro` |
| Underline Link | balick | Underline links | `styles/hero.css`, `styles/landing/links.css`, `styles/landing/battery-rows.css`, `styles/landing/ledger.css` |
| Vertical Titled Stepper | sean0205 | Numbered titles of the battery steps | `styles/battery.css`, `components/BatteryExplorer.tsx` |

If you are an author listed here and want a credit corrected or an adaptation removed, tell the
project lead in an issue or in a
[GitHub Discussion](https://github.com/cagancaliskan/psyche/discussions).

## 3. Packages installed from npm

Everything else the site uses comes from npm packages pinned in `website/package.json` and
`website/package-lock.json`. They are installed when the site is built and are not copied into
this repository. The built site bundles parts of these packages, and each package remains under
the licence it ships with; those terms apply to it. This file does not reproduce them.
