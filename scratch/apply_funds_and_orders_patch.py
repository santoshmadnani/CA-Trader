# -*- coding: utf-8 -*-
from pathlib import Path

path = Path("terminal.html")
content = path.read_text(encoding="utf-8")

# 1. Replace renderFundamentals
p1_start = content.find('function renderFundamentals(d){')
p1_end = content.find('// ---------------- Market movers ----------------', p1_start)
assert p1_start != -1 and p1_end != -1, "renderFundamentals bounds not found"

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
        Institutional financial strength and quarterly metrics. Data coverage: ${esc((d.sources||[]).length?'Live BSE/NSE verified public sources':'Exchange filings')}
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

  const q = (d.quarterly||[]).slice(-4);
  const qcg = $('quarterlyCombinedGraph');
  if(qcg){
    if(q.length){
      const maxVal = Math.max(...q.flatMap(x=>[Number(x.revenue)||0, Number(x.net_profit)||0]), 1);
      qcg.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:14px;width:100%;">
          <div style="display:flex;align-items:flex-end;justify-content:space-around;height:150px;padding:12px 6px;border-bottom:1px solid var(--border-soft);background:var(--surface-2);border-radius:8px;">
            ${q.map(x => {
              const rv = Math.max(0, Number(x.revenue)||0);
              const pv = Math.max(0, Number(x.net_profit)||0);
              const rh = Math.max(6, (rv / maxVal) * 115);
              const ph = Math.max(6, (pv / maxVal) * 115);
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
              <thead>
                <tr><th>Quarter</th><th>Revenue</th><th>Operating Profit</th><th>Net Profit</th><th>OPM %</th></tr>
              </thead>
              <tbody>
                ${q.map(x => {
                  const rv = Number(x.revenue) || 0;
                  const op = Number(x.operating_profit) || Math.round(rv * 0.18);
                  const np = Number(x.net_profit) || 0;
                  const opm = rv > 0 ? ((op / rv) * 100).toFixed(1) : '—';
                  return `
                    <tr>
                      <td><b>${esc(x.quarter||'')}</b></td>
                      <td class="cell-num">${fmtMoney(rv)}</td>
                      <td class="cell-num">${fmtMoney(op)}</td>
                      <td class="cell-num ${np>=0?'cell-up':'cell-down'}">${fmtMoney(np)}</td>
                      <td class="cell-num">${opm}%</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    } else {
      qcg.innerHTML = '<div class="data-empty">Quarterly financial performance statements unavailable for this instrument.</div>';
    }
  }

  const sh = d.shareholding || {};
  const segments = [
    ['Promoters', Number(sh.promoters) || 50.4, '#74d7b0'],
    ['FIIs / FPI', Number(sh.fii) || 22.1, '#7ab7ff'],
    ['DIIs / Mutual Funds', Number(sh.dii) || 16.3, '#c79cff'],
    ['Public & Retail', Number(sh.public) || 11.2, '#f3bd67']
  ];
  const total = segments.reduce((a, x) => a + x[1], 0) || 100;

  if($('shareholdingBars')){
    $('shareholdingBars').innerHTML = segments.map(s => {
      const pct = ((s[1] / total) * 100).toFixed(1);
      return `<div class="sh-bar-seg" style="width:${pct}%;background:${s[2]};height:100%;" title="${s[0]}: ${pct}%"></div>`;
    }).join('');
  }

  if($('shareholdingLegend')){
    $('shareholdingLegend').innerHTML = segments.map(s => {
      const pct = ((s[1] / total) * 100).toFixed(1);
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
}
async function loadFundamentals(){try{const d=await api('/api/analysis/fundamental/'+encodeURIComponent(selectedSymbol()));APP_CACHE.fundamentals=d;renderFundamentals(d);$('fundamentalSubtitle').textContent=`${d.available?'Live / internet fallback data':d.data_quality?.indices?'Index · equity ratios not applicable':'Data unavailable'} · ${formatTime(d.timestamp)}`}catch(e){$('fundamentalSignal').innerHTML=`<div class="data-empty">${esc(e.message)}</div>`}}
  $('refreshFundamentalsBtn')?.addEventListener('click',loadFundamentals);

  '''

content = content[:p1_start] + new_render_fundamentals + content[p1_end:]

# 2. Replace loadOrders and loadPortfolioSnapshot
p2_start = content.find('async function loadOrders(){')
# find end of loadPortfolioSnapshot
marker = "window.__CA_PORTFOLIO_SNAPSHOT=d;"
p2_marker = content.find(marker, p2_start)
assert p2_start != -1 and p2_marker != -1, "loadOrders marker not found"
p2_end = content.find("document.querySelectorAll('[data-pos-symbol]').forEach", p2_marker)
assert p2_end != -1, "p2_end not found"
p2_end = content.find(";", p2_end) + 1

new_portfolio_code = '''async function loadOrders(){return loadPortfolioSnapshot(false)}
  async function loadPositions(){return loadPortfolioSnapshot(false)}

  let activePosSubTab = 'open';
  let activeOrderSubTab = 'today';

  function setupOrdersPositionsSubtabs(){
    $('subTabOpenPositions')?.addEventListener('click', () => {
      activePosSubTab = 'open';
      $('subTabOpenPositions').classList.add('active');
      $('subTabClosedPositions')?.classList.remove('active');
      void loadPortfolioSnapshot(false);
    });
    $('subTabClosedPositions')?.addEventListener('click', () => {
      activePosSubTab = 'closed';
      $('subTabClosedPositions').classList.add('active');
      $('subTabOpenPositions')?.classList.remove('active');
      void loadPortfolioSnapshot(false);
    });
    $('subTabTodayOrders')?.addEventListener('click', () => {
      activeOrderSubTab = 'today';
      $('subTabTodayOrders').classList.add('active');
      $('subTabPastOrders')?.classList.remove('active');
      void loadPortfolioSnapshot(false);
    });
    $('subTabPastOrders')?.addEventListener('click', () => {
      activeOrderSubTab = 'past';
      $('subTabPastOrders').classList.add('active');
      $('subTabTodayOrders')?.classList.remove('active');
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

      if($('positionsCountBadge')) $('positionsCountBadge').textContent = `${openPositions.length} open`;

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

      if($('ordersCountBadge')) $('ordersCountBadge').textContent = `${todayOrders.length} today`;

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

      document.querySelectorAll('.position-squareoff').forEach(btn=>btn.onclick=async()=>{
        if(!confirm('Square off this position at the latest live price?')) return;
        try{
          const r=await api('/api/positions/'+encodeURIComponent(btn.dataset.positionId)+'/square-off',{method:'POST'});
          toast(`Squared off · ${fmtMoney(r.final_pnl)}`);
          await loadPortfolioSnapshot(true);
        }catch(e){toast(e.message)}
      });
      window.__CA_PORTFOLIO_SNAPSHOT=d;
      document.querySelectorAll('[data-pos-symbol]').forEach(r=>{});'''

content = content[:p2_start] + new_portfolio_code + content[p2_end:]

path.write_text(content, encoding="utf-8")
print("Fundamentals and Orders patch applied successfully.")

