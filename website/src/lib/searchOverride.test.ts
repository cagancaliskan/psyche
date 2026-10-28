import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

// components/chrome/Search.astro is Starlight's Search component with three small edits (see the
// comment at its top). This test applies the same edits to the Starlight file that is installed and
// requires the result to be the override, so an upgrade that changes the original cannot pass
// unnoticed: the override would go on shipping the old search.
const upstreamPath = createRequire(import.meta.url).resolve('@astrojs/starlight/components/Search.astro');
const upstream = readFileSync(upstreamPath, 'utf8');
const ours = readFileSync(new URL('../components/chrome/Search.astro', import.meta.url), 'utf8');

const EDITS: Array<[string, string]> = [
  [
    `import Icon from '../user-components/Icon.astro';`,
    `import { Icon } from '@astrojs/starlight/components';`,
  ],
  [
    `<kbd class="sl-hidden md:sl-flex" style="display: none;">
			<kbd>{Astro.locals.t('search.ctrlKey')}</kbd><kbd>K</kbd>
		</kbd>`,
    `<kbd class="sl-hidden md:sl-flex" style="display: none;" aria-hidden="true">
			<kbd data-key={Astro.locals.t('search.ctrlKey')}></kbd><kbd data-key="K"></kbd>
		</kbd>`,
  ],
  [`platformKey.textContent = '⌘';`, `platformKey.dataset.key = '⌘';`],
];

// The override opens with a block of // comment lines inside its front matter; the original does not.
const withoutHeader = (text: string) => text.replace(/^---\n(?:\/\/[^\n]*\n)+/, '---\n');

test('the Search override is the installed Starlight Search component with the three edits', () => {
  let expected = upstream;
  for (const [from, to] of EDITS) {
    assert.equal(
      expected.split(from).length - 1,
      1,
      `Starlight's Search.astro no longer contains (exactly once):\n${from}\ncopy the new file to src/components/chrome/Search.astro and make the edits again`,
    );
    expected = expected.replace(from, () => to);
  }
  assert.equal(
    withoutHeader(ours),
    expected,
    "src/components/chrome/Search.astro differs from Starlight's Search.astro with the edits applied: copy the installed file and make the edits again",
  );
});

test('the key cap holds no text, so the button name holds the visible text', () => {
  assert.ok(ours.includes(`aria-label={Astro.locals.t('search.label')}`), 'the button keeps its aria-label');
  assert.ok(ours.includes('aria-keyshortcuts'), 'the button keeps aria-keyshortcuts');
  assert.ok(
    ours.includes(`<kbd class="sl-hidden md:sl-flex" style="display: none;" aria-hidden="true">`),
    'the key cap is hidden from assistive technology',
  );
  assert.ok(
    ours.includes(`<kbd data-key={Astro.locals.t('search.ctrlKey')}></kbd><kbd data-key="K"></kbd>`),
    'each key is an empty element drawn from its data-key',
  );
  assert.ok(!/textContent\s*=\s*'⌘'/.test(ours), 'the Apple-device script does not write text into the cap');
});
