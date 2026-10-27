import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  NEXT_STEP_TEXT,
  OPEN_PHASE_DAYS,
  axisRange,
  currentPhase,
  dayNumber,
  formatDay,
  fraction,
  gateLabel,
  gateNote,
  gatePhrase,
  gateState,
  isoFromDay,
  lineStoppedAt,
  monthTicks,
  nextGate,
  phaseWhen,
  spans,
  todayIn,
  type NextStep,
  type Plan,
} from './plan.ts';

// The real plan from the repository, read directly (not the staged copy).
const plan: Plan = JSON.parse(readFileSync(new URL('../../../tools/research_plan.json', import.meta.url), 'utf8'));

test('the plan names its research line with exactly a title and a short name', () => {
  assert.deepEqual(Object.keys(plan.line).sort(), ['short_name', 'title']);
  assert.ok(plan.line.title.trim().length > 0);
  assert.ok(plan.line.short_name.trim().length > 0);
});

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

// A small plan of its own for the gate scenarios, so they do not move when the real plan does.
// Gate A ends P0, gate B ends P1, gate C has no date yet.
function fixture(): Plan {
  const phase = (id: string, start: string | null, end: string | null, gate: string | null, status: string) => ({
    id, title: `Phase ${id}`, start, end, gate, status, outputs: ['an output'],
  });
  const gate = (id: string, date: string | null) => ({
    id, title: `Gate ${id} title`, baseline_date: date, date, status: 'upcoming', question: 'q', if_missed: 'm',
  });
  return {
    as_of: '2026-10-23',
    timezone: 'Europe/Istanbul',
    line: { title: 'A fixture line', short_name: 'FX' },
    phases: [
      phase('P0', '2026-10-23', '2026-11-15', 'A', 'active'),
      phase('P1', '2026-11-16', '2026-12-31', 'B', 'planned'),
      phase('P2', '2027-01-01', null, 'C', 'planned'),
    ],
    gates: [gate('A', '2026-11-15'), gate('B', '2026-12-31'), gate('C', null)],
    deadlines: [],
    layers: [],
  };
}

/** The fixture with gate `id` decided, and its phase marked done when the line goes on or stops. */
function decide(id: string, step: NextStep | undefined, on = '2026-11-14', p: Plan = fixture()): Plan {
  const g = p.gates.find((x) => x.id === id)!;
  g.status = 'decided';
  g.decided_on = on;
  if (step) g.next_step = step;
  if (step !== 'extends') for (const ph of p.phases) if (ph.gate === id) ph.status = 'done';
  return p;
}

test('currentPhase is the single active phase', () => {
  assert.equal(plan.phases.filter((p) => p.status === 'active').length, 1);
  assert.equal(currentPhase(plan)?.status, 'active');
});

test('currentPhase is the plan label alone: it does not move with the date, past a phase end or a gate date', () => {
  // The phase ended on 15 November but its gate is not decided: the line is still there.
  const p = fixture();
  assert.equal(currentPhase(p)?.id, 'P0');
  // Gate A decided (continues) and P0 marked done in the same edit, P1 not yet marked active:
  // no phase is current, whatever today is. The bands, chips and the generated line say the same.
  const labelled = decide('A', 'continues');
  assert.equal(currentPhase(labelled), null);
  // The next phase becomes current when the plan marks it active, and only then.
  labelled.phases[1].status = 'active';
  assert.equal(currentPhase(labelled)?.id, 'P1');
});

test('currentPhase: a gate that extends the phase leaves it current; a gate that stops the line ends it', () => {
  const extended = decide('A', 'extends');
  assert.equal(currentPhase(extended)?.id, 'P0');
  const stopped = decide('A', 'stops');
  assert.equal(currentPhase(stopped), null);
  // Even a label left on active does not outlive a stop.
  stopped.phases[0].status = 'active';
  assert.equal(currentPhase(stopped), null);
});

test('currentPhase is null before the plan has an active phase', () => {
  const p = fixture();
  p.phases[0].status = 'planned';
  assert.equal(currentPhase(p), null);
});

test('gateState: upcoming, pending past its date, decided, and undated', () => {
  const g = fixture().gates[0];
  assert.deepEqual(gateState(g, '2026-11-01'), { kind: 'upcoming', daysLeft: 14 });
  assert.deepEqual(gateState(g, '2026-11-15'), { kind: 'upcoming', daysLeft: 0 });
  assert.deepEqual(gateState(g, '2026-11-16'), { kind: 'pending', daysOver: 1 });
  assert.deepEqual(gateState(g, '2027-01-01'), { kind: 'pending', daysOver: 47 });
  assert.deepEqual(gateState(fixture().gates[2], '2099-01-01'), { kind: 'unscheduled' });
  const decided = decide('A', 'continues').gates[0];
  // Once decided, the date no longer matters: it is decided before, on and after it.
  for (const today of ['2026-11-01', '2026-11-15', '2026-12-01']) {
    assert.deepEqual(gateState(decided, today), { kind: 'decided', decidedOn: '2026-11-14', nextStep: 'continues' });
  }
  assert.deepEqual(gateState({ ...decided, decided_on: undefined, next_step: undefined }, '2026-12-01'), {
    kind: 'decided',
    decidedOn: null,
    nextStep: null,
  });
});

test('gateLabel and gateNote say "decision pending" with the date, and "decided on" with the next step', () => {
  const g = fixture().gates[0];
  assert.deepEqual(gateLabel(gateState(g, '2026-11-01')), { tone: 'upcoming', text: 'Upcoming' });
  assert.deepEqual(gateLabel(gateState(g, '2026-11-20')), { tone: 'pending', text: 'Decision pending' });
  assert.deepEqual(gateLabel(gateState(g, '2026-11-20')), gateLabel(gateState(g, '2027-05-05')));
  assert.equal(gateNote(g, gateState(g, '2026-11-01')), null);
  assert.equal(gateNote(g, gateState(g, '2026-11-20')), 'Decision pending. The gate was due on 15 November 2026.');
  assert.equal(gatePhrase(gateState(g, '2026-11-20')), 'decision pending');
  const notes: Record<NextStep, string> = {
    continues: 'Decided on 14 November 2026. The line continues to the next phase.',
    extends: 'Decided on 14 November 2026. The line extends.',
    stops: 'Decided on 14 November 2026. The line stops.',
  };
  for (const step of ['continues', 'extends', 'stops'] as const) {
    const d = decide('A', step).gates[0];
    const state = gateState(d, '2026-11-20');
    assert.deepEqual(gateLabel(state), { tone: 'decided', text: 'Decided' });
    assert.equal(gateNote(d, state), notes[step]);
    assert.equal(gatePhrase(state), `decided on 14 November 2026, ${NEXT_STEP_TEXT[step]}`);
  }
  // A decided gate with no date or next step in the plan still says it is decided, and no more.
  const bare = { ...decide('A', undefined).gates[0], decided_on: undefined };
  assert.equal(gateNote(bare, gateState(bare, '2026-11-20')), 'Decided.');
  assert.equal(gatePhrase(gateState(bare, '2026-11-20')), 'decided');
});

test('what a decided gate shows carries no verdict: only the date and one of three next steps', () => {
  assert.deepEqual(Object.keys(NEXT_STEP_TEXT).sort(), ['continues', 'extends', 'stops']);
  for (const step of ['continues', 'extends', 'stops'] as const) {
    const d = decide('A', step).gates[0];
    const shown = [gateNote(d, gateState(d, '2026-11-20')), gatePhrase(gateState(d, '2026-11-20'))].join(' ');
    assert.doesNotMatch(shown, /pass|fail|verdict|evidence|because|reason|met|criteri/i);
  }
});

test('after a decision that stops the line, a later undecided gate is not reached, never pending', () => {
  const stopped = decide('A', 'stops');
  const stoppedAt = lineStoppedAt(stopped)?.id ?? null;
  assert.equal(stoppedAt, 'A');
  const b = stopped.gates[1];
  for (const today of ['2026-11-20', '2027-01-01', '2027-03-01', '2099-01-01']) {
    assert.deepEqual(gateState(b, today, stoppedAt), { kind: 'not-reached', stoppedAt: 'A' }, today);
    assert.deepEqual(gateLabel(gateState(b, today, stoppedAt)), { tone: 'upcoming', text: 'Not reached' });
    assert.equal(gateNote(b, gateState(b, today, stoppedAt)), 'The line stopped at Gate A.');
    assert.equal(gatePhrase(gateState(b, today, stoppedAt)), 'not reached');
  }
  // A gate with no fixed date is not reached either, and the decided gate itself stays decided.
  assert.equal(gateState(stopped.gates[2], '2099-01-01', stoppedAt).kind, 'not-reached');
  assert.equal(gateState(stopped.gates[0], '2027-03-01', stoppedAt).kind, 'decided');
  // Without a stop the same gate on the same day is pending, so the two cases stay apart.
  assert.equal(gateState(b, '2027-03-01', null).kind, 'pending');
  // A decision that extends the phase stops nothing.
  assert.equal(lineStoppedAt(decide('A', 'extends')), null);
  assert.equal(gateState(decide('A', 'extends').gates[1], '2027-03-01', null).kind, 'pending');
  // The words carry no verdict.
  assert.doesNotMatch(gateNote(b, gateState(b, '2027-03-01', stoppedAt)) ?? '', /pass|fail|verdict|evidence|because|reason|met|criteri/i);
});

test('nextGate counts whole days', () => {
  const p = fixture();
  const g = nextGate(p, '2026-11-15');
  assert.equal(g?.id, 'A');
  assert.equal(g?.daysLeft, 0);
  assert.equal(g?.pending, false);
  assert.equal(nextGate(p, '2026-11-14')?.daysLeft, 1);
  assert.equal(nextGate(p, '2026-10-23')?.daysLeft, 23);
});

test('nextGate does not skip a gate past its date with no decision: it is pending', () => {
  const p = fixture();
  const g = nextGate(p, '2026-11-16');
  assert.equal(g?.id, 'A');
  assert.equal(g?.pending, true);
  assert.equal(g?.daysLeft, -1);
  // Well past it, and past nothing else yet: still gate A, not B.
  assert.equal(nextGate(p, '2026-12-01')?.id, 'A');
  assert.equal(nextGate(p, '2026-12-01')?.pending, true);
  // Both dated gates past: the earlier undecided one is still the one the line waits on.
  assert.equal(nextGate(p, '2027-03-01')?.id, 'A');
  assert.equal(nextGate(p, '2099-01-01')?.id, 'A');
});

test('nextGate moves on once a gate is decided, and shows the next dated gate as upcoming or pending', () => {
  const p = decide('A', 'continues');
  assert.equal(nextGate(p, '2026-11-20')?.id, 'B');
  assert.equal(nextGate(p, '2026-11-20')?.pending, false);
  assert.equal(nextGate(p, '2026-12-31')?.daysLeft, 0);
  assert.equal(nextGate(p, '2027-01-02')?.id, 'B');
  assert.equal(nextGate(p, '2027-01-02')?.pending, true);
  // A gate decided out of order does not hide an earlier gate still waiting.
  const outOfOrder = decide('B', 'continues', '2026-11-10');
  assert.equal(nextGate(outOfOrder, '2026-11-20')?.id, 'A');
  assert.equal(nextGate(outOfOrder, '2026-11-20')?.pending, true);
});

test('nextGate is null when every dated gate is decided, and once the line has stopped', () => {
  const allDecided = decide('B', 'continues', '2026-12-30', decide('A', 'continues'));
  assert.equal(nextGate(allDecided, '2026-12-31'), null);
  const stopped = decide('A', 'stops');
  assert.equal(lineStoppedAt(stopped)?.id, 'A');
  // Gate B is still upcoming in the plan, but no gate follows a decision that the line stops.
  assert.equal(nextGate(stopped, '2026-11-20'), null);
  assert.equal(lineStoppedAt(fixture()), null);
  assert.equal(lineStoppedAt(decide('A', 'extends')), null);
});

test('the real plan: its gates and phases agree with each other and with its own date', () => {
  for (const g of plan.gates) {
    if (g.status === 'decided') {
      assert.ok(g.decided_on, `gate ${g.id} is decided and carries the day it was decided`);
      assert.ok(g.next_step && g.next_step in NEXT_STEP_TEXT, `gate ${g.id} carries one of the three next steps`);
      assert.ok(dayNumber(g.decided_on!) <= dayNumber(plan.as_of), `gate ${g.id} was decided on or before as_of`);
    } else {
      assert.equal(g.decided_on, undefined, `gate ${g.id} is not decided, so it has no decision date`);
      assert.equal(g.next_step, undefined, `gate ${g.id} is not decided, so it has no next step`);
    }
  }
  const active = plan.phases.find((p) => p.status === 'active');
  if (active) {
    assert.ok(active.start !== null && dayNumber(active.start) <= dayNumber(plan.as_of), 'the active phase has started by as_of');
    const gate = active.gate ? plan.gates.find((g) => g.id === active.gate) : undefined;
    assert.ok(!gate || gate.status !== 'decided' || gate.next_step === 'extends', 'the active phase is not one a decision closed');
    assert.equal(currentPhase(plan)?.id, active.id, 'currentPhase is the plan\'s active phase');
  }
  // A phase whose gate is decided with "continues" or "stops" is done (the validator enforces this too).
  for (const ph of plan.phases) {
    const gate = ph.gate ? plan.gates.find((g) => g.id === ph.gate) : undefined;
    if (gate?.status === 'decided' && (gate.next_step === 'continues' || gate.next_step === 'stops')) {
      assert.equal(ph.status, 'done', `phase ${ph.id}`);
    }
  }
});

test('todayIn uses the plan time zone, not UTC', () => {
  // 22:30 UTC on 2026-11-10 is already 2026-11-11 in Istanbul (UTC+3).
  assert.equal(todayIn('Europe/Istanbul', new Date(Date.UTC(2026, 10, 10, 22, 30))), '2026-11-11');
  assert.equal(todayIn('UTC', new Date(Date.UTC(2026, 10, 10, 22, 30))), '2026-11-10');
});

test('formatDay is stable', () => {
  assert.equal(formatDay('2026-11-15'), '15 November 2026');
});

test('phaseWhen gives dates, or the plan rule where a date is not fixed', () => {
  const base = { id: 'X', title: 'x', gate: null, status: 'planned', outputs: [] };
  assert.equal(phaseWhen({ ...base, start: '2027-03-01', end: '2027-04-15' }), '1 March 2027 to 15 April 2027');
  assert.equal(phaseWhen({ ...base, start: '2027-04-15', end: null, end_rule: 'the deadline' }), '15 April 2027 to the deadline');
  assert.equal(phaseWhen({ ...base, start: null, start_rule: 'after review', end: null, end_rule: 'set later' }), 'Starts after review; end set later');
  assert.equal(phaseWhen({ ...base, start: null, start_rule: 'after review', end: '2027-04-15' }), 'Starts after review, ends 15 April 2027');
  for (const p of plan.phases) assert.doesNotMatch(phaseWhen(p), /undefined|null/);
});
