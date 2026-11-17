import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { markdownToHtml } from 'satteri';
import { arrange, copyTree, digest, normalise, plainText, postFigures, postSlug, readPlan } from './post-figures.mjs';

const WEB = fileURLToPath(new URL('../', import.meta.url));
const KIT = join(WEB, 'src', 'kit');
// The posts are read from their committed sources (docs/blog/<slug>/index.md), never from a staged copy:
// this test runs before staging.
const POSTS_DIR = join(WEB, '..', 'docs', 'blog');

// The top-level nodes of a document as the processor makes them, copied out of its pass.
function blocksOf(md) {
  let kids = [];
  markdownToHtml(md, { hastPlugins: [() => ({ name: 'read', before(root) { kids = root.children.map(copyTree); } })] });
  return kids;
}
const render = (md, plan, still = () => '<svg><title>t</title></svg>') =>
  markdownToHtml(md, { hastPlugins: [() => ({ name: 'place', before(root, ctx) { ctx.replaceNode(root, { type: 'root', children: arrange(root.children, plan, still) }); } })] }).html;

const MD = 'First words.\n\n## Part one: the start\n\n![A drawing.](old.svg)\n\nSecond words.\n\n## Part two\n\nThird words.\n';
const d = (kind, text) => ({ kind, digest: digest(kind, text) });
const PLAN = {
  post: 'sample',
  replaces: ['old.svg'],
  sequence: [
    { read: { className: ['k-read', 'x-read'], id: 'reading' }, blocks: [d('p', 'First words.')] },
    {
      node: {
        type: 'element', tagName: 'section', properties: { className: ['x-q'], dataKWide: '' },
        children: [
          { type: 'block', ...d('h2', 'Part one: the start'), set: { className: ['x-q__h'], dataKPart: 'Part one' },
            children: [{ type: 'element', tagName: 'span', properties: {}, children: [{ type: 'text', value: 'Part one:' }] }, { type: 'text', value: ' ' },
              { type: 'element', tagName: 'span', properties: {}, children: [{ type: 'text', value: 'the start' }] }] },
          { type: 'element', tagName: 'figure', properties: { className: ['k-figure'], dataFigure: 'f', ariaDescribedby: 'f-cap' },
            children: [{ type: 'still', file: 'f.svg', properties: { className: ['k-still', 'k-still--both'], dataKStill: 'f' } },
              { type: 'element', tagName: 'figcaption', properties: { className: ['k-cap'], id: 'f-cap' }, children: [{ type: 'text', value: 'A caption.' }] }] },
        ],
      },
    },
    { read: { className: ['k-read', 'x-read'] }, blocks: [d('p', 'Second words.'), { ...d('h2', 'Part two'), set: { dataKPart: 'Two' } }, d('p', 'Third words.')] },
  ],
};

test('the text and its figures are laid out as the plan says, with the replaced image left out', () => {
  const html = render(MD, PLAN);
  assert.match(html, /^<div class="k-read x-read" id="reading"><p>First words\.<\/p><\/div>/);
  assert.match(html, /<section class="x-q" data-k-wide=""><h2 class="x-q__h" data-k-part="Part one"><span>Part one:<\/span> <span>the start<\/span><\/h2>/);
  assert.match(html, /<figure class="k-figure" data-figure="f" aria-describedby="f-cap"><div class="k-still k-still--both" data-k-still="f"><svg><title>t<\/title><\/svg><\/div><figcaption class="k-cap" id="f-cap">A caption\.<\/figcaption><\/figure>/);
  assert.match(html, /<div class="k-read x-read"><p>Second words\.<\/p>\n<h2 data-k-part="Two">Part two<\/h2>\n<p>Third words\.<\/p><\/div>\n?$/);
  assert.ok(!html.includes('old.svg'), 'the image the figure stands in for is not on the page');
  // every word of the post is there, once
  for (const w of ['First words.', 'Second words.', 'Third words.', 'Part two']) assert.equal(html.split(w).length, 2, w);
});

test('a post that changed after its figures were placed stops the build, and says where', () => {
  assert.throws(() => render(MD.replace('Second words.', 'Other words.'), PLAN), /block 3 \(reading column 3\) is a p reading "Other words\."/);
  assert.throws(() => render(MD.replace('## Part one: the start', '## Part one: a start'), PLAN), /block 2 \(part 2\) is a h2/);
  assert.throws(() => render(MD + '\nA new paragraph.\n', PLAN), /1 block\(s\) of the post have no place among its figures, from "A new paragraph\."/);
  assert.throws(() => render(MD.replace('\nThird words.\n', ''), PLAN), /expect a p at block 5 \(reading column 3\), but the post ends there/);
  assert.throws(() => render(MD.replace('![A drawing.](old.svg)', ''), PLAN), /stand in for the image old\.svg, which the post no longer shows/);
});

test('a heading split into the design\'s spans must keep its own words', () => {
  const bad = structuredClone(PLAN);
  bad.sequence[1].node.children[0].children[2].children[0].value = 'the end';
  assert.throws(() => render(MD, bad), /splits the h2 "Part one: the start" into words that are not its own/);
});

test('words are compared as written, whatever the typography', () => {
  assert.equal(normalise('“close to zero” – it’s…  done'), '"close to zero" - it\'s... done');
  assert.equal(plainText({ type: 'element', children: [{ type: 'raw', value: '<var>' }, { type: 'text', value: 'P' }, { type: 'raw', value: '</var> &lt; 1' }] }), 'P < 1');
  assert.equal(digest('p', 'a “b”'), digest('p', 'a  "b"'));
  assert.notEqual(digest('p', 'a'), digest('h2', 'a'));
});

test('only a staged post with a folder under src/kit/posts/ is touched', () => {
  assert.equal(postSlug(new URL('file:///x/website/src/content/docs/blog/my-post/index.md')), 'my-post');
  assert.equal(postSlug(new URL('file:///x/website/src/content/docs/guide.md')), null);
  assert.equal(postSlug(undefined), null);
  const factory = postFigures();
  assert.equal(factory({ fileURL: new URL('file:///x/website/src/content/docs/blog/no-such-post/index.md') }), undefined);
  assert.equal(factory({ fileURL: new URL('file:///x/website/src/content/docs/guide.md') }), undefined);
  assert.equal(markdownToHtml(MD, { hastPlugins: [factory] }).html, markdownToHtml(MD).html);
});

// The imported folders, against the posts' committed sources.
const designed = existsSync(join(KIT, 'posts')) ? readdirSync(join(KIT, 'posts'), { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name) : [];

test('every post folder of the kit belongs to a post and is complete', () => {
  for (const slug of designed) {
    assert.ok(existsSync(join(POSTS_DIR, slug, 'index.md')), `src/kit/posts/${slug}/ is not a post of docs/blog/`);
    for (const f of ['Open.astro', 'page.css', 'page.js', 'figures.json']) assert.ok(existsSync(join(KIT, 'posts', slug, f)), `src/kit/posts/${slug}/${f} is missing: re-run the page import`);
  }
});

test("each designed post's figures fit its Markdown as committed: every block placed once, every replaced image found, every still there", () => {
  for (const slug of designed) {
    const plan = readPlan(slug, KIT);
    const md = readFileSync(join(POSTS_DIR, slug, 'index.md'), 'utf8').replace(/^---\n[\s\S]*?\n---\n/, '');
    const files = [];
    const kids = arrange(blocksOf(md), plan, (f) => { files.push(f); return readFileSync(join(KIT, 'stills', 'posts', slug, f), 'utf8'); });
    assert.ok(kids.length > 0, slug);
    for (const f of plan.replaces) assert.match(md, new RegExp(`\\]\\(${f.replace(/\./g, '\\.')}\\)`), `${slug}: ${f}`);
    assert.ok(files.length > 0, `${slug}: no still read`);
    // figure ids are unique on the page (the opening's included), and each is drawn by the post's script
    const open = readFileSync(join(KIT, 'posts', slug, 'Open.astro'), 'utf8');
    const ids = [...(open + JSON.stringify(plan)).matchAll(/data-figure="([\w-]+)"|"dataFigure": ?"([\w-]+)"/g)].map((m) => m[1] || m[2]);
    assert.equal(new Set(ids).size, ids.length, `${slug}: a figure id twice: ${ids}`);
    const js = readFileSync(join(KIT, 'posts', slug, 'page.js'), 'utf8');
    for (const id of ids) assert.match(js, new RegExp(`\\bid: '${id}'`), `${slug}: figure ${id} is not registered by its script`);
    assert.doesNotMatch(js, /\binnerHTML\b|\bouterHTML\b|\binsertAdjacentHTML\b|\bdocument\.write|\beval\s*\(|\bnew\s+Function\b/, `${slug}: page.js writes markup or evaluates code`);
  }
});
