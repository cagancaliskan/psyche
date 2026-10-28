import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { brickRow, brickRows, keyOf, substrateReadout } from './status.ts';
import type { PublicLedger } from './ledger.ts';

const REPO = new URL('../../../', import.meta.url);
const ledger = JSON.parse(readFileSync(new URL('tools/ledger.json', REPO), 'utf8'));

const led = {
  tests: { suites: 26, assertions: 2645, failures: 0, captured_at: '2026-10-24 18:09:23 +0300', captured_python: '3.14.4' },
  determinism: { interpreters: ['3.10', '3.11', '3.12'], hash_seeds: [0, 1, 42] },
} as unknown as PublicLedger;

test('the readout is the projection\'s figures, with the full lists as details', () => {
  assert.deepEqual(substrateReadout(led), [
    { label: 'Suites', value: 26 },
    { label: 'Assertions', value: 2645 },
    { label: 'Failures', value: 0 },
    { label: 'CPython versions', value: 3, detail: '3.10, 3.11, 3.12' },
    { label: 'Hash seeds', value: 3, detail: '0, 1, 42' },
  ]);
});

test('a build status gives a build cell and no meaning verdict, and public text says verified', () => {
  const v = brickRow({ id: '0a', name: 'substrate store', status: 'PROVEN' });
  assert.deepEqual(v.build, { state: 'verified', label: 'Verified' });
  assert.deepEqual(v.meaning, { state: 'not-earned', label: 'Not earned' });
  assert.equal(v.status, 'PROVEN', 'the ledger name is kept as it is there');
  assert.deepEqual(brickRow({ id: '2c', name: 'x', status: 'BUILT-UNVALIDATED' }).build, { state: 'built', label: 'Built' });
  assert.deepEqual(brickRow({ id: '2a', name: 'x', status: 'DESIGNED' }).build, { state: 'designed', label: 'Designed' });
  assert.deepEqual(brickRow({ id: 'h', name: 'x', status: 'HORIZON' }).build, { state: 'horizon', label: 'Horizon' });
});

test('a meaning verdict is a status of its own axis: no build cell, and never a build status', () => {
  for (const [status, label] of [['NO-GO', 'No-go'], ['NOT-YET', 'Not yet'], ['EARNED', 'Earned']] as const) {
    const r = brickRow({ id: 'x', name: 'x', status });
    assert.equal(r.build, null, `${status} has no build status in the projection`);
    assert.equal(r.meaning.label, label);
  }
});

test('the two axes stay apart: only a meaning-axis status ever changes the meaning cell', () => {
  for (const status of ['PROVEN', 'BUILT-UNVALIDATED', 'DESIGNED', 'HORIZON', 'FIXED-UNCOMMITTED']) {
    const r = brickRow({ id: 'x', name: 'x', status });
    assert.equal(r.meaning.state, 'not-earned', `${status} says nothing about meaning`);
    assert.notEqual(r.build, null);
  }
});

test('a status outside the known ones is shown as the ledger records it, not dropped', () => {
  const r = brickRow({ id: 'x', name: 'x', status: 'FIXED-UNCOMMITTED' });
  assert.deepEqual(r.build, { state: 'other', label: 'Fixed uncommitted' });
});

test('rows run verified, built, attempts, other states, designed, each in the ledger\'s own order', () => {
  const rows = brickRows([
    { id: 'a', name: 'a', status: 'DESIGNED' },
    { id: 'b', name: 'b', status: 'PROVEN' },
    { id: 'c', name: 'c', status: 'NO-GO' },
    { id: 'd', name: 'd', status: 'BUILT-UNVALIDATED' },
    { id: 'e', name: 'e', status: 'FIXED-UNCOMMITTED' },
    { id: 'f', name: 'f', status: 'PROVEN' },
    { id: 'g', name: 'g', status: 'DESIGNED' },
  ]);
  assert.deepEqual(rows.map((r) => r.id), ['b', 'f', 'd', 'c', 'e', 'a', 'g']);
});

test('every brick of the real ledger has a row, and the counts of each axis add up', () => {
  const bricks = Object.entries<{ name: string; status: string }>(ledger.bricks).map(([id, b]) => ({ id, name: b.name, status: b.status }));
  const rows = brickRows(bricks);
  assert.equal(rows.length, bricks.length);
  assert.deepEqual(new Set(rows.map((r) => r.id)), new Set(bricks.map((b) => b.id)));
  const build = keyOf(rows.map((r) => r.build));
  const meaning = keyOf(rows.map((r) => r.meaning));
  assert.equal(meaning.reduce((n, e) => n + e.count, 0), rows.length, 'every row has one meaning cell');
  assert.equal(build.reduce((n, e) => n + e.count, 0), rows.filter((r) => r.build !== null).length);
  for (const r of rows) assert.ok(r.build === null || r.build.state !== 'other', `${r.id}: ${r.status} is a status the page knows`);
});

test('the meaning column\'s wording holds only while the meaning bar is open and no brick has earned a verdict', () => {
  // The cell "Not earned" and the line under the table are true of a brick whose status is a build
  // status only as long as this holds. When it stops holding, the wording in components/BrickBoard.astro
  // and the "Not earned" cell in lib/status.ts have to be rewritten by a person, not left to pass.
  assert.equal(ledger.meaning_bar.status, 'OPEN');
  const earned = Object.values<{ status: string }>(ledger.bricks).filter((b) => b.status === 'EARNED');
  assert.equal(earned.length, 0);
});

test('a status the ledger accepts is either mapped here or deliberately shown as another state', () => {
  const mapped = new Set(['PROVEN', 'BUILT-UNVALIDATED', 'DESIGNED', 'HORIZON', 'NO-GO', 'NOT-YET', 'EARNED']);
  const unknown = (ledger.valid_statuses as string[]).filter((s) => !mapped.has(s));
  // These two are transient work states, shown as the ledger names them. A new one should be looked at.
  assert.deepEqual(unknown.sort(), ['FIXED-UNCOMMITTED', 'PRE-CHECK-GO-DECISION-OPEN']);
});

test('no label on the page says proven', () => {
  for (const status of ['PROVEN', 'BUILT-UNVALIDATED', 'DESIGNED', 'HORIZON', 'NO-GO', 'NOT-YET', 'EARNED']) {
    const r = brickRow({ id: 'x', name: 'x', status });
    assert.doesNotMatch(`${r.build?.label ?? ''} ${r.meaning.label}`, /proven/i);
  }
});
