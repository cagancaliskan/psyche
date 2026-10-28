// The two packages scripts/check-a11y.mjs runs are pinned in two places: TOOLS in the script, and
// scripts/a11y-tools/package.json with its lockfile, which `npm ci` installs from. They must say the same,
// and the lockfile must hold both with a hash, so a release of one of their own dependencies cannot
// change what the check does.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');
const script = read('./check-a11y.mjs');
const tools = Object.fromEntries([...script.match(/const TOOLS = \{([^}]*)\}/)[1].matchAll(/'([^']+)':\s*'([^']+)'/g)].map((m) => [m[1], m[2]]));
const manifest = JSON.parse(read('./a11y-tools/package.json'));
const lock = JSON.parse(read('./a11y-tools/package-lock.json'));

test('the script names the same two packages at the same exact versions as the locked manifest', () => {
  assert.deepEqual(Object.keys(tools).sort(), ['axe-core', 'puppeteer-core']);
  assert.deepEqual(manifest.dependencies, tools);
  for (const v of Object.values(tools)) assert.match(v, /^\d+\.\d+\.\d+$/, 'an exact version, not a range');
});

test('the lockfile holds both packages at those versions, and every package in it has a hash', () => {
  for (const [name, version] of Object.entries(tools)) assert.equal(lock.packages[`node_modules/${name}`]?.version, version);
  assert.deepEqual(lock.packages[''].dependencies, tools);
  for (const [path, entry] of Object.entries(lock.packages)) {
    if (path === '') continue;
    assert.match(entry.integrity ?? '', /^sha(256|384|512)-/, `${path} has no integrity hash`);
  }
});

test('a setup that cannot be done is a different exit code from a violation', () => {
  assert.match(script, /process\.exitCode = 2/);
  assert.match(script, /class SetupError/);
});
