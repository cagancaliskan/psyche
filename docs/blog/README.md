# Writing for the blog

This folder holds the posts of the [blog](https://cagancaliskan.github.io/psyche/blog/), one folder
per post. A post reaches the site the way a docs page does: `tools/publish/stage.py` reads it from a
reviewed commit, checks it and stages it, and the build checks it again. This page sets out the
format, what a post may say, and the two ways to publish one. It is the guide for posts, not a post
itself, and it is never published as one.

## A post

A post is a folder whose name is the post's address: `docs/blog/<slug>/index.md` is published at
`/psyche/blog/<slug>/`. The name uses lowercase letters, digits and single hyphens, at most 80
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

The site serves a post on the same address as the editor below, and Markdown passes raw HTML
through as it is written, so staging limits what a post may write as HTML. Outside fenced and
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

An SVG is served from the same address as the editor below, so staging refuses one whose root is not
an SVG element, or that holds an element outside the SVG namespace (XHTML, or the RDF, Sodipodi and
Inkscape metadata some drawing programs write), a script, an event attribute, `foreignObject`, an
embedded frame or object, a `handler` or `listener` element, a processing instruction (an XSLT
stylesheet among them), an element of the XSLT namespace, an attribute of any namespace but XLink,
an `xml:` attribute other than `xml:lang` and `xml:space`, a `javascript:` address, a DOCTYPE or
entity declaration, an animation that sets a link or an event attribute, a link to anything outside
the file, an encoding other than UTF-8, or CSS that loads anything (`url()` or `@import`), except a
`#fragment` or a PNG, JPEG, WebP or GIF data address. Text inside an SVG is read by the same copy
checks as the post.

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
- The [disclosure policy](../research/disclosure-policy.md). The current state of stage 2 is private,
  so a post covers what is already public or has been released, never how the work is going from
  day to day. When unsure whether something is private, it is.
- No figure typed by hand. A count comes from `tools/ledger.json` and a plan date from
  `tools/research_plan.json`, and a post that needs one links to the page that shows it (the
  [progress page](../progress.md), the status page) instead of copying it.
- English only, in the plain tone the contributing guide asks for.

The commit gate reads every post (`ledger_check.py`, `ci_c2.py`, `check_copy.py`): it catches a
test count that disagrees with the ledger, the claim terms the project rules out, energy figures and
any language but English, and the disclosure job of the pull request reads the post against the
private list of withheld terms. It does not catch every figure or date typed by hand, nor the tone:
those rules are kept by the author and the reviewer.

## Publishing from a clone

1. Make a branch from `main` and add the post's folder.
2. Commit it. The site stages from the commit, never from the working tree.
3. Run `make check` at the root, and `npm test` and `npm run build` in `website/`.
4. Open a pull request. Merge it only when the checks the main branch requires (`governance`,
   `build` and every `run_tests`) and the `disclosure` check have all passed. The Pages workflow
   then deploys it.

## Publishing from the editor

The editor at [/psyche/admin/](https://cagancaliskan.github.io/psyche/admin/) writes the same files
through the GitHub API, so a post written there goes through the same checks as one written in a
clone. Saving a post never writes to `main`, and the editor offers no way to publish (its Asset
Library page does try to commit to `main`, which the ruleset refuses, see below):

| In the editor | On GitHub |
|---|---|
| Save a new post (its address is typed once, when it is created) | A branch `cms/posts/<slug>` from `main`, one commit `docs(blog): add <slug>` with the post and its images, and a pull request |
| Save again | Another commit on the same branch and pull request |
| Draft, In Review, Ready | A label on the pull request. Draft also makes it a GitHub draft pull request, which GitHub does not merge until it is marked ready for review. In Review and Ready are ordinary open pull requests: the label gates nothing, so merge only when the required checks and the `disclosure` check have passed |
| Delete a post | A pull request that removes its folder |
| Publish | Not offered: open the pull request on GitHub, wait for the required checks and the `disclosure` check, and merge it there |

Publishing stays on GitHub on purpose. The ruleset on `main` lets an administrator merge a pull
request whose checks failed, and a merge button inside the editor would do that without showing the
checks. Every save, a draft included, is public on GitHub at once, in the branch and the pull
request, before anything is published on the site.

To sign in, create a fine-grained personal access token on GitHub (Settings, Developer settings,
Personal access tokens, Fine-grained tokens): resource owner `cagancaliskan`, access to
`cagancaliskan/psyche` only, the repository permissions Contents (read and write) and Pull requests
(read and write) and nothing else, and the shortest expiry that covers the session, a week at most.
Do not grant Workflows. Paste it under "Sign In Using Access Token". When you are done, sign out,
which removes the token from the browser, and delete it on GitHub, which is the only way to end it
there. The editor is meant for Chromium and Firefox: it saves JPEG and PNG uploads as WebP with the
browser's own encoder, and in a browser without one (Safari) the result may not be WebP, which
staging then refuses.

What protects the editor, and what does not:

- The page is not indexed, sends no referrer and carries a content security policy: scripts load
  only from the pinned version's path on unpkg, and the browser refuses the main file unless its
  bytes match the integrity hash in the page. The chunks the main file loads later from the same
  path carry no hash, so for them the pin rests on unpkg serving that version's files unchanged.
  `npm run build` fails if the page loses its robots or referrer rule, if its `default-src`,
  `object-src`, `base-uri`, `form-action` or `script-src` directive changes, if a script, worker or
  child directive is added, or if its one script is not the pinned file with an integrity hash. It
  does not check the hosts the other directives allow (`connect-src`, `img-src`, `font-src` and
  the rest), nor that the hash matches the file.
- A meta policy cannot forbid framing, so another site can frame the editor. Current browsers keep
  the storage of a framed page apart from that of the same page opened directly, so a framing
  page meets a signed-out editor.
- The token stays in the browser's local storage while you are signed in, and every page of
  `cagancaliskan.github.io` shares that storage: a script on any of them could read it. Today that
  origin serves only this site, which loads no script from another host, and staging holds a post's
  HTML and SVG to lists of inert elements. A script on that origin would reach the token, so both
  have to stay true.
- The token can do more than the editor's interface: with Contents and Pull requests write it can
  change any file on a branch and merge a pull request, and a merge deploys. Without the Workflows
  permission it cannot change the workflow files. So keep a token to one editing session, and if it
  may have leaked, delete it on GitHub at once and look over the open `cms/` branches and pull
  requests.
- The image dialog inside a post offers a global location beside the post's own folder, and the
  editor's Asset Library page writes to it. A picture there is refused when the post is staged,
  because a file directly in `docs/blog/` is not allowed, and the Asset Library's commits to `main`
  are refused by the ruleset: always pick the post's own folder.

The version is pinned in `website/public/admin/index.html`, in the script address, the integrity
hash and the content security policy. To upgrade, hash `dist/sveltia-cms.js` of the new npm package,
check that unpkg serves the same bytes, change all three, and open a pull request.
