// Client behaviour shared by the site's cards and figures, loaded once per page however many
// components import it:
// - the spotlight: any element with data-spot gets the pointer position as --sx-spot-x and
//   --sx-spot-y (one delegated listener, at most one write per frame; touch is skipped);
// - the beam pass: a figure with data-sx-beams gets data-run once, when most of it is in view,
//   so its connectors carry one light pulse; the attribute is removed when the last pulse ends,
//   so hovering can play it again. With reduced motion nothing here runs except the spotlight,
//   whose light does not move on its own.

type Flagged = Window & { __sxMotion?: boolean };

function spotlight() {
  let frame = 0;
  let target: HTMLElement | null = null;
  let x = 0;
  let y = 0;
  document.addEventListener(
    'pointermove',
    (event) => {
      if (event.pointerType === 'touch') return;
      const el = event.target instanceof Element ? event.target.closest<HTMLElement>('[data-spot]') : null;
      if (!el) return;
      target = el;
      x = event.clientX;
      y = event.clientY;
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        if (!target) return;
        const box = target.getBoundingClientRect();
        target.style.setProperty('--sx-spot-x', `${x - box.left}px`);
        target.style.setProperty('--sx-spot-y', `${y - box.top}px`);
      });
    },
    { passive: true },
  );
}

function beams() {
  if (!('IntersectionObserver' in window)) return;
  if (!matchMedia('(prefers-reduced-motion: no-preference)').matches) return;
  const figures = document.querySelectorAll<HTMLElement>('[data-sx-beams]');
  if (figures.length === 0) return;
  const seen = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const figure = entry.target as HTMLElement;
        seen.unobserve(figure);
        figure.setAttribute('data-run', '');
        const pulses = figure.querySelectorAll('.sx-beam__pulse, .sx-rail__pulse');
        const last = pulses[pulses.length - 1];
        if (!last) continue;
        last.addEventListener('animationend', () => figure.removeAttribute('data-run'), { once: true });
      }
    },
    { threshold: 0.5 },
  );
  for (const figure of figures) seen.observe(figure);
}

const w = window as Flagged;
if (!w.__sxMotion) {
  w.__sxMotion = true;
  spotlight();
  beams();
}
