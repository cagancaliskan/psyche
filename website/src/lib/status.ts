/**
 * What the status page and the substrate overview show of the public ledger projection
 * (src/data/ledger.public.json, shape in ./ledger.ts): the five figures of the captured run, and
 * each brick on its two axes. Nothing here is computed from a document and nothing is typed: every
 * value is copied from the projection or counted from it.
 *
 * The two axes are the build axis (is the mechanism built and verified) and the meaning axis (does
 * it reproduce a cognitive effect, judged against external data). They are separate and never
 * collapsed (CONTRIBUTING rule 3). The ledger gives each brick one status, and a status is a name on
 * one axis or the other: PROVEN, BUILT-UNVALIDATED, DESIGNED and HORIZON are build statuses; EARNED,
 * NOT-YET and NO-GO are meaning verdicts, which the ledger carries as the status of a brick that is
 * only an attempt at a cognitive claim (docs/research/glossary.md, "Build axis" and "Meaning axis").
 *
 * So a brick whose status is a build status has no meaning verdict in the projection: it holds no
 * earned one, which is what an open meaning bar says, and its meaning cell reads "Not earned". A
 * brick whose status is a meaning verdict has no build status in the projection, and its build cell
 * says so. The projection holds no per-brick verdict besides that (the ledger's notes are not
 * projected), so the page never states one the ledger does not.
 *
 * PROVEN is the ledger's internal name. Public prose says "verified" (D-035).
 */
import type { PublicLedger } from './ledger.ts';

export interface ReadoutItem {
  label: string;
  value: number;
  detail?: string;
}

/** The five figures of the captured run, read from the projection, with the full lists as details. */
export function substrateReadout(led: PublicLedger): ReadoutItem[] {
  const t = led.tests;
  const { interpreters, hash_seeds } = led.determinism;
  return [
    { label: 'Suites', value: t.suites },
    { label: 'Assertions', value: t.assertions },
    { label: 'Failures', value: t.failures },
    { label: 'CPython versions', value: interpreters.length, detail: interpreters.join(', ') },
    { label: 'Hash seeds', value: hash_seeds.length, detail: hash_seeds.join(', ') },
  ];
}

export type BuildState = 'verified' | 'built' | 'designed' | 'horizon' | 'other';
export type MeaningState = 'earned' | 'not-yet' | 'no-go' | 'not-earned';

export interface Labelled<S extends string> {
  state: S;
  label: string;
}

/** The build statuses the ledger names, and the word a reader sees. */
const BUILD: Record<string, Labelled<Exclude<BuildState, 'other'>>> = {
  PROVEN: { state: 'verified', label: 'Verified' },
  'BUILT-UNVALIDATED': { state: 'built', label: 'Built' },
  DESIGNED: { state: 'designed', label: 'Designed' },
  HORIZON: { state: 'horizon', label: 'Horizon' },
};

/** The meaning verdicts the ledger names, which it carries as a brick's status. */
const MEANING: Record<string, Labelled<Exclude<MeaningState, 'not-earned'>>> = {
  EARNED: { state: 'earned', label: 'Earned' },
  'NOT-YET': { state: 'not-yet', label: 'Not yet' },
  'NO-GO': { state: 'no-go', label: 'No-go' },
};

export interface BrickRow {
  id: string;
  name: string;
  /** The ledger's own status name, kept as it is there. */
  status: string;
  /** Null when the ledger gives the brick a meaning verdict and no build status. */
  build: Labelled<BuildState> | null;
  meaning: Labelled<MeaningState>;
}

/** 'FIXED-UNCOMMITTED' becomes 'Fixed uncommitted': a status outside the four, as the ledger records it. */
function words(status: string): string {
  const s = status.toLowerCase().replace(/-/g, ' ');
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function brickRow(b: { id: string; name: string; status: string }): BrickRow {
  const verdict = MEANING[b.status];
  if (verdict) return { id: b.id, name: b.name, status: b.status, build: null, meaning: verdict };
  const build: Labelled<BuildState> = BUILD[b.status] ?? { state: 'other', label: words(b.status) };
  return { id: b.id, name: b.name, status: b.status, build, meaning: { state: 'not-earned', label: 'Not earned' } };
}

/**
 * Where a brick's row sits: verified, built, the attempts that carry a meaning verdict, any other
 * state, then designed. Within a place the ledger's own order holds.
 */
const PLACE = (r: BrickRow): number => {
  if (r.build === null) return 2;
  switch (r.build.state) {
    case 'verified':
      return 0;
    case 'built':
      return 1;
    case 'designed':
      return 4;
    default:
      return 3;
  }
};

export function brickRows(bricks: PublicLedger['bricks']): BrickRow[] {
  return bricks
    .map((b, i) => ({ r: brickRow(b), i }))
    .sort((a, b) => PLACE(a.r) - PLACE(b.r) || a.i - b.i)
    .map(({ r }) => r);
}

export interface KeyEntry<S extends string> {
  state: S;
  label: string;
  count: number;
}

/** How many bricks sit in each state of one axis, in the order the rows show them. */
export function keyOf<S extends string>(pairs: (Labelled<S> | null)[]): KeyEntry<S>[] {
  const out: KeyEntry<S>[] = [];
  for (const p of pairs) {
    if (p === null) continue;
    const hit = out.find((e) => e.state === p.state && e.label === p.label);
    if (hit) hit.count += 1;
    else out.push({ state: p.state, label: p.label, count: 1 });
  }
  return out;
}
