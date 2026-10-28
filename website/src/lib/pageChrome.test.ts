import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  STAGE_OF_SECTION,
  flattenLinks,
  footerDate,
  footerLinks,
  keepDays,
  nextGateText,
  sectionName,
  sectionOf,
  sectionOfRoute,
  sheetOf,
  stageLine,
  titleBlock,
  titleStrip,
  type SidebarItem,
} from './pageChrome.ts';
import type { Plan } from './plan.ts';
import { REPO_URL } from './seo.ts';

const REPO = new URL('../../../', import.meta.url);
const read = (rel: string) => JSON.parse(readFileSync(new URL(rel, REPO), 'utf8'));

const link = (label: string, isCurrent = false): SidebarItem => ({ type: 'link', label, href: `/psyche/${label.toLowerCase()}/`, isCurrent });
const group = (label: string, entries: SidebarItem[]): SidebarItem => ({ type: 'group', label, entries });

// The shape tools/publish/stage.py writes: "Start here" with the hand-written pages, then one group
// for each section of docs/publish.json.
const sidebar = (current: string): SidebarItem[] => [
  group('Start here', [link('Home', current === 'Home'), link('Step through the paradigms', current === 'Battery')]),
  group('Cognitive maps', [link('Overview', current === 'Overview'), link('Decision gates', current === 'Gates')]),
  group('Substrate', [link('The substrate', current === 'Substrate')]),
];

test('a section name is the sidebar group\'s label, as it stands', () => {
  assert.equal(sectionName('Cognitive maps'), 'Cognitive maps');
  assert.equal(sectionName('Substrate'), 'Substrate');
  assert.equal(sectionName('Start here'), 'Start here');
  assert.equal(sectionName('  Padded  '), 'Padded');
  // nothing is stripped: a state in a label would be shown as typed, which is why the manifest may not carry one
  assert.equal(sectionName('Cognitive maps (active)'), 'Cognitive maps (active)');
  assert.equal(sectionName('(all)'), '(all)');
  assert.equal(sectionName('Stage (1) notes'), 'Stage (1) notes');
});

test('the section of a page is the sidebar group that holds it, numbered as the sidebar numbers it', () => {
  assert.deepEqual(sectionOf(sidebar('Battery')), { index: '01', name: 'Start here' });
  assert.deepEqual(sectionOf(sidebar('Gates')), { index: '02', name: 'Cognitive maps' });
  assert.deepEqual(sectionOf(sidebar('Substrate')), { index: '03', name: 'Substrate' });
});

test('a page in no group has no section, and a nested group is found', () => {
  assert.equal(sectionOf(sidebar('Nowhere')), null);
  assert.equal(sectionOf([]), null);
  const nested = [group('Outer', [group('Inner', [link('Deep', true)])])];
  assert.deepEqual(sectionOf(nested), { index: '01', name: 'Outer' });
  // a link at the top of the sidebar is not a group: it takes no number and holds no page
  const mixed = [link('Loose', true), group('First', [link('A')]), group('Second', [link('B', true)])];
  assert.deepEqual(sectionOf(mixed), { index: '02', name: 'Second' });
});

test('the sheet number is the place among every link of the sidebar, counted from the sidebar', () => {
  assert.deepEqual(
    flattenLinks(sidebar('Gates')).map((l) => l.label),
    ['Home', 'Step through the paradigms', 'Overview', 'Decision gates', 'The substrate'],
  );
  assert.deepEqual(sheetOf(sidebar('Home')), { position: '1', total: '5', text: '1 / 5' });
  assert.deepEqual(sheetOf(sidebar('Gates')), { position: '4', total: '5', text: '4 / 5' });
  assert.equal(sheetOf(sidebar('Nowhere')), null);
  assert.equal(sheetOf([]), null);
  // padded to the width of the total, so the column of numbers does not jump from page to page
  const many = [group('G', Array.from({ length: 12 }, (_, i) => link(`P${i + 1}`, i === 4)))];
  assert.equal(sheetOf(many)?.text, '05 / 12');
  // a nested group is opened out, and a link with no address is still counted
  const nested = [group('A', [link('One'), group('B', [link('Two', true)])]), group('C', [link('Three')])];
  assert.equal(sheetOf(nested)?.text, '2 / 3');
});

test('every section of the publication manifest gives a section name, which is its title', () => {
  const manifest = read('docs/publish.json');
  for (const section of manifest.sections) {
    const name = sectionName(section.title);
    assert.ok(name.length > 0 && name === section.title, `"${section.title}" gives "${name}"`);
  }
});

const ledger = (substrate: object, cognitive: object) =>
  ({ program: { substrate, cognitive_map: cognitive } }) as Parameters<typeof stageLine>[1];
const LEDGER = ledger(
  { state: 'paused', since: '2026-10-23', decision: 'D-031' },
  { state: 'active', since: '2026-10-23', decision: 'D-031' },
);

test('a stage 2 page states the line active, a stage 1 page states it paused and since when', () => {
  assert.deepEqual(stageLine('research/gates', LEDGER), { stage: 2, state: 'active', since: null, text: 'Stage 2 · active' });
  assert.deepEqual(stageLine('research', LEDGER), { stage: 2, state: 'active', since: null, text: 'Stage 2 · active' });
  assert.deepEqual(stageLine('substrate/overview', LEDGER), {
    stage: 1,
    state: 'paused',
    since: { iso: '2026-10-23', label: '23 October 2026' },
    text: 'Stage 1 · paused since 23 October 2026',
  });
});

test('the state is read from the ledger, so a resumed or paused line changes the sentence', () => {
  const swapped = ledger({ state: 'active', since: '2027-01-05', decision: 'D-040' }, { state: 'paused', since: '2027-02-01', decision: 'D-041' });
  assert.equal(stageLine('substrate/architecture', swapped)?.text, 'Stage 1 · active');
  assert.equal(stageLine('research/roadmap', swapped)?.text, 'Stage 2 · paused since 1 February 2027');
  // a state the ledger might gain is repeated as it is
  const other = ledger({ state: 'archived', since: '2027-01-05', decision: 'D-040' }, LEDGER.program.cognitive_map);
  assert.equal(stageLine('substrate/overview', other)?.text, 'Stage 1 · archived');
});

test('a paused line without a date says paused and no more; a line with no state says nothing', () => {
  assert.equal(stageLine('substrate/overview', ledger({ state: 'paused', decision: 'D-031' }, LEDGER.program.cognitive_map))?.text, 'Stage 1 · paused');
  assert.equal(stageLine('substrate/overview', ledger({ state: '' }, LEDGER.program.cognitive_map)), null);
  assert.equal(stageLine('research/gates', { program: { substrate: LEDGER.program.substrate } } as never), null);
});

test('only the pages of the two stage sections carry a stage line', () => {
  for (const id of ['', 'battery', 'roadmap', 'status', '404', 'researchers', 'research-notes/x', 'constructor', 'constructor/x', '__proto__/x', 'toString']) {
    assert.equal(stageLine(id, LEDGER), null, `route "${id}"`);
  }
  assert.equal(sectionOfRoute('research/gates'), 'research');
  assert.equal(sectionOfRoute('/substrate/overview'), 'substrate');
  assert.equal(sectionOfRoute(''), '');
});

test('every section of the manifest has a stage, and every stage names a line of the ledger', () => {
  const manifest = read('docs/publish.json');
  for (const section of manifest.sections) {
    for (const page of section.pages) {
      const key = sectionOfRoute(page.slug);
      assert.ok(Object.hasOwn(STAGE_OF_SECTION, key), `page "${page.slug}" is in section "${key}", which has no stage: decide its stage in STAGE_OF_SECTION`);
    }
  }
  const program = read('tools/ledger.json').program;
  const numbers = new Set<number>();
  for (const { stage, line } of Object.values(STAGE_OF_SECTION)) {
    assert.ok(program[line] && typeof program[line].state === 'string', `the ledger has no program.${line}`);
    assert.ok(!numbers.has(stage), `stage ${stage} is named twice`);
    numbers.add(stage);
  }
});

test('no section title of the manifest carries a program state in brackets', () => {
  // The sidebar's group labels are docs/publish.json's section titles, shown as typed. A state is typed
  // once, in the ledger (program, D-031), and read from there: the title strip and the footer state it
  // for the page being read. A bracketed "(active)" or "(paused)" beside a group would be a second copy
  // that goes stale the day a line is paused or resumed, so no title carries one. A bracketed word that
  // is not a program state says what a stage is, not where it stands, and is not checked here.
  const states = new Set<string>(read('tools/ledger.json').program_states.map((w: string) => w.toLowerCase()));
  assert.ok(states.size >= 2, 'the ledger lists its program states');
  /** The program states a title names inside (), [] or {}. */
  const bracketed = (title: string) =>
    [...title.matchAll(/[(\[{]([^)\]}]*)[)\]}]/g)].flatMap((g) => g[1].toLowerCase().split(/[^a-z]+/)).filter((w) => states.has(w));
  for (const section of read('docs/publish.json').sections) {
    assert.deepEqual(bracketed(section.title), [], `"${section.title}" names a state in brackets: the ledger holds program state, so drop it from the label in docs/publish.json`);
  }
  // the check bites: the labels the manifest used to carry would fail it
  assert.deepEqual(bracketed('Cognitive maps (active)'), ['active']);
  assert.deepEqual(bracketed('Cognitive maps [Paused]'), ['paused']);
  assert.deepEqual(bracketed('Substrate (foundation)'), []);
  assert.deepEqual(bracketed('Cognitive maps'), []);
});

test('the strip of a stage page opens with the stage and its section, and ends with the ledger\'s state', () => {
  const gates = titleStrip('research/gates', sidebar('Gates'), LEDGER);
  assert.deepEqual(gates, {
    start: { tag: 'Stage 2', name: 'Cognitive maps', decorative: false },
    end: { state: 'active', since: null, text: 'active' },
  });
  const sub = titleStrip('substrate/overview', sidebar('Substrate'), LEDGER);
  assert.deepEqual(sub, {
    start: { tag: 'Stage 1', name: 'Substrate', decorative: false },
    end: { state: 'paused', since: { iso: '2026-10-23', label: '23 October 2026' }, text: 'paused since 23 October 2026' },
  });
  // the sidebar's own group number never sits beside a stage number
  for (const strip of [gates, sub]) assert.doesNotMatch(strip?.start.tag ?? '', /^\d/);
});

test('a page outside a stage opens with the sidebar\'s number for its group, and has no end', () => {
  assert.deepEqual(titleStrip('battery', sidebar('Battery'), LEDGER), {
    start: { tag: '01', name: 'Start here', decorative: true },
    end: null,
  });
  assert.equal(titleStrip('nowhere', sidebar('Nowhere'), LEDGER), null);
});

test('the 404 page says what it is', () => {
  assert.deepEqual(titleStrip('404', [], LEDGER), {
    start: { tag: 'Error', name: '404', decorative: false },
    end: { state: null, since: null, text: 'Not filed' },
  });
});

// A plan with three gates, the first decided.
const PLAN = {
  as_of: '2026-10-27',
  timezone: 'UTC',
  line: { title: 'A fixture line', short_name: 'FX' },
  phases: [],
  gates: [
    { id: 'A', title: 'First', baseline_date: '2026-11-15', date: '2026-11-15', status: 'upcoming', question: 'q', if_missed: 'm' },
    { id: 'B', title: 'Second', baseline_date: '2026-12-31', date: '2026-12-31', status: 'upcoming', question: 'q', if_missed: 'm' },
    { id: 'D', title: 'Last', baseline_date: null, date: null, date_rule: 'a rule', status: 'upcoming', question: 'q', if_missed: 'm' },
  ],
  deadlines: [],
  layers: [],
} as unknown as Plan;

test('the next gate is read from the plan: its date, or pending once the date has passed', () => {
  assert.equal(nextGateText(PLAN), 'Gate A, 15 November 2026');
  assert.equal(nextGateText({ ...PLAN, as_of: '2026-11-20' }), 'Gate A, decision pending');
  const decidedA: Plan = {
    ...PLAN,
    gates: PLAN.gates.map((g) => (g.id === 'A' ? { ...g, status: 'decided', decided_on: '2026-11-14', next_step: 'continues' as const } : g)),
  };
  assert.equal(nextGateText(decidedA), 'Gate B, 31 December 2026');
  // the line has stopped: there is no next gate
  const stopped: Plan = { ...decidedA, gates: decidedA.gates.map((g) => (g.id === 'A' ? { ...g, next_step: 'stops' as const } : g)) };
  assert.equal(nextGateText(stopped), null);
  // only undated gates left
  assert.equal(nextGateText({ ...PLAN, gates: [PLAN.gates[2]] }), null);
});

test('the title block holds the sheet, the stage and, on a stage 2 page, the next gate', () => {
  const block = (id: string, title: string, current: string) => titleBlock({ id, title, sidebar: sidebar(current), ledger: LEDGER, plan: PLAN });
  // a day is kept on one line (no-break spaces), and the gate cell carries what the browser's clock reads
  assert.deepEqual(block('research/gates', 'Decision gates', 'Gates'), [
    { label: 'Sheet', text: 'Decision gates', note: '4 / 5' },
    { label: 'Stage', text: '2 · active' },
    { label: 'Next gate', text: 'Gate A, 15\u00a0November\u00a02026', clock: { gate: 'A', date: '2026-11-15', tz: PLAN.timezone } },
  ]);
  // the substrate is another line: its state and since when, and no gate
  assert.deepEqual(block('substrate/overview', 'The substrate', 'Substrate'), [
    { label: 'Sheet', text: 'The substrate', note: '5 / 5' },
    { label: 'Stage', text: '1 · paused since 23\u00a0October\u00a02026' },
  ]);
  // a page outside the stages is a sheet and nothing more
  assert.deepEqual(block('battery', 'Step through the paradigms', 'Battery'), [{ label: 'Sheet', text: 'Step through the paradigms', note: '2 / 5' }]);
});

test('a day in words is kept on one line, and nothing else is touched', () => {
  assert.equal(keepDays('Gate A, 15 November 2026'), 'Gate A, 15\u00a0November\u00a02026');
  assert.equal(keepDays('1 · paused since 3 March 2027'), '1 · paused since 3\u00a0March\u00a02027');
  assert.equal(keepDays('Gate B, decision pending'), 'Gate B, decision pending');
  assert.equal(keepDays('2 · active'), '2 · active');
});

test('the landing page and the 404 page are not sheets; a page not in the sidebar has no sheet', () => {
  const none = (id: string, title: string, current: string) => titleBlock({ id, title, sidebar: sidebar(current), ledger: LEDGER, plan: PLAN });
  assert.deepEqual(none('', 'Psyche', 'Home'), []);
  assert.deepEqual(none('404', 'Page not found', 'Nowhere'), []);
  assert.deepEqual(none('battery', 'Elsewhere', 'Nowhere'), []);
  // a page with no title is not a sheet either
  assert.deepEqual(none('battery', '', 'Battery'), []);
});

test('the footer date is the day of the commit, in UTC, or nothing', () => {
  assert.deepEqual(footerDate('2026-03-05T08:30:00.000Z'), { iso: '2026-03-05', label: '5 March 2026' });
  assert.deepEqual(footerDate('2026-10-23T23:30:00.000Z'), { iso: '2026-10-23', label: '23 October 2026' });
  assert.deepEqual(footerDate('2026-10-24T00:30:00+02:00'), { iso: '2026-10-23', label: '23 October 2026' });
  assert.equal(footerDate(undefined), null);
  assert.equal(footerDate(''), null);
  assert.equal(footerDate('not a date'), null);
});

test('the footer links say what they do, and lead to the repository, its licence, discussions, citation file and security policy', () => {
  const links = footerLinks();
  assert.deepEqual(
    links.map((l) => l.text),
    ['MIT licence', 'Source code', 'Discussions', 'Cite this repository', 'Report a vulnerability'],
  );
  const byText = Object.fromEntries(links.map((l) => [l.text, l]));
  assert.equal(byText['MIT licence'].href, `${REPO_URL}/blob/main/LICENSE`);
  assert.equal(byText['Source code'].href, REPO_URL);
  assert.equal(byText.Discussions.href, 'https://github.com/cagancaliskan/psyche/discussions');
  assert.equal(byText['Cite this repository'].href, `${REPO_URL}/blob/main/CITATION.cff`);
  assert.equal(byText['Report a vulnerability'].href, `${REPO_URL}/blob/main/SECURITY.md`);
  assert.equal(new Set(links.map((l) => l.href)).size, links.length, 'no link twice');
  // the text is words, not the name of the file it opens
  for (const l of links) assert.doesNotMatch(l.text, /\.(md|cff)\b|^LICENSE$/);
  // every file the footer names is in the repository, so a link does not lead to a missing page
  for (const file of ['LICENSE', 'CITATION.cff', 'SECURITY.md']) {
    assert.ok(readFileSync(new URL(file, REPO), 'utf8').length > 0, `${file} is missing`);
  }
  assert.match(readFileSync(new URL('LICENSE', REPO), 'utf8'), /^MIT License/);
});
