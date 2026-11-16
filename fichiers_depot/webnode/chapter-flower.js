(function () {
  const canvas = document.getElementById('chapitres-canvas');
  if (!canvas || !window.vis) return;
  const flower = document.getElementById('graphe-vue-chapitres');
  const data = JSON.parse(document.getElementById('chapitres-data').textContent);
  const entries = new Map(data.nodes.map(node => [node.id, node]));
  const families = [...document.querySelectorAll('[data-chapter-family]')];
  const leafControl = document.getElementById('chapitres-feuilles');
  const referenceControl = document.getElementById('chapitres-renvois');
  const selection = document.getElementById('chapitres-fiche');
  const search = document.getElementById('chapitres-recherche');
  const results = document.getElementById('chapitres-resultats');
  let network, nodes, edges;

  function show(id) {
    const node = entries.get(id);
    const link = document.createElement('a');
    link.href = node.url;
    link.textContent = node.chapter ? 'Lire cette section' : 'Lire l’édition';
    selection.replaceChildren();
    const title = document.createElement('strong');
    title.textContent = node.label;
    selection.append(title, ' ', link);
  }

  function applyFilters() {
    if (!network) return;
    const disabled = new Set(families.filter(box => !box.checked).map(box => Number(box.value)));
    const hidden = new Set(data.nodes.filter(node =>
      disabled.has(node.family) || (node.chapter && !leafControl.checked)
    ).map(node => node.id));
    nodes.update(data.nodes.map(node => ({id: node.id, hidden: hidden.has(node.id)})));
    edges.update(data.edges.map(edge => ({
      id: edge.id,
      hidden: hidden.has(edge.from) || hidden.has(edge.to) || (edge.reference && !referenceControl.checked),
    })));
  }

  function mount() {
    if (!flower.checked) return;
    if (network) {
      network.redraw();
      return;
    }
    nodes = new vis.DataSet(data.nodes.map(node => ({
      id: node.id, x: node.x, y: node.y, color: node.color,
      size: node.chapter ? 4 : 9,
    })));
    edges = new vis.DataSet(data.edges.map(edge => ({
      ...edge, width: edge.reference ? .65 : .8,
      color: {color: edge.color, opacity: edge.reference ? .38 : .63},
    })));
    network = new vis.Network(canvas, {nodes, edges}, {
      physics: false,
      nodes: {shape: 'dot', borderWidth: 0},
      edges: {smooth: false},
      interaction: {hover: true, zoomView: false},
    });
    network.on('click', ({nodes: selected}) => {
      if (selected.length) show(selected[0]);
    });
    network.on('hoverNode', ({node}) => {
      canvas.setAttribute('aria-label', entries.get(node).label);
    });
    for (const button of document.querySelectorAll('[data-flower-zoom]')) {
      button.addEventListener('click', () => {
        const factor = Number(button.dataset.flowerZoom);
        if (factor) network.moveTo({scale: network.getScale() * factor});
        else network.fit();
      });
    }
    applyFilters();
  }

  search.addEventListener('input', () => {
    results.replaceChildren();
    const term = search.value.trim().toLocaleLowerCase('fr');
    if (term.length < 2) return;
    const matches = data.nodes.filter(node => node.label.toLocaleLowerCase('fr').includes(term)).slice(0, 10);
    for (const node of matches) {
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = node.url;
      link.textContent = node.label;
      item.append(link);
      results.append(item);
    }
  });
  for (const radio of document.querySelectorAll('input[name="graphe-vue"]')) radio.addEventListener('change', mount);
  for (const input of [...families, leafControl, referenceControl]) input.addEventListener('change', applyFilters);
  mount();
})();
