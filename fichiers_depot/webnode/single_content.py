"""Static single-content Webnode block. No second article and no volume fetch."""
from html.parser import HTMLParser
from hashlib import sha256
from html import escape
from pathlib import Path
import json

class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text=text;self.lines=[0];self.styles=[];self.links=[]
        self.template=0;self.in_head=False;self.style_start=None;self.body_start=None;self.body_end=None
        for line in text.splitlines(keepends=True):self.lines.append(self.lines[-1]+len(line))
        self.feed(text)
    def at(self):
        line,col=self.getpos();return self.lines[line-1]+col
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='template':self.template+=1
        if tag=='head':self.in_head=True
        if tag=='body' and self.body_start is None:self.body_start=self.at()+len(self.get_starttag_text())
        if tag=='style' and not self.template:self.style_start=self.at()
        if tag=='link' and self.in_head and attrs.get('rel') in ('stylesheet','preconnect'):
            self.links.append(self.get_starttag_text())
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs)
    def handle_endtag(self,tag):
        if tag=='head':self.in_head=False
        if tag=='body':self.body_end=self.at()
        if tag=='style' and self.style_start is not None:
            self.styles.append((self.style_start,self.at()+len('</style>')));self.style_start=None
        if tag=='template':self.template-=1
    def style_source(self):return '\n'.join(self.text[a:b] for a,b in self.styles)
    def body(self):
        assert self.body_start is not None and self.body_end is not None
        text=self.text[self.body_start:self.body_end]
        for a,b in reversed(self.styles):
            if self.body_start<=a<b<=self.body_end:text=text[:a-self.body_start]+text[b-self.body_start:]
        return text

def single_content_block(html, source, site, pages):
    doc=Document(html);directory=Path(source)/'fichiers_depot/webnode/single-content'
    manifest=json.loads((directory/'complementarite.json').read_text())
    if sha256(doc.style_source().encode()).hexdigest()!=manifest['source_styles_sha256']:
        raise ValueError('CSS Complémentarité modifiée : recompiler le style isolé avant publication.')
    css=(directory/'complementarite.css').read_bytes();digest=sha256(css).hexdigest()
    target=Path(site)/'webnode/single-content';target.mkdir(parents=True,exist_ok=True)
    (target/(digest+'.css')).write_bytes(css)
    href=pages+'webnode/single-content/'+digest+'.css'
    return ('<div id="ami-single-webnode" data-ami-public-block data-ami-single-content="ami-complementarite">'
            +''.join(doc.links)+'<link rel="stylesheet" href="'+escape(href,quote=True)+'">'
            '<script>document.body.classList.add("lecture");</script>'+doc.body()+
            '''<script>(()=>{const root=document.getElementById('ami-single-webnode');for(let p=root.parentElement;p&&p!==document.body;p=p.parentElement){const s=getComputedStyle(p);if(s.overflowX==='hidden')p.style.overflowX='clip';if(s.overflowY==='hidden')p.style.overflowY='visible';}window.dispatchEvent(new Event('resize'));})();</script></div>''')
