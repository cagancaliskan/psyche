// lib/devdocs.ts on fixtures. The staged list (src/data/docs.json) is never read here: it exists only
// after staging, and `npm test` runs before. What is read are sources: docs/publish.json (the manifest
// the list is staged from), tools/ledger.json (its program states) and the three site pages' own files.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  DEVELOPERS_LEAD,
  DEVELOPERS_ROUTE,
  START_SLUGS,
  countLabel,
  entriesOf,
  navGroups,
  neighbours,
  pageEditUrl,
  pageFacts,
  sourceEditUrl,
  startEntries,
  tocOf,
  type DocsData,
} from './devdocs.ts';
import { PAGES } from './head.ts';
import { REPO_URL } from './seo.ts';

const doc = (slug: string, title: string) => ({ kind: 'doc' as const, slug, title, description: `What ${title} Says.` });
const DATA: DocsData = {
  groups: [
    { title: 'Start here', items: [doc('guide', "Reader's guide"), doc('faq', 'Questions and answers'), { kind: 'page', route: 'roadmap', title: 'Explore the timeline' }] },
    { title: 'Cognitive maps', items: [doc('research', 'Overview'), doc('research/roadmap', 'Roadmap'), doc('research/test-battery', 'Test battery')] },
    { title: 'Substrate', items: [doc('substrate/overview', 'The substrate')] },
  ],
};

test('every page of the list in order, with its path, group, description and the filter text', () => {
  const all = entriesOf(DATA);
  assert.deepEqual(all.map((e) => e.route), ['guide', 'faq', 'roadmap', 'research', 'research/roadmap', 'research/test-battery', 'substrate/overview']);
  assert.deepEqual(all.map((e) => e.path), ['guide/', 'faq/', 'roadmap/', 'research/', 'research/roadmap/', 'research/test-battery/', 'substrate/overview/']);
  const guide = all[0];
  assert.equal(guide.group, 'Start here');
  assert.equal(guide.kind, 'doc');
  assert.equal(guide.text, "reader's guide what reader's guide says. start here");
  // a page of the site takes its description from lib/head.ts PAGES
  const timeline = all[2];
  assert.equal(timeline.kind, 'page');
  assert.equal(timeline.description, PAGES.roadmap.description);
  assert.equal(timeline.text, `explore the timeline ${PAGES.roadmap.description.toLowerCase()} start here`);
  assert.equal(all[6].text.endsWith(' substrate'), true);
});

test('a page of the site with no entry in PAGES, a page listed twice, or a route with a slash is refused', () => {
  assert.throws(() => pageFacts('no-such-page'), /does not describe/);
  assert.throws(() => entriesOf({ groups: [{ title: 'G', items: [{ kind: 'page', route: 'nowhere', title: 'X' }] }] }), /does not describe/);
  assert.throws(() => entriesOf({ groups: [{ title: 'G', items: [doc('guide', 'A'), doc('guide', 'B')] }] }), /listed twice/);
  assert.throws(() => entriesOf({ groups: [{ title: 'G', items: [doc('/guide', 'A')] }] }), /without slashes/);
  assert.throws(() => entriesOf({ groups: [{ title: 'G', items: [doc('guide/', 'A')] }] }), /without slashes/);
  assert.throws(() => entriesOf({ groups: [{ title: 'G', items: [{ ...doc('guide', 'A'), description: ' ' }] }] }), /no title or no description/);
  // a description can be given for a page by the caller
  const given = entriesOf({ groups: [{ title: 'G', items: [{ kind: 'page', route: 'nowhere', title: 'X' }] }] }, (route) => ({ route, title: 'X', description: 'Given.' }));
  assert.equal(given[0].description, 'Given.');
});

test('the navigation: groups in order, the current page marked, none marked on the home', () => {
  const groups = navGroups(DATA, 'research/roadmap');
  assert.deepEqual(groups.map((g) => g.title), ['Start here', 'Cognitive maps', 'Substrate']);
  assert.deepEqual(groups.flatMap((g) => g.items.filter((i) => i.current).map((i) => i.route)), ['research/roadmap']);
  assert.deepEqual(groups.map((g) => g.items.length), [3, 3, 1]);
  const home = navGroups(DATA);
  assert.equal(home.flatMap((g) => g.items).some((i) => i.current), false);
  assert.throws(() => navGroups(DATA, 'research/nowhere'), /not in the documentation list/);
  // an empty group is not drawn
  assert.deepEqual(navGroups({ groups: [{ title: 'Empty', items: [] }, ...DATA.groups] }).map((g) => g.title), ['Start here', 'Cognitive maps', 'Substrate']);
});

test('previous and next walk the whole list, the pages of the site included, across groups', () => {
  const all = entriesOf(DATA);
  assert.deepEqual(neighbours(all, 'guide'), { prev: null, next: all[1] });
  assert.equal(neighbours(all, 'faq').next?.route, 'roadmap');
  assert.equal(neighbours(all, 'roadmap').prev?.route, 'faq');
  assert.equal(neighbours(all, 'roadmap').next?.route, 'research');
  assert.equal(neighbours(all, 'research').prev?.route, 'roadmap');
  assert.deepEqual(neighbours(all, 'substrate/overview'), { prev: all[5], next: null });
  assert.throws(() => neighbours(all, 'nowhere'), /not in the documentation list/);
});

test('"Where to start": the reader\'s guide, the roadmap document and the test battery, in that order', () => {
  assert.deepEqual([...START_SLUGS], ['guide', 'research/roadmap', 'research/test-battery']);
  const start = startEntries(entriesOf(DATA));
  assert.deepEqual(start.map((e) => [e.route, e.title, e.path]), [
    ['guide', "Reader's guide", 'guide/'],
    ['research/roadmap', 'Roadmap', 'research/roadmap/'],
    ['research/test-battery', 'Test battery', 'research/test-battery/'],
  ]);
  // a starting page must be a document of the list (the timeline page is not the roadmap document)
  assert.throws(() => startEntries(entriesOf(DATA), ['roadmap']), /not a document of the list/);
  assert.throws(() => startEntries(entriesOf(DATA), ['research/gates']), /not a document of the list/);
});

test('the starting pages are published documents (docs/publish.json, a source)', () => {
  const manifest = JSON.parse(readFileSync(new URL('../../../docs/publish.json', import.meta.url), 'utf8'));
  const slugs = new Set(manifest.sections.flatMap((s: { pages: { slug: string }[] }) => s.pages.map((p) => p.slug)));
  for (const slug of START_SLUGS) assert.ok(slugs.has(slug), `${slug} is not a page of docs/publish.json`);
  assert.ok(!slugs.has(DEVELOPERS_ROUTE), 'a manifest page takes the documentation home\'s address');
});

test('the home: its route, its opening sentence, its head facts and its count', () => {
  assert.equal(DEVELOPERS_ROUTE, 'developers');
  assert.equal(PAGES.developers.route, DEVELOPERS_ROUTE);
  assert.equal(DEVELOPERS_LEAD, 'The documentation, records and source code behind Psyche.');
  assert.equal(countLabel(21), '21 pages');
  assert.equal(countLabel(1), '1 page');
});

test('"On this page": h2 and h3 with an id, in order, h3 as a sub-entry; nothing else', () => {
  const toc = tocOf([
    { depth: 1, slug: 'title', text: 'Title' },
    { depth: 2, slug: 'purpose', text: 'Purpose' },
    { depth: 3, slug: 'fairness-checklist', text: ' Fairness checklist ' },
    { depth: 4, slug: 'deep', text: 'Deep' },
    { depth: 2, slug: '', text: 'No id' },
    { depth: 2, slug: 'references', text: 'References' },
  ]);
  assert.deepEqual(toc, [
    { href: '#purpose', text: 'Purpose', sub: false },
    { href: '#fairness-checklist', text: 'Fairness checklist', sub: true },
    { href: '#references', text: 'References', sub: false },
  ]);
  assert.deepEqual(tocOf([{ depth: 1, slug: 't', text: 'T' }]), []);
});

test('edit links: a document\'s Markdown, a site page\'s page file, both on the repository\'s main branch', () => {
  assert.equal(sourceEditUrl('docs/research/test-battery.md'), `${REPO_URL}/blob/main/docs/research/test-battery.md`);
  assert.equal(pageEditUrl('roadmap'), `${REPO_URL}/blob/main/website/src/pages/roadmap.astro`);
  for (const bad of ['', '/etc/passwd', '../x.md', 'https://example.org/x.md']) assert.throws(() => sourceEditUrl(bad), /not a path/);
});

test('the three site pages in the list say what their own page files say (one description each)', () => {
  for (const key of ['roadmap', 'battery', 'status'] as const) {
    const file = readFileSync(new URL(`../pages/${key}.astro`, import.meta.url), 'utf8');
    const own = file.includes(`...PAGES.${key}`) || (file.includes(`title: '${PAGES[key].title}'`) && file.includes(`description: '${PAGES[key].description}'`));
    assert.ok(own, `src/pages/${key}.astro states a title or description that lib/head.ts PAGES.${key} does not`);
  }
});

test('no section title of the manifest carries a program state in brackets', () => {
  // The navigation's group names are docs/publish.json's section titles, shown as typed. A state is
  // typed once, in the ledger (program, D-031), and read from there. A bracketed "(active)" or "(paused)"
  // beside a group would be a second copy that goes stale the day a line is paused or resumed, so no
  // title carries one. A bracketed word that is not a program state says what a stage is, not where it
  // stands, and is not checked here.
  const repo = new URL('../../../', import.meta.url);
  const read = (rel: string) => JSON.parse(readFileSync(new URL(rel, repo), 'utf8'));
  const states = new Set<string>(read('tools/ledger.json').program_states.map((w: string) => w.toLowerCase()));
  assert.ok(states.size >= 2, 'the ledger lists its program states');
  /** The program states a title names inside (), [] or {}. */
  const bracketed = (title: string) =>
    [...title.matchAll(/[(\[{]([^)\]}]*)[)\]}]/g)].flatMap((g) => g[1].toLowerCase().split(/[^a-z]+/)).filter((w) => states.has(w));
  for (const section of read('docs/publish.json').sections as { title: string }[]) {
    assert.deepEqual(bracketed(section.title), [], `"${section.title}" names a state in brackets: the ledger holds program state, so drop it from the title in docs/publish.json`);
  }
  // the check bites: labels of that kind would fail it
  assert.deepEqual(bracketed('Cognitive maps (active)'), ['active']);
  assert.deepEqual(bracketed('Cognitive maps [Paused]'), ['paused']);
  assert.deepEqual(bracketed('Substrate (foundation)'), []);
  assert.deepEqual(bracketed('Cognitive maps'), []);
});
