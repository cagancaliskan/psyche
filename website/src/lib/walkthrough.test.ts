// lib/walkthrough.ts: the walk-through page's pictures, drawn from the paradigms of lib/battery.ts.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { TESTS } from './battery.ts';
import { doorPath, stepLabel, stepShapes, viewBox } from './walkthrough.ts';

const byId = (id: string) => {
  const t = TESTS.find((x) => x.id === id);
  assert.ok(t);
  return t;
};
const classes = (id: string, i: number) => stepShapes(byId(id), i).map((s) => s.attrs.class);

test('every step of every test has a picture with its walls or nodes, and a label that names the step', () => {
  for (const t of TESTS) {
    t.steps.forEach((s, i) => {
      assert.ok(stepShapes(t, i).length > 0);
      assert.equal(stepLabel(t, i), `${t.name}, step ${i + 1} of ${t.steps.length}: ${s.caption}`);
    });
  }
  assert.equal(viewBox(byId('T1')), '0.5 0.5 8 6');
  assert.equal(viewBox(byId('T2')), '0.5 0.5 8 5');
  assert.equal(viewBox(byId('T5')), '0 0.2 8.4 2.7');
});

test('a shut door is a mark across its corridor: upright in a corridor that runs sideways, flat in one that runs up and down', () => {
  const t2 = byId('T2');
  assert.ok(t2.kind === 'grid');
  const door2 = stepShapes(t2, 1).find((s) => s.attrs.class === 'bw-door');
  assert.equal(door2?.attrs.d, 'M3.5 4.5L3.5 5M3.5 4.5L3.5 4');
  const t3 = byId('T3');
  assert.ok(t3.kind === 'grid');
  assert.equal(stepShapes(t3, 0).find((s) => s.attrs.class === 'bw-door')?.attrs.d, 'M3.5 4.5L4 4.5M3.5 4.5L3 4.5');
  assert.equal(doorPath(t3.steps[1].grid, [4, 3]), 'M3.5 4.5L4 4.5M3.5 4.5L3 4.5');
});

test('each step draws what its words say', () => {
  // T1: exploration is a trail with no goal; then the goal; then the direct route and no trail
  assert.deepEqual(classes('T1', 0), ['bw-wall', 'bw-trail', 'bw-start']);
  assert.deepEqual(classes('T1', 1), ['bw-wall', 'bw-trail', 'bw-goal', 'bw-goal-dot', 'bw-start']);
  assert.deepEqual(classes('T1', 2), ['bw-wall', 'bw-route', 'bw-goal', 'bw-goal-dot', 'bw-start']);
  // T2: the door closes, then the detour
  assert.deepEqual(classes('T2', 1), ['bw-wall', 'bw-door', 'bw-goal', 'bw-goal-dot', 'bw-start']);
  // T4: the same layout, other letters
  const letters = (i: number) => stepShapes(byId('T4'), i).filter((s) => s.el === 'text').map((s) => s.text);
  assert.deepEqual(letters(0), ['A', 'B', 'C', 'D']);
  assert.deepEqual(letters(1), ['W', 'X', 'Y', 'Z']);
  // T5: four trained pairs; the test pair is asked with an arc and two marked nodes
  const t5 = stepShapes(byId('T5'), 1);
  assert.equal(t5.filter((s) => s.attrs.class === 'bw-edge').length, 4);
  assert.equal(t5.find((s) => s.attrs.class === 'bw-route')?.attrs.d, 'M2.6 1.52Q4.2 0.4 5.8 1.52');
  assert.equal(t5.filter((s) => s.attrs.class === 'bw-node bw-node--asked').length, 2);
  assert.equal(stepShapes(byId('T5'), 0)[0].attrs.x1, 1.42);
});
