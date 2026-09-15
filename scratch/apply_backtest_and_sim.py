# -*- coding: utf-8 -*-
"""
Apply Price Sensitivity Simulator and Backtesting Dual Charts overhaul
"""
with open('terminal.html', 'r', encoding='utf-8') as f:
    c = f.read()

print("Original size:", len(c))

# 1. Insert Price Sensitivity Simulator into #panel-charts
charts_anchor = """      <div class="card" style="margin-bottom:14px;">
        <div class="card-head"><div class="card-title">Technical Indicator Signals</div><div class="muted" id="signalUpdated">Waiting for data…</div></div>
        <div class="indicator-table-wrap"><table class="indicator-table"><thead><tr><th>Indicator</th><th>Value</th><th>Materiality</th><th>Signal</th><th>Criteria</th></tr></thead><tbody id="indicatorRows"></tbody></table></div>
      </div>"""

charts_sim_html = """      <div class="card" style="margin-bottom:14px;">
        <div class="card-head"><div class="card-title">Technical Indicator Signals</div><div class="muted" id="signalUpdated">Waiting for data…</div></div>
        <div class="indicator-table-wrap"><table class="indicator-table"><thead><tr><th>Indicator</th><th>Value</th><th>Materiality</th><th>Signal</th><th>Criteria</th></tr></thead><tbody id="indicatorRows"></tbody></table></div>
      </div>

      <!-- Indicator Price Sensitivity Simulator (Charts & Technicals - Item 10) -->
      <div class="card" style="margin-bottom:14px;" id="chartPriceSensitivityCard">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:rgba(232,184,75,0.15);color:var(--gold);font-size:12px;font-weight:700;">⚡</span>
            <div>
              <div class="card-title">Price Sensitivity Simulator</div>
              <div class="muted" style="font-size:10.5px;margin-top:1px;">Simulate underlying price shocks against key indicator levels, Greeks, and option prices</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="tag neutral" id="chartSimCmpBadge" style="font-family:var(--font-mono);font-size:11px;font-weight:700;">CMP: ₹--</span>
            <span class="tag buy" id="chartSimDiffBadge" style="font-family:var(--font-mono);font-size:11px;font-weight:700;">Diff: +₹0.00 (+0.00%)</span>
          </div>
        </div>
        <div style="margin-top:12px;">
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-faint);margin-bottom:4px;">
            <span>-5.0% Bear Shock</span>
            <span style="font-weight:700;color:var(--gold);" id="chartSimSliderDisplay">Simulated Price: ₹-- (CMP)</span>
            <span>+5.0% Bull Surge</span>
          </div>
          <input type="range" id="chartSimSlider" min="-50" max="50" value="0" step="1" style="width:100%;cursor:pointer;">
        </div>
        <div class="grid grid-4" style="margin-top:14px;gap:10px;" id="chartSimGrid">
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">Simulated Price</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:14px;color:var(--text);margin-top:2px;" id="chartSimPriceVal">--</div>
            <div style="font-size:10px;color:var(--buy);" id="chartSimPriceDiff">0.00% vs CMP</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">ATM Call Premium Impact</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:14px;color:var(--buy);margin-top:2px;" id="chartSimCallDelta">₹0.00</div>
            <div style="font-size:10px;color:var(--text-dim);" id="chartSimCallDetail">Δ ≈ 0.50 per ₹1</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">ATM Put Premium Impact</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:14px;color:var(--sell);margin-top:2px;" id="chartSimPutDelta">₹0.00</div>
            <div style="font-size:10px;color:var(--text-dim);" id="chartSimPutDetail">Δ ≈ -0.50 per ₹1</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">Technical Threshold Breach</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:12px;color:var(--gold);margin-top:2px;" id="chartSimThreshold">At CMP Level</div>
            <div style="font-size:10px;color:var(--text-dim);" id="chartSimThresholdDetail">Testing key support/resistance</div>
          </div>
        </div>
      </div>"""

if charts_anchor in c:
    c = c.replace(charts_anchor, charts_sim_html)
    print("1. Inserted Price Sensitivity Simulator into Charts tab")

# 2. Insert Price Sensitivity Simulator into #panel-reco
reco_anchor = """      <div id="recoHistorySection">"""
reco_sim_html = """      <!-- Price Sensitivity Simulator (Recommendation History - Item 10) -->
      <div class="card" style="margin-bottom:14px;" id="recoPriceSensitivityCard">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:rgba(232,184,75,0.15);color:var(--gold);font-size:12px;font-weight:700;">⚡</span>
            <div>
              <div class="card-title">Recommendation Price Sensitivity Simulator</div>
              <div class="muted" style="font-size:10.5px;margin-top:1px;">Test target & stop-loss tolerances against simulated underlying price fluctuations</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="tag neutral" id="recoSimCmpBadge" style="font-family:var(--font-mono);font-size:11px;font-weight:700;">CMP: ₹--</span>
            <span class="tag buy" id="recoSimDiffBadge" style="font-family:var(--font-mono);font-size:11px;font-weight:700;">Diff: +₹0.00 (+0.00%)</span>
          </div>
        </div>
        <div style="margin-top:12px;">
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-faint);margin-bottom:4px;">
            <span>-5.0% Downside</span>
            <span style="font-weight:700;color:var(--gold);" id="recoSimSliderDisplay">Simulated Price: ₹-- (CMP)</span>
            <span>+5.0% Upside</span>
          </div>
          <input type="range" id="recoSimSlider" min="-50" max="50" value="0" step="1" style="width:100%;cursor:pointer;">
        </div>
        <div class="grid grid-4" style="margin-top:14px;gap:10px;" id="recoSimGrid">
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">Simulated Underlying</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:14px;color:var(--text);margin-top:2px;" id="recoSimPriceVal">--</div>
            <div style="font-size:10px;color:var(--buy);" id="recoSimPriceDiff">0.00% vs CMP</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">Call Option Est. Value</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:14px;color:var(--buy);margin-top:2px;" id="recoSimCallDelta">₹0.00</div>
            <div style="font-size:10px;color:var(--text-dim);" id="recoSimCallDetail">Δ ≈ 0.50 sensitivity</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">Put Option Est. Value</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:14px;color:var(--sell);margin-top:2px;" id="recoSimPutDelta">₹0.00</div>
            <div style="font-size:10px;color:var(--text-dim);" id="recoSimPutDetail">Δ ≈ -0.50 sensitivity</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">Recommendation Status</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:12px;color:var(--gold);margin-top:2px;" id="recoSimThreshold">Holding Range</div>
            <div style="font-size:10px;color:var(--text-dim);" id="recoSimThresholdDetail">Within Target / SL bounds</div>
          </div>
        </div>
      </div>

      <div id="recoHistorySection">"""

if reco_anchor in c and "recoPriceSensitivityCard" not in c:
    c = c.replace(reco_anchor, reco_sim_html)
    print("2. Inserted Price Sensitivity Simulator into Recommendation History tab")

# Clean Recommendation History chips (Item 11: remove auto trade chip)
reco_chips_old = """<div style="display:flex;gap:8px;"><div class="chip-filter active">All</div><div class="chip-filter">Auto Trade</div><div class="chip-filter">On-Demand</div></div>"""
reco_chips_new = """<div style="display:flex;gap:8px;"><div class="chip-filter active">All History</div><div class="chip-filter">Bullish</div><div class="chip-filter">Bearish</div></div>"""
if reco_chips_old in c:
    c = c.replace(reco_chips_old, reco_chips_new)
    print("2b. Cleaned Recommendation History chips")

# 3. Backtesting Dual Charts HTML overhaul
# Find the entire #panel-backtest card structure and update it
bt_old_section = """            <button class="btn ghost small" id="btLoadDataBtn">Load Replay</button>
          </div>

          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            <button class="btn gold small" id="btPlayPauseBtn" style="min-width:80px;">▶ Play</button>
            <button class="btn ghost small" id="btStepBtn" title="Step one candle forward">⏭ Step</button>
            <div style="display:flex;gap:4px;background:var(--surface-2);border-radius:6px;padding:2px;border:1px solid var(--border-soft);">
              <button class="tf-btn active" data-bt-speed="1" style="padding:4px 8px;font-size:10px;">1x</button>
              <button class="tf-btn" data-bt-speed="2" style="padding:4px 8px;font-size:10px;">2x</button>
              <button class="tf-btn" data-bt-speed="5" style="padding:4px 8px;font-size:10px;">5x</button>
              <button class="tf-btn" data-bt-speed="10" style="padding:4px 8px;font-size:10px;">10x</button>
            </div>
            <button class="btn ghost small" id="btResetBtn">↺ Reset</button>
          </div>
        </div>

        <div style="margin-top:10px;display:flex;align-items:center;gap:12px;">
          <input type="range" id="btTimelineSlider" min="0" max="100" value="0" style="flex:1;cursor:pointer;">
          <span id="btProgressLabel" class="muted" style="font-family:var(--font-mono);font-size:11px;min-width:110px;text-align:right;">0 / 0 candles</span>
        </div>
      </div>"""

bt_new_section = """            <label style="font-size:10px;display:flex;align-items:center;gap:4px;color:var(--text-faint);font-weight:600;">
              Option
              <select id="btOptionContractSelect" class="tool-input" style="width:160px;font-size:11px;background:var(--surface-2);color:var(--text);border:1px solid var(--border-soft);border-radius:6px;" title="Selected Option Contract to backtest in sync">
                <option value="">Loading Option Chain…</option>
              </select>
            </label>
            <button class="btn ghost small" id="btLoadDataBtn">Load Replay</button>
          </div>

          <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
            <button class="btn ghost small" id="btStepBackBtn" title="Step one candle backward">⏮ Step</button>
            <button class="btn gold small" id="btPlayPauseBtn" style="min-width:80px;">▶ Play</button>
            <button class="btn ghost small" id="btStepBtn" title="Step one candle forward">⏭ Step</button>
            <div style="display:flex;gap:4px;background:var(--surface-2);border-radius:6px;padding:2px;border:1px solid var(--border-soft);">
              <button class="tf-btn active" data-bt-speed="1" style="padding:4px 8px;font-size:10px;">1x</button>
              <button class="tf-btn" data-bt-speed="2" style="padding:4px 8px;font-size:10px;">2x</button>
              <button class="tf-btn" data-bt-speed="5" style="padding:4px 8px;font-size:10px;">5x</button>
              <button class="tf-btn" data-bt-speed="10" style="padding:4px 8px;font-size:10px;">10x</button>
            </div>
            <button class="btn ghost small" id="btResetBtn">↺ Reset</button>
          </div>
        </div>

        <div style="margin-top:10px;display:flex;align-items:center;gap:12px;">
          <input type="range" id="btTimelineSlider" min="0" max="100" value="0" style="flex:1;cursor:pointer;">
          <span id="btProgressLabel" class="muted" style="font-family:var(--font-mono);font-size:11px;min-width:140px;text-align:right;">0 / 0 candles</span>
        </div>
      </div>"""

if bt_old_section in c:
    c = c.replace(bt_old_section, bt_new_section)
    print("3a. Updated Backtesting Control Bar with Option Selector & Step Back")

# Insert synchronized option chart right below the underlying chart in backtest
old_bt_chart = """        <div style="position:relative;height:460px;width:100%;background:var(--surface-2);border-radius:8px;border:1px solid var(--border-soft);overflow:hidden;" id="btChartViewport">
          <canvas id="btCanvas" style="width:100%;height:100%;display:block;cursor:crosshair;"></canvas>
          <div id="btChartPlaceholder" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--text-faint);font-size:13px;pointer-events:none;">
            Select dates and click "Load Replay" to begin tick-by-tick simulation.
          </div>
        </div>
      </div>"""

new_bt_chart = """        <div style="position:relative;height:380px;width:100%;background:var(--surface-2);border-radius:8px;border:1px solid var(--border-soft);overflow:hidden;" id="btChartViewport">
          <canvas id="btCanvas" style="width:100%;height:100%;display:block;cursor:crosshair;"></canvas>
          <div id="btChartPlaceholder" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--text-faint);font-size:13px;pointer-events:none;">
            Select dates and click "Load Replay" to begin tick-by-tick simulation.
          </div>
        </div>
      </div>

      <!-- Synchronized Option Contract Chart (Item 15) -->
      <div class="card" style="padding:14px;background:var(--surface);margin-bottom:16px;width:100%;border:1px solid rgba(232,184,75,0.25);">
        <div class="card-head" style="margin-bottom:8px;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="card-title">Option Contract Chart (Synchronized)</span>
            <span class="tag gold" id="btOptionNameBadge" style="font-size:11px;font-weight:700;">NIFTY 23500 CE</span>
            <span class="badge ghost" id="btOptionGreeksBadge" style="font-family:var(--font-mono);font-size:10.5px;padding:3px 8px;border-radius:6px;border:1px solid var(--border-soft);">Δ: 0.52 | Γ: 0.001 | Θ: -14.2 | ν: 8.5 | IV: 14.8%</span>
          </div>
          <div style="display:flex;gap:12px;font-family:var(--font-mono);font-size:11.5px;flex-wrap:wrap;padding-top:4px;" id="btOptOhlcBar">
            <span>Opt O: <b id="btOptO">--</b></span>
            <span>Opt H: <b id="btOptH">--</b></span>
            <span>Opt L: <b id="btOptL">--</b></span>
            <span>Opt C: <b id="btOptC">--</b></span>
            <span>Sim LTP: <b id="btOptLtp" style="color:var(--gold);">--</b></span>
          </div>
        </div>
        <div style="position:relative;height:260px;width:100%;background:var(--surface-2);border-radius:8px;border:1px solid var(--border-soft);overflow:hidden;" id="btOptionChartViewport">
          <canvas id="btOptionCanvas" style="width:100%;height:100%;display:block;cursor:crosshair;"></canvas>
          <div id="btOptionPlaceholder" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--text-faint);font-size:12px;pointer-events:none;">
            Option price chart synchronizes with replay tick and historical Black-Scholes Greeks.
          </div>
        </div>
      </div>"""

if old_bt_chart in c:
    c = c.replace(old_bt_chart, new_bt_chart)
    print("3b. Inserted Synchronized Option Contract Chart into Backtest tab")

# 4. Vertically stack simulated positions and simulation performance (Item 16)
old_stack = """      <!-- Bottom Tables: Active Replay Positions & Closed Trades Log -->
      <div class="grid grid-2" style="gap:16px;">
        <!-- Open Backtest Positions -->
        <div class="card" style="padding:14px;background:var(--surface);">"""

new_stack = """      <!-- Bottom Tables: Vertically Stacked Simulated Positions & Closed Performance (Item 16) -->
      <div style="display:flex;flex-direction:column;gap:16px;width:100%;margin-top:14px;">
        <!-- Open Backtest Positions (Full Width) -->
        <div class="card" style="padding:14px;background:var(--surface);width:100%;">"""

if old_stack in c:
    c = c.replace(old_stack, new_stack)
    print("4. Vertically stacked simulated positions and performance")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated terminal.html successfully with Simulator and Backtesting. Final size:", len(c))

