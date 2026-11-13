#!/usr/bin/env python3
"""Build the public Registre web edition from its immutable offline edition."""

from argparse import ArgumentParser
from base64 import b64decode, b64encode
from collections import defaultdict
from gzip import decompress
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re


ONLINE = 'Registre_en_ligne.html'
READING_INDEX = 'Registre_Index_Lecture.html'
PACKS = re.compile(
    rb'<script id="paquet-(\d+)" type="application/octet-stream" data-onglet="[a-z0-9-]+">([A-Za-z0-9+/=]+)</script>'
)

GROUP_START = "const tag=$('paquet-'+g);"
GROUP_END = 'return job}'
LOAD_GROUP = '''const [name,integrity,length]=groups[g];
  const job=(async()=>{
    const url=new URL('./registre-paquets/'+name,document.baseURI);
    const response=await fetch(url,{credentials:'omit',redirect:'error',integrity});
    if(!response.ok||response.url!==url.href)throw Error('Paquet du Registre indisponible.');
    const compressed=await response.arrayBuffer();
    if(compressed.byteLength!==length)throw Error('Taille du paquet différente de la référence.');
    const bytes=new Uint8Array(compressed);
    if(window.pako)return window.pako.ungzip(bytes);
    const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  })();
  G.set(g,job);
  job.catch(()=>{if(G.get(g)===job)G.delete(g)});
  if(G.size>4)G.delete(G.keys().next().value);
  return job}'''

HISTORY_BRIDGE = '''
// srcdoc inherits the Webnode origin while its base URL belongs to Pages.
const registreHost=window.location.href==='about:srcdoc' ? window.parent : window;
const registreLocation=registreHost.location, registreHistory=registreHost.history;
function registreHash(fragment){
  const url=new URL(registreLocation.href);
  url.hash=fragment;
  registreHistory.replaceState(registreHistory.state,'',url.href);
}
'''


def block(source, name):
    pattern = rb'<script id="' + re.escape(name.encode()) + rb'"[^>]*>(.*?)</script>'
    found = list(re.finditer(pattern, source, re.S))
    if len(found) != 1:
        raise ValueError(f'Bloc du Registre absent ou dupliqué : {name}')
    return found[0]


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f'Structure du Registre inattendue : {before[:80]!r}')
    return text.replace(before, after, 1)


def encode_json(data):
    return json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').encode()


def source_path(root):
    table = (root / 'fichiers_depot/routes-webnode.tsv').read_text(encoding='utf-8')
    entries = [row.split('\t')[1] for row in table.splitlines() if row.startswith('ami-registre\t')]
    if len(entries) != 1 or not re.fullmatch(r'annexes/Registre_des_Preenregistrements_[A-Za-z0-9_.-]+\.html', entries[0]):
        raise ValueError('Source publique du Registre absente ou ambiguë')
    return root / entries[0]


def prepare_packs(source, index, destination):
    pieces_by_group = defaultdict(list)
    for key, (group, offset, size) in index.items():
        pieces_by_group[group].append((key, offset, size))
    matches = list(PACKS.finditer(source))
    pack_ids = [int(match[1]) for match in matches]
    if not pack_ids or set(pack_ids) != set(pieces_by_group) or len(pack_ids) != len(pieces_by_group):
        raise ValueError('Liste des paquets discordante avec l’index public')

    destination.mkdir(parents=True, exist_ok=True)
    groups = {}
    for match, group in zip(matches, pack_ids, strict=True):
        packed = b64decode(match[2], validate=True)
        unpacked = decompress(packed)
        cursor = 0
        for key, offset, size in sorted(pieces_by_group[group], key=lambda item: item[1]):
            if offset != cursor or size <= 0 or offset + size > len(unpacked):
                raise ValueError(f'Découpage du paquet {group} non concordant')
            cursor += size
            if sha256(unpacked[offset:cursor]).hexdigest() != key:
                raise ValueError(f'Empreinte de la pièce discordante : {key}')
        if cursor != len(unpacked):
            raise ValueError(f'Octets sans référence dans le paquet {group}')
        digest = sha256(packed)
        name = f'{digest.hexdigest()}.bin'
        (destination / name).write_bytes(packed)
        groups[group] = [name, 'sha256-' + b64encode(digest.digest()).decode('ascii'), len(packed)]
    return groups, sum(item[2] for item in groups.values())


def reading_index(meta, offline_name):
    records = defaultdict(list)
    for record in meta['records']:
        records[record['tab']].append(record)

    toc = []
    sections = []
    tabs = [tab for tab in meta['mains'] if tab['id'] != 'tests'] + meta['subs']
    for tab in tabs:
        key = escape(tab['id'], quote=True)
        name = escape(' '.join(filter(None, (tab.get('em'), tab['label']))))
        items = records.pop(tab['id'], [])
        toc.append(f'<li><a href="#{key}">{name} · {len(items)}</a></li>')
        listing = []
        for item in items:
            title = escape(item['title'])
            reference = escape(item['id'], quote=True)
            hint = ' · 🔒 Empreinte seule' if item.get('reserve') else ''
            listing.append(f'<li id="{reference}"><a href="{ONLINE}#{reference}">{title}</a>{hint}</li>')
        sections.append(f'<details id="{key}"><summary>{name} · {len(items)} pièces</summary><ul>{"".join(listing)}</ul></details>')
    if records:
        raise ValueError('Des pièces sont absentes de l’index de lecture')

    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Sommaire public des préenregistrements, protocoles, résultats et sources du Protocole aMi.">
<title>Registre des PréEnregistrements · Index de Lecture</title>
<style>
:root{{color-scheme:dark;background:#0b0b11;color:#f3e8cf;font:1rem/1.65 system-ui,sans-serif}}
body{{max-width:68rem;margin:0 auto;padding:clamp(1rem,4vw,3rem);box-sizing:border-box}}
h1,summary{{font-family:Georgia,serif;color:#ffd06a}} h1{{font-size:clamp(1.8rem,6vw,3rem);line-height:1.15}}
a{{color:#ffd06a;text-underline-offset:.2em}} details{{border:1px solid #766025;padding:.7rem 1rem;margin:.65rem 0;border-radius:.55rem}}
summary{{font-weight:bold;cursor:pointer}} ul{{padding-inline-start:1.35rem}} li{{overflow-wrap:break-word}}
:target{{outline:2px solid #ffd06a;outline-offset:3px}} nav ul{{columns:2;column-gap:2rem}}
@media(max-width:40rem){{nav ul{{columns:1}}}}
</style></head><body>
<header><a href="../">❤️‍🔥 Protocole aMi</a><h1>🔏 Registre des PréEnregistrements</h1>
<p>Index de Lecture · {len(meta['records'])} pièces référencées dans l’édition publique {escape(str(meta['edition']))}.</p>
<p>Les titres et les repères se lisent directement ici. Les liens ouvrent les pièces dans le Registre interactif.</p>
<p><a href="{ONLINE}">Ouvrir le Registre interactif</a> · <a href="{escape(offline_name, quote=True)}" download>Emporter l’édition autonome</a></p></header>
<nav aria-label="Les parties du Registre"><ul>{"".join(toc)}</ul></nav>
<main>{"".join(sections)}</main></body></html>\n'''


def build(source_dir, site_dir):
    path = source_path(source_dir)
    source = path.read_bytes()
    annexes = site_dir / 'annexes'
    meta = json.loads(block(source, 'registre-data')[1])
    copy = meta['copie']
    if copy.get('publique') is not True or not copy.get('textes_reserves_retires'):
        raise ValueError('Le Registre en ligne exige une copie publique expurgée')
    manifest = block(source, 'registre-paquets')
    index = json.loads(manifest[1])['index']
    withheld = {item['sha256'] for item in copy['textes_reserves_retires']}
    if withheld.intersection(index):
        raise ValueError('L’index contient une pièce exclue de la copie publique')
    groups, packed_size = prepare_packs(source, index, annexes / 'registre-paquets')

    online = replace_once(source, manifest[1], encode_json({'index': index, 'groups': groups}))
    online, removed = PACKS.subn(b'', online)
    if removed != len(groups):
        raise ValueError('Nombre de paquets déplacés inattendu')
    app = block(online, 'registre-app')
    js = app[1].decode()
    js = replace_once(js, 'const idx=I?JSON.parse(I.textContent).index:{};', 'const manifest=JSON.parse(I.textContent),idx=manifest.index,groups=manifest.groups;')
    start = js.index(GROUP_START)
    stop = js.index(GROUP_END, start) + len(GROUP_END)
    js = js[:start] + LOAD_GROUP + js[stop:]
    js = replace_once(js, 'function decodeHash(s)', HISTORY_BRIDGE + '\nfunction decodeHash(s)')
    js = replace_once(js, "location.hash!=='#'+cur)history.replaceState(null,'','#'+cur)",
                      "registreLocation.hash!=='#'+cur)registreHash(cur)")
    js = replace_once(js, "history.replaceState(null,'','#'+encodeURIComponent(dest));", 'registreHash(encodeURIComponent(dest));')
    js = replace_once(js, "window.addEventListener('hashchange',()=>{const h=decodeHash(location.hash.slice(1));",
                      "registreHost.addEventListener('hashchange',()=>{const h=decodeHash(registreLocation.hash.slice(1));")
    js = replace_once(js, 'const initial=decodeHash(location.hash.slice(1));',
                      'const initial=decodeHash(registreLocation.hash.slice(1));')
    online = online[:app.start(1)] + js.encode() + online[app.end(1):]

    controls = (f'<p class="ver"><a href="./{READING_INDEX}">Index de Lecture</a> · '
                f'<a href="./{path.name}" download>Emporter l’édition autonome</a></p>')
    online = replace_once(online, b'</p></header><div id="repere-barre"',
                          ('</p>' + controls + '</header><div id="repere-barre"').encode())
    online = replace_once(online,
                          '<noscript>Cette édition autonome utilise JavaScript pour ouvrir les onglets et les pièces intégrées.</noscript>'.encode(),
                          (f'<noscript>Les pièces se chargent à l’ouverture. <a href="./{READING_INDEX}">Consulter l’index public sans JavaScript</a>.</noscript>').encode())
    (annexes / ONLINE).write_bytes(online)
    (annexes / READING_INDEX).write_text(reading_index(meta, path.name), encoding='utf-8')
    print(f'Registre : {len(source):,} → {len(online):,} octets au chargement, {len(groups)} paquets à la demande ({packed_size:,} octets), {len(index):,} empreintes vérifiées.')


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('site', type=Path)
    args = parser.parse_args()
    build(args.source, args.site)
