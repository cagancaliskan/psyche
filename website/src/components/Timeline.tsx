import { useEffect, useMemo, useState } from 'react';
import {
  axisRange,
  dayNumber,
  formatDay,
  fraction,
  monthTicks,
  phaseWhen,
  spans,
  todayIn,
  type Plan,
} from '../lib/plan.ts';
import '../styles/plan.css';

interface Props {
  plan: Plan;
}

const pct = (x: number) => `${(x * 100).toFixed(3)}%`;
const tone = (status: string) => (status === 'active' ? 'now' : status);
const label = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/**
 * Interactive phase timeline: one pill band per phase on a date axis, gate diamonds at gate dates.
 * Choosing a phase shows its outputs and gate in the card below. The today line is added after
 * hydration only, so the server-rendered HTML never contains a date that would go stale.
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
  const todayAt = todayVisible ? fraction(todayDay!, range) : 0;
  const todayAlign = todayAt < 0.06 ? 'start' : todayAt > 0.94 ? 'end' : 'center';

  return (
    <div className="sx-tl-wrap not-content">
      <div className="sx-tl" role="group" aria-label="Research phases on a time axis">
        <div className="sx-tl__axis" aria-hidden="true">
          {ticks.map((t) => (
            <span key={t.day} className="sx-tl__tick" style={{ left: pct(fraction(t.day, range)) }}>
              {t.label}
            </span>
          ))}
        </div>
        <div className="sx-tl__body">
          {ticks.map((t) => (
            <span
              key={t.day}
              className="sx-tl__gridline"
              style={{ left: pct(fraction(t.day, range)) }}
              aria-hidden="true"
            />
          ))}
          <ol className="sx-tl__rows">
            {rows.map((r) => {
              const left = fraction(r.from, range);
              const end = fraction(r.to, range);
              const width = Math.max(end - left, 0.012);
              const g = r.phase.gate ? gates.get(r.phase.gate) : undefined;
              const gateDay = g?.date ? dayNumber(g.date) : null;
              // Labels sit after the band (and its gate marker); late phases put them before it.
              // Each label may wrap to a second line inside the room it has.
              const after = end <= 0.6;
              const gap = gateDay !== null ? '1rem' : '0.5rem';
              const labelStyle = after
                ? { left: `calc(${pct(left + width)} + ${gap})`, maxWidth: `calc(${pct(1 - left - width)} - ${gap})` }
                : { right: `calc(${pct(1 - left)} + 0.5rem)`, maxWidth: `calc(${pct(left)} - 0.5rem)` };
              return (
                <li key={r.phase.id} className="sx-tl__row">
                  <button
                    type="button"
                    className="sx-tl__hit"
                    aria-pressed={selected === r.phase.id}
                    aria-label={`${r.phase.id}: ${r.phase.title}, ${phaseWhen(r.phase)}, ${r.phase.status}`}
                    onClick={() => setSelected(r.phase.id)}
                  >
                    <span
                      className="sx-tl__band"
                      style={{ left: pct(left), width: pct(width) }}
                      data-status={r.phase.status}
                      data-open={r.openEnd || r.openStart ? 'true' : 'false'}
                      aria-hidden="true"
                    />
                    <span className="sx-tl__label" data-side={after ? 'after' : 'before'} style={labelStyle} aria-hidden="true">
                      <span className="sx-tl__id">{r.phase.id}</span> {r.phase.title}
                    </span>
                  </button>
                  {gateDay !== null && (
                    <span
                      className="sx-tl__gate"
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
            <span className="sx-tl__today" data-align={todayAlign} style={{ left: pct(todayAt) }} aria-hidden="true">
              <span className="sx-tl__today-chip">Today</span>
            </span>
          )}
        </div>
        <section className="sx-tl__card" data-status={chosen.phase.status} aria-live="polite">
          <div className="sx-tl__card-head">
            <span className="sx-tl__card-id" aria-hidden="true">
              {chosen.phase.id}
            </span>
            <h3>
              <span className="sr-only">{chosen.phase.id}: </span>
              {chosen.phase.title}
            </h3>{' '}
            <span className="sx-chip" data-tone={tone(chosen.phase.status)}>
              {label(chosen.phase.status)}
            </span>
          </div>
          <p className="sx-tl__when">{phaseWhen(chosen.phase)}</p>
          <p className="sx-tl__kicker">Outputs</p>
          <ul className="sx-tl__outputs">
            {chosen.phase.outputs.map((o) => (
              <li key={o}>{o}</li>
            ))}
          </ul>
          {gate && (
            <p className="sx-tl__gateline">
              <span className="sx-diamond" aria-hidden="true" />
              <span>
                Ends at Gate {gate.id} ({gate.title}){gate.date ? `, on ${formatDay(gate.date)}` : `, ${gate.date_rule}`}:{' '}
                {gate.question}
              </span>
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
