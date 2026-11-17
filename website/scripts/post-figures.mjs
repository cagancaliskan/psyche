// A post's own figures, placed in its text the way the post's page design places them.
//
// A post is Markdown and stays Markdown: nothing here changes its words, headings, addresses or file.
// A post that has a page design gets a folder written by the page import, src/kit/posts/<slug>/:
// Open.astro (the opening, used by layouts/Post.astro), page.css, page.js (the figures' script) and
// figures.json, which this step reads. Its stills are in src/kit/stills/posts/<slug>/. A post with no
// such folder is left exactly as it is.
//
// figures.json is data only. `sequence` lists, in order, the parts of the page between its opening and
// its close:
//   { "read": { properties }, "blocks": [ { "kind", "digest", "set"? }, ... ] }
//       a reading column (div.k-read) that holds the next Markdown blocks: each is checked against the
//       post (its kind, h2 or p or ul, and a digest of its text), and `set` adds a class or a part name
//       (data-k-part, the rail's label) to it;
//   { "node": { a hast element } }
//       something the design puts between two columns: a figure, or a chapter that opens on one of the
//       post's own headings. Inside it, { "type": "block", "kind", "digest", "set", "children"? } is the
//       next Markdown block, taken out of the text and placed there (with `children`, the same words
//       split into the design's spans; their text must be the heading's text), and
//       { "type": "still", "file", "properties" } is the figure's baked still, read from its .svg file.
// `replaces` names the images of the Markdown that the figures stand in for: their paragraphs are left
// out of the page. The image stays in the post (GitHub shows it, and the post is complete without the
// site); the feeds carry no images.
//
// Every block of the post must be placed exactly once, in order, and every image named in `replaces`
// must be found; otherwise the build stops and says where. A post revised after its figures were
// imported therefore fails loudly instead of losing a figure or a paragraph: re-run the page import.
//
// Figure markup is built as tree nodes with properties, never as a string with values written into it;
// the only text that goes in as it is (a `raw` node) is a still, a file of src/kit/ written by the
// import. The step runs before the heading ids and the code blocks are made (the processor's own steps,
// after this one), so a heading keeps the id it would have had, in the same order.
//
// The Satteri counterpart of a rehype plugin, registered like scripts/table-region.mjs. It uses the
// standard library only.
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const KIT = fileURLToPath(new URL('../src/kit/', import.meta.url));
// A staged post: src/content/docs/blog/<slug>/index.md (tools/publish/stage.py).
const POST_FILE = /[\\/]src[\\/]content[\\/]docs[\\/]blog[\\/]([a-z0-9-]+)[\\/]index\.md$/;

const ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
const decode = (s) =>
  s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (all, e) => {
    if (e[0] === '#') return String.fromCodePoint(e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10));
    return ENTITIES[e.toLowerCase()] ?? all;
  });

/** A string with its tags left out. Repeated until nothing changes, so that removing one tag cannot leave another behind. */
const withoutTags = (s) => {
  let before;
  do {
    before = s;
    s = s.replace(/<[^>]*>/g, '');
  } while (s !== before);
  return s;
};

/** The words of a node: its text, and the text of inline HTML written in the Markdown, tags left out. */
export function plainText(node) {
  if (!node) return '';
  if (node.type === 'text') return node.value;
  if (node.type === 'raw') return decode(withoutTags(node.value));
  return (node.children ?? []).map(plainText).join('');
}

/** Text as compared: typographic quotes, dashes, ellipses and spaces written one way. */
export function normalise(text) {
  return String(text)
    .replace(/[‘’‚‛′]/g, "'")
    .replace(/[“”„‟″]/g, '"')
    .replace(/[‐‑–—]/g, '-')
    .replace(/…/g, '...')
    .replace(/\s+/g, ' ')
    .trim();
}

const classes = (node) => {
  const c = node?.properties?.className ?? node?.properties?.class ?? [];
  return Array.isArray(c) ? c.map(String) : String(c).split(/\s+/).filter(Boolean);
};

/** A block's kind: its tag; a table in its scroll region (scripts/table-region.mjs) is a table. */
export function blockKind(node) {
  if (node?.type !== 'element') return node?.type ?? 'none';
  if (node.tagName === 'div' && classes(node).includes('sx-table')) return 'table';
  return node.tagName;
}

/** The file name of the one image a paragraph holds and nothing else, or null. */
export function imageOnly(node) {
  if (node?.type !== 'element' || node.tagName !== 'p') return null;
  const kids = (node.children ?? []).filter((c) => !(c.type === 'text' && !c.value.trim()));
  if (kids.length !== 1 || kids[0].type !== 'element' || kids[0].tagName !== 'img') return null;
  const src = kids[0].properties?.src;
  return typeof src === 'string' && src ? basename(decodeURI(src.split(/[?#]/)[0])) : null;
}

/** A block's fingerprint: its kind and its text, normalised. */
export function digest(kind, text) {
  return createHash('sha256').update(`${kind}\n${normalise(text)}`).digest('hex').slice(0, 16);
}

/** A plain copy of a node and everything under it, which stays readable after the processor's pass. */
export function copyTree(node) {
  const out = { type: node.type };
  if (node.tagName !== undefined) out.tagName = node.tagName;
  if (node.properties !== undefined) out.properties = { ...node.properties };
  if (node.value !== undefined) out.value = node.value;
  if (node.children !== undefined) out.children = node.children.map(copyTree);
  return out;
}

const isBlank = (n) => n.type === 'text' && !n.value.trim();
// A comment is not a block: the staged copy of a post opens with one (stage.py's "generated from" note).
const isComment = (n) => n.type === 'comment' || (n.type === 'raw' && /^\s*<!--[\s\S]*?-->\s*$/.test(n.value));
const preview = (node) => {
  const t = normalise(plainText(node));
  return JSON.stringify(t.length > 70 ? t.slice(0, 67) + '...' : t);
};

function withSet(node, set) {
  if (!set) return node;
  const props = { ...(node.properties ?? {}) };
  for (const [k, v] of Object.entries(set)) {
    if (k === 'className') props.className = [...classes(node), ...v];
    else props[k] = v;
  }
  return { ...node, properties: props };
}

/**
 * The post's blocks arranged as its page design lays them out: the new list of the document's top-level
 * nodes, or an Error that says what does not match. `still(file)` returns a still's SVG text.
 */
export function arrange(children, plan, still) {
  const where = `post ${plan.post}`;
  const blocks = [];
  const comments = [];
  const replaced = new Map((plan.replaces ?? []).map((f) => [f, 0]));
  for (const node of children) {
    if (isBlank(node)) continue;
    if (isComment(node)) { comments.push(node); continue; }
    const img = imageOnly(node);
    if (img && replaced.has(img)) { replaced.set(img, replaced.get(img) + 1); continue; }
    blocks.push(node);
  }
  for (const [f, n] of replaced) {
    if (n === 0) throw new Error(`${where}: its figures stand in for the image ${f}, which the post no longer shows; re-run the page import`);
  }
  let at = 0;
  const take = (want, context) => {
    const node = blocks[at];
    if (!node) throw new Error(`${where}: its figures expect a ${want.kind} at block ${at + 1} (${context}), but the post ends there; re-run the page import`);
    const kind = blockKind(node);
    if (kind !== want.kind || digest(kind, plainText(node)) !== want.digest) {
      throw new Error(`${where}: block ${at + 1} (${context}) is a ${kind} reading ${preview(node)}, not the ${want.kind} its figures were placed against; the post changed after its figures were imported: re-run the page import`);
    }
    at++;
    return node;
  };
  const build = (spec, context) => {
    if (spec.type === 'text') return { type: 'text', value: String(spec.value) };
    if (spec.type === 'comment') return { type: 'comment', value: String(spec.value) };
    if (spec.type === 'still') {
      if (!/^[a-z0-9-]+\.svg$/.test(spec.file)) throw new Error(`${where}: a still's file name is not a plain .svg name: ${spec.file}`);
      return { type: 'element', tagName: 'div', properties: { ...spec.properties }, children: [{ type: 'raw', value: still(spec.file) }] };
    }
    if (spec.type === 'block') {
      const node = withSet(take(spec, context), spec.set);
      if (!spec.children) return node;
      const split = spec.children.map((c) => build(c, context));
      if (normalise(plainText({ children: split })) !== normalise(plainText(node))) {
        throw new Error(`${where}: the design splits the ${spec.kind} ${preview(node)} into words that are not its own`);
      }
      return { ...node, children: split };
    }
    if (spec.type === 'element') {
      return { type: 'element', tagName: spec.tagName, properties: { ...(spec.properties ?? {}) }, children: (spec.children ?? []).map((c) => build(c, context)) };
    }
    throw new Error(`${where}: unknown node in figures.json: ${JSON.stringify(spec.type)}`);
  };
  const out = [...comments];
  for (const [n, item] of (plan.sequence ?? []).entries()) {
    if (out.length) out.push({ type: 'text', value: '\n' });
    if (item.read) {
      const kids = [];
      for (const want of item.blocks ?? []) {
        if (kids.length) kids.push({ type: 'text', value: '\n' });
        kids.push(withSet(take(want, `reading column ${n + 1}`), want.set));
      }
      out.push({ type: 'element', tagName: 'div', properties: { ...item.read }, children: kids });
    } else if (item.node) {
      out.push(build(item.node, `part ${n + 1}`));
    } else {
      throw new Error(`${where}: part ${n + 1} of figures.json is neither a reading column nor a node`);
    }
  }
  if (at !== blocks.length) {
    throw new Error(`${where}: ${blocks.length - at} block(s) of the post have no place among its figures, from ${preview(blocks[at])}; re-run the page import`);
  }
  return out;
}

/** The slug of a staged post's file, or null for any other document. */
export function postSlug(fileURL) {
  if (!fileURL) return null;
  const path = fileURL instanceof URL ? fileURLToPath(fileURL) : String(fileURL);
  return POST_FILE.exec(path)?.[1] ?? null;
}

/** The plan of a post's figures (src/kit/posts/<slug>/figures.json), or null when it has none. */
export function readPlan(slug, kit = KIT) {
  const file = join(kit, 'posts', slug, 'figures.json');
  if (!existsSync(file)) return null;
  const plan = JSON.parse(readFileSync(file, 'utf8'));
  if (plan.post !== slug) throw new Error(`src/kit/posts/${slug}/figures.json belongs to the post ${JSON.stringify(plan.post)}`);
  return plan;
}

/** The hast plugin: a factory, called once per document with the document's address. */
export function postFigures({ kit = KIT } = {}) {
  return ({ fileURL } = {}) => {
    const slug = postSlug(fileURL);
    const plan = slug ? readPlan(slug, kit) : null;
    if (!plan) return undefined;
    return {
      name: 'psyche-post-figures',
      before(root, ctx) {
        const children = arrange(root.children ?? [], plan, (file) => readFileSync(join(kit, 'stills', 'posts', slug, file), 'utf8').trim());
        ctx.replaceNode(root, { type: 'root', children });
      },
    };
  };
}

/** An Astro integration that appends the plugin to the Satteri processor, or stops the build if there is none. */
export function postFiguresIntegration() {
  return {
    name: 'psyche-post-figures',
    hooks: {
      'astro:config:setup': ({ config }) => {
        const processor = config.markdown?.processor;
        if (processor?.name !== 'satteri' || !Array.isArray(processor.options?.hastPlugins)) {
          throw new Error(
            'psyche-post-figures: the Markdown processor is not Satteri, so the posts would lose their figures; update scripts/post-figures.mjs for the new processor.',
          );
        }
        processor.options.hastPlugins.push(postFigures());
      },
    },
  };
}
