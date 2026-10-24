import { useEffect, useMemo, useState } from 'react';
import {
  axisRange,
  dayNumber,
  formatDay,
  fraction,
  monthTicks,
  spans,
  todayIn,
  type Plan,
} from '../lib/plan.ts';

interface Props {
  plan: Plan;
}

const pct = (x: number) => `${(x * 100).toFixed(3)}%`;

/**
 * Interactive phase timeline. Each phase is a button; choosing one shows its outputs and gate
 * below. The today marker is added after hydration only, so the server-rendered HTML never
 * contains a date that would go stale.
 */
export default function Timeline({ plan }: Props) {
  const rows = useMemo(() => spans(plan), [plan]);
  const range = useMemo(() => axisRange(plan), [plan]);
  const ticks = useMemo(() => monthTicks(range), [range]);
  const gates = useMemo(() => new Map(plan.gates.map((g) => [g.id, g])), [plan]);
  const active = plan.phases.find((p) => p.status === 'active')?.id ?? plan.phases[0]?.id;
  const [selected, setSelected] = useState<string>(active);
  const [today, setToday] = useState<string | null>(null);

  useEffect(() => {
    setToday(todayIn(plan.timezone, new Date()));
  }, [plan.timezone]);

  const chosen = rows.find((r) => r.phase.id === selected) ?? rows[0];
  const gate = chosen.phase.gate ? gates.get(chosen.phase.gate) : undefined;
  const todayDay = today ? dayNumber(today) : null;
  const todayVisible = todayDay !== null && todayDay >= range.from && todayDay <= range.to;

  return (
    <div className="sx-timeline" aria-label="Thesis phases on a time axis">
      <div className="sx-timeline__axis" aria-hidden="true">
        {ticks.map((t) => (
          <span key={t.day} className="sx-timeline__tick" style={{ left: pct(fraction(t.day, range)) }}>
            {t.label}
          </span>
        ))}
      </div>
      <div className="sx-timeline__body">
      <ol className="sx-timeline__rows">
        {rows.map((r) => {
          const left = fraction(r.from, range);
          const end = fraction(r.to, range);
          const width = Math.max(end - left, 0.012);
          const g = r.phase.gate ? gates.get(r.phase.gate) : undefined;
          const gateDay = g?.date ? dayNumber(g.date) : null;
          // Labels sit after the band (and its gate marker); late phases put them before it.
          const labelAfter = end <= 0.6;
          const labelStyle = labelAfter
            ? { left: `calc(${pct(left + width)} + ${gateDay !== null ? '1rem' : '0.5rem'})` }
            : { right: `calc(${pct(1 - left)} + 0.5rem)` };
          const when = r.phase.start && r.phase.end
            ? `${formatDay(r.phase.start)} to ${formatDay(r.phase.end)}`
            : r.phase.start
              ? `from ${formatDay(r.phase.start)}, ${r.phase.end_rule ?? 'end not yet fixed'}`
              : r.phase.start_rule ?? 'start not yet fixed';
          return (
            <li key={r.phase.id} className="sx-timeline__row">
              <button
                type="button"
                className="sx-timeline__hit"
                aria-pressed={selected === r.phase.id}
                aria-label={`${r.phase.id}: ${r.phase.title}, ${when}, ${r.phase.status}`}
                onClick={() => setSelected(r.phase.id)}
              >
                <span
                  className="sx-timeline__band"
                  style={{ left: pct(left), width: pct(width) }}
                  data-status={r.phase.status}
                  data-open={r.openEnd || r.openStart ? 'true' : 'false'}
                  aria-hidden="true"
                />
                <span className="sx-timeline__label" style={labelStyle} aria-hidden="true">
                  <span className="sx-timeline__id">{r.phase.id}</span>
                  {r.phase.title}
                </span>
              </button>
              {gateDay !== null && (
                <span
                  className="sx-timeline__gate"
                  style={{ left: pct(fraction(gateDay, range)) }}
                  title={`Gate ${g!.id}: ${g!.title}, ${formatDay(g!.date!)}`}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
      {todayVisible && (
        <span className="sx-timeline__today" style={{ left: pct(fraction(todayDay!, range)) }} aria-hidden="true">
          <span>Today</span>
        </span>
      )}
      </div>
      <section className="sx-timeline__detail" aria-live="polite">
        <h3>
          {chosen.phase.id}: {chosen.phase.title}
        </h3>
        <p>
          {chosen.phase.start ? formatDay(chosen.phase.start) : chosen.phase.start_rule}
          {' to '}
          {chosen.phase.end ? formatDay(chosen.phase.end) : chosen.phase.end_rule}
          {` (${chosen.phase.status})`}
        </p>
        <ul>
          {chosen.phase.outputs.map((o) => (
            <li key={o}>{o}</li>
          ))}
        </ul>
        {gate && (
          <p>
            Ends at Gate {gate.id} ({gate.title})
            {gate.date ? `, on ${formatDay(gate.date)}` : `, ${gate.date_rule}`}: {gate.question}
          </p>
        )}
      </section>
    </div>
  );
}
