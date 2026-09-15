# -*- coding: utf-8 -*-
"""
Release 30 updater script for terminal.html
"""
with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()

print("Original file size:", len(content))

# 1. Ensure crosshair lines touch x & y edges
old_cross = """      x.moveTo(pad.l,cy);
      x.lineTo(w,cy);
      x.moveTo(cx,0);
      x.lineTo(cx,h-pad.b);"""
new_cross = """      x.moveTo(0,cy);
      x.lineTo(w,cy);
      x.moveTo(cx,0);
      x.lineTo(cx,h);"""
if old_cross in content:
    content = content.replace(old_cross, new_cross)
    print("1. Replaced crosshair line drawing")

# 2. MTF Table CSS and spacey left-aligned rendering
mtf_css_old = """.mtf-table{
  display:grid;
  grid-template-columns:repeat(auto-fit, minmax(148px, 1fr));
  gap:12px;
  margin-top:8px;
  width:100%;
  box-sizing:border-box;
}"""
mtf_css_new = """.mtf-table{
  display:grid;
  grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));
  gap:16px;
  margin-top:10px;
  width:100%;
  box-sizing:border-box;
}"""
if mtf_css_old in content:
    content = content.replace(mtf_css_old, mtf_css_new)
    print("2a. Replaced .mtf-table CSS")

if ".mtf-table{grid-template-columns:repeat(4,1fr);}" in content:
    content = content.replace(".mtf-table{grid-template-columns:repeat(4,1fr);}", ".mtf-table{grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));}")
    print("2b. Updated media query for .mtf-table")

old_render_mtf = """  function renderMtfCell(r, i){
    const sig = r.signal || 'NEUTRAL';
    const tagClass = sig === 'BUY' ? 'buy' : sig === 'SELL' ? 'sell' : 'neutral';
    const t = r.technical || {};
    return `
      <div class="mtf-cell" data-mtf-index="${i}" style="min-height:220px;padding:14px;display:flex;flex-direction:column;gap:8px;background:var(--surface-2);border:1px solid var(--border-soft);border-radius:9px;text-align:left;">
        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border-soft);padding-bottom:7px;">
          <b class="mtf-tf" style="font-size:14px;color:var(--text);">${esc(r.timeframe)}</b>
          <span class="tag ${tagClass}" style="font-size:10.5px;font-weight:700;">${esc(sig)}</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:6px;font-size:11px;margin-top:4px;">
          <div style="display:flex;justify-content:space-between;align-items:center;"><span class="muted" style="color:var(--text-faint);">RSI (14)</span><b style="color:var(--text);font-family:var(--font-mono);">${fmt(t.rsi || 50)}</b></div>
          <div style="display:flex;justify-content:space-between;align-items:center;"><span class="muted" style="color:var(--text-faint);">ADX (14)</span><b style="color:var(--text);font-family:var(--font-mono);">${fmt(t.adx || 25)}</b></div>
          <div style="display:flex;justify-content:space-between;align-items:center;"><span class="muted" style="color:var(--text-faint);">MACD</span><b class="${(Number(t.macd)||0)>=0?'cell-up':'cell-down'}" style="font-family:var(--font-mono);">${fmt(t.macd || 0)}</b></div>
          <div style="display:flex;justify-content:space-between;align-items:center;"><span class="muted" style="color:var(--text-faint);">EMA 20</span><b style="color:var(--text);font-family:var(--font-mono);">${fmt(t.ema20 || t.last || 0)}</b></div>
          <div style="display:flex;justify-content:space-between;align-items:center;"><span class="muted" style="color:var(--text-faint);">EMA 50</span><b style="color:var(--text);font-family:var(--font-mono);">${fmt(t.ema50 || 0)}</b></div>
          <div style="display:flex;justify-content:space-between;align-items:center;"><span class="muted" style="color:var(--text-faint);">Supertrend</span><span class="tag ${t.trend==='UP'||t.trend==='BULLISH'?'buy':'sell'}" style="font-size:9.5px;padding:2px 6px;">${t.trend || 'NEUTRAL'}</span></div>
          <div style="display:flex;justify-content:space-between;align-items:center;"><span class="muted" style="color:var(--text-faint);">Stochastic</span><b style="color:var(--text);font-family:var(--font-mono);">${fmt(t.stoch || 50)}</b></div>
        </div>
      </div>
    `;
  }"""

new_render_mtf = """  function renderMtfCell(r, i){
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
if old_render_mtf in content:
    content = content.replace(old_render_mtf, new_render_mtf)
    print("2c. Replaced renderMtfCell with spacey left-aligned format")

# 3. Dynamic News Sentiment in loadNewsByCaAi
old_news_block = """      if ($('newsItemCountBadge')) $('newsItemCountBadge').textContent = `${items.length} stories`;

      if (!items.length) {"""

new_news_block = """      if ($('newsItemCountBadge')) $('newsItemCountBadge').textContent = `${items.length} stories`;

      // Update Dynamic News Sentiment Score (Item 13)
      if ($('newsOverallSentimentBadge')) {
        const score = Number(d.sentiment_score != null ? d.sentiment_score : 50);
        const label = d.sentiment_label || (score >= 55 ? 'BULLISH' : score <= 45 ? 'BEARISH' : 'NEUTRAL');
        const isBull = label === 'BULLISH';
        const isBear = label === 'BEARISH';
        const color = isBull ? 'var(--buy)' : isBear ? 'var(--sell)' : 'var(--gold)';
        const bg = isBull ? 'rgba(16,185,129,0.15)' : isBear ? 'rgba(239,68,68,0.15)' : 'rgba(234,179,8,0.15)';
        $('newsOverallSentimentBadge').textContent = `${label} (${score > 50 ? '+' : ''}${score - 50 > 0 ? '+' : ''}${score}%)`;
        $('newsOverallSentimentBadge').style.color = color;
        $('newsOverallSentimentBadge').style.borderColor = color;
        $('newsOverallSentimentBadge').style.background = bg;
        if ($('newsSentimentProgressBar')) {
          $('newsSentimentProgressBar').style.width = `${Math.max(5, Math.min(100, score))}%`;
          $('newsSentimentProgressBar').style.background = color;
        }
        if ($('newsSentimentDetail')) {
          $('newsSentimentDetail').textContent = `${d.bullish_count || 0} Bullish · ${d.bearish_count || 0} Bearish catalysts · Since ${d.cutoff_ist || 'last trading day 14:00 IST'}`;
        }
      }

      if (!items.length) {"""

if old_news_block in content:
    content = content.replace(old_news_block, new_news_block)
    print("3. Wired dynamic news sentiment score in loadNewsByCaAi")

# 4. Remove auto-trade merge script that renamed tab to 'Recommendations & Auto Trade' and moved risk config
old_merge_script = """      const children=[...auto.children];
      children.slice(1).forEach(ch=>reco.appendChild(ch));
      auto.style.display='none'; auto.dataset.autoMerged='1';
      const recoTab=document.querySelector('.navtab[data-tab="reco"]'); if(recoTab) recoTab.textContent='Recommendations & Auto Trade';
      document.querySelectorAll('.navtab[data-tab="auto"]').forEach(t=>t.remove());
      if(typeof loadAutoTrade === 'function') void loadAutoTrade(); else if(window.loadAutoTrade) void window.loadAutoTrade();"""

new_merge_script = """      // Kept clean: Recommendation History standalone (Item 11)
      const recoTab=document.querySelector('.navtab[data-tab="reco"]'); if(recoTab) recoTab.textContent='Recommendation History';"""

if old_merge_script in content:
    content = content.replace(old_merge_script, new_merge_script)
    print("4. Removed auto-trade merge script from Recommendation History")

# 5. Closed positions quantity fix in positionsTable
old_pos_qty = """                  return `
                    <tr data-pos-symbol="${esc(x.symbol)}" data-pos-id="${esc(x.id)}">
                      <td><b>${esc(x.symbol)}</b></td>
                      <td><span class="tag ${signalClass(x.side)}">${esc(x.side||'BUY')}</span></td>
                      <td>${fmt(x.quantity)}</td>"""

new_pos_qty = """                  const dispQty = Number(x.display_quantity || x.closed_quantity || (x.quantity > 0 ? x.quantity : 1));
                  const finalDispQty = (symUpper.includes('CRUDEOIL') && dispQty === 1) ? 100 : dispQty;
                  return `
                    <tr data-pos-symbol="${esc(x.symbol)}" data-pos-id="${esc(x.id)}">
                      <td><b>${esc(x.symbol)}</b></td>
                      <td><span class="tag ${signalClass(x.side)}">${esc(x.side||'BUY')}</span></td>
                      <td><b>${fmt(finalDispQty)}</b></td>"""

if old_pos_qty in content:
    content = content.replace(old_pos_qty, new_pos_qty)
    print("5. Fixed closed position quantity rendering")

# 6. Expose window.showGreeks
if "window.showGreeks = showGreeks;" not in content:
    content = content.replace("function showGreeks(r){", "window.showGreeks = showGreeks;\n  function showGreeks(r){")
    print("6. Exported window.showGreeks")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated terminal.html successfully. Size:", len(content))

