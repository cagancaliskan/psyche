import { useEffect, useState } from 'react';
import { currentPhase, formatDay, nextGate, todayIn, type Plan } from '../lib/plan.ts';
import '../styles/plan.css';

interface Props {
  plan: Plan;
  /** Lead word for the current phase, e.g. 'Now in stage 2' on the landing page. */
  label?: string;
}

/**
 * Current phase and next gate, as two chips. The server render uses the plan's own as_of date, so
 * the HTML is deterministic; the browser then recomputes the next gate and adds the days left.
 */
export default function NowLine({ plan, label = 'Now' }: Props) {
  const phase = currentPhase(plan);
  const [today, setToday] = useState<string | null>(null);
  useEffect(() => setToday(todayIn(plan.timezone, new Date())), [plan.timezone]);
  const gate = nextGate(plan, today ?? plan.as_of);
  const dates = phase?.start && phase.end ? `, ${formatDay(phase.start)} to ${formatDay(phase.end)}` : '';

  return (
    <div className="sx-nowchips not-content">
      {phase && (
        <p className="sx-pair" data-tone="now">
          <span className="sx-pair__key">
            <span>{label}</span>
            <span className="sr-only">: </span>
          </span>{' '}
          <span className="sx-pair__val">
            {phase.id} {phase.title}
            {dates}
          </span>
        </p>
      )}
      <p className="sx-pair">
        <span className="sx-pair__key">
          <span>Next gate</span>
          <span className="sr-only">: </span>
        </span>{' '}
        {gate ? (
          <span className="sx-pair__val">
            <span>
              Gate {gate.id} ({gate.title}), {formatDay(gate.date!)}
            </span>
            {today !== null && (
              <>
                <span className="sr-only">, </span>
                <span className="sx-pair__days">
                  {gate.daysLeft === 0 ? 'today' : `${gate.daysLeft} ${gate.daysLeft === 1 ? 'day' : 'days'} left`}
                </span>
              </>
            )}
          </span>
        ) : (
          <span className="sx-pair__val">none dated yet</span>
        )}
      </p>
    </div>
  );
}
