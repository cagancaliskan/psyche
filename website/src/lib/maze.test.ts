import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  HERO_GOAL,
  HERO_PICTURE,
  HERO_SEED,
  HERO_START,
  HERO_STEPS,
  isOpen,
  parseGrid,
  pathLength,
  polylinePoints,
  randomWalk,
  shortestPath,
  withCell,
  type Cell,
  type Grid,
} from './maze.ts';

/** Independent BFS distance (no parent map) to cross-check shortestPath lengths. */
function bfsDistance(grid: Grid, start: Cell, goal: Cell): number | null {
  if (!isOpen(grid, start) || !isOpen(grid, goal)) return null;
  const seen = new Set([`${start[0]},${start[1]}`]);
  let frontier: Cell[] = [start];
  for (let d = 0; frontier.length; d++) {
    for (const [r, c] of frontier) if (r === goal[0] && c === goal[1]) return d;
    const next: Cell[] = [];
    for (const [r, c] of frontier) {
      for (const [dr, dc] of [[0, 1], [1, 0], [0, -1], [-1, 0]] as const) {
        const n: Cell = [r + dr, c + dc];
        const k = `${n[0]},${n[1]}`;
        if (isOpen(grid, n) && !seen.has(k)) {
          seen.add(k);
          next.push(n);
        }
      }
    }
    frontier = next;
  }
  return null;
}

test('parseGrid rejects ragged rows and unknown characters', () => {
  assert.throws(() => parseGrid(['##', '#']));
  assert.throws(() => parseGrid(['#x']));
  assert.throws(() => parseGrid([]));
});

test('the hero grid is enclosed and its start and goal are open', () => {
  const g = parseGrid(HERO_PICTURE);
  assert.ok(isOpen(g, HERO_START));
  assert.ok(isOpen(g, HERO_GOAL));
  for (let c = 0; c < g.cols; c++) assert.ok(g.blocked[0][c] && g.blocked[g.rows - 1][c]);
});

test('shortestPath matches an independent BFS distance on seeded random grids', () => {
  let seed = 7;
  for (let trial = 0; trial < 200; trial++) {
    seed = (seed * 1103515245 + 12345) >>> 0;
    const rows = 5 + (seed % 7);
    const cols = 5 + ((seed >>> 8) % 7);
    const picture = Array.from({ length: rows }, (_, r) =>
      Array.from({ length: cols }, (_, c) => (((seed >>> ((r * cols + c) % 24)) ^ (r * 31 + c * 17)) % 4 === 0 ? '#' : '.')).join(''),
    );
    const g = parseGrid(picture);
    const start: Cell = [0, 0];
    const goal: Cell = [rows - 1, cols - 1];
    const path = shortestPath(g, start, goal);
    const d = bfsDistance(g, start, goal);
    if (d === null) assert.equal(path, null);
    else {
      assert.ok(path);
      assert.equal(path.length - 1, d);
      for (let i = 1; i < path.length; i++) assert.equal(Math.abs(path[i][0] - path[i - 1][0]) + Math.abs(path[i][1] - path[i - 1][1]), 1);
    }
  }
});

test('closing a door forces a longer path or no path', () => {
  const g = parseGrid(HERO_PICTURE);
  const open = shortestPath(g, HERO_START, HERO_GOAL);
  assert.ok(open);
  const closed = withCell(g, [7, 9], true);
  const detour = shortestPath(closed, HERO_START, HERO_GOAL);
  assert.ok(detour);
  assert.ok(detour.length >= open.length);
});

test('randomWalk is deterministic for a seed and only visits open cells', () => {
  const g = parseGrid(HERO_PICTURE);
  const a = randomWalk(g, HERO_START, HERO_STEPS, HERO_SEED);
  const b = randomWalk(g, HERO_START, HERO_STEPS, HERO_SEED);
  assert.deepEqual(a, b);
  assert.equal(a.length, HERO_STEPS + 1);
  for (const cell of a) assert.ok(isOpen(g, cell));
  assert.notDeepEqual(a, randomWalk(g, HERO_START, HERO_STEPS, HERO_SEED + 1));
});

test('the hero walk explores all four rooms and passes the goal before any goal exists', () => {
  const g = parseGrid(HERO_PICTURE);
  const walk = randomWalk(g, HERO_START, HERO_STEPS, HERO_SEED);
  const room = ([r, c]: Cell) => (r <= 6 ? 0 : 2) + (c <= 5 ? 0 : 1);
  const rooms = new Set(walk.filter(([r, c]) => r !== 7 && c !== 6).map(room));
  assert.equal(rooms.size, 4);
  assert.ok(walk.some(([r, c]) => r === HERO_GOAL[0] && c === HERO_GOAL[1]));
});

test('polyline and length helpers', () => {
  const p: Cell[] = [[0, 0], [0, 1], [1, 1]];
  assert.equal(polylinePoints(p), '0.5,0.5 1.5,0.5 1.5,1.5');
  assert.equal(pathLength(p), 2);
});
