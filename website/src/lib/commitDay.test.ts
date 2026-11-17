import { test } from 'node:test';
import assert from 'node:assert/strict';
import { commitDay } from './commitDay.ts';

test('the day of a commit is its date in UTC, in figures and in words, or nothing', () => {
  assert.deepEqual(commitDay('2026-03-05T08:30:00.000Z'), { iso: '2026-03-05', label: '5 March 2026' });
  assert.deepEqual(commitDay('2026-10-23T23:30:00.000Z'), { iso: '2026-10-23', label: '23 October 2026' });
  assert.deepEqual(commitDay('2026-10-24T00:30:00+02:00'), { iso: '2026-10-23', label: '23 October 2026' });
  assert.equal(commitDay(undefined), null);
  assert.equal(commitDay(''), null);
  assert.equal(commitDay('not a date'), null);
});
