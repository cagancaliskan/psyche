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
// This is the step that markdown.rehypePlugins would be. Astro 7 renders Markdown with Satteri, whose
// plugins work on the same HTML tree (hast) but are registered on the processor; the legacy rehype
// option would need @astrojs/markdown-remark, which the site does not install. The plugin is added by a
// small integration, the way Starlight adds its own to the same list (astro.config.mjs). It uses the
// standard library only.

const HEADINGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
const PREFIX = 'Table: ';

const clean = (text) => String(text ?? '').replace(/\s+/g, ' ').trim();

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
        filter: [...HEADINGS, 'table'],
        visit(node, ctx) {
          if (node.tagName !== 'table') {
            heading = ctx.textContent(node);
            return;
          }
          const caption = (node.children ?? []).find((c) => c.type === 'element' && c.tagName === 'caption');
          let label = regionName(caption ? ctx.textContent(caption) : '', heading);
          const n = (seen.get(label) ?? 0) + 1;
          seen.set(label, n);
          if (n > 1) label += ` (${n})`;
          return {
            type: 'element',
            tagName: 'div',
            properties: { class: 'sx-table', role: 'region', tabindex: '0', 'aria-label': label },
            children: [node],
          };
        },
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
