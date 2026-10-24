import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  OPEN_PHASE_DAYS,
  axisRange,
  currentPhase,
  dayNumber,
  formatDay,
  fraction,
  isoFromDay,
  monthTicks,
  nextGate,
  spans,
  todayIn,
  type Plan,
} from './plan.ts';

// The real plan from the repository, read directly (not the staged copy).
const plan: Plan = JSON.parse(readFileSync(new URL('../../../tools/thesis_plan.json', import.meta.url), 'utf8'));

test('dayNumber round-trips and rejects invalid dates', () => {
  for (const iso of ['2026-10-23', '2027-02-28', '2028-02-29', '1999-12-31']) assert.equal(isoFromDay(dayNumber(iso)), iso);
  assert.throws(() => dayNumber('2027-02-29'));
  assert.throws(() => dayNumber('2026-1-1'));
  assert.throws(() => dayNumber('tomorrow'));
});

test('spans follow the plan in order and give open phases a fixed length', () => {
  const s = spans(plan);
  assert.equal(s.length, plan.phases.length);
  for (let i = 1; i < s.length; i++) assert.ok(s[i].from >= s[i - 1].from);
  for (const x of s) {
    assert.ok(x.to >= x.from);
    if (x.openEnd) assert.equal(x.to - x.from, OPEN_PHASE_DAYS);
  }
});

test('spans do not depend on the clock', () => {
  assert.deepEqual(spans(plan), spans(JSON.parse(JSON.stringify(plan))));
});

test('fraction is clamped to the axis', () => {
  const r = axisRange(plan);
  assert.equal(fraction(r.from - 100, r), 0);
  assert.equal(fraction(r.to + 100, r), 1);
  assert.equal(fraction(r.from, r), 0);
  assert.equal(fraction(r.to, r), 1);
});

test('monthTicks are first-of-month days inside the range, year shown in January', () => {
  const r = axisRange(plan);
  const ticks = monthTicks(r);
  assert.ok(ticks.length >= 6);
  for (const t of ticks) {
    assert.ok(t.day >= r.from && t.day <= r.to);
    assert.equal(isoFromDay(t.day).slice(8), '01');
  }
  assert.ok(ticks.some((t) => /Jan 2027/.test(t.label)));
});

test('currentPhase is the single active phase', () => {
  assert.equal(plan.phases.filter((p) => p.status === 'active').length, 1);
  assert.equal(currentPhase(plan)?.status, 'active');
});

test('nextGate counts whole days and skips past gates', () => {
  const first = plan.gates.find((g) => g.date !== null)!;
  const g = nextGate(plan, first.date!);
  assert.equal(g?.id, first.id);
  assert.equal(g?.daysLeft, 0);
  const dayBefore = isoFromDay(dayNumber(first.date!) - 1);
  assert.equal(nextGate(plan, dayBefore)?.daysLeft, 1);
  const dayAfter = isoFromDay(dayNumber(first.date!) + 1);
  assert.notEqual(nextGate(plan, dayAfter)?.id, first.id);
  assert.equal(nextGate(plan, '2099-01-01'), null);
});

test('todayIn uses the plan time zone, not UTC', () => {
  // 22:30 UTC on 2026-11-10 is already 2026-11-11 in Istanbul (UTC+3).
  assert.equal(todayIn('Europe/Istanbul', new Date(Date.UTC(2026, 10, 10, 22, 30))), '2026-11-11');
  assert.equal(todayIn('UTC', new Date(Date.UTC(2026, 10, 10, 22, 30))), '2026-11-10');
});

test('formatDay is stable', () => {
  assert.equal(formatDay('2026-11-15'), '15 November 2026');
});
