/* Fleur synaptique aMi — module public V002 (16/11/2026, Claude). V002 : chaque point mène à sa page (clic = fiche + lien, double-clic = ouvre).
   Reproduit le rendu de la Carte Graphify V003 : physique forceAtlas2Based
   qui se pose puis s'arrête, taille = nombre de liens, couleur = famille,
   zoom libre. Données : calque « Le protocole net » seulement (aucun chemin local).
   Éléments attendus : #fleur-synaptique-canvas, #fleur-synaptique-data (JSON),
   #fleur-synaptique-fiche, #fleur-synaptique-familles, #fleur-synaptique-recherche,
   boutons [data-fs-zoom]. Demande vis-network (9.1.6). */
(function () {
  const canvas = document.getElementById('fleur-synaptique-canvas');
  const source = document.getElementById('fleur-synaptique-data');
  if (!canvas || !source || !window.vis) return;
  const data = JSON.parse(source.textContent);
  const byId = new Map(data.nodes.map(n => [n.id, n]));
  const voisins = new Map(data.nodes.map(n => [n.id, []]));
  data.edges.forEach(e => { voisins.get(e.from).push(e.to); voisins.get(e.to).push(e.from); });
  const fiche = document.getElementById('fleur-synaptique-fiche');
  const boiteFamilles = document.getElementById('fleur-synaptique-familles');
  const recherche = document.getElementById('fleur-synaptique-recherche');
  let network = null, nodes, edges;

  function monter() {
    if (network) { network.redraw(); return; }
    if (!canvas.offsetWidth) return;              // vue cachée : on montera à l'affichage
    nodes = new vis.DataSet(data.nodes.map((n, i) => ({
      id: n.id, label: n.label, size: n.size,
      color: {background: n.color, border: n.color, highlight: {background: '#ffffff', border: n.color}},
      font: {size: n.label_size, color: '#f2e5cd', face: 'Jost, system-ui, sans-serif', strokeWidth: 3, strokeColor: '#0c101a'},
      x: 30 * Math.sqrt(i) * Math.cos(i * 2.4), y: 30 * Math.sqrt(i) * Math.sin(i * 2.4),
    })));
    edges = new vis.DataSet(data.edges.map((e, i) => ({
      id: i, from: e.from, to: e.to, dashes: e.dashes, width: e.width,
      color: {color: byId.get(e.from).color, opacity: e.opacity},
      arrows: {to: {enabled: true, scaleFactor: .5}},
    })));
    network = new vis.Network(canvas, {nodes, edges}, {
      physics: {enabled: true, solver: 'forceAtlas2Based',
        forceAtlas2Based: {gravitationalConstant: -60, centralGravity: .005, springLength: 120,
                           springConstant: .08, damping: .4, avoidOverlap: .8},
        stabilization: {iterations: 200, fit: true}},
      interaction: {hover: true, tooltipDelay: 100, hideEdgesOnDrag: true, zoomView: true},
      nodes: {shape: 'dot', borderWidth: 1.5},
      edges: {smooth: {type: 'continuous', roundness: .2}, selectionWidth: 3},
    });
    network.once('stabilizationIterationsDone', () => network.setOptions({physics: {enabled: false}}));
    network.on('click', ({nodes: sel}) => { if (sel.length) montrer(sel[0]); });
    network.on('doubleClick', ({nodes: sel}) => { const n = sel.length && byId.get(sel[0]); if (n && n.url) window.open(n.url, '_blank', 'noopener'); });
    network.on('hoverNode', () => { canvas.style.cursor = 'pointer'; });
    network.on('blurNode', () => { canvas.style.cursor = ''; });
    filtrer();
  }

  function montrer(id) {
    const n = byId.get(id);
    if (!fiche || !n) return;
    fiche.replaceChildren();
    const t = document.createElement('strong'); t.textContent = n.label;
    const f = document.createElement('p'); f.textContent = n.family + ' · ' + n.degree + ' lien' + (n.degree > 1 ? 's' : '');
    fiche.append(t, f);
    if (n.url) { const a = document.createElement('a'); a.href = n.url; a.target = '_blank'; a.rel = 'noopener';
      a.className = 'fs-lire'; a.textContent = '📖 Lire dans ' + (n.edition || 'l’édition'); fiche.append(a); }
    const ul = document.createElement('ul');
    [...new Set(voisins.get(id))].slice(0, 24).forEach(v => {
      const li = document.createElement('li'); const b = document.createElement('button');
      b.type = 'button'; b.textContent = byId.get(v).label;
      b.addEventListener('click', () => { network.selectNodes([v]); network.focus(v, {scale: 1.2, animation: true}); montrer(v); });
      li.append(b); ul.append(li);
    });
    fiche.append(ul);
  }

  const familles = [...new Map(data.nodes.map(n => [n.family, n.color])).entries()];
  const coches = familles.map(([nom, couleur]) => {
    const l = document.createElement('label'); const c = document.createElement('input');
    c.type = 'checkbox'; c.checked = true; c.value = nom;
    const p = document.createElement('span'); p.textContent = '●'; p.style.color = couleur; p.setAttribute('aria-hidden', 'true');
    l.append(c, ' ', p, ' ', nom); if (boiteFamilles) boiteFamilles.append(l);
    c.addEventListener('change', filtrer); return c;
  });
  function filtrer() {
    if (!network) return;
    const off = new Set(coches.filter(c => !c.checked).map(c => c.value));
    const cache = id => off.has(byId.get(id).family);
    nodes.update(data.nodes.map(n => ({id: n.id, hidden: cache(n.id)})));
    edges.update(data.edges.map((e, i) => ({id: i, hidden: cache(e.from) || cache(e.to)})));
  }
  if (recherche) recherche.addEventListener('change', () => {
    const q = recherche.value.trim().toLocaleLowerCase('fr'); if (q.length < 2 || !network) return;
    const n = data.nodes.find(n => n.label.toLocaleLowerCase('fr').includes(q));
    if (n) { network.selectNodes([n.id]); network.focus(n.id, {scale: 1.4, animation: true}); montrer(n.id); }
  });
  document.querySelectorAll('[data-fs-zoom]').forEach(b => b.addEventListener('click', () => {
    if (!network) return; const k = Number(b.dataset.fsZoom);
    if (k) network.moveTo({scale: network.getScale() * k}); else network.fit();
  }));
  new ResizeObserver(monter).observe(canvas);
  monter();
})();
