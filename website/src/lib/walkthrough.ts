/**
 * The pictures of the walk-through page (/battery/): one flat line drawing per test and step, from the
 * paradigms in lib/battery.ts. Public illustrations only, never a model or a result.
 *
 * A picture is a list of shapes (an SVG element name, its attributes and, for a letter, its text) that
 * pages/battery.astro writes into the HTML. Every colour comes from the stylesheet through the shape's
 * class (bw-wall, bw-route and the rest), so one drawing reads in both themes. The walls are the
 * outlines of the wall masses (lib/sheet.ts wallOutline); a shut door is a short mark across the
 * corridor at its cell; the route a line through cell centres; the start an open ring; the goal a ring
 * with its dot; reward-free exploration a dotted trail.
 *
 * Pure functions with no framework import, so `npm test` runs them.
 */
import type { Test } from './battery.ts';
import { isOpen, polylinePoints, withCell, type Cell, type Grid } from './maze.ts';
import { wallOutline } from './sheet.ts';

export interface Shape {
  el: 'path' | 'polyline' | 'circle' | 'line' | 'text';
  attrs: Record<string, string | number>;
  /** The letter of a node. */
  text?: string;
}

/** Three decimals at most, as the drawing's numbers are written. */
const r3 = (n: number) => Math.round(n * 1000) / 1000;
/** The centre of a cell: [x, y]. */
const centre = ([row, col]: Cell): [number, number] => [col + 0.5, row + 0.5];

/** The chain's nodes stand on a pitch of 1.6 units, one unit in from the left, on the line y = 2. */
const CHAIN_Y = 2;
export const chainX = (i: number) => 1 + i * 1.6;

/**
 * A shut door at `cell`: a mark across the corridor through the cell's centre, a cell wide. Where the
 * corridor runs left and right the mark stands upright; where it runs up and down it lies flat.
 */
export function doorPath(grid: Grid, cell: Cell): string {
  const [x, y] = centre(cell);
  const across = isOpen(grid, [cell[0], cell[1] - 1]) || isOpen(grid, [cell[0], cell[1] + 1]);
  return across ? `M${x} ${y}L${x} ${y + 0.5}M${x} ${y}L${x} ${y - 0.5}` : `M${x} ${y}L${x + 0.5} ${y}M${x} ${y}L${x - 0.5} ${y}`;
}

/** The drawing's view: the inside of the grid's outer wall, or the band the chain and its arc occupy. */
export function viewBox(test: Test): string {
  if (test.kind === 'chain') return '0 0.2 8.4 2.7';
  const g = test.kind === 'grid' ? test.steps[0].grid : test.grid;
  return `0.5 0.5 ${g.cols - 1} ${g.rows - 1}`;
}

/** What a picture shows, in words, for assistive technology: the test, the step and its caption. */
export function stepLabel(test: Test, i: number): string {
  return `${test.name}, step ${i + 1} of ${test.steps.length}: ${test.steps[i].caption}`;
}

/** The shapes of test `test` at step `i`, in drawing order. */
export function stepShapes(test: Test, i: number): Shape[] {
  const out: Shape[] = [];
  if (test.kind === 'chain') {
    const s = test.steps[i];
    const y = CHAIN_Y;
    for (const [a, b] of s.pairs) out.push({ el: 'line', attrs: { class: 'bw-edge', x1: r3(chainX(a) + 0.42), y1: y, x2: r3(chainX(b) - 0.42), y2: y } });
    if (s.query) {
      const a = chainX(s.query[0]);
      const b = chainX(s.query[1]);
      out.push({ el: 'path', attrs: { class: 'bw-route', d: `M${r3(a)} ${r3(y - 0.48)}Q${r3((a + b) / 2)} ${r3(y - 1.6)} ${r3(b)} ${r3(y - 0.48)}` } });
    }
    test.nodes.forEach((n, k) => {
      const asked = !!s.query && (k === s.query[0] || k === s.query[1]);
      out.push({ el: 'circle', attrs: { class: asked ? 'bw-node bw-node--asked' : 'bw-node', cx: r3(chainX(k)), cy: y, r: 0.42 } });
      out.push({ el: 'text', attrs: { class: 'bw-letter', x: r3(chainX(k)), y }, text: n });
    });
    return out;
  }
  if (test.kind === 'transfer') {
    const s = test.steps[i];
    out.push({ el: 'path', attrs: { class: 'bw-wall', d: wallOutline(test.grid) } });
    test.marks.forEach((m, k) => {
      const [x, y] = centre(m);
      out.push({ el: 'circle', attrs: { class: 'bw-node', cx: x, cy: y, r: 0.38 } });
      out.push({ el: 'text', attrs: { class: 'bw-letter', x, y }, text: test.symbols[s.set][k] });
    });
    return out;
  }
  const s = test.steps[i];
  const doors = s.doors ?? [];
  // a door is drawn as a mark in an open corridor, so its cell is left out of the wall mass
  const mass = doors.reduce((g, cell) => withCell(g, cell, false), s.grid);
  out.push({ el: 'path', attrs: { class: 'bw-wall', d: wallOutline(mass) } });
  for (const cell of doors) out.push({ el: 'path', attrs: { class: 'bw-door', d: doorPath(mass, cell) } });
  if (s.trail) out.push({ el: 'polyline', attrs: { class: 'bw-trail', points: polylinePoints(s.trail) } });
  if (s.path) out.push({ el: 'polyline', attrs: { class: 'bw-route', points: polylinePoints(s.path) } });
  if (s.goal) {
    const [x, y] = centre(s.goal);
    out.push({ el: 'circle', attrs: { class: 'bw-goal', cx: x, cy: y, r: 0.36 } });
    out.push({ el: 'circle', attrs: { class: 'bw-goal-dot', cx: x, cy: y, r: 0.15 } });
  }
  if (s.start) {
    const [x, y] = centre(s.start);
    out.push({ el: 'circle', attrs: { class: 'bw-start', cx: x, cy: y, r: 0.26 } });
  }
  return out;
}
