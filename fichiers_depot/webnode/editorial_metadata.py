"""Small date/source controls for editorial additions to autonomous aMi volumes."""
from datetime import date
from hashlib import sha256
from html import escape


def date_note(iso_date, source_title, source_url, edition='', key=''):
    d = date.fromisoformat(iso_date)
    months = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']
    label = f'{d.day} {months[d.month-1]} {d.year}'
    uid = 'ami-date-' + sha256((iso_date+source_url+edition+key).encode()).hexdigest()[:14]
    return (
        f'<button class="ami-date-note" type="button" aria-expanded="false" '
        f'aria-controls="{uid}" title="Ajout du {escape(label)} · date et source" '
        f'aria-label="Date et source de cet ajout : {escape(label)}"><span aria-hidden="true">(📆)</span></button>'
        f'<span class="ami-date-pop" id="{uid}" role="note" hidden>'
        f'<strong>Ajout du <time datetime="{escape(iso_date)}">{escape(label)}</time></strong><br>'
        f'<a href="{escape(source_url,quote=True)}" target="_blank" rel="noopener">{escape(source_title)}</a>'
        +(f'<br><small>{escape(edition)}</small>' if edition else '')+'</span>'
    )


SCRIPT = r'''(function(){'use strict';if(window.__amiEditorialDate)return;window.__amiEditorialDate=true;
var current=null,home=null,next=null;
function close(){if(!current)return;var box=document.getElementById(current.getAttribute('aria-controls'));if(box){if(typeof box.hidePopover==='function'&&box.matches(':popover-open'))box.hidePopover();box.hidden=true;if(home)home.insertBefore(box,next&&next.parentNode===home?next:null);}current.setAttribute('aria-expanded','false');current=null;home=null;next=null;}
function place(button,box){var r=button.getBoundingClientRect();box.hidden=false;if(typeof box.showPopover==='function'){box.setAttribute('popover','manual');box.showPopover();}else{home=box.parentNode;next=box.nextSibling;document.body.appendChild(box);}box.style.left='16px';box.style.top='16px';var b=box.getBoundingClientRect();var width=document.documentElement.clientWidth||window.innerWidth;var height=window.innerHeight;var x=Math.max(12,Math.min(r.left,width-b.width-12));var y=r.bottom+8;if(y+b.height>height-12)y=Math.max(12,r.top-b.height-8);box.style.left=x+'px';box.style.top=y+'px';}
document.addEventListener('click',function(e){var button=e.target.closest&&e.target.closest('button.ami-date-note');if(button){var was=current===button;close();if(!was){var box=document.getElementById(button.getAttribute('aria-controls'));if(box){current=button;button.setAttribute('aria-expanded','true');place(button,box);}}return;}if(current&&!(e.target.closest&&e.target.closest('.ami-date-pop')))close();});
document.addEventListener('keydown',function(e){if(e.key==='Escape'&&current){var button=current;close();button.focus();}});
window.addEventListener('resize',close,{passive:true});document.addEventListener('scroll',close,{passive:true,capture:true});
})();'''


def install_date_notes(document, root_id):
    assert document.count('id="'+root_id+'"') == 1, root_id
    # A provenance note is a floating note, not a sticky navigation bar.
    scanner = 'tous.forEach(function(e){\n     var c = getComputedStyle(e);'
    if scanner in document:
        assert document.count(scanner) == 1
        document = document.replace(scanner, "tous.forEach(function(e){\n     if(e.classList.contains('ami-date-pop'))return;\n     var c = getComputedStyle(e);", 1)
    prefix = '#'+root_id
    css = '''ROOT button.ami-date-note{font:inherit!important;font-size:.7em!important;line-height:1.2!important;letter-spacing:normal!important;text-transform:none!important;color:inherit!important;background:transparent!important;border:0!important;padding:.12em .35em!important;display:inline-flex!important;align-items:center;justify-content:center;vertical-align:middle;cursor:pointer;border-radius:.3em;margin:0 .12em;box-shadow:none!important;min-width:0!important;width:auto!important;height:auto!important}
ROOT button.ami-date-note span{font:inherit!important;pointer-events:none}
ROOT button.ami-date-note:hover,ROOT button.ami-date-note:focus-visible{outline:1px solid currentColor;outline-offset:2px;background:rgba(255,208,106,.08)!important}
ROOT span.ami-date-pop{position:fixed!important;z-index:2147482500!important;display:block!important;box-sizing:border-box!important;width:max-content!important;max-width:min(28rem,calc(100vw - 24px))!important;max-height:calc(100vh - 24px)!important;overflow:auto!important;padding:.85rem 1rem!important;border:1px solid #8a6d2c!important;border-radius:10px!important;background:#12121b!important;color:#eee9df!important;font:400 .9rem/1.55 Jost,system-ui,sans-serif!important;letter-spacing:normal!important;text-transform:none!important;white-space:normal!important;box-shadow:0 8px 32px #0009!important;text-align:left!important}
ROOT span.ami-date-pop[hidden]{display:none!important}
ROOT span.ami-date-pop a{color:#ffd06a!important;text-decoration:underline!important}
ROOT span.ami-date-pop small{font-size:.82em!important;color:#b9b5c5!important}
ROOT .ami-date-pop strong{font-weight:600!important;color:#eee9df!important}
'''.replace('position:fixed!important;z-index:', 'position:fixed!important;margin:0!important;right:auto!important;bottom:auto!important;z-index:').replace('ROOT span.ami-date-pop','span.ami-date-pop').replace('ROOT .ami-date-pop','.ami-date-pop').replace('ROOT',prefix)
    addition='<style id="ami-editorial-date-css">'+css+'</style>'
    script='<script id="ami-editorial-date-js">'+SCRIPT+'</script>'
    assert 'id="ami-editorial-date-css"' not in document
    assert '</head>' in document and '</body>' in document
    return document.replace('</head>',addition+'</head>',1).replace('</body>',script+'</body>',1)
