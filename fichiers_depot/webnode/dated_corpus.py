"""Publish a dated reading snapshot from the public Markdown in a fixed commit."""

from bisect import bisect_left, bisect_right
from hashlib import sha256
from html import escape
import json
from pathlib import PurePosixPath
import re
from subprocess import CalledProcessError, run
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from markdown_reading import render_markdown


DATED_PATH = 'lecture/V001_2026-11-14/'
ARCHIVE_NAME = 'Protocole-aMi_V001_2026-11-14.zip'
BOOK_NAME = 'Livre-Protocole-aMi_V001_2026-11-14.html'
VERSION = 'V001'
DATE = '2026-11-14'
DATE_LABEL = '14 novembre 2026'
REVISION = 'f319773ad98b640513daf63ec01ad5892386fd83'
TITLE = f'Protocole de ConScience aMi · Corpus public {VERSION} · {DATE_LABEL}'
DESCRIPTION = 'Édition datée des 28 Versions Texte publiques, avec sommaire et blocs de lecture statiques.'
MIN_BLOCK_BYTES = 200_000
TARGET_BLOCK_BYTES = 250_000
MAX_BLOCK_BYTES = 300_000
SOURCE_HEADING = re.compile(r'^ {0,3}#{1,6}[ \t]+(\S[^\n]*)$', re.M)

HTML_ONLY = {
    'ami-miroir': 'Miroir',
    'ami-controle-qualite': 'Contrôle Qualité',
    'ami-tests': 'Campagnes de Mesures IA',
    'ami-registre': 'Registre des Préenregistrements · index public',
    'ami-citer-contester-contribuer': 'Citer · Contester · Contribuer',
    'ami-tuto-esprit-critique': 'Tuto d’Esprit Critique',
}


def _git(source, *args):
    try:
        return run(['git', '-C', str(source), *args], check=True, capture_output=True).stdout
    except CalledProcessError as error:
        message = error.stderr.decode('utf-8', errors='replace').strip()
        raise ValueError(f'Impossible de lire le corpus figé {REVISION} dans Git : {message}') from error


def _snapshot(source):
    paths = set(_git(source, 'ls-tree', '-rz', '--name-only', REVISION).decode('utf-8').split('\0'))

    def read(path):
        return _git(source, 'show', f'{REVISION}:{path}')

    index = re.search(rb'\burl=(volumes_protocole/0_Index_aMi_[\w.-]+\.html)', read('index.html'), re.I)
    if not index:
        raise ValueError('Le corpus figé n’a pas de route pour l’Index.')
    routes = [('ami', index[1].decode('ascii'))]
    routes.extend(tuple(line.split('\t')) for line in read('fichiers_depot/routes-webnode.tsv').decode('utf-8').splitlines())

    volumes, html_only = [], []
    for slug, target in routes:
        if target not in paths or not re.fullmatch(r'ami(?:-[a-z0-9]+)*', slug):
            raise ValueError(f'Route invalide dans le corpus figé : {slug} → {target}')
        path = PurePosixPath(target).with_suffix('.md').as_posix()
        if path not in paths:
            html_only.append((slug, target))
            continue
        raw = read(path)
        headline = raw.split(b'\n', 1)[0].decode('utf-8').lstrip('\ufeff# ').strip()
        headline = re.sub(r'\s+[—–-]\s+Version Texte.*$', '', headline, flags=re.I)
        if not headline:
            raise ValueError(f'Titre absent de la Version Texte figée : {path}')
        volumes.append((slug, target, path, headline, raw))
    if len(volumes) != 28 or set(slug for slug, _ in html_only) != HTML_ONLY.keys():
        raise ValueError('L’édition V001 doit réunir 28 Versions Texte et référencer 6 éditions HTML.')
    return volumes, html_only


def _blocks(raw):
    # Each limit is an exact byte position at the end of a source line. Blank
    # lines and headings are preferred. The pinned sources never need a table
    # row or a single line split to meet the maximum size.
    lines = raw.splitlines(keepends=True)
    all_ends, safe_ends, preferred_ends = [], [], []
    offset = 0
    for i, line in enumerate(lines):
        offset += len(line)
        all_ends.append(offset)
        if i + 1 == len(lines):
            break
        following = lines[i + 1]
        if line.lstrip().startswith(b'|') and following.lstrip().startswith(b'|'):
            continue
        safe_ends.append(offset)
        if not line.strip() or re.match(rb'^#{1,6}[ \t]', following):
            preferred_ends.append(offset)

    def best(candidates, minimum, target, maximum):
        first, last = bisect_left(candidates, minimum), bisect_right(candidates, maximum)
        if first == last:
            return None
        return min(candidates[first:last], key=lambda value: (abs(value - target), value))

    start = 0
    while len(raw) - start > MAX_BLOCK_BYTES:
        remaining = len(raw) - start
        minimum = start + MIN_BLOCK_BYTES
        maximum = min(start + MAX_BLOCK_BYTES, len(raw) - MIN_BLOCK_BYTES)
        if maximum < minimum:
            minimum = start + remaining // 2 - 20_000
            maximum = start + remaining // 2 + 20_000
        target = min(start + TARGET_BLOCK_BYTES, start + remaining // 2)
        end = (best(preferred_ends, minimum, target, maximum)
               or best(safe_ends, minimum, target, maximum)
               or best(safe_ends, start + 1, target, start + MAX_BLOCK_BYTES)
               or best(all_ends, start + 1, target, start + MAX_BLOCK_BYTES))
        if end is None:
            raise ValueError(f'Une ligne dépasse {MAX_BLOCK_BYTES} octets dans une Version Texte figée.')
        yield start, end, bisect_right(all_ends, start) + 1, bisect_right(all_ends, end)
        start = end
    if start < len(raw):
        yield start, len(raw), bisect_right(all_ends, start) + 1, len(lines)


def _digest(raw):
    return {'octets': len(raw), 'sha256': sha256(raw).hexdigest()}


def _label(value):
    return value.replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]')


def _markdown_link(url, title):
    return f'[{_label(title)}]({url})'


def _book_content(slug, fragment, source_url):
    # The same headings can appear in several parts of the complete book.
    heading = re.compile(r'(<h[1-6] id=")([^"]+)(">)')
    anchors = {match[2] for match in heading.finditer(fragment)}
    fragment = heading.sub(lambda m: f'{m[1]}{slug}-{m[2]}{m[3]}', fragment)
    return re.sub(r'<a href="#([^"]*)"',
                  lambda m: f'<a href="#{slug}-{m[1]}"' if m[1] in anchors
                  else f'<a href="{escape(source_url, quote=True)}#{m[1]}"', fragment)


def _download_link(filename, label):
    return f'<a href="{filename}" download="{filename}">{escape(label)}</a>'


def publish_dated_corpus(source, site, base_url):
    """Write the V001 snapshot into Pages and return its canonical index URL."""
    from corpus_reading import LICENSE, add_to_sitemap, document, file_size, link

    volumes, html_only = _snapshot(source)
    base_url = base_url.rstrip('/') + '/'
    canonical = base_url + DATED_PATH
    directory = site / DATED_PATH
    directory.mkdir(parents=True, exist_ok=True)
    hashes = {}

    def write(path, content):
        raw = content.encode('utf-8') if isinstance(content, str) else content
        output = directory / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw)
        hashes[path] = _digest(raw)
        return {'fichier': path, **hashes[path]}

    note = (
        'Cette édition fixe 28 Versions Texte publiques dans leur ordre de lecture. '
        'Les blocs Markdown d’un même volume, concaténés dans l’ordre sans caractère ajouté, '
        'reconstituent à l’octet près son fichier d’origine. '
        'Les six éditions publiques disponibles en HTML seul sont référencées par lien.'
    )
    credits = 'Agdistys · Diane Serant · Licence CC BY-SA 4.0'
    md_contents = [f'# {TITLE}', '', credits, '', note, '', '## Versions Texte', '']
    html_contents, manifest_volumes = [], []
    book_sections, book_index = [], []
    full_corpus = bytearray(f'# {TITLE}\n\n{credits}\n\n{note}\n'.encode('utf-8'))
    for slug, target, source_path, title, raw in volumes:
        source_url = base_url + target
        chunks = list(_blocks(raw))
        manifest = {'route': slug, 'titre': title, 'source': source_path, **_digest(raw), 'blocs': []}
        full_corpus.extend(f'\n\n## Édition · {title}\n\nSHA-256 de la source Markdown : `{manifest["sha256"]}`\n\n'.encode('utf-8'))
        full_corpus.extend(raw)
        rows = []
        book_parts = []
        md_contents.extend([f'### {title}', ''])
        for part, (start, end, first_line, last_line) in enumerate(chunks, 1):
            stem = f'bloc-{part:03}'
            md_name, html_name = f'{slug}/{stem}.md', f'{slug}/{stem}.html'
            previous = link(f'bloc-{part - 1:03}.html', 'Bloc précédent') if part > 1 else ''
            following = link(f'bloc-{part + 1:03}.html', 'Bloc suivant') if part < len(chunks) else ''
            nav = ' · '.join(filter(None, (link('../', 'Sommaire de cette édition'), previous, following)))
            block = raw[start:end]
            markdown = write(md_name, block)
            label = f'Bloc {part}/{len(chunks)}'
            block_text = block.decode('utf-8')
            fragment = render_markdown(block_text, base_url=source_url)
            book_parts.append(_book_content(f'{slug}-{part}', fragment, source_url))
            first_lines = block_text.split('\n', 80)[:80]
            heading = None
            for match in SOURCE_HEADING.finditer('\n'.join(first_lines)[:30_000]):
                candidate = re.sub(r'[ \t]+#+[ \t]*$', '', match[1]).strip()
                if candidate != title and len(candidate) <= 240 and not re.search(r'\sVersion Texte\b', candidate):
                    heading = candidate
                    break
            body = (f'<nav aria-label="Navigation dans le volume">{nav}</nav>\n'
                    f'<h1>{escape(title)} · {label}</h1>\n'
                    f'<p>{VERSION} · {DATE_LABEL} · lignes {first_line} à {last_line} · '
                    f'{link(stem + ".md", "Ce bloc en Markdown")}</p>\n'
                    f'<article>{fragment}</article>\n'
                    f'<nav aria-label="Suite de la lecture">{nav}</nav>')
            html = write(html_name, document(f'{title} · {label} · {VERSION}', DESCRIPTION,
                                             canonical + html_name, body, canonical + md_name))
            manifest['blocs'].append({'numero': part, 'titre_repere': heading,
                                      'debut_octet': start, 'fin_octet_exclue': end,
                                      'premiere_ligne': first_line, 'derniere_ligne': last_line,
                                      'markdown': markdown, 'html': html})
            size = f'{len(block) / 1000:.0f} Ko'
            hint = f' · {escape(heading)}' if heading else ''
            rows.append(f'<li>{label}{hint} · {link(html_name, "HTML")} · {link(md_name, "Markdown")} · {size}</li>')
            hint = f' · {_label(heading)}' if heading else ''
            md_contents.append(f'- {label}{hint} · {_markdown_link(html_name, "HTML")} · {_markdown_link(md_name, "Markdown")} · {size}')
        md_contents.append('')
        html_contents.append(f'<h3 id="{slug}">{escape(title)}</h3>\n<ul>{"".join(rows)}</ul>')
        manifest_volumes.append(manifest)
        book_index.append(f'<li>{link("#" + slug, title)}</li>')
        book_sections.append(
            f'<section class="book-volume" id="{slug}" aria-labelledby="{slug}-titre">'
            f'<h2 id="{slug}-titre">{escape(title)}</h2>'
            f'<article>{"".join(book_parts)}</article>'
            '<p><a href="#sommaire">↑ Sommaire du livre</a></p></section>'
        )

    full_corpus.extend(b'\n\n## Editions publiques disponibles en HTML seul\n\n')
    html_links, manifest_html = [], []
    md_contents.extend(['## Éditions publiques disponibles en HTML seul', ''])
    for slug, target in html_only:
        url = base_url + ('annexes/Registre_Index_Lecture.html' if slug == 'ami-registre' else target)
        label = HTML_ONLY[slug]
        html_links.append(f'<li>{link(url, label)}</li>')
        manifest_html.append({'route': slug, 'titre': label, 'url': url})
        item = f'- {_markdown_link(url, label)}'
        md_contents.append(item)
        full_corpus.extend((item + '\n').encode('utf-8'))

    corpus = write('protocole-aMi.md', full_corpus)
    book_body = f'''<style>
    .book-menu{{position:sticky;top:0;z-index:1;padding:.6rem 0;background:#0c0c13;border-bottom:1px solid #745923}}
    .book-volume{{content-visibility:auto;contain-intrinsic-size:auto 850px;margin:3rem 0;scroll-margin-top:4rem}}
    @media print{{.book-volume{{content-visibility:visible}}.book-menu{{display:none}}}}
    </style>
    <nav class="book-menu" aria-label="Navigation dans le livre"><a href="#sommaire">Sommaire</a> · <a href="#annexes-en-ligne">Éditions complémentaires</a></nav>
    <h1>Le Livre du Protocole de ConScience aMi</h1>
    <p>{VERSION} · {DATE_LABEL} · {credits}</p>
    <p>Les 28 Versions Texte publiques réunies dans ce fichier. Utilise le sommaire ou la recherche de ton navigateur.</p>
    <h2 id="sommaire">Sommaire</h2>
    <ol>{"".join(book_index)}</ol>
    {"".join(book_sections)}
    <section id="annexes-en-ligne"><h2>Éditions publiques complémentaires en ligne</h2><ul>{"".join(html_links)}</ul></section>
    <p>{link(LICENSE, 'Consulter la licence CC BY-SA 4.0')}</p>'''
    book = write(BOOK_NAME, document('Livre du Protocole de ConScience aMi', DESCRIPTION,
                                    canonical + BOOK_NAME, book_body, canonical + 'protocole-aMi.md'))
    resources = (
        (BOOK_NAME, 'Lire le livre en un seul fichier HTML'),
        ('protocole-aMi.md', f'Corpus intégral en Markdown · {file_size(corpus["octets"])}'),
        ('manifeste.json', 'Manifeste des sources et des blocs'),
        ('SHA256SUMS.txt', 'Empreintes SHA-256'),
        (base_url + 'lecture/', 'Éditions publiques courantes'),
        (base_url + 'lecture/fiche/', 'Fiche de lecture du Protocole'),
        (LICENSE, 'Licence CC BY-SA 4.0'),
    )
    md_contents[5:5] = [' · '.join(_markdown_link(url, label) for url, label in resources), '']
    write('index.md', '\n'.join(md_contents) + '\n')
    html_links = ''.join(html_links)
    nav = ' · '.join(link(url, label) for url, label in resources)
    volume_index = ''.join(html_contents)
    body = f'''<h1>{escape(TITLE)}</h1>
<p>{credits}</p>
<h2 id="telechargements">Le livre en un seul fichier</h2>
<p>{link(BOOK_NAME, 'Ouvrir le livre HTML')} · {_download_link(BOOK_NAME, 'Télécharger le livre HTML')} · {_download_link('protocole-aMi.md', 'Télécharger le Markdown pour une IA')}</p>
<p>{note}</p>
<p>{nav} · {link('index.md', 'Sommaire en Markdown')} · {link(ARCHIVE_NAME, 'Télécharger l’édition (ZIP)')}</p>
<h2>Versions Texte</h2>
{volume_index}
<h2>Éditions publiques disponibles en HTML seul</h2>
<ul>{html_links}</ul>'''
    write('index.html', document(TITLE, DESCRIPTION, canonical, body, canonical + 'index.md'))
    write('manifeste.json', json.dumps({
        'schema': 1, 'version': VERSION, 'date': DATE, 'revision_git': REVISION,
        'corpus': corpus, 'livre_html': book, 'sommaire': {'html': hashes['index.html'], 'markdown': hashes['index.md']},
        'versions_texte': manifest_volumes, 'editions_html_seules': manifest_html,
    }, ensure_ascii=False, indent=2) + '\n')
    checksums = ''.join(f'{meta["sha256"]}  {path}\n' for path, meta in sorted(hashes.items()))
    write('SHA256SUMS.txt', checksums)
    with ZipFile(directory / ARCHIVE_NAME, 'w', compression=ZIP_DEFLATED) as archive:
        for name in sorted(hashes):
            info = ZipInfo(name, date_time=(2026, 11, 14, 0, 0, 0))
            archive.writestr(info, (directory / name).read_bytes(), compress_type=ZIP_DEFLATED)
    pages = [canonical, canonical + BOOK_NAME]
    pages.extend(canonical + block['html']['fichier'] for volume in manifest_volumes for block in volume['blocs'])
    add_to_sitemap(site/'sitemap.xml', pages)
