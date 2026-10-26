/**
 * Drafting geometry for the battery's sheets (components/battery/Pictures.tsx and
 * components/BatteryExplorer.tsx): the outline of the walls, the faint cell grid and the rulers on
 * a sheet's two axes. Pure functions of integer sizes, so the same input always draws the same
 * sheet.
 */
import type { Grid } from './maze.ts';

const solid = (grid: Grid, r: number, c: number) => r >= 0 && c >= 0 && r < grid.rows && c < grid.cols && grid.blocked[r][c];

/**
 * The outline of the wall cells as one SVG path: every side of a wall cell that faces an open
 * cell or the edge of the grid, with straight runs merged (`M x y h n` and `M x y v n`). A wall
 * mass is drawn as its boundary only, never as a frame around each cell.
 */
export function wallOutline(grid: Grid): string {
  let d = '';
  for (let r = 0; r <= grid.rows; r++) {
    for (let c = 0; c < grid.cols; ) {
      if (solid(grid, r - 1, c) === solid(grid, r, c)) {
        c++;
        continue;
      }
      let n = 1;
      while (c + n < grid.cols && solid(grid, r - 1, c + n) !== solid(grid, r, c + n)) n++;
      d += `M${c} ${r}h${n}`;
      c += n;
    }
  }
  for (let c = 0; c <= grid.cols; c++) {
    for (let r = 0; r < grid.rows; ) {
      if (solid(grid, r, c - 1) === solid(grid, r, c)) {
        r++;
        continue;
      }
      let n = 1;
      while (r + n < grid.rows && solid(grid, r + n, c - 1) !== solid(grid, r + n, c)) n++;
      d += `M${c} ${r}v${n}`;
      r += n;
    }
  }
  return d;
}

/** The faint cell grid inside a `cols` by `rows` sheet: a line at every inner cell edge. */
export function gridLines(cols: number, rows: number): string {
  let d = '';
  for (let c = 1; c < cols; c++) d += `M${c} 0v${rows}`;
  for (let r = 1; r < rows; r++) d += `M0 ${r}h${cols}`;
  return d;
}

export interface Tick {
  /** Position along the axis, in the drawing's units. */
  at: number;
  /** The numeral set on the tick, when it has one. */
  label?: string;
}

export interface Ruler {
  /** The axis' length, in the drawing's units. */
  len: number;
  /** Long ticks, with their numerals. */
  major: Tick[];
  /** Short ticks. */
  minor: number[];
}

/** Two digits, as the sheets set every numeral. */
export const pad2 = (n: number) => String(Math.round(n)).padStart(2, '0');

/**
 * A ruler in grid cells: a short tick at every cell edge, a long one with its numeral on every
 * third (so a nine-cell axis reads 00, 03, 06, 09).
 */
export function cellRuler(len: number): Ruler {
  const major: Tick[] = [];
  const minor: number[] = [];
  for (let at = 0; at <= len; at++) {
    if (at % 3 === 0) major.push({ at, label: pad2(at) });
    else minor.push(at);
  }
  return { len, major, minor };
}

/**
 * A ruler for a row of points (the nodes of the chain): a long tick on each point, a short tick
 * halfway between neighbours and at both ends of the axis. The ticks carry no numerals: the points
 * are already named on the drawing, and naming them twice would only repeat them.
 */
export function pointRuler(len: number, points: readonly number[]): Ruler {
  const major = points.map((at) => ({ at }));
  const half = (a: number, b: number) => Math.round(((a + b) / 2) * 1000) / 1000;
  const minor = [0, ...points.slice(1).map((at, i) => half(points[i], at)), len];
  return { len, major, minor };
}
