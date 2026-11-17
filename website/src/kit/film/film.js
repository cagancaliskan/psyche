// The film: three.js (the installed dependency) draws the shapes that the generator in gen.js builds.
// Imported from the page design. Written by the page import: do not edit here.
import GEN_SRC from './gen.js?raw';
const root = document.documentElement;
const goStatic = () => { root.classList.add('is-static'); };

const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const probe = document.createElement('canvas');
const hasGL = !!(probe.getContext('webgl2') || probe.getContext('webgl'));

if (reduced || !hasGL) {
  goStatic();
} else {
  import('three')
    .then((THREE) => run(THREE))
    .catch(() => goStatic());
}

/* ------------------------------------------------------------------ */
/* One world, one camera                                               */
/* ------------------------------------------------------------------ */
// Every shape is its own set of points with a fixed place, scale and turn in one nested world
// (Powers of Ten): the next shape already sits inside the current one, tiny, at the detail the
// camera is heading for, or the current one sits inside the next for a pull-back. The camera has
// one state (x, y, log-scale, roll) on one path through keys at the beats; a set is drawn relative
// to the camera in its own frame, and fades only by how large it is on screen.
const GEN = new Function(GEN_SRC + '\nreturn { orbCloud, buildSet, BRAIN_C, ORB_R, MARK_GEO };')();

const D = 10.26, TANH = Math.tan((17.5 * Math.PI) / 180); // every set is seen at rest from D, fov 35
const SQ = (t) => t * t * (3 - 2 * t);
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const R2 = (a, v) => [Math.cos(a) * v[0] - Math.sin(a) * v[1], Math.sin(a) * v[0] + Math.cos(a) * v[1]];
const add2 = (a, b) => [a[0] + b[0], a[1] + b[1]];
const sub2 = (a, b) => [a[0] - b[0], a[1] - b[1]];
const mul2 = (a, k) => [a[0] * k, a[1] * k];
const lerp = (a, b, t) => a + (b - a) * t;

// Sets, in world order. rot: [resting turn, idle sway, sway speed] (sway only while a set is held).
// fin/fout: apparent scale q (1 = as framed at its beat) over which it fades in as it grows from a
// detail, and out as it is magnified past usefulness. win: the stretch of the path a set belongs to;
// its edges always fall where the scale fade (or the frame) already hides it, so nothing pops.
const SPEC = [
  { name: 'brain', mode: 2, rot: [-0.55, 0.22, 0.17], fin: null, fout: [3.0, 8.0], win: [-1, 1.8] },
  { name: 'neurons', mode: 2, rot: [0, 0.18, 0.11], fin: [0.1, 0.3], fout: [6, 20], win: [1.2, 2.8] },
  { name: 'synapse', mode: 3, rot: [0.35, 0.3, 0.13], fin: [0.05, 0.12], fout: [2.2, 4.4], win: [2.2, 3.8], ap: 1.8 },
  { name: 'lattice', mode: 4, rot: [0, 0.06, 0.1], fin: [0.24, 0.5], finX: [0.08, 0.2], fout: [2.5, 6], win: [3.2, 4.8] },
  { name: 'spike', mode: 5, rot: [0, 0.05, 0.1], fin: [0.1, 0.35], fout: [7, 14], win: [4.2, 6.2], ap: 1.3 },
  { name: 'machine', mode: 6, rot: [-0.1, 0.1, 0.12], fin: [0.11, 0.25], fout: [2.5, 6], win: [5.2, 7.2] },
  { name: 'map', mode: 7, rot: [-0.1, 0.08, 0.09], fin: [0.03, 0.08], fout: [5, 11.5], win: [6.2, 99] },
  { name: 'mark', mode: 8, rot: [0, 0.06, 0.2], fin: null, fout: null, win: [7.2, 99], over: 1, mag: 0, kx: 0.16 },
];
// How each set sits in the next. 'in': the next is inside this one at pa, Z times smaller.
// 'out': this one is inside the next at pb, the next Z times larger. 'pan': same scale, pa meets pb.
// With directions given, the next set is turned so that the two directions line up.
const LINKS = [
  { a: 0, b: 1, kind: 'in', Z: 12, pa: 'out', pb: 'in' },                                   // the bright cell on the brain is the hero neuron
  { a: 1, b: 2, kind: 'in', Z: 28, pa: 'out', pb: 'in', lead: 0.6 },                                   // the terminal on its dendrite tip is the synapse
  { a: 2, b: 3, kind: 'in', Z: 4.5, pa: 'out', da: 'outDir', pb: 'in', db: 'dir' },        // the lattice runs in the bouton's stem
  { a: 3, b: 4, kind: 'out', Z: 11, pa: 'out', da: 'dir', pb: 'anchor', db: 'anchorDir' }, // and in the axon of the spiking cell
  { a: 4, b: 5, kind: 'pan', Z: 1, pa: 'end', da: 'endDir', pb: 'a0', db: 'a0Dir' },       // that axon runs on into the machine's input
  { a: 5, b: 6, kind: 'out', Z: 10, pa: 'core', pb: 'in' },                                 // the machine neuron is the route's first node
  { a: 6, b: 7, kind: 'out', Z: 30, pa: 'out', pb: 'in', dip: 0.75 },                                  // the network lies in the P's white stroke
];
// How each set is framed at its beat: f = the image point placed at sh (screen units: half the
// viewport height), at scale fit; desktop and portrait.
const FRAME = [
  { f: 'bbox', d: [0, 0.1], m: [0, 0.14], fd: 1, fm: 0.95 },
  { f: 'origin', d: [0.09, 0.07], m: [0, 0.1], fd: 1, fm: 1.0 },
  { f: 'origin', d: [0.06, 0.14], m: [0, 0.14], fd: 0.8, fm: 1.1 },
  { f: 'origin', d: [0.36, 0.2], m: [0.1, 0.2], fd: 1, fm: 0.8 },
  { f: 'bbox', d: [0.12, 0.06], m: [0.02, 0.12], fd: 1, fm: 0.62 },
  { f: 'origin', d: [0.45, 0.13], m: [0.05, 0.16], fd: 1, fm: 1.0 },
  { f: 'origin', d: [0, 0.24], m: [0, 0.2], fd: 1, fm: 0.85 },
  { f: 'origin', d: [0, 0.33], m: [0, 0.3], fd: 0.86, fm: 0.95 },
];
// Beat holds on the path (b): brain 1.0-1.2, then each beat k at k-0.2 .. k+0.2, the mark at 8.
const HOLD = [[1.0, 1.2], [1.8, 2.2], [2.8, 3.2], [3.8, 4.2], [4.8, 5.2], [5.8, 6.2], [6.8, 7.2], [8.0, 8.0]];
const PUSH = 0.035; // a slow push during each hold (log-scale)
// Scroll: weight of each stretch of the path (holds and moves). The page ends just past the point
// where the mark has formed; from there a short timer finishes it.
const B_END = 7.62;  // the page ends just past the finish threshold (bT)
const B_T = 7.54;     // scroll pulls back until the strokes of the mark are in view; past this a timer finishes it
const FIN_T = 1.3;    // seconds
const KNOTS = [1.0, 1.2, 1.8, 2.2, 2.8, 3.2, 3.8, 4.2, 4.8, 5.2, 5.8, 6.2, 6.8, 7.2, B_END];
const WEIGHT = [0.5, 0.75, 0.5, 1.0, 0.5, 0.7, 0.5, 0.85, 0.5, 0.95, 0.5, 0.8, 0.5, 1.0];
const SPAN = WEIGHT.reduce((a, q) => a + q, 0);
const VH_PER_UNIT = 88;
const bOfP = (p) => {
  let r = Math.min(1, Math.max(0, p)) * SPAN;
  for (let k = 0; k < WEIGHT.length; k++) { if (r <= WEIGHT[k] || k === WEIGHT.length - 1) return KNOTS[k] + (KNOTS[k + 1] - KNOTS[k]) * Math.min(1, r / WEIGHT[k]); r -= WEIGHT[k]; }
  return B_END;
};
const pOfB = (b) => {
  let acc = 0;
  for (let k = 0; k < WEIGHT.length; k++) {
    if (b <= KNOTS[k + 1] || k === WEIGHT.length - 1) return (acc + WEIGHT[k] * Math.min(1, Math.max(0, (b - KNOTS[k]) / (KNOTS[k + 1] - KNOTS[k])))) / SPAN;
    acc += WEIGHT[k];
  }
  return 1;
};

function run(THREE) {
  const canvas = document.getElementById('scene');
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: 'high-performance' });
  } catch (e) { goStatic(); return; }
  const QS = location.search;
  const FREEZE = /[?&]freeze\b/.test(QS), HOLDQ = /[?&]hold\b/.test(QS);
  const FROZEN_T = 2.7;
  const mobile = Math.min(innerWidth, innerHeight) < 640;
  const N = mobile ? 42000 : 78000;
  const DPR_CAP = Math.min(window.devicePixelRatio || 1, 2);
  let dpr = DPR_CAP;
  renderer.setPixelRatio(dpr);
  renderer.setClearColor(0x05070d, 1);
  const scene = new THREE.Scene();
  const cam3 = new THREE.Camera(); // the shader projects by itself

  const seeds = new Float32Array(N); { let a = 5; const r = () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; for (let i = 0; i < N; i++) seeds[i] = r(); }
  const seedAttr = new THREE.BufferAttribute(seeds, 1);

  // uniforms shared by all sets
  const U = {
    uTime: { value: 0 }, uD: { value: D }, uTanH: { value: TANH }, uAspect: { value: 1 },
    uPx: { value: 1 }, uFocus: { value: D * 0.84 }, uAperture: { value: 115 }, uDpr: { value: dpr }, uSizeQ: { value: 1 },
    uSettle: { value: 0 }, uDrift: { value: 1 },
    uSite0: { value: new THREE.Vector3() }, uSite1: { value: new THREE.Vector3() }, uSite2: { value: new THREE.Vector3() },
    uPulse: { value: 0 }, uPulseI: { value: 1 }, uRide: { value: -1 }, uRideI: { value: 0 }, uRideM: { value: -1 }, uRideMI: { value: 0 },
    uCharge: { value: 0 }, uFlash: { value: 0 }, uOut: { value: -1 }, uOutI: { value: 1 }, uTrail: { value: 0 },
  };

  const vert = /* glsl */`
    attribute vec3 aPosA; attribute vec3 aColA; attribute vec4 aAuxA;
    attribute vec3 aCol; attribute vec4 aAux; attribute float aSeed;
    uniform float uTime, uMorph, uModeA, uRotA, uMode, uRot;
    uniform vec3 uCen;
    uniform vec2 uOff; uniform float uS, uQs, uRoll, uAlpha, uDustA, uOver, uApert, uMag, uKx, uThin, uStar; uniform vec3 uRev;
    uniform float uD, uTanH, uAspect, uPx, uFocus, uAperture, uDpr, uSizeQ, uSettle, uDrift;
    uniform vec3 uSite0, uSite1, uSite2;
    uniform float uPulse, uPulseI, uRide, uRideI, uRideM, uRideMI, uCharge, uFlash, uOut, uOutI, uTrail;
    varying vec3 vCol; varying float vAlpha; varying float vBlur; varying float vOver;

    const vec3 MINT = vec3(0.37, 0.94, 0.78);
    const vec3 PERI = vec3(0.54, 0.64, 1.0);

    vec3 rotY(vec3 p, float a) { float c = cos(a), s = sin(a); return vec3(c * p.x + s * p.z, p.y, -s * p.x + c * p.z); }

    // packed normal: brain and neurons dim their far side; membranes (synapse, axon) light their rims
    float facing(float w, float rot, float mode) {
      if (w < 0.5) return 1.0;
      float v = w - 1.0;
      float nx = floor(v / 256.0) / 254.0 * 2.0 - 1.0;
      float nz = mod(v, 256.0) / 254.0 * 2.0 - 1.0;
      float f = -sin(rot) * nx + cos(rot) * nz;
      if ((mode > 2.5 && mode < 3.5) || (mode > 4.5 && mode < 5.5)) { float rim = 1.0 - abs(f); return 0.2 + 1.6 * rim * rim * rim; }
      return mix(0.05, 1.0, smoothstep(-0.12, 0.6, f));
    }
    // a comet: a sharp head ahead, a long tail fading behind
    float comet(float d, float kh, float k1, float k2) { return d > 0.0 ? exp(-d * d * kh) : exp(d * k1) * (0.35 + 0.65 * exp(d * k2)); }

    // per-shape life: glow (brightens and tints), gcol (glow colour), ea (alpha that exists only while lit),
    // am (alpha multiplier, for things that come and go)
    void fx(float mode, float param, inout vec3 p, out float glow, out vec3 gcol, out float ea, out float am) {
      glow = 0.0; ea = 0.0; gcol = MINT; am = 1.0;
      if (mode < 0.5 || param < -90.0) return;  // ambient dust has no life of its own
      if (mode < 1.5) {               // breathing orb, about its own centre
        float br = sin(uTime * 1.25) * 0.04 + sin(uTime * 2.1 + aSeed * 6.2831) * 0.01; // the same in every direction: it stays a sphere
        p = uCen + (p - uCen) * (1.0 + br);
        glow = 0.15 + 0.2 * sin(uTime * 1.25 + aSeed * 3.0);
        gcol = mix(MINT, PERI, step(0.5, fract(aSeed * 7.0)));
      } else if (mode < 2.5) {        // brain and neurons: rare sparks; the active region ripples
        glow = pow(max(0.0, sin(uTime * 0.55 + aSeed * 157.0)), 80.0) * 2.2;
        if (param > 0.5) {
          float w = 0.5 + 0.5 * sin(uTime * 2.4 - (param - 1.0) * 14.0);
          glow += 0.25 + 1.3 * pow(w, 5.0);
        }
      } else if (mode < 3.5) {        // synapse
        if (param >= 1.0 && param < 4.0) {          // transmitter: puffs out of its site, crosses, lands, fades
          float si = floor(param - 1.0), dl = fract(param);
          vec3 site = si < 0.5 ? uSite0 : (si < 1.5 ? uSite1 : uSite2);
          float cyc = fract(uTime / 3.4 + si * 0.37);
          float k = clamp((cyc - dl * 0.1) / 0.4, 0.0, 1.0);
          float e = 1.0 - pow(1.0 - k, 2.4);
          p = mix(site + vec3(fract(aSeed * 17.3) - 0.5, (fract(aSeed * 5.1) - 0.5) * 0.3, fract(aSeed * 29.7) - 0.5) * 0.2, p, e) + vec3(sin(uTime * 5.1 + aSeed * 40.0), cos(uTime * 4.3 + aSeed * 23.0), sin(uTime * 3.7 + aSeed * 61.0)) * 0.016 * e;
          am = smoothstep(0.0, 0.03, k) * (1.0 - smoothstep(0.66, 0.95, cyc));
          glow = 0.45 + 0.8 * (1.0 - e);
          am *= 0.5 + 0.5 * e;
        } else if (param <= -39.5) {                // calcium: blooms through the spine head after the receptors
          float q = -param - 40.0, si = floor(q), d = fract(q);
          float cyc = fract(uTime / 3.4 + si * 0.37);
          float a0 = 0.26 + 0.3 * d;
          float lit = smoothstep(a0, a0 + 0.12, cyc) * (1.0 - smoothstep(0.66, 0.98, cyc)) * (1.0 - 0.5 * d);
          glow = lit * 1.2; ea = lit * 0.05;
        } else if (param <= -20.0) {                // receptors: a field lit mint at rest, flaring as the cloud reaches them
          float q = -param - 20.0, si = floor(q), d = fract(q);
          float cyc = fract(uTime / 3.4 + si * 0.37);
          float a0 = 0.16 + 0.22 * d;
          float lit = smoothstep(a0, a0 + 0.08, cyc) * (1.0 - smoothstep(0.62, 0.95, cyc)) * (1.0 - 0.45 * d);
          lit = max(lit, 0.62 * (1.0 - 0.4 * d));
          glow = lit * 2.2; ea = lit * 0.3;
        } else if (param > -7.5 && param < -6.5) {  // the haze in the cleft: drifting, softly lit
          p += vec3(sin(uTime * 0.31 + aSeed * 30.0), sin(uTime * 0.23 + aSeed * 11.0) * 0.3, cos(uTime * 0.27 + aSeed * 19.0)) * 0.035;
          glow = 0.45 + 0.3 * sin(uTime * 0.9 + aSeed * 20.0);
        } else if (param > -6.0 && param < -4.0) { glow = 0.25 + 0.35 * sin(uTime * 1.4 + aSeed * 6.0); }
        else { glow = pow(max(0.0, sin(uTime * 0.55 + aSeed * 157.0)), 80.0) * 2.2; } // rare sparks, as in the brain
      } else if (mode < 4.5) {        // lattice: a shimmer travelling along the helix, rare sparks
        float w = 0.5 + 0.5 * sin(param * 2.4 - uTime * 2.2);
        glow = pow(w, 14.0) * 1.5 + pow(max(0.0, sin(uTime * 1.6 + aSeed * 91.0)), 40.0) * 1.4;
      } else if (mode < 5.5) {        // spike: a long comet down the axon; one on a loop, one the camera rides
        if (param >= 4.0) {                       // the streak on the axis: bright head, long fading tail
          float t = param - 4.0;
          float f = comet(t - uPulse, 9000.0, 9.0, 60.0) * uPulseI + comet(t - uRide, 9000.0, 9.0, 60.0) * uRideI;
          ea = f * 0.9; glow = f * 2.4; gcol = vec3(0.7, 1.0, 0.9);
        } else if (param >= 2.0) {                // the halo, only about the head
          float t = param - 2.0;
          float f = comet(t - uPulse, 5000.0, 14.0, 60.0) * uPulseI + comet(t - uRide, 5000.0, 14.0, 60.0) * uRideI;
          ea = f * 0.12; glow = f * 1.4; gcol = vec3(0.6, 1.0, 0.86);
        } else if (param >= 0.0) {
          float f = comet(param - uPulse, 8000.0, 3.0, 28.0) * uPulseI + comet(param - uRide, 8000.0, 3.0, 28.0) * uRideI;
          glow = f * 2.3;
        } else if (param > -3.5 && param < -2.5) {  // the soma charges, then flashes as the pulse is born
          float ph = (uPulse + 0.08) / 1.25;
          glow = (smoothstep(0.5, 1.0, ph) * 0.55 + exp(-pow((ph - 0.064) * 16.0, 2.0)) * 1.5) * uPulseI
               + exp(-pow(uRide * 14.0, 2.0)) * 1.6 * uRideI + 0.12;
        }
      } else if (mode < 6.5) {        // artificial spiking neuron
        gcol = PERI;
        if (param >= 0.0 && param < 1.5) {                     // core: brightens with charge, flares on firing
          glow = 0.1 + uCharge * 0.5 + uFlash * 0.6 * (1.0 - min(param, 1.0));
          ea = uCharge * 0.02 * (1.0 - min(param, 1.0)) + uFlash * 0.02;
        } else if (param >= 2.0 && param < 12.0) {             // inputs: mint pulses turning periwinkle at the cell
          float strand = floor(param - 2.0); float t = fract(param);
          float mine = 1.0 - step(0.5, abs(strand - 3.0));
          float head = fract(uTime * 0.5 + strand * 0.37);
          float d = t - head;
          gcol = mix(MINT, PERI, mine > 0.5 ? smoothstep(-0.3, 0.6, t) : smoothstep(0.45, 0.95, t));
          float f = exp(-d * d * 500.0) * (1.0 - mine * uRideMI);
          f += mine * comet(t - uRideM, 3000.0, 4.0, 30.0) * uRideMI * 1.4;   // the pulse that rode in on the axon
          glow = f * 1.2; ea = f * 0.2;
        } else if (param >= 20.0 && param < 25.0) {            // output spike
          float d = (param - 20.0) - uOut;
          glow = uOut > -0.5 ? (exp(-d * d * 400.0) * 3.5 + (d < 0.0 ? exp(d * 9.0) * 0.5 : 0.0)) * uOutI : 0.0;
          ea = uOut > -0.5 ? exp(-d * d * 400.0) * 0.3 * uOutI : 0.0;
        } else if (param >= 30.0 && param < 31.0) {            // the charge, rising as two arcs of light
          float a = param - 30.0;
          float lit = 1.0 - smoothstep(uCharge - 0.02, uCharge, a);
          float edge = exp(-pow((a - uCharge) * 30.0, 2.0)) * step(0.02, uCharge);
          ea = lit * (0.16 + 0.22 * a) + edge * 0.4 + uFlash * 0.12;
          glow = lit * (0.2 + 0.5 * a) + edge * 1.0 + uFlash * 0.5;
        } else if (param >= 31.0 && param < 32.0) {            // the threshold
          glow = 0.2 + smoothstep(0.7, 1.0, uCharge) * 1.2 + uFlash * 1.0;
        } else if (param >= 40.0) {                            // shock ring on firing
          float k = 1.0 - uFlash;
          p.xy *= 1.0 + k * 2.4;
          ea = uFlash * uFlash * 0.3;
          glow = ea * 1.5;
        }
      } else if (mode < 7.5) {        // map: a route lighting up
        gcol = PERI;
        if (param >= 0.0 && param < 1.5) {
          float lit = 1.0 - smoothstep(uTrail - 0.02, uTrail, param);
          float d = (param - uTrail) * 25.0;
          float head = exp(-d * d) * step(0.001, uTrail) * step(uTrail, 0.999);
          glow = lit * 0.45 + head * 1.0;
          ea = lit * 0.05 + head * 0.1;
        } else if (param >= 2.0 && param < 3.5) {               // place fields under the route
          float f = param - 2.0;
          float lit = 1.0 - smoothstep(uTrail - 0.03, uTrail, f);
          ea = lit * 0.11; glow = lit * 0.6;
        }
      } else {                        // mark: a faint slow sheen, gone once it settles
        glow = (0.03 + 0.05 * sin(param * 3.0 - uTime * 0.9)) * (1.0 - uSettle);
        gcol = vec3(0.6, 0.65, 0.75);
        // seen from close, the stroke shows only around the network inside it, and opens outward
        am = 1.0 - smoothstep(uRev.z * 0.35, uRev.z, length(p.xy - uRev.xy));
        // and from close its points are cells like the network's: a few bright, most faint, slowly twinkling
        float st = pow(fract(aSeed * 91.7), 5.0);
        am *= mix(1.0, (0.16 + 1.5 * st) * (0.8 + 0.2 * sin(uTime * (0.7 + fract(aSeed * 13.3)) + aSeed * 50.0)), uStar);
      }
    }

    void main() {
      float isDust = step(aAux.z, -90.0);
      vec3 pb = position; float gb; vec3 gcb; float eab; float amb;
      fx(uMode, aAux.z, pb, gb, gcb, eab, amb);
      float faceB = facing(aAux.w, uRot, uMode);
      vec3 p = rotY(pb, uRot);
      vec3 col = aCol + gcb * gb;
      float alpha = (aAux.y * faceB * (1.0 + gb * 0.6) + eab) * amb;
      float size = aAux.x * (1.0 + gb * 0.4);
      if (uMode > 7.5) size *= mix(1.0, 0.55 + 1.1 * pow(fract(aSeed * 91.7), 5.0), uStar);

      // the one morph: the orb's own points become the brain, each at its own moment
      if (uMorph < 0.999) {
        float t = clamp((uMorph - aSeed * 0.8) / 0.2, 0.0, 1.0);
        t = t * t * (3.0 - 2.0 * t);
        vec3 pa = aPosA; float ga; vec3 gca; float eaa; float ama;
        fx(uModeA, aAuxA.z, pa, ga, gca, eaa, ama);
        float faceA = facing(aAuxA.w, uRotA, uModeA);
        pa = rotY(pa, uRotA);
        float gA = 1.0 - smoothstep(0.0, 0.35, t), gB = smoothstep(0.65, 1.0, t);
        float fl = sin(t * 3.14159);
        vec3 dir = p - pa;
        p = mix(pa, p, t) + vec3(-dir.y, dir.x, 0.0) * (fract(aSeed * 13.7) - 0.5) * 0.28 * fl;
        float alA = (aAuxA.y * faceA * (1.0 + ga * gA * 0.6) + eaa * gA) * ama;
        float alB = (aAux.y * faceB * (1.0 + gb * gB * 0.6) + eab * gB) * amb;
        col = mix(aColA + gca * ga * gA, aCol + gcb * gb * gB, t);
        alpha = mix(alA, alB, t) * (1.0 - 0.4 * fl);
        size = mix(aAuxA.x * (1.0 + ga * 0.4), aAux.x * (1.0 + gb * 0.4), t);
        isDust = mix(step(aAuxA.z, -90.0), isDust, step(0.5, t));
      }
      // never frozen: a faint living drift (stilled once the mark settles)
      p += vec3(sin(uTime * 0.6 + aSeed * 31.0), cos(uTime * 0.5 + aSeed * 17.0), sin(uTime * 0.4 + aSeed * 23.0)) * 0.006 * uDrift;

      // the set's own resting view, then the camera: turn, scale and place it on screen
      float depth = uD - p.z;
      float dz = max(depth, 0.05);
      vec2 u = p.xy / (dz * uTanH);
      float cr = cos(uRoll), sr = sin(uRoll);
      u = vec2(cr * u.x - sr * u.y, sr * u.x + cr * u.y) * uS + uOff;
      gl_Position = vec4(u.x / uAspect, u.y, 0.0, 1.0);

      // size and depth of field at rest, then scaled with the set: a detail far off is small and
      // dim, a set magnified past the lens goes soft as it fades
      float k = uS < 1.0 ? pow(uS, 0.75) : pow(uS, uKx);
      float px = size * uPx / dz * k * uSizeQ;
      float blur = max(0.0, 1.0 / dz - 1.0 / uFocus) * uAperture * uApert * uDpr * k;
      blur += max(0.0, uQs - 1.0) * uDpr * (0.8 + 2.4 * fract(aSeed * 7.3)) * uMag; // passing the lens
      float s = clamp(px + blur, 1.2 * uDpr, 60.0 * uDpr);
      float energy = clamp(pow((px + 0.6 * uDpr) / s, 1.7), 0.01, 1.0);
      float sub = clamp(px / (1.2 * uDpr), 0.15, 1.0);
      float nearFade = smoothstep(0.9, 3.0, depth);
      float farFade = exp(-max(0.0, depth - uFocus) * 0.075);
      float dim = uQs < 1.0 ? mix(0.25, 1.0, sqrt(uQs)) : 1.0 / (1.0 + (uQs - 1.0) * 0.12);
      float setA = mix(uAlpha, uDustA, isDust);
      vOver = uOver * (1.0 - isDust);
      alpha *= 1.0 - 0.75 * uSettle * vOver;
      gl_PointSize = s;
      vCol = col;
      vAlpha = min(alpha * energy * sub * nearFade * farFade * dim * setA, 0.9);
      vBlur = clamp(blur / (px + blur + 0.001), 0.0, 1.0);
      // seen from close, a set can thin to fewer, brighter points (sparks of light, not grain)
      if (isDust < 0.5 && uThin < 0.999) { if (fract(aSeed * 3.71) > uThin) vAlpha = 0.0; else vAlpha = min(vAlpha / sqrt(uThin), 0.9); }
      if (depth < 0.05 || vAlpha < 0.0005) gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
    }
  `;
  const frag = /* glsl */`
    varying vec3 vCol; varying float vAlpha; varying float vBlur; varying float vOver;
    void main() {
      vec2 c = gl_PointCoord * 2.0 - 1.0;
      float d2 = dot(c, c);
      if (d2 > 1.0) discard;
      float g = exp(-d2 * 4.6);
      float disc = (1.0 - smoothstep(0.35, 1.0, sqrt(d2))) * 0.55 + g * 0.25;
      float a = mix(g, disc, vBlur) * vAlpha;
      // blend ONE, ONE_MINUS_SRC_ALPHA: with vOver = 0 this is plain additive light,
      // with vOver = 1 an opaque paint (the mark), so its colours never add into each other
      gl_FragColor = vec4(vCol * a, a * vOver);
    }
  `;

  /* ---- sets ---- */
  const SETS = SPEC.map((spec, i) => ({ i, spec, ready: false, meta: null, bbox: null, n: N }));
  function makeObject(S, pos, col, aux) {
    const geo = new THREE.BufferGeometry();
    const P = new THREE.BufferAttribute(pos, 3), C = new THREE.BufferAttribute(col, 3), A = new THREE.BufferAttribute(aux, 4);
    geo.setAttribute('position', P); geo.setAttribute('aCol', C); geo.setAttribute('aAux', A);
    geo.setAttribute('aPosA', P); geo.setAttribute('aColA', C); geo.setAttribute('aAuxA', A);
    geo.setAttribute('aSeed', seedAttr);
    geo.setDrawRange(0, 0);
    const own = {
      uMorph: { value: 1 }, uModeA: { value: 0 }, uRotA: { value: 0 }, uMode: { value: S.spec.mode }, uRot: { value: S.spec.rot[0] },
      uCen: { value: new THREE.Vector3(...GEN.BRAIN_C) }, uOff: { value: new THREE.Vector2() }, uS: { value: 1 }, uQs: { value: 1 },
      uRoll: { value: 0 }, uAlpha: { value: 0 }, uDustA: { value: 0 }, uOver: { value: S.spec.over || 0 }, uApert: { value: S.spec.ap || 1 }, uMag: { value: S.spec.mag ?? 1 },
      uKx: { value: S.spec.kx ?? 0.5 }, uThin: { value: 1 }, uStar: { value: 0 }, uRev: { value: new THREE.Vector3(0, 0, 99) },
    };
    const mat = new THREE.ShaderMaterial({
      uniforms: { ...U, ...own }, vertexShader: vert, fragmentShader: frag,
      transparent: true, depthWrite: false, depthTest: false,
      blending: THREE.CustomBlending, blendEquation: THREE.AddEquation,
      blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
    });
    const pts = new THREE.Points(geo, mat);
    pts.frustumCulled = false; pts.renderOrder = S.i === 6 ? 8 : S.i;
    scene.add(pts);
    S.geo = geo; S.mat = mat; S.u = own; S.pts = pts;
  }
  // the image of a local point in a set's resting view (screen units), and of a direction there
  const imgOf = (i, p, rot = SPEC[i].rot[0]) => {
    const c = Math.cos(rot), s = Math.sin(rot);
    const x = c * p[0] + s * p[2], y = p[1], z = -s * p[0] + c * p[2], d = D - z;
    return [x / (d * TANH), y / (d * TANH)];
  };
  const angOf = (i, p, dir) => { const a = imgOf(i, p), b = imgOf(i, [p[0] + dir[0] * 0.05, p[1] + dir[1] * 0.05, p[2] + dir[2] * 0.05]); return Math.atan2(b[1] - a[1], b[0] - a[0]); };
  function measure(S) { // image bounds of the set's own matter (not its dust)
    const pos = S.geo.attributes.position.array, aux = S.geo.attributes.aAux.array, rot = S.spec.rot[0];
    let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
    for (let k = 0; k < S.n; k += 3) {
      if (aux[k * 4 + 2] < -90 || aux[k * 4 + 1] <= 0) continue;
      const u = imgOf(S.i, [pos[k * 3], pos[k * 3 + 1], pos[k * 3 + 2]], rot);
      if (u[0] < x0) x0 = u[0]; if (u[0] > x1) x1 = u[0]; if (u[1] < y0) y0 = u[1]; if (u[1] > y1) y1 = u[1];
    }
    const px = (x1 - x0) * 0.12, py = (y1 - y0) * 0.12;
    S.bbox = [x0 - px, y0 - py, x1 + px, y1 + py];
  }

  // the brain's set exists from the first frame: it is the orb until the brain arrives
  const orb = GEN.orbCloud(N);
  const brainSet = SETS[0];
  makeObject(brainSet, orb.pos, orb.col, orb.aux);
  brainSet.u.uMorph.value = 0; brainSet.u.uModeA.value = 1; brainSet.u.uMode.value = 1;
  brainSet.orbOnly = true;

  /* ---- world layout and camera path ---- */
  let portrait = false, aspect = 1, layoutK = 1;
  const World = [];   // per set: { P: [x, y], L, R }
  let keys = [];      // per set: [holdStart, holdEnd] camera states
  let segs = [];      // the path: { b0, b1, K0, K1, A }
  let orbKey = null;
  const fitOf = (i) => { const F = FRAME[i]; return portrait ? F.fm * layoutK : F.fd * (i === 7 ? 1 : layoutK); };
  const frameKey = (i, push) => {
    const S = SETS[i], w = World[i], F = FRAME[i];
    const f = F.f === 'bbox' && S.bbox ? [(S.bbox[0] + S.bbox[2]) / 2, (S.bbox[1] + S.bbox[3]) / 2] : imgOf(i, [0, 0, 0]);
    const sh = portrait ? F.m : F.d;
    const L = w.L - Math.log(fitOf(i)) - push;
    const R = w.R + (F.roll || 0);
    const Wf = add2(w.P, mul2(R2(w.R, f), Math.exp(w.L)));
    return { C: sub2(Wf, mul2(R2(R, sh), Math.exp(L))), L, R, Wf };
  };
  const scr = (A, K) => mul2(R2(-K.R, sub2(A, K.C)), Math.exp(-K.L));
  function relayout() {
    World.length = 0; keys = []; segs = [];
    World[0] = { P: [0, 0], L: 0, R: 0 };
    for (const lk of LINKS) {
      const Sa = SETS[lk.a], Sb = SETS[lk.b];
      if (!Sa.meta || !Sb.meta || !World[lk.a]) break;
      const wa = World[lk.a], ma = Sa.meta, mb = Sb.meta;
      const ua = imgOf(lk.a, ma[lk.pa]), ub = imgOf(lk.b, mb[lk.pb]);
      const L = lk.kind === 'in' ? wa.L - Math.log(lk.Z) : lk.kind === 'out' ? wa.L + Math.log(lk.Z) : wa.L;
      let R = wa.R;
      if (lk.da && lk.db) R = wa.R + angOf(lk.a, ma[lk.pa], ma[lk.da]) - angOf(lk.b, mb[lk.pb], mb[lk.db]);
      const A = add2(wa.P, mul2(R2(wa.R, ua), Math.exp(wa.L)));
      World[lk.b] = { P: sub2(A, mul2(R2(R, ub), Math.exp(L))), L, R };
      lk.A = A;
    }
    // the lattice is held at a turn halfway between the synapse's and the spike's, so the camera
    // rolls a little on the way in and a little on the way out
    if (World[3] && World[4]) FRAME[3].roll = (World[2].R + World[4].R) / 2 - World[3].R;
    for (let i = 0; i < SETS.length; i++) {
      if (!World[i] || !SETS[i].ready) break;
      keys[i] = i === 7 ? [frameKey(7, 0), frameKey(7, 0)] : [frameKey(i, 0), frameKey(i, PUSH)];
    }
    // the orb: a sphere centred on the screen, as large as the brain's frame allows
    {
      const c = imgOf(0, GEN.BRAIN_C), L = -Math.log(portrait ? 0.95 * layoutK : layoutK);
      orbKey = { C: sub2(c, [0, 0]), L, R: 0 };
    }
    if (keys[0]) segs.push({ b0: 0, b1: HOLD[0][0], K0: orbKey, K1: keys[0][0], A: imgOf(0, GEN.BRAIN_C) });
    for (let i = 0; i < keys.length; i++) {
      if (i < 7) segs.push({ b0: HOLD[i][0], b1: HOLD[i][1], K0: keys[i][0], K1: keys[i][1], A: keys[i][0].Wf });
      if (keys[i + 1]) segs.push({ b0: HOLD[i][1], b1: HOLD[i + 1][0], K0: keys[i][1], K1: keys[i + 1][0], A: LINKS[i].A, lead: LINKS[i].lead || 0, dip: LINKS[i].dip || 0 });
    }
  }
  // the camera at a point of the path: within each stretch the meeting point of the two framings
  // slides on screen while scale and roll ease, so position and velocity are continuous everywhere
  function camAt(b) {
    if (!segs.length) return orbKey;
    let s = segs[0];
    if (b <= s.b0) return s.K0;
    for (const q of segs) { s = q; if (b <= q.b1) break; }
    if (b >= s.b1) return s.K1;
    const t = (b - s.b0) / (s.b1 - s.b0), e = SQ(t);
    // with a lead, the meeting point reaches its place on screen early, then the scale follows
    // (both still start and end at rest, so velocity stays continuous)
    const eA = s.lead ? SQ(Math.min(1, t / s.lead)) : e;
    const a = [lerp(scr(s.A, s.K0)[0], scr(s.A, s.K1)[0], eA), lerp(scr(s.A, s.K0)[1], scr(s.A, s.K1)[1], eA)];
    // with a dip, the meeting point sinks on screen mid-move and comes back (at rest at both ends):
    // pulling back from the network, the bowls above its stroke come into view sooner
    if (s.dip) a[1] -= s.dip * Math.sin(Math.PI * e);
    const L = lerp(s.K0.L, s.K1.L, e), R = lerp(s.K0.R, s.K1.R, e);
    return { C: sub2(s.A, mul2(R2(R, a), Math.exp(L))), L, R };
  }
  // the finish: just past the map's hold the pull-back is the timer's, not the scroll's
  const bT = B_T;
  function findThreshold() {}

  /* ---- generation: in a worker, so the orb never waits on it ---- */
  const t0 = performance.now();
  let workerUsed = false;
  function receive(r) {
    const S = SETS[r.k];
    if (r.k === 0) {
      const geo = S.geo;
      geo.setAttribute('position', new THREE.BufferAttribute(r.pos, 3));
      geo.setAttribute('aCol', new THREE.BufferAttribute(r.col, 3));
      geo.setAttribute('aAux', new THREE.BufferAttribute(r.aux, 4));
      S.u.uMode.value = S.spec.mode; S.orbOnly = false;
    } else {
      makeObject(S, r.pos, r.col, r.aux);
    }
    S.meta = r.meta; S.ready = true;
    measure(S);
    if (r.meta.sites) r.meta.sites.forEach((q, j) => U['uSite' + j].value.set(q[0], q[1], q[2]));
    relayout(); findThreshold();
  }
  function buildOnMainThread() { // fallback: one set per task, so the orb keeps breathing between them
    let k = 0;
    const orbM = GEN.orbCloud(N);
    const step = () => { if (k >= 8) return; receive(GEN.buildSet(k, N, mobile, orbM)); k++; setTimeout(step, 30); };
    setTimeout(step, 60);
  }
  try {
    const blob = new Blob([GEN_SRC + `
      self.onmessage = (e) => {
        const { N, mobile } = e.data, orb = orbCloud(N);
        for (let k = 0; k < 8; k++) { const r = buildSet(k, N, mobile, orb); self.postMessage(r, [r.pos.buffer, r.col.buffer, r.aux.buffer]); }
      };`], { type: 'text/javascript' });
    const worker = new Worker(URL.createObjectURL(blob));
    let got = 0;
    worker.onmessage = (e) => { got++; receive(e.data); if (got === 8) worker.terminate(); };
    worker.onerror = () => { if (!got) { worker.terminate(); buildOnMainThread(); } };
    worker.postMessage({ N, mobile });
    workerUsed = true;
  } catch (e) { buildOnMainThread(); }

  /* ---- layout ---- */
  let W = 0, H = 0, lastMark = '';
  function resize() {
    W = innerWidth; H = innerHeight;
    renderer.setPixelRatio(dpr);
    renderer.setSize(W, H, false);
    aspect = W / H;
    const wasPortrait = portrait;
    portrait = aspect < 0.8;
    // the frame a set fills on a wide screen; narrower screens see the same world from further back
    layoutK = portrait ? 1.176 * aspect : 1 / Math.max(1, 1.05 / aspect);
    U.uAspect.value = aspect;
    U.uDpr.value = dpr;
    U.uPx.value = (H * dpr) / (2 * TANH);
    U.uFocus.value = D * 0.84;
    U.uAperture.value = (H / 900) * 115;
    relayout(); findThreshold();
    if (wasPortrait !== portrait) lastMark = '';
  }
  const track = document.getElementById('track');
  track.style.height = (100 + SPAN * VH_PER_UNIT) + 'vh';
  resize();
  addEventListener('resize', resize);

  const scrollMax = () => track.offsetHeight - innerHeight;
  const targetB = () => { const max = scrollMax(); return bOfP(max > 0 ? scrollY / max : 0); };

  const caps = [...document.querySelectorAll('.caption')];
  const finale = document.getElementById('finale');
  const hint = document.getElementById('hint');
  const markVec = document.getElementById('markvec');
  finale.addEventListener('focusin', () => { const max = scrollMax(); if (scrollY < max - 2) scrollTo({ top: max, behavior: 'instant' }); });
  const lastStyle = new Map();
  function setStyle(el, o, y) {
    const key = o.toFixed(3) + '|' + y.toFixed(1);
    if (lastStyle.get(el) === key) return;
    lastStyle.set(el, key);
    el.style.opacity = o.toFixed(3);
    el.style.transform = `translate3d(0, ${y.toFixed(1)}px, 0)`;
    el.style.visibility = o < 0.002 ? 'hidden' : 'visible';
  }

  /* ---- quality: measured, and stepped down when frames get slow ---- */
  const LEVELS = [];
  { const ds = [2, 1.5, 1.25, 1].filter((v) => v <= DPR_CAP + 1e-6); for (const v of ds) LEVELS.push({ dpr: v, size: 1, frac: 1 }); if (!LEVELS.length) LEVELS.push({ dpr: DPR_CAP, size: 1, frac: 1 }); }
  { const last = LEVELS[LEVELS.length - 1]; LEVELS.push({ dpr: last.dpr, size: 0.85, frac: 1 }, { dpr: last.dpr, size: 0.85, frac: 0.75 }, { dpr: last.dpr, size: 0.85, frac: 0.55 }); }
  let qLevel = 0, frac = 1, qFrames = 0, qTime = 0, qSince = 0;
  const qLog = [];
  function applyQuality() {
    const L = LEVELS[qLevel];
    dpr = L.dpr; frac = L.frac; U.uSizeQ.value = L.size;
    resize();
  }
  applyQuality();
  function watchQuality(dt, now) {
    if (FREEZE || !introDone || document.visibilityState !== 'visible') { qFrames = 0; qTime = 0; return; }
    if (dt > 0.25) { qFrames = 0; qTime = 0; return; } // a stall from outside (tab switch), not the scene
    qFrames++; qTime += dt;
    if (qTime < 1.0) return;
    const fps = qFrames / qTime;
    qFrames = 0; qTime = 0;
    if (fps < 50 && qLevel < LEVELS.length - 1 && now - qSince > 1200) {
      qLevel++; qSince = now; applyQuality();
      qLog.push({ fps: Math.round(fps), level: qLevel, dpr, frac, size: U.uSizeQ.value });
    }
  }

  /* ---- the frame ---- */
  let b = 0, bS = 1, fin = 0, introStart = -1, introDone = false, lastNow = performance.now();
  const INTRO = 2600; // ms for the orb to become the brain
  function frame() {
    const now = performance.now();
    const dt = Math.min(0.1, (now - lastNow) / 1000); lastNow = now;
    watchQuality((now - (frame.prev || now)) / 1000, now); frame.prev = now;
    const time = FREEZE ? FROZEN_T : (now - t0) / 1000;
    U.uTime.value = time;

    // intro: the orb breathes until the brain is built, then becomes the brain where it stands
    if (SETS[0].ready && !HOLDQ && introStart < 0 && (FREEZE || now - t0 > 1300)) introStart = now;
    const intro = introStart < 0 ? 0 : FREEZE ? 1 : Math.min(1, (now - introStart) / INTRO);
    if (intro >= 1) introDone = true;
    // scroll, eased (not under ?freeze)
    const tb = targetB();
    if (FREEZE) bS = tb; else { bS += (tb - bS) * (1 - Math.exp(-dt * 4.5)); if (Math.abs(tb - bS) < 0.0005) bS = tb; }
    // the mark is never left as dots: past the threshold a short timer finishes it, and reverses it
    // test mode: the rest of the path spread evenly over the last stretch of scroll, no timer
    // (close to a constant zoom rate, so the 30x pull-back is not all in a few steps)
    const uFz = Math.min(1, Math.max(0, (bS - 7.2) / (B_END - 7.2)));
    const bFz = bS <= 7.2 ? bS : 7.2 + 0.8 * lerp(uFz, 0.5 - Math.sin(Math.asin(1 - 2 * uFz) / 3), 0.85);
    if (FREEZE) fin = Math.min(1, Math.max(0, (bFz - bT) / (8 - bT)));
    else { const want = introDone && bS >= bT ? 1 : 0; fin = Math.min(1, Math.max(0, fin + (want ? 1 : -1) * dt / FIN_T)); }
    const fe = SQ(fin);
    const settle = smooth(0.7, 1.0, fin);
    U.uSettle.value = settle; U.uDrift.value = FREEZE ? 0 : 1 - settle;
    if (!introDone) b = intro;
    else if (FREEZE) b = bFz;
    else b = bS + (8.0 - bS) * fe;

    // the camera
    const cam = camAt(b);
    const drift = FREEZE ? [0, 0] : mul2([Math.sin(time * 0.13) * 0.012, Math.cos(time * 0.11) * 0.009], 1 - settle);

    // per-beat signals
    const ride = SQ(Math.min(1, Math.max(0, (b - 5.2) / 0.6)));
    const inRide = b > 5.2 && b < 5.8;
    U.uPulse.value = ((time * 0.5) % 1) * 1.25 - 0.08;
    U.uPulseI.value = b < 5.2 ? 1 : 1 - smooth(5.2, 5.25, b);
    const rho = ride * 2.08 - 0.04;             // 0..1 along the axon, 1..2 along the machine's input
    U.uRide.value = rho; U.uRideM.value = rho - 1;
    U.uRideI.value = inRide ? smooth(5.2, 5.24, b) * (1 - smooth(5.76, 5.8, b)) : 0;
    U.uRideMI.value = U.uRideI.value;
    const period = 3.2, ph = (time % period) / period;
    let charge, flash, out;
    if (ph < 0.8) { const q = ph / 0.8; charge = (1 - Math.exp(-2.6 * q)) / (1 - Math.exp(-2.6)); flash = 0; out = -1; }
    else { const q = (ph - 0.8) / 0.2; charge = Math.max(0, 1 - q * 5); flash = Math.exp(-q * 5); out = q * 1.1; }
    // while the pulse rides in, it is what charges the cell
    const rideW = b < 5.8 ? 1 : 1 - smooth(5.8, 6.0, b);
    const rideQ = smooth(0.55, 1.0, rho - 1) * 0.92;
    U.uCharge.value = lerp(charge, rideQ, rideW);
    U.uFlash.value = flash * (1 - rideW);
    U.uOut.value = out; U.uOutI.value = 1 - rideW;
    U.uTrail.value = Math.min(1, Math.max(0, (b - 6.7) / 0.5));

    // the sets
    for (const S of SETS) {
      if (!S.geo) continue;
      const w = World[S.i];
      if (!w || (S.i > 0 && !S.ready)) { S.geo.setDrawRange(0, 0); continue; }
      const sp = S.spec;
      const s = Math.exp(w.L - cam.L), q = s / fitOf(S.i);
      const inWin = b > sp.win[0] && b < sp.win[1];
      const lq = Math.log(q);
      // a set may fade differently arriving (b before its beat) and leaving (after it)
      const fi = b > S.i + 1 && sp.finX ? sp.finX : sp.fin;
      const fIn = fi ? smooth(Math.log(fi[0]), Math.log(fi[1]), lq) : 1;
      const fOut = sp.fout ? 1 - smooth(Math.log(sp.fout[0]), Math.log(sp.fout[1]), lq) : 1;
      const off = add2(mul2(R2(-cam.R, sub2(w.P, cam.C)), Math.exp(-cam.L)), drift);
      const roll = w.R - cam.R;
      // dust: only while the set is near its own framing (it fades as the camera pans away from it)
      const fc = FRAME[S.i].f === 'bbox' && S.bbox ? [(S.bbox[0] + S.bbox[2]) / 2, (S.bbox[1] + S.bbox[3]) / 2] : imgOf(S.i, [0, 0, 0]);
      const cpos = add2(mul2(R2(roll, fc), s), off);
      const dist = Math.hypot(cpos[0] / Math.max(1, aspect), cpos[1]);
      const dustA = inWin ? smooth(Math.log(0.3), Math.log(0.7), lq) * (1 - smooth(Math.log(2.4), Math.log(4.4), lq)) * (1 - smooth(2.0, 3.6, dist)) : 0;
      let alpha = inWin ? fIn * fOut : 0;
      // the mark: pr = how far the camera has pulled back from the network (0) to the mark (1), in log-scale
      let pr = 1;
      if (S.i === 7 && keys[6]) { const lq0 = Math.log(Math.exp(w.L - keys[6][1].L) / fitOf(7)); pr = Math.min(1, Math.max(0, 1 - lq / lq0)); alpha *= smooth(0.004, 0.1, pr); }
      // the set's own matter on screen at all?
      let onScreen = alpha > 0.002;
      if (onScreen && S.bbox) {
        const bb = S.bbox, cs = [[bb[0], bb[1]], [bb[2], bb[1]], [bb[0], bb[3]], [bb[2], bb[3]]].map((v) => add2(mul2(R2(roll, v), s), off));
        const x0 = Math.min(...cs.map((v) => v[0])), x1 = Math.max(...cs.map((v) => v[0])), y0 = Math.min(...cs.map((v) => v[1])), y1 = Math.max(...cs.map((v) => v[1]));
        onScreen = x1 > -aspect * 1.05 && x0 < aspect * 1.05 && y1 > -1.05 && y0 < 1.05;
      }
      if (!onScreen && dustA < 0.002) { S.geo.setDrawRange(0, 0); continue; }
      const u = S.u;
      u.uS.value = s; u.uQs.value = q; u.uRoll.value = roll; u.uOff.value.set(off[0], off[1]);
      u.uAlpha.value = onScreen ? alpha * (S.i === 7 && q > 1 ? 1 + (q - 1) * 0.12 * (1 - smooth(0.5, 0.8, pr)) : 1) : 0; u.uDustA.value = dustA;
      const hold = 1 - smooth(0.22, 0.45, Math.abs(b - (S.i + 1)));
      const sway = FREEZE ? 0 : sp.rot[1] * Math.sin(time * sp.rot[2]) * hold * (S.i === 7 ? 1 - settle : 1);
      u.uRot.value = sp.rot[0] + sway;
      if (S.i === 0) {
        u.uMorph.value = S.orbOnly ? 0 : intro;
        u.uRotA.value = FREEZE ? 0 : Math.sin(time * 0.3) * 0.25;
      }
      if (S.i === 7 && S.meta) { const a = S.meta.in; u.uRev.value.set(a[0], a[1], 0.1 + 5.0 * Math.pow(smooth(0, 0.42, pr), 1.6)); u.uThin.value = lerp(0.5, 1, smooth(0.02, 0.4, pr)); u.uStar.value = 1 - smooth(0.1, 0.5, pr); }
      S.geo.setDrawRange(0, Math.floor(S.n * frac));
    }

    // the last frame is the logo itself: the vector mark, laid exactly over its particles
    const MK = SETS[7];
    if (MK.ready && World[7] && fin > 0.001) {
      const { S: ms, CX, CY, OY } = GEN.MARK_GEO, w = World[7];
      const s = Math.exp(w.L - cam.L), roll = w.R - cam.R;
      const off = add2(mul2(R2(-cam.R, sub2(w.P, cam.C)), Math.exp(-cam.L)), drift);
      const toPx = (x, y) => { const u0 = imgOf(7, [(x - CX) * ms, -(y - CY) * ms + OY, 0], MK.u.uRot.value); const u = add2(mul2(R2(roll, u0), s), off); return [(u[0] / aspect * 0.5 + 0.5) * W, (0.5 - u[1] * 0.5) * H]; };
      const p0 = toPx(0, 0), p1 = toPx(26, 24);
      const snap = (v) => Math.round(v * dpr) / dpr;
      const vo = smooth(0.8, 1.0, fin);
      const key = [snap(p0[0]), snap(p0[1]), p1[0] - p0[0], p1[1] - p0[1], vo].map((v) => v.toFixed(2)).join('|');
      if (key !== lastMark) {
        lastMark = key;
        markVec.style.transform = `translate(${snap(p0[0])}px, ${snap(p0[1])}px)`;
        markVec.style.width = (p1[0] - p0[0]).toFixed(2) + 'px';
        markVec.style.height = (p1[1] - p0[1]).toFixed(2) + 'px';
        markVec.style.opacity = vo.toFixed(3);
        finale.style.top = Math.round(p1[1] + (portrait ? 22 : 30)) + 'px';
      }
    } else if (lastMark) { lastMark = ''; markVec.style.opacity = '0'; }

    // captions: one at a time, for the length of their beat's hold
    caps.forEach((el, k) => {
      const c = k + 1;
      const inn = smooth(c - 0.32, c - 0.18, b), out = 1 - smooth(c + 0.2, c + 0.32, b);
      const o = c === 1 ? Math.min(introDone ? (FREEZE ? 1 : smooth(0, 1, (now - introStart - INTRO) / 900)) : 0, out) : inn * out;
      const y = (1 - (c === 1 ? o : inn)) * 18 - (1 - out) * 10;
      setStyle(el, introDone ? o : 0, y);
    });
    const fo = smooth(0.82, 1.0, fin);
    setStyle(finale, fo, (1 - fo) * 22);
    finale.style.visibility = 'visible'; // links stay reachable by keyboard
    hint.style.opacity = (introDone ? (FREEZE ? 1 : smooth(0, 1, (now - introStart - INTRO - 500) / 900)) : 0) * (1 - smooth(1.02, 1.12, b));

    renderer.render(scene, cam3);
    requestAnimationFrame(frame);
  }
  frame(); // the orb is drawn in the very first frame the page shows

  // inspection hooks
  window.__journey = {
    get b() { return b; },
    get ready() { return introDone && SETS.every((S) => S.ready); },
    get quality() { return { level: qLevel, dpr, frac, size: U.uSizeQ.value, log: qLog }; },
    get worker() { return workerUsed; },
    get threshold() { return bT; },
    jump(v) { const max = scrollMax(); scrollTo({ top: pOfB(v) * max, behavior: 'instant' }); bS = v; },
    pOfB,
  };
}
