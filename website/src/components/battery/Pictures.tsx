// Drawings of the five classic paradigms: public illustrations, never a model or a result.
// They are drawn in the landing figure's language (components/landing/MazeFigure.astro): walls as a
// very low structure-blue fill inside a fine structure outline, the agent's trail in ink, one signal
// route, a ringed start and a goal ring with its dot. The agent's trail and route, the arc between a
// test pair and a new goal ring carry the classes that the battery styles draw; doors and node
// labels fade in. Rendered on the server, so they need no client JavaScript of their own. The
// battery page passes `ruled` for the faint cell grid of its sheets (and the whole chain strip);
// the landing's thumbnails leave it off.
import '@/styles/battery.css';
import type { ChainStep, GridStep, Test, TransferStep } from '@/lib/battery.ts';
import { polylinePoints, wallPath, withCell, type Cell, type Grid } from '@/lib/maze.ts';
import { gridLines, wallOutline } from '@/lib/sheet.ts';

type Labelled = { decorative?: boolean };

const svgLabel = (label: string, decorative = false) =>
  decorative ? { 'aria-hidden': true as const, focusable: 'false' as const } : { role: 'img', 'aria-label': label };

/** A class list: `base`, and `extra` after it while `on` holds. */
const withClass = (base: string, extra: string, on: boolean) => (on ? `${base} ${extra}` : base);

const points = (cells?: readonly Cell[] | null) => (cells ? polylinePoints(cells) : '');
const cellKey = (cell?: Cell) => (cell ? `${cell[0]},${cell[1]}` : '');

/** The chain's nodes sit on a pitch of 1.6 units, one unit in from the left edge. */
export const chainX = (i: number) => 1 + i * 1.6;
/** The chain is one-dimensional: a short strip, with room above its nodes for the test pair's arc. */
const CHAIN_HEIGHT = 3.4;
const CHAIN_Y = 2;
const chainWidth = (count: number) => 2 + (count - 1) * 1.6;

/** The drawing's size in its own units: cells for the grid pictures, units for the chain. */
export function viewSize(test: Test): [number, number] {
  switch (test.kind) {
    case 'chain':
      return [chainWidth(test.nodes.length), CHAIN_HEIGHT];
    case 'grid':
      return [test.steps[0].grid.cols, test.steps[0].grid.rows];
    case 'transfer':
      return [test.grid.cols, test.grid.rows];
  }
}

/** The walls of a grid: the low fill and its outline, drawn once as two paths. */
function Walls({ grid }: { grid: Grid }) {
  return (
    <>
      <path className="wall-fill" d={wallPath(grid)} />
      <path className="wall-edge" d={wallOutline(grid)} />
    </>
  );
}

export function GridPicture({ step, prev, decorative, ruled }: { step: GridStep; prev?: GridStep; ruled?: boolean } & Labelled) {
  const g = step.grid;
  const doors = step.doors ?? [];
  const doorsBefore = new Set((prev?.doors ?? []).map(cellKey));
  // A door is drawn as a gate in the wall, so its cell is left out of the wall mass.
  const mass = doors.reduce((grid, cell) => withCell(grid, cell, false), g);
  const fresh = (now?: readonly Cell[] | null, before?: readonly Cell[] | null) => !prev || points(now) !== points(before);
  const newGoal = !prev || cellKey(prev.goal) !== cellKey(step.goal);
  return (
    <svg className="sx-pic" viewBox={`0 0 ${g.cols} ${g.rows}`} {...svgLabel(step.caption, decorative)}>
      {ruled && <path className="cells" d={gridLines(g.cols, g.rows)} />}
      <Walls grid={mass} />
      {doors.map(([r, c]) => (
        <rect key={`d${r},${c}`} className={withClass('door', 'appear', !prev || !doorsBefore.has(`${r},${c}`))} x={c + 0.16} y={r + 0.16} width={0.68} height={0.68} />
      ))}
      {step.trail && <polyline className={withClass('trail', 'draw', fresh(step.trail, prev?.trail))} pathLength={1} points={points(step.trail)} />}
      {step.path && <polyline className={withClass('path', 'draw', fresh(step.path, prev?.path))} pathLength={1} points={points(step.path)} />}
      {step.start && <circle className="start" cx={step.start[1] + 0.5} cy={step.start[0] + 0.5} r={0.34} />}
      {step.goal && (
        <>
          <circle className={withClass('goal-ring', 'appear', newGoal)} cx={step.goal[1] + 0.5} cy={step.goal[0] + 0.5} r={0.62} pathLength={1} />
          <circle className={withClass('goal-dot', 'appear', newGoal)} cx={step.goal[1] + 0.5} cy={step.goal[0] + 0.5} r={0.26} />
        </>
      )}
    </svg>
  );
}

export function ChainPicture({
  nodes,
  step,
  prev,
  decorative,
  ruled,
  idPrefix = 'sx-chain',
}: { nodes: string[]; step: ChainStep; prev?: ChainStep; ruled?: boolean; idPrefix?: string } & Labelled) {
  const width = chainWidth(nodes.length);
  const y = CHAIN_Y;
  // A sheet shows the whole strip; a thumbnail is cropped to the band the nodes and the arc occupy,
  // so they are as large as the box allows.
  const box = ruled ? `0 0 ${width} ${CHAIN_HEIGHT}` : `0.25 ${y - 1.4} ${width - 0.5} 2.4`;
  const arc = step.query
    ? `M ${chainX(step.query[0])} ${y - 0.45} Q ${(chainX(step.query[0]) + chainX(step.query[1])) / 2} ${y - 1.45} ${chainX(step.query[1])} ${y - 0.45}`
    : null;
  const freshArc = !prev || prev.query?.join() !== step.query?.join();
  const maskId = `${idPrefix}-arc`;
  return (
    <svg className="sx-pic" viewBox={box} {...svgLabel(step.caption, decorative)}>
      {/* The datum the nodes stand on. */}
      {ruled && <path className="cells" d={`M0 ${y}h${width}`} />}
      {step.pairs.map(([a, b]) => (
        <line key={`${a}-${b}`} className="edge" x1={chainX(a)} y1={y} x2={chainX(b)} y2={y} />
      ))}
      {arc && (
        <>
          <mask id={maskId} maskUnits="userSpaceOnUse" x={0} y={0} width={width} height={CHAIN_HEIGHT}>
            <path className={withClass('arc-reveal', 'draw', freshArc)} d={arc} pathLength={1} />
          </mask>
          <path className="query" d={arc} mask={`url(#${maskId})`} />
        </>
      )}
      {nodes.map((n, i) => (
        <g key={n}>
          <circle className="node" cx={chainX(i)} cy={y} r={0.42} />
          <text className="node-label" x={chainX(i)} y={y}>
            {n}
          </text>
        </g>
      ))}
    </svg>
  );
}

export function TransferPicture({
  grid,
  marks,
  symbols,
  fresh = false,
  decorative,
  ruled,
}: { grid: Grid; marks: readonly Cell[]; symbols: string[]; fresh?: boolean; ruled?: boolean } & Labelled) {
  return (
    <svg className="sx-pic" viewBox={`0 0 ${grid.cols} ${grid.rows}`} {...svgLabel(`Layout labelled ${symbols.join(', ')}`, decorative)}>
      {ruled && <path className="cells" d={gridLines(grid.cols, grid.rows)} />}
      <Walls grid={grid} />
      {marks.map(([r, c], i) => (
        <g key={`${r},${c}`}>
          <circle className="node" cx={c + 0.5} cy={r + 0.5} r={0.42} />
          <text className={withClass('node-label', 'appear', fresh)} x={c + 0.5} y={r + 0.5}>
            {symbols[i]}
          </text>
        </g>
      ))}
    </svg>
  );
}

/** One test's picture at step `index`; `prev` is the step shown before it, if any. */
export function TestPicture({
  test,
  index,
  prev,
  decorative,
  ruled,
  idPrefix,
}: { test: Test; index: number; prev?: number | null; ruled?: boolean; idPrefix?: string } & Labelled) {
  const before = prev ?? undefined;
  switch (test.kind) {
    case 'grid':
      return <GridPicture step={test.steps[index]} prev={before === undefined ? undefined : test.steps[before]} decorative={decorative} ruled={ruled} />;
    case 'chain':
      return (
        <ChainPicture
          nodes={test.nodes}
          step={test.steps[index]}
          prev={before === undefined ? undefined : test.steps[before]}
          decorative={decorative}
          ruled={ruled}
          idPrefix={idPrefix}
        />
      );
    case 'transfer': {
      const step: TransferStep = test.steps[index];
      const changed = before !== undefined && test.steps[before].set !== step.set;
      return <TransferPicture grid={test.grid} marks={test.marks} symbols={test.symbols[step.set]} fresh={changed} decorative={decorative} ruled={ruled} />;
    }
  }
}
