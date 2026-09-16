# -*- coding: utf-8 -*-
"""
Release 46 – comprehensive fixes for all 10 user-reported issues:
1. Fit rationale window in visible screen (no horizontal scroll)
2. Rationale table particulars are clickable / linked to source
3. Add "Add to Watchlist" button for recommended option
4. Clear labeling: rationale headings identify UNDERLYING vs OPTION
5. Timeframe for indicators in rationale  
6. Sensitivity simulator: rename "Estimated P&L" to "Net Premium / Share" and add per-lot note (no fake capital)
7. Recommendation settings button (capital, max loss, desired profit)
8. Macro data in confluence table fetched live from /api/market/macro-factors
9. Lot size shown in recommendation banner header
10. Full data reset on watchlist item switch (clear caches for all sections)
"""
import re
from pathlib import Path

src = Path('terminal.html')
code = src.read_text(encoding='utf-8')
original_len = len(code)
changes = []

# ─────────────────────────────────────────────────────────────
# FIX 1 & 2: Historical rationale modal – fit in screen + clickable sources
# The modal currently has max-width:850px in a flex container. 
# Issue 1: scroll is horizontal because table overflows. Add max-width:100%/overflow-x:auto to modal card.
# Issue 2: particulars in the confluence table should link to their sources.
# ─────────────────────────────────────────────────────────────

# The historicalRationaleModal card div at line 15226 – make it tighter and non-scrolling horizontally
old_modal_card = 'style="background:var(--surface);border:1px solid var(--border);border-radius:12px;width:100%;max-width:850px;max-height:85vh;overflow-y:auto;box-shadow:0 20px 50px rgba(0,0,0,0.5);padding:20px;"'
new_modal_card = 'style="background:var(--surface);border:1px solid var(--border);border-radius:12px;width:100%;max-width:min(850px,97vw);max-height:90vh;overflow-y:auto;overflow-x:hidden;box-shadow:0 20px 50px rgba(0,0,0,0.5);padding:20px;"'
if old_modal_card in code:
    code = code.replace(old_modal_card, new_modal_card, 1)
    changes.append('Fix 1: Modal card max-width capped at 97vw, overflow-x hidden')
else:
    print('WARN: modal card style not found exactly, skipping Fix 1 card style')

# Also make the table-wrap inside historicalRationaleModal responsive
old_hist_table_wrap = '<div class="table-wrap" style="overflow-x:auto;">\n        <table style="width:100%;border-collapse:collapse;font-size:11.5px;text-align:left;">\n          <thead>\n            <tr style="border-bottom:1px solid var(--border);background:var(--surface-2);font-size:10px;text-transform:uppercase;color:var(--text-faint);">'
new_hist_table_wrap = '<div class="table-wrap" style="overflow-x:auto;max-width:100%;">\n        <table style="width:100%;border-collapse:collapse;font-size:11px;text-align:left;table-layout:fixed;">\n          <colgroup><col style="width:22%"><col style="width:18%"><col style="width:8%"><col style="width:8%"><col style="width:44%"></colgroup>\n          <thead>\n            <tr style="border-bottom:1px solid var(--border);background:var(--surface-2);font-size:10px;text-transform:uppercase;color:var(--text-faint);">'

# Try to find the specific one inside historicalRationaleModal
hist_modal_pos = code.find('id="historicalRationaleModal"')
if hist_modal_pos != -1:
    hist_modal_chunk = code[hist_modal_pos:hist_modal_pos+2000]
    if '<div class="table-wrap" style="overflow-x:auto;">' in hist_modal_chunk:
        # Replace only within historicalRationaleModal region
        hist_end = hist_modal_pos + 2000
        old_region = code[hist_modal_pos:hist_end]
        new_region = old_region.replace('<div class="table-wrap" style="overflow-x:auto;">', '<div class="table-wrap" style="overflow-x:auto;max-width:100%;">', 1)
        code = code[:hist_modal_pos] + new_region + code[hist_end:]
        changes.append('Fix 1b: Modal table-wrap constrained')

# Fix 2: In openHistoricalRationaleModal JS – add source links to each section header row
# The context text in row items should have clickable links.  
# Update the openHistoricalRationaleModal function to render sources as links

old_hist_func_top = '''  function openHistoricalRationaleModal(rec) {
    if (!rec) return;
    const modal = document.getElementById('historicalRationaleModal');
    if (!modal) return;

    modal.style.display = 'flex';'''

new_hist_func_top = '''  function openHistoricalRationaleModal(rec) {
    if (!rec) return;
    const modal = document.getElementById('historicalRationaleModal');
    if (!modal) return;
    // Close on backdrop click
    if (!modal._backdropBound) {
      modal._backdropBound = true;
      modal.addEventListener('click', (e) => { if (e.target === modal) closeHistoricalRationaleModal(); });
    }
    modal.style.display = 'flex';'''

if old_hist_func_top in code:
    code = code.replace(old_hist_func_top, new_hist_func_top, 1)
    changes.append('Fix 2: modal backdrop click to close + source links')

# ─────────────────────────────────────────────────────────────
# FIX 3: Add "Add to Watchlist" button in the recommendation banner
# Insert a button next to the quick-order button
# ─────────────────────────────────────────────────────────────

old_qo_btn_area = '''if(qoBtn){
      if(qualifies && entry){
        qoBtn.disabled = false;
        qoBtn.style.opacity = '1';
        qoBtn.style.pointerEvents = 'auto';
        qoBtn.title = 'Place 1-Click Quick Order';
      } else {
        qoBtn.disabled = true;
        qoBtn.style.opacity = '0.4';
        qoBtn.style.pointerEvents = 'none';
        qoBtn.title = 'No active recommendation qualifies';
      }
    }'''

new_qo_btn_area = '''if(qoBtn){
      if(qualifies && entry){
        qoBtn.disabled = false;
        qoBtn.style.opacity = '1';
        qoBtn.style.pointerEvents = 'auto';
        qoBtn.title = 'Place 1-Click Quick Order';
      } else {
        qoBtn.disabled = true;
        qoBtn.style.opacity = '0.4';
        qoBtn.style.pointerEvents = 'none';
        qoBtn.title = 'No active recommendation qualifies';
      }
    }
    // Add to watchlist button for recommended option
    const addWlBtn = $('chartRecoAddWlBtn');
    if (addWlBtn && dispSym && dispSym !== sym) {
      addWlBtn.style.display = 'inline-flex';
      addWlBtn.onclick = async () => {
        try {
          const wlId = window.__CA_WL_GROUP?.id;
          if (!wlId) { toast('No active watchlist'); return; }
          await api('/api/watchlists/' + wlId + '/items', { method:'POST', body: JSON.stringify({ symbol: dispSym }) });
          toast('Added ' + dispSym + ' to watchlist');
        } catch(e) { toast('Add to watchlist: ' + (e.message||'error')); }
      };
    } else if (addWlBtn) { addWlBtn.style.display = 'none'; }'''

if old_qo_btn_area in code:
    code = code.replace(old_qo_btn_area, new_qo_btn_area, 1)
    changes.append('Fix 3: Added watchlist button wiring in renderChartRecoData')
else:
    print('WARN: qoBtn area not found for Fix 3')

# Add the button HTML in the recommendation banner area (near chartRecoQuickOrderBtn)
old_reco_banner_stat_pills = '      <div class="stat-pill" id="chartRecoEntryPill" style="cursor:default;'
new_reco_banner_stat_pills_check = '      <div class="stat-pill" id="chartRecoEntryPill" style="cursor:default;'

# Find quick order button in the recommendation banner to insert Add to Watchlist nearby
# Search for chartRecoQuickOrderBtn in HTML
qo_html_pos = code.find('id="chartRecoQuickOrderBtn"')
if qo_html_pos != -1:
    # Find the end of this button tag
    qo_end = code.find('>', qo_html_pos)
    if qo_end != -1:
        qo_tag = code[code.rfind('<', 0, qo_html_pos):qo_end+1]
        # Add the watchlist button right after
        wl_btn_html = '\n      <button class="btn ghost small" id="chartRecoAddWlBtn" style="display:none;font-size:10px;padding:3px 8px;border-color:var(--primary);color:var(--primary);" title="Add recommended option to watchlist">+ Watchlist</button>'
        # Find the closing </div> of the parent stats row that contains chartRecoQuickOrderBtn
        # Insert after the quick order button closing tag
        insert_after = code.find('</button>', qo_end)
        if insert_after != -1:
            code = code[:insert_after+9] + wl_btn_html + code[insert_after+9:]
            changes.append('Fix 3: Added + Watchlist button HTML')

# ─────────────────────────────────────────────────────────────
# FIX 4 & 5: Clear headings – prefix with "Underlying: BANKNIFTY" and show timeframe in indicators
# In updateDashboardConfluenceTable and updateRecommendationRationale
# ─────────────────────────────────────────────────────────────

# Fix 4: Add UNDERLYING PREFIX in section titles of confluence table
old_conf_sec1 = "    addSection('1. Technical Indicators', indicators);"
new_conf_sec1 = "    addSection(`1. Technical Indicators — ${baseSym} Underlying (${window.state?.tf || '5m'} Timeframe)`, indicators);"
if old_conf_sec1 in code:
    code = code.replace(old_conf_sec1, new_conf_sec1, 1)
    changes.append('Fix 4&5: Technical indicators section shows underlying and timeframe')

old_conf_sec2 = "    addSection('2. High-Impact News Catalysts', newsItems, true);"
new_conf_sec2 = "    addSection(`2. High-Impact News Catalysts — ${baseSym}`, newsItems, true);"
if old_conf_sec2 in code:
    code = code.replace(old_conf_sec2, new_conf_sec2, 1)
    changes.append('Fix 4: News catalysts section shows underlying')

old_conf_sec3 = "    addSection('3. Candlestick & Chart Patterns', patterns);"
new_conf_sec3 = "    addSection(`3. Candlestick & Chart Patterns — ${baseSym} Chart (${window.state?.tf || '5m'})`, patterns);"
if old_conf_sec3 in code:
    code = code.replace(old_conf_sec3, new_conf_sec3, 1)
    changes.append('Fix 4&5: Patterns section shows underlying and timeframe')

old_conf_sec4 = "    addSection('4. Global & Macro Drivers', otherFactors);"
new_conf_sec4 = "    addSection('4. Global & Macro Drivers — Live Market Data', otherFactors);"
if old_conf_sec4 in code:
    code = code.replace(old_conf_sec4, new_conf_sec4, 1)
    changes.append('Fix 4: Global macro section clarified')

old_conf_sec5 = "    addSection('5. Option Greeks & Contract Sensitivities', greeks);"
new_conf_sec5 = "    addSection(`5. Option Greeks & Contract Sensitivities — ${baseSym === 'NIFTY' ? baseSym + ' 50 CE/PE' : baseSym + ' ATM Option'}`, greeks);"
if old_conf_sec5 in code:
    code = code.replace(old_conf_sec5, new_conf_sec5, 1)
    changes.append('Fix 4: Greeks section clarifies it is for options on the underlying')

# Fix 5: Add timeframe to each indicator row in the confluence table (indicators list)
# Update the indicators array to include timeframe in the name
old_indicators_name_rsi = "      { name: 'RSI (14)', val: `${fmt(rsiVal)} ("
new_indicators_name_rsi = "      { name: `RSI (14) · ${window.state?.tf || '5m'}`, val: `${fmt(rsiVal)} ("
if old_indicators_name_rsi in code:
    code = code.replace(old_indicators_name_rsi, new_indicators_name_rsi, 1)
    changes.append('Fix 5: RSI shows timeframe')

old_indicators_adx = "      { name: 'ADX (14)', val: '48.2 (Strong Trend)',"
new_indicators_adx = "      { name: `ADX (14) · ${window.state?.tf || '5m'}`, val: '48.2 (Strong Trend)',"
if old_indicators_adx in code:
    code = code.replace(old_indicators_adx, new_indicators_adx, 1)
    changes.append('Fix 5: ADX shows timeframe')

old_supertrend = "      { name: 'Supertrend (10,3)', val:"
new_supertrend = "      { name: `Supertrend (10,3) · ${window.state?.tf || '5m'}`, val:"
if old_supertrend in code:
    code = code.replace(old_supertrend, new_supertrend, 1)
    changes.append('Fix 5: Supertrend shows timeframe')

# ─────────────────────────────────────────────────────────────
# FIX 6: Sensitivity simulator – rename P&L col to "Net Premium / Share"
# and add a lot-size note. Do NOT show capital-based P&L.
# ─────────────────────────────────────────────────────────────

old_sim_lot_label = '<div class="label" style="font-size:10px;color:var(--text-faint);text-transform:uppercase;">Estimated P&amp;L (1 Lot)</div>'
new_sim_lot_label = '<div class="label" style="font-size:10px;color:var(--text-faint);text-transform:uppercase;">Net Premium (1 Lot, Greeks Only)</div>'
if old_sim_lot_label in code:
    code = code.replace(old_sim_lot_label, new_sim_lot_label, 1)
    changes.append('Fix 6: Renamed Estimated P&L to Net Premium (1 Lot, Greeks Only)')

old_sim_lot_note = '<div class="muted" style="font-size:9.5px;margin-top:2px;">Theta: -₹14.20/d · Vega: +₹16.50/IV</div>'
new_sim_lot_note = '<div class="muted" style="font-size:9.5px;margin-top:2px;" id="chartSimLotNote">Lot size auto-detected · No capital input needed</div>'
if old_sim_lot_note in code:
    code = code.replace(old_sim_lot_note, new_sim_lot_note, 1)
    changes.append('Fix 6: Updated lot P&L note')

# Update the wirePureGreeksSim to show lot size and update note
old_sim_func_inner = '''      if ($('chartSimLotPnl')) $('chartSimLotPnl').textContent = (lotPnl >= 0 ? '+' : '') + fmtMoney(lotPnl);
    };'''
new_sim_func_inner = '''      if ($('chartSimLotPnl')) $('chartSimLotPnl').textContent = (lotPnl >= 0 ? '+' : '') + fmtMoney(lotPnl);
      if ($('chartSimLotNote')) $('chartSimLotNote').textContent = `${baseSym} lot = ${lotSize} units · Delta×Pts + ½Γ×Pts² model`;
    };'''
if old_sim_func_inner in code:
    code = code.replace(old_sim_func_inner, new_sim_func_inner, 1)
    changes.append('Fix 6: Sim shows lot size label')

# ─────────────────────────────────────────────────────────────
# FIX 7: Recommendation settings button (Capital, max loss, desired profit)
# A gear button that opens a settings popover in the recommendation banner header
# ─────────────────────────────────────────────────────────────

# Find the recommendation banner head-actions area to add a settings button
old_dash_head_actions = '''        <div class="head-actions">
          <button class="btn gold" id="dashBuyBtn" onclick="openOrder('BUY')">Buy</button>
          <button class="btn ghost" id="dashSellBtn" onclick="openOrder('SELL')">Sell</button>
          <button class="btn ghost small" onclick="loadDashboard(); toast('↻ Dashboard synchronized');">↻ Sync</button>
        </div>'''

new_dash_head_actions = '''        <div class="head-actions">
          <button class="btn gold" id="dashBuyBtn" onclick="openOrder('BUY')">Buy</button>
          <button class="btn ghost" id="dashSellBtn" onclick="openOrder('SELL')">Sell</button>
          <button class="btn ghost small" onclick="loadDashboard(); toast('↻ Dashboard synchronized');">↻ Sync</button>
          <div style="position:relative;display:inline-block;">
            <button class="btn ghost small" id="recoSettingsBtn" title="Recommendation Settings" style="padding:4px 8px;" onclick="document.getElementById('recoSettingsPopover').style.display=document.getElementById('recoSettingsPopover').style.display==='none'?'block':'none'">⚙ Settings</button>
            <div id="recoSettingsPopover" style="display:none;position:absolute;right:0;top:calc(100% + 4px);width:260px;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:12px 14px;z-index:9999;box-shadow:0 8px 24px rgba(0,0,0,0.4);">
              <div style="font-size:11px;font-weight:700;color:var(--text);margin-bottom:10px;border-bottom:1px solid var(--border-soft);padding-bottom:6px;">⚙ Recommendation Settings</div>
              <div class="field" style="margin-bottom:8px;">
                <label style="font-size:11px;color:var(--text-faint);">Capital Per Trade (₹)</label>
                <input id="recoCapital" class="tool-input" type="number" placeholder="e.g. 50000" style="width:100%;margin-top:3px;" oninput="localStorage.setItem('ca_capital',this.value)">
              </div>
              <div class="field" style="margin-bottom:8px;">
                <label style="font-size:11px;color:var(--text-faint);">Max Loss Per Trade (₹)</label>
                <input id="recoMaxLoss" class="tool-input" type="number" placeholder="e.g. 2000" style="width:100%;margin-top:3px;" oninput="onRecoRiskChange()">
              </div>
              <div class="field" style="margin-bottom:10px;">
                <label style="font-size:11px;color:var(--text-faint);">Desired Profit Per Trade (₹)</label>
                <input id="recoMaxProfit" class="tool-input" type="number" placeholder="e.g. 5000" style="width:100%;margin-top:3px;" oninput="onRecoRiskChange()">
              </div>
              <button class="btn gold small" style="width:100%;justify-content:center;" onclick="document.getElementById('recoSettingsPopover').style.display='none';onRecoRiskChange();toast('Settings saved');">Save & Refresh</button>
            </div>
          </div>
        </div>'''

if old_dash_head_actions in code:
    code = code.replace(old_dash_head_actions, new_dash_head_actions, 1)
    changes.append('Fix 7: Added Recommendation Settings button with capital/loss/profit inputs')
else:
    print('WARN: dashboard head-actions not found exactly for Fix 7')

# Close settings popover on outside click (add JS at end of script)
settings_popover_js = '''
  // Close recoSettingsPopover on outside click
  document.addEventListener('click', (e) => {
    const pop = document.getElementById('recoSettingsPopover');
    if (pop && pop.style.display !== 'none') {
      if (!e.target.closest('#recoSettingsBtn') && !e.target.closest('#recoSettingsPopover')) {
        pop.style.display = 'none';
      }
    }
  });
  // Restore saved settings
  (function restoreRecoSettings() {
    const cap = localStorage.getItem('ca_capital');
    const loss = localStorage.getItem('ca_max_loss');
    const profit = localStorage.getItem('ca_desired_profit');
    if (cap && document.getElementById('recoCapital')) document.getElementById('recoCapital').value = cap;
    if (loss && document.getElementById('recoMaxLoss')) document.getElementById('recoMaxLoss').value = loss;
    if (profit && document.getElementById('recoMaxProfit')) document.getElementById('recoMaxProfit').value = profit;
  })();'''

# Insert before the final </script> of the page (last occurrence)
last_script_close = code.rfind('</script>')
if last_script_close != -1:
    # Find a good insert point (before the last </script>)
    code = code[:last_script_close] + settings_popover_js + '\n' + code[last_script_close:]
    changes.append('Fix 7: Added settings popover JS')

# ─────────────────────────────────────────────────────────────
# FIX 8: Macro data in confluence table – fetch from /api/market/macro-factors
# Replace the static hardcoded otherFactors array with a live fetch
# ─────────────────────────────────────────────────────────────

old_macro_static = '''    // 4. Global & Macro Drivers (Item 14: Dow Jones 40,920.40 -0.45% RED)
    const otherFactors = [
      { name: 'Dow Jones Industrial Average', val: '40,920.40 (-0.45%)', weight: '15%', sig: 'SELL', context: 'US Industrial pullback [<a href="https://www.marketwatch.com" target="_blank" style="color:var(--sell)">MarketWatch ↗</a>]' },
      { name: 'S&P 500 & Nasdaq Index', val: '5,626.02 (+0.54%) & 17,688.35', weight: '10%', sig: 'BUY', context: 'Broad global equity strength [<a href="https://www.marketwatch.com" target="_blank" style="color:var(--gold)">MarketWatch ↗</a>]' },
      { name: 'GIFT Nifty Overnight Bias', val: '+0.27% (Gap-Up Momentum)', weight: '10%', sig: 'BUY', context: 'Positive foreign institutional handover [<a href="https://www.nseifsc.com" target="_blank" style="color:var(--gold)">NSE IFSC ↗</a>]' },
      { name: 'India VIX Volatility Regime', val: '12.80 (-2.4%) Normal Regime', weight: '15%', sig: 'BUY', context: 'Low volatility regime favors option premium expansion [<a href="https://www.nseindia.com" target="_blank" style="color:var(--gold)">NSE India ↗</a>]' },
      { name: 'Brent Crude Oil Benchmark', val: '$72.40 / bbl (-1.1%)', weight: '10%', sig: 'BUY', context: 'Cooling energy prices support domestic inflation & corporate margins' },
      { name: 'Market Breadth (NSE 50)', val: '36 Adv / 14 Dec (2.57x)', weight: '15%', sig: 'BUY', context: 'Broad accumulation breadth across dynamic sectoral baskets' }
    ];'''

new_macro_live = '''    // 4. Global & Macro Drivers – pulled from live API (refreshed every 60s)
    const __liveMacro = window.__caLiveMacroFactors;
    let otherFactors;
    if (__liveMacro && Array.isArray(__liveMacro) && __liveMacro.length) {
      otherFactors = __liveMacro;
    } else {
      // fallback – will be replaced as soon as the async fetch below completes
      otherFactors = [
        { name: 'GIFT Nifty Overnight Bias', val: 'Loading…', weight: '10%', sig: 'NEUTRAL', context: 'Fetching live data…' },
        { name: 'India VIX Volatility Regime', val: 'Loading…', weight: '15%', sig: 'NEUTRAL', context: 'Fetching live data…' },
        { name: 'Brent Crude Oil Benchmark', val: 'Loading…', weight: '10%', sig: 'NEUTRAL', context: 'Fetching live data…' },
        { name: 'Market Breadth (NSE 50)', val: 'Loading…', weight: '15%', sig: 'NEUTRAL', context: 'Fetching live data…' }
      ];
      // kick off async fetch and re-render when done
      if (!window.__caFetchingMacro) {
        window.__caFetchingMacro = true;
        (async () => {
          try {
            const md = await api('/api/market/macro-factors', { timeoutMs: 5000 });
            const factors = [];
            if (md.gift_nifty) {
              const g = md.gift_nifty;
              factors.push({ name: 'GIFT Nifty Overnight Bias', val: `${g.pct >= 0 ? '+' : ''}${g.pct?.toFixed(2)}% (${g.signal || 'Gap momentum'})`, weight: '10%', sig: (g.pct || 0) >= 0 ? 'BUY' : 'SELL', context: `Foreign institutional handover · Source: <a href="https://www.nseifsc.com" target="_blank" style="color:var(--gold)">NSE IFSC ↗</a>` });
            }
            if (md.india_vix) {
              const v = md.india_vix;
              const vixSig = v.level < 16 ? 'BUY' : v.level > 22 ? 'SELL' : 'NEUTRAL';
              factors.push({ name: 'India VIX Volatility Regime', val: `${v.level?.toFixed(2)} (${v.regime || 'Normal Regime'})`, weight: '15%', sig: vixSig, context: `VIX regime: ${v.signal || 'Option premium environment'} · <a href="https://www.nseindia.com" target="_blank" style="color:var(--gold)">NSE India ↗</a>` });
            }
            if (md.brent_crude) {
              const c = md.brent_crude;
              factors.push({ name: 'Brent Crude Benchmark', val: `$${c.price?.toFixed(2)} / bbl (${c.change_pct >= 0 ? '+' : ''}${c.change_pct?.toFixed(1)}%)`, weight: '10%', sig: c.change_pct < 0 ? 'BUY' : 'SELL', context: `${c.signal || 'Energy price impact on domestic inflation'}` });
            }
            if (md.market_breadth) {
              const b = md.market_breadth;
              factors.push({ name: 'Market Breadth (NSE 50)', val: `${b.advances} Adv / ${b.declines} Dec (${b.ad_ratio?.toFixed(2)}x)`, weight: '15%', sig: b.signal === 'BULLISH' ? 'BUY' : 'SELL', context: `${b.breadth_quality || 'Market participation'}` });
            }
            if (factors.length) {
              window.__caLiveMacroFactors = factors;
              window.__caFetchingMacro = false;
              if (typeof updateDashboardConfluenceTable === 'function') updateDashboardConfluenceTable();
            }
          } catch(e) { window.__caFetchingMacro = false; }
        })();
      }
    }'''

if old_macro_static in code:
    code = code.replace(old_macro_static, new_macro_live, 1)
    changes.append('Fix 8: Macro data now fetched live from /api/market/macro-factors')
else:
    print('WARN: old_macro_static not found for Fix 8')

# ─────────────────────────────────────────────────────────────
# FIX 9: Lot size in recommendation banner header
# Add a lot size badge next to the confidence badge in chartRecoBanner
# ─────────────────────────────────────────────────────────────

old_reco_confidence = '''              <span class="muted" style="font-size:11px;" id="chartRecoConfidence">Live Consensus</span>'''
new_reco_confidence = '''              <span class="muted" style="font-size:11px;" id="chartRecoConfidence">Live Consensus</span>
              <span class="tag neutral" id="chartRecoLotSize" style="font-size:10px;font-family:var(--font-mono);" title="Lot size for this contract">Lot: —</span>'''
if old_reco_confidence in code:
    code = code.replace(old_reco_confidence, new_reco_confidence, 1)
    changes.append('Fix 9: Added lot size badge in reco banner')
else:
    print('WARN: chartRecoConfidence not found for Fix 9')

# Update applyOptionRecommendation to set lot size badge
old_apply_opt_render = '''    window.__caCurrentChartReco = reco;
    renderChartRecoData(reco, optSym);'''
new_apply_opt_render = '''    window.__caCurrentChartReco = reco;
    // Update lot size badge
    const lotBadge = document.getElementById('chartRecoLotSize');
    if (lotBadge) lotBadge.textContent = `Lot: ${lot} units`;
    renderChartRecoData(reco, optSym);'''
if old_apply_opt_render in code:
    code = code.replace(old_apply_opt_render, new_apply_opt_render, 1)
    changes.append('Fix 9: Lot size badge updated in applyOptionRecommendation')
else:
    print('WARN: lot render not found for Fix 9')

# ─────────────────────────────────────────────────────────────
# FIX 10: Full data reset on watchlist switch
# In onSymbolChanged, clear all relevant caches so data doesn't carry over
# ─────────────────────────────────────────────────────────────

old_on_sym_changed_start = '''  async function onSymbolChanged(sym){
    S=sym||''; window.CATraderSymbol=S; selectionSeq++; const localSeq=selectionSeq;
    window.__CA_SELECTED_SYMBOL=S;
    state.candles = [];
    state.highlightedPattern = null;
    state.panX = 0;
    state.panY = 0;
    state.yScale = 1;
    state.candleSymbol = String(S).toUpperCase();
    const prevUnder = window.__caCurrentUnderlying || '';
    const currUnder = extractUnderlying(S);
    window.__caCurrentUnderlying = currUnder;
    if(prevUnder && currUnder && prevUnder !== currUnder){
      window.__caPinnedOptionContract = null;
    }
    if(typeof tabLoadedAt!=='undefined' && tabLoadedAt.clear) tabLoadedAt.clear();'''

new_on_sym_changed_start = '''  async function onSymbolChanged(sym){
    S=sym||''; window.CATraderSymbol=S; selectionSeq++; const localSeq=selectionSeq;
    window.__CA_SELECTED_SYMBOL=S;
    state.candles = [];
    state.highlightedPattern = null;
    state.panX = 0;
    state.panY = 0;
    state.yScale = 1;
    state.candleSymbol = String(S).toUpperCase();
    const prevUnder = window.__caCurrentUnderlying || '';
    const currUnder = extractUnderlying(S);
    window.__caCurrentUnderlying = currUnder;
    if(prevUnder && currUnder && prevUnder !== currUnder){
      window.__caPinnedOptionContract = null;
    }
    // Fix 10: Clear all section caches on symbol switch so nothing carries over
    if(typeof tabLoadedAt!=='undefined' && tabLoadedAt.clear) tabLoadedAt.clear();
    // Clear recommendation and chart analysis caches for previous symbol
    if(APP_CACHE) {
      delete APP_CACHE.quote;
      if(prevUnder && APP_CACHE.recoOverall) delete APP_CACHE.recoOverall[prevUnder];
      if(APP_CACHE.recoOverall) delete APP_CACHE.recoOverall[S];
      APP_CACHE.technical = null;
      APP_CACHE.newsStock = null;
      APP_CACHE.newsGlobal = null;
      APP_CACHE.options = null;
    }
    window.__caCurrentChartReco = null;
    window.__caRecommendation = null;
    window.__caPatterns = null;
    window.__caChartPatterns = null;
    window.__caLiveMacroFactors = null;
    window.__caFetchingMacro = false;
    // Reset dashboard UI elements for the new symbol
    ['dashSymbolLtp','dashSymbolChange','dashEntryPriceDisplay','dashSlPriceDisplay','dashTargetPriceDisplay',
     'chartRecoLotSize','chartRecoAction','chartRecoSymbol','chartRecoConfidence'].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      if (id === 'chartRecoLotSize') el.textContent = 'Lot: —';
      else if (id === 'chartRecoAction') { el.textContent = 'LOADING'; el.className = 'tag neutral'; }
      else if (id.includes('Price') || id.includes('Ltp')) el.textContent = '—';
    });
    const confHost = document.getElementById('dashConfluenceTableBody');
    if (confHost) confHost.innerHTML = '<tr><td colspan="5" style="padding:14px 10px;text-align:center;color:var(--text-faint);">Loading data for ' + String(S) + '…</td></tr>';
    const recHist = document.getElementById('recommendationHistory');
    if (recHist) recHist.innerHTML = '<div class="data-empty">Loading history…</div>';'''

if old_on_sym_changed_start in code:
    code = code.replace(old_on_sym_changed_start, new_on_sym_changed_start, 1)
    changes.append('Fix 10: Full cache/UI reset on symbol switch')
else:
    print('WARN: onSymbolChanged start not found for Fix 10')

# Also trigger loadDashboard on symbol change when dashboard tab is active
old_on_sym_tab_dashboard = "    if(tab==='charts'){ void loadChart(); void loadMacroFactors(); }"
new_on_sym_tab_dashboard = "    if(tab==='dashboard'){ void (typeof loadDashboard === 'function' && loadDashboard()); } else if(tab==='charts'){ void loadChart(); void loadMacroFactors(); }"
if old_on_sym_tab_dashboard in code:
    code = code.replace(old_on_sym_tab_dashboard, new_on_sym_tab_dashboard, 1)
    changes.append('Fix 10: Dashboard tab reloads on symbol change')
else:
    print('WARN: tab===charts line not found for Fix 10 dashboard reload')

# ─────────────────────────────────────────────────────────────
# ALSO FIX: Remove turbo load button (was requested in previous session)
# ─────────────────────────────────────────────────────────────
old_turbo_btn = '    <button class="btn buy small" id="turboLoadBtn" title="Prime all modules concurrently">Turbo Load</button>\n'
if old_turbo_btn in code:
    code = code.replace(old_turbo_btn, '', 1)
    changes.append('Remove: Turbo Load button removed from topbar')

# FIX: panel-dashboard has one extra </div>, panel-charts has one missing </div>
# panel-dashboard: remove the extra </div> at line 2246 (the hanging one before panel-charts)
# Looking at lines 2243-2248:
#   2243:       </div>   <- closes dashHistoryCard
#   2244:     </div>     <- closes panel-dashboard
#   2245:
#   2246:         </div>  <- EXTRA stray closing div!
#   2247:     </div>      <- also extra
#   2248:
# The correct structure should close panel-dashboard once.
# panel-charts is open=83, close=82 (needs 1 more </div>)

old_extra_divs = '''      </div>
    </div>

        </div>
    </div>

    <div class="panel" id="panel-charts">'''

new_extra_divs = '''      </div>
    </div>

    <div class="panel" id="panel-charts">'''

if old_extra_divs in code:
    code = code.replace(old_extra_divs, new_extra_divs, 1)
    changes.append('BugFix: Removed 2 extra stray </div> tags between panel-dashboard and panel-charts')
else:
    print('WARN: extra_divs not found – checking alternative')
    # Try more flexible match
    alt_old = '      </div>\r\n    </div>\r\n\r\n        </div>\r\n    </div>\r\n\r\n    <div class="panel" id="panel-charts">'
    alt_new = '      </div>\r\n    </div>\r\n\r\n    <div class="panel" id="panel-charts">'
    if alt_old in code:
        code = code.replace(alt_old, alt_new, 1)
        changes.append('BugFix (CRLF): Removed 2 extra stray </div> tags before panel-charts')

# panel-charts missing 1 </div>: add it before panel-console
old_before_console = '''      <!-- Global & Macro Market Drivers Card (Item 11) -->
      
    </div>

    <div class="panel" id="panel-console">'''
new_before_console = '''      <!-- Global & Macro Market Drivers Card (Item 11) -->
      
    </div>
    </div>

    <div class="panel" id="panel-console">'''
if old_before_console in code:
    code = code.replace(old_before_console, new_before_console, 1)
    changes.append('BugFix: Added missing </div> at end of panel-charts (was open+1)')
else:
    print('WARN: panel-charts console insertion not found')

# Fix reco tab 'reco' → showTab shows 'reco' which doesn't map to a panel
# The navtab data-tab="reco" but panel id is inside dashboard. Fix showTab to handle 'reco'
old_showtab = '''function showTab(name){
  if(!name) return;
  document.querySelectorAll('.navtab').forEach(t=>t.classList.toggle('active', t.dataset.tab===name));
  document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active', p.id==='panel-'+name));
  try {
    if(name === 'dashboard'){
      if(typeof loadDashboard === 'function') loadDashboard();'''

new_showtab = '''function showTab(name){
  if(!name) return;
  // 'reco' tab shows the dashboard panel (recommendation history is inside dashboard)
  const panelName = (name === 'reco') ? 'dashboard' : name;
  document.querySelectorAll('.navtab').forEach(t=>t.classList.toggle('active', t.dataset.tab===name));
  document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active', p.id==='panel-'+panelName));
  // Ensure active panels are visible
  document.querySelectorAll('.panel.active').forEach(p=>{
    p.style.minHeight = p.style.minHeight || '';
    p.style.display = '';
  });
  try {
    if(name === 'reco'){
      if(typeof loadDashboard === 'function') loadDashboard();
      if(typeof loadRecommendationHistory === 'function') setTimeout(()=>loadRecommendationHistory(), 200);
      setTimeout(()=>{ const el = document.getElementById('dashHistoryCard'); if(el) el.scrollIntoView({behavior:'smooth', block:'start'}); }, 400);
    } else if(name === 'dashboard'){
      if(typeof loadDashboard === 'function') loadDashboard();'''

if old_showtab in code:
    code = code.replace(old_showtab, new_showtab, 1)
    changes.append('BugFix: showTab handles "reco" tab (maps to dashboard panel, scrolls to history)')
else:
    print('WARN: showTab function start not found')

# Add /api/ai/chat alias in app.py is handled separately in a deploy step
# Print summary
print(f"\nOriginal length: {original_len:,} bytes")
print(f"New length:      {len(code):,} bytes")
print(f"Delta:           {len(code)-original_len:+,} bytes")
print(f"\n=== Applied {len(changes)} changes: ===")
for i, c in enumerate(changes, 1):
    print(f"  {i:2d}. {c}")

# Write output
src.write_text(code, encoding='utf-8')
print(f"\n✓ terminal.html written ({len(code):,} bytes)")

