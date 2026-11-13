    function tuneNavigation(root, base) {
      const routes = /* __AMI_NAV_ROUTES__ */ null;
      const nav = root.querySelector('#amiBarre');
      if (!nav) return;
      for (const door of nav.querySelectorAll('button.porte[title]')) {
        door.removeAttribute('title');
      }
      for (const link of nav.querySelectorAll('a[href]')) {
        const href = link.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('?')) continue;
        const url = new URL(href, base);
        let slug;
        if (url.hostname === 'agdistys.github.io' && url.pathname.startsWith('/aMi/')) {
          const path = url.pathname.slice('/aMi/'.length);
          slug = routes.files[path.split(/_V[0-9]/)[0]] || routes.pages[path.replace(/\/$/, '')];
        } else if (['agdistys.fr', 'www.agdistys.fr'].includes(url.hostname)) {
          slug = routes.legacy[url.pathname.replace(/^\/|\/$/g, '')];
        }
        if (!slug) continue;
        link.href = 'https://www.agdistys.fr/' + (routes.webnode[slug] || slug) + '/' + url.search + url.hash;
      }
    }
