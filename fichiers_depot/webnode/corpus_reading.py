"""Assemble the reading editions from the versions already published by Pages."""

from hashlib import sha256
from html import escape
from urllib.parse import urljoin
from xml.etree import ElementTree

from markdown_reading import render_markdown
from public_graph import publish_graph


READING_PATH = 'lecture/'
CORPUS_PATH = READING_PATH + 'protocole-aMi.md'

STYLE = """
:root{color-scheme:dark;background:#0c0c13;color:#ede5d7;font:1rem/1.65 system-ui,sans-serif;hyphens:none;overflow-wrap:anywhere}
body{margin:0}main{box-sizing:border-box;max-width:74rem;margin:auto;padding:clamp(1rem,5vw,3.5rem)}
h1,h2,h3,h4,h5,h6,a{color:#ffd06a}
h1{font:700 clamp(1.85rem,5vw,3.05rem)/1.15 Georgia,serif}
h2{margin-top:2rem}a{overflow-wrap:anywhere}a:focus-visible{outline:2px solid currentColor;outline-offset:3px}
.ami-lecture-reperes{padding:.35rem 1rem;border-inline-start:2px solid #c79840;background:#15141e}
.ami-lecture-links{display:flex;flex-wrap:wrap;gap:.4rem 1.2rem}
li{margin-block:.25rem}li span{color:#d6ccbc}
article img{max-width:100%;height:auto}pre{overflow:auto;padding:1rem;background:#191722}
.ami-reading-table{overflow-x:auto}table{border-collapse:collapse;max-width:100%;overflow-wrap:normal}
td,th{text-align:start;vertical-align:top;border:1px solid #745923;padding:.45rem .65rem}
td.align-left,th.align-left{text-align:left}td.align-right,th.align-right{text-align:right}
td.align-center,th.align-center{text-align:center}
blockquote{margin-inline:0;padding-inline:1rem;border-inline-start:2px solid #c79840}
hr{border:0;border-top:1px solid #745923}
"""

ETHICS = (
    'La lecture du Protocole commence par le consentement : garder la possibilité de dire non, de demander un délai '
    'et de revenir sur un accord. Une absence de réponse ne vaut pas accord.',
    'Distinguer les faits sourcés, le vécu rapporté, les interprétations et les hypothèses. Pour une affirmation précise, '
    'citer le volume, sa version et le passage pertinent. Quand un passage manque, signaler la limite.',
    'Les grilles et équations décrivent des propositions de travail. Leur statut, leurs conditions de calcul et les cas '
    'où le résultat reste indéterminé se lisent dans chaque source.',
    'Pour contester ou proposer une correction, revenir au contexte et préciser quelle observation ferait réviser la conclusion.',
)

LICENSE = 'https://creativecommons.org/licenses/by-sa/4.0/deed.fr'


def link(url, label):
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def document(title, description, canonical, body, markdown=None):
    alternate = (f'<link rel="alternate" type="text/markdown" href="{escape(markdown, quote=True)}">'
                 if markdown else '')
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description, quote=True)}">
<link rel="canonical" href="{escape(canonical, quote=True)}">
{alternate}
<style>{STYLE}</style>
</head><body><main>
{body}
</main></body></html>
"""


def file_size(value):
    return f'{value / 1_000_000:.1f}'.replace('.', ',') + ' Mo'


def add_to_sitemap(path, urls):
    namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ElementTree.register_namespace('', namespace)
    tree = ElementTree.parse(path)
    root = tree.getroot()
    known = {element.text for element in root.findall(f'.//{{{namespace}}}loc')}
    for url in urls:
        if url not in known:
            entry = ElementTree.SubElement(root, f'{{{namespace}}}url')
            ElementTree.SubElement(entry, f'{{{namespace}}}loc').text = url
            known.add(url)
    ElementTree.indent(tree)
    tree.write(path, encoding='utf-8', xml_declaration=True)


def publish_corpus(site, entries, base_url):
    directory = site / READING_PATH
    directory.mkdir(exist_ok=True)
    reading_page = base_url + READING_PATH
    corpus_url = base_url + CORPUS_PATH
    registry = {entry['slug']: entry for entry in entries}
    contribution = registry['ami-citer-contester-contribuer']['page_url']
    md_entries = [entry for entry in entries if entry['markdown']]
    html_only = [entry for entry in entries if not entry['markdown']]
    sections = [
        '# Protocole de ConScience aMi · Corpus public pour la lecture',
        'Agdistys · Diane Serant. Compilation des Versions Texte des éditions publiques actives.',
        f'[Accueil de lecture]({reading_page}) · [Graphe public]({reading_page}graphe/) · [Licence CC BY-SA 4.0]({LICENSE})',
        '## Repères de lecture',
        *(f'- {item}' for item in ETHICS),
        f'[Citer · Contester · Contribuer]({contribution})',
        '## Périmètre',
        f'{len(md_entries)} Versions Texte sont reproduites intégralement. '
        f'{len(html_only)} éditions publiques sans export Markdown figurent au catalogue par lien, dont Miroir. '
        'Les pièces du Registre se consultent depuis son index public.',
        '## Éditions',
        *(f'- [{entry["title"]}]({entry["reading_url"]})' for entry in entries),
    ]
    urls = [reading_page, reading_page + 'graphe/']
    rows = []
    for entry in entries:
        slug = entry['slug']
        title = entry['title']
        page_url = entry['page_url']
        reading_url = entry['reading_url']
        if not entry['markdown']:
            rows.append(f'<li>{link(reading_url, title)} <span>· édition publique HTML</span></li>')
            continue
        source = site / slug / 'texte.md'
        raw = source.read_bytes()
        markdown = raw.decode('utf-8')
        markdown_url = urljoin(reading_url, '../texte.md')
        section = (
            f'## Édition · {title}\n\n'
            f'[Lecture HTML]({reading_url}) · [Version Texte]({markdown_url})\n\n'
            f'SHA-256 du fichier Markdown publié : `{sha256(raw).hexdigest()}`\n\n'
        )
        sections.append(section + markdown.rstrip('\n'))
        rows.append(f'<li>{link(reading_url, title)} · {link(markdown_url, "Markdown")}</li>')
        nav = (
            f'<nav class="ami-lecture-links" aria-label="Formats de lecture">{link(reading_page, "Accueil de lecture")}'
            f'{link(page_url, "Volume interactif")}{link(markdown_url, "Version Markdown")}</nav>'
        )
        prose = render_markdown(markdown, base_url=entry['source_url'])
        body = f'{nav}\n<article>{prose}</article>'
        output = site / slug / 'lecture'
        output.mkdir(exist_ok=True)
        (output / 'index.html').write_text(
            document(f'{title} · Version Texte', f'Version Texte de {title}, lisible en HTML sans JavaScript.',
                     reading_url, body, markdown_url),
            encoding='utf-8',
        )
        urls.append(reading_url)
    corpus = ('\n\n'.join(sections) + '\n').encode('utf-8')
    (site / CORPUS_PATH).write_bytes(corpus)

    ethics = '\n'.join(f'<li>{escape(item)}</li>' for item in ETHICS)
    catalogue = '\n'.join(rows)
    body = f"""
<h1>Lire le Protocole de ConScience aMi</h1>
<p>Agdistys · Diane Serant</p>
<section class="ami-lecture-reperes" aria-labelledby="reperes">
<h2 id="reperes">Entrée en matière éthique</h2>
<ul>{ethics}</ul>
<p>{link(contribution, 'Citer · Contester · Contribuer')}</p>
</section>
<h2>Accès au corpus</h2>
<p>{link(corpus_url, f'Télécharger les {len(md_entries)} Versions Texte réunies (Markdown, {file_size(len(corpus))})')}</p>
<p>Pour une question ciblée, ouvre l’édition concernée ci-dessous. Le fichier réuni peut dépasser la capacité de lecture d’un assistant en un seul passage.</p>
<p>{link(reading_page + 'graphe/', 'Explorer le graphe du corpus public')} · {link(reading_page + 'graphe.json', 'Graphe au format JSON')}</p>
<ul>{catalogue}</ul>
<p>{link(LICENSE, 'Licence CC BY-SA 4.0')}</p>
"""
    (directory / 'index.html').write_text(
        document('Lire le Protocole de ConScience aMi', 'Cadre éthique, Versions Texte et graphe du corpus public.',
                 reading_page, body, corpus_url),
        encoding='utf-8',
    )
    publish_graph(site, entries, base_url, reading_page)
    add_to_sitemap(site / 'sitemap.xml', urls)
