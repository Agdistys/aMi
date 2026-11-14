#!/usr/bin/env python3
"""Generate immutable native Webnode adapters and a stable catalogue for GitHub Pages."""
from argparse import ArgumentParser
from base64 import b64encode
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
import json
import re
from public_reading import (
    BAREME, BAREME_LABEL, COMPACT_NAV_CSS, COMPACT_NAV_VOLUMES, CURRENT_SUBLIMATION_LINK, REGISTER,
    SUBLIMATION_LINK, canonicalize, navbar_routes, publish, without_door_titles,
)

PUBLISHER = 'https://agdistys.github.io/aMi/'
ROUTE = re.compile(r'/ami(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?/')
VOLUME_FILE = re.compile(r'(?:volumes_protocole|annexes)/[a-zA-Z0-9_.-]+\.html')
ANNEX_ROUTE = re.compile(r'/(?:benchmark|catalogue-des-outils-ami|lettre-ouverte|metaconscience|metamatrice)/')
JAVASCRIPT_TYPES = {'', 'text/javascript', 'application/javascript'}


class Textareas(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.buffers = {}

    def handle_starttag(self, tag, attrs):
        if tag != 'textarea':
            return
        name = dict(attrs).get('id')
        if name:
            if name in self.buffers:
                raise ValueError(f'Textarea dupliquée : {name}')
            self.buffers[name] = []
            self.current = name

    def handle_endtag(self, tag):
        if tag == 'textarea':
            self.current = None

    def handle_data(self, data):
        if self.current:
            self.buffers[self.current].append(data)

    def codes(self, path):
        self.feed(path.read_text(encoding='utf-8'))
        return {name: ''.join(parts).strip() for name, parts in self.buffers.items()}


def integrity(data):
    return 'sha256-' + b64encode(sha256(data).digest()).decode('ascii')


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Structure inattendue : ' + before[:120])
    return text.replace(before, after, 1)


def source_for(path, source_dir, site_dir):
    if not VOLUME_FILE.fullmatch(path):
        raise ValueError(f'Fichier HTML non autorisé : {path}')
    source = (source_dir / path).read_bytes()
    if source != (site_dir / path).read_bytes():
        raise ValueError(f'Volume déployé différent de la source : {path}')
    return source


def adapt_generic(code, slug, path, raw):
    found = re.search(r'<script[^>]*\bdata-ami-volume-config(?:="")?[^>]*>(.*?)</script>',code,re.S)
    if not found:
        raise ValueError(f'Configuration absente : {slug}')
    config = json.loads(found[1])
    if config['slug'] != slug:
        raise ValueError(f'Route non concordante : {slug}')
    root = config['root'].encode('ascii')
    if not re.search(rb'\bid=[\x22\x27]'+re.escape(root)+rb'[\x22\x27]',raw):
        raise ValueError(f'Racine incompatible : {slug}')
    code = code.replace(config['url'],PUBLISHER+path)
    config.update(url=PUBLISHER+path,sha256=sha256(raw).hexdigest(),bytes=len(raw))
    return once(code,re.search(r'(<script[^>]*\bdata-ami-volume-config(?:="")?[^>]*>)(.*?)(</script>)',code,re.S)[0],
                found[0].split('>',1)[0]+'>'+json.dumps(config,ensure_ascii=False,separators=(',',':'))+'</script>')


def adapt_astro(code,path,raw):
    if b'ami-webnode-natural-adapter' not in raw or b'ami-host-decompression-compat' not in raw:
        raise ValueError('AstroGlobe incompatible avec son intégrateur')
    code,count = re.subn(r"const sourceURL = '[^']+';",f"const sourceURL = '{PUBLISHER}{path}';",code)
    if count != 1:
        raise ValueError('Source AstroGlobe ambiguë')
    code,count = re.subn(r"const integrity = 'sha256-[^']+';",f"const integrity = '{integrity(raw)}';",code)
    if count != 1:
        raise ValueError('Empreinte AstroGlobe ambiguë')
    return once(code,"fetch(sourceURL, {integrity, credentials:'omit'})","fetch(sourceURL, {integrity, redirect:'error', credentials:'omit'})")


def strip_index_payload(code,optional=False):
    code,count = re.subn(r'<script[^>]*\bdata-index-source(?:="")?[^>]*>[\s\S]*?</script>\s*','',code)
    if count != 1 and not (optional and count == 0):
        raise ValueError('Charge utile Index ambiguë')
    return code


def adapt_index(code,path,raw):
    if not re.search(rb'\bid=[\x22\x27]ami-index[\x22\x27]',raw):
        raise ValueError('Racine de l’Index incompatible')
    code = strip_index_payload(code,optional=True)
    code,count = re.subn(r"const base = '[^']+';",f"const base = '{PUBLISHER}{path}';",code)
    if count != 1:
        raise ValueError('Source Index ambiguë')
    before = '''    const packed = placeholder.querySelector('[data-index-source]').textContent.trim();
    const bytes = Uint8Array.from(atob(packed), char => char.charCodeAt(0));
    const raw = await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();'''
    after = f'''    const response = await fetch(base, {{integrity:'{integrity(raw)}',redirect:'error',credentials:'omit'}});
    if (!response.ok || response.url !== base) throw Error('Index indisponible.');
    const raw = await response.text();'''
    code = once(code,before,after)
    label = 'Ouvrir l’Index sur GitHub Pages'
    return once(code,"if (status.isConnected) status.textContent = 'L’Index n’a pas pu se charger.';",
                "if (!status.isConnected && host.isConnected) host.replaceWith(placeholder);\n"
                "    if (status.isConnected) {\n"
                "      status.textContent = 'L’Index n’a pas pu se charger. ';\n"
                "      const link = document.createElement('a');\n"
                f"      link.href = '{PUBLISHER}'; link.textContent = '{label.replace(chr(39), chr(92)+chr(39))}'; status.append(link);\n"
                "    }")


def compatible_css(code):
    if 'const sheet = new CSSStyleSheet();' not in code:
        return code
    code = once(code, '    const sheet = new CSSStyleSheet();\n', '')
    code = once(code, '    sheet.replaceSync(source);\n', '')
    return once(code, "    return Array.from(sheet.cssRules, render).join('\\n');", """    if (typeof CSSStyleSheet !== 'undefined' && typeof CSSStyleSheet.prototype.replaceSync === 'function') {
      const sheet = new CSSStyleSheet();
      sheet.replaceSync(source);
      return Array.from(sheet.cssRules, render).join('\\n');
    }
    const parser = document.createElement('style');
    parser.media = 'not all';
    parser.textContent = source;
    document.head.append(parser);
    try {
      return Array.from(parser.sheet.cssRules, render).join('\\n');
    } finally {
      parser.remove();
    }""")


def recover_volume_fetch(code):
    start = "    const response = await fetch(expected, { redirect:'error', credentials:'omit', cache:'force-cache' });"
    end = "throw Error('La version reçue ne correspond pas au bloc.');"
    if start not in code:
        return code
    opening = code.index(start)
    closing = code.index(end, opening) + len(end)
    return code[:opening] + """    if (!crypto.subtle) throw Error('La vérification du volume exige une page HTTPS.');
    async function verifiedBytes(url, cache) {
      const response = await fetch(url, { redirect:'error', credentials:'omit', cache });
      if (!response.ok || response.url !== url.href) throw Error('Le volume est indisponible.');
      const buffer = await response.arrayBuffer();
      if (buffer.byteLength !== cfg.bytes) throw Error('La taille du volume ne correspond pas au bloc.');
      const digest = await crypto.subtle.digest('SHA-256', buffer);
      const hash = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2,'0')).join('');
      if (hash !== cfg.sha256) throw Error('La version reçue ne correspond pas au bloc.');
      return buffer;
    }
    const versioned = new URL(expected);
    versioned.searchParams.set('v', cfg.sha256);
    const bytes = await verifiedBytes(versioned, 'default')
      .catch(() => verifiedBytes(expected, 'reload'));""" + code[closing:]


def adapt_navigation(code, slug, routes):
    source = (Path(__file__).with_name('volume-navigation.js')).read_text().strip()
    chrome = Path(__file__).with_name('volume-chrome.css').read_text()
    source = once(source, '/* __AMI_NAV_ROUTES__ */ null',
                  json.dumps(routes, ensure_ascii=False, separators=(',', ':')))
    base = 'sourceURL' if slug == 'ami-astroglobe' else 'base' if slug == 'ami' else 'expected'
    if slug == 'ami-astroglobe':
        marker = '    const cockpit = frame.contentDocument;'
        return once(code, marker, marker + '\n' + source + f'\n    tuneNavigation(cockpit, {base});\n'
                    '    const chromeStyle = cockpit.createElement("style");\n'
                    f'    chromeStyle.textContent = {json.dumps(chrome)};\n'
                    '    cockpit.head.append(chromeStyle);')
    style = 'nativeStyle' if slug == 'ami' else 'style'
    marker = f'    host.append(fragment, {style});'
    code = once(code, marker, f'    {style}.textContent += {json.dumps(chrome)};\n' + marker)
    if slug != 'ami' and slug != 'ami-miroir':
        code = once(code, '      const owner = active || host;',
                    '''      const nav = (active || host).querySelector('#amiBarre');
      const owner = nav || active || host;''')
        code = once(code, "      const offset = active ? 0 : Math.max(0,site?.getBoundingClientRect().bottom || 0);",
                    '''      const sitePosition = site && getComputedStyle(site).position;
      const siteBounds = site?.getBoundingClientRect();
      const offset = !active && ['sticky','fixed'].includes(sitePosition) && siteBounds.top <= 2
        ? Math.max(0,siteBounds.bottom) : 0;''')
    marker = "    for (const style of fragment.querySelectorAll('style'))"
    prefix = source + f'\n    tuneNavigation(fragment, {base});\n'
    if slug in {'ami-initiation', 'ami-lunion-du-tout'}:
        prefix += (f'    for (const link of fragment.querySelectorAll(\'a[href="{SUBLIMATION_LINK}"]\')) '
                   f'link.href = "{CURRENT_SUBLIMATION_LINK}";\n')
    if slug == 'ami-lunion-du-tout':
        prefix += f'''    const volumeLinks = fragment.querySelector('#ami-union > .ami-fil-tome-v1');
    if (volumeLinks) {{
      const reading = document.createElement('p');
      reading.className = 'ami-bareme-link';
      const link = document.createElement('a');
      link.href = {json.dumps(BAREME)};
      link.textContent = {json.dumps(BAREME_LABEL)};
      reading.append(link);
      volumeLinks.before(reading);
    }}
'''
    if slug in COMPACT_NAV_VOLUMES:
        css = COMPACT_NAV_CSS.replace('#amiBarre#amiBarre', '#ami-volume-webnode #amiBarre#amiBarre')
        # Insert after style isolation so the selectors can start at the host itself.
        style_marker = '    style.textContent = `\n'
        code = once(code, style_marker, style_marker + css + '\n')
    return once(code, marker, prefix + marker)


def adapter_bytes(code):
    scripts = [m for m in re.finditer(r'<script\b([^>]*)>([\s\S]*?)</script>',code,re.I)
               if (kind := re.search(r'\btype\s*=\s*["\']([^"\']+)',m[1])) is None or kind[1] in JAVASCRIPT_TYPES]
    if len(scripts) != 1 or scripts[0][1].strip():
        raise ValueError('Le bloc doit avoir un script principal inline unique')
    script = scripts[0]
    markup = code[:script.start()]+'<span data-ami-adapter-script-slot hidden></span>'+code[script.end():]
    markup = re.sub(r'(<p\b[^>]*\brole="status"[^>]*>)Ouverture[^<]*</p>',
                    lambda m: m[1]+'</p>',markup)
    markup = re.sub(r'\s*<a data-astro-link\b', '\n  <a hidden data-astro-link', markup)
    markup = '<style>[data-ami-public-block] :is([data-ami-volume-status],[data-astro-status],[data-index-loading],[data-ami-annex-loader] > [role=status]):empty{display:none}</style>'+markup
    prefix = f'''// aMi · intégration Webnode générée.\n{{\n  const entryScript = document.currentScript;
  const entryPoint = entryScript?.parentElement;
  if (!entryPoint?.matches('[data-ami-webnode-anchor]')) throw Error('Ancre Webnode absente.');
  const shell = document.createElement('template');
  shell.innerHTML = {json.dumps(markup,ensure_ascii=False)};
  shell.content.querySelector('[data-ami-adapter-script-slot]').replaceWith(entryScript);
  entryPoint.replaceWith(shell.content);
}}\n'''
    return (prefix+script[2].strip()+'\n').encode('utf-8')


def read_routes(source_dir):
    rows = [row.split('\t') for row in (source_dir/'fichiers_depot/routes-webnode.tsv').read_text().splitlines() if row.strip()]
    if len({row[0] for row in rows}) != len(rows):
        raise ValueError('Routes dupliquées')
    return dict(rows)


def index_target(source_dir):
    index = (source_dir/'index.html').read_text()
    target = re.search(r'\burl=(volumes_protocole/0_Index_aMi_[a-zA-Z0-9_.-]+\.html)',index,re.I)
    if not target:
        raise ValueError('Renvoi Index absent')
    return target[1]


def public_href(value):
    url = urlparse(urljoin(PUBLISHER,value))
    if url.scheme != 'https' or url.netloc != 'agdistys.github.io' or not url.path.startswith('/aMi/'):
        raise ValueError(f'Lien hors du dépôt : {value}')
    return url.geturl()


def read_annexes(path):
    if path is None:
        return {}
    data = json.loads(path.read_text())
    for route,entry in data.items():
        if not ROUTE.fullmatch(route) and not ANNEX_ROUTE.fullmatch(route):
            raise ValueError(f'Route annexe interdite : {route}')
        if entry['kind'] not in ('link','links') or not isinstance(entry['label'],str):
            raise ValueError(f'Type de route annexe inconnu : {route}')
        if entry['kind'] == 'link' or 'href' in entry:
            entry['href'] = public_href(entry['href'])
        if entry['kind'] == 'links':
            if not 1 <= len(entry['links']) <= 50:
                raise ValueError(f'Liste annexe incorrecte : {route}')
            for link in entry['links']:
                if not isinstance(link['label'],str):
                    raise ValueError(f'Libellé annexe invalide : {route}')
                link['href'] = public_href(link['href'])
    return data


def native_entry(code, path, raw, assets, label, href):
    adapter = adapter_bytes(code)
    filename = sha256(adapter).hexdigest()+'.js'
    (assets/filename).write_bytes(adapter)
    return {
        'kind':'native', 'label':label, 'href':href,
        'adapter':{'path':'webnode/adapters/'+filename,'integrity':integrity(adapter)},
        'source':{'path':path,'sha256':sha256(raw).hexdigest(),'bytes':len(raw)},
    }


def charte_navigation(raw, routes, index):
    """Reuse the Charte’s navbar, palette and responsive rules in the annex shell."""
    charte = raw.decode('utf-8')
    navbar = re.search(r'<nav\b[^>]*id="amiBarre"[^>]*>[\s\S]*?</nav>', charte)
    palette = re.search(r'#ami-charte\s*\{\s*/\* la Charte des Couleurs.*?--r:4px}', charte, re.S)
    rules = re.search(r'#ami-charte \.ami-barre\{--noir:var\(--onyx\);--plaque:[\s\S]*?(?=\n#ami-charte \.ami-pied\{--noir:)', charte)
    zoom = re.search(r'#ami-charte \.coin-zoom\{[\s\S]*?(?=/\* ── les liens du pied)', charte)
    footer = re.search(r'<footer class="ami-pied">[\s\S]*?</footer>', charte)
    footer_rules = re.search(r'#ami-charte \.ami-pied\{--noir:[\s\S]*?(?=/\* ── l.empilement des trois barres)', charte)
    footer_colors = re.search(r'/\* 15 · LE PIED[\s\S]*?(?=/\* 11 · LE HAUT DE PAGE)', charte)
    if not all((navbar, palette, rules, zoom, footer, footer_rules, footer_colors)):
        raise ValueError('La barre canonique de la Charte est incomplète')

    def css_style(name):
        style = re.search(r'<style id="'+name+r'">([\s\S]*?)</style>', charte)
        if not style:
            raise ValueError('Style canonique absent : '+name)
        return style[1]

    def route_link(match):
        path = match[1]
        # The Charte may name an older edition. Follow the stable route.
        stem = lambda value: re.split(r'_V[0-9]', value, maxsplit=1)[0]
        slug = 'ami' if stem(path) == stem(index) else next(
            (slug for slug,value in routes.items() if stem(value) == stem(path)), None,
        )
        if slug is None:
            raise ValueError('Cible du menu canonique absente : '+path)
        return f'data-ami-route="{slug}" href="{PUBLISHER + ("" if slug == "ami" else slug+"/")}"'

    markup = re.sub(r'href="\.\./(volumes_protocole/[^"]+)"', route_link, without_door_titles(navbar[0]))
    markup = re.sub(
        r'href="\.\./(ami-[a-z0-9-]+)/"', lambda m:f'data-ami-route="{m[1]}" href="{PUBLISHER+m[1]}/"',
        markup,
    )
    markup = once(markup,'class="ami-barre replie"','class="ami-barre ami-annex-bar replie"')
    css = '\n'.join((palette[0], rules[0], zoom[0], css_style('ami-navbar-evolution-v49-css'),
                     css_style('charte-index-initiation-v54'), css_style('ami-barre-1111'),
                     css_style('ami-barre-1111-cibles'), footer_rules[0], footer_colors[0]))
    css = css.replace('#ami-charte', '[data-ami-annex-chrome]')
    fonts = re.search(r'<link href="(https://fonts.googleapis.com/css2\?[^"]+)" rel="stylesheet"', charte[charte.find('<style id="ami-navbar-evolution-v49-css">'):])
    if not fonts:
        raise ValueError('Police de la barre canonique absente')
    chrome = Path(__file__).with_name('volume-chrome.css').read_text()
    return {'html':markup, 'footer':footer[0], 'css':css+'\n'+chrome, 'fonts':fonts[1].replace('&amp;', '&')}


def adapt_annex(template, slug, label, path, raw):
    pattern = r'(<script\b[^>]*\bdata-ami-annex-config(?:="")?[^>]*>)(.*?)(</script>)'
    config = {
        'slug':slug, 'label':label, 'url':PUBLISHER+path,
        'sha256':sha256(raw).hexdigest(), 'bytes':len(raw),
    }
    encoded = json.dumps(config,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    code, count = re.subn(pattern,lambda match:match[1]+encoded+match[3],template,flags=re.S)
    if count != 1:
        raise ValueError('Configuration du modèle annexe absente ou répétée')
    return code


def standalone_annex(raw, slug, label, asset):
    text = raw.decode('utf-8')
    script = (
        f'<script defer src="../webnode/adapters/{asset}" '
        f'data-ami-annex-standalone data-slug="{escape(slug,quote=True)}" '
        f'data-label="{escape(label,quote=True)}"></script>'
    )
    body_end = list(re.finditer(r'</body\s*>',text,re.I))
    if body_end:
        position = body_end[-1].start()
        text = text[:position]+script+'\n'+text[position:]
    else:
        text += '\n'+script+'\n'
    return text.encode('utf-8')


def main():
    parser = ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--site',type=Path,required=True)
    parser.add_argument('--guide',type=Path)
    parser.add_argument('--index',type=Path)
    parser.add_argument('--templates',type=Path)
    parser.add_argument('--write-templates',type=Path)
    parser.add_argument('--annexes',type=Path)
    parser.add_argument('--annex-template',type=Path)
    parser.add_argument('--annex-shell',type=Path)
    parser.add_argument('--bootstrap',type=Path,default=Path(__file__).with_name('bootstrap.html'))
    args = parser.parse_args()
    routes = read_routes(args.source)
    volumes = {slug:path for slug,path in routes.items() if path.startswith('volumes_protocole/')}
    volumes = {'ami':index_target(args.source),**volumes}
    navigation_routes = navbar_routes({'ami': volumes['ami'], **routes})
    if args.templates:
        if args.templates.is_dir():
            blocks = {'code-'+file.stem:file.read_text().strip() for file in args.templates.glob('*.html')}
        else:
            blocks = json.loads(args.templates.read_text())
    elif args.guide and args.index:
        blocks = Textareas().codes(args.guide)
        blocks['code-ami'] = strip_index_payload(Textareas().codes(args.index)['code'])
    else:
        parser.error('Utiliser --templates, ou --guide et --index ensemble.')
    expected = {'code-'+slug for slug in volumes}
    if set(blocks) != expected:
        raise ValueError(f'Blocs discordants : {sorted(set(blocks)^expected)}')
    if args.write_templates:
        args.write_templates.mkdir(parents=True,exist_ok=True)
        for key,block in blocks.items():
            (args.write_templates/(key.removeprefix('code-')+'.html')).write_text(block+'\n',encoding='utf-8')
    annexes = read_annexes(args.annexes)
    entries = {}
    assets = args.site/'webnode/adapters'
    assets.mkdir(parents=True,exist_ok=True)
    for slug,path in volumes.items():
        route = '/'+slug+'/'
        if not ROUTE.fullmatch(route) or route in annexes:
            raise ValueError(f'Route native non autorisée : {route}')
        raw = source_for(path,args.source,args.site)
        code = blocks['code-'+slug]
        if slug == 'ami':
            code = adapt_index(code,path,raw)
        elif slug == 'ami-astroglobe':
            code = adapt_astro(code,path,raw)
        else:
            code = adapt_generic(code,slug,path,raw)
        code = adapt_navigation(code, slug, navigation_routes)
        code = compatible_css(recover_volume_fetch(code))
        entries[route] = native_entry(
            code, path, raw, assets,
            'Ouvrir le volume sur GitHub Pages', PUBLISHER+('' if slug == 'ami' else slug+'/'),
        )
    if args.annex_template:
        if not args.annex_shell:
            parser.error('--annex-shell est nécessaire avec --annex-template')
        charte = (args.source/routes['ami-charte']).read_bytes()
        navigation = charte_navigation(charte, routes, volumes['ami'])
        shell = once(
            args.annex_shell.read_text(), '/* __AMI_CHARTE_NAV__ */ null',
            json.dumps(navigation, ensure_ascii=False, separators=(',',':')),
        ).encode('utf-8')
        shell_path = assets/(sha256(shell).hexdigest()+'.js')
        shell_path.write_bytes(shell)
        template = once(args.annex_template.read_text(), '/* __AMI_ANNEX_SHELL__ */', shell.decode())
        annex_content = {}
        for route, entry in list(annexes.items()):
            if entry['kind'] != 'link':
                continue
            slug = urlparse(entry['href']).path.removeprefix('/aMi/').strip('/')
            path = routes.get(slug,'')
            if not path.startswith('annexes/'):
                raise ValueError(f'Annexe hors des routes publiées : {route}')
            if slug not in annex_content:
                if slug == 'ami-registre':
                    path = REGISTER
                    raw = (args.site/path).read_bytes()
                else:
                    raw = source_for(path, args.source, args.site)
                if slug == 'ami-registre':
                    raw = canonicalize(raw.decode(),slug).encode()
                raw = standalone_annex(raw, slug, entry['label'], shell_path.name)
                (args.site/path).write_bytes(raw)
                code = adapt_annex(template, slug, entry['label'], path, raw)
                annex_content[slug] = native_entry(code, path, raw, assets, entry['label'], entry['href'])
            annexes[route] = annex_content[slug]
    catalogue = {'schema':1,'routes':{**entries,**annexes}}
    (args.site/'webnode/catalogue-v1.json').write_text(json.dumps(catalogue,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    snippet = args.bootstrap.read_text()
    (args.site/'webnode/bloc-webnode-v1.txt').write_text(snippet)
    publish(args.source,args.site,routes,volumes['ami'],snippet)
    print(f'{len(entries)} intégrateurs natifs, {len(annexes)} routes annexes')


if __name__ == '__main__':
    main()
