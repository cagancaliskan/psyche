/**
 * The Atom feed of the progress page (pages/progress.xml.ts): a serialiser and nothing else. Which events
 * the plan has, in what order and in what words is decided once, in Python
 * (tools/publish/render_plan.py progress_events), and staged as src/data/progress.json by
 * tools/publish/stage.py; the progress page's table is written from the same list. This file turns that
 * list into Atom 1.0 (RFC 4287) and adds no event, no wording and no clock: the same data gives the same
 * bytes on any day and any machine, so a rebuild changes the feed only when the plan changes.
 *
 * No framework import, so `npm test` runs it as it is.
 */

/** One event of the plan, as render_plan.py progress_events writes it. */
export interface ProgressEvent {
  /** Stable for the life of the event: it names the kind and the item, and for a change the day and field. */
  id: string;
  kind: string;
  /** The day, YYYY-MM-DD, in the plan's time zone. */
  date: string;
  item: string;
  /** What the event is about: "Gate A, Novelty". */
  subject: string;
  /** A title for a feed entry: "Gate A decided". */
  headline: string;
  /** What happened, in lower case, to follow the subject: "decided; the line continues to the next phase". */
  change: string;
}

/** src/data/progress.json. */
export interface ProgressData {
  as_of: string;
  timezone: string;
  /** The first author of CITATION.cff, as the file gives the name. */
  author: string;
  events: ProgressEvent[];
}

/** The feed file, below the site base. */
export const FEED_FILE = 'progress.xml';
/** The page the feed is a record of, below the site base. */
export const PROGRESS_PAGE = 'progress/';
export const FEED_TITLE = 'Psyche progress';
export const FEED_SUBTITLE = "The public record of Psyche's research plan: phases, gates, dates and commitments.";
export const FEED_MEDIA_TYPE = 'application/atom+xml';

/**
 * The time of day an event is stamped with. An event has a day and no time, and Atom needs a date and
 * time, so every event is stamped noon UTC: the same calendar day in every zone from UTC-11 to UTC+11,
 * which includes the plan's own. Midnight would fall on the day before for a reader west of the plan's
 * zone, and the build's clock must not be used.
 */
export const STAMP_TIME = 'T12:00:00Z';

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

/** A day as an RFC 3339 date-time. Throws on anything that is not a calendar day. */
export function stamp(day: string): string {
  const ms = ISO_DAY.test(day) ? Date.parse(`${day}T00:00:00Z`) : Number.NaN;
  if (Number.isNaN(ms) || new Date(ms).toISOString().slice(0, 10) !== day) throw new Error(`not a calendar day: ${day}`);
  return day + STAMP_TIME;
}

// What XML 1.0 allows in text (production Char). Anything else is replaced, so the output is well-formed
// whatever the plan's text holds.
const ILLEGAL = /[^\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD\u{10000}-\u{10FFFF}]/gu;

/** Text for an element's content or an attribute value: the five predefined entities, and no character XML 1.0 forbids. */
export function escapeXml(text: string): string {
  return text
    .replace(ILLEGAL, '\uFFFD')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

/** The year the feed began in. It dates the host name in every tag URI (RFC 4151) and is never updated. */
export const TAG_YEAR = '2026';

/**
 * A tag URI (RFC 4151) for the feed or an entry: the site's host name, the year the feed began in and a
 * path below the site's base. It names an entry and not a place to fetch it, so it is the same on every
 * build and a reader never takes an entry for a new one when the site is rebuilt. It is made from the site's
 * address, so it does change if the host or the base path does: moving the site would make every entry new.
 */
export function tagId(siteUrl: string, path: string): string {
  const { hostname, pathname } = new URL(siteUrl);
  const prefix = pathname.replace(/^\/+|\/+$/g, '');
  const rest = [prefix, path].filter(Boolean).join('/');
  return `tag:${hostname},${TAG_YEAR}:${encodeURI(rest)}`;
}

/** Absolute address of a file or page of the site; `siteUrl` is the origin, the base and a closing slash. */
function absolute(siteUrl: string, path: string): string {
  return new URL(path, siteUrl).href;
}

/** An element holding text, with an optional attribute list already escaped. */
function leaf(name: string, text: string, indent = '  ', attrs = ''): string {
  return `${indent}<${name}${attrs}>${escapeXml(text)}</${name}>`;
}

const TEXT = ' type="text"';

/** The feed's `updated`: the newest event's day, or the day the plan was written when it has no event. */
export function feedDay(data: Pick<ProgressData, 'as_of' | 'events'>): string {
  return data.events.reduce((newest, e) => (e.date > newest ? e.date : newest), data.events.length ? data.events[0].date : data.as_of);
}

/**
 * Atom 1.0 for the progress data. Entries are written in the order given (the staged list is newest first);
 * the feed's `updated` is the newest day among them, never the build time. `siteUrl` is the site's origin
 * and base with a closing slash, from the Astro configuration, so every address is absolute.
 */
export function atomFeed(data: ProgressData, siteUrl: string): string {
  if (!siteUrl.endsWith('/')) throw new Error(`the site address must end in a slash: ${siteUrl}`);
  const self = absolute(siteUrl, FEED_FILE);
  const page = absolute(siteUrl, PROGRESS_PAGE);
  const lines: string[] = [
    '<?xml version="1.0" encoding="utf-8"?>',
    '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">',
    leaf('id', tagId(siteUrl, FEED_FILE)),
    leaf('title', FEED_TITLE, '  ', TEXT),
    leaf('subtitle', FEED_SUBTITLE, '  ', TEXT),
    leaf('updated', stamp(feedDay(data))),
    `  <link rel="self" type="${FEED_MEDIA_TYPE}" href="${escapeXml(self)}"/>`,
    `  <link rel="alternate" type="text/html" href="${escapeXml(page)}"/>`,
    `  <author>\n${leaf('name', data.author, '    ')}\n  </author>`,
  ];
  for (const e of data.events) {
    lines.push(
      '  <entry>',
      leaf('id', tagId(siteUrl, `${PROGRESS_PAGE}${e.id}`), '    '),
      leaf('title', e.headline, '    ', TEXT),
      leaf('updated', stamp(e.date), '    '),
      `    <link rel="alternate" type="text/html" href="${escapeXml(page)}"/>`,
      leaf('summary', `${e.subject}: ${e.change}.`, '    ', TEXT),
      '  </entry>',
    );
  }
  lines.push('</feed>', '');
  return lines.join('\n');
}
