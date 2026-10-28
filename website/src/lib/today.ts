/**
 * Today's date in a given IANA time zone, as YYYY-MM-DD. A module of its own, so that a page script that
 * needs only the day (components/chrome/NextGateClock.astro) does not load the rest of the plan's logic;
 * lib/plan.ts exports it too.
 */
export function todayIn(timeZone: string, now: Date): string {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(now);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? '';
  return `${get('year')}-${get('month')}-${get('day')}`;
}
