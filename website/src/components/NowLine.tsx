import { useEffect, useState } from 'react';
import { currentPhase, formatDay, nextGate, todayIn, type Plan } from '../lib/plan.ts';

interface Props {
  plan: Plan;
}

/**
 * Current phase and next gate. The server render uses the plan's own as_of date, so the HTML is
 * deterministic; the browser then recomputes the next gate and adds the days left.
 */
export default function NowLine({ plan }: Props) {
  const phase = currentPhase(plan);
  const [today, setToday] = useState<string | null>(null);
  useEffect(() => setToday(todayIn(plan.timezone, new Date())), [plan.timezone]);
  const gate = nextGate(plan, today ?? plan.as_of);

  return (
    <div className="sx-now">
      {phase && (
        <p>
          <strong>Now:</strong> {phase.id} {phase.title}
          {phase.start && phase.end ? `, ${formatDay(phase.start)} to ${formatDay(phase.end)}` : ''}
        </p>
      )}
      {gate ? (
        <p>
          <strong>Next gate:</strong> Gate {gate.id} ({gate.title}), {formatDay(gate.date!)}
          {today !== null && (
            <>
              {' '}
              <span className="sx-now__days">
                {gate.daysLeft === 0 ? '(today)' : `(${gate.daysLeft} ${gate.daysLeft === 1 ? 'day' : 'days'} left)`}
              </span>
            </>
          )}
        </p>
      ) : (
        <p>
          <strong>Next gate:</strong> none dated yet
        </p>
      )}
    </div>
  );
}
