/* Psyche developer documentation: behaviour only. A classic script, loaded after kit.js and only by
   the documentation pages (<body class="k-docs">).

   The server writes every part of these pages: the navigation and its current page, the home's lists
   and its count, "On this page", previous / next, the edit line and each table cell's label. Without
   script all of it is there and every link works; the search fields stay hidden, since they filter
   only with script. This script writes no page, title, link or description of its own. It adds:
   - the navigation's "Search pages" field (shown here) and the home's filter: every word typed must
     appear in a page's title, description or group (the server writes them, lower case, as
     data-k-text); "/" puts focus in the field, Escape clears it;
   - "Pages" on a narrow screen (900 px and under): it opens and closes the navigation in place;
     Escape closes it from anywhere on the page and returns focus to "Pages";
   - "On this page": the section being read is marked (aria-current="true");
   - a block that scrolls sideways (a code block, a table's region, a drawn diagram) is a keyboard stop
     only while it overflows; checked again when the fonts are in and whenever its box changes size;
   - a drawn diagram: one quiet line "Scrolls sideways" above it while it overflows, its plain-word
     reading as text after it (the drawing itself is then hidden from screen readers, so the reading
     is not heard twice), and, the first time it overflows, a start position that shows its first two
     steps whole (once, at once: no motion). */
(function () {
  'use strict';
  var doc = document;
  if (!doc.body || !doc.body.classList.contains('k-docs')) return;

  // after kit.js has set up the page (its styles are in by then, so sizes can be measured)
  function start(fn) {
    if (window.Psyche && window.Psyche.ready) window.Psyche.ready(fn);
    else if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', fn);
    else fn();
  }
  function list(root, sel) { return Array.prototype.slice.call(root.querySelectorAll(sel)); }
  function typing(t) { return !!t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.nodeName)); }
  function wordsOf(value) { return value.toLowerCase().split(/\s+/).filter(Boolean); }
  function hasAll(text, words) { return words.every(function (w) { return text.indexOf(w) >= 0; }); }
  function shown(el) { return !!el && el.offsetParent !== null; }
  // "/" anywhere outside a field puts focus in the given field while it is on screen
  function slashFocus(field) {
    doc.addEventListener('keydown', function (e) {
      if (e.key !== '/' || e.defaultPrevented || typing(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;
      if (!shown(field)) return;
      e.preventDefault();
      field.focus();
    });
  }

  /* ---------- The navigation: "Search pages" and "Pages" ---------- */
  function setupNav() {
    var nav = doc.querySelector('[data-k-docnav]');
    if (!nav) return;
    var box = nav.querySelector('.k-docnav__search'), q = nav.querySelector('.k-docnav__input');
    var none = nav.querySelector('.k-docnav__none');
    if (box && q) {
      box.hidden = false;
      var items = list(nav, 'li[data-k-text]'), groups = list(nav, '.k-docnav__group');
      var run = function () {
        var words = wordsOf(q.value), count = 0;
        items.forEach(function (li) {
          var ok = hasAll(li.getAttribute('data-k-text') || '', words);
          li.hidden = !ok;
          if (ok) count++;
        });
        groups.forEach(function (g) { g.hidden = !g.querySelector('li:not([hidden])'); });
        if (none) none.hidden = count > 0;
      };
      q.addEventListener('input', run);
      // the first Escape clears the words; the next one may close "Pages"
      q.addEventListener('keydown', function (e) { if (e.key === 'Escape' && q.value) { e.stopPropagation(); q.value = ''; run(); } });
      slashFocus(q);
      if (q.value) run();
    }
    var btn = doc.querySelector('[data-k-docmenu]');
    if (!btn) return;
    function folds() { return getComputedStyle(btn).display !== 'none'; }
    function isOpen() { return nav.classList.contains('is-open'); }
    function set(open, restore) {
      nav.classList.toggle('is-open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (!open && restore) btn.focus();
    }
    btn.setAttribute('aria-expanded', 'false');
    btn.addEventListener('click', function () { set(!isOpen(), false); });
    doc.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape' || e.defaultPrevented || !isOpen() || !folds()) return;
      e.preventDefault();
      set(false, true);
    });
  }

  /* ---------- The home: the filter over every page ---------- */
  function setupIndex() {
    var host = doc.querySelector('[data-k-docindex]'), input = doc.querySelector('[data-k-docfilter]');
    if (!host || !input) return;
    var field = input.closest('.k-filter');
    if (field) field.hidden = false;
    var count = doc.querySelector('[data-k-docfilter-count]'), none = host.querySelector('.k-docindex__none');
    var items = list(host, '.k-docindex__item[data-k-text]'), groups = list(host, '.k-docindex__group');
    var total = items.length;
    function say(n, filtered) {
      if (count) count.textContent = filtered ? n + (n === 1 ? ' page of ' : ' pages of ') + total : total + ' pages';
    }
    function run() {
      var words = wordsOf(input.value), n = 0;
      items.forEach(function (li) {
        var ok = hasAll(li.getAttribute('data-k-text') || '', words);
        li.hidden = !ok;
        if (ok) n++;
      });
      groups.forEach(function (g) { g.hidden = !g.querySelector('.k-docindex__item:not([hidden])'); });
      if (none) none.hidden = n > 0;
      say(n, words.length > 0);
    }
    input.addEventListener('input', run);
    input.addEventListener('keydown', function (e) { if (e.key === 'Escape' && input.value) { e.stopPropagation(); input.value = ''; run(); } });
    slashFocus(input);
    if (input.value) run();
  }

  /* ---------- "On this page": the section being read ---------- */
  // It is the last listed heading above a line just under the header; at the very end of the page the
  // last heading counts as read. Links jump; nothing scrolls smoothly.
  function setupToc() {
    var toc = doc.querySelector('[data-k-toc]');
    if (!toc) return;
    var links = [], heads = [];
    list(toc, 'a[href^="#"]').forEach(function (a) {
      var id;
      try { id = decodeURIComponent(a.getAttribute('href').slice(1)); } catch (e) { return; }
      var h = id && doc.getElementById(id);
      if (h) { links.push(a); heads.push(h); }
    });
    if (!heads.length) return;
    var cur = -1, queued = false;
    function update() {
      queued = false;
      if (!shown(toc)) return;
      var head = doc.querySelector('.k-head'), line = (head ? head.offsetHeight : 0) + 96, i = -1;
      for (var k = 0; k < heads.length; k++) { if (heads[k].getBoundingClientRect().top <= line) i = k; else break; }
      if (window.innerHeight + window.scrollY >= doc.documentElement.scrollHeight - 4) i = heads.length - 1;
      i = Math.max(i, 0);
      if (i === cur) return;
      cur = i;
      links.forEach(function (a, k) { if (k === i) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current'); });
    }
    function queue() { if (!queued) { queued = true; window.requestAnimationFrame(update); } }
    window.addEventListener('scroll', queue, { passive: true });
    window.addEventListener('resize', queue);
    update();
  }

  /* ---------- Blocks that scroll sideways ---------- */
  var checks = [];
  function overflows(el) { return el.scrollWidth > el.clientWidth + 2; }
  function watch(el, check) {
    checks.push(check);
    check();
    if (window.ResizeObserver) {
      var ro = new ResizeObserver(function () { check(); });
      ro.observe(el);
      if (el.firstElementChild) ro.observe(el.firstElementChild);
    }
  }
  function recheck() { checks.forEach(function (c) { c(true); }); }

  // a code block: a tab stop only while its lines run past its box
  function setupCode() {
    list(doc, '.k-doc pre').forEach(function (pre) {
      watch(pre, function () { if (overflows(pre)) pre.tabIndex = 0; else pre.removeAttribute('tabindex'); });
    });
  }

  // a table's region (<div class="sx-table" role="region" tabindex="0" aria-label="Table: …">, written by the
  // server so that it is reachable without script): a region whose table fits gives up its role, its name
  // and its tab stop, and takes them back the moment it scrolls
  var KEPT = ['role', 'tabindex', 'aria-label'];
  function setupTables() {
    list(doc, '.k-doc .sx-table').forEach(function (region) {
      var kept = KEPT.map(function (name) { return region.getAttribute(name); });
      watch(region, function () {
        var scrolls = overflows(region);
        KEPT.forEach(function (name, i) {
          if (!scrolls) region.removeAttribute(name);
          else if (kept[i] !== null) region.setAttribute(name, kept[i]);
        });
      });
    });
  }

  // a drawn diagram (figure.sx-diagram, as staging writes it)
  function setupDiagrams() {
    list(doc, '.k-doc .sx-diagram').forEach(function (fig) {
      var box = fig.querySelector('.sx-diagram__scroll'), svg = fig.querySelector('svg');
      if (!box || !svg) return;
      var title = svg.querySelector('title'), desc = svg.querySelector('desc');
      if (desc && !fig.querySelector('.k-diagram__reading')) {
        var read = doc.createElement('p');
        read.className = 'k-vh k-diagram__reading';
        var name = title ? title.textContent.trim() : '';
        if (name && name.charAt(name.length - 1) !== '.') name += '.';
        read.textContent = (name ? name + ' ' : '') + desc.textContent;
        fig.appendChild(read);
        svg.setAttribute('aria-hidden', 'true');
      }
      var note = doc.createElement('p');
      note.className = 'k-diagram__note';
      note.setAttribute('aria-hidden', 'true');
      note.textContent = 'Scrolls sideways';
      note.hidden = true;
      box.insertAdjacentElement('beforebegin', note);
      // a box that fits gives up its role, its name and its tab stop (a plain box may carry no name), and
      // takes them back the moment it scrolls
      var role = box.getAttribute('role') || 'group', named = box.getAttribute('aria-labelledby'), placed = false;
      watch(box, function (settled) {
        var over = overflows(box);
        if (over) {
          box.tabIndex = 0; box.setAttribute('role', role);
          if (named) box.setAttribute('aria-labelledby', named);
        } else { box.removeAttribute('tabindex'); box.removeAttribute('role'); box.removeAttribute('aria-labelledby'); }
        note.hidden = !over;
        if (!over) { placed = false; return; }
        // the start position, once the page's styles and fonts are in, so it is measured on the final layout
        if (settled !== true || placed || box.scrollLeft !== 0) return;
        placed = true;
        var nodes = svg.querySelectorAll('.node'), b = box.getBoundingClientRect(), lo = Infinity, hi = -Infinity;
        for (var i = 0; i < Math.min(2, nodes.length); i++) {
          var r = nodes[i].getBoundingClientRect();
          lo = Math.min(lo, r.left - b.left); hi = Math.max(hi, r.right - b.left);
        }
        if (hi > box.clientWidth) box.scrollLeft = Math.max(0, Math.min(lo - 4, Math.ceil(hi - box.clientWidth + 4)));
      });
    });
  }

  start(function () {
    setupNav();
    setupIndex();
    setupToc();
    setupCode();
    setupTables();
    setupDiagrams();
    if (!window.ResizeObserver) window.addEventListener('resize', function () { checks.forEach(function (c) { c(); }); });
    if (doc.readyState === 'complete') recheck(); else window.addEventListener('load', recheck);
    try { if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(recheck); } catch (e) { /* no font loading API */ }
  });
})();
