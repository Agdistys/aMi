"""Static single-content Webnode block. No second article and no volume fetch."""
from html.parser import HTMLParser
from hashlib import sha256
from html import escape
from pathlib import Path
import json
import re,base64

class Resources(HTMLParser):
    def __init__(self,text,target,url):
        super().__init__(convert_charrefs=False)
        self.text=text;self.target=target;self.url=url;self.edits=[];self.script=None;self.template=0;self.lines=[0]
        for line in text.splitlines(keepends=True):self.lines.append(self.lines[-1]+len(line))
        self.feed(text)
    def at(self):
        line,col=self.getpos();return self.lines[line-1]+col
    def asset(self,data,suffix):
        name=sha256(data).hexdigest()+suffix;(self.target/name).write_bytes(data);return self.url+name
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs);raw=self.get_starttag_text();at=self.at()
        if tag=='template':self.template+=1
        if tag=='img' and attrs.get('src','').startswith('data:image/'):
            match=re.fullmatch(r'data:image/(png|jpeg|webp|gif|svg\+xml);base64,(.*)',attrs['src'],re.S)
            if match:
                url=self.asset(base64.b64decode(match[2]),'.'+('svg' if match[1]=='svg+xml' else match[1]))
                new=re.sub(r'\bsrc=([\"\'])data:image/.*?\1','src="'+url+'"',raw,flags=re.S)
                self.edits.append((at,at+len(raw),new))
        if tag=='script' and not self.template and not attrs.get('src') and attrs.get('type','').lower() in ('','text/javascript','application/javascript'):
            self.script=(at,at+len(raw),raw)
    def handle_endtag(self,tag):
        if tag=='script' and self.script:
            a,start,raw=self.script;end=self.at();url=self.asset(self.text[start:end].encode(),'.js')
            self.edits.append((a,end+len('</script>'),raw[:-1]+' src="'+url+'"></script>'));self.script=None
        if tag=='template':self.template-=1
    def result(self):
        text=self.text
        for a,b,value in reversed(self.edits):text=text[:a]+value+text[b:]
        return text

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
    body=Resources(doc.body(),target,pages+'webnode/single-content/').result()
    return ('<div id="ami-single-webnode" data-ami-public-block data-ami-single-content="ami-complementarite">'
            +''.join(doc.links)+'<link rel="stylesheet" href="'+escape(href,quote=True)+'">'
            '<script>document.body.classList.add("lecture");</script>'+body+
            '''<script>(()=>{const root=document.getElementById('ami-single-webnode');for(let p=root.parentElement;p&&p!==document.body;p=p.parentElement){const s=getComputedStyle(p);if(s.overflowX==='hidden')p.style.overflowX='clip';if(s.overflowY==='hidden')p.style.overflowY='visible';}window.dispatchEvent(new Event('resize'));})();</script></div>''')
