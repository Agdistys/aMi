"""A complete initial document, progressively enhanced with the existing volume UI."""
from html import escape
import re

from markdown_reading import render_markdown

# First installed and checked on this Webnode page. Other volumes keep their
# existing blocks until their size and installed page have been checked.
FULL_INITIAL_ROUTES = {'ami-complementarite'}

STYLE = '''<style>
[data-ami-full-reading]{box-sizing:border-box;min-width:0;max-width:100%;overflow-wrap:anywhere}
[data-ami-full-reading]>.ami-reading-modes{display:flex;justify-content:center;align-items:center;flex-wrap:wrap;gap:.6rem;margin:.8rem auto;max-width:70rem;padding:.4rem .8rem;font:500 1rem/1.4 Jost,system-ui,sans-serif}
[data-ami-full-reading]>.ami-reading-modes button{font:inherit;min-height:44px;padding:.5rem .9rem;border:1px solid #80652d;border-radius:999px;background:#111119;color:#ffd06a;cursor:pointer}
[data-ami-full-reading]>.ami-reading-modes button[aria-pressed=true]{background:#ffd06a18;border-color:#ffd06a}
[data-ami-full-reading] [hidden]{display:none!important}
[data-ami-full-reading]>.ami-initial-reading{box-sizing:border-box;width:100%;max-width:72rem;margin:1rem auto;padding:clamp(.8rem,3vw,2rem);background:#0c0c13;color:#eee7db;font:400 1rem/1.7 Jost,system-ui,sans-serif;text-align:start;hyphens:none}
.ami-initial-reading :is(h1,h2,h3,h4,h5,h6){color:#ffd06a;line-height:1.3;margin-block:1.8em .7em;scroll-margin-top:6rem}
.ami-initial-reading>header{text-align:center;border-bottom:1px solid #80652d;padding-bottom:1.1rem}
.ami-initial-reading>header h2{font:600 clamp(1.6rem,4vw,2.6rem)/1.2 Georgia,serif;margin:.3rem auto}
.ami-initial-reading a{color:#ffd06a;text-decoration:underline;overflow-wrap:anywhere}
.ami-initial-reading>details{border:1px solid #685536;border-radius:.6rem;padding:.7rem 1rem;margin-block:1rem}.ami-initial-reading>details>summary{color:#ffd06a;cursor:pointer;min-height:44px}
.ami-initial-reading p{margin:.8rem 0}.ami-initial-reading ul,.ami-initial-reading ol{padding-inline-start:1.5rem}
.ami-initial-reading pre,.ami-initial-reading .ami-reading-table{overflow:auto;max-width:100%}
.ami-initial-reading pre{padding:1rem;background:#171620;white-space:pre-wrap}
.ami-initial-reading table{width:100%;border-collapse:collapse;font-size:.95rem}
.ami-initial-reading :is(th,td){border:1px solid #685536;padding:.5rem;vertical-align:top;text-align:start}
.ami-initial-reading blockquote{margin-inline:0;padding-inline:1rem;border-inline-start:2px solid #80652d}
.ami-initial-reading .ami-reading-provenance{font-size:.875rem;color:#c4bfce;border-top:1px solid #685536;margin-top:2rem;padding-top:1rem}
[data-ami-full-reading][data-ami-reading-view=tabs]>.ami-initial-reading{display:none!important}
[data-ami-full-reading][data-ami-reading-view=continuous]>#ami-volume-webnode{display:none!important}
[data-ami-full-reading][data-ami-reading-loading=true]>.ami-initial-reading{display:none!important}
[data-ami-full-reading]>.ami-fluid-loading{display:none;text-align:center;color:#ffd06a;padding:2rem 1rem;font:600 1rem/1.5 Jost,system-ui,sans-serif}
[data-ami-full-reading][data-ami-reading-loading=true]>.ami-fluid-loading{display:block}
[data-ami-full-reading][data-ami-reading-loading=true]>.ami-reading-modes,
[data-ami-full-reading][data-ami-reading-view=styled]>.ami-reading-modes,
[data-ami-full-reading][data-ami-reading-view=styled]>.ami-initial-reading{display:none!important}
html.ami-loading [data-ami-full-reading]>[data-ami-webnode-anchor]::before{display:none!important}
[data-ami-full-reading] #evo .ami-human-entry{text-align:center;margin:1.2rem auto 1.6rem;max-width:25rem}
[data-ami-full-reading] #evo .ami-human-transition{display:block!important;box-sizing:border-box!important;width:min(100%,22rem)!important;min-height:60px!important;margin:.5rem auto!important;padding:.7rem 1.3rem!important;border:1px solid #e6c477!important;border-radius:999px!important;background:linear-gradient(135deg,#312919,#17151b)!important;color:#ffe0a0!important;font:600 clamp(1.45rem,3vw,1.9rem)/1.2 'Cormorant Garamond',Georgia,serif!important;box-shadow:0 0 20px #e6c47720!important;cursor:pointer}
[data-ami-full-reading] #evo .ami-human-hint{font:400 .95rem/1.5 Jost,system-ui,sans-serif!important;color:#cec5b1!important;margin:.4rem auto!important}
[data-ami-full-reading][data-ami-native-reading=fluid] #evo details::details-content{display:block!important;content-visibility:visible!important;height:auto!important}
[data-ami-full-reading] #ami-volume-webnode.ami-view-transition{animation:amiHumanTransition .22s ease-out}
@keyframes amiHumanTransition{from{opacity:.55}to{opacity:1}}
@media(prefers-reduced-motion:reduce){[data-ami-full-reading] #ami-volume-webnode.ami-view-transition{animation:none}}
</style>'''

CONTROLLER = '''<script data-ami-reading-controller>
(() => {
  const block = document.currentScript.closest('[data-ami-full-reading]');
  let ready = false;
  const fallback = setTimeout(() => { delete block.dataset.amiReadingLoading; },28000);
  const observer = new MutationObserver(() => {
    const host = block.querySelector('[data-ami-mounted=true]');
    if (ready || !host) return;
    const cover = host.querySelector('.evo-cover');
    const fluidToggle = host.querySelector('#amiLecture');
    if (!cover || !fluidToggle) return;
    ready = true;
    clearTimeout(fallback);
    const entry = document.createElement('div'); entry.className='ami-human-entry';
    const button = document.createElement('button'); button.type='button';
    button.className='ami-human-transition'; button.setAttribute('aria-controls','evo');
    const hint = document.createElement('p'); hint.className='ami-human-hint';
    hint.id='ami-human-hint'; button.setAttribute('aria-describedby',hint.id);
    entry.append(button,hint); cover.querySelector('h1').after(entry);
    function sync() {
      const fluid = fluidToggle.getAttribute('aria-pressed')==='true';
      button.textContent=fluid?'👤 Vue Humaine':'📖 Lecture fluide';
      button.setAttribute('aria-pressed',String(!fluid));
      hint.textContent=fluid?'Retrouver les onglets et les outils':'Dérouler le volume en gardant sa mise en forme';
      block.dataset.amiNativeReading=fluid?'fluid':'human';
    }
    // Reveal the native details with CSS, without firing hundreds of toggle
    // handlers. Their individual open states survive the round trip.
    function setFluid(on) {
      if (on) host.querySelectorAll('details.chapter template').forEach(template => {
        const chapter=template.closest('details.chapter'), content=chapter.querySelector('.heritage');
        if (content) { content.append(template.content.cloneNode(true)); template.remove(); chapter.dataset.loaded='true'; }
      });
      document.body.classList.toggle('lecture',on);
      fluidToggle.setAttribute('aria-pressed',String(on));
      fluidToggle.classList.toggle('actif',on);
      fluidToggle.title=on?'Revenir à la lecture par onglets':'Lecture fluide — dérouler ce volume';
      sync();
      document.dispatchEvent(new CustomEvent('ami:lecture',{detail:{actif:on}}));
      window.dispatchEvent(new Event('resize'));
    }
    fluidToggle.addEventListener('click',event => {
      event.stopImmediatePropagation();
      setFluid(fluidToggle.getAttribute('aria-pressed')!=='true');
    },true);
    document.addEventListener('ami:lecture',sync);
    button.addEventListener('click',() => {
      fluidToggle.click(); sync();
      host.classList.remove('ami-view-transition'); void host.offsetWidth;
      host.classList.add('ami-view-transition');
      requestAnimationFrame(() => requestAnimationFrame(() => {
        const bar=host.querySelector('#amiBarre');
        const offset=Math.max(0,bar?.getBoundingClientRect().bottom||0);
        scrollTo({top:Math.max(0,cover.getBoundingClientRect().top+scrollY-offset-12),behavior:'instant'});
      }));
    });
    block.dataset.amiReadingView='styled'; delete block.dataset.amiReadingLoading;
    // Reuse the volume's real fluid reading: preserve its cards, figures,
    // tables and preformatted code instead of displaying a flattened export.
    if (fluidToggle.getAttribute('aria-pressed')!=='true') fluidToggle.click();
    sync();
    observer.disconnect();
  });
  observer.observe(block, {childList:true,subtree:true,attributes:true,attributeFilter:['data-ami-mounted']});
})();
</script>'''


def full_initial_block(bootstrap, title, slug, direct, markdown, base_url):
    """Embed every Markdown block. No fetch, truncation, folded panel or noscript."""
    # Keep export metadata and the flattened navigation after the volume,
    # rather than putting toolbar labels before the first paragraph. Retain
    # every source line; only the reading order changes.
    preface = ''
    marker = '\n# Complémentarité\n'
    if slug == 'ami-complementarite' and marker in markdown:
        preface, body = markdown.split(marker, 1)
        markdown = '# Complémentarité\n'+body
    prose = render_markdown(markdown, base_url=base_url)
    prefix = f'ami-initial-{slug}-'
    ids = set(re.findall(r'\bid="([^"]+)"', prose))
    prose = re.sub(r'\bid="([^"]+)"', lambda m:f'id="{prefix}{m[1]}"', prose)
    prose = re.sub(r'href="#([^"]+)"', lambda m:f'href="#{prefix}{m[1]}"' if m[1] in ids else m[0], prose)
    # One document title on the Webnode page; preserve lower-level headings.
    prose = re.sub(r'<(/?)h1(?=[ >])', r'<\1h2', prose)
    headings = re.findall(r'<h2 id="([^"]+)">(.+?)</h2>', prose)
    toc = '<details><summary>Sommaire du volume</summary><ul>'+''.join(
        f'<li><a href="#{anchor}">{label}</a></li>' for anchor,label in headings[1:]
    )+'</ul></details>'
    provenance = ('<footer class="ami-reading-provenance"><h3>Édition, source et repères de navigation</h3>'
                  + re.sub(r'\bid="([^"]+)"',lambda m:f'id="{prefix}source-{m[1]}"',render_markdown(preface,base_url=base_url))
                  + direct+'</footer>') if preface else direct
    title = re.sub(r'\s+· Protocole de ConScience aMi$', '', title)
    return (f'<div data-ami-public-block data-ami-full-reading="{escape(slug,quote=True)}" data-ami-reading-view="continuous">{STYLE}'
            '<script data-ami-reading-prepare>document.currentScript.parentElement.dataset.amiReadingLoading="true";</script>'
            '<div class="ami-fluid-loading" role="status">Chargement Protocole aMi</div>'
            '<nav class="ami-reading-modes" aria-label="Mode de lecture du volume">'
            '<button type="button" data-ami-reading-mode="tabs" hidden aria-pressed="false">Vue à onglets</button>'
            '<button type="button" data-ami-reading-mode="continuous" hidden aria-pressed="true">Lecture continue</button>'
            '<span role="status">Texte intégral · tous les chapitres</span></nav>'
            f'<article class="ami-initial-reading"><header><h2>{escape(title)}</h2>'
            '<p>Lecture intégrale de l’édition publiée. Les chapitres et tableaux sont réunis ci-dessous.</p>'
            f'</header>{toc}{prose}{provenance}</article>{bootstrap}{CONTROLLER}</div>\n')
