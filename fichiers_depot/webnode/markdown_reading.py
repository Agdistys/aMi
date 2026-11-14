"""Render the public aMi Markdown exports as static, escaped HTML fragments."""

from html import escape, unescape
import re
import string
import unicodedata
from urllib.parse import urljoin, urlsplit


HEADING = re.compile(r'^ {0,3}(#{1,6})(?:[ \t]+|$)(.*)$')
LIST_ITEM = re.compile(r'^ {0,3}(?:([-+*])|([0-9]{1,9})[.)])[ \t]+(.+)$')
QUOTE = re.compile(r'^ {0,3}>[ \t]?(.*)$')
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
RULE = re.compile(r'^ {0,3}(?:(?:-[ \t]*){3,}|(?:\*[ \t]*){3,}|(?:_[ \t]*){3,})$')
SETEXT = re.compile(r'^ {0,3}(=+|-+)[ \t]*$')
COLUMN = re.compile(r'^:?-{1,}:?$')
PIPE = re.compile(r'(?<!\\)\|')
INLINE = re.compile(
    r'(?P<escape>\\[' + re.escape(string.punctuation) + r'])'
    r'|(?P<ticks>`+)(?P<code>[^`\n]+)(?P=ticks)(?!`)'
    r'|\[(?P<label>(?:\\.|[^\[\]\\\n]|\[[^\[\]\n]*\])+?)\]'
    r'\([ \t]*(?P<destination><[^<>\n]+>|(?:\\.|[^()\s\\]|\([^()\n]*\))+?)'
    r'(?:[ \t]+(?:"[^"\n]*"|\'[^\'\n]*\'))?[ \t]*\)'
    r'|<(?P<autolink>https?://[^\s<>]+|mailto:[^\s<>]+)>'
    r'|(?P<raw_html><!--[^\n]*?-->|</?[a-zA-Z][\w:-]*(?:\s[^<>\n]*|/)?>)'
    r'|(?P<url>https?://[^\s<>"\'`]+)'
    r'|(?P<mark>\*\*|__|\*|_)(?P<emphasis>[^*_\n]+?)(?P=mark)(?![*_])',
    re.IGNORECASE,
)
UNESCAPE_MARKDOWN = re.compile(r'\\([' + re.escape(string.punctuation) + r'])')


def _text(value):
    return escape(unescape(value), quote=False)


def _href(value, base_url):
    value = unescape(UNESCAPE_MARKDOWN.sub(r'\1', value.removeprefix('<').removesuffix('>')))
    if not value or any(ch.isspace() or ord(ch) < 32 or ch == '\x7f' or ch == '\\' for ch in value):
        return None
    try:
        if base_url and not value.startswith('#'):
            value = urljoin(base_url, value)
        parts = urlsplit(value)
    except ValueError:
        return None
    if parts.scheme not in {'', 'http', 'https', 'mailto'}:
        return None
    if parts.scheme in {'http', 'https'} and not parts.netloc:
        return None
    return escape(value, quote=True)


def _trim_url(value):
    end = value.rstrip('.,;:!?…»”’')
    for close, opening in ((')', '('), (']', '['), ('}', '{')):
        while end.endswith(close) and end.count(close) > end.count(opening):
            end = end[:-1]
    return end, value[len(end):]


def _inline(value, base_url, *, links=True):
    parts, end = [], 0
    for match in INLINE.finditer(value):
        parts.append(_text(value[end:match.start()]))
        end = match.end()
        if match['escape']:
            parts.append(escape(match['escape'][1], quote=False))
        elif match['code']:
            code = match['code']
            if code.startswith(' ') and code.endswith(' ') and code.strip():
                code = code[1:-1]
            parts.append(f'<code>{escape(code, quote=False)}</code>')
        elif match['label'] and links:
            href = _href(match['destination'], base_url)
            label = _inline(match['label'], base_url, links=False)
            parts.append(f'<a href="{href}">{label}</a>' if href is not None else _text(match[0]))
        elif links and (match['autolink'] or match['url']):
            url, suffix = (match['autolink'], '') if match['autolink'] else _trim_url(match['url'])
            href = _href(url, base_url)
            parts.append(f'<a href="{href}">{_text(url)}</a>{_text(suffix)}' if href is not None else _text(match[0]))
        elif match['emphasis'] and match['emphasis'] == match['emphasis'].strip() and (
            match['mark'].startswith('*') or not (
                value[match.start() - 1:match.start()].isalnum() or value[end:end + 1].isalnum()
            )
        ):
            tag = 'strong' if len(match['mark']) == 2 else 'em'
            parts.append(f'<{tag}>{_inline(match["emphasis"], base_url, links=links)}</{tag}>')
        else:
            parts.append(_text(match[0]))
    parts.append(_text(value[end:]))
    return ''.join(parts)


def _cells(line):
    line = line.strip().removeprefix('|')
    if line.endswith('|') and not line.endswith(r'\|'):
        line = line[:-1]
    return [cell.strip() for cell in PIPE.split(line)]


def _columns(header, separator):
    if '|' not in header or '|' not in separator:
        return []
    cells = _cells(separator)
    return cells if len(cells) == len(_cells(header)) and all(COLUMN.fullmatch(cell) for cell in cells) else []


def _table(headings, columns, rows, inline):
    size = max(map(len, [headings, *rows]))
    alignments = []
    for col in columns:
        left, right = col.startswith(':'), col.endswith(':')
        direction = 'center' if left and right else 'left' if left else 'right' if right else ''
        alignments.append(f' class="align-{direction}"' if direction else '')
    alignments.extend([''] * (size - len(alignments)))

    def row(cells, tag, attributes=''):
        cells = cells + [''] * (size - len(cells))
        return '<tr>' + ''.join(f'<{tag}{attributes}{align}>{inline(cell)}</{tag}>'
                                for align, cell in zip(alignments, cells)) + '</tr>'

    header = row(headings, 'th', ' scope="col"')
    body = '\n'.join(row(cells, 'td') for cells in rows)
    return f'<div class="ami-reading-table"><table>\n<thead>{header}</thead>\n<tbody>\n{body}\n</tbody>\n</table></div>'


def render_markdown(markdown: str, *, base_url: str = '') -> str:
    """Render headings, tables, links, and the other blocks used by the aMi exports.

    Keep the export's line breaks in ordinary prose. Treat raw HTML as text and
    allow only relative, HTTP(S), and mailto links. This is an export renderer,
    so it does not implement the entire CommonMark grammar.
    """
    lines = markdown.splitlines()
    output, paragraph, used_ids = [], [], set()

    def inline(value):
        return _inline(value, base_url)

    def flush_paragraph():
        if paragraph:
            output.append('<p>' + '<br>\n'.join(inline(line) for line in paragraph) + '</p>')
            paragraph.clear()

    def heading(value, level):
        content = inline(value)
        text = unicodedata.normalize('NFC', unescape(value).strip().lower())
        stem = ''.join('-' if ch.isspace() else ch for ch in text if ch.isalnum() or ch in '-_' or ch.isspace())
        anchor, suffix = stem or 'section', 1
        while anchor in used_ids:
            anchor = f'{stem or "section"}-{suffix}'
            suffix += 1
        used_ids.add(anchor)
        return f'<h{level} id="{anchor}">{content}</h{level}>'

    i = 0
    while i < len(lines):
        line = lines[i]
        following = lines[i + 1] if i + 1 < len(lines) else ''
        if not line.strip():
            flush_paragraph()
            i += 1
            continue
        columns = _columns(line, following)
        if columns:
            flush_paragraph()
            rows, i = [], i + 2
            while i < len(lines) and PIPE.search(lines[i]):
                rows.append(_cells(lines[i]))
                i += 1
            output.append(_table(_cells(line), columns, rows, inline))
            continue
        if match := HEADING.fullmatch(line):
            flush_paragraph()
            title = re.sub(r'[ \t]+#+[ \t]*$', '', match[2]).strip()
            output.append(heading(title, len(match[1])))
        elif match := FENCE.fullmatch(line):
            flush_paragraph()
            marker, code = match[1], []
            closing = re.compile(r' {0,3}' + marker[0] + '{' + str(len(marker)) + r',}[ \t]*')
            i += 1
            while i < len(lines) and not closing.fullmatch(lines[i]):
                code.append(lines[i])
                i += 1
            output.append('<pre><code>' + escape('\n'.join(code), quote=False) + '</code></pre>')
        elif RULE.fullmatch(line):
            flush_paragraph()
            output.append('<hr>')
        elif match := LIST_ITEM.fullmatch(line):
            flush_paragraph()
            ordered = match[2] is not None
            tag = 'ol' if ordered else 'ul'
            expected = int(match[2]) if ordered else 1
            start = f' start="{expected}"' if expected != 1 else ''
            items = []
            while match and (match[2] is not None) == ordered:
                number = int(match[2]) if ordered else expected
                value = f' value="{number}"' if number != expected else ''
                items.append(f'<li{value}>{inline(match[3])}</li>')
                expected, i = number + 1, i + 1
                match = LIST_ITEM.fullmatch(lines[i]) if i < len(lines) else None
            output.append(f'<{tag}{start}>\n' + '\n'.join(items) + f'\n</{tag}>')
            continue
        elif match := QUOTE.fullmatch(line):
            flush_paragraph()
            quoted = []
            while match:
                quoted.append(inline(match[1]))
                i += 1
                match = QUOTE.fullmatch(lines[i]) if i < len(lines) else None
            output.append('<blockquote><p>' + '<br>\n'.join(quoted) + '</p></blockquote>')
            continue
        elif match := SETEXT.fullmatch(following):
            flush_paragraph()
            output.append(heading(line.strip(), 1 if match[1][0] == '=' else 2))
            i += 1
        else:
            paragraph.append(line.strip())
        i += 1
    flush_paragraph()
    return '\n'.join(output)
