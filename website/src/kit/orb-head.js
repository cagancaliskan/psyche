(function (w, d) {
var r = d.documentElement, sc = d.currentScript, fixed = sc && sc.getAttribute('data-k-theme');
function stored() { try { return localStorage.getItem('psyche-theme') === 'light' ? 'light' : 'dark'; } catch (e) { return 'dark'; } }
var q = fixed ? null : /[?&]theme=(light|dark)/.exec(location.search), theme = fixed || (q ? q[1] : stored());
r.setAttribute('data-theme', theme);
r.classList.add('k-js');
var rm = false;
try { rm = matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { }
var O = w.PsycheOrb = { state: rm ? 'open' : 'hold', theme: theme, beforeLeave: null };
var cbOpen = [], cbOpened = [], cbStyled = [];
function fire(list) { list.splice(0).forEach(function (f) { try { f(); } catch (e) { setTimeout(function () { throw e; }, 0); } }); }
O.onOpen = function (f) { if (O.state === 'hold') cbOpen.push(f); else setTimeout(f, 0); };
O.onOpened = function (f) { if (O.state === 'open') setTimeout(f, 0); else cbOpened.push(f); };
O.hold = function () { managed = true; };
O.ready = function () { if (!readyAt) readyAt = Date.now(); };
var managed = false, readyAt = 0, domAt = 0;
O.styled = false;
r.classList.add('k-wait');
function sheetsIn() {
var ls = d.querySelectorAll('link[data-k-css]');
for (var i = 0; i < ls.length; i++) if (!ls[i].kDone && !ls[i].sheet) return false;
return true;
}
function checkStyled() {
if (O.styled || !domAt || !sheetsIn()) return;
O.styled = true;
r.classList.remove('k-wait');
fire(cbStyled);
}
O.whenStyled = function (f) { if (O.styled) f(); else cbStyled.push(f); };
function sheetDone(e) {
var t = e.target;
if (t && t.nodeName === 'LINK' && t.hasAttribute('data-k-css')) { t.kDone = true; if (t.media === 'print') t.media = 'all'; setTimeout(checkStyled, 0); }
}
d.addEventListener('load', sheetDone, true);
d.addEventListener('error', sheetDone, true);
d.addEventListener('DOMContentLoaded', function () { domAt = Date.now(); checkStyled(); });
if (rm) { O.leave = function (href) { if (O.beforeLeave) O.beforeLeave(href); location.href = href; }; return; }
r.classList.add('k-arrive');
var FIELD = { dark: '#05070d', light: '#f5f7fb' };
var COL = { dark: ['rgb(238,241,248)', 'rgb(94,240,200)', 'rgb(138,162,255)'], light: ['rgb(10,13,20)', 'rgb(8,122,92)', 'rgb(47,79,214)'] };
var KEY = 'psyche-orb', DARK_ONLY = /^[a-z]+:\/\/[^/]+\/$/i, LEAVE = 720, OPEN = 1400, WAIT = 700, CAP = 4000;
function mulberry(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
var cache = {};
function points(n) {
if (cache[n]) return cache[n];
var rng = mulberry(7), pts = [], ga = Math.PI * (3 - Math.sqrt(5));
for (var k = 0; k < n; k++) {
var y = 1 - (k / (n - 1)) * 2, rr0 = Math.sqrt(1 - y * y), th = ga * k;
var inner = rng() < 0.16, rr = inner ? 0.35 + 0.5 * rng() : 1 + (rng() - 0.5) * 0.03, u = rng();
pts.push({ x: Math.cos(th) * rr0 * rr, y: y * rr, z: Math.sin(th) * rr0 * rr, c: u < 0.26 ? 1 : u < 0.4 ? 2 : 0,
s: inner ? 0.7 : 0.8 + rng() * 0.7, sx: rng() * 2 - 1, sy: rng() * 2 - 1, d: rng() * 0.35 });
}
return (cache[n] = pts.sort(function (a, b) { return a.c - b.c; }));
}
function draw(ctx, W, H, cx, cy, R, t, pts, o) {
var th = o.theme, fills = COL[th], dpr = o.dpr || 1, lastC = -1;
ctx.globalCompositeOperation = th === 'dark' ? 'lighter' : 'source-over';
var a = t * 0.35, ca = Math.cos(a), sa = Math.sin(a), ct = Math.cos(0.38), st = Math.sin(0.38);
for (var i = 0; i < pts.length; i++) {
var p = pts[i];
var x = p.x * ca + p.z * sa, z = -p.x * sa + p.z * ca, y = p.y * ct - z * st; z = p.y * st + z * ct;
var k = 3 / (3 - z), px = cx + x * R * k, py = cy + y * R * k;
var sp = o.spread ? Math.min(1, Math.max(0, (o.spread - p.d) / (1 - p.d))) : 0;
if (sp > 0) { var e = sp * sp * (3 - 2 * sp); px += (cx + p.sx * W * 0.62 - px) * e; py += (cy + p.sy * H * 0.62 - py) * e; }
var depth = (z + 1) / 2, al = (0.22 + 0.78 * depth) * (o.alpha == null ? 1 : o.alpha) * (1 - sp * 0.6);
if (th === 'light') al = Math.min(1, al * 1.15);
if (al < 0.004) continue;
if (p.c !== lastC) { ctx.fillStyle = fills[p.c]; lastC = p.c; }
ctx.globalAlpha = al > 1 ? 1 : al;
ctx.beginPath(); ctx.arc(px, py, Math.max(0.6, p.s * (R / 90) * dpr * (0.75 + 0.5 * depth)), 0, 6.2832); ctx.fill();
}
ctx.globalAlpha = 1;
ctx.globalCompositeOperation = 'source-over';
}
function frameAt(x, W, H, Rr, dpr, pts, th, ph, e) {
var field = 1, spread = 0, alpha = 1, grow = 1;
if (e >= 0) {
var u = Math.min(1, Math.max(0, (e - 0.06) / 0.94)), f = Math.min(1, e / 0.72);
spread = 1 - Math.pow(1 - u, 3); field = 1 - f * f * (3 - 2 * f);
alpha = 1 - Math.min(1, Math.max(0, (e - 0.4) / 0.6)); grow = 1 + spread * 0.6;
}
x.clearRect(0, 0, W, H);
if (field > 0) { x.globalAlpha = Math.min(1, field); x.fillStyle = FIELD[th]; x.fillRect(0, 0, W, H); x.globalAlpha = 1; }
draw(x, W, H, W / 2, H / 2, Rr * grow, ph, pts, { dpr: dpr, spread: spread, alpha: alpha, theme: th });
}
O.points = points; O.draw = draw; O.field = FIELD;
function bare(u) { try { u = decodeURI(u); } catch (e) { } return u.split('#')[0].split('?')[0]; }
var base = 1.5, at = Date.now();
try {
var s = JSON.parse(sessionStorage.getItem(KEY) || 'null');
sessionStorage.removeItem(KEY);
if (s && Date.now() - s.at < 15000 && s.to === bare(location.href)) { base = s.base; at = s.at; }
} catch (e) { }
function phase() { return base + (Date.now() - at) / 1000; }
function Veil() {
var c = d.createElement('canvas'), dpr = Math.min(2, w.devicePixelRatio || 1);
c.className = 'k-orb-veil'; c.setAttribute('aria-hidden', 'true');
var W = c.width = Math.round(innerWidth * dpr), H = c.height = Math.round(innerHeight * dpr);
(d.body || r).appendChild(c);
return { c: c, x: c.getContext('2d'), W: W, H: H, dpr: dpr, R: Math.min(W, H) * 0.12, n: innerWidth < 700 ? 700 : 1100, pts: points(innerWidth < 700 ? 700 : 1100) };
}
function paint(v, th, fieldA, spread, alpha, grow) {
var x = v.x;
x.clearRect(0, 0, v.W, v.H);
if (fieldA > 0) { x.globalAlpha = Math.min(1, fieldA); x.fillStyle = FIELD[th]; x.fillRect(0, 0, v.W, v.H); x.globalAlpha = 1; }
draw(x, v.W, v.H, v.W / 2, v.H / 2, v.R * grow, phase(), v.pts, { dpr: v.dpr, spread: spread, alpha: alpha, theme: th });
}
function spin() {
var o = null, x = null, tOpen = -1, live = true;
var next = self.requestAnimationFrame ? function (f) { self.requestAnimationFrame(f); } : function (f) { setTimeout(f, 16); };
function frame() {
if (!live) return;
var e = tOpen < 0 ? -1 : Math.min(1, (Date.now() - tOpen) / o.open);
frameAt(x, o.W, o.H, o.R, o.dpr, o.pts, o.theme, o.base + (Date.now() - o.at) / 1000, e);
if (e >= 1) { live = false; return; }
next(frame);
}
self.onmessage = function (m) {
var g = m.data;
if (g.canvas) {
try { o = g; x = g.canvas.getContext('2d'); o.pts = points(g.n); frame(); self.postMessage('ok'); } catch (e) { self.postMessage('fail'); }
} else if (g.open) tOpen = g.open;
else if (g.stop) live = false;
};
}
function Spinner(v) {
try {
if (!w.Worker || !w.OffscreenCanvas || !w.Blob || !w.URL || !HTMLCanvasElement.prototype.transferControlToOffscreen) return null;
var src = 'var cache={},FIELD=' + JSON.stringify(FIELD) + ',COL=' + JSON.stringify(COL) + ';\n' +
mulberry + '\n' + points + '\n' + draw + '\n' + frameAt + '\n(' + spin + ')();';
var url = URL.createObjectURL(new Blob([src], { type: 'text/javascript' }));
var c = d.createElement('canvas');
c.className = 'k-orb-veil'; c.setAttribute('aria-hidden', 'true');
c.width = v.W; c.height = v.H;
var off = c.transferControlToOffscreen(), wk = new Worker(url);
var sp = { c: c, wk: wk, ok: false, dead: false };
wk.onmessage = function (m) { if (m.data === 'ok') sp.ok = true; else sp.dead = true; };
wk.onerror = function () { sp.dead = true; };
wk.postMessage({ canvas: off, W: v.W, H: v.H, dpr: v.dpr, R: v.R, n: v.n, theme: theme, base: base, at: at, open: OPEN }, [off]);
v.c.parentNode.insertBefore(c, v.c.nextSibling);
setTimeout(function () { URL.revokeObjectURL(url); }, 0);
return sp;
} catch (e) { return null; }
}
function dropSpinner() { if (!sp) return; try { sp.wk.terminate(); } catch (e) { } sp.c.remove(); sp = null; }
var v = Veil(), t0 = Date.now(), tOpen = 0, raf = 0, sp = null;
paint(v, theme, 1, 0, 1, 1);
sp = Spinner(v);
function loop() {
raf = 0;
if (sp && sp.dead) dropSpinner();
if (O.state === 'hold') {
var n = Date.now();
if (O.styled && (readyAt || n - t0 > CAP || (!managed && domAt && n - domAt > WAIT))) {
O.state = 'opening'; tOpen = Date.now();
if (sp && sp.ok) { sp.wk.postMessage({ open: tOpen }); v.x.clearRect(0, 0, v.W, v.H); }
else dropSpinner();
r.classList.remove('k-arrive');
fire(cbOpen);
}
}
if (O.state === 'hold') { if (!sp || !sp.ok) paint(v, theme, 1, 0, 1, 1); }
else if (O.state === 'opening') {
var e = Math.min(1, (Date.now() - tOpen) / OPEN);
if (!sp) frameAt(v.x, v.W, v.H, v.R, v.dpr, v.pts, theme, phase(), e);
if (e >= 1) { dropSpinner(); v.c.remove(); v = null; O.state = 'open'; fire(cbOpened); return; }
} else return;
raf = requestAnimationFrame(loop);
}
raf = requestAnimationFrame(loop);
d.addEventListener('DOMContentLoaded', function () {
if (managed) return;
var go = function () { requestAnimationFrame(function () { requestAnimationFrame(O.ready); }); };
O.whenStyled(function () { try { d.fonts.ready.then(go, go); } catch (e) { go(); } });
});
function target(href) {
var a = d.createElement('a'); a.href = href;
var u = a.href, i = u.indexOf('#');
if (q && !DARK_ONLY.test(bare(u)) && u.indexOf('?') < 0) u = i < 0 ? u + '?theme=' + q[1] : u.slice(0, i) + '?theme=' + q[1] + u.slice(i);
return u;
}
O.leave = function (href) {
if (O.state === 'leaving') return;
if (O.beforeLeave) { try { O.beforeLeave(href); } catch (e) { setTimeout(function () { throw e; }, 0); } }
var to = target(href), th = DARK_ONLY.test(bare(to)) ? 'dark' : fixed ? stored() : (r.getAttribute('data-theme') === 'light' ? 'light' : 'dark');
base = 1.5; at = Date.now();
try { sessionStorage.setItem(KEY, JSON.stringify({ base: base, at: at, to: bare(to), theme: th })); } catch (e) { }
if (raf) cancelAnimationFrame(raf);
dropSpinner();
if (v) v.c.remove();
O.state = 'leaving';
r.classList.add('k-leaving');
v = Veil();
var s0 = Date.now(), gone = false;
(function frame() {
if (O.state !== 'leaving') return;
var e = Math.min(1, (Date.now() - s0) / LEAVE), g = 1 - Math.pow(1 - e, 3);
paint(v, th, g, 1 - g, 0.2 + 0.8 * g, 1);
if (e >= 1 && !gone) { gone = true; location.href = to; }
requestAnimationFrame(frame);
})();
};
d.addEventListener('click', function (e) {
if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
var a = e.target.closest && e.target.closest('a[href]'); if (!a) return;
var h = a.getAttribute('href');
if (!h || h.charAt(0) === '#' || a.target === '_blank' || a.hasAttribute('download') || /^(mailto:|tel:|javascript:)/i.test(h)) return;
if (/^[a-z]+:\/\//i.test(h) && a.host !== location.host) return;
if (!/(\/|\.html?)(#.*)?$/i.test(h)) return;
e.preventDefault();
O.leave(a.href);
});
w.addEventListener('pageshow', function (e) {
if (!e.persisted) return;
dropSpinner();
if (v) { v.c.remove(); v = null; }
O.state = 'open';
r.classList.remove('k-leaving', 'k-arrive');
});
})(window, document);
