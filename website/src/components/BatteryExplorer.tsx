import { useEffect, useRef, useState, type FocusEvent, type MouseEvent, type PointerEvent } from 'react';
import { Pause, Play } from 'lucide-react';
import '@/styles/battery.css';
import { TestPicture } from '@/components/battery/Pictures.tsx';
import { TESTS, type Test } from '@/lib/battery.ts';

/** Time each step stays on screen while a card steps on its own. */
const STEP_MS = 3000;
const THRESHOLDS = Array.from({ length: 11 }, (_, i) => i / 10);

/**
 * Five paradigm illustrations, one card each. A card in view steps through its pictures on its
 * own unless the reader prefers reduced motion; hovering pauses it, and any click or keyboard
 * focus inside it stops it until Play is pressed. The caption is announced only while the reader
 * is in control.
 */
export default function BatteryExplorer() {
  return (
    <div className="sx-test-stack not-content">
      {TESTS.map((t) => (
        <TestCard key={t.id} test={t} />
      ))}
    </div>
  );
}

interface View {
  step: number;
  prev: number | null;
  animate: boolean;
}

function TestCard({ test }: { test: Test }) {
  const count = test.steps.length;
  const [view, setView] = useState<View>({ step: 0, prev: null, animate: false });
  // null until the browser says; the toggle is rendered meanwhile so the step row does not shift.
  const [motion, setMotion] = useState<boolean | null>(null);
  const [stopped, setStopped] = useState(false);
  const [inView, setInView] = useState(false);
  const [hover, setHover] = useState(false);
  const [onToggle, setOnToggle] = useState(false);
  const card = useRef<HTMLElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: no-preference)');
    const update = () => setMotion(query.matches);
    update();
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);

  useEffect(() => {
    const el = card.current;
    if (!el || !('IntersectionObserver' in window)) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[entries.length - 1];
        const viewport = entry.rootBounds?.height ?? window.innerHeight;
        const needed = 0.5 * Math.min(entry.boundingClientRect.height, viewport);
        setInView(entry.isIntersecting && entry.intersectionRect.height >= needed);
      },
      { threshold: THRESHOLDS },
    );
    observer.observe(el);
    return () => observer.disconnect();
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
  const [w, h] = test.kind === 'chain' ? [2 + (test.nodes.length - 1) * 1.6, 3] : test.kind === 'grid' ? [test.steps[0].grid.cols, test.steps[0].grid.rows] : [test.grid.cols, test.grid.rows];
  return (
    <article
      ref={card}
      id={id}
      onClick={onClick}
      onFocus={onFocus}
      onPointerEnter={onPointerEnter}
      onPointerLeave={() => setHover(false)}
    >
      <div className="sx-test-text">
        <h2>
          <span className="sx-test-text__id">{test.id}</span> {test.name}
        </h2>
        <p className="sx-test-text__paradigm">{test.paradigm}</p>
        <p>{test.summary}</p>
      </div>
      <figure className="sx-test-fig" data-animate={view.animate ? '' : undefined}>
        <div className="sx-test-fig__frame" style={{ aspectRatio: `${Math.min(w / h, 2.2).toFixed(3)}` }}>
          <TestPicture key={view.step} test={test} index={view.step} prev={view.prev} idPrefix={`sx-page-${id}`} />
        </div>
        <div className="sx-test-controls">
          <ol className="sx-steps" aria-label={`${test.name}: steps`}>
            {test.steps.map((s, i) => (
              <li key={s.label} data-state={i < view.step ? 'done' : i === view.step ? 'current' : 'next'}>
                <button type="button" aria-pressed={i === view.step} onClick={() => show(i)}>
                  <span className="sx-steps__n" aria-hidden="true">
                    {i + 1}
                  </span>{' '}
                  {s.label}
                </button>
              </li>
            ))}
          </ol>
          {motion !== false && (
            <button
              ref={toggle}
              type="button"
              className="sx-test-toggle"
              onClick={() => setStopped((s) => !s)}
              onPointerEnter={() => setOnToggle(true)}
              onPointerLeave={() => setOnToggle(false)}
            >
              {stopped ? <Play aria-hidden="true" /> : <Pause aria-hidden="true" />}
              {stopped ? 'Play' : 'Pause'} <span className="sr-only">{test.id} steps</span>
            </button>
          )}
        </div>
        <figcaption aria-live={autoplay ? 'off' : 'polite'}>{current.caption}</figcaption>
      </figure>
    </article>
  );
}
