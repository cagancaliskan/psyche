// The two packages scripts/check-a11y.mjs runs are pinned in one place: scripts/a11y-tools/package.json,
// which the script reads its versions from, with the lockfile `npm ci` installs from. The manifest must
// name exact versions, and the lockfile must hold both packages at those versions and every package in
// it with a hash, so a release of one of their own dependencies cannot change what the check does.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');
const script = read('./check-a11y.mjs');
const manifest = JSON.parse(read('./a11y-tools/package.json'));
const lock = JSON.parse(read('./a11y-tools/package-lock.json'));
const tools = manifest.dependencies ?? {};

test('the manifest names the two packages, each at an exact version', () => {
  assert.deepEqual(Object.keys(tools).sort(), ['axe-core', 'puppeteer-core']);
  for (const v of Object.values(tools)) assert.match(v, /^\d+\.\d+\.\d+$/, 'an exact version, not a range');
});

test('the script reads its versions from that manifest and types none of its own', () => {
  assert.match(script, /const LOCKED = fileURLToPath\(new URL\('\.\/a11y-tools\/', import\.meta\.url\)\);/);
  assert.match(script, /const TOOLS = JSON\.parse\(readFileSync\(join\(LOCKED, 'package\.json'\), 'utf8'\)\)\.dependencies/);
  assert.doesNotMatch(script, /['"`]\d+\.\d+\.\d+['"`]/, 'a version typed into the script would drift from the manifest');
});

test('the lockfile holds both packages at the manifest versions, and every package in it has a hash', () => {
  assert.deepEqual(lock.packages[''].dependencies, tools);
  for (const [name, version] of Object.entries(tools)) assert.equal(lock.packages[`node_modules/${name}`]?.version, version);
  for (const [path, entry] of Object.entries(lock.packages)) {
    if (path === '') continue;
    assert.match(entry.integrity ?? '', /^sha(256|384|512)-/, `${path} has no integrity hash`);
  }
});

test('a setup that cannot be done is a different exit code from a violation', () => {
  assert.match(script, /process\.exitCode = 2/);
  assert.match(script, /class SetupError/);
});
