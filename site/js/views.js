import { j, inr, num, pct } from './api.js';
import { clearCharts, bar, donut } from './charts.js';
const el = h => { const t = document.createElement('template'); t.innerHTML = h.trim(); return t.content.firstChild; };

export async function home(_, root){
  clearCharts();
  const [meta, index, sectors, macro] = await Promise.all([j('meta.json'), j('index.json'), j('sectors.json'), j('macro.json')]);
  const withPrice = index.filter(s=>s.price!=null);
  const breadth = Math.round(withPrice.filter(s=>(s.chg||0)>0).length / Math.max(1,withPrice.length) * 100);
  root.innerHTML = `
    <section class="hero glass"><h1>Institutional-grade intelligence for <span>Indian equities</span>.</h1>
      <p>${meta.sectors} sectors · ${meta.companies} companies · refreshed ${new Date(meta.built_at).toLocaleString('en-IN')}</p></section>
    <section class="card glass"><h2>India Macro Pulse</h2><div class="kpis" id="mac"></div></section>
    <section class="kpis">
      <div class="kpi glass"><label>Universe</label><div class="v">${meta.companies}</div><div class="s">companies</div></div>
      <div class="kpi glass"><label>Priced</label><div class="v">${withPrice.length}</div><div class="s">coverage</div></div>
      <div class="kpi glass"><label>Breadth</label><div class="v ${breadth>=50?'up':'dn'}">${breadth}%</div><div class="s">advancing</div></div>
    </section>
    <section class="card glass"><h2>Sector Command Centre</h2><div class="grid-sectors" id="sg"></div></section>
    <section class="card glass"><h2>Top Movers</h2><div class="tbl" id="mv"></div></section>`;
  root.querySelector('#mac').innerHTML = macro.map(m=>`<div class="kpi glass"><label>${m.indicator}</label>
    <div class="v ${m.change_pct==null?'':(m.change_pct>=0?'up':'dn')}">${num(m.value)}</div>
    <div class="s">${m.change_pct==null?'policy':pct(m.change_pct)}</div></div>`).join('');
  const sg = root.querySelector('#sg');
  Object.values(sectors).sort((a,b)=>(b.avg_score||0)-(a.avg_score||0)).forEach(s=>{
    sg.appendChild(el(`<div class="sector-card glass" onclick="location.hash='#/sector/${s.slug}'">
      <span class="score-pill">${s.avg_score ?? '—'}</span><h3>${s.name}</h3>
      <div class="ind">${s.count} companies · ${s.playbook}</div>
      <div class="muted" style="font-size:12px">Top: ${s.top?.[0]?.name ?? '—'}</div></div>`));
  });
  const movers = [...withPrice].sort((a,b)=>(b.chg||0)-(a.chg||0)).slice(0,10);
  root.querySelector('#mv').innerHTML = `<table><thead><tr><th>Company</th><th>Sector</th><th>Price</th><th>Chg</th><th>Score</th></tr></thead><tbody>` +
    movers.map(s=>`<tr onclick="location.hash='#/stock/${s.code}'"><td>${s.name}</td><td><span class="chip">${s.sector}</span></td><td>${inr(s.price)}</td><td class="${(s.chg||0)>=0?'up':'dn'}">${pct(s.chg)}</td><td><b>${s.score ?? '—'}</b></td></tr>`).join('') + `</tbody></table>`;
}

export async function sector(_, root, s){
  clearCharts();
  const d = await j(`sector__${s}.json`); const m = d.meta;
  const scoreable = (m.metrics||[]).filter(x=>x.scorable);
  const qualitative = (m.metrics||[]).filter(x=>!x.scorable);
  
  root.innerHTML = `
    <section class="hero glass"><h1>${m.name}</h1>
      <p>${m.brief || 'Playbook research in progress.'}</p>
      <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
        <span class="chip">${m.count} companies</span>
        <span class="chip good">${m.playbook}</span>
        ${(m.regulators||[]).map(r=>`<span class="chip">${r}</span>`).join('')}
      </div></section>
    
    ${m.macro_sensitivities?.length ? `<section class="card glass"><h2>Macro Sensitivities</h2>
      <div style="display:flex;gap:8px;flex-wrap:wrap">${m.macro_sensitivities.map(ms=>`<span class="chip warn">${ms}</span>`).join('')}</div></section>` : ''}
    
    <section class="card glass"><h2>Sector Combined Analysis</h2><div class="kpis">
      <div class="kpi glass"><label>Avg Score</label><div class="v">${m.avg_score ?? '—'}</div></div>
      <div class="kpi glass"><label>Avg ROCE</label><div class="v">${num(m.avg_roce)}</div></div>
      <div class="kpi glass"><label>Avg ROE</label><div class="v">${num(m.avg_roe)}</div></div>
      <div class="kpi glass"><label>Avg P/E</label><div class="v">${num(m.avg_pe)}</div></div>
      <div class="kpi glass"><label>Avg D/E</label><div class="v">${num(m.avg_de)}</div></div>
      <div class="kpi glass"><label>Momentum</label><div class="v ${(m.momentum||0)>=0?'up':'dn'}">${pct(m.momentum)}</div></div>
    </div></section>
    
    ${m.red_flags?.length ? `<section class="card glass"><h2>⚠️ Red Flags — Institutional Kill Switches</h2>
      <div>${m.red_flags.map(rf=>`<div style="margin:10px 0;padding:12px;background:rgba(251,113,133,.08);border:1px solid rgba(251,113,133,.25);border-radius:12px">
        <b style="color:#fda4af">${rf.flag || rf.metric || rf.condition || "Unknown"}</b><br><span class="muted" style="font-size:13px">${rf.reason}</span></div>`).join('')}</div></section>` : ''}
    
    ${scoreable.length ? `<section class="card glass"><h2>Quantitative Screening Lens (${scoreable.length} metrics)</h2><div class="tbl">
      <table><thead><tr><th>Metric</th><th>Lens</th><th>Weight</th><th>Direction</th><th>Indian Nuance</th></tr></thead><tbody>
      ${scoreable.map(mt=>`<tr style="cursor:default"><td><b>${mt.metric_name}</b></td><td><span class="chip">${mt.lens}</span></td><td>${'★'.repeat(mt.weight||1)}</td><td class="${mt.direction==='higher'?'up':'dn'}">${mt.direction==='higher'?'↑ Higher':'↓ Lower'}</td><td class="muted" style="font-size:12px;max-width:300px;white-space:normal">${mt.indian_nuance||''}</td></tr>`).join('')}
      </tbody></table></div></section>` : ''}
    
    ${qualitative.length ? `<section class="card glass"><h2>Qualitative Indicators (${qualitative.length} metrics)</h2><div class="tbl">
      <table><thead><tr><th>Metric</th><th>Lens</th><th>Weight</th><th>Direction</th><th>Indian Nuance</th></tr></thead><tbody>
      ${qualitative.map(mt=>`<tr style="cursor:default"><td><b>${mt.metric_name}</b></td><td><span class="chip">${mt.lens}</span></td><td>${'★'.repeat(mt.weight||1)}</td><td class="${mt.direction==='higher'?'up':'dn'}">${mt.direction==='higher'?'↑ Higher':'↓ Lower'}</td><td class="muted" style="font-size:12px;max-width:300px;white-space:normal">${mt.indian_nuance||''}</td></tr>`).join('')}
      </tbody></table></div>
      <p class="muted" style="margin-top:10px;font-size:12px">ℹ️ These metrics require regulatory filings, concall transcripts, or proprietary data sources not available in Screener.in. They are displayed for analyst context.</p></section>` : ''}
    
    ${m.competitive_landscape ? `<section class="card glass"><h2>Competitive Landscape</h2><p class="muted">${m.competitive_landscape}</p></section>` : ''}
    
    <section class="split">
      <div class="card glass"><h2>Leaderboard — Composite Score</h2><div class="chart-box"><canvas id="c1"></canvas></div></div>
      <div class="card glass"><h2>Full Universe</h2><div class="tbl" id="t"></div></div>
    </section>`;
    
  const top = d.stocks.slice(0,10);
  bar('c1', top.map(x=>x.name.split(' ')[0]), top.map(x=>x.score||0), 'Score', '#22d3ee');
  root.querySelector('#t').innerHTML = `<table><thead><tr><th>#</th><th>Company</th><th>Industry</th><th>Price</th><th>Chg</th><th>Score</th></tr></thead><tbody>` +
    d.stocks.map((x,i)=>`<tr onclick="location.hash='#/stock/${x.code}'"><td>${i+1}</td><td>${x.name}</td><td class="muted">${x.industry}</td><td>${inr(x.price)}</td><td class="${(x.chg||0)>=0?'up':'dn'}">${pct(x.chg)}</td><td><b>${x.score ?? '—'}</b></td></tr>`).join('') + `</tbody></table>`;
}

function sectionTable(sec){
  if(!sec || typeof sec !== 'object') return '<p class="muted">No data.</p>';
  const rows = Object.entries(sec);
  const years = [...new Set(rows.flatMap(([,v]) => (v && typeof v==='object') ? Object.keys(v) : []))].sort();
  if(!years.length) return '<p class="muted">No tabular data.</p>';
  return `<div class="tbl"><table><thead><tr><th>Metric</th>${years.map(y=>`<th>${y}</th>`).join('')}</tr></thead><tbody>` +
    rows.map(([k,v])=>`<tr style="cursor:default"><td>${k}</td>${years.map(y=>`<td>${num(typeof v==='object'?v[y]:v)}</td>`).join('')}</tr>`).join('') + `</tbody></table></div>`;
}

export async function stock(_, root, code){
  clearCharts();
  const d = await j(`stock__${code}.json`); const r = d.raw;
  root.innerHTML = `
    <section class="hero glass">
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px"><span class="chip">${d.sector}</span><span class="chip">${d.industry}</span><span class="chip good">Score ${d.score ?? '—'}</span></div>
      <h1>${d.name} <span style="font-size:.5em" class="${(d.chg||0)>=0?'up':'dn'}">${inr(d.price)} · ${pct(d.chg)}</span></h1></section>
    <div class="tabs" id="tabs"></div>
    <section class="card glass" id="body"></section>`;
  const tabs = [['overview','Overview'],['pl','P & L'],['bs','Balance Sheet'],['cf','Cash Flow'],['ratios','Ratios'],['sh','Shareholding'],['docs','Documents']];
  const body = root.querySelector('#body');
  const render = {
    overview(){
      const cags = Object.entries(r.CAGRs||{}).map(([k,v])=>[k, typeof v==='object'?Object.values(v).pop():v]).filter(([,v])=>v!=null);
      body.innerHTML = `<div class="split"><div><h2>Strengths</h2><ul class="pros">${(r.analysis?.pros||[]).map(p=>`<li>✔ ${p}</li>`).join('')||'<p class="muted">—</p>'}</ul></div>
      <div><h2>Risks</h2><ul class="cons">${(r.analysis?.cons||[]).map(p=>`<li>⚠ ${p}</li>`).join('')||'<p class="muted">—</p>'}</ul></div></div>
      <h2 style="margin-top:18px">Growth CAGRs</h2><div class="chart-box"><canvas id="cc"></canvas></div>`;
      bar('cc', cags.map(([k])=>k), cags.map(([,v])=>v), 'CAGR %', '#a78bfa');
    },
    pl(){ body.innerHTML = `<h2>Profit & Loss</h2>` + sectionTable(r.profitLoss); },
    bs(){ body.innerHTML = `<h2>Balance Sheet</h2>` + sectionTable(r.balanceSheet); },
    cf(){ body.innerHTML = `<h2>Cash Flow</h2>` + sectionTable(r.cashFlow); },
    ratios(){ body.innerHTML = `<h2>Key Ratios</h2>` + sectionTable(r.ratios); },
    sh(){ body.innerHTML = `<h2>Shareholding Pattern</h2>` + sectionTable(r.shareholding); },
    docs(){ body.innerHTML = `<h2>Documents</h2>` + Object.entries(r.documents||{}).map(([k,v])=>`<p style="margin:6px 0"><span class="chip">${k}</span> ${typeof v==='string'?`<a href="${v}" target="_blank" style="color:#a5b4fc">link</a>`:''}</p>`).join('') || '<p class="muted">—</p>'; }
  };
  const tb = root.querySelector('#tabs');
  tabs.forEach(([id,label],i)=>{
    const b = el(`<button class="${i===0?'on':''}">${label}</button>`);
    b.onclick = ()=>{ tb.querySelectorAll('button').forEach(x=>x.classList.remove('on')); b.classList.add('on'); clearCharts(); render[id](); };
    tb.appendChild(b);
  });
  render.overview();
}

export async function portfolio(_, root, cid){
  clearCharts();
  const meta = await j('meta.json'); const p = await j(`portfolio__${cid}.json`);
  root.innerHTML = `
    <section class="hero glass" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
      <div><h1>${p.client}</h1><p>Multi-client ready · ${meta.portfolios.length} portfolio(s)</p></div>
      <select onchange="location.hash='#/portfolio/'+this.value">${meta.portfolios.map(id=>`<option value="${id}" ${id===cid?'selected':''}>${id}</option>`).join('')}</select></section>
    <section class="kpis">
      <div class="kpi glass"><label>Invested</label><div class="v">${inr(p.invested)}</div></div>
      <div class="kpi glass"><label>Current</label><div class="v">${inr(p.current)}</div></div>
      <div class="kpi glass"><label>P&L</label><div class="v ${(p.pnl||0)>=0?'up':'dn'}">${inr(p.pnl)}</div></div>
      <div class="kpi glass"><label>XIRR</label><div class="v ${(p.xirr||0)>=0?'up':'dn'}">${p.xirr!=null?p.xirr+'%':'—'}</div></div>
    </section>
    ${p.warnings.length?`<section class="card glass"><h2>Risk Desk — Guidance</h2>${p.warnings.map(w=>`<p style="margin:6px 0"><span class="chip warn">⚠ ${w}</span></p>`).join('')}</section>`:''}
    <section class="split">
      <div class="card glass"><h2>Allocation</h2><div class="chart-box"><canvas id="al"></canvas></div></div>
      <div class="card glass"><h2>Holdings</h2><div class="tbl" id="h"></div></div>
    </section>`;
  donut('al', Object.keys(p.allocation), Object.values(p.allocation));
  root.querySelector('#h').innerHTML = `<table><thead><tr><th>Stock</th><th>Qty</th><th>Avg</th><th>LTP</th><th>Value</th><th>P&L</th></tr></thead><tbody>` +
    p.holdings.map(h=>`<tr onclick="location.hash='#/stock/${h.code}'"><td>${h.name}<br><span class="muted" style="font-size:11px">${h.sector}</span></td><td>${h.qty}</td><td>${inr(h.avg)}</td><td>${inr(h.price)}</td><td>${inr(h.value)}</td><td class="${(h.pnl||0)>=0?'up':'dn'}">${pct(h.pnl_pct)}</td></tr>`).join('') + `</tbody></table>`;
}
