# -*- coding: utf-8 -*-
"""Comprehensive and surgical script to apply all Release 45 updates to terminal.html."""
import re
from pathlib import Path

path = Path("terminal.html")
code = path.read_text(encoding="utf-8")
orig_len = len(code)
print(f"Original terminal.html length: {orig_len:,} bytes")

# 1. Topbar userDisplayName default to 'Santosh' (Item 20)
code = code.replace('<div class="name" id="userDisplayName">—</div>', '<div class="name" id="userDisplayName">Santosh</div>', 1)
print("1. Set userDisplayName to Santosh")

# 2. Add CSS for .wl-r-btn, compact inputs, and badges
r_btn_css = """
  /* Auto-Reco 'R' button (Item 10) */
  .wl-r-btn {
    border: 1px solid var(--border-soft);
    background: var(--surface-2);
    color: var(--text-faint);
    font-size: 10px;
    font-weight: 800;
    width: 20px;
    height: 20px;
    border-radius: 4px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s;
    margin-right: 4px;
  }
  .wl-r-btn:hover {
    border-color: #00f0ff;
    color: #00f0ff;
  }
  .wl-r-btn.active {
    color: #00f0ff !important;
    text-shadow: 0 0 8px rgba(0, 240, 255, 0.8) !important;
    border-color: #00f0ff !important;
    background: rgba(0, 240, 255, 0.12) !important;
    box-shadow: 0 0 6px rgba(0, 240, 255, 0.3) !important;
  }
  /* Compact date pickers (Item 7 & 22) */
  .compact-date-input {
    width: 110px !important;
    max-width: 120px !important;
    font-size: 11px !important;
    padding: 2px 6px !important;
    height: 26px !important;
    border-radius: 4px !important;
    border: 1px solid var(--border-soft) !important;
    background: var(--surface-2) !important;
    color: var(--text) !important;
    font-family: var(--font-sans) !important;
  }
"""
code = code.replace("</style>", r_btn_css + "\n</style>", 1)
print("2. Added CSS")

# 3. Remove green advisory callout box (Item 1)
adv_match = re.search(r'<!--[^>]*Dynamic Advisory Callout Box -->\s*<div id="chartRecoAdvisoryBox"[\s\S]*?</div>\s*<div class="muted" id="chartRecoRationale"', code)
if adv_match:
    code = code[:adv_match.start()] + '<div class="muted" id="chartRecoRationale"' + code[adv_match.end():]
    print("3. Removed green advisory callout box")
else:
    print("3. Warning: chartRecoAdvisoryBox not found")

# 4. Remove popup clicks on Entry, SL, Target pills (Item 5)
code = code.replace('class="stat-pill clickable-calc" id="chartRecoEntryPill" title="Click to inspect Entry calculation proof" style="cursor:pointer;', 'class="stat-pill" id="chartRecoEntryPill" style="cursor:default;', 1)
code = code.replace('class="stat-pill clickable-calc" id="chartRecoSlPill" title="Click to inspect Stop Loss calculation proof" style="cursor:pointer;', 'class="stat-pill" id="chartRecoSlPill" style="cursor:default;', 1)
code = code.replace('class="stat-pill clickable-calc" id="chartRecoTgtPill" title="Click to inspect Target calculation proof" style="cursor:pointer;', 'class="stat-pill" id="chartRecoTgtPill" style="cursor:default;', 1)
print("4. Removed popup click styles on Entry, SL, Target pills")

# 5. Insert 3 Dedicated Rationale Cards (Entry, SL, Target) & Auto-Reco strip below Confluence Matrix (Item 5 & 10)
dash_three_cards = """
      <!-- Active Monitored Strategies Strip (Item 10) -->
      <div class="card" id="dashAutoRecoStrip" style="margin-bottom:12px;padding:8px 14px;background:var(--surface);border:1px solid var(--border-soft);border-radius:8px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
        <div style="display:flex;align-items:center;gap:8px;">
          <span class="wl-r-btn active" style="cursor:default;">R</span>
          <b style="font-size:11.5px;color:var(--text);">5-Min Background Auto-Reco Engine:</b>
          <span id="dashAutoRecoStatusText" style="font-size:11px;color:var(--text-dim);">Monitoring watchlist symbols with active 'R' badge</span>
        </div>
        <div id="dashAutoRecoSymbolsList" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
          <span class="tag neutral" style="font-size:10px;">NIFTY</span>
          <span class="tag neutral" style="font-size:10px;">BANKNIFTY</span>
          <span class="tag neutral" style="font-size:10px;">CRUDEOIL</span>
        </div>
      </div>

      <!-- 3 Dedicated Rationale Cards: Entry, Stop Loss, Target (Item 5) -->
      <div class="grid grid-3" style="margin-bottom:14px;gap:12px;" id="dashRationaleThreeCards">
        <!-- Entry Rationale Card -->
        <div class="card" style="padding:14px 16px;background:var(--surface);border:1px solid var(--border);border-top:3px solid var(--primary);border-radius:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <b style="font-size:12px;color:var(--text);text-transform:uppercase;letter-spacing:0.5px;">1. Entry Rationale &amp; Trigger</b>
            <span class="tag buy" id="dashEntryTriggerTag" style="font-size:9.5px;font-weight:700;">BREAKOUT CONFIRMED</span>
          </div>
          <div style="font-family:var(--font-mono);font-size:18px;font-weight:700;color:var(--text);margin-bottom:6px;" id="dashEntryPriceDisplay">₹--</div>
          <div style="font-size:11.5px;line-height:1.5;color:var(--text-dim);" id="dashEntryRationaleText">
            Breakout above dynamic 20-EMA pivot with surge in buyer queue depth and bullish momentum crossover confirmation.
          </div>
        </div>

        <!-- Stop Loss Rationale Card -->
        <div class="card" style="padding:14px 16px;background:var(--surface);border:1px solid var(--border);border-top:3px solid var(--sell);border-radius:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <b style="font-size:12px;color:var(--text);text-transform:uppercase;letter-spacing:0.5px;">2. Stop Loss &amp; Invalidation</b>
            <span class="tag sell" id="dashSlRiskTag" style="font-size:9.5px;font-weight:700;">1.5× ATR DYNAMIC SL</span>
          </div>
          <div style="font-family:var(--font-mono);font-size:18px;font-weight:700;color:var(--sell);margin-bottom:6px;" id="dashSlPriceDisplay">₹--</div>
          <div style="font-size:11.5px;line-height:1.5;color:var(--text-dim);" id="dashSlRationaleText">
            Structural swing support floor anchored at 1.5× ATR. Setup is strictly invalidated upon decisive candle close below this level.
          </div>
        </div>

        <!-- Target Rationale Card -->
        <div class="card" style="padding:14px 16px;background:var(--surface);border:1px solid var(--border);border-top:3px solid var(--buy);border-radius:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <b style="font-size:12px;color:var(--text);text-transform:uppercase;letter-spacing:0.5px;">3. Target &amp; Trailing Plan</b>
            <span class="tag gold" id="dashTargetModeTag" style="font-size:9.5px;font-weight:700;">R : R ≥ 1 : 2.0</span>
          </div>
          <div style="font-family:var(--font-mono);font-size:18px;font-weight:700;color:var(--buy);margin-bottom:6px;" id="dashTargetPriceDisplay">₹--</div>
          <div style="font-size:11.5px;line-height:1.5;color:var(--text-dim);" id="dashTargetRationaleText">
            Fibonacci 1.618 expansion pivot target satisfying institutional minimum ₹500 profit constraint. Trailing SL locks gains upon crossing 50% distance.
          </div>
        </div>
      </div>
"""
greeks_card_anchor = 'id="dashGreeksCard"'
assert greeks_card_anchor in code, "id=dashGreeksCard not found"
code = code.replace('<div class="card" style="margin-bottom:14px;" id="dashGreeksCard">', dash_three_cards + '\n      <div class="card" style="margin-bottom:14px;" id="dashGreeksCard">', 1)
print("5. Added 3 dedicated rationale cards and Auto-Reco strip")

# 6. Price Sensitivity Simulator: replace shell with pure Greeks model (Item 6)
idx_sim = code.find('id="chartPriceSensitivityCard"')
idx_hist = code.find('id="dashHistoryCard"')
assert idx_sim != -1 and idx_hist != -1, "chartPriceSensitivityCard or dashHistoryCard not found"
start_sim = code.rfind('<div class="card"', 0, idx_sim)
start_hist = code.rfind('<div class="card"', 0, idx_hist)

new_sim_markup = """      <!-- Price Sensitivity Simulator (Pure Greeks Model, Independent of CMP/LTP - Item 6) -->
      <div class="card" style="margin-bottom:14px;" id="chartPriceSensitivityCard">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:rgba(232,184,75,0.15);color:var(--gold);font-size:12px;font-weight:700;">⚡</span>
            <div>
              <div class="card-title" id="priceSensitivityTitle">Option Price Sensitivity Simulator (Pure Greeks Model)</div>
              <div class="muted" style="font-size:10.5px;margin-top:1px;">Simulate option premium delta &amp; gamma payoff independent of underlying CMP or option price</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="tag gold" id="chartSimPointsBadge" style="font-family:var(--font-mono);font-size:11px;font-weight:700;">Shift: +0 Points</span>
            <span class="tag buy" id="chartSimNetGainBadge" style="font-family:var(--font-mono);font-size:11px;font-weight:700;">Net Premium: +₹0.00</span>
          </div>
        </div>
        <div style="margin-top:12px;">
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-faint);margin-bottom:4px;">
            <span>0 Points Move</span>
            <span style="font-weight:700;color:var(--gold);" id="chartSimSliderDisplay">+0 Points Underlying Shift</span>
            <span>+100 Points Surge</span>
          </div>
          <input type="range" id="chartSimSlider" min="0" max="100" value="0" step="1" style="width:100%;cursor:pointer;accent-color:var(--buy);">
          
          <div class="grid grid-4" style="margin-top:12px;gap:10px;">
            <div style="background:var(--surface-2);padding:8px 10px;border-radius:6px;border:1px solid var(--border-soft);">
              <div class="label" style="font-size:10px;color:var(--text-faint);text-transform:uppercase;">Delta Impact (Δ × Pts)</div>
              <div class="value" id="chartSimDeltaImpact" style="font-size:14px;font-weight:700;color:var(--buy);font-family:var(--font-mono);margin-top:3px;">+₹0.00</div>
              <div class="muted" style="font-size:9.5px;margin-top:2px;">Linear directional capture (Δ ≈ 0.51)</div>
            </div>
            <div style="background:var(--surface-2);padding:8px 10px;border-radius:6px;border:1px solid var(--border-soft);">
              <div class="label" style="font-size:10px;color:var(--text-faint);text-transform:uppercase;">Gamma Accel (½ × Γ × Pts²)</div>
              <div class="value" id="chartSimGammaImpact" style="font-size:14px;font-weight:700;color:var(--gold);font-family:var(--font-mono);margin-top:3px;">+₹0.00</div>
              <div class="muted" style="font-size:9.5px;margin-top:2px;">Curvature / convexity acceleration</div>
            </div>
            <div style="background:var(--surface-2);padding:8px 10px;border-radius:6px;border:1px solid var(--border-soft);">
              <div class="label" style="font-size:10px;color:var(--text-faint);text-transform:uppercase;">Net Premium Move / Share</div>
              <div class="value" id="chartSimTotalImpact" style="font-size:14px;font-weight:700;color:var(--buy);font-family:var(--font-mono);margin-top:3px;">+₹0.00</div>
              <div class="muted" style="font-size:9.5px;margin-top:2px;">Total estimated contract price delta</div>
            </div>
            <div style="background:var(--surface-2);padding:8px 10px;border-radius:6px;border:1px solid var(--border-soft);">
              <div class="label" style="font-size:10px;color:var(--text-faint);text-transform:uppercase;">Estimated P&amp;L (1 Lot)</div>
              <div class="value" id="chartSimLotPnl" style="font-size:14px;font-weight:700;color:var(--buy);font-family:var(--font-mono);margin-top:3px;">+₹0.00</div>
              <div class="muted" style="font-size:9.5px;margin-top:2px;">Theta: -₹14.20/d · Vega: +₹16.50/IV</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Recommendation History at bottom of Dashboard -->
"""
code = code[:start_sim] + new_sim_markup + code[start_hist:]
print("6. Updated Price Sensitivity Simulator to pure Greeks model")

# 7. Make date filter inputs compact (Item 7)
old_dates = """            <input type="date" id="recoFilterFrom" class="tool-input" style="font-size:11px;padding:2px 6px;">
            <input type="date" id="recoFilterTo" class="tool-input" style="font-size:11px;padding:2px 6px;">"""
new_dates = """            <span style="font-size:11px;color:var(--text-faint);align-self:center;">From:</span>
            <input type="date" id="recoFilterFrom" class="tool-input compact-date-input" title="From Date">
            <span style="font-size:11px;color:var(--text-faint);align-self:center;">To:</span>
            <input type="date" id="recoFilterTo" class="tool-input compact-date-input" title="To Date">"""
assert old_dates in code, "old_dates not found"
code = code.replace(old_dates, new_dates, 1)
print("7. Made date filter inputs compact")

# 8. Add Historical Rationale Modal before </body> (Item 8)
hist_modal_html = """
  <!-- Historical Recommendation Rationale Snapshot Modal (Item 8) -->
  <div id="historicalRationaleModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.65);z-index:9999;align-items:center;justify-content:center;padding:20px;">
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;width:100%;max-width:850px;max-height:85vh;overflow-y:auto;box-shadow:0 20px 50px rgba(0,0,0,0.5);padding:20px;">
      <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border-soft);padding-bottom:12px;margin-bottom:16px;">
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:7px;background:rgba(24,144,255,0.15);color:var(--primary);font-size:14px;font-weight:700;">✦</span>
          <div>
            <b style="font-size:15px;color:var(--text);" id="histModalTitle">Recommendation Rationale Snapshot</b>
            <div style="font-size:11px;color:var(--text-dim);" id="histModalSubtitle">Captured at recommendation issuance time</div>
          </div>
        </div>
        <button type="button" class="btn ghost small" onclick="closeHistoricalRationaleModal()" style="font-size:14px;padding:4px 10px;">✕</button>
      </div>

      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px;">
        <div style="background:var(--surface-2);padding:10px;border-radius:6px;border:1px solid var(--border-soft);">
          <div style="font-size:10px;color:var(--text-faint);text-transform:uppercase;">Signal &amp; Direction</div>
          <div id="histModalSignal" style="font-size:14px;font-weight:700;margin-top:2px;">—</div>
        </div>
        <div style="background:var(--surface-2);padding:10px;border-radius:6px;border:1px solid var(--border-soft);">
          <div style="font-size:10px;color:var(--text-faint);text-transform:uppercase;">Entry Price</div>
          <div id="histModalEntry" style="font-size:14px;font-weight:700;color:var(--text);font-family:var(--font-mono);margin-top:2px;">—</div>
        </div>
        <div style="background:var(--surface-2);padding:10px;border-radius:6px;border:1px solid var(--border-soft);">
          <div style="font-size:10px;color:var(--text-faint);text-transform:uppercase;">Stop Loss</div>
          <div id="histModalSl" style="font-size:14px;font-weight:700;color:var(--sell);font-family:var(--font-mono);margin-top:2px;">—</div>
        </div>
        <div style="background:var(--surface-2);padding:10px;border-radius:6px;border:1px solid var(--border-soft);">
          <div style="font-size:10px;color:var(--text-faint);text-transform:uppercase;">Target (or Trailing)</div>
          <div id="histModalTarget" style="font-size:14px;font-weight:700;color:var(--buy);font-family:var(--font-mono);margin-top:2px;">—</div>
        </div>
      </div>

      <!-- Confluence Table Snapshot -->
      <div class="table-wrap" style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:11.5px;text-align:left;">
          <thead>
            <tr style="border-bottom:1px solid var(--border);background:var(--surface-2);font-size:10px;text-transform:uppercase;color:var(--text-faint);">
              <th style="padding:8px 10px;">Category / Particulars</th>
              <th style="padding:8px 10px;">Recorded Value</th>
              <th style="padding:8px 10px;">Weight</th>
              <th style="padding:8px 10px;">Signal</th>
              <th style="padding:8px 10px;">Relevance &amp; Basis</th>
            </tr>
          </thead>
          <tbody id="histModalTableBody">
            <!-- Populated on Show Rationale click -->
          </tbody>
        </table>
      </div>
      <div style="margin-top:14px;text-align:right;">
        <button type="button" class="btn ghost small" onclick="closeHistoricalRationaleModal()">Close Snapshot</button>
      </div>
    </div>
  </div>
"""
code = code.replace("</body>", hist_modal_html + "\n</body>", 1)
print("8. Added historicalRationaleModal HTML")

# 9. Clean Funds Tab: Remove Auto-Trade funds card (Item 23)
funds_auto_card = """        <div class="card stat-card" style="border-left:4px solid #60A5FA;padding:14px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="label" style="font-weight:700;color:var(--text);font-size:12px;">[AI] Auto-Trade Funds</span>
            <span class="tag" style="background:rgba(96,165,250,0.15);color:#60A5FA;font-size:9px;">Autonomous Bot</span>
          </div>
          <div class="value" id="walletAutoBalance" style="font-size:22px;font-weight:700;margin:6px 0;color:#60A5FA;">₹1,00,000.00</div>
          <div class="muted" id="walletAutoUsed" style="font-size:11px;">Used Margin: ₹0.00</div>
        </div>"""
if funds_auto_card in code:
    code = code.replace(funds_auto_card, "", 1)
    code = code.replace('<div class="grid grid-3" style="margin-bottom:16px;">', '<div class="grid grid-2" style="margin-bottom:16px;">', 1)
    print("9. Cleaned Funds Tab: Removed Auto-Trade Funds card")

# 10. Reports Tab: Add subtabs for User Trades vs System Recommendations (Item 23)
old_reports_head = """      <!-- KPI Summary Cards -->
      <div class="report-kpi-grid">"""
new_reports_head = """      <!-- Reports Subtabs (Item 23) -->
      <div style="display:flex;gap:8px;margin-bottom:14px;border-bottom:1px solid var(--border-soft);padding-bottom:8px;">
        <button type="button" class="btn small active" id="btnRepSubUserTrades" onclick="switchReportsSubTab('user')" style="font-size:11.5px;font-weight:700;">User Executed Trades</button>
        <button type="button" class="btn ghost small" id="btnRepSubSystemRecos" onclick="switchReportsSubTab('system')" style="font-size:11.5px;font-weight:700;">System Recommendation History</button>
      </div>

      <!-- KPI Summary Cards -->
      <div class="report-kpi-grid">"""
assert old_reports_head in code, "old_reports_head not found"
code = code.replace(old_reports_head, new_reports_head, 1)
print("10. Added Subtabs to Reports & P&L tab")

# 11. Legacy loadDashboard stub delegate (Item 3 & 4)
old_stub_guard = "if(!sym||!$('dashboardSignal'))return;"
new_stub_guard = "// Release 45: delegate immediately to authoritative loadDashboard\n    if(window.loadDashboard && window.loadDashboard !== loadDashboard){ return window.loadDashboard(); }"
assert old_stub_guard in code, "old_stub_guard not found"
code = code.replace(old_stub_guard, new_stub_guard, 1)
print("11. Delegated legacy loadDashboard to authoritative function")

# 12. Fix Watchlist Quote resolution in applyQuote (Item 21)
old_apply_quote = """const row=document.querySelector(`.wl-item[data-symbol="${CSS.escape(String(sym))}"]`);if(!row)return;"""
new_apply_quote = """const row=document.querySelector(`.wl-item[data-symbol="${CSS.escape(String(sym))}"]`) || document.querySelector(`.wl-item[data-symbol="${CSS.escape(String(q?.instrument || ''))}"]`) || document.querySelector(`.wl-item[data-symbol="${CSS.escape(String(q?.metadata?.name || ''))}"]`);if(!row)return;"""
assert old_apply_quote in code, "old_apply_quote not found"
code = code.replace(old_apply_quote, new_apply_quote, 1)
print("12. Fixed Watchlist quote resolution for commodities like CRUDEOIL")

# 13. Add 'R' (Auto-Reco) toggle button in watchlist items renderer R() (Item 10)
old_wl_actions = 'data-wl-sell="${esc(i.symbol)}">S</button><button type="button" class="wl-bs del" data-wl-del="${esc(i.symbol)}"'
new_wl_actions = 'data-wl-sell="${esc(i.symbol)}">S</button><button type="button" class="wl-r-btn ${window.__caAutoRecoSymbols && window.__caAutoRecoSymbols.has(i.symbol) ? \'active\' : \'\'}" data-auto-reco-sym="${esc(i.symbol)}" onclick="event.stopPropagation();toggleAutoRecoSymbol(\'${esc(i.symbol)}\');" title="Toggle 5-Min Auto-Recommendation">R</button><button type="button" class="wl-bs del" data-wl-del="${esc(i.symbol)}"'
assert old_wl_actions in code, "old_wl_actions not found in R()"
code = code.replace(old_wl_actions, new_wl_actions, 1)
print("13. Added 'R' button into watchlist item DOM construction")

# 14. Option Chain: Instant cached view toggle without 429 (Item 11)
old_chain_toggle = """      // Wire OI vs Greeks toggle
      document.getElementById('btnOptViewOI')?.addEventListener('click', () => {
        optChainMode = 'oi';
        document.getElementById('btnOptViewOI')?.classList.add('active');
        document.getElementById('btnOptViewGreeks')?.classList.remove('active');
        void fetchOptionChain();
      });
      document.getElementById('btnOptViewGreeks')?.addEventListener('click', () => {
        optChainMode = 'greeks';
        document.getElementById('btnOptViewGreeks')?.classList.add('active');
        document.getElementById('btnOptViewOI')?.classList.remove('active');
        void fetchOptionChain();
      });"""

new_chain_toggle = """      // Wire OI vs Greeks toggle (Instant cached toggle without 429 - Item 11)
      document.getElementById('btnOptViewOI')?.addEventListener('click', () => {
        optChainMode = 'oi';
        document.getElementById('btnOptViewOI')?.classList.add('active');
        document.getElementById('btnOptViewGreeks')?.classList.remove('active');
        if(typeof renderZerodhaOptionChain === 'function' && optionState.chain){
          renderZerodhaOptionChain(optionState.chain);
        } else {
          void fetchOptionChain();
        }
      });
      document.getElementById('btnOptViewGreeks')?.addEventListener('click', () => {
        optChainMode = 'greeks';
        document.getElementById('btnOptViewGreeks')?.classList.add('active');
        document.getElementById('btnOptViewOI')?.classList.remove('active');
        if(typeof renderZerodhaOptionChain === 'function' && optionState.chain){
          renderZerodhaOptionChain(optionState.chain);
        } else {
          void fetchOptionChain();
        }
      });"""
assert old_chain_toggle in code, "old_chain_toggle not found"
code = code.replace(old_chain_toggle, new_chain_toggle, 1)
print("14. Option Chain: Cached view toggle without 429")

# 15. Recommendation History Table: Add Rationale column and handle Trailing SL & Next Session Setup (Items 1, 8, 9, 10)
# Update outcome label logic
old_outcome_logic = """if(x.status === 'TARGET_HIT' || x.outcome === 'TARGET_HIT' || (isBuySig && tgt > 0 && curPrice >= tgt) || (!isBuySig && tgt > 0 && curPrice <= tgt && curPrice > 0)){
                  outcomeLabel = 'Target Hit (Success)';
                  outcomeTagCls = 'buy';
                } else if(x.status === 'SL_HIT' || x.outcome === 'SL_HIT' || (isBuySig && sl > 0 && curPrice <= sl && curPrice > 0) || (!isBuySig && sl > 0 && curPrice >= sl)){
                  outcomeLabel = 'SL Hit';
                  outcomeTagCls = 'sell';
                } else if(pnl > 0){
                  outcomeLabel = 'Target Hit (Success)';
                  outcomeTagCls = 'buy';
                } else if(pnl < 0){
                  outcomeLabel = 'SL Hit';
                  outcomeTagCls = 'sell';
                }"""

new_outcome_logic = """if(x.status === 'SETUP' || x.outcome === 'Next Session Setup' || x.outcome === 'Pending Setup' || x.outcome === 'Pending Market Open'){
                  outcomeLabel = 'Next Session Setup';
                  outcomeTagCls = 'neutral';
                } else if(x.status === 'TARGET_HIT' || x.outcome === 'Target Hit' || (isBuySig && tgt > 0 && curPrice >= tgt) || (!isBuySig && tgt > 0 && curPrice <= tgt && curPrice > 0)){
                  outcomeLabel = 'Target Hit';
                  outcomeTagCls = 'buy';
                } else if(x.status === 'SL_HIT' || x.outcome === 'SL Hit' || (isBuySig && sl > 0 && curPrice <= sl && curPrice > 0) || (!isBuySig && sl > 0 && curPrice >= sl)){
                  outcomeLabel = 'SL Hit';
                  outcomeTagCls = 'sell';
                } else if(x.outcome === 'Early Exit'){
                  outcomeLabel = 'Early Exit';
                  outcomeTagCls = 'sell';
                } else if(tgt === 0 || !tgt || x.outcome === 'Active Trailing'){
                  outcomeLabel = 'Active Trailing';
                  outcomeTagCls = 'gold';
                } else {
                  outcomeLabel = 'Active Signal';
                  outcomeTagCls = 'gold';
                }"""
assert old_outcome_logic in code, "old_outcome_logic not found"
code = code.replace(old_outcome_logic, new_outcome_logic, 1)
print("15. Updated Recommendation History outcome logic (removed fake Target Hit)")

# Add Rationale column header
code = code.replace('<th>Target</th>\n                <th>P&amp;L</th>\n              </tr>', '<th>Target</th>\n                <th>P&amp;L</th>\n                <th>Rationale</th>\n              </tr>', 1)

# Add Rationale column button & Trailing SL display in rows
old_row_cells = """<td style="cursor:pointer;color:var(--buy);" onclick="openRecoCalculationModal(${recJson}, 'target')" title="Click to view Target calculation">₹${fmt(x.target)}</td>
                    <td><b style="color:${pnlColor};font-family:var(--font-mono);">${pnlStr}</b></td>
                  </tr>"""

new_row_cells = """<td style="color:var(--buy);">${tgt > 0 ? `₹${fmt(tgt)}` : '<span class="tag gold" style="font-size:9.5px;">Trailing SL</span>'}</td>
                    <td><b style="color:${pnlColor};font-family:var(--font-mono);">${pnlStr}</b></td>
                    <td><button type="button" class="btn ghost small" onclick="openHistoricalRationaleModal(${recJson})" style="font-size:10px;padding:2px 7px;border-color:var(--primary);color:var(--primary);cursor:pointer;">Show Rationale</button></td>
                  </tr>"""
assert old_row_cells in code, "old_row_cells not found"
code = code.replace(old_row_cells, new_row_cells, 1)
print("16. Added 'Show Rationale' button to history rows")

# 17. Comprehensive Dashboard Engine & Features Replacement in the final <script>
idx_eng = code.find('// ==========================================\n  // DASHBOARD ENGINE (Release 43)')
if idx_eng == -1:
    idx_eng = code.find('DASHBOARD ENGINE')
assert idx_eng != -1, "DASHBOARD ENGINE block not found"
start_eng = code.rfind('<script', 0, idx_eng)
end_eng = code.find('</script>', idx_eng) + len('</script>')

code = code[:start_eng] + new_engine_script + code[end_eng:]
print("17. Replaced Dashboard engine with Release 45 authoritative implementation")

path.write_text(code, encoding="utf-8")
print(f"Updated terminal.html successfully written: {len(code):,} bytes")
