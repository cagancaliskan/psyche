# Writing for the blog

This folder holds the posts of the [blog](https://psyche.cagancaliskan.com/blog/), one folder
per post. A post reaches the site the way a docs page does: `tools/publish/stage.py` reads it from a
reviewed commit, checks it and stages it, and the build checks it again. This page sets out the
format, what a post may say, and how to publish one. It is the guide for posts, not a post
itself, and it is never published as one.

## A post

A post is a folder whose name is the post's address: `docs/blog/<slug>/index.md` is published at
`/blog/<slug>/`. The name uses lowercase letters, digits and single hyphens, at most 80
characters, is never `index` (the blog's own index) nor `build`, `dist` or `venv` (directory names
the publishing guard skips), and does not change once the post is published, because readers and
the feed link to it.

`index.md` is UTF-8 without a byte-order mark, and opens with front matter between two `---` lines:

```yaml
---
title: "Why Psyche keeps a blog"
date: "2026-11-04"
description: "One plain sentence of 120 to 160 characters, for search results and link previews."
tags:
  - "project"
  - "site"
---
```

| Field | Required | Rule |
|---|---|---|
| `title` | yes | One line, at most 120 characters, without `<` or `>`. It is the page title, so the body has no level-one heading. |
| `date` | yes | The day of publication, `YYYY-MM-DD`, no later than the day after the commit that publishes it. |
| `description` | yes | One plain sentence of 120 to 160 characters, different from every other page and post. |
| `tags` | no | Up to four of: `project`, `substrate`, `cognitive-maps`, `methods`, `engineering`, `reading`, `site`. |
| `author` | no | Defaults to the first author of `CITATION.cff`. No `<` or `>`. |
| `updated` | no | The day of a later correction, `YYYY-MM-DD`, not before `date` and no later than the day after the commit. |
| `draft` | no | `true` keeps the post off the site entirely. |

No other field is accepted. The values are plain YAML: quoted or plain strings on one line, `true`
or `false`, and lists written as `- item` lines, all indented alike, or `[a, b]`. A value that a
YAML reader would take for something other than text, such as `True`, `2026`, `2026-11-04` or a
lone `-`, has to be quoted; only `date` and `updated` take a plain day. The title, the description
and the author hold no control character and no invisible character such as a zero-width space or
a right-to-left override, so the text a reviewer reads is the text the site shows. Comments,
anchors and values over several lines are refused, with the line that holds them. A draft is read
only as far as its `draft: true`: its values are not checked, so they may still be unfinished, but
its front matter must still be written in the shapes above. It is kept off the site, but it is
public in the repository like every other file.

The body is Markdown, as on the docs pages: headings from level two, lists, tables, code blocks and
asides. A relative link to a docs page's source (`../../research/gates.md`) or to another post
(`../other-post/index.md`) becomes the page's address on the site; a link to any other file of the
repository becomes a GitHub link pinned to the published commit; a link that would be dead stops
the build, and so does a link or an image whose address uses any scheme but `http`, `https` or
`mailto`. The hand-written pages of the site (the status page, the roadmap, the battery) have no
Markdown source, so they are linked by their full address.

### HTML in a post

A post is text and pictures, never code. It is served from the site's own origin, and Markdown
passes raw HTML through as it is written, so staging limits what a post may write as HTML: anything
that runs on the site is site code, and site code is reviewed in a pull request. Outside fenced and
indented code, the only elements allowed are `a`, `abbr`, `b`, `br`, `code`, `del`, `details`,
`em`, `i`, `img`, `ins`, `kbd`, `mark`, `q`, `s`, `samp`, `small`, `strong`, `sub`, `summary`,
`sup`, `u`, `var` and `wbr`, with only these attributes: `href` and `title` on `a`, `title` on
`abbr`, `open` on `details`, and `src`, `alt`, `width`, `height` and `title` on `img`. A link is
relative or uses `http`, `https` or `mailto`; a picture is relative (a file of the post's folder,
or another file of the repository, which becomes a link pinned to the published commit) or an
`https` address, and has alt text. A tag closes on the line where it opens, an HTML comment sits on
one line and holds no `--`, and declarations and processing instructions are refused.

Inline code is not exempt: HTML inside backticks is read as HTML. Show HTML source in a fenced code
block, and in prose write a `<` that is text as `&lt;`, or follow it with a space.

## Images, diagrams and charts

Images sit beside `index.md` in the post's folder, with no subfolders, and are linked by their name:
`![What the figure shows, in one sentence](figure.png)`. The alt text is required, because it is all
a screen reader gets: staging refuses an image without it, and an alt made only of spaces or
invisible characters counts as none. A file may be PNG, JPEG, WebP, AVIF, GIF or SVG, at most
4 MiB, named with letters, digits, dots, hyphens, underscores and tildes, starting with a letter, a
digit, an underscore or a tilde.
Its bytes must be the format its extension names, and two names in one folder that differ only in
case are refused, because macOS and Windows keep them as one file. Staging refuses any other file
in a post's folder.

An SVG is served from the site's own origin, so a script in it would run there, and staging refuses
one whose root is not an SVG element, or that holds an element outside the SVG namespace (XHTML, or
the RDF, Sodipodi and Inkscape metadata some drawing programs write), a script, an event attribute,
`foreignObject`, an embedded frame or object, a `handler` or `listener` element, a processing
instruction (an XSLT stylesheet among them), an element of the XSLT namespace, an attribute of any
namespace but XLink, an `xml:` attribute other than `xml:lang` and `xml:space`, a `javascript:`
address, a DOCTYPE or entity declaration, an animation that sets a link or an event attribute, a
link to anything outside the file, an encoding other than UTF-8, or CSS that loads anything (`url()`
or `@import`), except a `#fragment` or a PNG, JPEG, WebP or GIF data address. Text inside an SVG is
read by the same copy checks as the post.

A diagram or a simple chart can also be written as a Mermaid fence, as on the docs pages. Its
drawing is made ahead of time: run `npm run diagrams` in `website/` and commit the file it writes
under `website/src/diagrams/`. Staging stops when a fence has no current drawing. Turning such a
post into a draft, or removing it, leaves its drawing unused, and staging stops on that too until
`npm run diagrams` removes the drawing.

## What a post may say

A post is public text and is held to the same rules as every page:

- [Rule 1](../../CONTRIBUTING.md#the-ten-non-negotiable-rules) of the contributing guide. Nothing is
  described as more than it has been shown to be; AGI is named only as the long-term aim; no
  priority claim; energy appears only as an analytic estimate.
- The [disclosure policy](../research/disclosure-policy.md). The current state of stage 2 is private.
  A post about it covers what is already public or has been released, or it is a
  [progress note](../research/disclosure-policy.md#progress-notes): it reports outcomes (a
  milestone, a count, whether a check met the criterion fixed for it, a failure) and never how the
  work is done. When unsure whether something is private, it is.
- No figure typed by hand. A count comes from `tools/ledger.json` and a plan date from
  `tools/research_plan.json`, and a post that needs one links to the page that shows it (the
  [progress page](../progress.md), the status page) instead of copying it. The one exception is a
  number in a progress note, which reports an outcome of stage 2 and is stated no more precisely
  than it was measured.
- English only, in the plain tone the contributing guide asks for.

The commit gate reads every post (`ledger_check.py`, `ci_c2.py`, `check_copy.py`): it catches a
test count that disagrees with the ledger, the claim terms the project rules out, energy figures and
any language but English, and the disclosure job of the pull request reads the post against the
private list of withheld terms. It does not catch every figure or date typed by hand, nor the tone:
those rules are kept by the author and the reviewer.

## Publishing

1. Make a branch from `main` and add the post's folder.
2. Commit it. The site stages from the commit, never from the working tree.
3. Run `make check` at the root, and `npm test` and `npm run build` in `website/`.
4. Open a pull request. Merge it only when the checks the main branch requires (`governance`,
   `build` and every `run_tests`) and the `disclosure` check have all passed. The Pages workflow
   then deploys it.
