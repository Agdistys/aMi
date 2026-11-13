"""Build stable public editions and static excerpts for Webnode."""
from html import escape, unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
import re

PAGES = 'https://agdistys.github.io/aMi/'
REGISTER = 'annexes/Registre_en_ligne.html'
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


def webnode_block(bootstrap, title, description, opening, slug, reading):
    text_label = 'Consulter l’Index de Lecture' if slug == 'ami-registre' else 'Lire la Version Texte'
    text_link = f' · <a href="{reading}">{text_label}</a>' if reading else ''
    description = f'<p>{escape(description)}</p>' if description else ''
    opening = f'<details><summary>Extrait du Volume</summary>{opening}</details>' if opening else ''
    return (f'<div data-ami-public-block>{STATIC_STYLE}\n<article class="ami-lecture-directe">'
            f'<h2>{escape(title)}</h2>{description}<p><a href="{href(slug)}">Lire le Volume</a>{text_link}</p>'
            f'{opening}</article>\n{bootstrap}\n</div>\n')


def publish(source, site, routes, index, bootstrap):
    directory = site/'webnode/blocs'
    directory.mkdir(parents=True, exist_ok=True)
    public_routes = {'ami': index, **routes}
    navigation = navbar_routes(public_routes)
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
        elif slug == 'ami-registre':
            reading = PAGES + 'annexes/Registre_Index_Lecture.html'
        alias_html = relocate(stable_navbar(html, navigation, target), target)
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
        (alias/'index.html').write_text(alias_html)
        if slug == 'ami':
            (site/'index.html').write_text(alias_html)
        (directory/(slug+'.txt')).write_text(webnode_block(
            bootstrap, title, summary.description, excerpt(blocks, 10500), slug, reading,
        ))
    for route, slug in ALIASES.items():
        (directory/(route+'.txt')).write_bytes((directory/(slug+'.txt')).read_bytes())
