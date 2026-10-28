// Draws the Mermaid diagrams of the published pages into static SVG, ahead of the build.
//
// The governed Markdown keeps its ```mermaid fences (GitHub draws them there). The site does not
// run Mermaid in the browser: tools/publish/stage.py puts one of the files this script writes,
// website/src/diagrams/<key>.svg, inline in place of each fence. So a reader's browser downloads
// no diagram code, sees no flash of source, and gets the drawing with JavaScript off.
//
//   node scripts/render-diagrams.mjs            draw what is missing, delete what no page uses
//   node scripts/render-diagrams.mjs --force    draw everything again
//   node scripts/render-diagrams.mjs --chrome PATH   (or CHROME_PATH) pick the browser
//
// Run it after changing a diagram, after `python3 tools/publish/render_plan.py --write` moves a
// date in the gantt or the gate flow, or after changing this file; then commit website/src/diagrams/.
// `python3 tools/publish/diagrams.py --check` (governance runs it) fails when a fence has no
// current drawing. The file name is a key over this file's own bytes and the fence's text
// (tools/publish/diagrams.py), so editing anything below, the pinned versions and the
// post-processing included, names new keys and asks for a new drawing; nothing can drift.
//
// What the SVG holds. Mermaid lays the diagram out in Chrome with the site's mono face, so label
// widths are the ones the reader sees. Everything that paints is then taken out: Mermaid's
// style sheet, its inline colours, and any literal colour. What stays is the geometry, the
// classes Mermaid gave the shapes, dash patterns (a class definition may dash a node) and a
// title and description written from the diagram itself (a gantt item the plan leaves undated,
// marked * by render_plan.py, is described as undated, never with the date it is drawn at; the
// name is the title and the description is a separate relation, so a reader of the page's
// accessibility tree hears each once). The colours come from the page:
// src/styles/docs.css paints `.sx-diagram` from the site's tokens, so one file reads in both
// themes. The gantt's "today" marker is dropped: a drawing made once cannot know the date.
//
// Three choices for the width of the page's text column, all made here and never in the governed
// Markdown: a flowchart written left to right is drawn top to bottom, a gantt is laid out at 690px
// and labelled every second month, and the stadium shape is a square with a second square inside it.
//
// And some of the drawing's notation, so that docs.css can paint a drafting figure (hairlines, square
// corners, no fill) and the timeline can read as the roadmap's does (styles/plan.css). The geometry
// CSS cannot reach is changed here: a rect's rounded corners (rx) are taken off, a connection is a
// right-angled trace and not a slanting line (down, across between two rows, down), an arrowhead is an
// open chevron and not a filled triangle, a gantt phase is a thin bar centred on its row (6px, 8px when
// it is in progress) with its label beside it (a label that Mermaid set inside a bar is moved out of
// it), a gate is a small square with four ticks beyond its sides in place of a rotated, rounded square,
// the bands behind the phases are one rule across the figure at the top of each phase and one for the
// axis, and whatever the plan leaves undated (marked * in its name by render_plan.py) is told by the
// class `open` on its bar or gate, so that docs.css can draw it differently. Nothing it draws adds,
// removes or changes a word.
//
// This is a development tool and nothing the site ships. Its two packages are not in
// package.json: the script installs them at the exact versions below into a private cache in
// website/node_modules/.cache the first time it runs (DIAGRAM_TOOLS_DIR changes where), never a
// shared temporary directory, since it loads code from there. The Mono face is the one
// the site already depends on (@fontsource-variable/martian-mono, in node_modules).
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { delimiter, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const TOOLS = { mermaid: '11.17.2', 'puppeteer-core': '25.12.0' };
const ROOT = resolve(fileURLToPath(new URL('../../', import.meta.url)));
const FONT_FILE = fileURLToPath(
  new URL('../node_modules/@fontsource-variable/martian-mono/files/martian-mono-latin-wght-normal.woff2', import.meta.url),
);
const FONT = '"Martian Mono Variable", ui-monospace, monospace';
// The text column of a docs page is at most 45rem and about 630px beside the sidebars of a laptop
// screen; the figure's padding takes 56px of it. The gantt is laid out to the narrowest width at
// which the longest task name, set to the left of its bar, still clears the phase titles, and the
// page then shows it at about 0.8 of that.
const GANTT_WIDTH = 690;

function arg(name) {
  const i = process.argv.indexOf(name);
  return i > -1 ? process.argv[i + 1] : undefined;
}

function ensureTools() {
  const dir = process.env.DIAGRAM_TOOLS_DIR || join(ROOT, 'website', 'node_modules', '.cache', 'psyche-diagram-tools');
  // Code is loaded from this directory, so it must be ours alone: created private, and refused
  // if it already exists owned by someone else or writable by group or others.
  mkdirSync(dir, { recursive: true, mode: 0o700 });
  if (typeof process.getuid === 'function') {
    const st = statSync(dir);
    if (st.uid !== process.getuid() || (st.mode & 0o022) !== 0) {
      throw new Error(`render-diagrams: ${dir} must be owned by you and not group- or world-writable`);
    }
  }
  const installed = (name, version) => {
    try {
      return JSON.parse(readFileSync(join(dir, 'node_modules', name, 'package.json'), 'utf8')).version === version;
    } catch {
      return false;
    }
  };
  if (!Object.entries(TOOLS).every(([n, v]) => installed(n, v))) {
    mkdirSync(dir, { recursive: true });
    console.log(`render-diagrams: installing ${Object.entries(TOOLS).map(([n, v]) => `${n}@${v}`).join(', ')} into ${dir}`);
    execFileSync(
      'npm',
      ['install', '--prefix', dir, '--no-save', '--no-audit', '--no-fund', '--ignore-scripts', '--loglevel=error',
        ...Object.entries(TOOLS).map(([n, v]) => `${n}@${v}`)],
      { stdio: 'inherit' },
    );
  }
  const req = createRequire(join(dir, 'noop.js'));
  return { puppeteer: req('puppeteer-core'), mermaidSource: readFileSync(req.resolve('mermaid/dist/mermaid.min.js'), 'utf8') };
}

function findChrome() {
  const given = arg('--chrome') || process.env.CHROME_PATH;
  if (given) {
    if (!existsSync(given)) throw new Error(`the Chrome given (${given}) does not exist`);
    return given;
  }
  const fixed = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
  ];
  for (const p of fixed) if (existsSync(p)) return p;
  for (const name of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
    for (const dir of (process.env.PATH || '').split(delimiter)) {
      const p = join(dir, name);
      if (dir && existsSync(p)) return p;
    }
  }
  throw new Error('no Chrome or Chromium found; pass --chrome PATH or set CHROME_PATH');
}

// ---------------------------------------------------------------------------------------------
// In the page: draw one diagram, strip it to geometry, describe it, and write it out as text.
// This function is serialised into Chrome, so it may use nothing from this file.
// ---------------------------------------------------------------------------------------------
async function drawInPage({ key, source: given, font, ganttWidth }) {
  await document.fonts.load(`400 12px ${font}`);
  if (![...document.fonts].some((f) => f.family.includes('Martian Mono') && f.status === 'loaded')) {
    throw new Error('the Mono face did not load; labels would be measured in another face');
  }
  const NS = 'http://www.w3.org/2000/svg';
  const id = `dg-${key}`;
  // A chain of labelled boxes drawn left to right is 900 to 1300px wide in a Mono face, and the
  // column is about 600: it would shrink to unreadable type. A flowchart written LR or RL is drawn
  // top to bottom; the connections, labels and classes are the source's, only the axis changes.
  const turned = given.replace(/^(\s*(?:flowchart|graph)\s+)(?:LR|RL)\b/m, '$1TB');
  // A gantt with a tick a month is labelled "Feb 2027Mar 2027" at this width: the labels are as
  // wide as the months. A label every second month reads.
  const source = /^\s*gantt\b/m.test(turned) && !/^\s*tickInterval\b/m.test(turned) ? `${turned}\n    tickInterval 2month` : turned;

  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    theme: 'base',
    logLevel: 5,
    fontFamily: font,
    themeVariables: { fontFamily: font, fontSize: '12px' },
    flowchart: { htmlLabels: false, curve: 'linear', padding: 10, nodeSpacing: 28, rankSpacing: 38, useMaxWidth: false },
    gantt: {
      fontSize: 10, sectionFontSize: 10, barHeight: 18, barGap: 6, leftPadding: 70, rightPadding: 16,
      gridLineStartPadding: 24, useWidth: ganttWidth, useMaxWidth: false, numberSectionStyles: 4,
    },
  });

  // Mermaid's own entity syntax: #80; is a code point, #quot; is a named character. Once parsed,
  // its model holds them as private markers (a code point as two marks, a name as one, both closed
  // by a pilcrow mark); both spellings are read here.
  const NAMED = { quot: '"', amp: '&', lt: '<', gt: '>', apos: "'", nbsp: '\u00a0', semi: ';', num: '#' };
  const entity = (s) =>
    String(s)
      .replace(/#(\d+);|\ufb02\u00b0\u00b0(\d+)\u00b6\u00df/g, (_, a, b) => String.fromCodePoint(Number(a ?? b)))
      .replace(/#([A-Za-z][A-Za-z0-9]*);|\ufb02\u00b0([A-Za-z][A-Za-z0-9]*)\u00b6\u00df/g, (m, a, b) => NAMED[a ?? b] ?? m);
  const plain = (s) => entity(String(s).replace(/<br\s*\/?>/gi, ' ')).replace(/\s+/g, ' ').trim();
  const day = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

  // What the diagram says, from Mermaid's own model of it, for the title and description.
  const diagram = await mermaid.mermaidAPI.getDiagramFromText(source);
  const type = String(diagram.type);
  let kind;
  let title;
  const sentences = [];
  if (type.startsWith('flowchart')) {
    kind = 'flowchart';
    const nodes = [...diagram.db.getVertices().values()];
    const text = new Map(nodes.map((v) => [v.id, plain(v.text ?? v.id)]));
    const edges = diagram.db.getEdges();
    const groups = diagram.db.getSubGraphs();
    title = `Flowchart of ${nodes.length} steps${nodes.length ? `, starting at ${text.get(nodes[0].id)}` : ''}`;
    sentences.push(`Steps: ${nodes.map((v) => text.get(v.id)).join('; ')}.`);
    if (groups.length) {
      sentences.push(groups.map((g) => `${plain(g.title)} holds ${g.nodes.map((n) => text.get(n) ?? n).join(', ')}.`).join(' '));
    }
    if (edges.length) {
      sentences.push(`Connections: ${edges.map((e) => {
        const dashed = e.stroke && e.stroke !== 'normal' ? `, ${e.stroke}` : '';
        const label = e.text ? ` (${plain(e.text)}${dashed})` : dashed ? ` (${dashed.slice(2)})` : '';
        return `${text.get(e.start) ?? e.start} to ${text.get(e.end) ?? e.end}${label}`;
      }).join('; ')}.`);
    }
  } else if (type === 'gantt') {
    kind = 'timeline';
    const tasks = diagram.db.getTasks();
    // render_plan.py writes " *" after the name of a phase or gate whose date the plan does not fix
    // and draws it up to a horizon it derives. That position is not a date, so the text alternative
    // gives none for it, and the range in the title is that of the dated items only.
    const undated = (t) => / \*$/.test(plain(t.task));
    const dated = tasks.filter((t) => !undated(t));
    const first = dated.reduce((a, t) => (a === null || t.startTime < a ? t.startTime : a), null);
    const last = dated.reduce((a, t) => (a === null || t.endTime > a ? t.endTime : a), null);
    const range = first ? `${day(first)} to ${day(last)}` : '';
    const open = dated.length < tasks.length;
    title = `Timeline of ${tasks.length} items${range ? (open ? `; the dated ones run ${range}` : `, ${range}`) : ''}`;
    let section = null;
    for (const t of tasks) {
      const lead = t.section !== section ? `${plain(t.section)}: ` : '';
      section = t.section;
      const name = plain(t.task).replace(/ \*$/, '');
      if (undated(t)) sentences.push(`${lead}${name}, ${t.milestone ? 'date' : 'dates'} not fixed.`);
      else if (t.milestone) sentences.push(`${lead}${name}, ${day(t.startTime)}.`);
      else sentences.push(`${lead}${name}, ${day(t.startTime)} to ${day(t.endTime)}${t.active ? ', in progress' : ''}.`);
    }
    if (open) sentences.push('Items marked * on the chart have no fixed date; their place on it is not a date.');
  } else {
    throw new Error(`no description for diagram type ${type}`);
  }

  if (/[\ufb02\u00b6]/.test(title + sentences.join(' '))) throw new Error('Mermaid entity marker left in the description');
  const { svg } = await mermaid.render(id, source);
  // Parsed as an inert document, then placed in the page so shapes can be measured.
  const root = document.adoptNode(new DOMParser().parseFromString(svg, 'text/html').querySelector('svg'));
  root.style.cssText = 'position:absolute;left:0;top:0;visibility:hidden';
  document.body.append(root);

  // -- the dash a class definition gives a node survives as a plain attribute --
  const dashOf = (style) => {
    const m = /(?:^|;)\s*stroke-dasharray\s*:\s*([^;!]+)/i.exec(style || '');
    if (!m) return null;
    const v = m[1].replace(/px/gi, '').replace(/,/g, ' ').replace(/\s+/g, ' ').trim();
    return v && !/^(0|1 0|none)$/.test(v) ? v : null;
  };
  const KEEP_STYLE = new Set(['stroke-width', 'text-anchor', 'font-style', 'font-weight']);
  for (const el of root.querySelectorAll('[style]')) {
    const style = el.getAttribute('style');
    const dash = el.closest('.node, .cluster') ? dashOf(style) : null;
    for (const decl of style.split(';')) {
      const [prop, ...rest] = decl.split(':');
      const name = (prop || '').trim().toLowerCase();
      const value = rest.join(':').replace(/!important/gi, '').trim();
      if (KEEP_STYLE.has(name) && value && !el.hasAttribute(name)) el.setAttribute(name, value);
    }
    el.removeAttribute('style');
    if (dash) el.setAttribute('stroke-dasharray', dash);
  }
  root.querySelectorAll('style, defs, script, foreignObject, linearGradient, radialGradient, filter').forEach((el) => el.remove());

  // Mermaid draws a stadium (a node written ([...])) as two hand-drawn paths of some 12 kB of
  // numbers each; here it is a square with a second square inside it (the class `terminal-inner`),
  // so the terminal of a flow is still told from a step by its shape.
  for (const outer of root.querySelectorAll('g.outer-path')) {
    const b = outer.getBBox();
    const num = (n) => String(Number(n.toFixed(2)));
    const rect = document.createElementNS(NS, 'rect');
    rect.setAttribute('class', 'basic label-container');
    rect.setAttribute('x', num(b.x));
    rect.setAttribute('y', num(b.y));
    rect.setAttribute('width', num(b.width));
    rect.setAttribute('height', num(b.height));
    const inner = document.createElementNS(NS, 'rect');
    inner.setAttribute('class', 'terminal-inner');
    inner.setAttribute('x', num(b.x + 3));
    inner.setAttribute('y', num(b.y + 3));
    inner.setAttribute('width', num(b.width - 6));
    inner.setAttribute('height', num(b.height - 6));
    outer.replaceWith(rect, inner);
  }
  // Flowchart nodes are square: a rounded rect (rx) has its corners taken off.
  root.querySelectorAll('.node rect[rx], .node rect[ry]').forEach((el) => {
    el.removeAttribute('rx');
    el.removeAttribute('ry');
  });
  // Connections are right-angled traces, as in the figure under the title of the research overview: a
  // trace leaves a node level, turns in the gap between two rows and enters the next node level, in place
  // of Mermaid's slanting segments. Mermaid's own route is kept as the skeleton: the points it laid out
  // between two nodes (where the connection passes the rows in between, and where its label sits) stay
  // on the trace, so a connection never crosses a node and a label is still on its line. What changes is
  // how the points are joined (down, across at half the height between two points, down again), and
  // where a trace meets a node: a box is left and entered at the point above or below the trace, a
  // decision (a rhombus) at its vertices, and the end stops 4px short of the node, because the
  // arrowhead's tip stands that far past the end of the path (refX 5 of 10, drawn 8px wide), as Mermaid
  // ends every connection. A connection that does not run downward, or whose ends are not a box or a
  // rhombus, is left as Mermaid drew it.
  const TIP = 4;
  const shapes = [...root.querySelectorAll('g.node')]
    .map((node) => [...node.children].find((c) => /^(rect|polygon)$/.test(c.localName) && !c.classList.contains('terminal-inner')))
    .filter(Boolean);
  const num3 = (n) => String(Number(n.toFixed(3)));
  for (const path of root.querySelectorAll('path.flowchart-link')) {
    const d = path.getAttribute('d') || '';
    if (!/^[ML\d.,\s-]+$/.test(d) || !path.getAttribute('marker-end')) continue;
    const nums = (d.match(/-?\d*\.?\d+/g) || []).map(Number);
    if (nums.length < 4 || nums.length % 2) continue;
    const P = Array.from({ length: nums.length / 2 }, (_, i) => ({ x: nums[2 * i], y: nums[2 * i + 1] }));
    const last = P[P.length - 1];
    // Every point lower than the one before it.
    if (!(last.y > P[0].y + 2) || P.some((q, i) => i > 0 && q.y < P[i - 1].y - 0.01)) continue;
    // The nodes, in the path's own coordinates.
    const inv = path.getCTM().inverse();
    const boxes = shapes.map((shape) => {
      const bb = shape.getBBox();
      const m = inv.multiply(shape.getCTM());
      const a = new DOMPoint(bb.x, bb.y).matrixTransform(m);
      const b = new DOMPoint(bb.x + bb.width, bb.y + bb.height).matrixTransform(m);
      return { x0: Math.min(a.x, b.x), x1: Math.max(a.x, b.x), y0: Math.min(a.y, b.y), y1: Math.max(a.y, b.y), diamond: shape.localName === 'polygon' };
    });
    const nearest = (pt, slack) => {
      const hit = boxes.filter((b) => pt.x >= b.x0 - slack && pt.x <= b.x1 + slack && pt.y >= b.y0 - slack && pt.y <= b.y1 + slack);
      const dist = (b) => Math.hypot(pt.x - (b.x0 + b.x1) / 2, pt.y - (b.y0 + b.y1) / 2);
      return hit.sort((a, b) => dist(a) - dist(b))[0];
    };
    const from = nearest(P[0], 3);
    const to = nearest(last, TIP + 3);
    if (!from || !to || from === to) continue;
    // A point between the ends stays where it lies in a run that goes straight down (it has the x of a
    // neighbour) or where the connection's label is centred; any other is only Mermaid's slanting bend,
    // which the trace's own turn replaces.
    const labels = [...root.querySelectorAll('g.edgeLabel')].map((el) => {
      const m = inv.multiply(el.getCTM());
      return { x: m.e, y: m.f };
    });
    const mids = P.slice(1, -1).filter((q, i) => {
      const [before, after] = [P[i], P[i + 2]];
      return Math.abs(q.x - before.x) < 0.01 || Math.abs(q.x - after.x) < 0.01 || labels.some((l) => Math.hypot(l.x - q.x, l.y - q.y) < 1);
    });
    const first = mids[0] ?? last;
    const within = (x, b) => x >= b.x0 + 3 && x <= b.x1 - 3;
    const clamp = (x, b) => Math.min(Math.max(x, b.x0 + 3), b.x1 - 3);
    const mid = (b) => ({ x: (b.x0 + b.x1) / 2, y: (b.y0 + b.y1) / 2 });
    // Where the trace leaves: the bottom of a box at the point its first turn is above (or the nearest
    // point of the box); a rhombus at its bottom vertex, or at a side vertex when the trace is bound
    // for a point beyond that side.
    let start;
    let aside = false;
    if (from.diamond) {
      const c = mid(from);
      const half = (from.x1 - from.x0) / 2;
      if (first.x > c.x + half + 2) [start, aside] = [{ x: from.x1, y: c.y }, true];
      else if (first.x < c.x - half - 2) [start, aside] = [{ x: from.x0, y: c.y }, true];
      else start = { x: c.x, y: from.y1 };
    } else {
      start = { x: within(first.x, from) ? first.x : clamp(P[0].x, from), y: from.y1 };
    }
    // Where it enters: the top of a box, straight below its last turn when that is under the box; a
    // rhombus at its top vertex.
    const lastTurn = (mids.at(-1) ?? first).x;
    const endX = to.diamond ? mid(to).x : within(lastTurn, to) ? lastTurn : clamp(last.x, to);
    const stops = [...mids, { x: endX, y: to.y0 - TIP }];
    const out = [`M${num3(start.x)} ${num3(start.y)}`];
    let [cx, cy] = [start.x, start.y];
    const down = (y) => {
      if (out.length > 1 && out.at(-1).startsWith('V')) out.pop();
      out.push(`V${num3(y)}`);
    };
    if (aside) {
      cx = stops[0].x;
      out.push(`H${num3(cx)}`);
    }
    for (const q of stops) {
      if (Math.abs(q.x - cx) > 0.01) {
        down((cy + q.y) / 2);
        out.push(`H${num3(q.x)}`);
      }
      down(q.y);
      [cx, cy] = [q.x, q.y];
    }
    path.setAttribute('d', out.join(''));
  }

  // -- the gantt, in the roadmap's notation (styles/plan.css) --
  // The today marker is dropped: a drawing made once cannot know the date.
  root.querySelectorAll('g.today').forEach((el) => el.remove());
  const num2 = (n) => String(Number(n.toFixed(2)));
  const BAR = 6;
  const BAR_ACTIVE = 8;
  const GATE = 8;
  const STUB = 4;
  for (const rect of root.querySelectorAll('rect.task')) {
    const [x, y, w, h] = ['x', 'y', 'width', 'height'].map((n) => Number(rect.getAttribute(n)));
    const cx = x + w / 2;
    const cy = y + h / 2;
    const text = root.querySelector(`#${CSS.escape(`${rect.id}-text`)}`);
    if (!text) throw new Error(`gantt: no label for the item ${rect.id}`);
    for (const a of ['rx', 'ry', 'transform']) rect.removeAttribute(a);
    // The plan leaves an item undated when render_plan.py marks its name with *.
    const open = / \*\s*$/.test(text.textContent);
    if (open) rect.setAttribute('class', `${rect.getAttribute('class')} open`);
    if (rect.classList.contains('milestone')) {
      const half = GATE / 2;
      rect.setAttribute('x', num2(cx - half));
      rect.setAttribute('y', num2(cy - half));
      rect.setAttribute('width', String(GATE));
      rect.setAttribute('height', String(GATE));
      const ticks = document.createElementNS(NS, 'path');
      ticks.setAttribute('class', open ? 'gate-ticks open' : 'gate-ticks');
      ticks.setAttribute(
        'd',
        `M${num2(cx - half - STUB)} ${num2(cy)}H${num2(cx - half)}M${num2(cx + half)} ${num2(cy)}H${num2(cx + half + STUB)}` +
          `M${num2(cx)} ${num2(cy - half - STUB)}V${num2(cy - half)}M${num2(cx)} ${num2(cy + half)}V${num2(cy + half + STUB)}`,
      );
      rect.after(ticks);
      continue;
    }
    const bar = /\bactive\d\b/.test(rect.getAttribute('class')) ? BAR_ACTIVE : BAR;
    rect.setAttribute('y', num2(cy - bar / 2));
    rect.setAttribute('height', String(bar));
    // A label Mermaid set inside the bar does not fit a bar this thin: it goes beside it, to the right
    // if it fits in the figure and to the left if not, as Mermaid does for a label that is too wide.
    if (text.classList.contains('taskText')) {
      const tw = text.getBBox().width;
      const level = (text.getAttribute('class').match(/taskText(\d)/) || [, '0'])[1];
      const right = x + w + 5 + tw <= ganttWidth - 8;
      text.setAttribute('x', num2(right ? x + w + 5 : x - 5));
      text.setAttribute('class', right ? `taskTextOutsideRight taskTextOutside${level}` : `taskTextOutsideLeft taskTextOutside${level}`);
    }
  }
  // The bands behind the phases (a fill) become a rule at the top of each phase and one for the axis.
  const bands = [...root.querySelectorAll('rect.section')];
  if (bands.length) {
    const grid = root.querySelector('g.grid');
    const axisY = Number(/translate\(\s*[-\d.]+[\s,]+([-\d.]+)\s*\)/.exec(grid?.getAttribute('transform') || '')?.[1]);
    const first = Number(bands[0].getAttribute('y'));
    const last = bands.at(-1);
    const rules = [];
    let seen = '';
    for (const b of bands) {
      const kind = /\bsection\d\b/.exec(b.getAttribute('class'))?.[0] ?? '';
      if (kind !== seen) rules.push(Number(b.getAttribute('y')));
      seen = kind;
    }
    rules.push(Number.isFinite(axisY) ? axisY : Number(last.getAttribute('y')) + Number(last.getAttribute('height')));
    const width = bands[0].getAttribute('width');
    const host = bands[0].parentNode;
    for (const y of rules) {
      const line = document.createElementNS(NS, 'line');
      line.setAttribute('class', 'rule');
      line.setAttribute('x1', '0');
      line.setAttribute('x2', width);
      line.setAttribute('y1', num2(y));
      line.setAttribute('y2', num2(y));
      host.append(line);
    }
    bands.forEach((b) => b.remove());
    // The gridlines run from the axis up to the first rule, not above it.
    if (Number.isFinite(axisY)) grid.querySelectorAll('.tick line').forEach((l) => l.setAttribute('y2', num2(first - axisY)));
  }

  // -- text placement that Mermaid's style sheet gave by class --
  const anchor = (el, value) => el.setAttribute('text-anchor', value);
  root.querySelectorAll('.node text, .cluster text, .cluster-label text, .edgeLabel text').forEach((el) => anchor(el, 'middle'));
  root.querySelectorAll('text.taskText, text.titleText').forEach((el) => anchor(el, 'middle'));
  root.querySelectorAll('text.taskTextOutsideRight, text.sectionTitle').forEach((el) => anchor(el, 'start'));
  root.querySelectorAll('text.taskTextOutsideLeft').forEach((el) => anchor(el, 'end'));
  root.querySelectorAll('.edgePaths path, path.flowchart-link').forEach((el) => {
    el.setAttribute('fill', 'none');
    const c = el.getAttribute('class') || '';
    if (/edge-pattern-dashed/.test(c)) el.setAttribute('stroke-dasharray', '4 3');
    if (/edge-pattern-dotted/.test(c)) el.setAttribute('stroke-dasharray', '1.5 3');
    if (/edge-thickness-thick/.test(c)) el.setAttribute('stroke-width', '2');
  });
  // A group's title is painted last, so a connection that runs under it does not strike through it
  // (edges are drawn after the group boxes, and the title is part of its box). The box and the title
  // have no transform between them and the root group, so the title keeps its place.
  for (const label of [...root.querySelectorAll('g.cluster-label')]) {
    const target = label.closest('g.root');
    let plainPath = Boolean(target);
    for (let n = label.parentElement; plainPath && n && n !== target; n = n.parentElement) {
      if (n.hasAttribute('transform')) plainPath = false;
    }
    if (plainPath) target.append(label);
  }
  root.querySelectorAll('.grid').forEach((el) => el.setAttribute('fill', 'none'));
  root.querySelectorAll('.grid .domain').forEach((el) => el.remove());

  // -- no literal colours, no stray metadata, no empty shells --
  const COLOUR = /^(#|rgb|hsl|black|white|red|navy|grey|gray|lightgrey|lightgray)/i;
  for (const el of root.querySelectorAll('*')) {
    for (const a of ['fill', 'stroke']) {
      const v = el.getAttribute(a);
      if (v && COLOUR.test(v.trim())) el.removeAttribute(a);
    }
    for (const a of ['font-family', 'transform-origin', 'data-points', 'data-look', 'data-et', 'data-edge', 'data-id', 'dominant-baseline']) {
      el.removeAttribute(a);
    }
    if (el.getAttribute('font-weight') === 'normal') el.removeAttribute('font-weight');
    if (el.getAttribute('font-style') === 'normal') el.removeAttribute('font-style');
    const cls = [...new Set((el.getAttribute('class') || '').split(/\s+/).filter((c) => c && !/^width-/.test(c)))];
    if (cls.length) el.setAttribute('class', cls.join(' '));
    else el.removeAttribute('class');
  }
  // A row of a label is one text node, not one tspan per word.
  root.querySelectorAll('tspan.text-outer-tspan').forEach((row) => {
    const words = [...row.children];
    const plainWords = words.length && words.every((c) => c.localName === 'tspan' && [...c.attributes].every((a) => a.name === 'class'));
    if (plainWords) row.textContent = words.map((c) => c.textContent).join('');
    row.removeAttribute('class');
  });
  root.querySelectorAll('text').forEach((el) => {
    if (!el.textContent.trim()) el.remove();
  });
  root.querySelectorAll('rect:not([width])').forEach((el) => el.remove());
  root.querySelectorAll('g.edgeLabel').forEach((el) => {
    if (!el.textContent.trim()) el.remove();
  });
  for (let pass = 0; pass < 6; pass += 1) {
    root.querySelectorAll('g').forEach((el) => {
      if (!el.children.length) el.remove();
    });
  }
  // an id stays only where something points at it
  const markup = root.outerHTML;
  const kept = new Set();
  for (const m of markup.matchAll(/url\(#([^)]+)\)/g)) kept.add(m[1]);
  root.querySelectorAll('[id]').forEach((el) => {
    if (!kept.has(el.id)) el.removeAttribute('id');
  });
  root.querySelectorAll('marker').forEach((el) => {
    if (!el.id) el.remove();
  });
  root.querySelectorAll('marker *').forEach((el) => {
    el.removeAttribute('stroke-dasharray');
    el.removeAttribute('stroke-width');
  });
  // An arrowhead is an open chevron, a hairline like the connection it ends (the tip stays where the
  // filled triangle's was).
  root.querySelectorAll('marker path.arrowMarkerPath').forEach((el) => {
    if (el.getAttribute('d') === 'M 0 0 L 10 5 L 0 10 z') el.setAttribute('d', 'M 1 0.75 L 10 5 L 1 9.25');
  });

  // -- the root: size, role, name, description --
  // The box is the drawing's own extent plus a margin: a label set to the left of a bar may reach past
  // Mermaid's frame, and the gantt keeps empty room above its first row.
  const extent = root.getBBox();
  const margin = 8;
  const box = [extent.x - margin, extent.y - margin, extent.width + 2 * margin, extent.height + 2 * margin];
  const [w, h] = [Math.ceil(box[2]), Math.ceil(box[3])];
  for (const a of [...root.attributes].map((x) => x.name)) root.removeAttribute(a);
  const titleEl = document.createElementNS(NS, 'title');
  titleEl.id = `${id}-t`;
  titleEl.textContent = title;
  const descEl = document.createElementNS(NS, 'desc');
  descEl.id = `${id}-d`;
  descEl.textContent = sentences.join(' ');
  root.prepend(titleEl, descEl);
  const set = (n, v) => root.setAttribute(n, v);
  set('xmlns', NS);
  set('role', 'img');
  // The name is the title alone; the description is a separate relation, so a screen reader reads
  // the step list once, not once as part of the name and again as the description.
  set('aria-labelledby', `${id}-t`);
  set('aria-describedby', `${id}-d`);
  set('data-key', key);
  set('data-diagram', kind);
  set('font-size', kind === 'flowchart' ? '12' : '10');
  set('viewBox', box.map((n) => Number(n.toFixed(2))).join(' '));
  set('width', String(w));
  set('height', String(h));

  // -- text out: one element per line, except inside <text>, where a line break would be a space --
  const esc = (s, attr) => {
    const out = s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return attr ? out.replace(/"/g, '&quot;') : out;
  };
  const ser = (el, depth) => {
    const pad = ' '.repeat(depth);
    const name = el.localName;
    const attrs = [...el.attributes].map((a) => ` ${a.name}="${esc(a.value, true)}"`).join('');
    if (name === 'text') return `${pad}<text${attrs}>${[...el.childNodes].map((n) => (n.nodeType === 3 ? esc(n.data, false) : inline(n))).join('')}</text>`;
    if (!el.childNodes.length) return `${pad}<${name}${attrs}/>`;
    if (name === 'title' || name === 'desc') return `${pad}<${name}${attrs}>${esc(el.textContent, false)}</${name}>`;
    return `${pad}<${name}${attrs}>\n${[...el.children].map((c) => ser(c, depth + 1)).join('\n')}\n${pad}</${name}>`;
  };
  const inline = (el) => {
    const attrs = [...el.attributes].map((a) => ` ${a.name}="${esc(a.value, true)}"`).join('');
    const inner = [...el.childNodes].map((n) => (n.nodeType === 3 ? esc(n.data, false) : inline(n))).join('');
    return `<${el.localName}${attrs}>${inner}</${el.localName}>`;
  };
  return `${ser(root, 0)}\n`;
}

// ---------------------------------------------------------------------------------------------

async function main() {
  const force = process.argv.includes('--force');
  const listing = JSON.parse(
    execFileSync('python3', ['-B', join(ROOT, 'tools/publish/diagrams.py'), '--list', '--root', ROOT], { encoding: 'utf8' }),
  );
  const dir = join(ROOT, listing.directory);
  mkdirSync(dir, { recursive: true });

  const wanted = new Set(listing.diagrams.map((d) => d.key));
  const todo = listing.diagrams.filter((d) => force || !existsSync(join(dir, `${d.key}.svg`)));
  let removed = 0;
  for (const name of readdirSync(dir)) {
    if (!wanted.has(name.replace(/\.svg$/, ''))) {
      rmSync(join(dir, name), { recursive: true });
      removed += 1;
      console.log(`render-diagrams: removed ${name} (no page uses it)`);
    }
  }
  if (!todo.length) {
    console.log(`render-diagrams: ${wanted.size} diagram(s), all drawn${removed ? `; ${removed} removed` : ''}`);
    return;
  }
  if (!existsSync(FONT_FILE)) throw new Error('the Mono face is missing: run `npm ci` in website/ first');

  const { puppeteer, mermaidSource } = ensureTools();
  const font64 = readFileSync(FONT_FILE).toString('base64');
  const browser = await puppeteer.launch({ executablePath: findChrome(), headless: true, args: ['--no-sandbox'] });
  try {
    for (const d of todo) {
      const page = await browser.newPage();
      try {
        await page.setViewport({ width: GANTT_WIDTH, height: 900, deviceScaleFactor: 1 });
        await page.setContent(
          `<!doctype html><meta charset="utf-8"><style>@font-face{font-family:"Martian Mono Variable";font-weight:100 800;` +
            `src:url(data:font/woff2;base64,${font64}) format("woff2")}html,body{margin:0;padding:0;width:${GANTT_WIDTH}px}</style><body></body>`,
        );
        await page.addScriptTag({ content: mermaidSource });
        const svg = await page.evaluate(drawInPage, { key: d.key, source: d.source, font: FONT, ganttWidth: GANTT_WIDTH });
        writeFileSync(join(dir, `${d.key}.svg`), svg, 'utf8');
        console.log(`render-diagrams: drew ${d.key}  ${d.where.join(', ')}`);
      } finally {
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
  console.log(`render-diagrams: ${todo.length} drawn, ${wanted.size - todo.length} already current${removed ? `, ${removed} removed` : ''}`);
}

main().catch((e) => {
  console.error(`render-diagrams: ${e.message}`);
  process.exit(1);
});
