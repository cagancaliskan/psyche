import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  FEED_FILE,
  FEED_MEDIA_TYPE,
  FEED_TITLE,
  PROGRESS_PAGE,
  STAMP_TIME,
  TAG_YEAR,
  atomFeed,
  escapeXml,
  feedDay,
  stamp,
  tagId,
  type ProgressData,
  type ProgressEvent,
} from './feed.ts';

const SITE = 'https://example.org/psyche/';

const event = (over: Partial<ProgressEvent> = {}): ProgressEvent => ({
  id: 'phase-started/P0',
  kind: 'phase-started',
  date: '2026-10-23',
  item: 'P0',
  subject: 'Phase P0, Novelty review and setup',
  headline: 'Phase P0 started',
  change: 'started',
  ...over,
});

// The shape tools/publish/render_plan.py progress_events writes, newest first.
const EVENTS: ProgressEvent[] = [
  event({ id: 'gate-decided/A', kind: 'gate-decided', date: '2026-11-14', item: 'A', subject: 'Gate A, Novelty', headline: 'Gate A decided', change: 'decided; the line continues to the next phase' }),
  event({ id: 'change/2026-11-01/A/date/1', kind: 'change', date: '2026-11-01', item: 'A', subject: 'Gate A, Novelty', headline: 'Gate A date changed', change: 'date changed from 2026-11-15 to 2026-11-22 (reason: a fixture move)' }),
  event(),
];
const DATA: ProgressData = { as_of: '2026-11-14', timezone: 'Europe/Istanbul', author: 'Ada Example', events: EVENTS };

/** A strict-enough check that `xml` is well-formed: one root, matched tags, quoted attributes, no bare & or <. */
function malformed(xml: string): string | null {
  const entity = /&(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);/y;
  const checkText = (text: string, where: string): string | null => {
    for (let i = 0; i < text.length; i += 1) {
      if (text[i] === '<') return `a bare < in ${where}`;
      if (text[i] === '&') {
        entity.lastIndex = i;
        if (!entity.test(text)) return `a bare & in ${where}`;
      }
    }
    return null;
  };
  const rest = xml.replace(/^<\?xml [^>]*\?>\n?/, '');
  const stack: string[] = [];
  let seenRoot = false;
  let i = 0;
  while (i < rest.length) {
    if (rest[i] !== '<') {
      const end = rest.indexOf('<', i);
      const text = rest.slice(i, end === -1 ? rest.length : end);
      if (stack.length === 0 && text.trim()) return 'text outside the root';
      const bad = checkText(text, 'text');
      if (bad && !bad.startsWith('a bare <')) return bad;
      i = end === -1 ? rest.length : end;
      continue;
    }
    const m = /^<(\/)?([A-Za-z_][\w.:-]*)((?:\s+[A-Za-z_][\w.:-]*="[^"<]*")*)\s*(\/)?>/.exec(rest.slice(i));
    if (!m) return `a tag that does not parse at ${JSON.stringify(rest.slice(i, i + 40))}`;
    const [whole, closing, name, attrs, selfClosing] = m;
    const names = [...attrs.matchAll(/\s([A-Za-z_][\w.:-]*)="([^"]*)"/g)];
    if (new Set(names.map((a) => a[1])).size !== names.length) return `an attribute given twice on <${name}>`;
    for (const a of names) {
      const bad = checkText(a[2], `an attribute of <${name}>`);
      if (bad) return bad;
    }
    if (closing) {
      if (stack.pop() !== name) return `</${name}> closes the wrong element`;
    } else {
      if (stack.length === 0) {
        if (seenRoot) return 'a second root';
        seenRoot = true;
      }
      if (!selfClosing) stack.push(name);
    }
    i += whole.length;
  }
  if (stack.length) return `<${stack[stack.length - 1]}> is never closed`;
  return seenRoot ? null : 'no root';
}

test('the well-formedness check used here catches what it should', () => {
  assert.equal(malformed('<a x="1"><b/>t &amp; u</a>'), null);
  assert.match(malformed('<a><b></a>') ?? '', /closes the wrong element/);
  assert.match(malformed('<a>fish & chips</a>') ?? '', /bare &/);
  assert.match(malformed('<a x=1/>') ?? '', /does not parse/);
  assert.match(malformed('<a x="1" x="2"/>') ?? '', /given twice/);
  assert.match(malformed('<a x="a<b"/>') ?? '', /does not parse/);
  assert.match(malformed('<a/><b/>') ?? '', /second root/);
  assert.match(malformed('<a>') ?? '', /never closed/);
  assert.match(malformed('text<a/>') ?? '', /outside the root/);
});

test('an event has a day and no time: it is stamped noon UTC, the same calendar day in nearly every zone', () => {
  assert.equal(stamp('2026-10-23'), '2026-10-23T12:00:00Z');
  assert.equal(STAMP_TIME, 'T12:00:00Z');
  // a leap day is a day; the 30th of February is not, and neither is a day written loosely
  assert.equal(stamp('2028-02-29'), '2028-02-29T12:00:00Z');
  for (const bad of ['2026-02-30', '2026-13-01', '2026-1-1', '20261023', '2026-10-23T00:00:00Z', '', 'today']) {
    assert.throws(() => stamp(bad), /not a calendar day/, bad);
  }
});

test('text is escaped for XML, and a character XML 1.0 forbids never reaches the output', () => {
  assert.equal(escapeXml(`<a href="x">Tom & 'Jerry'</a>`), '&lt;a href=&quot;x&quot;&gt;Tom &amp; &apos;Jerry&apos;&lt;/a&gt;');
  assert.equal(escapeXml('plain'), 'plain');
  // an escape is not escaped twice
  assert.equal(escapeXml('&amp;'), '&amp;amp;');
  const replacement = String.fromCharCode(0xfffd);
  const forbidden = [0x00, 0x01, 0x08, 0x0b, 0x0c, 0x0e, 0x1f, 0xfffe, 0xffff, 0xd800, 0xdfff].map((c) => String.fromCharCode(c));
  for (const ch of forbidden) assert.equal(escapeXml(`a${ch}b`), `a${replacement}b`, `U+${ch.charCodeAt(0).toString(16)}`);
  // tab, line feed, carriage return, a letter outside Latin-1 and a character beyond the BMP are allowed
  const astral = String.fromCodePoint(0x1f600);
  assert.equal(escapeXml(`\t\n\r${String.fromCharCode(0xe9)}${astral}`), `\t\n\r${String.fromCharCode(0xe9)}${astral}`);
});

test('a tag URI names the host, the year the feed began in and the path below the base, and is the same on every build', () => {
  assert.equal(tagId(SITE, 'progress.xml'), `tag:example.org,${TAG_YEAR}:psyche/progress.xml`);
  assert.equal(tagId('https://example.org/', 'progress.xml'), `tag:example.org,${TAG_YEAR}:progress.xml`);
  assert.equal(tagId(SITE, 'progress/change/2026-11-01/A/date/1'), `tag:example.org,${TAG_YEAR}:psyche/progress/change/2026-11-01/A/date/1`);
  // the path is percent-encoded, so an id with a space cannot break the IRI
  assert.equal(tagId(SITE, 'a b'), `tag:example.org,${TAG_YEAR}:psyche/a%20b`);
  assert.match(TAG_YEAR, /^\d{4}$/);
  assert.equal(tagId(SITE, 'progress.xml'), tagId(SITE, 'progress.xml'));
});

test('the feed is dated by its newest event, in any order, and by the plan when there is none; never by the clock', () => {
  assert.equal(feedDay(DATA), '2026-11-14');
  assert.equal(feedDay({ ...DATA, events: [...EVENTS].reverse() }), '2026-11-14');
  assert.equal(feedDay({ as_of: '2026-10-23', events: [] }), '2026-10-23');
  const source = readFileSync(new URL('./feed.ts', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /Date\.now\(|new Date\(\)|performance\.now/, 'the feed reads no clock');
});

test('the feed is valid Atom 1.0 in shape: id, title, updated, self and alternate links, an author, and one entry for each event', () => {
  const xml = atomFeed(DATA, SITE);
  assert.equal(malformed(xml), null);
  assert.ok(xml.startsWith('<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">\n'));
  assert.ok(xml.endsWith('</feed>\n'));
  const head = xml.slice(0, xml.indexOf('<entry>'));
  assert.match(head, /<id>tag:example\.org,\d{4}:psyche\/progress\.xml<\/id>/);
  assert.ok(head.includes(`<title type="text">${FEED_TITLE}</title>`));
  assert.ok(head.includes('<updated>2026-11-14T12:00:00Z</updated>'), 'updated is the newest event, not the build');
  assert.ok(head.includes(`<link rel="self" type="${FEED_MEDIA_TYPE}" href="https://example.org/psyche/${FEED_FILE}"/>`));
  assert.ok(head.includes(`<link rel="alternate" type="text/html" href="https://example.org/psyche/${PROGRESS_PAGE}"/>`));
  assert.ok(head.includes('<author>\n    <name>Ada Example</name>\n  </author>'));

  const entries = xml.split('<entry>').slice(1);
  assert.equal(entries.length, EVENTS.length);
  const ids = new Set<string>();
  entries.forEach((entry, n) => {
    const e = EVENTS[n];
    const id = /<id>([^<]+)<\/id>/.exec(entry)?.[1] ?? '';
    assert.match(id, /^tag:example\.org,\d{4}:psyche\/progress\/[A-Za-z0-9\/_.-]+$/);
    assert.ok(id.endsWith(`/${e.id}`), `${id} ends with the event's id`);
    ids.add(id);
    assert.ok(entry.includes(`<title type="text">${e.headline}</title>`));
    assert.ok(entry.includes(`<updated>${e.date}T12:00:00Z</updated>`));
    assert.ok(entry.includes(`<link rel="alternate" type="text/html" href="https://example.org/psyche/progress/"/>`));
    assert.ok(entry.includes(`<summary type="text">${e.subject}: ${e.change}.</summary>`));
  });
  assert.equal(ids.size, EVENTS.length, 'every entry has an id of its own');
});

test('the same data gives the same bytes, an entry keeps its id when another event is added, and the order given is kept', () => {
  assert.equal(atomFeed(DATA, SITE), atomFeed(structuredClone(DATA), SITE));
  const idOf = (xml: string, event: string) => new RegExp(`<id>([^<]*/${event.replace(/\//g, '\\/')})</id>`).exec(xml)?.[1];
  const before = atomFeed(DATA, SITE);
  const later = event({ id: 'phase-started/P1', date: '2026-11-16', item: 'P1', headline: 'Phase P1 started' });
  const after = atomFeed({ ...DATA, events: [later, ...EVENTS] }, SITE);
  for (const e of EVENTS) assert.equal(idOf(after, e.id), idOf(before, e.id), e.id);
  assert.ok(after.indexOf('Phase P1 started') < after.indexOf('Gate A decided'), 'entries are written in the order given');
  assert.ok(after.includes('<updated>2026-11-16T12:00:00Z</updated>\n  <link rel="self"'), 'a newer event moves the feed forward');
});

test('text from the plan cannot break the markup', () => {
  const hostile = event({
    headline: `</title><script>alert(1)</script> & "q" ${String.fromCharCode(1)}`,
    subject: 'A <b>subject</b>',
    change: "fish & chips ' \"",
  });
  const xml = atomFeed({ ...DATA, author: 'A. <Author> & Co', events: [hostile] }, SITE);
  assert.equal(malformed(xml), null);
  assert.ok(!xml.includes('<script>') && !xml.includes(String.fromCharCode(1)));
  assert.ok(xml.includes('<name>A. &lt;Author&gt; &amp; Co</name>'));
});

test('a plan with no event gives a valid feed with no entry, dated by the plan', () => {
  const xml = atomFeed({ ...DATA, events: [] }, SITE);
  assert.equal(malformed(xml), null);
  assert.ok(!xml.includes('<entry>'));
  assert.ok(xml.includes('<updated>2026-11-14T12:00:00Z</updated>'));
});

test('addresses are absolute from the site address given, which must end in a slash', () => {
  const xml = atomFeed(DATA, 'https://cagancaliskan.github.io/psyche/');
  for (const href of [...xml.matchAll(/href="([^"]*)"/g)].map((m) => m[1])) assert.match(href, /^https:\/\/cagancaliskan\.github\.io\/psyche\//, href);
  assert.throws(() => atomFeed(DATA, 'https://example.org/psyche'), /closing slash|end in a slash/);
  assert.throws(() => atomFeed({ ...DATA, events: [event({ date: '2026-02-30' })] }, SITE), /not a calendar day/);
});
