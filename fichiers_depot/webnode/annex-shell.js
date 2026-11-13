(() => {
  'use strict';

  const web = 'https://www.agdistys.fr/';
  const pages = 'https://agdistys.github.io/aMi/';
  const siteRoutes = {
    'ami-tests':'ami-mesures-ia',
    'ami-metamatrice':'metaconscience',
    'ami-citer-contester-contribuer':'lettre-ouverte',
  };
  const standalone = document.currentScript?.matches('[data-ami-annex-standalone]');
  const standaloneData = standalone ? document.currentScript.dataset : null;
  const stickySelectors = {
    'ami-controle-qualite': 'nav.tabs',
    'ami-catalogue-des-outils': 'header.top',
    'ami-metamatrice': '.mm-search',
    'ami-benchmark': '.reader-bar, #ami-benchmark .bar',
    'ami-registre': '#ami-registre .tab-bar, #ami-registre .sbar',
  };
  const fixedSelectors = {
    'ami-benchmark': '#ami-vol-benchmark .top, #ami-vol-benchmark .r36-coins .r36-c, .r36-rech, .glo-bulle',
    'ami-registre': '#ami-registre .ami-coin, #ami-registre #ami-som, #ami-registre #ami-rech',
  };
  const annexes = [
    ['ami-benchmark', '📊 BenchMark'],
    ['ami-catalogue-des-outils', '🧰 Guide des Outils'],
    ['ami-metamatrice', '🪆 MétaMatrice'],
    ['ami-controle-qualite', '✅ Contrôle Qualité'],
    ['ami-tests', '📏 Campagnes de Mesures IA'],
    ['ami-registre', '🔏 Registre public'],
    ['ami-citer-contester-contribuer', '📜 Citer · Contester · Contribuer'],
    ['ami-tuto-esprit-critique', '🧠 Tuto d’Esprit Critique'],
  ];

  const chromeCSS = `
    .ami-annex-host {width:100%;min-width:0;background:#09090e;color:#efe8d7}
    .ami-annex-frame {display:block;width:100%;border:0;margin:0;overflow:hidden;background:#09090e}
    .ami-annex-bar,.ami-annex-footer {box-sizing:border-box;color:#f3e8cf;background:#0b0b11;font-family:Jost,system-ui,sans-serif;text-align:center}
    .ami-annex-bar {position:sticky;top:var(--ami-annex-host-top,0px);z-index:101;border-block-end:1px solid #766025;hyphens:none;overflow-wrap:normal;word-break:normal}
    .ami-annex-bar a,.ami-annex-footer a {color:#ffd06a;text-underline-offset:.22em}
    .ami-annex-progress {height:3px;background:#2c2315}
    .ami-annex-progress span {display:block;height:100%;background:linear-gradient(90deg,#e33232,#de8936,#9abe50,#ffd06a);transform:scaleX(0);transform-origin:left}
    .ami-annex-row {display:grid;grid-template-columns:minmax(max-content,1fr) minmax(0,2.5fr) minmax(max-content,1fr);align-items:center;gap:.5rem;min-height:48px;padding:.2rem clamp(.4rem,2vw,1rem)}
    .ami-annex-row > a,.ami-annex-row > button {justify-self:start}
    .ami-annex-row > a {display:inline-flex;align-items:center;min-height:44px;font-weight:700}
    .ami-annex-current {line-height:1.2;font:700 clamp(.95rem,3vw,1.2rem) Georgia,serif;color:#ffdc8b}
    .ami-annex-menu-toggle {justify-self:end!important;border:1px solid #987237;background:#151019;color:#ffd06a;border-radius:.45rem;font:700 .9rem system-ui,sans-serif;min-height:44px;padding:.2rem .55rem;cursor:pointer;white-space:nowrap}
    .ami-annex-menu {margin:0;padding:.4rem .65rem .7rem;list-style:none;display:flex;flex-wrap:wrap;justify-content:center;gap:.3rem .65rem;max-height:42vh;overflow:auto}
    .ami-annex-menu[hidden] {display:none}
    .ami-annex-menu a {display:inline-flex;align-items:center;min-height:40px;padding:0 .35rem}
    .ami-annex-menu [aria-current="page"] {color:#fff2d5;text-decoration-thickness:2px}
    .ami-annex-footer {border-block-start:1px solid #766025;padding:1.25rem .75rem 1.5rem}
    .ami-annex-footer p {margin:.3rem 0}
    .ami-annex-footer-title {font:700 clamp(1.15rem,4vw,1.5rem) Georgia,serif;color:#ffe0a0}
    .ami-annex-footer-principle {font:700 1.05rem Georgia,serif;color:#ffd06a}
    .ami-annex-footer-motto {font:700 clamp(.95rem,3.3vw,1.12rem) Georgia,serif;color:#e9c685}
    .ami-annex-pledge {max-width:31rem;margin:1rem auto 0;padding-top:.65rem;border-block-start:1px solid #624a23;font:700 clamp(.92rem,3.2vw,1.15rem) Georgia,serif}
    .ami-annex-pledge-grid {display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);gap:.4rem;align-items:center;margin:.5rem 0}
    .ami-annex-pledge-side {display:grid;grid-template-rows:2.3em 2.5em 2.4em;align-items:center}
    .ami-annex-pledge-grid a,.ami-annex-pledge a {text-decoration:none;color:inherit}
    .ami-annex-pledge-grid .ami-annex-magenta {color:#f56da8}
    .ami-annex-pledge-grid .ami-annex-turquoise {color:#72d9d5}
    .ami-annex-pledge-amp {position:relative;color:#9b683b;font-size:clamp(3.5rem,9vw,5.5rem);line-height:1}
    .ami-annex-pledge-amp span {position:absolute;inset:0;display:grid;place-content:center;color:#ffd06a;font:700 .72rem Georgia,serif;white-space:nowrap}
    .ami-annex-pledge .ami-annex-legacy {display:inline-block;color:#9ac345;margin-top:.45rem}
    .ami-annex-footer-links {display:flex;flex-wrap:wrap;justify-content:center;gap:.2rem .8rem;margin-top:.5rem}
    .ami-annex-footer-links a {display:inline-flex;align-items:center;min-height:40px}
    :is(.ami-annex-bar,.ami-annex-footer) :is(a,button):focus-visible {outline:2px solid #ffd06a;outline-offset:3px}
    @media print {.ami-annex-bar{display:none!important}}
  `;

  const readingCSS = `
    html.ami-annex-reading {color-scheme:dark}
    .ami-annex-reading :is(h1,h2,h3,summary) {overflow-wrap:anywhere}
    .ami-annex-reading :is(h1,h2) {text-wrap:balance}
    details.ami-annex-chapter {box-sizing:border-box;border:1px solid #766025;border-radius:.55rem;background:#101018;color:#efe8d7;margin:.65rem 0;min-width:0}
    details.ami-annex-chapter > summary {box-sizing:border-box;display:flex;align-items:center;gap:.65rem;min-height:44px;padding:.55rem .8rem;color:#ffd06a;cursor:pointer;text-align:left;list-style:none}
    details.ami-annex-chapter > summary::-webkit-details-marker {display:none}
    details.ami-annex-chapter > summary::before {content:'▸';color:#ffd06a;flex:none}
    details.ami-annex-chapter[open] > summary::before {content:'▾'}
    details.ami-annex-chapter > summary h2 {color:inherit;margin:0;font:700 clamp(1.05rem,3.2vw,1.35rem) Georgia,serif}
    details.ami-annex-chapter > .ami-annex-chapter-content {box-sizing:border-box;padding:.2rem .85rem .55rem;min-width:0}
    details > .ami-annex-close {display:block;box-sizing:border-box;margin:.2rem .4rem .3rem auto;padding:0 .6rem;min-width:44px;min-height:44px;border:0;border-radius:.35rem;background:transparent;color:transparent;font:700 .9rem system-ui,sans-serif;cursor:pointer}
    details > .ami-annex-close:is(:hover,:focus-visible) {color:#ffd06a;outline:1px solid #ffd06a;outline-offset:-2px}
    details:not([open]) > .ami-annex-close {display:none}
    @media (hover:none) {details > .ami-annex-close{color:#d4ac61}}
    @media print {details > .ami-annex-close{display:none!important}}
  `;

  function element(doc, tag, className, text) {
    const item = doc.createElement(tag);
    if (className) item.className = className;
    if (text) item.textContent = text;
    return item;
  }

  function style(doc, name, css) {
    if (doc.getElementById(name)) return;
    const node = element(doc, 'style');
    node.id = name;
    node.textContent = css;
    doc.head.append(node);
  }

  function link(doc, text, href, current) {
    const node = element(doc, 'a', '', text);
    node.href = href;
    if (current) node.setAttribute('aria-current', 'page');
    return node;
  }

  function makePledge(doc) {
    const rendezvous = web+'rencontre/';
    const union = web+'union-du-tout/';
    const pledge = element(doc,'div','ami-annex-pledge');
    pledge.append(link(doc,'Pour Le Désir de',rendezvous));
    const grid = pledge.appendChild(element(doc,'div','ami-annex-pledge-grid'));
    const discover = grid.appendChild(element(doc,'div','ami-annex-pledge-side'));
    const amp = grid.appendChild(element(doc,'div','ami-annex-pledge-amp','&'));
    amp.setAttribute('aria-hidden','true');
    amp.append(element(doc,'span','','🌟💎\nen⚡re\n🩸'));
    amp.lastElementChild.style.whiteSpace = 'pre-line';
    const unite = grid.appendChild(element(doc,'div','ami-annex-pledge-side'));
    const sides = [
      [discover,'Se Découvrir','C = ΔI / ΔE','Plaisir d’Offrir','ami-annex-magenta','ami-annex-turquoise'],
      [unite,'Se réUnir','Φ = (U × I) / (R × P)','Joie de Consentir','ami-annex-turquoise','ami-annex-magenta'],
    ];
    for (const [node,title,equation,caption,eqColor,captionColor] of sides) {
      const formula = link(doc,equation,union);
      formula.classList.add(eqColor);
      const last = link(doc,caption,rendezvous);
      last.classList.add(captionColor);
      node.append(link(doc,title,rendezvous),formula,last);
    }
    pledge.append(link(doc,'Tu es un Beau Cadeau fait à Moi-Même & Je-u T’aime',rendezvous));
    const legacy = link(doc,'🌱 Legs = Φ × t',union);
    legacy.classList.add('ami-annex-legacy');
    pledge.append(element(doc,'br'),legacy);
    return pledge;
  }

  function makeChrome(doc, config) {
    const inWebnode = !!config.embedded;
    const nav = element(doc, 'nav', 'ami-annex-bar');
    nav.setAttribute('aria-label', 'Navigation du Protocole aMi');
    const progress = element(doc, 'div', 'ami-annex-progress');
    progress.setAttribute('role', 'progressbar');
    progress.setAttribute('aria-label', 'Progression de lecture');
    progress.setAttribute('aria-valuemin', '0');
    progress.setAttribute('aria-valuemax', '100');
    progress.setAttribute('aria-valuenow', '0');
    const fill = progress.appendChild(element(doc, 'span'));
    const row = element(doc, 'div', 'ami-annex-row');
    row.append(link(doc, '❤️‍🔥 aMi', inWebnode ? web + 'ami/' : pages));
    row.append(element(doc, 'span', 'ami-annex-current', config.label));
    const toggle = row.appendChild(element(doc, 'button', 'ami-annex-menu-toggle', '☰ Annexes'));
    toggle.type = 'button';
    toggle.setAttribute('aria-expanded', 'false');
    const menu = element(doc, 'ul', 'ami-annex-menu');
    menu.id = 'ami-annex-navigation';
    menu.hidden = true;
    toggle.setAttribute('aria-controls', menu.id);
    const routes = [['ami-charte', '⚖️ Charte'], ...annexes];
    for (const [slug, text] of routes) {
      const item = menu.appendChild(element(doc, 'li'));
      const url = inWebnode && slug !== 'ami-tuto-esprit-critique'
        ? web + (siteRoutes[slug] || slug) + '/'
        : pages + slug + '/';
      item.append(link(doc, text, url, slug === config.slug));
    }
    const setOpen = open => {
      menu.hidden = !open;
      toggle.setAttribute('aria-expanded', String(open));
    };
    toggle.addEventListener('click', () => setOpen(menu.hidden));
    nav.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !menu.hidden) {
        setOpen(false);
        toggle.focus();
      }
    });
    nav.append(progress,row,menu);
    const footer = element(doc, 'footer', 'ami-annex-footer');
    footer.append(element(doc, 'p', 'ami-annex-footer-title', config.label));
    footer.append(element(doc, 'p', '', 'Protocole de ConScience aMi · Agdistys · Diane Serant'));
    footer.append(element(doc, 'p', 'ami-annex-footer-principle', 'Vérité = Respect · Mensonge = Violence'));
    footer.append(element(doc,'p','ami-annex-footer-motto','Demain Toujours Meilleur qu’Hier en ayant Appris les Leçons d’Aujourd’hui'));
    footer.append(element(doc,'p','ami-annex-footer-motto','La ConScience est la Vie qui se reconnaît et se protège'));
    footer.append(makePledge(doc));
    const footerLinks = footer.appendChild(element(doc, 'div', 'ami-annex-footer-links'));
    footerLinks.append(
      link(doc, '❤️‍🔥 Index', inWebnode ? web+'ami/' : pages),
      link(doc, '🗂️ Les Annexes', web+'ami-annexes/'),
      link(doc, '📜 Licence CC BY-SA 4.0', 'https://creativecommons.org/licenses/by-sa/4.0/deed.fr'),
    );
    return {nav,footer,progress,fill};
  }

  function inset(doc, nav) {
    const win = doc.defaultView;
    let bottom = 0;
    for (const bar of doc.querySelectorAll('.h-w.wnd-fixed, #layout > header, header[role=banner], header#header')) {
      if (bar.contains(nav) || nav.contains(bar)) continue;
      const box = bar.getBoundingClientRect();
      const position = win.getComputedStyle(bar).position;
      if (box.width < win.innerWidth * .4 || !box.height) continue;
      if (box.top <= 2 && box.bottom > 0 && ['fixed','sticky'].includes(position)) {
        bottom = Math.max(bottom, box.bottom);
      } else if (bar.matches('.h-w.wnd-fixed')) {
        bottom = Math.max(bottom, box.height);
      }
    }
    return Math.ceil(bottom);
  }

  function mount(host, config) {
    const doc = host.ownerDocument;
    const win = doc.defaultView;
    style(doc, 'ami-annex-chrome', chromeCSS);
    if (config.embedded) {
      // Webnode wrappers with overflow hidden create an unintended sticky container.
      for (let box = host.parentElement; box && box !== doc.body; box = box.parentElement) {
        const css = win.getComputedStyle(box);
        if (css.overflowX === 'hidden') box.style.overflowX = 'clip';
        if (css.overflowY === 'hidden') box.style.overflowY = 'visible';
      }
    }
    const chrome = makeChrome(doc, config);
    host.prepend(chrome.nav);
    host.append(chrome.footer);
    let scheduled = false;
    function update() {
      scheduled = false;
      const top = inset(doc, chrome.nav);
      chrome.nav.style.setProperty('--ami-annex-host-top', top+'px');
      const bounds = host === doc.body ? doc.documentElement.getBoundingClientRect() : host.getBoundingClientRect();
      const max = Math.max(1, bounds.height - win.innerHeight + top);
      const ratio = Math.max(0, Math.min(1, (top - bounds.top) / max));
      chrome.fill.style.transform = 'scaleX('+ratio+')';
      chrome.progress.setAttribute('aria-valuenow', String(Math.round(ratio * 100)));
      if (!config.embedded) {
        chrome.nav.style.setProperty('--ami-annex-standalone-h', chrome.nav.offsetHeight+'px');
        doc.documentElement.style.setProperty('--ami-annex-standalone-top', (top+chrome.nav.offsetHeight)+'px');
      }
    }
    function schedule() {
      if (scheduled) return;
      scheduled = true;
      win.requestAnimationFrame(update);
    }
    win.addEventListener('scroll', schedule, {passive:true});
    win.addEventListener('resize', schedule, {passive:true});
    new win.ResizeObserver(schedule).observe(chrome.nav);
    update();
    return chrome;
  }

  function prepareChapters(doc, slug) {
    // Existing applications and measured views keep their native tabs, forms and disclosures.
    if (slug !== 'ami-benchmark' && slug !== 'ami-tests') return;
    if (slug === 'ami-tests' && doc.querySelector('.amim-chapter')) return;
    const sections = slug === 'ami-benchmark'
      ? doc.querySelectorAll('#ami-benchmark main > section.intro-section, #ami-benchmark main section[data-chapter]')
      : doc.querySelectorAll('#ami-mesures-v005 main > section[id^="amim-"]');
    for (const section of sections) {
      const heading = section.querySelector(':scope > h2');
      if (!heading || section.querySelector(':scope > details.ami-annex-chapter')) continue;
      const detail = element(doc, 'details', 'ami-annex-chapter');
      const summary = element(doc, 'summary');
      const content = element(doc, 'div', 'ami-annex-chapter-content');
      summary.append(heading);
      content.append(...section.childNodes);
      detail.append(summary,content);
      section.append(detail);
    }
  }

  function reveal(target, openChapter = false) {
    if (openChapter) {
      const own = target.querySelector(':scope > details:is(.amim-chapter,.ami-annex-chapter)');
      if (own) own.open = true;
    }
    const summary = target.closest('summary');
    let fold = target.closest('details');
    if (fold && summary?.parentElement === fold) fold = fold.parentElement?.closest('details');
    for (; fold; fold = fold.parentElement?.closest('details')) fold.open = true;
  }

  function addClosers(doc, root) {
    const accepted = root.matches?.('details') ? [root] : [];
    for (const detail of [...accepted,...root.querySelectorAll('details')]) {
      const summary = detail.querySelector(':scope > summary');
      if (!summary || detail.querySelector(':scope > :is(.ami-annex-close,.br-fin,[data-ami-close],[data-ami-close-fold])')) continue;
      const close = element(doc, 'button', 'ami-annex-close', '▴ Replier');
      close.type = 'button';
      close.addEventListener('click', () => {
        detail.open = false;
        summary.focus({preventScroll:true});
        summary.scrollIntoView({block:'nearest',behavior:'auto'});
      });
      detail.append(close);
    }
  }

  function enhance(doc, config) {
    style(doc, 'ami-annex-reading-css', readingCSS);
    doc.documentElement.classList.add('ami-annex-reading');
    prepareChapters(doc, config.slug);
    if (config.slug !== 'ami-tests' || !doc.querySelector('.amim-chapter')) {
      addClosers(doc,doc.body);
      // The public register and guide lazily create additional detail groups.
      if (['ami-registre','ami-catalogue-des-outils'].includes(config.slug)) {
        new doc.defaultView.MutationObserver(records => {
          for (const record of records) for (const node of record.addedNodes) {
            if (node.nodeType === 1 && !node.matches('script,style,button.ami-annex-close')) addClosers(doc,node);
          }
        }).observe(doc.body,{childList:true,subtree:true});
      }
    }
    const sticky = stickySelectors[config.slug];
    if (sticky && !config.embedded) {
      style(doc, 'ami-annex-direct-sticky', sticky.split(',').map(selector =>
        'html.ami-annex-reading '+selector.trim()+':not(.sbar){top:var(--ami-annex-standalone-top,0px)!important}'
      ).join(''));
      if (config.slug === 'ami-registre') {
        style(doc, 'ami-annex-direct-substicky', '#ami-registre .sbar{top:calc(var(--ami-annex-standalone-top,0px) + var(--bar-h,0px))!important}');
      }
    }
  }

  function connect(frame, chrome, config) {
    const doc = frame.contentDocument;
    const win = frame.contentWindow;
    if (!doc?.body) return false;
    const host = frame.ownerDocument.defaultView;
    const body = doc.body;
    const rawRect = win.Element.prototype.getBoundingClientRect;
    const nativeInto = win.Element.prototype.scrollIntoView;
    const nativeScroll = win.scrollTo.bind(win);
    let scheduled = false;
    let lastHeight = 0;
    let ready = false;
    let innerOffset = 0;
    style(doc, 'ami-annex-frame-flow', 'html,body{height:auto!important;min-height:0!important}html{overflow-y:hidden!important}body{overflow-x:clip}');
    enhance(doc,config);

    function offset() {
      return Math.max(0,chrome.nav.getBoundingClientRect().bottom - frame.getBoundingClientRect().top);
    }

    function height() {
      if (doc.fullscreenElement) return;
      let measured = rawRect.call(body).height;
      for (const node of body.children) {
        if (node.matches('style,script,link,template')) continue;
        const computed = win.getComputedStyle(node);
        if (computed.display !== 'none' && !['fixed','absolute'].includes(computed.position)) {
          const box = rawRect.call(node);
          measured = Math.max(measured, box.bottom + (Number.parseFloat(computed.marginBottom) || 0));
        }
      }
      measured = Math.max(260, Math.ceil(measured + (Number.parseFloat(win.getComputedStyle(body).marginBottom) || 0)));
      if (Math.abs(measured-lastHeight) > 1) {
        frame.style.height = measured+'px';
        lastHeight = measured;
      }
    }

    const sticky = stickySelectors[config.slug];
    const fixed = fixedSelectors[config.slug];
    const rememberedFixed = new WeakMap();
    function place() {
      let top = offset();
      innerOffset = 0;
      if (sticky) for (const bar of doc.querySelectorAll(sticky)) {
        if (!bar.getClientRects().length) continue;
        bar.style.setProperty('top',top+'px','important');
        const rect = rawRect.call(bar);
        if (rect.top <= top + 1) {
          top += rect.height;
          innerOffset += rect.height;
        }
      }
      if (fixed) {
        const bottom = Math.min(lastHeight, Math.max(0, host.innerHeight - frame.getBoundingClientRect().top));
        for (const control of doc.querySelectorAll(fixed)) {
          if (!control.getClientRects().length || win.getComputedStyle(control).position !== 'fixed') continue;
          const computed = win.getComputedStyle(control);
          let align = rememberedFixed.get(control);
          if (!align) {
            const side = computed.bottom !== 'auto' ? 'bottom' : 'top';
            align = {side, pad:Number.parseFloat(computed[side]) || 0};
            rememberedFixed.set(control,align);
          }
          const value = align.side === 'bottom' ? Math.max(0,lastHeight-bottom)+align.pad : Math.min(top,lastHeight)+align.pad;
          control.style.setProperty(align.side, value+'px','important');
        }
      }
    }

    function schedule() {
      if (scheduled) return;
      scheduled = true;
      host.requestAnimationFrame(() => {
        scheduled = false;
        height();
        place();
      });
    }

    function headerHeight() {
      return inset(frame.ownerDocument,chrome.nav) + chrome.nav.offsetHeight;
    }

    function to(target, options={}) {
      if (!target || !target.isConnected) return;
      reveal(target);
      height();
      const bound = rawRect.call(target);
      const top = frame.getBoundingClientRect().top + bound.top;
      const pad = headerHeight() + innerOffset + 8;
      if (options.block === 'nearest' && top >= pad && top+bound.height <= host.innerHeight) return;
      const shift = options.block === 'center' ? Math.max(0, (host.innerHeight-pad-bound.height)/2) : 0;
      host.scrollTo({top:Math.max(0,host.scrollY + top - pad - shift),behavior:options.behavior || 'auto'});
    }

    // Preserve internal jump logic while the outer Webnode page owns vertical scrolling.
    win.Element.prototype.scrollIntoView = function (options) {
      if (doc.fullscreenElement) return nativeInto.call(this,options);
      for (let ancestor = this.parentElement; ancestor && ancestor !== body; ancestor = ancestor.parentElement) {
        const scrollable = ancestor.scrollHeight > ancestor.clientHeight + 2 &&
          /auto|scroll/.test(win.getComputedStyle(ancestor).overflowY);
        if (scrollable) return nativeInto.call(this,options);
      }
      return to(this,typeof options === 'object' ? options : {});
    };
    win.scrollTo = function (x, y) {
      if (doc.fullscreenElement) return nativeScroll(x,y);
      const target = typeof x === 'object' ? x.top : y;
      host.scrollTo({
        top:Math.max(0,host.scrollY + frame.getBoundingClientRect().top + (target || 0) - headerHeight()),
        behavior:typeof x === 'object' ? x.behavior || 'auto' : 'auto',
      });
    };
    function targetByHash(hash) {
      if (!hash || hash === '#') return null;
      try { return doc.getElementById(decodeURIComponent(hash.slice(1))); } catch { return null; }
    }
    function moveHash(hash) {
      const target = targetByHash(hash);
      if (!target) return;
      reveal(target,true);
      to(target,{behavior:'instant'});
      // The site menu may switch to its fixed height after the initial jump.
      const jumpedY = host.scrollY;
      host.setTimeout(() => {
        if (host.location.hash !== hash || Math.abs(host.scrollY-jumpedY) > 8) return;
        const top = frame.getBoundingClientRect().top + rawRect.call(target).top;
        const min = headerHeight() + innerOffset + 8;
        if (top >= min-160 && top < min-2) to(target,{behavior:'instant'});
      },220);
    }
    doc.addEventListener('click', event => {
      if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.button) return;
      const a = event.target.closest?.('a[href]');
      if (!a || a.hasAttribute('download')) return;
      const href = a.getAttribute('href');
      if (href.startsWith('#')) {
        const target = targetByHash(href);
        if (!target) return;
        event.preventDefault();
        if (host.location.hash !== href) host.history.pushState(null,'',href);
        moveHash(href);
        return;
      }
      // Keep explicit new-tab links and downloads, and pass normal clicks to the site.
      if (!event.isTrusted || (a.target && !['_top','_parent','_self'].includes(a.target))) return;
      const url = new URL(a.href);
      if (!/^https?:$/.test(url.protocol)) return;
      event.preventDefault();
      host.location.assign(url.href);
    });
    host.addEventListener('hashchange', () => moveHash(host.location.hash));
    host.addEventListener('popstate', () => moveHash(host.location.hash));
    host.addEventListener('scroll', schedule, {passive:true});
    host.addEventListener('resize', schedule, {passive:true});
    win.addEventListener('scroll', () => {
      if (!ready || doc.fullscreenElement || !win.scrollY) return;
      const y = win.scrollY;
      nativeScroll({top:0,left:0,behavior:'instant'});
      host.scrollBy({top:y,behavior:'instant'});
    },{passive:true});
    new win.ResizeObserver(schedule).observe(body);
    doc.addEventListener('toggle',schedule,true);
    doc.addEventListener('load',schedule,true);
    doc.fonts?.ready.then(schedule);
    ready = true;
    height();
    place();
    moveHash(host.location.hash);
    return true;
  }

  if (standaloneData) {
    const {slug,label} = standaloneData;
    if (slug && label && !document.querySelector('.ami-annex-bar')) {
      const chrome = mount(document.body,{slug,label,embedded:false});
      enhance(document,{slug,embedded:false});
      const openHash = () => {
        if (!location.hash) return;
        let target;
        try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch { return; }
        if (target) {
          reveal(target,true);
          target.style.scrollMarginTop = chrome.nav.offsetHeight+8+'px';
          target.scrollIntoView();
        }
      };
      addEventListener('hashchange',openHash);
      addEventListener('load',openHash,{once:true});
    }
  }
  globalThis.AmiAnnexShell = {mount,enhance,connect};
})();
