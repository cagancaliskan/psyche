import { test } from 'node:test';
import assert from 'node:assert/strict';
import { TESTS, splitSummary, type GridStep } from './battery.ts';
import { isOpen } from './maze.ts';

const grid = (id: string) => {
  const t = TESTS.find((x) => x.id === id);
  assert.ok(t && t.kind === 'grid');
  return t.steps as GridStep[];
};
const onPath = (step: GridStep, [r, c]: readonly [number, number]) => (step.path ?? []).some(([pr, pc]) => pr === r && pc === c);

test('five tests, T1 to T5, each with at least two steps', () => {
  assert.deepEqual(TESTS.map((t) => t.id), ['T1', 'T2', 'T3', 'T4', 'T5']);
  for (const t of TESTS) assert.ok(t.steps.length >= 2);
});

test('every drawn path exists and stays on open cells', () => {
  for (const t of TESTS) {
    if (t.kind !== 'grid') continue;
    for (const s of t.steps) {
      if (s.path === undefined) continue;
      assert.ok(s.path, `${t.id} ${s.label}: path must exist`);
      for (const cell of s.path) assert.ok(isOpen(s.grid, cell));
      if (s.goal) assert.deepEqual(s.path.at(-1), s.goal);
      if (s.start) assert.deepEqual(s.path[0], s.start);
    }
  }
});

test('T2: the door lies on the usual route, and the detour is strictly longer', () => {
  const [usual, closed, detour] = grid('T2');
  const door = closed.doors![0];
  assert.ok(onPath(usual, door), 'the closed door must block the usual route');
  assert.ok(!onPath(detour, door));
  assert.ok(detour.path!.length > usual.path!.length);
});

test('T3: the opened passage gives a strictly shorter route that uses it', () => {
  const [known, , shortcut] = grid('T3');
  const gap = known.doors![0];
  assert.ok(!onPath(known, gap));
  assert.ok(onPath(shortcut, gap));
  assert.ok(shortcut.path!.length < known.path!.length);
});

test('T1: the first-trial route reaches a goal the exploration trail passed', () => {
  const [explore, , first] = grid('T1');
  const goal = first.goal!;
  assert.ok(explore.trail!.some(([r, c]) => r === goal[0] && c === goal[1]));
});

test('every summary splits into its set-up and the question the test asks', () => {
  for (const t of TESTS) {
    const { setup, ask } = splitSummary(t.summary);
    assert.ok(setup.length > 0, `${t.id}: a set-up comes first`);
    assert.match(ask, /^The test asks whether .+\.$/, `${t.id}: the question is the last sentence`);
    assert.equal(`${setup} ${ask}`, t.summary);
  }
  assert.deepEqual(splitSummary('No question here.'), { setup: '', ask: 'No question here.' });
});
