import { test } from 'node:test';
import assert from 'node:assert/strict';
import { markdownToHtml } from 'satteri';
import { isDateCell, regionName, splitDates, tableRegion, tableRegionIntegration } from './table-region.mjs';

// The plugin is tested on the processor Astro uses, with the same table syntax the docs use.
const render = (md) => markdownToHtml(md, { hastPlugins: [tableRegion()] }).html;
const regions = (html) => [...html.matchAll(/<div class="sx-table"[^>]*>/g)].map((m) => m[0]);
const label = (tag) => /aria-label="([^"]*)"/.exec(tag)?.[1];

const TABLE = '| A | B |\n|---|---|\n| 1 | 2 |\n';

test('a table is wrapped in a focusable, named region', () => {
  const html = render(`## Reveal log\n\n${TABLE}`);
  assert.match(html, /<div class="sx-table" role="region" tabindex="0" aria-label="Table: Reveal log"><table>/);
  assert.match(html, /<\/table>\s*<\/div>/);
  assert.equal(regions(html).length, 1);
});

test('the nearest heading before the table names it, at any depth', () => {
  const html = render(`# Top\n\n${TABLE}\n## Second\n\n- item\n\n  ${TABLE.replace(/\n(?=.)/g, '\n  ')}\n> ### Quoted\n>\n> ${TABLE.replace(/\n(?=.)/g, '\n> ')}`);
  assert.deepEqual(regions(html).map(label), ['Table: Top', 'Table: Second', 'Table: Quoted']);
});

test('two tables under one heading are told apart, and a table with no heading is still named', () => {
  assert.deepEqual(regions(render(`## Log\n\n${TABLE}\ntext\n\n${TABLE}`)).map(label), ['Table: Log', 'Table: Log (2)']);
  assert.deepEqual(regions(render(TABLE)).map(label), ['Table']);
});

test('a heading with markup is named by its words, and the count starts again in the next document', () => {
  assert.deepEqual(regions(render(`## The \`gate\` *log*\n\n${TABLE}`)).map(label), ['Table: The gate log']);
  assert.deepEqual(regions(render(`## Log\n\n${TABLE}`)).map(label), ['Table: Log']);
});

test('a page with no table is unchanged', () => {
  assert.equal(render('## Log\n\ntext\n'), markdownToHtml('## Log\n\ntext\n').html);
});

test('a cell that holds a date is marked to stay on one line, and no other cell is', () => {
  const html = render('## Log\n\n| Date | What | Status |\n|---|---|---|\n| 2026-10-23 | Phase P0 started on 2026-10-23 and went on | decided on 2026-11-14 |\n| soon | 2026-13-45x | 12 |\n');
  const cells = [...html.matchAll(/<td([^>]*)>(.*?)<\/td>/g)].map((m) => [m[2], m[1].trim()]);
  assert.deepEqual(cells, [
    ['2026-10-23', 'data-nowrap=""'],
    ['Phase P0 started on <span data-nowrap="">2026-10-23</span> and went on', ''],
    ['decided on 2026-11-14', 'data-nowrap=""'],
    ['soon', ''],
    ['2026-13-45x', ''],
    ['12', ''],
  ]);
  assert.ok(!/<th[^>]*data-nowrap/.test(html), 'a header cell is never marked');
  assert.ok(!/<td[^>]*class=/.test(html), 'a marked cell has no class, which the table rules would skip');
  assert.match(html, /<div class="sx-table" role="region"/);
});

test('a date in running text is kept on one line, and code and other numbers are left alone', () => {
  const html = render(
    '**Now:** P0 Setup (2026-10-23 to 2026-11-15) · **Next gate:** A, 2026-11-15\n\n- since 2026-10-23.\n\nRun `--as-of 2026-10-23` or 12026-10-23, 2026-10-231, 2026-10-23x and 2026-10-23-1.\n',
  );
  const spans = [...html.matchAll(/<span data-nowrap="">([^<]*)<\/span>/g)].map((m) => m[1]);
  assert.deepEqual(spans, ['2026-10-23', '2026-11-15', '2026-11-15', '2026-10-23']);
  assert.match(html, /<code>--as-of 2026-10-23<\/code>/);
  assert.match(html, /\(<span data-nowrap="">2026-10-23<\/span> to <span data-nowrap="">2026-11-15<\/span>\)/);
  assert.match(html, /<li>since <span data-nowrap="">2026-10-23<\/span>\.<\/li>/);
});

test('splitDates cuts a text around its dates without changing a character', () => {
  assert.equal(splitDates('no date here, 2026-1-2'), null);
  const parts = splitDates('from 2026-10-23 to 2026-11-15');
  assert.deepEqual(parts.map((p) => (p.type === 'text' ? p.value : `[${p.children[0].value}]`)), ['from ', '[2026-10-23]', ' to ', '[2026-11-15]']);
  assert.equal(parts.map((p) => (p.type === 'text' ? p.value : p.children[0].value)).join(''), 'from 2026-10-23 to 2026-11-15');
});

test('isDateCell takes a date, alone or after one or two plain words, and nothing longer', () => {
  assert.equal(isDateCell(' 2026-10-23 '), true);
  assert.equal(isDateCell('decided on 2026-11-14'), true);
  assert.equal(isDateCell('one two three 2026-11-14'), false);
  assert.equal(isDateCell('2026-10-23 and later'), false);
  assert.equal(isDateCell('20261-10-23'), false);
  assert.equal(isDateCell(''), false);
});

test('regionName prefers the caption, then the heading, then plain "Table"', () => {
  assert.equal(regionName('  Gate  decisions ', 'Elsewhere'), 'Table: Gate decisions');
  assert.equal(regionName('', ' Reveal   log '), 'Table: Reveal log');
  assert.equal(regionName('', '   '), 'Table');
  assert.equal(regionName(undefined, undefined), 'Table');
});

test('the integration adds the plugin to the Satteri processor and refuses any other', () => {
  const processor = { name: 'satteri', options: { hastPlugins: [] } };
  tableRegionIntegration().hooks['astro:config:setup']({ config: { markdown: { processor } } });
  assert.equal(processor.options.hastPlugins.length, 1);
  assert.throws(
    () => tableRegionIntegration().hooks['astro:config:setup']({ config: { markdown: { processor: { name: 'unified', options: {} } } } }),
    /not Satteri/,
  );
  assert.throws(() => tableRegionIntegration().hooks['astro:config:setup']({ config: {} }), /not Satteri/);
});
