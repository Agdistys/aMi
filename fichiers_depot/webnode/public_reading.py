"""Build stable public editions and static excerpts for Webnode."""
from html import escape, unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
import re

PAGES = 'https://agdistys.github.io/aMi/'
REGISTER = 'annexes/Registre_en_ligne.html'
UNION = 'ami-lunion-du-tout'
BAREME = PAGES + UNION + '/bareme/'
BAREME_LABEL = 'Lire les Barèmes et la Grille de Score'
BAREME_LINK = f'<a href="{BAREME}">{BAREME_LABEL}</a>'
ALIASES = {'ami-mesures-ia': 'ami-tests', 'metaconscience': 'ami-metamatrice',
           'lettre-ouverte': 'ami-citer-contester-contribuer'}
HEAD = re.compile(r'<head(?:\s[^>]*)?>', re.I)
CANONICAL = re.compile(r'<link\b[^>]*\brel=["\']canonical["\'][^>]*>', re.I)
TAG = re.compile(r'<(?:script|style|textarea)\b[^>]*>[\s\S]*?</(?:script|style|textarea)\s*>|<!--.*?-->|<[a-z][\w:-]*(?:[^>"\']|"[^"]*"|\'[^\']*\')*>', re.I | re.S)
ATTR = re.compile(r'(\b(?:href|src|action|poster|data)\s*=\s*)(["\'])(.*?)\2', re.I | re.S)
NAVBAR = re.compile(r'<nav\b[^>]*\bid=["\']amiBarre["\'][^>]*>[\s\S]*?</nav>', re.I)
ENCODED_NAVBAR = re.compile(
    r'&lt;nav\b(?:(?!&gt;).)*\bid=&quot;amiBarre&quot;(?:(?!&gt;).)*&gt;[\s\S]*?&lt;/nav&gt;'
)
LEGACY_NAV_LINKS = {
    'benchmark': 'ami-benchmark',
    'catalogue-des-outils-ami': 'ami-catalogue-des-outils',
    'ami-tests': 'ami-tests',
}
WEBNODE_NAV_ROUTES = {'ami-tests': 'ami-mesures-ia'}
SUBLIMATION_LINK = 'https://www.agdistys.fr/methodologie-sublimation/'
CURRENT_SUBLIMATION_LINK = 'https://www.agdistys.fr/sublimation/'
COMPACT_NAV_VOLUMES = {'ami-rencontre', 'ami-justice'}
COMPACT_NAV_CSS = """@media (hover:hover) and (pointer:fine) {
  #amiBarre#amiBarre .croix .porte,
  #amiBarre#amiBarre .tiroir[data-c="foret"] button.m {min-height:0!important}
}"""


def navbar_routes(routes):
    return {
        'files': {re.split(r'_V[0-9]', path, maxsplit=1)[0]: slug for slug, path in routes.items()},
        'pages': {slug: slug for slug in routes},
        'legacy': LEGACY_NAV_LINKS,
        'webnode': WEBNODE_NAV_ROUTES,
    }


def without_door_titles(nav):
    def button(match):
        tag = match[0]
        if not re.search(r'\bclass=["\'][^"\']*\bporte\b', tag):
            return tag
        return re.sub(r'\s+title=(["\']).*?\1', '', tag)

    return re.sub(r'<button\b[^>]*>', button, nav)


def stable_navbar(html, routes, target):
    def link(match):
        if match[1].split('=')[0].strip().lower() != 'href':
            return match[0]
        value = unescape(match[3])
        if value.startswith(('#', '?')):
            return match[0]
        url = urlsplit(urljoin(PAGES + target, value))
        if url.netloc == 'agdistys.github.io' and url.path.startswith('/aMi/'):
            relative = url.path.removeprefix('/aMi/')
            slug = routes['files'].get(re.split(r'_V[0-9]', relative, maxsplit=1)[0])
            slug = slug or routes['pages'].get(relative.strip('/'))
        elif url.netloc in {'agdistys.fr', 'www.agdistys.fr'}:
            slug = routes['legacy'].get(url.path.strip('/'))
        else:
            slug = None
        if not slug:
            return match[0]
        suffix = ('?' + url.query if url.query else '') + ('#' + url.fragment if url.fragment else '')
        return match[1] + match[2] + escape(href(slug) + suffix, quote=True) + match[2]

    return NAVBAR.sub(lambda m: ATTR.sub(link, without_door_titles(m[0])), html)


class Excerpt(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.tag = ''
        self.words = []
        self.blocks = []
        self.title = ''
        self.description = ''

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'template', 'svg', 'nav', 'footer'}:
            self.skip += 1
        if self.skip:
            return
        values = dict(attrs)
        if tag == 'meta' and values.get('name') == 'description':
            self.description = values.get('content', '')
        if not self.tag and tag in {'title', 'h1', 'h2', 'h3', 'p', 'summary'}:
            self.tag, self.words = tag, []
        if tag == 'br' and self.tag:
            self.words.append(' ')

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'template', 'svg', 'nav', 'footer'} and self.skip:
            self.skip -= 1
        if self.skip or tag != self.tag:
            return
        value = ' '.join(''.join(self.words).split())
        if tag == 'title':
            self.title = value
        elif len(value) >= 20:
            self.blocks.append((tag, value))
        self.tag = ''

    def handle_data(self, data):
        if self.tag and not self.skip:
            self.words.append(data)


def href(slug):
    return PAGES + ('' if slug == 'ami' else slug + '/')


def canonicalize(html, slug):
    canonical = f'<link rel="canonical" href="{href(slug)}">'
    if match := CANONICAL.search(html[:16000]):
        return html[:match.start()] + canonical + html[match.end():]
    if head := HEAD.search(html[:16000]):
        return html[:head.end()] + canonical + html[head.end():]
    return canonical + '\n' + html


def relocate(html, target):
    original = PAGES + target

    def attr(match):
        value = unescape(match[3])
        if not value or value.startswith(('#', '?', '//')) or urlsplit(value).scheme:
            return match[0]
        return match[1] + match[2] + escape(urljoin(original, value), quote=True) + match[2]

    def tag(match):
        value = match[0]
        if value.startswith('<!--') or re.match(r'<(?:style|textarea)\b', value, re.I):
            return value
        if re.match(r'<script\b', value, re.I):
            opening, separator, rest = value.partition('>')
            if target == REGISTER:
                rest = rest.replace("new URL('./registre-paquets/'+name,document.baseURI)",
                                    "new URL('../annexes/registre-paquets/'+name,document.baseURI)")
            return ATTR.sub(attr, opening) + separator + rest
        return ATTR.sub(attr, value)

    return TAG.sub(tag, html)


def from_markdown(path):
    lines = path.read_text().splitlines()
    start = next((i for i, line in enumerate(lines[1:], 1) if re.match(r'^#{1,3} \S', line)), 4)
    return [('h2' if line.startswith('#') else 'p', line.strip().lstrip('#').strip())
            for line in lines[start:] if line.strip() and not re.fullmatch(r'[-–—_=* ]+', line)]


def excerpt(blocks, limit):
    parts, used = [], 0
    for tag, text in blocks:
        if used + len(text) > limit:
            if not parts:
                parts.append(f'<p>{escape(text[:limit].rsplit(" ", 1)[0])}…</p>')
            break
        tag = 'h3' if tag in {'h1', 'h2', 'h3'} else 'p'
        parts.append(f'<{tag}>{escape(text)}</{tag}>')
        used += len(text)
    return '\n'.join(parts)


STATIC_STYLE = """<style>
.ami-lecture-directe{box-sizing:border-box;max-width:68rem;margin:1.25rem auto;padding:1rem clamp(.75rem,3vw,1.5rem);color:#f2e5cd;background:#101018;border:1px solid #745923;border-radius:.55rem;text-align:left;hyphens:none}
.ami-lecture-directe :is(h2,h3,a,summary){color:#ffd06a}.ami-lecture-directe summary{cursor:pointer}
.ami-lecture-directe h2{margin:.1rem 0 .65rem;font-size:clamp(1.25rem,4vw,1.85rem);line-height:1.2}
.ami-lecture-directe p{margin:.4rem 0}.ami-lecture-directe a{text-decoration:underline}
[data-ami-public-block]:has([data-ami-mounted=true],[data-index-mounted=true],#ami-astroglobe-webnode[data-ready],[data-ami-annex-mounted=true])>.ami-lecture-directe{display:none}
</style>"""


def alternate_markdown(reading):
    return f'<link rel="alternate" type="text/markdown" title="Version Texte" href="{escape(reading, quote=True)}">'


def direct_reading(reading, slug):
    label = 'Version Texte intégrale (Markdown)' if reading.endswith('.md') else 'Index de Lecture'
    url = escape(reading, quote=True)
    extra = f' · {BAREME_LINK}' if slug == UNION else ''
    return (f'<p class="ami-source-directe" style="box-sizing:border-box;max-width:68rem;margin:.45rem auto;'
            f'padding-inline:clamp(.75rem,3vw,1.5rem);font:normal .9rem/1.5 system-ui,sans-serif;text-align:left">'
            f'{label} : <a style="text-decoration:underline;overflow-wrap:anywhere;hyphens:none" href="{url}">{url}</a>{extra}</p>\n')


def webnode_block(bootstrap, title, description, opening, slug, direct):
    description = f'<p>{escape(description)}</p>' if description else ''
    opening = f'<details><summary>Extrait du Volume</summary>{opening}</details>' if opening else ''
    return (f'<div data-ami-public-block>{STATIC_STYLE}\n<article class="ami-lecture-directe">'
            f'<h2>{escape(title)}</h2>{description}<p><a href="{href(slug)}">Lire le Volume</a></p>'
            f'{opening}</article>\n{direct}{bootstrap}\n</div>\n')


def publish_union_bareme(alias, html, target):
    """Expose both source grids on a stable, script-free reading page."""
    card = re.search(r'(<div class="cm2-card" id="cm2-bareme">[\s\S]+?)\s*(?=<div class="cm2-card"(?:\s|>))', html)
    if not card or not card[1].endswith('</div>') or '✍️ barème de travail · 🔍 à éprouver' not in card[1]:
        raise ValueError('Le Barème de la Charte Mathématique est introuvable ou incomplet.')
    score = re.search(
        r'<section id="grille-score">\s*<details[^>]*><summary>.*?</summary>'
        r'<div class="u31-corps">(.*?)</div></details></section>', html, re.S,
    )
    if not score or not all(term in score[1] for term in ('C_grille', 'NON_REPONDU', 'Statut de cette grille')):
        raise ValueError('La Grille de Score est introuvable ou incomplète.')
    def clean(block):
        return re.sub(r'<span class="(?:u35-term|df)"[^>]*>', '<span>', block)
    version = re.search(r'_V(\d+)', target)[1]
    directory = alias / 'bareme'
    directory.mkdir(exist_ok=True)
    title = 'Barèmes et Grille de Score · L’Union du TouT'
    (directory/'index.html').write_text(f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="Deux extraits de L’Union du TouT : le barème de travail I, U, P (0 à 5) et la grille de score C_grille (dix items de 0 à 3).">
<link rel="canonical" href="{BAREME}">
{alternate_markdown(href(UNION) + 'texte.md')}
<style>
:root{{--gris:#d8cdbb;--turquoise:#75e1e0;color-scheme:dark;background:#09090e;color:#f1e6d3;font:1rem/1.65 system-ui,sans-serif;hyphens:none}}
body{{margin:0}}main{{max-width:67rem;margin:auto;padding:clamp(1rem,4vw,2.5rem)}}
h1,h2,h3,h4,a,th,.cm2-lab{{color:#ffd06a}}
h1{{font:700 clamp(1.75rem,5vw,2.8rem)/1.15 Georgia,serif}}
.cm2-lab{{font-weight:700}}.cm2-card{{padding-block:1rem;border-block:1px solid #745923}}
.cm2-tw,.tw{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;text-align:start}}
td,th{{padding:.65rem;vertical-align:top;border:1px solid #745923;text-align:start}}
.cm2-note,.note,.card,.eqbox{{margin-block:1rem;padding:.6rem .9rem;border-inline-start:2px solid #ffd06a;background:#15131b}}
.g2{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem}}
a:focus-visible{{outline:2px solid currentColor;outline-offset:3px}}
@media(max-width:640px){{.g2{{grid-template-columns:1fr}}table{{min-width:36rem}}}}
</style></head><body><main>
<h1>{title}</h1>
<p>Agdistys · Diane Serant · Deux extraits de L’Union du TouT V{version}. Les deux grilles ont des usages et des échelles distincts.</p>
<p><a href="{href(UNION)}">Ouvrir L’Union du TouT</a> · <a href="{href(UNION)}texte.md">Lire la Version Texte complète</a></p>
<ul>
<li><a href="#cm2-bareme">Le Barème de la Charte Mathématique</a> : niveaux 0 à 5 pour I, U et P.</li>
<li><a href="#grille-score">La Grille de Score</a> : dix items cotés de 0 à 3 pour comparer deux moments avec C_grille.</li>
</ul>
<section aria-labelledby="titre-bareme"><h2 id="titre-bareme">Le Barème de la Charte Mathématique · I, U et P</h2>
{clean(card[1])}</section>
<section id="grille-score"><h2>La Grille de Score · C_grille</h2>
{clean(score[1])}</section>
<p>Licence <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.fr">CC BY-SA 4.0</a>.</p>
</main></body></html>
''', encoding='utf-8')


def union_reading_links(html):
    marker = '<nav class="ami-fil-tome-v1"'
    position = html.index(marker)
    link = f'<p class="ami-bareme-link" style="text-align:center;padding:.55rem 1rem;margin:0">{BAREME_LINK}</p>\n'
    return html[:position] + link + html[position:]


def publish(source, site, routes, index, bootstrap):
    directory = site/'webnode/blocs'
    directory.mkdir(parents=True, exist_ok=True)
    public_routes = {'ami': index, **routes}
    navigation = navbar_routes(public_routes)
    entries = []
    for slug, path in public_routes.items():
        target = REGISTER if slug == 'ami-registre' else path
        built = site/target
        html = canonicalize(built.read_text(), slug)
        if slug in {'ami-initiation', 'ami-lunion-du-tout'}:
            html = html.replace(f'href="{SUBLIMATION_LINK}"', f'href="{CURRENT_SUBLIMATION_LINK}"')
        summary = Excerpt()
        summary.feed(html)
        title = summary.title or next((text for tag, text in summary.blocks if tag == 'h1'), slug)
        title = re.sub(r'\s+· Protocole de ConScience aMi$', '', title)
        md = (source/path).with_suffix('.md')
        alias = site/slug
        alias.mkdir(exist_ok=True)
        reading, blocks = None, summary.blocks
        if md.is_file():
            (alias/'texte.md').write_bytes(md.read_bytes())
            reading = PAGES + slug + '/texte.md'
            blocks = from_markdown(md)
            (directory/(slug+'-en-tete.txt')).write_text(alternate_markdown(reading)+'\n', encoding='utf-8')
        elif slug == 'ami-registre':
            reading = PAGES + 'annexes/Registre_Index_Lecture.html'
        direct = direct_reading(reading, slug) if reading else ''
        if direct:
            (directory/(slug+'-lecture.txt')).write_text(direct, encoding='utf-8')
        entries.append((slug, title, bool(direct), bool(reading and reading.endswith('.md'))))
        alias_html = relocate(stable_navbar(html, navigation, target), target)
        if reading and reading.endswith('.md'):
            alias_html = HEAD.sub(lambda match: match[0]+'\n'+alternate_markdown(reading)+'\n', alias_html, count=1)
        if slug in COMPACT_NAV_VOLUMES:
            alias_html = HEAD.sub(lambda match: match[0] + '\n<style>' + COMPACT_NAV_CSS + '</style>', alias_html, count=1)
        if slug == 'ami-astroglobe':
            alias_html = ENCODED_NAVBAR.sub(
                lambda match: escape(stable_navbar(unescape(match[0]), navigation, target), quote=True),
                alias_html,
                count=1,
            )
            preview = (f'<article><h1>{escape(title)}</h1><p><a href="{reading}">Lire la Version Texte</a></p>'
                       f'{excerpt(blocks, 4500)}</article>')
            alias_html = alias_html.replace('</body>', '<noscript>'+preview+'</noscript>\n</body>', 1)
        if slug == UNION:
            publish_union_bareme(alias, html, target)
            alias_html = union_reading_links(alias_html)
        (alias/'index.html').write_text(alias_html)
        if slug == 'ami':
            (site/'index.html').write_text(alias_html)
        (directory/(slug+'.txt')).write_text(webnode_block(
            bootstrap, title, summary.description, excerpt(blocks, 10500), slug, direct,
        ))
    for route, slug in ALIASES.items():
        (directory/(route+'.txt')).write_bytes((directory/(slug+'.txt')).read_bytes())
        for suffix in ('-lecture.txt', '-en-tete.txt'):
            fragment = directory/(slug+suffix)
            if fragment.is_file():
                (directory/(route+suffix)).write_bytes(fragment.read_bytes())
        _, title, direct, head = next(entry for entry in entries if entry[0] == slug)
        entries.append((route, f'{title} (adresse Webnode : {route})', direct, head))
    rows = '\n'.join(
        f'<li><strong>{escape(title)}</strong> : '
        + (f'<a href="{slug}-lecture.txt">Ligne à ajouter</a> · ' if direct else '')
        + f'<a href="{slug}.txt">Bloc complet</a>'
        + (f' · <a href="{slug}-en-tete.txt">Balise pour l’en-tête</a>' if head else '')
        + '</li>'
        for slug, title, direct, head in entries
    )
    (directory/'index.html').write_text(f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Codes Webnode · aMi</title><meta name="robots" content="noindex">
<style>:root{{color-scheme:dark;background:#101018;color:#f2e5cd;font:1rem/1.65 system-ui,sans-serif}}main{{max-width:68rem;margin:2rem auto;padding-inline:1rem}}a{{color:#ffd06a}}li{{margin:.5rem 0}}</style>
</head><body><main>
<h1>Codes Webnode · aMi</h1>
<p><strong>Ligne à ajouter :</strong> colle ce code HTML à côté du volume déjà installé. Il affiche l’adresse de lecture complète.</p>
<p><strong>Bloc complet :</strong> à utiliser quand tu installes ou remplaces tout le bloc du volume. Il comprend déjà la ligne de lecture.</p>
<p><strong>Balise pour l’en-tête :</strong> facultative, à ajouter dans les paramètres SEO de la page correspondante.</p>
<ul>{rows}</ul></main></body></html>
''', encoding='utf-8')
