/**
 * The pure logic behind the strip above a page title (components/chrome/PageTitle.astro) and the title
 * block at the foot of a page (components/chrome/Footer.astro): which section a page sits in, the state
 * of the stage it belongs to, the sheet number, the next gate, the footer's date and its links. No
 * framework import, so `npm test` runs it as it is.
 *
 * Nothing here is a list of pages and nothing is typed per page. The section and the sheet number are
 * read from the sidebar Starlight built for the page (the staged sidebar, tools/publish/stage.py), the
 * stage state from the public ledger projection (src/data/ledger.public.json), the next gate from the
 * public plan (src/data/plan.json) and the date from git (scripts/sitemap-lastmod.mjs).
 */
import type { ProgramLine, PublicLedger } from './ledger.ts';
import { formatDay, nextGate, type Plan } from './plan.ts';
import { NOT_FOUND, REPO_URL } from './seo.ts';

/** The part of a Starlight sidebar entry that is read here (utils/routing/types.d.ts). */
export interface SidebarItem {
  type: 'link' | 'group';
  label: string;
  href?: string;
  isCurrent?: boolean;
  entries?: SidebarItem[];
}

function holdsCurrent(item: SidebarItem): boolean {
  if (item.type === 'link') return item.isCurrent === true;
  return (item.entries ?? []).some(holdsCurrent);
}

/**
 * The title of the sidebar's first group, and of the manifest section (docs/publish.json) whose pages stand
 * in it after Home (tools/publish/stage.py START_GROUP). A page of this group belongs to no stage: it opens
 * with the group's number and name ("01 Start here") like the hand-written pages beside it, and neither the
 * strip nor the title block gives it a stage or a stage's state. pageChrome.test.ts holds the manifest to it.
 */
export const START_SECTION = 'Start here';

/**
 * A sidebar group's label as a section name: the label itself. The labels in docs/publish.json carry no
 * state ("Cognitive maps", "Substrate"), because a state is typed once, in the ledger, and read from
 * there by the stage line; pageChrome.test.ts fails when a section title names one.
 */
export function sectionName(label: string): string {
  return label.trim();
}

export interface Section {
  /** The group's place among the sidebar's groups, "01", "02": the number the sidebar shows beside it. */
  index: string;
  name: string;
}

/**
 * The top-level sidebar group that holds the page being shown, or null when the page is in none
 * (the 404 page, a page left out of the sidebar). The index counts groups only, as the sidebar's own
 * numbering does.
 */
export function sectionOf(sidebar: readonly SidebarItem[]): Section | null {
  let position = 0;
  for (const item of sidebar) {
    if (item.type !== 'group') continue;
    position += 1;
    if (holdsCurrent(item)) return { index: String(position).padStart(2, '0'), name: sectionName(item.label) };
  }
  return null;
}

/** Every link of the sidebar, in the order the sidebar shows them, groups opened out. */
export function flattenLinks(sidebar: readonly SidebarItem[]): { label: string; href: string; isCurrent: boolean }[] {
  const out: { label: string; href: string; isCurrent: boolean }[] = [];
  const walk = (items: readonly SidebarItem[]) => {
    for (const item of items) {
      if (item.type === 'link') out.push({ label: item.label, href: item.href ?? '', isCurrent: item.isCurrent === true });
      else walk(item.entries ?? []);
    }
  };
  walk(sidebar);
  return out;
}

/**
 * The sheet number of the page being shown: its place among all the sidebar's links, with the total,
 * both counted from the sidebar and padded to the width of the total ("05 / 16"). Null when the page
 * is not in the sidebar.
 */
export function sheetOf(sidebar: readonly SidebarItem[]): { position: string; total: string; text: string } | null {
  const links = flattenLinks(sidebar);
  const at = links.findIndex((l) => l.isCurrent);
  if (at < 0) return null;
  const width = String(links.length).length;
  const position = String(at + 1).padStart(width, '0');
  const total = String(links.length);
  return { position, total, text: `${position} / ${total}` };
}

/**
 * Which stage a docs section belongs to: the first segment of the page's route id, as
 * docs/publish.json sets it, against the public ledger's program line. The stage numbers are
 * CONTRIBUTING.md's (stage 1 is the substrate, stage 2 the cognitive-map line) and are fixed here,
 * as in tools/publish/og.py. pageChrome.test.ts fails when the manifest gains a section with no stage,
 * the START_SECTION apart: its pages are in no stage and no segment of its routes may be a stage's.
 */
export const STAGE_OF_SECTION = {
  substrate: { stage: 1, line: 'substrate' },
  research: { stage: 2, line: 'cognitive_map' },
} as const;

export type StageLineKey = (typeof STAGE_OF_SECTION)[keyof typeof STAGE_OF_SECTION]['line'];

export interface Day {
  iso: string;
  label: string;
}

export interface StageLine {
  stage: number;
  state: string;
  /** The day a paused stage was paused, or null. */
  since: Day | null;
  /** "Stage 2 · active", or "Stage 1 · paused since" and the day. */
  text: string;
}

/** The first segment of a route id: 'research/gates' is 'research', 'research' is 'research'. */
export function sectionOfRoute(id: string): string {
  return id.replace(/^\/+/, '').split('/')[0] ?? '';
}

/**
 * The stage status of a page, or null when it is not a page of stage 1 or stage 2. It states a state
 * and, for a paused stage, since when; it never judges. Everything but the stage number comes from
 * the ledger projection.
 */
export function stageLine(id: string, ledger: Pick<PublicLedger, 'program'>): StageLine | null {
  const key = sectionOfRoute(id);
  if (!Object.hasOwn(STAGE_OF_SECTION, key)) return null;
  const { stage, line } = STAGE_OF_SECTION[key as keyof typeof STAGE_OF_SECTION];
  const program: ProgramLine | undefined = ledger.program[line];
  if (!program || typeof program.state !== 'string' || !program.state) return null;
  const state = program.state;
  const since = state === 'paused' && program.since ? { iso: program.since, label: formatDay(program.since) } : null;
  return { stage, state, since, text: `Stage ${stage} · ${state}${since ? ` since ${since.label}` : ''}` };
}

export interface Strip {
  start: {
    /** What comes first: "Stage 1", "Error", or the sidebar's number for the group ("01"). */
    tag: string;
    /** The section's name, or what the error is. */
    name: string;
    /** The tag is only the sidebar's number: drawn, but not read out. */
    decorative: boolean;
  };
  /** The state of the page's stage, or a short word; null when the page has none. */
  end: { state: string | null; since: Day | null; text: string } | null;
}

/**
 * The strip above a page title. A page of a stage opens with the stage and its section ("Stage 1
 * Substrate") and ends with the stage's state from the ledger; the sidebar's own group number is left
 * off there, because it is a different number and the two would be read as one. A page outside any
 * stage opens with the sidebar's number and name for its group ("01 Start here"). The 404 page says
 * what it is.
 */
export function titleStrip(
  id: string,
  sidebar: readonly SidebarItem[],
  ledger: Pick<PublicLedger, 'program'>,
): Strip | null {
  if (id === NOT_FOUND.route) {
    return { start: { tag: 'Error', name: '404', decorative: false }, end: { state: null, since: null, text: 'Not filed' } };
  }
  const section = sectionOf(sidebar);
  const stage = stageLine(id, ledger);
  if (stage) {
    return {
      start: { tag: `Stage ${stage.stage}`, name: section?.name ?? '', decorative: false },
      end: { state: stage.state, since: stage.since, text: stage.since ? `${stage.state} since ${stage.since.label}` : stage.state },
    };
  }
  if (section) return { start: { tag: section.index, name: section.name, decorative: true }, end: null };
  return null;
}

/** The date for the footer: the commit time (ISO 8601) as a day, or null when there is none. */
export function footerDate(lastmod: string | undefined): Day | null {
  if (!lastmod) return null;
  const t = Date.parse(lastmod);
  if (Number.isNaN(t)) return null;
  const iso = new Date(t).toISOString().slice(0, 10);
  return { iso, label: formatDay(iso) };
}

/**
 * The gate the research line is waiting on, from the public plan as it stood when the plan was
 * written (`as_of`), the same reading the roadmap page renders on the server: the gate's letter and its
 * date, or its letter and "decision pending" once its date has passed with no decision recorded. Null
 * when the line has stopped or the plan has no dated gate left.
 */
export function nextGateText(plan: Plan): string | null {
  const gate = nextGate(plan, plan.as_of);
  if (!gate || !gate.date) return null;
  return `Gate ${gate.id}, ${gate.pending ? 'decision pending' : formatDay(gate.date)}`;
}

export interface BlockCell {
  label: string;
  text: string;
  /** A second, quieter figure beside the text: the sheet number. */
  note?: string;
  /**
   * The next gate's letter and date and the plan's time zone, for the footer's script, which reads the
   * gate against the reader's day as the roadmap does (lib/gateClock.ts): the page is built without a
   * clock, so the text is the plan's reading as of its `as_of`, and once the gate's date has passed with
   * no decision the script says "decision pending".
   */
  clock?: { gate: string; date: string; tz: string };
}

/** A day in words ("15 November 2026") kept on one line: a cell breaks before or after it, never inside. */
export function keepDays(text: string): string {
  return text.replace(/\b(\d{1,2}) ([A-Z][a-z]+) (\d{4})\b/g, '$1\u00a0$2\u00a0$3');
}

/**
 * The cells of the title block at the foot of a page: the sheet (the page's title and its number among
 * the sidebar's pages), the stage it belongs to and its state, and, on a page of stage 2, the next
 * gate. A cell is left out when its data is absent: the landing page and the 404 page are not sheets,
 * and a page outside a stage has no stage.
 */
export function titleBlock(input: {
  id: string;
  title: string;
  sidebar: readonly SidebarItem[];
  ledger: Pick<PublicLedger, 'program'>;
  plan: Plan;
}): BlockCell[] {
  const { id, title, sidebar, ledger, plan } = input;
  const cells: BlockCell[] = [];
  if (id !== '' && id !== NOT_FOUND.route) {
    const sheet = sheetOf(sidebar);
    if (sheet && title) cells.push({ label: 'Sheet', text: title, note: sheet.text });
  }
  const stage = stageLine(id, ledger);
  if (stage) {
    cells.push({ label: 'Stage', text: keepDays(`${stage.stage} · ${stage.since ? `${stage.state} since ${stage.since.label}` : stage.state}`) });
    const key = sectionOfRoute(id) as keyof typeof STAGE_OF_SECTION;
    if (STAGE_OF_SECTION[key].line === 'cognitive_map') {
      const next = nextGateText(plan);
      const gate = nextGate(plan, plan.as_of);
      if (next && gate?.date) {
        cells.push({ label: 'Next gate', text: keepDays(next), clock: { gate: gate.id, date: gate.date, tz: plan.timezone } });
      }
    }
  }
  return cells;
}

export interface FooterLink {
  text: string;
  href: string;
}

/**
 * The footer's links, in the order they are shown. Each says what it does, not the name of the file it
 * opens. The files are the repository's own: the licence, the citation file (which GitHub offers as
 * "Cite this repository"), the security policy (how to report a vulnerability). The discussions are
 * where questions go.
 */
export function footerLinks(repo: string = REPO_URL): FooterLink[] {
  return [
    { text: 'MIT licence', href: `${repo}/blob/main/LICENSE` },
    { text: 'Source code', href: repo },
    { text: 'Discussions', href: `${repo}/discussions` },
    { text: 'Cite this repository', href: `${repo}/blob/main/CITATION.cff` },
    { text: 'Report a vulnerability', href: `${repo}/blob/main/SECURITY.md` },
  ];
}
