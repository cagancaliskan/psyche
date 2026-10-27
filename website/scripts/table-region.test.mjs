import { test } from 'node:test';
import assert from 'node:assert/strict';
import { markdownToHtml } from 'satteri';
import { regionName, tableRegion, tableRegionIntegration } from './table-region.mjs';

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
