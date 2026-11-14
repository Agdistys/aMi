"""Build a catalogue graph using only explicit links in the public reading editions."""

from html import escape
import json
from math import cos, sin, tau
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


def plot(graph):
    center = (360, 300)
    positions = {'lecture': center}
    for kind, rx, ry in (('volume', 320, 250), ('annexe', 180, 139)):
        group = [node for node in graph['noeuds'] if node['type'] == kind]
        for index, node in enumerate(group):
            angle = tau * (index / len(group) - .25)
            positions[node['id']] = (round(center[0] + rx * cos(angle)), round(center[1] + ry * sin(angle)))
    paths = []
    for link in graph['liens']:
        x1, y1 = positions[link['source']]
        x2, y2 = positions[link['cible']]
        paths.append(f'<line class="{link["relation"]}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
    marks = []
    for index, node in enumerate(graph['noeuds']):
        x, y = positions[node['id']]
        title = escape(node['titre'], quote=True)
        label = str(index) if index else 'aMi'
        radius = 15 if index else 25
        marks.append(
            f'<a href="#{node["id"]}" aria-label="{title}"><title>{title}</title>'
            f'<circle class="{node["type"]}" cx="{x}" cy="{y}" r="{radius}"/>'
            f'<text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="central">{label}</text></a>'
        )
    return '<svg viewBox="0 0 720 600" role="group" aria-label="Carte des éditions">' + ''.join(paths + marks) + '</svg>'


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


def publish_graph(site, entries, base_url, reading_page):
    """Write the JSON and its script-free public reader into the Pages build."""
    graph = make_graph(site, entries, base_url, reading_page)
    path = site / 'lecture'
    directory = path / 'graphe'
    directory.mkdir(parents=True, exist_ok=True)
    (path / 'graphe.json').write_text(json.dumps(graph, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
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
h1,h2,h3,a{{color:#ffd06a}}h1{{font:700 clamp(1.7rem,5vw,2.7rem)/1.15 Georgia,serif}}
figure{{margin:1.35rem 0;background:#14121b;border:1px solid #745923;border-radius:.7rem}}
figcaption{{padding:0 1rem 1rem}}svg{{display:block;width:min(100%,45rem);margin:auto}}
line.indexe{{stroke:#705832;stroke-width:.8}}line.cite{{stroke:#60c1c4;stroke-width:1;opacity:.6}}
circle.volume{{fill:#ffe19a}}circle.annexe{{fill:#85dadd}}circle.index{{fill:#fff4d2}}
svg a:is(:hover,:focus-visible) circle{{stroke:white;stroke-width:3}}svg text{{fill:#160e05;font-size:14px;font-weight:700}}
ol{{padding-inline-start:2rem}}li{{padding:.7rem .8rem;scroll-margin-top:1rem}}
li:nth-child(odd),li:target{{background:#16131b}}li:target{{outline:1px solid #ffd06a}}
li h3,li p{{margin:.15rem 0}}a:focus-visible{{outline:2px solid currentColor;outline-offset:3px}}
</style></head><body><main>
<h1>{title}</h1>
<p><a id="lecture" href="{reading}">Index de Lecture</a> · <a href="{json_url}">Données JSON</a> · <a href="#editions">Liste des éditions</a></p>
<figure>
{plot(graph)}
<figcaption>Le centre représente l’Index de Lecture. L’ambre indique les volumes et le turquoise, les annexes. Les traits turquoise suivent les renvois relevés dans les Versions Texte. Les numéros correspondent à la liste ci-dessous.</figcaption>
</figure>
<h2 id="editions">Les éditions et leurs renvois</h2>
<ol>{edition_rows(graph)}</ol>
</main></body></html>
''', encoding='utf-8')
