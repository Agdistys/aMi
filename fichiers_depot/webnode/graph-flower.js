(function () {
  const canvas = document.getElementById('fleur-canvas');
  if (!window.vis || !canvas) return;
  const data = JSON.parse(document.getElementById('fleur-data').textContent);
  const colors = new Map(data.nodes.map(node => [node.id, node.color]));
  const types = new Map(data.nodes.map(node => [node.id, node.type]));
  const nodes = new vis.DataSet(data.nodes.map((node, index) => ({
    id: node.id,
    label: node.label,
    title: node.title,
    color: {background: colors.get(node.id), border: colors.get(node.id)},
    x: 30 * Math.sqrt(index) * Math.cos(index * 2.4),
    y: 30 * Math.sqrt(index) * Math.sin(index * 2.4),
    size: node.type === 'index' ? 18 : 9,
  })));
  const edges = new vis.DataSet(data.edges);
  const flower = document.getElementById('graphe-vue-fleur');
  const controls = document.querySelectorAll('input[name="graphe-vue"]');
  let network;

  function showFlower() {
    if (!flower.checked) return;
    if (network) {
      network.redraw();
      return;
    }
    canvas.hidden = false;
    network = new vis.Network(canvas, {nodes, edges}, {
      autoResize: true,
      interaction: {hover: true, zoomView: false},
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -60,
          centralGravity: 0.005,
          springLength: 120,
          springConstant: 0.08,
          damping: 0.4,
          avoidOverlap: 0.8,
        },
        stabilization: {iterations: 200, fit: true},
      },
      nodes: {shape: 'dot', font: {face: 'system-ui', size: 15, color: '#f2e5cd', strokeWidth: 3, strokeColor: '#101019'}},
      edges: {smooth: {type: 'continuous', roundness: 0.2}},
    });
    network.once('stabilized', () => network.setOptions({physics: false}));
    network.on('click', ({nodes: selected}) => {
      if (!selected.length) return;
      const link = document.createElement('a');
      link.setAttribute('href', '#' + selected[0]);
      canvas.append(link);
      link.click();
      link.remove();
    });
    canvas.closest('figure').classList.add('canvas-active');
    document.getElementById('fleur-ajuster').hidden = false;
  }

  function updateLayers() {
    const volumes = document.getElementById('fleur-volumes').checked;
    const annexes = document.getElementById('fleur-annexes').checked;
    const indexLinks = document.getElementById('fleur-index').checked;
    const hidden = id => types.get(id) === 'volume' ? !volumes : types.get(id) === 'annexe' && !annexes;
    nodes.update(data.nodes.map(node => ({id: node.id, hidden: hidden(node.id)})));
    edges.update(data.edges.map(edge => ({
      id: edge.id,
      hidden: hidden(edge.from) || hidden(edge.to) || (edge.relation === 'indexe' && !indexLinks),
    })));
  }
  for (const input of controls) input.addEventListener('change', showFlower);
  for (const input of document.querySelectorAll('.graph-flower input')) input.addEventListener('change', updateLayers);
  document.getElementById('fleur-ajuster').addEventListener('click', () => network.fit());
  showFlower();
})();
