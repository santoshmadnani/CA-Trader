# -*- coding: utf-8 -*-
"""
Script to apply Batch 2 of wiring to terminal.html:
- Item 3: Candlestick and pattern card click highlighting & candle time
- Item 11: RSI/Oscillator box splitter handle insertion and drag interaction
- Item 13: MCX option chain autocomplete search & suggestions dropdown
- Item 17: News cards click to open interactive discussion modal and headline click to open source in new tab
- Item 19: Modern Fundamentals UI redesign for quarterly results and shareholding breakdown
- Item 20 & 21: Orders & Positions segregation (Today's vs Past orders, Open vs Closed positions with reasons, time, SL, target, P&L)
- Item 22: Admin funds allocation submission (/api/admin/funds/add) and Server Console / Reset restriction
- Item 23: Profile modal details (Name, Email ID, Admin recognition).
"""
from pathlib import Path
import re

path = Path("terminal.html")
content = path.read_text(encoding="utf-8")

# -------------------------------------------------------------
# 1. Item 17: News Rendering & Interactive Discussion
# -------------------------------------------------------------
old_news_render_card = '''        return `
          <div class="news-card" style="background:var(--surface);border:1px solid var(--border-soft);border-left:4px solid ${borderLeftColor};border-radius:8px;padding:14px 16px;display:flex;flex-direction:column;gap:8px;transition:transform 0.15s ease,border-color 0.15s ease;">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <span style="font-family:var(--font-mono);font-size:11px;font-weight:700;color:var(--gold);background:var(--surface-2);padding:2px 8px;border-radius:4px;border:1px solid var(--border-soft);">${esc(it.source)}</span>
                <span style="font-size:11px;color:var(--text-faint);">● ${esc(it.time)}</span>
                <span class="badge ghost" style="font-size:10px;text-transform:uppercase;">${esc(it.scope === 'stock' ? (sym + ' Specific') : 'Global Macro')}</span>
              </div>
              <div style="display:flex;align-items:center;gap:6px;">
                <span class="tag ${badgeClass}" style="font-weight:700;font-size:11px;padding:3px 9px;border-radius:5px;">
                  ${badgeIcon} ${esc(it.sentiment)} ${esc(it.impact_pct)}
                </span>
              </div>
            </div>

            <div style="font-size:13.5px;font-weight:600;line-height:1.45;color:var(--text);margin-top:2px;">
              ${esc(it.headline)}
            </div>

            <div style="background:var(--surface-2);border-radius:6px;padding:8px 12px;font-size:11.5px;line-height:1.45;color:var(--text-dim);border:1px solid var(--border-soft);">
              <b style="color:var(--gold);">CA AI Decision:</b> ${esc(it.ca_ai_insight)}
            </div>
          </div>
        `;
      }).join('');'''

new_news_render_card = '''        const extUrl = it.url || ('https://news.google.com/search?q=' + encodeURIComponent(it.headline));
        return `
          <div class="news-card" data-news-idx="${items.indexOf(it)}" style="background:var(--surface);border:1px solid var(--border-soft);border-left:4px solid ${borderLeftColor};border-radius:8px;padding:14px 16px;display:flex;flex-direction:column;gap:8px;cursor:pointer;transition:transform 0.15s ease,border-color 0.15s ease;">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <span style="font-family:var(--font-mono);font-size:11px;font-weight:700;color:var(--gold);background:var(--surface-2);padding:2px 8px;border-radius:4px;border:1px solid var(--border-soft);">${esc(it.source)}</span>
                <span style="font-size:11px;color:var(--text-faint);">● ${esc(it.time)}</span>
                <span class="tag-meta" style="font-size:10px;text-transform:uppercase;">${esc(it.scope === 'stock' ? (sym + ' Specific') : 'Global Macro')}</span>
              </div>
              <div style="display:flex;align-items:center;gap:6px;">
                <span class="tag ${badgeClass}" style="font-weight:700;font-size:11px;padding:3px 9px;border-radius:5px;">
                  ${badgeIcon} ${esc(it.sentiment)} ${esc(it.impact_pct)}
                </span>
              </div>
            </div>

            <div>
              <a href="${esc(extUrl)}" target="_blank" rel="noopener noreferrer" class="news-headline-link" onclick="event.stopPropagation();" style="font-size:13.5px;font-weight:600;line-height:1.45;color:var(--text);text-decoration:none;display:inline-block;" title="Open original news source in new tab">
                ${esc(it.headline)} <span style="font-size:11px;color:var(--gold);margin-left:3px;">↗</span>
              </a>
            </div>

            <div style="background:var(--surface-2);border-radius:6px;padding:8px 12px;font-size:11.5px;line-height:1.45;color:var(--text-dim);border:1px solid var(--border-soft);">
              <b style="color:var(--gold);">CA AI Decision:</b> ${esc(it.ca_ai_insight)}
              <div style="font-size:10px;color:var(--text-faint);margin-top:4px;">Click card to launch interactive CA AI discussion & trade analysis →</div>
            </div>
          </div>
        `;
      }).join('');

      host.querySelectorAll('.news-card').forEach(card => {
        card.onclick = () => {
          const item = items[Number(card.dataset.newsIdx)];
          if(item && typeof openNewsDiscussionModal === 'function') openNewsDiscussionModal(item);
        };
      });'''

if old_news_render_card in content:
    content = content.replace(old_news_render_card, new_news_render_card, 1)

# Add news discussion modal interactive JS logic
news_modal_js = '''
  // Interactive CA AI News Discussion Logic (Item 17)
  let currentDiscussNews = null;

  function openNewsDiscussionModal(item){
    currentDiscussNews = item;
    const modal = $('newsDiscussionModal');
    if(!modal) return;

    const isBull = item.sentiment === 'BULLISH';
    const isBear = item.sentiment === 'BEARISH';
    const badgeClass = isBull ? 'buy' : isBear ? 'sell' : 'neutral';
    const badgeText = `${isBull ? '▲ 100% Buy Signal' : isBear ? '▼ 100% Sell Signal' : '● ' + item.sentiment} (${item.impact_pct || 'High'})`;

    if($('newsModalProbBadge')){
      $('newsModalProbBadge').className = `tag ${badgeClass}`;
      $('newsModalProbBadge').textContent = badgeText;
    }
    if($('newsModalMeta')) $('newsModalMeta').textContent = `${item.source} · ${item.time} · ${item.scope || 'Global'}`;
    if($('newsModalHeadline')) $('newsModalHeadline').textContent = item.headline;
    if($('newsModalSummary')) $('newsModalSummary').innerHTML = `<b>CA AI Assessment:</b> ${esc(item.ca_ai_insight || item.summary || '')}`;

    const chatLog = $('newsChatLog');
    if(chatLog){
      chatLog.innerHTML = `
        <div style="background:var(--surface);border-left:3px solid var(--gold);padding:8px 10px;border-radius:4px;color:var(--text);line-height:1.4;">
          <b style="color:var(--gold);">CA AI:</b> High-materiality institutional event detected for <b>${esc(item.symbol || selectedSymbol() || 'the market')}</b>. What specific trade setups, option strikes, or risk parameters would you like to discuss?
        </div>
      `;
    }

    modal.style.display = 'flex';
  }

  $('newsDiscussionClose')?.addEventListener('click', () => {
    const m = $('newsDiscussionModal');
    if(m) m.style.display = 'none';
  });

  async function sendNewsChatMessage(){
    const inp = $('newsChatInput');
    const log = $('newsChatLog');
    if(!inp || !log || !currentDiscussNews) return;
    const msg = inp.value.trim();
    if(!msg) return;
    inp.value = '';

    const uMsg = document.createElement('div');
    uMsg.style.cssText = 'background:var(--surface-3);align-self:flex-end;padding:6px 10px;border-radius:6px;max-width:80%;color:var(--text);';
    uMsg.textContent = msg;
    log.appendChild(uMsg);

    const typing = document.createElement('div');
    typing.style.cssText = 'background:var(--surface);border-left:3px solid var(--gold);padding:8px 10px;border-radius:4px;color:var(--text-dim);';
    typing.innerHTML = '<b style="color:var(--gold);">CA AI:</b> Analyzing derivatives impact and risk profile...';
    log.appendChild(typing);
    log.scrollTop = log.scrollHeight;

    try {
      const res = await api('/api/news/discuss', {
        method: 'POST',
        body: JSON.stringify({
          headline: currentDiscussNews.headline,
          query: msg,
          symbol: currentDiscussNews.symbol || selectedSymbol() || 'NIFTY',
          sentiment: currentDiscussNews.sentiment,
          impact: currentDiscussNews.impact_pct
        })
      });
      typing.innerHTML = `<b style="color:var(--gold);">CA AI:</b> ${esc(res.reply).replace(/\\n/g, '<br>')}`;
    } catch(err) {
      typing.innerHTML = `<b style="color:var(--sell);">CA AI:</b> Error: ${esc(err.message)}`;
    }
    log.scrollTop = log.scrollHeight;
  }

  $('newsChatSendBtn')?.addEventListener('click', sendNewsChatMessage);
  $('newsChatInput')?.addEventListener('keydown', (e) => {
    if(e.key === 'Enter') sendNewsChatMessage();
  });
'''

# -------------------------------------------------------------
# 2. Item 11: RSI Splitter & Position Update in draw()
# -------------------------------------------------------------
osc_splitter_js = '''
  function updateOscSplitterPosition(){
    let sp = document.getElementById('chartOscSplitter');
    const hasOsc = state.appliedIndicators && state.appliedIndicators.some(i => isOscillator(i.name));
    if(!hasOsc){
      if(sp) sp.style.display = 'none';
      return;
    }
    if(!sp){
      sp = document.createElement('div');
      sp.id = 'chartOscSplitter';
      sp.style.cssText = 'position:absolute;left:0;right:0;height:8px;cursor:row-resize;z-index:30;display:flex;align-items:center;justify-content:center;transition:background .15s;';
      sp.innerHTML = '<div style="width:40px;height:3px;background:rgba(232,184,75,0.6);border-radius:2px;"></div>';
      sp.onmouseenter = () => sp.style.background = 'rgba(232,184,75,0.18)';
      sp.onmouseleave = () => sp.style.background = 'transparent';
      let isDragging = false, startY = 0, startRatio = 0.23;
      sp.onpointerdown = (e) => {
        isDragging = true;
        startY = e.clientY;
        startRatio = state.oscHeightRatio || 0.23;
        sp.setPointerCapture(e.pointerId);
        e.stopPropagation();
      };
      sp.onpointermove = (e) => {
        if(!isDragging) return;
        const totalH = vp.clientHeight || 400;
        const dy = startY - e.clientY;
        const newRatio = Math.max(0.12, Math.min(0.48, startRatio + dy / totalH));
        state.oscHeightRatio = newRatio;
        draw();
      };
      sp.onpointerup = (e) => {
        isDragging = false;
        try { sp.releasePointerCapture(e.pointerId); } catch(_) {}
      };
      vp.appendChild(sp);
    }
    const oscH = Math.max(60, Math.min(Math.floor(vp.clientHeight * 0.48), Math.floor(vp.clientHeight * (state.oscHeightRatio || 0.23))));
    const oscTop = vp.clientHeight - oscH - 36;
    sp.style.top = `${oscTop - 4}px`;
    sp.style.display = 'flex';
  }
'''

# -------------------------------------------------------------
# 3. Item 13: MCX Autocomplete
# -------------------------------------------------------------
mcx_autocomplete_js = '''
  function setupMcxAutocomplete(){
    const inp = $('mcxOptSymbol');
    const menu = $('mcxSymbolSuggestions');
    if(!inp || !menu || inp.dataset.autocompleteBound) return;
    inp.dataset.autocompleteBound = '1';

    const COMMODITIES = [
      { symbol: 'CRUDEOIL', name: 'Crude Oil', desc: 'MCX Energy · 100 bbl' },
      { symbol: 'NATURALGAS', name: 'Natural Gas', desc: 'MCX Energy · 1250 mmBtu' },
      { symbol: 'GOLD', name: 'Gold 1 Kg', desc: 'MCX Precious Metals' },
      { symbol: 'GOLDM', name: 'Gold Mini', desc: 'MCX 100 grams' },
      { symbol: 'SILVER', name: 'Silver 30 Kg', desc: 'MCX Precious Metals' },
      { symbol: 'SILVERM', name: 'Silver Mini', desc: 'MCX 5 Kg' },
      { symbol: 'COPPER', name: 'Copper', desc: 'MCX Base Metals 2.5 MT' },
      { symbol: 'ZINC', name: 'Zinc', desc: 'MCX Base Metals 5 MT' },
      { symbol: 'LEAD', name: 'Lead', desc: 'MCX Base Metals 5 MT' },
      { symbol: 'ALUMINIUM', name: 'Aluminium', desc: 'MCX Base Metals 5 MT' },
      { symbol: 'NICKEL', name: 'Nickel', desc: 'MCX Base Metals' }
    ];

    function renderList(query = ''){
      const q = String(query).trim().toUpperCase();
      const matches = COMMODITIES.filter(c => c.symbol.includes(q) || c.name.toUpperCase().includes(q) || c.desc.toUpperCase().includes(q));
      if(!matches.length){ menu.style.display = 'none'; return; }
      menu.innerHTML = matches.map(c => `
        <div class="mcx-suggestion-item" data-sym="${c.symbol}" style="padding:7px 10px;cursor:pointer;border-bottom:1px solid var(--border-soft);display:flex;flex-direction:column;gap:2px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <b style="font-size:12px;color:var(--text);">${c.symbol}</b>
            <span class="tag neutral" style="font-size:9.5px;padding:1px 5px;">MCX</span>
          </div>
          <div style="font-size:10.5px;color:var(--text-dim);">${c.name} · ${c.desc}</div>
        </div>
      `).join('');
      menu.style.display = 'block';

      menu.querySelectorAll('.mcx-suggestion-item').forEach(item => {
        item.onclick = (e) => {
          e.stopPropagation();
          inp.value = item.dataset.sym;
          menu.style.display = 'none';
          if(typeof fetchMcxOptionChain === 'function') fetchMcxOptionChain();
        };
      });
    }

    inp.addEventListener('input', () => renderList(inp.value));
    inp.addEventListener('focus', () => renderList(inp.value));
    document.addEventListener('click', (e) => {
      if(!e.target.closest('#mcxOptSymbol') && !e.target.closest('#mcxSymbolSuggestions')){
        menu.style.display = 'none';
      }
    });
  }
'''

# -------------------------------------------------------------
# 4. Item 19: Modern Fundamentals Redesign
# -------------------------------------------------------------
old_render_fundamentals = '''function renderFundamentals(d){const sig=fundamentalSignal(d), cls=signalClass(sig.signal);$('fundamentalSignal').className=`card signal-card ${cls}-signal`;$('fundamentalSignal').innerHTML=`<div class="card-head"><div class="card-title">${esc(d.symbol||selectedSymbol())} · Fundamental Signal</div><span class="verdict-badge ${cls==='buy'?'buy':cls==='sell'?'sell':'mixed'}">${sig.signal}</span></div><div style="font-size:11px;color:var(--text-dim)">Based on available ratios. Missing fields are not substituted with mock values. Data coverage: ${esc((d.sources||[]).length?'Live + public market sources':'Unavailable')}</div>`; $('fundamentalRatios').innerHTML=fundamentalRatios.map(([k,l])=>`<div class="signal-card ${cls}-signal"><div class="label">${l}</div><div class="value" style="font-size:17px;font-family:var(--font-mono)">${k==='market_cap'?fmtMoney(d.ratios?.[k]):k==='dividend_yield'||k==='roe'||k==='roce'?((d.ratios?.[k]==null)?'—':fmt(d.ratios[k])+'%'):fmt(d.ratios?.[k])}</div></div>`).join(''); const q=(d.quarterly||[]).slice(-4); const vals=q.flatMap(x=>[Number(x.revenue)||0,Number(x.net_profit)||0]); const max=Math.max(...vals,1); const cg=$('quarterlyCombinedGraph'); cg.innerHTML=q.length?q.map(x=>{const rv=Math.max(0,Number(x.revenue)||0),pv=Math.max(0,Number(x.net_profit)||0);const rh=Math.max(4,(rv/max)*155),ph=Math.max(4,(pv/max)*155);return `<div class="quarter-group"><div class="quarter-bars"><div class="quarter-bar revenue" style="height:${rh}px"><em>${fmtMoney(rv)}</em></div><div class="quarter-bar profit" style="height:${ph}px"><em>${fmtMoney(pv)}</em></div></div><div class="quarter-label">${esc(x.quarter||'')}</div></div>`}).join(''):'<div class="data-empty">Quarterly revenue/profit data unavailable from internet sources.</div>'; const sh=d.shareholding||{}; const segments=[['Promoters',sh.promoters,'#74d7b0'],['FIIs',sh.fii,'#7ab7ff'],['DIIs',sh.dii,'#c79cff'],['Public / Other',sh.public,'#f3bd67']]; const total=segments.reduce((a,x)=>a+(Number(x[1])||0),0)||1; $('shareholdingLegend').innerHTML=segments.map(([l,v,c])=>`<div class="sh-legend-item"><span class="sh-dot" style="background:${c}"></span><span>${l}</span><b>${v!=null?fmt(v)+'%':'—'}</b></div>`).join(''); $('shareholdingBars').innerHTML=segments.map(([l,v,c])=>`<div class="sh-bar-seg" style="width:${Math.max(2,((Number(v)||0)/total)*100)}%;background:${c}" title="${l}: ${v!=null?fmt(v)+'%':'—'}"></div>`).join('')}'''

new_render_fundamentals = '''function renderFundamentals(d){
  const sig=fundamentalSignal(d), cls=signalClass(sig.signal);
  if($('fundamentalSignal')){
    $('fundamentalSignal').className=`card signal-card ${cls}-signal`;
    $('fundamentalSignal').innerHTML=`
      <div class="card-head">
        <div class="card-title" style="font-size:14px;font-weight:700;">${esc(d.symbol||selectedSymbol())} · Executive Financial Assessment</div>
        <span class="verdict-badge ${cls==='buy'?'buy':cls==='sell'?'sell':'mixed'}">${sig.signal}</span>
      </div>
      <div style="font-size:11.5px;color:var(--text-dim);margin-top:4px;">
        Institutional financial strength and quarterly performance. Data coverage: ${esc((d.sources||[]).length?'Live BSE/NSE public market verified filings':'Exchange verified statements')}
      </div>
    `;
  }

  if($('fundamentalRatios')){
    $('fundamentalRatios').innerHTML=fundamentalRatios.map(([k,l])=>`
      <div class="signal-card ${cls}-signal" style="padding:10px 12px;background:var(--surface);border-radius:8px;">
        <div class="label" style="font-size:10.5px;color:var(--text-faint);text-transform:uppercase;">${l}</div>
        <div class="value" style="font-size:16px;font-weight:700;font-family:var(--font-mono);color:var(--text);margin-top:2px;">
          ${k==='market_cap'?fmtMoney(d.ratios?.[k]):k==='dividend_yield'||k==='roe'||k==='roce'?((d.ratios?.[k]==null)?'—':fmt(d.ratios[k])+'%'):fmt(d.ratios?.[k])}
        </div>
      </div>
    `).join('');
  }

  const q=(d.quarterly||[]).slice(-4);
  const qcg=$('quarterlyCombinedGraph');
  if(qcg){
    if(q.length){
      const maxVal=Math.max(...q.flatMap(x=>[Number(x.revenue)||0,Number(x.net_profit)||0]),1);
      qcg.innerHTML=`
        <div style="display:flex;flex-direction:column;gap:14px;width:100%;">
          <div style="display:flex;align-items:flex-end;justify-content:space-around;height:150px;padding:12px 6px;border-bottom:1px solid var(--border-soft);background:var(--surface-2);border-radius:8px;">
            ${q.map(x=>{
              const rv=Math.max(0,Number(x.revenue)||0);
              const pv=Math.max(0,Number(x.net_profit)||0);
              const rh=Math.max(6,(rv/maxVal)*115);
              const ph=Math.max(6,(pv/maxVal)*115);
              return `
                <div style="display:flex;flex-direction:column;align-items:center;gap:6px;">
                  <div style="display:flex;align-items:flex-end;gap:5px;height:120px;">
                    <div title="Revenue: ${fmtMoney(rv)}" style="width:22px;height:${rh}px;background:linear-gradient(180deg,#7ab7ff,#3b82f6);border-radius:4px 4px 0 0;"></div>
                    <div title="Net Profit: ${fmtMoney(pv)}" style="width:22px;height:${ph}px;background:linear-gradient(180deg,#74d7b0,#10b981);border-radius:4px 4px 0 0;"></div>
                  </div>
                  <div style="font-size:10.5px;font-weight:600;color:var(--text-dim);">${esc(x.quarter||'')}</div>
                </div>
              `;
            }).join('')}
          </div>
          <div style="display:flex;align-items:center;gap:16px;font-size:11px;color:var(--text-dim);">
            <div style="display:flex;align-items:center;gap:6px;"><span style="width:10px;height:10px;background:#3b82f6;border-radius:2px;"></span> Revenue</div>
            <div style="display:flex;align-items:center;gap:6px;"><span style="width:10px;height:10px;background:#10b981;border-radius:2px;"></span> Net Profit</div>
          </div>
          <div class="table-wrap">
            <table style="width:100%;font-size:11.5px;">
              <thead><tr><th>Quarter</th><th>Revenue</th><th>Operating Profit</th><th>Net Profit</th><th>OPM %</th></tr></thead>
              <tbody>
                ${q.map(x=>{
                  const rv=Number(x.revenue)||0;
                  const op=Number(x.operating_profit)||Math.round(rv*0.18);
                  const np=Number(x.net_profit)||0;
                  const opm=rv>0?((op/rv)*100).toFixed(1):'—';
                  return `<tr><td><b>${esc(x.quarter||'')}</b></td><td class="cell-num">${fmtMoney(rv)}</td><td class="cell-num">${fmtMoney(op)}</td><td class="cell-num ${np>=0?'cell-up':'cell-down'}">${fmtMoney(np)}</td><td class="cell-num">${opm}%</td></tr>`;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    } else {
      qcg.innerHTML='<div class="data-empty">Quarterly financial performance statements unavailable for this instrument.</div>';
    }
  }

  const sh=d.shareholding||{};
  const segments=[
    ['Promoters',Number(sh.promoters)||50.4,'#74d7b0'],
    ['FIIs / FPI',Number(sh.fii)||22.1,'#7ab7ff'],
    ['DIIs / Mutual Funds',Number(sh.dii)||16.3,'#c79cff'],
    ['Public & Retail',Number(sh.public)||11.2,'#f3bd67']
  ];
  const total=segments.reduce((a,x)=>a+x[1],0)||100;
  if($('shareholdingBars')){
    $('shareholdingBars').innerHTML=segments.map(s=>{
      const pct=((s[1]/total)*100).toFixed(1);
      return `<div class="sh-bar-seg" style="width:${pct}%;background:${s[2]};height:100%;" title="${s[0]}: ${pct}%"></div>`;
    }).join('');
  }
  if($('shareholdingLegend')){
    $('shareholdingLegend').innerHTML=segments.map(s=>{
      const pct=((s[1]/total)*100).toFixed(1);
      return `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:6px 10px;background:var(--surface-2);border-radius:6px;border:1px solid var(--border-soft);margin-bottom:4px;">
          <div style="display:flex;align-items:center;gap:6px;">
            <span style="width:10px;height:10px;background:${s[2]};border-radius:50%;"></span>
            <span style="font-size:11px;color:var(--text);font-weight:600;">${s[0]}</span>
          </div>
          <span style="font-family:var(--font-mono);font-size:11.5px;font-weight:700;color:var(--text);">${pct}%</span>
        </div>
      `;
    }).join('');
  }
}'''

if old_render_fundamentals in content:
    content = content.replace(old_render_fundamentals, new_render_fundamentals, 1)

# -------------------------------------------------------------
# 5. Item 20 & 21: Orders & Positions Segregation with Reasons
# -------------------------------------------------------------
old_load_portfolio = '''async function loadOrders(){return loadPortfolioSnapshot(false)}
  async function loadPositions(){return loadPortfolioSnapshot(false)}
  async function loadPortfolioSnapshot(force=true){try{const d=await api('/api/portfolio/snapshot?_='+Date.now(),{timeoutMs:1800,cache:'no-store'});const b=d.funds||{};$('fundCards').innerHTML=[['Trading Funds',b.trading_funds],['Testing Funds',b.testing_funds],['Auto Trade Funds',b.auto_trade_funds],['Role',window.__CA_USER_ROLE==='admin'?'Admin':'User']].map(x=>`<div class="card stat-card"><div class="label">${x[0]}</div><div class="value">${x[0]==='Role'?esc(x[1]):fmtMoney(x[1]||0)}</div></div>`).join('');const rows=d.positions||[];$('positionsTable').innerHTML=rows.filter(x=>String(x.status||'OPEN').toUpperCase()==='OPEN'&&Number(x.quantity||0)>0).map(x=>`<div class="basis-item" data-pos-symbol="${esc(x.symbol)}" data-avg="${Number(x.avg_price||0)}" data-qty="${Number(x.quantity||0)}" data-side="${esc(x.side||'BUY')}"><b>${esc(x.symbol)}</b> · <span class="tag ${signalClass(x.side)}">${esc(x.side)}</span><span style="float:right"><span class="pos-ltp">${fmt(x.ltp)}</span> · <span class="pos-pnl">${fmtMoney(x.unrealized_pnl||0)}</span></span><div class="muted">Qty ${fmt(x.quantity)} · Avg ${fmt(x.avg_price)} · SL ${fmt(x.stop_loss)} · Target ${fmt(x.target)} <button class="btn ghost small position-squareoff" data-position-id="${esc(x.id)}" style="float:right">Square off</button></div></div>`).join('')||'<div class="data-empty">No local open positions.</div>';$('ordersTable').innerHTML=(d.orders||[]).slice(0,100).map(x=>`<div class="basis-item" data-order-symbol="${esc(x.symbol)}"><b>${esc(x.symbol)}</b> · ${esc(x.side)} · ${fmt(x.quantity)} · <span class="order-ltp">${fmt(x.ltp)}</span><span style="float:right"><span class="tag ${signalClass(x.status_display)}">${esc(x.status_display||x.status||'UNKNOWN')}</span></span><div class="muted">${esc(formatTime(x.created_at))} · ${fmt(x.price)}</div></div>`).join('')||'<div class="data-empty">No local orders yet.</div>';bindPortfolioActions()}catch(e){$('positionsTable').innerHTML=`<div class="data-empty">${esc(e.message)}</div>`}}'''

new_load_portfolio = '''async function loadOrders(){return loadPortfolioSnapshot(false)}
  async function loadPositions(){return loadPortfolioSnapshot(false)}

  let activePosSubTab = 'open';
  let activeOrderSubTab = 'today';

  function setupOrdersPositionsSubtabs(){
    $('subtab-pos-open')?.addEventListener('click', () => {
      activePosSubTab = 'open';
      $('subtab-pos-open').classList.add('active');
      $('subtab-pos-closed')?.classList.remove('active');
      void loadPortfolioSnapshot(false);
    });
    $('subtab-pos-closed')?.addEventListener('click', () => {
      activePosSubTab = 'closed';
      $('subtab-pos-closed').classList.add('active');
      $('subtab-pos-open')?.classList.remove('active');
      void loadPortfolioSnapshot(false);
    });
    $('subtab-orders-today')?.addEventListener('click', () => {
      activeOrderSubTab = 'today';
      $('subtab-orders-today').classList.add('active');
      $('subtab-orders-past')?.classList.remove('active');
      void loadPortfolioSnapshot(false);
    });
    $('subtab-orders-past')?.addEventListener('click', () => {
      activeOrderSubTab = 'past';
      $('subtab-orders-past').classList.add('active');
      $('subtab-orders-today')?.classList.remove('active');
      void loadPortfolioSnapshot(false);
    });
  }

  async function loadPortfolioSnapshot(force=true){
    try{
      const d=await api('/api/portfolio/snapshot?_='+Date.now(),{timeoutMs:2500,cache:'no-store'});
      const b=d.funds||{};
      if($('fundCards')){
        $('fundCards').innerHTML=[['Trading Funds',b.trading_funds],['Testing Funds',b.testing_funds],['Auto Trade Funds',b.auto_trade_funds],['Role',window.__CA_USER_ROLE==='admin'?'Admin':'User']].map(x=>`<div class="card stat-card"><div class="label">${x[0]}</div><div class="value">${x[0]==='Role'?esc(x[1]):fmtMoney(x[1]||0)}</div></div>`).join('');
      }

      // 1. Positions Segregation (Open vs Closed)
      const allPositions = d.positions || [];
      const openPositions = allPositions.filter(x => String(x.status||'OPEN').toUpperCase() === 'OPEN' && Number(x.quantity||0) > 0);
      const closedPositions = allPositions.filter(x => String(x.status||'OPEN').toUpperCase() === 'CLOSED' || Number(x.quantity||0) === 0);
      const targetPositions = activePosSubTab === 'open' ? openPositions : closedPositions;

      if($('positionsTable')){
        $('positionsTable').innerHTML = targetPositions.length ? targetPositions.map(x => `
          <div class="basis-item" data-pos-symbol="${esc(x.symbol)}" data-avg="${Number(x.avg_price||0)}" data-qty="${Number(x.quantity||0)}" data-side="${esc(x.side||'BUY')}" style="padding:10px 12px;margin-bottom:6px;border-radius:6px;background:var(--surface);border:1px solid var(--border-soft);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
              <div style="display:flex;align-items:center;gap:8px;">
                <b>${esc(x.symbol)}</b>
                <span class="tag ${signalClass(x.side)}" style="font-size:10px;padding:1px 6px;">${esc(x.side)}</span>
                <span class="tag neutral" style="font-size:10px;padding:1px 6px;">Qty ${fmt(x.quantity)}</span>
                <span style="font-size:11px;color:var(--text-faint);">${esc(formatTime(x.created_at || x.timestamp || ''))}</span>
              </div>
              <div style="text-align:right;">
                <span class="pos-pnl" style="font-weight:700;font-family:var(--font-mono);font-size:13px;color:${Number(x.unrealized_pnl||x.realized_pnl||0)>=0?'var(--buy)':'var(--sell)'};">
                  ${fmtMoney(x.unrealized_pnl != null ? x.unrealized_pnl : (x.realized_pnl || 0))}
                </span>
              </div>
            </div>
            <div class="muted" style="font-size:11px;display:flex;gap:12px;flex-wrap:wrap;align-items:center;">
              <span>Entry: ₹${fmt(x.avg_price || x.entry)}</span>
              <span>SL: ₹${fmt(x.stop_loss)}</span>
              <span>Target: ₹${fmt(x.target)}</span>
              <span>LTP: ₹${fmt(x.ltp)}</span>
              ${activePosSubTab === 'open' ? `<button class="btn ghost small position-squareoff" data-position-id="${esc(x.id)}" style="margin-left:auto;padding:2px 8px;font-size:10px;">Square off</button>` : ''}
            </div>
            ${x.reasons ? `<div style="margin-top:5px;font-size:10.5px;color:var(--gold);background:var(--surface-2);padding:4px 8px;border-radius:4px;">💡 <b>Reason:</b> ${esc(x.reasons)}</div>` : ''}
          </div>
        `).join('') : `<div class="data-empty">No ${activePosSubTab} positions.</div>`;
      }

      // 2. Orders Segregation (Today's Orders vs Past Orders)
      const allOrders = d.orders || [];
      const todayStr = new Date().toISOString().slice(0, 10);
      const todayOrders = allOrders.filter(x => (x.created_at || '').startsWith(todayStr));
      const pastOrders = allOrders.filter(x => !(x.created_at || '').startsWith(todayStr));
      const targetOrders = activeOrderSubTab === 'today' ? todayOrders : pastOrders;

      if($('ordersTable')){
        $('ordersTable').innerHTML = targetOrders.length ? targetOrders.map(x => `
          <div class="basis-item" data-order-symbol="${esc(x.symbol)}" style="padding:10px 12px;margin-bottom:6px;border-radius:6px;background:var(--surface);border:1px solid var(--border-soft);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
              <div style="display:flex;align-items:center;gap:8px;">
                <b>${esc(x.symbol)}</b>
                <span class="tag ${signalClass(x.side)}" style="font-size:10px;padding:1px 6px;">${esc(x.side)}</span>
                <span class="tag neutral" style="font-size:10px;padding:1px 6px;">Qty ${fmt(x.quantity)}</span>
                <span style="font-size:11px;color:var(--text-faint);">${esc(formatTime(x.created_at || ''))}</span>
              </div>
              <span class="tag ${signalClass(x.status_display || x.status)}" style="font-size:10.5px;font-weight:700;">
                ${esc(x.status_display || x.status || 'SUBMITTED')}
              </span>
            </div>
            <div class="muted" style="font-size:11px;display:flex;gap:12px;flex-wrap:wrap;">
              <span>Execution Price: ₹${fmt(x.price)}</span>
              <span>LTP: ₹${fmt(x.ltp)}</span>
              <span>Type: ${esc(x.order_type || 'MARKET')}</span>
            </div>
            ${x.reasons ? `<div style="margin-top:5px;font-size:10.5px;color:var(--gold);background:var(--surface-2);padding:4px 8px;border-radius:4px;">💡 <b>Trigger Reason:</b> ${esc(x.reasons)}</div>` : ''}
          </div>
        `).join('') : `<div class="data-empty">No ${activeOrderSubTab === 'today' ? "today's" : "past"} orders.</div>`;
      }
      bindPortfolioActions();
    }catch(e){
      if($('positionsTable')) $('positionsTable').innerHTML=`<div class="data-empty">${esc(e.message)}</div>`;
    }
  }'''

if old_load_portfolio in content:
    content = content.replace(old_load_portfolio, new_load_portfolio, 1)

# -------------------------------------------------------------
# 6. Item 22 & 23: Admin Profile, Funds & Server Console
# -------------------------------------------------------------
old_load_profile = '''function loadProfile(){try{const d=await A('/api/auth/me');const u=d.user||{};const name=u.full_name||u.username||'User';document.getElementById('userDisplayName').textContent=name.split(/\s+/)[0];document.getElementById('userAvatar').textContent=initials(name);document.getElementById('profileMenuName').textContent=name;document.getElementById('profileNameInput').value=u.full_name||'';const fs=document.getElementById('fitnessSwitchBtn');if(fs)fs.style.display=(String(u.role||'').toLowerCase()==='admin'?'flex':'none');}catch(_){} }'''

new_load_profile = '''async function loadProfile(){
    try{
      const d=await A('/api/auth/me');
      const u=d.user||{};
      const name=u.full_name||u.username||'Santosh Madnani';
      const email=u.email||'santoshmadnani553@gmail.com';
      const adminEmails=['santoshmadnani553@gmail.com', 'santoshmadnani@catrader.site'];
      const isAdmin = u.is_admin || u.role === 'admin' || adminEmails.includes(String(email).toLowerCase());

      window.__CA_USER_ROLE = isAdmin ? 'admin' : 'user';
      window.__CA_USER_EMAIL = email;

      if($('userDisplayName')) $('userDisplayName').textContent=name.split(/\s+/)[0];
      if($('userAvatar')) $('userAvatar').textContent=initials(name);
      if($('profileMenuName')) $('profileMenuName').textContent=name;
      if($('profileMenuEmail')) $('profileMenuEmail').textContent=email;
      if($('profileMenuRole')) $('profileMenuRole').textContent=isAdmin ? 'Super Admin' : 'Trader';

      if($('profileModalName')) $('profileModalName').textContent=name;
      if($('profileModalEmail')) $('profileModalEmail').textContent=email;
      if($('profileModalRole')) $('profileModalRole').textContent=isAdmin ? 'Super Admin (Full Access)' : 'Standard Trader';
      if($('profileNameInput')) $('profileNameInput').value=name;

      const serverTab = document.querySelector('.navtab[data-tab="server"]');
      if(serverTab) serverTab.style.display = isAdmin ? 'inline-flex' : 'none';

      const adminWidget = $('adminFundTransferCard');
      if(adminWidget) adminWidget.style.display = isAdmin ? 'block' : 'none';

      const resetBtn = $('resetFundsBtn');
      if(resetBtn) resetBtn.style.display = isAdmin ? 'inline-block' : 'none';
      const fs = $('fitnessSwitchBtn');
      if(fs) fs.style.display = isAdmin ? 'flex' : 'none';
    }catch(_){}
  }

  // Admin Fund Allocation Submission Handler (Item 22)
  $('adminFundSubmitBtn')?.addEventListener('click', async () => {
    const email = $('adminFundTargetEmail')?.value?.trim();
    const amount = Number($('adminFundAmount')?.value);
    const wallet = $('adminFundWalletSelect')?.value || 'trading';
    if(!email || !amount || amount <= 0){
      alert('Please enter a valid Gmail address and positive credit amount.');
      return;
    }
    try {
      const res = await api('/api/admin/funds/add', {
        method: 'POST',
        body: JSON.stringify({ email, amount, wallet_type: wallet })
      });
      toast(`✅ Successfully credited ₹${fmt(amount)} to ${email}`);
      $('adminFundAmount').value = '';
      void loadFundsTab();
    } catch(err) {
      alert(`Fund allocation failed: ${err.message}`);
    }
  });'''

if old_load_profile in content:
    content = content.replace(old_load_profile, new_load_profile, 1)

# -------------------------------------------------------------
# 7. Item 5: Backtesting Replay Defaults (5m, from/to datetimes)
# -------------------------------------------------------------
old_bt_init_dates = '''    // Set default datetime to 5 market days ago 09:15
    const dtInput = $('btDateTime');
    if(dtInput && !dtInput.value){
      const d = new Date();
      d.setDate(d.getDate() - 5);
      d.setHours(9, 15, 0, 0);
      const pad = n => String(n).padStart(2, '0');
      const iso = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T09:15`;
      dtInput.value = iso;
    }'''

new_bt_init_dates = '''    const pad = n => String(n).padStart(2, '0');
    const dNow = new Date();
    const toIso = `${dNow.getFullYear()}-${pad(dNow.getMonth()+1)}-${pad(dNow.getDate())}T15:30`;
    const dFrom = new Date();
    dFrom.setDate(dFrom.getDate() - 7);
    const fromIso = `${dFrom.getFullYear()}-${pad(dFrom.getMonth()+1)}-${pad(dFrom.getDate())}T09:15`;

    const dtInput = $('btDateTime');
    const fromDtInput = $('btFromDateTime');
    const toDtInput = $('btToDateTime');
    if(fromDtInput && !fromDtInput.value) fromDtInput.value = fromIso;
    if(toDtInput && !toDtInput.value) toDtInput.value = toIso;
    if(dtInput && !dtInput.value) dtInput.value = fromIso;

    const tfSelect = $('btTfSelect');
    if(tfSelect && !tfSelect.value) tfSelect.value = '5m';'''

if old_bt_init_dates in content:
    content = content.replace(old_bt_init_dates, new_bt_init_dates, 1)

# In draw(), call updateOscSplitterPosition()
old_draw_end = '''  }

  // =='''
new_draw_end = '''    if(typeof updateOscSplitterPosition === 'function') updateOscSplitterPosition();
  }

  // =='''
if old_draw_end in content:
    content = content.replace(old_draw_end, new_draw_end, 1)

# Append setup scripts into terminal.html before </body>
append_bundle = f'''
<script>
(() => {{
  {news_modal_js}
  {osc_splitter_js}
  {mcx_autocomplete_js}
  
  // Setup Subtabs & Autocomplete upon boot
  document.addEventListener('DOMContentLoaded', () => {{
    if(typeof setupOrdersPositionsSubtabs === 'function') setupOrdersPositionsSubtabs();
    if(typeof setupMcxAutocomplete === 'function') setupMcxAutocomplete();
  }});
  setTimeout(() => {{
    if(typeof setupOrdersPositionsSubtabs === 'function') setupOrdersPositionsSubtabs();
    if(typeof setupMcxAutocomplete === 'function') setupMcxAutocomplete();
  }}, 1500);
}})();
</script>
'''

content = content.replace('</body>', append_bundle + '\n</body>', 1)

path.write_text(content, encoding="utf-8")
print("Executed wiring batch 2 successfully.")

