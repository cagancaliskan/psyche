import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  FIELD_GOAL,
  FIELD_SEED,
  FIELD_SPEC,
  FIELD_START,
  FIELD_STEPS,
  arenaColumn,
  cellPath,
  closeLeftOf,
  isOpen,
  parseGrid,
  pathLength,
  persistentWalk,
  polylinePoints,
  randomWalk,
  roomField,
  shortestPath,
  wallCells,
  wallPath,
  withCell,
  type Cell,
  type Grid,
} from './maze.ts';

/** Independent BFS distance (no parent map) to cross-check shortestPath lengths. */
function bfsDistance(grid: Grid, start: Cell, goal: Cell): number | null {
  if (!isOpen(grid, start) || !isOpen(grid, goal)) return null;
  const seen = new Set([`${start[0]},${start[1]}`]);
  let layer: Cell[] = [start];
  for (let d = 0; layer.length; d++) {
    for (const [r, c] of layer) if (r === goal[0] && c === goal[1]) return d;
    const next: Cell[] = [];
    for (const [r, c] of layer) {
      for (const [dr, dc] of [[0, 1], [1, 0], [0, -1], [-1, 0]] as const) {
        const n: Cell = [r + dr, c + dc];
        const k = `${n[0]},${n[1]}`;
        if (isOpen(grid, n) && !seen.has(k)) {
          seen.add(k);
          next.push(n);
        }
      }
    }
    layer = next;
  }
  return null;
}

/** Every open cell reachable from `from` (independent of the module's own helpers). */
function reachable(grid: Grid, from: Cell): Set<string> {
  const seen = new Set([`${from[0]},${from[1]}`]);
  const stack: Cell[] = [from];
  while (stack.length) {
    const [r, c] = stack.pop()!;
    for (const [dr, dc] of [[0, 1], [1, 0], [0, -1], [-1, 0]] as const) {
      const n: Cell = [r + dr, c + dc];
      const k = `${n[0]},${n[1]}`;
      if (isOpen(grid, n) && !seen.has(k)) {
        seen.add(k);
        stack.push(n);
      }
    }
  }
  return seen;
}

const openCells = (grid: Grid) => {
  const out: string[] = [];
  for (let r = 0; r < grid.rows; r++) for (let c = 0; c < grid.cols; c++) if (!grid.blocked[r][c]) out.push(`${r},${c}`);
  return out;
};

const PITCH = FIELD_SPEC.size + 1;
const ARENA = arenaColumn(FIELD_SPEC);
/** The room a cell lies in, or null for a wall line (a door cell sits on one). */
const roomOf = ([r, c]: Cell) => (r % PITCH !== 0 && c % PITCH !== 0 ? `${Math.floor(r / PITCH)},${Math.floor(c / PITCH)}` : null);
const isUnitStep = (a: Cell, b: Cell) => Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) === 1;

const field = roomField(FIELD_SPEC, FIELD_SEED);
const arena = closeLeftOf(field, ARENA);
const trail = persistentWalk(arena, FIELD_START, FIELD_STEPS, FIELD_SEED);
const route = shortestPath(arena, FIELD_START, FIELD_GOAL);

test('parseGrid rejects ragged rows and unknown characters', () => {
  assert.throws(() => parseGrid(['##', '#']));
  assert.throws(() => parseGrid(['#x']));
  assert.throws(() => parseGrid([]));
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

test('the field is 65 by 25, deterministic for its seed, and differs for another seed', () => {
  assert.equal(field.rows, 25);
  assert.equal(field.cols, 65);
  assert.deepEqual(roomField(FIELD_SPEC, FIELD_SEED), field);
  assert.notDeepEqual(roomField(FIELD_SPEC, FIELD_SEED + 1).blocked, field.blocked);
  assert.equal(ARENA, 33);
});

test('the field is enclosed, connected, and has at least one loop of rooms', () => {
  for (let c = 0; c < field.cols; c++) assert.ok(field.blocked[0][c] && field.blocked[field.rows - 1][c]);
  for (let r = 0; r < field.rows; r++) assert.ok(field.blocked[r][0] && field.blocked[r][field.cols - 1]);
  const open = openCells(field);
  assert.equal(reachable(field, [1, 1]).size, open.length);
  // Doors between neighbouring rooms: a connected graph of R rooms with D doors has D - R + 1 loops.
  const rooms = FIELD_SPEC.roomRows * FIELD_SPEC.roomCols;
  let doors = 0;
  for (let i = 0; i < FIELD_SPEC.roomRows; i++) {
    for (let j = 0; j < FIELD_SPEC.roomCols; j++) {
      const east = Array.from({ length: FIELD_SPEC.size }, (_, k) => !field.blocked[i * PITCH + 1 + k][(j + 1) * PITCH]);
      const south = Array.from({ length: FIELD_SPEC.size }, (_, k) => !field.blocked[(i + 1) * PITCH][j * PITCH + 1 + k]);
      if (j + 1 < FIELD_SPEC.roomCols && east.some(Boolean)) doors++;
      if (i + 1 < FIELD_SPEC.roomRows && south.some(Boolean)) doors++;
    }
  }
  assert.ok(doors - rooms + 1 >= 1, `doors ${doors}, rooms ${rooms}`);
});

test('the arena is fully reachable from the start without leaving it', () => {
  assert.ok(isOpen(arena, FIELD_START));
  assert.ok(isOpen(arena, FIELD_GOAL));
  const inArena = openCells(field).filter((k) => Number(k.split(',')[1]) >= ARENA);
  const seen = reachable(arena, FIELD_START);
  assert.equal(seen.size, inArena.length);
  for (const k of inArena) assert.ok(seen.has(k), k);
});

test('the trail starts at the start, moves in unit steps, stays in the arena and explores every arena room', () => {
  assert.deepEqual(persistentWalk(arena, FIELD_START, FIELD_STEPS, FIELD_SEED), trail);
  assert.equal(trail.length, FIELD_STEPS + 1);
  assert.deepEqual(trail[0], FIELD_START);
  for (let i = 1; i < trail.length; i++) assert.ok(isUnitStep(trail[i - 1], trail[i]), `step ${i}`);
  for (const cell of trail) assert.ok(isOpen(arena, cell));
  const rooms = new Set(trail.map(roomOf).filter((k) => k !== null));
  const arenaRooms = FIELD_SPEC.roomRows * (FIELD_SPEC.roomCols - FIELD_SPEC.arenaFrom);
  assert.equal(rooms.size, arenaRooms);
});

test('the trail passes the goal before its last step: the space is explored before any goal exists', () => {
  const at = trail.findIndex(([r, c]) => r === FIELD_GOAL[0] && c === FIELD_GOAL[1]);
  assert.ok(at >= 0 && at < trail.length - 1, `reaches the goal at step ${at}`);
});

test('the route is a shortest path, shorter than the trail, and crosses at least three rooms', () => {
  assert.ok(route);
  assert.deepEqual(route[0], FIELD_START);
  assert.deepEqual(route[route.length - 1], FIELD_GOAL);
  for (let i = 1; i < route.length; i++) assert.ok(isUnitStep(route[i - 1], route[i]));
  assert.equal(route.length - 1, bfsDistance(arena, FIELD_START, FIELD_GOAL));
  assert.ok(pathLength(route) < pathLength(trail));
  assert.ok(new Set(route.map(roomOf).filter((k) => k !== null)).size >= 3);
});

test('no trail or route cell lies left of the arena, so neither passes under the text', () => {
  assert.ok(route);
  for (const [, c] of [...trail, ...route]) assert.ok(c >= ARENA, `column ${c}`);
});

test('closing a door on the route forces a longer route or none', () => {
  assert.ok(route);
  const doorCell = route.find((cell) => roomOf(cell) === null);
  assert.ok(doorCell, 'the route passes a door');
  const detour = shortestPath(withCell(arena, doorCell, true), FIELD_START, FIELD_GOAL);
  if (detour) assert.ok(detour.length > route.length);
});

/** Expand `M x y h w v h h -w z` rectangles back into cells; fails on overlap. */
function cellsOf(d: string): Set<string> {
  const cells = new Set<string>();
  const rect = /M(\d+) (\d+)h(\d+)v(\d+)h-(\d+)z/g;
  let consumed = 0;
  for (const m of d.matchAll(rect)) {
    const [x, y, w, h, back] = m.slice(1).map(Number);
    assert.equal(back, w);
    for (let r = y; r < y + h; r++) {
      for (let c = x; c < x + w; c++) {
        const k = `${r},${c}`;
        assert.ok(!cells.has(k), `overlap at ${k}`);
        cells.add(k);
      }
    }
    consumed += m[0].length;
  }
  assert.equal(consumed, d.length, 'only rectangles in the path');
  return cells;
}

test('wallPath covers exactly the wall cells, split cleanly between wing and arena', () => {
  const walls = new Set(wallCells(field).map(([r, c]) => `${r},${c}`));
  assert.deepEqual(cellsOf(wallPath(field)), walls);
  const wing = cellsOf(wallPath(field, 0, ARENA));
  const arenaWalls = cellsOf(wallPath(field, ARENA));
  for (const k of wing) assert.ok(Number(k.split(',')[1]) < ARENA);
  for (const k of arenaWalls) assert.ok(Number(k.split(',')[1]) >= ARENA);
  assert.deepEqual(new Set([...wing, ...arenaWalls]), walls);
  const small = parseGrid(['###', '#.#', '###']);
  assert.equal(wallPath(small), 'M0 0h3v1h-3zM0 1h1v1h-1zM2 1h1v1h-1zM0 2h3v1h-3z');
});

test('randomWalk is deterministic for a seed and only visits open cells', () => {
  const a = randomWalk(arena, FIELD_START, 200, FIELD_SEED);
  assert.deepEqual(a, randomWalk(arena, FIELD_START, 200, FIELD_SEED));
  assert.equal(a.length, 201);
  for (const cell of a) assert.ok(isOpen(arena, cell));
  assert.notDeepEqual(a, randomWalk(arena, FIELD_START, 200, FIELD_SEED + 1));
});

test('polyline, path and length helpers', () => {
  const p: Cell[] = [[0, 0], [0, 1], [1, 1]];
  assert.equal(polylinePoints(p), '0.5,0.5 1.5,0.5 1.5,1.5');
  assert.equal(pathLength(p), 2);
  assert.equal(cellPath([[0, 0], [0, 1], [0, 2], [1, 2], [1, 1]]), 'M0.5 0.5h2v1h-1');
  assert.equal(cellPath([]), '');
});
