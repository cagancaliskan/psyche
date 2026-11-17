# Third-party notices

Psyche's own code is released under the MIT licence (see [LICENSE](LICENSE)). This file lists the
third-party material that the site (`website/`) uses or was adapted from, with the
credit and the licence terms that go with it.

## 1. Typefaces

The site self-hosts two variable typefaces. They are installed from the Fontsource packages
named below, built into the site and served from its own origin. The project uses them as
packaged and does not modify or sell them.

| Typeface | Used for | npm package | Copyright, as stated in the package | Licence |
|---|---|---|---|---|
| Instrument Sans | Body text | `@fontsource-variable/instrument-sans` | Copyright 2022 The Instrument Sans Project Authors (<https://github.com/Instrument/instrument-sans>) | SIL Open Font License 1.1 |
| Martian Mono | Labels and code | `@fontsource-variable/martian-mono` | Copyright 2020 The Martian Mono Project Authors (<https://github.com/evilmartians/mono>) | SIL Open Font License 1.1 |

The copyright lines and the licence identifier are those in each package's `LICENSE` and
`package.json`. The two packages carry the same licence text. It is reproduced here, as the
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

The site serves one more face that is not from a package: **Psyche Lines**
(`website/src/assets/fonts/psyche-lines.woff2`). Martian Mono's Latin file, the one the site serves,
draws no box-drawing character, no triangle pointer and no leftwards or rightwards arrow, so Psyche
Lines holds them, at Martian Mono's width, and a text diagram in a code block keeps its columns. It is
drawn by `website/scripts/make-lines-font.mjs` from rectangles, arcs and triangles. No outline in it
comes from Martian Mono or from any other font, so it carries no third-party licence: it is released
under the project's own, the MIT licence ([LICENSE](LICENSE)).

## 2. Components adapted from the 21st.dev catalog

This section lists what on the site was adapted from components in the 21st.dev catalog. None
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
| Thinking Orb | adrielzimbril | A particle orb that a page opens out of while it loads and gathers into when the reader leaves it (the idea only; the component's drawing code was not obtained and nothing of it is copied) | `kit/kit.js` |

If you are an author listed here and want a credit corrected or an adaptation removed, tell the
project lead in an issue or in a
[GitHub Discussion](https://github.com/cagancaliskan/psyche/discussions).

## 3. Packages installed from npm

Everything else the site uses comes from npm packages pinned in `website/package.json` and
`website/package-lock.json`. They are installed when the site is built and are not copied into
this repository. The built site bundles parts of these packages, and each package remains under
the licence it ships with; those terms apply to it. This file does not reproduce them. One of them
is three.js (the npm package `three`, 0.160.0, MIT licence), which is bundled into the home page,
where it draws the film.
