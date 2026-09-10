/* Ashwin's notes: the only script the site needs.
   1. Theme toggle (light by default, dark on request or OS preference).
      A tiny inline script in the <head> applies the saved choice before paint;
      this file wires the button and remembers the choice.
   2. Tag filter on the home page (progressive enhancement: without JS every post shows). */
(function () {
  var root = document.documentElement;
  function current() { return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'; }
  function apply(theme) {
    root.setAttribute('data-theme', theme);
    try { localStorage.setItem('theme', theme); } catch (e) {}
    document.querySelectorAll('.theme-toggle').forEach(function (b) {
      b.setAttribute('aria-label', theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
    });
  }
  document.querySelectorAll('.theme-toggle').forEach(function (b) {
    b.addEventListener('click', function () { apply(current() === 'dark' ? 'light' : 'dark'); });
  });
  apply(current());

  var chips = document.querySelectorAll('.filters .chip[data-tag]');
  if (!chips.length) return;
  var cards = document.querySelectorAll('.post-card[data-tags]');
  function filter(tag) {
    chips.forEach(function (c) { c.setAttribute('aria-pressed', String(c.dataset.tag === tag)); });
    var shown = 0;
    cards.forEach(function (card) {
      var on = tag === '' || (' ' + card.dataset.tags + ' ').indexOf(' ' + tag + ' ') >= 0;
      card.classList.toggle('is-hidden', !on); if (on) shown++;
    });
    var empty = document.querySelector('.posts-empty'); if (empty) empty.hidden = shown > 0;
    if (history.replaceState) history.replaceState(null, '', tag ? '#tag=' + encodeURIComponent(tag) : location.pathname);
  }
  chips.forEach(function (c) { c.addEventListener('click', function () { filter(c.getAttribute('aria-pressed') === 'true' ? '' : c.dataset.tag); }); });
  var m = location.hash.match(/^#tag=(.+)$/); if (m) filter(decodeURIComponent(m[1]));
})();
