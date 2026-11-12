/* Google Scholar publication loader with static HTML fallback.
   The markup emitted here must stay in step with the static fallback in
   index.html — that fallback is what visitors see if this fetch fails. */
(function () {
  'use strict';

  function safeUrl(url) {
    return typeof url === 'string' && /^(https?:|mailto:)/i.test(url);
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function link(label, url) {
    var a = el('a', null, label);
    a.href = url;
    a.target = '_blank';
    a.rel = 'noopener';
    return a;
  }

  function pickTarget(links) {
    links = (links || []).filter(function (item) { return safeUrl(item.url); });
    var isScholar = function (item) {
      return /scholar\.google\./i.test(item.url) || /scholar/i.test(item.label || '');
    };
    var canonical = links.filter(function (item) { return !isScholar(item); })[0];
    return (canonical || links.filter(isScholar)[0] || {}).url || null;
  }

  function paperId(entry, prefix, index) {
    var id = entry.paper_id;
    return typeof id === 'string' && /^[A-Za-z0-9_-]+$/.test(id) ? id : prefix + (index + 1);
  }

  function renderAuthors(entry) {
    var authors = el('p', 'pub-authors');
    (entry.authors || []).forEach(function (author, index) {
      if (index > 0) authors.appendChild(document.createTextNode(', '));
      var name = (author.name || '') + (author.corresponding ? '*' : '');
      authors.appendChild(el(author.me ? 'b' : 'span', 'author', name));
    });
    if (entry.et_al) authors.appendChild(document.createTextNode(', et al.'));
    return authors;
  }

  /* Short venue and year for the first label, e.g. "PNAS 2026"; badges
     that already carry a year, like "SC '26", are used as they are. */
  function venueLabel(entry, item) {
    var badge = entry.venue_badge || item.venue || '';
    if (!badge || /'\d{2}\b/.test(badge) || !entry.year) return badge;
    return badge + ' ' + entry.year;
  }

  /* A paper featured on a journal cover gets a label pointing to the
     cover, which is shown on its own beside News (#cover). */
  function renderChips(entry, item) {
    var chips = el('p', 'pub-chips');
    var label = venueLabel(entry, item);
    if (label) chips.appendChild(el('span', 'chip', label));
    if (entry.status) chips.appendChild(el('span', 'chip chip--soft', entry.status));
    if (entry.frontispiece && document.getElementById('cover')) {
      var cover = el('a', 'chip chip--soft', 'Frontispiece');
      cover.href = '#cover';
      chips.appendChild(cover);
    }
    return chips.childNodes.length ? chips : null;
  }

  /* One text entry per paper: venue labels, title, authors, the full
     venue name, and link buttons. Papers carry no figures here. */
  function renderPaper(item) {
    var entry = item.entry;
    var target = pickTarget(item.links);
    var paper = el('article', 'pub');
    paper.id = 'paper-' + item.id;

    var chips = renderChips(entry, item);
    if (chips) paper.appendChild(chips);

    var title = el('h3', 'pub-title');
    if (target) title.appendChild(link(entry.title || '', target));
    else title.textContent = entry.title || '';
    paper.appendChild(title);

    if (item.withAuthors) paper.appendChild(renderAuthors(entry));

    var full = entry.venue_full || item.venue;
    if (item.isPreprint && !entry.venue_full) full += ' preprint';
    if (full) paper.appendChild(el('p', 'pub-venue', full));

    var links = el('p', 'pub-links');
    item.links.forEach(function (l) {
      if (!safeUrl(l.url)) return;
      links.appendChild(link(l.label || 'Link', l.url));
    });
    if (entry.cited_by > 0) links.appendChild(el('span', 'cites', 'Cited by ' + entry.cited_by));
    if (links.childNodes.length) paper.appendChild(links);
    return paper;
  }

  function capitalize(value) {
    value = String(value);
    return value.charAt(0).toUpperCase() + value.slice(1);
  }

  function collect(list, prefix, isPreprint) {
    return (list || []).map(function (entry, index) {
      var venue = entry.venue_short || (isPreprint ? 'Preprint' : '');
      return {
        entry: entry,
        id: paperId(entry, prefix, index),
        venue: venue,
        isPreprint: isPreprint,
        links: isPreprint ? (safeUrl(entry.url) ? [{ label: venue, url: entry.url }] : [])
                          : (entry.links || []),
        withAuthors: !isPreprint
      };
    });
  }

  function renderInto(list, items, source) {
    var fragment = document.createDocumentFragment();
    items.forEach(function (item) { fragment.appendChild(renderPaper(item)); });
    list.innerHTML = '';
    list.appendChild(fragment);
    list.setAttribute('data-source', source);
  }

  function renderUpdateDate(value) {
    var target = document.getElementById('publication-update');
    if (!target || !value) return;
    var date = new Date(value);
    if (isNaN(date.getTime())) return;
    var formatted = new Intl.DateTimeFormat('en-US', {
      month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC'
    }).format(date);
    target.textContent = 'Publication data updated ' + formatted + '.';
  }

  /* Publications first in their curated order, then preprints. */
  function init() {
    var list = document.getElementById('pub-list');
    if (!list) return;

    fetch('data/publications.json', { cache: 'no-cache' })
      .then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.json();
      })
      .then(function (data) {
        renderUpdateDate(data && data.meta && data.meta.generated_at);
        var items = collect(data && data.publications, 'p', false)
          .concat(collect(data && data.preprints, 'pre', true));
        if (items.length) renderInto(list, items, (data.meta && data.meta.source) || 'live');
      })
      .catch(function (error) {
        console.error('[publications] load failed; keeping static fallback:', error);
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
