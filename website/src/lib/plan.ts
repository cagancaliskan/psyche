/**
 * Date logic for the roadmap, over tools/research_plan.json (staged as src/data/plan.json).
 *
 * Pure functions with "today" passed in explicitly: the build never reads the clock, only the
 * browser does, so a rebuild of the same plan produces the same HTML.
 */

export interface PlanPhase {
  id: string;
  title: string;
  start: string | null;
  end: string | null;
  start_rule?: string;
  end_rule?: string;
  gate: string | null;
  status: string;
  outputs: string[];
}
/**
 * What follows a decided gate (D-034): the line continues to the next phase, extends, or stops.
 * One word, never free text, so a verdict cannot reach the public record through it.
 */
export type NextStep = 'continues' | 'extends' | 'stops';

export interface PlanGate {
  id: string;
  title: string;
  baseline_date: string | null;
  date: string | null;
  date_rule?: string;
  status: string;
  /** Only on a decided gate: the day it was decided. */
  decided_on?: string;
  /** Only on a decided gate: what follows. */
  next_step?: NextStep;
  question: string;
  if_missed: string;
}
export interface Plan {
  as_of: string;
  timezone: string;
  /** The research line the plan schedules: its working title and short name. */
  line: { title: string; short_name: string };
  phases: PlanPhase[];
  gates: PlanGate[];
  deadlines: { id: string; title: string; due: string | null; estimate: string; status: string }[];
  layers: { id: string; title: string; summary: string }[];
}

const DAY = 86_400_000;

/** Parse YYYY-MM-DD as a UTC day number (whole days since the epoch). */
export function dayNumber(iso: string): number {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) throw new Error(`not an ISO date: ${iso}`);
  const ms = Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10)));
  if (Number.isNaN(ms) || new Date(ms).toISOString().slice(0, 10) !== iso) throw new Error(`invalid date: ${iso}`);
  return Math.round(ms / DAY);
}

export function isoFromDay(day: number): string {
  return new Date(day * DAY).toISOString().slice(0, 10);
}

/** Today's date in a given IANA time zone, as YYYY-MM-DD (lib/today.ts). */
export { todayIn } from './today.ts';

/** Visible span of each phase on the axis. Open ends are drawn to a fixed horizon, never to today. */
export interface Span {
  phase: PlanPhase;
  from: number;
  to: number;
  openStart: boolean;
  openEnd: boolean;
}

/** Days added past the last dated point so open-ended phases have visible length. */
export const OPEN_PHASE_DAYS = 45;

export function spans(plan: Plan): Span[] {
  const out: Span[] = [];
  let cursor: number | null = null;
  for (const phase of plan.phases) {
    const openStart = phase.start === null;
    const from: number = phase.start !== null ? dayNumber(phase.start) : (cursor ?? dayNumber(plan.as_of));
    const openEnd = phase.end === null;
    const to: number = phase.end !== null ? dayNumber(phase.end) : from + OPEN_PHASE_DAYS;
    if (to < from) throw new Error(`phase ${phase.id} ends before it starts`);
    out.push({ phase, from, to, openStart, openEnd });
    cursor = to;
  }
  return out;
}

export function axisRange(plan: Plan): { from: number; to: number } {
  const s = spans(plan);
  return { from: Math.min(...s.map((x) => x.from)), to: Math.max(...s.map((x) => x.to)) };
}

/** Position of a day on the axis as a fraction in [0, 1] (clamped). */
export function fraction(day: number, range: { from: number; to: number }): number {
  if (range.to === range.from) return 0;
  return Math.min(1, Math.max(0, (day - range.from) / (range.to - range.from)));
}

/** First day of each month inside the range, for axis ticks. */
export function monthTicks(range: { from: number; to: number }): { day: number; label: string }[] {
  const ticks: { day: number; label: string }[] = [];
  const start = new Date(range.from * DAY);
  let y = start.getUTCFullYear();
  let m = start.getUTCMonth() + 1;
  for (;;) {
    if (m > 11) {
      m = 0;
      y += 1;
    }
    const day = Math.round(Date.UTC(y, m, 1) / DAY);
    if (day > range.to) break;
    const label = new Date(day * DAY).toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' }) + (m === 0 ? ` ${y}` : '');
    ticks.push({ day, label });
    m += 1;
  }
  return ticks;
}

/** The decided gate after which the line stops, if the plan records one. */
export function lineStoppedAt(plan: Plan): PlanGate | null {
  return plan.gates.find((g) => g.status === 'decided' && g.next_step === 'stops') ?? null;
}

/**
 * The phase the line is in: the one the plan marks active, and none once the line has stopped.
 * The plan is the only source. A gate decided with "continues" or "stops" can only be recorded
 * together with its phase marked done (the plan check enforces it), so a phase that a decision has
 * closed is never the one marked active; the next phase becomes current when the plan marks it
 * active in the same edit, never by the date alone. The phase bands, the list chips, the
 * generated "Now" line and this function therefore read the same label and cannot disagree.
 */
export function currentPhase(plan: Plan): PlanPhase | null {
  if (lineStoppedAt(plan)) return null;
  return plan.phases.find((p) => p.status === 'active') ?? null;
}

/** Where a gate stands on a given day. */
export type GateState =
  | { kind: 'decided'; decidedOn: string | null; nextStep: NextStep | null }
  /** The gate's date has passed and the plan records no decision. */
  | { kind: 'pending'; daysOver: number }
  | { kind: 'upcoming'; daysLeft: number }
  /** No fixed date yet; the plan holds a rule for it. */
  | { kind: 'unscheduled' }
  /** Not decided, and the line stopped at an earlier decision: this gate will not be reached. */
  | { kind: 'not-reached'; stoppedAt: string };

/**
 * Where a gate stands on `today`. `stoppedAt` is the id of the gate at which the line stopped
 * (lineStoppedAt), or null: an undecided gate is then never waited on, so it is not pending.
 */
export function gateState(
  gate: Pick<PlanGate, 'status' | 'date' | 'decided_on' | 'next_step'>,
  today: string,
  stoppedAt: string | null = null,
): GateState {
  if (gate.status === 'decided') {
    return { kind: 'decided', decidedOn: gate.decided_on ?? null, nextStep: gate.next_step ?? null };
  }
  if (stoppedAt !== null) return { kind: 'not-reached', stoppedAt };
  if (gate.date === null) return { kind: 'unscheduled' };
  const d = dayNumber(gate.date) - dayNumber(today);
  return d < 0 ? { kind: 'pending', daysOver: -d } : { kind: 'upcoming', daysLeft: d };
}

/** What a decided gate says is next, in the public record's own words (D-034). */
export const NEXT_STEP_TEXT: Record<NextStep, string> = {
  continues: 'the line continues to the next phase',
  extends: 'the line extends',
  stops: 'the line stops',
};

/** The chip for a gate: its tone (a data-tone value the stylesheet knows) and its words. */
export function gateLabel(state: GateState): { tone: 'decided' | 'pending' | 'upcoming'; text: string } {
  if (state.kind === 'decided') return { tone: 'decided', text: 'Decided' };
  if (state.kind === 'pending') return { tone: 'pending', text: 'Decision pending' };
  if (state.kind === 'not-reached') return { tone: 'upcoming', text: 'Not reached' };
  return { tone: 'upcoming', text: 'Upcoming' };
}

/**
 * What the public record says about a gate beyond its date: for a decided gate the day it was
 * decided and the next step, for a gate past its date that no decision is recorded yet, and for a
 * gate behind a stop that the line stopped before it. Null for a gate still to come.
 */
export function gateNote(gate: Pick<PlanGate, 'date'>, state: GateState): string | null {
  if (state.kind === 'pending') {
    return gate.date ? `Decision pending. The gate was due on ${formatDay(gate.date)}.` : 'Decision pending.';
  }
  if (state.kind === 'not-reached') return `The line stopped at Gate ${state.stoppedAt}.`;
  if (state.kind !== 'decided') return null;
  const head = state.decidedOn ? `Decided on ${formatDay(state.decidedOn)}.` : 'Decided.';
  if (!state.nextStep) return head;
  const step = NEXT_STEP_TEXT[state.nextStep];
  return `${head} ${step.charAt(0).toUpperCase()}${step.slice(1)}.`;
}

/** A gate as a short phrase, for titles and accessible names: "decision pending", "decided on ...", "not reached". */
export function gatePhrase(state: GateState): string {
  if (state.kind === 'pending') return 'decision pending';
  if (state.kind === 'not-reached') return 'not reached';
  if (state.kind === 'upcoming' || state.kind === 'unscheduled') return 'upcoming';
  const on = state.decidedOn ? `decided on ${formatDay(state.decidedOn)}` : 'decided';
  return state.nextStep ? `${on}, ${NEXT_STEP_TEXT[state.nextStep]}` : on;
}

export interface NextGate extends PlanGate {
  /** Whole days from `today` to the gate's date; negative once the date has passed. */
  daysLeft: number;
  /** The date has passed and no decision is recorded: shown as "decision pending". */
  pending: boolean;
}

/**
 * The gate the line is waiting on: the earliest dated gate that is not decided, whether its date
 * is still ahead or has passed. A gate past its date with no recorded decision is still next, and
 * is pending; it is never skipped for a later one. Null once the line has stopped.
 */
export function nextGate(plan: Plan, today: string): NextGate | null {
  if (lineStoppedAt(plan)) return null;
  const t = dayNumber(today);
  let best: NextGate | null = null;
  for (const g of plan.gates) {
    if (g.status !== 'upcoming' || g.date === null) continue;
    const d = dayNumber(g.date) - t;
    if (best === null || d < best.daysLeft) best = { ...g, daysLeft: d, pending: d < 0 };
  }
  return best;
}

export function formatDay(iso: string): string {
  const d = new Date(dayNumber(iso) * DAY);
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
}

/**
 * A phase's dates in words: "1 March 2027 to 15 April 2027", or the plan's own rule wherever a
 * date is not fixed yet.
 */
export function phaseWhen(phase: PlanPhase): string {
  const from = phase.start ? formatDay(phase.start) : null;
  const to = phase.end ? formatDay(phase.end) : null;
  if (from && to) return `${from} to ${to}`;
  if (from) return `${from} to ${phase.end_rule ?? 'an end not yet fixed'}`;
  const start = `Starts ${phase.start_rule ?? 'on a date not yet fixed'}`;
  return to ? `${start}, ends ${to}` : `${start}; end ${phase.end_rule ?? 'not yet fixed'}`;
}
