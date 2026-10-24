/**
 * Illustrations of the five classic paradigms the test battery is built from.
 * Public-knowledge drawings only: no protocol parameters, no criteria, no model.
 */
import { parseGrid, randomWalk, shortestPath, withCell, type Cell, type Grid } from './maze.ts';

export interface GridStep {
  label: string;
  caption: string;
  grid: Grid;
  /** Cells drawn as a closed door (structure colour, solid). */
  doors?: Cell[];
  trail?: Cell[];
  path?: Cell[] | null;
  goal?: Cell;
  start?: Cell;
}

export interface ChainStep {
  label: string;
  caption: string;
  pairs: [number, number][];
  query?: [number, number];
}

export interface TransferStep {
  label: string;
  caption: string;
  /** Which symbol set labels the layout. */
  set: 0 | 1;
}

export type Test =
  | { id: string; name: string; paradigm: string; summary: string; kind: 'grid'; steps: GridStep[] }
  | { id: string; name: string; paradigm: string; summary: string; kind: 'chain'; nodes: string[]; steps: ChainStep[] }
  | { id: string; name: string; paradigm: string; summary: string; kind: 'transfer'; grid: Grid; symbols: [string[], string[]]; marks: Cell[]; steps: TransferStep[] };

const ROOM = parseGrid([
  '#########',
  '#.......#',
  '#.#####.#',
  '#.#...#.#',
  '#.#.#.#.#',
  '#...#...#',
  '#########',
]);

const T1_START: Cell = [1, 1];
const T1_GOAL: Cell = [3, 3];

const LOOP = parseGrid([
  '#########',
  '#.......#',
  '#.#####.#',
  '#.#####.#',
  '#.......#',
  '#########',
]);
const LOOP_START: Cell = [1, 1];
const LOOP_GOAL: Cell = [4, 5];
const LOOP_DOOR: Cell = [4, 3];

const CORRIDOR = parseGrid([
  '#########',
  '#.......#',
  '#.#####.#',
  '#.#.....#',
  '#.#######',
  '#.......#',
  '#########',
]);
const SC_START: Cell = [5, 7];
const SC_GOAL: Cell = [3, 3];
const SC_GAP: Cell = [4, 3];

const closedLoop = withCell(LOOP, LOOP_DOOR, true);
const openCorridor = withCell(CORRIDOR, SC_GAP, false);

export const TESTS: Test[] = [
  {
    id: 'T1',
    name: 'Latent learning',
    paradigm: 'After Tolman (1948)',
    summary:
      'Exploration carries no reward. A goal is introduced afterwards. The test asks whether what was learned during reward-free exploration is available as soon as the goal appears.',
    kind: 'grid',
    steps: [
      { label: 'Explore', caption: 'Reward-free exploration: the trail covers the space, no goal exists yet.', grid: ROOM, start: T1_START, trail: randomWalk(ROOM, T1_START, 90, 30) },
      { label: 'Goal introduced', caption: 'After exploration, a goal is introduced.', grid: ROOM, start: T1_START, goal: T1_GOAL, trail: randomWalk(ROOM, T1_START, 90, 30) },
      { label: 'Direct route', caption: 'The direct route to the goal.', grid: ROOM, start: T1_START, goal: T1_GOAL, path: shortestPath(ROOM, T1_START, T1_GOAL) },
    ],
  },
  {
    id: 'T2',
    name: 'Detour',
    paradigm: 'After Tolman and Honzik (1930)',
    summary:
      'After the space is learned, a familiar route is blocked. The test asks whether the agent turns to a suitable alternative, using what it already knows about the environment.',
    kind: 'grid',
    steps: [
      { label: 'Usual route', caption: 'The learned, shortest route to the goal.', grid: LOOP, start: LOOP_START, goal: LOOP_GOAL, path: shortestPath(LOOP, LOOP_START, LOOP_GOAL) },
      { label: 'Door closes', caption: 'A door on that route closes.', grid: closedLoop, doors: [LOOP_DOOR], start: LOOP_START, goal: LOOP_GOAL },
      { label: 'Detour', caption: 'Another known route to the goal.', grid: closedLoop, doors: [LOOP_DOOR], start: LOOP_START, goal: LOOP_GOAL, path: shortestPath(closedLoop, LOOP_START, LOOP_GOAL) },
    ],
  },
  {
    id: 'T3',
    name: 'Shortcut',
    paradigm: 'After Tolman, Ritchie and Kalish (1946)',
    summary:
      'A direct route that was not available during exploration becomes available. The test asks whether the agent takes a direct route between places it knows but has never travelled between directly.',
    kind: 'grid',
    steps: [
      { label: 'Known route', caption: 'During exploration the passage is closed; the only route is long.', grid: CORRIDOR, doors: [SC_GAP], start: SC_START, goal: SC_GOAL, path: shortestPath(CORRIDOR, SC_START, SC_GOAL) },
      { label: 'Passage opens', caption: 'The passage opens.', grid: openCorridor, start: SC_START, goal: SC_GOAL },
      { label: 'Shortcut', caption: 'The new, shorter route through the opened passage.', grid: openCorridor, start: SC_START, goal: SC_GOAL, path: shortestPath(openCorridor, SC_START, SC_GOAL) },
    ],
  },
  {
    id: 'T4',
    name: 'Structural transfer',
    paradigm: 'Learning a layout once and reusing it',
    summary:
      'A second environment shares the layout of the first but not its observations. The test asks whether structure learned in the first speeds learning in the second.',
    kind: 'transfer',
    grid: ROOM,
    symbols: [
      ['A', 'B', 'C', 'D'],
      ['W', 'X', 'Y', 'Z'],
    ],
    marks: [[1, 1], [1, 7], [5, 1], [3, 3]],
    steps: [
      { label: 'Environment one', caption: 'The first environment, with its own observations.', set: 0 },
      { label: 'Environment two', caption: 'Same layout, new observations everywhere.', set: 1 },
    ],
  },
  {
    id: 'T5',
    name: 'Transitive inference',
    paradigm: 'For example, Dusek and Eichenbaum (1997)',
    summary:
      'Only neighbouring pairs of an ordered chain are trained. The test asks whether the agent orders a pair it never saw together, such as B and D in the classic studies.',
    kind: 'chain',
    nodes: ['A', 'B', 'C', 'D', 'E'],
    steps: [
      { label: 'Training pairs', caption: 'Only neighbouring pairs are shown: A and B, B and C, C and D, D and E.', pairs: [[0, 1], [1, 2], [2, 3], [3, 4]] },
      { label: 'Test pair', caption: 'A pair never seen together: B and D.', pairs: [[0, 1], [1, 2], [2, 3], [3, 4]], query: [1, 3] },
    ],
  },
];
