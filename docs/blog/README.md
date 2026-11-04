# Writing for the blog

This folder holds the posts of the [blog](https://cagancaliskan.github.io/psyche/blog/), one folder
per post. A post reaches the site the way a docs page does: `tools/publish/stage.py` reads it from a
reviewed commit, checks it and stages it, and the build checks it again. This page sets out the
format, what a post may say, and the two ways to publish one. It is the guide for posts, not a post
itself, and it is never published as one.

## A post

A post is a folder whose name is the post's address: `docs/blog/<slug>/index.md` is published at
`/psyche/blog/<slug>/`. The name uses lowercase letters, digits and single hyphens, at most 80
characters, is never `index` (the blog's own index), and does not change once the post is
published, because readers and the feed link to it.

`index.md` opens with front matter between two `---` lines:

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
| `title` | yes | One line, at most 120 characters. It is the page title, so the body has no level-one heading. |
| `date` | yes | The day of publication, `YYYY-MM-DD`. |
| `description` | yes | One plain sentence of 120 to 160 characters, different from every other page and post. |
| `tags` | no | Up to four of: `project`, `substrate`, `cognitive-maps`, `methods`, `engineering`, `reading`, `site`. |
| `author` | no | Defaults to the first author of `CITATION.cff`. |
| `updated` | no | The day of a later correction, `YYYY-MM-DD`, not before `date`. |
| `draft` | no | `true` keeps the post off the site entirely. |

No other field is accepted. The values are plain YAML: quoted or plain strings on one line, `true`
or `false`, and lists written as `- item` lines, all indented alike, or `[a, b]`. A value that a
YAML reader would take for something other than text, such as `True`, `2026` or a lone `-`, has to
be quoted. Comments, anchors and values over several lines are refused, with the line that holds
them. A draft is read only as far as its `draft: true`, so its other fields may still be unfinished;
it is kept off the site, but it is public in the repository like every other file.

The body is Markdown, as on the docs pages: headings from level two, lists, tables, code blocks and
asides. A relative link to a docs page's source (`../../research/gates.md`) or to another post
(`../other-post/index.md`) becomes the page's address on the site; a link to any other file of the
repository becomes a GitHub link pinned to the published commit; a link that would be dead stops
the build. The hand-written pages of the site (the status page, the roadmap, the battery) have no
Markdown source, so they are linked by their full address.

## Images, diagrams and charts

Images sit beside `index.md` in the post's folder, with no subfolders, and are linked by their name:
`![What the figure shows, in one sentence](figure.png)`. The alt text is required, because it is all
a screen reader gets: staging refuses an image without it. A file may be PNG, JPEG, WebP, AVIF, GIF
or SVG, at most 4 MiB, named with letters, digits, dots, hyphens, underscores and tildes, never
starting with a dot. Staging refuses any other file in a post's folder.

An SVG is served from the same address as the editor below, so staging refuses one whose root is not
an SVG element, or that holds a script, an event attribute, `foreignObject`, an embedded frame or
object, a processing instruction (an XSLT stylesheet among them), an element of the XSLT namespace,
a `javascript:` address, a DOCTYPE or entity declaration, a link to anything outside the file, or CSS
that loads anything (`url()` or `@import`), except a `#fragment` or a PNG, JPEG, WebP or GIF data
address. Text inside an SVG is read by the same copy checks as the post.

A diagram or a simple chart can also be written as a Mermaid fence, as on the docs pages. Its
drawing is made ahead of time: run `npm run diagrams` in `website/` and commit the file it writes
under `website/src/diagrams/`. Staging stops when a fence has no current drawing.

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
4. Open a pull request. It publishes when it is merged, once the checks the main branch requires
   (`governance`, `build` and every `run_tests`) have passed. The Pages workflow then deploys it.

## Publishing from the editor

The editor at [/psyche/admin/](https://cagancaliskan.github.io/psyche/admin/) writes the same files
through the GitHub API, so a post written there is checked exactly as one written in a clone. It
never writes to `main` and it cannot publish:

| In the editor | On GitHub |
|---|---|
| Save a new post (its address is typed once, when it is created) | A branch `cms/posts/<slug>` from `main`, one commit `docs(blog): add <slug>` with the post and its images, and a pull request |
| Save again | Another commit on the same branch and pull request |
| Draft, In Review, Ready | A label on the pull request |
| Delete a post | A pull request that removes its folder |
| Publish | Not offered: open the pull request on GitHub, wait for the required checks, and merge it there |

Publishing stays on GitHub on purpose. The ruleset on `main` lets an administrator merge a pull
request whose checks failed, and a merge button inside the editor would do that without showing the
checks. Every save, a draft included, is public on GitHub at once, in the branch and the pull
request, before anything is published on the site.

To sign in, create a fine-grained personal access token on GitHub (Settings, Developer settings,
Personal access tokens, Fine-grained tokens): resource owner `cagancaliskan`, access to
`cagancaliskan/psyche` only, the repository permissions Contents (read and write) and Pull requests
(read and write) and nothing else, and an expiry of a week or less. Do not grant Workflows. Paste
it under "Sign In Using Access Token", and sign out when you are done.

What protects the editor, and what does not:

- The page is not indexed, sends no referrer and carries a content security policy: scripts load
  only from the pinned version of the editor on unpkg, and the browser refuses its main file unless
  its bytes match the integrity hash in the page. `npm run build` fails if the page loses any of
  this.
- The token stays in the browser's local storage while you are signed in, and every project page
  of `cagancaliskan.github.io` shares that storage. A script on any of those pages could read it.
  Signing out removes it, and a short expiry and the one-repository scope limit what a lost token
  can do. Without the Workflows permission it cannot change the workflow files, but it can push a
  branch that changes the scripts they run, and a pull request from a branch of this repository runs
  its checks with the repository's secrets. So treat a token that may have leaked as a leak of those
  secrets too: delete it on GitHub at once, and look over the open `cms/` branches and pull
  requests.
- The image dialog inside a post offers a global location beside the post's own folder, and the
  editor's Asset Library page writes to it. A picture there is refused when the post is staged, and
  the Asset Library's commits to `main` are refused by the ruleset: always pick the post's own
  folder. JPEG and PNG uploads are saved as WebP.

The version is pinned in `website/public/admin/index.html`, in the script address, the integrity
hash and the content security policy. To upgrade, hash `dist/sveltia-cms.js` of the new npm package,
check that unpkg serves the same bytes, change all three, and open a pull request.
