// A screenshot of one HTML page at an exact size, taken with the Chrome or Chromium already on the
// machine (no package is installed). Shared by make-icons.mjs and make-og.mjs.
//
//   findChrome()                     --chrome PATH or CHROME_PATH, else the usual places
//   shoot({ html, width, height })   the PNG bytes of a width x height viewport, or a thrown error
//
// The page is written to a private directory made by mkdtempSync (owner only, a name nobody can
// guess) together with Chrome's own profile, and the directory is removed afterwards, so nothing
// is left behind and no other user of the machine can place a file Chrome would read. `transparent`
// leaves the page background clear: only what the page paints is opaque. Chrome starts and exits
// within the call; nothing keeps running.
import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { delimiter, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const PNG_MAGIC = '89504e470d0a1a0a';

export function findChrome(given = process.env.CHROME_PATH) {
  if (given) {
    if (!existsSync(given)) throw new Error(`the Chrome given (${given}) does not exist`);
    return given;
  }
  for (const p of [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
  ]) {
    if (existsSync(p)) return p;
  }
  for (const name of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
    for (const dir of (process.env.PATH || '').split(delimiter)) {
      const p = join(dir, name);
      if (dir && existsSync(p)) return p;
    }
  }
  throw new Error('no Chrome or Chromium found; pass --chrome PATH or set CHROME_PATH');
}

/** Width and height from a PNG's header, or null when the bytes are not a PNG. */
export function pngSize(buf) {
  if (buf.length < 24 || buf.subarray(0, 8).toString('hex') !== PNG_MAGIC) return null;
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

export function shoot({ html, width, height, transparent = false, chrome = findChrome() }) {
  const dir = mkdtempSync(join(tmpdir(), 'psyche-shot-'));
  try {
    const page = join(dir, 'page.html');
    const out = join(dir, 'out.png');
    writeFileSync(page, html, { mode: 0o600 });
    try {
      execFileSync(
        chrome,
        [
          '--headless=new',
          '--disable-gpu',
          '--hide-scrollbars',
          '--no-first-run',
          '--no-default-browser-check',
          `--user-data-dir=${join(dir, 'profile')}`,
          '--force-device-scale-factor=1',
          '--force-color-profile=srgb',
          `--default-background-color=${transparent ? '00000000' : 'ffffffff'}`,
          `--window-size=${width},${height}`,
          '--virtual-time-budget=10000',
          `--screenshot=${out}`,
          pathToFileURL(page).href,
        ],
        { stdio: 'ignore', timeout: 60000 },
      );
    } catch (e) {
      throw new Error(`Chrome failed to take the screenshot (${chrome}): ${e.message}`);
    }
    const png = readFileSync(out);
    const size = pngSize(png);
    if (!size || size.width !== width || size.height !== height) {
      throw new Error(`the screenshot is ${size ? `${size.width} x ${size.height}` : 'not a PNG'}, not ${width} x ${height}`);
    }
    return png;
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}
