/**
 * Deterministic grid-world geometry for the site's illustrations.
 *
 * These are drawings of classic behavioural paradigms (Tolman-style latent learning, detours,
 * shortcuts), not results and not a model: the "agent" here is a seeded walk, and its route is the
 * shortest path on a fully known grid. Everything is integer arithmetic with a fixed neighbour
 * order, so the same inputs always draw the same picture.
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


/** SVG path data through cell centres, in grid units, with straight runs merged into one move. */
export function cellPath(path: readonly Cell[]): string {
  if (path.length === 0) return '';
  let d = `M${path[0][1] + 0.5} ${path[0][0] + 0.5}`;
  for (let i = 1; i < path.length; ) {
    const dr = path[i][0] - path[i - 1][0];
    const dc = path[i][1] - path[i - 1][1];
    let n = 1;
    while (i + n < path.length && path[i + n][0] - path[i + n - 1][0] === dr && path[i + n][1] - path[i + n - 1][1] === dc) n++;
    d += dr !== 0 ? `v${dr * n}` : `h${dc * n}`;
    i += n;
  }
  return d;
}

/**
 * The wall cells in columns [fromCol, toCol) as one SVG path: runs of wall cells merged into
 * rectangles (`M x y h w v h h -w z`), so a whole field draws as one element instead of hundreds.
 * The rectangles never overlap and cover exactly the wall cells.
 */
export function wallPath(grid: Grid, fromCol = 0, toCol = grid.cols): string {
  type Rect = { c: number; w: number; r: number; h: number };
  let d = '';
  let growing: Rect[] = [];
  for (let r = 0; r <= grid.rows; r++) {
    const runs: [number, number][] = [];
    if (r < grid.rows) {
      for (let c = Math.max(0, fromCol); c < Math.min(grid.cols, toCol); c++) {
        if (!grid.blocked[r][c]) continue;
        const last = runs[runs.length - 1];
        if (last && last[0] + last[1] === c) last[1]++;
        else runs.push([c, 1]);
      }
    }
    const kept: Rect[] = [];
    for (const rect of growing) {
      const k = runs.findIndex(([c, w]) => c === rect.c && w === rect.w);
      if (k >= 0) {
        rect.h++;
        runs.splice(k, 1);
        kept.push(rect);
      } else d += `M${rect.c} ${rect.r}h${rect.w}v${rect.h}h-${rect.w}z`;
    }
    growing = kept.concat(runs.map(([c, w]) => ({ c, w, r, h: 1 })));
  }
  return d;
}

/** A field of square rooms on a regular pitch, joined by one-cell doors. */
export interface FieldSpec {
  /** Rooms down and across. */
  roomRows: number;
  roomCols: number;
  /** Open cells along a room's side; rooms sit on a pitch of size + 1, one wall cell apart. */
  size: number;
  /** The arena's leftmost room column. Rooms left of it are a decorative wing. */
  arenaFrom: number;
  /** Doors added on each side beyond its spanning tree, so there is more than one way round. */
  extraDoors: number;
}

/** The arena's leftmost grid column (the cell after its west wall). */
export function arenaColumn(spec: FieldSpec): number {
  return spec.arenaFrom * (spec.size + 1) + 1;
}

/**
 * A seeded field of rooms. The wing (room columns before `arenaFrom`) and the arena each get a
 * spanning tree of doors, so each is connected on its own; one door joins the two; then
 * `extraDoors` more doors on each side close loops, so a direct route can cut across.
 */
export function roomField(spec: FieldSpec, seed: number): Grid {
  const { roomRows, roomCols, size, arenaFrom, extraDoors } = spec;
  if (size < 3 || roomRows < 1 || roomCols < 2 || arenaFrom < 1 || arenaFrom >= roomCols) throw new Error('bad field spec');
  const pitch = size + 1;
  const rows = roomRows * pitch + 1;
  const cols = roomCols * pitch + 1;
  const blocked = Array.from({ length: rows }, (_, r) => Array.from({ length: cols }, (_, c) => r % pitch === 0 || c % pitch === 0));
  const next = prng(seed);

  /** Neighbouring room pairs as [row, col, dRow, dCol], in a fixed order, then shuffled. */
  const pairs: [number, number, number, number][] = [];
  for (let i = 0; i < roomRows; i++) {
    for (let j = 0; j < roomCols; j++) {
      if (j + 1 < roomCols) pairs.push([i, j, 0, 1]);
      if (i + 1 < roomRows) pairs.push([i, j, 1, 0]);
    }
  }
  for (let k = pairs.length - 1; k > 0; k--) {
    const m = next() % (k + 1);
    [pairs[k], pairs[m]] = [pairs[m], pairs[k]];
  }

  const door = ([i, j, di]: readonly number[]) => {
    const offset = 1 + (next() % (size - 2));
    if (di === 0) blocked[i * pitch + offset][(j + 1) * pitch] = false;
    else blocked[(i + 1) * pitch][j * pitch + offset] = false;
  };
  const side = (j: number) => (j < arenaFrom ? 0 : 1);
  const parent = Array.from({ length: roomRows * roomCols }, (_, k) => k);
  const root = (k: number): number => {
    while (parent[k] !== k) k = parent[k] = parent[parent[k]];
    return k;
  };

  const crossing: (typeof pairs)[number][] = [];
  const spare: (typeof pairs)[number][] = [];
  for (const p of pairs) {
    const [i, j, di, dj] = p;
    if (side(j) !== side(j + dj)) {
      crossing.push(p);
      continue;
    }
    const a = root(i * roomCols + j);
    const b = root((i + di) * roomCols + j + dj);
    if (a === b) spare.push(p);
    else {
      parent[a] = b;
      door(p);
    }
  }
  door(crossing[0]);
  for (const s of [0, 1]) spare.filter(([, j]) => side(j) === s).slice(0, extraDoors).forEach(door);
  return { rows, cols, blocked };
}

/** The same grid with every cell left of `col` walled, so a walk or route cannot leave the arena. */
export function closeLeftOf(grid: Grid, col: number): Grid {
  return { ...grid, blocked: grid.blocked.map((row) => row.map((wall, c) => wall || c < col)) };
}

/**
 * A reward-free walk that keeps its heading. It goes straight on; where the wall alongside it opens
 * (a doorway, or the end of a wall) it turns in one time in two; when the way ahead is a wall, or
 * one step in `turnOneIn` at random, it picks a new direction. It turns back only when nothing else
 * is open. Straight runs and wall-following read as exploring rather than jitter.
 */
export function persistentWalk(grid: Grid, start: Cell, steps: number, seed: number, turnOneIn = 6): Cell[] {
  if (!isOpen(grid, start)) throw new Error('start is not an open cell');
  const next = prng(seed);
  const step = ([r, c]: Cell, h: number): Cell => [r + STEPS[h][0], c + STEPS[h][1]];
  const walk: Cell[] = [start];
  let here = start;
  let heading = next() % 4;
  for (let i = 0; i < steps; i++) {
    const back = (heading + 2) % 4;
    const before = walk.length > 1 ? walk[walk.length - 2] : null;
    const openings = before ? [(heading + 1) % 4, (heading + 3) % 4].filter((h) => isOpen(grid, step(here, h)) && !isOpen(grid, step(before, h))) : [];
    const roll = next();
    if (openings.length > 0 && roll % 2 === 0) heading = openings[(roll >>> 1) % openings.length];
    else if (!isOpen(grid, step(here, heading)) || roll % turnOneIn === 1) {
      const options = [0, 1, 2, 3].filter((h) => h !== back && isOpen(grid, step(here, h)));
      if (options.length > 0) heading = options[next() % options.length];
      else if (isOpen(grid, step(here, back))) heading = back;
      else break;
    }
    here = step(here, heading);
    walk.push(here);
  }
  return walk;
}

/**
 * The landing hero's field: 8 by 3 rooms of 7 by 7 on a pitch of 8, a 65 by 25 grid. Room columns
 * 0-3 are a faded wing behind the copy; columns 4-7 are the arena, where the trail and the route
 * stay. The seed and step count are pinned by maze.test.ts: the walk explores every arena room and
 * passes the goal's cell before any goal exists, then the route crosses the field to it.
 */
export const FIELD_SPEC: FieldSpec = { roomRows: 3, roomCols: 8, size: 7, arenaFrom: 4, extraDoors: 3 };
export const FIELD_SEED = 222;
export const FIELD_STEPS = 320;
export const FIELD_START: Cell = [20, 36];
export const FIELD_GOAL: Cell = [4, 60];
