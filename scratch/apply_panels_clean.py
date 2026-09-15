# -*- coding: utf-8 -*-
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

start_marker = '    <!-- ============ DASHBOARD (Release 43) ============ -->'
end_marker = '    <div class="panel" id="panel-console">'

idx_start = text.find(start_marker)
idx_end = text.find(end_marker)

print("idx_start:", idx_start, "idx_end:", idx_end)
assert idx_start != -1 and idx_end != -1 and idx_start < idx_end

new_content = '''    <!-- ============ DASHBOARD (Release 43) ============ -->
    <div class="panel active" id="panel-dashboard">
      <div class="page-head">
        <div>
          <div class="page-title chart-symbol-line">
            <span id="dashSymbolTitle">—</span>
            <span class="chart-symbol-ltp" id="dashSymbolLtp">—</span>
            <span class="chart-symbol-change" id="dashSymbolChange">—</span>
          </div>
          <div class="page-sub chart-company" id="dashCompany">Institutional Quantitative Dashboard · Live Intelligence</div>
        </div>
        <div class="head-actions">
          <button class="btn gold" id="dashBuyBtn" onclick="openOrder('BUY')">Buy</button>
          <button class="btn ghost" id="dashSellBtn" onclick="openOrder('SELL')">Sell</button>
          <button class="btn ghost small" onclick="loadDashboard(); toast('↻ Dashboard synchronized');">↻ Sync</button>
        </div>
      </div>

      <!-- Recommendation Box -->
      <div class="card" id="chartRecoBanner" style="margin-bottom:12px;padding:12px 16px;background:var(--surface);border:1px solid rgba(38,217,166,0.3);box-shadow:0 6px 20px rgba(0,0,0,0.2);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;overflow:visible !important;position:relative;z-index:1000;">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
          <span style="display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:7px;background:var(--buy-bg);color:var(--buy);font-size:14px;font-weight:700;">✦</span>
          <div>
            <div style="display:flex;align-items:center;gap:8px;position:relative;flex-wrap:wrap;">
              <span class="tag neutral" id="chartRecoAction" style="font-size:11.5px;font-weight:700;padding:2px 8px;">SIGNAL</span>
              <span style="font-weight:700;font-size:13.5px;color:var(--text);" id="chartRecoSymbol">—</span>
              <select id="chartRecoOptionSelect" style="display:inline-block;height:26px;font-size:11px;padding:2px 6px;border-radius:6px;border:1px solid var(--border);background:var(--surface-2);color:var(--text);font-family:var(--font-mono);max-width:210px;cursor:pointer;">
                <option value="">Auto (Best Option)</option>
              </select>
              <span class="muted" style="font-size:11px;" id="chartRecoConfidence">Live Consensus</span>
            </div>
            <!-- Dynamic Advisory Callout Box -->
            <div id="chartRecoAdvisoryBox" style="margin-top:6px;padding:6px 12px;border-radius:6px;font-size:11.5px;line-height:1.45;background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.25);display:flex;align-items:flex-start;gap:8px;max-width:720px;">
              <span id="chartRecoAdvisoryIcon" style="font-size:13px;line-height:1.2;">💡</span>
              <div id="chartRecoAdvisoryText" style="flex:1;color:var(--text);">Analyzing technical structure and optimal option contracts…</div>
            </div>
            <div class="muted" id="chartRecoRationale" style="display:none;"></div>
          </div>
        </div>

        <!-- Entry / SL / Target / R:R pills -->
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;min-width:0;box-sizing:border-box;">
          <div class="stat-pill clickable-calc" id="chartRecoEntryPill" title="Click to inspect Entry calculation proof" style="cursor:pointer;background:var(--surface-2);border:1px solid var(--border-soft);padding:4px 10px;border-radius:6px;text-align:center;min-width:0;">
            <div style="font-size:9px;color:var(--text-faint);text-transform:uppercase;">Entry ⓘ</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:13px;color:var(--text);" id="chartRecoEntry">₹--</div>
          </div>
          <div class="stat-pill clickable-calc" id="chartRecoSlPill" title="Click to inspect Stop Loss calculation proof" style="cursor:pointer;background:var(--surface-2);border:1px solid var(--border-soft);padding:4px 10px;border-radius:6px;text-align:center;min-width:0;">
            <div style="font-size:9px;color:var(--text-faint);text-transform:uppercase;">Stop Loss ⓘ</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:13px;color:var(--sell);" id="chartRecoSl">₹--</div>
          </div>
          <div class="stat-pill clickable-calc" id="chartRecoTgtPill" title="Click to inspect Target calculation proof" style="cursor:pointer;background:var(--surface-2);border:1px solid var(--border-soft);padding:4px 10px;border-radius:6px;text-align:center;min-width:0;">
            <div style="font-size:9px;color:var(--text-faint);text-transform:uppercase;">Target (≥ ₹500) ⓘ</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:13px;color:var(--buy);" id="chartRecoTgt">₹--</div>
          </div>
          <div class="stat-pill" style="background:var(--surface-2);border:1px solid var(--border-soft);padding:6px 10px;border-radius:6px;text-align:center;min-width:0;">
            <div style="font-size:9px;color:var(--text-faint);text-transform:uppercase;">R : R</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:13px;color:var(--gold);" id="chartRecoRr">1 : 2.2</div>
          </div>
          <button type="button" class="icon-btn" id="chartRecoCriteriaBtn" title="Recommendation Criteria (Profit, Loss, Capital)" style="height:32px;width:32px;display:inline-flex;align-items:center;justify-content:center;border-radius:6px;background:var(--surface-2);border:1px solid var(--border);cursor:pointer;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          </button>
          <button type="button" class="btn ghost small" id="chartRecoRefreshBtn" title="Refresh Live Recommendation" style="height:32px;display:inline-flex;align-items:center;gap:5px;padding:0 10px;border-color:var(--border);background:var(--surface-2);cursor:pointer;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
            <span>Refresh</span>
          </button>
          <button type="button" class="btn gold small" id="chartRecoQuickOrderBtn" title="Place 1-Click Quick Order" style="height:32px;display:inline-flex;align-items:center;gap:5px;padding:0 12px;font-weight:700;cursor:pointer;">
            <span>Quick Order</span>
          </button>
        </div>
      </div>

      <!-- Criteria Settings Modal for Recommendation -->
      <div id="chartRecoCriteriaModal" style="display:none;position:fixed;top:120px;right:40px;z-index:9999;width:320px;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;box-shadow:0 16px 36px rgba(0,0,0,0.4);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;border-bottom:1px solid var(--border-soft);padding-bottom:8px;">
          <b style="font-size:13px;color:var(--text);">Recommendation &amp; Risk Criteria</b>
          <button type="button" class="btn ghost small" id="closeCriteriaModalBtn" style="padding:2px 6px;">✕</button>
        </div>
        <div style="display:flex;flex-direction:column;gap:10px;font-size:12px;">
          <div>
            <label style="display:block;font-size:11px;color:var(--buy);font-weight:700;margin-bottom:3px;">Desired Profit (₹)</label>
            <input id="chartCriteriaDesiredProfit" type="number" step="100" min="50" class="tool-input" style="width:100%;font-size:12px;" value="500">
          </div>
          <div>
            <label style="display:block;font-size:11px;color:var(--sell);font-weight:700;margin-bottom:3px;">Max Bearable Loss (₹)</label>
            <input id="chartCriteriaMaxLoss" type="number" step="100" min="100" class="tool-input" style="width:100%;font-size:12px;" value="1000">
          </div>
          <div>
            <label style="display:block;font-size:11px;color:var(--text-dim);font-weight:700;margin-bottom:3px;">Capital Allocation (₹)</label>
            <input id="chartCriteriaCapital" type="number" step="5000" min="5000" class="tool-input" style="width:100%;font-size:12px;" value="50000">
          </div>
          <div style="display:flex;align-items:center;gap:8px;margin-top:4px;">
            <input type="checkbox" id="chartCriteriaOptionsOnly" checked style="accent-color:var(--buy);cursor:pointer;">
            <label for="chartCriteriaOptionsOnly" style="cursor:pointer;font-size:11.5px;">Prefer Defined-Risk Options</label>
          </div>
          <div style="display:flex;gap:8px;margin-top:6px;">
            <button type="button" class="btn gold small" id="saveCriteriaModalBtn" style="flex:1;justify-content:center;">Apply &amp; Refresh</button>
          </div>
        </div>
      </div>

      <!-- Unified Recommendation Rationale & Confluence Matrix Table (Data-Driven, All Items, No Boring Sentences) -->
      <div class="card" id="dashRationaleCard" style="margin-bottom:14px;padding:16px 18px;background:var(--surface);border:1px solid var(--border);border-radius:10px;box-shadow:0 4px 18px rgba(0,0,0,0.14);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;border-bottom:1px solid var(--border-soft);padding-bottom:10px;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:10px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:7px;background:rgba(24,144,255,0.15);color:var(--primary);font-size:13px;font-weight:700;">✦</span>
            <b style="font-size:14px;color:var(--text);font-family:var(--font-display);">Recommendation Rationale · Evidence &amp; Confluence Matrix</b>
            <span class="tag buy" id="dashRationaleSignalTag" style="font-size:11px;font-weight:700;">BUY OPTION SETUP</span>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="tag gold" id="dashRationaleScoreBadge" style="font-size:11.5px;font-weight:700;">84.5% Overall Score</span>
            <span class="muted" style="font-size:11px;">100% Data-Driven Multi-Factor Verification</span>
          </div>
        </div>

        <div class="table-wrap" style="overflow-x:auto;">
          <table style="width:100%;border-collapse:collapse;font-size:11.5px;text-align:left;">
            <thead>
              <tr style="border-bottom:1px solid var(--border);background:var(--surface-2);font-size:10.5px;text-transform:uppercase;color:var(--text-faint);letter-spacing:0.5px;">
                <th style="padding:8px 10px;">Category / Particulars</th>
                <th style="padding:8px 10px;">Value / Level</th>
                <th style="padding:8px 10px;">Score / Weightage</th>
                <th style="padding:8px 10px;">Signal</th>
                <th style="padding:8px 10px;">Relevance &amp; Verification Source</th>
              </tr>
            </thead>
            <tbody id="dashConfluenceTableBody">
              <!-- Populated dynamically with all indicators, all patterns, all news, all other factors, and all Greeks -->
            </tbody>
          </table>
        </div>
      </div>

      <!-- Full-Width Option Greeks Card -->
      <div class="card" style="margin-bottom:14px;" id="dashGreeksCard">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div>
            <div class="card-title" id="dashGreeksTitle">Live Option Greeks &amp; Contract Sensitivities</div>
            <div class="muted" id="dashGreeksSubtitle" style="font-size:11px;">Click any Greek card to view institutional definition, formula &amp; trading impact</div>
          </div>
          <div style="display:flex;align-items:center;gap:6px;">
            <span class="tag gold" id="chartGreeksContractBadge" style="font-family:var(--font-mono);font-size:11px;">Contract: ATM</span>
            <span class="tag neutral" id="chartGreeksIvBadge" style="font-size:11px;">IV: 14.2%</span>
          </div>
        </div>
        <div class="grid grid-4" style="margin-top:12px;gap:10px;" id="chartGreeksGrid">
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);cursor:pointer;" onclick="openGreekModal('Delta', $('cgDelta')?.textContent, selectedSymbol(), null, $('cgDelta')?.textContent)" title="Click to view Delta definition">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span class="label" style="font-size:11px;color:var(--text-faint);text-transform:uppercase;">Delta (Δ)</span>
              <span class="tag buy" style="font-size:9.5px;padding:1px 5px;">Speed</span>
            </div>
            <div class="value" id="cgDelta" style="font-size:18px;font-weight:700;font-family:var(--font-mono);color:var(--text);margin-top:4px;">0.512</div>
            <div class="muted" style="font-size:10px;margin-top:2px;">₹ move per ₹1 underlying change (Click for details)</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);cursor:pointer;" onclick="openGreekModal('Gamma', $('cgGamma')?.textContent, selectedSymbol())" title="Click to view Gamma definition">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span class="label" style="font-size:11px;color:var(--text-faint);text-transform:uppercase;">Gamma (Γ)</span>
              <span class="tag neutral" style="font-size:9.5px;padding:1px 5px;">Accel</span>
            </div>
            <div class="value" id="cgGamma" style="font-size:18px;font-weight:700;font-family:var(--font-mono);color:var(--text);margin-top:4px;">0.0014</div>
            <div class="muted" style="font-size:10px;margin-top:2px;">Delta change rate per ₹1 underlying move</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);cursor:pointer;" onclick="openGreekModal('Theta', $('cgTheta')?.textContent, selectedSymbol())" title="Click to view Theta definition">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span class="label" style="font-size:11px;color:var(--text-faint);text-transform:uppercase;">Theta (Θ)</span>
              <span class="tag sell" style="font-size:9.5px;padding:1px 5px;">Decay</span>
            </div>
            <div class="value" id="cgTheta" style="font-size:18px;font-weight:700;font-family:var(--font-mono);color:var(--sell);margin-top:4px;">-14.200</div>
            <div class="muted" style="font-size:10px;margin-top:2px;">Daily time decay erosion per share</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);cursor:pointer;" onclick="openGreekModal('Vega', $('cgVega')?.textContent, selectedSymbol())" title="Click to view Vega definition">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span class="label" style="font-size:11px;color:var(--text-faint);text-transform:uppercase;">Vega (ν)</span>
              <span class="tag neutral" style="font-size:9.5px;padding:1px 5px;">Vol</span>
            </div>
            <div class="value" id="cgVega" style="font-size:18px;font-weight:700;font-family:var(--font-mono);color:var(--text);margin-top:4px;">16.500</div>
            <div class="muted" style="font-size:10px;margin-top:2px;">Option price change per 1% IV shift</div>
          </div>
        </div>
      </div>

      <!-- Price Sensitivity Simulator -->
      <div class="card" style="margin-bottom:14px;" id="chartPriceSensitivityCard">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:rgba(232,184,75,0.15);color:var(--gold);font-size:12px;font-weight:700;">⚡</span>
            <div>
              <div class="card-title" id="priceSensitivityTitle">Price Sensitivity Simulator</div>
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
      </div>

      <!-- Recommendation History at bottom of Dashboard -->
      <div class="card" style="margin-bottom:14px;" id="dashHistoryCard">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div>
            <div class="card-title">Recommendation Performance History</div>
            <div class="muted" style="font-size:11px;">Real-time outcome tracking (Target Hit, SL Hit, Active Trail, P&amp;L) for every recommendation</div>
          </div>
          <div style="display:flex;gap:6px;">
            <input type="date" id="recoFilterFrom" class="tool-input" style="font-size:11px;padding:2px 6px;">
            <input type="date" id="recoFilterTo" class="tool-input" style="font-size:11px;padding:2px 6px;">
            <button class="btn ghost small" id="recoClearAllBtn" style="font-size:10.5px;">Clear History</button>
          </div>
        </div>
        <div id="recommendationHistory"><div class="data-empty">Loading history…</div></div>
      </div>
    </div>

    <!-- ============ TECHNICALS & CHARTS ============ -->
    <div class="panel" id="panel-charts">
      <div class="page-head">
        <div>
          <div class="page-title chart-symbol-line"><span id="chartSymbolTitle">—</span><span class="chart-symbol-ltp" id="chartSymbolLtp">—</span><span class="chart-symbol-change" id="chartSymbolChange">—</span></div>
          <div class="page-sub chart-company" id="chartCompanyName">Select an instrument</div>
        </div>
        <div class="head-actions">
          <button class="btn gold" id="chartBuyBtn">Buy</button>
          <button class="btn ghost" id="chartSellBtn">Sell</button>
        </div>
      </div>

      <div class="chart-shell" id="chartShell">
        <div class="chart-toolbar chart-toolbar-pro zerodha-toolbar" style="position:relative;display:flex;align-items:center;justify-content:space-between;gap:6px;padding:6px 10px;background:var(--surface);border-bottom:1px solid var(--border-soft);flex-wrap:wrap;">
          <div style="display:flex;align-items:center;gap:4px;">
            <!-- Timeframe Dropdown (Zerodha Kite Style) -->
            <div style="position:relative;">
              <button type="button" class="tf-btn" id="btnTfDropdown" title="Select Timeframe" style="display:inline-flex;align-items:center;gap:4px;padding:4px 8px;font-weight:700;">
                <span id="selectedTfLabel">5m</span>
                <span style="font-size:10px;">▾</span>
              </button>
              <div id="timeframeDropdownMenu" style="display:none;position:absolute;top:calc(100% + 4px);left:0;z-index:200;background:var(--surface);border:1px solid var(--border);border-radius:8px;box-shadow:0 12px 30px rgba(0,0,0,0.35);padding:6px;min-width:145px;max-height:360px;overflow-y:auto;">
                <div style="font-size:10px;font-weight:700;color:var(--text-faint);padding:3px 8px;text-transform:uppercase;">Minutes</div>
                <div class="tf-dd-item" data-tf="1m">1m</div>
                <div class="tf-dd-item" data-tf="2m">2m</div>
                <div class="tf-dd-item" data-tf="3m">3m</div>
                <div class="tf-dd-item" data-tf="4m">4m</div>
                <div class="tf-dd-item active" data-tf="5m">5m</div>
                <div class="tf-dd-item" data-tf="10m">10m</div>
                <div class="tf-dd-item" data-tf="15m">15m</div>
                <div class="tf-dd-item" data-tf="30m">30m</div>
                <div style="height:1px;background:var(--border-soft);margin:4px 0;"></div>
                <div style="font-size:10px;font-weight:700;color:var(--text-faint);padding:3px 8px;text-transform:uppercase;">Hours &amp; Days</div>
                <div class="tf-dd-item" data-tf="60m">1h</div>
                <div class="tf-dd-item" data-tf="120m">2h</div>
                <div class="tf-dd-item" data-tf="180m">3h</div>
                <div class="tf-dd-item" data-tf="240m">4h</div>
                <div class="tf-dd-item" data-tf="1D">1D</div>
                <div class="tf-dd-item" data-tf="1W">1W</div>
                <div class="tf-dd-item" data-tf="1M">1M</div>
              </div>
            </div>

            <!-- Saved Views (Cloud Icon) -->
            <div style="position:relative;">
              <button type="button" class="tf-btn" id="btnSavedViews" title="Saved Views" style="display:inline-flex;align-items:center;justify-content:center;padding:4px 8px;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>
              </button>
              <div id="savedViewsDropdownMenu" style="display:none;position:absolute;top:calc(100% + 4px);left:0;z-index:200;background:var(--surface);border:1px solid var(--border);border-radius:8px;box-shadow:0 12px 30px rgba(0,0,0,0.35);padding:8px;min-width:175px;">
                <div style="font-size:10px;font-weight:700;color:var(--text-faint);margin-bottom:6px;text-transform:uppercase;">Saved Views</div>
                <button type="button" class="btn small" id="btnSaveCurrentView" style="width:100%;justify-content:center;font-size:11px;margin-bottom:6px;">+ Save View</button>
                <div id="savedViewsList" style="display:flex;flex-direction:column;gap:2px;">
                  <div class="view-item active" data-view="Default" style="padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11.5px;">Default Layout</div>
                </div>
              </div>
            </div>

            <!-- +fx Indicators Button -->
            <button type="button" class="tf-btn" id="btnOpenIndicatorsModal" title="Technical Indicators (110+ available)" style="display:inline-flex;align-items:center;justify-content:center;padding:4px 9px;font-weight:700;">
              <span style="font-weight:800;color:var(--gold);font-style:italic;font-size:13px;">fx</span>
            </button>

            <!-- Drawings Pen Icon Button -->
            <button type="button" class="tf-btn" id="btnToggleDrawingsToolbar" title="Toggle Drawing Tools (Trendline, Fib, Channel, etc.)" style="display:inline-flex;align-items:center;justify-content:center;padding:4px 8px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
            </button>

            <!-- Pan / Crosshair Switch -->
            <button type="button" class="tf-btn" id="chartModeToggle" title="Switch to Pan Drag mode" style="display:inline-flex;align-items:center;justify-content:center;padding:4px 7px;">
              <span id="chartModeToggleIcon"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block;"><path d="M18 11V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v0"/><path d="M14 10V4a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v2"/><path d="M10 10.5V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v8"/><path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/></svg></span>
            </button>

            <!-- Clear Drawings -->
            <button type="button" class="tf-btn" id="clearDrawings" title="Clear All Drawings" style="padding:4px 7px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18m-2 0v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6m3 0V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
            </button>
          </div>

          <div style="display:flex;align-items:center;gap:6px;">
            <!-- Hidden fallback selects so existing engine bindings remain 100% stable -->
            <select id="indicatorSelect" style="display:none"><option value="">Add indicator…</option></select>
            <select id="drawingSelect" style="display:none"><option value="">Add drawing…</option></select>
            <div id="timeframeGroup" style="display:none"></div>

            <!-- CA AI Suggestions Pill -->
            <button class="btn gold small" id="chartAiSuggestBtn" title="CA AI Indicator &amp; Trendline Suggestions" style="font-weight:700;display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:6px;background:linear-gradient(135deg,rgba(239,251,245,0.12),rgba(38,217,166,0.18));border:1px solid var(--buy);color:var(--text);cursor:pointer;">
              ✦ CA AI Suggestions <span class="badge" id="chartAiBadge" style="position:static;width:auto;height:15px;padding:0 4px;border-radius:6px;font-size:8.5px;background:var(--buy);color:#0B2A1E;border:none;margin-left:2px;font-weight:700;">AI</span>
            </button>
          </div>
        </div>
        <div class="applied-tools" id="appliedTools"></div>
        <div class="indicator-applied-pane" id="indicatorAppliedPane" aria-live="polite"></div>
        <div class="muted" id="drawingStatus" style="margin-top:4px;display:none"></div>

        <!-- CA AI CHART ASSISTANT PANEL -->
        <div class="ca-chart-ai-panel card" id="chartAiPanel" style="display:none;margin:8px 0 12px;padding:12px 14px;border-radius:10px;background:var(--surface);border:1px solid rgba(38,217,166,0.3);box-shadow:0 8px 24px rgba(0,0,0,0.25);">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border-soft);flex-wrap:wrap;gap:8px;">
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:6px;background:var(--buy-bg);color:var(--buy);font-size:13px;font-weight:700;">✦</span>
              <div>
                <div style="font-weight:700;font-size:13px;color:var(--text);display:flex;align-items:center;gap:6px;">CA AI Chart Assistant <span class="tag buy" id="chartAiStatusTag" style="font-size:9.5px;padding:1px 6px;">Live Suggestions</span></div>
                <div class="muted" id="chartAiSub" style="font-size:10.5px;margin-top:2px;">Algorithmic Top-to-Top &amp; Bottom-to-Bottom Trendlines, Key S/R &amp; Indicators</div>
              </div>
            </div>
            <div style="display:flex;align-items:center;gap:6px;">
              <button class="btn buy small" id="chartAiApplyAllBtn" style="padding:4px 10px;font-size:11px;font-weight:700;">✦ Apply All to Chart</button>
              <button class="btn ghost small" id="chartAiCloseBtn" style="padding:3px 8px;font-size:12px;line-height:1;" title="Close CA AI panel">✕</button>
            </div>
          </div>
          <div class="ca-chart-ai-grid" id="chartAiContent" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;">
            <div class="muted" style="padding:10px;font-size:11px;">Loading CA AI chart suggestions…</div>
          </div>
        </div>

        <div class="chart-area chart-area-pro" id="chartViewport" style="position:relative;">
          <!-- Chart OHLC Display -->
          <div id="chartOhlcBar" style="position:absolute;top:10px;left:14px;z-index:25;display:flex;align-items:center;gap:10px;padding:3px 10px;border-radius:6px;background:var(--surface);border:1px solid var(--border);color:var(--text);backdrop-filter:blur(4px);font-family:var(--font-mono);font-size:11px;pointer-events:none;box-shadow:0 2px 8px rgba(0,0,0,0.15);">
            <span><b style="color:var(--text-faint);">O:</b> <span id="chartOhlcO" style="color:var(--text);font-weight:700;">—</span></span>
            <span><b style="color:var(--text-faint);">H:</b> <span id="chartOhlcH" style="color:var(--buy);font-weight:700;">—</span></span>
            <span><b style="color:var(--text-faint);">L:</b> <span id="chartOhlcL" style="color:var(--sell);font-weight:700;">—</span></span>
            <span><b style="color:var(--text-faint);">C:</b> <span id="chartOhlcC" style="color:var(--text);font-weight:700;">—</span></span>
          </div>
          <!-- Floating Drawing Toolbox -->
          <div id="chartDrawingToolbox" style="display:none;position:absolute;top:48px;left:14px;z-index:20;background:var(--surface);border:1px solid var(--border);border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,0.3);padding:3px;flex-direction:column;gap:3px;">
            <button type="button" class="drawing-tb-btn active" data-tool="trendline" title="Trendline">╱</button>
            <button type="button" class="drawing-tb-btn" data-tool="horizontal" title="Horizontal Line">―</button>
            <button type="button" class="drawing-tb-btn" data-tool="vertical" title="Vertical Line">│</button>
            <button type="button" class="drawing-tb-btn" data-tool="channel" title="Parallel Channel">═</button>
            <button type="button" class="drawing-tb-btn" data-tool="fibonacci" title="Fibonacci Retracement">☷</button>
            <button type="button" class="drawing-tb-btn" data-tool="brush" title="Brush / Freehand">✎</button>
            <button type="button" class="drawing-tb-btn" data-tool="text" title="Text Note">T</button>
          </div>
          <canvas id="upstoxCandles" class="upstox-candle-chart"></canvas>
          <button class="chart-fullscreen" id="chartFullscreen" title="Full screen" aria-label="Full screen"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H3v5M16 3h5v5M8 21H3v-5M21 16v5h-5"/></svg></button>
          <button class="chart-fast-forward" id="chartFastForward" title="Go to latest candle" aria-label="Go to latest candle"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m7 5 8 7-8 7V5Z"/><path d="M17 5v14"/></svg></button>
          <div class="chart-axis-label" id="crosshairPriceLabel" style="display:none"></div>
          <div class="chart-axis-label" id="crosshairTimeLabel" style="display:none"></div>
        </div>
      </div>

      <div class="indicator-summary card" id="indicatorSummary">
        <div class="card-head"><div class="card-title" id="indicatorSummaryTitle">Technical Indicator Signals</div><div class="muted" id="signalUpdated">Waiting for data…</div></div>
        <div class="indicator-table-wrap"><table class="indicator-table"><thead><tr><th>Indicator</th><th>Value</th><th>Materiality</th><th>Signal</th><th>Criteria</th></tr></thead><tbody id="indicatorRows"></tbody></table></div>
      </div>

      <div class="card" style="margin-bottom:14px;">
        <div class="card-head"><div class="card-title" id="candlePatternCardTitle">Candlestick Patterns</div><div class="muted" id="patternScanStatus">Continuous multi-timeframe scan</div></div>
        <div id="patternList" class="pattern-list"><div class="muted">Loading patterns…</div></div>
      </div>
      <div class="card" style="margin-bottom:14px;">
        <div class="card-head"><div class="card-title" id="trendPatternCardTitle">Trend &amp; Pattern Identifier</div><div class="muted" id="structureStatus">Last 10 candles when no range is selected</div></div>
        <div id="structureBox" class="pattern-list"><div class="muted">Loading trend, structure and likely outcome…</div></div>
      </div>
      <div class="card" style="margin-bottom:14px;">
        <div class="card-head"><div class="card-title" id="chartPatternCardTitle">Chart Patterns</div><div class="muted" id="chartPatternStatus">Rule-based pattern scan</div></div>
        <div id="chartPatternList" class="pattern-list"><div class="muted">Loading chart patterns…</div></div>
      </div>
    </div>

'''

new_text = text[:idx_start] + new_content + text[idx_end:]
with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Replacement done! Total characters:", len(new_text))

