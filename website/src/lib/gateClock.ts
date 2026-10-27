import { gateLabel, gateNote, gateState, lineStoppedAt, nextGate, todayIn, type NextStep, type Plan, type PlanGate } from './plan.ts';

/**
 * Brings server-rendered gates up to date with the reader's day. The page is built without a
 * clock, so its gates are read as of the plan's own as_of date; in the browser this moves the
 * "next" mark to the gate the line is waiting on today, turns a gate past its date with no
 * recorded decision into "decision pending", and writes the note under it. The decision is the
 * same one the React islands make, because both call the functions in plan.ts.
 *
 * The markup it reads, on each gate's element: data-gate-id, data-date (empty when the gate has
 * no fixed date), data-state (the plan's status word), data-decided-on and data-next-step (empty
 * unless decided). Inside it, all optional: [data-gate-mark] gets data-next, [data-gate-chip]
 * gets the label and tone, [data-next-chip] is shown for the next gate only, and [data-gate-note]
 * gets the note, or is hidden when there is none. An element with data-gate-current also carries
 * aria-current="step" while it is the next gate. `root` names the plan's time zone in data-tz.
 */
export function applyGateClock(root: HTMLElement): void {
  let today: string;
  try {
    today = todayIn(root.dataset.tz ?? 'UTC', new Date());
  } catch {
    return;
  }
  const items = [...root.querySelectorAll<HTMLElement>('[data-gate-id]')];
  const gates: PlanGate[] = items.map((el) => ({
    id: el.dataset.gateId ?? '',
    title: '',
    baseline_date: null,
    date: el.dataset.date ? el.dataset.date : null,
    status: el.dataset.state ?? 'upcoming',
    decided_on: el.dataset.decidedOn ? el.dataset.decidedOn : undefined,
    next_step: el.dataset.nextStep ? (el.dataset.nextStep as NextStep) : undefined,
    question: '',
    if_missed: '',
  }));
  const plan = { gates } as unknown as Plan;
  const next = nextGate(plan, today)?.id ?? null;
  const stoppedAt = lineStoppedAt(plan)?.id ?? null;
  items.forEach((el, i) => {
    const gate = gates[i];
    const state = gateState(gate, today, stoppedAt);
    const label = gateLabel(state);
    const note = gateNote(gate, state);
    const on = gate.id === next;

    el.toggleAttribute('data-next', on);
    el.dataset.gateState = state.kind;
    if (el.hasAttribute('data-gate-current')) {
      if (on) el.setAttribute('aria-current', 'step');
      else el.removeAttribute('aria-current');
    }
    for (const mark of el.querySelectorAll<HTMLElement>('[data-gate-mark]')) {
      mark.toggleAttribute('data-next', on);
      mark.dataset.gateState = state.kind;
    }
    const chip = el.querySelector<HTMLElement>('[data-gate-chip]');
    if (chip) {
      chip.textContent = label.text;
      chip.dataset.tone = label.tone;
    }
    const nextChip = el.querySelector<HTMLElement>('[data-next-chip]');
    if (nextChip) nextChip.hidden = !on;
    const noteEl = el.querySelector<HTMLElement>('[data-gate-note]');
    if (noteEl) {
      noteEl.textContent = note ?? '';
      noteEl.hidden = note === null;
    }
  });
}
