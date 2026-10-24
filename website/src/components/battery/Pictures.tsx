// Drawings of the five classic paradigms: public illustrations, never a model or a result.
// Walls in the structure colour; the agent's route has a soft halo under it, and the goal a glow.
// Only the agent's trail and route (with its halo), and the arc between a test pair, carry the
// `draw` class that the battery styles animate. Rendered on the server, so they need no client
// JavaScript of their own.
import { clsx } from 'clsx';
import '@/styles/battery.css';
import type { ChainStep, GridStep, Test, TransferStep } from '@/lib/battery.ts';
import { polylinePoints, wallCells, type Cell, type Grid } from '@/lib/maze.ts';

type Labelled = { decorative?: boolean };

const svgLabel = (label: string, decorative = false) =>
  decorative ? { 'aria-hidden': true as const, focusable: 'false' as const } : { role: 'img', 'aria-label': label };

const points = (cells?: readonly Cell[] | null) => (cells ? polylinePoints(cells) : '');
const cellKey = (cell?: Cell) => (cell ? `${cell[0]},${cell[1]}` : '');

export function GridPicture({ step, prev, decorative }: { step: GridStep; prev?: GridStep } & Labelled) {
  const g = step.grid;
  const doors = new Set((step.doors ?? []).map(cellKey));
  const doorsBefore = new Set((prev?.doors ?? []).map(cellKey));
  const fresh = (now?: readonly Cell[] | null, before?: readonly Cell[] | null) => !prev || points(now) !== points(before);
  return (
    <svg className="sx-pic" viewBox={`0 0 ${g.cols} ${g.rows}`} {...svgLabel(step.caption, decorative)}>
      <rect className="floor" x={0} y={0} width={g.cols} height={g.rows} />
      {wallCells(g).map(([r, c]) =>
        doors.has(`${r},${c}`) ? (
          <rect
            key={`d${r},${c}`}
            className={clsx('door', (!prev || !doorsBefore.has(`${r},${c}`)) && 'appear')}
            x={c + 0.12}
            y={r + 0.12}
            width={0.76}
            height={0.76}
            rx={0.12}
          />
        ) : (
          <rect key={`w${r},${c}`} className="wall" x={c} y={r} width={1} height={1} />
        ),
      )}
      {step.trail && <polyline className={clsx('trail', fresh(step.trail, prev?.trail) && 'draw')} pathLength={1} points={points(step.trail)} />}
      {step.path && <polyline className={clsx('path-glow', fresh(step.path, prev?.path) && 'draw')} pathLength={1} points={points(step.path)} />}
      {step.path && <polyline className={clsx('path', fresh(step.path, prev?.path) && 'draw')} pathLength={1} points={points(step.path)} />}
      {step.start && <circle className="start-dot" cx={step.start[1] + 0.5} cy={step.start[0] + 0.5} r={0.28} />}
      {step.goal && (
        <>
          <circle
            className={clsx('goal-glow', (!prev || cellKey(prev.goal) !== cellKey(step.goal)) && 'appear')}
            cx={step.goal[1] + 0.5}
            cy={step.goal[0] + 0.5}
            r={0.62}
          />
          <circle
            className={clsx('goal', (!prev || cellKey(prev.goal) !== cellKey(step.goal)) && 'appear')}
            cx={step.goal[1] + 0.5}
            cy={step.goal[0] + 0.5}
            r={0.3}
          />
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
  idPrefix = 'sx-chain',
}: { nodes: string[]; step: ChainStep; prev?: ChainStep; idPrefix?: string } & Labelled) {
  const x = (i: number) => 1 + i * 1.6;
  const y = 1.4;
  const width = 2 + (nodes.length - 1) * 1.6;
  const height = 3;
  const arc = step.query
    ? `M ${x(step.query[0])} ${y - 0.45} Q ${(x(step.query[0]) + x(step.query[1])) / 2} ${y - 1.45} ${x(step.query[1])} ${y - 0.45}`
    : null;
  const freshArc = !prev || prev.query?.join() !== step.query?.join();
  const maskId = `${idPrefix}-arc`;
  return (
    <svg className="sx-pic" viewBox={`0 0 ${width} ${height}`} {...svgLabel(step.caption, decorative)}>
      {step.pairs.map(([a, b]) => (
        <line key={`${a}-${b}`} className="edge" x1={x(a)} y1={y} x2={x(b)} y2={y} />
      ))}
      {arc && (
        <>
          <mask id={maskId} maskUnits="userSpaceOnUse" x={0} y={0} width={width} height={height}>
            <path className={clsx('arc-reveal', freshArc && 'draw')} d={arc} pathLength={1} />
          </mask>
          <path className="query" d={arc} mask={`url(#${maskId})`} />
        </>
      )}
      {nodes.map((n, i) => (
        <g key={n}>
          <circle className="node" cx={x(i)} cy={y} r={0.42} />
          <text className="node-label" x={x(i)} y={y}>
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
}: { grid: Grid; marks: readonly Cell[]; symbols: string[]; fresh?: boolean } & Labelled) {
  return (
    <svg className="sx-pic" viewBox={`0 0 ${grid.cols} ${grid.rows}`} {...svgLabel(`Layout labelled ${symbols.join(', ')}`, decorative)}>
      <rect className="floor" x={0} y={0} width={grid.cols} height={grid.rows} />
      {wallCells(grid).map(([r, c]) => (
        <rect key={`w${r},${c}`} className="wall" x={c} y={r} width={1} height={1} />
      ))}
      {marks.map(([r, c], i) => (
        <g key={`${r},${c}`}>
          <circle className="node" cx={c + 0.5} cy={r + 0.5} r={0.42} />
          <text className={clsx('node-label', fresh && 'appear')} x={c + 0.5} y={r + 0.5}>
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
  idPrefix,
}: { test: Test; index: number; prev?: number | null; idPrefix?: string } & Labelled) {
  const before = prev ?? undefined;
  switch (test.kind) {
    case 'grid':
      return <GridPicture step={test.steps[index]} prev={before === undefined ? undefined : test.steps[before]} decorative={decorative} />;
    case 'chain':
      return (
        <ChainPicture
          nodes={test.nodes}
          step={test.steps[index]}
          prev={before === undefined ? undefined : test.steps[before]}
          decorative={decorative}
          idPrefix={idPrefix}
        />
      );
    case 'transfer': {
      const step: TransferStep = test.steps[index];
      const changed = before !== undefined && test.steps[before].set !== step.set;
      return <TransferPicture grid={test.grid} marks={test.marks} symbols={test.symbols[step.set]} fresh={changed} decorative={decorative} />;
    }
  }
}
