/**
 * Deterministic grid-world geometry for the site's illustrations.
 *
 * These are drawings of classic behavioural paradigms (Tolman-style latent learning, detours,
 * shortcuts), not results and not a model: the "agent" here is a seeded random walk followed by a
 * breadth-first shortest path on a fully known grid. Everything is integer arithmetic with a fixed
 * neighbour order, so the same inputs always draw the same picture.
 */

export type Cell = readonly [row: number, col: number];

export interface Grid {
  rows: number;
  cols: number;
  /** blocked[r][c] is true for a wall cell. */
  blocked: boolean[][];
}

/** Fixed neighbour order: north, east, south, west. Ties always resolve the same way. */
const STEPS: readonly Cell[] = [
  [-1, 0],
  [0, 1],
  [1, 0],
  [0, -1],
];

/** Parse a picture: '#' wall, '.' floor. Rows must have equal length. */
export function parseGrid(picture: readonly string[]): Grid {
  const rows = picture.length;
  const cols = picture[0]?.length ?? 0;
  if (rows === 0 || cols === 0) throw new Error('empty grid');
  const blocked = picture.map((line, r) => {
    if (line.length !== cols) throw new Error(`row ${r} has length ${line.length}, expected ${cols}`);
    return [...line].map((ch) => {
      if (ch !== '#' && ch !== '.') throw new Error(`unexpected character ${JSON.stringify(ch)}`);
      return ch === '#';
    });
  });
  return { rows, cols, blocked };
}

export function isOpen(grid: Grid, [r, c]: Cell): boolean {
  return r >= 0 && c >= 0 && r < grid.rows && c < grid.cols && !grid.blocked[r][c];
}

export function withCell(grid: Grid, cell: Cell, wall: boolean): Grid {
  const blocked = grid.blocked.map((row) => row.slice());
  blocked[cell[0]][cell[1]] = wall;
  return { ...grid, blocked };
}

export function openNeighbours(grid: Grid, [r, c]: Cell): Cell[] {
  const out: Cell[] = [];
  for (const [dr, dc] of STEPS) {
    const next: Cell = [r + dr, c + dc];
    if (isOpen(grid, next)) out.push(next);
  }
  return out;
}

/** mulberry32: a small, well-known 32-bit PRNG. Returns integers in [0, 2^32). */
export function prng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return (t ^ (t >>> 14)) >>> 0;
  };
}

/** A reward-free random walk of `steps` moves from `start` (uniform over open neighbours). */
export function randomWalk(grid: Grid, start: Cell, steps: number, seed: number): Cell[] {
  if (!isOpen(grid, start)) throw new Error('start is not an open cell');
  const next = prng(seed);
  const walk: Cell[] = [start];
  let here = start;
  for (let i = 0; i < steps; i++) {
    const options = openNeighbours(grid, here);
    if (options.length === 0) break;
    here = options[next() % options.length];
    walk.push(here);
  }
  return walk;
}

const key = ([r, c]: Cell) => `${r},${c}`;

/** Breadth-first shortest path; null when the goal is unreachable. */
export function shortestPath(grid: Grid, start: Cell, goal: Cell): Cell[] | null {
  if (!isOpen(grid, start) || !isOpen(grid, goal)) return null;
  const parent = new Map<string, Cell | null>([[key(start), null]]);
  const queue: Cell[] = [start];
  for (let head = 0; head < queue.length; head++) {
    const here = queue[head];
    if (here[0] === goal[0] && here[1] === goal[1]) {
      const path: Cell[] = [];
      let at: Cell | null = here;
      while (at) {
        path.push(at);
        at = parent.get(key(at)) ?? null;
      }
      return path.reverse();
    }
    for (const n of openNeighbours(grid, here)) {
      if (!parent.has(key(n))) {
        parent.set(key(n), here);
        queue.push(n);
      }
    }
  }
  return null;
}

/** SVG polyline points through cell centres, in grid units. */
export function polylinePoints(path: readonly Cell[]): string {
  return path.map(([r, c]) => `${c + 0.5},${r + 0.5}`).join(' ');
}

/** Path length in grid units (sum of unit moves), used for dash animation. */
export function pathLength(path: readonly Cell[]): number {
  let total = 0;
  for (let i = 1; i < path.length; i++) {
    total += Math.abs(path[i][0] - path[i - 1][0]) + Math.abs(path[i][1] - path[i - 1][1]);
  }
  return total;
}

export function wallCells(grid: Grid): Cell[] {
  const out: Cell[] = [];
  for (let r = 0; r < grid.rows; r++) for (let c = 0; c < grid.cols; c++) if (grid.blocked[r][c]) out.push([r, c]);
  return out;
}

/** Two rooms joined by a door in the middle wall; used by the hero figure. */
export const HERO_PICTURE: readonly string[] = [
  '#############',
  '#.....#.....#',
  '#.....#.....#',
  '#.....#.....#',
  '#...........#',
  '#.....#.....#',
  '#.....#.....#',
  '###.#####.###',
  '#.....#.....#',
  '#.....#.....#',
  '#...........#',
  '#.....#.....#',
  '#############',
];
export const HERO_START: Cell = [2, 2];
export const HERO_GOAL: Cell = [10, 10];
/** Chosen so the reward-free walk covers all four rooms and passes the goal's cell (pinned by
 *  maze.test.ts): latent learning is about a space explored before any goal exists. */
export const HERO_SEED = 15;
export const HERO_STEPS = 220;
