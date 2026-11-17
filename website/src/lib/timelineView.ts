/**
 * The timeline page's behaviour in the browser (pages/roadmap.astro writes all the markup on the
 * server; this adds to it and writes no markup of its own). Nothing moves by itself: the picture changes
 * only when the reader chooses a phase or a gate, and then at once.
 *
 * - The day: the page is built as of the plan's as_of date. Here the reader's day (in the plan's time
 *   zone) moves what depends on it, with the functions the server used (lib/timeline.ts): every element
 *   with data-gate-ref says where that gate stands (data-gate-show="word", "word-lower" or "note"), the
 *   "Next gate" line gets its days left (data-now-days), and the today line is drawn over the time column
 *   with the word "Today" beside it.
 * - The drawing, the sentence above it and the reading are written hidden, since they work only with
 *   script; the tables under them say everything without it. A choice of a row (pointer, Enter or
 *   Space) marks it pressed, draws its marks in full ink and shows its reading; the up and down arrows,
 *   Home and End move between the rows. The reading keeps the height of its longest text, so a choice
 *   never moves the drawing under the pointer.
 */
import { todayIn, dayNumber, fraction } from './plan.ts';
import { daysWords, gateFromData, gateReadings } from './timeline.ts';

const SVG = 'http://www.w3.org/2000/svg';

function applyDay(root: HTMLElement, today: string): void {
  const gates = [...root.querySelectorAll<HTMLElement>('[data-gate-id]')].map((el) => gateFromData(el.dataset));
  const readings = gateReadings(gates, today);
  for (const el of root.querySelectorAll<HTMLElement>('[data-gate-ref]')) {
    const reading = readings.get(el.dataset.gateRef ?? '');
    if (!reading) continue;
    const show = el.dataset.gateShow;
    if (show === 'word') el.textContent = reading.word;
    else if (show === 'word-lower') el.textContent = reading.word.toLowerCase();
    else if (show === 'note') {
      const text = el.querySelector<HTMLElement>('[data-gate-text]') ?? el;
      text.textContent = reading.note ?? '';
      el.hidden = reading.note === null;
    }
  }
  for (const el of root.querySelectorAll<HTMLElement>('[data-now-days]')) el.textContent = daysWords(gates, today);
}

/** The today line over the time column, a short piece of it in every row (shown on a phone) and the word. */
function drawToday(draw: HTMLElement, today: string): void {
  const from = Number(draw.dataset.from);
  const to = Number(draw.dataset.to);
  const day = dayNumber(today);
  if (!Number.isFinite(from) || !Number.isFinite(to) || day < from || day > to) return;
  const f = fraction(day, { from, to });
  const at = `${(f * 100).toFixed(3)}%`;
  for (const svg of draw.querySelectorAll<SVGSVGElement>('svg.tl-time')) {
    const line = document.createElementNS(SVG, 'line');
    line.setAttribute('class', 'tl-today tl-today--row');
    line.setAttribute('x1', at);
    line.setAttribute('x2', at);
    line.setAttribute('y1', '0');
    line.setAttribute('y2', '100%');
    svg.insertBefore(line, svg.firstChild);
    const where = svg.dataset.tlToday;
    if (where !== 'row' && where !== 'axis') continue;
    // beside the line, to its right, or to its left near the end of the axis
    const left = f > 0.88;
    const word = document.createElementNS(SVG, 'text');
    word.setAttribute('class', where === 'axis' ? 'tl-today-word tl-today-word--axis' : 'tl-today-word');
    word.setAttribute('x', at);
    if (where === 'axis') word.setAttribute('y', '64');
    else {
      word.setAttribute('y', '100%');
      word.setAttribute('dy', '-8');
    }
    word.setAttribute('dx', left ? '-6' : '6');
    word.setAttribute('text-anchor', left ? 'end' : 'start');
    word.textContent = 'Today';
    svg.appendChild(word);
  }
  const rule = document.createElement('span');
  rule.className = 'tl-todayline';
  rule.setAttribute('aria-hidden', 'true');
  rule.style.left = `calc(var(--tl-name) + (100% - var(--tl-name)) * ${f.toFixed(5)})`;
  draw.insertBefore(rule, draw.firstChild);
}

function mountDrawing(root: HTMLElement): void {
  const draw = root.querySelector<HTMLElement>('[data-tl-draw]');
  const box = root.querySelector<HTMLElement>('[data-tl-readbox]');
  const hint = root.querySelector<HTMLElement>('[data-tl-hint]');
  if (!draw || !box) return;
  const lanes = [...draw.querySelectorAll<HTMLButtonElement>('.tl-lane[data-tl]')];
  const marks = [...draw.querySelectorAll<SVGElement>('[data-tl-for]')];
  const readings = [...box.querySelectorAll<HTMLElement>('[data-tl-reading]')];
  if (!lanes.length || !readings.length) return;

  // a gate tick runs the middle of its row, and the full height while chosen
  const tickEnds = (mark: SVGElement, on: boolean): [string, string] =>
    on ? ['0', '100%'] : mark.dataset.tlRow === 'gate' ? ['25%', '75%'] : ['30%', '70%'];

  function choose(id: string): void {
    for (const b of lanes) b.setAttribute('aria-pressed', b.dataset.tl === id ? 'true' : 'false');
    for (const mark of marks) {
      const on = mark.dataset.tlFor === id;
      mark.classList.toggle('is-sel', on);
      if (mark.dataset.tlRow) {
        const [y1, y2] = tickEnds(mark, on);
        mark.setAttribute('y1', y1);
        mark.setAttribute('y2', y2);
      }
    }
    for (const r of readings) r.hidden = r.dataset.tlReading !== id;
  }

  // the reading box keeps the height of the longest reading at this width
  let measuredAt = -1;
  function reserve(): void {
    const width = box!.clientWidth;
    if (!width || width === measuredAt) return;
    measuredAt = width;
    const shown = readings.filter((r) => !r.hidden);
    box!.style.minHeight = '';
    let high = 0;
    for (const r of readings) {
      for (const other of readings) other.hidden = other !== r;
      high = Math.max(high, box!.offsetHeight);
    }
    for (const r of readings) r.hidden = !shown.includes(r);
    box!.style.minHeight = `${high}px`;
  }

  draw.addEventListener('click', (e) => {
    const lane = (e.target as Element | null)?.closest?.<HTMLButtonElement>('.tl-lane[data-tl]');
    if (lane?.dataset.tl) choose(lane.dataset.tl);
  });
  draw.addEventListener('keydown', (e) => {
    const i = lanes.indexOf(document.activeElement as HTMLButtonElement);
    if (i < 0) return;
    const j = e.key === 'ArrowDown' ? i + 1 : e.key === 'ArrowUp' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? lanes.length - 1 : null;
    if (j === null) return;
    // at the first or the last row an arrow stays put; it does not scroll the page
    e.preventDefault();
    if (j >= 0 && j < lanes.length) lanes[j].focus();
  });

  draw.hidden = false;
  box.hidden = false;
  if (hint) hint.hidden = false;
  const first = lanes.find((b) => b.getAttribute('aria-pressed') === 'true') ?? lanes[0];
  choose(first.dataset.tl ?? '');
  reserve();
  addEventListener('resize', reserve);
  document.fonts?.ready.then(() => {
    measuredAt = -1;
    reserve();
  }, () => {});
}

export function mountTimeline(root: HTMLElement): void {
  let today: string | null = null;
  try {
    today = todayIn(root.dataset.tz ?? 'UTC', new Date());
  } catch {
    today = null;
  }
  if (today) applyDay(root, today);
  const draw = root.querySelector<HTMLElement>('[data-tl-draw]');
  if (today && draw) drawToday(draw, today);
  mountDrawing(root);
}
