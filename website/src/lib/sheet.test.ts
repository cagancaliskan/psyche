import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cellRuler, gridLines, pad2, pointRuler, wallOutline } from './sheet.ts';
import { parseGrid } from './maze.ts';

/** Total length and number of drawn runs of a path made of `M x y h n` and `M x y v n` pieces. */
const measure = (d: string) => {
  const runs = [...d.matchAll(/M(\d+) (\d+)([hv])(\d+)/g)];
  return { runs: runs.length, length: runs.reduce((sum, m) => sum + Number(m[4]), 0), whole: runs.map((m) => m[0]).join('') === d };
};

test('a single wall cell is outlined by its four sides', () => {
  const grid = parseGrid(['...', '.#.', '...']);
  const { runs, length, whole } = measure(wallOutline(grid));
  assert.ok(whole);
  assert.equal(runs, 4);
  assert.equal(length, 4);
});

test('neighbouring wall cells share their inner side and merge into runs', () => {
  const grid = parseGrid(['....', '.##.', '....']);
  const { runs, length, whole } = measure(wallOutline(grid));
  assert.ok(whole);
  assert.equal(length, 6);
  assert.equal(runs, 4);
});

test('the edge of the grid is a boundary, and an open cell inside a ring is outlined too', () => {
  const ring = parseGrid(['###', '#.#', '###']);
  const { length } = measure(wallOutline(ring));
  assert.equal(length, 3 * 4 + 4);
  assert.equal(wallOutline(parseGrid(['...', '...'])), '');
});

test('the grid lines are the inner cell edges only', () => {
  assert.equal(gridLines(3, 2), 'M1 0v2M2 0v2M0 1h3');
});

test('a cell ruler numbers every third tick and marks every cell edge', () => {
  const nine = cellRuler(9);
  assert.deepEqual(nine.major.map((t) => t.label), ['00', '03', '06', '09']);
  assert.equal(nine.minor.length, 6);
  const seven = cellRuler(7);
  assert.deepEqual(seven.major.map((t) => t.label), ['00', '03', '06']);
  assert.deepEqual(seven.minor, [1, 2, 4, 5, 7]);
});

test('a point ruler ticks each point, without numerals, and ticks between them and at both ends', () => {
  const r = pointRuler(8.4, [1, 2.6, 4.2]);
  assert.deepEqual(r.major, [{ at: 1 }, { at: 2.6 }, { at: 4.2 }]);
  assert.deepEqual(r.minor, [0, 1.8, 3.4, 8.4]);
  assert.equal(pad2(4), '04');
});
