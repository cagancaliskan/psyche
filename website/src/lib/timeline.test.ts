// lib/timeline.ts on fixtures: what the timeline page (/roadmap/) says of the plan's gates on a given day,
// its axis and its ids. The staged plan (src/data/plan.json) is never read here.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { axisMonths, cap, daysWords, gateFromData, gateReadings, gateSlug, gateWhen, nextGateId, pct, type GateInput } from './timeline.ts';
import { dayNumber } from './plan.ts';

const GATES: GateInput[] = [
  { id: 'A', date: '2026-11-15', status: 'upcoming' },
  { id: 'B', date: '2026-12-31', status: 'upcoming' },
  { id: 'D', date: null, status: 'upcoming' },
];

test('the axis names each month from the one after the start, with the year under January only', () => {
  const range = { from: dayNumber('2026-10-23'), to: dayNumber('2027-02-10') };
  const months = axisMonths(range);
  assert.deepEqual(months.map((m) => m.month), ['Nov', 'Dec', 'Jan', 'Feb']);
  assert.deepEqual(months.map((m) => m.year), [null, null, 2027, null]);
  assert.ok(months.every((m) => /^\d+\.\d{3}%$/.test(m.at)));
  assert.equal(pct(0.5), '50.000%');
});

test('a gate past its date with no decision reads "Decision pending", with the day it was due', () => {
  const before = gateReadings(GATES, '2026-11-14');
  assert.deepEqual(before.get('A'), { word: 'Upcoming', note: null });
  const after = gateReadings(GATES, '2026-11-17');
  assert.deepEqual(after.get('A'), { word: 'Decision pending', note: 'Decision pending. The gate was due on 15 November 2026.' });
  assert.deepEqual(after.get('D'), { word: 'Upcoming', note: null });
});

test('a decided gate reads "Decided" with its day and next step; after a stop the later gates are not reached', () => {
  const decided: GateInput[] = [{ ...GATES[0], status: 'decided', decided_on: '2026-11-14', next_step: 'stops' }, GATES[1]];
  const r = gateReadings(decided, '2026-12-01');
  assert.deepEqual(r.get('A'), { word: 'Decided', note: 'Decided on 14 November 2026. The line stops.' });
  assert.deepEqual(r.get('B'), { word: 'Not reached', note: 'The line stopped at Gate A.' });
  assert.equal(nextGateId(decided), null);
  assert.equal(daysWords(decided, '2026-12-01'), '');
});

test('the next gate does not depend on the day; its days left do', () => {
  assert.equal(nextGateId(GATES), 'A');
  assert.equal(daysWords(GATES, '2026-11-03'), ', 12 days left');
  assert.equal(daysWords(GATES, '2026-11-14'), ', 1 day left');
  assert.equal(daysWords(GATES, '2026-11-15'), ', today');
  assert.equal(daysWords(GATES, '2026-11-17'), ', decision pending');
});

test('ids, dates in words and the markup round trip', () => {
  assert.equal(gateSlug({ id: 'C', title: 'Spiking model' }), 'gate-c-spiking-model');
  assert.equal(gateWhen({ date: '2026-12-31' }), '31 December 2026');
  assert.equal(gateWhen({ date: null, date_rule: 'one week before the submission deadline' }), 'one week before the submission deadline');
  assert.equal(cap('planned'), 'Planned');
  assert.deepEqual(gateFromData({ gateId: 'A', date: '', state: 'decided', decidedOn: '2026-11-14', nextStep: 'continues' }), {
    id: 'A',
    date: null,
    status: 'decided',
    decided_on: '2026-11-14',
    next_step: 'continues',
  });
});
