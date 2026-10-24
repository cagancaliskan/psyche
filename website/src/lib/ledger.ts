/**
 * Shape of the public ledger projection (tools/publish/core.py ledger_public, staged as
 * src/data/ledger.public.json). Pages cast the staged JSON to this type, so the type check
 * reads the projection's contract rather than whatever copy happens to be staged.
 *
 * Every value is copied from tools/ledger.json; nothing here is computed.
 */

/** Program state of one research line: which line is worked on, never what is true of a brick. */
export interface ProgramLine {
  state: string;
  since: string;
  decision: string;
}

export interface PublicLedger {
  /** The whole project's long-term aim, stated as an aim (D-033). */
  aim: string;
  tests: {
    suites: number;
    assertions: number;
    failures: number;
    captured_at: string;
    captured_python: string;
  };
  determinism: { interpreters: string[]; hash_seeds: number[] };
  bricks: { id: string; name: string; status: string }[];
  meaning_bar: { status: string };
  program: {
    /** Stage 1, the substrate. */
    substrate: ProgramLine;
    /** Stage 2, spiking cognitive maps. */
    cognitive_map: ProgramLine;
  };
}

/** A lowercase state word as a label: 'paused' becomes 'Paused'. */
export function stateLabel(state: string): string {
  return state.charAt(0).toUpperCase() + state.slice(1);
}
