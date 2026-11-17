/**
 * The timeline page (/roadmap/): what its drawing, its "Now" lines, its phase table and its gate parts
 * say, read from the research plan (tools/research_plan.json, staged as src/data/plan.json) through
 * lib/plan.ts. The page writes it all on the server as of the plan's own as_of date, so a rebuild of the
 * same plan gives the same HTML; in the browser lib/timelineView.ts reads the reader's day and moves
 * what depends on it (a gate past its date with no decision becomes "decision pending", the days left
 * to the next gate, the today line) with these same functions.
 *
 * Pure functions with no framework import and no clock, so `npm test` runs them on fixtures.
 */
import {
  axisRange,
  dayNumber,
  formatDay,
  fraction,
  gateLabel,
  gateNote,
  gateState,
  lineStoppedAt,
  nextGate,
  type NextStep,
  type Plan,
  type PlanGate,
} from './plan.ts';

const DAY = 86_400_000;
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** A fraction of the axis as an SVG length: "12.345%". */
export const pct = (f: number): string => `${(f * 100).toFixed(3)}%`;

/** A lower-case word with its first letter in capitals: "active" becomes "Active". */
export const cap = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1);

/** A month on the axis: where it starts, its short name, and the year under it in January only. */
export interface AxisMonth {
  at: string;
  month: string;
  year: number | null;
}

/** The first day of each month inside the plan's axis, the month the axis starts in left out. */
export function axisMonths(range: { from: number; to: number }): AxisMonth[] {
  const out: AxisMonth[] = [];
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
    out.push({ at: pct(fraction(day, range)), month: MONTHS[m], year: m === 0 ? y : null });
    m += 1;
  }
  return out;
}

/** Where a day falls on the plan's axis, as an SVG length; null for a day off the axis. */
export function dayAt(plan: Plan, iso: string): string | null {
  const range = axisRange(plan);
  const day = dayNumber(iso);
  return day < range.from || day > range.to ? null : pct(fraction(day, range));
}

/** The id of a gate's heading: "gate-a-novelty". */
export function gateSlug(gate: Pick<PlanGate, 'id' | 'title'>): string {
  const words = `gate ${gate.id} ${gate.title}`.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  return words.replace(/^-+|-+$/g, '');
}

/** A gate's date in words, or its rule where the plan fixes no date yet. */
export function gateWhen(gate: Pick<PlanGate, 'date' | 'date_rule'>): string {
  return gate.date ? formatDay(gate.date) : (gate.date_rule ?? 'a date not yet fixed');
}

/** What the page says of a gate on a given day: its state word and the note under it (or none). */
export interface GateReading {
  word: string;
  note: string | null;
}

/** The gates as the page needs them to say where each stands. */
export type GateInput = Pick<PlanGate, 'id' | 'date' | 'status' | 'decided_on' | 'next_step'>;

/** Where every gate stands on `today`, by id: "Upcoming", "Decision pending", "Decided" or "Not reached". */
export function gateReadings(gates: GateInput[], today: string): Map<string, GateReading> {
  const asPlan = { gates } as unknown as Plan;
  const stoppedAt = lineStoppedAt(asPlan)?.id ?? null;
  const out = new Map<string, GateReading>();
  for (const g of gates) {
    const state = gateState(g, today, stoppedAt);
    out.set(g.id, { word: gateLabel(state).text, note: gateNote(g, state) });
  }
  return out;
}

/** The gate the line waits on: the earliest dated gate not yet decided. It does not depend on the day. */
export function nextGateId(gates: GateInput[]): string | null {
  return nextGate({ gates } as unknown as Plan, '1970-01-01')?.id ?? null;
}

/** What follows the next gate's date in the "Next gate" line: ", decision pending", ", today" or ", 12 days left". */
export function daysWords(gates: GateInput[], today: string): string {
  const next = nextGate({ gates } as unknown as Plan, today);
  if (!next) return '';
  if (next.pending) return ', decision pending';
  if (next.daysLeft === 0) return ', today';
  return `, ${next.daysLeft} ${next.daysLeft === 1 ? 'day' : 'days'} left`;
}

/** A gate as the page's markup carries it (data-gate-id, data-date and the rest), back to its facts. */
export function gateFromData(data: { gateId?: string; date?: string; state?: string; decidedOn?: string; nextStep?: string }): GateInput {
  return {
    id: data.gateId ?? '',
    date: data.date ? data.date : null,
    status: data.state ?? 'upcoming',
    decided_on: data.decidedOn ? data.decidedOn : undefined,
    next_step: data.nextStep ? (data.nextStep as NextStep) : undefined,
  };
}
