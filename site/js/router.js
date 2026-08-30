import * as V from './views.js';
const routes = [
  [/^#\/$/, V.home],
  [/^#\/sector\/(.+)$/, (m,r)=>V.sector(m,r,m[1])],
  [/^#\/stock\/(\d+)$/, (m,r)=>V.stock(m,r,m[1])],
  [/^#\/portfolio(?:\/([\w-]+))?$/, (m,r)=>V.portfolio(m,r,m[1]||'default')],
];
async function render(){
  const root = document.getElementById('view');
  root.innerHTML = '<div class="loader">Crunching the universe…</div>';
  const h = location.hash || '#/';
  document.querySelectorAll('nav a').forEach(a=>a.classList.toggle('on',
    (a.dataset.nav==='portfolio') ? h.startsWith('#/portfolio') : (h==='#/'||h==='')));
  for(const [re, fn] of routes){
    const m = h.match(re);
    if(m){ try{ await fn(m, root); }catch(e){ root.innerHTML = `<div class="card glass"><h2>Error</h2><p class="muted">${e.message} — build may still be running.</p></div>`; } return; }
  }
}
addEventListener('hashchange', render);
render();
