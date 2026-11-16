"""Build a catalogue graph using only explicit links in the public reading editions."""

from html import escape
import json
from itertools import combinations
from pathlib import Path
from math import cos, hypot, sin, sqrt, tau
import re
from urllib.parse import unquote, urljoin, urlsplit


SLUG = re.compile(r'ami(?:-[a-z0-9]+)*')
MARKDOWN_LINK = re.compile(r'(?<!!)\[[^]\n]*\]\(\s*<?([^\s>)]+)|^\s{0,3}\[[^]\n]+\]:\s*<?([^\s>]+)', re.M)
MARKDOWN_IMAGE = re.compile(r'!\[[^]\n]*\]\([^\n)]*\)')
PUBLIC_URL = re.compile(r'https?://[^\s<>"\'\])]+')
FENCE = re.compile(r'^\s{0,3}(`{3,}|~{3,})')
WEBNODE_ALIASES = {
    'ami-mesures-ia': 'ami-tests',
    'metaconscience': 'ami-metamatrice',
    'lettre-ouverte': 'ami-citer-contester-contribuer',
}


def url_key(url):
    parts = urlsplit(url)
    if parts.scheme not in {'http', 'https'} or parts.username or parts.password:
        return None
    return parts.netloc.lower(), unquote(parts.path).rstrip('/')


def public_link_index(nodes, base_url):
    base = urlsplit(base_url)
    accepted = {}
    for node in nodes:
        slug = node['id']
        for field in ('url', 'source', 'lecture', 'markdown'):
            if node.get(field):
                key = url_key(node[field])
                if key:
                    accepted[key] = slug
                    host, path = key
                    if host == base.netloc and path.startswith(base.path):
                        accepted['ami.agdistys.fr', '/' + path.removeprefix(base.path)] = slug
        if slug == 'lecture':
            continue
        accepted[url_key(urljoin(base_url, slug + '/'))] = slug
        routes = [slug, *(alias for alias, target in WEBNODE_ALIASES.items() if target == slug)]
        for host in ('www.agdistys.fr', 'agdistys.fr'):
            for route in routes:
                accepted[host, '/' + route] = slug
    return accepted


def markdown_links(path):
    fence = None
    with path.open(encoding='utf-8') as source:
        for line in source:
            if marker := FENCE.match(line):
                value = marker[1]
                if not fence:
                    fence = value
                elif fence[0] == value[0] and len(value) >= len(fence) and not line[marker.end():].strip():
                    fence = None
                continue
            if fence:
                continue
            line = MARKDOWN_IMAGE.sub('', re.sub(r'`+[^`\n]+`+', '', line))
            for inline, reference in MARKDOWN_LINK.findall(line):
                yield inline or reference
            for url in PUBLIC_URL.findall(line):
                yield url.rstrip('.,;:')


def make_graph(site, entries, base_url, reading_page):
    if not reading_page.startswith(base_url) or not url_key(reading_page):
        raise ValueError('Adresse de l’Index de Lecture hors du corpus public.')
    nodes = [{'id': 'lecture', 'titre': 'Index de Lecture', 'url': reading_page, 'type': 'index'}]
    for entry in entries:
        slug = entry['slug']
        if not SLUG.fullmatch(slug) or any(node['id'] == slug for node in nodes):
            raise ValueError(f'Identifiant de lecture invalide ou en double : {slug}')
        source_url = entry['source_url']
        source_path = urlsplit(source_url).path
        node = {
            'id': slug,
            'titre': entry['title'],
            'url': entry['page_url'],
            'source': source_url,
            'type': 'annexe' if '/annexes/' in source_path else 'volume',
        }
        if entry['reading_url'] and entry['reading_url'] != entry['page_url']:
            node['lecture'] = entry['reading_url']
        if entry['markdown'] and slug != 'ami-miroir':
            node['markdown'] = urljoin(base_url, slug + '/texte.md')
        for field in ('url', 'source', 'lecture', 'markdown'):
            if field in node and (not node[field].startswith(base_url) or not url_key(node[field])):
                raise ValueError(f'Adresse de lecture hors du corpus public : {slug}/{field}')
        nodes.append(node)

    accepted = public_link_index(nodes, base_url)
    links = {('lecture', node['id'], 'indexe') for node in nodes[1:]}
    for entry in entries:
        slug = entry['slug']
        if not entry['markdown'] or slug == 'ami-miroir':
            continue
        path = site / slug / 'texte.md'
        for value in markdown_links(path):
            if value.startswith(('#', '?')):
                continue
            key = url_key(urljoin(entry['source_url'], value))
            target = accepted.get(key)
            if target and target != slug:
                links.add((slug, target, 'cite'))

    return {
        'schema': 1,
        'titre': 'Graphe du corpus public aMi',
        'provenance': 'Catalogue public et renvois vers ses éditions dans les Versions Texte publiées.',
        'relations': {
            'indexe': 'L’Index de Lecture donne accès à cette édition.',
            'cite': 'Une adresse de la Version Texte renvoie à cette autre édition.',
        },
        'noeuds': nodes,
        'liens': [
            {'source': source, 'cible': target, 'relation': relation}
            for source, target, relation in sorted(links)
        ],
    }


def _tome(node):
    if node['type'] == 'annexe':
        return 9
    if node['id'] == 'ami-karma':
        return 6
    match = re.search(r'(?<!\d)([0-8])(?:\.\d| ·)', node['titre'])
    return int(match[1]) if match else 0


FAMILIES = (
    ('Le Seuil', '#68a9e4'), ('Le Soi', '#ff9d60'),
    ('Le Monde', '#8bd082'), ('Le Lien', '#f286ac'),
    ('Le Sens', '#e0c965'), ('Le Temps', '#ab97ed'),
    ('Le Karma', '#66cfbf'), ('La Maîtrise', '#f18b76'),
    ('Évolution et Maturation', '#e8a7d9'), ('Annexes', '#85dadd'),
)


def force_positions(graph):
    nodes = graph['noeuds']
    ids = [node['id'] for node in nodes]
    families = {node['id']: _tome(node) for node in nodes[1:]}
    positions = {
        slug: [22 * sqrt(i) * cos(i * 2.4), 22 * sqrt(i) * sin(i * 2.4)]
        for i, slug in enumerate(ids)
    }
    pairs = list(combinations(ids, 2))
    edges = [link for link in graph['liens'] if link['relation'] == 'cite']
    for step in range(180):
        moves = {slug: [-x * .015, -y * .015] for slug, (x, y) in positions.items()}
        for first, second in pairs:
            x, y = positions[first]
            dx, dy = x - positions[second][0], y - positions[second][1]
            distance = max(hypot(dx, dy), 1)
            force = 450 / distance**2
            if first in families and families[first] == families.get(second):
                force -= max(0, distance - 35) * .011 / distance
            for axis, delta in enumerate((dx, dy)):
                moves[first][axis] += delta * force
                moves[second][axis] -= delta * force
        for edge in edges:
            first, second = edge['source'], edge['cible']
            dx, dy = (a - b for a, b in zip(positions[first], positions[second]))
            distance = max(hypot(dx, dy), 1)
            force = (distance - 49) * .06 / distance
            for axis, delta in enumerate((dx, dy)):
                moves[first][axis] -= delta * force
                moves[second][axis] += delta * force
        cooling = 1 - .8 * step / 180
        for slug in ids[1:]:
            for axis in (0, 1):
                positions[slug][axis] += max(-9, min(9, moves[slug][axis])) * cooling

    extent_x = max(1, max(abs(x) for x, _ in positions.values()))
    extent_y = max(1, max(abs(y) for _, y in positions.values()))
    scale = min(320 / extent_x, 260 / extent_y)
    return {slug: (round(360 + x * scale), round(300 + y * scale))
            for slug, (x, y) in positions.items()}


def plot(graph, *, flower=False):
    center = (360, 300)
    positions = {'lecture': center}
    if flower:
        positions = force_positions(graph)
    else:
        for kind, rx, ry in (('volume', 320, 250), ('annexe', 180, 139)):
            group = [node for node in graph['noeuds'] if node['type'] == kind]
            for index, node in enumerate(group):
                angle = tau * (index / len(group) - .25)
                positions[node['id']] = (round(center[0] + rx * cos(angle)), round(center[1] + ry * sin(angle)))
    types = {node['id']: node['type'] for node in graph['noeuds']}
    paths = []
    for link in graph['liens']:
        x1, y1 = positions[link['source']]
        x2, y2 = positions[link['cible']]
        layers = ' '.join({'layer-' + types[link[key]] for key in ('source', 'cible')})
        paths.append(f'<line class="{link["relation"]} {layers}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
    marks = []
    for index, node in enumerate(graph['noeuds']):
        x, y = positions[node['id']]
        title = escape(node['titre'], quote=True)
        label = str(index) if index else 'aMi'
        radius = 15 if index else 25
        color = FAMILIES[_tome(node)][1] if flower and index else '#fff4d2'
        fill = f' style="fill:{color}"' if flower else ''
        marks.append(
            f'<a href="#{node["id"]}" class="layer-{node["type"]}" aria-label="{title}"><title>{title}</title>'
            f'<circle class="{node["type"]}" cx="{x}" cy="{y}" r="{radius}"{fill}/>'
            f'<text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="central">{label}</text></a>'
        )
    label = 'Fleur synaptique' if flower else 'Carte des éditions'
    return f'<svg viewBox="0 0 720 600" role="group" aria-label="{label}">' + ''.join(paths + marks) + '</svg>'


def edition_rows(graph):
    nodes = {node['id']: node for node in graph['noeuds']}
    cited = {slug: [] for slug in nodes}
    for link in graph['liens']:
        if link['relation'] == 'cite':
            cited[link['source']].append(nodes[link['cible']])
    rows = []
    for node in graph['noeuds'][1:]:
        slug = node['id']
        page = f'<a href="{escape(node["url"], quote=True)}">Ouvrir l’édition</a>'
        label = 'Lire la Version Texte' if node.get('markdown') else 'Accès en lecture'
        reading = (f' · <a href="{escape(node["lecture"], quote=True)}">{label}</a>'
                   if node.get('lecture') else '')
        other = ', '.join(f'<a href="#{item["id"]}">{escape(item["titre"])}</a>' for item in cited[slug])
        references = f'<p>Renvois publics de la Version Texte · {other}</p>' if other else ''
        rows.append(f'<li id="{slug}"><h3>{escape(node["titre"])}</h3><p>{page}{reading}</p>{references}</li>')
    return '\n'.join(rows)


def synaptic_flower(assets, graph, base_url):
    data = json.loads((assets / 'fleur-synaptique-v002.json').read_text(encoding='utf-8'))
    known = {urlsplit(node[field]).path.removeprefix(urlsplit(base_url).path)
             for node in graph['noeuds'] for field in ('url', 'lecture') if field in node}
    ids = {node['id'] for node in data['nodes']}
    if len(ids) != len(data['nodes']) or any(
        edge['from'] not in ids or edge['to'] not in ids for edge in data['edges']
    ):
        raise ValueError('Nœuds ou renvois invalides dans la Fleur synaptique.')
    for node in data['nodes']:
        if not node.get('url'):
            continue
        url = urlsplit(node['url'])
        route = url.path.removeprefix('/')
        if url.scheme != 'https' or url.netloc != 'ami.agdistys.fr' or url.query or url.fragment or route not in known:
            raise ValueError(f'Lien hors du catalogue public : {node["id"]}')
        node['url'] = urljoin(base_url, route)
    return data


def publish_graph(site, entries, base_url, reading_page):
    """Write the JSON and its public reader into the Pages build."""
    graph = make_graph(site, entries, base_url, reading_page)
    path = site / 'lecture'
    directory = path / 'graphe'
    directory.mkdir(parents=True, exist_ok=True)
    (path / 'graphe.json').write_text(json.dumps(graph, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assets = Path(__file__).parent
    vendor = assets / 'vendor'
    vis = (vendor / 'vis-network-9.1.6.min.js').read_text(encoding='utf-8').split('//# sourceMappingURL=')[0]
    license_text = (vendor / 'vis-network-LICENSE-MIT').read_text(encoding='utf-8')
    flower_script = (assets / 'graph-flower.js').read_text(encoding='utf-8')
    flower_data = json.dumps({
        'nodes': [
            {'id': node['id'], 'title': escape(node['titre']), 'type': node['type'],
             'label': re.sub(r'^.*?\d[.]\d\s*·\s*', '', node['titre']).split(' — ')[0],
             'color': FAMILIES[_tome(node)][1] if index else '#ffd06a'}
            for index, node in enumerate(graph['noeuds'])
        ],
        'edges': [
            {'id': index, 'from': link['source'], 'to': link['cible'], 'relation': link['relation'],
             'color': '#69c5cb' if link['relation'] == 'cite' else '#4a412f',
             'arrows': {'to': {'enabled': link['relation'] == 'cite', 'scaleFactor': .5}}}
            for index, link in enumerate(graph['liens'])
        ],
    }, ensure_ascii=False).replace('<', r'\u003c')
    synaptic = synaptic_flower(assets, graph, base_url)
    synaptic_data = json.dumps(synaptic, ensure_ascii=False).replace('<', r'\u003c')
    synaptic_script = (assets / 'fleur-synaptique.js').read_text(encoding='utf-8')
    title = graph['titre']
    reading = escape(reading_page, quote=True)
    json_url = escape(urljoin(base_url, 'lecture/graphe.json'), quote=True)
    graph_url = escape(urljoin(base_url, 'lecture/graphe/'), quote=True)
    (directory / 'index.html').write_text(f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="La carte des éditions publiques aMi et des renvois de leurs Versions Texte.">
<link rel="canonical" href="{graph_url}">
<link rel="alternate" type="application/json" title="Graphe public aMi" href="{json_url}">
<style>
:root{{color-scheme:dark;background:#09090e;color:#f1e6d3;font:1rem/1.6 system-ui,sans-serif}}
body{{margin:0}}main{{max-width:65rem;margin:auto;padding:clamp(1rem,4vw,2.5rem)}}
h1,h2,h3,a{{color:#ffd06a}}h1{{font:700 clamp(1.7rem,5vw,2.7rem)/1.15 Georgia,serif;text-wrap:balance}}
.graph-header,.graph-controls,.graph-flower fieldset{{text-align:center}}
.graph-links{{display:flex;flex-wrap:wrap;justify-content:center;gap:.5rem 1rem;padding:0}}
.graph-links li{{padding:0;list-style:none;background:none}}
.graph-links a,.graph-choices>label,#fleur-ajuster{{display:inline-block;padding:.35rem .85rem;border:1px solid #745923;border-radius:2rem;background:#19151c;color:#ffd06a}}
.graph-choices>input:checked+label{{background:#ffd06a;color:#17121a}}
.graph-choices>input:focus-visible+label{{outline:2px solid #fff4d2;outline-offset:3px}}
.graph-choices>input{{position:absolute;width:1px;height:1px;opacity:0}}
.graph-controls,.graph-flower fieldset{{border:0;padding:.65rem;margin:0;min-width:0}}
.graph-controls legend{{margin-inline:auto;color:#f1e6d3}}
.graph-choices{{position:sticky;top:var(--ami-annex-standalone-top,0px);z-index:2;background:#09090e;padding:.4rem}}
#fleur-canvas{{height:clamp(400px,62vh,650px);background:#0c101a;border:1px solid #554524;border-radius:.65rem;margin:.5rem}}
.canvas-active>svg{{display:none}}
#fleur-ajuster{{cursor:pointer;margin:.35rem}}
#fleur-ajuster[hidden]{{display:none}}
figure{{margin:1.35rem 0;background:#14121b;border:1px solid #745923;border-radius:.7rem}}
figcaption{{padding:0 1rem 1rem}}svg{{display:block;width:min(100%,45rem);margin:auto}}
line.indexe{{stroke:#705832;stroke-width:.8}}line.cite{{stroke:#60c1c4;stroke-width:1;opacity:.6}}
circle.volume{{fill:#ffe19a}}circle.annexe{{fill:#85dadd}}circle.index{{fill:#fff4d2}}
.graph-flower:has(#fleur-volumes:not(:checked)) .layer-volume,
.graph-flower:has(#fleur-annexes:not(:checked)) .layer-annexe,
.graph-flower:has(#fleur-index:not(:checked)) .indexe{{display:none}}
.graph-flower .indexe{{opacity:.36}}
.graph-families{{display:flex;gap:.35rem 1rem;flex-wrap:wrap;padding:0;list-style:none}}
.graph-families li{{background:none;padding:0}}
svg :is(line,text){{pointer-events:none}}
svg a circle{{pointer-events:fill}}
.graph-controls label{{display:inline-block;padding:.25rem .85rem .25rem .2rem;cursor:pointer}}
.graph-controls:not(:has(#graphe-vue-orbite:checked)) .graph-orbits,
.graph-controls:not(:has(#graphe-vue-fleur:checked)) .graph-flower,
.graph-controls:not(:has(#graphe-vue-chapitres:checked)) .graph-chapters{{display:none}}
.chapter-layout{{display:grid;grid-template-columns:minmax(0,1fr) minmax(11rem,16rem);gap:.65rem;padding:.65rem}}
#fleur-synaptique-canvas{{height:clamp(420px,72vh,720px);background:#0e1019;border:1px solid #554524;border-radius:.65rem}}
.chapter-panel{{text-align:left;padding:.65rem;background:#191722;border:1px solid #554524;border-radius:.65rem;overflow-wrap:anywhere}}
.chapter-panel input[type=search]{{font:inherit;width:100%;box-sizing:border-box}}
.chapter-panel h3,.chapter-panel p{{margin:.45rem 0}}
.chapter-panel label{{display:block}}
.chapter-panel input[type=checkbox]{{accent-color:#ffca65}}
.chapter-panel button{{border:1px solid #745923;background:#211b23;color:#ffd06a;border-radius:.5rem;font:inherit;padding:.25rem .55rem;cursor:pointer}}
.chapter-panel ul{{padding-inline-start:1rem}}
.chapter-panel li{{padding:.1rem 0;background:none}}
@media(max-width:680px){{.chapter-layout{{grid-template-columns:minmax(0,1fr)}}}}
svg a:is(:hover,:focus-visible) circle{{stroke:white;stroke-width:3}}svg text{{fill:#160e05;font-size:14px;font-weight:700}}
ol{{padding-inline-start:2rem}}li{{padding:.7rem .8rem;scroll-margin-top:1rem}}
li:nth-child(odd),li:target{{background:#16131b}}li:target{{outline:1px solid #ffd06a}}
li h3,li p{{margin:.15rem 0}}a:focus-visible{{outline:2px solid currentColor;outline-offset:3px}}
</style></head><body><main>
<header class="graph-header"><h1>{title}</h1>
<ul class="graph-links"><li><a id="lecture" href="{reading}">Index de Lecture</a></li><li><a href="{json_url}">Données JSON</a></li><li><a href="#editions">Liste des éditions</a></li></ul></header>
<fieldset class="graph-controls"><legend>Disposition du graphe</legend>
<div class="graph-choices">
<input type="radio" name="graphe-vue" id="graphe-vue-orbite" aria-controls="vue-graphe-orbites"><label for="graphe-vue-orbite">Orbites</label>
<input type="radio" name="graphe-vue" id="graphe-vue-fleur" aria-controls="vue-graphe-reseau"><label for="graphe-vue-fleur">Réseau des éditions</label>
<input type="radio" name="graphe-vue" id="graphe-vue-chapitres" aria-controls="vue-graphe-chapitres" checked><label for="graphe-vue-chapitres">Fleur synaptique</label></div>
<div id="debut-vue-graphe" aria-hidden="true"></div>
<figure class="graph-chapters" id="vue-graphe-chapitres">
<div class="chapter-layout">
<div id="fleur-synaptique-canvas" role="img" aria-label="Fleur synaptique des sections publiques"></div>
<aside class="chapter-panel">
<label for="fleur-synaptique-recherche">Chercher un concept ou une édition</label>
<input type="search" id="fleur-synaptique-recherche">
<h3>Fiche</h3><div id="fleur-synaptique-fiche" aria-live="polite"><p>Clique sur un point pour ouvrir sa fiche.</p></div>
<p><button type="button" data-fs-zoom=".75" aria-label="Réduire">−</button>
<button type="button" data-fs-zoom="1.33" aria-label="Agrandir">+</button>
<button type="button" data-fs-zoom="0">Recentrer</button></p>
<details><summary>Familles</summary><div id="fleur-synaptique-familles"></div></details></aside>
</div>
<figcaption>Le protocole net · {len(synaptic['nodes'])} points et {len(synaptic['edges'])} liens. Les concepts partagés relient les éditions.</figcaption>
</figure>
<figure class="graph-orbits" id="vue-graphe-orbites">
{plot(graph)}
<figcaption>Le centre représente l’Index de Lecture. L’ambre indique les volumes et le turquoise, les annexes. Les traits turquoise suivent les renvois relevés dans les Versions Texte. Les numéros correspondent à la liste ci-dessous.</figcaption>
</figure>
<figure class="graph-flower" id="vue-graphe-reseau">
<fieldset><legend>Calques</legend>
<label><input type="checkbox" id="fleur-volumes" checked> Volumes</label>
<label><input type="checkbox" id="fleur-annexes" checked> Annexes</label>
<label><input type="checkbox" id="fleur-index" checked> Liens de l’Index</label>
</fieldset>
<div id="fleur-canvas" role="img" aria-label="Fleur synaptique interactive des éditions publiques" hidden></div>
<button type="button" id="fleur-ajuster" hidden>Recentrer la carte</button>
{plot(graph, flower=True)}
<figcaption>Les renvois rapprochent les nœuds. Les couleurs indiquent les familles.
<ul class="graph-families">{''.join(f'<li><span aria-hidden="true" style="color:{color}">●</span> {label}</li>' for label, color in FAMILIES)}</ul>
</figcaption>
</figure>
</fieldset>
<h2 id="editions">Les éditions et leurs renvois</h2>
<ol>{edition_rows(graph)}</ol>
</main>
<script id="fleur-data" type="application/json">{flower_data}</script>
<script>/* {license_text} */
{vis}</script>
<script>{flower_script}</script>
<script id="fleur-synaptique-data" type="application/json">{synaptic_data}</script>
<script>{synaptic_script}</script>
<script>
if (window === window.parent) {{
  document.documentElement.style.overflowAnchor = 'none';
  const choices = document.querySelector('.graph-choices');
  const start = document.getElementById('debut-vue-graphe');
  const positions = new Map();
  let current = choices.querySelector('input:checked').id;
  choices.addEventListener('change', event => {{
    const dock = choices.getBoundingClientRect().bottom + 8;
    const position = start.getBoundingClientRect().top;
    positions.set(current,Math.max(0,dock-position));
    current = event.target.id;
    const figure = document.getElementById(event.target.getAttribute('aria-controls'));
    const saved = Math.min(positions.get(current) ?? 0,Math.max(0,figure.offsetHeight-48));
    window.scrollBy({{top:position-dock+saved,behavior:'instant'}});
  }});
}}
</script>
</body></html>
''', encoding='utf-8')
