(function () {
  const main = document.querySelector('main');
  const rootDetails = main.querySelectorAll(':scope > aside > details[open]');
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
  if (location.hash) {
    const target = document.getElementById(location.hash.slice(1));
    reveal(target);
    target?.scrollIntoView();
  }
})();
