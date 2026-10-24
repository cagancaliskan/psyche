import { useState } from 'react';
import { TESTS, type ChainStep, type GridStep, type Test } from '../lib/battery.ts';
import { polylinePoints, wallCells, type Grid } from '../lib/maze.ts';

/**
 * Five paradigm illustrations. Every change of picture is a response to a button press; nothing
 * moves on its own. The caption is announced to screen readers when the step changes.
 */
export default function BatteryExplorer() {
  return (
    <ol className="sx-battery">
      {TESTS.map((t) => (
        <li key={t.id} id={t.id.toLowerCase()}>
          <Illustration test={t} />
          <div>
            <h3>
              {t.id}: {t.name}
            </h3>
            <p className="sx-battery__paradigm">{t.paradigm}</p>
            <p>{t.summary}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

function Illustration({ test }: { test: Test }) {
  const [step, setStep] = useState(0);
  const steps = test.steps;
  const current = steps[step];
  return (
    <figure className="sx-illustration">
      {test.kind === 'grid' && <GridPicture step={current as GridStep} />}
      {test.kind === 'chain' && <ChainPicture nodes={test.nodes} step={current as ChainStep} />}
      {test.kind === 'transfer' && (
        <TransferPicture grid={test.grid} marks={test.marks} symbols={test.symbols[(current as { set: 0 | 1 }).set]} />
      )}
      <div className="sx-step-controls" role="group" aria-label={`${test.name} illustration steps`}>
        {steps.map((s, i) => (
          <button key={s.label} type="button" aria-pressed={i === step} onClick={() => setStep(i)}>
            {s.label}
          </button>
        ))}
      </div>
      <figcaption aria-live="polite">{current.caption}</figcaption>
    </figure>
  );
}

function GridPicture({ step }: { step: GridStep }) {
  const g = step.grid;
  const doors = new Set((step.doors ?? []).map(([r, c]) => `${r},${c}`));
  return (
    <svg viewBox={`0 0 ${g.cols} ${g.rows}`} role="img" aria-label={step.caption}>
      <rect className="floor" x={0} y={0} width={g.cols} height={g.rows} />
      {wallCells(g).map(([r, c]) =>
        doors.has(`${r},${c}`) ? (
          <rect key={`d${r},${c}`} className="door" x={c + 0.12} y={r + 0.12} width={0.76} height={0.76} rx={0.12} />
        ) : (
          <rect key={`w${r},${c}`} className="wall" x={c} y={r} width={1} height={1} />
        ),
      )}
      {step.trail && <polyline className="trail" points={polylinePoints(step.trail)} />}
      {step.path && <polyline className="path" points={polylinePoints(step.path)} />}
      {step.start && <circle className="start-dot" cx={step.start[1] + 0.5} cy={step.start[0] + 0.5} r={0.28} fill="none" stroke="currentColor" strokeWidth={0.12} />}
      {step.goal && <circle className="goal" cx={step.goal[1] + 0.5} cy={step.goal[0] + 0.5} r={0.32} />}
    </svg>
  );
}

function ChainPicture({ nodes, step }: { nodes: string[]; step: ChainStep }) {
  const x = (i: number) => 1 + i * 1.6;
  const y = 1.4;
  return (
    <svg viewBox={`0 0 ${2 + (nodes.length - 1) * 1.6} 3`} role="img" aria-label={step.caption}>
      {step.pairs.map(([a, b]) => (
        <line key={`${a}-${b}`} className="edge" x1={x(a)} y1={y} x2={x(b)} y2={y} />
      ))}
      {step.query && (
        <path
          className="query"
          d={`M ${x(step.query[0])} ${y - 0.45} Q ${(x(step.query[0]) + x(step.query[1])) / 2} ${y - 1.45} ${x(step.query[1])} ${y - 0.45}`}
        />
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

function TransferPicture({ grid, marks, symbols }: { grid: Grid; marks: readonly (readonly [number, number])[]; symbols: string[] }) {
  return (
    <svg viewBox={`0 0 ${grid.cols} ${grid.rows}`} role="img" aria-label={`Layout labelled ${symbols.join(', ')}`}>
      <rect className="floor" x={0} y={0} width={grid.cols} height={grid.rows} />
      {wallCells(grid).map(([r, c]) => (
        <rect key={`w${r},${c}`} className="wall" x={c} y={r} width={1} height={1} />
      ))}
      {marks.map(([r, c], i) => (
        <g key={`${r},${c}`}>
          <circle className="node" cx={c + 0.5} cy={r + 0.5} r={0.42} />
          <text className="node-label" x={c + 0.5} y={r + 0.5}>
            {symbols[i]}
          </text>
        </g>
      ))}
    </svg>
  );
}
