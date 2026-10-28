// Every table of a Markdown page goes into a keyboard-reachable, named region:
//
//   <div class="sx-table" role="region" tabindex="0" aria-label="Table: Reveal log"><table>...</table></div>
//
// A table wider than its column scrolls sideways (styles/docs.css), and a scrolling box that cannot take
// focus cannot be scrolled from the keyboard (WCAG 2.1.1; axe: scrollable-region-focusable). The box has
// to be a tab stop even where it does not scroll, because static markup cannot know the width of the
// reader's screen; the diagrams' scroll box is the same. The region is named after the table's own
// caption or else the nearest heading before it, so a reader of a screen reader hears which table it is;
// two tables under one heading are told apart by a number.
//
// The same plugin marks a cell that holds a calendar date with `data-nowrap` (styles/docs.css keeps it on
// one line). A date is "2026-10-23", and a browser may break a line after either hyphen: in a narrow column
// of a table that fits a phone, the date then reads "2026-10-" over "23". The cell is marked, not given a
// class, because the table rules in docs.css leave out any cell that has a class, and the text is left as
// it is, so a date is still plain ASCII to copy and to search. A date anywhere else in running text, such
// as the generated status line, is put in a `<span data-nowrap>` for the same reason; code is left alone.
//
// This is the step that markdown.rehypePlugins would be. Astro 7 renders Markdown with Satteri, whose
// plugins work on the same HTML tree (hast) but are registered on the processor; the legacy rehype
// option would need @astrojs/markdown-remark, which the site does not install. The plugin is added by a
// small integration, the way Starlight adds its own to the same list (astro.config.mjs). It uses the
// standard library only.

const HEADINGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
const PREFIX = 'Table: ';
// A cell that is a date, or a date after one or two plain words ("decided on 2026-11-14"). A longer cell is
// prose that may wrap at its spaces, and keeping all of it on one line would widen the table for nothing.
const DATE_CELL = /^(?:[A-Za-z]+ ){0,2}\d{4}-\d{2}-\d{2}$/;
// A date inside running text, standing alone: not part of a longer word, number or run of hyphens.
const DATE_IN_TEXT = /(?<![\w-])\d{4}-\d{2}-\d{2}(?![\w-])/g;
// Text in these keeps its exact characters: code is copied as it is.
const VERBATIM = new Set(['code', 'pre', 'kbd', 'samp', 'script', 'style']);

const clean = (text) => String(text ?? '').replace(/\s+/g, ' ').trim();

/** Whether a table cell's text is a date that must stay on one line. */
export function isDateCell(text) {
  return DATE_CELL.test(clean(text));
}

/**
 * A text's pieces with every date in a `<span data-nowrap>`, or null when it holds no date. The text is
 * cut, never changed, so the pieces read back as the same characters.
 */
export function splitDates(text) {
  const parts = [];
  let last = 0;
  for (const m of String(text).matchAll(DATE_IN_TEXT)) {
    if (m.index > last) parts.push({ type: 'text', value: text.slice(last, m.index) });
    parts.push({ type: 'element', tagName: 'span', properties: { dataNowrap: '' }, children: [{ type: 'text', value: m[0] }] });
    last = m.index + m[0].length;
  }
  if (!parts.length) return null;
  if (last < text.length) parts.push({ type: 'text', value: text.slice(last) });
  return parts;
}

/** The region's name: the caption if there is one, else the heading before the table, else just "Table". */
export function regionName(caption, heading) {
  const name = clean(caption) || clean(heading);
  return name ? PREFIX + name : 'Table';
}

/**
 * The hast plugin. A factory, so that each document starts with no heading read and no table counted.
 * Visitors are called in document order, so the heading last seen is the nearest one before a table,
 * however deep the table is nested.
 */
export function tableRegion() {
  return () => {
    let heading = '';
    const seen = new Map();
    return {
      name: 'psyche-table-region',
      element: {
        filter: [...HEADINGS, 'table', 'td'],
        visit(node, ctx) {
          if (node.tagName === 'td') {
            if (isDateCell(ctx.textContent(node))) ctx.setProperty(node, 'dataNowrap', '');
            return;
          }
          if (node.tagName !== 'table') {
            heading = ctx.textContent(node);
            return;
          }
          const caption = (node.children ?? []).find((c) => c.type === 'element' && c.tagName === 'caption');
          let label = regionName(caption ? ctx.textContent(caption) : '', heading);
          const n = (seen.get(label) ?? 0) + 1;
          seen.set(label, n);
          if (n > 1) label += ` (${n})`;
          // wrapNode, not a returned wrapper holding the table: a date in a cell may be patched in the same
          // pass, and Satteri refuses to replace a node whose descendants it is also patching.
          ctx.wrapNode(node, {
            type: 'element',
            tagName: 'div',
            properties: { class: 'sx-table', role: 'region', tabindex: '0', 'aria-label': label },
            children: [],
          });
        },
      },
      text(node, ctx) {
        const parent = ctx.parent(node);
        if (parent?.type !== 'element' || VERBATIM.has(parent.tagName)) return;
        // A whole cell that is a date is already kept on one line by its marker.
        if (parent.tagName === 'td' && isDateCell(ctx.textContent(parent))) return;
        const parts = splitDates(node.value);
        if (parts) ctx.replaceNode(node, parts);
      },
    };
  };
}

/** An Astro integration that appends the plugin to the Satteri processor, or stops the build if there is none. */
export function tableRegionIntegration() {
  return {
    name: 'psyche-table-region',
    hooks: {
      'astro:config:setup': ({ config }) => {
        const processor = config.markdown?.processor;
        if (processor?.name !== 'satteri' || !Array.isArray(processor.options?.hastPlugins)) {
          throw new Error(
            'psyche-table-region: the Markdown processor is not Satteri, so tables would not get their scroll regions; update scripts/table-region.mjs for the new processor.',
          );
        }
        processor.options.hastPlugins.push(tableRegion());
      },
    },
  };
}
