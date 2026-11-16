(function () {
  const main = document.querySelector('main');
  const history = document.getElementById('hist');
  for (const aside of [...main.querySelectorAll(':scope > aside')].reverse()) {
    history.prepend(aside);
  }
  const rootDetails = main.querySelectorAll('aside > details[open]');
  for (const details of rootDetails) details.open = false;
  for (const panel of main.querySelectorAll(':scope > section')) {
    let body;
    for (const element of Array.from(panel.children)) {
      if (element.tagName === 'H2') {
        const details = document.createElement('details');
        details.className = 'cq-chapitre';
        const summary = document.createElement('summary');
        body = document.createElement('div');
        body.className = 'cq-chapitre-contenu';
        element.before(details);
        details.append(summary, body);
        summary.append(element);
      } else if (body) {
        body.append(element);
      }
    }
  }
  const tools = document.querySelector('#outils .cq-chapitre-contenu');
  if (tools) {
    const families = [
      ['Auditer et vérifier', /audit|verif|contraste|sonde|mes_cibles|passe[-_](rapport|photo|essai|tourner)/i],
      ['Navigation, intégration et plein écran', /webnode|collant|iframe|plein_ecran|barre|pied|cadre|pont|coins/i],
      ['Écriture, couleurs et lexique', /palette|couleur|majuscul|_texte|defs|jetons|_forme|_bom/i],
      ['Construire et publier les outils', /chaine|amiblocs|profil|page_cq|ville|cascade/i],
      ['Adapter un volume', /./],
    ].map(([title, pattern]) => {
      const group = document.createElement('details');
      group.className = 'cq-chapitre';
      const heading = document.createElement('summary');
      heading.textContent = title;
      group.append(heading);
      return {pattern,group};
    });
    const cards = tools.querySelectorAll(':scope > details.outil');
    if (cards.length) {
      tools.parentElement.open = true;
      const intro = tools.querySelector(':scope > p.lead');
      if (intro?.firstChild?.nodeType === Node.TEXT_NODE) {
        intro.firstChild.textContent = intro.firstChild.textContent.replace(
          "Dans l'ordre où ils se rejouent sur une page.", 'Outils classés par usage.');
      }
      for (const {group} of families) cards[0].before(group);
      for (const card of cards) families.find(({pattern}) => pattern.test(card.id)).group.append(card);
    }
  }
  function reveal(target) {
    if (!target) return;
    const panel = target.closest('main > section');
    if (panel?.hidden) {
      for (const button of document.querySelectorAll('nav.tabs button')) {
        if (button.dataset.t === panel.id) button.click();
      }
    }
    for (let parent = target; parent && parent !== main; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
  }
  document.addEventListener('click', event => {
    const link = event.target.closest?.('a[href^="#"]');
    if (link) reveal(document.getElementById(link.hash.slice(1)));
  }, true);
  if (window === window.parent) {
    const tabs = document.querySelector('nav.tabs');
    const positions = new Map();
    const dock = () => tabs.getBoundingClientRect().bottom + 8;
    let previous;
    tabs.addEventListener('click', event => {
      const button = event.target.closest('button[data-t]');
      previous = button?.getAttribute('aria-selected') === 'false'
        ? main.querySelector(':scope > section:not([hidden])') : null;
      if (!previous) return;
      const bounds = previous.getBoundingClientRect();
      positions.set(previous.id, Math.min(Math.max(0,bounds.height-48),Math.max(0,dock()-bounds.top)));
    }, true);
    tabs.addEventListener('click', event => {
      if (!previous) return;
      const panel = document.getElementById(event.target.closest('button[data-t]').dataset.t);
      const bounds = panel.getBoundingClientRect();
      const depth = Math.min(positions.get(panel.id) ?? 0,Math.max(0,bounds.height-48));
      window.scrollBy({top:bounds.top-dock()+depth,behavior:'instant'});
      previous = null;
    });
  }
  if (location.hash) {
    const target = document.getElementById(location.hash.slice(1));
    reveal(target);
    if (target && target.closest('details')) target.scrollIntoView();
  }
})();
