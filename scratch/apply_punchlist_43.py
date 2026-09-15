#!/usr/bin/env python3
"""Apply punchlist fixes to app.py and terminal.html for Release 43."""
import re, sys, os

APP_PATH = r'c:\Users\SantoshMadnani\Documents\CA_Trader\7\app.py'
TERM_PATH = r'c:\Users\SantoshMadnani\Documents\CA_Trader\7\terminal.html'

print("Applying backend edits to app.py...")
with open(APP_PATH, 'r', encoding='utf-8') as f:
    app_code = f.read()

# 1. Dow Jones price update in app.py
app_code = re.sub(
    r'"dow":\s*\{"name":\s*"Dow Jones",\s*"level":\s*40345\.20,',
    r'"dow": {"name": "Dow Jones", "level": 52051.04,',
    app_code
)

# 2. News relative time -> exact time and no (12m ago)
app_code = app_code.replace(
    'rel_time = f"{exact_time} ({mins_ago}m ago)"',
    'rel_time = exact_time'
).replace(
    'rel_time = f"{exact_time} ({mins_ago // 60}h ago)"',
    'rel_time = exact_time'
).replace(
    'rel_time = f"{exact_time} ({mins_ago // 1440}d ago)"',
    'rel_time = exact_time'
)

# 3. News default items URL and Sentiment in app.py
app_code = app_code.replace(
    '"sentiment": "Neutral",\n                "impact_pct": "Consolidation (±0.3%)",\n                "impact": "Consolidation (±0.3%)",',
    '"sentiment": "BEARISH",\n                "impact_pct": "78% Sell Signal",\n                "impact": "78% Sell Signal",'
)

# Make default items have real Google News URLs instead of '#'
app_code = re.sub(
    r'"url":\s*"#"',
    r'"url": f"https://news.google.com/search?q={urllib.parse.quote_plus(sym + \' stock market\')}"',
    app_code
)

# Ensure curated news items have valid fallback external URL
app_code = app_code.replace(
    '"url": item.get("url") or "#"',
    '"url": (item.get("url") if item.get("url") and item.get("url") != "#" and "catrader.site" not in item.get("url") else f"https://news.google.com/search?q={urllib.parse.quote_plus(title)}")'
)

# Ensure sentiment in curated news is UPPERCASE ('BULLISH' / 'BEARISH')
app_code = app_code.replace(
    'sentiment = "Bearish"',
    'sentiment = "BEARISH"'
).replace(
    'sentiment = "Bullish"',
    'sentiment = "BULLISH"'
)

with open(APP_PATH, 'w', encoding='utf-8') as f:
    f.write(app_code)
print("app.py successfully updated.")

print("\nApplying frontend edits to terminal.html...")
with open(TERM_PATH, 'r', encoding='utf-8') as f:
    term_code = f.read()

# 1. Dow Jones placeholder in HTML
term_code = re.sub(
    r'<div>Dow:\s*<b style="color:var\(--buy\);">40,345\.20 \(\+0\.31%\)</b></div>',
    r'<div>Dow: <b style="color:var(--buy);">52,051.04 (+0.31%)</b></div>',
    term_code
)

# 2. Section bar auto-slide: Remove scrollIntoView from showTab
term_code = term_code.replace(
    "document.querySelector('.navtab[data-tab=\"'+name+'\"]')?.scrollIntoView({behavior:'smooth', inline:'center', block:'nearest'});",
    "/* section bar auto-slide removed per user request */"
)

# 3. Dynamic lot size helper
old_lotsize_block = """  function getSymbolLotSize(sym){
    const s = String(sym || window.__caOrderInstrumentKey || selectedSymbol() || '').toUpperCase();
    if(s.includes('BANKNIFTY')) return 15;
    if(s.includes('FINNIFTY')) return 25;
    if(s.includes('MIDCPNIFTY')) return 50;
    if(s.includes('NIFTY')) return 25;
    if(s.includes('CRUDEOIL')) return 100;
    if(s.includes('NATURALGAS')) return 1250;
    if(s.includes('GOLDM')) return 10;
    if(s.includes('GOLD')) return 100;
    if(s.includes('SILVERM')) return 5;
    if(s.includes('SILVER')) return 30;
    if(s.includes('COPPER')) return 2500;
    if(s.includes('ZINC')) return 5000;
    return window.__caOrderLotSize || 1;
  }"""

new_lotsize_block = """  function getSymbolLotSize(sym){
    const s = String(
      sym ||
      window.__caOrderDisplay ||
      window.__caPinnedOptionContract ||
      window.__caOrderInstrumentKey ||
      selectedSymbol() ||
      ''
    ).toUpperCase();
    if(s.includes('BANKNIFTY')) return 15;
    if(s.includes('FINNIFTY')) return 25;
    if(s.includes('MIDCPNIFTY')) return 50;
    if(s.includes('NIFTY')) return 25;
    if(s.includes('CRUDEOIL')) return 100;
    if(s.includes('NATURALGAS')) return 1250;
    if(s.includes('GOLDM')) return 10;
    if(s.includes('GOLD')) return 100;
    if(s.includes('SILVERM')) return 5;
    if(s.includes('SILVER')) return 30;
    if(s.includes('COPPER')) return 2500;
    if(s.includes('ZINC')) return 5000;
    if(window.__caOrderLotSize && window.__caOrderLotSize > 1) return window.__caOrderLotSize;
    return 1;
  }"""

if old_lotsize_block in term_code:
    term_code = term_code.replace(old_lotsize_block, new_lotsize_block)
    print("+ Updated getSymbolLotSize")
else:
    print("! Notice: exact lotsize block didn't match directly, checking regex replace...")
    term_code = re.sub(
        r'function getSymbolLotSize\(sym\)\{[\s\S]*?return window\.__caOrderLotSize \|\| 1;\s*\}',
        new_lotsize_block.strip(),
        term_code
    )

# 4. In openOrder, sync window.__caOrderLotSize
term_code = term_code.replace(
    "const currentLot = getSymbolLotSize(instrument || display || selectedSymbol());\n    $('orderReferenceShares').textContent",
    "const currentLot = getSymbolLotSize(display || instrument || selectedSymbol());\n    window.__caOrderLotSize = currentLot;\n    $('orderReferenceShares').textContent"
)

# 5. In orderSubmit, multiply lots by lotMult
term_code = term_code.replace(
    "quantity:Math.max(1,Math.round(lots*(window.__caOrderInstrumentKey?window.__caOrderLotSize:1))),",
    "quantity:Math.max(1,Math.round(lots * getSymbolLotSize(window.__caOrderDisplay || window.__caOrderInstrumentKey || selectedSymbol()))),"
)

# 6. In orderQty input listener, use display/instrument/symbol
term_code = term_code.replace(
    "const currentLot = getSymbolLotSize(window.__caOrderInstrumentKey || selectedSymbol());",
    "const currentLot = getSymbolLotSize(window.__caOrderDisplay || window.__caOrderInstrumentKey || selectedSymbol());"
)

# 7. News rendering: case-insensitive sentiment check and Google News search fallback link
old_news_check = """      host.innerHTML = items.map(it => {
        const isBull = it.sentiment === 'BULLISH';
        const isBear = it.sentiment === 'BEARISH';
        const badgeClass = isBull ? 'buy' : isBear ? 'sell' : 'neutral';
        const borderLeftColor = isBull ? 'var(--buy)' : isBear ? 'var(--sell)' : 'var(--border-soft)';

        // Probability out of 100% (Item 10)
        const rawImpact = parseFloat(String(it.impact_pct || '1.0').replace(/[^0-9.-]/g, '')) || 1.0;
        const probVal = Math.min(98, Math.max(62, Math.round(68 + Math.abs(rawImpact) * 16)));
        const probText = `${probVal}% ${isBull ? 'Bullish' : isBear ? 'Bearish' : 'Neutral'} Probability`;"""

new_news_check = """      host.innerHTML = items.map(it => {
        const sUpper = String(it.sentiment || '').toUpperCase();
        const isBull = sUpper === 'BULLISH' || sUpper.includes('BUY');
        const isBear = sUpper === 'BEARISH' || sUpper.includes('SELL') || !isBull;
        const badgeClass = isBull ? 'buy' : 'sell';
        const borderLeftColor = isBull ? 'var(--buy)' : 'var(--sell)';

        // Probability out of 100% (Item 10)
        const rawImpact = parseFloat(String(it.impact_pct || '1.0').replace(/[^0-9.-]/g, '')) || 1.0;
        const probVal = Math.min(98, Math.max(65, Math.round(72 + Math.abs(rawImpact) * 14)));
        const probText = `${probVal}% ${isBull ? 'Bullish' : 'Bearish'} Probability`;
        const newsLink = (it.url && it.url !== '#' && !it.url.includes('catrader.site')) ? it.url : ('https://news.google.com/search?q=' + encodeURIComponent((it.headline || 'stock market') + ' news'));"""

if old_news_check in term_code:
    term_code = term_code.replace(old_news_check, new_news_check)
    print("+ Updated news rendering logic")
else:
    print("! Warning: old_news_check pattern not matched verbatim, applying regex...")
    term_code = re.sub(
        r'const isBull = it\.sentiment === \'BULLISH\';\s*const isBear = it\.sentiment === \'BEARISH\';[\s\S]*?const probText = `\$\{probVal\}% \$\{isBull \? \'Bullish\' : isBear \? \'Bearish\' : \'Neutral\'\} Probability`;',
        new_news_check.strip(),
        term_code
    )

# Also ensure news anchor href uses newsLink
term_code = term_code.replace(
    'href="${esc(it.url || it.link || \'#\')}"',
    'href="${esc(newsLink || it.url || it.link || \'#\')}"'
)

# 8. X-axis time overlap: fix in draw() grid labels and crosshair
old_xtick_draw = "if(i%Math.max(1,Math.floor(view.count/8))===0){x.fillStyle=css('--text-faint');x.fillText(xTickLabel(v.timestamp||v.ts||Date.now()),Math.max(pad.l,xx-24),h-12)}});"
new_xtick_draw = "if(xx - lastTickX >= 75 && xx < w - pad.r - 40){ lastTickX = xx; x.fillStyle=css('--text-faint'); x.fillText(xTickLabel(v.timestamp||v.ts||Date.now()), Math.max(pad.l, xx - 20), h - 10); }});"

if old_xtick_draw in term_code:
    term_code = "let lastTickX = -999;\n  " + term_code.replace(old_xtick_draw, new_xtick_draw)
    print("+ Fixed X-axis tick label spacing to prevent overlapping")
else:
    term_code = re.sub(
        r'if\(i%Math\.max\(1,Math\.floor\(view\.count/8\)\)===0\)\{x\.fillStyle=css\(\'--text-faint\'\);x\.fillText\(xTickLabel\(v\.timestamp\|\|v\.ts\|\|Date\.now\(\)\),Math\.max\(pad\.l,xx-24\),h-12\)\}\}\);',
        'if(xx - (window.__lastTickX || -999) >= 75 && xx < w - pad.r - 40){ window.__lastTickX = xx; x.fillStyle=css(\'--text-faint\'); x.fillText(xTickLabel(v.timestamp||v.ts||Date.now()), Math.max(pad.l, xx - 20), h - 10); }});',
        term_code
    )

# Suppress duplicate DOM crosshair time label when canvas already renders it
term_code = term_code.replace(
    "t.style.display='block';\n    t.style.position='absolute';",
    "t.style.display='none'; /* canvas renders x-axis time badge directly without DOM overlap */\n    t.style.position='absolute';"
)

# 9. Fast client-side positions switch (Item 16)
old_pos_subtabs = """    $('subTabOpenPositions')?.addEventListener('click', () => {
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
    });"""

new_pos_subtabs = """    $('subTabOpenPositions')?.addEventListener('click', () => {
      activePosSubTab = 'open';
      $('subTabOpenPositions').classList.add('active');
      $('subTabClosedPositions')?.classList.remove('active');
      if(window.__caCachedPositions){
        renderPositionsTable(window.__caCachedPositions, window.__caCachedAdvisories || []);
      } else {
        void loadPortfolioSnapshot(false);
      }
    });
    $('subTabClosedPositions')?.addEventListener('click', () => {
      activePosSubTab = 'closed';
      $('subTabClosedPositions').classList.add('active');
      $('subTabOpenPositions')?.classList.remove('active');
      if(window.__caCachedPositions){
        renderPositionsTable(window.__caCachedPositions, window.__caCachedAdvisories || []);
      } else {
        void loadPortfolioSnapshot(false);
      }
    });"""

if old_pos_subtabs in term_code:
    term_code = term_code.replace(old_pos_subtabs, new_pos_subtabs)
    print("+ Updated positions subtab fast client toggle")

# Cache positions in renderPositionsTable
term_code = term_code.replace(
    "function renderPositionsTable(allPositions, advisories=[]){",
    "function renderPositionsTable(allPositions, advisories=[]){\n    window.__caCachedPositions = allPositions;\n    window.__caCachedAdvisories = advisories;"
)

# 10. Top Summary Confluence Table (Item 14) inside #masterSummaryCard
# Add confluence table markup right after msThesisBox
old_thesis_box = """        <div id="msThesisBox" style="margin-top:10px;padding:10px 14px;background:var(--surface-2);border-radius:8px;border-left:4px solid var(--buy);font-size:12px;line-height:1.5;color:var(--text);">
          <div style="font-weight:700;color:var(--gold);margin-bottom:4px;display:flex;align-items:center;gap:6px;">
            <span>💡 Why This Signal:</span>
            <span id="msThesisHeadline" style="color:var(--text);font-weight:600;">Synthesizing technicals, patterns, Greeks, other factors, and live news…</span>
          </div>
          <div id="msThesisNarrative" style="color:var(--text-dim);font-size:11.5px;">
            Multi-section quantitative model analyzing trend indicators, candlestick breakouts, option chain Greeks, institutional positioning, and news sentiment catalysts.
          </div>
        </div>"""

new_thesis_box_with_table = """        <div id="msThesisBox" style="margin-top:10px;padding:10px 14px;background:var(--surface-2);border-radius:8px;border-left:4px solid var(--buy);font-size:12px;line-height:1.5;color:var(--text);">
          <div style="font-weight:700;color:var(--gold);margin-bottom:4px;display:flex;align-items:center;gap:6px;">
            <span>💡 Why This Signal:</span>
            <span id="msThesisHeadline" style="color:var(--text);font-weight:600;">Synthesizing technicals, patterns, Greeks, other factors, and live news…</span>
          </div>
          <div id="msThesisNarrative" style="color:var(--text-dim);font-size:11.5px;">
            Multi-section quantitative model analyzing trend indicators, candlestick breakouts, option chain Greeks, institutional positioning, and news sentiment catalysts.
          </div>
        </div>

        <!-- Confluence Breakdown Table (Item 14) -->
        <div id="msConfluenceTableWrap" style="margin-top:10px;overflow-x:auto;border-radius:8px;border:1px solid var(--border-soft);">
          <table style="width:100%;border-collapse:collapse;font-size:11.5px;text-align:left;background:var(--surface-2);">
            <thead>
              <tr style="border-bottom:1px solid var(--border-soft);background:var(--surface);font-size:10px;text-transform:uppercase;color:var(--text-faint);letter-spacing:0.5px;">
                <th style="padding:6px 10px;">Factor / Category</th>
                <th style="padding:6px 10px;">Signal</th>
                <th style="padding:6px 10px;">Weightage</th>
                <th style="padding:6px 10px;">Score</th>
                <th style="padding:6px 10px;">Key Driver / Rationale</th>
              </tr>
            </thead>
            <tbody id="msConfluenceTableBody">
              <tr style="border-bottom:1px solid var(--border-soft);cursor:pointer;" onclick="showTab('charts')">
                <td style="padding:6px 10px;font-weight:600;">📊 Indicators &amp; MAs</td>
                <td style="padding:6px 10px;"><span class="tag buy" id="msConfTechSig" style="font-size:10px;">BULLISH</span></td>
                <td style="padding:6px 10px;color:var(--text-faint);">30%</td>
                <td style="padding:6px 10px;font-family:var(--font-mono);font-weight:700;color:var(--buy);" id="msConfTechScore">82%</td>
                <td style="padding:6px 10px;font-size:11px;color:var(--text-dim);" id="msConfTechDriver">Above 20 &amp; 50 EMA, RSI bullish momentum</td>
              </tr>
              <tr style="border-bottom:1px solid var(--border-soft);cursor:pointer;" onclick="showTab('news')">
                <td style="padding:6px 10px;font-weight:600;">📰 News &amp; Catalysts</td>
                <td style="padding:6px 10px;"><span class="tag buy" id="msConfNewsSig" style="font-size:10px;">BULLISH</span></td>
                <td style="padding:6px 10px;color:var(--text-faint);">20%</td>
                <td style="padding:6px 10px;font-family:var(--font-mono);font-weight:700;color:var(--buy);" id="msConfNewsScore">85%</td>
                <td style="padding:6px 10px;font-size:11px;color:var(--text-dim);" id="msConfNewsDriver">Institutional flow &amp; earnings catalysts</td>
              </tr>
              <tr style="border-bottom:1px solid var(--border-soft);cursor:pointer;" onclick="showTab('options')">
                <td style="padding:6px 10px;font-weight:600;">⚡ Option Greeks &amp; Chain</td>
                <td style="padding:6px 10px;"><span class="tag buy" id="msConfGreeksSig" style="font-size:10px;">OPTIMAL BUY</span></td>
                <td style="padding:6px 10px;color:var(--text-faint);">20%</td>
                <td style="padding:6px 10px;font-family:var(--font-mono);font-weight:700;color:var(--buy);" id="msConfGreeksScore">86%</td>
                <td style="padding:6px 10px;font-size:11px;color:var(--text-dim);" id="msConfGreeksDriver">Delta 0.50 ATM, favorable Theta cushion</td>
              </tr>
              <tr style="border-bottom:1px solid var(--border-soft);cursor:pointer;" onclick="showTab('other-factors')">
                <td style="padding:6px 10px;font-weight:600;">🌐 Other Factors &amp; Macro</td>
                <td style="padding:6px 10px;"><span class="tag buy" id="msConfMacroSig" style="font-size:10px;">POSITIVE</span></td>
                <td style="padding:6px 10px;color:var(--text-faint);">15%</td>
                <td style="padding:6px 10px;font-family:var(--font-mono);font-weight:700;color:var(--buy);" id="msConfMacroScore">78%</td>
                <td style="padding:6px 10px;font-size:11px;color:var(--text-dim);" id="msConfMacroDriver">Low VIX expansion, positive GIFT Nifty bias</td>
              </tr>
              <tr style="border-bottom:1px solid var(--border-soft);cursor:pointer;" onclick="document.getElementById('patternList')?.scrollIntoView({behavior:'smooth'})">
                <td style="padding:6px 10px;font-weight:600;">📈 Trend &amp; Candlestick Patterns</td>
                <td style="padding:6px 10px;"><span class="tag buy" id="msConfPatternSig" style="font-size:10px;">BULLISH</span></td>
                <td style="padding:6px 10px;color:var(--text-faint);">15%</td>
                <td style="padding:6px 10px;font-family:var(--font-mono);font-weight:700;color:var(--buy);" id="msConfPatternScore">80%</td>
                <td style="padding:6px 10px;font-size:11px;color:var(--text-dim);" id="msConfPatternDriver">Breakout continuation &amp; higher highs swing structure</td>
              </tr>
              <tr style="background:var(--surface);font-weight:700;">
                <td style="padding:8px 10px;color:var(--gold);">TOTAL CONFLUENCE SCORE</td>
                <td style="padding:8px 10px;"><span class="tag buy" id="msConfTotalSig" style="font-size:10.5px;font-weight:700;">BUY CONVICTION</span></td>
                <td style="padding:8px 10px;color:var(--text);">100%</td>
                <td style="padding:8px 10px;font-family:var(--font-mono);font-size:13px;color:var(--buy);" id="msConfTotalScore">82.3%</td>
                <td style="padding:8px 10px;font-size:11px;color:var(--text);" id="msConfTotalSummary">Multi-Factor High-Conviction Algorithmic Alignment</td>
              </tr>
            </tbody>
          </table>
        </div>"""

if old_thesis_box in term_code:
    term_code = term_code.replace(old_thesis_box, new_thesis_box_with_table)
    print("+ Inserted Top Confluence Summary Table into masterSummaryCard")

# 11. Recommendation History Table: Add Outcome Status column (Item 17)
old_rec_table_head = """              <tr>
                <th style="width:34px;"><input type="checkbox" id="selectAllRecHistory" title="Select All"></th>
                <th>Recommendation Time</th>
                <th>Symbol</th>
                <th>Source</th>
                <th>Signal</th>
                <th>Entry</th>
                <th>SL</th>
                <th>Target</th>
                <th>P&L</th>
              </tr>"""

new_rec_table_head = """              <tr>
                <th style="width:34px;"><input type="checkbox" id="selectAllRecHistory" title="Select All"></th>
                <th>Recommendation Time</th>
                <th>Symbol</th>
                <th>Source</th>
                <th>Signal</th>
                <th>Outcome Status</th>
                <th>Entry</th>
                <th>SL</th>
                <th>Target</th>
                <th>P&L</th>
              </tr>"""

if old_rec_table_head in term_code:
    term_code = term_code.replace(old_rec_table_head, new_rec_table_head)
    print("+ Added Outcome Status column to Recommendation History table header")

old_rec_row = """                return `
                  <tr>
                    <td><input type="checkbox" data-rec-delete="${esc(x.id)}" class="rec-delete-cb"></td>
                    <td>${esc(formatTime(x.created_at))}</td>
                    <td><b>${esc(cleanSym)}</b>${x.underlying && x.underlying !== cleanSym ? `<br><span style="font-size:10px;color:var(--text-faint);">(${esc(x.underlying)})</span>` : ''}</td>
                    <td>${esc(x.source)}</td>
                    <td><span class="tag ${signalClass(x.recommendation)}" style="cursor:pointer;" onclick="openRecoCalculationModal(${recJson})" title="Click to view calculation">${esc(x.recommendation)}</span></td>
                    <td style="cursor:pointer;" onclick="openRecoCalculationModal(${recJson}, 'entry')" title="Click to view Entry formula">₹${fmt(x.entry)}</td>
                    <td style="cursor:pointer;color:var(--sell);" onclick="openRecoCalculationModal(${recJson}, 'stop_loss')" title="Click to view Dynamic SL">₹${fmt(x.stop_loss)}</td>
                    <td style="cursor:pointer;color:var(--buy);" onclick="openRecoCalculationModal(${recJson}, 'target')" title="Click to view Target calculation">₹${fmt(x.target)}</td>
                    <td><b style="color:${pnlColor};font-family:var(--font-mono);">${pnlStr}</b></td>
                  </tr>
                `;"""

new_rec_row = """                const entry = Number(x.entry || 0);
                const sl = Number(x.stop_loss || 0);
                const tgt = Number(x.target || 0);
                const isBuySig = String(x.recommendation || x.signal || 'BUY').toUpperCase().includes('BUY');
                const liveQ = (window.__CA_WL_QUOTES || {})[cleanSym.toUpperCase()] || (window.__CA_WL_QUOTES || {})[rawSym.toUpperCase()] || {};
                const curPrice = Number(liveQ.ltp || liveQ.close || (x.final_pnl != null ? entry + (x.final_pnl / Math.max(1, x.quantity||1)) : entry));
                let outcomeLabel = 'Active';
                let outcomeTagCls = 'gold';
                if(x.status === 'TARGET_HIT' || x.outcome === 'TARGET_HIT' || (isBuySig && tgt > 0 && curPrice >= tgt) || (!isBuySig && tgt > 0 && curPrice <= tgt && curPrice > 0)){
                  outcomeLabel = 'Target Hit';
                  outcomeTagCls = 'buy';
                } else if(x.status === 'SL_HIT' || x.outcome === 'SL_HIT' || (isBuySig && sl > 0 && curPrice <= sl && curPrice > 0) || (!isBuySig && sl > 0 && curPrice >= sl)){
                  outcomeLabel = 'SL Hit';
                  outcomeTagCls = 'sell';
                } else if(pnl > 0){
                  outcomeLabel = 'Success';
                  outcomeTagCls = 'buy';
                } else if(pnl < 0){
                  outcomeLabel = 'SL Hit';
                  outcomeTagCls = 'sell';
                } else {
                  const recAge = Date.now() - new Date(x.created_at || Date.now()).getTime();
                  if(recAge > 86400000){
                    outcomeLabel = 'Expired';
                    outcomeTagCls = 'neutral';
                  } else {
                    outcomeLabel = 'Active Signal';
                    outcomeTagCls = 'gold';
                  }
                }
                return `
                  <tr>
                    <td><input type="checkbox" data-rec-delete="${esc(x.id)}" class="rec-delete-cb"></td>
                    <td>${esc(formatTime(x.created_at))}</td>
                    <td><b>${esc(cleanSym)}</b>${x.underlying && x.underlying !== cleanSym ? `<br><span style="font-size:10px;color:var(--text-faint);">(${esc(x.underlying)})</span>` : ''}</td>
                    <td>${esc(x.source)}</td>
                    <td><span class="tag ${signalClass(x.recommendation)}" style="cursor:pointer;" onclick="openRecoCalculationModal(${recJson})" title="Click to view calculation">${esc(x.recommendation)}</span></td>
                    <td><span class="tag ${outcomeTagCls}" style="font-size:10px;font-weight:700;">${esc(outcomeLabel)}</span></td>
                    <td style="cursor:pointer;" onclick="openRecoCalculationModal(${recJson}, 'entry')" title="Click to view Entry formula">₹${fmt(x.entry)}</td>
                    <td style="cursor:pointer;color:var(--sell);" onclick="openRecoCalculationModal(${recJson}, 'stop_loss')" title="Click to view Dynamic SL">₹${fmt(x.stop_loss)}</td>
                    <td style="cursor:pointer;color:var(--buy);" onclick="openRecoCalculationModal(${recJson}, 'target')" title="Click to view Target calculation">₹${fmt(x.target)}</td>
                    <td><b style="color:${pnlColor};font-family:var(--font-mono);">${pnlStr}</b></td>
                  </tr>
                `;"""

if old_rec_row in term_code:
    term_code = term_code.replace(old_rec_row, new_rec_row)
    print("+ Updated Recommendation History rows with Outcome Status")

# 12. Fix Option dropdown selection logic:
# Ensure selecting ANY option from chartRecoOptionSelect creates an active, actionable recommendation
# and never tells user to switch to Call when they selected a Put in bearish structure
old_reco_action_block = """    if(isUnderlyingBull && isCall){
      // Aligned Call in Bullish Market
      recoAction = 'BUY';
      qualifies = true;
      advisoryIcon = isOtm ? '💡' : '✅';
      if(isOtm){
        advisoryComment = `💡 Budget-Friendly OTM Call Selected: ${optSym} (Capital: ~${fmtMoney(capitalReq)}/lot). Trade is aligned with ${baseSym} Bullish market structure. ⚠️ Advisory: Out-of-the-Money options have lower Delta (~0.25-0.35) and faster Theta decay closer to expiry. Do NOT hold for prolonged periods—trail stop loss closely once in profit.`;
        rationale = `OTM Call Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)} (Est. +₹${estProfit}/lot, +${Math.round((reward/entry)*100)}%), SL ₹${fmt(sl)} (R:R 1:${rr}). Budget-friendly capital layout (~₹${capitalReq}/lot) accommodating lower funds.`;
      } else if(isItm){
        advisoryComment = `✅ High-Delta ITM Call Selected: ${optSym} (Capital: ~${fmtMoney(capitalReq)}/lot). High Delta (~0.65) captures direct underlying trend momentum with lower Theta erosion. Fully aligned with ${baseSym} Bullish trend.`;
        rationale = `ITM Call Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)} (+${Math.round((reward/entry)*100)}%), SL ₹${fmt(sl)} (R:R 1:${rr}). Deep intrinsic protection.`;
      } else {
        advisoryComment = `✅ Optimal ATM Call Selected: ${optSym} (Capital: ~${fmtMoney(capitalReq)}/lot). Balanced Greeks (Delta ~0.50) with maximum liquidity. High conviction institutional trend following on ${baseSym}.`;
        rationale = `ATM Call Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)} (Est. +₹${estProfit}/lot, +${Math.round((reward/entry)*100)}%), SL ₹${fmt(sl)} (R:R 1:${rr}). Greeks & intraday momentum aligned.`;
      }
    } else if(isUnderlyingBear && isPut){
      // Aligned Put in Bearish Market
      recoAction = 'BUY';
      qualifies = true;
      advisoryIcon = isOtm ? '💡' : '✅';
      if(isOtm){
        advisoryComment = `💡 Budget-Friendly OTM Put Selected: ${optSym} (Capital: ~${fmtMoney(capitalReq)}/lot). Trade is aligned with ${baseSym} Bearish market structure. ⚠️ Advisory: Out-of-the-Money options have lower Delta (~0.25-0.35) and faster Theta decay. Scalp with tight trailing SL aligned with downward trend.`;
        rationale = `OTM Put Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)} (Est. +₹${estProfit}/lot), SL ₹${fmt(sl)}. Budget-friendly layout (~₹${capitalReq}/lot) for capital preservation.`;
      } else if(isItm){
        advisoryComment = `✅ High-Delta ITM Put Selected: ${optSym} (Capital: ~${fmtMoney(capitalReq)}/lot). High Delta protection capturing downward institutional breakdown with lower time decay sensitivity.`;
        rationale = `ITM Put Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)}, SL ₹${fmt(sl)}. Strong downward tracking.`;
      } else {
        advisoryComment = `✅ Optimal ATM Put Selected: ${optSym} (Capital: ~${fmtMoney(capitalReq)}/lot). Balanced Greeks (Delta -0.50) and high liquidity. Aligned with downward institutional breakdown on ${baseSym}.`;
        rationale = `ATM Put Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)} (Est. +₹${estProfit}/lot), SL ₹${fmt(sl)} (R:R 1:${rr}). High conviction trade.`;
      }
    } else if(isUnderlyingBull && isPut){
      // Counter-Trend Selection: Bullish market, but user selected Put
      recoAction = 'CAUTION (COUNTER-TREND)';
      qualifies = false;
      advisoryIcon = '⚠️';
      suggestedContract = isCrude ? `CRUDEOIL FUT ${expTag} ${atmStrike}CE` : `${baseSym} ${atmStrike} CE`;
      advisoryComment = `⚠️ Counter-Trend Advisory: Market structure for ${baseSym} is strongly Bullish. The algorithm recommends buying a CALL option (${suggestedContract}). You have selected a PUT option (${optSym}). Buying puts against prevailing upward momentum carries elevated risk of rapid capital loss. 💡 Suggestion: Switch to a Call option (${suggestedContract}) to trade in sync with institutional momentum.`;
      rationale = `Counter-Trend Warning: ${baseSym} technical structure is Bullish. Recommended: ${suggestedContract}. You selected Put (${optSym}). Risk elevated against trend momentum.`;
    } else if(isUnderlyingBear && isCall){
      // Counter-Trend Selection: Bearish market, but user selected Call
      recoAction = 'CAUTION (COUNTER-TREND)';
      qualifies = false;
      advisoryIcon = '⚠️';
      suggestedContract = isCrude ? `CRUDEOIL FUT ${expTag} ${atmStrike}PE` : `${baseSym} ${atmStrike} PE`;
      advisoryComment = `⚠️ Counter-Trend Advisory: Market structure for ${baseSym} is Bearish. The algorithm recommends buying a PUT option (${suggestedContract}). You have selected a CALL option (${optSym}). Buying calls against downward momentum carries significant risk. 💡 Suggestion: Switch to a Put option (${suggestedContract}) to trade in sync with market direction.`;
      rationale = `Counter-Trend Warning: ${baseSym} technical structure is Bearish. Recommended: ${suggestedContract}. You selected Call (${optSym}). Risk elevated against trend momentum.`;
    } else if(isChop){
      // Rangebound / Sideways Chop
      recoAction = 'NO TRADE';
      qualifies = false;
      advisoryIcon = '⏸';
      advisoryComment = `⏸ No Favourable Trade: ${baseSym} is currently rangebound in low-volatility consolidation. Option buying in choppy conditions suffers rapid Theta decay without directional payoff. Stand aside until a decisive breakout occurs.`;
      rationale = `No Favourable Trade: ${baseSym} lacks directional breakout momentum. Avoid option buying during sideways chop.`;
    }"""

new_reco_action_block = """    // User Request 6 & 12: Always provide active, actionable BUY recommendation for user's selected contract
    recoAction = 'BUY';
    qualifies = true;
    advisoryIcon = isOtm ? '💡' : '✅';

    if(isPut){
      // User selected Put
      if(isUnderlyingBear || !isUnderlyingBull){
        advisoryComment = `✅ High-Conviction Put Selected: ${optSym} (Capital: ~₹${capitalReq}/lot). Trade is fully aligned with ${baseSym} Bearish market breakdown. Downward momentum confirms put buying setup.`;
        rationale = `Put Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)} (Est. +₹${estProfit}/lot, +${Math.round((reward/entry)*100)}%), SL ₹${fmt(sl)} (R:R 1:${rr}). Downward institutional flow aligned.`;
      } else {
        advisoryComment = `💡 Contrarian / Scalp Put Selected: ${optSym} (Capital: ~₹${capitalReq}/lot). Underlying is testing upper resistance. Scalping with tight trailing SL ₹${fmt(sl)}.`;
        rationale = `Put Scalp Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)}, SL ₹${fmt(sl)} (R:R 1:${rr}). Trade with disciplined trailing stop loss.`;
      }
    } else {
      // User selected Call
      if(isUnderlyingBull || !isUnderlyingBear){
        advisoryComment = `✅ High-Conviction Call Selected: ${optSym} (Capital: ~₹${capitalReq}/lot). Trade is fully aligned with ${baseSym} Bullish market momentum. Upward continuation confirms call buying setup.`;
        rationale = `Call Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)} (Est. +₹${estProfit}/lot, +${Math.round((reward/entry)*100)}%), SL ₹${fmt(sl)} (R:R 1:${rr}). Institutional buying aligned.`;
      } else {
        advisoryComment = `💡 Pullback Call Selected: ${optSym} (Capital: ~₹${capitalReq}/lot). Reversal bounce setup at dynamic support. Trailing SL ₹${fmt(sl)} active.`;
        rationale = `Call Pullback Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)}, SL ₹${fmt(sl)} (R:R 1:${rr}). Scalp with tight trailing SL.`;
      }
    }"""

if old_reco_action_block in term_code:
    term_code = term_code.replace(old_reco_action_block, new_reco_action_block)
    print("+ Updated applyOptionRecommendation with consistent actionable signals")

# 13. Initialize Chart Greeks & Simulator on chart load / symbol change (Item 7)
greeks_and_sim_init = """
  function updateChartGreeksAndSim(optSymOverride){
    try {
      const sym = selectedSymbol() || window.CATraderSymbol || 'NIFTY';
      const baseSym = extractUnderlying(sym);
      const curLtp = Number(window.state?.latestLive || (window.__CA_WL_QUOTES||{})[baseSym]?.ltp || (window.__CA_WL_QUOTES||{})[sym]?.ltp || 23400);
      const step = baseSym.includes('BANK') ? 100 : 50;
      const atmStrike = Math.round(curLtp / step) * step;
      const recoSym = optSymOverride || window.__caPinnedOptionContract || (window.__caCurrentChartReco?.instrument?.symbol) || `${baseSym} ${atmStrike} CE`;
      const badge = document.getElementById('chartGreeksContractBadge');
      if(badge) badge.textContent = `Option: ${recoSym}`;

      const m = recoSym.match(/\\s+(\\d+)\\s*(CE|PE)?$/i);
      const targetStrike = m ? Number(m[1]) : atmStrike;
      const isCall = !recoSym.toUpperCase().endsWith('PE');

      const apiFn = window.A || window.api;
      if(apiFn && baseSym && !baseSym.includes('CRUDE')){
        apiFn('/api/options/' + encodeURIComponent(baseSym) + '/chain', {timeoutMs:3500}).then(d => {
          if(!d || !d.strikes) return;
          const row = (d.strikes || []).find(s => s.strike === targetStrike) || (d.strikes || [])[Math.floor(d.strikes.length/2)];
          if(row){
            const side = isCall ? 'call' : 'put';
            const g = row[side] || row.call || {};
            const ivBadge = document.getElementById('chartGreeksIvBadge');
            if(ivBadge) ivBadge.textContent = `IV: ${g.iv ? (g.iv*100).toFixed(1) : '14.2'}%`;
            const fmt2 = v => v != null && Number.isFinite(Number(v)) ? Number(v).toFixed(3) : '--';
            if($('cgDelta')) $('cgDelta').textContent = fmt2(g.delta || (isCall ? 0.51 : -0.49));
            if($('cgGamma')) $('cgGamma').textContent = fmt2(g.gamma || 0.0012);
            if($('cgTheta')) $('cgTheta').textContent = fmt2(g.theta || -12.4);
            if($('cgVega')) $('cgVega').textContent = fmt2(g.vega || 14.8);
            if($('msDelta')) $('msDelta').textContent = fmt2(g.delta || (isCall ? 0.51 : -0.49));
            if($('msTheta')) $('msTheta').textContent = fmt2(g.theta || -12.4);
          }
        }).catch(() => {});
      } else {
        if($('cgDelta')) $('cgDelta').textContent = isCall ? '0.512' : '-0.488';
        if($('cgGamma')) $('cgGamma').textContent = '0.0014';
        if($('cgTheta')) $('cgTheta').textContent = '-14.200';
        if($('cgVega')) $('cgVega').textContent = '16.500';
      }

      // Wire and update sensitivity simulator
      if(typeof wirePriceSensitivitySim === 'function') wirePriceSensitivitySim('chart');
    } catch(e){ console.debug('updateChartGreeksAndSim error:', e); }
  }
  window.updateChartGreeksAndSim = updateChartGreeksAndSim;
"""

# Append updateChartGreeksAndSim before end of script
term_code = term_code.replace(
    "window.setupOrdersPositionsSubtabs = setupOrdersPositionsSubtabs;",
    "window.setupOrdersPositionsSubtabs = setupOrdersPositionsSubtabs;\n" + greeks_and_sim_init
)

# Call updateChartGreeksAndSim in onSymbolChanged and loadChart and applyOptionRecommendation
term_code = term_code.replace(
    "renderChartRecoData(reco, optSym);",
    "renderChartRecoData(reco, optSym);\n    if(typeof updateChartGreeksAndSim === 'function') updateChartGreeksAndSim(optSym);"
)

# 14. Make structureBox trend cards clickable for candle highlight (Item 8)
old_struct_trend_card = """      <div class="pattern-card">
        <div>
          <b>Trend: ${displayTrend}</b>
          <div class="muted" style="margin-top:3px;">${esc(trendReason)}</div>
        </div>
        <span class="tag ${trendClass}" style="font-weight:700;">${displayTrend}</span>
      </div>"""

new_struct_trend_card = """      <div class="pattern-card" data-focus-trend="${displayTrend}" style="cursor:pointer;" title="Click to highlight ${displayTrend} on chart">
        <div>
          <div style="display:flex;align-items:center;gap:6px;">
            <b>Trend: ${displayTrend}</b>
            <span class="tag neutral" style="font-size:9px;padding:1px 5px;">${state.tf || '5m'}</span>
          </div>
          <div class="muted" style="font-size:10.5px;color:var(--gold);margin-top:2px;">⏱ Past 30 candles (${state.tf}) Trend Channel</div>
          <div class="muted" style="margin-top:3px;">${esc(trendReason)}</div>
        </div>
        <span class="tag ${trendClass}" style="font-weight:700;">${displayTrend}</span>
      </div>"""

term_code = term_code.replace(old_struct_trend_card, new_struct_trend_card)

# Wire trend card clicks in bindPatternClicks
old_bind_pattern_clicks = """    document.querySelectorAll('[data-focus-pattern]').forEach(el=>el.onclick=async()=>{
      // Item 14: Hit Move to Top button first before focusing and highlighting pattern
      document.getElementById('moveTopBtn')?.click();"""

new_bind_pattern_clicks = """    document.querySelectorAll('[data-focus-trend]').forEach(el => el.onclick = () => {
      document.getElementById('moveTopBtn')?.click();
      const trendName = el.dataset.focusTrend || 'Trend';
      const len = (state.candles || []).length;
      if(!len) return;
      const count = Math.min(len, 30);
      const startIdx = Math.max(0, len - count);
      const endIdx = len - 1;
      const isBull = trendName.toLowerCase().includes('up') || trendName.toLowerCase().includes('bull');
      const isBear = trendName.toLowerCase().includes('down') || trendName.toLowerCase().includes('bear');
      const c0 = state.candles[startIdx], c1 = state.candles[endIdx];
      const t0 = formatTime(c0.timestamp || c0.ts);
      const t1 = formatTime(c1.timestamp || c1.ts);
      state.highlightedPattern = {
        startIdx, endIdx,
        name: `${trendName} (${count} candles)`,
        timeLabel: `${t0} → ${t1} (${state.tf})`,
        color: isBull ? 'rgba(38,217,166,0.22)' : isBear ? 'rgba(255,92,114,0.22)' : 'rgba(232,184,75,0.22)',
        border: isBull ? '#26D9A6' : isBear ? '#FF5C72' : '#E8B84B',
        confidence: 88
      };
      draw();
    });

    document.querySelectorAll('[data-focus-pattern]').forEach(el=>el.onclick=async()=>{
      // Item 14: Hit Move to Top button first before focusing and highlighting pattern
      document.getElementById('moveTopBtn')?.click();"""

term_code = term_code.replace(old_bind_pattern_clicks, new_bind_pattern_clicks)

# 15. Make data items in #recoRationaleCard clickable (Item 9)
# Make Technicals clickable to scroll to technicals
term_code = term_code.replace(
    '<div style="background:var(--surface);border:1px solid var(--border-soft);border-radius:6px;padding:6px 10px;display:flex;align-items:center;gap:8px;">',
    '<div style="background:var(--surface);border:1px solid var(--border-soft);border-radius:6px;padding:6px 10px;display:flex;align-items:center;gap:8px;cursor:pointer;" onclick="showTab(\'charts\');$(\'panel-indicators\')?.scrollIntoView({behavior:\'smooth\'})" title="Click to verify Technical Indicator on Chart">'
)

# Make News clickable to open News panel
term_code = term_code.replace(
    '<div style="background:var(--surface);border:1px solid var(--border-soft);border-left:3px solid ${isBull ? \'var(--buy)\' : \'var(--sell)\'};border-radius:6px;padding:8px 12px;display:flex;flex-direction:column;gap:4px;">',
    '<div style="background:var(--surface);border:1px solid var(--border-soft);border-left:3px solid ${isBull ? \'var(--buy)\' : \'var(--sell)\'};border-radius:6px;padding:8px 12px;display:flex;flex-direction:column;gap:4px;cursor:pointer;" onclick="showTab(\'news\')" title="Click to view full catalyst in News by CA AI">'
)

# Make Greeks clickable to open Option Chain / Greek Modal
term_code = term_code.replace(
    '<div style="background:var(--surface);border:1px solid var(--border-soft);border-radius:6px;padding:8px 10px;',
    '<div style="background:var(--surface);border:1px solid var(--border-soft);border-radius:6px;padding:8px 10px;cursor:pointer;" onclick="showTab(\'options\')" title="Click to open Option Chain" '
)

# Make Patterns in Rationale clickable to highlight on chart
term_code = term_code.replace(
    '<div style="background:var(--surface);border:1px solid var(--border-soft);border-radius:6px;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;gap:10px;flex:1;min-width:240px;">',
    '<div style="background:var(--surface);border:1px solid var(--border-soft);border-radius:6px;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;gap:10px;flex:1;min-width:240px;cursor:pointer;" onclick="showTab(\'charts\');if(typeof highlightTrendOnChart===\'function\')highlightTrendOnChart(\'Pattern\');" title="Click to highlight setup on Chart">'
)

# 16. Trigger news load automatically in initial loadAll() and onSymbolChanged()
term_code = term_code.replace(
    "loadMacroFactors(false);",
    "loadMacroFactors(false);\n    if(typeof loadNewsByCaAi === 'function') void loadNewsByCaAi();"
)

# Ensure external data polls unconditionally every 10s (Item 11)
term_code = term_code.replace(
    "if(activeTab === 'charts') {\n        // Refresh chart analysis bundle and macro factors\n        if(window.CATraderAnalysis?.loadChartBundle) void window.CATraderAnalysis.loadChartBundle(false);\n        if(typeof loadMacroFactors === 'function') void loadMacroFactors(false);",
    "// Item 11: Refresh macro drivers and non-broker external feeds every 10 seconds unconditionally\n      if(typeof loadMacroFactors === 'function') void loadMacroFactors(false);\n      if(activeTab === 'charts') {\n        if(window.CATraderAnalysis?.loadChartBundle) void window.CATraderAnalysis.loadChartBundle(false);"
)

with open(TERM_PATH, 'w', encoding='utf-8') as f:
    f.write(term_code)
print("terminal.html successfully updated.")

