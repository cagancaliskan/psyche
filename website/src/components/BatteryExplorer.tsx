import { useEffect, useRef, useState, type CSSProperties, type FocusEvent, type MouseEvent, type PointerEvent } from 'react';
import '@/styles/battery.css';
import { TestPicture, chainX, viewSize } from '@/components/battery/Pictures.tsx';
import { TESTS, splitSummary, type Test } from '@/lib/battery.ts';
import { cellRuler, pad2, pointRuler, type Ruler as RulerData } from '@/lib/sheet.ts';

// Catalog (21st.dev), rewritten in plain CSS and a few lines of React, without their libraries:
// the step rows follow the anatomy of "Stepper" by kevingirelli (an ordered list of steps, each
// complete, current or upcoming, the current one marked aria-current="step") and the numbered
// titles of "Vertical Titled Stepper" by sean0205; the index follows "Table of Contents" (one
// IntersectionObserver, one active entry) and the passed, current and ahead states of "Kokonut UI
// Scroll Index" by kokonutd; the sheet's corner marks follow "Corner Frame" by kevingirelli.

/** Time each step stays on screen while a sheet steps on its own. */
const STEP_MS = 3000;
const THRESHOLDS = Array.from({ length: 21 }, (_, i) => i / 20);
/** The header and the sticky index cover this much of the top of the viewport. */
const COVERED_PX = 124;
const IDS = TESTS.map((t) => t.id.toLowerCase());

interface Seen {
  /** The test most in view, as an anchor id (t1 to t5); null until one is. */
  current: string | null;
  /** The tests at least half in view, which may step on their own. */
  half: Record<string, boolean>;
}

/**
 * One observer for the whole page: it says which test is most in view (the index marks it) and
 * which are at least half in view, counted against the viewport below the header and the index
 * (a sheet steps on its own only while the reader can see most of it).
 */
function useSeen(): Seen {
  const [seen, setSeen] = useState<Seen>({ current: null, half: {} });
  useEffect(() => {
    if (!('IntersectionObserver' in window)) return;
    const height = new Map<string, number>();
    const half: Record<string, boolean> = {};
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const id = (entry.target as HTMLElement).id;
          const shown = entry.isIntersecting ? entry.intersectionRect.height : 0;
          const viewport = entry.rootBounds?.height ?? window.innerHeight;
          height.set(id, shown);
          half[id] = shown > 0 && shown >= 0.5 * Math.min(entry.boundingClientRect.height, viewport);
        }
        let current: string | null = null;
        let most = 0;
        for (const id of IDS) {
          const shown = height.get(id) ?? 0;
          if (shown > most) {
            most = shown;
            current = id;
          }
        }
        setSeen((before) =>
          before.current === current && IDS.every((id) => !!before.half[id] === !!half[id]) ? before : { current, half: { ...half } },
        );
      },
      { rootMargin: `-${COVERED_PX}px 0px 0px 0px`, threshold: THRESHOLDS },
    );
    for (const id of IDS) {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, []);
  return seen;
}

/**
 * The battery: a ruled index of the five tests, then one drawing sheet per test with its picture,
 * its question and its steps. A sheet in view steps through its pictures on its own unless the
 * reader prefers reduced motion; hovering pauses it, and any click or keyboard focus inside it
 * stops it until Play is pressed. The step text is announced only while the reader is in control.
 */
export default function BatteryExplorer() {
  const { current, half } = useSeen();
  const at = current ? IDS.indexOf(current) : -1;
  return (
    <div className="sx-bt">
      <nav className="sx-bi" aria-label="Tests in the battery">
        <ol role="list">
          {TESTS.map((t, i) => {
            const state = at < 0 ? 'idle' : i < at ? 'passed' : i === at ? 'current' : 'ahead';
            return (
              <li key={t.id} data-state={state}>
                <a href={`#${t.id.toLowerCase()}`} aria-current={state === 'current' ? 'location' : undefined}>
                  <span className="sx-bi__id">{t.id}</span> <span className="sx-bi__name">{t.name}</span>
                </a>
              </li>
            );
          })}
        </ol>
      </nav>
      <div className="sx-bt__stack">
        {TESTS.map((t) => (
          <Sheet key={t.id} test={t} inView={!!half[t.id.toLowerCase()]} />
        ))}
      </div>
    </div>
  );
}

/**
 * The toggle's two glyphs, drawn on a 24-unit grid as a 2-unit round stroke (the stroke width is
 * set to 1.5 where the button is styled). Decorative: the button's own text names it.
 */
const GLYPH = {
  width: 24,
  height: 24,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  focusable: 'false',
} as const;

function PauseGlyph() {
  return (
    <svg {...GLYPH}>
      <rect x="14" y="3" width="5" height="18" rx="1" />
      <rect x="5" y="3" width="5" height="18" rx="1" />
    </svg>
  );
}

function PlayGlyph() {
  return (
    <svg {...GLYPH}>
      <path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z" />
    </svg>
  );
}

/** Whether a step's picture shows the agent: its route, a goal it goes to, or the pair it is asked about. */
function showsAgent(step: Test['steps'][number]): boolean {
  return ('path' in step && !!step.path) || ('goal' in step && !!step.goal) || ('query' in step && !!step.query);
}

interface View {
  step: number;
  prev: number | null;
  animate: boolean;
}

function Ruler({ axis, ruler }: { axis: 'x' | 'y'; ruler: RulerData }) {
  const { len, major, minor } = ruler;
  const long = major.map((t) => (axis === 'x' ? `M${t.at} 0v1` : `M0 ${t.at}h1`)).join('');
  const short = minor.map((t) => (axis === 'x' ? `M${t} .55v.45` : `M.55 ${t}h.45`)).join('');
  return (
    <div className={axis === 'x' ? 'sx-bs__rx' : 'sx-bs__ry'}>
      {major
        .filter((t) => t.label)
        .map((t) => (
          <span key={t.at} style={{ '--p': (t.at * 100) / len } as CSSProperties}>
            {t.label}
          </span>
        ))}
      <svg className="sx-bs__ticks" viewBox={axis === 'x' ? `0 0 ${len} 1` : `0 0 1 ${len}`} preserveAspectRatio="none" focusable="false">
        <path className="minor" d={short} />
        <path d={long} />
      </svg>
    </div>
  );
}

function Sheet({ test, inView }: { test: Test; inView: boolean }) {
  const count = test.steps.length;
  const [view, setView] = useState<View>({ step: 0, prev: null, animate: false });
  // null until the browser says; the toggle is rendered meanwhile so the controls do not shift.
  const [motion, setMotion] = useState<boolean | null>(null);
  const [stopped, setStopped] = useState(false);
  const [hover, setHover] = useState(false);
  const [onToggle, setOnToggle] = useState(false);
  const toggle = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: no-preference)');
    const update = () => setMotion(query.matches);
    update();
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);

  const autoplay = motion === true && !stopped;
  const running = autoplay && inView && !(hover && !onToggle);

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => {
      setView((v) => ({ step: (v.step + 1) % count, prev: v.step, animate: true }));
    }, STEP_MS);
    return () => window.clearInterval(timer);
  }, [running, count]);

  const show = (i: number) => setView((v) => (v.step === i ? v : { step: i, prev: v.step, animate: true }));
  const fromToggle = (target: EventTarget | null) => !!toggle.current && target instanceof Node && toggle.current.contains(target);
  const onClick = (e: MouseEvent) => {
    if (!fromToggle(e.target)) setStopped(true);
  };
  const onFocus = (e: FocusEvent) => {
    if (!fromToggle(e.target)) setStopped(true);
  };
  const onPointerEnter = (e: PointerEvent) => {
    if (e.pointerType !== 'touch') setHover(true);
  };

  const current = test.steps[view.step];
  const id = test.id.toLowerCase();
  const [w, h] = viewSize(test);
  // The chain is one-dimensional: its ruler marks the nodes, and it has no second axis.
  const chain = test.kind === 'chain';
  const rx = test.kind === 'chain' ? pointRuler(w, test.nodes.map((_, i) => chainX(i))) : cellRuler(w);
  const { setup, ask } = splitSummary(test.summary);
  return (
    <article
      id={id}
      className="sx-bs"
      aria-labelledby={`${id}-name`}
      onClick={onClick}
      onFocus={onFocus}
      onPointerEnter={onPointerEnter}
      onPointerLeave={() => setHover(false)}
    >
      <header className="sx-bs__head">
        <h2 id={`${id}-name`}>
          <span className="sx-bs__id">{test.id}</span> <span className="sx-bs__name">{test.name}</span>
        </h2>
        <p className="sx-bs__paradigm">{test.paradigm}</p>
      </header>

      <figure className="sx-bs__fig">
        <div className="sx-bs__sheet" aria-hidden="true" data-pagefind-ignore="" data-kind={test.kind} data-animate={view.animate ? '' : undefined}>
          <i className="sx-bs__cm tl" />
          <i className="sx-bs__cm tr" />
          <i className="sx-bs__cm bl" />
          <i className="sx-bs__cm br" />
          <Ruler axis="x" ruler={rx} />
          {!chain && <Ruler axis="y" ruler={cellRuler(h)} />}
          <div className="sx-bs__plot">
            <TestPicture key={view.step} test={test} index={view.step} prev={view.prev} idPrefix={`sx-page-${id}`} decorative ruled />
          </div>
        </div>
        <figcaption>
          <span className="sx-bs__fig-no">Fig. {test.id}</span> An illustration, not a result.
        </figcaption>
      </figure>

      <div className="sx-bs__body">
        {setup && <p className="sx-bs__setup">{setup}</p>}
        <p className="sx-bs__ask">
          <span className="sx-bs__lab">The question</span> {ask}
        </p>

        <ol className="sx-bs__steps" role="list" aria-label={`${test.name}: steps`}>
          {test.steps.map((s, i) => (
            <li key={s.label} data-state={i < view.step ? 'done' : i === view.step ? 'current' : 'next'} data-agent={showsAgent(s) ? '' : undefined}>
              <button type="button" aria-current={i === view.step ? 'step' : undefined} onClick={() => show(i)}>
                <span className="k" aria-hidden="true">
                  {pad2(i + 1)}
                </span>{' '}
                <span className="nm">{s.label}</span> <span className="tx">{s.caption}</span>
              </button>
            </li>
          ))}
        </ol>

        <div className="sx-bs__ctl">
          {motion !== false && (
            <button
              ref={toggle}
              type="button"
              className="sx-bs__toggle"
              title="Steps on its own while in view; choose a step to take over"
              onClick={() => setStopped((s) => !s)}
              onPointerEnter={() => setOnToggle(true)}
              onPointerLeave={() => setOnToggle(false)}
            >
              {stopped ? <PlayGlyph /> : <PauseGlyph />}
              <span>{stopped ? 'Play' : 'Pause'}</span>
              <span className="sr-only"> {test.id} steps</span>
            </button>
          )}
        </div>
        <p className="sr-only" aria-live={autoplay ? 'off' : 'polite'}>
          {current.caption}
        </p>
      </div>
    </article>
  );
}
