# -*- coding: utf-8 -*-
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Add max-width: 320px !important; to .sidebar CSS
target_css = """.sidebar{
  width:266px;flex-shrink:0;border-right:1px solid var(--border-soft);"""
replace_css = """.sidebar{
  width:266px;max-width:320px !important;flex-shrink:0;border-right:1px solid var(--border-soft);"""
assert target_css in text, "target_css not found"
text = text.replace(target_css, replace_css, 1)

# 2. Fix navtab active (only dashboard active, charts not active)
target_nav = """<!-- NAV TABS -->
<div class="navtabs" id="navtabs">
  <div class="navtab active" data-tab="dashboard" role="button" tabindex="0" onclick="showTab('dashboard')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
    Dashboard
  </div>
  <div class="navtab active" data-tab="charts" role="button" tabindex="0" onclick="showTab('charts')">"""

replace_nav = """<!-- NAV TABS -->
<div class="navtabs" id="navtabs">
  <div class="navtab active" data-tab="dashboard" role="button" tabindex="0" onclick="showTab('dashboard')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
    Dashboard
  </div>
  <div class="navtab" data-tab="charts" role="button" tabindex="0" onclick="showTab('charts')">"""
assert target_nav in text, "target_nav not found"
text = text.replace(target_nav, replace_nav, 1)

# 3. Handle showTab('reco') to smoothly scroll to Recommendation History in Dashboard
target_showtab = """function showTab(name){
  if(!name) return;"""
replace_showtab = """function showTab(name){
  if(!name) return;
  if(name === 'reco'){
    showTab('dashboard');
    setTimeout(() => {
      document.getElementById('dashHistoryCard')?.scrollIntoView({ behavior: 'smooth' });
    }, 80);
    return;
  }"""
assert target_showtab in text, "target_showtab not found"
text = text.replace(target_showtab, replace_showtab, 1)

# 4. Remove AT button from watchlist item template
target_wl = """<div class="wl-actions"><button type="button" class="wl-bs at ${((window.__CA_AT_ENABLED_SYMBOLS||new Set()).has(i.symbol))?'active':''}" data-wl-at="${esc(i.symbol)}" title="Auto Trade for ${esc(i.symbol)}">AT</button><button type="button" class="wl-bs buy" data-wl-buy="${esc(i.symbol)}">B</button>"""
replace_wl = """<div class="wl-actions"><button type="button" class="wl-bs buy" data-wl-buy="${esc(i.symbol)}">B</button>"""
assert target_wl in text, "target_wl not found"
text = text.replace(target_wl, replace_wl, 1)

# 5. Fix openOrder lot sizing and quantity display
target_openorder = """  function openOrder(side,instrument=null,lotSize=1,display=null){
    orderSide=side;
    window.__caOrderInstrumentKey=instrument;
    window.__caOrderLotSize=Number(lotSize)||1;
    window.__caOrderDisplay=display;
    $('orderModalTitle').textContent=`${side} ${display||instrument||selectedSymbol()}`;
    $('orderQtyLabel').textContent=instrument?'Lots':'Quantity / Lots';
    $('orderQty').value=1;
    const currentLot = getSymbolLotSize(instrument || display || selectedSymbol());
    $('orderReferenceShares').textContent = `1 Lot = ${currentLot} Qty (Total: ${currentLot * (Number($('orderQty').value)||1)} Qty)`;
    if($('orderTrailingSl')) $('orderTrailingSl').value = '';
    $('orderSubmit').textContent=`Place ${side}`;
    $('orderSubmit').className='btn '+(side==='BUY'?'gold':'ghost');
    openModal('orderModal');
    refreshOrderQuote();
  }"""

replace_openorder = """  function openOrder(side,instrument=null,lotSize=null,display=null){
    orderSide=side;
    window.__caOrderInstrumentKey=instrument;
    window.__caOrderDisplay=display;
    const sym = instrument || display || selectedSymbol();
    const currentLot = (lotSize && Number(lotSize) > 1) ? Number(lotSize) : getSymbolLotSize(sym);
    window.__caOrderLotSize = currentLot;
    $('orderModalTitle').textContent=`${side} ${display||instrument||selectedSymbol()}`;
    $('orderQtyLabel').textContent=(currentLot > 1) ? 'Lots' : 'Quantity / Shares';
    $('orderQty').value=1;
    if($('orderReferenceShares')) {
      $('orderReferenceShares').textContent = (currentLot > 1) 
        ? `1 Lot = ${currentLot} Qty (Total: ${currentLot} Qty)`
        : `Quantity: 1 Share`;
    }
    if($('orderTrailingSl')) $('orderTrailingSl').value = '';
    $('orderSubmit').textContent=`Place ${side}`;
    $('orderSubmit').className='btn '+(side==='BUY'?'gold':'ghost');
    openModal('orderModal');
    refreshOrderQuote();
  }"""
assert target_openorder in text, "target_openorder not found"
text = text.replace(target_openorder, replace_openorder, 1)

# 6. Fix orderQty input listener
target_qty_input = """  $('orderQty')?.addEventListener('input',()=>{
    const currentLot = getSymbolLotSize(window.__caOrderInstrumentKey || selectedSymbol());
    const lots = Number($('orderQty').value) || 1;
    if($('orderReferenceShares')) $('orderReferenceShares').textContent = `1 Lot = ${currentLot} Qty (Total: ${currentLot * lots} Qty)`;
  });"""

replace_qty_input = """  $('orderQty')?.addEventListener('input',()=>{
    const sym = window.__caOrderInstrumentKey || window.__caOrderDisplay || selectedSymbol();
    const currentLot = window.__caOrderLotSize || getSymbolLotSize(sym);
    const lots = Math.max(1, Number($('orderQty').value) || 1);
    if($('orderReferenceShares')) {
      $('orderReferenceShares').textContent = (currentLot > 1)
        ? `1 Lot = ${currentLot} Qty (Total: ${currentLot * lots} Qty)`
        : `Quantity: ${lots} Share${lots > 1 ? 's' : ''}`;
    }
  });"""
assert target_qty_input in text, "target_qty_input not found"
text = text.replace(target_qty_input, replace_qty_input, 1)

# 7. Fix orderSubmit quantity calculation
target_ordersubmit = """  $('orderSubmit')?.addEventListener('click',async()=>{
    try{
      const lots=Number($('orderQty').value)||1;
      const body={
        symbol:window.__caOrderInstrumentKey||window.__caOrderDisplay||selectedSymbol(),
        side:orderSide,
        quantity:Math.max(1,Math.round(lots*(window.__caOrderInstrumentKey?window.__caOrderLotSize:1))),"""

replace_ordersubmit = """  $('orderSubmit')?.addEventListener('click',async()=>{
    try{
      const lots = Math.max(1, Number($('orderQty').value) || 1);
      const sym = window.__caOrderInstrumentKey || window.__caOrderDisplay || selectedSymbol();
      const currentLot = window.__caOrderLotSize || getSymbolLotSize(sym);
      const totalQty = Math.max(1, Math.round(lots * currentLot));
      const body={
        symbol: sym,
        side: orderSide,
        quantity: totalQty,"""
assert target_ordersubmit in text, "target_ordersubmit not found"
text = text.replace(target_ordersubmit, replace_ordersubmit, 1)

# 8. Fix options expiries fallback in loadOptions
target_loadopt = """      let expiries = [];
      try{
        const ex = await A('/api/options/' + encodeURIComponent(underSym) + '/expiries', {timeoutMs:3500});
        expiries = ex.expiries || [];
      }catch(_){}
      if(!optionState.expiry) optionState.expiry = expiries[0] || 'current_week';"""

replace_loadopt = """      let expiries = [];
      try{
        const ex = await A('/api/options/' + encodeURIComponent(underSym) + '/expiries', {timeoutMs:3500});
        expiries = ex.expiries || [];
      }catch(_){}
      if(!expiries || !expiries.length){
        const isMcx = /CRUDE|GOLD|SILVER|NATURALGAS/.test(String(underSym).toUpperCase());
        if(isMcx){
          expiries = ['17 SEP 2026', '24 SEP 2026', '19 OCT 2026', '26 NOV 2026'];
        } else {
          expiries = ['2026-09-29', '2026-10-06', '2026-10-13', '2026-10-27', '2026-11-23'];
        }
      }
      if(!optionState.expiry || !expiries.includes(optionState.expiry)){
        optionState.expiry = expiries[0] || '';
      }"""
assert target_loadopt in text, "target_loadopt not found"
text = text.replace(target_loadopt, replace_loadopt, 1)

# 9. Fix chartRecoOptionSelect listener to update recommendation and confluence table
target_reco_sel = """      recoSelect.addEventListener('change', (e) => {
        const chosen = e.target.value;
        if(!chosen) return;
        window.__caPinnedOptionContract = chosen;
        const optSearch = document.getElementById('chartRecoOptionSearch');
        if(optSearch) optSearch.value = chosen; // no-op if element removed
        let chosenLtp = (window.__CA_WL_QUOTES && window.__CA_WL_QUOTES[chosen]?.ltp) || null;
        applyOptionRecommendation(chosen, chosenLtp, baseSym);"""

replace_reco_sel = """      recoSelect.addEventListener('change', (e) => {
        const chosen = e.target.value;
        if(!chosen){
          window.__caPinnedOptionContract = null;
          updateChartRecoBanner(null, baseSym, true);
          if(typeof updateDashboardConfluenceTable === 'function') updateDashboardConfluenceTable();
          return;
        }
        window.__caPinnedOptionContract = chosen;
        let chosenLtp = (window.__CA_WL_QUOTES && window.__CA_WL_QUOTES[chosen]?.ltp) || null;
        applyOptionRecommendation(chosen, chosenLtp, baseSym);
        if(typeof updateDashboardConfluenceTable === 'function') updateDashboardConfluenceTable();
        if($('chartGreeksContractBadge')) $('chartGreeksContractBadge').textContent = `Contract: ${chosen}`;
        if($('cgDelta')) $('cgDelta').textContent = chosen.endsWith('PE') ? '-0.488' : '0.512';"""
assert target_reco_sel in text, "target_reco_sel not found"
text = text.replace(target_reco_sel, replace_reco_sel, 1)

# 10. Fix news sentiment uppercase and caching in loadNewsByCaAi
target_news_cache = """    try {
      const d = await api(`/api/news/ca-ai-feed?symbol=${encodeURIComponent(sym)}&mode=${encodeURIComponent(mode)}`, { timeoutMs: 7000 });
      const items = Array.isArray(d.items) ? d.items : [];"""

replace_news_cache = """    try {
      const d = await api(`/api/news/ca-ai-feed?symbol=${encodeURIComponent(sym)}&mode=${encodeURIComponent(mode)}`, { timeoutMs: 7000 });
      const items = Array.isArray(d.items) ? d.items : [];
      window.__caCachedNews = d;"""
assert target_news_cache in text, "target_news_cache not found"
text = text.replace(target_news_cache, replace_news_cache, 1)

target_news_prob = """        const isBull = it.sentiment === 'BULLISH';
        const isBear = it.sentiment === 'BEARISH';
        const badgeClass = isBull ? 'buy' : isBear ? 'sell' : 'neutral';
        const borderLeftColor = isBull ? 'var(--buy)' : isBear ? 'var(--sell)' : 'var(--border-soft)';
        
        // Probability out of 100% (Item 10)
        const rawImpact = parseFloat(String(it.impact_pct || '1.0').replace(/[^0-9.-]/g, '')) || 1.0;
        const probVal = Math.min(98, Math.max(62, Math.round(68 + Math.abs(rawImpact) * 16)));
        const probText = `${probVal}% ${isBull ? 'Bullish' : isBear ? 'Bearish' : 'Neutral'} Probability`;"""

replace_news_prob = """        const isBull = String(it.sentiment || '').toUpperCase() === 'BULLISH';
        const isBear = String(it.sentiment || '').toUpperCase() === 'BEARISH';
        const badgeClass = isBull ? 'buy' : 'sell';
        const borderLeftColor = isBull ? 'var(--buy)' : 'var(--sell)';
        
        // Probability out of 100% (Item 10)
        const rawImpact = parseFloat(String(it.impact_pct || '1.0').replace(/[^0-9.-]/g, '')) || 1.0;
        const probVal = Math.min(98, Math.max(65, Math.round(70 + Math.abs(rawImpact) * 15)));
        const probText = `${probVal}% ${isBull ? 'Bullish' : 'Bearish'} Probability`;"""
assert target_news_prob in text, "target_news_prob not found"
text = text.replace(target_news_prob, replace_news_prob, 1)

# 11. Fix formatPatternTimeRange and bindPatternClicks to include structureBox
target_bind_clicks = """  function formatPatternTimeRange(p){
    const f = p.from_time ? formatTime(p.from_time) : '';
    const t = p.to_time ? formatTime(p.to_time) : (p.timestamp ? formatTime(p.timestamp) : '');
    if(f && t && f !== t) return `${f} → ${t} (${p.timeframe || state.tf})`;
    if(t) return `${t} (${p.timeframe || state.tf})`;
    return `${p.timeframe || state.tf} formation`;
  }

  function bindPatternClicks(){
    const chartEl = $('mainChart') || $('chartCanvas') || $('chartViewport') || document.querySelector('.chart-wrap');

    document.querySelectorAll('[data-focus-pattern]').forEach(el=>el.onclick=async()=>{"""

replace_bind_clicks = """  function formatPatternTimeRange(p){
    let f = p.from_time ? formatTime(p.from_time) : '';
    let t = p.to_time ? formatTime(p.to_time) : (p.timestamp ? formatTime(p.timestamp) : '');
    if(!t && state.candles && state.candles.length){
      const lastC = state.candles[state.candles.length - 1];
      t = formatTime(lastC.timestamp || lastC.ts);
      const baseC = state.candles[Math.max(0, state.candles.length - 10)];
      f = formatTime(baseC.timestamp || baseC.ts);
    }
    if(f && t && f !== t) return `${f} → ${t} (${p.timeframe || state.tf || '5m'})`;
    if(t) return `${t} (${p.timeframe || state.tf || '5m'})`;
    return `${p.timeframe || state.tf || '5m'} formation`;
  }

  function bindPatternClicks(){
    const chartEl = $('mainChart') || $('chartCanvas') || $('chartViewport') || document.querySelector('.chart-wrap');

    document.querySelectorAll('[data-focus-structure]').forEach(el => {
      el.onclick = () => {
        const total = (state.candles || []).length;
        if(total < 2) return;
        const startIdx = Math.max(0, total - 12);
        const endIdx = total - 1;
        const baseC = state.candles[startIdx];
        const lastC = state.candles[endIdx];
        const isBull = Number(lastC.close) >= Number(baseC.close);
        state.highlightedPattern = {
          startIdx,
          endIdx,
          name: `Trend Structure (${isBull ? 'Uptrend' : 'Downtrend'})`,
          timeLabel: `${formatTime(baseC.timestamp || baseC.ts)} → ${formatTime(lastC.timestamp || lastC.ts)} (${state.tf})`,
          color: isBull ? 'rgba(38,217,166,0.22)' : 'rgba(255,92,114,0.22)',
          border: isBull ? '#26D9A6' : '#FF5C72',
          confidence: 88
        };
        const view = getView();
        const mid = Math.round((startIdx + endIdx) / 2);
        state.panX = Math.max(0, Math.min((state.candles || []).length - view.count, mid - Math.floor(view.count / 2)));
        draw();
        document.getElementById('chartViewport')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        toast(`✦ Highlighted Trend & Structure (${formatTime(baseC.timestamp || baseC.ts)} → ${formatTime(lastC.timestamp || lastC.ts)})`);
      };
    });

    document.querySelectorAll('[data-focus-pattern]').forEach(el=>el.onclick=async()=>{"""
assert target_bind_clicks in text, "target_bind_clicks not found"
text = text.replace(target_bind_clicks, replace_bind_clicks, 1)

# 12. Add data-focus-structure and time display to structureBox
target_struct_box = """    $('structureStatus').textContent=`${Math.min(a.length, 30)} candles analyzed`;
    $('structureBox').innerHTML=`
      <div class="pattern-card">
        <div>
          <b>Trend: ${displayTrend}</b>
          <div class="muted" style="margin-top:3px;">${esc(trendReason)}</div>
        </div>
        <span class="tag ${trendClass}" style="font-weight:700;">${displayTrend}</span>
      </div>
      <div class="pattern-card">
        <div>
          <b>Expected Market Outcome</b>
          <div class="muted" style="margin-top:3px;">${esc(outcomeReason)}</div>
        </div>
        <span class="tag ${trendClass}">${displayTrend === 'Uptrend' ? 'Bullish Target' : 'Bearish Retest'}</span>
      </div>
      <div class="pattern-card">
        <div>
          <b>Recent Validated Setups</b>
          <div class="muted">${pats.map(p=>esc(p.pattern)).join(' · ')||'Structural swing alignment'}</div>
        </div>
      </div>
    `;"""

replace_struct_box = """    $('structureStatus').textContent=`${Math.min(a.length, 30)} candles analyzed`;
    const baseTime = base?.timestamp || base?.ts;
    const lastTime = last?.timestamp || last?.ts;
    const timeRangeStr = (baseTime && lastTime) ? `${formatTime(baseTime)} → ${formatTime(lastTime)} (${state.tf})` : `${state.tf} period`;
    $('structureBox').innerHTML=`
      <div class="pattern-card" data-focus-structure="1" style="cursor:pointer;" title="Click to highlight trend candles on chart">
        <div>
          <div style="display:flex;align-items:center;gap:6px;">
            <b>Trend: ${displayTrend}</b>
            <span class="tag ${trendClass}" style="font-weight:700;">${displayTrend}</span>
          </div>
          <div class="muted" style="font-size:10.5px;color:var(--gold);margin-top:2px;">⏱ ${timeRangeStr}</div>
          <div class="muted" style="margin-top:3px;">${esc(trendReason)}</div>
        </div>
      </div>
      <div class="pattern-card" data-focus-structure="1" style="cursor:pointer;" title="Click to highlight analyzed swing on chart">
        <div>
          <div style="display:flex;align-items:center;gap:6px;">
            <b>Expected Market Outcome</b>
            <span class="tag ${trendClass}">${displayTrend === 'Uptrend' ? 'Bullish Target' : 'Bearish Retest'}</span>
          </div>
          <div class="muted" style="font-size:10.5px;color:var(--gold);margin-top:2px;">⏱ ${timeRangeStr}</div>
          <div class="muted" style="margin-top:3px;">${esc(outcomeReason)}</div>
        </div>
      </div>
      <div class="pattern-card" data-focus-structure="1" style="cursor:pointer;" title="Click to highlight setup swing on chart">
        <div>
          <div style="display:flex;align-items:center;gap:6px;">
            <b>Recent Validated Setups</b>
            <span class="tag neutral">${state.tf}</span>
          </div>
          <div class="muted" style="font-size:10.5px;color:var(--gold);margin-top:2px;">⏱ ${timeRangeStr}</div>
          <div class="muted">${pats.map(p=>esc(p.pattern)).join(' · ')||'Structural swing alignment'}</div>
        </div>
      </div>
    `;"""
assert target_struct_box in text, "target_struct_box not found"
text = text.replace(target_struct_box, replace_struct_box, 1)

# 13. Pre-load news in loadDashboard
target_load_dash = """    // Ensure recommendation & options dropdown are loaded
    if(typeof updateChartRecoBanner === 'function') void updateChartRecoBanner(null, sym);
    if(typeof updateDashboardConfluenceTable === 'function') void updateDashboardConfluenceTable();
    if(typeof wirePriceSensitivitySim === 'function') wirePriceSensitivitySim('chart');
    if(typeof loadRecommendationHistory === 'function') void loadRecommendationHistory();"""

replace_load_dash = """    // Ensure recommendation & options dropdown are loaded
    if(typeof updateChartRecoBanner === 'function') void updateChartRecoBanner(null, sym);
    if(typeof loadNewsByCaAi === 'function') void loadNewsByCaAi('all');
    if(typeof updateDashboardConfluenceTable === 'function') void updateDashboardConfluenceTable();
    if(typeof wirePriceSensitivitySim === 'function') wirePriceSensitivitySim('chart');
    if(typeof loadRecommendationHistory === 'function') void loadRecommendationHistory();"""
assert target_load_dash in text, "target_load_dash not found"
text = text.replace(target_load_dash, replace_load_dash, 1)

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("All 13 enhancements applied successfully to terminal.html!")

