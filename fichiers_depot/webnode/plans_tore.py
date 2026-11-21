"""Publish the live eight Plans and Tore as a reusable, isolated Webnode block."""
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
import re


VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
SECTIONS = ('t8-tore', 't8-plans', 't8-3-mondes')
SCRIPTS = ('c21-son-sim', 'tr81-js', 'v057-tri-js', 'v089-axis-js', 'v091-explorateur-js')
CSS_KEYS = ('.t8-', '.tr81', '.v057-', '.q49-mo', '.q49-pli', '.c7-pl', '#ami-canon{', '.c21-')
PLAN_IDS = ('plan:DO', 'plan:RÉ', 'plan:MI', 'plan:FA', 'plan:SOL', 'plan:LA', 'plan:SI', 'plan:∞')


def validate_plan_matrix(block):
    """Keep the accepted matrix and the explanatory Spectrum together."""
    rows = re.findall(r'<tr class="t8-matrice-row t8-row-[^"]+" data-plan-id="([^"]+)"', block)
    cards = re.findall(r'<li class="c7-pl" data-plan-id="([^"]+)"', block)
    if tuple(rows) != PLAN_IDS or tuple(cards) != PLAN_IDS:
        raise ValueError('La matrice validée et les huit cartes doivent porter les mêmes Plans, dans le même ordre.')
    if 'id="t8-matrice-passage"' not in block or 'id="t8-spectre"' not in block:
        raise ValueError('Les deux lectures sont requises : Symétrie et Spectre avec ses définitions.')
    if len(re.findall(r'<li class="t8-lg-[^"]+"',block)) != 13:
        raise ValueError('Les treize définitions du Spectre doivent rester présentes.')
    if block.count('📕 Article du Code Peinal') != 10:
        raise ValueError('Le Code Peinal doit figurer dans Culture : Spectre, Symétrie et huit cartes.')


class Sections(HTMLParser):
    """Locate complete source elements without serializing their authored HTML."""
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.lines = [0]
        self.lines.extend(match.end() for match in re.finditer('\n', source))
        self.stack = []
        self.blocks = {}

    def position(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, dict(attrs).get('id'), self.position()))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                _, name, start = self.stack[index]
                if name in SECTIONS:
                    if name in self.blocks:
                        raise ValueError('Section des Plans dupliquée : ' + name)
                    end = self.source.index('>', self.position()) + 1
                    self.blocks[name] = self.source[start:end]
                del self.stack[index:]
                break


def publish_plans_tore(source_dir, site_dir, routes, publisher):
    path = routes['ami-complementarite']
    source = (source_dir / path).read_text(encoding='utf-8')
    parser = Sections(source)
    parser.feed(source)
    if set(parser.blocks) != set(SECTIONS):
        raise ValueError('Sections des huit Plans manquantes')
    validate_plan_matrix(parser.blocks['t8-plans'])
    styles = []
    for match in re.finditer(r'<style\b[^>]*>(.*?)</style>', source, re.S):
        if any(key in match[1] for key in CSS_KEYS) or 'id="q236-shared-fonts"' in match[0]:
            styles.append(match[0])
    scripts = []
    for name in SCRIPTS:
        matches = re.findall(r'<script\b[^>]*\bid="' + name + r'"[^>]*>(.*?)</script>', source, re.S)
        if len(matches) != 1:
            raise ValueError('Script des huit Plans manquant ou dupliqué : ' + name)
        scripts.append('<script id="' + name + '">' + matches[0] + '</script>')
    blocks = '\n'.join(parser.blocks[name] for name in SECTIONS)
    blocks = re.sub(r'(<details\b[^>]*\bid="t8-plans")([^>]*>)', r'\1 open\2', blocks, count=1)
    if len(re.findall(r'class="c7-pl"', parser.blocks['t8-plans'])) != 8:
        raise ValueError('Le bloc doit contenir huit cartes de Plan')
    # A fragment targeting another chapter opens the complete edition.
    ids = set(re.findall(r'\bid="([^"]+)"', blocks))
    def fragment_link(match):
        target = match[1]
        if target in ids:
            return match[0]
        return 'href="' + publisher + 'ami-complementarite/#' + escape(target, quote=True) + '" target="_blank" rel="noopener"'
    blocks = re.sub(r'href="#([^\"]+)"', fragment_link, blocks)
    # Keep relative authored resources usable from the extracted page.
    base = urljoin(publisher, path)
    def absolute_resource(match):
        attribute, value = match[1], match[2]
        if value.startswith(('#', '/', 'data:', 'http:', 'https:', 'mailto:', 'tel:')):
            return match[0]
        return attribute + '="' + escape(urljoin(base, value), quote=True) + '"'
    blocks = re.sub(r'\b(href|src|poster)="([^\"]+)"', absolute_resource, blocks)
    page_url = publisher + 'widgets/plans-conscience/'
    bridge = '''<script>
(() => {
  if (parent === window) return;
  const params = new URLSearchParams(location.search);
  const recipient = params.get('parent');
  let origin;
  try { origin = new URL(recipient).origin; } catch { return; }
  if (!/^https?:$/.test(new URL(origin).protocol)) return;
  const key = params.get('instance');
  if (!key) return;
  let lastHeight = 0;
  let pending = false;
  function update() {
    pending = false;
    const height = Math.ceil(document.querySelector('main').getBoundingClientRect().height);
    if (Math.abs(height - lastHeight) > 1) {
      lastHeight = height;
      parent.postMessage({type:'ami-plans-tore-height', instance:key, height}, origin);
    }
  }
  function schedule() {
    if (pending) return;
    pending = true;
    requestAnimationFrame(update);
  }
  new ResizeObserver(schedule).observe(document.querySelector('main'));
  document.addEventListener('toggle', schedule, true);
  addEventListener('load', schedule);
  document.fonts?.ready.then(schedule);
  schedule();
})();
</script>'''
    rendered = '''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Les 8 Plans de ConScience · Le Tore · aMi</title>
<meta name="description" content="Les huit Plans de ConScience aMi, leurs cartes et le Tore interactif. Extrait de Complémentarité.">
<link rel="canonical" href="''' + page_url + '''">
''' + '\n'.join(styles) + '''
<style>
html,body{margin:0;padding:0;background:#09090e;color-scheme:dark}
body{overflow-x:clip}
#ami-vol-complementarite #ami-canon{margin:0;max-width:none;padding:0 1rem 1rem;font-size:16px}
#ami-vol-complementarite #ami-canon .plans-entree{padding:1rem 0;text-align:center}
#ami-vol-complementarite #ami-canon .plans-entree h1{margin:.25rem 0;font:700 clamp(1.8rem,5vw,2.8rem)/1.15 "Cormorant Garamond",Georgia,serif;color:#ffc545}
#ami-vol-complementarite #ami-canon .plans-entree a{color:#ffc545}
#ami-vol-complementarite #ami-canon .plans-entree p{margin:.4rem 0!important}
body.ami-plans-standalone #ami-vol-complementarite #ami-canon .v091-title{display:none!important}
#ami-vol-complementarite #ami-canon #t8-plans{max-width:75rem;margin-inline:auto}
#ami-vol-complementarite #ami-canon :is(button,summary){min-height:44px}
#ami-vol-complementarite #ami-canon :is(button,a,summary):focus-visible{outline:2px solid #ffc545;outline-offset:3px}
@media(max-width:480px){#ami-vol-complementarite #ami-canon{padding-inline:.55rem}}
@media print{details>div{display:block!important}}
</style>
</head><body class="ami-plans-standalone"><main id="ami-vol-complementarite"><div id="ami-canon">
<header class="plans-entree"><h1>Les 8 Plans<br>Le Passage en Miroir</h1><p><a href="''' + publisher + '''ami-complementarite/" target="_blank" rel="noopener">Complémentarité · Protocole aMi</a> · <a href="''' + publisher + '''ami-complementarite/#courages-plans" target="_blank" rel="noopener">Les Huit Courages</a> · <a href="index.html" download="8_Plans_de_ConScience_et_Tore_aMi.html">Télécharger cette page HTML</a></p></header>
''' + blocks + '''
<p class="plans-entree">Agdistys · Diane Serant · <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.fr" target="_blank" rel="noopener">CC BY-SA 4.0</a></p>
</div></main>
''' + '\n'.join(scripts) + bridge + '\n</body></html>\n'
    if re.search(r'(?:file:|/Users/|computer:)', rendered):
        raise ValueError('Chemin local dans le bloc des huit Plans')
    directory = site_dir / 'widgets/plans-conscience'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'index.html').write_text(rendered, encoding='utf-8')
    sitemap = site_dir / 'sitemap.xml'
    sitemap_text = sitemap.read_text(encoding='utf-8')
    entry = '<url><loc>' + escape(page_url) + '</loc></url>'
    if '<loc>' + escape(page_url) + '</loc>' not in sitemap_text:
        if sitemap_text.count('</urlset>') != 1:
            raise ValueError('Sitemap des huit Plans inattendu')
        sitemap.write_text(sitemap_text.replace('</urlset>', entry + '</urlset>'), encoding='utf-8')
    block = '''<div data-ami-plans-tore>
  <p><a href="''' + page_url + '''" target="_blank" rel="noopener">Ouvrir les 8 Plans de ConScience et le Tore</a></p>
  <script>
  (() => {
    const box = document.currentScript.parentElement;
    const key = crypto.randomUUID ? crypto.randomUUID() : Date.now() + '-' + Math.random().toString(36).slice(2);
    const url = new URL('__AMI_PLANS_PAGE__');
    url.searchParams.set('parent', location.origin);
    url.searchParams.set('instance', key);
    const frame = document.createElement('iframe');
    frame.title = 'Les 8 Plans de ConScience · Le Tore aMi';
    frame.src = url.href;
    frame.style.cssText = 'display:block;width:100%;height:900px;border:0;background:#09090e;color-scheme:dark';
    frame.setAttribute('scrolling', 'no');
    const receive = event => {
      const data = event.data;
      if (event.origin !== url.origin || event.source !== frame.contentWindow || !data || data.type !== 'ami-plans-tore-height' || data.instance !== key) return;
      if (!Number.isFinite(data.height) || data.height < 100 || data.height > 200000) return;
      frame.style.height = Math.ceil(data.height) + 'px';
    };
    addEventListener('message', receive);
    box.append(frame);
  })();
  </script>
</div>
'''
    block = block.replace('__AMI_PLANS_PAGE__', page_url)
    (site_dir / 'webnode/blocs/ami-plans-tore.txt').write_text(block, encoding='utf-8')
    return directory / 'index.html'
