#!/usr/bin/env python3
"""Generate immutable native Webnode adapters and a stable catalogue for GitHub Pages."""
from argparse import ArgumentParser
from base64 import b64encode
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
import json
import re

PUBLISHER = 'https://agdistys.github.io/aMi/'
ROUTE = re.compile(r'/ami(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?/')
VOLUME_FILE = re.compile(r'volumes_protocole/[a-zA-Z0-9_.-]+\.html')
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
        raise ValueError(f'Volume non autorisé : {path}')
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


def adapter_bytes(code):
    scripts = [m for m in re.finditer(r'<script\b([^>]*)>([\s\S]*?)</script>',code,re.I)
               if (kind := re.search(r'\btype\s*=\s*["\']([^"\']+)',m[1])) is None or kind[1] in JAVASCRIPT_TYPES]
    if len(scripts) != 1 or scripts[0][1].strip():
        raise ValueError('Le bloc doit avoir un script principal inline unique')
    script = scripts[0]
    markup = code[:script.start()]+'<span data-ami-adapter-script-slot hidden></span>'+code[script.end():]
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
        if not ROUTE.fullmatch(route) and not re.fullmatch(r'/(?:benchmark|catalogue-des-outils-ami|lettre-ouverte)/',route):
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


def main():
    parser = ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--site',type=Path,required=True)
    parser.add_argument('--guide',type=Path)
    parser.add_argument('--index',type=Path)
    parser.add_argument('--templates',type=Path)
    parser.add_argument('--write-templates',type=Path)
    parser.add_argument('--annexes',type=Path)
    parser.add_argument('--bootstrap',type=Path,default=Path(__file__).with_name('bootstrap.html'))
    args = parser.parse_args()
    routes = read_routes(args.source)
    volumes = {slug:path for slug,path in routes.items() if path.startswith('volumes_protocole/')}
    volumes = {'ami':index_target(args.source),**volumes}
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
        adapter = adapter_bytes(code)
        filename = sha256(adapter).hexdigest()+'.js'
        (assets/filename).write_bytes(adapter)
        entries[route] = {'kind':'native','label':'Ouvrir le volume sur GitHub Pages','href':PUBLISHER+('' if slug == 'ami' else slug+'/'),
                          'adapter':{'path':'webnode/adapters/'+filename,'integrity':integrity(adapter)},
                          'source':{'path':path,'sha256':sha256(raw).hexdigest(),'bytes':len(raw)}}
    catalogue = {'schema':1,'routes':{**entries,**annexes}}
    (args.site/'webnode/catalogue-v1.json').write_text(json.dumps(catalogue,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    snippet = args.bootstrap.read_text()
    (args.site/'webnode/bloc-webnode-v1.txt').write_text(snippet)
    print(f'{len(entries)} intégrateurs natifs, {len(annexes)} routes annexes')


if __name__ == '__main__':
    main()
