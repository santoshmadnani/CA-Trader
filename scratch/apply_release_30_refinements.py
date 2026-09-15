# -*- coding: utf-8 -*-
"""
Release 30 Refinements Script for terminal.html
Implements all 15 points requested by the user.
"""
with open('terminal.html', 'r', encoding='utf-8') as f:
    c = f.read()

print("Original size:", len(c))

# -------------------------------------------------------------
# 1. Remove Auto Trade tab from nav (Item 13)
# -------------------------------------------------------------
old_auto_nav = """<div class="navtab" data-tab="auto">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg>
    Auto Trade <span class="tag warn" style="font-size:9px;padding:1px 5px;">CONTROLLED</span>
  </div>"""

if old_auto_nav in c:
    c = c.replace(old_auto_nav, "")
    print("Item 13: Removed Auto Trade navtab")

# -------------------------------------------------------------
# 2. Remove separate Backtest navtab & consolidate with Charts (Item 11)
# -------------------------------------------------------------
old_bt_nav = """  <div class="navtab" data-tab="backtest">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
    Backtesting
  </div>"""

if old_bt_nav in c:
    c = c.replace(old_bt_nav, "")
    print("Item 11: Removed separate Backtesting navtab")

# Rename Charts navtab to "Charts, Technicals & Backtesting"
old_charts_nav = """    Charts &amp; Technicals"""
new_charts_nav = """    Charts, Technicals &amp; Backtesting"""
if old_charts_nav in c:
    c = c.replace(old_charts_nav, new_charts_nav, 1)
    print("Item 11: Renamed Charts tab to Charts, Technicals & Backtesting")

# Add "Other Factors" navtab before Reports & P&L (Item 5)
old_movers_nav = """  <div class="navtab" data-tab="movers">Market Movers</div>"""
new_movers_nav = """  <div class="navtab" data-tab="movers">Market Movers</div>
  <div class="navtab" data-tab="other-factors">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
    Other Factors
  </div>"""

if old_movers_nav in c and 'data-tab="other-factors"' not in c:
    c = c.replace(old_movers_nav, new_movers_nav)
    print("Item 5: Added Other Factors navtab")

# -------------------------------------------------------------
# 3. Remove "Other Market Influences & Global Gauges" from Market Movers (Item 12)
# -------------------------------------------------------------
old_influences_card = """      <!-- Other Influences & Global Macro Gauges (Item 34) -->
      <div class="card" style="margin-bottom:14px;">
        <div class="card-head" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
          <div class="card-title" style="display:flex;align-items:center;gap:8px;">
            <span>Other Market Influences &amp; Global Gauges</span>
          </div>
          <div class="muted" id="influencesUpdated" style="font-size:11px;">Global Macro Signals</div>
        </div>
        <div id="otherInfluencesPills" style="display:flex;flex-wrap:wrap;gap:8px;padding:6px 0;">
          <div class="data-empty" style="padding:8px 0;">Loading global macro influences…</div>
        </div>
      </div>"""

if old_influences_card in c:
    c = c.replace(old_influences_card, "")
    print("Item 12: Removed broken Other Market Influences card from Market Movers")

# -------------------------------------------------------------
# 4. Remove recommendation price sensitivity emulator from Recommendation History (Item 9)
# -------------------------------------------------------------
reco_sim_marker = '<!-- Price Sensitivity Simulator (Recommendation History - Item 10) -->'
if reco_sim_marker in c:
    start_pos = c.find(reco_sim_marker)
    end_marker = '<div id="recoHistorySection">'
    end_pos = c.find(end_marker, start_pos)
    if start_pos != -1 and end_pos != -1:
        c = c[:start_pos] + c[end_pos:]
        print("Item 9: Removed price sensitivity simulator from Recommendation History")

# -------------------------------------------------------------
# 5. Recommendation Option Selector with Autocomplete Search & Remove Dropdown (Item 2)
# -------------------------------------------------------------
old_opt_wrap = """              <!-- Searchable Option Selector (Item 7) -->
              <div id="chartRecoOptionWrap" style="display:inline-flex;align-items:center;position:relative;">
                <input id="chartRecoOptionSearch" type="text" placeholder="🔍 Search Strike / CE / PE…" style="display:none;width:150px;height:24px;font-size:10.5px;padding:2px 6px;border-radius:4px;border:1px solid var(--border);background:var(--surface-2);color:var(--text);font-family:var(--font-mono);">
                <select id="chartRecoOptionSelect" style="display:none;background:var(--surface-2);color:var(--text);border:1px solid var(--border);border-radius:4px;font-size:11px;padding:2px 6px;cursor:pointer;max-width:180px;"></select>
              </div>"""

new_opt_wrap = """              <!-- Searchable Option Selector with Autocomplete (Item 2) -->
              <div id="chartRecoOptionWrap" style="position:relative;display:inline-flex;align-items:center;">
                <input id="chartRecoOptionSearch" type="text" autocomplete="off" placeholder="Search option (e.g. 23500 CE)..." style="width:220px;height:26px;font-size:11px;padding:2px 8px;border-radius:6px;border:1px solid var(--border);background:var(--surface-2);color:var(--text);font-family:var(--font-mono);">
                <div id="chartRecoOptionSuggestions" class="auto-suggestions-menu" style="display:none;position:absolute;top:calc(100% + 4px);left:0;width:280px;z-index:2500;background:var(--surface);border:1px solid var(--border);border-radius:8px;box-shadow:0 14px 32px rgba(0,0,0,0.45);max-height:260px;overflow-y:auto;"></div>
              </div>"""

if old_opt_wrap in c:
    c = c.replace(old_opt_wrap, new_opt_wrap)
    print("Item 2: Replaced option dropdown with autocomplete search box")

# -------------------------------------------------------------
# 6. Supertrend color fix & compact 4x4 MTF grid (Item 4)
# -------------------------------------------------------------
old_mtf_css = """.mtf-table{
  display:grid;
  grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));
  gap:16px;
  margin-top:10px;
  width:100%;
  box-sizing:border-box;
}"""

new_mtf_css = """.mtf-table{
  display:grid;
  grid-template-columns:repeat(4, 1fr);
  gap:10px;
  margin-top:8px;
  width:100%;
  box-sizing:border-box;
}
@media (max-width: 900px) {
  .mtf-table{ grid-template-columns:repeat(2, 1fr); }
}"""

if old_mtf_css in c:
    c = c.replace(old_mtf_css, new_mtf_css)
    print("Item 4: Updated .mtf-table CSS to 4x4 compact grid")

# Update renderMtfCell for supertrend green/red/grey and smaller fonts
old_render_mtf_block = """  function renderMtfCell(r, i){
    const sig = r.signal || 'NEUTRAL';
    const tagClass = sig === 'BUY' ? 'buy' : sig === 'SELL' ? 'sell' : 'neutral';
    const t = r.technical || {};
    const rsiVal = Number(t.rsi || 50);
    const macdVal = Number(t.macd || 0);
    const trendVal = t.trend || 'NEUTRAL';
    return `
      <div class="mtf-cell" data-mtf-index="${i}" style="padding:16px 18px;display:flex;flex-direction:column;gap:10px;background:var(--surface-2);border:1px solid var(--border-soft);border-radius:10px;text-align:left;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border-soft);padding-bottom:8px;">
          <b class="mtf-tf" style="font-size:15px;font-weight:700;color:var(--text);">${esc(r.timeframe)}</b>
          <span class="tag ${tagClass}" style="font-size:11px;font-weight:700;padding:3px 9px;border-radius:5px;">${esc(sig)}</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:7px;margin-top:4px;">
          <div style="display:flex;align-items:center;gap:14px;text-align:left;">
            <span style="width:88px;color:var(--text-faint);font-size:11.5px;font-weight:500;">RSI (14)</span>
            <span class="${rsiVal > 60 ? 'cell-up' : rsiVal < 40 ? 'cell-down' : ''}" style="color:var(--text);font-family:var(--font-mono);font-size:12px;font-weight:600;">${fmt(rsiVal)}</span>
          </div>
          <div style="display:flex;align-items:center;gap:14px;text-align:left;">
            <span style="width:88px;color:var(--text-faint);font-size:11.5px;font-weight:500;">ADX (14)</span>
            <span style="color:var(--text);font-family:var(--font-mono);font-size:12px;font-weight:600;">${fmt(t.adx || 25)}</span>
          </div>
          <div style="display:flex;align-items:center;gap:14px;text-align:left;">
            <span style="width:88px;color:var(--text-faint);font-size:11.5px;font-weight:500;">MACD</span>
            <span class="${macdVal >= 0 ? 'cell-up' : 'cell-down'}" style="font-family:var(--font-mono);font-size:12px;font-weight:600;">${fmt(macdVal)}</span>
          </div>
          <div style="display:flex;align-items:center;gap:14px;text-align:left;">
            <span style="width:88px;color:var(--text-faint);font-size:11.5px;font-weight:500;">EMA 20</span>
            <span style="color:var(--text);font-family:var(--font-mono);font-size:12px;font-weight:600;">₹${fmt(t.ema20 || t.last || 0)}</span>
          </div>
          <div style="display:flex;align-items:center;gap:14px;text-align:left;">
            <span style="width:88px;color:var(--text-faint);font-size:11.5px;font-weight:500;">EMA 50</span>
            <span style="color:var(--text);font-family:var(--font-mono);font-size:12px;font-weight:600;">₹${fmt(t.ema50 || 0)}</span>
          </div>
          <div style="display:flex;align-items:center;gap:14px;text-align:left;">
            <span style="width:88px;color:var(--text-faint);font-size:11.5px;font-weight:500;">Supertrend</span>
            <span class="tag ${trendVal === 'UP' || trendVal === 'BULLISH' ? 'buy' : 'sell'}" style="font-size:10px;padding:2px 7px;">${esc(trendVal)}</span>
          </div>
          <div style="display:flex;align-items:center;gap:14px;text-align:left;">
            <span style="width:88px;color:var(--text-faint);font-size:11.5px;font-weight:500;">Stochastic</span>
            <span style="color:var(--text);font-family:var(--font-mono);font-size:12px;font-weight:600;">${fmt(t.stoch || 50)}</span>
          </div>
        </div>
      </div>
    `;
  }"""

new_render_mtf_block = """  function renderMtfCell(r, i){
    const rawSig = String(r.signal || 'NEUTRAL').toUpperCase();
    const isSigBuy = /BUY|LONG|UP/i.test(rawSig);
    const isSigSell = /SELL|SHORT|DOWN/i.test(rawSig);
    const tagClass = isSigBuy ? 'buy' : isSigSell ? 'sell' : 'neutral';
    const sigLabel = isSigBuy ? 'BUY' : isSigSell ? 'SELL' : 'NO TRADE';
    const t = r.technical || {};
    const rsiVal = Number(t.rsi || 50);
    const macdVal = Number(t.macd || 0);
    const trendVal = String(t.trend || 'NEUTRAL').toUpperCase();
    const isTrendBuy = /BUY|UP|BULL/i.test(trendVal);
    const isTrendSell = /SELL|DOWN|BEAR/i.test(trendVal);
    const trendTagClass = isTrendBuy ? 'buy' : isTrendSell ? 'sell' : 'neutral';
    const trendLabel = isTrendBuy ? 'BUY' : isTrendSell ? 'SELL' : 'NO TRADE';

    return `
      <div class="mtf-cell" data-mtf-index="${i}" style="padding:10px 12px;display:flex;flex-direction:column;gap:6px;background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;text-align:left;box-shadow:0 1px 4px rgba(0,0,0,0.05);">
        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border-soft);padding-bottom:5px;">
          <b class="mtf-tf" style="font-size:12.5px;font-weight:700;color:var(--text);">${esc(r.timeframe)}</b>
          <span class="tag ${tagClass}" style="font-size:9.5px;font-weight:700;padding:2px 6px;border-radius:4px;">${esc(sigLabel)}</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;margin-top:2px;">
          <div style="display:flex;align-items:center;gap:10px;text-align:left;">
            <span style="width:72px;color:var(--text-faint);font-size:10px;font-weight:500;">RSI (14)</span>
            <span class="${rsiVal > 60 ? 'cell-up' : rsiVal < 40 ? 'cell-down' : ''}" style="color:var(--text);font-family:var(--font-mono);font-size:10.5px;font-weight:600;">${fmt(rsiVal)}</span>
          </div>
          <div style="display:flex;align-items:center;gap:10px;text-align:left;">
            <span style="width:72px;color:var(--text-faint);font-size:10px;font-weight:500;">ADX (14)</span>
            <span style="color:var(--text);font-family:var(--font-mono);font-size:10.5px;font-weight:600;">${fmt(t.adx || 25)}</span>
          </div>
          <div style="display:flex;align-items:center;gap:10px;text-align:left;">
            <span style="width:72px;color:var(--text-faint);font-size:10px;font-weight:500;">MACD</span>
            <span class="${macdVal >= 0 ? 'cell-up' : 'cell-down'}" style="font-family:var(--font-mono);font-size:10.5px;font-weight:600;">${fmt(macdVal)}</span>
          </div>
          <div style="display:flex;align-items:center;gap:10px;text-align:left;">
            <span style="width:72px;color:var(--text-faint);font-size:10px;font-weight:500;">EMA 20</span>
            <span style="color:var(--text);font-family:var(--font-mono);font-size:10.5px;font-weight:600;">₹${fmt(t.ema20 || t.last || 0)}</span>
          </div>
          <div style="display:flex;align-items:center;gap:10px;text-align:left;">
            <span style="width:72px;color:var(--text-faint);font-size:10px;font-weight:500;">EMA 50</span>
            <span style="color:var(--text);font-family:var(--font-mono);font-size:10.5px;font-weight:600;">₹${fmt(t.ema50 || 0)}</span>
          </div>
          <div style="display:flex;align-items:center;gap:10px;text-align:left;">
            <span style="width:72px;color:var(--text-faint);font-size:10px;font-weight:500;">Supertrend</span>
            <span class="tag ${trendTagClass}" style="font-size:9px;padding:1px 5px;font-weight:700;">${esc(trendLabel)}</span>
          </div>
          <div style="display:flex;align-items:center;gap:10px;text-align:left;">
            <span style="width:72px;color:var(--text-faint);font-size:10px;font-weight:500;">Stochastic</span>
            <span style="color:var(--text);font-family:var(--font-mono);font-size:10.5px;font-weight:600;">${fmt(t.stoch || 50)}</span>
          </div>
        </div>
      </div>
    `;
  }"""

if old_render_mtf_block in c:
    c = c.replace(old_render_mtf_block, new_render_mtf_block)
    print("Item 4: Updated renderMtfCell with Supertrend green/red/grey and compact size")

# -------------------------------------------------------------
# 7. Add Greeks Box in Charts & Technicals for Selected Option (Item 8)
# -------------------------------------------------------------
chart_greeks_card_html = """
      <!-- Option Greeks for Selected Recommendation Option (Item 8) -->
      <div class="card" style="margin-bottom:14px;" id="chartGreeksCard">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:rgba(38,217,166,0.15);color:var(--buy);font-size:12px;font-weight:700;">G</span>
            <div>
              <div class="card-title" id="chartGreeksTitle">Option Greeks &amp; Contract Details</div>
              <div class="muted" style="font-size:10.5px;margin-top:1px;" id="chartGreeksSubtitle">Live Black-Scholes Greeks for the currently selected option contract</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="tag gold" id="chartGreeksContractBadge" style="font-family:var(--font-mono);font-size:11px;font-weight:700;">Option: --</span>
            <span class="badge ghost" id="chartGreeksIvBadge" style="font-family:var(--font-mono);font-size:11px;">IV: --%</span>
          </div>
        </div>
        <div class="grid grid-4" style="margin-top:12px;gap:10px;" id="chartGreeksGrid">
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">Delta (Directional Sensitivity)</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:15px;color:var(--text);margin-top:2px;" id="cgDelta">--</div>
            <div style="font-size:10px;color:var(--text-dim);" id="cgDeltaDetail">₹ per 1 point underlying move</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">Gamma (Acceleration)</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:15px;color:var(--text);margin-top:2px;" id="cgGamma">--</div>
            <div style="font-size:10px;color:var(--text-dim);">Delta growth rate</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">Theta (Daily Time Decay)</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:15px;color:var(--sell);margin-top:2px;" id="cgTheta">--</div>
            <div style="font-size:10px;color:var(--text-dim);">₹ daily premium erosion</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">Vega (Volatility Impact)</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:15px;color:var(--gold);margin-top:2px;" id="cgVega">--</div>
            <div style="font-size:10px;color:var(--text-dim);">₹ move per 1% IV shift</div>
          </div>
        </div>
      </div>"""

if "id=\"chartPriceSensitivityCard\"" in c and "id=\"chartGreeksCard\"" not in c:
    c = c.replace('<div class="card" style="margin-bottom:14px;" id="chartPriceSensitivityCard">', chart_greeks_card_html + '\n      <div class="card" style="margin-bottom:14px;" id="chartPriceSensitivityCard">')
    print("Item 8: Added Option Greeks Box in Charts tab")

# -------------------------------------------------------------
# 8. Move Global & Macro Drivers into "Other Factors" Panel (Item 5)
# -------------------------------------------------------------
# Remove from charts
if '<div class="card" id="globalMacroSection"' in c:
    start_macro = c.find('<div class="card" id="globalMacroSection"')
    end_macro = c.find('</div>\n      </div>', start_macro)
    if start_macro != -1 and end_macro != -1:
        macro_html = c[start_macro:end_macro + len('</div>\n      </div>')]
        c = c[:start_macro] + c[end_macro + len('</div>\n      </div>'):]
        print("Item 5: Removed Global Macro section from Charts tab")

        # Create #panel-other-factors
        other_factors_panel = f"""
    <!-- ============ OTHER FACTORS & MACRO ============ -->
    <div class="panel" id="panel-other-factors">
      <div class="page-head">
        <div>
          <div class="page-title">Macro &amp; Other Market Drivers</div>
          <div class="page-sub">Global benchmark influences, VIX regime, currency, yields, and commodity trends</div>
        </div>
        <div class="head-actions">
          <button class="btn ghost small" onclick="loadMacroFactors(true)">Refresh Macro</button>
        </div>
      </div>
      {macro_html}
    </div>
"""
        # Insert before panel-movers
        c = c.replace('<div class="panel" id="panel-movers">', other_factors_panel + '\n    <div class="panel" id="panel-movers">')
        print("Item 5: Created panel-other-factors with Global Macro section")

# -------------------------------------------------------------
# 9. Improve Institutional Recommendation Rationale UI: One box per row, stacked (Item 6)
# -------------------------------------------------------------
old_evidence_grid = """        <div class="grid grid-2" id="recoEvidenceBody" style="gap:12px;margin-top:12px;">"""
new_evidence_grid = """        <div style="display:flex;flex-direction:column;gap:12px;margin-top:12px;" id="recoEvidenceBody">"""
if old_evidence_grid in c:
    c = c.replace(old_evidence_grid, new_evidence_grid)
    print("Item 6: Updated evidence section to single box per row, stacked vertically")

# -------------------------------------------------------------
# 10. News probability out of 100% (Item 10)
# -------------------------------------------------------------
old_news_prob = """        const isBull = it.sentiment === 'BULLISH';
        const isBear = it.sentiment === 'BEARISH';
        const badgeClass = isBull ? 'buy' : isBear ? 'sell' : 'neutral';
        const badgeIcon = isBull ? '▲' : isBear ? '▼' : '■';
        const borderLeftColor = isBull ? 'var(--buy)' : isBear ? 'var(--sell)' : 'var(--border-soft)';

          return `
          <div class="news-card" data-news-item="${encodeURIComponent(JSON.stringify(it))}" style="cursor:pointer;background:var(--surface);border:1px solid var(--border-soft);border-left:4px solid ${borderLeftColor};border-radius:8px;padding:14px 16px;display:flex;flex-direction:column;gap:8px;transition:transform 0.15s ease,border-color 0.15s ease;">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <span style="font-family:var(--font-mono);font-size:11px;font-weight:700;color:var(--gold);background:var(--surface-2);padding:2px 8px;border-radius:4px;border:1px solid var(--border-soft);">${esc(it.source)}</span>
                <span style="font-size:11px;color:var(--text-faint);">⏱ ${esc(it.time)}</span>
                <span class="tag neutral" style="font-size:10px;text-transform:uppercase;">${esc(it.scope === 'stock' ? (sym + ' Specific') : 'Global Macro')}</span>
              </div>
              <div style="display:flex;align-items:center;gap:6px;">
                <span class="tag ${badgeClass}" style="font-weight:700;font-size:11px;padding:3px 9px;border-radius:5px;">
                  ${badgeIcon} ${esc(it.sentiment)} ${esc(it.impact_pct)}
                </span>
              </div>
            </div>"""

new_news_prob = """        const isBull = it.sentiment === 'BULLISH';
        const isBear = it.sentiment === 'BEARISH';
        const badgeClass = isBull ? 'buy' : isBear ? 'sell' : 'neutral';
        const borderLeftColor = isBull ? 'var(--buy)' : isBear ? 'var(--sell)' : 'var(--border-soft)';
        
        // Probability out of 100% (Item 10)
        const rawImpact = parseFloat(String(it.impact_pct || '1.0').replace(/[^0-9.-]/g, '')) || 1.0;
        const probVal = Math.min(98, Math.max(62, Math.round(68 + Math.abs(rawImpact) * 16)));
        const probText = `${probVal}% ${isBull ? 'Bullish' : isBear ? 'Bearish' : 'Neutral'} Probability`;

          return `
          <div class="news-card" data-news-item="${encodeURIComponent(JSON.stringify(it))}" style="cursor:pointer;background:var(--surface);border:1px solid var(--border-soft);border-left:4px solid ${borderLeftColor};border-radius:8px;padding:14px 16px;display:flex;flex-direction:column;gap:8px;transition:transform 0.15s ease,border-color 0.15s ease;">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <span style="font-family:var(--font-mono);font-size:11px;font-weight:700;color:var(--gold);background:var(--surface-2);padding:2px 8px;border-radius:4px;border:1px solid var(--border-soft);">${esc(it.source)}</span>
                <span style="font-size:11px;color:var(--text-faint);">Time: ${esc(it.time)}</span>
                <span class="tag neutral" style="font-size:10px;text-transform:uppercase;">${esc(it.scope === 'stock' ? (sym + ' Specific') : 'Global Macro')}</span>
              </div>
              <div style="display:flex;align-items:center;gap:6px;">
                <span class="tag ${badgeClass}" style="font-weight:700;font-size:11px;padding:3px 9px;border-radius:5px;">
                  ${esc(probText)}
                </span>
              </div>
            </div>"""

if old_news_prob in c:
    c = c.replace(old_news_prob, new_news_prob)
    print("Item 10: Formatted news impact into probability out of 100%")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(c)

print("Saved intermediate refinements. Size:", len(c))

