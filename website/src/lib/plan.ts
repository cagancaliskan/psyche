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
export interface PlanGate {
  id: string;
  title: string;
  baseline_date: string | null;
  date: string | null;
  date_rule?: string;
  status: string;
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

/** Today's date in a given IANA time zone, as YYYY-MM-DD. */
export function todayIn(timeZone: string, now: Date): string {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(now);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? '';
  return `${get('year')}-${get('month')}-${get('day')}`;
}

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

export function currentPhase(plan: Plan): PlanPhase | null {
  return plan.phases.find((p) => p.status === 'active') ?? null;
}

/** The next upcoming gate with a date on or after `today` (YYYY-MM-DD), or null. */
export function nextGate(plan: Plan, today: string): (PlanGate & { daysLeft: number }) | null {
  const t = dayNumber(today);
  let best: (PlanGate & { daysLeft: number }) | null = null;
  for (const g of plan.gates) {
    if (g.status !== 'upcoming' || g.date === null) continue;
    const d = dayNumber(g.date) - t;
    if (d < 0) continue;
    if (best === null || d < best.daysLeft) best = { ...g, daysLeft: d };
  }
  return best;
}

export function formatDay(iso: string): string {
  const d = new Date(dayNumber(iso) * DAY);
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
}
